---
title: AWS PrivateLink
tags: [aws, privatelink, vpc, endpoint, security, networking, service]
updated: 2026-01-23
---

# AWS PrivateLink

## 개요

PrivateLink는 VPC와 AWS 서비스 또는 다른 VPC의 서비스를 프라이빗하게 연결한다. 인터넷을 거치지 않는다. 트래픽이 AWS 네트워크 내부에만 머문다. 보안이 강화되고 성능이 향상된다.

### 왜 필요한가

AWS 서비스나 외부 서비스에 접근할 때 보안 문제가 생긴다.

**문제 상황 1: S3 접근**

**일반적인 방법:**
프라이빗 서브넷의 EC2에서 S3에 접근한다.

```
EC2 (프라이빗) → NAT Gateway → Internet Gateway → S3 (Public)
```

**문제:**
- 트래픽이 인터넷을 거친다
- NAT Gateway 비용 발생
- 대역폭 제한
- 보안 리스크 (중간 경로 노출)

**해결: VPC Endpoint (PrivateLink)**
```
EC2 (프라이빗) → VPC Endpoint → S3
```

- 트래픽이 VPC 내부에만 머문다
- NAT Gateway 불필요
- 빠른 속도
- 안전

**문제 상황 2: 서비스 제공**

**배경:**
회사가 SaaS를 운영한다. 고객사가 수백 개다. 각 고객사가 우리 API를 호출한다.

**일반적인 방법:**
```
고객 VPC → Internet → ALB (Public) → 우리 서비스
```

**문제:**
- API가 인터넷에 노출된다
- DDoS 공격 위험
- 고객사가 보안 정책으로 인터넷 송신을 차단하면 접근 불가
- IP 화이트리스트 관리가 복잡

**해결: PrivateLink (VPC Endpoint Service)**
```
고객 VPC → VPC Endpoint → 우리 서비스 (Private)
```

- 인터넷 노출 없음
- 프라이빗 네트워크로 연결
- IP 화이트리스트 불필요
- 안전하고 빠름

**문제 상황 3: 멀티 테넌트 아키텍처**

**배경:**
각 고객사마다 VPC를 분리한다. 중앙 서비스 VPC가 있다. 모든 고객사가 중앙 서비스에 접근한다.

**일반적인 방법: VPC Peering**
- 고객 VPC 100개
- 각각 중앙 VPC와 Peering
- 100개 Peering 관리
- 라우팅 테이블 복잡

**해결: PrivateLink**
- 중앙 VPC에서 Endpoint Service 생성
- 각 고객 VPC에서 VPC Endpoint 생성
- Peering 불필요
- 라우팅 간단

## 핵심 개념

### VPC Endpoint

VPC에서 AWS 서비스나 다른 VPC의 서비스에 프라이빗하게 접근하는 진입점이다.

**두 가지 타입:**

**1. Gateway Endpoint:**
- S3, DynamoDB만 지원
- 라우팅 테이블에 규칙 추가
- 무료

**2. Interface Endpoint (PrivateLink):**
- 대부분의 AWS 서비스 지원
- ENI(Elastic Network Interface) 생성
- 프라이빗 IP 할당
- 시간당 비용 발생

### VPC Endpoint Service

자신의 서비스를 다른 VPC에 제공한다. PrivateLink로 연결된다.

**구성 요소:**
- Network Load Balancer
- VPC Endpoint Service
- 서비스를 제공하는 VPC

**접근 제어:**
- 특정 AWS 계정만 허용
- IAM 권한 설정

### ENI (Elastic Network Interface)

Interface Endpoint는 ENI를 생성한다. 프라이빗 IP 주소를 가진다.

**특징:**
- VPC 서브넷에 배치
- 보안 그룹 적용 가능
- DNS 이름 제공

## Interface Endpoint 사용

### S3 접근 (Interface Endpoint)

**생성:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-west-2.s3 \
  --subnet-ids subnet-11111111 subnet-22222222 \
  --security-group-ids sg-12345678
```

**보안 그룹 설정:**
```bash
# Endpoint의 보안 그룹
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp \
  --port 443 \
  --source-group sg-87654321  # EC2의 보안 그룹
```

EC2에서 Endpoint로 HTTPS 트래픽을 허용한다.

**사용:**
EC2에서 S3에 접근한다. 코드 변경 불필요.

```bash
# S3 목록 조회
aws s3 ls s3://my-bucket/
```

트래픽이 VPC Endpoint를 통해 S3로 간다. 인터넷을 거치지 않는다.

**DNS 확인:**
```bash
nslookup s3.us-west-2.amazonaws.com
```

Endpoint의 프라이빗 IP가 반환된다.

### Lambda 접근

Lambda 함수를 VPC 밖에서 호출한다. 보통 인터넷을 거친다. PrivateLink로 프라이빗하게 호출한다.

**Endpoint 생성:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-west-2.lambda \
  --subnet-ids subnet-11111111 \
  --security-group-ids sg-12345678
```

**Lambda 호출:**
```javascript
const AWS = require('aws-sdk');
const lambda = new AWS.Lambda({
  endpoint: 'https://vpce-12345678-abcd1234.lambda.us-west-2.vpce.amazonaws.com'
});

const result = await lambda.invoke({
  FunctionName: 'my-function',
  Payload: JSON.stringify({ key: 'value' })
}).promise();
```

Endpoint URL을 사용한다. 트래픽이 VPC 내부로만 흐른다.

## Gateway Endpoint 사용

### S3 접근 (Gateway Endpoint)

**생성:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-west-2.s3 \
  --route-table-ids rtb-11111111 rtb-22222222
```

**라우팅 테이블 확인:**
```bash
aws ec2 describe-route-tables --route-table-ids rtb-11111111
```

자동으로 규칙이 추가된다:
```
Destination         Target
pl-12345678         vpce-12345678
```

`pl-12345678`는 S3의 IP 범위를 나타내는 Prefix List다.

**사용:**
코드 변경 없이 S3에 접근한다.

```bash
aws s3 cp file.txt s3://my-bucket/
```

트래픽이 Gateway Endpoint를 통해 S3로 간다.

**Endpoint Policy:**
어떤 S3 버킷에 접근할지 제한한다.

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket/*",
        "arn:aws:s3:::my-other-bucket/*"
      ]
    }
  ]
}
```

`my-bucket`과 `my-other-bucket`만 접근 가능하다. 다른 버킷은 차단된다.

### DynamoDB 접근

**생성:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-west-2.dynamodb \
  --route-table-ids rtb-11111111
```

**사용:**
```javascript
const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

const result = await dynamodb.get({
  TableName: 'Users',
  Key: { user_id: 'user_123' }
}).promise();
```

트래픽이 Gateway Endpoint를 통해 DynamoDB로 간다.

## VPC Endpoint Service 생성

자신의 서비스를 다른 VPC에 제공한다.

### NLB 생성

Network Load Balancer를 만든다. PrivateLink는 NLB를 통해 트래픽을 전달한다.

```bash
aws elbv2 create-load-balancer \
  --name my-service-nlb \
  --type network \
  --scheme internal \
  --subnets subnet-11111111 subnet-22222222
```

**scheme: internal**
NLB를 프라이빗으로 만든다. 인터넷에서 접근 불가능.

**Target Group 생성:**
```bash
aws elbv2 create-target-group \
  --name my-service-targets \
  --protocol TCP \
  --port 80 \
  --vpc-id vpc-12345678 \
  --target-type instance
```

**Target 등록:**
```bash
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-service-targets/1234567890123456 \
  --targets Id=i-12345678 Id=i-87654321
```

**Listener 생성:**
```bash
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-service-nlb/1234567890123456 \
  --protocol TCP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-service-targets/1234567890123456
```

### Endpoint Service 생성

```bash
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-service-nlb/1234567890123456 \
  --acceptance-required
```

**acceptance-required:**
다른 계정이 연결을 요청하면 수동으로 승인한다. 보안을 위해 권장.

**Service Name 확인:**
```bash
aws ec2 describe-vpc-endpoint-service-configurations \
  --service-ids vpce-svc-12345678
```

Service Name: `com.amazonaws.vpce.us-west-2.vpce-svc-12345678`

이 이름을 고객에게 제공한다.

### 접근 허용

특정 AWS 계정만 접근하도록 설정한다.

```bash
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-id vpce-svc-12345678 \
  --add-allowed-principals arn:aws:iam::111122223333:root
```

계정 `111122223333`이 Endpoint를 생성할 수 있다.

## 고객이 Endpoint 생성

고객사가 자신의 VPC에서 Endpoint를 만든다.

**Endpoint 생성:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-customer123 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.vpce.us-west-2.vpce-svc-12345678 \
  --subnet-ids subnet-aaaaaaaa subnet-bbbbbbbb \
  --security-group-ids sg-customer123
```

**연결 요청:**
Endpoint가 "pendingAcceptance" 상태가 된다. 서비스 제공자가 승인해야 한다.

**서비스 제공자가 승인:**
```bash
aws ec2 accept-vpc-endpoint-connections \
  --service-id vpce-svc-12345678 \
  --vpc-endpoint-ids vpce-customer-12345678
```

Endpoint가 "available" 상태가 된다.

**고객이 서비스 사용:**
```bash
curl http://vpce-customer-12345678-abcd1234.vpce-svc-12345678.us-west-2.vpce.amazonaws.com
```

Endpoint DNS를 통해 서비스에 접근한다. 트래픽이 프라이빗 네트워크로만 흐른다.

## Private DNS

Endpoint에 커스텀 DNS 이름을 설정한다.

### 설정

**Endpoint Service에서 Private DNS 활성화:**
```bash
aws ec2 modify-vpc-endpoint-service-configuration \
  --service-id vpce-svc-12345678 \
  --private-dns-name api.mycompany.com
```

**DNS 검증:**
AWS가 TXT 레코드를 제공한다. 자신의 DNS에 추가해서 소유권을 증명한다.

```bash
# Route 53 또는 외부 DNS에 추가
_vpce:12345678.api.mycompany.com TXT "vpce:12345678abcdefg"
```

**검증 완료:**
```bash
aws ec2 start-vpc-endpoint-service-private-dns-verification \
  --service-id vpce-svc-12345678
```

### 사용

고객이 Endpoint를 생성할 때 Private DNS를 활성화한다.

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-customer123 \
  --service-name com.amazonaws.vpce.us-west-2.vpce-svc-12345678 \
  --private-dns-enabled \
  --subnet-ids subnet-aaaaaaaa \
  --security-group-ids sg-customer123
```

**접근:**
```bash
curl https://api.mycompany.com
```

`api.mycompany.com`이 Endpoint의 프라이빗 IP로 리졸브된다. 간편하게 사용할 수 있다.

## 실무 패턴

### 중앙 서비스 제공

**시나리오:**
회사에 여러 팀이 있다. 각 팀이 독립된 VPC를 사용한다. 중앙 DevOps 팀이 공통 서비스를 제공한다.

**서비스:**
- CI/CD API
- 로그 수집기
- 메트릭 수집기
- 시크릿 관리

**구성:**
- 중앙 VPC: 서비스들이 실행됨
- 팀 VPC: 각 팀의 리소스

**PrivateLink 사용:**
1. 중앙 VPC에서 Endpoint Service 생성
2. 각 팀 VPC에서 Endpoint 생성
3. 팀들이 서비스에 프라이빗하게 접근

**장점:**
- VPC Peering 불필요
- 라우팅 간단
- 팀 VPC끼리 격리됨
- 중앙 팀이 접근 제어

### SaaS 제공

**시나리오:**
SaaS를 운영한다. 고객사가 100개다. 각 고객사가 자신의 AWS 계정과 VPC를 사용한다.

**요구사항:**
- API를 인터넷에 노출하지 않음
- 고객사가 프라이빗하게 접근
- 고객사별 접근 제어

**구성:**
1. Endpoint Service 생성
2. Service Name을 고객에게 제공
3. 고객이 자신의 VPC에서 Endpoint 생성
4. 연결 요청을 승인

**접근 제어:**
- 연결 요청 시 고객 AWS 계정 확인
- 승인된 고객만 접근 가능
- NLB에서 추가 인증 (API Key 등)

**장점:**
- 인터넷 노출 없음
- 고객이 IP 화이트리스트 관리 불필요
- 안전하고 빠른 연결

### 멀티 리전 서비스

**시나리오:**
서비스를 여러 리전에서 제공한다. 고객이 가까운 리전에 접근한다.

**구성:**
- us-west-2에 Endpoint Service
- us-east-1에 Endpoint Service
- 고객이 리전별로 Endpoint 생성

**Private DNS 사용:**
- `api.mycompany.com`
- Route 53 Geolocation 라우팅
- 고객 위치에 따라 가까운 리전으로 연결

고객은 하나의 DNS만 사용한다. 자동으로 가까운 리전에 연결된다.

## 모니터링

### CloudWatch 메트릭

**Endpoint Service 메트릭:**
- **ActiveConnections**: 활성 연결 수
- **NewConnections**: 새 연결 수
- **BytesProcessed**: 처리된 바이트 수

**NLB 메트릭:**
- **TargetConnectionErrorCount**: Target 연결 실패
- **UnHealthyHostCount**: 비정상 Target 수

### VPC Flow Logs

Endpoint를 통과하는 트래픽을 로그로 남긴다.

```bash
aws ec2 create-flow-logs \
  --resource-type VpcEndpoint \
  --resource-ids vpce-12345678 \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpcendpoint/flowlogs
```

**분석:**
- 어떤 IP가 접근하는지
- 얼마나 많은 트래픽이 발생하는지
- 거부된 트래픽

## 트러블슈팅

### Endpoint에 연결이 안 된다

**1. Endpoint 상태 확인:**
```bash
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-12345678
```

"available" 상태여야 한다. "pending" 또는 "failed"면 문제가 있다.

**2. 보안 그룹:**
Endpoint의 보안 그룹이 인바운드 트래픽을 허용하는지 확인.

```bash
aws ec2 describe-security-groups --group-ids sg-12345678
```

필요한 포트가 열려있는지 확인 (예: 443, 80).

**3. NLB 상태 (Endpoint Service):**
NLB의 Target이 정상인지 확인.

```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/...
```

모든 Target이 "healthy" 상태여야 한다.

**4. DNS 리졸브:**
```bash
nslookup vpce-12345678-abcd1234.vpce-svc-12345678.us-west-2.vpce.amazonaws.com
```

Endpoint의 프라이빗 IP가 반환되어야 한다.

### Private DNS가 작동하지 않는다

**1. DNS 검증:**
Endpoint Service의 Private DNS가 검증되었는지 확인.

```bash
aws ec2 describe-vpc-endpoint-service-configurations \
  --service-ids vpce-svc-12345678
```

`PrivateDnsNameVerificationState`가 "verified"여야 한다.

**2. Endpoint 설정:**
Endpoint 생성 시 `--private-dns-enabled` 옵션을 사용했는지 확인.

**3. VPC DNS 설정:**
VPC에서 DNS 해석이 활성화되어 있는지 확인.

```bash
aws ec2 describe-vpc-attribute \
  --vpc-id vpc-12345678 \
  --attribute enableDnsSupport

aws ec2 describe-vpc-attribute \
  --vpc-id vpc-12345678 \
  --attribute enableDnsHostnames
```

둘 다 true여야 한다.

## 비용

### Interface Endpoint 비용

**시간당 요금:**
$0.01/시간 per Endpoint per AZ

**예시:**
- Endpoint 1개
- 2개 AZ
- 시간당: $0.01 × 2 = $0.02
- 월간: $0.02 × 730시간 = $14.60

**데이터 전송:**
$0.01/GB

**예시:**
100GB 전송 = $1.00

### Gateway Endpoint 비용

**무료:**
Gateway Endpoint는 비용이 없다. S3와 DynamoDB는 Gateway Endpoint를 사용하는 것이 좋다.

### Endpoint Service 비용

Endpoint Service 자체는 무료다. NLB 비용만 발생한다.

**NLB 비용:**
- 시간당: $0.0225
- LCU: $0.006 per LCU-hour

**예시:**
- NLB 1개
- 100 LCU/시간
- 시간당: $0.0225 + ($0.006 × 100) = $0.6225
- 월간: $0.6225 × 730 = $454

### NAT Gateway와 비교

**NAT Gateway:**
- 시간당: $0.045
- 데이터: $0.045/GB
- 100GB: $0.045 × 730 + $0.045 × 100 = $37.35

**Interface Endpoint (2 AZ):**
- 시간당: $0.02
- 데이터: $0.01/GB
- 100GB: $0.02 × 730 + $0.01 × 100 = $15.60

Endpoint가 더 저렴하다. AWS 서비스 접근 시 NAT Gateway 대신 Endpoint를 사용하는 것이 좋다.

## 참고

- AWS PrivateLink 개발자 가이드: https://docs.aws.amazon.com/vpc/latest/privatelink/
- PrivateLink 요금: https://aws.amazon.com/privatelink/pricing/
- VPC Endpoint Services: https://docs.aws.amazon.com/vpc/latest/privatelink/endpoint-service.html
- Gateway vs Interface Endpoint: https://docs.aws.amazon.com/vpc/latest/privatelink/vpce-gateway.html

