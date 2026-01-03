---
title: AWS Application Load Balancer (ALB)
tags: [aws, alb, loadbalancer, networking, http, microservices]
updated: 2026-01-03
---

# AWS Application Load Balancer (ALB)

## 개요

Application Load Balancer(ALB)는 AWS에서 제공하는 L7 계층(애플리케이션 계층)의 로드 밸런서다.  
HTTP 및 HTTPS 트래픽을 기반으로 다양한 조건에 따라 백엔드로 트래픽을 분산할 수 있다.

---

## 주요 특징

| 항목 | 설명 |
|------|------|
| 프로토콜 | HTTP, HTTPS (TLS 종료 지원) |
| 지원 대상 | EC2, ECS, Lambda, IP 주소 |
| 로드 밸런싱 기준 | URL 경로, Host 헤더, HTTP 헤더, 메서드, 쿼리 파라미터 등 |
| 통합 | Auto Scaling, CloudWatch, ACM, WAF 등 |
| 인증서 지원 | AWS ACM과 연동하여 TLS 인증서 자동 관리 가능 |

---

## 사용 사례

- 마이크로서비스 경로 기반 분기 (`/users`, `/orders`, `/admin`)
- ECS, Lambda 등 다양한 서비스로 트래픽 분산
- HTTPS 인증서 중앙 관리 및 암호화 통신
- A/B 테스트 또는 카나리 배포
- 모바일 또는 웹 트래픽 처리

---

## 아키텍처 구성 예시

```
Client
  ↓ HTTPS
ALB
 ├── /users/*     → EC2 Target Group
 ├── /orders/*    → ECS Target Group
 ├── /analytics/* → Lambda Target Group
```

---

## 핵심 구성 요소

### 1. Listener

클라이언트 요청을 수신하는 포트 및 프로토콜 지정

- 일반적으로 80(HTTP), 443(HTTPS)
- HTTPS 사용 시 ACM을 통한 인증서 연동
- 기본 액션 설정 가능 (리디렉션, 고정 응답 등)

### 2. Target Group

트래픽이 전달되는 대상(EC2, ECS, IP, Lambda 등)의 집합

- 라운드로빈 방식 또는 최소 미해결 요청 기준으로 분산
- 대상 등록 시 개별 헬스체크 수행

### 3. Routing Rule

라우팅 조건과 액션 지정

- 조건: Host 헤더, 경로, 메서드, 헤더, 쿼리스트링 등
- 액션: Forward(포워딩), Redirect(리디렉션), Fixed Response

---

## 주요 기능

### ✅ 경로 기반 라우팅

```
/api/users/*      → user-service
/api/orders/*     → order-service
/static/*         → CloudFront 또는 S3
```

### ✅ 호스트 기반 라우팅

```
api.example.com    → API 백엔드
admin.example.com  → 관리자 백엔드
```

### ✅ 고정 응답, 리디렉션

- 특정 조건에 대해 고정 응답 반환 가능
- HTTP → HTTPS 리디렉션 가능

### ✅ HTTPS TLS 종료

- ALB에서 HTTPS 인증서를 종료(TLS Termination)
- 백엔드에는 HTTP로 통신 (암호화 부담 분산)
- ACM을 통한 인증서 자동 갱신

### ✅ 헬스 체크

- 기본 `/` 또는 `/health` 경로
- 실패 시 트래픽 대상에서 제외
- 설정 항목: 간격, 타임아웃, 실패/성공 허용 횟수

---

## 고급 기능

### 1. Sticky Session (세션 고정)

- 쿠키 기반 세션 고정 가능
- 사용자 요청을 항상 동일한 인스턴스로 라우팅
- 세션 상태를 서버 간 공유하지 못할 경우 유용

### 2. 압축 (gzip)

- HTTP 응답을 gzip으로 압축
- 텍스트 기반 자원(CSS, JS, HTML 등)에 유리

### 3. HTTP/2 지원

- 멀티플렉싱, 헤더 압축 등 성능 향상
- 클라이언트가 HTTP/2 지원 시 자동 사용

### 4. WebSocket 지원

- 실시간 통신을 위한 WebSocket 지원 포함

---

## 보안 구성

### 1. ACM 인증서

- ACM에서 무료 인증서 발급
- 자동 갱신 가능
- SAN 인증서 지원 (여러 도메인)

### 2. WAF 연동

- ALB 앞단에 Web Application Firewall 적용 가능
- OWASP Top 10 대응 가능

### 3. 보안 그룹 구성 예시

- ALB SG: 0.0.0.0/0 → 80, 443 허용
- 백엔드 SG: ALB SG만 허용 (인바운드 제한)

---

## 모니터링 & 로깅

### CloudWatch 메트릭

- `RequestCount`: 전체 요청 수
- `TargetResponseTime`: 평균 응답 시간
- `HTTPCode_ELB_4XX_Count`, `5XX_Count`: 오류 수
- `UnHealthyHostCount`: 헬스체크 실패 수

### 액세스 로그

- S3에 저장
- 필드: 시간, IP, 요청, 응답코드, 지연 시간 등
- 보안 분석 및 트래픽 패턴 분석에 유용

### X-Ray 통합

- ALB → 백엔드까지 분산 추적 가능

---

## Auto Scaling 연동

- ALB 대상 그룹과 Auto Scaling Group 연결
- 요청 수 또는 CPU 사용률 기반으로 스케일 인/아웃
- Target Tracking 또는 Step Scaling 사용

---

## 실무 팁

- ALB는 모든 요청을 **요청 단위로 분산** (세션 유지 필요 시 sticky session 사용)
- **헬스체크 실패** → 즉시 대상 제외, **Auto Scaling과 반드시 연계**
- 기본 라우팅 외에 **정적 콘텐츠는 CloudFront 사용** 권장
- **ACM 인증서** 사용으로 HTTPS 적용이 매우 간편
- ALB는 일반적으로 **비용 효율이 높고 유연성 뛰어남**

---

## ALB vs NLB vs API Gateway 비교

| 항목 | ALB | NLB | API Gateway |
|------|-----|-----|--------------|
| 계층 | L7 | L4 | L7 (API) |
| 대상 | EC2, ECS, Lambda | EC2, IP | Lambda, HTTP |
| 사용 목적 | 웹, MSA 라우팅 | 실시간 통신, 게임 | 외부 API, 서버리스 |
| 인증서 | TLS 종료 | TLS 패스스루 | IAM, JWT, API Key |
| 기능 | 고급 라우팅 | 고성능, 저지연 | 인증, 레이트 리밋, CORS |

---

## 참고 링크

- [ALB 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [ALB 가격 안내](https://aws.amazon.com/elasticloadbalancing/pricing/)
- [AWS Load Balancer 선택 가이드](https://aws.amazon.com/elasticloadbalancing/features/)