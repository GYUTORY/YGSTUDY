---
title: ECS 로그 관리
tags: [aws, ecs, logging, cloudwatch-logs, firelens, fluent-bit, awslogs, logs-insights]
updated: 2026-04-20
---

# ECS 로그 관리

## 개요

ECS에서 로그는 "컨테이너 stdout/stderr이 어디로 흘러가는가"의 문제다. 온프레미스라면 파일로 떨어뜨리고 Filebeat이나 Fluentd가 긁어가지만, ECS 컨테이너는 재시작되는 순간 디스크가 날아간다. 그래서 로깅 드라이버(log driver)라는 추상화가 필요하다. Docker의 로깅 드라이버 체계를 ECS가 그대로 쓰면서 AWS 통합을 얹은 구조다.

선택지는 사실상 두 가지다.

- **awslogs 드라이버**: 컨테이너 stdout을 CloudWatch Logs로 직접 보낸다. 설정이 가장 간단하고 Fargate에서도 동작한다.
- **FireLens**: 사이드카로 Fluent Bit(또는 Fluentd)을 띄워 로그를 다양한 목적지로 라우팅한다. CloudWatch, S3, Kinesis, OpenSearch, Datadog, Splunk 모두 가능하다.

초보자는 awslogs만 써도 충분하지만, 트래픽이 커지고 요구사항이 다양해지면 결국 FireLens로 넘어간다. 넘어가는 시점은 대체로 **CloudWatch Logs 청구서가 EC2 비용을 넘기 시작할 때**다. 내가 겪은 프로젝트에서는 월 $12,000짜리 ECS 클러스터의 로그 비용이 $18,000이 찍혀 FireLens + S3로 전환했다. 이 문서는 그 경험을 정리한 것이다.

## awslogs 드라이버 기본 설정

Task Definition의 `containerDefinitions[].logConfiguration`에 설정한다. 실제로 쓰는 최소 구성은 이렇다.

```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/order-service",
      "awslogs-region": "ap-northeast-2",
      "awslogs-stream-prefix": "ecs",
      "awslogs-create-group": "true",
      "mode": "non-blocking",
      "max-buffer-size": "25m"
    }
  }
}
```

각 옵션이 실무에서 어떤 의미를 가지는지 하나씩 본다.

### awslogs-group

CloudWatch 로그 그룹 이름이다. 네이밍 규칙을 먼저 정해두지 않으면 `/ecs/my-service`, `/aws/ecs/my-service`, `my-service-logs`가 뒤섞여 나중에 관리가 지옥이 된다. 팀에서 쓰는 규칙은 이렇게 잡는다.

```
/ecs/{env}/{service-name}
```

예: `/ecs/prod/order-service`, `/ecs/stg/payment-service`. 환경을 접두로 두면 IAM 정책에서 `arn:aws:logs:ap-northeast-2:123456789012:log-group:/ecs/prod/*` 같이 환경별로 권한을 나누기 쉽다.

### awslogs-stream-prefix

로그 스트림 이름을 `{prefix}/{container-name}/{task-id}` 형태로 자동 생성한다. 이 옵션을 빼면 ECS가 스트림 이름을 만들지 못해 태스크가 아예 뜨지 않는다. Fargate에서는 **필수**다. EC2 launch type에서는 없어도 되지만, 있는 게 낫다. 그래야 Task ID로 스트림을 특정할 수 있다.

태스크 ID는 단조 증가가 아니라 해시 형태라서, 최신 로그를 보고 싶을 때 CloudWatch 콘솔에서 스트림을 정렬해봤자 별 소용이 없다. Logs Insights로 `@logStream`을 필터하는 게 빠르다.

### awslogs-create-group

로그 그룹이 없을 때 자동으로 만들어준다. IaC로 로그 그룹을 미리 만드는 구조라면 `false`가 맞다. 그런데 이걸 `false`로 두고 그룹을 미리 안 만들면 태스크가 `CannotStartContainerError: ResourceInitializationError: failed to validate logger args: ... log group does not exist`로 뜨지 않는다. 콘솔에서는 "태스크가 PROVISIONING에서 멈췄다"고만 보여서 원인을 한참 찾게 된다.

Task Role이 아니라 **Task Execution Role**이 `logs:CreateLogGroup` 권한을 가져야 동작하는 점도 자주 빠뜨린다. 관리형 정책 `AmazonECSTaskExecutionRolePolicy`에는 `CreateLogGroup`이 없다. 별도로 추가해야 한다.

```json
{
  "Effect": "Allow",
  "Action": ["logs:CreateLogGroup"],
  "Resource": "arn:aws:logs:ap-northeast-2:123456789012:log-group:/ecs/*"
}
```

### mode와 max-buffer-size

기본값은 `blocking`이다. 로그 드라이버가 CloudWatch API로 보내는 동안 **컨테이너 stdout 쓰기가 막힌다**는 뜻이다. 네트워크 이슈로 CloudWatch가 잠시 느려지면 애플리케이션 전체가 멈춘다. `System.out.println`이 300ms씩 걸리는 상황을 상상해보면 된다.

`non-blocking`으로 바꾸면 로그 드라이버 내부에 메모리 버퍼를 두고 비동기로 보낸다. 버퍼가 가득 차면 로그가 **버려진다**. 대신 컨테이너는 안 멈춘다. 운영 서비스는 무조건 `non-blocking` + `max-buffer-size`를 넉넉히(25~50m) 잡는다. 로그 좀 빠지는 것보다 서비스가 느려지는 게 훨씬 치명적이다.

## 로그 그룹과 스트림 네이밍 패턴

로그 스트림 이름은 `awslogs-stream-prefix/{container-name}/{task-id}`로 자동 생성된다고 했다. 컨테이너가 여러 개인 사이드카 패턴이라면 각 컨테이너의 로그가 같은 그룹 안에서 스트림으로 분리된다.

문제는 **한 로그 그룹에 너무 많은 스트림이 쌓이면 CloudWatch 콘솔이 버벅댄다**는 점이다. 하루에 태스크가 수천 개 새로 뜨는 서비스라면 한 달 뒤 로그 그룹에 수십만 개 스트림이 쌓인다. Logs Insights 쿼리도 느려진다. 이 경우는 로그 그룹의 **Retention**을 반드시 설정해야 한다.

```bash
aws logs put-retention-policy \
  --log-group-name /ecs/prod/order-service \
  --retention-in-days 14
```

기본값이 "영구 보관"이라서 이걸 놓치면 그룹 크기가 계속 늘어난다. CloudWatch Logs는 저장 비용이 GB당 $0.03(서울 리전)인데, 보관 기간이 없으면 몇 년 치가 쌓여 금방 $1,000 단위가 된다.

애플리케이션 로그는 14~30일, 감사(audit) 로그는 365일, 보안 로그는 S3로 장기 보관하는 식으로 등급을 나눠 설계한다. 모든 로그를 CloudWatch에 1년 보관하는 건 거의 항상 잘못된 설계다.

## CloudWatch Logs 비용 폭증 사례

비용 구조를 먼저 알아야 한다. CloudWatch Logs 요금은 세 덩어리다.

- **Ingestion**: 들어오는 데이터 GB당 $0.76 (서울). 이게 압도적으로 크다.
- **Storage**: 저장된 데이터 GB당 $0.03/월.
- **Logs Insights 쿼리**: 스캔한 데이터 GB당 $0.0076.

Ingestion이 스토리지의 25배다. "로그를 일단 다 넣고 필요할 때 보자"가 바로 파산 각이다.

실제로 본 사례를 하나 공유하자면, 스프링 부트 앱이 DEBUG 레벨로 Hibernate SQL을 찍고 있었고, 그게 Production으로 그대로 배포됐다. 초당 3,000 TPS에서 한 요청당 SQL이 5줄씩 나오니 로그가 초당 15,000줄. 한 줄 평균 400B로 계산하면 초당 6MB, 하루에 500GB. 한 달이면 15TB, 인제스트 비용만 $11,400이다.

이런 사고를 막으려면 몇 가지를 챙긴다.

첫째, **로그 레벨은 환경변수로 반드시 외부화**하고 Production은 INFO 이하로 제한한다. 프레임워크의 디버그 로거(Hibernate, Spring RestTemplate, Jackson 등)도 개별로 INFO/WARN으로 낮춘다.

둘째, **접근 로그(access log)는 awslogs 드라이버로 보내지 않는다**. ALB 접근 로그는 S3로 보내고, 애플리케이션 접근 로그도 FireLens + S3 경로로 따로 뺀다. CloudWatch에는 에러 위주로 남긴다.

셋째, **로그 필터를 드라이버 쪽에 둘 수 있는 FireLens를 검토**한다. awslogs는 필터링이 안 되고 들어오는 대로 다 보낸다. FireLens의 Fluent Bit `grep` 필터로 `level=DEBUG`를 drop하는 구성이 기본이다.

넷째, **CloudWatch Alarms에 `IncomingBytes` 지표를 걸어둔다**. 로그 그룹별로 평소 대비 2~3배 튀면 알람이 울리도록 한다. 누가 실수로 DEBUG를 켜고 배포하면 30분 안에 알 수 있다.

## JSON 구조화 로그와 Logs Insights

문자열 로그는 검색이 끔찍하다. `ERROR userId=12345 order=67890 reason=...` 이런 형태를 grep하면 정규식 지옥이 된다. ECS에서는 처음부터 JSON으로 찍는다.

스프링 부트 기준으로 `logback-spring.xml`을 이렇게 구성한다.

```xml
<configuration>
  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <customFields>{"service":"order-service","env":"${ENV}"}</customFields>
    </encoder>
  </appender>
  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>
</configuration>
```

이렇게 찍으면 stdout에 다음 같은 JSON이 한 줄로 떨어진다.

```json
{"@timestamp":"2026-04-20T11:32:14.215+09:00","level":"ERROR","logger_name":"c.e.o.OrderService","message":"payment failed","traceId":"abc123","userId":"12345","service":"order-service","env":"prod"}
```

CloudWatch Logs Insights는 JSON을 자동 파싱한다. 필드로 바로 필터가 가능하다.

```
fields @timestamp, level, message, traceId, userId
| filter level = "ERROR" and service = "order-service"
| filter userId = "12345"
| sort @timestamp desc
| limit 200
```

주의할 점은 Insights가 과금이라는 것이다. 스캔 데이터 GB당 $0.0076. 필터 없이 일주일 범위를 스캔하면 한 번에 $10씩 나갈 수도 있다. 쿼리에 **시간 범위를 가능한 한 좁게**, `@logStream`이나 `service` 필드로 **먼저 필터링**하는 습관을 들인다.

## 멀티라인 스택 트레이스 처리

awslogs 드라이버는 **줄바꿈 단위로 로그 이벤트를 만든다**. Java 스택 트레이스는 한 예외에 수십 줄이 나오는데, 그게 각각 따로 CloudWatch 이벤트가 된다. Logs Insights에서 `ERROR`로 필터링하면 첫 줄만 나오고 `Caused by:` 라인은 별도 이벤트로 흩어진다. 디버깅이 매우 힘들어진다.

해결책은 두 가지다.

첫째, **JSON 로거를 쓰면 자동으로 해결된다**. Logstash Encoder가 스택 트레이스 전체를 `stack_trace` 필드로 한 이벤트에 담는다. 이게 가장 깔끔하다.

둘째, JSON을 못 쓰는 레거시라면 `awslogs-multiline-pattern` 옵션을 쓴다.

```json
"options": {
  "awslogs-group": "/ecs/prod/legacy-app",
  "awslogs-stream-prefix": "ecs",
  "awslogs-multiline-pattern": "^\\d{4}-\\d{2}-\\d{2}"
}
```

이 패턴에 매칭되지 않는 줄은 이전 줄에 이어붙인다. 즉 `2026-04-20`으로 시작하는 줄만 새 이벤트로 간주하고, `at com.example...`로 시작하는 줄은 이전 이벤트에 합쳐진다. 이 방식은 Fargate에서도 동작한다.

FireLens를 쓴다면 Fluent Bit의 `multiline.parser`가 더 유연하다. Python Traceback, Go 스택 트레이스 등 언어별 프리셋이 있다.

## 로그 누락 원인 3가지

"로그가 분명히 찍혔는데 CloudWatch에 없다"는 문제는 실무에서 정말 자주 본다. 원인을 하나씩 짚어본다.

### 버퍼가 플러시되기 전에 컨테이너 종료

`non-blocking` 모드의 awslogs 드라이버는 내부에 메모리 버퍼를 둔다. 컨테이너가 갑자기 죽으면 이 버퍼의 내용이 **그대로 사라진다**. 특히 SIGKILL로 끝나는 태스크(Health Check 실패 후 강제 종료, OOM Kill 등)는 마지막 몇 초의 로그가 없다. 마지막 로그만 보고 원인을 찾으려 하면 헛수고다.

해결은 두 방향이다. 애플리케이션 쪽에서 정상 종료(SIGTERM 처리) 시 `System.out.flush()`를 호출하고 짧은 sleep을 줘서 드라이버가 플러시할 시간을 확보한다. 또 하나는 `stopTimeout`을 늘려 SIGTERM 후 강제 KILL까지의 여유를 30초에서 60~90초로 늘린다.

### 드라이버가 로그를 드랍

`mode: non-blocking`에서 버퍼가 가득 차면 새 로그를 버린다. CloudWatch에 로그가 띄엄띄엄 찍히거나 일정 구간이 통째로 비어있다면 드랍을 의심한다. `max-buffer-size`를 키우거나, 애플리케이션이 로그를 너무 많이 찍고 있지 않은지 점검한다.

Docker 엔진 로그(EC2 launch type이면 `/var/log/docker` 또는 systemd journal)에서 `logger buffer is full` 메시지로 확인할 수 있다. Fargate는 이 로그를 못 보니 CloudWatch 이벤트의 간격과 애플리케이션이 찍은 시각을 비교해 추정한다.

### Task Execution Role에 logs 권한 없음

드라이버가 CloudWatch로 보내는 권한은 **Task Execution Role**에 있어야 한다. Task Role이 아니다. 이걸 헷갈려 Task Role에 `logs:PutLogEvents`를 붙이면 동작하지 않는다. 관리형 정책 `AmazonECSTaskExecutionRolePolicy`에는 `PutLogEvents`와 `CreateLogStream`이 있지만 `CreateLogGroup`은 없다. `awslogs-create-group: true`를 쓰려면 별도로 추가해야 한다는 건 앞에서 언급했다.

## FireLens 사이드카로 로그 라우팅

awslogs의 한계가 보이기 시작하면 FireLens로 넘어간다. FireLens는 Task Definition에 Fluent Bit 컨테이너를 사이드카로 띄우고, 다른 컨테이너들의 로그를 그쪽으로 라우팅하는 구조다.

```json
{
  "containerDefinitions": [
    {
      "name": "log_router",
      "image": "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable",
      "essential": true,
      "firelensConfiguration": {
        "type": "fluentbit",
        "options": {
          "enable-ecs-log-metadata": "true",
          "config-file-type": "file",
          "config-file-value": "/fluent-bit/etc/extra.conf"
        }
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/prod/order-service/firelens",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "firelens"
        }
      }
    },
    {
      "name": "app",
      "image": "my-app:1.0.0",
      "logConfiguration": {
        "logDriver": "awsfirelens",
        "options": {
          "Name": "cloudwatch_logs",
          "region": "ap-northeast-2",
          "log_group_name": "/ecs/prod/order-service",
          "log_stream_prefix": "app-",
          "auto_create_group": "true"
        }
      }
    }
  ]
}
```

포인트는 세 가지다.

첫째, **log_router 컨테이너 자체의 로그**도 어딘가로 보내야 한다. 그래서 log_router는 `awslogs` 드라이버를 쓴다. 이 로그 그룹에는 Fluent Bit의 에러(파싱 실패, 전송 실패 등)가 찍힌다. FireLens 전환 후 디버깅은 거의 이 그룹을 본다.

둘째, **앱 컨테이너는 `awsfirelens` 드라이버**를 쓴다. 옵션에 들어간 키(Name, region, log_group_name 등)는 Fluent Bit `Output` 플러그인의 설정으로 그대로 전달된다. 여기에 적은 값이 FireLens가 생성하는 Fluent Bit 설정 파일에 자동으로 삽입된다.

셋째, **복잡한 라우팅은 별도 설정 파일**로 분리한다. `config-file-value`에 지정한 `/fluent-bit/etc/extra.conf`에 여러 Output, Filter를 정의하고 Fluent Bit 이미지에 같이 넣어 빌드한다.

### 실제 라우팅 구성

요구사항이 이런 경우가 많다. "INFO 이상은 S3로 장기 보관, ERROR는 CloudWatch + Slack, 접근 로그는 Kinesis Firehose로 OpenSearch에 넣기."

extra.conf는 이렇게 된다.

```
[FILTER]
    Name          grep
    Match         *
    Exclude       level DEBUG

[OUTPUT]
    Name          cloudwatch_logs
    Match         *
    region        ap-northeast-2
    log_group_name /ecs/prod/order-service
    log_stream_prefix app-
    auto_create_group true
    log_retention_days 14

[OUTPUT]
    Name          s3
    Match         *
    region        ap-northeast-2
    bucket        my-log-archive
    total_file_size 50M
    upload_timeout 5m
    s3_key_format /order-service/%Y/%m/%d/%H/$UUID.gz
    compression   gzip

[OUTPUT]
    Name          kinesis_firehose
    Match         access.*
    region        ap-northeast-2
    delivery_stream access-log-to-opensearch
```

CloudWatch에는 14일만 남기고 S3에는 365일을 gzip으로 쌓는다. 그 결과 인제스트 비용이 크게 줄었다. 기존 월 $11,000 → S3 저장 + Kinesis 요금 합쳐 월 $2,500 수준까지 내려갔다.

### FireLens의 주의점

Fluent Bit 사이드카가 죽으면 앱 컨테이너의 로그도 같이 막힌다. 그래서 `essential: true`로 둬서 **사이드카가 죽으면 태스크 전체를 재시작**하는 게 안전하다. 앱만 살아 로그 없이 돌아가는 상황이 더 위험하다.

Fluent Bit 자체가 OOM으로 죽는 경우도 있다. 메모리 버퍼(`Mem_Buf_Limit`)가 기본 너무 크면 안 맞는다. 사이드카 컨테이너에 `memory: 256` (MB) 정도 여유를 주고 Fluent Bit 설정에서도 `storage.type filesystem`으로 디스크 버퍼를 쓰는 편이 안전하다. Fargate는 20GB 임시 스토리지가 기본 제공되니 디스크 버퍼가 가능하다.

## S3/Kinesis/OpenSearch 전송 구성

### S3로 장기 보관

Fluent Bit의 `s3` Output을 쓰면 된다. 위 예제에 있다. 주의할 점은 `total_file_size`와 `upload_timeout`이다. 기본값이 크면 태스크가 종료될 때 **아직 업로드되지 않은 버퍼의 로그가 날아간다**. 운영에서는 50MB/5분 정도로 공격적으로 플러시한다.

S3에 쌓은 로그는 Athena로 쿼리한다. Glue 크롤러로 파티션을 걸거나, `s3_key_format`에 Hive 스타일 파티션(`year=%Y/month=%m/day=%d/`)을 넣어두면 Athena가 바로 파티션을 인식한다.

### Kinesis Data Streams / Firehose

실시간 스트림 처리가 필요하면 Kinesis Data Streams, OpenSearch/S3로 배치 전송이면 Firehose다. Fluent Bit의 `kinesis_streams`, `kinesis_firehose` Output이 둘 다 있다.

Firehose → OpenSearch 경로는 인덱스 템플릿 관리만 잘하면 거의 손이 안 간다. 다만 인제스트량이 많으면 **OpenSearch 비용이 CloudWatch보다 비싸질 수도 있다**. 클러스터를 m6g.large 2대로 돌려도 월 $500이고, 데이터 볼륨이 커지면 금방 $2,000이 된다. 전수 저장이 필요한지 아니면 에러만 인덱싱할지 먼저 정한다.

### 직접 OpenSearch로 보내기

Fluent Bit의 `opensearch` Output으로 OpenSearch에 직접 넣을 수도 있다. 이 경우는 OpenSearch가 잠깐 다운되면 로그가 Fluent Bit 버퍼에 쌓이다가 터진다. Firehose를 중간에 두는 편이 버퍼링과 재시도를 맡길 수 있어 안정적이다.

## awslogs-create-group 누락으로 태스크가 뜨지 않는 문제

앞에서 짧게 언급했지만 실무에서 가장 자주 보는 문제라 한 번 더 정리한다.

증상은 이렇다. ECS 서비스 이벤트에 `was unable to place a task` 같은 메시지가 없고 태스크가 PROVISIONING → STOPPED로 바로 간다. 중지된 태스크의 Stopped Reason을 보면 아래 둘 중 하나다.

```
CannotStartContainerError: ResourceInitializationError:
failed to create new container runtime task:
failed to create shim task: OCI runtime create failed:
runc create failed: unable to start container process:
error during container init: error setting log driver:
failed to create logger: LogGroup does not exist
```

또는

```
ResourceInitializationError: failed to validate logger args:
log group does not exist: /ecs/prod/my-service
```

원인은 세 가지 중 하나다.

1. 로그 그룹이 실제로 없는데 `awslogs-create-group`을 `false`로 두거나 아예 안 넣었다.
2. `awslogs-create-group: true`인데 Task Execution Role에 `logs:CreateLogGroup` 권한이 없다.
3. Task Execution Role이 제대로 attach되지 않았다(Task Role과 혼동).

해결 순서는 이렇게 본다.

CloudWatch에서 로그 그룹 이름을 직접 확인한다. Task Definition의 그룹 이름과 일치하는가. 대소문자까지 확인한다. `/ecs/Prod/...`와 `/ecs/prod/...`는 다른 그룹이다.

로그 그룹이 없다면 수동으로 만들거나 `awslogs-create-group: true`를 넣는다. 권한이 붙어있는지도 동시에 확인한다.

IaC(Terraform/CDK)로 관리한다면 그룹을 미리 리소스로 선언하고 드라이버에서는 `awslogs-create-group`을 빼는 쪽이 깔끔하다. 리텐션도 같이 설정할 수 있어 누락을 막는다.

## 정리

ECS 로깅에서 가장 중요한 건 "로그가 보이는가"가 아니라 "보여야 할 로그만 보이는가"다. 기본 awslogs 드라이버는 간단하지만 필터링이 없어 금세 CloudWatch 청구서가 폭증한다. non-blocking 모드, 멀티라인 처리, Task Execution Role 권한, 로그 그룹 Retention 설정까지 챙기는 것이 awslogs 단계의 목표다.

규모가 커지면 FireLens + Fluent Bit으로 넘어가 S3, Kinesis, OpenSearch로 분리 저장한다. 이때도 사이드카가 죽으면 앱도 같이 영향받는 구조라는 점을 기억해야 한다. 로그 파이프라인 자체도 감시 대상이 되어야 한다는 뜻이다. CloudWatch Alarms에 `IncomingBytes`, 로그 그룹별 사이즈 증가율, FireLens 사이드카 메모리 사용률 정도는 기본으로 걸어두는 게 좋다.
