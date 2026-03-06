---
title: AWS API Gateway 가이드
tags: [aws, api-gateway, rest-api, http-api, websocket, lambda, throttling, cognito]
updated: 2026-03-01
---

# AWS API Gateway

## 개요

AWS API Gateway는 REST, HTTP, WebSocket API를 생성하고 관리하는 **완전 관리형 서비스**이다. 서버리스 아키텍처의 핵심 진입점으로, Lambda, ECS, EC2 등 백엔드 서비스 앞에 위치한다.

```
Client ──▶ API Gateway ──▶ Lambda / ECS / EC2 / HTTP Endpoint
              │
              ├── 인증 (Cognito, Lambda Authorizer)
              ├── 스로틀링 & 레이트 리미팅
              ├── 요청/응답 변환
              ├── 캐싱
              └── API 키 관리
```

### API 유형 비교

| 항목 | REST API | HTTP API | WebSocket API |
|------|---------|---------|--------------|
| **프로토콜** | REST | REST | WebSocket |
| **비용** | 높음 | **낮음 (70% 저렴)** | 연결 + 메시지 기반 |
| **기능** | 풀 스펙 | 경량 | 양방향 실시간 |
| **캐싱** | ✅ | ❌ | ❌ |
| **WAF 통합** | ✅ | ❌ | ❌ |
| **API 키** | ✅ | ❌ | ❌ |
| **사용량 계획** | ✅ | ❌ | ❌ |
| **Lambda 통합** | ✅ | ✅ | ✅ |
| **VPC Link** | ✅ | ✅ | ❌ |
| **적합한 경우** | 엔터프라이즈 API | 단순 API, MSA 프록시 | 채팅, 실시간 알림 |

## 핵심

### 1. REST API 구성

```
REST API 구조:
  /api
    /users
      GET    → Lambda: listUsers
      POST   → Lambda: createUser
      /{id}
        GET    → Lambda: getUser
        PUT    → Lambda: updateUser
        DELETE → Lambda: deleteUser
    /orders
      GET    → Lambda: listOrders
      POST   → Lambda: createOrder
```

#### CloudFormation으로 API 생성

```yaml
Resources:
  MyApi:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: MyService-API
      Description: My Service REST API

  UsersResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref MyApi
      ParentId: !GetAtt MyApi.RootResourceId
      PathPart: users

  GetUsersMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref MyApi
      ResourceId: !Ref UsersResource
      HttpMethod: GET
      AuthorizationType: COGNITO_USER_POOLS
      AuthorizerId: !Ref CognitoAuthorizer
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${ListUsersFunction.Arn}/invocations
```

#### SAM (Serverless Application Model)

```yaml
# template.yaml (SAM으로 간결하게)
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  MyApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn

  ListUsersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: users.list
      Runtime: nodejs20.x
      Events:
        GetUsers:
          Type: Api
          Properties:
            RestApiId: !Ref MyApi
            Path: /users
            Method: GET

  CreateUserFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: users.create
      Runtime: nodejs20.x
      Events:
        PostUsers:
          Type: Api
          Properties:
            RestApiId: !Ref MyApi
            Path: /users
            Method: POST
```

### 2. 인증/인가

#### Cognito Authorizer

```yaml
# Cognito User Pool을 Authorizer로 설정
CognitoAuthorizer:
  Type: AWS::ApiGateway::Authorizer
  Properties:
    Name: CognitoAuth
    Type: COGNITO_USER_POOLS
    RestApiId: !Ref MyApi
    ProviderARNs:
      - !GetAtt UserPool.Arn
    IdentitySource: method.request.header.Authorization
```

#### Lambda Authorizer (커스텀 인증)

JWT를 직접 검증하거나, API 키, 커스텀 토큰 등을 처리한다.

```javascript
// Lambda Authorizer (토큰 기반)
exports.handler = async (event) => {
    const token = event.authorizationToken;

    try {
        const decoded = jwt.verify(token.replace('Bearer ', ''), SECRET);

        return {
            principalId: decoded.sub,
            policyDocument: {
                Version: '2012-10-17',
                Statement: [{
                    Action: 'execute-api:Invoke',
                    Effect: 'Allow',
                    Resource: event.methodArn
                }]
            },
            context: {
                userId: decoded.sub,
                email: decoded.email
            }
        };
    } catch (err) {
        throw new Error('Unauthorized');
    }
};
```

| 인증 방식 | 용도 |
|----------|------|
| **Cognito Authorizer** | AWS Cognito 기반 JWT 검증 |
| **Lambda Authorizer (Token)** | 커스텀 JWT, API 키 검증 |
| **Lambda Authorizer (Request)** | 헤더, 쿼리 파라미터 기반 인증 |
| **IAM Authorizer** | AWS SigV4 서명 기반 (서비스 간 통신) |
| **API Key** | 간단한 키 기반 접근 제어 (인증보다는 식별용) |

### 3. 스로틀링 & 사용량 계획

```
기본 제한:
  - 계정 레벨: 10,000 RPS (요청/초)
  - 버스트: 5,000 동시 요청

사용량 계획 (Usage Plan):
  - API 키별로 일/월 요청 한도 설정
  - 초당 요청 수 제한 (Rate Limiting)
  - 파트너별 다른 등급 적용
```

```yaml
UsagePlan:
  Type: AWS::ApiGateway::UsagePlan
  Properties:
    UsagePlanName: BasicPlan
    Throttle:
      RateLimit: 100          # 초당 100 요청
      BurstLimit: 200         # 순간 최대 200
    Quota:
      Limit: 10000            # 월 10,000 요청
      Period: MONTH
    ApiStages:
      - ApiId: !Ref MyApi
        Stage: prod
```

### 4. 요청/응답 변환

API Gateway에서 요청/응답을 **변환**할 수 있다.

```
Client 요청                 Lambda가 받는 요청
{                           {
  "userName": "홍길동"        "body": "{...}",
}                            "pathParameters": { "id": "1" },
                             "queryStringParameters": { "page": "1" },
                             "headers": { "Authorization": "Bearer ..." },
                             "requestContext": {
                               "authorizer": {
                                 "claims": { "sub": "user-123" }
                               }
                             }
                           }
```

```javascript
// Lambda 통합 응답 형식
exports.handler = async (event) => {
    const userId = event.pathParameters.id;
    const user = await getUser(userId);

    return {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        body: JSON.stringify(user)
    };
};
```

### 5. 캐싱 (REST API만)

```yaml
# 스테이지에서 캐싱 활성화
Stage:
  Type: AWS::ApiGateway::Stage
  Properties:
    CacheClusterEnabled: true
    CacheClusterSize: '0.5'       # GB 단위
    MethodSettings:
      - HttpMethod: GET
        ResourcePath: /users
        CachingEnabled: true
        CacheTtlInSeconds: 300    # 5분
```

```
캐싱 동작:
  1차 요청: Client → API Gateway → Lambda → 응답 (캐시 저장)
  2차 요청: Client → API Gateway → 캐시 응답 (Lambda 호출 안 함)

캐시 무효화:
  Header: Cache-Control: max-age=0
```

### 6. CORS 설정

```yaml
# SAM에서 CORS 설정
MyApi:
  Type: AWS::Serverless::Api
  Properties:
    Cors:
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowOrigin: "'https://example.com'"
```

### 7. VPC Link (프라이빗 통합)

프라이빗 서브넷의 ALB/NLB에 API Gateway에서 접근한다.

```
Client → API Gateway → VPC Link → NLB → ECS (Private Subnet)
```

### 8. API Gateway vs ALB

| 항목 | API Gateway | ALB |
|------|-----------|-----|
| **과금** | 요청 수 기반 | 시간 + LCU 기반 |
| **저트래픽** | 저렴 | 비쌈 (고정 비용) |
| **고트래픽** | 비쌈 | 저렴 |
| **인증** | Cognito, Lambda Auth | OIDC (Cognito) |
| **캐싱** | 내장 | 없음 |
| **WebSocket** | 지원 | 미지원 |
| **API 키/사용량** | 지원 | 미지원 |
| **서버리스** | Lambda 네이티브 | ECS/EC2 연동 |

```
선택 기준:
  서버리스 (Lambda) → API Gateway
  컨테이너 (ECS/EKS) → ALB
  월 1억 요청 이상 → ALB가 비용 유리
  API 키/사용량 관리 필요 → API Gateway
```

## 운영 팁

### 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| 인증 설정 | Cognito 또는 Lambda Authorizer | ✅ |
| 스로틀링 | 계정/API별 요청 제한 | ✅ |
| CORS | 프론트엔드 도메인 허용 | ✅ |
| 스테이지 분리 | dev/staging/prod | ✅ |
| 로깅 | CloudWatch 로그 활성화 | ✅ |
| 캐싱 | GET 요청에 캐싱 적용 | ⭐ |
| WAF 연동 | SQL Injection, XSS 방지 | ⭐ |

## 참고

- [AWS API Gateway 공식 문서](https://docs.aws.amazon.com/apigateway/)
- [Cognito](../Security/Cognito.md) — 인증 서비스 연동
- [Lambda](../Compute/Lambda.md) — 서버리스 함수
- [ALB vs API Gateway](../Load_Balancer/ALB vs API Gateway.md) — 비교
- [API Gateway 패턴](../../Network/GateWay/API_Gateway.md) — 일반 API Gateway 아키텍처
