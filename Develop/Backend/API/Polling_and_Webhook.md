---
title: Polling과 Webhook
tags: [polling, webhook, short-polling, long-polling, callback, API]
updated: 2026-03-26
---

# Polling과 Webhook

## Polling이란

클라이언트가 서버에 주기적으로 요청을 보내서 새로운 데이터가 있는지 확인하는 방식이다. 서버는 요청을 받을 때마다 현재 상태를 응답한다.

```
클라이언트 → 서버: "새 데이터 있어?"
서버 → 클라이언트: "없음"
(3초 후)
클라이언트 → 서버: "새 데이터 있어?"
서버 → 클라이언트: "없음"
(3초 후)
클라이언트 → 서버: "새 데이터 있어?"
서버 → 클라이언트: "있음, 여기"
```

구현이 단순하다는 게 가장 큰 장점이고, 대부분의 경우 첫 번째 선택지가 된다.

## Webhook이란

서버에서 이벤트가 발생하면 미리 등록된 URL로 HTTP 요청을 보내는 방식이다. 클라이언트가 물어보는 게 아니라 서버가 알려준다.

```
클라이언트 → 서버: "이 URL로 알려줘" (등록)
(이벤트 발생)
서버 → 클라이언트: POST /webhook {event: "payment_complete", data: {...}}
```

GitHub의 Push 이벤트 알림, Stripe의 결제 완료 알림, Slack의 메시지 이벤트가 대표적인 Webhook 사용 예다.

---

## Short Polling

가장 기본적인 Polling 방식이다. 일정 간격으로 요청을 보내고, 서버는 즉시 응답한다.

### Spring Boot 서버

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderRepository orderRepository;

    public OrderController(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @GetMapping("/{orderId}/status")
    public ResponseEntity<OrderStatus> getOrderStatus(@PathVariable Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new OrderNotFoundException(orderId));

        return ResponseEntity.ok(new OrderStatus(order.getStatus(), order.getUpdatedAt()));
    }
}
```

### 클라이언트 (JavaScript)

```javascript
async function pollOrderStatus(orderId) {
    const INTERVAL = 3000; // 3초
    const MAX_ATTEMPTS = 60; // 최대 3분
    let attempts = 0;

    while (attempts < MAX_ATTEMPTS) {
        const response = await fetch(`/api/orders/${orderId}/status`);
        const data = await response.json();

        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            return data;
        }

        attempts++;
        await new Promise(resolve => setTimeout(resolve, INTERVAL));
    }

    throw new Error('Polling timeout');
}
```

### Short Polling의 문제

3초 간격으로 100명이 동시에 주문 상태를 확인하면, 서버는 1분에 2,000번의 요청을 처리해야 한다. 대부분의 응답은 "변경 없음"이다. DB 커넥션도 매 요청마다 잡히고, 네트워크 비용도 계속 발생한다.

간격을 늘리면 서버 부하는 줄지만, 상태 변경을 감지하는 데 시간이 오래 걸린다. 이 트레이드오프에서 벗어나려면 Long Polling을 쓴다.

---

## Long Polling

서버가 새 데이터가 생길 때까지 응답을 보류하는 방식이다. 클라이언트는 요청을 보내고, 서버는 데이터가 준비될 때까지 커넥션을 열어둔다.

### Spring Boot 서버 (DeferredResult 사용)

```java
@RestController
@RequestMapping("/api/orders")
public class OrderLongPollingController {

    // orderId → 대기 중인 클라이언트 목록
    private final ConcurrentHashMap<Long, List<DeferredResult<OrderStatus>>> waitingClients
            = new ConcurrentHashMap<>();

    @GetMapping("/{orderId}/status/poll")
    public DeferredResult<OrderStatus> pollOrderStatus(@PathVariable Long orderId) {
        // 30초 타임아웃 설정
        DeferredResult<OrderStatus> result = new DeferredResult<>(30_000L);

        waitingClients.computeIfAbsent(orderId, k -> new CopyOnWriteArrayList<>()).add(result);

        // 타임아웃되면 목록에서 제거하고 204 응답
        result.onTimeout(() -> {
            waitingClients.getOrDefault(orderId, List.of()).remove(result);
            result.setResult(null);
        });

        result.onCompletion(() -> {
            waitingClients.getOrDefault(orderId, List.of()).remove(result);
        });

        return result;
    }

    // 주문 상태가 변경되면 대기 중인 클라이언트에게 알림
    public void notifyStatusChange(Long orderId, OrderStatus status) {
        List<DeferredResult<OrderStatus>> clients = waitingClients.remove(orderId);
        if (clients != null) {
            clients.forEach(client -> client.setResult(status));
        }
    }
}
```

### 클라이언트

```javascript
async function longPollOrderStatus(orderId) {
    while (true) {
        try {
            const response = await fetch(`/api/orders/${orderId}/status/poll`);

            if (response.status === 204) {
                // 타임아웃, 재연결
                continue;
            }

            const data = await response.json();
            if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                return data;
            }
            // 중간 상태면 다시 연결
        } catch (error) {
            // 네트워크 에러 시 잠시 대기 후 재연결
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
}
```

### Long Polling 사용 시 주의할 점

**스레드 점유 문제**: 전통적인 서블릿 방식에서 Long Polling을 구현하면 대기 중인 요청마다 스레드를 하나씩 잡는다. `DeferredResult`나 `CompletableFuture`를 써서 비동기로 처리해야 한다. 그렇지 않으면 동시 접속자가 늘어날 때 스레드 풀이 고갈된다.

**타임아웃 설정**: 프록시(Nginx, ALB 등)의 타임아웃보다 짧게 설정해야 한다. Nginx 기본 `proxy_read_timeout`이 60초인데, Long Polling 타임아웃을 90초로 잡으면 프록시가 먼저 끊어버린다. 보통 서버 타임아웃은 25~30초로 잡는다.

**로드밸런서**: Sticky Session이 없으면, 클라이언트가 재연결할 때 다른 서버로 갈 수 있다. 이벤트 발생 서버와 대기 중인 클라이언트가 연결된 서버가 다르면 알림이 전달되지 않는다. Redis Pub/Sub 같은 걸로 서버 간 이벤트를 전파해야 한다.

---

## Webhook 수신 서버 구현

### 기본 구조 (Spring Boot)

```java
@RestController
@RequestMapping("/webhooks")
public class WebhookController {

    private final WebhookEventProcessor eventProcessor;

    public WebhookController(WebhookEventProcessor eventProcessor) {
        this.eventProcessor = eventProcessor;
    }

    @PostMapping("/payment")
    public ResponseEntity<Void> handlePaymentWebhook(
            @RequestHeader("X-Webhook-Signature") String signature,
            @RequestBody String rawBody) {

        // 1. 서명 검증
        if (!verifySignature(rawBody, signature)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        // 2. 비동기 처리 (즉시 200 응답)
        eventProcessor.processAsync(rawBody);

        // 3. 빠르게 200 반환
        return ResponseEntity.ok().build();
    }
}
```

Webhook 수신 서버에서 가장 중요한 건 **빠르게 200을 반환하는 것**이다. 대부분의 Webhook 발신자는 응답이 느리면 타임아웃 처리하고 재시도한다. 실제 비즈니스 로직은 비동기로 처리한다.

### 서명 검증

Webhook 요청이 실제로 해당 서비스에서 보낸 건지 확인해야 한다. 검증 없이 받으면 누구든 해당 엔드포인트로 가짜 요청을 보낼 수 있다.

```java
@Component
public class WebhookSignatureVerifier {

    @Value("${webhook.secret}")
    private String webhookSecret;

    public boolean verify(String payload, String receivedSignature) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec secretKey = new SecretKeySpec(
                    webhookSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(secretKey);

            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            String computed = "sha256=" + Hex.encodeHexString(hash);

            // 타이밍 공격 방지를 위해 MessageDigest.isEqual 사용
            return MessageDigest.isEqual(
                    computed.getBytes(StandardCharsets.UTF_8),
                    receivedSignature.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            return false;
        }
    }
}
```

주의할 점:

- `String.equals()` 대신 `MessageDigest.isEqual()`을 써야 한다. 일반 문자열 비교는 앞에서부터 한 글자씩 비교하기 때문에, 응답 시간 차이로 서명 값을 유추할 수 있다(타이밍 공격).
- **raw body를 그대로 검증**해야 한다. JSON 파싱 후 다시 직렬화하면 키 순서나 공백이 달라져서 서명이 안 맞는다. `@RequestBody String rawBody`로 원문 그대로 받아서 검증한다.

### 멱등성 처리

Webhook 발신자는 응답을 못 받으면 같은 이벤트를 여러 번 보낸다. 같은 이벤트를 두 번 처리하면 결제가 두 번 되는 것 같은 문제가 생긴다.

```java
@Service
public class WebhookEventProcessor {

    private final WebhookEventRepository eventRepository;
    private final PaymentService paymentService;

    @Transactional
    public void process(WebhookEvent event) {
        // 이미 처리한 이벤트인지 확인
        if (eventRepository.existsByEventId(event.getEventId())) {
            log.info("이미 처리된 이벤트: {}", event.getEventId());
            return;
        }

        // 이벤트 저장 (중복 방지용)
        eventRepository.save(new ProcessedEvent(event.getEventId(), Instant.now()));

        // 실제 처리
        switch (event.getType()) {
            case "payment.completed":
                paymentService.completePayment(event.getData());
                break;
            case "payment.failed":
                paymentService.handleFailure(event.getData());
                break;
        }
    }
}
```

`event_id`에 유니크 인덱스를 걸어서, DB 레벨에서 중복을 차단한다. 애플리케이션 레벨 체크만으로는 동시에 같은 이벤트가 들어오면 둘 다 통과할 수 있다.

---

## 재시도 처리

### 발신 측 (내가 Webhook을 보내는 경우)

```java
@Component
public class WebhookSender {

    private final RestTemplate restTemplate;
    private final WebhookRetryRepository retryRepository;

    // 재시도 간격: 1분, 5분, 30분, 2시간, 24시간
    private static final long[] RETRY_INTERVALS = {
            60_000, 300_000, 1_800_000, 7_200_000, 86_400_000
    };

    public void send(String url, String payload, String secret) {
        String signature = sign(payload, secret);

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("X-Webhook-Signature", signature);
            headers.set("X-Webhook-Event-Id", UUID.randomUUID().toString());

            HttpEntity<String> entity = new HttpEntity<>(payload, headers);
            ResponseEntity<String> response = restTemplate.postForEntity(url, entity, String.class);

            if (!response.getStatusCode().is2xxSuccessful()) {
                scheduleRetry(url, payload, secret, 0);
            }
        } catch (Exception e) {
            scheduleRetry(url, payload, secret, 0);
        }
    }

    private void scheduleRetry(String url, String payload, String secret, int attempt) {
        if (attempt >= RETRY_INTERVALS.length) {
            log.error("Webhook 재시도 횟수 초과: url={}", url);
            // 알림 발송 (Slack, 이메일 등)
            return;
        }

        retryRepository.save(new WebhookRetry(
                url, payload, secret, attempt,
                Instant.now().plusMillis(RETRY_INTERVALS[attempt])
        ));
    }
}
```

재시도 간격을 점점 늘리는 게 중요하다(Exponential Backoff). 상대 서버가 죽어있는데 1초마다 계속 보내면 상대방 서버가 복구되자마자 밀린 요청이 몰려서 또 죽는다.

### 수신 측 주의사항

발신자가 재시도를 보내는데, 이전 요청은 사실 성공했고 응답만 못 받은 경우가 있다. 수신 측에서 멱등성 처리를 안 하면 같은 작업이 중복 실행된다. 반드시 `event_id` 기반 중복 체크를 해야 한다.

---

## Polling에서 Webhook으로 전환할 때 고려사항

### 1. 전환 기간에는 둘 다 운영해야 한다

Webhook을 붙였다고 바로 Polling을 끄면 안 된다. Webhook이 실패하거나 누락될 수 있으니, 전환 기간에는 Polling을 fallback으로 유지한다.

```java
@Service
public class OrderStatusService {

    private final WebhookSubscription webhookSubscription;

    public void checkOrderStatus(Long orderId) {
        if (webhookSubscription.isActive(orderId)) {
            // Webhook이 정상 동작 중이면 대기
            // 일정 시간 내에 Webhook이 안 오면 Polling fallback
            schedulePollingFallback(orderId, Duration.ofMinutes(5));
        } else {
            // Webhook이 없으면 기존 Polling 방식
            pollOrderStatus(orderId);
        }
    }
}
```

### 2. Webhook 수신 서버의 가용성

Polling은 내가 능동적으로 가져오는 거라 내 서버만 살아있으면 된다. Webhook은 수신 서버가 죽어있으면 이벤트를 놓친다. Webhook 수신 서버가 죽었을 때를 대비한 복구 방법이 있어야 한다.

- 발신자가 재시도를 지원하는지 확인
- 재시도 횟수가 소진된 후의 이벤트를 어떻게 복구할지 (수동 재전송 API, 이벤트 목록 조회 API 등)
- 발신자의 대시보드에서 실패한 Webhook을 재전송할 수 있는지

### 3. 방화벽과 네트워크

Polling은 아웃바운드 요청이라 대부분 방화벽에 걸리지 않는다. Webhook은 인바운드 요청을 받아야 하니까, 수신 서버가 외부에서 접근 가능해야 한다. 내부망에 있는 서버라면 별도의 프록시를 두거나 VPN 터널을 설정해야 한다.

### 4. 순서 보장

Webhook은 이벤트 발생 순서대로 도착한다는 보장이 없다. 네트워크 상황에 따라 먼저 보낸 요청이 나중에 도착할 수 있다. 순서가 중요한 경우에는 이벤트에 타임스탬프나 시퀀스 번호를 포함하고, 수신 측에서 순서를 맞춰야 한다.

```java
@Transactional
public void processOrderEvent(WebhookEvent event) {
    Order order = orderRepository.findById(event.getOrderId()).orElseThrow();

    // 이전 이벤트보다 오래된 이벤트면 무시
    if (event.getTimestamp().isBefore(order.getLastEventTimestamp())) {
        log.warn("순서가 맞지 않는 이벤트 무시: orderId={}, eventTime={}, lastTime={}",
                event.getOrderId(), event.getTimestamp(), order.getLastEventTimestamp());
        return;
    }

    order.updateStatus(event.getStatus());
    order.setLastEventTimestamp(event.getTimestamp());
    orderRepository.save(order);
}
```

---

## 선택 기준

### Polling이 맞는 경우

- 이벤트 빈도가 높고 거의 매번 데이터가 있는 경우 (예: 주식 시세 — 어차피 매 요청마다 새 데이터가 있다)
- 수신 서버를 외부에 노출할 수 없는 환경
- 상대 시스템이 Webhook을 지원하지 않는 경우
- 구현 복잡도를 낮추고 싶은 경우 (초기 프로토타입, MVP)

### Webhook이 맞는 경우

- 이벤트가 드물게 발생하는 경우 (예: 결제 완료 — 하루에 몇 건 안 되는데 매초 Polling하면 낭비다)
- 실시간에 가까운 반응이 필요한 경우
- 서버 리소스를 아껴야 하는 경우

### 둘 다 쓰는 경우

실무에서는 Webhook을 기본으로 쓰되, Polling을 보조 수단으로 두는 패턴이 많다. Webhook이 누락됐을 때 Polling으로 상태를 맞추는 방식이다. Stripe, GitHub 같은 대형 서비스들도 Webhook과 함께 이벤트 목록 조회 API를 제공하는 이유가 이것이다.

```java
// Webhook으로 실시간 이벤트 수신
@PostMapping("/webhooks/payment")
public ResponseEntity<Void> onPaymentEvent(...) {
    // 즉시 처리
}

// 5분마다 누락된 이벤트가 없는지 Polling으로 확인
@Scheduled(fixedRate = 300_000)
public void reconcilePaymentEvents() {
    Instant lastChecked = stateStore.getLastCheckedTime();
    List<PaymentEvent> events = paymentApi.getEvents(lastChecked, Instant.now());

    for (PaymentEvent event : events) {
        if (!eventRepository.existsByEventId(event.getId())) {
            log.warn("Webhook 누락된 이벤트 발견: {}", event.getId());
            eventProcessor.process(event);
        }
    }

    stateStore.updateLastCheckedTime(Instant.now());
}
```

이 조합이 가장 안정적이다. Webhook으로 실시간성을 확보하고, Polling으로 데이터 정합성을 맞춘다.
