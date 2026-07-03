---
title: NestJS 작업 큐 BullMQ 운영기
tags: [nestjs, bullmq, queue, redis, worker, retry, idempotency]
updated: 2026-05-27
---

# NestJS 작업 큐 BullMQ 운영기

이메일 발송, 썸네일 생성, 외부 API 호출 같은 작업을 요청 응답 안에서 처리하면 응답이 느려지고 외부 장애가 그대로 사용자에게 전파된다. 그래서 작업을 큐에 넣고 워커가 비동기로 처리하는 구조로 빼게 된다. Node 진영에서 이걸 가장 많이 쓰는 게 BullMQ고, NestJS는 `@nestjs/bullmq`로 모듈·프로바이더 패턴에 맞게 감싸준다.

문제는 큐를 붙이는 건 30분이면 되는데, 운영에서 터지는 건 전부 그 뒤에 있다는 점이다. 작업이 두 번 실행되고, 재시도가 무한 루프를 돌고, Redis가 재시작하면서 작업이 사라지고, 동시성을 잘못 잡아서 외부 API rate limit에 걸린다. 이 문서는 BullMQ를 NestJS에 붙이면서 실제로 데였던 지점들을 정리한다.

Redis 연결·캐시 쪽은 [Nest_JS_Cache_Module.md](Nest_JS_Cache_Module.md)를, 설정 주입은 [Nest_JS_설정_관리.md](Nest_JS_설정_관리.md)를 참고한다. 본 문서는 큐 자체에 집중한다.


## Bull과 BullMQ, 그리고 패키지 이름

먼저 헷갈리는 지점부터 정리한다. `bull`(구버전)과 `bullmq`(신버전)는 다른 패키지다. BullMQ는 TypeScript로 다시 쓰였고 Redis Streams 기반으로 동작 방식이 바뀌었다. 신규 프로젝트면 BullMQ를 쓴다.

NestJS 래퍼도 두 개로 나뉜다. `@nestjs/bull`은 구버전 Bull용, `@nestjs/bullmq`는 BullMQ용이다. 이름이 비슷해서 `npm install` 할 때 잘못 깔면 데코레이터 시그니처가 안 맞아서 한참 헤맨다.

```bash
npm install @nestjs/bullmq bullmq
```

BullMQ는 Redis 5 이상이 필요하다. 그리고 Redis가 아니라 KeyDB나 일부 매니지드 Redis 호환 서비스를 쓰면 Lua 스크립트 호환성 문제로 작업이 멈추는 경우가 있다. AWS ElastiCache for Redis는 정상 동작하지만 `maxmemory-policy`가 `noeviction`이 아니면 큐 데이터가 evict 돼서 작업이 사라진다. 큐용 Redis는 캐시용과 인스턴스를 분리하는 게 안전하다. 캐시는 evict 돼도 되지만 큐 데이터가 evict 되면 작업이 통째로 증발한다.


## 모듈 등록

루트에서 Redis 연결을 한 번 등록하고, 큐는 기능 모듈에서 등록한다.

```typescript
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { ConfigModule, ConfigService } from '@nestjs/config';

@Module({
  imports: [
    BullModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        connection: {
          host: config.get<string>('REDIS_HOST'),
          port: config.get<number>('REDIS_PORT'),
          password: config.get<string>('REDIS_PASSWORD'),
        },
        defaultJobOptions: {
          attempts: 3,
          backoff: { type: 'exponential', delay: 5000 },
          removeOnComplete: 1000,
          removeOnFail: 5000,
        },
      }),
    }),
  ],
})
export class AppModule {}
```

`defaultJobOptions`를 루트에 한 번 잡아두는 걸 권한다. 작업마다 `attempts`나 `removeOnComplete`를 빼먹으면 기본값으로 떨어지는데, BullMQ 기본값은 `attempts: 1`(재시도 없음)에 완료 작업을 Redis에 영구 보존이다. 이걸 모르면 며칠 뒤 Redis 메모리가 꽉 차서 큐가 멈춘다. `removeOnComplete`를 안 주면 완료된 작업이 계속 쌓인다.

기능 모듈에서는 큐를 등록한다.

```typescript
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { EmailProcessor } from './email.processor';
import { EmailService } from './email.service';

@Module({
  imports: [
    BullModule.registerQueue({
      name: 'email',
    }),
  ],
  providers: [EmailProcessor, EmailService],
})
export class EmailModule {}
```

큐 이름(`'email'`)은 문자열이라 오타가 나도 컴파일이 통과한다. 작업을 등록하는 쪽과 처리하는 쪽이 다른 이름을 쓰면 작업은 큐에 들어가는데 아무도 안 꺼내가서 영원히 대기한다. 큐 이름은 상수로 빼서 양쪽에서 같이 쓴다.

```typescript
export const QUEUE_EMAIL = 'email';
```


## 작업 등록 — Producer

서비스에서 큐에 작업을 넣는다. `@InjectQueue`로 큐를 주입받고 `add`로 등록한다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { QUEUE_EMAIL } from './constants';

@Injectable()
export class EmailService {
  constructor(@InjectQueue(QUEUE_EMAIL) private readonly emailQueue: Queue) {}

  async sendWelcome(userId: number, email: string) {
    await this.emailQueue.add(
      'welcome', // 작업 이름
      { userId, email }, // 페이로드
      {
        attempts: 5,
        backoff: { type: 'exponential', delay: 3000 },
        removeOnComplete: true,
      },
    );
  }
}
```

페이로드는 JSON으로 직렬화돼서 Redis에 저장된다. 여기서 첫 번째 함정이 나온다. 페이로드에 엔티티 객체나 Date, Buffer를 그대로 넣으면 직렬화·역직렬화 과정에서 형이 바뀐다. Date는 문자열로 돌아오고, 클래스 인스턴스는 평범한 객체가 된다. 워커에서 `job.data.createdAt.getTime()`을 호출하면 런타임 에러가 난다. 페이로드에는 원시 타입과 plain object만 넣고, 큰 데이터는 ID만 넣어서 워커가 DB에서 다시 조회하게 한다.

페이로드를 작게 유지하는 또 다른 이유는 Redis 메모리다. 작업 하나에 수백 KB짜리 객체를 통째로 넣으면 큐가 밀릴 때 Redis 메모리가 빠르게 찬다. "ID만 넣고 워커가 조회"는 거의 항상 맞는 선택이다.


## 작업 옵션

`add`의 세 번째 인자가 작업 옵션이다. 실무에서 자주 쓰는 것들을 정리한다.

```typescript
await this.queue.add('task', payload, {
  attempts: 5,                              // 최대 시도 횟수(최초 시도 포함)
  backoff: { type: 'exponential', delay: 3000 }, // 재시도 간격
  delay: 60_000,                            // 60초 뒤에 실행
  removeOnComplete: 100,                    // 완료 작업 100개만 보존
  removeOnFail: 1000,                       // 실패 작업 1000개만 보존
  priority: 1,                              // 숫자가 작을수록 우선
  jobId: `welcome:${userId}`,               // 멱등성 키
});
```

`attempts`는 최초 시도를 포함한다. `attempts: 3`이면 처음 한 번 + 재시도 두 번이다. `attempts: 1`은 재시도 없음이다. 이걸 "재시도 3번"으로 착각하면 실제로는 4번 돌아간다.

`backoff`는 재시도 간격이다. `fixed`는 매번 같은 간격, `exponential`은 `delay * 2^(시도횟수-1)`로 늘어난다. 외부 API가 일시적으로 죽었을 때 `fixed`로 짧게 잡으면 죽은 API를 계속 두드려서 복구를 방해한다. 외부 의존이 있는 작업은 `exponential`을 쓴다.

`delay`는 지정한 ms 뒤에 실행한다. "가입 후 1시간 뒤 안내 메일" 같은 지연 작업에 쓴다. 다만 `delay`로 며칠 단위 예약을 하면 안 된다. delay 작업은 Redis에 계속 떠 있어서 메모리를 먹고, 그 사이 Redis가 한 번 날아가면 예약이 통째로 사라진다. 하루 이상 지연은 DB에 예약 레코드를 남기고 크론이 시점에 맞춰 큐에 넣는 방식이 안전하다.

`removeOnComplete`에 숫자를 주면 최근 N개만 남기고 자동 정리한다. `true`면 완료 즉시 삭제다. 디버깅을 위해 최근 몇 개는 남겨두는 게 좋아서 숫자를 주는 편이다. `removeOnFail`도 마찬가지인데, 실패 작업은 원인 분석에 필요하므로 완료보다 넉넉하게 남긴다.


## Processor — Consumer

작업을 처리하는 쪽은 `@Processor` 데코레이터를 붙인 클래스가 `WorkerHost`를 상속하고 `process` 메서드를 구현한다. 구버전 Bull의 `@Process()` 메서드 데코레이터 방식과 다르다. BullMQ 래퍼는 `WorkerHost` 상속이 기본이다.

```typescript
import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';
import { Logger } from '@nestjs/common';
import { QUEUE_EMAIL } from './constants';

@Processor(QUEUE_EMAIL)
export class EmailProcessor extends WorkerHost {
  private readonly logger = new Logger(EmailProcessor.name);

  async process(job: Job): Promise<void> {
    switch (job.name) {
      case 'welcome':
        await this.handleWelcome(job);
        break;
      case 'reset-password':
        await this.handleReset(job);
        break;
      default:
        throw new Error(`알 수 없는 작업: ${job.name}`);
    }
  }

  private async handleWelcome(job: Job) {
    const { email } = job.data;
    this.logger.log(`환영 메일 발송: ${email}`);
    // 실제 발송 로직
  }

  private async handleReset(job: Job) {
    // ...
  }
}
```

한 큐에 여러 작업 이름을 넣으면 `process` 안에서 `job.name`으로 분기한다. 작업 종류가 많아지면 switch가 길어지는데, 이때 큐를 쪼갤지 고민하게 된다. 처리 특성이 다르면(동시성, 우선순위, 재시도 정책) 큐를 분리하고, 비슷하면 한 큐에서 분기하는 게 운영이 단순하다.

`process`에서 던진 예외는 작업 실패로 기록되고 재시도 대상이 된다. 정상 종료(반환)는 성공이다. 여기서 자주 하는 실수가 try-catch로 모든 예외를 삼키고 정상 반환하는 것이다. 그러면 실패한 작업이 성공으로 기록돼서 재시도가 안 된다. 재시도가 필요한 에러는 다시 던지고, 재시도해도 의미 없는 에러(잘못된 페이로드 등)만 잡아서 처리한다.


## 동시성 설정

기본 동시성은 1이다. 워커가 작업을 하나씩 순차 처리한다. 처리량을 늘리려면 `concurrency`를 올린다.

```typescript
@Processor(QUEUE_EMAIL, { concurrency: 10 })
export class EmailProcessor extends WorkerHost {
  // ...
}
```

`concurrency: 10`이면 워커 한 프로세스가 작업 10개를 동시에 처리한다. 여기서 두 가지를 헷갈리면 안 된다.

첫째, 이건 프로세스 단위 동시성이다. 워커 프로세스를 3개 띄우고 각각 `concurrency: 10`이면 전체 동시 처리는 30이다. 외부 API rate limit을 맞출 때는 인스턴스 수까지 곱해서 계산해야 한다. 단일 프로세스에서 10이라고 안심했다가 오토스케일링으로 인스턴스가 늘면서 외부 API에 차단당하는 경우가 있다.

둘째, 동시성을 높인다고 항상 빨라지는 게 아니다. 작업이 DB나 외부 API에 의존하면 그쪽이 병목이라 워커 동시성만 올리면 커넥션 풀이 고갈되거나 외부가 죽는다. CPU 바운드 작업(이미지 처리 등)은 Node 단일 스레드라 동시성을 올려도 의미가 없고 오히려 이벤트 루프가 막힌다. 이런 작업은 프로세스를 여러 개 띄우거나 BullMQ의 sandboxed processor(별도 프로세스에서 실행)를 쓴다.

전체 큐 차원의 처리율 제한이 필요하면 `limiter`를 쓴다.

```typescript
@Processor(QUEUE_EMAIL, {
  concurrency: 10,
  limiter: { max: 100, duration: 60_000 }, // 분당 최대 100건
})
export class EmailProcessor extends WorkerHost {}
```

외부 메일 API가 "분당 100건"으로 제한돼 있으면 `limiter`로 큐 전체의 속도를 맞춘다. `limiter`는 같은 Redis를 보는 모든 워커에 걸쳐 적용되므로 인스턴스가 늘어도 전체 합이 제한 안에 머문다. 이게 인스턴스별로 계산해야 하는 `concurrency`와 다른 점이다.


## 실패 처리와 재시도

작업이 실패하면 BullMQ가 `attempts`와 `backoff` 설정에 따라 자동 재시도한다. 모든 재시도를 소진하면 작업이 failed 상태로 넘어간다. 이때 알아둬야 할 게 몇 가지 있다.

재시도 횟수는 `job.attemptsMade`로 확인한다. 마지막 시도인지 알고 싶으면 `job.attemptsMade`와 옵션의 `attempts`를 비교한다. 마지막 시도에서 실패하면 알림을 보내는 식으로 쓴다.

```typescript
async process(job: Job): Promise<void> {
  try {
    await this.doWork(job.data);
  } catch (err) {
    const isLastAttempt = job.attemptsMade + 1 >= (job.opts.attempts ?? 1);
    if (isLastAttempt) {
      this.logger.error(`최종 실패: ${job.id}`, err.stack);
      // 데드레터 큐로 보내거나 알림
    }
    throw err; // 재시도를 위해 다시 던진다
  }
}
```

재시도해도 절대 성공할 수 없는 에러는 재시도하면 안 된다. 페이로드가 잘못됐거나 대상 리소스가 삭제된 경우가 그렇다. 이런 작업을 `attempts: 5`로 돌리면 같은 에러로 5번 실패하면서 backoff 시간만 잡아먹는다. BullMQ는 `UnrecoverableError`를 제공한다. 이걸 던지면 남은 재시도를 건너뛰고 즉시 failed로 보낸다.

```typescript
import { UnrecoverableError } from 'bullmq';

async process(job: Job) {
  const user = await this.userRepo.findById(job.data.userId);
  if (!user) {
    throw new UnrecoverableError(`사용자 없음: ${job.data.userId}`);
  }
  // ...
}
```

최종 실패한 작업은 `removeOnFail` 설정 안에서 Redis에 남는다. 이걸 수동으로 다시 돌리려면 failed 작업을 조회해서 `retry()`를 호출한다. 운영 중 외부 API가 몇 시간 죽었다가 살아났을 때, 그 사이 쌓인 failed 작업을 한꺼번에 재처리하는 식으로 쓴다.

```typescript
const failed = await this.queue.getFailed();
for (const job of failed) {
  await job.retry();
}
```

데드레터 큐 패턴을 직접 만들 수도 있다. 최종 실패한 작업을 별도 큐(`email-dead`)에 옮겨놓고, 나중에 사람이 확인하고 처리하는 구조다. BullMQ에 내장된 DLQ는 없어서 실패 이벤트 핸들러에서 직접 옮긴다.


## 반복 작업

크론 같은 주기 작업은 `repeat` 옵션으로 만든다. cron 표현식이나 밀리초 간격을 준다.

```typescript
await this.queue.add(
  'cleanup',
  {},
  {
    repeat: { pattern: '0 3 * * *' }, // 매일 새벽 3시
    removeOnComplete: true,
  },
);
```

반복 작업에서 가장 많이 데이는 게 중복 등록이다. 위 코드를 앱 부트스트랩에서 호출하면, 배포할 때마다 같은 반복 작업이 새로 등록된다. BullMQ는 repeat 키가 같으면 중복 등록을 막아주긴 하지만, cron 패턴이나 옵션이 조금만 달라도 다른 키로 인식해서 반복 작업이 두 개가 된다. 그러면 새벽 3시 정리 작업이 두 번 돈다.

안전한 방법은 등록 전에 기존 반복 작업을 정리하는 것이다.

```typescript
import { OnModuleInit } from '@nestjs/common';

@Injectable()
export class CleanupScheduler implements OnModuleInit {
  constructor(@InjectQueue(QUEUE_EMAIL) private readonly queue: Queue) {}

  async onModuleInit() {
    // 기존 반복 작업 제거
    const repeatables = await this.queue.getRepeatableJobs();
    for (const job of repeatables) {
      await this.queue.removeRepeatableByKey(job.key);
    }
    // 다시 등록
    await this.queue.add('cleanup', {}, { repeat: { pattern: '0 3 * * *' } });
  }
}
```

또 하나, 다중 인스턴스 환경에서 모든 인스턴스가 부트스트랩 때 반복 작업을 등록하려 한다. 같은 Redis를 보므로 결과적으로는 하나만 남지만, 등록·제거가 동시에 일어나면 경합이 생긴다. 반복 작업 등록은 리더 인스턴스 하나만 하게 하거나, 위처럼 제거 후 재등록으로 멱등하게 만든다.

반복 작업의 실제 실행 시점은 정확하지 않을 수 있다. 워커가 모두 바쁘면 트리거된 작업이 큐에서 대기한다. "매분 실행"인데 처리에 1분 넘게 걸리면 작업이 밀린다. 반복 주기보다 처리 시간이 짧은지 확인한다.


## 큐 이벤트 리스닝

작업의 상태 변화를 감지하려면 이벤트를 듣는다. NestJS 래퍼는 `WorkerHost`를 상속한 프로세서 안에서 `@OnWorkerEvent` 데코레이터로 워커 이벤트를 받는다.

```typescript
import { Processor, WorkerHost, OnWorkerEvent } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor(QUEUE_EMAIL)
export class EmailProcessor extends WorkerHost {
  async process(job: Job) {
    // ...
  }

  @OnWorkerEvent('completed')
  onCompleted(job: Job) {
    this.logger.log(`완료: ${job.id}`);
  }

  @OnWorkerEvent('failed')
  onFailed(job: Job, err: Error) {
    this.logger.error(`실패: ${job.id}, ${err.message}`);
  }

  @OnWorkerEvent('active')
  onActive(job: Job) {
    this.logger.debug(`시작: ${job.id}`);
  }
}
```

워커 이벤트(`@OnWorkerEvent`)와 큐 이벤트(`QueueEvents`)는 다르다. 워커 이벤트는 그 워커 프로세스가 처리한 작업에 대해서만 발생한다. 다른 프로세스에서 처리한 작업의 완료는 못 듣는다. 모든 인스턴스에서 발생한 이벤트를 한곳에서 모으려면 `QueueEvents`를 별도로 구독한다. 이건 Redis Streams를 읽어서 전체 이벤트를 받는다.

```typescript
import { QueueEventsListener, QueueEventsHost, OnQueueEvent } from '@nestjs/bullmq';

@QueueEventsListener(QUEUE_EMAIL)
export class EmailQueueEvents extends QueueEventsHost {
  @OnQueueEvent('completed')
  onCompleted({ jobId }: { jobId: string }) {
    // 어느 인스턴스가 처리했든 여기서 받는다
  }

  @OnQueueEvent('failed')
  onFailed({ jobId, failedReason }: { jobId: string; failedReason: string }) {
    // 실패 집계, 알림
  }
}
```

`QueueEvents`의 핸들러는 작업 객체 전체가 아니라 `jobId`만 받는다. 페이로드가 필요하면 `Job.fromId`로 다시 조회한다. 이벤트 핸들러에서 무거운 작업을 하면 안 된다. 이벤트는 빠르게 흘러가고, 핸들러가 느리면 이벤트가 밀린다. 알림이나 집계 같은 후처리는 이벤트 핸들러에서 또 다른 큐에 작업을 넣는 식으로 분리한다.


## 멱등성과 중복 실행 방지

큐 시스템에서 가장 중요하면서 가장 자주 사고가 나는 부분이다. BullMQ는 "최소 한 번(at-least-once)" 전달을 보장한다. 정확히 한 번이 아니다. 같은 작업이 두 번 실행될 수 있다는 뜻이다.

두 번 실행되는 경로는 여러 가지다. 워커가 작업을 처리하다가 완료 직전에 죽으면, 작업이 stalled로 판정돼서 다른 워커가 다시 가져간다. 이미 메일은 나갔는데 작업은 미완료로 남아서 재시도되면 메일이 두 번 나간다. 네트워크 문제로 producer가 `add`를 재시도하면 같은 작업이 두 번 들어간다.

해결의 출발점은 `jobId`다. `add`에 `jobId`를 명시하면 같은 ID의 작업은 큐에 한 번만 들어간다.

```typescript
await this.queue.add(
  'welcome',
  { userId },
  { jobId: `welcome:${userId}` }, // 같은 유저는 한 번만
);
```

같은 `jobId`로 다시 `add`하면 BullMQ가 무시한다. producer 쪽 중복 등록은 이걸로 막힌다. 다만 주의할 점이 있다. 이미 완료돼서 `removeOnComplete`로 삭제된 작업과 같은 `jobId`를 다시 add하면, Redis에 그 ID가 없으니 새 작업으로 들어간다. 즉 `jobId`는 "현재 큐에 살아있는 작업"의 중복만 막는다. 영구적인 중복 방지가 아니다.

그래서 producer 쪽 `jobId`만으로는 부족하고, consumer(워커) 쪽에서 멱등성을 한 번 더 보장해야 한다. 핵심은 작업 처리 결과를 어딘가에 기록하고, 처리 전에 이미 처리됐는지 확인하는 것이다.

```typescript
async process(job: Job) {
  const { userId } = job.data;
  const idemKey = `welcome-sent:${userId}`;

  // 이미 처리됐으면 건너뛴다
  const already = await this.redis.get(idemKey);
  if (already) {
    this.logger.log(`이미 처리됨, 건너뜀: ${userId}`);
    return;
  }

  await this.mailer.sendWelcome(userId);

  // 처리 완료 기록 (TTL은 재시도 윈도우보다 길게)
  await this.redis.set(idemKey, '1', 'EX', 86400);
}
```

여기서도 함정이 있다. 메일 발송과 멱등성 키 기록 사이에 워커가 죽으면, 메일은 나갔는데 키는 없는 상태가 된다. 재시도하면 또 나간다. 완벽한 정확히 한 번은 메일 발송 자체가 멱등하지 않는 한 불가능하다. 그래서 외부 작업이 멱등성을 지원하는지부터 본다. 결제 API라면 idempotency key를 그쪽에 넘기고, 그게 안 되면 "처리 시작"을 먼저 기록하고 작업하는 식으로 두 번 실행 가능성을 줄이되, 완전히는 못 막는다는 걸 전제로 설계한다.

DB 작업이라면 멱등성을 더 깔끔하게 만들 수 있다. 유니크 제약을 거는 것이다. "포인트 적립" 작업이라면 적립 이력 테이블에 `(userId, eventId)` 유니크 인덱스를 걸고, 중복 삽입 시 에러를 무시한다. 이러면 작업이 몇 번 실행되든 적립은 한 번만 된다. 멱등성 키를 Redis에 따로 두는 것보다 DB 제약으로 강제하는 게 더 안전하다. Redis 키는 evict 되거나 TTL로 사라질 수 있지만 DB 제약은 안 사라진다.

stalled 작업 문제는 `lockDuration` 설정과 관련 있다. 워커는 작업을 잡으면 락을 걸고 주기적으로 갱신한다. 작업이 `lockDuration`(기본 30초)보다 오래 걸리면서 락 갱신이 안 되면 stalled로 판정돼 다른 워커가 가져간다. 처리에 30초 넘게 걸리는 작업이면 `lockDuration`을 처리 시간보다 길게 잡아야 한다. 안 그러면 멀쩡히 처리 중인 작업을 다른 워커가 중복 실행한다. CPU 바운드 작업으로 이벤트 루프가 막혀서 락 갱신이 안 되는 경우도 같은 증상이 나온다.


## 그레이스풀 셧다운

배포할 때 워커를 그냥 죽이면 처리 중이던 작업이 stalled로 남아서 중복 실행 위험이 커진다. NestJS의 셧다운 훅을 켜고, BullModule이 워커를 깔끔하게 닫게 한다.

```typescript
// main.ts
const app = await NestFactory.create(AppModule);
app.enableShutdownHooks();
await app.listen(3000);
```

`enableShutdownHooks`를 켜면 SIGTERM을 받았을 때 BullMQ 워커가 진행 중인 작업을 마저 끝내고 새 작업을 안 받은 뒤 종료한다. 이게 없으면 `kill` 즉시 프로세스가 죽어서 작업이 중간에 끊긴다. 쿠버네티스 환경이면 `terminationGracePeriodSeconds`를 가장 긴 작업 처리 시간보다 길게 잡아야 셧다운이 작업을 마칠 시간을 확보한다. 짧으면 그레이스풀 셧다운 도중에 SIGKILL이 날아와서 결국 작업이 끊긴다.


## 모니터링

큐 상태는 눈에 안 보이면 곧 쌓인다. 최소한 대기(waiting)·활성(active)·실패(failed) 작업 수는 메트릭으로 뽑아야 한다.

```typescript
const counts = await this.queue.getJobCounts(
  'waiting', 'active', 'completed', 'failed', 'delayed',
);
// { waiting: 0, active: 3, failed: 12, ... }
```

waiting이 계속 늘면 워커가 처리량을 못 따라가는 것이다. 동시성을 올리거나 워커를 늘린다. failed가 갑자기 튀면 외부 의존 장애일 가능성이 높다. delayed가 비정상적으로 많으면 어딘가에서 `delay`나 backoff로 작업이 계속 미뤄지고 있다는 신호다.

대시보드가 필요하면 Bull Board를 붙인다. 큐 상태를 웹 UI로 보여주고 실패 작업 재시도를 버튼으로 할 수 있다. 운영자가 직접 failed 작업을 확인하고 재처리할 수 있어서 사고 대응이 빨라진다. 다만 이 UI는 큐 데이터를 그대로 노출하므로 인증 뒤에 둔다. 페이로드에 민감 정보가 들어있으면 UI에서 그대로 보인다.


## 흔히 마주치는 함정 정리

작업이 큐에 들어가는데 처리가 안 된다. producer의 큐 이름과 `@Processor`의 큐 이름이 다른 경우가 가장 흔하다. 큐 이름 상수를 한곳에서 관리한다. 그 다음으로 워커 프로세스가 아예 안 떠 있는 경우다. 웹 서버와 워커를 다른 프로세스로 분리 배포했는데 워커 배포를 빠뜨렸을 때다.

`job.data`의 Date가 문자열이다. JSON 직렬화의 당연한 결과다. 워커에서 `new Date(job.data.createdAt)`로 다시 만들거나, 페이로드에 timestamp(숫자)로 넣는다.

재시도가 안 된다. `process`에서 try-catch로 에러를 삼키고 정상 반환하면 성공으로 기록된다. 재시도가 필요하면 에러를 다시 던진다.

같은 작업이 두 번 실행된다. at-least-once의 정상 동작이다. `jobId`로 producer 중복을 막고, consumer에서 멱등성을 보장한다. DB 유니크 제약이 가장 확실하다.

Redis 메모리가 계속 찬다. `removeOnComplete`·`removeOnFail`을 안 줬거나, 페이로드가 너무 크거나, delay 작업이 쌓이고 있다. completed 작업이 무한히 남는 게 가장 흔한 원인이다.

배포 후 반복 작업이 두 번 돈다. 부트스트랩 때 repeat 작업을 옵션 바꿔가며 중복 등록한 것이다. 등록 전에 기존 repeatable을 정리한다.

긴 작업이 자꾸 중복 실행된다. 처리 시간이 `lockDuration`을 넘겨서 stalled 판정이 난 것이다. `lockDuration`을 처리 시간보다 길게 잡거나, CPU 바운드면 sandboxed processor로 빼서 이벤트 루프 차단을 푼다.


## 마무리

BullMQ를 붙이는 것 자체는 쉽다. 어려운 건 "작업이 정확히 한 번 실행된다"는 보장이 애초에 없다는 걸 받아들이고 설계하는 것이다. at-least-once를 전제로, 모든 작업을 두 번 실행돼도 결과가 같게 만드는 게 핵심이다. 멱등성은 DB 유니크 제약으로 강제하는 게 Redis 키보다 안전하다. `attempts`·`backoff`·`removeOnComplete`는 루트 기본값으로 잡고 시작하고, 동시성은 외부 의존의 한계를 보고 정한다. 큐 길이와 실패 수 메트릭은 처음부터 깔아둔다. 큐는 보이지 않으면 조용히 밀리다가 한꺼번에 터진다.
