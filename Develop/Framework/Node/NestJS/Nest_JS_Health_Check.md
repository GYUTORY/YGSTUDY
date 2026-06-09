---
title: NestJS Health Check 심화
tags:
  - NestJS
  - HealthCheck
  - Terminus
  - Kubernetes
  - GracefulShutdown
updated: 2026-06-09
---

# NestJS Health Check 심화

Health check는 단순히 `/health` 엔드포인트가 200을 반환하면 끝나는 일이 아니다. 어떤 의존성을 검사할지, 검사 실패가 어떤 의미를 갖는지, 누가 그 결과를 보고 어떤 결정을 내리는지가 다 다르다. Kubernetes는 liveness probe가 실패하면 컨테이너를 재시작하고, readiness probe가 실패하면 트래픽만 끊는다. 두 probe에 똑같은 엔드포인트를 물려두면 DB 일시 장애로 모든 Pod가 동시에 재시작되는 사고가 난다.

이 문서는 `@nestjs/terminus`의 동작 원리부터 indicator 구현, probe 분리, 그리고 graceful shutdown과의 연동까지 다룬다.

## @nestjs/terminus 구성

Terminus는 NestJS의 health check 표준 모듈이다. 내부적으로 `@godaddy/terminus`를 NestJS DI 컨테이너에 맞게 감싼 형태고, indicator라는 단위로 검사 로직을 모듈화한다.

```bash
npm install @nestjs/terminus
```

기본 모듈 등록은 간단하다.

```ts
import { Module } from '@nestjs/common'
import { TerminusModule } from '@nestjs/terminus'
import { HealthController } from './health.controller'

@Module({
  imports: [TerminusModule],
  controllers: [HealthController],
})
export class HealthModule {}
```

`TerminusModule`이 제공하는 것은 `HealthCheckService`와 각종 indicator다. Controller에서는 indicator를 주입받아 `HealthCheckService.check()`에 넘긴다.

```ts
import { Controller, Get } from '@nestjs/common'
import {
  HealthCheckService,
  HealthCheck,
  TypeOrmHealthIndicator,
  MemoryHealthIndicator,
} from '@nestjs/terminus'

@Controller('health')
export class HealthController {
  constructor(
    private readonly health: HealthCheckService,
    private readonly db: TypeOrmHealthIndicator,
    private readonly memory: MemoryHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  check() {
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 1500 }),
      () => this.memory.checkHeap('memory_heap', 300 * 1024 * 1024),
    ])
  }
}
```

`HealthCheck()` 데코레이터는 Swagger 문서화 메타데이터를 붙이고, 응답 스키마를 표준화한다. `check()`에 넘긴 함수들은 모두 병렬로 실행된다. 하나라도 실패하면 응답이 503, 모두 통과하면 200이다.

응답 구조는 이렇게 나온다.

```json
{
  "status": "ok",
  "info": {
    "database": { "status": "up" },
    "memory_heap": { "status": "up" }
  },
  "error": {},
  "details": {
    "database": { "status": "up" },
    "memory_heap": { "status": "up" }
  }
}
```

실패하면 `info`가 비고 `error`에 실패 항목이 들어간다. 모니터링 시스템에서 `error` 키만 보고 알람을 걸어도 된다.

## TypeOrmHealthIndicator

DB 연결이 살아있는지 확인하는 가장 흔한 indicator다. 내부적으로 `SELECT 1` 류의 가벼운 쿼리를 날리는 방식이다.

```ts
import { TypeOrmHealthIndicator } from '@nestjs/terminus'

@Get()
@HealthCheck()
check() {
  return this.health.check([
    () => this.db.pingCheck('postgres', { timeout: 1000 }),
  ])
}
```

`timeout`은 반드시 잡아야 한다. 기본값은 1000ms인데, 명시하지 않은 채로 두면 DB가 응답을 늦게 줄 때 health check 자체가 늘어진다. Kubernetes probe는 `timeoutSeconds`를 별도로 잡지만, 그 안쪽에서 indicator가 30초씩 매달려 있으면 probe 타임아웃 직전에 실패가 나서 노이즈가 된다. 보통 500~1500ms로 맞춘다.

여러 connection이 있으면 `connection` 옵션으로 지정한다.

```ts
@Get()
@HealthCheck()
check() {
  return this.health.check([
    () => this.db.pingCheck('primary', { connection: this.primaryDataSource, timeout: 1000 }),
    () => this.db.pingCheck('replica', { connection: this.replicaDataSource, timeout: 1000 }),
  ])
}
```

주의할 점은 `pingCheck`가 connection pool에서 커넥션을 하나 가져온다는 것이다. pool이 꽉 차 있으면 ping 자체가 대기 큐에 들어간다. 운영에서 traffic이 몰릴 때 health check가 503을 토하는 패턴이 보이면 pool 크기 부족을 의심해야 한다. probe 전용 커넥션을 쓰고 싶으면 별도 `DataSource`를 만들어서 넘기는 방법이 있다.

## MongooseHealthIndicator

Mongoose도 비슷한 방식이다. `@nestjs/mongoose`와 `mongoose`가 설치되어 있으면 자동으로 동작한다.

```ts
import { MongooseHealthIndicator } from '@nestjs/terminus'

@Get()
@HealthCheck()
check() {
  return this.health.check([
    () => this.mongo.pingCheck('mongodb', { timeout: 1500 }),
  ])
}
```

내부적으로 `admin().ping()`을 호출한다. MongoDB의 ping 명령은 매우 가벼워서 부담은 크지 않지만, replica set 구성에서 secondary로 연결된 클라이언트가 primary 선출 중일 때 일시적으로 실패한다. 이 실패가 liveness에 영향을 주지 않도록 readiness에만 묶어두는 게 안전하다.

## HttpHealthIndicator

외부 서비스 의존성을 검사하는 indicator다. 인증 서버, 결제 API, 다른 마이크로서비스 같은 외부 의존성을 확인한다.

```ts
import { HttpHealthIndicator } from '@nestjs/terminus'
import { HttpModule } from '@nestjs/axios'

@Module({
  imports: [TerminusModule, HttpModule],
  controllers: [HealthController],
})
export class HealthModule {}
```

```ts
@Get()
@HealthCheck()
check() {
  return this.health.check([
    () => this.http.pingCheck('auth-service', 'https://auth.example.com/health'),
  ])
}
```

여기서 함정이 하나 있다. 외부 서비스를 liveness probe에 넣으면 그 서비스 장애가 내 서비스의 Pod 재시작으로 번진다. 외부 의존성은 거의 항상 readiness에만 넣어야 한다. liveness는 "이 프로세스가 살아있나"를 묻는 것이고, 외부 서비스가 죽었다고 내 프로세스를 죽일 이유는 없다.

또 하나, `pingCheck`는 기본적으로 GET 요청을 날리고 응답 status code가 2xx면 통과로 간주한다. 외부 API가 인증을 요구하면 별도 로직이 필요하다. 그럴 때는 `responseCheck`를 쓴다.

```ts
() => this.http.responseCheck(
  'auth-service',
  'https://auth.example.com/health',
  (res) => res.status === 200 && res.data?.status === 'up',
)
```

타임아웃을 axios 레벨에서 잡아두지 않으면 외부 서비스가 응답을 안 줄 때 probe가 무한정 대기한다. `HttpModule.register({ timeout: 2000 })`로 모듈 단위에서 잡거나, 호출별로 `AxiosRequestConfig`를 넘긴다.

## MemoryHealthIndicator

힙 메모리와 RSS를 검사한다. 절대값 임계치를 넘으면 실패로 보고한다.

```ts
@Get()
@HealthCheck()
check() {
  return this.health.check([
    () => this.memory.checkHeap('heap', 500 * 1024 * 1024),
    () => this.memory.checkRSS('rss', 1024 * 1024 * 1024),
  ])
}
```

`checkHeap`은 V8 heap used가 임계치를 넘는지, `checkRSS`는 프로세스의 resident set size가 임계치를 넘는지 본다. 단위는 바이트다.

이 indicator는 신중하게 써야 한다. 메모리 임계치를 liveness probe에 묶어두면, 메모리가 일시적으로 튀어오를 때마다 컨테이너가 재시작된다. Node.js는 GC 직전에 heap이 꽉 차는 게 정상이고, 큰 요청이 들어오면 일시적으로 RSS가 튄다. liveness에 넣으면 그 모든 순간이 재시작 이벤트가 된다.

차라리 Kubernetes의 `resources.limits.memory`를 잡아두고 OOMKiller에게 맡기는 게 깔끔하다. memory indicator는 모니터링 목적의 `/health/details` 같은 별도 엔드포인트에 두는 편이 낫다.

## DiskHealthIndicator

디스크 사용량을 검사한다. 컨테이너 환경에서는 거의 쓸 일이 없지만 VM이나 베어메탈에 배포할 때는 유용하다.

```ts
import { DiskHealthIndicator } from '@nestjs/terminus'

@Get()
@HealthCheck()
check() {
  return this.health.check([
    () => this.disk.checkStorage('storage', {
      path: '/',
      thresholdPercent: 0.9,
    }),
  ])
}
```

`thresholdPercent: 0.9`는 디스크가 90% 차면 실패. `threshold` 옵션으로 절대값(바이트)을 줄 수도 있다.

컨테이너에서는 `/`가 컨테이너 layer 자체라서 큰 의미가 없고, 로그나 임시 파일을 쓰는 volume mount path를 검사해야 한다. emptyDir이나 PVC를 쓴다면 그 마운트 경로를 명시하자.

## 커스텀 HealthIndicator

내장 indicator로 못 다루는 게 항상 있다. Kafka consumer가 lag 없이 잘 돌고 있는지, Redis Cluster의 모든 노드가 응답하는지, 내부 큐가 안 막혔는지 같은 것들이다. 이럴 때 커스텀 indicator를 짠다.

```ts
import { Injectable } from '@nestjs/common'
import { HealthIndicator, HealthIndicatorResult, HealthCheckError } from '@nestjs/terminus'
import { Redis } from 'ioredis'

@Injectable()
export class RedisHealthIndicator extends HealthIndicator {
  constructor(private readonly redis: Redis) {
    super()
  }

  async pingCheck(key: string): Promise<HealthIndicatorResult> {
    try {
      const start = Date.now()
      const pong = await this.redis.ping()
      const latency = Date.now() - start

      const isHealthy = pong === 'PONG' && latency < 200

      const result = this.getStatus(key, isHealthy, {
        latency,
        response: pong,
      })

      if (isHealthy) {
        return result
      }
      throw new HealthCheckError('Redis ping failed', result)
    } catch (err) {
      throw new HealthCheckError(
        'Redis ping failed',
        this.getStatus(key, false, { message: err.message }),
      )
    }
  }
}
```

`HealthIndicator` 추상 클래스를 상속하고, `getStatus(key, isHealthy, payload)`로 표준 응답을 만든다. 실패 시 `HealthCheckError`를 던지면 `HealthCheckService`가 503으로 변환한다.

Kafka consumer의 lag 검사 같은 좀 더 복잡한 indicator는 이런 식으로 짠다.

```ts
@Injectable()
export class KafkaLagIndicator extends HealthIndicator {
  constructor(private readonly admin: Admin) {
    super()
  }

  async checkLag(key: string, topic: string, group: string, maxLag: number): Promise<HealthIndicatorResult> {
    const offsets = await this.admin.fetchOffsets({ groupId: group, topics: [topic] })
    const partitionOffsets = offsets[0]?.partitions ?? []

    const topicOffsets = await this.admin.fetchTopicOffsets(topic)

    const lags = partitionOffsets.map((p) => {
      const high = topicOffsets.find((t) => t.partition === p.partition)?.high
      return high && p.offset ? BigInt(high) - BigInt(p.offset) : 0n
    })

    const totalLag = lags.reduce((sum, l) => sum + l, 0n)
    const isHealthy = totalLag <= BigInt(maxLag)

    const result = this.getStatus(key, isHealthy, {
      totalLag: totalLag.toString(),
      maxLag,
    })

    if (isHealthy) return result
    throw new HealthCheckError('Kafka consumer lag too high', result)
  }
}
```

커스텀 indicator 짤 때 가장 흔히 빠지는 함정은 indicator 안에서 예외 처리를 제대로 안 하는 것이다. indicator가 throw하는 모든 예외는 `HealthCheckError`로 감싸야 한다. 그렇지 않으면 `HealthCheckService`가 의도하지 않은 형태로 응답을 만든다. try-catch로 모든 실패 경로를 잡아서 명시적으로 변환해야 한다.

## liveness와 readiness 분리

Kubernetes는 세 종류의 probe를 지원한다.

- **livenessProbe**: 실패하면 컨테이너 재시작
- **readinessProbe**: 실패하면 Service의 endpoint에서 Pod 제거 (트래픽 차단)
- **startupProbe**: 시작 단계에서만 동작, 통과하면 liveness/readiness가 활성화됨

각 probe의 의미가 다르니 검사 항목도 달라야 한다. 같은 `/health`를 셋에 다 물려두는 게 가장 흔한 실수다.

```ts
@Controller('health')
export class HealthController {
  constructor(
    private readonly health: HealthCheckService,
    private readonly db: TypeOrmHealthIndicator,
    private readonly http: HttpHealthIndicator,
    private readonly memory: MemoryHealthIndicator,
  ) {}

  @Get('live')
  @HealthCheck()
  liveness() {
    return this.health.check([
      () => this.memory.checkHeap('heap', 1024 * 1024 * 1024),
    ])
  }

  @Get('ready')
  @HealthCheck()
  readiness() {
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 1500 }),
      () => this.http.pingCheck('auth', 'https://auth.example.com/ping'),
    ])
  }

  @Get('startup')
  @HealthCheck()
  startup() {
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 3000 }),
    ])
  }
}
```

liveness는 거의 무조건 통과해야 한다. "프로세스가 살아있는가"만 보면 충분하다. heap 임계치를 매우 높게 잡아두거나, 아예 indicator 없이 `{ status: 'ok' }`만 반환해도 된다. DB나 외부 의존성을 여기 넣으면 안 된다. DB 일시 장애로 모든 Pod가 재시작되는 cascading failure가 일어난다.

readiness는 "이 Pod에 트래픽을 보내도 되는가"를 본다. DB, 캐시, 필수 외부 서비스를 검사한다. 실패해도 Pod는 살아있고, 의존성이 복구되면 자동으로 다시 endpoint에 추가된다.

startup은 부팅이 오래 걸리는 앱에 쓴다. NestJS는 보통 빠르지만, 부팅 중에 migration을 돌리거나 큰 캐시를 warming하는 경우가 있다. startup probe가 통과하기 전에는 liveness/readiness가 동작하지 않으므로, 시작 단계에서 일시적으로 응답이 늦더라도 재시작되지 않는다.

Kubernetes 설정 예시.

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 3000
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /health/startup
    port: 3000
  periodSeconds: 5
  failureThreshold: 30
```

`failureThreshold: 30`에 `periodSeconds: 5`면 startup이 150초까지 허용된다는 의미다. migration이 1~2분 걸리는 앱이라도 그 안에 완료되면 정상 기동으로 본다.

## startup probe와 부팅 단계 의존성

startup probe가 없던 시절에는 `initialDelaySeconds`로 liveness를 미루는 방식을 썼다. 이 방식의 문제는 부팅 시간을 정확히 예측해야 한다는 것이다. 30초 잡았는데 35초 걸리면 재시작 루프에 빠지고, 90초 잡아두면 평소엔 60초 늦게 트래픽이 들어온다.

startup probe는 "성공할 때까지 liveness를 보류"하는 방식이라 이 문제가 없다. NestJS에서는 부팅 중에 의존성을 초기화하는 동안 startup endpoint만 따로 반환을 다르게 줄 수도 있다.

```ts
import { Injectable, OnApplicationBootstrap } from '@nestjs/common'

@Injectable()
export class AppReadyState implements OnApplicationBootstrap {
  private ready = false

  onApplicationBootstrap() {
    this.ready = true
  }

  isReady() {
    return this.ready
  }
}
```

```ts
@Get('startup')
startup() {
  if (!this.appReady.isReady()) {
    throw new ServiceUnavailableException({ status: 'starting' })
  }
  return this.health.check([
    () => this.db.pingCheck('database', { timeout: 3000 }),
  ])
}
```

`onApplicationBootstrap`은 모든 모듈의 의존성이 다 초기화된 다음에 호출된다. 이 시점 전까지는 startup probe가 503을 반환해서 Kubernetes가 기다리게 만든다.

## graceful shutdown 연동

Pod가 종료될 때 시퀀스를 이해해야 한다. Kubernetes가 Pod를 종료할 때 두 가지 일이 거의 동시에 일어난다.

1. Service endpoint에서 Pod를 제거 (kubelet → kube-proxy 전파)
2. 컨테이너에 SIGTERM 전송

문제는 1번이 비동기라서 즉시 반영되지 않는다는 점이다. SIGTERM을 받은 직후에도 몇 초간 트래픽이 계속 들어온다. 이 시점에 앱이 연결을 끊으면 클라이언트는 5xx를 받는다.

올바른 시퀀스는 이렇다.

1. SIGTERM 수신
2. readiness probe를 의도적으로 실패시켜서 Service에서 빠지도록 유도
3. `preStop` hook의 sleep 또는 일정 시간 대기 (보통 5~15초)
4. 새 요청 안 받고 in-flight 요청만 완료
5. DB 연결 정리, 큐 작업 commit, Redis subscriber 정리
6. 프로세스 종료

NestJS에서는 `enableShutdownHooks()`를 켜야 lifecycle hook이 동작한다.

```ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule)
  app.enableShutdownHooks()
  await app.listen(3000)
}
bootstrap()
```

`enableShutdownHooks()`를 호출하지 않으면 `OnModuleDestroy`, `OnApplicationShutdown`이 전혀 동작하지 않는다. 이걸 빼먹고 "왜 종료 시 정리 로직이 안 도냐"고 고민하는 케이스가 자주 나온다.

readiness probe를 의도적으로 실패시키는 패턴은 이렇게 짠다.

```ts
import { Injectable, OnApplicationShutdown } from '@nestjs/common'

@Injectable()
export class ShutdownState implements OnApplicationShutdown {
  private shuttingDown = false

  onApplicationShutdown(signal?: string) {
    this.shuttingDown = true
  }

  isShuttingDown() {
    return this.shuttingDown
  }
}
```

```ts
@Get('ready')
readiness() {
  if (this.shutdown.isShuttingDown()) {
    throw new ServiceUnavailableException({ status: 'shutting_down' })
  }
  return this.health.check([
    () => this.db.pingCheck('database', { timeout: 1500 }),
  ])
}
```

SIGTERM이 오면 `onApplicationShutdown`이 호출되고, 그 순간부터 readiness가 503을 반환한다. Kubernetes의 다음 probe 주기(보통 5초)에 endpoint에서 제거된다.

`preStop` hook으로 강제 대기를 거는 것도 같이 쓴다.

```yaml
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 10"]
```

`preStop`은 SIGTERM이 가기 직전에 실행된다. 10초 sleep 동안 readiness가 떨어지고 endpoint에서 빠진 다음에야 SIGTERM이 간다. `terminationGracePeriodSeconds`는 이 preStop 시간과 실제 정리 시간을 합친 것보다 커야 한다.

## 종료 단계 인플라이트 요청 처리

NestJS는 종료 시 HTTP 서버를 닫는다. Node.js의 `server.close()`는 새 연결은 거부하지만 진행 중인 요청은 끝까지 처리한다. 문제는 keep-alive 연결을 열어둔 클라이언트가 한참 동안 새 요청을 그 연결로 보낼 수 있다는 점이다.

`@nestjs/platform-fastify`는 fastify의 `closeGraceDelay` 옵션으로 이 부분을 제어한다.

```ts
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({ pluginTimeout: 10000 }),
)
```

`@nestjs/platform-express`는 별도 처리가 필요하다. `http-terminator` 같은 라이브러리를 쓰거나, `OnApplicationShutdown`에서 명시적으로 connection close를 호출해야 한다.

```ts
import { OnApplicationShutdown } from '@nestjs/common'
import { createHttpTerminator } from 'http-terminator'

@Injectable()
export class HttpShutdown implements OnApplicationShutdown {
  private terminator: ReturnType<typeof createHttpTerminator>

  attach(server: any) {
    this.terminator = createHttpTerminator({
      server,
      gracefulTerminationTimeout: 10000,
    })
  }

  async onApplicationShutdown() {
    if (this.terminator) {
      await this.terminator.terminate()
    }
  }
}
```

```ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule)
  app.enableShutdownHooks()
  const server = app.getHttpServer()
  app.get(HttpShutdown).attach(server)
  await app.listen(3000)
}
```

## DB 연결과 큐 정리

DB 연결을 닫는 순서도 중요하다. `OnApplicationShutdown`은 모듈 의존성 그래프의 역순으로 호출된다. DB 모듈이 다른 모듈에서 주입되어 있으면 그 다른 모듈이 먼저 정리된 다음에 DB 모듈의 hook이 호출된다.

TypeORM은 모듈이 정리될 때 `DataSource.destroy()`를 자동으로 호출한다. 별도로 처리할 필요는 없지만, 직접 만든 DB 모듈이라면 명시적으로 처리해야 한다.

```ts
@Injectable()
export class RedisService implements OnApplicationShutdown {
  constructor(@Inject('REDIS_CLIENT') private readonly redis: Redis) {}

  async onApplicationShutdown() {
    await this.redis.quit()
  }
}
```

`quit()`은 명령 큐를 비운 다음 연결을 닫는다. `disconnect()`는 즉시 연결을 끊어버려서 in-flight 명령이 유실된다. graceful shutdown에서는 거의 항상 `quit()`을 써야 한다.

Bull/BullMQ 같은 큐 워커도 종료 시 처리가 필요하다. 진행 중인 job이 있는 상태에서 프로세스를 죽이면 그 job은 다른 워커가 picking up할 때까지 stalled 상태로 남는다.

```ts
@Processor('email')
export class EmailProcessor implements OnApplicationShutdown {
  constructor(private readonly worker: Worker) {}

  async onApplicationShutdown() {
    await this.worker.close()
  }
}
```

`worker.close()`는 현재 처리 중인 job이 완료될 때까지 기다린 다음 종료한다. `terminationGracePeriodSeconds`가 이 대기 시간을 커버해야 한다. 평균 job 처리 시간이 30초인데 grace period가 10초면 job이 잘려나간다.

## health check 자체의 인증

운영 환경에서 health endpoint가 외부에 노출되면 정보 노출 사고가 난다. 응답에 DB host, 외부 서비스 URL, 메모리 사용량이 다 들어있다. 외부 공격자에게 인프라 정보를 알려주는 셈이다.

가장 깔끔한 해결은 ingress 단계에서 health path를 외부에서 막는 것이다. Kubernetes 환경이면 NodePort나 ClusterIP에만 노출하고, Ingress에서 `/health/*`를 차단한다.

별도 포트로 분리하는 방법도 있다.

```ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule)
  app.enableShutdownHooks()
  await app.listen(3000)

  const healthApp = await NestFactory.create(HealthModule)
  await healthApp.listen(9090)
}
```

운영 트래픽은 3000번, health는 9090번. Service spec에서 9090은 cluster 내부에서만 접근 가능하게 한다. probe도 9090번을 본다. 외부 공격자는 3000번만 보이므로 정보 노출 표면이 줄어든다.

## 응답을 가볍게 유지하는 이유

probe는 `periodSeconds`마다 호출된다. 5초마다 호출되는 readiness probe에서 indicator가 매번 무거운 쿼리를 날리면 DB 부담이 누적된다. 10개 Pod가 5초마다 검사하면 분당 120번의 ping이 DB로 간다. 거기에 외부 HTTP probe까지 더하면 외부 서비스에도 부담이 간다.

indicator 안에서 결과를 짧게 캐싱하는 패턴이 도움이 된다.

```ts
@Injectable()
export class CachedDbIndicator extends HealthIndicator {
  private cache: { ts: number; result: HealthIndicatorResult } | null = null
  private readonly ttl = 2000

  constructor(private readonly db: TypeOrmHealthIndicator) {
    super()
  }

  async pingCheck(key: string): Promise<HealthIndicatorResult> {
    const now = Date.now()
    if (this.cache && now - this.cache.ts < this.ttl) {
      return this.cache.result
    }
    const result = await this.db.pingCheck(key, { timeout: 1000 })
    this.cache = { ts: now, result }
    return result
  }
}
```

TTL을 probe 주기보다 짧게 잡으면 매 probe가 캐시 미스가 나니까 의미가 없다. 보통 probe 주기의 1~2배로 잡는다. 5초 probe면 5~10초 TTL.

캐시를 너무 길게 잡으면 실제 장애 감지가 늦어진다. liveness/readiness 응답이 항상 시간 지연을 가진다는 점을 받아들여야 한다.

## 실제 운영에서 자주 놓치는 부분

운영하다 보면 health check가 잘못 짜져서 생기는 사고가 의외로 많다.

**DNS 캐시 문제**: HttpHealthIndicator로 외부 서비스를 검사하는데, DNS가 바뀌어도 Node.js의 DNS 캐시 때문에 옛날 IP로 계속 요청을 보낸다. 이걸 안 풀어주면 외부 서비스 마이그레이션 시 health가 계속 실패한다. `lookup` 옵션을 주거나 `cacheable-lookup` 같은 라이브러리를 쓴다.

**probe timeout과 indicator timeout의 비대칭**: Kubernetes probe의 `timeoutSeconds`보다 indicator의 timeout이 더 길면, probe는 timeout으로 실패하지만 indicator는 계속 실행 중이다. 다음 probe가 들어오면 indicator 호출이 중첩되고 DB connection이 누적된다. `timeoutSeconds` × 0.7 정도를 indicator timeout으로 잡는 게 안전하다.

**circuit breaker와 health check의 충돌**: 외부 서비스에 circuit breaker가 걸려 있는데, health check가 그 외부 서비스를 직접 호출한다. circuit이 열려도 health check는 직접 호출하므로 매번 timeout이 난다. circuit breaker 상태를 health에 반영하든가, breaker가 적용된 client를 indicator에 주입해야 한다.

**migration 동안 readiness 처리**: 부팅 직후 migration이 도는 동안 readiness가 통과하면 트래픽이 들어오는데, schema가 아직 안 만들어져서 쿼리가 실패한다. migration이 끝날 때까지 readiness를 false로 유지하는 게 안전하다. startup probe로 이걸 처리하든가, `AppReadyState` 패턴으로 명시적으로 제어한다.

**health endpoint가 부하 측정에 잡혀 들어감**: APM 도구가 모든 요청을 추적하면 health check도 그 안에 들어간다. 분당 수백 번 호출되는 health check가 traffic graph를 왜곡하고 throughput 통계를 망친다. APM 설정에서 `/health/*`를 제외하거나 sampling을 0으로 잡는다.
