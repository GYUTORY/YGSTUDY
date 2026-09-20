---
title: 학습 및 보완 항목
tags: [backend, database, cache, redis, aws, kubernetes, microservices, performance, architecture, design-patterns, testing]
updated: 2026-09-20
---

# 학습 및 보완 항목

5년차 백엔드 개발자 관점에서 완료한 학습과 남은 항목을 기록한다.

## 완료

### AWS 인프라

**컴퓨팅 & 컨테이너**: EKS, Fargate, Auto Scaling, Elastic Beanstalk를 학습했다. Fargate는 서버 관리 없이 컨테이너를 실행할 수 있지만, GPU 인스턴스나 특수 네트워크 설정이 필요한 경우에는 EC2 기반 노드를 써야 한다.

**메시징 & 스트리밍**: Kinesis, EventBridge, MSK, Step Functions을 다뤘다. EventBridge는 이벤트 스키마 레지스트리를 제공해 서비스 간 이벤트 형태를 관리하기 좋다. SQS+SNS 조합으로 구성했던 팬아웃 패턴이 EventBridge로 단순해졌다.

**데이터베이스 & 캐싱**: DynamoDB, ElastiCache, DMS, DAX를 확인했다. DynamoDB는 인덱스 설계를 처음부터 맞춰야 한다. RDB처럼 쿼리를 나중에 추가하면 GSI 비용이 크게 늘어난다.

**네트워킹 & 보안**: Transit Gateway, PrivateLink, WAF, Shield, ACM, Security Groups, NACLs, VPC Peering을 다뤘다. Security Group은 상태 추적(stateful)이라 인바운드를 허용하면 아웃바운드 응답이 자동 허용된다. NACLs는 상태 비추적(stateless)이라 양방향 모두 규칙이 필요하다. 이 차이를 모르고 NACLs만 열었다가 응답 패킷이 차단된 적이 있다.

**스토리지 & 백업**: EBS, EFS, S3 Glacier, AWS Backup을 확인했다. S3 Glacier는 복구 시간이 표준 검색 기준 3~5시간이라 SLA가 있는 데이터에는 맞지 않는다.

**모니터링 & 로깅**: X-Ray, CloudWatch Logs Insights, CloudWatch Alarms, AWS Config를 설정해봤다. Logs Insights 쿼리 문법이 처음에는 낯설다. `fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50` 같은 기본 패턴부터 시작하는 게 빠르다.

**배포 & CI/CD**: CodePipeline, CodeBuild, CodeDeploy, CodeCommit을 학습했다.

**비용 관리**: Cost Explorer, Budgets, Organizations, SCP를 확인했다. SCP는 루트 계정 접근이나 특정 리전 사용 자체를 막는 용도로 쓴다.

### 캐싱

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

### 데이터베이스 심화

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

### 장애 대응

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

### 테스트

TDD, Testcontainers 통합 테스트, Spring Cloud Contract 계약 테스트, k6 성능 테스트를 실습했다.

**TDD — Red → Green → Refactor:**

테스트를 먼저 쓰면 구현이 없는 상태에서 메서드 이름, 파라미터, 반환 타입을 결정하게 된다. 인터페이스 설계가 먼저 나온다는 게 핵심이다.

```java
// Red: 컴파일도 안 되는 테스트를 먼저 쓴다
@Test
void 포인트_충전_시_잔액이_증가한다() {
    Member member = new Member(1L, 1000);

    member.chargePoint(500);

    assertThat(member.getPoint()).isEqualTo(1500);
}
```

```java
// Green: 테스트를 통과하는 최소 코드만 작성한다
public class Member {
    private Long id;
    private int point;

    public Member(Long id, int point) {
        this.id = id;
        this.point = point;
    }

    public void chargePoint(int amount) {
        this.point += amount;
    }

    public int getPoint() {
        return point;
    }
}
```

```java
// Refactor: 테스트를 유지하면서 도메인 규칙을 추가한다
public void chargePoint(int amount) {
    if (amount <= 0) {
        throw new IllegalArgumentException("충전 금액은 0보다 커야 합니다");
    }
    this.point += amount;
}

// 새 케이스를 테스트로 추가한다
@Test
void 충전_금액이_0이하면_예외가_발생한다() {
    Member member = new Member(1L, 1000);

    assertThatThrownBy(() -> member.chargePoint(0))
        .isInstanceOf(IllegalArgumentException.class);
}
```

처음에는 "구현도 없는데 테스트를 어떻게 써?" 하는 느낌이 강하다. 그게 정상이다. 컴파일 오류를 보면서 인터페이스를 결정하는 과정 자체가 TDD의 설계 단계다.

**Testcontainers 통합 테스트:**

목(Mock)으로 Repository 테스트를 짜면 JPA 엔티티 매핑, 커스텀 쿼리, 인덱스 누락 같은 문제는 잡히지 않는다. 실제 DB 컨테이너를 올려서 테스트해야 한다.

```java
@SpringBootTest
@Testcontainers
class UserRepositoryTest {

    @Container
    static MySQLContainer<?> mysql = new MySQLContainer<>("mysql:8.0")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", mysql::getJdbcUrl);
        registry.add("spring.datasource.username", mysql::getUsername);
        registry.add("spring.datasource.password", mysql::getPassword);
    }

    @Autowired
    UserRepository userRepository;

    @Test
    void 사용자_저장_후_이메일로_조회한다() {
        User user = new User("test@example.com", "testuser");
        userRepository.save(user);

        Optional<User> found = userRepository.findByEmail("test@example.com");

        assertThat(found).isPresent();
        assertThat(found.get().getUsername()).isEqualTo("testuser");
    }
}
```

`@Container static`으로 선언하면 테스트 클래스 전체에서 컨테이너 하나를 공유한다. `static`을 빼면 테스트 메서드마다 새 컨테이너가 뜨는데, MySQL 컨테이너 기동에 3~5초가 걸려 테스트 수가 늘면 CI 시간이 눈에 띄게 길어진다.

여러 테스트 클래스에서 동일 컨테이너를 재사용하려면 `~/.testcontainers.properties`에 `testcontainers.reuse.enable=true`를 설정하고 컨테이너 선언에 `.withReuse(true)`를 붙인다. 단, 테스트 격리가 필요하다면 각 테스트에서 상태를 직접 정리해야 한다.

**Spring Cloud Contract 계약 테스트:**

API를 소비하는 쪽(Consumer)이 먼저 계약을 작성하고, 제공하는 쪽(Producer)이 그 계약을 만족하는지 테스트로 검증한다. Consumer가 응답에서 새 필드를 기대하면 Producer 계약 테스트가 배포 전에 먼저 실패한다.

```groovy
// consumer/src/test/resources/contracts/payment/get_payment_status.groovy
import org.springframework.cloud.contract.spec.Contract

Contract.make {
    request {
        method 'GET'
        url '/payments/1'
    }
    response {
        status 200
        body([
            id: 1,
            status: 'COMPLETED',
            amount: 10000
        ])
        headers {
            contentType applicationJson()
        }
    }
}
```

Producer 쪽에서는 계약 파일을 기반으로 테스트가 자동 생성된다. 베이스 클래스만 직접 작성한다.

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
public abstract class PaymentContractBase {

    @Autowired
    MockMvc mockMvc;

    @BeforeEach
    void setup() {
        RestAssuredMockMvc.mockMvc(mockMvc);
    }
}
```

`build.gradle`에 Spring Cloud Contract Verifier 플러그인을 추가하면 Groovy 계약 파일로부터 테스트 코드가 생성된다. Consumer 팀이 계약 파일로 PR을 열고, Producer 팀이 그 계약을 통과할 때까지 코드를 수정하는 흐름이 실무에서 자주 쓰인다. 구두 합의나 Swagger 문서 대신 코드가 계약 역할을 한다.

**k6 성능 테스트:**

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // 30초 동안 10 VU로 증가
    { duration: '1m', target: 50 },   // 1분 동안 50 VU 유지
    { duration: '30s', target: 0 },   // 30초 동안 0으로 감소
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95th 백분위 응답시간 500ms 미만
    http_req_failed: ['rate<0.01'],    // 실패율 1% 미만
  },
};

export default function () {
  const res = http.get('http://localhost:8080/api/users/1');

  check(res, {
    '상태 코드 200': (r) => r.status === 200,
    '응답시간 500ms 미만': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

```bash
k6 run script.js
```

처음 부하 테스트를 할 때는 `stages` 대신 `-u 10 -d 30s` 옵션으로 고정 부하를 먼저 보는 게 결과 해석이 쉽다. `stages`는 부하를 단계적으로 올리는 패턴이라 응답시간이 언제 나빠지는지 찾는 용도다.

`thresholds`를 설정해두면 기준 미달 시 종료 코드가 1이 된다. CI 파이프라인에서 `k6 run script.js`를 실행하면 성능 기준 미달을 빌드 실패로 처리할 수 있다.

### DB 마이그레이션

Flyway로 스키마 버전을 관리하는 방법과 운영 중 자주 나오는 문제를 실습했다.

Flyway는 마이그레이션 파일을 버전 순서로 적용하고 `flyway_schema_history` 테이블로 이력을 추적한다. 이미 적용된 파일은 다시 실행하지 않는다.

```
src/main/resources/db/migration/
├── V1__create_users_table.sql
├── V2__add_email_index.sql
└── V3__add_orders_table.sql
```

```sql
-- V1__create_users_table.sql
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```yaml
spring:
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: false  # 기존 DB에 처음 Flyway를 도입할 때만 true
    validate-on-migrate: true   # 체크섬 검증 — 적용된 파일을 수정하면 기동 실패
```

운영에서 자주 나오는 실수들이다.

이미 적용된 파일을 수정하면 `validate-on-migrate: true` 상태에서 앱 기동 시 바로 실패한다. 파일을 수정하는 대신 새 버전 파일을 만들어야 한다. V2에 실수가 있으면 V3으로 수정한다.

Flyway 오픈소스 버전은 자동 롤백을 지원하지 않는다. V3 마이그레이션을 취소하려면 V4에 역방향 DDL을 직접 써야 한다.

MySQL에서 `ALTER TABLE`은 암묵적 커밋을 발생시킨다. 같은 파일에 DDL과 DML을 섞으면 DDL 실패 시 DML만 롤백되고 DDL은 남는다. DDL과 DML은 파일을 분리한다.

기존 운영 DB에 Flyway를 처음 도입할 때는 `baseline-on-migrate: true`로 현재 상태를 기준선으로 잡고, 이후 변경부터 마이그레이션 파일로 관리한다. 기준선 이전 파일을 실행하지 않으므로 기존 테이블과 충돌하지 않는다.

## 진행 중

모니터링 설정(Jaeger/Zipkin 분산 추적, Trace ID MDC 전파)을 코드 예제 위주로 정리 중이다. CompletableFuture 비동기 체인(`thenApply` vs `thenCompose`)과 WebFlux Backpressure는 실습 환경을 구성하고 있다.

## 예정

**API 설계**: API 버저닝(URL vs Header 방식), gRPC, GraphQL, Webhook이 남았다.

**동시성**: Thread Pool 크기 결정 기준, CompletableFuture 비동기 체인, WebFlux, Backpressure, Graceful Shutdown, GC 튜닝이 남았다. GC 튜닝은 실제 Heap Dump 분석과 함께 다뤄야 의미 있다.

**보안**: API Gateway 보안, CORS Preflight 처리가 남았다. JWT Refresh Token 순환, OAuth2/OIDC 플로우, SSO(SAML 2.0)는 완료됐다.

**메시징 최적화**: Kafka `batch.size`, `linger.ms` 튜닝, Consumer Group 파티션 설계, 멱등성 처리가 남았다. Dead Letter Queue 설정은 완료됐다.

**모니터링**: Jaeger/Zipkin 분산 추적 구성, Trace ID MDC 전파, Micrometer 커스텀 메트릭, ELK 스택 구성이 남았다.

**아키텍처**: Hexagonal Architecture, BFF, Strangler Fig 패턴이 남았다. Bulkhead 패턴은 완료됐다. Strangler Fig는 레거시가 있는 팀에서 가장 현실적으로 쓰인다.

**배포**: Service Mesh(Istio), Blue-Green/Canary 배포, Feature Flag 구현이 남았다. Canary 배포는 트래픽 가중치 조절 방법을 실습 위주로 정리할 계획이다.

**도메인 설계**: DDD의 Aggregate, Entity, Value Object 구분, Bounded Context, Domain Event, Aggregate Root가 남았다. 개념보다 실제 코드로 경계를 어떻게 그을지를 중심으로 다룰 예정이다.
