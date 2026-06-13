---
title: 커스텀 xcaddy 이미지 CI/CD 파이프라인
tags:
  - WebServer
  - Caddy
  - xcaddy
  - GitHubActions
  - CICD
  - Docker
  - cosign
  - trivy
updated: 2026-06-13
---

# 커스텀 xcaddy 이미지 CI/CD 파이프라인

공식 `caddy` 이미지를 쓰는 동안은 CI/CD를 고민할 일이 거의 없다. 문제는 `caddy-dns/cloudflare` 같은 플러그인이 하나라도 필요해지는 순간 시작된다. xcaddy로 직접 빌드한 바이너리를 이미지에 박아야 하고, 그 이미지를 누가 언제 어떻게 빌드하고 어디로 푸시하는지가 곧 운영 안정성이 된다. 로컬에서 `docker build` 한 번 돌려 레지스트리에 올리는 식으로 굴리다 보면, 반년쯤 뒤에 "지금 production에 떠 있는 이미지가 정확히 어떤 플러그인 커밋으로 빌드됐는지" 아무도 모르는 상태가 된다.

이 문서는 커스텀 xcaddy 이미지의 빌드부터 production 롤아웃까지를 GitHub Actions로 자동화하는 과정을 다룬다. 기초 빌드 방법(`Docker_Caddy.md`)이나 런타임 운영(`Docker_Caddy_Operations_Advanced.md`)이 아니라, 그 사이에 비는 파이프라인 영역이다. 멀티 아키텍처 빌드 자체의 CGO 함정은 심화 문서에서 다뤘으니 여기서는 파이프라인에 끼워 넣는 관점으로만 짚는다.

## 왜 빌드를 자동화해야 하는가

xcaddy 빌드는 매번 결과가 미묘하게 달라질 수 있는 빌드다. `xcaddy build --with github.com/caddy-dns/cloudflare`는 버전을 지정하지 않으면 그 시점의 최신 태그(또는 메인 브랜치)를 끌어온다. 어제 빌드한 이미지와 오늘 빌드한 이미지가 같은 Dockerfile로 만들어졌는데 들어 있는 플러그인 커밋이 다른 일이 생긴다. 로컬 빌드로는 이 드리프트를 추적할 방법이 없다.

자동화의 핵심은 빌드를 재현 가능하게 만드는 것이다. 같은 입력(Dockerfile + 핀 고정된 버전)으로 빌드하면 항상 같은 바이너리가 나오고, 그 바이너리가 어떤 검증을 통과했는지 로그가 남는다. 사고가 났을 때 "이 digest로 롤백"이 가능해진다.

## Dockerfile에서 플러그인 버전 핀 고정

가장 먼저 손봐야 하는 건 Dockerfile이다. 핀을 안 박은 Dockerfile은 시한폭탄이다.

```dockerfile
# 나쁜 예 — 버전 미지정
FROM caddy:2.8-builder AS builder
RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/mholt/caddy-ratelimit
```

이렇게 쓰면 빌드할 때마다 cloudflare 플러그인의 최신 상태를 끌어온다. 어느 날 그 플러그인이 메인 브랜치에 호환성 깨지는 커밋을 머지하면, 그날 빌드부터 갑자기 모듈 로딩이 실패하거나 동작이 달라진다. 빌드는 성공했는데 런타임에서 죽는 경우가 제일 골치 아프다.

버전을 명시적으로 박는다.

```dockerfile
FROM --platform=$BUILDPLATFORM caddy:2.8.4-builder AS builder
ARG TARGETOS
ARG TARGETARCH
ENV CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH

RUN xcaddy build v2.8.4 \
    --with github.com/caddy-dns/cloudflare@v0.5.1 \
    --with github.com/mholt/caddy-ratelimit@v0.0.0-20240611204149-7e7b9b3f5a3e

# 빌드 직후 검증 — 여기서 막아야 런타임 사고를 안 본다
RUN /usr/bin/caddy validate --config /dev/null --adapter caddyfile 2>/dev/null || true && \
    /usr/bin/caddy list-modules --versions | grep -q 'cloudflare' && \
    /usr/bin/caddy list-modules --versions | grep -q 'rate_limit'

FROM caddy:2.8.4-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

`xcaddy build v2.8.4`처럼 Caddy 코어 버전까지 명시하고, 플러그인은 `@v0.5.1` 또는 의사 버전(pseudo-version)으로 커밋을 직접 고정한다. 태그가 없는 플러그인은 `@v0.0.0-<timestamp>-<commit>` 형태의 의사 버전으로 박을 수밖에 없는데, 이게 핀 관리에서 제일 지저분한 부분이다. 태그를 안 끊는 플러그인이 의외로 많다.

빌드 단계의 `list-modules --versions`로 플러그인이 실제로 바이너리에 들어갔는지 확인한다. xcaddy가 플러그인을 못 가져왔는데도 빌드가 성공하고, 그 플러그인 기능을 쓰는 Caddyfile이 런타임에서 "unknown directive"로 죽는 사고가 있다. `grep -q`로 막으면 이미지 빌드 단계에서 실패하니 production까지 안 간다.

마지막 스테이지에서 Caddyfile까지 `validate`하는 건 기초 문서에서도 권했지만, CI 맥락에서는 의미가 더 크다. validate를 통과하지 못하면 이미지 자체가 안 만들어지고 레지스트리에 푸시되지 않는다. 깨진 이미지가 태그를 달고 올라가는 일이 원천 차단된다.

## GitHub Actions 워크플로 기본 골격

전체 흐름을 한 워크플로에 담는다. 빌드 → 검증 → 스캔 → 서명 → 스테이징 스모크 테스트 → production 롤아웃 순서다.

```yaml
name: caddy-image

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

permissions:
  contents: read
  packages: write
  id-token: write   # cosign keyless 서명에 필요

env:
  REGISTRY: ghcr.io
  IMAGE: ghcr.io/${{ github.repository }}/caddy

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true
```

`id-token: write`는 cosign keyless 서명을 쓸 때 OIDC 토큰을 받기 위한 권한이다. 이걸 빼먹으면 서명 단계에서 토큰 발급이 안 돼서 한참 헤맨다.

태그를 커밋 SHA(`github.sha`)로 박는 게 중요하다. `latest`나 `v2.8`처럼 움직이는 태그를 빌드 단위로 삼으면 나중에 "production에 떠 있는 게 정확히 어떤 빌드인지" 추적이 안 된다. 사람이 읽는 태그(`v2.8.4`, `latest`)는 별도로 달되, 배포의 기준은 항상 불변 식별자여야 한다. 이 얘기는 뒤의 태그 전략에서 자세히 다룬다.

## 빌드 캐시 재사용과 캐시 꼬임

xcaddy 빌드는 매번 Go 모듈을 받고 컴파일하기 때문에 캐시가 없으면 5~10분씩 걸린다. `cache-from: type=gha` / `cache-to: type=gha,mode=max`로 GitHub Actions 캐시에 BuildKit 레이어를 저장한다. `mode=max`는 중간 스테이지 레이어까지 전부 캐싱한다는 의미다. xcaddy 빌더 스테이지가 캐싱되면 플러그인이 안 바뀐 빌드는 1분 안에 끝난다.

여기서 실무 사고가 하나 있다. 캐시가 꼬여서 옛날 플러그인 버전이 그대로 박혀 나오는 경우다. Dockerfile에서 `xcaddy build`를 호출하는 `RUN` 레이어가 캐시 히트되면 BuildKit은 그 명령을 다시 실행하지 않는다. 그런데 `@v0.5.1` 같은 버전을 `@v0.5.2`로 바꿨는데도 그 윗줄들이 동일하면 BuildKit이 레이어 캐시를 재사용하면서 명령 문자열이 바뀌었는지를 기준으로만 판단한다. 명령 문자열이 바뀌면 캐시 미스가 나는 게 정상이지만, 의사 버전을 환경변수나 ARG로 우회해서 주입하는 구조라면 명령 문자열이 안 바뀌어서 캐시가 그대로 먹힌다.

```dockerfile
# 위험 — 캐시 꼬임 유발 가능
ARG CLOUDFLARE_VERSION=latest
RUN xcaddy build --with github.com/caddy-dns/cloudflare@${CLOUDFLARE_VERSION}
```

`CLOUDFLARE_VERSION`을 바꿔도 `RUN` 명령 문자열은 ARG 전개 전이라 동일하게 보일 수 있고, 빌드 인자 변경이 캐시 무효화로 이어지지 않는 설정이면 옛날 플러그인이 그대로 나온다. 버전을 Dockerfile에 직접 박거나, ARG를 쓰더라도 그 값을 캐시 키에 반영되도록 빌드해야 한다. 의심스러우면 CI에서 주기적으로 `no-cache` 빌드를 한 번씩 돌려 캐시 없이 만든 이미지와 `list-modules --versions` 결과를 비교한다. 두 결과가 다르면 캐시가 거짓말을 하고 있는 것이다.

Go 모듈 캐시는 BuildKit 캐시 마운트로 분리하는 방법도 있다.

```dockerfile
RUN --mount=type=cache,target=/root/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    xcaddy build v2.8.4 --with github.com/caddy-dns/cloudflare@v0.5.1
```

캐시 마운트는 레이어 캐시와 별개로 동작해서, 레이어가 무효화돼도 다운로드받은 모듈은 재사용한다. 다만 GitHub Actions의 `type=gha` 캐시는 캐시 마운트를 기본으로 export하지 않으니, 이걸 쓰려면 `reproducible-containers/buildkit-cache-dance` 같은 액션으로 별도 처리해야 한다. 여기까지 가면 복잡도가 올라가니, 빌드가 자주 일어나지 않는 환경이면 레이어 캐시만으로도 충분하다.

## 플러그인 버전 갱신 감지 — Dependabot/Renovate

핀을 박으면 빌드는 안정되지만, 이번엔 플러그인이 보안 패치를 내도 자동으로 안 따라간다. 핀 고정과 갱신 감지는 한 세트로 가야 한다.

xcaddy 빌드는 내부적으로 `go.mod`를 생성해서 빌드하는데, 이 `go.mod`가 리포에 없으면 Dependabot/Renovate가 추적할 대상이 없다. 두 가지 방법이 있다.

첫째, Dockerfile의 `--with` 인자를 직접 갱신 대상으로 삼는다. Renovate는 Dockerfile 안의 Go 모듈 참조를 인식하는 커스텀 매니저를 지원한다.

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["(^|/)Dockerfile$"],
      "matchStrings": [
        "--with\\s+(?<depName>[^@\\s]+)@(?<currentValue>v[0-9][^\\s]+)"
      ],
      "datasourceTemplate": "go"
    }
  ]
}
```

이 정규식 매니저가 `--with github.com/caddy-dns/cloudflare@v0.5.1`에서 모듈 경로와 버전을 뽑아내서, Go datasource로 최신 버전을 조회하고 PR을 올린다. PR이 올라오면 CI가 그 버전으로 빌드·검증·스캔을 돌리니, 머지 전에 호환성을 확인할 수 있다.

둘째, 빌드를 위한 별도 `go.mod`를 리포에 두고 그걸 xcaddy에 먹이는 방식이다. Dependabot은 `go.mod`를 네이티브로 추적한다. 이게 더 표준적이지만 xcaddy 빌드 구조를 바꿔야 해서 손이 더 간다.

어느 쪽이든 핵심은 메인 브랜치 드리프트 방지다. 핀을 안 박으면 빌드할 때마다 메인 브랜치를 끌어와서 조용히 바뀌고, 핀만 박고 갱신 감지를 안 하면 보안 패치를 놓친다. 핀 + 봇 PR + CI 검증의 조합으로 "통제된 갱신"을 만드는 게 목적이다.

caddy-dns 계열 플러그인은 코어 Caddy 버전과의 호환성에 민감하다. 코어를 2.8에서 2.9로 올릴 때 일부 DNS 플러그인이 따라오지 못해 빌드가 깨지는 일이 있다. 봇이 코어 버전 PR과 플러그인 PR을 따로 올리면, 코어만 먼저 머지됐다가 빌드가 깨질 수 있으니 둘을 묶어서 검토한다.

## 취약점 스캔 — trivy

이미지를 푸시하기 전이나 직후에 trivy로 스캔한다. xcaddy 이미지는 Alpine 베이스라 OS 패키지 취약점이 가끔 잡히고, Go 바이너리 내부의 의존성 취약점도 trivy가 SBOM을 통해 잡아낸다.

```yaml
  scan:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Run Trivy
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ env.IMAGE }}@${{ needs.build.outputs.digest }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: '1'
          ignore-unfixed: true

      - name: Upload to code scanning
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results.sarif
```

`image-ref`를 태그가 아니라 digest로 지정하는 게 포인트다. 빌드한 그 이미지를 정확히 스캔해야지, 그 사이에 같은 태그로 다른 게 푸시됐을 가능성을 배제해야 한다.

`ignore-unfixed: true`는 현실적인 타협이다. Alpine 패키지 중에 패치가 아직 안 나온(unfixed) 취약점까지 `exit-code: 1`로 막으면 빌드가 영원히 통과를 못 한다. 고칠 수 있는 것만 막고, unfixed는 SARIF로 기록해서 추적한다. `exit-code: '1'`로 CRITICAL/HIGH가 잡히면 파이프라인을 멈춰서 푸시 이후 단계로 안 넘어가게 한다.

스캔을 빌드 푸시 후에 두면 이미 레지스트리에 올라간 이미지를 스캔하게 되는데, 취약점이 잡혀도 이미지는 이미 올라가 있다. 이게 신경 쓰이면 빌드 잡 안에서 `push: false`로 로컬 빌드한 뒤 스캔을 통과한 것만 별도 스텝에서 푸시하는 구조로 바꾼다. 다만 멀티 아키텍처 빌드는 로컬에 이미지를 못 올려놓는 제약이 있어서(`--load`가 단일 플랫폼만 지원) 구조가 까다로워진다. 보통은 SHA 태그로 푸시 → 스캔 통과 → 사람이 읽는 태그/서명 부여 순서로 간다. SHA 태그는 사람이 직접 안 쓰니, 스캔 안 통과한 SHA 이미지가 레지스트리에 잠깐 떠 있어도 실제 배포로 이어지지 않는다.

## SBOM 생성과 이미지 서명 — syft, cosign

SBOM(Software Bill of Materials)은 이미지에 뭐가 들어 있는지의 목록이다. xcaddy 이미지처럼 직접 빌드한 바이너리는 "이 안에 어떤 Go 모듈이 어떤 버전으로 들어 있나"가 중요해서 SBOM의 가치가 크다. 나중에 특정 플러그인에 CVE가 떴을 때, SBOM을 조회하면 영향받는 이미지를 즉시 골라낼 수 있다.

`build-push-action`에 `sbom: true`를 주면 BuildKit이 SBOM을 자동 생성해 이미지에 attestation으로 붙인다. 별도로 syft를 돌려 더 상세한 SBOM을 뽑을 수도 있다.

```yaml
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.IMAGE }}@${{ needs.build.outputs.digest }}
          format: spdx-json
          output-file: caddy-sbom.spdx.json
```

서명은 cosign으로 한다. 서명의 목적은 "이 digest의 이미지가 우리 파이프라인에서 나온 게 맞다"를 암호학적으로 보증하는 것이다. 레지스트리가 뚫려서 누가 같은 태그로 악성 이미지를 밀어넣어도, 서명이 없으면 배포 단계에서 거른다.

```yaml
  sign:
    needs: [build, scan]
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      packages: write
    steps:
      - uses: sigstore/cosign-installer@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Sign image (keyless)
        run: |
          cosign sign --yes \
            ${{ env.IMAGE }}@${{ needs.build.outputs.digest }}

      - name: Attest SBOM
        run: |
          cosign attest --yes \
            --predicate caddy-sbom.spdx.json \
            --type spdxjson \
            ${{ env.IMAGE }}@${{ needs.build.outputs.digest }}
```

keyless 서명은 개인 키를 관리하지 않고 OIDC 신원(이 경우 GitHub Actions 워크플로의 신원)으로 서명한다. 서명 기록은 Sigstore의 공개 투명성 로그(Rekor)에 올라간다. 키 분실/유출 걱정이 없는 대신, 서명 검증 시 "어떤 워크플로가 서명했는지"를 정책으로 고정해야 의미가 있다.

배포 단계에서 검증한다.

```bash
cosign verify \
    --certificate-identity-regexp "https://github.com/myorg/myrepo/.github/workflows/.*" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    ghcr.io/myorg/myrepo/caddy@sha256:abc...
```

`certificate-identity-regexp`로 우리 리포의 워크플로가 서명한 것만 통과시킨다. 이걸 빼고 그냥 `cosign verify`만 하면 누구의 서명이든 통과하니 보안 의미가 없어진다. 여기를 느슨하게 박는 게 흔한 실수다.

## 레지스트리 선택과 태그 전략

GHCR와 ECR 중 어디로 푸시할지는 배포 대상에 따라 갈린다. ECS/EKS로 AWS에서 굴린다면 ECR이 IAM 통합과 VPC 엔드포인트 면에서 자연스럽고, 이미지 풀 비용도 같은 리전이면 안 나간다. GitHub 중심으로 돌고 쿠버네티스가 여러 클라우드에 흩어져 있으면 GHCR가 편하다. cosign keyless 서명은 양쪽 다 된다.

ECR로 가는 경우 OIDC로 AWS 자격증명을 받는 게 깔끔하다. 장기 액세스 키를 GitHub Secrets에 박지 않는다.

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-ecr
          aws-region: ap-northeast-2

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2
```

ECR 쪽에서 신뢰 정책에 GitHub OIDC provider를 등록하고, 특정 리포·브랜치만 그 role을 assume할 수 있게 조건을 건다. 이 조건을 `repo:myorg/*:*`처럼 넓게 잡으면 조직 내 아무 리포나 ECR에 푸시할 수 있게 되니 `repo:myorg/myrepo:ref:refs/heads/main`까지 좁힌다.

태그 전략의 원칙은 하나다. 배포의 기준은 항상 immutable digest고, 사람이 읽는 태그는 보조 수단이다.

```
ghcr.io/myorg/caddy@sha256:abc123...   ← 배포는 이걸 본다 (불변)
ghcr.io/myorg/caddy:2.8.4              ← 사람이 읽는 릴리스 태그
ghcr.io/myorg/caddy:latest            ← 최신 가리킴 (움직임)
```

digest는 이미지 내용의 해시라 같은 digest는 영원히 같은 이미지다. `:latest`나 `:2.8.4`는 다른 이미지를 가리키도록 다시 푸시될 수 있다. ECR이든 GHCR이든 태그 immutability 옵션을 켜서 `:2.8.4`가 한 번 박히면 덮어쓰기를 막을 수 있는데, `:latest`만큼은 움직여야 하니 immutable로 못 잡는다.

배포 매니페스트(쿠버네티스 Deployment, ECS task definition)에는 반드시 digest를 박는다.

```yaml
# 좋음 — digest 핀
image: ghcr.io/myorg/caddy@sha256:abc123...

# 나쁨 — 움직이는 태그
image: ghcr.io/myorg/caddy:latest
```

`:latest`로 배포하면 같은 매니페스트로 Pod가 재생성될 때마다 그 시점의 `latest`를 끌어와서, 어제 떠 있던 Pod와 오늘 재시작된 Pod가 다른 이미지를 쓰는 상황이 생긴다. 더 심각한 건 롤백 불가다.

## digest 미고정으로 인한 롤백 불가 사고

실제로 겪는 시나리오를 하나 적는다. `:latest`로 배포하던 서비스에서 새 이미지를 빌드해 `:latest`로 밀었더니 Caddy가 부팅 직후 모듈 로딩에서 죽었다. 새로 추가한 플러그인이 코어 버전과 안 맞았던 거다. 롤백하려고 했는데, 직전에 잘 돌던 이미지의 digest를 아무도 기록 안 해뒀다. `:latest`는 이미 새 이미지를 가리키고 있고, 직전 이미지는 태그가 없으니 레지스트리에서 어떤 게 그건지 식별이 안 됐다. 결국 git에서 직전 커밋을 찾아 그 SHA로 이미지를 처음부터 다시 빌드해서 올렸고, 그 사이 서비스가 한참 떠 있다 죽다 했다.

digest로 배포했다면 직전 매니페스트의 `@sha256:...` 한 줄만 되돌리면 끝이었다. 이미지는 레지스트리에 그대로 있으니 재빌드도 필요 없다. 이게 digest 핀이 주는 가장 큰 실익이다. 빠른 배포보다 빠른 롤백이 운영에선 더 중요한데, 움직이는 태그는 롤백 경로를 통째로 막는다.

레지스트리 GC 정책도 같이 봐야 한다. ECR lifecycle policy나 GHCR의 미사용 버전 정리가 너무 공격적이면, 태그 안 달린 직전 이미지가 GC로 지워져서 digest를 알아도 롤백을 못 하는 일이 생긴다. 최근 N개 또는 며칠치는 태그 유무와 무관하게 보존하도록 정책을 잡는다.

## 스테이징 스모크 테스트 후 production 롤아웃

서명까지 끝난 이미지를 바로 production에 꽂지 않는다. 스테이징에서 실제 Caddyfile로 컨테이너를 띄워 스모크 테스트를 돌린 뒤, 통과한 digest만 production 롤아웃을 트리거한다.

스모크 테스트의 핵심은 `caddy validate`로 안 잡히는 런타임 동작을 확인하는 것이다. validate는 문법만 보지, 실제로 그 설정으로 Caddy가 부팅해서 요청을 처리하는지는 검증 못 한다. 플러그인이 바이너리에 들어 있어도 그 directive가 런타임에 제대로 동작하는지는 띄워봐야 안다.

```yaml
  smoke-test:
    needs: [build, scan, sign]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Caddy with prod Caddyfile
        run: |
          docker run -d --name caddy-smoke \
            -v ${{ github.workspace }}/Caddyfile:/etc/caddy/Caddyfile:ro \
            -e CLOUDFLARE_API_TOKEN=dummy \
            -p 8080:80 \
            ${{ env.IMAGE }}@${{ needs.build.outputs.digest }}

      - name: Wait for boot
        run: |
          for i in $(seq 1 15); do
            if docker logs caddy-smoke 2>&1 | grep -q 'serving initial configuration'; then
              echo "booted"; exit 0
            fi
            if ! docker ps -q -f name=caddy-smoke | grep -q .; then
              echo "container died"; docker logs caddy-smoke; exit 1
            fi
            sleep 2
          done
          echo "boot timeout"; docker logs caddy-smoke; exit 1

      - name: Probe health endpoint
        run: |
          code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/health)
          [ "$code" = "200" ] || { echo "health failed: $code"; docker logs caddy-smoke; exit 1; }

      - name: Verify modules loaded
        run: |
          docker exec caddy-smoke caddy list-modules --versions | grep cloudflare
```

여기서 보는 건 세 가지다. 컨테이너가 죽지 않고 부팅 로그(`serving initial configuration`)를 찍는지, health 엔드포인트가 200을 주는지, 기대한 플러그인 모듈이 실제 로드됐는지. ACME 발급까지 스테이징에서 돌리면 Let's Encrypt rate limit을 까먹으니, 스모크 단계에서는 staging CA(`acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`)를 쓰거나 `auto_https off`로 HTTPS를 끄고 부팅·라우팅만 본다.

DNS provider 토큰은 스모크 테스트에선 더미를 넣는다. DNS-01 challenge를 실제로 돌릴 게 아니라 플러그인이 로드되고 Caddyfile이 부팅되는지만 보는 거라, 토큰 검증까지 안 가는 경로면 더미로 충분하다. 토큰 검증이 부팅 시점에 일어나는 설정이면 staging용 실제 토큰을 secret으로 따로 둔다.

스모크가 통과하면 production 롤아웃을 트리거한다. 같은 워크플로에서 GitHub Environments의 승인 게이트를 거는 방식이 깔끔하다.

```yaml
  deploy-prod:
    needs: [build, smoke-test]
    runs-on: ubuntu-latest
    environment: production    # 승인 게이트가 걸린 환경
    steps:
      - name: Trigger rollout
        run: |
          # 매니페스트에 digest를 박아 배포 — 태그가 아니라 digest
          kubectl set image deployment/caddy \
            caddy=${{ env.IMAGE }}@${{ needs.build.outputs.digest }} \
            -n production
          kubectl rollout status deployment/caddy -n production --timeout=180s
```

`environment: production`에 required reviewer를 걸어두면, 이 잡이 시작되기 전에 사람이 승인을 눌러야 한다. 자동화하되 production 진입에는 사람 손을 한 번 거치게 하는 타협이다. 롤아웃은 항상 digest로 한다. 여기까지 와서 `:latest`로 set image를 하면 앞에서 쌓은 검증·서명·스모크가 다 무의미해진다. 검증한 그 digest와 배포되는 이미지가 같다는 보장이 끊기기 때문이다.

`kubectl rollout status`로 롤아웃이 완료될 때까지 기다리고, 타임아웃 안에 안 끝나면 잡이 실패한다. 앞 문서의 `maxUnavailable: 0` 전략과 맞물려서, 새 Pod가 readiness를 통과 못 하면 기존 Pod가 그대로 트래픽을 받고 롤아웃은 실패로 끝난다. 자동 롤백을 걸어두면 이 실패 시점에 직전 ReplicaSet으로 되돌아간다.

## 전체 파이프라인을 잇는 digest 한 줄

이 파이프라인 전체를 관통하는 한 가지는 digest다. 빌드가 digest를 출력하고(`needs.build.outputs.digest`), 스캔·서명·SBOM·스모크·배포가 전부 그 digest 하나를 참조한다. 중간에 태그를 끼워 넣는 순간 "내가 검증한 것과 내가 배포한 것이 같다"는 연결이 끊긴다.

태그는 사람을 위한 별칭이고, 파이프라인의 진짜 통화는 digest다. 빌드부터 production까지 같은 digest가 흐르는지만 확인하면, 캐시가 꼬여도, 누가 레지스트리에 다른 걸 밀어넣어도, 롤백을 해야 해도, 무엇이 어디에 떠 있는지가 항상 명확하다. xcaddy 이미지처럼 매 빌드가 미묘하게 달라질 수 있는 빌드에서는 이 추적 가능성이 운영의 토대가 된다.
