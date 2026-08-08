---
title: 고아 레코드
tags: [database, microservices, devops, backend]
updated: 2026-07-30
---

# 고아 레코드

고아 레코드(Orphan Record)는 FK 컬럼이 가리키는 부모 레코드가 더 이상 존재하지 않는 자식 레코드를 말한다. `orders.user_id = 42`인데 `users` 테이블에 id=42가 없는 상태다.

DB 레벨 FK가 걸려 있으면 이런 상태가 원천 차단된다. 문제는 FK가 없는 환경, MSA처럼 DB가 물리적으로 분리된 환경, 마이그레이션 중 제약을 비활성화한 경우다. 이 세 경우가 실무에서 고아 레코드가 쌓이는 주된 경로다.

`Referential_Integrity.md`는 FK 제약 자체를 어떻게 설정하는지를 다루고, `No_FK_Design.md`는 FK를 제거하는 판단과 그 대가를 다룬다. 이 문서는 이미 쌓인 고아 레코드를 어떻게 찾고 처리하는지에 집중한다.

---

## 발생 경로

### FK 미적용

FK 제약 없이 `user_id` 컬럼만 두는 설계에서는 DB가 참조 검사를 하지 않는다. 애플리케이션 코드가 삽입 전에 부모 존재를 확인하더라도, 직접 SQL을 실행하는 경로(DBA 작업, 마이그레이션 스크립트, 데이터 픽스)에서는 그 검증이 없다.

```sql
-- FK가 없는 상태에서 users.id=99가 없어도 이 INSERT는 성공한다
INSERT INTO orders (user_id, amount) VALUES (99, 5000);
```

애플리케이션 레이어에서 아무리 꼼꼼하게 검증해도, DB 직접 접근 경로가 하나라도 열려 있으면 결국 고아 레코드는 생긴다.

### MSA DB 분리

`user-service`와 `order-service`가 각각 별도 DB를 쓰는 구성에서는 cross-DB FK가 불가능하다. 의존 관계는 이벤트로만 관리하므로, 이벤트 처리 실패가 곧 고아 레코드 발생으로 이어진다.

가장 흔한 패턴은 다음과 같다.

1. 사용자가 탈퇴 처리됐다. `user-service`에서 `user.withdrawn` 이벤트를 발행한다.
2. Kafka 컨슈머가 다운되거나, 메시지를 처리하다 예외가 났다.
3. `order-service`의 orders 테이블에는 탈퇴한 user_id를 가진 row가 그대로 남는다.

이벤트 처리가 결국 성공한다면 일시적인 불일치지만, 실패가 누적되거나 재시도 없이 버려지면 영구적인 고아 레코드가 된다.

### 마이그레이션 중 제약 비활성화

대용량 데이터 이전 시 FK 검사를 꺼놓는 경우가 있다. 검사 비용 때문에 `foreign_key_checks=0` 상태로 수십만 건을 적재하고 끝낸다. 이때 참조하는 부모 데이터가 누락된 채로 자식 데이터만 들어오면 이후에 FK를 다시 활성화하더라도 이미 쌓인 고아 레코드는 그대로다.

```sql
-- MySQL: FK 검사 비활성화 후 bulk insert
SET foreign_key_checks = 0;
LOAD DATA INFILE '/data/orders.csv' INTO TABLE orders;
SET foreign_key_checks = 1;
-- FK 재활성화 후에도 이미 들어간 잘못된 데이터는 남는다
```

PostgreSQL에서 기존 FK에 `NOT VALID` 옵션으로 이미 있는 데이터를 검사하지 않고 제약만 추가하는 경우도 동일한 상태가 된다.

```sql
-- PostgreSQL: 새 데이터만 검사, 기존 데이터는 검사 안 함
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id)
NOT VALID;

-- 나중에 기존 데이터도 검사하려면
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_user;
-- 이 시점에 고아 레코드가 있으면 에러 발생
```

### 소프트 딜리트 충돌

부모 테이블은 소프트 딜리트(`deleted_at`)를 쓰는데, 자식 테이블은 아무 처리 없이 남아 있는 경우다. 이 상태를 고아로 볼지는 도메인 정책에 따라 다르지만, 실무에서 자주 논란이 된다.

논리 삭제된 사용자의 주문을 "유효한 참조"로 볼 것인지, "고아"로 볼 것인지를 결정하지 않고 방치하면 조회 쿼리마다 처리 방식이 달라진다. 어떤 API는 탈퇴한 사용자의 주문도 보여주고, 어떤 API는 빈 목록을 돌려준다.

---

## 탐지 쿼리

### LEFT JOIN IS NULL 패턴

같은 DB 안에 두 테이블이 있을 때 가장 기본적인 패턴이다.

```sql
-- orders 중 존재하지 않는 user_id를 가진 row
SELECT o.id, o.user_id, o.created_at
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL
  AND o.deleted_at IS NULL;
```

`u.id IS NULL`은 LEFT JOIN에서 매칭되는 부모가 없는 경우다. `o.deleted_at IS NULL`은 이미 논리 삭제된 자식은 탐지에서 제외하는 조건이다. 도메인에 따라 이 조건을 조정한다.

규모가 수백만 건 이상이면 `NOT EXISTS`가 더 빠른 경우가 있다. 플랜을 보고 판단한다.

```sql
-- NOT EXISTS 패턴: 대용량에서 LEFT JOIN보다 빠를 수 있다
SELECT o.id, o.user_id, o.created_at
FROM orders o
WHERE NOT EXISTS (
  SELECT 1 FROM users u WHERE u.id = o.user_id
)
AND o.deleted_at IS NULL
LIMIT 1000;
```

`LIMIT`을 붙이는 건 전체 스캔 비용을 먼저 확인하기 위해서다. 처음 실행할 때 전체 카운트를 바로 돌리면 수천만 건 테이블에서 수 분이 걸릴 수 있다.

### 소프트 딜리트 부모 탐지

부모가 물리 삭제된 케이스와 논리 삭제된 케이스를 분리해서 봐야 한다.

```sql
-- 1. 물리 삭제된 사용자를 참조하는 주문 (users 테이블에 아예 없음)
SELECT o.id, o.user_id, o.created_at, 'physically_deleted' AS orphan_type
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL AND o.deleted_at IS NULL;

-- 2. 논리 삭제된 사용자를 참조하는 주문 (users 테이블에 있지만 deleted_at 있음)
SELECT o.id, o.user_id, o.created_at, 'soft_deleted' AS orphan_type
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.deleted_at IS NOT NULL AND o.deleted_at IS NULL;
```

두 케이스의 처리 방식이 달라야 하는 경우가 많다. 물리 삭제된 사용자 참조는 즉시 정리 대상이고, 논리 삭제된 사용자 참조는 유예 기간 내라면 아직 유효한 데이터일 수 있다.

### 배치 스캔

수천만 건 테이블에서 한 번에 전체를 스캔하면 운영 중인 DB에 부하가 생긴다. id 범위로 쪼개서 순차 스캔하는 방식이 현실적이다.

```sql
-- id 범위 기반 배치 스캔
SELECT o.id, o.user_id
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE o.id BETWEEN 1 AND 100000
  AND u.id IS NULL
  AND o.deleted_at IS NULL;

-- 다음 배치
-- BETWEEN 100001 AND 200000 ...
```

애플리케이션에서 루프를 돌리는 형태로 만들면 처리 속도와 DB 부하를 조절할 수 있다.

```typescript
async function scanOrphanedOrders(batchSize: number = 100000): Promise<number[]> {
  const maxId: number = await dataSource
    .createQueryBuilder()
    .select('MAX(id)', 'max')
    .from('orders', 'o')
    .getRawOne()
    .then((r) => r.max);

  const orphanIds: number[] = [];

  for (let start = 1; start <= maxId; start += batchSize) {
    const end = start + batchSize - 1;

    const rows = await dataSource.query(
      `SELECT o.id FROM orders o
       LEFT JOIN users u ON o.user_id = u.id
       WHERE o.id BETWEEN ? AND ?
         AND u.id IS NULL
         AND o.deleted_at IS NULL`,
      [start, end],
    );

    orphanIds.push(...rows.map((r: { id: number }) => r.id));

    // 배치 간 슬립: 운영 DB 부하 조절
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  return orphanIds;
}
```

MSA 환경에서 DB가 분리돼 있다면 JOIN이 불가능하다. 이 경우 각 서비스가 보유한 ID 목록을 파일로 내보내서 분석 환경에서 비교하거나, user-service에 활성 사용자 ID 목록을 조회하는 API를 만들어 order-service에서 호출하는 방식을 쓴다.

```typescript
// MSA 환경: user-service에서 활성 ID 목록 조회 후 비교
async function findOrphanedOrdersInMsa(): Promise<Order[]> {
  // 페이지네이션으로 가져와야 할 수 있음
  const activeUserIds = await userServiceClient.getActiveUserIds();
  const activeUserIdSet = new Set(activeUserIds);

  const allOrders = await orderRepository
    .createQueryBuilder('o')
    .where('o.deletedAt IS NULL')
    .getMany();

  return allOrders.filter((o) => !activeUserIdSet.has(o.userId));
}
```

활성 사용자가 수백만 명이라면 이 방식도 부담이 크다. 그 경우에는 user-service가 탈퇴한 사용자 ID만 별도로 관리하고, order-service에서 그 목록과 비교한다.

---

## 정리 방법

### 배치 삭제

고아 레코드를 확인하고 정리 대상임을 확정했으면, 한 번에 전부 삭제하지 않는다. 대량 삭제는 InnoDB 언두 로그를 폭발시키고 락 경합을 만든다.

```sql
-- 배치 단위 삭제: 한 번에 1000건씩
DELETE FROM orders
WHERE id IN (
  SELECT o.id FROM (
    SELECT o.id FROM orders o
    LEFT JOIN users u ON o.user_id = u.id
    WHERE u.id IS NULL AND o.deleted_at IS NULL
    LIMIT 1000
  ) AS sub
);
```

MySQL에서 서브쿼리로 삭제할 때 같은 테이블을 직접 참조하면 에러가 난다. `FROM (...) AS sub` 형태로 한 번 감싸야 한다.

애플리케이션 레벨에서 제어하면 배치 간격을 조절하고 진행 상황을 로깅할 수 있다.

```typescript
@Cron('0 3 * * *') // 새벽 3시 배치
async cleanOrphanedOrders(): Promise<void> {
  let deleted = 0;

  while (true) {
    const result = await dataSource.query(`
      DELETE FROM orders
      WHERE id IN (
        SELECT id FROM (
          SELECT o.id FROM orders o
          LEFT JOIN users u ON o.user_id = u.id
          WHERE u.id IS NULL AND o.deleted_at IS NULL
          LIMIT 500
        ) AS sub
      )
    `);

    deleted += result.affectedRows;

    if (result.affectedRows === 0) break;

    this.logger.log(`Deleted ${deleted} orphaned orders so far`);
    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  this.logger.log(`Orphan cleanup done. Total deleted: ${deleted}`);
}
```

삭제 전 반드시 카운트를 먼저 확인한다. 예상보다 훨씬 많은 건수가 나오면 정리 로직이 잘못됐거나 탐지 쿼리 조건이 틀린 것이다.

```sql
-- 삭제 전 카운트 확인
SELECT COUNT(*) FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL AND o.deleted_at IS NULL;
```

### 아카이빙

삭제가 아니라 별도 테이블로 옮겨두는 방식이다. 법적 보관 의무가 있거나, 분석 목적으로 데이터가 필요하거나, 삭제 결정을 되돌릴 가능성이 있을 때 쓴다.

```sql
-- 고아 레코드를 아카이브 테이블로 이동
INSERT INTO orders_archive (id, user_id, amount, created_at, archived_at, archive_reason)
SELECT o.id, o.user_id, o.amount, o.created_at, NOW(), 'orphaned_user'
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL AND o.deleted_at IS NULL;

-- 아카이브 후 원본 삭제
DELETE FROM orders
WHERE id IN (SELECT id FROM orders_archive WHERE archive_reason = 'orphaned_user');
```

아카이브 테이블 구조는 원본과 동일하되 `archived_at`, `archive_reason` 컬럼을 추가하는 게 일반적이다. 나중에 왜 아카이빙됐는지 추적할 수 있어야 한다.

아카이빙 후에도 조회가 빈번하다면 아카이브 테이블에도 인덱스를 걸어야 한다. 조회가 거의 없다면 파티셔닝이나 별도 스토리지(S3 + Parquet 등)를 고려한다.

### 이벤트 기반 보상 처리

MSA 환경에서 이벤트 처리 실패로 쌓인 고아 레코드는, 놓친 이벤트를 다시 재생(replay)하는 방식으로 정리할 수 있다.

이미 처리됐어야 할 이벤트를 다시 발행하거나, 보상 이벤트를 따로 만들어 처리한다. 예를 들어 `user.withdrawn` 이벤트가 누락됐다면, 탈퇴한 사용자 목록을 확인하고 이벤트를 강제로 재발행한다.

```typescript
// 보상 이벤트 발행: 탈퇴 처리됐는데 order-service가 처리 못한 케이스
async compensateWithdrawnUsers(): Promise<void> {
  // user-service에서 탈퇴한 사용자 목록 조회
  const withdrawnUsers = await userRepository.find({
    where: { deletedAt: Not(IsNull()) },
    select: ['id', 'deletedAt'],
  });

  for (const user of withdrawnUsers) {
    // order-service가 처리했는지 확인
    const hasOrphans = await orderServiceClient.checkOrphanedOrders(user.id);

    if (hasOrphans) {
      // 보상 이벤트 재발행
      await eventBus.publish('user.withdrawn.compensate', {
        userId: user.id,
        withdrawnAt: user.deletedAt,
      });
    }
  }
}

// order-service: 보상 이벤트 처리
@EventPattern('user.withdrawn.compensate')
async handleCompensation(data: { userId: number; withdrawnAt: Date }): Promise<void> {
  await orderRepository.update(
    { userId: data.userId, status: Not(OrderStatus.COMPLETED) },
    { status: OrderStatus.CANCELLED, cancelledAt: data.withdrawnAt },
  );

  this.logger.log(`Compensated orphaned orders for userId: ${data.userId}`);
}
```

보상 처리는 멱등성이 보장돼야 한다. 같은 이벤트가 두 번 처리되더라도 결과가 같아야 한다. `CANCELLED` 상태를 다시 `CANCELLED`로 바꾸는 건 문제없지만, 취소 내역을 중복 생성하거나 환불을 두 번 실행하는 경우가 생기지 않도록 처리 전 상태 확인을 넣는다.

---

## 예방 패턴

고아 레코드를 찾아서 정리하는 것보다, 처음부터 생기지 않게 막는 게 비용이 낮다.

### 애플리케이션 레벨 무결성 검사

FK가 없는 환경에서 자식 레코드를 삽입하기 전에 부모 존재를 확인하는 것은 기본이다. 단, SELECT 후 INSERT 사이에 부모가 삭제되는 TOCTOU 경쟁 조건이 있다.

고부하가 아닌 일반 서비스라면 이 경쟁 조건이 실제로 발생할 가능성은 낮지만, 존재한다는 사실을 알고 있어야 한다. 부모 소프트 딜리트를 쓰면 이 문제 자체가 사라진다.

```typescript
async createOrder(userId: number, dto: CreateOrderDto): Promise<Order> {
  const user = await userRepository.findOne({
    where: { id: userId, deletedAt: IsNull() },
  });

  if (!user) {
    throw new NotFoundException(`User ${userId} not found`);
  }

  return orderRepository.save({
    userId,
    amount: dto.amount,
    status: OrderStatus.PENDING,
  });
}
```

배치 INSERT에서는 개별 확인 대신 한 번에 묶어서 확인한다.

```typescript
async bulkCreateOrders(dtos: CreateOrderDto[]): Promise<void> {
  const userIds = [...new Set(dtos.map((d) => d.userId))];

  const existingUsers = await userRepository.find({
    where: { id: In(userIds), deletedAt: IsNull() },
    select: ['id'],
  });

  const validUserIds = new Set(existingUsers.map((u) => u.id));
  const invalid = dtos.filter((d) => !validUserIds.has(d.userId));

  if (invalid.length > 0) {
    throw new BadRequestException(
      `Invalid userIds: ${invalid.map((d) => d.userId).join(', ')}`,
    );
  }

  await orderRepository.insert(dtos.map((d) => ({ ...d, status: OrderStatus.PENDING })));
}
```

### 트랜잭션 아웃박스

MSA 환경에서 이벤트 유실로 인한 고아 레코드를 막는 가장 확실한 방법이다. DB 트랜잭션과 이벤트 발행을 원자적으로 묶어, 이벤트 유실 자체를 없앤다.

핵심은 이벤트를 메시지 브로커로 바로 보내지 않고 같은 DB 트랜잭션 안에서 `outbox` 테이블에 먼저 저장하는 것이다. 별도 프로세스가 outbox를 폴링해서 브로커로 발행한다.

```sql
-- outbox 테이블 구조
CREATE TABLE outbox_events (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type VARCHAR(100) NOT NULL,
  payload    JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed  BOOLEAN NOT NULL DEFAULT FALSE,
  processed_at DATETIME,
  retry_count INT NOT NULL DEFAULT 0
);
```

```typescript
// user-service: 탈퇴 처리와 이벤트 저장을 하나의 트랜잭션으로
async withdrawUser(userId: number): Promise<void> {
  await dataSource.transaction(async (manager) => {
    await manager.update(User, userId, { deletedAt: new Date() });

    await manager.save(OutboxEvent, {
      eventType: 'user.withdrawn',
      payload: { userId },
      createdAt: new Date(),
      processed: false,
    });
  });
  // 트랜잭션이 커밋되면 두 작업 모두 성공하거나 둘 다 실패한다
}
```

```typescript
// outbox 폴러: 별도 프로세스 또는 스케줄러
@Cron('*/5 * * * * *') // 5초마다
async publishOutboxEvents(): Promise<void> {
  const events = await outboxRepository.find({
    where: { processed: false, retryCount: LessThan(5) },
    order: { createdAt: 'ASC' },
    take: 100,
  });

  for (const event of events) {
    try {
      await kafkaProducer.send({
        topic: event.eventType,
        messages: [{ value: JSON.stringify(event.payload) }],
      });

      await outboxRepository.update(event.id, {
        processed: true,
        processedAt: new Date(),
      });
    } catch (err) {
      await outboxRepository.increment({ id: event.id }, 'retryCount', 1);
      this.logger.error(`Failed to publish outbox event ${event.id}`, err);
    }
  }
}
```

아웃박스 패턴을 쓰면 이벤트가 최소 한 번 전달된다. 소비하는 쪽은 중복 처리에 대비한 멱등성 처리가 필요하다.

CDC(Change Data Capture) 방식으로 outbox 테이블 변경을 Debezium 같은 도구로 감지해서 브로커에 발행하는 방법도 있다. 폴링 방식보다 지연이 짧고 DB 부하도 낮다.

---

## 탐지와 정리 주기

고아 레코드가 생기는 환경이라면 주기적인 탐지 배치를 상시로 돌리는 것이 낫다. 쌓인 후 정리하는 비용이 예방 비용보다 항상 크다.

탐지 배치는 정리 배치와 분리하는 것이 좋다. 탐지는 빈번하게, 정리는 결과를 확인한 후 신중하게 실행한다. 예상치 못한 건수가 나왔을 때 삭제가 자동으로 실행되면 복구가 어렵다.

탐지 결과를 슬랙 알림이나 모니터링 메트릭으로 쌓아두면, 고아 레코드가 갑자기 증가하는 시점을 잡을 수 있다. 갑자기 증가한다면 이벤트 처리 실패나 버그가 생긴 것이다.
