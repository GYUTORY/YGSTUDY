---
title: AWS EventBridge
tags: [aws, eventbridge, event-driven, serverless, integration, event-bus]
updated: 2026-01-18
---

# AWS EventBridge

## 개요

AWS EventBridge는 이벤트 기반 아키텍처를 구축하는 서버리스 이벤트 버스 서비스다. 애플리케이션, AWS 서비스, SaaS 애플리케이션에서 발생하는 이벤트를 수집하고, 필터링하고, 라우팅한다. 코드를 작성하지 않고도 여러 서비스를 연결할 수 있다.

### 왜 EventBridge가 필요할까

과거에는 서비스 간 통신이 복잡했다.

**전통적인 방식의 문제:**

**직접 연결의 악몽:**
e커머스 사이트를 만든다고 하자. 주문이 들어오면 여러 일을 해야 한다:
1. 재고를 감소시킨다
2. 결제를 처리한다
3. 배송을 준비한다
4. 고객에게 이메일을 보낸다
5. 알림을 보낸다
6. 분석 데이터를 수집한다

**전통적인 구현:**
```javascript
async function createOrder(orderData) {
  // 주문 저장
  const order = await db.saveOrder(orderData);
  
  // 모든 서비스를 직접 호출
  await inventoryService.decreaseStock(order.items);
  await paymentService.processPayment(order.payment);
  await shippingService.createShipment(order);
  await emailService.sendConfirmation(order.customerEmail);
  await notificationService.sendPush(order.customerId);
  await analyticsService.trackOrder(order);
  
  return order;
}
```

**문제점:**

**1. 강한 결합 (Tight Coupling):**
- 주문 서비스가 모든 서비스를 알아야 한다
- 한 서비스가 변경되면 주문 서비스도 변경해야 한다
- 새 서비스를 추가하려면 주문 서비스를 수정해야 한다

**2. 에러 처리 복잡:**
- 이메일 서비스가 다운되면 어떻게 할까?
- 주문은 저장되었는데 알림이 실패했다면?
- 재시도 로직을 직접 구현해야 한다

**3. 확장 어려움:**
- 새로운 기능을 추가할 때마다 코드를 수정한다
- 마케팅 팀이 "주문 데이터를 CRM에 보내주세요"라고 요청한다
- 개발자가 코드를 수정하고 배포해야 한다

**4. 성능 문제:**
- 모든 작업이 동기적으로 실행된다
- 하나라도 느리면 전체가 느려진다
- 사용자는 주문 완료까지 기다려야 한다

**SNS/SQS의 개선:**
SNS와 SQS를 사용하면 어느 정도 해결된다.

```javascript
async function createOrder(orderData) {
  const order = await db.saveOrder(orderData);
  
  // SNS 토픽에 이벤트 발행
  await sns.publish({
    TopicArn: 'arn:aws:sns:us-west-2:123456789012:order-created',
    Message: JSON.stringify(order)
  });
  
  return order;
}
```

각 서비스가 SNS 토픽을 구독한다. 비동기로 처리된다. 하지만 여전히 제약이 있다.

**SNS/SQS의 한계:**

**1. 필터링 제한:**
SNS 필터링은 메시지 속성만 가능하다. 메시지 본문은 필터링할 수 없다.

```json
{
  "orderType": ["premium"]  // 이것만 가능
}
```

복잡한 조건은 불가능하다:
- 주문 금액이 $100 이상
- 특정 카테고리의 상품
- 특정 지역의 고객

**2. 라우팅 복잡:**
여러 조건에 따라 다른 서비스로 보내려면 토픽을 여러 개 만들어야 한다.
- order-created-premium
- order-created-standard
- order-created-international

관리가 어렵다.

**3. 변환 불가:**
메시지 형식을 변환할 수 없다. Consumer가 원하는 형식으로 데이터를 보낼 수 없다.

**4. 스케줄링 없음:**
"매일 오전 9시에 실행"같은 스케줄링이 불가능하다. CloudWatch Events를 별도로 사용해야 한다.

**EventBridge의 해결:**

EventBridge는 이 모든 문제를 해결한다.

**1. 강력한 필터링:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"],
  "detail": {
    "amount": [{ "numeric": [">=", 100] }],
    "category": ["electronics"],
    "region": ["us-west-2", "us-east-1"]
  }
}
```

복잡한 조건도 간단히 표현한다.

**2. 유연한 라우팅:**
하나의 이벤트를 여러 대상으로 보낸다. 각각 다른 필터를 사용한다.

**3. 입력 변환:**
메시지 형식을 Consumer에 맞게 변환한다.

**4. 통합 스케줄러:**
Cron 표현식으로 스케줄링한다.

**5. 많은 통합:**
AWS 서비스, SaaS 애플리케이션과 쉽게 연결한다.

### 이벤트 기반 아키텍처

EventBridge는 이벤트 기반 아키텍처의 핵심이다.

**이벤트란:**
"무언가 일어났다"는 사실을 나타낸다.
- 주문이 생성되었다
- 사용자가 로그인했다
- 파일이 업로드되었다
- 결제가 완료되었다

**이벤트 기반 아키텍처의 장점:**

**1. 느슨한 결합:**
- Producer는 Consumer를 모른다
- 새 Consumer를 추가해도 Producer는 변경 없다
- 서비스가 독립적으로 발전한다

**2. 확장성:**
- Consumer를 추가하거나 제거하기 쉽다
- 트래픽에 따라 독립적으로 스케일한다

**3. 유연성:**
- 비즈니스 요구사항이 변경되어도 쉽게 대응한다
- 새 기능을 빠르게 추가한다

## 핵심 개념

EventBridge의 구조를 이해하면 사용하기 쉬워진다.

### Event Bus (이벤트 버스)

Event Bus는 이벤트가 흐르는 채널이다. 모든 이벤트는 Event Bus를 통과한다.

**종류:**

**1. Default Event Bus:**
AWS가 자동으로 생성한다. AWS 서비스의 이벤트가 여기로 온다.

**예시:**
- EC2 인스턴스가 시작되었다
- S3 버킷에 파일이 업로드되었다
- Lambda 함수가 실패했다

코드를 작성하지 않아도 이벤트가 자동으로 발행된다.

**2. Custom Event Bus:**
직접 만드는 Event Bus다. 애플리케이션 이벤트를 보낸다.

**예시:**
- order-events: 주문 관련 이벤트
- user-events: 사용자 관련 이벤트
- payment-events: 결제 관련 이벤트

**분리의 장점:**
- 권한 관리가 쉽다. 각 팀이 자신의 Event Bus를 관리한다
- 이벤트가 명확히 구분된다
- 모니터링이 쉽다

**3. Partner Event Bus:**
SaaS 애플리케이션의 이벤트를 받는다.

**예시:**
- Shopify: 주문, 고객 이벤트
- Datadog: 알림 이벤트
- Auth0: 인증 이벤트

파트너 애플리케이션과 쉽게 통합한다.

### Event (이벤트)

이벤트는 JSON 형식의 데이터다.

**구조:**
```json
{
  "version": "0",
  "id": "53dc4d37-cffa-4f76-80c9-8b7d4a4d2eaa",
  "detail-type": "Order Created",
  "source": "order.service",
  "account": "123456789012",
  "time": "2026-01-18T10:30:00Z",
  "region": "us-west-2",
  "resources": [],
  "detail": {
    "orderId": "order-12345",
    "customerId": "customer-67890",
    "amount": 150.00,
    "items": [
      {
        "productId": "prod-111",
        "quantity": 2,
        "price": 50.00
      },
      {
        "productId": "prod-222",
        "quantity": 1,
        "price": 50.00
      }
    ],
    "shippingAddress": {
      "city": "Seattle",
      "state": "WA",
      "country": "US"
    }
  }
}
```

**주요 필드:**

**source:**
이벤트를 발생시킨 서비스다.
- AWS 서비스: `aws.ec2`, `aws.s3`
- 커스텀 애플리케이션: `order.service`, `user.service`

**detail-type:**
이벤트의 종류다.
- `"Order Created"`, `"Order Cancelled"`
- `"User Registered"`, `"User Deleted"`

**detail:**
이벤트의 실제 데이터다. 자유로운 JSON 구조다.

### Rule (규칙)

Rule은 이벤트를 필터링하고 라우팅한다.

**구성:**
1. Event Pattern (이벤트 패턴): 어떤 이벤트를 처리할지
2. Target (대상): 이벤트를 어디로 보낼지

**예시:**

**상황:** 고액 주문 ($100 이상)이 생성되면 관리자에게 알림을 보낸다.

**Rule 설정:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"],
  "detail": {
    "amount": [{ "numeric": [">=", 100] }]
  }
}
```

**Target:** SNS 토픽

**동작:**
1. 주문이 생성된다. $150이다
2. 이벤트가 Event Bus로 발행된다
3. Rule이 이벤트를 확인한다. 조건을 만족한다
4. SNS 토픽으로 이벤트를 전송한다
5. 관리자가 알림을 받는다

### Target (대상)

이벤트를 받을 서비스다.

**지원하는 Target:**

**Lambda:**
가장 많이 사용한다. 커스텀 로직을 실행한다.

```javascript
exports.handler = async (event) => {
  console.log('이벤트:', JSON.stringify(event, null, 2));
  
  const order = event.detail;
  await processOrder(order);
};
```

**Step Functions:**
복잡한 워크플로우를 실행한다.

**SQS:**
비동기 처리를 위해 큐에 넣는다.

**SNS:**
여러 구독자에게 알린다.

**Kinesis:**
스트리밍 처리를 위해 전송한다.

**API Gateway:**
외부 HTTP 엔드포인트를 호출한다.

**기타:**
- ECS Task: 컨테이너 실행
- EC2: API 호출
- CloudWatch Logs: 로그 저장
- CodePipeline: 배포 트리거

**여러 Target:**
하나의 Rule에 최대 5개의 Target을 설정할 수 있다.

**예시:**
주문 생성 이벤트를:
1. Lambda로 보내서 처리한다
2. SQS로 보내서 비동기 작업한다
3. Kinesis로 보내서 분석한다
4. CloudWatch Logs로 보내서 저장한다

모두 동시에 실행된다.

## 이벤트 패턴 (Event Pattern)

이벤트를 필터링하는 방법이다. 매우 강력하다.

### 기본 필터링

**정확히 일치:**
```json
{
  "source": ["order.service"]
}
```

source가 정확히 "order.service"인 이벤트만 처리한다.

**여러 값:**
```json
{
  "source": ["order.service", "user.service"]
}
```

source가 "order.service" 또는 "user.service"인 이벤트를 처리한다. OR 조건이다.

**여러 필드:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created", "Order Updated"]
}
```

source가 "order.service" AND (detail-type이 "Order Created" OR "Order Updated")인 이벤트를 처리한다.

### 숫자 비교

```json
{
  "source": ["order.service"],
  "detail": {
    "amount": [{ "numeric": [">=", 100] }]
  }
}
```

주문 금액이 $100 이상인 이벤트를 처리한다.

**지원하는 연산자:**
- `">="`: 크거나 같다
- `">"`: 크다
- `"<="`: 작거나 같다
- `"<"`: 작다
- `"="`: 같다

**범위:**
```json
{
  "detail": {
    "temperature": [{ "numeric": [">", 20, "<=", 30] }]
  }
}
```

온도가 20도 초과 30도 이하인 이벤트를 처리한다.

### 문자열 패턴

**Prefix (접두사):**
```json
{
  "detail": {
    "eventType": [{ "prefix": "order." }]
  }
}
```

eventType이 "order."로 시작하는 이벤트를 처리한다.
- "order.created" ✓
- "order.updated" ✓
- "user.created" ✗

**Suffix (접미사):**
```json
{
  "detail": {
    "fileName": [{ "suffix": ".jpg" }]
  }
}
```

파일명이 ".jpg"로 끝나는 이벤트를 처리한다.

### 존재 확인

**필드 존재:**
```json
{
  "detail": {
    "couponCode": [{ "exists": true }]
  }
}
```

couponCode 필드가 있는 이벤트를 처리한다.

**필드 부재:**
```json
{
  "detail": {
    "discountRate": [{ "exists": false }]
  }
}
```

discountRate 필드가 없는 이벤트를 처리한다.

### 중첩 필드

```json
{
  "detail": {
    "shippingAddress": {
      "country": ["US", "CA"]
    }
  }
}
```

배송 국가가 미국 또는 캐나다인 이벤트를 처리한다.

### 배열 필터링

```json
{
  "detail": {
    "items": {
      "category": ["electronics"]
    }
  }
}
```

items 배열 중 하나라도 category가 "electronics"인 이벤트를 처리한다.

### 복잡한 조건

**실제 예시: VIP 고객의 고액 주문**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"],
  "detail": {
    "amount": [{ "numeric": [">=", 500] }],
    "customer": {
      "tier": ["vip", "premium"]
    },
    "shippingAddress": {
      "country": ["US"]
    }
  }
}
```

조건:
- 주문 금액 $500 이상
- 고객 등급이 VIP 또는 Premium
- 배송 국가가 미국

이런 복잡한 조건도 코드 없이 표현한다.

## 입력 변환 (Input Transformation)

Target에 보내는 데이터를 변환한다.

### 왜 필요한가

**상황:**
Lambda 함수는 간단한 형식을 원한다:
```json
{
  "orderId": "order-12345",
  "amount": 150.00
}
```

하지만 이벤트는 복잡하다:
```json
{
  "version": "0",
  "id": "53dc4d37-cffa-4f76-80c9-8b7d4a4d2eaa",
  "detail-type": "Order Created",
  "source": "order.service",
  "detail": {
    "orderId": "order-12345",
    "customerId": "customer-67890",
    "amount": 150.00,
    "items": [...]
  }
}
```

Lambda에서 필요한 부분만 추출해야 한다. 매번 코드로 하면 번거롭다.

### 입력 경로 (Input Path)

```json
{
  "InputPath": "$.detail"
}
```

detail 부분만 Lambda로 전송한다.

**결과:**
```json
{
  "orderId": "order-12345",
  "customerId": "customer-67890",
  "amount": 150.00,
  "items": [...]
}
```

### 입력 템플릿 (Input Template)

더 세밀한 제어가 가능하다.

**설정:**
```json
{
  "InputPathsMap": {
    "order": "$.detail.orderId",
    "amount": "$.detail.amount",
    "customer": "$.detail.customerId"
  },
  "InputTemplate": "{\"orderId\": <order>, \"totalAmount\": <amount>, \"userId\": <customer>}"
}
```

**결과:**
```json
{
  "orderId": "order-12345",
  "totalAmount": 150.00,
  "userId": "customer-67890"
}
```

필드명도 변경하고, 필요한 필드만 선택한다.

### 고정 값 추가

```json
{
  "InputPathsMap": {
    "order": "$.detail.orderId",
    "amount": "$.detail.amount"
  },
  "InputTemplate": "{\"orderId\": <order>, \"amount\": <amount>, \"region\": \"us-west-2\", \"processed\": true}"
}
```

**결과:**
```json
{
  "orderId": "order-12345",
  "amount": 150.00,
  "region": "us-west-2",
  "processed": true
}
```

고정 값을 추가한다. Lambda가 어느 리전에서 처리되는지 알 수 있다.

## 스케줄링

Cron 표현식이나 Rate 표현식으로 정기적으로 작업을 실행한다.

### Rate 표현식

**매 X 시간/일/분:**
```
rate(5 minutes)  // 5분마다
rate(1 hour)     // 1시간마다
rate(1 day)      // 1일마다
```

**사용 사례:**
- 5분마다 Health Check 실행
- 1시간마다 데이터 동기화
- 매일 백업 수행

### Cron 표현식

더 정교한 스케줄링이 가능하다.

**형식:**
```
cron(분 시 일 월 요일 연도)
```

**예시:**

**평일 오전 9시:**
```
cron(0 9 ? * MON-FRI *)
```

**매월 1일 자정:**
```
cron(0 0 1 * ? *)
```

**매 15분마다:**
```
cron(0/15 * * * ? *)
```

**특정 날짜와 시간:**
```
cron(0 10 15 * ? *)  // 매월 15일 오전 10시
```

**실제 사용:**

**일일 리포트 생성:**
```json
{
  "ScheduleExpression": "cron(0 6 * * ? *)",
  "Target": {
    "Arn": "arn:aws:lambda:us-west-2:123456789012:function:generate-daily-report"
  }
}
```

매일 오전 6시에 Lambda 함수를 실행해 리포트를 생성한다.

## 실무 사용 사례

### 주문 처리 시스템

**요구사항:**
주문이 생성되면:
1. 재고를 확인하고 감소시킨다
2. 결제를 처리한다
3. 배송을 준비한다
4. 고객에게 이메일을 보낸다
5. VIP 고객이면 특별 처리한다
6. 고액 주문이면 관리자에게 알린다
7. 분석 데이터를 수집한다

**구현:**

**1. 주문 서비스:**
```javascript
async function createOrder(orderData) {
  // 주문 저장
  const order = await db.saveOrder(orderData);
  
  // 이벤트 발행
  await eventBridge.putEvents({
    Entries: [{
      Source: 'order.service',
      DetailType: 'Order Created',
      Detail: JSON.stringify(order),
      EventBusName: 'custom-event-bus'
    }]
  }).promise();
  
  return order;
}
```

주문 서비스는 이벤트만 발행한다. 다른 서비스를 모른다.

**2. EventBridge Rule 설정:**

**모든 주문:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"]
}
```
Target: Lambda (재고 처리), Lambda (결제 처리), Lambda (배송 준비), SQS (이메일 발송)

**VIP 고객:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"],
  "detail": {
    "customer": {
      "tier": ["vip"]
    }
  }
}
```
Target: Lambda (VIP 특별 처리)

**고액 주문:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"],
  "detail": {
    "amount": [{ "numeric": [">=", 500] }]
  }
}
```
Target: SNS (관리자 알림)

**분석:**
```json
{
  "source": ["order.service"],
  "detail-type": ["Order Created"]
}
```
Target: Kinesis Data Firehose (S3 저장)

**장점:**
- 주문 서비스는 간단하다. 이벤트만 발행한다
- 새 기능을 추가해도 주문 서비스는 변경 없다
- 각 처리가 독립적이다. 하나가 실패해도 다른 것은 영향 없다
- 조건을 쉽게 변경한다. 코드 수정 없이 콘솔에서 변경한다

### 인프라 자동화

**요구사항:**
EC2 인스턴스가 중지되면 알림을 받고, 자동으로 재시작한다.

**구현:**

**Rule:**
```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["stopped"]
  }
}
```

**Target 1: SNS**
관리자에게 알림을 보낸다.

**Target 2: Lambda**
인스턴스를 자동으로 재시작한다.

```javascript
exports.handler = async (event) => {
  const instanceId = event.detail.instance-id;
  
  await ec2.startInstances({
    InstanceIds: [instanceId]
  }).promise();
  
  console.log(`인스턴스 ${instanceId} 재시작`);
};
```

**자동화 완성:**
인스턴스가 중지되면:
1. EventBridge가 이벤트를 감지한다
2. SNS로 알림을 보낸다
3. Lambda가 인스턴스를 재시작한다

사람이 개입할 필요가 없다.

## 실무 운영

### 에러 처리

**재시도:**
EventBridge가 자동으로 재시도한다.
- 최대 24시간 동안 재시도
- 지수 백오프 사용 (1초, 2초, 4초, 8초...)

**Dead-Letter Queue:**
재시도가 모두 실패하면 DLQ로 보낸다.

**설정:**
```json
{
  "Target": {
    "Arn": "arn:aws:lambda:...",
    "DeadLetterConfig": {
      "Arn": "arn:aws:sqs:us-west-2:123456789012:event-dlq"
    }
  }
}
```

실패한 이벤트는 SQS 큐에 저장된다. 나중에 수동으로 재처리할 수 있다.

### 모니터링

**CloudWatch 메트릭:**
- **Invocations**: Rule이 실행된 횟수
- **FailedInvocations**: 실패한 횟수
- **TriggeredRules**: 트리거된 Rule 수

**알람 설정:**
```json
{
  "MetricName": "FailedInvocations",
  "Threshold": 10,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

실패가 10번 이상 발생하면 알림을 받는다.

### 비용 최적화

**비용 구조:**
- 이벤트 발행: 100만 건당 $1
- Rule 매칭: 무료
- 크로스 리전 이벤트: 추가 비용

**최적화 방법:**

**1. 이벤트 배치:**
여러 이벤트를 한 번에 발행한다.

```javascript
await eventBridge.putEvents({
  Entries: events.map(event => ({
    Source: 'order.service',
    DetailType: 'Order Created',
    Detail: JSON.stringify(event)
  }))
}).promise();
```

최대 10개까지 한 번에 보낼 수 있다.

**2. 필터링 최적화:**
가능한 빨리 필터링한다. 불필요한 Target 호출을 줄인다.

**3. 리전 최적화:**
같은 리전에서 사용한다. 크로스 리전 비용을 피한다.

## 참고

- AWS EventBridge 사용자 가이드: https://docs.aws.amazon.com/eventbridge/
- EventBridge 요금: https://aws.amazon.com/eventbridge/pricing/
- 이벤트 패턴 레퍼런스: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html

