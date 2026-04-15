---
title: API 페이지네이션 패턴
tags: [backend, api, pagination, cursor, keyset, relay, performance, database]
updated: 2026-04-15
---

# API 페이지네이션 패턴

## 개요

목록 API를 만들 때 페이지네이션은 빠지지 않는다. 오프셋 기반으로 시작했다가 데이터가 수백만 건이 되면 성능 문제에 부딪힌다. 커서 기반으로 바꾸려고 하면 기존 클라이언트 호환 문제가 생긴다. 처음부터 어떤 방식을 선택할지 판단하는 게 중요하다.

## 오프셋 기반 페이지네이션

가장 흔한 방식이다. `page`와 `size` 파라미터로 요청한다.

```
GET /api/posts?page=3&size=20
```

SQL로는 `OFFSET`과 `LIMIT`을 사용한다.

```sql
SELECT * FROM posts
ORDER BY created_at DESC
LIMIT 20 OFFSET 40;
```

### 장점

- 구현이 단순하다.
- 클라이언트에서 특정 페이지로 바로 이동할 수 있다. (1페이지 → 5페이지 건너뛰기)
- 전체 페이지 수를 계산해서 UI에 보여줄 수 있다.

### 문제점

**1. OFFSET이 커지면 느려진다**

데이터베이스는 OFFSET 40만 건이면, 40만 건을 읽고 버린 다음 20건을 반환한다. 페이지가 뒤로 갈수록 쿼리가 느려지는 이유다.

```sql
-- 1페이지: 빠르다
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 0;

-- 10000페이지: 199,980건을 읽고 버린다
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 199980;
```

MySQL의 `EXPLAIN`으로 확인하면 rows scanned가 OFFSET 값만큼 증가하는 것을 볼 수 있다.

**2. 데이터 변경 시 중복/누락이 발생한다**

사용자가 2페이지를 보는 사이에 새 글이 추가되면, 3페이지 요청 시 2페이지에서 봤던 글이 다시 나온다. 반대로 글이 삭제되면 한 건을 건너뛰게 된다.

```
시점 1: [A, B, C, D, E, F, G, H, I, J] (page=1, size=5 → A~E)
시점 2: [NEW, A, B, C, D, E, F, G, H, I, J] (새 글 추가)
시점 2: page=2, size=5 → E, F, G, H, I  (E가 중복)
```

## 커서 기반 페이지네이션

특정 레코드를 기준점(커서)으로 잡고, 그 다음 N건을 가져오는 방식이다.

```
GET /api/posts?cursor=eyJpZCI6MTAwfQ&size=20
```

커서는 보통 마지막 레코드의 식별값을 Base64 인코딩한 값이다. 클라이언트가 커서 내부 구조를 알 필요 없게 만든다.

```sql
-- 커서가 가리키는 id=100 이후의 20건
SELECT * FROM posts
WHERE id < 100
ORDER BY id DESC
LIMIT 20;
```

### 커서 인코딩

커서를 평문으로 넘기면 클라이언트가 값을 임의로 조작할 수 있다. Base64로 인코딩하는 이유는 보안이 아니라, 커서가 불투명(opaque)한 토큰이라는 것을 명시하기 위해서다.

```java
// 커서 생성
public String encodeCursor(Long id, Instant createdAt) {
    String raw = id + "," + createdAt.toEpochMilli();
    return Base64.getUrlEncoder().encodeToString(raw.getBytes());
}

// 커서 디코딩
public CursorData decodeCursor(String cursor) {
    String raw = new String(Base64.getUrlDecoder().decode(cursor));
    String[] parts = raw.split(",");
    return new CursorData(
        Long.parseLong(parts[0]),
        Instant.ofEpochMilli(Long.parseLong(parts[1]))
    );
}
```

### 장점

- OFFSET을 쓰지 않으므로 몇 페이지를 넘기든 일정한 속도를 보인다.
- 중간에 데이터가 추가/삭제되어도 중복이나 누락이 발생하지 않는다.

### 문제점

- 특정 페이지로 바로 이동할 수 없다. 무한 스크롤 UI에는 맞지만, 페이지 번호를 보여주는 UI에는 안 맞다.
- 전체 개수를 별도 쿼리로 구해야 한다.
- 정렬 기준이 바뀌면 커서 구조도 바뀐다.

## Keyset 페이지네이션

커서 기반 페이지네이션의 구체적인 구현 방식 중 하나다. WHERE 절에 정렬 컬럼의 마지막 값을 조건으로 넣는다. "seek method"라고도 부른다.

### 단일 컬럼 정렬

`id`로 정렬하는 경우가 가장 단순하다.

```sql
-- 첫 페이지
SELECT * FROM posts ORDER BY id DESC LIMIT 20;

-- 다음 페이지 (마지막 id가 80이었다면)
SELECT * FROM posts WHERE id < 80 ORDER BY id DESC LIMIT 20;
```

인덱스가 `id`에 걸려 있으면 항상 인덱스 스캔으로 처리된다. OFFSET처럼 앞의 데이터를 건너뛸 필요가 없다.

### 복합 컬럼 정렬

`created_at`으로 정렬하는데 같은 시간에 여러 건이 있을 수 있다면, 보조 정렬 컬럼이 필요하다. 보통 PK를 보조 컬럼으로 쓴다.

```sql
-- created_at DESC, id DESC로 정렬
-- 마지막 레코드: created_at='2026-04-10 12:00:00', id=500

SELECT * FROM posts
WHERE (created_at, id) < ('2026-04-10 12:00:00', 500)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

이 쿼리가 제대로 동작하려면 복합 인덱스가 있어야 한다.

```sql
CREATE INDEX idx_posts_created_id ON posts (created_at DESC, id DESC);
```

**주의**: MySQL에서 튜플 비교 `(a, b) < (x, y)`는 인덱스를 제대로 타지 못하는 경우가 있다. 이때는 풀어서 작성한다.

```sql
SELECT * FROM posts
WHERE created_at < '2026-04-10 12:00:00'
   OR (created_at = '2026-04-10 12:00:00' AND id < 500)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

PostgreSQL은 튜플 비교가 인덱스를 잘 활용한다. DB 엔진에 따라 실행 계획을 확인해야 한다.

### Spring Data JPA에서 Keyset 구현

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
            CursorData cursorData = decodeCursor(cursor);
            posts = postRepository.findNextPage(
                cursorData.createdAt(),
                cursorData.id(),
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

`size + 1`건을 조회해서 다음 페이지 존재 여부를 판단하는 방식이다. 별도의 COUNT 쿼리를 실행하지 않아도 된다.

## Relay 스펙 커넥션

GraphQL에서 페이지네이션을 표준화한 스펙이다. Facebook의 Relay 클라이언트에서 시작했지만, REST API에서도 이 구조를 차용하는 경우가 있다.

### 구조

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

- `edges`: 각 노드와 해당 노드의 커서를 쌍으로 가진다.
- `pageInfo`: 다음/이전 페이지 존재 여부와 시작/끝 커서를 담는다.
- `first` + `after`: 앞에서부터 N건 (다음 페이지)
- `last` + `before`: 뒤에서부터 N건 (이전 페이지)

### 쿼리 예시

```graphql
# 첫 페이지: 최신 20건
{
    posts(first: 20) {
        edges {
            node {
                id
                title
                createdAt
            }
            cursor
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}

# 다음 페이지: endCursor 이후 20건
{
    posts(first: 20, after: "eyJpZCI6ODB9") {
        edges {
            node { id, title, createdAt }
            cursor
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
```

### REST API에서 Relay 구조 차용

REST에서도 이 응답 구조를 그대로 쓸 수 있다. 일관성 있는 페이지네이션 응답 형식이 필요할 때 유용하다.

```json
{
    "edges": [
        {
            "node": { "id": 95, "title": "...", "createdAt": "2026-04-10T12:00:00Z" },
            "cursor": "eyJpZCI6OTV9"
        },
        {
            "node": { "id": 94, "title": "...", "createdAt": "2026-04-10T11:30:00Z" },
            "cursor": "eyJpZCI6OTR9"
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

### Java 구현

```java
public record Connection<T>(
    List<Edge<T>> edges,
    PageInfo pageInfo,
    int totalCount
) {}

public record Edge<T>(
    T node,
    String cursor
) {}

public record PageInfo(
    boolean hasNextPage,
    boolean hasPreviousPage,
    String startCursor,
    String endCursor
) {}
```

```java
public <T extends Identifiable> Connection<T> toConnection(
        List<T> items, int size, boolean hasNext, boolean hasPrevious) {

    List<Edge<T>> edges = items.stream()
        .map(item -> new Edge<>(item, encodeCursor(item.getId())))
        .toList();

    PageInfo pageInfo = new PageInfo(
        hasNext,
        hasPrevious,
        edges.isEmpty() ? null : edges.get(0).cursor(),
        edges.isEmpty() ? null : edges.get(edges.size() - 1).cursor()
    );

    return new Connection<>(edges, pageInfo, -1);
}
```

`totalCount`는 대용량 테이블에서 `COUNT(*)`가 느리기 때문에, 필요한 경우에만 별도로 구한다. `-1`이나 `null`로 두고 클라이언트가 명시적으로 요청할 때만 계산하는 방식이 현실적이다.

## 대용량 데이터에서의 성능 문제

### COUNT(*) 문제

전체 건수를 구하는 `COUNT(*)` 쿼리가 페이지네이션에서 가장 비싼 쿼리인 경우가 많다.

```sql
-- 1000만 건 테이블에서 이 쿼리는 수 초가 걸릴 수 있다
SELECT COUNT(*) FROM posts WHERE category_id = 5;
```

**대응 방법**

1. **카운트를 포기한다**: "총 N건" 대신 "다음 페이지 있음/없음"만 보여준다. `size + 1`건 조회 방식으로 처리한다.

2. **근사치를 사용한다**: PostgreSQL에서는 테이블 통계를 활용할 수 있다.

```sql
-- PostgreSQL: 대략적인 행 수 (ANALYZE 후 정확도 올라감)
SELECT reltuples::bigint AS estimate
FROM pg_class
WHERE relname = 'posts';
```

3. **카운트 캐싱**: 별도 테이블에 카운트를 저장하고, 데이터 변경 시 갱신한다.

```sql
CREATE TABLE post_counts (
    category_id BIGINT PRIMARY KEY,
    count BIGINT NOT NULL DEFAULT 0
);

-- 트리거나 애플리케이션 레벨에서 관리
```

실시간 정확도가 필요 없으면 1번, 대략적인 수치라도 보여줘야 하면 2번, 정확한 수치가 필요하면 3번을 쓴다.

### 깊은 페이지 접근

오프셋 기반에서 `page=100000`처럼 깊은 페이지 요청이 들어올 수 있다. 이걸 그대로 허용하면 DB에 부하가 걸린다.

**대응 방법**

1. **최대 페이지를 제한한다**: 보통 100페이지 이후는 차단하고, 검색 조건을 좁히도록 유도한다.

```java
public Page<Post> getPosts(int page, int size) {
    if (page > 100) {
        throw new BadRequestException("100페이지까지만 조회할 수 있습니다.");
    }
    return postRepository.findAll(PageRequest.of(page, size));
}
```

2. **커서 기반으로 전환한다**: 무한 스크롤이나 "더보기" UI에서는 커서 기반이 맞다.

3. **하이브리드 방식**: 앞쪽 페이지는 오프셋 기반으로, 뒤쪽 페이지는 커서 기반으로 처리한다. 구현 복잡도가 올라가므로 꼭 필요한 경우에만 쓴다.

### 정렬 컬럼의 인덱스

페이지네이션 성능은 결국 정렬 컬럼에 인덱스가 있느냐에 달려 있다. 인덱스 없이 `ORDER BY created_at DESC`를 걸면 전체 테이블을 스캔한다.

```sql
-- 이 인덱스가 없으면 페이지네이션이 느려진다
CREATE INDEX idx_posts_created_at ON posts (created_at DESC);

-- WHERE 조건이 있으면 복합 인덱스
CREATE INDEX idx_posts_category_created ON posts (category_id, created_at DESC);
```

커버링 인덱스를 활용하면 테이블 접근 없이 인덱스만으로 결과를 반환할 수 있다.

```sql
-- id, title, created_at만 SELECT하면 커버링 인덱스로 처리된다
CREATE INDEX idx_posts_covering
ON posts (created_at DESC, id, title);
```

다만 커버링 인덱스는 인덱스 크기가 커지므로, SELECT하는 컬럼이 적은 목록 API에서만 효과가 있다.

### Deferred Join (지연 조인)

OFFSET이 불가피한 상황에서 성능을 개선하는 방법이다. 먼저 PK만 빠르게 조회하고, 그 PK로 나머지 데이터를 가져온다.

```sql
-- 느린 쿼리: 200000건을 읽고 모든 컬럼을 가져온다
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

서브쿼리에서 `id`만 가져오므로 인덱스만 스캔하고, 실제 데이터는 20건에 대해서만 테이블에 접근한다. OFFSET이 크면 체감 차이가 확연하다.

## 방식 선택 기준

| 상황 | 선택 |
|------|------|
| 관리자 페이지, 데이터 수만 건 이하 | 오프셋 기반 (페이지 번호 UI) |
| 모바일 피드, 타임라인, 무한 스크롤 | 커서 기반 (Keyset) |
| GraphQL API | Relay Connection 스펙 |
| 데이터 수백만 건, 정렬 기준 변동 없음 | Keyset + 복합 인덱스 |
| 오프셋 기반인데 느려진 경우 | Deferred Join 적용 후, 근본적으로는 커서 기반 전환 검토 |

오프셋 기반으로 시작한 API를 나중에 커서 기반으로 바꾸면, 기존 클라이언트가 `page` 파라미터를 보내고 있어서 호환이 깨진다. 새 API를 만들거나 버전을 올려서 대응해야 한다. 처음부터 데이터 증가 추이를 예측하고 방식을 정하는 게 리워크를 줄이는 방법이다.
