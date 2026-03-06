---
title: AWS Cognito 인증 서비스 가이드
tags: [aws, security, cognito, authentication, user-pool, identity-pool, jwt, oauth2]
updated: 2026-03-01
---

# AWS Cognito

## 개요

AWS Cognito는 웹/모바일 앱에 **인증, 인가, 사용자 관리**를 제공하는 완전 관리형 서비스이다. 직접 인증 시스템을 구축하지 않아도 회원가입, 로그인, 소셜 로그인, MFA 등을 빠르게 구현할 수 있다.

### 핵심 구성 요소

| 구성 요소 | 역할 | 비유 |
|----------|------|------|
| **User Pool** | 사용자 디렉토리 + 인증 | "누구인가?" (Authentication) |
| **Identity Pool** | AWS 자격증명 발급 | "뭘 할 수 있는가?" (Authorization) |

```
                    ┌─────────────────┐
  사용자 ──로그인──▶ │   User Pool     │ ──JWT 토큰──▶ API Gateway / ALB
                    │  (인증 + 사용자) │
                    └────────┬────────┘
                             │ 토큰
                    ┌────────▼────────┐
                    │  Identity Pool  │ ──AWS 자격증명──▶ S3, DynamoDB 등
                    │ (AWS 리소스 접근)│
                    └─────────────────┘
```

## 핵심

### 1. User Pool (사용자 풀)

사용자 등록/로그인을 관리하는 **사용자 디렉토리**이다.

#### 제공 기능

| 기능 | 설명 |
|------|------|
| **회원가입/로그인** | 이메일, 전화번호, 사용자명 |
| **소셜 로그인** | Google, Facebook, Apple, Amazon |
| **SAML/OIDC** | 기업 IdP (Azure AD, Okta) 연동 |
| **MFA** | SMS, TOTP (Google Authenticator) |
| **비밀번호 정책** | 최소 길이, 대소문자, 특수문자 |
| **이메일/SMS 인증** | 가입 시 확인 코드 전송 |
| **JWT 토큰 발급** | ID Token, Access Token, Refresh Token |
| **커스텀 속성** | 사용자 프로필에 커스텀 필드 추가 |

#### 토큰 구조

```
로그인 성공 시 3가지 토큰 발급:

ID Token (인증 정보)
  - 사용자 정보 (이메일, 이름 등)
  - 용도: 프론트엔드에서 사용자 정보 표시
  - 만료: 1시간

Access Token (인가 정보)
  - 권한 스코프
  - 용도: API 호출 시 Authorization 헤더
  - 만료: 1시간

Refresh Token (갱신)
  - Access/ID Token 갱신용
  - 만료: 30일 (설정 가능)
```

#### Hosted UI (내장 로그인 페이지)

Cognito가 제공하는 **로그인/회원가입 UI**. 커스터마이징 없이 빠르게 적용 가능.

```
https://<your-domain>.auth.<region>.amazoncognito.com/login
  ?client_id=<app-client-id>
  &response_type=code
  &scope=openid+email+profile
  &redirect_uri=https://your-app.com/callback
```

### 2. Identity Pool (자격증명 풀)

인증된 사용자에게 **AWS 리소스에 접근할 수 있는 임시 자격증명**(STS)을 발급한다.

```
사용 시나리오:
  - 프론트엔드에서 직접 S3에 파일 업로드
  - 모바일 앱에서 DynamoDB 직접 읽기/쓰기
  - IoT 디바이스에서 AWS 서비스 접근

인증 흐름:
  1. User Pool에서 로그인 → JWT 토큰 수신
  2. JWT 토큰을 Identity Pool에 전달
  3. Identity Pool이 IAM Role 매핑
  4. STS 임시 자격증명 발급
  5. 자격증명으로 AWS 서비스 직접 접근
```

### 3. API Gateway 연동

```
Client → API Gateway (Cognito Authorizer) → Lambda / Backend
            │
            └── JWT 토큰 검증 (User Pool)
```

```yaml
# SAM/CloudFormation
Resources:
  MyApi:
    Type: AWS::Serverless::Api
    Properties:
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn
```

### 4. Lambda 트리거

사용자 인증 흐름의 각 단계에 **Lambda 함수를 삽입**하여 커스텀 로직을 실행한다.

| 트리거 | 시점 | 용도 |
|--------|------|------|
| **Pre Sign-up** | 회원가입 전 | 특정 도메인 이메일만 허용 |
| **Post Confirmation** | 이메일 인증 후 | DB에 사용자 레코드 생성 |
| **Pre Authentication** | 로그인 전 | IP 화이트리스트 검사 |
| **Post Authentication** | 로그인 후 | 로그인 이력 기록 |
| **Pre Token Generation** | 토큰 생성 전 | 커스텀 클레임 추가 |
| **Custom Message** | 메시지 전송 전 | 이메일/SMS 템플릿 커스텀 |

```javascript
// Pre Sign-up: 회사 이메일만 허용
exports.handler = async (event) => {
    const email = event.request.userAttributes.email;
    if (!email.endsWith('@company.com')) {
        throw new Error('회사 이메일만 가입 가능합니다');
    }
    event.response.autoConfirmUser = false;
    return event;
};

// Post Confirmation: DynamoDB에 사용자 생성
exports.handler = async (event) => {
    await dynamodb.put({
        TableName: 'Users',
        Item: {
            userId: event.userName,
            email: event.request.userAttributes.email,
            createdAt: new Date().toISOString()
        }
    }).promise();
    return event;
};
```

### 5. Spring Boot 연동

```yaml
# application.yml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://cognito-idp.ap-northeast-2.amazonaws.com/<user-pool-id>
          jwk-set-uri: https://cognito-idp.ap-northeast-2.amazonaws.com/<user-pool-id>/.well-known/jwks.json
```

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasAuthority("SCOPE_admin")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt
                    .jwtAuthenticationConverter(cognitoJwtConverter())
                )
            );
        return http.build();
    }

    private JwtAuthenticationConverter cognitoJwtConverter() {
        JwtGrantedAuthoritiesConverter converter = new JwtGrantedAuthoritiesConverter();
        converter.setAuthoritiesClaimName("cognito:groups");
        converter.setAuthorityPrefix("ROLE_");

        JwtAuthenticationConverter jwtConverter = new JwtAuthenticationConverter();
        jwtConverter.setJwtGrantedAuthoritiesConverter(converter);
        return jwtConverter;
    }
}

// Controller에서 사용자 정보 접근
@GetMapping("/api/me")
public Map<String, String> me(@AuthenticationPrincipal Jwt jwt) {
    return Map.of(
        "userId", jwt.getSubject(),
        "email", jwt.getClaimAsString("email"),
        "groups", jwt.getClaimAsStringList("cognito:groups").toString()
    );
}
```

### 6. Cognito vs 자체 인증 vs Auth0

| 항목 | Cognito | 자체 구축 | Auth0 |
|------|---------|----------|-------|
| **비용** | MAU 기반 과금 | 서버 비용 | MAU 기반 (비쌈) |
| **구현 시간** | 빠름 | 오래 걸림 | 빠름 |
| **커스텀** | Lambda 트리거 | 완전 자유 | 커스텀 규칙 |
| **AWS 통합** | 네이티브 | 별도 구현 | SDK |
| **소셜 로그인** | 기본 제공 | 직접 구현 | 기본 제공 |
| **MAU 50K 무료** | ✅ | - | ❌ (7K까지) |
| **적합한 경우** | AWS 기반 서비스 | 특수 요구사항 | 멀티 클라우드 |

## 운영 팁

### 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| MFA 활성화 | 관리자 계정 필수, 일반 사용자 권장 | ✅ |
| 비밀번호 정책 | 최소 8자, 대소문자+숫자+특수문자 | ✅ |
| 토큰 만료 시간 | Access Token 1시간 이하 | ✅ |
| Lambda 트리거 | Post Confirmation으로 사용자 동기화 | ⭐ |
| 어드밴스드 보안 | 이상 로그인 탐지, 자격증명 침해 보호 | ⭐ |

## 참고

- [AWS Cognito 공식 문서](https://docs.aws.amazon.com/cognito/)
- [IAM](IAM.md) — AWS 리소스 접근 제어
- [API Gateway](../Network/API_Gateway.md) — Cognito Authorizer 설정
- [인증 전략](../../Backend/Authentication/Authentication_Strategy.md) — 인증 방식 비교
