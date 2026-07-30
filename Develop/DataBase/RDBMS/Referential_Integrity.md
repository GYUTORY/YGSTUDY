---
title: 참조 무결성
tags: [database, foreign-key, referential-integrity, cascade, on-delete, on-update, innodb, postgresql, msa, typeorm, prisma, orphan-data]
updated: 2026-07-30
---

# 참조 무결성

참조 무결성(Referential Integrity)은 FK 컬럼에 존재하지 않는 PK 값이 들어오지 못하도록 막는 제약이다. "orders.user_id에 users 테이블에 없는 값이 절대 들어가지 않는다"를 DB가 보장하는 것이다.

개념 자체는 단순하지만, ON DELETE/ON UPDATE 옵션 선택을 잘못하면 예상치 못한 시점에 데이터가 지워지거나, 대규모 CASCADE가 연쇄적으로 터지거나, MSA 환경에서 DB FK 없이 운영하다가 고아 데이터가 쌓이는 문제로 이어진다.

---

## ON DELETE / ON UPDATE 옵션

FK 제약을 걸 때 부모 row가 삭제되거나 PK가 변경되면 자식 row를 어떻게 처리할지 지정한다.

### RESTRICT

부모를 삭제하려 할 때 자식이 존재하면 즉시 에러를 낸다. 트랜잭션 내에서도 즉각 검사한다.

```sql
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES users(id)
ON DELETE RESTRICT;

-- users에 id=1이 있고 orders에 user_id=1 row가 있을 때
DELETE FROM users WHERE id = 1;
-- ERROR: Cannot delete or update a parent row: a foreign key constraint fails
```

### NO ACTION

RESTRICT과 혼동하는 경우가 많다. 의미는 비슷하지만 검사 시점이 다르다. NO ACTION은 트랜잭션 종료 시점(COMMIT)에 검사한다. 트랜잭션 내에서 일시적으로 무결성이 깨진 상태가 허용된다.

MySQL InnoDB에서는 RESTRICT와 NO ACTION이 사실상 동일하게 동작한다. 트랜잭션 내 지연 검사를 지원하지 않아서 두 옵션 모두 즉시 검사한다.

PostgreSQL에서는 `DEFERRABLE INITIALLY DEFERRED`를 쓸 때 차이가 생긴다.

```sql
-- PostgreSQL에서 지연 검사 예시
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES users(id)
ON DELETE NO ACTION
DEFERRABLE INITIALLY DEFERRED;

BEGIN;
DELETE FROM users WHERE id = 1;  -- 아직 에러 없음
INSERT INTO users (id, name) VALUES (1, 'new user');  -- 같은 ID 재삽입
COMMIT;  -- 여기서 검사, 결과적으로 자식 참조 유효
```

이 패턴은 PK를 교체하거나 순환 참조가 있는 데이터를 재정렬할 때 쓴다.

### CASCADE

부모가 삭제되면 자식도 같이 삭제, 부모 PK가 바뀌면 자식 FK도 같이 변경된다.

```sql
ALTER TABLE order_items
ADD CONSTRAINT fk_items_order
FOREIGN KEY (order_id) REFERENCES orders(id)
ON DELETE CASCADE;

-- orders.id=100 삭제 시 order_items.order_id=100인 row도 자동 삭제
DELETE FROM orders WHERE id = 100;
```

편하지만 위험하다. `users → orders → order_items → item_reviews` 같은 계층 구조에 전부 CASCADE가 걸려 있으면, 사용자 한 명 삭제가 테이블 전체를 훑는 연쇄 삭제로 번진다. 이 문제는 뒤에서 따로 다룬다.

ON UPDATE CASCADE는 PK를 수정하는 경우에 쓰는데, 보통 PK를 수정할 일이 없으므로 실무에서 잘 쓰지 않는다. UUID나 시퀀스 PK를 쓰면 이 옵션이 필요한 상황 자체가 생기지 않는다.

### SET NULL

부모가 삭제되면 자식 FK 컬럼을 NULL로 바꾼다. FK 컬럼이 NOT NULL이면 에러가 난다.

```sql
ALTER TABLE posts
ADD CONSTRAINT fk_posts_author
FOREIGN KEY (author_id) REFERENCES users(id)
ON DELETE SET NULL;

-- users.id=5 삭제 후
SELECT author_id FROM posts WHERE id = 10;
-- author_id: NULL
```

작성자가 탈퇴해도 게시글은 남겨야 하는 경우에 쓴다. NULL이 된 author_id를 조회할 때 "탈퇴한 사용자"로 표시하는 로직을 애플리케이션에서 처리해야 한다.

### SET DEFAULT

부모가 삭제되면 자식 FK 컬럼을 컬럼의 DEFAULT 값으로 바꾼다.

MySQL InnoDB는 SET DEFAULT를 파싱은 하지만 실제로는 RESTRICT처럼 동작한다. 공식 문서에도 "syntax is parsed but ignored"라고 나와 있다.

PostgreSQL은 제대로 지원한다. DEFAULT 값이 실제 부모 row를 가리켜야 하므로, 보통 "알 수 없음"을 뜻하는 sentinel row(예: id=0, name='unknown')를 부모 테이블에 두고 그걸 DEFAULT로 설정한다.

```sql
-- PostgreSQL
ALTER TABLE posts
ADD CONSTRAINT fk_posts_author
FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET DEFAULT;

ALTER TABLE posts ALTER COLUMN author_id SET DEFAULT 0;
-- users.id=0은 '알 수 없는 사용자' sentinel row
```

실무에서 자주 쓰이지는 않는다. SET NULL이 더 명확하고 sentinel row 관리 부담도 없다.

---

## DB 레벨 FK vs 애플리케이션 레벨 강제

FK 제약을 DB에 걸지, 애플리케이션 코드로만 관리할지는 선택이 아닌 것처럼 보이지만, 실무에서는 두 방식 모두 쓰인다.

### DB 레벨 FK의 장단점

장점은 명확하다. 어떤 경로로 데이터가 들어오든 DB가 막아준다. 직접 psql 세션을 열어서 잘못된 데이터를 집어넣어도, 배치 스크립트가 검증을 빠트려도, DB에서 걸린다.

단점은 성능이다. InnoDB는 FK 컬럼에 반드시 인덱스를 요구한다(없으면 자동 생성). 부모 삭제 시 자식 테이블을 조회하는 비용, 자식 삽입 시 부모 존재 확인 비용이 추가된다. 높은 TPS에서 이 비용이 쌓인다.

더 큰 문제는 대용량 데이터 마이그레이션이다. FK가 걸린 상태에서 수천만 row를 bulk insert하면 매 row마다 참조 검사가 일어난다. 이 경우 FK를 일시 비활성화하고 작업 후 재활성화하는 패턴을 쓴다.

```sql
-- MySQL: FK 검사 비활성화
SET foreign_key_checks = 0;
-- bulk insert...
SET foreign_key_checks = 1;

-- PostgreSQL: 제약 비활성화
ALTER TABLE order_items DISABLE TRIGGER ALL;
-- bulk insert...
ALTER TABLE order_items ENABLE TRIGGER ALL;
```

MySQL의 `foreign_key_checks=0`은 세션 레벨이라 다른 세션에 영향이 없다. PostgreSQL은 superuser 권한이 필요하다.

### 애플리케이션 레벨 강제

FK 없이 애플리케이션 코드에서 참조 무결성을 관리하는 방식이다. MSA나 대용량 쓰기 시스템에서 선택하는 경우가 많다.

성능은 낫다. DB 레벨의 참조 검사가 없으니 쓰기 처리량이 올라간다. 샤딩 환경에서 양쪽 테이블이 다른 샤드에 있으면 DB 레벨 FK 자체가 불가능하다.

대신 다음 문제가 생긴다.

직접 SQL을 실행하는 경로(DBA 직접 수정, 배치, 데이터 픽스 스크립트)에서 무결성 검사가 없다. 애플리케이션 버그 하나로 고아 데이터가 쌓인다. 한 번 쌓이기 시작하면 발견하기까지 시간이 걸리고, 정리 비용도 크다.

---

## 대규모 CASCADE 삭제 폭발

CASCADE를 여러 테이블에 걸어두면 언젠가 예상보다 훨씬 많은 row가 삭제되는 사고가 발생한다.

```
users (1 row 삭제)
  → orders (50 rows 삭제, CASCADE)
    → order_items (500 rows 삭제, CASCADE)
      → item_reviews (2000 rows 삭제, CASCADE)
        → review_images (5000 rows 삭제, CASCADE)
```

`DELETE FROM users WHERE id = ?` 한 줄이 8000개 이상의 row를 삭제한다.

### 실제로 터지는 패턴

테스트 환경에서는 데이터가 적어 CASCADE 시간이 짧다. 프로덕션에서 데이터가 쌓인 후 삭제 한 번에 락이 수 초간 걸리거나, InnoDB의 경우 대형 삭제가 언두 로그를 폭발시켜 DB 전체 성능이 저하된다.

### 트러블슈팅 방법

먼저 삭제 전에 영향받을 row 수를 파악한다.

```sql
-- 삭제 전 영향 범위 확인
SELECT
    (SELECT COUNT(*) FROM orders WHERE user_id = 1) AS orders_count,
    (SELECT COUNT(*) FROM order_items oi
     JOIN orders o ON oi.order_id = o.id WHERE o.user_id = 1) AS items_count,
    (SELECT COUNT(*) FROM item_reviews ir
     JOIN order_items oi ON ir.item_id = oi.id
     JOIN orders o ON oi.order_id = o.id WHERE o.user_id = 1) AS reviews_count;
```

row 수가 예상보다 많으면 CASCADE 대신 수동으로 하위 테이블부터 순서대로 삭제한다.

```sql
BEGIN;

-- 하위부터 순서대로 삭제
DELETE FROM review_images
WHERE review_id IN (
    SELECT ir.id FROM item_reviews ir
    JOIN order_items oi ON ir.item_id = oi.id
    JOIN orders o ON oi.order_id = o.id
    WHERE o.user_id = 1
);

DELETE FROM item_reviews
WHERE item_id IN (
    SELECT oi.id FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    WHERE o.user_id = 1
);

DELETE FROM order_items
WHERE order_id IN (SELECT id FROM orders WHERE user_id = 1);

DELETE FROM orders WHERE user_id = 1;

DELETE FROM users WHERE id = 1;

COMMIT;
```

row 수가 수만 건을 넘으면 트랜잭션 하나로 묶지 않고 배치로 나눠 삭제한다. InnoDB는 하나의 트랜잭션에서 대량 삭제 시 언두 로그가 커지고 락 경합이 심해진다.

```sql
-- 배치 삭제 예시 (애플리케이션 레벨 루프)
DELETE FROM order_items
WHERE order_id IN (SELECT id FROM orders WHERE user_id = 1)
LIMIT 1000;
-- 위를 반복
```

---

## MySQL InnoDB vs PostgreSQL FK 동작 차이

### FK 인덱스 요구사항

InnoDB는 FK 컬럼에 인덱스가 없으면 자동으로 생성한다. 인덱스 없이는 FK를 걸 수 없다.

PostgreSQL은 자동 생성하지 않는다. FK를 걸면 부모 테이블의 PK/UNIQUE 제약을 참조하는데, 자식 테이블의 FK 컬럼에 별도 인덱스를 만들지 않으면 자식 조회 시 Seq Scan이 발생한다. 수동으로 인덱스를 추가해야 한다.

```sql
-- PostgreSQL: FK 컬럼에 인덱스 수동 추가
CREATE INDEX idx_orders_user_id ON orders(user_id);
```

### SET DEFAULT

앞서 언급했듯 MySQL InnoDB는 SET DEFAULT를 무시하고 RESTRICT처럼 동작한다. PostgreSQL만 올바르게 지원한다.

### 지연 검사 (DEFERRABLE)

MySQL은 지원하지 않는다. PostgreSQL만 `DEFERRABLE INITIALLY IMMEDIATE`와 `DEFERRABLE INITIALLY DEFERRED`를 지원한다.

```sql
-- PostgreSQL only
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES users(id)
DEFERRABLE INITIALLY DEFERRED;
```

### FK와 락

InnoDB에서 자식 row를 삽입할 때 부모 row에 공유 락(S lock)을 잡는다. 높은 동시성 환경에서 부모 삽입과 자식 삽입이 겹치면 데드락이 발생할 수 있다. 특히 같은 부모 ID를 가진 자식 row를 여러 트랜잭션이 동시에 삽입할 때 발생하는 패턴이 있다.

PostgreSQL에서는 자식 삽입 시 부모 row에 대해 `FOR KEY SHARE` 락을 잡는다. InnoDB보다 락 범위가 좁아 동시성 충돌이 덜하다.

---

## MSA 환경에서 고아 데이터 문제

MSA에서 서비스별 DB를 분리하면 DB 레벨 FK는 쓸 수 없다. `order-service` DB의 orders 테이블이 `user-service` DB의 users 테이블을 FK로 참조할 방법이 없다.

### 고아 데이터 발생 패턴

1. 사용자 삭제 이벤트가 Kafka로 발행된다.
2. `order-service`가 이벤트를 받아 관련 주문을 정리해야 한다.
3. 이벤트 처리가 실패하거나, 컨슈머가 다운되거나, 이벤트 순서가 뒤틀리면 삭제된 사용자의 주문이 그대로 남는다.

결국 `orders.user_id`가 이미 삭제된 사용자 ID를 가리키는 row가 생긴다.

### 보완 방법

**소프트 삭제(Soft Delete)** 패턴을 쓰면 즉각적인 물리 삭제를 피할 수 있다. `users.deleted_at` 컬럼을 두고 논리적으로만 삭제 처리한다. 이벤트 기반 정리가 완료된 후 물리 삭제한다.

```typescript
// 소프트 삭제
await userRepository.update(userId, { deletedAt: new Date() });
// 이벤트 발행
await eventBus.publish('user.deleted', { userId });

// 이후 order-service에서 처리 완료 확인 후 물리 삭제
// 또는 30일 후 배치로 물리 삭제
```

**주기적 정합성 검사 배치**를 돌리는 방법도 쓴다. 각 서비스가 보유한 외부 ID들을 교차 확인해서 고아 데이터를 찾아낸다.

```typescript
// order-service에서 주기적 실행
const orphanedOrders = await orderRepository
  .createQueryBuilder('o')
  .where('o.user_id NOT IN (:...activeUserIds)', { activeUserIds })
  .getMany();

// 발견된 고아 데이터 처리 (알림 발송, 수동 검토 큐 적재 등)
```

**이벤트 소싱(Event Sourcing)**이나 **아웃박스 패턴(Outbox Pattern)**은 이벤트 유실 자체를 막아준다. 삭제 이벤트가 DB 트랜잭션과 함께 저장되고, 실패 시 재시도가 보장된다.

고아 데이터가 이미 쌓여 있다면 정리 전에 범위를 먼저 파악한다.

```sql
-- user-service DB와 order-service DB를 데이터 분석 도구로 크로스 조인
-- 또는 user-service에서 활성 사용자 ID 목록을 내보내 order-service에서 비교
SELECT o.id, o.user_id, o.created_at
FROM orders o
LEFT JOIN users u ON o.user_id = u.id  -- 같은 DB라면
WHERE u.id IS NULL;
```

---

## ORM의 cascade와 DB 레벨 CASCADE 차이

TypeORM과 Prisma의 cascade 옵션은 DB 레벨 CASCADE와 전혀 다른 레이어에서 동작한다.

### TypeORM cascade 옵션

TypeORM의 `cascade: true`(또는 `cascade: ['insert', 'update', 'remove']`)는 ORM이 부모 엔티티를 저장하거나 삭제할 때 자식 엔티티도 함께 처리하는 **ORM 레벨 동작**이다. DB에 CASCADE 제약이 생기는 게 아니다.

```typescript
@OneToMany(() => Order, (order) => order.user, { cascade: true })
orders: Order[];

// 이 코드는 DB에 ON DELETE CASCADE를 걸지 않는다
// TypeORM이 user를 삭제할 때 orders를 먼저 DELETE 쿼리로 삭제한다
const user = await userRepository.findOne({ where: { id: 1 }, relations: ['orders'] });
await userRepository.remove(user);  // TypeORM이 orders도 DELETE
```

TypeORM cascade의 문제는 `relations`로 로드하지 않은 자식은 삭제되지 않는다는 점이다. 자식이 많으면 전부 로드 후 삭제하므로 메모리를 많이 쓴다.

DB 레벨 CASCADE는 DB가 직접 처리하므로 ORM을 통하지 않아도, 심지어 raw SQL로 삭제해도 동작한다.

```typescript
// DB 레벨 CASCADE가 걸려 있으면
await userRepository.delete(1);  // raw DELETE 쿼리 발행
// DB가 orders도 자동 삭제 — TypeORM은 이 삭제를 모른다

// TypeORM cascade만 있으면
await userRepository.delete(1);  // orders는 삭제 안 됨
// TypeORM의 cascade는 repository.remove()에서만 동작
```

DB 레벨 CASCADE를 걸면서 TypeORM cascade도 같이 켜두면 같은 자식 row에 대해 삭제가 두 번 시도될 수 있다. DB CASCADE가 먼저 지우면 TypeORM이 이미 없는 row를 또 지우려다 에러를 낸다.

### Prisma cascade 옵션

Prisma의 `onDelete`, `onUpdate` 옵션은 DB 레벨 FK 제약으로 생성된다. TypeORM과 달리 실제 DB 스키마에 반영된다.

```prisma
model Order {
  id     Int  @id
  userId Int
  user   User @relation(fields: [userId], references: [id], onDelete: Cascade)
}
```

`prisma migrate`를 실행하면 DB에 `ON DELETE CASCADE` FK 제약이 생긴다. 따라서 Prisma를 통하지 않고 raw SQL로 삭제해도 CASCADE가 작동한다.

단, Prisma의 기본값이 DB 엔진에 따라 다르다. PostgreSQL과 MySQL에서 지원하는 옵션이 다르고, SQLite는 FK를 기본적으로 비활성화(`PRAGMA foreign_keys = ON` 필요)한다.

```typescript
// Prisma에서 raw 쿼리 실행 시에도 DB 레벨 CASCADE 동작
await prisma.$executeRaw`DELETE FROM users WHERE id = 1`;
// orders도 자동 삭제 (DB CASCADE)
```

핵심 차이를 정리하면, TypeORM cascade는 ORM 레이어에서 추가 쿼리를 발행하는 것이고, Prisma onDelete/onUpdate와 DB 레벨 FK는 DB 엔진이 직접 처리하는 것이다. 후자가 더 안전하지만 앞서 설명한 대규모 CASCADE 위험도 함께 온다.
