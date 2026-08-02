---
title: 미래 예약 저장
tags: [scheduling, reservation, database, redis, sqs, rabbitmq, dst, idempotency, Optimistic-Locking, backend]
updated: 2026-07-31
---

# 미래 예약 저장

미래의 특정 시각에 어떤 작업을 실행하겠다는 데이터를 DB에 저장하고, 그 시각이 되면 꺼내서 실행하는 패턴이다. 알림 발송, 결제 예약, 배치 트리거, 구독 갱신 같은 기능이 전부 이 패턴을 쓴다. 단순해 보이지만 실제로 운영해보면 DST 구간 처리, 중복 실행, 취소·수정 경쟁 조건 같은 문제가 줄줄이 딸려온다.

## DB 스키마 설계

### scheduled_at 컬럼 타입

`TIMESTAMP WITH TIME ZONE`과 `TIMESTAMP WITHOUT TIME ZONE` 중 어떤 걸 쓰느냐가 출발점이다. PostgreSQL 기준으로 `TIMESTAMPTZ`는 내부적으로 UTC Epoch로 저장하고 조회 시 세션 타임존으로 변환한다. `TIMESTAMP`는 타임존 정보 없이 입력 그대로 저장한다.

미래 예약 실행 시각은 반드시 `TIMESTAMPTZ`를 쓴다. 실행 트리거 쿼리가 `WHERE scheduled_at <= NOW()`인데, `TIMESTAMP`를 쓰면 서버 로컬 타임 기준으로 비교가 돼서 서버 타임존 설정에 따라 동작이 달라진다. 서로 다른 타임존에 DB 서버와 앱 서버가 분리된 환경에서 특히 위험하다.

MySQL의 경우 `DATETIME`은 타임존 없이 저장되고, `TIMESTAMP`는 UTC로 저장한다. MySQL에서 `DATETIME`을 쓰면 `NOW()`와의 비교가 세션 타임존에 따라 달라진다. MySQL 환경에서는 `TIMESTAMP` 컬럼을 쓰거나, `DATETIME`을 쓴다면 UTC 값만 저장한다는 규칙을 팀 전체가 지켜야 한다.

```sql
-- PostgreSQL
CREATE TABLE scheduled_jobs (
    id          BIGSERIAL PRIMARY KEY,
    job_type    VARCHAR(100) NOT NULL,
    payload     JSONB,
    scheduled_at TIMESTAMPTZ NOT NULL,
    timezone_id  VARCHAR(50),
    status      VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    version     INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scheduled_jobs_poll
    ON scheduled_jobs (scheduled_at, status)
    WHERE status = 'PENDING';
```

### timezone_id 분리 저장 vs Instant 단독 저장

`scheduled_at`에 UTC Instant만 저장할지, 아니면 `timezone_id` 컬럼을 함께 둘지는 비즈니스 요구사항에 따라 갈린다.

UTC Instant만 저장하는 경우: 예약 생성 시점에 "사용자 타임존 오전 9시"를 UTC로 변환해서 저장한다. 이후 DST 규칙이 바뀌거나 사용자가 타임존을 바꿔도 저장된 UTC 실행 시각은 그대로다. 단순하고 폴링 쿼리도 깔끔하다.

`timezone_id`를 분리 저장하는 경우: "뉴욕 현지 오전 9시 실행"이라는 의도를 유지하고 싶을 때 쓴다. 예약 생성 시점이 DST 전이고 실행 시점이 DST 후라면, timezone_id를 보고 실행 직전에 UTC 시각을 재계산한다. 비즈니스 의미(현지 시각 고정)를 DB에 보존하지만, 폴링 쿼리와 실행 로직이 복잡해진다.

대부분의 경우 UTC Instant 단독 저장으로 충분하다. "사용자 현지 오전 9시"를 정확히 지켜야 하는 요구사항이 명시적으로 있을 때만 `timezone_id`를 추가한다. DST 처리 섹션에서 이 차이가 구체적으로 어떤 문제를 만드는지 설명한다.

### 상태 머신

예약 잡의 상태를 명확히 정의하지 않으면 폴링 쿼리와 중복 실행 방지 로직이 엉킨다.

```
PENDING → RUNNING → COMPLETED
                  ↘ FAILED
         ↘ CANCELLED
```

`PENDING`: 실행 대기 중. 폴링 대상.
`RUNNING`: 실행 중. 분산 락과 함께 이 상태를 거쳐야 중복 실행을 막을 수 있다.
`COMPLETED`: 정상 완료.
`FAILED`: 실행 실패. 재시도 정책에 따라 `PENDING`으로 되돌리거나 dead-letter로 분류.
`CANCELLED`: 취소됨. 폴링 대상에서 제외.

`RUNNING` 상태에 타임아웃을 걸어야 한다. 실행 중 프로세스가 죽으면 영원히 `RUNNING`에 머문다. `locked_until TIMESTAMPTZ` 컬럼을 추가하고, 폴링 쿼리에서 `locked_until < NOW()`인 `RUNNING` 건도 같이 집어간다.

```sql
ALTER TABLE scheduled_jobs
    ADD COLUMN locked_until TIMESTAMPTZ,
    ADD COLUMN locked_by    VARCHAR(100),
    ADD COLUMN retry_count  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN max_retries  INTEGER NOT NULL DEFAULT 3;
```

## 폴링 방식 실행

### 기본 폴링 쿼리

폴링은 일정 주기마다 `scheduled_at <= NOW()` 조건으로 대기 중인 잡을 꺼내서 실행하는 방식이다. 구현이 단순하고 DB 외 의존성이 없다. 단점은 폴링 주기만큼 실행 지연이 생기고, 인스턴스가 여러 개면 같은 잡을 여러 인스턴스가 동시에 집어갈 수 있다.

```sql
-- PostgreSQL: FOR UPDATE SKIP LOCKED로 분산 환경 안전하게 처리
SELECT id, job_type, payload, scheduled_at
FROM scheduled_jobs
WHERE status = 'PENDING'
  AND scheduled_at <= NOW()
ORDER BY scheduled_at
LIMIT 10
FOR UPDATE SKIP LOCKED;
```

`FOR UPDATE SKIP LOCKED`는 다른 트랜잭션이 잠근 행을 건너뛴다. 여러 워커가 동시에 폴링해도 같은 잡을 두 번 집어가지 않는다. 잡을 집어간 직후 상태를 `RUNNING`으로 바꾸는 UPDATE를 같은 트랜잭션 안에서 실행한다.

```java
@Transactional
public List<ScheduledJob> fetchAndLock(int batchSize, Duration lockTimeout) {
    List<ScheduledJob> jobs = jobRepository.fetchPendingForUpdate(batchSize);
    
    Instant lockedUntil = Instant.now().plus(lockTimeout);
    String lockerId = instanceId + "-" + Thread.currentThread().getId();
    
    for (ScheduledJob job : jobs) {
        job.setStatus(JobStatus.RUNNING);
        job.setLockedUntil(lockedUntil);
        job.setLockedBy(lockerId);
    }
    
    jobRepository.saveAll(jobs);
    return jobs;
}
```

### 타임아웃된 RUNNING 잡 복구

`locked_until`이 지난 `RUNNING` 상태 잡을 `PENDING`으로 되돌려야 한다. 별도의 복구 스레드나 배치로 주기적으로 실행한다.

```sql
UPDATE scheduled_jobs
SET status      = 'PENDING',
    locked_until = NULL,
    locked_by    = NULL,
    retry_count  = retry_count + 1
WHERE status = 'RUNNING'
  AND locked_until < NOW()
  AND retry_count < max_retries;

-- 최대 재시도 초과 시 FAILED 처리
UPDATE scheduled_jobs
SET status = 'FAILED'
WHERE status = 'RUNNING'
  AND locked_until < NOW()
  AND retry_count >= max_retries;
```

### 분산 락 없이 FOR UPDATE SKIP LOCKED로 충분한가

단일 DB 클러스터에서 `FOR UPDATE SKIP LOCKED`를 쓰면 중복 실행은 막힌다. 하지만 DB 장애 시 폴링 자체가 멈추고, DB 커넥션 수를 많이 잡아먹는다. 폴링 인스턴스가 수십 개로 늘어나면 폴링 쿼리 자체가 DB 부하를 만든다.

Redis 분산 락은 다른 용도다. 같은 잡 ID에 대한 중복 실행을 DB 외 레이어에서 한 번 더 막고 싶을 때, 또는 폴링과 실행이 비동기로 분리된 구조일 때 쓴다.

```java
public void executeJob(ScheduledJob job) {
    String lockKey = "job-lock:" + job.getId();
    String lockValue = UUID.randomUUID().toString();
    
    Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, lockValue, Duration.ofMinutes(10));
    
    if (!acquired) {
        // 다른 인스턴스가 이미 실행 중
        return;
    }
    
    try {
        doExecute(job);
        markCompleted(job);
    } catch (Exception e) {
        markFailed(job);
    } finally {
        // 본인이 건 락만 해제 (Lua 스크립트로 원자적 처리)
        String script = "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                        "return redis.call('del', KEYS[1]) else return 0 end";
        redisTemplate.execute(
            new DefaultRedisScript<>(script, Long.class),
            Collections.singletonList(lockKey),
            lockValue
        );
    }
}
```

락 해제를 단순히 `DEL`로 하면 안 된다. 락 TTL이 만료돼서 다른 인스턴스가 락을 가져간 상태에서 원래 인스턴스가 `DEL`을 날리면 다른 인스턴스의 락이 해제된다. Lua 스크립트로 값을 확인하고 삭제하는 원자적 연산이 필요하다.

## 지연 큐 방식

DB 폴링 대신 지연 큐에 잡을 넣고 큐가 알아서 지정 시각에 꺼내주는 방식이다.

### Redis ZSET

Redis Sorted Set을 큐로 쓰는 방식이다. score를 실행 시각(Unix timestamp)으로 쓴다. 워커가 `ZRANGEBYSCORE` 또는 `ZPOPMIN`으로 현재 시각 이전 score인 멤버를 꺼낸다.

```python
import time
import redis

r = redis.Redis()

def enqueue(job_id: str, payload: dict, run_at: float):
    """run_at은 Unix timestamp (UTC seconds)"""
    r.zadd('delayed_jobs', {f"{job_id}:{json.dumps(payload)}": run_at})

def poll_due_jobs(batch_size: int = 10):
    now = time.time()
    # ZPOPMIN은 Redis 5.0+. 원자적으로 꺼내서 중복 방지
    results = r.zpopmin('delayed_jobs', count=batch_size)
    
    due = []
    requeue = []
    for member, score in results:
        if score <= now:
            due.append(member)
        else:
            requeue.append((member, score))
    
    # 아직 시간 안 된 건 다시 넣기
    if requeue:
        r.zadd('delayed_jobs', {m: s for m, s in requeue})
    
    return due
```

`ZRANGEBYSCORE` + `ZREM` 조합 대신 `ZPOPMIN`을 쓰면 읽기와 삭제가 원자적으로 처리돼 중복 실행을 막기 쉽다. 단, `ZPOPMIN`은 score 기준이라 현재 시각보다 미래인 건도 같이 꺼낼 수 있어서 위 예시처럼 걸러서 다시 넣는 처리가 필요하다. 루아 스크립트로 묶으면 더 깔끔하다.

```lua
-- due_jobs.lua: 현재 시각 이전 score인 멤버만 원자적으로 꺼내기
local now = ARGV[1]
local count = ARGV[2]
local members = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', now, 'LIMIT', 0, count)
if #members > 0 then
    redis.call('ZREM', KEYS[1], unpack(members))
end
return members
```

Redis ZSET 방식의 한계는 Redis가 단일 장애점이 된다는 것과, 잡 페이로드가 커지면 메모리 사용량이 많아진다는 점이다. 잡 ID만 ZSET에 넣고 페이로드는 DB나 별도 Redis Hash에 저장하는 게 낫다.

### SQS Delay Queue

AWS SQS의 `DelaySeconds` 파라미터로 최대 15분 지연 발송이 된다. 15분을 넘는 지연이 필요하면 즉시 발송하는 대신, 실행 직전에 다시 큐에 넣는 방식을 쓴다.

```python
import boto3
from datetime import datetime, timezone

sqs = boto3.client('sqs')

def enqueue_with_delay(queue_url: str, payload: dict, run_at: datetime):
    now = datetime.now(timezone.utc)
    delay_seconds = int((run_at - now).total_seconds())
    
    if delay_seconds <= 0:
        # 이미 시각이 지남, 즉시 발송
        delay_seconds = 0
    elif delay_seconds > 900:
        # 15분 초과: 중간 단계로 다시 큐에 넣는 메시지를 보냄
        # 또는 step function이나 EventBridge Scheduler 사용 고려
        delay_seconds = 900
    
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(payload),
        DelaySeconds=delay_seconds,
        MessageAttributes={
            'run_at': {
                'StringValue': run_at.isoformat(),
                'DataType': 'String'
            }
        }
    )
```

SQS는 최소 1회 전달을 보장한다. 중복 전달이 생길 수 있어서 컨슈머 쪽에서 멱등성 처리가 필요하다. SQS FIFO 큐를 쓰면 중복 제거 기능이 있지만 처리량 제한(3000 TPS)이 생긴다.

15분 이상의 지연이 필요하면 EventBridge Scheduler나 Step Functions Wait 상태를 고려한다. EventBridge Scheduler는 특정 시각(one-time) 또는 반복 실행 모두 지원하고, UTC나 특정 타임존 기준으로 설정할 수 있다.

### RabbitMQ Delayed Exchange

`rabbitmq-delayed-message-exchange` 플러그인을 사용한다. 메시지 헤더의 `x-delay`에 밀리초 단위 지연을 설정하면 해당 시간 후에 큐로 라우팅한다.

```python
import pika
import json

def publish_delayed(connection, exchange: str, routing_key: str,
                    payload: dict, delay_ms: int):
    channel = connection.channel()
    
    channel.exchange_declare(
        exchange=exchange,
        exchange_type='x-delayed-message',
        arguments={'x-delayed-type': 'direct'}
    )
    
    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            headers={'x-delay': delay_ms},
            delivery_mode=2,  # 영속 메시지
            message_id=str(uuid.uuid4()),
        )
    )
```

`x-delay`는 정수형이고 밀리초 단위다. 최대값이 플러그인 내부적으로 32-bit signed integer(약 24.8일)로 제한된다. 그보다 긴 지연이 필요하면 중간 단계를 거쳐야 한다.

Delayed Message Exchange 플러그인은 지연 메시지를 Mnesia(RabbitMQ 내장 DB)에 저장한다. RabbitMQ 재시작 시 영속 메시지는 복구되지만, 노드가 늘어날수록 분산 지연 메시지 처리가 복잡해진다.

### 방식 비교

DB 폴링은 인프라 의존성이 없고 운영이 단순하다. 잡 수가 수십만 건 이하이고 초 단위 지연이 허용된다면 무리 없이 쓸 수 있다. 단점은 초당 수천 건 이상이면 폴링 쿼리 자체가 부하가 된다.

Redis ZSET은 단순하고 빠르다. 잡 메타데이터 관리와 분리가 필요하고, Redis 장애 시 데이터 유실 가능성을 감수할 수 있으면 쓴다.

SQS는 AWS 환경에서 인프라를 직접 관리하기 싫을 때 선택한다. 15분 이상 지연이 필요하면 EventBridge Scheduler와 조합한다.

RabbitMQ Delayed Exchange는 이미 RabbitMQ를 쓰는 환경에서 메시징 레이어를 통일하고 싶을 때 쓴다. 플러그인 의존성이 생기고 대규모 지연 메시지 관리가 복잡해진다.

## DST 전환 구간에 걸리는 예약

DST 전환 구간에 예약이 걸리면 두 가지 상황이 생긴다.

### timezone_id 없이 UTC Instant만 저장하는 경우

UTC Instant 저장 방식에서는 DST가 별 문제가 안 된다. 예약 생성 시 "뉴욕 현지 오전 2시"를 UTC로 변환해서 저장하면 끝이다. 봄 전환일 뉴욕 2:00 AM은 존재하지 않지만, 예약 생성 로직에서 이걸 잡아내야 한다.

```java
public Instant resolveScheduledAt(LocalDateTime localDt, ZoneId zoneId) {
    ZoneRules rules = zoneId.getRules();
    
    List<ZoneOffset> validOffsets = rules.getValidOffsets(localDt);
    
    if (validOffsets.isEmpty()) {
        // 봄 전환: 이 시각이 존재하지 않음
        // 전환 후 첫 유효 시각으로 조정하거나 예외 처리
        ZonedDateTime adjusted = localDt.atZone(zoneId); // 자동으로 조정됨
        log.warn("존재하지 않는 시각 요청: {}, 조정 결과: {}", localDt, adjusted);
        return adjusted.toInstant();
    }
    
    if (validOffsets.size() > 1) {
        // 가을 전환: 이 시각이 두 번 존재함
        // 첫 번째(DST 적용, 앞쪽)를 쓰거나 사용자에게 명확히 선택하게 함
        ZonedDateTime first = localDt.atOffset(validOffsets.get(0)).toZonedDateTime();
        return first.toInstant();
    }
    
    return localDt.atZone(zoneId).toInstant();
}
```

### timezone_id를 분리 저장하는 경우

실행 직전에 "현지 오전 9시"를 UTC로 재계산하는 방식이라면, DST 전환이 예약 생성 후 실행 전에 일어날 때 실행 UTC 시각이 달라진다. 이걸 의도한 건지 확인이 필요하다.

사용자가 2025년 3월 1일에 "3월 10일 오전 2시 America/New_York 기준으로 실행"을 예약했다고 하자. 3월 10일이 봄 전환일이다. 2:00 AM이 존재하지 않는다. 폴링 시점에 `timezone_id`와 `local_time`으로 UTC를 재계산하면 `ZoneRules`가 자동으로 3:00 AM으로 조정하거나 예외를 던진다.

이 케이스를 사전에 탐지해서 사용자에게 알리거나, 폴링 쿼리에서 자동 처리할 건지 정책을 명확히 해야 한다.

```sql
-- timezone_id와 local_time을 저장하는 경우 스키마 예시
ALTER TABLE scheduled_jobs
    ADD COLUMN local_time      TIME,
    ADD COLUMN local_date      DATE,
    ADD COLUMN timezone_id     VARCHAR(50);

-- 폴링 쿼리: AT TIME ZONE으로 UTC 변환 후 비교 (PostgreSQL)
SELECT id, job_type, payload
FROM scheduled_jobs
WHERE status = 'PENDING'
  AND (local_date + local_time) AT TIME ZONE timezone_id <= NOW()
ORDER BY (local_date + local_time) AT TIME ZONE timezone_id
LIMIT 10
FOR UPDATE SKIP LOCKED;
```

이 방식은 `AT TIME ZONE` 변환이 DST를 고려해서 UTC를 계산한다. 단, 존재하지 않는 시각이나 중복 시각에서 DB 엔진마다 동작이 다를 수 있어서 사전에 확인이 필요하다.

## 멱등성 보장과 중복 실행 방지

### 왜 중복 실행이 생기는가

폴링 방식에서 워커가 잡을 집어가고 `RUNNING`으로 바꾸는 트랜잭션 사이에 워커가 죽으면, 잡이 `PENDING` 상태로 남거나 `RUNNING`에서 복구된다. 복구된 잡이 다시 실행되면서 같은 작업이 두 번 실행된다.

SQS는 at-least-once delivery를 보장하므로 같은 메시지가 두 번 전달될 수 있다. RabbitMQ도 컨슈머 ACK 전에 채널이 끊기면 메시지를 다시 큐에 넣는다.

### 멱등 키 패턴

잡 실행의 최종 결과(외부 API 호출, DB INSERT 등)를 멱등하게 만드는 것이 근본 해결책이다. 잡 ID를 멱등 키로 쓰고, 실행 전 멱등 키 테이블에 기록한다.

```java
@Transactional
public boolean tryMarkAsExecuting(String jobId) {
    try {
        // idempotency_keys 테이블에 INSERT
        // UNIQUE constraint가 걸려 있어서 중복 시 예외
        idempotencyKeyRepository.insert(new IdempotencyKey(
            jobId,
            Instant.now(),
            Instant.now().plus(Duration.ofDays(7))  // 유효 기간
        ));
        return true;
    } catch (DataIntegrityViolationException e) {
        // 이미 실행됨
        return false;
    }
}
```

```sql
CREATE TABLE idempotency_keys (
    key         VARCHAR(255) PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_idempotency_keys_expires ON idempotency_keys (expires_at);
```

외부 API 호출이 멱등 키를 지원하면 같은 키로 두 번 호출해도 한 번만 처리된다. Stripe, Braintree 같은 결제 API가 `Idempotency-Key` 헤더를 지원한다.

```java
public String chargePayment(String jobId, ChargeRequest request) {
    return stripeClient.charges().create(
        ChargeCreateParams.builder()
            .setAmount(request.getAmount())
            .setCurrency(request.getCurrency())
            .setSource(request.getSourceToken())
            .build(),
        RequestOptions.builder()
            .setIdempotencyKey("charge-" + jobId)
            .build()
    );
}
```

외부 API가 멱등 키를 지원하지 않으면, 실행 전 결과 테이블에 잡 ID로 이미 처리됐는지 확인하는 체크가 필요하다.

### 실행 결과 저장

잡 실행 결과를 별도 테이블에 저장하면 멱등성 확인과 감사 추적이 된다.

```sql
CREATE TABLE job_executions (
    id              BIGSERIAL PRIMARY KEY,
    job_id          BIGINT NOT NULL REFERENCES scheduled_jobs(id),
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL,  -- SUCCESS, FAILED
    result_payload  JSONB,
    error_message   TEXT,
    UNIQUE (job_id)  -- 잡 하나당 실행 결과 하나 (재시도 추적이 필요하면 UNIQUE 제거)
);
```

`UNIQUE (job_id)` 제약을 걸면 같은 잡이 두 번 실행되더라도 결과 INSERT가 하나만 성공한다. 재시도 이력을 남기려면 UNIQUE를 제거하고 `attempt_number` 컬럼을 추가한다.

## 예약 취소·수정 시 낙관적 잠금

### 경쟁 조건

사용자가 예약을 취소하려는 순간, 폴링 워커가 같은 잡을 집어가서 실행을 시작할 수 있다. 취소 요청이 DB에 반영되기 전에 워커가 이미 실행을 시작했다면, 취소됐어야 할 작업이 실행된다.

낙관적 잠금으로 이 경쟁 조건을 처리한다. `version` 컬럼을 이용해서 취소 시점의 상태와 실제 DB 상태가 일치하는지 확인한 후 업데이트한다.

```java
@Transactional
public boolean cancelJob(long jobId, int expectedVersion) {
    int updated = jobRepository.cancelIfPending(jobId, expectedVersion);
    
    if (updated == 0) {
        // 두 가지 경우:
        // 1. 이미 다른 요청이 상태를 바꿨거나
        // 2. version이 다름 (동시 수정)
        ScheduledJob job = jobRepository.findById(jobId)
            .orElseThrow(JobNotFoundException::new);
        
        if (job.getStatus() == JobStatus.RUNNING) {
            throw new JobAlreadyRunningException("이미 실행 중인 잡은 취소할 수 없습니다");
        }
        if (job.getStatus() == JobStatus.COMPLETED) {
            throw new JobAlreadyCompletedException("이미 완료된 잡입니다");
        }
        throw new OptimisticLockException("동시 수정 충돌, 재시도 필요");
    }
    
    return true;
}
```

```sql
-- jobRepository.cancelIfPending
UPDATE scheduled_jobs
SET status  = 'CANCELLED',
    version = version + 1
WHERE id      = :jobId
  AND version = :expectedVersion
  AND status  = 'PENDING';
```

`AND status = 'PENDING'` 조건을 같이 걸면 `RUNNING` 상태인 경우 UPDATE가 0 rows를 반환하므로 실행 중 취소를 막을 수 있다.

### 예약 시각 수정

수정은 취소 후 재생성이 제일 단순하다. 하지만 잡 ID가 바뀌면 외부 참조(클라이언트가 저장한 예약 ID 등)가 끊어진다. 같은 ID를 유지하면서 `scheduled_at`만 업데이트하는 방식을 쓰려면 낙관적 잠금을 동일하게 적용한다.

```java
@Transactional
public boolean reschedule(long jobId, int expectedVersion, Instant newScheduledAt) {
    if (newScheduledAt.isBefore(Instant.now())) {
        throw new IllegalArgumentException("과거 시각으로는 재예약 불가");
    }
    
    int updated = jobRepository.rescheduleIfPending(jobId, expectedVersion, newScheduledAt);
    
    if (updated == 0) {
        throw new OptimisticLockException("수정 실패: 상태가 변경됐거나 version 불일치");
    }
    
    return true;
}
```

```sql
UPDATE scheduled_jobs
SET scheduled_at = :newScheduledAt,
    version      = version + 1,
    updated_at   = NOW()
WHERE id      = :jobId
  AND version = :expectedVersion
  AND status  = 'PENDING';
```

Redis ZSET 방식에서 수정이 필요하면 기존 멤버를 `ZREM`하고 새 score로 `ZADD`한다. 이 두 연산 사이에 워커가 기존 멤버를 집어가는 경우를 막으려면 Lua 스크립트로 원자적으로 처리하거나, 멤버에 version을 포함시키고 실행 시점에 유효성을 DB에서 재확인한다.

```lua
-- reschedule.lua: 원자적으로 기존 멤버 교체
local old_member = ARGV[1]
local new_member = ARGV[2]
local new_score  = ARGV[3]

local removed = redis.call('ZREM', KEYS[1], old_member)
if removed == 1 then
    redis.call('ZADD', KEYS[1], new_score, new_member)
    return 1
else
    return 0  -- 이미 처리됨
end
```

### 클라이언트에게 version 노출

REST API에서 예약 조회 응답에 `version`을 포함시키고, 취소·수정 요청에 `version`을 필수로 받는다.

```json
// GET /reservations/123 응답
{
  "id": 123,
  "scheduled_at": "2025-03-10T14:00:00Z",
  "status": "PENDING",
  "version": 3
}

// DELETE /reservations/123 요청
{
  "version": 3
}
```

클라이언트가 version 없이 요청하면 409 Conflict 대신 422 Unprocessable Entity를 반환하면서 version 필드를 요구한다. 동시 수정 충돌 시 409 Conflict를 반환하고 클라이언트가 재시도하도록 유도한다.

ETag 헤더로 version을 전달하는 방식도 있다. `ETag: "3"`, `If-Match: "3"`으로 HTTP 표준 방식을 따를 수 있다.
