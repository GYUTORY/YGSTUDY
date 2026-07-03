---
title: AWS MSK (Managed Streaming for Apache Kafka)
tags: [aws, msk, kafka, streaming, messaging, event-streaming, iam, encryption, msk-connect, msk-serverless, schema-registry]
updated: 2026-05-26
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
- Client 접근: 9092(평문), 9094(TLS), 9096(SASL/SCRAM), 9098(IAM)

인증 방식마다 포트가 다르다. 클라이언트가 9098로 붙는데 IAM 인증을 안 켰거나, 9094로 붙는데 mTLS 설정이 빠지면 연결이 안 된다. 포트와 인증 방식은 뒤의 인증·암호화 절에서 정리한다.

## 인증과 접근제어

MSK는 클라이언트 인증을 세 가지 지원한다. IAM, SASL/SCRAM, mTLS다. 인증 없이(평문 또는 TLS만) 붙는 모드도 있지만 프로덕션에서는 쓰지 않는다. 인증 방식은 클러스터 생성 시 켜고, 여러 개를 동시에 켤 수도 있다. 같은 클러스터에서 한 서비스는 IAM, 다른 서비스는 SCRAM으로 붙는 구성이 가능하다.

세 방식은 붙는 포트가 다르다. 인증을 켰는데 클라이언트가 엉뚱한 포트의 부트스트랩 주소를 쓰면 핸드셰이크 단계에서 막힌다. MSK 콘솔의 "클라이언트 정보 보기"에서 인증 방식별 부트스트랩 주소를 따로 제공한다.

### IAM 인증

AWS IAM 자격증명으로 Kafka에 붙는다. MSK 전용 SASL 메커니즘(`AWS_MSK_IAM`)을 쓰고, 클라이언트는 포트 9098로 붙는다. EC2 인스턴스 프로파일, EKS의 IRSA, Lambda 실행 역할에 정책을 붙이면 별도 비밀번호 없이 인증된다.

권한을 IAM 정책으로 통제한다. 토픽 단위, Consumer Group 단위로 읽기/쓰기를 나눌 수 있다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:us-west-2:111122223333:cluster/orders-cluster/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:DescribeTopic",
        "kafka-cluster:WriteData"
      ],
      "Resource": "arn:aws:kafka:us-west-2:111122223333:topic/orders-cluster/*/orders"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:DescribeGroup",
        "kafka-cluster:AlterGroup",
        "kafka-cluster:ReadData"
      ],
      "Resource": "arn:aws:kafka:us-west-2:111122223333:group/orders-cluster/*/order-processor"
    }
  ]
}
```

kafkajs는 IAM 메커니즘을 기본 내장하지 않는다. `aws-msk-iam-sasl-signer-js` 패키지로 인증 토큰을 만들어 OAuth Bearer 메커니즘에 넣는 방식이 표준이다.

```javascript
const { Kafka } = require('kafkajs');
const { generateAuthToken } = require('aws-msk-iam-sasl-signer-js');

async function oauthBearerProvider(region) {
  // 토큰은 약 15분 유효하다. kafkajs가 만료 전에 다시 호출한다.
  const { token } = await generateAuthToken({ region });
  return { value: token };
}

const kafka = new Kafka({
  clientId: 'order-service',
  brokers: ['b-1.orders-cluster.abc123.kafka.us-west-2.amazonaws.com:9098'],
  ssl: true,  // IAM 인증은 TLS 위에서만 동작한다
  sasl: {
    mechanism: 'oauthbearer',
    oauthBearerProvider: () => oauthBearerProvider('us-west-2')
  }
});
```

IAM 인증에서 자주 막히는 부분이 있다. 정책에 `kafka-cluster:Connect`가 빠지면 연결 자체가 안 된다. Consumer는 `group/...` 리소스에 `AlterGroup`이 없으면 Consumer Group에 합류하지 못한다. 권한 문제는 클라이언트 쪽에 `TopicAuthorizationException` 류로 떨어지는데, 어떤 액션이 모자란지 메시지에 안 나오는 경우가 많아 정책을 토픽/그룹 단위로 정확히 매핑해 두는 편이 디버깅이 빠르다.

### SASL/SCRAM

사용자명과 비밀번호로 붙는다. 포트는 9096이다. 비밀번호는 클러스터에 직접 저장하지 않고 Secrets Manager 시크릿과 연동한다.

여기서 처음 쓰는 사람이 거의 다 막히는 제약이 있다. SCRAM에 연결하는 시크릿은 (1) 이름이 `AmazonMSK_`로 시작해야 하고, (2) 기본 키(`aws/secretsmanager`)가 아니라 직접 만든 고객 관리 KMS 키로 암호화돼 있어야 한다. 기본 키로 암호화된 시크릿은 MSK에 연결되지 않는다. 조건을 안 맞추면 콘솔에서 시크릿이 목록에 아예 안 뜬다.

시크릿 형식:

```json
{
  "username": "order-service",
  "password": "..."
}
```

시크릿을 만들고 클러스터에 연결한 뒤, Kafka ACL을 따로 걸어야 실제 권한이 생긴다. SCRAM은 IAM과 달리 인증과 인가가 분리돼 있다. 인증은 비밀번호로 하지만 토픽 접근 권한은 `kafka-acls` 명령으로 부여한다.

```javascript
const kafka = new Kafka({
  clientId: 'order-service',
  brokers: ['b-1.orders-cluster.abc123.kafka.us-west-2.amazonaws.com:9096'],
  ssl: true,
  sasl: {
    mechanism: 'scram-sha-512',  // MSK는 SHA-512를 쓴다
    username: process.env.MSK_USERNAME,
    password: process.env.MSK_PASSWORD
  }
});
```

### mTLS 클라이언트 인증

양방향 TLS다. 서버 인증서뿐 아니라 클라이언트도 인증서를 제출한다. 포트는 9094다. 클라이언트 인증서는 ACM Private CA에서 발급한 것이어야 하고, 그 CA를 클러스터에 등록해 둔다.

```javascript
const fs = require('fs');
const { Kafka } = require('kafkajs');

const kafka = new Kafka({
  clientId: 'order-service',
  brokers: ['b-1.orders-cluster.abc123.kafka.us-west-2.amazonaws.com:9094'],
  ssl: {
    ca: [fs.readFileSync('/etc/msk/ca.pem', 'utf-8')],
    cert: fs.readFileSync('/etc/msk/client-cert.pem', 'utf-8'),
    key: fs.readFileSync('/etc/msk/client-key.pem', 'utf-8')
  }
});
```

mTLS는 인증서 갱신이 운영 부담이다. 인증서에 만료일이 있어서 갱신을 놓치면 모든 클라이언트가 한꺼번에 연결을 잃는다. 갱신 자동화를 안 해두면 만료일에 장애가 난다. SCRAM처럼 권한은 Kafka ACL로 따로 건다. 인증서의 DN(Distinguished Name)이 ACL의 Principal이 된다.

### 무엇을 언제 쓰나

세 방식의 차이를 정리하면 이렇다.

| 항목 | IAM | SASL/SCRAM | mTLS |
|------|-----|------------|------|
| 포트 | 9098 | 9096 | 9094 |
| 자격증명 | IAM 역할/사용자 | 사용자명·비밀번호 | 클라이언트 인증서 |
| 비밀번호 관리 | 불필요 | Secrets Manager | 인증서 갱신 |
| 권한 통제 | IAM 정책 | Kafka ACL | Kafka ACL |
| 갱신 | AWS가 자동 | 수동 회전 | 인증서 재발급 |

AWS 안에서 도는 애플리케이션(EC2, EKS, Lambda)이라면 IAM을 기본으로 쓴다. 비밀번호 회전이나 인증서 갱신을 신경 쓸 필요가 없고, 토픽 단위 권한을 IAM 정책으로 한곳에서 관리한다. MSK Serverless는 IAM만 지원해서 선택지도 없다.

온프레미스 서버나 AWS 밖의 클라이언트, 또는 IAM을 못 쓰는 서드파티 도구가 붙어야 하면 SASL/SCRAM을 쓴다. Kafka 표준 사용자명/비밀번호 방식이라 호환성이 넓다. 대신 시크릿 회전을 직접 관리해야 한다.

규제나 보안 요건으로 인증서 기반이 강제되거나 이미 사내 PKI가 있으면 mTLS를 쓴다. ACM Private CA 비용과 인증서 갱신 자동화를 감수해야 한다.

## 전송 중 암호화와 저장 시 암호화

### 전송 중 암호화 (in-transit)

클라이언트와 브로커 사이, 그리고 브로커 간 통신을 TLS로 암호화한다. 클러스터 생성 시 세 가지 중 고른다.

- **TLS만 허용**: 평문 연결을 막는다. 프로덕션 기본값으로 쓴다.
- **TLS와 평문 동시 허용**: 9092(평문)와 9094(TLS)를 둘 다 연다. 마이그레이션 중 잠깐 쓴다.
- **평문만**: 암호화 없음. VPC 내부 신뢰 구간이라도 권장하지 않는다.

브로커 간 통신 암호화도 따로 켤 수 있는데, 켜면 복제 트래픽이 암호화되면서 CPU를 더 쓴다. 처리량이 큰 클러스터에서는 이 부분이 CPU 사용률에 잡힌다.

### 저장 시 암호화 (at-rest)

브로커에 붙은 EBS 볼륨을 KMS로 암호화한다. 클러스터 생성 시 KMS 키를 고른다.

- **AWS 관리 키**: 별도 지정 안 하면 MSK 서비스 키로 암호화된다.
- **고객 관리 키 (CMK)**: 직접 만든 KMS 키를 지정한다. 키 정책, 회전, 접근 감사(CloudTrail)를 직접 통제하려면 CMK를 쓴다.

중요한 제약이 있다. 저장 시 암호화 키는 클러스터 생성 시점에만 지정할 수 있고, 만든 뒤에는 못 바꾼다. 규제상 CMK가 필요하다면 처음부터 CMK로 만들어야 한다. 나중에 바꾸려면 새 클러스터를 만들어 데이터를 옮기는 수밖에 없다.

CMK를 쓸 때는 KMS 키 정책에 MSK 서비스(`kafka.amazonaws.com`)가 키를 쓸 수 있도록 권한을 넣어야 한다. 빠지면 클러스터 생성이 실패한다.

### 포트 정리

| 포트 | 용도 |
|------|------|
| 9092 | 평문(PLAINTEXT). 암호화·인증 없음 |
| 9094 | TLS 암호화. mTLS 클라이언트 인증도 이 포트 |
| 9096 | SASL/SCRAM(TLS 위) |
| 9098 | IAM 인증(TLS 위) |

부트스트랩 주소는 인증 방식마다 포트가 박혀서 따로 제공된다. SCRAM 클라이언트가 9098 주소를 쓰거나, IAM 클라이언트가 9094 주소를 쓰면 핸드셰이크에서 막힌다. 연결 안 될 때 가장 먼저 포트와 인증 방식이 맞는지 확인하는 편이 빠르다.

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

## MSK Serverless

지금까지 설명한 방식은 브로커 수, 인스턴스 타입, EBS 크기를 직접 정하는 프로비저닝 모드다. MSK Serverless는 이걸 다 없앤다. 브로커 개념이 클라이언트에게 보이지 않고, 토픽과 파티션만 만든다. 처리량은 트래픽에 맞춰 자동으로 늘고 준다.

### 프로비저닝 모드와의 차이

프로비저닝 모드는 용량을 미리 정한다. 브로커 3대에 인스턴스 타입과 스토리지를 정해놓으면 그 한도 안에서 돈다. 트래픽이 그 한도를 넘으면 브로커를 추가하거나 스토리지를 늘려야 한다. 트래픽이 적으면 그만큼 놀고 있는 용량에 돈을 낸다.

Serverless는 용량 산정 자체가 없다. 파티션당 처리량 한도 안에서 쓴 만큼 과금된다. 스토리지도 무제한으로 자동 관리되고 따로 크기를 잡지 않는다.

### 언제 쓰나

트래픽 패턴이 들쭉날쭉하거나 예측이 어려울 때 맞다. 평소엔 한가하다가 특정 시간에만 몰리는 워크로드, 클러스터 사이징을 고민하기 싫은 개발·테스트 환경, 트래픽이 얼마나 들어올지 모르는 신규 서비스 초기에 쓴다.

반대로 트래픽이 일정하고 크면 프로비저닝 모드가 더 싸다. Serverless는 단위 처리량당 단가가 높아서 대규모 상시 트래픽에서는 비용이 빠르게 올라간다.

### 제약

쓰기 전에 알아야 할 제약이 여러 개다.

- **IAM 인증 전용**: SASL/SCRAM, mTLS를 못 쓴다. 클라이언트가 IAM으로만 붙는다. 온프레미스나 비-AWS 클라이언트가 SCRAM으로 붙어야 한다면 Serverless는 못 쓴다.
- **처리량 한도**: 파티션당 쓰기·읽기 처리량에 상한이 있고, 클러스터 전체 처리량에도 상한이 있다. 핫 파티션 하나에 트래픽이 몰리면 파티션 한도에 먼저 걸린다. 키 분포를 고르게 가져가야 한다.
- **파티션 수 상한**: 클러스터당 만들 수 있는 파티션 수에 한도가 있다. 토픽을 잘게 쪼개 파티션을 과하게 만들면 한도에 걸린다.
- **일부 설정 불가**: 브로커 수준 설정을 못 만진다. 프로비저닝 모드에서 튜닝하던 브로커 파라미터를 Serverless에서는 건드릴 수 없다.

처리량·파티션 한도는 서비스 쿼터라 값이 바뀐다. 사이징 전에 콘솔의 서비스 쿼터나 MSK 문서에서 현재 값을 확인해야 한다.

## MSK Connect

Kafka Connect를 관리형으로 돌린다. Kafka Connect는 외부 시스템과 Kafka 사이를 잇는 커넥터 실행 프레임워크다. 직접 운영하면 워커 클러스터를 따로 띄우고 관리해야 하는데, MSK Connect는 워커를 AWS가 굴린다.

### 커넥터 배포

커넥터 플러그인(JAR을 묶은 zip)을 S3에 올리고, MSK Connect에서 커스텀 플러그인으로 등록한다. 그 다음 커넥터를 만들면서 워커 수와 워커당 용량(MCU), 커넥터 설정(JSON)을 지정한다.

워커는 MSK 클러스터와 같은 VPC에 배치된다. IAM 인증 클러스터에 붙는 커넥터라면 커넥터의 서비스 실행 역할에 앞에서 본 `kafka-cluster:*` 권한을 줘야 한다.

### S3 Sink 예시

토픽 데이터를 S3에 적재하는 커넥터다. 로그나 이벤트를 장기 보관하거나 데이터 레이크로 보낼 때 쓴다.

```json
{
  "connector.class": "io.confluent.connect.s3.S3SinkConnector",
  "tasks.max": "2",
  "topics": "orders",
  "s3.region": "us-west-2",
  "s3.bucket.name": "orders-archive",
  "flush.size": "1000",
  "rotate.interval.ms": "60000",
  "storage.class": "io.confluent.connect.s3.storage.S3Storage",
  "format.class": "io.confluent.connect.s3.format.json.JsonFormat",
  "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
  "path.format": "'year'=YYYY/'month'=MM/'day'=dd/'hour'=HH",
  "partition.duration.ms": "3600000",
  "locale": "en-US",
  "timezone": "UTC"
}
```

`flush.size`와 `rotate.interval.ms`가 S3 객체가 만들어지는 단위를 정한다. flush.size를 너무 작게 잡으면 작은 파일이 무수히 쌓여서 나중에 읽을 때 느리고, S3 PUT 요청 비용도 올라간다. 트래픽에 맞춰 객체 하나가 수십~수백 MB가 되도록 잡는 편이 낫다.

### Debezium CDC 예시

Debezium은 DB의 변경 로그(MySQL binlog, PostgreSQL WAL)를 읽어서 Kafka 토픽으로 흘려보내는 CDC 커넥터다. 테이블의 INSERT/UPDATE/DELETE가 이벤트로 들어온다.

```json
{
  "connector.class": "io.debezium.connector.mysql.MySqlConnector",
  "tasks.max": "1",
  "database.hostname": "orders-db.abc123.us-west-2.rds.amazonaws.com",
  "database.port": "3306",
  "database.user": "debezium",
  "database.password": "${secretsManager:msk/debezium-db:password}",
  "database.server.id": "184054",
  "topic.prefix": "cdc.orders",
  "database.include.list": "orders",
  "table.include.list": "orders.order_items,orders.payments",
  "schema.history.internal.kafka.bootstrap.servers": "b-1.orders-cluster.abc123.kafka.us-west-2.amazonaws.com:9098",
  "schema.history.internal.kafka.topic": "schema-history.orders"
}
```

Debezium에는 주의할 게 몇 가지 있다.

- **DB 권한**: MySQL이면 binlog 읽기 권한(`REPLICATION SLAVE`, `REPLICATION CLIENT`)이, PostgreSQL이면 논리 복제 슬롯 권한이 필요하다. RDS면 binlog/logical replication을 파라미터 그룹에서 켜야 한다.
- **초기 스냅샷 부하**: 커넥터가 처음 뜨면 대상 테이블 전체를 한 번 스냅샷한다. 큰 테이블이면 이 단계에서 DB에 부하가 걸린다. 트래픽 적은 시간에 첫 기동을 하는 편이 안전하다.
- **오프셋 보관**: 커넥터가 어디까지 읽었는지를 내부 토픽(`connect-offsets`)에 저장한다. 이게 날아가면 스냅샷부터 다시 한다. PostgreSQL은 복제 슬롯이 커넥터 다운 동안 WAL을 잡아두는데, 커넥터가 오래 죽어 있으면 WAL이 쌓여 DB 디스크가 찬다.
- **태스크 1개 제약**: 단일 DB 소스 커넥터는 보통 태스크가 1개다. `tasks.max`를 올려도 병렬화가 안 되는 경우가 많다. 처리량이 부족하면 토픽 파티션을 늘려 다운스트림 Consumer를 병렬화한다.

## Glue Schema Registry 연동

메시지 스키마를 코드 밖에서 관리한다. Producer가 Avro 스키마를 레지스트리에 등록하고, 메시지에는 스키마 전체가 아니라 스키마 버전 ID만 실어 보낸다. Consumer는 ID로 스키마를 받아 역직렬화한다. 페이로드에서 필드 이름이 반복되지 않으니 메시지 크기가 줄고, 스키마가 한곳에서 관리된다.

### 호환성 관리

스키마가 바뀔 때 기존 Producer/Consumer가 깨지지 않게 하는 게 핵심이다. Glue Schema Registry는 호환성 모드를 둔다.

- **BACKWARD**: 새 스키마로 옛 데이터를 읽을 수 있어야 한다. 필드 삭제나 기본값 있는 필드 추가가 허용된다. Consumer를 먼저 새 스키마로 올리고 Producer를 나중에 올린다.
- **FORWARD**: 옛 스키마로 새 데이터를 읽을 수 있어야 한다. 필드 추가가 허용된다. Producer를 먼저 올린다.
- **FULL**: 양방향 모두 호환. 가장 안전하지만 변경 폭이 좁다.
- **NONE**: 검사 안 함. 깨지는 변경을 막지 못한다.

호환성 모드를 정해두면 깨는 스키마를 등록하려 할 때 등록 단계에서 막힌다. 배포 후 런타임에 터지는 대신 스키마 등록에서 걸러진다.

### 주의할 점

직렬화·역직렬화 라이브러리(SerDe)는 Java 쪽이 가장 잘 갖춰져 있다. `GlueSchemaRegistryKafkaSerializer`/`Deserializer`를 Producer/Consumer 설정에 끼우면 등록·검증이 자동으로 돈다.

Node(kafkajs)는 Glue Schema Registry 네이티브 지원이 약하다. AWS Glue Schema Registry용 JavaScript SerDe 라이브러리를 따로 붙이거나, 직렬화·버전 ID 처리 코드를 직접 짜야 한다. Node 클라이언트가 많은 환경에서 Avro+Glue를 도입할 때는 이 부분을 먼저 검증하는 게 좋다. Java 서비스끼리는 잘 되는데 Node 서비스가 같은 토픽을 못 읽어 막히는 경우가 있다.

## KRaft 모드와 Zookeeper

Kafka는 오래 클러스터 메타데이터(브로커 목록, 토픽, 파티션 리더, ACL)를 Zookeeper에 저장했다. Kafka 3.x에서 Zookeeper를 들어내고 Kafka 자체 합의 프로토콜(KRaft)로 메타데이터를 관리하는 모드가 나왔다.

### 버전별 차이

MSK는 구버전에서 Zookeeper 노드를 자동으로 운영해 왔다. 이 노드는 추가 과금 없이 AWS가 관리해서 사용자가 직접 볼 일이 거의 없었다. 최근 버전(3.7 이상 계열)에서는 새 클러스터를 KRaft 모드로 만들 수 있다.

KRaft 모드의 차이는 운영보다 확장성에서 드러난다. Zookeeper 기반은 파티션 수가 아주 많아지면 메타데이터 처리가 병목이 됐다. KRaft는 메타데이터를 컨트롤러가 로그로 관리해서 파티션 수가 많을 때 메타데이터 작업(리더 선출, 브로커 재시작 후 복구)이 빠르다. 파티션을 수만 개 단위로 쓰는 클러스터면 차이가 크다.

### 마이그레이션 시 주의

기존에 Zookeeper로 동작하던 클러스터를 KRaft로 옮기려면 MSK가 지원하는 버전 경로를 따라 업그레이드해야 한다. 버전을 건너뛰는 업그레이드는 안 되고, 단계별로 올린다.

코드와 운영 도구 쪽에서 깨질 수 있는 부분이 있다. 예전에 Zookeeper 엔드포인트에 직접 붙던 도구나, `kafka-topics --zookeeper ...`처럼 `--zookeeper` 플래그를 쓰던 스크립트는 KRaft에서 동작하지 않는다. `--bootstrap-server`로 바꿔야 한다. 이건 KRaft 이전부터 권장돼 온 방식이지만, 오래된 운영 스크립트에 `--zookeeper`가 남아 있으면 마이그레이션 후 깨진다. 미리 찾아서 고쳐둬야 한다.

## Tiered Storage

장기 보존 비용을 줄이는 기능이다. 브로커 로컬 EBS는 빠르지만 비싸다. 오래된 데이터까지 전부 EBS에 두면 스토리지 비용이 계속 올라간다. Tiered Storage는 데이터를 두 계층으로 나눈다. 최근 데이터는 로컬에, 오래된 데이터는 저비용 원격 계층에 둔다.

### 동작

토픽별로 켠다. `local.retention.ms`(또는 바이트 기준)만큼만 로컬에 두고, 그 기간을 넘긴 세그먼트는 자동으로 원격 계층으로 옮긴다. 전체 보존 기간(`retention.ms`)은 길게 잡아도 로컬 디스크는 최근 데이터분만 차지한다. 보존을 한 달, 1년으로 늘려도 EBS 사용량이 그만큼 늘지 않는다.

Consumer가 최근 데이터를 읽으면 로컬에서 바로 나온다. 오래된 오프셋을 읽으면 원격 계층에서 가져온다.

### 제약

- **버전 제약**: 특정 Kafka 버전 이상에서만 된다. 구버전 클러스터는 버전을 올려야 한다.
- **compacted 토픽 미지원**: 로그 컴팩션을 쓰는 토픽에는 적용되지 않는다. 시간 기반 보존(delete) 토픽에만 켠다.
- **원격 읽기 지연**: 원격 계층 읽기는 로컬보다 느리다. 실시간 Consumer는 대부분 로컬에서 읽으니 영향이 작지만, 오래된 데이터를 처음부터 다시 읽는 백필 작업은 느려진다. 과거 데이터 대량 재처리를 자주 한다면 이 지연을 감안해야 한다.
- **local.retention 하한**: 로컬 보존을 너무 짧게 잡으면 원격 이동이 잦아지고, 약간만 뒤처진 Consumer도 원격에서 읽게 돼 지연이 늘 수 있다. 정상 Consumer가 따라잡는 범위는 로컬에 남도록 잡는다.

## VPC 외부 접속과 멀티 VPC

MSK 클러스터는 VPC 안에 생성되고 기본적으로 그 VPC(또는 VPC 피어링·Transit Gateway로 연결된 네트워크) 안에서만 붙을 수 있다. 다른 VPC, 다른 계정, 또는 인터넷에서 붙어야 하면 별도 설정이 필요하다.

### 멀티 VPC 프라이빗 연결

다른 VPC나 다른 AWS 계정의 클라이언트가 PrivateLink 기반으로 클러스터에 붙게 한다. 설정은 두 쪽에서 한다.

- 클러스터 쪽: 멀티 VPC 연결을 켜고, 클러스터 정책(리소스 기반 정책)으로 어떤 계정·주체가 붙을 수 있는지 허용한다.
- 클라이언트 쪽: 관리형 VPC 연결을 만들면 그 VPC 전용 부트스트랩 엔드포인트가 생긴다. 클라이언트는 이 엔드포인트로 붙는다.

VPC 피어링과 달리 IP 대역이 겹쳐도 되고, 클러스터 VPC를 클라이언트에게 노출하지 않는다. 다만 멀티 VPC 연결은 인증을 켠 클러스터에서만 된다. 인증 없는(unauthenticated) 클러스터는 멀티 VPC로 못 연다. IAM, SASL/SCRAM, mTLS 중 하나를 쓴다.

### 온프레미스와 퍼블릭 접속

온프레미스에서 붙어야 하면 Direct Connect나 VPN으로 VPC와 연결하고, VPC 내부 경로로 브로커에 닿게 한다.

인터넷에서 붙어야 하는 드문 경우엔 퍼블릭 액세스를 켤 수 있다. 조건이 까다롭다. 평문(9092)은 못 열고 TLS만 허용해야 하며, 인증을 반드시 켜야 한다. 보안 노출이 크니 꼭 필요한 경우가 아니면 멀티 VPC 프라이빗 연결을 쓰는 편이 낫다.

## 실무 트러블슈팅

운영하면서 실제로 자주 부딪히는 상황들이다.

### Consumer Lag 급증

Consumer가 Producer 속도를 못 따라가면 Lag(처리 안 된 메시지 수)이 쌓인다. CloudWatch의 `MaxOffsetLag`, `SumOffsetLag`나 `kafka-consumer-groups --describe`로 확인한다.

원인은 보통 이 중 하나다.

- Consumer 처리 로직이 느리다. 메시지마다 외부 API를 동기 호출하거나 무거운 DB 쿼리를 돌리면 처리 속도가 안 나온다.
- 파티션 수가 부족하다. Consumer를 늘려도 파티션보다 많아질 수 없어서 병렬도가 막힌다.
- 리밸런스가 잦다. Consumer가 자꾸 그룹에서 빠졌다 들어오면 그때마다 처리가 멈춘다.

대응은 원인에 따라 다르다. 처리가 느리면 메시지 처리를 비동기·배치로 바꾸고, 한 번에 가져오는 양(`max.poll.records` 등)을 조정한다. 파티션이 부족하면 파티션을 늘리고 Consumer를 거기에 맞춘다. 단 파티션은 늘리기만 되고 줄이지 못하니 신중하게 늘린다. 리밸런스가 잦으면 `session.timeout.ms`/`heartbeat.interval.ms`를 점검하고, 처리 시간이 길어 `max.poll.interval.ms`를 넘겨 쫓겨나는 건 아닌지 본다. 협력적 리밸런싱(cooperative sticky assignor)을 쓰면 리밸런스 때 전체가 멈추지 않고 영향 범위가 준다.

### 디스크 풀 (KafkaDataLogsDiskUsed)

브로커 디스크가 100%에 차면 그 브로커는 쓰기를 못 받고 사실상 다운된다. 한 브로커가 죽으면 부하가 남은 브로커로 몰려 연쇄로 차오를 수 있다. 디스크는 80%를 넘기 전에 손을 쓰는 게 안전하다.

원인은 보존 기간이 길거나, 트래픽이 갑자기 늘었거나, under-replicated 상태라 로그가 안 지워지는 경우다. 파티션이 동기화가 안 끝나면 Kafka가 해당 로그 세그먼트를 삭제하지 못해 디스크가 계속 찬다.

대응:

- **스토리지 자동 확장**: MSK는 디스크 사용률이 기준을 넘으면 EBS를 자동으로 늘리는 기능이 있다. 프로비저닝 클러스터라면 켜둔다. 이게 꺼져 있으면 새벽에 디스크가 차도 아무도 안 늘려준다.
- **보존 기간 축소**: 급하면 토픽 `retention.ms`를 줄여 오래된 데이터를 빨리 지운다.
- **Tiered Storage**: 장기 보존이 목적이면 로컬 디스크 압박을 근본적으로 줄인다.
- **브로커 추가**: 용량 자체가 모자라면 스케일아웃한다. 단 아래 문제를 같이 봐야 한다.

### 파티션 재배치 시 성능 저하

파티션을 다른 브로커로 옮기는 재배치(reassignment)는 대량 복제 트래픽을 만든다. 옮기는 동안 원본 데이터가 통째로 새 브로커로 복사되면서 네트워크와 디스크 I/O가 포화되고, 같은 브로커에서 서비스 중인 다른 파티션의 읽기/쓰기 지연이 같이 올라간다.

재배치는 트래픽 적은 시간에 한다. 복제 속도에 상한(throttle)을 걸어 서비스 트래픽이 받는 영향을 줄인다. 한 번에 전부 옮기지 않고 파티션을 나눠 점진적으로 옮긴다. throttle 없이 대량 재배치를 돌리면 재배치 자체는 빠르지만 그동안 서비스 지연이 튀어서 장애처럼 보인다.

### 브로커 스케일아웃 후 데이터 재분배 누락

이게 모르면 가장 당하기 쉬운 함정이다. MSK에서 브로커를 추가하면 새 브로커는 비어 있는 상태로 들어온다. 기존 토픽의 파티션이 자동으로 새 브로커로 옮겨가지 않는다. 새로 만드는 토픽이나 추가하는 파티션만 새 브로커에 분배된다.

그래서 부하 분산을 기대하고 브로커를 늘렸는데, 기존 브로커는 여전히 과부하고 새 브로커는 놀고 있는 상황이 그대로 유지된다. 디스크가 차서 브로커를 늘렸는데 디스크 사용률이 안 떨어지는 것도 같은 이유다.

해결하려면 기존 파티션을 새 브로커로 직접 재배치해야 한다. MSK는 브로커 추가 후 파티션을 자동으로 고르게 재분배하는 기능을 제공한다. 이걸 돌리거나, `kafka-reassign-partitions`로 재배치 계획을 만들어 적용한다. 재배치는 앞에서 말한 대로 복제 트래픽을 만드니 throttle을 걸고 트래픽 적은 시간에 한다. 브로커를 늘렸으면 재배치까지가 한 작업이라고 봐야 한다. 늘리기만 하고 끝내면 효과가 없다.

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
- MSK 운영 권장 사항: https://docs.aws.amazon.com/msk/latest/developerguide/bestpractices.html

