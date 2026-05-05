---
title: WebSocket 심화 가이드
tags: [network, websocket, real-time, socket, stomp, socket-io, sse]
updated: 2026-05-04
---

# WebSocket 심화

## 개요

WebSocket은 단일 TCP 연결 위에서 전이중(Full-Duplex) 양방향 통신을 제공하는 프로토콜이다. RFC 6455에 정의되어 있고, HTTP의 요청-응답 모델과 달리 핸드셰이크 후에는 서버와 클라이언트가 언제든 자유롭게 메시지를 주고받는다.

```
HTTP (단방향):
  Client ──요청──▶ Server
  Client ◀──응답── Server
  Client ──요청──▶ Server  (매번 새 연결 또는 재요청)

WebSocket (양방향):
  Client ──HTTP 핸드셰이크──▶ Server
  Client ◀════ 양방향 통신 ════▶ Server  (연결 유지)
```

### 통신 방식 비교

| 방식 | 지연 | 서버 부하 | 양방향 | 적합한 경우 |
|------|------|----------|--------|-----------|
| Polling | 높음 (주기적) | 높음 | 아니오 | 단순 업데이트 |
| Long Polling | 중간 | 중간 | 아니오 | 알림 시스템 |
| SSE | 낮음 | 낮음 | 서버→클라이언트만 | 주식 시세, 로그 스트리밍 |
| WebSocket | 매우 낮음 | 낮음 | 예 | 채팅, 게임, 실시간 협업 |

WebSocket이 만능은 아니다. 서버→클라이언트 단방향이면 SSE가 인프라 친화적이고, 1초 단위 폴링으로 충분한 도메인이면 굳이 도입할 이유가 없다. 양방향 저지연이 명확히 필요한 시나리오에서만 가치가 있다.

## 연결 수립 (Handshake)

WebSocket은 HTTP 업그레이드 메커니즘으로 연결을 시작한다. 첫 GET 요청에 `Upgrade: websocket` 헤더를 실어 보내고, 서버가 `101 Switching Protocols`로 응답하면 그 시점부터 같은 TCP 소켓이 WebSocket 프레임 채널로 전환된다.

```
클라이언트 요청:
  GET /chat HTTP/1.1
  Host: server.example.com
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Key: dGhlIHNhbXBsZQ==
  Sec-WebSocket-Version: 13
  Sec-WebSocket-Protocol: chat, superchat
  Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits

서버 응답:
  HTTP/1.1 101 Switching Protocols
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9k...
  Sec-WebSocket-Protocol: chat
  Sec-WebSocket-Extensions: permessage-deflate
```

`Sec-WebSocket-Accept`는 클라이언트가 보낸 `Sec-WebSocket-Key`와 매직 GUID `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`를 이어붙인 뒤 SHA-1 해시를 Base64로 인코딩한 값이다. 서버가 진짜 WebSocket 프로토콜을 이해한다는 증명용이다. 이 값을 잘못 계산하면 브라우저는 핸드셰이크 실패로 처리한다.

핸드셰이크 과정에서 흔히 발생하는 문제는 두 가지다. 하나는 중간 프록시가 `Connection`, `Upgrade` 헤더를 임의로 제거하거나 변형하는 경우다. 또 하나는 서버가 `101` 대신 `400`이나 `200`을 반환하는 경우인데, 보통 `Sec-WebSocket-Version` 미스매치이거나 Origin 차단이다.

## 프레임 구조

핸드셰이크 이후 모든 데이터는 프레임(Frame) 단위로 전송된다. 프레임 헤더는 최소 2바이트, 마스킹 키와 확장 길이 필드까지 포함하면 최대 14바이트다.

```
WebSocket 프레임:
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-------+-+-------------+-------------------------------+
 |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
 |I|S|S|S|  (4)  |A|     (7)     |            (16/64)            |
 |N|V|V|V|       |S|             |   (if payload len==126/127)   |
 | |1|2|3|       |K|             |                               |
 +-+-+-+-+-------+-+-------------+-------------------------------+
 |     Masking-key (if MASK=1)   |       Payload Data ...        |
 +-------------------------------+-------------------------------+
```

| 필드 | 크기 | 설명 |
|------|------|------|
| FIN | 1 bit | 마지막 프레임 여부 (0이면 continuation 후속) |
| RSV1~3 | 3 bit | 확장용. permessage-deflate가 RSV1을 압축 표시로 사용 |
| opcode | 4 bit | 프레임 타입 (0x0 continuation, 0x1 text, 0x2 binary, 0x8 close, 0x9 ping, 0xA pong) |
| MASK | 1 bit | 클라이언트→서버는 반드시 1 |
| Payload length | 7/16/64 bit | 0~125 즉시값, 126이면 다음 16bit, 127이면 다음 64bit |
| Masking-key | 32 bit | MASK=1일 때만 존재 |
| Payload Data | 가변 | 마스킹된 실제 데이터 |

opcode는 4비트라 16개 값을 가질 수 있지만, RFC 6455에서 정의된 건 위 6개뿐이다. 0x3~0x7은 데이터 프레임용 예약, 0xB~0xF는 컨트롤 프레임용 예약 영역이다. 정의되지 않은 opcode를 받으면 즉시 1002(Protocol error)로 종료해야 한다.

## 프레임 마스킹 알고리즘

WebSocket의 가장 특이한 설계는 클라이언트→서버 방향에서 페이로드를 반드시 마스킹해야 한다는 점이다. 서버→클라이언트 방향은 마스킹하지 않는다.

### 마스킹 절차

마스킹은 4바이트 랜덤 키와 페이로드의 XOR 연산이다. 단순한 스트림 암호처럼 보이지만 보안 목적이 아니다.

```
1. 클라이언트가 4바이트 마스킹 키 생성 (암호학적 난수)
   masking_key = [k0, k1, k2, k3]

2. 페이로드의 i번째 바이트를 다음 공식으로 변환
   masked[i] = original[i] XOR masking_key[i mod 4]

3. 마스킹 키를 헤더에 그대로 실어 전송 (서버가 복호화하려면 필요)

4. 서버는 같은 공식을 반대로 적용
   original[i] = masked[i] XOR masking_key[i mod 4]
```

직접 구현해 보면 이런 모양이다.

```javascript
function maskPayload(payload, maskingKey) {
    const masked = Buffer.alloc(payload.length);
    for (let i = 0; i < payload.length; i++) {
        masked[i] = payload[i] ^ maskingKey[i % 4];
    }
    return masked;
}

function generateMaskingKey() {
    return crypto.randomBytes(4);
}
```

언마스킹도 같은 함수다. XOR 연산은 자기 역연산이라 한 번 더 적용하면 원본이 나온다.

### 마스킹을 강제하는 이유

마스킹은 데이터를 숨기기 위함이 아니다. 키를 헤더에 평문으로 실어 보내는데 보호가 될 리 없다. 진짜 이유는 캐시 포이즈닝(Cache Poisoning) 공격을 막기 위함이다.

WebSocket이 처음 표준화될 때 큰 우려가 있었다. 악성 페이지가 사용자의 브라우저로 하여금 ws:// 트래픽을 발생시키게 한 뒤, 그 트래픽을 중간 프록시가 일반 HTTP 응답으로 오해해서 캐시에 저장한다면, 같은 프록시를 쓰는 다른 사용자들에게 위변조된 응답이 전달될 수 있었다. 이 시나리오는 다음 단계로 진행된다.

```
1. 공격자가 운영하는 페이지가 피해자 브라우저에서 ws:// 연결을 연다
2. WebSocket 페이로드에 가짜 HTTP 응답 형태의 바이트열을 심는다
   "HTTP/1.1 200 OK\r\nContent-Type: text/javascript\r\n\r\n악성코드"
3. 중간 프록시가 이를 캐시 가능한 HTTP 응답으로 오인하면
   같은 URL을 요청하는 모든 사용자에게 악성 응답을 반환한다
```

마스킹이 도입되면 페이로드의 모든 바이트가 매번 다른 4바이트 키와 XOR된다. 공격자가 어떤 평문 바이트열을 꽂아 넣어도, 실제 와이어 위에서는 무작위로 보이는 바이트가 흐른다. 프록시가 이를 HTTP 응답 형태로 오해할 확률은 사실상 0이다.

운영하면서 이 점을 잊고 직접 프로토콜을 구현하면 곤란해진다. 프레임을 받는 서버가 MASK 비트가 0인 클라이언트 프레임을 받으면 즉시 close code 1002로 종료해야 한다. 표준 라이브러리는 이를 자동으로 검사하지만, 자체 구현시 빼먹기 쉽다.

서버→클라이언트는 왜 마스킹하지 않을까. 캐시 포이즈닝 위협이 그 방향에는 없기 때문이다. 클라이언트의 응답 캐시는 보통 동일 출처 응답만 캐싱하므로, 임의 출처의 페이지가 다른 사이트의 캐시를 오염시킬 경로가 차단되어 있다.

## 프레임 분할 (Fragmentation)

큰 메시지는 여러 프레임으로 쪼개서 보낼 수 있다. FIN 비트가 0이면 후속 프레임이 더 있다는 뜻이고, 1이면 마지막 프레임이다. 첫 프레임만 실제 opcode(0x1 text, 0x2 binary)를 가지고, 나머지는 continuation frame(opcode 0x0)이 된다.

```
큰 텍스트 메시지를 3개 프레임으로 분할한 예:

프레임 1: FIN=0, opcode=0x1 (text), payload="안녕하"
프레임 2: FIN=0, opcode=0x0 (continuation), payload="세요. 이"
프레임 3: FIN=1, opcode=0x0 (continuation), payload="것은 분할된 메시지입니다"

수신측은 세 프레임을 합쳐 단일 텍스트 메시지로 처리한다.
```

분할은 두 가지 상황에서 유용하다. 하나는 송신 시점에 전체 길이를 모르는 스트리밍 데이터(예: 압축 중인 데이터, 변환 중인 미디어 청크)를 보낼 때다. 또 하나는 한 번에 너무 큰 페이로드를 들고 있지 않으려 할 때다.

다만 실무에서 직접 분할 프레임을 만들 일은 거의 없다. 대부분의 라이브러리는 큰 메시지를 자동 분할하거나, 반대로 자동 결합해서 한 메시지처럼 콜백을 호출한다. 직접 다뤄야 하는 경우는 보통 프록시나 게이트웨이를 자체 구현할 때다.

분할 프레임 처리에서 주의할 함정이 하나 있다. continuation 프레임 사이에 컨트롤 프레임(ping/pong/close)이 끼어들 수 있다. 즉 텍스트 메시지의 첫 프레임을 받은 뒤 ping이 도착하고, 그 다음 continuation이 도착하는 흐름이 표준상 합법이다. 자체 파싱 로직이 단순히 "첫 프레임 받으면 같은 opcode가 끝까지 이어진다"고 가정하면 깨진다.

## Control Frame 제약

opcode 0x8(close), 0x9(ping), 0xA(pong)는 컨트롤 프레임이다. 데이터 프레임과는 다른 제약이 있다.

첫째, 페이로드 길이가 125바이트 이하여야 한다. Extended length 필드를 쓸 수 없다. 즉 ping/pong 페이로드에 큰 데이터를 실으면 안 된다. 직접 구현 시 이 한도를 넘으면 받는 쪽은 1002로 종료한다.

둘째, 분할이 불가능하다. FIN 비트가 항상 1이어야 한다. 컨트롤 프레임은 데이터 프레임 사이에 끼어들 수 있지만 그 자체로 쪼개지지 않는다.

셋째, 애플리케이션 메시지가 아니라 프로토콜 제어용이다. 애플리케이션 콜백(onmessage 등)으로 노출되지 않는다.

이 제약 덕분에 ping/pong은 어떤 상황에서도 작은 페이로드로 빠르게 처리된다. 데이터 프레임이 한창 흘러가는 중간에도 컨트롤 프레임을 끼워 넣어 keepalive를 유지할 수 있다.

```
타임라인:
  ──Text frame 1 (FIN=0)──
  ──Ping frame──
  ──Pong frame (응답)──
  ──Text continuation (FIN=0)──
  ──Text continuation (FIN=1)──
```

ping을 보낸 뒤 정해진 시간 내에 pong이 안 오면 죽은 연결로 간주하고 끊는 것이 일반적이다. Spring의 WebSocket 컨테이너는 이를 자동 처리하지만 타임아웃 값은 직접 설정해야 한다. 보통 25~30초 간격으로 ping을 보내고, 두 번 연속 응답 없으면 끊는다.

## Close Frame 코드 전수 정리

연결 종료 시 close 프레임(opcode 0x8)에 2바이트 상태 코드를 실어 보낸다. RFC 6455가 1000~4999 범위에서 의미를 정의하고, 4000~4999는 애플리케이션이 자유롭게 사용할 수 있다.

| 코드 | 의미 | 발생 시점 |
|------|------|----------|
| 1000 | Normal Closure | 정상 종료. 양쪽이 합의해서 끝낼 때 |
| 1001 | Going Away | 서버 셧다운, 브라우저 페이지 이동 |
| 1002 | Protocol Error | 잘못된 프레임 수신 (MASK 비트 누락, 알 수 없는 opcode 등) |
| 1003 | Unsupported Data | text 채널로 binary가 왔거나 그 반대 |
| 1004 | (예약, 사용 안 함) | RFC가 의미를 부여하지 않음 |
| 1005 | No Status Received | 코드가 실제로 와이어에 실리지 않았음을 표시하는 가상 코드 |
| 1006 | Abnormal Closure | TCP가 정상 close 프레임 없이 끊어짐. 와이어에 실리지 않음 |
| 1007 | Invalid frame payload data | UTF-8이 깨진 텍스트 등 |
| 1008 | Policy Violation | 정책 위반. 구체적 코드가 없을 때 일반적으로 사용 |
| 1009 | Message Too Big | 수신측 한도 초과 |
| 1010 | Mandatory Extension | 클라이언트가 요구한 확장이 거절됨 |
| 1011 | Internal Error | 서버 내부 에러 |
| 1012 | Service Restart | 재시작 중. RFC 7405 |
| 1013 | Try Again Later | 일시적 과부하 |
| 1014 | Bad Gateway | 게이트웨이 뒤단의 문제 |
| 1015 | TLS Handshake | TLS 실패. 와이어에 실리지 않음 |

1005, 1006, 1015는 "가상" 코드다. 실제로 close 프레임에 담겨 전송되지 않는다. 클라이언트 라이브러리가 onclose 콜백에 전달할 때 사용하는 표시값이다. 1006은 close 프레임 없이 TCP가 RST되거나 타임아웃됐을 때, 1015는 TLS 핸드셰이크 자체가 실패했을 때 붙는다.

### 1006 트러블슈팅

운영에서 가장 자주 보는 코드는 1006이다. 정상 종료가 아니라 TCP 레이어에서 끊긴 모든 케이스가 여기로 묶인다. 추적하기 까다로운 이유는 close 프레임이 없으니 reason 문자열도 비어 있고, 어디서 왜 끊겼는지 단서가 부족해서다.

자주 만나는 원인은 다음과 같다.

중간 프록시의 idle timeout이 가장 흔하다. AWS ALB는 기본 60초, Cloudflare는 100초, 사내 Nginx는 종종 60초로 설정되어 있다. 사용자가 트래픽 없이 가만히 있으면 프록시가 일방적으로 TCP를 끊는다. 양쪽 끝의 애플리케이션은 close 프레임을 받지 못하므로 1006으로 처리한다. 해결책은 ping/pong을 idle timeout보다 짧은 주기로 보내서 트래픽을 유지하는 것이다.

다음으로 흔한 건 모바일 네트워크의 NAT rebinding이다. 이동 중인 단말은 LTE 셀이 바뀌면서 외부 IP/포트가 바뀌고, 기존 TCP 연결이 통신 불가 상태가 된다. 클라이언트는 한참 후에 keepalive 실패로 1006을 받는다. 이 경우는 자동 재연결로 대응할 수밖에 없다.

서버 OOM, 컨테이너 재배포, 호스트 네트워크 일시 단절도 1006으로 나타난다. 서버측 로그와 시간대를 맞춰 확인해야 구분된다. 단순히 "1006이 늘었다"만으로는 원인 파악이 안 되고, 클라이언트와 서버 양측의 메트릭을 같이 봐야 한다.

### 애플리케이션 코드 (4000~4999)

업무 로직 종료 사유는 4000~4999 범위에서 임의로 정의해서 쓴다.

```javascript
const APP_CLOSE_CODES = {
    AUTH_EXPIRED: 4001,        // 토큰 만료
    KICKED_BY_ADMIN: 4002,     // 관리자 강퇴
    ROOM_DELETED: 4003,        // 방 삭제
    DUPLICATE_LOGIN: 4004,     // 다른 기기에서 로그인
};

ws.close(APP_CLOSE_CODES.AUTH_EXPIRED, '토큰이 만료되었습니다');
```

클라이언트는 코드를 보고 재연결할지, 로그인 화면으로 보낼지, 영구히 포기할지 결정한다. 1000번대 코드만으로는 이런 분기를 만들 수 없다.

## permessage-deflate 확장

RFC 7692가 정의한 메시지 단위 압축 확장이다. 핸드셰이크에서 협상한다.

```
클라이언트:
  Sec-WebSocket-Extensions: permessage-deflate;
    client_max_window_bits=15;
    client_no_context_takeover

서버:
  Sec-WebSocket-Extensions: permessage-deflate;
    server_no_context_takeover
```

압축은 프레임 단위가 아니라 메시지 단위로 적용된다. 압축된 메시지는 첫 프레임의 RSV1 비트가 1로 표시된다. 페이로드는 deflate(RFC 1951) 알고리즘으로 압축된 바이트열이다.

JSON 같은 텍스트 메시지는 압축률이 70~90%에 달한다. 채팅 메시지처럼 작고 빈번한 데이터에서도 누적 효과가 크다. 다만 모든 경우에 좋은 건 아니다.

### Context Takeover

deflate 알고리즘은 이전 메시지에서 본 패턴을 사전(window)으로 활용해 다음 메시지를 더 잘 압축한다. 이를 context takeover라 부른다. 같은 포맷의 JSON이 반복되는 채팅에서 압축률이 극대화된다.

문제는 이 사전이 메모리를 점유한다는 점이다. window_bits=15면 연결당 32KB의 deflate 컨텍스트가 양방향(송수신)으로 잡힌다. 즉 연결 하나당 64KB가 추가로 든다. 동시 접속이 10만이면 6.4GB다.

```
client_no_context_takeover:
  → 클라이언트는 메시지마다 사전을 리셋. 메모리 절약, 압축률 하락

server_no_context_takeover:
  → 서버측이 매번 사전 리셋. 같은 효과

client_max_window_bits=10:
  → 사전 크기를 1KB로 축소. 압축률 절충
```

대규모 서버에서는 보통 `server_no_context_takeover`를 협상한다. 메모리 폭증을 막고 GC 압력도 줄어든다. 트래픽이 많지 않은 서비스라면 기본값이 낫다.

### 압축이 손해인 경우

이미 압축된 데이터(이미지, 비디오, gzip 응답)는 두 번 압축해도 줄지 않고 CPU만 쓴다. binary 메시지를 다루는 채널은 압축을 끄는 편이 낫다.

암호화된 페이로드도 마찬가지다. 무작위 비트열이라 deflate가 줄일 게 없다. 일부 라이브러리는 페이로드 크기 임계값(예: 256바이트 이하 미압축)을 둬서 작은 메시지를 그냥 보낸다.

CRIME/BREACH 계열 사이드 채널 공격이 WebSocket에도 변형 형태로 적용 가능한지에 대한 논의가 있다. 평문에 사용자 입력과 비밀 토큰이 섞여 있고 공격자가 입력을 조작할 수 있는 상황이라면 압축률 변화로 토큰 추측이 이론적으로 가능하다. 일반적인 채팅에서는 노출되지 않지만, 인증 토큰을 메시지 본문에 매번 실어 보내는 설계는 피해야 한다.

## Backpressure 처리

WebSocket은 양방향이지만, 송신측이 수신측보다 빠르면 송신 큐가 무한정 쌓인다. 브라우저에서는 `WebSocket.bufferedAmount`로 송신 대기 중인 바이트 수를 확인할 수 있다.

```javascript
function safeSend(ws, data) {
    const HIGH_WATER_MARK = 1024 * 1024;  // 1MB
    if (ws.bufferedAmount > HIGH_WATER_MARK) {
        // 큐 폭주. 메시지 드롭하거나 송신 일시 중단
        return false;
    }
    ws.send(data);
    return true;
}
```

bufferedAmount가 계속 늘어난다는 건 네트워크가 페이로드를 받아내지 못하고 있다는 뜻이다. 이를 무시하고 계속 send()를 호출하면 메모리만 먹다가 결국 탭이 죽거나 OOM으로 서버가 내려간다.

서버측도 마찬가지다. Node.js의 `ws` 라이브러리는 내부 버퍼가 차면 `socket.send()`가 콜백을 늦게 호출하거나 false를 리턴한다. Java/Spring의 `WebSocketSession.sendMessage()`는 동기 메서드라 한 세션의 송신이 느리면 호출 스레드가 블록된다. NIO 기반 비동기 채널을 쓰더라도 송신 큐 한도를 명시적으로 설정해야 한다.

```java
// Spring WebSocket 송신 큐 한도
@Override
public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
    registry.addHandler(handler(), "/ws")
            .addHandshakeInterceptor(new HttpSessionHandshakeInterceptor());
}

@Bean
public ServletServerContainerFactoryBean createWebSocketContainer() {
    ServletServerContainerFactoryBean container = new ServletServerContainerFactoryBean();
    container.setMaxBinaryMessageBufferSize(64 * 1024);
    container.setMaxTextMessageBufferSize(64 * 1024);
    container.setAsyncSendTimeout(5000L);  // 5초 내 송신 못하면 끊음
    return container;
}
```

브로드캐스트 시나리오에서 backpressure가 특히 위험하다. 한 명의 느린 수신자가 서버 송신 스레드를 점유하면, 그 방의 다른 사용자들도 전부 느려진다. 송신은 반드시 비동기로 처리하고, 일정 시간 못 보내는 세션은 강제 종료해야 한다.

## HTTP/2 위 WebSocket (RFC 8441)

전통적인 WebSocket은 HTTP/1.1 위에서만 동작한다. HTTP/2는 멀티플렉싱과 프레임 구조가 달라서 그대로 업그레이드할 수 없었다. RFC 8441이 이 간극을 메우기 위해 `:protocol` 의사 헤더를 도입했다.

```
HTTP/2 CONNECT 요청 (RFC 8441):
  :method     = CONNECT
  :scheme     = https
  :path       = /chat
  :authority  = server.example.com
  :protocol   = websocket          ← RFC 8441이 신설한 의사 헤더
  sec-websocket-version = 13
  sec-websocket-protocol = chat
  origin = https://app.example.com
```

서버가 200 응답을 돌려보내면, 그 스트림은 더 이상 HTTP/2 메시지가 아니라 WebSocket 프레임 채널이 된다. 한 TCP/TLS 연결 위에서 일반 HTTP/2 요청들과 WebSocket 스트림이 공존한다.

장점은 명확하다. 같은 도메인의 HTTP/2 트래픽과 연결 풀을 공유하므로 추가 TCP/TLS 핸드셰이크가 없다. 모바일에서 첫 연결 지연이 줄어든다. 또 WebSocket 한 채널이 HTTP/2의 우선순위 제어와 흐름 제어 메커니즘 안에 들어온다.

단점도 있다. HTTP/2는 한 TCP 연결의 head-of-line blocking에 취약하다. 한 패킷이 손실되면 그 위의 모든 스트림이 멈춘다. WebSocket이 HTTP/2 위에 올라타면 같은 약점을 공유한다. HTTP/3(QUIC) 위에서는 이 문제가 해소된다(RFC 9220이 HTTP/3 위 WebSocket을 정의).

브라우저 지원은 갖춰져 있지만, 중간 프록시 호환성이 여전히 발목을 잡는다. ALB는 2024년 기준으로 RFC 8441을 지원하지 않고, 일부 사내 게이트웨이도 마찬가지다. 클라이언트가 HTTP/2 위 WebSocket을 시도했다가 실패하면 자동으로 HTTP/1.1로 폴백하는 경로를 둬야 한다.

## JavaScript 클라이언트

```javascript
const ws = new WebSocket('wss://server.example.com/chat');

ws.onopen = (event) => {
    ws.send(JSON.stringify({ type: 'join', room: 'general' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};

ws.onerror = (error) => {
    console.error('WebSocket error', error);
};

ws.onclose = (event) => {
    console.log(`closed: code=${event.code}, reason=${event.reason}, wasClean=${event.wasClean}`);
    if (event.code !== 1000 && event.code !== 1001) {
        scheduleReconnect();
    }
};

ws.send('Hello');
ws.send(new Uint8Array([1, 2, 3, 4]).buffer);
ws.close(1000, 'Normal closure');
```

`onerror`에는 의미 있는 정보가 거의 안 담긴다. 보안상 브라우저가 상세 에러를 노출하지 않기 때문이다. 실제 원인은 onclose의 code로 판단해야 한다.

### 재연결 패턴

```javascript
class ResilientWebSocket {
    constructor(url) {
        this.url = url;
        this.reconnectDelay = 1000;
        this.maxDelay = 30000;
        this.shouldReconnect = true;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            this.reconnectDelay = 1000;
        };

        this.ws.onclose = (event) => {
            // 4001~4999 중 일부는 재연결 금지로 약속
            if (event.code === 4001 || !this.shouldReconnect) return;

            const jitter = Math.random() * 500;
            setTimeout(() => this.connect(), this.reconnectDelay + jitter);
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
        };

        this.ws.onmessage = (event) => this.handleMessage(JSON.parse(event.data));
    }

    send(data) {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            // 큐에 쌓아두고 onopen에서 flush 하는 패턴도 흔함
        }
    }

    handleMessage(data) { /* override */ }
}
```

지수 백오프에 jitter를 더하지 않으면 큰 사고가 난다. 서버 장애로 모든 클라이언트가 동시에 끊기고, 같은 백오프 일정으로 일제히 재연결을 시도하면 복구된 서버를 다시 죽인다. 0~500ms 범위의 랜덤 지터만 더해도 충돌이 많이 분산된다.

## Spring WebSocket (서버)

### 기본 WebSocket

```java
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(chatHandler(), "/ws/chat")
                .setAllowedOrigins("https://example.com")
                .addInterceptors(new HttpSessionHandshakeInterceptor());
    }

    @Bean
    public WebSocketHandler chatHandler() {
        return new ChatWebSocketHandler();
    }
}

public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final Set<WebSocketSession> sessions = ConcurrentHashMap.newKeySet();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.add(session);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        for (WebSocketSession s : sessions) {
            if (s.isOpen()) {
                synchronized (s) {  // sendMessage는 동시 호출 금지
                    s.sendMessage(new TextMessage("Echo: " + message.getPayload()));
                }
            }
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
    }
}
```

`WebSocketSession.sendMessage()`는 동시 호출이 금지되어 있다. 한 세션을 여러 스레드에서 동시에 send 하면 프레임이 깨진다. 위 예제처럼 세션 객체를 락으로 잡거나, `ConcurrentWebSocketSessionDecorator`로 감싸 직렬화해야 한다.

### STOMP (Simple Text Oriented Messaging Protocol)

WebSocket 위에서 동작하는 메시지 브로커 프로토콜이다. pub/sub 패턴을 표준화해서 채팅, 알림, 공동 편집 같은 케이스를 빠르게 구현할 수 있다.

```java
@Configuration
@EnableWebSocketMessageBroker
public class StompConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        config.enableSimpleBroker("/topic", "/queue");
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOrigins("https://example.com")
                .withSockJS();
    }
}

@Controller
public class ChatController {

    @MessageMapping("/chat.send")
    @SendTo("/topic/chat")
    public ChatMessage sendMessage(ChatMessage message) {
        return message;
    }

    @MessageMapping("/chat.private")
    public void privateMessage(ChatMessage message,
                               SimpMessagingTemplate messagingTemplate) {
        messagingTemplate.convertAndSendToUser(
            message.getTo(), "/queue/private", message
        );
    }
}
```

```
STOMP 메시지 흐름:

Client A ──/app/chat.send──▶ Server ──/topic/chat──▶ Client A, B, C (구독자)

Client A ──/app/chat.private──▶ Server ──/queue/private──▶ Client B (특정 유저)
```

`enableSimpleBroker`는 인메모리 브로커라 단일 인스턴스에서만 동작한다. 다중 서버에서는 `enableStompBrokerRelay`로 외부 브로커(RabbitMQ, ActiveMQ)를 연결한다.

## Socket.IO (Node.js)

WebSocket 위에 자동 폴백, 룸/네임스페이스, 인증 핸드셰이크를 얹은 라이브러리다. 순수 WebSocket과 와이어 호환되지 않는 별개 프로토콜이라는 점을 헷갈리지 말아야 한다. Socket.IO 서버는 일반 WebSocket 클라이언트의 연결을 받지 못한다.

```javascript
// 서버
const { Server } = require('socket.io');
const io = new Server(server, {
    cors: { origin: 'https://example.com' }
});

io.on('connection', (socket) => {
    socket.on('join-room', (roomId) => {
        socket.join(roomId);
        socket.to(roomId).emit('user-joined', socket.id);
    });

    socket.on('chat-message', (data) => {
        io.to(data.roomId).emit('new-message', {
            from: socket.id,
            text: data.text,
            timestamp: Date.now()
        });
    });

    socket.on('disconnect', (reason) => {
        // reason: "transport close", "ping timeout", "client namespace disconnect" 등
    });
});

const admin = io.of('/admin');
admin.on('connection', (socket) => {
    // 관리자 네임스페이스 전용 로직
});
```

```javascript
// 클라이언트
import { io } from 'socket.io-client';

const socket = io('https://server.example.com', {
    auth: { token: 'jwt-token' },
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
});

socket.emit('join-room', 'room-1');
socket.on('new-message', (data) => {
    console.log(`${data.from}: ${data.text}`);
});
```

Socket.IO의 폴백 동작이 양날의 검이다. WebSocket이 막힌 환경에서는 long polling으로 자동 전환되어 동작은 하지만, 폴링은 양방향성이 가짜로 흉내낸 것이라 지연이 크다. 운영에서는 `transports: ['websocket']`로 폴링을 명시적으로 끄고, WebSocket 실패는 에러로 다루는 편이 디버깅하기 낫다.

다중 서버에서는 `@socket.io/redis-adapter`를 붙여 Redis pub/sub으로 메시지를 동기화한다. Spring STOMP의 broker relay와 같은 개념이다.

## SSE (Server-Sent Events) 비교

서버에서 클라이언트로의 단방향 스트리밍 프로토콜이다. WebSocket보다 단순하고, HTTP 위에서 동작하므로 인프라 호환성이 좋다.

```java
@GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<String>> stream() {
    return Flux.interval(Duration.ofSeconds(1))
        .map(seq -> ServerSentEvent.<String>builder()
            .id(String.valueOf(seq))
            .event("price-update")
            .data("{\"price\": " + getPrice() + "}")
            .build());
}
```

```javascript
const eventSource = new EventSource('/stream');
eventSource.addEventListener('price-update', (event) => {
    const data = JSON.parse(event.data);
    updatePrice(data.price);
});
eventSource.onerror = () => {
    // 브라우저가 자동 재연결
};
```

| 비교 | WebSocket | SSE |
|------|-----------|-----|
| 방향 | 양방향 | 서버→클라이언트 |
| 프로토콜 | ws:// / wss:// | HTTP |
| 바이너리 | 가능 | 텍스트만 (Base64로 우회) |
| 자동 재연결 | 직접 구현 | 브라우저 기본 제공 |
| 마지막 수신 ID 추적 | 직접 구현 | Last-Event-ID 헤더 자동 |
| HTTP/2 호환 | RFC 8441 필요 | 멀티플렉싱 가능 |
| 프록시/방화벽 | 문제 가능 | HTTP라 통과 용이 |
| 적합한 경우 | 채팅, 게임, 양방향 | 주식 시세, 알림, 로그 |

서버→클라이언트 단방향이면 거의 항상 SSE가 낫다. 재연결과 메시지 ID 복구가 표준 동작이라 구현 부담이 없고, HTTP/2 위에서 한 연결로 여러 SSE 스트림이 멀티플렉싱된다.

## 다중 서버 확장

WebSocket은 stateful한 연결이라 라운드 로빈으로 메시지를 흩뿌릴 수 없다. 같은 방의 사용자 A, B가 다른 서버에 접속해 있으면 A의 메시지를 B에게 전달할 경로가 필요하다.

```
                    ┌──────────┐
Client A ───────── │ Server 1 │
                    │  (WS)    │──┐
                    └──────────┘  │
                                  ├── Redis Pub/Sub ─── 메시지 동기화
                    ┌──────────┐  │
Client B ───────── │ Server 2 │──┘
                    │  (WS)    │
                    └──────────┘

→ Client A가 보낸 메시지를 Server 2의 Client B도 수신
```

```java
// Spring + 외부 STOMP 브로커
@Configuration
@EnableWebSocketMessageBroker
public class StompConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        config.enableStompBrokerRelay("/topic", "/queue")
              .setRelayHost("rabbitmq-host")
              .setRelayPort(61613);
        config.setApplicationDestinationPrefixes("/app");
    }
}
```

브로커 선택은 트래픽 패턴에 따른다. 메시지 보존이 필요 없는 채팅이면 Redis pub/sub이 가벼우면서 빠르다. 메시지 유실이 곤란한 알림이면 RabbitMQ나 Kafka를 두고 ack 기반으로 처리한다.

## 프록시/LB 트러블슈팅

WebSocket 운영에서 가장 골치 아픈 영역이다. 정상 코드, 정상 트래픽인데도 연결이 자꾸 끊긴다면 십중팔구 중간 인프라 문제다.

### Sticky Session

WebSocket은 첫 핸드셰이크에서 정해진 서버와 평생 통신한다. 라운드 로빈 LB는 핸드셰이크 자체는 한 서버로 보내고 끝이라 문제가 없어 보이지만, 인증 컨텍스트나 세션 데이터가 서버 메모리에 있다면 문제가 된다.

대표적으로 Socket.IO는 long polling 폴백을 쓸 때 같은 클라이언트의 여러 HTTP 요청이 같은 서버로 가야 한다. sticky session 없이 쓰면 폴링 핸드셰이크가 서버 A에서 시작됐는데 후속 요청이 서버 B로 가서 "session not found"로 실패한다. ALB의 stickiness, Nginx의 `ip_hash`, Cloudflare의 session affinity 같은 설정으로 고정해야 한다.

### ALB Idle Timeout

AWS Application Load Balancer는 기본 idle timeout이 60초다. 60초 동안 트래픽이 없으면 LB가 일방적으로 TCP를 끊는다. WebSocket 연결은 사용자 입력이 뜸해질 수 있으므로 거의 항상 ping/pong 없이는 살아남지 못한다.

해결 순서는 두 가지다. ALB의 idle timeout을 늘릴 수 있다(최대 4000초). 또는 ping을 30초 정도 간격으로 보내 트래픽을 유지한다. 후자가 일반적이다. ALB 설정을 늘려도 NLB나 Cloudflare 등 다른 장비가 그 앞에 있으면 거기서 끊긴다.

ALB는 WebSocket 자체는 잘 지원하지만 RFC 8441(HTTP/2 위 WebSocket)은 지원하지 않는다. 클라이언트가 HTTP/2 멀티플렉싱을 기대하고 보낸 CONNECT는 거절된다.

### Cloudflare 100초 제한

Cloudflare 무료 플랜은 WebSocket idle timeout이 100초다. 유료 플랜에서도 절대 무한대는 아니다. ping 간격을 80초 이내로 두는 게 안전하다.

또 Cloudflare는 worker가 실행되는 환경이라 일부 헤더가 변형되거나 추가된다. 클라이언트의 실제 IP는 `CF-Connecting-IP` 헤더에서 읽어야 하고, `X-Forwarded-For`는 신뢰하면 안 된다.

### Nginx proxy_read_timeout

Nginx 기본 `proxy_read_timeout`은 60초다. 백엔드(WebSocket 서버)에서 60초간 데이터가 안 오면 Nginx가 연결을 끊는다. 핵심 설정은 다음과 같다.

```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    proxy_read_timeout  3600s;
    proxy_send_timeout  3600s;
    proxy_connect_timeout 60s;

    proxy_buffering off;  # 실시간성 유지
}
```

`proxy_buffering off`를 빼먹으면 서버가 보낸 작은 메시지를 Nginx가 버퍼에 쌓아두고 한꺼번에 보낸다. 채팅이 뚝뚝 끊겨 도착하는 현상이 생긴다.

`proxy_set_header Upgrade`와 `proxy_set_header Connection "upgrade"` 두 줄이 빠지면 핸드셰이크 자체가 실패한다. Nginx가 HTTP 헤더를 백엔드로 그대로 전달하지 않기 때문이다.

## 메모리 누수 패턴

### 닫힌 세션 미제거

가장 흔한 누수다. 브로드캐스트를 위해 세션을 Set에 담아 두는데, `afterConnectionClosed`에서 제거를 빼먹으면 닫힌 세션이 누적된다. 송신 시 `isOpen()`만 체크하고 컬렉션에서는 안 빼면, 시간이 갈수록 컬렉션 순회 비용이 폭발하고 GC 부담이 늘어난다.

```java
@Override
public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
    sessions.remove(session);  // 반드시
    rooms.values().forEach(room -> room.remove(session));  // 룸에서도 제거
}
```

세션을 사용자 ID로 키 잡은 Map에 넣었다면, 같은 사용자가 재접속할 때 옛 세션을 명시적으로 close 하고 교체해야 한다. 둘 다 살려두면 한 사용자에게 메시지가 두 번 갈 뿐만 아니라 닫힌 세션이 누적된다.

### 재연결 폭주

서버가 잠깐 흔들렸다가 복구되는 순간이 가장 위험하다. 모든 클라이언트가 동시에 재연결을 시도하면 서버가 다시 쓰러진다. 클라이언트의 재연결 로직에 jitter가 빠지면 일제히 같은 시점에 몰린다.

```javascript
// 잘못된 패턴
setTimeout(() => connect(), reconnectDelay);

// jitter 추가
const jitter = Math.random() * reconnectDelay;
setTimeout(() => connect(), reconnectDelay + jitter);
```

서버측에서도 connection rate limit을 둬야 한다. IP당, 사용자당 초당 신규 연결 수를 제한하면 폭주가 일정 수준에서 멈춘다. 무제한으로 받으면 ulimit가 터지거나 OOM이 난다.

### 큐에 쌓인 메시지

연결이 끊긴 사용자에게 보낼 메시지를 메모리 큐에 쌓아두는 설계가 종종 누수 원인이다. 사용자가 한참 안 돌아오는 동안 큐가 무한히 자라면 OOM이 난다. 큐 크기 한도, TTL, 디스크/Redis 오프로딩 중 하나는 반드시 둬야 한다.

## 성능 튜닝

### TCP_NODELAY

TCP는 기본적으로 작은 패킷을 모아 보내는 Nagle 알고리즘을 켜둔다. 송신 버퍼에 작은 데이터가 들어오면 ACK를 기다렸다가 다음 데이터와 합쳐 보낸다. 효율은 좋지만 실시간성을 해친다.

WebSocket은 작고 빈번한 메시지가 특징이라 Nagle를 끄는 편이 낫다. 서버 측에서 소켓 옵션으로 `TCP_NODELAY`를 활성화한다. 대부분의 WebSocket 라이브러리는 기본으로 켜두지만 자체 구현 시 빼먹기 쉽다.

```java
// Netty 기반 서버
serverBootstrap.childOption(ChannelOption.TCP_NODELAY, true);
```

### ulimit 파일 디스크립터

리눅스에서 한 프로세스가 열 수 있는 파일 디스크립터(소켓 포함) 수는 기본 1024다. WebSocket 서버는 연결 하나당 소켓 하나를 쓰므로, 동시 1만 명만 받아도 한도를 초과한다. `Too many open files` 에러로 신규 연결이 거부되기 시작한다.

```bash
# 현재 한도 확인
ulimit -n

# 시스템 전역 설정
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# systemd 서비스
[Service]
LimitNOFILE=65536
```

컨테이너 환경에서는 호스트 ulimit과 별개로 컨테이너의 한도가 적용된다. Kubernetes pod의 `securityContext`나 Docker의 `--ulimit nofile=65536:65536`로 명시해야 한다.

소켓 외에도 epoll 인스턴스, 로그 파일 등이 디스크립터를 잡으므로, 동시 연결 수 N에 대해 적어도 1.2N 정도의 여유가 필요하다.

### epoll/kqueue 기반 서버

WebSocket 서버는 동시 연결 수가 핵심이다. 연결당 스레드 모델은 1만 연결만 돼도 컨텍스트 스위칭으로 무너진다. 이벤트 기반 I/O 멀티플렉싱이 표준이다.

리눅스에서는 epoll, BSD/macOS에서는 kqueue가 기본 메커니즘이다. Node.js, Netty, Vert.x, Tokio 같은 런타임이 내부적으로 이를 사용한다. select/poll은 연결 수가 늘어나면 O(N) 스캔 비용이 들어 1만 연결을 넘기면 답이 없다. epoll/kqueue는 변경된 이벤트만 보고하므로 연결 수와 무관하게 일정한 비용을 유지한다.

자바 진영에서는 NIO보다 Netty의 `EpollEventLoopGroup`을 명시적으로 쓰는 편이 성능이 더 잘 나온다. NIO 기본 구현은 selector를 사용하지만, Netty의 native 라이브러리는 epoll을 직접 호출해 시스템 콜 수를 줄인다.

### 커널 파라미터

10만 단위 동시 연결을 다루려면 기본 커널 파라미터 몇 개를 조정해야 한다.

```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535             # listen backlog
net.ipv4.tcp_max_syn_backlog = 65535   # SYN 큐 크기
net.ipv4.ip_local_port_range = 1024 65535  # 클라이언트 포트 범위
net.ipv4.tcp_tw_reuse = 1              # TIME_WAIT 소켓 재사용
net.core.rmem_max = 16777216           # 소켓 수신 버퍼 최대
net.core.wmem_max = 16777216           # 소켓 송신 버퍼 최대
```

이 값들은 정답이 없고 워크로드에 따라 달라진다. 모니터링하면서 병목이 되는 지점만 손대야 한다. 무작정 올리면 메모리 사용량만 늘어난다.

## 보안

WebSocket은 양방향이라 HTTP보다 보안 표면이 넓다. 핸드셰이크 시점만 인증하고 끝내면 토큰 만료 후에도 연결이 살아 있어 권한 우회가 가능하다.

`wss://`(TLS)는 프로덕션에서 선택이 아니다. 평문 ws://는 ISP, 카페 와이파이 등 모든 중간자가 메시지를 읽고 변조할 수 있다. TLS 종단을 LB에서 처리하더라도 LB와 백엔드 사이 트래픽도 암호화하는 것이 안전하다.

Origin 검증은 핸드셰이크에서 반드시 한다. CORS와 달리 WebSocket은 브라우저가 same-origin policy를 적용하지 않으므로, 서버가 직접 `Origin` 헤더를 화이트리스트와 대조해야 한다. 빠뜨리면 임의의 도메인에서 사용자의 인증 쿠키로 연결을 열 수 있다(CSWSH, Cross-Site WebSocket Hijacking).

JWT 토큰 인증을 쓴다면 만료 시점에 서버가 강제로 연결을 끊는 로직이 필요하다. 핸드셰이크 시점의 토큰이 영원히 유효하다고 가정하면 1년 묵은 토큰으로도 메시지를 보낼 수 있다. 보통 토큰 만료 1분 전쯤 클라이언트가 새 토큰으로 재인증하거나, 서버가 4001 close code로 끊고 클라이언트가 재연결하도록 만든다.

수신 메시지 크기 제한은 OOM 방지의 기본이다. 라이브러리 기본값(보통 64KB~1MB)을 그대로 두지 말고, 서비스에서 다루는 최대 메시지 크기에 맞춰 명시적으로 설정한다. 한도 초과 시 1009로 끊는다.

JSON 파싱은 입력 검증의 첫 관문이다. 깊이 무제한 중첩, 거대한 배열, 키 충돌 같은 페이로드는 파서를 죽이거나 메모리를 먹는다. depth limit을 가진 파서를 쓰거나, 파싱 후 비즈니스 검증을 거친다. XSS는 클라이언트가 받은 메시지를 DOM에 그대로 꽂을 때 일어나므로, 메시지 본문에 사용자 입력이 들어간다면 출력 시점에서 이스케이프한다.

## 참고

- [RFC 6455 — WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [RFC 7692 — Compression Extensions for WebSocket](https://tools.ietf.org/html/rfc7692)
- [RFC 8441 — Bootstrapping WebSockets with HTTP/2](https://tools.ietf.org/html/rfc8441)
- [RFC 9220 — Bootstrapping WebSockets with HTTP/3](https://tools.ietf.org/html/rfc9220)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Socket.IO Documentation](https://socket.io/docs/v4/)
- [STOMP over WebSocket](https://stomp.github.io/stomp-specification-1.2.html)
- [네트워크 프로토콜](Protocol.md) — HTTP, TCP, UDP 개요
- [Nginx 리버스 프록시](../../WebServer/Nginx/Reverse_Proxy_and_Load_Balancing.md) — WebSocket 프록시 설정
