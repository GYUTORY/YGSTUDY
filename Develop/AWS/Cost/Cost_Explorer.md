---
title: AWS Cost Explorer
tags: [aws, cost, billing, cost-explorer, optimization, budget]
updated: 2026-01-18
---

# AWS Cost Explorer

## 개요

Cost Explorer는 AWS 비용을 분석하는 서비스다. 어디서 돈이 나가는지 확인한다. 서비스별, 리전별, 태그별로 비용을 조회한다. 미래 비용을 예측한다. 비용 최적화 권장 사항을 제공한다.

### 왜 필요한가

AWS 청구서를 받고 놀란다.

**문제 상황:**

**예상 비용: $500**
**실제 청구: $2,800**

**어디서 돈이 나갔나?**
- EC2인가?
- RDS인가?
- 데이터 전송인가?
- NAT Gateway인가?

청구서만으로는 알 수 없다. 서비스별로 나뉘어 있지만 세부 내역이 부족하다.

**Cost Explorer의 해결:**
- 일별 비용 추이
- 서비스별 비용 분석
- 리전별 비용 비교
- 태그별 비용 추적 (팀별, 프로젝트별)
- 비용 급증 구간 즉시 파악

## 기본 사용

### 콘솔 접근

1. Billing 콘솔
2. "Cost Explorer" 클릭
3. 처음 사용 시 활성화 필요 (무료)
4. 24시간 후 데이터 표시

### 기본 화면

**Monthly costs by service:**
- 이번 달 서비스별 비용
- EC2: $1,200
- RDS: $450
- S3: $80
- 데이터 전송: $320

**예시:**
EC2가 가장 비싸다. EC2 최적화부터 시작한다.

### 시간 범위 선택

**기본 제공:**
- Last 3 months
- Last 6 months
- Last 12 months
- Custom date range

**예시:**
지난 3개월을 선택한다. 트렌드를 파악한다.

```
11월: $2,100
12월: $2,400
1월: $2,800
```

비용이 계속 증가한다. 어디서 증가했는지 확인한다.

## 필터와 그룹화

### 서비스별 분석

**Service:**
EC2 선택.

**세부 비용:**
- EC2-Instances: $800
- EC2-Other: $150 (Elastic IP, EBS Snapshots 등)
- EBS: $250

EBS 스냅샷이 쌓이고 있을 수 있다.

### 리전별 분석

**Group by: Region**

```
us-west-2: $1,800
us-east-1: $600
ap-northeast-2: $400
```

us-west-2가 메인 리전이다. 다른 리전에서 불필요한 리소스가 있나 확인한다.

### 태그별 분석

**Group by: Tag**

**사전 준비:**
모든 리소스에 태그를 붙인다.

```
Environment: Production, Staging, Development
Team: Backend, Frontend, Data
Project: ProjectA, ProjectB
```

**분석:**
```
Production: $2,200
Staging: $300
Development: $300
```

프로덕션이 78%를 차지한다. 정상이다.

**팀별:**
```
Backend: $1,600
Frontend: $800
Data: $400
```

Backend 팀이 가장 많이 사용한다. 세부 분석이 필요하다.

### 인스턴스 타입별

**Group by: Instance Type**

```
t3.medium: $600
m5.large: $800
r5.xlarge: $400
```

r5.xlarge를 사용하는 곳이 있다. 메모리 최적화 인스턴스는 비싸다. 정말 필요한지 확인한다.

## 세부 분석

### EC2 비용 분해

**EC2를 선택하고 Group by: Usage Type**

```
BoxUsage:t3.medium: $600
BoxUsage:m5.large: $800
EBS:VolumeUsage: $250
DataTransfer-Out: $200
```

**발견:**
- 인스턴스: $1,400
- EBS: $250
- 데이터 전송: $200

데이터 전송이 $200이다. CloudFront를 사용하면 줄일 수 있다.

### RDS 비용 분해

**RDS를 선택하고 Group by: Database Engine**

```
MySQL: $300
PostgreSQL: $150
```

**Instance 타입:**
```
db.m5.large: $250
db.t3.medium: $200
```

db.m5.large를 사용 중이다. db.t3로 다운그레이드 가능한지 확인한다.

### 데이터 전송 비용

**Filter: Service = Data Transfer**

**Group by: From/To Location:**
```
us-west-2 to Internet: $180
us-west-2 to us-east-1: $120
```

**문제:**
리전 간 데이터 전송이 $120이다. 불필요한 교차 리전 호출이 있나 확인한다.

## 비용 예측

### Forecast

향후 3개월 비용을 예측한다.

**예측 결과:**
```
현재 (1월): $2,800
예측 (2월): $2,900
예측 (3월): $3,000
```

계속 증가한다. 조치가 필요하다.

### 예측 기반

**과거 6개월 데이터:**
- 평균 증가율
- 계절성
- 트렌드

**주의:**
새로운 서비스를 시작하면 예측이 부정확하다. 과거 패턴과 다르기 때문이다.

## 비용 최적화

### 절감 기회

**Rightsizing Recommendations:**
사용률이 낮은 인스턴스를 다운그레이드한다.

**예시:**
```
Instance: i-12345678
Type: m5.xlarge ($140/월)
CPU 평균: 15%
권장: m5.large ($70/월)
절감: $70/월 (50%)
```

**Reserved Instances:**
장기 사용 인스턴스를 예약한다.

**예시:**
```
현재: On-Demand t3.medium $30.4/월
RI (1년): $20.8/월 (31% 절감)
RI (3년): $14.6/월 (52% 절감)
```

### 태그 없는 리소스

**Filter: No tag**

```
EC2: 5개 인스턴스
EBS: 10개 볼륨
S3: 2개 버킷
```

누가 만들었는지, 무엇에 사용하는지 모른다. 삭제 가능한지 확인한다.

## 비용 이상 탐지

### Cost Anomaly Detection

비정상적인 비용 급증을 자동으로 감지한다.

**활성화:**
1. Cost Explorer
2. "Cost Anomaly Detection" 메뉴
3. "Create monitor"
4. Monitor name: Production Monitor
5. Evaluation: By service
6. Alert preference: $100 이상 이상치
7. SNS topic 선택
8. 생성

**동작:**
- 머신러닝으로 정상 패턴 학습
- 이상 탐지 시 즉시 알림
- 원인 자동 분석

**예시:**
```
알림: EC2 비용 이상 탐지
정상 범위: $1,000-$1,200
실제 비용: $2,400 (+100%)
원인: m5.4xlarge 인스턴스 10개 추가
```

실수로 인스턴스를 많이 만들었다. 즉시 종료한다.

## 커스텀 리포트

### 저장된 리포트

자주 보는 분석을 저장한다.

**예시 1: 팀별 월간 비용**
- Time range: Last 3 months
- Granularity: Monthly
- Group by: Tag (Team)
- Chart type: Stacked bar

**예시 2: 프로덕션 일별 비용**
- Time range: Last 30 days
- Granularity: Daily
- Filter: Tag (Environment=Production)
- Chart type: Line

**저장:**
1. 원하는 설정으로 분석
2. "Save report" 클릭
3. 이름 입력
4. 저장

**사용:**
"Saved reports" 메뉴에서 바로 접근.

### 예약 리포트

정기적으로 이메일을 받는다.

**설정:**
1. 리포트 저장
2. "Subscribe" 클릭
3. 빈도: Weekly (매주 월요일)
4. 이메일 주소 입력

매주 월요일 아침 비용 리포트를 받는다. 비용 변화를 추적한다.

## API 사용

### CLI로 비용 조회

**최근 3개월 비용:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2026-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

**출력:**
```json
{
  "ResultsByTime": [
    {
      "TimePeriod": { "Start": "2025-11-01", "End": "2025-11-30" },
      "Groups": [
        { "Keys": ["Amazon Elastic Compute Cloud"], "Metrics": { "BlendedCost": { "Amount": "1200.50" } } },
        { "Keys": ["Amazon Relational Database Service"], "Metrics": { "BlendedCost": { "Amount": "450.20" } } }
      ]
    }
  ]
}
```

### Python으로 비용 분석

```python
import boto3
from datetime import datetime, timedelta

ce = boto3.client('ce')

# 지난 30일 비용
end_date = datetime.now().date()
start_date = end_date - timedelta(days=30)

response = ce.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.strftime('%Y-%m-%d'),
        'End': end_date.strftime('%Y-%m-%d')
    },
    Granularity='DAILY',
    Metrics=['BlendedCost'],
    GroupBy=[
        {'Type': 'DIMENSION', 'Key': 'SERVICE'}
    ]
)

# 서비스별 총 비용
service_costs = {}
for result in response['ResultsByTime']:
    for group in result['Groups']:
        service = group['Keys'][0]
        cost = float(group['Metrics']['BlendedCost']['Amount'])
        service_costs[service] = service_costs.get(service, 0) + cost

# 상위 10개 서비스
top_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:10]
for service, cost in top_services:
    print(f"{service}: ${cost:.2f}")
```

### Lambda로 자동 리포트

매일 비용을 집계해서 Slack에 알림.

```python
import boto3
import json
import urllib.request
from datetime import datetime, timedelta

def lambda_handler(event, context):
    ce = boto3.client('ce')
    
    # 어제 비용
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': yesterday.strftime('%Y-%m-%d'),
            'End': today.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['BlendedCost']
    )
    
    total_cost = float(response['ResultsByTime'][0]['Total']['BlendedCost']['Amount'])
    
    # Slack 메시지
    message = {
        "text": f"💰 어제 ({yesterday}) AWS 비용: ${total_cost:.2f}"
    }
    
    req = urllib.request.Request(
        "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        data=json.dumps(message).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    urllib.request.urlopen(req)
    
    return {'statusCode': 200}
```

**EventBridge 스케줄:**
매일 오전 9시 실행.

```bash
aws events put-rule \
  --name daily-cost-report \
  --schedule-expression "cron(0 9 * * ? *)"

aws events put-targets \
  --rule daily-cost-report \
  --targets "Id=1,Arn=arn:aws:lambda:us-west-2:123456789012:function:cost-report"
```

## 비용 절감 실전

### 사례 1: 미사용 리소스 정리

**분석:**
Cost Explorer에서 EBS 비용이 $500/월.

**조사:**
```bash
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].[VolumeId,Size,CreateTime]' \
  --output table
```

**결과:**
20개 볼륨이 연결되지 않음 (available). 총 2 TB.

**조치:**
스냅샷 생성 후 볼륨 삭제.

**절감:**
$500 → $100 (스냅샷 비용만)
**월 $400 절감**

### 사례 2: 리전 간 데이터 전송

**분석:**
데이터 전송 비용 $300/월. 높다.

**조사:**
us-west-2 ↔ us-east-1 전송이 많다.

**원인:**
- 메인 서버: us-west-2
- RDS Read Replica: us-east-1
- 애플리케이션이 교차 조회

**조치:**
Read Replica를 us-west-2로 이전.

**절감:**
$300 → $50
**월 $250 절감**

### 사례 3: 인스턴스 다운사이징

**분석:**
EC2 비용 $1,200/월. 많다.

**Rightsizing Recommendations 확인:**
- m5.xlarge 5개 → m5.large 권장
- CPU 평균 20%

**조치:**
인스턴스 타입 변경.

**절감:**
$1,200 → $600
**월 $600 절감**

### 종합 절감

**총 절감: $1,250/월 ($15,000/년)**

간단한 분석과 조치만으로 50% 절감.

## 비용

### Cost Explorer 자체 비용

**무료:**
- 콘솔 사용
- 기본 리포트

**유료:**
- API 호출: $0.01 per request

**예시:**
- Lambda로 매일 API 호출 (30회/월)
- 비용: 30 × $0.01 = $0.30/월

거의 무료 수준.

## 참고

- Cost Explorer 가이드: https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- Cost Explorer API: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/
- 비용 최적화 가이드: https://aws.amazon.com/pricing/cost-optimization/
- Rightsizing: https://aws.amazon.com/compute-optimizer/

