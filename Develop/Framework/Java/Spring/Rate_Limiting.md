---
title: Spring Boot Rate Limiting 구현
tags: [framework, java, spring, rate-limiting, bucket4j, redis, spring-cloud-gateway, distributed]
updated: 2026-04-06
---

# Spring Boot Rate Limiting 구현

## 배경

API를 외부에 열어두면 특정 클라이언트가 요청을 과도하게 보내는 상황이 생긴다. 장애가 아니라 정상적인 사용 패턴에서도 발생한다. 배치 작업이 API를 호출하거나, 프론트엔드에서 디바운싱 없이 검색 요청을 날리거나, 크롤러가 붙는 경우가 흔하다.

Rate Limiting은 일정 시간 내 요청 수를 제한하는 것이다. 구현 방식은 여러 가지가 있는데, Spring Boot 환경에서 자주 쓰이는 방법을 정리한다.

### Rate Limiting 알고리즘

| 알고리즘 | 동작 방식 | 특징 |
|----------|----------|------|
| **Token Bucket** | 일정 속도로 토큰이 채워지고, 요청마다 토큰을 소모 | 버스트 허용. 가장 많이 사용 |
| **Sliding Window** | 현재 시점 기준으로 윈도우를 이동하며 카운트 | 경계 문제 없음. 구현이 복잡 |
| **Fixed Window** | 고정된 시간 구간마다 카운터 리셋 | 구현이 단순하지만 윈도우 경계에서 2배 트래픽 가능 |
| **Leaky Bucket** | 큐에 요청을 넣고 일정 속도로 처리 | 출력 속도가 일정. 버스트 차단 |

실무에서는 Token Bucket을 가장 많이 쓴다. Bucket4j, Guava RateLimiter, Redis 기반 구현 모두 Token Bucket 변형이다.

## 핵심

### 1. Bucket4j 라이브러리

Bucket4j는 Java의 Token Bucket 구현체다. JSR 107(JCache) 호환이고, 로컬/분산 환경 모두 지원한다.

#### 의존성 추가

```xml
<!-- pom.xml -->
<dependency>
    <groupId>com.bucket4j</groupId>
    <artifactId>bucket4j-core</artifactId>
    <version>8.10.1</version>
</dependency>

<!-- Spring Boot 자동 설정을 쓰려면 -->
<dependency>
    <groupId>com.bucket4j</groupId>
    <artifactId>bucket4j-spring-boot-starter</artifactId>
    <version>0.12.3</version>
</dependency>
```

#### 기본 사용법

```java
import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.Refill;

import java.time.Duration;

public class RateLimiterExample {

    // 분당 50회 제한, 토큰이 점진적으로 채워짐
    private final Bucket bucket = Bucket.builder()
            .addLimit(Bandwidth.classic(50, Refill.greedy(50, Duration.ofMinutes(1))))
            .build();

    public boolean tryConsume() {
        return bucket.tryConsume(1);
    }
}
```

`Refill.greedy`는 토큰을 한꺼번에 채우고, `Refill.intervally`는 간격마다 나눠서 채운다. greedy를 쓰면 버스트 트래픽을 허용하고, intervally를 쓰면 요청이 고르게 분산된다.

```java
// greedy: 1분마다 50개 토큰을 한번에 충전
Refill.greedy(50, Duration.ofMinutes(1))

// intervally: 1분을 균등 분할해서 충전 (약 1.2초마다 1개)
Refill.intervally(50, Duration.ofMinutes(1))
```

실제 서비스에서는 두 가지 한도를 함께 거는 경우가 많다. 초당 버스트를 막으면서 분당 총량도 제한하는 식이다.

```java
Bucket bucket = Bucket.builder()
        .addLimit(Bandwidth.classic(10, Refill.greedy(10, Duration.ofSeconds(1))))   // 초당 10회
        .addLimit(Bandwidth.classic(100, Refill.greedy(100, Duration.ofMinutes(1)))) // 분당 100회
        .build();
```

#### Bucket4j + Spring Boot Starter 설정

`bucket4j-spring-boot-starter`를 쓰면 `application.yml`만으로 Rate Limiting을 설정할 수 있다.

```yaml
# application.yml
bucket4j:
  enabled: true
  filters:
    - cache-name: rate-limit-buckets
      url: /api/.*
      http-response-body: '{"error": "Too many requests"}'
      rate-limits:
        - cache-key: getRemoteAddr()
          bandwidths:
            - capacity: 100
              time: 1
              unit: minutes
              refill-speed: greedy
```

IP 기반으로 분당 100회 제한이 걸린다. `cache-key`에 헤더 값이나 인증 정보를 쓸 수도 있다.

```yaml
# 인증된 사용자 기준으로 제한
rate-limits:
  - cache-key: "@securityService.getUsername()"
    bandwidths:
      - capacity: 200
        time: 1
        unit: minutes
```

캐시 구현체가 필요한데, JCache(Caffeine, Hazelcast, Redis 등)를 연결한다.

```xml
<dependency>
    <groupId>com.bucket4j</groupId>
    <artifactId>bucket4j-jcache</artifactId>
    <version>8.10.1</version>
</dependency>
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
</dependency>
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>jcache</artifactId>
    <version>3.1.8</version>
</dependency>
```

### 2. Spring Cloud Gateway RequestRateLimiter

API Gateway를 쓰고 있다면 Spring Cloud Gateway의 `RequestRateLimiter` 필터가 가장 간단하다. Redis 기반으로 동작하고, 별도 코드 없이 설정만으로 끝난다.

#### 의존성

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
</dependency>
```

#### 설정

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/users/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10    # 초당 토큰 충전 수
                redis-rate-limiter.burstCapacity: 20     # 최대 버스트 크기
                redis-rate-limiter.requestedTokens: 1    # 요청당 소모 토큰
                key-resolver: "#{@ipKeyResolver}"

  data:
    redis:
      host: localhost
      port: 6379
```

`replenishRate`는 초 단위다. 10으로 설정하면 초당 10개 토큰이 충전된다. `burstCapacity`는 토큰 버킷의 최대 크기로, 순간 최대 20개 요청까지 허용한다.

#### KeyResolver 구현

어떤 기준으로 Rate Limit을 적용할지 결정하는 부분이다.

```java
@Configuration
public class RateLimiterConfig {

    // IP 기준
    @Bean
    public KeyResolver ipKeyResolver() {
        return exchange -> Mono.just(
                exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
        );
    }

    // 사용자 ID 기준
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> exchange.getPrincipal()
                .map(Principal::getName)
                .defaultIfEmpty("anonymous");
    }

    // API 키 기준
    @Bean
    public KeyResolver apiKeyResolver() {
        return exchange -> Mono.just(
                exchange.getRequest().getHeaders().getFirst("X-API-Key") != null
                        ? exchange.getRequest().getHeaders().getFirst("X-API-Key")
                        : exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
        );
    }
}
```

Rate Limit에 걸리면 `429 Too Many Requests`가 반환된다. 응답 헤더에 `X-RateLimit-Remaining`, `X-RateLimit-Burst-Capacity` 등이 자동으로 포함된다.

주의할 점이 있다. Spring Cloud Gateway는 WebFlux 기반이라 Spring MVC 프로젝트에서는 쓸 수 없다. Gateway가 별도 서비스로 분리된 구조에서 사용해야 한다.

### 3. 커스텀 인터셉터 기반 구현

라이브러리 의존성을 추가하고 싶지 않거나, 세밀한 제어가 필요한 경우 `HandlerInterceptor`로 직접 구현할 수 있다.

#### 기본 구현

```java
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    // IP별 버킷 관리. ConcurrentHashMap으로 동시성 처리
    private final Map<String, Bucket> bucketCache = new ConcurrentHashMap<>();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                             Object handler) throws Exception {

        String clientIp = resolveClientIp(request);
        Bucket bucket = bucketCache.computeIfAbsent(clientIp, this::createBucket);

        ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);

        // Rate Limit 관련 헤더 추가
        response.addHeader("X-RateLimit-Remaining", String.valueOf(probe.getRemainingTokens()));

        if (probe.isConsumed()) {
            return true;
        }

        // 다음 토큰이 사용 가능해지는 시간을 알려줌
        long waitForRefillNanos = probe.getNanosToWaitForRefill();
        long retryAfterSeconds = TimeUnit.NANOSECONDS.toSeconds(waitForRefillNanos) + 1;

        response.addHeader("Retry-After", String.valueOf(retryAfterSeconds));
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"error\": \"Rate limit exceeded\", \"retryAfter\": " + retryAfterSeconds + "}");

        return false;
    }

    private Bucket createBucket(String key) {
        return Bucket.builder()
                .addLimit(Bandwidth.classic(60, Refill.greedy(60, Duration.ofMinutes(1))))
                .build();
    }

    private String resolveClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isEmpty()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
```

#### 인터셉터 등록

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final RateLimitInterceptor rateLimitInterceptor;

    public WebConfig(RateLimitInterceptor rateLimitInterceptor) {
        this.rateLimitInterceptor = rateLimitInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(rateLimitInterceptor)
                .addPathPatterns("/api/**")
                .excludePathPatterns("/api/health", "/api/ready");
    }
}
```

이 방식의 문제점은 `ConcurrentHashMap`이 계속 커진다는 것이다. 오래된 클라이언트의 버킷이 정리되지 않으면 메모리가 누수된다. Caffeine 캐시로 교체하면 TTL 기반 정리가 가능하다.

```java
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    private final Cache<String, Bucket> bucketCache = Caffeine.newBuilder()
            .expireAfterAccess(10, TimeUnit.MINUTES)  // 10분간 접근 없으면 제거
            .maximumSize(100_000)
            .build();

    // ... 나머지는 동일. computeIfAbsent 대신 bucketCache.get(key, this::createBucket) 사용
}
```

#### 어노테이션 기반으로 확장

엔드포인트별로 다른 한도를 적용하고 싶으면 커스텀 어노테이션을 만든다.

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RateLimit {
    int capacity() default 60;
    int refillTokens() default 60;
    int refillSeconds() default 60;
}
```

```java
@RestController
@RequestMapping("/api")
public class ApiController {

    @RateLimit(capacity = 10, refillTokens = 10, refillSeconds = 60)
    @PostMapping("/send-email")
    public ResponseEntity<Void> sendEmail(@RequestBody EmailRequest request) {
        // 이메일 발송은 분당 10회로 제한
        return ResponseEntity.ok().build();
    }

    @RateLimit(capacity = 100, refillTokens = 100, refillSeconds = 60)
    @GetMapping("/products")
    public ResponseEntity<List<Product>> getProducts() {
        // 상품 조회는 분당 100회
        return ResponseEntity.ok(productService.findAll());
    }
}
```

인터셉터에서 어노테이션을 읽어서 버킷 설정을 바꾼다.

```java
@Override
public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                         Object handler) throws Exception {

    if (!(handler instanceof HandlerMethod handlerMethod)) {
        return true;
    }

    RateLimit rateLimit = handlerMethod.getMethodAnnotation(RateLimit.class);
    if (rateLimit == null) {
        return true;  // 어노테이션 없으면 제한 없음
    }

    String clientIp = resolveClientIp(request);
    String bucketKey = clientIp + ":" + handlerMethod.getMethod().getName();

    Bucket bucket = bucketCache.get(bucketKey, key -> Bucket.builder()
            .addLimit(Bandwidth.classic(
                    rateLimit.capacity(),
                    Refill.greedy(rateLimit.refillTokens(), Duration.ofSeconds(rateLimit.refillSeconds()))
            ))
            .build());

    // 이하 동일
    ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);
    // ...
}
```

### 4. Redisson RRateLimiter를 이용한 분산 Rate Limiting

서버가 여러 대면 로컬 Rate Limiting은 의미가 없다. 서버 3대에 각각 분당 100회 제한을 걸면 실제로는 300회까지 가능하다. Redis를 중심으로 상태를 공유해야 한다.

Redisson은 Redis 기반의 분산 자료구조를 제공하는 라이브러리인데, `RRateLimiter`가 분산 Rate Limiting을 지원한다.

#### 의존성

```xml
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
    <version>3.36.0</version>
</dependency>
```

#### 설정

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
```

#### RRateLimiter 사용

```java
@Service
public class DistributedRateLimiterService {

    private final RedissonClient redissonClient;

    public DistributedRateLimiterService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    /**
     * 분산 환경에서 Rate Limit 체크.
     * Redis에 상태가 저장되므로 서버가 몇 대든 전체 합산으로 제한된다.
     */
    public boolean tryAcquire(String key, long rate, long rateInterval, RateIntervalUnit unit) {
        RRateLimiter limiter = redissonClient.getRateLimiter("rate-limit:" + key);

        // trySetRate는 이미 설정이 있으면 무시한다.
        // 한도를 변경하려면 delete() 후 다시 설정해야 한다.
        limiter.trySetRate(RateType.OVERALL, rate, rateInterval, unit);

        return limiter.tryAcquire(1);
    }
}
```

`RateType.OVERALL`은 모든 서버 합산, `RateType.PER_CLIENT`는 Redisson 클라이언트(서버 인스턴스)별 제한이다. 대부분의 경우 `OVERALL`을 쓴다.

#### 필터로 연결

```java
@Component
public class DistributedRateLimitFilter extends OncePerRequestFilter {

    private final DistributedRateLimiterService rateLimiterService;

    public DistributedRateLimitFilter(DistributedRateLimiterService rateLimiterService) {
        this.rateLimiterService = rateLimiterService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        String clientIp = resolveClientIp(request);

        boolean allowed = rateLimiterService.tryAcquire(
                clientIp, 100, 1, RateIntervalUnit.MINUTES
        );

        if (!allowed) {
            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write("{\"error\": \"Rate limit exceeded\"}");
            return;
        }

        filterChain.doFilter(request, response);
    }

    private String resolveClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isEmpty()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
```

Redisson RRateLimiter를 쓸 때 주의사항이 있다. `trySetRate`는 최초 한 번만 적용되고, 이후 호출에서는 기존 설정을 유지한다. 런타임에 한도를 바꾸려면 해당 키를 `delete()` 한 뒤 다시 설정해야 한다. 이 때 짧은 순간 Rate Limiting이 풀리는 구간이 생기는데, 트래픽이 많은 서비스에서는 Lua 스크립트로 atomic하게 처리하는 게 안전하다.

Redis 장애 시 Rate Limiting이 동작하지 않는다는 점도 고려해야 한다. 장애 시 모든 요청을 차단할지(fail-closed), 모든 요청을 허용할지(fail-open) 정책을 정해야 한다.

```java
public boolean tryAcquire(String key, long rate, long rateInterval, RateIntervalUnit unit) {
    try {
        RRateLimiter limiter = redissonClient.getRateLimiter("rate-limit:" + key);
        limiter.trySetRate(RateType.OVERALL, rate, rateInterval, unit);
        return limiter.tryAcquire(1);
    } catch (Exception e) {
        // fail-open: Redis 장애 시 요청 허용
        log.warn("Rate limiter unavailable, allowing request: {}", e.getMessage());
        return true;
    }
}
```

### 5. 테넌트/플랜별 동적 한도 관리

SaaS 환경에서는 고객 플랜에 따라 API 한도가 다르다. Free는 분당 100회, Pro는 1000회, Enterprise는 10000회 같은 식이다.

#### 플랜 정의

```java
public enum PricingPlan {
    FREE(100),
    PRO(1000),
    ENTERPRISE(10000);

    private final int requestsPerMinute;

    PricingPlan(int requestsPerMinute) {
        this.requestsPerMinute = requestsPerMinute;
    }

    public int getRequestsPerMinute() {
        return requestsPerMinute;
    }

    public Bandwidth createBandwidth() {
        return Bandwidth.classic(
                requestsPerMinute,
                Refill.greedy(requestsPerMinute, Duration.ofMinutes(1))
        );
    }
}
```

#### 테넌트별 Rate Limiter 서비스

```java
@Service
public class TenantRateLimiterService {

    private final RedissonClient redissonClient;
    private final TenantRepository tenantRepository;

    public TenantRateLimiterService(RedissonClient redissonClient,
                                     TenantRepository tenantRepository) {
        this.redissonClient = redissonClient;
        this.tenantRepository = tenantRepository;
    }

    public RateLimitResult checkRateLimit(String tenantId) {
        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow(() -> new IllegalArgumentException("Unknown tenant: " + tenantId));

        PricingPlan plan = tenant.getPricingPlan();

        RRateLimiter limiter = redissonClient.getRateLimiter("tenant-rate:" + tenantId);
        limiter.trySetRate(
                RateType.OVERALL,
                plan.getRequestsPerMinute(),
                1,
                RateIntervalUnit.MINUTES
        );

        boolean allowed = limiter.tryAcquire(1);
        long remaining = limiter.availablePermits();

        return new RateLimitResult(allowed, remaining, plan.getRequestsPerMinute());
    }
}
```

```java
public record RateLimitResult(boolean allowed, long remaining, int limit) {}
```

#### 필터에서 응답 헤더 설정

```java
@Component
public class TenantRateLimitFilter extends OncePerRequestFilter {

    private final TenantRateLimiterService rateLimiterService;

    public TenantRateLimitFilter(TenantRateLimiterService rateLimiterService) {
        this.rateLimiterService = rateLimiterService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        String tenantId = request.getHeader("X-Tenant-Id");
        if (tenantId == null) {
            response.setStatus(HttpStatus.UNAUTHORIZED.value());
            return;
        }

        RateLimitResult result = rateLimiterService.checkRateLimit(tenantId);

        // RFC 6585에서 권장하는 Rate Limit 헤더
        response.addHeader("X-RateLimit-Limit", String.valueOf(result.limit()));
        response.addHeader("X-RateLimit-Remaining", String.valueOf(result.remaining()));

        if (!result.allowed()) {
            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write(
                    "{\"error\": \"Rate limit exceeded\", \"limit\": " + result.limit() + "}"
            );
            return;
        }

        filterChain.doFilter(request, response);
    }
}
```

#### 플랜 변경 시 한도 갱신

고객이 플랜을 업그레이드하면 기존 Rate Limit 설정을 갱신해야 한다.

```java
@Service
public class PlanUpgradeService {

    private final RedissonClient redissonClient;
    private final TenantRepository tenantRepository;

    public PlanUpgradeService(RedissonClient redissonClient,
                               TenantRepository tenantRepository) {
        this.redissonClient = redissonClient;
        this.tenantRepository = tenantRepository;
    }

    @Transactional
    public void upgradePlan(String tenantId, PricingPlan newPlan) {
        Tenant tenant = tenantRepository.findById(tenantId)
                .orElseThrow();

        tenant.setPricingPlan(newPlan);
        tenantRepository.save(tenant);

        // 기존 Rate Limit 삭제 후 재설정
        RRateLimiter limiter = redissonClient.getRateLimiter("tenant-rate:" + tenantId);
        limiter.delete();
        limiter.trySetRate(
                RateType.OVERALL,
                newPlan.getRequestsPerMinute(),
                1,
                RateIntervalUnit.MINUTES
        );
    }
}
```

`delete()` 후 `trySetRate()`까지의 간격 동안 Rate Limiting이 적용되지 않는다. 트래픽이 많은 서비스에서는 이 갭이 문제될 수 있다. Lua 스크립트로 원자적 갱신을 구현하거나, 갱신 전에 새 키를 먼저 만들고 참조를 교체하는 방식을 쓸 수 있다.

## 실무 주의사항

### 프록시 뒤에서의 IP 식별

로드밸런서나 리버스 프록시 뒤에 서버가 있으면 `request.getRemoteAddr()`가 프록시 IP를 반환한다. `X-Forwarded-For` 헤더를 파싱해야 하는데, 이 헤더는 클라이언트가 조작할 수 있다.

```java
private String resolveClientIp(HttpServletRequest request) {
    String xff = request.getHeader("X-Forwarded-For");
    if (xff != null && !xff.isEmpty()) {
        // 첫 번째 값이 원래 클라이언트 IP
        // 단, 클라이언트가 헤더를 직접 설정할 수 있으므로 신뢰할 수 있는 프록시 개수만큼 뒤에서부터 읽는 게 안전
        String[] ips = xff.split(",");
        // 신뢰할 수 있는 프록시가 1개라면 뒤에서 두 번째
        if (ips.length >= 2) {
            return ips[ips.length - 2].trim();
        }
        return ips[0].trim();
    }
    return request.getRemoteAddr();
}
```

Spring Boot에서는 `server.forward-headers-strategy=framework`를 설정하면 `ForwardedHeaderFilter`가 자동으로 처리해준다.

### 429 응답 설계

Rate Limit 초과 시 클라이언트에게 충분한 정보를 줘야 한다. `Retry-After` 헤더가 있으면 클라이언트가 재시도 타이밍을 잡기 쉽다.

```java
// 응답 헤더 예시
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
Retry-After: 23

{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "분당 100회 요청 한도를 초과했습니다",
    "retryAfter": 23
}
```

### 테스트

Rate Limiting은 테스트가 까다롭다. 시간 기반이라 실제로 기다리면 테스트가 느려진다.

```java
@Test
void rateLimitExceeded() {
    Bucket bucket = Bucket.builder()
            .addLimit(Bandwidth.classic(5, Refill.greedy(5, Duration.ofMinutes(1))))
            .build();

    // 5회는 성공
    for (int i = 0; i < 5; i++) {
        assertThat(bucket.tryConsume(1)).isTrue();
    }

    // 6번째는 실패
    assertThat(bucket.tryConsume(1)).isFalse();
}

@Test
void rateLimitWithMockClock() {
    // Bucket4j는 TimeMeter를 주입할 수 있어서 테스트가 편하다
    TimeMeter timeMeter = new TimeMeter() {
        long currentTimeNanos = System.nanoTime();

        @Override
        public long currentTimeNanos() {
            return currentTimeNanos;
        }

        @Override
        public boolean isWallClockBased() {
            return false;
        }

        // 시간을 앞으로 이동
        public void addSeconds(long seconds) {
            currentTimeNanos += TimeUnit.SECONDS.toNanos(seconds);
        }
    };

    BucketConfiguration config = BucketConfiguration.builder()
            .addLimit(Bandwidth.classic(10, Refill.greedy(10, Duration.ofSeconds(60))))
            .build();

    Bucket bucket = Bucket.builder()
            .withCustomTimePrecision(timeMeter)
            .addLimit(Bandwidth.classic(10, Refill.greedy(10, Duration.ofSeconds(60))))
            .build();

    // 10회 소모
    for (int i = 0; i < 10; i++) {
        bucket.tryConsume(1);
    }

    assertThat(bucket.tryConsume(1)).isFalse();

    // 60초 후 토큰이 다시 채워짐
    ((TimeMeter) timeMeter).addSeconds(60);
    // 실제로는 커스텀 TimeMeter 구현에서 시간을 제어해야 한다
}
```

통합 테스트에서는 실제 엔드포인트를 빠르게 호출해서 429가 돌아오는지 확인한다.

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class RateLimitIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void shouldReturn429WhenRateLimitExceeded() {
        // 한도까지 요청
        for (int i = 0; i < 100; i++) {
            restTemplate.getForEntity("/api/products", String.class);
        }

        // 한도 초과
        ResponseEntity<String> response = restTemplate.getForEntity("/api/products", String.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.TOO_MANY_REQUESTS);
        assertThat(response.getHeaders().get("Retry-After")).isNotNull();
    }
}
```

### 어떤 방식을 써야 하는가

| 상황 | 방식 |
|------|------|
| 단일 서버, 단순한 API 보호 | Bucket4j + Spring Boot Starter |
| API Gateway 구조 | Spring Cloud Gateway RequestRateLimiter |
| 서버 여러 대, Redis 사용 중 | Redisson RRateLimiter |
| 세밀한 제어 필요 | 커스텀 인터셉터 + Bucket4j |
| SaaS, 테넌트별 다른 한도 | Redisson + 테넌트 서비스 조합 |

단순한 경우 Bucket4j Spring Boot Starter로 시작하고, 서버가 늘어나면 Redis 기반으로 전환하는 흐름이 자연스럽다. 처음부터 분산 환경을 고려해서 Redis 기반으로 가도 되지만, Redis 의존성이 추가된다는 점을 감안해야 한다.
