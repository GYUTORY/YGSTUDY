---
title: Terraform 인프라 자동화
tags: [terraform, iac, infrastructure-as-code, devops, aws, automation]
updated: 2025-11-01
---

# Terraform 인프라 자동화

## 📋 목차

1. [Terraform이란 무엇인가?](#terraform이란-무엇인가)
2. [핵심 개념](#핵심-개념)
3. [기본 문법과 구조](#기본-문법과-구조)
4. [상태 관리](#상태-관리)
5. [모듈 시스템](#모듈-시스템)
6. [실전 AWS 인프라 구축](#실전-aws-인프라-구축)
7. [고급 패턴](#고급-패턴)
8. [운영 및 협업](#운영-및-협업)
9. [참고 자료](#참고-자료)

---

## Terraform이란 무엇인가?

### Terraform의 정의

Terraform은 HashiCorp에서 개발한 **오픈소스 Infrastructure as Code(IaC) 도구**입니다. 인프라를 코드로 작성하여 버전 관리하고, 자동으로 생성, 변경, 삭제할 수 있습니다.

**핵심 특징:**
```
1. 선언적 문법 (Declarative)
   - 원하는 최종 상태를 정의
   - 어떻게(How)가 아닌 무엇을(What)

2. 멀티 클라우드 지원
   - AWS, Azure, GCP, DigitalOcean
   - Kubernetes, Docker, GitHub
   - 200+ 프로바이더

3. 실행 계획 (Plan)
   - 변경 사항을 미리 확인
   - 실수 방지

4. 리소스 그래프
   - 의존성 자동 파악
   - 병렬 처리

5. 상태 관리
   - 현재 인프라 상태 추적
   - 팀 협업 가능
```

### Terraform의 탄생 배경

**클라우드 시대의 문제점 (2014년 이전)**

```
수동 인프라 관리의 고통:
- AWS 콘솔 클릭 작업 (사람이 직접)
- 문서화 어려움 (어떻게 만들었는지 기억 안 남)
- 재현 불가능 (다른 환경에 똑같이 만들기 어려움)
- 팀 협업 어려움 (누가 뭘 만들었는지 모름)
- 휴먼 에러 빈번 (클릭 한 번 잘못하면 장애)

예시:
개발자: "프로덕션과 똑같은 스테이징 환경 만들어주세요"
인프라 담당자: "음... EC2가 몇 개였더라... VPC 설정이..."
→ 3일 소요, 설정 차이로 버그 발생
```

**기존 솔루션의 한계**

```
1. AWS CloudFormation
   ✓ AWS 전용 (다른 클라우드는?)
   ✗ JSON/YAML 복잡
   ✗ 상태 관리 제한적

2. Ansible
   ✓ 범용적
   ✗ 절차적 (순서 중요)
   ✗ 인프라보다 구성 관리에 적합

3. Chef/Puppet
   ✓ 강력한 구성 관리
   ✗ 러닝 커브 높음
   ✗ 인프라 생성보다 설정에 특화
```

**Terraform의 설계 철학 (2014년 출시)**

```
HashiCorp의 목표:
"간단하고, 멀티 클라우드이며, 선언적인 IaC 도구"

핵심 원칙:
1. 인프라를 코드로
2. 실행 전 확인 가능 (terraform plan)
3. 상태 파일로 현재 상태 추적
4. 모든 클라우드에서 동일한 경험
```

### 왜 Terraform을 사용하는가?

**1. 인프라 버전 관리**

```
Git으로 인프라 이력 관리:

before (수동):
"3개월 전에 누가 이 보안 그룹 규칙 바꿨지?"
→ 알 수 없음

after (Terraform):
git log infrastructure/security-groups.tf
→ 누가, 언제, 왜 변경했는지 명확
```

**2. 재현 가능한 환경**

```
똑같은 환경을 여러 개 만들기:

개발 환경:
terraform apply -var="env=dev"

스테이징 환경:
terraform apply -var="env=staging"

프로덕션 환경:
terraform apply -var="env=prod"

→ 설정 파일만 다르고 구조는 동일
```

**3. 협업과 리뷰**

```
Pull Request로 인프라 변경 리뷰:

변경 전:
"VPC 서브넷 추가하려고 합니다"
→ "아 실수로 잘못 클릭했네요" (이미 늦음)

변경 후:
1. terraform plan 결과를 PR에 첨부
2. 팀원들이 리뷰
3. 승인 후 terraform apply
→ 실수 방지, 지식 공유
```

**4. 비용 절감**

```
리소스 낭비 방지:

수동 관리:
"이 EC2 인스턴스 뭐하는 건지 모르겠는데 일단 놔둬야지..."
→ 매달 불필요한 비용 발생

Terraform:
terraform state list
→ 모든 리소스가 코드로 정의됨
→ 불필요한 것은 즉시 파악
```

### Terraform vs 다른 도구

| 특성 | Terraform | CloudFormation | Ansible | Pulumi |
|------|-----------|----------------|---------|--------|
| **언어** | HCL (선언적) | JSON/YAML | YAML (절차적) | 프로그래밍 언어 |
| **클라우드** | 멀티 클라우드 | AWS 전용 | 멀티 클라우드 | 멀티 클라우드 |
| **상태 관리** | 명시적 (tfstate) | AWS 관리 | 없음 (멱등성) | 명시적 |
| **실행 계획** | terraform plan | Change Set | 없음 | pulumi preview |
| **러닝 커브** | 낮음 | 중간 | 낮음 | 높음 |
| **커뮤니티** | 매우 큼 | AWS 생태계 | 큼 | 성장 중 |
| **용도** | 인프라 생성 | 인프라 생성 | 구성 관리 | 인프라 생성 |

**실무 선택 기준:**

```
Terraform 선택:
✓ 멀티 클라우드 (AWS + GCP 등)
✓ 팀 협업 중요
✓ 오픈소스 선호
✓ 러닝 커브 낮추고 싶음

CloudFormation 선택:
✓ AWS만 사용
✓ AWS 생태계 깊이 활용
✓ AWS 지원 중요

Ansible 선택:
✓ 서버 설정 관리 위주
✓ 배포 자동화
✓ 인프라보다 소프트웨어

Pulumi 선택:
✓ 프로그래밍 언어 사용하고 싶음
✓ 복잡한 로직 필요
```

---

## 핵심 개념

### 프로바이더 (Provider)

**프로바이더란?**

Terraform과 클라우드/서비스를 연결하는 플러그인입니다.

```hcl
# AWS 프로바이더
provider "aws" {
  region = "ap-northeast-2"  # 서울 리전
  
  default_tags {
    tags = {
      Environment = "Production"
      ManagedBy   = "Terraform"
    }
  }
}

# 여러 프로바이더 동시 사용 가능
provider "aws" {
  alias  = "us"
  region = "us-east-1"  # 버지니아 리전
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "github" {
  token = var.github_token
}
```

**주요 프로바이더:**

```
클라우드:
- AWS (aws)
- Azure (azurerm)
- GCP (google)
- DigitalOcean (digitalocean)

컨테이너/오케스트레이션:
- Kubernetes (kubernetes)
- Docker (docker)
- Helm (helm)

SaaS:
- GitHub (github)
- Datadog (datadog)
- PagerDuty (pagerduty)

데이터베이스:
- MySQL (mysql)
- PostgreSQL (postgresql)
- MongoDB Atlas (mongodbatlas)
```

### 리소스 (Resource)

**리소스란?**

생성하고 관리할 인프라 구성 요소입니다.

```hcl
# 기본 문법
resource "프로바이더_리소스타입" "이름" {
  속성1 = "값1"
  속성2 = "값2"
}

# 실제 예시: EC2 인스턴스
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  
  tags = {
    Name = "웹서버"
  }
}

# 실제 예시: VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "메인-VPC"
  }
}

# 실제 예시: S3 버킷
resource "aws_s3_bucket" "logs" {
  bucket = "my-app-logs-2024"
  
  tags = {
    Purpose = "로그 저장소"
  }
}
```

**리소스 참조:**

```hcl
# 다른 리소스의 속성 참조
resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id  # VPC 리소스의 ID 참조
  cidr_block = "10.0.1.0/24"
}

resource "aws_instance" "web" {
  subnet_id = aws_subnet.public.id  # 서브넷 리소스의 ID 참조
  # ...
}
```

**암묵적 의존성:**

```
Terraform이 자동으로 순서 파악:

1. aws_vpc.main 생성
2. aws_subnet.public 생성 (VPC 필요)
3. aws_instance.web 생성 (서브넷 필요)

→ 병렬 처리 가능한 것은 동시에 생성
```

### 데이터 소스 (Data Source)

**데이터 소스란?**

이미 존재하는 리소스의 정보를 가져옵니다.

```hcl
# 최신 Amazon Linux AMI 찾기
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# 사용
resource "aws_instance" "web" {
  ami = data.aws_ami.amazon_linux.id
  # ...
}

# 현재 AWS 계정 정보
data "aws_caller_identity" "current" {}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

# 기존 VPC 정보 가져오기
data "aws_vpc" "existing" {
  tags = {
    Name = "기존-VPC"
  }
}

resource "aws_subnet" "new" {
  vpc_id = data.aws_vpc.existing.id
  # ...
}
```

**리소스 vs 데이터 소스:**

```
리소스 (resource):
- 생성, 변경, 삭제
- Terraform이 관리
- 예: 새 EC2 인스턴스 생성

데이터 소스 (data):
- 읽기 전용
- 이미 존재하는 것
- 예: 기존 AMI ID 조회
```

### 변수 (Variable)

**변수란?**

재사용 가능하고 유연한 설정을 위한 입력 값입니다.

```hcl
# variables.tf
variable "region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "instance_type" {
  description = "EC2 인스턴스 타입"
  type        = string
  default     = "t3.micro"
}

variable "instance_count" {
  description = "인스턴스 개수"
  type        = number
  default     = 1
  
  validation {
    condition     = var.instance_count > 0 && var.instance_count <= 10
    error_message = "인스턴스는 1~10개 사이여야 합니다."
  }
}

variable "enable_monitoring" {
  description = "모니터링 활성화 여부"
  type        = bool
  default     = false
}

variable "availability_zones" {
  description = "가용 영역 리스트"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "tags" {
  description = "공통 태그"
  type        = map(string)
  default     = {
    Environment = "dev"
    Team        = "backend"
  }
}

# 민감한 정보
variable "db_password" {
  description = "데이터베이스 비밀번호"
  type        = string
  sensitive   = true  # 로그에 출력 안 됨
}
```

**변수 사용:**

```hcl
# main.tf
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type     # 변수 참조
  count         = var.instance_count
  
  tags = merge(var.tags, {
    Name = "web-${count.index + 1}"
  })
}
```

**변수 값 전달 방법:**

```bash
# 1. 커맨드라인
terraform apply -var="instance_count=3"

# 2. 변수 파일
# terraform.tfvars
instance_count = 3
instance_type  = "t3.small"

terraform apply

# 3. 환경별 변수 파일
terraform apply -var-file="production.tfvars"

# 4. 환경 변수
export TF_VAR_instance_count=3
terraform apply
```

### 출력 (Output)

**출력이란?**

Terraform 실행 후 필요한 정보를 표시합니다.

```hcl
# outputs.tf
output "vpc_id" {
  description = "생성된 VPC의 ID"
  value       = aws_vpc.main.id
}

output "public_ip" {
  description = "웹서버 공개 IP"
  value       = aws_instance.web.public_ip
}

output "database_endpoint" {
  description = "데이터베이스 엔드포인트"
  value       = aws_db_instance.main.endpoint
  sensitive   = true  # 민감 정보
}

output "instance_ips" {
  description = "모든 인스턴스 IP 목록"
  value       = aws_instance.web[*].private_ip
}
```

**출력 사용:**

```bash
# terraform apply 후 자동 표시
terraform apply

Outputs:
vpc_id = "vpc-12345678"
public_ip = "54.180.123.45"
instance_ips = ["10.0.1.10", "10.0.1.11"]

# 특정 출력만 조회
terraform output public_ip
54.180.123.45

# JSON 형식으로
terraform output -json

# 다른 Terraform 프로젝트에서 사용
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "terraform-state"
    key    = "network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.subnet_id
  # ...
}
```

### 로컬 값 (Locals)

**로컬 값이란?**

복잡한 표현식을 재사용하기 위한 임시 변수입니다.

```hcl
locals {
  # 공통 태그
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Owner       = "DevOps Team"
    CostCenter  = "Engineering"
  }
  
  # 이름 접두사
  name_prefix = "${var.project_name}-${var.environment}"
  
  # 조건부 값
  instance_type = var.environment == "production" ? "t3.medium" : "t3.micro"
  
  # 복잡한 계산
  subnet_count = length(var.availability_zones)
  
  # 리스트 생성
  subnet_cidrs = [
    for i in range(local.subnet_count) : 
    cidrsubnet(var.vpc_cidr, 8, i)
  ]
}

# 사용
resource "aws_instance" "web" {
  instance_type = local.instance_type
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-web"
  })
}
```

---

## 기본 문법과 구조

### HCL (HashiCorp Configuration Language)

**기본 블록 구조:**

```hcl
# 블록 타입   레이블1        레이블2
resource "aws_instance" "web" {
  # 속성
  ami           = "ami-12345678"
  instance_type = "t3.micro"
  
  # 중첩 블록
  tags {
    Name = "웹서버"
  }
}
```

**주석:**

```hcl
# 한 줄 주석

// 이것도 한 줄 주석

/*
여러 줄 주석
여러 줄 주석
*/
```

**문자열:**

```hcl
# 일반 문자열
name = "hello"

# 문자열 보간 (String Interpolation)
name = "${var.project_name}-server"

# 여러 줄 문자열
description = <<EOF
이것은
여러 줄
문자열입니다
EOF

# 템플릿
user_data = <<-EOT
  #!/bin/bash
  echo "Hello ${var.name}"
  echo "Environment: ${var.environment}"
EOT
```

**숫자와 불린:**

```hcl
instance_count = 3
port           = 8080
cpu_credits    = 0.5

enable_monitoring = true
is_production     = false
```

**리스트와 맵:**

```hcl
# 리스트 (List)
availability_zones = ["ap-northeast-2a", "ap-northeast-2c"]

# 인덱스 접근
first_az = var.availability_zones[0]

# 리스트 순회
resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  availability_zone = var.availability_zones[count.index]
  # ...
}

# 맵 (Map)
tags = {
  Environment = "production"
  Team        = "backend"
}

# 키 접근
env = var.tags["Environment"]
```

### 표현식과 함수

**조건 표현식:**

```hcl
# 삼항 연산자
instance_type = var.environment == "production" ? "t3.large" : "t3.micro"

# 복잡한 조건
alarm_enabled = (
  var.environment == "production" && 
  var.enable_monitoring
) ? true : false
```

**자주 사용하는 함수:**

```hcl
# 문자열 함수
upper("hello")           # "HELLO"
lower("HELLO")           # "hello"
title("hello world")     # "Hello World"
trimspace("  hello  ")   # "hello"
format("web-%03d", 1)    # "web-001"
join("-", ["a", "b"])    # "a-b"
split("-", "a-b-c")      # ["a", "b", "c"]

# 숫자 함수
min(1, 2, 3)            # 1
max(1, 2, 3)            # 3
ceil(5.1)               # 6
floor(5.9)              # 5
abs(-5)                 # 5

# 컬렉션 함수
length(["a", "b", "c"])             # 3
concat(["a"], ["b", "c"])           # ["a", "b", "c"]
contains(["a", "b"], "a")           # true
distinct(["a", "b", "a"])           # ["a", "b"]
flatten([["a"], ["b", "c"]])        # ["a", "b", "c"]
merge({a=1}, {b=2})                 # {a=1, b=2}

# CIDR 함수
cidrsubnet("10.0.0.0/16", 8, 0)    # "10.0.0.0/24"
cidrsubnet("10.0.0.0/16", 8, 1)    # "10.0.1.0/24"

# 파일 함수
file("${path.module}/script.sh")   # 파일 내용
fileexists("file.txt")              # true/false
templatefile("template.tpl", {     # 템플릿 파일
  name = "value"
})

# 날짜/시간
timestamp()              # "2024-01-15T10:30:00Z"
formatdate("YYYY-MM-DD", timestamp())  # "2024-01-15"
```

**for 표현식:**

```hcl
# 리스트 변환
upper_zones = [for az in var.availability_zones : upper(az)]

# 맵 생성
subnet_map = {
  for idx, cidr in var.subnet_cidrs :
  "subnet-${idx}" => cidr
}

# 필터링
prod_instances = [
  for inst in aws_instance.web :
  inst.id if inst.tags.Environment == "production"
]

# 조건부 for
instance_names = [
  for i in range(var.instance_count) :
  var.environment == "production" ? "prod-web-${i}" : "dev-web-${i}"
]
```

**splat 표현식:**

```hcl
# 모든 인스턴스의 ID
instance_ids = aws_instance.web[*].id

# 다음과 같음
instance_ids = [for inst in aws_instance.web : inst.id]

# 여러 속성
instance_info = [
  for inst in aws_instance.web : {
    id = inst.id
    ip = inst.private_ip
  }
]
```

### 프로젝트 구조

**기본 구조:**

```
terraform-project/
├── main.tf              # 메인 리소스 정의
├── variables.tf         # 변수 선언
├── outputs.tf          # 출력 정의
├── terraform.tfvars    # 변수 값 (git 제외)
├── versions.tf         # Terraform/프로바이더 버전
├── backend.tf          # 상태 파일 백엔드 설정
└── .gitignore          # Git 제외 파일
```

**환경별 분리:**

```
terraform/
├── modules/             # 재사용 가능한 모듈
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── ec2/
│   └── rds/
│
├── environments/        # 환경별 설정
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   │
│   ├── staging/
│   │   └── ...
│   │
│   └── production/
│       └── ...
│
└── global/             # 공통 리소스
    ├── s3/             # S3 버킷
    └── iam/            # IAM 역할/정책
```

**main.tf 예시:**

```hcl
# versions.tf
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# main.tf
provider "aws" {
  region = var.region
}

# VPC 모듈 사용
module "vpc" {
  source = "../../modules/vpc"
  
  name               = "${var.project_name}-${var.environment}"
  cidr_block         = var.vpc_cidr
  availability_zones = var.availability_zones
  
  tags = local.common_tags
}

# EC2 모듈 사용
module "ec2" {
  source = "../../modules/ec2"
  
  name          = "${var.project_name}-${var.environment}"
  instance_type = local.instance_type
  subnet_ids    = module.vpc.private_subnet_ids
  
  tags = local.common_tags
}
```

---

## 상태 관리

### 상태 파일이란?

**terraform.tfstate:**

Terraform이 관리하는 인프라의 현재 상태를 기록하는 JSON 파일입니다.

```json
{
  "version": 4,
  "terraform_version": "1.5.0",
  "serial": 1,
  "lineage": "abc-123-def",
  "resources": [
    {
      "mode": "managed",
      "type": "aws_instance",
      "name": "web",
      "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
      "instances": [
        {
          "attributes": {
            "id": "i-1234567890abcdef",
            "ami": "ami-12345678",
            "instance_type": "t3.micro",
            "public_ip": "54.180.123.45"
          }
        }
      ]
    }
  ]
}
```

**왜 상태 파일이 필요한가?**

```
문제:
코드만으로는 "실제 무엇이 생성되었는지" 알 수 없음

예시:
resource "aws_instance" "web" {
  ami = "ami-12345"
  # ...
}

→ 이 코드로 이미 EC2가 만들어졌을까?
→ 만들어졌다면 ID는?
→ 코드를 변경하면 새로 만들까, 수정할까?

상태 파일:
"i-1234567890" 인스턴스가 이미 있어요
→ 코드 변경 시 기존 인스턴스 수정
→ 코드 삭제 시 기존 인스턴스 삭제
```

### 로컬 상태 관리

**기본 동작:**

```bash
# 초기화
terraform init

# 계획 (상태 파일과 코드 비교)
terraform plan

# 적용 (상태 파일 업데이트)
terraform apply

# 현재 디렉토리에 생성:
# - terraform.tfstate (현재 상태)
# - terraform.tfstate.backup (이전 상태)
```

**로컬 상태의 문제점:**

```
1. 팀 협업 불가
   - A가 terraform apply
   - B도 terraform apply
   → 충돌 발생

2. 상태 파일 유실 위험
   - 로컬 파일이 삭제되면
   → Terraform이 인프라를 "새로 만들어야 한다"고 판단
   → 기존 리소스 삭제 후 재생성 (장애!)

3. 민감 정보 노출
   - 상태 파일에 비밀번호 등 저장됨
   - Git에 커밋하면 안 됨
```

### 원격 상태 저장소

**S3 + DynamoDB 백엔드 (AWS 권장):**

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

**S3 버킷 및 DynamoDB 테이블 생성:**

```hcl
# bootstrap/main.tf (한 번만 실행)
resource "aws_s3_bucket" "terraform_state" {
  bucket = "my-terraform-state"
  
  lifecycle {
    prevent_destroy = true  # 실수로 삭제 방지
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  
  versioning_configuration {
    status = "Enabled"  # 버전 관리
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"  # 암호화
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 락 테이블 (동시 실행 방지)
resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  
  attribute {
    name = "LockID"
    type = "S"
  }
}
```

**원격 상태의 장점:**

```
1. 팀 협업
   - 모두 같은 상태 파일 사용
   - 동시 실행 방지 (DynamoDB 락)

2. 안전성
   - S3 버전 관리 → 이전 상태 복구 가능
   - 암호화 → 민감 정보 보호
   - 백업 자동화

3. 공유 가능
   - 다른 프로젝트에서 상태 참조
```

**백엔드 초기화:**

```bash
# 1. backend.tf 작성
# 2. 초기화 (상태 파일을 S3로 이동)
terraform init

# 로컬 → S3 마이그레이션
Do you want to copy existing state to the new backend?
  Enter a value: yes

# 로컬 상태 파일 삭제
rm terraform.tfstate*
```

### 상태 파일 명령어

```bash
# 상태 파일 내 모든 리소스 목록
terraform state list

# 특정 리소스 상세 정보
terraform state show aws_instance.web

# 리소스 이름 변경
terraform state mv aws_instance.old aws_instance.new

# 상태 파일에서 리소스 제거 (실제 리소스는 유지)
terraform state rm aws_instance.web

# 기존 리소스를 Terraform으로 가져오기
terraform import aws_instance.web i-1234567890

# 상태 파일 갱신 (코드 변경 없이)
terraform refresh
```

**실무 시나리오:**

```bash
# 시나리오 1: 리소스를 수동으로 만들었는데 Terraform으로 관리하고 싶음
terraform import aws_s3_bucket.logs my-existing-bucket

# 시나리오 2: 실수로 코드에서 리소스를 삭제했지만 실제로는 유지하고 싶음
terraform state rm aws_instance.important

# 시나리오 3: 리소스 이름을 코드에서 변경했는데 재생성되는 것을 방지
terraform state mv aws_instance.old_name aws_instance.new_name

# 시나리오 4: 이전 상태로 롤백
# S3 버전 관리로 이전 tfstate 다운로드 후
terraform state push terraform.tfstate.backup
```

---

## 모듈 시스템

### 모듈이란?

재사용 가능한 Terraform 코드 묶음입니다.

**왜 모듈을 사용하는가?**

```
문제:
똑같은 VPC 코드를 dev, staging, prod에서 복붙
→ 수정 시 3곳 모두 수정
→ 실수 발생

해결:
VPC 모듈 1개 작성
→ dev, staging, prod에서 재사용
→ 수정 시 1곳만 수정
```

### 모듈 구조

**기본 모듈:**

```
modules/vpc/
├── main.tf        # 리소스 정의
├── variables.tf   # 입력 변수
├── outputs.tf     # 출력 값
└── README.md      # 사용 설명서
```

**VPC 모듈 예시:**

```hcl
# modules/vpc/variables.tf
variable "name" {
  description = "VPC 이름"
  type        = string
}

variable "cidr_block" {
  description = "VPC CIDR"
  type        = string
}

variable "availability_zones" {
  description = "가용 영역"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "퍼블릭 서브넷 CIDR"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "프라이빗 서브넷 CIDR"
  type        = list(string)
}

variable "tags" {
  description = "태그"
  type        = map(string)
  default     = {}
}
```

```hcl
# modules/vpc/main.tf
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(var.tags, {
    Name = var.name
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  
  tags = merge(var.tags, {
    Name = "${var.name}-igw"
  })
}

resource "aws_subnet" "public" {
  count = length(var.availability_zones)
  
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  
  tags = merge(var.tags, {
    Name = "${var.name}-public-${count.index + 1}"
    Type = "public"
  })
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)
  
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]
  
  tags = merge(var.tags, {
    Name = "${var.name}-private-${count.index + 1}"
    Type = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  
  tags = merge(var.tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT Gateway (프라이빗 서브넷 인터넷 접근)
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"
  
  tags = merge(var.tags, {
    Name = "${var.name}-nat-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "this" {
  count = length(var.availability_zones)
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  tags = merge(var.tags, {
    Name = "${var.name}-nat-${count.index + 1}"
  })
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.this.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[count.index].id
  }
  
  tags = merge(var.tags, {
    Name = "${var.name}-private-rt-${count.index + 1}"
  })
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
```

```hcl
# modules/vpc/outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR"
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "퍼블릭 서브넷 ID 목록"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "프라이빗 서브넷 ID 목록"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ids" {
  description = "NAT Gateway ID 목록"
  value       = aws_nat_gateway.this[*].id
}
```

### 모듈 사용

```hcl
# environments/production/main.tf
module "vpc" {
  source = "../../modules/vpc"
  
  name               = "production"
  cidr_block         = "10.0.0.0/16"
  availability_zones = ["ap-northeast-2a", "ap-northeast-2c"]
  
  public_subnet_cidrs = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]
  
  private_subnet_cidrs = [
    "10.0.11.0/24",
    "10.0.12.0/24"
  ]
  
  tags = {
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# 모듈 출력 사용
resource "aws_instance" "web" {
  subnet_id = module.vpc.private_subnet_ids[0]
  # ...
}
```

### 공식 모듈 활용

**Terraform Registry:**

```hcl
# AWS VPC 공식 모듈
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  
  name = "my-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["ap-northeast-2a", "ap-northeast-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
  
  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}

# EKS 클러스터 모듈
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.0.0"
  
  cluster_name    = "my-cluster"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  # ...
}
```

---

## 실전 AWS 인프라 구축

### 3-Tier 웹 애플리케이션

**목표 아키텍처:**

```
Internet
   ↓
ALB (로드 밸런서)
   ↓
EC2 (웹 서버) - Auto Scaling
   ↓
RDS (데이터베이스) - Multi-AZ

+ ElastiCache (Redis)
+ S3 (정적 파일)
```

### 1단계: VPC와 네트워크

```hcl
# main.tf
module "vpc" {
  source = "./modules/vpc"
  
  name               = "${var.project_name}-${var.environment}"
  cidr_block         = "10.0.0.0/16"
  availability_zones = ["ap-northeast-2a", "ap-northeast-2c"]
  
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24"]
  database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = var.environment != "production"
  
  tags = local.common_tags
}
```

### 2단계: 보안 그룹

```hcl
# security-groups.tf
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-alb-sg"
  })
}

resource "aws_security_group" "web" {
  name_prefix = "${var.project_name}-web-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  ingress {
    description = "SSH from bastion"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-web-sg"
  })
}

resource "aws_security_group" "database" {
  name_prefix = "${var.project_name}-db-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description     = "MySQL from web servers"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-db-sg"
  })
}
```

### 3단계: ALB (Application Load Balancer)

```hcl
# alb.tf
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnet_ids
  
  enable_deletion_protection = var.environment == "production"
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-alb"
  })
}

resource "aws_lb_target_group" "web" {
  name     = "${var.project_name}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = module.vpc.vpc_id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
  
  deregistration_delay = 30
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-tg"
  })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# HTTPS 리스너 (선택)
resource "aws_lb_listener" "https" {
  count = var.certificate_arn != "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}
```

### 4단계: Auto Scaling EC2

```hcl
# ec2.tf
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_launch_template" "web" {
  name_prefix   = "${var.project_name}-web-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  
  key_name = aws_key_pair.main.key_name
  
  vpc_security_group_ids = [aws_security_group.web.id]
  
  iam_instance_profile {
    name = aws_iam_instance_profile.web.name
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    db_endpoint = aws_db_instance.main.endpoint
    redis_endpoint = aws_elasticache_cluster.redis.cache_nodes[0].address
    s3_bucket = aws_s3_bucket.app.bucket
  }))
  
  tag_specifications {
    resource_type = "instance"
    
    tags = merge(local.common_tags, {
      Name = "${var.project_name}-web"
    })
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "web" {
  name                = "${var.project_name}-asg"
  vpc_zone_identifier = module.vpc.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.web.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300
  
  min_size         = var.asg_min_size
  max_size         = var.asg_max_size
  desired_capacity = var.asg_desired_capacity
  
  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }
  
  tag {
    key                 = "Name"
    value               = "${var.project_name}-web"
    propagate_at_launch = true
  }
  
  dynamic "tag" {
    for_each = local.common_tags
    
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

# Auto Scaling 정책
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "${var.project_name}-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.web.name
}

resource "aws_autoscaling_policy" "scale_down" {
  name                   = "${var.project_name}-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.web.name
}

# CloudWatch 알람
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web.name
  }
  
  alarm_actions = [aws_autoscaling_policy.scale_up.arn]
}

resource "aws_cloudwatch_metric_alarm" "cpu_low" {
  alarm_name          = "${var.project_name}-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "20"
  
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web.name
  }
  
  alarm_actions = [aws_autoscaling_policy.scale_down.arn]
}
```

### 5단계: RDS 데이터베이스

```hcl
# rds.tf
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = module.vpc.database_subnet_ids
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-db-subnet"
  })
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-mysql8"
  family = "mysql8.0"
  
  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }
  
  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }
  
  parameter {
    name  = "max_connections"
    value = "200"
  }
  
  tags = local.common_tags
}

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"
  
  engine         = "mysql"
  engine_version = "8.0.35"
  instance_class = var.db_instance_class
  
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  
  multi_az               = var.environment == "production"
  backup_retention_period = var.environment == "production" ? 7 : 1
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  enabled_cloudwatch_logs_exports = ["error", "general", "slowquery"]
  
  skip_final_snapshot       = var.environment != "production"
  final_snapshot_identifier = "${var.project_name}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  deletion_protection       = var.environment == "production"
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-db"
  })
}

# Read Replica (선택)
resource "aws_db_instance" "read_replica" {
  count = var.create_read_replica ? 1 : 0
  
  identifier     = "${var.project_name}-db-replica"
  replicate_source_db = aws_db_instance.main.identifier
  
  instance_class = var.db_instance_class
  
  publicly_accessible = false
  skip_final_snapshot = true
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-db-replica"
  })
}
```

### 6단계: ElastiCache (Redis)

```hcl
# elasticache.tf
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-redis-subnet"
  subnet_ids = module.vpc.private_subnet_ids
  
  tags = local.common_tags
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-redis-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description     = "Redis from web servers"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-redis-sg"
  })
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-redis"
  })
}
```

### 7단계: S3 버킷

```hcl
# s3.tf
resource "aws_s3_bucket" "app" {
  bucket = "${var.project_name}-${var.environment}-app"
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-app"
  })
}

resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM 정책 (EC2가 S3 접근)
resource "aws_iam_role" "web" {
  name = "${var.project_name}-web-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy" "web_s3" {
  name = "${var.project_name}-web-s3-policy"
  role = aws_iam_role.web.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.app.arn}/*"
      },
      {
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = aws_s3_bucket.app.arn
      }
    ]
  })
}

resource "aws_iam_instance_profile" "web" {
  name = "${var.project_name}-web-profile"
  role = aws_iam_role.web.name
}
```

### 8단계: 출력 값

```hcl
# outputs.tf
output "alb_dns_name" {
  description = "ALB DNS 이름"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB Zone ID"
  value       = aws_lb.main.zone_id
}

output "database_endpoint" {
  description = "RDS 엔드포인트"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis 엔드포인트"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 버킷 이름"
  value       = aws_s3_bucket.app.bucket
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}
```

---

## 고급 패턴

### Workspace로 환경 분리

```bash
# Workspace 생성
terraform workspace new dev
terraform workspace new staging
terraform workspace new production

# Workspace 목록
terraform workspace list

# Workspace 전환
terraform workspace select production

# 현재 Workspace
terraform workspace show
```

**Workspace 활용:**

```hcl
locals {
  environment = terraform.workspace
  
  # Workspace별 설정
  instance_type = {
    dev        = "t3.micro"
    staging    = "t3.small"
    production = "t3.medium"
  }
  
  asg_min_size = {
    dev        = 1
    staging    = 2
    production = 3
  }
}

resource "aws_instance" "web" {
  instance_type = local.instance_type[local.environment]
  # ...
}
```

### 조건부 리소스 생성

```hcl
# 프로덕션에서만 생성
resource "aws_db_instance" "read_replica" {
  count = var.environment == "production" ? 1 : 0
  
  # ...
}

# 모니터링 활성화 시에만 생성
resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_monitoring ? 1 : 0
  
  # ...
}

# for_each로 동적 생성
variable "additional_security_groups" {
  type = map(object({
    description = string
    port        = number
  }))
  
  default = {}
}

resource "aws_security_group" "additional" {
  for_each = var.additional_security_groups
  
  name        = "${var.project_name}-${each.key}"
  description = each.value.description
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = each.value.port
    to_port     = each.value.port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### Null Resource로 프로비저닝

```hcl
# 인스턴스 생성 후 스크립트 실행
resource "null_resource" "web_setup" {
  depends_on = [aws_instance.web]
  
  triggers = {
    instance_id = aws_instance.web.id
  }
  
  connection {
    type        = "ssh"
    host        = aws_instance.web.public_ip
    user        = "ec2-user"
    private_key = file("~/.ssh/id_rsa")
  }
  
  provisioner "remote-exec" {
    inline = [
      "sudo yum update -y",
      "sudo yum install -y docker",
      "sudo systemctl start docker",
      "sudo docker run -d -p 80:80 nginx"
    ]
  }
}
```

### Dynamic 블록

```hcl
# 동적으로 여러 ingress 규칙 생성
variable "ingress_rules" {
  type = list(object({
    description = string
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
  }))
  
  default = [
    {
      description = "HTTP"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    },
    {
      description = "HTTPS"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  ]
}

resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = module.vpc.vpc_id
  
  dynamic "ingress" {
    for_each = var.ingress_rules
    
    content {
      description = ingress.value.description
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
    }
  }
}
```

---

## 운영 및 협업

### Terraform 명령어 워크플로우

```bash
# 1. 초기화 (프로바이더 다운로드)
terraform init

# 2. 검증 (문법 체크)
terraform validate

# 3. 포맷팅 (코드 정리)
terraform fmt -recursive

# 4. 계획 수립 (변경 사항 확인)
terraform plan -out=plan.out

# 5. 적용 (인프라 생성/변경)
terraform apply plan.out

# 또는 바로 적용 (승인 필요)
terraform apply

# 6. 리소스 제거
terraform destroy

# 특정 리소스만 적용/제거
terraform apply -target=aws_instance.web
terraform destroy -target=aws_s3_bucket.logs
```

### CI/CD 통합

**GitHub Actions 예시:**

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2
      
      - name: Terraform Init
        run: terraform init
      
      - name: Terraform Format
        run: terraform fmt -check
      
      - name: Terraform Validate
        run: terraform validate
      
      - name: Terraform Plan
        if: github.event_name == 'pull_request'
        run: terraform plan -no-color
        continue-on-error: true
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const output = `#### Terraform Plan 📖
            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\`
            `;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });
      
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve
```

### 보안 사항

```hcl
# 1. 민감 정보는 절대 하드코딩 금지
# ❌ 나쁜 예
resource "aws_db_instance" "main" {
  password = "password123"  # 절대 금지!
}

# ✅ 좋은 예: 환경 변수
variable "db_password" {
  type      = string
  sensitive = true
}

# ✅ 더 좋은 예: AWS Secrets Manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/db/password"
}

resource "aws_db_instance" "main" {
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
}

# 2. 상태 파일 보호
# - S3 암호화
# - S3 버전 관리
# - S3 접근 제한
# - .gitignore에 추가

# 3. 최소 권한 원칙
# IAM 사용자/역할에 필요한 권한만 부여
```

**.gitignore:**

```
# .gitignore
**/.terraform/*
*.tfstate
*.tfstate.*
crash.log
*.tfvars
*.tfvars.json
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terraformrc
terraform.rc
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.83.5
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_docs
      - id: terraform_tflint
```

---

## 참고 자료

- **공식 문서**: https://developer.hashicorp.com/terraform/docs
- **Terraform Registry**: https://registry.terraform.io/
- **HashiCorp Learn**: https://learn.hashicorp.com/terraform

---

