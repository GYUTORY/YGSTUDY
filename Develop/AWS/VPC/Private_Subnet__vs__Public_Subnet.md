
# AWS VPC에서 Private Subnet과 Public Subnet

Amazon Virtual Private Cloud(VPC)는 AWS 클라우드에서 격리된 네트워크 환경을 제공합니다. VPC는 서브넷을 통해 네트워크를 세분화하며, 서브넷은 Public Subnet과 Private Subnet으로 나뉩니다. 이 문서에서는 두 서브넷의 차이와 각각의 사용 사례를 설명합니다.

---

## 서브넷(Subnet)이란?

서브넷은 VPC 내에서 IP 주소 범위를 논리적으로 나누는 네트워크 단위입니다. 서브넷은 AWS 리전의 특정 가용 영역(AZ, Availability Zone)에 속하며, 인터넷 게이트웨이 및 라우팅 설정에 따라 Public Subnet 또는 Private Subnet으로 분류됩니다.

---

## Public Subnet

Public Subnet은 인터넷과 직접 통신할 수 있는 서브넷입니다.

### Public Subnet의 특징
- **인터넷 연결 가능:**  
  인터넷 게이트웨이(Internet Gateway, IGW)와 연결된 라우팅 테이블이 설정되어 있어 인터넷과 통신할 수 있습니다.
- **퍼블릭 IP 할당 가능:**  
  퍼블릭 IP 주소(또는 Elastic IP)를 가진 인스턴스가 배포될 수 있습니다.
- **사용 사례:**
    - 웹 서버(HTTP/HTTPS)
    - Bastion Host(Private Subnet 접근용)
    - 애플리케이션 서버(인터넷 트래픽이 필요한 경우)

### Public Subnet 라우팅 테이블 예시

```json
{
  "Destination": "0.0.0.0/0",
  "Target": "igw-xxxxxxxx"
}
```

위의 라우팅 테이블은 모든 외부 트래픽(`0.0.0.0/0`)을 인터넷 게이트웨이(IGW)로 전달합니다.

---

## Private Subnet

Private Subnet은 인터넷과 직접 연결되지 않는 서브넷입니다.

### Private Subnet의 특징
- **인터넷과 단절:**  
  라우팅 테이블에 인터넷 게이트웨이가 설정되지 않음.
- **NAT Gateway를 통해 제한적 인터넷 통신 가능:**  
  아웃바운드 트래픽이 필요한 경우, NAT Gateway 또는 NAT 인스턴스를 사용하여 인터넷에 접근할 수 있습니다.
- **보안이 강화된 환경 제공:**  
  외부에서 직접 접근할 수 없기 때문에 민감한 데이터와 서비스를 안전하게 보호할 수 있습니다.
- **사용 사례:**
    - 데이터베이스 서버(RDS, DynamoDB)
    - 백엔드 애플리케이션 서버
    - 캐시 서버(Redis, Memcached)

### Private Subnet 라우팅 테이블 예시

```json
{
  "Destination": "0.0.0.0/0",
  "Target": "nat-xxxxxxxx"
}
```

위의 라우팅 테이블은 모든 외부 트래픽(`0.0.0.0/0`)을 NAT Gateway를 통해 전달합니다.

---

## Public Subnet과 Private Subnet의 비교

| 구분               | Public Subnet                            | Private Subnet                            |
|--------------------|------------------------------------------|------------------------------------------|
| **인터넷 게이트웨이** | 있음                                     | 없음                                     |
| **퍼블릭 IP**        | 할당 가능                                 | 할당 불가                                 |
| **사용 사례**        | 웹 서버, Bastion Host 등                 | 데이터베이스, 내부 서비스 등              |
| **보안**            | 인터넷 노출 가능                          | 인터넷과 단절, 보안 강화                  |
| **인터넷 접근 방식** | IGW를 통해 직접 접근                     | NAT Gateway 또는 NAT 인스턴스를 통해 제한적 접근 |

---

## VPC 아키텍처 예시

### 기본 구조
1. **Public Subnet**에 웹 서버 배포.
2. **Private Subnet**에 데이터베이스 배포.
3. NAT Gateway를 통해 Private Subnet에서 외부로 아웃바운드 트래픽 허용.

### 다이어그램

```plaintext
+-------------------------+
|        Internet         |
+-------------------------+
           |
           ▼
+-------------------------+
|    Internet Gateway     |
+-------------------------+
           |
  +-----------------+
  | Public Subnet   | <-- 웹 서버, Bastion Host
  +-----------------+
           |
  +-----------------+
  | NAT Gateway     |
  +-----------------+
           |
  +-----------------+
  | Private Subnet  | <-- 데이터베이스, 내부 서비스
  +-----------------+
```

---

## 참고 사항

- **NAT Gateway 요금:** NAT Gateway를 사용할 경우 데이터 처리량에 따라 추가 요금이 발생합니다.
- **보안 그룹:** 서브넷에서 사용하는 리소스는 보안 그룹을 통해 세부적인 트래픽 제어가 가능합니다.
- **VPC 엔드포인트:** Private Subnet에서 AWS 서비스(S3, DynamoDB 등)와 통신하려면 VPC 엔드포인트를 사용할 수 있습니다.

