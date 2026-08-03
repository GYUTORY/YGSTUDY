---
title: 소프트 삭제
tags: [database, soft-delete, deleted-at, is-deleted, partial-index, gdpr, referential-integrity, unique-constraint, audit-log, mysql, postgresql]
updated: 2026-08-03
---

# 소프트 삭제

행을 실제로 지우지 않고 삭제됐다는 표시만 남기는 패턴이다. 데이터를 물리적으로 제거하는 하드 삭제와 달리 row는 테이블에 남아 있고, 애플리케이션이 삭제 여부를 나타내는 컬럼을 보고 필터링한다.

쓰는 이유는 명확하다. 데이터 복구, 감사 이력 보존, 참조 관계 유지다. 그런데 단순해 보이는 이 패턴이 실무에서 꽤 다양한 방식으로 문제를 일으킨다.

---

## deleted_at vs is_deleted

컬럼 선택지는 두 가지다.

```sql
-- 방법 1: 타임스탬프
deleted_at TIMESTAMP NULL DEFAULT NULL

-- 방법 2: 불리언 플래그
is_deleted BOOLEAN NOT NULL DEFAULT FALSE
```

`is_deleted`는 단순하다. 인덱스 카디널리티도 낮고, 삭제 여부만 알면 되는 단순 필터링에 쓰기 적합하다. 문제는 정보가 너무 적다는 것이다. 언제 삭제됐는지 알 수 없고, 삭제 시점 기준의 감사 로그 연계나 시간 범위 쿼리를 쓸 수 없다.

`deleted_at`은 삭제 시점 정보가 포함된다. 감사 로그와 연계할 때 "이 행은 2024-03-15 14:32:00에 삭제됐다"는 사실을 테이블에서 바로 알 수 있다. 삭제 여부 필터는 `deleted_at IS NULL`로 쓴다. NULL 체크가 약간 더 복잡해 보이지만 실제 성능 차이는 없다.

실무에서 `deleted_at`이 표준에 가까운 이유는 두 가지다. 복구 시 언제 삭제됐는지 알 수 있고, 감사 로그 테이블과 시간 기반으로 조인할 수 있다. `is_deleted = true`인 행이 언제 삭제됐는지 추적하려면 별도 컬럼이나 별도 테이블이 필요하고, 그러면 `deleted_at` 하나로 해결될 걸 두 곳에 관리하게 된다.

GDPR 요청 처리나 데이터 수명 주기 관리에서 "30일 이상 된 삭제 행을 물리 삭제한다" 같은 정책을 구현할 때도 `deleted_at`이 필요하다. `is_deleted`만 있으면 기간 기준 배치를 쓸 수 없다.

단, 팀 내 히스토리가 `is_deleted`로 쌓여 있고 현재 감사 요구사항이 없다면 굳이 마이그레이션할 필요는 없다. `deleted_at`을 추가할 때의 마이그레이션 비용과 기존 쿼리 수정 범위가 이득보다 크다면 그냥 유지하는 게 맞다.

---

## 인덱스 설계

### 필터링이 항상 따라오는 구조

소프트 삭제 패턴에서 모든 SELECT 쿼리는 `deleted_at IS NULL` 조건을 달고 다닌다. 이 조건 없이 데이터를 조회하면 삭제된 행이 섞여서 나온다. 전체 데이터 중 삭제된 비율이 낮을 때는 괜찮지만, 운영 기간이 길어지면서 삭제된 행이 전체의 30~50%를 넘어가면 쿼리 성능에 직접 영향이 생긴다.

### PostgreSQL: 부분 인덱스

PostgreSQL에서는 부분 인덱스(partial index)로 삭제되지 않은 행만 인덱싱할 수 있다.

```sql
-- 삭제되지 않은 행만 인덱스에 포함
CREATE INDEX idx_users_email_active
  ON users (email)
  WHERE deleted_at IS NULL;

CREATE INDEX idx_orders_user_id_active
  ON orders (user_id)
  WHERE deleted_at IS NULL;
```

부분 인덱스의 장점은 인덱스 크기다. 삭제된 행 50%가 인덱스에서 제외되면 인덱스가 절반 크기로 줄어들고, 메모리 사용량과 스캔 비용이 줄어든다. 쿼리에서 `WHERE deleted_at IS NULL`을 명시하면 옵티마이저가 부분 인덱스를 선택한다.

주의할 점이 있다. 부분 인덱스는 `WHERE deleted_at IS NULL` 조건이 쿼리에 정확히 있을 때만 동작한다. `WHERE deleted_at IS NULL AND user_id = 123`은 부분 인덱스를 쓸 수 있지만, `WHERE deleted_at IS NULL OR is_admin = true`처럼 조건이 복잡해지면 옵티마이저가 부분 인덱스를 포기하고 전체 테이블 스캔으로 빠지는 경우가 있다. `EXPLAIN ANALYZE`로 실행 계획을 확인해야 한다.

### MySQL: 복합 인덱스

MySQL InnoDB는 부분 인덱스를 지원하지 않는다. 대신 `deleted_at`을 인덱스에 포함시켜서 커버링 인덱스나 범위 필터로 처리한다.

```sql
-- deleted_at을 앞에 두는 방법: NULL 값이 먼저 클러스터링됨
CREATE INDEX idx_users_active_email
  ON users (deleted_at, email);

-- 또는 email + deleted_at 순서
CREATE INDEX idx_users_email_deleted
  ON users (email, deleted_at);
```

컬럼 순서 선택이 중요하다. `(email, deleted_at)` 순서면 특정 email을 조회하면서 `deleted_at IS NULL`을 필터로 추가하는 쿼리에 적합하다. 반대로 `(deleted_at, email)`은 삭제되지 않은 전체 사용자를 email 순서로 스캔할 때 유리하다.

MySQL에서 `deleted_at IS NULL` 조건은 NULL 범위 스캔으로 처리된다. InnoDB B-Tree에서 NULL은 가장 작은 값으로 정렬되므로 `deleted_at IS NULL`은 인덱스 앞 부분에 집중된 범위 스캔이 된다. 삭제 비율이 낮으면 이 범위가 좁아서 효율적이지만, 삭제된 행이 많으면 NULL이 아닌 범위가 늘어나고 스캔 범위 자체가 줄어든다. 오히려 삭제가 많을수록 인덱스 효율이 좋아지는 구조다.

### 실제 성능 저하 사례

삭제 비율이 높지 않아서 인덱스 설계를 미룬 테이블에서 다음과 같은 쿼리가 문제가 됐다.

```sql
SELECT * FROM posts
WHERE user_id = 123
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 20;
```

`user_id` 단독 인덱스만 있을 때, MySQL은 `user_id = 123`으로 row를 찾은 다음 `deleted_at IS NULL`을 필터로 걸고 정렬한다. user_id = 123인 게시물이 1만 건이고 그 중 삭제된 게 8천 건이면, 인덱스로 1만 건을 가져와서 8천 건을 버리고 2천 건에서 정렬해서 20건을 반환한다. 인덱스를 써도 실제로는 거의 풀스캔에 가까운 비용이 된다.

`(user_id, deleted_at, created_at)` 복합 인덱스를 추가하면, `user_id = 123 AND deleted_at IS NULL`로 범위를 좁힌 후 `created_at DESC`로 정렬된 데이터를 바로 읽을 수 있다.

```sql
CREATE INDEX idx_posts_user_active_date
  ON posts (user_id, deleted_at, created_at DESC);
```

PostgreSQL이면 부분 인덱스로 더 간단하게 해결된다.

```sql
CREATE INDEX idx_posts_user_active
  ON posts (user_id, created_at DESC)
  WHERE deleted_at IS NULL;
```

---

## 외래 키 무결성 문제

소프트 삭제에서 가장 골치 아픈 부분이 외래 키다.

```sql
-- users 테이블: deleted_at 있음
-- orders 테이블: user_id FK로 users 참조

SELECT o.id, u.name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.deleted_at IS NULL;
```

이 쿼리에서 `u.deleted_at IS NULL` 조건이 없으면 소프트 삭제된 사용자의 정보도 같이 나온다. 비즈니스 로직에서 탈퇴한 사용자의 주문이 보이면 안 된다면 JOIN 조건에 `AND u.deleted_at IS NULL`을 추가해야 한다.

더 심각한 경우는 반대 방향이다. users를 소프트 삭제해도 DB 레벨 FK 제약은 그대로 살아 있다. `deleted_at`을 채우는 것은 그냥 UPDATE이므로 FK 검사가 트리거되지 않는다. 따라서 소프트 삭제된 부모를 참조하는 자식 row를 새로 INSERT하는 것이 DB 레벨에서 막히지 않는다. 탈퇴한 사용자 ID로 새 주문이 들어오는 상황이 이론상 가능하다.

이 문제를 처리하는 방법은 세 가지다.

**애플리케이션 레이어에서 검증**: 삽입 전에 부모 row가 소프트 삭제되지 않았는지 확인하는 쿼리를 실행한다. 간단하지만 TOCTOU 경쟁 조건이 생길 수 있다. SELECT로 확인하는 사이에 다른 트랜잭션이 부모를 소프트 삭제할 수 있다.

**DB 트리거**: INSERT/UPDATE 시 부모의 `deleted_at IS NULL`을 확인하는 트리거를 건다. DB 레벨 보장이 생기지만 트리거는 디버깅이 어렵고, ORM이 트리거 존재를 모르기 때문에 예상치 못한 에러를 내거나 성능 문제가 생길 수 있다.

**FK를 제거하고 애플리케이션에서 무결성 관리**: 소프트 삭제 패턴을 적극적으로 쓰는 시스템에서 현실적으로 선택하는 방법이다. DB FK 없이 애플리케이션에서 참조 무결성을 관리한다. [외래키 없는 설계](No_FK_Design.md) 문서의 판단 기준을 같이 보면 된다.

---

## unique constraint 충돌

소프트 삭제 패턴에서 UNIQUE 제약이 자주 문제가 된다.

```sql
-- email 유니크 제약
CREATE UNIQUE INDEX uq_users_email ON users (email);
```

user@example.com으로 가입했다가 탈퇴하고, 같은 email로 재가입하려 하면 유니크 제약이 막는다. `deleted_at`이 있는 row가 이미 email 값을 차지하고 있어서다.

**방법 1: deleted_at 포함 복합 유니크**

```sql
-- MySQL: NULL은 유니크 비교에서 서로 다른 값으로 취급
CREATE UNIQUE INDEX uq_users_email_deleted
  ON users (email, deleted_at);
```

MySQL에서 NULL은 유니크 인덱스에서 NULL != NULL로 취급된다. `deleted_at IS NULL`인 행은 서로 email 기준으로 충돌이 생기고, `deleted_at IS NOT NULL`인 행은 아무리 많아도 같은 email로 여러 개가 들어갈 수 있다. 탈퇴 후 재가입 시나리오에서 email + NULL 조합은 하나만 허용된다.

PostgreSQL도 동일하게 동작한다.

```sql
-- PostgreSQL: 동일한 방식
CREATE UNIQUE INDEX uq_users_email_deleted
  ON users (email, deleted_at);
```

**방법 2: 부분 인덱스 (PostgreSQL)**

```sql
CREATE UNIQUE INDEX uq_users_email_active
  ON users (email)
  WHERE deleted_at IS NULL;
```

삭제되지 않은 row에서만 email 유니크를 강제한다. 삭제된 row는 인덱스에 없으므로 같은 email로 재가입이 가능하다. MySQL에서는 부분 인덱스가 없으므로 방법 1을 쓴다.

**방법 3: 삭제 시 email 값 변조**

```sql
UPDATE users
SET
  email = CONCAT('deleted_', id, '_', email),
  deleted_at = NOW()
WHERE id = 123;
```

소프트 삭제 시 원본 email을 prefix로 변조한다. 유니크 제약이 그대로 유지되고 재가입이 자유롭다. 단점은 원래 email 값을 알려면 파싱이 필요하고, 감사 로그와 email 기반 추적이 복잡해진다.

---

## 복구 시나리오

소프트 삭제의 장점인 복구는 생각보다 복잡하다.

단순 복구는 `deleted_at`을 NULL로 되돌리면 된다.

```sql
UPDATE users SET deleted_at = NULL WHERE id = 123;
```

문제는 복구 이후다. 이 사용자가 삭제됐다가 복구됐다는 사실을 감사 로그에 남겨야 한다. 삭제된 동안 동일 email로 다른 계정이 생겼다면 유니크 충돌이 발생한다. 연관된 자식 테이블(orders, posts 등)도 같이 복구해야 하는지 결정해야 한다.

자식 테이블이 각자 `deleted_at`을 갖고 있고 부모와 동시에 소프트 삭제됐다면, 부모만 복구하면 자식은 여전히 삭제 상태로 남는다. 일괄 복구 스크립트가 필요하다.

```sql
-- 사용자와 함께 소프트 삭제된 주문 복구
-- 삭제 시점이 비슷한 row만 복구 (같은 트랜잭션에서 삭제된 것으로 가정)
UPDATE orders
SET deleted_at = NULL
WHERE user_id = 123
  AND deleted_at BETWEEN '2024-03-15 14:30:00' AND '2024-03-15 14:35:00';
```

복구 범위를 시간으로 추정해야 한다는 것 자체가 취약하다. 삭제 이벤트와 복구 이벤트를 별도 감사 테이블에 기록하는 게 더 견고하다.

### 감사 로그 연계

```sql
CREATE TABLE audit_log (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  table_name  VARCHAR(64)  NOT NULL,
  record_id   BIGINT       NOT NULL,
  action      ENUM('CREATE', 'UPDATE', 'SOFT_DELETE', 'RESTORE', 'HARD_DELETE') NOT NULL,
  changed_by  BIGINT,
  changed_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  before_data JSON,
  after_data  JSON
);
```

소프트 삭제 시 `SOFT_DELETE`, 복구 시 `RESTORE` 액션으로 audit_log에 row를 남긴다. `before_data`와 `after_data`에 변경 전후 상태를 JSON으로 저장하면, 복구 시 무엇이 변경됐는지 추적할 수 있다.

`deleted_at`으로 삭제 시점을 알고, audit_log로 누가 삭제했는지 알면 대부분의 감사 요구사항을 충족한다.

---

## GDPR Right to Erasure

소프트 삭제가 GDPR 삭제 요청(Right to Erasure, Article 17)에 충분한지 물으면, 답은 "단독으로는 충분하지 않다"다.

GDPR에서 요구하는 삭제는 개인정보의 처리 중단과 복구 불가능한 제거다. `deleted_at`을 채운 소프트 삭제는 데이터가 DB에 그대로 남아 있고, 관리자 권한으로 언제든 조회 가능하다. 이는 "지웠다"는 주장을 뒷받침하기 어렵다.

처리 방법은 두 단계로 나눈다.

**단계 1: 즉시 처리 — 개인정보 익명화**

삭제 요청을 받는 즉시 PII(개인식별정보)를 실제로 제거하거나 대체한다.

```sql
UPDATE users
SET
  email      = CONCAT('deleted_', id, '@deleted.invalid'),
  name       = 'Deleted User',
  phone      = NULL,
  birth_date = NULL,
  address    = NULL,
  deleted_at = NOW()
WHERE id = 123;
```

이렇게 하면 row는 남아 있지만 개인을 식별할 수 있는 정보가 없다. 참조 무결성을 유지하면서 GDPR 요구사항을 충족한다.

**단계 2: 지연 처리 — 물리 삭제**

법적 보존 기간(financial records는 보통 7년)이 지난 후 물리 삭제한다. 보존 기간이 끝나면 배치로 하드 삭제한다.

```sql
-- 삭제된 지 7년 이상 된 row 물리 삭제 (익명화된 상태)
DELETE FROM users
WHERE deleted_at < NOW() - INTERVAL 7 YEAR;
```

감사 로그의 경우, 감사 목적의 로그는 개인정보가 포함되지 않는 수준으로 설계해야 한다. "user_id=123이 2024-03-15에 삭제됐다"는 로그에서 user_id=123이 더 이상 누구인지 알 수 없다면, 감사 로그 자체는 보존해도 된다.

백업 데이터도 처리 대상이다. 소프트 삭제만 하고 익명화를 안 했다면, 어제 만든 DB 백업에 개인정보가 여전히 있다. GDPR 삭제 요청 처리 후 백업에서도 해당 데이터가 복구 불가능해야 하므로, 백업 보존 기간 정책과 암호화 키 관리를 같이 고려해야 한다.

---

## 쿼리 성능 튜닝

소프트 삭제 패턴에서 쿼리 성능 저하가 나타나는 주요 경로는 세 가지다.

**ORM의 자동 필터 누락**: TypeORM의 `@DeleteDateColumn`이나 Hibernate의 `@Where` 같은 ORM 수준 소프트 삭제 필터는 편리하지만, 네이티브 쿼리를 실행하거나 QueryBuilder를 잘못 쓰면 필터가 적용 안 된 쿼리가 나간다. `SHOW PROCESSLIST`나 slow query log에서 `deleted_at IS NULL` 조건 없이 나가는 쿼리를 잡아내야 한다.

```typescript
// TypeORM: softDelete 설정 시
@Entity()
export class User {
  @DeleteDateColumn()
  deletedAt: Date | null;
}

// find()는 deletedAt IS NULL 자동 적용
await userRepo.find({ where: { email: 'user@example.com' } });

// createQueryBuilder()는 기본 필터 적용 안 됨 - 직접 추가 필요
await userRepo.createQueryBuilder('user')
  .where('user.email = :email', { email: 'user@example.com' })
  .andWhere('user.deletedAt IS NULL')  // 반드시 명시
  .getOne();
```

**삭제 비율이 높아진 테이블**: 테이블 전체 row 중 삭제된 비율이 70%를 넘어가면, 전체 테이블을 대상으로 하는 집계 쿼리나 통계 쿼리에서 비용이 높아진다. 이 시점에 `deleted_at IS NOT NULL`인 row를 별도 아카이브 테이블로 이동시키는 데이터 수명 주기 관리를 도입한다.

```sql
-- 1년 이상 된 삭제 row를 아카이브 테이블로 이동
INSERT INTO orders_archive
  SELECT * FROM orders
  WHERE deleted_at < NOW() - INTERVAL 1 YEAR;

DELETE FROM orders
WHERE deleted_at < NOW() - INTERVAL 1 YEAR;
```

**카운트 쿼리**: `COUNT(*)`에 소프트 삭제 필터가 없으면 삭제된 row까지 집계된다. 통계 대시보드에서 숫자가 맞지 않는 버그가 이 원인인 경우가 많다. `COUNT(*) WHERE deleted_at IS NULL`이 표준 패턴이다.

MySQL에서 `COUNT(*) WHERE deleted_at IS NULL` 쿼리가 느리면 커버링 인덱스 여부를 확인한다. `(deleted_at)` 단일 인덱스나 `(deleted_at, id)` 인덱스가 있으면 테이블 접근 없이 인덱스만으로 카운트를 처리할 수 있다.

PostgreSQL에서는 부분 인덱스가 있으면 `COUNT(*) WHERE deleted_at IS NULL`이 인덱스 온리 스캔으로 처리된다.
