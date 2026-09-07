---
title: Bull Arena 대시보드 NestJS 통합
tags: [nodejs, messaging, redis, backend]
updated: 2026-09-07
---

# Bull Arena 대시보드 NestJS 통합

Bull Arena는 `bull` 큐의 상태를 브라우저에서 보여주는 웹 UI다. 대기 중인 작업, 완료·실패 건수, 개별 job 상세, 재시도·삭제 버튼이 있다. Express 라우터 하나를 반환하는 구조라서 NestJS에 붙이려면 `app.use()`로 마운트한다.

주의할 게 두 가지다. 첫째, Arena는 `bull` 전용이다. `bullmq`와는 호환되지 않는다. 둘째, 인증이 없다. 라우터를 그냥 붙이면 누구든 접근할 수 있다.

BullMQ를 쓰고 있다면 이 문서는 관계없다. [Nest_JS_작업_큐_Bull_MQ.md](Nest_JS_작업_큐_Bull_MQ.md)에서 Bull Board 통합을 보면 된다.


## 설치

```bash
npm install bull-arena bull
```

`bull`이 별도로 필요하다. Arena가 bull의 Queue 객체를 직접 받아서 쓰기 때문이다.

NestJS에서 bull 큐를 이미 `@nestjs/bull`로 등록하고 있다면 `bull`은 이미 설치돼 있다.


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
