---
title: MySQL vs PostgreSQL 실무 비교
tags:
  - RDBMS
  - MySQL
  - PostgreSQL
  - InnoDB
  - MVCC
  - 트랜잭션
  - 인덱스
  - 복제
updated: 2026-05-22
---

# MySQL vs PostgreSQL 실무 비교

두 DB를 5년 이상 다루면서 깨달은 것은, 단순한 기능 비교표로는 선택을 못 한다는 점이다. 같은 SQL을 던져도 락이 잡히는 범위가 다르고, 같은 인덱스를 쓰는데도 옵티마이저가 다른 판단을 한다. 이 문서는 양쪽을 운영하면서 부딪힌 차이를 실제 쿼리와 함께 정리한 것이다.

---

## 1. 스토리지 엔진과 MVCC 구현 차이

MySQL은 스토리지 엔진을 갈아끼울 수 있는 구조다. InnoDB가 사실상 표준이지만, MyISAM, Memory, Archive 같은 엔진이 따로 존재한다. 같은 테이블의 다른 인덱스도 엔진이 다를 수 있다는 뜻이 아니라, 테이블 단위로 엔진을 고른다.

PostgreSQL은 그런 구조가 아니다. 스토리지 레이어가 하나로 통합되어 있고, MVCC가 엔진의 일부가 아니라 PostgreSQL 그 자체다. 8.x 이후로 pluggable storage가 도입되긴 했지만, 실무에서 heap 외에 다른 걸 쓰는 경우는 거의 없다.

### InnoDB의 MVCC

InnoDB는 row의 옛 버전을 언두 로그(undo log)에 저장한다. 현재 row는 그대로 두고, 갱신 전 데이터를 언두 영역에 백업한 뒤 새 값으로 덮어쓴다. 트랜잭션이 옛 스냅샷을 봐야 하면 언두 체인을 거꾸로 따라가서 복원한다.

이 구조의 장점은 테이블 자체가 깔끔하게 유지된다는 점이다. 죽은 row가 쌓이지 않는다. 단점은 언두 로그가 계속 커진다는 점이다. 긴 트랜잭션이 하나라도 살아 있으면 그 트랜잭션이 봐야 할 옛 버전을 다 보존해야 하므로 언두 영역이 폭발한다.

### PostgreSQL의 MVCC

PostgreSQL은 다르다. UPDATE를 하면 새 row를 추가하고 옛 row에 `xmax`를 찍어서 "이 트랜잭션 ID에서 죽었다"라고 표시한다. DELETE도 마찬가지로 row를 지우지 않고 `xmax`만 찍는다. 죽은 row는 VACUUM이 청소하기 전까지 그대로 남는다.

장점은 롤백이 거의 무료라는 점이다. 새로 추가한 row의 `xmin`이 무효 처리되면 끝이다. 단점은 테이블이 부풀어 오른다(bloat). VACUUM이 제대로 안 돌면 100만 row 테이블이 디스크 상으로 1000만 row만큼의 공간을 차지하는 사태가 벌어진다.

```sql
-- PostgreSQL에서 bloat 확인
SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    round(n_dead_tup::numeric / nullif(n_live_tup, 0) * 100, 2) AS dead_pct,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_pct DESC NULLS LAST
LIMIT 20;
```

실무에서 한 번 겪은 사례: 24시간 돌아가는 배치가 트랜잭션을 열어 둔 채로 새벽에 죽었다. autovacuum이 그 트랜잭션 이전의 dead row를 못 지워서 며칠 만에 테이블이 5배로 부풀어 올랐다. 쿼리 응답이 점점 느려졌고, 원인을 잡는 데 한참 걸렸다. `pg_stat_activity`에서 `xact_start`가 오래된 세션을 주기적으로 모니터링하는 습관을 들여야 한다.

---

## 2. 트랜잭션 격리 수준의 실제 동작

ANSI SQL 표준은 격리 수준 이름만 정의하고 구현은 DB에 맡겼다. 그래서 같은 `REPEATABLE READ`도 MySQL과 PostgreSQL이 다르게 동작한다.

### MySQL InnoDB의 REPEATABLE READ

InnoDB의 기본 격리 수준은 REPEATABLE READ다. 표준에 따르면 이 수준에서는 phantom read가 발생해야 하지만, InnoDB는 갭락(gap lock)과 넥스트 키 락(next-key lock)으로 phantom을 막는다.

```sql
-- 세션 1
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
SELECT * FROM orders WHERE user_id BETWEEN 100 AND 200 FOR UPDATE;
-- 100~200 범위에 갭락이 걸린다

-- 세션 2
INSERT INTO orders (user_id, amount) VALUES (150, 5000);
-- 블로킹된다. 세션 1이 끝날 때까지 대기
```

이 갭락이 데드락의 주범이다. 인덱스가 없는 컬럼으로 UPDATE를 치면 갭락 범위가 넓어진다. 두 트랜잭션이 서로 다른 갭에 락을 잡고 상대 갭에 INSERT를 시도하면 데드락이 터진다.

```sql
-- MySQL 데드락 추적
SHOW ENGINE INNODB STATUS\G
-- LATEST DETECTED DEADLOCK 섹션을 보면 어떤 락이 충돌했는지 나온다
```

### PostgreSQL의 REPEATABLE READ

PostgreSQL의 REPEATABLE READ는 Snapshot Isolation이다. 트랜잭션 시작 시점의 스냅샷을 그대로 본다. phantom read가 발생할 가능성이 있지만, 갭락을 쓰지 않으므로 동시성이 훨씬 높다.

```sql
-- 세션 1
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT * FROM orders WHERE user_id BETWEEN 100 AND 200;
-- 락이 안 잡힌다

-- 세션 2
INSERT INTO orders (user_id, amount) VALUES (150, 5000);
COMMIT;
-- 즉시 성공
```

대신 PostgreSQL의 REPEATABLE READ에서 같은 row를 동시에 UPDATE하면 한쪽이 `could not serialize access due to concurrent update` 에러로 죽는다. 애플리케이션에서 재시도 로직을 넣어야 한다.

```python
def update_with_retry(conn, max_retries=3):
    for attempt in range(max_retries):
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
                    cur.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
                    cur.execute("COMMIT")
            return
        except psycopg2.errors.SerializationFailure:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.1 * (2 ** attempt))
```

### SERIALIZABLE

PostgreSQL의 SERIALIZABLE은 SSI(Serializable Snapshot Isolation)로 구현됐다. 실제로 락을 더 거는 게 아니라 트랜잭션 간 의존성을 추적해서 직렬화 가능성이 깨지면 한쪽을 abort 시킨다. MySQL의 SERIALIZABLE은 모든 SELECT에 공유 락을 거는 단순한 방식이라 성능이 훨씬 떨어진다.

---

## 3. 인덱스 구조

### B-Tree

양쪽 다 기본은 B-Tree다. 하지만 InnoDB의 클러스터드 인덱스와 PostgreSQL의 힙 기반 인덱스 구조가 다르다.

InnoDB는 primary key가 곧 클러스터드 인덱스다. 테이블 row가 PK 순서로 디스크에 저장된다. secondary index는 leaf에 PK 값을 들고 있다. 그래서 secondary index로 찾으면 PK 인덱스를 한 번 더 타야 row를 가져온다.

PostgreSQL은 모든 인덱스가 secondary다. 테이블은 힙(heap)에 무순서로 쌓이고, 인덱스는 leaf에 row의 물리적 위치(ctid)를 들고 있다. 그래서 PK 조회와 다른 인덱스 조회의 비용 차이가 거의 없다.

이 차이가 만드는 실무 효과: InnoDB에서는 PK 선택이 성능에 큰 영향을 미친다. UUID를 PK로 쓰면 INSERT가 무작위 위치에 일어나면서 페이지 분할이 자주 일어난다. PostgreSQL은 UUID PK를 써도 힙은 append-only로 쌓이므로 그런 페널티가 작다.

```sql
-- InnoDB: PK 정렬을 의도한 PK 선택
CREATE TABLE events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    created_at TIMESTAMP,
    INDEX idx_user_created (user_id, created_at)
) ENGINE=InnoDB;

-- PostgreSQL: UUID PK도 부담이 작다
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT,
    created_at TIMESTAMP,
    user_id_created_idx ON events (user_id, created_at)
);
```

### GIN과 GiST

PostgreSQL의 특기 영역이다. MySQL에는 없는 인덱스 타입이다.

GIN(Generalized Inverted Index)은 한 row가 여러 값을 가진 경우에 강하다. 배열, JSONB, full-text search 벡터에 쓴다. JSONB의 특정 키를 검색하는 쿼리는 GIN 없이는 거의 못 쓴다.

```sql
-- JSONB GIN 인덱스
CREATE INDEX idx_metadata_gin ON products USING GIN (metadata);

-- 이 쿼리가 인덱스를 탄다
SELECT * FROM products WHERE metadata @> '{"category": "electronics"}';
```

GiST(Generalized Search Tree)는 기하 데이터, 범위 타입, full-text에 쓴다. PostGIS의 공간 인덱스가 GiST 위에 올라가 있다.

### Hash 인덱스

PostgreSQL은 hash 인덱스를 정식 지원한다. 10 버전부터 WAL에 기록되어 복제도 된다. 단, 등호 비교만 가능하고 범위 검색은 못 한다. B-Tree 대비 압도적으로 빠른 경우가 별로 없어서 잘 안 쓴다.

MySQL InnoDB는 명시적인 hash 인덱스가 없다. 대신 adaptive hash index라는 내부 메커니즘이 있어서 자주 접근하는 B-Tree 페이지를 hash 형태로 캐시한다. 사용자가 직접 만드는 게 아니라 InnoDB가 알아서 한다.

### BRIN

대용량 시계열 데이터에서 빛을 발하는 인덱스다. PostgreSQL만 지원한다. B-Tree가 모든 row를 인덱싱하는 반면, BRIN은 페이지 범위(block range)별로 min/max만 저장한다. 인덱스 크기가 1/100 수준이다.

물리적 순서와 논리적 순서가 일치할 때만 효과가 있다. created_at으로 정렬되어 들어오는 로그 테이블에 BRIN을 걸면 B-Tree 대비 인덱스 크기는 작고 성능은 비슷하다.

```sql
CREATE INDEX idx_logs_created_brin ON logs USING BRIN (created_at) WITH (pages_per_range = 32);
```

---

## 4. JSON과 JSONB

MySQL 5.7부터 JSON 타입이 들어왔다. 내부적으로 바이너리 포맷으로 저장하고 부분 업데이트도 지원한다. PostgreSQL은 JSON과 JSONB 두 타입이 있다. JSON은 텍스트 그대로 저장하고, JSONB는 바이너리 파싱된 형태다.

실무에서 PostgreSQL은 거의 항상 JSONB를 쓴다. JSON은 입력 그대로 보존해야 하는 경우(공백, 키 순서)에만 의미가 있다.

### 인덱싱 차이

MySQL은 JSON 컬럼 자체에는 인덱스를 못 건다. 대신 가상 컬럼(generated column)을 만들어서 인덱싱한다.

```sql
-- MySQL
CREATE TABLE products (
    id BIGINT PRIMARY KEY,
    data JSON,
    category VARCHAR(50) AS (JSON_UNQUOTE(JSON_EXTRACT(data, '$.category'))) STORED,
    INDEX idx_category (category)
);
```

PostgreSQL은 JSONB에 GIN 인덱스를 바로 걸 수 있다. 표현식 인덱스도 가능하다.

```sql
-- PostgreSQL
CREATE INDEX idx_data_gin ON products USING GIN (data);
CREATE INDEX idx_category ON products ((data->>'category'));
```

### 쿼리 문법

```sql
-- MySQL
SELECT * FROM products WHERE JSON_EXTRACT(data, '$.tags[0]') = 'sale';
SELECT * FROM products WHERE data->'$.category' = '"electronics"';

-- PostgreSQL
SELECT * FROM products WHERE data->'tags'->>0 = 'sale';
SELECT * FROM products WHERE data->>'category' = 'electronics';
SELECT * FROM products WHERE data @> '{"category": "electronics"}';
```

PostgreSQL의 `@>` 연산자는 containment 검색인데, GIN 인덱스를 직접 활용한다. 중첩된 JSON 구조에서 특정 키-값을 찾는 쿼리는 PostgreSQL이 압도적으로 편하다.

MySQL의 부분 업데이트는 JSON_SET, JSON_INSERT, JSON_REPLACE를 쓰는데 문법이 번잡하다. PostgreSQL은 `jsonb_set` 함수를 쓰는데, 둘 다 깊이 중첩된 구조를 다루기는 불편하다.

---

## 5. 복제 방식

### MySQL binlog 기반 복제

MySQL은 binlog(binary log)를 마스터에서 슬레이브로 보내는 방식이다. binlog 포맷은 STATEMENT, ROW, MIXED 세 가지다.

STATEMENT는 SQL 문장을 그대로 보낸다. 가벼우나 `NOW()`, `RAND()` 같은 비결정적 함수에서 결과가 갈린다. ROW는 변경된 row 데이터를 통째로 보낸다. 안전하지만 BLOB 컬럼이 있으면 binlog 크기가 폭발한다. MIXED는 가능하면 STATEMENT, 위험하면 ROW로 자동 전환한다.

실무에서는 ROW를 기본으로 쓴다. STATEMENT의 결정성 문제로 마스터-슬레이브 데이터가 갈리는 사고를 한 번 겪으면 다시는 STATEMENT를 안 쓴다.

```sql
-- 복제 지연 확인
SHOW SLAVE STATUS\G
-- Seconds_Behind_Master 값을 본다. 단, 이 값이 0이라고 정합성이 보장된 건 아니다
```

### PostgreSQL WAL 기반 복제

PostgreSQL은 WAL(Write-Ahead Log)을 그대로 슬레이브로 스트리밍한다. WAL은 물리적 변경 로그라서 마스터와 슬레이브의 데이터 페이지가 비트 단위로 같아진다.

물리 복제는 결정성 문제가 원천적으로 없다. 대신 마스터와 슬레이브의 PostgreSQL 버전이 같아야 하고, 슬레이브에서 스키마가 다르거나 인덱스를 추가하는 게 불가능하다.

10 버전부터 논리 복제(logical replication)도 정식 지원한다. publish/subscribe 모델로 테이블 단위 복제가 가능하다. 슬레이브에 다른 인덱스를 추가하거나, 일부 테이블만 복제받는 시나리오에 쓴다.

```sql
-- PostgreSQL 복제 지연 확인 (마스터에서)
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- 슬레이브에서
SELECT
    now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

### 복제 토폴로지의 차이

MySQL은 마스터-마스터 복제, 멀티소스 복제 같은 토폴로지가 자유롭다. 다만 충돌 해결은 운영자 책임이다.

PostgreSQL은 기본적으로 단방향이다. 양방향 복제는 BDR 같은 서드파티 솔루션이 있지만 OSS 코어에는 없다. 대신 단방향 복제의 안정성은 매우 높다.

---

## 6. 시퀀스 vs AUTO_INCREMENT

MySQL의 `AUTO_INCREMENT`는 테이블에 종속된다. 컬럼 하나에만 붙일 수 있고, 다른 테이블과 공유 못 한다. PostgreSQL의 SEQUENCE는 독립 객체다. 여러 테이블에서 같은 시퀀스를 nextval로 당겨 쓸 수 있다.

```sql
-- PostgreSQL
CREATE SEQUENCE global_id_seq START 1;
CREATE TABLE orders (id BIGINT DEFAULT nextval('global_id_seq'), ...);
CREATE TABLE invoices (id BIGINT DEFAULT nextval('global_id_seq'), ...);
-- 두 테이블이 같은 ID 공간을 공유
```

### 트랜잭션 롤백 시 동작

양쪽 다 시퀀스 값을 미리 발급해 두고, 트랜잭션이 롤백되어도 발급된 값은 복원하지 않는다. 즉, ID에 구멍이 생긴다.

이걸 못 받아들이고 "ID가 연속이어야 한다"라고 우기는 요구사항을 만나면 시퀀스를 못 쓴다. 그러면 트랜잭션 내에서 별도 카운터 테이블을 락 잡고 증가시키는 수밖에 없는데, 동시성이 박살난다. 차라리 시퀀스 + gapless를 요구하는 비즈니스 요건 자체를 다시 협상하는 게 낫다.

### identity 컬럼

PostgreSQL 10부터 표준 SQL의 IDENTITY 컬럼이 지원된다. 시퀀스를 명시적으로 만드는 대신 더 깔끔하게 쓸 수 있다.

```sql
CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ...
);
```

`GENERATED ALWAYS`는 사용자가 명시적으로 INSERT 값을 못 넣는다. `GENERATED BY DEFAULT`는 넣을 수 있다. 마이그레이션할 때는 BY DEFAULT가 편하다.

---

## 7. NULL 처리

NULL의 표준은 같은데 동작이 미묘하게 다른 부분이 있다.

### UNIQUE 인덱스와 NULL

MySQL: 한 테이블의 UNIQUE 컬럼에 NULL을 여러 개 넣을 수 있다.
PostgreSQL: 마찬가지로 NULL은 UNIQUE 제약을 위반하지 않는다.

15 버전부터 PostgreSQL은 `UNIQUE NULLS NOT DISTINCT` 옵션이 생겼다. NULL을 단일 값으로 취급해서 NULL 중복을 막을 수 있다.

```sql
-- PostgreSQL 15+
CREATE UNIQUE INDEX idx_email_unique ON users (email) NULLS NOT DISTINCT;
```

### NULL과 정렬

MySQL: ASC 정렬 시 NULL이 앞, DESC 정렬 시 NULL이 뒤.
PostgreSQL: ASC 정렬 시 NULL이 뒤, DESC 정렬 시 NULL이 앞. (반대)

`NULLS FIRST`, `NULLS LAST` 키워드로 양쪽 다 명시적으로 지정할 수 있는데, MySQL은 8.0에서야 지원하기 시작했다.

```sql
SELECT * FROM users ORDER BY last_login DESC NULLS LAST;
```

NULL 정렬 순서 차이로 페이지네이션 결과가 뒤바뀌는 버그를 한 번 겪었다. 마이그레이션 시 확인해야 할 항목이다.

---

## 8. 문자열과 타입 처리

### VARCHAR 길이

MySQL의 VARCHAR(n)에서 n은 문자 수다. 8.0 기준으로 utf8mb4 charset이면 byte로는 최대 65,532까지 들어간다.

PostgreSQL의 VARCHAR(n)은 문자 수다. n 제한이 없는 TEXT 타입을 쓸 수도 있다. 성능 차이가 거의 없어서 PostgreSQL에서는 그냥 TEXT를 쓰는 경우가 많다.

### 대소문자 구분

MySQL의 기본 collation은 대소문자 무시(case-insensitive)다. `WHERE name = 'JOHN'`이 'john'에도 매칭된다. 의도와 다른 동작이라 운영 중에 사고가 난다.

```sql
-- MySQL에서 대소문자 구분
SELECT * FROM users WHERE BINARY name = 'John';
-- 또는 컬럼 자체에 utf8mb4_bin collation 지정
```

PostgreSQL은 기본이 대소문자 구분이다. case-insensitive 검색이 필요하면 `citext` 확장을 쓰거나 `LOWER()` 인덱스를 건다.

```sql
-- PostgreSQL
CREATE EXTENSION citext;
CREATE TABLE users (email CITEXT UNIQUE);

-- 또는 표현식 인덱스
CREATE INDEX idx_users_email_lower ON users (LOWER(email));
SELECT * FROM users WHERE LOWER(email) = LOWER('John@Example.com');
```

### 빈 문자열과 NULL

오라클은 빈 문자열을 NULL로 취급하지만, MySQL과 PostgreSQL 모두 빈 문자열과 NULL은 다르다.

### 타임존

MySQL의 TIMESTAMP는 UTC로 저장되고 조회 시 세션 타임존으로 변환된다. DATETIME은 타임존 정보 없이 그대로 저장된다. 둘 다 미묘하게 다르게 동작해서 헷갈린다.

PostgreSQL의 `TIMESTAMP WITH TIME ZONE`(timestamptz)은 UTC로 저장하고 조회 시 세션 타임존으로 변환된다. `TIMESTAMP WITHOUT TIME ZONE`은 입력 그대로 저장한다.

실무 권장은 timestamptz를 기본으로 쓰는 것이다. 애플리케이션이 글로벌하면 거의 필수다.

```sql
-- PostgreSQL
SET TIME ZONE 'Asia/Seoul';
SELECT NOW(); -- 2026-05-22 14:30:00+09
SET TIME ZONE 'UTC';
SELECT NOW(); -- 2026-05-22 05:30:00+00
-- 같은 시점을 표시만 다르게 한다
```

---

## 9. 풀텍스트 검색

MySQL은 InnoDB에 내장된 FULLTEXT 인덱스가 있다. ngram parser 플러그인을 쓰면 한국어, 중국어, 일본어 검색이 가능하다.

```sql
-- MySQL
CREATE FULLTEXT INDEX ft_idx ON articles(title, body) WITH PARSER ngram;
SELECT * FROM articles WHERE MATCH(title, body) AGAINST('+검색어' IN BOOLEAN MODE);
```

PostgreSQL은 `tsvector`, `tsquery` 타입과 GIN 인덱스로 풀텍스트 검색을 한다. 영어/유럽어 검색은 강하지만, 한국어 검색은 별도 형태소 분석기가 필요하다. mecab-ko 같은 외부 확장을 붙여야 한다.

```sql
-- PostgreSQL
CREATE INDEX idx_articles_search ON articles USING GIN (to_tsvector('simple', title || ' ' || body));
SELECT * FROM articles WHERE to_tsvector('simple', title || ' ' || body) @@ to_tsquery('검색어');
```

한국어 환경이라면 양쪽 다 한계가 있다. 본격적인 풀텍스트가 필요하면 Elasticsearch나 Meilisearch 같은 별도 검색 엔진을 붙이는 게 답이다. RDBMS 내장 풀텍스트는 보조 검색 용도로 쓰는 것이 적당하다.

---

## 10. 파티셔닝

### MySQL 파티셔닝

MySQL은 RANGE, LIST, HASH, KEY 파티셔닝을 지원한다. 파티션 키가 PK나 UNIQUE 키에 포함되어야 한다는 제약이 있다.

```sql
CREATE TABLE logs (
    id BIGINT AUTO_INCREMENT,
    created_at DATE,
    PRIMARY KEY (id, created_at)
)
PARTITION BY RANGE (TO_DAYS(created_at)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

문제는 PK에 파티션 키를 반드시 포함시켜야 한다는 점이다. id만으로는 PK가 안 된다. id, created_at의 복합 PK를 써야 한다. 이건 ORM 매핑에 영향을 준다.

### PostgreSQL 파티셔닝

10부터 declarative partitioning이 들어왔다. 11에서 default partition, 12에서 외래 키 지원 등 매년 개선되고 있다.

```sql
CREATE TABLE logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMPTZ NOT NULL,
    message TEXT
) PARTITION BY RANGE (created_at);

CREATE TABLE logs_202601 PARTITION OF logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE logs_202602 PARTITION OF logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

PostgreSQL은 PK 제약이 더 유연하다. 다만 UNIQUE 제약을 전체 테이블에 걸려면 파티션 키를 포함해야 한다.

파티션을 자동 생성하는 기능은 둘 다 없다. `pg_partman` 같은 확장이나 직접 짠 스크립트로 월별 파티션을 미리 만들어 둬야 한다. 파티션 생성 누락으로 INSERT가 실패하는 사고가 흔하다.

---

## 11. VACUUM과 언두 로그 관리

### PostgreSQL의 VACUUM

dead row를 청소하는 작업이다. autovacuum이 기본으로 켜져 있고, 테이블 변경량이 임계치를 넘으면 자동으로 돈다. 하지만 실무에서는 autovacuum이 못 따라가는 경우가 많다.

대량 UPDATE/DELETE가 일어나는 테이블은 autovacuum 설정을 테이블별로 조정해야 한다.

```sql
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_vacuum_threshold = 1000,
    autovacuum_analyze_scale_factor = 0.005
);
```

`VACUUM FULL`은 테이블을 통째로 다시 쓰는 작업이라 ACCESS EXCLUSIVE 락을 잡는다. 운영 중에는 쓰면 안 된다. 대신 `pg_repack` 확장이나 `VACUUM`의 일반 모드로 처리한다.

트랜잭션 ID wraparound라는 무서운 현상이 있다. PostgreSQL의 트랜잭션 ID는 32비트라서 약 40억을 넘으면 순환한다. autovacuum이 freeze를 제대로 안 하면 wraparound 직전에 DB가 셧다운된다. `datfrozenxid`를 모니터링해야 한다.

```sql
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
-- 2억 정도부터 경계, 17억 넘어가면 위험
```

### MySQL의 언두 로그

InnoDB는 언두 로그를 system tablespace나 별도 언두 tablespace에 저장한다. 5.7 이후로 언두 tablespace를 분리할 수 있게 됐고, 8.0에서는 truncate도 자동으로 된다.

긴 트랜잭션이 살아 있으면 언두 로그가 무한정 쌓인다. ibdata1 파일이 폭증하는 사태가 옛 버전에서 흔했다. 8.0의 분리된 언두 tablespace는 이 문제를 완화한다.

```sql
-- 긴 트랜잭션 추적
SELECT * FROM information_schema.innodb_trx
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60
ORDER BY trx_started;
```

---

## 12. 락 동작과 데드락 처리

### 락 호환성 행렬

양쪽 다 row-level lock, table-level lock, intention lock 같은 구조를 갖고 있다. 세부 동작이 다른 부분만 짚는다.

InnoDB는 인덱스 row에 락을 건다. 인덱스가 없는 컬럼으로 WHERE를 걸면 테이블 전체에 락이 잡힌다. PostgreSQL도 비슷한데, 갭락이 없으므로 phantom 방지를 위한 추가 락이 적다.

### 데드락 감지

MySQL InnoDB는 wait-for graph로 데드락을 감지한다. 발견 즉시 한쪽을 abort 시킨다. `SHOW ENGINE INNODB STATUS`로 마지막 데드락 정보를 볼 수 있는데, 한 번에 하나만 보존된다는 점이 답답하다.

```sql
-- innodb_print_all_deadlocks 옵션을 켜면 모든 데드락이 에러 로그에 남는다
SET GLOBAL innodb_print_all_deadlocks = ON;
```

PostgreSQL은 `deadlock_timeout`(기본 1초) 동안 락 대기가 풀리지 않으면 데드락 감지 알고리즘을 돌린다. 감지되면 한쪽을 abort 시키고 에러 로그에 자세한 정보를 남긴다.

### 락 디버깅

PostgreSQL의 락 정보 쿼리는 표준화되어 있다.

```sql
SELECT
    blocked.pid AS blocked_pid,
    blocked.query AS blocked_query,
    blocking.pid AS blocking_pid,
    blocking.query AS blocking_query,
    blocking.usename AS blocking_user
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';
```

MySQL은 8.0의 `performance_schema.data_locks`와 `data_lock_waits` 테이블로 비슷한 정보를 볼 수 있다.

```sql
SELECT
    w.requesting_engine_lock_id,
    r.thread_id AS waiting_thread,
    b.thread_id AS blocking_thread,
    w.blocking_engine_lock_id,
    w.requesting_engine_transaction_id,
    w.blocking_engine_transaction_id
FROM performance_schema.data_lock_waits w
JOIN performance_schema.data_locks r ON r.engine_lock_id = w.requesting_engine_lock_id
JOIN performance_schema.data_locks b ON b.engine_lock_id = w.blocking_engine_lock_id;
```

---

## 13. EXPLAIN 출력 해석

### MySQL EXPLAIN

```
mysql> EXPLAIN SELECT * FROM orders o
    -> JOIN users u ON o.user_id = u.id
    -> WHERE u.created_at > '2026-01-01';
+----+-------------+-------+--------+---------------+---------+---------+---------------+------+-------------+
| id | select_type | table | type   | possible_keys | key     | key_len | ref           | rows | Extra       |
+----+-------------+-------+--------+---------------+---------+---------+---------------+------+-------------+
|  1 | SIMPLE      | u     | range  | PRIMARY,idx_c | idx_c   | 5       | NULL          | 1234 | Using where |
|  1 | SIMPLE      | o     | ref    | idx_user      | idx_user| 8       | db.u.id       |    5 | NULL        |
+----+-------------+-------+--------+---------------+---------+---------+---------------+------+-------------+
```

`type` 컬럼이 핵심이다. 빠른 순서로 `system > const > eq_ref > ref > range > index > ALL`. ALL이 보이면 full scan이라는 뜻이니 인덱스가 필요한지 확인한다.

`EXPLAIN FORMAT=JSON` 또는 `EXPLAIN ANALYZE`(8.0+)로 실제 실행 정보를 볼 수 있다.

### PostgreSQL EXPLAIN

```
QUERY PLAN
-----------------------------------------------------------------------
 Nested Loop  (cost=0.86..123.45 rows=10 width=120) (actual time=0.123..1.234 rows=8 loops=1)
   ->  Index Scan using idx_users_created on users u  (cost=0.43..45.67 rows=2 width=60)
         Index Cond: (created_at > '2026-01-01'::date)
   ->  Index Scan using idx_orders_user on orders o  (cost=0.43..38.89 rows=5 width=60)
         Index Cond: (user_id = u.id)
 Planning Time: 0.456 ms
 Execution Time: 1.567 ms
```

cost는 추정치, actual은 실제 측정치다. 추정 rows와 실제 rows가 크게 다르면 통계가 잘못된 것이니 ANALYZE를 돌려야 한다.

`EXPLAIN (ANALYZE, BUFFERS, VERBOSE)`로 상세 정보를 본다. BUFFERS는 디스크 I/O 통계가 나와서 캐시 효율을 판단할 때 유용하다.

두 DB의 EXPLAIN은 출력 형식과 용어가 완전히 달라서, MySQL 경험만으로 PostgreSQL 플랜을 읽기 어렵다. 양쪽 다 explain.depesz.com 같은 시각화 도구의 도움을 받는다.

---

## 14. 실무 선택 기준

### MySQL이 유리한 경우

- 단순 OLTP 워크로드, 짧은 트랜잭션, 인덱스로 풀리는 쿼리가 대부분
- 마스터-슬레이브로 읽기 확장이 필요한 웹 서비스
- 운영자 인력 풀이 더 많이 확보 가능
- 관리형 서비스(RDS MySQL, Aurora MySQL) 선택지가 풍부
- 복잡한 분석 쿼리 비중이 낮음
- 운영팀이 binlog 기반 도구(Debezium, Maxwell 등)에 익숙

### PostgreSQL이 유리한 경우

- 복잡한 쿼리, CTE, window function, lateral join을 자주 씀
- JSONB, 배열, 범위 타입, 지리 정보 같은 풍부한 타입이 필요
- GIN/GiST/BRIN 같은 특수 인덱스가 도움이 되는 워크로드
- 데이터 정합성과 표준 준수가 중요
- 확장(PostGIS, TimescaleDB, pgvector 등)을 적극 활용
- SERIALIZABLE 격리 수준이 필요한 금융/예약 시스템
- 분석성 쿼리 비중이 높음

### 둘 다 비슷한 경우

- 단순 CRUD 위주의 백오피스
- 트래픽이 작고 데이터가 수십 GB 수준
- ORM이 차이를 대부분 가려주는 표준 SQL만 사용

내 경험상 신규 프로젝트라면 PostgreSQL을 기본으로 깔고 시작하는 게 낫다. 기능 폭이 넓고 확장성이 좋다. 단, 팀이 MySQL만 다뤄봤고 PostgreSQL 운영 경험이 없다면 MySQL이 안전하다. 운영 노하우가 없는 DB를 도입하면 새벽 3시에 후회한다.

---

## 15. 마이그레이션 시 주의사항

### MySQL → PostgreSQL

**대소문자**: MySQL의 case-insensitive 동작에 의존한 쿼리가 PostgreSQL에서 안 맞는다. LOWER() 또는 citext로 대응.

**식별자 quoting**: MySQL은 백틱(\`), PostgreSQL은 큰따옴표("). MySQL에서 백틱으로 감싼 식별자가 대소문자 섞여 있으면 PostgreSQL에서 대소문자 그대로 살아남는다.

**AUTO_INCREMENT → IDENTITY**: 시퀀스로 변환된다. nextval 동작은 비슷하지만 트랜잭션 격리 시점에서 살짝 다르다.

**boolean**: MySQL은 TINYINT(1)로 boolean을 표현한다. PostgreSQL의 진짜 boolean으로 변환할 때 0/1을 false/true로 매핑한다.

**ENUM**: 양쪽 다 ENUM을 지원하지만 동작이 다르다. PostgreSQL ENUM은 ALTER TYPE으로만 값을 추가할 수 있고, 트랜잭션 안에서 추가하면 즉시 사용 못 한다.

**INSERT IGNORE, REPLACE**: MySQL 고유 문법이다. PostgreSQL에서는 `INSERT ... ON CONFLICT DO NOTHING` 또는 `ON CONFLICT DO UPDATE`로 바꾼다.

```sql
-- MySQL
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- PostgreSQL
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name;
```

**LIMIT/OFFSET 문법은 같다**. 대신 PostgreSQL은 `FETCH FIRST n ROWS ONLY` 표준 문법도 지원한다.

### PostgreSQL → MySQL

훨씬 어렵다. PostgreSQL에만 있는 기능이 많아서 무손실 마이그레이션이 안 된다.

- 배열 타입 → JSON 또는 별도 테이블
- JSONB의 GIN 인덱스 → 가상 컬럼 + 인덱스로 부분 대응
- CTE는 8.0부터 지원되지만 RECURSIVE의 일부 패턴이 안 됨
- FILTER 절, LATERAL JOIN 일부 동작이 다르거나 안 됨
- 윈도우 함수의 RANGE 프레임 동작 차이
- EXCLUDE 제약 → 없음. 트리거로 대체
- 부분 인덱스(WHERE 절 인덱스) → 8.0에 함수형 인덱스로 부분 대체

대규모 마이그레이션이라면 pgloader 같은 도구를 쓰되, 마이그레이션 전후로 양쪽에서 같은 쿼리를 돌려서 결과를 비교하는 검증 단계가 반드시 필요하다.

---

## 16. 트러블슈팅 사례

### 사례 1: MySQL 갭락 데드락

배치 작업이 매일 새벽에 데드락으로 죽었다. 두 워커가 같은 테이블에 INSERT/UPDATE를 동시에 치는데, 인덱스 없는 컬럼으로 WHERE를 걸어서 넓은 갭락이 잡혔다.

해결: 적절한 인덱스 추가, 격리 수준을 READ COMMITTED로 낮춤. READ COMMITTED에서는 갭락이 잡히지 않는다. binlog 포맷이 ROW여야 가능하다.

```sql
SET GLOBAL transaction_isolation = 'READ-COMMITTED';
SET GLOBAL binlog_format = 'ROW';
```

### 사례 2: PostgreSQL bloat로 응답 지연

매일 수백만 row를 INSERT/DELETE하는 큐 테이블이 있었다. autovacuum이 못 따라가서 테이블 크기가 100GB까지 부풀었고 SELECT가 점점 느려졌다.

해결: 큐 테이블을 파티셔닝으로 바꾸고, 처리 완료된 파티션을 DROP. DELETE 대신 DROP을 쓰면 dead row 자체가 안 생긴다. autovacuum 설정도 공격적으로 조정.

### 사례 3: MySQL 복제 지연 폭증

대량 ALTER TABLE을 마스터에 쳤더니 슬레이브에서 그대로 재현되면서 슬레이브가 멈췄다. binlog_format=ROW였는데도 DDL은 STATEMENT로 기록되기 때문이다.

해결: pt-online-schema-change(pt-osc) 또는 gh-ost 같은 온라인 스키마 변경 도구로 ALTER를 처리. 새 테이블을 만들고 트리거로 동기화한 뒤 RENAME으로 swap하는 방식.

### 사례 4: PostgreSQL 트랜잭션 ID wraparound 경보

`datfrozenxid` age가 17억을 넘어가면서 alert가 떴다. autovacuum이 freeze를 못 따라가고 있었다.

해결: 큰 테이블에 `VACUUM FREEZE`를 수동으로 돌리되, 시간을 나눠서 진행. `vacuum_freeze_min_age`, `autovacuum_freeze_max_age` 같은 파라미터를 조정.

```sql
-- 위험한 테이블 식별
SELECT relname, age(relfrozenxid) AS xid_age
FROM pg_class
WHERE relkind = 'r'
ORDER BY xid_age DESC
LIMIT 20;

-- 수동 freeze
VACUUM (FREEZE, VERBOSE) target_table;
```

### 사례 5: MySQL utf8 인코딩 이슈

5.7 이전 환경에서 `utf8` charset을 썼는데, 이 utf8은 사실 utf8mb3로 3바이트까지만 지원했다. 이모지가 들어오면 데이터가 잘렸다.

해결: charset을 utf8mb4로 통째로 변경. 기존 인덱스 크기가 utf8mb4로 바뀌면 늘어나서 키 길이 제한(767바이트 → 3072바이트로 늘었지만 그래도 부족)에 걸리는 경우가 있다. innodb_large_prefix=ON, ROW_FORMAT=DYNAMIC으로 대응.

### 사례 6: PostgreSQL 통계 부정확으로 잘못된 플랜

JOIN하는 두 테이블에서 ANALYZE를 한참 안 돌렸더니 옵티마이저가 NESTED LOOP으로 풀어버렸다. 실제로는 HASH JOIN이 맞는 상황이었다. 응답이 수십 배 느려졌다.

해결: 해당 테이블에 ANALYZE 수동 실행. autovacuum_analyze_scale_factor를 낮춰서 더 자주 통계가 갱신되도록 조정. 큰 테이블은 `default_statistics_target`을 100에서 500이나 1000으로 올려서 히스토그램 정밀도를 높임.

---

## 정리

MySQL과 PostgreSQL은 외관상 비슷한 RDBMS지만 내부 동작이 꽤 다르다. 락 동작, MVCC 구현, 인덱스 종류, 격리 수준의 의미, EXPLAIN 출력 모두 다르므로 한쪽 경험만으로 다른 쪽을 운영하면 사고가 난다. 신규 도입 시에는 팀의 운영 경험을 우선 고려하고, 둘 다 다뤄야 한다면 차이점을 명시적으로 학습한 사람이 운영을 맡아야 한다. 두 DB 모두 매년 새로운 기능이 들어오므로 마이너 버전 노트를 챙겨 보는 습관이 중요하다.
