---
title: npm ci와 bin
tags: [framework, node, 모듈-시스템, npm, ci, bin, nodejs]
updated: 2026-08-05
---

# npm ci와 bin

## npm ci vs npm install

`npm install`과 `npm ci`는 둘 다 패키지를 설치하지만 동작 방식이 다르다.

`npm install`은 `package.json`의 버전 범위를 기준으로 설치한다. `^4.18.2`라고 적혀 있으면 4.x.x 중 최신을 받아올 수 있다. `package-lock.json`이 있으면 참고하지만, 없어도 설치된다. 기존 `node_modules`가 있으면 그 위에 덮어쓰듯 처리한다.

`npm ci`는 동작이 다르다. 반드시 `package-lock.json`이 있어야 한다. 없으면 에러로 종료된다. 설치 전에 `node_modules` 디렉토리를 통째로 삭제하고 처음부터 다시 설치한다. `package-lock.json`에 기록된 정확한 버전만 설치한다.

```bash
# npm install: lock 파일 없어도 동작, 기존 node_modules 위에 설치
npm install

# npm ci: lock 파일 필수, node_modules 삭제 후 재설치
npm ci
```

`package.json`과 `package-lock.json`의 버전이 맞지 않으면 `npm ci`는 에러를 낸다. `package.json`에서 버전 범위를 바꿨는데 `npm install`을 빠뜨려서 lock 파일이 갱신되지 않은 상태가 그 예다.

```
npm ERR! `npm ci` can only install packages when your package.json and package-lock.json or npm-shrinkwrap.json are in sync.
```

이 경우 로컬에서 `npm install`을 먼저 실행해 lock 파일을 갱신한 다음 커밋해야 한다.

## CI 환경에서 npm ci를 써야 하는 이유

CI에서 `npm install` 대신 `npm ci`를 써야 하는 이유는 재현 가능성 때문이다.

`npm install`은 `package.json`의 버전 범위 안에서 최신 버전을 설치할 수 있다. 오늘 CI에서 설치한 버전과 일주일 후 설치한 버전이 다를 수 있다. 어떤 패키지 메인테이너가 버그 있는 패치 버전을 릴리즈하면 CI가 갑자기 깨진다. 로컬에서는 되는데 CI에서만 실패하는 상황이 여기서 온다.

`npm ci`는 `package-lock.json`의 내용 그대로 설치하기 때문에 어느 환경, 어느 시점에 실행해도 동일한 패키지 버전이 나온다. lock 파일을 git에 커밋해두고 CI에서 `npm ci`로 설치하면 로컬과 CI 환경이 동일하게 유지된다.

속도도 `npm ci`가 더 빠른 경우가 많다. 의존성 해석 과정을 건너뛰고 lock 파일에서 바로 설치하기 때문이다.

```yaml
# GitHub Actions 예시
steps:
  - uses: actions/checkout@v3
  - uses: actions/setup-node@v3
    with:
      node-version: '20'
      cache: 'npm'
  - run: npm ci
  - run: npm test
```

`node_modules` 캐싱과 함께 쓸 때 주의할 점이 있다. 캐시 키를 `package-lock.json`의 해시로 설정해야 한다. `package.json`으로 설정하면 lock 파일이 바뀌어도 캐시를 재사용해 잘못된 버전이 설치될 수 있다.

```yaml
- uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

## package.json의 bin 필드

`bin` 필드는 패키지가 제공하는 CLI 실행 파일을 등록한다.

```json
{
  "name": "my-cli-tool",
  "version": "1.0.0",
  "bin": {
    "my-tool": "./bin/cli.js",
    "mt": "./bin/cli.js"
  }
}
```

`bin` 값이 하나일 때는 문자열로 줄여 쓸 수 있다. 커맨드 이름은 패키지 이름과 동일하게 등록된다.

```json
{
  "name": "my-cli-tool",
  "bin": "./bin/cli.js"
}
```

CLI 파일 첫 줄에 shebang이 있어야 한다.

```js
#!/usr/bin/env node

// bin/cli.js
const args = process.argv.slice(2);
console.log('args:', args);
```

shebang이 없으면 운영체제가 어떤 인터프리터로 실행할지 몰라 에러가 난다. Windows에서는 shebang이 무시되고 npm이 별도 처리하지만, 있어도 문제가 없으므로 항상 넣는 게 맞다.

파일에 실행 권한도 있어야 한다.

```bash
chmod +x bin/cli.js
```

## node_modules/.bin/의 심링크

패키지를 설치하면 `node_modules/.bin/` 디렉토리에 심링크가 생성된다.

`typescript` 패키지를 설치하면 다음 심링크가 생긴다.

```
node_modules/.bin/tsc -> ../typescript/bin/tsc
node_modules/.bin/tsserver -> ../typescript/bin/tsserver
```

`typescript/package.json`의 `bin` 필드에 정의된 내용이 그대로 반영된 것이다.

```json
// node_modules/typescript/package.json
{
  "bin": {
    "tsc": "./bin/tsc",
    "tsserver": "./bin/tsserver"
  }
}
```

npm은 패키지를 설치할 때 이 `bin` 필드를 읽고, 지정된 파일을 가리키는 심링크를 `node_modules/.bin/`에 만든다. 전역 설치(`npm install -g`)라면 시스템 PATH에 있는 디렉토리(예: `/usr/local/bin`)에 심링크를 만든다.

`npm run` 스크립트 안에서는 `node_modules/.bin/`이 자동으로 PATH에 추가된다. 그래서 `package.json`의 `scripts`에서는 전체 경로 없이 커맨드 이름만 써도 된다.

```json
{
  "scripts": {
    "build": "tsc --build",
    "lint": "eslint src/"
  }
}
```

`.bin/` 디렉토리를 직접 실행하는 것도 된다.

```bash
./node_modules/.bin/tsc --version
```

## npx와 .bin/ 직접 실행의 차이

`npx`와 `node_modules/.bin/` 직접 실행은 비슷해 보이지만 동작이 다르다.

`node_modules/.bin/tsc`를 직접 실행하면 현재 프로젝트에 설치된 tsc만 실행된다. 없으면 에러다.

`npx tsc`는 순서대로 찾는다. 현재 `node_modules/.bin/`에서 먼저 찾고, 없으면 전역 설치 경로에서 찾는다. 거기도 없으면 npm 레지스트리에서 임시로 받아서 실행한다.

```bash
# 현재 프로젝트의 tsc 실행 (없으면 에러)
./node_modules/.bin/tsc --version

# 현재 프로젝트 > 전역 > 레지스트리 순서로 실행
npx tsc --version

# 레지스트리에서 특정 버전을 받아서 실행 (설치 안 함)
npx typescript@5.0.0 tsc --version
```

`npx`의 임시 설치 기능은 편리하지만 CI에서는 쓰지 않는 게 맞다. 매번 외부 네트워크 요청이 생기고, 받아오는 버전이 달라질 수 있다.

`npm exec`는 `npx`와 거의 같은 기능을 하는 npm 공식 커맨드다. npm 7 이상에서 `npx`는 내부적으로 `npm exec`를 호출한다.

## CI 파이프라인에서 bin 스크립트가 인식되지 않는 경우

### npm run 밖에서 직접 실행할 때

`npm run` 안에서는 `node_modules/.bin/`이 PATH에 자동으로 들어가지만, shell 스크립트에서 직접 실행하면 그렇지 않다.

```bash
# CI 스크립트에서 직접 실행하면 실패
tsc --build  # command not found

# 전체 경로를 지정하거나
./node_modules/.bin/tsc --build

# npx를 쓰거나
npx tsc --build

# npm run으로 감싸거나
npm run build
```

### node_modules를 캐싱할 때

CI에서 `node_modules` 자체를 캐싱하면 `.bin/` 디렉토리의 심링크가 깨질 수 있다. 심링크가 가리키는 파일이 없거나 권한이 달라진 경우다. `~/.npm` 캐시를 캐싱하고 `npm ci`로 재설치하는 방식이 안정적이다.

```yaml
# node_modules 캐싱 - 심링크 문제 발생 가능
- uses: actions/cache@v3
  with:
    path: node_modules  # 권장하지 않음
    key: ...

# npm 캐시 사용 후 npm ci로 재설치
- uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
- run: npm ci
```

### 파일 권한 문제

Linux CI 환경에서 Windows나 macOS에서 작성한 bin 파일을 실행하면 실행 권한이 없는 경우가 있다.

```bash
# 에러: permission denied
./node_modules/.bin/my-tool

# 그 자리에서 해결
chmod +x ./node_modules/.bin/my-tool
```

근본적인 해결은 git에 커밋할 때 파일 권한을 포함하는 것이다.

```bash
git add bin/cli.js
git update-index --chmod=+x bin/cli.js
git commit -m "add executable permission to bin/cli.js"
```

git이 실행 권한을 추적하면, CI에서 체크아웃할 때 권한이 유지된다.

### monorepo에서 bin 스크립트를 못 찾는 경우

모노레포 환경에서 workspace 패키지의 bin 스크립트를 루트에서 실행하려 할 때 못 찾는 경우가 있다.

```
packages/
  tool/
    package.json  <- bin 필드 있음
    bin/cli.js
node_modules/
  .bin/
    my-tool -> ???  <- 이 심링크가 없음
```

npm workspace를 쓰면 루트 `node_modules/.bin/`에 workspace 패키지의 bin도 링크된다. 하지만 `npm ci` 후 이 링크가 없다면 루트 `package.json`의 workspace 설정이 빠진 것이다.

```json
// 루트 package.json
{
  "workspaces": ["packages/*"]
}
```

workspace 설정이 있어야 `npm ci`가 각 패키지의 `bin` 필드를 읽고 루트 `.bin/`에 심링크를 만든다.
