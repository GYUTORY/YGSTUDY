---
title: NestJS @nestjs/bull (Bull v3) 작업 큐
tags: [nodejs, messaging, redis, backend]
updated: 2026-09-07
---

# NestJS @nestjs/bull (Bull v3) 작업 큐

신규 프로젝트라면 BullMQ를 쓴다. 그런데 실제 현장에는 `@nestjs/bull`로 작성된 코드가 여전히 많다. `@nestjs/bull`은 bull v3를 NestJS 모듈·데코레이터 패턴으로 감싼 것이고, `@nestjs/bullmq`와는 설치 패키지부터 데코레이터 시그니처, 내부 Redis 사용 방식까지 다르다.

BullMQ 기반 운영은 [Nest_JS_작업_큐_Bull_MQ.md](Nest_JS_작업_큐_Bull_MQ.md)에 정리했다. 이 문서는 bull v3 + `@nestjs/bull` 사용법과, 언젠가 BullMQ로 넘어갈 때 바꿔야 할 지점을 다룬다.


## 설치

```bash
npm install @nestjs/bull bull
```

bull 패키지만 설치하면 된다. BullMQ는 별개 패키지다. `@nestjs/bull`과 `bullmq`를 동시에 설치하면 타입 충돌이 나고 데코레이터가 제대로 붙지 않는다.

bull은 내부적으로 ioredis를 쓴다. ioredis 버전 충돌이 가끔 나는데, `npm ls ioredis`로 버전이 하나로 통일됐는지 먼저 확인한다.


## 모듈 등록

루트 모듈에서 Redis 연결 한 번, 기능 모듈에서 큐 이름 등록 한 번이다.

```typescript
// app.module.ts
import { BullModule } from '@nestjs/bull';
import { ConfigModule, ConfigService } from '@nestjs/config';

@Module({
  imports: [
    BullModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        redis: {
          host: config.get<string>('REDIS_HOST'),
          port: config.get<number>('REDIS_PORT'),
          password: config.get<string>('REDIS_PASSWORD'),
        },
      }),
    }),
  ],
})
export class AppModule {}
```

BullMQ의 `connection` 키와 달리 `@nestjs/bull`에서는 `redis`다. `connection`으로 쓰면 연결 설정이 무시되고 기본값(localhost:6379)으로 붙는다. 개발 환경에서는 Redis 인증 없이 붙어서 잘 돌다가 프로덕션에서 터지는 상황이 나온다.

기능 모듈에서 큐를 등록한다.

```typescript
// email.module.ts
import { BullModule } from '@nestjs/bull';

@Module({
  imports: [
    BullModule.registerQueue({
      name: 'email',
      defaultJobOptions: {
        attempts: 3,
        backoff: { type: 'exponential', delay: 5000 },
        removeOnComplete: true,
        removeOnFail: false,
      },
    }),
  ],
  providers: [EmailProcessor, EmailService],
})
export class EmailModule {}
```

`defaultJobOptions`를 여기에 두면 이 큐로 들어오는 모든 job에 적용된다. `attempts` 기본값은 1이라 설정 안 하면 실패해도 재시도 없이 끝난다. `removeOnComplete`도 기본값이 false라 완료된 job이 Redis에 계속 쌓인다.


## Producer: 큐에 job 추가

```typescript
import { InjectQueue } from '@nestjs/bull';
import { Queue } from 'bull';

@Injectable()
export class EmailService {
  constructor(@InjectQueue('email') private readonly emailQueue: Queue) {}

  async sendWelcomeEmail(userId: string) {
    await this.emailQueue.add('send-welcome', { userId }, {
      attempts: 5,
      backoff: { type: 'exponential', delay: 3000 },
      delay: 1000,
      priority: 10,
      removeOnComplete: true,
    });
  }
}
```

`@InjectQueue('email')`에서 문자열이 `registerQueue`의 `name`과 일치해야 한다. 다르면 의존성 주입 오류가 아니라 런타임에 `add`가 에러를 낸다.


## @Process() 핸들러

`@Processor('큐이름')` 클래스 안에 `@Process('잡이름')` 메서드를 선언한다.

```typescript
import { Processor, Process } from '@nestjs/bull';
import { Job } from 'bull';

@Processor('email')
export class EmailProcessor {
  @Process('send-welcome')
  async handleSendWelcome(job: Job<{ userId: string }>) {
    const { userId } = job.data;
    await this.mailerService.sendWelcome(userId);
  }

  @Process('send-reset-password')
  async handleResetPassword(job: Job<{ email: string }>) {
    await this.mailerService.sendResetPassword(job.data.email);
  }
}
```

잡 이름 없이 `@Process()`만 쓰면 해당 큐의 모든 job을 처리한다. 이름이 지정된 핸들러가 있으면 그쪽이 우선한다.

`@Processor('email')`의 문자열이 큐 이름과 다르면 이 프로세서는 아무 job도 처리하지 않는다. 에러도 안 나고 조용히 무시된다. 큐에 job이 쌓이는데 워커가 안 돌면 이 지점을 먼저 확인한다.


## job 옵션 상세

### attempts와 backoff

```typescript
await this.emailQueue.add('send-welcome', data, {
  attempts: 5,
  backoff: {
    type: 'exponential',  // 또는 'fixed'
    delay: 3000,          // 첫 재시도 대기 시간(ms)
  },
});
```

`exponential`은 지수 백오프다. delay가 3000이면 첫 재시도는 3초 뒤, 두 번째는 9초 뒤, 세 번째는 27초 뒤다. `fixed`를 쓰면 재시도가 한꺼번에 몰려서 장애 중인 외부 API에 스파이크를 만들 수 있다.

`attempts`는 총 시도 횟수다. 첫 시도 포함이라 `attempts: 3`이면 실패 시 재시도 2회다.

### delay

```typescript
await this.emailQueue.add('send-later', data, {
  delay: 60000, // 60초 뒤 실행
});
```

지연 실행이다. bull v3는 내부적으로 Redis sorted set을 써서 실행 시각 기준으로 정렬한다. 서버가 여러 개면 어느 워커가 처리해도 된다.

### removeOnComplete와 removeOnFail

`removeOnComplete: true`를 안 주면 완료된 job이 Redis에 계속 쌓인다. 트래픽이 많으면 Redis 메모리가 빠르게 찬다.

`removeOnFail: false`가 기본값이다. 실패한 job을 남겨두면 원인 분석에 쓸 수 있지만, 이것도 쌓이므로 Bull Arena나 별도 도구로 정기적으로 비워줘야 한다.

숫자를 주면 최근 N개만 남긴다.

```typescript
removeOnComplete: 1000, // 최근 1000개만 남긴다
removeOnFail: 500,
```

bull 패키지 버전에 따라 `removeOnComplete`의 타입 정의가 `boolean`만 있는 경우도 있다. 숫자를 넣었을 때 타입 오류가 나면 bull 버전을 확인한다.

### jobId로 중복 방지

같은 job이 두 번 큐에 들어가는 걸 막을 때 쓴다.

```typescript
await this.emailQueue.add('send-welcome', { userId }, {
  jobId: `welcome-${userId}`,
});
```

동일한 jobId를 가진 job이 이미 큐에 있으면 새 job을 추가하지 않는다. 주의할 점은 완료·실패 후 삭제된 job의 jobId는 재사용 가능하다는 것이다. 같은 사용자에게 주 1회만 이메일을 보내려면 jobId만으로는 안 된다. 외부에서 별도로 상태를 관리해야 한다.


## 동시성 설정

```typescript
@Processor({ name: 'email', concurrency: 5 })
export class EmailProcessor {
  @Process('send-welcome')
  async handleSendWelcome(job: Job) { ... }
}
```

`concurrency`는 이 프로세서 인스턴스가 동시에 처리할 수 있는 job 수다. 기본값은 1이다. 서버 인스턴스가 여러 개면 각 인스턴스의 concurrency가 합산된다. 인스턴스 2개에 `concurrency: 5`이면 최대 동시 처리 수는 10이다.

`@Process()` 메서드 단위로도 concurrency를 설정할 수 있다.

```typescript
@Process({ name: 'send-welcome', concurrency: 3 })
async handleSendWelcome(job: Job) { ... }
```

외부 API에 동시 요청을 보낼 때 rate limit 제약이 있으면 concurrency를 낮게 잡는다. 스케일 아웃할 때 인스턴스 수 × concurrency가 실제 동시 처리 수라는 점을 계산에 넣어야 한다.


## stalled job과 lockDuration

bull v3에서 워커가 job을 가져가서 처리 중인 동안 워커가 죽으면 그 job은 stalled 상태가 된다. bull은 `lockDuration`(기본 30000ms) 안에 워커가 lock을 갱신하지 않으면 job을 stalled로 판정하고 다시 대기열에 넣는다.

```typescript
BullModule.registerQueue({
  name: 'email',
  settings: {
    lockDuration: 30000,    // ms, job 처리 예상 시간보다 길게
    stalledInterval: 30000, // stalled 체크 주기
    maxStalledCount: 1,     // stalled 판정 후 재시도 횟수
  },
})
```

job 처리 시간이 30초를 넘으면 stalled로 잘못 판정돼서 같은 job이 두 번 처리된다. 처리 시간이 긴 작업은 `lockDuration`을 충분히 늘리거나 작업을 잘게 쪼개야 한다.

`maxStalledCount: 0`으로 설정하면 stalled job을 재시도하지 않고 바로 실패 처리한다. 멱등성이 없는 작업에서는 중복 실행보다 나을 수 있다.


## 이벤트 리스너

```typescript
import { Processor, Process, OnQueueFailed, OnQueueCompleted } from '@nestjs/bull';
import { Job } from 'bull';

@Processor('email')
export class EmailProcessor {
  @OnQueueFailed()
  async onFailed(job: Job, err: Error) {
    this.logger.error(`Job ${job.id} failed: ${err.message}`, {
      jobName: job.name,
      attempt: job.attemptsMade,
      data: job.data,
    });
  }

  @OnQueueCompleted()
  async onCompleted(job: Job) {
    this.logger.log(`Job ${job.id} completed`);
  }
}
```

`@OnQueueFailed()`는 최종 실패가 아니라 각 시도 실패마다 호출된다. 재시도가 3회면 3번 다 호출된다. 마지막 실패에만 반응하려면 `job.attemptsMade === job.opts.attempts`를 확인한다.


## bull v3와 BullMQ의 구조 차이

### Redis 사용 방식

bull v3는 Redis의 List와 Sorted Set으로 큐를 구현한다. `waiting`은 List, `delayed`·`active`·`completed`·`failed`는 Sorted Set이다.

BullMQ는 Redis Streams를 쓴다. Consumer Group 개념이 들어오고, at-least-once 전달을 보장하는 방식이 다르다. 실용적인 차이는 Redis 버전이다. BullMQ는 Redis 5 이상이 필요하다. bull v3는 Redis 2.6 이상이면 동작한다.

### lockDuration 동작

bull v3에서 lock은 Redis의 SET NX EX로 구현한다. 워커가 살아있는 동안 주기적으로 lock을 갱신(extend)한다. 갱신에 실패하면 job이 stalled 처리된다.

BullMQ에서는 Redis Streams의 Consumer Group이 이 역할을 일부 대신한다. stalled job 처리 방식이 다르고, `lockDuration`의 의미도 약간 다르다. BullMQ에서는 lock을 제때 갱신하지 못하면 다른 워커가 job을 가져갈 수 있다. 동일한 lockDuration 값이라도 두 라이브러리에서 동작이 같지 않다.

### job ID 중복 방지

bull v3에서 `jobId`를 지정하면 Redis HSETNX로 중복을 막는다. 이미 해당 ID가 waiting·active·delayed 상태면 추가를 건너뛴다. completed·failed 후 삭제됐으면 재추가가 가능하다.

BullMQ에서는 `jobId` 외에 `deduplication` 옵션이 추가됐다.

```typescript
// BullMQ에서
await queue.add('job', data, {
  deduplication: { id: `welcome-${userId}`, ttl: 3600000 },
});
```

`ttl` 동안은 같은 deduplication ID의 job을 추가하지 않는다. 삭제 여부와 무관하게 TTL 기준으로 동작하므로 bull v3 방식보다 더 명시적으로 제어할 수 있다.

### @Process() vs WorkerHost

bull v3 + `@nestjs/bull`은 `@Process()` 데코레이터로 핸들러를 선언한다.

BullMQ + `@nestjs/bullmq`는 `WorkerHost`를 extend하고 `process()` 메서드를 override한다.

```typescript
// @nestjs/bullmq 방식
import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor('email')
export class EmailProcessor extends WorkerHost {
  async process(job: Job): Promise<void> {
    switch (job.name) {
      case 'send-welcome':
        await this.handleWelcome(job);
        break;
    }
  }
}
```

여러 job 이름을 하나의 `process()` 안에서 switch로 처리하는 구조가 BullMQ 스타일이다. bull v3는 잡 이름마다 메서드를 따로 선언한다.


## @nestjs/bull → @nestjs/bullmq 마이그레이션

### 패키지 교체

```bash
npm uninstall @nestjs/bull bull
npm install @nestjs/bullmq bullmq
```

두 패키지가 동시에 설치되면 타입 충돌이 난다. 완전히 교체한다.

### 모듈 등록 변경

```typescript
// @nestjs/bull
BullModule.forRootAsync({
  useFactory: (config) => ({
    redis: { host: '...', port: 6379 },
  }),
})

// @nestjs/bullmq
BullModule.forRootAsync({
  useFactory: (config) => ({
    connection: { host: '...', port: 6379 },
  }),
})
```

`redis` → `connection`으로 바꾼다.

### 프로세서 클래스 변경

```typescript
// @nestjs/bull
@Processor('email')
export class EmailProcessor {
  @Process('send-welcome')
  async handle(job: Job<WelcomeDto>) { ... }
}

// @nestjs/bullmq
@Processor('email')
export class EmailProcessor extends WorkerHost {
  async process(job: Job<WelcomeDto>): Promise<void> {
    if (job.name === 'send-welcome') {
      // ...
    }
  }
}
```

`WorkerHost` extend를 빠뜨리면 프로세서가 등록은 되는데 실제로 job을 처리하지 않는다. 에러 없이 조용히 넘어가니 주의한다.

### 이벤트 리스너 변경

```typescript
// @nestjs/bull
@OnQueueFailed()
async onFailed(job: Job, err: Error) { }

// @nestjs/bullmq
@OnWorkerEvent('failed')
async onFailed(job: Job, err: Error) { }
```

`@OnQueueFailed()`, `@OnQueueCompleted()` 등이 `@OnWorkerEvent('failed')`, `@OnWorkerEvent('completed')`로 바뀐다.

### Job 타입 교체

```typescript
// @nestjs/bull
import { Job } from 'bull';

// @nestjs/bullmq
import { Job } from 'bullmq';
```

API는 비슷하지만 세부 필드가 다르다. `job.opts`의 구조, `job.attemptsMade` 존재 여부 등을 실제로 확인한다. TypeScript가 잡지 못하는 런타임 필드 차이가 있다.

### defaultJobOptions 위치

bull v3에서는 `registerQueue`의 `defaultJobOptions`에 줄 수 있었다. BullMQ에서는 `forRoot`의 `defaultJobOptions`에 두거나 큐별 worker 옵션으로 준다. 마이그레이션 후 기본 옵션이 실제로 적용되고 있는지 job을 직접 추가해서 확인한다.


## 전환 시점

bull v3는 2023년 이후 사실상 유지보수 모드다. 보안 패치는 나오지만 새 기능은 없다. 현재 운영 중인 시스템이 안정적이라면 전환을 급하게 할 필요는 없다.

전환을 고려할 시점은 세 가지다.

- Redis 버전을 올리면서 Redis Streams 기반 처리를 쓰고 싶을 때
- job 처리량이 늘어서 bull v3의 List/SortedSet 방식이 병목이 될 때
- TypeScript 타입 지원 부족으로 개발 경험이 나빠질 때

운영 중인 큐를 교체할 때는 bull v3와 BullMQ가 Redis에 데이터를 저장하는 구조가 달라서 기존 bull v3 job을 BullMQ 워커가 처리하지 못한다. 배포 전에 큐를 비우거나, bull v3 워커를 잠시 남겨둬서 기존 job을 소화한 뒤 BullMQ로 전환해야 한다.
