---
title: API Gateway 심화 가이드
tags: [network, api-gateway, spring-cloud-gateway, kong, envoy, rate-limiting, bff, circuit-breaker]
updated: 2026-03-01
---

# API Gateway 심화

## 개요

API Gateway는 모든 클라이언트 요청의 **단일 진입점(Single Entry Point)**으로, 마이크로서비스 아키텍처의 핵심 인프라이다. 인증, 라우팅, 레이트 리미팅, 로드 밸런싱 등 **횡단 관심사**를 중앙에서 처리한다.

```
                        ┌────────────────────────────────────┐
                        │          API Gateway               │
  Web ──────┐           │                                    │           ┌── User Service
  Mobile ───┤──────────▶│  인증 → 라우팅 → 레이트 리밋 → LB  │──────────▶├── Order Service
  Partner ──┘           │                                    │           ├── Product Service
                        └────────────────────────────────────┘           └── Payment Service
```

### API Gateway가 없다면?

```
❌ Gateway 없이:
  - 각 서비스마다 인증 로직 구현
  - 클라이언트가 서비스 주소를 직접 알아야 함
  - 서비스 변경 시 클라이언트도 수정 필요
  - CORS, 로깅, 레이트 리미팅을 서비스마다 개별 구현

✅ Gateway 있으면:
  - 인증을 Gateway에서 한 번만 처리
  - 클라이언트는 Gateway 주소만 알면 됨
  - 서비스 변경해도 클라이언트 영향 없음
  - 횡단 관심사를 Gateway에서 중앙 관리
```

## 핵심

### 1. API Gateway 패턴

#### Edge Gateway (기본)

가장 일반적인 패턴. 외부 트래픽의 단일 진입점.

```
Client → API Gateway → Service A
                     → Service B
                     → Service C
```

#### BFF (Backend For Frontend)

클라이언트 유형별로 전용 Gateway를 두는 패턴이다.

```
Web Client    → Web BFF    ─┐
Mobile Client → Mobile BFF ─┤→ User Service
Partner API   → Partner BFF ─┘→ Order Service
```

| 항목 | Edge Gateway | BFF |
|------|-------------|-----|
| **Gateway 수** | 1개 | 클라이언트 유형별 N개 |
| **응답 최적화** | 일반적 | 클라이언트별 맞춤 |
| **복잡도** | 낮음 | 높음 |
| **적합한 경우** | 단순한 서비스 | 모바일/웹 응답이 크게 다를 때 |

```
예시: 상품 조회
  Web BFF    → { 상세 정보, 리뷰, 추천, 이미지 10장 }
  Mobile BFF → { 요약 정보, 이미지 3장, 가격 }
  (같은 서비스를 호출하되, 응답을 클라이언트에 맞게 가공)
```

#### API Composition (응답 집계)

Gateway에서 여러 서비스 호출 결과를 **합쳐서** 클라이언트에 전달한다.

```
Client → Gateway
            ├── GET /users/1         → { name, email }
            ├── GET /orders?user=1   → [ { id, total } ]
            └── GET /points?user=1   → { balance: 5000 }

         Gateway가 합쳐서 응답:
         {
           user: { name, email },
           recentOrders: [ ... ],
           points: 5000
         }
```

### 2. 핵심 기능

#### 라우팅 (Routing)

```
경로 기반:
  /api/users/**    → user-service:8080
  /api/orders/**   → order-service:8081
  /api/products/** → product-service:8082

헤더 기반:
  X-Api-Version: v1 → user-service-v1
  X-Api-Version: v2 → user-service-v2

가중치 기반 (카나리 배포):
  90% → user-service-stable
  10% → user-service-canary
```

#### 인증/인가 (Authentication/Authorization)

```
Client → Gateway (JWT 검증) → Service (비즈니스 로직만)

1. 클라이언트가 JWT 토큰과 함께 요청
2. Gateway에서 토큰 검증 (서명, 만료, 권한)
3. 유효하면 서비스로 전달 (X-User-Id 헤더 추가)
4. 서비스는 인증 로직 없이 X-User-Id만 사용
```

#### 레이트 리미팅 (Rate Limiting)

API 남용을 방지하고 서비스를 보호하는 핵심 기능이다.

| 알고리즘 | 원리 | 특징 |
|---------|------|------|
| **고정 윈도우** | 시간 구간별 카운트 | 구현 간단, 경계 시점 폭주 가능 |
| **슬라이딩 윈도우** | 이동 시간 구간별 카운트 | 더 정확, 메모리 사용 증가 |
| **토큰 버킷** | 일정 속도로 토큰 충전, 요청 시 소비 | 버스트 허용, 가장 많이 사용 |
| **Leaky 버킷** | 일정 속도로만 요청 처리 | 균일한 처리 속도 보장 |

```
토큰 버킷 예시 (초당 10 요청, 버스트 20):

  ┌──────────────────┐
  │  버킷 (max: 20)  │ ← 초당 10개 토큰 충전
  │  ████████████     │
  │  (현재 12개)      │
  └────────┬─────────┘
           │ 요청마다 토큰 1개 소비
           ▼
  요청 → 토큰 있으면 통과, 없으면 429 Too Many Requests
```

#### 서킷 브레이커 (Circuit Breaker)

하위 서비스 장애가 Gateway를 통해 전체로 퍼지는 것을 방지한다.

```
CLOSED (정상)
  │ 연속 실패 임계치 도달
  ▼
OPEN (차단)
  │ 지정 시간 경과
  ▼
HALF-OPEN (테스트)
  │ 성공 → CLOSED로 복귀
  │ 실패 → OPEN으로 다시 전환
```

```
예시:
  Order Service 장애 발생 시

  ❌ 서킷 브레이커 없이:
    모든 주문 요청이 타임아웃 → 스레드 고갈 → Gateway 전체 마비

  ✅ 서킷 브레이커 있으면:
    Order Service 실패 5회 → 서킷 OPEN → 즉시 fallback 응답 (503)
    → 다른 서비스(User, Product)는 정상 운영
```

### 3. Spring Cloud Gateway

Spring 생태계의 API Gateway이다. WebFlux 기반으로 비동기 논블로킹 처리를 지원한다.

#### 기본 라우팅 설정

```yaml
# application.yml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service      # 서비스 디스커버리 연동
          predicates:
            - Path=/api/users/**
          filters:
            - StripPrefix=1            # /api 제거 후 전달

        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
            - Method=GET,POST
          filters:
            - StripPrefix=1
            - AddRequestHeader=X-Gateway, true

        - id: canary-route
          uri: lb://product-service-v2
          predicates:
            - Path=/api/products/**
            - Weight=group1, 10        # 10% 트래픽
          filters:
            - StripPrefix=1

        - id: stable-route
          uri: lb://product-service-v1
          predicates:
            - Path=/api/products/**
            - Weight=group1, 90        # 90% 트래픽
          filters:
            - StripPrefix=1

      default-filters:
        - DedupeResponseHeader=Access-Control-Allow-Origin
```

#### 커스텀 필터 (JWT 인증)

```java
@Component
public class JwtAuthFilter implements GatewayFilterFactory<JwtAuthFilter.Config> {

    private final JwtTokenProvider tokenProvider;

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String token = extractToken(exchange.getRequest());

            if (token == null || !tokenProvider.validate(token)) {
                exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
                return exchange.getResponse().setComplete();
            }

            // 검증된 사용자 정보를 헤더로 전달
            String userId = tokenProvider.getUserId(token);
            ServerHttpRequest request = exchange.getRequest().mutate()
                .header("X-User-Id", userId)
                .build();

            return chain.filter(exchange.mutate().request(request).build());
        };
    }

    private String extractToken(ServerHttpRequest request) {
        String bearer = request.getHeaders().getFirst("Authorization");
        if (bearer != null && bearer.startsWith("Bearer ")) {
            return bearer.substring(7);
        }
        return null;
    }

    @Data
    public static class Config { }
}
```

#### 레이트 리미팅 (Redis 기반)

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: rate-limited-route
          uri: lb://user-service
          predicates:
            - Path=/api/users/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10    # 초당 10 요청
                redis-rate-limiter.burstCapacity: 20    # 최대 버스트 20
                redis-rate-limiter.requestedTokens: 1   # 요청당 토큰 1개
                key-resolver: "#{@userKeyResolver}"
```

```java
@Bean
public KeyResolver userKeyResolver() {
    return exchange -> {
        String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
        return Mono.justOrEmpty(userId).defaultIfEmpty("anonymous");
    };
}

// IP 기반 제한
@Bean
public KeyResolver ipKeyResolver() {
    return exchange -> Mono.just(
        exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
    );
}
```

#### 서킷 브레이커 (Resilience4j)

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: CircuitBreaker
              args:
                name: orderCircuitBreaker
                fallbackUri: forward:/fallback/orders

resilience4j:
  circuitbreaker:
    instances:
      orderCircuitBreaker:
        slidingWindowSize: 10
        failureRateThreshold: 50       # 실패율 50% 이상 시 OPEN
        waitDurationInOpenState: 10000  # 10초 후 HALF-OPEN
        permittedNumberOfCallsInHalfOpenState: 3
```

```java
@RestController
public class FallbackController {

    @GetMapping("/fallback/orders")
    public ResponseEntity<Map<String, String>> orderFallback() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                "message", "주문 서비스가 일시적으로 이용 불가합니다",
                "fallback", "true"
            ));
    }
}
```

### 4. Kong Gateway

플러그인 기반의 고성능 API Gateway이다. Nginx(OpenResty) 위에 구축되었다.

#### Docker Compose로 설치

```yaml
# docker-compose.yml
services:
  kong-database:
    image: postgres:15
    environment:
      POSTGRES_DB: kong
      POSTGRES_USER: kong
      POSTGRES_PASSWORD: kong

  kong-migration:
    image: kong:3.6
    command: kong migrations bootstrap
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
    depends_on:
      - kong-database

  kong:
    image: kong:3.6
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: kong-database
      KONG_PROXY_LISTEN: 0.0.0.0:8000
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
    ports:
      - "8000:8000"   # Proxy
      - "8001:8001"   # Admin API
    depends_on:
      - kong-migration
```

#### 서비스 등록 및 라우팅

```bash
# 서비스 등록
curl -X POST http://localhost:8001/services \
  --data name=user-service \
  --data url=http://user-service:8080

# 라우트 등록
curl -X POST http://localhost:8001/services/user-service/routes \
  --data paths[]=/api/users \
  --data strip_path=true

# Rate Limiting 플러그인 적용
curl -X POST http://localhost:8001/services/user-service/plugins \
  --data name=rate-limiting \
  --data config.minute=100 \
  --data config.policy=redis \
  --data config.redis_host=redis

# JWT 인증 플러그인 적용
curl -X POST http://localhost:8001/services/user-service/plugins \
  --data name=jwt

# CORS 플러그인
curl -X POST http://localhost:8001/services/user-service/plugins \
  --data name=cors \
  --data config.origins[]=https://example.com \
  --data config.methods[]=GET \
  --data config.methods[]=POST
```

#### 주요 플러그인

| 카테고리 | 플러그인 | 기능 |
|---------|---------|------|
| **인증** | jwt, oauth2, key-auth, basic-auth | 다양한 인증 방식 |
| **보안** | cors, ip-restriction, bot-detection | 접근 제어 |
| **트래픽** | rate-limiting, request-size-limiting | 트래픽 제어 |
| **변환** | request-transformer, response-transformer | 요청/응답 수정 |
| **로깅** | file-log, http-log, tcp-log | 요청 로깅 |
| **모니터링** | prometheus, datadog, zipkin | 메트릭/트레이싱 |

### 5. Envoy Proxy

Lyft에서 개발한 고성능 L7 프록시이다. Istio 서비스 메시의 데이터 플레인으로 사용된다.

```yaml
# envoy.yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api/users"
                          route:
                            cluster: user_service
                        - match:
                            prefix: "/api/orders"
                          route:
                            cluster: order_service
                http_filters:
                  - name: envoy.filters.http.router

  clusters:
    - name: user_service
      type: STRICT_DNS
      load_assignment:
        cluster_name: user_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: user-service
                      port_value: 8080
      health_checks:
        - timeout: 5s
          interval: 10s
          unhealthy_threshold: 3
          healthy_threshold: 2
          http_health_check:
            path: /health
```

### 6. Gateway 솔루션 비교

| 항목 | Spring Cloud Gateway | Kong | Envoy | AWS API Gateway |
|------|---------------------|------|-------|----------------|
| **언어** | Java (WebFlux) | Lua (OpenResty) | C++ | 관리형 |
| **성능** | 높음 | 매우 높음 | 매우 높음 | 높음 |
| **생태계** | Spring 통합 | 플러그인 마켓 | Istio/서비스 메시 | AWS 통합 |
| **설정** | YAML/Java | Admin API/YAML | YAML/xDS | 콘솔/CloudFormation |
| **서비스 디스커버리** | Eureka, Consul | DNS, Consul | DNS, xDS | 내장 |
| **적합한 경우** | Spring MSA | 멀티 언어 MSA | K8s 서비스 메시 | AWS 서버리스 |
| **학습 곡선** | 중간 | 낮음 | 높음 | 낮음 |

**선택 기준:**
- Spring Boot MSA → **Spring Cloud Gateway**
- 멀티 언어 + 고성능 → **Kong**
- Kubernetes + 서비스 메시 → **Envoy (Istio)**
- AWS 서버리스 → **AWS API Gateway**

## 운영 팁

### 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| 레이트 리미팅 | API 남용 방지, DDoS 완화 | ✅ |
| 인증/인가 | Gateway에서 중앙 처리 | ✅ |
| 헬스 체크 | 하위 서비스 상태 모니터링 | ✅ |
| 서킷 브레이커 | 장애 전파 방지 | ✅ |
| 로깅/트레이싱 | 요청 추적, 디버깅 | ✅ |
| CORS 설정 | 브라우저 크로스 오리진 허용 | ✅ |
| 타임아웃 설정 | 요청별 적절한 타임아웃 | ✅ |
| TLS 종료 | Gateway에서 SSL 처리 | ⭐ |
| 카나리 배포 | 가중치 라우팅으로 점진적 배포 | ⭐ |

### 흔한 실수

| 실수 | 결과 | 해결 |
|------|------|------|
| 타임아웃 미설정 | 느린 서비스가 전체 블로킹 | 서비스별 타임아웃 설정 |
| 서킷 브레이커 없음 | 장애 연쇄 전파 | Resilience4j / Hystrix 적용 |
| Gateway에 비즈니스 로직 | Gateway가 비대해짐 | 라우팅/인증만, 로직은 서비스에 |
| 단일 Gateway | SPOF (단일 장애점) | Gateway 이중화 + LB |
| 레이트 리밋 없음 | DDoS, 비용 폭증 | Redis 기반 분산 레이트 리밋 |

## 참고

- [Spring Cloud Gateway 공식 문서](https://docs.spring.io/spring-cloud-gateway/reference/)
- [Kong Gateway 공식 문서](https://docs.konghq.com/gateway/)
- [Envoy Proxy 공식 문서](https://www.envoyproxy.io/docs)
- [게이트웨이 개요](Definition.md) — 게이트웨이 기본 개념
- [MSA 아키텍처](../../Architecture/MSA/Saga_패턴_및_분산_트랜잭션.md) — 마이크로서비스 패턴
- [Kubernetes Ingress](../../DevOps/Kubernetes/Kubernetes.md) — K8s 인그레스 라우팅
- [Nginx 리버스 프록시](../../WebServer/Nginx/Reverse_Proxy_and_Load_Balancing.md) — Nginx LB 설정
