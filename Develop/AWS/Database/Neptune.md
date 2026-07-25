---
title: Amazon Neptune
tags: [AWS, Database, Graph, Neptune, Gremlin, SPARQL, Serverless]
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

소셜 네트워크에서 특정 사용자와 N단계 이내의 모든 연결을 찾는 경우, RDS라면 재귀 쿼리를 써야 하고 깊이 5단계만 돼도 수초가 걸린다. Neptune은 그래프 순회 자체가 기본 연산이라 깊이에 비례해 선형적으로 처리한다.

추천 엔진에서 "이 상품을 구매한 고객이 함께 구매한 상품" 패턴은 협업 필터링의 기본이다. DynamoDB로 구현하면 중간 집계 테이블을 따로 만들어야 하고 실시간 반영이 어렵다. 그래프로 모델링하면 엣지 하나가 구매 이력이 되어 순회만으로 추천 후보를 뽑을 수 있다.

사기 탐지에서 계좌-인물-IP-기기 간의 관계망을 분석할 때, 서로 다른 계좌가 동일 IP나 기기를 공유하는 패턴을 찾는 건 그래프 순회로 자연스럽게 표현된다. RDS에서 이걸 JOIN으로 구현하면 쿼리가 관리 불가능한 수준이 된다.

단순 CRUD 위주의 서비스, 집계 쿼리(SUM, GROUP BY)가 핵심인 서비스, 관계보다 속성 검색이 주인 서비스는 Neptune보다 RDS나 DynamoDB가 적합하다.

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

## Neptune Serverless

2022년에 출시된 Serverless 모드는 NCU(Neptune Capacity Unit) 단위로 자동 스케일링한다. 최솟값과 최댓값을 설정하면 Neptune이 부하에 따라 그 범위 안에서 조정한다. 최소 2.5 NCU에서 최대 128 NCU까지 설정 가능하다.

트래픽이 간헐적이거나 개발/스테이징 환경처럼 평시 요청이 없고 가끔 대량 조회가 발생하는 워크로드에 맞다. 지속적인 고트래픽 환경에서는 프로비저닝 인스턴스가 더 저렴하다.

스케일 업 과정에서 수초에서 수십 초의 레이턴시 스파이크가 발생한다는 점을 주의해야 한다. SLA가 엄격한 서비스라면 최솟값을 높게 잡거나 프로비저닝 인스턴스를 선택하는 게 낫다.

```bash
# Serverless 클러스터 생성 (AWS CLI)
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-serverless \
  --engine neptune \
  --serverless-v2-scaling-configuration MinCapacity=2.5,MaxCapacity=32 \
  --no-publicly-accessible
```

## 보안

Neptune은 퍼블릭 엔드포인트를 제공하지 않는다. VPC 안에서만 실행되며, 인터넷에서 직접 접근하는 건 구조적으로 불가능하다. 보안 그룹으로 어떤 리소스가 8182 포트에 접근할 수 있는지 제어한다.

**IAM 인증**

클러스터 생성 후 IAM 인증을 별도로 활성화해야 한다. 비활성화 상태에서는 같은 VPC 안이면 누구든 Neptune에 쿼리를 날릴 수 있다. 프로덕션에서는 반드시 켜야 한다.

IAM 인증을 활성화하면 모든 요청에 AWS SigV4 서명이 필요하다. gremlin-python에서 WebSocket 연결에 SigV4를 붙이려면 직접 구현하거나 `neptune-python-utils` 같은 헬퍼 라이브러리를 써야 한다.

```python
# neptune-python-utils 사용 (IAM 인증 포함)
from neptune_python_utils.endpoints import Endpoints
from neptune_python_utils.gremlin_utils import GremlinUtils
from gremlin_python.process.anonymous_traversal import traversal

endpoints = Endpoints(
    neptune_endpoint="your-cluster.xxx.us-east-1.neptune.amazonaws.com"
)
gremlin_utils = GremlinUtils(endpoints)
conn = gremlin_utils.remote_connection()

g = traversal().withRemote(conn)
names = g.V().has('User', 'userId', 'userA').out('FOLLOWS').values('name').toList()
```

IAM 정책에서 `neptune-db:connect`, `neptune-db:ReadDataViaQuery`, `neptune-db:WriteDataViaQuery` 같은 액션으로 세분화된 권한 제어가 가능하다. 읽기 전용 서비스에는 `ReadDataViaQuery`만 부여하면 된다.

**TLS와 저장 데이터 암호화**

TLS는 기본 활성화다. Neptune 엔드포인트로 나가는 모든 통신은 암호화된다.

저장 데이터 암호화는 클러스터 생성 시 KMS 키를 지정한다. 생성 후 변경이 불가능하므로 초기에 결정해야 한다. AWS 관리형 키를 쓰거나 CMK(Customer Managed Key)를 사용할 수 있다. CMK를 쓰면 키 로테이션 주기와 키 삭제 정책을 직접 관리해야 한다.

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

**Bulk Loader 실패 트러블슈팅**

파싱 오류가 가장 흔하다. `failOnError: FALSE`로 실행하면 에러를 건너뛰고 진행한다. 완료 후 로드 상태 API에서 에러 항목을 확인한다.

```bash
# 로드 상태 확인
curl -G https://your-cluster:8182/loader/{load-id}

# 에러 상세 조회
curl -G "https://your-cluster:8182/loader/{load-id}?errors=true&page=1&errorsPerPage=10"
```

IAM 권한 문제도 자주 발생한다. Neptune 클러스터가 S3에 접근하려면 `rds.amazonaws.com`을 신뢰하는 IAM 역할이 필요하다. 역할에 `AmazonS3ReadOnlyAccess`를 붙이고, 해당 역할 ARN을 클러스터에 연결해야 한다.

VPC 안에서 S3로 나가는 트래픽에 S3 VPC 엔드포인트(게이트웨이 타입)가 없으면 라우팅이 막혀 Bulk Loader가 시작조차 하지 않는다. S3 게이트웨이 엔드포인트를 만들고 Neptune이 있는 서브넷의 라우팅 테이블에 추가해야 한다.

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

**슈퍼노드 OOM**

소셜 그래프에서 팔로워가 수백만 명인 인플루언서 같은 노드를 슈퍼노드라고 한다. Neptune은 쿼리 처리 결과를 메모리에 올리기 때문에, 엣지가 수백만 개인 노드를 한 번에 전부 순회하면 r5.8xlarge에서도 OOM이 발생해 인스턴스가 재시작된다.

`profile()`로 확인했을 때 특정 단계에서 Traverser 수가 수십만 이상이면 슈퍼노드가 순회 경로에 있는 것이다. `choose()` 스텝으로 슈퍼노드를 분기 처리하거나, 쓰기 시점에 엣지 수를 vertex property로 캐싱해두면 순회 없이 판별할 수 있다.

```gremlin
// 슈퍼노드 분기 처리
g.V().has('User', 'userId', uid)
  .choose(
    __.outE('FOLLOWS').count().is(gt(100000)),
    __.out('FOLLOWS').coin(0.01).limit(1000),
    __.out('FOLLOWS')
  )
  .values('name')
```

**읽기 부하 분산**

읽기 전용 쿼리는 Read Replica로 보내야 한다. 클러스터 읽기 엔드포인트를 별도로 설정해야 하며, 코드에서 명시적으로 분리하지 않으면 모든 트래픽이 Primary로 몰린다.

## 연결 관리

Neptune은 기본적으로 WebSocket 연결을 1200초 후 끊는다. 연결 풀을 오래 유지하는 서비스에서 이 제한에 걸려 `CancelledError`나 `TimeoutError`가 간헐적으로 발생한다.

애플리케이션 레벨에서 연결 최대 유효 시간을 1200초 미만으로 설정하거나, 주기적으로 빈 쿼리를 날려서 연결을 유지하는 방법을 쓴다. Neptune 앞에 NLB를 두는 경우 NLB의 idle timeout도 이 값과 맞춰야 한다.

```python
import threading
from gremlin_python.driver import serializer
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal

conn = DriverRemoteConnection(
    'wss://your-cluster:8182/gremlin',
    'g',
    pool_size=10,
    max_workers=10,
    message_serializer=serializer.GraphSONSerializersV2d0()
)

g = traversal().withRemote(conn)

def keepalive(traversal_source, interval=300):
    while True:
        try:
            traversal_source.inject(1).toList()
        except Exception:
            pass
        threading.Event().wait(interval)

threading.Thread(target=keepalive, args=(g,), daemon=True).start()
```

연결 오류 발생 시 재연결 로직이 없으면 서비스가 Neptune에 붙지 못하는 상태가 지속된다. 재연결 시도 로직과 지수 백오프를 함께 적용해야 한다.

## 비용 구조

Neptune 비용은 인스턴스, 스토리지, I/O 세 가지로 나뉜다.

인스턴스는 Primary와 각 Replica에 대해 시간당 과금한다. 개발 환경은 t3.medium이나 t4g.medium으로 충분하다. Replica를 늘릴수록 인스턴스 비용이 선형으로 증가한다.

스토리지는 GB당 월 과금이다. 6개 복사본을 3개 AZ에 유지하는 구조라 실제 데이터 크기의 6배 분량이 청구된다고 보면 된다. 10GB 데이터를 저장하면 60GB 분량이 청구된다.

I/O는 백만 요청당 과금한다. RDS와 달리 Neptune은 I/O 요청 수로 과금하므로, 읽기/쓰기가 많은 워크로드에서 I/O 비용이 예상보다 크게 나올 수 있다. CloudWatch에서 `VolumeReadIOPs`와 `VolumeWriteIOPs`를 모니터링해서 I/O 패턴을 파악해야 한다.

Neptune Serverless는 NCU 사용량으로 초당 과금된다. 1 NCU는 약 2 vCPU, 8GB 메모리에 해당한다. 간헐적 워크로드는 Serverless가 저렴하지만, 지속적인 고트래픽이면 프로비저닝 인스턴스가 훨씬 싸다. 예상 비용 차이가 크면 두 모드를 모두 테스트해보는 게 낫다.

## 모니터링

**요청 레이턴시**

`MainRequestLatency`(p99)가 가장 중요한 지표다. 갑자기 상승하면 슈퍼노드 쿼리나 대형 순회가 들어온 경우가 많다. `GremlinRequestsPerSec`와 함께 보면 요청량 증가인지 특정 쿼리 문제인지 구분된다.

**메모리와 커넥션**

`BufferCacheHitRatio`가 90% 아래로 떨어지면 버퍼 캐시가 워크로드를 수용하지 못하는 것이다. 인스턴스 크기 업그레이드를 검토한다.

`GremlinWebSocketMaxCreatedSessionCount`가 한계에 가까워지면 애플리케이션의 연결 수가 Neptune 인스턴스의 최대 세션 수에 근접한 것이다. 연결 풀 크기를 줄이거나 인스턴스를 올려야 한다.

**스토리지와 I/O**

`FreeLocalStorage`가 부족해지면 임시 파일이나 쿼리 결과 저장 공간이 부족한 것이다. 대형 순회 결과를 많이 쌓는 쿼리 패턴을 줄이거나 인스턴스 크기를 늘려야 한다.

`VolumeReadIOPs`와 `VolumeWriteIOPs`는 I/O 비용과 직결된다. 비용 이상 급증이 보이면 어떤 쿼리가 I/O를 많이 쓰는지 `profile()`로 확인해야 한다.

**Neptune Streams**

Streams를 활성화하면 그래프 변경 이력을 스트림으로 받을 수 있다. Kinesis Data Streams와 연동해서 그래프 변경을 다른 시스템에 전파하는 CDC 파이프라인을 만들 수 있다.
