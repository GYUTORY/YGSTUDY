---
title: Spring Security 핵심 개념과 실전 적용
tags: [framework, java, spring, spring-security, authentication, authorization, jwt, oauth2]
updated: 2026-03-01
---

# Spring Security 핵심 개념과 실전 적용

## 배경

Spring Security는 Spring 기반 애플리케이션의 **인증(Authentication)**과 **인가(Authorization)**를 담당하는 보안 프레임워크이다. 서블릿 필터 체인 기반으로 동작하며, 선언적 보안 설정과 세밀한 접근 제어를 제공한다.

### 왜 Spring Security인가

- **표준화된 보안**: 직접 구현 시 발생하는 보안 허점을 방지
- **필터 체인**: 요청마다 자동으로 보안 검증 수행
- **유연한 확장**: 폼 로그인, JWT, OAuth2, LDAP 등 다양한 인증 방식 지원
- **Spring 생태계 통합**: Spring Boot Auto Configuration으로 최소 설정

### 핵심 용어

| 용어 | 설명 |
|------|------|
| **Authentication** | "누구인가" — 사용자 신원 확인 |
| **Authorization** | "무엇을 할 수 있는가" — 권한/역할 기반 접근 제어 |
| **Principal** | 현재 인증된 사용자 |
| **GrantedAuthority** | 사용자에게 부여된 권한 (ROLE_USER, ROLE_ADMIN 등) |
| **SecurityContext** | 현재 요청의 보안 정보를 저장하는 컨텍스트 |

## 핵심

### 1. 아키텍처

#### Security Filter Chain

Spring Security는 **서블릿 필터 체인**으로 동작한다. 모든 HTTP 요청은 필터를 순서대로 통과한다.

```
HTTP 요청 → SecurityFilterChain
    │
    ├─ SecurityContextPersistenceFilter  (SecurityContext 로드)
    ├─ CorsFilter                        (CORS 처리)
    ├─ CsrfFilter                        (CSRF 토큰 검증)
    ├─ UsernamePasswordAuthenticationFilter (폼 로그인)
    ├─ BearerTokenAuthenticationFilter   (JWT 토큰)
    ├─ ExceptionTranslationFilter        (예외 처리)
    └─ AuthorizationFilter               (인가 확인)
    │
    ▼
  Controller
```

#### 인증 흐름

```
사용자 → AuthenticationFilter → AuthenticationManager
                                       │
                                AuthenticationProvider
                                       │
                                UserDetailsService  ←── DB 조회
                                       │
                                  UserDetails (사용자 정보)
                                       │
                               Authentication 객체 생성
                                       │
                              SecurityContextHolder에 저장
```

### 2. 기본 설정 (Spring Boot 3.x)

#### SecurityConfig

```java
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtFilter;
    private final CustomUserDetailsService userDetailsService;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(csrf -> csrf.disable())          // REST API는 CSRF 비활성화
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()        // 인증 없이 접근
                .requestMatchers("/api/admin/**").hasRole("ADMIN")  // ADMIN만 접근
                .requestMatchers("/api/**").authenticated()         // 인증 필요
                .anyRequest().permitAll()
            )
            .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
            .build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationManager(
            AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }
}
```

#### UserDetailsService 구현

```java
@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {

    private final UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        User user = userRepository.findByEmail(email)
            .orElseThrow(() -> new UsernameNotFoundException("사용자를 찾을 수 없습니다: " + email));

        return org.springframework.security.core.userdetails.User.builder()
            .username(user.getEmail())
            .password(user.getPassword())            // BCrypt 해시값
            .roles(user.getRole().name())             // ROLE_ 접두사 자동 추가
            .build();
    }
}
```

### 3. JWT 인증

REST API에서 가장 일반적인 인증 방식이다. 세션을 사용하지 않고 토큰으로 상태를 관리한다.

#### JWT 토큰 유틸리티

```java
@Component
public class JwtTokenProvider {

    @Value("${jwt.secret}")
    private String secretKey;

    @Value("${jwt.access-token-expiry}")
    private long accessTokenExpiry;     // 30분

    @Value("${jwt.refresh-token-expiry}")
    private long refreshTokenExpiry;    // 7일

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(secretKey.getBytes(StandardCharsets.UTF_8));
    }

    // Access Token 생성
    public String generateAccessToken(String email, String role) {
        return Jwts.builder()
            .subject(email)
            .claim("role", role)
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + accessTokenExpiry))
            .signWith(getSigningKey())
            .compact();
    }

    // Refresh Token 생성
    public String generateRefreshToken(String email) {
        return Jwts.builder()
            .subject(email)
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + refreshTokenExpiry))
            .signWith(getSigningKey())
            .compact();
    }

    // 토큰에서 이메일 추출
    public String getEmailFromToken(String token) {
        return getClaims(token).getSubject();
    }

    // 토큰 유효성 검증
    public boolean validateToken(String token) {
        try {
            getClaims(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            return false;
        }
    }

    private Claims getClaims(String token) {
        return Jwts.parser()
            .verifyWith(getSigningKey())
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }
}
```

#### JWT 인증 필터

```java
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider tokenProvider;
    private final CustomUserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        String token = extractToken(request);

        if (token != null && tokenProvider.validateToken(token)) {
            String email = tokenProvider.getEmailFromToken(token);
            UserDetails userDetails = userDetailsService.loadUserByUsername(email);

            UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(
                    userDetails, null, userDetails.getAuthorities());
            authentication.setDetails(
                new WebAuthenticationDetailsSource().buildDetails(request));

            SecurityContextHolder.getContext().setAuthentication(authentication);
        }

        filterChain.doFilter(request, response);
    }

    private String extractToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            return header.substring(7);
        }
        return null;
    }
}
```

### 4. OAuth2 로그인

소셜 로그인(Google, GitHub, Kakao 등)을 지원하는 OAuth2 설정이다.

#### application.yml

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: profile, email
          kakao:
            client-id: ${KAKAO_CLIENT_ID}
            client-secret: ${KAKAO_CLIENT_SECRET}
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
            scope: profile_nickname, account_email
        provider:
          kakao:
            authorization-uri: https://kauth.kakao.com/oauth/authorize
            token-uri: https://kauth.kakao.com/oauth/token
            user-info-uri: https://kapi.kakao.com/v2/user/me
            user-name-attribute: id
```

#### OAuth2 성공 핸들러

```java
@Component
@RequiredArgsConstructor
public class OAuth2SuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final JwtTokenProvider tokenProvider;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request,
                                        HttpServletResponse response,
                                        Authentication authentication) throws IOException {
        OAuth2User oAuth2User = (OAuth2User) authentication.getPrincipal();
        String email = oAuth2User.getAttribute("email");

        String accessToken = tokenProvider.generateAccessToken(email, "USER");
        String refreshToken = tokenProvider.generateRefreshToken(email);

        // 프론트엔드로 토큰 전달
        String redirectUrl = String.format(
            "https://frontend.com/oauth/callback?access=%s&refresh=%s",
            accessToken, refreshToken);

        getRedirectStrategy().sendRedirect(request, response, redirectUrl);
    }
}
```

### 5. 메서드 레벨 보안

Controller나 Service 메서드에 직접 권한을 지정할 수 있다.

```java
@Configuration
@EnableMethodSecurity   // Spring Boot 3.x
public class MethodSecurityConfig { }
```

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    // ADMIN 역할만 접근
    @PreAuthorize("hasRole('ADMIN')")
    @GetMapping
    public List<UserResponse> getAllUsers() { ... }

    // 본인 또는 ADMIN만 접근
    @PreAuthorize("#id == authentication.principal.id or hasRole('ADMIN')")
    @GetMapping("/{id}")
    public UserResponse getUser(@PathVariable Long id) { ... }

    // 인증된 사용자만 접근
    @PreAuthorize("isAuthenticated()")
    @PutMapping("/profile")
    public UserResponse updateProfile(@RequestBody UpdateRequest request) { ... }
}
```

### 6. CORS 설정

프론트엔드와 백엔드가 다른 도메인일 때 필수적인 설정이다.

```java
@Configuration
public class CorsConfig {

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of(
            "https://frontend.com",
            "http://localhost:3000"
        ));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "PATCH"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
```

## 예시

### 1. 회원가입 + 로그인 API 전체 구현

```java
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/signup")
    public ResponseEntity<AuthResponse> signup(@Valid @RequestBody SignupRequest request) {
        AuthResponse response = authService.signup(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        AuthResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/refresh")
    public ResponseEntity<AuthResponse> refresh(@RequestBody RefreshRequest request) {
        AuthResponse response = authService.refresh(request.getRefreshToken());
        return ResponseEntity.ok(response);
    }
}
```

```java
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;
    private final AuthenticationManager authenticationManager;

    @Transactional
    public AuthResponse signup(SignupRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new DuplicateEmailException(request.getEmail());
        }

        User user = User.builder()
            .email(request.getEmail())
            .password(passwordEncoder.encode(request.getPassword()))
            .name(request.getName())
            .role(Role.USER)
            .build();

        userRepository.save(user);

        String accessToken = tokenProvider.generateAccessToken(user.getEmail(), "USER");
        String refreshToken = tokenProvider.generateRefreshToken(user.getEmail());

        return new AuthResponse(accessToken, refreshToken);
    }

    public AuthResponse login(LoginRequest request) {
        authenticationManager.authenticate(
            new UsernamePasswordAuthenticationToken(
                request.getEmail(), request.getPassword()));

        String accessToken = tokenProvider.generateAccessToken(request.getEmail(), "USER");
        String refreshToken = tokenProvider.generateRefreshToken(request.getEmail());

        return new AuthResponse(accessToken, refreshToken);
    }
}
```

### 2. 현재 사용자 정보 조회

```java
// 커스텀 어노테이션
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
public @interface CurrentUser { }

// ArgumentResolver
@Component
public class CurrentUserResolver implements HandlerMethodArgumentResolver {

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return parameter.hasParameterAnnotation(CurrentUser.class)
            && parameter.getParameterType().equals(UserDetails.class);
    }

    @Override
    public Object resolveArgument(MethodParameter parameter, ...) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        return auth.getPrincipal();
    }
}

// Controller에서 사용
@GetMapping("/me")
public UserResponse getCurrentUser(@CurrentUser UserDetails userDetails) {
    return userService.findByEmail(userDetails.getUsername());
}
```

## 운영 팁

### 보안 체크리스트

| 항목 | 설명 | 적용 |
|------|------|------|
| **비밀번호 해싱** | BCrypt 사용 (cost factor 10 이상) | ✅ 필수 |
| **JWT 시크릿** | 환경변수로 관리, 최소 256비트 | ✅ 필수 |
| **Token 만료** | Access 15~30분, Refresh 7~14일 | ✅ 필수 |
| **HTTPS** | 프로덕션에서 반드시 사용 | ✅ 필수 |
| **CORS** | 허용 도메인을 명시적으로 지정 | ✅ 필수 |
| **Rate Limiting** | 로그인 시도 제한 | ⭐ 권장 |
| **Refresh Token Rotation** | 사용된 Refresh Token 폐기 | ⭐ 권장 |
| **IP 기반 제한** | 관리자 API 접근 IP 제한 | 선택 |

### 흔한 실수

| 실수 | 결과 | 해결 |
|------|------|------|
| CSRF 비활성화 없이 REST API 구축 | POST/PUT/DELETE 요청 403 | `csrf.disable()` (REST API 한정) |
| SecurityContext를 비동기에서 접근 | null 반환 | `SecurityContextHolder.setStrategyName(MODE_INHERITABLETHREADLOCAL)` |
| 패스워드 평문 저장 | 데이터 유출 시 전체 계정 노출 | BCryptPasswordEncoder 필수 사용 |
| JWT 시크릿을 코드에 하드코딩 | 소스 유출 시 토큰 위조 가능 | 환경변수 또는 Vault 사용 |

## 참고

- [Spring Security 공식 문서](https://docs.spring.io/spring-security/reference/)
- [Spring Security Architecture](https://spring.io/guides/topicals/spring-security-architecture)
- [JJWT GitHub](https://github.com/jwtk/jjwt)
- [OAuth 2.0 개요](../../Security/OAuth.md)
