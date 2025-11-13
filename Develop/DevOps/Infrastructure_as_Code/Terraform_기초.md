# Terraform 기초 가이드 (Terraform Basics Guide)

## 목차 (Table of Contents)
1. [Terraform 개요 (Terraform Overview)](#terraform-개요)
2. [Terraform 설치 및 설정 (Terraform Installation and Setup)](#terraform-설치-및-설정)
3. [AWS 리소스 생성 예제 (AWS Resource Creation Examples)](#aws-리소스-생성-예제)
4. [모듈화된 인프라 관리 (Modular Infrastructure Management)](#모듈화된-인프라-관리)
5. [상태 파일 관리 (State File Management)](#상태-파일-관리)
6. [실제 EC2, RDS 생성 예제 (Real EC2, RDS Creation Examples)](#실제-ec2-rds-생성-예제)
7. [고급 기능 및 모범 사례 (Advanced Features and Best Practices)](#고급-기능-및-모범-사례)

## Terraform 개요 (Terraform Overview)

Terraform은 HashiCorp에서 개발한 Infrastructure as Code (IaC) 도구로, 클라우드 인프라를 코드로 정의하고 관리할 수 있습니다.

### Terraform의 주요 특징 (Key Features)

- **선언적 구성 (Declarative Configuration)**: 원하는 상태를 선언하면 Terraform이 자동으로 구현
- **멀티 클라우드 지원 (Multi-cloud Support)**: AWS, Azure, GCP 등 다양한 클라우드 제공업체 지원
- **상태 관리 (State Management)**: 인프라의 현재 상태를 추적하고 관리
- **의존성 관리 (Dependency Management)**: 리소스 간 의존성을 자동으로 해결
- **계획 및 적용 (Plan and Apply)**: 변경사항을 미리 확인하고 안전하게 적용

### Terraform 워크플로우 (Terraform Workflow)

```mermaid
graph LR
    A[코드 작성<br/>Write Code] --> B[초기화<br/>terraform init]
    B --> C[계획 수립<br/>terraform plan]
    C --> D[적용<br/>terraform apply]
    D --> E[상태 확인<br/>terraform show]
```

## Terraform 설치 및 설정 (Terraform Installation and Setup)

### 1. Terraform 설치 (Terraform Installation)

#### macOS 설치
```bash
# Homebrew를 사용한 설치
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# 설치 확인
terraform version
```

#### Linux 설치
```bash
# Terraform 다운로드
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip

# 압축 해제
unzip terraform_1.6.0_linux_amd64.zip

# 실행 권한 부여 및 PATH 설정
chmod +x terraform
sudo mv terraform /usr/local/bin/

# 설치 확인
terraform version
```

#### Windows 설치
```powershell
# Chocolatey를 사용한 설치
choco install terraform

# 또는 직접 다운로드 후 PATH 설정
```

### 2. AWS CLI 설정 (AWS CLI Setup)

```bash
# AWS CLI 설치 (macOS)
brew install awscli

# AWS CLI 설치 (Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# AWS 자격 증명 설정
aws configure
```

### 3. 기본 프로젝트 구조 (Basic Project Structure)

```
terraform-project/
├── main.tf              # 메인 구성 파일
├── variables.tf          # 변수 정의
├── outputs.tf           # 출력 값 정의
├── terraform.tfvars     # 변수 값 설정
├── .terraform/          # Terraform 초기화 파일
└── terraform.tfstate    # 상태 파일
```

## AWS 리소스 생성 예제 (AWS Resource Creation Examples)

### 1. 기본 VPC 및 서브넷 생성 (Basic VPC and Subnet Creation)

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC 생성
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# 인터넷 게이트웨이
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# 퍼블릭 서브넷
resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}

# 프라이빗 서브넷
resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
  }
}

# 라우트 테이블 (퍼블릭)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# 라우트 테이블 연결 (퍼블릭)
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
```

### 2. 변수 정의 (Variable Definitions)

```hcl
# variables.tf
variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "프로젝트 이름"
  type        = string
  default     = "terraform-example"
}

variable "vpc_cidr" {
  description = "VPC CIDR 블록"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "가용 영역 목록"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "public_subnet_cidrs" {
  description = "퍼블릭 서브넷 CIDR 블록"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "프라이빗 서브넷 CIDR 블록"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}
```

### 3. 출력 값 정의 (Output Definitions)

```hcl
# outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR 블록"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "퍼블릭 서브넷 ID 목록"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "프라이빗 서브넷 ID 목록"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "인터넷 게이트웨이 ID"
  value       = aws_internet_gateway.main.id
}
```

## 모듈화된 인프라 관리 (Modular Infrastructure Management)

### 1. VPC 모듈 생성 (VPC Module Creation)

```hcl
# modules/vpc/main.tf
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.name}-vpc"
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
    Name = "${var.name}-public-subnet-${count.index + 1}"
  })
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.name}-private-subnet-${count.index + 1}"
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
```

### 2. VPC 모듈 변수 및 출력 (VPC Module Variables and Outputs)

```hcl
# modules/vpc/variables.tf
variable "name" {
  description = "VPC 이름"
  type        = string
}

variable "cidr_block" {
  description = "VPC CIDR 블록"
  type        = string
}

variable "availability_zones" {
  description = "가용 영역 목록"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "퍼블릭 서브넷 CIDR 블록"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "프라이빗 서브넷 CIDR 블록"
  type        = list(string)
}

variable "tags" {
  description = "추가 태그"
  type        = map(string)
  default     = {}
}
```

```hcl
# modules/vpc/outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR 블록"
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

output "internet_gateway_id" {
  description = "인터넷 게이트웨이 ID"
  value       = aws_internet_gateway.this.id
}
```

### 3. 모듈 사용 (Module Usage)

```hcl
# main.tf
module "vpc" {
  source = "./modules/vpc"

  name                = var.project_name
  cidr_block          = var.vpc_cidr
  availability_zones  = var.availability_zones
  public_subnet_cidrs = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
```

## 상태 파일 관리 (State File Management)

### 1. 로컬 상태 파일 (Local State File)

```hcl
# 기본적으로 Terraform은 로컬에 상태 파일을 저장
# terraform.tfstate 파일이 생성됨
```

### 2. 원격 상태 저장소 설정 (Remote State Backend Configuration)

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### 3. S3 버킷 및 DynamoDB 테이블 생성 (S3 Bucket and DynamoDB Table Creation)

```hcl
# state-backend.tf
resource "aws_s3_bucket" "terraform_state" {
  bucket = "your-terraform-state-bucket"

  tags = {
    Name        = "Terraform State Bucket"
    Environment = "Production"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "terraform-state-lock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform State Lock Table"
    Environment = "Production"
  }
}
```

### 4. 상태 파일 작업 (State File Operations)

```bash
# 상태 파일 초기화
terraform init

# 상태 파일 확인
terraform show

# 상태 파일 리스트
terraform state list

# 특정 리소스 상태 확인
terraform state show aws_vpc.main

# 상태 파일 가져오기
terraform import aws_vpc.main vpc-12345678

# 상태 파일에서 리소스 제거
terraform state rm aws_vpc.main

# 상태 파일 이동
terraform state mv aws_vpc.main aws_vpc.old_main
```

## 실제 EC2, RDS 생성 예제 (Real EC2, RDS Creation Examples)

### 1. 보안 그룹 생성 (Security Group Creation)

```hcl
# security-groups.tf
resource "aws_security_group" "web" {
  name_prefix = "${var.project_name}-web-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}

resource "aws_security_group" "database" {
  name_prefix = "${var.project_name}-db-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "MySQL"
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

  tags = {
    Name = "${var.project_name}-db-sg"
  }
}
```

### 2. EC2 인스턴스 생성 (EC2 Instance Creation)

```hcl
# ec2.tf
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = file(var.public_key_path)

  tags = {
    Name = "${var.project_name}-key"
  }
}

resource "aws_instance" "web" {
  count = var.instance_count

  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.main.key_name
  vpc_security_group_ids = [aws_security_group.web.id]
  subnet_id              = module.vpc.public_subnet_ids[count.index % length(module.vpc.public_subnet_ids)]

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    db_endpoint = aws_db_instance.main.endpoint
    db_name     = var.db_name
    db_username = var.db_username
    db_password = var.db_password
  }))

  tags = {
    Name = "${var.project_name}-web-${count.index + 1}"
  }
}

# 로드 밸런서
resource "aws_lb" "main" {
  name               = "${var.project_name}-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web.id]
  subnets            = module.vpc.public_subnet_ids

  tags = {
    Name = "${var.project_name}-lb"
  }
}

resource "aws_lb_target_group" "web" {
  name     = "${var.project_name}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = module.vpc.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-tg"
  }
}

resource "aws_lb_target_group_attachment" "web" {
  count            = var.instance_count
  target_group_arn = aws_lb_target_group.web.arn
  target_id        = aws_instance.web[count.index].id
  port             = 80
}

resource "aws_lb_listener" "web" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}
```

### 3. RDS 데이터베이스 생성 (RDS Database Creation)

```hcl
# rds.tf
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = module.vpc.private_subnet_ids

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  engine         = "mysql"
  engine_version = "8.0"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp2"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = var.environment != "production"
  deletion_protection = var.environment == "production"

  tags = {
    Name = "${var.project_name}-db"
  }
}
```

### 4. 사용자 데이터 스크립트 (User Data Script)

```bash
#!/bin/bash
# user_data.sh

# 시스템 업데이트
yum update -y

# Apache 설치
yum install -y httpd

# Apache 시작 및 자동 시작 설정
systemctl start httpd
systemctl enable httpd

# 간단한 웹 페이지 생성
cat > /var/www/html/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Terraform Example</title>
</head>
<body>
    <h1>Welcome to Terraform Example!</h1>
    <p>This instance was created using Terraform.</p>
    <p>Database Endpoint: ${db_endpoint}</p>
    <p>Database Name: ${db_name}</p>
    <p>Database Username: ${db_username}</p>
</body>
</html>
EOF

# Apache 재시작
systemctl restart httpd
```

### 5. 변수 파일 (Variables File)

```hcl
# variables.tf
variable "environment" {
  description = "환경 (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "instance_count" {
  description = "EC2 인스턴스 개수"
  type        = number
  default     = 2
}

variable "instance_type" {
  description = "EC2 인스턴스 타입"
  type        = string
  default     = "t3.micro"
}

variable "public_key_path" {
  description = "SSH 공개키 파일 경로"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_cidr" {
  description = "SSH 접근 허용 CIDR"
  type        = string
  default     = "0.0.0.0/0"
}

variable "db_instance_class" {
  description = "RDS 인스턴스 클래스"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS 할당된 스토리지 (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS 최대 할당된 스토리지 (GB)"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "데이터베이스 이름"
  type        = string
  default     = "example"
}

variable "db_username" {
  description = "데이터베이스 사용자명"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "데이터베이스 비밀번호"
  type        = string
  sensitive   = true
}
```

### 6. 출력 값 (Outputs)

```hcl
# outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "web_instance_ids" {
  description = "웹 인스턴스 ID 목록"
  value       = aws_instance.web[*].id
}

output "web_instance_public_ips" {
  description = "웹 인스턴스 퍼블릭 IP 목록"
  value       = aws_instance.web[*].public_ip
}

output "load_balancer_dns" {
  description = "로드 밸런서 DNS 이름"
  value       = aws_lb.main.dns_name
}

output "database_endpoint" {
  description = "데이터베이스 엔드포인트"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "database_port" {
  description = "데이터베이스 포트"
  value       = aws_db_instance.main.port
}
```

## 고급 기능 및 모범 사례 (Advanced Features and Best Practices)

### 1. 환경별 변수 파일 (Environment-specific Variable Files)

```hcl
# terraform.tfvars (개발 환경)
environment = "dev"
instance_count = 1
instance_type = "t3.micro"
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
```

```hcl
# production.tfvars (프로덕션 환경)
environment = "production"
instance_count = 3
instance_type = "t3.medium"
db_instance_class = "db.t3.small"
db_allocated_storage = 100
```

### 2. Terraform 명령어 실행 (Terraform Commands)

```bash
# 초기화
terraform init

# 계획 수립
terraform plan -var-file="production.tfvars"

# 적용
terraform apply -var-file="production.tfvars"

# 특정 리소스만 적용
terraform apply -target=aws_instance.web

# 자동 승인
terraform apply -auto-approve

# 리소스 제거
terraform destroy

# 특정 리소스만 제거
terraform destroy -target=aws_instance.web
```

### 3. 모범 사례 (Best Practices)

#### 코드 구조화
```
terraform-project/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── production/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── vpc/
│   ├── ec2/
│   └── rds/
└── shared/
    ├── backend.tf
    └── providers.tf
```

#### 보안 모범 사례
```hcl
# 민감한 데이터는 변수로 관리
variable "db_password" {
  description = "데이터베이스 비밀번호"
  type        = string
  sensitive   = true
}

# AWS Secrets Manager 사용
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/db/password"
}

resource "aws_db_instance" "main" {
  # ... 기타 설정
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
}
```

#### 태깅 전략
```hcl
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = "DevOps Team"
  }
}

resource "aws_instance" "web" {
  # ... 기타 설정
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-web"
    Type = "Web Server"
  })
}
```

## 결론 (Conclusion)

Terraform을 사용하면 인프라를 코드로 관리하여 일관성, 재사용성, 버전 관리의 이점을 얻을 수 있습니다. 모듈화된 구조와 적절한 상태 관리로 확장 가능하고 유지보수가 용이한 인프라를 구축할 수 있습니다.

### 주요 포인트 (Key Points)

1. **코드로 인프라 관리**: 선언적 방식으로 인프라 정의
2. **모듈화**: 재사용 가능한 모듈 구조
3. **상태 관리**: 원격 상태 저장소 활용
4. **환경 분리**: 환경별 변수 파일 관리
5. **보안**: 민감한 데이터 보호 및 접근 제어
6. **모범 사례**: 일관된 태깅 및 코드 구조

Terraform을 통해 Infrastructure as Code의 모든 이점을 활용할 수 있습니다.
