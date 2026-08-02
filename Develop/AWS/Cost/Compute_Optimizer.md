---
title: AWS Compute Optimizer
tags: [aws, cost, compute-optimizer, ec2, lambda, ecs, ebs, right-sizing, savings-plans]
updated: 2026-07-25
---

# AWS Compute Optimizer

## 개요

Compute Optimizer는 EC2 인스턴스, EBS 볼륨, Lambda 함수, ECS on Fargate 태스크의 실제 사용 메트릭을 분석해서 적정 사이즈 권고를 내놓는 서비스다. ML 모델이 CloudWatch 지표를 14일치 기본(최대 93일치 확장) 학습하고, "현재 이 인스턴스는 과대 사양이다" 또는 "이 볼륨은 IOPS가 부족해서 성능 위험이 있다"는 형태로 결론을 낸다.

Cost Explorer의 Rightsizing Recommendations와 혼동하기 쉬운데, 그 기능이 Compute Optimizer를 내부 엔진으로 쓴다. Cost Explorer 화면에서 보는 Rightsizing은 비용 절감 숫자만 보여주는 요약판이고, Compute Optimizer 콘솔에서 직접 보면 CPU 사용률 그래프, 메모리 사용률, 네트워크 성능, 추천 이유까지 훨씬 상세하게 나온다.

활성화 자체는 무료 티어가 있다. 14일치 분석은 추가 비용 없이 쓸 수 있고, 확장 분석(Inferred Workload Types, 외부 메트릭 통합)은 리소스당 월 0.0003달러 수준의 추가 요금이 붙는다. 계정이 많은 Organizations 환경에서 멤버 계정 전체에 활성화하면 비용이 쌓이기는 하지만, 절감액 대비로는 거의 무시할 수 있는 수준이다.

## Trusted Advisor와 차이

클라우드 비용 최적화 도구로 Trusted Advisor도 있어서 혼동이 잦다. 결론부터 말하면 두 서비스는 역할이 다르다.

Trusted Advisor는 계정 수준 점검을 한다. "m3 계열 인스턴스는 지원이 끊기니 마이그레이션해라", "S3 버킷 퍼블릭 접근이 열려 있다", "사용 중인 서비스 중 제한에 근접한 항목이 있다" 같은 폭넓은 권고를 준다. EC2 Rightsizing 관련 항목도 있지만 분석 깊이가 얕다. CPU 사용률이 낮다는 정도의 신호만 잡는다.

Compute Optimizer는 Rightsizing에 특화돼 있다. 단순히 CPU 평균이 낮다는 사실만 보는 게 아니라 CPU 버스팅 패턴, 메모리 사용률(CloudWatch Agent 수집 시), 네트워크 성능, EBS 처리량, Lambda 실행 시간 분포를 같이 본다. 권고의 신호 대 잡음비가 훨씬 높다.

Trusted Advisor의 Cost Optimization 탭을 보고 전체 비용 건강도를 먼저 파악하고, 개별 인스턴스/함수 수준 최적화는 Compute Optimizer로 들어가는 순서가 자연스럽다.

| 항목 | Trusted Advisor | Compute Optimizer |
|---|---|---|
| 분석 범위 | 계정 전반(보안·성능·비용·서비스 한도) | EC2·EBS·Lambda·ECS Fargate Rightsizing |
| 분석 깊이 | 얕음(기본 CloudWatch 메트릭) | 깊음(ML + 14~93일 메트릭 학습) |
| 메모리 사용률 | 미포함 | CloudWatch Agent 설치 시 포함 |
| 무료 여부 | Business/Enterprise Support 이상 | 기본 무료(확장 분석은 유료) |
| 권고 방향 | 폭넓음 | Rightsizing 전문 |

## 지원 리소스와 분석 조건

### EC2

14일 이상 실행된 인스턴스가 대상이다. 기본 분석은 CloudWatch의 CPU 사용률과 네트워크 성능 지표를 본다. 메모리 사용률은 기본 분석에 포함되지 않는다. CloudWatch Agent를 설치해서 `mem_used_percent` 메트릭을 수집해야 Compute Optimizer가 메모리까지 고려한 권고를 낸다.

실무에서 메모리 메트릭 없이 나오는 권고는 신뢰도가 떨어진다. CPU가 20%라고 해서 인스턴스를 절반으로 줄였더니 메모리 부족으로 애플리케이션이 죽는 상황이 생긴다. 특히 Java 기반 서비스는 CPU보다 Heap 사이즈가 인스턴스 선택의 기준이라 메모리 메트릭 없이는 권고를 그대로 따르면 안 된다.

CloudWatch Agent 설정은 SSM Parameter Store에 올려두고 Fleet Manager로 일괄 배포하는 방식이 관리하기 편하다.

```json
{
  "metrics": {
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}"
    },
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["disk_used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["/"]
      }
    }
  }
}
```

### EBS

권고 대상은 gp2, gp3, io1, io2 볼륨이다. IOPS와 처리량 사용률을 본다. 과도하게 프로비저닝된 볼륨(io1을 10,000 IOPS로 프로비저닝했는데 실제는 500 IOPS만 쓰는 경우)과, 반대로 성능 한계에 근접한 볼륨(gp2 볼륨이 burst credit을 지속 소진 중인 경우)을 모두 잡는다.

gp2에서 gp3로 전환하는 권고가 자주 나온다. gp3는 기본 IOPS(3,000)와 처리량(125 MB/s)이 gp2보다 낫고 가격도 20% 저렴하다. 대부분의 경우 인스턴스를 중지하지 않고 볼륨 타입을 그 자리에서 바꿀 수 있다.

### Lambda

권고는 메모리 사이즈 조정이다. Lambda는 메모리 설정이 CPU 할당과 비례하기 때문에, 메모리를 줄이면 실행 시간이 늘어나서 실제 비용이 오히려 오를 수 있다. Compute Optimizer는 "메모리 X MB에서 Y MB로 낮춰도 실행 시간이 Z% 증가하는 데 그쳐서 순 비용은 절감된다" 같은 계산을 같이 보여준다.

반대로 메모리를 올리는 권고도 나온다. 메모리가 부족해서 실행 시간이 길어지는 경우다. 128 MB 함수가 1.5초 실행되는데 메모리를 256 MB로 올리면 0.6초에 끝나서 비용이 더 저렴해지는 패턴은 Lambda에서 꽤 흔하다.

### ECS on Fargate

태스크 정의의 CPU와 메모리 예약(reservation) 사이즈를 분석한다. 태스크가 실제로 쓰는 CPU와 메모리를 CloudWatch Container Insights 메트릭으로 보고, 예약 대비 사용률이 낮으면 다운사이즈 권고를 낸다. Container Insights가 활성화되어 있어야 분석이 가능하다.

## ML 기반 예측 정확도의 한계

Compute Optimizer 권고를 그대로 따랐다가 문제가 생기는 경우는 패턴이 있다.

**버스팅 워크로드 오인식.** 평소에는 CPU 10~15%를 유지하다가 매일 오전 9시에 배치 작업이 돌면서 90%까지 치솟는 인스턴스가 있다. 14일 평균으로 보면 CPU 평균은 25% 수준이고, Compute Optimizer는 과대 사양이라고 판단한다. 피크 구간만 보면 현재 인스턴스 사이즈가 필요하다. 권고의 "maximum"과 "average" 수치를 같이 봐야 하는 이유다.

**메모리와 CPU의 불균형.** r5.large(16 GB 메모리)를 쓰는 서비스가 있고, CPU는 15%인데 메모리는 75%를 쓴다. Compute Optimizer가 CPU만 보면 m5.large(8 GB)로 다운 권고가 나온다. 바꾸면 메모리 부족이 난다. 메모리 메트릭 없이는 이런 상황을 걸러내지 못한다.

**학습 기간 문제.** 마케팅 캠페인 직후나, 크론잡을 막 추가한 직후처럼 최근 2주가 비정상적인 패턴이었으면 그 기간 기준으로 권고가 만들어진다. 반대로 평소보다 트래픽이 낮은 성수기 직후 비수기 데이터로 학습되면 과소 사양으로 권고가 나올 수 있다.

**유의미한 트래픽 분산.** 동일한 사이즈 인스턴스 여러 개 중 일부만 높은 부하를 받고, 나머지는 유휴 상태인 경우다. 부하분산이 고르지 않은 환경에서 인스턴스 단위 권고는 개별 인스턴스 지표만 보기 때문에 전체 맥락을 놓친다.

권고를 볼 때 "Risk" 지표를 먼저 확인한다. `Very Low`, `Low`, `Medium`, `High`로 표시되는데, 권고 신뢰도를 나타낸다. `Medium` 이상이면 메트릭 그래프를 직접 열어서 피크 패턴을 확인한 다음 판단한다.

## 권고 수락 전 검증 방법

권고를 바로 적용하는 대신 단계를 밟는 게 안전하다.

**1단계: 메트릭 그래프 직접 확인.**

Compute Optimizer 콘솔에서 권고를 클릭하면 CPU, 네트워크, 메모리(수집된 경우) 그래프가 14일치로 나온다. 평균 외에 P99 값을 보는 것이 중요하다. P99 CPU가 80%를 넘어가는 인스턴스를 사이즈 다운하면 피크 시간에 스로틀링이 생긴다.

```bash
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:ap-northeast-2:123456789012:instance/i-0abcd1234ef567890 \
  --query 'instanceRecommendations[0].utilizationMetrics'
```

`utilizationMetrics` 배열에서 `statistic` 값이 `MAXIMUM`인 항목을 먼저 본다. Average만 낮고 Maximum이 높으면 피크 대역이 있다.

**2단계: 스테이징에서 먼저 적용.**

운영 인스턴스를 바로 바꾸지 않는다. 동일한 AMI와 같은 크기의 권장 타입으로 스테이징 인스턴스를 하나 띄우고, 실제 트래픽을 일부 라우팅해서 성능 지표를 비교한다. ALB 가중치 라우팅이나 Auto Scaling Group 내 Launch Template 버전 전환으로 할 수 있다.

**3단계: 무중단 타입 변경.**

EC2 인스턴스 타입 변경은 중지 후 변경이다. 오토스케일링 그룹이라면 Launch Template을 업데이트하고 인스턴스를 하나씩 교체하는 방식으로 무중단으로 진행된다.

```bash
# Launch Template 새 버전 생성
aws ec2 create-launch-template-version \
  --launch-template-id lt-0abc123def456 \
  --source-version 1 \
  --launch-template-data '{"InstanceType":"m5.large"}'

# ASG에 최신 버전 적용
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name my-asg \
  --launch-template LaunchTemplateId=lt-0abc123def456,Version='$Latest'

# 인스턴스 순차 교체
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name my-asg \
  --preferences MinHealthyPercentage=90,InstanceWarmup=300
```

**4단계: 변경 후 모니터링 기간.**

타입 변경 직후 최소 1주일은 CloudWatch 알람을 빡빡하게 잡아둔다. CPU, 메모리, 응답 시간, 5xx 오류율. 피크 타임을 한 번 이상 거친 뒤 문제가 없으면 확정한다.

## Savings Plans와 연동한 비용 절감 계산

Compute Optimizer 권고와 Savings Plans를 같이 쓰면 절감 효과가 겹쳐서 계산이 복잡해진다. 순서를 이해해야 실제 절감액을 제대로 계산할 수 있다.

### 적용 순서

Savings Plans 할인은 인스턴스 타입과 무관하게 온디맨드 시간당 요금에 대해 적용된다. 인스턴스를 사이즈 다운하면 시간당 요금이 줄어들고, 줄어든 요금 기준에 Savings Plans 할인율이 곱해진다.

예를 들어 m5.xlarge(온디맨드 $0.192/hr)를 m5.large($0.096/hr)로 줄이고, Compute Savings Plans로 30% 할인을 받는 경우를 계산해보면:

```
변경 전:
  m5.xlarge × Savings Plans 할인 = $0.192 × 0.70 = $0.1344/hr

변경 후:
  m5.large × Savings Plans 할인 = $0.096 × 0.70 = $0.0672/hr

월 절감 (720시간 기준):
  ($0.1344 - $0.0672) × 720 = $48.38/월/인스턴스
```

Compute Optimizer 권고 화면의 "Estimated monthly savings"는 Savings Plans 적용 전 요금으로 계산된 숫자를 보여주는 경우가 많다. 실제 절감액은 SP 할인율을 곱한 값이다. "그냥 권고 화면 숫자가 아니라 SP 적용 후 숫자를 봐야 한다"는 점을 놓치면 절감 효과를 과대평가한다.

### Savings Plans Coverage 변화

인스턴스를 사이즈 다운하면 기존에 구매한 Compute SP의 Coverage가 올라간다. 시간당 약정(예: $5/hr)은 그대로인데, 커버하는 실제 온디맨드 비용이 줄었기 때문이다. Coverage가 100%에 가까워지면 추가 약정 구매 효과가 생긴다는 의미다.

반대로 인스턴스를 잘못된 판단으로 다운했다가 다시 올리면 Coverage가 낮아진다. SP 약정을 추가 구매해야 할 수도 있다. 권고 적용 전에 현재 SP Coverage 리포트를 뽑아두는 편이 좋다.

```bash
aws ce get-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-07-25 \
  --granularity MONTHLY \
  --group-by Type=DIMENSION,Key=INSTANCE_FAMILY
```

### EC2 Instance SP와 Compute SP의 차이

EC2 Instance Savings Plans는 특정 인스턴스 패밀리와 리전이 고정된다. m5 패밀리 SP를 가지고 있는데 Compute Optimizer 권고를 따라 c6g로 옮기면 그 SP는 적용이 안 된다. Compute SP라면 패밀리가 바뀌어도 적용된다.

Rightsizing 권고가 패밀리 변경을 포함하는 경우(m5 → t3, 또는 m5 → c6g)라면 기존 EC2 Instance SP가 있으면 해당 SP 이용률이 떨어지는 부작용이 생긴다. 변경 전에 어떤 SP를 얼마나 사고 있는지 확인한다.

```bash
aws savingsplans describe-savings-plans \
  --states active \
  --query 'savingsPlans[*].[savingsPlanType,description,commitment,end]' \
  --output table
```

## API로 권고 가져오기

콘솔에서 보는 권고를 API로 빼서 자동화하는 패턴을 많이 쓴다. 매주 권고를 뽑아서 Jira 티켓을 자동으로 만들거나, 슬랙으로 보내거나, 팀별로 분류해서 담당자에게 배분하는 식이다.

```bash
# EC2 권고 전체 조회
aws compute-optimizer get-ec2-instance-recommendations \
  --query 'instanceRecommendations[*].{
    Instance:instanceArn,
    Finding:finding,
    CurrentType:currentInstanceType,
    RecommendedType:recommendationOptions[0].instanceType,
    MonthlySavings:recommendationOptions[0].estimatedMonthlySavings.value
  }' \
  --output table

# EBS 권고
aws compute-optimizer get-ebs-volume-recommendations \
  --query 'volumeRecommendations[*].{
    Volume:volumeArn,
    Finding:finding,
    CurrentType:currentConfiguration.volumeType,
    RecommendedType:volumeRecommendationOptions[0].configuration.volumeType
  }' \
  --output table

# Lambda 권고
aws compute-optimizer get-lambda-function-recommendations \
  --query 'lambdaFunctionRecommendations[*].{
    Function:functionArn,
    Finding:finding,
    CurrentMemory:currentMemorySize,
    RecommendedMemory:memorySizeRecommendationOptions[0].memorySize,
    MonthlySavings:memorySizeRecommendationOptions[0].projectedUtilizationMetrics[0].upperBoundValue
  }' \
  --output table
```

Python으로 Organizations 전체 계정에서 권고를 수집하는 예시다.

```python
import boto3
from typing import Generator

def iter_member_accounts(org_client) -> Generator[str, None, None]:
    paginator = org_client.get_paginator('list_accounts')
    for page in paginator.paginate():
        for account in page['Accounts']:
            if account['Status'] == 'ACTIVE':
                yield account['Id']

def get_ec2_recommendations(account_id: str, region: str) -> list:
    sts = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/ComputeOptimizerReadRole"
    creds = sts.assume_role(RoleArn=role_arn, RoleSessionName='optimizer-scan')
    
    co = boto3.client(
        'compute-optimizer',
        region_name=region,
        aws_access_key_id=creds['Credentials']['AccessKeyId'],
        aws_secret_access_key=creds['Credentials']['SecretAccessKey'],
        aws_session_token=creds['Credentials']['SessionToken'],
    )
    
    recs = []
    paginator = co.get_paginator('get_ec2_instance_recommendations')
    for page in paginator.paginate():
        for rec in page['instanceRecommendations']:
            if rec['finding'] == 'OVER_PROVISIONED' and rec['recommendationOptions']:
                best = rec['recommendationOptions'][0]
                recs.append({
                    'account': account_id,
                    'instance': rec['instanceArn'].split('/')[-1],
                    'current': rec['currentInstanceType'],
                    'recommended': best['instanceType'],
                    'savings': best.get('estimatedMonthlySavings', {}).get('value', 0),
                    'risk': best.get('performanceRisk'),
                })
    return recs
```

권고를 뽑을 때 `finding` 값으로 걸러낸다.

- `OVER_PROVISIONED`: 과대 사양. 다운사이즈 권고.
- `UNDER_PROVISIONED`: 과소 사양. 업사이즈 또는 성능 최적화 권고.
- `OPTIMIZED`: 적정.
- `NOT_OPTIMIZED`: EBS 전용. 설정 변경 여지가 있음.

`UNDER_PROVISIONED`는 비용이 오르더라도 적용하는 것을 고려해야 한다. 성능 병목이 있는 상태를 그냥 방치하면 장애로 이어진다.

## Organizations 환경에서의 설정

여러 계정을 운영한다면 Management 계정에서 Compute Optimizer를 Organizations 수준으로 활성화하는 편이 낫다. 멤버 계정 각각에서 따로 활성화하지 않아도 되고, Management 계정 한 곳에서 전체 권고를 볼 수 있다.

```bash
aws compute-optimizer update-enrollment-status \
  --status Active \
  --include-member-accounts
```

활성화 이후 멤버 계정의 CloudWatch 메트릭이 Compute Optimizer로 수집되기까지 최대 24시간 걸린다. 첫 권고가 나오기까지 약 14일이 필요하므로, 처음 활성화하고 바로 권고를 기대하면 안 된다.

## 실무에서의 활용 패턴

권고를 그냥 리스트로 보는 것보다 우선순위를 잡아서 처리하는 게 효율적이다.

절감액이 크고 Risk가 낮은 권고부터 처리한다. 절감액이 아무리 커도 Risk가 `Medium` 이상이면 메트릭을 먼저 검토한다. Risk가 `Low`이고 절감액이 큰 순서로 정렬하면 자연스럽게 우선순위가 잡힌다.

비프로덕션 환경에서 먼저 적용한다. 개발/스테이징 환경은 프로덕션보다 변경 비용이 낮다. 거기서 먼저 권고를 적용해서 문제가 없으면 프로덕션으로 가져오는 패턴이 안전하다.

패밀리 변경 권고는 별도로 검토한다. 같은 패밀리 내 사이즈 변경(m5.xlarge → m5.large)은 특성이 같아서 검증 부담이 낮다. 패밀리 자체가 바뀌는 경우(m5 → c6g, m5 → t3)는 버스트 크레딧 모델 차이, 아키텍처 차이(x86 → ARM), 네트워크 대역폭 차이가 있어서 별도로 테스트한다.

## 참고

- AWS Compute Optimizer 사용자 가이드: https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html
- EC2 인스턴스 권고 API: https://docs.aws.amazon.com/compute-optimizer/latest/APIReference/API_GetEC2InstanceRecommendations.html
- Lambda 권고 API: https://docs.aws.amazon.com/compute-optimizer/latest/APIReference/API_GetLambdaFunctionRecommendations.html
- EBS 권고 API: https://docs.aws.amazon.com/compute-optimizer/latest/APIReference/API_GetEBSVolumeRecommendations.html
- Savings Plans 타입 비교: https://docs.aws.amazon.com/savingsplans/latest/userguide/what-is-savings-plans.html
