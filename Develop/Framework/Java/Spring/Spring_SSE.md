---
title: Spring SSE (Server-Sent Events)
tags: [spring, web-server, language, java]
updated: 2026-07-21
---

# Spring SSE (Server-Sent Events)

## SSE가 필요한 상황

서버에서 클라이언트로 데이터를 단방향으로 밀어야 할 때 선택지는 세 가지다. 폴링, WebSocket, SSE.

폴링은 클라이언트가 주기적으로 요청을 보내는 방식이라 지연이 생긴다. WebSocket은 양방향이 필요 없는데도 연결 유지 코드를 전부 작성해야 한다. SSE는 HTTP 위에서 동작하고, 클라이언트(브라우저)가 자동 재연결을 처리하며, 단방향 스트림이라 구현이 단순하다.

알림 시스템, 실시간 로그 스트리밍, 주식 시세, 진행률 표시 같은 용도에서 실제로 많이 쓴다. 양방향이 필요하지 않은 이상 WebSocket보다 SSE가 구현과 운영 모두 덜 복잡하다.

SSE는 `text/event-stream` 콘텐츠 타입으로 HTTP 응답을 열어두고, 아래 형식으로 데이터를 흘려보낸다.

```
id: 1
event: message
data: {"type":"notification","content":"새 댓글이 달렸습니다"}

id: 2
event: heartbeat
data: ping

```

각 이벤트는 빈 줄 두 개로 구분된다. 브라우저는 `EventSource` API로 이 스트림을 소비한다.

## Spring MVC: SseEmitter

### 기본 구조

Spring MVC에서는 `SseEmitter`를 반환하면 된다. 컨트롤러가 `SseEmitter`를 반환하는 순간 HTTP 응답은 열린 상태로 유지되고, 다른 스레드에서 `emitter.send()`를 호출할 때마다 데이터가 나간다.

```java
@RestController
@RequestMapping("/api/sse")
public class SseController {

    private final SseEmitterService sseEmitterService;

    @GetMapping(value = "/subscribe/{userId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter subscribe(@PathVariable String userId) {
        // 타임아웃 0L = 무한 대기 (주의사항은 아래 참조)
        SseEmitter emitter = new SseEmitter(30_000L);
        sseEmitterService.register(userId, emitter);
        return emitter;
    }
}
```

```java
@Service
public class SseEmitterService {

    // ConcurrentHashMap 사용 필수. HashMap 쓰면 동시성 문제 발생
    private final Map<String, SseEmitter> emitters = new ConcurrentHashMap<>();

    public void register(String userId, SseEmitter emitter) {
        emitter.onCompletion(() -> emitters.remove(userId));
        emitter.onTimeout(() -> emitters.remove(userId));
        emitter.onError(e -> emitters.remove(userId));

        emitters.put(userId, emitter);

        // 구독 직후 초기 이벤트 전송 (연결 확인용)
        try {
            emitter.send(SseEmitter.event()
                    .id("0")
                    .name("connect")
                    .data("connected"));
        } catch (IOException e) {
            emitters.remove(userId);
        }
    }

    public void sendToUser(String userId, Object data) {
        SseEmitter emitter = emitters.get(userId);
        if (emitter == null) return;

        try {
            emitter.send(SseEmitter.event()
                    .id(String.valueOf(System.currentTimeMillis()))
                    .name("notification")
                    .data(data, MediaType.APPLICATION_JSON));
        } catch (IOException e) {
            emitters.remove(userId);
            emitter.completeWithError(e);
        }
    }
}
```

### 타임아웃 설정 주의사항

`new SseEmitter(Long timeout)` 생성자에 넘기는 값이 실제로 어디서 동작하는지 이해하지 못하면 설정이 의미 없어진다.

Spring MVC는 기본적으로 비동기 처리를 서블릿 컨테이너(Tomcat)에 위임한다. `SseEmitter`를 반환하면 내부적으로 `AsyncContext`를 시작하고, 타임아웃은 이 `AsyncContext`에 걸린다. 타임아웃이 지나면 Tomcat이 `onTimeout` 콜백을 호출한다.

```java
// 타임아웃별 동작 정리

// 0L: 무한 대기. Nginx 같은 프록시의 read_timeout이 먼저 끊음
SseEmitter emitter = new SseEmitter(0L);

// 30_000L: 30초. 클라이언트가 자동으로 재연결하므로 짧아도 무방
SseEmitter emitter = new SseEmitter(30_000L);

// -1L: Tomcat 기본값 사용 (보통 10초). 설정하지 않은 것과 같음
SseEmitter emitter = new SseEmitter(-1L);
```

Tomcat의 기본 비동기 타임아웃(10초)이 SseEmitter 생성자 값보다 우선할 수 있다. `application.yml`에서 서블릿 비동기 타임아웃을 별도로 설정해야 한다.

```yaml
server:
  servlet:
    async:
      timeout: 60000  # 밀리초. SseEmitter 타임아웃과 맞춰야 함
```

타임아웃 후 클라이언트 재연결을 유도하려면 `onTimeout`에서 `emitter.complete()`를 명시적으로 호출해야 한다. 호출하지 않으면 클라이언트가 재연결을 시도하다 이상한 상태에 빠진다.

```java
emitter.onTimeout(() -> {
    emitters.remove(userId);
    emitter.complete();  // 명시적으로 완료 처리
});
```

### 다중 구독자 브로드캐스트와 스레드 격리

모든 구독자에게 같은 이벤트를 보내는 브로드캐스트는 단순해 보이지만 스레드 문제가 숨어 있다.

`emitter.send()`는 내부적으로 `HttpServletResponse`의 `OutputStream`에 쓰는 작업이다. 이 작업이 느린 클라이언트(네트워크 지연, 버퍼 꽉 참)를 만나면 블로킹된다. 루프에서 순서대로 send를 호출하면 느린 구독자 하나가 전체 브로드캐스트를 지연시킨다.

```java
// 잘못된 방법: 느린 클라이언트가 전체를 블로킹
public void broadcast(Object data) {
    for (Map.Entry<String, SseEmitter> entry : emitters.entrySet()) {
        try {
            entry.getValue().send(data);  // 여기서 블로킹 발생 가능
        } catch (IOException e) {
            emitters.remove(entry.getKey());
        }
    }
}
```

각 `send()`를 별도 스레드에서 실행하면 격리된다.

```java
@Service
public class SseEmitterService {

    private final Map<String, SseEmitter> emitters = new ConcurrentHashMap<>();
    // 브로드캐스트 전용 스레드 풀. 무한정 생성 막기 위해 크기 제한
    private final Executor broadcastExecutor = Executors.newFixedThreadPool(10);

    public void broadcast(String eventName, Object data) {
        List<String> deadEmitters = new ArrayList<>();

        emitters.forEach((userId, emitter) ->
            broadcastExecutor.execute(() -> {
                try {
                    emitter.send(SseEmitter.event()
                            .name(eventName)
                            .data(data, MediaType.APPLICATION_JSON));
                } catch (IOException e) {
                    deadEmitters.add(userId);
                    emitter.completeWithError(e);
                }
            })
        );

        // 전송 실패한 emitter 정리
        deadEmitters.forEach(emitters::remove);
    }
}
```

구독자가 수백 명을 넘어가면 고정 크기 스레드 풀도 병목이 된다. 이 경우 Spring WebFlux로 전환하거나, Virtual Thread(Java 21+)를 쓰는 편이 낫다.

```java
// Java 21: Virtual Thread 기반 Executor
private final Executor broadcastExecutor = Executors.newVirtualThreadPerTaskExecutor();
```

## Spring WebFlux: Flux<ServerSentEvent>

### 기본 구조

WebFlux에서는 `Flux<ServerSentEvent<T>>`를 반환한다. 논블로킹이기 때문에 SseEmitter처럼 별도 스레드 관리를 직접 하지 않아도 된다.

```java
@RestController
@RequestMapping("/api/sse")
public class SseController {

    private final SseFluxService sseFluxService;

    @GetMapping(value = "/subscribe/{userId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> subscribe(@PathVariable String userId) {
        return sseFluxService.getStream(userId);
    }
}
```

```java
@Service
public class SseFluxService {

    // Sinks.Many: WebFlux에서 프로그래밍 방식으로 Flux에 데이터를 밀어넣는 API
    private final Map<String, Sinks.Many<String>> sinks = new ConcurrentHashMap<>();

    public Flux<ServerSentEvent<String>> getStream(String userId) {
        Sinks.Many<String> sink = sinks.computeIfAbsent(userId,
                id -> Sinks.many().multicast().onBackpressureBuffer());

        return sink.asFlux()
                .map(data -> ServerSentEvent.<String>builder()
                        .id(String.valueOf(System.currentTimeMillis()))
                        .event("notification")
                        .data(data)
                        .build())
                .doOnCancel(() -> sinks.remove(userId))
                .doOnTerminate(() -> sinks.remove(userId));
    }

    public void sendToUser(String userId, String data) {
        Sinks.Many<String> sink = sinks.get(userId);
        if (sink == null) return;

        Sinks.EmitResult result = sink.tryEmitNext(data);
        if (result.isFailure()) {
            sinks.remove(userId);
        }
    }
}
```

### Heartbeat 처리

네트워크 중간 장비(로드밸런서, Nginx)가 유휴 연결을 끊는 문제를 막으려면 주기적으로 heartbeat를 보내야 한다.

```java
// MVC: 스케줄러로 heartbeat 전송
@Scheduled(fixedDelay = 15_000)
public void sendHeartbeat() {
    emitters.forEach((userId, emitter) -> {
        try {
            emitter.send(SseEmitter.event().name("heartbeat").data("ping"));
        } catch (IOException e) {
            emitters.remove(userId);
        }
    });
}

// WebFlux: Flux.interval로 heartbeat 병합
public Flux<ServerSentEvent<String>> getStream(String userId) {
    Flux<ServerSentEvent<String>> heartbeat = Flux.interval(Duration.ofSeconds(15))
            .map(tick -> ServerSentEvent.<String>builder()
                    .event("heartbeat")
                    .data("ping")
                    .build());

    Flux<ServerSentEvent<String>> dataStream = sink.asFlux()
            .map(data -> ServerSentEvent.<String>builder()
                    .event("notification")
                    .data(data)
                    .build());

    return Flux.merge(dataStream, heartbeat);
}
```

## 수평 확장: Redis Pub/Sub 연동

단일 서버에서는 `ConcurrentHashMap`으로 emitter를 관리하면 된다. 서버를 여러 대 띄우면 문제가 생긴다. A 서버에 연결된 사용자에게 B 서버에서 이벤트를 보내려 해도, B 서버의 Map에 그 emitter가 없다.

Redis Pub/Sub으로 서버 간 이벤트를 중계하면 해결된다.

```
[이벤트 발생 서버 B]
     │
     ▼
Redis Pub/Sub (채널: "sse-events")
     │
     ├── 서버 A (구독자 연결 있음) → emitter.send()
     └── 서버 B (구독자 없음) → 무시
```

```java
// 이벤트 발행 (어느 서버에서든 호출)
@Service
public class SseEventPublisher {

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    public void publish(String userId, Object event) {
        try {
            SseEvent sseEvent = new SseEvent(userId, objectMapper.writeValueAsString(event));
            redisTemplate.convertAndSend("sse-events", objectMapper.writeValueAsString(sseEvent));
        } catch (JsonProcessingException e) {
            throw new RuntimeException("SSE 이벤트 직렬화 실패", e);
        }
    }
}
```

```java
// Redis 메시지 수신 및 로컬 emitter로 전달
@Component
public class SseRedisSubscriber {

    private final SseEmitterService sseEmitterService;
    private final ObjectMapper objectMapper;

    @Bean
    public MessageListenerAdapter messageListenerAdapter() {
        return new MessageListenerAdapter(this, "onMessage");
    }

    @Bean
    public RedisMessageListenerContainer container(
            RedisConnectionFactory connectionFactory,
            MessageListenerAdapter listenerAdapter) {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.addMessageListener(listenerAdapter, new PatternTopic("sse-events"));
        return container;
    }

    public void onMessage(String message, String pattern) {
        try {
            SseEvent event = objectMapper.readValue(message, SseEvent.class);
            // 이 서버에 해당 userId의 emitter가 있을 때만 전송
            sseEmitterService.sendToUser(event.getUserId(), event.getData());
        } catch (JsonProcessingException e) {
            log.error("SSE Redis 메시지 파싱 실패", e);
        }
    }
}
```

Redis Pub/Sub은 메시지를 영속하지 않는다. 구독자가 없을 때 발행된 메시지는 사라진다. 수신 보장이 필요하면 Redis Stream이나 Kafka를 써야 한다. 단순 실시간 알림 정도라면 Pub/Sub으로 충분하다.

## Spring Security 환경에서 인증 처리

SSE 엔드포인트에 인증을 붙이는 건 일반 REST API보다 까다롭다. 브라우저의 `EventSource`는 커스텀 헤더를 설정하는 API를 제공하지 않는다. Authorization 헤더로 JWT를 전달하는 방식이 동작하지 않는다.

선택지는 두 가지다: 쿠키에 담거나, 쿼리 파라미터로 넘기거나.

### 쿠키 방식

`HttpOnly` 쿠키에 JWT를 담으면 `EventSource` 연결 시 브라우저가 자동으로 쿠키를 전송한다. CSRF 토큰과 함께 쓰거나 SameSite 설정을 맞추면 보안 측면에서 더 낫다.

```java
// Spring Security 설정에서 쿠키 기반 JWT 필터 추가
@Component
public class CookieJwtAuthFilter extends OncePerRequestFilter {

    private final JwtProvider jwtProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        // 쿠키에서 JWT 추출
        String token = Arrays.stream(
                Optional.ofNullable(request.getCookies()).orElse(new Cookie[0]))
                .filter(c -> "access_token".equals(c.getName()))
                .findFirst()
                .map(Cookie::getValue)
                .orElse(null);

        if (token != null && jwtProvider.validate(token)) {
            Authentication auth = jwtProvider.getAuthentication(token);
            SecurityContextHolder.getContext().setAuthentication(auth);
        }

        filterChain.doFilter(request, response);
    }
}
```

### 쿼리 파라미터 방식

쿠키를 쓸 수 없는 환경(모바일 앱, 서버-서버 통신)에서는 쿼리 파라미터로 토큰을 받는다.

```
GET /api/sse/subscribe/user123?token=eyJhbGciOiJIUzI1NiJ9...
```

로그에 토큰이 남는다는 단점이 있다. 토큰 유효기간을 짧게 잡고, SSE 연결 전용 단기 토큰을 별도 발급하는 식으로 보완한다.

```java
@Component
public class QueryParamJwtAuthFilter extends OncePerRequestFilter {

    private final JwtProvider jwtProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        // SSE 엔드포인트에만 쿼리 파라미터 인증 적용
        if (request.getRequestURI().startsWith("/api/sse/")) {
            String token = request.getParameter("token");
            if (token != null && jwtProvider.validate(token)) {
                Authentication auth = jwtProvider.getAuthentication(token);
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }

        filterChain.doFilter(request, response);
    }
}
```

```java
// Security 설정
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf
                // SSE 엔드포인트는 CSRF 비활성화 (EventSource는 CSRF 토큰 전송 불가)
                .ignoringRequestMatchers("/api/sse/**"))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/sse/**").authenticated()
                .anyRequest().authenticated())
            .addFilterBefore(cookieJwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
            .addFilterBefore(queryParamJwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
```

WebFlux 환경에서는 `SecurityContextHolder` 대신 `ReactiveSecurityContextHolder`를 사용하고, 필터는 `WebFilter`를 구현한다.

## Nginx 프록시 설정

SSE는 HTTP/1.1의 chunked transfer encoding을 사용한다. Nginx 기본 설정은 프록시 응답을 버퍼링하기 때문에 그대로 두면 이벤트가 쌓였다가 한꺼번에 클라이언트에 도달하거나 아예 전달이 안 된다.

```nginx
upstream spring_backend {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name example.com;

    location /api/sse/ {
        proxy_pass http://spring_backend;

        # SSE 핵심 설정
        proxy_buffering off;              # 응답 버퍼링 비활성화 (필수)
        proxy_cache off;                  # 캐시 비활성화
        proxy_http_version 1.1;           # chunked transfer encoding 사용
        proxy_set_header Connection '';   # keep-alive 연결 유지

        # 타임아웃 설정
        proxy_read_timeout 3600s;         # 1시간. 기본값 60s면 연결이 끊김
        proxy_send_timeout 3600s;
        proxy_connect_timeout 75s;

        # 헤더 전달
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS (필요한 경우)
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    location / {
        proxy_pass http://spring_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

`proxy_buffering off`가 없으면 데이터가 클라이언트에 즉시 전달되지 않는다. SSE 문제 디버깅할 때 제일 먼저 확인해야 할 설정이다.

`proxy_read_timeout`의 기본값은 60초다. Heartbeat 간격보다 길게 설정해야 한다. 예를 들어 15초마다 heartbeat를 보내면 `proxy_read_timeout`은 최소 30~60초 이상으로 잡아야 한다.

로드밸런서 뒤에 여러 서버를 둘 때는 SSE 연결이 같은 서버에 유지되도록 sticky session을 설정하거나, Redis Pub/Sub으로 서버 간 이벤트를 중계해야 한다.

```nginx
# sticky session: IP 해시 방식
upstream spring_backend {
    ip_hash;
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    keepalive 64;
}
```

## 실제 운영에서 자주 만나는 문제

**클라이언트가 재연결을 무한 반복한다**

서버가 `complete()` 없이 연결만 끊으면 브라우저 `EventSource`가 즉시 재연결을 시도한다. 타임아웃 시 `emitter.complete()`를 명시적으로 호출해야 한다. 재연결 간격은 `retry:` 필드로 조정할 수 있다.

```java
emitter.send(SseEmitter.event().reconnectTime(3000L).data(""));  // 3초 후 재연결
```

**메모리 누수**

연결이 끊겼는데 `emitters` Map에서 제거되지 않으면 메모리가 계속 쌓인다. `onCompletion`, `onTimeout`, `onError` 콜백 세 개를 모두 등록해야 한다. `send()` 실패 시에도 Map에서 제거하는 코드가 있어야 한다.

**첫 이벤트가 바로 안 온다**

브라우저가 응답을 완전히 수신했다고 판단하기 전까지 이벤트를 렌더링하지 않는 경우가 있다. 구독 즉시 더미 이벤트를 하나 보내면 연결이 열렸음을 확인할 수 있고, 첫 데이터 수신이 빨라진다.

**HTTP/2 환경**

HTTP/2는 단일 연결로 다중 스트림을 지원한다. SSE와 HTTP/2를 함께 쓰면 브라우저당 동시 SSE 연결 수 제한(HTTP/1.1은 도메인당 6개)이 사라진다. Nginx에서 HTTP/2를 활성화하면 별도 작업 없이 적용된다. 단, HTTP/2 환경에서 `Connection: keep-alive` 헤더는 무시되므로 Nginx 설정에서 `proxy_http_version 1.1`이 백엔드 통신에는 여전히 필요하다.
