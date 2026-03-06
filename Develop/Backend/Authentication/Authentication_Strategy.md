---
title: 인증/인가 전략 비교 가이드
tags: [backend, authentication, authorization, session, jwt, oauth2, sso, token]
updated: 2026-03-01
---

# 인증/인가 전략 비교 가이드

## 개요

인증(Authentication)과 인가(Authorization)는 모든 백엔드 시스템의 핵심이다. 세션, JWT, OAuth2 등 다양한 방식이 있으며, 시스템 요구사항에 맞는 전략을 선택해야 한다.

### 인증 vs 인가

```
인증 (Authentication): "너 누구야?"
  → 로그인, 신원 확인

인가 (Authorization): "너 이거 할 수 있어?"
  → 권한 확인, 접근 제어
```

## 핵심

### 1. 인증 방식 비교

| 항목 | Session | JWT | OAuth2 |
|------|---------|-----|--------|
| **상태** | Stateful (서버 저장) | Stateless (토큰 자체) | 둘 다 가능 |
| **저장 위치** | 서버 메모리/Redis | 클라이언트 (쿠키/헤더) | 인가 서버 |
| **확장성** | 세션 공유 필요 (Redis) | 서버 간 공유 불필요 | 높음 |
| **보안** | 서버 제어 (즉시 무효화) | 만료 전 무효화 어려움 | 토큰 위임 |
| **적합한 상황** | 전통적 웹, 소규모 | REST API, MSA | 소셜 로그인, 3rd party |

### 2. Session 기반 인증

```
1. 로그인 요청 (ID/PW)
2. 서버: 세션 생성, 세션 ID 발급
3. 클라이언트: 쿠키에 세션 ID 저장
4. 이후 요청마다 쿠키로 세션 ID 전송
5. 서버: 세션 ID → 세션 스토어 조회 → 사용자 확인

Client ──Cookie: JSESSIONID=abc123──▶ Server
                                       │
                                  Session Store
                                  (Memory / Redis)
```

**장점:**
- 서버가 세션을 완전히 제어 (즉시 로그아웃, 강제 종료)
- 구현이 단순 (Spring Security 기본)
- 민감 정보가 서버에만 존재

**단점:**
- 서버 수 증가 시 세션 공유 필요 (Sticky Session 또는 Redis)
- 모바일 앱에서 쿠키 관리 불편
- CSRF 공격에 취약 (쿠키 자동 전송)

```java
// Spring Security 세션 설정
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    return http
        .sessionManagement(session -> session
            .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
            .maximumSessions(1)                // 동시 세션 1개
            .maxSessionsPreventsLogin(false))   // 기존 세션 만료
        .build();
}
```

### 3. JWT 기반 인증

```
1. 로그인 요청 (ID/PW)
2. 서버: JWT Access Token + Refresh Token 발급
3. 클라이언트: 토큰 저장 (메모리/localStorage)
4. 이후 요청마다 Authorization 헤더로 전송
5. 서버: 토큰 서명 검증 → 페이로드에서 사용자 확인 (DB 조회 불필요)

Client ──Authorization: Bearer eyJhbG...──▶ Server
                                             │
                                      서명 검증만 (DB 조회 X)
```

**장점:**
- Stateless: 서버 확장 용이 (세션 공유 불필요)
- 모바일/SPA에 적합 (헤더 기반)
- 마이크로서비스 간 토큰 전달 용이

**단점:**
- 발급된 토큰 즉시 무효화 불가 (만료까지 유효)
- 토큰 크기가 세션 ID보다 큼 (매 요청 전송)
- 탈취 시 만료까지 악용 가능

#### Token 전략

```
Access Token (짧은 수명: 15~30분)
  └─ API 요청 인증에 사용
  └─ 탈취 시 피해 최소화

Refresh Token (긴 수명: 7~14일)
  └─ Access Token 재발급에만 사용
  └─ DB/Redis에 저장하여 서버 측 무효화 가능
  └─ Rotation: 사용 시 새 Refresh Token 발급, 이전 것 폐기
```

```java
// Refresh Token Rotation
@Transactional
public AuthResponse refresh(String refreshToken) {
    // 1. Refresh Token 유효성 확인
    if (!tokenProvider.validateToken(refreshToken)) {
        throw new InvalidTokenException();
    }

    // 2. DB에서 저장된 Refresh Token과 비교
    String email = tokenProvider.getEmailFromToken(refreshToken);
    RefreshToken stored = refreshTokenRepository.findByEmail(email)
        .orElseThrow(InvalidTokenException::new);

    if (!stored.getToken().equals(refreshToken)) {
        // 이미 사용된 토큰 → 탈취 의심 → 모든 토큰 무효화
        refreshTokenRepository.deleteByEmail(email);
        throw new TokenReusedException("토큰 재사용 감지. 재로그인 필요.");
    }

    // 3. 새 토큰 쌍 발급 (Rotation)
    String newAccessToken = tokenProvider.generateAccessToken(email, stored.getRole());
    String newRefreshToken = tokenProvider.generateRefreshToken(email);

    // 4. 기존 Refresh Token 교체
    stored.updateToken(newRefreshToken);

    return new AuthResponse(newAccessToken, newRefreshToken);
}
```

### 4. OAuth2 / OpenID Connect

**제3자 인증 위임** 방식이다. 사용자가 Google, Kakao 등에 로그인하면, 해당 서비스가 인증을 대신 처리한다.

```
1. 사용자 → "Google로 로그인" 클릭
2. Google 로그인 페이지로 리다이렉트
3. 사용자: Google에서 로그인
4. Google → 우리 서버로 Authorization Code 전달
5. 우리 서버: Code → Google API → Access Token 획득
6. 우리 서버: Access Token으로 Google 사용자 정보 조회
7. 우리 서버: 자체 JWT/Session 발급

사용자 ──▶ 우리 서비스 ──▶ Google (인가 서버)
                           │
                     Code 발급
                           │
            우리 서비스 ◀───┘
                │
          Token 교환 → 사용자 정보 획득
                │
          자체 JWT 발급
```

| 용어 | 설명 |
|------|------|
| **Authorization Code** | 일회용 코드 (토큰 교환에 사용) |
| **Access Token** | 리소스 접근용 토큰 (Google API 호출) |
| **Refresh Token** | Access Token 재발급용 |
| **Scope** | 접근 범위 (email, profile 등) |
| **OpenID Connect** | OAuth2 위에 인증 계층 추가 (ID Token) |

### 5. SSO (Single Sign-On)

한 번 로그인하면 여러 서비스에 자동 로그인되는 방식이다.

```
사용자 → 서비스 A (로그인 필요)
           │
      SSO 서버로 리다이렉트
           │
      SSO 서버에서 로그인
           │
      서비스 A 접근 가능
           │
사용자 → 서비스 B (로그인 필요)
           │
      SSO 서버 확인 → 이미 인증됨
           │
      서비스 B 접근 가능 (재로그인 불필요)
```

| 구현 방식 | 설명 |
|-----------|------|
| **SAML** | XML 기반, 엔터프라이즈 (Active Directory 등) |
| **OAuth2 + OIDC** | 모던 SSO의 표준 |
| **Keycloak** | 오픈소스 IAM (자체 호스팅 SSO 서버) |
| **Auth0 / Firebase Auth** | 관리형 SaaS |

### 6. API Key 인증

서버 간 통신이나 외부 API 연동에 사용하는 간단한 인증 방식이다.

```
Client ──X-API-Key: sk_live_abc123──▶ Server

장점: 구현 단순, 서버 간 통신에 적합
단점: 키 탈취 시 무제한 접근, 사용자 식별 불가
```

| 인증 방식 | 적합한 상황 |
|-----------|-----------|
| **API Key** | 서버 간 통신, 3rd party API |
| **JWT** | 사용자 인증, REST API, MSA |
| **Session** | 전통적 웹 애플리케이션 |
| **OAuth2** | 소셜 로그인, 3rd party 접근 위임 |

## 운영 팁

### 보안 체크리스트

| 항목 | 설명 |
|------|------|
| **HTTPS 필수** | 토큰/쿠키가 평문으로 전송되면 탈취 가능 |
| **비밀번호 해싱** | BCrypt (cost 10+) 필수 |
| **토큰 저장** | Access: 메모리, Refresh: httpOnly 쿠키 또는 서버 DB |
| **CSRF** | 쿠키 인증 시 CSRF 토큰 필수 |
| **Rate Limiting** | 로그인 시도 제한 (brute force 방지) |
| **Refresh Token Rotation** | 재사용 감지로 탈취 대응 |
| **로그아웃** | JWT: 블랙리스트/Refresh Token 삭제, Session: 세션 무효화 |

### 토큰 저장 위치 비교

| 위치 | XSS | CSRF | 추천 |
|------|-----|------|------|
| **localStorage** | 취약 | 안전 | 비추천 |
| **httpOnly Cookie** | 안전 | 취약 (CSRF 대응 필요) | Access Token |
| **메모리 (변수)** | 안전 | 안전 | Access Token (SPA) |
| **서버 DB/Redis** | 안전 | 안전 | Refresh Token |

## 참고

- [OAuth 2.0 스펙](https://oauth.net/2/)
- [JWT.io](https://jwt.io/)
- [Spring Security](Spring_Security.md) — Spring 구현 상세
- [OAuth 개요](../../Security/OAuth.md)
- [CORS](../../WebServer/Nginx/CORS.md)
