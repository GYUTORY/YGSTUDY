---
title: AWS VPC Private Subnet vs Public Subnet
tags: [aws, vpc, privatesubnet, publicsubnet, 네트워크보안, 클라우드아키텍처]
updated: 2025-12-02
---

# AWS VPC에서 Private Subnet과 Public Subnet

## 들어가며

- 클라우드 아키텍처를 설계할 때 가장 중요한 결정 중 하나가 바로 서브넷 구성입니다. AWS VPC(Virtual Private Cloud)에서 Private Subnet과 Public Subnet을 어떻게 구분하고 활용할지에 대한 이해는 안전하고 효율적인 클라우드 인프라 구축의 핵심입니다.

- 단순히 정의를 나열하는 것이 아니라, 실제 운영 환경에서 왜 이런 구분이 필요한지, 어떤 상황에서 어떤 서브넷을 선택해야 하는지에 대해 다룹니다.

## VPC의 본질적 이해

### VPC란 무엇인가?

VPC는 AWS 클라우드 내에서 논리적으로 격리된 네트워크 환경을 제공합니다. 마치 전통적인 데이터센터에서 자신만의 네트워크를 운영하는 것과 같지만, 클라우드의 유연성과 확장성을 모두 갖추고 있습니다.

VPC의 핵심 특징:
- **논리적 격리**: 다른 VPC와 완전히 분리된 네트워크 환경
- **IP 주소 범위 제어**: 사용자가 직접 CIDR 블록을 지정
- **네트워크 구성 자유도**: 라우팅, 보안 그룹, 서브넷 등을 자유롭게 설계
- **하이브리드 연결**: 온프레미스 환경과의 연결 가능

### 서브넷의 역할과 중요성

서브넷은 VPC 내에서 IP 주소 범위를 나누는 논리적 단위입니다. 하지만 단순히 IP를 나누는 것이 아니라, **보안 경계**와 **네트워크 정책**을 정의하는 핵심 요소입니다.

서브넷을 구분하는 이유:
1. **보안 격리**: 민감한 리소스와 외부 접근 가능한 리소스 분리
2. **네트워크 정책**: 서브넷별로 다른 라우팅 및 보안 규칙 적용
3. **가용성**: 여러 가용 영역에 분산 배치로 장애 대응
4. **비용 최적화**: 리소스별로 적절한 네트워크 구성 적용

## Private Subnet: 내부 보안의 요새

### Private Subnet의 본질

Private Subnet은 인터넷과 직접적인 연결이 없는 서브넷입니다. 이는 단순히 "인터넷에 연결되지 않았다"는 의미를 넘어서, **의도적으로 격리된 보안 영역**을 의미합니다.

Private Subnet의 핵심 특징:
- **인터넷 게이트웨이 없음**: 직접적인 인터넷 접근 불가
- **NAT 게이트웨이를 통한 아웃바운드**: 필요한 경우에만 외부 통신
- **내부 통신 중심**: VPC 내부 리소스 간 통신에 최적화
- **보안 우선**: 외부 위협으로부터 최대한 보호

### 왜 Private Subnet이 필요한가?

#### 1. 데이터 보호의 핵심
가장 중요한 이유는 **데이터 보호**입니다. 데이터베이스, 사용자 정보, 비즈니스 로직 등 민감한 정보는 절대 외부에서 직접 접근할 수 없어야 합니다. Private Subnet은 이런 리소스들을 외부 위협으로부터 보호하는 첫 번째 방어선입니다.

#### 2. 네트워크 공격 표면 최소화
외부에서 직접 접근할 수 있는 리소스가 적을수록 공격자가 침투할 수 있는 경로가 줄어듭니다. Private Subnet에 배치된 리소스들은 외부에서 직접 스캔하거나 공격할 수 없어 전체적인 보안 수준을 크게 향상시킵니다.

#### 3. 규정 준수 요구사항
많은 산업 분야에서 데이터 보호와 관련된 엄격한 규정이 있습니다. PCI DSS, HIPAA, GDPR 등은 모두 민감한 데이터의 접근을 제한하고 보호할 것을 요구합니다. Private Subnet은 이런 규정 준수를 위한 기술적 기반을 제공합니다.

### Private Subnet에 배치해야 할 리소스들

#### 데이터베이스 서버
- **RDS 인스턴스**: MySQL, PostgreSQL, Oracle 등
- **Aurora 클러스터**: 고가용성 데이터베이스
- **DynamoDB**: NoSQL 데이터베이스 (VPC 엔드포인트 사용)
- **ElastiCache**: Redis, Memcached 캐시 서버

#### 백엔드 애플리케이션
- **API 서버**: RESTful API, GraphQL 서버
- **마이크로서비스**: 비즈니스 로직을 담당하는 서비스들
- **배치 처리 서버**: 데이터 처리, ETL 작업
- **메시지 큐**: SQS, RabbitMQ 등

#### 내부 도구 및 서비스
- **모니터링 서버**: Prometheus, Grafana
- **로그 수집 서버**: ELK Stack, Fluentd
- **CI/CD 서버**: Jenkins, GitLab Runner
- **백업 서버**: 데이터 백업 및 복원

### Private Subnet의 네트워크 아키텍처

```
Internet
    ↓
[Internet Gateway]
    ↓
[Public Subnet]
    ↓ (NAT Gateway)
[Private Subnet]
    ├── Database Servers
    ├── Backend Applications
    ├── Cache Servers
    └── Internal Tools
```

이 구조에서 Private Subnet의 리소스들은:
- **인바운드**: Public Subnet의 리소스에서만 접근 가능
- **아웃바운드**: NAT Gateway를 통해서만 인터넷 접근
- **내부 통신**: VPC 내 다른 서브넷과 자유로운 통신

## Public Subnet: 외부와의 연결점

### Public Subnet의 역할

Public Subnet은 인터넷과 직접 연결된 서브넷으로, 외부 사용자나 시스템이 접근할 수 있는 리소스들을 배치하는 곳입니다. 하지만 "Public"이라는 이름과 달리, 이는 **제어된 공개**를 의미합니다.

Public Subnet의 핵심 특징:
- **인터넷 게이트웨이 연결**: 직접적인 인터넷 접근 가능
- **외부 접근 허용**: 웹 트래픽, API 호출 등 수신
- **보안 설정 필수**: 외부 위협에 노출되므로 강력한 보안 필요
- **최소 권한 원칙**: 꼭 필요한 리소스만 배치

### Public Subnet이 필요한 이유

#### 1. 사용자 접근성
웹 애플리케이션, API, 모바일 앱 등은 사용자가 접근할 수 있어야 합니다. 이런 서비스들은 Public Subnet에 배치되어 외부에서 접근 가능해야 합니다.

#### 2. 로드 밸런싱
대부분의 웹 서비스는 여러 인스턴스에 트래픽을 분산시킵니다. 로드 밸런서는 Public Subnet에 배치되어 외부 트래픽을 받아 내부의 여러 인스턴스로 분산시킵니다.

#### 3. 관리 접근
시스템 관리자나 개발자가 서버에 접근할 수 있는 Bastion Host나 관리 도구들은 Public Subnet에 배치됩니다.

### Public Subnet에 배치해야 할 리소스들

#### 웹 서버 및 프론트엔드
- **웹 서버**: Apache, Nginx, IIS
- **정적 웹사이트**: S3 + CloudFront
- **SPA 애플리케이션**: React, Vue, Angular 앱
- **API Gateway**: 외부 API 노출

#### 로드 밸런서
- **Application Load Balancer (ALB)**: HTTP/HTTPS 트래픽
- **Network Load Balancer (NLB)**: TCP/UDP 트래픽
- **Classic Load Balancer**: 레거시 애플리케이션

#### 관리 및 접근 도구
- **Bastion Host**: SSH 접근을 위한 점프 서버
- **VPN 서버**: 원격 접근을 위한 VPN
- **관리 도구**: 모니터링, 로깅 도구의 웹 인터페이스

#### CDN 및 캐시
- **CloudFront**: 글로벌 CDN
- **엣지 서버**: 지역별 캐시 서버
- **리버스 프록시**: Nginx, HAProxy

### Public Subnet의 보안 고려사항

#### 1. 최소 권한 원칙
Public Subnet에는 꼭 필요한 리소스만 배치해야 합니다. 민감한 데이터나 비즈니스 로직은 절대 Public Subnet에 두지 않습니다.

#### 2. 강력한 보안 그룹 설정
- **특정 포트만 개방**: 80(HTTP), 443(HTTPS) 등 필요한 포트만
- **IP 기반 접근 제어**: 특정 IP 대역에서만 접근 허용
- **프로토콜 제한**: 필요한 프로토콜만 허용

#### 3. 네트워크 ACL 활용
서브넷 레벨에서 추가적인 보안을 제공하는 NACL을 적극 활용합니다.

#### 4. WAF 및 DDoS 보호
- **AWS WAF**: 웹 애플리케이션 방화벽
- **AWS Shield**: DDoS 공격 방어
- **CloudFront**: 추가적인 보안 계층

## 서브넷 간 통신 패턴

### 일반적인 통신 흐름

```
사용자 요청 → Public Subnet (ALB) → Private Subnet (App Server) → Private Subnet (Database)
```

이 패턴에서:
1. **사용자**: 인터넷을 통해 Public Subnet의 ALB에 접근
2. **ALB**: 요청을 Private Subnet의 애플리케이션 서버로 전달
3. **App Server**: 필요한 데이터를 Private Subnet의 데이터베이스에서 조회
4. **응답**: 역순으로 사용자에게 전달

### 보안을 고려한 통신 설계

#### 1. 단방향 통신 원칙
- Public → Private: 허용 (외부 요청 처리)
- Private → Public: 제한 (NAT Gateway를 통해서만)
- Private → Private: 허용 (내부 서비스 간 통신)

#### 2. 네트워크 분할
- **DMZ 개념**: Public Subnet을 DMZ로 활용
- **계층화된 보안**: 여러 보안 계층으로 방어
- **네트워크 세분화**: 기능별, 환경별 서브넷 분리

## 실제 운영에서의 고려사항

### 비용 최적화

#### 1. NAT Gateway 비용
Private Subnet의 아웃바운드 트래픽은 NAT Gateway를 통해야 하므로 추가 비용이 발생합니다. 이를 최적화하기 위해:
- **불필요한 아웃바운드 트래픽 최소화**
- **VPC 엔드포인트 활용**: AWS 서비스 접근 시
- **프록시 서버 활용**: 여러 인스턴스가 하나의 NAT Gateway 공유

#### 2. 데이터 전송 비용
Public Subnet의 인터넷 트래픽은 데이터 전송 비용이 발생합니다:
- **CDN 활용**: 정적 콘텐츠는 CloudFront 사용
- **압축 및 최적화**: 전송 데이터 크기 최소화
- **캐싱**: 불필요한 외부 요청 최소화

### 성능 최적화

#### 1. 네트워크 지연 최소화
- **가용 영역 내 통신**: 같은 AZ 내 서브넷 간 통신
- **네트워크 최적화**: 적절한 인스턴스 타입 선택
- **연결 풀링**: 데이터베이스 연결 최적화

#### 2. 확장성 고려
- **서브넷 크기 계획**: 미래 확장을 고려한 CIDR 블록 설계
- **멀티 AZ 배치**: 고가용성을 위한 여러 AZ 활용
- **자동 스케일링**: 트래픽에 따른 자동 확장

### 모니터링 및 로깅

#### 1. VPC Flow Logs
네트워크 트래픽을 모니터링하여:
- **비정상적인 트래픽 패턴 감지**
- **보안 위협 분석**
- **성능 문제 진단**

#### 2. CloudWatch 메트릭
- **네트워크 성능 모니터링**
- **보안 그룹 규칙 위반 감지**
- **리소스 사용률 추적**

## 보안 모범 사례

### 1. 방어적 설계
- **기본 거부 원칙**: 명시적으로 허용하지 않은 모든 트래픽 차단
- **최소 권한**: 필요한 최소한의 접근만 허용
- **다층 보안**: 여러 보안 계층으로 방어

### 2. 정기적인 보안 점검
- **보안 그룹 규칙 검토**: 불필요한 규칙 제거
- **네트워크 ACL 점검**: 서브넷 레벨 보안 강화
- **접근 로그 분석**: 비정상적인 접근 패턴 감지

### 3. 인시던트 대응
- **자동 차단**: 의심스러운 트래픽 자동 차단
- **알림 시스템**: 보안 위협 발생 시 즉시 알림
- **복구 계획**: 보안 사고 발생 시 대응 절차

## 마무리

Private Subnet과 Public Subnet의 구분은 단순한 네트워크 설계가 아니라, **보안, 성능, 비용을 모두 고려한 종합적인 아키텍처 결정**입니다. 

올바른 서브넷 설계는:
- **보안을 강화**하면서도
- **사용자 경험을 보장**하고
- **운영 비용을 최적화**할 수 있게 해줍니다.

실제 프로젝트에서는 비즈니스 요구사항, 보안 정책, 성능 요구사항을 종합적으로 고려하여 서브넷을 설계해야 합니다.

## 참고 자료

1. [AWS VPC 사용자 가이드](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)
2. [AWS 보안 모범 사례](https://aws.amazon.com/architecture/security-identity-compliance/)
3. [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
4. [AWS 네트워크 보안 백서](https://d1.awsstatic.com/whitepapers/Security/AWS_Security_Best_Practices.pdf)
5. [VPC 네트워킹 가이드](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Networking.html)