---
title: Packer로 이미지 빌드하기
tags:
  - infra
  - packer
  - image
  - ami
  - docker
  - golden-image
updated: 2026-06-23
---

# Packer로 이미지 빌드하기

## Packer를 쓰게 된 배경

처음 AWS에 서비스를 올렸을 땐 EC2 인스턴스를 띄우고 SSH로 들어가 패키지를 설치하고, nginx 설정 올리고, 애플리케이션 배포하고, 그 인스턴스에서 AMI를 떠서 그걸로 오토스케일링 그룹을 굴렸다. 문제는 6개월쯤 지나면 그 AMI가 어떻게 만들어졌는지 아무도 기억을 못 한다는 것이다. 누가 SSH로 들어가서 뭘 깔았는지 기록이 없으니, 새 베이스 이미지로 갈아탈 때마다 같은 작업을 손으로 반복하고 매번 미묘하게 다른 결과가 나온다.

Packer는 이 과정을 코드로 박제하는 도구다. HCL 템플릿에 "이 베이스 이미지에서 시작해서, 이 인스턴스 타입으로 임시 인스턴스를 띄우고, 이 스크립트들을 실행한 뒤, 그 결과를 AMI로 떠라"를 적어두면 `packer build` 한 번으로 항상 같은 절차를 밟는다. 손으로 만든 AMI와 달리 빌드 과정이 git에 남고, 리뷰가 되고, CI에서 자동으로 돌릴 수 있다.

한 가지 먼저 짚어둘 것은 Packer가 만드는 건 "이미지"라는 점이다. 인프라를 띄우거나 상태를 관리하는 도구가 아니다. 이 경계가 흐려지면 Packer 안에서 Terraform이 할 일을 하려다 꼬인다. 역할 분담 얘기는 뒤에서 다시 한다.

## HCL 템플릿 구조

Packer 1.7부터 HCL2가 정식 포맷이 됐다. 예전 JSON 템플릿은 지금도 동작하지만 신규 작성이면 HCL2를 쓴다. JSON은 주석을 못 달고 변수 표현이 빈약해서 템플릿이 커지면 금방 읽기 힘들어진다.

템플릿은 크게 네 개의 블록으로 나뉜다.

- `packer` 블록: 필요한 플러그인과 버전 제약을 선언한다.
- `source` 블록: 어떤 베이스에서 시작해 어떤 임시 머신을 띄울지 정의한다. 예전 용어로 builder다.
- `build` 블록: 어떤 source를 쓸지 고르고, 그 위에서 돌릴 provisioner와 빌드 후 처리할 post-processor를 묶는다.
- `variable` / `locals`: 변수 선언과 계산된 값.

가장 단순한 AMI 빌드 템플릿은 이렇게 생겼다.

```hcl
packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = ">= 1.2.0"
    }
  }
}

variable "app_version" {
  type    = string
  default = "dev"
}

locals {
  timestamp = formatdate("YYYYMMDD-hhmmss", timestamp())
}

source "amazon-ebs" "app" {
  region        = "ap-northeast-2"
  instance_type = "t3.medium"
  ssh_username  = "ubuntu"

  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
      virtualization-type = "hvm"
      root-device-type    = "ebs"
    }
    owners      = ["099720109477"] # Canonical
    most_recent = true
  }

  ami_name = "app-${var.app_version}-${local.timestamp}"

  tags = {
    Name       = "app-${var.app_version}"
    AppVersion = var.app_version
    BuildTime  = local.timestamp
    BaseAMI    = "{{ .SourceAMI }}"
  }
}

build {
  sources = ["source.amazon-ebs.app"]

  provisioner "shell" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get install -y nginx",
    ]
  }
}
```

여기서 `source_ami_filter`를 쓰는 부분을 눈여겨봐야 한다. AMI ID를 하드코딩하면 Canonical이 새 패치를 낸 베이스로 갱신할 때마다 템플릿을 고쳐야 한다. 필터에 `most_recent = true`를 주면 빌드 시점의 최신 Ubuntu 22.04 베이스를 자동으로 잡는다. 다만 이건 양날의 검이다. 베이스가 바뀌면 같은 템플릿으로 빌드해도 결과 AMI가 달라진다. 완전한 재현성이 필요하면 베이스 AMI ID를 변수로 고정하고, 베이스 갱신은 별도 단계로 명시적으로 관리한다.

`ami_name`에 타임스탬프를 넣은 이유는 AMI 이름이 리전 내에서 유일해야 하기 때문이다. 같은 이름으로 두 번 빌드하면 충돌이 난다. 타임스탬프나 빌드 번호를 붙여 매번 다른 이름이 나오게 한다.

## builder, provisioner, post-processor

세 단계가 빌드의 뼈대다.

builder(HCL2에서는 source)는 임시 머신을 만든다. `amazon-ebs`는 EC2 인스턴스를 띄우고, `docker`는 컨테이너를 띄우고, `googlecompute`는 GCE 인스턴스를 띄운다. 빌드가 끝나면 임시 머신은 자동으로 정리된다. 빌드 중간에 실패하면 임시 인스턴스가 남아 비용이 새는 경우가 있으니, 실패가 잦은 초기엔 콘솔에서 한 번씩 확인하는 게 좋다.

provisioner는 그 임시 머신 안에서 실제 작업을 한다. 패키지 설치, 파일 복사, 설정 적용이 전부 여기서 일어난다. 종류가 여러 개다.

```hcl
build {
  sources = ["source.amazon-ebs.app"]

  # 파일을 임시 머신으로 올린다
  provisioner "file" {
    source      = "files/nginx.conf"
    destination = "/tmp/nginx.conf"
  }

  # 셸 스크립트를 실행한다
  provisioner "shell" {
    scripts = [
      "scripts/install-deps.sh",
      "scripts/setup-app.sh",
    ]
    # 셸 변수를 넘긴다
    environment_vars = [
      "APP_VERSION=${var.app_version}",
    ]
  }

  # 위에서 올린 파일을 제자리로 옮긴다
  provisioner "shell" {
    inline = [
      "sudo mv /tmp/nginx.conf /etc/nginx/nginx.conf",
      "sudo systemctl enable nginx",
    ]
  }
}
```

`file` provisioner로 직접 `/etc/nginx/`에 못 쓰는 이유는 SSH 사용자에게 그 경로 쓰기 권한이 없어서다. `/tmp`에 올린 뒤 셸로 `sudo mv` 하는 패턴을 자주 쓴다.

post-processor는 빌드 산출물을 후처리한다. Docker 이미지를 레지스트리에 푸시하거나, 빌드 결과의 메타데이터를 manifest 파일로 떨군다. AMI 빌드에선 manifest를 많이 쓴다.

```hcl
build {
  sources = ["source.amazon-ebs.app"]

  provisioner "shell" {
    inline = ["echo provisioning"]
  }

  post-processor "manifest" {
    output     = "manifest.json"
    strip_path = true
  }
}
```

`manifest.json`에 방금 만든 AMI ID가 적힌다. CI에서 이 파일을 파싱해 다음 단계(Terraform 배포 등)로 AMI ID를 넘기는 식으로 쓴다. 빌드와 배포를 잇는 다리 역할을 한다.

## AMI 빌드 실전

빌드 명령은 단순하다.

```bash
# 문법 검증과 포맷
packer fmt .
packer validate .

# 플러그인 설치 (required_plugins 기준)
packer init .

# 변수를 넘겨 빌드
packer build -var "app_version=1.4.2" .
```

`packer init`을 빼먹고 바로 `build`를 돌리면 플러그인을 못 찾는다고 멈춘다. 새 환경에서 처음 돌릴 땐 init부터 한다.

실무에서 부딪히는 문제 몇 가지가 있다.

빌드가 SSH 연결에서 멈추는 경우가 가장 흔하다. Packer가 임시 인스턴스를 띄우고 SSH로 붙으려는데 보안 그룹이 22번 포트를 막고 있으면 타임아웃까지 기다리다 죽는다. Packer가 임시로 만드는 보안 그룹은 기본적으로 자기 IP에서의 SSH를 열지만, VPC 라우팅이나 NACL이 막혀 있으면 안 된다. `-debug` 플래그를 붙이면 단계마다 멈추면서 임시 인스턴스 정보를 보여주니 직접 SSH를 시도해 어디서 막히는지 확인할 수 있다.

```bash
packer build -debug -var "app_version=1.4.2" .
```

`-debug`는 각 provisioner 실행 전에 엔터를 기다린다. 이때 콘솔에서 임시 인스턴스에 직접 들어가 상태를 보고, 문제 구간을 좁힌다. 빌드가 30분쯤 걸리는 무거운 이미지에서 마지막 단계가 실패할 때 이 기능이 시간을 많이 아껴준다.

또 하나는 apt 락 충돌이다. 갓 부팅한 Ubuntu는 `unattended-upgrades`가 백그라운드에서 apt를 잡고 있어서, provisioner의 `apt-get install`이 락을 못 얻고 실패한다. 이걸 피하려면 설치 전에 락이 풀릴 때까지 기다리는 단계를 넣는다.

```bash
# scripts/wait-apt.sh
while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
  echo "waiting for apt lock..."
  sleep 5
done
```

## Docker 이미지 빌드

Packer로 Docker 이미지도 만든다. Dockerfile을 쓰는 게 보통이지만, 이미 Ansible 플레이북으로 서버 구성을 관리하고 있다면 같은 플레이북을 컨테이너 이미지에도 재사용할 수 있어 Packer의 docker builder가 쓸모 있다.

```hcl
packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = ">= 1.0.0"
    }
  }
}

source "docker" "app" {
  image  = "ubuntu:22.04"
  commit = true
  changes = [
    "ENTRYPOINT [\"/usr/local/bin/app\"]",
    "EXPOSE 8080",
  ]
}

build {
  sources = ["source.docker.app"]

  provisioner "shell" {
    inline = [
      "apt-get update",
      "apt-get install -y ca-certificates",
    ]
  }

  post-processor "docker-tag" {
    repository = "registry.example.com/app"
    tags       = ["1.4.2", "latest"]
  }
  post-processor "docker-push" {
    login          = true
    login_server   = "registry.example.com"
    login_username = "ci"
    login_password = "${var.registry_password}"
  }
}
```

`commit = true`는 컨테이너 상태를 그대로 이미지로 커밋한다는 뜻이다. `changes`로 ENTRYPOINT나 EXPOSE 같은 메타데이터를 덧붙인다. post-processor 두 개를 연달아 쓴 부분을 보면, `docker-tag`로 태그를 붙이고 `docker-push`로 레지스트리에 올린다. 순서대로 체인처럼 흐른다.

솔직히 컨테이너 이미지만 만들 거라면 그냥 Dockerfile이 낫다. 레이어 캐싱, 멀티스테이지 빌드 같은 Docker 생태계의 도구가 다 갖춰져 있다. Packer의 docker builder가 빛나는 건 AMI와 컨테이너를 같은 provisioner 코드로 함께 만들고 싶을 때다. 베어메탈/VM과 컨테이너에 동일한 구성을 보장해야 하는 경우가 그렇다.

## Ansible provisioner 연동

셸 스크립트가 길어지면 멱등성이나 에러 처리가 엉성해진다. 이미 Ansible로 서버 구성을 관리하고 있다면 같은 플레이북을 Packer 빌드에 그대로 끌어쓸 수 있다.

```hcl
build {
  sources = ["source.amazon-ebs.app"]

  provisioner "ansible" {
    playbook_file = "ansible/site.yml"
    extra_arguments = [
      "--extra-vars", "app_version=${var.app_version}",
    ]
    ansible_env_vars = [
      "ANSIBLE_HOST_KEY_CHECKING=False",
    ]
  }
}
```

Packer의 ansible provisioner는 로컬에 설치된 ansible을 임시 인스턴스를 대상으로 실행한다. 즉 빌드를 돌리는 머신(보통 CI 러너)에 ansible이 깔려 있어야 한다. 컨테이너 빌드에서 ansible을 쓸 땐 SSH가 아니라 다른 연결 방식이 필요하니 `ansible-local` provisioner를 쓰는 편이 덜 번거롭다. `ansible-local`은 플레이북을 임시 머신 안으로 복사한 뒤 그 안에서 ansible을 돌린다.

운영 서버에 ansible을 직접 돌려 구성을 바꾸던 방식에서 Packer로 옮기면, 구성 적용 시점이 "배포 때마다"에서 "이미지 빌드 때 한 번"으로 바뀐다. 런타임에 ansible이 도는 시간이 사라지니 인스턴스 부팅이 빨라지고, 부팅 중 외부 패키지 저장소가 죽어서 스케일아웃이 실패하는 사고도 막힌다. 이게 골든 이미지로 넘어가는 핵심 동기다.

## Terraform과의 역할 분담

여기서 자주 헷갈린다. Packer와 Terraform은 둘 다 HashiCorp 도구고 HCL을 쓰지만 하는 일이 다르다.

Packer는 이미지를 만든다. "이 서버에 무엇이 설치돼 있어야 하는가"를 책임진다.

Terraform은 인프라를 띄운다. "그 이미지로 인스턴스 몇 대를 어떤 네트워크에 어떻게 배치하는가"를 책임진다.

경계는 명확하다. 디스크 안에 박제되는 건 Packer가, 인스턴스 바깥의 배치는 Terraform이 맡는다. nginx 바이너리와 애플리케이션 코드는 이미지에 굽고(Packer), 오토스케일링 그룹·로드밸런서·보안 그룹·VPC는 Terraform이 만든다.

둘을 잇는 게 AMI ID다. Packer가 manifest.json에 AMI ID를 떨구면 Terraform이 그걸 읽어 launch template에 꽂는다.

```hcl
# Terraform 쪽
data "aws_ami" "app" {
  most_recent = true
  owners      = ["self"]
  filter {
    name   = "name"
    values = ["app-1.4.2-*"]
  }
}

resource "aws_launch_template" "app" {
  image_id      = data.aws_ami.app.id
  instance_type = "t3.medium"
}
```

이렇게 Terraform이 AMI 이름 패턴으로 최신 이미지를 찾아 쓰게 하면, 새 이미지를 빌드한 뒤 `terraform apply`만으로 launch template이 갱신된다.

흔한 안티패턴은 Packer provisioner 안에서 인스턴스의 런타임 설정(특정 IP, 특정 DB 엔드포인트)을 굽는 것이다. 그러면 이미지가 환경에 묶여 재사용이 안 된다. 환경별로 달라지는 값은 부팅 시 user-data나 외부 설정 저장소(파라미터 스토어, Consul)에서 주입한다. 이미지에는 환경 무관한 것만 굽는다는 원칙을 지킨다.

## 빌드 캐싱과 CI 파이프라인 통합

Packer는 Docker처럼 레이어 캐시가 있는 게 아니라서, 매 빌드가 베이스 이미지에서 처음부터 다시 시작한다. 무거운 의존성을 매번 다운로드하면 빌드가 느리다. 캐싱 방법이 몇 가지 있다.

베이스 이미지를 계층화하는 방법이 가장 효과 좋다. 자주 안 바뀌는 OS 패키지와 런타임(JDK, Node 등)을 깐 "베이스 골든 이미지"를 따로 빌드해두고, 애플리케이션 이미지는 그 위에서 시작한다. 그러면 애플리케이션만 바뀌는 잦은 빌드는 무거운 설치를 건너뛴다.

```hcl
# 애플리케이션 이미지는 미리 만든 베이스를 source_ami로 받는다
variable "base_ami" {
  type = string
}

source "amazon-ebs" "app" {
  source_ami    = var.base_ami
  instance_type = "t3.medium"
  # ...
}
```

CI 파이프라인에 넣을 땐 단계를 나눈다.

```yaml
# GitHub Actions 예시
jobs:
  build-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-packer@v3
      - name: packer init
        run: packer init .
      - name: validate
        run: packer validate -var "app_version=${{ github.sha }}" .
      - name: build
        run: packer build -var "app_version=${{ github.sha }}" .
      - name: capture AMI id
        run: |
          AMI_ID=$(jq -r '.builds[-1].artifact_id' manifest.json | cut -d: -f2)
          echo "ami_id=$AMI_ID" >> "$GITHUB_OUTPUT"
        id: ami
```

`manifest.json`을 jq로 파싱해 AMI ID를 뽑아 다음 잡으로 넘기는 흐름이 핵심이다. `artifact_id`는 `리전:AMI-ID` 형태라 `cut`으로 ID만 잘라낸다.

CI에서 돌릴 때 자격증명은 IAM 역할로 넘긴다. AWS 액세스 키를 템플릿에 박지 않는다. GitHub Actions라면 OIDC로 AWS 역할을 assume 하게 설정하고, Packer는 환경의 자격증명을 알아서 집어 쓴다. 빌드 권한은 EC2 인스턴스 생성/종료, AMI 생성, 임시 보안 그룹 관리 정도로 좁힌다.

빌드 시간이 길어 CI가 자주 타임아웃되면, 야간에 베이스 이미지를 미리 빌드해두는 스케줄 잡을 따로 두는 게 도움이 된다. 잦은 애플리케이션 빌드는 가벼운 베이스 위에서만 돌게 만든다.

## 골든 이미지 운영

골든 이미지는 "검증된, 그대로 찍어내는 표준 이미지"를 말한다. 운영하다 보면 챙겨야 할 게 몇 가지 있다.

버전 관리가 첫째다. AMI 이름과 태그에 빌드한 커밋 SHA나 시맨틱 버전을 반드시 박는다. 장애가 났을 때 "지금 도는 이미지가 어느 커밋으로 만들어졌나"를 추적할 수 있어야 롤백이 가능하다. 앞 예제에서 태그에 `AppVersion`, `BuildTime`, `BaseAMI`를 넣은 게 그래서다. 특히 `BaseAMI`(어느 OS 베이스에서 출발했는지)를 기록해두면 OS 레벨 취약점이 터졌을 때 영향받는 이미지를 한 번에 가려낸다.

오래된 AMI 정리도 필요하다. 빌드를 매일 돌리면 AMI와 그에 딸린 EBS 스냅샷이 쌓여 비용이 샌다. 보존 정책을 정해(예: 최근 10개와 운영 중인 것만 유지) 주기적으로 청소하는 람다나 스크립트를 둔다. 단, 현재 launch template이 참조하는 AMI는 절대 지우면 안 된다. 스케일아웃이 그 순간 깨진다.

이미지 빌드가 실패했을 때의 디버깅은 `-debug`가 기본이고, 여기에 `-on-error` 옵션을 더한다.

```bash
# 실패 시 임시 인스턴스를 정리하지 않고 남긴다
packer build -on-error=ask -var "app_version=1.4.2" .
```

`-on-error=ask`는 빌드 실패 시 임시 인스턴스를 지울지 물어본다. `cleanup`(기본, 바로 정리), `abort`, `ask` 중 고를 수 있다. `ask`로 두면 실패한 인스턴스를 살려두고 SSH로 들어가 로그를 직접 까볼 수 있다. provisioner 마지막 단계에서 알 수 없는 이유로 실패할 때, 정리돼버린 인스턴스로는 원인을 못 찾으니 이 옵션이 사실상 필수다. 다만 디버깅 끝나면 남은 인스턴스를 손으로 꼭 종료해야 한다. 잊으면 비용이 샌다.

마지막으로 골든 이미지는 정기적으로 재빌드해야 한다. 베이스 OS의 보안 패치가 누적되는데 이미지를 몇 달째 안 갈면 그만큼 취약점을 안고 도는 셈이다. 코드 변경이 없어도 주기적으로(예: 주 1회) 최신 베이스로 재빌드해 패치를 흡수하고, 그 이미지로 인스턴스를 교체(immutable 방식)하는 운영이 안전하다. 살아있는 인스턴스에 패치를 직접 거는 방식으로 돌아가면, 결국 다시 "이 서버에 뭐가 깔렸는지 모르는" 상태로 회귀한다.
