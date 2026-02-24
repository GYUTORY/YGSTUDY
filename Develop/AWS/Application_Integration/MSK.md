---
title: AWS MSK (Managed Streaming for Apache Kafka)
tags: [aws, msk, kafka, streaming, messaging, event-streaming]
updated: 2026-01-18
---

# AWS MSK (Managed Streaming for Apache Kafka)

## 개요

AWS MSK는 Apache Kafka를 AWS에서 실행할 수 있는 완전 관리형 서비스다. Kafka 클러스터를 직접 운영하지 않고도 Kafka의 모든 기능을 사용할 수 있다. AWS가 서버 프로비저닝, 패치, 장애 복구를 자동으로 처리한다.

### Apache Kafka란

Kafka는 분산 이벤트 스트리밍 플랫폼이다. LinkedIn이 개발했고 현재는 Apache 오픈소스 프로젝트다.

**Kafka의 역할:**
대량의 데이터를 실시간으로 수집하고, 저장하고, 처리한다. 초당 수백만 개의 메시지를 처리할 수 있다.

**핵심 특징:**
- **높은 처리량**: 초당 수백만 메시지 처리
- **낮은 지연 시간**: 밀리초 단위 응답
- **확장성**: 수평 확장 가능
- **내구성**: 디스크에 영구 저장
- **순서 보장**: 파티션 내에서 순서 보장

### 왜 Kafka가 필요한가

전통적인 메시지 큐로는 부족한 경우가 있다.

**SQS의 한계:**

**처리량 제한:**
- Standard Queue: 무제한이지만 순서 보장 안 함
- FIFO Queue: 초당 300개로 제한됨

**예시:**
IoT 센서 데이터를 수집한다. 센서가 10,000개다. 각 센서가 초당 10개 메시지를 보낸다.
- 총 메시지: 10,000 × 10 = 100,000개/초
- FIFO Queue로는 불가능하다

**저장 기간:**
- SQS: 최대 14일
- 오래된 데이터를 다시 읽을 수 없다

**여러 Consumer:**
- SQS: 한 메시지를 한 Consumer만 읽는다
- 여러 시스템이 같은 데이터를 읽을 수 없다

**Kinesis의 한계:**

Kinesis도 강력하지만 제약이 있다.

**샤드 관리:**
- 처리량이 증가하면 샤드를 수동으로 추가해야 한다
- 샤드 수를 계산하고 관리해야 한다

**비용:**
- 샤드당 고정 비용이 발생한다
- 데이터가 적어도 샤드 비용은 나간다

**제한적인 보존:**
- 기본 24시간, 최대 365일
- 영구 보관이 필요하면 S3로 옮겨야 한다

**Kafka의 강점:**

**무제한 처리량:**
- 브로커(서버)를 추가하면 처리량이 증가한다
- 초당 수백만 메시지 처리 가능

**영구 저장:**
- 데이터를 영구적으로 저장할 수 있다
- 몇 년 전 데이터도 다시 읽을 수 있다
- 스토리지 크기만 충분하면 제한 없다

**여러 Consumer:**
- Consumer Group으로 독립적으로 읽는다
- 각 Consumer Group이 자신의 속도로 읽는다
- 서로 영향을 주지 않는다

**복잡한 처리:**
- Kafka Streams로 실시간 처리한다
- 집계, 조인, 윈도우 연산 등
- 별도 처리 시스템 불필요

### 왜 직접 운영하지 않고 MSK를 사용하나

Kafka는 강력하지만 운영이 어렵다.

**직접 운영의 어려움:**

**1. 초기 설정:**
- Zookeeper 클러스터 구성 (Kafka 3.0 이전)
- Kafka 브로커 설치
- 네트워크 구성
- 보안 설정
- 며칠이 걸린다

**2. 운영 부담:**
- 24시간 모니터링 필요
- 브로커가 죽으면 수동 복구
- 디스크 공간 관리
- 로그 정리
- 성능 튜닝

**3. 확장:**
- 브로커 추가 시 데이터 재분배 필요
- 파티션 재배치
- 다운타임 발생 가능

**4. 업그레이드:**
- Kafka 버전 업그레이드 복잡
- 하나씩 순차적으로 업그레이드
- 호환성 문제 발생 가능

**5. 장애 대응:**
- 새벽 3시에 브로커가 죽으면?
- 담당자가 일어나서 복구해야 한다
- 복구 시간 동안 서비스 영향

**MSK의 해결:**

**자동 프로비저닝:**
- 몇 번의 클릭으로 클러스터 생성
- 10-20분이면 준비 완료

**자동 복구:**
- 브로커가 죽으면 자동으로 교체
- 사람이 개입할 필요 없다
- 다운타임 최소화

**자동 패치:**
- Kafka 버전 업그레이드 자동
- 보안 패치 자동 적용
- 다운타임 없이 진행

**모니터링 통합:**
- CloudWatch와 자동 연동
- 기본 메트릭 자동 수집
- 알람 쉽게 설정

## Kafka 핵심 개념

MSK를 이해하려면 Kafka의 기본 개념을 알아야 한다.

### Topic (토픽)

Topic은 메시지의 카테고리다. 데이터를 구분하는 기준이다.

**예시:**
- `orders`: 주문 데이터
- `payments`: 결제 데이터
- `user-events`: 사용자 이벤트
- `system-logs`: 시스템 로그

**특징:**
- 하나의 클러스터에 여러 Topic을 만들 수 있다
- Topic마다 독립적으로 설정한다
- Topic 이름은 변경할 수 없다

### Partition (파티션)

Topic은 여러 Partition으로 나뉜다. 병렬 처리의 단위다.

**왜 필요한가:**

**병렬 처리:**
하나의 서버로는 모든 메시지를 처리할 수 없다. Partition으로 나누면 여러 서버가 동시에 처리한다.

**예시:**
- `orders` Topic에 Partition 10개
- 10개의 Consumer가 동시에 처리
- 처리 속도 10배 증가

**순서 보장:**
같은 Partition 내에서는 순서가 보장된다.

**동작 방식:**
1. 메시지를 보낼 때 Key를 지정한다
2. Key를 해시해서 Partition을 결정한다
3. 같은 Key는 항상 같은 Partition으로 간다

**예시:**
```javascript
// 같은 user_id는 같은 Partition으로
await producer.send({
  topic: 'user-events',
  messages: [{
    key: 'user_123',  // 이 Key로 Partition 결정
    value: JSON.stringify({
      event: 'click',
      timestamp: Date.now()
    })
  }]
});
```

user_123의 모든 이벤트는 같은 Partition으로 간다. 순서가 보장된다.

**Partition 개수 선택:**

**너무 적으면:**
- 병렬 처리가 제한된다
- 처리 속도가 느리다

**너무 많으면:**
- 관리 오버헤드 증가
- 각 Partition의 데이터가 적다
- 비효율적

**권장:**
- 처음: 토픽당 3-5개
- 처리량 증가: 10-30개
- 대규모: 50-100개

**주의:** Partition 개수는 증가만 가능하다. 감소는 불가능하다.

### Producer (생산자)

데이터를 Kafka에 보내는 애플리케이션이다.

**동작 과정:**
1. 메시지를 생성한다
2. Topic과 Key를 지정한다
3. Kafka에 전송한다
4. Kafka가 저장 확인을 보낸다

**예시 코드:**
```javascript
const { Kafka } = require('kafkajs');

const kafka = new Kafka({
  clientId: 'my-app',
  brokers: ['b-1.mycluster.kafka.us-west-2.amazonaws.com:9092']
});

const producer = kafka.producer();

await producer.connect();

// 메시지 전송
await producer.send({
  topic: 'orders',
  messages: [
    {
      key: 'order_12345',
      value: JSON.stringify({
        orderId: 'order_12345',
        amount: 150.00,
        timestamp: Date.now()
      })
    }
  ]
});

await producer.disconnect();
```

**배치 전송:**
여러 메시지를 모아서 한 번에 보낸다. 처리량이 높아진다.

```javascript
const messages = orders.map(order => ({
  key: order.id,
  value: JSON.stringify(order)
}));

await producer.send({
  topic: 'orders',
  messages  // 한 번에 여러 메시지
});
```

### Consumer (소비자)

Kafka에서 데이터를 읽는 애플리케이션이다.

**동작 과정:**
1. Topic을 구독한다
2. 주기적으로 폴링한다
3. 메시지를 읽는다
4. 처리한다
5. Offset을 커밋한다

**예시 코드:**
```javascript
const consumer = kafka.consumer({ groupId: 'order-processor' });

await consumer.connect();
await consumer.subscribe({ topic: 'orders' });

await consumer.run({
  eachMessage: async ({ topic, partition, message }) => {
    const order = JSON.parse(message.value.toString());
    
    console.log({
      partition,
      offset: message.offset,
      value: order
    });
    
    // 주문 처리
    await processOrder(order);
  }
});
```

### Consumer Group

여러 Consumer가 협력해서 메시지를 처리한다.

**동작 방식:**

**상황:**
- `orders` Topic에 Partition 6개
- Consumer Group에 Consumer 3개

**분배:**
- Consumer 1: Partition 0, 1
- Consumer 2: Partition 2, 3
- Consumer 3: Partition 4, 5

각 Consumer가 2개씩 Partition을 담당한다. 병렬 처리된다.

**Consumer 추가:**
Consumer를 3개에서 6개로 증가한다.
- 각 Consumer가 1개 Partition씩 담당
- 처리 속도 2배 증가

**Consumer 감소:**
Consumer 하나가 죽는다.
- 남은 Consumer가 Partition을 재분배 받는다
- 자동으로 처리된다

**독립적인 Group:**
여러 Consumer Group이 같은 Topic을 읽는다.

**예시:**
- Group 1 (order-processor): 주문 처리
- Group 2 (analytics): 분석
- Group 3 (backup): 백업

각 Group이 독립적으로 읽는다. 서로 영향을 주지 않는다.

### Offset

Offset은 메시지의 위치를 나타낸다. Partition 내에서 순차적인 번호다.

**동작:**
- Partition의 첫 메시지: Offset 0
- 두 번째 메시지: Offset 1
- 세 번째 메시지: Offset 2

**Consumer의 Offset 관리:**

**읽은 위치 기억:**
Consumer가 Offset 100까지 읽었다. 재시작하면 Offset 101부터 읽는다. 중복이나 누락이 없다.

**Offset 커밋:**
처리 완료 후 Offset을 저장한다.

**자동 커밋:**
```javascript
const consumer = kafka.consumer({
  groupId: 'my-group',
  autoCommit: true  // 자동으로 Offset 커밋
});
```

일정 시간마다 자동으로 커밋한다. 간단하지만 중복 처리 가능성이 있다.

**수동 커밋:**
```javascript
const consumer = kafka.consumer({
  groupId: 'my-group',
  autoCommit: false
});

await consumer.run({
  eachMessage: async ({ topic, partition, message }) => {
    await processMessage(message);
    
    // 처리 완료 후 커밋
    await consumer.commitOffsets([{
      topic,
      partition,
      offset: (parseInt(message.offset) + 1).toString()
    }]);
  }
});
```

처리 완료 후 명시적으로 커밋한다. 안전하다.

**재처리:**
Offset을 이전 위치로 되돌린다. 데이터를 다시 읽는다.

**사용 사례:**
- 처리 로직에 버그가 있었다
- Offset을 24시간 전으로 되돌린다
- 데이터를 다시 처리한다

## MSK 클러스터 구성

### Broker (브로커)

Broker는 Kafka 서버다. 실제 데이터를 저장하고 처리한다.

**역할:**
- 메시지 저장
- Producer로부터 메시지 받기
- Consumer에게 메시지 전달
- Replication 관리

**개수 선택:**

**최소 3개:**
고가용성을 위해 최소 3개를 권장한다. 하나가 죽어도 서비스가 유지된다.

**처리량에 따라:**
- 소규모: 3개
- 중규모: 6-9개
- 대규모: 12개 이상

**인스턴스 타입:**
- **kafka.m5.large**: 소규모 (2 vCPU, 8GB)
- **kafka.m5.xlarge**: 중규모 (4 vCPU, 16GB)
- **kafka.m5.2xlarge**: 대규모 (8 vCPU, 32GB)

### Replication (복제)

데이터를 여러 Broker에 복제한다. 장애 대비다.

**Replication Factor:**
데이터를 몇 개의 Broker에 저장할지 결정한다.

**Replication Factor 3:**
- 원본 1개
- 복제본 2개
- 총 3개 Broker에 저장

**장점:**
- Broker 2개가 죽어도 데이터가 남아있다
- 가용성이 높다

**단점:**
- 스토리지가 3배 필요하다
- 쓰기 성능이 조금 느리다

**권장:**
프로덕션에서는 Replication Factor 3을 사용한다.

**Leader와 Follower:**

**Leader:**
- 읽기와 쓰기를 모두 처리한다
- 각 Partition마다 하나의 Leader가 있다

**Follower:**
- Leader의 데이터를 복제한다
- Leader가 죽으면 Follower 중 하나가 Leader가 된다

**자동 장애 조치:**
1. Leader Broker가 죽는다
2. Kafka가 Follower 중 하나를 새 Leader로 선출한다
3. 몇 초 안에 복구된다
4. Consumer는 새 Leader에서 읽는다

### Storage (스토리지)

Broker마다 EBS 볼륨이 연결된다.

**크기 계산:**

**예시:**
- 메시지 크기: 1KB
- 초당 메시지: 10,000개
- 보존 기간: 7일
- Replication Factor: 3

**계산:**
- 일일 데이터: 10,000 × 1KB × 86,400초 = 약 860GB
- 7일: 860GB × 7 = 약 6TB
- Replication: 6TB × 3 = 18TB
- Broker 3개: 18TB ÷ 3 = 6TB/Broker

각 Broker에 6TB 스토리지가 필요하다.

**여유분:**
실제로는 20-30% 여유를 둔다. 7-8TB로 설정한다.

**스토리지 타입:**
- **gp3 (범용 SSD)**: 대부분의 경우 사용
- **io1 (프로비저닝 IOPS)**: 매우 높은 성능 필요 시

### 네트워크 구성

**VPC 배치:**
MSK 클러스터는 VPC 안에 생성된다.

**Multi-AZ:**
여러 가용 영역에 Broker를 분산 배치한다.

**예시:**
- Broker 3개
- us-west-2a: Broker 1
- us-west-2b: Broker 2
- us-west-2c: Broker 3

한 가용 영역에 장애가 나도 서비스가 유지된다.

**보안 그룹:**
- Broker 간 통신: 9092, 9094, 2181 포트
- Client 접근: 9092 포트 (Plain), 9094 포트 (TLS)

## 실무 사용

### Producer 최적화

**배치와 압축:**
```javascript
const producer = kafka.producer({
  // 배치 설정
  batch: {
    size: 16384,      // 16KB 배치
  },
  // 압축
  compression: CompressionTypes.GZIP,
  // 재시도
  retry: {
    retries: 5
  }
});
```

**배치:**
메시지를 모아서 보낸다. 네트워크 왕복 횟수가 줄어든다. 처리량이 증가한다.

**압축:**
데이터를 압축해서 보낸다. 네트워크 대역폭이 절약된다. GZIP, Snappy, LZ4 지원.

**Acks 설정:**
```javascript
await producer.send({
  topic: 'orders',
  messages: [...],
  acks: 1  // Leader만 확인
});
```

**acks 옵션:**
- **0**: 확인 안 받음. 가장 빠름. 데이터 손실 가능
- **1**: Leader만 확인. 빠름. Leader 죽으면 손실 가능
- **-1 (all)**: 모든 Replica 확인. 느림. 데이터 손실 없음

프로덕션에서는 `-1`을 사용한다.

### Consumer 최적화

**병렬 처리:**
Consumer 개수를 Partition 개수에 맞춘다.

**예시:**
- Partition 10개
- Consumer 10개
- 각 Consumer가 1개 Partition 처리

Consumer를 10개 이상 늘려도 의미 없다. Partition보다 많을 수 없다.

**배치 읽기:**
```javascript
await consumer.run({
  eachBatch: async ({ batch }) => {
    // 여러 메시지를 한 번에 처리
    await Promise.all(
      batch.messages.map(message => processMessage(message))
    );
  }
});
```

여러 메시지를 한 번에 읽어서 처리한다. 처리량이 증가한다.

### 모니터링

**CloudWatch 메트릭:**

**Producer 메트릭:**
- **BytesInPerSec**: 초당 들어오는 데이터량
- **MessagesInPerSec**: 초당 메시지 수

**Consumer 메트릭:**
- **BytesOutPerSec**: 초당 나가는 데이터량
- **ConsumerLag**: Consumer 지연

**Broker 메트릭:**
- **CPUUtilization**: CPU 사용률
- **DiskUsed**: 디스크 사용량

**알람 설정:**

**Consumer Lag:**
```json
{
  "MetricName": "SumOffsetLag",
  "Threshold": 10000,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

Consumer가 10,000 메시지 이상 뒤처지면 알림을 받는다. Consumer를 확장해야 한다.

**디스크 사용량:**
```json
{
  "MetricName": "KafkaDataLogsDiskUsed",
  "Threshold": 80,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

디스크 사용률이 80%를 넘으면 알림을 받는다. 스토리지를 확장하거나 보존 기간을 줄여야 한다.

## MSK vs Kinesis vs SQS

언제 무엇을 사용할까?

### MSK를 선택하는 경우

**높은 처리량:**
- 초당 수백만 메시지
- Kinesis보다 더 높은 처리량

**영구 저장:**
- 데이터를 영구적으로 보관
- 몇 년 전 데이터도 재처리

**복잡한 처리:**
- Kafka Streams 사용
- 실시간 집계, 조인

**Kafka 생태계:**
- 이미 Kafka를 사용 중
- Kafka Connect, Kafka Streams

**비용:**
- 대량 데이터에서 비용 효율적
- 장기 보관 시 저렴

### Kinesis를 선택하는 경우

**간단한 사용:**
- Kafka 지식 불필요
- AWS 통합 쉬움

**서버리스:**
- 서버 관리 불필요
- Auto Scaling 자동

**적은 데이터:**
- 소규모 스트리밍
- 설정이 간단

### SQS를 선택하는 경우

**간단한 큐:**
- 메시지 전달만 필요
- 순서 불필요

**서버리스:**
- 완전 관리형
- 설정 최소

**적은 메시지:**
- 초당 수천 개 이하
- 간헐적 처리

## 참고

- AWS MSK 개발자 가이드: https://docs.aws.amazon.com/msk/
- Apache Kafka 문서: https://kafka.apache.org/documentation/
- MSK 요금: https://aws.amazon.com/msk/pricing/
- Kafka 모범 사례: https://docs.aws.amazon.com/msk/latest/developerguide/bestpractices.html

