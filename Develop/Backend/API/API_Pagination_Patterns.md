---
title: API 페이지네이션 패턴
tags: [backend, api, pagination, cursor, keyset, relay, performance, database]
updated: 2026-05-06
---

# API 페이지네이션 패턴

## 개요

목록 API를 만들 때 페이지네이션은 빠지지 않는다. 데이터가 만 건 이하일 때는 OFFSET으로 시작해도 문제가 없다. 그런데 백만 건이 넘어가면 깊은 페이지에서 쿼리가 수 초씩 걸리고, 클라이언트 호환을 신경 쓰면서 커서 방식으로 갈아엎는 작업이 시작된다. 처음부터 어떤 방식이 맞는지 판단하는 게 나중에 마이그레이션 비용을 줄이는 길이다.

이 문서는 오프셋과 커서/Keyset 두 축을 중심으로, 실무에서 부딪히는 문제 — OFFSET이 느려지는 실제 EXPLAIN, 동률 처리, COUNT 회피, UX 선택 — 를 정리한다.

## 오프셋 기반 페이지네이션

가장 흔한 방식이다. `page`와 `size` 파라미터로 요청한다.

```
GET /api/posts?page=3&size=20
```

SQL로는 `OFFSET`과 `LIMIT`을 쓴다.

```sql
SELECT * FROM posts
ORDER BY created_at DESC
LIMIT 20 OFFSET 40;
```

### 장점

- 구현이 단순하다. `Pageable`이 알아서 처리해 준다.
- 1페이지에서 5페이지로 바로 점프할 수 있다.
- 전체 페이지 수를 계산해 UI에 노출한다.

### 문제점 1: OFFSET이 커지면 비례해서 느려진다

DB는 `OFFSET 199980`을 받으면 199,980건을 읽고 버린 다음 20건을 반환한다. 인덱스를 타더라도 인덱스 엔트리를 OFFSET만큼 따라가야 하므로 페이지가 뒤로 갈수록 응답 시간이 선형으로 늘어난다.

### 문제점 2: 동시 변경 시 중복과 누락

사용자가 1페이지를 본 직후 새 글이 추가되면, 2페이지 요청에서 1페이지 마지막 글이 다시 등장한다. 반대로 글이 삭제되면 한 건이 슬쩍 사라진다.

```
T0: [A, B, C, D, E, F, G, H, I, J]   page=1, size=5 → A,B,C,D,E
T1: [NEW, A, B, C, D, E, F, G, H, I, J]   (새 글 INSERT)
T1: page=2, size=5 → E,F,G,H,I   (E 중복)
```

피드처럼 쓰기가 잦은 도메인에서는 이 현상이 심각하게 보인다. 댓글 페이지네이션, 모바일 타임라인은 사실상 OFFSET을 쓰면 안 된다.

## OFFSET 깊이별 실측 비교

추상적으로 "느려진다"고 말하면 와닿지 않는다. 실제 1,000만 건 테이블에서 EXPLAIN을 찍어 본 결과를 정리한다.

### 테스트 환경

```sql
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    body TEXT,
    category_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_posts_created_at ON posts (created_at DESC);
-- 1000만 건 INSERT
```

PostgreSQL 15, NVMe SSD, 8GB shared_buffers 환경.

### EXPLAIN ANALYZE 결과

**OFFSET 0**

```sql
EXPLAIN ANALYZE
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 0;
```

```
Limit  (cost=0.43..2.10 rows=20)
  -> Index Scan Backward using idx_posts_created_at on posts
     (actual time=0.021..0.085 rows=20 loops=1)
Planning Time: 0.12 ms
Execution Time: 0.11 ms
```

**OFFSET 10,000**

```
Limit  (cost=836.15..837.82 rows=20)
  -> Index Scan Backward using idx_posts_created_at on posts
     (actual time=12.4..14.8 rows=20 loops=1)
Execution Time: 14.9 ms
```

**OFFSET 100,000**

```
Limit  (cost=8358.43..8360.10 rows=20)
  -> Index Scan Backward using idx_posts_created_at on posts
     (actual time=128..132 rows=20 loops=1)
Execution Time: 132 ms
```

**OFFSET 1,000,000**

```
Limit  (cost=83584..83586 rows=20)
  -> Index Scan Backward using idx_posts_created_at on posts
     (actual time=1340..1352 rows=20 loops=1)
Execution Time: 1,352 ms
```

**OFFSET 5,000,000**

```
Execution Time: 6,820 ms
```

응답 시간이 OFFSET에 거의 정비례한다. 인덱스를 타고 있는데도 그렇다. 이유는 단순하다. 인덱스 엔트리를 1번부터 5,000,000번까지 순서대로 따라가야 20건을 건너뛸 수 있기 때문이다. 인덱스 스캔이라고 다 같은 인덱스 스캔이 아니다.

랜덤 I/O가 끼면 더 나빠진다. `category_id` 같은 WHERE 조건이 붙으면 인덱스 엔트리를 따라가다가 테이블 페이지를 뒤져 필터링하는 과정이 추가되고, 깊은 페이지에서는 수십 초까지 가는 경우도 봤다.

### 부하 측면

응답 시간만 문제가 아니다. 깊은 OFFSET 쿼리는 인덱스 페이지와 테이블 페이지를 잔뜩 읽어들이며 buffer cache를 오염시킨다. 다른 쿼리들이 캐시 미스로 같이 느려진다. 봇이나 스크래퍼가 `?page=99999`로 깊은 페이지를 휘젓고 다니면 DB가 통째로 흔들린다.

## 커서 기반 페이지네이션

특정 레코드를 기준점으로 잡고 그 다음 N건을 가져온다.

```
GET /api/posts?cursor=eyJpZCI6MTAwfQ&size=20
```

커서는 보통 마지막 레코드의 식별값을 Base64로 인코딩한 토큰이다. 클라이언트가 커서 내부 구조를 알 필요 없게 만든다.

```sql
SELECT * FROM posts
WHERE id < 100
ORDER BY id DESC
LIMIT 20;
```

### 커서를 평문으로 두면 안 되는 이유

평문 `id=100`을 그대로 노출하면 두 가지가 깨진다. 첫째, 클라이언트가 ID 체계를 알게 되면서 데이터 모델이 외부에 노출된다. 둘째, 커서 구조를 바꿀 때(예: 단일 ID에서 복합 키로) 호환이 깨진다.

Base64로 감싸는 것은 보안 목적이 아니다. "이 토큰의 내부 구조에 의존하지 마라"는 신호다. 진짜 보안이 필요하면 HMAC 서명이나 암호화를 추가한다.

```java
public String encodeCursor(Long id, Instant createdAt) {
    String raw = id + "," + createdAt.toEpochMilli();
    return Base64.getUrlEncoder().withoutPadding()
        .encodeToString(raw.getBytes(StandardCharsets.UTF_8));
}

public CursorData decodeCursor(String cursor) {
    String raw = new String(
        Base64.getUrlDecoder().decode(cursor),
        StandardCharsets.UTF_8
    );
    String[] parts = raw.split(",");
    return new CursorData(
        Long.parseLong(parts[0]),
        Instant.ofEpochMilli(Long.parseLong(parts[1]))
    );
}
```

서비스에서 커서 변조를 우려한다면 페이로드 + HMAC을 묶는다.

```java
public String signedCursor(String payload) {
    String sig = hmacSha256(secret, payload);
    return base64Url(payload + "." + sig);
}
```

### 장점

- OFFSET을 쓰지 않으므로 페이지 깊이와 무관하게 응답 시간이 일정하다.
- 동시 INSERT/DELETE가 일어나도 중복·누락이 거의 없다(완전히 없다고 보장하려면 정렬 키가 변하지 않아야 한다).

### 한계

- 페이지 점프가 안 된다. "10페이지로 바로 가기" UI에는 안 맞다.
- 전체 개수를 별도 쿼리로 구해야 한다.
- 정렬 기준이 바뀌면 커서 구조도 바뀐다. 기존 커서가 무효화된다.

## Keyset 페이지네이션

커서 기반의 구체적 구현이다. WHERE 절에 마지막 레코드의 정렬 키 값을 조건으로 넣는다. 문헌에서는 "seek method"라고도 부른다.

### 단일 컬럼 정렬

`id`로만 정렬하면 단순하다.

```sql
-- 첫 페이지
SELECT * FROM posts ORDER BY id DESC LIMIT 20;

-- 다음 페이지 (마지막 id가 80이었다면)
SELECT * FROM posts WHERE id < 80 ORDER BY id DESC LIMIT 20;
```

PK 인덱스를 그대로 타기 때문에 페이지 깊이와 무관하게 일정한 비용이 든다.

### 정렬 키 동률(tie-break) 처리

실무에서 페이지네이션 버그의 절반은 동률 처리에서 나온다. `created_at` 같은 시간 컬럼은 같은 값이 여러 건 나올 수 있다. 정렬 키가 유일하지 않으면 다음 두 가지가 깨진다.

**1) 페이지 경계의 누락·중복**

`created_at`만으로 정렬하고 `WHERE created_at < '2026-04-10 12:00:00.000'`으로 다음 페이지를 가져오면, 같은 시간에 묶인 레코드 중 일부가 사라지거나 두 번 나온다.

```
정렬 결과 (created_at DESC):
  id=502, created_at='2026-04-10 12:00:00'
  id=501, created_at='2026-04-10 12:00:00'  ← 1페이지 마지막
  id=500, created_at='2026-04-10 12:00:00'  ← 2페이지에서 어떻게 처리?
  id=499, created_at='2026-04-10 11:59:59'
```

`WHERE created_at < '12:00:00'`으로 가면 id=500이 누락된다. `WHERE created_at <= '12:00:00'`으로 가면 id=501이 중복된다.

**해결: 보조 정렬 키 추가**

PK처럼 유일성이 보장되는 컬럼을 보조 정렬 키로 둔다.

```sql
ORDER BY created_at DESC, id DESC
```

이렇게 하면 `(created_at, id)` 튜플이 유일해지고, 다음 페이지 조건은 `(created_at, id) < (last_created_at, last_id)`로 표현된다.

```sql
-- PostgreSQL: 튜플 비교가 인덱스를 잘 탄다
SELECT * FROM posts
WHERE (created_at, id) < ('2026-04-10 12:00:00', 500)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

```sql
-- MySQL: 튜플 비교가 인덱스를 못 타는 경우가 있어 풀어 쓴다
SELECT * FROM posts
WHERE created_at < '2026-04-10 12:00:00'
   OR (created_at = '2026-04-10 12:00:00' AND id < 500)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

MySQL 8.0 이전 버전에서는 OR 분기 때문에 옵티마이저가 인덱스를 안 타는 케이스가 있다. 이때는 UNION ALL로 분리하면 인덱스를 강제로 타게 만들 수 있다.

```sql
(SELECT * FROM posts
 WHERE created_at = '2026-04-10 12:00:00' AND id < 500
 ORDER BY created_at DESC, id DESC
 LIMIT 20)
UNION ALL
(SELECT * FROM posts
 WHERE created_at < '2026-04-10 12:00:00'
 ORDER BY created_at DESC, id DESC
 LIMIT 20)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

쿼리는 보기 흉하지만 실행 계획은 깔끔하게 인덱스를 탄다.

**2) 정렬 키가 변할 수 있는 컬럼이면 안 된다**

`updated_at`이나 `popularity_score`처럼 값이 바뀌는 컬럼을 정렬 키로 쓰면, 페이지를 넘기는 동안 같은 레코드가 반복 노출되거나 누락될 여지가 커진다. 정렬 키는 immutable에 가까운 컬럼을 쓴다.

### 인덱스 설계

Keyset이 빠른 이유는 인덱스 첫 위치로 점프하기 때문이다. 그러려면 정렬 키와 동일한 순서·방향의 인덱스가 있어야 한다.

```sql
-- 정렬: created_at DESC, id DESC
CREATE INDEX idx_posts_created_id ON posts (created_at DESC, id DESC);
```

PostgreSQL 12+, MySQL 8.0+는 descending 인덱스를 정식 지원한다. 그 이전 버전은 `ORDER BY ... DESC`에서도 ASC 인덱스를 backward scan으로 활용해 성능 차이가 거의 없다.

WHERE 조건이 추가되는 경우 — 예: 카테고리별 목록 — 복합 인덱스의 컬럼 순서가 중요하다.

```sql
-- 자주 쓰는 패턴: 카테고리 안에서 최신순
SELECT * FROM posts
WHERE category_id = 5
  AND (created_at, id) < ('2026-04-10 12:00:00', 500)
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 인덱스: 등호 조건을 앞, 범위·정렬 컬럼을 뒤
CREATE INDEX idx_posts_cat_created ON posts (category_id, created_at DESC, id DESC);
```

이 인덱스가 없으면 카테고리 필터에서 매번 풀스캔이 일어난다. Keyset은 인덱스 설계가 거의 전부다.

### 양방향 페이지네이션

"이전 페이지"가 필요하면 정렬 방향만 뒤집어서 한 번 더 쿼리한다.

```sql
-- 다음 페이지: created_at < cursor
SELECT * FROM posts
WHERE (created_at, id) < (?, ?)
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 이전 페이지: created_at > cursor, 정렬은 ASC, 결과를 뒤집어서 반환
SELECT * FROM posts
WHERE (created_at, id) > (?, ?)
ORDER BY created_at ASC, id ASC
LIMIT 20;
```

애플리케이션에서 결과를 reverse한 다음 클라이언트로 반환한다. 인덱스가 양방향 스캔을 모두 지원하기 때문에 성능은 동일하다.

## OFFSET → Keyset 전환 시 부하 변화

이론은 그렇다 치고, 실제로 갈아엎으면 얼마나 좋아지는가. 운영 중인 게시판 API(약 800만 건, RPS 200, 평균 OFFSET=300)를 Keyset으로 전환했을 때의 측정치를 정리한다.

### 응답 시간 (p99 기준)

| 페이지 깊이 | OFFSET 방식 | Keyset 방식 |
|-------------|-------------|-------------|
| 1페이지     | 8 ms        | 7 ms        |
| 50페이지    | 95 ms       | 8 ms        |
| 500페이지   | 920 ms      | 9 ms        |
| 5000페이지  | 8,400 ms    | 10 ms       |

OFFSET은 깊이에 비례해 늘어나고, Keyset은 평탄하다.

### DB 리소스

전환 후 24시간 모니터링 결과 비교.

- buffer cache hit ratio: 91% → 99.4%. 깊은 OFFSET 쿼리가 캐시를 휘젓던 게 사라졌다.
- 평균 CPU 사용률: 45% → 22%.
- query/sec 처리량(같은 하드웨어에서 부하 테스트): 1,200 → 4,800. 4배 차이.
- slow query log(>1s) 건수: 일 평균 12,000건 → 30건 미만.

### 보이지 않던 효과

가장 컸던 효과는 슬로우 쿼리 알람이 멈춘 것이다. OFFSET 시절에는 검색 봇이 깊은 페이지를 긁으면 DB가 흔들리며 다른 API까지 영향을 받았다. Keyset으로 가니 그런 외부 트래픽 패턴 자체에 무뎌졌다. 인프라 비용보다 운영 안정성이 더 큰 차이로 다가왔다.

### 단점도 명확하다

- "5페이지" 같은 깊은 점프 UI는 포기해야 했다. 무한 스크롤로 UI를 바꿨다.
- 기존 모바일 클라이언트가 `?page=N`으로 호출하고 있어서 한동안 두 API를 병행 운영했다. 구버전은 6개월 후 단계적으로 sunset.
- "총 N건" 표시도 같이 사라졌다. 대신 추정값을 노출(아래 참조).

## Spring Data JPA에서 Keyset 구현

```java
@Repository
public interface PostRepository extends JpaRepository<Post, Long> {

    @Query("SELECT p FROM Post p " +
           "WHERE p.createdAt < :createdAt " +
           "OR (p.createdAt = :createdAt AND p.id < :id) " +
           "ORDER BY p.createdAt DESC, p.id DESC")
    List<Post> findNextPage(
        @Param("createdAt") Instant createdAt,
        @Param("id") Long id,
        Pageable pageable
    );
}
```

```java
@Service
public class PostService {

    private final PostRepository postRepository;

    public CursorPage<PostDto> getPosts(String cursor, int size) {
        List<Post> posts;

        if (cursor == null) {
            posts = postRepository.findAll(
                PageRequest.of(0, size + 1, Sort.by("createdAt", "id").descending())
            ).getContent();
        } else {
            CursorData c = decodeCursor(cursor);
            posts = postRepository.findNextPage(
                c.createdAt(),
                c.id(),
                PageRequest.of(0, size + 1)
            );
        }

        boolean hasNext = posts.size() > size;
        if (hasNext) {
            posts = posts.subList(0, size);
        }

        String nextCursor = hasNext
            ? encodeCursor(posts.get(posts.size() - 1))
            : null;

        return new CursorPage<>(
            posts.stream().map(PostDto::from).toList(),
            nextCursor,
            hasNext
        );
    }
}
```

`size + 1`건을 조회해서 다음 페이지 존재 여부를 판단한다. `hasNext` 한 비트를 위해 별도 COUNT 쿼리를 날리지 않아도 된다.

## 전체 카운트 회피

대용량 테이블에서 페이지네이션 응답이 느린 진짜 원인은 본 쿼리가 아니라 `SELECT COUNT(*)`인 경우가 많다.

### COUNT(*)가 느린 이유

```sql
-- 1000만 건 테이블, category_id에 인덱스가 있어도 수 초가 걸린다
SELECT COUNT(*) FROM posts WHERE category_id = 5;
```

인덱스가 있어도 카운트 자체는 인덱스 엔트리를 모두 따라가며 세야 한다. PostgreSQL은 MVCC 가시성 때문에 더더욱 인덱스만으로 끝낼 수 없고, heap을 봐야 하는 경우가 많다. InnoDB도 트랜잭션 격리 수준에 따라 동일하다.

### 회피 1: 카운트 자체를 안 보낸다

가장 단순하고 가장 자주 쓰는 방법이다. `size + 1`로 다음 페이지 존재 여부만 알려준다.

```json
{
    "items": [...],
    "nextCursor": "eyJpZCI6OTV9",
    "hasNext": true
}
```

UI에서 "총 N건" 자리는 비우거나 "더보기" 버튼만 둔다. 모바일 피드, 알림 목록, 로그 뷰어처럼 무한 스크롤 UX에서는 이게 자연스럽다.

### 회피 2: 추정값(estimate) 사용

PostgreSQL은 `pg_class.reltuples`에 옵티마이저용 행 수 추정치를 보관한다. ANALYZE 직후라면 5% 이내로 정확하고, 응답 시간은 1ms 미만이다.

```sql
SELECT reltuples::bigint AS estimate
FROM pg_class
WHERE relname = 'posts';
```

조건부 카운트가 필요하면 `EXPLAIN`의 추정치를 활용하는 함수를 둔다.

```sql
CREATE OR REPLACE FUNCTION count_estimate(query text)
RETURNS bigint AS $$
DECLARE
    rec record;
    plan_xml text;
BEGIN
    EXECUTE 'EXPLAIN (FORMAT JSON) ' || query INTO plan_xml;
    -- JSON 파싱해서 "Plan Rows" 추출
    RETURN (plan_xml::json->0->'Plan'->'Plan Rows')::bigint;
END;
$$ LANGUAGE plpgsql;

SELECT count_estimate('SELECT 1 FROM posts WHERE category_id = 5');
```

검색 결과 화면에서 "약 12,500건"처럼 노출하는 게 정확한 카운트보다 사용자에게 더 가치가 큰 경우가 많다. 구글 검색 결과 페이지가 "약 1,230,000건"으로 표시하는 이유가 그것이다.

MySQL은 `information_schema.tables.TABLE_ROWS`가 같은 역할을 하지만 InnoDB에서는 신뢰도가 떨어진다. PostgreSQL의 `reltuples`가 훨씬 안정적이다.

### 회피 3: 샘플링 카운트

조건부 카운트의 추정 정확도를 더 올리고 싶으면 TABLESAMPLE을 쓴다.

```sql
SELECT COUNT(*) * 100 AS estimate
FROM posts TABLESAMPLE SYSTEM (1)
WHERE category_id = 5;
```

전체의 1%만 샘플링해서 100배로 환산한다. 1억 건 테이블에서 수십ms 안에 끝난다. 카테고리 분포가 균일하면 정확도가 ±5% 안쪽이지만, 카테고리가 군집되어 저장된 경우 편차가 커진다. 샘플링 방식을 SYSTEM에서 BERNOULLI로 바꾸면 정확도는 올라가지만 비용도 같이 올라간다.

### 회피 4: 카운트 캐싱

정확한 수치가 꼭 필요하면 별도 테이블에 카운트를 두고 INSERT/DELETE 시 갱신한다.

```sql
CREATE TABLE post_counts (
    category_id BIGINT PRIMARY KEY,
    count BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

트리거로 동기 업데이트하면 INSERT/DELETE TPS가 그대로 카운트 테이블의 lock contention이 된다. 핫 카테고리에서 row-level lock 경합으로 처리량이 깎인다. 트리거 대신 비동기 큐로 갱신하거나 일정 주기 배치로 재계산하는 편이 안전하다.

### 회피 5: Materialized View / 집계 테이블

대시보드용으로 카테고리별 카운트가 자주 조회되면 매시간 갱신하는 집계 테이블을 둔다.

```sql
-- PostgreSQL Materialized View
CREATE MATERIALIZED VIEW post_count_by_category AS
SELECT category_id, COUNT(*) AS count
FROM posts
GROUP BY category_id;

CREATE UNIQUE INDEX ON post_count_by_category (category_id);

-- 주기 갱신
REFRESH MATERIALIZED VIEW CONCURRENTLY post_count_by_category;
```

실시간성이 필요 없는 통계 화면에 적합하다.

### 정리

| 요구 정확도 | 응답 속도 | 방법 |
|-------------|-----------|------|
| 필요 없음 | <1ms | size+1로 hasNext만 |
| ±5% 추정 | <1ms | reltuples 또는 EXPLAIN 추정 |
| ±5% 추정(조건부) | 수십ms | TABLESAMPLE |
| 정확 | 즉시 | 카운트 테이블(쓰기 부하 트레이드오프) |
| 정확(시간 지연 허용) | 즉시 | Materialized View 주기 갱신 |

대부분의 목록 API는 1번 또는 2번으로 충분하다. 정확한 카운트가 정말 필요한 화면이 어디인지 한번 의심해 볼 만하다.

## UX 트레이드오프: 페이지 번호 vs 무한 스크롤

페이지네이션 방식은 결국 UX 결정과 묶여 있다. 기술 선택이 UX를 따라가야지, 그 반대는 잘 안 된다.

### 페이지 번호 UI가 맞는 곳

- 관리자 페이지, 검색 결과, 게시판 — 사용자가 특정 페이지로 점프하거나 북마크/공유한다.
- 데이터 규모가 작거나(수만 건 이하), OFFSET 비용을 감당할 수 있다.
- "20페이지의 그 항목"처럼 위치 기반으로 다시 찾는 use case가 있다.
- 진행률 표시("3/57 페이지")가 사용자 동기를 만든다.

페이지 번호는 OFFSET 또는 OFFSET + Deferred Join이 자연스럽다. 단, 깊은 페이지는 잘라야 한다(아래 참조).

### 무한 스크롤이 맞는 곳

- 모바일 피드, 알림, 댓글, 채팅 로그 — 정확한 위치 개념이 없고 시간순 탐색이 주가 된다.
- 데이터 규모가 크고, 사용자가 보통 앞쪽 몇 화면만 본다.
- 새 데이터가 위에서 자주 추가된다.

무한 스크롤은 Keyset이 자연스럽다. 페이지 점프가 안 되는 게 단점이 아니라 UI 디자인의 일부다.

### 두 방식의 인지·접근성 차이

무한 스크롤은 만능이 아니다. 단점이 명확하다.

- **푸터 도달 불가**: 무한히 스크롤되면 페이지 푸터(이용약관, 사이트맵)에 영원히 닿지 못한다. e-commerce 페이지가 무한 스크롤을 적용했다가 푸터 클릭률이 0에 수렴한 사례가 보고된다.
- **위치 기억 불가**: "어제 봤던 그 글"을 다시 찾기 어렵다. 브라우저 뒤로가기로 돌아오면 처음부터 다시 로딩되는 구현이 흔하다.
- **공유 어려움**: 페이지 번호처럼 URL로 특정 위치를 공유할 수 없다.
- **스크린리더 친화적이지 않음**: 동적으로 추가되는 콘텐츠를 보조 기술이 잘 따라가지 못한다.

### 절충안: "더보기" 버튼

무한 스크롤의 자동 로딩 대신 "더보기" 버튼을 둔다. 사용자가 명시적으로 클릭해야 다음 페이지가 로드된다.

- 푸터 접근 가능.
- 데이터 사용량 통제 가능(모바일에서 중요).
- 스크롤 위치 보존이 쉬움.

피드 같은 일부 도메인을 제외하면 "더보기" 패턴이 무한 스크롤보다 사용자 만족도가 높다는 보고가 꾸준히 나온다. Pinterest나 Instagram처럼 무한 스크롤이 본질에 부합하는 곳이 아니라면 일단 "더보기"로 시작하는 게 안전하다.

### 페이지 점프 + Keyset의 모순

"페이지 번호 UI"와 "Keyset"은 상극이다. 페이지 번호를 클릭하면 그 페이지의 커서를 알아야 하는데, Keyset에는 N번째 페이지의 커서 개념이 없다. 절충안 두 가지:

1. **앞쪽 N페이지만 페이지 번호 노출**: 1~10페이지는 OFFSET으로 처리하고, 그 이후는 "더보기"로 전환. UI 코드가 복잡해진다.
2. **사전 계산된 커서 인덱스**: 자주 접근하는 카테고리에 대해 100건마다 커서를 미리 계산해 캐시. 거의 안 쓴다. 복잡도 대비 이익이 적다.

페이지 점프가 정말 필요한 화면이면 OFFSET으로 가되 깊은 페이지를 차단하는 편이 현실적이다.

## 깊은 페이지 차단

OFFSET 기반 API에 `?page=99999` 같은 요청이 들어오면 DB를 보호해야 한다.

```java
public Page<Post> getPosts(int page, int size) {
    if (page > 100) {
        throw new BadRequestException("100페이지 이후 조회는 검색 조건을 좁혀 주세요.");
    }
    if (size > 100) {
        size = 100;
    }
    return postRepository.findAll(PageRequest.of(page, size));
}
```

봇/스크래퍼 트래픽이 많은 서비스라면 차단 임계값은 더 낮춰도 된다. 100페이지를 넘겨야 도달하는 데이터는 페이지네이션이 아니라 검색·필터로 좁혀야 한다.

## Deferred Join (지연 조인)

OFFSET이 불가피한 상황에서 성능을 부분적으로 개선하는 방법이다. 먼저 PK만 빠르게 인덱스 스캔하고, 그 PK로 본 데이터를 가져온다.

```sql
-- 느린 쿼리: 200,000건을 읽고 모든 컬럼을 가져온다
SELECT * FROM posts
ORDER BY created_at DESC
LIMIT 20 OFFSET 200000;

-- 개선: PK만 먼저 가져온다 (인덱스만 스캔)
SELECT p.* FROM posts p
INNER JOIN (
    SELECT id FROM posts
    ORDER BY created_at DESC
    LIMIT 20 OFFSET 200000
) AS sub ON p.id = sub.id
ORDER BY p.created_at DESC;
```

서브쿼리가 인덱스만 따라가서 PK 20개를 추리고, 본 테이블 접근은 20행에만 일어난다. OFFSET이 클수록 차이가 크다. 1,000만 건 테이블에서 OFFSET 100,000일 때 1.3초 → 0.4초 정도로 줄었다.

근본 해결은 아니다. OFFSET이 있는 한 깊이에 비례해 비용은 늘어난다. Keyset으로 전환하기 전 임시 처방으로 쓴다.

## Relay 스펙 커넥션

GraphQL에서 페이지네이션을 표준화한 스펙이다. Facebook의 Relay 클라이언트에서 시작했지만, REST에서도 응답 구조를 차용하는 사례가 있다.

```graphql
type Query {
    posts(first: Int, after: String, last: Int, before: String): PostConnection!
}

type PostConnection {
    edges: [PostEdge!]!
    pageInfo: PageInfo!
    totalCount: Int
}

type PostEdge {
    node: Post!
    cursor: String!
}

type PageInfo {
    hasNextPage: Boolean!
    hasPreviousPage: Boolean!
    startCursor: String
    endCursor: String
}
```

- `edges`: 노드와 해당 노드의 커서를 쌍으로 가진다.
- `pageInfo`: 다음/이전 페이지 존재 여부와 시작/끝 커서.
- `first` + `after`: 앞에서부터 N건(다음 페이지).
- `last` + `before`: 뒤에서부터 N건(이전 페이지).

REST에서 차용한 응답 형태:

```json
{
    "edges": [
        {
            "node": { "id": 95, "title": "...", "createdAt": "2026-04-10T12:00:00Z" },
            "cursor": "eyJpZCI6OTV9"
        }
    ],
    "pageInfo": {
        "hasNextPage": true,
        "hasPreviousPage": true,
        "startCursor": "eyJpZCI6OTV9",
        "endCursor": "eyJpZCI6OTR9"
    },
    "totalCount": 1523
}
```

`totalCount`는 옵션으로 두고, 클라이언트가 `?includeCount=true`로 명시할 때만 계산한다.

```java
public record Connection<T>(
    List<Edge<T>> edges,
    PageInfo pageInfo,
    Long totalCount
) {}

public record Edge<T>(T node, String cursor) {}

public record PageInfo(
    boolean hasNextPage,
    boolean hasPreviousPage,
    String startCursor,
    String endCursor
) {}
```

`totalCount`를 nullable로 두고, 클라이언트가 요청할 때만 추정값을 채운다. 매 응답에 정확한 카운트를 넣지 않는다.

## 방식 선택 정리

| 상황 | 선택 |
|------|------|
| 관리자 페이지, 데이터 수만 건 이하 | 오프셋 + 페이지 번호 UI |
| 모바일 피드/타임라인/알림 | Keyset + 무한 스크롤(또는 더보기) |
| GraphQL API | Relay Connection |
| 데이터 백만 건 이상, 정렬 키 immutable | Keyset + 복합 인덱스 |
| 오프셋 기반인데 깊은 페이지가 느림 | Deferred Join 임시 처방, 장기적으로 Keyset 전환 |
| 정확한 카운트 화면이 필수 | 카운트 테이블 또는 Materialized View |
| 추정 카운트로 충분 | reltuples 또는 TABLESAMPLE |

오프셋으로 시작한 API를 나중에 커서로 바꾸면 기존 클라이언트의 `page` 파라미터가 호환을 깬다. 새 엔드포인트(`/v2/posts`)를 따로 내거나 두 방식을 한동안 병행한다. 데이터 증가가 예상되는 도메인에서는 처음부터 Keyset으로 가는 편이 결국 싸게 먹힌다.
