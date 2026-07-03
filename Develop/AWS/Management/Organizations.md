---
title: AWS Organizations
tags: [aws, organizations, multi-account, governance, management, consolidated-billing]
updated: 2026-05-08
---

# AWS Organizations

## 개요

AWS Organizations는 여러 AWS 계정을 하나의 조직 트리로 묶어서 관리하는 서비스다. 결제는 한 계정에 합치고, 정책은 트리의 노드 단위로 내려보내고, 일부 서비스는 조직 전체에 위임 관리자를 둔다. 핵심 모델은 단순하다. **루트(Root)** 아래에 **OU(Organizational Unit)** 가 들어가고, OU나 루트 바로 아래에 **계정(Account)** 이 매달린다. 정책(SCP, Tag Policy, Backup Policy 등)은 이 노드들에 붙고, 부모에서 자식으로 상속된다.

운영 6년 차 정도 가도 처음에는 한 계정에서 시작한다. 회사가 커지면서 결국 갈라지는데, 그때 Organizations를 도입한다. 핵심 동기는 보통 셋이다. 청구서를 합쳐서 볼륨 할인을 받으려는 재무 요구, 환경별 폭발 반경을 끊으려는 보안 요구, 그리고 SOC2/ISO 같은 감사 대응이다. 어떤 동기로 들어오든 결과적으로 OU 설계와 SCP가 가장 까다로운 작업이 된다.

### 한 계정에 다 몰아넣었을 때 무엇이 깨지는가

겉으로는 "IAM으로 잘 끊으면 되지 않나" 싶지만, 실제로 사고 나는 지점은 IAM이 닿지 않는 부분이다.

```
하나의 계정 안:
- 개발 환경 EC2/RDS
- 스테이징 환경 EC2/RDS
- 프로덕션 환경 EC2/RDS
```

이 구조에서 막상 운영해 보면 다음과 같은 일이 일어난다.

- 서비스 한도(quota)가 환경 간에 공유된다. 개발에서 EC2 vCPU를 다 쓰면 프로덕션 오토스케일이 막힌다.
- VPC 피어링·NAT·라우팅 테이블이 뒤엉킨다. 환경 분리가 IAM 태그 조건문으로 흐릿해진다.
- 비용을 태그로만 분리해야 하는데, 태그가 빠진 리소스는 추적이 안 된다.
- 프로덕션 KMS 키가 개발자 IAM에 잘못 노출되면 데이터 평문 노출 사고가 한 번에 일어난다.
- 결정적으로, 누군가 IAM 권한을 잘못 만들면 차단할 상위 보호막이 없다.

계정을 분리하면 위 문제 대부분이 자연스럽게 사라진다. 계정 경계는 AWS가 강제하는 가장 강한 격리 단위라서, IAM 정책을 잘못 써도 다른 계정 리소스에는 닿지 않는다.

## 핵심 용어

### Management Account (구 Master Account)

조직을 처음 만든 계정이다. 다른 모든 계정의 청구가 여기로 합쳐진다. 다음 권한이 이 계정에 묶인다.

- 계정 생성·초대·이동·제거
- OU 생성 및 정책 부착
- Trusted Access 활성화, Delegated Administrator 지정
- 통합 결제와 RI/Savings Plans 공유 설정 변경

이 계정은 워크로드를 절대 실행하지 않는다. 실수로 lambda 하나 돌렸다가 그 계정의 보안 사고가 조직 전체를 흔드는 사고가 된다. 이 계정의 root 자격증명을 통제하는 게 멀티 계정 보안의 출발점이다.

### Member Account

조직 안에 속한 일반 계정이다. 다른 조직으로 이중 가입은 불가능하다. 조직에서 제거하려면 결제 연락처·세금 정보 등이 채워져 있어야 하고 Management Account의 승인이 필요하다.

### Organizational Unit (OU)

계정을 묶는 폴더 같은 노드다. 정책 부착·상속의 단위이기도 하다. 한 OU에는 다른 OU와 계정을 함께 둘 수 있다. 깊이는 5단계까지 허용되는데, 실무에서 4단계를 넘어가면 정책 추적이 거의 불가능해진다.

### Root

조직의 최상위 노드. 콘솔에서 단일 노드처럼 보이지만, 정책을 직접 붙일 수 있다. Root에 SCP를 붙이면 Management Account를 제외한 모든 계정에 도달한다.

## OU 계층 구조 설계 패턴

OU를 환경별(dev/stg/prod)로 자르느냐, 팀별로 자르느냐는 항상 나오는 논쟁이다. AWS가 백서에서 권장하는 형태는 환경이나 팀이 아니라 **"같은 통제가 필요한 계정끼리 묶는다"** 다. 정책 부착이 곧 OU의 존재 이유이기 때문이다.

실무에서 자리 잡은 형태는 보통 이렇다.

```
Root
├── Security OU
│   ├── LogArchive 계정
│   ├── Audit 계정 (Security Hub / GuardDuty 위임)
│   └── Tooling 계정 (이미지 빌드, AMI 공유 등)
├── Infrastructure OU
│   ├── Network 계정 (Transit Gateway, Route53 호스팅)
│   ├── Shared Services 계정
│   └── Backup 계정
├── Workloads OU
│   ├── Prod OU
│   │   ├── Service-A-Prod
│   │   └── Service-B-Prod
│   └── NonProd OU
│       ├── Service-A-Dev
│       └── Service-A-Stg
├── Sandbox OU
│   └── 개인 실험 계정들 (예산 알람·자동 정리 강제)
├── Suspended OU
│   └── 비활성/탈퇴 예정 계정 (전체 차단 SCP)
├── Exceptions OU
│   └── 일반 SCP를 우회해야 하는 특수 계정
└── PolicyStaging OU
    └── 새 SCP를 먼저 붙여보는 계정
```

이 구조의 핵심은 다음 네 가지다.

**1. Security와 Workloads를 형제 노드로 둔다.** Security 계정은 일반 워크로드 SCP에 영향받지 않아야 한다. GuardDuty가 Workloads OU 차단 SCP에 막히는 사고가 흔하다.

**2. Prod와 NonProd를 같은 부모 OU 아래 둔다.** 워크로드 공통 SCP(예: 글로벌 리전 차단, 결제 정보 보호)는 Workloads OU에 한 번만 붙이고, 차이 나는 정책만 Prod/NonProd에 따로 붙인다. 같은 SCP를 두 군데에 붙여두면 한쪽만 고쳐서 정책이 어긋나는 사고가 반드시 난다.

**3. Sandbox와 Suspended를 분리한다.** Sandbox는 자유롭되 비용·시간 한도가 강제되고, Suspended는 사실상 모든 API를 차단해 좀비 리소스가 더 안 생기게 한다.

**4. PolicyStaging을 둔다.** 새 SCP를 만들면 먼저 이 OU의 빈 계정에 붙여서 의도한 차단이 일어나는지 본다. 곧장 Prod에 붙이면 결제 작업이 막히는 식의 사고가 일어난다.

OU를 지나치게 잘게 자르면 같은 정책을 여러 OU에 중복 부착하느라 시간을 다 쓰게 된다. 보통 한 OU에 5~30개 계정이 들어가는 정도가 관리 가능한 범위다.

## 통합 결제와 볼륨 할인 동작 방식

통합 결제(Consolidated Billing)는 Organizations의 가장 단순하면서 오해가 많은 기능이다. "그냥 청구서 합쳐주는 것" 정도로 알고 있다가 정산을 시작하면 모델이 생각보다 까다롭다는 것을 알게 된다.

### 청구의 흐름

각 Member Account가 사용한 비용이 매시간 단위로 Management Account의 청구 데이터에 합쳐진다. Member Account는 자기 계정 비용만 콘솔에서 본다. Management Account는 전체 합계와 계정별 분개를 본다. 결제 수단(신용카드)은 Management Account 한 군데에만 등록된다.

청구 데이터는 다음 두 갈래로 흘러나간다.

- **Cost Explorer / Billing 콘솔**: Management Account에서 계정·태그·서비스별 분리 가능
- **Cost and Usage Report (CUR)**: S3에 시간 단위 raw 청구 데이터를 떨어뜨린다. 정산이나 챠지백을 자동화하려면 이게 사실상 유일한 통로다.

### 볼륨 할인 (Tiered Pricing)

S3, 데이터 전송 같은 서비스는 사용량이 늘면 단가가 떨어지는 계단형 요금이다. 통합 결제는 모든 Member Account의 사용량을 **하나로 합쳐서** 이 계단을 적용한다.

S3 Standard 첫 50TB는 GB당 $0.023, 50~500TB는 $0.022 같은 식이라고 하자.

```
계정 분리 시:
- A 계정: 30TB × $0.023 = $690
- B 계정: 25TB × $0.023 = $575
- C 계정: 40TB × $0.023 = $920
합계: $2,185

통합 청구 (총 95TB):
- 0~50TB: 50 × $0.023 = $1,150
- 50~95TB: 45 × $0.022 = $990
합계: $2,140
```

차이는 작아 보이지만 데이터 전송에서는 격차가 훨씬 크다. 가령 인터넷 아웃바운드는 첫 10TB가 GB당 $0.09, 10~50TB가 $0.085로 떨어지는데, 한 계정에서 1TB씩 쓰는 계정이 10개라면 합칠 때 비로소 다음 계단으로 넘어간다.

다만 모든 서비스가 합산 대상은 아니다. Free Tier는 한 조직에서 한 계정만 받는 것으로 처리된다. Marketplace 구독은 합산되지 않는다. RDS 같은 서비스의 일부 요금은 계정별로 별도 계산된다. 정산 모델을 짤 때는 CUR을 직접 뜯어봐야 정확하다.

### Reserved Instance / Savings Plans 공유

이 부분이 통합 결제의 가장 큰 금전적 효과다. Management Account의 결제 설정에서 "RI/Savings Plans Discount Sharing"을 켜면, 한 계정에서 산 RI/SP가 다른 계정의 동일 사용량에 자동으로 적용된다.

```
A 계정: t3.medium RI 10개 구매, 실제 사용 6개
B 계정: t3.medium On-Demand 5개 사용

공유 ON 시:
- A의 RI 6개가 A에 적용
- A의 남는 RI 4개가 B의 4개에 적용
- B의 1개만 On-Demand 요금
```

이걸 모르고 운영하면 RI 활용률이 50%대에서 머문다. 공유를 켜는 것 자체는 한 줄짜리 토글이지만, 한 번 켜면 어느 계정의 사용량이 어느 계정의 RI를 잡아먹었는지 추적이 까다로워진다. 일부 회사는 정산 공평성을 이유로 일부 계정만 공유에서 빼는데, 그 경우 콘솔에서 계정별로 opt-out을 해줘야 한다.

### Credit과 Refund

AWS 크레딧은 기본적으로 Management Account에 들어오고, 적용 우선순위가 있다. 별도 설정 없이 두면 한 계정의 크레딧이 다른 계정 청구에 흘러 들어가서 정산이 꼬인다. 크레딧 공유 옵션도 결제 설정에서 끌 수 있다.

## 정책의 종류와 차이

Organizations에 부착할 수 있는 정책은 네 종류가 있다. 같은 메커니즘(트리 상속)을 쓰지만 작동 시점과 영향 범위가 다르다.

### Service Control Policy (SCP)

API 호출 시점에 평가되는 **권한 경계**다. IAM 평가 흐름에서 SCP가 먼저 검증되고, 그다음 IAM Policy/Resource Policy가 검증된다. SCP에서 막히면 그 계정에서는 누구도(IAM 사용자·역할·root 모두) 그 작업을 할 수 없다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyOutsideApprovedRegions",
    "Effect": "Deny",
    "NotAction": [
      "iam:*", "organizations:*", "route53:*",
      "cloudfront:*", "support:*", "sts:*"
    ],
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": ["ap-northeast-2", "us-west-2"]
      }
    }
  }]
}
```

글로벌 서비스는 리전이 없어서 `NotAction`으로 빼주지 않으면 IAM 콘솔조차 안 열린다. SCP 만들 때 처음 만나는 함정이다.

### Tag Policy

태그의 표기 규칙을 강제한다. 정확히는 **신고하는 정책**이라 SCP처럼 차단하지는 않는다. 대신 콘솔의 Tag Editor에서 정책 위반 리소스를 보여주고, "compliant" 여부를 추적할 수 있다.

```json
{
  "tags": {
    "CostCenter": {
      "tag_key": { "@@assign": "CostCenter" },
      "tag_value": { "@@assign": ["CC-1001", "CC-1002", "CC-1003"] },
      "enforced_for": { "@@assign": ["ec2:instance", "rds:db"] }
    }
  }
}
```

`enforced_for`에 들어간 리소스 타입은 태그 키 대소문자나 값이 다르면 생성·수정 자체가 막힌다. 들어가지 않은 리소스 타입은 컴플라이언스 신고만 된다. 태그 표기를 강제하고 싶으면 `enforced_for`에 모든 대상 리소스 타입을 명시적으로 넣어야 한다.

태그 기반 비용 분석을 하려면 Tag Policy로 "필수 태그가 빠진 리소스를 만들지 못하게" 하고 SCP로 "특정 태그 없이 EC2 RunInstances 차단" 같은 식으로 보강한다. 둘 중 하나만으로는 부족하다.

### Backup Policy

AWS Backup의 Backup Plan을 조직 단위로 강제한다. 각 계정에서 같은 이름의 Backup Plan을 만들 필요 없이, 부모 OU에서 한 번 정의하면 자식 계정에 자동 배포된다.

```json
{
  "plans": {
    "OrgDailyBackup": {
      "regions": { "@@assign": ["ap-northeast-2"] },
      "rules": {
        "Daily": {
          "schedule_expression": { "@@assign": "cron(0 5 ? * * *)" },
          "target_backup_vault_name": { "@@assign": "Default" },
          "lifecycle": {
            "delete_after_days": { "@@assign": "35" }
          }
        }
      },
      "selections": {
        "tags": {
          "RequireBackup": {
            "iam_role_arn": { "@@assign": "arn:aws:iam::$account:role/AWSBackupDefaultRole" },
            "tag_key": { "@@assign": "Backup" },
            "tag_value": { "@@assign": ["true"] }
          }
        }
      }
    }
  }
}
```

`$account` 같은 변수가 들어가서 계정마다 다른 IAM Role ARN을 알아서 채워준다. SCP가 "막는" 정책이면 Backup Policy는 "강제로 만드는" 정책이라는 점이 다르다.

### AI Services Opt-out Policy

Bedrock·CodeWhisperer·Comprehend 같은 AI 서비스에 보내진 데이터를 AWS가 모델 개선에 쓰는 것을 끄는 정책이다. 단순한 토글에 가까워서 보통 Root에 한 번 붙이고 끝낸다.

### 네 정책의 동시 사용

같은 OU에 SCP·Tag·Backup을 동시에 붙이는 게 흔한 형태다. 평가 시점이 다르기 때문에 충돌하지 않는다.

| 정책 | 평가 시점 | 효과 |
|---|---|---|
| SCP | API 호출 직전 | 호출 자체를 차단 |
| Tag Policy | 태그가 붙는 작업의 입력 검증 | 잘못된 태그 차단·신고 |
| Backup Policy | 정책 부착 시 비동기 적용 | Backup Plan 자동 생성 |
| AI Opt-out | AWS 측 데이터 사용 결정 | AI 학습 사용 차단 |

## SCP 상속 동작 보강

SCP 상속은 IAM과 다른 모델이라 처음 다루면 헷갈린다. 한 계정에 적용되는 "최종 SCP"는 Root부터 그 계정 자신까지 경로상 모든 노드의 SCP를 **AND**로 묶은 결과다.

### 평가 규칙

부모와 자식 SCP는 합집합이 아니라 교집합처럼 작동한다. 다음 두 규칙이 핵심이다.

1. **Allow는 모든 경로 노드에서 명시적으로 허용되어야 한다.** 부모에서 Allow가 빠지면 자식에서 아무리 Allow해도 차단된다.
2. **Deny는 한 노드에서만 나와도 즉시 차단된다.** 자식 SCP에서 Allow를 줘도 부모의 Deny를 못 이긴다.

```
Root (FullAWSAccess)
└── Workloads OU (DenyOutsideRegions)
    └── Prod OU (DenyEC2Terminate without MFA)
        └── Service-A-Prod 계정
```

Service-A-Prod에서 ec2:TerminateInstances를 호출할 때 평가는 다음과 같다.

- Root의 FullAWSAccess: Allow `*`
- Workloads OU의 DenyOutsideRegions: 리전이 허용 목록 안이면 통과
- Prod OU의 Deny: MFA 없으면 차단

이 중 하나라도 차단이면 작업이 막힌다. 모든 노드에서 Allow가 떨어져야 작업이 통과한다.

### FullAWSAccess가 자동으로 붙는 이유

Organizations를 처음 만들면 Root와 모든 OU에 `FullAWSAccess`라는 SCP가 자동으로 붙는다. 이걸 떼는 순간 그 노드 아래 모든 계정에서 모든 API가 차단된다. 자식 노드의 SCP는 "이 작업은 허용한다"가 아니라 "허용 가능 후보"로만 작동하기 때문이다. Allow는 부모에서부터 끊기지 않고 흘러내려와야 한다.

이 동작 때문에 SCP에는 두 가지 운영 모델이 있다.

**Deny List 모델 (대부분의 회사가 쓰는 방식):**
FullAWSAccess는 그대로 두고, 차단할 작업만 Deny SCP로 추가한다. 새 서비스가 출시돼도 자동으로 사용 가능 상태로 들어온다.

**Allow List 모델:**
FullAWSAccess를 떼고, 허용할 서비스만 Allow SCP로 명시한다. 보안 수준은 높지만 새 서비스가 나올 때마다 SCP를 고쳐야 한다. 금융권 일부에서 쓰는 정도다.

### 상속에서 자주 나오는 사고

```
Workloads OU에 SCP 부착:
{
  "Effect": "Allow",
  "Action": "ec2:*",
  "Resource": "*"
}
```

이렇게 만들면 "EC2를 허용한다"는 의도지만 실제로는 **EC2를 제외한 모든 작업이 차단된다**. Allow SCP는 "이것만 허용 후보"라는 의미라서, S3·RDS 같은 다른 서비스의 Allow가 사라진다. Deny가 아닌 Allow를 쓸 때는 항상 FullAWSAccess와 함께 사용해야 한다.

또 한 가지 흔한 실수는 **Management Account에 SCP를 붙이는 것**이다. SCP는 Management Account에 적용되지 않는다는 사실이 문서에는 분명히 적혀 있는데, 콘솔에서 부착은 되어 보여서 "왜 안 막히지?"를 한참 디버깅하게 된다. 의도적으로 그런 설계다. SCP가 잘못돼서 조직 전체가 잠겼을 때 Management Account에서 풀어줄 수 있어야 하기 때문이다.

## 멀티 계정 환경의 root 계정 보호

각 AWS 계정에는 root 사용자가 있다. IAM과 별개로 존재하고, 계정 수준의 최종 권한이 여기에 있다. SCP도 root는 막을 수 있다(Management Account의 root만 예외). 멀티 계정 운영에서 root 보호는 단일 계정 시절보다 훨씬 더 중요해진다. 계정이 50개라면 root도 50개라는 뜻이기 때문이다.

### 계정 생성 직후 처리해야 할 root 정리

새 Member Account를 만들면 그 계정의 root는 **생성 시 입력한 이메일과 임시 비밀번호**로 접근 가능한 상태다. Organizations API로 만들면 임시 비밀번호가 따로 없지만, 이메일로 비밀번호 재설정을 하면 그 시점에 root에 들어갈 수 있다. 이 root를 그대로 두면 안 된다. 다음 작업이 표준이다.

- root 이메일을 사람이 아닌 그룹 메일로 등록 (DL: aws-root+account@example.com 형태)
- root 비밀번호를 충분히 긴 무작위 값으로 재설정 후 봉인 보관 (1Password Vault 분리, 또는 AWS Secrets Manager에 별도 저장)
- root에 가상 MFA 디바이스 등록. 2024년 11월부터 root에 패스키(FIDO2) 등록이 가능해서 패스키를 쓰는 게 운영상 더 쉽다.
- 액세스 키가 있으면 즉시 삭제. root 액세스 키는 어떤 정당한 사유도 없다.

### root만 할 수 있는 작업

이 작업들은 IAM에서도, SCP에서도 우회할 수 없다. 미리 알아두지 않으면 사고 나기 좋은 부분이다.

- 계정 닫기(Close Account)
- 결제 정보·세금 정보 변경
- AWS Support 플랜 변경
- 일부 S3 버킷 정책 복구(Bucket Owner가 자기 자신을 락아웃했을 때)
- 일부 SQS·SNS 정책 복구

### IAM Identity Center로 일상 사용 차단

위의 root만 할 수 있는 작업을 제외하면, 일상적으로 root를 쓸 일이 없어야 한다. IAM Identity Center(구 AWS SSO)에 모든 인간 사용자를 묶고, 각 계정에는 Permission Set을 배포하는 형태가 표준이다. 이렇게 하면 각 Member Account에 IAM 사용자가 0명이 되고, root만 남는다. root는 봉인된 상태이므로 사실상 인간이 들어갈 수 있는 통로가 모두 통제된다.

### Centralized Root Access (2024년 말 추가 기능)

비교적 최근에 들어온 기능인데, Member Account의 root 자격 증명 자체를 Management Account에서 일괄로 무력화할 수 있다. Trusted Access를 IAM에 활성화하고, Organizations에서 Root Credentials Management를 켜면 Member Account의 root 비밀번호·MFA·액세스 키가 모두 비어 있는 상태로 강제된다. root만 할 수 있는 작업이 필요한 순간에는 Management Account에서 임시 root 세션을 발급받는다.

이 기능을 켜면 Member Account의 root 봉인 작업을 안 해도 되어서 운영 부담이 크게 줄어든다. 다만 Management Account가 침해되면 모든 root에 닿을 수 있는 단일 실패점이 된다는 점은 유념해야 한다. Management Account의 root와 Identity Center 통합 모두 다중 인원 승인 절차로 묶어 두는 게 안전하다.

### Management Account 보호

Management Account는 SCP로 자기 자신을 막을 수 없는 유일한 계정이다. 보호 수단이 다른 계정과 다르다.

- 워크로드를 절대 두지 않는다. CloudTrail Organization Trail의 S3 버킷도 별도 LogArchive 계정에 둔다.
- root에 하드웨어 MFA(YubiKey 등) 또는 FIDO2 패스키를 등록하고 봉인.
- root 액세스 키 0개 유지.
- 평상시 작업은 Identity Center의 별도 권한 세트로만. 가능한 한 ReadOnly Permission Set을 기본값으로.
- CloudTrail로 Management Account의 모든 API 호출을 별도 알람.

## Trusted Access와 Delegated Administrator

Organizations와 통합되는 AWS 서비스(Config, GuardDuty, Security Hub, Macie, IAM Access Analyzer, AWS Backup, CloudFormation StackSets, IAM Identity Center 등)는 두 가지 통합 모드가 있다. 처음에는 비슷해 보이지만 실제 권한 모델이 다르다.

### Trusted Access

Organizations 트리를 읽고, 자식 계정에 Service-Linked Role을 만들 수 있는 권한을 그 서비스에게 주는 것이다. **활성화는 Management Account에서만 할 수 있다.** 그 서비스가 조직 전체를 다룰 수 있게 되는 시작점이다.

```bash
aws organizations enable-aws-service-access \
  --service-principal config.amazonaws.com
```

Trusted Access만 켜져 있는 상태에서는 그 서비스의 운영도 여전히 Management Account에서 해야 한다. Security Hub를 이대로 두면 Security 팀이 Management Account에 들어가야 하는데, 그건 운영상 위험하다.

### Delegated Administrator

Trusted Access를 켠 다음, **특정 Member Account를 그 서비스의 위임 관리자로 지정**한다. 이렇게 하면 해당 Member Account가 조직 전체에 대한 그 서비스의 운영 권한을 갖는다.

```bash
aws organizations register-delegated-administrator \
  --account-id 222222222222 \
  --service-principal securityhub.amazonaws.com
```

Security 계정을 GuardDuty·Security Hub·Macie의 위임 관리자로 지정하면, Management Account 들어갈 일이 거의 사라진다. 이게 멀티 계정 보안 운영의 표준 형태다. Network 계정을 Resource Access Manager나 IPAM의 위임 관리자로 두는 식으로 서비스마다 다른 계정에 위임할 수 있다.

서비스마다 위임 가능 계정 수가 다르다. Security Hub는 1개, GuardDuty도 1개, CloudFormation StackSets는 여러 개 가능하다. AWS 문서를 보고 그 서비스 모델을 따로 확인해야 한다.

```
Management Account
├── Trusted Access 활성화 (config, guardduty, securityhub, ...)
└── 위임:
    ├── Security 계정 ← guardduty, securityhub, macie, accessanalyzer
    ├── Network 계정 ← ram, ipam
    └── Audit 계정 ← config, cloudtrail
```

### 위임의 회수

Delegated Administrator를 풀면 그 계정의 그 서비스 통합 데이터가 일부 사라질 수 있다. GuardDuty의 경우 Member Account 연결이 끊기고 통합 발견 데이터가 위임 계정에서 안 보이게 된다. 단순한 권한 토글이 아니라 데이터 연결까지 끊어지므로, 위임 변경은 점검 시간을 잡고 해야 한다.

## AWS Control Tower와의 관계

Control Tower를 Organizations의 상위 호환쯤으로 오해하기 쉬운데, 실제로는 **Organizations + 사전 설정된 가드레일·계정 팩토리·Identity Center 통합**을 한 번에 깔아주는 도구다. 내부에서는 여전히 Organizations를 쓴다.

### Control Tower가 자동으로 만드는 것

처음 Control Tower 랜딩 존을 깔면 다음 리소스가 한꺼번에 생긴다.

- Organizations (Management Account에)
- 기본 OU 두 개: `Security`, `Sandbox`
- LogArchive 계정과 Audit 계정 (Security OU 안)
- 조직 CloudTrail Trail (LogArchive에 로그 저장)
- 조직 Config (Audit 계정으로 집계)
- 일련의 SCP (Control Tower가 "Preventive Guardrail"이라 부르는 것)
- AWS Config Rules (Detective Guardrail)
- IAM Identity Center (선택)
- Account Factory (Service Catalog 기반 계정 생성 워크플로)

### Organizations 직접 운영 vs Control Tower

선택은 보통 두 축으로 나뉜다.

**Control Tower를 쓰는 경우**

- 처음부터 표준 가드레일을 빠르게 깔고 싶을 때
- 계정 신청·생성 워크플로를 셀프서비스로 두고 싶을 때 (Account Factory)
- AWS 모범 형태의 LogArchive·Audit 분리를 빠르게 따라가고 싶을 때

**Organizations를 직접 운영하는 경우**

- 이미 OU·SCP·계정이 깊게 자리 잡혀 있을 때
- Terraform/CDK로 모든 SCP·OU를 코드로 관리하고 싶을 때
- Control Tower의 가드레일이 자사 컴플라이언스에 맞지 않을 때

Control Tower는 자기가 만들어 놓은 SCP를 사용자가 직접 수정하면 "Drift"라는 상태가 되어, 다음 업데이트 때 강제로 원래대로 되돌린다. 이 동작 때문에 Control Tower 위에서 SCP를 자유롭게 손대기는 어렵다. 직접 만든 SCP는 Control Tower가 안 건드리는 별도 OU를 만들어 거기에 부착하는 회피책이 흔하다.

이미 만들어져 있는 Organizations 위에 Control Tower를 얹는 것도 가능하다("Extend governance"). 다만 기존 Root 직접 부착 SCP가 있으면 그걸 OU로 옮기라고 요구한다.

### Account Factory와 Customizations for Control Tower (CfCT)

Account Factory는 새 계정을 만들 때 베이스라인(VPC, IAM Role, Identity Center 권한 세트 등)을 같이 깔아준다. CfCT는 그 베이스라인을 CloudFormation StackSets로 자유롭게 확장하는 프레임워크다. 신규 계정 생성을 자동화하려면 결국 CfCT 또는 비슷한 자체 파이프라인이 필요해진다.

## 흔히 마주치는 운영 이슈

### 계정 이동 시 정책 충돌

계정을 다른 OU로 옮기면 그 순간부터 새 OU의 SCP를 받는다. 이전 OU에서 허용되던 작업이 새 OU에서 차단되면 진행 중이던 자동화가 깨진다. 특히 야간 배치 잡이 도는 시간에 계정을 옮기면 다음 날 출근해서 Slack을 마주하게 된다.

### Service-Linked Role 차단

SCP에서 특정 IAM 작업을 차단하면 AWS 서비스가 자기 Service-Linked Role을 생성하려다 막힌다. 가령 Lambda에서 처음 VPC를 붙일 때 Lambda가 SLR을 만들려 하는데, 이게 SCP에 막혀서 함수가 안 뜨는 식이다. SCP를 짤 때는 Service-Linked Role 생성과 사용은 항상 예외로 빼는 게 안전하다.

```json
{
  "Effect": "Deny",
  "Action": "iam:*",
  "Resource": "*",
  "Condition": {
    "StringNotLike": {
      "aws:PrincipalArn": [
        "arn:aws:iam::*:role/aws-service-role/*"
      ]
    }
  }
}
```

### 결제 데이터 가시성

Member Account에서 자기 비용을 못 보게 하는 것은 Management Account의 결제 설정 한 군데에서 컨트롤된다. 보통 Member Account 사용자가 자기 비용을 보는 게 챠지백 운영에 도움이 되어서, 기본값(보임)을 그대로 두는 회사가 많다. 이걸 막으면 팀 단위 비용 책임 모델이 흐릿해진다.

### Organizations 탈퇴

Member Account가 조직에서 빠지려면 결제 정보·세금 정보·전화번호 등이 모두 채워져 있어야 한다. Account Factory로 만든 계정은 이 정보가 비어 있는 경우가 많아서 탈퇴 작업이 막힌다. 빠질 때 한꺼번에 채우려면 root에 들어가야 하는데, root가 봉인돼 있어서 다시 풀어야 한다. 계정 폐기 절차를 미리 정해두지 않으면 이 단계에서 시간을 많이 쓴다.

## 참고

- AWS Organizations 사용자 가이드: https://docs.aws.amazon.com/organizations/latest/userguide/
- Organizing Your AWS Environment Using Multiple Accounts (백서): https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/
- SCP 평가 로직: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- AWS Control Tower 사용자 가이드: https://docs.aws.amazon.com/controltower/latest/userguide/
- Centralized Root Access: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user-access-management.html
