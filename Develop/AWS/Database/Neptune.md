---
title: Amazon Neptune
tags: [AWS, Database, Graph, Neptune, Gremlin, SPARQL]
updated: 2026-07-25
---

# Amazon Neptune

관계형 데이터베이스나 DynamoDB로 해결하기 어려운 문제가 있다. 노드 간 관계가 데이터의 핵심인 경우다. "이 사용자와 3단계 이내로 연결된 모든 사람을 찾아라", "이 제품을 산 사람이 함께 산 제품은 무엇인가"를 SQL로 표현하면 재귀 CTE나 다중 조인이 필요하고, 관계 깊이가 늘어날수록 쿼리가 폭발적으로 느려진다. Neptune은 이런 문제를 위한 그래프 데이터베이스다.

## 두 가지 그래프 모델

Neptune은 하나의 클러스터에서 두 모델을 동시에 지원한다.

**Property Graph + Gremlin**

데이터를 vertex(노드)와 edge(간선)로 표현하고, 각각에 property를 붙인다. 쿼리 언어는 Gremlin이다. Apache TinkerPop 스택 위에서 동작하기 때문에 TinkerPop을 쓰던 팀이라면 마이그레이션이 상대적으로 쉽다.

```gremlin
// 사용자 A와 직접 연결된 친구 목록
g.V().has('User', 'userId', 'userA')
  .out('FOLLOWS')
  .values('name')

// 2단계 추천: 내 친구의 친구 (나는 제외)
g.V().has('User', 'userId', 'userA')
  .out('FOLLOWS').aggregate('friends')
  .out('FOLLOWS')
  .where(without('friends'))
  .dedup()
  .values('name')
```

**RDF + SPARQL**

지식 그래프와 시맨틱 웹 계열에서 쓰는 모델이다. 데이터를 주어-술어-목적어(Subject-Predicate-Object) 트리플로 표현한다. 의료, 금융, 정부 데이터처럼 표준 온톨로지를 따라야 하는 경우에 사용한다.

```sparql
# 특정 약물과 상호작용하는 모든 약물 조회
SELECT ?drug ?interaction
WHERE {
  :DrugA :interactsWith ?drug .
  ?drug :hasInteractionType ?interaction .
}
```

실무에서는 Gremlin을 사용하는 Property Graph 쪽이 압도적으로 많다. SPARQL은 W3C 표준 데이터셋을 다루거나 온톨로지 추론이 필요한 특수 케이스에 등장한다.

## RDS나 DynamoDB 대신 Neptune을 선택하는 경우

관계형 DB와 그래프 DB의 차이는 "관계 자체가 1등 시민인가"에 있다. RDS에서 관계는 외래 키와 조인으로 표현되는데, 관계 깊이가 늘어날수록 쿼리 복잡도가 기하급수적으로 커진다.

**Neptune이 적합한 시나리오:**

소셜 네트워크에서 특정 사용자와 N단계 이내의 모든 연결을 찾는 경우, RDS라면 재귀 쿼리를 써야 하고 깊이 5단계만 돼도 수초가 걸린다. Neptune은 그래프 순회 자체가 기본 연산이라 깊이에 비례해 선형적으로 처리한다.

추천 엔진에서 "이 상품을 구매한 고객이 함께 구매한 상품" 패턴은 협업 필터링의 기본이다. DynamoDB로 구현하면 중간 집계 테이블을 따로 만들어야 하고 실시간 반영이 어렵다. 그래프로 모델링하면 엣지 하나가 구매 이력이 되어 순회만으로 추천 후보를 뽑을 수 있다.

사기 탐지에서 계좌-인물-IP-기기 간의 관계망을 분석할 때, 서로 다른 계좌가 동일 IP나 기기를 공유하는 패턴을 찾는 건 그래프 순회로 자연스럽게 표현된다. RDS에서 이걸 JOIN으로 구현하면 쿼리가 관리 불가능한 수준이 된다.

반면 단순 CRUD 위주의 서비스, 집계 쿼리(SUM, GROUP BY)가 핵심인 서비스, 관계보다 속성 검색이 주인 서비스는 Neptune보다 RDS나 DynamoDB가 적합하다.

## 클러스터 구조

Neptune 클러스터는 Aurora와 유사한 구조다.

```
클러스터 엔드포인트 (쓰기)
        |
  Primary Instance
        |
  공유 스토리지 (6개 복사본, 3 AZ)
        |
  Read Replica × N (최대 15개)
        |
읽기 엔드포인트 (라운드로빈)
```

Primary 인스턴스가 쓰기를 담당하고, Read Replica들이 읽기를 처리한다. 스토리지는 Primary와 Replica가 공유하기 때문에 Replica를 추가해도 스토리지 복사가 일어나지 않는다. Replica 추가는 빠르고, Primary 장애 시 Replica 중 하나가 자동으로 Primary로 승격된다.

스토리지는 10GB 단위로 자동 확장되며 최대 128TB까지 늘어난다. 용량을 미리 프로비저닝하지 않아도 된다.

**연결 방법:**

Gremlin용 WebSocket 엔드포인트와 HTTPS REST 엔드포인트를 별도로 제공한다. 실시간 순회에는 WebSocket, 배치 로드에는 REST를 쓰는 패턴이 일반적이다.

```python
from gremlin_python.driver import client, serializer

neptune_endpoint = "wss://your-cluster.cluster-xxx.us-east-1.neptune.amazonaws.com:8182/gremlin"

connection = client.Client(
    neptune_endpoint,
    'g',
    message_serializer=serializer.GraphSONSerializersV2d0()
)

result = connection.submit(
    "g.V().has('User', 'userId', uid).out('FOLLOWS').values('name')",
    {"uid": "userA"}
).result().all().result()
```

## 데이터 로딩

Neptune Bulk Loader는 S3에서 직접 대용량 데이터를 적재하는 기능이다. Neptune에 데이터를 처음 밀어넣을 때 Gremlin로 한 건씩 insert하면 수백만 건 기준으로 몇 시간이 걸린다. Bulk Loader를 쓰면 같은 양을 수십 분으로 줄일 수 있다.

입력 포맷은 CSV(Gremlin 전용)와 N-Triples, N-Quads, RDF/XML, Turtle(RDF용)을 지원한다.

```csv
# vertex 파일 (nodes.csv)
~id,~label,name:String,age:Int
v1,User,Alice,30
v2,User,Bob,25
v3,Product,Laptop,

# edge 파일 (edges.csv)
~id,~from,~to,~label,weight:Double
e1,v1,v2,FOLLOWS,1.0
e2,v1,v3,PURCHASED,1.0
```

```bash
# Bulk Loader API 호출
curl -X POST \
  https://your-cluster:8182/loader \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "s3://your-bucket/graph-data/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::account:role/NeptuneLoadRole",
    "region": "us-east-1",
    "failOnError": "FALSE"
  }'
```

## 쿼리 성능 튜닝

**인덱스 구조 이해**

Neptune은 자동으로 4가지 인덱스를 유지한다: SPOG(Subject-Predicate-Object-Graph), POGS, OSPC, GSPO. Property Graph에서는 vertex label, edge label, property key별로 인덱스가 자동 생성된다. 별도로 인덱스를 만들 수 없기 때문에 쿼리 패턴에 맞게 그래프를 모델링하는 게 핵심이다.

**순회 방향 선택**

Gremlin에서 `out()`(나가는 방향)과 `in()`(들어오는 방향)의 성능 차이가 있을 수 있다. 엣지를 정의할 때 자주 순회하는 방향을 `out()` 방향으로 맞추면 쿼리가 더 빠르다.

```gremlin
// 느린 패턴: 역방향 순회가 많은 경우
g.V().has('Product', 'productId', pid).in('PURCHASED').values('userId')

// 빠른 패턴: 엣지 방향을 바꿔 모델링
// User -[PURCHASED]-> Product 대신
// Product -[PURCHASED_BY]-> User로 저장
g.V().has('Product', 'productId', pid).out('PURCHASED_BY').values('userId')
```

**프로파일링**

`profile()` 스텝을 붙이면 각 단계별 실행 시간과 처리한 요소 수를 확인할 수 있다.

```gremlin
g.V().has('User', 'userId', 'userA')
  .out('FOLLOWS')
  .out('FOLLOWS')
  .dedup()
  .profile()
```

결과에서 `Traversers`가 급격히 늘어나는 단계가 병목이다. 중간에 `limit()`이나 `has()` 필터를 추가해서 순회 대상을 줄여야 한다.

**슈퍼노드 문제**

소셜 그래프에서 팔로워가 수백만 명인 인플루언서 같은 노드를 슈퍼노드라고 한다. 슈퍼노드를 순회하는 쿼리는 항상 느리다. 이 경우 모든 엣지를 순회하는 대신 `sample()`이나 `coin()`으로 확률적 샘플링을 적용하거나, 슈퍼노드 여부를 property로 미리 마킹해서 별도로 처리하는 패턴을 쓴다.

```gremlin
// 슈퍼노드에서 랜덤 샘플 100개만 순회
g.V().has('User', 'userId', 'celebrity')
  .out('FOLLOWS')
  .coin(0.1)  // 10% 확률로 통과
  .limit(100)
  .values('name')
```

**읽기 부하 분산**

읽기 전용 쿼리는 Read Replica로 보내야 한다. 애플리케이션에서 클러스터 읽기 엔드포인트를 별도로 설정해야 하며, 이를 코드에서 명시적으로 분리하지 않으면 모든 트래픽이 Primary로 몰린다.

## 모니터링

CloudWatch에서 확인할 주요 지표는 세 가지다.

`GremlinRequestsPerSec`와 `SparqlRequestsPerSec`로 전체 요청량을 파악한다. `GremlinWebSocketMaxCreatedSessionCount`가 커넥션 풀 한계에 가까워지면 인스턴스 크기를 올려야 한다. `BufferCacheHitRatio`가 낮으면 메모리가 부족한 것으로, 인스턴스 업그레이드를 검토한다.

Neptune Streams를 활성화하면 그래프 변경 이력을 스트림으로 받을 수 있다. Kinesis Data Streams와 연동해서 그래프 변경을 다른 시스템에 전파하는 CDC 파이프라인을 만들 수 있다.
