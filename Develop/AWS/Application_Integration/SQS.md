---
title: AWS SQS (Simple Queue Service)
tags: [aws, sqs, messaging, queue, asynchronous, serverless, microservices]
updated: 2025-12-17
---

# AWS SQS (Simple Queue Service)

## 개요

AWS SQS는 클라우드 기반의 완전관리형 메시지 큐 서비스다. 분산 시스템에서 비동기 메시지 처리를 위한 인프라다.

**특징:**
- 완전관리형: AWS가 인프라 관리, 확장, 모니터링 담당
- 높은 가용성: 99.9% 이상 가용성, 여러 가용 영역에 메시지 저장
- 무제한 확장성: 처리량 제한 없음, 트래픽 급증 시 자동 확장
- 비용 효율성: 사용한 만큼만 비용 지불

**사용하는 경우:**
- 비동기 작업 처리
- 마이크로서비스 간 통신
- 이벤트 기반 아키텍처
- 워크로드 버퍼링

## 큐 유형

### Standard Queue

높은 처리량과 최소한의 지연 시간을 제공하는 기본 큐 유형이다.

**특징:**
- 높은 처리량: 초당 거의 무제한의 메시지 처리 가능
- 최소 1회 전달: 메시지가 최소 한 번은 전달되지만, 중복 전달 가능성 존재
- 순서 보장 없음: 메시지가 전송된 순서와 다르게 처리될 수 있음
- 최대 처리량: 초당 거의 무제한의 트랜잭션 지원

**사용 사례:**
- 웹 애플리케이션의 백그라운드 작업 처리
- 이미지/비디오 처리 파이프라인
- 이메일 발송 시스템
- 로그 수집 및 분석

**실무 팁:**
대부분의 경우 Standard Queue로 충분하다. 순서가 중요하지 않다면 Standard Queue를 사용한다.

### FIFO Queue

메시지 순서와 중복 제거를 보장하는 큐 유형이다.

**특징:**
- 순서 보장: 메시지가 전송된 순서대로 처리됨
- 정확히 1회 전달: 메시지 중복 없이 정확히 한 번만 전달
- 제한된 처리량: 초당 최대 300개의 메시지 처리
- 메시지 그룹화: MessageGroupId를 통한 병렬 처리 지원

**사용 사례:**
- 금융 거래 처리
- 주문 처리 시스템
- 데이터베이스 복제
- 중요한 비즈니스 워크플로우

**실무 팁:**
FIFO Queue는 처리량이 제한적이다. 정말 순서가 중요한 경우에만 사용한다.

## 메시지 생명주기

### 메시지 전송 과정

1. Producer가 메시지 전송: 애플리케이션이 SQS 큐에 메시지를 전송
2. SQS가 메시지 저장: 메시지가 큐에 안전하게 저장됨
3. Consumer가 폴링: Consumer가 주기적으로 큐를 확인하여 메시지 수신
4. 메시지 처리: Consumer가 메시지를 처리
5. 명시적 삭제: 처리 완료 후 Consumer가 메시지를 명시적으로 삭제

**예시 (Node.js):**
```javascript
const AWS = require('aws-sdk');
const sqs = new AWS.SQS();

// 메시지 전송
await sqs.sendMessage({
  QueueUrl: process.env.QUEUE_URL,
  MessageBody: JSON.stringify({ orderId: '123', amount: 100 })
}).promise();

// 메시지 수신
const result = await sqs.receiveMessage({
  QueueUrl: process.env.QUEUE_URL,
  MaxNumberOfMessages: 10,
  WaitTimeSeconds: 20
}).promise();

// 메시지 처리 및 삭제
for (const message of result.Messages || []) {
  const body = JSON.parse(message.Body);
  await processMessage(body);
  
  await sqs.deleteMessage({
    QueueUrl: process.env.QUEUE_URL,
    ReceiptHandle: message.ReceiptHandle
  }).promise();
}
```

### 가시성 타임아웃 (Visibility Timeout)

메시지가 Consumer에 의해 수신되면, 다른 Consumer가 동일한 메시지를 수신하지 못하도록 일정 시간 동안 "보이지 않게" 된다.

**설정 원칙:**
- 메시지 처리 시간보다 충분히 길게 설정
- 너무 짧으면 중복 처리 발생 가능
- 너무 길면 처리 실패 시 재처리 지연

**예시:**
```javascript
// 가시성 타임아웃 설정 (30초)
await sqs.receiveMessage({
  QueueUrl: process.env.QUEUE_URL,
  VisibilityTimeout: 30
}).promise();
```

**실무 팁:**
가시성 타임아웃은 메시지 처리 시간의 3배 정도로 설정한다. 처리 중 메시지가 다시 보이면 중복 처리가 발생할 수 있다.

### Dead Letter Queue (DLQ)

처리에 실패한 메시지를 격리하는 특별한 큐다.

**DLQ 활용 전략:**
- 최대 수신 횟수 설정으로 무한 재시도 방지
- 실패한 메시지 분석을 통한 시스템 개선
- 수동 재처리 또는 별도 처리 파이프라인 구축

**예시:**
```javascript
// DLQ 설정
await sqs.setQueueAttributes({
  QueueUrl: process.env.QUEUE_URL,
  Attributes: {
    'RedrivePolicy': JSON.stringify({
      'deadLetterTargetArn': process.env.DLQ_ARN,
      'maxReceiveCount': 3
    })
  }
}).promise();
```

**실무 팁:**
DLQ는 반드시 설정한다. 실패한 메시지가 계속 재시도되면 비용이 증가하고 시스템에 부하가 생긴다.

## 메시지 속성

### 메시지 본문 (Message Body)
- 최대 256KB의 텍스트 데이터
- JSON, XML, 바이너리 데이터 등 다양한 형식 지원
- Base64 인코딩을 통한 바이너리 데이터 전송 가능

### 메시지 속성 (Message Attributes)
- 메시지와 함께 전송되는 메타데이터
- 문자열, 숫자, 바이너리 데이터 타입 지원
- 최대 10개의 속성, 각각 최대 256KB

**예시:**
```javascript
await sqs.sendMessage({
  QueueUrl: process.env.QUEUE_URL,
  MessageBody: JSON.stringify({ orderId: '123' }),
  MessageAttributes: {
    'Priority': {
      DataType: 'String',
      StringValue: 'High'
    }
  }
}).promise();
```

### 시스템 속성
- MessageId: 메시지의 고유 식별자
- ReceiptHandle: 메시지 삭제를 위한 핸들
- MD5OfBody: 메시지 본문의 무결성 검증
- Attributes: 메시지의 시스템 메타데이터

**실무 팁:**
메시지 본문은 256KB로 제한된다. 더 큰 데이터는 S3에 저장하고 S3 키만 메시지로 전송한다.

## 성능 최적화

### 장기 폴링 (Long Polling)

폴링 간격을 늘려 비용을 절감한다.

**예시:**
```javascript
// Short Polling (기본값, 비효율적)
await sqs.receiveMessage({
  QueueUrl: process.env.QUEUE_URL
}).promise();

// Long Polling (권장)
await sqs.receiveMessage({
  QueueUrl: process.env.QUEUE_URL,
  WaitTimeSeconds: 20 // 1-20초 권장
}).promise();
```

**장점:**
- 비용 절감: 빈 응답 감소로 API 호출 횟수 감소
- 응답성 향상: 메시지가 있으면 즉시 반환
- 빈 응답 감소

**실무 팁:**
WaitTimeSeconds를 20초로 설정하면 비용을 크게 절감할 수 있다.

### 배치 작업

최대 10개의 메시지를 한 번에 전송/수신한다.

**예시:**
```javascript
// 배치 전송 (최대 10개)
await sqs.sendMessageBatch({
  QueueUrl: process.env.QUEUE_URL,
  Entries: [
    { Id: '1', MessageBody: JSON.stringify({ id: 1 }) },
    { Id: '2', MessageBody: JSON.stringify({ id: 2 }) }
  ]
}).promise();

// 배치 수신 (최대 10개)
const result = await sqs.receiveMessage({
  QueueUrl: process.env.QUEUE_URL,
  MaxNumberOfMessages: 10
}).promise();
```

**장점:**
- API 호출 횟수 감소로 비용 절감
- 처리량 향상

**실무 팁:**
배치 작업을 사용하면 비용을 크게 절감할 수 있다. 가능하면 배치로 처리한다.

## 보안

### IAM 정책

최소 권한 원칙에 따른 세밀한 권한 제어다.

**예시:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage"
      ],
      "Resource": "arn:aws:sqs:region:account:queue-name"
    }
  ]
}
```

**실무 팁:**
큐별, 작업별로 권한을 분리한다. 모든 큐에 대한 권한을 주지 않는다.

### 서버 측 암호화 (SSE)

전송 중 및 저장 중 데이터 암호화다.

**예시:**
```javascript
await sqs.setQueueAttributes({
  QueueUrl: process.env.QUEUE_URL,
  Attributes: {
    'KmsMasterKeyId': 'alias/aws/sqs'
  }
}).promise();
```

**실무 팁:**
민감한 데이터는 반드시 암호화한다. KMS를 사용하면 키 관리가 편리하다.

### VPC 엔드포인트

프라이빗 네트워크를 통한 안전한 접근이다.

**실무 팁:**
Private Subnet의 리소스에서 SQS에 접근할 때는 VPC 엔드포인트를 사용한다. 인터넷 트래픽 없이 접근할 수 있다.

## 모니터링

### CloudWatch 메트릭

**주요 메트릭:**
- ApproximateNumberOfMessages: 큐에 대기 중인 메시지 수
- ApproximateAgeOfOldestMessage: 가장 오래된 메시지의 대기 시간
- NumberOfMessagesSent/Received: 메시지 전송/수신 통계
- NumberOfEmptyReceives: 빈 응답 횟수

**알람 설정 예시:**
```javascript
await cloudwatch.putMetricAlarm({
  AlarmName: 'HighQueueDepth',
  MetricName: 'ApproximateNumberOfMessages',
  Namespace: 'AWS/SQS',
  Statistic: 'Average',
  Period: 300,
  Threshold: 1000,
  ComparisonOperator: 'GreaterThanThreshold',
  Dimensions: [{ Name: 'QueueName', Value: 'my-queue' }]
}).promise();
```

**실무 팁:**
큐 깊이가 계속 증가하면 Consumer를 확장하거나 처리 로직을 최적화해야 한다.

### CloudTrail 로깅

모든 SQS API 호출이 기록된다.

**활용:**
- 보안 감사 및 컴플라이언스 지원
- 문제 해결을 위한 상세 로그

**실무 팁:**
CloudTrail을 활성화하면 모든 API 호출을 추적할 수 있다. 보안 감사에 필수다.

## 비용 최적화

### 요금 구조

**요청 기반 과금:**
- API 호출 횟수에 따라 과금
- 데이터 전송 비용
- DLQ 사용 시 추가 비용

**비용 예시 (us-east-1 기준):**
- 첫 1백만 건: 무료
- 이후: $0.40/1백만 건
- 데이터 전송: $0.09/GB (아웃바운드)

### 비용 절감 방법

**1. 장기 폴링:**
- WaitTimeSeconds를 20초로 설정
- 빈 응답 감소로 API 호출 횟수 감소

**2. 배치 작업:**
- 최대 10개 메시지를 한 번에 처리
- API 호출 횟수 90% 감소 가능

**3. 불필요한 큐 정리:**
- 사용하지 않는 큐 삭제
- 메시지 보존 기간 최적화

**4. 메시지 보존 기간:**
- 기본값: 4일
- 최대: 14일
- 필요 이상으로 길게 설정하지 않는다

**실무 팁:**
장기 폴링과 배치 작업을 함께 사용하면 비용을 크게 절감할 수 있다.

## 운영 고려사항

### 애플리케이션 설계

**멱등성 보장:**
동일한 메시지의 중복 처리에 대비한다.

**예시:**
```javascript
const processedIds = new Set();

async function processMessage(message) {
  const body = JSON.parse(message.Body);
  const id = body.orderId;
  
  // 멱등성 보장: 이미 처리된 메시지인지 확인
  if (processedIds.has(id)) {
    return; // 중복 처리 방지
  }
  
  await processOrder(body);
  processedIds.add(id);
}
```

**오류 처리:**
재시도 로직과 회로 차단기 패턴을 적용한다.

**백프레셔:**
큐 깊이에 따른 처리 속도를 조절한다.

**실무 팁:**
Standard Queue는 중복 전달이 가능하다. 멱등성 보장이 필수다.

### 큐 관리

**정기적인 모니터링:**
- 큐 상태 모니터링
- DLQ 메시지 정기 검토
- 큐 설정 최적화

**실무 팁:**
DLQ에 메시지가 쌓이면 원인을 분석해야 한다. 처리 로직에 문제가 있을 수 있다.

### 확장성 고려사항

**Consumer 수평 확장:**
- Auto Scaling으로 Consumer 수 조절
- 큐 깊이에 따라 자동 확장

**큐별 처리량 분산:**
- 여러 큐로 부하 분산
- 리전별 큐 분산 고려

**실무 팁:**
큐 깊이가 계속 증가하면 Consumer를 확장한다. Auto Scaling을 설정하면 자동으로 처리된다.

## 사용 시나리오

### 전자상거래 주문 처리 시스템

온라인 쇼핑몰에서 주문이 들어올 때마다 재고 확인, 결제 처리, 배송 준비 등의 작업을 비동기로 처리한다.

**아키텍처:**
```
주문 API → SQS (주문 큐) → 재고 서비스
                              ↓
                         결제 서비스 → SQS (배송 큐) → 배송 서비스
```

**예시:**
```javascript
// 주문 API
app.post('/orders', async (req, res) => {
  await sqs.sendMessage({
    QueueUrl: process.env.ORDER_QUEUE_URL,
    MessageBody: JSON.stringify(req.body)
  }).promise();
  
  res.json({ orderId: req.body.id, status: 'processing' });
});

// 재고 서비스
async function processOrder() {
  const result = await sqs.receiveMessage({
    QueueUrl: process.env.ORDER_QUEUE_URL,
    MaxNumberOfMessages: 10,
    WaitTimeSeconds: 20
  }).promise();
  
  for (const message of result.Messages || []) {
    const order = JSON.parse(message.Body);
    
    if (await checkInventory(order)) {
      await sqs.sendMessage({
        QueueUrl: process.env.PAYMENT_QUEUE_URL,
        MessageBody: JSON.stringify(order)
      }).promise();
    }
    
    await sqs.deleteMessage({
      QueueUrl: process.env.ORDER_QUEUE_URL,
      ReceiptHandle: message.ReceiptHandle
    }).promise();
  }
}
```

**장점:**
- 주문 API의 응답 시간 단축
- 각 서비스의 독립적 확장 가능
- 일부 서비스 장애 시에도 주문 수신 가능

### 이미지 처리 파이프라인

사용자가 업로드한 이미지를 다양한 크기로 리사이징하고 썸네일을 생성한다.

**처리 과정:**
1. 이미지 업로드 시 원본 이미지 정보를 SQS에 전송
2. 이미지 처리 워커가 큐에서 작업을 수신
3. 다양한 크기로 이미지 리사이징 수행
4. 처리 완료 후 결과를 다른 큐에 전송하여 알림 발송

**예시:**
```javascript
// 이미지 업로드 후
await sqs.sendMessage({
  QueueUrl: process.env.IMAGE_PROCESSING_QUEUE_URL,
  MessageBody: JSON.stringify({
    s3Key: 'uploads/original/image.jpg',
    sizes: ['thumbnail', 'medium', 'large']
  })
}).promise();

// 이미지 처리 워커
async function processImage() {
  const result = await sqs.receiveMessage({
    QueueUrl: process.env.IMAGE_PROCESSING_QUEUE_URL,
    MaxNumberOfMessages: 10
  }).promise();
  
  for (const message of result.Messages || []) {
    const task = JSON.parse(message.Body);
    await resizeImage(task.s3Key, task.sizes);
    
    await sqs.deleteMessage({
      QueueUrl: process.env.IMAGE_PROCESSING_QUEUE_URL,
      ReceiptHandle: message.ReceiptHandle
    }).promise();
  }
}
```

### 로그 수집 및 분석 시스템

여러 애플리케이션에서 발생하는 로그를 중앙에서 수집하고 실시간 분석한다.

**구성 요소:**
- 로그 수집기: 각 애플리케이션의 로그를 SQS에 전송
- 로그 처리기: 큐에서 로그를 수신하여 파싱 및 정제
- 분석 엔진: 처리된 로그를 분석하여 메트릭 생성
- 알림 시스템: 이상 상황 감지 시 알림 발송

**실무 팁:**
로그 수집 시 배치로 전송하면 비용을 절감할 수 있다.

## 고급 패턴

### Fan-out 패턴

하나의 메시지를 여러 큐에 동시에 전송하는 패턴이다. SNS와 SQS를 조합하여 구현한다.

**사용 사례:**
- 주문 정보를 재고, 결제, 배송 큐에 동시 전송
- 사용자 활동 로그를 분석, 알림, 백업 큐에 전송

**구현:**
```
SNS Topic → SQS Queue 1 (재고)
         → SQS Queue 2 (결제)
         → SQS Queue 3 (배송)
```

**실무 팁:**
SNS를 사용하면 여러 큐에 동시에 메시지를 전송할 수 있다. 각 큐는 독립적으로 처리된다.

### Priority Queue 패턴

중요도에 따라 메시지 처리 순서를 조절하는 패턴이다.

**구현 방법:**
- 여러 큐를 우선순위별로 구성
- Consumer가 높은 우선순위 큐부터 처리
- 메시지 속성에 우선순위 정보 포함

**예시:**
```javascript
// 우선순위별 큐 처리
async function processWithPriority() {
  // 높은 우선순위 큐부터 처리
  const high = await sqs.receiveMessage({
    QueueUrl: process.env.HIGH_PRIORITY_QUEUE_URL
  }).promise();
  
  if (high.Messages) {
    await processMessages(high.Messages);
    return;
  }
  
  // 낮은 우선순위 큐 처리
  const low = await sqs.receiveMessage({
    QueueUrl: process.env.LOW_PRIORITY_QUEUE_URL
  }).promise();
  
  if (low.Messages) {
    await processMessages(low.Messages);
  }
}
```

### Circuit Breaker 패턴

연속적인 실패 시 일시적으로 메시지 처리를 중단하는 패턴이다.

**구현 요소:**
- 실패 횟수 추적
- 임계값 도달 시 회로 차단
- 복구 시도 및 회로 복구

**예시:**
```javascript
let failureCount = 0;
const FAILURE_THRESHOLD = 5;
let circuitOpen = false;

async function processMessage(message) {
  if (circuitOpen) {
    return; // 회로 차단 상태
  }
  
  try {
    await processOrder(message);
    failureCount = 0;
  } catch (error) {
    failureCount++;
    
    if (failureCount >= FAILURE_THRESHOLD) {
      circuitOpen = true;
      // 60초 후 복구 시도
      setTimeout(() => {
        circuitOpen = false;
        failureCount = 0;
      }, 60000);
    }
  }
}
```

**실무 팁:**
Circuit Breaker 패턴을 사용하면 연속적인 실패로 인한 리소스 낭비를 방지할 수 있다.

## 문제 해결

### 일반적인 문제들

**큐 깊이 증가:**
- 원인: Consumer 처리 속도 < Producer 전송 속도
- 해결: Consumer 수평 확장, 처리 로직 최적화

**메시지 중복 처리:**
- 원인: 가시성 타임아웃 설정 부적절
- 해결: 처리 시간에 맞는 타임아웃 설정, 멱등성 보장

**높은 비용:**
- 원인: 과도한 API 호출, 비효율적인 폴링
- 해결: 장기 폴링 적용, 배치 작업 활용

**실무 팁:**
큐 깊이가 계속 증가하면 Consumer를 확장한다. Auto Scaling을 설정하면 자동으로 처리된다.

### 모니터링 지표

**성능 지표:**
- 큐 깊이 (ApproximateNumberOfMessages)
- 메시지 처리 지연 시간
- Consumer 처리량

**비용 지표:**
- API 호출 횟수
- 데이터 전송량
- DLQ 사용량

**안정성 지표:**
- 메시지 처리 실패율
- DLQ 메시지 수
- 가시성 타임아웃 초과 횟수

**실무 팁:**
CloudWatch 대시보드를 만들어 주요 지표를 모니터링한다. 알람을 설정하면 문제를 빠르게 감지할 수 있다.

## 마이그레이션 전략

### 기존 시스템에서 SQS 도입

**단계별 접근:**
1. 새로운 기능에 SQS 적용
2. 기존 시스템의 일부 기능을 SQS로 이전
3. 점진적으로 전체 시스템 마이그레이션

**고려사항:**
- 기존 메시지 큐와의 호환성
- 데이터 마이그레이션 계획
- 다운타임 최소화 방안

**실무 팁:**
기존 시스템과 병행 운영하면서 점진적으로 마이그레이션한다. 한 번에 전환하면 위험이 크다.

### 하이브리드 아키텍처

**온프레미스와 클라우드 연동:**
- VPN 또는 Direct Connect를 통한 연결
- 하이브리드 메시지 브로커 활용
- 데이터 동기화 전략 수립

**실무 팁:**
온프레미스에서 SQS에 접근할 때는 VPC 엔드포인트를 사용한다. 인터넷 트래픽 없이 접근할 수 있다.

## 참고

- AWS SQS 개발자 가이드: https://docs.aws.amazon.com/ko_kr/AWSSimpleQueueService/latest/SQSDeveloperGuide/
- AWS SQS 모범 사례: https://docs.aws.amazon.com/ko_kr/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-best-practices.html
- AWS 요금 계산기: https://calculator.aws/
