---
title: AWS CloudWatch 로그 분석 및 실시간 모니터링
tags: [aws, cloudwatch, monitoring, logs, observability]
updated: 2026-04-26
---

# AWS CloudWatch Logs 실무 운영

CloudWatch는 AWS에서 로그·메트릭을 다루는 기본 창구다. 단순히 "로그 모이는 곳" 정도로 다루다가 청구서를 보고 놀라거나, 장애 한가운데서 쿼리가 타임아웃 나서 더 큰 사고로 번지는 경우가 흔하다. 이 문서는 운영 중 자주 부딪히는 함정 위주로 정리한다.

---

## 1. Log Group 명명과 retention — 첫 단추가 비용을 결정한다

CloudWatch Logs는 **수집(ingest) GB**, **저장(storage) GB-월**, **Logs Insights 스캔량 GB**, 세 항목으로 청구된다. 가장 자주 터지는 사고가 retention을 설정하지 않은 채 운영을 시작하는 경우다. 기본값은 **Never expire**이고, 이 상태로 6개월을 넘기면 저장 비용이 수집 비용을 추월한다. 한 팀에서 1년 넘게 방치된 `/aws/lambda/*` 로그가 4TB까지 쌓여 매월 100달러가 그대로 새는 사례를 봤다. Lambda 로그는 자동 생성되기 때문에 Terraform으로 인프라를 관리해도 retention이 누락되기 쉽다.

### Log Group 명명 규칙

규칙 없이 만들면 나중에 권한을 주거나 Subscription Filter를 걸 때 와일드카드가 안 먹는 상황이 생긴다. 운영 환경에서 자주 쓰는 컨벤션은 다음과 같다.

```
/aws/lambda/{function-name}              # AWS가 자동 생성
/aws/ecs/{cluster}/{service}             # 직접 생성
/aws/apigateway/{api-id}/{stage}         # API Gateway 액세스 로그
/aws/vpc/flowlogs/{vpc-id}               # VPC Flow Logs
/{env}/{team}/{service}/{component}      # 사내 컨벤션 예시
```

`/{env}/...` 형태로 환경을 prefix에 두면 IAM 정책에서 `Resource: "arn:aws:logs:*:*:log-group:/prod/*"` 같은 한 줄로 권한을 끊을 수 있다. 환경을 suffix에 두면 와일드카드가 깨져서 정책이 길어진다.

### retention은 코드로 박아라

콘솔에서 일일이 클릭하면 누락된다. Lambda 자동 생성 로그 그룹까지 retention을 강제하려면 함수 배포 직후에 Log Group을 직접 생성·관리하거나, Config Rule이나 EventBridge로 보정하는 패턴을 쓴다.

```hcl
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.logs.arn
}

resource "aws_lambda_function" "app" {
  function_name = var.function_name
  # Log Group이 먼저 만들어져야 retention이 0(무제한)으로 떨어지지 않는다
  depends_on    = [aws_cloudwatch_log_group.lambda]
}
```

`depends_on`을 빼먹으면 Lambda가 먼저 호출되면서 AWS가 retention 무제한 상태로 Log Group을 자동 생성하고, 그 뒤에 Terraform이 `Already exists` 오류를 낸다.

저장이 길어야 하는 감사 로그(CloudTrail, ALB 액세스, VPC Flow)는 **30일만 CloudWatch에 두고 S3로 export**하는 패턴이 일반적이다. S3 Standard-IA 또는 Glacier Instant Retrieval에 두면 저장 비용이 1/10 수준으로 떨어진다.

---

## 2. 로그 수집 — Agent와 ECS 드라이버 선택

### EC2: CloudWatch Agent

레거시 awslogs 데몬은 deprecated로 보면 된다. 신규 구성은 **CloudWatch Agent** 단일화가 정답이다. Agent는 `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`에 설정을 두고 SSM Parameter Store에서 끌어올릴 수 있다.

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/*.log",
            "log_group_name": "/prod/orders/api",
            "log_stream_name": "{instance_id}/{ip_address}",
            "timezone": "UTC",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S",
            "multi_line_start_pattern": "^\\d{4}-\\d{2}-\\d{2}"
          }
        ]
      }
    },
    "force_flush_interval": 5
  }
}
```

`multi_line_start_pattern`을 빼먹으면 Java 스택트레이스가 줄별로 잘려서 Insights에서 검색이 무용지물이 된다. 운영 중 가장 흔한 실수다.

### ECS: awslogs vs awsfirelens

ECS Task Definition의 `logConfiguration.logDriver`는 두 가지를 자주 쓴다.

**awslogs 드라이버**는 가장 단순하다. ECS Agent가 Docker 표준 출력을 받아 CloudWatch Logs로 직접 보낸다. 설정이 짧고 안정적이지만, **로그 파싱·라우팅·필터링이 불가능**하다. 컨테이너에서 INFO/DEBUG가 섞여 나가는 그대로 들어간다.

```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/prod/orders/api",
      "awslogs-region": "ap-northeast-2",
      "awslogs-stream-prefix": "ecs",
      "awslogs-create-group": "true",
      "mode": "non-blocking",
      "max-buffer-size": "25m"
    }
  }
}
```

`mode: non-blocking`을 빼면 CloudWatch가 throttling 걸렸을 때 컨테이너 stdout 쓰기가 블록되면서 애플리케이션 응답 시간이 같이 무너진다. 한 번 겪으면 절대 안 잊는 함정이다. 25MB 버퍼가 차면 그제야 로그가 드롭된다.

**awsfirelens(FluentBit)** 는 사이드카로 FluentBit을 띄워서 라우팅·필터링·다중 destination을 지원한다. 다음 중 하나라도 해당되면 awsfirelens가 맞다.

- 동일 로그를 CloudWatch + S3 + OpenSearch로 동시에 보내야 함
- 컨테이너에서 나오는 INFO 이상만 CloudWatch에 보내고 나머지는 드롭
- 로그를 JSON으로 재가공 후 전송
- 멀티라인 처리(스택트레이스)가 필요

```json
{
  "containerDefinitions": [
    {
      "name": "log_router",
      "image": "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable",
      "firelensConfiguration": {
        "type": "fluentbit",
        "options": { "enable-ecs-log-metadata": "true" }
      }
    },
    {
      "name": "app",
      "image": "...",
      "logConfiguration": {
        "logDriver": "awsfirelens",
        "options": {
          "Name": "cloudwatch_logs",
          "region": "ap-northeast-2",
          "log_group_name": "/prod/orders/api",
          "log_stream_prefix": "fluentbit-",
          "auto_create_group": "false"
        }
      }
    }
  ]
}
```

awsfirelens의 함정은 **사이드카 컨테이너의 메모리 제한**이다. FluentBit에 256MB만 주면 트래픽 피크에 OOM으로 죽고, FluentBit이 죽으면 애플리케이션 stdout이 막혀 같이 죽는다. 최소 512MB, 가능하면 1GB를 잡고 시작한다.

---

## 3. Logs Insights 실무 쿼리

Insights는 SQL이 아니라 파이프 기반 쿼리 언어다. 익숙해지면 grep+awk보다 빠르지만, 문법 함정이 몇 가지 있다.

### parse로 비정형 로그에서 필드 뽑기

`parse`는 두 가지 모드가 있다. 글로브 패턴(`*`)과 정규식이다. 정규식 모드는 named capture group을 쓴다.

```
fields @timestamp, @message
| parse @message /(?<level>INFO|WARN|ERROR)\s+\[(?<traceId>[a-f0-9]+)\]\s+(?<msg>.*)/
| filter level = "ERROR"
| stats count(*) as cnt by bin(5m)
| sort @timestamp desc
```

`bin(5m)`은 시계열 집계의 핵심이다. `bin(1m)`, `bin(1h)` 처럼 단위를 바꿔서 분포를 본다. 알람을 만들기 전에 항상 `bin()`으로 분 단위 분포를 먼저 보고 임계값을 정해야 false positive를 줄일 수 있다.

### dedup으로 중복 제거

같은 trace ID가 여러 로그 라인에 찍힐 때 원본 trace 단위로 보고 싶으면 `dedup`을 쓴다.

```
fields @timestamp, traceId, status
| filter status >= 500
| parse @message /traceId=(?<traceId>\S+)/
| dedup traceId
| limit 100
```

`dedup`은 첫 번째 발견된 행만 남긴다. 정렬을 어떻게 했느냐에 따라 결과가 달라지므로 `sort @timestamp asc | dedup traceId` 처럼 원하는 시점을 명시한다.

### 스캔량과 타임아웃 — 장애 한가운데서 쿼리가 멈추는 이유

Insights는 **쿼리당 60GB 스캔 한도, 15분 타임아웃**이 있다. 장애 났을 때 "최근 24시간 ERROR 다 보여줘" 식으로 던지면 십중팔구 타임아웃이 나거나 비용이 튄다. 스캔량은 `@message` 자체가 아니라 **로그 그룹 전체**가 기준이다. 7일 동안 50GB가 쌓인 로그 그룹에서 15분 범위 쿼리를 돌리면 비례해서 약 1GB 정도만 스캔하지만, time range를 안 좁히면 50GB를 다 스캔한다.

장애 대응 중에는 다음 순서를 지킨다.

1. 시간 범위를 5~15분으로 먼저 좁힌다
2. `filter`를 가장 앞에 둬서 후속 파이프 연산의 데이터를 줄인다
3. `fields @timestamp, @message`만 먼저 띄우고 패턴 확인 후 `parse`를 추가한다
4. 같은 쿼리를 여러 사람이 동시에 돌리면 계정 단위 동시 쿼리 제한(기본 30개)에 걸린다 — 슬랙에 결과 URL 공유하는 습관 필요

쿼리 결과 페이지에 "Logs scanned: XXX MB"가 찍힌다. 이게 `$0.005/GB` 곱하기로 직결되니 매번 확인한다.

---

## 4. Metric Filter — 패턴 문법과 카디널리티 함정

Metric Filter는 Log Group에서 패턴이 매칭될 때 카운터를 1씩 올리는 식의 메트릭을 만든다. 문법이 두 가지다.

### 평문 패턴

공백이 OR이 아니라 AND다. `ERROR Database`는 한 라인에 `ERROR`와 `Database`가 모두 있어야 매칭된다. OR이 필요하면 `?ERROR ?WARN` 처럼 `?` 접두를 쓴다.

```
[ip, user, timestamp, request, status_code = 5*, size]
```

이런 비정형 토큰 파싱 문법도 있는데, 각 토큰을 공백 단위로 자르고 위치별로 이름·조건을 붙인다. `status_code = 5*`는 5xx만 잡는다. 숫자 비교는 `>`, `>=`, `=` 모두 된다.

### JSON 패턴

JSON 로그면 JSON 패턴이 훨씬 정확하다. `$.level = "ERROR"` 처럼 JSONPath를 쓴다.

```
{ $.level = "ERROR" && $.statusCode >= 500 }
```

문자열 매칭에는 `=`를, 부분 매칭에는 `=*`를 쓴다. `{ $.path = "/api/orders/*" }` 처럼 와일드카드를 끝에 붙이는 식이다. 정규식은 못 쓴다는 점을 항상 기억해야 한다. 복잡한 패턴은 Subscription Filter + Lambda로 가야 한다.

### 차원(dimension) 카디널리티 폭발

Metric Filter의 `metric_transformation`에 dimension을 추가할 수 있다. 예를 들어 status code별로 카운터를 분리하면 다음과 같다.

```hcl
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "api-errors-by-path"
  log_group_name = "/prod/orders/api"
  pattern        = "{ $.statusCode >= 500 }"

  metric_transformation {
    name       = "ApiServerErrors"
    namespace  = "Orders/Api"
    value      = "1"
    dimensions = {
      Path       = "$.path"
      StatusCode = "$.statusCode"
    }
  }
}
```

여기서 `Path`를 dimension에 넣으면 **고유한 path 조합마다 별도 메트릭**이 생긴다. `/api/orders/{orderId}` 같은 경로가 그대로 들어가면 주문 ID마다 메트릭 시리즈가 만들어져서 카디널리티가 수만~수백만으로 폭발한다. 커스텀 메트릭은 메트릭당 과금이고, dimension 조합 하나가 메트릭 하나로 친다. 청구서가 두 자릿수로 늘어난 사례를 직접 봤다.

원칙은 **dimension에는 닫힌 집합만 넣는다**. status code, region, environment, service name처럼 개수가 정해진 값만. path는 라우트 패턴(`/api/orders`)으로 정규화해서 애플리케이션이 이미 분류한 라벨을 로그에 찍어두고 그 필드를 dimension으로 쓴다.

---

## 5. Subscription Filter — 실시간 스트리밍

Metric Filter는 카운터까지가 한계다. 로그를 실시간으로 다른 시스템(OpenSearch, S3, 외부 SIEM)에 흘려보내려면 **Subscription Filter**를 건다. destination은 세 가지다.

- **Kinesis Data Streams**: 컨슈머 측에서 자유롭게 처리. 다중 컨슈머 지원
- **Kinesis Data Firehose**: S3·OpenSearch·Redshift로 자동 적재. 가장 흔한 패턴
- **Lambda**: 즉시 처리. 페이로드 작을 때

전형적인 구성은 `Log Group → Subscription Filter → Firehose → S3(원본) + OpenSearch(검색)`다. Firehose는 64KB 단위로 압축·배치하고 buffer interval 60초~900초를 설정한다. OpenSearch에는 인덱스 회전과 ISM 정책으로 자동 삭제까지 묶어둔다.

```hcl
resource "aws_cloudwatch_log_subscription_filter" "to_firehose" {
  name            = "orders-to-opensearch"
  log_group_name  = "/prod/orders/api"
  filter_pattern  = "{ $.level = \"ERROR\" || $.level = \"WARN\" }"
  destination_arn = aws_kinesis_firehose_delivery_stream.logs.arn
  role_arn        = aws_iam_role.cw_to_firehose.arn
}
```

함정은 **Subscription Filter는 Log Group당 2개 제한**이다. 이미 한 개를 OpenSearch로 쓰는데 SIEM도 붙이려면 Kinesis Streams를 한 번 거쳐서 fan-out 해야 한다. 또 CloudWatch가 Firehose로 보낼 때 페이로드는 **gzip 압축된 base64 인코딩 JSON 배열**이라서 컨슈머에서 한 번 풀어야 한다. Lambda destination이면 다음 형태의 이벤트가 온다.

```python
import base64, gzip, json

def lambda_handler(event, context):
    payload = base64.b64decode(event["awslogs"]["data"])
    decoded = json.loads(gzip.decompress(payload))
    for log_event in decoded["logEvents"]:
        msg = json.loads(log_event["message"])
        # 처리 로직
```

압축 해제를 빼먹어서 처음 며칠 동안 Lambda가 invalid JSON으로 계속 실패하는 사례가 흔하다.

---

## 6. Embedded Metric Format — PutMetricData 호출 비용 줄이기

커스텀 메트릭을 발행하는 단순한 방법은 `CloudWatch.PutMetricData` API를 호출하는 것이다. 이게 호출당 과금이고, 동기 호출이라 애플리케이션 응답 시간에 더해진다. 매 요청마다 메트릭 5~10개를 찍는 서비스라면 백 단위 RPS만 돼도 PutMetricData가 응답 시간을 5~10ms 끌어올린다.

대안이 **EMF(Embedded Metric Format)**다. 애플리케이션에서 그냥 stdout으로 JSON을 찍으면, CloudWatch Logs가 `_aws.CloudWatchMetrics` 필드를 인식해서 메트릭으로 자동 추출한다. 호출도 없고, 압축된 로그 ingest 비용만 든다.

```python
import json, time

def emit_metric(order_count, latency_ms, region):
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": "Orders/Api",
                "Dimensions": [["Region"]],
                "Metrics": [
                    {"Name": "OrdersProcessed", "Unit": "Count"},
                    {"Name": "LatencyMs", "Unit": "Milliseconds"}
                ]
            }]
        },
        "Region": region,
        "OrdersProcessed": order_count,
        "LatencyMs": latency_ms,
        "traceId": "..."
    }
    print(json.dumps(payload))
```

EMF의 강점은 **같은 레코드에 메트릭과 컨텍스트를 같이 넣는다**는 점이다. `traceId`, `userId` 같은 필드는 메트릭 차원에는 안 들어가지만 Logs Insights로는 검색 가능하다. 메트릭이 튄 시점에 traceId로 원본 로그를 바로 추적할 수 있다. AWS의 `aws-embedded-metrics` 라이브러리(Python·Node·Java)가 EMF 페이로드를 만들어준다.

함정은 **카디널리티는 동일한 비용**을 친다는 점이다. EMF든 PutMetricData든 dimension 조합 하나가 메트릭 하나로 카운트된다. EMF가 싸진다고 dimension에 userId를 넣으면 똑같이 청구서가 터진다.

---

## 7. Composite Alarm과 Anomaly Detection

알람을 단일 메트릭에만 걸면 false positive에 시달린다. 야간 배포 직후 5xx가 잠깐 튀는 정도로 페이저가 울리면 팀이 알람을 무시하기 시작하고, 그게 진짜 장애를 놓치는 시작이다.

### Composite Alarm

여러 알람을 AND/OR/NOT으로 묶는다. "5xx 비율이 1% 초과 **AND** 트래픽이 평소의 50% 이상"처럼, 트래픽이 거의 없는 새벽에 우연히 비율이 튀는 경우를 자동으로 걸러낸다.

```hcl
resource "aws_cloudwatch_composite_alarm" "real_outage" {
  alarm_name = "orders-real-outage"
  alarm_rule = join(" AND ", [
    "ALARM(${aws_cloudwatch_metric_alarm.error_rate.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.traffic_floor.alarm_name})"
  ])
  alarm_actions = [aws_sns_topic.pager.arn]
}
```

배포 직후 false positive를 줄이려면 `NOT ALARM(deploy_in_progress)` 같은 deploy gate를 추가한다. 배포 파이프라인에서 시작 시점에 deploy_in_progress 알람을 ALARM 상태로 만들고 끝날 때 OK로 돌리는 식이다.

### Anomaly Detection

고정 임계값을 정하기 어려운 메트릭(요청 수, 응답 시간 분포)은 **Anomaly Detection band**로 임계를 동적으로 잡는다. CloudWatch가 과거 패턴(요일·시간대 주기성 포함)을 학습해서 평균 ± N표준편차 밴드를 만든다. 알람은 "anomaly band 밖으로 벗어남"으로 건다.

```hcl
resource "aws_cloudwatch_metric_alarm" "latency_anomaly" {
  alarm_name          = "orders-latency-anomaly"
  comparison_operator = "GreaterThanUpperThreshold"
  evaluation_periods  = 3
  threshold_metric_id = "ad1"

  metric_query {
    id          = "m1"
    return_data = true
    metric {
      metric_name = "TargetResponseTime"
      namespace   = "AWS/ApplicationELB"
      period      = 60
      stat        = "p95"
      dimensions  = { LoadBalancer = "app/orders/abc" }
    }
  }

  metric_query {
    id          = "ad1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 2)"
    label       = "TargetResponseTime expected band"
    return_data = true
  }
}
```

함정은 **학습 기간이 최소 2주**라는 점이다. 새 서비스를 띄우자마자 anomaly 알람을 걸면 거의 항상 ALARM 상태가 된다. 처음에는 고정 임계로 시작하고 트래픽이 안정되면 anomaly로 갈아타는 게 맞다.

---

## 8. 로그 폭증 시 디버깅 — API 한도와 페이지네이션

장애가 나서 로그가 평소의 100배로 쏟아지면 콘솔과 API 양쪽 모두 휘청댄다.

**GetLogEvents**는 stream 단위 조회 API다. 계정·리전당 기본 **TPS 25**이고 burst까지 합쳐도 50 정도다. SDK로 스트림을 죽 훑는 스크립트를 돌리면 금방 throttling이 걸린다. `ThrottlingException` 받으면 exponential backoff을 넣어야 한다.

**FilterLogEvents**는 Log Group 단위로 패턴 필터를 거는 API인데, 한 호출당 **최대 1MB / 10,000건** 응답 후 `nextToken`으로 페이지네이션해야 한다. 폭증 시에는 1초 안에 수만 건이 쏟아지므로 `nextToken`이 끝없이 생기고, 결국 페이지네이션이 따라가지 못해 영원히 못 끝나는 루프가 된다. 이때는 콘솔이 아니라 **Logs Insights로 시간 범위를 1분 단위로 쪼개 쿼리**하는 편이 빠르다. Insights는 내부적으로 분산 처리해서 같은 양을 훨씬 빨리 끝낸다.

폭증 자체를 막는 안전장치도 필요하다. Log Group에 **data protection policy**를 걸거나, 애플리케이션에 로그 레벨 동적 변경 기능(예: AWS AppConfig로 INFO/DEBUG 토글)을 넣어서 평상시 INFO 이상만 찍게 한다. 로그가 평소의 10배 이상이 되면 **CloudWatch Logs ingest 자체가 throttling**되어 일부 데이터가 드롭된다는 점도 기억해야 한다 — 한도는 계정 단위 IncomingBytes, IncomingLogEvents다. CloudWatch 메트릭 `IncomingBytes`에 알람을 걸어두면 폭증을 사전에 잡을 수 있다.

---

## 9. 서비스별 로그 포맷 차이

같은 CloudWatch Logs라도 출처에 따라 포맷이 완전히 다르다.

### VPC Flow Logs

기본 포맷은 공백 구분 14필드다. v3·v5에서 필드가 추가되면서 포맷이 늘어났다.

```
2 123456789012 eni-abc123 10.0.1.5 10.0.2.10 443 54321 6 12 1500 1700000000 1700000060 ACCEPT OK
```

`srcaddr`, `dstaddr`, `srcport`, `dstport`, `action`이 분석 핵심이다. Insights에서 파싱하려면 다음과 같이 한다.

```
parse @message "* * * * * * * * * * * * * *" as version, account, eni, srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, start, end, action, status
| filter action = "REJECT"
| stats sum(bytes) as total by srcaddr, dstaddr
| sort total desc
```

함정은 **Flow Logs가 1분 단위 집계**라는 점이다. 1초 단위 패킷이 아니다. 짧은 burst는 안 보인다. 또 **rejected 트래픽이 ACCEPT로 보이는 경우**가 있는데, 이는 보안그룹은 통과했지만 호스트 방화벽에서 막힌 상황이다.

### Lambda 로그

Lambda 런타임이 자동으로 찍는 라인이 있다. `START`, `END`, `REPORT`다. `REPORT`는 메트릭 분석에 핵심이다.

```
REPORT RequestId: abc Duration: 1234.56 ms Billed Duration: 1235 ms Memory Size: 512 MB Max Memory Used: 234 MB Init Duration: 567.89 ms
```

`Init Duration`은 cold start 비용이다. 이걸 추출해서 cold start 비율을 모니터링한다.

```
filter @type = "REPORT"
| parse @message /Duration: (?<dur>\S+) ms.*Init Duration: (?<init>\S+) ms/
| stats avg(dur), max(dur), pct(dur, 95), count(init) as cold_starts, count(*) as total by bin(5m)
```

`Max Memory Used`가 `Memory Size`의 90% 이상이면 OOM 위험이다. 메모리 튜닝 지표로 쓴다.

### ALB 액세스 로그

ALB는 **CloudWatch Logs로 직접 안 보낸다**. S3에 5분 단위로 떨군다. CloudWatch에서 보려면 Lambda나 Firehose로 한 번 거쳐서 넣어야 한다. 보통은 Athena로 S3에서 직접 쿼리한다. 포맷은 공백 구분이지만 일부 필드가 따옴표로 감싸져서 단순 split이 깨진다 — User-Agent에 공백이 들어가는 경우가 흔하다.

ALB 로그에서 `target_status_code = -`는 ALB가 아예 백엔드에 못 붙었다는 뜻이다. `request_processing_time`, `target_processing_time`, `response_processing_time` 세 값을 분리해서 봐야 ALB 자체 문제와 백엔드 문제를 구분할 수 있다.

---

## 10. Cross-account / Cross-region 집계와 KMS 함정

조직이 커지면 멀티 계정·멀티 리전 로그를 한 곳에 모아야 한다. CloudWatch Logs는 두 가지 방식을 지원한다.

### Subscription Filter cross-account

소스 계정의 Subscription Filter destination을 **타 계정 Kinesis Stream/Firehose**의 ARN으로 지정한다. 타겟 계정에서 destination 정책으로 소스 계정을 허용해야 한다. CloudWatch destination(`aws_cloudwatch_log_destination`) 리소스가 이 권한 경계 역할을 한다.

```hcl
# 중앙 계정
resource "aws_cloudwatch_log_destination" "central" {
  name       = "central-logs-destination"
  role_arn   = aws_iam_role.dest.arn
  target_arn = aws_kinesis_stream.central.arn
}

resource "aws_cloudwatch_log_destination_policy" "central" {
  destination_name = aws_cloudwatch_log_destination.central.name
  access_policy    = data.aws_iam_policy_document.allow_source_accounts.json
}

# 소스 계정에서는 destination_arn으로 위 ARN을 가리킨다
```

함정은 **리전이 강제로 묶인다**는 점이다. Subscription Filter는 같은 리전의 destination만 가리킬 수 있다. 멀티 리전 집계는 각 리전마다 destination을 따로 만들거나, Firehose에서 cross-region 복제를 추가해야 한다.

### Cross-account Observability (관측성 통합)

2022년 말에 추가된 기능으로, 모니터링 계정이 여러 소스 계정의 메트릭·로그·트레이스를 **API 레벨에서 그대로 조회**할 수 있게 해준다. 데이터 복제가 아니라 권한 위임 방식이라 비용이 덜 들지만, **Insights 쿼리 비용은 소스 계정에 청구**된다는 점을 팀에 미리 알려야 한다.

### KMS 암호화 Log Group 권한

규제 요건(개인정보, 금융)이 있으면 Log Group을 KMS CMK로 암호화한다. 이때 가장 자주 터지는 사고가 **키 정책에 logs.amazonaws.com 권한 누락**이다. 키 정책에 다음이 없으면 Log Group 생성 자체가 `KMSAccessDeniedException`으로 실패한다.

```json
{
  "Sid": "AllowCloudWatchLogs",
  "Effect": "Allow",
  "Principal": { "Service": "logs.ap-northeast-2.amazonaws.com" },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:ReEncrypt*",
    "kms:GenerateDataKey*",
    "kms:Describe*"
  ],
  "Resource": "*",
  "Condition": {
    "ArnLike": {
      "kms:EncryptionContext:aws:logs:arn":
        "arn:aws:logs:ap-northeast-2:123456789012:log-group:*"
    }
  }
}
```

`Service`의 리전이 빠지거나 잘못되면 같은 키를 쓰는 다른 리전에서 사일런트로 실패한다. 또 Subscription Filter destination이 다른 계정에 있을 때, **그 계정에서도 Log Group 키를 복호화할 권한**이 필요하다. KMS는 cross-account 권한을 키 정책 + IAM 정책 양쪽 다 줘야 한다는 점을 잊으면 디버깅에 반나절이 날아간다.

---

## 운영하면서 자주 마주치는 함정 정리

CloudWatch는 단순해 보이지만 운영 중 발견되는 비용·신뢰성 함정이 가장 많은 서비스 중 하나다. 정리하면 다음 지점들이다.

retention 미설정으로 저장 비용이 수집을 추월한다. ECS awslogs를 blocking 모드로 두면 CloudWatch throttling이 애플리케이션 응답 지연으로 그대로 전파된다. Insights 쿼리는 시간 범위를 좁히지 않으면 GB 단위 스캔 비용이 누적된다. Metric Filter dimension에 path나 user_id 같은 고카디널리티 필드를 넣으면 메트릭 수가 폭발한다. PutMetricData를 동기 호출로 쓰면 응답 시간이 늘고 비용이 든다 — EMF로 우회한다. Subscription Filter는 Log Group당 2개 제한이라 fan-out이 필요하면 Kinesis Streams를 한 번 거친다. KMS 암호화 Log Group은 키 정책에 `logs.{region}.amazonaws.com` 권한이 정확히 들어가야 한다.

처음 구축할 때 이 항목들을 미리 확인하면 6개월 후에 청구서를 보고 놀라거나 장애 한가운데서 쿼리가 안 도는 일을 피할 수 있다.

---

## 참고 자료

- [CloudWatch Logs Insights query syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [Embedded Metric Format spec](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html)
- [aws-embedded-metrics SDK](https://github.com/awslabs/aws-embedded-metrics-python)
- [Subscription Filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html)
- [Cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)
