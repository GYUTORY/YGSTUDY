---
title: SFU 미디어 서버
tags: [network]
updated: 2026-07-25
---

# SFU 미디어 서버

## P2P 풀메시의 한계

1:1 WebRTC는 잘 된다. 문제는 3명부터다.

N명이 서로 직접 연결하는 풀메시(full-mesh)에서는 각 단말이 N-1개의 PeerConnection을 유지하고, 자신의 영상을 N-1개의 스트림으로 각각 인코딩해서 보내야 한다. 연결 수는 N*(N-1)/2개가 된다.

```
4명 풀메시:
  - 각자 PeerConnection 3개
  - 각자 영상 3번 인코딩해서 업로드
  - 총 연결 6개

  A ──── B
  │ \  / │
  │  \/  │
  │  /\  │
  │ /  \ │
  C ──── D
```

4명이면 어떻게든 버티는 경우가 있지만, 6명을 넘어가면 노트북 팬이 돌기 시작한다. 같은 영상을 5번 인코딩하는 게 CPU를 잡아먹고, 업로드 대역폭도 5배로 필요하다. 5명에게 720p 30fps를 보내면 업로드 약 10Mbps다. 일반 가정용 인터넷에서 안정적으로 유지하기 어렵다.

NAT 문제도 곱해진다. 풀메시에서는 참가자 쌍마다 ICE를 돌린다. N=10이면 45개 연결에 대해 각각 STUN/TURN이 필요하고, 그 중 대칭형 NAT 뒤에 있는 조합은 전부 TURN 릴레이로 떨어진다. 참가자가 늘수록 TURN 트래픽이 N² 스케일로 증가한다.

이 문제를 해결하는 방법이 미디어 서버를 두는 것이다.

---

## SFU와 MCU

### SFU (Selective Forwarding Unit)

각 단말은 서버 하나와만 연결한다. 자신의 영상을 서버에 업로드하면, 서버는 그 스트림을 받아서 다른 참가자들에게 그대로 전달(forwarding)한다. 서버가 영상을 디코딩하거나 재인코딩하지 않고 RTP 패킷을 그대로 포워딩하기 때문에 서버 CPU 부담이 낮다.

```
SFU 구조:

  A ──── SFU ──── B
              └── C
              └── D

  - 각자 서버와 PeerConnection 1개
  - 업로드 1번 (자신의 영상을 서버에만)
  - 다운로드 N-1개 (다른 사람들 영상)
  - 서버는 RTP 포워딩만, 인코딩 없음
```

클라이언트 입장에서는 업로드 부담이 사라진다. 자신의 영상은 서버에 한 번만 보내면 된다. 대신 다운로드는 N-1개 스트림을 받아야 하므로 참가자 수에 비례해서 다운로드 대역폭이 늘어난다. 10명짜리 방이면 9개 스트림을 동시에 받는다.

SFU의 "Selective"는 서버가 상황에 따라 어떤 품질의 스트림을 누구에게 보낼지 고를 수 있다는 뜻이다. A가 720p와 360p 두 품질로 올리면, 대역폭이 나쁜 D에게는 360p만 포워딩하는 식이다. 이게 뒤에서 설명하는 시뮬캐스트(simulcast)와 연결된다.

### MCU (Multipoint Control Unit)

MCU는 모든 참가자의 영상을 서버에서 디코딩하고 합성해서 하나의 스트림으로 재인코딩해서 보낸다. 각 단말은 서버에서 받은 합성 영상 하나만 보면 된다.

```
MCU 구조:

  A ──┐
  B ──┤ MCU ──── A (합성 영상)
  C ──┤     ──── B (합성 영상)
  D ──┘     ──── C (합성 영상)

  - 클라이언트 다운로드: 합성 스트림 1개
  - 서버 부담: 모든 스트림 디코딩 + 합성 + 재인코딩
```

클라이언트 다운로드가 단 한 개라 레거시 단말이나 저사양 기기에 유리하다. 하지만 서버가 실시간으로 모든 영상을 디코딩·합성·인코딩해야 하므로 서버 CPU가 폭발적으로 필요하다. 참가자 100명의 영상을 전부 합성하면서 100명에게 각기 다른 버전을 내보내는 건 엄청난 계산량이다. 그래서 MCU는 전용 하드웨어 인코더(NVENC 같은)를 활용하지 않으면 경제성이 나오지 않는다.

실무에서는 SFU가 대세다. 서버 비용 대비 성능이 훨씬 낫고, 클라이언트가 레거시 단말이 아닌 이상 다운로드 다중 스트림을 처리할 수 있다.

| 항목 | SFU | MCU |
|------|-----|-----|
| 서버 CPU | 낮음 (포워딩만) | 매우 높음 (인코딩) |
| 클라이언트 다운로드 | N-1개 스트림 | 합성본 1개 |
| 레이턴시 | 낮음 | 높음 (합성 처리 시간) |
| 배포 비용 | 보통 | 높음 |
| 대표 구현 | mediasoup, LiveKit | Kurento (MixerElement) |

---

## TURN 릴레이 비율 변화

SFU를 도입하면 TURN 상황이 바뀐다. 풀메시에서는 피어-피어 연결 하나하나가 NAT 통과 문제를 가진다. 10명 방의 45개 연결 중 대칭형 NAT이 섞인 조합은 모두 TURN이 필요하다. 참가자 한 명이 CGNAT 뒤 모바일이라면 그 사람과 맺는 9개 연결이 전부 TURN 릴레이가 된다.

SFU에서는 단말이 서버에만 연결한다. 서버는 공인 IP를 가진 인프라라 서버 쪽은 NAT 문제가 없다. 클라이언트-서버 연결에서만 NAT 통과가 필요하다. 대칭형 NAT 뒤 클라이언트라도 TURN은 그 클라이언트의 연결 1개에만 적용된다. 10명 방에서 CGNAT 모바일 사용자 1명이 있으면 TURN이 필요한 연결은 1개(클라이언트↔서버)뿐이다. 풀메시였다면 9개였을 것이다.

결과적으로 SFU에서 TURN 릴레이 비율은 세션 단위가 아니라 참가자 단위로 계산된다. 전체 사용자 중 대칭형 NAT 뒤에 있는 비율(통상 10~20%)만큼의 연결이 TURN을 쓴다. TURN 대역폭도 그 연결들의 업로드 스트림만 릴레이하면 된다. 풀메시 대비 TURN 트래픽이 크게 줄어든다.

그러나 SFU를 도입해도 서버와 클라이언트 사이에 TURN을 빼면 안 된다. SFU 서버가 공인 IP를 가지더라도 클라이언트가 UDP 아웃바운드를 막는 기업망에 있으면 연결이 안 된다. TURN over TLS:443을 iceServers에 포함시켜야 한다.

---

## mediasoup 세션 관리

mediasoup는 Node.js 기반 SFU 라이브러리다. 자체 시그널링 서버는 없고, WebRTC 미디어 처리 엔진만 제공한다. 애플리케이션이 시그널링(WebSocket 등)을 직접 구현하고 mediasoup API를 호출해서 라우터와 트랜스포트를 관리한다.

### 핵심 개념

- Worker: C++ 미디어 처리 프로세스. CPU 코어당 하나씩 올리는 게 일반적이다.
- Router: 미디어 라우팅 공간. 방(room) 하나당 Router 하나를 만든다.
- Transport: 클라이언트와의 WebRTC 연결 단위. 각 참가자가 Producer용, Consumer용 Transport를 각각 가진다.
- Producer: 클라이언트가 올리는 미디어 스트림.
- Consumer: 클라이언트가 받는 미디어 스트림. Producer 하나당 Consumer를 여러 개 만들 수 있다.

### 서버 코드 (Node.js)

```javascript
const mediasoup = require('mediasoup');

// Worker와 Router 초기화
async function createRouter() {
  const worker = await mediasoup.createWorker({
    logLevel: 'warn',
    rtcMinPort: 10000,
    rtcMaxPort: 10999,
  });

  worker.on('died', () => {
    console.error('mediasoup worker died, restarting...');
    // 실제 운영에서는 여기서 worker를 재생성해야 한다
    process.exit(1);
  });

  const router = await worker.createRouter({
    mediaCodecs: [
      {
        kind: 'video',
        mimeType: 'video/VP8',
        clockRate: 90000,
        parameters: { 'x-google-start-bitrate': 1000 },
      },
      {
        kind: 'video',
        mimeType: 'video/H264',
        clockRate: 90000,
        parameters: {
          'packetization-mode': 1,
          'profile-level-id': '42e01f',
          'level-asymmetry-allowed': 1,
        },
      },
      { kind: 'audio', mimeType: 'audio/opus', clockRate: 48000, channels: 2 },
    ],
  });

  return { worker, router };
}

// 참가자 입장: WebRTC 트랜스포트 생성
async function createTransport(router) {
  const transport = await router.createWebRtcTransport({
    listenIps: [
      { ip: '0.0.0.0', announcedIp: process.env.PUBLIC_IP }, // 서버 공인 IP
    ],
    enableUdp: true,
    enableTcp: true,
    preferUdp: true,
    iceServers: [
      // 클라이언트 → SFU 서버 연결에도 TURN이 필요한 경우
      { urls: 'turn:turn.example.com:3478', username: 'u', credential: 'p' },
      { urls: 'turns:turn.example.com:443?transport=tcp', username: 'u', credential: 'p' },
    ],
  });

  transport.on('dtlsstatechange', (dtlsState) => {
    if (dtlsState === 'closed') transport.close();
  });

  return transport;
}

// Producer 생성: 클라이언트가 미디어를 업로드하는 쪽
async function createProducer(transport, rtpParameters) {
  const producer = await transport.produce({
    kind: 'video', // 'audio'
    rtpParameters,  // 클라이언트 SDP에서 추출한 RTP 파라미터
    appData: { peerId: '...' },
  });

  producer.on('transportclose', () => producer.close());

  return producer;
}

// Consumer 생성: 다른 참가자의 미디어를 받는 쪽
async function createConsumer(router, transport, producer, rtpCapabilities) {
  // 클라이언트가 이 코덱을 받을 수 있는지 먼저 확인
  if (!router.canConsume({ producerId: producer.id, rtpCapabilities })) {
    throw new Error('클라이언트가 이 Producer를 소비할 수 없음 (코덱 불일치)');
  }

  const consumer = await transport.consume({
    producerId: producer.id,
    rtpCapabilities,
    paused: true, // 처음에는 일시 중지, 클라이언트 준비 후 resume
  });

  consumer.on('transportclose', () => consumer.close());
  consumer.on('producerclose', () => consumer.close());

  return consumer;
}
```

### 시그널링 흐름 (WebSocket)

mediasoup는 시그널링을 직접 제공하지 않는다. 아래는 방 입장부터 미디어 수신까지의 전형적인 메시지 흐름이다.

```javascript
// 클라이언트 측 시그널링 흐름
const ws = new WebSocket('wss://server/signaling');

// 1. 방 입장, 서버에서 Router의 RTP 능력을 받아온다
ws.send(JSON.stringify({ type: 'join', roomId: 'room-1' }));
// 서버 응답: { rtpCapabilities: {...} }

// 2. 내 RTP 능력 설정
const device = new mediasoupClient.Device();
await device.load({ routerRtpCapabilities });

// 3. 업로드용 트랜스포트 생성 요청
ws.send(JSON.stringify({ type: 'createTransport', direction: 'send' }));
// 서버 응답: { id, iceParameters, iceCandidates, dtlsParameters }

const sendTransport = device.createSendTransport(transportParams);

sendTransport.on('connect', ({ dtlsParameters }, callback, errback) => {
  // 서버에 DTLS 파라미터 전달해서 핸드셰이크 완료
  ws.send(JSON.stringify({ type: 'connectTransport', dtlsParameters }));
  callback();
});

sendTransport.on('produce', async ({ kind, rtpParameters }, callback, errback) => {
  // 서버에 Producer 생성 요청
  ws.send(JSON.stringify({ type: 'produce', kind, rtpParameters }));
  // 서버 응답의 producerId를 callback으로 넘겨야 한다
});

// 4. 미디어 스트림 얻어서 Producer 시작
const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
const videoTrack = stream.getVideoTracks()[0];
const producer = await sendTransport.produce({ track: videoTrack });
```

`sendTransport.on('connect')`와 `sendTransport.on('produce')` 콜백 안에서 시그널링을 통해 서버와 왕복해야 한다는 점이 처음에 헷갈린다. callback을 즉시 호출하면 서버와 동기화 없이 DTLS 핸드셰이크가 진행되어 연결이 실패한다. 서버 응답을 확인한 뒤 callback을 호출해야 한다.

---

## LiveKit 세션 관리

LiveKit는 mediasoup와 달리 완성된 SFU 플랫폼이다. Go로 작성된 서버와 각 언어용 SDK를 제공한다. mediasoup처럼 시그널링을 직접 짤 필요 없이, Room API와 SDK로 참가자와 트랙을 관리한다.

### 서버 사이드 (Node.js SDK)

```javascript
const { AccessToken, RoomServiceClient } = require('livekit-server-sdk');

const LIVEKIT_HOST = 'wss://livekit.example.com';
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;

// 참가자에게 방 입장 토큰 발급
function createToken(roomName, participantName, isPublisher = true) {
  const at = new AccessToken(API_KEY, API_SECRET, {
    identity: participantName,
    ttl: '2h',
  });

  at.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: isPublisher,    // 발행 권한
    canSubscribe: true,         // 구독 권한
    canPublishData: true,       // DataChannel 사용 권한
  });

  return at.toJwt();
}

// 서버에서 방 상태 관리
const roomService = new RoomServiceClient(LIVEKIT_HOST, API_KEY, API_SECRET);

async function getRoomParticipants(roomName) {
  const participants = await roomService.listParticipants(roomName);
  return participants.map((p) => ({
    identity: p.identity,
    state: p.state,
    tracks: p.tracks.map((t) => ({ sid: t.sid, type: t.type, muted: t.muted })),
  }));
}

// 특정 참가자 강퇴
async function removeParticipant(roomName, identity) {
  await roomService.removeParticipant(roomName, identity);
}

// 방 삭제 (녹화 완료 후 정리 등)
async function deleteRoom(roomName) {
  await roomService.deleteRoom(roomName);
}
```

### 클라이언트 사이드 (브라우저)

```javascript
import { Room, RoomEvent, Track, VideoPresets } from 'livekit-client';

const room = new Room({
  adaptiveStream: true,        // 대역폭에 따라 수신 품질 자동 조정
  dynacast: true,              // 보는 사람 없는 트랙은 전송 중단
  videoCaptureDefaults: {
    resolution: VideoPresets.h720.resolution,
  },
  publishDefaults: {
    simulcast: true,           // 시뮬캐스트 활성화 (아래에서 설명)
    videoSimulcastLayers: [
      VideoPresets.h180,
      VideoPresets.h360,
      VideoPresets.h720,
    ],
  },
});

// 이벤트: 다른 참가자의 트랙이 구독될 때
room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
  if (track.kind === Track.Kind.Video) {
    const videoEl = document.createElement('video');
    track.attach(videoEl);
    document.body.appendChild(videoEl);
  }
  if (track.kind === Track.Kind.Audio) {
    const audioEl = document.createElement('audio');
    track.attach(audioEl);
    document.body.appendChild(audioEl);
  }
});

room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
  track.detach();
});

// 방 입장
await room.connect('wss://livekit.example.com', token);

// 카메라, 마이크 발행
await room.localParticipant.setCameraEnabled(true);
await room.localParticipant.setMicrophoneEnabled(true);

// 화면 공유
const screenTrack = await room.localParticipant.createScreenTracks({
  video: true,
  audio: true,
});
await room.localParticipant.publishTrack(screenTrack[0]);
```

mediasoup는 저수준 제어가 필요한 경우(코덱 세밀 설정, 라우팅 로직 커스터마이징)에 적합하고, LiveKit는 빠르게 기능을 올려야 할 때 적합하다. LiveKit는 내부적으로 mediasoup 수준의 SFU 엔진을 Go로 구현해두었다.

---

## 운영에서 겪는 인코딩·대역폭 문제

### 시뮬캐스트 (Simulcast)

SFU를 쓴다고 대역폭 문제가 사라지진 않는다. 모든 구독자가 항상 최고 품질을 받으면 고화질 참가자가 많아질수록 서버의 포워딩 대역폭이 폭증한다. 방에 10명이 있고 각자 720p를 올리면, 서버가 소화해야 하는 업로드(인바운드) 대역폭은 10 * ~2Mbps = 20Mbps다. 여기에 각 참가자가 나머지 9명의 스트림을 받으면 아웃바운드는 10 * 9 * ~2Mbps = 180Mbps다. 방 하나에 이미 수백 Mbps다.

시뮬캐스트는 발신자가 동일 스트림을 여러 해상도·비트레이트로 동시에 올리는 방식이다. 720p, 360p, 180p 세 레이어를 동시에 발송한다. SFU는 수신자 상황(대역폭, 화면 크기)에 따라 어떤 레이어를 포워딩할지 고른다. 발신자 CPU 부담이 약간 늘지만, 서버가 재인코딩하지 않아도 다양한 품질을 서비스할 수 있다.

```javascript
// mediasoup에서 시뮬캐스트 Consumer의 레이어 전환
// 대역폭이 부족한 수신자에게 낮은 레이어로 전환
await consumer.setPreferredLayers({
  spatialLayer: 1,   // 0=최저, 2=최고 해상도 (spatial layer)
  temporalLayer: 2,  // 0=낮은 fps, 2=최고 fps (temporal layer)
});

// 수신자의 현재 레이어 확인
console.log(consumer.currentLayers); // { spatialLayer: 1, temporalLayer: 2 }
```

발신자 쪽에서 시뮬캐스트를 활성화하면 같은 인터페이스로 여러 스트림이 올라오므로, 서버와의 연결이 맺힐 때 SDP를 잘 봐야 한다. 시뮬캐스트 SDP는 `a=rid:` 줄로 각 레이어를 구분한다.

```
a=simulcast:send h;m;l
a=rid:h send
a=rid:m send; max-width=640
a=rid:l send; max-width=320
```

### SVC (Scalable Video Coding)

시뮬캐스트는 여러 스트림을 동시에 올리므로 발신자 인코딩 부담이 크다. VP9의 SVC(K-SVC 모드)나 AV1의 레이어드 인코딩은 하나의 스트림 안에 여러 품질 레이어를 담는다. 발신자가 인코딩을 한 번만 하면서도 SFU가 레이어를 골라 포워딩할 수 있다.

운영에서 VP9 SVC가 까다로운 이유는 크롬과 사파리의 지원 범위가 달라서 코덱 협상이 예상대로 안 되는 경우가 있다는 점이다. 발신자가 VP9 SVC로 올리는데 수신자가 VP9 SVC를 받지 못하면 SFU가 레이어 분리를 못 해서 최고 레이어 전체를 그냥 포워딩하게 된다. 다양한 단말을 지원해야 한다면 VP8 시뮬캐스트가 호환성이 더 낫다.

### 대역폭 추정과 적응

클라이언트는 REMB(Receiver Estimated Maximum Bitrate) 또는 TWCC(Transport Wide Congestion Control)로 수신 가능한 대역폭을 서버에 피드백한다. SFU는 이 피드백을 보고 해당 구독자에게 어떤 시뮬캐스트 레이어를 보낼지 실시간으로 조정한다.

운영에서 발생하는 전형적인 문제는 이렇다. 와이파이 신호가 약해지거나 모바일이 LTE에서 3G로 떨어지면 REMB 수치가 급격히 낮아진다. SFU가 레이어를 내리기 전에 이미 패킷이 손실되고, 수신자 화면이 프리징된다. 이때 클라이언트가 PLI(Picture Loss Indication)를 보내서 발신자에게 키프레임을 요청한다. 키프레임이 오기 전까지 수신자 화면은 멈춰있다. 모바일 네트워크가 불안정한 환경에서 이 PLI → 키프레임 사이클이 잦으면 사용자가 체감하는 품질이 나빠진다.

```javascript
// 발신자 쪽에서 키프레임 요청 빈도 모니터링 (mediasoup)
producer.on('score', (scores) => {
  // scores: [{ ssrc, score }] — score가 낮으면 품질 나쁨
  for (const { ssrc, score } of scores) {
    if (score < 5) {
      // 인코더 설정 조정을 고려해야 하는 시점
      console.warn(`Producer ${producer.id} score low: ${score}`);
    }
  }
});
```

### CPU 인코딩 병목

서버 CPU 부담이 낮은 게 SFU의 장점이지만, 동방 수가 많아지거나 참가자가 많아지면 Node.js의 mediasoup worker 프로세스들이 CPU를 나눠먹는다. 보통 물리 코어당 worker 하나를 올리고 방을 worker들에게 분산시킨다. 특정 worker에 큰 방들이 몰리면 그 worker의 CPU가 포화되어 패킷 처리가 지연된다.

```javascript
// worker pool에서 CPU 사용량이 가장 낮은 worker 선택
function getLeastLoadedWorker(workers) {
  return workers.reduce((min, w) =>
    w.appData.roomCount < min.appData.roomCount ? w : min
  );
}

// 방 생성 시 worker를 선택하고 사용 중인 방 수 추적
async function createRoom(roomId) {
  const worker = getLeastLoadedWorker(workers);
  const router = await worker.createRouter({ mediaCodecs });
  worker.appData.roomCount++;
  rooms.set(roomId, { router, worker });
  return router;
}
```

실제로는 CPU 사용량을 주기적으로 polling해서 worker 상태를 확인하는 게 더 정확하다. mediasoup worker는 `worker.getResourceUsage()`로 CPU 사용량을 확인할 수 있다.

### 대역폭과 포트 설계

SFU를 방화벽 뒤에 올릴 때 포트 범위 설정을 빠뜨리는 경우가 많다. mediasoup는 참가자 트랜스포트마다 UDP 포트를 하나 잡는다. 동시 접속자가 100명이면 포트 200개(업로드용, 다운로드용)가 필요하다. `rtcMinPort`, `rtcMaxPort`로 범위를 지정하고 방화벽에서 해당 UDP 포트 범위를 열어야 한다. 포트를 안 열어두면 ICE가 서버 reflexive 후보를 못 만들어서 클라이언트-서버 연결이 실패한다.

```bash
# 방화벽 포트 범위 개방 (예: UFW)
sudo ufw allow 10000:10999/udp
sudo ufw allow 3478/udp   # STUN/TURN
sudo ufw allow 5349/tcp   # TURN over TLS
```

coturn과 mediasoup를 같은 서버에 올리면 포트 충돌이 날 수 있다. coturn의 `min-port`, `max-port`와 mediasoup의 `rtcMinPort`, `rtcMaxPort`가 겹치지 않도록 범위를 나눠야 한다.

### 녹화와 인코딩 부담

서버 사이드 녹화가 필요하면 SFU 포워딩 스트림을 파일로 저장해야 한다. mediasoup에서는 `PlainTransport`로 RTP 스트림을 꺼내서 FFmpeg에 파이프하는 방식을 많이 쓴다. 이 구간에서 FFmpeg가 트랜스코딩을 하면 CPU를 상당히 소모한다. 녹화 세션이 많아지면 별도 녹화 전용 서버를 두거나, 받은 RTP를 트랜스코딩 없이 WebM/Matroska로 저장하고 후처리하는 방식을 쓰는 게 서버 부담을 줄인다.

LiveKit는 `Egress` API로 방 녹화를 제공한다. 내부적으로 Chromium 인스턴스를 띄워서 화면을 캡처하거나 합성 영상을 만드는 방식이라 CPU 사용량이 크다. 대규모 동시 녹화가 필요하다면 Egress 서버를 별도로 스케일아웃해야 한다.
