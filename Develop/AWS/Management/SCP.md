---
title: AWS SCP (Service Control Policies)
tags: [aws, scp, organizations, policy, governance, security, compliance]
updated: 2026-01-18
---

# AWS SCP (Service Control Policies)

## 개요

SCP는 Organizations의 정책이다. 계정이나 OU에서 사용할 수 있는 AWS 서비스와 작업을 제한한다. 최대 권한의 경계다. IAM보다 상위에 있다. 규정 준수를 강제한다. 실수를 방지한다.

### 왜 필요한가

IAM만으로는 부족하다.

**문제 상황:**

**시나리오:**
개발자에게 EC2 관리 권한을 준다.

**IAM Policy:**
```json
{
  "Effect": "Allow",
  "Action": "ec2:*",
  "Resource": "*"
}
```

**문제:**
개발자가 실수로 (또는 고의로) 자신의 권한을 확대할 수 있다.

```bash
# 자기 자신에게 AdministratorAccess 부여
aws iam attach-user-policy \
  --user-name myself \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

이제 모든 권한을 가진다. 프로덕션 DB 삭제 가능.

**SCP의 해결:**

**계정 레벨 제한:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "iam:*",
      "Resource": "*"
    }
  ]
}
```

이 SCP가 적용된 계정에서는 **누구도** IAM 작업을 할 수 없다. 관리자라도 불가능.

IAM 권한을 스스로 확대하는 것을 원천 차단한다.

## IAM vs SCP

### IAM Policy

**개별 사용자/역할 권한:**
```
IAM: "이 사용자는 EC2를 시작할 수 있다"
```

**Allow 기반:**
명시적으로 허용해야 한다.

### SCP

**계정 전체 제한:**
```
SCP: "이 계정의 누구도 us-east-1 외 리전을 사용할 수 없다"
```

**Deny 기반 (주로):**
명시적으로 차단한다.

### 관계

**SCP와 IAM 모두 허용해야 실행 가능:**

```
SCP: 허용
IAM: 허용
→ 실행 가능

SCP: 차단
IAM: 허용
→ 실행 불가

SCP: 허용
IAM: 차단
→ 실행 불가
```

**SCP는 최대 권한의 경계다.**

## 기본 SCP

### FullAWSAccess

Organizations 생성 시 자동으로 적용된다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```

모든 작업을 허용한다. 제한이 없다.

**주의:**
이 SCP를 제거하면 아무것도 할 수 없다. 다른 SCP로 명시적으로 허용해야 한다.

## 실무 SCP

### 리전 제한

**요구사항:**
비용 절감과 규정 준수를 위해 특정 리전만 사용한다.

**SCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAllOutsideAllowedRegions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-west-2",
            "ap-northeast-2"
          ]
        }
      }
    }
  ]
}
```

**동작:**
us-west-2, ap-northeast-2 외 리전에서는 아무것도 할 수 없다.

**예외 (글로벌 서비스):**
IAM, CloudFront, Route 53은 리전이 없다. 명시적으로 허용한다.

```json
{
  "Condition": {
    "StringNotEquals": {
      "aws:RequestedRegion": ["us-west-2"]
    },
    "ForAllValues:StringNotLike": {
      "aws:PrincipalOrgID": ["o-*"]
    }
  },
  "NotAction": [
    "iam:*",
    "cloudfront:*",
    "route53:*",
    "support:*"
  ]
}
```

### 루트 사용자 제한

**요구사항:**
루트 사용자는 매우 위험하다. 일상적인 사용을 금지한다.

**SCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyRootUser",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:root"
        }
      }
    }
  ]
}
```

**동작:**
루트 사용자는 아무것도 할 수 없다.

**예외:**
계정 닫기, 결제 등 루트만 할 수 있는 작업은 Management Account에서 한다.

### 특정 서비스 차단

**요구사항:**
비용이 많이 드는 서비스를 차단한다.

**SCP (EMR, Redshift 차단):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyExpensiveServices",
      "Effect": "Deny",
      "Action": [
        "emr:*",
        "redshift:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**적용:**
Development OU에 적용. 개발 계정에서는 EMR, Redshift 사용 불가.

### 인스턴스 타입 제한

**요구사항:**
개발 환경에서 큰 인스턴스를 막는다.

**SCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLargeInstances",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotLike": {
          "ec2:InstanceType": [
            "t3.*",
            "t2.*"
          ]
        }
      }
    }
  ]
}
```

**동작:**
t3, t2 인스턴스만 시작 가능. m5, r5 등 큰 인스턴스는 차단.

### 보안 그룹 0.0.0.0/0 차단

**요구사항:**
보안 그룹에서 전 세계 접근을 막는다.

**SCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicSecurityGroups",
      "Effect": "Deny",
      "Action": [
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress"
      ],
      "Resource": "*",
      "Condition": {
        "ForAnyValue:StringEquals": {
          "ec2:IpProtocol": "tcp",
          "ec2:FromPort": "22"
        },
        "ForAnyValue:StringLike": {
          "ec2:CidrIp": ["0.0.0.0/0"]
        }
      }
    }
  ]
}
```

**동작:**
SSH 포트 (22)를 0.0.0.0/0에 여는 것을 차단.

### S3 Public 접근 차단

**요구사항:**
실수로 S3 버킷을 public으로 만드는 것을 막는다.

**SCP:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyS3PublicAccess",
      "Effect": "Deny",
      "Action": [
        "s3:PutBucketPublicAccessBlock",
        "s3:PutAccountPublicAccessBlock"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "s3:BlockPublicAcls": "false",
          "s3:BlockPublicPolicy": "false",
          "s3:IgnorePublicAcls": "false",
          "s3:RestrictPublicBuckets": "false"
        }
      }
    }
  ]
}
```

## SCP 적용

### OU에 적용

**콘솔:**
1. Organizations 콘솔
2. "Policies" → "Service control policies"
3. SCP 선택
4. "Targets" 탭
5. "Attach" 클릭
6. OU 선택

**CLI:**
```bash
aws organizations attach-policy \
  --policy-id p-abc123 \
  --target-id ou-abc123-production
```

**효과:**
해당 OU와 하위 모든 계정에 적용된다.

### 계정에 적용

```bash
aws organizations attach-policy \
  --policy-id p-abc123 \
  --target-id 123456789012
```

특정 계정에만 적용.

### 상속

```
Root
├── Production OU (SCP: Deny EMR)
│   ├── Prod-App (상속: Deny EMR)
│   └── Prod-DB (상속: Deny EMR)
└── Development OU
    └── Dev (SCP 없음)
```

Production OU의 SCP가 하위 계정에 자동 적용된다.

## 계층 구조

### 예시

```
Root
├── SCP: DenyAllOutsideUS (모든 계정)
├── Production OU
│   ├── SCP: DenyRootUser (Production 계정들)
│   ├── Prod-App
│   │   └── SCP: DenyLargeInstances (Prod-App만)
│   └── Prod-DB
└── Development OU
    ├── SCP: DenyExpensiveServices (개발 계정들)
    └── Dev
```

**Prod-App에 적용되는 SCP:**
1. Root의 DenyAllOutsideUS
2. Production OU의 DenyRootUser
3. Prod-App의 DenyLargeInstances

**3개 모두 적용된다.**

## 테스트

### IAM Policy Simulator

SCP를 테스트한다.

**콘솔:**
1. IAM 콘솔
2. "Policy Simulator"
3. "Service Control Policy" 선택
4. SCP JSON 붙여넣기
5. Action 선택 (예: ec2:RunInstances)
6. Simulate

**결과:**
- Allowed: SCP가 허용
- Denied: SCP가 차단

### 실제 테스트

**테스트 계정:**
1. 테스트용 Member Account 생성
2. SCP 적용
3. 실제로 작업 시도
4. 차단되는지 확인

**예시:**
```bash
# us-east-1 차단 SCP 적용 후
aws ec2 describe-instances --region us-east-1

# 에러
An error occurred (UnauthorizedOperation) when calling the DescribeInstances operation: You are not authorized to perform this operation.
```

정상 작동.

## 실수 방지

### Deny는 신중하게

**잘못된 SCP:**
```json
{
  "Effect": "Deny",
  "Action": "*",
  "Resource": "*"
}
```

**결과:**
아무것도 할 수 없다. 계정이 잠긴다.

**복구:**
Management Account에서 SCP를 제거한다. Member Account에서는 불가능.

### Management Account 제외

**권장:**
Management Account에는 SCP를 적용하지 않는다.

**이유:**
SCP가 잘못되어도 Management Account에서 수정할 수 있다.

### 점진적 적용

**절차:**
1. 테스트 계정에 적용
2. 문제 없으면 Development OU에 적용
3. Staging OU에 적용
4. 마지막에 Production OU에 적용

갑자기 모든 계정에 적용하면 위험하다.

## 실무 구조

### 스타트업

```
Root (FullAWSAccess)
├── SCP: DenyRootUser
├── Production (추가 SCP 없음)
└── Development
    └── SCP: DenyExpensiveServices
```

**간단:**
- 루트 사용자 차단
- 개발 환경 비용 제한

### 중견 기업

```
Root
├── SCP: DenyAllOutsideUS
├── SCP: DenyRootUser
├── Production
│   └── SCP: RequireMFA
├── Non-Production
│   ├── SCP: DenyExpensiveServices
│   └── Development
│       └── SCP: DenyLargeInstances
└── Security
    └── (SCP 없음 - 감사 목적)
```

**세밀한 제어:**
- 리전 제한
- MFA 강제
- 환경별 제한

### 대기업

```
Root
├── SCP: DenyAllOutsideAllowedRegions
├── SCP: DenyRootUser
├── SCP: RequireTags
├── Production
│   ├── SCP: RequireEncryption
│   ├── SCP: DenyPublicAccess
│   └── (세부 OU별 추가 SCP)
├── Non-Production
│   ├── SCP: DenyExpensiveServices
│   └── SCP: DenyLargeInstances
└── Security
    └── SCP: AuditOnly
```

**규정 준수:**
- 암호화 강제
- 태그 필수
- Public 접근 차단

## 비용

### SCP 자체

**무료**

Organizations 기능의 일부. 추가 비용 없음.

### 비용 절감 효과

**리전 제한:**
실수로 비싼 리전 사용 방지.

**인스턴스 타입 제한:**
개발자가 r5.24xlarge 실수로 실행 방지 ($6.912/시간).

**비싼 서비스 차단:**
EMR, Redshift 무분별한 사용 방지.

**총 효과:**
월 $1,000+ 절감 가능.

## 참고

- SCP 가이드: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- SCP 예시: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html
- Policy Simulator: https://policysim.aws.amazon.com/
- 모범 사례: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices.html

