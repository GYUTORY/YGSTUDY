# 🌐 AWS VPC에서 Private Subnet과 Public Subnet

## 📚 개요

AWS VPC(Virtual Private Cloud)는 AWS에서 제공하는 **가상 네트워크 환경**으로, 사용자가 자신의 클라우드 네트워크를 구성할 수 있도록 합니다. 이는 마치 데이터센터 내에서 자신만의 네트워크를 운영하는 것과 같습니다.

- **Private Subnet (프라이빗 서브넷)**: 인터넷과 직접 연결되지 않은 서브넷으로, 내부 리소스 보호에 중점을 둡니다.
- **Public Subnet (퍼블릭 서브넷)**: 인터넷과 직접 연결 가능한 서브넷으로, 외부와의 통신이 필요한 리소스를 배치합니다.

---

## ✅ VPC (Virtual Private Cloud)란?

**VPC (가상 사설 클라우드)**는 AWS에서 제공하는 **사용자 정의 가상 네트워크**입니다. 이는 AWS 클라우드 내에서 논리적으로 격리된 네트워크를 생성할 수 있게 해줍니다.

### 📦 VPC의 주요 구성 요소

1. **서브넷 (Subnet)**
   - VPC 내에서 IP 주소 범위를 나눈 **서브 네트워크**
   - 가용 영역(AZ)별로 분리되어 고가용성 보장
   - CIDR 블록으로 IP 주소 범위 지정

2. **보안 그룹 (Security Group)**
   - 인스턴스 수준의 **방화벽 규칙**을 정의
   - 인바운드/아웃바운드 트래픽 제어
   - 상태 저장(stateful) 방식으로 동작

3. **라우팅 테이블 (Route Table)**
   - 트래픽이 이동하는 경로를 정의
   - 서브넷별로 다른 라우팅 규칙 적용 가능
   - 인터넷 게이트웨이, NAT 게이트웨이 등과 연결

4. **인터넷 게이트웨이 (Internet Gateway)**
   - VPC와 인터넷 간의 통신을 가능하게 하는 게이트웨이
   - 수평 확장 가능하고 가용성이 높은 구성
   - VPC당 하나만 연결 가능

5. **NAT 게이트웨이 (NAT Gateway)**
   - 프라이빗 서브넷의 인스턴스가 인터넷과 통신할 수 있게 해주는 게이트웨이
   - 퍼블릭 서브넷에 위치
   - 아웃바운드 트래픽만 허용

---

# 📦 Private Subnet (프라이빗 서브넷)

### ✅ 정의 및 특징
- **인터넷 게이트웨이 (IGW)**가 연결되지 않은 서브넷
- **외부 인터넷과 직접 통신 불가**
- 내부적으로 **데이터베이스, 애플리케이션 서버** 등을 배치
- **NAT 게이트웨이**를 통해서만 외부 통신 가능
- **보안성이 매우 높음**

### 📦 Private Subnet 사용 사례

1. **데이터베이스 서버**
   - RDS, Aurora, DynamoDB 등의 데이터베이스 서버
   - 민감한 데이터 보호
   - 직접적인 외부 접근 차단

2. **백엔드 애플리케이션 서버**
   - API 서버
   - 마이크로서비스
   - 내부 처리 로직

3. **캐시 서버**
   - ElastiCache
   - Redis/Memcached 서버
   - 세션 저장소

4. **파일 스토리지**
   - EFS (Elastic File System)
   - 내부 파일 서버
   - 백업 저장소

### 📦 Private Subnet 아키텍처 예시

```plaintext
+---------------------+     +---------------------+
|  Public Subnet      |     |  Private Subnet     |
|  (10.0.1.0/24)      |     |  (10.0.2.0/24)      |
|                     |     |                     |
|  +---------------+  |     |  +---------------+  |
|  |  NAT Gateway  |--+---->|  |  RDS Instance |  |
|  +---------------+  |     |  +---------------+  |
|                     |     |                     |
|  +---------------+  |     |  +---------------+  |
|  |  Load Balancer|--+---->|  |  App Server   |  |
|  +---------------+  |     |  +---------------+  |
+---------------------+     +---------------------+
```

### 📦 Private Subnet 보안 설정

1. **보안 그룹 설정**
```json
{
    "SecurityGroup": {
        "InboundRules": [
            {
                "Protocol": "TCP",
                "Port": 3306,
                "Source": "10.0.1.0/24"
            }
        ],
        "OutboundRules": [
            {
                "Protocol": "TCP",
                "Port": 443,
                "Destination": "0.0.0.0/0"
            }
        ]
    }
}
```

2. **네트워크 ACL 설정**
```json
{
    "NetworkACL": {
        "InboundRules": [
            {
                "RuleNumber": 100,
                "Protocol": "TCP",
                "PortRange": "3306",
                "Action": "ALLOW",
                "CIDR": "10.0.1.0/24"
            }
        ],
        "OutboundRules": [
            {
                "RuleNumber": 100,
                "Protocol": "TCP",
                "PortRange": "443",
                "Action": "ALLOW",
                "CIDR": "0.0.0.0/0"
            }
        ]
    }
}
```

---

# 📦 Public Subnet (퍼블릭 서브넷)

### ✅ 정의 및 특징
- **인터넷 게이트웨이 (IGW)**를 통해 인터넷과 연결 가능한 서브넷
- **외부에서 직접 접근 가능**
- **웹 서버, 로드밸런서, Bastion Host** 등을 배치
- **보안 설정이 매우 중요**
- **비용이 더 높을 수 있음** (인터넷 트래픽 비용)

### 📦 Public Subnet 사용 사례

1. **웹 서버**
   - 정적 웹사이트 호스팅
   - 동적 웹 애플리케이션
   - API 게이트웨이

2. **로드 밸런서**
   - Application Load Balancer (ALB)
   - Network Load Balancer (NLB)
   - Classic Load Balancer

3. **Bastion Host**
   - SSH 접근을 위한 점프 서버
   - 관리자 접근 제어
   - 감사 로그 기록

4. **CDN 엣지 서버**
   - CloudFront 엣지 로케이션
   - 캐시 서버
   - 정적 콘텐츠 제공

### 📦 Public Subnet 아키텍처 예시

```plaintext
+---------------------+     +---------------------+
|  Internet           |     |  Public Subnet      |
|                     |     |  (10.0.1.0/24)      |
|  +---------------+  |     |  +---------------+  |
|  |  Users        |--+---->|  |  ALB          |  |
|  +---------------+  |     |  +---------------+  |
|                     |     |                     |
|  +---------------+  |     |  +---------------+  |
|  |  CDN          |--+---->|  |  Web Server   |  |
|  +---------------+  |     |  +---------------+  |
+---------------------+     +---------------------+
```

### 📦 Public Subnet 보안 설정

1. **보안 그룹 설정**
```json
{
    "SecurityGroup": {
        "InboundRules": [
            {
                "Protocol": "TCP",
                "Port": 80,
                "Source": "0.0.0.0/0"
            },
            {
                "Protocol": "TCP",
                "Port": 443,
                "Source": "0.0.0.0/0"
            }
        ],
        "OutboundRules": [
            {
                "Protocol": "TCP",
                "Port": 443,
                "Destination": "0.0.0.0/0"
            }
        ]
    }
}
```

2. **네트워크 ACL 설정**
```json
{
    "NetworkACL": {
        "InboundRules": [
            {
                "RuleNumber": 100,
                "Protocol": "TCP",
                "PortRange": "80",
                "Action": "ALLOW",
                "CIDR": "0.0.0.0/0"
            },
            {
                "RuleNumber": 110,
                "Protocol": "TCP",
                "PortRange": "443",
                "Action": "ALLOW",
                "CIDR": "0.0.0.0/0"
            }
        ],
        "OutboundRules": [
            {
                "RuleNumber": 100,
                "Protocol": "TCP",
                "PortRange": "443",
                "Action": "ALLOW",
                "CIDR": "0.0.0.0/0"
            }
        ]
    }
}
```

---

# 🛠️ **VPC 및 서브넷 생성 예제 (AWS CLI)**

### ✅ 1. VPC 생성

```bash
# VPC 생성
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=MyVPC}]'

# VPC ID 저장
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=MyVPC" --query 'Vpcs[0].VpcId' --output text)
```

### ✅ 2. 인터넷 게이트웨이 생성 및 연결

```bash
# IGW 생성
aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=MyIGW}]'

# IGW ID 저장
IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=MyIGW" --query 'InternetGateways[0].InternetGatewayId' --output text)

# IGW를 VPC에 연결
aws ec2 attach-internet-gateway \
    --vpc-id $VPC_ID \
    --internet-gateway-id $IGW_ID
```

### ✅ 3. Public Subnet 생성

```bash
# 가용영역 확인
AZ=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].ZoneId' --output text)

# Public Subnet 생성
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone-id $AZ \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=PublicSubnet}]'

# Public Subnet ID 저장
PUBLIC_SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=PublicSubnet" --query 'Subnets[0].SubnetId' --output text)
```

### ✅ 4. Private Subnet 생성

```bash
# Private Subnet 생성
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone-id $AZ \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=PrivateSubnet}]'

# Private Subnet ID 저장
PRIVATE_SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=PrivateSubnet" --query 'Subnets[0].SubnetId' --output text)
```

### ✅ 5. 라우팅 테이블 구성

```bash
# Public 라우팅 테이블 생성
aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=PublicRT}]'

# Public 라우팅 테이블 ID 저장
PUBLIC_RT_ID=$(aws ec2 describe-route-tables --filters "Name=tag:Name,Values=PublicRT" --query 'RouteTables[0].RouteTableId' --output text)

# 인터넷 게이트웨이 라우팅 추가
aws ec2 create-route \
    --route-table-id $PUBLIC_RT_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID

# Public Subnet에 라우팅 테이블 연결
aws ec2 associate-route-table \
    --subnet-id $PUBLIC_SUBNET_ID \
    --route-table-id $PUBLIC_RT_ID

# NAT 게이트웨이 생성
aws ec2 create-nat-gateway \
    --subnet-id $PUBLIC_SUBNET_ID \
    --allocation-id $(aws ec2 allocate-address --query 'AllocationId' --output text) \
    --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=MyNAT}]'

# NAT 게이트웨이 ID 저장
NAT_ID=$(aws ec2 describe-nat-gateways --filters "Name=tag:Name,Values=MyNAT" --query 'NatGateways[0].NatGatewayId' --output text)

# Private 라우팅 테이블 생성
aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=PrivateRT}]'

# Private 라우팅 테이블 ID 저장
PRIVATE_RT_ID=$(aws ec2 describe-route-tables --filters "Name=tag:Name,Values=PrivateRT" --query 'RouteTables[0].RouteTableId' --output text)

# NAT 게이트웨이 라우팅 추가
aws ec2 create-route \
    --route-table-id $PRIVATE_RT_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id $NAT_ID

# Private Subnet에 라우팅 테이블 연결
aws ec2 associate-route-table \
    --subnet-id $PRIVATE_SUBNET_ID \
    --route-table-id $PRIVATE_RT_ID
```

---

# 📦 VPC 사용 시 보안 고려사항

### ✅ 보안 그룹 (Security Group) 설정

1. **퍼블릭 서브넷 보안 그룹**
   - HTTP(80), HTTPS(443) 포트만 허용
   - 특정 IP 대역에서만 접근 허용
   - 불필요한 포트는 모두 차단

2. **프라이빗 서브넷 보안 그룹**
   - 데이터베이스 포트 (3306, 5432)만 허용
   - 퍼블릭 서브넷에서만 접근 가능하도록 설정
   - 내부 통신만 허용

### ✅ 네트워크 ACL (NACL) 설정

1. **퍼블릭 서브넷 NACL**
   - 아웃바운드 트래픽 전부 허용
   - 인바운드는 필요한 포트만 허용
   - 기본적으로 모든 트래픽 차단

2. **프라이빗 서브넷 NACL**
   - 내부 통신만 허용
   - NAT 게이트웨이를 통한 아웃바운드만 허용
   - 불필요한 트래픽 차단

### ✅ 추가 보안 설정

1. **VPC Flow Logs**
   - 네트워크 트래픽 모니터링
   - 보안 분석 및 문제 해결
   - CloudWatch Logs에 저장

2. **AWS WAF**
   - 웹 애플리케이션 방화벽
   - SQL 인젝션 방지
   - XSS 공격 방지

3. **AWS Shield**
   - DDoS 공격 방어
   - 자동 보호 기능
   - 실시간 모니터링

---

# ✅ 결론

- **Private Subnet**은 **인터넷과 단절된 내부 네트워크**로, **데이터베이스 및 백엔드 서버** 배포에 적합합니다.
- **Public Subnet**은 **인터넷과 연결 가능한 서브넷**으로, **웹 서버 및 로드 밸런서** 배포에 사용됩니다.
- 보안 강화를 위해 **Private Subnet**에 중요한 데이터를 배치하고, **Public Subnet**은 최소한의 외부 접근만 허용하는 것이 일반적입니다.
- **NAT 게이트웨이**를 통해 프라이빗 서브넷의 인스턴스가 안전하게 외부와 통신할 수 있습니다.
- **보안 그룹**과 **네트워크 ACL**을 적절히 구성하여 네트워크 보안을 강화해야 합니다.
- **VPC Flow Logs**를 활성화하여 네트워크 트래픽을 모니터링하고 보안 위협을 감지할 수 있습니다.

---

# 📚 참고 자료

1. [AWS VPC 공식 문서](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)
2. [AWS 보안 모범 사례](https://aws.amazon.com/architecture/security-identity-compliance/)
3. [AWS 네트워크 보안](https://aws.amazon.com/security/network-security/)
4. [AWS 아키텍처 센터](https://aws.amazon.com/architecture/)
