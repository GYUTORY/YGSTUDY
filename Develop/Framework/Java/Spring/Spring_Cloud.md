---
title: Spring Cloud MSA 가이드
tags: [spring, spring-cloud, msa, eureka, config-server, gateway, feign, circuit-breaker, distributed-tracing]
updated: 2026-03-01
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
- [MSA](../../../Application Architecture/MSA/Saga_패턴_및_분산_트랜잭션.md) — MSA 아키텍처 패턴
- [Resilience](../../../Backend/Resilience/Fault_Tolerance.md) — Circuit Breaker, Retry
- [메시지 큐](../../../Backend/Messaging/Message_Queue.md) — 이벤트 기반 통신
