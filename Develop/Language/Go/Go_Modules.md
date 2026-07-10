---
title: Go Modules
tags:
  - Go
  - Golang
  - Go Modules
  - go.mod
  - GOPATH
  - Workspace
updated: 2026-07-10
---

# Go Modules

Go 1.11에서 모듈 시스템이 도입되기 전까지는 GOPATH 하나에 모든 프로젝트를 몰아넣는 방식을 썼다. 의존성 버전 관리가 사실상 불가능했고, 같은 라이브러리를 쓰는 두 프로젝트가 서로 다른 버전을 요구하면 답이 없었다. Go 1.16부터 모듈이 기본값이 되면서 GOPATH 방식은 사실상 쓸 일이 없어졌다.

## go.mod 구조

모듈의 루트 디렉토리에 `go.mod`가 있어야 모듈로 인식된다.

```
module github.com/myorg/myapp

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/jackc/pgx/v5 v5.5.4
)

require (
    github.com/bytedance/sonic v1.10.2 // indirect
    github.com/pelletier/go-toml/v2 v2.1.1 // indirect
)
```

`module` 줄은 이 모듈의 경로다. 다른 프로젝트에서 이 모듈을 임포트할 때 쓰는 이름이다. 퍼블릭 공개 예정이면 실제 저장소 경로로 맞춰야 하고, 내부 전용이면 아무 경로나 써도 된다.

`go` 줄은 이 모듈이 요구하는 최소 Go 버전이다. 단순히 문서화 목적이 아니라, 해당 버전의 언어 기능 여부를 컴파일러가 이 값을 보고 판단한다. 1.21부터는 toolchain 줄도 생겼다.

`require` 블록은 직접 의존성과 간접 의존성을 함께 담는다. `// indirect` 주석이 붙은 항목은 직접 import하지 않지만 의존 라이브러리가 필요로 하는 것들이다. `go mod tidy`를 실행하면 자동으로 정리된다.

## go.sum 역할

`go.sum`은 각 모듈의 해시값을 담는다.

```
github.com/gin-gonic/gin v1.9.1 h1:4idEAncQnU5cB7BerypkHKia1UmaNo9A/Jrp+RnWhPk=
github.com/gin-gonic/gin v1.9.1/go.mod h1:hPrL7YrpYKXt5YId3A/Tnip5kqbEAP+KLuI3SUcPTeU=
```

각 줄은 모듈 경로, 버전, 파일 해시 세 부분으로 구성된다. `.zip` 해시와 `go.mod` 해시 두 가지를 기록한다. 빌드 시 다운로드한 파일이 이 해시와 다르면 빌드가 실패한다. 공급망 공격 방어 목적이다.

`go.sum`은 항상 git에 커밋해야 한다. `.gitignore`에 넣으면 팀원이 다운로드한 패키지와 해시가 달라질 수 있고, CI에서 터진다.

## replace 디렉티브

`replace`는 특정 모듈 경로를 다른 경로나 로컬 디렉토리로 교체한다.

```
replace github.com/myorg/shared => ../shared
```

이게 필요한 상황은 주로 두 가지다.

첫 번째는 로컬 개발이다. `shared` 라이브러리를 수정하면서 동시에 그걸 쓰는 `myapp`을 테스트할 때, 매번 배포하고 버전 올리는 과정을 건너뛰고 로컬 경로를 직접 참조한다. 다만 이 상태로 배포하면 다른 환경에서 경로를 찾지 못하니, 로컬 `replace`는 배포 전에 제거해야 한다.

두 번째는 포크 대체다. 오픈소스 라이브러리에 버그가 있는데 아직 upstream에 머지되지 않았을 때, 자체 포크로 교체하는 용도로 쓴다.

```
replace github.com/some/buggy-lib v1.2.3 => github.com/myorg/buggy-lib-fork v1.2.3-patch1
```

버전까지 지정하면 그 버전에만 replace가 적용되고, 버전을 생략하면 해당 모듈의 모든 버전에 적용된다.

## exclude 디렉티브

특정 버전을 아예 사용하지 않도록 막는다.

```
exclude github.com/some/lib v1.2.0
```

MVS 알고리즘이 v1.2.0을 선택하더라도 이 버전은 건너뛰고 그 다음 버전을 선택한다. 보안 취약점이 발견된 버전을 강제로 배제할 때 쓴다. 단, `exclude`는 메인 모듈에서만 효과가 있다. 의존 라이브러리의 `go.mod`에 있는 `exclude`는 무시된다.

## MVS (Minimum Version Selection)

Go의 버전 선택 알고리즘이다. 이름이 '최소 버전 선택'이지만 실제로는 '요구하는 최소 버전 중 가장 높은 것을 선택'이다.

A가 lib v1.2.0을 요구하고, B가 lib v1.3.0을 요구하면, Go는 v1.3.0을 선택한다. npm처럼 최신 버전을 자동으로 당기지 않는다. 빌드가 항상 예측 가능한 버전을 쓰는 게 핵심이다.

```
# 의존 그래프
myapp
├── A v1.0.0 (requires lib v1.2.0)
└── B v1.0.0 (requires lib v1.3.0)
         └── lib → v1.3.0 선택
```

`go get github.com/some/lib@latest`로 명시적으로 올리지 않는 한 버전이 자동으로 올라가지 않는다. 이게 가끔 불편하게 느껴지지만, 버전이 몰래 바뀌어서 빌드가 깨지는 상황을 막는다.

`go mod graph` 명령으로 의존 그래프를 볼 수 있다. 왜 특정 버전이 선택됐는지 추적할 때 유용하다.

## private 모듈 설정

회사 내부 모듈은 public proxy를 거치면 안 된다. Go는 기본적으로 `GOPROXY=https://proxy.golang.org,direct`를 쓰기 때문에, 별도 설정 없이는 모든 모듈 요청이 proxy를 거친다.

**GOPRIVATE**

가장 먼저 설정해야 하는 환경변수다.

```bash
export GOPRIVATE=github.com/myorg/*,gitlab.internal.com/*
```

`GOPRIVATE`을 설정하면 해당 패턴의 모듈은 proxy를 거치지 않고 직접 VCS에서 받아온다. 동시에 sum DB 검증도 건너뛴다.

**GONOSUMDB / GONOSUMCHECK**

`GONOSUMDB`는 sum DB 검증을 건너뛸 모듈을 지정한다. `GONOSUMCHECK`는 이미 다운로드된 파일의 체크섬 확인을 건너뛴다. `GOPRIVATE`을 쓰면 두 설정이 자동으로 포함되기 때문에, 별도로 설정할 필요는 거의 없다. 다만 proxy는 통하되 sum 검증만 건너뛰고 싶을 때는 `GONOSUMDB`를 따로 쓴다.

**GONOSUMCHECK vs GONOSUMDB 차이**

`GONOSUMDB`는 sum DB에 조회 자체를 안 하는 것이고, `GONOSUMCHECK`는 `go.sum`의 체크섬 비교를 건너뛰는 것이다. 내부 proxy를 직접 운영하면서 sum 검증은 proxy가 담당하는 구성에서 `GONOSUMDB`만 쓰는 경우가 있다.

**내부 proxy 설정**

JFrog Artifactory나 Athens 같은 사설 proxy를 운영하는 경우 아래처럼 설정한다.

```bash
export GOPROXY=https://proxy.internal.com,direct
export GONOSUMDB=*.internal.com
```

CI 환경에서는 이 값들을 환경변수로 주입하거나 `go env -w`로 영구 설정한다.

```bash
go env -w GOPRIVATE=github.com/myorg/*
go env -w GOPROXY=https://proxy.internal.com,direct
```

`go env -w`로 설정하면 `$GOENV` 파일(기본값: `~/.config/go/env`)에 저장된다.

## vendor 모드

`go mod vendor`를 실행하면 `vendor/` 디렉토리에 의존성 소스를 복사한다.

```bash
go mod vendor
go build -mod=vendor ./...
```

외부 인터넷 접근이 제한된 CI 환경이나, 의존성을 소스와 함께 보관해야 하는 보안 요구사항이 있을 때 쓴다. `vendor/` 디렉토리를 git에 올리면 외부 접근 없이 빌드할 수 있다.

저장소 크기가 늘어나는 게 단점이다. 의존성이 많은 프로젝트는 vendor 디렉토리가 수백 MB가 되기도 한다. 이를 싫어하는 팀은 GOPROXY 사설 서버를 두고 vendor는 쓰지 않는 방식을 택한다.

`-mod=vendor` 플래그를 명시하거나, `GOFLAGS=-mod=vendor`를 설정하면 빌드 시 vendor 디렉토리를 사용한다. Go 1.14부터는 vendor 디렉토리가 존재하면 자동으로 `-mod=vendor`가 활성화된다.

## go workspace (1.18+)

workspace는 여러 모듈을 동시에 개발할 때 `replace` 디렉티브를 남발하지 않아도 되도록 만든 기능이다.

```bash
# 루트에서 workspace 초기화
go work init ./myapp ./shared ./api-client
```

`go.work` 파일이 생성된다.

```
go 1.21

use (
    ./myapp
    ./shared
    ./api-client
)
```

`go.work`가 있으면 Go 툴체인은 `use`에 나열된 모듈들을 하나의 workspace로 묶어 다룬다. `myapp`에서 `shared`를 임포트하면 `go.mod`의 버전이 아니라 로컬 `./shared` 경로가 자동으로 우선된다.

`replace`와 달리 `go.work`는 각 모듈의 `go.mod`를 수정하지 않는다. 개발 중에만 workspace를 쓰고, 배포할 때는 각 모듈을 독립적으로 릴리즈하면 된다.

```bash
# workspace에 모듈 추가
go work use ./another-module

# 특정 모듈 제외 (go.work에서 삭제)
go work edit -dropuse ./old-module
```

`go.work.sum`도 자동으로 생성되는데, `go.sum`과 동일한 역할을 한다. `go.work`는 배포 환경에서는 쓰지 않으니 `.gitignore`에 넣어도 되지만, 팀 전체가 같은 workspace 구성을 공유한다면 커밋하는 게 낫다.

workspace를 일시적으로 비활성화하고 싶으면 `GOWORK=off` 환경변수를 쓴다.

```bash
GOWORK=off go build ./...
```

## 자주 쓰는 명령 정리

```bash
# 의존성 정리 (사용하지 않는 것 제거, 필요한 것 추가)
go mod tidy

# 특정 버전으로 업데이트
go get github.com/some/lib@v1.5.0

# 최신 마이너/패치 버전으로 업데이트
go get -u github.com/some/lib

# 모든 의존성 최신으로 업데이트
go get -u ./...

# 의존 그래프 확인
go mod graph

# 모듈 다운로드 캐시로 복사
go mod download

# vendor 디렉토리 생성
go mod vendor

# 현재 모듈 정보 확인
go list -m all
```

`go get -u ./...`는 가끔 예상치 못한 버전으로 올라가서 빌드가 깨지는 경우가 있다. 운영 중인 서비스라면 라이브러리 하나씩 올리고 테스트하는 게 안전하다.