---
title: CI/CD 파이프라인 Zero Trust 적용
tags: [security, ci-cd, auth, aws]
updated: 2026-07-27
---

# CI/CD 파이프라인 Zero Trust 적용

## 왜 파이프라인이 공격 대상이 되는가

CI/CD 파이프라인은 코드 저장소부터 프로덕션까지 연결되는 경로다. 이 경로가 뚫리면 공격자는 코드 변조나 시크릿 탈취 없이도 프로덕션 환경에 접근할 수 있다. 파이프라인 자체가 신뢰받는 실행자이기 때문이다.

실제로 2020년 SolarWinds 침해가 그 구조였다. 빌드 파이프라인에 악성 코드를 주입해서 배포된 소프트웨어 자체를 오염시켰다. CircleCI도 2023년 초에 내부 시스템 침해로 파이프라인에 등록된 시크릿들이 대규모로 유출됐다. 피해를 받은 팀들의 공통점은 하나였다. 파이프라인을 신뢰받는 내부 시스템으로 취급했고, 거기 등록된 자격증명은 유효기간 없이 장기간 유지되고 있었다.

Zero Trust를 파이프라인에 적용한다는 건 크게 세 가지를 바꾸는 일이다. 장기 자격증명을 단기 토큰으로 교체하고, 파이프라인 단계마다 권한을 분리하고, 빌드 컨텍스트(어느 브랜치, 누가 트리거)에 따라 접근 가능한 리소스를 다르게 제한하는 것이다.

---

## GitHub Actions OIDC로 AWS 장기 자격증명 제거

파이프라인에서 AWS 자격증명을 다루는 전통적인 방식은 IAM 사용자를 만들고, 액세스 키를 발급해서 GitHub Secrets에 등록하는 것이다. 이 방식의 문제는 액세스 키가 유출되면 즉각 피해로 이어진다는 게 아니다. 실제 문제는 이 키가 몇 달, 몇 년씩 교체되지 않고 살아있다는 것이다. 만료 메커니즘이 없고, 누가 언제 어디서 사용했는지 추적하기 어렵고, Secrets에 등록된 값은 로그에 마스킹되지만 파이프라인 내부에서는 평문으로 존재한다.

GitHub Actions OIDC 페더레이션은 이 문제를 구조적으로 해결한다. 파이프라인이 실행될 때 GitHub이 OIDC 토큰을 발급하고, AWS는 그 토큰을 검증해서 임시 자격증명(STS AssumeRoleWithWebIdentity)을 돌려준다. 임시 자격증명은 기본 1시간 유효하고, 파이프라인이 끝나면 쓸모없어진다.

### AWS 측 설정

먼저 AWS에 GitHub OIDC 프로바이더를 등록한다.

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

그 다음 파이프라인이 AssumeRole할 IAM 역할을 만든다. 신뢰 정책에서 어느 리포지토리, 어느 브랜치에서만 이 역할을 가정할 수 있는지 명시한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

`sub` 조건이 핵심이다. `repo:myorg/myrepo:ref:refs/heads/main`으로 제한하면 main 브랜치 워크플로우만 이 역할을 가정할 수 있다. PR 빌드나 feature 브랜치에서는 이 역할 자체에 접근할 수 없다.

배포 역할과 빌드 역할을 분리해야 한다면 역할을 두 개 만든다. 배포 역할은 `ref:refs/heads/main`으로 제한하고, 빌드/테스트 역할은 `ref:refs/pull/*`까지 허용하되 권한을 읽기 전용으로 묶는다.

### GitHub Actions 워크플로우

```yaml
name: deploy

on:
  push:
    branches: [main]

permissions:
  id-token: write   # OIDC 토큰 발급에 필요
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy-role
          aws-region: ap-northeast-2
          role-session-name: github-actions-${{ github.run_id }}

      - name: Deploy
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
          # 이후 배포 로직
```

`role-session-name`에 `github.run_id`를 넣으면 CloudTrail에서 어느 워크플로우 실행이 어떤 AWS 작업을 했는지 추적할 수 있다.

### OIDC 토큰에 담기는 클레임

GitHub OIDC 토큰에는 파이프라인 컨텍스트 정보가 클레임으로 들어간다.

```
{
  "sub": "repo:myorg/myrepo:ref:refs/heads/main",
  "repository": "myorg/myrepo",
  "repository_owner": "myorg",
  "workflow": "deploy",
  "ref": "refs/heads/main",
  "sha": "abc123...",
  "event_name": "push",
  "job_workflow_ref": "myorg/myrepo/.github/workflows/deploy.yml@refs/heads/main",
  "runner_environment": "github-hosted"
}
```

AWS 신뢰 정책에서 `Condition`으로 이 클레임들을 조합해서 접근 제어 조건을 정밀하게 설정할 수 있다. `event_name`이 `push`인 경우만 허용한다거나, `runner_environment`가 `github-hosted`인 경우만 허용하는 식이다.

---

## HashiCorp Vault AppRole과 단기 토큰 시크릿 주입

AWS 자격증명은 OIDC로 해결했지만, DB 패스워드, API 키, 외부 서비스 시크릿 같은 다른 자격증명들은 별도로 처리해야 한다. Vault AppRole은 파이프라인이 Vault에 인증해서 단기 시크릿을 받아가는 방식이다.

AppRole 인증은 RoleID(누구인지)와 SecretID(비밀번호)를 조합한다. RoleID는 공개해도 되는 식별자고, SecretID가 실제 인증 수단이다. SecretID를 단기 발급(use-limit, ttl 설정)하면 파이프라인 한 번 실행에만 유효한 SecretID를 사용할 수 있다.

### Vault AppRole 설정

```bash
# AppRole 인증 활성화
vault auth enable approle

# 파이프라인용 역할 생성
vault write auth/approle/role/cicd-deploy \
    secret_id_ttl=10m \
    secret_id_num_uses=1 \
    token_ttl=30m \
    token_max_ttl=60m \
    policies=cicd-deploy-policy

# RoleID 조회 (배포 인프라에 고정)
vault read auth/approle/role/cicd-deploy/role-id

# SecretID 발급 (파이프라인 실행마다 새로 발급)
vault write -f auth/approle/role/cicd-deploy/secret-id
```

`secret_id_num_uses=1`이 핵심이다. SecretID 하나를 한 번만 사용할 수 있게 만들면, 설령 SecretID가 로그에 노출되더라도 이미 사용된 뒤라면 재사용이 불가능하다.

### 파이프라인에서 Vault 연동

파이프라인 실행 시 SecretID를 파이프라인 외부(별도 인프라 또는 Vault 자체의 신뢰 체계)에서 발급해서 주입하는 구조가 이상적이다. 하지만 그 체계가 없다면 GitHub Secrets에 RoleID와 SecretID 발급용 제한된 토큰만 넣고, 실행 중에 SecretID를 발급받는 방식을 쓴다.

```yaml
- name: Fetch secrets from Vault
  env:
    VAULT_ADDR: https://vault.internal.example.com
    VAULT_ROLE_ID: ${{ secrets.VAULT_ROLE_ID }}
    VAULT_SECRET_ID: ${{ secrets.VAULT_SECRET_ID }}
  run: |
    # AppRole로 Vault 인증
    VAULT_TOKEN=$(vault write -field=token auth/approle/login \
      role_id="$VAULT_ROLE_ID" \
      secret_id="$VAULT_SECRET_ID")

    # 단기 토큰으로 시크릿 조회
    DB_PASSWORD=$(VAULT_TOKEN=$VAULT_TOKEN vault kv get \
      -field=password secret/prod/database)

    # 환경변수로만 노출 (파일 시스템에 쓰지 않음)
    echo "::add-mask::$DB_PASSWORD"
    echo "DB_PASSWORD=$DB_PASSWORD" >> $GITHUB_ENV
```

`::add-mask::` 지시어로 이후 로그에서 해당 값을 마스킹한다. 파일 시스템에 시크릿을 쓰지 않고 환경변수로만 전달하면 빌드 아티팩트나 컨테이너 레이어에 시크릿이 남지 않는다.

### Vault 정책 설계

시크릿 접근 정책도 파이프라인 역할별로 분리해야 한다.

```hcl
# cicd-build-policy: 빌드 단계용 (읽기 전용, 빌드 관련 시크릿만)
path "secret/data/cicd/build/*" {
  capabilities = ["read"]
}

# cicd-deploy-policy: 배포 단계용 (프로덕션 시크릿 읽기)
path "secret/data/prod/*" {
  capabilities = ["read"]
}

# 프로덕션 시크릿에 대한 쓰기 권한은 파이프라인에서 완전히 제외
path "secret/data/prod/*" {
  capabilities = []
}
```

빌드 정책과 배포 정책을 다른 AppRole에 매핑하면, 빌드 잡이 탈취되더라도 배포용 시크릿에는 접근할 수 없다.

---

## 파이프라인 단계별 최소 권한 분리

빌드 단계와 배포 단계를 같은 잡에서 같은 권한으로 실행하는 경우가 많다. 이 구조에서는 빌드 단계에 공급망 공격이 들어오면 배포 권한까지 함께 탈취된다.

단계를 분리하면 이 공격 경로를 끊을 수 있다.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      packages: write  # 컨테이너 레지스트리 푸시용
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS (build role - ECR push only)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-build-role
          aws-region: ap-northeast-2

      - name: Build and push image
        id: build
        run: |
          docker build -t myapp:${{ github.sha }} .
          docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:${{ github.sha }}
          # digest를 output으로 내보냄
          echo "digest=$(docker inspect --format='{{index .RepoDigests 0}}' myapp:${{ github.sha }})" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production  # 환경 보호 규칙 적용
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS (deploy role - ECS update only)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy-role
          aws-region: ap-northeast-2

      - name: Deploy with verified digest
        run: |
          # 태그가 아닌 digest로 배포 (이미지 변조 방지)
          IMAGE_DIGEST="${{ needs.build.outputs.image-digest }}"
          aws ecs update-service \
            --cluster prod \
            --service myapp \
            --force-new-deployment \
            --task-definition "$(aws ecs describe-task-definition --task-definition myapp \
              --query 'taskDefinition.taskDefinitionArn' --output text | \
              sed "s|myapp:.*|myapp@${IMAGE_DIGEST}|")"
```

빌드 역할의 IAM 권한은 ECR 푸시로만 제한한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp"
    }
  ]
}
```

배포 역할은 ECS 서비스 업데이트로만 제한한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:ecs:ap-northeast-2:123456789012:service/prod/myapp",
        "arn:aws:ecs:ap-northeast-2:123456789012:task-definition/myapp:*"
      ]
    }
  ]
}
```

빌드 잡이 ECR 외에 다른 AWS 리소스에 접근하려 하면 IAM 거부로 막힌다. 공급망 공격으로 빌드 잡 내부 코드가 오염되더라도 AWS 인프라를 직접 건드릴 수 없는 구조다.

### 이미지 digest 사용의 이유

배포 단계에서 태그(`myapp:latest`, `myapp:main`) 대신 digest(`myapp@sha256:...`)로 배포하는 이유가 있다. 태그는 가변 참조다. 빌드 후 배포 사이에 레지스트리에서 이미지가 교체되면 다른 이미지가 배포된다. Digest는 내용 기반 해시라서 빌드한 이미지와 배포되는 이미지가 동일함을 보장한다.

---

## 빌드 환경 격리와 공급망 공격 방어

공급망 공격의 주요 경로는 세 가지다. 의존성 패키지 오염(npm, PyPI, Maven 등), 베이스 이미지 오염, 빌드 스크립트 오염이다.

### 의존성 고정

패키지를 버전 범위로 지정하면 공격자가 해당 버전 범위에 오염된 버전을 배포했을 때 자동으로 설치된다.

```bash
# 나쁜 예: 범위 지정
npm install express@^4.0.0

# 좋은 예: 정확한 버전 고정
npm install express@4.18.2

# 더 좋은 예: lockfile로 전이 의존성까지 고정
npm ci  # package-lock.json 기반으로 설치, 변경 불허
```

`npm ci`는 `npm install`과 달리 lockfile이 없거나 `package.json`과 불일치하면 실패한다. 파이프라인에서 `npm install` 대신 반드시 `npm ci`를 써야 한다.

Python은 `pip install -r requirements.txt`에 해시 검증을 추가할 수 있다.

```bash
pip install --require-hashes -r requirements.txt
```

`requirements.txt`에 해시가 없으면 설치가 거부된다.

```
django==4.2.7 \
    --hash=sha256:abc123... \
    --hash=sha256:def456...
```

### 베이스 이미지 고정

```dockerfile
# 나쁜 예: 태그 사용
FROM python:3.11-slim

# 좋은 예: digest로 고정
FROM python:3.11-slim@sha256:a8a61de5d0c5...
```

베이스 이미지도 digest로 고정하면 레지스트리에서 이미지가 바뀌더라도 영향받지 않는다. 다만 보안 패치 적용을 위한 주기적 업데이트 프로세스가 함께 있어야 한다.

### 빌드 스텝 격리

빌드 단계에서 외부 네트워크 접근을 제한하면 오염된 스크립트가 C2 서버에 연결하거나 데이터를 외부로 전송하는 걸 막을 수 있다. GitHub Actions에서는 에그레스 트래픽 제어가 기본으로 없지만, 셀프 호스팅 러너를 쓴다면 네트워크 정책으로 허용 도메인을 화이트리스트로 관리할 수 있다.

아티팩트 서명으로 빌드 출력물의 무결성을 검증하는 방법도 있다. Sigstore/cosign을 쓰면 컨테이너 이미지에 서명하고, 배포 전에 서명을 검증하는 단계를 넣을 수 있다.

```bash
# 빌드 후 이미지 서명
cosign sign --key cosign.key \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp@${IMAGE_DIGEST}

# 배포 전 서명 검증
cosign verify --key cosign.pub \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp@${IMAGE_DIGEST}
```

---

## 파이프라인 실행 컨텍스트 검증

PR 빌드와 main 브랜치 빌드에 같은 권한을 주면 안 된다. PR은 외부 기여자가 제출할 수 있고, fork에서 온 PR은 원 리포지토리의 Secrets에 접근할 수 없도록 GitHub이 차단하지만, 같은 리포지토리 내 PR이라면 Secrets에 접근 가능하다.

컨텍스트별 권한 분리 구조를 명확히 설계해야 한다.

| 컨텍스트 | AWS 역할 | Vault 정책 | 프로덕션 접근 |
|---|---|---|---|
| PR (fork) | 없음 | 없음 | 불가 |
| PR (same repo) | 빌드 역할 (ECR push 불가) | 없음 | 불가 |
| main 브랜치 | 빌드 역할 | 빌드 정책 | ECR push만 |
| main 브랜치 + deploy 잡 | 배포 역할 | 배포 정책 | ECS 업데이트만 |

GitHub Actions에서 컨텍스트를 조건으로 사용하는 예다.

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run tests (no secrets needed)
        run: make test

  build:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: test
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS (build role)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-build-role
          aws-region: ap-northeast-2

  deploy:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: build
    environment: production
    concurrency:
      group: production-deploy
      cancel-in-progress: false
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS (deploy role)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy-role
          aws-region: ap-northeast-2
```

`environment: production`을 설정하면 GitHub에서 해당 환경에 보호 규칙(required reviewers, deployment branch restrictions)을 걸 수 있다. 프로덕션 배포 잡은 지정된 사람이 승인한 뒤에만 실행된다.

`concurrency`로 동시 배포를 막는 것도 중요하다. 여러 배포가 동시에 진행되면 상태가 꼬이고, 어떤 버전이 실제로 배포됐는지 추적하기 어려워진다.

### PR 빌드에서 Secrets 노출 차단

GitHub의 경우 외부 fork에서 온 PR은 Secrets에 접근할 수 없지만, 같은 조직 내 리포지토리에서 온 PR은 기본적으로 Secrets에 접근 가능하다. 민감한 Secrets를 environment로 이동하고, 그 environment에 배포 브랜치 제한을 걸면 PR 빌드에서 민감한 Secrets가 노출되지 않는다.

```yaml
# GitHub 리포지토리 환경 설정 (API 또는 UI)
# Settings > Environments > production
# Deployment branches: main only
# Required reviewers: [senior-engineer]
```

OIDC를 쓰면 Secrets 자체가 없으니 이 문제가 상당 부분 해소된다. PR 빌드에서 OIDC 토큰은 발급되지만, IAM 신뢰 정책에서 `sub` 조건으로 main 브랜치만 허용하기 때문에 해당 역할을 가정할 수 없다.

---

## 파이프라인 감사와 이상 탐지

Zero Trust는 인증과 권한 제어만이 아니라 모든 접근을 기록하고 이상 징후를 탐지하는 것까지 포함한다.

AWS CloudTrail에서 파이프라인이 수행한 모든 API 호출이 기록된다. `role-session-name`에 워크플로우 실행 ID를 넣으면 특정 배포 실행이 어떤 AWS 작업을 했는지 역추적할 수 있다.

Vault 감사 로그도 활성화해야 한다.

```bash
vault audit enable file file_path=/var/log/vault/audit.log
```

Vault 감사 로그에는 어떤 토큰이 어떤 경로에 접근했는지 모두 기록된다. 비정상적인 접근 패턴(평소에 접근하지 않던 경로, 비업무 시간 접근 등)을 탐지하는 데 쓸 수 있다.

파이프라인에서 실제로 문제가 발생하면 대부분 로그를 뒤늦게 확인하게 된다. 처음부터 로그 구조를 잡아놓으면 사고 대응 시간을 크게 줄일 수 있다.

---

## 흔히 놓치는 부분

OIDC 설정을 하면서 `sub` 조건 없이 `aud`만 검증하는 경우가 있다. `aud`만 검증하면 같은 GitHub 조직의 다른 리포지토리도 해당 역할을 가정할 수 있다. `sub` 조건으로 리포지토리와 브랜치까지 명시해야 한다.

Vault SecretID를 Secrets에 장기 보관하는 경우도 많다. SecretID가 탈취되면 AppRole 인증이 뚫린다. SecretID는 파이프라인 실행 직전에 발급하고 즉시 소비하는 구조가 맞다. 아니면 GitHub OIDC로 Vault 자체에 인증하는 방법(Vault JWT Auth)을 쓰면 SecretID 자체를 없앨 수 있다.

```bash
# Vault JWT Auth로 GitHub OIDC 연동
vault auth enable jwt

vault write auth/jwt/config \
  oidc_discovery_url="https://token.actions.githubusercontent.com" \
  bound_issuer="https://token.actions.githubusercontent.com"

vault write auth/jwt/role/cicd-deploy \
  role_type="jwt" \
  bound_audiences="https://vault.example.com" \
  user_claim="sub" \
  bound_claims='{"sub": "repo:myorg/myrepo:ref:refs/heads/main"}' \
  policies=cicd-deploy-policy \
  ttl=30m
```

이렇게 구성하면 Secrets에 아무 자격증명도 저장하지 않고 파이프라인이 AWS와 Vault 모두에 OIDC로 인증할 수 있다.
