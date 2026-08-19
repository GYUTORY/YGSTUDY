---
title: AWS Control Tower
tags: [aws, cloud]
updated: 2026-07-25
---

# AWS Control Tower

## 개요

Control Tower는 다계정 AWS 환경을 처음부터 표준 형태로 깔아주는 서비스다. 내부적으로는 Organizations, IAM Identity Center, Config, CloudTrail, Service Catalog를 묶어서 동작한다. "Landing Zone"이라고 부르는 기준 환경을 만들어주고, 그 위에서 계정을 추가할 때 일관된 구성을 강제한다.

Organizations와의 차이를 한 줄로 요약하면, Organizations는 계정 트리와 정책 부착 메커니즘만 제공하고 Control Tower는 그 위에 "무엇을 어떻게 설정해야 하는가"까지 결정해서 자동화해준다. 처음부터 혼자 OU 설계, SCP 작성, LogArchive 계정 구성, Config 집계, CloudTrail Organization Trail 설정을 해본 사람은 Control Tower가 이 작업을 자동화한다는 점을 바로 알 수 있다.

단점도 명확하다. Control Tower가 만들어 놓은 리소스를 직접 수정하면 Control Tower가 인식하는 "올바른 상태"에서 벗어나는 Drift가 발생하고, 다음 업데이트나 Landing Zone 재설정 때 강제로 되돌린다. 자유도와 자동화 사이의 트레이드오프다.

## Organizations와의 관계

Control Tower를 Organizations의 상위 호환으로 오해하는 경우가 있는데, 실제로는 계층이 다르다.

```
Control Tower
└── Organizations (Control Tower가 내부에서 생성하고 관리)
    ├── Management Account (Landing Zone 설치 계정)
    ├── Security OU
    │   ├── Log Archive 계정
    │   └── Audit 계정
    └── Sandbox OU
        └── 실험 계정들
```

Control Tower는 Organizations를 생성한 뒤, 그 위에 자신만의 OU 구조, SCP, Config Rule, IAM Identity Center 설정을 올린다. Management Account가 Organizations의 Management Account이기도 하다. Control Tower를 삭제하면 Organizations는 남는다. 반대로 Organizations가 이미 있는 환경에 Control Tower를 나중에 올릴 수도 있는데, 이 경우 "Extend governance" 경로를 쓴다.

이미 Organizations를 Terraform으로 관리하고 있는 환경에 Control Tower를 올리면 충돌이 생긴다. Control Tower는 Root에 SCP를 붙이려 하는데, 기존 Terraform 코드가 이를 모르고 덮어쓰거나, Control Tower가 Terraform 상태 밖에서 만든 리소스 때문에 `terraform apply`가 충돌한다. 기존 Organizations 위에 올릴 때는 이 충돌을 먼저 정리해야 한다.

## Landing Zone

Landing Zone은 Control Tower가 설치될 때 만들어지는 기준 환경 전체를 가리킨다. 리소스 하나가 아니라, 아래 항목들의 집합이다.

**Control Tower가 Landing Zone 설치 시 자동으로 만드는 것:**

- Organizations (이미 있으면 재사용)
- Security OU, Sandbox OU 두 개의 기본 OU
- Log Archive 계정 (Security OU 안)
- Audit 계정 (Security OU 안)
- Organizations CloudTrail Trail → Log Archive 계정 S3에 저장
- Organizations Config → Audit 계정으로 집계
- Preventive Guardrail(SCP) 다수
- Detective Guardrail(Config Rule) 다수
- IAM Identity Center(선택 사항, 리전 제약 있음)
- Account Factory(Service Catalog 기반)

설치는 한 번이다. Landing Zone 버전은 주기적으로 업그레이드가 필요하다. 업그레이드를 미루면 Control Tower 콘솔에 "Update available" 배너가 뜨고, 오래 방치하면 일부 기능이 Drift 상태로 빠진다. 업그레이드는 실제 AWS 리소스를 수정하는 작업이라 운영 시간에 점검을 잡고 해야 한다. 업그레이드 중에 Account Factory로 새 계정을 만들거나 Guardrail을 바꾸는 작업은 하지 않는 게 안전하다.

### Landing Zone 설정 파라미터

설치 시 결정해야 할 주요 설정이 있다.

**홈 리전(Home Region):** Landing Zone의 주 리전. 나중에 바꿀 수 없다. IAM Identity Center는 홈 리전에만 설치된다. 한국 서비스라면 `ap-northeast-2`로 설정한다.

**Governed Regions:** Log Archive와 Config 수집 대상 리전. 여기에 들어간 리전에서 Config 레코더가 켜진다. 리전 수가 늘면 Config 비용이 선형으로 늘어나니, 실제 사용하는 리전만 넣어야 한다.

**Log Archive 보존 기간:** 기본값은 1년이다. 컴플라이언스 요구에 따라 늘릴 수 있다. 나중에 늘리는 건 되는데 줄이는 건 안 된다.

## Log Archive 계정과 Audit 계정

Control Tower가 Security OU 안에 자동으로 만드는 두 계정이 운영의 핵심이다.

### Log Archive 계정

Organizations CloudTrail Trail 로그, Config 스냅샷/히스토리, S3 액세스 로그가 여기 S3 버킷으로 집중된다.

이 계정의 S3 버킷은 Control Tower가 만들고 관리한다. 버킷 정책도 Control Tower가 설정한다. 직접 수정하면 Drift가 발생한다.

```
s3://aws-controltower-logs-{management-account-id}-{region}/
├── AWSLogs/{org-id}/CloudTrail/{region}/YYYY/MM/DD/*.gz
├── AWSLogs/{org-id}/Config/{region}/YYYY/MM/DD/*.gz
└── ...
```

이 계정에서 누군가 로그를 삭제하거나 버킷 정책을 바꾸는 것을 막아야 한다. Control Tower가 기본으로 Preventive Guardrail을 붙이는데, Log Archive 계정에서 S3 버킷 설정 변경, 로그 삭제, CloudTrail 비활성화를 차단한다. 그래서 보안 감사 때 "로그가 변조 불가 상태인가"를 물으면 이 Guardrail을 보여주면 된다.

문제는 Control Tower가 만든 버킷 이외에 직접 로그를 보내야 하는 경우다. ELB 액세스 로그, VPC Flow Log, WAF 로그는 각 계정에서 직접 S3 경로를 설정해야 한다. 이때 Log Archive 계정의 S3에 cross-account delivery를 구성하거나, 별도 S3 버킷에 보내고 Replication으로 Log Archive로 모으는 방식을 쓴다.

### Audit 계정

Organizations Config, Security Hub, GuardDuty 집계가 여기로 모인다. Control Tower는 이 계정을 Config, CloudTrail, Security Hub의 Delegated Administrator로 등록한다. Audit 계정에 접근할 수 있는 보안 팀이 전체 조직의 보안 상태를 이 한 계정에서 본다.

Audit 계정에는 SNS Topic이 있다. Control Tower의 Detective Guardrail이 위반을 탐지하면 이 SNS로 알림이 온다.

```
aws-controltower-SecurityNotifications (SNS Topic in Audit 계정)
  └── 구독: 보안 팀 이메일, PagerDuty, Slack 알림 Lambda 등
```

SNS를 이메일 구독으로만 두면 운영이 안 된다. 실제로는 Lambda를 연결해서 Slack 채널로 보내거나 PagerDuty 티켓을 여는 식으로 연결해야 Alert이 묻히지 않는다.

### 두 계정의 접근 제어

Log Archive와 Audit 계정에 일반 개발자가 들어가면 안 된다. IAM Identity Center에서 이 두 계정의 Permission Set을 별도로 제한하는데, 가장 단순한 방법은 SCP로 이 두 계정에 들어가는 인간 접근 자체를 줄이고, 필요한 보안 팀 역할만 Audit 계정에서 ReadOnly로 들어가게 하는 것이다.

## Account Factory

Control Tower에서 새 계정을 만드는 경로다. Service Catalog의 Product로 구현돼 있다. 콘솔에서 Account Factory에서 "Enroll account" 또는 "Create account"를 누르면 내부에서 Service Catalog Product를 실행한다.

### 계정 생성 시 자동으로 처리되는 것

- 지정한 OU 아래 계정 배치
- 베이스라인 VPC 생성(선택 사항, 기본값은 생성)
- IAM Identity Center에 계정 등록 및 Permission Set 배포
- CloudTrail, Config 자동 활성화
- Audit SNS 알림 설정
- AWSControlTowerExecution Role 생성(Management Account에서 해당 계정으로 들어오는 역할)

AWSControlTowerExecution Role은 Control Tower가 새 계정을 설정할 때 쓰는 역할이다. 계정 생성 후 초기 설정이 다 끝나도 이 역할이 남아 있다. 삭제하면 Control Tower가 그 계정에 대한 제어를 잃는다. 나중에 Landing Zone 업데이트 때 그 계정에서 작업을 못 한다.

### Account Factory Customization (AFC)

Account Factory 기본값으로는 VPC 외에 커스텀 리소스를 못 만든다. 실무에서는 계정마다 Security Group 규칙, IAM Role, S3 버킷, Config Rule 등을 같은 형태로 초기화해야 하는데, 이를 위한 경로가 두 개 있다.

**Customizations for Control Tower (CfCT):** CloudFormation StackSets로 커스터마이징을 배포하는 프레임워크다. `manifest.yaml`로 어떤 계정에 어떤 StackSet을 배포할지 선언한다. 새 계정이 생길 때 CodePipeline이 트리거되어 해당 StackSet을 자동 배포한다. AWS 공식 방식이다.

```yaml
# manifest.yaml (CfCT)
region: ap-northeast-2
version: 2021-03-15
resources:
  - name: SecurityGroupBaseline
    resource_file: templates/security-group-baseline.yaml
    deploy_method: stack_set
    deployment_targets:
      organizational_units:
        - Workloads
    regions:
      - ap-northeast-2
```

**Account Factory for Terraform (AFT):** Terraform을 쓰는 팀을 위한 경로다. AFT 자체가 Terraform 모듈로 제공되고, 계정 요청도 Terraform 코드로 작성한다. 계정 생성과 커스터마이징이 모두 Terraform State로 관리된다. Terraform을 이미 쓰는 팀이라면 CfCT보다 이 쪽이 훨씬 자연스럽다.

```hcl
# AFT 계정 요청 예시
module "account_request" {
  source = "./modules/aft-account-request"

  control_tower_parameters = {
    AccountEmail = "service-a-prod@example.com"
    AccountName  = "service-a-prod"
    ManagedOrganizationalUnit = "Workloads/Prod"
    SSOUserEmail = "admin@example.com"
    SSOUserFirstName = "Admin"
    SSOUserLastName  = "User"
  }

  account_tags = {
    Environment = "prod"
    Service     = "service-a"
  }

  account_customizations_name = "prod-baseline"
}
```

CfCT와 AFT 둘 다 계정 생성 후 커스터마이징 적용까지 30~45분 걸린다. Control Tower 자체의 계정 생성 단계(약 20분)에 커스터마이징 파이프라인 실행 시간이 더해진다.

## Guardrails

Control Tower의 정책 체계다. AWS가 사전에 정의해 놓은 규칙 묶음으로, 개별 SCP 작성 없이 콘솔에서 켜고 끄는 방식으로 적용한다.

### Preventive Guardrail

SCP로 구현된다. API 호출 시점에 차단한다. 한 번 켜면 해당 OU 아래 모든 계정에서 그 작업이 막힌다.

예시:

- "루트 사용자 액세스 키 생성 금지"
- "MFA 없이 루트 로그인 차단"
- "Log Archive 계정의 S3 버킷 설정 변경 금지"
- "CloudTrail 비활성화 금지"
- "Config 비활성화 금지"

Control Tower가 기본으로 켜는 Preventive Guardrail은 "Mandatory Guardrail"이라 부른다. 끌 수 없다.

"Elective Guardrail"은 선택이다. 콘솔에서 원하는 OU에 켤 수 있다.

```
Mandatory Preventive Guardrail(예):
- Disallow Changes to AWS Config Rules set up by AWS Control Tower
- Disallow Deletion of Log Archive
- Disallow Changes to Encryption Settings for AWS Control Tower Created S3 Buckets

Elective Preventive Guardrail(예):
- Disallow Creation of Access Keys for the Root User
- Require MFA for console access to AWS accounts
```

### Detective Guardrail

AWS Config Rule로 구현된다. 위반을 탐지해서 Audit 계정 SNS로 알린다. 작업을 막지는 않는다. 이미 만들어진 리소스의 상태를 검사한다.

예시:

- "MFA 없는 루트 계정 탐지"
- "퍼블릭 S3 버킷 탐지"
- "암호화 없는 EBS 볼륨 탐지"
- "VPC Flow Log 비활성화 탐지"

Detective Guardrail 위반은 Control Tower 콘솔의 "Noncompliant resources" 화면에서 볼 수 있다. AWS Config에서 직접 보는 것과 같은 데이터다.

### SCP와 Guardrails 차이

핵심 차이는 **누가 만들고 관리하는가**다.

| 구분 | SCP(직접 작성) | Preventive Guardrail |
|---|---|---|
| 생성 주체 | 운영자 | Control Tower |
| 수정 가능 여부 | 자유롭게 수정 | 수정 시 Drift 발생 |
| 내용 | 자유롭게 정의 | AWS가 사전 정의 |
| 적용 단위 | OU, 계정, Root | OU |

Control Tower가 만든 SCP를 직접 수정하면 Control Tower 콘솔에서 Drift가 보인다. Drift를 해소하려면 "Re-register OU" 또는 "Reset landing zone"으로 Control Tower가 원하는 상태로 되돌려야 한다.

Control Tower 환경에서 커스텀 SCP를 쓰려면 Control Tower가 관리하지 않는 별도 OU를 만들고 거기에 붙이거나, OU가 아닌 개별 계정 레벨에 붙이는 방식을 쓴다. Control Tower는 계정 레벨 SCP는 건드리지 않는다.

### Proactive Guardrail

2022년 말에 추가된 타입이다. AWS CloudFormation Guard를 사용해 CloudFormation 스택 배포 전에 검사한다. Preventive가 API 호출을 막고 Detective가 기존 상태를 검사한다면, Proactive는 CloudFormation 배포 단계에서 비준수 리소스를 사전 차단한다.

```
배포 흐름:
CloudFormation 스택 생성 요청
  └── Proactive Guardrail 검사
      ├── 통과 → 배포 진행
      └── 위반 → 스택 생성 실패
```

IaC로 인프라를 배포하는 팀에서 의도치 않은 비준수 리소스 배포를 막는 용도로 쓴다.

## Drift 관리

Control Tower를 운영하면서 가장 자주 마주치는 개념이다. Control Tower가 기대하는 상태에서 벗어나면 Drift다.

**Drift가 발생하는 주요 상황:**

- Control Tower가 만든 SCP를 수정하거나 삭제
- Log Archive, Audit 계정을 다른 OU로 이동
- Security OU를 삭제하거나 이름 변경
- AWSControlTowerExecution Role을 삭제
- Landing Zone에 등록된 계정을 Organizations에서 직접 이동

**Drift 확인:**

Control Tower 콘솔 > Account Factory > "Detect and resolve drift" 또는 Dashboard에서 Drift 상태 배너로 확인한다.

**Drift 해소:**

OU Drift는 "Re-register OU"로 해소한다. 계정 Drift는 "Re-register account"로 해소한다. Landing Zone 전체 Drift는 "Reset landing zone"으로 해소하는데, 이 경우 모든 Guardrail 설정이 Control Tower 기본값으로 돌아간다.

Drift가 쌓이면 Landing Zone 업그레이드가 안 되는 경우도 있다. 주기적으로 Drift 없는 상태를 유지하는 게 운영 부담을 줄인다.

## 실무에서 마주치는 문제들

### 베이스라인 VPC 충돌

Account Factory 기본 설정으로 계정을 만들면 각 리전에 VPC를 하나 만든다. 팀이 직접 Terraform으로 VPC를 관리하는 경우 이 기본 VPC가 충돌 지점이 된다.

해결 방법은 두 가지다. Account Factory 설정에서 "VPC configuration"을 "Internet-accessible subnets" 대신 "None"으로 바꿔서 VPC를 아예 안 만들게 하거나, 기본 VPC를 계정 초기화 시 AFT Customization에서 삭제한다.

### IAM Identity Center 리전 제약

Control Tower의 IAM Identity Center는 홈 리전에만 설치된다. 홈 리전을 `ap-northeast-2`로 설정했으면 IAM Identity Center도 `ap-northeast-2`에 있다. Identity Center는 글로벌 서비스가 아니라 단일 리전에 인스턴스가 하나 뜨는 구조다.

Permission Set의 배포는 리전 제약이 없다. 한국 리전의 Identity Center에서 만든 Permission Set이 미국 리전 계정에도 배포된다.

### Account Factory로 만든 계정의 탈퇴

Account Factory로 만든 계정을 조직에서 빼거나 폐쇄하려면 결제 정보가 채워져 있어야 한다. Account Factory로 만든 계정에는 이 정보가 비어 있어서 root 자격으로 들어가서 채워야 한다. AWSControlTowerExecution Role로는 루트만 할 수 있는 결제 정보 수정을 못 한다.

계정 폐쇄 절차를 미리 Runbook으로 만들어 두지 않으면 이 단계에서 시간을 많이 쓴다.

### Organizations와 Control Tower의 혼용

팀에서 Organizations를 Terraform으로 관리하는 동시에 Control Tower를 쓰면 충돌한다. Control Tower가 OU를 만들고, Terraform도 OU를 관리하려 하면 `terraform apply` 때 충돌이 발생한다.

현실적인 분리 방법은 Control Tower가 만든 OU(Security, Sandbox)는 Terraform State 밖에 두고, Workloads 아래의 추가 OU는 Control Tower가 아닌 Organizations API로 Terraform에서 관리하는 것이다. AFT를 쓰면 이 경계가 더 명확해진다.

### Guardrail 적용 지연

Guardrail을 OU에 활성화하면 즉시 모든 계정에 적용되지 않는다. Detective Guardrail(Config Rule)은 계정 수가 많을수록 배포까지 시간이 걸린다. 100개 계정이면 1~2시간 걸리는 경우도 있다. 활성화 직후 "적용 중" 상태가 Control Tower 콘솔에서 보인다.

Preventive Guardrail(SCP)은 상대적으로 빠르게 붙는다. SCP는 Organizations 레벨에서 직접 부착되기 때문이다.

## Control Tower를 쓸지 말지 결정하는 기준

처음 다계정 환경을 구성할 때 Control Tower가 주는 자동화가 크다. Landing Zone 설치 한 번으로 LogArchive/Audit 분리, CloudTrail Organization Trail, Config 집계가 다 된다. 이걸 직접 구성하면 설계와 구현에 상당한 시간이 든다.

기존에 Organizations가 이미 깊게 운영 중이라면 Control Tower를 올리는 작업 자체가 위험하다. 기존 SCP, OU 구조와 충돌할 수 있고, Extend governance 작업 중에 계정 접근이 일시 차단되는 사고가 나기도 한다. 이 경우는 Organizations 직접 운영을 유지하면서 Control Tower의 개념(LogArchive 계정, Audit 계정 구조, Preventive/Detective 분리)만 참고해서 직접 구성하는 쪽이 낫다.

## 참고

- AWS Control Tower 사용자 가이드: https://docs.aws.amazon.com/controltower/latest/userguide/
- Account Factory for Terraform (AFT): https://docs.aws.amazon.com/controltower/latest/userguide/aft-overview.html
- Customizations for Control Tower (CfCT): https://aws.amazon.com/solutions/implementations/customizations-for-aws-control-tower/
- Control Tower Guardrail 목록: https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html
