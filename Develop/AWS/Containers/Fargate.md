---
title: AWS Fargate
tags: [aws, fargate, serverless, containers, ecs, eks]
updated: 2026-01-18
---

# AWS Fargate

## 개요

AWS Fargate는 서버를 관리하지 않고 컨테이너를 실행할 수 있는 서버리스 컴퓨팅 엔진이다. EC2 인스턴스를 프로비저닝하거나 관리할 필요 없이 컨테이너만 정의하면 AWS가 인프라를 자동으로 관리한다.

### 왜 Fargate가 필요할까

컨테이너 오케스트레이션을 사용할 때 서버 관리는 큰 부담이다.

**EC2 모드의 불편함:**
- 인스턴스 타입을 결정해야 한다. t3.medium? t3.large? m5.xlarge?
- Auto Scaling Group을 설정해야 한다
- 용량 계획을 세워야 한다. 인스턴스가 몇 대 필요할까?
- 패치와 업데이트를 관리해야 한다
- 인스턴스가 죽으면 대응해야 한다
- 리소스 활용률을 최적화해야 한다

**실제 겪는 문제:**
금요일 저녁, 갑자기 트래픽이 급증했다. 인스턴스를 추가해야 하는데 Auto Scaling이 늦게 반응한다. 인스턴스가 시작되는 데 2-3분이 걸린다. 그 사이에 사용자는 느린 응답을 경험한다.

또는, 새벽 시간에 트래픽이 거의 없는데 인스턴스 10대가 계속 실행 중이다. CPU 사용률이 5%밖에 되지 않는다. 비용이 낭비되고 있다.

**Fargate의 해결:**
Fargate는 이런 고민을 없애준다. 서버를 관리할 필요가 없다.

**개발자가 하는 것:**
- 컨테이너 이미지를 정의한다
- vCPU와 메모리를 지정한다. 예: 0.5 vCPU, 1GB 메모리
- 실행 버튼을 누른다

**AWS가 하는 것:**
- 필요한 리소스를 자동으로 할당한다
- 컨테이너를 실행한다
- 패치와 업데이트를 관리한다
- 장애 발생 시 자동으로 복구한다
- 사용한 만큼만 비용을 청구한다

### 서버리스의 의미

"서버리스"는 서버가 없다는 뜻이 아니다. 서버는 존재하지만, 개발자가 관리하지 않는다는 의미다.

**Lambda와의 유사점:**
Lambda도 서버리스다. 함수 코드만 작성하면 AWS가 서버를 관리한다. Fargate도 마찬가지다. 컨테이너만 정의하면 AWS가 서버를 관리한다.

**Lambda와의 차이점:**
- Lambda: 함수 단위, 15분 실행 제한, 이벤트 기반
- Fargate: 컨테이너 단위, 시간 제한 없음, 지속 실행 가능

Fargate는 전통적인 웹 애플리케이션을 서버리스로 실행할 수 있게 해준다.

## EC2 vs Fargate 상세 비교

실무에서 가장 많이 고민하는 부분이다. 어떤 것을 선택할까?

### 관리 부담 차이

**EC2 모드에서 해야 하는 일:**

**1. 인스턴스 시작 전:**
- AMI를 선택한다. Amazon Linux 2? Ubuntu? 커스텀 AMI?
- 인스턴스 타입을 결정한다. CPU와 메모리 조합
- 키 페어를 생성한다. SSH 접속용
- 보안 그룹을 설정한다. 어떤 포트를 열까?
- IAM 역할을 생성한다. 어떤 권한이 필요할까?

**2. 인스턴스 실행 중:**
- ECS Agent가 제대로 실행되는지 확인한다
- CloudWatch로 인스턴스를 모니터링한다
- CPU, 메모리, 디스크 사용률을 추적한다
- 로그를 확인한다

**3. 유지보수:**
- 보안 패치를 주기적으로 적용한다
- ECS Agent를 업데이트한다
- AMI를 최신으로 업데이트한다
- 인스턴스가 죽으면 대응한다
- Auto Scaling Group을 조정한다

**4. 용량 계획:**
- Task가 몇 개 실행될까? 각 Task는 얼마나 리소스를 사용할까?
- 인스턴스 한 대에 Task가 몇 개 들어갈까?
- 피크 시간대 트래픽을 고려해 인스턴스를 몇 대 준비할까?
- 리소스 활용률을 어떻게 높일까?

**Fargate에서 하는 일:**

**1. Task Definition 작성:**
```json
{
  "family": "my-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",        # 0.25 vCPU
  "memory": "512",     # 0.5 GB
  "containerDefinitions": [{
    "name": "app",
    "image": "my-app:latest",
    "portMappings": [{
      "containerPort": 8080
    }]
  }]
}
```

**2. Service 생성:**
- Task Definition을 선택한다
- 몇 개의 Task를 실행할지 지정한다
- VPC와 Subnet을 선택한다
- 보안 그룹을 지정한다
- 끝

AWS가 나머지를 알아서 한다. 인스턴스 관리, 패치, 모니터링, 스케일링 모두 자동이다.

**실무 예시:**

**EC2 모드의 하루:**
오전 9시, CloudWatch 알람이 울린다. 인스턴스 한 대의 CPU 사용률이 90%다. 인스턴스를 확인하니 ECS Agent가 응답하지 않는다. SSH로 접속해 재시작한다.

오후 2시, 새 Task를 배포하려는데 인스턴스에 공간이 부족하다. Auto Scaling Group의 최대 인스턴스 개수를 늘린다. 새 인스턴스가 시작되길 기다린다.

오후 6시, 보안팀에서 패치를 적용하라는 요청이 온다. 하나씩 인스턴스를 drain하고, 패치하고, 다시 시작한다. 2시간이 걸린다.

**Fargate의 하루:**
오전 9시, CloudWatch를 확인한다. Task가 정상 실행 중이다. 특별히 할 일이 없다.

오후 2시, 새 Task를 배포한다. 이미지 태그만 변경하고 배포한다. AWS가 알아서 새 Task를 시작한다.

오후 6시, 보안 패치? AWS가 알아서 한다. 개발자는 신경 쓸 필요가 없다.

**실무 팁:**
소규모 팀이거나 인프라 관리에 시간을 쓰고 싶지 않다면 Fargate를 선택한다. 인프라 엔지니어가 없어도 운영할 수 있다.

### 비용 상세 비교

비용은 중요한 결정 요소다. 자세히 비교해보자.

**EC2 모드 비용:**

**계산 방식:**
인스턴스가 실행되는 시간만큼 비용이 발생한다. Task가 실행되지 않아도 인스턴스가 켜져 있으면 비용이 나간다.

**예시 1: 24시간 실행하는 웹 서비스**
- Task: 2 vCPU, 4GB 메모리, 3개 실행
- 필요한 리소스: 총 6 vCPU, 12GB 메모리
- 인스턴스 선택: t3.xlarge (4 vCPU, 16GB 메모리) 2대
- 비용: $0.1664/시간 × 2대 × 24시간 × 30일 = 약 $240/월

**예시 2: 야간에만 실행하는 배치 작업**
- Task: 1 vCPU, 2GB 메모리, 1개 실행
- 실행 시간: 매일 2시간 (새벽 2-4시)
- 인스턴스: t3.small (2 vCPU, 2GB 메모리) 1대를 24시간 실행
- 비용: $0.0208/시간 × 24시간 × 30일 = 약 $15/월
- 실제 사용 시간: 2시간 × 30일 = 60시간
- 낭비되는 시간: 22시간 × 30일 = 660시간 (91% 낭비)

**Fargate 비용:**

**계산 방식:**
Task가 실행되는 시간만큼 비용이 발생한다. vCPU와 메모리 사용량에 따라 초 단위로 청구된다. 최소 1분 과금이다.

**가격 (us-east-1 기준):**
- vCPU: $0.04048/시간
- 메모리: $0.004445/GB/시간

**예시 1: 24시간 실행하는 웹 서비스**
- Task: 0.5 vCPU, 1GB 메모리, 3개 실행
- vCPU 비용: 0.5 × $0.04048 × 24 × 30 × 3 = $43.7
- 메모리 비용: 1 × $0.004445 × 24 × 30 × 3 = $9.6
- 총 비용: 약 $53.3/월

Task당 비용이 $17.8/월이다. EC2 모드(t3.xlarge 2대)는 $240/월이었다. 하지만 EC2는 더 많은 Task를 실행할 수 있다.

**더 정확한 비교:**
- EC2: t3.xlarge 2대에 Task 10개 실행 가능 → Task당 $24/월
- Fargate: Task당 $17.8/월

Task 개수가 많지 않으면 Fargate가 저렴하다.

**예시 2: 야간에만 실행하는 배치 작업**
- Task: 1 vCPU, 2GB 메모리, 1개 실행
- 실행 시간: 매일 2시간
- vCPU 비용: 1 × $0.04048 × 2 × 30 = $2.4
- 메모리 비용: 2 × $0.004445 × 2 × 30 = $0.5
- 총 비용: 약 $2.9/월

EC2는 $15/월이었다. Fargate는 $2.9/월이다. 5배 저렴하다. 간헐적으로 실행되는 워크로드에서 Fargate의 장점이 크다.

**Fargate Spot:**
Fargate Spot은 온디맨드 대비 최대 70% 저렴하다.

**예시:**
- 일반 Fargate: $17.8/월
- Fargate Spot: $5.3/월 (70% 할인)

하지만 중단될 수 있다. AWS가 용량이 필요하면 2분 전에 알림을 보내고 Task를 종료한다.

**비용 선택 가이드:**

**EC2가 저렴한 경우:**
- 24시간 실행하는 서비스
- 리소스 활용률이 높은 경우 (70% 이상)
- 예약 인스턴스나 Spot 인스턴스를 사용할 수 있는 경우
- Task가 많은 경우 (인스턴스 한 대에 10개 이상)

**Fargate가 저렴한 경우:**
- 간헐적으로 실행되는 작업
- 트래픽 변동이 큰 서비스
- 리소스 활용률이 낮은 경우
- Task가 적은 경우
- 개발/테스트 환경

**실무 팁:**
비용만 보고 결정하지 말자. 인프라 관리 비용(인건비)도 고려해야 한다. DevOps 엔지니어 한 명의 연봉이 월 $8,000라면, Fargate로 인프라 관리 시간을 50% 줄이면 월 $4,000를 절약하는 것이다. Fargate가 월 $100 더 비싸도 총 비용은 오히려 줄어든다.

### 유연성과 제약사항

**EC2의 유연성:**

**1. 인스턴스 타입 선택:**
모든 EC2 인스턴스 타입을 사용할 수 있다.
- 범용: t3, m5
- 컴퓨팅 최적화: c5, c6i
- 메모리 최적화: r5, x2
- GPU: p3, g4, inf1
- ARM: a1, t4g, m6g

**2. 커스텀 AMI:**
자체 AMI를 만들 수 있다.
- 특정 소프트웨어를 미리 설치한다
- 보안 정책을 적용한다
- 회사 표준을 따른다

예를 들어, 모든 로그를 특정 포맷으로 전송하는 에이전트를 설치할 수 있다.

**3. 로컬 스토리지:**
Instance Store를 사용할 수 있다. 매우 빠른 임시 스토리지다. NVMe SSD.

**4. 특수 하드웨어:**
- GPU로 머신러닝 모델을 실행한다
- 고성능 네트워크가 필요한 경우
- 대용량 메모리가 필요한 경우

**Fargate의 제약:**

**1. vCPU와 메모리 조합 제한:**
Fargate는 정해진 조합만 사용할 수 있다.

**0.25 vCPU:**
- 0.5GB, 1GB, 2GB

**0.5 vCPU:**
- 1GB ~ 4GB (1GB 단위)

**1 vCPU:**
- 2GB ~ 8GB (1GB 단위)

**2 vCPU:**
- 4GB ~ 16GB (1GB 단위)

**4 vCPU:**
- 8GB ~ 30GB (1GB 단위)

이 조합 외에는 사용할 수 없다. 예를 들어, 3 vCPU는 불가능하다.

**2. GPU 불가:**
Fargate는 GPU를 지원하지 않는다. 머신러닝 모델 학습이나 추론에 GPU가 필요하면 EC2를 사용해야 한다.

**3. 로컬 스토리지 제한:**
- 기본: 20GB
- 최대: 200GB (ECS만, EKS는 20GB 고정)

Instance Store를 사용할 수 없다.

**4. 커스텀 런타임 제한:**
AMI를 선택할 수 없다. Fargate 플랫폼이 제공하는 환경만 사용할 수 있다. 특수한 소프트웨어가 필요하면 컨테이너 이미지에 포함시켜야 한다.

**실무 예시:**

**EC2가 필요한 경우:**
- 머신러닝 모델 학습에 GPU가 필요하다
- 실시간 영상 처리에 고성능이 필요하다
- 특정 보안 에이전트가 호스트에 설치되어야 한다
- 매우 큰 메모리가 필요하다 (100GB 이상)

**Fargate로 충분한 경우:**
- 일반 웹 애플리케이션
- REST API 서버
- 백그라운드 작업 처리
- 마이크로서비스

대부분의 웹 애플리케이션은 Fargate로 충분하다.

### 시작 시간

Task가 시작되는 데 걸리는 시간이다.

**EC2 모드:**

**인스턴스가 이미 실행 중인 경우:**
- Task 시작 시간: 5-10초
- 이미지를 다운로드하고 컨테이너를 시작하는 시간

**새 인스턴스를 시작하는 경우:**
- 인스턴스 부팅: 30-60초
- ECS Agent 시작: 10-20초
- Task 시작: 5-10초
- 총: 1-2분

Auto Scaling으로 인스턴스를 미리 준비하면 빠르게 시작할 수 있다.

**Fargate:**

**콜드 스타트:**
- 처음 Task를 시작하거나, 오랫동안 실행하지 않은 경우
- 시작 시간: 30초 ~ 1분

**웜 스타트:**
- 최근에 실행한 Task를 다시 시작하는 경우
- 시작 시간: 10-20초

**Task를 미리 실행:**
빠른 시작이 중요하면 Task를 미리 실행해둔다. desired count를 1로 설정하고 항상 실행 상태로 유지한다.

**실무 팁:**
일반적인 웹 서비스에서는 30초 차이가 큰 문제가 되지 않는다. 서비스는 이미 실행 중이고, 스케일 아웃 시에만 새 Task가 시작되기 때문이다.

하지만 이벤트 기반 처리에서는 중요할 수 있다. SQS 메시지를 받아서 Task를 시작하는 경우, 30초는 긴 지연이다. 이런 경우 Lambda를 고려한다.

## ECS Fargate 사용법

ECS에서 Fargate를 사용하는 방법을 상세히 설명한다.

### Task Definition 작성

Task Definition은 컨테이너 실행 방법을 정의한다.

**필수 설정:**

**1. networkMode:**
반드시 `awsvpc`여야 한다. Fargate는 awsvpc 모드만 지원한다.

```json
{
  "networkMode": "awsvpc"
}
```

awsvpc 모드는 각 Task에 ENI(Elastic Network Interface)를 할당한다. Task가 VPC의 일반 IP 주소를 받는다.

**2. requiresCompatibilities:**
FARGATE를 명시한다.

```json
{
  "requiresCompatibilities": ["FARGATE"]
}
```

EC2와 Fargate를 모두 지원하려면 `["EC2", "FARGATE"]`로 설정한다.

**3. cpu와 memory:**
Task 레벨에서 지정한다. 컨테이너 레벨이 아니다.

```json
{
  "cpu": "256",     # 0.25 vCPU
  "memory": "512"   # 0.5 GB
}
```

**유효한 조합:**
- 256 (.25 vCPU) - 512, 1024, 2048 (0.5GB, 1GB, 2GB)
- 512 (.5 vCPU) - 1024, 2048, 3072, 4096 (1-4GB)
- 1024 (1 vCPU) - 2048, 3072, 4096, 5120, 6144, 7168, 8192 (2-8GB)

잘못된 조합을 사용하면 에러가 발생한다.

**전체 예시:**

```json
{
  "family": "my-web-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/myTaskRole",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "my-app:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/my-web-app",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**실무 팁:**
처음에는 작은 리소스로 시작한다. 0.5 vCPU, 1GB 메모리. CloudWatch 메트릭으로 실제 사용량을 확인한 후 조정한다. 과도하게 할당하면 비용만 증가한다.

### Service 생성과 설정

Service는 Task를 실행하고 유지한다.

**1. Launch Type 선택:**
```json
{
  "launchType": "FARGATE"
}
```

또는 Capacity Provider를 사용한다.
```json
{
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE",
      "weight": 1,
      "base": 0
    }
  ]
}
```

**2. 네트워크 구성:**

**VPC와 Subnet 선택:**
```json
{
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": [
        "subnet-12345678",
        "subnet-87654321"
      ],
      "securityGroups": [
        "sg-12345678"
      ],
      "assignPublicIp": "DISABLED"
    }
  }
}
```

**Public Subnet vs Private Subnet:**
- **Public Subnet + assignPublicIp: ENABLED**: Task가 Public IP를 받는다. 외부 인터넷에 직접 접근 가능하다
- **Private Subnet + NAT Gateway**: Task가 Private IP만 받는다. NAT Gateway를 통해 외부 통신한다 (권장)
- **Private Subnet + VPC Endpoint**: 인터넷 없이 AWS 서비스에 접근한다

**실무 권장:**
Private Subnet에서 실행한다. 보안이 강화된다. 외부 접근은 ALB를 통해서만 허용한다.

**3. 로드 밸런서 연동:**

```json
{
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
      "containerName": "web",
      "containerPort": 8080
    }
  ]
}
```

**동작 과정:**
1. Task가 시작된다
2. ECS가 Task의 IP를 확인한다
3. ALB의 타겟 그룹에 자동으로 등록한다
4. Health Check를 통과하면 트래픽을 받기 시작한다
5. Task가 종료되면 자동으로 타겟 그룹에서 제거된다

**4. Auto Scaling 설정:**

**Target Tracking:**
```json
{
  "serviceNamespace": "ecs",
  "resourceId": "service/my-cluster/my-service",
  "scalableDimension": "ecs:service:DesiredCount",
  "policyType": "TargetTrackingScaling",
  "targetTrackingScalingPolicyConfiguration": {
    "targetValue": 70.0,
    "predefinedMetricSpecification": {
      "predefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "scaleInCooldown": 300,
    "scaleOutCooldown": 60
  }
}
```

**동작 방식:**
- CPU 사용률이 70%를 넘으면 Task를 추가한다
- CPU 사용률이 70% 아래로 떨어지면 Task를 제거한다
- scaleOutCooldown: 60초 → 빠르게 확장
- scaleInCooldown: 300초 → 천천히 축소

**실무 팁:**
- scaleOutCooldown을 짧게: 트래픽 급증에 빠르게 대응
- scaleInCooldown을 길게: 불필요한 축소를 방지
- CPU 70% 목표가 일반적. 여유분을 유지

## Fargate Spot

Fargate Spot은 중단 가능한 워크로드를 저렴하게 실행한다.

### 동작 원리

**가격:**
온디맨드 대비 최대 70% 저렴하다. 실시간 수요에 따라 가격이 변동한다.

**중단 메커니즘:**
1. AWS가 용량이 필요하면 Task를 중단한다
2. 2분 전에 SIGTERM 신호를 보낸다
3. 2분 후 SIGKILL 신호로 강제 종료한다

**재시작:**
ECS Service는 자동으로 새 Task를 시작한다. 새 Task는 온디맨드 또는 Spot으로 시작된다.

### 혼합 전략

온디맨드와 Spot을 섞어서 사용한다.

**설정 예시:**
```json
{
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE",
      "weight": 1,
      "base": 2
    },
    {
      "capacityProvider": "FARGATE_SPOT",
      "weight": 4,
      "base": 0
    }
  ]
}
```

**해석:**
- base: 2 → 최소 2개는 온디맨드로 실행
- weight 비율: FARGATE 1, FARGATE_SPOT 4 → 추가 Task는 80% Spot, 20% 온디맨드

**예시:**
desired count가 7이면:
- 온디맨드: 2 (base) + 1 (20%) = 3개
- Spot: 4 (80%) = 4개

**실무 팁:**
중요한 Task는 항상 온디맨드로 실행한다. base를 설정해 최소 개수를 보장한다. 추가 Task는 Spot으로 실행해 비용을 절감한다.

## 참고

- AWS Fargate 사용자 가이드: https://docs.aws.amazon.com/AmazonECS/latest/userguide/what-is-fargate.html
- ECS Fargate 시작하기: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html
- EKS Fargate: https://docs.aws.amazon.com/eks/latest/userguide/fargate.html
- Fargate 요금: https://aws.amazon.com/fargate/pricing/
