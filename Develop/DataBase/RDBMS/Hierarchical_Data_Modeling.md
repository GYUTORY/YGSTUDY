---
title: 계층형 데이터 모델링
tags: [database, hierarchical, tree, adjacency-list, closure-table, nested-set, recursive-cte, category, comment]
updated: 2026-04-08
---

# 계층형 데이터 모델링

## 개요

카테고리, 조직도, 댓글 트리처럼 부모-자식 관계가 반복되는 데이터를 RDB에 저장하는 건 생각보다 까다롭다. RDB는 기본적으로 평면(flat) 구조라서 트리를 표현하려면 별도의 설계가 필요하다.

실무에서 자주 쓰는 방식은 4가지다.

| 방식 | 핵심 아이디어 |
|------|-------------|
| 인접 리스트 (Adjacency List) | 각 행이 자기 부모의 ID를 갖는다 |
| 경로 열거 (Path Enumeration) | 루트부터 현재 노드까지의 경로를 문자열로 저장한다 |
| 중첩 집합 (Nested Set) | 각 노드에 left/right 번호를 매겨서 범위로 하위 트리를 조회한다 |
| 클로저 테이블 (Closure Table) | 모든 조상-후손 관계를 별도 테이블에 저장한다 |

어떤 방식이 맞는지는 "읽기가 많은지 쓰기가 많은지", "트리 깊이가 어느 정도인지", "부분 트리 조회가 필요한지"에 따라 달라진다.

---

## 1. 인접 리스트 (Adjacency List)

가장 직관적인 방식이다. 각 행에 `parent_id` 컬럼을 두고 자기 부모를 가리킨다.

### DDL

```sql
CREATE TABLE category (
    id        BIGINT PRIMARY KEY AUTO_INCREMENT,
    name      VARCHAR(100) NOT NULL,
    parent_id BIGINT NULL,
    FOREIGN KEY (parent_id) REFERENCES category(id)
);

CREATE INDEX idx_category_parent ON category(parent_id);
```

### 데이터 예시

```sql
INSERT INTO category (id, name, parent_id) VALUES
(1, '전자제품', NULL),
(2, '컴퓨터', 1),
(3, '노트북', 2),
(4, '데스크탑', 2),
(5, '스마트폰', 1),
(6, '게이밍 노트북', 3);
```

트리 구조:

```
전자제품 (1)
├── 컴퓨터 (2)
│   ├── 노트북 (3)
│   │   └── 게이밍 노트북 (6)
│   └── 데스크탑 (4)
└── 스마트폰 (5)
```

### 주요 쿼리

**직속 자식 조회** — 간단하다.

```sql
SELECT * FROM category WHERE parent_id = 2;
-- 노트북, 데스크탑
```

**전체 하위 트리 조회** — 재귀 CTE가 필요하다.

```sql
WITH RECURSIVE subtree AS (
    SELECT id, name, parent_id, 0 AS depth
    FROM category
    WHERE id = 1

    UNION ALL

    SELECT c.id, c.name, c.parent_id, s.depth + 1
    FROM category c
    JOIN subtree s ON c.parent_id = s.id
)
SELECT * FROM subtree;
```

**노드 삽입** — parent_id만 지정하면 된다.

```sql
INSERT INTO category (name, parent_id) VALUES ('울트라북', 3);
```

**노드 삭제** — 자식이 있으면 처리가 필요하다. 자식까지 같이 지우려면 재귀가 필요하고, 자식을 상위로 올리려면 UPDATE를 먼저 해야 한다.

```sql
-- 자식을 상위로 올리고 삭제
UPDATE category SET parent_id = 2 WHERE parent_id = 3;
DELETE FROM category WHERE id = 3;
```

### 장단점

- INSERT가 빠르다. 행 하나만 추가하면 된다.
- 직속 자식 조회는 인덱스 하나로 해결된다.
- 전체 하위 트리 조회에 재귀 CTE가 필요하다. 트리가 깊으면 성능이 떨어진다.
- 노드 이동은 parent_id UPDATE 한 번이면 끝나서 구조 변경이 쉽다.

---

## 2. 경로 열거 (Path Enumeration)

루트부터 현재 노드까지의 경로를 문자열로 저장한다. 파일 시스템 경로와 비슷한 방식이다.

### DDL

```sql
CREATE TABLE category (
    id   BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    path VARCHAR(500) NOT NULL
);

CREATE INDEX idx_category_path ON category(path);
```

### 데이터 예시

```sql
INSERT INTO category (id, name, path) VALUES
(1, '전자제품', '1/'),
(2, '컴퓨터', '1/2/'),
(3, '노트북', '1/2/3/'),
(4, '데스크탑', '1/2/4/'),
(5, '스마트폰', '1/5/'),
(6, '게이밍 노트북', '1/2/3/6/');
```

### 주요 쿼리

**전체 하위 트리 조회** — LIKE 하나로 끝난다. 재귀가 필요 없다.

```sql
SELECT * FROM category WHERE path LIKE '1/2/%';
-- 노트북, 데스크탑, 게이밍 노트북
```

**조상 조회** — 현재 노드의 path에 포함된 ID를 추출한다.

```sql
-- 게이밍 노트북(6)의 조상 조회
SELECT * FROM category
WHERE '1/2/3/6/' LIKE CONCAT(path, '%');
-- 전자제품, 컴퓨터, 노트북, 게이밍 노트북
```

**깊이 계산** — 구분자 개수를 세면 된다.

```sql
SELECT name,
       (LENGTH(path) - LENGTH(REPLACE(path, '/', ''))) - 1 AS depth
FROM category;
```

**노드 삽입** — 부모의 path를 가져와서 자기 ID를 붙인다.

```sql
-- 부모(3)의 path가 '1/2/3/'이면
INSERT INTO category (id, name, path) VALUES (7, '울트라북', '1/2/3/7/');
```

**노드 이동** — 자기와 모든 하위 노드의 path를 일괄 UPDATE 해야 한다.

```sql
-- 노트북(3) 하위 트리를 스마트폰(5) 아래로 이동
UPDATE category
SET path = REPLACE(path, '1/2/3/', '1/5/3/')
WHERE path LIKE '1/2/3/%';
```

### 장단점

- 하위 트리 조회가 LIKE 한 번이라 빠르다.
- 조상 조회도 쉽다.
- path 문자열 관리가 번거롭다. 노드를 이동하면 하위 전체의 path를 UPDATE 해야 한다.
- path 컬럼 길이에 제한이 있어서 트리가 매우 깊으면 문제가 된다.
- 참조 무결성을 DB 레벨에서 보장하기 어렵다. path 값이 잘못되어도 DB가 잡아주지 않는다.

---

## 3. 중첩 집합 (Nested Set)

각 노드에 `lft`와 `rgt` 값을 부여한다. 노드의 하위 트리는 lft와 rgt 사이에 있는 노드들이다. 트리를 깊이 우선 탐색(DFS)하면서 번호를 매기는 방식이다.

### DDL

```sql
CREATE TABLE category (
    id   BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    lft  INT NOT NULL,
    rgt  INT NOT NULL
);

CREATE INDEX idx_category_lft_rgt ON category(lft, rgt);
```

### 데이터 예시

```
          전자제품 [1, 12]
         /              \
   컴퓨터 [2, 9]     스마트폰 [10, 11]
    /        \
노트북 [3, 6]  데스크탑 [7, 8]
    |
게이밍 노트북 [4, 5]
```

```sql
INSERT INTO category (id, name, lft, rgt) VALUES
(1, '전자제품', 1, 12),
(2, '컴퓨터', 2, 9),
(3, '노트북', 3, 6),
(4, '게이밍 노트북', 4, 5),
(5, '데스크탑', 7, 8),
(6, '스마트폰', 10, 11);
```

### 주요 쿼리

**전체 하위 트리 조회** — lft, rgt 범위 비교 한 번이면 된다. 재귀가 필요 없다.

```sql
-- 컴퓨터(lft=2, rgt=9)의 모든 하위 노드
SELECT * FROM category
WHERE lft BETWEEN 2 AND 9;
-- 컴퓨터, 노트북, 게이밍 노트북, 데스크탑
```

**조상 조회** — 반대로 현재 노드의 lft를 포함하는 범위를 찾는다.

```sql
-- 게이밍 노트북(lft=4)의 조상
SELECT * FROM category
WHERE lft < 4 AND rgt > 5
ORDER BY lft;
-- 전자제품, 컴퓨터, 노트북
```

**리프 노드 조회** — rgt = lft + 1인 노드가 리프다.

```sql
SELECT * FROM category WHERE rgt = lft + 1;
```

**노드 삽입** — 삽입 위치 이후의 lft, rgt를 전부 밀어야 한다.

```sql
-- 데스크탑(lft=7, rgt=8) 아래에 새 노드 추가
-- 1) 공간 확보: rgt >= 8인 노드들의 rgt를 +2
UPDATE category SET rgt = rgt + 2 WHERE rgt >= 8;
-- 2) lft >= 8인 노드들의 lft를 +2
UPDATE category SET lft = lft + 2 WHERE lft > 8;
-- 3) 새 노드 삽입
INSERT INTO category (name, lft, rgt) VALUES ('조립PC', 8, 9);
```

**노드 삭제** — 삭제 후 빈 공간을 메우기 위해 전체 번호를 다시 조정해야 한다.

```sql
-- 게이밍 노트북(lft=4, rgt=5) 삭제
DELETE FROM category WHERE lft BETWEEN 4 AND 5;

-- 빈 공간(2만큼) 메우기
UPDATE category SET lft = lft - 2 WHERE lft > 5;
UPDATE category SET rgt = rgt - 2 WHERE rgt > 5;
```

### 장단점

- 하위 트리 조회, 조상 조회가 단순 범위 비교라서 읽기가 빠르다.
- INSERT, DELETE, UPDATE 할 때마다 lft/rgt 값을 대량으로 갱신해야 한다. 쓰기 비용이 크다.
- 트리 구조가 자주 바뀌는 서비스에서는 쓰기 잠금 때문에 병목이 생긴다.
- 읽기 비율이 압도적으로 높고 구조 변경이 거의 없는 경우에 적합하다. 예를 들어 쇼핑몰의 상품 카테고리 같은 곳에서 쓴다.

---

## 4. 클로저 테이블 (Closure Table)

모든 조상-후손 쌍을 별도 테이블에 저장한다. 정규화된 방식이라서 데이터 무결성이 가장 좋다.

### DDL

```sql
CREATE TABLE category (
    id   BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE category_path (
    ancestor   BIGINT NOT NULL,
    descendant BIGINT NOT NULL,
    depth      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (ancestor, descendant),
    FOREIGN KEY (ancestor) REFERENCES category(id),
    FOREIGN KEY (descendant) REFERENCES category(id)
);

CREATE INDEX idx_cp_descendant ON category_path(descendant);
CREATE INDEX idx_cp_depth ON category_path(depth);
```

### 데이터 예시

```sql
INSERT INTO category (id, name) VALUES
(1, '전자제품'), (2, '컴퓨터'), (3, '노트북'),
(4, '게이밍 노트북'), (5, '데스크탑'), (6, '스마트폰');

-- 모든 조상-후손 관계 (자기 자신 포함)
INSERT INTO category_path (ancestor, descendant, depth) VALUES
-- 자기 자신
(1, 1, 0), (2, 2, 0), (3, 3, 0), (4, 4, 0), (5, 5, 0), (6, 6, 0),
-- 전자제품의 후손
(1, 2, 1), (1, 3, 2), (1, 4, 3), (1, 5, 2), (1, 6, 1),
-- 컴퓨터의 후손
(2, 3, 1), (2, 4, 2), (2, 5, 1),
-- 노트북의 후손
(3, 4, 1);
```

### 주요 쿼리

**전체 하위 트리 조회** — JOIN 한 번이면 된다.

```sql
SELECT c.* FROM category c
JOIN category_path cp ON c.id = cp.descendant
WHERE cp.ancestor = 2 AND cp.depth > 0;
-- 노트북, 게이밍 노트북, 데스크탑
```

**직속 자식만 조회** — depth 조건을 추가한다.

```sql
SELECT c.* FROM category c
JOIN category_path cp ON c.id = cp.descendant
WHERE cp.ancestor = 2 AND cp.depth = 1;
-- 노트북, 데스크탑
```

**조상 조회**

```sql
SELECT c.* FROM category c
JOIN category_path cp ON c.id = cp.ancestor
WHERE cp.descendant = 4 AND cp.depth > 0
ORDER BY cp.depth DESC;
-- 전자제품, 컴퓨터, 노트북
```

**노드 삽입** — 새 노드와 모든 조상의 관계를 추가한다.

```sql
-- '울트라북'을 노트북(3) 아래에 추가
INSERT INTO category (id, name) VALUES (7, '울트라북');

-- 자기 자신 + 노트북의 모든 조상과의 관계를 복사
INSERT INTO category_path (ancestor, descendant, depth)
SELECT cp.ancestor, 7, cp.depth + 1
FROM category_path cp
WHERE cp.descendant = 3
UNION ALL
SELECT 7, 7, 0;
```

**서브트리 삭제** — 관계 행만 지우면 된다. 다른 노드에 영향이 없다.

```sql
-- 노트북(3) 하위 트리 삭제
DELETE FROM category_path
WHERE descendant IN (
    SELECT descendant FROM (
        SELECT descendant FROM category_path WHERE ancestor = 3
    ) tmp
);

DELETE FROM category
WHERE id IN (3, 4, 6); -- 노트북, 게이밍 노트북 등
```

**서브트리 이동** — 기존 관계를 끊고 새 관계를 연결한다.

```sql
-- 노트북(3) 하위 트리를 스마트폰(6) 아래로 이동

-- 1) 이동할 서브트리 내부 관계를 제외하고, 외부 조상과의 관계 삭제
DELETE FROM category_path
WHERE descendant IN (SELECT descendant FROM category_path WHERE ancestor = 3)
  AND ancestor NOT IN (SELECT descendant FROM category_path WHERE ancestor = 3);

-- 2) 새 부모(6)의 조상들과 서브트리의 관계를 생성
INSERT INTO category_path (ancestor, descendant, depth)
SELECT sup.ancestor, sub.descendant, sup.depth + sub.depth + 1
FROM category_path sup
CROSS JOIN category_path sub
WHERE sup.descendant = 6
  AND sub.ancestor = 3;
```

### 장단점

- 읽기 쿼리가 간단하고 빠르다. 하위 트리, 조상, 깊이별 조회를 모두 인덱스로 처리한다.
- INSERT는 조상 수만큼의 행을 추가해야 한다. 트리가 깊으면 행 수가 늘어난다.
- 서브트리 이동이 다른 노드에 영향을 주지 않는다. 중첩 집합처럼 전체 번호를 재조정할 필요가 없다.
- 저장 공간을 가장 많이 쓴다. 노드 N개에 대해 관계 테이블의 행 수는 O(N × 깊이)다.
- FK 제약을 걸 수 있어서 데이터 무결성이 가장 좋다.

---

## 성능 비교

노드 수 10,000개, 평균 깊이 5~6인 트리 기준으로 각 작업의 성능 특성을 정리한다.

| 작업 | 인접 리스트 | 경로 열거 | 중첩 집합 | 클로저 테이블 |
|------|-----------|----------|----------|-------------|
| 직속 자식 조회 | O(1) — 인덱스 스캔 | O(N) — LIKE 패턴 | O(N) — 범위 스캔 후 필터 | O(1) — depth=1 조건 |
| 전체 하위 트리 | O(깊이) — 재귀 CTE | O(N) — LIKE 프리픽스 | O(1) — 범위 스캔 | O(K) — K=하위 노드 수 |
| 조상 경로 | O(깊이) — 재귀 CTE | O(N) — LIKE 역방향 | O(log N) — 범위 스캔 | O(깊이) — 인덱스 스캔 |
| INSERT 1건 | O(1) — 행 1개 | O(1) — 행 1개 | O(N) — lft/rgt 갱신 | O(깊이) — 관계 행 추가 |
| DELETE 1건 | O(1)* | O(1) | O(N) — lft/rgt 갱신 | O(깊이) — 관계 행 삭제 |
| 서브트리 이동 | O(1) — parent_id 변경 | O(K) — path 일괄 변경 | O(N) — lft/rgt 재계산 | O(K × 깊이) — 관계 재연결 |
| 저장 공간 | 최소 | 중간 (path 문자열) | 최소 | 최대 (관계 테이블) |

*인접 리스트의 DELETE는 자식 처리 방식에 따라 달라진다. CASCADE면 O(서브트리 크기), 부모 변경이면 O(자식 수).

---

## 실무에서 어떤 패턴을 쓰는가

### 쇼핑몰 카테고리

카테고리는 한 번 잡으면 구조가 거의 바뀌지 않는다. 읽기가 99% 이상이다. 카테고리 페이지를 열 때마다 하위 카테고리 전체를 가져와야 하니까 조회 성능이 중요하다.

- 소규모 쇼핑몰(카테고리 100개 이하): **인접 리스트 + 재귀 CTE**로 충분하다. 구현이 간단하고 관리하기 쉽다.
- 대규모 쇼핑몰(카테고리 1,000개 이상): **중첩 집합**이나 **클로저 테이블**을 쓴다. 카테고리 변경은 관리자만 가끔 하니까 쓰기 비용이 높아도 상관없다. 캐시를 같이 쓰면 DB 호출 자체를 줄일 수 있다.

### 조직도

조직 구조는 팀 개편, 인사 이동 때 바뀐다. 빈번하지는 않지만 변경 시 서브트리 이동이 필요하다.

- **인접 리스트**가 가장 적합하다. 조직도 깊이가 보통 5~7단계 정도라서 재귀 CTE의 성능 문제가 거의 없다. 인사 이동 시 parent_id 하나만 바꾸면 되니까 구조 변경이 간단하다.
- 조직 내 모든 하위 구성원을 빠르게 조회해야 하는 권한 시스템이 있으면 **클로저 테이블**을 고려한다.

### 댓글 트리 (대댓글)

댓글은 INSERT가 빈번하다. 사용자가 댓글을 달 때마다 트리에 노드가 추가된다. 조회도 자주 일어난다.

- **인접 리스트**가 가장 많이 쓰인다. INSERT가 빠르고 구현이 단순하다. 대부분의 서비스에서 댓글 깊이를 2~3단계로 제한하기 때문에 재귀 CTE의 비용이 거의 없다.
- 댓글 깊이에 제한이 없는 서비스(Reddit 스타일)에서는 **경로 열거**가 괜찮다. path로 정렬하면 트리 순서대로 댓글을 표시할 수 있다. 다만 path 길이 제한에 주의해야 한다.

### 파일/폴더 구조

path 기반으로 조회하는 패턴이 자연스럽다.

- **경로 열거**가 잘 맞는다. 파일 시스템 자체가 경로 기반이라서 모델링이 직관적이다. `/documents/project/design/` 같은 경로로 LIKE 조회하면 하위 항목이 바로 나온다.

---

## MySQL과 PostgreSQL의 재귀 CTE

인접 리스트 방식에서 트리 전체를 조회하려면 재귀 CTE가 필수다. MySQL 8.0부터 지원하고, PostgreSQL은 8.4부터 지원한다.

### 기본 문법

MySQL과 PostgreSQL 모두 `WITH RECURSIVE` 문법은 동일하다.

```sql
WITH RECURSIVE tree AS (
    -- 앵커 멤버: 시작 노드
    SELECT id, name, parent_id, 0 AS depth, CAST(name AS CHAR(500)) AS path
    FROM category
    WHERE id = 1

    UNION ALL

    -- 재귀 멤버: 자식 노드 탐색
    SELECT c.id, c.name, c.parent_id, t.depth + 1,
           CONCAT(t.path, ' > ', c.name)
    FROM category c
    JOIN tree t ON c.parent_id = t.id
)
SELECT * FROM tree ORDER BY path;
```

### MySQL에서 주의할 점

MySQL은 재귀 CTE의 최대 반복 횟수가 기본 1000번이다.

```sql
-- 기본값 확인
SHOW VARIABLES LIKE 'cte_max_recursion_depth';

-- 세션 단위로 변경
SET SESSION cte_max_recursion_depth = 10000;
```

트리 깊이가 1000을 넘는 경우는 드물지만, 데이터가 잘못 들어가서 순환 참조가 생기면 이 제한에 걸린다. 순환 참조 방지 로직을 애플리케이션 레벨에서 넣어두는 게 좋다.

MySQL의 재귀 CTE는 내부적으로 임시 테이블을 사용한다. 결과가 많으면 디스크 기반 임시 테이블로 전환되면서 느려진다. `tmp_table_size`와 `max_heap_table_size`를 확인한다.

### PostgreSQL에서의 활용

PostgreSQL은 재귀 CTE에 `CYCLE` 절을 지원한다(14 버전부터). 순환 참조를 자동으로 감지해서 무한 루프를 방지한다.

```sql
WITH RECURSIVE tree AS (
    SELECT id, name, parent_id, 0 AS depth
    FROM category
    WHERE id = 1

    UNION ALL

    SELECT c.id, c.name, c.parent_id, t.depth + 1
    FROM category c
    JOIN tree t ON c.parent_id = t.id
)
CYCLE id SET is_cycle USING cycle_path
SELECT * FROM tree WHERE NOT is_cycle;
```

14 이전 버전에서는 배열로 방문한 노드를 추적해서 직접 순환을 감지한다.

```sql
WITH RECURSIVE tree AS (
    SELECT id, name, parent_id, ARRAY[id] AS visited
    FROM category
    WHERE id = 1

    UNION ALL

    SELECT c.id, c.name, c.parent_id, t.visited || c.id
    FROM category c
    JOIN tree t ON c.parent_id = t.id
    WHERE c.id != ALL(t.visited)  -- 순환 방지
)
SELECT id, name FROM tree;
```

### PostgreSQL의 ltree 확장

PostgreSQL에는 `ltree`라는 확장 모듈이 있다. 경로 열거 방식을 네이티브로 지원한다.

```sql
CREATE EXTENSION IF NOT EXISTS ltree;

CREATE TABLE category (
    id   BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100) NOT NULL,
    path ltree NOT NULL
);

CREATE INDEX idx_category_path_gist ON category USING GIST (path);

INSERT INTO category (id, name, path) OVERRIDING SYSTEM VALUE VALUES
(1, '전자제품', '1'),
(2, '컴퓨터', '1.2'),
(3, '노트북', '1.2.3'),
(4, '게이밍 노트북', '1.2.3.4'),
(5, '데스크탑', '1.2.5'),
(6, '스마트폰', '1.6');
```

ltree 전용 연산자로 조회한다.

```sql
-- 하위 트리 조회: @> (조상이 후손을 포함하는지)
SELECT * FROM category WHERE path <@ '1.2';

-- 특정 패턴 매치
SELECT * FROM category WHERE path ~ '1.2.*{1}';
-- depth 1인 직속 자식만

-- 최소 공통 조상
SELECT lca(path) FROM category WHERE id IN (4, 5);
```

GiST 인덱스를 타기 때문에 LIKE보다 성능이 좋다. PostgreSQL을 쓴다면 경로 열거 방식 대신 ltree를 쓰는 게 낫다.

---

## 마이그레이션: 인접 리스트에서 다른 방식으로 전환

서비스 초기에 인접 리스트로 시작했다가 트리 조회 성능이 문제가 되면 다른 방식으로 전환해야 하는 상황이 생긴다.

### 인접 리스트 → 클로저 테이블

기존 인접 리스트 데이터에서 클로저 테이블을 생성하는 쿼리다.

```sql
-- 클로저 테이블 생성
CREATE TABLE category_path (
    ancestor   BIGINT NOT NULL,
    descendant BIGINT NOT NULL,
    depth      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (ancestor, descendant)
);

-- 재귀 CTE로 모든 조상-후손 관계를 추출해서 삽입
WITH RECURSIVE closure AS (
    -- 자기 자신
    SELECT id AS ancestor, id AS descendant, 0 AS depth
    FROM category

    UNION ALL

    -- 부모를 따라 올라가면서 관계 추가
    SELECT cl.ancestor, c.id, cl.depth + 1
    FROM category c
    JOIN closure cl ON c.parent_id = cl.descendant
    WHERE cl.ancestor = cl.descendant  -- 직전 단계의 자기 자신 행만 확장
)
-- 위 CTE가 복잡하면 아래 방식이 더 직관적이다
INSERT INTO category_path (ancestor, descendant, depth)
WITH RECURSIVE tree AS (
    SELECT id, id AS root, 0 AS depth
    FROM category

    UNION ALL

    SELECT t.root, c.id, t.depth + 1
    FROM category c
    JOIN tree t ON c.parent_id = t.id
    -- 여기서 t.id는 "현재 탐색 중인 노드"
    -- 실제로는 root를 기준으로 모든 후손을 탐색
)
SELECT root, id, depth FROM tree;
```

실무에서는 이런 마이그레이션을 한 번에 하기보다는, 클로저 테이블을 먼저 만들어서 이중 쓰기(dual write)를 하고, 읽기를 점진적으로 전환하는 방식이 안전하다.

---

## 정리

| 기준 | 추천 방식 |
|------|----------|
| 구현이 간단해야 한다 | 인접 리스트 |
| 읽기가 대부분이고 쓰기가 거의 없다 | 중첩 집합 |
| 경로 기반 조회가 필요하다 | 경로 열거 (PostgreSQL이면 ltree) |
| 읽기/쓰기 균형 + 데이터 무결성 | 클로저 테이블 |
| 트리 깊이가 얕고(5단계 이하) 쓰기가 빈번하다 | 인접 리스트 + 재귀 CTE |

대부분의 경우 인접 리스트로 시작하는 게 맞다. 트리 조회가 병목이 되는 시점에 클로저 테이블이나 다른 방식으로 전환하면 된다. 처음부터 복잡한 방식을 도입하면 관리 비용이 올라가고, 실제로 성능 문제가 발생하지 않을 수도 있다.
