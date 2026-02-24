---
title: AWS Auto Scaling
tags: [aws, auto-scaling, ec2, ecs, scaling, high-availability]
updated: 2026-01-18
---

# AWS Auto Scaling

## 개요

AWS Auto Scaling은 애플리케이션의 부하에 따라 리소스를 자동으로 조절하는 서비스다. 트래픽이 증가하면 인스턴스를 추가하고, 감소하면 제거한다. 수동 개입 없이 성능을 유지하면서 비용을 최적화한다.

### 왜 Auto Scaling이 필요할까

과거에는 서버 용량을 수동으로 관리했다. 이로 인해 많은 문제가 발생했다.

**수동 관리의 문제점:**

**1. 트래픽 급증 대응:**
금요일 저녁 8시, 쇼핑몰에 주문이 폭주한다. 서버 CPU가 95%까지 올라간다. 응답 시간이 5초에서 30초로 느려진다. 고객들이 불만을 토로한다.

담당자에게 전화가 온다. "서버를 추가해주세요!" 담당자가 AWS 콘솔에 로그인한다. 새 EC2 인스턴스를 시작한다. 로드 밸런서에 수동으로 등록한다. 이 모든 과정에 10분이 걸린다. 그 사이에 고객 100명이 포기하고 나간다.

**2. 트래픽 감소 후:**
자정이 지나고 트래픽이 줄어든다. 서버 10대가 실행 중인데 CPU 사용률이 5%다. 95%의 리소스가 낭비되고 있다. 하지만 담당자는 자고 있다. 서버는 아침까지 계속 실행된다. 8시간 동안 불필요한 비용이 발생한다.

**3. 예측의 어려움:**
다음 주에 TV 광고가 나간다. 트래픽이 얼마나 증가할까? 10배? 20배? 서버를 몇 대 준비해야 할까? 너무 적으면 서비스가 다운된다. 너무 많으면 비용이 낭비된다.

**4. 휴일과 야간:**
새벽 3시, 트래픽이 거의 없다. 하지만 낮 시간 트래픽을 위해 서버 10대가 계속 실행된다. 누가 새벽에 일어나서 서버를 줄일까? 주말도 마찬가지다. 월요일 아침까지 불필요한 서버가 실행된다.

**Auto Scaling의 해결:**

Auto Scaling은 이 모든 것을 자동화한다.

**자동 확장 (Scale Out):**
트래픽이 증가하면 자동으로 인스턴스를 추가한다. CPU 사용률이 70%를 넘으면 새 인스턴스를 시작한다. 로드 밸런서에 자동으로 등록한다. 사람의 개입이 필요 없다. 2-3분 안에 처리된다.

**자동 축소 (Scale In):**
트래픽이 감소하면 자동으로 인스턴스를 제거한다. CPU 사용률이 30% 아래로 떨어지면 인스턴스를 종료한다. 비용이 절감된다. 역시 사람의 개입이 필요 없다.

**예측 스케일링:**
과거 데이터를 분석해 트래픽 패턴을 학습한다. 평일 오전 9시에 트래픽이 증가한다는 것을 안다. 8시 50분에 미리 인스턴스를 추가한다. 사용자는 항상 빠른 응답을 경험한다.

**스케줄 스케일링:**
평일 오전 9시에 서버 10대로 증가한다. 오후 6시에 3대로 감소한다. 주말에는 2대만 유지한다. 모두 자동으로 처리된다.

### 자동화의 가치

**비용 절감:**
한 회사의 사례다. 평일 낮에는 서버 20대, 야간에는 5대가 필요하다. 수동 관리 시에는 항상 20대를 유지했다. 월 비용: $3,000. Auto Scaling 도입 후 평균 10대를 유지한다. 월 비용: $1,500. 50% 절감했다.

**가용성 향상:**
서버가 죽으면 Auto Scaling이 자동으로 새 서버를 시작한다. 사람이 알아채기도 전에 복구된다. 다운타임이 최소화된다.

**운영 부담 감소:**
담당자가 24시간 대기할 필요가 없다. 주말에도, 휴가 중에도 시스템이 알아서 동작한다. 담당자는 더 중요한 일에 집중할 수 있다.

## EC2 Auto Scaling 상세

EC2 인스턴스를 자동으로 관리하는 방법이다.

### Auto Scaling Group (ASG)

Auto Scaling Group은 EC2 인스턴스의 집합을 관리하는 논리적 그룹이다.

**ASG의 역할:**

**1. 인스턴스 개수 유지:**
원하는 개수(Desired Capacity)의 인스턴스를 항상 유지한다.

**예시:**
Desired Capacity가 3이라고 설정했다. 현재 3개의 인스턴스가 실행 중이다. 하나가 죽으면 어떻게 될까?

**동작 과정:**
1. Health Check가 인스턴스 장애를 감지한다
2. ASG가 인스턴스를 Unhealthy로 표시한다
3. 해당 인스턴스를 종료한다
4. 새 인스턴스를 시작한다
5. Health Check를 통과하면 서비스에 추가한다
6. 다시 3개의 인스턴스가 유지된다

이 모든 과정이 자동으로 진행된다. 2-3분이면 완료된다.

**2. 자동 복구:**
인스턴스에 문제가 생기면 자동으로 교체한다.

**문제 상황:**
- 인스턴스가 응답하지 않는다
- 애플리케이션이 계속 크래시된다
- Health Check에 계속 실패한다
- 하드웨어 장애가 발생한다

ASG가 이 모든 상황을 감지하고 자동으로 대응한다. 사람이 개입할 필요가 없다.

**3. 다중 가용 영역 (Multi-AZ):**
여러 가용 영역에 인스턴스를 분산 배치한다.

**설정:**
```json
{
  "AvailabilityZones": ["us-west-2a", "us-west-2b", "us-west-2c"]
}
```

**동작 방식:**
- Desired Capacity가 6이면 각 AZ에 2개씩 배치한다
- us-west-2a가 장애나면 다른 AZ의 인스턴스가 트래픽을 처리한다
- ASG가 자동으로 다른 AZ에 인스턴스를 추가한다

**실제 사례:**
2021년 12월, AWS us-east-1의 한 가용 영역에 장애가 발생했다. Multi-AZ를 사용하지 않은 서비스는 다운되었다. Multi-AZ를 사용한 서비스는 정상 작동했다. 사용자는 장애를 인지하지 못했다.

### Launch Template

Launch Template은 인스턴스 생성 시 사용할 설정을 정의한다. 인스턴스의 "청사진"이다.

**왜 Launch Template이 필요할까:**

**과거에는:**
ASG에서 인스턴스를 시작할 때마다 모든 설정을 지정해야 했다. AMI, 인스턴스 타입, 보안 그룹, 키 페어... 설정이 복잡하고 실수하기 쉬웠다.

**Launch Template 사용:**
설정을 한 번만 정의한다. ASG는 이 템플릿으로 인스턴스를 생성한다. 일관성이 보장된다.

**필수 설정:**

**1. AMI (Amazon Machine Image):**
어떤 운영체제와 소프트웨어를 사용할지 정의한다.

**예시:**
```json
{
  "ImageId": "ami-0c55b159cbfafe1f0"  // Amazon Linux 2
}
```

**커스텀 AMI:**
자체 AMI를 만들 수 있다. 필요한 소프트웨어를 미리 설치한다.

예를 들어:
- Node.js 18 설치
- Nginx 설치
- CloudWatch Agent 설치
- 회사 표준 보안 설정 적용

이렇게 하면 인스턴스 시작 시간이 단축된다. User Data로 설치하는 것보다 빠르다.

**2. 인스턴스 타입:**
CPU와 메모리를 선택한다.

**일반적인 선택:**
- **t3.micro**: 테스트, 개발 환경 (1 vCPU, 1GB)
- **t3.small**: 소규모 웹사이트 (2 vCPU, 2GB)
- **t3.medium**: 일반 웹 애플리케이션 (2 vCPU, 4GB)
- **m5.large**: 중간 규모 애플리케이션 (2 vCPU, 8GB)
- **c5.large**: CPU 집약적 작업 (2 vCPU, 4GB, 고성능 CPU)

**3. 보안 그룹:**
어떤 트래픽을 허용할지 정의한다.

**예시:**
```json
{
  "SecurityGroupIds": ["sg-12345678"]
}
```

**일반적인 설정:**
- 80번 포트: HTTP 허용 (ALB에서만)
- 443번 포트: HTTPS 허용 (ALB에서만)
- 22번 포트: SSH 허용 (관리자 IP에서만)

**4. IAM 역할:**
인스턴스가 AWS 서비스에 접근할 수 있는 권한을 부여한다.

**예시:**
```json
{
  "IamInstanceProfile": {
    "Name": "MyInstanceProfile"
  }
}
```

**권한 예시:**
- S3 읽기: 설정 파일 다운로드
- CloudWatch Logs 쓰기: 로그 전송
- DynamoDB 읽기/쓰기: 데이터 저장

**5. User Data:**
인스턴스 시작 시 실행할 스크립트다.

**예시:**
```bash
#!/bin/bash
# 패키지 업데이트
yum update -y

# Node.js 설치
curl -sL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

# 애플리케이션 다운로드
aws s3 cp s3://my-bucket/app.zip /home/ec2-user/
unzip /home/ec2-user/app.zip -d /home/ec2-user/app

# 애플리케이션 시작
cd /home/ec2-user/app
npm install
npm start
```

**주의사항:**
User Data 실행 시간이 길면 인스턴스 시작이 느려진다. 가능하면 커스텀 AMI를 사용한다.

**버전 관리:**

Launch Template은 버전 관리가 가능하다.

**시나리오:**
현재 v1을 사용 중이다. Node.js를 16에서 18로 업그레이드하려고 한다.

**작업 과정:**
1. Launch Template v2를 만든다. Node.js 18 AMI를 사용한다
2. 테스트 ASG에 v2를 적용한다
3. 테스트를 수행한다
4. 문제가 없으면 프로덕션 ASG에 v2를 적용한다
5. 문제가 생기면 v1으로 롤백한다

롤백이 쉽다. ASG 설정에서 버전만 변경하면 된다.

### Scaling Policy (스케일링 정책)

언제, 얼마나 인스턴스를 추가하거나 제거할지 정의한다.

**1. Target Tracking Scaling**

목표 값을 유지하도록 자동으로 조절한다. 가장 간단하고 많이 사용하는 방식이다.

**동작 원리:**

**목표 설정:**
"CPU 사용률을 70%로 유지하고 싶어요."

**ASG의 동작:**
1. 현재 CPU 사용률을 확인한다. 85%다
2. 목표(70%)보다 높다. 인스턴스를 추가해야 한다
3. 얼마나 추가할까? 계산한다
4. 현재: 4개 인스턴스, 85% CPU
5. 필요: 약 5개 인스턴스 (85% ÷ 70% × 4 ≈ 4.86)
6. 1개 인스턴스를 추가한다
7. 몇 분 후 다시 확인한다. 68%가 되었다
8. 목표에 근접했다. 추가 작업은 하지 않는다

**축소도 자동:**
1. 현재 CPU 사용률을 확인한다. 40%다
2. 목표(70%)보다 낮다. 인스턴스를 제거할 수 있다
3. 현재: 5개 인스턴스, 40% CPU
4. 필요: 약 3개 인스턴스 (40% ÷ 70% × 5 ≈ 2.86)
5. 2개 인스턴스를 제거한다
6. 3개 인스턴스로 60% CPU를 유지한다

**지원하는 메트릭:**

**CPU 사용률:**
가장 일반적이다. 70-80%를 목표로 설정한다.

```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageCPUUtilization"
  }
}
```

**네트워크 트래픽:**
네트워크 집약적인 애플리케이션에 적합하다.

```json
{
  "TargetValue": 1000000.0,  // 1MB/s
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageNetworkIn"
  }
}
```

**ALB 요청 수:**
웹 애플리케이션에 적합하다.

```json
{
  "TargetValue": 1000.0,  // 인스턴스당 1000 요청/분
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ALBRequestCountPerTarget"
  }
}
```

**커스텀 메트릭:**
비즈니스 로직에 특화된 지표를 사용할 수 있다.

예를 들어:
- 큐에 대기 중인 작업 수
- 활성 연결 수
- 평균 응답 시간
- 처리 중인 주문 수

CloudWatch에 커스텀 메트릭을 전송하고, Target Tracking에서 사용한다.

**실무 팁:**
처음에는 CPU 사용률로 시작한다. 간단하고 대부분의 경우 잘 작동한다. 70%를 목표로 설정한다. 너무 높으면(90%) 버퍼가 부족하다. 너무 낮으면(30%) 비용이 낭비된다.

**2. Step Scaling**

임계값에 따라 단계적으로 조절한다. 더 세밀한 제어가 가능하다.

**왜 Step Scaling을 사용할까:**

Target Tracking은 간단하지만 제약이 있다. 트래픽 급증 시 천천히 확장된다. Step Scaling은 상황에 따라 다르게 반응한다.

**설정 예시:**

**Scale Out (확장):**
```json
{
  "MetricAggregationType": "Average",
  "StepAdjustments": [
    {
      "MetricIntervalLowerBound": 0,
      "MetricIntervalUpperBound": 10,
      "ScalingAdjustment": 1
    },
    {
      "MetricIntervalLowerBound": 10,
      "MetricIntervalUpperBound": 20,
      "ScalingAdjustment": 2
    },
    {
      "MetricIntervalLowerBound": 20,
      "ScalingAdjustment": 3
    }
  ]
}
```

**CloudWatch 알람:**
```json
{
  "MetricName": "CPUUtilization",
  "Threshold": 70,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

**해석:**
알람 임계값이 70%다. 현재 CPU가 75%라면:
- 70 + 0 = 70% ~ 70 + 10 = 80% 범위
- 1개 인스턴스 추가

현재 CPU가 85%라면:
- 70 + 10 = 80% ~ 70 + 20 = 90% 범위
- 2개 인스턴스 추가

현재 CPU가 95%라면:
- 70 + 20 = 90% 이상
- 3개 인스턴스 추가

트래픽이 급증하면 빠르게 많은 인스턴스를 추가한다.

**Scale In (축소):**
```json
{
  "StepAdjustments": [
    {
      "MetricIntervalUpperBound": 0,
      "ScalingAdjustment": -1
    }
  ]
}
```

**CloudWatch 알람:**
```json
{
  "MetricName": "CPUUtilization",
  "Threshold": 30,
  "ComparisonOperator": "LessThanThreshold"
}
```

CPU가 30% 아래로 떨어지면 1개씩 제거한다.

**실무 팁:**
Scale Out은 공격적으로, Scale In은 보수적으로 설정한다. 확장은 빠르게, 축소는 천천히. 불필요한 확장/축소 반복을 방지한다.

**3. Scheduled Scaling**

특정 시간에 용량을 조절한다. 트래픽 패턴을 알고 있을 때 유용하다.

**사용 사례:**

**평일 패턴:**
회사 업무 시간에 트래픽이 집중된다.

```json
{
  "ScheduledActionName": "scale-up-morning",
  "Recurrence": "0 9 * * 1-5",  // 평일 오전 9시
  "MinSize": 5,
  "MaxSize": 20,
  "DesiredCapacity": 10
}
```

```json
{
  "ScheduledActionName": "scale-down-evening",
  "Recurrence": "0 18 * * 1-5",  // 평일 오후 6시
  "MinSize": 2,
  "MaxSize": 10,
  "DesiredCapacity": 3
}
```

**동작:**
- 평일 오전 9시: 인스턴스 10개로 증가
- 평일 오후 6시: 인스턴스 3개로 감소
- 주말: 계속 3개 유지

**온라인 쇼핑몰:**
저녁 시간에 트래픽이 많다.

```json
{
  "Recurrence": "0 20 * * *",  // 매일 오후 8시
  "DesiredCapacity": 15
}
```

```json
{
  "Recurrence": "0 2 * * *",  // 매일 새벽 2시
  "DesiredCapacity": 5
}
```

**특별 이벤트:**
TV 광고가 방송되는 시간.

```json
{
  "StartTime": "2026-01-25T21:00:00Z",  // 특정 날짜와 시간
  "EndTime": "2026-01-25T22:00:00Z",
  "MinSize": 20,
  "MaxSize": 50,
  "DesiredCapacity": 30
}
```

광고 방송 1시간 전에 미리 확장한다. 트래픽 급증에 대비한다.

**실무 팁:**
Scheduled Scaling과 Target Tracking을 함께 사용한다. Scheduled Scaling으로 기본 용량을 설정하고, Target Tracking으로 세밀하게 조절한다.

예를 들어:
- 오전 9시: Scheduled Scaling으로 10개 시작
- 트래픽 급증: Target Tracking이 15개로 확장
- 오후 6시: Scheduled Scaling으로 3개로 감소

### Health Check

인스턴스가 정상인지 확인하고, 비정상 인스턴스를 교체한다.

**Health Check 타입:**

**1. EC2 Health Check:**
인스턴스 자체의 상태를 확인한다.

**확인 항목:**
- 인스턴스가 running 상태인가?
- 시스템 상태 체크를 통과하는가?
- 인스턴스 상태 체크를 통과하는가?

**실패 상황:**
- 하드웨어 장애
- 네트워크 연결 끊김
- 커널 패닉
- 파일 시스템 손상

**2. ELB Health Check:**
애플리케이션 수준의 상태를 확인한다. 더 정확하다.

**동작 방식:**
1. ALB가 주기적으로 인스턴스에 HTTP 요청을 보낸다
2. 예: GET /health
3. 200 OK 응답을 기대한다
4. 연속으로 2번 성공하면 Healthy
5. 연속으로 2번 실패하면 Unhealthy

**Health Check 엔드포인트:**
애플리케이션에서 /health 엔드포인트를 구현한다.

```javascript
// Node.js 예시
app.get('/health', (req, res) => {
  // 데이터베이스 연결 확인
  if (!db.isConnected()) {
    return res.status(503).send('DB not connected');
  }
  
  // 중요한 서비스 확인
  if (!externalService.isAvailable()) {
    return res.status(503).send('External service unavailable');
  }
  
  res.status(200).send('OK');
});
```

이렇게 하면 애플리케이션 수준의 문제를 감지할 수 있다. 단순히 서버가 살아있는지만 확인하는 것이 아니라, 실제로 서비스 가능한지 확인한다.

**Grace Period:**
인스턴스 시작 후 Health Check를 시작하기 전 대기 시간이다.

**왜 필요할까:**
인스턴스가 시작되고 애플리케이션이 준비되는 데 시간이 걸린다.
- OS 부팅: 30초
- 애플리케이션 시작: 60초
- 데이터베이스 연결 풀 생성: 10초
- 캐시 워밍: 30초
- 총: 약 130초

Grace Period를 300초(5분)로 설정한다. 이 시간 동안은 Health Check에 실패해도 인스턴스를 종료하지 않는다.

**교체 과정:**

**시나리오:**
인스턴스 3개가 실행 중이다. 하나가 Unhealthy가 되었다.

**동작 과정:**
1. Health Check가 실패를 감지한다
2. 재확인한다. 일시적 문제일 수 있다
3. 연속으로 2번 실패한다
4. 인스턴스를 Unhealthy로 표시한다
5. ALB가 해당 인스턴스로 트래픽을 보내지 않는다
6. ASG가 새 인스턴스를 시작한다
7. 새 인스턴스가 Health Check를 통과한다
8. ALB가 새 인스턴스로 트래픽을 보낸다
9. 기존 Unhealthy 인스턴스를 종료한다

이 과정에서 서비스는 계속 실행된다. 2개의 Healthy 인스턴스가 트래픽을 처리한다.

**실무 팁:**
반드시 ELB Health Check를 사용한다. EC2 Health Check만으로는 부족하다. 애플리케이션이 크래시되어도 인스턴스는 running 상태일 수 있다.

## ECS Auto Scaling

ECS Service의 Task 개수를 자동으로 조절한다.

### Service Auto Scaling

**동작 방식:**
EC2 Auto Scaling과 유사하다. 인스턴스 대신 Task를 확장/축소한다.

**Target Tracking 예시:**

```json
{
  "ServiceNamespace": "ecs",
  "ResourceId": "service/my-cluster/my-service",
  "ScalableDimension": "ecs:service:DesiredCount",
  "TargetTrackingScalingPolicyConfiguration": {
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }
}
```

**동작:**
- Task의 평균 CPU가 70% 이상: Task 추가
- Task의 평균 CPU가 70% 이하: Task 제거

**메트릭 선택:**
- **CPU**: 컴퓨팅 집약적 작업
- **메모리**: 캐싱, 데이터 처리
- **ALB 요청 수**: 웹 애플리케이션

**실무 주의사항:**

**Task 시작 시간 고려:**
Fargate Task는 시작에 30-60초가 걸린다. ScaleOutCooldown을 60초로 설정한다. 너무 빠르게 반복하지 않도록 한다.

**Scale In 신중하게:**
ScaleInCooldown을 300초(5분)로 설정한다. 트래픽 변동에 너무 민감하게 반응하지 않도록 한다.

**최소 Task 개수:**
MinCapacity를 2 이상으로 설정한다. 고가용성을 보장한다.

### Cluster Auto Scaling (EC2 모드)

ECS 클러스터의 EC2 인스턴스를 자동으로 조절한다.

**Capacity Provider:**

**동작 원리:**
1. Task를 배치할 인스턴스가 없다
2. Capacity Provider가 감지한다
3. Auto Scaling Group에 인스턴스 추가를 요청한다
4. 새 인스턴스가 시작된다
5. ECS 클러스터에 등록된다
6. Task가 새 인스턴스에 배치된다

**설정 예시:**

```json
{
  "capacityProviders": ["my-capacity-provider"],
  "defaultCapacityProviderStrategy": [
    {
      "capacityProvider": "my-capacity-provider",
      "weight": 1,
      "base": 0
    }
  ]
}
```

**Managed Scaling:**
```json
{
  "managedScaling": {
    "status": "ENABLED",
    "targetCapacity": 80,
    "minimumScalingStepSize": 1,
    "maximumScalingStepSize": 10
  }
}
```

- targetCapacity: 80% → 클러스터 사용률 목표
- 사용률이 80% 이상: 인스턴스 추가
- 사용률이 80% 이하: 인스턴스 제거

**실무 팁:**
Fargate를 사용하면 이런 복잡한 설정이 필요 없다. AWS가 자동으로 리소스를 관리한다. EC2 모드는 비용 최적화가 중요한 경우에만 사용한다.

## 참고

- AWS Auto Scaling 사용자 가이드: https://docs.aws.amazon.com/autoscaling/
- EC2 Auto Scaling: https://docs.aws.amazon.com/autoscaling/ec2/userguide/
- ECS Auto Scaling: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html
