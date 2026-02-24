---
title: AWS Organizations
tags: [aws, organizations, multi-account, governance, management, consolidated-billing]
updated: 2026-01-18
---

# AWS Organizations

## 개요

AWS Organizations는 여러 AWS 계정을 중앙에서 관리하는 서비스다. 계정을 그룹화한다 (Organizational Units). 통합 결제를 한다. 정책을 일괄 적용한다 (SCP). 계정 간 리소스를 공유한다.

### 왜 필요한가

하나의 AWS 계정으로 모든 것을 관리하면 위험하다.

**문제 상황:**

**단일 계정 사용:**
```
하나의 AWS 계정:
- 개발 환경
- 스테이징 환경
- 프로덕션 환경
- 테스트
```

**문제점:**

**1. 보안 위험:**
개발자가 실수로 프로덕션 RDS를 삭제할 수 있다. 모든 리소스가 같은 계정에 있기 때문이다.

**2. 권한 관리 복잡:**
IAM Policy가 매우 복잡해진다.
```json
{
  "Condition": {
    "StringEquals": {
      "ec2:ResourceTag/Environment": "Production"
    }
  }
}
```
태그 기반 권한. 실수하기 쉽다.

**3. 비용 분리 불가:**
개발, 스테이징, 프로덕션 비용을 분리할 수 없다. 태그로만 구분해야 한다.

**4. 격리 부족:**
한 환경의 문제가 다른 환경에 영향을 줄 수 있다. 예: Rate Limiting.

**Organizations의 해결:**

**계정 분리:**
```
Organization
├── Dev Account
├── Staging Account
└── Production Account
```

각 환경이 완전히 분리된다. 안전하다.

## 기본 개념

### Organization

조직. 모든 계정의 최상위 컨테이너다.

### Management Account (Master Account)

조직을 관리하는 계정. 처음 Organizations를 만든 계정이다.

**권한:**
- 다른 계정 초대/생성
- OU 생성
- SCP 적용
- 통합 결제 관리

**주의:**
가장 중요한 계정이다. 2FA 필수. 최소 인원만 접근.

### Member Account

조직에 속한 계정.

**제한:**
- 다른 Organization에 참가 불가
- 탈퇴 시 승인 필요

### Organizational Unit (OU)

계정을 그룹화하는 단위. 폴더처럼 사용한다.

**예시:**
```
Root
├── Production OU
│   ├── Prod-App Account
│   └── Prod-DB Account
├── Non-Production OU
│   ├── Dev Account
│   └── Staging Account
└── Security OU
    ├── Audit Account
    └── Log Archive Account
```

## Organization 생성

### 콘솔

1. AWS Organizations 콘솔
2. "Create organization"
3. 기능 선택:
   - All features (권장)
   - Consolidated billing only
4. 생성
5. 이메일 인증

**All features:**
- 통합 결제
- SCP
- Tag Policy
- AI services opt-out

**Consolidated billing only:**
- 통합 결제만

### CLI

```bash
aws organizations create-organization --feature-set ALL
```

## 계정 추가

### 새 계정 생성

**콘솔:**
1. "AWS accounts" → "Add an AWS account"
2. "Create an AWS account"
3. 이름: Dev Account
4. 이메일: dev-aws@example.com
5. IAM role name: OrganizationAccountAccessRole
6. 생성

**CLI:**
```bash
aws organizations create-account \
  --email dev-aws@example.com \
  --account-name "Dev Account" \
  --role-name OrganizationAccountAccessRole
```

**자동으로:**
- 계정 생성
- OrganizationAccountAccessRole 생성 (Management Account에서 접근 가능)
- Organization에 추가

### 기존 계정 초대

**콘솔:**
1. "AWS accounts" → "Add an AWS account"
2. "Invite an existing AWS account"
3. 계정 ID 또는 이메일 입력
4. 초대

**대상 계정에서:**
1. Organizations 콘솔
2. "Invitations" 확인
3. "Accept" 클릭

## Organizational Unit (OU)

### 생성

```bash
aws organizations create-organizational-unit \
  --parent-id r-abc123 \
  --name Production
```

### 계정 이동

```bash
aws organizations move-account \
  --account-id 123456789012 \
  --source-parent-id r-abc123 \
  --destination-parent-id ou-abc123-production
```

### OU 구조 예시

**환경별:**
```
Root
├── Production
│   ├── Prod-Web
│   ├── Prod-API
│   └── Prod-DB
├── Staging
│   └── Staging-All
└── Development
    ├── Dev-Backend
    └── Dev-Frontend
```

**팀별:**
```
Root
├── Backend Team
│   ├── Backend-Prod
│   └── Backend-Dev
├── Frontend Team
│   ├── Frontend-Prod
│   └── Frontend-Dev
└── Data Team
    ├── Data-Prod
    └── Data-Dev
```

**기능별 (추천):**
```
Root
├── Production
├── Non-Production
│   ├── Staging
│   └── Development
├── Security
│   ├── Audit
│   └── Log Archive
└── Shared Services
    ├── DNS
    └── Networking
```

## 통합 결제

### 동작

**개별 계정 사용 시:**
```
Dev Account: $500/월
Staging Account: $300/월
Production Account: $2,000/월

각 계정마다 청구서 3개
```

**Organizations 사용 시:**
```
Management Account에 하나의 청구서:
Total: $2,800/월

계정별 내역:
- Dev: $500
- Staging: $300
- Production: $2,000
```

### 볼륨 할인

**통합 사용량으로 할인:**

**S3 요금 (예시):**
- 0-50 TB: $0.023/GB
- 50-500 TB: $0.022/GB
- 500 TB+: $0.021/GB

**개별 계정:**
- Dev: 30 TB × $0.023 = $690
- Staging: 25 TB × $0.023 = $575
- Production: 40 TB × $0.023 = $920
- 합계: $2,185

**Organizations (95 TB 통합):**
- 0-50 TB: 50 × $0.023 = $1,150
- 50-95 TB: 45 × $0.022 = $990
- 합계: $2,140

**$45 절감**

### Reserved Instances 공유

**시나리오:**
- Production Account: t3.medium RI 10개 구매
- 실제 사용: 8개
- 여유: 2개

**자동 공유:**
- Dev Account가 t3.medium 2개 사용
- RI 할인 자동 적용
- RI 낭비 없음

**효과:**
RI 활용률 100% 유지.

## 계정 간 접근

### OrganizationAccountAccessRole

**Management Account → Member Account 접근:**

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/OrganizationAccountAccessRole \
  --role-session-name dev-session
```

**임시 자격 증명 발급:**
```json
{
  "Credentials": {
    "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
    "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "SessionToken": "...",
    "Expiration": "2026-01-18T12:00:00Z"
  }
}
```

**환경 변수 설정:**
```bash
export AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_SESSION_TOKEN=...

# 이제 Dev Account로 작업
aws ec2 describe-instances
```

### 스위치 롤 (콘솔)

**Management Account 콘솔에서:**
1. 우측 상단 계정 메뉴
2. "Switch Role"
3. Account: 123456789012
4. Role: OrganizationAccountAccessRole
5. Display Name: Dev Account
6. Color 선택
7. Switch

Dev Account 콘솔로 전환된다.

## 리소스 공유

### RAM (Resource Access Manager)

계정 간 리소스를 공유한다.

**공유 가능 리소스:**
- VPC Subnets
- Transit Gateway
- Route 53 Resolver Rules
- License Manager Configurations

**예시: VPC Subnet 공유**

**Shared Services Account:**
```bash
aws ram create-resource-share \
  --name shared-vpc \
  --resource-arns arn:aws:ec2:us-west-2:111111111111:subnet/subnet-12345678 \
  --principals arn:aws:organizations::123456789012:organization/o-abc123
```

**모든 조직 계정이 해당 서브넷 사용 가능:**
- 중앙 집중식 네트워킹
- 각 계정이 VPC를 만들 필요 없음

## 서비스 통합

### CloudTrail

**조직 Trail:**
모든 계정의 API 호출을 하나의 S3 버킷에 저장.

**설정 (Management Account):**
```bash
aws cloudtrail create-trail \
  --name organization-trail \
  --s3-bucket-name organization-cloudtrail-logs \
  --is-organization-trail
```

**효과:**
- 중앙 집중식 감사
- Security Account에서 모든 계정 모니터링

### Config

**조직 Config Rules:**
모든 계정에 Config 규칙을 일괄 적용.

**예시:**
```bash
aws configservice put-organization-config-rule \
  --organization-config-rule-name s3-bucket-encryption \
  --organization-managed-rule-metadata \
    RuleIdentifier=S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED
```

모든 계정의 S3 버킷이 암호화되었는지 자동 검사.

### SSO (IAM Identity Center)

**단일 로그인:**
```
SSO Portal → 계정 선택 → Role 선택 → 콘솔 접속
```

**설정:**
1. IAM Identity Center 활성화
2. Permission Set 생성 (AdministratorAccess, ReadOnlyAccess 등)
3. 사용자/그룹에 Permission Set 할당

**효과:**
- 각 계정마다 IAM User 생성 불필요
- 중앙에서 권한 관리
- 2FA 한 번만 설정

## 실무 구조

### 스타트업 (소규모)

```
Root
├── Production
├── Development
└── Shared Services
```

**3개 계정:**
- 간단
- 비용 저렴
- 관리 쉬움

### 성장 단계

```
Root
├── Production
│   ├── Prod-App
│   └── Prod-Data
├── Non-Production
│   ├── Staging
│   └── Development
├── Security
│   └── Audit
└── Shared Services
    └── Network
```

**7개 계정:**
- 환경 격리
- 보안 계정 분리
- 네트워크 중앙화

### 대기업

```
Root
├── Production
│   ├── Prod-US
│   ├── Prod-EU
│   └── Prod-APAC
├── Non-Production
│   ├── Staging-US
│   ├── Staging-EU
│   ├── Dev-Backend
│   └── Dev-Frontend
├── Security
│   ├── Audit
│   ├── Log Archive
│   └── Security Tools
└── Shared Services
    ├── Network
    ├── DNS
    └── CI/CD
```

**15개+ 계정:**
- 리전별 분리
- 세밀한 격리
- 중앙 집중식 보안

## 비용

### Organizations 자체

**무료**

### 계정 비용

**무료:**
각 AWS 계정 자체는 무료. 사용한 리소스만 과금.

**예시:**
- 계정 10개
- Organizations 비용: $0
- 리소스 비용: 사용한 만큼

### 통합 결제 효과

**볼륨 할인:**
월 $100-200 절감 (규모에 따라)

**RI 공유:**
활용률 증가 → 월 $500+ 절감

**총 효과:**
Organizations 사용이 오히려 저렴하다.

## 마이그레이션

### 단일 계정 → 다중 계정

**기존:**
하나의 계정에 모든 환경.

**목표:**
환경별로 계정 분리.

**과정:**

**1. Organization 생성:**
```bash
aws organizations create-organization
```

**2. 새 계정 생성:**
```bash
aws organizations create-account --email dev@example.com --account-name Dev
aws organizations create-account --email staging@example.com --account-name Staging
aws organizations create-account --email prod@example.com --account-name Prod
```

**3. 리소스 이동:**
- 개발 리소스 → Dev Account로 재생성
- 스테이징 리소스 → Staging Account로 재생성
- 프로덕션은 기존 계정 유지 (Production Account로 지정)

**4. 점진적 마이그레이션:**
- 개발부터 시작
- 스테이징
- 마지막에 프로덕션

**주의:**
리소스를 직접 이동할 수 없다. 재생성해야 한다.

## 참고

- AWS Organizations 가이드: https://docs.aws.amazon.com/organizations/
- 모범 사례: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices.html
- 계정 구조: https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/
- RAM: https://docs.aws.amazon.com/ram/

