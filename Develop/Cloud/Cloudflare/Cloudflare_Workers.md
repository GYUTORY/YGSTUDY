---
title: Cloudflare Workers
tags: [cloud, backend, javascript, typescript, performance]
updated: 2026-09-25
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

## Cron 트리거

HTTP 요청 없이 주기적으로 실행하는 작업은 `scheduled` 핸들러로 처리한다. `wrangler.toml`에 크론 표현식을 등록하면 Cloudflare가 해당 Worker를 자동으로 호출한다.

```toml
# wrangler.toml
[triggers]
crons = ["0 * * * *", "0 0 * * *"]
```

```typescript
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    return new Response("OK");
  },

  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(syncData(env));
  },
};
```

`scheduled` 핸들러는 `Response`를 반환하지 않는다. 실행 결과를 외부에 알릴 방법이 없으니, 작업 상태를 KV나 D1에 기록해두는 경우가 많다.

`event.cron`으로 어떤 크론 표현식이 발동했는지 알 수 있다. cron을 여러 개 등록하면 이걸로 분기한다.

```typescript
async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
  switch (event.cron) {
    case "0 * * * *":
      ctx.waitUntil(hourlySync(env));
      break;
    case "0 0 * * *":
      ctx.waitUntil(dailyReport(env));
      break;
  }
}
```

로컬에서 테스트할 때 `wrangler dev --test-scheduled`로 시작하고, 별도 터미널에서 아래 요청을 보낸다.

```bash
curl "http://localhost:8787/__scheduled?cron=*+*+*+*+*"
```

`event.scheduledTime`은 예정 실행 시각을 ms 단위 유닉스 타임으로 준다. 실제 실행 시점과 수십 초 차이가 날 수 있어서, 정확한 실행 시각이 필요하면 이 값을 기준으로 써야 한다. CPU 시간 제한은 `fetch` 핸들러와 동일하게 적용된다.

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

## wrangler.toml 라우트 패턴

Workers.dev 서브도메인(`xxx.workers.dev`)은 별도 설정 없이 자동으로 연결된다. 직접 소유한 도메인에 Worker를 붙이려면 라우트를 등록해야 한다.

```toml
[[routes]]
pattern = "example.com/api/*"
zone_name = "example.com"
```

`zone_name` 대신 `zone_id`를 써도 된다. Zone ID는 Cloudflare 대시보드에서 해당 도메인을 선택하면 우측 사이드바에 표시된다.

패턴에서 `*`는 `/`를 제외한 모든 문자에 매칭된다. `example.com/api/*`는 `example.com/api/users`는 잡지만 `example.com/api/v1/users`는 잡지 못한다. 하위 경로 전체를 잡으려면 `example.com/api/**`를 쓴다.

Worker를 여러 개 운영하면서 라우트를 나눠 붙이는 경우, 더 구체적인 패턴이 우선이다. `example.com/api/*`와 `example.com/*`가 같이 있으면 `/api/`로 시작하는 요청은 전자가 먼저 받는다.

라우트 매칭은 Cloudflare 엣지에서 처리된다. 로컬 `wrangler dev`에서는 라우트 패턴이 동작하지 않는다. 라우트 동작을 확인하려면 `wrangler dev --remote`로 에지에 올려서 테스트해야 한다.

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

## D1 SQLite 연동

D1은 SQLite 기반 서버리스 데이터베이스다. KV처럼 키-값이 아니라 실제 SQL을 쓴다. 관계형 데이터가 필요한데 별도 데이터베이스 서버를 두기 부담스러운 경우에 쓴다.

```toml
[[d1_databases]]
binding = "DB"
database_name = "my-app-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

`database_id`는 `wrangler d1 create my-app-db`로 데이터베이스를 만들 때 출력된다.

```typescript
export interface Env {
  DB: D1Database;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/users" && request.method === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT id, name, email FROM users ORDER BY created_at DESC LIMIT 20"
      ).all<{ id: number; name: string; email: string }>();

      return Response.json(results);
    }

    if (url.pathname === "/users" && request.method === "POST") {
      const body = await request.json() as { name: string; email: string };

      const result = await env.DB.prepare(
        "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)"
      ).bind(body.name, body.email, new Date().toISOString()).run();

      return Response.json({ id: result.meta.last_row_id });
    }

    return new Response("Not Found", { status: 404 });
  },
};
```

`.bind()`로 파라미터를 바인딩해야 한다. 문자열 보간으로 SQL을 만들면 SQL 인젝션 위험이 생기고, D1 자체도 권장하지 않는다.

여러 쿼리를 하나의 트랜잭션으로 묶을 때는 `batch()`를 쓴다.

```typescript
await env.DB.batch([
  env.DB.prepare("INSERT INTO orders (user_id, total) VALUES (?, ?)").bind(userId, total),
  env.DB.prepare("UPDATE inventory SET quantity = quantity - ? WHERE product_id = ?").bind(qty, productId),
  env.DB.prepare("INSERT INTO audit_log (action, user_id) VALUES (?, ?)").bind("purchase", userId),
]);
```

`batch()`는 원자적이다. 하나라도 실패하면 전체가 롤백된다.

스키마 마이그레이션은 SQL 파일로 관리한다.

```bash
# 마이그레이션 파일을 적용한다
wrangler d1 migrations apply my-app-db

# 로컬 D1에만 적용 (프로덕션에 반영 안 됨)
wrangler d1 migrations apply my-app-db --local
```

로컬 `wrangler dev`에서는 프로덕션 D1과 별도의 로컬 인스턴스를 쓴다. `wrangler d1 execute`를 `--local` 없이 실행하면 프로덕션에 반영된다. 개발 중에는 `--local`을 붙이는 습관이 필요하다.

D1이 SQLite 기반이라 단순해 보이지만, 분산 환경에서 돌아간다. 읽기는 리전 복제본에서 처리되고 쓰기는 프라이머리로 간다. 쓰기 직후 읽기가 이전 값을 반환하는 경우가 있다. 쓰기 직후 결과를 다시 읽어야 하는 경우 쿼리 흐름을 다시 설계해야 한다.

## Durable Objects

KV는 eventually consistent다. 쓰기 후 읽기가 이전 값을 반환할 수 있다. 채팅방 참여자 목록, 게임 세션 상태, 분산 락처럼 강한 일관성이 필요한 경우 Durable Objects(DO)를 쓴다.

DO는 클래스 하나가 하나의 인스턴스 타입이다. 각 인스턴스는 단일 위치에서 실행되고, 해당 인스턴스로 들어오는 요청은 직렬화해서 처리한다. 여러 Worker가 동시에 같은 DO에 요청을 보내도 DO 내부에서는 동시 실행이 없다.

`wrangler.toml`에 바인딩과 마이그레이션을 등록한다.

```toml
[[durable_objects.bindings]]
name = "ROOM"
class_name = "ChatRoom"

[[migrations]]
tag = "v1"
new_classes = ["ChatRoom"]
```

`migrations` 태그가 없으면 배포가 실패한다. 처음 등록하는 경우에도 필수다. 클래스를 추가할 때마다 `new_classes`에 넣고 태그를 올린다.

```typescript
export class ChatRoom implements DurableObject {
  private state: DurableObjectState;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/join") {
      const participants = (await this.state.storage.get<string[]>("participants")) ?? [];
      const user = await request.json() as { userId: string };

      if (!participants.includes(user.userId)) {
        participants.push(user.userId);
        await this.state.storage.put("participants", participants);
      }

      return new Response(JSON.stringify({ count: participants.length }));
    }

    return new Response("Not Found", { status: 404 });
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const roomId = new URL(request.url).searchParams.get("room") ?? "default";

    // 같은 roomId는 항상 같은 DO 인스턴스를 가리킨다
    const id = env.ROOM.idFromName(roomId);
    const room = env.ROOM.get(id);

    return room.fetch(request);
  },
};
```

`idFromName()`은 결정적이다. 같은 문자열은 항상 같은 DO 인스턴스를 가리킨다. 사용자별로 인스턴스를 만들 때 `idFromName(userId)`, 세션별로는 `idFromName(sessionId)` 식으로 쓴다.

`state.storage`는 트랜잭셔널이다. `put()` 이후 오류가 나도 원자적으로 처리된다.

DO 인스턴스는 한 위치에서만 돌아서 그 위치와 멀리 있는 요청은 왕복 지연이 생긴다. 글로벌 서비스에서 특정 인스턴스에 전 세계 트래픽을 모으면 지연시간이 크게 올라간다. DO는 무료 플랜에서 쓸 수 없고 Workers Paid 이상 필요하다.

## Service Bindings

하나의 Worker에서 다른 Worker를 직접 호출하는 방식이다. `fetch()`로 공개 URL을 부르는 것과 달리, Cloudflare 내부 네트워크를 통해 전달된다. 외부 인터넷을 거치지 않아 지연시간이 거의 없고, 별도 인증도 필요 없다.

```toml
# 호출하는 Worker의 wrangler.toml
[[services]]
binding = "AUTH_SERVICE"
service = "auth-worker"
```

`auth-worker`는 같은 계정 내에 이미 배포된 Worker 이름이어야 한다.

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const authResult = await env.AUTH_SERVICE.fetch(
      new Request("https://internal/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: request.headers.get("Authorization") }),
      })
    );

    if (authResult.status === 401) {
      return new Response("Unauthorized", { status: 401 });
    }

    return handleRequest(request, env);
  },
};
```

URL 호스트 부분은 어떤 값이든 상관없다. Cloudflare가 바인딩에 등록된 Worker로 전달하기 때문에 실제 네트워크 요청이 발생하지 않는다. 관행적으로 `https://internal/` 같은 더미 호스트를 쓴다.

인증 처리, 이미지 변환, 결제 같은 공통 기능을 별도 Worker로 분리하고 Service Binding으로 연결하면 각 Worker를 독립적으로 배포하고 버전 관리할 수 있다.

주의할 점은 서브요청 카운트다. A Worker가 B를 호출하고 B가 C를 호출하면, A 기준으로 서브요청이 2개로 잡힌다. 깊은 체인을 만들면 무료 플랜의 50개 제한에 빨리 걸린다.

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
