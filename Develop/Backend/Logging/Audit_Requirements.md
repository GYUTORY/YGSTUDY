---
title: 감사 요구사항
tags: [audit-log, compliance, nestjs, pci-dss, gdpr, logging]
updated: 2026-08-03
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

**무결성 요구**: 운영 로그는 장애 상황에서 일부 유실돼도 큰 문제가 없지만, 감사 로그는 유실이 규정 위반이다. 별도 파이프라인에서 높은 내구성 설정(예: Kafka acks=all, min.insync.replicas=2)을 적용해야 한다.

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
    const startTime = Date.now();

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

**비동기 처리 시 주의사항**

`auditService.log()`를 `await` 없이 호출하면 로그 저장 실패가 조용히 묻힌다. 반드시 에러를 잡아서 별도 알림(Slack, PagerDuty)으로 보내야 한다. 감사 로그 저장 실패가 API 응답을 막아서는 안 되지만, 실패 자체를 모르면 안 된다.

```typescript
this.auditService.log(entry).catch((err) => {
  this.logger.error('Audit log write failed', { err, entry });
  this.alertService.notify('AUDIT_LOG_FAILURE', entry);
});
```

감사 로그 저장이 메인 트랜잭션과 결합되면 감사 로그 DB 장애가 서비스 전체 장애로 번진다. Kafka나 SQS 같은 메시지 큐를 중간에 두고, 컨슈머가 내구성 높은 스토리지에 기록하는 구조가 일반적이다.
