---
title: API 인증/인가 실무 패턴
tags:
  - API
  - Security
  - JWT
  - OAuth2
  - HMAC
updated: 2026-03-26
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
