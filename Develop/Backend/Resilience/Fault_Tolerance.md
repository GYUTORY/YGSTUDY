---
title: 장애 대응 패턴 (Fault Tolerance)
tags: [backend, resilience, circuit-breaker, retry, timeout, fallback, health-check, resilience4j]
updated: 2026-01-18
---

# 장애 대응 패턴 (Fault Tolerance)

## 개요

분산 시스템에서 장애는 언제든 발생한다. 외부 API가 느려지거나 DB 연결이 끊기거나 네트워크가 불안정해진다. 이런 장애가 전체 시스템으로 전파되는 것을 막아야 한다. Circuit Breaker, Retry, Timeout, Fallback을 조합해서 사용한다.

### 왜 필요한가

**문제 상황:**

**시나리오:**
주문 서비스가 결제 API를 호출한다. 결제 API가 갑자기 느려진다 (응답 시간 30초).

**연쇄 장애:**
```
주문 요청 → 결제 API 호출 (30초 대기)
주문 요청 → 결제 API 호출 (30초 대기)
주문 요청 → 결제 API 호출 (30초 대기)
...
```

**결과:**
- 모든 주문 스레드가 30초씩 대기
- 스레드 풀 고갈
- 새로운 주문 요청 불가
- 전체 서비스 다운

**결제 API 하나의 문제가 전체 시스템을 마비시킨다.**

**장애 대응 패턴 적용:**
- **Timeout**: 3초 내 응답 없으면 즉시 실패
- **Circuit Breaker**: 연속 실패 시 API 호출 차단
- **Retry**: 일시적 오류는 재시도
- **Fallback**: 실패 시 대체 동작

**결과:**
결제 API 문제가 있어도 주문 서비스는 정상 동작한다.

## Circuit Breaker

### 개념

전기 회로 차단기처럼 동작한다. 연속으로 실패하면 회로를 차단한다. 외부 시스템이 복구될 시간을 준다.

**3가지 상태:**

**CLOSED (정상):**
- 요청을 정상적으로 전달
- 실패율 모니터링

**OPEN (차단):**
- 모든 요청을 즉시 차단
- Fallback 실행
- 일정 시간 대기 (Wait Duration)

**HALF_OPEN (반개방):**
- 일부 요청만 전달 (테스트)
- 성공하면 CLOSED로
- 실패하면 다시 OPEN으로

### Resilience4j 설정

**의존성 추가 (Spring Boot):**
```xml
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
    <version>2.1.0</version>
</dependency>
```

**application.yml:**
```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentService:
        # 슬라이딩 윈도우 크기 (최근 N개 요청)
        sliding-window-size: 10
        # 슬라이딩 윈도우 타입 (COUNT_BASED / TIME_BASED)
        sliding-window-type: COUNT_BASED
        # 실패율 임계값 (50%)
        failure-rate-threshold: 50
        # 최소 호출 수 (통계 계산 전 필요한 최소 요청 수)
        minimum-number-of-calls: 5
        # OPEN 상태 유지 시간
        wait-duration-in-open-state: 10s
        # HALF_OPEN에서 허용할 요청 수
        permitted-number-of-calls-in-half-open-state: 3
        # 실패로 간주할 예외
        record-exceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException
        # 무시할 예외 (실패로 카운트하지 않음)
        ignore-exceptions:
          - com.example.BusinessException
```

**코드:**
```java
@Service
public class PaymentService {
    
    private final RestTemplate restTemplate;
    
    @CircuitBreaker(name = "paymentService", fallbackMethod = "paymentFallback")
    public PaymentResponse processPayment(PaymentRequest request) {
        // 외부 결제 API 호출
        return restTemplate.postForObject(
            "https://payment-api.com/process",
            request,
            PaymentResponse.class
        );
    }
    
    // Fallback 메서드
    private PaymentResponse paymentFallback(PaymentRequest request, Exception e) {
        log.error("Payment failed, using fallback", e);
        return new PaymentResponse("PENDING", "결제 처리 중입니다");
    }
}
```

### 동작 예시

**시나리오:**
```
요청 1-4: 성공 (CLOSED 상태 유지)
요청 5: 실패 (실패율 10%)
요청 6: 실패 (실패율 20%)
요청 7: 실패 (실패율 30%)
요청 8: 실패 (실패율 40%)
요청 9: 실패 (실패율 50%)
요청 10: 실패 (실패율 60%) → 임계값 초과

상태: CLOSED → OPEN

요청 11-100: 즉시 차단, Fallback 실행 (10초간)

10초 후: HALF_OPEN

요청 101-103: 테스트 요청 (3개)
  - 모두 성공 → CLOSED
  - 하나라도 실패 → 다시 OPEN
```

## Retry

### 개념

일시적인 오류는 재시도하면 성공할 수 있다. 네트워크 지연, 일시적 과부하 등.

**주의:**
무한 재시도는 위험하다. 최대 횟수와 대기 시간을 설정한다.

### Exponential Backoff

재시도 간격을 지수적으로 증가시킨다.

**예시:**
- 1차 재시도: 1초 대기
- 2차 재시도: 2초 대기
- 3차 재시도: 4초 대기
- 4차 재시도: 8초 대기

**이유:**
- 외부 시스템에 부하를 주지 않음
- 복구 시간 확보
- Thundering Herd 방지

### Resilience4j 설정

**application.yml:**
```yaml
resilience4j:
  retry:
    instances:
      paymentService:
        # 최대 재시도 횟수
        max-attempts: 3
        # 대기 시간
        wait-duration: 1s
        # Exponential Backoff 활성화
        enable-exponential-backoff: true
        # 지수 배율
        exponential-backoff-multiplier: 2
        # 최대 대기 시간
        exponential-max-wait-duration: 10s
        # 재시도할 예외
        retry-exceptions:
          - java.io.IOException
          - java.net.SocketTimeoutException
        # 재시도하지 않을 예외
        ignore-exceptions:
          - com.example.BusinessException
```

**코드:**
```java
@Service
public class PaymentService {
    
    @Retry(name = "paymentService", fallbackMethod = "paymentFallback")
    @CircuitBreaker(name = "paymentService")
    public PaymentResponse processPayment(PaymentRequest request) {
        log.info("Calling payment API, attempt: {}", 
            RetryRegistry.of(retryConfig).retry("paymentService").getMetrics().getNumberOfSuccessfulCallsWithRetryAttempt());
        
        return restTemplate.postForObject(
            "https://payment-api.com/process",
            request,
            PaymentResponse.class
        );
    }
    
    private PaymentResponse paymentFallback(PaymentRequest request, Exception e) {
        return new PaymentResponse("FAILED", "결제 실패");
    }
}
```

### Retry + Circuit Breaker

**조합 사용:**
```java
@Retry(name = "paymentService")
@CircuitBreaker(name = "paymentService", fallbackMethod = "paymentFallback")
public PaymentResponse processPayment(PaymentRequest request) {
    // ...
}
```

**동작:**
1. Retry가 먼저 적용 (최대 3회 재시도)
2. 모두 실패하면 Circuit Breaker에 실패 카운트
3. Circuit Breaker가 OPEN 상태면 재시도하지 않고 즉시 Fallback

### Jitter (지터)

재시도 시간에 랜덤성을 추가한다.

**이유:**
여러 클라이언트가 동시에 실패하고 동시에 재시도하면 Thundering Herd 발생.

**Jitter 적용:**
```yaml
resilience4j:
  retry:
    instances:
      paymentService:
        wait-duration: 1s
        enable-randomized-wait: true
        randomized-wait-factor: 0.5  # 50% ~ 150% 범위
```

**효과:**
- 1초 ± 50% → 0.5초 ~ 1.5초
- 클라이언트들이 분산되어 재시도

## Timeout

### 개념

무한 대기를 방지한다. 일정 시간 내 응답이 없으면 실패로 간주한다.

**3가지 Timeout:**

**Connection Timeout:**
연결 수립 시간. 보통 짧게 설정 (1-3초).

**Read Timeout:**
데이터 수신 시간. API 특성에 따라 다름 (3-30초).

**Write Timeout:**
데이터 전송 시간. 보통 Read Timeout과 동일.

### RestTemplate 설정

```java
@Configuration
public class RestTemplateConfig {
    
    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        
        // Connection Timeout: 2초
        factory.setConnectTimeout(2000);
        
        // Read Timeout: 5초
        factory.setReadTimeout(5000);
        
        return new RestTemplate(factory);
    }
}
```

### WebClient 설정

```java
@Configuration
public class WebClientConfig {
    
    @Bean
    public WebClient webClient() {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 2000)
            .responseTimeout(Duration.ofSeconds(5))
            .doOnConnected(conn -> 
                conn.addHandlerLast(new ReadTimeoutHandler(5))
                    .addHandlerLast(new WriteTimeoutHandler(5)));
        
        return WebClient.builder()
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }
}
```

### Resilience4j TimeLimiter

```yaml
resilience4j:
  timelimiter:
    instances:
      paymentService:
        timeout-duration: 5s
        cancel-running-future: true
```

```java
@TimeLimiter(name = "paymentService")
@CircuitBreaker(name = "paymentService", fallbackMethod = "paymentFallback")
public CompletableFuture<PaymentResponse> processPaymentAsync(PaymentRequest request) {
    return CompletableFuture.supplyAsync(() -> 
        restTemplate.postForObject(
            "https://payment-api.com/process",
            request,
            PaymentResponse.class
        )
    );
}
```

## Fallback

### 개념

주 동작이 실패했을 때 대체 동작을 수행한다.

**Fallback 전략:**

**1. 기본값 반환:**
```java
private UserProfile getUserProfileFallback(String userId, Exception e) {
    log.warn("Failed to fetch user profile, returning default", e);
    return UserProfile.builder()
        .userId(userId)
        .name("Guest")
        .avatar("/images/default-avatar.png")
        .build();
}
```

**2. 캐시 사용:**
```java
@Cacheable(value = "userProfiles", key = "#userId")
@CircuitBreaker(name = "userService", fallbackMethod = "getUserProfileFromCache")
public UserProfile getUserProfile(String userId) {
    return restTemplate.getForObject(
        "https://user-api.com/users/" + userId,
        UserProfile.class
    );
}

private UserProfile getUserProfileFromCache(String userId, Exception e) {
    log.warn("Using cached user profile", e);
    return cacheManager.getCache("userProfiles").get(userId, UserProfile.class);
}
```

**3. 다른 서비스 호출:**
```java
@CircuitBreaker(name = "primaryPaymentService", fallbackMethod = "useSecondaryPayment")
public PaymentResponse processPayment(PaymentRequest request) {
    return primaryPaymentService.process(request);
}

private PaymentResponse useSecondaryPayment(PaymentRequest request, Exception e) {
    log.warn("Primary payment failed, using secondary", e);
    return secondaryPaymentService.process(request);
}
```

**4. 저하된 서비스 제공:**
```java
@CircuitBreaker(name = "recommendationService", fallbackMethod = "getPopularItems")
public List<Product> getRecommendations(String userId) {
    return recommendationService.getPersonalized(userId);
}

private List<Product> getPopularItems(String userId, Exception e) {
    log.warn("Personalized recommendations failed, returning popular items", e);
    // 개인화 추천 실패 시 인기 상품 반환
    return productService.getPopularProducts();
}
```

### Fallback 주의사항

**Fallback도 실패할 수 있다:**
```java
private PaymentResponse paymentFallback(PaymentRequest request, Exception e) {
    try {
        // 보조 결제 시스템 시도
        return backupPaymentService.process(request);
    } catch (Exception ex) {
        // 보조 시스템도 실패
        log.error("Both primary and backup payment failed", ex);
        return new PaymentResponse("FAILED", "결제 불가");
    }
}
```

**Fallback이 주 동작보다 느리면 안 된다:**
```java
// Bad: Fallback이 DB 조회
private UserProfile fallback(String userId, Exception e) {
    return userRepository.findById(userId).orElse(null);  // 느릴 수 있음
}

// Good: Fallback은 빠르게
private UserProfile fallback(String userId, Exception e) {
    return UserProfile.DEFAULT;  // 즉시 반환
}
```

## Health Check

### Liveness vs Readiness

**Liveness (살아있는지):**
- 프로세스가 실행 중인지 확인
- 실패 시: 컨테이너 재시작
- 예: 데드락, 무한 루프

**Readiness (준비됐는지):**
- 요청을 받을 준비가 됐는지 확인
- 실패 시: 트래픽 차단 (재시작 X)
- 예: DB 연결 안 됨, 캐시 워밍업 중

### Spring Boot Actuator

**의존성:**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

**application.yml:**
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true
  health:
    circuitbreakers:
      enabled: true
```

**엔드포인트:**
```
GET /actuator/health          # 전체 헬스
GET /actuator/health/liveness  # Liveness
GET /actuator/health/readiness # Readiness
```

### 커스텀 Health Indicator

```java
@Component
public class PaymentServiceHealthIndicator implements HealthIndicator {
    
    private final PaymentService paymentService;
    
    @Override
    public Health health() {
        try {
            // 결제 서비스 상태 확인
            boolean isHealthy = paymentService.ping();
            
            if (isHealthy) {
                return Health.up()
                    .withDetail("service", "payment")
                    .withDetail("status", "available")
                    .build();
            } else {
                return Health.down()
                    .withDetail("service", "payment")
                    .withDetail("status", "unavailable")
                    .build();
            }
        } catch (Exception e) {
            return Health.down()
                .withDetail("service", "payment")
                .withDetail("error", e.getMessage())
                .build();
        }
    }
}
```

**응답:**
```json
{
  "status": "UP",
  "components": {
    "paymentService": {
      "status": "UP",
      "details": {
        "service": "payment",
        "status": "available"
      }
    },
    "db": {
      "status": "UP"
    }
  }
}
```

### Kubernetes 설정

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  template:
    spec:
      containers:
      - name: app
        image: order-service:1.0
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

**동작:**
- **Liveness 실패 3회**: Pod 재시작
- **Readiness 실패 2회**: Service에서 제거 (트래픽 차단)

## 실무 패턴

### 패턴 1: 외부 API 호출

```java
@Service
public class PaymentService {
    
    @Retry(name = "payment")
    @TimeLimiter(name = "payment")
    @CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
    public CompletableFuture<PaymentResponse> processPayment(PaymentRequest request) {
        return CompletableFuture.supplyAsync(() -> {
            return restTemplate.postForObject(
                paymentApiUrl,
                request,
                PaymentResponse.class
            );
        });
    }
    
    private CompletableFuture<PaymentResponse> paymentFallback(
            PaymentRequest request, Exception e) {
        log.error("Payment failed, using fallback", e);
        
        // 결제 정보를 큐에 저장 (나중에 재시도)
        paymentQueue.add(request);
        
        return CompletableFuture.completedFuture(
            new PaymentResponse("PENDING", "결제 처리 중")
        );
    }
}
```

**설정:**
```yaml
resilience4j:
  circuitbreaker:
    instances:
      payment:
        sliding-window-size: 20
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
  retry:
    instances:
      payment:
        max-attempts: 3
        wait-duration: 1s
        enable-exponential-backoff: true
  timelimiter:
    instances:
      payment:
        timeout-duration: 5s
```

### 패턴 2: DB 조회

```java
@Service
public class UserService {
    
    @Cacheable(value = "users", key = "#userId")
    @TimeLimiter(name = "database")
    @CircuitBreaker(name = "database", fallbackMethod = "getUserFromCache")
    public CompletableFuture<User> getUser(String userId) {
        return CompletableFuture.supplyAsync(() -> {
            return userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException(userId));
        });
    }
    
    private CompletableFuture<User> getUserFromCache(String userId, Exception e) {
        log.warn("DB query failed, checking cache", e);
        
        User cachedUser = cacheManager.getCache("users").get(userId, User.class);
        if (cachedUser != null) {
            return CompletableFuture.completedFuture(cachedUser);
        }
        
        throw new UserNotFoundException(userId);
    }
}
```

### 패턴 3: 마이크로서비스 간 통신

```java
@Service
@Slf4j
public class OrderService {
    
    private final WebClient inventoryClient;
    private final WebClient paymentClient;
    
    @Transactional
    public OrderResponse createOrder(OrderRequest request) {
        // 1. 재고 확인 (Circuit Breaker 적용)
        boolean hasStock = checkInventory(request.getProductId(), request.getQuantity())
            .block(Duration.ofSeconds(3));
        
        if (!hasStock) {
            throw new OutOfStockException();
        }
        
        // 2. 주문 생성
        Order order = orderRepository.save(new Order(request));
        
        // 3. 결제 처리 (비동기 + Fallback)
        processPaymentAsync(order.getId(), request.getPaymentInfo())
            .exceptionally(e -> {
                log.error("Payment failed for order: {}", order.getId(), e);
                order.setStatus(OrderStatus.PAYMENT_PENDING);
                orderRepository.save(order);
                return null;
            });
        
        return new OrderResponse(order);
    }
    
    @CircuitBreaker(name = "inventory", fallbackMethod = "inventoryFallback")
    @Retry(name = "inventory")
    private Mono<Boolean> checkInventory(String productId, int quantity) {
        return inventoryClient.get()
            .uri("/inventory/{productId}/check?quantity={quantity}", productId, quantity)
            .retrieve()
            .bodyToMono(Boolean.class);
    }
    
    private Mono<Boolean> inventoryFallback(String productId, int quantity, Exception e) {
        log.warn("Inventory check failed, assuming available", e);
        // 재고 확인 실패 시 일단 주문 접수 (나중에 확인)
        return Mono.just(true);
    }
    
    @CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
    @Async
    private CompletableFuture<PaymentResponse> processPaymentAsync(
            String orderId, PaymentInfo paymentInfo) {
        return paymentClient.post()
            .uri("/payments")
            .bodyValue(paymentInfo)
            .retrieve()
            .bodyToMono(PaymentResponse.class)
            .toFuture();
    }
    
    private CompletableFuture<PaymentResponse> paymentFallback(
            String orderId, PaymentInfo paymentInfo, Exception e) {
        log.error("Payment failed, queuing for retry", e);
        paymentRetryQueue.add(new PaymentRetryTask(orderId, paymentInfo));
        return CompletableFuture.completedFuture(
            new PaymentResponse("PENDING", "결제 처리 중")
        );
    }
}
```

## 모니터링

### Metrics

**Resilience4j Actuator:**
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,circuitbreakers,ratelimiters,retries
```

**엔드포인트:**
```
GET /actuator/circuitbreakers
GET /actuator/retries
GET /actuator/metrics/resilience4j.circuitbreaker.calls
```

### Prometheus

```java
@Configuration
public class MetricsConfig {
    
    @Bean
    public MeterRegistry meterRegistry() {
        return new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
    }
}
```

**Grafana 대시보드:**
- Circuit Breaker 상태 (OPEN/CLOSED/HALF_OPEN)
- 실패율
- 재시도 횟수
- 평균 응답 시간

## 참고

- Resilience4j 공식 문서: https://resilience4j.readme.io/
- Spring Cloud Circuit Breaker: https://spring.io/projects/spring-cloud-circuitbreaker
- Martin Fowler - Circuit Breaker: https://martinfowler.com/bliki/CircuitBreaker.html
- AWS Well-Architected Framework: https://aws.amazon.com/architecture/well-architected/


