---
title: Terraform
tags: [terraform, iac, infrastructure-as-code, devops, aws, hcl]
updated: 2026-03-31
---

# Terraform

## Terraform이 뭔가

HashiCorp가 만든 Infrastructure as Code 도구다. HCL(HashiCorp Configuration Language)이라는 선언적 문법으로 인프라를 정의하고, `plan`으로 변경사항을 확인한 뒤 `apply`로 반영한다.

AWS 콘솔에서 클릭으로 인프라를 만들면 3가지 문제가 생긴다:

- 누가 언제 뭘 바꿨는지 추적이 안 된다
- 같은 환경을 다시 만들 수 없다
- 사람이 실수한다

Terraform은 이 문제를 코드로 풀었다. `.tf` 파일에 원하는 상태를 선언하면, Terraform이 현재 상태와 비교해서 차이만 반영한다.

### CloudFormation, Ansible과 뭐가 다른가

CloudFormation은 AWS 전용이다. AWS만 쓴다면 괜찮지만, GCP나 Azure 리소스가 하나라도 끼는 순간 별도 도구가 필요하다.

Ansible은 절차적(procedural) 도구다. "EC2를 3개 만들어라"라고 쓰면 실행할 때마다 3개씩 추가된다. Terraform은 선언적이라서 "EC2가 3개여야 한다"고 쓰면 현재 2개일 때 1개만 추가한다.

Pulumi는 Python/TypeScript 같은 범용 언어를 쓴다. 복잡한 조건 분기가 필요하면 Pulumi가 편하지만, HCL의 제약이 오히려 인프라 코드를 읽기 쉽게 만드는 경우가 많다.

## 핵심 개념

### Provider

Terraform과 클라우드 서비스를 연결하는 플러그인이다. AWS, GCP, Kubernetes, GitHub 등 3,000개 이상의 프로바이더가 있다.

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"

  default_tags {
    tags = {
      ManagedBy = "Terraform"
    }
  }
}
```

버전 제약 조건(`~> 5.0`)은 반드시 건다. 안 걸면 `terraform init` 할 때마다 최신 버전을 받는데, 메이저 버전이 바뀌면서 기존 리소스 정의가 깨지는 일이 생긴다. 실제로 AWS 프로바이더 4.x에서 5.x로 넘어갈 때 `aws_s3_bucket` 리소스의 하위 속성들이 별도 리소스로 분리되면서 대규모 마이그레이션이 필요했다.

### Resource와 Data Source

Resource는 Terraform이 생성하고 관리하는 인프라 구성요소다.

```hcl
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public.id

  tags = {
    Name = "web-server"
  }
}
```

`aws_subnet.public.id`처럼 다른 리소스를 참조하면 Terraform이 의존성을 자동으로 파악한다. VPC를 먼저 만들고, 서브넷을 만들고, 그 다음 EC2를 만드는 식이다. 의존성이 없는 리소스는 병렬로 생성한다.

Data Source는 이미 존재하는 리소스 정보를 읽어온다. 직접 만들지 않은 리소스를 참조할 때 쓴다.

```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}
```

### Variable과 Output

Variable은 외부에서 값을 주입받는 통로다.

```hcl
variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment는 dev, staging, prod 중 하나여야 한다."
  }
}

variable "db_password" {
  type      = string
  sensitive = true
}
```

값을 전달하는 방법은 4가지다:

```bash
# 1. tfvars 파일 (가장 많이 씀)
# dev.tfvars
# environment = "dev"
# instance_type = "t3.micro"
terraform apply -var-file="dev.tfvars"

# 2. 커맨드라인
terraform apply -var="environment=prod"

# 3. 환경 변수 (CI/CD에서 시크릿 전달할 때)
export TF_VAR_db_password="secret123"

# 4. terraform.tfvars 파일은 자동으로 읽힌다
```

Output은 생성된 리소스의 정보를 외부로 노출한다. 다른 Terraform 프로젝트에서 `terraform_remote_state`로 읽거나, CI/CD 파이프라인에서 `terraform output -json`으로 가져다 쓸 수 있다.

```hcl
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}
```

### Locals

반복되는 표현식을 변수처럼 정의하는 블록이다. Variable과 다른 점은 외부에서 값을 바꿀 수 없다는 것이다.

```hcl
locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags       = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}
```

## State 관리

### State가 뭔가

Terraform은 `.tfstate` 파일에 현재 인프라 상태를 JSON으로 저장한다. `plan`을 실행하면 이 파일과 실제 인프라를 비교해서 차이를 계산한다.

로컬에 `terraform.tfstate`를 두면 혼자 쓸 때는 괜찮지만, 팀에서 쓰는 순간 문제가 된다. 두 사람이 동시에 `apply`하면 state가 꼬인다.

### Remote Backend

팀에서는 반드시 remote backend를 써야 한다. S3 + DynamoDB 조합이 가장 보편적이다.

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "services/api/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

DynamoDB 테이블은 동시 `apply`를 막는 락(lock) 역할을 한다. 이걸 빼면 두 사람이 동시에 실행했을 때 state가 꼬여서 수동 복구해야 한다. 한 번 겪어보면 절대 빼지 않게 된다.

### Terraform Cloud vs S3 Backend

**S3 backend**는 직접 관리해야 한다. S3 버킷 생성, DynamoDB 테이블 생성, IAM 권한 설정을 모두 수동으로 한다. state 파일 자체를 Terraform으로 관리하려면 닭과 달걀 문제가 생기기 때문에, backend 인프라는 별도 스크립트나 CloudFormation으로 만드는 경우가 많다.

**Terraform Cloud(HCP Terraform)**는 state 저장, 락, 실행 환경을 모두 제공한다. 무료 플랜도 있어서 소규모 팀에서 빠르게 시작하기 좋다. 단점은 apply 실행이 HashiCorp 서버에서 일어나기 때문에, VPC 내부 리소스에 접근하려면 Terraform Cloud Agent를 별도로 운영해야 한다.

실무에서 판단 기준:

- 인프라가 AWS에 있고, 이미 S3/DynamoDB를 쓰고 있다면 S3 backend가 간단하다
- 팀 규모가 커서 정책 관리(Sentinel)나 비용 추정 기능이 필요하면 Terraform Cloud
- 보안 정책상 state 파일이 외부에 나가면 안 되면 S3 backend

### State 분리

프로젝트가 커지면 하나의 state 파일이 거대해진다. 리소스가 500개를 넘으면 `plan`에 30초 이상 걸리기 시작하고, 1,000개를 넘으면 1분이 넘는 경우도 있다.

state를 분리하는 기준은 보통 이렇다:

- **변경 빈도**: 네트워크(VPC, 서브넷)는 거의 안 바뀌고, 애플리케이션 인프라(ECS, Lambda)는 자주 바뀐다. 같이 두면 네트워크 건드릴 때 앱 인프라까지 plan 대상이 된다.
- **팀 경계**: 플랫폼팀이 관리하는 공유 인프라와 서비스팀이 관리하는 앱 인프라를 분리한다.
- **blast radius**: state 하나가 깨지면 그 안의 모든 리소스가 영향받는다. 분리하면 피해 범위가 줄어든다.

분리된 state 간에 데이터를 전달할 때는 `terraform_remote_state`를 쓴다:

```hcl
# 네트워크 프로젝트의 output
output "vpc_id" {
  value = aws_vpc.main.id
}

# 앱 프로젝트에서 참조
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "my-terraform-state"
    key    = "network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

resource "aws_ecs_service" "app" {
  network_configuration {
    subnets = data.terraform_remote_state.network.outputs.private_subnet_ids
  }
}
```

### State 조작

가끔 state를 직접 만져야 할 때가 있다. 리소스 이름을 바꾸거나, 수동으로 만든 리소스를 Terraform으로 가져올 때다.

```bash
# 리소스 이름 변경 (destroy + create 없이)
terraform state mv aws_instance.old aws_instance.new

# Terraform 관리에서 제외 (리소스는 삭제 안 됨)
terraform state rm aws_instance.web

# 수동으로 만든 리소스를 Terraform으로 가져오기
terraform import aws_instance.web i-1234567890abcdef0
```

Terraform 1.5부터 `import` 블록을 HCL로 선언할 수 있다. 코드로 남기 때문에 PR 리뷰도 가능하다:

```hcl
import {
  to = aws_instance.web
  id = "i-1234567890abcdef0"
}
```

`terraform state mv`는 refactoring할 때 많이 쓰는데, 실수하면 Terraform이 기존 리소스를 삭제하고 새로 만들려고 한다. **반드시 `plan`으로 확인한 뒤 진행한다.**

## 모듈

### 모듈이 필요한 이유

비슷한 리소스 조합을 여러 환경에서 반복할 때 모듈로 묶는다. VPC + 서브넷 + NAT 게이트웨이 같은 조합이 대표적이다.

```
modules/
  vpc/
    main.tf
    variables.tf
    outputs.tf
environments/
  dev/
    main.tf
  prod/
    main.tf
```

```hcl
# modules/vpc/main.tf
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true

  tags = {
    Name = "${var.name}-vpc"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]

  tags = {
    Name = "${var.name}-private-${count.index + 1}"
  }
}
```

```hcl
# environments/dev/main.tf
module "vpc" {
  source = "../../modules/vpc"

  name                 = "dev"
  cidr_block           = "10.0.0.0/16"
  private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
  azs                  = ["ap-northeast-2a", "ap-northeast-2c"]
}
```

### 모듈 작성 시 주의할 점

모듈은 작게 만든다. "VPC + 서브넷 + NAT + ECS + ALB + RDS"를 하나의 모듈에 넣으면 수정할 때 전체를 이해해야 한다. VPC 모듈, ECS 모듈, RDS 모듈로 나누는 게 낫다.

모듈에 하드코딩된 값을 넣지 않는다. 리전, 인스턴스 타입, CIDR 같은 건 변수로 뺀다.

Terraform Registry의 공식 모듈(`terraform-aws-modules/vpc/aws` 같은)은 잘 만들어져 있지만, 옵션이 너무 많다. 처음에는 직접 만드는 게 구조를 이해하기 좋고, 이후 공식 모듈로 마이그레이션해도 된다.

## 반복문과 조건문

### count vs for_each

`count`는 숫자로 반복한다. 리소스 목록이 변경될 때 인덱스가 밀리면서 의도치 않은 재생성이 일어나는 문제가 있다.

```hcl
# count 사용 - 중간 요소를 삭제하면 나머지가 밀린다
resource "aws_subnet" "public" {
  count      = length(var.subnet_cidrs)
  cidr_block = var.subnet_cidrs[count.index]
}
```

`subnet_cidrs`가 `["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]`인데 두 번째를 삭제하면, 세 번째가 인덱스 1로 밀리면서 `aws_subnet.public[1]`이 재생성된다. 프로덕션에서 서브넷이 재생성되면 그 안의 EC2도 날아간다.

`for_each`는 키 기반이라 이 문제가 없다:

```hcl
resource "aws_subnet" "public" {
  for_each   = toset(var.subnet_cidrs)
  cidr_block = each.value
}
```

경험상 `count`는 "동일한 리소스를 N개 만들 때"만 쓰고, 나머지는 전부 `for_each`를 쓴다.

### for 표현식

리스트나 맵을 변환할 때 쓴다:

```hcl
locals {
  # 리스트에서 맵으로 변환
  subnet_map = {
    for s in aws_subnet.private : s.availability_zone => s.id
  }

  # 조건부 필터링
  production_instances = [
    for i in aws_instance.all : i.id
    if i.tags["Environment"] == "prod"
  ]
}
```

### dynamic 블록

반복되는 중첩 블록을 동적으로 생성한다. Security Group의 ingress 규칙 같은 곳에서 쓴다:

```hcl
variable "ingress_rules" {
  type = list(object({
    port        = number
    cidr_blocks = list(string)
    description = string
  }))
}

resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = aws_vpc.main.id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = "tcp"
      cidr_blocks = ingress.value.cidr_blocks
      description = ingress.value.description
    }
  }
}
```

`dynamic` 블록을 남용하면 코드를 읽기 어려워진다. 규칙이 2~3개면 그냥 직접 쓰는 게 낫다.

## 멀티 계정, 멀티 리전

### Provider Alias

AWS 멀티 리전 구성에서 provider alias를 쓴다:

```hcl
provider "aws" {
  region = "ap-northeast-2"
}

provider "aws" {
  alias  = "virginia"
  region = "us-east-1"
}

# 서울 리전에 S3 버킷
resource "aws_s3_bucket" "main" {
  bucket = "my-app-data"
}

# 버지니아에 CloudFront용 ACM 인증서
resource "aws_acm_certificate" "cdn" {
  provider          = aws.virginia
  domain_name       = "example.com"
  validation_method = "DNS"
}
```

자주 겪는 삽질:

**모듈에서 provider를 전달하는 방식**이 직관적이지 않다. 모듈 내부에서 provider alias를 직접 정의하면 안 되고, 호출하는 쪽에서 주입해야 한다:

```hcl
# 잘못된 방법 - 모듈 내부에서 provider 정의
# module "cdn" {
#   source = "./modules/cdn"
# }
# modules/cdn/main.tf 안에서 provider "aws" { alias = "virginia" ... }
# -> 이렇게 하면 모듈을 재사용할 때 리전을 바꿀 수 없다

# 올바른 방법 - 호출하는 쪽에서 전달
module "cdn" {
  source = "./modules/cdn"

  providers = {
    aws.cert_region = aws.virginia
  }
}

# modules/cdn/main.tf
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.cert_region]
    }
  }
}

resource "aws_acm_certificate" "this" {
  provider    = aws.cert_region
  domain_name = var.domain_name
  # ...
}
```

### 멀티 계정 구성

AWS Organizations 환경에서 계정별 provider를 나눈다:

```hcl
provider "aws" {
  region = "ap-northeast-2"
  # 관리 계정
}

provider "aws" {
  alias  = "staging"
  region = "ap-northeast-2"

  assume_role {
    role_arn = "arn:aws:iam::111111111111:role/TerraformRole"
  }
}

provider "aws" {
  alias  = "production"
  region = "ap-northeast-2"

  assume_role {
    role_arn = "arn:aws:iam::222222222222:role/TerraformRole"
  }
}
```

계정이 3개 이상이면 provider 블록이 급격히 늘어난다. 이때는 Terragrunt를 도입하거나, 계정별로 Terraform 프로젝트를 완전히 분리하는 게 관리하기 편하다.

## terraform_data와 check 블록

### terraform_data (null_resource 대체)

Terraform 1.4에서 추가된 `terraform_data`는 `null_resource`를 대체한다. null_resource는 외부 프로바이더(`hashicorp/null`)가 필요했지만, terraform_data는 Terraform 내장이다.

```hcl
# 예전 방식 - null_resource
resource "null_resource" "deploy" {
  triggers = {
    image_tag = var.image_tag
  }

  provisioner "local-exec" {
    command = "kubectl set image deployment/app app=${var.image_tag}"
  }
}

# 새로운 방식 - terraform_data
resource "terraform_data" "deploy" {
  triggers_replace = [var.image_tag]

  provisioner "local-exec" {
    command = "kubectl set image deployment/app app=${var.image_tag}"
  }
}
```

차이점은 크지 않지만, `terraform_data`는 `input`과 `output` 속성을 지원한다. 값을 저장해두고 다른 리소스에서 참조할 때 유용하다:

```hcl
resource "terraform_data" "version" {
  input = var.app_version
}

resource "aws_instance" "web" {
  # terraform_data의 output을 참조
  user_data = "#!/bin/bash\necho ${terraform_data.version.output}"
}
```

### check 블록 (1.5+)

`check` 블록은 인프라가 apply된 후 상태를 검증한다. 실패해도 apply 자체는 성공하지만, warning을 출력한다.

```hcl
check "api_health" {
  data "http" "api" {
    url = "https://api.example.com/health"
  }

  assert {
    condition     = data.http.api.status_code == 200
    error_message = "API 헬스체크 실패: ${data.http.api.status_code}"
  }
}

check "certificate_expiry" {
  data "aws_acm_certificate" "main" {
    domain   = "example.com"
    statuses = ["ISSUED"]
  }

  assert {
    condition     = timecmp(
      data.aws_acm_certificate.main.not_after,
      timeadd(timestamp(), "720h")
    ) > 0
    error_message = "인증서가 30일 이내에 만료된다."
  }
}
```

`check` 블록은 모니터링 도구를 대체하는 게 아니다. "apply 직후 기본적인 검증"을 코드로 남겨두는 용도다. 인증서 만료, DNS 레코드 확인, 헬스체크 같은 걸 넣어두면 apply 할 때마다 자동으로 확인된다.

## 테스트

### terraform test (1.6+)

Terraform 1.6에서 추가된 내장 테스트 프레임워크다. `.tftest.hcl` 파일에 테스트를 작성한다.

```hcl
# tests/vpc.tftest.hcl
variables {
  environment = "test"
  cidr_block  = "10.0.0.0/16"
}

run "vpc_creation" {
  command = plan  # 실제 리소스를 만들지 않고 plan만 확인

  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "VPC CIDR이 예상값과 다르다."
  }

  assert {
    condition     = aws_vpc.main.tags["Environment"] == "test"
    error_message = "Environment 태그가 설정되지 않았다."
  }
}

run "subnet_count" {
  command = plan

  assert {
    condition     = length(aws_subnet.private) == 2
    error_message = "프라이빗 서브넷이 2개여야 한다."
  }
}
```

```bash
terraform test
```

`command = plan`이면 실제 인프라를 만들지 않는다. `command = apply`로 바꾸면 실제로 리소스를 만들고 테스트한 뒤 삭제한다. CI에서 돌릴 때는 별도 AWS 계정을 쓰는 게 안전하다.

### Terratest

Go로 작성하는 인프라 테스트 프레임워크다. terraform test보다 유연하지만, Go 코드를 작성해야 한다.

```go
// test/vpc_test.go
package test

import (
    "testing"

    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestVpcModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/vpc",
        Vars: map[string]interface{}{
            "name":       "test",
            "cidr_block": "10.0.0.0/16",
        },
    })

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    vpcId := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcId)
}
```

Terratest는 실제 인프라를 만들기 때문에 실행 시간이 길다(VPC 하나 만드는 데 2~3분). CI에서 PR마다 돌리기보다는 merge 후 또는 정기적으로 실행하는 게 현실적이다.

## CI/CD 파이프라인

### 기본 흐름

Terraform CI/CD의 핵심은 "PR에서 plan, merge 후 apply"다.

1. 개발자가 `.tf` 파일을 수정하고 PR을 올린다
2. CI가 `terraform plan`을 실행하고 결과를 PR 코멘트로 남긴다
3. 팀원이 plan 결과를 리뷰하고 승인한다
4. merge되면 `terraform apply`가 실행된다

### GitHub Actions 예시

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    paths:
      - 'infrastructure/**'
  push:
    branches:
      - main
    paths:
      - 'infrastructure/**'

permissions:
  contents: read
  pull-requests: write
  id-token: write

jobs:
  plan:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infrastructure
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ap-northeast-2

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.7.0

      - run: terraform init

      - id: plan
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      - uses: actions/github-script@v7
        with:
          script: |
            const output = `#### Terraform Plan
            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\`
            *Triggered by @${{ github.actor }}*`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });

      - if: steps.plan.outcome == 'failure'
        run: exit 1

  apply:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production  # GitHub Environment로 승인 흐름 추가
    defaults:
      run:
        working-directory: infrastructure
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ap-northeast-2

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.7.0

      - run: terraform init
      - run: terraform apply -auto-approve
```

`environment: production`을 설정하면 GitHub의 Environment Protection Rules로 승인 절차를 넣을 수 있다. apply 전에 지정된 사람이 승인해야 실행된다.

### GitLab CI 예시

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - plan
  - apply

variables:
  TF_ROOT: infrastructure

.terraform:
  image: hashicorp/terraform:1.7
  before_script:
    - cd $TF_ROOT
    - terraform init

validate:
  extends: .terraform
  stage: validate
  script:
    - terraform validate
    - terraform fmt -check

plan:
  extends: .terraform
  stage: plan
  script:
    - terraform plan -out=tfplan
  artifacts:
    paths:
      - $TF_ROOT/tfplan
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

apply:
  extends: .terraform
  stage: apply
  script:
    - terraform apply tfplan
  dependencies:
    - plan
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  when: manual  # 수동 승인 필요
```

### CI/CD 구성 시 주의사항

**plan과 apply 사이에 시간 차이가 있다.** PR 올린 시점의 plan 결과와, merge 후 apply 시점의 실제 인프라 상태가 다를 수 있다. 누군가 그 사이에 콘솔에서 직접 수정했거나, 다른 PR이 먼저 merge됐을 수 있다. apply 전에 다시 plan을 실행하거나, plan 파일(`tfplan`)을 artifact로 저장해서 그대로 apply하는 방식으로 대응한다.

**시크릿 관리**: AWS 자격 증명은 OIDC(OpenID Connect)로 받는 게 좋다. GitHub Actions의 `aws-actions/configure-aws-credentials`에 `role-to-assume`을 쓰면 장기 Access Key 없이 임시 자격 증명을 받을 수 있다. Access Key를 GitHub Secrets에 넣는 건 키 유출 위험이 있다.

**병렬 실행 방지**: 두 개의 CI 파이프라인이 동시에 `apply`하면 state 충돌이 난다. DynamoDB 락이 있으면 하나가 대기하지만, 타임아웃이 나는 경우도 있다. apply job은 동시 실행 수를 1로 제한하는 게 안전하다.

## 실전 디렉토리 구조

소규모 프로젝트에서는 flat한 구조로 시작해도 충분하다:

```
infrastructure/
  main.tf
  variables.tf
  outputs.tf
  terraform.tfvars
  versions.tf
```

환경이 나뉘면 디렉토리를 분리한다:

```
infrastructure/
  modules/
    vpc/
    ecs/
    rds/
  environments/
    dev/
      main.tf
      terraform.tfvars
      backend.tf
    staging/
    prod/
```

`environments/dev/main.tf`에서 `../../modules/vpc`를 호출하는 방식이다. 환경마다 다른 값은 `terraform.tfvars`에 넣는다.

프로젝트가 더 커지면 Terragrunt를 도입해서 환경별 반복 코드(backend 설정, provider 설정)를 줄이는 경우가 많다.

## 실무에서 자주 겪는 문제

### state lock이 안 풀릴 때

CI에서 apply 도중에 파이프라인이 강제 종료되면 DynamoDB 락이 남아있을 수 있다. 다음 apply가 계속 "Lock held by..."로 실패한다.

```bash
# 락 강제 해제
terraform force-unlock LOCK_ID
```

LOCK_ID는 에러 메시지에 나온다. **다른 사람이 정말로 apply 중인 게 아닌지 반드시 확인한다.**

### plan에서는 괜찮았는데 apply에서 실패

주로 두 가지 원인이다:

1. **권한 부족**: plan은 읽기 권한만으로 되지만, apply는 쓰기 권한이 필요하다. IAM 정책을 확인한다.
2. **리소스 제한**: AWS 서비스 쿼터에 걸리는 경우. EIP 5개 제한, VPC 5개 제한 같은 것들이 있다. AWS Support Console에서 쿼터를 올려야 한다.

### 수동 변경과의 충돌 (drift)

누군가 콘솔에서 직접 Security Group 규칙을 추가하면, 다음 `plan`에서 "삭제할 것"으로 나온다. Terraform은 자기가 모르는 변경을 되돌리려 한다.

대응 방법:
- `terraform import`로 수동 변경을 코드에 반영한다
- `lifecycle { ignore_changes = [security_groups] }`로 특정 속성의 변경을 무시한다 (임시 방편)

근본적으로는 콘솔 직접 수정을 금지하는 문화를 만들어야 한다. AWS Config이나 SCPs(Service Control Policies)로 수동 변경을 탐지하거나 차단하는 방법도 있다.

### lifecycle 설정

리소스의 생성/삭제 동작을 제어한다:

```hcl
resource "aws_instance" "web" {
  # ...

  lifecycle {
    # 새 리소스를 먼저 만들고 기존 것을 삭제 (다운타임 최소화)
    create_before_destroy = true

    # 특정 속성 변경 무시 (콘솔에서 변경될 수 있는 것)
    ignore_changes = [tags["UpdatedAt"]]

    # 삭제 방지 (실수로 destroy하는 것을 막음)
    prevent_destroy = true
  }
}
```

`prevent_destroy`는 프로덕션 DB 같은 곳에 건다. `terraform destroy`를 실행해도 에러가 나면서 삭제되지 않는다.

### moved 블록으로 리팩토링

Terraform 1.1에서 추가된 `moved` 블록은 `terraform state mv` 없이 리소스 이름을 바꿀 수 있게 한다:

```hcl
# 리소스 이름 변경
moved {
  from = aws_instance.web_server
  to   = aws_instance.web
}

# 모듈로 이동
moved {
  from = aws_instance.web
  to   = module.compute.aws_instance.web
}
```

`moved` 블록은 코드에 남기 때문에 팀원들에게 변경 의도가 전달된다. `state mv`는 실행한 사람만 알고, 다른 사람이 apply하면 에러가 나는 경우가 있다.

## 참고 자료

- [Terraform 공식 문서](https://developer.hashicorp.com/terraform/docs)
- [Terraform Registry](https://registry.terraform.io/) - 프로바이더와 모듈 검색
- [Terraform Best Practices (Anton Babenko)](https://www.terraform-best-practices.com/) - 실무 구조 참고
- [Terragrunt 문서](https://terragrunt.gruntwork.io/) - 대규모 Terraform 관리
