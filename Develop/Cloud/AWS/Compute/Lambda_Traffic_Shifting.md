---
title: Lambda 무중단 배포 — Traffic Shifting
tags: [aws, lambda, alias, traffic-shifting, canary, codedeploy, sam, cdk, serverless]
updated: 2026-08-06
---

# Lambda 무중단 배포 — Traffic Shifting

Lambda는 서버리스라서 배포가 쉬울 것 같지만, 운영 트래픽이 붙은 함수를 교체하는 일은 EC2 롤링 배포만큼 섬세하게 다뤄야 한다. 새 코드를 올리는 순간 $LATEST가 바뀌고, 그 함수를 직접 호출하는 클라이언트가 있다면 오류가 즉시 퍼진다. alias와 weighted routing을 쓰면 트래픽을 점진적으로 옮기면서 문제가 생기면 즉시 이전 버전으로 되돌릴 수 있다.

## version과 alias

Lambda 함수를 배포하면 `$LATEST`라는 변경 가능한 포인터가 생긴다. 여기서 특정 시점의 코드를 고정하면 숫자 버전(1, 2, 3...)이 만들어진다. 버전은 한 번 게시되면 코드도, 런타임도, 환경 변수도 바꿀 수 없다. 불변이다.

alias는 이 버전 위에 이름을 붙인 포인터다. `production`, `staging`, `v2-canary` 같은 이름으로 특정 버전을 가리키고, 가중치를 주면 두 버전에 트래픽을 분산할 수 있다.

```bash
# 버전 게시
aws lambda publish-version \
  --function-name my-api \
  --description "feat: add retry logic"

# alias 생성 — 처음엔 버전 1에 100%
aws lambda create-alias \
  --function-name my-api \
  --name production \
  --function-version 1

# 버전 2로 10% 트래픽 이동
aws lambda update-alias \
  --function-name my-api \
  --name production \
  --function-version 2 \
  --routing-config AdditionalVersionWeights={"1"=0.9}
```

`--function-version 2`가 메인(90%)이고, `AdditionalVersionWeights`에 넣은 버전 1이 나머지다. 헷갈리기 쉬운 부분이다. alias는 "주 버전"과 "추가 버전" 두 슬롯만 지원하고, 두 가중치의 합이 반드시 1.0이 되어야 한다.

클라이언트는 alias ARN을 호출 대상으로 쓴다. `arn:aws:lambda:ap-northeast-2:123456789:function:my-api:production` 형태다. 클라이언트 코드를 건드리지 않아도 alias가 내부에서 트래픽을 분산한다.

주의할 점이 있다. alias에서 weighted routing을 쓰면 같은 요청 내에서 버전이 섞이지는 않는다. 요청 단위로 버전이 결정된다. 근데 한 번의 요청 안에서 람다가 람다를 호출하는 구조라면, 외부 요청은 버전 2를 타더라도 내부 호출이 $LATEST를 보고 있으면 행동이 달라질 수 있다. 내부 호출도 alias ARN을 쓰도록 통일해야 한다.

## CodeDeploy로 배포 자동화

alias 가중치를 손으로 바꾸는 건 스크립트 한두 줄이면 되지만, 배포 도중 오류 감지와 롤백까지 묶으려면 CodeDeploy를 쓰는 게 현실적이다.

CodeDeploy는 Lambda deployment group을 만들고, 배포 설정(deployment config)에 따라 가중치를 자동으로 조정한다.

### 배포 설정 비교

| Config | 동작 |
|--------|------|
| `LambdaCanary10Percent5Minutes` | 10% → 5분 대기 → 이상 없으면 나머지 90% 한 번에 |
| `LambdaLinear10PercentEvery1Minute` | 10분에 걸쳐 10%씩 증가, 총 10단계 |
| `LambdaAllAtOnce` | 즉시 100% 전환, 사실상 무중단 아님 |

Canary는 초기 검증 구간이 필요한 경우에 쓴다. 10%에서 5분을 버티면 나머지를 한 번에 넘긴다. 단계가 둘뿐이라 배포 속도가 빠르다. Linear는 단계가 많아서 오류를 더 세밀하게 감지할 수 있지만, 전체 배포 완료까지 10분이 걸린다. SLA가 빡빡한 환경에선 Canary를 주로 쓰게 된다.

`AllAtOnce`는 사실 무중단 배포가 아니다. 단지 CodeDeploy 파이프라인을 통해 배포하는 것뿐이고, 전환 자체는 순간적으로 일어난다. 개발 환경이나 테스트 목적 외에는 잘 안 쓴다.

커스텀 config를 만들면 비율과 간격을 조정할 수 있다.

```bash
aws deploy create-deployment-config \
  --deployment-config-name LambdaCanary20Percent10Minutes \
  --compute-platform Lambda \
  --traffic-routing-config '{
    "type": "TimeBasedCanary",
    "timeBasedCanary": {
      "canaryPercentage": 20,
      "canaryInterval": 10
    }
  }'
```

## 라이프사이클 훅

CodeDeploy는 배포 전후에 Lambda 함수를 실행할 수 있는 훅을 두 개 제공한다. `BeforeAllowTraffic`과 `AfterAllowTraffic`이다.

`BeforeAllowTraffic`은 트래픽이 새 버전으로 넘어가기 전에 실행된다. DB 스키마 호환성 확인, warm-up 요청 발송, 외부 의존성 연결 테스트 같은 사전 검증을 여기서 한다.

`AfterAllowTraffic`은 배포 완료 후에 실행된다. 스모크 테스트, 메트릭 샘플링, 알림 발송이 여기 들어간다.

훅 Lambda는 반드시 `put_lifecycle_event_hook_execution_status`를 호출해서 성공/실패를 CodeDeploy에 알려야 한다. 이걸 빠뜨리면 배포가 기본 1시간 타임아웃까지 멈춘 채로 기다린다.

```python
import boto3
import os

codedeploy = boto3.client('codedeploy')

def handler(event, context):
    deployment_id = event['DeploymentId']
    lifecycle_event_hook_execution_id = event['LifecycleEventHookExecutionId']

    try:
        # 사전 검증 로직
        validate_new_version()

        codedeploy.put_lifecycle_event_hook_execution_status(
            deploymentId=deployment_id,
            lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
            status='Succeeded'
        )
    except Exception as e:
        print(f"validation failed: {e}")
        codedeploy.put_lifecycle_event_hook_execution_status(
            deploymentId=deployment_id,
            lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
            status='Failed'
        )
        raise


def validate_new_version():
    # 새 버전 함수 ARN은 환경 변수나 event에서 꺼낼 수 있다
    # 여기선 내부 헬스체크 엔드포인트 호출 예시
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName=os.environ['NEW_VERSION_ARN'],
        InvocationType='RequestResponse',
        Payload=b'{"action": "healthcheck"}'
    )
    if response['StatusCode'] != 200:
        raise ValueError(f"health check failed: {response['StatusCode']}")
```

`status`는 `'Succeeded'`와 `'Failed'` 두 값만 쓴다. `Failed`를 보내면 CodeDeploy가 즉시 롤백을 시작한다.

훅 Lambda에도 IAM 권한이 필요하다. 실행 역할에 `codedeploy:PutLifecycleEventHookExecutionStatus`를 붙여야 한다. 이걸 빠뜨리면 훅이 AccessDeniedException으로 터지고, 타임아웃까지 배포가 멈춘다.

## CloudWatch 알람 연동 자동 롤백

CodeDeploy는 배포 중 CloudWatch 알람이 울리면 자동으로 롤백하는 기능을 제공한다. 배포가 진행되는 동안 알람 상태를 주기적으로 체크하고, `ALARM` 상태가 되면 rollback event를 트리거한다.

```bash
# 배포 그룹 생성 시 알람 연동
aws deploy create-deployment-group \
  --application-name my-lambda-app \
  --deployment-group-name production \
  --service-role-arn arn:aws:iam::123456789:role/CodeDeployRole \
  --deployment-config-name LambdaCanary10Percent5Minutes \
  --alarm-configuration '{
    "enabled": true,
    "alarms": [
      {"name": "lambda-error-rate-high"},
      {"name": "lambda-p99-latency-high"}
    ]
  }' \
  --auto-rollback-configuration '{
    "enabled": true,
    "events": ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }'
```

알람 설정에서 자주 하는 실수가 있다. 알람 이름을 잘못 적거나, 알람 자체가 존재하지 않으면 CodeDeploy는 에러를 내지 않고 알람 없이 그냥 배포를 진행한다. 콘솔에서 deployment group 상세를 열면 알람 연동 상태를 확인할 수 있다.

Lambda 함수용 알람은 주로 두 가지를 쓴다.

```bash
# 오류율 알람 — 5분 내 오류 10건 초과
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-error-rate-high \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=my-api Name=Resource,Value=my-api:production \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 5 \
  --threshold 10 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching

# P99 지연 알람 — 3분 내 P99가 3초 초과
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-p99-latency-high \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=my-api Name=Resource,Value=my-api:production \
  --extended-statistic p99 \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 3000 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching
```

`Resource` 차원에 alias ARN 포맷(`function-name:alias-name`)을 쓰면 alias 단위로 메트릭이 잡힌다. 이 부분을 빠뜨리면 함수 전체 메트릭이 나와서 특정 alias의 오류를 알람으로 잡기 어려워진다.

## SAM에서 alias 트래픽 분배

SAM은 `AutoPublishAlias`와 `DeploymentPreference`로 위 설정을 선언적으로 관리한다.

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  MyApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: my-api
      CodeUri: src/
      Handler: app.handler
      Runtime: python3.12
      AutoPublishAlias: production
      DeploymentPreference:
        Type: Canary10Percent5Minutes
        Alarms:
          - !Ref LambdaErrorAlarm
          - !Ref LambdaLatencyAlarm
        Hooks:
          PreTraffic: !Ref PreTrafficHook
          PostTraffic: !Ref PostTrafficHook

  PreTrafficHook:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: CodeDeployHook_pre-traffic-my-api
      CodeUri: hooks/
      Handler: pre_traffic.handler
      Runtime: python3.12
      DeploymentPreference:
        Enabled: false
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action: codedeploy:PutLifecycleEventHookExecutionStatus
              Resource: '*'

  LambdaErrorAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: lambda-error-rate-high
      Namespace: AWS/Lambda
      MetricName: Errors
      Dimensions:
        - Name: FunctionName
          Value: my-api
        - Name: Resource
          Value: !Sub "my-api:production"
      Statistic: Sum
      Period: 60
      EvaluationPeriods: 5
      Threshold: 10
      ComparisonOperator: GreaterThanOrEqualToThreshold
      TreatMissingData: notBreaching
```

`AutoPublishAlias`를 선언하면 `sam deploy` 실행 때마다 새 버전이 자동으로 게시되고, 지정한 alias가 업데이트된다. `DeploymentPreference`에 `Type`을 쓰면 CodeDeploy application과 deployment group을 SAM이 알아서 만들어준다.

훅 Lambda의 이름이 `CodeDeployHook_`으로 시작해야 한다는 제약이 있다. CodeDeploy가 훅 함수 이름으로 권한을 검증하기 때문에 이 프리픽스를 빠뜨리면 훅 호출이 실패한다.

## CDK에서 alias 트래픽 분배

```typescript
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as codedeploy from 'aws-cdk-lib/aws-codedeploy';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';

const fn = new lambda.Function(this, 'MyApiFunction', {
  functionName: 'my-api',
  runtime: lambda.Runtime.PYTHON_3_12,
  code: lambda.Code.fromAsset('src'),
  handler: 'app.handler',
});

// 버전 게시 — 코드나 설정이 바뀔 때마다 새 버전
const version = fn.currentVersion;

// alias 생성
const alias = new lambda.Alias(this, 'ProductionAlias', {
  aliasName: 'production',
  version,
});

// CloudWatch 알람
const errorAlarm = new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
  alarmName: 'lambda-error-rate-high',
  metric: alias.metricErrors({
    period: cdk.Duration.minutes(1),
    statistic: 'Sum',
  }),
  threshold: 10,
  evaluationPeriods: 5,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
});

// 훅 Lambda
const preTrafficHook = new lambda.Function(this, 'PreTrafficHook', {
  functionName: 'CodeDeployHook_pre-traffic-my-api',
  runtime: lambda.Runtime.PYTHON_3_12,
  code: lambda.Code.fromAsset('hooks'),
  handler: 'pre_traffic.handler',
});

preTrafficHook.addToRolePolicy(new iam.PolicyStatement({
  actions: ['codedeploy:PutLifecycleEventHookExecutionStatus'],
  resources: ['*'],
}));

// CodeDeploy 연동
new codedeploy.LambdaDeploymentGroup(this, 'DeploymentGroup', {
  alias,
  deploymentConfig: codedeploy.LambdaDeploymentConfig.CANARY_10PERCENT_5MINUTES,
  alarms: [errorAlarm],
  preHook: preTrafficHook,
  autoRollback: {
    failedDeployment: true,
    stoppedDeployment: true,
    deploymentInAlarm: true,
  },
});
```

CDK에서 `fn.currentVersion`은 함수 코드나 설정이 변경될 때마다 새 Version 리소스를 생성한다. 변경이 없으면 같은 버전을 재사용한다. `alias.metricErrors()`처럼 alias 단위 메트릭 헬퍼를 쓰면 Resource 차원이 자동으로 들어간다.

## 배포 실패 디버깅

배포가 실패하거나 롤백됐을 때 원인을 찾는 과정이다.

**alias routing 확인**

```bash
# 현재 alias 상태 확인
aws lambda get-alias \
  --function-name my-api \
  --name production

# 응답 예시
{
  "FunctionVersion": "3",
  "RoutingConfig": {
    "AdditionalVersionWeights": {
      "2": 0.1
    }
  }
}
```

`FunctionVersion`이 메인(90%)이고, `AdditionalVersionWeights`에 있는 게 카나리(10%)다. 배포 도중에 이 값을 주기적으로 찍어보면 가중치가 의도대로 변하는지 확인할 수 있다.

**CodeDeploy 배포 상태 확인**

```bash
# 최근 배포 목록
aws deploy list-deployments \
  --application-name my-lambda-app \
  --deployment-group-name production \
  --query 'deployments' \
  --output text

# 배포 상세 — 훅 실행 결과 포함
aws deploy get-deployment \
  --deployment-id d-XXXXXXXXX

# 배포 실패 원인 (lifecycle events)
aws deploy get-deployment-instance \
  --deployment-id d-XXXXXXXXX \
  --instance-id XXXXX
```

훅이 타임아웃됐는지, `put_lifecycle_event_hook_execution_status` 호출이 실패했는지는 `get-deployment` 응답의 `lifecycleEventList`에서 확인할 수 있다.

**배포 롤백 후 alias가 이전 버전인지 확인**

롤백이 완료됐는데도 alias가 바뀌지 않은 것처럼 보이는 경우가 있다. CodeDeploy가 alias를 원래 버전으로 되돌리는 데 몇 초 걸리기 때문이다. `get-alias`를 다시 호출해서 `RoutingConfig`에 가중치가 없고, `FunctionVersion`이 이전 버전인지 확인한다.

**로그 확인**

alias 단위로 로그가 구분되지는 않는다. 버전 번호가 로그에 찍히지 않기 때문에 카나리 단계에서 어떤 버전의 오류인지 구분하려면 코드 안에서 버전을 로깅해야 한다.

```python
import os

def handler(event, context):
    # context.function_version으로 현재 실행 버전 확인
    print(f"function_version={context.function_version}")
    # ...
```

`context.function_version`은 실행 중인 버전 번호를 반환한다. 카나리 중에 로그를 보면 `function_version=2`와 `function_version=3`이 섞여서 나온다. 오류 로그에 버전이 찍혀 있으면 새 버전에서 발생한 건지 바로 판별할 수 있다.
