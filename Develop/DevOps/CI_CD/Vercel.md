---
title: Vercel
tags: [devops, vercel, deployment, serverless, edge, ci-cd]
updated: 2026-04-13
---

# Vercel

## 개요

Vercel은 프론트엔드 프레임워크와 정적 사이트를 배포하는 클라우드 플랫폼이다. Next.js를 만든 회사에서 운영하고, Git 리포지토리에 push하면 자동으로 빌드·배포가 진행된다. Preview 환경이 PR마다 생성되는 게 큰 특징이다.

AWS에 직접 인프라를 구성하는 것과 비교하면 설정이 거의 없다. 대신 제어할 수 있는 범위가 좁고, 특정 상황에서 비용이 급격히 올라가는 구조다.

| 항목 | 설명 |
|------|------|
| **지원 프레임워크** | Next.js, Nuxt, SvelteKit, Remix, Astro, Vite, CRA 등 |
| **배포 방식** | Git push 자동 배포 / CLI 수동 배포 |
| **인프라** | AWS Lambda 기반 Serverless + Cloudflare 기반 Edge |
| **CDN** | Vercel Edge Network (글로벌) |
| **빌드 시스템** | Turbo Remote Cache 지원 |

## 프로젝트 설정과 배포 흐름

### Git 연동 배포

Vercel 대시보드에서 GitHub/GitLab/Bitbucket 리포지토리를 연결하면 된다. 연결 후에는 모든 push에 자동 배포가 동작한다.

```
main 브랜치 push → Production 배포
feature 브랜치 push → Preview 배포
PR 생성 → Preview URL이 PR 코멘트에 자동 등록
```

`vercel.json`으로 프로젝트 설정을 관리한다. 이 파일이 없어도 프레임워크를 자동 감지해서 배포하지만, 세부 설정이 필요하면 만들어야 한다.

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "framework": "vite"
}
```

프레임워크를 자동 감지하지 못하는 경우가 있다. `package.json`에 `build` 스크립트가 없거나, 모노레포 구조에서 루트가 아닌 하위 디렉토리에 프로젝트가 있을 때 주로 발생한다. 이때 `framework` 필드를 명시해야 한다.

### CLI 배포

```bash
# Vercel CLI 설치
npm i -g vercel

# 로그인
vercel login

# 현재 디렉토리 배포 (Preview)
vercel

# Production 배포
vercel --prod

# 특정 디렉토리 배포
vercel ./packages/web --prod
```

CLI 배포는 Git 연동과 별개로 동작한다. CI/CD 파이프라인에서 Vercel CLI로 배포하는 경우, Git 연동 자동 배포를 끄지 않으면 같은 커밋에 대해 두 번 배포가 실행된다. 프로젝트 Settings → Git에서 자동 배포를 비활성화해야 한다.

## Preview와 Production 환경 분리

Vercel의 핵심 기능이다. 브랜치별로 독립된 환경이 생성된다.

### 환경 구분

| 환경 | 트리거 | URL 형태 | 용도 |
|------|--------|---------|------|
| **Production** | main(또는 지정 브랜치) push | `project.vercel.app` | 실서비스 |
| **Preview** | main 외 브랜치 push, PR | `project-{hash}.vercel.app` | 리뷰, QA |

Preview 환경마다 고유한 URL이 부여된다. PR 리뷰할 때 코드만 보지 않고 실제 동작하는 화면을 확인할 수 있다. QA 팀에 Preview URL을 공유하면 별도 스테이징 서버 없이 테스트가 가능하다.

### 환경별 환경변수

같은 변수명이라도 환경별로 다른 값을 설정할 수 있다.

```
DATABASE_URL
  - Production: postgres://prod-db:5432/app
  - Preview: postgres://staging-db:5432/app
  - Development: postgres://localhost:5432/app
```

주의할 점: Preview 환경의 URL이 외부에 노출되면 스테이징 DB에 접근 가능한 상태가 된다. Vercel 대시보드에서 **Deployment Protection**을 설정해서 Vercel 인증을 거치도록 해야 한다. Hobby 플랜에서는 이 기능을 사용할 수 없다.

## Serverless Functions

### 기본 구조

`/api` 디렉토리에 파일을 생성하면 자동으로 Serverless Function이 된다. 파일 경로가 곧 API 경로다.

```
api/
├── hello.ts        → GET /api/hello
├── users/
│   ├── index.ts    → GET /api/users
│   └── [id].ts     → GET /api/users/:id
└── webhook.ts      → POST /api/webhook
```

```typescript
// api/users/[id].ts
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  const { id } = req.query;

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // DB 조회 등 로직
  return res.status(200).json({ userId: id });
}
```

Next.js의 API Routes를 쓰고 있다면 `/api` 디렉토리 방식과 혼용하지 않는 게 좋다. Next.js API Routes가 우선 처리되고, 충돌 시 디버깅이 어렵다.

### Cold Start 문제

Serverless Function은 요청이 없으면 인스턴스가 내려간다. 다시 요청이 들어오면 인스턴스를 새로 띄우는데, 이 과정에서 지연이 발생한다. 이걸 Cold Start라고 한다.

체감되는 수준:

- Node.js 런타임: 200~500ms 정도 추가 지연
- Python 런타임: 500ms~1s 이상
- DB 커넥션이 포함되면 1s 이상도 흔함

Cold Start를 줄이는 방법:

```typescript
// 1. 함수 번들 크기 줄이기
// 무거운 라이브러리를 통째로 import하지 말 것
import dayjs from 'dayjs'; // 번들에 전부 포함됨

// 필요한 것만 import
import utc from 'dayjs/plugin/utc';

// 2. DB 커넥션 재사용
// 함수 밖에서 커넥션을 생성하면 Warm 상태에서 재사용됨
let cachedConnection: any = null;

function getConnection() {
  if (cachedConnection) return cachedConnection;
  cachedConnection = createConnection(process.env.DATABASE_URL);
  return cachedConnection;
}

export default function handler(req: VercelRequest, res: VercelResponse) {
  const db = getConnection();
  // ...
}
```

Pro 플랜 이상에서는 **Fluid Compute** 옵션으로 함수를 Warm 상태로 유지할 수 있다. 트래픽이 일정한 서비스라면 고려할 만하다.

### 실행 제한

| 항목 | Hobby | Pro |
|------|-------|-----|
| 실행 시간 | 10초 | 60초 (설정 가능, 최대 300초) |
| 메모리 | 1024MB | 1024MB (최대 3008MB) |
| 페이로드 크기 | 4.5MB | 4.5MB |

실행 시간 제한은 자주 문제가 된다. 외부 API 호출이 느리거나, 이미지 처리처럼 시간이 걸리는 작업은 Hobby 플랜의 10초 제한에 걸린다. 이런 작업은 별도 서비스(AWS Lambda, Cloud Run 등)로 분리하는 게 맞다.

## Edge Functions

### Serverless vs Edge

| 비교 | Serverless Functions | Edge Functions |
|------|---------------------|---------------|
| 실행 위치 | 특정 리전 (기본: iad1) | CDN 엣지 (글로벌) |
| 런타임 | Node.js, Python, Go, Ruby | V8 (Web API 기반) |
| Cold Start | 있음 (200ms~1s+) | 거의 없음 (~0ms) |
| 실행 시간 | 최대 300초 | 최대 30초 |
| Node.js API | 전체 사용 가능 | 제한적 (fs, child_process 불가) |

Edge Functions는 V8 런타임에서 동작한다. 브라우저의 JavaScript 엔진과 같다. Node.js 전체 API를 쓸 수 없고, Web API(fetch, Request, Response 등)만 사용 가능하다.

```typescript
// middleware.ts (Next.js Edge Middleware)
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export const config = {
  matcher: ['/api/:path*', '/dashboard/:path*'],
};

export function middleware(request: NextRequest) {
  // 국가별 리다이렉트
  const country = request.geo?.country || 'US';

  if (country === 'KR' && !request.nextUrl.pathname.startsWith('/ko')) {
    return NextResponse.redirect(new URL('/ko' + request.nextUrl.pathname, request.url));
  }

  // 인증 체크
  const token = request.cookies.get('auth-token');
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}
```

Edge Functions에서 DB에 직접 연결하려면 TCP 소켓이 필요한데, Edge 런타임에서는 TCP를 지원하지 않는다. HTTP 기반 DB 드라이버(Neon의 `@neondatabase/serverless`, PlanetScale의 `@planetscale/database` 등)를 써야 한다. 기존 `pg`나 `mysql2` 같은 드라이버는 동작하지 않는다.

## 환경변수 관리

### 설정 방법

대시보드 Settings → Environment Variables에서 설정한다. CLI로도 가능하다.

```bash
# 환경변수 추가
vercel env add DATABASE_URL production
# 값을 입력하라는 프롬프트가 나옴

# .env 파일에서 일괄 추가
vercel env pull .env.local    # 현재 설정을 로컬로 가져오기

# 환경변수 목록 확인
vercel env ls
```

### 주의사항

클라이언트에 노출할 환경변수는 프레임워크별 prefix가 다르다.

```
Next.js:    NEXT_PUBLIC_API_URL
Vite:       VITE_API_URL
CRA:        REACT_APP_API_URL
Nuxt:       NUXT_PUBLIC_API_URL
```

prefix 없이 설정한 환경변수는 서버 사이드에서만 접근 가능하다. 클라이언트 코드에서 `process.env.API_KEY`를 참조해도 `undefined`가 된다. 빌드 로그에 에러가 나지 않아서 배포 후에야 발견하는 경우가 많다.

시크릿 값(DB 비밀번호, API 키 등)에는 절대 클라이언트 prefix를 붙이면 안 된다. 빌드 시점에 JavaScript 번들에 포함되어 브라우저 DevTools에서 그대로 보인다.

## 모노레포 설정

Turborepo, Nx, pnpm workspace 같은 모노레포 구조에서 Vercel을 사용하는 경우가 많다.

### Root Directory 설정

프로젝트 Settings → General → Root Directory에서 배포할 패키지 경로를 지정한다.

```
monorepo/
├── packages/
│   ├── web/          ← Vercel 프로젝트 A (Root: packages/web)
│   ├── admin/        ← Vercel 프로젝트 B (Root: packages/admin)
│   └── shared/       ← 공유 라이브러리
├── package.json
└── turbo.json
```

모노레포에서 하나의 패키지를 배포할 때, 다른 패키지의 변경에도 배포가 트리거되는 게 기본 동작이다. `vercel.json`의 `ignoreCommand`를 설정하면 관련 없는 변경에 배포가 실행되지 않는다.

```json
{
  "ignoreCommand": "git diff HEAD^ HEAD --quiet -- ."
}
```

이 명령이 exit code 0을 반환하면 (변경 없음) 빌드를 건너뛴다. Turborepo를 쓰고 있다면 `npx turbo-ignore`를 사용하면 의존성 그래프까지 고려해서 판단한다.

```json
{
  "ignoreCommand": "npx turbo-ignore"
}
```

## 커스텀 도메인, 리다이렉트, 헤더 설정

### 커스텀 도메인

프로젝트 Settings → Domains에서 추가한다. DNS 레코드를 설정해야 한다.

```
타입: CNAME
이름: www
값: cname.vercel-dns.com

타입: A
이름: @
값: 76.76.21.21
```

SSL 인증서는 자동 발급된다. Let's Encrypt 기반이고, 갱신도 자동이다. 별도 설정이 필요 없다.

### 리다이렉트와 헤더

`vercel.json`에서 설정한다.

```json
{
  "redirects": [
    {
      "source": "/blog/:slug",
      "destination": "/posts/:slug",
      "permanent": true
    },
    {
      "source": "/old-page",
      "destination": "/new-page",
      "statusCode": 301
    }
  ],
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Cache-Control", "value": "s-maxage=60, stale-while-revalidate=600" }
      ]
    },
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" }
      ]
    }
  ]
}
```

리다이렉트 규칙은 위에서 아래로 순서대로 매칭된다. 범위가 넓은 규칙을 위에 두면 구체적인 규칙이 무시되니, 구체적인 규칙을 먼저 작성해야 한다.

### Rewrites

URL은 유지하면서 내부적으로 다른 경로를 서빙한다. 프록시 용도로 많이 쓴다.

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://backend.example.com/api/:path*"
    }
  ]
}
```

CORS 문제를 피하기 위해 같은 도메인에서 백엔드 API를 프록시하는 패턴이다. 클라이언트에서 `/api/users`를 호출하면 내부적으로 `https://backend.example.com/api/users`로 요청이 간다.

## Vercel CLI 주요 명령어

```bash
# 프로젝트 관리
vercel                    # 현재 디렉토리 배포 (Preview)
vercel --prod             # Production 배포
vercel dev                # 로컬 개발 서버 (Serverless Functions 포함)
vercel link               # 로컬 디렉토리를 Vercel 프로젝트에 연결

# 환경변수
vercel env add KEY        # 환경변수 추가
vercel env rm KEY         # 환경변수 삭제
vercel env pull           # 원격 환경변수를 .env.local로 가져오기

# 배포 관리
vercel ls                 # 배포 목록 조회
vercel inspect <url>      # 특정 배포 상세 정보
vercel rollback <url>     # 특정 배포로 롤백
vercel logs <url>         # 배포 로그 확인

# 도메인
vercel domains ls         # 도메인 목록
vercel domains add <domain>  # 도메인 추가
```

`vercel dev`는 로컬에서 Serverless Functions과 Edge Functions를 실행할 수 있다. Next.js의 `next dev`와 다르게, Vercel의 라우팅 규칙(rewrites, redirects)도 적용된 상태로 동작한다. 환경변수도 Vercel 프로젝트에 설정된 값을 사용한다.

## Next.js 외 프레임워크 배포 시 주의사항

Vercel은 Next.js에 가장 최적화되어 있다. 다른 프레임워크를 배포할 때는 몇 가지 차이가 있다.

### 프레임워크별 설정

**Vite / React SPA**

```json
{
  "framework": "vite",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

SPA는 모든 경로를 `index.html`로 라우팅해야 한다. rewrite 설정이 없으면 `/about` 같은 경로에서 404가 발생한다.

**Nuxt**

Nuxt 3는 Nitro 서버 엔진을 사용하는데, Vercel에서 자동으로 Serverless Functions로 변환된다. SSR이 기본 동작이고, 별도 설정 없이 배포된다. 다만 `nuxt.config.ts`에서 `ssr: false`로 설정한 경우 정적 사이트로 배포되는데, 이때 서버 사이드 기능(API Routes 등)은 동작하지 않는다.

**SvelteKit**

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-vercel';

export default {
  kit: {
    adapter: adapter({
      runtime: 'nodejs18.x'  // 또는 'edge'
    })
  }
};
```

SvelteKit은 Vercel 전용 어댑터가 필요하다. `@sveltejs/adapter-auto`를 쓰면 Vercel 환경을 감지해서 자동으로 적용하지만, 런타임 옵션을 세밀하게 제어하려면 `@sveltejs/adapter-vercel`을 직접 사용하는 게 낫다.

### 공통 주의사항

- `outputDirectory`가 프레임워크마다 다르다 (Vite: `dist`, CRA: `build`, Next.js: `.next`). 잘못 설정하면 빈 페이지가 배포된다.
- Node.js 버전은 프로젝트 Settings에서 지정한다. `package.json`의 `engines` 필드는 무시된다.
- Vercel은 빌드 시 `npm ci`를 기본으로 실행한다. `yarn.lock`이 있으면 `yarn install`, `pnpm-lock.yaml`이 있으면 `pnpm install`을 자동 감지한다. lock 파일 없이 배포하면 매 빌드마다 의존성 버전이 달라질 수 있다.

## 빌드 캐시와 배포 롤백

### 빌드 캐시

Vercel은 `node_modules`와 프레임워크별 빌드 캐시를 자동으로 저장한다. Next.js의 `.next/cache` 디렉토리가 대표적이다.

캐시가 오염되면 빌드는 성공하지만 런타임에 이상한 동작이 발생하는 경우가 있다. 대시보드 Settings → General에서 **Override Build Cache**를 토글하면 다음 빌드에서 캐시 없이 클린 빌드를 실행한다.

CLI로도 캐시를 무시할 수 있다.

```bash
vercel --force
```

Turborepo의 Remote Cache를 Vercel과 연동하면 모노레포에서 변경되지 않은 패키지의 빌드를 건너뛸 수 있다. 빌드 시간이 크게 줄어든다.

### 배포 롤백

문제가 생기면 이전 배포로 즉시 롤백할 수 있다. 새로 빌드하는 게 아니라 이전 빌드 결과물을 다시 서빙하는 방식이라 수 초 내에 반영된다.

```bash
# 특정 배포 URL로 롤백
vercel rollback https://my-app-abc123.vercel.app

# 대시보드에서도 가능
# Deployments 탭 → 원하는 배포 → ... 메뉴 → Promote to Production
```

롤백해도 환경변수는 현재 설정이 유지된다. 코드는 이전 버전인데 환경변수는 현재 값을 쓰는 상태가 되니, 환경변수 변경과 코드 변경이 동시에 있었던 배포를 롤백할 때는 환경변수도 함께 되돌려야 한다.

## 비용 구조

### 플랜 비교

| 항목 | Hobby (무료) | Pro ($20/월/멤버) |
|------|------------|-----------------|
| 배포 횟수 | 하루 100회 | 무제한 |
| 빌드 시간 | 월 6,000분 | 월 24,000분 |
| Serverless 실행 | 월 100GB-시간 | 월 1,000GB-시간 |
| 대역폭 | 월 100GB | 월 1TB |
| Edge Middleware | 월 1,000,000 호출 | 월 1,000,000 호출 (이후 과금) |
| 동시 빌드 | 1 | 1 (추가 구매 가능) |
| 팀 멤버 | 1명 | 무제한 |
| Deployment Protection | 미지원 | 지원 |
| Speed Insights | 미지원 | 지원 |

### 비용이 올라가는 패턴

**Serverless Function 실행 시간**이 가장 큰 변수다. API 응답이 느린 외부 서비스를 호출하거나, 이미지 처리를 Serverless에서 하면 실행 시간이 금방 소진된다.

**대역폭**도 주의해야 한다. 이미지나 동영상 같은 대용량 에셋을 Vercel에서 직접 서빙하면 비용이 급증한다. 이런 에셋은 S3 + CloudFront 같은 별도 CDN을 쓰는 게 맞다.

**빌드 시간**은 모노레포에서 문제가 된다. 패키지 하나를 수정했는데 전체 모노레포가 빌드되면 빌드 시간이 불필요하게 소모된다. `ignoreCommand` 설정이나 Turborepo Remote Cache로 해결해야 한다.

Pro 플랜에서도 한도를 초과하면 추가 과금이 발생한다. 특히 대역폭 초과 비용($40/100GB)은 예상보다 비싸다. 프로덕션에 투입하기 전에 예상 트래픽으로 비용을 계산해봐야 한다. Vercel 대시보드의 Usage 탭에서 현재 사용량을 확인할 수 있다.
