---
title: AWS Terraform 실전
tags: [terraform, aws, iac, devops, ecs, vpc, rds]
updated: 2026-06-12
---

# AWS Terraform 실전

[Terraform](./Terraform.md)과 [Terraform 기초](./Terraform_기초.md)는 HCL 문법, state 관리, 모듈 같은 범용 내용을 다룬다. 이 문서는 AWS 위에서 실제 스택을 올릴 때만 겪는 문제를 정리한다. provider 인증, backend 부트스트랩, VPC부터 ECS/RDS까지 이어지는 end-to-end 구성, AWS에서만 나는 drift, 콘솔에서 만든 리소스를 코드로 가져오는 import 순서까지다.

AWS provider 버전은 메이저마다 리소스 인자가 바뀌어서 항상 고정해야 한다. 이 문서 예제는 `hashicorp/aws` 5.x, Terraform 1.9 기준이다.

---

## provider 인증

AWS provider는 인증 정보를 코드에 박지 않는다. 자격증명은 환경 변수, 공유 credentials 파일, EC2/ECS의 인스턴스 role, OIDC 같은 외부 소스에서 읽는다. 어디서 읽느냐가 로컬 개발이냐 CI냐에 따라 갈린다.

### 로컬은 profile, 운영 자동화는 assume_role

로컬에서 여러 계정을 오갈 때는 named profile이 제일 깔끔하다. `~/.aws/config`에 profile을 정의하고 provider에서 지정한다.

```hcl
provider "aws" {
  region  = "ap-northeast-2"
  profile = "myteam-dev"
}
```

문제는 이 `profile = "myteam-dev"`가 코드에 박힌다는 점이다. dev에서 만든 코드를 prod에 그대로 apply하면 엉뚱한 계정으로 나간다. profile은 변수로 빼거나 `AWS_PROFILE` 환경 변수로 넘기고 코드에는 안 적는 게 낫다.

```hcl
provider "aws" {
  region = "ap-northeast-2"
  # profile은 AWS_PROFILE 환경 변수로 주입
}
```

```bash
AWS_PROFILE=myteam-dev terraform plan
AWS_PROFILE=myteam-prod terraform plan
```

크로스 계정 배포에서는 `assume_role`을 쓴다. 권한이 약한 베이스 자격증명으로 시작해서, 대상 계정의 role을 떠맡아(assume) 그 권한으로 리소스를 만든다.

```hcl
provider "aws" {
  region = "ap-northeast-2"

  assume_role {
    role_arn     = "arn:aws:iam::111122223333:role/terraform-deploy"
    session_name = "terraform-ci"
  }
}
```

`session_name`은 CloudTrail에 그대로 찍힌다. 누가 어떤 파이프라인에서 apply했는지 추적하려면 의미 있는 이름을 넣어야 한다. 비워두면 나중에 사고 났을 때 로그만 보고는 범인을 못 찾는다.

### GitHub Actions는 OIDC로 키 없이 인증

CI에서 가장 흔한 실수가 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`를 GitHub Secrets에 넣는 것이다. 이 키는 만료가 없어서 한 번 유출되면 끝까지 살아있다. GitHub Actions OIDC를 쓰면 장기 키 없이 단기 토큰으로 role을 assume한다.

먼저 AWS에 GitHub의 OIDC provider를 등록하고, 그 provider를 신뢰하는 role을 만든다. 이 부분도 Terraform으로 관리한다.

```hcl
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_actions" {
  name = "github-actions-terraform"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:myorg/myrepo:ref:refs/heads/main"
        }
      }
    }]
  })
}
```

여기서 `sub` 조건이 핵심이다. `repo:myorg/myrepo:ref:refs/heads/main`으로 묶으면 main 브랜치에서 도는 워크플로우만 이 role을 떠맡을 수 있다. 이 조건을 `repo:myorg/myrepo:*`처럼 느슨하게 풀면 누군가 PR을 열어서 워크플로우를 돌리는 것만으로 prod role을 얻는다. fork PR이 돌 수 있는 저장소라면 더 조여야 한다.

워크플로우 쪽은 `aws-actions/configure-aws-credentials`가 OIDC 토큰을 받아 role을 assume한다.

```yaml
permissions:
  id-token: write   # OIDC 토큰 발급에 필요. 빠지면 인증 자체가 안 된다
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111122223333:role/github-actions-terraform
          aws-region: ap-northeast-2
      - run: terraform init
      - run: terraform apply -auto-approve
```

`permissions: id-token: write`를 빠뜨리면 토큰 발급이 안 돼서 인증이 통째로 실패한다. 에러 메시지가 "Could not assume role"이라 OIDC 등록을 의심하기 쉬운데, 실제로는 워크플로우 권한 한 줄이 빠진 경우가 많다.

### default_tags로 태그 누락 막기

리소스마다 `tags`를 일일이 적으면 빠뜨리는 게 생긴다. 비용 추적용 태그가 절반쯤 빠져 있으면 월말에 어느 팀이 얼마 썼는지 못 가른다. provider 레벨 `default_tags`를 쓰면 그 provider로 만든 모든 리소스에 태그가 자동으로 붙는다.

```hcl
provider "aws" {
  region = "ap-northeast-2"

  default_tags {
    tags = {
      Environment = "prod"
      ManagedBy   = "terraform"
      Team        = "backend"
    }
  }
}
```

리소스에서 같은 키로 `tags`를 또 적으면 리소스 쪽이 이긴다. 다만 주의할 게 있다. `default_tags`와 리소스 `tags`에 같은 키가 있으면 plan에서 매번 변경으로 잡히는 버그성 동작이 provider 버전에 따라 나온다. 같은 키를 양쪽에 중복으로 두지 말고, 공통 태그는 `default_tags`에만 두는 게 안전하다.

태그를 안 받는 리소스도 있다. `default_tags`는 태그를 지원하는 리소스에만 붙으니, 모든 리소스에 다 들어갈 거라고 기대하면 안 된다.

---

## S3 + DynamoDB backend 부트스트랩

state를 로컬에 두면 팀 작업이 불가능하다. S3에 state를 두고 DynamoDB로 lock을 건다. 그런데 여기서 닭과 달걀 문제가 생긴다. backend로 쓸 S3 버킷과 DynamoDB 테이블을 Terraform으로 만들고 싶은데, 그 state를 어디에 둘 것인가. 아직 backend가 없다.

### 2단계로 푼다

해법은 backend 리소스만 먼저 로컬 state로 만들고, 만든 다음에 backend를 그 버킷으로 옮기는 것이다.

먼저 `bootstrap/` 디렉토리를 따로 두고 backend 블록 없이 시작한다.

```hcl
# bootstrap/main.tf — backend 블록 없음. state는 로컬 파일로 시작

resource "aws_s3_bucket" "tfstate" {
  bucket = "myteam-tfstate-prod"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# 실수로 state 버킷을 지우는 일을 막는다
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tflock" {
  name         = "myteam-tflock-prod"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
```

`versioning`은 반드시 켠다. state가 깨졌을 때 이전 버전으로 되돌릴 유일한 수단이다. 안 켜두면 잘못된 apply 한 번에 state가 날아가고 복구 불가능하다.

이걸 로컬 state로 apply한다.

```bash
cd bootstrap
terraform init
terraform apply
```

이제 버킷과 테이블이 생겼다. 다음으로 backend 블록을 추가하고 로컬 state를 S3로 옮긴다.

```hcl
# bootstrap/backend.tf 추가
terraform {
  backend "s3" {
    bucket         = "myteam-tfstate-prod"
    key            = "bootstrap/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "myteam-tflock-prod"
    encrypt        = true
  }
}
```

```bash
terraform init -migrate-state
# "Do you want to copy existing state to the new backend?" → yes
```

`-migrate-state`가 로컬 `terraform.tfstate`를 S3로 복사한다. 이 한 번만 닭과 달걀을 수동으로 끊으면, 이후 본체 스택은 처음부터 backend를 S3로 선언하면 된다.

> AWS provider 5.x 후반부터 DynamoDB 대신 S3 자체 lock(`use_lockfile = true`)을 쓸 수 있다. 다만 기존 프로젝트는 대부분 DynamoDB 방식이라 여기서는 그 구성을 기준으로 둔다.

### state key는 환경별로 분리

같은 버킷을 쓰더라도 `key`를 환경별로 나눠야 한다. `prod/terraform.tfstate`, `dev/terraform.tfstate` 식이다. 같은 key를 dev와 prod가 공유하면 한쪽 apply가 다른 쪽 state를 덮어쓴다. 이건 복구가 까다로운 사고다.

### Terraform 실행용 IAM Role 최소 권한

CI에서 assume하는 `terraform-deploy` role에 `AdministratorAccess`를 붙이는 경우가 많다. 편하지만 그 role이 유출되면 계정 전체가 털린다. 실제로 그 스택이 건드리는 서비스로만 좁혀야 한다.

VPC/ECS/RDS 스택이면 대략 이 정도다.

```hcl
resource "aws_iam_role_policy" "terraform_deploy" {
  name = "terraform-deploy-policy"
  role = aws_iam_role.terraform_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:*",
          "ecs:*",
          "elasticloadbalancing:*",
          "rds:*",
          "logs:*",
        ]
        Resource = "*"
      },
      {
        # state 접근
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::myteam-tfstate-prod",
          "arn:aws:s3:::myteam-tfstate-prod/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "arn:aws:dynamodb:ap-northeast-2:111122223333:table/myteam-tflock-prod"
      },
      {
        # IAM은 거의 필수다. ECS task role 등을 만들기 때문
        Effect = "Allow"
        Action = [
          "iam:CreateRole", "iam:DeleteRole", "iam:GetRole",
          "iam:PassRole", "iam:AttachRolePolicy", "iam:DetachRolePolicy",
          "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:ListRolePolicies",
        ]
        Resource = "*"
      },
    ]
  })
}
```

`ec2:*`처럼 서비스 단위로 와일드카드를 주는 건 현실적 타협이다. 액션 하나하나 좁히면 plan 한 번 돌릴 때마다 권한 부족 에러가 나서 끝없이 추가하게 된다. 서비스 범위로 막고 `Resource`로 계정/리전을 거는 선에서 시작하는 게 운영하기 편하다.

`iam:PassRole`을 빼먹으면 ECS task definition을 만들 때 "is not authorized to perform iam:PassRole"로 막힌다. ECS, Lambda처럼 다른 서비스에 role을 넘기는 리소스를 만들려면 반드시 들어가야 한다.

---

## VPC → ALB → ECS Fargate → RDS end-to-end

실제 웹 서비스 스택을 한 번에 올려본다. 흐름은 VPC와 subnet을 깔고, ALB를 public에 두고, ECS Fargate 서비스를 private에 띄우고, RDS를 가장 안쪽에 두는 구조다. 신규 VPC를 만들지 않고 기존 VPC에 얹는 경우가 많아서 data source 조회도 같이 다룬다.

### data source로 기존 리소스 조회

회사에서 VPC는 네트워크 팀이 따로 관리하는 경우가 흔하다. 그럴 때는 VPC를 만들지 않고 조회한다.

```hcl
# 태그로 기존 VPC를 찾는다
data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = ["main-vpc"]
  }
}

# 그 VPC의 private subnet들
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "tag:Tier"
    values = ["private"]
  }
}

# 최신 Amazon Linux 2023 AMI (EC2를 쓸 경우)
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}
```

AMI를 `data` source로 `most_recent = true`로 잡으면 함정이 있다. AWS가 새 AMI를 내놓는 순간 plan에 변경이 잡혀서 인스턴스를 갈아엎으려 든다. ASG/launch template에서는 AMI ID를 변수로 고정하거나 `ignore_changes`로 막는 게 안전하다. 조회 자체는 편하지만 그 값이 자동으로 따라 움직인다는 걸 항상 의식해야 한다.

### subnet과 security group

여기서는 신규 VPC를 만드는 쪽으로 전체를 보여준다. ALB는 public subnet, ECS와 RDS는 private subnet에 둔다.

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

data "aws_availability_zones" "available" {
  state = "available"
}
```

security group은 계층별로 나눈다. ALB는 인터넷에서 443을 받고, ECS는 ALB에서만 받고, RDS는 ECS에서만 받는다. 핵심은 source를 CIDR이 아니라 다른 security group ID로 거는 것이다.

```hcl
resource "aws_security_group" "alb" {
  name   = "alb-sg"
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group" "ecs" {
  name   = "ecs-sg"
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group" "rds" {
  name   = "rds-sg"
  vpc_id = aws_vpc.main.id
}

# 규칙은 aws_security_group_rule이 아니라
# aws_vpc_security_group_ingress_rule로 (5.x 권장 방식)
resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}
```

규칙을 `aws_security_group` 블록 안 inline `ingress`로 쓰지 말고 별도 리소스(`aws_vpc_security_group_ingress_rule`)로 빼는 이유는 drift 때문이다. 뒤에서 따로 다룬다.

### ALB와 target group

```hcl
resource "aws_lb" "main" {
  name               = "app-alb"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "app" {
  name        = "app-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"   # Fargate는 ip 모드. instance 모드 아님

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

Fargate에서 target group `target_type`은 반드시 `ip`다. `instance`로 두면 task가 등록이 안 돼서 health check가 영원히 unhealthy로 뜬다. 이걸 모르면 한참 헤맨다.

### ECS Fargate 서비스

```hcl
resource "aws_ecs_cluster" "main" {
  name = "app-cluster"
}

resource "aws_ecs_task_definition" "app" {
  family                   = "app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "app"
    image = "${var.ecr_repo_url}:${var.image_tag}"
    portMappings = [{
      containerPort = 8080
    }]
    environment = [
      { name = "DB_HOST", value = aws_db_instance.main.address }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = "ap-northeast-2"
        "awslogs-stream-prefix" = "app"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  name            = "app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8080
  }
}
```

`execution_role`과 `task_role`을 헷갈리면 안 된다. execution role은 ECS 에이전트가 이미지를 ECR에서 당기고 로그를 CloudWatch에 쓰는 권한이다. task role은 컨테이너 안 애플리케이션 코드가 S3나 SQS 같은 AWS 서비스를 호출할 때 쓰는 권한이다. 둘을 한 role로 합치면 애플리케이션에 불필요한 ECR/로그 권한이 새어 들어간다.

### RDS

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "app-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier             = "app-db"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.t4g.medium"
  allocated_storage      = 50
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  username = "appuser"
  # 비밀번호는 뒤 drift 절에서 다룬다
  manage_master_user_password = true

  skip_final_snapshot = false
  final_snapshot_identifier = "app-db-final"
}
```

RDS는 생성에 10분 넘게 걸린다. ECS task가 `DB_HOST`로 `aws_db_instance.main.address`를 참조하니, Terraform이 RDS를 먼저 만들고 ECS를 띄운다. 의존성을 명시적으로 안 적어도 참조가 걸려 있으면 순서가 맞춰진다. 다만 RDS 생성 시간 때문에 첫 apply는 길다는 걸 감안해야 한다.

---

## AWS에서만 겪는 drift

drift는 코드에 적힌 상태와 실제 AWS 리소스가 어긋난 상태다. AWS는 콘솔, 오토스케일링, 다른 서비스가 리소스를 자동으로 바꿔서 drift가 유독 잘 난다. 대부분 `lifecycle { ignore_changes = [...] }`로 푼다.

### ASG desired_capacity

오토스케일링 그룹의 `desired_capacity`를 코드에 `2`로 적었는데, 트래픽이 늘어서 ASG가 자동으로 5로 늘렸다고 하자. 다음 apply에서 Terraform은 이걸 2로 되돌리려 한다. 한밤중 피크 시간에 인스턴스가 강제로 줄어드는 사고다.

```hcl
resource "aws_autoscaling_group" "app" {
  desired_capacity = 2
  min_size         = 2
  max_size         = 10

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}
```

`desired_capacity`는 런타임에 오토스케일링이 주인이다. Terraform은 초기값만 정하고 이후 변동은 무시해야 한다. `min_size`/`max_size`는 사람이 정하는 경계라 ignore하지 않는다.

### security group rule 순서

inline `ingress` 블록으로 규칙을 여러 개 적으면, AWS가 반환하는 순서와 코드 순서가 달라서 plan에 매번 변경이 뜬다. 실제로는 아무것도 안 바뀌었는데 plan이 계속 더러워진다. 위 예제에서 규칙을 `aws_vpc_security_group_ingress_rule` 별도 리소스로 뺀 이유가 이것이다.

이미 inline으로 짜버린 기존 코드라면 규칙을 별도 리소스로 옮기는 게 정답이지만, 당장 안 되면 `ignore_changes`로 막는다.

```hcl
resource "aws_security_group" "legacy" {
  # inline ingress가 잔뜩 있는 기존 리소스
  lifecycle {
    ignore_changes = [ingress, egress]
  }
}
```

### RDS master password

`aws_db_instance`에 `password = "..."`를 직접 적으면 그 비밀번호가 state 파일에 평문으로 남는다. S3 backend가 암호화돼 있어도 state를 당겨보는 사람은 다 본다. 그래서 위 RDS 예제에서 `manage_master_user_password = true`를 썼다. 이러면 AWS가 비밀번호를 Secrets Manager에 만들고 관리한다.

직접 비밀번호를 넣어야 하는 상황이면 콘솔이나 CLI에서 한 번 바꾼 뒤 Terraform은 그 값을 안 건드리게 한다.

```hcl
resource "aws_db_instance" "main" {
  # password를 외부에서 관리하고 Terraform은 무시
  lifecycle {
    ignore_changes = [password]
  }
}
```

비밀번호를 콘솔에서 돌렸는데 코드에 옛날 값이 남아 있으면, 다음 apply가 DB 비밀번호를 옛날 값으로 되돌려서 애플리케이션 연결이 죽는다. 운영 중 DB에서 이게 터지면 장애다.

### ECS task_definition revision

ECS는 배포할 때마다 task definition revision이 올라간다(`:5` → `:6`). CD 파이프라인이 새 이미지로 task definition을 갱신하는 구조라면, Terraform이 가진 건 옛날 revision이다. 다음 `terraform apply`가 ECS 서비스를 옛날 revision으로 되돌려서 방금 배포한 버전을 롤백시킨다.

배포를 Terraform 밖(CodeDeploy, GitHub Actions의 ECS 배포 액션 등)에서 한다면, Terraform은 task definition과 image를 무시해야 한다.

```hcl
resource "aws_ecs_service" "app" {
  # 이미지 배포는 CD가 담당, Terraform은 서비스 구성만 관리
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }
}
```

여기서 선택이 갈린다. 이미지 배포까지 Terraform으로 할 거면 `image_tag`를 변수로 받아서 apply로 배포하고 `ignore_changes`를 안 건다. 배포는 별도 CD가 할 거면 위처럼 무시한다. 둘을 섞으면 서로 상대 변경을 되돌리는 핑퐁이 난다. 어느 쪽이 task definition의 주인인지 팀에서 먼저 정해야 한다.

---

## terraform import

콘솔에서 급하게 만든 리소스를 나중에 코드로 가져올 때 `import`를 쓴다. import는 실제 리소스를 state에 등록할 뿐 코드를 만들어주지 않는다. 코드는 사람이 직접 써야 한다.

### import 블록 방식 (1.5+)

예전엔 `terraform import` CLI 명령으로 했지만, 1.5부터는 `import` 블록으로 코드에 선언한다. plan으로 미리 확인할 수 있어서 이쪽이 안전하다.

```hcl
import {
  to = aws_s3_bucket.legacy
  id = "my-existing-bucket"
}

# 이 리소스 코드는 직접 채운다
resource "aws_s3_bucket" "legacy" {
  bucket = "my-existing-bucket"
}
```

```bash
terraform plan   # import 후 차이를 보여준다
terraform apply  # 실제 import 실행
```

### 핵심은 코드와 실제를 완벽히 맞추는 것

import 후 plan에서 변경이 잡히면, 코드가 실제 리소스와 다르다는 뜻이다. 이 상태로 apply하면 콘솔에서 만든 설정을 코드 기준으로 덮어쓴다. 모르고 넘어가면 운영 설정이 날아간다.

순서는 이렇게 잡는다. import 블록만 먼저 넣고 빈 resource 블록으로 plan을 돌린다. plan이 보여주는 실제 속성을 보고 코드를 채운다. plan에서 변경이 "No changes"가 될 때까지 코드를 실제에 맞춘다. 그 다음 apply한다.

`terraform plan -generate-config-out=generated.tf`로 코드 초안을 자동 생성할 수 있다. 다만 생성된 코드는 모든 속성을 다 적어놓은 거친 상태라, 그대로 쓰지 말고 정리해야 한다. default값까지 다 박혀 있어서 읽기 나쁘다.

### import할 때 자주 막히는 지점

리소스마다 import용 ID 형식이 다르다. S3는 버킷 이름, EC2는 인스턴스 ID, IAM role은 role 이름, security group rule은 복합 ID(`sg-xxx_ingress_tcp_443_443_0.0.0.0/0` 같은 형식)다. 형식을 틀리면 import가 그냥 실패한다. 리소스 문서의 import 섹션을 봐야 한다.

여러 리소스를 한꺼번에 import할 때는 의존성 있는 것부터 순서대로 한다. VPC를 import하지 않고 그 안 subnet부터 import하면 참조가 깨진다. VPC → subnet → security group → 인스턴스 순으로 바깥부터 안으로 들어간다.

이미 state에 있는 리소스를 또 import하면 "Resource already managed" 에러가 난다. 이럴 땐 import가 아니라 `terraform state` 명령으로 옮기거나 정리하는 문제다.
