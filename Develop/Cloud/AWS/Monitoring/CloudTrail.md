---
title: AWS CloudTrail
tags: [aws, security, cloud, monitoring, observability]
updated: 2026-10-11
---

# AWS CloudTrail

AWS 계정의 모든 API 호출을 기록하는 감사 서비스다. "누가 EC2 인스턴스를 삭제했나", "어떤 역할이 S3 버킷 정책을 바꿨나" 같은 질문에 답하는 게 주 목적이다.

기본 제공되는 Event History는 90일, 단일 리전, 관리 이벤트만 포함한다. 장기 보관이나 멀티 리전 감사가 필요하면 Trail을 직접 생성해야 한다.

---

## 로그가 도착하는 경로

API 호출 한 건이 어디에 어떤 형태로 남는지 알아야 사고 때 어디를 볼지 정해진다. 아래 도식은 호출이 이벤트가 되고, Trail을 거쳐 세 갈래로 나뉘는 흐름이다. 관리 이벤트는 기본으로 수집되고 데이터 이벤트는 직접 켠 대상만 수집된다.

```mermaid
flowchart LR
    A["API 호출<br/>콘솔 · CLI · SDK"] --> M["관리 이벤트<br/>기본 수집"]
    A --> D["데이터 이벤트<br/>S3 객체 · Lambda 실행<br/>켠 대상만 수집"]
    M --> H["Event History<br/>90일 · 관리 이벤트만"]
    M --> T["Trail"]
    D --> T
    T --> S3["S3 버킷<br/>5~15분 지연"]
    T --> CW["CloudWatch Logs"]
    T --> EB["EventBridge"]
    S3 --> AT["Athena<br/>사후 분석"]
    CW --> AL["메트릭 필터 · 알람"]
    EB --> LM["Lambda · SNS<br/>자동 대응"]
```

S3 버킷에 로그 파일이 쓰이기까지 보통 5~15분이 걸린다. 침해가 진행 중인데 Athena에서 방금 일어난 호출이 안 보인다고 해서 안 일어난 것으로 판단하면 안 된다. 데이터 이벤트는 Trail에 명시적으로 켜지 않았다면 어디에도 없다. 누가 `GetObject`로 파일을 가져갔는지 묻는 시점에야 데이터 이벤트가 꺼져 있었다는 걸 알게 되는 경우가 많다.

---

## Trail 생성

### 기본 Trail

콘솔보다 CLI로 만드는 게 재현 가능하고 버전 관리하기 좋다.

```bash
# Trail 전용 S3 버킷 생성
aws s3 mb s3://my-cloudtrail-logs-123456789012 --region ap-northeast-2

# 버킷 버전 관리 활성화
aws s3api put-bucket-versioning \
  --bucket my-cloudtrail-logs-123456789012 \
  --versioning-configuration Status=Enabled

# Trail 생성 (멀티 리전, 로그 무결성 검증 포함)
aws cloudtrail create-trail \
  --name my-audit-trail \
  --s3-bucket-name my-cloudtrail-logs-123456789012 \
  --is-multi-region-trail \
  --include-global-service-events \
  --enable-log-file-validation \
  --kms-key-id arn:aws:kms:ap-northeast-2:123456789012:key/KEY_ID

# Trail 활성화 (create-trail만으로는 로깅이 시작되지 않는다)
aws cloudtrail start-logging --name my-audit-trail
```

`--enable-log-file-validation`은 반드시 켠다. 나중에 로그 무결성 검증을 돌리려면 Trail 생성 시점부터 Digest 파일이 쌓여야 한다.

### Organizations Trail

여러 계정을 운영하는 환경에서는 Organizations Trail로 중앙화한다. 관리 계정에서 생성하면 모든 멤버 계정의 이벤트가 단일 버킷으로 모인다.

```bash
# Organizations Trail 생성 (관리 계정에서 실행)
aws cloudtrail create-trail \
  --name org-audit-trail \
  --s3-bucket-name central-audit-logs-123456789012 \
  --is-multi-region-trail \
  --is-organization-trail \
  --include-global-service-events \
  --enable-log-file-validation

aws cloudtrail start-logging --name org-audit-trail
```

멤버 계정 수가 늘어도 Trail을 새로 만들 필요가 없다. 계정이 조직에 합류하면 자동으로 로그가 수집된다.

---

## 이벤트 유형

### 관리 이벤트

IAM 정책 변경, 보안 그룹 수정, VPC 설정 변경 같은 제어 평면 작업이다. 첫 번째 Trail은 관리 이벤트에 한해 무료다.

읽기(Read)와 쓰기(Write)를 분리해 활성화할 수 있다. 보안 감사 목적이면 쓰기 이벤트만 켜도 충분한 경우가 많다. 읽기 이벤트는 볼륨이 훨씬 커서 비용 압박이 생긴다.

```bash
# 쓰기 이벤트만 활성화
aws cloudtrail put-event-selectors \
  --trail-name my-audit-trail \
  --event-selectors '[
    {
      "ReadWriteType": "WriteOnly",
      "IncludeManagementEvents": true,
      "DataResources": []
    }
  ]'
```

### 데이터 이벤트

S3 객체 읽기/쓰기, Lambda 실행 같은 데이터 평면 작업이다. 기본 비활성화 상태이고, 트래픽이 많은 S3 버킷을 전체 대상으로 켜면 비용이 빠르게 올라간다.

트래픽이 있는 S3 버킷 하나에서 하루 1억 건 이상의 데이터 이벤트가 나오는 경우가 있다. 버킷 전체를 켜는 대신 보안상 민감한 경로만 골라서 활성화해야 한다.

Advanced Event Selectors로 특정 버킷의 특정 경로만 로깅할 수 있다.

```bash
# 특정 경로와 특정 Lambda만 데이터 이벤트 활성화
aws cloudtrail put-event-selectors \
  --trail-name my-audit-trail \
  --advanced-event-selectors '[
    {
      "Name": "sensitive-s3-writes",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
        {"Field": "readOnly", "Equals": ["false"]},
        {"Field": "resources.ARN", "StartsWith": [
          "arn:aws:s3:::my-sensitive-bucket/pii/",
          "arn:aws:s3:::my-sensitive-bucket/financial/"
        ]}
      ]
    },
    {
      "Name": "payment-lambda",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::Lambda::Function"]},
        {"Field": "resources.ARN", "Equals": [
          "arn:aws:lambda:ap-northeast-2:123456789012:function:payment-processor"
        ]}
      ]
    }
  ]'
```

### 인사이트 이벤트

비정상적인 API 호출 패턴을 자동으로 감지한다. 평소보다 CreateUser 호출이 갑자기 급증하거나, DeleteBucket 에러율이 치솟는 경우를 잡아낸다.

100,000건당 $0.35다. GuardDuty와 기능이 겹치는 부분이 있어 둘 다 켜면 중복 비용이 발생한다. 보안 요구사항과 예산을 비교해 선택한다.

---

## CloudTrail Lake

2022년에 추가된 기능으로, S3에 로그를 저장하고 Athena로 쿼리하는 대신 CloudTrail 안에서 바로 SQL 쿼리를 실행할 수 있는 이벤트 데이터 스토어다. 최대 7년 보관, 변경 불가 저장소라 감사 목적에 적합하다.

기존 Trail + S3 + Athena 구성 대비 Glue 테이블 관리, Athena 파티션 설정 같은 운영 작업이 없다. 단, 비용 구조가 달라 무조건 저렴하지는 않다.

```bash
# Event Data Store 생성
aws cloudtrail create-event-data-store \
  --name production-audit-store \
  --retention-period 2557 \
  --multi-region-enabled \
  --organization-enabled \
  --termination-protection-enabled

# 생성된 ARN 확인 (쿼리 시 FROM 절에 사용)
aws cloudtrail list-event-data-stores \
  --query 'EventDataStores[?Name==`production-audit-store`].[EventDataStoreArn,Status]' \
  --output table
```

쿼리는 콘솔이나 CLI로 바로 실행한다. FROM 절에는 Event Data Store ARN을 쓴다.

```bash
# 루트 계정 활동 조회
aws cloudtrail start-query \
  --query-statement "
    SELECT
      eventTime,
      userIdentity.arn,
      sourceIPAddress,
      userAgent,
      eventName
    FROM arn:aws:cloudtrail:ap-northeast-2:123456789012:eventdatastore/STORE_ID
    WHERE userIdentity.type = 'Root'
      AND eventTime > '2026-09-01 00:00:00'
    ORDER BY eventTime DESC
    LIMIT 100
  "

# 쿼리 결과 확인
aws cloudtrail get-query-results --query-id QUERY_ID
```

### S3+Athena vs CloudTrail Lake 비용 비교

월 100만 관리 이벤트 기준 대략적인 비교다. 실제 비용은 리전과 쿼리 빈도에 따라 다르다.

| 항목 | Trail + S3 + Athena | CloudTrail Lake |
|---|---|---|
| 이벤트 수집 | 관리 이벤트 첫 Trail 무료 | GB당 $2.50 (약 7만 이벤트/GB) |
| 저장 비용 | S3 GB당 $0.023 | 포함 |
| 쿼리 비용 | Athena TB당 $5.00 | TB당 $0.005 |
| 운영 부담 | Glue, Athena 설정 필요 | 없음 |
| 최대 보관 기간 | S3 생명주기 설정에 따라 무제한 | 7년 |

쿼리를 자주 하고 운영 편의를 중시하면 Lake가 낫다. 볼륨이 크고 쿼리는 가끔 하는 환경이면 기존 S3+Athena가 저렴하다.

---

## 로그 무결성 검증

`--enable-log-file-validation`을 켜고 Trail을 만들면, CloudTrail이 매 시간 Digest 파일을 생성하고 SHA-256 해시로 로그 파일을 연결한다. 로그가 삭제되거나 변조됐는지 확인할 수 있다.

보안 침해 대응 시 "이 로그 파일이 원본인지" 증명해야 할 때 쓴다. 특히 로그를 저장하는 계정 자체가 공격받았을 때 Digest 파일로 변조 여부를 입증할 수 있다.

```bash
# 특정 기간 로그 무결성 검증
aws cloudtrail validate-logs \
  --trail-arn arn:aws:cloudtrail:ap-northeast-2:123456789012:trail/my-audit-trail \
  --start-time 2026-09-01T00:00:00Z \
  --end-time 2026-09-28T23:59:59Z \
  --verbose
```

정상 출력 예시:
```
Validating log files for trail arn:aws:cloudtrail:ap-northeast-2:123456789012:trail/my-audit-trail
2026-09-28T10:00:00Z: s3://my-cloudtrail-logs.../CloudTrail-Digest/...digest.json.gz validated
2026-09-28T09:00:00Z: s3://my-cloudtrail-logs.../CloudTrail/...json.gz validated
...
Results requested for 2026-09-01T00:00:00Z to 2026-09-28T23:59:59Z
672 log files validated, 0 log files failed validation, 0 log files were skipped
```

검증이 실패하면 해당 파일이 변조됐거나 삭제된 것이다. `0 log files failed validation`이 아닌 숫자가 나오면 즉시 조사한다.

멀티 계정 구성에서는 로그 수집 계정의 Digest 파일에 대한 읽기 권한만 있으면 본 계정에서 검증을 실행할 수 있다.

---

## EventBridge 연동

특정 이벤트 발생 시 즉각 대응이 필요하면 CloudTrail → EventBridge → Lambda 패턴을 쓴다. 루트 계정 로그인, IAM 정책 대량 변경, 보안 그룹에 0.0.0.0/0 추가 같은 이벤트를 실시간으로 잡는다.

### EventBridge 규칙 생성

```bash
# 루트 계정 콘솔 로그인 성공 감지
aws events put-rule \
  --name detect-root-login \
  --event-pattern '{
    "source": ["aws.signin"],
    "detail-type": ["AWS Console Sign In via CloudTrail"],
    "detail": {
      "userIdentity": {
        "type": ["Root"]
      },
      "responseElements": {
        "ConsoleLogin": ["Success"]
      }
    }
  }' \
  --state ENABLED

# IAM 정책 변경 감지
aws events put-rule \
  --name detect-iam-policy-changes \
  --event-pattern '{
    "source": ["aws.iam"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventName": [
        "PutUserPolicy", "PutRolePolicy",
        "AttachUserPolicy", "AttachRolePolicy",
        "CreatePolicy", "DeletePolicy",
        "CreateUser", "DeleteUser"
      ]
    }
  }' \
  --state ENABLED
```

### Lambda 자동 대응

```python
import json
import boto3
from datetime import datetime

sns = boto3.client('sns')
ALERT_TOPIC = 'arn:aws:sns:ap-northeast-2:123456789012:security-alerts'

def lambda_handler(event, context):
    detail = event['detail']
    event_name = detail.get('eventName', 'ConsoleLogin')
    user_identity = detail.get('userIdentity', {})

    caller = user_identity.get('arn') or user_identity.get('type', 'unknown')
    source_ip = detail.get('sourceIPAddress', 'unknown')
    event_time = detail.get('eventTime', datetime.utcnow().isoformat())
    error_code = detail.get('errorCode', '')
    error_message = detail.get('errorMessage', '')

    body = (
        f"이벤트: {event_name}\n"
        f"호출자: {caller}\n"
        f"IP: {source_ip}\n"
        f"시간: {event_time}\n"
    )

    if error_code:
        body += f"에러: {error_code} - {error_message}\n"

    request_params = detail.get('requestParameters', {})
    if request_params:
        body += f"\n요청 파라미터:\n{json.dumps(request_params, indent=2, ensure_ascii=False)}"

    sns.publish(
        TopicArn=ALERT_TOPIC,
        Subject=f'[보안 알림] {event_name}',
        Message=body
    )

    return {'statusCode': 200}
```

Lambda를 EventBridge 타겟으로 연결한다:

```bash
aws events put-targets \
  --rule detect-root-login \
  --targets '[
    {
      "Id": "security-alert-lambda",
      "Arn": "arn:aws:lambda:ap-northeast-2:123456789012:function:security-alert-handler"
    }
  ]'

# Lambda에 EventBridge 호출 권한 부여
aws lambda add-permission \
  --function-name security-alert-handler \
  --statement-id allow-eventbridge-root-login \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:ap-northeast-2:123456789012:rule/detect-root-login
```

---

## Athena로 로그 분석

S3에 쌓인 CloudTrail 로그를 Athena로 분석하려면 먼저 외부 테이블을 만들어야 한다. CloudTrail 전용 SerDe를 쓰면 gzip 압축 JSON을 직접 읽는다.

```sql
CREATE EXTERNAL TABLE cloudtrail_logs (
  eventVersion STRING,
  userIdentity STRUCT<
    type: STRING,
    principalId: STRING,
    arn: STRING,
    accountId: STRING,
    accessKeyId: STRING,
    userName: STRING,
    sessionContext: STRUCT<
      attributes: STRUCT<
        mfaAuthenticated: STRING,
        creationDate: STRING
      >,
      sessionIssuer: STRUCT<
        type: STRING,
        arn: STRING,
        userName: STRING
      >
    >
  >,
  eventTime STRING,
  eventSource STRING,
  eventName STRING,
  awsRegion STRING,
  sourceIPAddress STRING,
  userAgent STRING,
  errorCode STRING,
  errorMessage STRING,
  requestParameters STRING,
  responseElements STRING,
  requestId STRING,
  eventId STRING,
  eventType STRING
)
ROW FORMAT SERDE 'com.amazon.emr.hive.serde.CloudTrailSerde'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://my-cloudtrail-logs-123456789012/AWSLogs/123456789012/CloudTrail/';
```

자주 쓰는 쿼리들이다.

루트 계정 활동 전체 조회:
```sql
SELECT eventTime, eventSource, eventName, sourceIPAddress, userAgent
FROM cloudtrail_logs
WHERE userIdentity.type = 'Root'
  AND eventTime >= '2026-09-01'
ORDER BY eventTime DESC;
```

MFA 없이 로그인한 IAM 사용자의 활동:
```sql
SELECT eventTime, userIdentity.arn, eventName, sourceIPAddress
FROM cloudtrail_logs
WHERE userIdentity.sessionContext.attributes.mfaAuthenticated = 'false'
  AND userIdentity.type = 'IAMUser'
  AND eventTime >= '2026-09-01'
ORDER BY eventTime DESC;
```

IAM 정책 변경 이력:
```sql
SELECT
  eventTime,
  userIdentity.userName,
  userIdentity.arn,
  eventName,
  requestParameters
FROM cloudtrail_logs
WHERE eventName IN (
  'PutUserPolicy', 'PutRolePolicy', 'PutGroupPolicy',
  'AttachUserPolicy', 'AttachRolePolicy', 'AttachGroupPolicy',
  'DeleteUserPolicy', 'DeleteRolePolicy', 'DetachUserPolicy',
  'CreatePolicy', 'DeletePolicy'
)
  AND eventTime >= '2026-09-01'
ORDER BY eventTime DESC;
```

로그인 실패를 반복하는 IP 조회:
```sql
SELECT sourceIPAddress, COUNT(*) AS failure_count
FROM cloudtrail_logs
WHERE eventName = 'ConsoleLogin'
  AND errorCode IS NOT NULL
  AND eventTime >= '2026-09-01'
GROUP BY sourceIPAddress
HAVING COUNT(*) > 5
ORDER BY failure_count DESC;
```

---

## 탈취된 액세스 키 추적

GitHub에 올라간 `.env`, 퇴사자 노트북, CI 로그에 찍힌 환경변수에서 키가 새는 경우가 대부분이다. 키가 새면 공격자는 대개 비슷한 순서로 움직이고, 그 순서가 그대로 CloudTrail에 남는다. 추적은 이 순서를 알고 거꾸로 짚어 가는 일이다.

```mermaid
sequenceDiagram
    participant X as 공격자
    participant API as AWS API
    participant CT as CloudTrail

    Note over X: 유출된 AKIA 키 확보
    X->>API: GetCallerIdentity
    API-->>X: 계정 ID, 사용자 ARN
    X->>API: ListAttachedUserPolicies, ListRoles, ListBuckets, DescribeInstances
    API-->>X: 권한 범위와 리소스 목록, 일부는 AccessDenied
    opt 권한이 넓은 경우
        X->>API: GetObject, CopyObject 로 데이터 접근
        X->>API: CreateAccessKey, CreateUser 로 새 진입로 확보
        X->>API: AssumeRole 로 다른 역할 이동
    end
    X->>API: StopLogging, DeleteTrail
    API->>CT: 호출마다 이벤트 기록
    Note over API,CT: StopLogging 호출 자체도 이벤트로 남는다
```

정찰 단계는 읽기 호출이라 Trail을 쓰기 전용으로 만들어 두면 통째로 빠진다. 앞서 쓰기 이벤트만 켜도 충분하다고 한 것은 변경 이력 용도이고, 침해 조사까지 염두에 두면 읽기 이벤트가 있어야 정찰이 보인다.

### 키 하나로 전체 활동 뽑기

의심되는 키가 있으면 가장 먼저 그 키가 한 일 전부를 시간순으로 본다. 90일 이내이고 관리 이벤트라면 Athena를 세팅하지 않고도 CLI로 바로 된다.

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAIOSFODNN7EXAMPLE \
  --query 'Events[].[EventTime,EventName,Username]' --output table
```

`lookup-events`는 리전 하나만 본다. 공격자가 쓴 리전을 모르면 리전별로 돌려야 하고, 그래서 멀티 리전 Trail을 Athena로 한 번에 보는 편이 빠르다. 앞의 DDL에는 `userIdentity.accessKeyId`가 있어야 이 쿼리가 돈다. 이 테이블은 파티션이 없어서 `eventTime` 범위를 좁히지 않으면 로그 전체를 스캔한다.

```sql
SELECT eventTime, awsRegion, eventSource, eventName,
       sourceIPAddress, userAgent, errorCode
FROM cloudtrail_logs
WHERE userIdentity.accessKeyId = 'AKIAIOSFODNN7EXAMPLE'
  AND eventTime >= '2026-10-01'
ORDER BY eventTime;
```

### 평소와 다른 점 찾기

공격자가 쓴 호출 하나하나는 정상 호출과 구분되지 않는다. 구분되는 것은 호출이 나온 환경이다. 같은 키에 대해 IP, userAgent, 리전을 묶어 처음과 마지막 시각, 횟수를 보면 평소 쓰던 환경과 새로 나타난 환경이 갈린다.

```sql
SELECT sourceIPAddress,
       regexp_extract(userAgent, '^[^/ ]+') AS client,
       awsRegion,
       COUNT(*) AS calls,
       MIN(eventTime) AS first_seen,
       MAX(eventTime) AS last_seen
FROM cloudtrail_logs
WHERE userIdentity.accessKeyId = 'AKIAIOSFODNN7EXAMPLE'
  AND eventTime >= '2026-09-01'
GROUP BY 1, 2, 3
ORDER BY first_seen;
```

| 단서 | 정상 | 의심 |
|---|---|---|
| sourceIPAddress | 사무실 NAT, 서버 EIP 대역 | 처음 보는 해외 IP, VPN·Tor 출구 노드 |
| userAgent | 서버 키인데 `Boto3` 또는 `aws-sdk-java` | 서버용 키에 `aws-cli`, 브라우저 문자열, `Pacu`·`ScoutSuite` 같은 도구 이름 |
| awsRegion | 서비스가 쓰는 리전 | 한 번도 안 쓴 리전의 `RunInstances` |
| 시간대 | 업무 시간 또는 배치 주기 | 새벽에 갑자기 시작, 분 단위로 촘촘한 호출 |

서버 애플리케이션용 키가 `aws-cli`로 호출됐다면 사람이 손으로 쳤다는 뜻이다. 애플리케이션이 쓰던 userAgent가 바뀌었다는 것만으로도 조사할 근거가 된다. IP는 VPN 때문에 단독 근거가 못 되고, userAgent는 공격자가 바꿀 수 있어서 둘 다 보조 증거로만 쓴다.

### 정찰 호출 패턴

탈취 직후에는 이 키가 살아 있는지, 무엇을 할 수 있는지를 확인하는 호출이 몰려 나온다. 서버 키는 평소에 `GetCallerIdentity`를 호출하지 않는 경우가 많아서 이 호출이 나오는 것만으로도 눈에 띈다. `GetCallerIdentity`는 권한이 없어도 항상 성공하기 때문에 공격자가 키 생존 확인용으로 가장 먼저 쓴다.

```sql
SELECT eventTime, eventName, sourceIPAddress, errorCode
FROM cloudtrail_logs
WHERE userIdentity.accessKeyId = 'AKIAIOSFODNN7EXAMPLE'
  AND eventName IN (
    'GetCallerIdentity', 'ListBuckets', 'DescribeInstances',
    'ListUsers', 'ListRoles', 'ListAttachedUserPolicies',
    'GetAccountAuthorizationDetails', 'DescribeSecurityGroups'
  )
  AND eventTime >= '2026-10-01'
ORDER BY eventTime;
```

짧은 시간 안에 서로 다른 서비스의 List·Describe가 이어지고 중간에 `AccessDenied`가 섞여 있으면 권한을 하나씩 두드려 보는 중이다. `errorCode`가 있는 행의 비율이 높은 구간을 잡으면 정찰이 시작된 시각을 특정할 수 있고, 그 시각이 유출 시점의 하한이 된다.

### AssumeRole 체인 따라가기

공격자가 키로 `AssumeRole`을 호출하면 이후 활동은 원래 키가 아니라 `ASIA`로 시작하는 임시 자격증명으로 나온다. 앞의 키로만 필터링하면 여기서 추적이 끊긴다. `AssumeRole` 응답에 새 임시 키 ID가 들어 있으므로 그것을 꺼내 다시 필터링한다.

```sql
SELECT eventTime, eventName, sourceIPAddress,
       json_extract_scalar(requestParameters, '$.roleArn') AS role_arn,
       regexp_extract(responseElements,
         '"accessKeyId"\s*:\s*"(ASIA[A-Z0-9]+)"', 1) AS temp_key
FROM cloudtrail_logs
WHERE eventName = 'AssumeRole'
  AND userIdentity.accessKeyId = 'AKIAIOSFODNN7EXAMPLE'
  AND eventTime >= '2026-10-01'
ORDER BY eventTime;
```

나온 `temp_key`를 위의 첫 쿼리 조건에 넣어 다시 돌린다. 그 역할이 또 다른 역할을 맡았으면 같은 일을 반복한다. 임시 자격증명의 이벤트는 `userIdentity.sessionContext.sessionIssuer.arn`에 원래 역할이 찍히므로, 역할 기준으로 먼저 훑고 싶으면 이 필드로 필터링해도 된다. 다른 계정의 역할로 이동했다면 로그는 그쪽 계정 Trail에 있다. 조직 Trail이 없으면 그 계정 소유자에게 로그를 받아야 한다.

### 지속 경로 확인

조사 중에 가장 놓치기 쉬운 것은 키를 회수해도 공격자가 다른 진입로를 이미 만들어 뒀다는 점이다. 키를 비활성화하기 전에 아래 호출이 있었는지 먼저 확인한다.

```sql
SELECT eventTime, userIdentity.accessKeyId, eventName,
       requestParameters, responseElements
FROM cloudtrail_logs
WHERE eventName IN (
    'CreateAccessKey', 'CreateUser', 'CreateLoginProfile',
    'UpdateLoginProfile', 'AttachUserPolicy', 'PutUserPolicy',
    'UpdateAssumeRolePolicy', 'CreateRole'
  )
  AND eventTime >= '2026-10-01'
ORDER BY eventTime;
```

`CreateAccessKey`의 `requestParameters.userName`이 다른 사용자라면 그 사용자도 오염된 것이다. 새로 생긴 키도 같은 방식으로 이어서 추적한다.

### 로그가 꺼졌거나 조작됐을 때

공격자가 권한이 충분하면 마지막에 `StopLogging`, `DeleteTrail`, `UpdateTrail`, `PutEventSelectors`로 흔적을 줄이려 한다. 이 호출들도 호출되는 순간에는 이벤트로 남는다. 먼저 이 이벤트를 찾고, 그 시각 이후 로그를 믿을 수 있는지를 따로 판단한다.

```sql
SELECT eventTime, userIdentity.arn, userIdentity.accessKeyId,
       eventName, awsRegion, sourceIPAddress
FROM cloudtrail_logs
WHERE eventSource = 'cloudtrail.amazonaws.com'
  AND eventName IN ('StopLogging', 'DeleteTrail', 'UpdateTrail',
                    'PutEventSelectors', 'PutInsightSelectors')
  AND eventTime >= '2026-10-01'
ORDER BY eventTime;
```

Trail 상태를 확인하는 순서는 아래 도식과 같다. Trail이 살아 있으면 Digest 검증으로, 지워졌으면 Event History로 넘어간다.

```mermaid
flowchart TD
    S["의심 시각 이후 로그가 비어 있다"] --> Q{"Trail이 존재하고<br/>IsLogging이 true인가"}
    Q -->|"아니오"| E["Event History에서<br/>StopLogging · DeleteTrail 검색"]
    Q -->|"예"| V["validate-logs로<br/>Digest 검증"]
    V --> R{"실패 · 누락 파일이 있는가"}
    R -->|"예"| B["로그 버킷의 DeleteObject ·<br/>버킷 정책 변경 이력 확인"]
    R -->|"아니오"| O["다른 리전 Trail ·<br/>조직 Trail에 같은 구간이 있는지 확인"]
    E --> O
```

Trail이 지워졌다면 S3의 로그는 이미 없을 수 있다. 이때는 Event History가 마지막 수단이다. Trail과 무관하게 리전별로 90일치 관리 이벤트를 따로 갖고 있어서, `lookup-events`로 `StopLogging`이나 `DeleteTrail`을 직접 찾을 수 있다.

```bash
aws cloudtrail describe-trails --include-shadow-trails
aws cloudtrail get-trail-status --name my-audit-trail
```

`get-trail-status`에서 `IsLogging`이 `false`이거나 `LatestDeliveryTime`이 오래전이면 그 시각부터 구멍이 있다. `LatestDeliveryError`, `LatestDigestDeliveryError`가 채워져 있으면 버킷 정책이나 KMS 권한이 바뀌어 전달이 막힌 것이다.

| 확인할 것 | 보는 이유 |
|---|---|
| Log file validation | `validate-logs`로 S3의 로그 파일이 지워졌거나 바뀌었는지 확인한다. Digest 파일이 끊긴 시간대가 있으면 그 구간이 의심 대상이다. 이 옵션을 안 켜고 만든 Trail은 검증 자체가 안 된다. |
| 조직 트레일 | 멤버 계정에서는 조직 Trail을 중지하거나 삭제할 수 없다. 멤버 계정 Trail은 조용히 꺼져도 조직 Trail에는 같은 기간 이벤트가 그대로 남아 있다. |
| 다른 리전 트레일 | 멀티 리전이 아닌 Trail은 만든 리전만 본다. 공격자가 안 쓰던 리전에서 활동했다면 그 리전에 Trail이 있는지, `describe-trails --include-shadow-trails`에 잡히는지 본다. |
| 로그 버킷 자체 | 버킷에 `DeleteObject`나 `PutBucketPolicy`가 있었는지 본다. 버전 관리와 MFA Delete가 꺼져 있으면 지워진 로그는 복구할 방법이 없다. |

가장 안전한 구성은 로그를 별도 계정 버킷으로 보내고, 그 계정에는 일반 운영 권한을 주지 않는 것이다. 운영 계정이 뚫려도 공격자가 지울 수 있는 것은 운영 계정 쪽 Trail 설정뿐이고, 조직 Trail이 그 구간을 이미 다른 곳에 쌓아 둔다.

---

## 운영 문제 해결

### S3 버킷 삭제 범인 찾기

버킷이 갑자기 없어졌을 때 삭제 시간 근방을 먼저 좁히고 Athena로 확인한다.

```sql
SELECT
  eventTime,
  userIdentity.userName,
  userIdentity.arn,
  userIdentity.type,
  sourceIPAddress,
  userAgent,
  requestParameters
FROM cloudtrail_logs
WHERE eventName = 'DeleteBucket'
  AND eventTime >= '2026-09-27'
ORDER BY eventTime DESC;
```

삭제 주체가 `userIdentity.type = 'AssumedRole'`이면 사람이 아닌 서비스나 자동화다. `userIdentity.sessionContext.sessionIssuer.arn`에서 원래 역할을 확인하고, 해당 역할을 어떤 서비스가 맡고 있는지 추적한다.

### 비용 급증 원인 파악

특정 날짜 이후 비용이 튀었다면 그날 이후 생성된 리소스를 먼저 확인한다.

```sql
SELECT
  eventTime,
  eventSource,
  eventName,
  awsRegion,
  userIdentity.arn,
  requestParameters
FROM cloudtrail_logs
WHERE eventName LIKE 'Create%'
  AND eventTime >= '2026-09-21'
  AND errorCode IS NULL
ORDER BY eventTime DESC;
```

`ec2.amazonaws.com`의 RunInstances가 갑자기 많이 나오면서 평소와 다른 리전에서 발생했다면 크립토 마이닝 공격 가능성이 있다. awsRegion 컬럼을 확인해 비인가 리전 활동이 있는지 본다.

### 접근 거부 오류로 서비스 장애

애플리케이션이 갑자기 AWS 서비스에 접근하지 못하면 권한 변경이 원인인 경우가 많다.

```sql
SELECT
  eventTime,
  eventSource,
  eventName,
  userIdentity.arn,
  errorCode,
  errorMessage
FROM cloudtrail_logs
WHERE errorCode IN ('AccessDenied', 'UnauthorizedOperation')
  AND eventTime >= '2026-09-28T00:00:00Z'
ORDER BY eventTime DESC;
```

errorMessage에 "is not authorized to perform"이 있으면 거부된 액션이 나온다. 같은 시간대에 해당 역할/정책을 누가 수정했는지 IAM 정책 변경 쿼리와 교차해서 본다.

---

## 규정 준수 감사

### 미사용 IAM 계정 파악

PCI DSS와 SOX는 최소 권한 원칙 준수를 증명해야 한다. 특정 기간 동안 실제로 활동한 IAM 사용자 목록을 뽑고, 전체 IAM 사용자 목록과 비교해 미사용 계정을 찾는다.

```sql
-- 최근 90일 동안 활동이 있었던 IAM 사용자 목록
SELECT DISTINCT userIdentity.userName
FROM cloudtrail_logs
WHERE userIdentity.type = 'IAMUser'
  AND eventTime >= '2026-07-01'
  AND eventTime < '2026-10-01'
  AND userIdentity.userName IS NOT NULL
ORDER BY userIdentity.userName;
```

이 목록에 없는 IAM 사용자가 90일 이상 미사용 계정이다. IAM Credential Report와 함께 보면 마지막 로그인 시간도 확인할 수 있다.

### 프로덕션 변경 이력 추출

변경 관리 프로세스를 운영하는 경우, 특정 기간의 인프라 변경 내역을 뽑아 변경 요청 기록과 대조한다.

```sql
-- 특정 기간 읽기 이벤트를 제외한 실제 변경 이력
SELECT
  eventTime,
  userIdentity.arn,
  eventSource,
  eventName,
  awsRegion,
  requestParameters
FROM cloudtrail_logs
WHERE eventTime >= '2026-09-01'
  AND eventTime < '2026-10-01'
  AND errorCode IS NULL
  AND eventName NOT LIKE 'Describe%'
  AND eventName NOT LIKE 'List%'
  AND eventName NOT LIKE 'Get%'
ORDER BY eventTime;
```

월 단위로 뽑아 감사 보고서에 첨부하는 방식으로 쓴다. 읽기 전용 이벤트(Describe, List, Get)를 제외하면 실제 상태를 변경한 이벤트만 남는다.

### 개인정보 접근 추적

GDPR 대응 환경에서는 개인정보가 담긴 S3 버킷에 데이터 이벤트를 활성화하고, 아래 쿼리로 정기 리포트를 생성한다.

```sql
SELECT
  eventTime,
  userIdentity.arn,
  eventName,
  requestParameters,
  sourceIPAddress
FROM cloudtrail_logs
WHERE eventSource = 's3.amazonaws.com'
  AND eventName IN ('GetObject', 'PutObject', 'DeleteObject')
  AND requestParameters LIKE '%pii-data-bucket%'
  AND eventTime >= '2026-09-01'
ORDER BY eventTime;
```

---

## CloudWatch Logs 연동

Athena 쿼리 없이 실시간 알람이 필요하면 Trail을 CloudWatch Logs로 연동한다.

```bash
# CloudWatch Logs 그룹 생성
aws logs create-log-group --log-group-name /aws/cloudtrail/my-trail

# Trail에 CloudWatch Logs 연동
aws cloudtrail update-trail \
  --name my-audit-trail \
  --cloud-watch-logs-log-group-arn arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/cloudtrail/my-trail:* \
  --cloud-watch-logs-role-arn arn:aws:iam::123456789012:role/CloudTrail-CloudWatchLogs-Role

# 루트 계정 로그인 메트릭 필터
aws logs put-metric-filter \
  --log-group-name /aws/cloudtrail/my-trail \
  --filter-name RootAccountLogin \
  --filter-pattern '{ $.userIdentity.type = "Root" && $.eventName = "ConsoleLogin" && $.responseElements.ConsoleLogin = "Success" }' \
  --metric-transformations '[
    {
      "metricName": "RootLoginCount",
      "metricNamespace": "CloudTrailMetrics",
      "metricValue": "1"
    }
  ]'

# 알람 생성
aws cloudwatch put-metric-alarm \
  --alarm-name root-account-login \
  --alarm-description "루트 계정 콘솔 로그인 감지" \
  --metric-name RootLoginCount \
  --namespace CloudTrailMetrics \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:security-alerts
```

CloudWatch Logs 전송은 추가 비용이 발생한다. 모든 이벤트를 전송하면 대용량 환경에서 비용이 빠르게 올라간다. 루트 계정 활동이나 IAM 변경처럼 고위험 이벤트만 메트릭 필터로 잡고, 나머지는 Athena 쿼리로 사후 분석하는 방식이 현실적이다.

---

## 비용

### 이벤트 유형별 요금

| 이벤트 유형 | 요금 | 비고 |
|---|---|---|
| 관리 이벤트 | 첫 번째 Trail 무료 | 두 번째 Trail부터 100,000건당 $2.00 |
| 데이터 이벤트 | 100,000건당 $0.10 | - |
| 인사이트 이벤트 | 100,000건당 $0.35 | 분석 대상 관리 이벤트 볼륨 기준 |
| CloudTrail Lake 수집 | GB당 $2.50 | 약 7만 이벤트/GB |
| CloudTrail Lake 쿼리 | TB당 $0.005 | - |

### 환경별 예상 비용

개발자 30명, EC2 50대, S3 버킷 30개 규모의 환경 기준이다.

관리 이벤트는 첫 Trail에서 무료지만 S3 저장 비용이 발생한다. 관리 이벤트만으로 월 50만~200만 건 정도 나오고, S3 저장 비용은 월 $5~20 수준이다.

데이터 이벤트가 변수다. S3 버킷 30개를 전부 켜면 트래픽에 따라 하루 수천만~수억 건이 발생할 수 있다. 100만 건/일이면 월 약 $3이지만, 10억 건/일이면 월 $3,000이다. 민감한 버킷 3~5개만 선택적으로 켜는 게 현실적이다.

### S3 저장 비용 절감

로그를 장기 보관하면서 비용을 줄이려면 S3 생명주기 정책으로 오래된 로그를 Glacier로 이전한다.

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-cloudtrail-logs-123456789012 \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "cloudtrail-archive",
        "Status": "Enabled",
        "Filter": {"Prefix": "AWSLogs/"},
        "Transitions": [
          {
            "Days": 90,
            "StorageClass": "STANDARD_IA"
          },
          {
            "Days": 365,
            "StorageClass": "GLACIER"
          }
        ]
      }
    ]
  }'
```

90일 이후 Standard-IA($0.0125/GB), 365일 이후 Glacier($0.004/GB)로 이전한다. 1년치 로그가 100GB라면 Standard 대비 연간 약 $20 절감된다.

---

## AWS Config와의 차이

운영하다 보면 두 서비스를 혼동하는 경우가 있다.

**CloudTrail**은 "누가 무엇을 했는가"를 기록한다. API 호출 이력이다. "누가 보안 그룹을 변경했나"는 CloudTrail이 답한다.

**AWS Config**는 "리소스의 상태가 어떻게 변했는가"를 기록한다. "보안 그룹에 어떤 인바운드 규칙이 추가됐나"는 Config가 답한다.

보안 침해를 조사할 때는 CloudTrail로 행위자와 시간을 특정하고, Config로 그 결과로 리소스 설정이 어떻게 바뀌었는지 확인하는 방식으로 함께 쓴다.
