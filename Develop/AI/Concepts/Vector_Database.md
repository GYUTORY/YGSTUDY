---
title: 벡터 DB 실무 비교와 운영 (pgvector·Qdrant·Pinecone·Milvus)
tags: [ai, vector-database, pgvector, qdrant, hnsw, ivfflat]
updated: 2026-06-22
---

# 벡터 DB 실무 비교와 운영

## 1. 무엇을 고를 것인가

벡터 검색을 백엔드에 붙일 때 처음 막히는 지점은 "어떤 DB를 쓸 것인가"다. 보통 4개 중 하나로 좁혀진다.

| 제품 | 형태 | 인덱스 | 메타데이터 필터 | 운영 부담 |
|------|------|--------|----------------|-----------|
| pgvector | Postgres 확장 | HNSW, IVFFlat | SQL WHERE 그대로 | 낮음 (기존 Postgres 재사용) |
| Qdrant | 전용 엔진 (Rust) | HNSW | payload 필터 (인덱싱 가능) | 중간 |
| Pinecone | 매니지드 SaaS | 자체 (블랙박스) | metadata 필터 | 없음 (대신 비용·종속) |
| Milvus | 전용 엔진 (분산) | HNSW, IVF 계열 다수 | scalar 필터 | 높음 (etcd, MinIO 등 의존) |

결론부터 말하면, 이미 Postgres를 쓰고 데이터가 수백만 건 이하라면 pgvector로 시작하는 게 거의 항상 맞다. 별도 인프라가 늘지 않고, 벡터와 원본 row를 한 트랜잭션에서 다룰 수 있다. 데이터가 수천만~억 단위로 가거나 QPS가 높아지면 그때 Qdrant나 Milvus를 검토한다. Pinecone은 인프라를 아예 안 만지고 싶을 때 선택지인데, 비용이 데이터 양에 비례해서 빠르게 올라가고 인덱스 내부를 못 건드린다는 점을 감수해야 한다.

처음부터 Milvus를 깔았다가 etcd, MinIO, Pulsar까지 같이 운영하느라 정작 검색 품질 튜닝은 손도 못 대는 경우를 본 적이 있다. 트래픽이 그만큼 안 나오는데 분산 시스템부터 들이면 운영 비용만 먹는다.

## 2. HNSW와 IVFFlat — 인덱스 방식 차이

벡터 인덱스는 결국 "전체를 다 비교하지 않고(brute force 회피) 근사적으로 가까운 걸 빠르게 찾는다"는 ANN(Approximate Nearest Neighbor) 문제다. 실무에서 만나는 인덱스는 사실상 HNSW와 IVFFlat 둘이다.

### 2.1 IVFFlat

벡터 공간을 미리 여러 개의 클러스터(`lists`)로 나눠두고, 쿼리가 들어오면 가까운 몇 개 클러스터(`probes`)만 뒤진다. k-means로 중심점을 잡는 방식이라 인덱스를 만들기 전에 데이터가 어느 정도 쌓여 있어야 클러스터가 제대로 나뉜다.

- 빌드가 빠르고 메모리를 적게 쓴다.
- 데이터가 별로 없을 때 인덱스를 만들면 클러스터가 엉성해져서 recall이 떨어진다.
- 데이터 분포가 바뀌면(대량 insert 후) 재학습이 필요하다. 안 하면 검색 품질이 서서히 나빠진다.

### 2.2 HNSW

벡터들을 그래프로 연결해두고, 진입점에서 가까운 노드로 점프하며 내려가는 방식이다. 계층 구조라 탐색이 로그 스케일에 가깝다. recall과 속도 모두 IVFFlat보다 좋은 경우가 많아서 요즘은 기본값으로 HNSW를 쓴다.

- recall·QPS 모두 우수하다. 데이터가 적어도 동작한다.
- 빌드가 느리고 메모리를 많이 먹는다. 그래프 자체를 메모리에 들고 있어야 한다.
- insert가 들어올 때마다 그래프를 갱신하므로 쓰기 부하가 IVFFlat보다 크다.

### 2.3 어느 쪽을 쓸 것인가

읽기 위주에 검색 품질이 중요하면 HNSW. 메모리가 빠듯하거나 인덱스를 자주 새로 만들어야 하면 IVFFlat. 대부분의 서비스는 HNSW로 가면 된다. 다만 수억 건 규모에서 HNSW 메모리가 부담되면 IVFFlat이나 양자화(quantization)를 같이 검토한다.

## 3. pgvector 실전

### 3.1 테이블과 인덱스

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id          bigserial PRIMARY KEY,
    content     text,
    category    text,
    embedding   vector(1536)   -- OpenAI text-embedding-3-small 차원
);

-- HNSW 인덱스. m, ef_construction이 핵심 파라미터다.
CREATE INDEX ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

여기서 거리 연산자를 인덱스의 `*_ops`와 쿼리의 연산자를 맞추는 게 중요하다. 코사인 거리로 인덱스를 만들었으면 쿼리도 `<=>`를 써야 인덱스를 탄다. 다른 연산자(`<->` L2, `<#>` 내적)를 섞으면 인덱스를 무시하고 풀스캔이 돈다. 이걸 모르고 "인덱스 만들었는데 왜 느리지" 하는 경우가 흔하다.

```sql
-- 코사인 거리 검색 (vector_cosine_ops 인덱스와 짝)
SELECT id, content, embedding <=> $1 AS distance
FROM documents
ORDER BY embedding <=> $1
LIMIT 10;
```

### 3.2 파라미터 튜닝

HNSW에서 만지는 값은 세 개다.

- `m`: 노드당 연결 수. 크게 잡으면 recall이 오르지만 메모리·빌드 시간이 늘어난다. 기본 16에서 시작한다.
- `ef_construction`: 빌드 시 탐색 폭. 크게 잡으면 인덱스 품질이 좋아지지만 빌드가 느려진다. 64~200 사이.
- `ef_search`: 검색 시 탐색 폭. 이건 인덱스가 아니라 세션 단위로 조절한다.

```sql
SET hnsw.ef_search = 100;   -- 기본 40. 올리면 recall↑, 속도↓
```

`ef_search`는 런타임에 바꿀 수 있어서, "검색 품질이 부족하다"는 피드백이 오면 인덱스를 다시 만들지 말고 이 값부터 올려본다. 40에서 100으로만 올려도 누락되던 결과가 잡히는 경우가 많다. 대신 latency가 비례해서 늘어나니 p99를 보면서 조정한다.

IVFFlat은 `lists`(빌드 시)와 `probes`(검색 시)다.

```sql
CREATE INDEX ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);   -- 보통 행 수의 제곱근 근처에서 시작

SET ivfflat.probes = 10;   -- lists의 1~10% 정도
```

`lists`를 너무 작게 잡으면 클러스터당 벡터가 많아져 느리고, 너무 크게 잡으면 클러스터가 잘게 쪼개져 `probes`를 늘려야 recall이 나온다. 행 수 √N을 기준선으로 잡고 조정한다.

### 3.3 인덱스 빌드 시 주의

수백만 건에 HNSW 인덱스를 만들면 시간이 꽤 걸린다. 빌드 중 `maintenance_work_mem`이 작으면 디스크로 스왑되면서 몇 배 느려진다.

```sql
SET maintenance_work_mem = '2GB';
SET max_parallel_maintenance_workers = 4;   -- 병렬 빌드
```

그리고 데이터를 다 넣고 인덱스를 만드는 게 빠르다. 빈 테이블에 인덱스부터 만들고 한 건씩 insert하면 매 insert마다 그래프가 갱신돼서 전체 적재 시간이 늘어난다. 대량 마이그레이션은 "insert 먼저, 인덱스 나중에" 순서로 한다.

## 4. 메타데이터 필터링과 성능 저하

실무에서 가장 골치 아픈 부분이다. 순수 벡터 검색만 하는 경우는 드물고, 보통 "특정 카테고리 안에서, 특정 유저 것만, 최근 30일 안에서" 같은 조건이 붙는다.

```sql
SELECT id, content
FROM documents
WHERE category = 'finance'
  AND created_at > now() - interval '30 days'
ORDER BY embedding <=> $1
LIMIT 10;
```

문제는 ANN 인덱스와 WHERE 조건이 서로 따로 논다는 점이다. HNSW는 벡터 그래프를 타고 가까운 후보를 모으는데, 그 후보들이 WHERE 조건을 만족한다는 보장이 없다. 두 가지 방식이 있다.

### 4.1 pre-filter vs post-filter

- post-filter: 벡터로 후보 N개를 먼저 뽑고 그중에서 WHERE를 적용. 필터가 빡세면 N개 중 조건 통과가 2~3개밖에 안 나와서 결과가 LIMIT을 못 채운다.
- pre-filter: WHERE를 먼저 적용해서 후보를 좁힌 뒤 그 안에서 벡터 검색. 조건에 맞는 게 수만 건이면 그 안에서 다시 ANN을 돌려야 해서 인덱스 효율이 떨어진다.

pgvector에서 필터가 매우 선택적이면(결과 row가 적으면) 플래너가 인덱스 스캔 대신 그냥 필터 후 정렬을 택하기도 한다. 반대로 필터가 느슨하면 HNSW를 타되 `ef_search`를 충분히 키워야 필터 통과분이 LIMIT을 채운다.

실제로 겪는 증상은 이렇다. "카테고리 필터 없을 땐 잘 나오는데, 필터 걸면 결과가 3개밖에 안 나온다." 원인은 HNSW가 후보 40개(`ef_search` 기본)를 뽑았는데 그중 해당 카테고리가 3개뿐이라서다. 해결은 `ef_search`를 올려서 후보를 더 많이 뽑게 하는 것.

```sql
SET hnsw.ef_search = 200;   -- 필터가 빡셀수록 더 키워야 한다
```

### 4.2 필터 컬럼 인덱싱

`category` 같은 필터 컬럼에 일반 B-tree 인덱스를 같이 만들어두면 플래너가 선택지를 더 갖는다. Qdrant는 payload에 명시적으로 인덱스를 만들 수 있고(`create_payload_index`), 필터가 선택적일 때 이걸 안 만들면 전체 스캔이 돈다. Qdrant를 쓰면서 필터 검색이 느리면 payload 인덱스부터 확인한다.

### 4.3 카디널리티가 낮은 필터의 함정

`is_deleted = false`처럼 거의 모든 row가 해당되는 조건은 필터로서 의미가 없는데, 이걸 WHERE에 넣으면 플래너가 헷갈려서 엉뚱한 플랜을 고르기도 한다. 이런 건 차라리 partial index로 빼거나 soft delete된 row를 아예 별도 테이블로 분리하는 게 낫다.

## 5. 백엔드 서비스에 붙일 때 실제로 겪는 문제

### 5.1 임베딩 차원·모델 불일치

인덱스를 `vector(1536)`으로 만들어놓고 나중에 임베딩 모델을 차원이 다른 걸로 바꾸면 전체를 다시 임베딩해서 적재해야 한다. 모델을 바꾸는 순간 기존 벡터와 새 벡터는 같은 공간이 아니라서 섞으면 검색이 망가진다. 같은 모델이라도 버전이 올라가면서 분포가 미묘하게 달라질 수 있으니, 어떤 모델·버전으로 임베딩했는지 컬럼에 박아두는 게 좋다.

```sql
ALTER TABLE documents ADD COLUMN embedding_model text DEFAULT 'text-embedding-3-small';
```

재임베딩은 무조건 한 번은 겪는다. 배치로 돌리되, 새 컬럼에 새 모델로 채운 뒤 검증하고 스위치하는 식으로 무중단을 설계해두면 덜 고생한다.

### 5.2 정규화와 거리 함수

코사인 유사도를 쓸 거면 벡터를 미리 정규화(L2 normalize)해두고 내적(`<#>`)으로 검색하는 게 코사인 거리 계산보다 빠르다. 대부분의 임베딩 API는 이미 정규화된 벡터를 주지만, 직접 학습한 모델이면 정규화 여부를 확인해야 한다. 정규화 안 된 벡터에 코사인을 쓰면 결과는 맞지만 매 쿼리마다 노름 계산이 들어간다.

### 5.3 distance를 그대로 점수로 쓰지 마라

`embedding <=> $1`이 돌려주는 건 거리(작을수록 가까움)지 유사도 점수가 아니다. 프론트에 "유사도 87%"로 보여주려고 거리를 그대로 쓰면 거꾸로 된다. 코사인 거리면 `1 - distance`가 유사도다. 그리고 이 점수의 절대값으로 "관련 있다/없다"를 자르는 임계값은 모델마다 다르니, 실제 데이터로 분포를 보고 정해야 한다. 다른 모델에서 쓰던 임계값을 그대로 가져오면 안 맞는다.

### 5.4 커넥션과 메모리

HNSW 검색은 CPU·메모리를 꽤 쓴다. `ef_search`를 크게 잡은 쿼리가 동시에 많이 들어오면 Postgres 커넥션마다 작업 메모리를 잡아서 인스턴스가 휘청인다. 검색 전용 read replica를 두거나, 애플리케이션 단에서 동시 검색 수를 제한하는 게 안전하다. 벡터 검색을 일반 OLTP 쿼리와 같은 인스턴스에서 마구 돌리면 서로 자원을 뺏는다.

### 5.5 하이브리드 검색

순수 벡터 검색만으로는 정확한 키워드(제품 코드, 고유명사) 매칭이 약하다. "ABC-1234"를 찾는데 임베딩은 의미가 비슷한 다른 코드를 위로 올려버린다. 이럴 때 전통적인 풀텍스트 검색(Postgres `tsvector`, 또는 BM25)과 벡터 검색을 합치는 하이브리드가 필요하다. 두 결과를 RRF(Reciprocal Rank Fusion) 같은 방식으로 합치면 키워드와 의미 검색의 약점을 서로 메운다. Qdrant는 sparse vector를 지원해서 이걸 엔진 안에서 처리할 수 있고, pgvector는 풀텍스트 검색 결과와 벡터 검색 결과를 SQL에서 합쳐야 한다.

## 6. 정리해두면 좋은 운영 감각

- 데이터가 천만 건 이하면 pgvector로 충분하다. 인프라를 늘리기 전에 `ef_search`부터 만져본다.
- 필터를 걸었을 때 결과가 모자라면 인덱스를 의심하기 전에 `ef_search`를 키워본다.
- 임베딩 모델·버전을 row에 기록해두면 재임베딩 때 산다.
- 거리와 유사도를 헷갈리지 않는다. 임계값은 실데이터로 정한다.
- 키워드 정확도가 중요하면 처음부터 하이브리드 검색을 염두에 둔다.