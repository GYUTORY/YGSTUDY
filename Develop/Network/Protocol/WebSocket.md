---
title: WebSocket 심화 가이드
tags: [network, websocket, real-time, socket, stomp, socket-io, sse]
updated: 2026-03-01
---

# WebSocket 심화

## 개요

WebSocket은 **하나의 TCP 연결 위에서 전이중(Full-Duplex) 양방향 통신**을 제공하는 프로토콜이다. HTTP의 요청-응답 모델과 달리, 서버와 클라이언트가 언제든 자유롭게 메시지를 주고받을 수 있다.

```
HTTP (단방향):
  Client ──요청──▶ Server
  Client ◀──응답── Server
  Client ──요청──▶ Server  (매번 새 연결 or 재요청)

WebSocket (양방향):
  Client ──HTTP 핸드셰이크──▶ Server
  Client ◀════ 양방향 통신 ════▶ Server  (연결 유지)
```

### 왜 WebSocket인가

| 방식 | 지연 | 서버 부하 | 양방향 | 적합한 경우 |
|------|------|----------|--------|-----------|
| **Polling** | 높음 (주기적) | 높음 | ❌ | 단순 업데이트 |
| **Long Polling** | 중간 | 중간 | ❌ | 알림 시스템 |
| **SSE** | 낮음 | 낮음 | 서버→클라이언트만 | 주식 시세, 로그 스트리밍 |
| **WebSocket** | **매우 낮음** | **낮음** | **✅** | 채팅, 게임, 실시간 협업 |

## 핵심

### 1. 연결 수립 (Handshake)

WebSocket은 HTTP 업그레이드 메커니즘으로 연결을 시작한다.

```
1. 클라이언트 → HTTP 업그레이드 요청
2. 서버 → 101 Switching Protocols 응답
3. 이후 → WebSocket 프레임으로 통신

┌──────────┐                         ┌──────────┐
│  Client  │──HTTP GET (Upgrade)───▶│  Server  │
│          │◀──101 Switching─────── │          │
│          │◀════ WebSocket ════▶   │          │
└──────────┘                         └──────────┘
```

#### 핸드셰이크 상세

```
클라이언트 요청:
  GET /chat HTTP/1.1
  Host: server.example.com
  Upgrade: websocket                    ← 프로토콜 업그레이드 요청
  Connection: Upgrade
  Sec-WebSocket-Key: dGhlIHNhbXBsZQ==  ← 랜덤 Base64 키
  Sec-WebSocket-Version: 13            ← WebSocket 버전
  Sec-WebSocket-Protocol: chat, superchat  ← 서브 프로토콜 (선택)

서버 응답:
  HTTP/1.1 101 Switching Protocols
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9k...  ← Key + GUID의 SHA-1 해시
  Sec-WebSocket-Protocol: chat              ← 선택된 서브 프로토콜
```

### 2. 프레임 구조

핸드셰이크 이후 데이터는 **프레임(Frame)** 단위로 전송된다.

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
| **FIN** | 1 bit | 마지막 프레임 여부 |
| **opcode** | 4 bit | 프레임 타입 (text=0x1, binary=0x2, close=0x8, ping=0x9, pong=0xA) |
| **MASK** | 1 bit | 클라이언트→서버는 반드시 마스킹 |
| **Payload length** | 7/16/64 bit | 데이터 길이 |
| **Payload Data** | 가변 | 실제 데이터 |

### 3. JavaScript 클라이언트

```javascript
// 기본 연결
const ws = new WebSocket('wss://server.example.com/chat');

// 이벤트 핸들링
ws.onopen = (event) => {
    console.log('연결됨');
    ws.send(JSON.stringify({ type: 'join', room: 'general' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('수신:', data);
};

ws.onerror = (error) => {
    console.error('에러:', error);
};

ws.onclose = (event) => {
    console.log(`연결 종료: code=${event.code}, reason=${event.reason}`);
    // 재연결 로직
    if (event.code !== 1000) {
        setTimeout(() => reconnect(), 3000);
    }
};

// 메시지 전송
ws.send('Hello');                          // 텍스트
ws.send(new ArrayBuffer(8));               // 바이너리
ws.send(new Blob(['binary data']));        // Blob

// 연결 종료
ws.close(1000, 'Normal closure');
```

#### 재연결 패턴

```javascript
class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.reconnectDelay = 1000;
        this.maxDelay = 30000;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            this.reconnectDelay = 1000;  // 성공 시 딜레이 초기화
        };

        this.ws.onclose = (event) => {
            if (event.code !== 1000) {
                // 지수 백오프로 재연결
                setTimeout(() => this.connect(), this.reconnectDelay);
                this.reconnectDelay = Math.min(
                    this.reconnectDelay * 2,
                    this.maxDelay
                );
            }
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
    }

    send(data) {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    handleMessage(data) { /* 오버라이드 */ }
}
```

### 4. Spring WebSocket (서버)

#### 기본 WebSocket

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
        // 전체 브로드캐스트
        for (WebSocketSession s : sessions) {
            if (s.isOpen()) {
                s.sendMessage(new TextMessage("Echo: " + message.getPayload()));
            }
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
    }
}
```

#### STOMP (Simple Text Oriented Messaging Protocol)

메시지 브로커 패턴으로 **pub/sub** 기반 실시간 통신을 구현한다.

```java
@Configuration
@EnableWebSocketMessageBroker
public class StompConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        config.enableSimpleBroker("/topic", "/queue");  // 구독 경로
        config.setApplicationDestinationPrefixes("/app");  // 전송 경로
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOrigins("https://example.com")
                .withSockJS();  // SockJS 폴백
    }
}

@Controller
public class ChatController {

    // 클라이언트가 /app/chat.send로 전송 → /topic/chat 구독자에게 브로드캐스트
    @MessageMapping("/chat.send")
    @SendTo("/topic/chat")
    public ChatMessage sendMessage(ChatMessage message) {
        return message;
    }

    // 특정 사용자에게 1:1 메시지
    @MessageMapping("/chat.private")
    public void privateMessage(ChatMessage message, SimpMessageHeaderAccessor headerAccessor) {
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

### 5. Socket.IO (Node.js)

WebSocket + 자동 폴백 + 룸/네임스페이스를 지원하는 라이브러리.

```javascript
// 서버 (Node.js)
const { Server } = require('socket.io');
const io = new Server(server, {
    cors: { origin: 'https://example.com' }
});

io.on('connection', (socket) => {
    console.log(`연결: ${socket.id}`);

    // 룸 참여
    socket.on('join-room', (roomId) => {
        socket.join(roomId);
        socket.to(roomId).emit('user-joined', socket.id);
    });

    // 메시지 전송
    socket.on('chat-message', (data) => {
        io.to(data.roomId).emit('new-message', {
            from: socket.id,
            text: data.text,
            timestamp: Date.now()
        });
    });

    // 연결 해제
    socket.on('disconnect', (reason) => {
        console.log(`연결 해제: ${socket.id}, 사유: ${reason}`);
    });
});

// 네임스페이스 (기능별 분리)
const admin = io.of('/admin');
admin.on('connection', (socket) => {
    // 관리자 전용 로직
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

### 6. SSE (Server-Sent Events) 비교

서버에서 클라이언트로의 **단방향 스트리밍**. WebSocket보다 단순하다.

```java
// Spring SSE
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
// 클라이언트 SSE
const eventSource = new EventSource('/stream');
eventSource.addEventListener('price-update', (event) => {
    const data = JSON.parse(event.data);
    updatePrice(data.price);
});
eventSource.onerror = () => {
    // 자동 재연결 (브라우저 기본 동작)
};
```

| 비교 | WebSocket | SSE |
|------|-----------|-----|
| **방향** | 양방향 | 서버→클라이언트 |
| **프로토콜** | ws:// / wss:// | HTTP |
| **바이너리** | ✅ | ❌ (텍스트만) |
| **자동 재연결** | 직접 구현 | 브라우저 기본 제공 |
| **HTTP/2 호환** | 별도 연결 | 멀티플렉싱 가능 |
| **프록시/방화벽** | 문제 가능 | HTTP이므로 통과 용이 |
| **적합한 경우** | 채팅, 게임, 양방향 | 주식 시세, 알림, 로그 |

### 7. 확장성 패턴

#### 다중 서버 환경

WebSocket은 상태를 유지하는(Stateful) 연결이므로, 다중 서버에서 **메시지 브로커**가 필요하다.

```
                    ┌──────────┐
Client A ──────── │ Server 1  │
                    │ (WS)     │──┐
                    └──────────┘  │
                                   ├── Redis Pub/Sub ──── 메시지 동기화
                    ┌──────────┐  │
Client B ──────── │ Server 2  │──┘
                    │ (WS)     │
                    └──────────┘

→ Client A가 보낸 메시지를 Server 2의 Client B도 수신
```

```java
// Spring + Redis Pub/Sub 브로커
@Configuration
@EnableWebSocketMessageBroker
public class StompConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Redis를 외부 브로커로 사용 (다중 서버 동기화)
        config.enableStompBrokerRelay("/topic", "/queue")
              .setRelayHost("redis-host")
              .setRelayPort(61613);
        config.setApplicationDestinationPrefixes("/app");
    }
}
```

#### 연결 수 관리

| 항목 | 권장 설정 | 이유 |
|------|----------|------|
| **연결 유휴 타임아웃** | 5~10분 | 비활성 연결 정리 |
| **Heartbeat (Ping/Pong)** | 25~30초 | 연결 상태 확인 |
| **최대 연결 수** | 서버당 10K~50K | OS 파일 디스크립터 제한 |
| **메시지 크기 제한** | 64KB~1MB | 메모리 보호 |

```nginx
# Nginx WebSocket 프록시 설정
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400s;   # 24시간 (유휴 타임아웃)
    proxy_send_timeout 86400s;
}
```

### 8. 보안

```
1. wss:// 사용 (TLS 암호화)
   - 평문 ws://는 프로덕션에서 사용 금지
   - 중간자 공격 방지

2. Origin 검증
   - 허용된 도메인만 연결 허용
   - CORS와 유사한 역할

3. 인증
   - 핸드셰이크 시 JWT 토큰 검증
   - 쿠키 기반 세션 인증

4. Rate Limiting
   - 연결 수 제한 (IP당, 유저당)
   - 메시지 전송 속도 제한

5. 입력 검증
   - 수신 메시지 크기 제한
   - JSON 파싱 전 유효성 검사
   - XSS 방지를 위한 이스케이프
```

## 참고

- [RFC 6455 — WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Socket.IO Documentation](https://socket.io/docs/v4/)
- [네트워크 프로토콜](Protocol.md) — HTTP, TCP, UDP 개요
- [STOMP over WebSocket](https://stomp.github.io/stomp-specification-1.2.html)
- [Nginx 리버스 프록시](../../WebServer/Nginx/Reverse_Proxy_and_Load_Balancing.md) — WebSocket 프록시 설정
