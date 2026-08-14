---
title: NestJS gRPC 트랜스포트 심화
tags: [nodejs, grpc, messaging]
updated: 2026-07-10
---

# NestJS gRPC 트랜스포트 심화

마이크로서비스 문서에서 gRPC 개요를 다뤘다. 여기서는 proto 스키마 설계부터 스트리밍 패턴, 메타데이터 전달, HTTP 변환 에러 핸들링까지 실무에서 실제로 부딪히는 부분을 다룬다.

gRPC를 NestJS에서 처음 쓸 때 가장 많이 막히는 지점이 세 가지다. proto 파일 타입 매핑, `ClientGrpc`와 `ClientProxy`의 차이, 그리고 gRPC 에러 코드를 HTTP로 변환하는 방법이다.


## proto 파일 설계

### 기본 타입 매핑

proto3 타입과 TypeScript 타입이 항상 1:1로 대응하지 않는다. 특히 숫자 타입이 문제가 된다.

```protobuf
syntax = "proto3";

package hero;

// 서비스 정의
service HeroService {
  rpc FindOne (HeroById) returns (Hero);
  rpc FindMany (HeroFilter) returns (stream Hero);       // server streaming
  rpc CreateHero (stream CreateHeroRequest) returns (Hero); // client streaming
  rpc Chat (stream ChatMessage) returns (stream ChatMessage); // bidirectional
}

// 메시지 정의
message HeroById {
  string id = 1;
}

message HeroFilter {
  optional string name = 1;   // proto3에서 optional은 필드 존재 여부 감지 가능
  int32 limit = 2;
  int32 offset = 3;
}

message CreateHeroRequest {
  string name = 1;
  int32 power = 2;
}

message Hero {
  string id = 1;
  string name = 2;
  int32 power = 3;
  int64 created_at = 4;    // Unix timestamp (ms) — google.protobuf.Timestamp보다 단순함
  repeated string tags = 5; // 배열
  HeroStatus status = 6;    // enum
}

message ChatMessage {
  string hero_id = 1;
  string content = 2;
}

enum HeroStatus {
  HERO_STATUS_UNKNOWN = 0; // proto3에서 첫 번째 enum 값은 반드시 0
  HERO_STATUS_ACTIVE = 1;
  HERO_STATUS_RETIRED = 2;
}
```

proto3 타입별 JavaScript 변환 결과:

| proto3 타입 | JavaScript 타입 | 주의사항 |
|------------|----------------|---------|
| `string` | `string` | 없음 |
| `int32`, `uint32`, `sint32` | `number` | 32비트 정수 |
| `int64`, `uint64` | `string` | JS에서 64비트 정수를 안전하게 처리 못해서 문자열로 옴 |
| `float`, `double` | `number` | 없음 |
| `bool` | `boolean` | 없음 |
| `bytes` | `Buffer` | 없음 |
| `repeated T` | `T[]` | 없음 |
| `map<K, V>` | `Record<K, V>` | 없음 |
| `optional T` | `T \| undefined` | proto3.5+ |

`int64`가 문자열로 오는 건 처음에 꽤 당황스럽다. DB에서 `BigInt`로 저장된 값을 gRPC로 보낼 때 `.toString()` 해야 한다는 걸 잊기 쉽다.

### 패키지 구조

서비스가 여러 개면 패키지 구조를 잡는 게 중요하다. proto 파일은 가능하면 별도 레포나 모노레포의 공유 패키지로 관리한다.

```
proto/
├── hero/
│   └── hero.proto       # package hero
├── payment/
│   └── payment.proto    # package payment
└── common/
    └── types.proto      # 공통 메시지 타입
```

```protobuf
// common/types.proto
syntax = "proto3";

package common;

message Pagination {
  int32 page = 1;
  int32 size = 2;
}

message Empty {}
```

```protobuf
// hero/hero.proto
import "common/types.proto";

message HeroFilter {
  optional string name = 1;
  common.Pagination pagination = 2; // 다른 패키지 타입 참조
}
```

NestJS에서 여러 proto 파일을 쓸 때 `protoPath`를 배열로 전달한다.

```typescript
{
  transport: Transport.GRPC,
  options: {
    package: ['hero', 'common'],
    protoPath: [
      join(__dirname, './proto/hero/hero.proto'),
      join(__dirname, './proto/common/types.proto'),
    ],
    url: '0.0.0.0:5000',
  },
}
```

### 하위 호환성 유지

필드를 삭제하거나 번호를 바꾸면 호환성이 깨진다. proto3는 필드가 없으면 기본값으로 채워지기 때문에 서버가 먼저 배포되면 클라이언트는 새 필드를 그냥 무시한다. 클라이언트가 먼저 배포되면 서버는 모르는 필드를 무시한다. 둘 다 에러가 나지 않아서 데이터 불일치를 눈치채기 어렵다.

```protobuf
// 잘못된 방법 — 절대 하지 말아야 한다
message Hero {
  // string id = 1; ← 삭제하면 번호 1을 재사용할 수 없음
  // reserved 구문으로 재사용 금지 표시
  reserved 1;
  reserved "id";

  string uuid = 10;  // 새 필드는 새 번호로
  string name = 2;
}
```

필드를 실제로 지울 일이 생기면 `reserved` 구문으로 해당 번호를 봉인한다. 봉인하지 않으면 나중에 다른 팀에서 같은 번호를 재사용해 데이터가 꼬일 수 있다.


## 코드 생성

### 수동 타입 정의 방식

NestJS에서 gRPC를 쓸 때 공식 문서는 인터페이스를 직접 작성하는 방법을 소개한다. proto 파일에서 자동 생성하지 않는다.

```typescript
// interfaces/hero.interface.ts
import { Observable } from 'rxjs';
import { Metadata } from '@grpc/grpc-js';

export interface HeroById {
  id: string;
}

export interface HeroFilter {
  name?: string;
  limit?: number;
  offset?: number;
}

export interface Hero {
  id: string;
  name: string;
  power: number;
  createdAt: string;  // int64는 문자열로 옴
  tags: string[];
  status: number;     // enum은 숫자로 옴
}

// 클라이언트에서 쓸 인터페이스 — proto의 service 정의와 1:1 매핑
export interface HeroServiceClient {
  findOne(data: HeroById, metadata?: Metadata): Observable<Hero>;
  findMany(data: HeroFilter, metadata?: Metadata): Observable<Hero>;  // server streaming
  createHero(data: Observable<CreateHeroRequest>, metadata?: Metadata): Observable<Hero>; // client streaming
  chat(data: Observable<ChatMessage>, metadata?: Metadata): Observable<ChatMessage>; // bidirectional
}
```

### proto-loader-gen-types로 자동 생성

수동으로 인터페이스를 유지하는 건 proto 파일이 많아지면 금방 한계에 온다. `proto-loader-gen-types`를 쓰면 타입 파일을 자동 생성할 수 있다.

```bash
npm install -D grpc-tools grpc_tools_node_protoc_ts
npm install @grpc/grpc-js @grpc/proto-loader
```

```bash
# 타입 생성 스크립트
npx proto-loader-gen-types \
  --longs=String \
  --enums=String \
  --defaults \
  --oneofs \
  --grpcLib=@grpc/grpc-js \
  --outDir=src/proto-types \
  proto/**/*.proto
```

`package.json`에 스크립트로 등록해두면 proto 파일이 바뀔 때마다 실행할 수 있다.

```json
{
  "scripts": {
    "proto:gen": "npx proto-loader-gen-types --longs=String --enums=String --defaults --oneofs --grpcLib=@grpc/grpc-js --outDir=src/proto-types proto/**/*.proto"
  }
}
```

`buf`를 쓰면 proto 파일 린팅과 브레이킹 체인지 감지도 같이 할 수 있다. 팀이 커지면 `buf.yaml`과 `buf.gen.yaml`로 코드 생성 파이프라인을 관리하는 게 낫다.


## 단방향 RPC (Unary)

단방향이 가장 기본이다. 일반 HTTP 요청-응답과 같은 구조다.

### 서버 측 구현

```typescript
// hero.controller.ts
import { Controller } from '@nestjs/common';
import { GrpcMethod } from '@nestjs/microservices';
import { Metadata, ServerUnaryCall } from '@grpc/grpc-js';
import { HeroService } from './hero.service';
import { HeroById, Hero } from './interfaces/hero.interface';

@Controller()
export class HeroController {
  constructor(private readonly heroService: HeroService) {}

  @GrpcMethod('HeroService', 'FindOne')
  async findOne(
    data: HeroById,
    metadata: Metadata,
    call: ServerUnaryCall<HeroById, Hero>,
  ): Promise<Hero> {
    // metadata에서 인증 토큰이나 트레이싱 헤더를 꺼낸다
    const authToken = metadata.get('authorization')[0] as string;

    const hero = await this.heroService.findById(data.id);
    if (!hero) {
      // gRPC 에러는 아래 에러 핸들링 섹션에서 자세히 다룬다
      throw new RpcException({
        code: Status.NOT_FOUND,
        message: `Hero ${data.id} not found`,
      });
    }
    return hero;
  }
}
```

`@GrpcMethod`의 두 번째 인자(메서드 이름)를 생략하면 핸들러 메서드 이름을 PascalCase로 변환해서 매칭한다. `findOne` → `FindOne`. 이름이 정확히 맞아야 하기 때문에, 명시적으로 적어두는 게 실수를 줄인다.

### 클라이언트 측 구현

```typescript
// payment.module.ts
import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { join } from 'path';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'HERO_PACKAGE',
        transport: Transport.GRPC,
        options: {
          package: 'hero',
          protoPath: join(__dirname, '../proto/hero/hero.proto'),
          url: 'hero-service:5000',
          // TLS 설정 (프로덕션)
          // credentials: ChannelCredentials.createSsl(
          //   rootCerts,
          //   privateKey,
          //   certChain,
          // ),
        },
      },
    ]),
  ],
})
export class PaymentModule {}
```

```typescript
// payment.service.ts
import { Injectable, OnModuleInit } from '@nestjs/common';
import { Client, ClientGrpc } from '@nestjs/microservices';
import { Inject } from '@nestjs/common';
import { lastValueFrom } from 'rxjs';
import { Metadata } from '@grpc/grpc-js';
import { HeroServiceClient } from './interfaces/hero.interface';

@Injectable()
export class PaymentService implements OnModuleInit {
  private heroService: HeroServiceClient;

  constructor(
    @Inject('HERO_PACKAGE') private readonly client: ClientGrpc,
  ) {}

  onModuleInit() {
    // ClientGrpc.getService()로 proto에 정의된 서비스 스텁을 가져온다.
    // ClientProxy와 달리 ClientGrpc는 getService()를 명시적으로 호출해야 한다.
    this.heroService = this.client.getService<HeroServiceClient>('HeroService');
  }

  async findHero(heroId: string, requesterId: string): Promise<Hero> {
    // 메타데이터 전달이 필요한 경우
    const metadata = new Metadata();
    metadata.add('x-requester-id', requesterId);

    return lastValueFrom(
      this.heroService.findOne({ id: heroId }, metadata),
    );
  }
}
```

`ClientGrpc`와 `ClientProxy`를 혼동하는 경우가 많다. TCP나 Redis 트랜스포트는 `ClientProxy`를 쓰고 `send()`로 호출한다. gRPC는 `ClientGrpc`를 쓰고 `getService()`로 서비스 스텁을 가져온 다음 메서드를 직접 호출한다. 주입 방식이 다르다.

### 동적 ClientGrpc 주입

설정을 런타임에 결정해야 할 때는 `ClientProxyFactory`를 직접 쓴다.

```typescript
import { ClientProxyFactory, Transport } from '@nestjs/microservices';

@Injectable()
export class GrpcClientFactory {
  createHeroClient(serviceUrl: string): ClientGrpc {
    return ClientProxyFactory.create({
      transport: Transport.GRPC,
      options: {
        package: 'hero',
        protoPath: join(__dirname, '../proto/hero/hero.proto'),
        url: serviceUrl,
      },
    }) as unknown as ClientGrpc;
  }
}
```


## 서버 스트리밍

서버가 클라이언트 요청 하나에 여러 응답을 순차적으로 보내는 패턴이다. 대량 데이터 조회나 실시간 피드에 쓴다.

### 서버 측

```typescript
import { GrpcStreamCall } from '@nestjs/microservices';
import { ServerWritableStream } from '@grpc/grpc-js';
import { Subject, from } from 'rxjs';

@Controller()
export class HeroController {
  // Observable을 리턴하는 방식
  @GrpcMethod('HeroService', 'FindMany')
  findMany(data: HeroFilter): Observable<Hero> {
    // from()으로 배열이나 Promise를 Observable로 변환
    return from(this.heroService.findByFilter(data));
  }

  // 스트림을 직접 제어해야 할 때 — @GrpcStreamCall 사용
  @GrpcStreamCall('HeroService', 'FindMany')
  findManyStream(
    call: ServerWritableStream<HeroFilter, Hero>,
  ): void {
    const filter = call.request;

    this.heroService
      .findByFilterCursor(filter) // DB 커서
      .on('data', (hero: Hero) => {
        call.write(hero); // 한 건씩 스트림으로 전송
      })
      .on('end', () => {
        call.end(); // 스트림 종료
      })
      .on('error', (err) => {
        call.destroy(err);
      });
  }
}
```

`@GrpcMethod`에서 `Observable`을 리턴하는 방식이 더 간단하지만, DB 커서처럼 스트림을 직접 제어해야 할 때는 `@GrpcStreamCall`로 `call` 객체를 직접 다루는 게 낫다.

### 클라이언트 측

```typescript
async streamHeroes(filter: HeroFilter): Promise<Hero[]> {
  // server streaming도 Observable로 온다
  const heroes: Hero[] = [];

  return new Promise((resolve, reject) => {
    this.heroService.findMany(filter).subscribe({
      next: (hero) => heroes.push(hero),
      error: (err) => reject(err),
      complete: () => resolve(heroes),
    });
  });
}

// 스트림을 그대로 클라이언트에 전달해야 하는 경우
streamHeroesPassthrough(filter: HeroFilter): Observable<Hero> {
  return this.heroService.findMany(filter);
}
```


## 클라이언트 스트리밍

클라이언트가 여러 메시지를 보내고 서버가 처리 완료 후 하나의 응답을 돌려준다. 파일 업로드, 배치 처리에 쓴다.

### 서버 측

```typescript
@Controller()
export class HeroController {
  @GrpcStreamCall('HeroService', 'CreateHero')
  async createHeroStream(
    call: ServerReadableStream<CreateHeroRequest, Hero>,
    callback: sendUnaryData<Hero>,
  ): Promise<void> {
    const requests: CreateHeroRequest[] = [];

    call.on('data', (req: CreateHeroRequest) => {
      requests.push(req);
    });

    call.on('end', async () => {
      try {
        // 모든 요청을 받은 후 처리
        const hero = await this.heroService.createBatch(requests);
        callback(null, hero); // 단일 응답
      } catch (err) {
        callback(err, null);
      }
    });
  }
}
```

### 클라이언트 측

NestJS의 `ClientGrpc`에서 클라이언트 스트리밍을 호출할 때는 `Observable`을 인자로 넘긴다.

```typescript
async createHeroesBatch(requests: CreateHeroRequest[]): Promise<Hero> {
  const subject = new Subject<CreateHeroRequest>();

  const result$ = this.heroService.createHero(subject.asObservable());

  // 메시지를 순차적으로 emit
  for (const req of requests) {
    subject.next(req);
    // 필요하면 await로 백프레셔 처리
  }
  subject.complete(); // 스트림 종료 신호

  return lastValueFrom(result$);
}
```


## 양방향 스트리밍

클라이언트와 서버가 동시에 스트림을 주고받는다. 채팅, 실시간 게임 상태 동기화 같은 곳에 쓴다.

### 서버 측

```typescript
@Controller()
export class HeroController {
  @GrpcStreamCall('HeroService', 'Chat')
  chatStream(
    call: ServerDuplexStream<ChatMessage, ChatMessage>,
  ): void {
    call.on('data', (message: ChatMessage) => {
      // 받은 메시지를 처리하고 응답
      const reply: ChatMessage = {
        heroId: 'server',
        content: `Echo: ${message.content}`,
      };
      call.write(reply);
    });

    call.on('end', () => {
      call.end();
    });
  }
}
```

### 클라이언트 측

```typescript
async startChat(): Promise<void> {
  const subject = new Subject<ChatMessage>();

  const replies$ = this.heroService.chat(subject.asObservable());

  // 수신 구독
  replies$.subscribe({
    next: (reply) => console.log('받은 메시지:', reply.content),
    error: (err) => console.error(err),
    complete: () => console.log('스트림 종료'),
  });

  // 메시지 전송
  subject.next({ heroId: 'client-1', content: '안녕' });

  // 2초 후 추가 메시지
  await setTimeout(2000);
  subject.next({ heroId: 'client-1', content: '또 안녕' });

  // 스트림 종료
  subject.complete();
}
```

NestJS에서 양방향 스트리밍은 실제로 쓰기 까다롭다. `@grpc/grpc-js`의 저수준 API를 직접 다뤄야 하는 경우가 많고, RxJS Subject로 스트림을 브리지하는 과정에서 에러 핸들링이 복잡해진다. 단순한 양방향 통신이라면 WebSocket을 쓰는 게 더 나을 수 있다.


## 메타데이터 전달

gRPC 메타데이터는 HTTP 헤더와 같은 역할을 한다. 인증 토큰, 트레이싱 ID, 테넌트 ID 등을 메타데이터로 전달한다.

### 클라이언트에서 메타데이터 전송

```typescript
import { Metadata } from '@grpc/grpc-js';

async findHero(heroId: string, token: string): Promise<Hero> {
  const metadata = new Metadata();
  metadata.add('authorization', `Bearer ${token}`);
  metadata.add('x-trace-id', generateTraceId());
  metadata.add('x-tenant-id', this.tenantId);

  return lastValueFrom(
    this.heroService.findOne({ id: heroId }, metadata),
  );
}
```

### 서버에서 메타데이터 수신

```typescript
@GrpcMethod('HeroService', 'FindOne')
async findOne(data: HeroById, metadata: Metadata): Promise<Hero> {
  const authHeader = metadata.get('authorization');
  if (!authHeader.length) {
    throw new RpcException({
      code: Status.UNAUTHENTICATED,
      message: 'Missing authorization header',
    });
  }

  const token = (authHeader[0] as string).replace('Bearer ', '');
  const user = await this.authService.validateToken(token);

  return this.heroService.findById(data.id, user.id);
}
```

### 서버에서 메타데이터 응답으로 전송

서버도 클라이언트에게 메타데이터를 보낼 수 있다. 주로 응답 헤더로 트레이싱 정보나 페이지네이션 커서를 전달할 때 쓴다.

```typescript
@GrpcMethod('HeroService', 'FindOne')
async findOne(
  data: HeroById,
  metadata: Metadata,
  call: ServerUnaryCall<HeroById, Hero>,
): Promise<Hero> {
  // 응답 메타데이터 전송
  const responseMetadata = new Metadata();
  responseMetadata.add('x-request-id', uuid());
  call.sendMetadata(responseMetadata);

  return this.heroService.findById(data.id);
}
```

### 인터셉터로 메타데이터 처리

서비스마다 메타데이터 추출 코드를 반복하지 않으려면 인터셉터로 공통 처리한다.

```typescript
// grpc-metadata.interceptor.ts
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { Metadata } from '@grpc/grpc-js';

@Injectable()
export class GrpcMetadataInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    // gRPC 컨텍스트에서만 실행
    if (context.getType() !== 'rpc') {
      return next.handle();
    }

    const metadata: Metadata = context.switchToRpc().getContext();
    const traceId = metadata.get('x-trace-id')[0] as string;

    // AsyncLocalStorage나 cls-hooked로 트레이스 ID를 요청 컨텍스트에 저장
    this.traceContext.set(traceId || generateTraceId());

    return next.handle();
  }
}
```

gRPC 컨텍스트에서 `switchToRpc().getContext()`가 리턴하는 게 `Metadata` 객체다. HTTP에서 `switchToHttp().getRequest()`로 요청 객체를 꺼내는 것과 같다.


## 에러 핸들링

### gRPC Status 코드

gRPC는 HTTP 상태 코드 대신 자체 상태 코드를 쓴다.

| gRPC Status | 코드 | 대응 HTTP 상태 |
|------------|------|--------------|
| OK | 0 | 200 |
| CANCELLED | 1 | 499 |
| UNKNOWN | 2 | 500 |
| INVALID_ARGUMENT | 3 | 400 |
| DEADLINE_EXCEEDED | 4 | 504 |
| NOT_FOUND | 5 | 404 |
| ALREADY_EXISTS | 6 | 409 |
| PERMISSION_DENIED | 7 | 403 |
| RESOURCE_EXHAUSTED | 8 | 429 |
| FAILED_PRECONDITION | 9 | 400 |
| ABORTED | 10 | 409 |
| UNIMPLEMENTED | 12 | 501 |
| INTERNAL | 13 | 500 |
| UNAVAILABLE | 14 | 503 |
| UNAUTHENTICATED | 16 | 401 |

### 서버에서 gRPC 에러 던지기

```typescript
import { status as Status } from '@grpc/grpc-js';
import { RpcException } from '@nestjs/microservices';

@GrpcMethod('HeroService', 'FindOne')
async findOne(data: HeroById): Promise<Hero> {
  if (!data.id) {
    throw new RpcException({
      code: Status.INVALID_ARGUMENT,
      message: 'Hero ID is required',
    });
  }

  const hero = await this.heroService.findById(data.id);
  if (!hero) {
    throw new RpcException({
      code: Status.NOT_FOUND,
      message: `Hero ${data.id} not found`,
    });
  }

  return hero;
}
```

`RpcException`에 `code`를 넣지 않으면 `INTERNAL` (13)으로 처리된다. 클라이언트에서 에러 종류를 구분할 수 없게 되므로, 항상 적절한 코드를 지정한다.

### gRPC Exception Filter

서버에서 발생한 에러를 일관되게 처리하는 필터를 만든다.

```typescript
// grpc-exception.filter.ts
import { Catch, RpcExceptionFilter, ArgumentsHost } from '@nestjs/common';
import { Observable, throwError } from 'rxjs';
import { RpcException } from '@nestjs/microservices';
import { status as Status } from '@grpc/grpc-js';

interface GrpcError {
  code: number;
  message: string;
  details?: string;
}

@Catch(RpcException)
export class GrpcExceptionFilter implements RpcExceptionFilter<RpcException> {
  catch(exception: RpcException, host: ArgumentsHost): Observable<never> {
    const error = exception.getError() as GrpcError | string;

    if (typeof error === 'string') {
      return throwError(() => ({
        code: Status.INTERNAL,
        message: error,
      }));
    }

    return throwError(() => ({
      code: error.code ?? Status.INTERNAL,
      message: error.message,
      details: error.details,
    }));
  }
}

// main.ts 또는 컨트롤러에서 등록
app.useGlobalFilters(new GrpcExceptionFilter());
```

### gRPC 에러를 HTTP 상태 코드로 변환

API 게이트웨이 역할을 하는 NestJS 서비스가 내부 gRPC 에러를 HTTP 응답으로 변환해야 할 때 쓴다.

```typescript
// grpc-to-http-exception.filter.ts
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpStatus,
} from '@nestjs/common';
import { Response } from 'express';
import { status as GrpcStatus } from '@grpc/grpc-js';

const GRPC_TO_HTTP: Record<number, number> = {
  [GrpcStatus.OK]: HttpStatus.OK,
  [GrpcStatus.INVALID_ARGUMENT]: HttpStatus.BAD_REQUEST,
  [GrpcStatus.NOT_FOUND]: HttpStatus.NOT_FOUND,
  [GrpcStatus.ALREADY_EXISTS]: HttpStatus.CONFLICT,
  [GrpcStatus.PERMISSION_DENIED]: HttpStatus.FORBIDDEN,
  [GrpcStatus.UNAUTHENTICATED]: HttpStatus.UNAUTHORIZED,
  [GrpcStatus.RESOURCE_EXHAUSTED]: HttpStatus.TOO_MANY_REQUESTS,
  [GrpcStatus.FAILED_PRECONDITION]: HttpStatus.BAD_REQUEST,
  [GrpcStatus.UNIMPLEMENTED]: HttpStatus.NOT_IMPLEMENTED,
  [GrpcStatus.INTERNAL]: HttpStatus.INTERNAL_SERVER_ERROR,
  [GrpcStatus.UNAVAILABLE]: HttpStatus.SERVICE_UNAVAILABLE,
  [GrpcStatus.DEADLINE_EXCEEDED]: HttpStatus.GATEWAY_TIMEOUT,
};

interface GrpcError {
  code: number;
  message: string;
  details?: string;
}

@Catch()
export class GrpcToHttpExceptionFilter implements ExceptionFilter {
  catch(error: any, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    // gRPC 에러는 code 필드를 가지고 있다
    const grpcError = error as GrpcError;
    const httpStatus =
      GRPC_TO_HTTP[grpcError.code] ?? HttpStatus.INTERNAL_SERVER_ERROR;

    response.status(httpStatus).json({
      statusCode: httpStatus,
      message: grpcError.message ?? 'Internal server error',
      grpcCode: grpcError.code,
    });
  }
}
```

```typescript
// api-gateway.controller.ts
@Controller('heroes')
@UseFilters(new GrpcToHttpExceptionFilter())
export class HeroController {
  @Get(':id')
  async findOne(@Param('id') id: string): Promise<Hero> {
    // gRPC 에러가 발생하면 GrpcToHttpExceptionFilter가 HTTP 응답으로 변환
    return this.heroService.findHero(id);
  }
}
```

필터를 컨트롤러 단위로 적용하는 게 낫다. 전역으로 달면 일반 HTTP 에러까지 영향을 받는다.


## 실제 서비스 간 호출 예제

주문 서비스(Order Service)가 재고 서비스(Inventory Service)를 gRPC로 호출하는 예제다.

### proto 정의

```protobuf
// proto/inventory/inventory.proto
syntax = "proto3";

package inventory;

service InventoryService {
  rpc CheckStock (CheckStockRequest) returns (StockStatus);
  rpc ReserveStock (ReserveRequest) returns (ReserveResult);
  rpc ReleaseStock (ReleaseRequest) returns (ReleaseResult);
}

message CheckStockRequest {
  string product_id = 1;
  int32 quantity = 2;
}

message StockStatus {
  string product_id = 1;
  bool available = 2;
  int32 current_stock = 3;
}

message ReserveRequest {
  string order_id = 1;
  string product_id = 2;
  int32 quantity = 3;
}

message ReserveResult {
  bool success = 1;
  string reservation_id = 2;
  string message = 3;
}

message ReleaseRequest {
  string reservation_id = 1;
}

message ReleaseResult {
  bool success = 1;
}
```

### Inventory Service (서버)

```typescript
// inventory/inventory.controller.ts
import { Controller } from '@nestjs/common';
import { GrpcMethod } from '@nestjs/microservices';
import { status as Status } from '@grpc/grpc-js';
import { RpcException } from '@nestjs/microservices';

@Controller()
export class InventoryController {
  constructor(private readonly inventoryService: InventoryService) {}

  @GrpcMethod('InventoryService', 'CheckStock')
  async checkStock(data: CheckStockRequest): Promise<StockStatus> {
    const stock = await this.inventoryService.getStock(data.productId);

    return {
      productId: data.productId,
      available: stock >= data.quantity,
      currentStock: stock,
    };
  }

  @GrpcMethod('InventoryService', 'ReserveStock')
  async reserveStock(data: ReserveRequest): Promise<ReserveResult> {
    const stock = await this.inventoryService.getStock(data.productId);

    if (stock < data.quantity) {
      throw new RpcException({
        code: Status.FAILED_PRECONDITION,
        message: `Insufficient stock: ${stock} < ${data.quantity}`,
      });
    }

    const reservationId = await this.inventoryService.reserve(
      data.orderId,
      data.productId,
      data.quantity,
    );

    return { success: true, reservationId, message: 'Reserved successfully' };
  }

  @GrpcMethod('InventoryService', 'ReleaseStock')
  async releaseStock(data: ReleaseRequest): Promise<ReleaseResult> {
    await this.inventoryService.release(data.reservationId);
    return { success: true };
  }
}
```

```typescript
// inventory/main.ts
async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    InventoryModule,
    {
      transport: Transport.GRPC,
      options: {
        package: 'inventory',
        protoPath: join(__dirname, '../proto/inventory/inventory.proto'),
        url: '0.0.0.0:5001',
      },
    },
  );
  app.useGlobalFilters(new GrpcExceptionFilter());
  await app.listen();
}
bootstrap();
```

### Order Service (클라이언트)

```typescript
// order/order.module.ts
@Module({
  imports: [
    ClientsModule.registerAsync([
      {
        name: 'INVENTORY_PACKAGE',
        useFactory: (configService: ConfigService) => ({
          transport: Transport.GRPC,
          options: {
            package: 'inventory',
            protoPath: join(__dirname, '../proto/inventory/inventory.proto'),
            url: configService.get('INVENTORY_SERVICE_URL'),
          },
        }),
        inject: [ConfigService],
      },
    ]),
  ],
})
export class OrderModule {}
```

```typescript
// order/order.service.ts
@Injectable()
export class OrderService implements OnModuleInit {
  private inventoryService: InventoryServiceClient;

  constructor(
    @Inject('INVENTORY_PACKAGE') private readonly client: ClientGrpc,
    private readonly orderRepository: OrderRepository,
  ) {}

  onModuleInit() {
    this.inventoryService =
      this.client.getService<InventoryServiceClient>('InventoryService');
  }

  async createOrder(dto: CreateOrderDto, userId: string): Promise<Order> {
    // 1. 재고 확인
    const stockStatus = await lastValueFrom(
      this.inventoryService.checkStock({
        productId: dto.productId,
        quantity: dto.quantity,
      }),
    );

    if (!stockStatus.available) {
      throw new BadRequestException(
        `Insufficient stock: ${stockStatus.currentStock} available`,
      );
    }

    // 2. 주문 생성
    const order = await this.orderRepository.create({
      userId,
      productId: dto.productId,
      quantity: dto.quantity,
      status: 'PENDING',
    });

    // 3. 재고 예약
    let reservationId: string;
    try {
      const reserveResult = await lastValueFrom(
        this.inventoryService.reserveStock({
          orderId: order.id,
          productId: dto.productId,
          quantity: dto.quantity,
        }),
      );
      reservationId = reserveResult.reservationId;
    } catch (err) {
      // gRPC FAILED_PRECONDITION이면 경쟁 조건으로 재고 부족
      await this.orderRepository.updateStatus(order.id, 'FAILED');
      throw new ConflictException('Stock reservation failed. Try again.');
    }

    // 4. 주문 확정
    await this.orderRepository.update(order.id, {
      status: 'CONFIRMED',
      reservationId,
    });

    return this.orderRepository.findById(order.id);
  }
}
```

### nest-cli.json proto 파일 복사 설정

빌드 결과물에 proto 파일이 포함되지 않으면 프로덕션 배포 후 gRPC 서버가 뜨지 않는다.

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true,
    "assets": [
      {
        "include": "**/*.proto",
        "watchAssets": true
      }
    ]
  }
}
```

`watchAssets: true`를 설정하면 개발 모드(`nest start --watch`)에서 proto 파일이 바뀌면 자동으로 복사된다.


## 실무에서 자주 겪는 문제

### getService()를 OnModuleInit 밖에서 호출하면 빈 객체가 온다

```typescript
@Injectable()
export class OrderService {
  // 이렇게 하면 안 된다
  private heroService = this.client.getService<HeroServiceClient>('HeroService');

  constructor(@Inject('HERO_PACKAGE') private readonly client: ClientGrpc) {}
}
```

`ClientGrpc`는 모듈 초기화가 완료된 후에야 준비된다. 생성자에서 `getService()`를 호출하면 gRPC 채널이 아직 없는 상태라 빈 객체가 반환된다. 반드시 `OnModuleInit`에서 호출한다.

### snake_case vs camelCase

proto 파일에서 `product_id`로 정의하면, `@grpc/proto-loader`가 기본적으로 camelCase(`productId`)로 변환한다. 서버에서 보낸 `product_id`가 클라이언트에서 `productId`로 받아진다. 혼용하면 `undefined`가 나오므로 주의한다.

```typescript
// proto-loader 옵션에서 camelCase 변환 끄는 방법
{
  transport: Transport.GRPC,
  options: {
    package: 'hero',
    protoPath: '...',
    loader: {
      keepCase: true, // snake_case 유지
    },
  },
}
```

팀 컨벤션에 따라 선택하되, 한쪽으로 통일한다.

### 타임아웃

gRPC 클라이언트 호출은 기본 타임아웃이 없다. 서버가 응답하지 않으면 무한 대기한다.

```typescript
import { timeout } from 'rxjs/operators';

async findHero(heroId: string): Promise<Hero> {
  return lastValueFrom(
    this.heroService.findOne({ id: heroId }).pipe(
      timeout(3000), // 3초
    ),
  );
}
```

또는 메타데이터로 데드라인을 설정한다.

```typescript
import { Metadata } from '@grpc/grpc-js';

async findHero(heroId: string): Promise<Hero> {
  const metadata = new Metadata();
  // 현재 시각 + 3초를 데드라인으로 설정
  const deadline = new Date(Date.now() + 3000);
  metadata.set('deadline', deadline.toISOString());

  return lastValueFrom(
    this.heroService.findOne({ id: heroId }, metadata),
  );
}
```

서비스 간 호출 체인이 길면 각 호출마다 타임아웃을 설정한다. 상위 서비스의 타임아웃보다 하위 서비스의 타임아웃이 짧아야 상위에서 의미 있는 에러 처리가 가능하다.

### 리플렉션과 grpcurl

개발 중에 gRPC 서버가 제대로 응답하는지 확인할 때 `grpcurl`을 쓴다. NestJS gRPC 서버에 리플렉션 서비스를 붙이면 proto 파일 없이도 서버의 서비스 목록과 메서드를 조회할 수 있다.

```bash
# 서비스 목록 조회
grpcurl -plaintext localhost:5000 list

# 특정 서비스의 메서드 조회
grpcurl -plaintext localhost:5000 list hero.HeroService

# 메서드 호출
grpcurl -plaintext -d '{"id": "1"}' localhost:5000 hero.HeroService/FindOne
```

NestJS에서 gRPC 리플렉션을 활성화하려면 `@grpc/reflection` 패키지를 써야 한다. NestJS 내장 gRPC 모듈이 직접 지원하지 않아서 별도 설정이 필요하다.


## 실측으로 바로잡는 부분

아래는 `@grpc/grpc-js` 1.14.4 + `@grpc/proto-loader` 0.8.1로 실제 서버와 클라이언트를 띄워 확인한 것이다.

### 데드라인은 메타데이터로 설정되지 않는다

위 "타임아웃" 절의 두 번째 방법은 동작하지 않는다. 서버가 3초 지연하도록 만들어 두고, 500ms 데드라인을 두 방식으로 걸어봤다.

```
metadata.set('deadline')  →  3015ms 걸림, 에러 없음, 응답 정상 수신
options.deadline          →   501ms 만에 DEADLINE_EXCEEDED(4)
```

`Metadata`는 HTTP/2 헤더에 그대로 실리는 키-값일 뿐이다. `deadline`이라는 이름을 붙여도 gRPC 런타임은 그걸 데드라인으로 해석하지 않는다. 그냥 `deadline`이라는 이름의 헤더 하나가 서버로 전달될 뿐이고, **타임아웃은 전혀 걸리지 않는다.** 데드라인은 메타데이터가 아니라 호출 옵션(`CallOptions`)이다.

```javascript
client.FindOne({ id: '1' }, metadata, { deadline: Date.now() + 3000 }, cb);
```

NestJS의 `ClientGrpc.getService()`가 만들어 주는 스텁은 `(request, metadata, options)` 형태로 인자를 받는다. 세 번째 자리에 옵션을 넘긴다.

```typescript
return lastValueFrom(
  this.heroService.findOne({ id: heroId }, metadata, { deadline: Date.now() + 3000 }),
);
```

앞에 나온 RxJS `timeout(3000)`과는 성격이 다르다. `timeout()`은 **클라이언트 쪽에서 구독을 끊을 뿐** 서버는 계속 일한다. `deadline`은 gRPC 프로토콜 차원의 취소라 서버 핸들러의 `call.cancelled`가 켜지고, 그 서버가 또 다른 서비스를 부르고 있었다면 데드라인이 그 호출까지 전파된다. 호출 체인이 길면 이 차이가 크다. 둘 다 걸어두되 데드라인을 주 수단으로 삼는다.

### 기본 설정에서 `int64`는 문자열이 아니라 `Long` 객체다

타입 매핑 표는 `int64` → `string`이라고 적고 있는데, 그건 `longs: String`을 지정했을 때다. 같은 값을 옵션만 바꿔가며 받아봤다.

```
기본(옵션 없음)   => {"low":1,"high":2097152,"unsigned":false}   typeof object, ctor Long
longs: String    => "9007199254740993"                          typeof string
longs: Number    => 9007199254740992                            typeof number  ← 값이 바뀌었다
```

기본값으로 두면 응답 객체에 `Long` 인스턴스가 들어간다. 그대로 `JSON.stringify` 하면 `{"low":...,"high":...}`가 API 응답으로 나간다. `longs: Number`는 더 나쁘다 — `9007199254740993`이 `9007199254740992`로 조용히 바뀐다(`Number.MAX_SAFE_INTEGER`가 `9007199254740991`이다).

그리고 NestJS는 `loader` 옵션에 기본값을 채워주지 않는다. `@nestjs/microservices` 11.1.29의 `helpers/grpc-helpers.js:16`을 보면 `loadSync(file, options['loader'])`로 받은 값을 그대로 넘긴다. **`loader`를 안 적으면 proto-loader 기본값이 적용된다.** 명시하는 편이 안전하다.

```typescript
options: {
  package: 'hero',
  protoPath: '...',
  loader: { longs: String, enums: String, defaults: true, oneofs: true, keepCase: false },
}
```

`enums`도 같다. 인터페이스에 `status: number`라고 적어뒀지만 `enums: String`을 주면 문자열로 온다. 코드 생성 스크립트에는 `--enums=String`을 쓰고 런타임 loader에는 안 적으면 **생성된 타입과 실제 값이 어긋난다.** 두 곳의 옵션을 같은 값으로 맞춘다.

### snake_case로 응답을 채우면 필드가 조용히 사라진다

"snake_case vs camelCase" 절의 경고가 실제로 어떻게 나타나는지 확인했다. proto에 `int64 created_at = 4;`로 정의하고, 서버 핸들러가 `created_at`이라는 키로 값을 채웠다.

```
서버가 보낸 객체: { id: '1', name: 'n', created_at: '12345' }
클라이언트 수신 : {"id":"1","name":"n"}
```

**에러가 나지 않는다.** `keepCase: false`(기본값)에서 직렬화기가 찾는 키는 `createdAt`이라, `created_at`은 그냥 모르는 속성으로 무시된다. 필드가 빠진 채로 전송되고 수신 측에서는 `undefined`가 된다. 서버 코드에서 오타 하나로 필드가 통째로 사라져도 아무도 알려주지 않는다는 뜻이다.

proto 정의는 snake_case로 쓰고 **JS 코드에서는 항상 camelCase로 다룬다.** 팀이 `keepCase: true`를 택했다면 반대로 전부 snake_case로 통일한다. 어느 쪽이든 응답 DTO에 필수 필드가 채워졌는지 확인하는 테스트가 있어야 이 부류가 잡힌다.

### 상태 코드 표에 두 개가 빠졌다

`@grpc/grpc-js`의 `status` enum을 그대로 찍으면 17개다.

```
0=OK 1=CANCELLED 2=UNKNOWN 3=INVALID_ARGUMENT 4=DEADLINE_EXCEEDED 5=NOT_FOUND
6=ALREADY_EXISTS 7=PERMISSION_DENIED 8=RESOURCE_EXHAUSTED 9=FAILED_PRECONDITION
10=ABORTED 11=OUT_OF_RANGE 12=UNIMPLEMENTED 13=INTERNAL 14=UNAVAILABLE
15=DATA_LOSS 16=UNAUTHENTICATED
```

위 표에는 `11=OUT_OF_RANGE`와 `15=DATA_LOSS`가 없다. `GRPC_TO_HTTP` 매핑에도 빠져 있어서 두 코드는 500으로 떨어진다. `OUT_OF_RANGE`는 페이지네이션 범위 초과에 쓰이므로 400 쪽이 맞다.

### `@Catch()`가 HTTP 예외까지 잡아서 전부 500으로 만든다

`GrpcToHttpExceptionFilter`는 `@Catch()`를 인자 없이 선언했다. 이러면 **모든 예외**를 잡는다. 그런데 `catch()`는 `error.code`로만 매핑을 찾는다. NestJS의 `HttpException`에는 `code`가 없다.

```
gRPC NOT_FOUND        → HTTP 404
NestJS BadRequest     → HTTP 500   (원래 의도: 400)
NestJS NotFound       → HTTP 500   (원래 의도: 404)
Node ECONNREFUSED     → HTTP 500
```

이 필터를 붙인 컨트롤러에서는 `ValidationPipe`가 던지는 400도, 직접 던진 `NotFoundException`도 전부 500이 된다. 클라이언트는 자기 요청이 잘못된 건지 서버가 죽은 건지 구분할 수 없고, 500이 늘어나니 알림도 오작동한다. 문서가 "전역으로 달면 일반 HTTP 에러까지 영향을 받는다"고 적어뒀는데, **컨트롤러 단위로 달아도 그 컨트롤러 안에서는 똑같이 발생한다.**

`HttpException`을 먼저 걸러낸다.

```typescript
catch(error: any, host: ArgumentsHost): void {
  const response = host.switchToHttp().getResponse<Response>();

  if (error instanceof HttpException) {
    const status = error.getStatus();
    response.status(status).json(error.getResponse());
    return;
  }

  const httpStatus = GRPC_TO_HTTP[error?.code] ?? HttpStatus.INTERNAL_SERVER_ERROR;
  response.status(httpStatus).json({ statusCode: httpStatus, message: error?.message ?? 'Internal server error' });
}
```

`grpcCode`를 응답 본문에 그대로 실어 보내는 것도 다시 볼 만하다. 내부 서비스 구조를 외부에 알려주는 값이라, 게이트웨이 응답에는 빼고 로그에만 남기는 쪽이 낫다.

### 기본 수신 한도는 4MB — 넘으면 `RESOURCE_EXHAUSTED`

응답 본문이 커지면 어느 날 갑자기 실패한다. 5MB짜리 문자열을 담아 보내봤다.

```
code=8 (RESOURCE_EXHAUSTED)
Received message larger than max (5242893 vs 4194304)
```

한도는 **수신 측**에 걸린다. 서버는 문제없이 보냈고 클라이언트가 거부한 것이다. 그래서 서버 로그에는 아무것도 안 남고, 클라이언트만 실패한다. 원인을 서버에서 찾으면 오래 걸린다.

목록 조회처럼 결과 개수가 데이터에 따라 늘어나는 RPC 가 이 한도에 걸린다. 개발 중에는 데이터가 적어 안 걸리다가, 운영 데이터가 쌓이면서 특정 계정만 실패하기 시작한다.

한도는 채널 옵션으로 올린다.

```typescript
options: {
  package: 'hero',
  protoPath: '...',
  channelOptions: {
    'grpc.max_receive_message_length': 16 * 1024 * 1024,
    'grpc.max_send_message_length': 16 * 1024 * 1024,
  },
}
```

**다만 숫자를 올리는 건 임시방편이다.** 한 응답에 수 MB 가 실린다는 건 페이지네이션이나 스트리밍으로 나눠야 한다는 신호다. gRPC 는 서버 스트리밍을 지원하므로, 큰 목록은 `stream` 으로 흘려보내면 한도 자체가 문제가 되지 않는다.

### proto3 에서는 "값이 0" 과 "안 보냄" 이 구분되지 않는다

서버가 `score` 와 `active` 를 아예 채우지 않고 응답했을 때 클라이언트가 받는 값이다.

```
수신: {"id":"1","name":"n","score":0,"active":false}
score 가 "설정 안 됨"인지 "0으로 설정됨"인지 구분 가능? 불가능
```

`loader` 의 `defaults: true` 가 빠진 필드를 타입 기본값(`0`, `""`, `false`)으로 채운다. 문제는 **서버가 진짜 0을 보낸 경우와 결과가 똑같다**는 점이다. proto3 는 기본값과 같은 값을 아예 전송하지 않기 때문에, 와이어 상에서도 둘이 구분되지 않는다.

이게 문제가 되는 자리는 정해져 있다.

- **부분 수정(PATCH)** — "재고를 0으로 바꿔줘"와 "재고는 건드리지 마"가 같은 요청이 된다
- **필터 조건** — `minScore: 0` 이 "조건 없음"인지 "0점 이상"인지 알 수 없다
- **불리언 플래그** — `active: false` 로 끄려는 요청과 미지정이 같다

해결책은 두 가지다. `optional` 키워드를 붙이면 presence 정보가 유지된다. 같은 실험을 `optional` 필드로 다시 해보면:

```protobuf
message Hero {
  string id = 1;
  optional int32 score = 2;
  optional bool active = 3;
}
```

```
optional + 미지정     : {}                          / score typeof: undefined
optional + 0 으로 지정 : {"score":0,"active":false}  / score typeof: number
```

**`defaults: true` 를 그대로 둔 채로도 두 경우가 갈린다.** 미지정 필드는 응답 객체에 아예 나타나지 않는다.

아니면 `google.protobuf.Int32Value` 같은 wrapper 타입을 쓴다. 어느 쪽이든 **"이 필드는 없을 수 있다"를 스키마에 적어두는 것**이 핵심이다. 코드에서 `if (req.score)` 로 판단하는 순간 0이 미지정과 섞인다.

### `await setTimeout(2000)`은 기다리지 않는다 — 예외가 난다

양방향 스트리밍 예제의 이 줄은 Node 22에서 그 자리에서 죽는다.

```
TypeError [ERR_INVALID_ARG_TYPE]: The "callback" argument must be of type function.
Received type number (2000)
```

전역 `setTimeout`은 `(callback, delay)` 순서를 받는다. 숫자를 첫 인자로 주면 콜백 검증에 걸린다. 프로미스 버전은 `timers/promises`에 있다.

```typescript
import { setTimeout as sleep } from 'timers/promises';
await sleep(2000);
```

이름이 같아서 import 한 줄 차이로 갈린다. `import { setTimeout } from 'timers/promises'`를 쓰면 같은 파일 안의 다른 `setTimeout(fn, ms)` 호출까지 프로미스 버전으로 바뀌므로, 위처럼 `sleep`으로 이름을 바꿔 받는 게 안전하다.
