---
title: 대리키
tags: [database, java, devops, backend]
updated: 2026-07-30
---

# 대리키

대리키(Surrogate Key)는 도메인 의미 없이 DB가 생성하는 인위적인 식별자를 PK로 쓰는 방식이다. auto-increment, UUID, Snowflake ID가 모두 여기에 해당한다. 자연키(Natural Key)가 도메인 값 자체를 PK로 삼는 것과 대비된다.

실무에서 자연키를 PK로 설계했다가 나중에 대리키로 바꾸는 작업은 생각보다 훨씬 고통스럽다. 데이터가 수백만 건 쌓인 뒤에는 FK 컬럼 전체를 변경해야 하고, 그 과정에서 서비스 중단이 불가피한 경우도 있다. 어떤 경우에 대리키를 선택해야 하는지, JPA에서 어떻게 동작하는지, 마이그레이션은 어떻게 처리하는지 정리한다.

## 복합 PK vs 대리키

많은 팀이 N:M 관계 테이블에서 복합 PK를 선택한다. 직관적이고 별도 컬럼이 필요 없다. 그런데 복합 PK는 몇 가지 상황에서 문제가 된다.

### 복합 PK가 유지 가능한 경우

값이 변하지 않고, FK로 참조되는 일이 없으며, 해당 테이블에 직접 접근하는 API가 없을 때다.

```sql
-- 단순 N:M 관계 (조회와 삽입만 일어남)
CREATE TABLE user_roles (
    user_id  BIGINT NOT NULL,
    role_id  BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
```

이 경우 `(user_id, role_id)` 조합이 PK이고, 삽입/삭제/조회가 전부라면 복합 PK로 충분하다.

### 복합 PK가 문제가 되는 경우

연결 테이블이 단순 관계 이상의 속성을 갖기 시작할 때부터 복잡해진다.

```sql
-- 복합 PK에 컬럼이 추가되기 시작하면
CREATE TABLE order_items (
    order_id    BIGINT NOT NULL,
    product_id  BIGINT NOT NULL,
    quantity    INT NOT NULL,
    unit_price  DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id)
    -- order_items 자체를 참조하는 테이블이 생기면 FK가 두 컬럼이 됨
);
```

`order_items`를 참조하는 테이블이 생기면 FK를 `(order_id, product_id)` 두 컬럼으로 선언해야 한다. 인덱스 크기가 늘고 조인 조건이 복잡해진다.

같은 `order_id`와 `product_id` 조합의 주문이 두 번 발생하는 도메인 변경(예: 같은 상품을 다른 옵션으로 두 번 주문)이 생기면 PK 자체를 바꿔야 한다.

```sql
-- 대리키 도입 후
CREATE TABLE order_items (
    id          BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_id    BIGINT NOT NULL,
    product_id  BIGINT NOT NULL,
    quantity    INT NOT NULL,
    unit_price  DECIMAL(10, 2) NOT NULL,
    UNIQUE INDEX uq_order_product (order_id, product_id), -- 중복 방지는 UNIQUE로
    FOREIGN KEY (order_id)   REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

이 구조에서 `order_items`를 참조하는 테이블은 `item_id BIGINT` 컬럼 하나로 FK를 선언할 수 있다.

### 선택 기준

| 상황 | 선택 |
|------|------|
| 단순 연결 테이블이고 다른 테이블에서 FK로 참조되지 않음 | 복합 PK |
| 연결 테이블에 추가 속성이 있거나 생길 가능성이 있음 | 대리키 |
| 연결 테이블 자체를 API로 직접 식별해야 함 | 대리키 |
| 구성 요소 중 하나가 변경될 수 있음 | 대리키 |

자연키나 복합 PK로 시작했더라도 도메인이 확장되면 대리키가 필요해지는 경우가 많다. 초기 설계에서 확장 가능성이 조금이라도 보인다면 대리키가 낫다.

## JPA @GeneratedValue 전략별 동작

JPA에서 대리키를 선언할 때 `@GeneratedValue`의 strategy 옵션이 실제로 어떻게 동작하는지 모르면 성능 문제를 유발할 수 있다.

### IDENTITY

```typescript
// TypeORM — IDENTITY 전략 (AUTO_INCREMENT / SERIAL)
@Entity()
export class Order {
    @PrimaryGeneratedColumn()
    id: number;
}
```

INSERT 후 DB가 생성한 값을 `LAST_INSERT_ID()` / `RETURNING id`로 조회한다. MySQL의 `AUTO_INCREMENT`와 1:1 대응한다.

핵심 문제가 있다. TypeORM은 기본적으로 각 `save()` 호출 시 INSERT를 실행하며, IDENTITY 전략에서는 INSERT 전에 PK 값을 알 수 없으므로 배치 INSERT가 불가능하다.

수백 건을 한 번에 저장하는 상황에서 IDENTITY 전략은 SQL을 N번 개별 실행한다.

```typescript
// 이 코드는 IDENTITY 전략에서 SQL 100번 실행
for (const order of orders) {
    await manager.save(Order, order); // 즉시 INSERT
}
```

대용량 배치 처리가 필요하다면 TypeORM의 `insert()` 메서드나 raw 쿼리를 직접 사용한다.

### SEQUENCE

```typescript
// TypeORM — SEQUENCE 전략 (PostgreSQL)
@Entity()
export class Order {
    @PrimaryGeneratedColumn('increment')
    id: number;
}
```

PostgreSQL이나 Oracle의 시퀀스 객체를 사용한다. Hibernate는 `allocationSize` 만큼 미리 시퀀스 값을 예약해 메모리에 캐싱한다. 50개씩 예약하면 50번의 `persist()` 동안 시퀀스 조회가 1번만 발생한다.

MySQL 8.0 이전에는 시퀀스 객체가 없어 Hibernate가 별도 테이블(`hibernate_sequence`)을 만들어 시퀀스를 에뮬레이션한다. 이 테이블에 잠금이 걸리므로 경합이 발생할 수 있다.

```sql
-- Hibernate가 MySQL에서 시퀀스를 에뮬레이션할 때 생성하는 테이블
CREATE TABLE hibernate_sequence (next_val BIGINT);
```

MySQL에서 SEQUENCE 전략을 쓰면 이 에뮬레이션 테이블에 UPDATE 잠금이 걸려 삽입 처리량에 병목이 생긴다. MySQL에서는 IDENTITY 전략이 현실적이다.

### TABLE

시퀀스 에뮬레이션 테이블을 명시적으로 정의하는 방식이다. 이식성은 가장 높지만 성능이 가장 낮다. 잠금 경합이 심해 실무에서는 거의 쓰지 않는다.

### UUID 기반 생성

```typescript
// TypeORM — UUID 전략
@Entity()
export class Session {
    @PrimaryGeneratedColumn('uuid')
    id: string;
}
```

기본으로 UUID v4를 생성한다. MySQL InnoDB에서 PK로 쓰면 페이지 분할 문제가 발생하므로, UUID를 쓴다면 애플리케이션에서 UUID v7을 직접 생성하고 `@PrimaryColumn`으로 할당하는 방식이 낫다.

```typescript
import { v7 as uuidv7 } from 'uuid';

@Entity()
export class Session {
    @PrimaryColumn('uuid')
    id: string;

    @BeforeInsert()
    generateId(): void {
        if (!this.id) {
            this.id = uuidv7(); // UUID v7 — 시간 순 정렬 가능
        }
    }
}
```

`@PrimaryGeneratedColumn('uuid')`를 쓰면 ID 생성을 TypeORM에 위임하고, `@PrimaryColumn` + `@BeforeInsert()`를 쓰면 생성 시점과 방식을 제어할 수 있다.

## 키 공간 설계

대리키 타입을 고를 때 키 공간(전체 발급 가능한 값의 범위)을 먼저 따져야 한다. 단일 DB에서 쓰는 `AUTO_INCREMENT`와 분산 환경에서 독립적으로 발급하는 UUID/ULID는 설계 관점이 다르다.

### AUTO_INCREMENT 상한

MySQL `AUTO_INCREMENT`는 컬럼 타입이 상한을 결정한다.

```sql
-- INT (부호 있는 4바이트): 상한 2,147,483,647 ≈ 21억
CREATE TABLE events (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY
);

-- BIGINT (부호 있는 8바이트): 상한 9,223,372,036,854,775,807 ≈ 922경
CREATE TABLE events (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY
);
```

INT 상한(21억)은 초당 1만 건 삽입 기준으로 약 59시간이면 소진된다. 소비자 서비스 규모에서 실제로 상한에 도달해 장애가 난 사례가 있다. 트래픽이 예측하기 어렵다면 처음부터 BIGINT를 쓴다.

BIGINT 상한(922경, ≈ 9.2 × 10^18)은 초당 100만 건을 삽입해도 약 29만 년이 걸린다. 단일 DB에서 순차 발급하는 한 실질적인 한계는 아니다.

`AUTO_INCREMENT`는 DB 서버가 단일 카운터를 관리하므로 분산 노드에서 독립적으로 발급할 수 없다. 여러 노드에서 중복 없이 발급해야 한다면 UUID나 ULID가 필요하다.

### UUID v4와 UUID v7의 키 공간

UUID는 128비트 고정 길이다. v4와 v7 모두 같은 총 비트 수를 쓰지만 비트 배치가 다르다.

**UUID v4**

```
xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
(x = random, 4 = version, y = variant(8/9/a/b))

총 128비트
├─ 버전(4비트) + 배리언트(2비트) = 6비트 고정
└─ 유효 랜덤 비트: 122비트 → 키 공간 2^122 ≈ 5.3 × 10^36
```

키 공간 자체는 충분히 넓다. 문제는 완전 랜덤이라는 특성이다. InnoDB는 PK 기준으로 레코드를 물리적으로 정렬한다(클러스터드 인덱스). 새 UUID v4가 기존 레코드 사이의 무작위 위치에 삽입되면서 B-Tree 페이지 분할이 빈번하게 일어나고, 버퍼 풀 캐시 히트율이 낮아진다. 데이터가 수백만 건을 넘으면 INSERT 성능이 눈에 띄게 느려진다.

**UUID v7**

```
tttttttt-tttt-7xxx-yxxx-xxxxxxxxxxxx
(t = 48비트 타임스탬프, 7 = version, x = random, y = variant)

총 128비트
├─ 타임스탬프: 48비트 (Unix epoch 밀리초)
├─ 버전: 4비트
├─ 밀리초 내 랜덤/시퀀스: 12비트
├─ 배리언트: 2비트
└─ 랜덤: 62비트

밀리초 내 유효 랜덤 비트: 74비트 (12 + 62)
타임스탬프 범위: 2^48 밀리초 ≈ 8,925년
```

48비트 타임스탬프가 앞에 오기 때문에 시간이 흐를수록 UUID 값이 단조 증가한다. InnoDB에서 새 레코드가 항상 PK 인덱스 끝에 추가되므로 페이지 분할이 거의 발생하지 않는다.

같은 밀리초 안에서는 74비트 랜덤 공간에서 값을 고른다. 밀리초당 수천만 건이 아닌 이상 충돌 가능성은 없다.

### ULID 키 공간 구조

ULID(Universally Unique Lexicographically Sortable Identifier)는 UUID v7과 유사하게 타임스탬프 + 랜덤 구조를 Crockford Base32로 인코딩한 26자 문자열이다.

```
01ARZ3NDEKTSV4RRFFQ69G5FAV

128비트 구조:
┌──────────────────────┬─────────────────────────────────────────┐
│  타임스탬프 48비트    │              랜덤 80비트                 │
│  (Unix epoch 밀리초) │                                         │
└──────────────────────┴─────────────────────────────────────────┘

타임스탬프 범위: 2^48 밀리초 ≈ 8,925년
밀리초 내 랜덤 공간: 2^80 ≈ 1.2 × 10^24
```

UUID v7의 74비트 대비 밀리초 내 랜덤 비트가 80비트로 더 넓다. 분산 환경에서 같은 밀리초에 여러 노드가 각자 랜덤 80비트를 독립적으로 초기화하므로 충돌 가능성은 충분히 낮다.

같은 밀리초 내에서 삽입 순서까지 보장해야 할 때는 `monotonicFactory`를 쓴다.

```typescript
import { monotonicFactory } from 'ulid';

const ulid = monotonicFactory();

const id1 = ulid();
const id2 = ulid(); // 같은 밀리초여도 id1 < id2 보장
// 랜덤 80비트의 최하위 비트를 1씩 올리는 방식으로 단조성 유지
```

단조성 모드에서 같은 밀리초에 2^80개 이상 생성하면 랜덤 부분이 오버플로된다. 밀리초당 수십억 건이 아닌 이상 이론적인 한계에 불과하다.

### 분산 환경에서의 충돌 확률

생일 문제(Birthday Problem) 공식으로 충돌 확률을 근사할 수 있다. k개 ID를 n 크기의 공간에서 생성할 때, 충돌이 하나 이상 발생할 확률은 다음과 같다.

```
P(충돌) ≈ k² / 2n   (k << √n 일 때)
```

| 타입 | 유효 랜덤 비트 | 키 공간 (n) | 누적 10억 개 생성 시 충돌 확률 |
|------|--------------|-------------|-------------------------------|
| UUID v4 | 122비트 | 2^122 ≈ 5.3 × 10^36 | ≈ 9.4 × 10^-20 (사실상 0) |
| UUID v7 (밀리초 내) | 74비트 | 2^74 ≈ 1.9 × 10^22 | 밀리초당 10만 건 시 ≈ 3 × 10^-10 |
| ULID (밀리초 내) | 80비트 | 2^80 ≈ 1.2 × 10^24 | 밀리초당 10만 건 시 ≈ 4 × 10^-12 |

UUID v4는 누적 생성량 기준으로 충돌이 실질적으로 불가능하다. UUID v7과 ULID는 밀리초마다 랜덤이 재초기화되므로 같은 밀리초 내 동시 생성 건수가 충돌 확률을 결정한다.

실제 분산 환경에서 대리키 충돌이 발생한 사례는 UUID가 아니라 `timestamp + 서버 ID + 시퀀스` 형태의 커스텀 ID에서 서버 ID 중복 설정이나 NTP 재동기화로 인한 시계 역행이 원인인 경우가 대부분이었다.

## 브릿지 테이블에 대리키 추가

N:M 관계를 표현하는 브릿지 테이블(연결 테이블)에 대리키를 추가하는 패턴이다. 처음부터 추가하는 경우와 기존 테이블에 추가하는 경우로 나뉜다.

### 처음부터 설계하는 경우

```sql
CREATE TABLE post_tags (
    id         BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    post_id    BIGINT NOT NULL,
    tag_id     BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX uq_post_tag (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
);
```

`UNIQUE INDEX`로 동일 조합의 중복을 막는다. `post_id + tag_id` 조합의 조회가 자주 일어나면 `UNIQUE INDEX`가 그대로 인덱스 역할을 하므로 별도 인덱스가 필요 없다.

`tag_id` 기준으로 포스트를 찾는 쿼리(`WHERE tag_id = ?`)가 있다면 `tag_id` 단독 인덱스를 추가해야 한다. `UNIQUE INDEX (post_id, tag_id)`는 `post_id` 단독 검색에는 유효하지만 `tag_id` 단독 검색에는 사용되지 않는다.

```sql
-- tag_id 기준 검색을 위한 인덱스
INDEX idx_tag_id (tag_id)
```

### TypeORM에서 브릿지 테이블 엔티티화

단순 N:M 관계를 `@ManyToMany`로 매핑하면 브릿지 테이블을 직접 다루기 어렵다. 추가 속성이 생기거나 브릿지 테이블 레코드를 직접 식별해야 할 때 엔티티로 분리한다.

```typescript
@Entity('post_tags')
export class PostTag {
    @PrimaryGeneratedColumn()
    id: number;

    @ManyToOne(() => Post, { lazy: true })
    @JoinColumn({ name: 'post_id' })
    post: Post;

    @ManyToOne(() => Tag, { lazy: true })
    @JoinColumn({ name: 'tag_id' })
    tag: Tag;

    @Column({ name: 'created_at', type: 'timestamp', default: () => 'CURRENT_TIMESTAMP' })
    createdAt: Date;
}
```

`@ManyToMany` 대신 `@OneToMany` + `@ManyToOne`으로 풀어낸 구조다. `Post`에서는 `@OneToMany(() => PostTag, (pt) => pt.post)`로, `Tag`에서는 `@OneToMany(() => PostTag, (pt) => pt.tag)`로 양방향을 설정할 수 있다.

이 방식에서 중복 방지는 DB의 `UNIQUE INDEX`가 담당하고, TypeORM 레이어에서는 중복 삽입 시 unique 제약 위반 예외를 잡아서 처리한다.

## 자연키 테이블에 대리키 후행 추가 마이그레이션

기존에 자연키를 PK로 쓰던 테이블에 대리키를 추가하는 작업은 여러 단계로 나눠 처리해야 한다. 한 번에 PK를 바꾸려 하면 잠금 범위가 너무 넓어 서비스 중단이 발생한다.

### 상황

`email`을 PK로 쓰는 `users` 테이블이 있고, 이를 참조하는 FK가 3개 테이블에 분산돼 있다.

```sql
-- 기존 구조
CREATE TABLE users (
    email VARCHAR(254) PRIMARY KEY,
    name  VARCHAR(50) NOT NULL
);

CREATE TABLE orders (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(254) NOT NULL,
    FOREIGN KEY (user_email) REFERENCES users(email)
);
```

### 단계별 마이그레이션

**1단계: 새 컬럼 추가 (무중단)**

```sql
ALTER TABLE users
    ADD COLUMN id BIGINT NOT NULL AUTO_INCREMENT UNIQUE FIRST;
```

`PRIMARY KEY`로 바꾸지 않고 `UNIQUE`만 걸어둔다. 기존 데이터에 값이 채워지고 새 삽입에서도 자동 증가한다. 이 시점에서 서비스는 중단되지 않는다.

**2단계: FK 참조 테이블에 새 컬럼 추가**

```sql
ALTER TABLE orders
    ADD COLUMN user_id BIGINT;

UPDATE orders o
    JOIN users u ON o.user_email = u.email
    SET o.user_id = u.id;

ALTER TABLE orders
    MODIFY user_id BIGINT NOT NULL,
    ADD FOREIGN KEY (user_id) REFERENCES users(id);
```

`UPDATE`로 기존 레코드를 채운 뒤 NOT NULL 제약을 건다. 데이터 양에 따라 이 UPDATE가 시간이 걸릴 수 있다. 수백만 건이라면 배치로 나눠서 처리한다.

```sql
-- 배치 UPDATE (1만 건씩)
UPDATE orders o
    JOIN users u ON o.user_email = u.email
    SET o.user_id = u.id
WHERE o.user_id IS NULL
LIMIT 10000;
-- 위 쿼리를 user_id IS NULL이 없을 때까지 반복
```

**3단계: 애플리케이션 코드 전환**

FK를 `user_email` 대신 `user_id`로 쓰도록 애플리케이션 코드를 수정하고 배포한다. 이 시점에서도 두 컬럼이 모두 있으므로 롤백이 가능하다.

**4단계: 기존 FK 컬럼 제거 및 PK 교체**

모든 서비스가 새 컬럼을 사용하는 것을 확인한 뒤 정리한다.

```sql
-- 기존 FK 제거
ALTER TABLE orders
    DROP FOREIGN KEY fk_orders_user_email,
    DROP COLUMN user_email;

-- users 테이블의 PK 교체
ALTER TABLE users
    DROP PRIMARY KEY,
    MODIFY id BIGINT NOT NULL AUTO_INCREMENT,
    ADD PRIMARY KEY (id),
    MODIFY email VARCHAR(254) NOT NULL,
    ADD UNIQUE INDEX uq_email (email);
```

MySQL에서 `ALTER TABLE`로 PK를 바꾸면 테이블 전체를 재작성한다. 대용량 테이블이라면 `pt-online-schema-change`나 `gh-ost` 같은 무중단 DDL 도구를 써야 한다.

```bash
# Percona Toolkit 사용 예
pt-online-schema-change \
    --alter "DROP PRIMARY KEY, ADD PRIMARY KEY (id), ADD UNIQUE INDEX uq_email (email)" \
    --execute \
    D=mydb,t=users
```

## 대리키만으로는 관계를 파악할 수 없는 문제

대리키의 가장 큰 단점은 값 자체에 의미가 없다는 점이다. `order_id = 4827` 같은 값만 보면 어떤 주문인지 알 수 없다. 자연키였다면 `order_date + customer_code` 조합에서 맥락이 보인다.

이 문제는 주로 두 곳에서 나타난다.

### 디버깅과 운영

로그에 `user_id=3401, order_id=8821`이 찍혀도 해당 레코드를 조회하기 전까지 무엇인지 알 수 없다. 장애 상황에서 로그만 보고 원인을 파악하기 어렵다.

```typescript
// 로그에 의미 있는 식별자를 함께 남기는 방식
logger.error('결제 처리 실패', {
    userId: user.id,
    userEmail: user.email,
    orderId: order.id,
    orderNo: order.orderNo,
});
```

`orderId`(대리키)와 `orderNo`(인간이 읽을 수 있는 자연 식별자)를 함께 로깅한다. `order_no`는 도메인에서 의미 있는 주문번호(`2024-08-001234` 같은 형태)로, DB PK와 별도로 관리한다.

```sql
CREATE TABLE orders (
    id         BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_no   VARCHAR(20) NOT NULL UNIQUE, -- 사람이 읽는 주문번호
    user_id    BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 데이터 분석과 리포팅

분석 쿼리에서 대리키만으로는 관계를 따라가기 어렵다. 조인을 여러 번 써야 한다.

```sql
-- 대리키만 있을 때의 분석 쿼리
SELECT u.email, COUNT(o.id) AS order_count
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.created_at >= '2024-01-01'
GROUP BY u.id, u.email;
```

분석 환경에서는 조인 비용이 문제가 되는 경우가 있다. 대용량 테이블을 집계할 때 조인이 전체 스캔을 유발하면 오래 걸린다.

실무에서는 두 가지 방향으로 대응한다.

**자연 식별자를 별도 컬럼으로 두기**

```sql
-- 분석에 자주 쓰이는 식별 정보를 비정규화
CREATE TABLE orders (
    id          BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    user_email  VARCHAR(254) NOT NULL, -- 분석 편의를 위해 비정규화
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

정규화 관점에서는 `user_email`을 `orders`에 두는 것이 맞지 않지만, 분석 쿼리에서 `users` 테이블 조인 없이 직접 필터링할 수 있다. `user_email`이 바뀌면 `orders`의 값은 과거 시점의 이메일을 유지한다. 이것이 문제인지 아닌지는 도메인에 따라 다르다. 주문 생성 당시의 이메일을 보존해야 하는 경우라면 오히려 맞다.

**분석 전용 뷰나 별도 데이터 마트 구성**

트랜잭션 DB에서는 정규화를 유지하고, 분석 쿼리는 별도로 집계된 데이터를 쓴다. CDC나 배치로 분석용 테이블에 비정규화된 데이터를 올린다. 운영 DB의 조인 부담을 없애면서 분석 편의성도 확보한다.

### 외부 API 응답에서의 문제

대리키만 응답으로 내려주면 클라이언트가 해당 리소스를 추적하거나 디버깅하기 어렵다.

```json
// 대리키만 있으면 클라이언트 측 로그가 의미 없음
{
    "orderId": 8821,
    "status": "FAILED"
}
```

```json
// 의미 있는 식별자를 함께 내려줌
{
    "orderId": 8821,
    "orderNo": "2024-08-001234",
    "status": "FAILED"
}
```

`orderNo` 같은 사람이 읽을 수 있는 식별자를 API 응답에 함께 포함하면 클라이언트 측에서 고객 응대나 디버깅을 할 때 DB 조회 없이도 맥락을 파악할 수 있다.
