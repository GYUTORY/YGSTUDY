
# 🌐 AWS VPC에서 Private Subnet과 Public Subnet

## 📚 개요

AWS VPC(Virtual Private Cloud)는 AWS에서 제공하는 **가상 네트워크 환경**으로, 사용자가 자신의 클라우드 네트워크를 구성할 수 있도록 합니다.

- **Private Subnet (프라이빗 서브넷)**: 인터넷과 직접 연결되지 않은 서브넷.
- **Public Subnet (퍼블릭 서브넷)**: 인터넷과 직접 연결 가능한 서브넷.

---

## ✅ VPC (Virtual Private Cloud)란?

**VPC (가상 사설 클라우드)**는 AWS에서 제공하는 **사용자 정의 가상 네트워크**입니다.

- **서브넷 (Subnet)**: VPC 내에서 IP 주소 범위를 나눈 **서브 네트워크**.
- **보안 그룹 (Security Group)**: 인스턴스 수준의 **방화벽 규칙**을 정의.
- **라우팅 테이블 (Route Table)**: 트래픽이 이동하는 경로를 정의.

---

# 📦 Private Subnet (프라이빗 서브넷)

### ✅ 정의
- **인터넷 게이트웨이 (IGW)**가 연결되지 않은 서브넷.
- **외부 인터넷과 직접 통신 불가**.
- 내부적으로 **데이터베이스, 애플리케이션 서버** 등을 배치할 때 사용.

### 📦 Private Subnet 사용 예제

1. **데이터베이스 배치:** 외부 접근을 차단하기 위해 RDS(Database)를 배치.
2. **백엔드 서버 배치:** 외부에 노출되지 않는 내부 API 서버.

### 📦 Private Subnet 설정 예시 (CIDR 범위: `10.0.2.0/24`)

- **IP 범위:** `10.0.2.0 - 10.0.2.255`
- **라우팅 테이블:** 인터넷 게이트웨이 없음

```plaintext
+---------------------+
|  Private Subnet     |
|  CIDR: 10.0.2.0/24  |
|  인터넷 불가         |
|  DB, 백엔드 서버     |
+---------------------+
```

---

# 📦 Public Subnet (퍼블릭 서브넷)

### ✅ 정의
- **인터넷 게이트웨이 (IGW)**를 통해 인터넷과 연결 가능한 서브넷.
- **외부에서 직접 접근 가능**.
- **웹 서버, 로드밸런서, Bastion Host** 등을 배치할 때 사용.

### 📦 Public Subnet 사용 예제

1. **웹 서버 호스팅:** EC2에 웹 애플리케이션을 배포.
2. **로드 밸런서 배치:** 외부에서 트래픽을 받아 내부 프라이빗 서브넷으로 전달.
3. **Bastion Host:** SSH 접근을 위한 보안 게이트웨이 서버.

### 📦 Public Subnet 설정 예시 (CIDR 범위: `10.0.1.0/24`)

- **IP 범위:** `10.0.1.0 - 10.0.1.255`
- **라우팅 테이블:** 인터넷 게이트웨이 연결됨

```plaintext
+---------------------+
|  Public Subnet      |
|  CIDR: 10.0.1.0/24  |
|  인터넷 연결 가능    |
|  웹 서버, 로드밸런서 |
+---------------------+
```

---

# 📦 Private Subnet과 Public Subnet 비교

| **항목**                  | **Private Subnet**                   | **Public Subnet**                     |
|--------------------------|-------------------------------------|-------------------------------------|
| **인터넷 연결 여부**      | ❌ 불가능                           | ✅ 가능                              |
| **주요 용도**             | 데이터베이스, 백엔드 서버           | 웹 서버, 로드밸런서, Bastion Host  |
| **인터넷 게이트웨이 연결** | ❌ 없음                            | ✅ 있음                              |
| **IP 범위 예제**          | `10.0.2.0/24`                     | `10.0.1.0/24`                      |
| **보안**                  | 외부 접근 불가능, 높은 보안 수준    | 외부 접근 가능, 보안 설정 필요       |

---

# 🛠️ **VPC 및 서브넷 생성 예제 (AWS CLI)**

### ✅ 1. VPC 생성

```bash
aws ec2 create-vpc --cidr-block 10.0.0.0/16
```

### ✅ 2. 인터넷 게이트웨이 생성 및 연결

```bash
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway --vpc-id <VPC_ID> --internet-gateway-id <IGW_ID>
```

### ✅ 3. Public Subnet 생성

```bash
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.1.0/24
```

### ✅ 4. Private Subnet 생성

```bash
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.2.0/24
```

### ✅ 5. 라우팅 테이블 구성

- **Public Subnet:** 인터넷 게이트웨이 연결
```bash
aws ec2 create-route --route-table-id <RT_ID> --destination-cidr-block 0.0.0.0/0 --gateway-id <IGW_ID>
```

- **Private Subnet:** NAT 게이트웨이 연결 (외부 요청만 가능)
```bash
aws ec2 create-nat-gateway --subnet-id <PUBLIC_SUBNET_ID>
aws ec2 create-route --route-table-id <PRIVATE_RT_ID> --destination-cidr-block 0.0.0.0/0 --nat-gateway-id <NAT_ID>
```

---

# 📦 VPC 사용 시 보안 고려사항

### ✅ 보안 그룹 (Security Group)
- **퍼블릭 서브넷**: HTTP(80), HTTPS(443) 포트만 허용
- **프라이빗 서브넷**: 데이터베이스 포트 (3306, 5432)만 허용

### ✅ 네트워크 ACL (NACL)
- **퍼블릭 서브넷**: 아웃바운드 트래픽 전부 허용, 인바운드는 제한.
- **프라이빗 서브넷**: 내부 통신만 허용.

---

# ✅ 결론

- **Private Subnet**은 **인터넷과 단절된 내부 네트워크**로, **데이터베이스 및 백엔드 서버** 배포에 적합합니다.
- **Public Subnet**은 **인터넷과 연결 가능한 서브넷**으로, **웹 서버 및 로드 밸런서** 배포에 사용됩니다.
- 보안 강화를 위해 **Private Subnet**에 중요한 데이터를 배치하고, **Public Subnet**은 최소한의 외부 접근만 허용하는 것이 일반적입니다.
