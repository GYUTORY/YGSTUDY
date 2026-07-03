---
title: pnpm
tags: [framework, node, 모듈-시스템, pnpm, store, monorepo, nodejs]
updated: 2026-05-27
---

# pnpm

pnpm은 npm, yarn과 같은 자리에 놓이는 패키지 매니저지만 `node_modules`를 만드는 방식이 근본적으로 다르다. 이 문서는 store와 설치 동작에 집중한다. lock 파일 포맷과 catalog는 [Pnpm_Lock_and_Catalog.md](Pnpm_Lock_and_Catalog.md)에서 따로 다룬다.

설치가 빠르다거나 디스크를 덜 쓴다는 건 결과일 뿐이고, 실제로 일하다 보면 "왜 npm에서는 되던 import가 pnpm에서는 안 되지" 같은 문제로 먼저 부딪힌다. 그 차이가 어디서 오는지를 알아야 마이그레이션이나 CI 세팅에서 시간을 안 버린다.

## content-addressable store

npm은 프로젝트마다 `node_modules`에 패키지를 통째로 복사한다. lodash를 쓰는 프로젝트가 10개면 lodash가 10번 복사된다. pnpm은 패키지를 전역 store 한 곳에 두고, 프로젝트에서는 그 파일을 링크로 가리킨다.

store 위치는 환경마다 다르다. 직접 확인하려면:

```bash
pnpm store path
# /Users/me/Library/pnpm/store/v3   (macOS 예시)
```

여기서 핵심은 store가 **패키지 단위가 아니라 파일 단위**로 저장된다는 점이다. 각 파일은 내용을 해시한 값으로 식별된다. 그래서 lodash 4.17.20과 4.17.21이 있을 때, 두 버전 사이에서 바뀌지 않은 파일은 store에 한 번만 저장된다. 버전을 올려도 실제로 디스크에 새로 쓰이는 건 변경된 파일뿐이다.

store 내부는 대략 이렇게 생겼다.

```
store/v3/
├── files/
│   ├── 00/
│   │   └── 1a2b3c...    (파일 내용, 해시 이름)
│   ├── 01/
│   │   └── 4d5e6f...
│   └── ...
└── index/
    └── <registry>-<pkg>-<version>.json   (어떤 파일들이 이 패키지를 구성하는지)
```

`index`의 json은 "이 패키지는 이런 경로의 파일들로 이루어져 있고, 각 파일의 내용은 이 해시다"라는 매핑이다. 설치할 때 pnpm은 이 인덱스를 보고 store의 파일들을 프로젝트로 링크한다.

store는 시간이 지나면 안 쓰는 파일이 쌓인다. 정리는 수동이다.

```bash
pnpm store prune   # 어떤 프로젝트도 참조하지 않는 파일 제거
```

CI에서 store를 캐싱하면 이게 무한정 커지는 경우가 있다. 캐시 키를 잘못 잡으면 매 빌드마다 새 store가 쌓여서 캐시 용량 한도에 걸린다. 뒤에서 다시 다룬다.

## 하드링크와 심볼릭 링크

store에서 프로젝트로 파일을 가져오는 방법이 하드링크다. 복사가 아니라 같은 inode를 두 경로가 가리키는 것이라, 디스크를 추가로 쓰지 않는다. 그래서 store에 한 번 받아둔 패키지는 새 프로젝트에서 설치할 때 거의 즉시 끝난다. 네트워크도 디스크 쓰기도 없이 링크만 거는 작업이기 때문이다.

여기서 운영상 함정이 두 개 있다.

하나는 **store와 프로젝트가 같은 파일시스템에 있어야 한다**는 점이다. 하드링크는 파일시스템 경계를 넘지 못한다. store는 홈 디렉토리에 있는데 프로젝트가 다른 마운트(별도 볼륨, Docker의 다른 레이어, 네트워크 드라이브)에 있으면 하드링크가 안 걸린다. 이때 pnpm은 조용히 복사로 폴백한다. 설치는 되지만 느려지고 디스크가 늘어난다. "pnpm인데 왜 안 빨라지지" 싶으면 store와 프로젝트가 같은 드라이브에 있는지부터 본다.

가져오는 방식은 설정으로 바꿀 수 있다.

```ini
# .npmrc
package-import-method=auto
```

`auto`가 기본이고, 파일시스템이 지원하면 clone(copy-on-write)을, 안 되면 hardlink를, 그것도 안 되면 copy를 쓴다. macOS의 APFS나 btrfs처럼 CoW를 지원하는 파일시스템에서는 clone이 걸려서 store와 프로젝트 파일이 독립적이다. 반면 ext4 같은 데서는 하드링크라서 같은 inode를 공유한다.

이게 두 번째 함정으로 이어진다. **하드링크 상태에서 `node_modules` 안의 파일을 직접 고치면 store의 원본이 같이 바뀐다.** 디버깅한다고 `node_modules/some-lib/index.js`에 `console.log`를 박으면, 그 라이브러리를 쓰는 다른 모든 프로젝트가 오염된다. 라이브러리를 고쳐야 하면 직접 편집하지 말고 patch를 쓴다.

```bash
pnpm patch some-lib@1.2.3
# 임시 디렉토리에서 수정한 뒤
pnpm patch-commit <임시경로>
# package.json에 patchedDependencies가 추가되고, 설치마다 패치가 적용된다
```

심볼릭 링크는 store가 아니라 `node_modules` 내부 구조를 만드는 데 쓴다. 이게 pnpm의 `node_modules`가 npm과 완전히 다르게 생긴 이유다.

## node_modules가 평탄하지 않다

npm과 yarn classic은 의존성을 `node_modules` 최상위로 끌어올린다(hoisting). 내가 직접 선언한 패키지든, 그 패키지가 끌고 온 transitive 의존성이든 전부 평탄하게 펼쳐진다. 결과적으로 최상위 `node_modules`에 수백 개 폴더가 한 줄로 깔린다.

pnpm의 `node_modules`는 이렇게 생겼다.

```
node_modules/
├── .pnpm/
│   ├── express@4.18.2/
│   │   └── node_modules/
│   │       ├── express/          (store에서 하드링크된 실제 파일)
│   │       ├── body-parser/      (express가 의존하는 것 → 심볼릭 링크)
│   │       └── cookie/           (심볼릭 링크)
│   ├── body-parser@1.20.1/
│   │   └── node_modules/
│   │       └── body-parser/
│   └── cookie@0.5.0/
│       └── node_modules/
│           └── cookie/
└── express -> .pnpm/express@4.18.2/node_modules/express   (심볼릭 링크)
```

최상위 `node_modules`에는 내가 `package.json`에 직접 적은 의존성만 심볼릭 링크로 올라온다. 위 예시에서 express만 직접 설치했다면 최상위에는 express 링크 하나만 보인다. body-parser나 cookie는 express의 transitive 의존성이라 `.pnpm` 안에만 있고 최상위에는 없다.

Node.js의 모듈 해석은 `node_modules`를 위로 거슬러 올라가며 찾는다. 그래서 내 코드에서 `require('express')`는 최상위 심볼릭 링크를 타고 들어가 정상 동작한다. 그런데 `require('body-parser')`는 최상위에 그게 없으니까 실패한다. 내가 body-parser를 직접 설치한 적이 없기 때문이다.

```js
// package.json에 express만 있고 body-parser는 없는 상태

const express = require('express');     // OK
const bodyParser = require('body-parser'); // Error: Cannot find module 'body-parser'
```

npm에서는 둘 다 됐다. express가 끌고 온 body-parser가 최상위에 펼쳐져 있어서 우연히 import가 됐던 거다. 이렇게 선언하지 않은 패키지를 우연히 쓰게 되는 걸 유령 의존성(phantom dependency)이라고 한다. pnpm은 transitive 의존성을 최상위에 올리지 않으니까 유령 의존성이 컴파일/실행 단계에서 바로 막힌다.

이게 pnpm을 쓰는 가장 실질적인 이유다. body-parser를 직접 쓰고 싶으면 `package.json`에 직접 추가해야 한다. 나중에 express가 body-parser를 내부적으로 빼버려도 내 코드는 안 깨진다. npm에서는 express 업데이트 한 번에 유령 의존성이 사라져서 런타임 에러가 나는 사고가 종종 생긴다.

## hoist 설정과 도구 호환

유령 의존성 차단은 내 코드에는 좋지만, 평탄한 `node_modules`를 가정하고 만들어진 도구들과 충돌한다. ESLint 플러그인, Prettier, 일부 babel 프리셋, 오래된 webpack 설정 등이 "당연히 최상위에 있겠지" 하고 모듈을 찾다가 실패한다.

pnpm은 이런 경우를 위해 일부 패키지를 끌어올리는 설정을 둔다.

```ini
# .npmrc

# .pnpm/node_modules 아래로 끌어올림 (도구가 내부적으로 찾을 수 있게)
hoist-pattern[]=*eslint*
hoist-pattern[]=*prettier*

# 최상위 node_modules로 끌어올림 (내 코드에서도 직접 보임)
public-hoist-pattern[]=*types*
```

`hoist-pattern`은 `.pnpm/node_modules`까지만 올린다. 도구가 자기 의존성을 찾을 때만 보이고, 내 애플리케이션 코드의 모듈 해석에는 영향을 안 준다. `public-hoist-pattern`은 최상위까지 올려서 내 코드에서도 직접 import 가능하게 만든다. `@types/*`를 여기 넣는 팀이 많다.

정말 답이 없으면 npm처럼 전부 평탄하게 만드는 탈출구가 있다.

```ini
# .npmrc
shamefully-hoist=true
```

이름이 "shamefully(부끄럽게도)"인 건 의도된 거다. 이걸 켜면 유령 의존성 차단이라는 pnpm의 핵심 이점이 사라진다. 마이그레이션 초기에 너무 많은 게 깨질 때 임시로 켜고, 하나씩 정리한 뒤 다시 끄는 용도다. 켜둔 채로 방치하면 그냥 느린 npm을 쓰는 셈이다.

`node_modules` 레이아웃 자체를 바꾸는 설정도 있다.

```ini
# .npmrc
node-linker=isolated   # 기본값, 위에서 설명한 심볼릭 링크 구조
# node-linker=hoisted  # npm처럼 완전히 평탄하게
# node-linker=pnp      # Yarn PnP 방식, node_modules 없이 .pnp.cjs로 해석
```

`hoisted`는 store와 하드링크의 디스크 이점은 유지하면서 레이아웃만 npm처럼 만든다. React Native나 일부 모바일 빌드 도구처럼 심볼릭 링크를 못 따라가는 환경에서 이 설정을 쓴다.

## 워크스페이스

모노레포는 `pnpm-workspace.yaml`로 워크스페이스 범위를 정한다.

```yaml
packages:
  - "apps/*"
  - "packages/*"
  - "tools/*"
```

워크스페이스 안의 패키지끼리 의존할 때는 `workspace:` 프로토콜을 쓴다.

```json
{
  "name": "@myorg/web",
  "dependencies": {
    "@myorg/ui": "workspace:*",
    "react": "^18.2.0"
  }
}
```

`workspace:*`는 "레지스트리에서 받지 말고 워크스페이스 안의 `@myorg/ui`를 심볼릭 링크로 연결해라"는 뜻이다. `@myorg/ui`를 수정하면 `@myorg/web`이 즉시 그 변경을 본다. 빌드하고 publish하고 다시 설치하는 과정 없이 바로 반영된다.

`workspace:` 표기는 publish할 때 자동으로 실제 버전으로 치환된다.

```
workspace:*   → 현재 워크스페이스 패키지의 정확한 버전 (예: 1.4.2)
workspace:^   → ^1.4.2
workspace:~   → ~1.4.2
```

외부 사용자는 `workspace:`가 뭔지 모르니까, `pnpm publish`가 `package.json`을 변환해서 올린다. 직접 `npm publish`를 돌리면 변환이 안 되니 라이브러리를 publish하는 모노레포라면 `pnpm publish`를 써야 한다. 이 동작은 catalog의 publish 치환과 같은 맥락이다(`Pnpm_Lock_and_Catalog.md` 참고).

여러 패키지에 명령을 한 번에 돌릴 때는 `--filter`를 쓴다.

```bash
# 전체 워크스페이스에서 test 실행
pnpm -r test

# 특정 패키지만
pnpm --filter @myorg/web build

# 그 패키지가 의존하는 워크스페이스 패키지까지 순서대로 빌드
pnpm --filter @myorg/web... build

# 변경된 패키지와 그 영향을 받는 패키지만 (CI에서 유용)
pnpm --filter "...[origin/main]" test
```

마지막 `...[origin/main]`은 main 이후 변경된 패키지와 그것에 의존하는 패키지만 고른다. 모노레포가 커지면 전체 테스트는 시간이 너무 들어서, 변경 영향 범위만 돌리는 이 필터를 CI에서 자주 쓴다.

여러 워크스페이스 패키지가 같은 외부 라이브러리를 쓸 때 버전을 한 곳에서 맞추는 catalog 기능은 `Pnpm_Lock_and_Catalog.md`에서 다룬다.

## npm/yarn에서 옮길 때 실제로 깨지는 것들

`pnpm import`로 기존 lock 파일을 `pnpm-lock.yaml`로 변환하고 `pnpm install`을 돌리면 설치 자체는 대개 끝난다. 문제는 그다음에 터진다.

**유령 의존성**. 가장 흔하다. 코드 어딘가에서 `package.json`에 없는 패키지를 import하고 있었는데 npm에서는 우연히 됐던 거다. pnpm에서는 빌드나 테스트에서 `Cannot find module`로 줄줄이 터진다. 해결은 단순하다. 터지는 패키지를 `package.json`에 직접 추가한다. 짜증나지만 이게 정상화 과정이다.

**의존성의 빌드 스크립트가 안 돈다**. pnpm 10부터 의존성 패키지의 `postinstall` 같은 lifecycle 스크립트가 기본으로 차단된다. esbuild, sharp, Prisma, better-sqlite3, Puppeteer처럼 설치 시 네이티브 바이너리를 받거나 컴파일하는 패키지가 동작을 안 한다. 임의의 패키지가 설치만으로 코드를 실행하던 보안 문제 때문에 막은 거다. 명시적으로 허용해야 한다.

```bash
pnpm approve-builds
# 대화형으로 빌드를 허용할 패키지를 고른다
```

허용 목록은 설정에 박힌다.

```yaml
# pnpm-workspace.yaml (또는 package.json의 pnpm 필드)
onlyBuiltDependencies:
  - esbuild
  - sharp
  - "@prisma/engines"
```

마이그레이션 후 "왜 sharp가 안 깔리지", "Prisma client가 생성이 안 되네" 하면 십중팔구 이거다.

**빌드 도구가 모듈을 못 찾는다**. webpack, jest, storybook 등이 평탄한 `node_modules`를 가정하고 만들어진 경우 의존성을 못 찾는다. 위에서 다룬 `public-hoist-pattern`이나 `hoist-pattern`으로 해당 도구가 찾는 패키지를 끌어올린다. 그래도 안 되면 임시로 `shamefully-hoist=true`로 전체를 띄워놓고 하나씩 좁혀간다.

**심볼릭 링크를 못 따라가는 도구**. 일부 번들러나 모듈 해석기는 심볼릭 링크를 realpath로 풀어버려서 `.pnpm` 경로로 빠지고, 거기서 중복 인스턴스 문제를 일으킨다. React가 두 인스턴스로 로드돼서 hooks가 깨지는 식이다. `node --preserve-symlinks`나 번들러의 `resolve.symlinks: false` 같은 옵션으로 대응하거나, 안 되면 `node-linker=hoisted`로 레이아웃을 바꾼다.

**peer dependency 경고가 갑자기 쏟아진다**. npm은 peer 충돌을 대체로 조용히 넘어가지만 pnpm은 깐깐하게 경고한다. 경고 자체는 무시해도 되는 경우가 많은데, 진짜 버전이 안 맞아서 런타임에 깨지는 것도 섞여 있어서 한 번은 훑어야 한다. 자동으로 peer를 설치하게 하려면 `auto-install-peers=true`를 쓴다(최신 pnpm은 기본 켜짐).

## CI에서 store 캐싱

CI에서 캐싱할 대상은 `node_modules`가 아니라 **store**다. `node_modules`는 심볼릭 링크와 하드링크 덩어리라 캐시로 압축했다가 복원하면 링크가 깨지거나 복원이 더 느리다. store를 캐싱하고 `pnpm install`로 링크만 다시 거는 게 빠르다.

GitHub Actions 예시.

```yaml
- uses: pnpm/action-setup@v4
  with:
    version: 9

- uses: actions/setup-node@v4
  with:
    node-version: 20
    cache: 'pnpm'   # pnpm store를 lock 파일 해시 기준으로 캐싱

- run: pnpm install --frozen-lockfile
```

`actions/setup-node`의 `cache: 'pnpm'`은 `pnpm store path`를 알아서 찾아 `pnpm-lock.yaml` 해시를 캐시 키로 잡는다. lock 파일이 안 바뀌면 store를 그대로 복원하고, 바뀌면 새로 받는다.

캐시를 직접 다루려면 store 경로를 명시적으로 잡는 게 안전하다.

```yaml
- name: store 경로 구하기
  run: echo "STORE_PATH=$(pnpm store path --silent)" >> $GITHUB_ENV

- uses: actions/cache@v4
  with:
    path: ${{ env.STORE_PATH }}
    key: pnpm-store-${{ hashFiles('**/pnpm-lock.yaml') }}
    restore-keys: pnpm-store-
```

여기서 자주 하는 실수가 있다. `restore-keys`로 부분 일치 복원을 두면 lock이 바뀌어도 옛 store를 복원해서 그 위에 새 패키지가 얹힌다. 빌드는 잘 돌지만 store가 계속 커진다. 몇 주 지나면 캐시가 수 GB가 돼서 캐시 한도에 걸리거나 복원이 느려진다. 주기적으로 `pnpm store prune`을 캐시 저장 전에 한 번 돌려서 안 쓰는 파일을 털어내면 이 누적이 줄어든다.

`--frozen-lockfile`은 lock 파일에 적힌 대로만 설치하고 어긋나면 실패한다. CI(`CI=true`)에서는 기본으로 켜진다. 동작과 `ERR_PNPM_OUTDATED_LOCKFILE` 대응은 `Pnpm_Lock_and_Catalog.md`에 자세히 있다. 여기서는 CI 설치 명령에 명시적으로 붙여두는 걸 권한다는 정도만 적는다. 의도가 분명히 드러나고, `CI` 환경변수 세팅이 다른 러너로 옮겨도 동작이 안 바뀐다.

## Docker에서 pnpm fetch

Docker 이미지를 만들 때 `package.json`이 한 글자라도 바뀌면 `COPY . .` 이후 레이어 캐시가 전부 무효화돼서 의존성을 다시 받는다. pnpm에는 lock 파일만으로 store를 채우는 명령이 따로 있다.

```dockerfile
FROM node:20-slim AS deps
RUN corepack enable
WORKDIR /app

# lock 파일만 먼저 복사 → 이 레이어는 lock이 안 바뀌면 캐시됨
COPY pnpm-lock.yaml ./
RUN pnpm fetch --prod

# 소스와 package.json은 그다음에
COPY . .
RUN pnpm install --offline --frozen-lockfile
```

`pnpm fetch`는 `package.json`을 안 보고 `pnpm-lock.yaml`만 보고 store를 채운다. 소스 코드나 `package.json`이 바뀌어도 lock 파일이 그대로면 이 레이어 캐시가 유지돼서 패키지를 다시 안 받는다. 그다음 `pnpm install --offline`은 이미 채워진 store에서 링크만 건다. 네트워크를 안 타니 빠르고, 오프라인 빌드 환경에서도 동작한다.

모노레포에서는 루트 `pnpm-lock.yaml` 하나만 복사하면 워크스페이스 전체 의존성을 fetch한다. 패키지별 `package.json`을 일일이 복사하는 dockerfile을 짜던 시절보다 훨씬 단순해진다.

## 참조

- [pnpm 공식 문서](https://pnpm.io/)
- [pnpm의 store와 node_modules 구조](https://pnpm.io/symlinked-node-modules-structure)
- [pnpm-workspace.yaml 설정](https://pnpm.io/pnpm-workspace_yaml)
- [pnpm fetch](https://pnpm.io/cli/fetch)
- [pnpm 설정(.npmrc) 레퍼런스](https://pnpm.io/npmrc)
