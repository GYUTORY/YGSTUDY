---
title: NAT 트래버설 — STUN, TURN, ICE
tags: [network, nat-traversal, stun, turn, ice, webrtc, hole-punching, coturn, p2p]
updated: 2026-06-24
---

# NAT 트래버설 — STUN, TURN, ICE

## 왜 이게 문제가 되는가

NAT 뒤에 있는 두 호스트를 직접 연결하려고 하면 양쪽 다 자기 공인 IP를 모른다는 데서 막힌다. 집에 있는 노트북은 자기 IP가 `192.168.0.10`인 줄 알지만, 인터넷 너머의 상대가 보는 주소는 공유기의 공인 IP에 NAT이 할당한 임의 포트다. 노트북은 그 포트 번호가 몇 번인지 알 길이 없다. 양쪽 다 모르니 서로에게 "여기로 보내"라고 알려줄 수도 없다.

게다가 NAT은 상태 테이블에 매칭되지 않는 inbound 패킷을 떨군다(NAT.md에서 다룬 내용이다). 안에서 밖으로 먼저 나간 흔적이 없으면 밖에서 들어오는 패킷은 그냥 버려진다. 서버라면 공인 IP에 포트를 열어두고 inbound를 기다리면 되지만, NAT 뒤 호스트끼리는 둘 다 "기다리는 쪽"이 될 수 없다. 누군가 먼저 나가야 구멍이 뚫리는데 양쪽이 동시에 그 짓을 해야 한다.

이걸 푸는 게 NAT 트래버설이다. 핵심 도구가 셋이다. STUN은 "내 공인 IP/포트가 뭐냐"를 알아내고, TURN은 직접 연결이 안 될 때 중계 서버로 우회하고, ICE는 이 둘을 포함한 여러 연결 경로 후보를 모아서 실제로 뚫리는 걸 골라낸다. WebRTC, VoIP, 게임 P2P, 화상회의 전부 이 셋 위에서 돌아간다.

```
         [STUN 서버]                    [TURN 서버]
              │                              │
   "네 공인 주소는              "직접 안 되면 나를 거쳐
    1.2.3.4:50000이야"              릴레이해줄게"
              │                              │
        ┌─────┴─────┐                  ┌─────┴─────┐
     [Peer A]    [Peer B]           직접 연결 실패 시
   NAT 뒤         NAT 뒤              모든 트래픽 우회
```

---

## STUN — 내 공인 주소 발견

STUN(Session Traversal Utilities for NAT)은 단순하다. NAT 뒤 호스트가 공인 인터넷에 있는 STUN 서버로 패킷 하나 보내면, 서버는 그 패킷이 도착했을 때 본 출발지 주소(즉 NAT이 바꿔치기한 공인 IP/포트)를 그대로 응답에 담아 돌려준다. 호스트는 그 응답을 보고 "아, 밖에서 내가 이 주소로 보인다"는 걸 알게 된다.

동작을 패킷 단위로 보면 이렇다. 노트북(`192.168.0.10:54321`)이 STUN 서버(`stun.example.com:3478`)로 Binding Request를 보낸다. 공유기를 지나면서 출발지가 `198.51.100.7:40000`으로 바뀐다. STUN 서버는 이 패킷을 받고 "너 `198.51.100.7:40000`에서 왔어"라고 Binding Response에 담아 보낸다. 응답이 공유기를 거꾸로 통과해 노트북에 도착한다.

```
sequenceDiagram
    participant N as 노트북 192.168.0.10:54321
    participant R as 공유기 NAT
    participant S as STUN 서버 3478

    N->>R: Binding Request (src 192.168.0.10:54321)
    R->>S: Binding Request (src 198.51.100.7:40000)
    Note over R: NAT 매핑 생성<br/>54321 ↔ 40000
    S-->>R: Binding Response<br/>(XOR-MAPPED-ADDRESS 198.51.100.7:40000)
    R-->>N: Binding Response
    Note over N: 내 공인 주소를 알게 됨
```

여기서 STUN이 알려주는 주소를 **서버 리플렉시브 주소**(server reflexive address, srflx)라고 부른다. ICE 단계에서 후보 타입 이름으로 다시 나오니 기억해둬야 한다.

STUN의 한계는 분명하다. 알려주는 건 "이 STUN 서버를 향해 나갔을 때의 매핑"이다. 상대 피어가 같은 매핑으로 들어올 수 있느냐는 NAT 타입에 달렸다. 이게 홀펀칭이 NAT 타입마다 성공/실패가 갈리는 이유다.

### STUN 직접 테스트

서버 운영하다 보면 STUN이 응답을 제대로 주는지 확인할 일이 생긴다. `stunclient`(coturn 패키지에 포함)로 바로 찍어볼 수 있다.

```bash
# coturn 설치하면 같이 들어오는 클라이언트
stunclient stun.l.google.com 19302

# 출력 예
# Binding test: success
# Local address: 192.168.0.10:54321
# Mapped address: 198.51.100.7:40000
```

`Mapped address`가 내 공인 주소다. 같은 명령을 여러 번 돌렸을 때 매핑 포트가 매번 바뀌면 Symmetric NAT을 의심해야 한다(아래에서 설명).

---

## NAT 타입과 홀펀칭 성공/실패

홀펀칭은 양쪽 피어가 거의 동시에 서로를 향해 패킷을 쏴서, 각자의 NAT에 outbound 매핑(=구멍)을 만들고 그 구멍으로 상대 패킷이 들어오게 하는 기법이다. 성공 여부는 NAT이 매핑과 필터링을 어떻게 하느냐에 달렸다. 전통적으로 네 가지로 나눈다.

| NAT 타입 | 매핑 동작 | inbound 필터링 | 홀펀칭 |
|---|---|---|---|
| Full Cone | 출발지 포트 고정, 목적지 무관하게 같은 매핑 | 아무나 그 포트로 보내면 통과 | 거의 항상 성공 |
| Restricted Cone | 출발지 포트 고정 | 내가 먼저 보낸 IP에서 온 것만 통과 | 성공 |
| Port Restricted Cone | 출발지 포트 고정 | 내가 먼저 보낸 IP+포트에서 온 것만 통과 | 성공(타이밍 민감) |
| Symmetric | 목적지마다 다른 포트 매핑 | 내가 보낸 IP+포트에서 온 것만 통과 | 자주 실패 |

핵심 구분은 **매핑이 목적지에 따라 바뀌느냐**다. Cone 계열(앞 세 개)은 어디로 보내든 같은 공인 포트를 쓴다. 그래서 STUN 서버를 향해 만든 매핑(`40000`)을 상대 피어도 그대로 쓸 수 있다. Symmetric NAT은 목적지가 다르면 다른 포트를 쓴다. STUN 서버로 갈 때는 `40000`, 상대 피어로 갈 때는 `40002`를 할당한다. STUN이 알려준 `40000`은 상대에게 쓸모가 없다. 상대가 `40000`으로 보내봤자 그 매핑은 STUN 서버 전용이라 필터링에 막힌다.

### 양쪽 다 Cone일 때 홀펀칭이 뚫리는 과정

```
sequenceDiagram
    participant A as Peer A (Restricted Cone)
    participant SA as A의 NAT
    participant SB as B의 NAT
    participant B as Peer B (Restricted Cone)

    Note over A,B: 시그널링으로 서로의 srflx 주소를 이미 교환함
    A->>SA: B의 공인주소로 패킷 발사
    SA->>SB: 도착 (B의 NAT에 아직 A 매핑 없음 → 떨굼)
    Note over SB: 하지만 A의 NAT에는<br/>B행 구멍이 뚫림
    B->>SB: A의 공인주소로 패킷 발사
    SB->>SA: 도착 (A의 NAT에 B 매핑 있음 → 통과!)
    SA->>A: 패킷 전달
    A->>B: 이후 양방향 통신 성립
```

먼저 쏜 A의 패킷은 B의 NAT에서 버려진다. 하지만 그 패킷이 A의 NAT에 "B로 가는 구멍"을 뚫어놨다. 곧이어 B가 쏜 패킷이 A의 NAT에 도착하면 이미 구멍이 있으니 통과한다. 이 타이밍을 맞추는 게 ICE의 연결성 점검이다.

### Symmetric NAT이 끼면 왜 실패하나

한쪽이라도 Symmetric NAT이면 곤란해진다. 상대 피어로 나가는 매핑 포트를 STUN으로는 미리 알 수가 없기 때문이다. 실무에서 Symmetric NAT을 만나는 대표적인 경우가 통신사 CGNAT(Carrier-Grade NAT), 기업 방화벽, 일부 LTE/5G 모바일 망이다. 모바일 핫스팟으로 화상통화하면 릴레이 타는 비율이 확 올라가는 게 이 때문이다.

양쪽 다 Symmetric이면 홀펀칭은 사실상 불가능하다. 한쪽만 Symmetric이고 다른 쪽이 Full Cone이면 가끔 뚫리는데(포트 예측을 시도하는 구현도 있다), 신뢰할 수 없다. 결국 TURN으로 폴백한다.

---

## TURN — 직접 연결이 안 될 때의 릴레이

TURN(Traversal Using Relays around NAT)은 홀펀칭이 실패했을 때 쓰는 우회로다. 공인 인터넷에 있는 TURN 서버가 두 피어 사이에서 패킷을 중계한다. A가 보낸 걸 TURN 서버가 받아서 B에게 전달하고, 그 반대도 한다. 양쪽 피어는 TURN 서버하고만 통신하면 되니 NAT 타입이 뭐든 상관없다. 둘 다 outbound 연결은 되니까.

```
   [Peer A] ──outbound──▶ [TURN 서버] ◀──outbound── [Peer B]
            ◀──relay────             ────relay──▶
   
   A는 TURN 서버의 relayed address를 통해 B와 통신
   실제 패킷은 전부 TURN 서버를 경유
```

TURN을 쓰면 연결은 거의 항상 성립한다. 대신 대가가 크다. 모든 트래픽이 서버를 거치니 **대역폭 비용이 그대로 서버 부담**이 된다. 화상회의 1:1이 릴레이로 떨어지면 양방향 영상 전체가 TURN 서버를 통과한다. 지연도 늘어난다(A → 서버 → B로 한 단계 더 거친다). 그래서 TURN은 최후의 수단이고, 가능하면 직접 연결을 먼저 시도한다. 이 우선순위를 자동으로 처리하는 게 ICE다.

TURN이 알려주는 중계 주소를 **릴레이드 주소**(relayed address, relay)라고 한다. ICE 후보의 한 종류다.

### 운영에서 TURN 비중이 곧 비용이다

서비스 규모가 커지면 "전체 세션 중 몇 %가 TURN을 타느냐"가 인프라 비용을 좌우한다. 보통 직접 연결 성공률이 80~90%, 나머지가 릴레이다. 그런데 사용자층에 모바일이나 기업망이 많으면 릴레이 비율이 30~40%까지 올라간다. coturn 같은 자체 TURN을 운영하느냐, Twilio 같은 상용 TURN을 쓰느냐는 이 비율과 트래픽 단가를 보고 결정한다. 자체 운영은 서버 대역폭(특히 egress) 비용이 직접 청구된다.

---

## coturn 서버 설정

TURN 서버 구현체로 사실상 표준인 게 coturn이다. STUN과 TURN을 한 데몬에서 같이 처리한다. 실무에서 자주 쓰는 설정만 추린다.

```bash
# /etc/turnserver.conf

# 리스닝 포트 (STUN/TURN 기본 3478, TLS는 5349)
listening-port=3478
tls-listening-port=5349

# 서버가 바인딩할 IP. 공인 IP가 직접 붙어있으면 그걸,
# 클라우드처럼 NAT 뒤(사설 IP에 EIP 매핑)면 external-ip로 명시
listening-ip=0.0.0.0
external-ip=203.0.113.50

# 릴레이에 쓸 포트 범위. 동시 세션 수만큼 포트가 필요하니 넉넉히
min-port=49152
max-port=65535

# 인증 — 이걸 안 하면 누구나 내 서버로 릴레이를 돌린다(오픈 릴레이)
# long-term credential 방식
lt-cred-mech
realm=turn.example.com

# 정적 계정 (테스트용). 운영은 아래 use-auth-secret 권장
user=webrtcuser:strongpassword

# TLS 인증서 (TCP/TLS 릴레이용, 방화벽 우회에 필수)
cert=/etc/letsencrypt/live/turn.example.com/fullchain.pem
pkey=/etc/letsencrypt/live/turn.example.com/privkey.pem

# 로그
log-file=/var/log/turnserver.log
verbose
```

운영에서 정적 `user=`를 그대로 쓰면 안 된다. 자격증명이 클라이언트 코드에 박혀 유출되면 누구나 내 릴레이를 공짜로 쓴다. 그래서 **시간 제한 자격증명**(time-limited credential)을 쓴다. 공유 시크릿으로 만료 시각이 들어간 임시 username/password를 서버 쪽에서 발급하고, 클라이언트는 그걸 받아 잠깐만 쓴다.

```bash
# turnserver.conf
use-auth-secret
static-auth-secret=여기에_긴_랜덤_시크릿
realm=turn.example.com
```

애플리케이션 서버에서 자격증명을 만드는 코드(Node.js 예시)다.

```javascript
const crypto = require('crypto');

function makeTurnCredential(secret, ttlSeconds = 3600) {
  // username = 만료 unix timestamp (필요하면 ":userId"를 붙이기도 함)
  const expiry = Math.floor(Date.now() / 1000) + ttlSeconds;
  const username = String(expiry);

  // password = HMAC-SHA1(secret, username)을 base64로
  const hmac = crypto.createHmac('sha1', secret);
  hmac.update(username);
  const credential = hmac.digest('base64');

  return { username, credential };
}

// WebRTC 클라이언트에 내려줄 iceServers 구성
const { username, credential } = makeTurnCredential(process.env.TURN_SECRET);
const iceServers = [
  { urls: 'stun:turn.example.com:3478' },
  {
    urls: [
      'turn:turn.example.com:3478?transport=udp',
      'turn:turn.example.com:3478?transport=tcp',
      'turns:turn.example.com:5349?transport=tcp'  // TLS
    ],
    username,
    credential
  }
];
```

`turns:`(TLS)와 `transport=tcp`를 같이 넣는 게 중요하다. UDP가 막힌 환경에서 폴백 경로가 되기 때문이다(다음 절).

설정 끝나면 외부에서 실제로 릴레이가 도는지 확인한다.

```bash
# UDP TURN 할당 테스트
turnutils_uclient -u webrtcuser -w strongpassword -v turn.example.com

# 성공하면 "allocate" "refresh" 로그가 찍히고 패킷이 오감
# 방화벽에서 min-port~max-port 범위가 안 열려있으면 allocate는 되는데
# 실제 데이터가 안 가는 증상이 나온다 — 포트 범위 개방 확인할 것
```

---

## ICE — 후보 수집과 연결성 점검

ICE(Interactive Connectivity Establishment)는 STUN과 TURN을 묶어서 "쓸 수 있는 모든 경로를 모으고, 실제로 뚫리는 걸 골라 쓰는" 프레임워크다. 직접 STUN/TURN을 호출하는 코드를 짜는 게 아니라, WebRTC 같은 라이브러리가 ICE를 내부에서 돌리고 우리는 시그널링만 연결해준다.

ICE는 세 종류의 **후보**(candidate)를 모은다.

- **host 후보**: 단말의 로컬 IP/포트 그대로. 같은 LAN이면 이걸로 바로 붙는다. NAT을 아예 안 거치는 경우다.
- **srflx 후보**: STUN으로 알아낸 공인 주소. NAT 너머 직접 연결용.
- **relay 후보**: TURN 서버의 중계 주소. 최후의 폴백.

각 피어가 자기 후보를 다 모아서 상대에게 보낸다. 그러면 양쪽 후보를 짝지어(candidate pair) 우선순위 순으로 실제 패킷을 주고받으며 뚫리는지 확인한다. 이 점검에 STUN Binding Request를 쓴다(connectivity check). 뚫린 짝 중 우선순위가 가장 높은 걸 골라 실제 미디어/데이터를 흘린다.

우선순위는 host > srflx > relay 순이다. 같은 LAN이면 host로 즉시, NAT 너머면 srflx로 홀펀칭, 그것도 안 되면 relay. 이 폴백이 자동이다. 그래서 ICE를 쓰면 "직접 되면 직접, 안 되면 릴레이"가 코드 한 줄 없이 처리된다.

```
flowchart TD
    A[후보 수집 시작] --> B[host 후보: 로컬 IP]
    A --> C[srflx 후보: STUN 질의]
    A --> D[relay 후보: TURN allocate]
    B --> E[후보 목록 완성]
    C --> E
    D --> E
    E --> F[시그널링으로 상대와 후보 교환]
    F --> G[candidate pair 우선순위 정렬]
    G --> H[높은 우선순위부터 연결성 점검]
    H --> I{뚫린 pair 있나}
    I -->|host/srflx 성공| J[직접 연결 사용]
    I -->|직접 전부 실패| K[relay pair 사용]
```

### Trickle ICE — 후보를 모으는 족족 보낸다

원래 ICE는 후보를 전부 모은 다음 한꺼번에 교환했다. 문제는 relay 후보 수집(TURN allocate)이 느려서, 다 모일 때까지 기다리면 연결 시작이 지연된다. 그래서 **Trickle ICE**가 나왔다. 후보가 하나 생길 때마다 즉시 상대에게 흘려보내고, 받는 쪽은 받는 족족 점검을 시작한다. host 후보로 LAN 연결이 바로 되면 느린 relay 후보는 기다릴 필요도 없다. WebRTC는 기본이 Trickle ICE다.

---

## WebRTC 시그널링과 ICE candidate 교환

ICE가 후보를 교환하려면 "교환할 통로"가 있어야 한다. 그런데 그 통로가 바로 우리가 뚫으려는 P2P 연결이다. 닭과 달걀이다. 그래서 ICE는 **시그널링 채널**을 별도로 요구한다. 보통 WebSocket 서버를 하나 띄워서, 그걸 통해 양쪽이 연결 정보(SDP)와 ICE 후보를 주고받는다. 시그널링 서버는 연결 협상만 중계하고, 일단 P2P가 맺어지면 실제 데이터에는 관여하지 않는다.

교환되는 게 둘이다. **SDP**(Session Description Protocol)는 코덱, 미디어 종류, 암호화 정보 같은 세션 메타데이터다. offer/answer 형태로 한 번씩 주고받는다. **ICE candidate**는 위에서 모은 후보들이고, Trickle ICE라 SDP 교환 후에도 계속 흘러나온다.

```
sequenceDiagram
    participant A as Peer A
    participant SIG as 시그널링 서버 (WebSocket)
    participant B as Peer B

    A->>A: createOffer() → SDP offer
    A->>SIG: offer 전송
    SIG->>B: offer 전달
    B->>B: setRemoteDescription(offer)
    B->>B: createAnswer() → SDP answer
    B->>SIG: answer 전송
    SIG->>A: answer 전달
    A->>A: setRemoteDescription(answer)

    Note over A,B: 이제 양쪽이 후보를 수집하며 흘려보냄 (Trickle)
    A->>SIG: ICE candidate (host)
    SIG->>B: candidate 전달
    B->>SIG: ICE candidate (host)
    SIG->>A: candidate 전달
    A->>SIG: ICE candidate (srflx)
    SIG->>B: candidate 전달
    Note over A,B: 받는 족족 연결성 점검
    A-->>B: 연결 성립 시 P2P 데이터 흐름 (서버 거치지 않음)
```

클라이언트 코드의 뼈대는 이렇다. ICE 자체는 브라우저가 처리하고, 우리는 이벤트를 시그널링으로 중계하는 글루 코드만 쓴다.

```javascript
const pc = new RTCPeerConnection({ iceServers });  // 위에서 만든 iceServers

// 브라우저가 후보를 하나 찾을 때마다 호출됨 → 시그널링으로 상대에게
pc.onicecandidate = (event) => {
  if (event.candidate) {
    signaling.send({ type: 'candidate', candidate: event.candidate });
  }
};

// 상대로부터 후보를 받으면 추가
signaling.on('candidate', async (msg) => {
  await pc.addIceCandidate(msg.candidate);
});

// 연결 상태 추적 — 디버깅의 핵심
pc.oniceconnectionstatechange = () => {
  console.log('ICE state:', pc.iceConnectionState);
  // checking → connected/completed가 정상
  // failed면 후보 점검 전부 실패 (TURN 설정/방화벽 의심)
};

// 발신 측
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);
signaling.send({ type: 'offer', sdp: offer });
```

`iceConnectionState`가 디버깅의 출발점이다. `checking`에서 멈춰있다가 `failed`로 가면 어떤 후보도 안 뚫린 거다. `connected`까지 갔는데 영상이 안 나오면 후보는 뚫렸으나 미디어 협상(코덱 등) 문제다. 둘을 구분해야 헛다리를 안 짚는다.

실제로 어떤 후보 pair가 선택됐는지는 `getStats()`로 확인한다.

```javascript
const stats = await pc.getStats();
stats.forEach((report) => {
  if (report.type === 'candidate-pair' && report.nominated && report.state === 'succeeded') {
    console.log('선택된 pair:', report.localCandidateId, report.remoteCandidateId);
    // 여기서 local/remote 후보 타입을 추적하면
    // 직접 연결(srflx)인지 릴레이(relay)인지 알 수 있다
  }
});
```

운영 중에 "이 세션이 릴레이를 탔는지"를 집계하려면 이 stats에서 후보 타입을 긁어 로깅한다. relay 비율이 비용 지표라 모니터링할 가치가 있다.

---

## 트러블슈팅 — UDP가 막혀 TCP/TLS 릴레이로 떨어질 때

가장 자주 겪는 문제가 이거다. ICE는 기본적으로 UDP를 쓴다. 미디어는 약간의 패킷 손실을 감수하고 지연을 줄이는 게 이득이라 UDP가 맞다. 그런데 기업 방화벽이나 일부 공공 와이파이는 UDP outbound를 통째로 막는다. 443/80 같은 웹 포트만 열어둔다. 이런 환경에서는 STUN도 안 되고(UDP 3478 막힘) TURN UDP 릴레이도 안 된다. host/srflx/relay-udp 후보가 전부 점검에 실패한다.

이때 살아남는 경로가 **TCP, 그리고 TLS over TCP TURN**이다. 우선순위는 이렇게 떨어진다.

```
UDP 직접(host/srflx)  ──막힘──▶  TURN over UDP  ──막힘──▶
TURN over TCP (3478)  ──DPI에 막힘──▶  TURN over TLS (5349, 443처럼 보임)
```

`turns:`(TLS) 릴레이가 마지막 보루인 이유는, **TLS로 감싼 TCP 트래픽이 평범한 HTTPS와 구분이 안 되기 때문**이다. 방화벽이 패킷 내용을 들여다보는 DPI(Deep Packet Inspection)를 해도 TLS 핸드셰이크 안쪽은 못 본다. 그래서 TURN 서버를 5349가 아니라 아예 **443 포트**로 띄우는 경우가 많다. 443은 어떤 방화벽도 막기 어렵다(막으면 웹이 다 죽으니까).

```bash
# turnserver.conf — TLS TURN을 443에 띄우기
tls-listening-port=443
cert=/etc/letsencrypt/live/turn.example.com/fullchain.pem
pkey=/etc/letsencrypt/live/turn.example.com/privkey.pem
```

클라이언트 iceServers에 `turns:turn.example.com:443?transport=tcp`를 넣어두면, UDP가 다 막힌 환경에서도 이 경로로 연결이 살아난다. 대신 TCP+TLS라 지연과 오버헤드가 가장 크다. 그래도 안 되는 것보단 낫다.

### 증상별로 원인 좁히기

연결이 안 될 때 어디가 문제인지 좁히는 순서다.

`iceConnectionState`가 `checking`에서 `failed`로 가는데 같은 LAN에서는 잘 된다 → 외부 망에서 STUN/TURN이 안 닿는 거다. 클라이언트에서 STUN 서버로 UDP가 나가는지부터 확인한다.

```bash
# 클라이언트 망에서 직접 STUN 도달 확인
stunclient turn.example.com 3478
# "Binding test: fail"이면 UDP 3478 outbound가 막힌 것
```

TURN allocate는 되는데 데이터가 안 흐른다 → coturn의 `min-port~max-port` 범위가 방화벽/보안그룹에서 안 열렸다. allocate는 3478로 처리되지만 실제 릴레이는 그 포트 범위를 쓴다. 클라우드면 보안그룹에 UDP 49152-65535를 열어야 한다.

`turn:`(평문 TCP)는 막히는데 원인을 모르겠다 → DPI가 TURN 프로토콜 시그니처를 잡아 떨구는 경우가 있다. `turns:` 443으로 바꾸면 우회된다.

coturn 로그(`verbose` 켜고 `/var/log/turnserver.log`)에서 `allocate` 요청이 들어오는지, `401 Unauthorized`가 뜨는지 본다. 401이 반복되면 시간 제한 자격증명의 시계가 안 맞거나(TTL 만료) 시크릿이 서버/클라이언트 간 불일치다.

`external-ip`를 빠뜨린 경우도 흔하다. 클라우드 인스턴스는 사설 IP에 공인 EIP가 매핑된 구조라, coturn이 자기 사설 IP를 후보로 광고해버리면 외부에서 못 닿는다. `external-ip=공인IP/사설IP` 형식으로 명시해야 광고 주소가 교정된다.

---

## 정리해두면 좋은 것

NAT 트래버설은 결국 "직접 연결을 최대한 시도하되 안 되면 릴레이로 떨어진다"는 한 문장으로 요약된다. STUN은 내 공인 주소를 알려주고, TURN은 중계로 우회하고, ICE는 이 둘로 만든 후보를 점검해 최적 경로를 자동으로 고른다. 실무에서 신경 쓸 지점은 셋이다. NAT 타입(특히 모바일/기업망의 Symmetric)이 릴레이 비율을 좌우한다는 것, TURN 릴레이 트래픽이 곧 서버 비용이라는 것, UDP가 막힌 환경을 위해 TLS over TCP TURN을 443에 반드시 준비해둬야 한다는 것이다. 이 세 가지를 빼먹으면 "내 환경에서는 되는데 고객사에서는 안 되는" 전형적인 NAT 트래버설 장애를 만난다.
