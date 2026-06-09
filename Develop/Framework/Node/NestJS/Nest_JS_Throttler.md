---
title: NestJS Throttler 심화
tags:
  - NestJS
  - Throttler
  - RateLimit
  - Redis
  - Security
updated: 2026-06-09
---

# NestJS Throttler 심화

Rate limiting은 단순히 "초당 몇 번"을 막는 기능이 아니다. 누가 요청했는지 식별하고, 어디에 카운터를 두고, 여러 인스턴스에서 어떻게 합칠지, 프록시 뒤에서 클라이언트 IP를 어떻게 신뢰할지가 모두 얽혀 있다. `@nestjs/throttler` v5/v6는 이 부분을 모듈로 풀어 놓았는데, 기본 설정만 갖다 쓰면 분산 환경에서 카운터가 인스턴스별로 따로 쌓이거나, 로드밸런서 뒤에서 모든 요청이 같은 IP로 카운트되는 사고가 나기 쉽다.

이 문서는 단일 노드 메모리 throttle에서 시작해서 Redis 기반 분산 throttle, 다중 정책, WebSocket/GraphQL/Microservice 적용, 프록시 신뢰 경계까지 다룬다.

## 기본 모듈 구성

`@nestjs/throttler`는 `ThrottlerModule`로 전역 설정을 잡고, `ThrottlerGuard`를 글로벌 가드로 등록해서 모든 라우트에 자동 적용하는 구조다. v5부터 단일 정책이 아니라 정책 배열을 받는 형태로 바뀌었다.

```ts
import { Module } from '@nestjs/common'
import { APP_GUARD } from '@nestjs/core'
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler'

@Module({
  imports: [
    ThrottlerModule.forRoot([
      {
        name: 'default',
        ttl: 60_000,
        limit: 100,
      },
    ]),
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: ThrottlerGuard,
    },
  ],
})
export class AppModule {}
```

`ttl`은 밀리초 단위 윈도우, `limit`은 윈도우 안에서 허용할 요청 수다. v4까지는 `ttl`이 초 단위였는데 v5에서 밀리초로 바뀌었으니 마이그레이션할 때 60을 그대로 두면 1분이 아니라 60ms가 된다. 이 부분에서 한 번씩 사고가 난다.

라우트마다 다르게 적용하고 싶으면 `@Throttle()`이나 `@SkipThrottle()`을 쓴다.

```ts
import { Controller, Get, Post } from '@nestjs/common'
import { Throttle, SkipThrottle } from '@nestjs/throttler'

@Controller('users')
export class UsersController {
  @Get()
  list() {
    return []
  }

  @Throttle({ default: { limit: 5, ttl: 60_000 } })
  @Post('login')
  login() {
    return { ok: true }
  }

  @SkipThrottle()
  @Get('health')
  health() {
    return { status: 'ok' }
  }
}
```

`@Throttle()`에 넘기는 객체의 키는 `forRoot`에서 지정한 정책 `name`이다. `name`을 지정하지 않으면 내부적으로 `'default'`가 자동으로 붙는다. 정책 여러 개를 동시에 쓸 때 이 키 매칭이 중요해진다.

## Throttle key 커스터마이징

기본 동작은 클라이언트 IP를 키로 카운트한다. 실제 서비스에서는 이걸 그대로 두면 곤란한 경우가 많다.

- 같은 사무실에서 NAT 뒤에 있는 직원들이 모두 한 IP로 묶여서 한 명이 폭주하면 전부 차단된다
- JWT로 인증된 사용자는 IP가 아니라 user ID로 세야 한다
- API key 기반 트래픽은 key 단위로 세야 정확하다

`ThrottlerGuard`를 상속해서 `getTracker`를 오버라이드한다.

```ts
import { Injectable, ExecutionContext } from '@nestjs/common'
import { ThrottlerGuard } from '@nestjs/throttler'

@Injectable()
export class UserAwareThrottlerGuard extends ThrottlerGuard {
  protected async getTracker(req: Record<string, any>): Promise<string> {
    const userId = req.user?.id
    if (userId) {
      return `user:${userId}`
    }

    const apiKey = req.headers['x-api-key']
    if (apiKey) {
      return `apikey:${apiKey}`
    }

    return `ip:${req.ip}`
  }
}
```

여기서 주의할 점이 있다. `getTracker`가 호출되는 시점에 인증 가드보다 throttle 가드가 먼저 돌면 `req.user`가 비어 있다. NestJS의 글로벌 가드는 등록 순서대로 실행되는데, `APP_GUARD`로 여러 개를 등록해도 실행 순서는 모듈 그래프 해석 순서에 영향을 받는다. 인증 가드 → throttle 가드 순서가 필요하면 컨트롤러 레벨에서 `@UseGuards(AuthGuard, UserAwareThrottlerGuard)`로 명시하는 게 안전하다.

또 하나, 비인증 엔드포인트(로그인, 회원가입)는 user ID가 없으니 결국 IP로 떨어진다. 이런 곳은 brute force 방어가 가장 중요한 지점이라 IP만으로는 부족하고, email이나 username을 키에 섞어야 한다.

```ts
@Injectable()
export class LoginThrottlerGuard extends ThrottlerGuard {
  protected async getTracker(req: Record<string, any>): Promise<string> {
    const email = req.body?.email
    if (email) {
      return `login:email:${email}:${req.ip}`
    }
    return `login:ip:${req.ip}`
  }
}
```

email과 IP를 조합하면, 한 IP에서 여러 계정을 돌려가며 시도하는 credential stuffing과 한 계정에 여러 IP에서 들이대는 패턴을 모두 잡을 수 있다. 단, email 기반 키는 공격자가 임의의 email로 카운터를 늘려서 정상 사용자의 로그인을 막는 형태로 악용될 수 있으니, 너무 짧은 윈도우에 너무 낮은 limit을 잡으면 안 된다.

## Storage 추상화와 Redis 분산 throttle

`@nestjs/throttler`는 카운터 저장을 `ThrottlerStorage` 인터페이스로 분리해 놓았다. 기본 구현은 메모리(`ThrottlerStorageService`)인데, 인스턴스가 두 대만 돼도 카운터가 따로 쌓인다. 100/min 정책으로 인스턴스가 4대면 실질 한도가 400/min이 된다.

분산 throttle은 Redis를 쓰는 게 사실상 표준이다. 커뮤니티 패키지 `@nest-lab/throttler-storage-redis`나 `nestjs-throttler-storage-redis`를 사용한다.

```ts
import { Module } from '@nestjs/common'
import { ThrottlerModule } from '@nestjs/throttler'
import { ThrottlerStorageRedisService } from '@nest-lab/throttler-storage-redis'
import Redis from 'ioredis'

@Module({
  imports: [
    ThrottlerModule.forRootAsync({
      useFactory: () => ({
        throttlers: [{ name: 'default', ttl: 60_000, limit: 100 }],
        storage: new ThrottlerStorageRedisService(
          new Redis({
            host: process.env.REDIS_HOST,
            port: Number(process.env.REDIS_PORT),
            password: process.env.REDIS_PASSWORD,
            enableAutoPipelining: true,
            maxRetriesPerRequest: 3,
          }),
        ),
      }),
    }),
  ],
})
export class AppModule {}
```

Redis storage 구현체는 보통 `INCR` + `EXPIRE` 조합이나 Lua 스크립트로 카운터를 원자적으로 증가시킨다. 윈도우 방식은 fixed window(고정 윈도우)가 기본인데, 윈도우 경계 직전·직후에 두 번씩 요청을 보내면 순간적으로 2배까지 통과하는 burst 문제가 있다. 정확한 sliding window가 필요하면 자체 구현하거나, [ratelimit-redis](https://github.com/animir/node-rate-limiter-flexible) 같은 라이브러리를 storage로 감싸야 한다.

운영하면서 겪었던 함정 몇 가지를 정리한다.

**Redis 장애 시 동작.** Redis가 죽으면 throttle 카운터 조회·증가가 실패한다. 기본 구현은 보통 예외를 던져서 요청을 5xx로 떨어뜨리는데, 이게 더 큰 문제다. Redis가 잠깐 흔들리면 모든 API가 죽는 fail-closed 동작이 된다. fail-open(에러 시 통과)으로 바꾸려면 storage를 래핑한다.

```ts
@Injectable()
export class FailOpenRedisStorage implements ThrottlerStorage {
  constructor(private readonly delegate: ThrottlerStorageRedisService) {}

  async increment(
    key: string,
    ttl: number,
    limit: number,
    blockDuration: number,
    throttlerName: string,
  ): Promise<ThrottlerStorageRecord> {
    try {
      return await this.delegate.increment(key, ttl, limit, blockDuration, throttlerName)
    } catch (err) {
      this.logger.warn(`Throttler storage failed, allowing request: ${err.message}`)
      return {
        totalHits: 0,
        timeToExpire: ttl,
        isBlocked: false,
        timeToBlockExpire: 0,
      }
    }
  }
}
```

fail-open이 항상 옳은 건 아니다. 결제·인증 같은 critical 엔드포인트는 fail-closed가 맞고, 일반 조회 API는 fail-open이 맞다. 정책별로 다르게 가는 게 현실적이다.

**키 prefix 충돌.** 여러 서비스가 같은 Redis 클러스터를 쓰면 키가 섞인다. 반드시 `keyPrefix`를 분리한다. `nestjs-throttler-storage-redis`는 생성자 옵션으로, `@nest-lab/...`는 `keyPrefix` 옵션을 받는다. 안 그러면 다른 서비스의 카운터가 우리 서비스 throttle에 영향을 준다.

**TTL과 메모리 압박.** throttle 키는 `user:12345:throttler:default` 같은 형태로 사용자 수만큼 늘어난다. TTL이 짧으면 자동 만료되지만, blockDuration을 길게 (예: 24시간 차단) 잡으면 키가 누적된다. Redis 메모리 정책에서 `volatile-lru` 정도는 깔아 둬야 폭주 시 OOM이 안 난다.

## 라우트별 다중 정책 (short/medium/long)

API 전체에 단일 정책을 거는 건 거의 항상 부족하다. 짧은 burst, 중간 빈도, 장기 누적을 동시에 막으려면 정책을 여러 개 깔아야 한다.

```ts
ThrottlerModule.forRoot([
  { name: 'short', ttl: 1_000, limit: 3 },
  { name: 'medium', ttl: 10_000, limit: 20 },
  { name: 'long', ttl: 60_000, limit: 100 },
])
```

이렇게 등록하면 모든 라우트에 세 정책이 동시에 적용된다. 1초에 3번, 10초에 20번, 60초에 100번 중 하나라도 걸리면 429가 떨어진다. 짧은 burst(스크립트로 즉시 1000번 때리는 패턴)는 short가, 일정 페이스로 들이대는 패턴은 long이 잡는다.

라우트별로 정책을 다르게 깔고 싶으면 `@Throttle()`에 정책별 override를 넣는다.

```ts
@Controller('search')
export class SearchController {
  @Throttle({
    short: { limit: 10, ttl: 1_000 },
    long: { limit: 1000, ttl: 60_000 },
  })
  @Get()
  search() {
    return []
  }
}
```

검색처럼 burst가 자연스러운 엔드포인트는 short를 크게 잡고, 결제처럼 burst가 의심스러운 엔드포인트는 short를 작게 잡는다. 인증·결제 엔드포인트는 더 엄격하게.

```ts
@Throttle({
  short: { limit: 1, ttl: 1_000 },
  medium: { limit: 5, ttl: 60_000 },
  long: { limit: 20, ttl: 3_600_000 },
})
@Post('login')
login() {}
```

여기서 알아둘 점은, `@Throttle`에 모든 정책 키를 명시할 필요 없이 override하고 싶은 정책만 적으면 된다는 점이다. 적지 않은 정책은 `forRoot`의 기본값이 그대로 적용된다.

## ignoreUserAgents와 화이트리스트

내부 모니터링 시스템(Prometheus scraper, healthcheck)이 throttle에 걸리면 false alert이 뜬다. `skipIf` 옵션이나 `ignoreUserAgents`로 제외한다.

```ts
ThrottlerModule.forRoot({
  throttlers: [{ name: 'default', ttl: 60_000, limit: 100 }],
  ignoreUserAgents: [/Prometheus/, /HealthCheck/, /kube-probe/],
  skipIf: (context) => {
    const req = context.switchToHttp().getRequest()
    return req.ip === '10.0.0.1'
  },
})
```

User-Agent 기반 제외는 위조가 쉬워서 보안 측면에선 약하지만, 내부 도구를 단순히 분리하는 용도로는 충분하다. IP 화이트리스트는 내부 네트워크 CIDR(예: 사무실 NAT, k8s 노드 IP 범위)에만 적용해야 한다.

## 프록시 뒤에서의 X-Forwarded-For 처리

이 부분이 운영에서 가장 자주 사고가 나는 지점이다. ALB·CloudFront·Nginx 같은 프록시 뒤에 NestJS가 있으면, `req.ip`는 프록시의 IP가 된다. 결과적으로 모든 클라이언트가 같은 IP로 묶이고, throttle은 사실상 무력화된다(전체 트래픽이 한 카운터로 들어가서 늘 한도 초과).

Express 기반 NestJS에서는 trust proxy 설정이 필수다.

```ts
import { NestFactory } from '@nestjs/core'
import { NestExpressApplication } from '@nestjs/platform-express'

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule)
  app.set('trust proxy', 1)
  await app.listen(3000)
}
```

`trust proxy`는 hop 수를 의미한다. ALB 한 단만 있으면 1, CloudFront → ALB → app이면 2다. `true`로 잡으면 모든 hop을 신뢰하는데, 이건 위험하다. 클라이언트가 임의로 `X-Forwarded-For: 1.2.3.4, 5.6.7.8`을 보내면 `req.ip`가 `1.2.3.4`로 잡혀서 throttle 우회가 가능하다. 정확한 hop 수를 알면 숫자로, 모르면 신뢰할 수 있는 프록시의 CIDR로 지정한다.

```ts
app.set('trust proxy', ['10.0.0.0/8', '172.16.0.0/12'])
```

Fastify 기반은 다르다.

```ts
import { NestFactory } from '@nestjs/core'
import { NestFastifyApplication, FastifyAdapter } from '@nestjs/platform-fastify'

const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({ trustProxy: true }),
)
```

Fastify의 `trustProxy`도 boolean·number·string·function·CIDR을 받는다. boolean true는 위험하니 마찬가지로 CIDR을 명시한다.

CloudFront 뒤에 ALB가 있는 환경에서는 `X-Forwarded-For`가 누적된다. CloudFront가 진짜 클라이언트 IP를 맨 앞에 붙이고, ALB가 CloudFront 엣지 IP를 뒤에 붙인다. `req.ip`(또는 `req.ips`)가 맨 왼쪽 값을 잡아야 하는데, 이게 프레임워크·hop 수·헤더 파싱 방식에 따라 다르게 동작한다. 의심스러우면 직접 헤더를 파싱하는 게 안전하다.

```ts
@Injectable()
export class TrustedIpThrottlerGuard extends ThrottlerGuard {
  protected async getTracker(req: Record<string, any>): Promise<string> {
    const forwarded = req.headers['x-forwarded-for']
    if (typeof forwarded === 'string') {
      const ip = forwarded.split(',')[0].trim()
      if (this.isValidIp(ip)) {
        return `ip:${ip}`
      }
    }
    return `ip:${req.socket.remoteAddress}`
  }

  private isValidIp(ip: string): boolean {
    return /^(\d{1,3}\.){3}\d{1,3}$/.test(ip) || /^[0-9a-f:]+$/i.test(ip)
  }
}
```

이 방식의 함정은, X-Forwarded-For 헤더 자체를 신뢰하려면 그 헤더가 우리 프록시에서 온 것임이 보장돼야 한다는 점이다. 클라이언트가 직접 NestJS에 닿을 수 있는 경로(예: 인증된 내부 망 우회)가 있으면 헤더 위조가 가능하다. 진입점이 ALB로만 한정되도록 보안 그룹·NACL에서 막아야 한다.

CloudFront를 쓰면 `CloudFront-Viewer-Address`나 `CloudFront-Viewer-Country` 같은 더 신뢰할 수 있는 헤더가 있다. CloudFront가 추가하는 헤더는 클라이언트가 보낸 동일 이름 헤더를 덮어쓰니, 가능하면 이쪽을 쓰는 게 안전하다.

## WebSocket throttle

`ThrottlerGuard`는 HTTP 컨텍스트를 가정하고 만들어졌다. WebSocket 메시지에 그대로 붙이면 `req`가 없어서 깨진다. WebSocket용 전용 가드를 만들어야 한다.

`@nestjs/throttler` v5부터 `ThrottlerGuard`의 일부 메서드를 오버라이드해서 트랜스포트별로 처리할 수 있게 분리됐다. 직접 만드는 게 더 명확하다.

```ts
import { Injectable, ExecutionContext } from '@nestjs/common'
import { ThrottlerGuard, ThrottlerException } from '@nestjs/throttler'

@Injectable()
export class WsThrottlerGuard extends ThrottlerGuard {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const client = context.switchToWs().getClient()
    const ip =
      client.handshake.headers['x-forwarded-for']?.split(',')[0].trim() ??
      client.handshake.address

    const tracker = `ws:${ip}`
    const key = this.generateKey(context, tracker, 'default')

    const { totalHits } = await this.storageService.increment(
      key,
      this.throttlers[0].ttl,
      this.throttlers[0].limit,
      0,
      'default',
    )

    if (totalHits > this.throttlers[0].limit) {
      throw new ThrottlerException()
    }

    return true
  }
}
```

```ts
@WebSocketGateway()
export class ChatGateway {
  @UseGuards(WsThrottlerGuard)
  @SubscribeMessage('message')
  handleMessage(@MessageBody() data: string) {
    return { echo: data }
  }
}
```

WebSocket에서 주의할 점은, throttle 위반 시 어떻게 응답할지다. HTTP는 429를 던지면 끝이지만 WebSocket은 연결을 끊을지(`client.disconnect()`), 에러 이벤트만 emit하고 연결을 유지할지를 결정해야 한다. 채팅 같은 서비스에서 위반마다 연결을 끊으면 정상 사용자도 잦은 재연결로 고생한다. 보통은 위반 카운트를 누적해서 일정 횟수 초과 시 끊는다.

또 WebSocket throttle 키는 IP만으로는 부족하다. 연결 시점에 JWT로 인증하고 user ID를 `client.data`에 저장한 뒤, 그걸 키로 쓴다.

```ts
@WebSocketGateway()
export class ChatGateway implements OnGatewayConnection {
  async handleConnection(client: Socket) {
    const token = client.handshake.auth?.token
    const user = await this.authService.verify(token)
    if (!user) {
      client.disconnect()
      return
    }
    client.data.userId = user.id
  }
}
```

```ts
@Injectable()
export class WsUserThrottlerGuard extends WsThrottlerGuard {
  protected async getTracker(client: any): Promise<string> {
    return client.data?.userId ? `ws:user:${client.data.userId}` : `ws:ip:${client.handshake.address}`
  }
}
```

## GraphQL throttle

GraphQL은 단일 엔드포인트(`/graphql`)로 모든 쿼리·뮤테이션이 들어오기 때문에 HTTP throttle만 걸면 쿼리 종류와 무관하게 한 카운터로 묶인다. 비싼 쿼리(예: 전체 사용자 리스트)에 throttle을 더 엄격하게 걸려면 resolver 레벨에서 가드를 붙여야 한다.

```ts
import { Injectable, ExecutionContext } from '@nestjs/common'
import { GqlExecutionContext } from '@nestjs/graphql'
import { ThrottlerGuard } from '@nestjs/throttler'

@Injectable()
export class GqlThrottlerGuard extends ThrottlerGuard {
  getRequestResponse(context: ExecutionContext) {
    const gqlCtx = GqlExecutionContext.create(context)
    const ctx = gqlCtx.getContext()
    return { req: ctx.req, res: ctx.res }
  }
}
```

```ts
@Resolver()
export class UsersResolver {
  @Throttle({ default: { limit: 5, ttl: 60_000 } })
  @UseGuards(GqlThrottlerGuard)
  @Query(() => [User])
  expensiveUserSearch(@Args('query') query: string) {
    return this.usersService.search(query)
  }
}
```

GraphQL throttle의 진짜 문제는 쿼리 복잡도다. 한 요청으로 수십 개의 nested resolver를 호출하는 쿼리는 요청 수로는 1번이지만 실제 부하는 수십 배다. throttle만으로는 부족하고 쿼리 복잡도 제한(`graphql-query-complexity`)이나 depth limit을 같이 걸어야 한다. throttle은 요청 빈도만 제한할 뿐 비용을 제한하지 않는다.

또 하나, persisted query를 쓰는 환경에서는 query hash를 throttle key에 섞어서 특정 비싼 쿼리만 더 엄격하게 잡는 방법도 있다.

## Microservice throttle (TCP, Redis, Kafka)

Microservice 트랜스포트는 HTTP가 아니라 메시지 패턴 기반이다. `ThrottlerGuard`를 그대로 붙이면 안 된다. 직접 컨텍스트를 풀어서 카운트한다.

```ts
import { Injectable, ExecutionContext } from '@nestjs/common'
import { ThrottlerGuard, ThrottlerException } from '@nestjs/throttler'

@Injectable()
export class RpcThrottlerGuard extends ThrottlerGuard {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const rpcCtx = context.switchToRpc()
    const data = rpcCtx.getData()

    const tracker = data?.clientId ?? data?.userId ?? 'unknown'
    const handler = context.getHandler().name
    const key = `rpc:${handler}:${tracker}`

    const { totalHits } = await this.storageService.increment(
      key,
      this.throttlers[0].ttl,
      this.throttlers[0].limit,
      0,
      'default',
    )

    if (totalHits > this.throttlers[0].limit) {
      throw new ThrottlerException()
    }
    return true
  }
}
```

```ts
@Controller()
export class OrdersController {
  @UseGuards(RpcThrottlerGuard)
  @MessagePattern('order.create')
  create(@Payload() data: CreateOrderDto) {
    return this.ordersService.create(data)
  }
}
```

Microservice throttle은 보통 client 식별을 어떻게 할지가 관건이다. Kafka는 producer ID, NATS는 subject prefix, TCP는 connection metadata를 봐야 한다. 클라이언트 측에서 식별자를 메시지에 박아서 보내는 컨벤션이 필요하다. 식별자 없이는 throttle이 의미가 없거나, 트랜스포트 레이어에서 들어온 연결 단위로 묶어야 하는데 보통 그 정보가 컨텍스트에 잘 안 노출된다.

Microservice를 외부에 직접 노출하지 않고 API gateway 뒤에 둔 구조라면, throttle은 gateway에서만 걸고 내부 RPC는 throttle을 빼는 게 단순하다. 내부 RPC throttle을 거는 건 보통 우발적 폭주(버그로 무한 루프 호출) 방지 목적이지 보안 목적이 아니다.

## ThrottlerException 응답 커스터마이징

기본 응답은 `429 Too Many Requests`에 JSON body로 메시지가 들어간다. 운영에선 `Retry-After` 헤더를 응답에 추가하는 게 클라이언트한테 친절하다.

`ThrottlerGuard`의 `throwThrottlingException`을 오버라이드한다.

```ts
@Injectable()
export class FriendlyThrottlerGuard extends ThrottlerGuard {
  protected async throwThrottlingException(
    context: ExecutionContext,
    throttlerLimitDetail: ThrottlerLimitDetail,
  ): Promise<void> {
    const res = context.switchToHttp().getResponse()
    const retryAfterSec = Math.ceil(throttlerLimitDetail.timeToExpire / 1000)
    res.setHeader('Retry-After', retryAfterSec.toString())
    res.setHeader('X-RateLimit-Limit', throttlerLimitDetail.limit.toString())
    res.setHeader('X-RateLimit-Remaining', '0')
    res.setHeader('X-RateLimit-Reset', new Date(Date.now() + throttlerLimitDetail.timeToExpire).toISOString())
    throw new ThrottlerException('요청이 너무 많습니다. 잠시 후 다시 시도하세요.')
  }
}
```

평상시에도 `X-RateLimit-Remaining`을 응답에 넣어 두면 클라이언트가 자체적으로 페이스 조절을 할 수 있다. 이건 `throwThrottlingException`이 아니라 가드의 `canActivate` 마지막에 헤더를 박는 방식으로 구현한다.

```ts
@Injectable()
export class HeaderEnrichedThrottlerGuard extends ThrottlerGuard {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const result = await super.canActivate(context)
    const res = context.switchToHttp().getResponse()
    res.setHeader('X-RateLimit-Limit', this.throttlers[0].limit.toString())
    return result
  }
}
```

`X-RateLimit-Remaining`을 정확히 박으려면 storage에서 현재 카운트를 가져와야 하는데, `increment`가 totalHits를 리턴하니까 그 값을 가드 내부에서 들고 있다가 응답에 박는 형태로 만든다.

## 실전에서 자주 빠지는 함정

**테스트 환경에서 throttle 켜져 있어서 E2E 테스트가 fail.** E2E에서 같은 IP로 빠르게 여러 요청을 보내면 throttle에 걸린다. 테스트 환경에서는 `forRootAsync`로 환경별 limit을 크게 잡거나 `ThrottlerModule`을 mock으로 교체한다.

**Health check가 throttle에 잡혀서 k8s readiness probe 실패.** 위에서 다룬 `ignoreUserAgents`나 `skipIf` 또는 `@SkipThrottle()`로 health 엔드포인트는 항상 제외한다.

**Storage가 init 전에 가드가 돌아서 NullPointer.** `forRootAsync`로 비동기 초기화하는 경우, lifecycle 순서에 따라 storage가 준비되기 전에 첫 요청이 들어올 수 있다. `OnModuleInit`에서 connection을 보장하거나, ioredis의 `lazyConnect: false`로 즉시 연결한다.

**여러 인스턴스 시간차로 카운트 어긋남.** Redis storage를 쓰더라도 각 인스턴스가 윈도우 시작 시점을 자기 로컬 시간으로 계산하면 약간씩 어긋난다. 보통은 무시할 수준이지만, NTP가 깨진 인스턴스가 있으면 카운터가 이상하게 보인다. EC2면 chrony, 컨테이너면 호스트 시간 동기화 상태를 점검한다.

**`limit: 0`은 throttle 해제가 아니라 항상 차단.** "이 라우트는 무제한"으로 만들고 싶어서 0을 넣으면 모든 요청이 막힌다. 해제하려면 `@SkipThrottle()`을 쓴다.

**`ttl`을 너무 길게(예: 1시간) 잡으면 카운터 reset이 늦다.** 한번 폭주한 사용자가 1시간 내내 차단된다. 의도한 거면 괜찮지만, 정상 사용자가 우발적으로 limit을 넘긴 경우엔 너무 가혹하다. blockDuration을 분리해서 짧게 잡거나, short/medium/long 정책으로 분산시킨다.

## 모니터링과 관측

throttle 동작은 반드시 로깅한다. 어떤 키가 차단됐는지, 얼마나 자주 차단되는지를 보지 않으면 정책이 너무 빡빡한지 너무 헐거운지 판단이 안 된다.

```ts
@Injectable()
export class ObservableThrottlerGuard extends ThrottlerGuard {
  constructor(
    options: ThrottlerModuleOptions,
    storageService: ThrottlerStorage,
    reflector: Reflector,
    private readonly metrics: MetricsService,
  ) {
    super(options, storageService, reflector)
  }

  protected async throwThrottlingException(
    context: ExecutionContext,
    throttlerLimitDetail: ThrottlerLimitDetail,
  ): Promise<void> {
    const req = context.switchToHttp().getRequest()
    this.metrics.increment('throttler.blocked', {
      route: req.route?.path ?? 'unknown',
      throttler: throttlerLimitDetail.throttlerName,
    })
    await super.throwThrottlingException(context, throttlerLimitDetail)
  }
}
```

Prometheus나 DataDog 같은 곳으로 카운터를 보내면, 차단 비율이 갑자기 튈 때 공격을 받고 있다는 신호로 쓸 수 있다. 정상 트래픽에서 throttle 차단이 1% 이상 발생하면 정책이 너무 빡빡하다는 신호로 본다.
