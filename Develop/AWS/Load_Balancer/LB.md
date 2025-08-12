---
title: AWS ALB vs NLB vs ELB
tags: [aws, loadbalancer, lb]
updated: 2025-08-10
---
# AWS 로드 밸런서 비교: ALB vs NLB vs ELB

## 배경
- [1. AWS 로드 밸런서 개요](#1-aws-로드-밸런서-개요)
- [2. ALB (Application Load Balancer)](#2-alb-application-load-balancer)
- [3. NLB (Network Load Balancer)](#3-nlb-network-load-balancer)
- [4. ELB (Elastic Load Balancer)](#4-elb-elastic-load-balancer)
- [5. 상세 비교표](#5-상세-비교표)
- [6. 선택 가이드](#6-선택-가이드)
- [7. 실제 사용 사례](#7-실제-사용-사례)

---

ALB 구성:
  - 서비스: 사용자 관리 API
    경로: /api/users/*
    타겟: user-service:8080
  
  - 서비스: 주문 관리 API
    경로: /api/orders/*
    타겟: order-service:8080
  
  - 서비스: 결제 API
    경로: /api/payments/*
    타겟: payment-service:8080
```

### 7.2 NLB 사용 사례
```yaml

NLB 구성:
  - 프로토콜: TCP
  - 포트: 7777
  - 타겟: 게임 서버 인스턴스들
  - 고정 IP: 203.0.113.10
  
NLB 구성:
  - 프로토콜: TCP
  - 포트: 3306
  - 타겟: MySQL 클러스터
  - 고정 IP: 203.0.113.20
```

### 7.3 ELB 사용 사례
```yaml

ELB 구성:
  - 프로토콜: HTTP
  - 포트: 80
  - 타겟: 레거시 웹 서버들
  - EC2-Classic 네트워크
```

---


**ALB**는 HTTP/HTTPS 웹 애플리케이션과 마이크로서비스에 최적화되어 있으며, **NLB**는 TCP/UDP 기반 고성능 애플리케이션에 적합합니다. **ELB**는 레거시 시스템을 위한 호환성 서비스입니다.

프로젝트의 요구사항에 따라 적절한 로드 밸런서를 선택하는 것이 중요합니다:
- **웹 애플리케이션** → ALB
- **게임/데이터베이스/실시간** → NLB  
- **보안 어플라이언스 체인** → GWLB
- **레거시 시스템** → ELB

---


### 스티키 세션
- ALB: Application Cookie(앱이 세팅) 또는 LB Cookie(`AWSALB`) 사용. 세션 일관성은 높아지나, 특정 타깃에 트래픽이 몰릴 수 있어 오토스케일/재배치와 균형 필요.
- NLB: 소스 IP 스티키(고정 연결) 성격. 프록시 너머의 SNAT 구조에 따라 분산이 왜곡될 수 있으니, 프런트단 프록시 수/세션 재사용 정책을 함께 본다.

### 헬스체크
- 경로: 최대한 가벼운 `/healthz`로 구성하고, 의존 외부 서비스 호출을 제거한다.
- 간격/임계치: 짧은 간격은 빠른 장애 감지지만, 오탐을 늘린다. 일반적으로 `interval 15s`, `healthy/unhealthy threshold 2-3`부터 시작해 조정.
- 타임아웃: 앱의 p95 응답시간보다 짧게 두면 오탐이 증가한다. 약간 여유를 둔다.
- NLB TCP 체크: L4에서는 애플리케이션 레벨을 모른다. 가능하면 HTTP 체크로 바꿔 상위 레이어 확인.

---

- ALB: Application Cookie(앱이 세팅) 또는 LB Cookie(`AWSALB`) 사용. 세션 일관성은 높아지나, 특정 타깃에 트래픽이 몰릴 수 있어 오토스케일/재배치와 균형 필요.
- NLB: 소스 IP 스티키(고정 연결) 성격. 프록시 너머의 SNAT 구조에 따라 분산이 왜곡될 수 있으니, 프런트단 프록시 수/세션 재사용 정책을 함께 본다.

- 경로: 최대한 가벼운 `/healthz`로 구성하고, 의존 외부 서비스 호출을 제거한다.
- 간격/임계치: 짧은 간격은 빠른 장애 감지지만, 오탐을 늘린다. 일반적으로 `interval 15s`, `healthy/unhealthy threshold 2-3`부터 시작해 조정.
- 타임아웃: 앱의 p95 응답시간보다 짧게 두면 오탐이 증가한다. 약간 여유를 둔다.
- NLB TCP 체크: L4에서는 애플리케이션 레벨을 모른다. 가능하면 HTTP 체크로 바꿔 상위 레이어 확인.

---

- [AWS Elastic Load Balancing 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/)
- [AWS 로드 밸런서 비교 가이드](https://aws.amazon.com/elasticloadbalancing/features/)
- [AWS 비용 계산기](https://calculator.aws/)







**ALB**는 HTTP/HTTPS 웹 애플리케이션과 마이크로서비스에 최적화되어 있으며, **NLB**는 TCP/UDP 기반 고성능 애플리케이션에 적합합니다. **ELB**는 레거시 시스템을 위한 호환성 서비스입니다.

프로젝트의 요구사항에 따라 적절한 로드 밸런서를 선택하는 것이 중요합니다:
- **웹 애플리케이션** → ALB
- **게임/데이터베이스/실시간** → NLB  
- **보안 어플라이언스 체인** → GWLB
- **레거시 시스템** → ELB

---


### 스티키 세션
- ALB: Application Cookie(앱이 세팅) 또는 LB Cookie(`AWSALB`) 사용. 세션 일관성은 높아지나, 특정 타깃에 트래픽이 몰릴 수 있어 오토스케일/재배치와 균형 필요.
- NLB: 소스 IP 스티키(고정 연결) 성격. 프록시 너머의 SNAT 구조에 따라 분산이 왜곡될 수 있으니, 프런트단 프록시 수/세션 재사용 정책을 함께 본다.

### 헬스체크
- 경로: 최대한 가벼운 `/healthz`로 구성하고, 의존 외부 서비스 호출을 제거한다.
- 간격/임계치: 짧은 간격은 빠른 장애 감지지만, 오탐을 늘린다. 일반적으로 `interval 15s`, `healthy/unhealthy threshold 2-3`부터 시작해 조정.
- 타임아웃: 앱의 p95 응답시간보다 짧게 두면 오탐이 증가한다. 약간 여유를 둔다.
- NLB TCP 체크: L4에서는 애플리케이션 레벨을 모른다. 가능하면 HTTP 체크로 바꿔 상위 레이어 확인.

---

- ALB: Application Cookie(앱이 세팅) 또는 LB Cookie(`AWSALB`) 사용. 세션 일관성은 높아지나, 특정 타깃에 트래픽이 몰릴 수 있어 오토스케일/재배치와 균형 필요.
- NLB: 소스 IP 스티키(고정 연결) 성격. 프록시 너머의 SNAT 구조에 따라 분산이 왜곡될 수 있으니, 프런트단 프록시 수/세션 재사용 정책을 함께 본다.

- 경로: 최대한 가벼운 `/healthz`로 구성하고, 의존 외부 서비스 호출을 제거한다.
- 간격/임계치: 짧은 간격은 빠른 장애 감지지만, 오탐을 늘린다. 일반적으로 `interval 15s`, `healthy/unhealthy threshold 2-3`부터 시작해 조정.
- 타임아웃: 앱의 p95 응답시간보다 짧게 두면 오탐이 증가한다. 약간 여유를 둔다.
- NLB TCP 체크: L4에서는 애플리케이션 레벨을 모른다. 가능하면 HTTP 체크로 바꿔 상위 레이어 확인.

---

- [AWS Elastic Load Balancing 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/)
- [AWS 로드 밸런서 비교 가이드](https://aws.amazon.com/elasticloadbalancing/features/)
- [AWS 비용 계산기](https://calculator.aws/)






- ALB: Application Cookie(앱이 세팅) 또는 LB Cookie(`AWSALB`) 사용. 세션 일관성은 높아지나, 특정 타깃에 트래픽이 몰릴 수 있어 오토스케일/재배치와 균형 필요.
- NLB: 소스 IP 스티키(고정 연결) 성격. 프록시 너머의 SNAT 구조에 따라 분산이 왜곡될 수 있으니, 프런트단 프록시 수/세션 재사용 정책을 함께 본다.

- 경로: 최대한 가벼운 `/healthz`로 구성하고, 의존 외부 서비스 호출을 제거한다.
- 간격/임계치: 짧은 간격은 빠른 장애 감지지만, 오탐을 늘린다. 일반적으로 `interval 15s`, `healthy/unhealthy threshold 2-3`부터 시작해 조정.
- 타임아웃: 앱의 p95 응답시간보다 짧게 두면 오탐이 증가한다. 약간 여유를 둔다.
- NLB TCP 체크: L4에서는 애플리케이션 레벨을 모른다. 가능하면 HTTP 체크로 바꿔 상위 레이어 확인.

---

- ALB: Application Cookie(앱이 세팅) 또는 LB Cookie(`AWSALB`) 사용. 세션 일관성은 높아지나, 특정 타깃에 트래픽이 몰릴 수 있어 오토스케일/재배치와 균형 필요.
- NLB: 소스 IP 스티키(고정 연결) 성격. 프록시 너머의 SNAT 구조에 따라 분산이 왜곡될 수 있으니, 프런트단 프록시 수/세션 재사용 정책을 함께 본다.

- 경로: 최대한 가벼운 `/healthz`로 구성하고, 의존 외부 서비스 호출을 제거한다.
- 간격/임계치: 짧은 간격은 빠른 장애 감지지만, 오탐을 늘린다. 일반적으로 `interval 15s`, `healthy/unhealthy threshold 2-3`부터 시작해 조정.
- 타임아웃: 앱의 p95 응답시간보다 짧게 두면 오탐이 증가한다. 약간 여유를 둔다.
- NLB TCP 체크: L4에서는 애플리케이션 레벨을 모른다. 가능하면 HTTP 체크로 바꿔 상위 레이어 확인.

---

- [AWS Elastic Load Balancing 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/)
- [AWS 로드 밸런서 비교 가이드](https://aws.amazon.com/elasticloadbalancing/features/)
- [AWS 비용 계산기](https://calculator.aws/)










## 1. AWS 로드 밸런서 개요

### 1.1 기본 개념
**AWS Elastic Load Balancing (ELB)**는 들어오는 애플리케이션 트래픽을 여러 타겟(EC2 인스턴스, 컨테이너, IP 주소 등)에 자동으로 분산시키는 서비스입니다.

### 1.2 로드 밸런서 종류
AWS는 현재 **3가지 유형**의 로드 밸런서를 제공합니다:

1. **ALB (Application Load Balancer)** - 7계층 로드 밸런서
2. **NLB (Network Load Balancer)** - 4계층 로드 밸런서  
3. **ELB (Elastic Load Balancer)** - 레거시 로드 밸런서 (구 CLB)

### 1.3 핵심 용어 설명
- **OSI 7계층**: 네트워크 통신을 7단계로 나누어 설명하는 모델
  - 4계층 (Transport Layer): TCP/UDP 프로토콜이 동작하는 계층
  - 7계층 (Application Layer): HTTP/HTTPS 프로토콜이 동작하는 계층
- **로드 밸런서**: 들어오는 트래픽을 여러 서버에 분산시켜 부하를 조절하는 장치
- **고정 IP**: 변경되지 않는 고유한 IP 주소
- **동적 IP**: 필요에 따라 변경될 수 있는 IP 주소

---

## 2. ALB (Application Load Balancer)

### 2.1 기본 개념
**Application Load Balancer**는 OSI 7계층의 **Application Layer (7계층)**에서 동작하는 로드 밸런서입니다. HTTP/HTTPS 트래픽을 처리하는데 최적화되어 있으며, 마이크로서비스 아키텍처와 컨테이너 기반 애플리케이션에 적합합니다.

### 2.2 주요 특징 ✨

#### 2.2.1 고급 라우팅 기능
```plaintext
✅ Path-based 라우팅: URL 경로 기반으로 트래픽 분배
✅ Host-based 라우팅: 도메인 이름 기반 라우팅
✅ Query string 파라미터 기반 라우팅
✅ HTTP 헤더 기반 라우팅
✅ HTTP 메서드 기반 라우팅
```

#### 2.2.2 컨테이너 지원
```plaintext
✅ Amazon ECS와 완벽 통합
✅ Amazon EKS 지원
✅ 동적 포트 매핑
✅ 서비스 디스커버리 지원
✅ 마이크로서비스 아키텍처 최적화
```

#### 2.2.3 보안 기능 🔒
```plaintext
✅ AWS WAF 통합
✅ SSL/TLS 종료
✅ AWS Certificate Manager(ACM) 통합
✅ HTTP/2 지원
✅ WebSocket 지원
```

#### 2.2.4 성능 및 모니터링
```plaintext
✅ 최대 100,000 RPS(초당 요청 수) 처리
✅ 자동 스케일링
✅ 다중 가용영역 지원
✅ CloudWatch 지표
✅ 액세스 로그
```

### 2.3 ALB 사용 시나리오 🎯
```plaintext
🌐 웹 애플리케이션
- HTTP/HTTPS 트래픽 처리
- 복잡한 라우팅 규칙 필요
- 마이크로서비스 아키텍처

📱 API 서버
- RESTful API 처리
- 다양한 엔드포인트 라우팅
- 버전별 API 관리

🐳 컨테이너 기반 애플리케이션
- Docker 컨테이너 지원
- ECS/EKS 통합
- 동적 포트 매핑
```

---

## 3. NLB (Network Load Balancer) 🟢

### 3.1 기본 개념
**Network Load Balancer**는 OSI 7계층의 **Transport Layer (4계층)**에서 동작하는 로드 밸런서입니다. TCP, UDP, TLS 프로토콜을 지원하며, **초고성능**과 **초저지연시간**을 제공하는 것이 특징입니다.

### 3.2 주요 특징 ✨

#### 3.2.1 고정 IP 주소 지원
```plaintext
✅ 고정 IP 주소 제공
✅ Elastic IP 할당 가능
✅ 클라이언트가 항상 동일한 IP로 접근 가능
✅ 다중 가용영역에서 고정 IP
```

#### 3.2.2 초고성능 처리
```plaintext
✅ 초당 수백만 개 요청 처리
✅ 초저지연시간 (밀리초 단위)
✅ 자동 스케일링 지원
✅ 다중 가용영역 지원
```

#### 3.2.3 프로토콜 지원
| 프로토콜 | 설명 | 사용 사례 |
|---------|------|-----------|
| **TCP** | 연결 지향적 프로토콜 | 데이터베이스 연결, 게임 서버 |
| **UDP** | 비연결 지향적 프로토콜 | 실시간 스트리밍, VoIP |
| **TLS** | 보안 통신 프로토콜 | HTTPS, 보안 연결 |

#### 3.2.4 보안 기능 🔒
```plaintext
✅ SSL/TLS 종료 지원
✅ AWS Certificate Manager (ACM) 통합
✅ VPC 내부에서만 동작
✅ 보안 그룹으로 접근 제어
```

### 3.3 NLB 사용 시나리오 🎯
```plaintext
🎮 게임 서버
- TCP 프로토콜 사용
- 초저지연시간 필요
- 고정 IP 주소 필요
- 수만 명의 동시 접속자 처리

🗄️ 데이터베이스 연결
- TCP 프로토콜 사용
- 고정 IP 주소로 연결
- 높은 처리량 필요
- 안정적인 연결 유지

📺 실시간 스트리밍
- UDP 프로토콜 사용
- 대용량 데이터 전송
- 낮은 지연시간 필요
- 수백만 시청자 지원

💰 금융 거래 시스템
- TLS 프로토콜 사용
- 보안 연결 필요
- 고정 IP 주소 필요
- 초고성능 처리 필요
```

---

## 4. ELB (Elastic Load Balancer)

### 4.1 기본 개념
**Elastic Load Balancer (ELB)**는 AWS의 **레거시 로드 밸런서**입니다. 이전에는 **Classic Load Balancer (CLB)**라고 불렸으며, AWS의 첫 번째 로드 밸런서 서비스입니다. 현재는 새로운 프로젝트에서는 권장되지 않습니다.

### 4.2 주요 특징

#### 4.2.1 레거시 지원
- EC2-Classic 네트워크 지원
- 레거시 애플리케이션 호환
- 단순한 구성
- 비용 효율적

#### 4.2.2 제한된 기능
- 라우팅 기능이 제한적
- 컨테이너 지원 부족
- 고급 보안 기능 부족
- 성능 제한

#### 4.2.3 지원 프로토콜
- TCP
- SSL/TLS
- HTTP/HTTPS

### 4.3 ELB 사용 시나리오
- 레거시 시스템
  - 기존 EC2-Classic 환경
  - 단순한 로드 밸런싱 필요
  - 마이그레이션 중인 시스템

- 비용 최적화가 중요한 경우
  - 최소한의 기능만 필요
  - 단순한 웹 서버 클러스터

---

## 5. 상세 비교표

### 5.1 핵심 기능 비교

| 구분 | **ALB** | **NLB** | **GWLB** | **ELB(CLB)** |
|------|---------|---------|----------|---------------|
| 동작 계층 | L7 (HTTP/HTTPS) | L4 (TCP/UDP/TLS) | L3/4 (Geneve) | L4/L7(레거시) |
| 주요 용도 | 웹/API, 마이크로서비스 | 초저지연, 고정 IP, DB/게임 | 보안 장비 체인, 트래픽 미러링 | 레거시 호환 |
| 지원 프로토콜 | HTTP/HTTPS/WebSocket/HTTP2 | TCP/UDP/TLS | Geneve(6081) | TCP/SSL/HTTP |
| IP | 동적 | 고정/EIP | NLB 앞단 고정 | 동적 |
| 라우팅 | Path/Host/Header/메서드 | 포트/고정 연결 | 서비스 인서트(어플라이언스) | 단순 |
| 컨테이너 | 매우 적합(ECS/EKS) | 적합(NodePort/타깃=IP) | 별도(어플라이언스) | 미흡 |
| WAF | 지원 | 미지원 | 미지원 | 미지원 |
| 헬스체크 | HTTP/HTTPS | TCP/HTTP/HTTPS | TCP/HTTP | HTTP/HTTPS/TCP |
| 스티키 | Cookie 기반 | 소스 IP 기반 | 해당 없음 | 제한적 |
| 비용 | 중간 | 높음 | 중간~높음 | 낮음 |

### 5.2 성능 비교

| 성능 지표 | ALB | NLB | ELB |
|-----------|-----|-----|-----|
| **최대 처리량** | 100,000 RPS | 수백만 RPS | 수천 RPS |
| **지연시간** | ~10ms | ~1ms | ~20ms |
| **연결 유지** | 지원 | 지원 | 제한적 |
| **자동 스케일링** | 완벽 지원 | 완벽 지원 | 제한적 |

### 5.3 보안 기능 비교

| 보안 기능 | ALB | NLB | ELB |
|-----------|-----|-----|-----|
| **AWS WAF 통합** | ✅ | ❌ | ❌ |
| **SSL/TLS 종료** | ✅ | ✅ | ✅ |
| **ACM 통합** | ✅ | ✅ | 제한적 |
| **HTTP/2 지원** | ✅ | ❌ | ❌ |
| **WebSocket** | ✅ | ✅ | 제한적 |

---

## 6. 선택 가이드

### 6.1 ALB를 선택해야 하는 경우
- HTTP/HTTPS 웹 애플리케이션
- 마이크로서비스 아키텍처
- 컨테이너 기반 애플리케이션(ECS/EKS)
- 복잡한 라우팅 규칙 필요
- AWS WAF 통합 필요
- HTTP/2 지원 필요
- WebSocket 지원 필요

### 6.2 NLB를 선택해야 하는 경우
- TCP/UDP 기반 애플리케이션
- 고정 IP 주소 필요
- 초고성능 및 초저지연시간 필요
- 게임 서버, 데이터베이스 연결
- 실시간 스트리밍 애플리케이션
- 금융 거래 시스템
- 수백만 요청 처리 필요

### 6.4 GWLB를 선택해야 하는 경우
- 네트워크/보안 어플라이언스를 통과시켜야 할 때(IPS/IDS/방화벽/패킷브로커)
- 트래픽 미러링/서비스 인서트 필요
- 경로 유연성과 확장성 필요(NLB와 조합)

### 6.3 ELB를 선택해야 하는 경우
- EC2-Classic 네트워크 사용
- 레거시 애플리케이션
- 단순한 로드 밸런싱만 필요
- 비용이 중요한 프로젝트
- 신규 프로젝트에는 일반적으로 권장하지 않음

---

## 7. 실제 사용 사례

### 7.1 ALB 사용 사례
```yaml

