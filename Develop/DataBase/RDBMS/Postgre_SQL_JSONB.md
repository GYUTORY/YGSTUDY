---
title: PostgreSQL JSONB 실무
tags: [postgresql, jsonb, json, gin-index, jsonpath, jsonb_set, jsonb_each]
updated: 2026-08-07
---

# PostgreSQL JSONB 실무

## JSON vs JSONB 저장 구조

PostgreSQL에는 JSON 타입이 두 개다. `json`과 `jsonb`. 이름만 보면 비슷해 보이지만 저장 방식이 완전히 다르다.

`json`은 입력 텍스트를 그대로 저장한다. 공백, 키 순서, 중복 키까지 전부 보존된다. 읽을 때마다 파싱이 일어난다. 인덱스를 걸 수 없다.

`jsonb`는 파싱된 바이너리 구조로 저장한다. 저장 시 한 번 파싱하고, 그 결과물을 보관한다. 몇 가지 부작용이 따른다.

- 키 순서가 보존되지 않는다. PostgreSQL이 내부적으로 정렬한다.
- 중복 키가 있으면 마지막 것만 남는다. 에러도 안 난다.
- 의미 없는 공백이 사라진다.

실무에서는 거의 항상 `jsonb`를 쓴다. `json`이 의미 있는 경우는 딱 하나다. HTTP 요청 원본이나 외부 API 응답 전문처럼 입력 그대로를 감사 목적으로 보존해야 할 때다. 그 외에는 `jsonb`가 맞다.

---

## 연산자

`->`와 `->>`부터 정리하면, `->` 는 JSON을 반환하고 `->>`는 TEXT를 반환한다.

```sql
-- 단일 키 접근
SELECT data->'user' FROM events;         -- jsonb 반환
SELECT data->>'user' FROM events;        -- text 반환

-- 배열 인덱스 접근 (0-based)
SELECT data->'tags'->0 FROM events;      -- 첫 번째 요소, jsonb
SELECT data->'tags'->>0 FROM events;     -- 첫 번째 요소, text

-- 중첩 경로: #> 와 #>>
SELECT data#>'{user,address,city}' FROM events;   -- jsonb
SELECT data#>>'{user,address,city}' FROM events;  -- text
```

`->` 체이닝과 `#>` 경로 표기는 기능이 같다. 중첩이 깊으면 `#>`가 가독성이 낫다.

### containment 연산자: @> 와 <@

`@>`는 왼쪽 jsonb가 오른쪽을 포함하는지 검사한다. GIN 인덱스를 활용하므로 대용량 테이블에서 핵심 연산자다.

```sql
-- 특정 키-값 포함 여부
SELECT * FROM products WHERE data @> '{"status": "active"}';

-- 배열 내 특정 값 포함 여부
SELECT * FROM products WHERE data @> '{"tags": ["sale"]}';

-- 중첩 객체 포함 여부
SELECT * FROM products WHERE data @> '{"pricing": {"currency": "KRW"}}';

-- <@ : 왼쪽이 오른쪽에 포함되는지
SELECT * FROM products WHERE '{"status": "active"}' <@ data;
```

`@>`에서 한 가지 주의할 점: 배열 포함 검사는 순서를 따지지 않는다. `{"tags": ["a", "b"]}`는 `{"tags": ["b"]}`를 포함한다. 하지만 `{"tags": ["a", "b"]}`가 `{"tags": ["a", "b", "c"]}`에 포함되지는 않는다. 포함 방향을 헷갈리면 결과가 다르게 나온다.

### 키 존재 연산자: ?, ?|, ?&

```sql
-- 최상위 키가 존재하는지
SELECT * FROM products WHERE data ? 'discount';

-- 키 중 하나라도 존재하는지
SELECT * FROM products WHERE data ?| array['sale_price', 'discount_rate'];

-- 키 모두 존재하는지
SELECT * FROM products WHERE data ?& array['price', 'stock', 'sku'];
```

`?` 계열 연산자는 최상위 키만 검사한다. 중첩 키의 존재 여부는 `@>`로 확인한다.

```sql
-- 중첩 키 존재 여부: @>로 빈 객체 포함 검사
SELECT * FROM products WHERE data @> '{"pricing": {}}';
```

### 기타 연산자

```sql
-- concatenation: 최상위 키 병합 (shallow merge)
UPDATE products SET data = data || '{"updated_at": "2026-08-07"}' WHERE id = 1;

-- 최상위 키 삭제
UPDATE products SET data = data - 'deprecated_field' WHERE id = 1;

-- 특정 경로 삭제
UPDATE products SET data = data #- '{pricing,old_price}' WHERE id = 1;
```

`||` 연산자는 shallow merge다. 중첩 객체가 있으면 통째로 대체된다. `data->'pricing'`이 있는 상태에서 `data || '{"pricing": {"vat": 0.1}}'`을 치면, 기존 pricing 객체의 다른 키가 전부 날아간다.

---

## GIN 인덱스: jsonb_ops vs jsonb_path_ops

GIN 인덱스를 만들 때 operator class를 선택해야 한다.

`jsonb_ops`는 기본값이다. 모든 키, 값, 경로를 인덱싱한다. `@>`, `<@`, `?`, `?|`, `?&` 전부 인덱스를 탄다. 인덱스가 크다.

`jsonb_path_ops`는 `@>` 연산자만 지원한다. 경로와 값의 조합을 해시로 저장하므로 인덱스 크기가 `jsonb_ops`보다 작고 `@>` 검색이 빠르다. `?`, `?|`, `?&`는 인덱스를 타지 않는다.

```sql
-- jsonb_ops (기본, 명시하지 않으면 이것)
CREATE INDEX idx_products_gin ON products USING GIN (data);

-- jsonb_path_ops
CREATE INDEX idx_products_gin_path ON products USING GIN (data jsonb_path_ops);
```

선택 기준은 단순하다. 쿼리에서 `?`, `?|`, `?&`를 쓰면 `jsonb_ops`를 써야 한다. `@>` containment 검색만 한다면 `jsonb_path_ops`가 낫다. 같은 컬럼에 두 인덱스를 다 만들 수도 있지만 쓰기 비용이 두 배가 된다.

특정 키 값만 인덱싱하려면 표현식 인덱스가 전체 GIN보다 가볍다.

```sql
-- 특정 키에 B-Tree 인덱스 (등호, 범위 검색 가능)
CREATE INDEX idx_products_category ON products ((data->>'category'));
CREATE INDEX idx_products_price ON products (((data->>'price')::numeric));

-- 부분 인덱스와 조합
CREATE INDEX idx_products_active_category ON products ((data->>'category'))
WHERE data->>'status' = 'active';
```

표현식 인덱스는 `data->>'category' = 'electronics'` 같은 단순 등호나 범위 쿼리에 쓴다. `@>` containment에는 GIN이 필요하다.

GIN 인덱스 구축은 B-Tree보다 훨씬 느리다. 수백만 row 테이블이라면 `CONCURRENTLY` 옵션을 써야 잠금 없이 만들 수 있다.

```sql
CREATE INDEX CONCURRENTLY idx_products_gin ON products USING GIN (data);
```

---

## jsonpath 쿼리 (PostgreSQL 12+)

jsonpath는 SQL/JSON Path Language 표준을 PostgreSQL이 구현한 것이다. XPath와 비슷한 개념으로 JSON 안을 탐색한다. `@`가 현재 컨텍스트를 의미한다.

### 기본 함수

```sql
-- 경로가 매칭되는 값이 있는지 (boolean 반환)
SELECT * FROM orders
WHERE jsonb_path_exists(data, '$.items[*].price ? (@ > 50000)');

-- 매칭되는 모든 값을 set으로 반환
SELECT jsonb_path_query(data, '$.items[*].name') FROM orders;

-- 매칭되는 모든 값을 배열로 반환
SELECT jsonb_path_query_array(data, '$.items[*].price') FROM orders;

-- 첫 번째 매칭 값만 반환
SELECT jsonb_path_query_first(data, '$.user.name') FROM orders;
```

### @@ 와 @? 연산자

`@@`는 jsonb에 jsonpath를 적용해서 boolean을 반환한다. `@?`는 경로가 존재하면 true를 반환한다.

```sql
-- @@ : 조건 평가
SELECT * FROM orders WHERE data @@ '$.status == "pending"';
SELECT * FROM orders WHERE data @@ '$.amount > 5000';
SELECT * FROM orders WHERE data @@ '$.user.age >= 18';

-- @? : 경로 존재 여부
SELECT * FROM orders WHERE data @? '$.items[*] ? (@.price > 50000)';
SELECT * FROM orders WHERE data @? '$.shipping.tracking_number';
```

jsonpath가 편한 상황은 배열 내 조건 필터링이다. 기존 연산자로는 배열 안의 특정 요소만 골라내기가 불편한데, jsonpath의 `?` 필터 표현식을 쓰면 된다.

```sql
-- 10만원 이상 아이템이 하나라도 있는 주문
SELECT id FROM orders WHERE data @? '$.items[*] ? (@.price >= 100000)';

-- 특정 카테고리의 재고가 0인 상품
SELECT id FROM products WHERE data @? '$.variants[*] ? (@.stock == 0 && @.category == "electronics")';
```

`@@`와 `@?`는 GIN 인덱스(`jsonb_path_ops`)를 탈 수 있지만, 조건의 복잡도에 따라 planner가 인덱스를 안 쓰기도 한다. `EXPLAIN`으로 확인한다.

---

## 수정 함수

### jsonb_set

`jsonb_set(target jsonb, path text[], new_value jsonb, create_missing boolean)`

특정 경로의 값을 교체한다. 기본값인 `create_missing = false`이면 경로가 없을 때 null을 반환한다.

```sql
-- 최상위 키 값 변경
UPDATE products
SET data = jsonb_set(data, '{status}', '"inactive"')
WHERE id = 1;

-- 중첩 경로 변경
UPDATE products
SET data = jsonb_set(data, '{pricing, discounted}', 'true', true)
WHERE id = 1;

-- 배열 특정 위치 값 변경
UPDATE products
SET data = jsonb_set(data, '{tags, 0}', '"featured"')
WHERE id = 1;
```

`create_missing = true`는 중간 경로를 자동 생성하지 않는다. 최종 키만 생성한다. `{a, b, c}`에서 `a`, `b`가 없어도 `c`만 만든다는 뜻이 아니라, `a.b`가 있는 상태에서 `c`가 없을 때 `c`를 만든다는 의미다. 중간 객체까지 없으면 결과는 null이다.

### jsonb_insert

`jsonb_insert(target jsonb, path text[], new_value jsonb, insert_after boolean)`

배열에 요소를 삽입할 때 쓴다. `insert_after = false`(기본)이면 path 앞에, `true`이면 뒤에 삽입한다.

```sql
-- 배열 끝에 추가
UPDATE products
SET data = jsonb_insert(data, '{tags, -1}', '"clearance"', true)
WHERE id = 1;

-- 배열 맨 앞에 삽입
UPDATE products
SET data = jsonb_insert(data, '{tags, 0}', '"featured"')
WHERE id = 1;
```

`-1`은 마지막 요소를 가리킨다. `insert_after = true`와 조합하면 배열 끝에 추가된다.

### jsonb_strip_nulls

JSON null 값을 가진 키를 재귀적으로 제거한다.

```sql
SELECT jsonb_strip_nulls('{"a": 1, "b": null, "c": {"d": null, "e": 2}}'::jsonb);
-- 결과: {"a": 1, "c": {"e": 2}}
```

실무에서 외부 API 응답을 저장할 때 null 필드가 많으면 사전에 strip_nulls를 돌려서 저장 공간을 줄이기도 한다.

---

## 중첩 구조 업데이트 주의사항

중첩 JSONB를 업데이트할 때 자주 만나는 문제가 두 가지다.

첫째, `jsonb_set`이 반환하는 값이 null인 경우다.

```sql
-- pricing 키가 없으면 NULL을 반환한다
UPDATE products
SET data = jsonb_set(data, '{pricing, sale_price}', '9900')
WHERE id = 1;
-- pricing이 없으면 data 컬럼 자체가 NULL로 업데이트된다
```

방어적으로 처리하려면 경로가 있는지 먼저 확인하거나 `coalesce`를 쓴다.

```sql
UPDATE products
SET data = jsonb_set(
    CASE
        WHEN data ? 'pricing' THEN data
        ELSE data || '{"pricing": {}}'::jsonb
    END,
    '{pricing, sale_price}',
    '9900',
    true
)
WHERE id = 1;
```

둘째, `||` 연산자의 shallow merge 특성이다.

```sql
-- 이렇게 하면 기존 pricing 내용이 통째로 대체된다
UPDATE products
SET data = data || '{"pricing": {"vat": 0.1}}'::jsonb
WHERE id = 1;
-- 기존 pricing.original_price, pricing.sale_price 등이 전부 사라진다
```

최상위 키만 바꾸는 게 아니라면 `jsonb_set`을 써야 한다. 여러 중첩 필드를 동시에 바꿔야 하면 jsonb_set을 체이닝한다.

```sql
UPDATE products
SET data = jsonb_set(
               jsonb_set(data, '{pricing, vat}', '0.1', true),
               '{pricing, updated_at}', '"2026-08-07"'::jsonb, true
           )
WHERE id = 1;
```

세 단계 이상 중첩을 체이닝으로 다루면 코드가 읽기 어려워진다. 이 시점이 오면 애플리케이션에서 JSON을 읽어 수정한 뒤 통째로 다시 저장하는 편이 낫다. DB에서 복잡한 JSONB 수술을 하는 건 득보다 실이 많다.

---

## jsonb_each / jsonb_array_elements로 언피벗

JSONB 내부를 행으로 풀어내야 할 때 쓰는 함수들이다.

### 객체 언피벗

```sql
-- jsonb_each: 객체의 키-값 쌍을 행으로
SELECT p.id, e.key, e.value
FROM products p, jsonb_each(p.data) e;

-- jsonb_each_text: value를 TEXT로
SELECT p.id, e.key, e.value
FROM products p, jsonb_each_text(p.data) e;

-- jsonb_object_keys: 키 목록만
SELECT DISTINCT key FROM products, jsonb_object_keys(data) key;
```

`jsonb_each`는 최상위 키만 전개한다. 중첩 객체를 재귀적으로 전개하려면 재귀 CTE가 필요하다.

### 배열 언피벗

```sql
-- jsonb_array_elements: 배열을 행으로
SELECT p.id, tag
FROM products p, jsonb_array_elements(p.data->'tags') tag;

-- jsonb_array_elements_text: TEXT로
SELECT p.id, tag
FROM products p, jsonb_array_elements_text(p.data->'tags') tag;
```

배열 안 객체를 다루는 패턴이 자주 쓰인다.

```sql
-- 주문 내 아이템 행 전개
SELECT
    o.id AS order_id,
    item->>'name'           AS item_name,
    (item->>'price')::numeric AS item_price,
    (item->>'qty')::int     AS qty
FROM orders o,
     jsonb_array_elements(o.data->'items') item
WHERE (item->>'price')::numeric > 10000;
```

배열이 없거나 null인 경우 `jsonb_array_elements`가 에러를 낸다. 방어하려면 `jsonb_typeof`로 확인하거나 `LEFT JOIN LATERAL`을 쓴다.

```sql
-- 배열이 없는 row도 포함
SELECT o.id, item
FROM orders o
LEFT JOIN LATERAL jsonb_array_elements(
    CASE WHEN jsonb_typeof(o.data->'items') = 'array'
         THEN o.data->'items'
         ELSE '[]'::jsonb
    END
) item ON true;
```

---

## 타입 캐스팅과 NULL 처리

JSONB에서 실수가 잦은 부분이다.

`->>`는 항상 TEXT를 반환한다. 숫자 비교에서 캐스팅을 빠뜨리면 예상과 다른 결과가 나온다.

```sql
-- 잘못된 비교: 문자열 비교로 처리된다
WHERE data->>'price' > '9000'     -- '9000' < '999' (사전 순)

-- 올바른 비교
WHERE (data->>'price')::numeric > 9000
WHERE (data->>'created_at')::timestamptz > '2026-01-01'::timestamptz
```

SQL NULL과 JSON null은 다르다.

```sql
-- SQL NULL: 컬럼 자체가 없는 경우
WHERE data IS NULL

-- JSON null: 키가 있고 값이 null인 경우
WHERE data = 'null'::jsonb

-- 키가 있지만 값이 null인 경우 찾기
WHERE data ? 'discount' AND data->'discount' = 'null'::jsonb

-- 키가 없거나 값이 null인 경우 모두
WHERE NOT (data ? 'discount') OR data->'discount' = 'null'::jsonb
```

---

## 대용량 JSONB 운영

PostgreSQL은 row 하나가 8kB 페이지에 안 들어가면 TOAST(The Oversized-Attribute Storage Technique)로 처리한다. JSONB 컬럼이 큰 문서를 담으면 자동으로 압축해서 별도 TOAST 테이블에 저장한다. TOAST 조회는 별도 I/O가 발생하므로, 자주 읽는 작은 필드와 가끔 읽는 큰 필드를 같은 JSONB에 다 넣으면 비효율이 생긴다.

대용량 JSON 문서가 필요하면 JSONB 컬럼을 분리하거나, 자주 조회하는 필드는 별도 컬럼으로 추출하는 방식을 고려한다.

```sql
-- 자주 검색하는 필드를 컬럼으로 분리
ALTER TABLE products ADD COLUMN category TEXT GENERATED ALWAYS AS (data->>'category') STORED;
CREATE INDEX idx_products_category ON products (category);
```

Generated column을 쓰면 INSERT/UPDATE 때 자동으로 채워지고, 별도 인덱스를 걸 수 있다. 전체 GIN 인덱스보다 작고 B-Tree라서 범위 검색도 된다.

---

## 실제로 겪은 문제

### GIN 인덱스가 안 타는 쿼리

```sql
-- 인덱스를 안 탄다: 형변환이 들어가면 GIN은 안 탄다
WHERE (data->>'price')::numeric > 5000

-- 인덱스를 탄다: containment
WHERE data @> '{"status": "active"}'

-- 표현식 인덱스로 해결
CREATE INDEX idx_products_price ON products (((data->>'price')::numeric));
WHERE (data->>'price')::numeric > 5000  -- 이제 인덱스 탄다
```

GIN 인덱스는 `@>`, `<@`, `?`, `?|`, `?&`, `@@`, `@?` 연산자에 작동한다. `->>`로 꺼낸 값에 비교 연산자를 쓰면 GIN이 아닌 표현식 인덱스가 필요하다.

### 배열 요소 업데이트 누락

배열 안 특정 요소를 조건으로 찾아서 업데이트하는 경우가 있다. JSONB는 SQL의 UPDATE처럼 배열 내 특정 요소만 수정하는 문법이 없다. 전체 배열을 가져와서 애플리케이션에서 수정한 뒤 다시 쓰거나, `jsonb_set`으로 인덱스를 지정해야 한다.

인덱스를 모르는 상태에서 조건에 맞는 요소를 수정하려면 쿼리가 복잡해진다.

```sql
-- items 배열 중 특정 sku의 price를 바꾸는 예제
WITH updated AS (
    SELECT
        id,
        jsonb_agg(
            CASE WHEN item->>'sku' = 'ABC-001'
                 THEN jsonb_set(item, '{price}', '15000')
                 ELSE item
            END
        ) AS new_items
    FROM orders, jsonb_array_elements(data->'items') item
    GROUP BY id
)
UPDATE orders o
SET data = jsonb_set(o.data, '{items}', u.new_items)
FROM updated u
WHERE o.id = u.id;
```

이런 쿼리가 반복된다면, JSONB 내부 구조 설계를 다시 봐야 한다. 배열 내 요소를 자주 단독으로 업데이트해야 한다면 별도 테이블로 분리하는 편이 훨씬 낫다.

### @> 와 ? 의 GIN operator class 불일치

```sql
-- jsonb_path_ops로 만든 인덱스
CREATE INDEX idx_gin_path ON products USING GIN (data jsonb_path_ops);

-- 이 쿼리는 인덱스를 못 탄다
WHERE data ? 'discount'  -- jsonb_path_ops는 ? 연산자 미지원
```

`?`, `?|`, `?&`가 필요한데 `jsonb_path_ops`로 만들면 이 연산자들은 seq scan으로 빠진다. `EXPLAIN`으로 확인하지 않으면 놓치기 쉽다.
