---
title: AWS CodeDeploy
tags: [aws, codedeploy, deployment, blue-green, canary, rolling, ec2, ecs, lambda]
updated: 2026-01-18
---

# AWS CodeDeploy

## 개요

CodeDeploy는 배포 자동화 서비스다. EC2, ECS, Lambda에 배포한다. Blue-Green, Canary, Rolling 배포를 지원한다. 자동 롤백 기능이 있다. 배포 중 헬스 체크를 수행한다.

### 왜 필요한가

수동 배포는 위험하다.

**문제 상황:**

**수동 SSH 배포:**
```bash
# 서버 1
ssh server1
sudo systemctl stop app
sudo cp new-app.jar /opt/app/
sudo systemctl start app

# 서버 2
ssh server2
...
```

**문제점:**
- 서버가 10대면 10번 반복
- 실수로 파일 경로 잘못 입력
- 배포 중 일부 서버만 새 버전
- 문제 발생 시 롤백 복잡
- 다운타임 발생

**CodeDeploy의 해결:**
- 모든 서버에 자동 배포
- 일관된 배포 과정
- 단계별 배포 (일부 서버씩)
- 자동 롤백
- 다운타임 최소화 (Blue-Green)

## 배포 전략

### In-Place (Rolling)

기존 서버에 새 버전을 배포한다.

**동작:**
1. 로드 밸런서에서 인스턴스 제거
2. 애플리케이션 중지
3. 새 버전 설치
4. 애플리케이션 시작
5. 헬스 체크
6. 로드 밸런서에 다시 추가

**예시 (4대 서버, 50% 동시):**
```
Step 1: 서버 1, 2 배포 (서버 3, 4 운영)
Step 2: 서버 3, 4 배포 (서버 1, 2 운영)
```

**장점:**
- 비용 효율적 (추가 서버 불필요)
- 간단

**단점:**
- 일시적 용량 감소
- 롤백 느림 (다시 배포)

### Blue-Green

새 서버를 만들고 트래픽을 전환한다.

**동작:**
1. 새 인스턴스 (Green) 생성
2. Green에 새 버전 배포
3. 헬스 체크
4. 로드 밸런서 트래픽을 Green으로 전환
5. Blue 인스턴스는 대기 (또는 종료)

**예시:**
```
Before: ALB → Blue (v1.0)
Deploy: ALB → Blue (v1.0) + Green (v2.0)
After:  ALB → Green (v2.0)
```

**장점:**
- 다운타임 없음
- 빠른 롤백 (트래픽 다시 Blue로)
- 안전

**단점:**
- 비용 증가 (배포 중 2배 리소스)

### Canary

일부 트래픽만 새 버전으로 보낸다.

**동작:**
1. 10% 트래픽을 새 버전으로
2. 10분 대기 및 모니터링
3. 문제 없으면 나머지 90% 전환

**예시:**
```
Step 1: 10% → v2.0, 90% → v1.0 (10분)
Step 2: 100% → v2.0
```

**장점:**
- 위험 최소화
- 문제 조기 발견

**단점:**
- 배포 시간 길어짐
- 복잡

## EC2 배포

### 기본 설정

**1. CodeDeploy Agent 설치:**
```bash
# Amazon Linux 2
sudo yum install -y ruby wget
cd /home/ec2-user
wget https://aws-codedeploy-us-west-2.s3.us-west-2.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo service codedeploy-agent start
```

**확인:**
```bash
sudo service codedeploy-agent status
```

**2. IAM Role 연결:**
EC2에 CodeDeploy Agent가 S3, CodeDeploy에 접근할 수 있도록 IAM Role을 연결한다.

**정책:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-deployment-bucket/*"
      ]
    }
  ]
}
```

**3. 태그 추가:**
배포 대상 인스턴스에 태그를 추가한다.

```
Key: Environment
Value: Production
```

### appspec.yml

배포 동작을 정의한다. 프로젝트 루트에 위치한다.

**기본 구조:**
```yaml
version: 0.0
os: linux
files:
  - source: /
    destination: /opt/myapp
hooks:
  BeforeInstall:
    - location: scripts/before_install.sh
      timeout: 300
      runas: root
  AfterInstall:
    - location: scripts/after_install.sh
      timeout: 300
      runas: root
  ApplicationStart:
    - location: scripts/start_server.sh
      timeout: 300
      runas: root
  ApplicationStop:
    - location: scripts/stop_server.sh
      timeout: 300
      runas: root
  ValidateService:
    - location: scripts/validate_service.sh
      timeout: 300
```

### Lifecycle Hooks

**순서:**
1. **ApplicationStop**: 기존 애플리케이션 중지
2. **DownloadBundle**: S3에서 새 버전 다운로드
3. **BeforeInstall**: 설치 전 준비
4. **Install**: 파일 복사
5. **AfterInstall**: 설치 후 작업
6. **ApplicationStart**: 애플리케이션 시작
7. **ValidateService**: 헬스 체크

### 실무 스크립트

**scripts/stop_server.sh:**
```bash
#!/bin/bash
if systemctl is-active --quiet myapp; then
  echo "Stopping application..."
  sudo systemctl stop myapp
else
  echo "Application is not running"
fi
```

**scripts/before_install.sh:**
```bash
#!/bin/bash
echo "Cleaning up old files..."
rm -rf /opt/myapp/*

echo "Creating directories..."
mkdir -p /opt/myapp/logs
```

**scripts/after_install.sh:**
```bash
#!/bin/bash
echo "Setting permissions..."
chown -R myapp:myapp /opt/myapp
chmod +x /opt/myapp/bin/start.sh

echo "Loading environment variables..."
cp /opt/myapp/config/production.env /opt/myapp/.env
```

**scripts/start_server.sh:**
```bash
#!/bin/bash
echo "Starting application..."
sudo systemctl start myapp
```

**scripts/validate_service.sh:**
```bash
#!/bin/bash
echo "Validating service..."

# HTTP 헬스 체크
for i in {1..30}; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
  if [ $HTTP_CODE -eq 200 ]; then
    echo "Service is healthy"
    exit 0
  fi
  echo "Waiting for service... ($i/30)"
  sleep 2
done

echo "Service validation failed"
exit 1
```

### Deployment Group 생성

**콘솔:**
1. CodeDeploy 콘솔
2. Applications → Create application
3. Name: MyApp
4. Compute platform: EC2/On-premises
5. Create deployment group
6. Name: Production
7. Service role: CodeDeploy role
8. Deployment type: In-place
9. Environment: EC2 instances (Tag: Environment=Production)
10. Deployment settings: CodeDeployDefault.AllAtOnce
11. Load balancer: My-ALB

**CLI:**
```bash
aws deploy create-deployment-group \
  --application-name MyApp \
  --deployment-group-name Production \
  --deployment-config-name CodeDeployDefault.OneAtATime \
  --ec2-tag-filters Key=Environment,Value=Production,Type=KEY_AND_VALUE \
  --service-role-arn arn:aws:iam::123456789012:role/CodeDeployServiceRole \
  --load-balancer-info targetGroupInfoList=[{name=my-target-group}]
```

### 배포 실행

**CLI:**
```bash
aws deploy create-deployment \
  --application-name MyApp \
  --deployment-group-name Production \
  --s3-location bucket=my-deployment-bucket,key=app-v1.0.zip,bundleType=zip
```

**GitHub 연동:**
```bash
aws deploy create-deployment \
  --application-name MyApp \
  --deployment-group-name Production \
  --github-location repository=my-org/my-app,commitId=abc123
```

## Deployment Configurations

### 사전 정의 구성

**AllAtOnce:**
모든 인스턴스에 동시 배포.
- 빠름
- 일시적 다운타임

**HalfAtATime:**
50%씩 배포.
- 중간 속도
- 용량 50% 유지

**OneAtATime:**
한 번에 한 대씩.
- 느림
- 용량 최대 유지
- 안전

### 커스텀 구성

**예시: 25%씩 배포**
```bash
aws deploy create-deployment-config \
  --deployment-config-name Custom25Percent \
  --minimum-healthy-hosts type=FLEET_PERCENT,value=75
```

75% 이상 정상 유지하면서 배포. 즉, 25%씩 배포.

## Blue-Green 배포

### Auto Scaling Group 사용

**동작:**
1. Green Auto Scaling Group 생성
2. Green에 배포
3. ALB 트래픽을 Green으로
4. Blue ASG 삭제 (또는 대기)

**Deployment Group 설정:**
```yaml
DeploymentGroup:
  BlueGreenDeploymentConfiguration:
    TerminateBlueInstancesOnDeploymentSuccess:
      Action: TERMINATE
      TerminationWaitTimeInMinutes: 5
    DeploymentReadyOption:
      ActionOnTimeout: CONTINUE_DEPLOYMENT
      WaitTimeInMinutes: 0
    GreenFleetProvisioningOption:
      Action: COPY_AUTO_SCALING_GROUP
```

**배포:**
```bash
aws deploy create-deployment \
  --application-name MyApp \
  --deployment-group-name BlueGreen \
  --deployment-config-name CodeDeployDefault.AllAtOnce
```

### 수동 승인

Green 배포 후 수동 승인까지 대기.

```yaml
DeploymentReadyOption:
  ActionOnTimeout: STOP_DEPLOYMENT
  WaitTimeInMinutes: 60
```

60분 내 승인하지 않으면 배포 중단.

## ECS 배포

### appspec.yml (ECS)

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: "arn:aws:ecs:us-west-2:123456789012:task-definition/my-app:2"
        LoadBalancerInfo:
          ContainerName: "my-container"
          ContainerPort: 8080
Hooks:
  - BeforeInstall: "LambdaFunctionToValidateBeforeInstall"
  - AfterInstall: "LambdaFunctionToValidateAfterInstall"
  - AfterAllowTestTraffic: "LambdaFunctionToValidateAfterTestTrafficStarts"
  - BeforeAllowTraffic: "LambdaFunctionToValidateBeforeAllowingProductionTraffic"
  - AfterAllowTraffic: "LambdaFunctionToValidateAfterAllowingProductionTraffic"
```

### Blue-Green (ECS)

**ALB 구성:**
- Production Listener: Port 80 → Blue Target Group
- Test Listener: Port 8080 → Green Target Group

**동작:**
1. Green 작업 세트 배포
2. Test Listener로 Green 검증 (포트 8080)
3. Production Listener를 Green으로 전환
4. Blue 작업 세트 종료

### Canary (ECS)

**Linear10PercentEvery1Minute:**
1분마다 10%씩 트래픽 전환.

**Canary10Percent5Minutes:**
10% 트래픽을 5분 동안 Green으로. 문제 없으면 나머지 90% 전환.

```bash
aws deploy create-deployment \
  --application-name MyECSApp \
  --deployment-group-name Production \
  --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes
```

## Lambda 배포

### appspec.yml (Lambda)

```yaml
version: 0.0
Resources:
  - MyFunction:
      Type: AWS::Lambda::Function
      Properties:
        Name: "my-function"
        Alias: "live"
        CurrentVersion: "1"
        TargetVersion: "2"
Hooks:
  - BeforeAllowTraffic: "PreTrafficHook"
  - AfterAllowTraffic: "PostTrafficHook"
```

### Canary (Lambda)

**LambdaCanary10Percent5Minutes:**
1. 10% 트래픽 → 새 버전
2. 5분 대기
3. 나머지 90% 전환

**Pre/Post Hook:**
```python
import boto3
import json

codedeploy = boto3.client('codedeploy')

def lambda_handler(event, context):
    deployment_id = event['DeploymentId']
    lifecycle_event_hook_execution_id = event['LifecycleEventHookExecutionId']
    
    # 테스트 실행
    result = run_smoke_tests()
    
    if result['success']:
        # 성공
        codedeploy.put_lifecycle_event_hook_execution_status(
            deploymentId=deployment_id,
            lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
            status='Succeeded'
        )
    else:
        # 실패 → 롤백
        codedeploy.put_lifecycle_event_hook_execution_status(
            deploymentId=deployment_id,
            lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
            status='Failed'
        )
```

## 자동 롤백

### 조건

**배포 실패 시:**
```yaml
AutoRollbackConfiguration:
  Enabled: true
  Events:
    - DEPLOYMENT_FAILURE
```

**CloudWatch Alarm 시:**
```yaml
AutoRollbackConfiguration:
  Enabled: true
  Events:
    - DEPLOYMENT_FAILURE
    - DEPLOYMENT_STOP_ON_ALARM
AlarmConfiguration:
  Enabled: true
  Alarms:
    - Name: high-error-rate
```

**예시:**
에러율이 5%를 넘으면 자동으로 이전 버전으로 롤백.

### 수동 롤백

```bash
aws deploy stop-deployment \
  --deployment-id d-ABCDEFGH \
  --auto-rollback-enabled
```

## 모니터링

### 배포 상태

**콘솔:**
CodeDeploy → Deployments → 배포 ID 선택

**표시:**
- 배포 상태 (진행 중, 성공, 실패)
- 인스턴스별 상태
- Lifecycle 단계별 진행률
- 에러 로그

**CLI:**
```bash
aws deploy get-deployment --deployment-id d-ABCDEFGH
```

### CloudWatch Logs

각 Lifecycle Hook의 로그를 CloudWatch Logs에 전송한다.

**설정 (appspec.yml):**
```yaml
version: 0.0
os: linux
hooks:
  AfterInstall:
    - location: scripts/after_install.sh
      timeout: 300
      runas: root
      # stdout, stderr 로그
```

**로그 그룹:**
`/aws/codedeploy/<deployment-group-name>`

## 비용

### 무료

**EC2/온프레미스:**
무료 (CodeDeploy Agent 사용)

**Lambda, ECS:**
무료

### 비용 발생 요소

**EC2 추가 인스턴스:**
Blue-Green 배포 시 일시적으로 2배 인스턴스.

**예시:**
- 기존: t3.medium × 4 = $134/월
- Blue-Green 배포 중 (1시간): 추가 $2.24
- 무시할 수준

**S3 (Artifact 저장):**
$0.023/GB-월

## 참고

- CodeDeploy 개발자 가이드: https://docs.aws.amazon.com/codedeploy/
- appspec 레퍼런스: https://docs.aws.amazon.com/codedeploy/latest/userguide/reference-appspec-file.html
- Deployment Configurations: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html

