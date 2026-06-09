---
title: NestJS Provider Scope 심화
tags:
  - nestjs
  - provider
  - scope
  - di
  - request-scope
  - async-local-storage
  - durable-provider
  - multi-tenancy
updated: 2026-06-09
---

# NestJS Provider Scope 심화

NestJS에서 Provider Scope를 처음 만지는 사람들은 대부분 똑같은 함정에 빠진다. 멀티테넌시 구현하려고 `Scope.REQUEST`를 박았다가 운영에서 응답 지연이 두세 배로 튀거나, 요청별 로거를 만들겠다고 컨트롤러에 REQUEST scope를 걸어놓고 왜 트랜잭션 ID가 안 찍히는지 한참 헤매는 경우다. 단순한 옵션 하나처럼 보이지만, 의존성 그래프 전체에 전파되는 특성 때문에 잘못 쓰면 인스턴스 폭증과 GC 압박을 동시에 만든다.

이 문서는 세 가지 Scope의 동작 원리, Scope bubbling이 어떻게 일어나는지, 그리고 Durable Provider와 AsyncLocalStorage 같은 대안을 언제 써야 하는지 다룬다.

## Scope의 종류와 기본 동작

NestJS Provider는 세 가지 Scope 중 하나를 가진다.

- `Scope.DEFAULT` (Singleton): 애플리케이션 부트스트랩 시 한 번 생성되고 그 인스턴스가 계속 재사용된다. 명시하지 않으면 이게 기본값이다.
- `Scope.REQUEST`: HTTP 요청(또는 RPC, GraphQL 요청)이 들어올 때마다 새 인스턴스가 만들어지고, 응답이 끝나면 GC 대상이 된다.
- `Scope.TRANSIENT`: 주입받는 컨슈머마다 별개의 인스턴스가 만들어진다. 같은 클래스 안에서 두 번 주입받으면 두 인스턴스가 생긴다.

```typescript
import { Injectable, Scope } from '@nestjs/common';

@Injectable() // Scope.DEFAULT
export class CatsService {}

@Injectable({ scope: Scope.REQUEST })
export class TenantService {}

@Injectable({ scope: Scope.TRANSIENT })
export class LoggerService {}
```

여기서 핵심은 Singleton과 REQUEST의 라이프사이클 차이가 단순한 "더 자주 만들어진다" 수준이 아니라는 점이다. Singleton 인스턴스는 NestJS 컨테이너가 직접 참조를 잡고 있어서 GC가 절대 회수하지 않는다. 반면 REQUEST 인스턴스는 요청이 들어올 때마다 새 객체 그래프를 만들고, 응답이 끝나면 컨테이너가 참조를 끊는다. 이 차이가 메모리 패턴과 성능에 큰 영향을 준다.

## DEFAULT(Singleton) — 가장 흔하고 가장 안전한 기본값

대부분의 Provider는 Singleton으로 충분하다. 서비스 클래스에 요청별 상태를 저장하지 않는 한 굳이 다른 Scope를 쓸 이유가 없다.

```typescript
@Injectable()
export class OrderService {
  constructor(
    private readonly orderRepository: OrderRepository,
    private readonly paymentClient: PaymentClient,
  ) {}

  async createOrder(userId: string, items: Item[]) {
    return this.orderRepository.create({ userId, items });
  }
}
```

이 OrderService는 인스턴스 필드에 상태를 갖지 않고 메서드 인자로 모든 컨텍스트를 받는다. 동시에 천 개의 요청이 와도 같은 인스턴스 하나가 처리한다.

Singleton의 함정은 인스턴스 필드에 무심코 상태를 박는 경우다.

```typescript
// 잘못된 예
@Injectable()
export class BadUserContext {
  private currentUserId: string; // 모든 요청이 공유한다

  setUser(id: string) {
    this.currentUserId = id;
  }

  getCurrentUser() {
    return this.currentUserId; // 다른 요청이 덮어쓴 값을 볼 수 있다
  }
}
```

이 코드는 동시 요청 환경에서 즉시 데이터 누출 사고로 이어진다. A 사용자의 요청이 처리되는 중에 B 사용자 요청이 `setUser`를 호출하면, A의 후속 로직이 B의 ID로 동작한다. 인증·인가 관련 코드에서 이런 패턴이 나오면 사실상 보안 사고다.

## REQUEST scope — 요청별 인스턴스의 비용

REQUEST scope를 걸면 NestJS는 요청이 들어올 때마다 해당 Provider와 그 의존성을 새로 인스턴스화한다. `@Inject(REQUEST)`로 현재 요청 객체에 접근할 수 있게 된다.

```typescript
import { Injectable, Scope, Inject } from '@nestjs/common';
import { REQUEST } from '@nestjs/core';
import { Request } from 'express';

@Injectable({ scope: Scope.REQUEST })
export class TenantContext {
  readonly tenantId: string;

  constructor(@Inject(REQUEST) request: Request) {
    this.tenantId = request.headers['x-tenant-id'] as string;
  }

  isAdminTenant() {
    return this.tenantId === 'admin';
  }
}
```

이 패턴은 직관적이고 타입 안전성이 좋다. 멀티테넌시 SaaS를 NestJS로 만들 때 가장 먼저 떠오르는 방식이기도 하다.

문제는 비용이다. REQUEST scope provider 하나를 만들면 다음 작업이 매 요청마다 일어난다.

1. Provider 클래스의 새 인스턴스 생성
2. 해당 인스턴스의 생성자 의존성을 모두 새 인스턴스로 생성 (의존성이 Singleton이 아닌 한)
3. 라이프사이클 훅(`onModuleInit`, `onModuleDestroy`)을 매 요청마다 실행
4. 응답 종료 후 인스턴스 그래프 전체를 GC 대상으로 전환

초당 수천 요청이 들어오는 API에서 REQUEST scope provider가 의존성 트리에 5~6개 매달려 있으면, 매 요청마다 그만큼의 객체가 만들어졌다가 사라진다. 짧은 시간에 많은 객체를 만들고 버리면 V8의 Young Generation이 빠르게 차고, Minor GC가 자주 일어나 응답 지연의 꼬리가 길어진다.

내가 본 운영 사례 중에 평균 응답 시간은 멀쩡한데 p99가 800ms를 넘어가는 경우가 있었다. 프로파일링해 보니 REQUEST scope로 잡힌 도메인 서비스 두 개가 GraphQL Resolver의 거의 모든 노드에 주입되고 있었다. 요청당 수십 번씩 인스턴스가 생성되면서 GC가 응답 처리를 잘게 쪼개고 있었던 것이다. 해당 Provider들을 Singleton으로 바꾸고 tenant 정보만 AsyncLocalStorage로 옮기자 p99가 즉시 200ms 아래로 떨어졌다.

## Scope bubbling — 가장 위험한 함정

NestJS Provider Scope의 가장 큰 함정은 Scope bubbling이다. REQUEST scope provider를 주입받는 모든 Provider가 자동으로 REQUEST scope가 된다. 명시적으로 Singleton으로 선언했어도 마찬가지다.

```typescript
@Injectable({ scope: Scope.REQUEST })
export class TenantContext {
  /* ... */
}

@Injectable() // Singleton 처럼 보인다
export class OrderService {
  constructor(private readonly tenantContext: TenantContext) {} // REQUEST scope bubbling 발생
}

@Injectable() // 역시 Singleton 처럼 보인다
export class OrderController {
  constructor(private readonly orderService: OrderService) {} // 여기까지 bubbling
}
```

위 코드에서 `OrderService`와 `OrderController`는 명시적으로 Scope를 지정하지 않았지만, 실제로는 둘 다 REQUEST scope로 동작한다. NestJS가 의존성 그래프를 분석해서 "REQUEST scope에 의존하는 Provider는 그 자체가 REQUEST scope여야 한다"고 판단하기 때문이다. 의존성이 매 요청마다 새로 만들어지는데 컨슈머가 Singleton이면 첫 요청의 의존성을 영원히 들고 있는 꼴이 되니, 이건 NestJS가 알아서 해결해 줄 수밖에 없다.

문제는 이 전파가 의존성 그래프 전체로 퍼진다는 점이다. 컨트롤러까지 REQUEST scope가 되면 라우터의 인스턴스 캐싱이 무력화된다. NestJS의 라우터는 평소엔 컨트롤러 인스턴스를 캐시해서 빠르게 호출하지만, REQUEST scope 컨트롤러는 요청마다 컨트롤러부터 만들어야 하니 라우팅 자체가 느려진다.

Scope bubbling을 디버깅할 때 가장 헷갈리는 게 의도하지 않은 광범위한 전파다. 도메인 코어에 작은 REQUEST scope provider 하나를 넣었더니 거의 모든 컨트롤러가 REQUEST scope가 돼버린 사례를 본 적 있다. 정작 그 provider가 필요한 곳은 두세 군데뿐이었는데도 의존성 그래프를 통해 모든 곳에 전파됐다.

이 문제 때문에 NestJS는 `Scope.REQUEST`를 가능한 한 그래프의 잎(leaf) 노드에만 두라고 가이드한다. 도메인 서비스나 리포지토리 같은 핵심 컴포넌트에는 절대 REQUEST scope를 걸지 말아야 한다.

## TRANSIENT scope — 인스턴스 격리가 필요할 때

TRANSIENT scope는 주입받는 컨슈머마다 별개의 인스턴스를 만든다. 같은 모듈 안에서 두 클래스가 `LoggerService`를 주입받으면 각자 독립적인 인스턴스를 받는다.

```typescript
@Injectable({ scope: Scope.TRANSIENT })
export class LoggerService {
  private context: string;

  setContext(context: string) {
    this.context = context;
  }

  log(message: string) {
    console.log(`[${this.context}] ${message}`);
  }
}

@Injectable()
export class UserService {
  constructor(private readonly logger: LoggerService) {
    this.logger.setContext('UserService'); // 이 인스턴스는 UserService 전용
  }
}

@Injectable()
export class OrderService {
  constructor(private readonly logger: LoggerService) {
    this.logger.setContext('OrderService'); // 별개의 인스턴스
  }
}
```

TRANSIENT는 의외로 잘 안 쓰이는데, 실제로 인스턴스 단위 상태가 필요한 경우가 드물기 때문이다. 위의 로거 예시 정도가 거의 유일한 실용 사례다. 그리고 TRANSIENT는 Scope bubbling을 일으키지 않기 때문에 REQUEST보다 안전하다. 단, 인스턴스가 늘어나는 만큼 메모리는 더 쓴다.

TRANSIENT scope를 쓸 때 주의할 점은 `forwardRef`나 동적 모듈 import 패턴과 섞이면 같은 클래스를 주입받는데 인스턴스가 의도와 다르게 공유되거나 분리될 수 있다는 것이다. 디버깅이 어렵기 때문에 정말 필요한 곳에만 써야 한다.

## ContextIdFactory와 Durable Provider

REQUEST scope의 비용 문제를 NestJS 차원에서 해결하기 위해 도입된 게 Durable Provider다. 핵심 아이디어는 "요청마다 새 인스턴스를 만들지 말고, 요청을 어떤 그룹(예: 테넌트)에 매핑한 다음 그룹별로 인스턴스를 캐싱하자"는 것이다.

기본 동작에서는 매 요청마다 `ContextId`가 새로 발급되고, REQUEST scope provider 인스턴스가 그 ContextId에 묶여 생성된다. Durable Provider를 쓰면 ContextId를 우리가 정의한 키(테넌트 ID 등)로 재사용할 수 있다.

```typescript
import { ContextIdFactory, ContextIdStrategy, HostComponentInfo } from '@nestjs/core';
import { Request } from 'express';

const tenants = new Map<string, ContextId>();

export class TenantContextIdStrategy implements ContextIdStrategy {
  attach(contextId: ContextId, request: Request) {
    const tenantId = request.headers['x-tenant-id'] as string;

    let tenantSubTreeId: ContextId;
    if (tenants.has(tenantId)) {
      tenantSubTreeId = tenants.get(tenantId)!;
    } else {
      tenantSubTreeId = ContextIdFactory.create();
      tenants.set(tenantId, tenantSubTreeId);
    }

    return (info: HostComponentInfo) => (info.isTreeDurable ? tenantSubTreeId : contextId);
  }
}

// main.ts
ContextIdFactory.apply(new TenantContextIdStrategy());
```

그리고 Provider에 `durable: true`를 추가한다.

```typescript
@Injectable({ scope: Scope.REQUEST, durable: true })
export class TenantContext {
  constructor(@Inject(REQUEST) request: Request) {
    this.tenantId = request.headers['x-tenant-id'] as string;
  }
}
```

이렇게 하면 같은 테넌트의 요청은 모두 같은 `TenantContext` 인스턴스를 공유한다. 인스턴스 생성 비용이 테넌트 수에 비례하지, 요청 수에 비례하지 않게 된다. 테넌트가 100개고 초당 1만 요청이 와도 인스턴스는 100개만 만들어진다.

다만 Durable Provider도 함정이 있다.

첫째, durable로 표시한 Provider 내부에서 요청별로 다른 상태를 저장하면 안 된다. 같은 테넌트의 모든 요청이 인스턴스를 공유하기 때문에 한 요청에서 저장한 값이 다른 요청에 그대로 노출된다. 인스턴스 필드는 "테넌트 단위로 변하지 않는 값"만 담아야 한다.

둘째, `@Inject(REQUEST)`로 받은 요청 객체는 인스턴스 생성 시점의 요청만 가리킨다. 그 인스턴스를 재사용하는 다음 요청들은 첫 요청의 REQUEST 객체를 계속 보게 된다. 이걸 모르고 `request.user`를 인스턴스 필드에 저장했다가 다른 사용자 정보가 노출되는 사고가 자주 난다.

셋째, 테넌트 ID를 키로 쓴다고 했지만 실제로는 그 키를 어디서 가져오느냐가 까다롭다. 헤더에서 가져오면 인증 미들웨어보다 먼저 실행되는 시점이라 신뢰할 수 없는 값일 가능성이 있다. JWT 검증 후의 정보를 키로 쓰려면 별도 처리가 필요하다.

## AsyncLocalStorage — 더 가벼운 대안

Scope를 건드리지 않고 요청별 컨텍스트만 전달하고 싶다면 Node.js의 `AsyncLocalStorage`가 더 가볍다. NestJS 10부터는 `nestjs-cls` 같은 라이브러리가 잘 통합돼 있어서 손쉽게 쓸 수 있다.

```typescript
import { ClsModule, ClsService } from 'nestjs-cls';

@Module({
  imports: [
    ClsModule.forRoot({
      middleware: {
        mount: true,
        setup: (cls, req) => {
          cls.set('tenantId', req.headers['x-tenant-id']);
          cls.set('requestId', req.headers['x-request-id'] ?? randomUUID());
        },
      },
    }),
  ],
})
export class AppModule {}

@Injectable() // Singleton 유지
export class OrderService {
  constructor(private readonly cls: ClsService) {}

  async createOrder(items: Item[]) {
    const tenantId = this.cls.get('tenantId');
    const requestId = this.cls.get('requestId');
    return this.orderRepository.create({ tenantId, requestId, items });
  }
}
```

이 방식의 장점은 명확하다. 모든 Provider가 Singleton 그대로 유지된다. Scope bubbling 걱정이 없고, 인스턴스 폭증도 없다. 컨텍스트는 비동기 흐름을 따라 자동으로 전파되기 때문에 `await`를 거쳐도 같은 값을 읽을 수 있다.

단점도 있다. AsyncLocalStorage는 컨텍스트 진입·이탈마다 약간의 오버헤드를 만든다. Node.js 16 이후로 많이 개선됐지만 완전히 공짜는 아니다. 그리고 ClsService를 통해 값을 꺼낼 때 타입 안전성이 떨어진다. `cls.get('tenantId')`는 기본적으로 `any`다. 이건 TypeScript에 ClsStore 타입을 직접 정의해서 어느 정도 보완할 수 있다.

```typescript
interface AppClsStore extends ClsStore {
  tenantId: string;
  requestId: string;
  userId?: string;
}

// 사용 시
const tenantId = this.cls.get<AppClsStore>('tenantId'); // string으로 추론됨
```

세 방식을 비교하면 다음과 같다.

| 항목 | REQUEST scope | Durable Provider | AsyncLocalStorage |
|------|---------------|------------------|-------------------|
| 인스턴스 생성 빈도 | 요청마다 | 테넌트(키)마다 | 없음 (Singleton) |
| Scope bubbling | 있음 (의존 그래프 전체) | 있음 (durable 트리 내) | 없음 |
| GC 압박 | 큼 | 적음 | 거의 없음 |
| 타입 안전성 | 좋음 | 좋음 | 별도 타입 정의 필요 |
| 멀티테넌시 적합성 | 트래픽 적을 때만 | 좋음 (테넌트 단위 캐싱) | 좋음 |
| 비동기 전파 | 자연스러움 | 자연스러움 | 자동 (ALS) |
| 라이프사이클 훅 호출 | 매 요청마다 | 키마다 1회 | 호출 안 됨 |

성능이 중요한 API에서는 AsyncLocalStorage를 우선 검토하는 게 맞다. REQUEST scope는 GraphQL Resolver처럼 컨텍스트 객체를 자연스럽게 받는 환경, 또는 트래픽이 충분히 적어서 GC 부담이 무시할 만한 환경에서만 쓰는 게 안전하다.

## 멀티테넌시 구현 시 함정

멀티테넌시 SaaS에서 Provider Scope를 어떻게 쓸지는 거의 항상 논쟁거리다. 흔히 마주치는 함정 몇 가지를 짚어둔다.

### 테넌트별 데이터베이스 연결을 REQUEST scope로 만들기

PostgreSQL 같은 RDB에서 테넌트별로 schema나 연결 풀을 분리하는 경우 "테넌트별 DataSource"가 필요하다. 이걸 REQUEST scope로 만들면 요청마다 새 연결을 만들거나 풀에서 가져오게 되는데, 풀 관리가 꼬이기 시작한다.

```typescript
// 안티 패턴
@Injectable({ scope: Scope.REQUEST })
export class TenantDataSource {
  constructor(@Inject(REQUEST) request: Request) {
    this.dataSource = createDataSource({
      schema: request.headers['x-tenant-id'] as string,
    });
  }
}
```

이렇게 짜면 요청마다 새 DataSource를 만들고, 응답이 끝나면 풀이 통째로 버려진다. 연결 비용이 누적되고, 어느 순간 DB의 `max_connections`을 넘어서 장애가 난다.

대신 테넌트별 DataSource를 Singleton 풀에서 미리 만들어 두거나, lazy하게 생성하되 같은 테넌트 키에 대해서는 같은 DataSource를 재사용하는 패턴이 안전하다. Durable Provider가 정확히 이 시나리오를 위해 설계됐다.

### 요청별 로거에서 트랜잭션 ID가 안 찍히는 경우

요청별 로거를 만들려고 LoggerService를 REQUEST scope로 만들고 미들웨어에서 트랜잭션 ID를 주입하는 코드를 자주 본다.

```typescript
@Injectable({ scope: Scope.REQUEST })
export class RequestLogger {
  private requestId: string;

  constructor(@Inject(REQUEST) request: Request) {
    this.requestId = request.headers['x-request-id'] as string;
  }

  log(message: string) {
    console.log(`[${this.requestId}] ${message}`);
  }
}
```

문제는 이 RequestLogger를 비동기 작업 큐 핸들러나 스케줄러에서 호출하면 REQUEST가 없어서 인스턴스 생성 자체가 실패한다는 점이다. 큐 워커가 처리하는 작업은 HTTP 요청 컨텍스트 밖에서 실행되기 때문이다.

이런 경우 로거는 Singleton으로 두고, 트랜잭션 ID는 AsyncLocalStorage로 흘려보내는 게 훨씬 깔끔하다. 큐 워커도 자체적으로 작업 시작 시점에 ALS 컨텍스트를 만들고 worker job ID를 거기에 넣어주면 같은 로거가 그대로 동작한다.

### `@Inject(REQUEST)` 객체의 라이프사이클

REQUEST 토큰으로 주입받는 객체는 Express 또는 Fastify의 원본 Request 객체다. 이 객체에 미들웨어나 가드가 추가한 프로퍼티(`request.user`, `request.tenant` 등)는 인스턴스 생성 시점에 이미 추가돼 있어야 한다.

NestJS Provider의 생성자는 라우트 핸들러 실행 직전에 호출되는데, 미들웨어보다는 늦지만 일부 가드/인터셉터보다는 빠를 수 있다. 정확한 순서는 라우트 구성에 따라 달라지므로, `@Inject(REQUEST)`로 받은 객체에서 `user`가 비어 있는 경우를 자주 만난다. 가드에서 인증된 사용자를 `request.user`에 채워 넣었다면, 그 사용자에 의존하는 로직은 생성자가 아니라 메서드에서 `request.user`를 읽는 식으로 짜야 한다.

## 정리

Provider Scope는 강력한 도구지만 잘못 쓰면 성능과 안정성 양쪽을 다 망친다. 기본 원칙은 단순하다.

- 기본은 Singleton. 인스턴스 필드에 요청별 상태를 절대 저장하지 말 것.
- 요청별 컨텍스트가 필요하면 AsyncLocalStorage(nestjs-cls)를 먼저 검토.
- 테넌트별로 캐싱할 수 있는 상태가 있다면 Durable Provider.
- REQUEST scope는 GraphQL 리졸버나 트래픽이 낮은 어드민 API처럼 명확한 이유가 있을 때만.
- TRANSIENT는 같은 클래스를 여러 컨슈머가 독립적으로 써야 할 때만.

Scope bubbling 때문에 REQUEST scope의 영향이 의존성 그래프 전체로 퍼진다는 점은 항상 기억하고 있어야 한다. 도메인 코어에 REQUEST scope를 박는 순간 거의 모든 컨트롤러가 REQUEST scope가 된다고 보면 된다.
