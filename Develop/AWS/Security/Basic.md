---
title: AWS 보안 서비스 통합 아키텍처
tags: [aws, security, waf, shield, guardduty, securityhub]
updated: 2025-09-23
---

# AWS 보안 서비스 통합 아키텍처

## 개요

AWS 보안 서비스들은 각각 독립적인 기능을 수행하면서도 서로 연동되어 종합적인 보안 방어 체계를 구축합니다. 이 문서에서는 AWS WAF, Shield, GuardDuty, Security Hub가 어떻게 협력하여 다층 보안을 구현하는지 살펴봅니다.

## 핵심 보안 서비스

### AWS WAF (Web Application Firewall)

**개념과 역할**
AWS WAF는 애플리케이션 계층(Layer 7)에서 작동하는 웹 방화벽으로, HTTP/HTTPS 트래픽을 실시간으로 분석하고 필터링합니다. 전통적인 네트워크 방화벽과 달리 애플리케이션의 비즈니스 로직을 이해하고 보호할 수 있습니다.

**주요 기능**
- **규칙 기반 필터링**: 요청의 다양한 속성(IP 주소, 헤더, 쿼리 파라미터, 요청 본문 등)을 기반으로 허용, 차단, 카운트 결정
- **매니지드 룰셋**: AWS와 보안 업체가 제공하는 사전 정의된 규칙 세트로 일반적인 공격 패턴 차단
- **사용자 정의 룰**: 특정 애플리케이션 요구사항에 맞는 맞춤형 보안 규칙 생성
- **레이트 리미팅**: 특정 IP나 사용자로부터의 과도한 요청을 자동으로 제한

**로그 및 모니터링**
WAF는 모든 요청에 대한 상세한 로그를 생성하며, 이를 CloudWatch Logs, S3, Kinesis Data Streams로 전송하여 보안 분석과 트렌드 파악이 가능합니다.

### AWS Shield

**개념과 역할**
AWS Shield는 DDoS(분산 서비스 거부) 공격으로부터 AWS 리소스를 보호하는 완화 서비스입니다. DDoS 공격은 정상적인 서비스 요청을 압도하여 서비스를 사용할 수 없게 만드는 공격 방식입니다.

**Shield Standard**
- 모든 AWS 고객에게 무료로 제공
- 자동으로 일반적인 DDoS 공격 탐지 및 완화
- 네트워크 계층(Layer 3, 4) 공격에 대한 기본 보호

**Shield Advanced**
- 고급 DDoS 보호 기능 제공
- 애플리케이션 계층(Layer 7) 공격까지 포함한 포괄적 보호
- 공격 중 발생하는 데이터 전송 비용 보호
- 24x7 DDoS Response Team(DRT) 지원
- WAF와 통합된 자동 완화 기능

### Amazon GuardDuty

**개념과 역할**
GuardDuty는 AWS 환경에서 발생하는 악의적인 활동과 비정상적인 동작을 탐지하는 위협 탐지 서비스입니다. 머신러닝과 위협 인텔리전스를 활용하여 지속적으로 보안 위협을 모니터링합니다.

**데이터 소스**
- **CloudTrail**: API 호출 로그 분석
- **VPC Flow Logs**: 네트워크 트래픽 패턴 분석
- **DNS Logs**: DNS 쿼리 패턴 분석
- **EKS 감사 로그**: Kubernetes 클러스터 활동 분석

**탐지 결과**
GuardDuty는 발견된 위협을 Finding이라는 형태로 보고하며, 각 Finding은 다음 정보를 포함합니다:
- **심각도**: CRITICAL, HIGH, MEDIUM, LOW
- **영향받는 리소스**: EC2 인스턴스, IAM 사용자 등
- **위협 유형**: 악성 IP 통신, 권한 상승 시도 등
- **상세 설명**: 탐지된 활동의 구체적인 내용

### AWS Security Hub

**개념과 역할**
Security Hub는 AWS 보안 서비스들로부터 수집된 보안 결과를 중앙에서 통합 관리하는 서비스입니다. 여러 보안 도구의 결과를 하나의 대시보드에서 확인하고, 상관관계를 분석하여 종합적인 보안 상황을 파악할 수 있습니다.

**통합 기능**
- **ASFF(Amazon Security Finding Format)**: 다양한 보안 서비스의 결과를 표준화된 형식으로 변환
- **상관관계 분석**: 여러 서비스에서 발견된 관련 보안 이벤트들을 연결하여 분석
- **자동 대응**: EventBridge와 연동하여 보안 이벤트 발생 시 자동으로 대응 조치 실행

## 보안 서비스 통합 워크플로우

### 1단계: 관찰 (Observation)
- **CloudTrail**: 모든 API 호출 기록
- **VPC Flow Logs**: 네트워크 트래픽 모니터링
- **WAF 로그**: 웹 애플리케이션 요청 분석

### 2단계: 탐지 (Detection)
- **GuardDuty**: 머신러닝 기반 이상 행위 탐지
- **WAF**: 규칙 기반 악성 요청 차단
- **Shield**: DDoS 공격 자동 탐지

### 3단계: 차단 (Blocking)
- **WAF**: 악성 요청 즉시 차단
- **Shield**: DDoS 트래픽 자동 완화
- **Security Groups**: 네트워크 레벨 접근 제어

### 4단계: 대응 (Response)
- **Security Hub**: 통합된 보안 이벤트 관리
- **EventBridge**: 자동 대응 워크플로우 실행
- **Lambda/SSM**: 자동화된 대응 조치 수행

## 실제 시나리오: 자동 보안 대응

### 시나리오: 악성 API 호출 탐지 및 대응

1. **탐지 단계**
   - GuardDuty가 의심스러운 API 호출 패턴을 탐지
   - Finding 생성: "UnauthorizedAPICall" 유형, HIGH 심각도

2. **통합 단계**
   - Security Hub가 GuardDuty Finding을 수집
   - ASFF 형식으로 표준화하여 저장
   - 관련된 다른 보안 이벤트와 상관관계 분석

3. **자동 대응 단계**
   - EventBridge가 Security Hub 이벤트를 감지
   - 사전 정의된 룰에 따라 Lambda 함수 실행
   - 자동 조치 수행:
     - 해당 IP를 WAF 차단 목록에 추가
     - IAM 액세스 키 비활성화
     - 보안 그룹 규칙 수정

4. **모니터링 단계**
   - CloudWatch를 통한 지속적인 모니터링
   - 대응 조치의 효과성 검증
   - 필요시 추가 조치 수행

## 핵심 용어 정리

**매니지드 룰셋 (Managed Rule Sets)**
AWS나 보안 업체에서 제공하는 사전 정의된 WAF 규칙 모음입니다. 일반적인 웹 공격 패턴을 빠르게 차단할 수 있어 기본적인 보안 수준을 확보하는 데 유용합니다.

**Finding**
보안 서비스에서 탐지한 위협이나 이상 행위에 대한 상세한 정보를 담은 객체입니다. Security Hub는 다양한 보안 서비스의 Finding을 ASFF 형식으로 표준화하여 통합 관리합니다.

**DRT (DDoS Response Team)**
AWS의 전문 DDoS 대응 팀으로, Shield Advanced 고객에게 심각한 DDoS 공격 발생 시 24시간 지원을 제공합니다. 공격 분석, 완화 전략 수립, 사후 분석 등을 담당합니다.

**ASFF (Amazon Security Finding Format)**
AWS Security Hub에서 사용하는 표준화된 보안 이벤트 형식입니다. 다양한 보안 서비스의 서로 다른 데이터 형식을 통일하여 중앙에서 관리할 수 있게 합니다.

## 보안 아키텍처 설계 고려사항

### 다층 방어 전략
각 보안 서비스는 서로 다른 계층에서 작동하므로, 여러 서비스를 조합하여 다층 방어 체계를 구축해야 합니다. 한 계층에서 놓친 위협을 다른 계층에서 탐지하고 차단할 수 있습니다.

### 자동화의 중요성
수동으로 보안 이벤트를 처리하는 것은 시간이 오래 걸리고 실수가 발생할 수 있습니다. EventBridge와 Lambda를 활용한 자동 대응 시스템을 구축하면 빠르고 일관된 보안 대응이 가능합니다.

### 지속적인 모니터링
보안은 일회성 작업이 아닌 지속적인 프로세스입니다. CloudWatch와 Security Hub를 통해 보안 상태를 지속적으로 모니터링하고, 정기적인 보안 검토를 통해 방어 체계를 개선해야 합니다.

## 참조

- AWS WAF 공식 문서: https://docs.aws.amazon.com/waf/
- AWS Shield 공식 문서: https://docs.aws.amazon.com/shield/
- Amazon GuardDuty 공식 문서: https://docs.aws.amazon.com/guardduty/
- AWS Security Hub 공식 문서: https://docs.aws.amazon.com/securityhub/
- AWS Well-Architected Framework 보안 핵심: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/
- NIST 사이버보안 프레임워크: https://www.nist.gov/cyberframework