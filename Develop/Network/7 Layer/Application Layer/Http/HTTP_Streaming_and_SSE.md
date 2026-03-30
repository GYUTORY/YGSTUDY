---
title: HTTP 스트리밍과 실시간 통신
tags: [network, http, streaming, chunked-transfer, sse, websocket, long-polling, server-sent-events]
updated: 2026-03-30
---

# HTTP 스트리밍과 실시간 통신

## 왜 필요한가

HTTP는 기본적으로 요청-응답 모델이다. 클라이언트가 요청하면 서버가 응답하고 연결이 끝난다. 그런데 실시간 알림, 채팅, 주식 시세처럼 서버에서 클라이언트로 데이터를 계속 보내야 하는 상황이 있다. 이때 매번 새로운 요청을 보내는 건 비효율적이다.

이 문제를 해결하기 위해 여러 방식이 존재한다. 각각 동작 원리가 다르고, 적합한 상황도 다르다.

## Long Polling

### 동작 방식

일반 Polling은 클라이언트가 일정 주기로 서버에 요청을 보내는 방식이다. 데이터가 없어도 요청을 보내므로 불필요한 트래픽이 발생한다.

Long Polling은 이 문제를 개선한 방식이다. 클라이언트가 요청을 보내면 서버가 즉시 응답하지 않고, 새 데이터가 생길 때까지 연결을 유지한다. 데이터가 생기면 응답을 보내고, 클라이언트는 응답을 받자마자 다시 요청을 보낸다.

```
Client → Server: GET /updates (대기)
            ... 30초 후 새 데이터 발생 ...
Server → Client: 200 OK (데이터 포함)
Client → Server: GET /updates (다시 대기)
```

### 구현 시 주의사항

서버 측에서 연결을 오래 유지하면 커넥션 풀이 고갈될 수 있다. Tomcat 같은 서블릿 컨테이너는 스레드 하나가 요청 하나를 잡고 있으므로, 동시 접속자가 많으면 스레드가 모자라는 상황이 생긴다.

타임아웃 설정도 중요하다. 서버 앞에 Nginx나 로드밸런서가 있으면 프록시 타임아웃에 걸릴 수 있다. 보통 30초 정도로 설정하고, 타임아웃되면 클라이언트가 재연결하는 구조로 만든다.

### Spring 구현 예제

```java
@RestController
public class LongPollingController {

    private final Map<String, DeferredResult<ResponseEntity<String>>> waitingClients
            = new ConcurrentHashMap<>();

    @GetMapping("/poll")
    public DeferredResult<ResponseEntity<String>> poll(@RequestParam String clientId) {
        // 30초 타임아웃 설정
        DeferredResult<ResponseEntity<String>> result = new DeferredResult<>(30000L);

        result.onTimeout(() -> {
            waitingClients.remove(clientId);
            result.setResult(ResponseEntity.noContent().build());
        });

        result.onCompletion(() -> waitingClients.remove(clientId));

        waitingClients.put(clientId, result);
        return result;
    }

    // 새 데이터가 생기면 대기 중인 클라이언트에게 전달
    public void pushMessage(String clientId, String message) {
        DeferredResult<ResponseEntity<String>> result = waitingClients.get(clientId);
        if (result != null) {
            result.setResult(ResponseEntity.ok(message));
        }
    }
}
```

`DeferredResult`를 사용하면 서블릿 스레드를 바로 반환하면서 응답은 나중에 보낼 수 있다. 스레드 풀 고갈 문제를 줄이는 핵심이다.

## Chunked Transfer-Encoding

### 동작 방식

HTTP/1.1에서 도입된 전송 방식이다. 응답의 전체 크기를 미리 알 수 없을 때, 데이터를 조각(chunk)으로 나눠서 보낸다. `Content-Length` 헤더 대신 `Transfer-Encoding: chunked` 헤더를 사용한다.

```http
HTTP/1.1 200 OK
Transfer-Encoding: chunked

7\r\n
Hello, \r\n
6\r\n
World!\r\n
0\r\n
\r\n
```

각 chunk는 `크기(16진수)\r\n데이터\r\n` 형식이다. 크기가 0인 chunk가 전송 종료를 의미한다.

### 스트리밍에 활용

Chunked Transfer-Encoding 자체가 실시간 통신 프로토콜은 아니다. 원래 목적은 큰 파일이나 동적 콘텐츠를 점진적으로 전송하는 것이다. 하지만 서버가 chunk를 천천히 보내면 스트리밍처럼 동작한다. SSE가 내부적으로 이 방식을 사용한다.

### 실무에서 겪는 문제

Nginx를 리버스 프록시로 사용하면 기본적으로 응답을 버퍼링한다. 서버가 chunk를 보내도 Nginx가 전부 모았다가 한 번에 클라이언트로 보내는 현상이 발생한다. 스트리밍이 필요하면 `proxy_buffering off` 설정이 필요하다.

```nginx
location /stream {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
}
```

## Server-Sent Events (SSE)

### 동작 방식

SSE는 서버에서 클라이언트로 단방향 스트리밍을 위한 표준이다. HTTP 위에서 동작하며 별도의 프로토콜 업그레이드가 필요 없다. 서버가 `text/event-stream` 콘텐츠 타입으로 응답하면, 브라우저의 `EventSource` API가 이를 처리한다.

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: 첫 번째 메시지

event: notification
data: {"type": "alert", "message": "서버 점검"}

id: 3
data: 세 번째 메시지
```

각 이벤트는 빈 줄(`\n\n`)로 구분한다. `data:` 필드가 실제 데이터이고, `event:` 필드로 이벤트 타입을 지정할 수 있다. `id:` 필드는 재연결 시 마지막으로 받은 이벤트를 서버에 알려주는 용도다.

### 자동 재연결

SSE의 큰 장점은 연결이 끊어지면 브라우저가 자동으로 재연결을 시도한다는 점이다. 서버가 `retry:` 필드로 재연결 간격(밀리초)을 지정할 수 있다.

```http
retry: 5000
data: 5초 후 재연결하도록 설정
```

재연결할 때 브라우저는 `Last-Event-ID` 헤더에 마지막으로 받은 `id` 값을 보낸다. 서버는 이를 확인해서 놓친 이벤트부터 다시 보내주면 된다.

### Spring 구현 예제

```java
@RestController
public class SseController {

    private final CopyOnWriteArrayList<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    @GetMapping(value = "/sse", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(60_000L); // 60초 타임아웃

        emitters.add(emitter);
        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError(e -> emitters.remove(emitter));

        return emitter;
    }

    // 이벤트를 모든 구독자에게 전달
    public void broadcast(String eventName, Object data) {
        List<SseEmitter> deadEmitters = new ArrayList<>();

        emitters.forEach(emitter -> {
            try {
                emitter.send(SseEmitter.event()
                        .name(eventName)
                        .data(data, MediaType.APPLICATION_JSON));
            } catch (IOException e) {
                deadEmitters.add(emitter);
            }
        });

        emitters.removeAll(deadEmitters);
    }
}
```

`SseEmitter`의 타임아웃은 서블릿 컨테이너의 비동기 타임아웃과 맞춰야 한다. Spring Boot에서는 `spring.mvc.async.request-timeout` 설정과 `SseEmitter` 생성자의 타임아웃 값이 다르면 예상치 못한 연결 종료가 발생한다.

### Express 구현 예제

```javascript
const express = require('express');
const app = express();

const clients = new Set();

app.get('/sse', (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    });

    // 연결 직후 초기 데이터 전송
    res.write('retry: 5000\n\n');

    clients.add(res);

    req.on('close', () => {
        clients.delete(res);
    });
});

function broadcast(event, data) {
    const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
    clients.forEach(client => client.write(message));
}
```

Node.js는 이벤트 루프 기반이라 연결을 오래 유지해도 스레드를 점유하지 않는다. Long Polling이나 SSE 구현에 유리한 이유다.

### SSE 사용 시 주의사항

HTTP/1.1에서는 브라우저별로 동일 도메인에 대한 SSE 연결 수가 제한된다. 대부분의 브라우저에서 6개가 최대다. 탭을 여러 개 열면 금방 한계에 도달한다. HTTP/2를 사용하면 멀티플렉싱 덕분에 이 제한이 사라진다.

IE는 SSE를 지원하지 않는다. polyfill 라이브러리를 사용하거나, IE 지원이 필요하면 Long Polling으로 대체해야 한다.

## WebSocket과 HTTP Upgrade

### HTTP Upgrade 메커니즘

WebSocket은 HTTP와 다른 프로토콜이지만, 연결 수립은 HTTP를 통해 이루어진다. 클라이언트가 HTTP 요청에 `Upgrade: websocket` 헤더를 포함하면, 서버가 `101 Switching Protocols` 응답으로 프로토콜을 전환한다.

```http
GET /ws HTTP/1.1
Host: example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

이 핸드셰이크가 완료되면 HTTP 연결이 WebSocket 연결로 전환된다. 이후부터는 HTTP가 아니라 WebSocket 프레임 단위로 양방향 통신이 이루어진다.

### SSE와의 차이

WebSocket은 양방향 통신이다. 클라이언트와 서버 모두 자유롭게 메시지를 보낼 수 있다. SSE는 서버에서 클라이언트 방향만 가능하다. 클라이언트가 서버로 데이터를 보내려면 별도의 HTTP 요청을 사용해야 한다.

WebSocket은 바이너리 데이터도 전송할 수 있다. SSE는 텍스트만 가능하다. 이미지나 파일 같은 바이너리를 실시간으로 주고받아야 하면 WebSocket이 맞다.

### Spring WebSocket 예제

```java
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(chatHandler(), "/ws/chat")
                .setAllowedOrigins("*");
    }

    @Bean
    public WebSocketHandler chatHandler() {
        return new TextWebSocketHandler() {

            private final Set<WebSocketSession> sessions
                    = ConcurrentHashMap.newKeySet();

            @Override
            public void afterConnectionEstablished(WebSocketSession session) {
                sessions.add(session);
            }

            @Override
            protected void handleTextMessage(WebSocketSession session,
                                             TextMessage message) throws Exception {
                // 받은 메시지를 모든 세션에 전달
                for (WebSocketSession s : sessions) {
                    if (s.isOpen()) {
                        s.sendMessage(message);
                    }
                }
            }

            @Override
            public void afterConnectionClosed(WebSocketSession session,
                                              CloseStatus status) {
                sessions.remove(session);
            }
        };
    }
}
```

### 프록시 환경에서의 문제

WebSocket은 HTTP Upgrade를 사용하므로 중간에 프록시가 있으면 연결이 실패하는 경우가 있다. Nginx에서 WebSocket을 지원하려면 별도 설정이 필요하다.

```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

`proxy_read_timeout`을 늘려줘야 한다. 기본값 60초가 지나면 Nginx가 유휴 상태의 WebSocket 연결을 끊어버린다.

AWS ALB는 WebSocket을 기본 지원하지만, Classic Load Balancer는 지원하지 않는다. Classic ELB 환경이면 TCP 모드로 설정하거나 ALB로 변경해야 한다.

## 방식별 비교

| 항목 | Long Polling | SSE | WebSocket |
|------|-------------|-----|-----------|
| 통신 방향 | 단방향 (서버 → 클라이언트) | 단방향 (서버 → 클라이언트) | 양방향 |
| 프로토콜 | HTTP | HTTP | WS (HTTP로 핸드셰이크) |
| 데이터 형식 | 텍스트/바이너리 | 텍스트 | 텍스트/바이너리 |
| 자동 재연결 | 직접 구현 | 브라우저 내장 | 직접 구현 |
| 연결 유지 | 요청마다 새 연결 | 하나의 연결 유지 | 하나의 연결 유지 |
| 방화벽 통과 | 문제 없음 | 문제 없음 | 간혹 차단됨 |
| HTTP/2 호환 | 가능 | 멀티플렉싱 이점 | 별도 프로토콜 |

## 실무에서 선택하는 기준

**SSE를 사용하는 경우**: 서버에서 클라이언트로 이벤트를 보내는 단방향 통신이면 SSE가 가장 단순하다. 알림 시스템, 실시간 피드, 대시보드 업데이트 같은 상황에 적합하다. LLM 응답 스트리밍(ChatGPT 같은 서비스)도 SSE를 사용한다. 브라우저 내장 자동 재연결이 있어서 안정적이다.

**WebSocket을 사용하는 경우**: 채팅, 실시간 게임, 공동 편집처럼 클라이언트와 서버가 동시에 데이터를 주고받아야 하면 WebSocket이 맞다. 바이너리 데이터 전송이 필요한 경우에도 WebSocket을 선택한다.

**Long Polling을 사용하는 경우**: SSE나 WebSocket을 쓸 수 없는 환경에서 대안으로 사용한다. IE 지원이 필요하거나, 인프라가 WebSocket/SSE를 지원하지 않는 레거시 환경에서 선택하게 된다. 새로 만드는 서비스에서 의도적으로 Long Polling을 선택하는 경우는 거의 없다.

**Chunked Transfer-Encoding만 사용하는 경우**: 파일 다운로드 진행률 표시나 대용량 응답의 점진적 렌더링 같은 상황에서 사용한다. 실시간 이벤트 스트리밍 목적이면 SSE를 사용하는 게 맞다. Chunked Transfer-Encoding은 SSE의 하위 메커니즘이지 독립적인 실시간 통신 방법은 아니다.

## 인프라 설정 시 확인할 것

어떤 방식을 쓰든 서버와 클라이언트 사이에 있는 중간 장비 설정을 확인해야 한다.

- **Nginx/Apache**: 프록시 버퍼링, 타임아웃, WebSocket Upgrade 헤더 전달 설정
- **로드밸런서**: WebSocket 지원 여부, sticky session 필요성, idle timeout 값
- **CDN**: 대부분의 CDN은 SSE와 WebSocket을 제대로 처리하지 못한다. 실시간 통신 경로는 CDN을 우회하도록 구성해야 한다
- **방화벽/보안장비**: 일부 기업 방화벽이 WebSocket 연결을 차단한다. 이 경우 SSE나 Long Polling으로 폴백하는 로직이 필요하다. Socket.IO 같은 라이브러리가 이 폴백을 자동으로 처리한다
