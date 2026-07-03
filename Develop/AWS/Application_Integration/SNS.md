---
title: AWS SNS (Simple Notification Service)
tags: [aws, sns, notification, messaging, pub-sub, serverless]
updated: 2026-05-29
---

# AWS SNS (Simple Notification Service)

## 서비스 개요

AWS SNS(Simple Notification Service)는 완전 관리형 메시지 알림 서비스다. 애플리케이션과 서비스 사이에서 메시지를 전달하는 중앙 허브 역할을 한다. 퍼블리셔-구독자(Pub-Sub) 패턴을 따르며, 한 곳에서 메시지를 발행하면 여러 구독자에게 동시에 전달한다.

### 핵심 아키텍처 개념

**퍼블리셔(Publisher)**

메시지를 만들어 SNS 주제에 발행하는 주체다. 애플리케이션, 서비스, AWS 서비스가 퍼블리셔가 될 수 있다. 발행할 때 구독자가 누구인지 알 필요가 없다. 주제에 메시지를 보내면 SNS가 모든 구독자에게 전달한다.

주문 서비스가 주문 완료 이벤트를 발행하면 재고 서비스, 결제 서비스, 배송 서비스가 각각 구독한다. 주문 서비스는 어떤 서비스가 구독하는지 알 필요가 없다. 새 서비스가 추가돼도 주문 서비스 코드는 그대로 둔다.

**주제(Topic)**

메시지의 중앙 엔드포인트다. 고유한 ARN(Amazon Resource Name)을 가진다. 메시지를 받아 모든 구독자에게 전달한다.

주제는 논리적으로 관련된 메시지를 묶는다. "주문-이벤트" 주제에는 주문 생성, 주문 취소, 주문 완료 이벤트가 발행된다. 각 이벤트 타입은 메시지 속성으로 구분한다.

**구독자(Subscriber)**

주제를 구독해 메시지를 받는 엔드포인트다. 이메일, SMS, 모바일 푸시, HTTP(S), Lambda, SQS 등을 지원한다.

같은 주제에 구독자가 여럿 등록돼 있으면 메시지 발행 시 모두에게 동시에 전달한다. 구독자 하나가 실패해도 나머지에는 영향이 없다.

## 핵심 특징

### 푸시 기반 메시징

SNS는 푸시 기반으로 동작한다. 구독자가 메시지를 폴링하지 않아도 발생 시점에 바로 전달받는다.

폴링 방식은 클라이언트가 주기적으로 서버에 요청을 보내 메시지가 있는지 확인한다. 메시지가 없어도 계속 요청을 보내므로 빈 트래픽과 서버 부하가 생긴다. 푸시 방식은 메시지가 생겼을 때만 보내므로 빈 요청이 없다.

SNS는 메시지가 발행되면 즉시 모든 구독자에게 전달을 시도한다. HTTP 엔드포인트면 POST 요청으로 전달하고, Lambda면 함수를 트리거하고, SQS 큐면 큐에 메시지를 넣는다.

### 확장성과 가용성

SNS는 트래픽 증가에 맞춰 자동으로 확장된다. 초당 수백만 건의 메시지를 처리한다. 99.9% 이상의 가용성 SLA를 제공한다.

트래픽이 갑자기 늘어도 별도 설정 없이 처리량이 따라 올라간다. 블랙프라이데이처럼 주문이 급증해도 SNS는 자동으로 확장돼 메시지를 모두 처리한다.

SNS는 여러 가용 영역에 걸쳐 운영된다. 한 가용 영역에 장애가 나도 다른 영역에서 서비스를 이어간다.

### 전송 프로토콜 지원

**이메일**

SMTP로 이메일 알림을 보낸다. 단순 텍스트와 HTML 이메일을 모두 지원한다. 구독자로 이메일 주소를 등록하면 메시지 발행 시 해당 주소로 메일이 간다.

이메일 구독은 확인 과정이 필요하다. SNS가 주소로 확인 링크를 보내고 사용자가 클릭해야 구독이 활성화된다. 스팸 방지 조치다.

**SMS**

전 세계 모바일 기기로 문자를 보낸다. 국가마다 비용이 다르고 일일 전송 한도가 있다. SMS는 비용이 높으므로 중요한 알림에만 쓴다.

SMS 구독도 확인 과정이 필요하다. 사용자가 받은 확인 코드를 입력해야 활성화된다.

**모바일 푸시**

APNS(Apple Push Notification Service), FCM(Google Firebase Cloud Messaging), ADM(Amazon Device Messaging)을 지원한다. iOS, Android, Kindle 기기로 푸시 알림을 보낸다.

모바일 푸시를 쓰려면 각 플랫폼의 인증서나 키를 SNS에 등록한다. APNS는 인증서나 키를 업로드하고, FCM은 서버 키를 등록한다.

**HTTP/HTTPS**

RESTful API 엔드포인트로 메시지를 전달한다. 구독자로 HTTP/HTTPS URL을 등록하면 메시지 발행 시 해당 URL로 POST 요청을 보낸다.

HTTP 엔드포인트는 200 OK를 반환해야 구독이 유지된다. 계속 실패하면 구독이 비활성화된다. 일시적으로 응답하지 못하는 경우를 대비해 재시도가 있다.

**AWS 서비스**

Lambda, SQS, Kinesis Data Firehose 등과 연동한다. Lambda 함수를 구독자로 등록하면 메시지 발행 시 함수가 트리거된다. SQS 큐를 등록하면 큐에 메시지가 들어간다.

### 메시지 필터링

구독자별로 필터 정책을 설정해 필요한 메시지만 받는다. 불필요한 트래픽과 비용을 줄인다.

"주문-이벤트" 주제에 구독자가 여럿 있다. 재고 서비스는 주문 생성 이벤트만, 배송 서비스는 주문 완료 이벤트만 필요하다. 각 구독에 필터 정책을 걸면 필요한 메시지만 받는다.

필터 정책은 기본적으로 메시지 속성을 기준으로 동작한다. 메시지에 담긴 속성 값으로 거른다. 여러 조건을 AND, OR로 조합한다.

## 메시지 전달 보장과 재시도

### At-Least-Once 전달 보장

SNS는 메시지가 최소 한 번은 전달되도록 보장한다. 네트워크 오류나 일시적 장애로 전달이 실패하면 자동으로 재시도한다.

At-Least-Once는 메시지가 한 번 이상 전달될 수 있다는 뜻이다. 재시도 과정에서 같은 메시지가 여러 번 전달될 수 있다. 구독자는 중복 메시지를 처리할 수 있어야 한다.

메시지에 고유 ID를 넣거나 구독자 쪽에서 중복 제거 로직을 둔다. SQS를 구독자로 쓰면 SQS의 중복 제거 기능을 쓸 수 있다.

### 재시도 정책

**표준 주제**

지수 백오프로 재시도한다. 첫 재시도는 짧은 간격으로 하고, 실패할수록 간격을 늘린다. 최대 재시도 횟수에 도달하면 전달을 포기한다.

재시도 간격은 구독자 타입마다 다르다. HTTP 엔드포인트는 즉시 재시도한 뒤 점차 간격을 늘리고, Lambda는 Lambda의 재시도 정책을 따른다.

**FIFO 주제**

순서가 보장되는 전달을 제공한다. 메시지 그룹 ID를 기준으로 순서를 보장한다. 같은 그룹 ID를 가진 메시지는 발행 순서대로 전달된다.

FIFO 주제는 표준 주제보다 처리량이 낮다. 순서가 중요한 경우에만 쓴다.

**Dead Letter Queue**

최대 재시도 횟수를 넘겨도 전달되지 못한 메시지는 Dead Letter Queue(DLQ)로 보낸다. SQS 큐를 DLQ로 지정하면 실패한 메시지가 그 큐로 간다.

DLQ에 쌓인 메시지는 모니터링하고 주기적으로 확인해 원인을 해결한다. DLQ에 메시지가 계속 쌓이면 구독자 쪽에 문제가 있다는 신호다.

## 보안과 접근 제어

### IAM 기반 권한 관리

IAM으로 세밀하게 권한을 제어한다. 주제별, 구독자별로 접근 권한을 설정한다. 교차 계정 액세스도 지원한다.

주제에 대한 Publish 권한을 특정 IAM 역할이나 사용자에게만 준다. 이렇게 하면 인증된 주체만 메시지를 발행한다.

구독자에 대한 Subscribe 권한도 제어한다. 특정 주제에 구독을 추가하거나 제거하는 권한을 제한한다.

### 암호화

**전송 중 암호화**

TLS/SSL로 전송 중 암호화를 제공한다. HTTP 엔드포인트로 전달할 때 HTTPS를 쓰면 메시지가 암호화돼 전송된다.

**저장 시 암호화**

KMS 키로 저장 시 암호화를 설정한다. 주제를 만들 때 KMS 키를 지정하면 메시지가 암호화돼 저장된다.

**엔드포인트 인증**

HTTP 엔드포인트는 메시지 서명으로 무결성을 확인한다. SNS가 보내는 모든 메시지에는 서명이 들어 있다. 구독자는 서명을 검증해 메시지가 SNS에서 온 것인지 확인한다.

서명을 검증하지 않으면 누군가 가짜 메시지를 보낼 수 있다. 서명은 반드시 검증한다.

## 비용 구조

### 사용량 기반 과금

메시지 발행 건수에 따라 과금된다. 전송 프로토콜마다 요금이 다르다. 데이터 전송 비용은 별도로 붙는다.

표준 주제는 메시지 발행 자체가 무료다. 구독자에게 전달할 때만 비용이 든다. HTTP 엔드포인트로 전달하면 전달 건수당 요금이 붙는다. Lambda로 전달하면 Lambda 실행 비용만 들고 SNS 전달 비용은 없다.

SMS는 비용이 높다. 국가마다 요금이 다르고 일일 전송 한도가 있다. SMS를 대량으로 보내면 예상치 못한 비용이 생긴다.

### 비용 줄이기

**메시지 필터링**

필터링으로 불필요한 전송을 막으면 비용이 준다. 구독자가 필요 없는 메시지를 받지 않도록 필터 정책을 건다.

**메시지 크기**

메시지 크기를 줄이면 전송 비용이 준다. 큰 데이터는 S3에 저장하고 참조 링크만 메시지에 넣는다.

**리전 선택**

리전마다 가격이 다를 수 있다. 비용을 따져 리전을 고른다.

## 실제 사용 사례

### 이커머스 주문 알림 시스템

온라인 쇼핑몰에서 주문이 발생하면 SNS로 여러 알림을 동시에 보낸다. 주문 확인 이메일, 배송 상태 SMS, 모바일 앱 푸시를 한 주제에서 관리한다.

주문 서비스는 주문 완료 이벤트를 SNS 주제에 발행한다. 이메일 서비스는 주문 확인 메일을, SMS 서비스는 배송 시작 알림을, 모바일 앱은 푸시를 보낸다. 각 서비스는 독립적으로 동작하고 하나가 실패해도 나머지에 영향이 없다.

### 모니터링 및 알림 시스템

시스템 장애나 임계값 초과 시 개발팀, 운영팀, 관리자에게 즉시 알린다. CloudWatch와 연동해 자동화된 모니터링을 구성한다.

CloudWatch 알람이 임계값을 넘으면 SNS 주제에 알림을 발행한다. 개발팀은 Slack으로, 운영팀은 이메일로, 관리자는 SMS로 받는다. 심각도에 따라 알림 채널을 나눈다.

### 마이크로서비스 간 이벤트 전파

마이크로서비스 아키텍처에서 서비스 간 결합을 느슨하게 두려고 SNS를 쓴다. 주문 서비스가 주문 완료 이벤트를 발행하면 재고 관리, 결제, 배송 서비스가 각자 필요한 작업을 한다.

주문 서비스는 다른 서비스를 알 필요가 없다. 새 서비스가 추가돼도 주문 서비스 코드는 그대로 두고, 이벤트를 구독하는 서비스만 붙인다.

### 개인화 푸시 알림

앱 사용자에게 맞춤 푸시를 보낸다. 사용자 행동 패턴에 따라 다른 메시지를 보낸다.

사용자가 특정 상품을 조회하면 그 상품의 할인 알림을 보낸다. 장바구니에 담긴 상품이 있으면 구매 유도 메시지를 보낸다. 필터링으로 사용자별로 다른 메시지를 보낸다.

## SNS와 다른 AWS 서비스 연동

### SNS + SQS 패턴

SNS 주제에 SQS 큐를 구독자로 붙이는 팬아웃은 가장 많이 쓰는 구성이다. SNS는 푸시, SQS는 풀이라서, SNS가 큐에 메시지를 넣어 두면 소비자는 자기 속도로 꺼내 처리한다. 소비자가 잠깐 죽어도 메시지가 큐에 남아 있어 복구 후 이어서 처리한다. 트래픽이 튀어도 큐가 버퍼 역할을 해 소비자가 밀리지 않는다.

문제는 "구독을 걸었는데 메시지가 안 들어온다"는 상황이 흔하다는 점이다. 대부분 큐 액세스 정책, RawMessageDelivery, 필터 정책, FIFO 설정 중 하나를 빠뜨린 경우다. 아래에서 하나씩 짚는다.

#### SQS 큐 액세스 정책

`aws sns subscribe`를 호출하면 구독은 바로 만들어지지만, 그것만으로는 메시지가 큐에 들어오지 않는다. SNS 서비스 주체(`sns.amazonaws.com`)가 큐에 `sqs:SendMessage`를 할 권한이 큐 쪽에 있어야 한다. 콘솔에서 구독을 만들면 이 정책을 자동으로 붙여 주지만, CLI나 IaC로 만들면 직접 넣어야 한다.

큐 액세스 정책 예시:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSNSPublish",
      "Effect": "Allow",
      "Principal": { "Service": "sns.amazonaws.com" },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:ap-northeast-2:123456789012:order-fulfillment",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:sns:ap-northeast-2:123456789012:order-events"
        }
      }
    }
  ]
}
```

CLI로 적용한다. `set-queue-attributes`의 `Policy` 속성은 위 JSON을 문자열로 넣어야 한다:

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.ap-northeast-2.amazonaws.com/123456789012/order-fulfillment \
  --attributes Policy="$(cat queue-policy.json | jq -c . | jq -Rs .)"
```

`aws:SourceArn` 조건은 반드시 건다. 조건이 없으면 아무 SNS 주제나 이 큐에 메시지를 넣을 수 있어 confused deputy 문제가 생긴다. 조건을 토픽 ARN으로 좁혀 두면 그 토픽에서 온 메시지만 받는다.

구독이 `Confirmed`로 보이는데 메시지가 안 들어오면 십중팔구 이 큐 정책 누락이다. 토픽의 CloudWatch 지표 `NumberOfMessagesPublished`는 올라가는데 큐의 `NumberOfMessagesSent`/`ApproximateNumberOfMessagesVisible`이 그대로면 권한 문제로 보면 된다. 토픽에 DLQ를 걸어 두지 않았다면 이때 메시지는 그냥 버려진다.

#### RawMessageDelivery 차이

구독자가 실제로 받는 페이로드 모양은 `RawMessageDelivery` 설정에 따라 달라진다. 이 차이를 모르고 소비자 코드를 짜면 파싱에서 깨진다.

기본값은 `false`다. SNS가 원본 페이로드를 envelope(봉투) JSON으로 감싸서 큐에 넣는다. 실제 메시지는 `Message` 필드에 문자열로 들어가고, 메시지 속성은 `MessageAttributes` 안에 박힌다. 큐에 들어오는 본문은 이렇게 생겼다:

```json
{
  "Type": "Notification",
  "MessageId": "22b80b92-...",
  "TopicArn": "arn:aws:sns:ap-northeast-2:123456789012:order-events",
  "Subject": "주문 이벤트: ORDER_COMPLETED",
  "Message": "{\"orderId\":\"order-001\",\"status\":\"COMPLETED\"}",
  "Timestamp": "2026-05-29T08:12:03.456Z",
  "SignatureVersion": "1",
  "Signature": "EXAMPLEpH+...",
  "SigningCertURL": "https://sns.ap-northeast-2.amazonaws.com/...",
  "UnsubscribeURL": "https://sns.ap-northeast-2.amazonaws.com/?Action=Unsubscribe...",
  "MessageAttributes": {
    "eventType": { "Type": "String", "Value": "ORDER_COMPLETED" }
  }
}
```

소비자는 SQS 본문을 파싱한 뒤 다시 `Message`를 파싱해야 한다. 두 번 파싱한다:

```javascript
const outer = JSON.parse(record.body);      // SNS envelope
const payload = JSON.parse(outer.Message);  // 실제 주문 데이터
const eventType = outer.MessageAttributes?.eventType?.Value;
```

`RawMessageDelivery=true`로 켜면 envelope 없이 원본 페이로드만 큐에 들어간다. 메시지 속성은 SNS envelope 안이 아니라 SQS 메시지 속성으로 그대로 넘어간다. 큐 본문은 이렇게 단순해진다:

```json
{"orderId":"order-001","status":"COMPLETED"}
```

소비자는 한 번만 파싱하고, 속성은 SQS 메시지 속성에서 읽는다:

```javascript
const payload = JSON.parse(record.body);                 // 바로 주문 데이터
const eventType = record.messageAttributes?.eventType?.stringValue;
```

raw delivery 켜기:

```bash
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:ap-northeast-2:123456789012:order-events:abc123 \
  --attribute-name RawMessageDelivery \
  --attribute-value true
```

같은 큐가 SNS 구독과 직접 SQS 전송을 함께 받는다면 raw delivery를 켜서 본문 형식을 맞추는 게 낫다. 반대로 `Subject`, `Timestamp`, 서명 같은 envelope 필드를 소비자가 쓰고 있었다면 raw로 바꾸는 순간 그 값들이 사라지므로 주의한다. 필터 정책은 raw 여부와 무관하게 동작한다. 속성이 SQS 메시지 속성으로 옮겨가도 SNS가 구독 단계에서 거르기 때문이다.

#### FIFO 토픽 → FIFO 큐 연동

순서와 중복 제거가 필요하면 FIFO 토픽에 FIFO 큐를 붙인다. 페어링 제약이 있다. FIFO 토픽에는 SQS FIFO 큐만 구독자로 붙는다. 표준 큐는 FIFO 토픽을 구독할 수 없고, FIFO 큐는 표준 토픽을 구독할 수 없다. 토픽과 큐의 종류를 맞춰야 한다.

FIFO 토픽에 발행할 때는 `MessageGroupId`가 필수다. 같은 그룹 ID끼리만 순서가 보장되므로, 순서를 지켜야 하는 단위(예: 한 사용자, 한 주문)를 그룹 ID로 잡는다. 중복 제거는 `MessageDeduplicationId`를 명시하거나, 토픽에 `ContentBasedDeduplication=true`를 켜서 본문 SHA-256으로 자동 계산하게 한다.

```bash
# FIFO 토픽 생성 (콘텐츠 기반 중복 제거)
aws sns create-topic \
  --name order-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true

# FIFO 큐 생성
aws sqs create-queue \
  --queue-name order-fulfillment.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true

# 발행 (그룹 ID로 사용자 단위 순서 보장)
aws sns publish \
  --topic-arn arn:aws:sns:ap-northeast-2:123456789012:order-events.fifo \
  --message '{"orderId":"order-001","status":"COMPLETED"}' \
  --message-group-id "user-123" \
  --message-deduplication-id "order-001-completed"
```

SNS는 발행 시 받은 `MessageGroupId`와 `MessageDeduplicationId`를 구독한 FIFO 큐로 그대로 전파한다. 그래서 발행 → 토픽 → 큐 → 소비자까지 그룹 단위 순서가 유지된다. 토픽에서 `ContentBasedDeduplication`을 켜면 토픽 레벨에서 중복을 걸러 같은 본문이 큐로 두 번 가지 않는다. 큐에도 자체 `ContentBasedDeduplication`이 따로 있으므로, 직접 SQS로도 보낼 거면 큐 쪽도 함께 설정한다.

토픽의 중복 제거 윈도는 5분이다. 같은 dedup ID로 5분 안에 다시 발행하면 두 번째는 조용히 버려진다. 재처리 테스트를 하다가 "발행은 됐는데 큐에 안 들어온다"면 dedup 윈도에 걸린 경우가 많으니 dedup ID를 바꿔서 확인한다.

#### 필터 정책 연산자

필터 정책은 기본적으로 메시지 속성을 본다. 같은 키 안의 배열은 OR, 서로 다른 키는 AND로 묶인다. 자주 쓰는 연산자를 한 정책에 모아 보면:

```json
{
  "eventType": ["ORDER_COMPLETED", "ORDER_REFUNDED"],
  "region":    [{ "prefix": "KR" }],
  "amount":    [{ "numeric": [">=", 10000, "<", 1000000] }],
  "channel":   [{ "anything-but": ["TEST", "INTERNAL"] }],
  "couponCode":[{ "exists": true }]
}
```

- exact: `["ORDER_COMPLETED", "ORDER_REFUNDED"]` — 값이 둘 중 하나와 정확히 일치.
- numeric: `[{"numeric": [">=", 10000]}]` 단일 비교, `[{"numeric": [">=", 10000, "<", 1000000]}]` 범위. `=`도 가능하다.
- prefix: `[{"prefix": "KR"}]` — `KR`, `KR-SEOUL` 등 접두사 매칭.
- anything-but: `[{"anything-but": ["TEST"]}]` — 해당 값을 뺀 나머지. `[{"anything-but": {"prefix": "TEST"}}]`처럼 접두사 부정도 된다.
- exists: `[{"exists": true}]` 속성이 있으면 통과, `[{"exists": false}]` 속성이 없으면 통과.

자주 걸리는 함정 두 가지가 있다. 첫째, numeric 매칭은 속성을 `Number` 타입으로 발행해야 한다. `String`으로 보내면 `{"numeric": ...}` 조건이 절대 매칭되지 않는다. 둘째, 필터가 참조하는 속성이 메시지에 없으면(그리고 `exists: false`로 다루지 않으면) 그 메시지는 해당 구독자에게 전달되지 않는다. 필터 정책이 아예 없는 구독자는 모든 메시지를 받는다.

본문(raw payload)을 기준으로 거르고 싶으면 `FilterPolicyScope`를 `MessageBody`로 바꾼다. raw delivery로 속성을 따로 안 싣는 구성에서 쓸모가 있다:

```bash
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:ap-northeast-2:123456789012:order-events:abc123 \
  --attribute-name FilterPolicyScope \
  --attribute-value MessageBody

aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:ap-northeast-2:123456789012:order-events:abc123 \
  --attribute-name FilterPolicy \
  --attribute-value '{"status":["COMPLETED"],"amount":[{"numeric":[">=",10000]}]}'
```

#### 구독별 redrive policy (DLQ)

DLQ에는 두 종류가 있고 막는 실패가 다르다. 둘을 헷갈리면 엉뚱한 큐만 비워 두고 메시지를 잃는다.

- 구독 redrive policy: SNS가 구독 엔드포인트(여기서는 SQS 큐)로 전달하는 데 재시도까지 실패했을 때 보내는 DLQ. 구독 단위로 건다.
- SQS 큐 자체의 redrive policy: 소비자가 메시지를 처리하지 못해 `maxReceiveCount`를 넘겼을 때 보내는 DLQ. 큐 단위로 건다.

SNS→SQS는 AWS 내부 전송이라 구독 단계 전달은 거의 실패하지 않는다. 실무에서 메시지를 잃는 지점은 대부분 소비자 처리 실패 쪽이므로 SQS 큐의 redrive policy가 더 중요하다. 둘 다 거는 게 안전하다.

구독 redrive policy 설정:

```bash
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:ap-northeast-2:123456789012:order-events:abc123 \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:ap-northeast-2:123456789012:sns-delivery-dlq"}'
```

이 DLQ도 SQS 큐이므로, 구독 대상 큐와 똑같이 `sns.amazonaws.com`이 `sqs:SendMessage`를 할 수 있도록 큐 정책을 걸어 줘야 한다(조건은 토픽 ARN으로 좁히고, 더 엄격히 하려면 구독 ARN으로 좁힌다). 정책을 빠뜨리면 전달 실패 메시지가 DLQ에도 못 들어가고 사라진다.

소비자 처리 실패용 DLQ는 SQS 큐의 redrive policy로 건다:

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.ap-northeast-2.amazonaws.com/123456789012/order-fulfillment \
  --attributes RedrivePolicy='{"deadLetterTargetArn":"arn:aws:sqs:ap-northeast-2:123456789012:order-fulfillment-dlq","maxReceiveCount":"5"}'
```

CloudFormation으로 구독 하나에 raw delivery, 필터, 구독 DLQ를 함께 거는 예시:

```yaml
FulfillmentSubscription:
  Type: AWS::SNS::Subscription
  Properties:
    TopicArn: !Ref OrderEventsTopic
    Protocol: sqs
    Endpoint: !GetAtt FulfillmentQueue.Arn
    RawMessageDelivery: true
    FilterPolicy:
      eventType:
        - ORDER_COMPLETED
      amount:
        - numeric: [">=", 10000]
    RedrivePolicy: !Sub '{"deadLetterTargetArn":"${SnsDeliveryDlq.Arn}"}'
```

### SNS + Lambda 패턴

Lambda 함수를 SNS 구독자로 설정해 서버리스 이벤트 처리를 구성한다. 메시지를 받으면 함수가 자동으로 실행돼 비즈니스 로직을 처리한다.

Lambda는 트래픽에 맞춰 자동으로 확장된다. 메시지가 많으면 인스턴스가 늘어난다. 비용은 실행 시간과 메모리 사용량으로 정해진다.

Lambda 함수가 실패하면 SNS가 재시도한다. 최대 재시도를 넘기면 DLQ로 메시지를 보낸다.

### SNS + CloudWatch 패턴

CloudWatch 알람이 임계값을 넘으면 SNS로 알림을 보낸다. 모니터링과 알림을 자동화한다.

CloudWatch 메트릭이 임계값을 넘으면 알람이 트리거된다. 알람은 SNS 주제에 메시지를 발행하고 구독자가 알림을 받는다.

알람 여러 개를 한 SNS 주제로 모으면 알림을 중앙에서 관리한다. 알림 채널을 바꾸거나 추가할 때 구독자만 수정한다.

## 운영 시 주의사항

### 메시지 설계

**메시지 크기 최소화**

메시지 크기를 줄여 전송 비용을 아낀다. 큰 데이터는 S3에 저장하고 참조 링크만 넣는다. 단일 메시지 최대 크기는 256KB다.

**구조화된 메시지 형식**

JSON 형식으로 보내 소비자가 파싱하기 쉽게 한다. 메시지 구조를 일관되게 유지한다.

**메시지 버전 관리**

메시지에 버전 정보를 넣어 하위 호환을 유지한다. 구조가 바뀌어도 소비자가 버전에 따라 다르게 처리한다.

### 모니터링과 로깅

**CloudWatch 메트릭**

메시지 전송 성공률을 본다. 실패 건수, 전송 지연 시간을 추적한다.

**Dead Letter Queue**

실패 메시지용 DLQ를 건다. DLQ에 메시지가 쌓이면 구독자 쪽 문제라는 신호다. 주기적으로 확인해 해결한다.

**구독자별 전송 지연 시간**

구독자별 전송 지연을 추적한다. 특정 구독자로의 전송이 느리면 그 구독자 문제일 수 있다.

### 보안

**민감한 정보 처리**

민감한 정보는 메시지에 넣지 않고 참조 ID만 보낸다. 비밀번호 대신 사용자 ID만 넣는다.

**HTTPS 엔드포인트 사용**

HTTP 엔드포인트로 전달할 때는 HTTPS를 써서 전송 중 암호화를 보장한다.

**주제 정책**

주제 정책으로 접근 권한을 세밀하게 제어한다. 특정 IAM 역할이나 사용자만 발행하도록 제한한다.

**서명 검증**

HTTP 엔드포인트는 메시지 서명을 반드시 검증한다. 검증하지 않으면 누군가 가짜 메시지를 보낼 수 있다.

### 전송 줄이기

**메시지 필터링**

필터링으로 불필요한 전송을 막는다. 구독자가 필요 없는 메시지를 받지 않도록 필터 정책을 건다.

**SQS와 연동**

배치 처리가 가능한 경우 SQS와 연동한다. SQS에서 메시지를 배치로 가져와 처리하면 비용이 준다.

**리전 선택**

리전별 가격 차이를 따져 리전을 고른다. 지연 시간도 함께 본다.

## 주의사항과 제한

### 메시지 크기 제한

단일 메시지 최대 크기는 256KB다. 큰 데이터는 S3에 저장하고 참조 링크만 보낸다.

메시지에 큰 데이터를 넣으면 전송 비용이 늘고 전송 시간이 길어진다. 소비자가 처리하는 데 시간이 더 걸린다.

### 전송 프로토콜별 제한

**SMS**

일일 전송 한도가 있고 국가별 제한이 있다. 비용이 높으므로 중요한 알림에만 쓴다.

SMS를 대량으로 보내면 예상치 못한 비용이 생긴다. 비용 알람을 걸어 예산을 넘지 않게 한다.

**이메일**

스팸 필터로 전송이 실패할 수 있다. 메일 제공자가 스팸으로 판단하면 전달되지 않는다.

발신 주소를 신뢰할 수 있는 도메인으로 두고, SPF, DKIM 레코드를 설정해 스팸으로 분류되지 않게 한다.

**모바일 푸시**

플랫폼별 인증서를 관리해야 한다. APNS는 인증서나 키를 업로드하고, FCM은 서버 키를 등록한다.

인증서가 만료되면 푸시가 나가지 않는다. 만료일을 모니터링하고 갱신한다.

### 비용 관리

메시지 발행 건수로 과금되므로 예상치 못한 비용이 생길 수 있다. 사용량을 모니터링하고 비용 알람을 걸어 예산을 넘지 않게 한다.

필터링으로 불필요한 전송을 막으면 비용이 준다. 구독자가 필요 없는 메시지를 받지 않도록 필터 정책을 건다.

### 웹 클라이언트 직접 연결 불가

SNS는 웹 브라우저에서 직접 구독할 수 없다. HTTP/HTTPS 엔드포인트로만 구독하고, 이 엔드포인트는 서버 측이어야 한다.

웹 브라우저에서 실시간으로 메시지를 받아야 하면 WebSocket이나 Socket.IO 같은 실시간 통신 프로토콜을 쓴다. SNS → SQS → Lambda → WebSocket 서버 경로로 전달하거나 API Gateway WebSocket API를 쓴다.

---

## 코드 예제

### AWS CLI로 SNS 설정

```bash
# ── 토픽 생성 ─────────────────────────────────────────
TOPIC_ARN=$(aws sns create-topic \
  --name order-events \
  --attributes DisplayName="주문 이벤트" \
  --query 'TopicArn' --output text)

echo "Topic ARN: $TOPIC_ARN"

# FIFO 토픽 (순서 보장, 중복 제거)
FIFO_TOPIC_ARN=$(aws sns create-topic \
  --name order-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true \
  --query 'TopicArn' --output text)

# ── 구독 추가 ─────────────────────────────────────────
# SQS 구독
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:ap-northeast-2:123456789012:order-queue

# 이메일 구독
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint ops-team@example.com

# Lambda 구독
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:ap-northeast-2:123456789012:function:order-processor

# ── 메시지 발행 ───────────────────────────────────────
aws sns publish \
  --topic-arn $TOPIC_ARN \
  --message '{"orderId":"order-001","userId":"user-123","status":"COMPLETED"}' \
  --message-attributes '{
    "eventType": {"DataType":"String","StringValue":"ORDER_COMPLETED"},
    "region":    {"DataType":"String","StringValue":"KR"},
    "amount":    {"DataType":"Number","StringValue":"50000"}
  }'

# ── 구독 목록 확인 ────────────────────────────────────
aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN
```

> numeric 필터를 걸 속성(`amount`)은 위처럼 `DataType:Number`로 발행한다. `String`으로 보내면 numeric 조건이 매칭되지 않는다.

### 필터 정책 설정 (메시지 선별 구독)

```bash
# 한국 주문, 1만원 이상, 취소 이벤트 제외, 쿠폰 있는 건만 처리
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:ap-northeast-2:...:order-events:abc123 \
  --attribute-name FilterPolicy \
  --attribute-value '{
    "eventType": [{"anything-but": ["ORDER_CANCELLED"]}],
    "region":    [{"prefix": "KR"}],
    "amount":    [{"numeric": [">=", 10000]}],
    "couponCode":[{"exists": true}]
  }'
```

### Node.js AWS SDK로 SNS 발행

```javascript
const { SNSClient, PublishCommand, CreateTopicCommand } = require('@aws-sdk/client-sns');

const sns = new SNSClient({ region: 'ap-northeast-2' });
const TOPIC_ARN = process.env.ORDER_EVENTS_TOPIC_ARN;

// ── 단일 메시지 발행 ──────────────────────────────────
async function publishOrderEvent(event) {
    const response = await sns.send(new PublishCommand({
        TopicArn: TOPIC_ARN,
        Message: JSON.stringify(event),
        MessageAttributes: {
            eventType: { DataType: 'String', StringValue: event.type },
            userId:    { DataType: 'String', StringValue: event.userId },
            amount:    { DataType: 'Number', StringValue: String(event.totalAmount) }
        },
        Subject: `주문 이벤트: ${event.type}`
    }));
    console.log('Published MessageId:', response.MessageId);
    return response.MessageId;
}

// 사용
await publishOrderEvent({
    type: 'ORDER_COMPLETED',
    orderId: 'order-001',
    userId: 'user-123',
    totalAmount: 50000
});

// ── 채널별 다른 메시지 (Message Structure) ───────────
await sns.send(new PublishCommand({
    TopicArn: TOPIC_ARN,
    MessageStructure: 'json',
    Message: JSON.stringify({
        default: '주문이 완료되었습니다.',
        email:   '주문 #order-001이 완료되었습니다. 배송을 준비 중입니다.',
        sqs:     JSON.stringify({ orderId: 'order-001', event: 'COMPLETED' })
    })
}));
```

### SNS → SQS 팬아웃 패턴

```
주문 서비스
    ↓ Publish
[SNS Topic: order-events]
    ├── SQS: order-fulfillment-queue  → 재고/배송 처리 Lambda
    ├── SQS: notification-queue       → 이메일/SMS 알림 Lambda
    ├── SQS: analytics-queue          → 분석/BI 처리 Lambda
    └── Lambda: fraud-detection       → 실시간 사기 탐지
```

```bash
# CloudFormation으로 팬아웃 아키텍처 구성
cat > fanout-stack.yaml << 'EOF'
Resources:
  OrderEventsTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: order-events

  FulfillmentQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: order-fulfillment
      VisibilityTimeout: 300

  # SNS가 큐에 메시지를 넣을 수 있도록 큐 정책 부여
  FulfillmentQueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      Queues:
        - !Ref FulfillmentQueue
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: AllowSNSPublish
            Effect: Allow
            Principal:
              Service: sns.amazonaws.com
            Action: sqs:SendMessage
            Resource: !GetAtt FulfillmentQueue.Arn
            Condition:
              ArnEquals:
                aws:SourceArn: !Ref OrderEventsTopic

  FulfillmentSubscription:
    Type: AWS::SNS::Subscription
    Properties:
      TopicArn: !Ref OrderEventsTopic
      Protocol: sqs
      Endpoint: !GetAtt FulfillmentQueue.Arn
      RawMessageDelivery: true
      FilterPolicy:
        eventType:
          - ORDER_COMPLETED

  NotificationQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: notification

  NotificationQueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      Queues:
        - !Ref NotificationQueue
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: sns.amazonaws.com
            Action: sqs:SendMessage
            Resource: !GetAtt NotificationQueue.Arn
            Condition:
              ArnEquals:
                aws:SourceArn: !Ref OrderEventsTopic

  NotificationSubscription:
    Type: AWS::SNS::Subscription
    Properties:
      TopicArn: !Ref OrderEventsTopic
      Protocol: sqs
      Endpoint: !GetAtt NotificationQueue.Arn
      FilterPolicy:
        eventType:
          - ORDER_COMPLETED
          - ORDER_CANCELLED
          - PAYMENT_FAILED
EOF

aws cloudformation deploy --template-file fanout-stack.yaml --stack-name order-fanout
```

### Lambda에서 SNS 이벤트 수신

```javascript
// SNS → Lambda 연동 시 이벤트 구조 (Lambda 구독은 raw delivery 없이 envelope로 전달)
exports.handler = async (event) => {
    for (const record of event.Records) {
        const snsMessage = record.Sns;
        console.log('Subject:', snsMessage.Subject);
        console.log('Timestamp:', snsMessage.Timestamp);

        const body = JSON.parse(snsMessage.Message);
        const attrs = snsMessage.MessageAttributes;

        const eventType = attrs.eventType?.Value;
        console.log(`Processing ${eventType}:`, body);

        switch (eventType) {
            case 'ORDER_COMPLETED':
                await handleOrderCompleted(body);
                break;
            case 'ORDER_CANCELLED':
                await handleOrderCancelled(body);
                break;
        }
    }
};
```

### SQS 소비자에서 SNS 메시지 처리

```javascript
// 같은 큐를 RawMessageDelivery on/off 모두 받을 수 있게 방어적으로 파싱
function extractPayload(record) {
    const body = JSON.parse(record.body);

    // raw delivery=false 면 SNS envelope 구조다
    if (body.Type === 'Notification' && typeof body.Message === 'string') {
        const payload = JSON.parse(body.Message);
        const attrs = body.MessageAttributes ?? {};
        const eventType = attrs.eventType?.Value;
        return { payload, eventType };
    }

    // raw delivery=true 면 본문이 곧 페이로드, 속성은 SQS 메시지 속성에서
    const eventType = record.messageAttributes?.eventType?.stringValue;
    return { payload: body, eventType };
}

exports.handler = async (event) => {
    for (const record of event.Records) {
        const { payload, eventType } = extractPayload(record);
        console.log(`Processing ${eventType}:`, payload);
        // 처리 실패 시 throw → 가시성 타임아웃 후 재시도 → maxReceiveCount 초과 시 큐 DLQ로 이동
    }
};
```

---

## 참고 자료

### AWS 공식 문서

- [AWS SNS 개발자 가이드](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/welcome.html)
- [SNS API 참조](https://docs.aws.amazon.com/ko_kr/sns/latest/api/welcome.html)
- [SNS 보안 문서](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-security-best-practices.html)

### AWS 서비스 연동 문서

- [SNS와 SQS 연동](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-sqs-as-subscriber.html)
- [SNS 메시지 필터링](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-message-filtering.html)
- [SNS 구독 DLQ (redrive policy)](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-dead-letter-queues.html)
- [SNS FIFO 토픽](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-fifo-topics.html)
- [SNS와 Lambda 연동](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-lambda-as-subscriber.html)
- [CloudWatch와 SNS 연동](https://docs.aws.amazon.com/ko_kr/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html)

### SDK 및 도구

- [AWS SDK for JavaScript v3](https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/sns-examples.html)
- [AWS CLI SNS 명령어](https://docs.aws.amazon.com/cli/latest/reference/sns/)
- [AWS CDK SNS 구성 요소](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sns-readme.html)
