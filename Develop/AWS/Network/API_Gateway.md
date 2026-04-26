---
title: AWS API Gateway 가이드
tags: [aws, api-gateway, rest-api, http-api, websocket, lambda, throttling, cognito]
updated: 2026-04-26
---

# AWS API Gateway

## 개요

AWS API Gateway는 REST, HTTP, WebSocket API를 만드는 관리형 서비스다. Lambda 백엔드 앞에 두는 진입점으로 가장 많이 쓰이고, EC2/ECS/외부 HTTP 엔드포인트 앞에 둘 수도 있다.

```
Client ──▶ API Gateway ──▶ Lambda / ECS / EC2 / HTTP Endpoint
              │
              ├── 인증 (Cognito, Lambda Authorizer, IAM)
              ├── 스로틀링
              ├── 요청/응답 변환 (VTL)
              ├── 캐싱 (REST API 한정)
              └── API 키 / Usage Plan
```

운영하다 보면 단순히 "Lambda 앞단"이라고 생각했다가 호되게 당하는 부분이 많다. 29초 timeout, 10MB 페이로드, Authorizer 캐싱, 사용량 계획 동작 방식 같은 제약들이 실제 장애로 자주 이어진다. 이 문서는 그 함정 위주로 정리한 것이다.

## REST API vs HTTP API

같은 "REST를 받는 API"이지만 둘은 완전히 다른 제품이다. HTTP API는 2019년에 새로 나온 경량 버전인데, 가격은 70% 정도 싸지만 기능이 빠진 게 많다.

| 항목 | REST API | HTTP API |
|------|----------|----------|
| 비용 | 백만 요청당 $3.50 | 백만 요청당 $1.00 |
| 캐싱 | 지원 | 지원 안 함 |
| API 키 / Usage Plan | 지원 | 지원 안 함 |
| WAF 연동 | 직접 연동 가능 | CloudFront 통해서만 |
| 요청/응답 변환 (VTL) | 지원 | 지원 안 함 |
| Private 엔드포인트 | 지원 | 지원 안 함 |
| Authorizer | Cognito, Lambda(Token/Request), IAM | JWT, Lambda |
| 통합 latency overhead | 약 50~100ms | 약 10~30ms |

### REST → HTTP API 마이그레이션 주의점

저렴하다는 이유로 HTTP API로 옮기려다 막히는 경우가 가장 많은 게 두 가지다.

첫째, **Usage Plan이 없다**. API 키별로 일/월 한도를 걸어서 파트너사에 차등 과금하던 구조라면 HTTP API로 옮길 수 없다. 굳이 옮기려면 인증 토큰을 발급할 때 자체적으로 quota를 카운트하는 Redis 같은 게 따로 필요하다.

둘째, **응답 캐싱이 없다**. REST API에서 GET 응답을 5분 캐시로 돌리고 있었다면, HTTP API로 옮기는 순간 모든 요청이 Lambda를 호출한다. Lambda invocation 비용 + 실행 시간 비용이 폭증한다. 앞단에 CloudFront를 따로 붙이거나, 애플리케이션 레벨 캐시(ElastiCache)를 추가해야 한다.

세 번째 함정은 **VTL Mapping Template 부재**다. REST API에서 Lambda Proxy 통합이 아니라 일반 통합으로 요청 변환을 쓰고 있었다면, HTTP API에선 통째로 다시 짜야 한다. 보통 Lambda 안에서 변환하는 식으로 옮긴다.

결론적으로 신규로 만든다면 HTTP API를 우선 검토하지만, 기존 REST API 마이그레이션은 위 세 가지 항목 사용 여부부터 봐야 한다.

## Lambda 통합과 29초 timeout

API Gateway → Lambda 통합에는 **하드 리밋 29초**가 걸려 있다. Lambda 자체는 15분까지 돌 수 있어도 API Gateway가 29초에 끊는다. 이걸 모르고 있다가 운영 중에 504 Gateway Timeout이 우후죽순 떠서 알게 되는 경우가 많다.

29초 안에 못 끝나는 작업을 처리하는 방법이 몇 가지 있다.

### 비동기 Lambda 호출

응답을 즉시 받고 작업은 백그라운드에서 돌린다. 클라이언트에 jobId를 돌려주고 따로 폴링하게 만든다.

```javascript
// API Gateway → Lambda (Sync) → Lambda (Async invoke)
const AWS = require('aws-sdk');
const lambda = new AWS.Lambda();

exports.handler = async (event) => {
    const jobId = crypto.randomUUID();

    // 응답은 즉시 반환, 실제 작업은 다른 Lambda에서 비동기로
    await lambda.invoke({
        FunctionName: 'long-running-worker',
        InvocationType: 'Event',  // 비동기
        Payload: JSON.stringify({ jobId, ...event.body })
    }).promise();

    return {
        statusCode: 202,
        body: JSON.stringify({ jobId, status: 'processing' })
    };
};
```

### Step Functions 분기

워크플로우가 여러 단계로 나뉘는 경우 Step Functions로 옮기는 게 깔끔하다. API Gateway → Step Functions StartExecution을 호출하고 executionArn을 응답하는 식이다.

### Server-Sent Events (SSE)는 안 된다

SSE를 쓰려면 응답 스트리밍이 필요한데, REST API는 스트리밍 응답을 지원하지 않는다. 응답 전체가 만들어진 뒤에야 클라이언트로 간다. 진짜 SSE가 필요하면 ALB + ECS/Lambda Function URL(스트리밍 지원)로 가야 한다.

WebSocket API는 별도 제품이라 양방향 실시간이 필요하면 그쪽을 써야 한다.

## 페이로드 / 헤더 제한

| 항목 | 한도 |
|------|------|
| 요청/응답 페이로드 | 10MB |
| 헤더 전체 크기 | 10KB |
| 헤더 값 길이 | 8KB |
| URL 길이 | 8192 bytes |
| Lambda Proxy 통합 응답 | 6MB (Lambda 자체 한도) |
| Integration timeout | 29초 |

Lambda Proxy 통합에서는 사실상 **6MB**가 응답 한도다. 큰 파일은 무조건 S3 presigned URL로 우회한다. base64 인코딩하면 33% 더 커지니까 4.5MB짜리 파일도 못 보낸다는 얘기다.

쿠키가 많이 쌓인 클라이언트에서 헤더 10KB를 넘어 413 Request Entity Too Large가 떨어지는 케이스도 있다. JWT 토큰 + 여러 쿠키가 쌓이면 의외로 잘 터진다.

## Stage Variables로 환경별 분기

Stage Variables는 Stage(dev/staging/prod) 단위로 다른 값을 주입하는 기능이다. 가장 흔한 용도가 **Lambda alias 분기**다.

```yaml
# CloudFormation
DevStage:
  Type: AWS::ApiGateway::Stage
  Properties:
    StageName: dev
    Variables:
      lambdaAlias: dev
      backendUrl: https://dev-api.internal

ProdStage:
  Type: AWS::ApiGateway::Stage
  Properties:
    StageName: prod
    Variables:
      lambdaAlias: prod
      backendUrl: https://api.internal
```

```yaml
# Method 통합에서 Stage Variable 참조
Integration:
  Type: AWS_PROXY
  Uri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${MyFunction.Arn}:${!stageVariables.lambdaAlias}/invocations
```

이러면 Lambda 함수 하나만 만들고 alias만 dev/prod로 분기해서 동일한 API Gateway 정의로 환경별 라우팅이 된다. 트래픽 시프팅(canary deploy)이 필요할 때도 alias 가중치를 바꾸는 식으로 쓰면 된다.

주의: Stage Variable로 통합 URI를 동적으로 바꾸려면 해당 Lambda alias에 **InvokePermission을 명시적으로 주어야 한다**. 안 그러면 500 에러가 떨어지는데 CloudWatch 로그에는 "permission denied"라는 단서밖에 없어서 디버깅이 골치 아프다.

## Custom Domain + Base Path Mapping

여러 API를 한 도메인 아래 매핑하는 방식이다. `api.example.com/users`는 user-api로, `api.example.com/orders`는 order-api로 각각 다른 API Gateway에 매핑한다.

```yaml
CustomDomain:
  Type: AWS::ApiGateway::DomainName
  Properties:
    DomainName: api.example.com
    CertificateArn: !Ref AcmCertificate
    EndpointConfiguration:
      Types:
        - REGIONAL

UsersMapping:
  Type: AWS::ApiGateway::BasePathMapping
  Properties:
    DomainName: !Ref CustomDomain
    BasePath: users
    RestApiId: !Ref UsersApi
    Stage: prod

OrdersMapping:
  Type: AWS::ApiGateway::BasePathMapping
  Properties:
    DomainName: !Ref CustomDomain
    BasePath: orders
    RestApiId: !Ref OrdersApi
    Stage: prod
```

마이크로서비스 환경에서 도메인 하나에 API를 모으는 데 자주 쓴다. 단점은 base path가 백엔드 Lambda에서 그대로 들어와서, Lambda 코드에서 `/users`를 stripping해야 하는 케이스가 생긴다는 점이다. SAM의 `OpenApiVersion: '3.0.1'`을 쓰거나 Mapping Template으로 path를 다시 쓸 수도 있다.

## Edge-optimized vs Regional vs Private

REST API에서 엔드포인트 타입을 세 가지 중에 골라야 한다.

| 타입 | 동작 | 적합한 경우 |
|------|------|-----------|
| Edge-optimized | CloudFront 자동 프록시 | 글로벌 API, 단일 리전 사용 |
| Regional | 리전 내 직접 노출 | CloudFront 직접 관리, 멀티리전 |
| Private | VPC 내부 endpoint만 | 내부 서비스 간 통신 |

가장 많은 실수가 **Edge-optimized 앞에 또 CloudFront를 붙이는 것**이다. API Gateway가 이미 CloudFront 위에 있는데 추가로 CloudFront 배포를 만들면 캐싱 정책이 두 단계 충돌해서 디버깅이 매우 어려워진다. 캐시 무효화도 두 곳에 다 해줘야 한다. 이 경우는 **Regional**을 쓰고 본인 CloudFront 배포를 직접 관리하는 게 맞다.

엔드포인트 타입은 **변경이 안 되는 항목**이다. 만들 때 신중히 정해야 하고, 바꾸려면 새 API를 만들고 도메인을 옮기는 식으로 가야 한다.

Private 엔드포인트는 VPC Endpoint(인터페이스 타입)를 통해서만 접근 가능하다. 외부에서 호출하면 403이 떨어진다. 사내 API에 자주 쓴다.

## Mapping Template (VTL) - 비-프록시 통합

Lambda Proxy 통합이 아니라 일반 통합을 쓸 때, 요청/응답을 VTL(Velocity Template Language)로 변환할 수 있다. 외부 SOAP 서비스를 REST로 노출하거나, DynamoDB를 직접 호출하는 통합에서 자주 쓴다.

DynamoDB GetItem을 직접 호출하는 예시:

```velocity
## 요청 변환 (Mapping Template)
{
    "TableName": "Users",
    "Key": {
        "userId": {
            "S": "$input.params('id')"
        }
    }
}
```

```velocity
## 응답 변환
#set($item = $input.path('$.Item'))
{
    "userId": "$item.userId.S",
    "email": "$item.email.S",
    "createdAt": "$item.createdAt.S"
}
```

Lambda 없이 DynamoDB를 직접 노출할 수 있어서 단순 CRUD에서는 비용이 덜 든다. 단점은 VTL 디버깅이 매우 까다롭다는 점. 문법 에러는 500으로만 떨어지고, 로그에 단서가 거의 없다. 복잡한 변환은 그냥 Lambda 안에 넣는 게 정신건강에 좋다.

## 5xx 에러 디버깅

API Gateway에서 5xx가 떨어지면 원인이 어디인지부터 좁혀야 한다.

| 코드 | 의미 | 보통 원인 |
|------|------|----------|
| 500 | Internal Server Error | Mapping Template 에러, 통합 응답 매칭 실패 |
| 502 | Bad Gateway | Lambda 응답 형식 오류, 백엔드 응답 파싱 실패 |
| 503 | Service Unavailable | 백엔드 가용 불가 |
| 504 | Gateway Timeout | 29초 timeout 초과 |

디버깅 흐름:

1. **CloudWatch Logs (Execution Logging) 활성화**: Stage 설정에서 INFO 레벨 켜면 매 요청마다 통합 단계별 로그가 남는다. 운영에서는 비용 때문에 ERROR 레벨로 놓고 문제 생길 때만 INFO로 올린다.

2. **X-Ray 활성화**: API Gateway → Lambda → 다른 AWS 서비스 호출 흐름이 한 번에 보인다. 어느 단계에서 시간이 오래 걸리는지, 어디서 에러가 났는지 시각적으로 확인 가능하다.

3. **CloudWatch 메트릭**: `IntegrationLatency` vs `Latency` 차이를 본다. `Latency`는 API Gateway 전체, `IntegrationLatency`는 백엔드(Lambda 등) 응답 시간이다. 이 둘이 비슷하면 백엔드가 느린 거고, `Latency`만 크면 API Gateway 자체에서 시간이 걸린 것(Authorizer, Mapping Template 등).

4. **Lambda CloudWatch Logs**: 502가 떨어지는데 Lambda 로그에는 정상 종료로 찍혀 있다면 응답 형식이 잘못된 것이다. Lambda Proxy 통합은 `{ statusCode, headers, body }` 형식을 정확히 맞춰야 한다. body는 반드시 문자열이어야 하고, JSON 객체를 그대로 리턴하면 502가 떨어진다.

```javascript
// 잘못된 예 - 502 떨어짐
return { statusCode: 200, body: { ok: true } };

// 올바른 예
return { statusCode: 200, body: JSON.stringify({ ok: true }) };
```

## Throttling 429 발생

429 Too Many Requests가 떨어지는 이유는 여러 레이어에서 한도가 걸려 있기 때문이다.

```
요청 → [계정 한도] → [API/Stage 한도] → [Method 한도] → [Usage Plan 한도] → 백엔드
        10000 RPS    설정값            설정값           API 키별
```

가장 헷갈리는 사례가 **Usage Plan을 거치지 않는 요청은 Account/Stage 레벨 한도만 적용된다**는 점이다. API 키 없는 요청에 Usage Plan rate limit이 걸린다고 착각하는 경우가 많다.

또 한 가지 함정은 **Stage 레벨 throttle은 burst까지 모두 그 값을 따른다**는 점이다. Method 레벨에서 더 낮은 값을 설정해도 Stage가 우선되는 게 아니라 둘 중 더 낮은 게 적용된다. 우선순위는 Method > Stage > Account.

운영 중에 429가 떨어지면 우선 어느 레이어에서 걸린 건지 확인해야 한다. CloudWatch 메트릭의 `4XXError`가 갑자기 튀고 `Count`(요청 수)는 그대로면 throttling이 의심된다. `ThrottleCount` 메트릭을 켜면 정확하게 보인다.

계정 한도 10,000 RPS는 AWS Support에 요청해서 올릴 수 있다. 다만 즉시 올라가는 게 아니라 검토 후 며칠 걸린다. 트래픽 폭증 이벤트(블랙프라이데이 등)가 예정되어 있으면 미리 한도 증설을 신청해야 한다.

## WAF 연동

REST API는 AWS WAF v2를 직접 연동할 수 있다. (HTTP API는 직접 연동 불가, 앞에 CloudFront를 두고 거기에 WAF를 붙여야 한다.)

자주 쓰는 두 가지 룰:

```
IP Set 기반 차단:
  악성 IP 목록을 IP Set에 등록 → WebACL 룰로 Block

Rate-based rule:
  IP당 5분에 2000 요청 초과 시 Block
  봇/크롤러/DoS 차단에 효과적
```

```yaml
RateBasedRule:
  Type: AWS::WAFv2::WebACL
  Properties:
    Scope: REGIONAL
    Rules:
      - Name: RateLimit
        Priority: 1
        Statement:
          RateBasedStatement:
            Limit: 2000
            AggregateKeyType: IP
        Action:
          Block: {}
        VisibilityConfig:
          SampledRequestsEnabled: true
          CloudWatchMetricsEnabled: true
          MetricName: RateLimit
```

운영 중 IP 차단을 자주 한다면 IP Set을 따로 만들어두고 람다로 자동 추가하는 식으로 해두는 게 편하다. 직접 콘솔 들어가서 추가하는 건 새벽 호출 받으면 정신없다.

## API 키 노출 사고 대응

API 키가 GitHub에 푸시되거나 클라이언트 앱에 박혀서 노출되는 사고가 의외로 많다. 대응 절차는 정해놓는 게 좋다.

1. **즉시 해당 키를 비활성화**: API 키 자체를 삭제하지 말고 우선 disable. 삭제하면 Usage Plan 연결도 끊겨서 복구가 번거롭다.
2. **새 키 발급 후 정상 클라이언트에 배포**: 키를 secrets manager 같은 곳에 두고 환경변수로 주입하던 방식이라면 빠르게 교체 가능하다. 하드코딩되어 있으면 앱 재배포가 필요하다.
3. **CloudWatch Logs에서 비정상 사용 패턴 분석**: 어디서 얼마나 호출했는지 확인.
4. **Usage Plan을 분리**: 한 Usage Plan에 여러 키를 묶어두면 한 키만 노출돼도 같은 Plan을 쓰는 모든 키가 영향을 받는다(throttle 한도가 공유되지 않지만 quota 정책 변경이 일괄됨). 등급별로 분리해야 사고 시 격리가 된다.

키 로테이션을 정기적으로 하려면 Lambda + EventBridge로 자동화하는 게 일반적이다. 로테이션 후 일정 기간(보통 24시간) 양쪽 키를 다 살려두고 메트릭을 확인한 뒤 옛 키를 비활성화한다.

## Cognito Authorizer 캐싱

Cognito Authorizer는 기본적으로 **TTL 5분**으로 결과를 캐싱한다. 토큰을 한 번 검증하면 5분간 같은 토큰은 검증을 건너뛴다.

여기서 잘 모르고 당하는 게 **권한 갱신 지연**이다. Cognito User Pool에서 사용자 그룹을 변경했는데 새 권한이 즉시 반영되지 않는다. 정확히는, 토큰 자체에 그룹 정보가 들어있으니까 새 토큰을 발급받아야 하는 것이고, 거기다 API Gateway가 5분간 옛날 토큰의 검증 결과(claims)를 캐시한다.

해결 방법:

- **TTL을 0으로 설정**: 매 요청마다 검증. Cognito 호출 비용이 늘고 latency가 추가된다.
- **권한 변경 시 토큰 재발급 강제**: 클라이언트가 다시 로그인하게 만들거나, refresh token으로 새 토큰을 받게 한다.
- **권한 정보를 토큰에 넣지 않고 백엔드에서 매번 조회**: 토큰엔 userId만 두고 Lambda 안에서 DB로 권한 확인. 일관성이 좋지만 매 요청마다 DB 조회가 추가된다.

## Lambda Authorizer 캐싱 키 실수

Lambda Authorizer도 TTL 캐싱이 있는데, **캐시 키 설정을 잘못 잡으면 큰 사고**가 난다.

기본 설정은 `IdentitySource`(보통 Authorization 헤더)를 캐시 키로 쓴다. 이러면 토큰별로 캐싱되니까 정상이다.

문제는 일부 팀이 캐시 키에서 토큰을 빼고 IP 같은 걸로 바꾸거나, Token Authorizer 대신 Request Authorizer로 바꾸면서 캐시 키를 잘못 설정하는 경우다. 한 번은 **모든 사용자가 같은 권한을 받는 사고**가 실제로 있었다. 캐시 키가 빈 값이었거나 모든 요청에 공통인 헤더로 잡혀 있었던 것.

```yaml
# 올바른 예 - 토큰 자체를 캐시 키로
LambdaAuthorizer:
  Type: AWS::ApiGateway::Authorizer
  Properties:
    Type: TOKEN
    IdentitySource: method.request.header.Authorization
    AuthorizerResultTtlInSeconds: 300
```

Request Authorizer를 쓸 때는 `IdentitySource`를 여러 개 잡을 수 있는데, 모두 합쳐서 캐시 키가 된다. 사용자를 구분하는 값이 반드시 포함되어야 한다.

문제 의심되면 일시적으로 `AuthorizerResultTtlInSeconds: 0`으로 두고 매 요청 검증하게 만들어 격리한다.

## OPTIONS Preflight CORS 디버깅

브라우저에서 cross-origin 요청 시 OPTIONS 메서드로 preflight가 먼저 간다. API Gateway가 OPTIONS를 처리하지 않으면 본 요청 자체가 안 가고 CORS 에러가 난다.

가장 흔한 사고:

- **Lambda Proxy 통합인데 OPTIONS 메서드를 만들지 않음**: 일반 GET/POST만 만들고 OPTIONS는 빠뜨린다. 브라우저 콘솔엔 "CORS policy" 에러만 나오고 실제로는 OPTIONS가 403/404로 떨어지는 상황.
- **OPTIONS는 정의했지만 응답 헤더에 Access-Control-Allow-* 가 없음**: Mock 통합으로 응답을 만들 때 헤더 매핑을 빠뜨리면 헤더 자체가 안 간다.
- **AllowOrigin에 와일드카드 + 자격증명**: `Access-Control-Allow-Origin: *`와 `Access-Control-Allow-Credentials: true`는 동시에 못 쓴다. 와일드카드 대신 정확한 도메인을 명시해야 한다.

SAM에서 가장 깔끔한 방법:

```yaml
MyApi:
  Type: AWS::Serverless::Api
  Properties:
    StageName: prod
    Cors:
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowOrigin: "'https://app.example.com'"
      AllowCredentials: true
```

이러면 SAM이 자동으로 OPTIONS 메서드를 모든 리소스에 추가하고 헤더도 넣어준다.

Lambda Proxy 통합에서 응답 헤더로 직접 CORS를 처리할 수도 있다. 이 경우 모든 응답에 `Access-Control-Allow-*`를 일관되게 붙여야 한다.

```javascript
const corsHeaders = {
    'Access-Control-Allow-Origin': 'https://app.example.com',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization'
};

exports.handler = async (event) => {
    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers: corsHeaders, body: '' };
    }
    // ...
    return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify(result)
    };
};
```

## 비용 폭탄 사례

API Gateway 자체는 비싸지 않지만 운영 패턴에 따라 청구서가 갑자기 튀는 경우가 있다.

### 사례 1: 캐시 미사용 + 고빈도 GET

상품 목록 같은 거의 안 변하는 데이터를 매 요청마다 Lambda → RDS 조회로 응답하는 구조. 클라이언트가 SPA에서 스크롤할 때마다 호출하는 식이면 한 사용자가 분당 수십~수백 번 부른다.

비용 산정:

```
월 1억 요청 (REST API)
- API Gateway: $350
- Lambda invocation: $20
- Lambda 실행 (200ms × 128MB): $267
- RDS 부하 비용 (인스턴스 한 단계 업): $200
합계: 월 $837

캐싱 (5분 TTL, 0.5GB) 적용 시
- API Gateway: $350
- 캐시 비용: $14/일 × 30 = $420
- Lambda invocation: $0.5 (95% hit 가정)
- Lambda 실행: $7
- RDS 부하 감소: 인스턴스 다운그레이드 가능
합계: 월 $777, 게다가 latency 향상
```

캐시가 작동만 하면 비용이 비슷해도 사용자 경험이 좋고 백엔드 부하가 줄어 인프라 다운사이징 여지가 생긴다.

캐시를 안 쓰는 게 더 싸지는 경우도 있다. 트래픽이 낮은데 5분 TTL을 걸어두면 캐시 비용($14/일)이 Lambda 비용보다 많아진다. 일 100만 미만 요청에는 보통 ElastiCache나 CloudFront 쪽이 더 합리적이다.

### 사례 2: Mobile 앱이 인증 실패 시 무한 재시도

Mobile 앱에서 토큰 만료 처리를 잘못 짜서 401 받으면 즉시 재시도하는 버그. 한 사용자가 초당 수십 번 호출. WAF rate-based rule도 1000 RPS 단위로 걸려 있어서 막지 못한 사례. API Gateway는 인증 실패 요청도 과금된다.

대응:
- 짧은 주기 rate-based rule 추가 (1분 100요청 등)
- 클라이언트 라이브러리 강제 업데이트
- 인증 실패 시 백오프 로직 명시화

### 사례 3: WebSocket 연결을 안 끊음

WebSocket API는 **연결 시간 + 메시지 수**로 과금된다. 클라이언트가 disconnect를 안 보내고 백그라운드로 갔다가 다시 안 켜는 모바일 환경에선 idle 연결이 누적된다. API Gateway WebSocket의 idle timeout은 10분이지만, 연결당 비용이 크진 않아도 동시 연결 수가 만 단위면 청구서에 보인다. 서버 쪽에서 ping/pong을 하고 응답 없으면 명시적으로 끊어야 한다.

## API Gateway vs ALB

| 항목 | API Gateway | ALB |
|------|-------------|-----|
| 과금 | 요청 수 + 데이터 | 시간 + LCU |
| 저트래픽 | 저렴 | 비쌈 (고정비 약 $20/월) |
| 고트래픽 | 비쌈 | 저렴 (월 1억 요청 이상) |
| 인증 | Cognito, Lambda Auth, IAM | OIDC (Cognito) |
| 캐싱 | 내장 (REST API) | 없음 |
| WebSocket | 지원 (별도 API 타입) | 미지원 |
| 응답 스트리밍 | 미지원 | 지원 |
| API 키/Usage Plan | 지원 (REST API) | 미지원 |
| 백엔드 적합도 | Lambda | ECS/EC2 |

월 1억 요청을 넘어가면 ALB 쪽이 통상 더 싸다. 다만 Lambda를 ALB에 직접 붙이면 Lambda Proxy 통합과 동작이 약간 달라서(Multi-Value 헤더 처리 등) 주의가 필요하다.

## 참고

- [AWS API Gateway 공식 문서](https://docs.aws.amazon.com/apigateway/)
- [Cognito](../Security/Cognito.md)
- [Lambda](../Compute/Lambda.md)
- [ALB vs API Gateway](../Load_Balancer/ALB vs API Gateway.md)
