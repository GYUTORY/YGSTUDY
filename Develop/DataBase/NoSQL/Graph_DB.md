---
title: Graph DB 관계 모델
tags: [database, nosql]
updated: 2026-07-28
---

# Graph DB 관계 모델

## Property Graph Model

그래프 데이터베이스는 데이터를 **노드(Node)**, **엣지(Edge)**, **레이블(Label)**, **프로퍼티(Property)** 네 가지 요소로 구성한다.

```
[노드: User]        [엣지: FOLLOWS]       [노드: User]
  id: 1       ──────────────────────────>   id: 2
  name: "Alice"    since: "2024-01-15"      name: "Bob"
  age: 30                                   age: 25
```

**노드**는 엔티티를 나타낸다. RDBMS의 row에 해당하지만, 고정 스키마가 없어서 같은 레이블을 가진 노드끼리도 프로퍼티 집합이 다를 수 있다.

**레이블**은 노드의 타입을 구분한다. 하나의 노드가 여러 레이블을 가질 수 있다. `User`, `Admin` 레이블을 동시에 붙이는 식이다.

**엣지**는 두 노드 사이의 관계를 나타낸다. RDBMS에서 외래키로 암묵적으로 표현하던 것을 엣지는 명시적 관계 타입으로 드러낸다. 중요한 점은 엣지에도 프로퍼티를 붙일 수 있다는 것이다. `FOLLOWS` 관계에 `since`, `weight` 같은 속성을 저장한다.

**프로퍼티**는 노드와 엣지 모두에 key-value 형태로 붙는다. 인덱스를 걸 수 있고 쿼리 조건으로 사용한다.

---

## RDBMS JOIN vs 그래프 Traversal

관계형 데이터베이스에서 "A를 팔로우하는 사람 중에서 B도 팔로우하는 사람"을 조회하려면 다음처럼 된다.

```sql
-- RDBMS
SELECT u.id, u.name
FROM users u
JOIN follows f1 ON u.id = f1.follower_id AND f1.following_id = 1
JOIN follows f2 ON u.id = f2.follower_id AND f2.following_id = 2;
```

이 쿼리는 `follows` 테이블 전체를 두 번 스캔하고 조인한다. 데이터가 수천만 건이 되면 인덱스가 있어도 성능이 떨어진다.

그래프 DB는 출발 노드에서 엣지를 따라 이동하는 traversal 방식이다.

```cypher
-- Cypher (Neo4j)
MATCH (a:User {id: 1})<-[:FOLLOWS]-(common)-[:FOLLOWS]->(b:User {id: 2})
RETURN common.id, common.name
```

Traversal은 인덱스로 시작 노드를 찾은 뒤, 이미 해시된 인접 노드 목록을 따라간다. JOIN처럼 전체 테이블을 스캔하지 않는다. "친구의 친구의 친구" 같은 다단계 관계에서 RDBMS는 JOIN을 반복해야 하지만, Cypher는 깊이를 파라미터로 조정한다.

```cypher
-- 최대 4단계 이내 연결된 사용자
MATCH (start:User {id: 1})-[:FOLLOWS*1..4]->(end:User)
RETURN DISTINCT end.id, end.name
```

단, 그래프 traversal이 항상 빠른 건 아니다. 시작 노드가 수백만 개의 엣지를 가진 슈퍼노드(supernode)라면 traversal 자체가 병목이 된다. Twitter의 유명인 계정처럼 팔로워가 수천만 명인 경우가 이에 해당한다.

---

## Neo4j Cypher 기본

### 노드와 관계 생성

```cypher
-- 노드 생성
CREATE (alice:User {id: 1, name: "Alice", age: 30})
CREATE (bob:User {id: 2, name: "Bob", age: 25})

-- 관계 생성 (엣지 프로퍼티 포함)
MATCH (a:User {id: 1}), (b:User {id: 2})
CREATE (a)-[:FOLLOWS {since: "2024-01-15", weight: 0.8}]->(b)
```

### 관계 조회

```cypher
-- Alice가 팔로우하는 사람 목록
MATCH (alice:User {name: "Alice"})-[r:FOLLOWS]->(following:User)
RETURN following.name, r.since
ORDER BY r.since DESC

-- 상호 팔로우 관계
MATCH (a:User)-[:FOLLOWS]->(b:User)-[:FOLLOWS]->(a)
RETURN a.name, b.name
```

### 관계 업데이트와 삭제

```cypher
-- 엣지 프로퍼티 수정
MATCH (a:User {id: 1})-[r:FOLLOWS]->(b:User {id: 2})
SET r.weight = 0.9

-- 관계만 삭제 (노드 유지)
MATCH (a:User {id: 1})-[r:FOLLOWS]->(b:User {id: 2})
DELETE r

-- 노드와 연결된 모든 관계 삭제
MATCH (u:User {id: 1})
DETACH DELETE u
```

노드를 삭제할 때 `DELETE` 만 쓰면 엣지가 남아있는 경우 에러가 난다. `DETACH DELETE`가 노드와 연결된 엣지를 함께 제거한다.

---

## 엣지 프로퍼티 활용

관계 자체에 속성을 붙이는 게 그래프 DB의 핵심 차별점이다. RDBMS에서 N:M 관계에 메타데이터를 붙이려면 중간 테이블을 만들어야 한다.

```sql
-- RDBMS: 사용자-콘텐츠 좋아요 + 좋아요 누른 시각
CREATE TABLE likes (
    user_id BIGINT,
    content_id BIGINT,
    liked_at TIMESTAMP,
    reaction_type VARCHAR(20),
    PRIMARY KEY (user_id, content_id)
);
```

그래프 DB에서는 엣지에 직접 프로퍼티를 붙인다.

```cypher
MATCH (u:User {id: 1}), (c:Content {id: 100})
CREATE (u)-[:LIKES {liked_at: datetime(), reaction_type: "heart"}]->(c)
```

엣지 프로퍼티를 쿼리 조건으로 쓰는 경우가 많다.

```cypher
-- 최근 7일 이내 좋아요 누른 콘텐츠
MATCH (u:User {id: 1})-[r:LIKES]->(c:Content)
WHERE r.liked_at > datetime() - duration({days: 7})
RETURN c.title, r.liked_at
```

---

## 관계가 1등 시민인 도메인

그래프 DB를 선택할 만한 도메인은 관계 자체를 조회하거나 관계의 패턴을 찾는 경우다.

**소셜 그래프**는 가장 흔한 사례다. 팔로우/팔로워, 공통 친구 찾기, 인플루언서 영향권 분석이 여기 해당한다. "나의 2촌 내 공통 관심사를 가진 사람"처럼 다단계 관계 탐색이 잦으면 RDBMS보다 낫다.

**권한 트리**는 역할 기반 접근 제어(RBAC)나 조직도에서 쓴다. 부모-자식 노드 구조에서 "이 리소스에 접근 가능한 모든 역할"을 조회할 때 트리 traversal이 재귀 SQL보다 단순하다.

```cypher
-- 역할 계층에서 특정 권한을 가진 모든 역할
MATCH (perm:Permission {name: "READ_USER"})<-[:HAS_PERMISSION*1..5]-(role:Role)
RETURN DISTINCT role.name
```

**추천 시스템**에서는 협업 필터링 기반 추천을 그래프로 표현한다. "나와 비슷한 취향의 사람들이 좋아하는 콘텐츠" 패턴이 Cypher로 직관적으로 표현된다.

```cypher
-- 나와 공통 좋아요 3개 이상인 사용자가 좋아요 누른 콘텐츠 (내가 아직 보지 않은 것)
MATCH (me:User {id: 1})-[:LIKES]->(c:Content)<-[:LIKES]-(similar:User)
WITH similar, COUNT(c) AS common_likes
WHERE common_likes >= 3
MATCH (similar)-[:LIKES]->(rec:Content)
WHERE NOT (me)-[:LIKES]->(rec)
RETURN rec.title, COUNT(*) AS score
ORDER BY score DESC
LIMIT 10
```

반대로 그래프 DB가 맞지 않는 경우도 있다. 집계 쿼리(일별 매출 합산, 기간별 통계)는 RDBMS가 낫다. 그래프 traversal은 관계를 따라가는 데 특화되어 있고 범위 스캔이나 집계에는 최적화되어 있지 않다.

---

## RDBMS N:M 관계를 그래프로 전환

RDBMS에서 가장 흔한 구조 중 하나인 N:M 관계가 그래프 DB로 넘어올 때 처리 방식이 달라진다.

**RDBMS 구조**

```sql
-- 사용자-태그 N:M
CREATE TABLE users (id BIGINT PRIMARY KEY, name VARCHAR(100));
CREATE TABLE tags (id BIGINT PRIMARY KEY, name VARCHAR(50));
CREATE TABLE user_tags (
    user_id BIGINT REFERENCES users(id),
    tag_id BIGINT REFERENCES tags(id),
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, tag_id)
);
```

**그래프 DB 구조**

```cypher
-- 중간 테이블 없이 엣지로 직접 표현
CREATE (u:User {id: 1, name: "Alice"})
CREATE (t:Tag {id: 10, name: "backend"})

MATCH (u:User {id: 1}), (t:Tag {id: 10})
CREATE (u)-[:HAS_TAG {created_at: datetime()}]->(t)
```

단순 N:M이라면 이렇게 끝난다. 문제는 중간 테이블이 단순 연결 이상의 역할을 할 때다.

예를 들어 사용자가 프로젝트에 참여하면서 역할(개발자/리뷰어/PM)을 가지는 경우, RDBMS에서는 중간 테이블에 컬럼을 추가한다.

```sql
CREATE TABLE project_members (
    user_id BIGINT,
    project_id BIGINT,
    role VARCHAR(20),
    joined_at TIMESTAMP,
    PRIMARY KEY (user_id, project_id)
);
```

그래프에서는 엣지 프로퍼티로 처리하거나, 중간 노드(intermediate node)를 만드는 방법 중 선택한다.

```cypher
-- 엣지 프로퍼티 방식 (단순할 때)
MATCH (u:User {id: 1}), (p:Project {id: 5})
CREATE (u)-[:MEMBER_OF {role: "developer", joined_at: datetime()}]->(p)

-- 중간 노드 방식 (멤버십 자체를 쿼리 대상으로 삼아야 할 때)
CREATE (m:Membership {role: "developer", joined_at: datetime()})
WITH m
MATCH (u:User {id: 1}), (p:Project {id: 5})
CREATE (u)-[:HAS_MEMBERSHIP]->(m)-[:IN_PROJECT]->(p)
```

중간 노드 방식은 "특정 프로젝트의 모든 개발자 역할 멤버십"을 노드로 조회해야 하거나, 멤버십에 추가 관계를 붙여야 할 때 선택한다. 단순히 관계 속성만 필요하다면 엣지 프로퍼티가 더 간단하다.

전환 시 주의할 점은 외래키 제약이 없다는 것이다. Neo4j는 RDBMS의 참조 무결성을 자동으로 보장하지 않는다. 애플리케이션 레벨에서 존재하지 않는 노드로의 엣지 생성을 막는 로직이 필요하다.

```cypher
-- MERGE로 중복 방지 (없으면 생성, 있으면 매칭)
MERGE (u:User {id: 1})
ON CREATE SET u.name = "Alice", u.created_at = datetime()
ON MATCH SET u.updated_at = datetime()
```

`MERGE`는 `UPSERT`와 같은 역할을 한다. 중복 노드 생성을 막을 때 쓴다.
