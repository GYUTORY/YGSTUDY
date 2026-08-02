---
title: DLQ 재처리 자동화
tags: [messaging, dlq, dead-letter-queue, kafka, rabbitmq, sqs, idempotency, monitoring, parking-lot]
updated: 2026-08-02
---

# DLQ 재처리 자동화

DLQ에 메시지가 쌓였을 때 나중에 보자고 넘기는 팀이 많다. 그런데 정작 재처리가 필요한 시점에 어떤 메시지가 왜 거기 있는지 파악하는 데 시간이 걸린다. 더 나쁜 건, 수정되지 않은 컨슈머로 재처리를 돌려서 같은 메시지가 다시 DLQ로 돌아오는 상황이다. 이 문서는 분류부터 자동화까지 실제 운영에 쓸 수 있는 수준으로 정리한다.

## DLQ 메시지 분류

DLQ에 들어온 메시지를 묻지도 따지지도 않고 전부 재처리하면 대부분 다시 DLQ로 돌아온다. 재처리 전에 원인을 분류하는 게 먼저다.

### 일시적 에러

컨슈머나 외부 의존성이 잠깐 불안정한 상황에서 발생한 실패다. 근본 원인이 해결되면 같은 메시지를 다시 처리했을 때 성공한다.

DB 연결 오류, 커넥션 풀 고갈, 외부 API 타임아웃이나 5xx 응답, 네트워크 단절이 여기에 해당한다. 배포 직후 연결이 초기화되기 전에 들어온 메시지가 실패하는 케이스도 흔하다. 이 유형은 배포 완료 확인 후 자동 재처리 파이프라인의 대상이 된다.

### 영구 에러

메시지 내용 자체에 문제가 있거나 비즈니스 규칙을 위반한 경우다. 컨슈머가 정상이어도 처리할 수 없다.

참조하는 주문 ID나 사용자 ID가 DB에서 이미 삭제된 경우, 환불 금액이 결제 금액을 초과하는 비즈니스 규칙 위반, 유효 기간이 지난 메시지(10분 안에 처리해야 하는데 1시간이 지남)가 여기에 해당한다. 자동 재처리 대상이 아니다. Parking Lot으로 이관 후 수동 검토한다.

### Poison Message

컨슈머가 역직렬화나 파싱 단계에서 예외를 던지는 메시지다. 재처리해도 즉시 다시 실패한다.

JSON 형식 오류, 스키마 버전 불일치, null 필드를 참조하는 역직렬화 로직이 원인이다. 프로듀서 쪽 코드가 변경되면서 기존 스키마와 호환되지 않는 메시지가 발행됐을 때 이런 일이 생긴다. 컨슈머 코드를 수정하지 않는 한 Parking Lot에서 대기한다.

### 분류 로직 구현

에러 타입을 컨슈머 레벨에서 태깅해서 DLQ 메시지 헤더나 속성으로 함께 저장해야 한다. 나중에 재처리할 때 분류 기준이 된다.

```typescript
type DlqErrorType = 'TRANSIENT' | 'PERMANENT' | 'POISON';

function classifyError(error: Error): DlqErrorType {
  if (error instanceof SyntaxError || error instanceof DeserializationError) {
    return 'POISON';
  }
  if (error instanceof NotFoundError || error instanceof BusinessRuleError) {
    return 'PERMANENT';
  }
  return 'TRANSIENT';
}

// SQS 메시지 속성으로 태깅
async function sendToDlq(
  originalMessage: SQSMessage,
  error: Error,
  dlqUrl: string
) {
  const errorType = classifyError(error);
  await sqs.send(new SendMessageCommand({
    QueueUrl: dlqUrl,
    MessageBody: originalMessage.Body ?? '',
    MessageAttributes: {
      'x-error-type': { DataType: 'String', StringValue: errorType },
      'x-error-message': { DataType: 'String', StringValue: error.message },
      'x-original-queue': { DataType: 'String', StringValue: SOURCE_QUEUE_URL }
    }
  }));
}
```

Kafka는 헤더로, RabbitMQ는 `message.properties.headers`로 같은 정보를 넘긴다.

## 브로커별 재처리 자동화

### SQS — start-message-move-task

2023년부터 SQS가 지원하는 API다. DLQ에서 원본 큐로 메시지를 이동시키는 managed 작업을 생성한다. 콘솔에서 "Start DLQ redrive" 버튼과 같은 동작이지만 API를 쓰면 자동화할 수 있다.

```typescript
import { SQSClient, StartMessageMoveTaskCommand, ListMessageMoveTasksCommand } from '@aws-sdk/client-sqs';

const sqs = new SQSClient({ region: 'ap-northeast-2' });

async function redriveFromDlq(dlqArn: string, destinationArn?: string) {
  const command = new StartMessageMoveTaskCommand({
    SourceArn: dlqArn,
    DestinationArn: destinationArn, // 생략 시 원본 소스 큐로 자동 이동
    MaxNumberOfMessagesPerSecond: 10  // 낮게 시작하고 처리량 보면서 올린다
  });
  const result = await sqs.send(command);
  return result.TaskHandle;
}

// 태스크 진행 상황 확인
async function checkRedriveStatus(dlqArn: string) {
  const tasks = await sqs.send(new ListMessageMoveTasksCommand({ SourceArn: dlqArn }));
  return tasks.Results; // Status: 'RUNNING' | 'COMPLETED' | 'CANCELLING' | 'CANCELLED' | 'FAILED'
}
```

`MaxNumberOfMessagesPerSecond`를 높게 잡으면 컨슈머가 갑자기 대량 메시지를 받아서 DB 연결 풀이 고갈될 수 있다. 처음엔 5~10으로 시작하고 원본 큐의 소비 속도를 보면서 올린다.

TRANSIENT 메시지만 선별해서 재처리하려면 Lambda를 앞에 붙인다. DLQ 이벤트를 Lambda가 받아서 속성으로 분류한 뒤 원본 큐에 발행하고, PERMANENT·POISON은 Parking Lot으로 보내는 방식이다. `start-message-move-task`는 전체를 한꺼번에 이동시키기 때문에 필터링이 필요할 땐 이쪽을 쓴다.

### Kafka — DLT Consumer

Kafka에서 DLT(Dead Letter Topic)는 브로커 기능이 아니라 컨슈머 애플리케이션이 만드는 패턴이다. 재처리도 별도의 consumer group이 DLT를 소비해서 원본 토픽으로 다시 produce하는 방식이다.

```typescript
async function startDltReprocessor(
  dltTopic: string,
  originalTopic: string,
  kafka: Kafka
) {
  const consumer = kafka.consumer({ groupId: 'dlt-reprocessor' }); // 원본 group ID와 다르게
  const producer = kafka.producer({ idempotent: true });

  await consumer.connect();
  await producer.connect();
  await consumer.subscribe({ topic: dltTopic, fromBeginning: false });

  await consumer.run({
    eachMessage: async ({ message }) => {
      const errorType = message.headers?.['x-error-type']?.toString();

      if (errorType === 'PERMANENT' || errorType === 'POISON') {
        await producer.send({
          topic: 'parking-lot',
          messages: [{
            key: message.key,
            value: message.value,
            headers: {
              ...message.headers,
              'x-moved-from': Buffer.from(dltTopic),
              'x-moved-at': Buffer.from(Date.now().toString())
            }
          }]
        });
        return;
      }

      // TRANSIENT만 원본 토픽으로 재발행
      await producer.send({
        topic: originalTopic,
        messages: [{
          key: message.key,
          value: message.value,
          headers: {
            ...message.headers,
            'x-reprocessed-from': Buffer.from(dltTopic),
            'x-original-offset': Buffer.from(message.offset)
          }
        }]
      });
    }
  });
}
```

DLT consumer group ID를 원본과 다르게 잡는 게 중요하다. 같은 group ID를 쓰면 offset 관리가 섞인다. 원본 토픽으로 produce 완료 후 DLT offset을 커밋한다. produce 실패 시 DLT offset을 커밋하지 않으면 재시작 시 같은 메시지를 다시 시도한다.

### RabbitMQ — Shovel Plugin

RabbitMQ에서 DLQ의 메시지를 다른 큐로 이동시키는 방법 중 Shovel Plugin이 안정적이다. 브로커 레벨에서 직접 이동시키기 때문에 별도 컨슈머 코드를 짤 필요가 없다.

```bash
# Shovel Plugin 활성화
rabbitmq-plugins enable rabbitmq_shovel
rabbitmq-plugins enable rabbitmq_shovel_management
```

HTTP API로 DLQ → 원본 큐 이동 태스크를 동적으로 생성한다:

```bash
curl -u admin:password -X PUT \
  http://rabbitmq:15672/api/parameters/shovel/%2F/dlq-to-orders \
  -H "Content-Type: application/json" \
  -d '{
    "value": {
      "src-protocol": "amqp091",
      "src-uri": "amqp://localhost",
      "src-queue": "orders.dlq",
      "dest-protocol": "amqp091",
      "dest-uri": "amqp://localhost",
      "dest-queue": "orders",
      "src-delete-after": "queue-length",
      "src-prefetch-count": 10
    }
  }'
```

`src-delete-after: "queue-length"`가 핵심이다. Shovel 생성 시점의 DLQ 메시지 수만큼 이동 후 자동으로 종료한다. 이게 없으면 Shovel이 계속 살아 있으면서 새로 들어오는 DLQ 메시지까지 원본 큐로 보내버린다.

Shovel 제거는 DELETE로 한다:

```bash
curl -u admin:password -X DELETE \
  http://rabbitmq:15672/api/parameters/shovel/%2F/dlq-to-orders
```

직접 consumer를 짤 때는 `basic_get`으로 DLQ에서 꺼내서 원본 exchange로 publish하고 ack하는 방식을 쓴다. 이때 publish 성공 여부를 confirm 후 ack해야 한다. publish가 실패한 상태에서 ack하면 메시지가 사라진다.

## Parking Lot 자동 이관 배치

DLQ에서 오래 방치된 메시지를 Parking Lot으로 옮기는 배치다. 10분 이상 DLQ에 있는 메시지는 일시적 에러가 아닐 가능성이 높다. 수동 검토가 필요한 메시지를 Parking Lot으로 격리하면 DLQ에 남은 것들만 재처리 대상으로 관리할 수 있다.

```typescript
async function evacuateStaleDlqMessages(
  dlqUrl: string,
  parkingLotUrl: string,
  maxAgeMinutes: number = 10
) {
  const maxAgeMs = maxAgeMinutes * 60 * 1000;
  const now = Date.now();
  let moved = 0;

  while (true) {
    const { Messages } = await sqs.send(new ReceiveMessageCommand({
      QueueUrl: dlqUrl,
      MaxNumberOfMessages: 10,
      MessageAttributeNames: ['All'],
      AttributeNames: ['SentTimestamp']
    }));

    if (!Messages?.length) break;

    for (const msg of Messages) {
      const sentAt = Number(msg.Attributes?.SentTimestamp ?? 0);
      const ageMs = now - sentAt;
      const errorType = msg.MessageAttributes?.['x-error-type']?.StringValue;
      const isOld = ageMs > maxAgeMs;
      const isPermanentOrPoison = errorType === 'PERMANENT' || errorType === 'POISON';

      if (!isOld && !isPermanentOrPoison) {
        continue; // 아직 재처리 대상
      }

      await sqs.send(new SendMessageCommand({
        QueueUrl: parkingLotUrl,
        MessageBody: msg.Body ?? '',
        MessageAttributes: {
          ...msg.MessageAttributes,
          'x-moved-from-dlq': { DataType: 'String', StringValue: dlqUrl },
          'x-dlq-age-minutes': {
            DataType: 'Number',
            StringValue: String(Math.floor(ageMs / 60000))
          }
        }
      }));

      await sqs.send(new DeleteMessageCommand({
        QueueUrl: dlqUrl,
        ReceiptHandle: msg.ReceiptHandle!
      }));

      moved++;
    }
  }

  return moved;
}
```

`SendMessage` 성공 후 `DeleteMessage`가 실패하면 메시지가 DLQ와 Parking Lot 양쪽에 존재하게 된다. Parking Lot 컨슈머가 멱등하게 구현돼 있어야 이 상황이 문제가 되지 않는다.

이 배치는 5~10분 간격으로 실행하면 충분하다. 너무 자주 돌리면 SQS API 호출 비용이 쌓인다. Parking Lot의 retention은 DLQ보다 길게 잡는다. DLQ가 7일이면 Parking Lot은 30일 이상으로 설정해서 검토 시간을 확보한다.

## 재처리 전 컨슈머 버전 확인

DLQ 재처리를 시작하기 전에 원본 큐의 컨슈머가 문제를 일으킨 버그가 수정된 버전인지 확인해야 한다. 수정되지 않은 상태에서 재처리하면 같은 메시지가 다시 DLQ로 돌아온다. 이걸 놓치고 재처리를 돌리는 실수가 생각보다 자주 발생한다.

자동화 파이프라인에 확인 단계를 강제로 넣는 게 현실적이다.

```typescript
interface DlqContext {
  failedSinceVersion: string;  // 이 버전 이후 메시지가 DLQ로 가기 시작
  failureReason: string;
  createdAt: Date;
}

async function assertConsumerFixed(
  consumerDeploymentName: string,
  dlqContext: DlqContext
): Promise<void> {
  const currentImage = await getDeployedImageTag(consumerDeploymentName);
  const currentVersion = extractVersionFromImage(currentImage);

  const [curMajor, curMinor, curPatch] = currentVersion.split('.').map(Number);
  const [reqMajor, reqMinor, reqPatch] = dlqContext.failedSinceVersion.split('.').map(Number);

  const isSameOrOlder =
    curMajor < reqMajor ||
    (curMajor === reqMajor && curMinor < reqMinor) ||
    (curMajor === reqMajor && curMinor === reqMinor && curPatch <= reqPatch);

  if (isSameOrOlder) {
    throw new Error(
      `Consumer ${consumerDeploymentName} is v${currentVersion}. ` +
      `DLQ started filling at v${dlqContext.failedSinceVersion}: ${dlqContext.failureReason}. ` +
      `Deploy a fix before redriving.`
    );
  }
}
```

버전 추적을 자동화하기 어려운 환경이면 재처리 스크립트에 확인 프롬프트를 넣는다:

```bash
#!/bin/bash
set -e

echo "DLQ: $DLQ_URL"
echo "현재 컨슈머 이미지:"
kubectl get deployment order-consumer \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""
echo "DLQ가 쌓이기 시작한 시점의 장애 내용:"
echo "$FAILURE_REASON"
echo ""
read -p "해당 버그가 현재 버전에서 수정됐는지 확인했습니까? (yes/no): " confirmed
if [ "$confirmed" != "yes" ]; then
  echo "재처리를 중단합니다."
  exit 1
fi
```

자동화 여부와 상관없이 재처리 전에 DLQ의 메시지 몇 개를 꺼내서 payload를 직접 눈으로 확인하는 습관을 들이는 게 좋다. 예상과 다른 패턴이 보이면 재처리 전에 원인을 다시 파악해야 한다.

## DLQ 모니터링 알람

알람 없는 DLQ는 블랙홀이다. 메시지가 쌓여도 아무도 모른다. 최소 두 가지 알람을 걸어야 한다.

**메시지 수 > 0**: DLQ에 메시지 하나라도 들어오면 즉시 알람을 받는다. 운영 초기에는 자주 울릴 수 있지만 DLQ에 메시지가 있다는 것 자체가 조사가 필요한 상태다.

**메시지 최고 나이 > 10분**: 메시지가 10분 이상 DLQ에 방치됐다면 일시적 에러가 아니다. 이 알람이 오면 Parking Lot 이관이나 수동 검토가 필요하다.

AWS CloudWatch에서 SQS DLQ 알람을 설정하면:

```typescript
async function createDlqAlarms(dlqName: string, snsTopicArn: string) {
  const cw = new CloudWatchClient({ region: 'ap-northeast-2' });

  await cw.send(new PutMetricAlarmCommand({
    AlarmName: `${dlqName}-has-messages`,
    Namespace: 'AWS/SQS',
    MetricName: 'ApproximateNumberOfMessagesVisible',
    Dimensions: [{ Name: 'QueueName', Value: dlqName }],
    Statistic: 'Sum',
    Period: 60,
    EvaluationPeriods: 1,
    Threshold: 0,
    ComparisonOperator: 'GreaterThanThreshold',
    AlarmActions: [snsTopicArn],
    TreatMissingData: 'notBreaching'
  }));

  await cw.send(new PutMetricAlarmCommand({
    AlarmName: `${dlqName}-age-over-10min`,
    Namespace: 'AWS/SQS',
    MetricName: 'ApproximateAgeOfOldestMessage',
    Dimensions: [{ Name: 'QueueName', Value: dlqName }],
    Statistic: 'Maximum',
    Period: 60,
    EvaluationPeriods: 1,
    Threshold: 600,
    ComparisonOperator: 'GreaterThanOrEqualToThreshold',
    AlarmActions: [snsTopicArn],
    TreatMissingData: 'notBreaching'
  }));
}
```

Kafka DLT는 consumer lag 메트릭으로 알람을 건다. Prometheus + kafka-exporter 조합이라면:

```yaml
groups:
  - name: dlq
    rules:
      - alert: KafkaDltHasMessages
        expr: kafka_consumer_group_lag{topic=~".*\\.DLT"} > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "DLT {{ $labels.topic }}에 미처리 메시지 {{ $value }}개"

      - alert: KafkaDltMessageStale
        expr: >
          (time() - kafka_topic_partition_latest_offset_time{topic=~".*\\.DLT"}) > 600
          and kafka_consumer_group_lag{topic=~".*\\.DLT"} > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "DLT {{ $labels.topic }} 메시지 10분 이상 미처리"
```

RabbitMQ는 `rabbitmq_prometheus` 플러그인을 활성화하면 `rabbitmq_queue_messages` 메트릭으로 DLQ 메시지 수를 수집할 수 있다. 최고 나이는 Management API의 `/api/queues/{vhost}/{name}` 엔드포인트의 `message_stats` 필드에서 가져온다.

DLQ 알람의 알림 대상을 팀 전체 슬랙 채널로 설정하는 게 좋다. 특정 개인에게만 오면 휴가 중이거나 부재 시 놓친다.

## 재처리 중 멱등 처리 연계

DLQ에서 원본 큐로 메시지를 되돌리면 컨슈머는 같은 메시지를 두 번 이상 받게 된다. 첫 번째 실패가 처리 도중에 일어났다면 일부 사이드이펙트가 이미 DB에 반영됐을 수 있다.

멱등 처리의 핵심은 같은 메시지 ID로 같은 작업을 두 번 실행해도 결과가 한 번 실행한 것과 같아야 한다는 점이다.

```typescript
async function processMessageIdempotently(
  messageId: string,
  db: Database,
  process: () => Promise<void>
): Promise<void> {
  // UPSERT로 레이스 컨디션 방지
  const result = await db.query<{ status: string }>(`
    INSERT INTO processed_messages (message_id, status, processed_at)
    VALUES ($1, 'processing', NOW())
    ON CONFLICT (message_id) DO UPDATE
      SET status = CASE
        WHEN processed_messages.status = 'completed' THEN 'completed'
        ELSE 'processing'
      END,
      processed_at = NOW()
    RETURNING status
  `, [messageId]);

  if (result.rows[0].status === 'completed') {
    return; // 이미 처리됨 — 중복 수신
  }

  try {
    await db.transaction(async (trx) => {
      await process(); // 실제 비즈니스 로직
      await trx.query(
        'UPDATE processed_messages SET status = $1 WHERE message_id = $2',
        ['completed', messageId]
      );
    });
  } catch (error) {
    await db.query(
      'UPDATE processed_messages SET status = $1, error = $2 WHERE message_id = $3',
      ['failed', String(error), messageId]
    );
    throw error;
  }
}
```

메시지 ID를 뭘로 쓸지는 브로커마다 다르다.

SQS 표준 큐는 `MessageId` 속성(브로커 자동 생성)을 쓴다. FIFO 큐에서는 프로듀서가 설정한 `MessageDeduplicationId`가 더 명확하다. Kafka는 `topic + partition + offset` 조합이 고유하다. DLT에서 재처리할 때 원본 offset을 헤더로 넘겨두면 중복 확인이 쉽다. RabbitMQ는 프로듀서가 `messageId` 속성을 직접 설정해야 한다. 브로커가 자동 생성하지 않아서 빠뜨리는 경우가 많다.

```typescript
function extractMessageId(msg: ConsumedMessage): string {
  switch (msg.broker) {
    case 'sqs':
      return msg.MessageAttributes?.['MessageDeduplicationId']?.StringValue
        ?? msg.MessageId;
    case 'kafka':
      // DLT에서 재처리 시 원본 식별자 사용
      const originalTopic = msg.headers?.['x-original-topic']?.toString();
      const originalOffset = msg.headers?.['x-original-offset']?.toString();
      if (originalTopic && originalOffset) {
        return `${originalTopic}-${msg.partition}-${originalOffset}`;
      }
      return `${msg.topic}-${msg.partition}-${msg.offset}`;
    case 'rabbitmq':
      if (!msg.properties.messageId) {
        throw new Error('RabbitMQ message is missing messageId property');
      }
      return msg.properties.messageId;
  }
}
```

`processed_messages` 테이블의 `message_id`에는 유니크 인덱스가 있어야 한다. 처리량이 많으면 이 테이블이 빠르게 커지므로 30일 이상 지난 `completed` 레코드를 정기적으로 삭제하는 배치도 함께 운영한다.
