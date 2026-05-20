---
title: NestJS GraphQL 모듈 운영기
tags: [nestjs, graphql, apollo, mercurius, dataloader, federation]
updated: 2026-05-20
---

# NestJS GraphQL 모듈 운영기

REST로 잘 굴러가던 서비스에 모바일팀이 와서 "필드 골라 받고 싶다"고 했다. 처음엔 `fields` 쿼리 파라미터로 막아보다가 결국 GraphQL을 붙였다. `@nestjs/graphql`은 첫인상은 깔끔한데, 막상 운영에 올리면 N+1, 메모리 누수, 권한 체크 누락이 한꺼번에 터진다. 이 문서는 NestJS에서 GraphQL을 도입하면서 부딪힌 지점들을 정리한다.

REST 기반 컨트롤러 라이프사이클은 [Nest_JS_요청_라이프사이클.md](Nest_JS_요청_라이프사이클.md)에서 다루고, 본 문서는 GraphQL 레이어가 그 위에 어떻게 얹히는지에 집중한다.


## 드라이버 선택: Apollo vs Mercurius

`@nestjs/graphql`은 드라이버 추상화 위에 동작한다. 같은 데코레이터 코드를 쓰면서 내부 엔진만 갈아끼울 수 있다. 선택지는 사실상 둘이다.

**Apollo Driver** (`@nestjs/apollo`)
- Express 위에서 가장 안정적으로 굴러간다
- 플러그인 생태계가 크다. APQ(Automatic Persisted Queries), Apollo Studio, 트레이싱 등 외부 도구 연동이 풍부하다
- Federation(`@apollo/subgraph`) 공식 지원
- 메모리 사용량이 Mercurius보다 30~40% 정도 높았다(우리 사례, 동시 접속 1k 기준)

**Mercurius Driver** (`@nestjs/mercurius`)
- Fastify 기반. 벤치마크 상 처리량이 Apollo의 1.5~2배 정도 나온다
- JIT 컴파일러가 내장되어 동일 쿼리 반복 호출 시 빠르다
- Federation 지원은 있는데 Apollo Federation 2 일부 기능이 늦게 따라온다
- 플러그인 수가 적어 직접 짜야 할 일이 늘어난다

신규 프로젝트면 Mercurius가 매력적이지만, Apollo Federation 게이트웨이를 이미 운영 중이거나 Apollo Studio로 스키마 변경 이력을 보고 있다면 Apollo를 그대로 쓰는 게 낫다. 우리는 모놀리식 단계에서는 Mercurius로 시작했다가 서비스를 쪼개면서 Apollo Federation으로 갈아탔다.

```typescript
// Apollo Driver
import { ApolloDriver, ApolloDriverConfig } from '@nestjs/apollo';
import { GraphQLModule } from '@nestjs/graphql';

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloDriverConfig>({
      driver: ApolloDriver,
      autoSchemaFile: 'schema.gql',
      playground: false,
      introspection: process.env.NODE_ENV !== 'production',
      formatError: (error) => {
        const { message, extensions, path } = error;
        delete extensions?.exception?.stacktrace;
        return { message, extensions, path };
      },
    }),
  ],
})
export class AppModule {}
```

```typescript
// Mercurius Driver
import { MercuriusDriver, MercuriusDriverConfig } from '@nestjs/mercurius';

@Module({
  imports: [
    GraphQLModule.forRoot<MercuriusDriverConfig>({
      driver: MercuriusDriver,
      autoSchemaFile: 'schema.gql',
      graphiql: false,
      jit: 1,
      queryDepth: 7,
    }),
  ],
})
export class AppModule {}
```

`playground`나 `graphiql`은 운영에서 무조건 꺼야 한다. 사내망이라도 마찬가지다. introspection은 스키마를 외부에 그대로 노출하므로, 외부 공개 API라면 끄거나 권한 체크를 붙여야 한다.


## Code First vs Schema First

GraphQL을 NestJS에서 쓰는 방식은 두 가지로 갈린다.

### Schema First

`.graphql` 파일에 SDL을 먼저 쓰고, 거기서 TypeScript 타입을 생성한다.

```graphql
# schema/user.graphql
type User {
  id: ID!
  email: String!
  name: String!
  posts: [Post!]!
}

type Query {
  user(id: ID!): User
}
```

`@nestjs/graphql`의 `typePaths`와 `generateOptions`로 타입을 뽑는다.

```typescript
GraphQLModule.forRoot({
  typePaths: ['./**/*.graphql'],
  definitions: {
    path: join(process.cwd(), 'src/graphql.ts'),
    outputAs: 'class',
  },
});
```

장점은 스키마가 진실의 원천이라는 것. 프론트엔드와 SDL 파일만 공유하면 끝난다. 단점은 SDL과 코드가 분리되어 있어 리졸버를 짤 때 SDL을 보고 다시 타입을 맞춰야 한다는 점이다. SDL이 바뀌면 코드와 어긋날 수 있다.

### Code First

데코레이터로 클래스에 메타데이터를 박고, NestJS가 그걸 보고 SDL을 만든다.

```typescript
import { Field, ID, ObjectType } from '@nestjs/graphql';

@ObjectType()
export class User {
  @Field(() => ID)
  id: string;

  @Field()
  email: string;

  @Field()
  name: string;

  @Field(() => [Post])
  posts: Post[];
}
```

`autoSchemaFile`을 지정하면 빌드/부팅 시 SDL이 생성된다.

```typescript
GraphQLModule.forRoot({
  autoSchemaFile: join(process.cwd(), 'src/schema.gql'),
  sortSchema: true,
});
```

장점은 TypeScript 타입과 GraphQL 타입이 한 곳에 있다는 점. DTO에 `@Field`만 추가하면 끝이다. 단점은 데코레이터에 의존하므로 ts 컴파일러 옵션(`emitDecoratorMetadata`, `experimentalDecorators`)이 꺼져 있으면 동작이 깨진다. 또 SDL 파일이 자동 생성이라 PR 리뷰 때 스키마 변경 의도를 읽기 어렵다. 이 문제는 `sortSchema: true`와 자동 생성된 `schema.gql`을 git에 함께 커밋하는 룰로 보완한다.

실무 경험상 TypeScript 진영이면 Code First가 압도적으로 편하다. Schema First는 프론트엔드가 SDL을 직접 작성/리뷰하는 팀에서 쓰는 게 의미 있다.


## ObjectType, Field, Resolver

Code First 기준으로 가장 자주 쓰는 데코레이터를 정리한다.

### ObjectType과 Field

```typescript
import { Field, ID, Int, ObjectType, GraphQLISODateTime } from '@nestjs/graphql';

@ObjectType({ description: '사용자' })
export class User {
  @Field(() => ID)
  id: string;

  @Field()
  email: string;

  @Field({ nullable: true })
  name?: string;

  @Field(() => Int)
  age: number;

  @Field(() => GraphQLISODateTime)
  createdAt: Date;

  // GraphQL 스키마에서 숨기고 싶은 필드
  passwordHash: string;
}
```

타입 추론에 주의해야 한다. `string`, `boolean`은 명시 없이도 인식되지만, `number`는 `Float`로 기본 추론된다. 정수가 필요하면 `@Field(() => Int)`로 명시해야 한다. 안 그러면 클라이언트에 소수점이 섞여 들어가는 일이 생긴다.

`nullable`도 함정이다. TypeScript의 optional(`?`)과 GraphQL의 nullable은 별개다. `@Field()`만 쓰면 non-null로 잡히는데, 실제 값이 `undefined`로 들어오면 런타임 에러가 난다.

### Args와 InputType

쿼리/뮤테이션 인자는 `@Args`로 받는다. 단일 스칼라는 그대로 받지만, 객체 인자는 `@InputType`으로 감싸야 한다.

```typescript
import { ArgsType, Field, InputType, Int } from '@nestjs/graphql';
import { IsEmail, MinLength } from 'class-validator';

@InputType()
export class CreateUserInput {
  @Field()
  @IsEmail()
  email: string;

  @Field()
  @MinLength(8)
  password: string;
}

@ArgsType()
export class GetUsersArgs {
  @Field(() => Int, { defaultValue: 0 })
  offset: number;

  @Field(() => Int, { defaultValue: 20 })
  limit: number;
}
```

`@InputType`과 `@ArgsType`의 차이는 GraphQL 스키마에 input 객체로 정의되느냐, 인자가 펼쳐지느냐이다. 페이지네이션처럼 인자 여러 개를 묶고 싶지만 GraphQL 입장에서는 평평하게 받고 싶을 때 `@ArgsType`을 쓴다.

class-validator를 그대로 쓰려면 `ValidationPipe`를 글로벌로 걸어야 한다.

```typescript
app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));
```

`whitelist: true`를 안 걸면 클라이언트가 임의 필드를 인자에 끼워 넣어도 그냥 통과한다.

### Resolver

```typescript
import { Args, ID, Mutation, Query, Resolver } from '@nestjs/graphql';

@Resolver(() => User)
export class UserResolver {
  constructor(private readonly userService: UserService) {}

  @Query(() => User, { nullable: true })
  user(@Args('id', { type: () => ID }) id: string): Promise<User | null> {
    return this.userService.findById(id);
  }

  @Query(() => [User])
  users(@Args() args: GetUsersArgs): Promise<User[]> {
    return this.userService.findAll(args);
  }

  @Mutation(() => User)
  createUser(@Args('input') input: CreateUserInput): Promise<User> {
    return this.userService.create(input);
  }
}
```

`@Resolver(() => User)`에 부모 타입을 넘기는 이유는 다음에 설명할 `@ResolveField` 때문이다. 단순 Query/Mutation만 다루는 리졸버라면 인자 없이 `@Resolver()`만 써도 동작한다.

### ResolveField

GraphQL의 핵심은 트리 형태의 응답이다. `User.posts`처럼 자식 필드를 채울 때 `@ResolveField`를 쓴다.

```typescript
@Resolver(() => User)
export class UserResolver {
  @ResolveField(() => [Post])
  posts(@Parent() user: User): Promise<Post[]> {
    return this.postService.findByUserId(user.id);
  }
}
```

여기서 N+1이 터진다. 사용자 100명을 가져오는 쿼리에서 각자 `posts`를 요청하면 `findByUserId`가 100번 돈다. DataLoader가 필요한 지점이다.


## DataLoader로 N+1 해결

DataLoader는 같은 틱(tick) 안의 키 요청을 모아서 배치 호출로 바꿔주는 라이브러리다. Facebook이 만들었고, GraphQL 진영에서는 사실상 표준이다.

```bash
npm install dataloader
```

### 기본 사용법

```typescript
import DataLoader from 'dataloader';

const postsByUserLoader = new DataLoader<string, Post[]>(async (userIds) => {
  const posts = await postRepository.find({
    where: { userId: In(userIds as string[]) },
  });
  // 입력 순서와 결과 순서가 같아야 한다
  const grouped = new Map<string, Post[]>();
  for (const id of userIds) grouped.set(id, []);
  for (const post of posts) grouped.get(post.userId)?.push(post);
  return userIds.map((id) => grouped.get(id) ?? []);
});
```

DataLoader가 동작하는 핵심 규칙: 배치 함수가 받은 키 순서와 같은 순서로, 같은 개수의 결과를 돌려줘야 한다. 이 약속이 깨지면 다른 사용자의 데이터가 섞여 나간다. 운영에서 가장 자주 실수하는 부분이다. `find().then(rs => rs)`로 그대로 돌려주면 안 되고, 입력 키 기준으로 정렬해 맞춰야 한다.

### 요청 스코프 주입

DataLoader는 요청마다 새로 만들어야 한다. 캐시가 요청 단위로 격리되어야 다른 사용자 데이터를 흘리지 않는다. NestJS에서는 `REQUEST` 스코프 프로바이더 또는 `context` 콜백을 활용한다.

```typescript
// Apollo Driver 기준
GraphQLModule.forRoot({
  driver: ApolloDriver,
  autoSchemaFile: true,
  context: ({ req }) => ({
    req,
    loaders: createLoaders(),
  }),
});
```

```typescript
// loaders.ts
export function createLoaders() {
  return {
    postsByUser: new DataLoader<string, Post[]>(async (userIds) => {
      // ...
    }),
  };
}
```

리졸버에서 `@Context()`로 꺼낸다.

```typescript
@ResolveField(() => [Post])
posts(@Parent() user: User, @Context() ctx: { loaders: Loaders }) {
  return ctx.loaders.postsByUser.load(user.id);
}
```

REQUEST 스코프 프로바이더로 만드는 방법도 있는데, 스코프가 부모로 전파되어 성능 저하가 큰 경우가 있어 우리는 `context` 콜백 방식을 더 선호한다.

### 캐시 함정

DataLoader는 같은 키로 두 번 부르면 캐시된 결과를 돌려준다. 뮤테이션 후에 같은 ID를 다시 조회하면 변경 전 값이 나올 수 있다. 뮤테이션 안에서 다시 조회하기 전에 `loader.clear(id)` 또는 `loader.clearAll()`을 호출해야 한다.

```typescript
@Mutation(() => User)
async updateUser(
  @Args('id', { type: () => ID }) id: string,
  @Args('input') input: UpdateUserInput,
  @Context() ctx: { loaders: Loaders },
) {
  const updated = await this.userService.update(id, input);
  ctx.loaders.userById.clear(id);
  return updated;
}
```


## Subscription

GraphQL Subscription은 WebSocket으로 양방향 통신을 한다. 채팅, 알림, 실시간 상태 표시 같은 곳에 쓴다.

### 단일 인스턴스 구성

`graphql-subscriptions`의 `PubSub`을 사용하면 같은 프로세스 안에서 동작한다.

```typescript
import { PubSub } from 'graphql-subscriptions';

const pubSub = new PubSub();

@Resolver()
export class NotificationResolver {
  @Subscription(() => Notification, {
    filter: (payload, variables) => payload.userId === variables.userId,
  })
  notificationReceived(@Args('userId') userId: string) {
    return pubSub.asyncIterator('notification');
  }

  @Mutation(() => Boolean)
  async sendNotification(@Args('input') input: SendNotificationInput) {
    await pubSub.publish('notification', {
      notificationReceived: input,
      userId: input.userId,
    });
    return true;
  }
}
```

`filter` 함수는 클라이언트에게 보낼지 말지를 결정한다. 모든 구독자에게 발행한 뒤 필터링하므로, 발행량이 많고 구독자가 많으면 성능 부담이 생긴다.

### 다중 인스턴스 구성

서비스 인스턴스가 두 대 이상이면 위 방식으로는 안 된다. A 인스턴스에서 발행한 이벤트가 B 인스턴스에 붙은 구독자에게는 안 간다. Redis 같은 외부 PubSub이 필요하다.

```typescript
import { RedisPubSub } from 'graphql-redis-subscriptions';
import Redis from 'ioredis';

@Module({
  providers: [
    {
      provide: 'PUB_SUB',
      useFactory: () => {
        const options = { host: 'redis', port: 6379 };
        return new RedisPubSub({
          publisher: new Redis(options),
          subscriber: new Redis(options),
        });
      },
    },
  ],
  exports: ['PUB_SUB'],
})
export class PubSubModule {}
```

Redis 연결은 publisher와 subscriber를 따로 두어야 한다. 같은 연결을 쓰면 subscribe 모드로 들어간 뒤 publish 명령이 실패한다. 이 함정에 한 번 빠진 적이 있다.

### Subscription 인증

WebSocket 연결 핸드셰이크 시점에 인증 토큰을 받아야 한다. HTTP 헤더와는 다른 경로다.

```typescript
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  subscriptions: {
    'graphql-ws': {
      onConnect: (context: any) => {
        const token = context.connectionParams?.authorization;
        if (!token) throw new Error('Missing token');
        const user = verifyJwt(token);
        return { user };
      },
    },
  },
});
```

`graphql-ws`는 신 표준이고, `subscriptions-transport-ws`는 deprecated다. 신규 프로젝트는 `graphql-ws`로 가야 한다. 클라이언트도 같이 맞춰야 하니 프론트엔드와 합의가 필요하다.


## Federation: 스키마를 나눠 운영하기

서비스가 커지면 단일 스키마를 모놀리식으로 두기 어렵다. 사용자 도메인은 user-service가, 주문은 order-service가 책임지되, 게이트웨이에서 하나의 그래프로 보이게 하는 패턴이 Federation이다.

### 서브그래프 작성

```typescript
import { Directive, Field, ID, ObjectType } from '@nestjs/graphql';

@ObjectType()
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  id: string;

  @Field()
  email: string;
}

@Resolver(() => User)
export class UserResolver {
  @Query(() => User, { nullable: true })
  user(@Args('id', { type: () => ID }) id: string) {
    return this.userService.findById(id);
  }

  @ResolveReference()
  resolveReference(reference: { __typename: string; id: string }) {
    return this.userService.findById(reference.id);
  }
}
```

```typescript
GraphQLModule.forRoot<ApolloFederationDriverConfig>({
  driver: ApolloFederationDriver,
  autoSchemaFile: { federation: 2 },
});
```

`@key` 디렉티브가 핵심이다. 다른 서비스가 `User`를 참조할 때 어떤 필드로 식별하는지를 선언한다. `@ResolveReference`는 게이트웨이가 "id=42인 User 가져와"라고 요청했을 때 응답하는 진입점이다.

### Order 서비스에서 User 확장

```typescript
@ObjectType()
@Directive('@extends')
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  @Directive('@external')
  id: string;

  @Field(() => [Order])
  orders: Order[];
}

@Resolver(() => User)
export class UserOrdersResolver {
  @ResolveField(() => [Order])
  orders(@Parent() user: { id: string }) {
    return this.orderService.findByUserId(user.id);
  }
}
```

User 본체는 user-service가 가지고 있지만, `orders` 필드는 order-service가 채운다. 클라이언트 입장에서는 `user(id: ...) { orders { ... } }` 한 번의 쿼리로 받는다.

### 게이트웨이

```typescript
GraphQLModule.forRoot<ApolloGatewayDriverConfig>({
  driver: ApolloGatewayDriver,
  gateway: {
    supergraphSdl: new IntrospectAndCompose({
      subgraphs: [
        { name: 'user', url: 'http://user-service:3001/graphql' },
        { name: 'order', url: 'http://order-service:3002/graphql' },
      ],
    }),
  },
});
```

`IntrospectAndCompose`는 부팅 시 각 서브그래프에서 스키마를 받아 합친다. 운영에서는 서브그래프 중 하나가 죽어 있으면 게이트웨이가 부팅 자체를 못 한다. 그래서 실제로는 빌드 타임에 supergraph SDL을 컴파일해 두고 정적으로 로드하는 방식을 쓴다. Apollo가 만든 `rover` CLI가 그 작업을 담당한다.

### Federation 운영 함정

서브그래프 간 순환 참조가 생기면 게이트웨이 컴포지션이 깨진다. 예: user-service가 Order를 확장하고, order-service가 다시 User를 확장하면서 같은 필드를 다루는 경우. 도메인 경계를 분명히 그어야 한다.

또 한 가지, 인증 정보 전파다. 게이트웨이가 받은 JWT는 서브그래프로 자동 전달되지 않는다. `RemoteGraphQLDataSource`의 `willSendRequest`를 오버라이드해서 헤더를 넘겨야 한다.

```typescript
class AuthDataSource extends RemoteGraphQLDataSource {
  willSendRequest({ request, context }) {
    if (context.token) request.http.headers.set('authorization', context.token);
  }
}
```


## 운영에서 부딪힌 것들

### 쿼리 깊이/복잡도 제한

GraphQL은 클라이언트가 쿼리를 자유롭게 짤 수 있어서 악의적이거나 실수로 무거운 쿼리가 들어오기 쉽다. 깊이 5짜리 재귀 쿼리 하나로 DB 커넥션이 다 마른 적이 있다.

```typescript
import depthLimit from 'graphql-depth-limit';
import { createComplexityLimitRule } from 'graphql-validation-complexity';

GraphQLModule.forRoot({
  validationRules: [
    depthLimit(7),
    createComplexityLimitRule(1000),
  ],
});
```

깊이는 7~10 정도, 복잡도는 도메인에 맞게 정한다. 복잡도는 필드마다 가중치를 다르게 줄 수 있다. 리스트 필드는 가중치를 높게 잡아야 한다.

### 에러 마스킹

`formatError`에서 스택트레이스와 내부 에러 메시지를 지워야 한다. 안 그러면 SQL 에러 메시지나 파일 경로가 그대로 노출된다.

```typescript
formatError: (error) => {
  if (process.env.NODE_ENV === 'production') {
    return {
      message: error.extensions?.code === 'BAD_USER_INPUT'
        ? error.message
        : 'Internal server error',
      extensions: { code: error.extensions?.code },
    };
  }
  return error;
}
```

### Guard와 GraphQL Context

NestJS Guard는 `ExecutionContext`에서 request를 꺼내는데, GraphQL은 HTTP 컨텍스트가 아니라 `GqlExecutionContext`를 통해 꺼내야 한다.

```typescript
@Injectable()
export class GqlAuthGuard extends AuthGuard('jwt') {
  getRequest(context: ExecutionContext) {
    const ctx = GqlExecutionContext.create(context);
    return ctx.getContext().req;
  }
}
```

이 부분을 빠뜨리면 Guard가 request를 못 찾아서 모든 요청이 401이 난다. 새 팀원이 GraphQL 처음 붙일 때마다 겪는 통과의례다.

### 캐싱

REST와 달리 GraphQL은 URL이 항상 `/graphql`이고 본문이 다르다. HTTP 캐시 레이어가 잘 안 먹는다. 응답 캐시가 필요하면 Apollo Server의 `@cacheControl` 디렉티브와 KeyvAdapter 같은 외부 캐시 백엔드를 붙이거나, 클라이언트(Apollo Client)에서 정규화 캐시를 활용해야 한다.

### 파일 업로드

GraphQL multipart spec(`graphql-upload`)으로 처리할 수 있지만, 우리는 별도 REST 엔드포인트로 빼는 쪽을 택했다. multipart 처리에 보안 이슈가 자주 보고됐고, 큰 파일을 GraphQL 파이프라인에 태우는 게 메모리 효율도 나쁘다. presigned URL 받아서 S3에 직접 올리고, GraphQL은 키만 받는 방식이 무난하다.

### 스키마 변경 정책

GraphQL은 버전 없이 진화하는 게 원칙이다. 필드 삭제는 `@deprecated`로 마킹하고 일정 기간 유지하다 제거한다.

```typescript
@Field({ deprecationReason: '2026-06-01 이후 제거. fullName 사용' })
displayName: string;
```

Apollo Studio를 쓰면 클라이언트별로 어떤 필드가 사용되는지 추적되어 제거 시점을 판단하기 쉽다. 우리는 자체 분석 로그로 같은 효과를 냈다.
