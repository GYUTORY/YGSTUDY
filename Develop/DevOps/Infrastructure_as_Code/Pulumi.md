---
title: Pulumi
tags: [pulumi, iac, infrastructure-as-code, devops, typescript, python]
updated: 2026-04-08
---

# Pulumi

## Pulumi가 뭔가

범용 프로그래밍 언어로 인프라를 정의하는 IaC 도구다. TypeScript, Python, Go, C#, Java를 지원한다. HCL 같은 DSL이 아니라 일반 프로그래밍 언어를 쓰기 때문에, 반복문, 조건 분기, 함수 추상화를 언어 자체 문법으로 처리한다.

Terraform을 쓰다 보면 `count`와 `for_each`로 해결 안 되는 복잡한 조건이 나오는 순간이 있다. 환경별로 리소스 구성이 완전히 달라지거나, 외부 API 호출 결과에 따라 리소스를 만들어야 하는 경우다. HCL에서 이걸 억지로 하면 코드가 읽기 어려워진다. Pulumi는 이런 상황에서 쓸만하다.

다만, 인프라 코드에 범용 언어를 쓰는 건 양날의 검이다. 자유도가 높은 만큼 팀원마다 작성 스타일이 갈리기 쉽고, 인프라 코드가 아닌 일반 애플리케이션 코드처럼 복잡해질 수 있다.

## 핵심 개념

### Stack

Stack은 동일한 Pulumi 프로그램의 독립적인 인스턴스다. 보통 환경(dev, staging, prod)별로 Stack을 나눈다.

```bash
# Stack 생성
pulumi stack init dev
pulumi stack init prod

# Stack 목록 확인
pulumi stack ls

# Stack 전환
pulumi stack select dev
```

Terraform의 workspace와 비슷하지만 차이가 있다. Terraform workspace는 같은 backend에 state를 나눠 저장하는 거고, Pulumi Stack은 각각 독립된 설정(Config)과 상태(State)를 갖는다. workspace는 환경 분리용으로 쓰지 말라는 의견이 많은데, Pulumi Stack은 처음부터 환경 분리를 목적으로 설계됐다.

### State

Pulumi도 Terraform처럼 상태 파일을 관리한다. 차이점은 기본 백엔드가 Pulumi Cloud(구 Pulumi SaaS)라는 것이다.

```bash
# 기본: Pulumi Cloud에 저장
pulumi login

# S3에 저장하려면
pulumi login s3://my-pulumi-state

# 로컬 파일로 저장
pulumi login --local
```

Pulumi Cloud를 쓰면 state 잠금, 암호화, 히스토리를 자동으로 처리해준다. 다만 무료 플랜은 리소스 수 제한이 있고, 사내 보안 정책상 외부 SaaS에 인프라 상태를 올릴 수 없는 경우가 있다. 그때는 S3 + DynamoDB 조합이나 자체 호스팅 백엔드를 쓴다.

state 파일에 민감 정보가 평문으로 들어가는 건 Terraform과 동일한 문제다. Pulumi는 기본적으로 secret 값을 state에 저장할 때 암호화한다. 이건 Terraform보다 나은 점이다.

### Config

Stack별로 설정값을 관리하는 시스템이다. `Pulumi.<stack-name>.yaml` 파일에 저장된다.

```bash
# 일반 설정값
pulumi config set aws:region ap-northeast-2
pulumi config set instanceType t3.medium

# 민감 정보 (암호화 저장)
pulumi config set --secret dbPassword 'my-secret-pw'
```

`Pulumi.dev.yaml` 파일은 이렇게 생긴다:

```yaml
config:
  aws:region: ap-northeast-2
  myproject:instanceType: t3.medium
  myproject:dbPassword:
    secure: AAABADQXFlU0MaBSkJQ...
```

`--secret` 플래그로 설정한 값은 암호화되어 저장된다. Terraform에서 `terraform.tfvars`에 비밀번호를 넣고 `.gitignore`에 추가하는 것보다 깔끔하다. Config 파일 자체를 git에 커밋해도 secret 값은 암호화되어 있다.

## TypeScript로 인프라 정의하기

### 프로젝트 시작

```bash
# 새 프로젝트 생성
pulumi new aws-typescript

# 생성되는 파일 구조
# ├── Pulumi.yaml          # 프로젝트 메타데이터
# ├── Pulumi.dev.yaml      # dev Stack 설정
# ├── index.ts             # 인프라 코드
# ├── package.json
# └── tsconfig.json
```

`Pulumi.yaml`은 프로젝트 이름과 런타임 정보를 담는다:

```yaml
name: my-infra
runtime: nodejs
description: Production infrastructure
```

### VPC + EC2 예제

```typescript
import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";

const config = new pulumi.Config();
const env = pulumi.getStack(); // "dev" 또는 "prod"

// VPC
const vpc = new aws.ec2.Vpc(`${env}-vpc`, {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
    tags: { Name: `${env}-vpc`, Environment: env },
});

// 서브넷 - 가용영역별로 생성
const azs = ["ap-northeast-2a", "ap-northeast-2c"];
const publicSubnets = azs.map((az, i) =>
    new aws.ec2.Subnet(`${env}-public-${i}`, {
        vpcId: vpc.id,
        cidrBlock: `10.0.${i}.0/24`,
        availabilityZone: az,
        mapPublicIpOnLaunch: true,
        tags: { Name: `${env}-public-${az}` },
    })
);

// Security Group
const sg = new aws.ec2.SecurityGroup(`${env}-sg`, {
    vpcId: vpc.id,
    ingress: [{
        protocol: "tcp",
        fromPort: 22,
        toPort: 22,
        cidrBlocks: [config.require("allowedSshCidr")],
    }],
    egress: [{
        protocol: "-1",
        fromPort: 0,
        toPort: 0,
        cidrBlocks: ["0.0.0.0/0"],
    }],
});

// EC2
const instance = new aws.ec2.Instance(`${env}-web`, {
    ami: "ami-0c9c942bd7bf113a2",
    instanceType: config.get("instanceType") || "t3.micro",
    subnetId: publicSubnets[0].id,
    vpcSecurityGroupIds: [sg.id],
    tags: { Name: `${env}-web` },
});

export const publicIp = instance.publicIp;
export const vpcId = vpc.id;
```

`azs.map()`으로 서브넷을 만드는 부분이 Terraform과 다른 점이다. Terraform에서는 `for_each`와 `toset()`을 조합해야 하는데, Pulumi에서는 그냥 배열 메서드를 쓰면 된다.

`export`로 내보낸 값은 `pulumi stack output`으로 조회할 수 있다. Terraform의 `output` 블록과 같은 역할이다.

### 리소스 간 의존성

Pulumi는 리소스 속성 참조만으로 의존 관계를 자동 추론한다. `subnetId: publicSubnets[0].id`라고 쓰면 서브넷이 먼저 생성된다. 명시적 의존성이 필요한 경우:

```typescript
const bucket = new aws.s3.Bucket("data", {});

// bucket이 완전히 생성된 후에 실행
const notification = new aws.s3.BucketNotification("notify", {
    bucket: bucket.id,
    lambdaFunctions: [{ lambdaFunctionArn: fn.arn, events: ["s3:ObjectCreated:*"] }],
}, { dependsOn: [lambdaPermission] }); // 명시적 의존성
```

`dependsOn`은 Terraform의 `depends_on`과 동일하다. 속성 참조로 추론할 수 없는 의존 관계에만 쓴다.

## Python으로 인프라 정의하기

```bash
pulumi new aws-python
```

같은 VPC + EC2 구성을 Python으로 작성하면:

```python
import pulumi
import pulumi_aws as aws

config = pulumi.Config()
env = pulumi.get_stack()

vpc = aws.ec2.Vpc(f"{env}-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    tags={"Name": f"{env}-vpc", "Environment": env},
)

azs = ["ap-northeast-2a", "ap-northeast-2c"]
public_subnets = []
for i, az in enumerate(azs):
    subnet = aws.ec2.Subnet(f"{env}-public-{i}",
        vpc_id=vpc.id,
        cidr_block=f"10.0.{i}.0/24",
        availability_zone=az,
        map_public_ip_on_launch=True,
        tags={"Name": f"{env}-public-{az}"},
    )
    public_subnets.append(subnet)

instance = aws.ec2.Instance(f"{env}-web",
    ami="ami-0c9c942bd7bf113a2",
    instance_type=config.get("instanceType") or "t3.micro",
    subnet_id=public_subnets[0].id,
    tags={"Name": f"{env}-web"},
)

pulumi.export("public_ip", instance.public_ip)
```

TypeScript든 Python이든 패턴은 거의 같다. 리소스 클래스 이름과 속성명이 snake_case(Python)냐 camelCase(TypeScript)냐의 차이 정도다. 팀에서 이미 쓰는 언어를 기준으로 고르면 된다.

## Terraform HCL과 비교

### 언어와 표현력

Terraform HCL은 선언적 DSL이다. 배울 건 적지만, 복잡한 로직을 표현할 때 한계가 있다.

```hcl
# Terraform: 조건에 따라 리소스 생성
resource "aws_instance" "web" {
  count = var.create_instance ? 1 : 0
  ami   = var.ami_id
  # ...
}

# 3항 연산자로 처리 가능한 수준은 괜찮다
# 하지만 이런 코드가 나오기 시작하면 문제다:
locals {
  instance_configs = {
    for env in var.environments :
    env => {
      type  = env == "prod" ? "m5.xlarge" : (env == "staging" ? "t3.large" : "t3.micro")
      count = env == "prod" ? 3 : (env == "staging" ? 2 : 1)
      monitoring = env == "prod" ? true : false
    }
  }
}
```

```typescript
// Pulumi: 같은 로직
const envConfigs: Record<string, { type: string; count: number; monitoring: boolean }> = {
    prod:    { type: "m5.xlarge", count: 3, monitoring: true },
    staging: { type: "t3.large",  count: 2, monitoring: false },
    dev:     { type: "t3.micro",  count: 1, monitoring: false },
};

const cfg = envConfigs[pulumi.getStack()];
```

중첩된 3항 연산자가 나오는 순간 HCL은 읽기 어렵다. Pulumi에서는 일반 자료구조로 표현하면 끝이다.

### 테스트

Terraform은 `terraform test`(1.6+)가 있지만 아직 성숙하지 않다. 통합 테스트는 Terratest 같은 외부 도구를 써야 한다.

Pulumi는 언어 자체의 테스트 프레임워크를 쓴다:

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as assert from "assert";

// 모의 테스트: 실제 리소스를 만들지 않고 검증
pulumi.runtime.setMocks({
    newResource: (args) => ({ id: `${args.name}-id`, state: args.inputs }),
    call: (args) => ({}),
});

describe("infrastructure", () => {
    let infra: typeof import("./index");

    before(async () => {
        infra = await import("./index");
    });

    it("EC2 인스턴스에 Name 태그가 있어야 한다", (done) => {
        pulumi.all([infra.instance.tags]).apply(([tags]) => {
            assert.ok(tags?.Name, "Name 태그가 없다");
            done();
        });
    });
});
```

실제 배포 없이 리소스 속성을 검증할 수 있다. Policy as Code(CrossGuard)로 조직 규칙을 강제하는 것도 가능하다.

### Terraform이 나은 경우

- **팀원 대부분이 HCL에 익숙할 때**: 커뮤니티, 레퍼런스, 모듈 생태계가 압도적으로 크다.
- **인프라 코드를 단순하게 유지하고 싶을 때**: HCL의 제약이 오히려 장점이다. "이 코드는 인프라 선언만 한다"는 게 명확하다.
- **State 관리를 직접 하고 싶을 때**: S3 + DynamoDB 백엔드가 검증되어 있고, `terraform state mv` 같은 state 조작 명령이 성숙하다.

### Pulumi가 나은 경우

- **복잡한 조건 분기가 많을 때**: 환경별로 리소스 구성이 크게 달라지는 경우.
- **애플리케이션 코드와 인프라 코드를 같은 언어로 관리하고 싶을 때**: 타입 공유, 같은 CI 파이프라인 사용이 가능하다.
- **동적 인프라 생성이 필요할 때**: 외부 API 응답에 따라 리소스를 만들거나, 런타임에 결정되는 값이 많은 경우.

## tf2pulumi로 마이그레이션

기존 Terraform 코드를 Pulumi로 변환하는 도구가 `tf2pulumi`(현재는 `pulumi convert`로 통합)다.

### 기본 사용법

```bash
# Terraform 프로젝트 디렉토리에서 실행
cd existing-terraform-project

# TypeScript로 변환
pulumi convert --from terraform --language typescript --out ../pulumi-project

# Python으로 변환
pulumi convert --from terraform --language python --out ../pulumi-project
```

### 변환 결과 확인

Terraform 코드가 이렇다면:

```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
  tags   = { Environment = "prod" }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

변환된 TypeScript 코드:

```typescript
import * as aws from "@pulumi/aws";

const dataBucket = new aws.s3.Bucket("data", {
    bucket: "my-data-bucket",
    tags: { Environment: "prod" },
});

const dataVersioning = new aws.s3.BucketVersioningV2("data", {
    bucket: dataBucket.id,
    versioningConfiguration: { status: "Enabled" },
});
```

### 마이그레이션 시 주의사항

**State 가져오기가 핵심이다.** 코드만 변환하면 Pulumi는 기존 리소스를 모르기 때문에 새로 만들려고 한다. 기존 리소스를 Pulumi State에 등록해야 한다:

```bash
# 기존 리소스를 Pulumi State에 import
pulumi import aws:s3/bucket:Bucket data my-data-bucket
pulumi import aws:s3/bucketVersioningV2:BucketVersioningV2 data my-data-bucket
```

리소스가 수십 개 이상이면 import를 하나씩 하는 게 고통스럽다. bulk import JSON 파일을 만들어서 한 번에 처리할 수 있다:

```json
{
    "resources": [
        {
            "type": "aws:s3/bucket:Bucket",
            "name": "data",
            "id": "my-data-bucket"
        },
        {
            "type": "aws:ec2/instance:Instance",
            "name": "web",
            "id": "i-0abc123def456"
        }
    ]
}
```

```bash
pulumi import --file resources.json
```

**점진적 마이그레이션을 권장한다.** 한 번에 전체를 옮기면 문제가 생겼을 때 원인을 찾기 어렵다. 새로 만드는 인프라부터 Pulumi로 작성하고, 기존 Terraform 리소스는 `pulumi import`로 하나씩 옮기는 게 안전하다. 마이그레이션 중에는 두 도구의 state가 같은 리소스를 동시에 관리하지 않도록 주의한다. Terraform에서 `terraform state rm`으로 해당 리소스를 state에서 제거한 뒤, Pulumi에서 import하는 순서로 진행한다.

## 복잡한 조건 분기가 필요할 때

Pulumi가 Terraform보다 편한 구체적인 사례들이다.

### 환경별 완전히 다른 아키텍처

dev는 단일 인스턴스, staging은 ALB + ASG, prod는 ALB + ASG + CloudFront 구성이라고 하자.

```typescript
import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";

const env = pulumi.getStack();

// 공통: VPC는 모든 환경에 필요
const vpc = new aws.ec2.Vpc(`${env}-vpc`, {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
});

if (env === "dev") {
    // dev: EC2 하나
    const instance = new aws.ec2.Instance(`${env}-app`, {
        ami: "ami-0c9c942bd7bf113a2",
        instanceType: "t3.micro",
        subnetId: subnet.id,
    });
} else {
    // staging, prod: ALB + Auto Scaling Group
    const alb = new aws.lb.LoadBalancer(`${env}-alb`, {
        loadBalancerType: "application",
        subnets: publicSubnets.map(s => s.id),
    });

    const asg = new aws.autoscaling.Group(`${env}-asg`, {
        minSize: env === "prod" ? 3 : 1,
        maxSize: env === "prod" ? 10 : 3,
        desiredCapacity: env === "prod" ? 3 : 1,
        vpcZoneIdentifiers: privateSubnets.map(s => s.id),
    });

    if (env === "prod") {
        // prod만: CloudFront
        const cdn = new aws.cloudfront.Distribution(`${env}-cdn`, {
            origins: [{
                domainName: alb.dnsName,
                originId: "alb",
                customOriginConfig: {
                    httpPort: 80,
                    httpsPort: 443,
                    originProtocolPolicy: "https-only",
                    originSslProtocols: ["TLSv1.2"],
                },
            }],
            enabled: true,
            defaultCacheBehavior: {
                allowedMethods: ["GET", "HEAD"],
                cachedMethods: ["GET", "HEAD"],
                targetOriginId: "alb",
                viewerProtocolPolicy: "redirect-to-https",
                forwardedValues: { queryString: false, cookies: { forward: "none" } },
            },
            restrictions: { geoRestriction: { restrictionType: "none" } },
            viewerCertificate: { cloudfrontDefaultCertificate: true },
        });
    }
}
```

Terraform에서 이걸 하려면 `count`로 리소스 존재 여부를 제어하고, 참조할 때마다 `aws_instance.web[0]`처럼 인덱스를 붙여야 한다. 리소스가 많아지면 `count = var.env == "prod" ? 1 : 0`이 파일 전체에 흩어진다.

### 외부 데이터에 따른 동적 리소스 생성

설정 파일이나 외부 소스에서 읽은 데이터로 리소스를 만드는 경우:

```typescript
import * as fs from "fs";
import * as aws from "@pulumi/aws";
import * as yaml from "js-yaml";

// YAML 파일에서 서비스 목록을 읽어서 각각 리소스를 생성
interface ServiceConfig {
    name: string;
    port: number;
    cpu: number;
    memory: number;
    healthCheckPath: string;
}

const services: ServiceConfig[] = yaml.load(
    fs.readFileSync("services.yaml", "utf8")
) as ServiceConfig[];

for (const svc of services) {
    const taskDef = new aws.ecs.TaskDefinition(`${svc.name}-task`, {
        family: svc.name,
        cpu: String(svc.cpu),
        memory: String(svc.memory),
        networkMode: "awsvpc",
        requiresCompatibilities: ["FARGATE"],
        containerDefinitions: JSON.stringify([{
            name: svc.name,
            image: `${accountId}.dkr.ecr.ap-northeast-2.amazonaws.com/${svc.name}:latest`,
            portMappings: [{ containerPort: svc.port }],
            healthCheck: {
                command: ["CMD-SHELL", `curl -f http://localhost:${svc.port}${svc.healthCheckPath} || exit 1`],
                interval: 30,
                timeout: 5,
                retries: 3,
            },
        }]),
    });

    const service = new aws.ecs.Service(`${svc.name}-service`, {
        cluster: cluster.arn,
        taskDefinition: taskDef.arn,
        desiredCount: 2,
        launchType: "FARGATE",
        networkConfiguration: {
            subnets: privateSubnets.map(s => s.id),
            securityGroups: [sg.id],
        },
    });
}
```

`services.yaml`에 서비스를 추가하면 ECS Task Definition과 Service가 자동으로 생긴다. Terraform에서도 `for_each`와 `yamldecode()`로 비슷한 걸 할 수 있지만, JSON 문자열 조립이나 중첩 구조 처리에서 코드가 지저분해진다.

## 실행 흐름

```bash
# 변경사항 미리보기 (terraform plan에 해당)
pulumi preview

# 배포 (terraform apply에 해당)
pulumi up

# 리소스 삭제 (terraform destroy에 해당)
pulumi destroy

# 특정 리소스만 갱신
pulumi up --target urn:pulumi:dev::myproject::aws:ec2/instance:Instance::dev-web
```

`pulumi up`을 실행하면 변경사항을 보여주고 확인을 받는다. `--yes` 플래그를 붙이면 확인 없이 바로 적용하는데, CI/CD에서만 쓴다. 로컬에서는 반드시 미리보기를 확인한다.

## 실무에서 주의할 점

**리소스 이름은 고유해야 한다.** Pulumi에서 첫 번째 인자가 논리적 이름인데, 같은 이름을 두 번 쓰면 에러가 난다. Stack 이름을 prefix로 붙이는 습관을 들이면 환경 간 충돌을 피할 수 있다.

**Output 타입을 이해해야 한다.** `vpc.id`는 `string`이 아니라 `Output<string>`이다. 리소스가 실제로 생성되기 전에는 값을 알 수 없기 때문이다. Output 값을 가공하려면 `apply()`를 써야 한다:

```typescript
const bucketUrl = bucket.bucket.apply(name => `https://${name}.s3.amazonaws.com`);

// 여러 Output을 조합할 때
const connectionString = pulumi.interpolate
    `postgresql://${dbUser}:${dbPassword}@${db.endpoint}/${dbName}`;
```

`pulumi.interpolate`는 Output 값이 포함된 문자열을 만들 때 쓴다. 일반 템플릿 리터럴로는 `Output<string>`을 직접 쓸 수 없다.

**ComponentResource로 추상화한다.** 여러 리소스를 묶어서 재사용 가능한 컴포넌트를 만들 수 있다:

```typescript
class VpcComponent extends pulumi.ComponentResource {
    public readonly vpcId: pulumi.Output<string>;
    public readonly publicSubnetIds: pulumi.Output<string>[];

    constructor(name: string, args: VpcArgs, opts?: pulumi.ComponentResourceOptions) {
        super("custom:network:Vpc", name, {}, opts);

        const vpc = new aws.ec2.Vpc(`${name}-vpc`, {
            cidrBlock: args.cidrBlock,
            enableDnsHostnames: true,
        }, { parent: this });

        this.vpcId = vpc.id;
        // ... 서브넷, 라우트 테이블 등

        this.registerOutputs({ vpcId: this.vpcId });
    }
}

// 사용
const network = new VpcComponent("prod", {
    cidrBlock: "10.0.0.0/16",
});
```

Terraform의 module과 같은 역할이다. 차이점은 클래스 상속, 인터페이스 구현 같은 OOP 패턴을 쓸 수 있다는 것이다. 다만 과도한 추상화는 인프라 코드를 읽기 어렵게 만든다. 2~3단계 이상 상속이 들어가면 무슨 리소스가 만들어지는지 추적하기 어려워진다.
