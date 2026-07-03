---
title: NestJS Schedule Module 심화
tags:
  - NestJS
  - Schedule
  - Cron
  - SchedulerRegistry
  - BullMQ
  - Distributed Lock
updated: 2026-06-09
---

# NestJS Schedule Module

주기적으로 돌아야 하는 작업이 생기면 가장 먼저 떠오르는 게 cron이다. 리눅스 crontab을 그대로 쓸 수도 있지만, 애플리케이션 코드 안에서 DB 세션이나 DI 컨테이너를 그대로 쓰면서 스케줄을 돌리고 싶을 때 `@nestjs/schedule`이 답이 된다. node-cron을 감싸서 데코레이터 기반으로 노출한 패키지인데, 처음에는 단순해 보여도 실제 운영에 올리면 timezone, 분산 환경 중복 실행, 동적 스케줄 변경 같은 문제가 줄줄이 따라온다.

## 설치와 기본 구조

```bash
npm install @nestjs/schedule
```

`ScheduleModule.forRoot()`를 루트 모듈에 한 번 import 해야 한다. 이 한 줄이 빠지면 데코레이터를 달아도 아무 작업도 실행되지 않는다. 처음 NestJS 스케줄을 쓰는 사람이 가장 많이 빠지는 함정이다.

```ts
// app.module.ts
import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';
import { TasksService } from './tasks/tasks.service';

@Module({
  imports: [ScheduleModule.forRoot()],
  providers: [TasksService],
})
export class AppModule {}
```

내부적으로 `SchedulerRegistry`와 `SchedulerOrchestrator`라는 두 클래스가 핵심이다. `forRoot()`가 호출되면 컨테이너가 `OnApplicationBootstrap` 시점에 등록된 데코레이터를 스캔해서 cron/interval/timeout 큐에 넣고, `Reflector`로 메타데이터를 읽어 node-cron 인스턴스를 만든다. 그래서 부팅 직후가 아니라 `onApplicationBootstrap` 이후에야 첫 스케줄이 동작한다.

## @Cron, @Interval, @Timeout

세 가지 데코레이터의 용도가 다르다.

### @Cron

cron expression이나 `CronExpression` enum을 받는다. expression은 5필드(분-시-일-월-요일)와 6필드(초-분-시-일-월-요일) 두 형식을 모두 지원하는데, 디폴트가 6필드라는 점을 모르면 매시 0분이 아니라 매분 0초마다 돌게 된다.

```ts
import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';

@Injectable()
export class TasksService {
  private readonly logger = new Logger(TasksService.name);

  // 매일 새벽 3시
  @Cron('0 0 3 * * *', {
    name: 'daily-cleanup',
    timeZone: 'Asia/Seoul',
  })
  async cleanupExpiredSessions() {
    this.logger.log('만료된 세션 정리 시작');
    // ...
  }

  // enum 형태
  @Cron(CronExpression.EVERY_30_MINUTES)
  async syncExternalData() {
    // 30분마다 외부 API 동기화
  }
}
```

`name` 옵션은 나중에 `SchedulerRegistry`로 꺼낼 때 키 역할을 한다. 안 주면 자동 생성 ID가 들어가서 동적 제어가 사실상 불가능하다. 운영 환경에서 켜고 끌 가능성이 조금이라도 있는 작업은 무조건 `name`을 박아둬야 한다.

### @Interval

밀리초 단위로 반복한다. 첫 실행은 ms가 지나야 일어난다. 부팅 직후 바로 한 번 돌려야 하면 `onApplicationBootstrap`에서 명시적으로 호출하고 그 다음부터 interval에 맡기는 식으로 처리한다.

```ts
@Interval('health-ping', 10_000)
checkUpstream() {
  // 10초마다 업스트림 헬스체크
}
```

interval은 함수가 비동기로 오래 걸려도 다음 틱을 기다리지 않는다. 즉 10초 interval에서 작업이 12초 걸리면 두 인스턴스가 겹쳐 돈다. 동시에 돌면 안 되는 작업이면 내부 락이나 `if (isRunning) return;` 가드가 필요하다.

### @Timeout

지정된 ms 뒤 한 번만 실행된다. 부팅 후 30초 뒤 캐시 워밍업, 1분 뒤 외부 시스템 초기 동기화 같은 경우에 쓴다.

```ts
@Timeout('warm-cache', 30_000)
async warmCache() {
  await this.cache.preload();
}
```

`SchedulerRegistry.deleteTimeout('warm-cache')`로 삭제 가능하지만 이미 실행된 뒤에는 의미가 없다.

## Cron Expression 패턴

`@nestjs/schedule`은 내부적으로 `cron` 라이브러리를 쓴다. node-cron이 아니라 [kelektiv/node-cron](https://github.com/kelektiv/node-cron) 쪽이다. 6필드 표기가 디폴트라는 점이 표준 crontab과 다르다.

| 필드 | 범위 |
|------|------|
| 초 (옵션) | 0-59 |
| 분 | 0-59 |
| 시 | 0-23 |
| 일 | 1-31 |
| 월 | 1-12 또는 JAN-DEC |
| 요일 | 0-7 (0,7=일) 또는 SUN-SAT |

실무에서 자주 헷갈리는 케이스 몇 가지.

```ts
'0 */15 * * * *'   // 매시 0,15,30,45분 0초
'*/15 * * * * *'   // 매 15초마다 (의도와 다를 가능성 높음)
'0 30 9 * * 1-5'   // 평일 오전 9:30
'0 0 0 1 * *'      // 매월 1일 자정
'0 0 0 L * *'      // 매월 마지막 날 자정 (L 지원)
```

별표를 잘못 찍어서 매 15초마다 무거운 작업이 돌고 DB가 죽는 사고가 흔하다. 배포 전에 [crontab.guru](https://crontab.guru) 같은 도구로 expression을 한 번 더 확인하는 습관이 필요하다. 단, crontab.guru는 5필드 기준이라 첫 필드 의미가 다르다는 점을 잊으면 안 된다.

## Timezone 처리

서버가 UTC인데 cron expression은 한국 시간 기준으로 적어놓으면 9시간 어긋난다. AWS ECS·EKS·Lambda 같은 환경은 보통 UTC가 디폴트라 이 문제가 자주 터진다.

```ts
@Cron('0 0 9 * * *', { timeZone: 'Asia/Seoul' })
async sendDailyReport() {
  // 서버 TZ와 무관하게 한국 시간 09:00 실행
}
```

`timeZone`은 IANA timezone 문자열을 받는다. `Asia/Seoul`, `America/New_York` 같은 식이다. 서머타임 적용 지역은 DST 전환 시점에 한 번 건너뛰거나 두 번 실행되는 경우가 생기는데, 이건 cron 자체의 한계라 비즈니스 요구사항에 따라 처리 방식을 정해야 한다. 결제 정산처럼 정확히 한 번 돌아야 하면 UTC로 작성하고 timezone 옵션을 빼는 게 안전하다.

서버 시간을 `process.env.TZ`로 강제 변경하는 방법도 있지만, 다른 코드(로그 타임스탬프, DB 시간 파라미터)에 영향을 주기 때문에 권장하지 않는다. cron 데코레이터에 timezone을 명시하는 게 부작용이 없다.

## SchedulerRegistry로 동적 제어

데코레이터로 박아둔 스케줄은 정적이다. 운영 중에 관리자 페이지에서 켜고 끄거나, 사용자가 등록한 알림 시각에 맞춰 동적으로 cron job을 추가해야 할 때 `SchedulerRegistry`를 직접 다룬다.

```ts
import { Injectable } from '@nestjs/common';
import { SchedulerRegistry } from '@nestjs/schedule';
import { CronJob } from 'cron';

@Injectable()
export class DynamicCronService {
  constructor(private readonly registry: SchedulerRegistry) {}

  addNotification(userId: string, hhmm: string) {
    const [hh, mm] = hhmm.split(':');
    const name = `notify:${userId}`;

    if (this.registry.doesExist('cron', name)) {
      this.registry.deleteCronJob(name);
    }

    const job = new CronJob(`0 ${mm} ${hh} * * *`, () => {
      this.sendNotification(userId);
    }, null, false, 'Asia/Seoul');

    this.registry.addCronJob(name, job);
    job.start();
  }

  removeNotification(userId: string) {
    const name = `notify:${userId}`;
    if (this.registry.doesExist('cron', name)) {
      this.registry.deleteCronJob(name);
    }
  }

  listJobs() {
    const jobs = this.registry.getCronJobs();
    return [...jobs.entries()].map(([name, job]) => ({
      name,
      next: job.nextDate().toISO(),
      running: job.running,
    }));
  }

  private async sendNotification(userId: string) {
    // ...
  }
}
```

`CronJob` 생성자의 네 번째 인자가 `start` 플래그인데, `addCronJob` 전에 `true`로 만들면 등록과 동시에 두 번 시작되거나 등록 안 된 채로 돌아갈 수 있어서 일부러 `false`로 만든 뒤 `addCronJob` 후 `start()`를 호출하는 패턴을 쓴다.

동적 스케줄의 단점은 프로세스가 죽으면 다 사라진다는 점이다. 사용자별 알림 같은 영구 데이터는 DB에 따로 저장하고, 부팅 시 `onApplicationBootstrap`에서 DB를 읽어 재등록해야 한다.

```ts
async onApplicationBootstrap() {
  const rules = await this.notificationRepo.find({ where: { enabled: true } });
  for (const rule of rules) {
    this.addNotification(rule.userId, rule.time);
  }
}
```

## 분산 환경에서 중복 실행 문제

가장 골치 아픈 문제다. ECS task가 3개 떠 있으면 cron이 3번 돌고, DB 정산 작업이 세 번 실행되어 데이터가 깨진다. NestJS 스케줄러는 단일 프로세스 안에서만 동작하기 때문에 멀티 인스턴스에서 누가 책임지고 돌릴지 코드 차원에서 정해야 한다.

해결 방법은 크게 세 가지다.

### 1. 단일 인스턴스 지정

가장 단순한 방법. 스케줄 전용 컨테이너를 1개만 띄우거나, 환경변수로 leader 지정.

```ts
@Cron('0 0 3 * * *')
async dailyJob() {
  if (process.env.ROLE !== 'scheduler') return;
  // ...
}
```

깔끔하지만 leader가 죽으면 작업이 안 돈다. failover까지 고려하려면 락 기반으로 가야 한다.

### 2. Redis 분산 락

가장 보편적인 방식. 작업 시작 전 `SETNX`로 락을 잡고, TTL을 작업 예상 시간보다 길게 잡는다.

```ts
import { Injectable, Inject } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import Redis from 'ioredis';

@Injectable()
export class SettlementService {
  constructor(@Inject('REDIS') private readonly redis: Redis) {}

  @Cron('0 0 3 * * *')
  async settle() {
    const lockKey = 'lock:settlement:daily';
    const lockId = `${process.env.HOSTNAME}-${process.pid}`;
    const ttlMs = 10 * 60 * 1000; // 10분

    const acquired = await this.redis.set(lockKey, lockId, 'PX', ttlMs, 'NX');
    if (!acquired) return;

    try {
      await this.runSettlement();
    } finally {
      // 자기가 잡은 락만 해제 (Lua script로 atomic하게)
      await this.redis.eval(
        `if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end`,
        1,
        lockKey,
        lockId,
      );
    }
  }
}
```

락 해제를 단순 `DEL`로 하면 TTL이 만료된 뒤 다른 인스턴스가 잡은 락을 내가 풀어버리는 사고가 생긴다. 위 Lua 스크립트처럼 `lockId` 일치 확인 후 삭제하는 게 정석이다. Redlock 알고리즘이 필요할 정도로 엄격한 일관성이 요구되면 [redlock](https://github.com/mike-marcacci/node-redlock) 같은 라이브러리를 쓰는 게 낫다.

### 3. DB 락 (Postgres advisory lock)

Redis가 없는 환경이면 Postgres advisory lock으로도 같은 효과를 낼 수 있다.

```ts
@Cron('0 0 3 * * *')
async settle() {
  const lockId = 91827364; // 작업별 고유 정수
  const result = await this.dataSource.query(
    'SELECT pg_try_advisory_lock($1) AS acquired',
    [lockId],
  );
  if (!result[0].acquired) return;

  try {
    await this.runSettlement();
  } finally {
    await this.dataSource.query('SELECT pg_advisory_unlock($1)', [lockId]);
  }
}
```

advisory lock은 트랜잭션 단위(`pg_try_advisory_xact_lock`)와 세션 단위가 따로 있다. 세션 단위 락은 명시적으로 unlock 해주거나 커넥션이 끊겨야 풀린다. 커넥션 풀에서 빌려온 커넥션을 락 잡고 반환하면 다른 쿼리가 그 커넥션을 빌릴 때 락이 따라가는 사고가 생기니, 단일 트랜잭션 안에서 처리하는 advisory_xact_lock이 안전하다.

### 락 vs 큐

락 기반은 "어차피 한 인스턴스만 돌면 된다"는 정책이고, 큐 기반은 "여러 worker가 나눠서 처리한다"는 정책이다. 정산처럼 한 번만 돌아야 하는 작업은 락이 맞지만, 1000개 이메일을 보내야 하는 작업은 큐로 흘려서 worker N개가 병렬로 처리하는 게 맞다.

## 작업 큐(BullMQ) 선택 기준

`@nestjs/schedule`로 모든 걸 처리하려고 하면 결국 한계를 만난다. 다음 상황이면 BullMQ로 넘어가야 한다.

| 상황 | Schedule | BullMQ |
|------|----------|--------|
| 단순 주기 실행 (예: 매일 새벽 정리) | 적합 | 과한 인프라 |
| 분산 환경 중복 실행 방지 | 락 직접 구현 필요 | 자체적으로 단일 처리 보장 |
| 실패 시 재시도 | 직접 구현 | exponential backoff 내장 |
| 작업 진행 상태 추적 | 불가능 | progress, completed, failed 이벤트 |
| 작업 우선순위, rate limit | 불가능 | priority, limiter 내장 |
| 작업 결과 보관, 모니터링 | 직접 구현 | Bull Board로 UI 제공 |
| 지연 실행 (예: 10분 뒤 알림) | @Timeout으로 단발성만 | delay 옵션으로 영구 저장 |
| 부하 분산 (worker N개) | 불가 | concurrency, worker scale-out |

실무 패턴은 보통 두 가지를 같이 쓴다. Schedule 모듈로 cron 트리거만 잡고, 실제 작업은 BullMQ 큐에 enqueue 해서 worker가 처리한다.

```ts
import { Injectable } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';

@Injectable()
export class ReportTrigger {
  constructor(@InjectQueue('report') private readonly queue: Queue) {}

  @Cron('0 0 9 * * 1-5', { timeZone: 'Asia/Seoul' })
  async triggerDailyReports() {
    const users = await this.userRepo.findActive();
    await this.queue.addBulk(
      users.map((u) => ({
        name: 'send-report',
        data: { userId: u.id },
        opts: { attempts: 3, backoff: { type: 'exponential', delay: 5000 } },
      })),
    );
  }
}
```

이 구조면 cron 트리거는 한 인스턴스만 락 잡고 enqueue 하면 되고, 실제 처리는 worker N개가 BullMQ에서 끌어다 병렬로 돌리니까 부하 분산까지 자연스럽게 해결된다.

## 자주 만나는 트러블슈팅

**스케줄이 안 돈다.** 9할은 `ScheduleModule.forRoot()` 누락이다. 그 다음은 `@Injectable()` 누락이거나, 해당 service가 모듈 `providers`에 등록 안 된 경우다.

**테스트에서 cron이 실제로 돈다.** 테스트 환경에서 Schedule이 활성화되면 의도치 않은 실행이 일어난다. 테스트 모듈에서는 `ScheduleModule.forRoot()` 대신 mocking 하거나, cron 메서드를 직접 호출해서 단위 테스트하는 식으로 분리한다.

**작업이 겹쳐 돈다.** interval/cron에서 비동기 작업이 다음 틱보다 오래 걸리면 동시 실행이 일어난다. 클래스 멤버 `private running = false` 같은 가드를 두거나, 분산 환경이면 락으로 처리한다.

**메모리 누수.** `SchedulerRegistry.addCronJob`으로 동적 등록한 작업을 삭제하지 않고 새로 추가하면 같은 이름이 중복 등록되거나 핸들러가 누적된다. 등록 전 `doesExist` 체크와 `deleteCronJob`을 묶어두는 습관이 필요하다.

**graceful shutdown.** SIGTERM이 들어왔는데 cron 작업이 한창 돌고 있으면 중간에 끊긴다. `enableShutdownHooks()`를 호출하고, 작업 안에서 shutdown signal을 받아 중단 가능한 지점에서 빠져나오게 만들어야 한다. 긴 배치 작업은 처음부터 BullMQ로 보내는 게 낫다.

## 정리

`@nestjs/schedule`은 단일 프로세스에서 단순 주기 작업을 돌리기에는 충분히 좋은 도구다. 데코레이터 한 줄로 cron이 붙고, `SchedulerRegistry`로 동적 제어까지 된다. 다만 분산 환경에 올라가는 순간 중복 실행 문제가 따라오고, 재시도·진행상태 추적 같은 요구가 붙으면 빠르게 한계를 보인다. 트리거는 Schedule로, 무거운 처리는 BullMQ로 나누는 패턴이 실무에서 가장 안정적이다.
