---
title: AWS DynamoDB
tags: [aws, dynamodb, nosql, database, key-value, serverless]
updated: 2026-01-18
---

# AWS DynamoDB

## 개요

DynamoDB는 AWS의 완전 관리형 NoSQL 데이터베이스다. Key-Value 스토어와 Document 스토어로 사용할 수 있다. 서버를 관리할 필요가 없고, 자동으로 확장된다. 밀리초 단위의 빠른 응답 속도를 제공한다.

### NoSQL이란

NoSQL은 관계형 데이터베이스(RDS)와 다른 방식으로 데이터를 저장한다.

**관계형 데이터베이스(RDS):**
- 테이블에 행과 열로 저장
- SQL로 쿼리
- JOIN으로 테이블 연결
- 스키마가 고정됨
- ACID 트랜잭션 보장

**NoSQL(DynamoDB):**
- Key-Value 쌍으로 저장
- API로 쿼리
- JOIN 없음
- 스키마가 유연함
- 최종 일관성 (선택적으로 강한 일관성)

### 왜 DynamoDB가 필요한가

RDS로 충분한 경우도 많다. 하지만 다음 상황에서는 DynamoDB가 더 적합하다.

**1. 매우 높은 처리량이 필요할 때**

**문제:**
RDS는 단일 서버로 동작한다. CPU, 메모리, 네트워크에 한계가 있다.

**예시:**
온라인 게임 서버를 운영한다. 동시 접속자 100만 명. 초당 읽기 요청이 10만 건.

RDS로는 불가능하다. 읽기 전용 복제본을 여러 개 만들어도 한계가 있다.

**DynamoDB의 해결:**
자동으로 데이터를 여러 서버에 분산한다. 처리량에 제한이 없다. 초당 수천만 요청도 처리한다.

**2. 예측할 수 없는 트래픽 패턴**

**문제:**
RDS는 인스턴스 크기를 사전에 정해야 한다. 트래픽이 급증하면 인스턴스를 수동으로 확장해야 한다. 시간이 걸린다.

**예시:**
쇼핑몰을 운영한다. 평소에는 초당 100건 요청. 블랙프라이데이에는 초당 10,000건 요청.

RDS를 큰 인스턴스로 미리 준비하면 비용 낭비다. 작은 인스턴스로 시작하면 블랙프라이데이에 다운된다.

**DynamoDB의 해결:**
On-Demand 모드를 사용하면 자동으로 확장된다. 트래픽에 맞춰 용량이 조절된다. 사용한 만큼만 비용을 낸다.

**3. 단순한 Key-Value 조회**

**문제:**
RDS는 복잡한 쿼리에 강하다. 하지만 단순한 Key로 조회하는 경우에는 오버헤드가 있다.

**예시:**
사용자 세션 데이터를 저장한다. session_id로 조회한다.

```sql
SELECT * FROM sessions WHERE session_id = 'abc123';
```

RDS는 SQL을 파싱하고, 실행 계획을 세우고, 인덱스를 찾는다. 불필요한 과정이 많다.

**DynamoDB의 해결:**
Key로 직접 접근한다. 중간 과정이 없다. 1-2ms 응답 속도.

```javascript
await dynamodb.get({
  TableName: 'sessions',
  Key: { session_id: 'abc123' }
});
```

**4. 서버 관리가 부담스러울 때**

**RDS의 운영:**
- 인스턴스 크기 선택
- 백업 설정
- 패치 적용
- 장애 조치 설정
- 성능 모니터링
- 디스크 공간 관리

**DynamoDB의 운영:**
- 테이블 생성
- 끝

나머지는 AWS가 자동으로 처리한다.

### DynamoDB가 적합하지 않은 경우

**복잡한 JOIN:**
여러 테이블을 JOIN해서 조회해야 하는 경우. DynamoDB는 JOIN을 지원하지 않는다. 애플리케이션에서 여러 번 조회해야 한다.

**복잡한 트랜잭션:**
여러 테이블의 데이터를 동시에 수정하고 일관성을 보장해야 하는 경우. DynamoDB도 트랜잭션을 지원하지만 제약이 많다.

**집계 쿼리:**
SUM, AVG, GROUP BY 같은 집계 쿼리. DynamoDB는 지원하지 않는다. 데이터를 모두 읽어서 애플리케이션에서 계산해야 한다.

**기존 SQL 애플리케이션:**
이미 SQL로 작성된 애플리케이션. DynamoDB로 마이그레이션하려면 모든 쿼리를 다시 작성해야 한다.

## 핵심 개념

### Table (테이블)

데이터를 저장하는 컨테이너다. RDS의 테이블과 비슷하다.

**예시:**
- `Users`: 사용자 정보
- `Orders`: 주문 정보
- `Products`: 상품 정보

### Item (아이템)

테이블의 개별 데이터다. RDS의 행(row)과 비슷하다.

**예시:**
Users 테이블의 한 사용자:
```json
{
  "user_id": "user_123",
  "name": "김철수",
  "email": "kim@example.com",
  "age": 30
}
```

### Attribute (속성)

Item의 개별 필드다. RDS의 열(column)과 비슷하다.

**예시:**
- `user_id`: 사용자 ID
- `name`: 이름
- `email`: 이메일
- `age`: 나이

**중요:** DynamoDB는 스키마가 없다. 각 Item이 다른 Attribute를 가질 수 있다.

**예시:**
```json
// Item 1
{
  "user_id": "user_123",
  "name": "김철수",
  "email": "kim@example.com"
}

// Item 2 - age 추가
{
  "user_id": "user_456",
  "name": "이영희",
  "email": "lee@example.com",
  "age": 25
}

// Item 3 - phone 추가
{
  "user_id": "user_789",
  "name": "박민수",
  "phone": "010-1234-5678"
}
```

모두 같은 테이블에 저장할 수 있다.

### Primary Key (기본 키)

Item을 고유하게 식별하는 키다. 필수다.

**두 가지 타입:**

**1. Partition Key (단순 기본 키):**
하나의 Attribute로 구성된다.

**예시:**
```javascript
{
  TableName: 'Users',
  KeySchema: [
    { AttributeName: 'user_id', KeyType: 'HASH' }
  ]
}
```

`user_id`가 Primary Key다. `user_id`로 Item을 조회한다.

**2. Partition Key + Sort Key (복합 기본 키):**
두 개의 Attribute로 구성된다.

**예시:**
```javascript
{
  TableName: 'Orders',
  KeySchema: [
    { AttributeName: 'user_id', KeyType: 'HASH' },
    { AttributeName: 'order_date', KeyType: 'RANGE' }
  ]
}
```

`user_id`와 `order_date`의 조합이 Primary Key다.
- 같은 `user_id`에 여러 주문이 있을 수 있다
- `order_date`로 정렬된다
- 특정 사용자의 특정 날짜 주문을 조회할 수 있다

**Partition Key의 역할:**
데이터를 여러 서버에 분산한다. 같은 Partition Key를 가진 Item은 같은 서버에 저장된다.

**중요:** Partition Key를 잘 선택해야 한다. 특정 Partition Key에 데이터가 몰리면 성능이 나빠진다.

**나쁜 예:**
```javascript
// status를 Partition Key로 사용
KeySchema: [
  { AttributeName: 'status', KeyType: 'HASH' }
]
```

대부분의 주문이 'completed' 상태다. 모든 데이터가 하나의 서버에 집중된다. 병목이 발생한다.

**좋은 예:**
```javascript
// user_id를 Partition Key로 사용
KeySchema: [
  { AttributeName: 'user_id', KeyType: 'HASH' },
  { AttributeName: 'order_date', KeyType: 'RANGE' }
]
```

사용자마다 데이터가 분산된다. 부하가 골고루 분산된다.

## 읽기와 쓰기

### GetItem (항목 가져오기)

Primary Key로 Item을 하나 가져온다. 가장 빠른 방법이다.

**예시:**
```javascript
const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

const result = await dynamodb.get({
  TableName: 'Users',
  Key: {
    user_id: 'user_123'
  }
}).promise();

console.log(result.Item);
// { user_id: 'user_123', name: '김철수', email: 'kim@example.com' }
```

**응답 시간:** 1-2ms

### PutItem (항목 넣기)

Item을 저장한다. 같은 Primary Key가 있으면 덮어쓴다.

**예시:**
```javascript
await dynamodb.put({
  TableName: 'Users',
  Item: {
    user_id: 'user_123',
    name: '김철수',
    email: 'kim@example.com',
    age: 30,
    created_at: Date.now()
  }
}).promise();
```

### UpdateItem (항목 수정)

Item의 일부 Attribute만 수정한다.

**예시:**
```javascript
await dynamodb.update({
  TableName: 'Users',
  Key: {
    user_id: 'user_123'
  },
  UpdateExpression: 'SET age = :age, updated_at = :updated_at',
  ExpressionAttributeValues: {
    ':age': 31,
    ':updated_at': Date.now()
  }
}).promise();
```

`age`와 `updated_at`만 수정된다. 나머지 Attribute는 그대로다.

**조건부 수정:**
특정 조건을 만족할 때만 수정한다.

```javascript
await dynamodb.update({
  TableName: 'Users',
  Key: {
    user_id: 'user_123'
  },
  UpdateExpression: 'SET login_count = login_count + :inc',
  ConditionExpression: 'attribute_exists(user_id)',
  ExpressionAttributeValues: {
    ':inc': 1
  }
}).promise();
```

`user_id`가 존재할 때만 `login_count`를 증가한다. 존재하지 않으면 에러를 반환한다.

### DeleteItem (항목 삭제)

Item을 삭제한다.

**예시:**
```javascript
await dynamodb.delete({
  TableName: 'Users',
  Key: {
    user_id: 'user_123'
  }
}).promise();
```

### Query (쿼리)

Partition Key로 여러 Item을 조회한다. Sort Key 범위를 지정할 수 있다.

**예시:**
특정 사용자의 최근 30일 주문을 조회한다.

```javascript
const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);

const result = await dynamodb.query({
  TableName: 'Orders',
  KeyConditionExpression: 'user_id = :user_id AND order_date > :date',
  ExpressionAttributeValues: {
    ':user_id': 'user_123',
    ':date': thirtyDaysAgo
  }
}).promise();

console.log(result.Items);
// [{ user_id: 'user_123', order_date: 1234567890, ... }, ...]
```

**효율적:** Partition Key로 데이터 위치를 찾고, Sort Key로 필터링한다. 빠르다.

**제약:** Partition Key는 필수다. Partition Key 없이 Sort Key만으로는 조회할 수 없다.

### Scan (스캔)

테이블 전체를 읽는다. 매우 느리다. 피해야 한다.

**예시:**
나이가 30세 이상인 모든 사용자를 조회한다.

```javascript
const result = await dynamodb.scan({
  TableName: 'Users',
  FilterExpression: 'age >= :age',
  ExpressionAttributeValues: {
    ':age': 30
  }
}).promise();
```

**문제:**
1. 테이블의 모든 Item을 읽는다
2. 각 Item을 필터링한다
3. 데이터가 많으면 몇 초에서 몇 분이 걸린다
4. 비용이 많이 든다

**대안:**
Global Secondary Index를 사용한다.

## Secondary Index (보조 인덱스)

Primary Key가 아닌 Attribute로 조회하고 싶을 때 사용한다.

### Global Secondary Index (GSI)

완전히 새로운 Primary Key로 조회할 수 있다.

**상황:**
Users 테이블의 Primary Key는 `user_id`다. 하지만 `email`로 사용자를 찾고 싶다.

**해결:**
GSI를 생성한다.

```javascript
{
  TableName: 'Users',
  GlobalSecondaryIndexes: [
    {
      IndexName: 'email-index',
      KeySchema: [
        { AttributeName: 'email', KeyType: 'HASH' }
      ],
      Projection: {
        ProjectionType: 'ALL'  // 모든 Attribute 포함
      }
    }
  ]
}
```

**조회:**
```javascript
const result = await dynamodb.query({
  TableName: 'Users',
  IndexName: 'email-index',
  KeyConditionExpression: 'email = :email',
  ExpressionAttributeValues: {
    ':email': 'kim@example.com'
  }
}).promise();
```

`email`로 빠르게 조회할 수 있다.

**주의:**
GSI는 별도의 용량을 소비한다. GSI에 쓰기를 할 때도 비용이 발생한다. GSI를 너무 많이 만들면 비용이 증가한다.

### Local Secondary Index (LSI)

같은 Partition Key를 유지하고 다른 Sort Key를 사용한다.

**상황:**
Orders 테이블의 Primary Key는 `user_id` (Partition) + `order_date` (Sort)다. 같은 사용자의 주문을 금액 순으로 정렬하고 싶다.

**해결:**
LSI를 생성한다.

```javascript
{
  TableName: 'Orders',
  KeySchema: [
    { AttributeName: 'user_id', KeyType: 'HASH' },
    { AttributeName: 'order_date', KeyType: 'RANGE' }
  ],
  LocalSecondaryIndexes: [
    {
      IndexName: 'user-amount-index',
      KeySchema: [
        { AttributeName: 'user_id', KeyType: 'HASH' },
        { AttributeName: 'amount', KeyType: 'RANGE' }
      ],
      Projection: {
        ProjectionType: 'ALL'
      }
    }
  ]
}
```

**조회:**
```javascript
const result = await dynamodb.query({
  TableName: 'Orders',
  IndexName: 'user-amount-index',
  KeyConditionExpression: 'user_id = :user_id AND amount > :amount',
  ExpressionAttributeValues: {
    ':user_id': 'user_123',
    ':amount': 100000
  }
}).promise();
```

같은 사용자의 10만원 이상 주문을 금액 순으로 조회한다.

**제약:**
- LSI는 테이블 생성 시에만 만들 수 있다
- 나중에 추가할 수 없다
- 최대 5개까지만 만들 수 있다

**GSI는 나중에 추가할 수 있다.** 보통 GSI를 더 많이 사용한다.

## 용량 모드

DynamoDB는 두 가지 용량 모드를 제공한다.

### Provisioned (프로비저닝)

읽기/쓰기 용량을 미리 지정한다.

**설정:**
```javascript
{
  TableName: 'Users',
  BillingMode: 'PROVISIONED',
  ProvisionedThroughput: {
    ReadCapacityUnits: 5,
    WriteCapacityUnits: 5
  }
}
```

**Read Capacity Unit (RCU):**
- 1 RCU = 초당 4KB 읽기 1회 (강한 일관성)
- 1 RCU = 초당 4KB 읽기 2회 (최종 일관성)

**Write Capacity Unit (WCU):**
- 1 WCU = 초당 1KB 쓰기 1회

**예시:**
- Item 크기: 8KB
- 초당 읽기: 100회 (강한 일관성)
- 초당 쓰기: 50회

**필요한 용량:**
- RCU: (8KB / 4KB) × 100 = 200
- WCU: (8KB / 1KB) × 50 = 400

**비용:**
- 용량을 예약하고 시간당 비용을 낸다
- 사용 여부와 관계없이 비용이 발생한다

**장점:**
- 일정한 비용
- 예측 가능

**단점:**
- 트래픽이 적어도 비용 발생
- 용량 초과 시 요청 거부 (Throttling)

### On-Demand (온디맨드)

용량을 미리 지정하지 않는다. 사용한 만큼 비용을 낸다.

**설정:**
```javascript
{
  TableName: 'Users',
  BillingMode: 'PAY_PER_REQUEST'
}
```

**동작:**
- 트래픽에 맞춰 자동으로 확장
- 용량 제한 없음
- 요청당 비용 부과

**비용:**
- 읽기 요청: $1.25 per million
- 쓰기 요청: $6.25 per million

Provisioned보다 비싸다. 하지만 트래픽이 적거나 예측할 수 없으면 더 저렴할 수 있다.

**장점:**
- 용량 계획 불필요
- 자동 확장
- 트래픽이 적으면 비용 절감

**단점:**
- 요청당 비용이 높음
- 트래픽이 많으면 비용 증가

### 선택 기준

**Provisioned를 선택:**
- 트래픽이 예측 가능
- 일정한 부하
- 높은 트래픽

**On-Demand를 선택:**
- 트래픽이 예측 불가능
- 간헐적인 부하
- 새로운 서비스 (트래픽 패턴 모름)
- 개발/테스트 환경

## DynamoDB Streams

Item이 변경되면 이벤트를 발생시킨다. Lambda로 처리할 수 있다.

### 동작 방식

**활성화:**
```javascript
{
  TableName: 'Users',
  StreamSpecification: {
    StreamEnabled: true,
    StreamViewType: 'NEW_AND_OLD_IMAGES'
  }
}
```

**StreamViewType:**
- **KEYS_ONLY**: Primary Key만
- **NEW_IMAGE**: 변경 후 Item 전체
- **OLD_IMAGE**: 변경 전 Item 전체
- **NEW_AND_OLD_IMAGES**: 변경 전후 모두

**이벤트:**
Item이 추가, 수정, 삭제되면 Stream에 이벤트가 기록된다.

### Lambda 연동

**예시:**
사용자가 회원가입하면 환영 이메일을 보낸다.

```javascript
exports.handler = async (event) => {
  for (const record of event.Records) {
    if (record.eventName === 'INSERT') {
      const newUser = record.dynamodb.NewImage;
      
      await sendWelcomeEmail({
        email: newUser.email.S,
        name: newUser.name.S
      });
    }
  }
};
```

**사용 사례:**
- 실시간 데이터 복제
- 감사 로그 생성
- 알림 발송
- 검색 인덱스 업데이트
- 캐시 무효화

## 트랜잭션

여러 Item을 원자적으로 처리한다. 모두 성공하거나 모두 실패한다.

### TransactWriteItems (쓰기 트랜잭션)

**예시:**
주문 생성과 재고 감소를 하나의 트랜잭션으로 처리한다.

```javascript
await dynamodb.transactWrite({
  TransactItems: [
    {
      Put: {
        TableName: 'Orders',
        Item: {
          order_id: 'order_123',
          user_id: 'user_123',
          product_id: 'prod_456',
          quantity: 2
        }
      }
    },
    {
      Update: {
        TableName: 'Products',
        Key: { product_id: 'prod_456' },
        UpdateExpression: 'SET stock = stock - :qty',
        ConditionExpression: 'stock >= :qty',
        ExpressionAttributeValues: {
          ':qty': 2
        }
      }
    }
  ]
}).promise();
```

**동작:**
1. 주문을 생성한다
2. 재고를 2개 감소한다
3. 재고가 부족하면 모두 롤백한다

**제약:**
- 최대 100개 Item
- 같은 AWS 계정, 같은 리전
- 4MB 크기 제한
- 비용이 2배 (트랜잭션 오버헤드)

### TransactGetItems (읽기 트랜잭션)

여러 Item을 일관되게 읽는다.

```javascript
const result = await dynamodb.transactGet({
  TransactItems: [
    {
      Get: {
        TableName: 'Users',
        Key: { user_id: 'user_123' }
      }
    },
    {
      Get: {
        TableName: 'Orders',
        Key: { order_id: 'order_123' }
      }
    }
  ]
}).promise();
```

모든 Item을 같은 시점에서 읽는다.

## TTL (Time To Live)

일정 시간이 지나면 Item을 자동으로 삭제한다.

### 설정

**활성화:**
```javascript
await dynamodb.updateTimeToLive({
  TableName: 'Sessions',
  TimeToLiveSpecification: {
    Enabled: true,
    AttributeName: 'expire_at'
  }
}).promise();
```

**Item 저장:**
```javascript
await dynamodb.put({
  TableName: 'Sessions',
  Item: {
    session_id: 'sess_123',
    user_id: 'user_123',
    data: '...',
    expire_at: Math.floor(Date.now() / 1000) + (30 * 60)  // 30분 후
  }
}).promise();
```

`expire_at`에 Unix 타임스탬프를 저장한다. 해당 시간이 지나면 자동으로 삭제된다.

**주의:**
- 삭제가 즉시 일어나지 않는다
- 보통 48시간 이내에 삭제된다
- 삭제 비용이 없다 (무료)

**사용 사례:**
- 세션 데이터
- 임시 데이터
- 캐시
- 로그 (일정 기간 보관)

## 백업과 복원

### On-Demand Backup

수동으로 백업을 생성한다.

```javascript
await dynamodb.createBackup({
  TableName: 'Users',
  BackupName: 'users-backup-2026-01-18'
}).promise();
```

**특징:**
- 전체 테이블 백업
- 다운타임 없음
- 성능 영향 없음
- 백업 크기만큼 비용 발생

**복원:**
```javascript
await dynamodb.restoreTableFromBackup({
  TargetTableName: 'Users-Restored',
  BackupArn: 'arn:aws:dynamodb:...:backup/...'
}).promise();
```

새로운 테이블로 복원된다. 기존 테이블은 그대로 유지된다.

### Point-in-Time Recovery (PITR)

지속적으로 백업한다. 특정 시점으로 복원할 수 있다.

**활성화:**
```javascript
await dynamodb.updateContinuousBackups({
  TableName: 'Users',
  PointInTimeRecoverySpecification: {
    PointInTimeRecoveryEnabled: true
  }
}).promise();
```

**복원:**
최근 35일 내의 임의 시점으로 복원할 수 있다.

```javascript
await dynamodb.restoreTableToPointInTime({
  SourceTableName: 'Users',
  TargetTableName: 'Users-Restored',
  RestoreDateTime: new Date('2026-01-17T10:30:00Z')
}).promise();
```

**비용:**
- 테이블 크기의 약 20% 추가 비용
- 데이터 손실 방지에 필수

## 실무 패턴

### 단일 테이블 설계

여러 엔티티를 하나의 테이블에 저장한다.

**배경:**
DynamoDB는 JOIN을 지원하지 않는다. 여러 테이블을 조회하려면 여러 번 요청해야 한다. 느리고 비용이 증가한다.

**해결:**
관련된 데이터를 같은 테이블에 저장한다.

**예시:**
사용자와 주문을 같은 테이블에 저장한다.

```javascript
// 사용자
{
  PK: 'USER#user_123',
  SK: 'PROFILE',
  name: '김철수',
  email: 'kim@example.com'
}

// 사용자의 주문
{
  PK: 'USER#user_123',
  SK: 'ORDER#2026-01-18#order_456',
  amount: 150000,
  status: 'completed'
}

{
  PK: 'USER#user_123',
  SK: 'ORDER#2026-01-17#order_789',
  amount: 80000,
  status: 'pending'
}
```

**조회:**
```javascript
// 사용자와 주문을 한 번에 조회
const result = await dynamodb.query({
  TableName: 'AppData',
  KeyConditionExpression: 'PK = :pk',
  ExpressionAttributeValues: {
    ':pk': 'USER#user_123'
  }
}).promise();
```

사용자 정보와 모든 주문이 한 번에 조회된다. 빠르고 비용이 절감된다.

### 복합 Sort Key

Sort Key에 여러 정보를 담는다.

**예시:**
```javascript
{
  PK: 'USER#user_123',
  SK: 'ORDER#2026-01-18#order_456',
  ...
}
```

`SK`에 타입, 날짜, ID를 모두 포함한다.

**장점:**
```javascript
// 특정 날짜의 주문만 조회
KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
ExpressionAttributeValues: {
  ':pk': 'USER#user_123',
  ':sk': 'ORDER#2026-01-18'
}
```

날짜별로 쉽게 필터링할 수 있다.

## 성능 최적화

### Batch 작업

여러 Item을 한 번에 처리한다.

**BatchGetItem:**
```javascript
const result = await dynamodb.batchGet({
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

3개의 Item을 한 번의 요청으로 가져온다. 네트워크 왕복이 줄어든다.

**BatchWriteItem:**
```javascript
await dynamodb.batchWrite({
  RequestItems: {
    'Users': [
      {
        PutRequest: {
          Item: { user_id: 'user_123', name: '김철수' }
        }
      },
      {
        PutRequest: {
          Item: { user_id: 'user_456', name: '이영희' }
        }
      }
    ]
  }
}).promise();
```

최대 25개까지 한 번에 처리할 수 있다.

### Eventually Consistent Reads

최종 일관성 읽기를 사용한다. 빠르고 저렴하다.

```javascript
const result = await dynamodb.get({
  TableName: 'Users',
  Key: { user_id: 'user_123' },
  ConsistentRead: false  // 최종 일관성 (기본값)
}).promise();
```

**최종 일관성:**
- 최신 데이터가 아닐 수 있다
- 보통 1초 이내에 반영된다
- RCU가 절반

**강한 일관성:**
- 항상 최신 데이터
- RCU가 2배

대부분의 경우 최종 일관성으로 충분하다.

### Projection 최소화

GSI에서 필요한 Attribute만 포함한다.

```javascript
{
  IndexName: 'email-index',
  Projection: {
    ProjectionType: 'INCLUDE',
    NonKeyAttributes: ['name', 'phone']  // 필요한 것만
  }
}
```

GSI 크기가 줄어든다. 비용이 절감된다.

## 비용 최적화

### Reserved Capacity

1년 또는 3년 예약하면 할인을 받는다.

**할인율:**
- 1년: 약 40% 할인
- 3년: 약 60% 할인

트래픽이 일정하면 Reserved Capacity를 구매한다.

### Auto Scaling

트래픽에 맞춰 용량을 자동 조절한다.

```javascript
{
  TargetTrackingScalingPolicyConfiguration: {
    TargetValue: 70.0,  // CPU 70% 유지
    ScaleInCooldown: 60,
    ScaleOutCooldown: 60
  }
}
```

사용률이 70%를 넘으면 용량을 증가한다. 70% 미만이면 감소한다.

### 불필요한 GSI 삭제

사용하지 않는 GSI는 삭제한다. GSI도 용량을 소비한다.

**확인:**
CloudWatch에서 GSI 사용량을 확인한다. 읽기가 0이면 삭제를 고려한다.

## 참고

- AWS DynamoDB 개발자 가이드: https://docs.aws.amazon.com/dynamodb/
- DynamoDB 요금: https://aws.amazon.com/dynamodb/pricing/
- 단일 테이블 설계: https://aws.amazon.com/blogs/compute/creating-a-single-table-design-with-amazon-dynamodb/
- DynamoDB 모범 사례: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html

