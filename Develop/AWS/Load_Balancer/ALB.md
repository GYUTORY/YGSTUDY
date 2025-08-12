---
title: AWS Application Load Balancer (ALB)
tags: [aws, loadbalancer, alb, networking, http]
updated: 2024-12-19
---

# AWS Application Load Balancer (ALB)

## 배경

AWS Application Load Balancer(ALB)는 OSI 7계층(애플리케이션 계층)에서 동작하는 로드 밸런서로, HTTP/HTTPS 트래픽을 여러 대상(EC2 인스턴스, 컨테이너, Lambda 함수 등)에 분산시킵니다. 고급 라우팅 기능과 마이크로서비스 아키텍처에 최적화된 기능을 제공하여 현대적인 웹 애플리케이션의 요구사항을 충족합니다.

## 핵심

### ALB의 기본 개념

#### 애플리케이션 계층 로드 밸런싱
- HTTP/HTTPS 트래픽을 기반으로 한 지능적인 라우팅
- URL 경로, 호스트 헤더, HTTP 메서드 등을 기반으로 트래픽 분산
- 세션 기반이 아닌 요청 기반 로드 밸런싱

#### 마이크로서비스 지원
- 경로 기반 라우팅으로 서비스별 트래픽 분리
- 컨테이너 기반 애플리케이션 지원
- 서버리스 아키텍처와의 통합

### ALB의 주요 특징

| 특징 | 설명 | 장점 |
|------|------|------|
| **고급 라우팅** | URL 경로, 호스트 헤더 기반 라우팅 | 마이크로서비스 아키텍처 지원 |
| **SSL/TLS 종료** | 클라이언트와 ALB 간 HTTPS 통신 | 백엔드 서버 부하 감소 |
| **헬스 체크** | 대상 그룹의 상태 모니터링 | 자동 장애 복구 |
| **자동 스케일링** | 트래픽에 따른 자동 확장 | 성능 최적화 |
| **WAF 통합** | 웹 애플리케이션 방화벽 지원 | 보안 강화 |

### ALB 구성 요소

#### 리스너 (Listener)
- 클라이언트 요청을 받는 엔드포인트
- 프로토콜(HTTP/HTTPS)과 포트 설정
- SSL/TLS 인증서 관리

#### 대상 그룹 (Target Group)
- 트래픽을 받을 대상들의 그룹
- EC2 인스턴스, IP 주소, Lambda 함수, 컨테이너 등 지원
- 헬스 체크 설정

#### 라우팅 규칙 (Routing Rules)
- 요청을 어떤 대상 그룹으로 전달할지 결정
- 조건(경로, 호스트, 헤더 등)과 액션 정의
- 우선순위 기반 규칙 적용

## 예시

### 기본 ALB 생성

```python
import boto3

# AWS ELB 클라이언트 생성
elbv2 = boto3.client('elbv2', region_name='ap-northeast-2')

# ALB 생성
response = elbv2.create_load_balancer(
    Name='my-alb',
    Subnets=[
        'subnet-12345678',
        'subnet-87654321'
    ],
    SecurityGroups=[
        'sg-12345678'
    ],
    Scheme='internet-facing',
    Type='application',
    IpAddressType='ipv4'
)

alb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
alb_dns = response['LoadBalancers'][0]['DNSName']

print(f"ALB 생성 완료: {alb_dns}")
```

### 대상 그룹 생성

```python
# 대상 그룹 생성 (EC2 인스턴스용)
response = elbv2.create_target_group(
    Name='web-target-group',
    Protocol='HTTP',
    Port=80,
    VpcId='vpc-12345678',
    HealthCheckProtocol='HTTP',
    HealthCheckPath='/health',
    HealthCheckIntervalSeconds=30,
    HealthCheckTimeoutSeconds=5,
    HealthyThresholdCount=2,
    UnhealthyThresholdCount=2,
    TargetType='instance'
)

target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
print(f"대상 그룹 생성 완료: {target_group_arn}")

# 대상 그룹에 인스턴스 등록
elbv2.register_targets(
    TargetGroupArn=target_group_arn,
    Targets=[
        {
            'Id': 'i-1234567890abcdef0',
            'Port': 80
        },
        {
            'Id': 'i-0987654321fedcba0',
            'Port': 80
        }
    ]
)
```

### 리스너 및 라우팅 규칙 설정

```python
# HTTPS 리스너 생성
response = elbv2.create_listener(
    LoadBalancerArn=alb_arn,
    Protocol='HTTPS',
    Port=443,
    Certificates=[
        {
            'CertificateArn': 'arn:aws:acm:ap-northeast-2:123456789012:certificate/abcd1234-5678-90ef-ghij-klmnopqrstuv'
        }
    ],
    DefaultActions=[
        {
            'Type': 'forward',
            'TargetGroupArn': target_group_arn
        }
    ]
)

listener_arn = response['Listeners'][0]['ListenerArn']

# 경로 기반 라우팅 규칙 추가
elbv2.create_rule(
    ListenerArn=listener_arn,
    Priority=1,
    Conditions=[
        {
            'Field': 'path-pattern',
            'Values': ['/api/*']
        }
    ],
    Actions=[
        {
            'Type': 'forward',
            'TargetGroupArn': 'arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:targetgroup/api-target-group/abcdef1234567890'
        }
    ]
)
```

### Python을 사용한 ALB 관리

```python
class ALBManager:
    def __init__(self, region='ap-northeast-2'):
        self.elbv2_client = boto3.client('elbv2', region_name=region)
    
    def create_alb_with_targets(self, name, subnets, security_groups, target_instances):
        """ALB와 대상 그룹을 함께 생성"""
        try:
            # ALB 생성
            alb_response = self.elbv2_client.create_load_balancer(
                Name=name,
                Subnets=subnets,
                SecurityGroups=security_groups,
                Scheme='internet-facing',
                Type='application'
            )
            
            alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
            alb_dns = alb_response['LoadBalancers'][0]['DNSName']
            
            # 대상 그룹 생성
            tg_response = self.elbv2_client.create_target_group(
                Name=f'{name}-target-group',
                Protocol='HTTP',
                Port=80,
                VpcId='vpc-12345678',
                HealthCheckProtocol='HTTP',
                HealthCheckPath='/health',
                TargetType='instance'
            )
            
            target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            
            # 대상 등록
            targets = [{'Id': instance_id, 'Port': 80} for instance_id in target_instances]
            self.elbv2_client.register_targets(
                TargetGroupArn=target_group_arn,
                Targets=targets
            )
            
            # 리스너 생성
            listener_response = self.elbv2_client.create_listener(
                LoadBalancerArn=alb_arn,
                Protocol='HTTP',
                Port=80,
                DefaultActions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn
                    }
                ]
            )
            
            return {
                'alb_arn': alb_arn,
                'alb_dns': alb_dns,
                'target_group_arn': target_group_arn,
                'listener_arn': listener_response['Listeners'][0]['ListenerArn']
            }
            
        except Exception as e:
            print(f"ALB 생성 실패: {e}")
            return None
    
    def add_path_rule(self, listener_arn, path_pattern, target_group_arn, priority):
        """경로 기반 라우팅 규칙 추가"""
        try:
            response = self.elbv2_client.create_rule(
                ListenerArn=listener_arn,
                Priority=priority,
                Conditions=[
                    {
                        'Field': 'path-pattern',
                        'Values': [path_pattern]
                    }
                ],
                Actions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn
                    }
                ]
            )
            return response['Rules'][0]['RuleArn']
        except Exception as e:
            print(f"라우팅 규칙 추가 실패: {e}")
            return None
    
    def get_alb_health(self, alb_arn):
        """ALB 상태 조회"""
        try:
            response = self.elbv2_client.describe_target_health(
                TargetGroupArn=alb_arn
            )
            return response['TargetHealthDescriptions']
        except Exception as e:
            print(f"ALB 상태 조회 실패: {e}")
            return []

# 사용 예시
alb_manager = ALBManager()

# ALB 생성
result = alb_manager.create_alb_with_targets(
    name='my-web-alb',
    subnets=['subnet-12345678', 'subnet-87654321'],
    security_groups=['sg-12345678'],
    target_instances=['i-1234567890abcdef0', 'i-0987654321fedcba0']
)

if result:
    print(f"ALB DNS: {result['alb_dns']}")
    
    # API 경로 규칙 추가
    alb_manager.add_path_rule(
        listener_arn=result['listener_arn'],
        path_pattern='/api/*',
        target_group_arn='arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:targetgroup/api-tg/abcdef1234567890',
        priority=1
    )
```

### CloudFormation 템플릿

```yaml
# alb-template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Application Load Balancer with Target Groups'

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC ID
  
  PublicSubnets:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Public subnet IDs

Resources:
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for ALB
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

  WebTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: web-target-group
      Protocol: HTTP
      Port: 80
      VpcId: !Ref VpcId
      HealthCheckProtocol: HTTP
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 2
      TargetType: instance

  ApiTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: api-target-group
      Protocol: HTTP
      Port: 8080
      VpcId: !Ref VpcId
      HealthCheckProtocol: HTTP
      HealthCheckPath: /api/health
      HealthCheckIntervalSeconds: 30
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 2
      TargetType: instance

  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: my-application-lb
      Scheme: internet-facing
      Type: application
      Subnets: !Ref PublicSubnets
      SecurityGroups:
        - !Ref ALBSecurityGroup

  ALBListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ApplicationLoadBalancer
      Protocol: HTTP
      Port: 80
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref WebTargetGroup

  ApiPathRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      ListenerArn: !Ref ALBListener
      Priority: 1
      Conditions:
        - Field: path-pattern
          Values: ['/api/*']
      Actions:
        - Type: forward
          TargetGroupArn: !Ref ApiTargetGroup

Outputs:
  ALBDNSName:
    Description: DNS name of the load balancer
    Value: !GetAtt ApplicationLoadBalancer.DNSName
  
  WebTargetGroupArn:
    Description: ARN of the web target group
    Value: !Ref WebTargetGroup
  
  ApiTargetGroupArn:
    Description: ARN of the API target group
    Value: !Ref ApiTargetGroup
```

## 운영 팁

### 1. 고가용성 구성

#### Multi-AZ 배포
```python
# 여러 가용영역에 서브넷 배포
subnets = [
    'subnet-12345678',  # ap-northeast-2a
    'subnet-87654321',  # ap-northeast-2c
    'subnet-abcdef12'   # ap-northeast-2d
]

response = elbv2.create_load_balancer(
    Name='high-availability-alb',
    Subnets=subnets,
    SecurityGroups=['sg-12345678'],
    Scheme='internet-facing',
    Type='application'
)
```

#### 크로스 존 로드 밸런싱
```python
# 크로스 존 로드 밸런싱 활성화
elbv2.modify_load_balancer_attributes(
    LoadBalancerArn=alb_arn,
    Attributes=[
        {
            'Key': 'load_balancing.cross_zone.enabled',
            'Value': 'true'
        }
    ]
)
```

### 2. 보안 설정

#### HTTPS 리스너 구성
```python
# HTTPS 리스너 생성
response = elbv2.create_listener(
    LoadBalancerArn=alb_arn,
    Protocol='HTTPS',
    Port=443,
    Certificates=[
        {
            'CertificateArn': 'arn:aws:acm:ap-northeast-2:123456789012:certificate/abcd1234-5678-90ef-ghij-klmnopqrstuv'
        }
    ],
    DefaultActions=[
        {
            'Type': 'forward',
            'TargetGroupArn': target_group_arn
        }
    ]
)

# HTTP에서 HTTPS로 리다이렉션
elbv2.create_listener(
    LoadBalancerArn=alb_arn,
    Protocol='HTTP',
    Port=80,
    DefaultActions=[
        {
            'Type': 'redirect',
            'RedirectConfig': {
                'Protocol': 'HTTPS',
                'Port': '443',
                'StatusCode': 'HTTP_301'
            }
        }
    ]
)
```

#### WAF 연동
```python
import boto3

wafv2 = boto3.client('wafv2')

# WAF 웹 ACL 생성
response = wafv2.create_web_acl(
    Name='alb-web-acl',
    Scope='REGIONAL',
    DefaultAction={
        'Allow': {}
    },
    Rules=[
        {
            'Name': 'RateLimitRule',
            'Priority': 1,
            'Statement': {
                'RateBasedStatement': {
                    'Limit': 2000,
                    'AggregateKeyType': 'IP'
                }
            },
            'Action': {
                'Block': {}
            },
            'VisibilityConfig': {
                'SampledRequestsEnabled': True,
                'CloudWatchMetricsEnabled': True,
                'MetricName': 'RateLimitRule'
            }
        }
    ],
    VisibilityConfig={
        'SampledRequestsEnabled': True,
        'CloudWatchMetricsEnabled': True,
        'MetricName': 'ALBWebACL'
    }
)

web_acl_arn = response['Summary']['ARN']

# ALB에 WAF 연동
elbv2.set_web_acl(
    ResourceArn=alb_arn,
    WebACLArn=web_acl_arn
)
```

### 3. 성능 최적화

#### 연결 드레이닝 설정
```python
# 대상 그룹에 연결 드레이닝 설정
elbv2.modify_target_group_attributes(
    TargetGroupArn=target_group_arn,
    Attributes=[
        {
            'Key': 'deregistration_delay.timeout_seconds',
            'Value': '30'
        }
    ]
)
```

#### 압축 활성화
```python
# ALB 압축 설정
elbv2.modify_load_balancer_attributes(
    LoadBalancerArn=alb_arn,
    Attributes=[
        {
            'Key': 'routing.http.compression.enabled',
            'Value': 'true'
        },
        {
            'Key': 'routing.http.compression.types',
            'Value': 'text/html,text/css,application/javascript,application/json'
        }
    ]
)
```

### 4. 모니터링 및 로깅

#### 액세스 로그 활성화
```python
# S3 버킷에 액세스 로그 저장
elbv2.modify_load_balancer_attributes(
    LoadBalancerArn=alb_arn,
    Attributes=[
        {
            'Key': 'access_logs.s3.enabled',
            'Value': 'true'
        },
        {
            'Key': 'access_logs.s3.bucket',
            'Value': 'my-alb-logs-bucket'
        },
        {
            'Key': 'access_logs.s3.prefix',
            'Value': 'alb-logs'
        }
    ]
)
```

#### CloudWatch 메트릭 모니터링
```python
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')

def get_alb_metrics(alb_name):
    """ALB 메트릭 조회"""
    
    # 요청 수
    request_response = cloudwatch.get_metric_statistics(
        Namespace='AWS/ApplicationELB',
        MetricName='RequestCount',
        Dimensions=[
            {
                'Name': 'LoadBalancer',
                'Value': alb_name
            }
        ],
        StartTime=datetime.utcnow() - timedelta(hours=1),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=['Sum']
    )
    
    # 대상 응답 시간
    latency_response = cloudwatch.get_metric_statistics(
        Namespace='AWS/ApplicationELB',
        MetricName='TargetResponseTime',
        Dimensions=[
            {
                'Name': 'LoadBalancer',
                'Value': alb_name
            }
        ],
        StartTime=datetime.utcnow() - timedelta(hours=1),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=['Average']
    )
    
    return {
        'request_count': request_response['Datapoints'],
        'target_response_time': latency_response['Datapoints']
    }

# 메트릭 조회
metrics = get_alb_metrics('app/my-alb/1234567890abcdef0')
print(f"요청 수: {metrics['request_count']}")
print(f"대상 응답 시간: {metrics['target_response_time']}")
```

### 5. 마이크로서비스 라우팅

#### 서비스별 라우팅 규칙
```python
# 서비스별 대상 그룹 생성
services = {
    'api': {'port': 8080, 'path': '/api/*'},
    'web': {'port': 80, 'path': '/*'},
    'admin': {'port': 8081, 'path': '/admin/*'}
}

for service_name, config in services.items():
    # 대상 그룹 생성
    tg_response = elbv2.create_target_group(
        Name=f'{service_name}-target-group',
        Protocol='HTTP',
        Port=config['port'],
        VpcId='vpc-12345678',
        HealthCheckProtocol='HTTP',
        HealthCheckPath=f'{config["path"].replace("/*", "")}/health',
        TargetType='instance'
    )
    
    # 라우팅 규칙 추가
    elbv2.create_rule(
        ListenerArn=listener_arn,
        Priority=len(services) - list(services.keys()).index(service_name),
        Conditions=[
            {
                'Field': 'path-pattern',
                'Values': [config['path']]
            }
        ],
        Actions=[
            {
                'Type': 'forward',
                'TargetGroupArn': tg_response['TargetGroups'][0]['TargetGroupArn']
            }
        ]
    )
```

## 참고

### ALB vs 다른 로드 밸런서 비교

| 기능 | ALB | NLB | CLB | Gateway Load Balancer |
|------|-----|-----|-----|----------------------|
| **계층** | 7계층 (애플리케이션) | 4계층 (전송) | 4계층 (전송) | 3계층 (네트워크) |
| **프로토콜** | HTTP/HTTPS | TCP/UDP/TLS | TCP/SSL/TLS | IP |
| **라우팅** | 경로, 호스트 기반 | IP 기반 | IP 기반 | IP 기반 |
| **대상** | EC2, 컨테이너, Lambda | EC2, 컨테이너 | EC2 | EC2, 컨테이너 |
| **SSL 종료** | 지원 | 지원 | 지원 | 미지원 |

### ALB 사용 사례

| 사용 사례 | 설명 | 구성 |
|-----------|------|------|
| **웹 애플리케이션** | 일반적인 웹 서비스 | HTTP/HTTPS 리스너, 경로 기반 라우팅 |
| **마이크로서비스** | 서비스별 트래픽 분리 | 경로 기반 라우팅, 서비스별 대상 그룹 |
| **API 게이트웨이** | API 요청 라우팅 | 경로 기반 라우팅, Lambda 통합 |
| **컨테이너 오케스트레이션** | ECS/EKS 연동 | 컨테이너 대상 그룹, 서비스 디스커버리 |

### 관련 링크

- [AWS ALB 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [AWS ALB 가격](https://aws.amazon.com/elasticloadbalancing/pricing/)
- [ALB Best Practices](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/best-practices.html)
- [AWS Well-Architected Framework - 로드 밸런싱](https://aws.amazon.com/architecture/well-architected/)
