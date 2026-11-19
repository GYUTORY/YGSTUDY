---
title: AWS Step Functions
tags: [aws, architecture, cloud]
updated: 2026-11-19
description: "AWS Step Functions로 Lambda 함수들을 연결해 워크플로우를 설계하는 방법"
---

# AWS Step Functions

## 개요

Step Functions는 여러 AWS 서비스를 연결해서 워크플로우를 만드는 서비스다. Lambda 함수들을 순서대로 실행하고, 조건에 따라 분기하고, 에러를 처리할 수 있다. 코드 없이 시각적으로 워크플로우를 설계한다.

### 왜 필요한가

Lambda 함수를 여러 개 연결해야 하는 경우가 있다.

주문 처리 시스템을 예로 든다. 단계는 다섯 개다.

1. 주문 검증
2. 재고 확인
3. 결제 처리
4. 배송 요청
5. 알림 발송

각 단계를 Lambda 함수로 만든다. 어떻게 연결할까?

방법 1은 Lambda에서 다음 Lambda를 직접 호출하는 방식이다.

```javascript
// orderValidator.js
exports.handler = async (event) => {
  // 주문 검증
  const order = validateOrder(event);
  
  // 다음 Lambda 호출
  await lambda.invoke({
    FunctionName: 'checkInventory',
    Payload: JSON.stringify(order)
  }).promise();
};
```

이 방식에는 문제가 있다.

- Lambda 코드에 워크플로우 로직이 섞인다
- 순서를 바꾸려면 코드를 수정해야 한다
- 에러 처리가 복잡하다
- 전체 흐름을 파악하기 어렵다
- 각 Lambda가 다음 Lambda를 알아야 한다 (결합도 높음)

방법 2는 SQS로 단계를 연결하는 방식이다.

```javascript
// orderValidator.js
exports.handler = async (event) => {
  const order = validateOrder(event);
  
  // SQS에 메시지 전송
  await sqs.sendMessage({
    QueueUrl: inventoryQueueUrl,
    MessageBody: JSON.stringify(order)
  }).promise();
};
```

이 방식에도 문제가 있다.

- 순서 보장이 어렵다
- 에러 시 어디서부터 재시도할지 모호하다
- 조건부 분기가 어렵다
- 전체 진행 상황을 추적하기 어렵다

Step Functions에서는 워크플로우를 JSON으로 정의한다. 단계 순서는 `Next`로 이어진다.

```json
{
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:validateOrder",
      "Next": "CheckInventory"
    },
    "CheckInventory": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:checkInventory",
      "Next": "ProcessPayment"
    },
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:processPayment",
      "Next": "RequestShipping"
    }
  }
}
```

Step Functions로 옮기면 이 점이 달라진다.

- 워크플로우가 코드에서 분리된다
- 시각적으로 확인할 수 있다
- 순서 변경이 쉽다
- 에러 처리가 명확하다
- 진행 상황을 실시간으로 볼 수 있다

### 주요 특징

State Machine을 그래프로 보여준다. 각 단계와 연결을 한눈에 파악한다.

Lambda 실행이 실패하면 자동으로 재시도한다. 재시도 횟수와 간격을 설정한다.

에러가 발생하면 특정 단계로 이동한다. 롤백이나 보상 트랜잭션을 실행한다.

여러 Lambda를 동시에 실행한다. 모든 Lambda가 완료될 때까지 기다린다.

일정 시간 동안 대기한다. 외부 작업이 완료될 때까지 기다린다.

Lambda 외에 DynamoDB, SNS, SQS, ECS 같은 AWS 서비스도 호출한다.

## State Machine

State Machine은 워크플로우를 정의한 것이다. 여러 State(상태)로 구성된다.

### State 종류

Task State는 실제 작업을 수행한다. Lambda 함수를 호출하거나 AWS 서비스를 실행한다.

```json
{
  "ValidateOrder": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:region:account:function:validateOrder",
    "Next": "CheckInventory"
  }
}
```

Choice State는 조건에 따라 분기한다. if-else 문과 같다.

```json
{
  "CheckInventory": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.inventory",
        "NumericGreaterThan": 0,
        "Next": "ProcessPayment"
      },
      {
        "Variable": "$.inventory",
        "NumericEquals": 0,
        "Next": "OutOfStock"
      }
    ],
    "Default": "Failed"
  }
}
```

재고가 있으면 결제로 진행하고, 없으면 재고 부족 처리를 한다.

Parallel State는 여러 작업을 동시에 실행한다.

```json
{
  "NotifyAll": {
    "Type": "Parallel",
    "Branches": [
      {
        "StartAt": "SendEmail",
        "States": {
          "SendEmail": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:...:sendEmail",
            "End": true
          }
        }
      },
      {
        "StartAt": "SendSMS",
        "States": {
          "SendSMS": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:...:sendSMS",
            "End": true
          }
        }
      }
    ],
    "Next": "Done"
  }
}
```

이메일과 SMS를 동시에 보낸다. 둘 다 완료되면 다음 단계로 진행한다.

Wait State는 일정 시간 동안 대기한다.

```json
{
  "WaitForApproval": {
    "Type": "Wait",
    "Seconds": 300,
    "Next": "CheckApprovalStatus"
  }
}
```

5분 동안 기다린 후 승인 상태를 확인한다.

Pass State는 입력을 그대로 출력으로 전달한다. 테스트나 데이터 변환에 사용한다.

```json
{
  "AddTimestamp": {
    "Type": "Pass",
    "Result": {
      "timestamp": "2026-01-18T10:00:00Z"
    },
    "ResultPath": "$.metadata",
    "Next": "ProcessData"
  }
}
```

Succeed State는 워크플로우를 성공으로 종료한다.

```json
{
  "OrderCompleted": {
    "Type": "Succeed"
  }
}
```

Fail State는 워크플로우를 실패로 종료한다.

```json
{
  "OrderFailed": {
    "Type": "Fail",
    "Error": "ValidationError",
    "Cause": "Invalid order data"
  }
}
```

## 상태 머신 실패 복구 및 재시도 전략
Lambda 실행이 실패하거나 타임아웃이 발생할 수 있다. 에러 처리가 중요하다.

### Retry (재시도)

자동으로 재시도한다. 일시적인 에러를 처리한다.

```json
{
  "ProcessPayment": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:region:account:function:processPayment",
    "Retry": [
      {
        "ErrorEquals": ["TimeoutError", "NetworkError"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }
    ],
    "Next": "RequestShipping"
  }
}
```

재시도는 이 순서로 진행된다.

1. 첫 시도 실패
2. 2초 대기 후 재시도
3. 실패하면 4초 대기 (2 × 2.0)
4. 실패하면 8초 대기 (4 × 2.0)
5. 3회 재시도 후에도 실패하면 에러

BackoffRate는 재시도 간격을 점점 늘린다. 서버 부하를 줄인다.

### Catch (에러 잡기)

재시도해도 실패하면 에러를 잡아서 처리한다.

```json
{
  "ProcessPayment": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:region:account:function:processPayment",
    "Retry": [
      {
        "ErrorEquals": ["TimeoutError"],
        "MaxAttempts": 3
      }
    ],
    "Catch": [
      {
        "ErrorEquals": ["PaymentDeclined"],
        "Next": "PaymentFailedNotification"
      },
      {
        "ErrorEquals": ["States.ALL"],
        "Next": "GeneralErrorHandler"
      }
    ],
    "Next": "RequestShipping"
  }
}
```

Catch는 에러 종류에 따라 갈라진다.

- 결제 거부 에러: 고객에게 알림
- 그 외 모든 에러: 일반 에러 처리

ErrorEquals에 쓸 수 있는 에러 타입은 다섯 가지다.

- **States.Timeout**: 타임아웃
- **States.TaskFailed**: Task 실패
- **States.Permissions**: 권한 부족
- **States.ALL**: 모든 에러
- **CustomError**: Lambda에서 던진 커스텀 에러

Lambda에서 에러를 던지는 코드는 이렇다.

```javascript
exports.handler = async (event) => {
  const payment = await processPayment(event);
  
  if (payment.status === 'declined') {
    throw new Error('PaymentDeclined');
  }
  
  return payment;
};
```

Step Functions가 에러를 잡아서 처리한다.

## 입력과 출력

각 State는 입력을 받아서 출력을 생성한다. 다음 State로 전달된다.

### InputPath

입력 데이터의 일부만 선택한다.

```json
{
  "ProcessOrder": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...",
    "InputPath": "$.order",
    "Next": "Done"
  }
}
```

입력 데이터가 이렇다고 하자.

```json
{
  "order": {
    "orderId": "123",
    "amount": 100
  },
  "metadata": {
    "timestamp": "2026-01-18"
  }
}
```

이때 Lambda에 전달되는 데이터는 이렇다.

```json
{
  "orderId": "123",
  "amount": 100
}
```

`$.order`만 Lambda에 전달된다.

### OutputPath

출력 데이터의 일부만 선택한다.

```json
{
  "ProcessOrder": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...",
    "OutputPath": "$.result",
    "Next": "Done"
  }
}
```

Lambda가 이런 값을 반환한다고 하자.

```json
{
  "result": {
    "status": "success",
    "orderId": "123"
  },
  "debug": {
    "executionTime": 100
  }
}
```

다음 State로 전달되는 데이터는 이렇다.

```json
{
  "status": "success",
  "orderId": "123"
}
```

`$.result`만 다음 State로 전달된다.

### ResultPath

Lambda 출력을 입력 데이터에 추가한다.

```json
{
  "ProcessOrder": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...",
    "ResultPath": "$.paymentResult",
    "Next": "Done"
  }
}
```

입력이 이렇다고 하자.

```json
{
  "orderId": "123",
  "amount": 100
}
```

Lambda 반환값은 이렇다.

```json
{
  "status": "success",
  "transactionId": "txn_456"
}
```

다음 State로 전달되는 데이터는 이렇다.

```json
{
  "orderId": "123",
  "amount": 100,
  "paymentResult": {
    "status": "success",
    "transactionId": "txn_456"
  }
}
```

원본 데이터가 유지되고 Lambda 결과가 추가된다.

`ResultPath: null`이면 Lambda 결과를 버리고 입력을 그대로 전달한다.

```json
{
  "LogActivity": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:logActivity",
    "ResultPath": null,
    "Next": "ProcessOrder"
  }
}
```

로그만 남기고 데이터는 변경하지 않는다.

## 실무 예제

### 주문 처리 워크플로우

요구사항은 여섯 가지다.

1. 주문 검증
2. 재고 확인
3. 재고가 있으면 결제 처리
4. 재고가 없으면 재고 부족 알림
5. 결제 성공하면 배송 요청
6. 결제 실패하면 고객에게 알림

전체 State Machine 정의다.

```json
{
  "Comment": "주문 처리 워크플로우",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "validateOrder",
        "Payload.$": "$"
      },
      "ResultPath": "$.validation",
      "Next": "CheckInventory",
      "Catch": [
        {
          "ErrorEquals": ["ValidationError"],
          "Next": "OrderInvalid"
        }
      ]
    },
    "CheckInventory": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "checkInventory",
        "Payload.$": "$"
      },
      "ResultPath": "$.inventory",
      "Next": "HasInventory"
    },
    "HasInventory": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.inventory.Payload.available",
          "BooleanEquals": true,
          "Next": "ProcessPayment"
        }
      ],
      "Default": "OutOfStock"
    },
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "processPayment",
        "Payload.$": "$"
      },
      "ResultPath": "$.payment",
      "Retry": [
        {
          "ErrorEquals": ["TimeoutError", "NetworkError"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["PaymentDeclined"],
          "Next": "PaymentFailed"
        }
      ],
      "Next": "RequestShipping"
    },
    "RequestShipping": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "requestShipping",
        "Payload.$": "$"
      },
      "ResultPath": "$.shipping",
      "Next": "OrderSuccess"
    },
    "OutOfStock": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:region:account:out-of-stock",
        "Message.$": "$.orderId"
      },
      "Next": "OrderFailed"
    },
    "PaymentFailed": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:region:account:payment-failed",
        "Message": {
          "orderId.$": "$.orderId",
          "reason": "Payment declined"
        }
      },
      "Next": "OrderFailed"
    },
    "OrderInvalid": {
      "Type": "Fail",
      "Error": "ValidationError",
      "Cause": "Order validation failed"
    },
    "OrderSuccess": {
      "Type": "Succeed"
    },
    "OrderFailed": {
      "Type": "Fail",
      "Error": "OrderProcessingError",
      "Cause": "Order processing failed"
    }
  }
}
```

실행 흐름은 이렇다.

1. `ValidateOrder`: 주문 검증. 실패하면 `OrderInvalid`
2. `CheckInventory`: 재고 확인
3. `HasInventory`: 재고 여부 체크
   - 재고 있음: `ProcessPayment`
   - 재고 없음: `OutOfStock`
4. `ProcessPayment`: 결제 처리. 실패하면 재시도. 재시도 실패하면 `PaymentFailed`
5. `RequestShipping`: 배송 요청
6. `OrderSuccess`: 성공 종료

### 병렬 처리 예제

여러 작업을 동시에 실행한다.

주문 완료 후 여러 알림을 동시에 보낸다.

- 고객에게 이메일
- 고객에게 SMS
- 재고 시스템에 알림
- 분석 시스템에 로그

State Machine 정의는 이렇다.

```json
{
  "NotifyAll": {
    "Type": "Parallel",
    "Branches": [
      {
        "StartAt": "SendEmail",
        "States": {
          "SendEmail": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "sendEmail",
              "Payload.$": "$"
            },
            "End": true
          }
        }
      },
      {
        "StartAt": "SendSMS",
        "States": {
          "SendSMS": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "sendSMS",
              "Payload.$": "$"
            },
            "End": true
          }
        }
      },
      {
        "StartAt": "NotifyInventory",
        "States": {
          "NotifyInventory": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "notifyInventory",
              "Payload.$": "$"
            },
            "End": true
          }
        }
      },
      {
        "StartAt": "LogAnalytics",
        "States": {
          "LogAnalytics": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "logAnalytics",
              "Payload.$": "$"
            },
            "End": true
          }
        }
      }
    ],
    "Next": "Done"
  }
}
```

4개 작업이 동시에 실행된다. 모두 완료되면 `Done`으로 진행한다.

하나라도 실패하면 전체가 실패한다. 각 Branch에 에러 처리를 추가해야 한다.

### 대기 및 폴링 예제

외부 작업이 완료될 때까지 기다린다.

배치 작업을 시작하고 완료될 때까지 주기적으로 상태를 확인한다.

State Machine 정의는 이렇다.

```json
{
  "StartBatchJob": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "startBatchJob",
      "Payload.$": "$"
    },
    "ResultPath": "$.jobId",
    "Next": "WaitForJob"
  },
  "WaitForJob": {
    "Type": "Wait",
    "Seconds": 30,
    "Next": "CheckJobStatus"
  },
  "CheckJobStatus": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "checkJobStatus",
      "Payload": {
        "jobId.$": "$.jobId.Payload.jobId"
      }
    },
    "ResultPath": "$.status",
    "Next": "IsJobComplete"
  },
  "IsJobComplete": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.status.Payload.status",
        "StringEquals": "COMPLETED",
        "Next": "JobSuccess"
      },
      {
        "Variable": "$.status.Payload.status",
        "StringEquals": "FAILED",
        "Next": "JobFailed"
      }
    ],
    "Default": "WaitForJob"
  },
  "JobSuccess": {
    "Type": "Succeed"
  },
  "JobFailed": {
    "Type": "Fail",
    "Error": "BatchJobFailed",
    "Cause": "Batch job execution failed"
  }
}
```

실행 흐름은 이렇다.

1. 배치 작업 시작
2. 30초 대기
3. 상태 확인
4. 완료되면 성공, 실패하면 실패, 진행 중이면 2번으로 돌아간다

30초마다 상태를 확인한다. 완료될 때까지 반복한다.

## Standard vs Express

Step Functions에는 두 가지 타입이 있다.

### Standard Workflow

Standard Workflow의 특징이다.

- 최대 실행 시간: 1년
- 실행 히스토리 저장
- Exactly-once 실행 보장
- 높은 안정성

이런 경우에 쓴다.

- 장기 실행 워크플로우
- 정확한 실행 보장 필요
- 감사 로그 필요
- 주문 처리, 승인 프로세스

가격 체계는 이렇다.

- State 전환당 과금
- 1,000 State 전환: $0.025

### Express Workflow

Express Workflow의 특징이다.

- 최대 실행 시간: 5분
- 실행 히스토리 선택적
- At-least-once 실행
- 높은 처리량

이런 경우에 쓴다.

- 짧은 실행 시간
- 높은 처리량 필요
- IoT 데이터 처리
- 스트리밍 데이터 변환

가격 체계는 이렇다.

- 실행 횟수와 시간 기반
- 1,000 실행 (1초): $0.001

훨씬 저렴하다. 하지만 실행 시간이 5분으로 제한된다.

## 모니터링

### CloudWatch Logs

Step Functions 실행 로그를 CloudWatch에 저장한다.

로그 설정 예시다.

```json
{
  "loggingConfiguration": {
    "level": "ALL",
    "includeExecutionData": true,
    "destinations": [
      {
        "cloudWatchLogsLogGroup": {
          "logGroupArn": "arn:aws:logs:region:account:log-group:/aws/stepfunctions/order-processing"
        }
      }
    ]
  }
}
```

로그 레벨은 네 가지다.

- **ALL**: 모든 이벤트
- **ERROR**: 에러만
- **FATAL**: 치명적 에러만
- **OFF**: 로그 없음

### CloudWatch Metrics

자동으로 메트릭을 수집한다.

주로 보는 메트릭은 이렇다.

- **ExecutionsStarted**: 시작된 실행 수
- **ExecutionsSucceeded**: 성공한 실행 수
- **ExecutionsFailed**: 실패한 실행 수
- **ExecutionTime**: 평균 실행 시간

알람 설정 예시다.

```json
{
  "MetricName": "ExecutionsFailed",
  "Threshold": 10,
  "ComparisonOperator": "GreaterThanThreshold",
  "EvaluationPeriods": 1
}
```

실패한 실행이 10개를 넘으면 알림을 받는다.

### X-Ray 통합

X-Ray로 분산 추적을 할 수 있다.

State Machine 생성 시 X-Ray 추적을 활성화한다.

X-Ray에서 볼 수 있는 것은 이렇다.

- 각 State의 실행 시간
- Lambda 실행 시간
- AWS 서비스 호출 시간
- 에러 발생 위치

병목 구간을 찾는다. 최적화할 부분을 파악한다.

## 비용 최적화

### State 전환 줄이기

Standard Workflow는 State 전환마다 과금된다. 불필요한 State를 제거한다.

수정 전 정의다.

```json
{
  "State1": {
    "Type": "Pass",
    "Next": "State2"
  },
  "State2": {
    "Type": "Pass",
    "Next": "State3"
  },
  "State3": {
    "Type": "Task",
    "Resource": "...",
    "End": true
  }
}
```

3번의 State 전환이 발생한다.

수정 후 정의다.

```json
{
  "State3": {
    "Type": "Task",
    "Resource": "...",
    "End": true
  }
}
```

1번의 State 전환만 발생한다. 비용이 3분의 1로 줄어든다.

### Express Workflow 사용

짧은 워크플로우는 Express를 사용한다. 비용이 훨씬 저렴하다.

Standard로 돌리면 이렇다.

- 10,000 실행
- State 5개
- 총 50,000 State 전환
- 비용: $1.25

Express로 돌리면 이렇다.

- 10,000 실행
- 실행당 1초
- 비용: $0.01

125배 저렴하다.

### Lambda 함수 통합

여러 Lambda를 하나로 합친다. State 전환이 줄어든다.

수정 전 구성이다.

- State 1: Lambda A
- State 2: Lambda B
- State 3: Lambda C

3번의 State 전환과 3번의 Lambda 호출.

수정 후 구성이다.

- State 1: Lambda ABC (A, B, C를 순차 실행)

1번의 State 전환과 1번의 Lambda 호출.

단, Lambda 함수가 복잡해진다. 트레이드오프를 고려한다.

## 주의사항

### 최대 실행 시간

**Standard:** 1년
**Express:** 5분

5분을 초과하는 작업은 Standard를 사용한다.

### 입력/출력 크기

**최대 크기:** 256KB

큰 데이터는 S3에 저장하고 S3 키만 전달한다.

```javascript
// Bad
return {
  largeData: [...] // 1MB 데이터
};

// Good
await s3.putObject({
  Bucket: 'my-bucket',
  Key: 'data.json',
  Body: JSON.stringify(largeData)
});

return {
  s3Key: 'data.json'
};
```

### 실행 히스토리

Standard Workflow의 실행 히스토리는 90일 동안 저장된다. 이후 자동 삭제된다.

장기 보관이 필요하면 CloudWatch Logs에 저장한다.

### 동시 실행 제한

계정당 동시 실행 한도는 이렇다.

- Standard: 무제한
- Express: 100,000개 (증가 요청 가능)

대부분의 경우 충분하다.

## 참고

- AWS Step Functions 개발자 가이드: https://docs.aws.amazon.com/step-functions/
- State Machine 언어 명세: https://states-language.net/spec.html
- Step Functions 요금: https://aws.amazon.com/step-functions/pricing/
- 워크플로우 스튜디오: https://aws.amazon.com/step-functions/getting-started/

