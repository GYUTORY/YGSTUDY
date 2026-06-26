---
title: NestJS GraphQL·마이크로서비스 버전 관리
tags: [nestjs, graphql, microservice, versioning, schema-evolution, e2e, supertest, node]
updated: 2026-06-26
---

# NestJS GraphQL·마이크로서비스 버전 관리

HTTP REST는 `enableVersioning`으로 URI/Header/Media-Type 버전 분기를 프레임워크가 처리해준다. 그런데 GraphQL과 마이크로서비스 트랜스포트에는 이게 안 먹는다. `enableVersioning`은 HTTP 라우터 레이어에서 동작하는데, GraphQL은 단일 `/graphql` 엔드포인트로 들어오고 마이크로서비스는 애초에 HTTP 라우터를 안 탄다. 그래서 이 두 영역은 버전 관리를 다른 방식으로 해야 한다.

REST 버저닝(`enableVersioning`, URI/Header/Media-Type, `VERSION_NEUTRAL`, 버전별 DTO 분기, deprecation, Swagger 분리)은 [Nest_JS_API_Versioning.md](Nest_JS_API_Versioning.md)에서 다룬다. 이 문서는 거기서 빠진 GraphQL 스키마 진화, 마이크로서비스 메시지 패턴 버저닝, 그리고 버전별 라우트 e2e 테스트만 정리한다.


## GraphQL에는 enableVersioning이 안 먹는다

`main.ts`에서 `app.enableVersioning()`을 켜도 GraphQL 리졸버에는 아무 영향이 없다. 직접 확인해보면 금방 안다. 컨트롤러에 `@Version('2')`를 붙이면 `/v2/users`로 분기되지만, 리졸버에 같은 데코레이터를 붙여도 무시된다. GraphQL 요청은 전부 `POST /graphql` 하나로 들어오고, Apollo/Mercurius 드라이버가 그 안에서 쿼리를 파싱해 리졸버로 보내기 때문이다. 라우터가 버전을 가를 기회 자체가 없다.

그래서 URI에 `/graphql/v2` 같은 별도 엔드포인트를 파는 사람들이 있는데, 이건 권장하지 않는다. 스키마를 통째로 복제해야 하고, 클라이언트는 어느 엔드포인트를 쓸지 또 결정해야 한다. GraphQL은 원래 "필드 단위로 클라이언트가 필요한 것만 받는다"는 전제로 설계됐다. 그 전제 위에서는 엔드포인트를 쪼개는 게 아니라 스키마를 진화시키는 방식으로 버전을 관리한다.


## 스키마 진화: 필드를 더하고 deprecated로 빼낸다

GraphQL 버전 관리의 기본은 단일 스키마를 깨지 않게 키우는 것이다. 핵심은 두 가지다. 새 필드는 추가만 한다. 기존 필드는 바로 지우지 않고 `@deprecated`로 표시한 뒤 나중에 뺀다.

REST에서 응답 구조를 바꾸면 그 API를 쓰던 클라이언트가 깨지지만, GraphQL은 클라이언트가 쿼리에 명시한 필드만 받아간다. 그래서 새 필드를 추가하는 건 기존 쿼리에 영향을 주지 않는다. 이게 GraphQL이 버전 번호 없이도 굴러가는 이유다.

```typescript
// user.model.ts
import { ObjectType, Field, ID } from '@nestjs/graphql';

@ObjectType()
export class User {
  @Field(() => ID)
  id: string;

  // 구버전 필드. 풀네임을 한 덩어리로 주던 것
  @Field({
    deprecationReason: 'firstName/lastName으로 분리됨. 2026-09-01 제거 예정',
  })
  fullName: string;

  // 신버전 필드. 추가만 했으므로 기존 쿼리는 그대로 동작
  @Field({ nullable: true })
  firstName?: string;

  @Field({ nullable: true })
  lastName?: string;
}
```

`deprecationReason`을 넣으면 SDL에 `@deprecated(reason: "...")`로 박히고, GraphQL Playground나 Apollo Studio에서 해당 필드에 취소선이 그어진다. 클라이언트 개발자는 자동완성에서 경고를 보고 옮겨갈 수 있다. REST의 `Deprecation` 헤더보다 클라이언트 쪽에 더 직접 노출된다는 게 GraphQL 쪽 장점이다.

여기서 실수하기 쉬운 게 있다. `@deprecated`를 붙였다고 리졸버 로직을 같이 지우면 안 된다. 필드가 스키마에 남아있는 한 그 필드를 쿼리하는 클라이언트가 있고, 리졸버는 계속 값을 채워줘야 한다. 그래서 deprecated 기간 동안은 구필드와 신필드를 둘 다 채운다.

```typescript
// user.resolver.ts
@ResolveField(() => String)
fullName(@Parent() user: UserEntity): string {
  // deprecated여도 제거 전까지는 계속 값을 채운다
  return `${user.firstName} ${user.lastName}`.trim();
}
```

언제 실제로 필드를 제거하느냐가 운영의 핵심이다. Apollo Studio를 붙였다면 field usage 통계로 해당 필드를 쿼리하는 트래픽이 0에 수렴하는지 본다. 통계가 없으면 리졸버에 로그를 박아 호출량을 직접 센다. 트래픽이 빠진 걸 확인한 다음에 필드를 빼야 한다. 통계 없이 날짜만 보고 지우면 아직 옮겨가지 않은 클라이언트가 깨진다.


## 깨지는 변경은 타입을 분리한다

필드 추가/deprecated로 감당 안 되는 변경이 있다. 같은 필드의 타입을 바꾸거나(String → Object), nullable이던 걸 non-null로 조이거나, 인자 구조를 통째로 바꾸는 경우다. 이건 단일 타입 안에서 진화시킬 수 없다. 새 타입을 만들고 쿼리 진입점을 따로 둔다.

```typescript
// 구버전: 주소를 문자열 하나로 주던 타입
@ObjectType()
export class UserV1 {
  @Field(() => ID) id: string;
  @Field() address: string; // "서울시 강남구 ..."
}

// 신버전: 주소를 구조화한 타입
@ObjectType()
export class Address {
  @Field() city: string;
  @Field() street: string;
  @Field({ nullable: true }) zipcode?: string;
}

@ObjectType()
export class UserV2 {
  @Field(() => ID) id: string;
  @Field(() => Address) address: Address;
}
```

```typescript
// 쿼리 진입점을 분리. 구쿼리는 살려두고 신쿼리를 추가
@Resolver()
export class UserResolver {
  @Query(() => UserV1, { name: 'user', deprecationReason: 'userV2 사용' })
  getUser(@Args('id') id: string): Promise<UserV1> { ... }

  @Query(() => UserV2, { name: 'userV2' })
  getUserV2(@Args('id') id: string): Promise<UserV2> { ... }
}
```

타입 분리는 스키마가 비대해지는 단점이 있다. `User`, `UserV1`, `UserV2`가 공존하면 스키마를 처음 보는 사람이 뭘 써야 할지 헷갈린다. 그래서 타입 분리는 정말 깨지는 변경에만 쓰고, 어지간하면 필드 추가로 끝내는 게 낫다. 그리고 구타입은 deprecated로 묶어서 "지울 예정"임을 명시한다.


## 단일 /graphql 엔드포인트에서 버전을 처리할 때의 한계

GraphQL 스키마 진화에는 REST 버저닝에 없는 제약이 몇 가지 있다.

스키마가 단조 증가한다. 한번 추가한 필드는 트래픽이 빠질 때까지 못 지운다. REST는 `/v1` 컨트롤러를 통째로 들어내면 끝나지만, GraphQL은 단일 스키마라 deprecated 필드가 계속 쌓인다. 정리 주기를 안 잡으면 1~2년 뒤 스키마에 죽은 필드가 수십 개 박혀있다.

버전을 헤더로 강제 분기할 수 없다. REST는 `Accept-Version: 2` 헤더로 같은 URL에서 다른 응답을 줄 수 있지만, GraphQL은 그게 안 된다. 같은 스키마에서 같은 필드를 쿼리하면 항상 같은 모양으로 응답한다. 헤더로 분기하고 싶으면 리졸버 안에서 컨텍스트를 까서 직접 처리해야 하는데, 이건 스키마와 실제 응답이 어긋나게 만들어서 권장하지 않는다.

전체 스키마를 한번에 갈아엎는 마이그레이션이 어렵다. REST는 `/v2`를 통째로 새로 짜서 병행 운영하다 `/v1`을 내리면 되지만, GraphQL에서 같은 걸 하려면 스키마 전체를 복제한 `/graphql/v2`를 따로 띄워야 한다. 드라이버를 두 개 등록하고 모듈을 분리하는 작업이라 비용이 크다. 어지간하면 단일 스키마 진화로 버티고, 정말 호환이 깨지는 대개편일 때만 엔드포인트를 분리한다.

GraphQL 모듈 도입 자체(N+1, DataLoader, 권한)는 [Nest_JS_Graph_QL.md](Nest_JS_Graph_QL.md)에서 다룬다.


## 마이크로서비스: URI가 없으니 메시지 패턴에 버전을 넣는다

`@MessagePattern`, `@EventPattern` 기반 마이크로서비스는 HTTP URL이 없다. TCP, Redis, NATS, Kafka 어느 트랜스포트를 쓰든 메시지는 "패턴"으로 라우팅된다. URI가 없으니 `/v2` 같은 경로 버저닝도 없고 `enableVersioning`도 안 통한다. 여기선 버전을 두 군데에 넣을 수 있다. 패턴 이름에 넣거나, 페이로드에 넣는다.


### 방법 1: 패턴 이름(cmd 키)에 버전을 박는다

패턴은 보통 `{ cmd: 'get_user' }` 같은 객체다. 여기에 버전을 끼워넣는다.

```typescript
// 구버전 핸들러. 그대로 유지
@MessagePattern({ cmd: 'get_user', version: '1' })
getUserV1(data: { id: string }): UserV1Dto {
  return this.userService.findV1(data.id);
}

// 신버전 핸들러를 별도로 추가
@MessagePattern({ cmd: 'get_user', version: '2' })
getUserV2(data: { id: string }): UserV2Dto {
  return this.userService.findV2(data.id);
}
```

호출하는 쪽도 버전을 명시해서 보낸다.

```typescript
// 게이트웨이/호출자
this.client.send({ cmd: 'get_user', version: '2' }, { id });
```

NestJS는 패턴을 객체 전체로 매칭한다. `{ cmd: 'get_user', version: '1' }`과 `{ cmd: 'get_user', version: '2' }`는 완전히 다른 패턴으로 취급되어 각각의 핸들러로 라우팅된다. 이 방식의 장점은 핸들러가 버전별로 물리적으로 분리된다는 것이다. 구버전 로직과 신버전 로직이 다른 메서드에 있으니 한쪽을 고쳐도 다른 쪽이 안 깨진다.

주의할 점이 하나 있다. 패턴 객체는 키 순서나 구조가 정확히 일치해야 매칭된다. 호출자가 `{ version: '2', cmd: 'get_user' }`로 키 순서를 바꿔 보내도 NestJS는 정규화해서 매칭하지만, 버전 키를 빠뜨리고 `{ cmd: 'get_user' }`로 보내면 어느 핸들러에도 안 걸려서 타임아웃이 난다. 구버전 호출자가 버전 키 없이 보내던 걸 그대로 두고 신버전 핸들러만 추가하면, 구버전 호출이 통째로 죽는다. 그래서 버전을 도입하는 시점에 기존 무버전 패턴을 "버전 1"로 함께 유지해야 한다.

```typescript
// 기존 무버전 호출자를 위한 호환 핸들러
@MessagePattern({ cmd: 'get_user' })          // 버전 키 없는 구호출
@MessagePattern({ cmd: 'get_user', version: '1' }) // 명시적 v1
getUserLegacy(data: { id: string }): UserV1Dto {
  return this.userService.findV1(data.id);
}
```

`@MessagePattern`은 한 메서드에 여러 번 붙일 수 있어서 무버전과 v1을 같은 핸들러로 묶을 수 있다.


### 방법 2: 페이로드에 version 필드를 둔다

패턴은 그대로 두고 데이터 안에 버전을 넣는 방식이다.

```typescript
@MessagePattern({ cmd: 'get_user' })
getUser(@Payload() data: { id: string; version?: number }) {
  const version = data.version ?? 1;
  if (version >= 2) {
    return this.userService.findV2(data.id);
  }
  return this.userService.findV1(data.id);
}
```

이 방식은 패턴이 하나라 라우팅이 단순하고, `version`이 없으면 1로 떨어뜨려서 구호출자를 자동으로 받아낸다. 대신 한 핸들러 안에 버전 분기가 `if`로 쌓인다. 버전이 3, 4로 늘면 메서드가 길어지고, 버전별 로직이 한 곳에 엉킨다. REST에서 버전별 DTO를 나눠 분기하던 것과 같은 문제다.

둘 중에는 패턴 이름에 버전을 넣는 쪽(방법 1)을 기본으로 쓴다. 핸들러가 버전별로 분리되어 회귀 위험이 적기 때문이다. 페이로드 방식은 버전 차이가 응답 필드 하나 정도로 작을 때, 핸들러를 쪼갤 만큼은 아닐 때 쓴다.


### 이벤트 패턴은 더 조심해야 한다

`@EventPattern`은 `@MessagePattern`과 달리 응답을 안 돌려주는 fire-and-forget이다. 그래서 버전이 안 맞아 핸들러에 안 걸려도 호출자는 에러를 못 받는다. 메시지가 그냥 사라진다. Kafka처럼 이벤트를 여러 구독자가 받는 경우, 구버전 구독자와 신버전 구독자가 같은 이벤트를 받아야 할 수도 있다. 이럴 땐 패턴을 쪼개지 말고 페이로드에 버전을 넣어서 모든 구독자가 같은 패턴을 구독하되 안에서 분기하게 하는 게 안전하다.

```typescript
// 이벤트는 패턴을 유지하고 페이로드 버전으로 분기
@EventPattern('user.created')
handleUserCreated(@Payload() event: { version?: number; user: any }) {
  const v = event.version ?? 1;
  // v1, v2 구독자가 같은 패턴을 받되 필요한 버전만 처리
  if (v >= 2) this.handleV2(event);
  else this.handleV1(event);
}
```

마이크로서비스 트랜스포트 구성과 메시지 송수신 기본은 [Nest_JS_마이크로서비스.md](Nest_JS_마이크로서비스.md)에서 다룬다.


### 구버전 패턴 핸들러를 언제 뺄까

REST의 deprecation과 똑같이, 구버전 패턴 핸들러는 트래픽이 빠진 걸 확인하고 뺀다. 마이크로서비스는 호출자가 다른 서비스라 더 까다롭다. 어느 서비스가 아직 `{ cmd: 'get_user', version: '1' }`을 부르는지 코드만 봐선 모른다. 구버전 핸들러에 로그를 박아서 호출량과 호출 출처를 기록한다.

```typescript
@MessagePattern({ cmd: 'get_user', version: '1' })
getUserV1(@Payload() data: { id: string }, @Ctx() ctx: NatsContext) {
  this.logger.warn(`v1 get_user 호출됨, subject=${ctx.getSubject()}`);
  return this.userService.findV1(data.id);
}
```

호출량이 0으로 떨어지고 일정 기간 유지되면 핸들러를 뺀다. 뺄 때 호출자 서비스부터 신버전으로 옮긴 뒤 핸들러를 제거하는 순서를 지킨다. 핸들러를 먼저 빼면 아직 옮기지 않은 호출자가 타임아웃이나 메시지 유실을 겪는다.


## 버전별 라우트 e2e 테스트

버전을 도입하면 v1과 v2가 동시에 살아있다. 둘 다 의도대로 동작하는지, v2를 고치다 v1을 깨지 않았는지 확인하는 e2e 테스트가 필요하다. REST 버저닝 기준으로 supertest를 쓴다.

```typescript
// users.e2e-spec.ts
import { Test } from '@nestjs/testing';
import { INestApplication, VersioningType } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../src/app.module';

describe('Users versioning (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleRef.createNestApplication();
    // 테스트 앱에도 운영과 동일하게 버저닝을 켜야 한다
    app.enableVersioning({ type: VersioningType.URI });
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('v1은 fullName을 단일 필드로 준다', () => {
    return request(app.getHttpServer())
      .get('/v1/users/1')
      .expect(200)
      .expect((res) => {
        expect(res.body.fullName).toBeDefined();
        expect(res.body.firstName).toBeUndefined();
      });
  });

  it('v2는 firstName/lastName으로 분리해서 준다', () => {
    return request(app.getHttpServer())
      .get('/v2/users/1')
      .expect(200)
      .expect((res) => {
        expect(res.body.firstName).toBeDefined();
        expect(res.body.lastName).toBeDefined();
      });
  });
});
```

여기서 가장 중요한 한 줄은 테스트 앱에 `app.enableVersioning()`을 빼먹지 않는 것이다. `createNestApplication()`은 `main.ts`의 bootstrap을 안 탄다. `main.ts`에서 `enableVersioning`을 호출했어도 테스트 앱에는 자동으로 안 들어간다. 이걸 빠뜨리면 `/v1/users`, `/v2/users` 둘 다 404가 나서 "버전 라우트가 등록 안 됐다"고 착각하게 된다. 운영 코드는 멀쩡한데 테스트 설정만 다른 케이스다. NestJS 테스트의 DI 컨테이너 구성은 [Nest_JS_테스트.md](Nest_JS_테스트.md)에서 다룬다.


### 헤더 버저닝 테스트의 함정

URI 버저닝은 경로만 다르게 부르면 되니 테스트가 단순하다. 헤더 버저닝(`VersioningType.HEADER`)은 같은 URL에 헤더만 바꿔 보내야 해서 실수 지점이 더 많다.

```typescript
beforeAll(async () => {
  // ... moduleRef 생성 ...
  app = moduleRef.createNestApplication();
  app.enableVersioning({
    type: VersioningType.HEADER,
    header: 'X-API-Version', // 운영과 똑같은 헤더 이름을 써야 한다
  });
  await app.init();
});

it('헤더로 v1을 요청', () => {
  return request(app.getHttpServer())
    .get('/users/1')
    .set('X-API-Version', '1')   // 헤더 이름 정확히 일치
    .expect(200)
    .expect((res) => expect(res.body.fullName).toBeDefined());
});

it('헤더로 v2를 요청', () => {
  return request(app.getHttpServer())
    .get('/users/1')
    .set('X-API-Version', '2')
    .expect(200)
    .expect((res) => expect(res.body.firstName).toBeDefined());
});

it('헤더가 없으면 기본 버전으로 떨어진다', () => {
  return request(app.getHttpServer())
    .get('/users/1')             // 헤더 없음
    .expect(200);
});
```

헤더 버저닝 테스트에서 막히는 지점이 둘 있다. 첫째, `enableVersioning`에 설정한 `header` 이름과 `.set()`에 쓰는 헤더 이름이 한 글자라도 다르면 매칭이 안 된다. `X-API-Version`과 `X-Api-Version`은 HTTP 헤더가 대소문자를 안 가리니 괜찮지만, `X-API-Version`과 `API-Version`은 다른 헤더다. 운영 설정과 테스트 설정에서 헤더 이름을 상수 하나로 공유하는 게 안전하다.

둘째, 헤더를 안 보냈을 때 어디로 떨어지는지를 꼭 테스트한다. 기본 버전(`defaultVersion`)을 설정해뒀으면 그 버전으로 가고, 안 했으면 404가 난다. 구버전 클라이언트가 헤더 없이 호출하던 걸 그대로 받으려면 `defaultVersion`을 v1로 잡아야 하는데, 이게 의도대로 동작하는지 헤더 없는 요청으로 검증한다. 이 테스트를 빼먹으면 헤더 안 보내는 구클라이언트가 운영에서 404를 맞는다.


### v1→v2 동시 운영 중 회귀 방지

v1과 v2를 같이 굴리는 동안 v2 기능을 계속 고치게 된다. 이때 v1이 안 깨졌는지를 매번 확인해야 한다. v1, v2 테스트를 같은 spec 파일에 묶어두고 CI에서 항상 같이 돌리는 게 기본이다. v2만 따로 테스트하면 v1 회귀를 못 잡는다.

특히 v1과 v2가 같은 서비스 메서드를 공유하다가 한쪽 요구로 그 메서드를 고치는 경우가 위험하다. 예를 들어 `userService.find()`를 v1, v2가 같이 쓰는데 v2 때문에 반환 구조를 바꾸면 v1 응답도 같이 바뀐다. 이걸 잡으려면 v1 테스트가 응답의 정확한 모양(어떤 필드가 있고 어떤 필드가 없어야 하는지)까지 검증해야 한다. 위 예제에서 v1 테스트에 `expect(res.body.firstName).toBeUndefined()`를 넣은 게 그 목적이다. v2 작업이 실수로 v1 응답에 `firstName`을 흘리면 이 단언이 깨지면서 회귀를 잡아낸다.

마이크로서비스 패턴 버저닝도 같은 원칙으로 테스트한다. 단 supertest는 HTTP용이라 안 맞고, `ClientProxy`로 메시지를 보내 응답을 검증한다.

```typescript
it('v1, v2 패턴이 각각 다른 응답을 준다', async () => {
  const v1 = await firstValueFrom(
    client.send({ cmd: 'get_user', version: '1' }, { id: '1' }),
  );
  const v2 = await firstValueFrom(
    client.send({ cmd: 'get_user', version: '2' }, { id: '1' }),
  );
  expect(v1.fullName).toBeDefined();
  expect(v2.firstName).toBeDefined();
  // 무버전 호출이 v1으로 떨어지는지도 확인
  const legacy = await firstValueFrom(
    client.send({ cmd: 'get_user' }, { id: '1' }),
  );
  expect(legacy.fullName).toBeDefined();
});
```

무버전 호출이 v1으로 떨어지는지 검증하는 마지막 케이스가 핵심이다. 버전을 도입하면서 기존 무버전 호출자를 챙기는 호환 핸들러가 의도대로 동작하는지를 여기서 잡는다. 이게 깨지면 아직 안 옮긴 호출자 서비스가 운영에서 통째로 죽는다.
