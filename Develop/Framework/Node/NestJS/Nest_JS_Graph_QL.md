---
title: NestJS GraphQL 모듈 운영기
tags: [nestjs, graphql, apollo, mercurius, dataloader, federation, subscription, auth]
updated: 2026-06-04
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

GraphQL을 NestJS에서 쓰는 방식은 두 가지로 갈린다. 어느 쪽을 고르느냐가 이후 6개월 동안 팀의 작업 방식을 결정한다.

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

type Post {
  id: ID!
  title: String!
  authorId: ID!
}

type Query {
  user(id: ID!): User
  users(offset: Int = 0, limit: Int = 20): [User!]!
}

input CreateUserInput {
  email: String!
  password: String!
  name: String
}

type Mutation {
  createUser(input: CreateUserInput!): User!
}
```

`@nestjs/graphql`의 `typePaths`와 `definitions`로 타입을 뽑는다.

```typescript
GraphQLModule.forRoot({
  typePaths: ['./**/*.graphql'],
  definitions: {
    path: join(process.cwd(), 'src/graphql.ts'),
    outputAs: 'class',
    watch: process.env.NODE_ENV !== 'production',
  },
});
```

생성된 `graphql.ts`는 빌드 산출물에 가깝다. git에 커밋하지 않고 `.gitignore`에 넣는 팀도 있고, PR 리뷰에 도움되도록 커밋하는 팀도 있다. 우리는 커밋하는 쪽으로 갔다. 리졸버 변경 PR에서 타입이 같이 바뀌면 스키마 변경 의도가 보이기 때문이다.

리졸버를 짤 때는 SDL을 보고 시그니처를 맞춰야 한다.

```typescript
import { Args, Query, Resolver } from '@nestjs/graphql';
import { User } from '../graphql';

@Resolver('User')
export class UserResolver {
  constructor(private readonly userService: UserService) {}

  @Query()
  async user(@Args('id') id: string): Promise<User | null> {
    return this.userService.findById(id);
  }
}
```

SDL이 진실의 원천이라는 게 장점이다. 프론트엔드와 SDL 파일만 공유하면 끝나고, 다른 언어(Go, Rust, Python)로 짠 백엔드와도 같은 스키마를 공유할 수 있다. 모바일이 GraphQL Codegen으로 클라이언트 타입을 자동 생성하는 워크플로우와도 잘 맞는다.

단점은 SDL과 코드가 분리되어 있다는 점이다. SDL에서 필드 하나 바꾸면 리졸버에서 시그니처를 손으로 맞춰야 한다. 이 동기화를 잊으면 컴파일은 통과해도 런타임에서 깨진다. `strict` 모드를 켜둬도 `any`로 빠져나가는 경우가 생긴다.

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

장점은 TypeScript 타입과 GraphQL 타입이 한 곳에 있다는 점이다. DTO에 `@Field`만 추가하면 끝이다. 리졸버 메서드 시그니처가 그대로 스키마와 묶여 있어서 리팩터링 안전성이 높다. 필드명을 IDE에서 rename 하면 SDL도 같이 바뀐다.

단점은 데코레이터에 의존하므로 ts 컴파일러 옵션(`emitDecoratorMetadata`, `experimentalDecorators`)이 꺼져 있으면 동작이 깨진다. 또 SDL 파일이 자동 생성이라 PR 리뷰 때 스키마 변경 의도를 읽기 어렵다. 이 문제는 `sortSchema: true`와 자동 생성된 `schema.gql`을 git에 함께 커밋하는 룰로 보완한다.

### 어느 쪽을 골라야 하나

| 기준 | Schema First | Code First |
|---|---|---|
| 진실의 원천 | SDL 파일 | TypeScript 클래스 |
| 프론트엔드 협업 | SDL을 직접 공유 | SDL 자동 생성물 공유 |
| 타입 안전성 | 생성된 타입 + 수동 매핑 | 클래스가 곧 타입 |
| 리팩터링 | SDL과 코드 동시 수정 | IDE rename으로 동기화 |
| 멀티 언어 백엔드 | 잘 맞음 | 어색함 |
| 학습 곡선 | GraphQL SDL만 알면 됨 | NestJS 데코렉이터 추가 학습 |

실무 경험상 TypeScript 진영이면 Code First가 압도적으로 편하다. Schema First는 다음 상황에서 의미가 있다.

- 프론트엔드가 SDL을 직접 작성/리뷰하는 팀
- 백엔드 언어가 여러 개라 SDL을 공통 자산으로 관리해야 하는 경우
- BFF 패턴에서 외부 GraphQL API를 그대로 프록시할 때

우리는 모든 신규 프로젝트는 Code First로 가고, 외부 파트너에 스키마를 정식 문서로 제공해야 하는 케이스에서는 빌드 산출물인 `schema.gql`을 별도 저장소에 push해 SDL을 진실의 원천처럼 보이게 했다. 두 방식을 한 프로젝트에 섞는 건 권장하지 않는다. 데코레이터가 만든 타입과 SDL이 만든 타입이 충돌하면 디버깅이 어렵다.

### Schema First에서 Code First로 마이그레이션

기존 코드가 Schema First로 짜여 있는데 Code First로 옮기고 싶다면, 한 모듈씩 점진적으로 옮길 수 있다. NestJS는 두 방식의 결과물을 합쳐서 하나의 스키마로 묶어준다.

```typescript
GraphQLModule.forRoot({
  typePaths: ['./legacy/**/*.graphql'],   // Schema First 잔재
  autoSchemaFile: 'schema.gql',           // 새로 만드는 건 Code First
  definitions: {
    path: join(process.cwd(), 'src/legacy-graphql.ts'),
  },
});
```

같은 타입을 양쪽에서 동시에 선언하지 않도록 주의한다. 충돌 나면 부팅 시 `Schema must contain uniquely named types`로 죽는다.


## Resolver 실전 패턴

Code First 기준으로 리졸버를 짤 때 자주 쓰는 패턴을 정리한다.

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

`nullable`도 함정이다. TypeScript의 optional(`?`)과 GraphQL의 nullable은 별개다. `@Field()`만 쓰면 non-null로 잡히는데, 실제 값이 `undefined`로 들어오면 런타임 에러가 난다. DB에서 `null` 가능한 컬럼은 반드시 `@Field({ nullable: true })`로 표시해야 한다.

엔티티와 GraphQL ObjectType을 하나로 묶는 경우와 분리하는 경우가 있다. 작은 프로젝트면 묶어도 되지만, ORM 엔티티의 모든 필드가 그래프에 노출되면 곤란한 상황(`passwordHash`, 내부 상태 컬럼 등)이 자주 생긴다. 우리는 분리하는 쪽으로 갔다. ORM 엔티티는 도메인 객체로, GraphQL ObjectType은 응답 DTO로 두고, Resolver에서 매핑한다.

```typescript
// domain entity
@Entity()
export class UserEntity {
  @PrimaryColumn()
  id: string;

  @Column()
  email: string;

  @Column()
  passwordHash: string;
}

// GraphQL DTO
@ObjectType('User')
export class UserModel {
  @Field(() => ID)
  id: string;

  @Field()
  email: string;

  static from(entity: UserEntity): UserModel {
    const m = new UserModel();
    m.id = entity.id;
    m.email = entity.email;
    return m;
  }
}
```

매번 매핑 함수를 쓰는 게 번거롭지만, 도메인 변경이 그래프에 자동 전파되는 사고를 막아준다.

### Args와 InputType

쿼리/뮤테이션 인자는 `@Args`로 받는다. 단일 스칼라는 그대로 받지만, 객체 인자는 `@InputType`으로 감싸야 한다.

```typescript
import { ArgsType, Field, InputType, Int } from '@nestjs/graphql';
import { IsEmail, IsOptional, MinLength } from 'class-validator';

@InputType()
export class CreateUserInput {
  @Field()
  @IsEmail()
  email: string;

  @Field()
  @MinLength(8)
  password: string;

  @Field({ nullable: true })
  @IsOptional()
  name?: string;
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

`whitelist: true`를 안 걸면 클라이언트가 임의 필드를 인자에 끼워 넣어도 그냥 통과한다. `forbidNonWhitelisted: true`까지 쓰면 알 수 없는 필드가 들어왔을 때 400을 던진다. 보수적으로 가려면 켜라.

### Resolver와 의존성

```typescript
import { Args, ID, Mutation, Query, Resolver } from '@nestjs/graphql';

@Resolver(() => User)
export class UserResolver {
  constructor(
    private readonly userService: UserService,
    private readonly postService: PostService,
  ) {}

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

리졸버는 컨트롤러와 같은 레이어다. 비즈니스 로직을 리졸버 안에 직접 쓰지 말고 서비스로 빼는 게 좋다. 트랜잭션 경계도 서비스에서 잡아야 한다. 리졸버에 트랜잭션을 걸면 N+1 해소 때 DataLoader가 이상하게 동작한다.

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

`@ResolveField`는 부모 객체가 해당 필드를 이미 가지고 있더라도 항상 호출되는 게 기본이다. 부모에 이미 있으면 건너뛰고 싶다면 명시적으로 분기해야 한다.

```typescript
@ResolveField(() => [Post])
async posts(
  @Parent() user: User & { posts?: Post[] },
  @Context() ctx: GqlContext,
) {
  if (user.posts) return user.posts;
  return ctx.loaders.postsByUser.load(user.id);
}
```

ORM에서 eager loading으로 같이 끌고 온 경우 이 패턴이 유효하다.

### 에러 처리

리졸버에서 던지는 에러는 GraphQL 응답의 `errors` 배열에 들어간다. `HttpException`을 그대로 던지면 메시지가 노출되니, 의도한 메시지인지 점검해야 한다.

```typescript
@Query(() => User)
async user(@Args('id', { type: () => ID }) id: string) {
  const user = await this.userService.findById(id);
  if (!user) {
    throw new NotFoundException(`User ${id} not found`);
  }
  return user;
}
```

REST와 달리 GraphQL은 부분 성공이 가능하다. 한 필드의 리졸버에서 에러가 나도 다른 필드는 응답한다. `errors`에 그 필드 경로가 들어가고 해당 필드 값은 `null`이 된다. 이 동작 때문에 non-null 필드에서 에러가 나면 부모 객체 전체가 `null`로 떨어진다. 스키마 설계 시 어떤 필드를 nullable로 둘지가 장애 범위를 결정한다.


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

키 하나에 결과가 하나인 경우(1:1)는 더 헷갈리는데, 못 찾은 키 위치에는 `null`이나 `Error` 객체를 넣어야 한다. `undefined`를 넣으면 DataLoader가 캐시 미스로 오해해 무한 루프에 빠진다.

```typescript
const userByIdLoader = new DataLoader<string, User | null>(async (ids) => {
  const users = await userRepository.findByIds(ids as string[]);
  const map = new Map(users.map((u) => [u.id, u]));
  return ids.map((id) => map.get(id) ?? null);
});
```

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
import DataLoader from 'dataloader';
import { dataSource } from './data-source';

export interface Loaders {
  userById: DataLoader<string, User | null>;
  postsByUser: DataLoader<string, Post[]>;
  commentsByPost: DataLoader<string, Comment[]>;
}

export function createLoaders(): Loaders {
  return {
    userById: new DataLoader(async (ids) => {
      const rows = await dataSource.getRepository(User).findByIds(ids as string[]);
      const map = new Map(rows.map((u) => [u.id, u]));
      return ids.map((id) => map.get(id) ?? null);
    }),
    postsByUser: new DataLoader(async (userIds) => {
      const rows = await dataSource.getRepository(Post).find({
        where: { userId: In(userIds as string[]) },
      });
      const grouped = new Map<string, Post[]>();
      for (const id of userIds) grouped.set(id, []);
      for (const r of rows) grouped.get(r.userId)?.push(r);
      return userIds.map((id) => grouped.get(id) ?? []);
    }),
    commentsByPost: new DataLoader(async (postIds) => {
      const rows = await dataSource.getRepository(Comment).find({
        where: { postId: In(postIds as string[]) },
      });
      const grouped = new Map<string, Comment[]>();
      for (const id of postIds) grouped.set(id, []);
      for (const r of rows) grouped.get(r.postId)?.push(r);
      return postIds.map((id) => grouped.get(id) ?? []);
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

REQUEST 스코프 프로바이더로 만드는 방법도 있는데, 스코프가 부모로 전파되어 성능 저하가 큰 경우가 있어 우리는 `context` 콜백 방식을 더 선호한다. NestJS DI 컨테이너는 REQUEST 스코프 프로바이더를 만나면 의존 트리 전체를 요청마다 다시 인스턴스화한다. 큰 모듈에서 이 비용이 무시할 수준이 아니다.

### NestJS DI와 DataLoader 결합

DataLoader 안에서 다른 NestJS 서비스를 호출하고 싶다면, `createLoaders`를 팩토리로 두지 말고 클래스로 만드는 게 깔끔하다.

```typescript
@Injectable()
export class LoaderRegistry {
  constructor(
    private readonly userService: UserService,
    private readonly postService: PostService,
  ) {}

  create(): Loaders {
    return {
      userById: new DataLoader(async (ids) => {
        const users = await this.userService.findByIds(ids as string[]);
        const map = new Map(users.map((u) => [u.id, u]));
        return ids.map((id) => map.get(id) ?? null);
      }),
      postsByUser: new DataLoader(async (userIds) => {
        return this.postService.batchByUserIds(userIds as string[]);
      }),
    };
  }
}
```

```typescript
GraphQLModule.forRootAsync({
  driver: ApolloDriver,
  imports: [LoaderModule],
  inject: [LoaderRegistry],
  useFactory: (registry: LoaderRegistry) => ({
    autoSchemaFile: true,
    context: ({ req }) => ({
      req,
      loaders: registry.create(),
    }),
  }),
});
```

`LoaderRegistry` 자체는 싱글톤이고, `create()`가 매 요청마다 새 인스턴스를 만든다. 서비스 의존성은 그대로 주입되니 트랜잭션이나 캐시 같은 인프라 코드를 재활용할 수 있다.

### 캐시 함정과 무효화

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
  ctx.loaders.postsByUser.clear(id);
  return updated;
}
```

연관된 로더까지 같이 무효화해야 하는 경우가 많다. 예를 들어 사용자 이름을 바꿨는데 게시글 작성자 표시가 그대로면, 게시글 로더도 같이 비워야 한다. 어떤 로더가 어떤 엔티티에 의존하는지 추적하는 게 어렵다 보니, 우리는 도메인별로 `invalidate(userId)` 같은 헬퍼를 만들었다.

```typescript
class LoaderInvalidator {
  constructor(private readonly loaders: Loaders) {}

  user(id: string) {
    this.loaders.userById.clear(id);
    this.loaders.postsByUser.clear(id);
  }

  post(id: string, userId: string) {
    this.loaders.postById?.clear(id);
    this.loaders.postsByUser.clear(userId);
    this.loaders.commentsByPost.clear(id);
  }
}
```

### 배치 사이즈 조절

기본 동작은 같은 틱의 모든 키를 한 번에 보낸다. 키가 1만 개 쌓이면 `WHERE id IN (...)`이 1만 개짜리가 된다. DB가 견디지 못한다. `maxBatchSize` 옵션으로 잘라야 한다.

```typescript
new DataLoader(batchFn, { maxBatchSize: 500 });
```

PostgreSQL 기준 `IN` 절은 1만 개 이상도 받지만 쿼리 플래너가 인덱스를 안 타는 경우가 생긴다. 500~1000개 단위로 잘라서 병렬 호출하는 게 안전했다.

### 캐시 키 함수

키가 문자열/숫자가 아니라 객체일 때는 `cacheKeyFn`을 지정해야 한다.

```typescript
const loader = new DataLoader<{ tenantId: string; userId: string }, User | null>(
  async (keys) => {
    // ...
  },
  {
    cacheKeyFn: (key) => `${key.tenantId}:${key.userId}`,
  },
);
```

멀티테넌트 환경에서 테넌트 ID와 엔티티 ID를 같이 묶을 때 자주 쓴다. 이 함수가 없으면 객체 참조로 비교해서 캐시가 무용지물이 된다.

### DataLoader 라이프사이클

DataLoader 인스턴스는 요청이 끝나면 가비지 컬렉션으로 회수된다. 따로 `dispose`를 부를 필요는 없다. 하지만 큰 응답을 캐시에 들고 있는 로더가 요청 중 계속 살아 있으면 메모리 사용량이 튄다. 사용 직후 `loader.clear(key)`로 비워주는 패턴이 도움 될 때가 있다. 특히 페이지네이션으로 같은 로더를 여러 번 부르는 경우다.

### 성능 측정

DataLoader가 실제로 배치되는지 확인하는 게 중요하다. 로컬에서는 잘 묶이는데 운영에서 안 묶이는 경우가 있다. 원인은 대부분 `Promise.all` 대신 `await` 시퀀스를 썼기 때문이다.

```typescript
// 잘못된 패턴: 순차 await로 틱이 분리됨
for (const user of users) {
  user.posts = await ctx.loaders.postsByUser.load(user.id);
}

// 올바른 패턴: 모두 같은 틱에 큐잉됨
await Promise.all(
  users.map(async (u) => {
    u.posts = await ctx.loaders.postsByUser.load(u.id);
  }),
);
```

GraphQL 리졸버가 자동으로 병렬 실행되므로 보통은 문제가 없는데, 서비스 레이어에서 명시적으로 루프를 도는 경우 이 함정에 빠진다.


## Subscription

GraphQL Subscription은 WebSocket으로 양방향 통신을 한다. 채팅, 알림, 실시간 상태 표시 같은 곳에 쓴다. REST에서 SSE나 WebSocket을 따로 붙이는 것보다 스키마가 통일된다는 게 강점이지만, 운영 난이도가 한 단계 올라간다.

### 단일 인스턴스 구성

`graphql-subscriptions`의 `PubSub`을 사용하면 같은 프로세스 안에서 동작한다.

```typescript
import { PubSub } from 'graphql-subscriptions';
import { Args, Mutation, Resolver, Subscription } from '@nestjs/graphql';

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

`filter` 함수는 클라이언트에게 보낼지 말지를 결정한다. 모든 구독자에게 발행한 뒤 필터링하므로, 발행량이 많고 구독자가 많으면 성능 부담이 생긴다. 구독자가 1만 명일 때 단순 알림이라도 모든 구독자에 대해 필터가 한 번씩 돈다. 발행 시점에 채널 키를 잘 잘라야 한다.

```typescript
@Subscription(() => Notification, {
  filter: (payload, variables) => payload.userId === variables.userId,
  resolve: (payload) => payload.notificationReceived,
})
notificationReceived(@Args('userId') userId: string) {
  return pubSub.asyncIterator(`notification.${userId}`);
}

// 발행 측에서 사용자별 채널로 보냄
await pubSub.publish(`notification.${input.userId}`, { ... });
```

채널 이름에 ID를 박으면 필터가 사실상 필요 없고, 발행도 해당 채널 구독자에게만 간다. 구독자 수가 많은 서비스에서 필수다.

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

Redis Cluster를 쓰면 채널명 해시 슬롯이 노드별로 흩어진다. 같은 채널을 구독한 인스턴스 두 대가 서로 다른 마스터에 연결되어 있으면, 발행 한 번에 모든 마스터로 fan-out이 가야 한다. Redis 7의 `SHARDED_PUBSUB`을 쓰거나, Cluster 대신 Sentinel + 단일 마스터로 가는 게 운영 부담이 적었다.

### Subscription 인증

WebSocket 연결 핸드셰이크 시점에 인증 토큰을 받아야 한다. HTTP 헤더와는 다른 경로다. 쿠키는 첫 connect 요청에만 실리므로 의존하지 말고, `connectionParams`로 명시 전달하는 게 표준이다.

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

`onConnect`에서 반환한 객체는 이후 모든 구독 리졸버의 컨텍스트에 들어간다. 여기서 user 정보를 박아두면 리졸버에서 그대로 꺼내 권한 검사를 할 수 있다.

`graphql-ws`는 신 표준이고, `subscriptions-transport-ws`는 deprecated다. 신규 프로젝트는 `graphql-ws`로 가야 한다. 클라이언트도 같이 맞춰야 하니 프론트엔드와 합의가 필요하다.

### 권한 가드를 Subscription에 적용

`@UseGuards`를 Subscription에 그대로 붙일 수 있는데, request 객체 구조가 HTTP와 달라서 Guard를 GraphQL용으로 따로 만들어야 한다.

```typescript
@Injectable()
export class SubscriptionAuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const gqlCtx = GqlExecutionContext.create(context);
    const ctx = gqlCtx.getContext();
    // graphql-ws는 connectionParams에서 받은 값을 ctx에 보존
    const user = ctx.user ?? ctx.req?.user;
    if (!user) throw new UnauthorizedException();
    gqlCtx.getArgs(); // args 검증이 필요하면 여기서
    return true;
  }
}

@Subscription(() => Notification)
@UseGuards(SubscriptionAuthGuard)
notificationReceived(@Args('userId') userId: string) {
  return pubSub.asyncIterator(`notification.${userId}`);
}
```

### 연결 끊김과 백프레셔

WebSocket 연결은 의외로 자주 끊긴다. 모바일 네트워크 전환, NAT 타임아웃, 로드밸런서 idle timeout. 클라이언트 측 자동 재연결 + 서버 측 ping/pong이 둘 다 있어야 한다.

```typescript
subscriptions: {
  'graphql-ws': {
    onConnect: (ctx) => { ... },
    onDisconnect: (ctx, code, reason) => {
      logger.info('subscription disconnected', { code, reason });
    },
  },
},
```

ALB나 nginx 뒤에 있을 때는 idle timeout을 60초 이상으로 늘리거나, 클라이언트가 30초 간격으로 ping을 보내게 해야 한다. `graphql-ws`는 `keepAlive` 옵션으로 ping 주기를 잡는다.

발행 속도가 소비 속도를 추월하면 메모리에 메시지가 쌓인다. Subscription을 가벼운 알림 위주로 쓰고, 큰 데이터는 알림 + REST polling 조합으로 가는 게 안전하다. 우리도 처음엔 Subscription으로 전체 리스트를 보내다가, 결국 "이벤트 발생" 신호만 보내고 클라이언트가 다시 쿼리하는 패턴으로 바꿨다.

### 클라이언트 예시

Apollo Client 기준 클라이언트 설정은 다음과 같다.

```typescript
import { ApolloClient, InMemoryCache, split, HttpLink } from '@apollo/client';
import { GraphQLWsLink } from '@apollo/client/link/subscriptions';
import { getMainDefinition } from '@apollo/client/utilities';
import { createClient } from 'graphql-ws';

const httpLink = new HttpLink({ uri: '/graphql' });

const wsLink = new GraphQLWsLink(
  createClient({
    url: 'wss://example.com/graphql',
    connectionParams: () => ({
      authorization: `Bearer ${localStorage.getItem('token')}`,
    }),
    keepAlive: 30_000,
  }),
);

const link = split(
  ({ query }) => {
    const def = getMainDefinition(query);
    return def.kind === 'OperationDefinition' && def.operation === 'subscription';
  },
  wsLink,
  httpLink,
);

export const client = new ApolloClient({ link, cache: new InMemoryCache() });
```

토큰이 만료되면 connect 시점 인증에 실패한다. refresh token 흐름에서 새 토큰을 받은 직후 WebSocket을 재연결하도록 클라이언트 측 로직을 짜야 한다.


## 인증/인가 통합

NestJS Guard를 GraphQL에 그대로 적용하려고 하면 request 객체를 못 찾는다. GraphQL은 ExecutionContext의 형태가 HTTP와 달라서 `GqlExecutionContext`로 한 단계 변환해야 한다.

### GraphQL용 Guard

```typescript
import { ExecutionContext, Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { GqlExecutionContext } from '@nestjs/graphql';

@Injectable()
export class GqlAuthGuard extends AuthGuard('jwt') {
  getRequest(context: ExecutionContext) {
    const ctx = GqlExecutionContext.create(context);
    return ctx.getContext().req;
  }
}
```

`AuthGuard('jwt')`를 상속하고 `getRequest`만 오버라이드하면 JWT 검증 로직은 Passport가 그대로 처리한다. 이 부분을 빠뜨리면 Guard가 request를 못 찾아서 모든 요청이 401이 난다. 새 팀원이 GraphQL 처음 붙일 때마다 겪는 통과의례다.

리졸버에 적용하는 방법은 두 가지다.

```typescript
// 메서드 레벨
@Query(() => User)
@UseGuards(GqlAuthGuard)
me(@CurrentUser() user: User) {
  return user;
}

// 리졸버 클래스 레벨 (모든 메서드에 적용)
@Resolver()
@UseGuards(GqlAuthGuard)
export class UserResolver { ... }
```

### CurrentUser 데코레이터

리졸버 시그니처에서 사용자 정보를 깔끔하게 받으려면 커스텀 파라미터 데코레이터를 만든다.

```typescript
import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { GqlExecutionContext } from '@nestjs/graphql';

export const CurrentUser = createParamDecorator(
  (data: keyof User | undefined, context: ExecutionContext) => {
    const ctx = GqlExecutionContext.create(context);
    const user = ctx.getContext().req.user;
    return data ? user?.[data] : user;
  },
);
```

```typescript
@Query(() => [Order])
@UseGuards(GqlAuthGuard)
myOrders(@CurrentUser() user: User): Promise<Order[]> {
  return this.orderService.findByUserId(user.id);
}

@Query(() => String)
@UseGuards(GqlAuthGuard)
myEmail(@CurrentUser('email') email: string): string {
  return email;
}
```

### 역할 기반 권한

역할(role) 체크는 Guard + 메타데이터로 구성한다.

```typescript
import { SetMetadata } from '@nestjs/common';
import { Reflector } from '@nestjs/core';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<string[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!required) return true;
    const ctx = GqlExecutionContext.create(context);
    const user = ctx.getContext().req.user;
    return required.some((r) => user.roles?.includes(r));
  }
}
```

```typescript
@Mutation(() => Boolean)
@UseGuards(GqlAuthGuard, RolesGuard)
@Roles('admin')
async deleteUser(@Args('id', { type: () => ID }) id: string): Promise<boolean> {
  await this.userService.delete(id);
  return true;
}
```

Guard 순서가 중요하다. `GqlAuthGuard`가 먼저 user를 request에 박은 다음 `RolesGuard`가 그걸 읽는다. 순서가 바뀌면 user가 없는 상태에서 role 체크가 돌아 항상 거부된다.

### 필드 레벨 권한

REST에는 없는 개념이다. 같은 객체 안에서 어떤 필드는 본인만, 어떤 필드는 관리자만 볼 수 있게 해야 할 때가 있다.

```typescript
@ObjectType()
export class User {
  @Field(() => ID)
  id: string;

  @Field()
  name: string;

  @Field({ nullable: true })  // 본인만 보임
  email?: string;

  @Field({ nullable: true })  // 관리자만 보임
  lastLoginIp?: string;
}
```

리졸버에서 분기한다.

```typescript
@Resolver(() => User)
export class UserResolver {
  @ResolveField(() => String, { nullable: true })
  email(@Parent() user: User, @CurrentUser() me: User): string | null {
    if (me?.id === user.id || me?.roles?.includes('admin')) {
      return user.email;
    }
    return null;
  }

  @ResolveField(() => String, { nullable: true })
  lastLoginIp(@Parent() user: User, @CurrentUser() me: User): string | null {
    if (me?.roles?.includes('admin')) {
      return user.lastLoginIp;
    }
    return null;
  }
}
```

이 패턴이 늘어나면 데코레이터로 추상화하는 게 깔끔하다.

```typescript
export function FieldAuth(check: (parent: any, me: any) => boolean) {
  return (target: any, key: string, descriptor: PropertyDescriptor) => {
    const original = descriptor.value;
    descriptor.value = function (...args: any[]) {
      const parent = args[0];
      const me = args[args.length - 1]?.req?.user;
      if (!check(parent, me)) return null;
      return original.apply(this, args);
    };
  };
}
```

쓰는 측이 깔끔해지지만, 데코레이터 안에서 Context를 어떻게 꺼낼지는 리졸버 시그니처에 따라 달라진다. 모든 케이스를 한 데코레이터로 커버하기 어려워서 결국 직접 분기하는 패턴으로 돌아갔다.

### 디렉티브 기반 권한

스키마에 권한을 명시하는 방법도 있다. `@auth` 디렉티브를 만들어 SDL에 박아두면 권한 정책이 스키마에서 보인다.

```graphql
directive @auth(roles: [String!]) on FIELD_DEFINITION | OBJECT

type Query {
  adminStats: Stats @auth(roles: ["admin"])
}
```

Code First에서도 `@Directive`로 지정할 수 있다.

```typescript
@ObjectType()
export class Stats {
  @Field(() => Int)
  totalUsers: number;
}

@Resolver()
export class AdminResolver {
  @Query(() => Stats)
  @Directive('@auth(roles: ["admin"])')
  adminStats() {
    return this.statsService.compute();
  }
}
```

디렉티브를 실제로 동작시키려면 `mapSchema` 같은 함수로 스키마를 변환해 리졸버를 감싸야 한다. 손이 좀 가지만 권한 정책을 한곳에서 보고 싶을 때 가치가 있다. 우리는 외부 파트너에게 SDL을 공개하는 케이스에서 이 방식을 썼다. 파트너가 디렉티브만 봐도 어떤 필드가 어떤 권한이 필요한지 안다.

### 인가 정책 분리

권한 로직을 Guard나 리졸버에 흩뿌리지 말고, 한 곳에 모으는 게 유지보수에 좋다. CASL 같은 라이브러리를 쓰거나 자체 PolicyService를 만든다.

```typescript
@Injectable()
export class OrderPolicyService {
  canRead(actor: User, order: Order): boolean {
    if (actor.roles.includes('admin')) return true;
    return order.userId === actor.id;
  }

  canCancel(actor: User, order: Order): boolean {
    if (!this.canRead(actor, order)) return false;
    return order.status === 'PENDING' && order.userId === actor.id;
  }
}
```

리졸버는 정책 서비스에 위임한다.

```typescript
@Mutation(() => Order)
@UseGuards(GqlAuthGuard)
async cancelOrder(
  @Args('id', { type: () => ID }) id: string,
  @CurrentUser() user: User,
): Promise<Order> {
  const order = await this.orderService.findById(id);
  if (!this.orderPolicy.canCancel(user, order)) {
    throw new ForbiddenException();
  }
  return this.orderService.cancel(order);
}
```

정책 함수는 단위 테스트하기도 쉽다. 리졸버를 띄우지 않고 PolicyService만 테스트하면 권한 규칙의 회귀를 잡을 수 있다.

### Subscription의 인가

Subscription은 연결 시점 인증과 메시지 발행 시점 인가가 다르다. 연결할 때는 토큰만 보고 통과시키되, 실제 메시지가 그 사용자에게 가도 되는지는 발행 시점에 검사한다.

```typescript
@Subscription(() => OrderUpdate, {
  filter: (payload, variables, ctx) => {
    if (!ctx.user) return false;
    if (ctx.user.roles.includes('admin')) return true;
    return payload.userId === ctx.user.id;
  },
})
@UseGuards(SubscriptionAuthGuard)
orderUpdated() {
  return pubSub.asyncIterator('order.updated');
}
```

`filter`는 매 발행마다 호출되어 무거우면 비싸다. 발행 시점에 채널을 잘게 잘라(`order.updated.${userId}`) 필터를 줄이는 게 보통이다.

### 인증 컨텍스트 전파

마이크로서비스로 쪼개진 환경에서는 게이트웨이가 받은 인증 정보를 서브그래프에 전파해야 한다. Federation 절에서 다룬 `RemoteGraphQLDataSource.willSendRequest`로 헤더를 넘기는 방식이 정석이다. JWT를 그대로 전달할지, 게이트웨이에서 검증한 뒤 별도 헤더(`x-user-id`, `x-roles`)로 풀어줄지는 보안 정책에 달려있다.

JWT를 그대로 넘기는 쪽은 서브그래프에서도 한 번 더 검증해야 한다(zero trust). 별도 헤더로 푸는 쪽은 서브그래프가 게이트웨이를 신뢰해야 하고, 서브그래프가 외부에서 직접 호출되지 않게 망 분리가 필요하다.


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

Apollo Studio를 쓰면 클라이언트별로 어떤 필드가 사용되는지 추적되어 제거 시점을 판단하기 쉽다. 우리는 자체 분석 로그로 같은 효과를 냈다. 리졸버 진입점에 필드명을 기록하고 ELK로 집계했다. 한 달 동안 0건이면 제거한다는 룰을 두니 정리 작업이 의사 결정 비용 없이 굴러갔다.

### 옵저버빌리티

GraphQL은 한 요청에 여러 리졸버가 돌기 때문에 어디서 느린지 찾기 어렵다. Apollo Server의 `plugins`로 리졸버 단위 트레이싱을 켜거나, OpenTelemetry GraphQL 인스트루멘테이션을 붙이면 필드별 latency가 보인다.

```typescript
import { ApolloServerPluginLandingPageDisabled } from '@apollo/server/plugin/disabled';

GraphQLModule.forRoot({
  driver: ApolloDriver,
  plugins: [
    ApolloServerPluginLandingPageDisabled(),
    {
      async requestDidStart() {
        return {
          async didResolveOperation(ctx) {
            logger.info('operation', { name: ctx.operationName });
          },
          async willSendResponse(ctx) {
            const took = Date.now() - ctx.request.http?.startTime;
            logger.info('response', { name: ctx.operationName, took });
          },
        };
      },
    },
  ],
});
```

운영에서는 operationName이 없는 쿼리는 거부하는 정책도 검토할 만하다. 익명 쿼리는 추적이 어려워서 문제 생겼을 때 원인 파악이 힘들다.
