# AWS 로드 밸런서 비교: ALB vs NLB vs ELB 🌐

## 📋 목차
- [1. AWS 로드 밸런서 개요](#1-aws-로드-밸런서-개요)
- [2. ALB (Application Load Balancer)](#2-alb-application-load-balancer)
- [3. NLB (Network Load Balancer)](#3-nlb-network-load-balancer)
- [4. ELB (Elastic Load Balancer)](#4-elb-elastic-load-balancer)
- [5. 상세 비교표](#5-상세-비교표)
- [6. 선택 가이드](#6-선택-가이드)
- [7. 실제 사용 사례](#7-실제-사용-사례)

---

## 1. AWS 로드 밸런서 개요 🤔

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

## 2. ALB (Application Load Balancer) 🔵

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

## 4. ELB (Elastic Load Balancer) 🟡

### 4.1 기본 개념
**Elastic Load Balancer (ELB)**는 AWS의 **레거시 로드 밸런서**입니다. 이전에는 **Classic Load Balancer (CLB)**라고 불렸으며, AWS의 첫 번째 로드 밸런서 서비스입니다. 현재는 새로운 프로젝트에서는 권장되지 않습니다.

### 4.2 주요 특징 ✨

#### 4.2.1 레거시 지원
```plaintext
✅ EC2-Classic 네트워크 지원
✅ 레거시 애플리케이션 호환성
✅ 단순한 구성
✅ 비용 효율적
```

#### 4.2.2 제한된 기능
```plaintext
⚠️ 제한된 라우팅 기능
⚠️ 컨테이너 지원 부족
⚠️ 고급 보안 기능 부족
⚠️ 성능 제한
```

#### 4.2.3 지원 프로토콜
```plaintext
✅ TCP
✅ SSL/TLS
✅ HTTP/HTTPS
```

### 4.3 ELB 사용 시나리오 🎯
```plaintext
🔧 레거시 시스템
- 기존 EC2-Classic 환경
- 단순한 로드 밸런싱 필요
- 마이그레이션 중인 시스템

💰 비용 최적화
- 최소한의 기능만 필요
- 비용이 중요한 프로젝트
- 단순한 웹 서버 클러스터
```

---

## 5. 상세 비교표 📊

### 5.1 핵심 기능 비교

| 구분 | **ALB** (Application Load Balancer) | **NLB** (Network Load Balancer) | **ELB** (Elastic Load Balancer) |
|------|-------------------------------------|----------------------------------|----------------------------------|
| **동작 계층** | 7계층 (Application Layer) | 4계층 (Transport Layer) | 4계층 & 7계층 |
| **지원 프로토콜** | HTTP/HTTPS | TCP/UDP/TLS | TCP/SSL/TLS/HTTP/HTTPS |
| **IP 주소** | 동적 IP (변경 가능) | 고정 IP (Elastic IP 지원) | 동적 IP |
| **지연시간** | 낮음 (~10ms) | 초저 (~1ms) | 중간 (~20ms) |
| **처리량** | 높음 (수만 RPS) | 초고 (수백만 RPS) | 중간 (수천 RPS) |
| **라우팅 기능** | 고급 (Path, Host, Header 기반) | 기본 (포트 기반) | 기본 |
| **컨테이너 지원** | 완벽 지원 (ECS/EKS) | 제한적 지원 | 미지원 |
| **EC2-Classic** | 미지원 | 미지원 | 지원 |
| **비용** | 중간 | 높음 | 낮음 |

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

## 6. 선택 가이드 🎯

### 6.1 ALB를 선택해야 하는 경우
```plaintext
✅ HTTP/HTTPS 웹 애플리케이션
✅ 마이크로서비스 아키텍처
✅ 컨테이너 기반 애플리케이션 (ECS/EKS)
✅ 복잡한 라우팅 규칙 필요
✅ AWS WAF 통합 필요
✅ HTTP/2 지원 필요
✅ WebSocket 지원 필요
```

### 6.2 NLB를 선택해야 하는 경우
```plaintext
✅ TCP/UDP 기반 애플리케이션
✅ 고정 IP 주소 필요
✅ 초고성능 및 초저지연시간 필요
✅ 게임 서버, 데이터베이스 연결
✅ 실시간 스트리밍 애플리케이션
✅ 금융 거래 시스템
✅ 수백만 요청 처리 필요
```

### 6.3 ELB를 선택해야 하는 경우
```plaintext
✅ EC2-Classic 네트워크 사용
✅ 레거시 애플리케이션
✅ 단순한 로드 밸런싱만 필요
✅ 비용이 중요한 프로젝트
⚠️ 새로운 프로젝트에서는 권장하지 않음
```

---

## 7. 실제 사용 사례 💼

### 7.1 ALB 사용 사례
```yaml
# 마이크로서비스 아키텍처
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
# 게임 서버 클러스터
NLB 구성:
  - 프로토콜: TCP
  - 포트: 7777
  - 타겟: 게임 서버 인스턴스들
  - 고정 IP: 203.0.113.10
  
# 데이터베이스 클러스터
NLB 구성:
  - 프로토콜: TCP
  - 포트: 3306
  - 타겟: MySQL 클러스터
  - 고정 IP: 203.0.113.20
```

### 7.3 ELB 사용 사례
```yaml
# 레거시 웹 애플리케이션
ELB 구성:
  - 프로토콜: HTTP
  - 포트: 80
  - 타겟: 레거시 웹 서버들
  - EC2-Classic 네트워크
```

---

## 🎯 결론

**ALB**는 HTTP/HTTPS 웹 애플리케이션과 마이크로서비스에 최적화되어 있으며, **NLB**는 TCP/UDP 기반 고성능 애플리케이션에 적합합니다. **ELB**는 레거시 시스템을 위한 호환성 서비스입니다.

프로젝트의 요구사항에 따라 적절한 로드 밸런서를 선택하는 것이 중요합니다:
- **웹 애플리케이션** → ALB
- **게임/데이터베이스/실시간** → NLB  
- **레거시 시스템** → ELB

---

## 📚 참고 자료
- [AWS Elastic Load Balancing 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/)
- [AWS 로드 밸런서 비교 가이드](https://aws.amazon.com/elasticloadbalancing/features/)
- [AWS 비용 계산기](https://calculator.aws/)
