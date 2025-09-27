---
title: AWS Route 53
tags: [aws, networking-and-content-delivery, route-53, dns]
updated: 2025-09-23
---

# AWS Route 53

## 개요

### Route 53이란?

AWS Route 53은 **인터넷의 주소록 역할을 하는 DNS(Domain Name System) 서비스**입니다. 사용자가 입력한 도메인 이름을 실제 서버의 IP 주소로 변환해주는 핵심 인프라 서비스입니다.

**이름의 유래**
- **Route**: 경로를 찾아주는 역할
- **53**: DNS 프로토콜이 사용하는 포트 번호
- 즉, "53번 포트로 경로를 찾아주는 서비스"

### DNS의 기본 개념

DNS는 **인터넷의 전화번호부**라고 생각하면 됩니다. 사람이 기억하기 쉬운 도메인 이름(예: www.google.com)을 컴퓨터가 이해하는 IP 주소(예: 142.250.191.78)로 변환하는 시스템입니다.

**DNS 동작 과정**
1. 사용자가 브라우저에 도메인 입력
2. 로컬 DNS 서버에 'example.com의 IP가 뭐야?'라고 질의
3. Route 53이 '192.168.1.1'이라고 응답
4. 브라우저가 해당 IP로 연결

### 도메인 구조 이해

```
www.example.com
│   │      │
│   │      └── TLD (Top Level Domain): .com, .net, .org
│   └────────── Second Level Domain: example
└────────────── Subdomain: www
```

- **TLD (Top Level Domain)**: 최상위 도메인 (.com, .net, .org 등)
- **Second Level Domain**: 실제 도메인 이름 (example)
- **Subdomain**: 하위 도메인 (www, mail, blog 등)

## Route 53의 핵심 기능

### 1. 도메인 등록 및 관리

Route 53은 도메인 등록 기관(Registrar) 역할도 수행합니다. 400개 이상의 TLD를 지원하며, 도메인 등록부터 DNS 관리까지 원스톱으로 처리할 수 있습니다.

**도메인 등록 과정**
1. 도메인 이름 검색 및 가용성 확인
2. 등록 기간 선택 (1-10년)
3. 연락처 정보 입력
4. 개인정보 보호 서비스 선택
5. 결제 및 등록 완료

**주요 TLD별 연간 비용**
- .com: $12.00
- .net: $12.00
- .org: $15.00
- .io: $40.00
- .co.kr: $15.00

### 2. DNS 레코드 관리

DNS 레코드는 도메인과 실제 서버를 연결하는 핵심 설정입니다.

**주요 DNS 레코드 타입**

| 레코드 타입 | 설명 | 용도 | 예시 |
|------------|------|------|------|
| **A** | IPv4 주소 매핑 | 웹서버 연결 | example.com → 192.168.1.1 |
| **AAAA** | IPv6 주소 매핑 | IPv6 지원 | example.com → 2001:db8::1 |
| **CNAME** | 도메인 별칭 | 서브도메인 연결 | www.example.com → example.com |
| **MX** | 메일 서버 지정 | 이메일 서비스 | example.com → mail.example.com |
| **TXT** | 텍스트 정보 | 도메인 검증, SPF | example.com → "v=spf1 include:_spf.google.com ~all" |
| **NS** | 네임서버 지정 | DNS 위임 | example.com → ns1.route53.com |
| **PTR** | 역방향 DNS | IP → 도메인 | 192.168.1.1 → example.com |

**TTL (Time To Live)**
- DNS 레코드의 캐시 유지 시간
- 짧을수록: 빠른 변경 반영, 높은 DNS 쿼리 비용
- 길수록: 느린 변경 반영, 낮은 DNS 쿼리 비용
- 일반적 권장값: 300초(5분) ~ 3600초(1시간)

### 3. 호스팅 영역 (Hosted Zone)

호스팅 영역은 특정 도메인의 DNS 레코드들을 관리하는 컨테이너입니다.

**Public Hosted Zone (공개 영역)**
- 인터넷에서 누구나 접근 가능
- 웹사이트, 이메일 서버 등에 사용
- 월 $0.50 비용

**Private Hosted Zone (비공개 영역)**
- VPC 내부에서만 사용
- 내부 서비스, 데이터베이스 등에 사용
- 월 $0.50 비용

### 4. 트래픽 라우팅 정책

Route 53의 가장 강력한 기능 중 하나로, 다양한 조건에 따라 트래픽을 분배할 수 있습니다.

#### 단순 라우팅 (Simple Routing)
- 가장 기본적인 라우팅 방식
- 단일 서버로 운영하는 웹사이트에 적합
- 하나의 도메인을 하나의 IP로 연결

#### 가중치 라우팅 (Weighted Routing)
- 트래픽을 비율에 따라 분배
- A/B 테스트, 점진적 배포에 활용
- 예: 서버 A(70%), 서버 B(30%)

#### 지리적 라우팅 (Geolocation Routing)
- 사용자의 지리적 위치에 따라 서버 선택
- 지역별 콘텐츠 제공, 규정 준수에 활용
- 예: 미국 사용자 → 미국 서버, 아시아 사용자 → 아시아 서버

#### 지연 시간 라우팅 (Latency-based Routing)
- 가장 빠른 응답 시간을 제공하는 서버 선택
- 글로벌 서비스 최적화에 활용
- Route 53이 실시간으로 지연 시간 측정

#### 장애 조치 라우팅 (Failover Routing)
- Primary 서버 장애 시 Secondary 서버로 자동 전환
- 고가용성 구성에 필수
- 헬스 체크와 연동하여 자동 장애 감지

#### 다중값 라우팅 (Multivalue Answer Routing)
- 여러 IP 주소 중 무작위로 선택
- 단순한 로드 밸런싱 효과
- 헬스 체크와 연동하여 정상 서버만 응답

### 5. 헬스 체크 (Health Check)

서버의 상태를 지속적으로 모니터링하여 정상 작동 여부를 확인합니다.

**헬스 체크 타입**
- **HTTP/HTTPS**: 웹 서버 상태 확인
- **TCP**: 포트 연결성 확인
- **CALCULATED**: 여러 헬스 체크 결과를 조합

**헬스 체크 설정**
- **간격**: 10초, 30초 (기본값)
- **타임아웃**: 2초, 3초, 4초, 5초, 6초, 7초, 8초, 9초, 10초
- **실패 임계값**: 1-10 (연속 실패 횟수)
- **성공 임계값**: 1-10 (연속 성공 횟수)

**헬스 체크 활용**
- 장애 조치 라우팅과 연동
- 다중값 라우팅에서 정상 서버만 응답
- CloudWatch 알림 설정

## 실무 활용 사례

### 1. 단일 웹사이트 운영
```
도메인 등록 → Public Hosted Zone 생성 → A 레코드 설정 → CNAME으로 www 서브도메인 연결
```

### 2. 다중 리전 배포
- 여러 AWS 리전에 서버 배포
- 지연 시간 라우팅으로 최적 서버 선택
- 각 리전별 헬스 체크 설정

### 3. 고가용성 구성
- Primary/Secondary 서버 구성
- 장애 조치 라우팅 설정
- 헬스 체크로 자동 장애 감지 및 전환

### 4. A/B 테스트
- 가중치 라우팅으로 트래픽 분배
- 점진적 배포 (10% → 50% → 100%)
- 실시간 트래픽 조정

## 비용 구조

### 도메인 등록 비용
- 연간 $12-40 (TLD에 따라 상이)
- 개인정보 보호 서비스: 연간 $4

### 호스팅 영역 비용
- Public/Private: 월 $0.50
- 쿼리 비용: 월 $0.40/백만 쿼리

### 고급 라우팅 비용
- 지연 시간 기반: 월 $0.60/백만 쿼리
- 지리적 라우팅: 월 $0.70/백만 쿼리

### 헬스 체크 비용
- 기본: 월 $0.50/체크
- 추가 엔드포인트: 월 $0.50/체크

## 보안 고려사항

### DNSSEC (DNS Security Extensions)
- DNS 응답의 무결성 보장
- 도메인 스푸핑 공격 방지
- Route 53에서 자동 관리

### IAM 정책 설정
- 최소 권한 원칙 적용
- 도메인별 접근 권한 제어
- API 호출 로깅

### 도메인 도용 방지
- 도메인 잠금 기능
- 이메일 인증 강화
- 정기적인 도메인 상태 확인

## AWS 서비스와의 통합

### CloudFront
- CDN과 DNS 통합
- 지연 시간 최적화
- 글로벌 엣지 로케이션 활용

### ALB/NLB
- 로드 밸런서와 DNS 연동
- 헬스 체크 통합
- 자동 스케일링 지원

### ACM (AWS Certificate Manager)
- SSL 인증서 자동 검증
- DNS-01 챌린지 지원
- 인증서 자동 갱신

### CloudWatch
- DNS 쿼리 수 모니터링
- 헬스 체크 상태 추적
- 알림 및 대시보드 구성

### CloudTrail
- API 호출 로깅
- 설정 변경 이력 추적
- 보안 감사 지원

## 모범 사례

### 1. DNS 설계
- 적절한 TTL 설정 (300-3600초)
- CNAME vs A 레코드 적절한 선택
- 서브도메인 구조 체계적 설계

### 2. 고가용성
- 다중 AZ 배포
- 헬스 체크 적극 활용
- 장애 조치 계획 수립

### 3. 성능 최적화
- 지연 시간 기반 라우팅 활용
- CloudFront와 연동
- DNS 캐싱 최적화

### 4. 보안
- DNSSEC 활성화
- IAM 정책 세밀하게 설정
- 정기적인 보안 점검

### 5. 모니터링
- CloudWatch 알림 설정
- 헬스 체크 상태 모니터링
- 비용 추적 및 최적화

## VPC Endpoint와 PrivateLink

### VPC Endpoint
VPC 내부에서 퍼블릭 인터넷을 거치지 않고 AWS 서비스에 사설로 연결하는 엔드포인트입니다.

**Gateway VPC Endpoint**
- 라우팅 테이블에 목적지로 추가
- S3, DynamoDB에 사용
- 무료 제공

**Interface VPC Endpoint**
- ENI(네트워크 인터페이스)로 연결
- 대부분의 AWS 서비스에 사용
- PrivateLink 기반
- 시간당 $0.01 비용

### PrivateLink
서비스 제공자 VPC의 NLB를 고객 VPC의 인터페이스 엔드포인트로 노출하여 사설 통신을 가능하게 하는 서비스입니다.

**주요 특징**
- VPC 간 사설 연결
- 인터넷 트래픽 없음
- 보안성 향상
- 네트워크 성능 최적화

**실무 활용**
- S3 프라이빗 액세스
- ECR 프라이빗 액세스
- RDS 프라이빗 액세스
- 서드파티 서비스 연동

---

## 참조

- [AWS Route 53 공식 문서](https://docs.aws.amazon.com/route53/)
- [DNS 기본 개념 및 동작 원리](https://www.cloudflare.com/learning/dns/what-is-dns/)
- [AWS Well-Architected Framework - DNS](https://aws.amazon.com/architecture/well-architected/)
- [Route 53 모범 사례 가이드](https://aws.amazon.com/route53/faqs/)
- [DNS 보안 모범 사례](https://www.ietf.org/rfc/rfc4033.txt)
- [VPC Endpoint 및 PrivateLink 가이드](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints.html)