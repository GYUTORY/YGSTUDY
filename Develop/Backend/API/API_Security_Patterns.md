---
title: API 인증/인가 실무 패턴
tags:
  - API
  - Security
  - JWT
  - OAuth2
  - HMAC
updated: 2026-05-06
---

# API 인증/인가 실무 패턴

## JWT 토큰 설계

### payload 크기 문제

JWT는 매 요청마다 헤더에 실려 간다. payload에 권한 목록, 사용자 프로필 전부 넣으면 토큰이 수 KB까지 커진다. 실제로 겪는 문제:

- **Nginx/ALB 기본 헤더 크기 제한**에 걸린다. Nginx는 `large_client_header_buffers` 기본값이 8KB다. 토큰이 커지면 431 Request Header Fields Too Large가 뜬다.
- **Redis 세션 저장 대비 이점이 사라진다.** payload가 크면 네트워크 비용이 세션 방식과 비슷해진다.

payload에는 `sub`(사용자 ID), `roles`(역할 배열), `exp`, `iat` 정도만 넣는다. 상세 권한은 서버에서 캐시로 조회한다.

```json
{
  "sub": "user-123",
  "roles": ["admin"],
  "exp": 1711468800,
  "iat": 1711465200
}
```

### 만료 처리

access token 만료 시간을 짧게 잡으면(15분 이하) 보안은 좋지만, 클라이언트에서 만료 처리를 제대로 안 하면 사용자가 수시로 로그아웃된다.

서버 측 검증 시 주의할 점:

```java
try {
    Claims claims = Jwts.parserBuilder()
        .setSigningKey(secretKey)
        .setAllowedClockSkewSeconds(30) // 서버 간 시간 차이 허용
        .build()
        .parseClaimsJws(token)
        .getBody();
} catch (ExpiredJwtException e) {
    // 만료된 토큰이라도 claims는 꺼낼 수 있다
    // refresh 토큰 갱신 시 사용자 식별에 쓸 수 있음
    Claims claims = e.getClaims();
    String userId = claims.getSubject();
}
```

`setAllowedClockSkewSeconds`를 안 넣으면 서버 간 시간이 1초만 어긋나도 토큰 검증이 실패한다. 멀티 인스턴스 환경에서 NTP 동기화가 완벽하지 않은 경우 반드시 넣어야 한다.

### Refresh Token Rotation

refresh token은 한 번 사용하면 폐기하고 새 refresh token을 발급한다. 탈취된 refresh token이 재사용되면 즉시 감지할 수 있다.

```java
@Transactional
public TokenPair refresh(String refreshToken) {
    RefreshTokenEntity stored = refreshTokenRepository
        .findByToken(refreshToken)
        .orElseThrow(() -> new InvalidTokenException("존재하지 않는 토큰"));

    // 이미 사용된 토큰이면 토큰 탈취로 판단
    if (stored.isUsed()) {
        // 해당 사용자의 모든 refresh token 폐기
        refreshTokenRepository.revokeAllByUserId(stored.getUserId());
        throw new TokenTheftException("토큰 재사용 감지");
    }

    // 현재 토큰을 사용 처리
    stored.markAsUsed();
    refreshTokenRepository.save(stored);

    // 새 토큰 쌍 발급
    String newAccessToken = generateAccessToken(stored.getUserId());
    String newRefreshToken = generateRefreshToken(stored.getUserId());

    refreshTokenRepository.save(
        new RefreshTokenEntity(newRefreshToken, stored.getUserId())
    );

    return new TokenPair(newAccessToken, newRefreshToken);
}
```

주의할 점: rotation 구현 시 DB 트랜잭션을 걸어야 한다. 동시에 같은 refresh token으로 2개 요청이 들어오면, 하나는 성공하고 하나는 토큰 탈취로 감지되는 게 정상이다. 트랜잭션 없이 구현하면 둘 다 성공해서 refresh token이 2개 생긴다.

### 토큰 강제 무효화 (jti blacklist)

JWT는 stateless가 장점인데, 그게 단점도 된다. 만료 전에는 폐기 수단이 없다. 비밀번호 변경, 계정 정지, 이상 로그인 감지 같은 상황에서 발급된 토큰을 즉시 막아야 하는 일이 실무에서는 자주 생긴다.

표준 방식은 `jti`(JWT ID) 클레임을 넣고, 폐기된 jti를 Redis에 올려놓는 것이다. 모든 access token에 jti를 발급한다.

```java
public String generateAccessToken(String userId) {
    String jti = UUID.randomUUID().toString();
    return Jwts.builder()
        .setId(jti)
        .setSubject(userId)
        .setIssuedAt(new Date())
        .setExpiration(Date.from(Instant.now().plusSeconds(900)))
        .signWith(secretKey)
        .compact();
}
```

폐기 시 Redis에 jti를 저장한다. TTL은 토큰 남은 만료 시간으로 잡는다. 만료가 지나면 어차피 토큰이 무효라 blacklist에 둘 필요가 없다.

```java
public void revokeToken(String jti, long expiresInSeconds) {
    String key = "jwt:blacklist:" + jti;
    redis.opsForValue().set(key, "1", Duration.ofSeconds(expiresInSeconds));
}

public void revokeAllUserTokens(String userId) {
    // 사용자 전체 토큰 무효화는 jti 단위로는 어렵다
    // 사용자별 token version을 올리는 방식이 실무에서 많이 쓴다
    String key = "jwt:user_version:" + userId;
    redis.opsForValue().increment(key);
}
```

검증 필터에서는 jti를 매번 Redis에 조회한다. 모든 요청에서 1번 추가 조회가 발생하지만, Redis 단순 GET은 1ms 미만이라 실측상 큰 부담은 아니다. 캐시 미스를 줄이려면 Caffeine 같은 로컬 캐시를 1~2초짜리로 앞에 두면 된다.

```java
public Authentication authenticate(String token) {
    Claims claims = parseToken(token);
    String jti = claims.getId();

    // blacklist 조회
    if (Boolean.TRUE.equals(redis.hasKey("jwt:blacklist:" + jti))) {
        throw new InvalidTokenException("폐기된 토큰");
    }

    // 사용자 단위 무효화 (token version)
    String userId = claims.getSubject();
    Long tokenVersion = claims.get("ver", Long.class);
    String currentVersion = redis.opsForValue()
        .get("jwt:user_version:" + userId);
    if (currentVersion != null
            && Long.parseLong(currentVersion) > tokenVersion) {
        throw new InvalidTokenException("사용자 토큰 버전 불일치");
    }

    return buildAuthentication(claims);
}
```

사용자 단위 무효화는 토큰에 `ver` 클레임을 넣고, 폐기 시점에 Redis 카운터를 올리는 방식이 깔끔하다. jti 하나하나를 다 blacklist에 넣을 필요가 없다.

실무에서 자주 빠뜨리는 것:
- access token만 무효화하고 refresh token은 그대로 두는 경우. 비밀번호 변경 같은 시나리오에서는 refresh token도 같이 폐기해야 한다.
- Redis가 죽었을 때 blacklist 조회가 실패하면 어떻게 처리할지. fail-open(통과)이면 보안 구멍, fail-closed(거부)면 가용성 문제가 된다. 실무에서는 fail-closed + 회로 차단기로 짧게 끊고, blacklist 조회 실패율을 알람으로 걸어둔다.

---

## OAuth2 Authorization Code + PKCE

모바일 앱이나 SPA에서 OAuth2를 쓸 때 Authorization Code + PKCE를 써야 한다. client_secret을 클라이언트에 넣을 수 없기 때문이다.

### PKCE 흐름

```
1. 클라이언트가 code_verifier(랜덤 문자열)를 생성
2. code_verifier를 SHA256 해시 → code_challenge
3. 인가 요청 시 code_challenge 전달
4. 인가 코드를 받으면 토큰 요청 시 code_verifier 전달
5. 서버가 code_verifier를 해시해서 code_challenge와 비교
```

Spring Security로 구현할 때:

```java
@Configuration
@EnableWebSecurity
public class OAuth2Config {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.oauth2Login(oauth2 -> oauth2
            .authorizationEndpoint(auth -> auth
                .authorizationRequestResolver(
                    pkceAuthorizationRequestResolver()
                )
            )
        );
        return http.build();
    }

    private OAuth2AuthorizationRequestResolver pkceAuthorizationRequestResolver() {
        DefaultOAuth2AuthorizationRequestResolver resolver =
            new DefaultOAuth2AuthorizationRequestResolver(
                clientRegistrationRepository,
                "/oauth2/authorization"
            );

        // PKCE 파라미터 자동 추가
        resolver.setAuthorizationRequestCustomizer(
            OAuth2AuthorizationRequestCustomizers.withPkce()
        );
        return resolver;
    }
}
```

Spring Security 6.x부터는 `withPkce()`를 호출하면 code_verifier 생성, code_challenge 계산, 세션 저장까지 자동 처리된다. 직접 구현할 필요 없다.

직접 구현해야 하는 경우(비 Spring 환경):

```java
public class PkceUtil {

    public static String generateCodeVerifier() {
        byte[] bytes = new byte[32];
        new SecureRandom().nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    public static String generateCodeChallenge(String codeVerifier) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(codeVerifier.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }
}
```

code_verifier는 반드시 `SecureRandom`을 써야 한다. `Math.random()`이나 `UUID.randomUUID()`는 예측 가능성이 있다.

### Resource Server 검증 패턴

OAuth2에서 access token을 받은 Resource Server(API 서버)가 토큰을 검증하는 방식은 둘 중 하나다.

**JWT 자체 검증 (local validation)**: 토큰 안에 서명이 들어 있어서 서버에서 공개키로 검증만 하면 된다. Authorization Server에 요청을 보낼 필요가 없다. Auth Server의 JWKS 엔드포인트에서 공개키를 받아 캐시한다.

```java
@Configuration
@EnableWebSecurity
public class ResourceServerConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.oauth2ResourceServer(oauth2 -> oauth2
            .jwt(jwt -> jwt
                .jwkSetUri("https://auth.example.com/.well-known/jwks.json")
                .jwtAuthenticationConverter(jwtAuthenticationConverter())
            )
        );
        return http.build();
    }

    private JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtGrantedAuthoritiesConverter converter =
            new JwtGrantedAuthoritiesConverter();
        converter.setAuthorityPrefix("SCOPE_");
        converter.setAuthoritiesClaimName("scope");

        JwtAuthenticationConverter jwtConverter =
            new JwtAuthenticationConverter();
        jwtConverter.setJwtGrantedAuthoritiesConverter(converter);
        return jwtConverter;
    }
}
```

**Token Introspection (RFC 7662)**: 토큰을 받을 때마다 Authorization Server에 물어본다. opaque token(서명되지 않은 임의 문자열)을 쓸 때 사용한다.

```java
@Bean
public OpaqueTokenIntrospector introspector() {
    return new SpringOpaqueTokenIntrospector(
        "https://auth.example.com/oauth2/introspect",
        "client-id",
        "client-secret"
    );
}

http.oauth2ResourceServer(oauth2 -> oauth2
    .opaqueToken(opaque -> opaque.introspector(introspector()))
);
```

introspection 응답은 RFC 7662 표준 형식을 따른다.

```json
{
  "active": true,
  "scope": "read write",
  "client_id": "abc123",
  "username": "user@example.com",
  "exp": 1711468800,
  "sub": "user-123"
}
```

`active: false`면 토큰이 만료됐거나 폐기된 것이다. 다른 필드는 표시되지 않을 수도 있다.

둘 중 무엇을 쓸지 판단 기준:

| 기준 | JWT (local) | Introspection (remote) |
|------|------------|------------------------|
| 검증 속도 | 빠름 (공개키 검증만) | 느림 (HTTP 호출) |
| 즉시 폐기 | 어려움 (jti blacklist 필요) | 쉬움 (Auth Server에서 무효화하면 끝) |
| 네트워크 의존 | JWKS 캐시 갱신 시점만 | 모든 요청 |
| 토큰 크기 | 큼 (KB 단위) | 작음 (랜덤 문자열) |

실무에서 자주 보는 절충안: access token은 JWT(빠른 검증) + jti blacklist(즉시 폐기), refresh token은 opaque(introspection으로만 검증). 양쪽 장점만 챙기는 패턴이다.

introspection을 쓸 때는 캐시가 필수다. 매 API 요청마다 Auth Server를 때리면 Auth Server가 병목이 된다.

```java
@Bean
public OpaqueTokenIntrospector cachedIntrospector(
        OpaqueTokenIntrospector delegate,
        CacheManager cacheManager) {
    return new CachingOpaqueTokenIntrospector(
        delegate,
        cacheManager.getCache("introspection"),
        Duration.ofSeconds(60) // 토큰 유효 기간보다 짧게
    );
}

public class CachingOpaqueTokenIntrospector implements OpaqueTokenIntrospector {

    private final OpaqueTokenIntrospector delegate;
    private final Cache cache;
    private final Duration ttl;

    public OAuth2AuthenticatedPrincipal introspect(String token) {
        // 토큰 자체를 캐시 키로 쓰면 토큰이 로그에 남을 수 있다
        // SHA-256 해시를 키로 쓰는 게 안전하다
        String cacheKey = sha256(token);
        OAuth2AuthenticatedPrincipal cached =
            cache.get(cacheKey, OAuth2AuthenticatedPrincipal.class);
        if (cached != null) {
            return cached;
        }

        OAuth2AuthenticatedPrincipal principal = delegate.introspect(token);
        cache.put(cacheKey, principal);
        return principal;
    }
}
```

캐시 TTL은 60초 이하로 짧게 잡아야 한다. 길게 잡으면 토큰을 폐기해도 캐시가 살아 있는 동안 통과한다. 즉시 폐기가 중요하면 캐시를 안 쓰거나, Auth Server에서 폐기 이벤트를 받아 캐시를 무효화하는 구조를 만든다.

---

## API Key 관리

### 발급

API Key는 충분히 길어야 한다. 최소 32바이트(256비트). 저장할 때는 해시값만 저장하고, 원본은 발급 시점에만 보여준다.

```java
@Transactional
public ApiKeyResponse issueApiKey(Long clientId, String description) {
    // 원본 키 생성
    byte[] keyBytes = new byte[32];
    new SecureRandom().nextBytes(keyBytes);
    String rawKey = "sk_live_" + Base64.getUrlEncoder()
        .withoutPadding().encodeToString(keyBytes);

    // prefix만 저장 (목록 조회용)
    String prefix = rawKey.substring(0, 12);

    // SHA-256 해시만 DB에 저장
    String hashedKey = sha256(rawKey);

    ApiKeyEntity entity = new ApiKeyEntity();
    entity.setClientId(clientId);
    entity.setKeyHash(hashedKey);
    entity.setKeyPrefix(prefix);
    entity.setDescription(description);
    entity.setCreatedAt(Instant.now());
    apiKeyRepository.save(entity);

    // 원본은 이 응답에서만 보여줌
    return new ApiKeyResponse(rawKey, prefix, entity.getId());
}
```

prefix(`sk_live_`)를 붙이는 이유: 로그나 코드에서 실수로 노출됐을 때 어떤 종류의 키인지 바로 알 수 있고, secret scanning 도구가 탐지할 수 있다. Stripe, OpenAI 등 대부분의 서비스가 이 패턴을 쓴다.

### 폐기

즉시 폐기가 가능해야 한다. API Key 검증 시 캐시를 쓰고 있다면, 폐기 시점에 캐시도 같이 날려야 한다.

```java
@Transactional
public void revokeApiKey(Long keyId, Long clientId) {
    ApiKeyEntity key = apiKeyRepository.findByIdAndClientId(keyId, clientId)
        .orElseThrow(() -> new NotFoundException("API Key not found"));

    key.setRevokedAt(Instant.now());
    apiKeyRepository.save(key);

    // 캐시 즉시 무효화
    apiKeyCache.evict(key.getKeyHash());
}
```

폐기된 키로 요청이 들어오면 401이 아니라 403을 반환하는 게 맞다. 401은 "인증 안 됨", 403은 "인증은 됐지만 권한 없음(폐기됨)"이다. 클라이언트가 키를 재발급해야 하는지, 다른 키를 써야 하는지 구분할 수 있다.

### Rate Limit 연동

API Key별로 rate limit을 걸어야 한다. Redis의 sliding window 방식이 실무에서 가장 많이 쓰인다.

```java
@Component
public class ApiKeyRateLimiter {

    private final StringRedisTemplate redis;

    public boolean isAllowed(String keyHash, RateLimitPlan plan) {
        String redisKey = "rate:" + keyHash;
        long now = Instant.now().toEpochMilli();
        long windowStart = now - plan.getWindowMillis();

        // Lua 스크립트로 원자적 처리
        String luaScript = """
            redis.call('ZREMRANGEBYSCORE', KEYS[1], '0', ARGV[1])
            local count = redis.call('ZCARD', KEYS[1])
            if count < tonumber(ARGV[2]) then
                redis.call('ZADD', KEYS[1], ARGV[3], ARGV[3])
                redis.call('EXPIRE', KEYS[1], ARGV[4])
                return 1
            end
            return 0
            """;

        Long result = redis.execute(
            new DefaultRedisScript<>(luaScript, Long.class),
            List.of(redisKey),
            String.valueOf(windowStart),
            String.valueOf(plan.getMaxRequests()),
            String.valueOf(now),
            String.valueOf(plan.getWindowMillis() / 1000 + 1)
        );

        return result != null && result == 1;
    }
}
```

Lua 스크립트를 쓰는 이유: ZREMRANGEBYSCORE → ZCARD → ZADD를 별도 명령으로 보내면 그 사이에 다른 요청이 끼어들 수 있다. Lua 스크립트는 Redis에서 원자적으로 실행된다.

rate limit 응답 헤더도 내려줘야 한다:

```java
response.setHeader("X-RateLimit-Limit", String.valueOf(plan.getMaxRequests()));
response.setHeader("X-RateLimit-Remaining", String.valueOf(remaining));
response.setHeader("X-RateLimit-Reset", String.valueOf(resetTimestamp));
```

### 키 회전 (rotation)

API Key는 정기적으로 회전시켜야 한다. 회전 자체보다 회전 중 다운타임 없이 교체하는 게 어렵다. 클라이언트가 새 키로 한 번에 갈아탈 수 없는 환경(여러 서버, 배포 시차, 외부 파트너)에서는 새 키와 옛 키가 동시에 유효한 grace period가 필요하다.

스키마 설계는 한 클라이언트에 여러 키가 동시 존재할 수 있게 만든다. `is_primary` 같은 플래그는 두지 않는다. 모든 활성 키가 검증을 통과하게 두는 게 운영이 단순하다.

```sql
CREATE TABLE api_keys (
    id BIGINT PRIMARY KEY,
    client_id BIGINT NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    key_prefix VARCHAR(16) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    INDEX idx_key_hash (key_hash),
    INDEX idx_client_active (client_id, revoked_at, expires_at)
);
```

회전 흐름은 보통 이렇게 간다.

1. 새 키 발급. 옛 키는 그대로 둔다. 두 키 모두 유효.
2. 클라이언트가 새 키로 교체. `last_used_at`을 보면서 옛 키가 여전히 쓰이는지 모니터링.
3. 옛 키 사용이 멈추거나 grace period(보통 7~30일)가 지나면 옛 키 폐기.

```java
@Transactional
public ApiKeyResponse rotateApiKey(Long oldKeyId, Long clientId, Duration gracePeriod) {
    ApiKeyEntity oldKey = apiKeyRepository.findByIdAndClientId(oldKeyId, clientId)
        .orElseThrow(() -> new NotFoundException("API Key not found"));

    if (oldKey.getRevokedAt() != null) {
        throw new IllegalStateException("이미 폐기된 키");
    }

    // 옛 키에 만료 시각 설정. 즉시 폐기는 아님
    oldKey.setExpiresAt(Instant.now().plus(gracePeriod));
    apiKeyRepository.save(oldKey);

    // 새 키 발급
    ApiKeyResponse newKey = issueApiKey(clientId, oldKey.getDescription());

    // 클라이언트에 회전 알림 (이메일, 웹훅)
    rotationNotifier.notify(clientId, oldKey.getKeyPrefix(),
        newKey.getPrefix(), oldKey.getExpiresAt());

    return newKey;
}
```

`last_used_at`을 매 요청마다 DB에 업데이트하면 부하가 크다. Redis에 1분 단위로 모았다가 백그라운드 잡에서 DB로 flush하는 식으로 처리한다.

회전 시점 판단: AWS, GCP 같은 클라우드 IAM은 90일 권장이지만, B2B API에서는 6개월~1년이 현실적이다. 짧을수록 좋지만 클라이언트 운영 부담을 같이 봐야 한다. 사고 발생 시(키 유출 의심)는 즉시 강제 회전. 정기 회전은 캘린더에 박아두고 한다.

옛 키 만료가 임박했을 때 클라이언트가 아직 새 키로 교체 못 했으면 차단보다 알림이 먼저다. 이메일 + 응답 헤더로 경고한다.

```java
if (key.isExpiringSoon(Duration.ofDays(7))) {
    response.setHeader("X-ApiKey-Deprecation",
        "key " + key.getKeyPrefix() + " expires at " + key.getExpiresAt());
    response.setHeader("Sunset", key.getExpiresAt().toString());
}
```

`Sunset` 헤더는 RFC 8594 표준이다. 클라이언트 SDK가 이 헤더를 보고 자동으로 경고 로그를 찍게 만들 수 있다.

### IP allowlist의 한계

API Key + IP allowlist 조합은 자주 쓰이지만, IP만 믿으면 안 된다. 실무에서 부딪히는 한계가 명확하다.

**클라우드 IP는 동적이다.** AWS Lambda, ECS Fargate, Cloud Run 같은 환경은 outbound IP가 풀에서 동적으로 할당된다. NAT Gateway를 고정해서 EIP를 쓰지 않으면 IP가 매번 바뀐다. 클라이언트에게 "이 IP로 요청하세요"라고 알려줘도 인프라 변경 한 번이면 무용지물이 된다.

**IP 풀을 받으면 의미가 약해진다.** AWS는 region별 IP 대역을 공개한다(`ip-ranges.json`). 어떤 클라이언트가 "AWS us-east-1 전체"를 allowlist에 올려달라고 하면, 그 안에서 누구든 요청을 보낼 수 있다는 뜻이다. allowlist 자체의 의미가 거의 사라진다.

**프록시 환경에서 IP 추출이 까다롭다.** ALB, CloudFront, Nginx 뒤에 있는 서버에서 클라이언트 IP를 받으려면 `X-Forwarded-For`를 파싱해야 하는데, 이 헤더는 클라이언트가 임의로 보낼 수 있다. 신뢰 가능한 프록시만 거치는지 확인 안 하고 `X-Forwarded-For`의 첫 IP를 그대로 쓰면 우회된다.

```java
public String getClientIp(HttpServletRequest request) {
    // 신뢰할 수 있는 프록시 IP 목록
    Set<String> trustedProxies = Set.of("10.0.0.0/8", "172.16.0.0/12");

    String xForwardedFor = request.getHeader("X-Forwarded-For");
    if (xForwardedFor == null) {
        return request.getRemoteAddr();
    }

    // X-Forwarded-For는 "client, proxy1, proxy2" 형태
    // 오른쪽부터 신뢰 가능한 프록시를 벗기고, 첫 untrusted IP가 실제 클라이언트
    String[] ips = xForwardedFor.split(",");
    for (int i = ips.length - 1; i >= 0; i--) {
        String ip = ips[i].trim();
        if (!isTrustedProxy(ip, trustedProxies)) {
            return ip;
        }
    }
    return request.getRemoteAddr();
}
```

이 작업은 직접 구현하지 말고 Spring의 `ForwardedHeaderFilter`나 `RemoteIpValve`(Tomcat)를 쓰는 게 안전하다. 직접 짜면 십중팔구 한두 곳에서 틀린다.

**IPv6 매칭 실수.** allowlist를 IPv4만 검사하다가 IPv6로 들어오는 요청을 놓치는 경우가 있다. CIDR 매칭 라이브러리(`IPAddress`, `commons-net`)를 쓰는 게 안전하다.

결론: IP allowlist는 보조 통제다. 단독으로 쓰지 말고 API Key 또는 mTLS 같은 강한 인증과 같이 써야 의미가 있다. "IP만 맞으면 통과"는 사실상 인증이 없는 상태다.

---

## CORS 설정에서 자주 틀리는 부분

### 와일드카드와 credentials

`Access-Control-Allow-Origin: *`와 `Access-Control-Allow-Credentials: true`는 동시에 쓸 수 없다. 브라우저가 거부한다.

```java
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            // 이렇게 하면 credentials 요청이 안 된다
            // .allowedOrigins("*")
            // .allowCredentials(true)

            // 명시적으로 origin을 지정해야 한다
            .allowedOrigins(
                "https://app.example.com",
                "https://admin.example.com"
            )
            .allowCredentials(true)
            .allowedMethods("GET", "POST", "PUT", "DELETE")
            .allowedHeaders("Authorization", "Content-Type")
            .maxAge(3600);
    }
}
```

### preflight 캐시

브라우저는 `Content-Type: application/json` 같은 비표준 헤더가 있으면 매번 OPTIONS preflight 요청을 보낸다. `maxAge`를 안 주면 매 API 호출마다 OPTIONS + 실제 요청, 총 2번 요청이 간다. `maxAge(3600)`을 주면 1시간 동안 preflight 결과를 캐시한다.

### allowedHeaders 누락

Spring에서 `allowedHeaders`를 지정하지 않으면 기본적으로 모든 헤더를 허용한다. 문제는 커스텀 헤더를 쓸 때 `exposedHeaders`를 안 넣는 경우다.

```java
// 클라이언트가 응답에서 커스텀 헤더를 읽어야 하는 경우
registry.addMapping("/api/**")
    .exposedHeaders("X-Request-Id", "X-RateLimit-Remaining");
```

`exposedHeaders`를 안 넣으면 브라우저 JavaScript에서 해당 헤더 값을 읽을 수 없다. 네트워크 탭에서는 보이는데 코드에서 접근이 안 되면 이 설정을 확인해야 한다.

### Spring Security와 CORS 충돌

Spring Security를 쓰면 `WebMvcConfigurer`의 CORS 설정이 무시될 수 있다. Security 필터가 먼저 실행되기 때문이다.

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.cors(cors -> cors.configurationSource(corsConfigurationSource()));
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of(
            "https://app.example.com"
        ));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source =
            new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
```

Spring Security를 쓰면 `SecurityFilterChain`에서 CORS를 설정하는 게 맞다. `WebMvcConfigurer`에만 넣으면 인증 실패 응답에 CORS 헤더가 안 붙어서, 클라이언트에서 401인지 CORS 에러인지 구분이 안 된다.

---

## 요청 서명(HMAC) 검증

웹훅 수신이나 서버 간 통신에서 요청이 변조되지 않았는지 검증할 때 HMAC을 쓴다. Stripe, GitHub Webhook 등이 이 방식을 사용한다.

### 서명 생성

```java
public class HmacUtil {

    public static String sign(String secret, String payload) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec keySpec = new SecretKeySpec(
                secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"
            );
            mac.init(keySpec);
            byte[] hash = mac.doFinal(
                payload.getBytes(StandardCharsets.UTF_8)
            );
            return Hex.encodeHexString(hash);
        } catch (Exception e) {
            throw new RuntimeException("HMAC 서명 실패", e);
        }
    }
}
```

### 서명 검증 필터

```java
@Component
public class HmacVerificationFilter extends OncePerRequestFilter {

    private final WebhookSecretProvider secretProvider;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {

        // 서명 헤더 확인
        String signature = request.getHeader("X-Signature-256");
        String timestamp = request.getHeader("X-Timestamp");

        if (signature == null || timestamp == null) {
            response.sendError(401, "서명 헤더 누락");
            return;
        }

        // 타임스탬프 검증 (replay attack 방지)
        long requestTime = Long.parseLong(timestamp);
        long now = Instant.now().getEpochSecond();
        if (Math.abs(now - requestTime) > 300) { // 5분 허용
            response.sendError(401, "요청 시간 초과");
            return;
        }

        // body 읽기 (한 번만 읽을 수 있으므로 캐싱 필요)
        CachedBodyHttpServletRequest cachedRequest =
            new CachedBodyHttpServletRequest(request);
        String body = new String(
            cachedRequest.getInputStream().readAllBytes(),
            StandardCharsets.UTF_8
        );

        // 서명 검증
        String signPayload = timestamp + "." + body;
        String expected = HmacUtil.sign(
            secretProvider.getSecret(), signPayload
        );

        // timing-safe 비교
        if (!MessageDigest.isEqual(
                signature.getBytes(StandardCharsets.UTF_8),
                ("sha256=" + expected).getBytes(StandardCharsets.UTF_8))) {
            response.sendError(401, "서명 불일치");
            return;
        }

        chain.doFilter(cachedRequest, response);
    }
}
```

중요한 부분 3가지:

**1. timing-safe 비교를 써야 한다.** `String.equals()`는 첫 번째 다른 문자에서 바로 false를 리턴한다. 공격자가 응답 시간을 측정해서 서명을 한 글자씩 맞출 수 있다(timing attack). `MessageDigest.isEqual()`은 항상 전체 바이트를 비교한다.

**2. timestamp를 서명에 포함해야 한다.** timestamp 없이 body만 서명하면, 과거에 유효했던 요청을 그대로 다시 보내는 replay attack이 가능하다. timestamp를 서명 payload에 넣고, 서버에서 현재 시간과 비교해서 5분 이내 요청만 허용한다.

**3. request body 캐싱이 필요하다.** `HttpServletRequest`의 `InputStream`은 한 번만 읽을 수 있다. 필터에서 서명 검증을 위해 읽으면, 컨트롤러에서 `@RequestBody`로 못 읽는다. `ContentCachingRequestWrapper`나 직접 만든 `CachedBodyHttpServletRequest`를 써서 body를 캐싱해야 한다.

```java
public class CachedBodyHttpServletRequest
        extends HttpServletRequestWrapper {

    private final byte[] cachedBody;

    public CachedBodyHttpServletRequest(HttpServletRequest request)
            throws IOException {
        super(request);
        this.cachedBody = request.getInputStream().readAllBytes();
    }

    @Override
    public ServletInputStream getInputStream() {
        ByteArrayInputStream bais = new ByteArrayInputStream(cachedBody);
        return new ServletInputStream() {
            @Override
            public int read() { return bais.read(); }
            @Override
            public boolean isFinished() { return bais.available() == 0; }
            @Override
            public boolean isReady() { return true; }
            @Override
            public void setReadListener(ReadListener listener) {}
        };
    }
}
```

### nonce 기반 replay 방어

timestamp 5분 윈도우만 두면 그 5분 안에는 같은 요청을 그대로 재전송할 수 있다. 결제처럼 멱등성이 깨지면 안 되는 API에서는 timestamp 검증만으로 부족하다. nonce를 같이 검증한다.

nonce는 요청마다 유일한 값이다. UUID를 쓰는 게 일반적이다. 서버에서 받은 nonce는 Redis에 timestamp 윈도우와 같은 TTL로 저장한다. 같은 nonce가 다시 오면 replay로 본다.

```java
@Component
public class NonceVerifier {

    private final StringRedisTemplate redis;
    private static final Duration NONCE_TTL = Duration.ofMinutes(5);

    public boolean verifyAndStore(String clientId, String nonce) {
        String key = "nonce:" + clientId + ":" + nonce;

        // SETNX: 키가 없을 때만 set, 있으면 false
        Boolean inserted = redis.opsForValue()
            .setIfAbsent(key, "1", NONCE_TTL);

        return Boolean.TRUE.equals(inserted);
    }
}
```

필터에 nonce 검증을 추가한다.

```java
String nonce = request.getHeader("X-Nonce");
if (nonce == null || nonce.length() < 16) {
    response.sendError(401, "nonce 누락 또는 길이 부족");
    return;
}

if (!nonceVerifier.verifyAndStore(clientId, nonce)) {
    response.sendError(401, "nonce 재사용 감지");
    return;
}

// nonce도 서명 payload에 포함시킨다
String signPayload = timestamp + "." + nonce + "." + body;
```

nonce도 서명 payload에 포함해야 한다. 안 그러면 공격자가 nonce만 바꿔서 서명을 다시 보내면 검증이 통과해버린다(서명은 timestamp + body로만 만든 거라).

nonce 저장 비용이 부담스러우면 client별로 prefix를 나눠서 저장한다. 여러 client의 nonce가 우연히 충돌해도 영향이 없다. TTL을 짧게(timestamp 윈도우와 동일) 잡으면 메모리 사용량은 분당 요청 수 × TTL 정도로 예측 가능하다.

### AWS SigV4 스타일 헤더 설계

웹훅 단방향 검증을 넘어 양방향 API 호출(B2B, 내부 서비스 간)에서 서명을 도입할 때 AWS Signature Version 4의 헤더 구조를 따라가는 게 합리적이다. 자체 발명하면 빠뜨리는 게 생긴다.

핵심 헤더 4개와 의미:

```
Authorization: HMAC-SHA256
  Credential=ak_abc123/20260506/api/v1,
  SignedHeaders=host;x-timestamp;x-nonce;content-type,
  Signature=a3c2...

X-Timestamp: 1715000000
X-Nonce: 3f8c-a2e1-...
Content-SHA256: 9b1a...
```

`Credential`은 키 ID + 날짜 + 스코프. 날짜를 분리한 이유는 derived key를 만들 때 쓰기 위해서다. AWS는 `kSecret → kDate → kRegion → kService → kSigning`으로 단계적 HMAC을 만든다. 이렇게 하면 root secret을 직접 서명에 쓰지 않고, 일자별 파생 키를 캐시할 수 있다.

`SignedHeaders`는 서명에 포함된 헤더 목록을 명시한다. 이게 없으면 서버가 어떤 헤더를 검증해야 할지 모른다. 클라이언트가 보낸 헤더 목록을 그대로 표기한다.

`Content-SHA256`은 body 해시를 별도 헤더로 분리. body가 비어 있을 때(`GET`)도 빈 문자열의 SHA-256을 넣어 일관되게 만든다.

서명 대상 문자열(canonical request) 구성:

```
HMAC-SHA256
20260506T120000Z
20260506/api/v1
SHA256(canonical_request)
```

`canonical_request`:

```
POST
/v1/payments
api_key=abc&limit=10
content-type:application/json
host:api.example.com
x-nonce:3f8c-a2e1-...
x-timestamp:1715000000

content-type;host;x-nonce;x-timestamp
9b1a5e...  (body SHA-256)
```

자체 구현 시 빠지기 쉬운 부분:

```java
public class CanonicalRequestBuilder {

    public String build(HttpServletRequest request, String body, List<String> signedHeaders) {
        StringBuilder sb = new StringBuilder();
        sb.append(request.getMethod()).append('\n');

        // path는 RFC 3986 방식으로 인코딩 (URI.create로 정규화)
        sb.append(URI.create(request.getRequestURI()).normalize().getPath()).append('\n');

        // query string은 키 알파벳 순으로 정렬, 같은 키는 값으로 또 정렬
        sb.append(canonicalQueryString(request.getQueryString())).append('\n');

        // header는 소문자 + trim, 알파벳 순 정렬
        for (String header : signedHeaders) {
            String value = request.getHeader(header).trim().replaceAll("\\s+", " ");
            sb.append(header.toLowerCase()).append(':').append(value).append('\n');
        }
        sb.append('\n');
        sb.append(String.join(";", signedHeaders)).append('\n');
        sb.append(sha256Hex(body));

        return sb.toString();
    }
}
```

빠뜨리면 검증이 어긋나는 포인트:

- 헤더 값의 trim과 연속 공백 정규화. 클라이언트가 보낸 `Content-Type: application/json `(끝 공백)과 서버에서 받은 값이 다르면 서명이 깨진다.
- query string의 정렬. `?b=2&a=1`과 `?a=1&b=2`는 의미가 같지만 서명은 다르다. 클라이언트와 서버 둘 다 알파벳 순으로 정렬해야 한다.
- 헤더 이름 대소문자. HTTP 헤더는 대소문자 구분이 없지만 서명 입력은 일관돼야 한다. 둘 다 소문자로 변환한다.
- path 정규화. `/v1/payments/`와 `/v1/payments`는 라우팅이 같아도 서명은 다르다. 클라이언트가 보낸 그대로 정규화한다.

derived key 방식:

```java
public byte[] deriveSigningKey(String secret, String date, String scope) {
    byte[] kDate = hmacSha256(("AWS4" + secret).getBytes(UTF_8), date);
    byte[] kScope = hmacSha256(kDate, scope);
    return hmacSha256(kScope, "aws4_request");
}
```

매 요청에서 root secret을 그대로 쓰지 않는다. 일자 + scope로 파생한 키만 서명에 사용한다. root secret이 노출되더라도 지난 키들이 자동으로 무효화되지는 않지만, 메모리에 root secret이 머무는 시간이 짧아진다. 일자별 캐시도 가능하다.

자체 프로토콜이 필요한 게 아니라면, 차라리 mTLS나 OAuth2 client_credentials를 쓰는 게 운영 부담이 적다. SigV4 스타일은 정말 클라이언트 라이브러리 없이 외부 파트너가 직접 호출해야 하고, 모든 요청에 무결성 + 인증이 필요한 상황에서만 쓴다.
