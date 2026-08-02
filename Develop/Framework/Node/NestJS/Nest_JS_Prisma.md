---
title: NestJS Prisma 연동
tags: [nestjs, prisma, database, orm, migration, transaction]
updated: 2026-07-10
---

# NestJS Prisma 연동
## 들어가며

NestJS에서 데이터 접근 계층을 잡을 때 TypeORM 대신 Prisma를 고르는 경우가 늘었다. Prisma는 `@nestjs/typeorm` 같은 공식 NestJS 패키지가 따로 없다. 그냥 `@prisma/client`를 쓰고, PrismaClient를 NestJS 라이프사이클에 맞춰 감싸는 얇은 서비스 하나만 직접 만들면 된다. 이 단순함이 장점이자 함정이다. 연결을 언제 열고 언제 닫을지, 트랜잭션을 어떻게 넘길지, 테스트에서 DB를 어떻게 격리할지를 프레임워크가 정해주지 않으니 직접 결정해야 한다.

이 문서는 PrismaClient를 NestJS에 붙이는 기본 패턴부터 실제 운영하면서 밟는 지뢰까지 정리한다. TypeORM 문서는 별도로 있으니 여기서는 Prisma 고유의 동작과 둘 중 무엇을 고를지 판단 기준에 집중한다.

## 스키마와 클라이언트 생성

Prisma는 `schema.prisma` 파일이 단일 소스다. 엔티티 클래스에 데코레이터를 붙이는 TypeORM과 달리, 별도 DSL로 모델을 정의하고 거기서 타입과 쿼리 빌더를 코드 생성한다.

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
}

model Post {
  id        Int      @id @default(autoincrement())
  title     String
  content   String?
  published Boolean  @default(false)
  author    User     @relation(fields: [authorId], references: [id])
  authorId  Int
}
```

스키마를 고친 뒤에는 반드시 `prisma generate`를 다시 돌려야 클라이언트 타입이 갱신된다. 이걸 빼먹으면 새로 추가한 필드가 타입에 안 잡혀서 컴파일은 통과하는데 런타임에서 `undefined`가 나오는 식으로 어긋난다. `postinstall` 스크립트에 `prisma generate`를 걸어두면 CI나 동료 환경에서 클라이언트가 안 만들어진 채로 빌드되는 사고를 줄인다.

```json
// package.json
{
  "scripts": {
    "postinstall": "prisma generate"
  }
}
```

## PrismaService — OnModuleInit으로 연결 관리

PrismaClient는 생성 시점에 연결을 만들지 않는다. 첫 쿼리가 들어올 때 lazy하게 연결한다. 그래서 `$connect()`를 명시적으로 부르지 않아도 동작은 한다. 그런데 부팅 직후 첫 요청이 연결 수립 지연까지 떠안는 게 싫고, DB가 죽어있을 때 부팅 단계에서 바로 실패시키고 싶으면 `OnModuleInit`에서 `$connect()`를 호출한다.

```typescript
// prisma/prisma.service.ts
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  constructor() {
    super({
      log: ['warn', 'error'],
    });
  }

  async onModuleInit() {
    await this.$connect();
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }
}
```

`PrismaClient`를 상속하면 PrismaService 인스턴스가 곧 클라이언트라서 `prisma.user.findMany()`처럼 바로 쓸 수 있다. 상속 대신 멤버로 들고 있는 방식(`this.client.user...`)도 가능한데, 상속 쪽이 호출부가 깔끔해서 대부분 이렇게 쓴다.

`onModuleDestroy`의 `$disconnect()`가 중요하다. 이걸 빼면 테스트를 여러 개 돌릴 때 연결이 안 닫혀서 Jest가 "A worker process has failed to exit gracefully" 경고를 띄우고 행이 걸린다. 운영에서도 graceful shutdown 시 연결이 안 닫혀 DB 쪽에 좀비 커넥션이 남는다.

### enableShutdownHooks 함정

예전 NestJS 문서에는 Prisma의 `beforeExit` 이벤트를 받아서 `app.close()`를 부르는 코드가 있었다. Prisma 5부터 `beforeExit` 훅이 라이브러리 엔진에서 제거됐기 때문에 이 패턴은 더 이상 동작하지 않는다. 지금은 `OnModuleDestroy`만 제대로 구현하면 되고, NestJS 쪽 시그널 처리는 `main.ts`에서 켠다.

```typescript
// main.ts
const app = await NestFactory.create(AppModule);
app.enableShutdownHooks();
```

`enableShutdownHooks()`를 켜야 SIGTERM/SIGINT가 들어왔을 때 NestJS가 `onModuleDestroy`를 실제로 호출한다. 이걸 안 켜면 Ctrl+C나 컨테이너 종료 신호에서 `$disconnect()`가 안 불린다.

## 모듈 주입 패턴

PrismaService를 전역 모듈로 만들어 한 번만 등록하고 어디서든 주입받는 방식이 가장 흔하다.

```typescript
// prisma/prisma.module.ts
import { Global, Module } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Global()
@Module({
  providers: [PrismaService],
  exports: [PrismaService],
})
export class PrismaModule {}
```

```typescript
// app.module.ts
@Module({
  imports: [PrismaModule],
})
export class AppModule {}
```

`@Global()`을 붙이면 다른 모듈에서 `imports`에 PrismaModule을 또 넣지 않아도 PrismaService를 주입받는다. DB 접근은 거의 모든 모듈에서 필요하니 전역이 합리적이다. 다만 전역 모듈을 남발하면 의존 관계가 코드에서 안 보이게 되니, 프로젝트에서 전역으로 둘 건 Config·Prisma 정도로 제한하는 편이 낫다.

서비스에서는 그냥 생성자 주입으로 받는다.

```typescript
// user.service.ts
@Injectable()
export class UserService {
  constructor(private readonly prisma: PrismaService) {}

  findById(id: number) {
    return this.prisma.user.findUnique({ where: { id } });
  }
}
```

TypeORM처럼 모델별 Repository를 주입받는 구조가 아니라, PrismaService 하나에서 `prisma.user`, `prisma.post`로 모든 모델에 접근한다. Repository 패턴이 익숙하면 모델별 Repository 클래스를 직접 만들어 그 안에서 PrismaService를 호출하게 감쌀 수도 있지만, 추상화 한 겹을 더 얹는 거라 팀 합의가 없으면 굳이 안 만든다.

## 트랜잭션

Prisma의 트랜잭션은 두 가지 형태가 있다. 겉보기엔 비슷해 보여도 내부 동작이 다르니 구분해서 써야 한다.

### Sequential — 배열 방식

쿼리 배열을 넘기면 한 트랜잭션 안에서 순서대로 실행한다.

```typescript
const [user, post] = await this.prisma.$transaction([
  this.prisma.user.create({ data: { email: 'a@b.com' } }),
  this.prisma.post.create({ data: { title: 'hi', authorId: 1 } }),
]);
```

`this.prisma.user.create(...)` 라인을 작성하는 시점에는 실제 쿼리가 나가지 않는다. Prisma는 이 호출을 `PrismaPromise`라는 지연 실행 객체로 만들고, `$transaction([...])` 호출 시점에 배열 안 쿼리들을 한꺼번에 실행한다. 내부적으로는 `BEGIN` → 순차 실행 → `COMMIT` 흐름이다.

이 방식의 한계는 명확하다. 첫 번째 쿼리 결과의 id를 두 번째 쿼리에서 참조할 수 없다. 실행 전에 배열을 전부 구성해야 하기 때문이다. 쿼리 간에 의존성이 없을 때만 쓴다.

### Interactive — 콜백 방식

콜백 안에서 트랜잭션 전용 클라이언트(`tx`)를 받아 쓴다. 중간 결과를 보고 분기하거나, 앞 쿼리의 id를 뒤 쿼리에 넘겨야 할 때 이걸 쓴다.

```typescript
async transfer(fromId: number, toId: number, amount: number) {
  return this.prisma.$transaction(async (tx) => {
    const from = await tx.account.update({
      where: { id: fromId },
      data: { balance: { decrement: amount } },
    });

    if (from.balance < 0) {
      throw new Error('잔액 부족');
    }

    await tx.account.update({
      where: { id: toId },
      data: { balance: { increment: amount } },
    });
  });
}
```

Interactive 트랜잭션은 내부적으로 커넥션 풀에서 커넥션 하나를 예약하고 `BEGIN`을 실행한다. 콜백이 resolve되면 `COMMIT`, reject되면 `ROLLBACK`이 나가고 커넥션을 풀로 돌려보낸다. 배열 방식과 달리 콜백 실행 전체 시간 동안 커넥션을 점유한다. 콜백이 오래 걸리면 그만큼 풀 압박이 생긴다.

콜백 안에서는 반드시 `tx`를 써야 한다. 실수로 `this.prisma`를 쓰면 그 쿼리는 트랜잭션 밖에서 별도 연결로 나가서, 롤백돼야 할 때 안 돌아간다. 이게 진짜 자주 나오는 버그다. 콜백 안에서 다른 서비스 메서드를 호출하는 구조라면 그 메서드도 `tx`를 인자로 받게 시그니처를 바꿔야 한다.

```typescript
// 트랜잭션 클라이언트를 받을 수 있게 타입을 연다
type TxClient = Omit<PrismaClient, '$connect' | '$disconnect' | '$on' | '$transaction' | '$use' | '$extends'>;

async createPost(tx: TxClient, authorId: number) {
  return tx.post.create({ data: { title: 'x', authorId } });
}
```

Interactive 트랜잭션에는 기본 타임아웃이 있다. 콜백 안에서 외부 API 호출이나 무거운 연산을 하면 트랜잭션이 길어지고, 기본값(보통 5초)을 넘기면 `Transaction already closed` 에러가 난다. 트랜잭션 안에서는 DB 작업만 빠르게 끝내고, 외부 호출은 트랜잭션 밖으로 빼야 한다. 길게 가야 한다면 옵션으로 늘린다.

```typescript
this.prisma.$transaction(async (tx) => { /* ... */ }, {
  timeout: 15000,
  maxWait: 5000,
});
```

`timeout`을 무작정 늘리는 건 답이 아니다. 트랜잭션이 길수록 락을 오래 쥐고 있어 동시성이 떨어진다. 외부 호출을 트랜잭션 밖으로 빼는 게 먼저다.

### Sequential vs Interactive 선택 기준

두 방식 중 무엇을 쓸지 판단 기준이다.

| 상황 | 방식 |
|---|---|
| 쿼리 간 의존성 없음 (id 참조 등) | Sequential |
| 앞 결과를 보고 다음 쿼리 구성 | Interactive |
| 중간에 분기 로직 있음 | Interactive |
| 다른 서비스 메서드를 같은 트랜잭션으로 묶어야 함 | Interactive |
| 쿼리가 완전히 독립적이고 단순 묶음이면 됨 | Sequential |

Sequential이 커넥션을 덜 오래 점유하는 경향이 있지만, 차이가 두드러지는 경우는 드물다. 대부분은 쿼리 간 의존성 여부로 결정된다.

### 중첩 트랜잭션과 Savepoint 제한

Prisma는 중첩 트랜잭션을 지원하지 않는다. `tx` 안에서 `tx.$transaction()`을 호출하려고 하면 `tx`에 `$transaction` 메서드 자체가 없어서 타입 에러가 난다. 데이터베이스 레벨의 `SAVEPOINT`도 Prisma가 노출하지 않는다.

이 제한이 문제가 되는 경우는 대개 서비스 계층이 서로를 호출하는 구조에서다. A 서비스가 트랜잭션을 열고, 그 안에서 B 서비스 메서드를 호출하는데 B 메서드 내부에도 `$transaction`이 있으면 중첩이 된다.

```typescript
// 문제가 되는 구조
async transferAndNotify(fromId: number, toId: number, amount: number) {
  return this.prisma.$transaction(async (tx) => {
    await this.transferService.transfer(fromId, toId, amount); // 내부에 $transaction 있음
    await this.notificationService.create(toId, amount);       // 내부에 $transaction 있음
  });
}
```

해결 방법은 `tx`를 명시적으로 인자로 내려보내는 것이다. `$transaction`을 열지 않고, 받은 `tx`로 쿼리만 실행하게 메서드를 나눈다.

```typescript
type TxClient = Omit<PrismaClient, '$connect' | '$disconnect' | '$on' | '$transaction' | '$use' | '$extends'>;

// TransferService
async transfer(tx: TxClient, fromId: number, toId: number, amount: number) {
  const from = await tx.account.update({
    where: { id: fromId },
    data: { balance: { decrement: amount } },
  });
  if (from.balance < 0) throw new Error('잔액 부족');
  await tx.account.update({
    where: { id: toId },
    data: { balance: { increment: amount } },
  });
}

// NotificationService
async create(tx: TxClient, userId: number, amount: number) {
  return tx.notification.create({ data: { userId, amount } });
}

// 호출부
async transferAndNotify(fromId: number, toId: number, amount: number) {
  return this.prisma.$transaction(async (tx) => {
    await this.transferService.transfer(tx, fromId, toId, amount);
    await this.notificationService.create(tx, toId, amount);
  });
}
```

`tx`를 인자로 받는 메서드와 `$transaction`을 여는 메서드를 분리하면, 혼자 쓸 때는 `$transaction`을 열고 같이 쓸 때는 받은 `tx`를 그대로 넘기는 구조가 된다.

`SAVEPOINT`가 정말 필요하면 `$executeRaw`로 직접 SQL을 쓰는 방법이 있긴 하다. 하지만 Prisma가 커넥션을 어떻게 관리하는지 내부 동작과 맞물리는 부분이 있어서, 이 방향은 테스트를 충분히 하고 가야 한다.

### Nested write

부모와 자식 레코드를 한 번에 만들 때는 트랜잭션을 명시적으로 안 열어도 된다. `create` 안에서 관계 필드에 중첩 write를 쓰면 Prisma가 알아서 한 트랜잭션으로 묶는다.

```typescript
await this.prisma.user.create({
  data: {
    email: 'a@b.com',
    posts: {
      create: [
        { title: 'first' },
        { title: 'second' },
      ],
    },
  },
});
```

User 생성과 Post 2개 생성이 모두 성공하거나 모두 실패한다. 중간에 하나라도 깨지면 User도 안 만들어진다. `connect`, `connectOrCreate`, `update`, `upsert`도 중첩으로 쓸 수 있다. 단순한 부모-자식 동시 생성은 `$transaction`을 직접 쓰는 것보다 중첩 write가 읽기 쉽다.

### 트랜잭션 Context 패턴 — AsyncLocalStorage 활용

`tx`를 인자로 내려보내는 방식의 문제는 호출 스택 깊이에 비례해 인자가 증가한다는 점이다. 서비스가 여러 레이어를 거치면 모든 메서드 시그니처가 `tx?: TxClient`를 달고 다녀야 한다. 이게 지저분해지면 Node.js의 `AsyncLocalStorage`로 트랜잭션 클라이언트를 컨텍스트에 태워 넘기는 방식을 쓸 수 있다.

```typescript
// prisma/prisma.service.ts
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';
import { AsyncLocalStorage } from 'async_hooks';

type TxClient = Omit<
  PrismaClient,
  '$connect' | '$disconnect' | '$on' | '$transaction' | '$use' | '$extends'
>;

const txStorage = new AsyncLocalStorage<TxClient>();

@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  constructor() {
    super({ log: ['warn', 'error'] });
  }

  async onModuleInit() {
    await this.$connect();
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }

  // 현재 실행 컨텍스트의 tx 클라이언트를 반환한다
  // 트랜잭션 밖이면 this(기본 PrismaClient)를 반환한다
  get client(): TxClient {
    return txStorage.getStore() ?? this;
  }

  // 트랜잭션을 열고 해당 컨텍스트 안에서 실행되는 모든 코드가 tx를 쓰게 한다
  async runInTransaction<T>(fn: () => Promise<T>): Promise<T> {
    return this.$transaction((tx) => txStorage.run(tx, fn));
  }
}
```

서비스에서는 `tx`를 인자로 받을 필요 없이 `this.prisma.client`로 현재 컨텍스트에 맞는 클라이언트를 가져온다.

```typescript
// user.service.ts
@Injectable()
export class UserService {
  constructor(private readonly prisma: PrismaService) {}

  async createUser(data: CreateUserDto) {
    // 트랜잭션 안이면 tx 클라이언트, 밖이면 기본 클라이언트
    return this.prisma.client.user.create({ data });
  }

  async findById(id: number) {
    return this.prisma.client.user.findUnique({ where: { id } });
  }
}

// account.service.ts
@Injectable()
export class AccountService {
  constructor(private readonly prisma: PrismaService) {}

  async deductBalance(userId: number, amount: number) {
    const account = await this.prisma.client.account.update({
      where: { userId },
      data: { balance: { decrement: amount } },
    });
    if (account.balance < 0) throw new Error('잔액 부족');
    return account;
  }
}
```

트랜잭션을 여는 쪽에서만 `runInTransaction`을 호출한다. 내부에서 다른 서비스를 호출해도 인자 변경 없이 자동으로 같은 tx를 쓴다.

```typescript
// transfer.service.ts
@Injectable()
export class TransferService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly userService: UserService,
    private readonly accountService: AccountService,
  ) {}

  async transfer(fromId: number, toId: number, amount: number) {
    return this.prisma.runInTransaction(async () => {
      await this.accountService.deductBalance(fromId, amount);
      await this.accountService.addBalance(toId, amount);
      // userService 내부도 같은 tx를 쓴다
      await this.userService.recordTransfer(fromId, toId, amount);
    });
  }
}
```

주의할 점이 있다. `AsyncLocalStorage`는 같은 비동기 실행 컨텍스트 안에서만 값이 전파된다. `setImmediate`, `setTimeout`, 별도로 띄운 `Promise.all` 중에 하나가 컨텍스트를 벗어나면 `txStorage.getStore()`가 `undefined`를 돌려줘서 트랜잭션 밖 클라이언트로 쿼리가 나간다. 이 경우 롤백돼야 할 쿼리가 커밋된 채로 남는다.

```typescript
// 이렇게 쓰면 안 된다 — setTimeout은 AsyncLocalStorage 컨텍스트를 잃는다
await this.prisma.runInTransaction(async () => {
  await this.accountService.deductBalance(fromId, amount);
  setTimeout(() => {
    this.accountService.addBalance(toId, amount); // tx 없이 실행된다
  }, 0);
});
```

트랜잭션 안에서는 `setTimeout`, 외부 이벤트 핸들러 같은 컨텍스트 탈출 경로를 쓰지 않아야 한다.

이 패턴은 편리하지만 암묵적으로 동작하는 만큼 팀원이 동작 원리를 알고 써야 한다. `tx`를 명시적으로 넘기는 방식보다 추적이 어렵다. 서비스 호출 깊이가 얕고 구조가 단순하면 명시적 인자 전달이 더 낫다.

## 마이그레이션 운영

개발할 때와 배포할 때 쓰는 명령이 다르다. 이걸 섞으면 운영 DB가 날아갈 수 있으니 확실히 구분해야 한다.

개발 환경에서는 `prisma migrate dev`를 쓴다. 스키마 변경을 감지해 마이그레이션 SQL 파일을 만들고, 로컬 DB에 적용하고, 클라이언트를 다시 생성한다. 이 명령은 스키마가 어긋났다고 판단하면 DB를 리셋(drop)할 수 있다. 그래서 운영 DB에는 절대 쓰면 안 된다.

운영·스테이징 배포에서는 `prisma migrate deploy`만 쓴다.

```bash
# 배포 파이프라인
npx prisma migrate deploy
```

`migrate deploy`는 이미 만들어진 마이그레이션 파일만 순서대로 적용한다. 새 마이그레이션을 만들지도, DB를 리셋하지도 않는다. 적용 안 된 마이그레이션만 골라 실행하므로 멱등하게 돌려도 안전하다. CI/CD에서 앱 배포 직전 단계에 넣는다.

마이그레이션 파일은 반드시 Git에 커밋해서 코드와 함께 버전 관리한다. 마이그레이션을 만든 개발자의 로컬에만 있고 커밋이 안 되면, 배포 환경에서 `migrate deploy`가 적용할 파일이 없어 스키마가 안 바뀐다.

### 운영 배포 절차

배포 파이프라인에서 마이그레이션 순서는 이렇게 가야 한다.

```
1. 새 앱 이미지 빌드
2. prisma migrate deploy  (스키마 변경 적용)
3. 앱 컨테이너 교체 (새 이미지로 롤링 업데이트)
```

앱을 먼저 배포하고 마이그레이션을 나중에 돌리면, 새 코드가 아직 없는 컬럼을 참조하다 에러가 난다. 반대로 마이그레이션 후 이전 앱이 잠깐 돌아가는 상황은 괜찮은 경우가 많다. 신규 컬럼 추가처럼 이전 버전에서는 무시되는 변경이면 큰 문제가 없다. 컬럼 이름 변경이나 삭제 같은 파괴적 변경은 구버전 앱이 참조하는 컬럼이 사라지므로 더 신중하게 진행해야 한다.

`migrate deploy`는 쿠버네티스 환경에서 init container나 별도 Job으로 실행하는 경우가 많다. 여러 앱 파드가 동시에 `migrate deploy`를 실행해도 Prisma가 내부적으로 잠금을 잡아서 중복 실행을 막는다. 멱등하게 돌려도 괜찮다.

### 운영에서 마이그레이션이 막힐 때

배포 중 마이그레이션이 중간에 실패하면 `_prisma_migrations` 테이블에 실패 기록이 남고, 이후 `migrate deploy`가 "이전 마이그레이션이 실패 상태"라며 멈춘다. 이때 함부로 `migrate dev`나 `migrate reset`을 운영에서 돌리면 안 된다. 실패한 마이그레이션을 수동으로 정리한 뒤 `prisma migrate resolve`로 상태를 맞춰야 한다.

```bash
# 실패한 마이그레이션을 롤백 처리로 표시
npx prisma migrate resolve --rolled-back 20260101000000_add_column

# 또는 수동으로 SQL을 직접 적용했다면 적용됨으로 표시
npx prisma migrate resolve --applied 20260101000000_add_column
```

`--rolled-back`은 해당 마이그레이션을 "적용 안 된 상태"로 기록만 바꾸는 것이다. DB 변경 사항을 실제로 되돌리지는 않는다. 마이그레이션이 중간에 실패했다면 SQL이 일부만 실행된 상태일 수 있으므로, `_prisma_migrations` 상태를 바꾸기 전에 DB를 직접 확인해야 한다.

### 마이그레이션 롤백

Prisma Migrate는 자동 롤백 기능이 없다. 롤백 SQL을 Prisma가 생성해주지 않는다. 운영에서 마이그레이션을 되돌리는 방법은 두 가지다.

첫째, 새 마이그레이션으로 역방향 변경을 추가하는 방법이다. 컬럼을 추가했다면 컬럼을 삭제하는 마이그레이션을 새로 만들어 배포한다. Prisma 워크플로와 자연스럽게 맞고, 마이그레이션 히스토리가 남아서 추적하기 쉽다.

```bash
# 스키마를 이전 상태로 되돌린 뒤 새 마이그레이션 생성
npx prisma migrate dev --name revert_add_column
```

둘째, 미리 준비해둔 롤백 SQL을 직접 실행하는 방법이다. 배포 전에 롤백 SQL 파일을 같이 준비해두고, 문제가 생기면 수동으로 실행한다.

```sql
-- migrations/rollback/20260101000000_add_column_rollback.sql
ALTER TABLE "User" DROP COLUMN IF EXISTS "newColumn";
```

```bash
# 롤백 SQL 직접 실행
psql $DATABASE_URL -f migrations/rollback/20260101000000_add_column_rollback.sql

# DB 상태를 바꾼 뒤 Prisma 마이그레이션 기록도 맞춘다
npx prisma migrate resolve --rolled-back 20260101000000_add_column
```

롤백 SQL을 미리 준비하는 습관이 중요하다. 장애 상황에서 역방향 SQL을 즉석에서 작성하면 실수가 난다.

컬럼 추가에 `NOT NULL` 제약을 기존 데이터가 있는 테이블에 걸면 마이그레이션이 깨진다. 기본값 없이 NOT NULL을 넣으면 기존 행이 제약을 위반하기 때문이다. 단계를 나눠서 nullable로 컬럼 추가 → 데이터 백필 → NOT NULL 제약 추가 순으로 가야 한다. 큰 테이블이면 이 과정에서 락 시간도 신경 써야 한다.

## N+1과 include / select 함정

Prisma는 관계 데이터를 자동으로 안 가져온다. `include`나 `select`로 명시해야 한다. 이걸 안 하고 루프 안에서 관계를 따로 조회하면 N+1이 터진다.

```typescript
// N+1 발생: user 수만큼 post 쿼리가 추가로 나간다
const users = await this.prisma.user.findMany();
for (const user of users) {
  const posts = await this.prisma.post.findMany({
    where: { authorId: user.id },
  });
}
```

```typescript
// include로 한 번에: 쿼리가 묶인다
const users = await this.prisma.user.findMany({
  include: { posts: true },
});
```

`include`를 쓰면 Prisma가 관계를 별도 쿼리로 가져온 뒤 메모리에서 합친다(JOIN이 아니라 별도 쿼리 + 애플리케이션 조인이 기본 동작). 그래서 N개 row에 대해 관계 쿼리 1개가 추가되는 식이라, 루프에서 N번 도는 것보다 훨씬 낫다. Prisma 5.7 이후로는 `relationLoadStrategy: 'join'` 옵션으로 실제 DB JOIN을 쓰게 할 수도 있는데, 데이터 모양에 따라 어느 쪽이 빠른지 달라지니 측정해보고 정한다.

`select`는 필요한 컬럼만 가져온다. 큰 텍스트 컬럼이나 안 쓰는 필드를 매번 끌어오면 네트워크와 메모리를 낭비한다.

```typescript
const users = await this.prisma.user.findMany({
  select: {
    id: true,
    email: true,
    posts: {
      select: { id: true, title: true },
    },
  },
});
```

`include`와 `select`는 같은 쿼리에서 동시에 못 쓴다. 한쪽을 골라야 한다. 관계를 가져오면서 필드도 제한하고 싶으면 `select` 안에서 관계를 다시 `select`로 파고드는 구조로 쓴다.

가장 흔한 N+1은 코드에 직접 루프가 없는 경우다. GraphQL 리졸버나 응답 직렬화 과정에서 관계 필드에 접근하면 lazy 조회처럼 보이는데, Prisma는 lazy loading이 없어서 처음 조회 때 `include` 안 했으면 그 필드는 그냥 없다. TypeORM의 lazy relation처럼 나중에 접근하면 자동으로 채워지는 동작을 기대하면 안 된다.

## 테스트 시 DB 격리

Prisma 테스트에서 제일 골치 아픈 게 격리다. 테스트가 같은 DB를 공유하면 한 테스트가 만든 데이터가 다른 테스트에 새어 들어가 간헐적으로 깨진다.

가장 확실한 방법은 테스트마다 실제 DB에 쓰되 트랜잭션으로 감싸고 끝나면 롤백하는 것이다. 다만 Prisma의 interactive 트랜잭션은 콜백이 끝나면 자동 커밋/롤백이라, 테스트 본문을 트랜잭션 안에 넣기가 구조적으로 까다롭다. 그래서 현실적으로는 두 가지를 많이 쓴다.

첫째, 테스트별로 데이터를 정리(truncate)하는 방법.

```typescript
afterEach(async () => {
  // 외래키 순서 때문에 자식부터 지운다
  await prisma.post.deleteMany();
  await prisma.user.deleteMany();
});
```

테이블이 많으면 일일이 지우는 게 번거롭고 순서도 신경 써야 한다. `TRUNCATE ... CASCADE`를 raw로 돌리면 한 번에 정리된다.

```typescript
afterEach(async () => {
  await prisma.$executeRawUnsafe(
    `TRUNCATE TABLE "Post", "User" RESTART IDENTITY CASCADE`,
  );
});
```

둘째, 테스트 스위트마다 독립된 DB(또는 스키마)를 띄우는 방법. PostgreSQL이면 `DATABASE_URL`의 schema 파라미터를 테스트마다 다르게 줘서 격리한다. Testcontainers로 테스트 시작 시 일회용 DB 컨테이너를 띄우면 운영 DB와 완전히 분리되고 병렬 실행도 안전하다. CI에서 가장 깔끔한 방식이지만 컨테이너 부팅 시간이 붙는다.

NestJS 테스트 모듈에서는 PrismaService를 그대로 쓰되 `DATABASE_URL`만 테스트용으로 바꾸거나, mock으로 갈아끼운다. 단위 테스트라면 PrismaService를 mock으로 교체해 DB 없이 서비스 로직만 검증한다.

```typescript
const module = await Test.createTestingModule({
  providers: [
    UserService,
    {
      provide: PrismaService,
      useValue: {
        user: {
          findUnique: jest.fn().mockResolvedValue({ id: 1, email: 'a@b.com' }),
        },
      },
    },
  ],
}).compile();
```

mock으로 가면 빠르지만 실제 쿼리가 맞는지는 검증 못 한다. 쿼리 동작까지 보장하려면 실제 DB를 쓰는 통합 테스트가 따로 있어야 한다. 단위 테스트는 mock으로, 핵심 흐름은 Testcontainers 통합 테스트로 이원화하는 구성이 무난하다.

## TypeORM과 선택 기준

둘 다 NestJS에서 잘 돌아간다. 프로젝트 성격에 따라 갈린다.

Prisma를 고르는 경우:

- 타입 안정성이 최우선일 때. 스키마에서 타입을 생성하므로 쿼리 결과 타입이 정확하다. `select`로 일부 필드만 골라도 반환 타입이 그에 맞게 좁혀진다. TypeORM은 부분 select 시 타입이 느슨하다.
- 마이그레이션 워크플로가 명확한 게 중요할 때. `migrate dev` / `migrate deploy` 구분이 명시적이라 운영 사고가 덜 난다.
- 단순한 CRUD와 명시적 쿼리 위주일 때. 관계를 항상 명시적으로 가져오니 N+1이 코드에 드러난다.

TypeORM을 고르는 경우:

- 복잡한 동적 쿼리가 많을 때. QueryBuilder가 조건 조합이나 서브쿼리를 자유롭게 짜는 데 유리하다. Prisma도 가능하지만 한계에 부딪히면 `$queryRaw`로 내려가야 한다.
- Spring/JPA 출신이 많은 팀일 때. 데코레이터 기반 엔티티와 Repository 패턴이 익숙하다.
- ActiveRecord나 lazy loading 같은 ORM 편의 기능에 기대고 싶을 때. Prisma는 일부러 그런 마법을 안 넣어서, 명시성을 선호하면 장점이고 편의를 원하면 단점이다.

성능은 둘 다 잘 쓰면 비슷하고, 못 쓰면 둘 다 N+1로 죽는다. 결정 요인은 보통 팀의 익숙함과 타입 안정성·명시성을 어디까지 원하느냐다. 새 프로젝트이고 팀이 타입스크립트 친화적이면 Prisma, 기존 코드베이스가 TypeORM이거나 동적 쿼리가 핵심이면 TypeORM 쪽으로 기운다.

Prisma의 가장 큰 약점은 raw 쿼리로 내려갔을 때다. 복잡한 분석 쿼리, 윈도우 함수, DB 특화 기능을 많이 쓰면 `$queryRaw`를 자주 쓰게 되고, 그러면 Prisma의 타입 안정성 이점이 사라진다. 이런 비중이 높은 프로젝트면 처음부터 TypeORM이나 Knex 같은 쿼리 빌더를 고려하는 게 낫다.
