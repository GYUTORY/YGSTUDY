---
title: AWS IAM 권한 관리 심화
tags: [aws, security, iam, policy, abac, scp]
updated: 2026-05-01
---

# AWS IAM 권한 관리 심화

기본 개념(사용자/그룹/역할/정책)은 [IAM.md](IAM.md)에서 다룬다. 이 문서는 그 위에 얹히는 심화 주제를 다룬다. 실무에서 IAM이 진짜 골치 아파지는 지점은 정책 평가가 어떻게 돌아가는지 모른 채 `Allow`만 잔뜩 붙여놓는 단계를 지난 다음이다. 권한 위임을 시작하거나, 멀티 계정 구조로 넘어가거나, 외부 파트너와 IAM Role을 공유하기 시작하면 그때부터 평가 우선순위와 조건 키 동작을 정확히 알아야 한다.

---

## 1. 정책 평가 로직(Policy Evaluation Logic)

### 6단계 평가 흐름

AWS가 어떤 API 호출을 허용할지 결정할 때 단순히 "정책에 Allow가 있나?"만 보지 않는다. 요청 컨텍스트를 모아서 적용 가능한 모든 정책을 6단계로 평가한다.

1. **인증(Authentication)** - 누가 요청했는지(Principal) 확인
2. **요청 컨텍스트 수집** - Action, Resource, Condition에 사용될 키들 수집(IP, 시간, MFA, 태그 등)
3. **Organization SCP 평가** - 계정이 Organization에 속하면 SCP가 허용하는 범위 안인지 확인
4. **Resource-based Policy 평가** - 대상 리소스에 붙은 정책 확인(S3 버킷 정책, KMS 키 정책 등)
5. **Identity-based Policy + Permissions Boundary + Session Policy 평가** - 호출자의 정책 묶음 평가
6. **최종 결정** - 위 평가 결과를 합쳐 `Allow` / `Deny` 결정

### Explicit Deny > Allow > Default Deny

이 순서가 IAM의 가장 중요한 원칙이다. 어디든 `Deny`가 한 번이라도 매칭되면 그걸로 끝이다. 다른 정책에 `Allow`가 100개 있어도 무력하다.

```
Explicit Deny  →  거부 (다른 정책 무관)
Explicit Allow →  허용 (Deny가 없을 때만)
아무 매칭 없음   →  Default Deny (암묵적 거부)
```

5년차 정도 되면 이 우선순위 자체는 외우고 있는데, 실제 사고는 "Allow가 있는데 왜 안 돼?"가 아니라 "Deny가 어디에 박혀 있는지 모르겠다"에서 터진다. SCP에 박혀 있을 수도, Permissions Boundary에 박혀 있을 수도, KMS Key Policy에 박혀 있을 수도 있다. 평가 흐름을 정확히 따라가야 어디서 막혔는지 보인다.

### 충돌 시나리오 예제

같은 사용자에게 두 정책이 동시에 붙어 있다고 하자.

```json
// 정책 A - S3 전체 허용
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}

// 정책 B - 특정 버킷 삭제만 거부
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "s3:DeleteBucket",
      "Resource": "arn:aws:s3:::production-*"
    }
  ]
}
```

`s3:DeleteBucket` 호출이 `production-logs` 버킷에 들어오면 정책 B의 `Deny`가 매칭되어 거부된다. 정책 A의 `s3:*`는 무의미해진다. 운영 환경 보호 패턴으로 자주 쓰는 방식이다. Allow는 넓게 주고, 위험한 작업만 Deny로 못박는다.

---

## 2. Permissions Boundary와 Identity-based Policy

### 교집합 동작

Permissions Boundary는 IAM 사용자/역할에 "최대 권한 천장"을 씌우는 정책이다. 중요한 건 Identity-based Policy와 OR 결합이 아니라 AND 결합이라는 점이다. 둘 다 허용하는 액션만 실제로 허용된다.

```
실제 허용 권한 = Identity Policy ∩ Permissions Boundary
```

Identity Policy에 `s3:*`가 있어도 Boundary에 `s3:GetObject`만 있으면 GetObject만 가능하다. 반대로 Boundary에 `s3:*`가 있어도 Identity Policy에 `s3:GetObject`만 있으면 역시 GetObject만 가능하다.

### 권한 위임 시나리오

실무에서 Permissions Boundary가 빛을 발하는 건 "개발자에게 IAM 권한을 위임하되, 그들이 스스로에게 무한 권한을 주는 걸 막을 때"다.

```json
// 개발자에게 부여하는 Identity Policy
// IAM Role을 만들 수 있지만, 반드시 Boundary를 붙여야만 만들 수 있게 강제
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy"
      ],
      "Resource": "arn:aws:iam::123456789012:role/dev-*",
      "Condition": {
        "StringEquals": {
          "iam:PermissionsBoundary": "arn:aws:iam::123456789012:policy/DevTeamBoundary"
        }
      }
    }
  ]
}
```

`iam:PermissionsBoundary` 조건 키 덕분에 개발자가 새 Role을 만들 때 반드시 `DevTeamBoundary` 정책을 Boundary로 붙여야만 한다. 개발자가 만든 Role이 어떤 정책을 가지든 결국 Boundary 안에서만 동작하므로, 개발자가 자기 Role에 `*:*` Allow를 박아도 Boundary가 막아준다.

권한 에스컬레이션 방어 패턴인데, 이걸 안 걸어두면 개발자가 Lambda Role 만들면서 `AdministratorAccess`를 붙이는 사고가 자주 난다.

---

## 3. SCP, Permissions Boundary, Session Policy, Resource-based Policy

### 평가 순서와 역할

| 정책 종류 | 적용 대상 | 평가 시점 | 역할 |
|---------|---------|---------|------|
| SCP (Service Control Policy) | Organization 계정 전체 | 가장 먼저 | 계정 단위 최대 권한 |
| Resource-based Policy | 리소스 자체 | 별도로 | 리소스 접근 허용 |
| Identity-based Policy | IAM User/Role | 호출자 권한 | 호출자가 가진 권한 |
| Permissions Boundary | IAM User/Role | Identity Policy와 교집합 | 권한 천장 |
| Session Policy | STS AssumeRole 세션 | 세션 한정 | 세션 권한 축소 |

### 결합 동작

같은 계정 내에서 호출자가 자기 계정 리소스에 접근할 때, 최종 권한은 다음 교집합이다.

```
허용 = SCP ∩ Identity Policy ∩ Permissions Boundary ∩ Session Policy
```

Resource-based Policy는 별도 트랙으로 평가된다. Identity Policy나 Resource Policy 둘 중 하나만 허용해도 같은 계정에서는 통과한다(단, Cross-account는 다르다 - 7번 항목 참고).

### Session Policy 사용 사례

Session Policy는 `sts:AssumeRole` 호출 시 인라인으로 전달하는 정책이다. Role이 가진 권한을 일시적으로 축소할 때 쓴다.

```python
import boto3

sts = boto3.client('sts')

# Role에는 s3:* 권한이 있지만, 이번 세션은 GetObject만 쓰게 제한
session_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-bucket/*"
        }
    ]
}

response = sts.assume_role(
    RoleArn='arn:aws:iam::123456789012:role/DataProcessor',
    RoleSessionName='temp-read-session',
    Policy=json.dumps(session_policy)
)
```

권한이 큰 Role을 가진 워커 프로세스가 특정 작업만 수행하는 하위 작업을 호출할 때, Session Policy로 권한을 좁혀서 임시 자격증명을 발급한다. 자격증명이 유출돼도 피해 범위가 작아진다.

### SCP 함정

SCP는 "허용"이 아니라 "허용 가능한 범위"만 정의한다. SCP에 `s3:GetObject` Allow가 있다고 해서 사용자가 GetObject를 쓸 수 있는 게 아니다. Identity Policy에서 별도로 Allow해야 한다. SCP는 천장이지 바닥이 아니다.

`FullAWSAccess` SCP가 모든 OU의 기본값으로 붙어 있는 이유가 이거다. SCP가 없거나 Allow가 비면 그 계정의 모든 IAM은 무력화된다(Default Deny가 SCP 단계에서 발동).

---

## 4. ABAC (Attribute-Based Access Control)

### RBAC의 한계

전통적인 Role-Based Access Control은 사람이 늘어나고 프로젝트가 늘어날수록 Role이 폭발한다. `dev-projectA-readonly`, `dev-projectA-admin`, `dev-projectB-readonly`... 이렇게 N×M으로 불어난다.

ABAC는 태그를 기준으로 권한을 부여한다. 사람의 태그와 리소스의 태그가 매칭되면 접근 허용하는 방식이다. Role 하나로 N개 프로젝트를 커버할 수 있다.

### aws:PrincipalTag와 aws:ResourceTag

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances"
      ],
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Project": "${aws:PrincipalTag/Project}"
        }
      }
    }
  ]
}
```

이 정책이 붙은 Role을 가진 사용자가 `Project=alpha` 태그를 가지고 있고, EC2 인스턴스에 `Project=alpha` 태그가 붙어 있으면 Start/Stop이 허용된다. `Project=beta` 인스턴스에는 거부된다.

`${aws:PrincipalTag/Project}`는 정책 변수 문법이다. 평가 시점에 호출자의 태그 값으로 치환된다.

### ABAC 도입 시 주의할 점

- **태그 무결성**: 사용자가 자기 태그를 수정할 수 있으면 ABAC 자체가 무너진다. `iam:TagUser`, `iam:UntagUser`는 반드시 Deny하거나 특정 어드민에게만 허용해야 한다.
- **태그 누락 처리**: 태그가 없는 리소스는 `aws:ResourceTag/Project`가 존재하지 않아 조건이 매칭되지 않는다(StringEquals는 키 부재 시 false). 이 동작이 의도와 맞는지 확인해야 한다.
- **태그 강제**: 리소스 생성 시 특정 태그가 반드시 있어야 하는 정책을 별도로 거는 게 일반적이다.

```json
{
  "Effect": "Deny",
  "Action": "ec2:RunInstances",
  "Resource": "arn:aws:ec2:*:*:instance/*",
  "Condition": {
    "Null": {
      "aws:RequestTag/Project": "true"
    }
  }
}
```

`Project` 태그 없이는 인스턴스 생성 자체를 거부한다.

---

## 5. AssumeRole 체인과 ExternalId

### Role Chaining

한 Role을 Assume해서 받은 임시 자격증명으로 다른 Role을 또 Assume하는 게 Role Chaining이다. 가능은 한데 제약이 있다.

- 체인된 세션의 최대 지속 시간은 **1시간**으로 강제된다(원래 Role이 12시간 설정이어도)
- CloudTrail에서 추적할 때 한 단계 전 Role만 보이고 그 이전은 안 보일 수 있다

체인이 깊어지면 디버깅이 지옥이 된다. 가능하면 평탄하게 가야 한다.

### ExternalId - 혼동된 대리인 문제

외부 회사(예: 모니터링 SaaS)에 자기 AWS 계정을 들여다볼 권한을 줄 때 IAM Role을 Cross-account로 넘기는데, 여기서 "혼동된 대리인 문제(Confused Deputy)"가 발생한다.

문제 시나리오:

1. SaaS 회사 A는 자기 AWS 계정 하나로 여러 고객을 관리한다
2. 고객 B는 A의 AWS 계정 ID를 신뢰해서 Role의 `Principal`을 A로 설정한다
3. 고객 C도 동일하게 한다
4. A 직원이(또는 A 시스템 버그가) B의 RoleArn으로 AssumeRole 호출하면 그냥 통과된다 - C도 마찬가지

A는 B와 C를 구분하지 못한 채 권한을 사용하게 된다. 이게 혼동된 대리인이다.

해결책이 ExternalId다. 고객 B는 자기만 아는 ExternalId를 발급받아 SaaS A에 제공하고, AssumeRole 정책에 그걸 강제한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::AAAAAAAAAAAA:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "B-secret-uuid-xxxx"
        }
      }
    }
  ]
}
```

A가 B의 Role을 Assume할 때 반드시 B의 ExternalId를 보내야 한다. A 직원이 C의 RoleArn을 들고 와도 C의 ExternalId를 모르므로 실패한다.

ExternalId는 비밀이 아니라 식별자다. 추측 불가능하면 충분하다(UUID 정도면 OK).

### sts:SourceIdentity

AssumeRole 체인에서 누가 처음 요청했는지 추적하기 어려운 문제를 해결하기 위해 도입된 기능이다. AssumeRole 호출 시 `SourceIdentity`를 설정하면, 그 세션이 다른 Role을 Assume해도 `SourceIdentity`가 따라간다.

```json
// Role의 Trust Policy
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::123456789012:root" },
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {
      "sts:SourceIdentity": "alice@company.com"
    }
  }
}
```

CloudTrail의 `userIdentity.sessionContext.sourceIdentity` 필드로 추적된다. 한 번 설정되면 변경 불가능하므로 위/변조가 어렵다. SSO + AssumeRole 조합에서 누가 진짜 호출자인지 감사 추적할 때 거의 필수다.

---

## 6. 조건 키 심화

### aws:SourceVpce

VPC 엔드포인트를 통한 호출만 허용할 때 쓴다. S3 버킷을 사내 VPC에서만 접근하게 막는 패턴.

```json
{
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": [
    "arn:aws:s3:::internal-bucket",
    "arn:aws:s3:::internal-bucket/*"
  ],
  "Condition": {
    "StringNotEquals": {
      "aws:SourceVpce": "vpce-1a2b3c4d"
    }
  }
}
```

VPC 엔드포인트가 아닌 경로(인터넷, 다른 VPC)에서 들어오는 모든 요청을 차단한다. 버킷 정책에 거는 게 일반적이다.

### aws:PrincipalOrgID

Organization 안에서만 Cross-account 접근을 허용할 때 쓴다. 새 계정이 Organization에 추가될 때마다 정책을 고칠 필요가 없다.

```json
{
  "Effect": "Allow",
  "Principal": "*",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::shared-data/*",
  "Condition": {
    "StringEquals": {
      "aws:PrincipalOrgID": "o-abc123def4"
    }
  }
}
```

특정 계정 ID들을 일일이 나열하던 시절보다 훨씬 간결하다.

### aws:CalledVia

다른 AWS 서비스를 거쳐서 호출되는지 구분할 때 쓴다. CloudFormation이나 Lambda를 통한 간접 호출만 허용하고 싶을 때 유용하다.

```json
{
  "Effect": "Allow",
  "Action": "kms:Decrypt",
  "Resource": "*",
  "Condition": {
    "ForAnyValue:StringEquals": {
      "aws:CalledVia": ["lambda.amazonaws.com"]
    }
  }
}
```

Lambda 실행 컨텍스트 안에서만 KMS Decrypt 허용. 사용자가 직접 KMS를 호출하면 거부된다.

### IfExists 변형 (StringEqualsIfExists)

조건 키가 요청에 존재하지 않을 때 동작이 다르다.

- `StringEquals`: 키가 없으면 매칭 실패 → 조건 false → 정책 적용 안 됨
- `StringEqualsIfExists`: 키가 없으면 통과 → 조건 true 취급

전체 차단(Deny)을 만들 때 위험하다. 다음 예시를 보자.

```json
// 의도: 회사 IP에서 들어오는 요청은 허용
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*",
  "Condition": {
    "IpAddressIfExists": {
      "aws:SourceIp": "10.0.0.0/8"
    }
  }
}
```

`IfExists`라서 `aws:SourceIp` 조건 키가 없는 요청(예: VPC 내부 호출)도 통과한다. 의도가 "회사 IP가 아니면 거부"라면 이 정책은 잘못됐다. 반대로 "회사 IP인 경우만 체크하고 다른 경로는 신경 쓰지 않음"이 의도라면 맞다.

`IfExists`는 멀티 서비스 통합 정책에서 일부 서비스가 해당 조건 키를 안 보낼 때 유용하다. 예를 들어 MFA 조건을 거는데 STS는 MFA 컨텍스트를 보내고 어떤 서비스는 안 보낼 때, `BoolIfExists`로 묶으면 컨텍스트가 있을 때만 검증하고 없으면 통과시킨다.

---

## 7. Resource-based Policy vs Identity-based Policy

### 같은 계정 내에서

Identity Policy 또는 Resource Policy 중 하나라도 Allow하고 어디에도 Deny가 없으면 허용된다. OR 결합이다.

### Cross-account에서

여기서 동작이 완전히 달라진다. 둘 다 Allow가 있어야 한다. AND 결합이다.

```
계정 A의 사용자가 계정 B의 S3 버킷에 접근

필요 조건:
- 계정 A의 Identity Policy에 s3:GetObject Allow
- 계정 B의 S3 버킷 정책에 계정 A를 Allow하는 statement
```

5년차 개발자가 자주 헷갈리는 지점이다. "버킷 정책에 다 열어놨는데 왜 안 돼?" → 호출 측 IAM에 권한이 없기 때문. "IAM에 다 열어놨는데 왜 안 돼?" → 버킷 정책이 다른 계정을 막고 있기 때문.

KMS는 더 까다롭다. KMS Key Policy에 명시적으로 Allow가 없으면 같은 계정 IAM도 KMS를 못 쓴다. KMS는 기본적으로 Key Policy가 모든 권한의 진입점이다. Key Policy가 IAM에 위임하는 statement(`kms:ViaService` 등)가 있어야만 IAM Identity Policy가 의미가 있다.

```json
// KMS Key Policy - IAM에게 권한 위임 허용
{
  "Sid": "Enable IAM User Permissions",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::123456789012:root" },
  "Action": "kms:*",
  "Resource": "*"
}
```

이 statement가 없는 KMS 키는 IAM Identity Policy에서 `kms:Decrypt`를 허용해도 사용 못 한다. KMS 키 만든 사람이 이걸 빼먹고 다른 어드민에게 공유했다가 영원히 못 쓰게 만드는 사고가 있다(키 삭제 외에는 복구 불가).

---

## 8. Access Analyzer와 CloudTrail

### IAM Access Analyzer

외부 접근 가능한 리소스를 찾아내는 서비스다. S3, IAM Role, KMS Key, Lambda, SQS, Secrets Manager 같은 Resource-based Policy를 가진 리소스를 분석해서 "현재 Organization 외부 또는 계정 외부에서 접근 가능한가?"를 알려준다.

자주 발견되는 패턴:

- S3 버킷이 `Principal: "*"`로 열려 있는데 Condition으로 막혀 있지 않은 경우
- IAM Role의 Trust Policy가 너무 넓은 Principal을 가진 경우(`Principal: "*"` + Condition)
- KMS 키가 다른 계정을 신뢰하는데 추적되지 않은 경우

ExternalAccess findings는 진짜 위험할 수 있고, UnusedAccess findings(Access Analyzer Unused Access 분석기)는 미사용 권한을 찾아준다.

### CloudTrail로 미사용 권한 식별

Access Analyzer Unused Access 외에도 직접 CloudTrail 로그를 분석해서 정책 슬리밍이 가능하다.

```sql
-- Athena로 CloudTrail 로그 분석
SELECT eventName, COUNT(*) as cnt
FROM cloudtrail_logs
WHERE useridentity.sessioncontext.sessionissuer.username = 'DataProcessorRole'
  AND eventtime > CURRENT_TIMESTAMP - INTERVAL '90' DAY
GROUP BY eventName
ORDER BY cnt DESC;
```

90일간 한 번도 호출되지 않은 액션은 정책에서 빼도 안전하다(완전히 안전하진 않다 - 분기/연 단위 작업이 누락될 수 있으니 1년 단위로 보는 게 낫다).

`AccessAdvisor`(IAM 콘솔의 "Last accessed") 정보도 같은 목적으로 쓸 수 있다. 사용된 적 없는 서비스를 한눈에 보여준다. 다만 액션 단위가 아니라 서비스 단위라 정밀도는 낮다.

---

## 9. 트러블슈팅

### Implicit Deny 디버깅

"왜 안 되는지 모르겠다"가 IAM 디버깅의 99%다. 원인은 보통 다음 중 하나다.

1. **어디에도 Allow가 없음** (Default Deny) - 가장 흔함
2. **어딘가에 Explicit Deny가 있음** - SCP, Boundary, Resource Policy 어딘가
3. **조건이 매칭 안 됨** - IP, MFA, 시간, 태그 조건
4. **Resource-based Policy가 막고 있음** - Cross-account 케이스
5. **KMS Key Policy** - KMS 관련 작업의 단골

디버깅 순서:

```
1. CloudTrail에서 실패한 API 호출 찾기 (errorCode: AccessDenied)
2. errorMessage 정독 - 메시지에 "explicit deny in a service control policy" 같은 힌트가 있음
3. IAM Policy Simulator로 Identity Policy 단독 평가
4. SCP/Boundary 적용된 결과로 다시 시뮬레이션
5. Resource-based Policy 별도 확인
```

CloudTrail의 `errorMessage`는 의외로 친절하다. "User: arn:... is not authorized to perform: s3:GetObject on resource: arn:... because no resource-based policy allows the s3:GetObject action"처럼 어디서 막혔는지 적혀 있다.

### 정책 시뮬레이터 한계

IAM Policy Simulator는 편하지만 다음을 평가하지 않는다.

- **Resource-based Policy** - S3 버킷 정책, KMS Key Policy 등은 시뮬레이터에서 무시됨
- **SCP** - 시뮬레이터는 Identity Policy + Boundary까지만 봄
- **Session Policy** - 시뮬레이터에서 직접 평가 어려움
- **VPC Endpoint Policy** - 시뮬레이터 범위 밖

S3 Cross-account 접근이 실패할 때 시뮬레이터로는 "Allow"가 나오는데 실제로는 거부되는 일이 자주 있다. 시뮬레이터를 신뢰하지 말고 실제 API 호출로 검증해야 한다.

### NotAction과 NotResource 함정

`NotAction`은 "지정한 액션을 제외한 모든 액션"이다. 의도와 다르게 광범위한 권한을 주는 함정이 있다.

```json
// 의도: IAM 액션만 거부
// 실제: IAM을 제외한 모든 AWS 액션 허용 - s3:*, ec2:*, 다 허용됨
{
  "Effect": "Allow",
  "NotAction": "iam:*",
  "Resource": "*"
}
```

`NotAction` + `Allow` 조합은 거의 항상 잘못된 정책이다. 의도가 "IAM 외 모든 권한"이라면 의도대로지만, 보통 그런 의도는 없다. `NotAction` + `Deny`는 그나마 안전하다("이 액션 외에는 다 막아라"는 의미).

`NotResource`도 비슷하다. `NotResource: "arn:aws:s3:::my-bucket"`은 "내 버킷 빼고 다른 모든 리소스"이지, "내 버킷이 아니면 거부"가 아니다. 의도와 정반대로 동작하기 쉽다.

가능하면 `NotAction`/`NotResource`는 안 쓰는 게 좋다. 명시적인 `Action` 리스트가 길어도 안전하다.

### Wildcard 위험 케이스

`Resource: "*"`나 `Action: "*"`은 명백한 위험이지만, 더 미묘한 케이스가 있다.

**케이스 1**: `iam:PassRole`에 Resource Wildcard

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "*"
}
```

이게 붙은 사용자는 EC2 인스턴스를 만들면서 어떤 Role이든 붙일 수 있다. `AdministratorAccess` Role을 가진 EC2를 띄우고 거기 SSH로 들어가면 권한 에스컬레이션이 끝난다. `iam:PassRole`은 항상 특정 Role ARN으로 제한해야 한다.

**케이스 2**: `iam:CreateAccessKey`

```json
{
  "Effect": "Allow",
  "Action": "iam:CreateAccessKey",
  "Resource": "*"
}
```

다른 사용자(어드민 포함)의 Access Key를 만들 수 있다. Resource를 `arn:aws:iam::*:user/${aws:username}`으로 제한해서 자기 자신만 가능하게 해야 한다.

**케이스 3**: `lambda:UpdateFunctionCode`

람다 코드를 자유롭게 바꿀 수 있으면 그 람다의 Execution Role 권한을 그대로 쓸 수 있다. 람다가 Admin Role을 쓰고 있다면 그게 그대로 권한 에스컬레이션 경로가 된다.

권한 에스컬레이션 가능한 액션 조합은 IAM의 어두운 면이다. `iam:*`을 막아도 `iam:PassRole`이나 `lambda:UpdateFunctionCode` 같은 다른 서비스의 액션으로 우회 가능한 경로가 있다. 정책 검토 시 이런 패턴을 의식적으로 찾아야 한다.

---

## 마무리

권한 관리 심화의 핵심은 결국 평가 흐름을 정확히 따라가는 것이다. 어떤 정책이 어느 시점에 평가되고, 어떻게 결합되는지 모르면 디버깅이 추측 게임이 된다. SCP는 천장, Boundary는 천장, Identity Policy는 실제 권한, Resource Policy는 별도 트랙. 이 구조를 머릿속에 그려놓고 CloudTrail의 errorMessage를 읽으면 대부분의 IAM 문제는 풀린다.

위험한 액션(`iam:PassRole`, `iam:CreateAccessKey`, `lambda:UpdateFunctionCode`, `kms:*` 등)에 Wildcard를 쓰지 않는 것, ExternalId 같은 보호 장치를 빼먹지 않는 것, Permissions Boundary로 권한 위임 시 안전망을 까는 것 - 이 정도가 사고를 막는 기본 방어선이다.
