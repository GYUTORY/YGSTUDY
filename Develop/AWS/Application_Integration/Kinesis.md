---
title: AWS Kinesis
tags: [aws, kinesis, streaming, real-time, data-processing, analytics]
updated: 2026-01-18
---

# AWS Kinesis

## 개요

AWS Kinesis는 실시간 스트리밍 데이터를 수집하고 처리하는 서비스다. 대량의 데이터를 실시간으로 받아서 분석하고, 저장하고, 다른 시스템으로 전달한다. 로그, 클릭스트림, IoT 센서 데이터, 금융 거래 데이터 등을 초 단위로 처리할 수 있다.

### 왜 Kinesis가 필요할까

과거에는 실시간 데이터 처리가 어려웠다.

**전통적인 방식의 문제:**

**배치 처리의 한계:**
로그 데이터를 분석한다고 하자. 전통적인 방식은 이렇다:
1. 서버가 로그 파일에 데이터를 쓴다
2. 매일 자정에 로그 파일을 수집한다
3. S3에 업로드한다
4. 다음날 아침에 분석 작업을 시작한다
5. 분석 결과는 오후에 나온다

문제가 생겼을 때는 이미 늦다. 어제 일어난 일을 오늘 오후에 안다. 24시간 이상 지연된다.

**SQS의 한계:**
SQS도 메시지를 처리한다. 하지만 실시간 스트리밍에는 부족하다.

**SQS의 제약:**
- 메시지 순서 보장이 어렵다 (Standard Queue)
- FIFO Queue는 초당 300개로 제한된다
- 여러 Consumer가 같은 메시지를 받을 수 없다
- 시간 기반 처리가 어렵다 (최근 1시간 데이터만 분석)

**예시:**
e커머스 사이트의 실시간 추천 시스템을 만든다. 사용자가 상품을 클릭하면 즉시 추천을 업데이트해야 한다.

SQS로는 어렵다:
- 클릭 이벤트가 초당 10,000개 발생한다
- 순서가 중요하다. 최신 클릭이 가장 중요하다
- 여러 시스템이 같은 데이터를 사용한다 (추천, 분석, 저장)
- 최근 5분 데이터만 필요하다

**Kinesis의 해결:**

**실시간 처리:**
데이터가 들어오는 즉시 처리한다. 지연 시간이 1초 미만이다. 문제가 생기면 즉시 감지하고 대응한다.

**순서 보장:**
데이터가 들어온 순서대로 처리된다. Partition Key를 사용해 관련 데이터를 묶어서 순서를 보장한다.

**높은 처리량:**
초당 수백만 개의 레코드를 처리한다. 샤드를 추가해 처리량을 늘린다.

**여러 Consumer:**
같은 데이터를 여러 애플리케이션이 동시에 읽을 수 있다. 추천 시스템, 분석 시스템, 저장 시스템이 모두 같은 스트림을 읽는다.

**시간 기반 처리:**
최근 24시간 데이터를 언제든 다시 읽을 수 있다. 실수로 잘못 처리했으면 처음부터 다시 읽어서 처리한다.

### 실제 사용 사례

**실시간 대시보드:**
웹사이트의 실시간 트래픽을 모니터링한다. 페이지뷰, 클릭, 에러가 발생하면 즉시 대시보드에 표시된다. 트래픽이 급증하면 즉시 알림을 보낸다.

**이상 탐지:**
금융 거래를 실시간으로 분석한다. 비정상적인 패턴을 감지하면 즉시 차단한다. 사기 거래를 몇 초 안에 막는다.

**IoT 데이터 처리:**
수천 개의 센서가 데이터를 보낸다. 온도, 습도, 압력 데이터를 실시간으로 수집하고 분석한다. 이상 값이 감지되면 즉시 경고를 보낸다.

**로그 분석:**
모든 서버의 로그를 실시간으로 수집한다. 에러 로그가 급증하면 즉시 감지한다. 원인을 빠르게 파악하고 대응한다.

## Kinesis 서비스 종류

Kinesis는 4가지 서비스로 구성된다. 각각 다른 용도로 사용한다.

### Kinesis Data Streams

가장 기본이 되는 서비스다. 실시간 데이터 스트림을 수집하고 처리한다.

**동작 방식:**

**Producer → Stream → Consumer**

**1. Producer가 데이터를 전송:**
- 웹 서버, 모바일 앱, IoT 디바이스가 데이터를 보낸다
- Kinesis API를 사용한다: PutRecord, PutRecords
- 데이터는 JSON, 바이너리, 텍스트 등 어떤 형식이든 가능하다

**2. Stream이 데이터를 저장:**
- 데이터는 Stream에 저장된다
- 기본 24시간 보관된다 (최대 365일)
- 샤드(Shard)에 분산 저장된다

**3. Consumer가 데이터를 읽음:**
- Lambda, EC2, Kinesis Data Analytics, Kinesis Data Firehose 등
- 여러 Consumer가 동시에 읽을 수 있다
- 각 Consumer는 독립적으로 데이터를 처리한다

**주요 특징:**

**순서 보장:**
Partition Key를 사용한다. 같은 Partition Key를 가진 레코드는 같은 샤드로 간다. 같은 샤드 내에서는 순서가 보장된다.

**예시:**
사용자 클릭 이벤트를 처리한다. Partition Key를 user_id로 설정한다.
- user_123의 모든 클릭은 같은 샤드로 간다
- user_123의 클릭 순서가 보장된다
- user_456의 클릭은 다른 샤드로 갈 수 있다

**데이터 보관:**
데이터가 Stream에 보관된다. Consumer가 읽어도 삭제되지 않는다. 다른 Consumer가 다시 읽을 수 있다. 기간이 지나면 자동으로 삭제된다.

**재처리 가능:**
실수로 잘못 처리했으면 처음부터 다시 읽는다. 24시간 전 데이터부터 다시 처리할 수 있다.

### Kinesis Data Firehose

데이터를 자동으로 목적지에 전달하는 서비스다. 가장 간단하고 많이 사용한다.

**동작 방식:**

Producer → Firehose → 목적지 (S3, Redshift, Elasticsearch 등)

**자동 전달:**
- 데이터를 받으면 자동으로 목적지에 저장한다
- 배치로 묶어서 전송한다 (예: 5분마다 또는 5MB마다)
- 압축을 자동으로 수행한다 (GZIP, Snappy, Zip)
- 포맷 변환을 수행한다 (JSON을 Parquet으로)

**목적지:**
- **S3**: 데이터 레이크, 장기 보관
- **Redshift**: 데이터 웨어하우스, SQL 분석
- **Elasticsearch**: 로그 검색, 시각화
- **Splunk**: 로그 분석
- **HTTP Endpoint**: 커스텀 API

**변환 (Transform):**
Lambda 함수로 데이터를 변환할 수 있다.

**예시:**
원본 로그에서 민감한 정보를 제거한다:
1. Firehose가 로그를 받는다
2. Lambda 함수를 호출한다
3. Lambda가 이메일, 전화번호를 마스킹한다
4. 변환된 데이터를 S3에 저장한다

**실무 팁:**
가장 간단하다. 서버를 관리할 필요가 없다. 단순히 데이터를 S3에 저장하려면 Firehose를 사용한다.

### Kinesis Data Analytics

SQL이나 Apache Flink로 실시간 데이터를 분석하는 서비스다.

**동작 방식:**

Stream → Analytics → 결과 출력

**SQL 분석:**
표준 SQL로 스트리밍 데이터를 분석한다.

**예시:**
실시간으로 페이지뷰를 집계한다:

```sql
SELECT STREAM 
  page_url,
  COUNT(*) as view_count,
  STEP(event_time BY INTERVAL '1' MINUTE) as minute_window
FROM input_stream
GROUP BY 
  page_url,
  STEP(event_time BY INTERVAL '1' MINUTE)
```

매 1분마다 각 페이지의 뷰 수를 계산한다. 결과는 실시간으로 출력된다.

**Apache Flink:**
더 복잡한 처리가 필요하면 Flink를 사용한다. Java나 Scala로 코드를 작성한다.

**사용 사례:**
- 실시간 집계: 매출, 주문 수, 활성 사용자 수
- 이상 탐지: 비정상 패턴 감지
- 시계열 분석: 트렌드 분석, 예측

### Kinesis Video Streams

비디오 스트림을 실시간으로 수집하고 처리하는 서비스다. 일반적인 데이터 스트리밍과는 다르다.

**사용 사례:**
- 보안 카메라 영상 실시간 전송
- 영상 분석 (얼굴 인식, 객체 탐지)
- 원격 모니터링

대부분의 경우 Kinesis Data Streams나 Firehose를 사용한다. Video Streams는 특수한 경우에만 사용한다.

## Kinesis Data Streams 상세

가장 많이 사용하고 이해가 필요한 서비스다.

### Shard (샤드)

Shard는 Stream의 기본 단위다. 처리량을 결정한다.

**하나의 Shard 용량:**
- **쓰기**: 초당 1MB 또는 1,000개 레코드
- **읽기**: 초당 2MB (전체 Consumer 합산)

**예시 계산:**

**상황 1: 로그 수집**
- 로그 하나 크기: 1KB
- 초당 로그 발생: 5,000개
- 필요한 Shard: 5,000 ÷ 1,000 = 5개

**상황 2: 센서 데이터**
- 데이터 하나 크기: 500 bytes
- 초당 데이터 발생: 10,000개
- 데이터량: 10,000 × 500 bytes = 5MB
- 필요한 Shard: 5MB ÷ 1MB = 5개

**Shard 추가:**
처리량이 증가하면 Shard를 추가한다.

**작업 과정:**
1. CloudWatch 메트릭을 확인한다
2. WriteProvisionedThroughputExceeded 에러가 발생한다
3. Shard를 추가한다 (Reshard)
4. 5개 → 10개로 증가
5. 처리량이 2배가 된다

**Shard 제거:**
처리량이 감소하면 Shard를 제거한다. 비용을 절감한다.

**비용:**
Shard당 시간당 $0.015다. Shard 10개를 24시간 실행하면:
- 10 × $0.015 × 24 = $3.6/일
- 월 약 $108

Shard 개수를 최적화하는 것이 중요하다.

### Partition Key

데이터를 Shard에 분산하는 기준이다.

**동작 원리:**

**1. Producer가 Partition Key를 지정:**
```javascript
const params = {
  StreamName: 'my-stream',
  PartitionKey: 'user_12345',  // 이 값으로 Shard가 결정됨
  Data: JSON.stringify({
    event: 'click',
    timestamp: Date.now()
  })
};

kinesis.putRecord(params);
```

**2. Kinesis가 Shard를 선택:**
- Partition Key를 해시한다
- 해시 값으로 Shard를 결정한다
- 같은 Partition Key는 항상 같은 Shard로 간다

**3. 순서 보장:**
- 같은 Shard 내에서는 순서가 보장된다
- user_12345의 모든 이벤트는 순서대로 처리된다

**Partition Key 선택:**

**좋은 예:**
- **user_id**: 사용자별로 분산된다. 고르게 분포한다
- **device_id**: IoT 디바이스별로 분산된다
- **order_id**: 주문별로 분산된다

**나쁜 예:**
- **날짜**: 같은 날의 모든 데이터가 하나의 Shard로 간다. Hot Shard 발생
- **상수값**: 모든 데이터가 하나의 Shard로 간다. 나머지 Shard는 사용되지 않음

**실무 팁:**
Partition Key를 잘 선택해야 한다. 데이터가 고르게 분산되어야 한다. 한 Shard에 집중되면 병목이 발생한다.

### Producer (데이터 전송)

데이터를 Stream에 전송하는 방법이다.

**1. Kinesis SDK:**

직접 API를 호출한다.

**Node.js 예시:**
```javascript
const AWS = require('aws-sdk');
const kinesis = new AWS.Kinesis();

async function sendEvent(userId, event) {
  const params = {
    StreamName: 'user-events',
    PartitionKey: userId,
    Data: JSON.stringify({
      userId,
      event,
      timestamp: new Date().toISOString()
    })
  };
  
  await kinesis.putRecord(params).promise();
}

// 사용
await sendEvent('user_123', {
  type: 'page_view',
  page: '/products'
});
```

**배치 전송:**
여러 레코드를 한 번에 전송한다. 처리량이 높아진다.

```javascript
const records = users.map(user => ({
  Data: JSON.stringify(user),
  PartitionKey: user.id
}));

await kinesis.putRecords({
  StreamName: 'user-events',
  Records: records  // 최대 500개
}).promise();
```

**2. Kinesis Producer Library (KPL):**

고성능 Producer 라이브러리다. 자동으로 배치, 압축, 재시도를 처리한다.

**특징:**
- 자동 배치: 여러 레코드를 모아서 전송한다
- 자동 재시도: 실패하면 자동으로 재시도한다
- 압축: 데이터를 압축해서 전송한다
- 높은 처리량: 초당 수만 개 레코드 전송 가능

**사용 시기:**
처리량이 매우 높은 경우 (초당 수천 개 이상) KPL을 사용한다.

**3. Kinesis Agent:**

서버의 로그 파일을 자동으로 Kinesis로 전송한다.

**설정 예시:**
```json
{
  "flows": [
    {
      "filePattern": "/var/log/app/*.log",
      "kinesisStream": "app-logs",
      "partitionKeyOption": "RANDOM"
    }
  ]
}
```

Agent가 로그 파일을 모니터링한다. 새 로그가 생기면 자동으로 Kinesis로 전송한다.

### Consumer (데이터 읽기)

Stream에서 데이터를 읽는 방법이다.

**1. Lambda:**

가장 간단하다. 새 레코드가 들어오면 자동으로 Lambda가 실행된다.

**설정:**
```javascript
exports.handler = async (event) => {
  for (const record of event.Records) {
    // Base64 디코딩
    const data = Buffer.from(record.kinesis.data, 'base64').toString();
    const json = JSON.parse(data);
    
    console.log('처리:', json);
    
    // 데이터 처리
    await processEvent(json);
  }
};
```

**배치 크기:**
한 번에 몇 개의 레코드를 처리할지 설정한다.
- 배치 크기: 100 → Lambda가 최대 100개 레코드를 받는다
- 배치 윈도우: 5초 → 5초마다 또는 100개가 모이면 Lambda 실행

**2. EC2/ECS (Kinesis Client Library):**

장시간 실행되는 애플리케이션에서 사용한다.

**동작 방식:**
```javascript
const AWS = require('aws-sdk');
const kinesis = new AWS.Kinesis();

async function processRecords() {
  // Shard Iterator 획득
  const iterator = await kinesis.getShardIterator({
    StreamName: 'my-stream',
    ShardId: 'shardId-000000000000',
    ShardIteratorType: 'LATEST'  // 최신 데이터부터
  }).promise();
  
  let currentIterator = iterator.ShardIterator;
  
  while (true) {
    // 레코드 읽기
    const result = await kinesis.getRecords({
      ShardIterator: currentIterator,
      Limit: 100
    }).promise();
    
    // 레코드 처리
    for (const record of result.Records) {
      const data = Buffer.from(record.Data, 'base64').toString();
      await processEvent(JSON.parse(data));
    }
    
    // 다음 Iterator
    currentIterator = result.NextShardIterator;
    
    // 잠시 대기 (속도 제한 방지)
    await sleep(1000);
  }
}
```

**3. Kinesis Data Firehose:**

가장 간단하다. 자동으로 S3, Redshift 등에 저장한다.

**설정만 하면 됨:**
- Source: Kinesis Data Stream
- Destination: S3 버킷
- 끝

코드를 작성할 필요가 없다.

### Enhanced Fan-Out

여러 Consumer가 독립적으로 데이터를 읽을 수 있게 한다.

**문제 상황:**

**일반 Consumer:**
- 하나의 Shard는 초당 2MB 읽기를 제공한다
- 3개의 Consumer가 있으면 각각 0.67MB씩 나눠 가진다
- Consumer가 많아지면 각자의 처리량이 줄어든다

**Enhanced Fan-Out:**
- 각 Consumer가 독립적으로 초당 2MB를 받는다
- Consumer가 3개면 총 6MB 읽기 가능
- Consumer끼리 영향을 주지 않는다

**언제 사용하나:**
- Consumer가 2개 이상인 경우
- 각 Consumer가 높은 처리량을 필요로 하는 경우
- 지연 시간을 최소화하고 싶은 경우 (70ms 이하)

**비용:**
추가 비용이 발생한다. Consumer당 시간당 $0.015, 데이터 전송 GB당 $0.013. 필요한 경우에만 사용한다.

## Kinesis Data Firehose 상세

가장 많이 사용하는 서비스다. 간단하고 관리가 쉽다.

### S3로 자동 저장

가장 일반적인 사용 사례다.

**설정:**

**1. Delivery Stream 생성:**
- Source: Direct PUT (또는 Kinesis Data Stream)
- Destination: S3
- S3 버킷 선택
- Prefix 설정 (폴더 구조)

**2. 버퍼 설정:**
```json
{
  "SizeInMBs": 5,      // 5MB가 모이면 전송
  "IntervalInSeconds": 300  // 또는 5분마다 전송
}
```

둘 중 하나가 먼저 도달하면 S3에 저장한다.

**3. 압축:**
```json
{
  "CompressionFormat": "GZIP"  // 또는 Snappy, Zip
}
```

데이터를 압축해서 저장한다. 스토리지 비용이 줄어든다.

**4. 포맷 변환:**
JSON을 Parquet 또는 ORC로 변환한다. Athena에서 쿼리할 때 빠르고 저렴하다.

**결과:**

데이터가 S3에 이렇게 저장된다:
```
s3://my-bucket/logs/2026/01/18/10/my-stream-1-2026-01-18-10-00-00-abc123
s3://my-bucket/logs/2026/01/18/10/my-stream-1-2026-01-18-10-05-00-def456
s3://my-bucket/logs/2026/01/18/10/my-stream-1-2026-01-18-10-10-00-ghi789
```

5분마다 파일이 생성된다. 압축되어 있다. Athena로 쉽게 쿼리할 수 있다.

### Lambda 변환

데이터를 저장하기 전에 변환한다.

**사용 사례:**

**1. 민감 정보 제거:**
```javascript
exports.handler = async (event) => {
  const records = event.records.map(record => {
    // Base64 디코딩
    const data = Buffer.from(record.data, 'base64').toString();
    const json = JSON.parse(data);
    
    // 이메일 마스킹
    if (json.email) {
      json.email = json.email.replace(/(.{3}).*(@.*)/, '$1***$2');
    }
    
    // 전화번호 제거
    delete json.phone;
    
    // 다시 인코딩
    const transformed = Buffer.from(JSON.stringify(json)).toString('base64');
    
    return {
      recordId: record.recordId,
      result: 'Ok',
      data: transformed
    };
  });
  
  return { records };
};
```

**2. 데이터 정제:**
- 불필요한 필드 제거
- 필드명 변경
- 데이터 타입 변환
- 검증 및 필터링

**3. enrichment (데이터 보강):**
- IP 주소로 지역 정보 추가
- 사용자 ID로 사용자 정보 추가
- 타임스탬프를 여러 포맷으로 추가

### 실패 처리

데이터 전달이 실패할 수 있다.

**실패 원인:**
- S3 버킷이 존재하지 않음
- 권한 부족
- Lambda 변환 실패
- 네트워크 오류

**재시도:**
Firehose가 자동으로 재시도한다. 최대 24시간 동안 재시도한다.

**실패한 데이터:**
재시도가 모두 실패하면 별도의 S3 버킷에 저장한다.

**설정:**
```json
{
  "ErrorOutputPrefix": "errors/",
  "S3BackupMode": "FailedDataOnly"
}
```

실패한 데이터는 `s3://my-bucket/errors/`에 저장된다. 나중에 수동으로 재처리할 수 있다.

## 실무 운영

### 모니터링

**CloudWatch 메트릭:**

**Kinesis Data Streams:**
- **IncomingBytes**: 초당 들어오는 데이터량
- **IncomingRecords**: 초당 들어오는 레코드 수
- **WriteProvisionedThroughputExceeded**: Shard 용량 초과
- **ReadProvisionedThroughputExceeded**: 읽기 용량 초과
- **GetRecords.IteratorAgeMilliseconds**: Consumer 지연 시간

**알람 설정:**

**처리량 초과:**
```json
{
  "MetricName": "WriteProvisionedThroughputExceeded",
  "Threshold": 0,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

Shard 용량을 초과하면 알림을 보낸다. Shard를 추가해야 한다.

**Consumer 지연:**
```json
{
  "MetricName": "GetRecords.IteratorAgeMilliseconds",
  "Threshold": 60000,  // 1분
  "ComparisonOperator": "GreaterThanThreshold"
}
```

Consumer가 1분 이상 뒤처지면 알림을 보낸다. Consumer를 확장하거나 최적화해야 한다.

### 비용 최적화

**Shard 개수 조정:**
필요한 만큼만 Shard를 사용한다.

**주간 패턴:**
- 평일 낮: Shard 10개
- 평일 밤: Shard 3개
- 주말: Shard 2개

Application Auto Scaling으로 자동화한다.

**Firehose 버퍼 크기:**
버퍼를 크게 설정하면 파일 개수가 줄어든다. S3 PUT 요청 비용이 절감된다.
- 작은 버퍼: 1MB, 60초 → 파일 많음
- 큰 버퍼: 128MB, 900초 → 파일 적음

**압축:**
반드시 압축을 활성화한다. 스토리지 비용이 70-90% 절감된다.

**포맷 변환:**
JSON을 Parquet으로 변환한다. Athena 쿼리 비용이 80-90% 절감된다.

## 참고

- AWS Kinesis 개발자 가이드: https://docs.aws.amazon.com/kinesis/
- Kinesis Data Streams: https://docs.aws.amazon.com/streams/latest/dev/
- Kinesis Data Firehose: https://docs.aws.amazon.com/firehose/latest/dev/
- Kinesis 요금: https://aws.amazon.com/kinesis/pricing/

