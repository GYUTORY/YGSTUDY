---
title: AWS ECS (Elastic Container Service)
tags: [aws, containers, ecs, docker, orchestration]
updated: 2024-12-19
---

# AWS ECS (Elastic Container Service)

## 배경

AWS ECS(Elastic Container Service)는 Docker 컨테이너를 실행하고 관리하기 위한 완전 관리형 컨테이너 오케스트레이션 서비스입니다. 개발자가 컨테이너화된 애플리케이션을 쉽게 배포하고 확장할 수 있도록 도와주며, AWS의 다른 서비스들과 원활하게 통합됩니다.

## 핵심

### ECS의 기본 개념

#### 컨테이너 오케스트레이션
- 여러 컨테이너를 효율적으로 관리하고 배포
- 자동 스케일링 및 로드 밸런싱
- 서비스 디스커버리 및 헬스 체크

#### AWS 통합
- EC2, Fargate와의 통합
- Application Load Balancer 연동
- CloudWatch를 통한 모니터링
- IAM을 통한 보안 관리

### ECS 구성 요소

| 구성 요소 | 설명 | 역할 |
|-----------|------|------|
| **Cluster** | ECS 리소스의 논리적 그룹 | 태스크와 서비스를 실행하는 환경 |
| **Task Definition** | 컨테이너 실행 방법 정의 | CPU, 메모리, 포트, 환경변수 등 설정 |
| **Task** | 실행 중인 컨테이너 인스턴스 | Task Definition의 실제 실행체 |
| **Service** | 태스크의 지속적 실행 관리 | 자동 스케일링, 배포 관리 |
| **Container Instance** | 태스크를 실행하는 EC2 인스턴스 | ECS Agent가 설치된 EC2 |

### ECS 실행 모드

#### EC2 모드
- 사용자가 관리하는 EC2 인스턴스에서 실행
- 더 많은 제어권과 커스터마이징 가능
- 비용 효율적이지만 관리 부담 있음

#### Fargate 모드
- AWS가 관리하는 서버리스 환경에서 실행
- 서버 관리 불필요, 자동 스케일링
- 사용한 만큼만 비용 지불

## 예시

### 기본 ECS 클러스터 생성

```bash
# ECS 클러스터 생성
aws ecs create-cluster --cluster-name my-production-cluster

# 클러스터 목록 조회
aws ecs list-clusters

# 클러스터 상세 정보 조회
aws ecs describe-clusters --clusters my-production-cluster
```

### Task Definition 생성

```json
{
  "family": "web-app-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "web-container",
      "image": "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/web-app:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/web-app-task",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ]
    }
  ]
}
```

### Python을 사용한 ECS 관리

```python
import boto3
import json

class ECSManager:
    def __init__(self, region='ap-northeast-2'):
        self.ecs_client = boto3.client('ecs', region_name=region)
        self.region = region
    
    def create_cluster(self, cluster_name):
        """ECS 클러스터 생성"""
        try:
            response = self.ecs_client.create_cluster(
                clusterName=cluster_name,
                capacityProviders=['FARGATE'],
                defaultCapacityProviderStrategy=[
                    {
                        'capacityProvider': 'FARGATE',
                        'weight': 1
                    }
                ]
            )
            return response['cluster']['clusterArn']
        except Exception as e:
            print(f"클러스터 생성 실패: {e}")
            return None
    
    def register_task_definition(self, task_definition):
        """Task Definition 등록"""
        try:
            response = self.ecs_client.register_task_definition(
                **task_definition
            )
            return response['taskDefinition']['taskDefinitionArn']
        except Exception as e:
            print(f"Task Definition 등록 실패: {e}")
            return None
    
    def create_service(self, cluster_name, service_name, task_definition_arn):
        """ECS 서비스 생성"""
        try:
            response = self.ecs_client.create_service(
                cluster=cluster_name,
                serviceName=service_name,
                taskDefinition=task_definition_arn,
                desiredCount=2,
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': ['subnet-12345678', 'subnet-87654321'],
                        'securityGroups': ['sg-12345678'],
                        'assignPublicIp': 'ENABLED'
                    }
                }
            )
            return response['service']['serviceArn']
        except Exception as e:
            print(f"서비스 생성 실패: {e}")
            return None
    
    def update_service(self, cluster_name, service_name, task_definition_arn):
        """서비스 업데이트 (새 버전 배포)"""
        try:
            response = self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=task_definition_arn
            )
            return response['service']['serviceArn']
        except Exception as e:
            print(f"서비스 업데이트 실패: {e}")
            return None

# 사용 예시
ecs_manager = ECSManager()

# 클러스터 생성
cluster_arn = ecs_manager.create_cluster('my-web-cluster')
print(f"클러스터 ARN: {cluster_arn}")

# Task Definition 등록
task_def_arn = ecs_manager.register_task_definition({
    'family': 'web-app',
    'networkMode': 'awsvpc',
    'requiresCompatibilities': ['FARGATE'],
    'cpu': '256',
    'memory': '512',
    'containerDefinitions': [
        {
            'name': 'web',
            'image': 'nginx:latest',
            'portMappings': [{'containerPort': 80}],
            'essential': True
        }
    ]
})
print(f"Task Definition ARN: {task_def_arn}")

# 서비스 생성
service_arn = ecs_manager.create_service('my-web-cluster', 'web-service', task_def_arn)
print(f"서비스 ARN: {service_arn}")
```

### Docker Compose와 ECS 연동

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/web-app:latest
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

```bash
# ECS Compose를 사용한 배포
ecs-cli compose --project-name my-app up --cluster my-cluster
```

## 운영 팁

### 1. 클러스터 설계

#### 프로덕션 클러스터 구성
```bash
# 프로덕션용 클러스터 생성
aws ecs create-cluster \
    --cluster-name production-cluster \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --tags Key=Environment,Value=Production
```

#### 개발/테스트 클러스터 구성
```bash
# 개발용 클러스터 생성
aws ecs create-cluster \
    --cluster-name dev-cluster \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --tags Key=Environment,Value=Development
```

### 2. Task Definition 최적화

#### 리소스 설정 최적화
```json
{
  "family": "optimized-web-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "nginx:alpine",
      "portMappings": [{"containerPort": 80}],
      "essential": true,
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost/ || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "ulimits": [
        {
          "name": "nofile",
          "softLimit": 65536,
          "hardLimit": 65536
        }
      ]
    }
  ]
}
```

#### 멀티 컨테이너 Task Definition
```json
{
  "family": "multi-container-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "nginx:alpine",
      "portMappings": [{"containerPort": 80}],
      "essential": true
    },
    {
      "name": "sidecar",
      "image": "fluentd:latest",
      "essential": false,
      "dependsOn": [
        {
          "containerName": "web",
          "condition": "START"
        }
      ]
    }
  ]
}
```

### 3. 서비스 설정

#### 자동 스케일링 설정
```bash
# Application Auto Scaling 설정
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/my-cluster/web-service \
    --min-capacity 1 \
    --max-capacity 10

# CPU 사용률 기반 스케일링 정책
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/my-cluster/web-service \
    --policy-name cpu-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        }
    }'
```

#### 무중단 배포 설정
```bash
# Blue/Green 배포를 위한 서비스 생성
aws ecs create-service \
    --cluster my-cluster \
    --service-name web-service \
    --task-definition web-app:1 \
    --desired-count 2 \
    --deployment-configuration '{
        "maximumPercent": 200,
        "minimumHealthyPercent": 50,
        "deploymentCircuitBreaker": {
            "enable": true,
            "rollback": true
        }
    }'
```

### 4. 모니터링 및 로깅

#### CloudWatch 로그 설정
```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/web-app",
      "awslogs-region": "ap-northeast-2",
      "awslogs-stream-prefix": "ecs",
      "awslogs-create-group": "true"
    }
  }
}
```

#### 메트릭 모니터링
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def get_ecs_metrics(cluster_name, service_name):
    """ECS 서비스 메트릭 조회"""
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/ECS',
        MetricName='CPUUtilization',
        Dimensions=[
            {
                'Name': 'ClusterName',
                'Value': cluster_name
            },
            {
                'Name': 'ServiceName',
                'Value': service_name
            }
        ],
        StartTime=datetime.utcnow() - timedelta(hours=1),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=['Average']
    )
    return response['Datapoints']
```

### 5. 보안 설정

#### IAM 역할 설정
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:123456789012:log-group:/ecs/*"
    }
  ]
}
```

#### 보안 그룹 설정
```bash
# ECS 서비스용 보안 그룹 생성
aws ec2 create-security-group \
    --group-name ecs-service-sg \
    --description "Security group for ECS service" \
    --vpc-id vpc-12345678

# 인바운드 규칙 추가
aws ec2 authorize-security-group-ingress \
    --group-id sg-12345678 \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0
```

## 참고

### ECS vs EKS 비교

| 기능 | ECS | EKS |
|------|-----|-----|
| **관리 복잡성** | 낮음 (완전 관리형) | 높음 (Kubernetes 지식 필요) |
| **커스터마이징** | 제한적 | 높음 |
| **AWS 통합** | 완전 통합 | 부분적 통합 |
| **학습 곡선** | 완만함 | 가파름 |
| **비용** | 상대적으로 저렴 | 상대적으로 비쌈 |
| **확장성** | AWS 내에서 우수 | 멀티 클라우드 지원 |

### ECS vs EC2 비교

| 기능 | ECS | EC2 |
|------|-----|-----|
| **컨테이너 관리** | 자동화 | 수동 관리 |
| **스케일링** | 자동 | 수동 또는 Auto Scaling |
| **배포** | 무중단 배포 | 수동 또는 스크립트 |
| **모니터링** | 통합 모니터링 | 별도 설정 필요 |
| **보안** | IAM 통합 | 별도 보안 설정 |

### 관련 링크

- [AWS ECS 공식 문서](https://docs.aws.amazon.com/ecs/)
- [AWS ECS 가격](https://aws.amazon.com/ecs/pricing/)
- [ECS Best Practices](https://docs.aws.amazon.com/ecs/latest/bestpracticesguide/)
- [AWS Well-Architected Framework - 컨테이너](https://aws.amazon.com/architecture/well-architected/)
