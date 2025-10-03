---
title: GSLB (Global Server Load Balancing)
tags: [network, 7-layer, gslb, dns, load-balancing]
updated: 2025-10-03
---

# GSLB (Global Server Load Balancing) 개요

GSLB(Global Server Load Balancing)는 전 세계적으로 분산된 서버들의 부하를 분산시키고 가용성을 높이는 고급 DNS 서비스입니다. 단순한 DNS 서비스와 달리, 서버의 상태, 지리적 위치, 네트워크 상태 등 다양한 요소를 고려하여 최적의 서버를 선택합니다.

## DNS의 한계점

DNS는 도메인 주소와 IP를 매핑하여 도메인으로 요청이 들어왔을 때 대상의 주소로 변환해주는 서비스입니다. 하나의 도메인 주소에 대해서 여러 개의 IP주소를 제공할 수 있어 가용성 구성과 로드 밸런싱 기능을 수행하기도 하지만, 근본적으로 다음과 같은 한계가 있습니다:

### 주요 한계점
1. **서버 상태 모니터링 불가**: 서버가 다운되었는지, 과부하 상태인지 알 수 없음
2. **단순한 라운드 로빈 방식**: 서버의 실제 부하나 성능을 고려하지 않음
3. **지리적 위치 고려 불가**: 사용자와 서버 간의 거리를 고려하지 않음
4. **실시간 대응 불가**: 서버 상태 변화에 실시간으로 대응할 수 없음

> **핵심 문제**: DNS의 로드 밸런싱은 IP 목록 중 하나를 반환할 뿐, 네트워크 지연, 성능, 트래픽 유입, 서비스 실패 등은 전혀 고려하지 않습니다.

---

## GSLB vs DNS 비교 분석

### 1. 재해복구 (Disaster Recovery)

#### DNS 방식
<div align="center">
    <img src="../../../etc/image/Network_image/DNS.png" alt="DNS 재해복구" width="60%">
</div>

**문제점:**
- 서버의 상태를 알 수 없어 실패한 서버로도 요청이 계속 전달됨
- 서버 장애 발생 시 자동 전환 메커니즘이 없어 서비스 중단 발생
- Health Check 기능이 없어 사용자들이 실패한 서버에 접속하게 됨

#### GSLB 방식
<div align="center">
    <img src="../../../etc/image/Network_image/GSLB.png" alt="GSLB 재해복구" width="60%">
</div>

**장점:**
- 서버의 상태를 실시간 모니터링하여 실패한 서버의 IP는 응답에서 제외
- Active-Active 또는 Active-Standby 구성으로 고가용성 보장
- 자동 장애 감지 및 복구 메커니즘으로 서비스 연속성 유지
- 지역별 장애 격리 및 대응 가능

---

### 2. 로드밸런싱 (Load Balancing)

#### DNS 방식
<div align="center">
    <img src="../../../etc/image/Network_image/DNS_LB.png" alt="DNS 로드밸런싱" width="60%">
</div>

**문제점:**
- 단순한 Round Robin 방식으로 로드밸런싱
- 서버의 실제 부하 상태를 고려하지 않아 특정 서버에 과부하 발생 가능
- 트래픽 패턴에 따른 동적 조정이 불가능
- 고트래픽 서비스에서는 정교한 로드 밸런싱이 필요하지만 DNS로는 한계

#### GSLB 방식
<div align="center">
    <img src="../../../etc/image/Network_image/GSLB_LB.png" alt="GSLB 로드밸런싱" width="60%">
</div>

**장점:**
- 서버의 로드(상태)를 실시간 모니터링하여 트래픽이 적은 서버의 IP 반환
- 다양한 로드밸런싱 알고리즘 지원:
  - **Least Connection**: 현재 연결 수가 가장 적은 서버 선택
  - **Weighted Round Robin**: 서버별 가중치를 부여한 라운드 로빈
  - **Response Time**: 응답 시간이 가장 빠른 서버 선택
  - **Geographic**: 지리적 위치 기반 서버 선택
- 실시간 부하 모니터링 및 동적 조정
- 트래픽 패턴 분석 및 예측 기반 부하 분산

---

### 3. 레이턴시 기반 (Latency-based)

#### DNS 방식
<div align="center">
    <img src="../../../etc/image/Network_image/DNS_LT.png" alt="DNS 레이턴시" width="60%">
</div>

**문제점:**
- Round Robin 방식을 사용하여 사용자가 멀리 떨어진 서버로 연결될 수 있음
- 네트워크 지연 시간을 고려하지 않아 사용자 경험 저하 가능성
- RTT(Round Trip Time) 측정 불가
- 패킷 손실률 모니터링 불가

#### GSLB 방식
<div align="center">
    <img src="../../../etc/image/Network_image/GSLB_LT.png" alt="GSLB 레이턴시" width="60%">
</div>

**장점:**
- 각 지역별로 서버에 대한 레이턴시(latency) 정보를 보유
- 사용자로부터 레이턴시가 가장 적은 서버의 IP 반환
- 네트워크 성능 모니터링:
  - **RTT 측정**: 실시간 지연 시간 모니터링
  - **패킷 손실률 모니터링**: 네트워크 품질 추적
  - **대역폭 사용량 추적**: 네트워크 리소스 모니터링
- BGP 라우팅 정보 활용
- Anycast 네트워크 구성 지원

---

### 4. 위치 기반 (Geographic-based)

#### DNS 방식
<div align="center">
    <img src="../../../etc/image/Network_image/DNS_GPS.png" alt="DNS 위치기반" width="60%">
</div>

**문제점:**
- Round Robin 방식을 사용하여 사용자의 지리적 위치를 고려하지 않음
- 지역별 최적화 불가능
- 데이터 주권 준수 어려움
- 지역별 콘텐츠 최적화 불가

#### GSLB 방식
<div align="center">
    <img src="../../../etc/image/Network_image/GSLB_GPS.png" alt="GSLB 위치기반" width="60%">
</div>

**장점:**
- 사용자의 지역정보를 기반으로 가까운 지역의 서버로 연결
- 위치 인식 기능:
  - **IP 기반 위치 파악**: 사용자 IP를 통한 지리적 위치 식별
  - **GeoIP 데이터베이스 활용**: 정확한 위치 정보 제공
  - **지역별 서버 매핑**: 지역별 최적 서버 매핑
- 지역별 최적화:
  - **데이터 주권 준수**: 각 지역의 데이터 보호 규정 준수
  - **지역별 콘텐츠 최적화**: 지역에 맞는 콘텐츠 제공
  - **지역별 트래픽 관리**: 지역별 트래픽 패턴 분석 및 최적화

---

## GSLB 구현 방식

### 1. DNS 기반 GSLB
- **동작 원리**: DNS 쿼리에 대한 응답으로 최적의 서버 IP 반환
- **캐시 관리**: TTL(Time To Live) 값을 통한 효율적인 캐시 관리
- **프로토콜 확장**: DNS 프로토콜 확장을 통한 추가 정보 전달
- **장점**: 기존 DNS 인프라 활용 가능, 구현이 상대적으로 간단

### 2. Anycast 기반 GSLB
- **동작 원리**: 동일한 IP 주소를 여러 위치에서 광고
- **라우팅**: BGP 라우팅을 통한 최적 경로 선택
- **부하 분산**: 네트워크 레벨에서의 자동 부하 분산
- **장점**: 네트워크 레벨에서 처리되어 성능이 우수

---

## GSLB 도입 시 고려사항

### 1. 비용 (Cost)
- **라이선스 비용**: GSLB 솔루션 라이선스 비용
- **인프라 비용**: 구축 및 유지보수 비용
- **운영 비용**: 모니터링 및 관리 비용
- **ROI 분석**: 비용 대비 효과 분석 필요

### 2. 복잡성 (Complexity)
- **설정 복잡성**: 설정 및 관리의 복잡성 증가
- **아키텍처 변경**: 네트워크 아키텍처 변경 필요
- **전문성 요구**: 운영팀의 전문성 요구
- **학습 곡선**: 새로운 기술에 대한 학습 필요

### 3. 성능 (Performance)
- **DNS 해석 시간**: DNS 해석 시간 증가 가능성
- **Health Check 오버헤드**: Health Check로 인한 성능 오버헤드
- **캐시 정책**: 캐시 정책 최적화 필요
- **모니터링**: 성능 모니터링 및 튜닝 필요

---

## 주요 GSLB 솔루션

### 1. F5 BIG-IP GTM
- **특징**: 엔터프라이즈급 GSLB 솔루션
- **장점**: 고성능, 고가용성, 다양한 기능 제공
- **용도**: 대규모 엔터프라이즈 환경

### 2. Citrix NetScaler
- **특징**: ADC(Application Delivery Controller) 통합 솔루션
- **장점**: 애플리케이션 레벨 최적화
- **용도**: 애플리케이션 중심 환경

### 3. AWS Route 53
- **특징**: 클라우드 네이티브 DNS 및 GSLB 서비스
- **장점**: AWS 생태계 통합, 관리형 서비스
- **용도**: AWS 기반 클라우드 환경

### 4. Cloudflare
- **특징**: CDN과 통합된 GSLB 서비스
- **장점**: 글로벌 네트워크, DDoS 보호
- **용도**: 웹 애플리케이션 최적화

### 5. Akamai
- **특징**: 글로벌 CDN 및 GSLB 서비스
- **장점**: 전 세계 최대 CDN 네트워크
- **용도**: 글로벌 콘텐츠 배포

---

## 참고 자료

1. [DNS와 GSLB의 차이점](https://coding-start.tistory.com/339)
2. [F5 GSLB 가이드](https://www.f5.com/services/resources/glossary/global-server-load-balancing)
3. [Nginx GSLB 설명](https://www.nginx.com/resources/glossary/global-server-load-balancing/)

--- 

