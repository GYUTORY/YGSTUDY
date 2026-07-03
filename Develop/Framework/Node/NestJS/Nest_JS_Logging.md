---
title: NestJS 로깅 실무
tags:
  - NestJS
  - Logging
  - Pino
  - Winston
  - AsyncLocalStorage
  - Correlation ID
  - Structured Logging
updated: 2026-06-12
---

# NestJS 로깅

로깅은 처음 개발할 때는 `console.log` 하나로 충분해 보인다. 그러다 운영에 올리고 나면 상황이 달라진다. 특정 사용자가 결제가 안 된다고 문의하는데 로그에서 그 요청을 찾으려면 timestamp 추정해서 grep을 돌려야 하고, 동시에 들어온 다른 요청 로그와 섞여서 어느 줄이 그 사용자 건인지 알 수 없다. 로그가 텍스트라서 CloudWatch나 Loki에서 필드로 검색이 안 된다. 트래픽이 늘면 로그가 초당 수천 줄씩 쏟아져서 정작 봐야 할 에러가 묻힌다. 이 문서는 그 단계들을 하나씩 넘어가면서 겪은 문제와 해결을 정리한다.

## 내장 Logger의 위치와 한계

NestJS는 `@nestjs/common`에 `Logger` 클래스를 기본 제공한다. 부트스트랩 로그, DI 컨테이너 초기화 로그가 전부 이 Logger로 찍힌다.

```ts
import { Injectable, Logger } from '@nestjs/common';

@Injectable()
export class OrderService {
  private readonly logger = new Logger(OrderService.name);

  async createOrder(dto: CreateOrderDto) {
    this.logger.log(`주문 생성 시작 userId=${dto.userId}`);
    // ...
    this.logger.error('주문 생성 실패', error.stack);
  }
}
```

`new Logger(OrderService.name)`로 context를 넘기면 출력에 `[OrderService]`가 붙는다. 클래스마다 이 패턴을 반복하는 게 기본 사용법이다.

내장 Logger는 개발 단계까지는 쓸 만하다. 색깔도 입혀주고 context도 붙여준다. 운영에 올리면 세 가지가 발목을 잡는다.

첫째, 출력이 사람이 읽는 텍스트 포맷이다. JSON이 아니라서 로그 수집기에서 필드 단위로 쿼리할 수 없다. `level:error AND userId:1234` 같은 검색이 불가능하다.

둘째, 동기 출력이다. 내장 Logger는 `process.stdout.write`를 동기로 호출한다. 초당 로그가 수천 건이면 이 동기 write가 이벤트 루프를 붙잡는다. 부하 테스트를 돌려보면 로그를 끄는 것만으로 처리량이 올라가는 경우가 있는데, 원인이 이거다.

셋째, 요청 단위 추적이 안 된다. 어느 로그가 어느 HTTP 요청에서 나왔는지 연결할 방법이 기본 제공되지 않는다.

이 세 가지 때문에 운영에 들어가는 서비스는 거의 다 외부 로깅 라이브러리로 갈아탄다. 선택지는 사실상 pino와 winston 둘이다.

## pino vs winston

winston은 오래됐고 transport 생태계가 넓다. 파일 로테이션, 여러 목적지로 동시 출력, 커스텀 포맷 같은 게 다 된다. 대신 느리다. 포맷팅과 transport 처리를 메인 스레드에서 하기 때문에 로그가 많아지면 winston 자체가 병목이 된다.

pino는 속도를 최우선으로 만든 라이브러리다. 로그를 JSON으로 직렬화해서 stdout에 던지는 것까지만 메인 스레드에서 하고, 파일 기록이나 포맷팅 같은 무거운 작업은 별도 worker 스레드(transport)로 넘긴다. NestJS와는 `nestjs-pino`로 붙인다.

처리량이 중요하고 로그를 stdout으로 뽑아서 외부 수집기(CloudWatch, Loki, ELK)로 보내는 구조라면 pino를 권한다. 컨테이너 환경에서는 애플리케이션이 stdout에만 찍고 수집은 인프라가 맡는 게 표준이라, pino의 "stdout에 JSON 한 줄" 방식이 그대로 들어맞는다. 이 문서는 pino 기준으로 진행하고, winston은 뒤에서 따로 다룬다.

## nestjs-pino 연동

```bash
npm install nestjs-pino pino-http
npm install -D pino-pretty
```

`pino-http`는 HTTP 요청/응답을 자동으로 로깅해주는 미들웨어다. `nestjs-pino`가 이걸 감싼다.

```ts
// app.module.ts
import { Module } from '@nestjs/common';
import { LoggerModule } from 'nestjs-pino';

@Module({
  imports: [
    LoggerModule.forRoot({
      pinoHttp: {
        level: process.env.LOG_LEVEL || 'info',
        // 개발 환경에서만 pretty 출력, 운영은 JSON 한 줄
        transport:
          process.env.NODE_ENV !== 'production'
            ? { target: 'pino-pretty', options: { singleLine: true } }
            : undefined,
      },
    }),
  ],
})
export class AppModule {}
```

`main.ts`에서 NestJS 기본 Logger를 pino로 교체한다. 이걸 해야 부트스트랩 로그까지 pino로 나간다.

```ts
// main.ts
import { NestFactory } from '@nestjs/core';
import { Logger } from 'nestjs-pino';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useLogger(app.get(Logger));
  await app.listen(3000);
}
bootstrap();
```

`bufferLogs: true`가 중요하다. NestFactory가 만들어지는 시점에는 아직 pino Logger가 DI 컨테이너에서 준비되지 않았다. 이 옵션을 켜면 그 사이에 발생하는 로그를 버퍼에 모았다가 `useLogger`로 교체한 뒤 한꺼번에 흘려보낸다. 빼먹으면 초기 부트스트랩 로그가 기본 포맷으로 나가서 JSON 일관성이 깨진다.

서비스 안에서 로그를 찍을 때는 두 가지 방법이 있다. 기존 `@nestjs/common`의 `Logger`를 그대로 써도 `useLogger`로 교체했기 때문에 출력은 pino로 나간다.

```ts
import { Injectable, Logger } from '@nestjs/common';

@Injectable()
export class OrderService {
  private readonly logger = new Logger(OrderService.name);

  doSomething() {
    this.logger.log('처리 완료');
  }
}
```

구조화 필드를 붙이려면 `nestjs-pino`의 `PinoLogger`를 주입한다.

```ts
import { Injectable } from '@nestjs/common';
import { PinoLogger, InjectPinoLogger } from 'nestjs-pino';

@Injectable()
export class OrderService {
  constructor(
    @InjectPinoLogger(OrderService.name)
    private readonly logger: PinoLogger,
  ) {}

  async createOrder(userId: number, amount: number) {
    this.logger.info({ userId, amount }, '주문 생성');
  }
}
```

pino는 첫 인자에 객체, 둘째 인자에 메시지를 받는다. `console.log` 습관 때문에 메시지를 먼저 쓰면 객체가 무시되니 순서를 조심해야 한다.

## 구조화 로깅이 실제로 뭘 바꾸나

텍스트 로그와 JSON 로그의 차이는 운영에서 검색할 때 드러난다. 텍스트 로그는 이렇게 나간다.

```
2026-06-12 14:32:01 [OrderService] 주문 생성 userId=1234 amount=50000
```

이걸 CloudWatch에서 "userId 1234의 주문 실패 건만" 찾으려면 정규식 필터를 만들어야 하고, 포맷이 한 글자라도 바뀌면 필터가 깨진다. JSON 로그는 이렇게 나간다.

```json
{"level":"info","time":1718166721000,"context":"OrderService","userId":1234,"amount":50000,"msg":"주문 생성"}
```

CloudWatch Logs Insights에서 `fields @timestamp, msg | filter userId = 1234 and level = "error"`로 바로 검색된다. Loki면 `{app="order"} | json | userId="1234"`로 끝난다. 필드가 구조화돼 있으니 대시보드에서 집계도 된다. "지난 1시간 동안 amount가 100만 원 넘는 주문 수" 같은 쿼리가 가능해진다.

여기서 규칙 하나. 메시지 문자열에 값을 끼워 넣지 말고 필드로 분리한다.

```ts
// 나쁨 — 값이 메시지에 박혀서 검색이 안 됨
this.logger.info(`결제 실패 orderId=${orderId} reason=${reason}`);

// 좋음 — orderId, reason이 독립 필드로 들어감
this.logger.info({ orderId, reason }, '결제 실패');
```

`${}`로 끼워 넣는 순간 그 값은 다시 텍스트가 된다. 구조화 로깅을 도입한 의미가 없어진다. 이 습관을 팀 전체가 들이는 데 생각보다 시간이 걸린다.

## correlation ID — 요청 하나를 끝까지 추적하기

운영 디버깅에서 제일 답답한 순간은 "이 에러 로그가 어느 요청에서 나온 건지" 모를 때다. 동시에 수십 개 요청이 처리되면 로그가 시간순으로 뒤섞인다. A 사용자 요청 중간에 B 사용자 요청 로그가 끼어든다.

해법은 요청마다 고유 ID를 발급하고, 그 요청에서 나오는 모든 로그에 같은 ID를 붙이는 것이다. 이 ID를 correlation ID 또는 request ID라고 부른다. 발급한 ID로 검색하면 그 요청에서 나온 로그만 시간순으로 모인다. 마이크로서비스 환경이면 이 ID를 다음 서비스로 헤더에 실어 보내서 서비스 경계를 넘어 추적한다(trace ID로 확장).

문제는 NestJS의 DI 구조다. Controller → Service → Repository로 호출이 내려가는데, 각 계층에서 로그를 찍을 때마다 correlation ID를 인자로 넘겨받아야 한다면 모든 메서드 시그니처가 오염된다.

```ts
// 이렇게 하고 싶지 않다
async createOrder(dto: CreateOrderDto, correlationId: string) {
  await this.paymentService.charge(dto, correlationId);
  await this.inventoryService.reserve(dto, correlationId);
}
```

이 문제를 푸는 게 `AsyncLocalStorage`다.

## AsyncLocalStorage로 correlation ID 전파

`AsyncLocalStorage`는 Node.js 내장 모듈(`async_hooks`)이다. 비동기 호출 체인 전체에서 공유되는 저장소를 만든다. 한 요청이 들어와서 `run()`으로 컨텍스트를 열면, 그 안에서 호출되는 모든 비동기 함수가 `await`를 몇 번 건너뛰든 같은 저장소에 접근할 수 있다. 스레드 로컬 스토리지의 비동기 버전이라고 보면 된다.

요청별 저장소를 관리하는 모듈을 만든다.

```ts
// als/request-context.ts
import { AsyncLocalStorage } from 'node:async_hooks';

export interface RequestStore {
  correlationId: string;
}

export const requestContext = new AsyncLocalStorage<RequestStore>();

export function getCorrelationId(): string | undefined {
  return requestContext.getStore()?.correlationId;
}
```

미들웨어에서 요청마다 컨텍스트를 연다. 들어온 요청에 `x-correlation-id` 헤더가 있으면 재사용하고(상위 서비스가 보낸 경우), 없으면 새로 발급한다.

```ts
// als/correlation.middleware.ts
import { Injectable, NestMiddleware } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import { Request, Response, NextFunction } from 'express';
import { requestContext } from './request-context';

@Injectable()
export class CorrelationMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const correlationId =
      (req.headers['x-correlation-id'] as string) || randomUUID();

    res.setHeader('x-correlation-id', correlationId);

    requestContext.run({ correlationId }, () => {
      next();
    });
  }
}
```

`requestContext.run(store, callback)` 안에서 `next()`를 호출하는 게 핵심이다. 이렇게 해야 이후 Controller, Service에서 실행되는 모든 코드가 이 `run`의 컨텍스트 안에 들어간다. `run` 밖에서 `next()`를 부르면 컨텍스트가 전파되지 않는다.

미들웨어를 전역 등록한다.

```ts
// app.module.ts
import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { CorrelationMiddleware } from './als/correlation.middleware';

@Module({ /* ... */ })
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(CorrelationMiddleware).forRoutes('*');
  }
}
```

이제 어느 계층에서든 `getCorrelationId()`로 ID를 꺼낼 수 있다. 인자로 넘길 필요가 없다.

마지막으로 모든 로그에 이 ID가 자동으로 붙게 한다. pino의 `mixin` 옵션을 쓴다. `mixin`은 로그를 찍을 때마다 호출돼서 반환한 객체를 모든 로그에 합쳐준다.

```ts
// app.module.ts
LoggerModule.forRoot({
  pinoHttp: {
    level: process.env.LOG_LEVEL || 'info',
    mixin() {
      const correlationId = getCorrelationId();
      return correlationId ? { correlationId } : {};
    },
  },
});
```

이제 서비스 코드에서 그냥 `this.logger.info({ amount }, '주문 생성')`만 찍어도 출력에는 correlationId가 자동으로 들어간다.

```json
{"level":"info","correlationId":"a3f...","amount":50000,"msg":"주문 생성"}
{"level":"error","correlationId":"a3f...","msg":"재고 부족"}
```

같은 `a3f...`로 검색하면 이 요청에서 나온 로그가 전부 모인다.

### nestjs-pino의 내장 기능과 겹치는 부분

`nestjs-pino`는 `pino-http`를 통해 요청별 `req.id`를 자동 생성하고, 그 요청 안에서 `PinoLogger`로 찍는 로그에 자동으로 묶어준다. 단순히 "요청별로 로그를 묶는다"만 필요하면 `genReqId` 옵션으로 끝낼 수도 있다.

```ts
LoggerModule.forRoot({
  pinoHttp: {
    genReqId: (req, res) => {
      const id = (req.headers['x-correlation-id'] as string) || randomUUID();
      res.setHeader('x-correlation-id', id);
      return id;
    },
  },
});
```

`AsyncLocalStorage` 방식을 따로 만드는 이유는 로깅 바깥에서도 correlation ID가 필요할 때가 있어서다. 외부 API 호출 시 헤더에 실어 보내거나, 에러 알림(Sentry, Slack)에 ID를 넣거나, 응답 바디에 추적용으로 넣을 때 `getCorrelationId()` 한 줄로 어디서든 꺼낼 수 있다. `pino-http`의 `req.id`는 로깅 컨텍스트 안에서만 접근 가능하다. 둘 중 어느 쪽이든 프로젝트 상황에 맞춰 고르면 된다.

## 로그 레벨 환경별 분리

레벨은 운영 환경마다 다르게 가야 한다. 로컬에서는 `debug`까지 다 보고 싶고, 운영에서는 `info` 이상만 봐야 디스크와 비용을 아낀다. 스테이징은 그 중간이다.

레벨을 코드에 하드코딩하지 않고 환경변수로 뺀다.

```ts
LoggerModule.forRoot({
  pinoHttp: {
    level: process.env.LOG_LEVEL || 'info',
  },
});
```

```bash
# .env.local
LOG_LEVEL=debug

# .env.production
LOG_LEVEL=info
```

pino 레벨 순서는 `trace(10) < debug(20) < info(30) < warn(40) < error(50) < fatal(60)`이다. `level`을 `info`로 두면 30 미만, 즉 `debug`와 `trace`는 직렬화 자체를 건너뛴다. 여기서 성능 포인트 하나. 운영에서 `debug` 로그를 끄면 그 로그는 객체 직렬화도 안 일어난다. 그래서 비싼 로그(`this.logger.debug({ hugeObject }, ...)`)를 코드에 남겨둬도 운영에서는 비용이 0에 가깝다. 디버깅용 상세 로그를 지우지 말고 `debug` 레벨로 내려두는 게 낫다.

운영 중에 특정 시점만 로그 레벨을 낮춰 보고 싶을 때가 있다. 장애 조사 중에 `debug`를 잠깐 켜는 경우다. 재배포 없이 바꾸려면 레벨을 동적으로 바꿀 수 있게 해둔다. pino 인스턴스의 `level` 속성은 런타임에 변경 가능하다.

```ts
import { Injectable } from '@nestjs/common';
import { PinoLogger } from 'nestjs-pino';

@Injectable()
export class LogLevelService {
  constructor(private readonly logger: PinoLogger) {}

  setLevel(level: string) {
    this.logger.logger.level = level; // 하위 pino 인스턴스에 직접 접근
  }
}
```

이걸 관리자 전용 엔드포인트나 SIGUSR2 시그널 핸들러에 연결해두면 장애 시 유용하다. 다만 운영 중 레벨을 낮추면 로그 폭증으로 이어질 수 있으니, 잠깐 켜고 반드시 다시 올리는 절차를 정해둬야 한다.

## 민감정보 마스킹

로그에 비밀번호, 토큰, 카드번호, 주민번호가 그대로 찍히면 사고다. 컴플라이언스 감사에서 가장 먼저 걸리는 항목이고, 한번 로그 수집기에 들어간 평문은 회수가 사실상 불가능하다. 요청 바디를 통째로 로깅하다가 비밀번호가 그대로 들어가는 게 가장 흔한 사례다.

pino는 `redact` 옵션으로 특정 경로의 값을 마스킹한다. 직렬화 단계에서 처리하기 때문에 성능 부담이 거의 없다.

```ts
LoggerModule.forRoot({
  pinoHttp: {
    redact: {
      paths: [
        'req.headers.authorization',
        'req.headers.cookie',
        'req.body.password',
        'req.body.cardNumber',
        '*.password',          // 어느 깊이든 password 키
        '*.ssn',
      ],
      censor: '[REDACTED]',
    },
  },
});
```

`req.headers.authorization`은 거의 항상 넣어야 한다. `pino-http`가 요청 헤더를 통째로 로깅하는데 Bearer 토큰이 그대로 노출되기 때문이다. `cookie` 헤더도 세션 토큰이 들어 있어 마찬가지다.

`redact`의 한계는 경로를 미리 알아야 한다는 점이다. 중첩 객체의 동적 키나 예상 못 한 위치에 민감정보가 들어오면 놓친다. 그래서 redact만 믿지 말고, 애초에 요청 바디 전체를 로깅하지 않는 게 더 안전하다. 로깅할 필드를 명시적으로 골라서 찍는다.

```ts
// 나쁨 — 바디 전체. 새 필드가 추가되면 마스킹이 따라가지 못함
this.logger.info({ body: dto }, '주문 요청');

// 좋음 — 필요한 필드만 골라서
this.logger.info(
  { userId: dto.userId, productId: dto.productId, amount: dto.amount },
  '주문 요청',
);
```

추가로, 카드번호나 주민번호처럼 일부만 보여줘야 하는 값은 마스킹 함수를 따로 둔다. `redact`는 통째로 `[REDACTED]`로 바꾸지만, 디버깅하려면 뒤 4자리 정도는 봐야 할 때가 있다.

```ts
function maskCard(card: string): string {
  return card.replace(/\d(?=\d{4})/g, '*'); // 뒤 4자리만 남김
}

this.logger.info({ card: maskCard(dto.cardNumber) }, '결제 시도');
// card: "************1234"
```

`pino-http`가 자동으로 찍는 헤더 외에, custom serializer로 `req`/`res`에서 필요한 필드만 추출하면 노출 면적을 더 줄일 수 있다.

```ts
LoggerModule.forRoot({
  pinoHttp: {
    serializers: {
      req(req) {
        return { method: req.method, url: req.url, id: req.id };
      },
    },
  },
});
```

## 로그 폭증과 샘플링

트래픽이 늘면 로그량이 선형으로 늘어난다. 초당 만 건 요청이면 요청 로그만 초당 만 줄이다. 여기에 디버그 로그까지 섞이면 CloudWatch 수집 비용이 월 단위로 무섭게 올라가고, 정작 중요한 에러 로그가 노이즈에 묻힌다. 우리 팀도 로그 수집 비용이 EC2 비용을 넘긴 적이 있다.

대응은 단계별로 한다.

먼저 헬스체크, 메트릭 스크래핑 같은 노이즈 경로는 아예 로깅에서 제외한다. `pino-http`의 `autoLogging` 옵션으로 특정 경로를 거른다.

```ts
LoggerModule.forRoot({
  pinoHttp: {
    autoLogging: {
      ignore: (req) =>
        req.url === '/health' || req.url?.startsWith('/metrics'),
    },
  },
});
```

이것만으로도 헬스체크가 1초에 여러 번 들어오는 환경에서는 로그가 눈에 띄게 줄어든다.

그 다음이 샘플링이다. 정상(2xx) 요청 로그는 전부 남길 필요가 없다. 100건 중 1건만 남겨도 트래픽 패턴 파악에는 충분하다. 반면 에러(5xx)는 한 건도 놓치면 안 된다. 그래서 "정상은 샘플링하고 에러는 항상 남긴다"는 규칙으로 간다.

`customLogLevel`로 응답 상태에 따라 레벨을 정하고, 정상 요청은 일정 비율만 통과시킨다.

```ts
LoggerModule.forRoot({
  pinoHttp: {
    // 상태 코드별 레벨 — 5xx는 error, 4xx는 warn, 나머지는 info
    customLogLevel: (req, res, err) => {
      if (res.statusCode >= 500 || err) return 'error';
      if (res.statusCode >= 400) return 'warn';
      return 'info';
    },
    autoLogging: {
      ignore: (req) => {
        // 정상 GET 요청의 90%를 로깅에서 제외 (10%만 샘플링)
        // 에러는 customLogLevel에서 처리되므로 여기선 정상 요청만 거른다
        if (req.method === 'GET' && samplingSkip(0.9)) return true;
        return false;
      },
    },
  },
});
```

샘플링 비율을 코드에 박지 말고 환경변수로 빼서 트래픽 상황에 맞춰 조절한다. 평소엔 10% 남기다가 장애 조사 중엔 100%로 올리는 식이다.

애플리케이션 레벨 로그(서비스 안에서 직접 찍는 로그)도 같은 원칙이다. 루프 안에서 항목마다 `info`를 찍으면 만 건짜리 배치가 만 줄을 만든다. 이런 건 처음과 끝, 그리고 실패 건만 남긴다.

```ts
async processBatch(items: Item[]) {
  this.logger.info({ count: items.length }, '배치 시작');
  let failed = 0;

  for (const item of items) {
    try {
      await this.process(item);
      // 항목마다 로그 찍지 않는다 — 만 건이면 만 줄
    } catch (e) {
      failed++;
      this.logger.error({ itemId: item.id, err: e.message }, '항목 처리 실패');
    }
  }

  this.logger.info({ total: items.length, failed }, '배치 완료');
}
```

성공 건은 집계만 하고, 실패 건만 개별 로그를 남긴다. 이렇게만 해도 정상 흐름의 로그량이 수백 분의 일로 줄어든다.

샘플링을 넣을 때 주의할 점. correlation ID로 한 요청을 추적하는 중인데 그 요청의 일부 로그가 샘플링으로 빠지면 추적이 끊긴다. 그래서 샘플링은 "요청 단위"로 결정하는 게 맞다. 한 요청을 남기기로 했으면 그 요청의 모든 로그를 남기고, 버리기로 했으면 전부 버린다. 줄 단위로 무작위 샘플링하면 안 된다. `autoLogging.ignore`가 요청 단위로 동작하는 게 이래서 맞는 위치다.

## winston을 써야 하는 경우

pino를 권하지만 winston이 맞는 상황도 있다. 로그를 stdout이 아니라 파일로 직접 쓰고 일자별 로테이션을 해야 하거나(`winston-daily-rotate-file`), 여러 목적지로 동시에 보내야 하거나, 기존 코드베이스가 이미 winston으로 깔려 있을 때다. NestJS와는 `nest-winston`으로 붙인다.

```bash
npm install nest-winston winston
```

```ts
// app.module.ts
import { WinstonModule } from 'nest-winston';
import * as winston from 'winston';

@Module({
  imports: [
    WinstonModule.forRoot({
      level: process.env.LOG_LEVEL || 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json(), // JSON 구조화 출력
      ),
      transports: [new winston.transports.Console()],
    }),
  ],
})
export class AppModule {}
```

```ts
// main.ts
import { WINSTON_MODULE_NEST_PROVIDER } from 'nest-winston';

const app = await NestFactory.create(AppModule, { bufferLogs: true });
app.useLogger(app.get(WINSTON_MODULE_NEST_PROVIDER));
```

winston에서도 correlation ID 전파는 동일하게 `AsyncLocalStorage`로 한다. winston은 pino의 `mixin`에 해당하는 게 `format`이다. 커스텀 format에서 `getCorrelationId()`를 읽어 매 로그에 넣는다.

```ts
const correlationFormat = winston.format((info) => {
  const correlationId = getCorrelationId();
  if (correlationId) info.correlationId = correlationId;
  return info;
});

WinstonModule.forRoot({
  format: winston.format.combine(
    correlationFormat(),
    winston.format.timestamp(),
    winston.format.json(),
  ),
  // ...
});
```

마스킹은 pino의 `redact`처럼 깔끔한 내장 옵션이 없어서 custom format에서 직접 키를 찾아 치환하거나, 로깅 전에 마스킹 함수를 거치는 식으로 처리한다. 이 부분이 winston이 pino보다 손이 더 가는 지점이다.

winston을 쓸 때 성능 주의점. `winston.format.json()`과 transport 처리가 메인 스레드에서 돌기 때문에, 초당 수천 건 이상 로그가 나가는 서비스에서는 winston 자체가 latency를 올린다. 부하가 큰 서비스면 pino를, 로그량이 많지 않고 파일 로테이션 같은 기능이 필요하면 winston을 고르는 기준으로 보면 된다.

## 정리하며 챙길 것

내장 Logger는 개발용으로 두고, 운영 서비스는 pino(또는 winston)로 JSON 구조화 로깅을 한다. 값은 메시지 문자열에 끼우지 말고 필드로 분리해야 검색이 된다. correlation ID는 `AsyncLocalStorage`로 전파하면 메서드 시그니처를 오염시키지 않고 모든 로그에 자동으로 붙는다. 로그 레벨은 환경변수로 빼서 환경별로 분리하고, 운영에서 debug를 끄면 직렬화 비용까지 사라진다. 민감정보는 `redact`로 마스킹하되 애초에 바디 전체를 찍지 않는 게 더 안전하다. 트래픽이 커지면 헬스체크 제외 → 정상 요청 샘플링 → 애플리케이션 로그 집계 순으로 줄여나가되, 샘플링은 요청 단위로 결정해서 correlation 추적이 끊기지 않게 한다.
