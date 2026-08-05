---
title: Aurora MySQL에서의 JSON 타입 실무
tags: [aws, aurora, mysql, json, index, parallel-query, replication]
updated: 2026-06-15
---

# Aurora MySQL에서의 JSON 타입 실무

Aurora MySQL은 MySQL 8.0과 호환되므로 JSON 타입 동작도 기본적으로 커뮤니티 MySQL 8.0과 같다. 함수 시그니처, 저장 포맷, 인덱싱 우회 방법 모두 8.0 그대로다. 하지만 Aurora는 스토리지 계층과 복제 메커니즘이 다르기 때문에, JSON을 많이 쓰는 워크로드에서 커뮤니티 MySQL과 다르게 움직이는 지점이 몇 군데 있다. Parallel Query 적용 제외, reader 분산, in-place update와 복제 부하가 그렇다.

이 문서는 JSON 타입의 기본 쿼리부터 시작해서 인덱싱 우회, Aurora 특화 주의사항, 그리고 실무에서 반복적으로 겪는 안티패턴까지 다룬다. 엔진 자체 비교는 [My_SQL_vs_Postgre_SQL.md](../../DataBase/RDBMS/My_SQL_vs_Postgre_SQL.md), Aurora 클러스터 운영은 [Aurora_DB_Cluster.md](Aurora_DB_Cluster.md)를 참고한다.

---

## 1. JSON 타입의 저장 구조와 TEXT 대비 차이

### 1.1 왜 TEXT가 아니라 JSON인가

MySQL 5.7 이전에는 JSON 문자열을 그냥 TEXT나 LONGTEXT에 박아 넣었다. 8.0의 JSON 타입은 입력받은 텍스트를 파싱해서 바이너리 포맷으로 저장한다. 이 바이너리 포맷에는 키와 값의 오프셋이 인덱스처럼 들어 있어서, `JSON_EXTRACT`로 특정 키를 꺼낼 때 문서 전체를 다시 파싱하지 않고 해당 위치로 바로 점프한다.

TEXT에 JSON을 넣으면 매 쿼리마다 문자열을 파싱해야 하고, 파싱 비용은 문서가 클수록 커진다. 또 TEXT는 JSON 함수가 동작하긴 하지만 매번 유효성 검사와 파싱을 새로 하므로 느리다. 정렬·비교 시에도 TEXT는 문자열 사전순으로 비교하지만 JSON 타입은 타입을 인식해서 숫자는 숫자끼리, 문자열은 문자열끼리 비교한다.

차이를 코드로 보면 이렇다.

```sql
-- TEXT 컬럼: 입력 그대로 저장, 유효성 검사 없음
CREATE TABLE log_text (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  payload TEXT
);

-- 깨진 JSON도 그냥 들어간다
INSERT INTO log_text (payload) VALUES ('{"a": 1, broken');  -- 성공

-- JSON 컬럼: 파싱 + 유효성 검사 + 바이너리 변환
CREATE TABLE log_json (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  payload JSON
);

INSERT INTO log_json (payload) VALUES ('{"a": 1, broken');
-- ERROR 3140: Invalid JSON text
```

JSON 타입은 입력 시점에 유효성을 막아주므로, 데이터 무결성 측면에서 TEXT보다 낫다. 단점은 입력 시 파싱 비용이 한 번 더 든다는 것인데, 대부분의 워크로드에서 이건 읽기 시 매번 파싱하는 비용보다 싸다.

### 1.2 키 순서가 바뀐다

JSON 타입에 넣으면 객체 키가 정규화된다. 중복 키는 마지막 값만 남고, 공백은 제거된다. 키 순서는 보존되지 않는다(MySQL 8.0.x 버전에 따라 동작 차이가 있지만, 순서에 의존하면 안 된다).

```sql
SELECT CAST('{"b": 1, "a": 2, "b": 3}' AS JSON);
-- 결과: {"a": 2, "b": 3}  -- b 중복 제거, 키 정렬됨, 공백 제거
```

원본 텍스트를 한 글자도 안 바꾸고 보존해야 하는 요구사항(예: 외부 서명 검증용 페이로드 원문)이 있으면 JSON 타입을 쓰면 안 된다. 이건 TEXT/LONGTEXT로 가야 한다. 서명 검증 대상 원문을 JSON 컬럼에 넣었다가 키 순서가 바뀌어서 서명이 깨지는 사고를 실제로 본 적 있다.

---

## 2. 자주 쓰는 JSON 함수

### 2.1 추출 — JSON_EXTRACT와 ->, ->>

가장 많이 쓰는 게 값 추출이다. `JSON_EXTRACT(col, path)`가 기본이고, `->`는 그 축약, `->>`는 `JSON_UNQUOTE(JSON_EXTRACT(...))`의 축약이다.

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  attrs JSON
);

INSERT INTO orders (attrs) VALUES
  ('{"channel": "web", "coupon": {"code": "A10", "rate": 0.1}, "tags": ["new", "vip"]}');

-- 셋 다 같은 값을 가리키지만 결과 타입이 다르다
SELECT
  JSON_EXTRACT(attrs, '$.channel'),  -- "web"  (큰따옴표 포함된 JSON 문자열)
  attrs -> '$.channel',              -- "web"  (위와 동일)
  attrs ->> '$.channel';             -- web    (UNQUOTE된 순수 문자열)
```

`->`와 `->>`의 차이를 모르고 쓰면 WHERE 절에서 자주 헛발질한다.

```sql
-- 잘못된 비교: 왼쪽은 JSON "web", 오른쪽은 SQL 문자열 web
SELECT * FROM orders WHERE attrs -> '$.channel' = 'web';   -- 매칭 안 됨

-- 올바른 비교 두 가지
SELECT * FROM orders WHERE attrs ->> '$.channel' = 'web';        -- UNQUOTE 후 비교
SELECT * FROM orders WHERE attrs -> '$.channel' = JSON_QUOTE('web');  -- 양쪽 다 JSON
```

중첩 경로와 배열 인덱스도 path 표현식으로 접근한다.

```sql
SELECT
  attrs ->> '$.coupon.code',    -- A10
  attrs ->> '$.coupon.rate',    -- 0.1
  attrs ->> '$.tags[0]',        -- new
  JSON_LENGTH(attrs, '$.tags'); -- 2
```

### 2.2 수정 — JSON_SET, JSON_REPLACE, JSON_INSERT, JSON_REMOVE

세 함수의 차이는 "경로가 이미 있을 때 / 없을 때" 동작이다.

- `JSON_SET`: 있으면 갱신, 없으면 추가
- `JSON_REPLACE`: 있으면 갱신, 없으면 무시
- `JSON_INSERT`: 없으면 추가, 있으면 무시
- `JSON_REMOVE`: 경로 삭제

```sql
SET @doc = '{"a": 1, "b": 2}';

SELECT JSON_SET(@doc, '$.a', 10, '$.c', 3);     -- {"a": 10, "b": 2, "c": 3}
SELECT JSON_REPLACE(@doc, '$.a', 10, '$.c', 3); -- {"a": 10, "b": 2}  (c는 무시)
SELECT JSON_INSERT(@doc, '$.a', 10, '$.c', 3);  -- {"a": 1, "b": 2, "c": 3}  (a는 무시)
SELECT JSON_REMOVE(@doc, '$.b');                -- {"a": 1}
```

실제 UPDATE는 이렇게 쓴다.

```sql
-- coupon.rate를 0.15로 갱신
UPDATE orders
SET attrs = JSON_SET(attrs, '$.coupon.rate', 0.15)
WHERE id = 1;

-- tags 배열에 원소 추가 (JSON_ARRAY_APPEND)
UPDATE orders
SET attrs = JSON_ARRAY_APPEND(attrs, '$.tags', 'sale')
WHERE id = 1;
```

`JSON_SET`을 어떻게 쓰느냐가 뒤에 나올 in-place update 최적화와 직결된다. 값의 길이를 바꾸지 않는 갱신(`JSON_REPLACE`/`JSON_SET`으로 같은 길이 값 교체)은 부분 업데이트로 처리되지만, 키를 추가하거나 값 길이를 늘리면 문서 전체를 다시 쓴다. 4장에서 자세히 다룬다.

### 2.3 검색 — JSON_CONTAINS, JSON_CONTAINS_PATH

`JSON_CONTAINS(target, candidate, path)`는 후보 값이 대상 안에 들어 있는지 본다. 배열에 특정 원소가 있는지 확인할 때 자주 쓴다.

```sql
-- tags 배열에 "vip"가 있는 행
SELECT * FROM orders
WHERE JSON_CONTAINS(attrs -> '$.tags', '"vip"');

-- 객체 부분 매칭: coupon.code가 "A10"인 행
SELECT * FROM orders
WHERE JSON_CONTAINS(attrs, '{"code": "A10"}', '$.coupon');

-- 특정 경로의 존재 여부만 확인
SELECT * FROM orders
WHERE JSON_CONTAINS_PATH(attrs, 'one', '$.coupon');
```

주의할 점은 `JSON_CONTAINS`의 두 번째 인자는 JSON 문자열이어야 한다는 것이다. 문자열 `"vip"`를 찾을 때 작은따옴표 안에 큰따옴표를 넣은 `'"vip"'` 형태로 줘야 한다. `'vip'`로 주면 유효한 JSON이 아니라 에러난다.

### 2.4 JSON_TABLE — 배열을 행으로 펼치기

JSON 배열을 관계형 행으로 펼쳐서 JOIN하거나 집계할 때 `JSON_TABLE`을 쓴다. MySQL 8.0에서 추가된 기능이고 Aurora MySQL 3(8.0 호환)에서 동작한다.

```sql
-- 한 주문의 tags 배열을 행으로 펼치기
SELECT o.id, t.tag
FROM orders o,
JSON_TABLE(
  o.attrs, '$.tags[*]'
  COLUMNS (tag VARCHAR(50) PATH '$')
) AS t
WHERE o.id = 1;
-- id | tag
-- 1  | new
-- 1  | vip
```

객체 배열을 펼칠 때가 실무에서 더 흔하다. 주문 안에 라인 아이템 배열이 들어 있는 경우를 보자.

```sql
INSERT INTO orders (attrs) VALUES ('{
  "items": [
    {"sku": "A", "qty": 2, "price": 1000},
    {"sku": "B", "qty": 1, "price": 3000}
  ]
}');

SELECT o.id, i.sku, i.qty, i.price, i.qty * i.price AS amount
FROM orders o,
JSON_TABLE(
  o.attrs, '$.items[*]'
  COLUMNS (
    sku   VARCHAR(20) PATH '$.sku',
    qty   INT         PATH '$.qty',
    price INT         PATH '$.price'
  )
) AS i
WHERE o.id = 2;
```

`JSON_TABLE`에는 `FOR ORDINALITY`로 배열 인덱스를 뽑거나, `DEFAULT ... ON EMPTY` / `ON ERROR`로 누락값 처리를 지정하는 옵션도 있다.

```sql
SELECT o.id, i.pos, i.sku, i.qty
FROM orders o,
JSON_TABLE(
  o.attrs, '$.items[*]'
  COLUMNS (
    pos FOR ORDINALITY,                          -- 1부터 시작하는 순번
    sku VARCHAR(20) PATH '$.sku',
    qty INT PATH '$.qty' DEFAULT '0' ON EMPTY    -- qty 누락 시 0
  )
) AS i
WHERE o.id = 2;
```

`JSON_TABLE`은 편리하지만, 이걸 자주 쓰게 된다는 건 정형 데이터를 JSON에 넣었다는 신호일 때가 많다. 5장에서 다룬다.

---

## 3. JSON 컬럼 인덱싱

### 3.1 JSON 컬럼에 직접 인덱스를 못 건다

MySQL은 JSON 컬럼 자체에 인덱스를 만들 수 없다.

```sql
CREATE INDEX idx_attrs ON orders (attrs);
-- ERROR 3152: JSON column 'attrs' supplied to index 'idx_attrs'
--             cannot be used in key specification.
```

이유는 JSON 문서 전체가 BLOB처럼 가변 길이라서 B-tree 키로 쓸 수 없기 때문이다. 그래서 JSON 안의 특정 값을 인덱싱하려면 generated column으로 그 값을 끄집어낸 뒤 거기에 인덱스를 건다.

### 3.2 generated column + 보조 인덱스

generated column에는 STORED와 VIRTUAL 두 종류가 있다.

- **VIRTUAL**: 값을 디스크에 저장하지 않고 읽을 때마다 계산한다. 인덱스를 걸면 인덱스에는 값이 들어간다. 컬럼 추가가 메타데이터 변경만으로 끝나 빠르다(8.0 기준 INSTANT 가능).
- **STORED**: 값을 실제로 디스크에 저장한다. 행이 커지고, 추가 시 테이블을 다시 쓴다.

대부분의 경우 VIRTUAL + 인덱스 조합을 쓴다. 인덱스 자체에 값이 물리적으로 저장되므로 인덱스 검색에는 STORED와 차이가 없고, 행은 안 커지기 때문이다.

```sql
-- channel 값을 VIRTUAL 컬럼으로 뽑고 인덱스 생성
ALTER TABLE orders
  ADD COLUMN channel VARCHAR(20)
    AS (attrs ->> '$.channel') VIRTUAL,
  ADD INDEX idx_channel (channel);

-- 이제 옵티마이저가 인덱스를 탄다
SELECT * FROM orders WHERE channel = 'web';

-- 원래 JSON 표현식으로 써도 옵티마이저가 generated column 인덱스를 매칭한다
SELECT * FROM orders WHERE attrs ->> '$.channel' = 'web';
```

여기서 자주 막히는 게 타입과 길이 불일치다. generated column의 타입이 비교 대상과 다르면 인덱스를 안 탄다. JSON에서 뽑은 값은 기본이 문자열(LONGTEXT 계열)이므로, 숫자로 비교하려면 명시적으로 캐스팅하거나 컬럼 타입을 숫자로 선언해야 한다.

```sql
-- 숫자 비교용 generated column은 타입을 명확히 지정
ALTER TABLE orders
  ADD COLUMN coupon_rate DECIMAL(4,2)
    AS (attrs ->> '$.coupon.rate') VIRTUAL,
  ADD INDEX idx_coupon_rate (coupon_rate);
```

문자열을 인덱싱할 때는 collation도 신경 써야 한다. JSON에서 `->>`로 뽑은 값은 `utf8mb4_bin` 계열로 나오는 경우가 있어서, 테이블 기본 collation과 다르면 인덱스를 못 타거나 비교 결과가 예상과 다르다. generated column 정의에 `COLLATE`를 명시하면 안전하다.

```sql
ALTER TABLE orders
  ADD COLUMN channel VARCHAR(20)
    AS (attrs ->> '$.channel') VIRTUAL
    COLLATE utf8mb4_0900_ai_ci,
  ADD INDEX idx_channel (channel);
```

### 3.3 multi-valued index — JSON 배열 인덱싱

generated column 방식은 스칼라 값 하나에만 쓸 수 있다. 배열 안의 여러 값을 인덱싱하려면 MySQL 8.0.17부터 들어온 multi-valued index를 쓴다. Aurora MySQL 3.04 이상에서 지원한다(버전 확인 필요).

```sql
-- tags 배열의 모든 원소를 인덱싱
ALTER TABLE orders
  ADD INDEX idx_tags ((CAST(attrs -> '$.tags' AS CHAR(20) ARRAY)));

-- JSON_CONTAINS / MEMBER OF / JSON_OVERLAPS에서 이 인덱스를 탄다
SELECT * FROM orders
WHERE JSON_CONTAINS(attrs -> '$.tags', '"vip"');

SELECT * FROM orders
WHERE 'vip' MEMBER OF (attrs -> '$.tags');

SELECT * FROM orders
WHERE JSON_OVERLAPS(attrs -> '$.tags', '["vip", "sale"]');
```

multi-valued index에는 제약이 몇 가지 있다.

- 한 인덱스에 multi-valued key part는 하나만 들어갈 수 있다. 복합 인덱스에서 배열 키는 1개로 제한된다.
- 인덱스를 타려면 `MEMBER OF`, `JSON_CONTAINS`, `JSON_OVERLAPS` 중 하나를 써야 한다. 일반 `=` 비교로는 안 탄다.
- 배열 원소가 많으면 한 행이 인덱스에 그만큼 여러 엔트리를 만든다. 원소 수백 개짜리 배열을 가진 행을 대량 INSERT하면 인덱스 쓰기 부하가 크다.
- `CAST(... AS ... ARRAY)`의 타입이 실제 배열 원소 타입과 안 맞으면 런타임 에러가 난다. 숫자 배열이면 `UNSIGNED ARRAY`, 문자열이면 `CHAR(n) ARRAY`로 맞춘다.

`EXPLAIN`으로 실제 인덱스를 탔는지 꼭 확인한다. multi-valued index는 옵티마이저가 안 타는 경우가 종종 있어서, 쿼리를 짜고 나면 `EXPLAIN`에서 `key`에 인덱스 이름이 찍히는지 봐야 한다.

```sql
EXPLAIN SELECT * FROM orders WHERE 'vip' MEMBER OF (attrs -> '$.tags');
-- key 컬럼에 idx_tags가 찍히면 인덱스 사용 중
```

---

## 4. Aurora 특화 주의사항

여기부터가 커뮤니티 MySQL과 갈라지는 부분이다.

### 4.1 Parallel Query와 JSON 함수

Aurora MySQL의 Parallel Query는 스토리지 노드로 필터·집계 연산을 밀어내려서(push down) 대용량 스캔을 병렬 처리하는 기능이다. 문제는 push down 가능한 연산 목록이 제한적이고, JSON 함수가 들어간 조건은 대부분 push down 대상에서 빠진다는 것이다.

```sql
-- 이 쿼리는 Parallel Query가 적용되지 않을 가능성이 높다
SELECT COUNT(*) FROM big_table
WHERE attrs ->> '$.status' = 'active';
```

`JSON_EXTRACT`, `->`, `->>` 같은 함수가 WHERE 조건에 있으면, Aurora 옵티마이저가 해당 조건을 스토리지 계층으로 내리지 못하고 일반 실행 경로로 돌린다. 그래서 "Parallel Query를 켰는데 왜 안 빨라지지?"의 원인이 JSON 함수인 경우가 있다. `EXPLAIN`에서 `Using parallel query`가 안 보이면 이걸 의심한다.

우회는 3장의 generated column이다. JSON에서 뽑은 값을 STORED generated column으로 실체화해두면, 그 컬럼은 일반 컬럼이므로 Parallel Query의 push down 대상이 된다.

```sql
-- status를 STORED 컬럼으로 실체화 (Parallel Query push down 가능)
ALTER TABLE big_table
  ADD COLUMN status VARCHAR(20)
    AS (attrs ->> '$.status') STORED;

SELECT COUNT(*) FROM big_table WHERE status = 'active';
-- 이제 status 조건이 스토리지 계층으로 내려간다
```

여기서는 VIRTUAL이 아니라 STORED를 쓴다. VIRTUAL은 디스크에 값이 없어서 스토리지 노드가 직접 평가할 수 없고, push down 이점을 못 받는다. Parallel Query 대상 테이블에서 JSON 값을 자주 필터링한다면 STORED로 가는 게 맞다. 대신 행이 커지는 비용은 감수해야 한다.

### 4.2 reader 분산 시 고려사항

Aurora 클러스터는 reader 엔드포인트로 읽기 쿼리를 복제본에 분산한다. JSON 함수가 무거운 쿼리를 reader로 보내는 것 자체는 문제없다. reader도 같은 스토리지를 공유하므로 데이터는 동일하다.

주의할 건 두 가지다.

첫째, JSON 함수는 CPU를 많이 쓴다. 큰 문서에서 `JSON_EXTRACT`를 수천 번 호출하는 분석 쿼리를 reader로 보내면, 그 reader 인스턴스의 CPU가 100%로 튄다. reader가 여러 대여도 reader 엔드포인트는 라운드로빈으로만 분산하므로, 무거운 쿼리가 특정 reader에 몰리면 그 인스턴스만 죽는다. 분석용 JSON 쿼리는 전용 reader(커스텀 엔드포인트)로 격리하는 게 안전하다.

둘째, generated column을 reader에서 쓸 때 복제 일관성이다. VIRTUAL generated column은 reader에서도 읽을 때 계산되므로 writer와 항상 같은 값이 나온다. 문제는 generated column에 인덱스를 추가하는 DDL 시점이다. 인덱스 추가 중에는 옵티마이저가 reader마다 인덱스 가용 여부를 다르게 볼 수 있어서, DDL 적용 직후 잠깐 동안 같은 쿼리가 reader마다 다른 실행 계획을 탈 수 있다. 인덱스 추가 직후 성능이 들쭉날쭉하면 이걸 의심한다.

### 4.3 큰 JSON 문서가 행 크기와 버퍼풀에 주는 영향

JSON 컬럼은 내부적으로 BLOB 계열로 저장된다. 문서가 작으면 행 안에 인라인으로 들어가지만, 일정 크기를 넘으면 오버플로우 페이지로 분리되어 별도 저장된다. 이게 성능에 영향을 준다.

InnoDB는 한 행을 읽을 때 인라인 부분을 통째로 버퍼풀에 올린다. JSON 컬럼이 행 안에 인라인으로 크게 들어가 있으면, JSON과 무관한 `SELECT id, created_at` 같은 쿼리도 그 큰 행을 통째로 버퍼풀에 적재한다. 자주 읽는 작은 컬럼과 큰 JSON이 한 행에 같이 있으면, 큰 JSON이 버퍼풀을 잡아먹어서 캐시 효율이 떨어진다.

Aurora는 버퍼풀이 인스턴스 메모리에 묶여 있다(스토리지는 분산이지만 버퍼풀은 인스턴스 로컬이다). 큰 JSON이 버퍼풀을 점유하면 다른 핫 데이터가 밀려나서 스토리지 노드에서 다시 읽어오는 빈도가 늘고, 이건 Aurora에서 네트워크 왕복 비용으로 직결된다.

대응은 두 가지다. 큰 JSON을 자주 안 읽으면 별도 테이블로 분리해서 메인 테이블 행을 가볍게 유지한다. 또는 자주 같이 안 읽는 거대 JSON은 아예 S3 같은 외부 저장소에 두고 DB에는 포인터만 둔다. JSON 문서가 수십 KB를 넘어가기 시작하면 이 판단을 해야 한다.

---

## 5. 부분 업데이트(in-place update)와 복제 부하

### 5.1 부분 업데이트가 동작하는 조건

MySQL 8.0은 JSON 컬럼을 갱신할 때, 조건이 맞으면 문서 전체를 다시 쓰지 않고 바뀐 부분만 제자리에서 고치는 부분 업데이트를 한다. 큰 문서에서 작은 값 하나를 바꿀 때 이게 동작하면 쓰기 비용이 크게 준다.

부분 업데이트가 동작하려면 모든 조건을 만족해야 한다.

- `JSON_SET`, `JSON_REPLACE`, `JSON_REMOVE`만 사용해야 한다. `JSON_INSERT`나 `JSON_ARRAY_APPEND`로 새 요소를 추가하면 부분 업데이트가 안 된다.
- 갱신 대상 컬럼이 갱신 소스와 같은 컬럼이어야 한다(`SET attrs = JSON_SET(attrs, ...)` 형태).
- 새 값이 기존 값보다 크지 않아야 한다. 같거나 작아야 한다. 값 길이가 늘면 제자리에 못 넣으니 전체를 다시 쓴다.
- 경로가 이미 존재해야 한다. 없는 키를 추가하는 건 부분 업데이트 대상이 아니다.

```sql
-- 부분 업데이트 가능: 기존 rate(0.1)를 같은 길이 0.2로 교체
UPDATE orders SET attrs = JSON_REPLACE(attrs, '$.coupon.rate', 0.2) WHERE id = 1;

-- 부분 업데이트 깨짐: 값 길이 증가 (0.1 -> 0.123456)
UPDATE orders SET attrs = JSON_REPLACE(attrs, '$.coupon.rate', 0.123456) WHERE id = 1;

-- 부분 업데이트 깨짐: 없던 키 추가
UPDATE orders SET attrs = JSON_SET(attrs, '$.new_key', 1) WHERE id = 1;
```

부분 업데이트가 실제로 일어났는지는 직접 보기 어렵지만, 정해진 길이 슬롯을 미리 잡아두는 설계로 유도할 수 있다. 예를 들어 상태 값을 `"active"`, `"paused"`처럼 길이가 다른 문자열로 두면 상태 전환 시 길이가 바뀌어 전체 재작성이 일어난다. 길이를 맞추거나 코드값(`"01"`, `"02"`)으로 두면 부분 업데이트가 유지된다. 빈번하게 갱신되는 키라면 이 정도까지 신경 쓸 가치가 있다.

### 5.2 binlog와 복제 부하

기본적으로 MySQL의 row 기반 복제는 UPDATE 시 바뀐 행 전체를 binlog에 기록한다. JSON 컬럼이 1MB짜리인데 그 안의 숫자 하나만 바꿔도, 기본 설정이면 1MB 행 전체가 binlog에 들어간다. JSON 컬럼을 초당 수백 번 갱신하는 워크로드라면 binlog가 폭증한다.

이걸 줄이는 게 `binlog_row_value_options = PARTIAL_JSON`이다. 이 옵션을 켜면 부분 업데이트가 일어난 JSON 컬럼에 대해, 전체가 아니라 변경된 부분(diff)만 binlog에 기록한다.

```sql
-- 부분 JSON diff만 binlog에 기록 (파라미터 그룹에서 설정)
SET GLOBAL binlog_row_value_options = 'PARTIAL_JSON';
```

단, 5.1의 부분 업데이트 조건을 만족할 때만 diff가 기록된다. 부분 업데이트가 깨지는 갱신은 여전히 전체 행이 binlog에 들어간다. 즉 `PARTIAL_JSON`의 효과를 보려면 5.1 조건을 지키는 쿼리를 써야 한다. 둘은 세트로 움직인다.

Aurora MySQL에서 추가로 봐야 할 게 있다. Aurora의 writer-reader 복제는 binlog가 아니라 스토리지 계층 redo log로 동작하므로, 클러스터 내부 reader 복제에는 binlog 크기가 직접 영향을 주지 않는다. 하지만 binlog를 켜는 경우(다른 리전이나 외부 시스템으로의 binlog 복제, CDC, DMS 연동 등)에는 위의 binlog 폭증 문제가 그대로 적용된다. CDC로 JSON 테이블을 다른 데로 흘려보내고 있다면 `PARTIAL_JSON`과 부분 업데이트 조건을 반드시 챙겨야 한다.

---

## 6. 실무에서 겪는 문제

### 6.1 JSON에 정형 데이터를 넣는 안티패턴

가장 흔한 실수다. 초기에 "스키마가 자주 바뀔 것 같으니 일단 JSON에 다 넣자"고 시작했다가, 결국 그 JSON 안의 값으로 필터·정렬·조인을 다 하게 되는 경우다.

증상은 이렇게 나타난다. generated column이 5개, 6개로 늘어난다. JSON_TABLE을 쓴 쿼리가 도처에 생긴다. 인덱스가 JSON 표현식 인덱스로 도배된다. 이 시점이면 사실상 정형 테이블을 JSON 위에 어설프게 재구현한 것이다.

판단 기준은 단순하다. **그 키로 WHERE, ORDER BY, JOIN을 하는가**. 셋 중 하나라도 자주 한다면 그 값은 정규 컬럼으로 빼야 한다. JSON은 "통째로 읽고 통째로 쓰지만, 그 안의 개별 값으로 검색은 거의 안 하는" 데이터에 맞다. 예를 들어 외부 API 응답 원본, 사용자별로 키가 제각각인 설정값, 로그의 가변 메타데이터 같은 것이다.

반대로 JSON이 잘 맞는 경우도 분명히 있다. 키 집합이 행마다 다른 sparse한 속성, 스키마를 못 박을 수 없는 외부 데이터, 읽기는 통째로만 하는 스냅샷. 이런 건 컬럼으로 빼면 NULL 천지가 되거나 컬럼이 수십 개로 늘어나니 JSON이 낫다.

### 6.2 JSON_EXTRACT 결과 타입 캐스팅 함정

JSON에서 뽑은 값은 타입이 모호하다. 이걸 다른 값과 비교하거나 연산할 때 의도와 다르게 동작하는 경우가 많다.

```sql
-- JSON 숫자를 문자열로 뽑으면 숫자 비교가 사전순이 된다
SELECT * FROM orders
WHERE attrs ->> '$.priority' > '9';
-- '10'은 '9'보다 사전순으로 작아서(첫 글자 '1' < '9') 누락된다

-- 명시적 캐스팅으로 숫자 비교
SELECT * FROM orders
WHERE CAST(attrs ->> '$.priority' AS UNSIGNED) > 9;
```

날짜도 마찬가지다. JSON 안에 ISO 문자열로 든 날짜는 그냥 문자열이라 날짜 함수가 바로 안 먹는다.

```sql
-- 문자열 그대로면 날짜 비교가 사전순. ISO 8601이면 우연히 맞지만 위험하다
SELECT * FROM orders
WHERE attrs ->> '$.created_at' >= '2026-01-01';

-- 명시적 캐스팅이 안전
SELECT * FROM orders
WHERE CAST(attrs ->> '$.created_at' AS DATETIME) >= '2026-01-01';
```

`->`로 뽑은 값(JSON 타입)과 `->>`로 뽑은 값(문자열)을 섞어서 비교하면 결과가 또 달라진다. NULL 처리도 함정이다. JSON 안의 `null`은 SQL의 NULL이 아니라 JSON null이라서, `JSON_EXTRACT`로 뽑으면 문자열 `"null"`이 아니라 JSON null 값이 나온다. `IS NULL`로는 안 잡히고 `JSON_TYPE`으로 봐야 한다.

```sql
-- JSON null과 경로 부재를 구분
SELECT
  JSON_EXTRACT('{"a": null}', '$.a'),        -- NULL 리터럴 (JSON null)
  JSON_EXTRACT('{"a": null}', '$.b'),        -- SQL NULL (경로 없음)
  JSON_TYPE(JSON_EXTRACT('{"a": null}', '$.a'));  -- 'NULL' (JSON null 타입)
```

generated column으로 값을 뽑을 때 타입을 명확히 선언하면 이런 캐스팅 함정 대부분을 컬럼 정의 시점에 한 번에 막을 수 있다. 그래서 3장에서 generated column 타입을 신경 쓰라고 한 것이다.

### 6.3 컬럼 분리 기준 정리

JSON에 둘지 컬럼으로 뺄지 매번 헷갈린다면 이렇게 정리한다.

- 검색·정렬·조인 키 → 정규 컬럼. JSON에 두면 인덱스와 캐스팅이 끝없이 따라온다.
- 자주 갱신되는 단일 값 → 정규 컬럼. JSON 안에 두면 부분 업데이트 조건을 매번 신경 써야 한다.
- 통째로 읽고 통째로 쓰는 스냅샷·원본 → JSON 또는 TEXT.
- 행마다 키가 다른 sparse 속성 → JSON.
- 외부 시스템이 주는 그대로의 페이로드 → 원문 보존이 필요하면 TEXT, 검색이 필요하면 JSON.

한 테이블 안에서 정규 컬럼과 JSON을 섞어 쓰는 게 정상이다. 자주 쓰는 핵심 필드는 컬럼으로 빼서 인덱스 걸고, 나머지 부가 정보만 JSON에 모아두는 형태가 운영하기 가장 무난하다. 처음부터 완벽하게 나눌 수는 없으니, generated column이 서너 개를 넘어가기 시작하면 그때 정규 컬럼으로 승격하는 리팩터링을 한다.
