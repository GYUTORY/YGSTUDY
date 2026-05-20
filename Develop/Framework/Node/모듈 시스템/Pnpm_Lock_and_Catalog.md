---
title: pnpm-lock.yaml과 catalog
tags: [framework, node, 모듈-시스템, pnpm, lockfile, catalog, monorepo]
updated: 2026-05-20
---

# pnpm-lock.yaml과 catalog

## pnpm-lock.yaml이 하는 일

`package.json`에는 `"react": "^18.2.0"` 같은 범위 표기가 들어간다. 범위 표기는 "18.2.0 이상, 19 미만 중 아무거나"라는 뜻이라 설치 시점마다 다른 버전이 깔릴 수 있다. 어제는 18.2.0이었는데 오늘은 18.3.1이 깔리면 빌드가 깨지는 일이 종종 생긴다. lock 파일은 "이번 설치에서 실제로 이 버전들을 썼다"를 박제하는 역할을 한다.

`pnpm-lock.yaml`은 npm의 `package-lock.json`이나 yarn의 `yarn.lock`과 같은 자리에 있지만, 내부 구조는 꽤 다르다. pnpm은 심볼릭 링크 기반의 `node_modules`를 만들기 때문에 lock 파일에도 "어떤 패키지가 어떤 의존성을 보고 있는지"를 좀 더 명시적으로 적는다.

## lock 파일의 내부 구조

직접 열어보면 대략 이런 형태다.

```yaml
lockfileVersion: '9.0'

settings:
  autoInstallPeers: true
  excludeLinksFromLockfile: false

importers:
  .:
    dependencies:
      react:
        specifier: ^18.2.0
        version: 18.2.0
      next:
        specifier: 14.1.0
        version: 14.1.0(react@18.2.0)(react-dom@18.2.0)
    devDependencies:
      typescript:
        specifier: ^5.3.0
        version: 5.3.3

packages:

  react@18.2.0:
    resolution: {integrity: sha512-...}
    engines: {node: '>=0.10.0'}

  next@14.1.0:
    resolution: {integrity: sha512-...}
    engines: {node: '>=18.17.0'}
    peerDependencies:
      react: ^18.2.0
      react-dom: ^18.2.0

snapshots:

  react@18.2.0:
    dependencies:
      loose-envify: 1.4.0

  next@14.1.0(react@18.2.0)(react-dom@18.2.0):
    dependencies:
      '@next/env': 14.1.0
      react: 18.2.0
      react-dom: 18.2.0(react@18.2.0)
```

핵심 섹션은 네 개다.

**lockfileVersion**: lock 파일 포맷 버전. pnpm 9 이상은 `'9.0'`을 쓴다. 이게 다르면 같은 저장소에서 작업하는 사람들끼리 lock 파일이 자꾸 갈아엎힌다. CI와 로컬의 pnpm 버전이 다를 때 가장 흔히 터지는 문제다.

**importers**: 워크스페이스에 속한 각 패키지가 어떤 의존성을 선언했는지 적는다. 모노레포가 아닌 단일 프로젝트면 `.` 하나만 있다. 모노레포면 `apps/web`, `packages/ui` 같은 키가 줄줄이 생긴다. `specifier`는 `package.json`에 적힌 범위 표기 그대로, `version`은 실제로 해결된 버전이다.

**packages**: 의존성 트리에 등장한 모든 패키지의 메타데이터. `resolution.integrity`로 다운로드한 tarball의 해시를 검증한다. 누군가 레지스트리에서 같은 버전을 다른 내용으로 갈아치우는 사고가 나면 여기서 걸린다.

**snapshots**: 각 패키지가 실제로 어떤 의존성 그래프 위에서 해결됐는지. `next@14.1.0(react@18.2.0)(react-dom@18.2.0)` 같은 표기가 보이는데, peer dependency가 다르면 같은 next라도 다른 스냅샷으로 취급된다. 같은 라이브러리를 두 군데서 다른 peer로 쓰면 lock 파일에 두 번 등장하는 이유가 이거다.

## 왜 yaml인가

npm은 json, yarn은 자체 포맷이다. pnpm이 yaml을 고른 이유는 단순하다. 디스플레이가 사람이 읽기 쉽고, 키 충돌 시 diff가 비교적 깔끔하게 나온다. 그래도 100MB짜리 lock 파일은 누구한테든 지옥이다.

## frozen-lockfile의 동작

`pnpm install`은 기본적으로 lock 파일을 "필요하면 업데이트"한다. 누군가 `package.json`에 새 의존성을 추가하고 커밋했는데 lock 파일은 안 올렸다면, 내가 `pnpm install`을 돌리는 순간 내 머신에서 lock 파일이 새로 쓰여진다.

CI에서는 이게 문제가 된다. CI는 "lock 파일에 적힌 대로만 설치해라. 거기 없는 게 있으면 실패해라"를 원한다. 그래서 `--frozen-lockfile` 옵션이 있다.

```bash
pnpm install --frozen-lockfile
```

pnpm 7부터는 `CI=true` 환경변수가 있으면 자동으로 `--frozen-lockfile`이 켜진다. GitHub Actions, GitLab CI, CircleCI 같은 데서는 `CI=true`가 기본으로 잡혀 있어서 별도로 안 적어도 frozen 모드로 돈다. 로컬에서 만든 lock 파일이 `package.json`과 어긋난 채 push되면 CI에서 다음 메시지로 죽는다.

```
ERR_PNPM_OUTDATED_LOCKFILE  Cannot install with "frozen-lockfile" because pnpm-lock.yaml is not up to date with package.json
```

이 에러가 뜨면 로컬에서 `pnpm install`을 다시 돌려서 lock 파일을 동기화하고 같이 커밋하면 된다. lock 파일을 안 올리려는 시도는 거의 항상 며칠 안에 다른 사람의 빌드를 깨뜨린다.

반대 옵션도 있다. `--no-frozen-lockfile`은 lock 파일을 강제로 업데이트하게 한다. CI에서 lock 파일을 자동으로 갱신하는 잡을 돌리거나, 임시로 종속성을 검증하고 싶을 때 쓴다. 일반적인 CI에서는 켜지 않는다.

## lock 파일 충돌 해결

여러 명이 동시에 의존성을 건드리면 `pnpm-lock.yaml`에 충돌이 난다. yaml이라서 git이 머지를 해주긴 하는데, 패키지 트리가 얽히면 머지 결과가 깨진 lock 파일이 되는 경우가 많다. 머지 결과를 그대로 커밋하면 CI에서 integrity 해시 검증에 걸려서 죽는다.

해결 방법은 단순하다.

```bash
# 충돌난 lock 파일을 일단 무시하고 main 기준으로 맞춘 뒤
git checkout origin/main -- pnpm-lock.yaml

# pnpm한테 다시 만들라고 시킨다
pnpm install

# 결과를 커밋
git add pnpm-lock.yaml
git commit
```

`pnpm install`은 `package.json`과 기존 lock 파일을 비교해서 차이만 갱신한다. 머지 충돌이 난 상태에서 돌려도 알아서 정리해준다. 손으로 yaml을 편집해서 충돌을 푸는 건 거의 항상 나쁜 결과로 끝난다.

pnpm 8.6부터는 `pnpm install`이 충돌난 lock 파일을 자동으로 감지하고 복구해주는 기능이 들어갔다. 충돌 마커가 남아 있는 상태에서 `pnpm install`을 돌리면 알아서 처리한다. 그래도 결과는 항상 한 번 확인해야 한다.

## catalog가 등장한 이유

모노레포에서 같은 라이브러리를 여러 패키지가 쓴다. 예를 들어 `apps/web`, `apps/admin`, `packages/ui`가 전부 React를 쓴다고 하자. 각각의 `package.json`에 `"react": "^18.2.0"`이 들어간다.

여기서 문제는 누가 한 명만 `^18.3.0`으로 바꾸면 모노레포 안에 React 두 버전이 공존하게 된다는 거다. React는 인스턴스가 두 개면 hooks가 깨지는 등 별별 문제를 일으킨다. styled-components, react-query 같은 라이브러리도 마찬가지다.

해결책은 모든 `package.json`을 일일이 동기화하는 거였다. 누군가 까먹으면 그날 저녁에 누군가 야근한다. syncpack 같은 외부 도구로 검사하는 팀도 있고, lint rule로 강제하는 팀도 있다.

pnpm 9.5에서 정식 도입된 `catalog`는 이 문제를 워크스페이스 수준에서 풀어준다.

## catalog 기본 사용법

`pnpm-workspace.yaml`에 catalog 섹션을 만든다.

```yaml
packages:
  - "apps/*"
  - "packages/*"

catalog:
  react: ^18.2.0
  react-dom: ^18.2.0
  typescript: ^5.3.0
  zod: ^3.22.4
```

각 패키지의 `package.json`에서는 버전 자리에 `catalog:` 프로토콜을 쓴다.

```json
{
  "name": "@myorg/web",
  "dependencies": {
    "react": "catalog:",
    "react-dom": "catalog:"
  },
  "devDependencies": {
    "typescript": "catalog:"
  }
}
```

`pnpm install`을 돌리면 `catalog:` 부분이 `pnpm-workspace.yaml`의 버전 범위로 해결된다. lock 파일에는 실제 버전이 박제된다. 모든 워크스페이스 패키지가 같은 React 버전을 보게 된다.

React를 18.3으로 올리고 싶으면 `pnpm-workspace.yaml`의 한 줄만 고치면 된다. 각 패키지 `package.json`을 돌아다닐 필요가 없다.

## 명명된 catalog

`catalog`는 기본 카탈로그고, `catalogs` 아래에 이름을 붙여서 여러 개를 만들 수도 있다. React 18을 쓰는 앱과 React 19로 마이그레이션 중인 앱이 공존하는 시기에 유용하다.

```yaml
packages:
  - "apps/*"
  - "packages/*"

catalog:
  typescript: ^5.3.0

catalogs:
  react18:
    react: ^18.2.0
    react-dom: ^18.2.0
  react19:
    react: ^19.0.0
    react-dom: ^19.0.0
```

사용할 때는 카탈로그 이름을 명시한다.

```json
{
  "name": "@myorg/legacy-admin",
  "dependencies": {
    "react": "catalog:react18",
    "react-dom": "catalog:react18"
  }
}
```

```json
{
  "name": "@myorg/new-web",
  "dependencies": {
    "react": "catalog:react19",
    "react-dom": "catalog:react19"
  }
}
```

`catalog:` (이름 생략)은 기본 카탈로그를, `catalog:react18`처럼 콜론 뒤에 이름을 붙이면 명명된 카탈로그를 본다.

## catalog가 적용되는 시점

`catalog:` 프로토콜은 pnpm이 의존성을 해결하는 시점에 실제 버전으로 변환된다. 결과물인 lock 파일에는 catalog 표기가 그대로 남아 있지만, 각 importer의 `version` 필드에는 실제 해결된 버전이 들어간다.

```yaml
importers:
  apps/web:
    dependencies:
      react:
        specifier: 'catalog:'
        version: 18.2.0
```

`specifier`가 `'catalog:'`로 남아 있는 게 보인다. 이게 의도된 동작이다. 누가 `pnpm-workspace.yaml`의 React 버전을 올리면 `specifier`는 그대로지만 `version`이 바뀐다.

## 외부로 publish할 때의 함정

`catalog:` 표기는 pnpm 워크스페이스 안에서만 의미가 있다. 워크스페이스 안의 패키지를 npm에 publish하면 외부 사용자는 `catalog:`가 뭔지 모른다. 그대로 publish하면 사용자가 설치할 때 깨진다.

pnpm은 publish 시점에 `catalog:`를 실제 버전으로 치환해서 publish해준다. `pnpm publish`나 `pnpm pack`을 거치면 `package.json`이 자동으로 변환된다. 직접 `npm publish`를 돌리면 변환이 안 일어나니까, 라이브러리 publish가 있는 워크스페이스라면 `pnpm publish`를 써야 한다.

내부용 패키지만 있는 모노레포라면 신경 쓸 필요 없다. 외부에 publish하는 라이브러리를 만드는 회사에서 catalog를 도입할 때 가장 먼저 확인할 부분이다.

## catalog로 풀기 어려운 케이스

catalog는 만능이 아니다. 다음 경우에는 도입하기 전에 한 번 더 생각해야 한다.

**peer dependency**: 어떤 패키지의 peer dependency를 catalog로 쓰는 건 가능하지만, peer 충돌이 났을 때 추적이 어려워진다. peer는 보통 직접 명시하는 게 디버깅하기 편하다.

**버전 범위가 다른 게 의도일 때**: 가끔 한 앱은 의도적으로 옛 버전에 묶여 있어야 하는 경우가 있다. 외부 SDK가 특정 React 버전만 지원하는 식이다. 이런 패키지는 catalog에서 빼고 직접 명시해야 한다. catalog에 넣고 예외 처리하기 시작하면 catalog의 의미가 없어진다.

**type-only 의존성**: `@types/node` 같은 거는 catalog에 넣어도 문제는 없는데, 종종 TypeScript 버전에 묶여서 같이 올려야 하는 케이스가 생긴다. 따로 빼서 관리하는 팀이 많다.

## 모노레포 도입 사례

실제로 catalog를 적용해서 정리한 케이스를 보면 대략 이런 식이다.

도입 전:
- 패키지 12개, 공통으로 쓰는 의존성 약 30개
- `package.json` 12군데에 같은 의존성이 흩어져 있음
- 분기마다 의존성 업데이트 PR을 만들면 변경 파일이 50개 이상
- 누군가 한 명만 까먹으면 빌드는 통과하지만 런타임에 에러

도입 후 `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/*"
  - "packages/*"

catalog:
  # 프레임워크
  react: ^18.3.1
  react-dom: ^18.3.1
  next: ^14.2.0

  # 상태 관리
  zustand: ^4.5.0
  '@tanstack/react-query': ^5.40.0

  # 유틸
  zod: ^3.23.0
  date-fns: ^3.6.0
  lodash-es: ^4.17.21

  # 타입
  typescript: ^5.4.0
  '@types/node': ^20.12.0

  # 테스트
  vitest: ^1.6.0
  '@testing-library/react': ^15.0.0
```

각 패키지의 `package.json`은 이렇게 단순해진다.

```json
{
  "name": "@myorg/web",
  "dependencies": {
    "react": "catalog:",
    "react-dom": "catalog:",
    "next": "catalog:",
    "zustand": "catalog:",
    "@tanstack/react-query": "catalog:",
    "zod": "catalog:"
  },
  "devDependencies": {
    "typescript": "catalog:",
    "@types/node": "catalog:",
    "vitest": "catalog:"
  }
}
```

의존성 업데이트 PR은 `pnpm-workspace.yaml` 한 줄 변경과 `pnpm-lock.yaml` 갱신, 그게 끝이다. 코드 리뷰도 훨씬 쉬워진다.

## 도입 시 주의사항

**Renovate / Dependabot 호환**: 의존성 업데이트 봇이 `catalog:` 표기를 인식해야 한다. Renovate는 pnpm catalog를 지원한다 (2024년 중반부터). Dependabot은 한참 동안 catalog를 인식하지 못했고, 2026년 초까지도 완전한 지원은 들어오지 않았다. Dependabot을 쓰는 팀은 catalog 도입 전에 한 번 확인해야 한다.

**기존 코드 마이그레이션**: 한꺼번에 모든 의존성을 catalog로 옮기지 말고, 공통으로 쓰이는 것 5~10개부터 시작하는 게 안전하다. 모든 패키지에서 같은 버전을 쓰는 게 확인된 것만 catalog로 옮기고, 버전이 갈리는 건 그대로 둔다. 정리하면서 의도하지 않은 버전 불일치를 발견하기 마련이다.

**Storybook이나 외부 도구**: 일부 도구가 catalog 표기를 못 읽는 경우가 있다. Storybook의 일부 addon이나 npm-check-updates 같은 도구는 catalog 도입 후 한동안 호환성 이슈가 있었다. 도입 직후에는 빌드 파이프라인 전체를 한 번 돌려서 깨지는 곳이 없는지 확인하는 게 좋다.

**catalog가 너무 커지면**: 의존성이 100개 넘게 catalog에 들어가면 `pnpm-workspace.yaml`이 너무 길어진다. 명명된 카탈로그로 카테고리별로 쪼개거나, 굳이 모든 패키지에서 공유하지 않는 건 catalog에서 빼는 정리가 필요하다.

## lock 파일과 catalog의 상호작용

catalog를 도입하면 lock 파일에 있는 `specifier` 필드 값이 `^18.2.0` 같은 범위 표기에서 `'catalog:'` 또는 `'catalog:react18'` 같은 형태로 바뀐다. 기존 lock 파일을 그대로 두고 `package.json`만 catalog로 바꿔도, 다음 `pnpm install`에서 lock 파일이 알아서 정리된다.

기존 프로젝트에서 catalog 도입 후 처음 lock 파일을 만들 때는 변경 줄 수가 수백~수천 줄이 된다. 이 PR은 의존성 변경 PR과 분리해서 올리는 게 리뷰하는 사람에게 친절하다. catalog 도입은 catalog 도입대로, 의존성 버전 변경은 그 다음에 별도로 처리한다.

## 참조

- [pnpm Catalogs 공식 문서](https://pnpm.io/catalogs)
- [pnpm-lock.yaml 포맷](https://pnpm.io/9.x/git#lockfiles)
- [pnpm Workspace 설정](https://pnpm.io/pnpm-workspace_yaml)
- [pnpm CLI - install 옵션](https://pnpm.io/cli/install)
- [Renovate Bot - pnpm catalog 지원](https://docs.renovatebot.com/modules/manager/pnpm-catalog/)
