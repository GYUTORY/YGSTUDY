---
title: AWS DAX (DynamoDB Accelerator)
tags: [aws, cache, performance, cloud]
updated: 2026-11-18
---

# AWS DAX (DynamoDB Accelerator)

## 개요

DAX는 DynamoDB 전용 인메모리 캐시다. DynamoDB 앞단에 위치해서 읽기 성능을 높인다. 응답 시간을 밀리초에서 마이크로초로 줄인다. DynamoDB API와 완전히 호환된다. 기존 코드를 거의 수정하지 않고 사용할 수 있다.

### 왜 필요한가

DynamoDB는 빠르지만 캐시만큼은 아니다. 작업별 응답 시간은 이 정도다.

- GetItem: 평균 5-10ms
- Query: 평균 10-20ms
- Scan: 수백 ms ~ 수 초

초당 수천 개 요청이 오면 DynamoDB 비용이 증가한다. 게임 리더보드가 대표적이다. 사용자가 리더보드를 조회할 때마다 DynamoDB를 읽는다.

- 초당 10,000개 요청
- 비용: 10,000 RCU = 시간당 $0.5

DAX를 앞에 두면 읽기 경로가 바뀐다.

- 첫 요청: DynamoDB에서 읽는다 (10ms)
- 이후 요청: DAX에서 읽는다 (1ms 미만)
- 10배 빨라진다
- DynamoDB 읽기가 99% 감소한다
- 비용 절감

### ElastiCache vs DAX

둘 다 캐시지만 성격이 다르다.

ElastiCache는 Redis/Memcached 기반의 범용 캐시다.

- 캐시 로직을 직접 작성한다
- 모든 데이터를 저장할 수 있다
- DynamoDB 외 다른 소스도 캐시한다

DAX는 DynamoDB 전용이다.

- DynamoDB API와 호환된다
- 캐시 로직이 자동이다
- DynamoDB 데이터만 캐시한다
- 코드 수정이 최소다

DAX를 고르는 경우는 이렇다.

- DynamoDB만 사용한다
- 빠르게 구현해야 한다
- 캐시 로직을 자동화하고 싶다
- DynamoDB API를 그대로 유지하고 싶다

ElastiCache를 고르는 경우는 이렇다.

- 캐싱 로직이 복잡하다
- DynamoDB 외 다른 소스도 캐시해야 한다
- 여러 데이터 타입을 다룬다
- TTL을 세밀하게 제어해야 한다

## 동작 방식

### Write-Through Cache

DAX는 Write-Through 방식이다.

읽기 요청은 6단계를 거친다.

1. 애플리케이션이 DAX에 요청
2. DAX 캐시 확인
3. 있으면 반환 (캐시 히트)
4. 없으면 DynamoDB 조회 (캐시 미스)
5. DAX에 저장
6. 반환

쓰기 요청은 4단계다.

1. 애플리케이션이 DAX에 쓰기 요청
2. DAX가 DynamoDB에 쓰기
3. 쓰기 성공하면 DAX 캐시 업데이트
4. 반환

쓰기도 DAX를 거친다. 캐시가 항상 최신 상태로 유지된다.

### Cache Types

DAX는 두 가지 캐시를 제공한다.

Item Cache는 GetItem, BatchGetItem 결과를 캐시한다.

- Primary Key로 조회한 결과
- 기본 TTL: 5분

Query Cache는 Query, Scan 결과를 캐시한다.

- 쿼리 파라미터가 같으면 캐시 히트
- 기본 TTL: 5분

## 기본 사용

### 클러스터 생성

콘솔에서 만드는 순서는 이렇다.

1. DynamoDB 콘솔 → DAX
2. "Create cluster" 클릭
3. 클러스터 이름 입력
4. 노드 타입 선택 (dax.t3.small)
5. 노드 개수 선택 (3개 권장)
6. VPC, 서브넷 선택
7. 보안 그룹 설정
8. 생성

CLI로 만들 때는 아래 명령을 쓴다.

```bash
aws dax create-cluster \
  --cluster-name my-dax-cluster \
  --node-type dax.t3.small \
  --replication-factor 3 \
  --iam-role-arn arn:aws:iam::123456789012:role/DAXServiceRole \
  --subnet-group my-subnet-group \
  --security-group-ids sg-12345678
```

### 애플리케이션 연동

기존 코드는 DynamoDB DocumentClient로 읽는다.

```javascript
const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

const result = await dynamodb.get({
  TableName: 'Users',
  Key: { user_id: 'user_123' }
}).promise();
```

DAX로 바꾼 코드는 클라이언트와 엔드포인트만 다르다.

```javascript
const AmazonDaxClient = require('amazon-dax-client');
const dax = new AmazonDaxClient({
  endpoints: ['my-dax-cluster.xxx.dax-clusters.us-west-2.amazonaws.com:8111']
});

// DynamoDB DocumentClient 대신 DAX 사용
const result = await dax.get({
  TableName: 'Users',
  Key: { user_id: 'user_123' }
}).promise();
```

바뀌는 것은 `AWS.DynamoDB.DocumentClient` → `AmazonDaxClient`와 엔드포인트뿐이다. API는 동일하다.

DAX가 응답하지 않으면 DynamoDB로 직접 요청하는 페일오버가 필요하다. 그래서 DynamoDB 클라이언트도 유지한다.

```javascript
const dax = new AmazonDaxClient({ endpoints: [...] });
const dynamodb = new AWS.DynamoDB.DocumentClient();

async function getUser(userId) {
  try {
    return await dax.get({
      TableName: 'Users',
      Key: { user_id: userId }
    }).promise();
  } catch (err) {
    console.error('DAX error, falling back to DynamoDB:', err);
    return await dynamodb.get({
      TableName: 'Users',
      Key: { user_id: userId }
    }).promise();
  }
}
```

## 캐시 동작

### Item Cache

GetItem과 BatchGetItem의 결과를 캐시한다. 같은 Key를 두 번 조회하면 두 번째부터 DAX 캐시에서 나온다.

```javascript
// 첫 요청 - DynamoDB 조회
const user1 = await dax.get({
  TableName: 'Users',
  Key: { user_id: 'user_123' }
}).promise();
// 응답 시간: 5-10ms

// 두 번째 요청 - DAX 캐시
const user2 = await dax.get({
  TableName: 'Users',
  Key: { user_id: 'user_123' }
}).promise();
// 응답 시간: 1ms 미만
```

BatchGetItem도 같은 방식이다.

```javascript
const result = await dax.batchGet({
  RequestItems: {
    'Users': {
      Keys: [
        { user_id: 'user_123' },
        { user_id: 'user_456' },
        { user_id: 'user_789' }
      ]
    }
  }
}).promise();
```

각 Item이 개별적으로 캐시된다. 일부는 캐시에서, 일부는 DynamoDB에서 읽을 수 있다.

### Query Cache

Query와 Scan의 결과를 캐시한다. 같은 쿼리를 다시 보내면 캐시 히트가 난다.

```javascript
// 첫 요청
const orders1 = await dax.query({
  TableName: 'Orders',
  KeyConditionExpression: 'user_id = :user_id',
  ExpressionAttributeValues: {
    ':user_id': 'user_123'
  }
}).promise();
// DynamoDB 조회

// 같은 쿼리 - 캐시 히트
const orders2 = await dax.query({
  TableName: 'Orders',
  KeyConditionExpression: 'user_id = :user_id',
  ExpressionAttributeValues: {
    ':user_id': 'user_123'
  }
}).promise();
// DAX 캐시
```

쿼리 파라미터가 조금만 달라도 캐시 미스가 발생한다.

```javascript
// 쿼리 1
const orders1 = await dax.query({
  KeyConditionExpression: 'user_id = :user_id',
  ExpressionAttributeValues: { ':user_id': 'user_123' },
  Limit: 10
}).promise();

// 쿼리 2 - Limit이 다름
const orders2 = await dax.query({
  KeyConditionExpression: 'user_id = :user_id',
  ExpressionAttributeValues: { ':user_id': 'user_123' },
  Limit: 20
}).promise();
```

두 쿼리는 별도로 캐시된다.

### Cache Invalidation

데이터가 변경되면 캐시가 자동으로 무효화된다. PutItem을 예로 들면 아래와 같다.

```javascript
await dax.put({
  TableName: 'Users',
  Item: {
    user_id: 'user_123',
    name: '김철수',
    email: 'kim@example.com'
  }
}).promise();
```

`user_123` Item의 캐시가 삭제된다. 다음 GetItem은 DynamoDB에서 읽는다.

UpdateItem도 같다.

```javascript
await dax.update({
  TableName: 'Users',
  Key: { user_id: 'user_123' },
  UpdateExpression: 'SET age = :age',
  ExpressionAttributeValues: { ':age': 31 }
}).promise();
```

마찬가지로 캐시가 무효화된다.

Query Cache도 무효화된다. 정확히 어떤 쿼리가 무효화되는지는 내부 로직에 달려있다.

## TTL 설정

캐시 유효 시간을 설정한다. 기본값은 Item Cache TTL 5분, Query Cache TTL 5분이다.

TTL은 클러스터 생성 시 또는 수정 시 바꾼다.

```bash
aws dax update-cluster \
  --cluster-name my-dax-cluster \
  --parameter-group-name my-parameter-group
```

Parameter Group에서 TTL을 설정한다. Parameter Group은 아래처럼 만든다.

```bash
aws dax create-parameter-group \
  --parameter-group-name my-parameter-group \
  --description "Custom TTL settings"

aws dax update-parameter-group \
  --parameter-group-name my-parameter-group \
  --parameter-name-values \
    ParameterName=query-ttl-millis,ParameterValue=300000 \
    ParameterName=record-ttl-millis,ParameterValue=300000
```

`query-ttl-millis`: Query Cache TTL (밀리초)
`record-ttl-millis`: Item Cache TTL (밀리초)

짧은 TTL(1-5분)은 이런 경우에 맞다.

- 데이터가 자주 변경됨
- 최신 데이터 중요
- 캐시 히트율 낮음

긴 TTL(10-30분)은 이런 경우에 맞다.

- 데이터가 거의 변경 안 됨
- 약간 오래된 데이터 허용
- 캐시 히트율 높음
- 비용 절감

데이터 종류별 TTL은 이 정도로 잡는다.

- 사용자 프로필: 5-10분
- 상품 정보: 10-30분
- 설정 값: 30-60분
- 실시간 순위: 1-2분

## 클러스터 구성

### 노드 개수

노드는 최소 1개, 최대 10개다.

3개를 권장한다.

- 고가용성
- 노드 1개가 죽어도 서비스 유지
- 부하 분산

1개는 개발/테스트 환경용이다.

- 단일 장애점 (SPOF)
- 프로덕션에서는 비추천

5개 이상은 트래픽이 매우 높을 때 쓴다.

- 읽기 처리량 증가

### 노드 타입

개발/테스트용 노드 타입은 이렇다.

- **dax.t3.small**: 1.5GB, 2 vCPU
- **dax.t3.medium**: 3GB, 2 vCPU

프로덕션용 노드 타입은 이렇다.

- **dax.r5.large**: 13.5GB, 2 vCPU
- **dax.r5.xlarge**: 26GB, 4 vCPU
- **dax.r5.2xlarge**: 52GB, 8 vCPU

메모리가 클수록 더 많은 데이터를 캐시할 수 있다. 노드 타입은 캐시할 데이터양, 요청 처리량, 예산으로 고른다.

시작은 작게 하고 모니터링하면서 확장한다.

### Multi-AZ

여러 가용 영역에 노드를 배치한다. 노드가 3개 이상이면 자동으로 여러 AZ에 분산된다.

- 가용 영역 장애에도 서비스 유지
- 지연 시간 최소화 (가까운 AZ 선택)

## 실무 패턴

### Hot Key 문제 해결

특정 Key에 요청이 집중되는 경우가 있다. 인기 상품 하나에 초당 10,000개 요청이 같은 product_id로 들어오는 상황이다.

```javascript
// 인기 상품 조회
// 초당 10,000개 요청이 같은 product_id로
const product = await dynamodb.get({
  TableName: 'Products',
  Key: { product_id: 'hot_product_123' }
}).promise();
```

DynamoDB는 Partition 단위로 1,000 RCU 제한이 있다. 초과하면 Throttling이 발생한다.

DAX를 쓰면 이 문제가 풀린다.

```javascript
const product = await dax.get({
  TableName: 'Products',
  Key: { product_id: 'hot_product_123' }
}).promise();
```

첫 요청만 DynamoDB로 간다. 이후는 DAX에서 처리한다. DynamoDB 부하가 99% 감소한다.

### 리더보드

게임 리더보드를 Query로 조회한다.

```javascript
const leaderboard = await dax.query({
  TableName: 'Scores',
  IndexName: 'game-score-index',
  KeyConditionExpression: 'game_id = :game_id',
  ExpressionAttributeValues: {
    ':game_id': 'game_123'
  },
  ScanIndexForward: false,  // 내림차순
  Limit: 100
}).promise();
```

이 쿼리는 세 가지 특징이 있다.

- 자주 조회됨 (초당 수천 회)
- 데이터가 자주 변경됨 (플레이어가 점수 갱신)
- Query 결과가 크다 (100개 Item)

DAX는 Query 결과 전체를 캐시한다.

- 응답 시간 10배 감소
- DynamoDB 비용 99% 감소

점수가 갱신되면 캐시가 무효화된다. TTL을 짧게 설정한다 (1-2분).

### 읽기 전용 복제본 대체

RDS의 읽기 전용 복제본처럼 사용한다. RDS Read Replica는 쓰기를 Primary에, 읽기를 Replica에 보낸다. DynamoDB + DAX는 쓰기를 DynamoDB에, 읽기를 DAX에 보낸다.

DAX가 읽기 부하를 분산한다.

## 모니터링

### CloudWatch 메트릭

주로 보는 메트릭은 이렇다.

- **CPUUtilization**: CPU 사용률
- **NetworkBytesIn/Out**: 네트워크 트래픽
- **ItemCacheHits**: Item Cache 히트 수
- **ItemCacheMisses**: Item Cache 미스 수
- **QueryCacheHits**: Query Cache 히트 수
- **QueryCacheMisses**: Query Cache 미스 수

캐시 히트율은 히트 수와 미스 수로 계산한다.

```
Item Cache Hit Rate = ItemCacheHits / (ItemCacheHits + ItemCacheMisses)
Query Cache Hit Rate = QueryCacheHits / (QueryCacheHits + QueryCacheMisses)
```

히트율 목표는 이렇다.

- 80% 이상: 좋음
- 50-80%: 보통
- 50% 미만: 나쁨

히트율이 낮으면 DAX의 효과가 적다. TTL을 늘리거나 클러스터를 크게 한다.

Evictions는 메모리가 부족해서 캐시를 삭제한 수다. 0이 좋다. 증가하면 노드 타입을 크게 한다.

### 알람 설정

캐시 미스 알람은 이렇게 건다.

```json
{
  "MetricName": "ItemCacheMisses",
  "Threshold": 1000,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

미스가 많으면 알림을 받는다. TTL이나 클러스터 크기를 조정한다.

CPU 사용률 알람은 이렇게 건다.

```json
{
  "MetricName": "CPUUtilization",
  "Threshold": 80,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

80%를 넘으면 노드를 추가하거나 타입을 크게 한다.

## DAX vs ElastiCache 비교

### 코드 수정

DAX는 클라이언트만 바꾼다.

```javascript
// 변경 전
const dynamodb = new AWS.DynamoDB.DocumentClient();

// 변경 후
const dax = new AmazonDaxClient({ endpoints: [...] });

// API는 동일
await dax.get({ TableName: 'Users', Key: { user_id: '123' } }).promise();
```

캐시 로직은 자동이다.

ElastiCache는 캐시 로직을 직접 작성한다.

```javascript
const redis = new Redis({ host: '...' });
const dynamodb = new AWS.DynamoDB.DocumentClient();

async function getUser(userId) {
  // 캐시 확인
  const cached = await redis.get(`user:${userId}`);
  if (cached) {
    return JSON.parse(cached);
  }
  
  // DynamoDB 조회
  const result = await dynamodb.get({
    TableName: 'Users',
    Key: { user_id: userId }
  }).promise();
  
  // 캐시 저장
  await redis.setex(`user:${userId}`, 300, JSON.stringify(result.Item));
  
  return result.Item;
}
```

코드가 복잡하다.

### 일관성

DAX는 일관성 유지가 쉽다.

- 쓰기가 DAX를 거친다
- 캐시가 자동으로 무효화된다

ElastiCache는 일관성 유지가 어렵다.

- 쓰기를 직접 처리해야 한다
- 캐시 무효화를 잊으면 오래된 데이터 반환

### 유연성

DAX는 제약이 있다.

- DynamoDB API만 지원
- TTL 제어가 제한적
- 복잡한 캐싱 로직 불가능

ElastiCache는 자유도가 높다.

- 모든 데이터 캐시 가능
- 세밀한 TTL 제어
- 복잡한 로직 구현 가능

### 선택 가이드

DAX를 고르는 경우는 이렇다.

- DynamoDB 전용 캐시
- 빠른 구현
- 간단한 사용
- 코드 수정 최소화
- 자동 무효화 필요

ElastiCache를 고르는 경우는 이렇다.

- 여러 소스 캐시
- 복잡한 캐싱 로직
- 세밀한 제어
- DynamoDB 외 RDS, API 등도 캐시

## 비용

### 노드 비용

us-west-2 기준 시간당 요금은 이렇다.

- **dax.t3.small**: $0.08 ($58/월)
- **dax.t3.medium**: $0.16 ($116/월)
- **dax.r5.large**: $0.45 ($328/월)
- **dax.r5.xlarge**: $0.90 ($657/월)
- **dax.r5.2xlarge**: $1.80 ($1,314/월)

클러스터 비용은 노드 3개 × 노드 비용이다. dax.r5.large × 3이면 $0.45 × 3 × 730시간 = $985/월이다.

### 비용 vs 절감

DynamoDB 읽기 비용은 이렇다.

- On-Demand: $1.25 per million reads
- Provisioned: $0.09 per 100 RCU per hour

초당 1,000 reads인 워크로드를 예로 들면 시간당 3,600,000 reads, 월 2.6B reads다.

DynamoDB On-Demand만 쓰면 2.6B × $1.25/million = $3,250/월이다.

DAX를 함께 쓰면 비용이 이렇게 나뉜다.

- DAX: $985/월
- DynamoDB: 캐시 히트율 95%
- DynamoDB 읽기: 2.6B × 5% × $1.25/million = $163/월
- 합계: $1,148/월

절감액은 $2,102/월(65% 감소)이다. 읽기 트래픽이 많을수록 DAX의 비용 절감 효과가 크다.

## 주의사항

### Eventually Consistent

DAX는 DynamoDB의 최종 일관성을 따른다. 쓰기 직후에 읽으면 문제가 생길 수 있다.

```javascript
// 쓰기
await dax.put({ TableName: 'Users', Item: { user_id: '123', name: '김철수' } }).promise();

// 즉시 읽기
const user = await dax.get({ TableName: 'Users', Key: { user_id: '123' } }).promise();
```

쓰기 직후 읽기하면 이전 데이터가 반환될 수 있다. 밀리초 단위의 지연이 있다.

Strongly Consistent Read를 쓰면 해결된다.

```javascript
const user = await dax.get({
  TableName: 'Users',
  Key: { user_id: '123' },
  ConsistentRead: true  // 강한 일관성
}).promise();
```

캐시를 건너뛰고 DynamoDB에서 직접 읽는다. 느리지만 정확하다.

### 쓰기 성능

DAX를 거치면 쓰기가 약간 느려진다. DynamoDB에 직접 쓰면 응답 시간이 5-10ms이고, DAX를 경유하면 10-15ms다.

네트워크 홉이 하나 추가된다. 읽기 성능을 위해 약간의 쓰기 지연을 감수한다.

### VPC 내부에만

DAX는 VPC 내부에서만 접근 가능하다. 인터넷에서 직접 접근할 수 없다.

Lambda 함수가 DAX에 접근하려면 VPC 내에 배치해야 한다.

```javascript
// Lambda in VPC
exports.handler = async (event) => {
  const dax = new AmazonDaxClient({
    endpoints: ['my-dax-cluster.xxx.dax-clusters.us-west-2.amazonaws.com:8111']
  });
  
  const result = await dax.get({
    TableName: 'Users',
    Key: { user_id: event.userId }
  }).promise();
  
  return result.Item;
};
```

VPC Lambda는 Cold Start가 느리다. 트레이드오프를 고려한다.

## 참고

- AWS DAX 개발자 가이드: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html
- DAX 요금: https://aws.amazon.com/dynamodb/pricing/
- DAX SDK: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.client.html
- 모범 사례: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.client.run-application-nodejs.html

