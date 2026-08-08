---
title: Go Modules
tags: [go, language]
updated: 2026-07-27
---

# Go Modules

Go 1.11에서 모듈 시스템이 도입되기 전까지는 GOPATH 하나에 모든 프로젝트를 몰아넣는 방식을 썼다. 의존성 버전 관리가 사실상 불가능했고, 같은 라이브러리를 쓰는 두 프로젝트가 서로 다른 버전을 요구하면 답이 없었다. Go 1.16부터 모듈이 기본값이 되면서 GOPATH 방식은 사실상 쓸 일이 없어졌다.

## go.mod 구조

모듈의 루트 디렉토리에 `go.mod`가 있어야 모듈로 인식된다.

```
module github.com/myorg/myapp

go 1.21

toolchain go1.21.5

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

`go` 줄은 이 모듈이 요구하는 최소 Go 버전이다. 단순히 문서화 목적이 아니라, 해당 버전의 언어 기능 여부를 컴파일러가 이 값을 보고 판단한다.

`require` 블록은 직접 의존성과 간접 의존성을 함께 담는다. `// indirect` 주석이 붙은 항목은 직접 import하지 않지만 의존 라이브러리가 필요로 하는 것들이다. `go mod tidy`를 실행하면 자동으로 정리된다.

## toolchain 디렉티브 (Go 1.21+)

Go 1.21부터 `toolchain` 디렉티브가 추가됐다. `go` 줄이 언어 최소 버전이라면, `toolchain`은 실제로 사용할 컴파일러 버전을 명시한다.

```
go 1.21
toolchain go1.21.5
```

Go 1.21부터 Go 툴체인 자체도 모듈처럼 관리된다. `GOTOOLCHAIN` 환경변수로 동작을 제어한다.

```bash
# go.mod의 toolchain 버전보다 낮으면 자동으로 최신 버전 다운로드
export GOTOOLCHAIN=auto

# go.mod에 명시된 toolchain 버전만 사용
export GOTOOLCHAIN=local

# 특정 버전 고정
export GOTOOLCHAIN=go1.21.5
```

`GOTOOLCHAIN=auto`일 때 현재 설치된 Go 버전이 `go.mod`의 `toolchain` 버전보다 낮으면, Go가 자동으로 적합한 버전을 다운로드해서 실행한다. CI에서 예상치 못한 버전이 사용되는 원인이 되기도 하니, CI 환경에서는 `GOTOOLCHAIN=local`로 고정하는 게 낫다.

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

## retract 디렉티브 (Go 1.16+)

`retract`는 이미 배포한 버전을 철회할 때 쓴다. 버그가 심하거나 잘못 배포된 버전을 사용자가 받지 않도록 막는다.

```
module github.com/myorg/mylib

go 1.16

retract (
    v1.3.0 // 치명적 데이터 손실 버그. v1.3.1 사용 권장
    v1.2.5 // 실수로 배포된 미완성 버전
    [v1.1.0, v1.1.9] // v1.1.x 전체 범위 철회
)
```

`retract`를 추가한 뒤 새 버전을 배포해야 효과가 있다. 새 버전의 `go.mod`에 retract를 넣고 배포하면, 그때부터 `go get`이나 `go mod tidy`를 실행할 때 철회된 버전을 경고와 함께 표시한다.

```bash
# 철회된 버전 목록 확인
go list -m -retracted all
```

`retract`는 실제로 버전을 삭제하지 않는다. 이미 그 버전을 쓰고 있는 프로젝트의 `go.mod`를 강제로 바꾸지도 않는다. 새로 사용하려는 사람에게 경고를 보여주는 것이다. 프록시 서버는 철회된 버전도 계속 제공한다.

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

## 메이저 버전 관리

Go 모듈에서 v2 이상의 메이저 버전은 모듈 경로에 버전을 포함해야 한다.

```
github.com/myorg/mylib      → v0.x, v1.x
github.com/myorg/mylib/v2   → v2.x
github.com/myorg/mylib/v3   → v3.x
```

이렇게 설계된 이유가 있다. 메이저 버전 업은 하위 호환성을 깬다는 신호다. 하나의 프로그램에서 `mylib v1`과 `mylib v2`를 동시에 쓸 수 있어야 하는데, 경로가 같으면 둘을 구분할 방법이 없다. 경로에 `/v2`를 붙이면 Go 입장에서 완전히 다른 모듈이 된다.

새 메이저 버전을 배포할 때는 `go.mod`의 module 경로를 바꿔야 한다.

```
# v1
module github.com/myorg/mylib

# v2로 올릴 때
module github.com/myorg/mylib/v2
```

사용하는 쪽도 import 경로를 바꿔야 한다.

```go
// v1 사용
import "github.com/myorg/mylib"

// v2 사용
import "github.com/myorg/mylib/v2"
```

이 규칙을 지키지 않고 v2를 배포하면 `+incompatible` 문제가 생긴다.

디렉토리 구조는 두 가지 방식 중 하나를 선택한다. major branch 방식은 `main` 브랜치에서 v1을 유지하고 `v2` 브랜치에서 v2를 관리하는 방식이다. major subdirectory 방식은 같은 브랜치에 `v2/` 디렉토리를 만들어 관리한다. 어느 쪽이든 상관없지만, 팀 내에서 하나로 통일해야 한다.

## pseudo-version

`go get`으로 태그가 없는 특정 커밋을 지정하거나, 비공개 저장소의 최신 커밋을 받아오면 pseudo-version이 생긴다.

```
github.com/some/lib v0.0.0-20231015123456-abcdef012345
```

형식은 `vX.Y.Z-yyyymmddhhmmss-abcdefabcdef`다. 타임스탬프는 UTC 기준 커밋 시간이고, 마지막 12자리는 커밋 해시의 앞부분이다.

pseudo-version이 생기는 상황은 세 가지다. 아직 릴리즈 태그가 없는 모듈을 `@latest`나 `@main`으로 받아올 때. 특정 커밋 해시를 직접 지정할 때(`go get lib@abc123`). 태그는 있는데 `go.mod`가 없는 구버전 패키지를 받아올 때다.

```bash
# 특정 브랜치의 최신 커밋
go get github.com/some/lib@main

# 특정 커밋 해시
go get github.com/some/lib@abc1234

# 결과: go.mod에 pseudo-version으로 기록됨
```

pseudo-version은 `go mod tidy`를 실행할 때 자동으로 유효성이 검사된다. 커밋이 존재하지 않거나 해시가 다르면 에러가 난다. 운영 코드에서 pseudo-version을 쓰는 건 그 커밋이 언제든 force-push로 사라질 수 있어서 위험하다. 가능하면 정식 태그를 기다리거나 fork해서 태그를 붙이는 게 낫다.

## +incompatible 접미사

모듈 시스템 도입 이전에 배포된 v2 이상의 패키지를 참조하면 `+incompatible` 접미사가 붙는다.

```
github.com/some/old-lib v2.3.0+incompatible
```

이 패키지는 `go.mod`가 없거나, 있더라도 module 경로에 `/v2`를 붙이지 않은 채 v2를 배포한 경우다. Go는 이 패키지를 v1 호환 방식으로 취급하면서 `+incompatible`로 표시한다.

실제로 겪는 문제는 두 가지다. 하나는 이 패키지가 하위 호환성을 깼는데 그걸 알기 어렵다는 것이다. `+incompatible`이 붙어있으면 API 변경에 주의해야 한다. 다른 하나는 패키지 제작자가 나중에 `go.mod`를 추가하면 `+incompatible` 없이 새 버전이 배포되는데, 이 둘이 의존 그래프에서 충돌할 수 있다.

```bash
# +incompatible 패키지 확인
go list -m all | grep incompatible
```

`+incompatible` 패키지를 장기간 유지하는 건 권장하지 않는다. 해당 라이브러리가 업데이트됐다면 정식 모듈 버전으로 마이그레이션하는 게 낫다.

## 모듈 그래프 프루닝과 lazy loading (Go 1.17+)

Go 1.17 이전에는 모든 의존성의 전체 의존 그래프를 로드했다. A → B → C → D 관계에서 A를 쓰면 B, C, D의 의존성까지 전부 `go.mod`에 반영됐다.

Go 1.17부터는 `go.mod`에 `go 1.17` 이상이 명시되면 lazy loading이 활성화된다.

lazy loading에서는 직접 의존하는 모듈의 `go.mod`만 읽는다. A → B에서 B의 하위 의존성은 B의 `go.mod`를 직접 참조하지 않는 한 로드하지 않는다. 대신 `go.mod`에 직접 의존성의 모든 간접 의존성이 기록된다. 파일이 길어지는 대신 빌드 시간과 메모리 사용이 줄어든다.

실제로 Go 1.17 이상으로 올리고 `go mod tidy`를 실행하면 `// indirect` 항목이 눈에 띄게 늘어난다. 이게 정상이다. 이전에는 깊은 의존성을 암묵적으로 처리했는데, 이제는 명시적으로 기록하는 방식으로 바뀐 것이다.

모듈 그래프 프루닝의 이점은 대규모 모노레포에서 두드러진다. 사용하지 않는 모듈의 `go.mod`를 읽느라 시간을 쓰지 않는다. `go.mod`의 `go` 버전을 올리는 것만으로 이 이점을 얻는다.

## GOPROXY fallback 동작

`GOPROXY`는 쉼표로 구분된 프록시 목록을 받는다.

```bash
export GOPROXY=https://proxy.golang.org,direct
```

각 항목은 순서대로 시도된다. 첫 번째 프록시에서 모듈을 찾으면 거기서 받아온다. 찾지 못하거나 에러가 나면 다음 항목으로 넘어간다. `direct`는 VCS에서 직접 받아오는 것이다.

에러 처리에서 주의할 점이 있다. 프록시가 404나 410을 반환하면 "이 모듈은 없다"고 판단해서 fallback을 시도한다. 그런데 500이나 네트워크 에러가 나면 기본적으로 에러로 처리하고 멈춘다. fallback을 강제하려면 `|` 구분자를 쓴다.

```bash
# | 앞의 프록시는 어떤 에러가 나도 다음으로 넘어감
export GOPROXY=https://proxy.internal.com|https://proxy.golang.org,direct
```

쉼표(`,`)와 파이프(`|`)의 차이가 중요하다. `,`는 404/410에만 fallback하고, `|`는 모든 에러에 fallback한다.

`off`를 넣으면 그 이후 항목으로는 절대 진행하지 않는다.

```bash
# proxy.internal.com에서 못 찾으면 에러. 외부 인터넷 차단 환경에서 씀
export GOPROXY=https://proxy.internal.com,off
```

CI에서 외부 접근을 차단하고 싶을 때 `off`를 끝에 추가하면, 사설 프록시에 없는 패키지를 실수로 외부에서 받아오는 상황을 막는다.

## private 모듈 설정

회사 내부 모듈은 public proxy를 거치면 안 된다. Go는 기본적으로 `GOPROXY=https://proxy.golang.org,direct`를 쓰기 때문에, 별도 설정 없이는 모든 모듈 요청이 proxy를 거친다.

**GOPRIVATE**

가장 먼저 설정해야 하는 환경변수다.

```bash
export GOPRIVATE=github.com/myorg/*,gitlab.internal.com/*
```

`GOPRIVATE`을 설정하면 해당 패턴의 모듈은 proxy를 거치지 않고 직접 VCS에서 받아온다. 동시에 sum DB 검증도 건너뛴다.

**GONOSUMDB / GONOSUMCHECK**

`GONOSUMDB`는 sum DB 검증을 건너뛸 모듈을 지정한다. `GOPRIVATE`을 쓰면 두 설정이 자동으로 포함되기 때문에, 별도로 설정할 필요는 거의 없다. 다만 proxy는 통하되 sum 검증만 건너뛰고 싶을 때는 `GONOSUMDB`를 따로 쓴다.

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

## GOMODCACHE 관리

모듈을 처음 다운로드하면 `GOMODCACHE`에 캐시된다. 기본 경로는 `$GOPATH/pkg/mod`다.

```bash
# 현재 캐시 경로 확인
go env GOMODCACHE

# 캐시 전체 크기 확인
du -sh $(go env GOMODCACHE)
```

캐시 파일은 읽기 전용(0444)으로 저장된다. 실수로 수정하거나 삭제하지 못하도록 막는 것인데, 수동으로 지우려면 권한을 바꿔야 한다. `go clean -modcache`를 쓰면 Go가 권한 처리까지 해준다.

```bash
# 캐시 전체 삭제
go clean -modcache

# dry-run으로 삭제 대상 확인
go clean -modcache -n
```

디스크 공간이 부족할 때 `GOMODCACHE`가 수 GB씩 쌓여있는 경우가 있다. 여러 버전을 번갈아가며 개발하는 환경에서 특히 빠르게 쌓인다. 주기적으로 `go clean -modcache`를 실행하거나, GOMODCACHE 경로를 tmpfs나 별도 볼륨으로 분리하는 방법을 쓴다.

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

# 특정 패키지가 왜 의존성에 포함됐는지 추적
go mod why github.com/some/lib

# 모듈 단위로 추적
go mod why -m github.com/some/lib

# 다운로드된 모듈의 무결성 검증
go mod verify
```

**go mod why**

`go mod why`는 왜 특정 패키지가 빌드에 포함됐는지 추적한다.

```bash
$ go mod why github.com/pelletier/go-toml/v2

# github.com/pelletier/go-toml/v2
github.com/myorg/myapp
github.com/gin-gonic/gin
github.com/pelletier/go-toml/v2
```

의존성 정리를 하다가 "이 패키지를 왜 쓰고 있지?"라는 의문이 들 때 쓴다. `-m` 플래그를 붙이면 패키지 단위가 아닌 모듈 단위로 추적한다.

**go mod verify**

`go mod verify`는 로컬에 캐시된 모듈 파일들이 `go.sum`의 해시와 일치하는지 검사한다.

```bash
$ go mod verify
all modules verified
```

캐시가 손상됐거나 누군가 수동으로 파일을 건드렸을 때 감지한다. CI에서 빌드 전에 실행하면 환경 신뢰성을 높인다.

`go get -u ./...`는 가끔 예상치 못한 버전으로 올라가서 빌드가 깨지는 경우가 있다. 운영 중인 서비스라면 라이브러리 하나씩 올리고 테스트하는 게 안전하다.

## CI/Dockerfile에서 go.mod 레이어 캐싱

Docker 빌드에서 의존성 다운로드를 매번 반복하지 않으려면 레이어 순서가 중요하다.

```dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

# go.mod와 go.sum을 먼저 복사해서 별도 레이어로 만든다
COPY go.mod go.sum ./
RUN go mod download

# 소스 코드는 그 다음에 복사
COPY . .
RUN go build -o /app/server ./cmd/server
```

`go.mod`와 `go.sum`이 변경되지 않으면 `go mod download` 레이어가 캐시에서 재사용된다. 소스 코드만 변경됐을 때 의존성 다운로드를 건너뛰는 게 핵심이다.

멀티스테이지 빌드에서는 builder 스테이지에서 캐시를 최대한 활용한다.

```dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server ./cmd/server

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/server /app/server
CMD ["/app/server"]
```

`go mod verify`를 `go mod download` 직후에 실행하면 다운로드된 파일의 무결성을 확인하고 넘어간다.

BuildKit의 `--mount=type=cache`를 쓰면 빌드 간에 모듈 캐시를 유지한다.

```dockerfile
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
```

컨테이너 레이어가 아닌 BuildKit 캐시에 모듈을 저장하기 때문에 이미지 크기는 커지지 않으면서 반복 빌드 속도를 높인다.

GitHub Actions에서는 `go.sum`을 캐시 키로 쓰는 게 표준적인 방법이다.

```yaml
- name: Cache Go modules
  uses: actions/cache@v3
  with:
    path: |
      ~/go/pkg/mod
      ~/.cache/go-build
    key: ${{ runner.os }}-go-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      ${{ runner.os }}-go-

- name: Download dependencies
  run: go mod download
```

`~/go/pkg/mod`(모듈 캐시)와 `~/.cache/go-build`(빌드 캐시) 두 경로를 함께 캐시하면 의존성 다운로드와 컴파일 결과 모두를 재사용한다.
