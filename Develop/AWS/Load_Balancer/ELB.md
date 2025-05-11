# AWS Application Load Balancer (ALB) 🚀

## 개요
Application Load Balancer(ALB)는 AWS에서 제공하는 7계층(Application Layer) 로드 밸런서로, HTTP와 HTTPS 트래픽을 처리하는 최신 세대의 로드 밸런서입니다. 

## 주요 특징 ✨

### 1. 고급 라우팅 기능
- **Path-based 라우팅**: URL 경로 기반으로 트래픽 분배
- **Host-based 라우팅**: 도메인 이름 기반 라우팅
- **Query string 파라미터 기반 라우팅**
- **HTTP 헤더 기반 라우팅**

### 2. 컨테이너 지원
- Amazon ECS와 완벽한 통합
- 동적 포트 매핑 지원
- 컨테이너 기반 애플리케이션에 최적화

### 3. 보안 기능 🔒
- SSL/TLS 종료
- AWS WAF 통합
- AWS Certificate Manager(ACM) 통합
- 보안 그룹을 통한 접근 제어

### 4. 고가용성
- 다중 가용영역(AZ) 배포
- 자동 장애 조치
- 상태 확인(Health Check) 기능

## 사용 사례 💡

1. **마이크로서비스 아키텍처**
   - 서비스 간 트래픽 분배
   - 서비스 디스커버리

2. **웹 애플리케이션**
   - HTTP/HTTPS 트래픽 처리
   - SSL/TLS 종료

3. **컨테이너 기반 애플리케이션**
   - ECS/EKS 통합
   - 동적 포트 매핑

## 비용 구조 💰

- 시간당 요금
- 처리된 데이터 양에 따른 요금
- LCU(Load Balancer Capacity Units) 기반 과금

## 모니터링 및 로깅 📊

- CloudWatch 통합
- 액세스 로그 활성화 가능
- 실시간 메트릭 모니터링

## 모범 사례 ⭐

1. **고가용성 구성**
   - 최소 2개 이상의 가용영역 사용
   - 크로스 존 로드 밸런싱 활성화

2. **보안 강화**
   - HTTPS 리스너 사용
   - 보안 그룹 적절히 구성
   - WAF 규칙 적용

3. **성능 최적화**
   - 적절한 타겟 그룹 구성
   - 효율적인 상태 확인 설정
   - 캐싱 전략 수립

## 제한사항 ⚠️

- 리전당 최대 ALB 수 제한
- 리스너당 규칙 수 제한
- 타겟 그룹당 타겟 수 제한

## 결론 🎯

AWS ALB는 현대적인 웹 애플리케이션과 마이크로서비스 아키텍처에 최적화된 로드 밸런서입니다. 고급 라우팅 기능, 강력한 보안 기능, 그리고 컨테이너 지원을 통해 다양한 사용 사례에 대응할 수 있습니다.

## AWS 로드 밸런서 비교 🔄

### 1. Application Load Balancer (ALB) vs Network Load Balancer (NLB)

| 기능 | ALB | NLB |
|------|-----|-----|
| 계층 | 7계층 (Application) | 4계층 (Transport) |
| 프로토콜 | HTTP, HTTPS, gRPC | TCP, UDP, TLS |
| 고정 IP | ❌ | ✅ |
| 타겟 유형 | EC2, ECS, Lambda | EC2, IP 주소 |
| 비용 | 상대적으로 저렴 | 상대적으로 비쌈 |
| 지연 시간 | 상대적으로 높음 | 매우 낮음 |
| 사용 사례 | 웹 애플리케이션, 마이크로서비스 | TCP/UDP 기반 애플리케이션, 게임 서버 |

### 2. Application Load Balancer (ALB) vs Classic Load Balancer (CLB)

| 기능 | ALB | CLB |
|------|-----|-----|
| 세대 | 2세대 | 1세대 |
| 프로토콜 | HTTP, HTTPS, gRPC | HTTP, HTTPS, TCP, SSL |
| 컨테이너 지원 | ✅ | ❌ |
| Lambda 통합 | ✅ | ❌ |
| 고급 라우팅 | ✅ | ❌ |
| WebSocket | ✅ | ✅ |
| 사용 사례 | 현대적 웹 앱, 마이크로서비스 | 레거시 애플리케이션 |

### 3. Application Load Balancer (ALB) vs Gateway Load Balancer (GWLB)

| 기능 | ALB | GWLB |
|------|-----|------|
| 주요 목적 | 애플리케이션 트래픽 분배 | 네트워크 가시성 및 보안 |
| 프로토콜 | HTTP, HTTPS, gRPC | IP 패킷 |
| 사용 사례 | 웹 서비스, API | 방화벽, IDS/IPS, DDoS 보호 |
| 통합 | 웹 서비스 | 네트워크 보안 장비 |

## 선택 가이드 📋

1. **ALB 선택 시나리오**
   - HTTP/HTTPS 기반 웹 애플리케이션
   - 마이크로서비스 아키텍처
   - 컨테이너 기반 애플리케이션
   - 고급 라우팅이 필요한 경우

2. **NLB 선택 시나리오**
   - TCP/UDP 기반 애플리케이션
   - 고정 IP 주소가 필요한 경우
   - 초저지연이 필요한 경우
   - 초고성능이 필요한 경우

3. **CLB 선택 시나리오**
   - EC2-Classic 네트워크 사용
   - 레거시 애플리케이션
   - 간단한 로드 밸런싱만 필요한 경우

4. **GWLB 선택 시나리오**
   - 네트워크 보안 장비 배포
   - 트래픽 검사 및 필터링
   - 중앙화된 보안 관리
