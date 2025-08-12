---
title: AWS CloudWatch
tags: [aws, monitoring-and-management, cloudwatch]
updated: 2025-08-10
---


# 🌩 AWS CloudWatch 개념 및 설명

## 1️⃣ AWS CloudWatch란?
**AWS CloudWatch**는 AWS 리소스와 애플리케이션을 모니터링할 수 있는 서비스입니다.  
실시간으로 로그, 지표(Metric), 이벤트를 수집하고 분석할 수 있으며, 이를 통해 장애 대응 및 성능 최적화를 할 수 있습니다.

---

## 2️⃣ CloudWatch의 주요 기능
### ✅ 1. 지표(Metrics) 모니터링
- **CloudWatch Metrics**를 사용하여 CPU, 메모리, 디스크 사용량 등을 확인할 수 있습니다.
- EC2, RDS, Lambda 같은 AWS 서비스에서 기본 제공하는 지표뿐만 아니라, **사용자 정의(Custom) 지표**도 설정 가능합니다.

### ✅ 2. 로그(Log) 관리
- **CloudWatch Logs**를 사용하면 애플리케이션 및 시스템 로그를 수집하고 저장할 수 있습니다.
- 로그 데이터를 쿼리하여 특정 이벤트를 분석할 수도 있습니다.

### ✅ 3. 알람(Alarm) 설정
- 특정 조건을 설정하면 자동으로 알람을 트리거할 수 있습니다.
- 예를 들어, CPU 사용률이 80%를 초과하면 **SNS(Simple Notification Service)** 를 통해 알림을 받을 수 있습니다.

### ✅ 4. 대시보드(Dashboard) 제공
- CloudWatch 대시보드를 사용하면 지표와 로그를 한눈에 확인할 수 있습니다.
- 맞춤형 대시보드를 만들어서 원하는 정보만 모아서 볼 수도 있습니다.

### ✅ 5. 이벤트(Event) 관리
- 특정 이벤트(예: EC2 인스턴스 시작/중지, S3 객체 업로드 등)에 따라 자동으로 작업을 수행할 수 있습니다.
- **CloudWatch Events(현재 EventBridge로 통합됨)** 을 사용하여 Lambda, SNS, SQS 등과 연계할 수 있습니다.

---

## 3️⃣ CloudWatch Metrics 예제

## 배경
```python
import boto3










# CloudWatch 클라이언트 생성
cloudwatch = boto3.client('cloudwatch')

# EC2 인스턴스의 CPU 사용률 가져오기
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',  # 서비스 네임스페이스
    MetricName='CPUUtilization',  # 지표 이름
    Dimensions=[
        {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
    ],
    StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=10),  # 10분 전 데이터부터 조회
    EndTime=datetime.datetime.utcnow(),  # 현재 시간까지 데이터 조회
    Period=60,  # 60초 간격
    Statistics=['Average']  # 평균값 조회
)

print(response)
```
> 위 코드는 특정 EC2 인스턴스의 CPU 사용률을 조회하는 예제입니다.

---

## 4️⃣ CloudWatch Logs 설정 및 활용

### ✅ CloudWatch Logs를 사용한 로그 수집

AWS에서 **EC2 인스턴스**의 로그를 CloudWatch로 전송하려면 **CloudWatch Agent**를 설정해야 합니다.

### ✨ CloudWatch Logs Agent 설치
```bash
# Amazon Linux 또는 Ubuntu 기준
sudo yum install -y amazon-cloudwatch-agent
```

### ✨ CloudWatch Logs에 로그 전송 설정하기
```json
{
  "agent": {
    "metrics_collection_interval": 60,
    "logfile": "/var/log/myapp.log"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/myapp.log",
            "log_group_name": "my-app-logs",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```
> 위 설정은 `/var/log/myapp.log` 파일을 CloudWatch Logs로 전송하도록 설정합니다.

---

## 5️⃣ CloudWatch Alarm 설정

### ✅ CloudWatch Alarm 생성
```python
response = cloudwatch.put_metric_alarm(
    AlarmName='HighCPUUtilization',
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Statistic='Average',
    Period=300,  # 5분 간격
    EvaluationPeriods=2,  # 2번 연속 조건 충족 시 알람 발생
    Threshold=80.0,  # CPU 사용률 80% 이상일 때 알람 발생
    ComparisonOperator='GreaterThanThreshold',
    Dimensions=[
        {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
    ],
    AlarmActions=['arn:aws:sns:us-east-1:123456789012:my-sns-topic']
)
print("Alarm Created:", response)
```
> 위 코드는 CPU 사용률이 80%를 초과하면 **SNS를 통해 알람을 보내는 예제**입니다.

---

## 6️⃣ CloudWatch Events 설정

### ✅ 특정 이벤트 발생 시 Lambda 트리거하기
```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["stopped"]
  }
}
```
> 위 이벤트 패턴은 **EC2 인스턴스가 중지될 때 Lambda를 실행하는 트리거를 설정**하는 예제입니다.

---

## 7️⃣ CloudWatch 요금 계산

- **CloudWatch는 사용량 기반 요금제**로 작동합니다.
- 무료 티어가 제공되지만, 일정량을 초과하면 요금이 부과됩니다.
- 요금은 **수집한 로그 양, 모니터링한 지표 개수, 생성한 알람 개수**에 따라 달라집니다.

