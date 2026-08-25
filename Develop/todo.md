---
title: 학습 및 보완 항목
tags: [backend, database, cache, redis, aws, kubernetes, microservices, performance, architecture, design-patterns]
updated: 2026-08-25
---

# 학습 및 보완 항목

5년차 백엔드 개발자 관점에서 실무에 필요한 항목을 정리했다. 우선순위는 현업에서 자주 마주치는 순서다.

## AWS 인프라

### 컴퓨팅 & 컨테이너 (우선순위: 높음)
- [V] **EKS**: 프로덕션에서 Kubernetes 운영 시 필수. ECS와 비교하면서 학습
- [V] **Fargate**: 서버리스 컨테이너 실행. ECS/EKS 운영 부담 줄이는 용도
- [V] **Auto Scaling**: EC2, ECS 스케일링 정책 설정. CPU/메모리 임계값 기반
- [V] **Elastic Beanstalk**: 빠른 배포가 필요한 경우 사용. 하지만 제약사항 많음

### 메시징 & 스트리밍 (우선순위: 높음)
- [V] **Kinesis**: 실시간 로그 처리, 이벤트 스트리밍. SQS로는 부족한 경우
- [V] **EventBridge**: 이벤트 기반 아키텍처. SNS/SQS 조합보다 유연함
- [V] **MSK**: Kafka 관리형 서비스. 직접 운영할 필요 없음
- [V] **Step Functions**: Lambda 여러 개 연결할 때. 워크플로우 시각화 가능

### 데이터베이스 & 캐싱 (우선순위: 높음)
- [V] **DynamoDB**: NoSQL 필요한 경우. 키-값 조회가 많으면 적합
- [V] **ElastiCache**: Redis/Memcached 관리형. 직접 운영보다 편함
- [V] **DMS**: RDS 간 마이그레이션, 온프레미스에서 AWS로 이전
- [V] **DAX**: DynamoDB 앞단 캐시. 읽기 성능 향상

### 네트워킹 & 보안 (우선순위: 중간)
- [V] **Transit Gateway**: 여러 VPC 연결. VPC Peering보다 관리 편함
- [V] **PrivateLink**: 외부 노출 없이 서비스 연결. 보안 강화
- [V] **WAF**: SQL Injection, XSS 방어. ALB 앞단 배치
- [V] **Shield**: DDoS 공격 방어. Standard는 자동 적용됨
- [V] **ACM**: SSL 인증서 자동 갱신. Route 53 + ALB와 연동
- [V] **Security Groups vs NACLs**: 차이점 명확히 알아야 함
- [V] **VPC Peering**: VPC 간 프라이빗 통신

### 스토리지 & 백업 (우선순위: 낮음)
- [V] **EBS**: EC2 볼륨. IOPS, Throughput 타입별 차이
- [V] **EFS**: 여러 EC2에서 파일 공유. NFS 프로토콜
- [V] **S3 Glacier**: 장기 보관용. 비용 저렴하지만 복구 느림
- [V] **AWS Backup**: RDS, EBS 자동 백업 설정

### 모니터링 & 로깅 (우선순위: 높음)
- [V] **X-Ray**: 분산 추적. Lambda, ECS 호출 흐름 파악
- [V] **CloudWatch Logs Insights**: 로그 쿼리. SQL 비슷한 문법
- [V] **CloudWatch Alarms**: CPU, 메모리, 큐 깊이 알람 설정
- [V] **AWS Config**: 리소스 변경 추적. 컴플라이언스 체크

### 배포 & CI/CD (우선순위: 중간)
- [V] **CodePipeline**: GitHub Actions, Jenkins 대체 가능
- [V] **CodeBuild**: Docker 이미지 빌드, 테스트 실행
- [V] **CodeDeploy**: Blue-Green, Canary 배포 지원
- [V] **CodeCommit**: Git 저장소. GitHub/GitLab 대신 사용 가능

### 비용 & 거버넌스 (우선순위: 중간)
- [V] **Cost Explorer**: 비용 분석. 어디서 돈 나가는지 파악
- [V] **Budgets**: 예산 초과 시 알림
- [V] **Organizations**: 멀티 어카운트 관리. 개발/스테이징/프로덕션 분리
- [V] **SCP**: 조직 단위 정책. 특정 리전 사용 제한 등

## 백엔드 아키텍처

### API 설계 (우선순위: 높음)
- [ ] **API 버저닝**: URL 방식 vs Header 방식. 하위 호환성 유지 방법
- [ ] **GraphQL**: REST API 한계 있을 때. 단일 엔드포인트로 여러 리소스 조회
- [ ] **gRPC**: 내부 서비스 간 통신. HTTP/2 기반, Protobuf 사용
- [ ] **Rate Limiting**: Token Bucket, Leaky Bucket 알고리즘. Redis 기반 구현
- [ ] **Webhook**: 이벤트 발생 시 외부에 알림. Retry, Timeout 처리

### 캐싱 (우선순위: 높음)
- [V] **Cache-Aside**: 애플리케이션에서 캐시 직접 관리
- [V] **Write-Through**: 쓰기 시 캐시도 업데이트
- [V] **Write-Behind**: 쓰기를 캐시에만 하고 나중에 DB 반영
- [V] **캐시 일관성**: 분산 환경에서 캐시 동기화. Pub/Sub 활용
- [V] **캐시 무효화**: TTL, 수동 삭제, 태그 기반 무효화
- [V] **로컬 vs 분산 캐시**: Caffeine vs Redis. 사용 시점 구분

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

캐시 삭제 순서가 중요하다. DB 업데이트 전에 캐시를 먼저 삭제하면 그 사이에 다른 요청이 캐시 미스 후 DB에서 읽고 구버전을 캐시에 올린다. DB 업데이트 완료 후 캐시를 삭제해야 한다.

Write-Behind를 쓸 때는 캐시가 내려가면 아직 DB에 반영 안 된 데이터가 날아간다. 결제, 재고 같은 데이터에는 절대 쓰면 안 된다.

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

로컬 캐시는 다중 인스턴스 환경에서 인스턴스마다 다른 값을 들고 있을 수 있다. 한 서버에서 업데이트해도 다른 서버의 캐시는 TTL 만료 전까지 구버전을 반환한다. 변경 빈도가 낮거나 일시적 불일치가 허용되는 데이터(공지사항, 환율 등)에만 쓴다.

### 데이터베이스 심화 (우선순위: 높음)
- [V] **Connection Pool**: HikariCP 설정. maximumPoolSize, connectionTimeout
- [V] **Optimistic Lock**: 버전 번호 체크. 동시 수정 감지
- [V] **Pessimistic Lock**: SELECT FOR UPDATE. 데드락 주의
- [V] **파티셔닝**: Range, List, Hash. 테이블 크기 커질 때
- [V] **Query 최적화**: EXPLAIN ANALYZE. 인덱스 활용도 체크
- [V] **N+1 문제**: Fetch Join, @EntityGraph. Lazy Loading 주의
- [V] **격리 수준**: Read Committed, Repeatable Read. Phantom Read 차이

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

### 동시성 & 성능 (우선순위: 높음)
- [ ] **Thread Pool**: Core, Max 크기 결정. Queue 용량 설정
- [ ] **CompletableFuture**: 비동기 체인. thenApply, thenCompose 차이
- [ ] **Reactive**: WebFlux, Reactor. 높은 동시 연결 필요할 때
- [ ] **Backpressure**: 프로듀서가 컨슈머보다 빠를 때 제어
- [ ] **Graceful Shutdown**: 진행 중인 요청 완료 대기. SIGTERM 처리
- [ ] **GC 튜닝**: G1GC, ZGC 선택. Heap 크기, Young/Old 비율

### 보안 (우선순위: 높음)
- [ ] **JWT Refresh Token**: Access Token 짧게, Refresh Token 길게
- [ ] **Token Rotation**: Refresh Token 재발급 시 갱신
- [ ] **SSO**: SAML 2.0, OpenID Connect. 기업 환경 필수
- [ ] **API Gateway 보안**: Kong, Tyk, AWS API Gateway
- [ ] **CORS Preflight**: OPTIONS 요청 처리. withCredentials 설정
- [ ] **Input Validation**: Bean Validation, 커스텀 검증 로직

### 메시징 (우선순위: 높음)
- [ ] **Kafka 최적화**: batch.size, linger.ms, compression.type
- [ ] **Consumer Group**: 파티션 개수와 컨슈머 수 관계
- [ ] **RabbitMQ**: Direct, Fanout, Topic Exchange 차이
- [ ] **멱등성**: 메시지 ID 기반 중복 체크. Redis Set 활용
- [ ] **순서 보장**: Partition Key, Message Group ID 사용
- [ ] **Dead Letter**: 재시도 횟수 초과 시 별도 큐로 이동

### 모니터링 & 관찰성 (우선순위: 높음)
- [ ] **Distributed Tracing**: Jaeger, Zipkin, AWS X-Ray
- [ ] **Trace ID 전파**: HTTP Header, MDC 활용
- [ ] **커스텀 메트릭**: Micrometer, Prometheus Client
- [ ] **로그 집계**: ELK Stack, Grafana Loki
- [ ] **SLI/SLO/SLA**: 가용성 99.9%, 응답 시간 p95 < 200ms
- [ ] **알림 피로도**: 중요도 분류. 야간 알림 최소화

### 테스트 (우선순위: 중간)
- [ ] **Contract Testing**: 마이크로서비스 간 계약 검증
- [ ] **성능 테스트**: JMeter 스크립트, k6 시나리오
- [ ] **Chaos Engineering**: 네트워크 지연, 서비스 다운 시뮬레이션
- [ ] **E2E 테스트**: Selenium, Cypress. CI에 통합
- [ ] **테스트 커버리지**: 80% 목표는 의미 없음. 핵심 로직 위주

### 아키텍처 패턴 (우선순위: 중간)
- [ ] **Hexagonal Architecture**: 도메인 로직과 인프라 분리
- [ ] **Clean Architecture**: Usecase, Entity, Gateway 계층
- [ ] **BFF**: iOS/Android/Web 각각 다른 API
- [ ] **API Composition**: 여러 마이크로서비스 결과 합침
- [ ] **Strangler Fig**: 레거시 점진적 교체. Proxy 패턴 활용
- [ ] **Bulkhead**: 스레드 풀 분리. 장애 전파 차단

### 데이터 처리 (우선순위: 중간)
- [ ] **Batch Processing**: Spring Batch. Chunk 단위 처리
- [ ] **Job Scheduling**: Quartz, @Scheduled. 분산 환경 고려
- [ ] **ETL Pipeline**: Extract, Transform, Load. Airflow 활용
- [ ] **CDC**: Debezium, AWS DMS. 데이터 변경 캡처
- [ ] **Data Versioning**: Schema 변경 관리. Flyway, Liquibase

### 배포 (우선순위: 중간)
- [ ] **Service Mesh**: Istio, Linkerd. 트래픽 관리, 보안
- [ ] **Blue-Green**: 새 버전 배포 후 트래픽 전환. 롤백 빠름
- [ ] **Canary**: 일부 트래픽만 새 버전으로. 점진적 확대
- [ ] **Feature Flag**: LaunchDarkly, Unleash. 배포와 릴리스 분리
- [ ] **Container Security**: Trivy, Clair. 이미지 취약점 스캔

### 성능 최적화 (우선순위: 중간)
- [ ] **Connection Pool 튜닝**: 최적 크기는 CPU 코어 수 * 2 정도
- [ ] **Heap Dump 분석**: VisualVM, MAT. 메모리 누수 찾기
- [ ] **CPU 프로파일링**: async-profiler. 병목 메서드 찾기
- [ ] **HTTP/2**: 멀티플렉싱. 단일 연결로 여러 요청
- [ ] **압축**: Gzip, Brotli. 응답 크기 줄이기

### 도메인 설계 (우선순위: 낮음)
- [ ] **DDD**: Aggregate, Entity, Value Object 구분
- [ ] **Bounded Context**: 도메인 경계 설정. 서로 다른 용어 사용
- [ ] **Domain Event**: 도메인 로직에서 이벤트 발행
- [ ] **Aggregate Root**: 트랜잭션 경계. 일관성 보장 범위

### 장애 대응 (우선순위: 높음)
- [V] **Circuit Breaker**: Resilience4j. 연속 실패 시 회로 차단
- [V] **Retry**: Exponential Backoff. 1초, 2초, 4초, 8초...
- [V] **Timeout**: Connection, Read, Write 각각 설정
- [V] **Fallback**: 기본값 반환, 캐시 사용, 다른 서비스 호출
- [V] **Health Check**: Liveness(프로세스 살아있는지), Readiness(요청 받을 준비)

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

## 학습 순서 (실무 기준)

### 1개월 차: 인프라 기초
1. EKS + Service Mesh (Istio)
2. Kinesis + Kafka
3. X-Ray + Distributed Tracing
4. ElastiCache + 캐싱 전략

### 2개월 차: API & 보안
1. API Gateway 패턴 (Rate Limiting, Circuit Breaker)
2. JWT + SSO
3. gRPC
4. GraphQL

### 3개월 차: 성능 & 모니터링
1. 성능 테스트 (JMeter, k6)
2. 커스텀 메트릭 + SLI/SLO
3. Connection Pool 튜닝
4. GC 튜닝

### 4개월 차: 아키텍처 & 설계
1. DDD + Hexagonal Architecture
2. BFF + API Composition
3. Blue-Green + Canary 배포
4. Feature Flag

### 5개월 차: 비용 & 운영
1. AWS Cost Explorer
2. 장애 대응 패턴
3. Chaos Engineering
4. 로그 집계 + 분석

## 참고

실무에서 자주 쓰는 순서대로 정리했다. 모든 항목을 다 알 필요는 없다. 현재 팀에서 사용하는 기술 스택에 맞춰서 선택적으로 학습한다.

우선순위 '높음'은 반드시 알아야 하고, '중간'은 필요할 때 찾아보면 되고, '낮음'은 나중에 천천히 학습한다.
