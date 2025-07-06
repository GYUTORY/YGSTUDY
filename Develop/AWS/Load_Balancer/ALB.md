# AWS Application Load Balancer (ALB)

> 📚 **이 가이드를 읽기 전에 알아야 할 기본 개념**
> - **로드 밸런서**: 서버에 들어오는 트래픽을 여러 서버에 분산시켜 부하를 줄이는 장치
> - **HTTP/HTTPS**: 웹에서 사용하는 통신 규약 (HTTP는 일반 텍스트, HTTPS는 암호화된 통신)
> - **마이크로서비스**: 하나의 큰 애플리케이션을 작은 서비스들로 나누어 개발하는 방식

---

## 📋 목차
1. [ALB란 무엇인가?](#1-alb란-무엇인가)
2. [AWS 로드 밸런서 비교](#2-aws-로드-밸런서-비교)
3. [ALB의 주요 특징](#3-alb의-주요-특징)
4. [ALB 사용 사례](#4-alb-사용-사례)
5. [ALB 구성 요소](#5-alb-구성-요소)
6. [실제 구성 예시](#6-실제-구성-예시)
7. [ALB 모범 사례](#7-alb-모범-사례)
8. [비용 최적화](#8-비용-최적화)
9. [문제 해결 가이드](#9-문제-해결-가이드)

---

## 1. ALB란 무엇인가? 🤔

### 1.1 기본 개념
**Application Load Balancer(ALB)**는 AWS에서 제공하는 **7계층 로드 밸런서**입니다. 

> 💡 **7계층이란?**
> - OSI 7계층 모델에서 **Application Layer**를 의미
> - HTTP, HTTPS 같은 웹 프로토콜을 이해하고 처리할 수 있음
> - URL 경로, 헤더, 쿠키 등을 분석하여 지능적으로 트래픽을 분산

### 1.2 ALB가 필요한 이유
```
❌ ALB 없이: 사용자 → 서버 1개 (과부하, 다운타임 위험)
✅ ALB 사용: 사용자 → ALB → 여러 서버 (부하 분산, 고가용성)
```

### 1.3 ALB의 핵심 역할
- **트래픽 분산**: 들어오는 요청을 여러 서버에 균등하게 분배
- **헬스 체크**: 서버가 정상 작동하는지 주기적으로 확인
- **SSL 종료**: HTTPS 암호화/복호화 처리
- **고급 라우팅**: URL 경로나 헤더에 따라 다른 서버로 요청 전달

---

## 2. AWS 로드 밸런서 비교 📊

### 2.1 4가지 로드 밸런서 종류

| 기능 | ALB | NLB | CLB | GWLB |
|------|-----|-----|-----|------|
| **계층** | 7계층 | 4계층 | 4/7계층 | 3계층 |
| **프로토콜** | HTTP/HTTPS | TCP/UDP/TLS | TCP/SSL/TLS/HTTP/HTTPS | IP 패킷 |
| **고정 IP** | ❌ | ✅ | ❌ | ✅ |
| **타겟 타입** | EC2, IP, Lambda, 컨테이너 | EC2, IP, ALB | EC2 | EC2, IP |
| **SSL 종료** | ✅ | ❌ | ✅ | ❌ |
| **WAF 통합** | ✅ | ❌ | ❌ | ❌ |
| **비용** | 중간 | 낮음 | 높음 | 중간 |

### 2.2 언제 어떤 로드 밸런서를 사용할까?

#### 🎯 ALB 사용 시기
- **웹 애플리케이션** (HTTP/HTTPS)
- **마이크로서비스** 아키텍처
- **컨테이너** 기반 애플리케이션
- **고급 라우팅** 기능이 필요할 때

#### 🎯 NLB 사용 시기
- **TCP/UDP** 트래픽
- **고정 IP** 주소가 필요할 때
- **게임 서버**나 **실시간 통신** 애플리케이션

#### 🎯 CLB 사용 시기
- **레거시 애플리케이션** (점진적으로 ALB로 마이그레이션 권장)
- **EC2-Classic** 환경

#### 🎯 GWLB 사용 시기
- **네트워크 보안** 장비 (방화벽, IDS/IPS)
- **트랜지트 게이트웨이** 패턴

> 💡 **용어 설명**
> - **SSL 종료**: HTTPS 요청을 받아서 복호화한 후 HTTP로 백엔드 서버에 전달
> - **WAF**: Web Application Firewall, 웹 애플리케이션 보안 방화벽
> - **고정 IP**: 항상 같은 IP 주소를 유지하는 것

---

## 3. ALB의 주요 특징 ⭐

### 3.1 고급 라우팅 기능

#### Path-based 라우팅
```
사용자 요청: https://example.com/api/users
ALB 라우팅: /api/* → API 서버 그룹으로 전달

사용자 요청: https://example.com/admin
ALB 라우팅: /admin/* → 관리자 서버 그룹으로 전달
```

#### Host-based 라우팅
```
사용자 요청: https://api.example.com
ALB 라우팅: api.example.com → API 서버로 전달

사용자 요청: https://www.example.com
ALB 라우팅: www.example.com → 웹 서버로 전달
```

#### Query string 파라미터 기반 라우팅
```
사용자 요청: https://example.com/search?type=product
ALB 라우팅: type=product → 상품 검색 서버로 전달
```

### 3.2 컨테이너 지원
- **Amazon ECS/EKS**와 완벽한 통합
- **동적 포트 매핑**: 컨테이너가 어떤 포트를 사용하든 자동으로 감지
- **서비스 디스커버리**: 새로운 컨테이너가 시작되면 자동으로 등록

### 3.3 보안 기능 🔒
- **SSL/TLS 종료**: 인증서 관리와 암호화 처리
- **AWS WAF 통합**: 웹 공격 방어
- **AWS Certificate Manager(ACM)**: 무료 SSL 인증서 관리
- **AWS Shield**: DDoS 공격 방어

### 3.4 모니터링 및 로깅
- **CloudWatch 지표**: 실시간 성능 모니터링
- **액세스 로깅**: 모든 요청에 대한 상세 로그
- **요청 추적**: 개별 요청의 처리 과정 추적

---

## 4. ALB 사용 사례 🎯

### 4.1 마이크로서비스 아키텍처

#### 시나리오: 온라인 쇼핑몰
```
사용자 → ALB → [주문 서비스] [상품 서비스] [결제 서비스] [사용자 서비스]
```

**라우팅 규칙:**
- `/api/orders/*` → 주문 서비스
- `/api/products/*` → 상품 서비스
- `/api/payments/*` → 결제 서비스
- `/api/users/*` → 사용자 서비스

### 4.2 컨테이너 기반 애플리케이션

#### 시나리오: ECS 클러스터
```
사용자 → ALB → ECS 클러스터 → [컨테이너 1] [컨테이너 2] [컨테이너 3]
```

**특징:**
- 컨테이너가 자동으로 시작/종료되어도 ALB가 자동 감지
- 동적 포트 매핑으로 포트 충돌 방지

### 4.3 다중 환경 구성

#### 시나리오: 개발/스테이징/프로덕션
```
개발자 → dev.example.com → 개발 환경 ALB → 개발 서버들
테스터 → staging.example.com → 스테이징 환경 ALB → 스테이징 서버들
사용자 → www.example.com → 프로덕션 환경 ALB → 프로덕션 서버들
```

---

## 5. ALB 구성 요소 🧩

### 5.1 리스너(Listener)
**리스너**는 ALB가 어떤 포트에서 어떤 프로토콜로 요청을 받을지 정의합니다.

#### 리스너 설정 예시
```yaml
리스너 1:
  프로토콜: HTTPS
  포트: 443
  인증서: example.com SSL 인증서

리스너 2:
  프로토콜: HTTP
  포트: 80
  리다이렉션: HTTPS로 자동 리다이렉션
```

### 5.2 대상 그룹(Target Group)
**대상 그룹**은 실제 요청을 처리할 서버들의 그룹입니다.

#### 대상 그룹 타입
- **EC2 인스턴스**: AWS 가상 서버
- **IP 주소**: 특정 IP 주소
- **Lambda 함수**: 서버리스 함수
- **컨테이너**: ECS/EKS 컨테이너

#### 헬스 체크 설정
```yaml
헬스 체크:
  프로토콜: HTTP
  경로: /health
  포트: 8080
  간격: 30초
  타임아웃: 5초
  성공 임계값: 2
  실패 임계값: 2
```

### 5.3 라우팅 규칙
**라우팅 규칙**은 어떤 조건에서 어떤 대상 그룹으로 요청을 보낼지 정의합니다.

#### 라우팅 규칙 예시
```yaml
규칙 1 (우선순위: 1):
  조건: Path is /api/*
  액션: Forward to api-target-group

규칙 2 (우선순위: 2):
  조건: Path is /admin/*
  액션: Forward to admin-target-group

규칙 3 (우선순위: 3):
  조건: Default
  액션: Forward to web-target-group
```

---

## 6. 실제 구성 예시 🛠️

### 6.1 기본 웹 애플리케이션 구성

#### 아키텍처 다이어그램
```
인터넷 → ALB → [웹 서버 1] [웹 서버 2] [웹 서버 3]
```

#### AWS 콘솔에서 설정하는 순서
1. **ALB 생성**
   - 이름: `my-web-alb`
   - 스키마: `internet-facing`
   - IP 주소 타입: `ipv4`

2. **보안 그룹 설정**
   ```yaml
   인바운드 규칙:
     - HTTP (80): 0.0.0.0/0
     - HTTPS (443): 0.0.0.0/0
   ```

3. **대상 그룹 생성**
   ```yaml
   이름: web-target-group
   타겟 타입: Instances
   프로토콜: HTTP
   포트: 80
   ```

4. **리스너 설정**
   ```yaml
   리스너 1:
     프로토콜: HTTP
     포트: 80
     기본 액션: Forward to web-target-group
   ```

### 6.2 마이크로서비스 구성

#### 아키텍처 다이어그램
```
인터넷 → ALB → [API 서버] [웹 서버] [관리자 서버]
```

#### 라우팅 규칙 설정
```yaml
규칙 1:
  조건: Path pattern is /api/*
  액션: Forward to api-target-group

규칙 2:
  조건: Path pattern is /admin/*
  액션: Forward to admin-target-group

규칙 3:
  조건: Default
  액션: Forward to web-target-group
```

---

## 7. ALB 모범 사례 🏆

### 7.1 보안 🔒

#### HTTPS 강제 적용
```yaml
리스너 1 (HTTP):
  포트: 80
  액션: Redirect to HTTPS

리스너 2 (HTTPS):
  포트: 443
  액션: Forward to target group
```

#### 보안 그룹 최적화
```yaml
ALB 보안 그룹:
  인바운드:
    - HTTP (80): 0.0.0.0/0
    - HTTPS (443): 0.0.0.0/0
  아웃바운드:
    - HTTP (80): target-group-sg
    - HTTPS (443): target-group-sg

타겟 그룹 보안 그룹:
  인바운드:
    - HTTP (80): ALB-sg
    - HTTPS (443): ALB-sg
```

#### WAF 규칙 적용
```yaml
WAF 규칙:
  - SQL Injection 방지
  - Cross-site Scripting (XSS) 방지
  - Rate Limiting (초당 2000 요청 제한)
  - Geographic restrictions (특정 국가만 허용)
```

### 7.2 고가용성

#### 다중 AZ 구성
```yaml
가용 영역:
  - us-east-1a
  - us-east-1b
  - us-east-1c

각 AZ에 최소 2개 이상의 서브넷 구성
```

#### 자동 스케일링 설정
```yaml
Auto Scaling Group:
  최소 용량: 2
  최대 용량: 10
  목표 용량: 4
  
스케일링 정책:
  - CPU 사용률 > 70% → 인스턴스 추가
  - CPU 사용률 < 30% → 인스턴스 제거
```

#### 헬스 체크 최적화
```yaml
헬스 체크:
  경로: /health
  간격: 30초
  타임아웃: 5초
  성공 임계값: 2
  실패 임계값: 3
  정상 임계값: 2
  비정상 임계값: 3
```

### 7.3 성능 최적화

#### 적절한 인스턴스 타입 선택
```yaml
웹 서버: t3.medium (2 vCPU, 4GB RAM)
API 서버: t3.large (2 vCPU, 8GB RAM)
데이터베이스: r5.large (2 vCPU, 16GB RAM)
```

#### 연결 드레이닝 설정
```yaml
연결 드레이닝:
  활성화: true
  타임아웃: 300초 (5분)
```

#### 캐싱 전략
```yaml
CloudFront 배포:
  - 정적 콘텐츠 (이미지, CSS, JS)
  - 지역별 엣지 로케이션
  - 캐시 TTL: 24시간
```

---

## 8. 비용 최적화 💰

### 8.1 요금 구조 이해

#### 기본 요금
```yaml
시간당 요금: $0.0225/시간 (약 $16.20/월)
데이터 처리량: $0.006/GB
LCU 요금: $0.008/LCU-시간
```

#### LCU (Load Balancer Capacity Units) 계산
```yaml
LCU 구성 요소:
  - 새 연결: 25개/초
  - 활성 연결: 3,000개/분
  - 처리된 바이트: 1GB/시간
  - 규칙 평가: 1,000개/초
```

### 8.2 비용 절감 전략

#### 적절한 인스턴스 크기 선택
```yaml
트래픽 예상:
  - 낮음 (< 1000 req/min): t3.micro
  - 중간 (1000-5000 req/min): t3.small
  - 높음 (> 5000 req/min): t3.medium
```

#### 자동 스케일링 활용
```yaml
스케일링 정책:
  - 비즈니스 시간: 최소 4개 인스턴스
  - 야간 시간: 최소 2개 인스턴스
  - 주말: 최소 1개 인스턴스
```

#### 리소스 태깅
```yaml
태그 전략:
  - Environment: production/staging/development
  - Project: my-web-app
  - Owner: team-name
  - CostCenter: department-code
```

---

## 9. 문제 해결 가이드 🔧

### 9.1 일반적인 문제들

#### 문제 1: ALB가 요청을 받지 못함
**증상**: ALB에 요청이 도달하지 않음
**원인 및 해결책**:
```yaml
확인 사항:
  1. 보안 그룹 설정
     - ALB 보안 그룹에 HTTP(80)/HTTPS(443) 인바운드 규칙 확인
  2. 서브넷 설정
     - ALB가 public 서브넷에 있는지 확인
  3. 라우팅 테이블
     - 인터넷 게이트웨이로의 라우팅 확인
```

#### 문제 2: 타겟 그룹 헬스 체크 실패
**증상**: 서버가 정상이지만 ALB에서 비정상으로 표시
**원인 및 해결책**:
```yaml
확인 사항:
  1. 헬스 체크 경로
     - /health 엔드포인트가 실제로 존재하는지 확인
  2. 포트 설정
     - 헬스 체크 포트와 애플리케이션 포트가 일치하는지 확인
  3. 보안 그룹
     - 타겟 그룹 보안 그룹에서 ALB로부터의 트래픽 허용 확인
```

#### 문제 3: SSL 인증서 오류
**증상**: HTTPS 접속 시 인증서 오류
**원인 및 해결책**:
```yaml
확인 사항:
  1. ACM 인증서
     - 도메인 이름이 인증서와 일치하는지 확인
  2. 리스너 설정
     - HTTPS 리스너에 올바른 인증서가 연결되어 있는지 확인
  3. 인증서 상태
     - 인증서가 유효한지 확인
```

### 9.2 모니터링 및 디버깅

#### CloudWatch 지표 확인
```yaml
중요 지표:
  - RequestCount: 요청 수
  - TargetResponseTime: 응답 시간
  - HTTPCode_ELB_4XX: 클라이언트 오류
  - HTTPCode_ELB_5XX: 서버 오류
  - HealthyHostCount: 정상 호스트 수
  - UnHealthyHostCount: 비정상 호스트 수
```

#### 액세스 로그 분석
```yaml
로그 활성화:
  - S3 버킷에 로그 저장
  - 로그 형식: JSON
  - 로그 보존 기간: 7일

분석 도구:
  - AWS Athena로 로그 쿼리
  - CloudWatch Logs Insights
  - ELK Stack (Elasticsearch, Logstash, Kibana)
```

---

## 📚 추가 학습 자료

### AWS 공식 문서
- [Application Load Balancer 사용자 가이드](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [ALB 모범 사례](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/best-practices.html)

### 실습 환경
- [AWS Free Tier](https://aws.amazon.com/free/)를 활용한 실습
- [AWS Workshop](https://workshops.aws/)에서 ALB 실습

### 관련 서비스
- **Route 53**: DNS 관리
- **CloudFront**: CDN 서비스
- **WAF**: 웹 애플리케이션 방화벽
- **Certificate Manager**: SSL 인증서 관리

---

## 🎯 핵심 요약

### ALB의 핵심 가치
1. **고가용성**: 다중 AZ 구성으로 99.99% 가용성 보장
2. **확장성**: 자동 스케일링으로 트래픽 변화에 대응
3. **보안성**: SSL 종료, WAF 통합으로 보안 강화
4. **유연성**: 고급 라우팅으로 복잡한 아키텍처 지원

