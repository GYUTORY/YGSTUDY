---
title: AWS AppSync (관리형 GraphQL API)
tags: [aws, graphql, cloud]
updated: 2026-07-03
---

# AWS AppSync (관리형 GraphQL API)

## 개요

AppSync는 GraphQL API를 서버 없이 굴리게 해주는 관리형 서비스다. 스키마를 올리고, 각 필드에 리졸버를 붙이고, 리졸버가 DynamoDB·Lambda·RDS 같은 데이터소스를 직접 호출한다. GraphQL 서버를 EC2나 ECS에 직접 띄우고 스키마 파싱, 쿼리 실행, 구독용 WebSocket 연결까지 다 관리하던 걸 AppSync가 대신 맡는다.

실무에서 AppSync를 꺼내는 순간은 대체로 이렇다. 모바일이나 SPA 프론트엔드가 한 화면에서 여러 리소스를 조합해서 불러와야 하는데, REST로 짜면 요청이 5~6번 나가거나 백엔드에서 화면 전용 응답을 매번 만들어줘야 할 때. 그리고 실시간 갱신(채팅, 주문 상태, 알림)이 필요할 때. 이 두 가지가 겹치면 AppSync가 REST보다 손이 덜 간다.

반대로 이 조건이 아니면 굳이 GraphQL을 쓸 이유가 약하다. 아래에서 그 경계선부터 정리한다.

리전과 계정 ID는 예제 전체에서 `ap-northeast-2`(서울), `123456789012`를 쓴다. 본인 환경 값으로 바꿔서 실행해야 한다.

## REST(API Gateway)와 갈리는 기준

둘 다 프론트엔드가 붙는 API 앞단이지만 성격이 다르다. AppSync를 쓸지 API Gateway를 쓸지는 취향이 아니라 트래픽 모양으로 갈린다.

| 상황 | 선택 |
|------|------|
| 클라이언트가 필요한 필드만 골라 받고 싶다 | AppSync |
| 화면마다 조합할 리소스가 달라 응답 형태가 자주 바뀐다 | AppSync |
| 실시간 push(구독)가 필요하다 | AppSync |
| 서버 간 통신, 웹훅 수신, 단순 CRUD 엔드포인트 | API Gateway |
| 파일 업로드/다운로드, 바이너리 응답 | API Gateway |
| 외부에 공개하는 공용 API, OpenAPI 스펙 배포 | API Gateway |

GraphQL의 장점은 오버페칭·언더페칭을 클라이언트가 직접 조절한다는 데 있다. 화면 A는 사용자 이름만, 화면 B는 이름+주문내역+포인트를 한 번에 가져가는 식이다. REST면 이런 화면별 차이를 백엔드가 엔드포인트로 흡수해야 하는데, GraphQL은 클라이언트 쿼리로 흡수한다.

그런데 이 장점이 그대로 함정이 되기도 한다. 클라이언트가 필드를 마음대로 조합한다는 건, 특정 필드 조합이 백엔드에 얼마나 부하를 줄지 예측이 어렵다는 뜻이다. REST는 엔드포인트 단위로 캐시하고 rate limit을 걸기 쉬운데, GraphQL은 쿼리 하나가 리졸버 수십 개를 타면서 DB를 두들길 수 있다. 그래서 공개 API를 GraphQL로 여는 건 신중해야 하고, 사내 프론트엔드처럼 쿼리 패턴을 어느 정도 통제할 수 있는 환경에서 쓰는 게 안전하다.

서버 간 통신에 GraphQL을 쓰는 것도 대체로 과하다. 백엔드끼리는 어차피 필요한 필드가 고정돼 있어서 오버페칭 문제가 없고, GraphQL 클라이언트 세팅이 REST 호출보다 번거롭다. 이 경우는 API Gateway나 직접 호출이 낫다.

## 스키마와 리졸버 구조

AppSync의 기본 단위는 스키마(SDL)와 리졸버다. 스키마는 타입과 필드를 선언하고, 리졸버는 특정 필드가 요청될 때 어떤 데이터소스를 어떻게 호출할지 정의한다.

```graphql
type User {
  id: ID!
  name: String!
  email: String!
  orders: [Order!]!
}

type Order {
  id: ID!
  amount: Int!
  status: OrderStatus!
}

enum OrderStatus {
  PENDING
  PAID
  SHIPPED
}

type Query {
  getUser(id: ID!): User
}

type Mutation {
  createOrder(userId: ID!, amount: Int!): Order
}

type Subscription {
  onOrderStatusChanged(userId: ID!): Order
    @aws_subscribe(mutations: ["updateOrderStatus"])
}
```

여기서 리졸버가 붙는 지점은 두 종류다. 하나는 최상위 필드(`Query.getUser`, `Mutation.createOrder`)이고, 다른 하나는 타입 안의 관계 필드(`User.orders`)다. 후자를 놓치면 바로 N+1이 터지는데, 이건 뒤에서 따로 다룬다.

리졸버는 두 가지 방식으로 짤 수 있다. 예전부터 있던 VTL(Velocity Template Language)과 이후 나온 JavaScript 리졸버(APPSYNC_JS 런타임)다.

## VTL 리졸버와 JS 리졸버

VTL은 AppSync 초기부터 쓰던 매핑 템플릿 언어다. 요청 템플릿에서 GraphQL 인자를 데이터소스 요청으로 변환하고, 응답 템플릿에서 데이터소스 결과를 GraphQL 응답으로 변환한다.

DynamoDB에서 사용자를 조회하는 VTL 요청 템플릿:

```vtl
{
    "version": "2018-05-29",
    "operation": "GetItem",
    "key": {
        "id": $util.dynamodb.toDynamoDBJson($ctx.args.id)
    }
}
```

응답 템플릿:

```vtl
$util.toJson($ctx.result)
```

VTL의 문제는 디버깅이다. 자바 기반 템플릿 언어라 자바스크립트처럼 로직을 짜기 어렵고, `if`/`foreach` 정도는 되지만 조금만 복잡해지면 읽기 힘들어진다. 에러가 나도 스택트레이스가 친절하지 않다. 그래서 2023년 이후 새로 짜는 리졸버는 JS 리졸버를 쓰는 쪽으로 많이 넘어갔다.

같은 조회를 JS 리졸버로 짜면:

```javascript
import { util } from '@aws-appsync/utils';

export function request(ctx) {
  return {
    operation: 'GetItem',
    key: util.dynamodb.toMapValues({ id: ctx.args.id }),
  };
}

export function response(ctx) {
  if (ctx.error) {
    util.error(ctx.error.message, ctx.error.type);
  }
  return ctx.result;
}
```

JS 리졸버는 익숙한 문법으로 짜고 `console.log`로 값을 찍어볼 수 있어서 디버깅이 훨씬 낫다. 다만 APPSYNC_JS 런타임은 일반 Node.js가 아니다. 표준 라이브러리 상당수가 빠져 있고 `async`/`await`, 네트워크 호출, 대부분의 npm 패키지를 못 쓴다. 리졸버는 순수 변환 함수여야 한다는 제약이 있다. 무거운 로직이 필요하면 그건 리졸버에서 하지 말고 Lambda 데이터소스로 넘겨야 한다.

기존 VTL 리졸버를 굳이 다 갈아엎을 필요는 없다. 잘 돌아가는 VTL은 두고, 새로 만들거나 복잡한 로직이 필요한 리졸버만 JS로 짜는 식으로 섞어 쓴다. 한 API 안에 두 방식이 공존해도 문제없다.

## 데이터소스 연결

AppSync 리졸버가 붙을 수 있는 데이터소스는 DynamoDB, Lambda, RDS(Aurora Serverless Data API), OpenSearch, HTTP, EventBridge 등이다. 실무에서 대부분 DynamoDB와 Lambda를 쓰고, 관계형 데이터가 필요하면 RDS를 붙인다.

### DynamoDB

가장 궁합이 좋다. AppSync가 DynamoDB 연동 헬퍼(`util.dynamodb.*`)를 기본 제공하고, GetItem·PutItem·Query·Scan을 리졸버에서 바로 호출한다. 단순 CRUD는 Lambda 없이 리졸버만으로 끝난다.

주의할 건 DynamoDB 데이터 모델링을 GraphQL 스키마에 맞춰야지, 그 반대로 하면 안 된다는 점이다. GraphQL은 관계를 자유롭게 표현하지만 DynamoDB는 파티션 키 기준으로만 효율적으로 조회된다. `User.orders`를 매번 Scan으로 긁으면 데이터가 늘수록 죽는다. 접근 패턴을 먼저 정하고 GSI(Global Secondary Index)를 설계한 다음 스키마를 얹어야 한다.

### Lambda

리졸버에서 처리하기엔 로직이 복잡하거나, 여러 소스를 조합해야 하거나, 외부 API를 호출해야 할 때 Lambda 데이터소스를 쓴다. 리졸버는 이벤트만 넘기고 실제 처리는 Lambda가 한다.

```javascript
export function request(ctx) {
  return {
    operation: 'Invoke',
    payload: {
      field: ctx.info.fieldName,
      arguments: ctx.args,
      identity: ctx.identity,
    },
  };
}

export function response(ctx) {
  return ctx.result;
}
```

Lambda 쪽에서 `event.field`로 어떤 필드가 호출됐는지 분기한다. 필드마다 Lambda를 따로 두기보다 하나의 Lambda에서 필드로 라우팅하는 경우가 많은데, 이러면 콜드 스타트 대상이 하나로 줄어서 지연이 덜하다. 대신 Lambda가 비대해지므로 도메인 단위로 쪼개는 균형을 잡아야 한다.

### RDS

Aurora Serverless의 Data API를 통해 SQL을 실행한다. RDS Proxy가 아니라 Data API라는 점이 중요하다. 커넥션 풀을 AppSync가 직접 관리하지 않고 HTTP 기반으로 쿼리를 던진다. 관계형 조인이 자연스러운 데이터라면 DynamoDB로 억지로 모델링하는 것보다 RDS가 낫다.

Data API는 초당 쿼리 수 제한과 요청당 결과 크기 제한(기본 1MB)이 있어서 대량 조회에는 안 맞는다. 페이지네이션을 반드시 걸어야 하고, 리포팅성 대용량 쿼리는 AppSync 경로가 아니라 별도 배치로 빼는 게 맞다.

## N+1을 리졸버에서 잡기

GraphQL을 쓰면 반드시 만나는 문제다. 다음 쿼리를 보자.

```graphql
query {
  listUsers {
    id
    name
    orders {
      id
      amount
    }
  }
}
```

`listUsers`가 사용자 100명을 반환하면, 각 사용자의 `orders` 필드 리졸버가 100번 따로 호출된다. 사용자 목록 쿼리 1번 + 주문 조회 100번 = 101번의 DB 호출. 이게 N+1이다. 사용자가 늘수록 선형으로 호출이 늘어서 응답이 느려지고 DynamoDB RCU나 RDS 커넥션을 잡아먹는다.

AppSync에서 이걸 잡는 방법은 배치 리졸버다. DynamoDB의 경우 `BatchGetItem`이나 `BatchInvoke`(Lambda)를 쓴다. AppSync는 같은 부모 타입의 자식 필드 리졸버 호출을 모아서 한 번에 넘겨주는 배치 기능을 제공한다.

Lambda 데이터소스에서 배치를 쓰려면 리졸버에 `Invoke`가 아니라 `BatchInvoke`를 지정한다.

```javascript
export function request(ctx) {
  return {
    operation: 'BatchInvoke',
    payload: { userId: ctx.source.id },
  };
}

export function response(ctx) {
  return ctx.result;
}
```

이렇게 하면 AppSync가 100명분의 `ctx.source.id`를 모아서 Lambda를 **한 번** 호출하고, payload를 배열로 넘긴다. Lambda는 배열을 받아서 `userId in (...)` 형태로 한 번에 조회하고, 입력 순서와 같은 순서의 배열로 응답해야 한다. 순서가 어긋나면 엉뚱한 사용자에게 남의 주문이 붙는다. 이 순서 보장이 배치 리졸버에서 가장 실수하기 쉬운 부분이다.

```javascript
// Lambda handler
exports.handler = async (event) => {
  // event는 [{ userId: 'u1' }, { userId: 'u2' }, ...] 형태
  const userIds = event.map((e) => e.userId);
  const rows = await queryOrdersByUserIds(userIds);

  // 입력 순서대로 매핑해서 반환
  const byUser = {};
  for (const row of rows) {
    (byUser[row.userId] ||= []).push(row);
  }
  return event.map((e) => byUser[e.userId] || []);
};
```

배치 크기는 기본 최대 5개, 설정으로 최대 2000개까지 올린다. 사용자가 500명이면 배치 크기가 5일 때 100번 호출로 쪼개지므로, 목록이 클 것 같으면 배치 크기를 넉넉히 잡아야 효과가 난다. 배치를 걸어놓고도 크기가 작아서 N+1이 여전한 경우가 있다.

DynamoDB 직결 리졸버라면 `BatchGetItem`으로 같은 효과를 낸다. 다만 BatchGetItem은 키 목록으로 조회하는 거라 `User.orders`처럼 1:N 관계에는 안 맞고, GSI Query를 배치로 묶기 어렵다. 이런 1:N 관계는 Lambda 배치로 처리하는 게 현실적이다.

## 구독(Subscription) 기반 실시간 처리

AppSync 구독은 WebSocket 위에서 돈다. 클라이언트가 구독을 걸면 AppSync가 WebSocket 연결을 유지하다가, 연결된 뮤테이션이 실행되면 그 결과를 구독자에게 밀어준다. 채팅, 주문 상태 실시간 반영, 알림 배지 같은 데 쓴다.

핵심은 구독이 뮤테이션에 묶여 있다는 점이다. 앞의 스키마에서:

```graphql
type Subscription {
  onOrderStatusChanged(userId: ID!): Order
    @aws_subscribe(mutations: ["updateOrderStatus"])
}
```

`@aws_subscribe`가 `updateOrderStatus` 뮤테이션에 이 구독을 연결한다. 즉 누군가 `updateOrderStatus`를 호출해서 성공하면, 그 반환값이 `onOrderStatusChanged`를 구독 중인 클라이언트에게 자동으로 전달된다. 별도의 push 코드를 짤 필요가 없다.

여기서 실무에서 자주 막히는 지점이 두 개다.

첫째, 구독은 뮤테이션의 **반환값**만 받는다. `updateOrderStatus`가 `Order`의 일부 필드만 반환하도록 짜여 있으면, 구독자도 그 일부 필드만 받는다. 구독 쿼리에서 뮤테이션이 반환하지 않은 필드를 요청하면 `null`이 온다. 그래서 구독에 물릴 뮤테이션은 구독자가 필요로 하는 필드를 다 반환하도록 설계해야 한다.

둘째, 필터링이다. `onOrderStatusChanged(userId: ID!)`처럼 인자를 주면 AppSync가 뮤테이션 반환값 중 `userId`가 일치하는 구독자에게만 전달한다. 이 필터는 뮤테이션 반환 객체에 `userId` 필드가 실제로 들어 있어야 동작한다. 뮤테이션이 `userId`를 반환하지 않으면 필터가 걸리지 않아서 모든 구독자에게 뿌려지거나 아무에게도 안 간다. 구독 인자로 쓰는 필드는 반드시 뮤테이션 응답에 포함시켜야 한다.

서버(백엔드 배치, Lambda)에서 구독을 트리거하고 싶을 때도 방법은 같다. 백엔드가 직접 push하는 API는 없고, 백엔드가 해당 뮤테이션을 호출하면 된다. 주문 상태를 배치가 바꿨다면, 배치가 `updateOrderStatus` 뮤테이션을 AppSync에 호출하고, 그러면 연결된 구독자에게 전달된다. 이때 백엔드용 인증(IAM이나 API Key)으로 뮤테이션을 호출한다.

## 인증 방식별 주의점

AppSync는 API Key, Cognito User Pools, IAM, OIDC, Lambda Authorizer를 지원한다. 한 API에 여러 방식을 동시에 붙일 수도 있다(기본 방식 하나 + 추가 방식들). 각 방식이 실무에서 걸리는 지점이 다르다.

### API Key

가장 간단하다. 키 하나로 인증하고 프론트엔드 코드에 넣어 쓴다. 문제는 **키에 만료가 있다는 것**이다. 기본 7일, 최대 365일이다. 최대로 잡아도 1년 뒤엔 만료돼서 API가 통째로 죽는다. API Key를 프로덕션 사용자 인증에 쓰면 안 되는 이유가 이거다. 개발·테스트나 공개 읽기 전용 데이터(누구나 봐도 되는 것)에만 쓴다. 만료 갱신을 깜빡해서 서비스가 멈추는 사고가 실제로 난다.

### Cognito User Pools

실제 사용자 인증에 가장 많이 쓴다. 로그인한 사용자의 토큰으로 인증하고, Cognito 그룹을 필드 단위 권한(`@aws_auth`)에 연결한다.

```graphql
type Mutation {
  deleteUser(id: ID!): Boolean
    @aws_auth(cognito_groups: ["Admin"])
}
```

리졸버 안에서는 `ctx.identity`로 로그인 정보를 꺼낸다. `ctx.identity.sub`(사용자 고유 ID), `ctx.identity.claims`(토큰 클레임), `ctx.identity.groups`(그룹)를 데이터 필터링에 쓴다. 예를 들어 사용자가 자기 데이터만 보게 하려면 리졸버에서 `ctx.identity.sub`와 조회 대상의 소유자를 비교한다. 이 검증을 리졸버에서 안 하고 스키마 레벨 권한만 믿으면, 로그인한 사용자가 남의 `userId`를 인자로 넣어 남의 데이터를 긁어가는 구멍이 생긴다. 필드 접근 권한과 데이터 소유권 검증은 별개다.

### IAM

서버 간 호출이나 다른 AWS 서비스가 AppSync를 호출할 때 쓴다. SigV4 서명으로 인증한다. Lambda가 AppSync 뮤테이션을 호출해 구독을 트리거하는 경우가 대표적이다. IAM 방식은 IAM 정책으로 어떤 필드에 접근 가능한지까지 제어할 수 있어서, 백엔드 서비스별로 권한을 좁게 주기 좋다.

주의할 건 프론트엔드에서 IAM 인증을 쓰는 경우다. Cognito Identity Pool로 임시 자격 증명을 받아서 IAM 인증을 하는 구성인데, 이러면 브라우저에서 SigV4 서명을 해야 해서 세팅이 번거롭다. 사용자 인증은 웬만하면 Cognito User Pools로 가는 게 단순하다.

### 혼합 구성

실무에서 흔한 조합은 "사용자용 Cognito + 백엔드용 IAM"이다. 프론트엔드는 로그인 토큰으로, 배치·Lambda는 IAM으로 같은 API를 호출한다. 이때 구독 트리거용 뮤테이션은 IAM으로도 호출 가능해야 하므로, 해당 뮤테이션에 `@aws_iam`과 `@aws_cognito_user_pools`를 둘 다 붙여야 한다. 하나만 붙이면 다른 쪽에서 호출할 때 인증 거부가 난다.

```graphql
type Mutation {
  updateOrderStatus(id: ID!, status: OrderStatus!): Order
    @aws_iam
    @aws_cognito_user_pools
}
```

## 리졸버 매핑 템플릿 디버깅

리졸버가 기대와 다르게 동작할 때 어디를 봐야 하는지 정리한다.

먼저 CloudWatch 로그를 켜야 한다. AppSync API 설정에서 로그 레벨을 `ALL`로 올리면 요청 템플릿 입력, 데이터소스로 나간 실제 요청, 데이터소스 응답, 응답 템플릿 출력이 전부 찍힌다. 리졸버가 이상하면 로그를 `ALL`로 올려 어느 단계에서 값이 틀어지는지부터 확인한다. 다만 `ALL`은 로그량이 많아서 비용이 뛰므로 문제 해결 후엔 `ERROR`로 내려야 한다.

JS 리졸버는 `console.log`를 찍으면 CloudWatch에 나온다. VTL은 `$util.log.info($ctx.args)` 형태로 로그를 남긴다.

콘솔의 쿼리 편집기에서 리졸버 로그를 바로 볼 수도 있다. AppSync 콘솔에서 쿼리를 실행하면 응답과 함께 각 리졸버가 어떤 요청을 만들었는지 보여준다. 로컬에서 재현하기 전에 콘솔에서 먼저 돌려보는 게 빠르다.

실무에서 매핑 템플릿 때문에 자주 겪는 것들:

- `$ctx.args`와 `$ctx.arguments`는 같은 값이다. 둘 다 인자를 가리킨다. 헷갈려서 오타 내면 `null`이 나온다.
- 관계 필드 리졸버에서는 부모 값을 `$ctx.source`로 받는다. `User.orders` 리졸버는 `$ctx.source.id`로 부모 사용자 ID를 꺼낸다. 이걸 `$ctx.args`에서 찾으면 없다.
- DynamoDB 요청에서 타입 변환을 빼먹는 실수. `$ctx.args.id`를 그냥 넣으면 DynamoDB가 타입을 몰라서 에러가 난다. `$util.dynamodb.toDynamoDBJson()`으로 감싸야 한다. JS 리졸버는 `util.dynamodb.toMapValues()`를 쓴다.
- 응답 템플릿에서 에러 처리를 안 하면, 데이터소스 에러가 그냥 삼켜지고 `null`만 반환돼서 원인을 찾기 어렵다. `$ctx.error`(VTL) / `ctx.error`(JS)를 항상 확인해서 `$util.error()`로 올려야 실제 에러 메시지가 클라이언트와 로그에 남는다.

파이프라인 리졸버(여러 함수를 순서대로 실행)를 쓸 때는 함수 사이에 값을 넘기는 `$ctx.stash`를 확인한다. 앞 함수가 `stash`에 넣은 값을 뒤 함수가 못 꺼내면 대개 키 이름이 안 맞는 것이다.

## 스키마 변경 시 하위호환 깨지는 사례

GraphQL 스키마는 클라이언트와의 계약이다. 배포된 프론트엔드가 특정 스키마를 전제로 짜여 있어서, 스키마를 잘못 바꾸면 아직 업데이트 안 된 앱이 깨진다. 모바일 앱은 사용자가 업데이트를 안 하면 옛 스키마로 계속 요청하므로 특히 조심해야 한다.

깨지는 변경(호환 안 됨):

- 필드 삭제. 그 필드를 요청하던 클라이언트가 에러를 받는다.
- 필드 타입 변경. `String`을 `Int`로 바꾸면 파싱이 깨진다.
- nullable 필드(`String`)를 non-null(`String!`)로 바꾸기. 서버가 `null`을 반환하던 자리에 non-null을 강제하면, 값이 없을 때 응답 전체가 에러가 된다. 반대로 non-null을 nullable로 푸는 건 안전하다.
- 필드 이름 변경. 삭제+추가와 같아서 옛 이름을 쓰던 클라이언트가 깨진다.
- enum 값 삭제. 그 값을 반환받던 클라이언트가 처리 못 한다.
- 인자를 non-null로 추가. `getUser(id: ID!)`에 `region: String!`을 새로 추가하면, 이 인자를 안 보내던 기존 클라이언트 요청이 전부 거부된다.

안전한 변경(호환 됨):

- 새 필드 추가. 안 요청하던 클라이언트는 영향 없다.
- 새 타입, 새 쿼리·뮤테이션 추가.
- nullable 인자 추가. `region: String`(non-null 아님)으로 추가하면 안 보내도 된다.
- enum 값 추가는 신중히. 서버가 새 enum 값을 반환하기 시작하면, 그 값을 모르는 옛 클라이언트가 에러를 낼 수 있다. 값 추가 자체는 스키마 호환이지만 런타임에서 깨질 수 있는 회색지대다.

가장 많이 당하는 게 non-null 관련이다. "이 필드는 항상 값이 있으니 `!`를 붙이자"라고 스키마를 조이는 순간, 데이터에 하나라도 `null`이 있으면 그 객체를 포함한 응답 전체가 깨진다. GraphQL은 non-null 필드가 `null`이면 그 필드만 비우는 게 아니라 부모까지 `null`로 전파시킨다. 목록 쿼리에서 항목 하나의 non-null 필드가 `null`이면 목록 전체가 `null`이 되는 식이다. 스키마를 조일 땐 실제 데이터에 `null`이 절대 없는지 먼저 확인해야 한다.

필드를 없애야 할 때는 바로 지우지 말고 `@deprecated`를 붙여서 알린 다음, 모든 클라이언트가 그 필드를 안 쓰는 걸 확인하고 지운다.

```graphql
type User {
  id: ID!
  name: String!
  fullName: String @deprecated(reason: "name으로 대체됨. 2026-09 제거 예정")
}
```

`@deprecated`는 스키마에 표시만 남기고 동작은 그대로라, 클라이언트가 옮겨갈 시간을 벌어준다. 모바일 앱처럼 강제 업데이트가 어려운 클라이언트가 있으면 이 유예 기간을 넉넉히 잡아야 한다.

## 정리

AppSync는 화면 주도 데이터 조합과 실시간 push가 필요한 프론트엔드에 맞는다. 그 조건이 아니면 API Gateway가 단순하다. DynamoDB와 궁합이 가장 좋고, 복잡한 로직은 Lambda로, 관계형은 RDS Data API로 뺀다. 실무에서 발목 잡는 건 대개 세 가지다. 관계 필드에서 터지는 N+1(배치 리졸버로 잡는다), 구독 필터가 뮤테이션 반환 필드에 의존한다는 점, 그리고 non-null로 스키마를 조였다가 `null` 데이터 하나에 응답 전체가 깨지는 하위호환 사고다. 이 셋만 미리 알고 설계하면 나머지는 관리형이 알아서 해준다.
