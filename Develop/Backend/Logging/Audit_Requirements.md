---
title: 감사 요구사항
tags: [security, java, spring, nodejs, observability, backend, messaging]
updated: 2026-09-23
---

# 감사 요구사항

감사 로그(Audit Log)는 일반 애플리케이션 로그와 목적이 다르다. 애플리케이션 로그는 디버깅과 운영 모니터링을 위해 쓰지만, 감사 로그는 "누가, 언제, 무엇을 했는가"를 법적·규정적으로 증명하기 위해 존재한다. 장애 분석이 아니라 감사(audit)와 책임 추적(accountability)이 목적이다.

금융권 프로젝트에서 개인정보 유출 사고가 났을 때, 감사 로그가 제대로 없으면 누가 어떤 데이터를 언제 조회했는지 추적할 방법이 없다. 당시 일반 애플리케이션 로그만 있어서 "접근 시도"는 파악됐지만 "실제 어떤 데이터를 가져갔는지"는 복원하지 못했다.

## 기록 대상 이벤트

감사 로그에 기록해야 하는 이벤트는 크게 네 범주로 나뉜다.

**인증 관련 이벤트**는 로그인 성공/실패, 로그아웃, 비밀번호 변경, MFA 등록/해제, 세션 만료, 잠금 해제 등이다. 실패한 로그인 시도도 반드시 남겨야 한다. 브루트포스 공격 탐지와 계정 탈취 여부 판단에 필수다.

**데이터 접근 이벤트**는 민감 데이터 조회, 생성, 수정, 삭제다. 일반 목록 조회는 선택이지만 개인정보·금융정보·의료정보처럼 민감 데이터는 읽기 행위 자체를 기록해야 한다. PCI DSS는 카드 데이터에 접근하는 모든 행위를 요구하고, GDPR은 개인정보 처리 행위를 기록하게 한다.

**권한 변경 이벤트**는 역할(role) 부여/회수, 권한(permission) 변경, 관리자 계정 생성/삭제다. 권한 변경이 감사 로그에 없으면 내부자 위협을 사후에 추적하기 어렵다.

**시스템 설정 변경 이벤트**는 애플리케이션 설정, 암호화 키 교체, API 키 발급/폐기, 방화벽 규칙 변경 등이다. 설정 변경은 변경 전후 값을 함께 남겨야 한다.

## 감사 로그 포맷

감사 로그는 아래 필드를 포함해야 한다. 각 필드는 나중에 쿼리할 것을 고려해 구조화된 형태로 저장한다.

```json
{
  "audit_id": "01J5K2X9P3QRST4UVWXY",
  "timestamp": "2026-08-03T14:23:45.123Z",
  "actor": {
    "user_id": "usr_8f3k2p",
    "email": "admin@example.com",
    "ip": "203.0.113.45",
    "user_agent": "Mozilla/5.0 ...",
    "session_id": "sess_9x2m1n"
  },
  "action": {
    "type": "DATA_UPDATE",
    "category": "USER_MANAGEMENT"
  },
  "resource": {
    "type": "User",
    "id": "usr_target_1234",
    "name": "홍길동"
  },
  "before": {
    "role": "VIEWER",
    "email": "hong@example.com"
  },
  "after": {
    "role": "ADMIN",
    "email": "hong@example.com"
  },
  "result": "SUCCESS",
  "metadata": {
    "service": "user-service",
    "version": "2.1.0",
    "trace_id": "tr_abc123"
  }
}
```

`before`와 `after`는 민감 정보 노출에 주의해야 한다. 비밀번호 같은 필드는 `"[REDACTED]"`로 마스킹하고, 카드번호는 마지막 4자리만 남긴다. 그래도 변경 사실 자체는 기록해야 한다.

`actor.ip`는 프록시 뒤에 있는 실제 클라이언트 IP를 기록해야 한다. `X-Forwarded-For` 헤더를 그대로 믿으면 클라이언트가 조작할 수 있으므로, 신뢰할 수 있는 프록시 구간에서만 파싱하거나 로드밸런서가 주입한 `X-Real-IP`를 사용한다.

`audit_id`는 ULID나 UUID v7처럼 시간 순서가 보장되는 ID를 쓰는 것이 검색 성능 면에서 낫다.

## 불변성 보장

감사 로그의 핵심 속성은 사후 수정이 불가능해야 한다는 것이다. 관리자가 실수나 고의로 로그를 지우거나 변조할 수 없는 구조를 만들어야 한다.

**Append-Only 스토리지**

데이터베이스 레벨에서 UPDATE, DELETE 권한을 감사 로그 테이블에 부여하지 않는다. 애플리케이션 DB 유저는 INSERT와 SELECT만 허용한다.

```sql
-- 감사 로그 전용 DB 유저 생성
CREATE USER audit_writer WITH PASSWORD '...';
GRANT INSERT, SELECT ON audit_logs TO audit_writer;
-- UPDATE, DELETE 권한은 부여하지 않음
```

PostgreSQL이면 Row Security Policy로 추가 제한도 걸 수 있다.

**외부 스토리지 분리**

애플리케이션 DB와 다른 스토리지에 감사 로그를 보낸다. AWS CloudTrail, AWS S3(Object Lock), Elasticsearch 전용 클러스터, 또는 전용 SIEM 시스템이 옵션이다. S3 Object Lock의 Compliance 모드는 루트 계정으로도 삭제가 불가능하다.

**암호화 서명**

각 감사 로그 항목에 HMAC-SHA256 서명을 붙이면 저장된 레코드가 변조됐는지 검증할 수 있다. 서명 키는 KMS 같은 외부 키 관리 시스템에 보관한다.

```typescript
import { createHmac } from 'crypto';

function signAuditLog(log: AuditLog, secret: string): string {
  const payload = JSON.stringify({
    audit_id: log.audit_id,
    timestamp: log.timestamp,
    actor: log.actor,
    action: log.action,
    resource: log.resource,
  });
  return createHmac('sha256', secret).update(payload).digest('hex');
}
```

검증 시 동일한 페이로드로 서명을 재계산해서 저장된 서명과 비교한다. 불일치하면 해당 레코드가 수정됐다는 의미다.

**로그 체이닝**

각 레코드에 이전 레코드의 서명을 포함시키는 방법도 있다. 블록체인과 유사한 구조로, 중간 레코드 하나를 변조하면 이후 모든 레코드의 서명이 깨진다. 구현 복잡도가 높지만 규제 요구가 강한 환경에서 쓴다.

## 애플리케이션 로그와 분리하는 이유

감사 로그를 일반 애플리케이션 로그와 같은 파이프라인에 섞으면 생기는 문제가 있다.

**보존 기간 불일치**: 애플리케이션 로그는 보통 30~90일이면 충분하지만, 감사 로그는 규제에 따라 1~7년을 보관해야 한다. 같은 파이프라인에 있으면 한쪽 정책이 다른 쪽에 영향을 준다.

**접근 제어 불일치**: 감사 로그는 보안팀과 컴플라이언스 담당자만 접근해야 하는 경우가 많다. 운영팀이 자유롭게 볼 수 있는 애플리케이션 로그와 섞이면 접근 제어가 복잡해진다.

**무결성 요구**: 운영 로그는 장애 상황에서 일부 유실돼도 큰 문제가 없지만, 감사 로그는 유실이 규정 위반이다. 별도 파이프라인에서 높은 내구성 설정(예: Kafka `acks=all`, `min.insync.replicas=2`)을 적용해야 한다.

**볼륨 및 비용 분리**: 트래픽이 많은 서비스에서 모든 API 호출 로그가 감사 로그 스토리지에 들어가면 비용이 폭발한다. 감사 대상만 선별해서 더 비싼 장기 스토리지에 보내는 것이 맞다.

## 규제별 보존 기간

| 규제 | 대상 | 보존 기간 | 주요 요구 |
|------|------|-----------|-----------|
| PCI DSS v4.0 | 카드 데이터 처리 환경 | 최소 12개월 (3개월은 즉시 조회 가능) | 카드 데이터 접근, 관리자 행위, 보안 이벤트 |
| GDPR | EU 개인정보 처리 | 명시 없음 (처리 목적 종료 후 삭제) | 개인정보 접근·처리·이전 내역 |
| 전자금융거래법 | 국내 금융기관 | 5년 | 전자금융거래 기록, 접근 로그 |
| 정보통신망법 | 개인정보 처리 서비스 | 3년 (접속 기록) | 개인정보 처리 시스템 접속 기록 |
| 의료법 | 전자의무기록 | 10년 | 진료 기록 접근 및 수정 이력 |

GDPR은 보존 기간을 명시하지 않는 대신 "처리 목적이 소멸하면 삭제"를 요구하므로, 감사 로그 보존 정책을 데이터 처리 목적과 연동해야 한다. 실무에서는 법무팀과 협의해 2~3년을 기본 정책으로 잡는 경우가 많다.

보존 기간이 지난 감사 로그를 삭제할 때도 로그를 남긴다. 언제 어떤 범위의 로그를 삭제했는지 기록하지 않으면, 나중에 "해당 기간 로그가 없는 이유"를 설명하지 못한다.

## 비동기 파이프라인 — Kafka

감사 로그 저장을 메인 트랜잭션에 직접 결합하면 감사 로그 DB 장애가 서비스 전체 장애로 번진다. Kafka를 중간에 두면 프로듀서(애플리케이션 서버)와 컨슈머(감사 로그 저장소)를 분리할 수 있다.

토픽 설정에서 `replication.factor=3`, `min.insync.replicas=2`, `acks=all`을 맞춰야 브로커 1대가 죽어도 메시지를 잃지 않는다. 프로듀서에서는 `enable.idempotence=true`를 설정해 재시도 시 중복 쓰기를 막는다.

```java
// Kafka 프로듀서 — 감사 이벤트 발행
@Component
public class AuditEventProducer {

    private final KafkaTemplate<String, AuditEvent> kafkaTemplate;
    private static final String TOPIC = "audit-events";

    public void send(AuditEvent event) {
        kafkaTemplate.send(TOPIC, event.getAuditId(), event)
            .whenComplete((result, ex) -> {
                if (ex != null) {
                    log.error("Audit event send failed: auditId={}", event.getAuditId(), ex);
                    alertService.notifyCritical("AUDIT_PRODUCE_FAILURE", event.getAuditId());
                }
            });
    }
}
```

```java
// Kafka 컨슈머 — 감사 이벤트 저장
@Component
public class AuditEventConsumer {

    private final AuditLogRepository auditLogRepository;

    @KafkaListener(
        topics = "audit-events",
        groupId = "audit-consumer",
        containerFactory = "auditKafkaListenerContainerFactory"
    )
    public void consume(AuditEvent event) {
        auditLogRepository.save(AuditLog.from(event));
    }
}
```

컨슈머 설정에서 `enable.auto.commit=false`를 명시하고 수동 커밋을 써야 한다. DB 저장이 완료된 뒤에만 오프셋을 커밋하지 않으면, 저장 직후 컨슈머가 죽었을 때 재처리 시 중복이 발생한다.

**SQS 사용 시**

Kafka 대신 SQS를 쓰는 경우 `MessageRetentionPeriod`를 최소 345,600초(4일)로 설정한다. `VisibilityTimeout`은 컨슈머 처리 시간의 6배 이상으로 잡아야 처리 중 다른 컨슈머가 같은 메시지를 가져가는 상황을 막는다.

```java
@SqsListener("audit-events-queue")
public void processAuditEvent(AuditEvent event) {
    try {
        auditLogRepository.save(AuditLog.from(event));
    } catch (Exception e) {
        // 예외를 다시 던지면 SQS가 VisibilityTimeout 후 재전송
        throw new RuntimeException("Audit log save failed", e);
    }
}
```

## 저장 실패 처리 — DLQ와 재시도

감사 로그 저장이 실패했을 때 조용히 넘어가는 구조는 규제 환경에서 허용되지 않는다. 실패를 감지하고, 재처리하고, 끝내 처리하지 못한 것을 격리하는 메커니즘이 필요하다.

**Kafka — Dead Letter Topic**

컨슈머에서 처리 실패 시 Dead Letter Topic으로 보내도록 설정한다. `@RetryableTopic`을 쓰면 재시도 횟수와 DLT 토픽을 선언적으로 지정할 수 있다.

```java
@Component
public class AuditEventConsumer {

    @RetryableTopic(
        attempts = "4",                          // 최초 1회 + 재시도 3회
        backoff = @Backoff(delay = 1000, multiplier = 2.0),
        dltTopicSuffix = "-dlt",                 // 토픽명: audit-events-dlt
        include = {DataAccessException.class}    // DB 장애만 재시도
    )
    @KafkaListener(topics = "audit-events", groupId = "audit-consumer")
    public void consume(AuditEvent event) {
        auditLogRepository.save(AuditLog.from(event));
    }

    @DltHandler
    public void handleDlt(AuditEvent event, Exception e) {
        log.error("Audit event moved to DLT: auditId={}", event.getAuditId(), e);
        alertService.notifyCritical("AUDIT_DLT", event.getAuditId());
    }
}
```

`DataAccessException`만 재시도 대상으로 지정하는 이유는 직렬화 오류나 유효성 검사 실패는 재시도해도 의미가 없기 때문이다. 모든 예외를 재시도하면 DLT가 아니라 무한 루프를 만든다.

DLT에 메시지가 쌓이는 것 자체가 알람이어야 한다. DLT 컨슈머 랙(consumer lag)이 0보다 크면 즉시 PagerDuty나 Slack 알림을 보낸다. 감사 로그 유실 가능성을 운영팀이 인지하지 못한 채 넘어가는 상황을 막기 위해서다.

DLT에 쌓인 메시지는 원인을 파악한 뒤 원본 토픽으로 재발행하거나, DB를 복구한 뒤 DLT 컨슈머를 별도로 돌린다.

**SQS DLQ 설정**

```json
{
  "RedrivePolicy": {
    "deadLetterTargetArn": "arn:aws:sqs:...:audit-events-dlq",
    "maxReceiveCount": 3
  }
}
```

`maxReceiveCount`가 3이면 3번 처리 실패 후 DLQ로 이동한다. DLQ의 `MessageRetentionPeriod`는 원본 큐보다 길게(14일) 설정해 분석과 재처리 시간을 확보한다.

## Spring Boot 구현

Spring Boot에서는 AOP를 써서 서비스 메서드 단위로 감사 로그를 선언적으로 붙인다. NestJS의 데코레이터 + 인터셉터 구조와 목적은 같지만, Spring에서는 `@Around` 어드바이스로 구현한다.

**AuditLog 엔티티**

```java
@Entity
@Table(name = "audit_logs")
public class AuditLog {

    @Id
    private String auditId;

    @Column(nullable = false)
    private Instant timestamp;

    @Column(columnDefinition = "jsonb")
    @Convert(converter = JsonbConverter.class)
    private ActorInfo actor;

    @Column(columnDefinition = "jsonb")
    @Convert(converter = JsonbConverter.class)
    private ActionInfo action;

    @Column(columnDefinition = "jsonb")
    @Convert(converter = JsonbConverter.class)
    private ResourceInfo resource;

    @Column(columnDefinition = "jsonb")
    @Convert(converter = JsonbConverter.class)
    private Map<String, Object> before;

    @Column(columnDefinition = "jsonb")
    @Convert(converter = JsonbConverter.class)
    private Map<String, Object> after;

    @Enumerated(EnumType.STRING)
    private AuditResult result;

    private String signature;

    public static AuditLog from(AuditEvent event) {
        AuditLog log = new AuditLog();
        log.auditId = event.getAuditId();
        log.timestamp = event.getTimestamp();
        log.actor = event.getActor();
        log.action = event.getAction();
        log.resource = event.getResource();
        log.before = event.getBefore();
        log.after = event.getAfter();
        log.result = event.getResult();
        log.signature = event.getSignature();
        return log;
    }
}
```

**커스텀 어노테이션과 AuditAspect**

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Auditable {
    String action();
    String category();
}
```

```java
@Aspect
@Component
public class AuditAspect {

    private final AuditEventProducer auditProducer;
    private final HttpServletRequest request;

    @Around("@annotation(auditable)")
    public Object audit(ProceedingJoinPoint pjp, Auditable auditable) throws Throwable {
        AuditResult auditResult;
        Object result;
        try {
            result = pjp.proceed();
            auditResult = AuditResult.SUCCESS;
        } catch (Exception e) {
            auditResult = AuditResult.FAILURE;
            sendAuditEvent(auditable, auditResult);
            throw e;
        }
        sendAuditEvent(auditable, auditResult);
        return result;
    }

    private void sendAuditEvent(Auditable auditable, AuditResult result) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        AuditEvent event = AuditEvent.builder()
            .auditId(UlidCreator.getUlid().toString())
            .timestamp(Instant.now())
            .actor(ActorInfo.from(auth, request))
            .action(ActionInfo.of(auditable.action(), auditable.category()))
            .result(result)
            .build();
        auditProducer.send(event);
    }
}
```

서비스 메서드에 어노테이션을 붙이면 된다.

```java
@Service
public class UserService {

    @Auditable(action = "ROLE_CHANGE", category = "USER_MANAGEMENT")
    public void changeRole(String userId, ChangeRoleRequest request) {
        // 비즈니스 로직
    }
}
```

`before`/`after` 값이 필요한 경우에는 어스펙트만으로 처리하기 어렵다. 변경 전 값 조회와 변경 후 값 확인을 서비스 메서드 안에서 직접 `auditProducer.send()`를 호출해 처리한다.

## NestJS 구현

**AuditLog 엔티티**

```typescript
@Entity('audit_logs')
export class AuditLog {
  @PrimaryColumn()
  audit_id: string;

  @Column({ type: 'timestamptz' })
  timestamp: Date;

  @Column({ type: 'jsonb' })
  actor: {
    user_id: string;
    email: string;
    ip: string;
    session_id?: string;
  };

  @Column({ type: 'jsonb' })
  action: {
    type: string;
    category: string;
  };

  @Column({ type: 'jsonb' })
  resource: {
    type: string;
    id: string;
    name?: string;
  };

  @Column({ type: 'jsonb', nullable: true })
  before: Record<string, unknown> | null;

  @Column({ type: 'jsonb', nullable: true })
  after: Record<string, unknown> | null;

  @Column()
  result: 'SUCCESS' | 'FAILURE';

  @Column({ nullable: true })
  signature: string;
}
```

**AuditService**

```typescript
@Injectable()
export class AuditService {
  constructor(
    @InjectRepository(AuditLog)
    private readonly auditRepo: Repository<AuditLog>,
    private readonly configService: ConfigService,
  ) {}

  async log(entry: CreateAuditLogDto): Promise<void> {
    const auditId = ulid();
    const log = this.auditRepo.create({
      audit_id: auditId,
      timestamp: new Date(),
      ...entry,
      signature: this.sign(auditId, entry),
    });

    await this.auditRepo.save(log);
  }

  private sign(auditId: string, entry: CreateAuditLogDto): string {
    const secret = this.configService.get<string>('AUDIT_SIGNING_SECRET');
    const payload = JSON.stringify({
      audit_id: auditId,
      actor: entry.actor,
      action: entry.action,
      resource: entry.resource,
    });
    return createHmac('sha256', secret).update(payload).digest('hex');
  }
}
```

**Decorator로 감사 로그 자동화**

핸들러마다 `auditService.log()`를 직접 호출하면 누락이 생긴다. Decorator와 Interceptor를 써서 선언적으로 처리한다.

```typescript
export const Audit = (action: string, category: string) =>
  SetMetadata('audit', { action, category });

@Injectable()
export class AuditInterceptor implements NestInterceptor {
  constructor(
    private readonly auditService: AuditService,
    private readonly reflector: Reflector,
  ) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const auditMeta = this.reflector.get<{ action: string; category: string }>(
      'audit',
      context.getHandler(),
    );

    if (!auditMeta) return next.handle();

    const request = context.switchToHttp().getRequest<Request>();

    return next.handle().pipe(
      tap({
        next: () => {
          this.auditService.log({
            actor: {
              user_id: request.user?.id,
              email: request.user?.email,
              ip: request.ip,
              session_id: request.session?.id,
            },
            action: auditMeta,
            resource: {
              type: 'unknown',
              id: request.params?.id ?? '',
            },
            result: 'SUCCESS',
          });
        },
        error: () => {
          this.auditService.log({
            actor: {
              user_id: request.user?.id,
              email: request.user?.email,
              ip: request.ip,
            },
            action: auditMeta,
            resource: {
              type: 'unknown',
              id: request.params?.id ?? '',
            },
            result: 'FAILURE',
          });
        },
      }),
    );
  }
}
```

컨트롤러에서 사용:

```typescript
@Patch(':id/role')
@Audit('ROLE_CHANGE', 'USER_MANAGEMENT')
async changeRole(
  @Param('id') userId: string,
  @Body() dto: ChangeRoleDto,
) {
  return this.userService.changeRole(userId, dto);
}
```

`before`/`after` 값이 필요한 경우에는 서비스 레이어에서 직접 `auditService.log()`를 호출하고, Interceptor는 인증 실패·인가 실패처럼 핸들러에 진입하기 전에 터지는 케이스를 잡는 용도로 쓴다.

저장 실패를 조용히 넘기면 안 된다.

```typescript
this.auditService.log(entry).catch((err) => {
  this.logger.error('Audit log write failed', { err, entry });
  this.alertService.notify('AUDIT_LOG_FAILURE', entry);
});
```

## 감사 요구사항 검증

감사 로그 구현이 완료됐다는 것을 증명하려면 테스트 코드가 필요하다. "동작하는 것 같다"는 주관적 판단이 아니라, 특정 행위가 감사 로그를 발생시키는지 자동화된 검증이 있어야 한다.

컴플라이언스 감사 시 테스트 결과를 증거로 제출하는 경우가 있다. 이 상황에서 "코드 리뷰로 확인했다"는 대답은 받아들여지지 않는다.

**Spring Boot — 통합 테스트**

```java
@SpringBootTest
@AutoConfigureMockMvc
class AuditIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @Test
    @WithMockUser(username = "admin@example.com", roles = "ADMIN")
    void 권한_변경_시_감사_로그가_기록된다() throws Exception {
        ChangeRoleRequest body = new ChangeRoleRequest("ADMIN");

        mockMvc.perform(patch("/users/usr_123/role")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(body)))
            .andExpect(status().isOk());

        List<AuditLog> logs = auditLogRepository.findByResourceId("usr_123");
        assertThat(logs).hasSize(1);
        AuditLog log = logs.get(0);
        assertThat(log.getAction().getType()).isEqualTo("ROLE_CHANGE");
        assertThat(log.getActor().getEmail()).isEqualTo("admin@example.com");
        assertThat(log.getResult()).isEqualTo(AuditResult.SUCCESS);
        assertThat(log.getSignature()).isNotBlank();
    }

    @Test
    @WithMockUser(username = "user@example.com", roles = "USER")
    void 권한_없는_접근_시도도_감사_로그에_기록된다() throws Exception {
        mockMvc.perform(delete("/users/usr_456"))
            .andExpect(status().isForbidden());

        List<AuditLog> logs = auditLogRepository.findByActorEmail("user@example.com");
        assertThat(logs).anyMatch(log -> log.getResult() == AuditResult.FAILURE);
    }

    @Test
    void 감사_로그_테이블에_수정_권한이_없다() {
        assertThatThrownBy(() ->
            jdbcTemplate.execute("UPDATE audit_logs SET result = 'SUCCESS' WHERE 1=1")
        ).isInstanceOf(DataAccessException.class)
         .hasMessageContaining("permission denied");
    }
}
```

**Kafka 파이프라인 테스트**

감사 이벤트가 Kafka로 발행되는지 확인할 때는 `EmbeddedKafka`를 쓰거나, Testcontainers로 실제 브로커를 올린다. Mock 기반으로 `kafkaTemplate.send()`가 호출됐는지만 검증하면 직렬화 오류나 파티션 설정 문제를 잡지 못한다.

```java
@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = {"audit-events"})
class AuditKafkaTest {

    @Autowired
    private UserService userService;

    private Consumer<String, AuditEvent> consumer;

    @BeforeEach
    void setUp() {
        Map<String, Object> consumerProps = KafkaTestUtils.consumerProps(
            "test-group", "true", embeddedKafka
        );
        consumer = new DefaultKafkaConsumerFactory<String, AuditEvent>(consumerProps)
            .createConsumer();
        consumer.subscribe(Collections.singleton("audit-events"));
    }

    @Test
    void 역할_변경_시_audit_events_토픽에_메시지가_발행된다() {
        userService.changeRole("usr_123", new ChangeRoleRequest("ADMIN"));

        ConsumerRecord<String, AuditEvent> record =
            KafkaTestUtils.getSingleRecord(consumer, "audit-events");

        assertThat(record.value().getAction().getType()).isEqualTo("ROLE_CHANGE");
        assertThat(record.value().getActor()).isNotNull();
    }
}
```

테스트에서 최소한 다음을 검증한다.

- 대상 행위마다 로그가 1건 생성되는지 (N+1이면 인터셉터 중복 호출)
- `actor`, `action`, `resource` 필드가 실제 요청 정보와 일치하는지
- 실패한 행위(403, 401, 500)도 로그에 남는지
- `signature` 필드가 비어 있지 않은지
- 감사 로그 테이블에 UPDATE, DELETE 권한이 없는지
