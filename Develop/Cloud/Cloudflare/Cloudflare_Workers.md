---
title: Cloudflare Workers
tags: [cloud, backend, javascript, typescript, performance]
updated: 2026-09-23
---

# Cloudflare Workers

Cloudflare Workers는 Cloudflare의 엣지 네트워크 위에서 돌아가는 서버리스 실행 환경이다. 300개 이상의 데이터센터에 코드가 배포되고, 요청은 사용자와 가장 가까운 노드에서 처리된다. AWS Lambda와 가장 큰 차이는 콜드스타트가 없다는 점인데, 그 이유가 V8 Isolate 방식에 있다.

## V8 Isolate와 콜드스타트

Lambda는 요청마다 컨테이너를 띄우거나 재사용한다. 이미 떠 있는 컨테이너가 없으면 수백 ms의 콜드스타트가 생긴다. Workers는 다르다. V8 Isolate는 Node.js나 컨테이너가 아니라 브라우저 탭처럼 작동한다. 이미 떠 있는 V8 엔진 위에서 새 Isolate를 만드는 비용이 수 ms 수준이라 콜드스타트로 느껴지지 않는다.

대신 제약이 있다. Isolate는 OS 프로세스가 아니라서 Node.js 표준 라이브러리를 쓸 수 없다. `fs`, `net`, `child_process`는 없다. `fetch`, `crypto`, `TextEncoder` 같은 Web API만 쓸 수 있다. npm 패키지도 Node API 없이 동작하는 것만 번들링해서 올릴 수 있다.

CPU 시간 제한도 있다. 무료 플랜은 요청당 CPU 10ms, 유료(Workers Paid)는 30ms다. 네트워크 I/O 대기 시간은 여기 포함되지 않는다. `fetch()`로 외부 API를 부르는 동안 CPU 카운터는 멈춘다.

## Request/Response 가로채기

Workers의 기본 진입점은 `fetch` 이벤트 핸들러다.

```typescript
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // 특정 경로만 가로채기
    if (url.pathname.startsWith("/api/")) {
      return handleApi(request, env);
    }

    // 나머지는 원본 서버로 그대로 전달
    return fetch(request);
  },
};
```

요청을 수정해서 오리진에 전달하거나, 오리진 응답을 받아서 헤더를 추가하거나 내용을 바꿀 수 있다.

```typescript
async function addSecurityHeaders(request: Request): Promise<Response> {
  const response = await fetch(request);

  // Response는 불변이라 새로 만들어야 한다
  const newHeaders = new Headers(response.headers);
  newHeaders.set("X-Frame-Options", "DENY");
  newHeaders.set("X-Content-Type-Options", "nosniff");

  return new Response(response.body, {
    status: response.status,
    headers: newHeaders,
  });
}
```

`Response`는 불변 객체다. 헤더를 추가하려면 기존 헤더를 복사해서 새 `Response`를 만들어야 한다. 이 부분을 모르면 `response.headers.set()`이 에러 없이 실행되는데 실제로 아무 효과가 없어서 디버깅이 어렵다.

## 환경 변수 바인딩

Workers의 환경 변수는 `wrangler.toml`에 선언한다.

```toml
# wrangler.toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[vars]
APP_ENV = "production"
API_BASE_URL = "https://api.example.com"
```

민감한 값(API 키, 비밀키)은 `vars`에 평문으로 넣으면 안 된다. `wrangler secret put`으로 따로 등록한다.

```bash
wrangler secret put DATABASE_PASSWORD
# 입력 프롬프트가 뜬다. 값이 터미널 히스토리에 남지 않는다.
```

TypeScript에서 타입 안전하게 쓰려면 `Env` 인터페이스를 직접 정의해야 한다.

```typescript
export interface Env {
  APP_ENV: string;
  API_BASE_URL: string;
  DATABASE_PASSWORD: string; // secret
  MY_KV: KVNamespace;        // KV 바인딩
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const apiUrl = env.API_BASE_URL;
    // ...
  },
};
```

## KV 스토리지 연동

Workers KV는 엣지 네트워크에 분산된 키-값 저장소다. 읽기 성능이 좋고 전 세계 어디서든 낮은 지연시간으로 접근할 수 있다. 대신 쓰기 후 전파에 최대 60초가 걸린다. 강한 일관성이 필요한 곳에는 쓰면 안 된다.

`wrangler.toml`에 KV 바인딩을 추가한다.

```toml
[[kv_namespaces]]
binding = "MY_KV"
id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
preview_id = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
```

`id`는 프로덕션 네임스페이스, `preview_id`는 로컬 개발과 `wrangler dev`에서 쓰는 네임스페이스다. 둘 다 `wrangler kv:namespace create`로 만든다.

```bash
wrangler kv:namespace create MY_KV
wrangler kv:namespace create MY_KV --preview
```

코드에서는 이렇게 쓴다.

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const key = new URL(request.url).pathname;

    // 캐시에서 먼저 확인
    const cached = await env.MY_KV.get(key);
    if (cached !== null) {
      return new Response(cached, {
        headers: { "Content-Type": "application/json" },
      });
    }

    // 오리진에서 가져와서 KV에 저장
    const response = await fetch(`https://api.example.com${key}`);
    const data = await response.text();

    // TTL 설정: 3600초 후 자동 삭제
    await env.MY_KV.put(key, data, { expirationTtl: 3600 });

    return new Response(data, {
      headers: { "Content-Type": "application/json" },
    });
  },
};
```

KV에는 객체를 그대로 넣을 수 없다. 반드시 `JSON.stringify()`로 직렬화해서 저장하고, 꺼낼 때 `JSON.parse()`로 복원한다. `getWithMetadata()`를 쓰면 메타데이터를 함께 저장하고 읽을 수 있는데, 만료 시간을 별도로 추적할 때 유용하다.

## wrangler CLI 배포

로컬에서 개발할 때는 `wrangler dev`를 쓴다.

```bash
# 로컬 에뮬레이션 (기본 포트 8787)
wrangler dev

# 실제 Cloudflare 네트워크 위에서 실행 (원격 미리보기)
wrangler dev --remote
```

`wrangler dev`는 로컬에서 돌아가지만 실제 Workers 환경과 미묘한 차이가 있다. `--remote`는 Cloudflare 엣지에 임시 배포해서 실행하는 방식이라 더 정확하다. KV나 D1, R2 같은 바인딩을 쓸 때는 `--remote`를 권장한다.

배포는 `wrangler deploy`다.

```bash
# 프로덕션 배포
wrangler deploy

# 특정 환경 배포 (wrangler.toml에 [env.staging] 정의된 경우)
wrangler deploy --env staging
```

`wrangler.toml`에 환경별 설정을 넣을 수 있다.

```toml
name = "my-worker"
main = "src/index.ts"

[env.staging]
name = "my-worker-staging"
vars = { APP_ENV = "staging" }

[env.production]
name = "my-worker-production"
vars = { APP_ENV = "production" }
```

배포 후 로그를 실시간으로 보려면 `wrangler tail`을 쓴다.

```bash
wrangler tail my-worker
```

## 로컬 개발 시 주의사항

`wrangler dev`로 로컬 개발할 때 자주 걸리는 문제들이다.

**CORS 문제.** 로컬 Worker(`localhost:8787`)에서 다른 도메인 API를 호출하면 브라우저가 CORS 오류를 낸다. Worker 코드 자체는 서버 사이드라 CORS 제약이 없지만, 브라우저에서 Worker 응답을 받는 경우 Worker가 적절한 CORS 헤더를 내려줘야 한다.

**Miniflare와 실제 환경 차이.** `wrangler dev`는 내부적으로 Miniflare를 쓴다. Miniflare는 Workers 환경을 Node.js에서 에뮬레이션하는데, 완전히 동일하지 않다. `crypto.subtle`의 일부 알고리즘이나 `cache` API 동작이 다를 수 있다. 확인이 필요하면 `--remote`로 테스트한다.

**환경 변수 누락.** `wrangler dev` 로컬 실행에서 `wrangler secret put`으로 등록한 시크릿에 접근하려면 `.dev.vars` 파일을 만들어야 한다.

```bash
# .dev.vars (로컬 전용, 절대 커밋하지 말 것)
DATABASE_PASSWORD=local-dev-password
```

이 파일 없이 로컬에서 시크릿 값을 읽으면 `undefined`가 된다.

**CPU 시간 초과.** 로컬에서 잘 돌아가다가 프로덕션에서 CPU 초과 오류가 나는 경우가 있다. 로컬 Miniflare는 CPU 시간 제한이 느슨하다. 특히 JSON 파싱, 정규식, 암호화 연산이 많으면 실제 환경에서 10ms를 넘길 수 있다. `wrangler dev --remote`로 미리 확인해두는 게 낫다.

**KV 프리뷰 ID.** `wrangler dev`에서 KV를 쓰려면 `wrangler.toml`에 `preview_id`가 있어야 한다. `preview_id` 없이 로컬에서 KV 작업을 하면 인메모리 저장소를 쓰는데, 이 데이터는 `wrangler dev`를 재시작하면 사라진다.

## 실제로 쓸 때 자주 보게 되는 것들

Workers에서 `waitUntil()`을 모르면 응답을 보낸 후 처리가 필요한 작업을 놓치게 된다. Workers는 응답을 반환하는 순간 실행 컨텍스트가 종료된다. 로깅, 분석 데이터 전송처럼 응답 이후에 해도 되는 작업은 `ctx.waitUntil()`에 넘기면 응답과 비동기로 계속 실행된다.

```typescript
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const response = await handleRequest(request, env);

    // 응답 반환 후에도 계속 실행됨
    ctx.waitUntil(logToAnalytics(request, response));

    return response;
  },
};
```

`subrequest` 제한도 있다. Workers 하나에서 보낼 수 있는 서브요청(fetch 호출)은 무료 플랜 50개, 유료 1000개다. 여러 외부 API를 병렬로 호출하는 경우 `Promise.all()`을 써도 카운트는 각각 잡힌다.

메모리 상태를 전역 변수에 저장하면 안 된다고 알려져 있지만, 실제로는 같은 Isolate가 재사용되는 동안에는 전역 상태가 유지된다. 다만 언제 새 Isolate로 전환되는지 보장이 없다. 요청 간 공유 상태가 필요하면 KV나 Durable Objects를 써야 한다.
