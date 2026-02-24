---
title: AWS Budgets
tags: [aws, budgets, cost, alert, notification, threshold]
updated: 2026-01-18
---

# AWS Budgets

## 개요

AWS Budgets는 비용 알림 서비스다. 예산을 설정하고 초과 시 알림을 받는다. 비용, 사용량, RI/Savings Plans 커버리지를 추적한다. 자동 조치를 실행한다 (인스턴스 중지, Lambda 호출).

### 왜 필요한가

청구서를 받고 나서 알면 늦다.

**문제 상황:**

**시나리오:**
개발자가 테스트 중 r5.8xlarge 인스턴스 20개를 실행했다. 종료를 깜빡했다.

**시간당 비용:**
20 × $2.016 = $40.32/시간

**하루:**
$40.32 × 24 = $967.68

**1주일:**
$967.68 × 7 = $6,773.76

**월말 청구서를 받고 발견:**
손실: $6,773.76

**AWS Budgets의 해결:**
- 일일 예산 $100 설정
- $100 초과 시 즉시 알림
- 첫날 발견하고 인스턴스 종료
- 손실: $967 (하루치만)

**99% 손실 방지**

## 예산 타입

### Cost Budget

실제 비용을 추적한다.

**사용 사례:**
- 월 예산 $3,000
- $2,700 (90%) 도달 시 경고
- $3,000 초과 시 위험 알림

### Usage Budget

사용량을 추적한다 (시간, GB 등).

**사용 사례:**
- EC2 사용 시간: 1,000 시간/월
- 800 시간 도달 시 알림

### Reservation Budget

RI/Savings Plans 활용률을 추적한다.

**사용 사례:**
- RI 활용률 목표: 90%
- 80% 이하로 떨어지면 알림

## Cost Budget 생성

### 월간 예산

**콘솔:**
1. Billing 콘솔
2. "Budgets" 클릭
3. "Create budget"
4. Template: Monthly cost budget
5. Budget name: Production Monthly Budget
6. Budgeted amount: $3,000
7. Email recipients: admin@example.com, finance@example.com
8. Alert threshold: 
   - 85% ($2,550) - Warning
   - 100% ($3,000) - Critical
   - 120% ($3,600) - Over Budget
9. 생성

**동작:**
- 현재 비용이 $2,550 도달: Warning 이메일
- $3,000 도달: Critical 이메일
- $3,600 도달: Over Budget 이메일

### CLI로 생성

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**budget.json:**
```json
{
  "BudgetName": "Monthly-Cost-Budget",
  "BudgetLimit": {
    "Amount": "3000",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": ["user:Environment$Production"]
  }
}
```

**notifications.json:**
```json
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 85,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "admin@example.com"
      }
    ]
  },
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "finance@example.com"
      },
      {
        "SubscriptionType": "SNS",
        "Address": "arn:aws:sns:us-west-2:123456789012:billing-alerts"
      }
    ]
  }
]
```

## 예측 알림

미래 비용을 예측해서 알림을 보낸다.

**시나리오:**
- 오늘: 1월 15일
- 현재 비용: $1,800
- 예산: $3,000/월
- 예측: $3,600 (120%)

**예측 알림:**
"현재 추세로 가면 월말에 $3,600이 될 예정입니다."

**조치:**
미리 비용 절감 작업을 시작한다.

**설정:**
```json
{
  "Notification": {
    "NotificationType": "FORECASTED",
    "ComparisonOperator": "GREATER_THAN",
    "Threshold": 100,
    "ThresholdType": "PERCENTAGE"
  }
}
```

## 필터링

특정 리소스만 추적한다.

### 서비스별 예산

**EC2만:**
```json
{
  "CostFilters": {
    "Service": ["Amazon Elastic Compute Cloud - Compute"]
  }
}
```

EC2 비용만 추적. 예산: $1,500/월

### 태그별 예산

**프로덕션만:**
```json
{
  "CostFilters": {
    "TagKeyValue": ["user:Environment$Production"]
  }
}
```

**팀별:**
```json
{
  "CostFilters": {
    "TagKeyValue": ["user:Team$Backend"]
  }
}
```

Backend 팀 비용만 추적. 예산: $1,000/월

### 리전별 예산

```json
{
  "CostFilters": {
    "Region": ["us-west-2"]
  }
}
```

## 자동 조치

예산 초과 시 자동으로 작업을 실행한다.

### EC2 인스턴스 중지

**시나리오:**
개발 환경 예산 $500/월. 초과 시 모든 개발 인스턴스 중지.

**Lambda 함수:**
```python
import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # 개발 환경 인스턴스 찾기
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Environment', 'Values': ['Development']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if instance_ids:
        ec2.stop_instances(InstanceIds=instance_ids)
        print(f"Stopped {len(instance_ids)} instances")
    
    return {'statusCode': 200}
```

**SNS → Lambda 연결:**
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-west-2:123456789012:budget-alerts \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-west-2:123456789012:function:stop-dev-instances
```

**Budget 알림:**
예산 100% 초과 시 SNS로 알림 → Lambda 자동 실행.

### Slack 알림

```python
import json
import urllib.request

def lambda_handler(event, context):
    message_text = event['Records'][0]['Sns']['Message']
    budget_data = json.loads(message_text)
    
    budget_name = budget_data['budgetName']
    threshold = budget_data['threshold']
    actual = budget_data['actual']
    
    slack_message = {
        "text": f"⚠️ 예산 알림: {budget_name}",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "임계값", "value": f"{threshold}%", "short": True},
                {"title": "실제 비용", "value": f"${actual}", "short": True}
            ]
        }]
    }
    
    req = urllib.request.Request(
        "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        data=json.dumps(slack_message).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    urllib.request.urlopen(req)
    
    return {'statusCode': 200}
```

## Usage Budget

### EC2 사용 시간

**예산:**
- EC2 사용 시간: 2,000 시간/월
- 임계값: 1,800 시간 (90%)

**계산:**
- t3.medium 10개 × 24시간 × 30일 = 7,200 시간
- 실제 사용: 1,850 시간 (일부 인스턴스 중지)

**알림:**
1,800 시간 도달 시 경고.

**생성:**
```json
{
  "BudgetName": "EC2-Usage-Budget",
  "BudgetLimit": {
    "Amount": "2000",
    "Unit": "HOURS"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "USAGE",
  "CostFilters": {
    "Service": ["Amazon Elastic Compute Cloud - Compute"]
  }
}
```

### S3 저장 용량

**예산:**
- S3 저장: 1 TB/월
- 임계값: 900 GB (90%)

**사용:**
현재 저장: 950 GB

**알림:**
900 GB 초과. 불필요한 파일 삭제 또는 Glacier 이동.

## Reservation Budget

### RI 활용률

**시나리오:**
- RI 구매: t3.medium 10개 (1년)
- 목표 활용률: 90%
- 실제 활용률: 75%

**문제:**
RI를 충분히 활용하지 못한다. 돈을 낭비한다.

**Budget 설정:**
```json
{
  "BudgetName": "RI-Utilization",
  "BudgetLimit": {
    "Amount": "90",
    "Unit": "PERCENT"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "RI_UTILIZATION",
  "CostFilters": {
    "Service": ["Amazon Elastic Compute Cloud - Compute"]
  }
}
```

**알림:**
활용률이 90% 미만이면 경고.

**조치:**
- 사용하지 않는 인스턴스 찾기
- RI에 맞춰 인스턴스 타입 변경
- 또는 RI 판매

### Savings Plans 커버리지

**목표:**
전체 사용량의 80%를 Savings Plans로 커버.

**현재:**
70% 커버리지.

**Budget:**
```json
{
  "BudgetName": "Savings-Plans-Coverage",
  "BudgetLimit": {
    "Amount": "80",
    "Unit": "PERCENT"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "SAVINGS_PLANS_COVERAGE"
}
```

**알림:**
80% 미만이면 추가 Savings Plans 구매 검토.

## 다중 예산

여러 예산을 동시에 관리한다.

**예시:**

**1. 전체 예산:**
- 모든 서비스
- $10,000/월

**2. 서비스별 예산:**
- EC2: $4,000/월
- RDS: $2,000/월
- S3: $500/월

**3. 환경별 예산:**
- Production: $7,000/월
- Staging: $2,000/월
- Development: $1,000/월

**4. 팀별 예산:**
- Backend: $5,000/월
- Frontend: $3,000/월
- Data: $2,000/월

각 예산이 독립적으로 추적된다. 중복 허용.

## 실무 사용

### 스타트업

**상황:**
- 초기 예산 제한
- 월 $5,000 이하 유지 필요

**Budget 설정:**
- 월 예산: $5,000
- 85% ($4,250): 팀 알림
- 100% ($5,000): CTO 알림
- 110% ($5,500): 자동 개발 환경 중지

**효과:**
예산 초과 방지. 비용 통제.

### 중견 기업

**상황:**
- 여러 팀, 여러 프로젝트
- 팀별로 예산 할당

**Budget 설정:**
- Backend 팀: $10,000/월
- Frontend 팀: $5,000/월
- Data 팀: $15,000/월

**효과:**
팀별 비용 책임. 투명한 비용 관리.

### 대기업

**상황:**
- 여러 계정 (Organizations)
- 계정별 예산

**Budgets in Master Account:**
- 전체 조직: $500,000/월
- 계정별 예산 (50개 계정)

**효과:**
중앙 집중식 비용 관리. 계정별 추적.

## 비용

### Budgets 자체 비용

**무료:**
- 처음 2개 예산

**유료:**
- $0.02 per budget per day
- $0.60/월 per budget
- $7.20/년 per budget

**예시:**
- 10개 예산
- 비용: (10 - 2) × $0.60 = $4.80/월

저렴하다. 비용 초과 방지 효과가 훨씬 크다.

### ROI

**예산 비용:**
10개 예산 × $0.60 = $6/월

**방지한 손실:**
테스트 인스턴스 방치: $6,773

**ROI:**
$6,773 / $6 = 1,129배

## 모범 사례

### 여러 임계값

**권장:**
- 50%: 정보
- 85%: 경고
- 100%: 위험
- 120%: 긴급

단계별로 대응한다.

### 예측 + 실제

**실제 알림:**
현재 비용 추적.

**예측 알림:**
미래 비용 예측.

둘 다 설정한다. 미리 대응한다.

### 환경별 분리

**프로덕션:**
- 엄격한 예산
- 경고만 (자동 중지 금지)

**개발:**
- 느슨한 예산
- 초과 시 자동 중지

### 정기 검토

**월말:**
- 예산 vs 실제 비교
- 다음 달 예산 조정
- 불필요한 Budget 삭제

## 참고

- AWS Budgets 가이드: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- Budgets API: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_Operations_AWS_Budgets.html
- 비용 최적화: https://aws.amazon.com/pricing/cost-optimization/

