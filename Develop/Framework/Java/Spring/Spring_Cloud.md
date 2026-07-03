---
title: Spring Cloud MSA
tags: [spring, spring-cloud, msa, eureka, config-server, gateway, feign, circuit-breaker, resilience4j, cloud-bus, load-balancer, distributed-tracing]
updated: 2026-03-29
---

# Spring Cloud MSA

## 개요

Spring Cloud는 **마이크로서비스 아키텍처(MSA)를 구축하기 위한 도구 모음**이다. 서비스 디스커버리, 설정 관리, API 게이트웨이, 서비스 간 통신, 분산 추적 등 MSA의 핵심 인프라를 제공한다.

```
MSA 인프라 구성:

Client → API Gateway → 서비스 A ←→ 서비스 B
           │                ↕           ↕
           │           Config Server   Message Broker
           │                ↕
           └──────── Service Registry (Eureka)
                          ↕
                    Distributed Tracing (Zipkin)
```

### 주요 컴포넌트

| 컴포넌트 | 역할 | 구현체 |
|---------|------|--------|
| **Service Discovery** | 서비스 등록/검색 | Eureka, Consul |
| **Config Server** | 중앙 설정 관리 | Spring Cloud Config |
| **API Gateway** | 라우팅, 인증, 필터링 | Spring Cloud Gateway |
| **Service Communication** | 서비스 간 HTTP 호출 | OpenFeign |
| **Circuit Breaker** | 장애 차단 | Resilience4j |
| **Distributed Tracing** | 분산 추적 | Micrometer Tracing + Zipkin |
| **Messaging** | 이벤트 기반 통신 | Spring Cloud Stream (Kafka/RabbitMQ) |

## 핵심

### 1. Eureka (Service Discovery)

서비스가 자신을 등록하고, 다른 서비스를 검색한다.

```
1. 서비스 A 시작 → Eureka에 등록 (IP, 포트, 이름)
2. 서비스 B가 A를 호출 → Eureka에서 A의 위치 조회
3. B → A 호출 (실제 IP:포트)
4. A 중지 → Eureka에서 자동 제거

  ┌──────────┐
  │  Eureka   │  ← 서비스 레지스트리
  │  Server   │
  └─────┬────┘
     ┌──┴──────────┐
     │              │
  ┌──┴───┐     ┌───┴──┐
  │Svc A │     │Svc B │  ← Eureka Client
  │:8081 │     │:8082 │
  └──────┘     └──────┘
```

```java
// Eureka Server
@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication { }
```

```yaml
# Eureka Server (application.yml)
server:
  port: 8761
eureka:
  client:
    register-with-eureka: false
    fetch-registry: false
```

```yaml
# Eureka Client (각 서비스)
spring:
  application:
    name: user-service
eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/
  instance:
    prefer-ip-address: true
```

### 2. Config Server (중앙 설정)

모든 서비스의 설정을 **Git 레포에서 중앙 관리**한다.

```
Git Repository (설정 저장소):
  config-repo/
  ├── user-service.yml         ← user-service 기본 설정
  ├── user-service-dev.yml     ← dev 환경
  ├── user-service-prod.yml    ← prod 환경
  └── order-service.yml

서비스 시작 시:
  user-service → Config Server → Git에서 설정 로드
```

```java
// Config Server
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication { }
```

```yaml
# Config Server
spring:
  cloud:
    config:
      server:
        git:
          uri: https://github.com/org/config-repo
          default-label: main
          search-paths: '{application}'

# 클라이언트 (각 서비스)
spring:
  config:
    import: optional:configserver:http://localhost:8888
  cloud:
    config:
      fail-fast: true
      retry:
        max-attempts: 5
```

### 3. Spring Cloud Gateway

API 진입점. 라우팅, 필터링, 인증, Rate Limiting을 담당한다.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://USER-SERVICE          # Eureka 연동 로드밸런싱
          predicates:
            - Path=/api/users/**
          filters:
            - StripPrefix=1
            - name: CircuitBreaker
              args:
                name: userService
                fallbackUri: forward:/fallback/users

        - id: order-service
          uri: lb://ORDER-SERVICE
          predicates:
            - Path=/api/orders/**
          filters:
            - StripPrefix=1
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10
                redis-rate-limiter.burstCapacity: 20
```

```java
// 커스텀 필터 (JWT 인증)
@Component
public class JwtAuthFilter implements GatewayFilterFactory<JwtAuthFilter.Config> {

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String token = exchange.getRequest().getHeaders()
                .getFirst(HttpHeaders.AUTHORIZATION);

            if (token == null || !token.startsWith("Bearer ")) {
                exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
                return exchange.getResponse().setComplete();
            }

            // JWT 검증 후 사용자 정보를 헤더에 추가
            String userId = jwtUtil.extractUserId(token.substring(7));
            ServerHttpRequest request = exchange.getRequest().mutate()
                .header("X-User-Id", userId)
                .build();

            return chain.filter(exchange.mutate().request(request).build());
        };
    }

    public static class Config { }
}
```

### 4. OpenFeign (서비스 간 통신)

선언적 HTTP 클라이언트. 인터페이스만 정의하면 구현이 자동 생성된다.

```java
@FeignClient(
    name = "user-service",                    // Eureka 서비스 이름
    fallbackFactory = UserClientFallback.class  // 폴백
)
public interface UserClient {

    @GetMapping("/api/users/{id}")
    UserResponse getUser(@PathVariable("id") Long id);

    @PostMapping("/api/users")
    UserResponse createUser(@RequestBody CreateUserRequest request);

    @GetMapping("/api/users")
    List<UserResponse> getUsers(@RequestParam("ids") List<Long> ids);
}

// 폴백 (장애 시 대체 동작)
@Component
public class UserClientFallback implements FallbackFactory<UserClient> {

    @Override
    public UserClient create(Throwable cause) {
        return new UserClient() {
            @Override
            public UserResponse getUser(Long id) {
                log.warn("User service unavailable, returning default", cause);
                return UserResponse.unknown(id);
            }
            // ...
        };
    }
}
```

```yaml
# Feign 설정
spring:
  cloud:
    openfeign:
      circuitbreaker:
        enabled: true
      client:
        config:
          default:
            connect-timeout: 3000
            read-timeout: 5000
            logger-level: BASIC
```

### 5. 분산 추적 (Distributed Tracing)

여러 서비스를 거치는 요청의 **전체 흐름을 추적**한다.

```
Client → Gateway → User Service → Order Service → Payment Service
  │         │            │              │               │
  traceId: abc-123 (전체 요청에 동일한 ID)
  spanId:  001      002          003            004

Zipkin UI에서:
  [abc-123] Gateway(10ms) → User(50ms) → Order(30ms) → Payment(100ms)
  총 190ms, Payment에서 병목 발견!
```

```yaml
# 의존성: micrometer-tracing-bridge-brave, zipkin-reporter-brave
management:
  tracing:
    sampling:
      probability: 1.0    # 100% 샘플링 (프로덕션은 0.1 등)
  zipkin:
    tracing:
      endpoint: http://localhost:9411/api/v2/spans
```

### 6. Spring Cloud Stream (이벤트 기반)

```java
// 이벤트 발행
@Component
public class OrderEventPublisher {

    private final StreamBridge streamBridge;

    public void publishOrderCreated(Order order) {
        streamBridge.send("order-events-out-0",
            new OrderCreatedEvent(order.getId(), order.getUserId(), order.getAmount()));
    }
}

// 이벤트 소비
@Configuration
public class OrderEventConsumer {

    @Bean
    public Consumer<OrderCreatedEvent> orderCreated() {
        return event -> {
            log.info("주문 생성 이벤트 수신: {}", event.getOrderId());
            notificationService.sendOrderConfirmation(event);
        };
    }
}
```

```yaml
spring:
  cloud:
    stream:
      bindings:
        order-events-out-0:
          destination: order-events
        orderCreated-in-0:
          destination: order-events
          group: notification-service
      kafka:
        binder:
          brokers: localhost:9092
```

### 7. Config Server 암호화

Config Server에 민감한 설정값(DB 비밀번호, API 키 등)을 평문으로 넣으면 Git 레포에 그대로 노출된다. Config Server는 `/encrypt`, `/decrypt` 엔드포인트를 제공하고, 설정 파일에서 `{cipher}` 접두사가 붙은 값을 자동 복호화한다.

#### 대칭키 암호화

가장 간단한 방식이다. Config Server의 `bootstrap.yml`에 키 하나만 설정하면 된다.

```yaml
# Config Server bootstrap.yml
encrypt:
  key: my-secret-encrypt-key-at-least-32chars
```

설정 파일에 암호화된 값을 넣는 과정:

```bash
# 암호화
curl -X POST http://localhost:8888/encrypt -d 'real-db-password'
# → AQBx8Hk3j2Kp...  (암호화된 문자열 반환)

# 복호화 확인
curl -X POST http://localhost:8888/decrypt -d 'AQBx8Hk3j2Kp...'
# → real-db-password
```

```yaml
# config-repo/user-service.yml
spring:
  datasource:
    password: '{cipher}AQBx8Hk3j2Kp...'   # 중괄호+cipher 접두사 필수
```

서비스가 Config Server에서 설정을 받아올 때 자동으로 복호화된 값이 전달된다. 주의할 점은, YAML 파일에서 `{cipher}` 값을 반드시 작은따옴표로 감싸야 한다. 안 그러면 YAML 파서가 중괄호를 객체로 해석하려다 에러가 난다.

#### 비대칭키(RSA) 암호화

운영 환경에서는 대칭키보다 RSA 키 페어를 쓰는 게 낫다. 암호화용 공개키와 복호화용 개인키를 분리할 수 있다.

```bash
# JKS 키스토어 생성
keytool -genkeypair -alias config-server-key \
  -keyalg RSA -keysize 2048 \
  -keystore config-server.jks \
  -storepass keystorepass \
  -keypass keypass \
  -dname "CN=Config Server"
```

```yaml
# Config Server bootstrap.yml
encrypt:
  key-store:
    location: classpath:config-server.jks
    password: keystorepass
    alias: config-server-key
    secret: keypass
```

사용법은 대칭키와 동일하다. `/encrypt` 엔드포인트로 암호화하고, 설정 파일에 `{cipher}` 접두사를 붙인다.

#### HashiCorp Vault 연동

설정 파일에 암호화된 값을 넣는 것도 결국 Git에 cipher 텍스트가 남는다. Vault를 쓰면 민감한 설정 자체를 Vault에 저장하고, Config Server가 Vault에서 직접 읽어온다.

```yaml
# Config Server application.yml
spring:
  profiles:
    active: vault        # vault 프로필 활성화
  cloud:
    config:
      server:
        vault:
          host: vault.internal.company.com
          port: 8200
          scheme: https
          backend: secret
          default-key: application
          kv-version: 2
          authentication: TOKEN
          token: s.aBcDeFgHiJkLmNoPqRsT   # 운영에선 환경변수로
```

Vault에 값을 넣는 방법:

```bash
# user-service의 설정을 Vault에 저장
vault kv put secret/user-service \
  spring.datasource.password=real-db-password \
  api.external.key=some-api-key

# 프로필별 설정
vault kv put secret/user-service,prod \
  spring.datasource.password=prod-db-password
```

Git과 Vault를 동시에 쓰는 복합 구성도 가능하다. Git에는 일반 설정, Vault에는 민감한 설정을 분리한다.

```yaml
spring:
  profiles:
    active: git, vault
  cloud:
    config:
      server:
        git:
          uri: https://github.com/org/config-repo
          default-label: main
        vault:
          host: vault.internal.company.com
          port: 8200
          scheme: https
```

이 경우 두 소스에서 읽어온 설정이 병합된다. 같은 키가 있으면 뒤에 선언된 프로필(vault)이 우선한다.

### 8. OpenFeign 고급 설정

기본 설정만으로는 운영 환경에서 문제가 생긴다. 에러 응답 처리, 서비스 간 인증 토큰 전달, 타임아웃과 재시도를 제대로 설정해야 한다.

#### ErrorDecoder 커스텀

Feign의 기본 ErrorDecoder는 4xx, 5xx 응답을 모두 `FeignException`으로 던진다. 문제는 이게 circuit breaker에서 전부 실패로 잡힌다는 것이다. 400 Bad Request 같은 클라이언트 에러는 상대 서비스 장애가 아닌데도 서킷이 열릴 수 있다.

```java
public class CustomFeignErrorDecoder implements ErrorDecoder {

    private final ErrorDecoder defaultDecoder = new Default();

    @Override
    public Exception decode(String methodKey, Response response) {
        HttpStatus status = HttpStatus.valueOf(response.status());

        // 4xx는 비즈니스 예외로 변환 — circuit breaker가 실패로 카운트하지 않게
        if (status.is4xxClientError()) {
            String body = readBody(response);
            return switch (status) {
                case NOT_FOUND -> new ResourceNotFoundException(body);
                case BAD_REQUEST -> new InvalidRequestException(body);
                case CONFLICT -> new DuplicateResourceException(body);
                default -> new ClientException(status, body);
            };
        }

        // 5xx만 기본 처리 (circuit breaker 실패 카운트 대상)
        return defaultDecoder.decode(methodKey, response);
    }

    private String readBody(Response response) {
        try {
            if (response.body() == null) return "";
            return new String(response.body().asInputStream().readAllBytes(),
                StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "";
        }
    }
}
```

```java
// Feign 설정 클래스에 등록
@Configuration
public class FeignConfig {

    @Bean
    public ErrorDecoder errorDecoder() {
        return new CustomFeignErrorDecoder();
    }
}
```

Resilience4j와 함께 쓸 때, 특정 예외를 circuit breaker 실패에서 제외하려면:

```yaml
resilience4j:
  circuitbreaker:
    configs:
      default:
        ignore-exceptions:
          - com.example.exception.ResourceNotFoundException
          - com.example.exception.InvalidRequestException
```

#### RequestInterceptor로 토큰 전달

서비스 A → 서비스 B 호출 시, 원래 요청의 인증 토큰을 Feign 요청에 실어야 한다. `RequestInterceptor`를 쓴다.

```java
@Component
public class AuthTokenRelayInterceptor implements RequestInterceptor {

    @Override
    public void apply(RequestTemplate template) {
        // 현재 요청의 SecurityContext에서 토큰 추출
        ServletRequestAttributes attrs =
            (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();

        if (attrs != null) {
            String token = attrs.getRequest().getHeader(HttpHeaders.AUTHORIZATION);
            if (token != null) {
                template.header(HttpHeaders.AUTHORIZATION, token);
            }
        }
    }
}
```

주의: Feign 호출이 별도 스레드에서 실행되면 `RequestContextHolder`에서 값을 못 읽는다. Hystrix나 @Async와 함께 쓸 때 이 문제가 발생한다. 해결 방법은 두 가지다.

```yaml
# 방법 1: Feign을 같은 스레드에서 실행 (Hystrix 사용 시)
hystrix:
  command:
    default:
      execution:
        isolation:
          strategy: SEMAPHORE   # THREAD 대신 SEMAPHORE
```

```java
// 방법 2: InheritableThreadLocal 사용 — 직접 컨텍스트를 전파
@Bean
public RequestContextListener requestContextListener() {
    return new RequestContextListener();
}
```

#### 타임아웃과 재시도 설정

Feign, Resilience4j, Spring Cloud LoadBalancer 각각에 타임아웃 설정이 있다. 어디에 걸리는지 모르면 디버깅이 힘들다.

```yaml
spring:
  cloud:
    openfeign:
      client:
        config:
          default:                    # 전체 기본값
            connect-timeout: 3000
            read-timeout: 5000
            logger-level: BASIC
          user-service:               # 특정 서비스만 다르게
            connect-timeout: 2000
            read-timeout: 10000       # user-service는 응답이 느려서 넉넉하게
            logger-level: FULL

      # Feign 자체 재시도 (기본은 NEVER_RETRY)
      # Resilience4j retry와 중복되므로 둘 중 하나만 쓴다
```

Feign의 Retryer를 직접 설정하는 경우:

```java
@Bean
public Retryer retryer() {
    // 100ms 간격, 최대 1초까지 백오프, 최대 3회 재시도
    return new Retryer.Default(100, 1000, 3);
}
```

실무에서는 Feign Retryer 대신 Resilience4j의 retry를 쓰는 게 낫다. circuit breaker와 연동이 되고, 재시도 조건을 세밀하게 제어할 수 있다.

```yaml
resilience4j:
  retry:
    instances:
      user-service:
        max-attempts: 3
        wait-duration: 500ms
        retry-exceptions:
          - java.io.IOException
          - feign.RetryableException
        ignore-exceptions:
          - com.example.exception.ClientException  # 4xx는 재시도 안 함
```

### 9. Resilience4j 상세 설정

Circuit Breaker만 쓰는 경우가 많은데, Resilience4j는 Bulkhead, RateLimiter, TimeLimiter도 제공한다. 이것들을 조합해야 서비스 간 장애 전파를 제대로 막을 수 있다.

#### Bulkhead

동시 호출 수를 제한한다. 특정 서비스로의 호출이 전체 스레드 풀을 잡아먹는 걸 방지한다.

Bulkhead에는 두 가지 타입이 있다.

```yaml
resilience4j:
  bulkhead:
    instances:
      user-service:
        max-concurrent-calls: 25            # 동시 호출 최대 25개
        max-wait-duration: 0ms              # 꽉 차면 바로 reject (대기 안 함)
      payment-service:
        max-concurrent-calls: 10            # 결제는 더 보수적으로
        max-wait-duration: 500ms            # 500ms까지 대기

  thread-pool-bulkhead:                     # 별도 스레드 풀로 격리
    instances:
      external-api:
        max-thread-pool-size: 10
        core-thread-pool-size: 5
        queue-capacity: 20
        keep-alive-duration: 100ms
```

`SemaphoreBulkhead`는 호출 스레드를 그대로 쓰면서 동시 수만 제한한다. `ThreadPoolBulkhead`는 별도 스레드 풀에서 실행하므로 완전히 격리되지만, 컨텍스트 전파(SecurityContext, MDC 등)를 직접 처리해야 한다.

```java
@Service
public class OrderService {

    @Bulkhead(name = "user-service", fallbackMethod = "getUserFallback")
    @CircuitBreaker(name = "user-service", fallbackMethod = "getUserFallback")
    public UserResponse getUser(Long userId) {
        return userClient.getUser(userId);
    }

    private UserResponse getUserFallback(Long userId, Exception e) {
        log.warn("user-service 호출 실패 (userId={}): {}", userId, e.getMessage());
        return UserResponse.unknown(userId);
    }
}
```

어노테이션을 여러 개 붙이면 실행 순서가 중요하다. 기본 순서는 `Retry → CircuitBreaker → RateLimiter → TimeLimiter → Bulkhead` 순이다. 안쪽(Bulkhead)부터 실행되고 바깥(Retry)이 감싼다.

#### RateLimiter

일정 시간 동안의 호출 횟수를 제한한다. 외부 API 호출에 rate limit이 걸려 있거나, 특정 서비스에 트래픽 제한을 걸고 싶을 때 쓴다.

```yaml
resilience4j:
  ratelimiter:
    instances:
      external-sms-api:
        limit-for-period: 50               # 주기당 최대 50회
        limit-refresh-period: 1s            # 1초마다 리셋
        timeout-duration: 2s                # 제한 초과 시 2초까지 대기
      payment-service:
        limit-for-period: 100
        limit-refresh-period: 1s
        timeout-duration: 0s                # 초과하면 바로 reject
```

```java
@RateLimiter(name = "external-sms-api", fallbackMethod = "sendSmsFallback")
public void sendSms(String phoneNumber, String message) {
    smsApiClient.send(phoneNumber, message);
}

private void sendSmsFallback(String phoneNumber, String message, Exception e) {
    // 큐에 넣고 나중에 재시도
    smsRetryQueue.enqueue(new SmsRequest(phoneNumber, message));
    log.warn("SMS 발송 rate limit 초과, 큐에 적재: {}", phoneNumber);
}
```

#### TimeLimiter

비동기 호출의 타임아웃을 제어한다. `CompletableFuture`를 반환하는 메서드에 적용된다.

```yaml
resilience4j:
  timelimiter:
    instances:
      user-service:
        timeout-duration: 3s               # 3초 초과하면 TimeoutException
        cancel-running-future: true         # 타임아웃 시 실행 중인 Future 취소
      report-service:
        timeout-duration: 30s              # 리포트 생성은 오래 걸림
```

```java
@TimeLimiter(name = "user-service", fallbackMethod = "getUserAsyncFallback")
@CircuitBreaker(name = "user-service", fallbackMethod = "getUserAsyncFallback")
public CompletableFuture<UserResponse> getUserAsync(Long userId) {
    return CompletableFuture.supplyAsync(() -> userClient.getUser(userId));
}

private CompletableFuture<UserResponse> getUserAsyncFallback(Long userId, Exception e) {
    return CompletableFuture.completedFuture(UserResponse.unknown(userId));
}
```

#### Resilience4j 조합 설정 예시

실제 운영에서는 여러 패턴을 조합한다. 아래는 외부 결제 API 호출에 적용한 설정이다.

```yaml
resilience4j:
  circuitbreaker:
    instances:
      payment-api:
        sliding-window-type: COUNT_BASED
        sliding-window-size: 10
        failure-rate-threshold: 50          # 10건 중 5건 실패하면 서킷 오픈
        wait-duration-in-open-state: 30s    # 30초 후 half-open
        permitted-number-of-calls-in-half-open-state: 3
        slow-call-duration-threshold: 5s
        slow-call-rate-threshold: 80

  retry:
    instances:
      payment-api:
        max-attempts: 3
        wait-duration: 1s
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2   # 1s → 2s → 4s
        retry-exceptions:
          - java.io.IOException
          - java.net.SocketTimeoutException

  bulkhead:
    instances:
      payment-api:
        max-concurrent-calls: 10
        max-wait-duration: 0ms

  ratelimiter:
    instances:
      payment-api:
        limit-for-period: 30
        limit-refresh-period: 1s
        timeout-duration: 0s
```

### 10. Spring Cloud Bus

Config Server에서 설정을 바꿔도 각 서비스를 재시작해야 반영된다. `/actuator/refresh`를 서비스마다 호출하는 것도 번거롭다. Spring Cloud Bus는 메시지 브로커(RabbitMQ, Kafka)를 통해 **설정 변경을 모든 서비스에 한번에 전파**한다.

```
설정 변경 흐름:

Git push (설정 변경)
    → Config Server에 /busrefresh POST
    → RabbitMQ/Kafka로 이벤트 전파
    → 모든 서비스가 Config Server에서 설정 다시 로드
```

```xml
<!-- Config Server와 각 서비스 모두에 추가 -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bus-amqp</artifactId>   <!-- RabbitMQ -->
</dependency>
<!-- 또는 -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bus-kafka</artifactId>
</dependency>
```

```yaml
# Config Server (RabbitMQ 사용 시)
spring:
  rabbitmq:
    host: rabbitmq.internal
    port: 5672
    username: config
    password: config-pass

management:
  endpoints:
    web:
      exposure:
        include: busrefresh     # busrefresh 엔드포인트 노출
```

```yaml
# 각 서비스 (동일한 RabbitMQ 연결)
spring:
  rabbitmq:
    host: rabbitmq.internal
    port: 5672
    username: config
    password: config-pass
```

설정 변경 후 한 번만 호출하면 전체 서비스에 반영된다.

```bash
# 전체 서비스 설정 갱신
curl -X POST http://config-server:8888/actuator/busrefresh

# 특정 서비스만 갱신
curl -X POST http://config-server:8888/actuator/busrefresh/user-service
```

`@RefreshScope`가 붙은 빈만 갱신된다는 점을 기억해야 한다.

```java
@RestController
@RefreshScope
public class FeatureFlagController {

    @Value("${feature.new-checkout:false}")
    private boolean newCheckoutEnabled;

    @GetMapping("/api/feature/new-checkout")
    public boolean isNewCheckoutEnabled() {
        return newCheckoutEnabled;    // busrefresh 후 자동으로 새 값 반영
    }
}
```

Git webhook과 연동하면 설정 파일 push 시 자동으로 전파할 수 있다.

```
GitHub Webhook → Config Server /monitor 엔드포인트
    → Config Server가 Git에서 변경 감지
    → /busrefresh 자동 트리거
    → 전체 서비스 설정 갱신
```

```yaml
# Config Server — monitor 엔드포인트 활성화
spring:
  cloud:
    config:
      server:
        monitor:
          github:
            enabled: true
```

### 11. Spring Cloud LoadBalancer 커스텀

Spring Cloud LoadBalancer는 Ribbon을 대체하는 클라이언트 사이드 로드밸런서다. 기본은 라운드로빈인데, 서비스 특성에 따라 커스텀 알고리즘이 필요한 경우가 있다.

#### 기본 제공 알고리즘

```java
// 랜덤 로드밸런서로 변경
@Configuration
@LoadBalancerClient(name = "user-service", configuration = UserServiceLbConfig.class)
public class LoadBalancerConfig { }

public class UserServiceLbConfig {

    @Bean
    public ReactorLoadBalancer<ServiceInstance> randomLoadBalancer(
            Environment environment,
            LoadBalancerClientFactory clientFactory) {
        String name = environment.getProperty(LoadBalancerClientFactory.PROPERTY_NAME);
        return new RandomLoadBalancer(
            clientFactory.getLazyProvider(name, ServiceInstanceListSupplier.class),
            name
        );
    }
}
```

#### 커스텀 알고리즘 — 가중치 기반

인스턴스별로 성능이 다른 경우(예: 2코어 서버와 8코어 서버가 섞여 있을 때) 가중치 기반 로드밸런싱을 쓴다.

```java
public class WeightedLoadBalancer implements ReactorServiceInstanceLoadBalancer {

    private final ObjectProvider<ServiceInstanceListSupplier> supplierProvider;
    private final String serviceId;
    private final AtomicInteger position = new AtomicInteger(0);

    public WeightedLoadBalancer(
            ObjectProvider<ServiceInstanceListSupplier> supplierProvider,
            String serviceId) {
        this.supplierProvider = supplierProvider;
        this.serviceId = serviceId;
    }

    @Override
    public Mono<Response<ServiceInstance>> choose(Request request) {
        return supplierProvider.getIfAvailable()
            .get(request)
            .next()
            .map(this::selectByWeight);
    }

    private Response<ServiceInstance> selectByWeight(List<ServiceInstance> instances) {
        if (instances.isEmpty()) {
            return new EmptyResponse();
        }

        // metadata에서 weight 값을 읽어서 가중치 적용
        List<ServiceInstance> weightedList = new ArrayList<>();
        for (ServiceInstance instance : instances) {
            int weight = Integer.parseInt(
                instance.getMetadata().getOrDefault("weight", "1"));
            for (int i = 0; i < weight; i++) {
                weightedList.add(instance);
            }
        }

        int idx = Math.abs(position.incrementAndGet()) % weightedList.size();
        return new DefaultResponse(weightedList.get(idx));
    }
}
```

```yaml
# Eureka 인스턴스에 weight 메타데이터 설정
eureka:
  instance:
    metadata-map:
      weight: 3          # 이 인스턴스는 3배 트래픽 수신
```

#### 헬스 체크 기반 필터링

불건전한 인스턴스를 로드밸런싱 대상에서 제외한다.

```yaml
spring:
  cloud:
    loadbalancer:
      configurations: health-check     # 헬스 체크 활성화
      health-check:
        initial-delay: 5s
        interval: 25s
        path:
          user-service: /actuator/health
```

```java
// Zone 기반 필터링 — 같은 zone 인스턴스 우선
@Bean
public ServiceInstanceListSupplier zonePreferenceSupplier(
        ConfigurableApplicationContext context) {
    return ServiceInstanceListSupplier.builder()
        .withDiscoveryClient()
        .withZonePreference()           // 같은 zone 우선
        .withHealthChecks()             // 헬스 체크 필터링
        .build(context);
}
```

### 12. 서비스 간 인증 — 토큰 릴레이 패턴

MSA에서 서비스 간 호출 시 인증을 어떻게 전파할지가 문제가 된다. Gateway에서 인증한 사용자 정보를 내부 서비스 간 호출에도 전달해야 한다.

#### Gateway에서 내부 서비스로 전달

Gateway가 JWT를 검증하고, 사용자 정보를 커스텀 헤더로 넣어 전달하는 패턴이다.

```
Client → [JWT] → Gateway → [X-User-Id, X-User-Role] → 내부 서비스들
                  (JWT 검증)
```

```java
// Gateway 필터 — JWT 검증 후 헤더에 사용자 정보 추가
@Component
public class AuthRelayFilter implements GlobalFilter, Ordered {

    private final JwtDecoder jwtDecoder;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String authHeader = exchange.getRequest().getHeaders()
            .getFirst(HttpHeaders.AUTHORIZATION);

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return chain.filter(exchange);   // 인증 불필요한 경로일 수 있음
        }

        String token = authHeader.substring(7);
        Jwt jwt = jwtDecoder.decode(token);

        ServerHttpRequest request = exchange.getRequest().mutate()
            .header("X-User-Id", jwt.getSubject())
            .header("X-User-Role", jwt.getClaimAsString("role"))
            .header("X-Request-Id", UUID.randomUUID().toString())
            .build();

        return chain.filter(exchange.mutate().request(request).build());
    }

    @Override
    public int getOrder() {
        return -1;   // 다른 필터보다 먼저 실행
    }
}
```

#### 서비스 간 호출 시 헤더 전파

서비스 A가 서비스 B를 Feign으로 호출할 때, 원래 요청의 헤더를 자동으로 전달한다.

```java
@Component
public class InternalAuthInterceptor implements RequestInterceptor {

    private static final List<String> RELAY_HEADERS = List.of(
        "X-User-Id", "X-User-Role", "X-Request-Id"
    );

    @Override
    public void apply(RequestTemplate template) {
        ServletRequestAttributes attrs =
            (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();

        if (attrs == null) return;

        HttpServletRequest request = attrs.getRequest();
        for (String header : RELAY_HEADERS) {
            String value = request.getHeader(header);
            if (value != null) {
                template.header(header, value);
            }
        }
    }
}
```

#### 내부 서비스 보호 — 외부 직접 호출 차단

내부 서비스는 Gateway를 통해서만 접근 가능해야 한다. X-User-Id 헤더가 없거나, Gateway가 아닌 곳에서 직접 호출하면 차단한다.

```java
@Component
public class InternalOnlyFilter extends OncePerRequestFilter {

    @Value("${security.gateway-secret}")
    private String gatewaySecret;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
            HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        // 내부 호출 식별용 시크릿 헤더 확인
        String secret = request.getHeader("X-Gateway-Secret");
        if (!gatewaySecret.equals(secret)) {
            response.sendError(HttpStatus.FORBIDDEN.value(),
                "Direct access not allowed");
            return;
        }

        chain.doFilter(request, response);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // 헬스 체크는 필터링 제외
        return request.getRequestURI().startsWith("/actuator/");
    }
}
```

```yaml
# Gateway에서 내부 호출 시 시크릿 헤더 추가
spring:
  cloud:
    gateway:
      default-filters:
        - AddRequestHeader=X-Gateway-Secret, ${GATEWAY_SECRET}
```

#### 서비스 간 전용 토큰 (Service-to-Service)

일부 서비스 간 호출은 사용자 컨텍스트 없이 발생한다. 예를 들어 배치 작업이나 이벤트 처리에서 다른 서비스를 호출하는 경우다. 이때는 서비스 전용 토큰을 발급해서 쓴다.

```java
@Component
public class ServiceTokenProvider {

    @Value("${service.name}")
    private String serviceName;

    @Value("${service.secret}")
    private String serviceSecret;

    private final JwtEncoder jwtEncoder;

    public String issueServiceToken() {
        Instant now = Instant.now();
        JwtClaimsSet claims = JwtClaimsSet.builder()
            .issuer(serviceName)
            .subject(serviceName)
            .claim("type", "service")
            .issuedAt(now)
            .expiresAt(now.plusSeconds(300))   // 5분 유효
            .build();

        return jwtEncoder.encode(JwtEncoderParameters.from(claims))
            .getTokenValue();
    }
}

// Feign Interceptor에서 사용자 토큰이 없으면 서비스 토큰 사용
@Component
public class SmartAuthInterceptor implements RequestInterceptor {

    private final ServiceTokenProvider tokenProvider;

    @Override
    public void apply(RequestTemplate template) {
        ServletRequestAttributes attrs =
            (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();

        if (attrs != null) {
            String userToken = attrs.getRequest()
                .getHeader(HttpHeaders.AUTHORIZATION);
            if (userToken != null) {
                template.header(HttpHeaders.AUTHORIZATION, userToken);
                return;
            }
        }

        // 사용자 컨텍스트가 없으면 서비스 토큰 발급
        String serviceToken = tokenProvider.issueServiceToken();
        template.header(HttpHeaders.AUTHORIZATION, "Bearer " + serviceToken);
        template.header("X-Service-Call", "true");
    }
}
```

## Docker Compose 전체 구성

```yaml
services:
  eureka:
    image: eureka-server:latest
    ports: ["8761:8761"]

  config-server:
    image: config-server:latest
    ports: ["8888:8888"]
    depends_on: [eureka]

  gateway:
    image: api-gateway:latest
    ports: ["8080:8080"]
    depends_on: [eureka, config-server]

  user-service:
    image: user-service:latest
    deploy:
      replicas: 2
    depends_on: [eureka, config-server]

  order-service:
    image: order-service:latest
    deploy:
      replicas: 2
    depends_on: [eureka, config-server]

  zipkin:
    image: openzipkin/zipkin
    ports: ["9411:9411"]
```

## 참고

- [Spring Cloud 공식 문서](https://spring.io/projects/spring-cloud)
- [Spring Cloud Gateway](https://docs.spring.io/spring-cloud-gateway/reference/)
- [OpenFeign](https://docs.spring.io/spring-cloud-openfeign/reference/)
- [Resilience4j 공식 문서](https://resilience4j.readme.io/docs)
- [Spring Cloud Bus](https://docs.spring.io/spring-cloud-bus/reference/)
- [HashiCorp Vault](https://developer.hashicorp.com/vault/docs)
- [MSA](../../../Architecture/MSA/Saga_패턴_및_분산_트랜잭션.md) — MSA 아키텍처 패턴
- [Resilience](../../../Backend/Resilience/Fault_Tolerance.md) — Circuit Breaker, Retry
- [메시지 큐](../../../Backend/Messaging/Message_Queue.md) — 이벤트 기반 통신
