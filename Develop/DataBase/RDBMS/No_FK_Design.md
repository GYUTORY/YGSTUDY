---
title: 외래키 없는 설계
tags: [database, foreign-key, no-fk, typeorm, prisma, msa, ddd, aggregate, toctou, orphan-data, soft-delete, referential-integrity]
updated: 2026-07-30
---

# 외래키 없는 설계

FK(외래키) 제약을 걸지 않는 것은 무결성을 포기하는 게 아니다. DB 레벨 제약이 감당하기 어려운 상황에서 무결성 책임을 애플리케이션 레이어로 옮기는 선택이다. 선택 자체보다 언제 이 선택을 하는지, 그 대가로 무엇을 직접 챙겨야 하는지를 명확히 알고 있어야 한다.

---

## FK를 제거하는 판단 기준

### TPS 임계점

InnoDB는 자식 row를 삽입할 때마다 부모 테이블에 S lock을 잡는다. 단일 부모 ID에 여러 트랜잭션이 동시에 자식을 삽입하면 락 경합이 심해진다. 낮은 TPS 환경에서는 이 비용이 무시 가능하지만, 초당 수천 건 이상의 INSERT가 집중되는 테이블이라면 FK가 병목이 된다.

정확한 임계점은 하드웨어와 쿼리 구성에 따라 다르다. 실무에서 경험한 패턴은 단일 부모를 참조하는 자식 INSERT가 초당 2,000~3,000건을 넘어가기 시작할 때 FK 검사 비용이 눈에 띄게 나타났다. `SHOW ENGINE INNODB STATUS`로 락 대기 빈도를 확인하고, `performance_schema`의 `events_waits_summary_by_event_name`에서 `wait/synch/mutex/innodb/lock_mutex`를 추적하면 병목 여부를 판단할 수 있다.

DELETE 경로에서도 마찬가지다. 부모를 삭제할 때 자식 테이블 전체를 스캔해서 참조 여부를 확인하므로, 자식 테이블이 수천만 건 이상이면 삭제 한 번이 테이블 락을 상당 시간 잡는다.

### 샤딩 환경

DB 레벨 FK는 같은 DB 인스턴스 안에서만 동작한다. orders 테이블과 users 테이블이 서로 다른 샤드에 있으면 FK 자체를 걸 수 없다. 샤딩을 도입하는 순간 DB 레벨 참조 무결성은 선택지에서 사라진다.

샤딩 키 설계에 따라 같은 샤드 안에 묶이는 경우도 있다. 예를 들어 user_id 기준으로 샤딩하고 orders도 user_id 기준으로 동일 샤드에 배치하면 같은 DB 안에서 FK가 가능하다. 하지만 대부분의 샤딩 환경에서는 서로 다른 논리 엔티티를 동일 샤드에 묶기 어렵고, 샤드 리밸런싱 시 FK 관계가 깨지는 위험도 있다.

### MSA DB 분리

서비스별로 DB를 완전히 분리하면 물리적으로 FK가 불가능하다. `order-service`의 orders 테이블이 `user-service`의 users 테이블을 직접 참조할 방법이 없다. MSA에서 DB를 공유하면 서비스 간 결합도가 높아져 배포와 스케일링 독립성이 사라지므로, DB 분리는 MSA의 전제 조건에 가깝다.

### DDD Aggregate 경계

DDD에서 Aggregate는 하나의 트랜잭션 경계다. Order Aggregate 안에 OrderItem이 포함된다면 같은 트랜잭션 안에서 일관성이 보장되고, DB 레벨 FK를 걸어두는 게 자연스럽다.

반면 Order와 Product는 서로 다른 Aggregate다. Order가 Product의 ID를 참조하지만, Product 가격이 변해도 주문 당시 가격은 변하면 안 된다. DB 레벨 FK를 걸면 Product가 삭제될 때 관련 Orders를 어떻게 처리할지 CASCADE 정책을 결정해야 하고, 그 결정이 도메인 경계를 무너뜨린다. 서로 다른 Aggregate 간 참조는 DB FK 대신 ID 값으로만 연결하고 무결성은 도메인 레이어가 책임지는 것이 Aggregate 경계 규칙에 맞다.

---

## ORM 설정 패턴

### TypeORM: createForeignKeyConstraints

TypeORM에서 FK 제약 없이 관계를 정의하는 방법은 `createForeignKeyConstraints: false` 옵션을 사용하는 것이다.

```typescript
// order.entity.ts
@Entity()
export class Order {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  userId: number;

  // DB에 FK 제약 생성 안 함. 타입 힌트와 join 편의만 제공
  @ManyToOne(() => User, (user) => user.orders, {
    createForeignKeyConstraints: false,
  })
  @JoinColumn({ name: 'user_id' })
  user: User;
}
```

이 설정으로 마이그레이션을 실행하면 `user_id` 컬럼은 생성되지만 FK 제약 조건은 DB에 추가되지 않는다. ORM 레벨 관계 탐색(`order.user`)과 TypeORM QueryBuilder의 join 구문은 정상적으로 쓸 수 있다.

기존 엔티티에서 FK를 제거할 때는 마이그레이션에서 직접 DROP CONSTRAINT를 실행해야 한다. TypeORM이 `createForeignKeyConstraints: false`로 바뀐 것을 감지해 자동으로 DROP하지는 않는다.

```typescript
// 마이그레이션 파일에서 FK 제거
export class RemoveOrderUserFk1722300000000 implements MigrationInterface {
  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.dropForeignKey('orders', 'FK_orders_user_id');
  }

  async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.createForeignKey(
      'orders',
      new TableForeignKey({
        columnNames: ['user_id'],
        referencedColumnNames: ['id'],
        referencedTableName: 'users',
        onDelete: 'RESTRICT',
      }),
    );
  }
}
```

FK 이름은 DB마다 자동 생성 규칙이 다르다. 실제 이름은 `information_schema.TABLE_CONSTRAINTS`에서 확인한다.

```sql
SELECT CONSTRAINT_NAME
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_NAME = 'orders'
  AND CONSTRAINT_TYPE = 'FOREIGN KEY';
```

### Prisma: 관계 없는 ID 컬럼 단독 정의

Prisma에서 FK 없이 순수 ID 컬럼만 두는 방법은 `@relation`을 쓰지 않고 컬럼을 단독으로 정의하는 것이다.

```prisma
model Order {
  id        Int      @id @default(autoincrement())
  userId    Int      // FK 제약 없음. 단순 컬럼
  createdAt DateTime @default(now())

  @@index([userId])
}
```

`@relation`을 쓰지 않으면 Prisma가 FK 제약을 생성하지 않는다. `prisma db pull`로 스키마를 역으로 가져올 때도 DB에 FK가 없으면 `@relation`이 생기지 않는다.

반면 `@relation`을 쓰면 Prisma는 기본적으로 FK 제약을 생성하려 한다. DB 레벨 FK 없이 `@relation`을 유지하고 싶다면 Prisma 스키마에서 `relationMode = "prisma"`를 설정해야 한다.

```prisma
// schema.prisma
datasource db {
  provider     = "mysql"
  url          = env("DATABASE_URL")
  relationMode = "prisma"  // DB FK 대신 Prisma 레벨에서 관계 관리
}

model Order {
  id     Int  @id @default(autoincrement())
  userId Int
  user   User @relation(fields: [userId], references: [id])

  @@index([userId])
}

model User {
  id     Int     @id @default(autoincrement())
  orders Order[]
}
```

`relationMode = "prisma"`는 PlanetScale처럼 FK를 지원하지 않는 DB를 쓸 때 도입된 옵션이다. DB에 FK 제약이 생기지 않고 Prisma가 런타임에 참조 무결성을 흉내 낸다. 단, Prisma가 처리하지 않는 경로(raw SQL, 직접 DB 접속)에서는 무결성 보장이 없다.

---

## 애플리케이션 레벨 무결성 보장

FK를 제거하면 무결성 책임이 모두 애플리케이션 코드로 온다. 아래 네 가지 방법을 조합해서 쓴다.

### 삽입 전 존재 확인과 TOCTOU 문제

가장 기본적인 방법은 자식 row를 삽입하기 전에 부모가 존재하는지 SELECT로 확인하는 것이다.

```typescript
async createOrder(userId: number, items: OrderItem[]): Promise<Order> {
  const user = await this.userRepository.findOne({ where: { id: userId } });
  if (!user) {
    throw new NotFoundException(`User ${userId} not found`);
  }

  return this.orderRepository.save({
    userId,
    items,
    createdAt: new Date(),
  });
}
```

이 방식은 TOCTOU(Time-Of-Check-To-Time-Of-Use) 경쟁 조건에 취약하다. SELECT로 확인한 직후, INSERT 실행 직전에 해당 사용자가 삭제되는 경우가 있다. FK가 있다면 DB가 INSERT 시점에 부모 존재를 검증하므로 이 경쟁 조건이 없다.

TOCTOU를 방어하는 방법은 두 가지다.

첫 번째는 SELECT FOR UPDATE로 부모 row에 배타 락을 잡고 INSERT하는 것이다. 삭제보다 삽입이 먼저 락을 잡으면 삭제는 대기하고, 삭제가 먼저 락을 잡으면 삽입이 없는 사용자로 실패한다.

```typescript
async createOrder(userId: number, items: OrderItem[]): Promise<Order> {
  return this.dataSource.transaction(async (manager) => {
    const user = await manager
      .createQueryBuilder(User, 'u')
      .setLock('pessimistic_write')
      .where('u.id = :userId', { userId })
      .getOne();

    if (!user) {
      throw new NotFoundException(`User ${userId} not found`);
    }

    return manager.save(Order, { userId, items, createdAt: new Date() });
  });
}
```

두 번째는 소프트 삭제를 써서 물리 삭제 자체를 피하는 것이다. 부모가 물리적으로 사라지지 않으면 TOCTOU 문제도 발생하지 않는다. 고부하 시스템에서는 락을 잡는 비용보다 소프트 삭제로 물리 삭제를 미루는 게 낫다.

### 소프트 삭제

`deleted_at` 컬럼을 두고 논리 삭제만 수행한다. FK가 없는 환경에서 부모 row를 물리적으로 삭제하면 이미 존재하는 자식 row들이 고아가 되므로, 소프트 삭제로 부모를 남겨두는 게 현실적인 선택이다.

```typescript
// user.entity.ts
@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ nullable: true })
  deletedAt: Date | null;
}

// 소프트 삭제 처리
async softDeleteUser(userId: number): Promise<void> {
  await this.userRepository.update(userId, { deletedAt: new Date() });
  // 이벤트 발행: 다른 서비스가 연관 데이터를 비동기로 정리
  await this.eventBus.publish('user.soft-deleted', { userId });
}
```

소프트 삭제를 쓰면 모든 SELECT 쿼리에 `WHERE deleted_at IS NULL` 조건이 따라다닌다. TypeORM `@DeleteDateColumn` 데코레이터나 Prisma의 `softDelete` 미들웨어를 쓰면 이 조건을 자동으로 붙여준다.

```typescript
// TypeORM: @DeleteDateColumn을 쓰면 find 계열에 자동으로 deleted_at IS NULL 필터 적용
@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @DeleteDateColumn()
  deletedAt: Date | null;
}

// softRemove 호출 시 deleted_at을 현재 시각으로 설정
await this.userRepository.softRemove(user);
```

소프트 삭제된 row가 쌓이면 테이블 크기가 계속 커진다. 일정 기간(예: 30일) 후에 물리 삭제하는 배치를 별도로 돌려야 한다. 물리 삭제 전에 연관 데이터 정리가 완료됐는지 확인하는 로직도 배치에 포함시킨다.

### 이벤트 기반 정리

부모 엔티티 삭제 이벤트를 발행하고 소비하는 측에서 연관 데이터를 비동기로 정리하는 방식이다. MSA 환경에서 주로 쓴다.

```typescript
// user-service: 사용자 탈퇴 처리
async withdrawUser(userId: number): Promise<void> {
  await this.dataSource.transaction(async (manager) => {
    await manager.update(User, userId, { deletedAt: new Date() });

    // Outbox 패턴: 이벤트를 같은 트랜잭션 안에서 DB에 기록
    await manager.save(OutboxEvent, {
      eventType: 'user.withdrawn',
      payload: JSON.stringify({ userId }),
      createdAt: new Date(),
      processed: false,
    });
  });
}

// order-service: user.withdrawn 이벤트 수신
@EventPattern('user.withdrawn')
async handleUserWithdrawn(data: { userId: number }): Promise<void> {
  await this.orderRepository.update(
    { userId: data.userId, status: Not(OrderStatus.COMPLETED) },
    { status: OrderStatus.CANCELLED, cancelledAt: new Date() },
  );
}
```

이벤트 유실을 막으려면 Outbox 패턴이 필요하다. 이벤트를 Kafka나 SQS로만 바로 발행하면 DB 트랜잭션은 성공했는데 메시지 브로커 발행이 실패할 수 있다. Outbox 패턴은 이벤트를 DB 트랜잭션과 함께 저장하고, 별도 프로세스가 Outbox 테이블을 폴링해서 발행하므로 유실 가능성이 낮다.

이벤트 기반 정리는 결과적 일관성이다. 이벤트 소비 지연 동안 고아 데이터가 잠시 존재할 수 있다. 이 상태를 애플리케이션이 정상적으로 처리할 수 있도록 설계해야 한다. 예를 들어 탈퇴한 사용자의 주문을 조회할 때 userId로 user-service를 호출하고 404가 오면 "탈퇴한 사용자"로 표시하는 식이다.

### 주기적 정합성 배치

이벤트 처리 실패, 버그, 직접 DB 수정 등으로 고아 데이터가 쌓이는 경우가 있다. 주기적으로 정합성을 확인하는 배치를 돌려 누락된 케이스를 잡아낸다.

```typescript
// 주기 배치: 고아 데이터 탐지 후 처리
@Cron('0 2 * * *')  // 매일 새벽 2시
async detectOrphanedOrders(): Promise<void> {
  // user-service에서 전체 활성 userId 목록 가져오기
  const activeUserIds = await this.userServiceClient.getActiveUserIds();

  // 활성 유저 목록에 없는 userId를 가진 주문 탐지
  const orphanedOrders = await this.orderRepository
    .createQueryBuilder('o')
    .where('o.userId NOT IN (:...activeUserIds)', { activeUserIds })
    .andWhere('o.deletedAt IS NULL')
    .getMany();

  if (orphanedOrders.length > 0) {
    this.logger.warn(`Orphaned orders detected: ${orphanedOrders.length}`);
    // 알림 발송 또는 수동 검토 큐에 적재
    await this.alertService.notify('orphaned-orders', { count: orphanedOrders.length });
  }
}
```

활성 userId 목록을 외부 서비스에서 매번 가져오는 비용이 크다면, 탈퇴 처리 시 `withdrawn_users` 테이블에 ID를 기록하고 그 목록과 비교하는 방식으로 범위를 좁힌다.

---

## 고아 데이터 탐지 쿼리

같은 DB 안에 두 테이블이 있는 경우 LEFT JOIN으로 고아 row를 탐지한다.

```sql
-- orders 중 존재하지 않는 user_id를 가진 row 탐지
SELECT o.id, o.user_id, o.created_at
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL
  AND o.deleted_at IS NULL;

-- 규모가 클 때: NOT EXISTS가 LEFT JOIN보다 빠른 경우가 있다
SELECT o.id, o.user_id, o.created_at
FROM orders o
WHERE NOT EXISTS (
  SELECT 1 FROM users u WHERE u.id = o.user_id
)
AND o.deleted_at IS NULL
LIMIT 1000;
```

소프트 삭제를 쓰는 경우 부모 테이블의 `deleted_at`도 고려해야 한다. 논리 삭제된 부모를 참조하는 자식 row를 고아로 볼지, 아직 유효한 참조로 볼지는 도메인 정책에 따라 다르다.

```sql
-- 물리 삭제된 사용자 참조 (users 테이블에 없음)
SELECT o.id, o.user_id FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL AND o.deleted_at IS NULL;

-- 논리 삭제된 사용자 참조 (users 테이블에 있지만 deleted_at이 있음)
SELECT o.id, o.user_id FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.deleted_at IS NOT NULL AND o.deleted_at IS NULL;
```

서비스가 분리된 MSA 환경에서는 각 서비스의 DB에 직접 접근하기 어렵다. 이 경우 정기적으로 각 서비스의 ID 목록을 파일이나 공유 스토리지로 내보내고, 데이터 분석 도구(BigQuery, Redshift, 또는 별도 분석 DB)에 모아서 크로스 조인하는 방식을 쓴다.

---

## 인덱스 전략과 성능 트레이드오프

### FK 제거 후 인덱스 관리

InnoDB는 FK 컬럼에 인덱스가 없으면 FK를 허용하지 않고 자동으로 인덱스를 생성한다. FK를 제거하면 이 인덱스도 함께 사라지는 경우가 있다. FK 제거 후 해당 컬럼의 인덱스가 남아 있는지 반드시 확인해야 한다.

```sql
-- MySQL: 테이블 인덱스 확인
SHOW INDEX FROM orders;

-- 없으면 직접 생성
CREATE INDEX idx_orders_user_id ON orders(user_id);
```

FK를 제거한다고 해서 조회 성능이 자동으로 개선되지 않는다. 오히려 FK가 인덱스를 보장하던 것이 사라졌으므로, 명시적으로 인덱스를 관리해야 한다.

### 커버링 인덱스

FK 없는 환경에서 고아 데이터 탐지 쿼리나 관계 조회를 자주 실행한다면 커버링 인덱스를 고려한다.

```sql
-- orders 테이블: user_id + status 복합 인덱스
-- 탈퇴 사용자의 활성 주문을 찾는 쿼리에 인덱스만으로 처리 가능
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- 이 쿼리는 테이블 접근 없이 인덱스만으로 처리됨
SELECT user_id, status FROM orders WHERE user_id = 123;
```

### 쓰기 vs 읽기 트레이드오프

FK 제약이 없으면 쓰기 경로에서 부모 조회 오버헤드가 사라진다. 하지만 읽기 경로에서 JOIN 쿼리는 동일하게 발생하므로 읽기 성능 차이는 없다.

트레이드오프가 명확히 드러나는 상황은 배치 INSERT다. FK가 있으면 수십만 건 INSERT 시 매 row마다 부모 존재를 검증하므로 처리 시간이 길어진다. FK가 없으면 이 검증 없이 바로 적재할 수 있다. 단, 검증이 없다는 것은 잘못된 데이터도 그대로 들어간다는 의미다. 배치 입력 전 애플리케이션 레벨에서 유효성 검사를 하거나, 배치 완료 후 정합성 확인 쿼리를 돌려야 한다.

```typescript
// 배치 INSERT 전 유효성 확인
async bulkInsertOrders(orders: CreateOrderDto[]): Promise<void> {
  const userIds = [...new Set(orders.map((o) => o.userId))];
  const existingUsers = await this.userRepository.findBy({ id: In(userIds) });
  const existingUserIds = new Set(existingUsers.map((u) => u.id));

  const invalidOrders = orders.filter((o) => !existingUserIds.has(o.userId));
  if (invalidOrders.length > 0) {
    throw new BadRequestException(
      `Invalid userId in orders: ${invalidOrders.map((o) => o.userId).join(', ')}`,
    );
  }

  await this.orderRepository.insert(orders);
}
```

FK를 제거하면 얻는 것은 쓰기 처리량과 설계 유연성이다. 잃는 것은 DB가 자동으로 보장하던 무결성이다. 그 무결성을 코드로 메우지 않으면 시간이 지날수록 데이터 품질이 나빠진다.
