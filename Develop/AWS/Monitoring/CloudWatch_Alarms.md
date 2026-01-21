---
title: AWS CloudWatch Alarms
tags: [aws, cloudwatch, alarms, monitoring, alerts, sns, autoscaling]
updated: 2026-01-22
---

# AWS CloudWatch Alarms

## 개요

CloudWatch Alarms는 메트릭을 모니터링하고 알림을 보낸다. CPU 사용률, 메모리, 에러율 등을 추적한다. 임계값을 초과하면 SNS로 알림을 보낸다. Auto Scaling을 트리거한다. EC2 인스턴스를 재부팅한다. Lambda 함수를 실행한다.

### 왜 필요한가

시스템 문제를 빠르게 감지해야 한다.

**문제 상황 1: 서버 과부하**

**상황:**
새벽 3시에 CPU 사용률이 95%로 급증한다. 서버가 응답하지 않는다. 고객이 불만을 제기한다. 아침에 출근해서 문제를 발견한다.

**손실:**
- 3시간 다운타임
- 고객 이탈
- 매출 손실

**CloudWatch Alarms의 해결:**
- CPU 사용률 80% 알람 설정
- SNS로 Slack/PagerDuty 연동
- 즉시 알림 받음
- 문제 해결 또는 Auto Scaling 자동 실행

**문제 상황 2: 에러 급증**

**상황:**
외부 API가 다운된다. 애플리케이션에서 500 에러가 급증한다. 사용자가 서비스를 이용할 수 없다.

**일반적인 대응:**
- 고객이 문의
- 로그 확인
- 원인 파악
- 대응

시간이 오래 걸린다.

**CloudWatch Alarms:**
- 에러율 5% 알람 설정
- 즉시 알림
- 빠른 대응 (외부 API Fallback 활성화)

## Alarm 생성

### 기본 설정

**콘솔:**
1. CloudWatch 콘솔
2. "Alarms" → "Create alarm"
3. "Select metric"
4. 메트릭 선택 (예: EC2 → Per-Instance Metrics → CPUUtilization)
5. 인스턴스 선택
6. "Select metric"

**조건 설정:**
- Threshold type: Static
- Whenever CPUUtilization is...: Greater than
- than...: 80

**기간:**
- Period: 5 minutes
- Datapoints to alarm: 2 out of 3

3개 데이터 포인트 중 2개가 80%를 넘으면 알람.

**Action:**
- Notification: SNS topic 선택
- 생성

**CLI:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu \
  --alarm-description "CPU usage exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --datapoints-to-alarm 2 \
  --dimensions Name=InstanceId,Value=i-12345678 \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:admin-alerts
```

## Alarm 상태

### OK

메트릭이 임계값 이하다. 정상 상태다.

### ALARM

메트릭이 임계값을 초과했다. 알람이 트리거된다.

### INSUFFICIENT_DATA

데이터가 부족하다. 판단할 수 없다.

**원인:**
- 메트릭이 아직 생성되지 않음
- 데이터 포인트가 충분하지 않음
- 인스턴스가 중지됨

## Statistic (통계)

### Average (평균)

기간 내 평균값.

**예시:**
5분 동안 CPU: 70%, 80%, 90%, 85%, 75%
Average: 80%

### Sum (합계)

기간 내 총합.

**예시:**
5분 동안 에러 수: 10, 15, 20, 25, 30
Sum: 100

### Maximum (최대)

기간 내 최대값.

**사용:**
- CPU 피크 감지
- 응답 시간 최악의 경우

### Minimum (최소)

기간 내 최소값.

### SampleCount (샘플 수)

데이터 포인트 개수.

### p99 (백분위수)

상위 1%를 제외한 최대값.

**예시:**
100개 요청의 응답 시간.
p99 = 99번째로 느린 요청의 시간.

**사용:**
평균보다 정확한 사용자 경험 측정.

## 실무 Alarms

### CPU 알람

**높은 CPU:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-warning \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=i-12345678 \
  --alarm-actions arn:aws:sns:...:warnings
```

CPU 80% 이상이 10분 지속되면 알림.

**매우 높은 CPU:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name critical-cpu \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 95 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=i-12345678 \
  --alarm-actions arn:aws:sns:...:critical
```

CPU 95% 이상이면 즉시 알림.

### 메모리 알람

**CloudWatch Agent 설치 필요:**
```bash
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U amazon-cloudwatch-agent.rpm
```

**설정 파일 (config.json):**
```json
{
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
```

**시작:**
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c file:config.json
```

**알람:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-memory \
  --metric-name mem_used_percent \
  --namespace CWAgent \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=i-12345678 \
  --alarm-actions arn:aws:sns:...:alerts
```

### 에러율 알람

**ALB 타겟 5xx 에러:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=LoadBalancer,Value=app/my-alb/1234567890abcdef \
  --alarm-actions arn:aws:sns:...:alerts
```

1분에 500 에러가 100개 이상이면 알림.

**Lambda 에러:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=order-processor \
  --alarm-actions arn:aws:sns:...:alerts
```

### RDS 연결 수

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name rds-high-connections \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DBInstanceIdentifier,Value=mydb \
  --alarm-actions arn:aws:sns:...:alerts
```

### SQS 큐 깊이

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name sqs-backlog \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=orders-queue \
  --alarm-actions arn:aws:sns:...:alerts
```

큐에 1,000개 이상 메시지가 쌓이면 알림. Consumer를 확장한다.

## Composite Alarms

여러 알람을 조합한다.

**예시:**
CPU와 메모리가 모두 높을 때만 알림.

```bash
# CPU 알람 생성
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu \
  --metric-name CPUUtilization \
  --threshold 80 \
  ...

# 메모리 알람 생성
aws cloudwatch put-metric-alarm \
  --alarm-name high-memory \
  --metric-name mem_used_percent \
  --threshold 85 \
  ...

# Composite 알람
aws cloudwatch put-composite-alarm \
  --alarm-name high-cpu-and-memory \
  --alarm-rule "ALARM(high-cpu) AND ALARM(high-memory)" \
  --alarm-actions arn:aws:sns:...:critical
```

**OR 조건:**
```bash
--alarm-rule "ALARM(high-cpu) OR ALARM(high-memory)"
```

CPU 또는 메모리 중 하나라도 높으면 알림.

## Actions

### SNS 알림

**SNS Topic 생성:**
```bash
aws sns create-topic --name system-alerts
```

**이메일 구독:**
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-west-2:123456789012:system-alerts \
  --protocol email \
  --notification-endpoint admin@example.com
```

이메일 확인 링크를 클릭한다.

**Slack 통합:**
- AWS Chatbot 사용
- SNS → Chatbot → Slack

### Auto Scaling

**CPU 높으면 인스턴스 추가:**
```bash
# Scaling Policy 생성
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-asg \
  --policy-name scale-up \
  --scaling-adjustment 1 \
  --adjustment-type ChangeInCapacity

# 알람에 연결
aws cloudwatch put-metric-alarm \
  --alarm-name high-cpu-scale \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=AutoScalingGroupName,Value=my-asg \
  --alarm-actions arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:...
```

CPU 80% 이상이면 인스턴스 1개 추가.

### EC2 Actions

**인스턴스 재부팅:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name instance-stuck \
  --metric-name StatusCheckFailed_System \
  --namespace AWS/EC2 \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=InstanceId,Value=i-12345678 \
  --alarm-actions arn:aws:automate:us-west-2:ec2:reboot
```

시스템 체크가 2회 실패하면 재부팅.

**인스턴스 복구:**
```bash
--alarm-actions arn:aws:automate:us-west-2:ec2:recover
```

하드웨어 장애 시 다른 호스트로 복구.

### Lambda 함수 실행

**Lambda 함수:**
```python
import boto3

def lambda_handler(event, context):
    # 알람 정보
    alarm = event['Records'][0]['Sns']['Message']
    
    # 조치 수행
    # 예: 캐시 클리어, 설정 변경, 외부 API 호출
    
    return {'statusCode': 200}
```

**SNS → Lambda 연결:**
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-west-2:123456789012:system-alerts \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-west-2:123456789012:function:alarm-handler
```

알람 발생 시 Lambda 실행.

## Alarm 상태 변경 알림

**OK → ALARM:**
문제 발생.

**ALARM → OK:**
문제 해결. 

**OK → INSUFFICIENT_DATA:**
데이터 부족. 인스턴스 중지 등.

**알림 설정:**
```bash
--alarm-actions arn:aws:sns:...:alerts         # ALARM 상태
--ok-actions arn:aws:sns:...:ok-notifications  # OK 상태
--insufficient-data-actions arn:aws:sns:...:warnings  # INSUFFICIENT_DATA
```

## 비용

### 알람 비용

**Standard:**
$0.10 per alarm per month

**High-resolution (1분 미만):**
$0.30 per alarm per month

**예시:**
- 알람 100개
- Standard: 100 × $0.10 = $10/월
- High-resolution 20개: 20 × $0.30 = $6/월
- 합계: $16/월

저렴하다. 제한 없이 만든다.

### 메트릭 비용

**Standard 메트릭:**
무료 (AWS 서비스 기본 메트릭)

**Custom 메트릭:**
$0.30 per metric per month

**예시:**
- Custom 메트릭 50개
- 비용: 50 × $0.30 = $15/월

## 알람 최적화

### 알람 피로도 방지

**문제:**
알람이 너무 많이 온다. 중요하지 않은 알람도 많다. 무시하게 된다.

**해결:**

**임계값 조정:**
- 너무 낮으면 false positive
- 너무 높으면 늦게 감지

**평가 기간 증가:**
- 1개 데이터 포인트: 일시적 스파이크도 알람
- 2-3개 데이터 포인트: 지속적인 문제만 알람

**우선순위 분리:**
- Critical (PagerDuty, 24/7)
- Warning (Slack, 근무 시간)
- Info (Email, 주간 리포트)

**예시:**
```bash
# Critical: CPU 95% 이상
aws cloudwatch put-metric-alarm \
  --alarm-name critical-cpu \
  --threshold 95 \
  --alarm-actions arn:aws:sns:...:pagerduty

# Warning: CPU 80% 이상
aws cloudwatch put-metric-alarm \
  --alarm-name warning-cpu \
  --threshold 80 \
  --alarm-actions arn:aws:sns:...:slack
```

### 시간 기반 알람

**야간에는 알람 조정:**
트래픽이 적다. 임계값을 낮춘다.

**EventBridge + Lambda:**
- 오전 8시: 임계값 80%
- 오후 6시: 임계값 60%

```python
import boto3

def lambda_handler(event, context):
    cloudwatch = boto3.client('cloudwatch')
    
    # 시간에 따라 임계값 변경
    hour = datetime.now().hour
    threshold = 80 if 8 <= hour < 18 else 60
    
    cloudwatch.put_metric_alarm(
        AlarmName='high-cpu',
        Threshold=threshold,
        ...
    )
```

## 참고

- CloudWatch Alarms 가이드: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- CloudWatch 요금: https://aws.amazon.com/cloudwatch/pricing/
- SNS 통합: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html
- Auto Scaling 통합: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-monitoring.html

