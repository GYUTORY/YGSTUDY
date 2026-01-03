---
title: ALB vs API Gateway — AWS HTTP 트래픽 처리 비교
tags: [aws, alb, apigateway, networking, loadbalancer, microservices, serverless]
updated: 2026-01-03
---

# ALB vs API Gateway — 어떤 경우에 무엇을 쓸까?

AWS에서 HTTP 기반 요청을 처리할 때 가장 많이 쓰이는 두 가지 서비스:

- **Application Load Balancer (ALB)**
- **Amazon API Gateway**

비슷해 보이지만, 목적과 기능이 분명하게 다르다.

---

## 기본 개념

| 항목 | ALB | API Gateway |
|------|-----|-------------|
| 타입 | L7 애플리케이션 로드밸런서 | 완전관리형 API 관리 서비스 |
| 계층 | OSI 7계층 (HTTP/HTTPS) | HTTP API 게이트웨이 (REST/HTTP/WebSocket) |
| 대상 | EC2, ECS, Lambda | Lambda, HTTP 엔드포인트, AWS 서비스 |
| 주 용도 | 마이크로서비스 로드밸런싱 | 서버리스 API, 외부 개발자 대상 API |

---

## 공통 기능

| 기능 | 지원 여부 |
|------|-----------|
| 인증(TLS/SSL) | ✅ 둘 다 지원 |
| 경로 기반 라우팅 | ✅ 둘 다 지원 |
| CORS 설정 | ✅ 둘 다 지원 (API Gateway는 더 세밀하게 설정 가능) |
| 커스텀 도메인 | ✅ 둘 다 가능 |
| WAF 연동 | ✅ 가능 |
| IAM 인증 | ❌ ALB 불가 / ✅ API Gateway 가능 |
| Rate Limit (요청 제한) | ❌ / ✅ 가능 (API Gateway의 Throttling 기능) |

---

## 사용 아키텍처

### ALB 구조

```
사용자 ──▶ ALB ──▶ Target Group (EC2, ECS, Lambda)
```

- ALB는 주로 **사내 API, 웹 서비스, MSA 내부 통신**에 사용
- ALB는 직접적인 인증, 요금제, 요청 제한 등의 기능이 없음

### API Gateway 구조

```
사용자 ──▶ API Gateway ──▶ Lambda / HTTP 엔드포인트 / AWS 서비스
```

- **외부 API 노출**, **서버리스 환경**, **모바일/클라이언트 API**에 적합
- 요청 인증, 요금제, 캐싱 등 **API 관리 기능** 탑재

---

## 주요 차이점

| 항목 | ALB | API Gateway |
|------|-----|-------------|
| 사용 환경 | EC2, ECS 기반 마이크로서비스 | Lambda 기반 서버리스 or HTTP API |
| 요금 기준 | LCU(Load Capacity Unit) 기반 | API 요청 수 기반 (요청당 과금) |
| 인증/인가 | ACM 기반 TLS 인증 | IAM, Cognito, OAuth2 지원 |
| 요청 제한 | ❌ 불가 | ✅ 요청 제한/쿼터 설정 가능 |
| 캐싱 기능 | ❌ 없음 | ✅ 응답 캐싱 지원 |
| Swagger / OpenAPI 연동 | ❌ | ✅ 가능 |
| 개발자 포털 기능 | ❌ | ✅ 가능 (서드파티 연동) |

---

## 비용 비교

| 항목 | ALB | API Gateway |
|------|-----|-------------|
| 과금 기준 | 처리량(LCU), 시간당 | 요청 수 + 데이터 전송 |
| 무료 혜택 | 없음 | 월 100만 건 무료 (HTTP API 기준) |
| 캐시 | ❌ | ✅ 응답 캐싱 별도 과금 |
| 트래픽 처리 비용 | GB당 별도 과금 | GB당 별도 과금 (외부 호출 기준) |

---

## 어떤 경우에 어떤 걸 쓰는가?

| 상황 | 추천 |
|------|------|
| EC2/ECS 기반 MSA의 HTTP 요청 라우팅 | ✅ ALB |
| 서버리스 백엔드(Lambda)로 REST API 제공 | ✅ API Gateway |
| 외부 개발자용 API 제공 | ✅ API Gateway |
| 내부 마이크로서비스 간 요청 | ✅ ALB |
| 모바일 앱과 연동되는 API | ✅ API Gateway |
| 인증/인가, 요청 제한이 필요한 경우 | ✅ API Gateway |
| 고속, 대량 HTTP 라우팅 | ✅ ALB |

---

## 실무 팁

- **ALB는 고성능 웹 트래픽 처리**에 적합하고, **API Gateway는 보안/요금제/인증**이 중요한 **서버리스 API**에 적합하다.
- **둘을 함께 사용하는 하이브리드 아키텍처도 가능**:
    - 외부 요청 → API Gateway → 내부 ALB → 서비스

---

## 보안 및 인증 비교

| 기능 | ALB | API Gateway |
|------|-----|-------------|
| SSL/TLS | ✅ | ✅ |
| WAF 통합 | ✅ | ✅ |
| IAM 인증 | ❌ | ✅ |
| API 키 | ❌ | ✅ |
| JWT 인증 | ❌ | ✅ (Cognito 연동) |
| Throttling / Rate Limiting | ❌ | ✅ |

---

## 예시 아키텍처

### MSA 내부 통신 (ALB 기반)

```
Client
  ↓
ALB
  ├── /user → user-service
  ├── /order → order-service
  └── /chat → chat-service
```

### 외부 API 서비스 (API Gateway 기반)

```
Web / Mobile App
     ↓
API Gateway
     ↓
Lambda / Backend
```

---

## 참고 자료

- [API Gateway 공식 문서](https://docs.aws.amazon.com/apigateway/)
- [ALB 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [AWS API Gateway vs ALB 공식 비교](https://aws.amazon.com/ko/compare/api-gateway-vs-application-load-balancer/)