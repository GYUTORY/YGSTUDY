---
title: GraphQL Security
tags: [security, graphql, apollo, introspection, query-complexity, dos, persisted-query, authorization]
updated: 2026-06-21
---

# GraphQL 보안

GraphQL은 REST랑 보안 모델이 다르다. REST는 엔드포인트가 자원별로 쪼개져 있어서 URL 패턴만 봐도 어디를 통제해야 하는지 보인다. GraphQL은 엔드포인트가 `/graphql` 하나고, 그 안에서 클라이언트가 원하는 쿼리를 자유롭게 조합한다. 즉 클라이언트가 서버에 "어떤 데이터를 어떤 깊이로 가져올지"를 결정한다. 이 자유도가 GraphQL의 장점이자 공격 표면이다.

5년 동안 GraphQL을 운영하면서 사고가 났거나 날 뻔한 패턴은 거의 정해져 있다. introspection을 프로덕션에 그대로 열어둬서 스키마가 통째로 노출되거나, 쿼리 깊이 제한이 없어서 중첩 쿼리 한 방에 DB가 터지거나, alias로 같은 mutation을 수백 번 묶어 보내서 rate limit을 우회당하거나, resolver마다 인가를 따로 안 걸어서 BOLA(객체 수준 인가 깨짐)가 나거나. REST에서는 잘 안 겪는 문제들이라 처음 GraphQL을 도입하면 이 지점들을 놓치기 쉽다.

이 문서는 GraphQL에서만 발생하는 공격과 방어를 다룬다. 인증 토큰 발급이나 TLS 같은 공통 주제는 API_Security 문서에 있으니 여기서는 GraphQL 고유 문제에 집중한다.

---

## introspection 노출

GraphQL은 스키마 자체를 쿼리로 조회할 수 있다. `__schema`, `__type` 같은 메타 필드로 모든 타입, 필드, 인자, deprecated 마킹까지 다 끌어올 수 있다. GraphiQL이나 Apollo Sandbox가 자동완성을 해주는 게 이 introspection 덕분이다.

개발 단계에서는 편한데, 프로덕션에 그대로 열어두면 공격자에게 API 명세서를 통째로 넘기는 꼴이다. `deleteUser`, `internalAdminPanel` 같은 숨겨놓은 mutation도 introspection 한 방이면 다 보인다. 실제 침투 테스트에서 가장 먼저 던지는 쿼리가 introspection이다.

전형적인 introspection 쿼리는 이렇게 생겼다.

```graphql
query IntrospectionQuery {
  __schema {
    types {
      name
      fields {
        name
        args { name type { name } }
      }
    }
  }
}
```

이거 한 번이면 스키마 전체 구조가 JSON으로 떨어진다.

### Apollo Server에서 차단

Apollo Server는 `introspection` 옵션으로 끈다. 환경 변수로 프로덕션에서만 끄는 식으로 한다.

```javascript
const server = new ApolloServer({
  typeDefs,
  resolvers,
  // 프로덕션에서는 introspection 비활성화
  introspection: process.env.NODE_ENV !== 'production',
});
```

주의할 점이 있다. Apollo Server 4부터는 `introspection: false`로 꺼도 Apollo Studio의 Landing Page 플러그인이 기본으로 붙어서 `/graphql`에 GET으로 접근하면 Sandbox 페이지가 뜬다. 내부 정보가 새는 건 아니지만, 프로덕션에 이런 페이지가 노출되는 게 보안 리뷰에서 지적받는다. Landing Page도 같이 끄는 게 깔끔하다.

```javascript
import { ApolloServerPluginLandingPageProductionDefault } from '@apollo/server/plugin/landingPage/default';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: false,
  plugins: [
    // 프로덕션용 랜딩 페이지(빈 화면)로 교체
    ApolloServerPluginLandingPageProductionDefault({ footer: false }),
  ],
});
```

### graphql-java에서 차단

graphql-java는 introspection을 끄는 옵션이 별도로 없다. `IntrospectionWhitelist` 같은 게 표준에 없어서 `Instrumentation`으로 introspection 필드를 막거나, 아예 introspection을 비활성화하는 방식을 쓴다. graphql-java 16 이상은 `GraphQL.Builder`에서 introspection을 끄는 옵션을 제공한다.

```java
GraphQLSchema schema = GraphQLSchema.newSchema()
    .query(queryType)
    // introspection 비활성화
    .additionalDirective(/* ... */)
    .build();

// graphql-java 권장 방식: 별도 Instrumentation으로 __schema/__type 차단
GraphQL graphQL = GraphQL.newGraphQL(schema)
    .instrumentation(new IntrospectionDisablingInstrumentation())
    .build();
```

Spring for GraphQL을 쓴다면 더 간단하다. `application.yml`에서 끈다.

```yaml
spring:
  graphql:
    schema:
      introspection:
        enabled: false
```

introspection을 끄면 클라이언트 팀이 스키마를 못 받는다고 불평하는 경우가 있다. 그럴 때는 빌드 타임에 스키마를 SDL 파일로 export해서 별도 채널(내부 위키, 사내 스키마 레지스트리)로 공유한다. 런타임 introspection이랑 스키마 공유는 별개 문제다.

---

## 쿼리 깊이 제한 (depth limiting)

GraphQL은 관계를 따라 무한히 중첩할 수 있다. 게시글 → 작성자 → 게시글 → 작성자 → ... 이런 식으로 순환 참조가 가능한 스키마라면, 깊이 제한이 없을 때 한 번의 쿼리로 서버를 마비시킬 수 있다.

```graphql
query EvilNesting {
  post(id: 1) {
    author {
      posts {
        author {
          posts {
            author {
              posts {
                # ... 이걸 50단계 반복
              }
            }
          }
        }
      }
    }
  }
}
```

깊이가 깊어질수록 resolver 호출이 기하급수적으로 늘어난다. 각 단계가 DB 조회를 한다면 단일 요청으로 수만 건의 쿼리가 나간다. 인증도 필요 없는 공격이다. introspection이 켜져 있으면 순환 관계가 있는 타입을 찾아서 이런 쿼리를 정밀하게 만들 수 있다.

### Apollo Server에서 깊이 제한

`graphql-depth-limit` 패키지를 validation rule로 넣는다.

```javascript
import depthLimit from 'graphql-depth-limit';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  validationRules: [
    // 최대 깊이 7로 제한. 그 이상은 파싱 단계에서 거부
    depthLimit(7),
  ],
});
```

깊이를 몇으로 잡을지는 스키마에 따라 다르다. 실제 클라이언트가 보내는 가장 깊은 정상 쿼리를 로그에서 뽑아보고 거기에 여유를 1~2 더한 값으로 잡는다. 보통 7~10 사이면 정상 쿼리는 안 걸리고 공격성 쿼리만 거른다. 처음에는 넉넉하게 잡고 로그로 모니터링하다가 줄이는 게 안전하다. 너무 빡빡하게 잡으면 정상 클라이언트가 깨진다.

depth limit은 파싱·검증 단계에서 동작하므로 resolver가 한 번도 안 불린 채로 거부된다. 즉 DB 조회 전에 막힌다. 이게 핵심이다.

### graphql-java에서 깊이 제한

graphql-java는 `MaxQueryDepthInstrumentation`을 기본 제공한다.

```java
GraphQL graphQL = GraphQL.newGraphQL(schema)
    .instrumentation(new MaxQueryDepthInstrumentation(10))
    .build();
```

깊이를 초과하면 `AbortExecutionException`이 던져지고 쿼리가 실행 전에 중단된다. 여러 Instrumentation을 같이 쓸 때는 `ChainedInstrumentation`으로 묶는다.

```java
List<Instrumentation> chain = List.of(
    new MaxQueryDepthInstrumentation(10),
    new MaxQueryComplexityInstrumentation(200)
);

GraphQL graphQL = GraphQL.newGraphQL(schema)
    .instrumentation(new ChainedInstrumentation(chain))
    .build();
```

---

## 쿼리 복잡도 분석 (query cost analysis)

깊이 제한만으로는 부족하다. 깊이는 얕아도 한 단계에서 많은 데이터를 요청하면 부하가 크다. 예를 들어 `users(first: 10000) { posts(first: 10000) { comments(first: 10000) } }`는 깊이가 3밖에 안 되지만 10000 × 10000 × 10000 건을 요청한다. 깊이 제한은 이걸 못 막는다.

복잡도 분석은 각 필드에 비용 점수를 매기고, 쿼리 전체 비용이 한도를 넘으면 거부한다. 리스트 필드는 인자(`first`, `limit`)를 곱셈 계수로 반영한다.

### Apollo Server에서 복잡도 제한

`graphql-query-complexity`를 쓴다. 필드별 비용을 directive나 estimator로 정의한다.

```javascript
import { createComplexityRule, simpleEstimator } from 'graphql-query-complexity';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  validationRules: [
    createComplexityRule({
      maximumComplexity: 1000,
      // 인자 기반 비용 계산 + 기본 비용 1
      estimators: [
        fieldExtensionsEstimator(),
        simpleEstimator({ defaultComplexity: 1 }),
      ],
      onComplete: (complexity) => {
        // 모니터링용. 어떤 쿼리가 비용이 큰지 로그로 추적
        console.log('Query complexity:', complexity);
      },
    }),
  ],
});
```

스키마에서 필드별 비용을 directive로 지정한다.

```graphql
type Query {
  # 리스트 조회는 first 인자만큼 비용이 곱해짐
  users(first: Int): [User] @complexity(value: 1, multipliers: ["first"])
}
```

실무에서는 `onComplete` 콜백을 먼저 붙여서 실제 트래픽의 복잡도 분포를 며칠 모니터링한다. 그 분포를 보고 `maximumComplexity`를 정한다. 처음부터 한도를 걸면 정상 쿼리가 막혀서 장애로 이어진다. 모니터링 → 한도 설정 → 점진적 강화 순서로 가야 한다.

### graphql-java에서 복잡도 제한

graphql-java는 `MaxQueryComplexityInstrumentation`을 제공한다. 필드별 복잡도 계산 함수를 넘긴다.

```java
FieldComplexityCalculator calculator = (env, childComplexity) -> {
    // first 인자가 있으면 그 값만큼 곱하고, 없으면 기본 1 + 자식 복잡도
    Integer first = env.getArguments().containsKey("first")
        ? (Integer) env.getArguments().get("first")
        : 1;
    return first * (1 + childComplexity);
};

GraphQL graphQL = GraphQL.newGraphQL(schema)
    .instrumentation(new MaxQueryComplexityInstrumentation(200, calculator))
    .build();
```

복잡도 계산 로직은 스키마마다 직접 짜야 해서 손이 좀 간다. 그래도 리스트 인자를 곱셈으로 반영하는 것만 제대로 해도 대부분의 폭주 쿼리는 잡힌다.

---

## 배치 공격 (aliasing / batching)

GraphQL의 alias 기능을 악용하면 rate limit을 우회할 수 있다. 보통 rate limit은 "HTTP 요청 N건/분"으로 거는데, GraphQL은 단일 HTTP 요청 안에 여러 작업을 넣을 수 있어서 요청 수 기준 제한이 무력화된다.

```graphql
mutation BruteForce {
  attempt1: login(user: "admin", pass: "1234") { token }
  attempt2: login(user: "admin", pass: "1235") { token }
  attempt3: login(user: "admin", pass: "1236") { token }
  # ... 같은 요청 안에 1000개 alias
  attempt1000: login(user: "admin", pass: "9999") { token }
}
```

HTTP 요청은 1건이지만 실제로는 로그인 시도 1000번이다. 요청 수 기반 rate limit은 이걸 1건으로 센다. 비밀번호 무차별 대입, OTP 무차별 대입이 이런 식으로 들어온다.

배치 쿼리(여러 operation을 배열로 전송)도 비슷한 우회 경로다. Apollo Server는 `allowBatchedHttpRequests`가 기본 비활성화지만, 켜놨다면 한 HTTP 요청에 여러 operation이 들어온다.

방어는 두 갈래다.

첫째, 같은 필드의 alias 개수를 제한한다. 동일 필드가 한 쿼리에서 N번 이상 등장하면 거부한다. `graphql-no-alias` 같은 validation rule을 쓰거나 직접 작성한다.

```javascript
// 동일 필드의 alias 호출 횟수를 세는 커스텀 validation rule
function aliasLimitRule(maxAliases) {
  return (context) => {
    const counts = {};
    return {
      Field(node) {
        const name = node.name.value;
        counts[name] = (counts[name] || 0) + 1;
        if (counts[name] > maxAliases) {
          context.reportError(
            new GraphQLError(`Field "${name}" aliased too many times`)
          );
        }
      },
    };
  };
}

const server = new ApolloServer({
  typeDefs,
  resolvers,
  validationRules: [aliasLimitRule(10)],
});
```

둘째, rate limit을 HTTP 요청 수가 아니라 작업 단위로 건다. `login` resolver 안에서 IP·계정 기준 카운터를 증가시킨다. resolver 레벨에서 세면 alias로 묶어 보내도 1000번 다 카운트된다. 무차별 대입 방어는 결국 resolver 레벨 rate limit이 본질이다. HTTP 게이트웨이 rate limit만 믿으면 안 된다.

배치 HTTP 요청은 꼭 필요한 게 아니면 끈다.

```javascript
const server = new ApolloServer({
  typeDefs,
  resolvers,
  allowBatchedHttpRequests: false, // 기본값이지만 명시
});
```

---

## N+1 기반 DoS

N+1은 보통 성능 문제로 이야기하는데, GraphQL에서는 DoS 벡터가 된다. 리스트를 조회하고 각 항목마다 연관 데이터를 resolver가 따로 가져오면, 100개 항목에 대해 1(리스트) + 100(연관) = 101번 쿼리가 나간다. 여기에 깊이까지 더해지면 폭발한다.

```graphql
query {
  posts(first: 100) {      # 1번 쿼리
    author {               # 항목마다 1번씩 → 100번 쿼리
      followers(first: 100) {  # 다시 항목마다 → 10000번 쿼리
        name
      }
    }
  }
}
```

복잡도 제한으로 일부 막히지만, 근본 해결은 DataLoader로 같은 키 조회를 배치·캐싱하는 것이다. DataLoader는 한 틱 안에 모인 키를 모아서 `IN (...)` 한 방으로 조회한다. 100번 나갈 쿼리가 1번으로 줄어든다.

```javascript
import DataLoader from 'dataloader';

// 요청마다 새 DataLoader 인스턴스 생성 (요청 간 캐시 공유 금지)
function createLoaders() {
  return {
    userLoader: new DataLoader(async (userIds) => {
      // userIds = [1, 2, 3, ...] 한 번에 조회
      const users = await db.user.findMany({ where: { id: { in: userIds } } });
      // 입력 키 순서대로 정렬해서 반환 (DataLoader 규약)
      const map = new Map(users.map((u) => [u.id, u]));
      return userIds.map((id) => map.get(id));
    }),
  };
}

const server = new ApolloServer({ typeDefs, resolvers });

await startStandaloneServer(server, {
  context: async () => ({ loaders: createLoaders() }),
});
```

DataLoader에서 자주 하는 실수가 두 가지 있다. 하나는 반환 배열 순서를 입력 키 순서랑 안 맞추는 것이다. DataLoader는 입력 키와 같은 인덱스에 결과가 있다고 가정한다. DB가 정렬을 보장 안 하므로 위 예제처럼 Map으로 다시 매핑해야 한다. 안 그러면 엉뚱한 사용자 데이터가 섞여서 나간다. 이건 보안 사고다.

다른 하나는 DataLoader를 요청 간에 재사용하는 것이다. DataLoader는 내부에 캐시를 들고 있어서 전역으로 만들면 A 사용자가 조회한 데이터를 B 사용자가 그대로 받는다. 반드시 요청마다 새로 만든다.

graphql-java 쪽은 `org.dataloader.DataLoader`를 `DataLoaderRegistry`에 등록해서 쓴다. Spring for GraphQL은 `BatchLoaderRegistry`로 등록하면 `@BatchMapping`이 알아서 배치 처리한다.

```java
@Controller
public class PostController {

    // author 필드를 항목별이 아니라 배치로 한 번에 로드
    @BatchMapping
    public Map<Post, Author> author(List<Post> posts) {
        List<Long> authorIds = posts.stream()
            .map(Post::getAuthorId).toList();
        Map<Long, Author> authors = authorRepository.findAllById(authorIds)
            .stream().collect(Collectors.toMap(Author::getId, a -> a));
        return posts.stream()
            .collect(Collectors.toMap(p -> p, p -> authors.get(p.getAuthorId())));
    }
}
```

---

## 필드 레벨 인가

GraphQL 인가에서 가장 많이 깨지는 지점이다. REST는 엔드포인트 단위라 컨트롤러 앞단에서 한 번 막으면 되는데, GraphQL은 같은 객체라도 클라이언트가 어떤 필드를 요청할지 모른다. `User` 타입에 `email`, `phone`, `salary` 같은 민감 필드가 있다면, 필드별로 누가 볼 수 있는지를 따로 통제해야 한다.

흔한 사고가 이거다. `me { email }`은 본인 거니까 잘 막아놨는데, `user(id: 999) { email }`로 남의 이메일을 조회하는 경로는 안 막은 경우. 객체 레벨 인가(BOLA)가 깨진 전형적인 케이스다. resolver마다 "지금 이 요청자가 이 객체의 이 필드를 볼 권한이 있는가"를 검사해야 한다.

인가는 게이트웨이나 미들웨어 한 곳이 아니라 resolver 안에서 하는 게 원칙이다. 쿼리가 어떤 필드를 타고 들어올지 미리 알 수 없기 때문이다.

```javascript
const resolvers = {
  User: {
    // email은 본인 또는 관리자만 조회 가능
    email: (parent, args, context) => {
      const requester = context.user;
      if (!requester) throw new GraphQLError('Unauthorized');
      if (requester.id !== parent.id && requester.role !== 'ADMIN') {
        throw new GraphQLError('Forbidden');
      }
      return parent.email;
    },
    // salary는 관리자만
    salary: (parent, args, context) => {
      if (context.user?.role !== 'ADMIN') {
        throw new GraphQLError('Forbidden');
      }
      return parent.salary;
    },
  },
};
```

필드마다 이렇게 쓰면 코드가 장황해진다. 스키마 directive로 선언적으로 거는 방식을 많이 쓴다.

```graphql
type User {
  id: ID!
  name: String!
  email: String! @auth(requires: SELF_OR_ADMIN)
  salary: Int @auth(requires: ADMIN)
}
```

`@auth` directive를 처리하는 로직을 한 곳에 모아두면 스키마만 봐도 어떤 필드가 어떤 권한을 요구하는지 보인다. graphql-java는 `SchemaDirectiveWiring`로 같은 패턴을 구현한다. Apollo Server 4는 directive를 `mapSchema`로 처리한다.

인가 에러를 던질 때 주의할 게 있다. 권한 없는 필드에 `Forbidden`을 던지면 "그 필드가 존재한다"는 정보가 새는 경우가 있다. 민감한 경우는 필드 자체를 null로 처리하고 에러를 안 던지는 방식을 쓰기도 한다. 이건 보안 요구사항에 따라 결정한다.

---

## persisted query

클라이언트가 임의 쿼리를 보낼 수 있다는 것 자체가 공격 표면이다. 모바일 앱이나 웹 프론트처럼 쿼리가 정해져 있는 클라이언트라면, 미리 등록된 쿼리만 허용하는 persisted query가 강력한 방어다.

동작 방식은 이렇다. 빌드 타임에 클라이언트가 쓰는 모든 쿼리를 해시로 만들어 서버에 등록한다. 런타임에는 클라이언트가 쿼리 전문 대신 해시만 보낸다. 서버는 등록된 해시인지 확인하고, 맞으면 미리 저장해둔 쿼리를 실행한다.

이걸 "allowlist" 모드로 쓰면 등록 안 된 쿼리는 전부 거부된다. introspection 공격, 깊이 폭탄, alias 배치 공격이 한 번에 막힌다. 임의 쿼리 자체가 불가능하니까. 깊이 제한이나 복잡도 분석보다 근본적인 방어다.

Apollo는 APQ(Automatic Persisted Queries)와 등록형 persisted query를 둘 다 지원한다. 주의할 점은 APQ랑 보안용 allowlist를 헷갈리면 안 된다는 것이다.

APQ는 처음 보는 해시면 서버가 클라이언트에 "쿼리 전문 보내줘"라고 요청하고, 받은 쿼리를 캐시에 등록한다. 즉 새 쿼리를 클라이언트가 등록할 수 있다. 이건 네트워크 대역폭 최적화 용도지 보안이 아니다. 공격자도 자기 쿼리를 등록할 수 있으니까.

보안용으로 쓰려면 빌드 타임에 만든 manifest만 허용하고 런타임 등록을 막는 allowlist 모드로 설정해야 한다.

```javascript
import { ApolloServerPluginUsageReporting } from '@apollo/server/plugin/usageReporting';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  persistedQueries: {
    // 빌드 타임에 생성한 manifest만 허용. 런타임 등록 차단
    ttl: null,
  },
  plugins: [
    // 등록 안 된 쿼리 거부 플러그인 (Apollo의 operation registry)
  ],
});
```

persisted query는 외부 파트너에게 공개하는 퍼블릭 API에는 못 쓴다. 그쪽은 쿼리를 우리가 통제 못 하니까. 사내 클라이언트(자사 앱, 자사 웹)에만 적용하고, 퍼블릭 API는 깊이·복잡도 제한으로 방어하는 식으로 나눈다.

---

## 에러 메시지로 정보 노출

GraphQL은 에러를 친절하게 돌려주는 경향이 있다. 개발 환경에서는 stack trace, DB 쿼리, 내부 경로까지 에러 응답에 담긴다. 이게 프로덕션에 그대로 나가면 내부 구조가 새고, SQL 에러 메시지로 인젝션 가능 지점을 알려주는 꼴이 된다.

Apollo Server는 `NODE_ENV=production`이면 stack trace를 자동으로 숨기지만, 에러 메시지 본문은 그대로 나간다. `formatError`로 프로덕션에서 메시지를 정제한다.

```javascript
const server = new ApolloServer({
  typeDefs,
  resolvers,
  formatError: (formattedError, error) => {
    // 내부 에러는 로깅만 하고 클라이언트에는 일반 메시지
    if (formattedError.extensions?.code === 'INTERNAL_SERVER_ERROR') {
      logger.error(error); // 서버 로그에는 원본 남김
      return { message: 'Internal server error' };
    }
    return formattedError;
  },
});
```

validation 에러도 정보를 흘린다. introspection을 꺼놨는데 `__schema`를 쿼리하면 "Cannot query field __schema"라는 에러가 나온다. 이걸로 introspection이 꺼져 있다는 사실은 알 수 있지만 스키마 자체는 안 새니까 보통은 그냥 둔다. 다만 "Did you mean ...?" 같은 필드 추천 메시지는 꺼야 한다. 존재하는 필드 이름을 추천해주면 스키마를 추측당한다.

```javascript
import { NoSchemaIntrospectionCustomRule } from 'graphql';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  validationRules: [NoSchemaIntrospectionCustomRule], // introspection 쿼리 자체를 검증 단계에서 거부
});
```

---

## 트러블슈팅 사례

**introspection을 껐는데 클라이언트 빌드가 깨진다**

GraphQL Code Generator 같은 도구가 빌드 타임에 introspection으로 스키마를 가져오는 경우가 있다. 프로덕션 엔드포인트에서 introspection을 끄면 이게 실패한다. 해결은 스키마 SDL 파일을 git에 커밋하거나 스키마 레지스트리에서 받아오게 바꾸는 것이다. 런타임 introspection에 의존하던 빌드 파이프라인을 정적 스키마 기반으로 옮긴다.

**깊이 제한을 걸었더니 정상 쿼리가 막힌다**

depth limit을 너무 낮게(예: 5) 잡으면 중첩이 정상적으로 깊은 쿼리가 걸린다. 프래그먼트를 많이 쓰는 쿼리는 펼쳤을 때 깊이가 예상보다 깊다. validation 에러 로그에서 막힌 쿼리들을 뽑아보고, 정상 쿼리면 한도를 올린다. 깊이는 처음에 넉넉히 잡고 모니터링하면서 조이는 게 맞다.

**복잡도 계산이 실제 부하랑 안 맞는다**

필드별 비용을 균일하게 1로 잡으면, 가벼운 필드 100개랑 무거운 조인 1개가 같은 비용으로 계산된다. 실제로 부하를 만드는 필드(조인, 외부 API 호출, 집계 쿼리)에 높은 비용을 따로 매겨야 한다. 슬로우 쿼리 로그랑 복잡도 점수를 대조해서 비용을 보정한다.

**DataLoader를 넣었는데 N+1이 그대로다**

resolver에서 DataLoader 인스턴스를 안 거치고 직접 DB를 조회하는 코드가 남아있는 경우다. 또는 DataLoader를 매 resolver 호출마다 새로 만들어서(요청 단위가 아니라 필드 단위로) 배치가 안 모이는 경우도 있다. DataLoader는 요청당 하나, 그리고 모든 연관 조회가 그 인스턴스를 거쳐야 배치가 동작한다. DB 쿼리 로그를 켜고 실제 나가는 쿼리 수를 세서 확인한다.

**alias 제한을 걸었더니 정상 배치 쿼리가 막힌다**

한 화면에서 여러 항목을 alias로 묶어 조회하는 정상 패턴이 있다. alias 개수를 너무 빡빡하게 잡으면 이게 걸린다. 무차별 대입이 우려되는 mutation(login, verifyOtp 등)에만 별도로 낮은 한도를 걸고, 일반 query는 한도를 넉넉히 두거나 복잡도 제한으로 대체하는 식으로 나눈다.

---

## 정리

GraphQL 보안은 결국 "클라이언트가 쿼리 형태를 결정한다"는 특성에서 출발한다. REST처럼 엔드포인트 앞단에서 한 번 막는 모델이 안 통하므로, 파싱·검증 단계(introspection 차단, 깊이·복잡도 제한, alias 제한)와 resolver 단계(필드 레벨 인가, resolver 레벨 rate limit, DataLoader)를 같이 깔아야 한다.

우선순위를 잡자면, 프로덕션 introspection 차단과 깊이 제한은 도입 즉시 건다. 복잡도 분석과 필드 레벨 인가는 스키마를 보면서 점진적으로 강화한다. 사내 클라이언트만 쓰는 API라면 persisted query allowlist로 임의 쿼리 자체를 막는 게 가장 확실하다.
