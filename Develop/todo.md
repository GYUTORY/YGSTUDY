---
title: 학습 및 보완 항목
tags: [backend, database, cache, redis, aws, kubernetes, microservices, performance, architecture, design-patterns]
updated: 2026-08-31
---

# 학습 및 보완 항목

5년차 백엔드 개발자 관점에서 완료한 학습과 남은 항목을 기록한다.

## AWS 인프라

**컴퓨팅 & 컨테이너**: EKS, Fargate, Auto Scaling, Elastic Beanstalk를 학습했다. Fargate는 서버 관리 없이 컨테이너를 실행할 수 있지만, GPU 인스턴스나 특수 네트워크 설정이 필요한 경우에는 EC2 기반 노드를 써야 한다.

**메시징 & 스트리밍**: Kinesis, EventBridge, MSK, Step Functions을 다뤘다. EventBridge는 이벤트 스키마 레지스트리를 제공해 서비스 간 이벤트 형태를 관리하기 좋다. SQS+SNS 조합으로 구성했던 팬아웃 패턴이 EventBridge로 단순해졌다.

**데이터베이스 & 캐싱**: DynamoDB, ElastiCache, DMS, DAX를 확인했다. DynamoDB는 인덱스 설계를 처음부터 맞춰야 한다. RDB처럼 쿼리를 나중에 추가하면 GSI 비용이 크게 늘어난다.

**네트워킹 & 보안**: Transit Gateway, PrivateLink, WAF, Shield, ACM, Security Groups, NACLs, VPC Peering을 다뤘다. Security Group은 상태 추적(stateful)이라 인바운드를 허용하면 아웃바운드 응답이 자동 허용된다. NACLs는 상태 비추적(stateless)이라 양방향 모두 규칙이 필요하다. 이 차이를 모르고 NACLs만 열었다가 응답 패킷이 차단된 적이 있다.

**스토리지 & 백업**: EBS, EFS, S3 Glacier, AWS Backup을 확인했다. S3 Glacier는 복구 시간이 표준 검색 기준 3~5시간이라 SLA가 있는 데이터에는 맞지 않는다.

**모니터링 & 로깅**: X-Ray, CloudWatch Logs Insights, CloudWatch Alarms, AWS Config를 설정해봤다. Logs Insights 쿼리 문법이 처음에는 낯설다. `fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50` 같은 기본 패턴부터 시작하는 게 빠르다.

**배포 & CI/CD**: CodePipeline, CodeBuild, CodeDeploy, CodeCommit을 학습했다.

**비용 관리**: Cost Explorer, Budgets, Organizations, SCP를 확인했다. SCP는 루트 계정 접근이나 특정 리전 사용 자체를 막는 용도로 쓴다.

## 캐싱

Cache-Aside, Write-Through, Write-Behind, 캐시 일관성, 캐시 무효화, 로컬 vs 분산 캐시를 실습했다.

**Redis Cache-Aside 구현:**

```java
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;
    private final RedisTemplate<String, User> redisTemplate;

    public User getUser(Long userId) {
        String key = "user:" + userId;
        User cached = redisTemplate.opsForValue().get(key);
        if (cached != null) {
            return cached;
        }
        User user = userRepository.findById(userId)
            .orElseThrow(EntityNotFoundException::new);
        redisTemplate.opsForValue().set(key, user, Duration.ofMinutes(10));
        return user;
    }

    @Transactional
    public void updateUser(User user) {
        userRepository.save(user);
        redisTemplate.delete("user:" + user.getId());
    }
}
```

캐시 삭제 순서가 중요하다. DB 업데이트 전에 캐시를 먼저 삭제하면 그 사이에 다른 요청이 캐시 미스 후 DB에서 읽어 구버전을 캐시에 올린다. DB 업데이트 완료 후 캐시를 삭제해야 한다.

Write-Behind를 쓸 때는 캐시가 내려가면 아직 DB에 반영 안 된 데이터가 날아간다. 결제, 재고 같은 데이터에는 쓰면 안 된다.

**Caffeine 로컬 캐시 설정:**

```java
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager manager = new CaffeineCacheManager("users", "products");
        manager.setCaffeine(Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(Duration.ofMinutes(5))
            .recordStats());
        return manager;
    }
}
```

로컬 캐시는 다중 인스턴스 환경에서 인스턴스마다 다른 값을 들고 있을 수 있다. 한 서버에서 업데이트해도 다른 서버의 캐시는 TTL 만료 전까지 구버전을 반환한다. 변경 빈도가 낮거나 일시적 불일치가 허용되는 데이터(공지사항, 환율 등)에만 써야 한다.

## 데이터베이스 심화

Connection Pool, Optimistic Lock, Pessimistic Lock, 파티셔닝, 쿼리 최적화, N+1 문제, 격리 수준을 학습했다.

**HikariCP 설정:**

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb?socketTimeout=30000&connectTimeout=5000
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 3000        # 풀에서 커넥션 대기 최대 시간 (ms)
      idle-timeout: 600000            # 유휴 커넥션 유지 시간 (ms)
      max-lifetime: 1800000           # 커넥션 최대 수명 — DB wait_timeout보다 반드시 짧게
      validation-timeout: 5000
      leak-detection-threshold: 60000 # 이 시간 안에 반납 안 되면 경고 로그
```

`connectionTimeout`과 `socketTimeout`은 다른 설정이다. `connectionTimeout`은 HikariCP 풀에서 커넥션을 빌리는 대기 시간이고, `socketTimeout`은 JDBC URL에서 설정하며 DB가 쿼리에 응답하는 시간이다. `socketTimeout` 없이 운영하면 DB가 응답하지 않을 때 스레드가 무한 대기한다.

`max-lifetime`은 MySQL의 `wait_timeout`(기본 8시간)보다 짧게 설정해야 한다. 그렇지 않으면 MySQL이 커넥션을 끊었는데 HikariCP는 살아있다고 착각해서 `Communications link failure`가 난다.

**Optimistic Lock 사용:**

```java
@Entity
public class Order {
    @Id @GeneratedValue
    private Long id;

    @Version
    private Long version;

    private OrderStatus status;
    private int quantity;
}
```

```java
@Transactional
public void approveOrder(Long orderId) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    order.setStatus(OrderStatus.APPROVED);
    // flush 시점에 version 충돌 감지 → OptimisticLockingFailureException
}

// 재시도가 필요하면 호출부에서 처리
@Retryable(
    value = OptimisticLockingFailureException.class,
    maxAttempts = 3,
    backoff = @Backoff(delay = 100)
)
public void approveWithRetry(Long orderId) {
    approveOrder(orderId);
}
```

Optimistic Lock은 충돌이 드문 상황에 적합하다. 선착순 좌석 예약처럼 경쟁이 심한 경우에는 재시도가 폭증해서 오히려 느려진다. 그런 경우에는 Pessimistic Lock이 낫다.

Pessimistic Lock을 쓸 때는 락 획득 순서를 코드 전체에서 일관되게 유지해야 한다. 주문과 상품을 잠글 때 어디서는 주문→상품 순서, 어디서는 상품→주문 순서로 잠그면 데드락이 생긴다.

## 장애 대응

Circuit Breaker, Retry, Timeout, Fallback, Health Check를 실습했다.

**Resilience4j Circuit Breaker + Retry 설정:**

```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentService:
        sliding-window-size: 10
        minimum-number-of-calls: 5
        failure-rate-threshold: 50          # 50% 실패율에서 Open 상태로
        wait-duration-in-open-state: 30s    # 30초 후 Half-Open으로 전환
        permitted-number-of-calls-in-half-open-state: 3
        record-exceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException
        ignore-exceptions:
          - com.example.BusinessException    # 비즈니스 예외는 실패로 카운트 안 함
  retry:
    instances:
      paymentService:
        max-attempts: 3
        wait-duration: 1s
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2
        retry-exceptions:
          - java.io.IOException
```

```java
@CircuitBreaker(name = "paymentService", fallbackMethod = "paymentFallback")
@Retry(name = "paymentService")
public PaymentResponse processPayment(PaymentRequest request) {
    return paymentClient.pay(request);
}

public PaymentResponse paymentFallback(PaymentRequest request, Throwable e) {
    log.warn("Payment fallback triggered for order {}: {}", request.getOrderId(), e.getMessage());
    return PaymentResponse.pending(request.getOrderId());
}
```

Circuit Breaker와 Retry를 같이 쓸 때 어노테이션 순서가 실행 순서다. `@Retry`가 바깥, `@CircuitBreaker`가 안쪽이 돼야 Circuit Breaker가 Open일 때 Retry가 시도하지 않는다. 위 예시는 반대로 적혀 있는데, Resilience4j 어노테이션은 안쪽부터 적용되므로 `@CircuitBreaker`를 먼저 쓰면 Retry가 바깥에서 감싸는 구조가 된다.

`record-exceptions`를 지정하지 않으면 모든 예외가 실패 카운트에 들어간다. 입력값 오류처럼 클라이언트 문제인 경우도 Circuit Breaker를 열어버릴 수 있다. `ignore-exceptions`에 비즈니스 예외를 반드시 넣어야 한다.

Fallback 메서드 시그니처는 원래 메서드와 파라미터가 같고 마지막에 `Throwable`을 추가한 형태여야 한다. 타입이 맞지 않으면 Fallback이 동작하지 않고 예외가 그대로 올라온다.

## 앞으로 다룰 영역

**API 설계**: API 버저닝(URL vs Header 방식), gRPC, GraphQL, Rate Limiting, Webhook이 남았다. Rate Limiting은 Redis 기반 Token Bucket 구현이 실무에서 자주 나오는 패턴이라 먼저 다룰 예정이다.

**동시성**: Thread Pool 크기 결정 기준, CompletableFuture 비동기 체인(`thenApply` vs `thenCompose` 차이), WebFlux, Backpressure, Graceful Shutdown, GC 튜닝이 남았다. GC 튜닝은 실제 Heap Dump 분석과 함께 다뤄야 의미 있다.

**보안**: JWT Refresh Token 순환, SSO(SAML 2.0, OpenID Connect), API Gateway 보안, CORS Preflight 처리가 남았다. 기업 환경에서 SSO가 빠지는 경우가 없어서 우선순위가 높다.

**메시징 최적화**: Kafka `batch.size`, `linger.ms` 튜닝, Consumer Group 파티션 설계, 멱등성 처리, Dead Letter Queue 설정이 남았다.

**모니터링**: Jaeger나 Zipkin으로 분산 추적 구성, Trace ID MDC 전파, Micrometer 커스텀 메트릭, ELK 스택 구성이 남았다.

**아키텍처**: Hexagonal Architecture, BFF, Strangler Fig, Bulkhead 패턴은 실제 프로젝트에 적용하면서 다룰 예정이다. Strangler Fig는 레거시가 있는 팀에서 가장 현실적으로 쓰인다.

**배포**: Service Mesh(Istio), Blue-Green/Canary 배포, Feature Flag 구현이 남았다. Canary 배포는 트래픽 가중치 조절 방법을 실습 위주로 정리할 계획이다.

**도메인 설계**: DDD의 Aggregate, Entity, Value Object 구분, Bounded Context, Domain Event, Aggregate Root가 남았다. 개념보다 실제 코드로 경계를 어떻게 그을지를 중심으로 다룰 예정이다.
