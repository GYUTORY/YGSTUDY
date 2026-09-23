---
title: Cloudflare Pages
tags: [cloud, frontend, ci-cd, backend, javascript]
updated: 2026-09-23
---

# Cloudflare Pages

Cloudflare Pages는 정적 사이트와 풀스택 앱을 배포하는 플랫폼이다. GitHub·GitLab 저장소를 연결하면 푸시할 때마다 빌드·배포가 자동으로 돌아간다. Vercel이나 Netlify와 역할이 겹치는데, Cloudflare 네트워크 위에서 돌아가서 WAF·R2·Workers와 같은 계정 안에서 연동된다는 게 차이점이다.

## Git 연동과 빌드 설정

대시보드에서 "Create application → Pages → Connect to Git"으로 저장소를 연결하면 빌드 설정 화면이 뜬다. 프레임워크를 선택하면 빌드 명령어와 출력 디렉토리가 자동 입력되는데, 이 값이 실제 프로젝트와 다를 때가 있어서 확인해야 한다.

자주 쓰는 설정 예시:

| 프레임워크 | 빌드 명령어 | 출력 디렉토리 |
|---|---|---|
| React (CRA) | `npm run build` | `build` |
| Vite | `npm run build` | `dist` |
| Next.js (static) | `next build && next export` | `out` |
| MkDocs | `mkdocs build` | `site` |
| Astro | `astro build` | `dist` |

빌드 명령어 앞에 설치 명령이 별도로 없다. Pages는 `npm install`을 빌드 전에 자동으로 실행한다. 패키지 매니저를 `pnpm`이나 `yarn`으로 바꾸려면 환경변수 `NPM_FLAGS`가 아니라 빌드 명령어 자체를 `pnpm install && pnpm run build`로 바꿔야 한다.

Node.js 버전은 기본값이 낮다. 2024년 기준 기본값이 18인데, 프로젝트가 20 이상을 요구하면 환경변수 `NODE_VERSION`을 설정해야 한다. 설정하지 않으면 빌드는 되는데 런타임 동작이 다를 수 있다.

```bash
NODE_VERSION=20
```

저장소 루트에 `package.json`이 없는 모노레포 구조면 "Root directory" 설정을 바꿔야 한다. 기본값은 저장소 루트라서 `apps/web` 같은 하위 디렉토리를 지정하지 않으면 빌드가 맞는 `package.json`을 못 찾는다.

## 환경변수 관리

Pages 대시보드의 Settings → Environment variables에서 환경변수를 관리한다. "Production"과 "Preview" 환경을 따로 설정할 수 있는데, 로컬 개발 환경과 분리되어 있다.

평문 환경변수와 암호화 환경변수(Encrypt)를 구분한다. API 키나 DB 비밀번호는 "Encrypt" 체크를 해야 한다. Encrypt 체크를 하면 대시보드에서 다시 볼 수 없고, 빌드 로그에도 마스킹된다.

빌드 시점에 접근 가능한 변수와 런타임에 접근 가능한 변수가 다르다. 정적 사이트 빌드에서 `process.env.API_URL`처럼 쓰는 변수는 빌드 중에만 주입된다. Pages Functions에서 쓰는 변수는 런타임 환경변수다. 둘 다 같은 화면에서 설정하지만 동작이 다르다.

```javascript
// 빌드 시점 주입 (Next.js, Vite 등 프레임워크에서 접근)
// 빌드 중에만 사용 가능, 최종 번들에 하드코딩됨
const apiUrl = process.env.VITE_API_URL;

// Pages Functions 런타임 (함수 코드에서 접근)
export async function onRequest(context) {
  const apiKey = context.env.API_KEY; // 런타임 시크릿
}
```

Vite 기반 프로젝트에서 자주 실수하는 부분이 있다. Vite는 `VITE_` 접두사가 붙은 변수만 클라이언트 번들에 포함한다. 접두사 없이 `API_KEY`를 설정해도 클라이언트 코드에서 `import.meta.env.API_KEY`는 `undefined`가 된다. 서버 코드(Functions)에서는 접두사와 무관하게 `context.env.API_KEY`로 접근한다.

## 커스텀 도메인 연결

Settings → Custom domains에서 도메인을 추가한다. 도메인이 Cloudflare에서 관리되는 경우와 외부 DNS인 경우 절차가 다르다.

**Cloudflare 관리 도메인**이면 "Add domain"만 입력하면 자동으로 CNAME 레코드가 생성된다. 보통 수분 내에 완료된다.

**외부 DNS**면 안내에 따라 CNAME 레코드를 수동으로 추가해야 한다.

```
CNAME  www   <project>.pages.dev
```

루트 도메인(`example.com`)에 CNAME을 설정하려면 DNS 제공자가 CNAME flattening을 지원해야 한다. 지원하지 않으면 A 레코드로는 Pages를 연결하기 어렵다. 이 경우 도메인 자체를 Cloudflare로 이전하거나, `www` 서브도메인으로만 운영한다.

커스텀 도메인을 연결하면 SSL 인증서가 자동 발급된다. Let's Encrypt 기반이고 자동 갱신된다. 발급에 보통 수분이 걸리는데, 간혹 수십 분 걸리는 경우도 있다.

## Pages Functions

Pages Functions는 정적 사이트와 함께 배포되는 서버리스 함수다. 저장소 루트의 `functions/` 디렉토리에 파일을 놓으면 자동으로 라우팅된다.

```
functions/
  api/
    hello.js          → /api/hello
    users/
      [id].js         → /api/users/:id
  _middleware.js      → 모든 요청에 적용
```

파일 이름의 `[id]`는 동적 라우트 파라미터다. 요청이 `/api/users/42`로 오면 `context.params.id`로 `"42"`를 꺼낸다.

```javascript
// functions/api/users/[id].js
export async function onRequestGet(context) {
  const userId = context.params.id;
  const db = context.env.DB; // D1 바인딩이나 환경변수

  // 실제 데이터 조회 예시 (D1 연동)
  const user = await db.prepare(
    "SELECT id, name, email FROM users WHERE id = ?"
  ).bind(userId).first();

  if (!user) {
    return new Response("Not found", { status: 404 });
  }

  return Response.json(user);
}

// POST 처리
export async function onRequestPost(context) {
  const body = await context.request.json();
  // ...
}
```

HTTP 메서드별로 함수를 분리할 수 있다. `onRequestGet`, `onRequestPost`, `onRequestPut`, `onRequestDelete`처럼 메서드 이름을 붙이거나, 하나의 `onRequest`에서 `context.request.method`로 분기한다.

**미들웨어**는 `_middleware.js`로 작성한다. 디렉토리 구조상 해당 경로와 하위 경로에 적용된다.

```javascript
// functions/_middleware.js — 전체 Functions에 적용
export async function onRequest(context) {
  // 인증 체크
  const token = context.request.headers.get("Authorization");
  if (!token || !isValidToken(token)) {
    return new Response("Unauthorized", { status: 401 });
  }

  // 통과
  return context.next();
}
```

`context.next()`를 빠뜨리면 요청이 미들웨어에서 막혀서 실제 함수가 실행되지 않는다. 응답을 반환하지 않으면 500 에러가 나는 게 아니라 빈 응답이 오는 경우가 있어서 디버깅이 어렵다.

### Workers와 Pages Functions의 차이

Workers와 비슷해 보이는데 몇 가지 차이가 있다. Pages Functions는 정적 파일 서빙과 하나의 배포로 묶인다. Workers는 독립 배포다. 같은 V8 Isolate 기반이고 `context.env`로 환경변수·바인딩에 접근하는 방식도 같다.

Pages Functions는 `wrangler.toml`이 아니라 대시보드에서 바인딩을 설정한다. KV, D1, R2 같은 리소스를 Functions에 연결하려면 Settings → Functions → KV namespace bindings에서 추가해야 한다.

## 배포 미리보기 URL

`main` 브랜치가 아닌 다른 브랜치에 푸시하면 자동으로 미리보기 배포가 생성된다. URL 형식은 다음과 같다.

```
https://<브랜치명>.<프로젝트명>.pages.dev
```

브랜치명에 `/`가 있으면 `-`로 치환된다. `feature/login` 브랜치면 `feature-login.<프로젝트명>.pages.dev`가 된다.

PR을 열면 GitHub 코멘트로 미리보기 URL이 자동으로 달린다. GitHub Actions와 별도로 설정하지 않아도 된다. Cloudflare가 GitHub App으로 저장소에 접근해서 PR 코멘트를 달아준다.

각 커밋마다 배포가 생성되는 건 아니다. 브랜치당 하나의 미리보기 URL이 유지되고, 해당 브랜치에 새 커밋이 오면 같은 URL을 덮어쓴다. 특정 커밋의 배포 URL을 고정하려면 대시보드의 Deployments 목록에서 개별 배포의 URL을 확인해야 한다.

미리보기 배포에도 인증을 걸고 싶을 때는 Settings → Access Policy에서 Cloudflare Access를 붙인다. 팀 내부에서만 확인해야 하는 스테이징 환경에 사용하면 된다.

## 실제로 자주 겪는 문제

**SPA 라우팅.** React Router나 Vue Router를 쓰는 SPA에서 `/about` 같은 경로를 직접 접근하면 404가 난다. Pages는 정적 파일을 서빙하는데 `/about/index.html`이 없기 때문이다. `public` 디렉토리에 `_redirects` 파일을 만들면 해결된다.

```
/* /index.html 200
```

Pages는 Netlify의 `_redirects` 포맷을 지원한다. 빌드 출력 디렉토리에 이 파일이 있으면 모든 경로를 `index.html`로 넘긴다.

**빌드 캐시.** Pages는 빌드 간 `node_modules`를 캐시한다. 패키지를 업데이트했는데 반영이 안 될 때가 있다. 대시보드에서 "Clear cache and retry deployment"로 캐시를 지우고 재빌드한다.

**Functions 크기 제한.** 개별 Function 파일 하나당 압축 전 1MB 제한이 있다. 번들이 크면 이 제한에 걸린다. `wrangler pages` CLI로 로컬에서 빌드해보면 크기를 확인한다.

**환경변수 변경 후 재배포.** 환경변수를 바꿔도 기존 배포에 즉시 적용되지 않는다. 새 배포를 트리거해야 한다. 대시보드에서 최신 배포를 선택하고 "Retry deployment"를 누르면 된다.