---
title: WebRTC 심화
tags: [network, webrtc, p2p, stun, turn, ice, sdp, datachannel, nat]
updated: 2026-06-17
---

# WebRTC 심화

## 개요

WebRTC는 브라우저나 앱 사이에서 서버를 거치지 않고 직접 미디어와 데이터를 주고받는 기술이다. 화상 통화, 화면 공유, 저지연 게임 데이터 동기화 같은 곳에 쓴다. WebSocket과 헷갈리는 사람이 많은데, WebSocket은 클라이언트-서버 연결이고 WebRTC는 클라이언트-클라이언트(P2P) 연결이다. 다만 P2P 연결을 맺기까지의 과정이 WebSocket보다 훨씬 복잡하다. 두 단말이 서로의 주소를 모르고, 대부분 NAT 뒤에 있어서 공인 IP로 바로 연결되지 않기 때문이다.

WebRTC를 처음 붙일 때 "코드는 다 짰는데 로컬에서는 되고 운영에서는 연결이 안 된다"는 상황을 거의 다 겪는다. 이 문서는 그 연결 과정이 내부에서 어떻게 돌아가는지, 그리고 안 될 때 어디를 봐야 하는지를 중심으로 정리한다.

```
WebSocket:
  Client ──────▶ Server ◀────── Client
  (모든 트래픽이 서버를 경유)

WebRTC:
  Client ◀══════ 직접 연결(P2P) ══════▶ Client
       │                              │
       └──── 시그널링 서버 (연결 수립용) ────┘
  (연결만 서버 도움으로 맺고, 미디어/데이터는 직접)
```

P2P 개념 자체는 [P2P 문서](../P2P.md)에서 다루고, 여기서는 WebRTC가 실제로 그 연결을 어떻게 뚫는지를 본다.

## 전체 연결 흐름

연결이 맺히기까지 크게 세 단계를 거친다.

1. 시그널링: 두 단말이 서로의 정보(SDP, ICE 후보)를 교환한다. 이 교환 통로는 WebRTC가 제공하지 않는다. 직접 만들어야 한다.
2. ICE: 양쪽이 가능한 연결 경로 후보를 모으고, 그중 실제로 통하는 경로를 찾는다.
3. 연결: 찾은 경로로 DTLS 핸드셰이크를 하고 미디어/데이터를 흘린다.

```
A 단말                  시그널링 서버                  B 단말
  │                          │                          │
  │── Offer(SDP) ───────────▶│── Offer 전달 ───────────▶│
  │                          │                          │
  │◀─────────── Answer(SDP) ─│◀──────────── Answer ─────│
  │                          │                          │
  │── ICE 후보 ─────────────▶│── 후보 전달 ────────────▶│
  │◀──────────────── ICE 후보│◀──────────────── ICE 후보│
  │                          │                          │
  │◀════ 연결 점검(STUN 바인딩) ════▶ (서버 안 거침)      │
  │◀═══════ DTLS 핸드셰이크 ═══════▶                      │
  │◀═════ 미디어 / DataChannel ════▶                      │
```

핵심은 시그널링 서버는 연결을 맺을 때까지만 쓰이고, 일단 P2P가 뚫리면 미디어와 데이터는 서버를 거치지 않는다는 점이다. 그래서 서버 대역폭이 사용자 수에 비례해서 폭증하지 않는다. 단 뒤에서 설명할 TURN 릴레이로 떨어지면 이 전제가 깨진다.

## 시그널링 서버

WebRTC 명세에는 시그널링 프로토콜이 없다. 일부러 비워뒀다. 두 단말이 SDP와 ICE 후보를 교환할 통로만 있으면 되고, 그 통로를 WebSocket으로 만들든 HTTP 폴링으로 만들든 상관없다. 보통 WebSocket으로 만든다. 양방향이고 지연이 낮아서 후보 교환에 잘 맞는다.

시그널링 서버가 하는 일은 단순하다. A가 보낸 메시지를 B에게, B가 보낸 메시지를 A에게 전달한다. 메시지 내용을 해석할 필요도 없다. 그냥 상대에게 던져주면 된다.

```javascript
// 시그널링 서버 (Node.js + ws) — 룸 단위 릴레이만 한다
const rooms = new Map(); // roomId -> Set<WebSocket>

wss.on('connection', (ws) => {
  let roomId = null;

  ws.on('message', (raw) => {
    const msg = JSON.parse(raw);

    if (msg.type === 'join') {
      roomId = msg.roomId;
      if (!rooms.has(roomId)) rooms.set(roomId, new Set());
      rooms.get(roomId).add(ws);
      return;
    }

    // offer / answer / candidate 는 같은 방의 다른 사람에게 그대로 전달
    const peers = rooms.get(roomId);
    if (!peers) return;
    for (const peer of peers) {
      if (peer !== ws && peer.readyState === peer.OPEN) {
        peer.send(raw);
      }
    }
  });

  ws.on('close', () => {
    if (roomId && rooms.has(roomId)) {
      rooms.get(roomId).delete(ws);
    }
  });
});
```

여기서 자주 빠뜨리는 게 연결 종료 처리다. close 이벤트에서 룸 set을 비워주지 않으면 끊긴 소켓에 계속 send를 시도하고, 룸 인원 카운트도 틀어진다. 운영하다 보면 "방을 나갔는데 상대 화면에 아직 내가 보인다"는 류의 버그가 여기서 나온다.

시그널링 서버는 연결만 맺어주면 역할이 끝나지만, 실무에서는 보통 연결 유지 동안 켜둔다. 통화 중에 한쪽 네트워크가 바뀌면(와이파이→LTE) ICE 재협상이 일어나고, 새 후보를 다시 교환해야 하기 때문이다.

## SDP 교환

SDP(Session Description Protocol)는 "내가 어떤 코덱을 쓸 수 있고, 어떤 미디어를 보낼 거고, 암호화 키는 뭐고" 같은 연결 조건을 텍스트로 적은 문서다. A가 만든 걸 Offer, B가 그에 답해서 만든 걸 Answer라고 부른다. 이 둘을 교환하면 양쪽이 공통으로 쓸 코덱과 파라미터가 정해진다.

```javascript
// A 단말 (발신)
const pc = new RTCPeerConnection({ iceServers });

const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
stream.getTracks().forEach(track => pc.addTrack(track, stream));

const offer = await pc.createOffer();
await pc.setLocalDescription(offer);
signaling.send({ type: 'offer', sdp: offer.sdp });

// B 단말 (수신)
pc.ondatachannel = ... ;
signaling.on('offer', async (msg) => {
  await pc.setRemoteDescription({ type: 'offer', sdp: msg.sdp });
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  signaling.send({ type: 'answer', sdp: answer.sdp });
});

// 다시 A 단말
signaling.on('answer', async (msg) => {
  await pc.setRemoteDescription({ type: 'answer', sdp: msg.sdp });
});
```

SDP 본문은 이렇게 생겼다. 직접 파싱할 일은 거의 없지만 디버깅할 때 한 번씩 읽게 된다.

```
v=0
o=- 4611731400430051336 2 IN IP4 127.0.0.1
s=-
t=0 0
m=video 9 UDP/TLS/RTP/SAVPF 96 97
a=rtpmap:96 VP8/90000
a=rtpmap:97 H264/90000
a=candidate:1 1 udp 2122260223 192.168.0.10 54321 typ host
a=candidate:2 1 udp 1686052607 203.0.113.5 54321 typ srflx ...
```

`m=` 줄이 미디어 종류, `a=rtpmap` 이 코덱 협상 후보다. A가 VP8과 H264를 둘 다 제시했는데 B가 VP8만 지원하면 결과적으로 VP8로 합의된다. 여기서 양쪽이 겹치는 코덱이 하나도 없으면 연결은 맺혀도 영상이 안 나온다. 모바일에서 H264만 되는 단말과 데스크톱 브라우저를 붙일 때 가끔 이 문제가 난다.

순서도 중요하다. `setRemoteDescription`을 하기 전에 도착한 ICE 후보를 `addIceCandidate`로 넣으면 에러가 난다. 시그널링이 빨라서 후보가 Answer보다 먼저 도착하는 경우가 있어서, remoteDescription이 세팅되기 전 후보는 큐에 모아뒀다가 나중에 넣는 처리를 해두는 게 안전하다.

## ICE 후보 수집

ICE(Interactive Connectivity Establishment)는 "이 두 단말이 실제로 통할 수 있는 경로"를 찾는 절차다. 단말 하나가 가질 수 있는 주소는 한 개가 아니다. 사설 IP도 있고, NAT를 거친 공인 IP도 있고, 릴레이 서버 주소도 있다. 이 가능한 주소들을 후보(candidate)라고 부르고, 양쪽이 후보를 다 모아서 서로 교환한 뒤 짝을 지어가며 통하는 조합을 찾는다.

후보는 세 종류다.

| 종류 | 표기 | 의미 | 통하는 경우 |
|------|------|------|-----------|
| host | typ host | 단말의 로컬 주소 (사설 IP 포함) | 같은 LAN |
| server reflexive | typ srflx | STUN으로 알아낸 NAT 바깥 공인 주소 | 일반적인 NAT 환경 |
| relay | typ relay | TURN 서버가 대신 받아주는 주소 | NAT 통과 실패 시 |

```
후보 수집 과정:

  단말 A ── "내 공인 주소가 뭐야?" ──▶ STUN 서버
        ◀── "너는 203.0.113.5:54321 로 보여" ──

  → A는 자기 사설 주소(host)와 STUN이 알려준 공인 주소(srflx)를
    둘 다 후보로 등록하고, 시그널링으로 B에게 보낸다.
```

### STUN의 역할

NAT 뒤에 있는 단말은 자기 공인 IP를 모른다. 자기가 아는 건 사설 IP(예: 192.168.0.10)뿐이다. STUN 서버는 "너 지금 나한테 어떤 주소로 보이는지" 알려주는 역할만 한다. 단말이 STUN 서버에 패킷을 하나 보내면, STUN 서버는 그 패킷의 출발지 주소(즉 NAT를 거친 공인 주소)를 그대로 응답에 담아 돌려준다. 단말은 이걸로 자기 공인 주소를 알게 되고 srflx 후보로 등록한다.

STUN 서버는 가볍다. 주소만 알려주고 끝이라 트래픽을 중계하지 않는다. 구글이 공개로 운영하는 `stun.l.google.com:19302`를 테스트용으로 많이 쓴다. 다만 운영에서는 자체 STUN/TURN을 띄우는 게 맞다. 공개 STUN은 가용성 보장이 없다.

```javascript
const iceServers = [
  { urls: 'stun:stun.l.google.com:19302' },
  {
    urls: 'turn:turn.example.com:3478',
    username: 'webrtc',
    credential: 'secret',
  },
];
```

### Trickle ICE

후보를 다 모은 다음에 한꺼번에 보내면 느리다. STUN 응답을 기다리는 동안 연결이 지연된다. 그래서 후보가 하나 발견될 때마다 즉시 보내는 방식을 쓴다. 이걸 Trickle ICE라고 한다.

```javascript
pc.onicecandidate = (event) => {
  if (event.candidate) {
    // 후보 하나 발견 → 바로 시그널링으로 전송
    signaling.send({ type: 'candidate', candidate: event.candidate });
  } else {
    // event.candidate 가 null 이면 후보 수집 완료
    console.log('ICE 후보 수집 끝');
  }
};

signaling.on('candidate', async (msg) => {
  try {
    await pc.addIceCandidate(msg.candidate);
  } catch (e) {
    // remoteDescription 세팅 전이면 여기서 터진다 → 큐잉 필요
    console.error('candidate 추가 실패', e);
  }
};
```

host 후보는 STUN을 안 거치니 즉시 나오고, srflx는 STUN 왕복 후에, relay는 TURN 할당 후에 나온다. 그래서 후보가 시간차를 두고 도착한다. 로그를 보면 host가 먼저 깔리고 srflx, relay가 순서대로 붙는 게 보인다.

## NAT 통과와 TURN 릴레이

NAT 종류에 따라 STUN만으로 뚫리는 경우와 안 뚫리는 경우가 갈린다. 여기서 WebRTC 트러블슈팅의 절반이 나온다.

NAT는 동작 방식에 따라 분류되는데, 실무에서 문제 되는 건 Symmetric NAT다. Symmetric NAT는 목적지마다 다른 외부 포트를 할당한다. 즉 A가 STUN 서버에 보낼 때 쓴 공인 포트와, B에게 직접 보낼 때 쓰는 공인 포트가 다르다. STUN으로 알아낸 주소(srflx)가 B에게 보낼 때는 무효가 되는 것이다. 양쪽이 다 Symmetric NAT면 srflx 후보로는 절대 연결이 안 된다.

```
일반 NAT (Cone):
  A → STUN  : 공인주소 = 203.0.113.5:54321
  A → B     : 공인주소 = 203.0.113.5:54321  (같음 → srflx 통함)

Symmetric NAT:
  A → STUN  : 공인주소 = 203.0.113.5:54321
  A → B     : 공인주소 = 203.0.113.5:60000  (다름 → srflx 무효)
  → 직접 연결 불가, TURN 릴레이로 떨어짐
```

이때 쓰는 게 TURN(Traversal Using Relays around NAT)이다. TURN 서버는 양쪽 단말의 트래픽을 대신 받아서 상대에게 넘겨준다. 직접 연결이 아니라 서버를 한 번 거치는 중계다. 직접 연결이 안 되는 환경에서도 통신이 되게 해주는 마지막 수단이다.

```
직접 연결 실패 시 TURN 릴레이:

  A ──▶ TURN 서버 ──▶ B
  A ◀── TURN 서버 ◀── B

  미디어/데이터가 전부 TURN을 경유한다.
  → P2P의 장점(서버 부하 안 늘어남)이 사라진다.
```

TURN으로 떨어지면 그 통화의 모든 트래픽이 TURN 서버 대역폭을 먹는다. 화상 통화 한 건이 수 Mbps인데 이게 전부 서버를 지난다. 그래서 TURN 서버는 STUN과 달리 트래픽 비용이 크고, 공개 무료 TURN이 거의 없는 이유도 이거다. 운영에서는 coturn을 직접 띄우거나 Twilio 같은 유료 TURN을 쓴다.

```bash
# coturn 최소 설정 (/etc/turnserver.conf)
listening-port=3478
tls-listening-port=5349
fingerprint
lt-cred-mech
user=webrtc:secret
realm=turn.example.com
# 방화벽 환경 대응 — 뒤에서 설명
listening-ip=0.0.0.0
external-ip=203.0.113.50
```

전체 통화 중 TURN으로 떨어지는 비율은 환경에 따라 다르다. 일반 가정용 인터넷끼리는 대부분 직접 연결이 되지만, 기업 네트워크나 모바일 캐리어 NAT가 끼면 비율이 확 올라간다. 운영 모니터링에서 "TURN relay 비율"을 지표로 잡아두면, 갑자기 이 비율이 튈 때 네트워크 쪽 문제를 빨리 잡을 수 있다.

### ICE 후보 짝짓기

후보를 다 교환하면 ICE는 가능한 모든 조합을 만들어서 우선순위 순으로 연결을 시도한다. 우선순위는 host > srflx > relay 순이다. 직접 연결이 가장 좋고, 릴레이가 가장 비싸니까 마지막이다.

```
후보 쌍 점검 (Connectivity Check):

  (A host, B host)   → 같은 LAN이면 성공, 아니면 실패
  (A srflx, B srflx) → 일반 NAT면 성공
  (A relay, B *)     → 위가 다 실패하면 여기로
```

각 쌍에 대해 STUN 바인딩 요청을 주고받아서 실제로 통하는지 확인한다. 통하는 쌍 중 우선순위가 가장 높은 걸로 연결이 맺힌다. 이 과정이 `iceConnectionState`로 노출된다.

```javascript
pc.oniceconnectionstatechange = () => {
  console.log('ICE 상태:', pc.iceConnectionState);
  // checking → connected → completed  (정상)
  // checking → failed                 (모든 후보 쌍 실패)
  // connected → disconnected          (일시적 끊김, 복구될 수 있음)
};
```

`failed`가 뜨면 통하는 후보 쌍이 하나도 없다는 뜻이다. 십중팔구 TURN 설정이 없거나 잘못됐다. `disconnected`는 다르다. 네트워크가 잠깐 끊긴 거라 곧 `connected`로 돌아오는 경우가 많아서, 바로 연결을 끊지 말고 몇 초 기다려보는 게 낫다.

## DataChannel과 미디어 채널

WebRTC로 보낼 수 있는 건 두 가지다. 카메라/마이크 같은 미디어 트랙과, 임의의 데이터를 보내는 DataChannel이다. 둘은 전송 방식이 다르다.

| 구분 | 미디어 채널 | DataChannel |
|------|-----------|-------------|
| 전송 | RTP/SRTP over UDP | SCTP over DTLS |
| 신뢰성 | 비신뢰 (손실 허용) | 신뢰/비신뢰 선택 가능 |
| 순서 보장 | 없음 | 선택 가능 |
| 용도 | 영상, 음성 | 채팅, 파일, 게임 상태, 시그널 |

미디어는 실시간성이 신뢰성보다 중요하다. 영상 프레임 하나 손실됐다고 재전송 기다리면 화면이 멈춘다. 그래서 미디어는 UDP 위에서 손실을 허용하고 그냥 다음 프레임으로 넘어간다.

DataChannel은 TCP처럼 신뢰성 있게 보낼 수도 있고, UDP처럼 손실을 허용하게 설정할 수도 있다. 게임에서 위치 동기화처럼 "최신 값만 중요하고 옛날 패킷은 버려도 되는" 데이터는 비신뢰/비순서로 설정하는 게 낫다.

```javascript
// 신뢰성 있는 채널 (기본) — 채팅, 파일 전송
const chatChannel = pc.createDataChannel('chat');

// 비신뢰 채널 — 게임 위치 동기화 같은 거
const gameChannel = pc.createDataChannel('game', {
  ordered: false,        // 순서 보장 안 함
  maxRetransmits: 0,     // 재전송 안 함 (손실 허용)
});

chatChannel.onopen = () => chatChannel.send('연결됨');
chatChannel.onmessage = (e) => console.log('받음:', e.data);

// 수신 쪽
pc.ondatachannel = (event) => {
  const channel = event.channel;
  channel.onmessage = (e) => console.log(channel.label, e.data);
};
```

DataChannel만 쓰는 경우도 많다. 미디어 없이 P2P 데이터만 주고받는 멀티플레이 게임이나, 서버 부하 없이 파일을 직접 전송하는 경우다. 이때도 NAT 통과 과정은 미디어와 똑같다. STUN/TURN/ICE를 거쳐야 채널이 열린다. DataChannel은 서버 안 거치니 공짜라고 생각하기 쉬운데, TURN으로 떨어지면 데이터도 릴레이를 타서 똑같이 서버 대역폭을 먹는다.

한 가지 주의할 점은 DataChannel의 메시지 크기 제한이다. 큰 파일을 한 번에 send하면 버퍼가 넘쳐서 채널이 끊긴다. 보통 16KB 정도로 잘라서 보내고, `bufferedAmount`를 보면서 흐름을 조절해야 한다.

```javascript
const CHUNK = 16 * 1024;
const THRESHOLD = 1 * 1024 * 1024; // 1MB 넘으면 잠깐 멈춤

async function sendFile(channel, buffer) {
  for (let offset = 0; offset < buffer.byteLength; offset += CHUNK) {
    // 버퍼가 차면 비워질 때까지 대기
    while (channel.bufferedAmount > THRESHOLD) {
      await new Promise(r => setTimeout(r, 50));
    }
    channel.send(buffer.slice(offset, offset + CHUNK));
  }
}
```

## 방화벽 환경 트러블슈팅

로컬에서는 잘 되던 WebRTC가 회사 망이나 특정 고객사 환경에서 연결이 안 되는 일이 흔하다. 원인은 대부분 방화벽이 UDP를 막거나 특정 포트를 차단하는 데 있다. 순서대로 확인할 항목을 정리한다.

### UDP 차단

WebRTC 미디어는 기본적으로 UDP를 쓴다. 그런데 기업 방화벽은 보안상 UDP를 통째로 막아둔 곳이 많다. 이러면 STUN도 안 되고(STUN도 UDP), 미디어도 못 흐른다. 이때는 TURN을 TCP로, 더 나아가 TLS(443 포트)로 돌리는 설정이 필요하다.

```javascript
const iceServers = [
  { urls: 'stun:turn.example.com:3478' },
  // UDP TURN
  { urls: 'turn:turn.example.com:3478', username: 'u', credential: 'p' },
  // TCP TURN — UDP 막힌 환경
  { urls: 'turn:turn.example.com:3478?transport=tcp', username: 'u', credential: 'p' },
  // TLS TURN — 443 으로 위장, 거의 모든 방화벽 통과
  { urls: 'turns:turn.example.com:443?transport=tcp', username: 'u', credential: 'p' },
];
```

`turns:` (s가 붙은 것)는 TLS 위의 TURN이다. 443 포트로 돌리면 HTTPS 트래픽과 구분이 안 돼서 웬만한 방화벽은 통과시킨다. 연결이 도저히 안 되는 빡빡한 환경에서 마지막 카드로 쓴다. 단 모든 트래픽이 TURN을 경유하므로 가장 느리고 서버 부하가 크다.

### 어디서 막히는지 확인하는 법

연결이 안 될 때 추측하지 말고 실제 후보 상태를 봐야 한다. 크롬이면 `chrome://webrtc-internals`를 열면 ICE 후보와 연결 시도 과정이 전부 나온다. 코드에서는 `getStats()`로 확인한다.

```javascript
// 어떤 후보 쌍으로 연결됐는지 확인
const stats = await pc.getStats();
stats.forEach(report => {
  if (report.type === 'candidate-pair' && report.state === 'succeeded') {
    console.log('연결된 쌍:', report.localCandidateId, report.remoteCandidateId);
  }
  if (report.type === 'local-candidate') {
    console.log('로컬 후보:', report.candidateType, report.protocol, report.address);
  }
});
```

여기서 봐야 할 건 성공한 candidate-pair의 후보 타입이다.

- 양쪽 다 host면: 같은 LAN. 정상.
- srflx면: NAT 통과 성공. 정상.
- relay면: 직접 연결 실패해서 TURN 릴레이 중. 동작은 하지만 느리고 비싸다. 이게 의도보다 자주 나오면 NAT/방화벽을 점검해야 한다.
- candidate-pair가 아예 succeeded 없이 failed면: 통하는 경로가 없다. TURN이 없거나 TURN도 막힌 것.

### 자주 겪는 증상과 원인

운영하면서 반복적으로 만난 패턴들이다.

연결은 되는데 영상이 안 나온다. ICE는 connected인데 화면이 검다. 코덱 협상 실패이거나 미디어 트랙이 SDP에 안 실린 경우다. SDP의 `m=video` 줄과 양쪽 코덱 교집합을 확인한다.

로컬에서는 되고 운영에서만 안 된다. 로컬은 같은 LAN이라 host 후보로 바로 붙는다. 운영은 서로 다른 NAT 뒤라 STUN/TURN이 필요한데 TURN 설정이 빠진 경우가 대부분이다. 로컬 테스트로는 NAT 통과를 검증할 수 없다는 걸 기억해야 한다.

특정 고객사에서만 안 된다. 그 망의 방화벽이 UDP나 3478 포트를 막은 것이다. `turns:443` 으로 떨어뜨려서 되는지 본다. 되면 방화벽이 원인이라는 게 확정된다.

가끔 끊겼다가 다시 붙는다. `disconnected` → `connected` 반복. 모바일에서 네트워크가 흔들리거나 와이파이/LTE 전환 시 ICE 재협상이 일어나는 정상 동작에 가깝다. `iceRestart` 옵션으로 후보를 다시 모아 재연결하는 처리를 넣어두면 사용자가 끊김을 덜 느낀다.

```javascript
// 연결이 실패하면 ICE 재시작으로 후보 재수집
pc.oniceconnectionstatechange = async () => {
  if (pc.iceConnectionState === 'failed') {
    const offer = await pc.createOffer({ iceRestart: true });
    await pc.setLocalDescription(offer);
    signaling.send({ type: 'offer', sdp: offer.sdp });
  }
};
```

## 다대다 연결의 한계

여기까지는 1:1 연결을 전제로 했다. 그런데 화상 회의처럼 여러 명이 붙으면 P2P 풀메시는 금방 한계에 부딪힌다. N명이 서로 다 연결하면 각 단말이 N-1개의 연결을 유지하고 자기 영상을 N-1번 인코딩해서 보내야 한다. 4~5명만 넘어가도 클라이언트 CPU와 업로드 대역폭이 못 버틴다.

```
풀메시 (P2P 다대다):
  4명이면 각자 3개 연결 → 총 6개 연결, 각자 3번 송신
  10명이면 각자 9개 연결 → 클라이언트 폭발

SFU (미디어 서버):
  각 단말은 서버와 1개 연결만
  서버가 받아서 다른 사람들에게 분배
```

그래서 인원이 많아지면 SFU(Selective Forwarding Unit)나 MCU 같은 미디어 서버를 둔다. 각 단말은 서버와만 연결하고, 서버가 영상을 받아서 다른 참가자에게 뿌린다. 이러면 순수 P2P는 아니지만 클라이언트 부담이 사라진다. mediasoup, Janus, LiveKit 같은 게 이 SFU 구현이다. 소규모는 P2P로 충분하지만, 회의 규모가 커지면 SFU 도입을 검토하게 된다.

## 정리

WebRTC 연결이 안 될 때 볼 곳은 거의 정해져 있다. 시그널링이 SDP와 후보를 제대로 전달하는지, ICE 후보가 양쪽에서 수집되는지, TURN 설정이 있는지, 방화벽이 UDP를 막지는 않는지. `chrome://webrtc-internals`와 `getStats()`로 어느 후보 쌍에서 막히는지 확인하면 원인의 대부분이 잡힌다. 로컬에서 된다고 운영에서 되는 게 아니라는 것, TURN 없이는 NAT 통과가 보장되지 않는다는 것, 이 두 개만 기억해도 초기 삽질을 크게 줄인다.
