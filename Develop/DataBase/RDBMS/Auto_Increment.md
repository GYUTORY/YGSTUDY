---
title: AUTO_INCREMENT
tags: [MySQL, AUTO_INCREMENT, InnoDB, innodb_autoinc_lock_mode, PostgreSQL, SEQUENCE, JPA, IDENTITY, bulk-insert, replication]
updated: 2026-07-29
---

# AUTO_INCREMENT

MySQL InnoDB에서 AUTO_INCREMENT 카운터는 테이블 메타데이터에 영구 저장되지 않는다. MySQL 8.0 이전에는 서버가 시작될 때 `SELECT MAX(id) + 1`을 실행해서 메모리에 올렸다. 서버 재시작 전에 id 1000을 할당받은 행이 롤백됐다면, 재시작 후 카운터는 현재 테이블 최대값 기준으로 재계산되어 1000이 재사용될 수 있었다.

8.0부터는 카운터 변경을 redo log에 기록하기 때문에 재시작 후에도 카운터가 유지된다. 롤백된 값이 재사용되는 문제도 사라졌다.

## innodb_autoinc_lock_mode

INSERT 시 AUTO_INCREMENT 값을 할당하는 방식을 제어한다. 0, 1, 2 세 가지 모드가 있다.

### 모드 0 (traditional)

INSERT마다 테이블 수준의 `AUTO-INC` 락을 획득한다. 트랜잭션 A가 INSERT를 실행하는 동안 트랜잭션 B의 INSERT가 대기한다. INSERT가 완료되면 락이 해제된다.

동시성이 가장 낮다. statement-based replication에서 마스터와 슬레이브가 같은 순서로 값을 받기 때문에 복제 일관성은 보장된다.

### 모드 1 (consecutive, MySQL 5.x 기본값)

행 수가 미리 알려진 simple INSERT(`INSERT INTO t VALUES (...)`, `INSERT INTO t VALUES (...), (...)`)는 뮤텍스만 사용해서 빠르게 값을 할당한다. 락이 불필요할 만큼 짧다.

행 수를 실행 전에 알 수 없는 bulk INSERT(`INSERT ... SELECT`, `LOAD DATA`)는 모드 0처럼 `AUTO-INC` 테이블 락을 사용한다. 이 경우 bulk INSERT가 끝날 때까지 다른 INSERT가 대기한다.

"consecutive"라는 이름대로 한 문장에서 INSERT된 행들이 연속된 id를 받는 것이 보장된다. statement-based replication에서 안전하게 동작한다.

### 모드 2 (interleaved, MySQL 8.0 기본값)

모든 INSERT에서 뮤텍스만 사용한다. `AUTO-INC` 테이블 락을 사용하지 않아 동시 처리량이 가장 높다.

bulk INSERT 실행 중 다른 INSERT가 끼어들면 값이 섞인다. 예를 들어 트랜잭션 A의 `INSERT ... SELECT`가 1000~1050을 예약했더라도, 트랜잭션 B가 중간에 끼어들어 1025를 가져갈 수 있다. statement-based replication에서는 마스터와 슬레이브의 값이 달라지므로 row-based replication과 같이 써야 한다.

MySQL 8.0에서 기본값이 1에서 2로 바뀌면서 바이너리 로그 포맷도 STATEMENT에서 ROW로 바뀐 이유가 여기 있다.

```sql
-- 현재 모드 확인
SELECT @@innodb_autoinc_lock_mode;

-- 설정 변경 (my.cnf)
-- innodb_autoinc_lock_mode = 2
```

statement-based replication을 유지해야 하는 환경에서 8.0으로 마이그레이션하면 이 조합을 확인해야 한다. row-based replication 없이 모드 2를 쓰면 복제가 깨진다.

## 갭이 생기는 이유

AUTO_INCREMENT 값은 트랜잭션 결과와 무관하게 소비된다. 트랜잭션 A가 INSERT를 실행해서 id 1000을 할당받은 뒤 롤백해도 카운터는 1001로 남는다.

**롤백**

가장 흔한 갭 원인이다.

```sql
BEGIN;
INSERT INTO orders (user_id, total) VALUES (1, 5000); -- id 1000 할당
ROLLBACK;
-- 다음 INSERT는 id 1001을 받는다
INSERT INTO orders (user_id, total) VALUES (2, 3000); -- id 1001
```

**INSERT IGNORE와 REPLACE INTO**

`INSERT IGNORE`는 중복 키 충돌 시 행을 삽입하지 않지만 카운터는 올라간다.

```sql
-- id가 unique인 테이블에서
INSERT IGNORE INTO tags (id, name) VALUES (5, 'mysql'); -- id 5가 이미 있으면 스킵
-- 카운터는 이미 증가
INSERT INTO tags (name) VALUES ('redis'); -- 기대와 다른 id를 받을 수 있다
```

`REPLACE INTO`는 내부적으로 충돌 시 DELETE + INSERT를 실행한다. 새 INSERT에서 새 id를 할당한다.

**Bulk INSERT에서의 예약**

모드 1에서 `INSERT ... SELECT`는 결과 행 수를 미리 알 수 없어 테이블 락을 쓰지만, 일부 구현에서 예상 행 수를 초과 예약하는 경우가 있다. 실제 삽입된 행보다 카운터가 더 올라갈 수 있다.

갭이 없어야 한다는 요구사항은 AUTO_INCREMENT로 충족하기 어렵다. 주문번호처럼 비즈니스적으로 연속 번호가 필요하면 별도 채번 테이블로 관리해야 한다.

## DELETE vs TRUNCATE 후 카운터 차이

`DELETE FROM t`는 행만 지운다. AUTO_INCREMENT 카운터는 그대로다. 테이블을 비운 뒤 다시 INSERT하면 삭제 전 마지막 값의 다음부터 이어진다.

```sql
INSERT INTO t (name) VALUES ('a'), ('b'), ('c'); -- id 1, 2, 3
DELETE FROM t;
INSERT INTO t (name) VALUES ('d'); -- id 4, not 1
```

`TRUNCATE TABLE t`는 테이블 자체를 재생성하기 때문에 카운터가 1로 리셋된다. DDL이라 트랜잭션으로 롤백할 수 없다.

```sql
INSERT INTO t (name) VALUES ('a'), ('b'), ('c'); -- id 1, 2, 3
TRUNCATE TABLE t;
INSERT INTO t (name) VALUES ('d'); -- id 1
```

외래 키 제약이 있으면 TRUNCATE가 실패한다. 자식 테이블이 부모 테이블의 행을 참조하고 있기 때문이다.

```sql
-- 외래 키가 있을 때 TRUNCATE 순서
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE order_items;
TRUNCATE TABLE orders;
SET FOREIGN_KEY_CHECKS = 1;
```

카운터만 조정하고 싶을 때는 `ALTER TABLE`을 쓴다.

```sql
ALTER TABLE t AUTO_INCREMENT = 1;
```

현재 MAX(id)보다 낮은 값을 지정하면 MySQL이 무시하고 MAX(id) + 1로 맞춘다. 데이터를 지우지 않는 한 카운터를 내릴 수 없다.

## INT / BIGINT 오버플로우

INT SIGNED 최대값은 약 21억(2,147,483,647), INT UNSIGNED는 약 43억(4,294,967,295)이다.

한계에 도달하면 다음 INSERT에서 카운터가 최대값에서 멈춰 같은 값을 계속 시도한다.

```
ERROR 1062 (23000): Duplicate entry '2147483647' for key 'PRIMARY'
```

이 에러가 나오면 서비스가 중단된다. 미리 여유를 확인해야 한다.

```sql
SELECT
    TABLE_NAME,
    AUTO_INCREMENT AS current_counter,
    (
        SELECT MAX(id) FROM your_table
    ) AS current_max_id,
    ROUND(
        (POW(2, 31) - 1 - AUTO_INCREMENT) / AUTO_INCREMENT * 100,
        2
    ) AS remaining_pct_signed
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_db'
  AND TABLE_NAME = 'your_table';
```

BIGINT로 변환하는 방법은 단순하다.

```sql
ALTER TABLE t MODIFY id BIGINT NOT NULL AUTO_INCREMENT;
```

행이 많으면 이 작업이 테이블 재작성을 유발해 오래 걸린다. 운영 중인 서비스라면 `pt-online-schema-change`나 `gh-ost`를 써서 무중단으로 진행한다.

```bash
pt-online-schema-change \
    --alter "MODIFY id BIGINT NOT NULL AUTO_INCREMENT" \
    --execute \
    D=mydb,t=your_table
```

BIGINT UNSIGNED 최대값은 약 1844경(18,446,744,073,709,551,615)이라 사실상 한계에 부딪힐 일은 없다. 초당 100만 건씩 INSERT해도 약 58만 년이 걸린다.

INT를 쓸 때는 처음부터 UNSIGNED로 선언하는 습관이 낫다. 음수 id는 의미가 없고 UNSIGNED로 하면 한계가 두 배로 늘어난다.

```sql
CREATE TABLE events (
    id   INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);
```

## 마스터-마스터 복제에서의 충돌 방지

마스터 두 대가 동시에 쓰기를 받으면 양쪽에서 같은 id를 생성할 수 있다. 이를 막기 위해 두 파라미터를 사용한다.

`auto_increment_increment`는 증가 단위, `auto_increment_offset`은 시작 오프셋이다.

```ini
# 마스터 1 (my.cnf)
auto_increment_increment = 2
auto_increment_offset    = 1
# 생성되는 id: 1, 3, 5, 7, ...

# 마스터 2 (my.cnf)
auto_increment_increment = 2
auto_increment_offset    = 2
# 생성되는 id: 2, 4, 6, 8, ...
```

마스터가 3대면 increment를 3으로, offset을 각각 1, 2, 3으로 설정한다.

```ini
# 마스터 1
auto_increment_increment = 3
auto_increment_offset    = 1

# 마스터 2
auto_increment_increment = 3
auto_increment_offset    = 2

# 마스터 3
auto_increment_increment = 3
auto_increment_offset    = 3
```

이 설정의 단점이 있다. 마스터를 추가하거나 제거할 때 increment 값을 바꾸면 기존 id 범위와 충돌할 수 있다. 마스터 2대에서 increment=2로 운영하다 3대로 늘릴 때 increment를 3으로 바꾸면, 기존에 생성된 홀수/짝수 id와 새 오프셋이 겹치는 경우가 생긴다.

실무에서는 마스터 대수가 고정된 경우에 잘 맞는다. 동적으로 확장해야 한다면 UUID나 Snowflake 같은 분산 id 생성기를 쓰는 것이 낫다.

```sql
-- 현재 설정 확인
SELECT @@auto_increment_increment, @@auto_increment_offset;

-- 세션 레벨 변경도 가능 (테스트용)
SET auto_increment_increment = 2;
SET auto_increment_offset = 1;
```

## PostgreSQL SERIAL / SEQUENCE

PostgreSQL에는 AUTO_INCREMENT가 없다. SEQUENCE 객체를 사용한다.

```sql
-- SERIAL은 아래와 동일하다
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    -- ...
);

-- 내부적으로 이렇게 처리된다
CREATE SEQUENCE orders_id_seq;
CREATE TABLE orders (
    id INTEGER NOT NULL DEFAULT nextval('orders_id_seq') PRIMARY KEY
);
ALTER SEQUENCE orders_id_seq OWNED BY orders.id;
```

PostgreSQL 10부터는 `IDENTITY`가 표준 문법으로 추가됐다.

```sql
CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    total NUMERIC(12, 2) NOT NULL
);

-- GENERATED BY DEFAULT는 직접 값을 INSERT할 수 있다
CREATE TABLE orders (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
);
```

MySQL AUTO_INCREMENT와 다른 점이 몇 가지 있다.

**트랜잭션 밖에서 동작한다**

SEQUENCE는 트랜잭션 범위를 벗어난다. `nextval()`을 호출하면 트랜잭션이 롤백되더라도 그 값은 소비된 것으로 처리된다. 갭이 생기는 것은 MySQL과 같다.

**CACHE 설정으로 성능 조절이 가능하다**

```sql
-- CACHE를 크게 잡으면 nextval 호출 횟수를 줄일 수 있다
ALTER SEQUENCE orders_id_seq CACHE 100;
```

캐시 크기를 키우면 성능이 올라가지만, 서버 재시작 시 캐시에 남은 값이 사라지면서 갭이 커진다. 캐시 100이면 재시작마다 최대 100개의 id가 날아갈 수 있다.

**여러 테이블에서 공유할 수 있다**

MySQL AUTO_INCREMENT는 테이블에 종속되지만 PostgreSQL SEQUENCE는 독립 객체다. 여러 테이블에서 같은 SEQUENCE를 공유해서 전역 유일 id를 만들 수 있다.

```sql
CREATE SEQUENCE global_id_seq;

CREATE TABLE events (
    id BIGINT DEFAULT nextval('global_id_seq') PRIMARY KEY
);

CREATE TABLE logs (
    id BIGINT DEFAULT nextval('global_id_seq') PRIMARY KEY
);
```

**시퀀스 값 직접 조작**

```sql
-- 다음 값 조회 (소비됨)
SELECT nextval('orders_id_seq');

-- 현재 값 조회 (이 세션에서 nextval 호출 후에만 유효)
SELECT currval('orders_id_seq');

-- 이 세션에서 마지막으로 생성된 시퀀스 값
SELECT lastval();

-- 강제 설정
SELECT setval('orders_id_seq', 10000);
SELECT setval('orders_id_seq', 10000, false); -- 다음 nextval이 10000을 반환
```

MySQL의 `LAST_INSERT_ID()`와 대응하는 것이 `lastval()`이다.

## JPA IDENTITY 전략이 배치 INSERT를 막는 이유

`@GeneratedValue(strategy = GenerationType.IDENTITY)`는 데이터베이스의 AUTO_INCREMENT에 id 생성을 맡긴다.

```java
@Entity
public class Order {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
}
```

Hibernate는 기본적으로 쓰기 지연(write-behind)을 통해 여러 INSERT를 배치로 묶는다. 이 배치가 동작하려면 INSERT 전에 각 엔티티의 id를 알아야 한다. 영속성 컨텍스트가 엔티티를 id를 키로 관리하기 때문이다.

IDENTITY 전략에서는 실제 INSERT가 완료된 후에야 데이터베이스가 id를 반환한다(`LAST_INSERT_ID()`). INSERT 전에 id를 알 수 없으므로, Hibernate는 `entityManager.persist()` 시점에 즉시 INSERT를 실행한다. 배치로 묶을 수 없다.

```java
// application.yml
spring:
  jpa:
    properties:
      hibernate.jdbc.batch_size: 50
      hibernate.order_inserts: true

// 이 설정이 있어도 IDENTITY 전략이면 배치가 동작하지 않는다
for (Order order : orders) {
    entityManager.persist(order); // 즉시 INSERT 실행, 배치 아님
}
```

SEQUENCE 전략은 이 문제가 없다. INSERT 전에 `nextval()`로 id를 미리 받아올 수 있어 Hibernate가 배치를 구성할 수 있다.

```java
@Entity
@SequenceGenerator(
    name = "order_seq",
    sequenceName = "order_sequence",
    allocationSize = 50
)
public class Order {
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "order_seq")
    private Long id;
}

// allocationSize = 50이면 50번의 persist()마다 nextval 1번
for (Order order : orders) {
    entityManager.persist(order); // INSERT가 묶인다
}
// flush 시점에 50개 INSERT를 배치로 실행
```

MySQL에서 SEQUENCE 전략을 쓰면 Hibernate가 `hibernate_sequence` 에뮬레이션 테이블을 만들어 잠금 기반으로 처리한다. 잠금 경합이 발생해서 MySQL에서는 IDENTITY 전략이 현실적이다.

MySQL에서 대량 INSERT 성능이 중요한 경우 Hibernate 배치를 포기하고 직접 JDBC 배치를 쓰는 것이 실용적이다.

```java
@Repository
public class OrderBatchRepository {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    public void batchInsert(List<Order> orders) {
        jdbcTemplate.batchUpdate(
            "INSERT INTO orders (user_id, total, created_at) VALUES (?, ?, ?)",
            orders,
            500,
            (ps, order) -> {
                ps.setLong(1, order.getUserId());
                ps.setBigDecimal(2, order.getTotal());
                ps.setTimestamp(3, Timestamp.valueOf(order.getCreatedAt()));
            }
        );
    }
}
```

`JdbcTemplate.batchUpdate()`는 IDENTITY 전략의 제약을 받지 않는다. INSERT 후 생성된 id가 필요하면 `KeyHolder`를 사용한다.

```java
KeyHolder keyHolder = new GeneratedKeyHolder();
jdbcTemplate.update(
    con -> {
        PreparedStatement ps = con.prepareStatement(
            "INSERT INTO orders (user_id, total) VALUES (?, ?)",
            Statement.RETURN_GENERATED_KEYS
        );
        ps.setLong(1, userId);
        ps.setBigDecimal(2, total);
        return ps;
    },
    keyHolder
);
long generatedId = keyHolder.getKey().longValue();
```

Spring Batch를 쓰는 경우라면 `JdbcBatchItemWriter`가 내부적으로 배치 처리를 한다. Hibernate를 통하지 않아 IDENTITY 전략의 영향을 받지 않는다.
