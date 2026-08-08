---
title: 컬럼 접미 패턴
tags: [database, java, rdbms, mysql]
updated: 2026-08-07
---

# 컬럼 접미 패턴

컬럼 이름은 그 자체로 타입과 용도를 설명해야 한다. `created`와 `created_at`은 의미가 다르다. `is_deleted`와 `deleted_yn`은 같은 정보를 담지만 팀에 따라 혼재한다. 접미사 규칙 없이 프로젝트가 커지면 리뷰어가 컬럼 이름만 보고 타입을 유추할 수 없는 상황이 발생한다.

접미사는 컬럼이 어떤 종류의 값을 담는지 암묵적으로 알려준다. 팀 전체가 같은 규칙을 쓰면 DDL을 보지 않고도 컬럼의 의미를 파악할 수 있다.

---

## `_at` — 타임스탬프

특정 이벤트가 발생한 시각을 담는다. `_at`이 붙으면 DATETIME 또는 TIMESTAMP 타입이다.

```sql
created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
deleted_at   DATETIME NULL,
published_at DATETIME NULL,
expired_at   DATETIME NULL
```

`_at`은 단순 날짜(DATE)에는 쓰지 않는다. 생일이나 계약 만료일처럼 시각이 아닌 날짜 값은 `_date`를 쓴다.

```sql
birth_date     DATE NOT NULL,   -- 날짜만 의미 있는 경우
contract_end_date DATE NULL
```

`_at`을 `_date`와 혼용하면 실수가 생긴다. 예를 들어 `deleted_at DATE`로 정의하면 같은 날 여러 번 삭제된 경우 시각 정보가 사라진다. 소프트 삭제를 구현하면서 `deleted_at DATETIME NULL`로 써야 할 것을 `deleted_date DATE NULL`로 선언하는 실수가 실제로 자주 발생한다.

시간대 처리 방침도 정해야 한다. MySQL TIMESTAMP는 UTC로 저장하고 조회 시 세션 time_zone에 맞춰 변환한다. DATETIME은 그대로 저장한다. 글로벌 서비스라면 DATETIME에 UTC 값을 명시적으로 저장하고 애플리케이션에서 변환하는 방식을 쓰는 팀이 많다. 규칙을 정하지 않으면 TIMESTAMP로 저장된 컬럼과 DATETIME으로 저장된 컬럼이 섞이고, 시간대 비교 쿼리에서 미묘한 버그가 생긴다.

---

## `_id` — 식별자

다른 엔티티를 참조하는 FK 컬럼 또는 외부 시스템의 식별자를 담는다.

```sql
user_id      BIGINT NOT NULL,
order_id     BIGINT NOT NULL,
category_id  INT NOT NULL,
external_id  CHAR(26) NOT NULL  -- 외부 노출용 ULID
```

자기 자신의 PK 컬럼도 `id`라고 쓰는 경우가 대부분이다. `user_id`를 PK로 쓰는 방식도 있지만, JPA와 TypeORM에서 `@Id` 필드 이름이 `id`로 굳어져 있어 `id`로 통일하는 팀이 많다.

문제는 `_id`가 FK인지 내부 시퀀스인지 외부 시스템 ID인지 이름만 보면 알 수 없다는 점이다. 이를 구분하기 위해 외부 시스템 ID에는 시스템 이름을 명시하는 방식을 쓴다.

```sql
-- 외부 시스템 식별자
kakao_user_id   VARCHAR(100),
stripe_charge_id VARCHAR(100),
pg_transaction_id VARCHAR(100)
```

`_id` 컬럼에 NULL을 허용할 때는 NULL의 의미를 명확히 해야 한다. `assigned_user_id IS NULL`이 "미배정"을 의미하는지 "삭제된 사용자"를 의미하는지 컬럼 이름만으로는 구분할 수 없다. 주석을 달거나 별도 상태 컬럼으로 분리해야 한다.

---

## `_yn` / `_flag` — 불리언

`_yn`은 한국 SI 환경에서 오래된 관행이다. `Y`/`N` 문자열 또는 `TINYINT(1)` `1`/`0`으로 저장한다.

```sql
use_yn      CHAR(1) NOT NULL DEFAULT 'Y',   -- 'Y' 또는 'N'
delete_yn   CHAR(1) NOT NULL DEFAULT 'N',
active_yn   CHAR(1) NOT NULL DEFAULT 'Y'
```

`_flag`는 주로 `TINYINT(1)` 또는 BOOLEAN 타입과 함께 쓴다.

```sql
is_active   BOOLEAN NOT NULL DEFAULT TRUE,
is_deleted  TINYINT(1) NOT NULL DEFAULT 0,
is_verified BOOLEAN NOT NULL DEFAULT FALSE
```

`is_` 접두사와 `_yn` 접미사가 팀 내에서 섞이면 혼란이 생긴다. `is_deleted`와 `delete_yn`이 같은 테이블에 공존하는 경우가 있다. 둘 중 하나만 쓰기로 정해야 한다.

`_yn` 방식의 실질적 문제는 타입 강제가 없다는 점이다. `CHAR(1)` 컬럼에 `Y`/`N` 외의 값이 들어가는 것을 DB 레벨에서 막으려면 CHECK 제약이 필요하다.

```sql
use_yn CHAR(1) NOT NULL DEFAULT 'Y',
CHECK (use_yn IN ('Y', 'N'))
```

MySQL 8.0 이전 버전에서는 CHECK 제약이 파싱만 되고 실제로 적용되지 않았다. 8.0.16부터 실제로 동작한다. 레거시 MySQL 환경에서는 애플리케이션 레이어에서만 유효성 검사가 이뤄지는 경우가 많다.

BOOLEAN 타입을 쓰면 더 명확하다.

```sql
is_active   BOOLEAN NOT NULL DEFAULT TRUE
```

PostgreSQL은 BOOLEAN 타입을 네이티브로 지원한다. MySQL은 `TINYINT(1)`의 별칭으로 처리하며, `TRUE`/`FALSE`는 각각 `1`/`0`으로 저장된다.

---

## `_type` / `_cd` — 분류값

엔티티의 종류나 분류를 담는다. 유한한 값 집합에서 하나를 선택한다.

```sql
-- _type: 비교적 긴 문자열 또는 의미 있는 영어 단어
payment_type  VARCHAR(20) NOT NULL,  -- 'card', 'bank_transfer', 'virtual_account'
event_type    VARCHAR(30) NOT NULL,  -- 'CLICK', 'PURCHASE', 'REFUND'
member_type   VARCHAR(20) NOT NULL   -- 'INDIVIDUAL', 'CORPORATE'

-- _cd: 코드성 짧은 값, 레거시 SI에서 많이 씀
payment_cd    CHAR(4) NOT NULL,      -- 'CARD', 'BNKX', 'VATL'
gender_cd     CHAR(1) NOT NULL,      -- 'M', 'F', 'X'
nation_cd     CHAR(2) NOT NULL       -- ISO 3166-1 alpha-2
```

`_type`과 `_cd`는 용도가 겹친다. 차이를 정하지 않으면 어느 것을 써야 할지 기준이 없어진다. 한 가지 방법은 `_type`은 의미 있는 영단어 값을, `_cd`는 코드 테이블을 참조하는 짧은 코드 값을 저장하는 것으로 구분하는 것이다. 코드 테이블 기반 시스템을 쓰지 않는다면 `_type`으로 통일하는 편이 낫다.

ENUM 타입을 쓰는 경우도 있다.

```sql
status ENUM('PENDING', 'ACTIVE', 'SUSPENDED', 'DELETED') NOT NULL DEFAULT 'PENDING'
```

MySQL ENUM은 값을 추가할 때 ALTER TABLE이 필요하다. 값이 자주 늘어나는 경우 운영 중 DDL 변경이 부담이 된다. PostgreSQL에서도 ENUM 타입 수정은 `ALTER TYPE ... ADD VALUE`로 가능하지만 트랜잭션 밖에서만 실행된다. 변경 가능성이 있는 분류값에는 VARCHAR를 쓰고 애플리케이션에서 유효한 값 목록을 관리하는 방식을 선호하는 이유다.

---

## `_cnt` — 카운트

집계된 수치를 담는 캐시 컬럼이다.

```sql
view_cnt     INT NOT NULL DEFAULT 0,
comment_cnt  INT NOT NULL DEFAULT 0,
like_cnt     INT NOT NULL DEFAULT 0,
retry_cnt    INT NOT NULL DEFAULT 0
```

`_cnt`는 실시간 집계 비용을 피하기 위한 역정규화 컬럼이다. 실제 카운트는 다른 테이블에서 집계하면 정확하지만 느리고, `_cnt`는 빠르지만 정합성 유지 책임이 생긴다.

정합성 유지 방법은 두 가지다. 댓글이 INSERT/DELETE될 때마다 `comment_cnt`를 UPDATE하는 방식, 또는 배치로 주기적으로 동기화하는 방식이다. 전자는 동시성 문제가 생길 수 있다. 같은 게시물에 댓글이 동시에 달리면 카운트가 밀릴 수 있으므로 `UPDATE posts SET comment_cnt = comment_cnt + 1 WHERE id = ?` 형태로 원자적으로 처리해야 한다.

`_cnt` 대신 `_count`를 쓰는 팀도 있다. 영문 기준 의미가 더 명확하지만 타자가 두 글자 더 들어간다는 이유로 `_cnt`를 선호하는 경우도 있다. 팀 내 통일이 중요하지 둘 중 어느 것이 옳다고 할 수는 없다.

`_cnt`가 `INT`인데 언더플로가 생기지 않도록 주의해야 한다. 댓글 삭제 이벤트가 중복 발생하거나 순서가 바뀌면 카운트가 음수가 되는 경우가 있다. `UNSIGNED` 타입으로 정의하면 음수 저장 시도에서 에러가 나지만, 부주의하게 처리하면 rollback 없이 0 미만으로 가는 대신 0으로 clamp되는 동작을 이용하기도 한다.

---

## `_status` — 상태

엔티티의 현재 상태를 담는다. `_type`이 분류라면 `_status`는 라이프사이클 상태다.

```sql
order_status   VARCHAR(20) NOT NULL DEFAULT 'PENDING',
payment_status VARCHAR(20) NOT NULL DEFAULT 'WAITING',
batch_status   VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
```

`_status`와 `_type`의 혼용이 가장 흔한 충돌 포인트다. `order_type`이 주문의 종류(일반/예약/정기)라면 `order_status`는 주문의 진행 상태(접수/처리중/완료/취소)다. 상태는 시간이 지나면서 전이하지만 종류는 생성 시점에 결정되고 바뀌지 않는다. 이 구분이 명확하지 않으면 `order_status`에 종류와 상태가 섞여 들어가는 경우가 생긴다.

상태 전이 규칙을 DB 레벨에서 강제하기는 어렵다. `PENDING → PROCESSING → COMPLETED`나 `PENDING → CANCELLED` 같은 전이 규칙은 애플리케이션 레이어에서 검사해야 한다. DB는 현재 상태가 유효한 값인지만 확인한다.

---

## 혼용 금지 사례

같은 프로젝트에서 아래처럼 섞이면 어떤 컬럼이 어떤 타입인지 파악하기 어려워진다.

```sql
-- 혼용 예: 피해야 하는 상황
created        DATETIME,     -- _at 없음
is_deleted     BOOLEAN,      -- is_ 접두사
delete_yn      CHAR(1),      -- _yn 접미사 (동일 의미 충돌)
useFlag        TINYINT(1),   -- camelCase + _flag 혼용
payment_status VARCHAR(20),  -- _status 사용
order_type     VARCHAR(20),  -- _type 사용 (같은 테이블 내 기준 없음)
```

`is_deleted`와 `delete_yn`이 같은 테이블에 함께 있는 경우가 실제로 발생한다. 마이그레이션 과정에서 한쪽을 추가하고 반대쪽을 미처 삭제하지 않거나, 서로 다른 개발자가 같은 개념을 다른 이름으로 추가할 때 생긴다.

규칙의 예시:

- 타임스탬프: `_at` (DATE 타입만 담는 경우 `_date`)
- 불리언: `is_` 접두사 + BOOLEAN 타입으로 통일 (`_yn` 쓰지 않음)
- 분류: `_type`으로 통일 (코드 테이블 쓰지 않을 경우)
- 카운트: `_cnt` 또는 `_count` 중 하나로 통일
- 상태: `_status`

이 다섯 가지 접미사 기준만 명문화해도 컬럼 이름에서 발생하는 PR 리뷰 코멘트가 줄어든다.

---

## 팀 규약 수립 시 충돌 포인트

### `_yn` vs `is_` 진영

레거시 SI 출신 개발자와 스타트업 출신 개발자가 섞인 팀에서 가장 자주 충돌한다. `_yn` 방식은 CHAR(1)에 'Y'/'N'을 담고, `is_` 방식은 BOOLEAN에 true/false를 담는다. 어느 쪽이든 팀 내 통일이 우선이다.

JPA 입장에서는 `is_` 방식이 편하다. `@Column(name = "is_active")` 선언 후 필드를 `boolean isActive`로 선언하면 Getter가 `isIsActive()`가 되는 문제가 생긴다. 이를 피하려면 필드 이름을 `active`로 두고 컬럼 이름만 `is_active`로 매핑하거나, `@JsonProperty("is_active")`를 따로 달아야 한다.

```java
@Column(name = "is_active")
private boolean active;  // 필드는 active, 컬럼은 is_active

public boolean isActive() {  // 자동 생성 getter
    return active;
}
```

TypeORM에서는 문제가 없다.

```typescript
@Column({ name: 'is_active', type: 'boolean', default: true })
isActive: boolean;
```

### `created_at` vs `create_at` vs `createdAt`

스네이크 케이스 자체에서도 과거형 사용 여부로 나뉜다. `created_at`(과거분사)과 `create_at`(동사원형)이 혼용되면 일관성이 깨진다. 표준은 과거분사형(`created_at`, `updated_at`, `deleted_at`)이다. 동사원형을 쓰는 경우는 명령형의 뉘앙스가 있어 타임스탬프 컬럼 이름으로 어색하다.

### NULL 허용 여부

`deleted_at IS NULL`을 소프트 삭제 여부 확인에 쓰는 패턴은 `_at` 컬럼의 NULL을 의미 있게 사용하는 방식이다. 편하지만 "언제 삭제됐는가"와 "삭제됐는가"가 하나의 컬럼에 섞인다. 인덱스에서 NULL은 다르게 처리된다. MySQL에서 `deleted_at IS NULL` 조건은 일반 범위 조건과 달리 인덱스 활용 방식이 달라질 수 있다.

별도 `is_deleted` 컬럼과 `deleted_at` 컬럼을 함께 두는 팀도 있다. 저장 공간이 약간 늘지만 쿼리가 명확해진다.

### 상태 값 케이스

`order_status` 값을 `'pending'`(소문자)으로 할지 `'PENDING'`(대문자)으로 할지도 통일해야 한다. 소문자는 Python/JS 관행, 대문자는 Java enum 관행이다. 팀 주력 언어에 맞추되 DB 내에서 섞이지 않게 한다.

---

## JPA 매핑 시 주의사항

### `_at` 컬럼

```java
@Column(name = "created_at", nullable = false, updatable = false)
@CreationTimestamp
private LocalDateTime createdAt;

@Column(name = "updated_at", nullable = false)
@UpdateTimestamp
private LocalDateTime updatedAt;

@Column(name = "deleted_at")
private LocalDateTime deletedAt;
```

`@CreationTimestamp`와 `@UpdateTimestamp`는 Hibernate가 자동으로 값을 설정한다. `updatedAt` 컬럼에 MySQL `ON UPDATE CURRENT_TIMESTAMP`를 동시에 적용하면 Hibernate 업데이트와 MySQL 트리거가 이중으로 작동한다. 어느 쪽 하나만 쓰도록 결정해야 한다.

`LocalDateTime`을 쓸 때 JPA가 JDBC 드라이버에 어떤 시간대로 값을 전달하는지 확인해야 한다. Spring Boot에서 `spring.jpa.properties.hibernate.jdbc.time_zone=UTC`를 설정하지 않으면 JVM 시간대에 따라 저장되는 값이 달라질 수 있다.

### `_yn` 컬럼

`CHAR(1)` 컬럼을 boolean으로 매핑하려면 AttributeConverter가 필요하다.

```java
@Converter
public class YnToBooleanConverter implements AttributeConverter<Boolean, String> {
    @Override
    public String convertToDatabaseColumn(Boolean attribute) {
        return Boolean.TRUE.equals(attribute) ? "Y" : "N";
    }

    @Override
    public Boolean convertToEntityAttribute(String dbData) {
        return "Y".equals(dbData);
    }
}

@Column(name = "use_yn", length = 1, nullable = false)
@Convert(converter = YnToBooleanConverter.class)
private boolean useYn;
```

BOOLEAN 타입 컬럼이라면 그냥 쓸 수 있다.

```java
@Column(name = "is_active", nullable = false)
private boolean active;
```

### `_status` / `_type` 컬럼

Java Enum을 문자열로 저장하려면 `@Enumerated(EnumType.STRING)`을 쓴다.

```java
public enum OrderStatus {
    PENDING, PROCESSING, COMPLETED, CANCELLED
}

@Column(name = "order_status", length = 20, nullable = false)
@Enumerated(EnumType.STRING)
private OrderStatus orderStatus;
```

`EnumType.ORDINAL`은 Enum 순서(0, 1, 2...)를 DB에 저장한다. Enum 멤버 순서가 바뀌면 기존 데이터가 깨지므로 쓰지 않는다.

DB에 이미 저장된 값과 Java Enum 이름이 다를 경우 JPA 6.2부터 추가된 `@EnumMapping`을 쓰거나, 직접 AttributeConverter를 구현해야 한다.

---

## TypeORM 매핑 시 주의사항

### `_at` 컬럼

```typescript
@CreateDateColumn({ name: 'created_at' })
createdAt: Date;

@UpdateDateColumn({ name: 'updated_at' })
updatedAt: Date;

@Column({ name: 'deleted_at', type: 'datetime', nullable: true })
deletedAt: Date | null;
```

`@DeleteDateColumn`을 쓰면 TypeORM의 소프트 삭제 기능과 자동으로 연동된다. `softDelete(id)` 호출 시 `deleted_at`에 현재 시각을 자동으로 설정하고, 이후 find 쿼리에서 `deleted_at IS NULL` 조건을 자동으로 추가한다.

```typescript
@DeleteDateColumn({ name: 'deleted_at' })
deletedAt: Date | null;
```

주의할 점은 `@DeleteDateColumn`을 쓸 때 `withDeleted()` 옵션을 명시하지 않으면 삭제된 레코드가 조회에서 자동으로 빠진다는 것이다. 관리자 화면에서 삭제된 데이터를 조회해야 할 때 이를 잊으면 데이터가 보이지 않아 디버깅에 시간을 쓰는 경우가 있다.

### `_status` / `_type` 컬럼

TypeScript enum을 직접 매핑할 수 있다.

```typescript
export enum OrderStatus {
    PENDING = 'PENDING',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    CANCELLED = 'CANCELLED',
}

@Column({
    name: 'order_status',
    type: 'varchar',
    length: 20,
    enum: OrderStatus,
    default: OrderStatus.PENDING,
})
orderStatus: OrderStatus;
```

TypeScript enum 값을 문자열로 명시하지 않으면(`PENDING = 'PENDING'` 대신 `PENDING`만 쓰면) TypeORM이 숫자 인덱스를 저장하는 경우가 있다. enum 값은 항상 문자열로 명시하는 것이 안전하다.

`_cnt` 컬럼은 별도 처리 없이 `number` 타입으로 매핑된다.

```typescript
@Column({ name: 'view_cnt', type: 'int', default: 0 })
viewCnt: number;
```

증가 쿼리는 TypeORM QueryBuilder를 써서 원자적으로 처리한다.

```typescript
await this.postRepository
    .createQueryBuilder()
    .update(Post)
    .set({ viewCnt: () => 'view_cnt + 1' })
    .where('id = :id', { id })
    .execute();
```

`entity.viewCnt += 1; await save(entity)` 방식은 select 후 update 사이에 동시 요청이 들어오면 카운트가 씹힌다.
