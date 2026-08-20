---
title: AWS 보안 서비스 통합 아키텍처
tags: [aws, security, cloud]
updated: 2025-09-23
---

# AWS 보안 서비스 통합 아키텍처

## 개요

AWS 보안 서비스는 각각 독립적으로 동작하면서도 서로 연동돼 하나의 방어 체계를 이룬다. 여기서는 AWS WAF, Shield, GuardDuty, Security Hub가 어떻게 맞물려 다층 보안을 만드는지 살펴본다.

## 핵심 보안 서비스

### AWS WAF (Web Application Firewall)

**개념과 역할**
AWS WAF는 애플리케이션 계층(Layer 7)에서 도는 웹 방화벽이다. HTTP/HTTPS 트래픽을 실시간으로 분석하고 걸러낸다. 네트워크 방화벽과 달리 애플리케이션의 비즈니스 로직까지 이해하고 보호한다.

**주요 기능**
- **규칙 기반 필터링**: 요청 속성(IP 주소, 헤더, 쿼리 파라미터, 요청 본문 등)을 보고 허용, 차단, 카운트 결정
- **매니지드 룰셋**: AWS와 보안 업체가 미리 만들어둔 규칙 세트로 일반적인 공격 패턴 차단
- **사용자 정의 룰**: 애플리케이션 요구사항에 맞춘 보안 규칙 직접 작성
- **레이트 리미팅**: 특정 IP나 사용자가 쏟아내는 과도한 요청을 자동 제한

**로그 및 모니터링**
WAF는 요청마다 상세 로그를 남긴다. 이 로그를 CloudWatch Logs, S3, Kinesis Data Streams로 보내면 보안 분석과 트렌드 파악에 쓸 수 있다.

### AWS Shield

**개념과 역할**
AWS Shield는 DDoS(분산 서비스 거부) 공격에서 AWS 리소스를 지키는 완화 서비스다. DDoS는 정상적인 서비스 요청을 압도해 서비스를 못 쓰게 만드는 공격이다.

**Shield Standard**
- 모든 AWS 고객에게 무료로 제공
- 일반적인 DDoS 공격은 자동 탐지 및 완화
- 네트워크 계층(Layer 3, 4) 공격 기본 보호

**Shield Advanced**
- 고급 DDoS 보호 기능 제공
- 애플리케이션 계층(Layer 7) 공격까지 보호
- 공격 중 발생하는 데이터 전송 비용 보호
- 24x7 DDoS Response Team(DRT) 지원
- WAF와 통합된 자동 완화 기능

### Amazon GuardDuty

**개념과 역할**
GuardDuty는 AWS 환경에서 벌어지는 악의적인 활동과 비정상 동작을 잡아내는 위협 탐지 서비스다. 머신러닝과 위협 인텔리전스로 보안 위협을 계속 모니터링한다.

**데이터 소스**
- **CloudTrail**: API 호출 로그 분석
- **VPC Flow Logs**: 네트워크 트래픽 패턴 분석
- **DNS Logs**: DNS 쿼리 패턴 분석
- **EKS 감사 로그**: Kubernetes 클러스터 활동 분석

**탐지 결과**
GuardDuty는 찾아낸 위협을 Finding 형태로 보고한다. Finding 하나에는 다음이 담긴다.
- **심각도**: CRITICAL, HIGH, MEDIUM, LOW
- **영향받는 리소스**: EC2 인스턴스, IAM 사용자 등
- **위협 유형**: 악성 IP 통신, 권한 상승 시도 등
- **상세 설명**: 탐지된 활동의 구체적인 내용

### AWS Security Hub

**개념과 역할**
Security Hub는 여러 AWS 보안 서비스가 내놓은 결과를 한곳에 모아 관리하는 서비스다. 도구별로 흩어진 결과를 대시보드 하나에서 보고, 상관관계를 분석해 전체 보안 상황을 파악한다.

**통합 기능**
- **ASFF(Amazon Security Finding Format)**: 서비스마다 다른 결과를 표준화된 형식으로 변환
- **상관관계 분석**: 여러 서비스에서 나온 관련 보안 이벤트를 묶어서 분석
- **자동 대응**: EventBridge와 연동해 보안 이벤트가 뜨면 대응 조치 자동 실행

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
   - CloudWatch로 지속 모니터링
   - 대응 조치가 실제로 먹혔는지 검증
   - 필요시 추가 조치 수행

## 핵심 용어 정리

**매니지드 룰셋 (Managed Rule Sets)**
AWS나 보안 업체가 미리 만들어둔 WAF 규칙 모음이다. 일반적인 웹 공격 패턴을 빠르게 막아줘서 기본 보안 수준을 잡는 데 쓸 만하다.

**Finding**
보안 서비스가 탐지한 위협이나 이상 행위의 상세 정보를 담은 객체다. Security Hub는 서비스마다 다른 Finding을 ASFF 형식으로 표준화해 한곳에서 관리한다.

**DRT (DDoS Response Team)**
AWS의 전문 DDoS 대응 팀이다. Shield Advanced 고객이 심각한 DDoS 공격을 받으면 24시간 지원한다. 공격 분석, 완화 전략 수립, 사후 분석을 맡는다.

**ASFF (Amazon Security Finding Format)**
AWS Security Hub가 쓰는 표준화된 보안 이벤트 형식이다. 서비스마다 제각각인 데이터 형식을 하나로 맞춰 중앙에서 관리하게 해준다.

## 보안 아키텍처 설계 고려사항

### 다층 방어 전략
보안 서비스는 저마다 다른 계층에서 작동한다. 그래서 여러 서비스를 조합해 다층 방어 체계를 세워야 한다. 한 계층에서 놓친 위협을 다른 계층에서 탐지하고 차단한다.

### 자동화의 중요성
보안 이벤트를 손으로 처리하면 시간이 오래 걸리고 실수도 난다. EventBridge와 Lambda로 자동 대응 시스템을 짜두면 빠르고 일관되게 대응한다.

### 지속적인 모니터링
보안은 한 번 하고 끝나는 작업이 아니라 계속 굴러가는 프로세스다. CloudWatch와 Security Hub로 보안 상태를 계속 지켜보고, 정기적인 보안 검토로 방어 체계를 개선해야 한다.

---

## IAM 최소 권한 정책 예제

### 서비스 계정 — S3 특정 버킷 읽기 전용

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadSpecificBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket",
        "arn:aws:s3:::my-app-bucket/*"
      ]
    }
  ]
}
```

### ECS Task Role — Secrets Manager + 특정 파라미터만

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:prod/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:ap-northeast-2:123456789012:parameter/prod/*"
    }
  ]
}
```

### IAM 권한 경계 (Permission Boundary) — 개발자 계정 제한

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "s3:List*",
        "s3:Get*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "logs:Get*",
        "logs:Describe*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": [
        "iam:*",
        "organizations:*",
        "account:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## VPC 보안 설계 패턴

```
프로덕션 권장 구조:

  인터넷
    │
  Internet Gateway
    │
  ┌─────────────────────────────┐
  │ Public Subnet                │
  │  ALB (443/80 인바운드)       │
  │  NAT Gateway                 │
  └─────────────────────────────┘
    │ (ALB → 8080만 허용)
  ┌─────────────────────────────┐
  │ Private Subnet (App)         │
  │  ECS Tasks / EC2             │
  │  (인터넷 직접 접근 불가)     │
  └─────────────────────────────┘
    │ (App → DB 포트만 허용)
  ┌─────────────────────────────┐
  │ Private Subnet (DB)          │
  │  RDS, ElastiCache            │
  │  (앱 서브넷에서만 접근 가능) │
  └─────────────────────────────┘
```

### 보안 그룹 설계 기준

```bash
# ALB 보안 그룹 — 인터넷에서 80/443만 허용
aws ec2 create-security-group \
  --group-name alb-sg \
  --description "ALB Security Group"

aws ec2 authorize-security-group-ingress \
  --group-id sg-alb-xxx \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-alb-xxx \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

# App 보안 그룹 — ALB에서만 8080 허용
aws ec2 authorize-security-group-ingress \
  --group-id sg-app-xxx \
  --protocol tcp --port 8080 \
  --source-group sg-alb-xxx   # ALB SG에서만 허용

# DB 보안 그룹 — App에서만 3306 허용
aws ec2 authorize-security-group-ingress \
  --group-id sg-db-xxx \
  --protocol tcp --port 3306 \
  --source-group sg-app-xxx   # App SG에서만 허용
```

### 보안 그룹 vs NACL

| 항목 | 보안 그룹 | NACL |
|------|---------|------|
| **적용 범위** | ENI (인스턴스) | 서브넷 |
| **규칙 평가** | 모든 규칙 | 번호 순서대로 |
| **상태** | Stateful (응답 자동 허용) | Stateless (인/아웃 모두 설정) |
| **기본값** | 모든 아웃바운드 허용 | 모든 트래픽 허용 |
| **권장 용도** | 주 방어선 | 추가 서브넷 레벨 방어 |

---

## AWS 보안 서비스 활성화 체크리스트

### 필수 (모든 계정)

```bash
# 1. CloudTrail — API 호출 이력 기록
aws cloudtrail create-trail \
  --name prod-trail \
  --s3-bucket-name my-cloudtrail-logs \
  --is-multi-region-trail \
  --enable-log-file-validation

aws cloudtrail start-logging --name prod-trail

# 2. GuardDuty — 위협 탐지 활성화
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES

# 3. AWS Config — 리소스 변경 추적
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::123456789012:role/config-role \
  --recording-group allSupported=true

# 4. Security Hub — 보안 결과 중앙 집계
aws securityhub enable-security-hub \
  --enable-default-standards
```

### 권장 설정

```bash
# S3 퍼블릭 액세스 차단 (계정 전체)
aws s3control put-public-access-block \
  --account-id 123456789012 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# IAM 패스워드 정책 강화
aws iam update-account-password-policy \
  --minimum-password-length 14 \
  --require-symbols \
  --require-numbers \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --max-password-age 90 \
  --password-reuse-prevention 12

# MFA 미사용 계정 탐지 (IAM Access Analyzer)
aws accessanalyzer create-analyzer \
  --analyzer-name account-analyzer \
  --type ACCOUNT
```

---

## 보안 체크리스트

### 계정 수준
- [ ] Root 계정 MFA 활성화
- [ ] Root 계정 액세스 키 없음 확인
- [ ] CloudTrail 멀티 리전 활성화
- [ ] GuardDuty 활성화
- [ ] Security Hub 활성화
- [ ] AWS Config 활성화

### IAM
- [ ] 모든 IAM 사용자 MFA 활성화
- [ ] 사용하지 않는 IAM 자격 증명 삭제 (90일 이상 미사용)
- [ ] 최소 권한 원칙 적용
- [ ] IAM 역할로 임시 자격 증명 사용 (장기 액세스 키 최소화)

### 네트워크
- [ ] 모든 리소스 VPC 내 배치
- [ ] DB/캐시는 Private Subnet에만 배치
- [ ] 보안 그룹 0.0.0.0/0 인바운드 최소화
- [ ] VPC Flow Logs 활성화

### 데이터
- [ ] S3 퍼블릭 액세스 차단
- [ ] RDS/EBS 저장 암호화 활성화
- [ ] 전송 암호화 (TLS 1.2+) 강제
- [ ] 민감 정보 Secrets Manager 보관 (하드코딩 금지)

## 참조

- AWS WAF 공식 문서: https://docs.aws.amazon.com/waf/
- AWS Shield 공식 문서: https://docs.aws.amazon.com/shield/
- Amazon GuardDuty 공식 문서: https://docs.aws.amazon.com/guardduty/
- AWS Security Hub 공식 문서: https://docs.aws.amazon.com/securityhub/
- AWS Well-Architected Framework 보안 핵심: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/
- NIST 사이버보안 프레임워크: https://www.nist.gov/cyberframework