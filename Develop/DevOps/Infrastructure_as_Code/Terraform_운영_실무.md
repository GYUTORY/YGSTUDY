---
title: Terraform 운영 실무
tags: [terraform, iac, infrastructure, State, module, Workspace]
updated: 2026-07-25
---

# Terraform 운영 실무
Terraform은 HashiCorp이 만든 IaC 도구다. HCL(HashiCorp Configuration Language)로 인프라를 선언하고, 실제 클라우드 리소스와 state 파일을 동기화해서 관리한다. 선언적으로 쓰지만, 내부적으로는 DAG를 그려서 리소스 생성 순서를 결정한다.

처음에 로컬에서 `terraform.tfstate`만 쓰다가 팀이 커지면 반드시 remote backend로 이전해야 한다. 로컬 state로 여러 명이 작업하면 충돌이 생기고, 누군가 파일을 덮어쓰면 리소스 추적이 깨진다.

---

## State 관리

### Remote Backend

State를 S3, GCS, Terraform Cloud 같은 원격 저장소에 보관한다. S3 + DynamoDB 조합이 AWS 환경에서 가장 많이 쓰인다.

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/vpc/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
```

DynamoDB 테이블은 `LockID`를 파티션 키로 가진 테이블이어야 한다. 이 테이블이 없으면 locking이 작동하지 않는다.

```bash
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### State Locking

`terraform apply`나 `terraform plan`을 실행하면 DynamoDB에 락을 건다. 다른 사람이 같은 state에 동시에 접근하면 아래 에러가 난다.

```
Error: Error locking state: Error acquiring the state lock:
  ConditionalCheckFailedException: The conditional request failed
Lock Info:
  ID:        f5b8d1c2-...
  Who:       user@hostname
  Operation: apply
```

락이 비정상적으로 남아있으면 `terraform force-unlock <LOCK_ID>`로 해제한다. 단, 진짜로 다른 사람이 작업 중인지 먼저 확인해야 한다. 잘못 풀면 두 사람이 동시에 apply 되는 상황이 생긴다.

### State 파일 직접 수정

`terraform.tfstate`를 텍스트 에디터로 직접 수정하면 안 된다. 수정이 필요한 경우 `terraform state mv`, `terraform state rm` 명령을 쓴다.

```bash
# 리소스 이름 바꾸기
terraform state mv aws_instance.old_name aws_instance.new_name

# state에서 리소스 제거 (실제 리소스는 삭제 안 됨)
terraform state rm aws_s3_bucket.legacy
```

---

## Module 구조 설계

### 기본 디렉토리 구조

모듈은 재사용 가능한 단위로 쪼갠다. 한 디렉토리 안에 모든 리소스를 때려넣으면 나중에 특정 환경에만 변경을 적용하기 어려워진다.

```
infra/
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── eks/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── rds/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── dev/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── terraform.tfvars
    └── prod/
        ├── main.tf
        ├── variables.tf
        └── terraform.tfvars
```

모듈 호출 시 버전을 고정해두지 않으면 나중에 모듈이 업데이트됐을 때 예상치 못한 변경이 적용된다.

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.1.2"  # 버전 고정 필수

  name = "my-vpc"
  cidr = "10.0.0.0/16"
}
```

### 모듈 설계 원칙

모듈이 너무 작으면 호출 코드만 늘어나고, 너무 크면 재사용하기 어렵다. 실무에서는 AWS의 논리적 그룹 단위(VPC, EKS 클러스터, RDS 인스턴스)로 나누는 경우가 많다.

모듈 내부에서 `count`나 `for_each`로 동적으로 리소스를 생성할 때, 나중에 리소스가 삭제되면 인덱스가 밀려서 의도치 않은 destroy가 발생하는 경우가 있다. `for_each`에 map을 쓰면 키 기반으로 관리되기 때문에 이 문제를 피할 수 있다.

```hcl
# count 방식 - 중간 항목 삭제 시 인덱스 재배치로 의도치 않은 destroy 발생 가능
resource "aws_subnet" "private" {
  count = length(var.private_subnets)
  cidr_block = var.private_subnets[count.index]
}

# for_each 방식 - 키 기반이라 다른 항목에 영향 없음
resource "aws_subnet" "private" {
  for_each   = var.private_subnets
  cidr_block = each.value
}
```

---

## Workspace vs 디렉토리 분리

### Workspace 방식

`terraform workspace`는 같은 코드베이스로 여러 환경을 관리할 때 쓴다. `terraform.workspace`로 현재 workspace 이름을 참조한다.

```bash
terraform workspace new dev
terraform workspace new prod
terraform workspace select prod
```

```hcl
locals {
  env = terraform.workspace

  instance_type = {
    dev  = "t3.micro"
    prod = "m5.large"
  }
}

resource "aws_instance" "app" {
  instance_type = local.instance_type[local.env]
}
```

workspace는 state 파일만 분리한다. 코드는 동일하게 쓰기 때문에, dev와 prod가 완전히 다른 구조를 가지면 workspace 방식이 맞지 않는다. 조건문이 코드 전체에 퍼지면 가독성이 급격히 나빠진다.

### 디렉토리 분리 방식

환경별로 디렉토리를 나누는 방식이 더 명확하다. 각 환경이 독립된 state를 가지고, 코드도 환경에 맞게 커스터마이징할 수 있다.

```
environments/
├── dev/
│   ├── main.tf       # 모듈 호출
│   ├── backend.tf    # dev용 backend 설정
│   └── terraform.tfvars
└── prod/
    ├── main.tf
    ├── backend.tf    # prod용 backend 설정
    └── terraform.tfvars
```

단점은 디렉토리마다 `terraform init`, `terraform apply`를 따로 실행해야 한다는 점이다. Terragrunt를 쓰면 이 반복을 줄일 수 있다.

두 방식을 비교하면, 환경 간 차이가 크고 독립적으로 배포해야 하는 경우에는 디렉토리 분리가 낫다. 환경 간 차이가 변수 몇 개 수준이면 workspace도 충분하다.

---

## import / taint / refresh 주의사항

### terraform import

이미 수동으로 만든 리소스를 Terraform 관리 대상으로 가져올 때 쓴다.

```bash
terraform import aws_instance.web i-1234567890abcdef0
```

import는 state에 리소스 정보만 추가한다. `.tf` 파일에 해당 리소스 블록을 직접 작성해야 한다. 작성하지 않으면 다음 plan에서 해당 리소스를 destroy하려 한다.

Terraform 1.5부터 `import` 블록을 HCL에 직접 쓸 수 있다.

```hcl
import {
  to = aws_instance.web
  id = "i-1234567890abcdef0"
}
```

import 후 `terraform plan`을 반드시 실행해서 diff가 없는지 확인한다. 속성 값이 실제 리소스와 다르게 작성돼 있으면 불필요한 변경이 발생한다.

### terraform taint (deprecated)

taint는 특정 리소스를 다음 apply 시 destroy 후 재생성하도록 표시하는 명령이었다. Terraform 0.15.2부터 deprecated됐고, 대신 `-replace` 옵션을 쓴다.

```bash
# 구 방식
terraform taint aws_instance.web

# 현재 방식
terraform apply -replace="aws_instance.web"
```

`-replace`는 plan 단계에서 어떤 리소스가 교체되는지 미리 볼 수 있어서 더 안전하다.

### terraform refresh

현재 실제 리소스 상태를 읽어서 state 파일을 업데이트한다. `terraform plan`과 `terraform apply` 실행 시 자동으로 수행되기 때문에 명시적으로 실행할 일은 많지 않다.

수동으로 변경된 리소스가 많은 환경에서 refresh를 실행하면 state가 실제 상태로 덮어써진다. 이 상태에서 plan을 보면 Terraform 코드와 실제 상태의 차이가 드러나는데, 여기서 바로 apply하면 수동 변경이 모두 Terraform 코드 기준으로 되돌아간다.

```bash
# -refresh-only로 state만 업데이트하고 변경은 하지 않음
terraform apply -refresh-only
```

---

## Plan 결과 해석 및 리뷰

### 기호 읽기

```
+ create         # 새 리소스 생성
- destroy        # 리소스 삭제
~ update in-place # 리소스 속성 변경 (재생성 없음)
-/+ destroy and then create replacement  # 재생성 필요
```

`-/+`가 가장 위험하다. 이 기호가 보이면 반드시 리소스가 삭제되고 새로 만들어진다. 데이터베이스, EKS 노드 그룹, EIP 같은 리소스는 재생성 시 데이터 손실이나 서비스 중단이 발생한다.

### Plan 파일 저장

CI/CD 파이프라인에서 plan과 apply를 분리할 때 plan 결과를 파일로 저장한다.

```bash
# plan 저장
terraform plan -out=tfplan

# 저장된 plan 적용 (plan 이후 변경이 없음을 보장)
terraform apply tfplan
```

plan 파일 없이 apply하면 apply 직전에 plan을 다시 실행하기 때문에, 그 사이에 다른 사람이 변경을 가했을 때 의도치 않은 결과가 생길 수 있다.

### 리뷰 포인트

plan 결과를 리뷰할 때 확인해야 하는 항목:

- `known after apply`로 표시된 값이 다른 리소스의 참조로 쓰이는 경우, 실제 값을 예측해서 문제가 없는지 판단해야 한다.
- `# forces replacement` 주석이 붙은 속성은 변경 시 리소스 재생성을 의미한다.
- `destroy` 숫자가 예상보다 많으면 모듈 이름이 바뀌었거나 `count`에서 `for_each`로 전환하면서 인덱스가 변경된 경우일 수 있다.

---

## 운영 중 리소스 변경 시 destroy/recreate 트랩

### `name` 속성 변경

AWS의 많은 리소스는 `name`이 immutable 속성이다. 이름을 바꾸면 기존 리소스를 삭제하고 새로 만든다.

```hcl
# 이름 변경 → -/+ destroy and then create replacement
resource "aws_security_group" "web" {
  name = "web-sg-v2"  # 기존 "web-sg"에서 변경
}
```

이름 변경이 필요한 경우 `create_before_destroy` lifecycle 설정으로 순서를 바꿀 수 있다.

```hcl
resource "aws_security_group" "web" {
  name = "web-sg-v2"

  lifecycle {
    create_before_destroy = true
  }
}
```

단, `create_before_destroy`가 항상 작동하는 건 아니다. 기존 리소스에 의존하는 다른 리소스가 있으면 의존성 그래프 때문에 순서를 바꾸기 어렵다.

### RDS 인스턴스 파라미터 변경

`db_subnet_group_name`, `engine`, `engine_version` 변경은 RDS 재생성을 트리거한다. `engine_version` 업그레이드는 콘솔에서 수동으로 한 다음 state에 반영하거나, `apply_method = "pending-reboot"` 파라미터 그룹 변경을 먼저 적용하는 순서로 진행해야 한다.

```hcl
resource "aws_db_parameter_group" "mysql" {
  parameter {
    name         = "slow_query_log"
    value        = "1"
    apply_method = "pending-reboot"  # 즉시 적용하지 않음
  }
}
```

### EKS 노드 그룹 변경

`instance_types`, `ami_type`, `disk_size` 변경은 노드 그룹을 재생성한다. 노드 그룹 재생성은 드레인과 재스케줄링 과정이 필요하기 때문에 운영 중에 갑자기 적용하면 안 된다.

```hcl
resource "aws_eks_node_group" "workers" {
  instance_types = ["m5.large"]

  lifecycle {
    # 특정 속성 변경 무시 (신중하게 사용)
    ignore_changes = [scaling_config]
  }
}
```

`ignore_changes`는 Terraform 외부에서 값이 변경되는 경우(예: Auto Scaling이 노드 수를 조정)에 쓴다. 무분별하게 쓰면 실제 코드와 state 차이를 놓치게 된다.

### 태그 변경

대부분의 AWS 리소스는 태그 변경 시 in-place update가 된다. 단, 태그가 리소스 이름이나 identifier로 쓰이는 경우(예: EKS 클러스터 태그, Karpenter 노드 선택기)는 변경 전에 영향 범위를 확인해야 한다.

### 운영 중 변경 전 확인 절차

운영 환경에서 apply 전에 반드시 확인해야 하는 것들:

1. plan에서 `-/+`가 있는 리소스를 전부 확인한다.
2. 재생성 대상 리소스에 연결된 의존성(보안 그룹, 서브넷 연결, IAM 역할)을 파악한다.
3. 데이터베이스나 스테이트풀 리소스는 스냅샷을 먼저 찍는다.
4. 변경 창(maintenance window)을 잡고 모니터링 준비 후 진행한다.

plan 결과를 팀원에게 리뷰받는 절차를 CI/CD에 넣으면 실수를 줄일 수 있다. Atlantis나 Terraform Cloud의 PR 연동 기능이 이 목적에 맞다.
