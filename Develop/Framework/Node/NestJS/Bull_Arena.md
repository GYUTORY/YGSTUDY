---
title: Bull Arena 대시보드 NestJS 통합
tags: [nodejs, messaging, redis, backend]
updated: 2026-09-07
---

# Bull Arena 대시보드 NestJS 통합

Bull Arena는 `bull` 큐의 상태를 브라우저에서 보여주는 웹 UI다. 대기 중인 작업, 완료·실패 건수, 개별 job 상세, 재시도·삭제 버튼이 있다. Express 라우터 하나를 반환하는 구조라서 NestJS에 붙이려면 `app.use()`로 마운트한다.

주의할 게 두 가지다. 첫째, Arena는 `bull` 전용이다. `bullmq`와는 호환되지 않는다. 둘째, 인증이 없다. 라우터를 그냥 붙이면 누구든 접근할 수 있다.

BullMQ를 쓰고 있다면 이 문서는 관계없다. [Nest_JS_작업_큐_Bull_MQ.md](Nest_JS_작업_큐_Bull_MQ.md)에서 Bull Board 통합을 보면 된다.


## 설치와 버전 호환

```bash
npm install bull-arena bull
```

`bull`이 별도로 필요하다. Arena가 bull의 Queue 객체를 직접 받아서 쓰기 때문이다.

NestJS에서 bull 큐를 이미 `@nestjs/bull`로 등록하고 있다면 `bull`은 이미 설치돼 있다.

bull-arena는 bull@3.x의 내부 Redis 키 구조를 직접 읽는다. bull 패키지 메이저 버전이 맞지 않으면 job이 0개로 나오거나 undefined 에러가 난다.

| bull-arena | bull | bullmq |
|---|---|---|
| 3.x (현행) | ^3.x | 미지원 |
| 2.x | ^3.x | 미지원 |

bullmq는 어느 버전의 bull-arena도 지원하지 않는다. 키 구조 자체가 다르다.

`@nestjs/bull`은 bull@3.x를 peer dependency로 요구한다. bull-arena@3.x와 세트로 쓸 수 있다. `@nestjs/bullmq`를 쓰고 있다면 Arena는 선택지에서 빠진다.


## NestJS에 마운트하기

`main.ts`에서 Express 인스턴스를 꺼내 라우터를 붙인다.

```typescript
import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import Arena from 'bull-arena';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);

  const arena = Arena(
    {
      queues: [
        {
          type: 'bull',
          name: 'email',
          hostId: 'api-server',
          redis: {
            host: process.env.REDIS_HOST,
            port: Number(process.env.REDIS_PORT),
          },
        },
        {
          type: 'bull',
          name: 'thumbnail',
          hostId: 'api-server',
          redis: {
            host: process.env.REDIS_HOST,
            port: Number(process.env.REDIS_PORT),
          },
        },
      ],
    },
    {
      basePath: '/arena',
      disableListen: true, // 반드시 true. Arena가 자체 포트를 열지 못하게 막는다
    }
  );

  app.use('/arena', arena);

  await app.listen(3000);
}
bootstrap();
```

`disableListen: true`를 빠뜨리면 Arena가 4567 포트로 별도 서버를 연다. NestJS 프로세스 안에서 포트가 두 개 뜨고, 인증 미들웨어를 달아도 직접 4567로 접근하면 뚫린다.

`basePath`는 URL prefix다. `/arena`로 설정하면 `http://host/arena`에서 UI가 열린다. Arena 내부 정적 파일 경로도 여기에 맞춰진다. basePath 없이 루트에 붙이면 NestJS 라우터와 충돌한다.


## 인증 미들웨어

Arena는 인증 기능이 없다. 운영 환경에 그냥 올리면 누구든 job을 보고 삭제하고 재시도할 수 있다.

가장 단순한 방법은 Basic Auth 미들웨어를 `/arena` 앞에 세우는 것이다.

```typescript
import basicAuth from 'express-basic-auth';

app.use(
  '/arena',
  basicAuth({
    users: { admin: process.env.ARENA_PASSWORD },
    challenge: true,
    realm: 'Bull Arena',
  }),
  arena
);
```

`express-basic-auth`가 없으면 `npm install express-basic-auth`로 설치한다.

JWT 기반 인증을 쓰는 경우, 미들웨어를 직접 작성한다.

```typescript
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

function arenaAuthMiddleware(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    res.status(401).json({ message: 'Unauthorized' });
    return;
  }
  try {
    jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ message: 'Unauthorized' });
  }
}

app.use('/arena', arenaAuthMiddleware, arena);
```

브라우저에서 직접 접근하는 특성상 JWT 방식은 사용성이 불편하다. 내부 망에서만 쓴다면 IP 화이트리스트로 막는 게 현실적이다.

```typescript
function ipWhitelistMiddleware(req: Request, res: Response, next: NextFunction) {
  const allowedIPs = (process.env.ARENA_ALLOWED_IPS ?? '').split(',');
  const clientIP = req.ip ?? req.socket.remoteAddress ?? '';
  if (!allowedIPs.some(ip => clientIP.includes(ip))) {
    res.status(403).send('Forbidden');
    return;
  }
  next();
}
```

어느 방식이든, **미들웨어가 arena 라우터보다 먼저 등록돼야 한다**. `app.use('/arena', arena, middleware)` 순서로 넣으면 미들웨어가 실행되지 않는다.


## Redis Sentinel 연결

운영 환경에서 Redis를 Sentinel로 구성한 경우, bull-arena의 `redis` 설정에 ioredis Sentinel 옵션을 그대로 쓸 수 있다.

```typescript
const arena = Arena({
  queues: [
    {
      type: 'bull',
      name: 'email',
      hostId: 'api-server',
      redis: {
        sentinels: [
          { host: 'sentinel-1.internal', port: 26379 },
          { host: 'sentinel-2.internal', port: 26379 },
          { host: 'sentinel-3.internal', port: 26379 },
        ],
        name: 'mymaster',      // Sentinel master 이름. redis.conf의 sentinel monitor와 일치해야 한다
        password: process.env.REDIS_PASSWORD,
        sentinelPassword: process.env.SENTINEL_PASSWORD,
      },
    },
  ],
}, { basePath: '/arena', disableListen: true });
```

bull-arena가 내부적으로 ioredis를 쓰기 때문에 ioredis의 Sentinel 옵션이 그대로 통한다. `host`/`port` 대신 `sentinels` 배열을 넣으면 된다.

Redis Cluster는 bull@3와 함께 쓸 수 없다. bull이 내부적으로 Lua 스크립트(EVAL)와 멀티키 연산을 쓰는데, Redis Cluster는 키가 다른 슬롯에 있을 때 이 명령을 거부한다. bull@3 공식 문서도 Cluster 비지원을 명시하고 있다. Cluster를 쓰는 환경이라면 bullmq + Redis Cluster 조합으로 가야 한다(이 경우 Arena 대신 Bull Board를 쓴다).


## 폴링 방식의 한계

Arena는 WebSocket이나 SSE가 없다. 브라우저가 Arena API 엔드포인트를 주기적으로 폴링해서 화면을 갱신한다. 기본 간격은 약 2~5초다. 이 값은 Arena 설정으로 조정할 수 없다.

실제로 문제가 되는 상황은 두 가지다.

첫째, job 처리 속도가 폴링 간격보다 빠를 때다. 초당 수백 건씩 처리되는 큐라면 `active` 탭에서 job이 순식간에 왔다 사라지거나, 방금 완료된 job이 여전히 active로 보이기도 한다. Arena로 실시간 처리 현황을 모니터링하는 건 무리다.

둘째, 큐에 오류가 쌓일 때 확인이 늦다. failed 건수가 갑자기 치솟는 상황을 Arena로는 놓치기 쉽다. 실시간 알림이 필요하다면 bull의 이벤트 훅(`queue.on('failed', ...)`)을 별도로 달아야 한다.

새로고침 버튼을 눌러도 즉각 반영되지 않는 경우가 있다. Arena가 내부적으로 응답을 짧게 캐싱하기 때문이다. 방금 재시도를 눌렀는데 여전히 failed로 보인다면 몇 초 기다리면 된다.


## big payload 로드 지연

Arena는 job 목록을 불러올 때 각 job의 `data` 필드(페이로드) 전체를 가져온다. payload가 크면 completed 탭이나 failed 탭 진입 자체가 느려진다.

운영하다 보면 이런 경우가 생긴다. 예를 들어 이미지 처리 큐에 원본 파일을 Base64로 직렬화해서 payload에 담으면, 건당 수십 KB~수 MB가 된다. completed 건수가 수천 개 쌓인 상태에서 탭을 열면 Arena가 Redis에서 그 데이터를 전부 읽어 JSON으로 변환하고 브라우저에 내려보낸다. 탭이 수십 초 동안 안 열리거나 브라우저가 멈춘다.

해결 방법은 job payload를 작게 유지하는 것이다. 파일이나 대용량 데이터는 S3·스토리지에 올리고 job에는 참조 키만 넣는다.

```typescript
// 피해야 할 패턴
await emailQueue.add({
  attachment: fs.readFileSync('report.pdf').toString('base64'), // 수 MB
  to: 'user@example.com',
});

// 대신
await emailQueue.add({
  attachmentKey: 's3://bucket/report-uuid.pdf', // 참조만
  to: 'user@example.com',
});
```

이미 payload가 커진 상태라면 Arena 설정에서 `removeOnComplete`를 활용한다. bull 큐 등록 시점에 완료된 job을 자동으로 제거하면 Arena가 읽어야 하는 데이터 양이 줄어든다.

```typescript
// @nestjs/bull 큐 등록 시
BullModule.registerQueue({
  name: 'email',
  defaultJobOptions: {
    removeOnComplete: 100,  // 최근 100개만 남긴다
    removeOnFail: 200,
  },
}),
```


## 여러 서비스가 같은 Redis를 공유할 때 hostId 충돌

`hostId`는 Arena UI에서 큐를 그룹핑하는 라벨이다. 실제 Redis 연결이나 큐 동작과는 관계없다.

문제가 생기는 건 이런 경우다. api-server와 worker-server가 각각 `email` 큐를 갖고 있고 같은 Redis를 쓴다. 이 두 큐를 하나의 Arena에 모아 보려고 아래처럼 등록했다.

```typescript
queues: [
  {
    type: 'bull',
    name: 'email',
    hostId: 'api-server',
    redis: redisConfig,
  },
  {
    type: 'bull',
    name: 'email',
    hostId: 'worker-server',
    redis: redisConfig,  // 동일한 Redis
  },
],
```

두 항목이 같은 Redis의 같은 키(`bull:email:waiting` 등)를 읽기 때문에 Arena 사이드바에 `email` 큐가 두 줄로 나오고, 각 줄의 job 수치가 동일하다. 삭제나 재시도 버튼을 한 줄에서 누르면 다른 줄에도 즉각 반영된다. 사실상 같은 큐를 두 번 보고 있는 것이다.

실제로 api-server와 worker-server가 같은 `email` 큐를 공유하는 경우라면 Arena에 한 번만 등록한다.

```typescript
// 같은 Redis의 같은 큐: 하나만 등록
queues: [
  {
    type: 'bull',
    name: 'email',
    hostId: 'shared',
    redis: redisConfig,
  },
],
```

여러 서비스가 이름이 다른 큐를 각각 갖고 있다면 hostId로 서비스를 구분해도 된다. 단, 큐 이름이 겹치지 않을 때만이다.

```typescript
queues: [
  { type: 'bull', name: 'api-email', hostId: 'api', redis: redisConfig },
  { type: 'bull', name: 'api-sms', hostId: 'api', redis: redisConfig },
  { type: 'bull', name: 'worker-thumbnail', hostId: 'worker', redis: redisConfig },
  { type: 'bull', name: 'worker-report', hostId: 'worker', redis: redisConfig },
],
```

큐 이름 자체에 서비스 prefix를 붙이는 게 가장 단순하다. hostId는 시각적 그룹핑에 불과하고 충돌을 막아주지 않는다.


## BullMQ와 동작하지 않는 이유

Arena는 `bull` v3의 내부 구조를 그대로 읽는다. bull이 Redis에 저장하는 키 패턴은 `bull:{queueName}:waiting`, `bull:{queueName}:active` 형태다.

BullMQ는 키 구조가 다르다. `bull:{queueName}:marker`, `bull:{queueName}:events` 같은 키를 쓰고, job 데이터 형식도 달라졌다. Arena를 BullMQ 큐에 붙이면 두 가지 결과 중 하나다.

- 큐 목록은 뜨는데 job이 0개로 나온다. Arena가 읽는 키에 데이터가 없으니까.
- `Queue is not defined` 또는 `Cannot read properties of undefined` 에러가 난다. BullMQ의 Queue 인스턴스를 Arena에 넘기면 메서드 시그니처가 달라서 내부에서 터진다.

고칠 방법이 없다. Arena가 BullMQ를 지원하지 않는다.


## 실제로 자주 틀리는 것들

**redis 연결 설정을 큐마다 반복한다.** `queues` 배열 안에 연결 정보를 넣는 구조라서 큐가 늘어날수록 반복이 생긴다. 환경변수로 공통 객체를 만들어 spread해서 쓴다.

```typescript
const redisConfig = {
  host: process.env.REDIS_HOST,
  port: Number(process.env.REDIS_PORT),
};

const arena = Arena({
  queues: [
    { type: 'bull', name: 'email', hostId: 'worker', redis: redisConfig },
    { type: 'bull', name: 'sms', hostId: 'worker', redis: redisConfig },
  ],
}, { basePath: '/arena', disableListen: true });
```

**`hostId`를 의미 있게 짓지 않으면 나중에 헷갈린다.** 여러 서버에서 같은 큐를 바라볼 때 어느 서버의 Arena인지 구분하는 값이다. 서버 식별자나 역할 이름을 넣는다.

**`app.use()` 시점이 `await app.listen()` 이후면 안 붙는다.** Express 미들웨어 등록은 서버 시작 전에 해야 한다. bootstrap 함수 안에서 listen 전에 `app.use()`를 호출한다.


## Bull Board로 넘어가는 시점

아래 상황 중 하나라면 Bull Board로 전환을 검토한다.

BullMQ로 마이그레이션하는 경우. Arena가 BullMQ를 지원하지 않으니 전환 말고는 방법이 없다.

NestJS 모듈 시스템에 제대로 통합하고 싶은 경우. Arena는 `main.ts`에서 직접 Express 라우터를 다루는 방식이라 모듈 시스템 밖에 있다. Bull Board는 `@bull-board/nestjs`가 NestJS 모듈로 통합되고, 인증도 어댑터 형태로 붙일 수 있다.

여러 팀이 같은 Arena를 쓰는데 권한을 나눠야 하는 경우. Arena는 인증 자체가 없어서 읽기/쓰기 구분이 불가능하다.

Bull Board 설치는 다음과 같다.

```bash
npm install @bull-board/api @bull-board/nestjs @bull-board/express bullmq
```

```typescript
// app.module.ts
import { BullBoardModule } from '@bull-board/nestjs';
import { BullMQAdapter } from '@bull-board/api/bullMQAdapter';
import { ExpressAdapter } from '@bull-board/express';

@Module({
  imports: [
    BullModule.forRoot({ connection: { host: 'localhost', port: 6379 } }),
    BullModule.registerQueue({ name: 'email' }),
    BullBoardModule.forRoot({
      route: '/queues',
      adapter: ExpressAdapter,
    }),
    BullBoardModule.forFeature({
      name: 'email',
      adapter: BullMQAdapter,
    }),
  ],
})
export class AppModule {}
```

Bull Arena에서 Bull Board로 옮길 때 기존 bull 큐가 있으면 `@bull-board/api/bullAdapter`를 쓴다. BullMQ 큐면 `@bull-board/api/bullMQAdapter`다. 같은 UI에 두 어댑터를 섞어 쓸 수 있다.
