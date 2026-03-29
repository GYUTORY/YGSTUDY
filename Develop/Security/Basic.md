---
title: 보안 기초 개념
tags: [security, CIA-triad, authentication, authorization, encryption, hash, defense-in-depth, input-validation, error-handling, logging]
updated: 2026-03-29
---

# 보안 기초 개념

## CIA 트라이어드

보안을 이야기할 때 가장 먼저 나오는 개념이다. 기밀성(Confidentiality), 무결성(Integrity), 가용성(Availability) 세 가지로 구성된다.

### 기밀성 (Confidentiality)

허가받지 않은 사람이 데이터를 볼 수 없어야 한다. DB에 저장된 비밀번호가 평문이면 기밀성이 깨진 거다. HTTPS 없이 로그인 요청을 보내면 중간에서 패킷을 가로채 비밀번호를 볼 수 있다.

실무에서 기밀성이 깨지는 경우:

- 로그에 사용자 개인정보가 그대로 찍힌다
- API 응답에 다른 사용자의 데이터가 포함된다
- 에러 메시지에 DB 스키마나 내부 경로가 노출된다
- `.env` 파일이 Git에 올라간다

### 무결성 (Integrity)

데이터가 중간에 변조되지 않았음을 보장한다. 은행 송금 요청에서 금액이 바뀌면 무결성이 깨진 거다.

무결성을 확인하는 방법은 해시 비교다. 파일을 다운로드한 뒤 SHA-256 체크섬을 비교하는 게 대표적이다. JWT의 서명도 토큰 내용이 변조되지 않았는지 검증하는 용도다.

```bash
# 파일 무결성 검증
sha256sum downloaded-file.tar.gz
# 출력된 해시를 공식 사이트의 체크섬과 비교
```

### 가용성 (Availability)

서비스가 필요할 때 정상 동작해야 한다. 아무리 기밀성과 무결성을 잘 지켜도, 서버가 다운되면 의미가 없다.

DDoS 공격이 가용성을 노리는 대표적인 사례다. 실무에서는 장애 대응과도 연결되는데, 단일 서버 구성이면 그 서버가 죽는 순간 가용성이 0이 된다. 이중화, 로드밸런싱, 자동 복구 같은 인프라 설계가 가용성과 직결된다.

세 가지가 항상 동시에 만족되진 않는다. 기밀성을 극단적으로 높이면 접근 절차가 복잡해져 가용성이 떨어진다. 보안 설계는 이 세 가지의 균형을 잡는 일이다.

---

## 인증과 인가

혼동하기 쉬운 두 개념이다.

### 인증 (Authentication)

"너 누구야?"에 대한 답이다. 사용자가 본인이 맞는지 확인하는 과정이다.

- **지식 기반**: 비밀번호, PIN
- **소유 기반**: OTP 디바이스, 인증서, SMS 코드
- **생체 기반**: 지문, 얼굴 인식

현업에서 비밀번호만으로 인증하는 시스템은 점점 줄고 있다. 2단계 인증(MFA)이 거의 표준이 되었다.

### 인가 (Authorization)

"이 사람이 이 작업을 할 수 있어?"에 대한 답이다. 인증이 끝난 뒤에 일어나는 과정이다.

일반 사용자가 관리자 페이지에 접근하면 안 된다. API에서 다른 사용자의 리소스를 수정할 수 없어야 한다.

```java
// 인증은 통과했지만, 인가 검사가 빠진 코드 — 취약점이다
@GetMapping("/api/users/{userId}/profile")
public UserProfile getProfile(@PathVariable Long userId) {
    // 현재 로그인한 사용자가 이 userId의 프로필을 볼 권한이 있는지 검사하지 않음
    return userService.findById(userId);  // IDOR 취약점
}

// 인가 검사를 추가한 코드
@GetMapping("/api/users/{userId}/profile")
public UserProfile getProfile(@PathVariable Long userId, Authentication auth) {
    Long currentUserId = ((UserPrincipal) auth.getPrincipal()).getId();
    if (!currentUserId.equals(userId) && !auth.getAuthorities().contains("ROLE_ADMIN")) {
        throw new AccessDeniedException("권한 없음");
    }
    return userService.findById(userId);
}
```

인증과 인가는 순서가 있다. 인증 → 인가 순으로 처리된다. 인증되지 않은 요청은 인가 검사 자체가 의미 없다.

---

## 대칭키 암호화 vs 비대칭키 암호화

### 대칭키 암호화

암호화와 복호화에 같은 키를 쓴다. AES가 대표적이다.

속도가 빠르다. 대량 데이터 암호화에 적합하다. 문제는 키 전달이다. 상대방에게 키를 어떻게 안전하게 전달할 것인가? 키가 탈취되면 모든 데이터가 노출된다.

```
평문 --[키 A로 암호화]--> 암호문 --[키 A로 복호화]--> 평문
```

대칭키 알고리즘 비교:

| 알고리즘 | 키 길이 | 상태 |
|----------|---------|------|
| DES | 56bit | 사용 금지. 이미 깨졌다 |
| 3DES | 168bit | 레거시. 신규 시스템에 쓰지 않는다 |
| AES-128 | 128bit | 현재 표준 |
| AES-256 | 256bit | 높은 보안 등급에 사용 |

### 비대칭키 암호화

공개키와 개인키 두 개를 쓴다. RSA, ECDSA가 대표적이다.

공개키로 암호화하면 개인키로만 복호화할 수 있다. 키 교환 문제가 해결된다. 공개키는 말 그대로 공개해도 된다. 대신 대칭키보다 느리다.

```
평문 --[공개키로 암호화]--> 암호문 --[개인키로 복호화]--> 평문
```

HTTPS가 두 방식을 조합한 대표 사례다. TLS 핸드셰이크에서 비대칭키로 대칭키를 안전하게 교환한 뒤, 실제 데이터 전송은 대칭키로 한다. 비대칭키의 안전한 키 교환 + 대칭키의 빠른 속도를 결합한 구조다.

---

## 해시와 암호화의 차이

실무에서 이 둘을 혼동하면 보안 사고가 난다.

### 해시 (Hash)

단방향이다. 원본으로 되돌릴 수 없다. 같은 입력은 항상 같은 출력을 만든다. 출력 길이가 고정되어 있다.

**용도**: 비밀번호 저장, 데이터 무결성 검증, 디지털 서명

```python
import hashlib

# SHA-256 해시
data = "hello"
hash_value = hashlib.sha256(data.encode()).hexdigest()
# 항상 같은 값: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```

### 암호화 (Encryption)

양방향이다. 키가 있으면 원본으로 복원할 수 있다.

**용도**: 데이터 전송, 저장 데이터 보호, 통신 보안

비밀번호를 암호화해서 저장하면 안 된다. 암호화는 복호화가 가능하니까, 키가 유출되면 모든 비밀번호가 노출된다. 비밀번호는 반드시 해시로 저장한다.

반대로, 사용자 이메일이나 전화번호처럼 원본이 필요한 데이터는 해시가 아니라 암호화로 저장한다. 해시하면 원본을 알 수 없으니 서비스에서 사용할 수가 없다.

| 구분 | 해시 | 암호화 |
|------|------|--------|
| 방향 | 단방향 | 양방향 |
| 키 필요 여부 | 불필요 | 필요 |
| 비밀번호 저장 | 적합 | 부적합 |
| 데이터 전송 | 부적합 | 적합 |

### 비밀번호 해시 시 주의할 점

단순 해시만으로는 부족하다. Rainbow Table 공격으로 해시값에서 원본을 찾아낼 수 있다.

**솔트(Salt)**: 해시 전에 랜덤 값을 붙인다. 같은 비밀번호라도 솔트가 다르면 해시 결과가 달라진다. Rainbow Table이 무력화된다.

**반복(Iteration)**: 해시 함수를 수만 번 반복 적용한다. 공격자가 무차별 대입(brute force)을 시도할 때 시간 비용이 크게 증가한다.

bcrypt, Argon2, PBKDF2 같은 비밀번호 전용 해시 함수는 솔트와 반복을 내장하고 있다. SHA-256을 직접 돌리지 말고 이런 전용 함수를 써야 한다.

```javascript
const bcrypt = require('bcrypt');

// 비밀번호 해시 — saltRounds가 반복 횟수를 결정한다
const saltRounds = 12;
const hashedPassword = await bcrypt.hash('userPassword', saltRounds);

// 비밀번호 검증
const isMatch = await bcrypt.compare('userPassword', hashedPassword);
```

---

## 최소 권한 원칙 (Principle of Least Privilege)

작업에 필요한 최소한의 권한만 부여한다. 이게 전부다.

DB 접속 계정을 예로 들면, 애플리케이션 서버에서 읽기만 하는 테이블에 대해 SELECT 권한만 주면 된다. `GRANT ALL PRIVILEGES`를 습관적으로 쓰면 SQL 인젝션이 발생했을 때 DROP TABLE까지 가능해진다.

실무에서 자주 보이는 위반 사례:

- 모든 마이크로서비스가 같은 DB 계정을 공유한다
- AWS IAM 정책에 `"Action": "*"`, `"Resource": "*"`를 넣는다
- 배포 스크립트에 root 권한으로 실행한다
- API 토큰에 전체 권한을 부여한다

```sql
-- 나쁜 예: 전체 권한
GRANT ALL PRIVILEGES ON mydb.* TO 'app_user'@'%';

-- 좋은 예: 필요한 권한만
GRANT SELECT, INSERT ON mydb.orders TO 'order_service'@'10.0.0.%';
GRANT SELECT ON mydb.products TO 'order_service'@'10.0.0.%';
```

클라우드 환경에서 IAM 정책도 마찬가지다. 서비스가 S3에서 읽기만 하면 `s3:GetObject`만 허용한다. 처음엔 귀찮지만, 보안 사고가 터졌을 때 피해 범위가 확연히 줄어든다.

---

## 심층 방어 (Defense in Depth)

한 겹의 방어만으로는 부족하다. 여러 계층에 걸쳐 보안 장치를 두는 개념이다.

웹 서비스 기준으로 계층별 방어 구조를 보면:

```
[사용자 요청]
    ↓
[1. 네트워크 계층] — 방화벽, WAF, DDoS 방어
    ↓
[2. 전송 계층] — TLS/HTTPS
    ↓
[3. 애플리케이션 계층] — 입력값 검증, 인증/인가
    ↓
[4. 데이터 계층] — 암호화 저장, 접근 제어
    ↓
[5. 모니터링] — 로그, 이상 탐지, 알림
```

WAF가 SQL 인젝션을 막더라도, 애플리케이션에서 파라미터 바인딩을 하지 않으면 WAF 우회 시 바로 뚫린다. 반대로 애플리케이션에서 완벽히 방어해도, 네트워크 계층 보안이 없으면 DDoS로 서비스가 죽는다.

각 계층이 독립적으로 방어하고, 한 계층이 뚫려도 다음 계층에서 막는 구조를 만든다.

Spring 기반 웹 애플리케이션에서 심층 방어가 적용된 예:

```java
// 1. 인증 필터 (Spring Security)
@Configuration
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse()))
            .headers(headers -> headers
                .contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'"))
                .frameOptions(frame -> frame.deny())
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/**").authenticated()
            );
        return http.build();
    }
}

// 2. 입력값 검증 (Controller 계층)
@PostMapping("/api/users")
public ResponseEntity<?> createUser(@Valid @RequestBody CreateUserRequest request) {
    // @Valid로 Bean Validation 수행 — 길이, 형식 제한
    return ResponseEntity.ok(userService.create(request));
}

// 3. SQL 인젝션 방어 (Repository 계층)
@Query("SELECT u FROM User u WHERE u.email = :email")
Optional<User> findByEmail(@Param("email") String email);
// 파라미터 바인딩 사용. 문자열 연결로 쿼리를 만들지 않는다.
```

---

## 입력값 검증 (Input Validation)

외부에서 들어오는 모든 데이터는 오염되어 있다고 가정한다. 사용자 입력, API 요청 파라미터, HTTP 헤더, 쿠키, 파일 업로드 전부 해당한다. 입력값 검증은 SQL 인젝션, XSS, 커맨드 인젝션 같은 인젝션 계열 공격의 첫 번째 방어선이다.

### 화이트리스트 vs 블랙리스트

블랙리스트는 "이건 안 돼"를 정의하는 방식이다. `<script>` 태그를 차단하거나, `DROP TABLE`을 필터링하는 식이다. 문제는 우회 방법이 끝없이 나온다는 거다. 대소문자 혼합(`<ScRiPt>`), 인코딩 변환(`%3Cscript%3E`), 널바이트 삽입 등으로 필터를 피할 수 있다.

화이트리스트는 "이것만 돼"를 정의한다. 나이 필드에 양의 정수만 허용, 이메일 필드에 이메일 형식만 허용하는 식이다. 허용 목록에 없으면 전부 거부한다.

```java
// 블랙리스트 — 우회 가능성이 항상 남아 있다
public boolean isUnsafe(String input) {
    return input.contains("<script>") || input.contains("DROP TABLE");
    // <SCRIPT>, <scr\0ipt> 등으로 우회 가능
}

// 화이트리스트 — 허용 범위를 명시한다
public boolean isValidAge(String input) {
    return input.matches("^[1-9][0-9]?$|^1[0-4][0-9]$|^150$");
    // 1~150 범위의 숫자만 통과
}

public boolean isValidUsername(String input) {
    return input.matches("^[a-zA-Z0-9_]{3,20}$");
    // 영문, 숫자, 밑줄만 허용. 3~20자 제한
}
```

원칙은 화이트리스트를 우선 적용하는 거다. 화이트리스트로 처리할 수 없는 자유 형식 텍스트(게시글 본문 등)만 블랙리스트와 이스케이핑을 조합해서 처리한다.

### 서버 사이드 검증이 필수인 이유

프론트엔드 검증은 사용자 경험을 위한 것이지, 보안을 위한 게 아니다. 브라우저의 JavaScript 검증은 개발자 도구에서 끌 수 있고, API를 직접 호출하면 프론트엔드를 아예 건너뛴다. curl이나 Postman으로 요청을 보내면 클라이언트 검증은 존재하지 않는 거나 마찬가지다.

```bash
# 프론트엔드 검증을 완전히 무시하고 직접 요청
curl -X POST https://example.com/api/users \
  -H "Content-Type: application/json" \
  -d '{"age": -1, "name": "<script>alert(1)</script>"}'
```

서버에서 검증하지 않으면 이 요청이 그대로 처리된다. 프론트엔드 검증과 서버 검증을 둘 다 해야 한다. 프론트엔드는 UX용, 서버는 보안용이다.

### 검증 위치 — 경계면에서 검증한다

입력값 검증은 시스템의 경계면(boundary)에서 수행한다. 외부 데이터가 시스템 내부로 진입하는 지점이다.

- **Controller 계층**: HTTP 요청 파라미터, 요청 본문, 헤더 값
- **메시지 컨슈머**: 큐에서 꺼낸 메시지
- **파일 처리**: 업로드된 파일의 타입, 크기, 내용
- **외부 API 응답**: 다른 서비스에서 받은 데이터

경계면에서 검증을 마치면, 시스템 내부에서는 데이터가 이미 검증된 상태로 흐른다. Service 계층에서 같은 검증을 반복할 필요가 없다. 다만 Service 계층에서는 비즈니스 규칙 검증(잔액이 충분한지, 재고가 있는지)을 별도로 수행한다.

```java
// Controller — 경계면에서 형식 검증
@PostMapping("/api/orders")
public ResponseEntity<?> createOrder(@Valid @RequestBody OrderRequest request) {
    // @Valid가 형식 검증을 처리한다 (null, 범위, 패턴 등)
    return ResponseEntity.ok(orderService.create(request));
}

public class OrderRequest {
    @NotNull
    @Min(1)
    private Long productId;

    @NotNull
    @Min(1) @Max(100)
    private Integer quantity;

    @NotBlank
    @Size(max = 200)
    @Pattern(regexp = "^[가-힣a-zA-Z0-9\\s,.-]+$")
    private String shippingAddress;
}

// Service — 비즈니스 규칙 검증 (형식은 이미 검증됨)
public Order create(OrderRequest request) {
    Product product = productRepository.findById(request.getProductId())
        .orElseThrow(() -> new NotFoundException("상품 없음"));
    if (product.getStock() < request.getQuantity()) {
        throw new BusinessException("재고 부족");
    }
    // ...
}
```

---

## 에러 메시지 보안

에러 메시지는 공격자에게 시스템 내부 정보를 넘겨주는 통로가 된다. 스택 트레이스에 DB 테이블명, 내부 클래스 경로, 프레임워크 버전이 그대로 들어 있다. 공격자는 이 정보로 공격 벡터를 좁힌다.

### 스택 트레이스 노출 금지

Spring Boot의 기본 에러 응답은 개발 모드에서 스택 트레이스를 포함한다. 운영 환경에서 이게 그대로 나가면 문제다.

```json
// 절대 이런 응답이 사용자에게 가면 안 된다
{
  "timestamp": "2026-03-29T10:15:30",
  "status": 500,
  "error": "Internal Server Error",
  "trace": "org.postgresql.util.PSQLException: ERROR: relation \"users\" does not exist\n\tat org.postgresql.core.v3.QueryExecutorImpl...",
  "path": "/api/users"
}
```

이 응답에서 공격자가 알 수 있는 것: PostgreSQL 사용, `users` 테이블 존재, Spring Boot 프레임워크 사용, 내부 패키지 구조. 이 정보만으로 PostgreSQL 특화 SQL 인젝션을 시도할 수 있다.

### 사용자용 에러와 개발자용 에러를 분리한다

사용자에게는 일반적인 메시지만 보내고, 상세 정보는 서버 로그에 남긴다. 에러 응답에 추적용 ID를 포함시키면, 사용자가 문의할 때 해당 로그를 바로 찾을 수 있다.

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleException(Exception ex, HttpServletRequest request) {
        String errorId = UUID.randomUUID().toString().substring(0, 8);

        // 서버 로그에는 전체 정보를 남긴다
        log.error("[{}] {} {} - {}", errorId, request.getMethod(),
                  request.getRequestURI(), ex.getMessage(), ex);

        // 사용자에게는 최소한의 정보만 응답한다
        ErrorResponse response = new ErrorResponse(
            errorId,
            "요청을 처리하는 중 오류가 발생했습니다."
        );
        return ResponseEntity.status(500).body(response);
    }

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        // 404도 구체적인 이유를 노출하지 않는다
        // "users 테이블에서 id=123을 찾을 수 없음" 대신 "리소스를 찾을 수 없습니다"
        ErrorResponse response = new ErrorResponse(null, "리소스를 찾을 수 없습니다.");
        return ResponseEntity.status(404).body(response);
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponse> handleAccessDenied(AccessDeniedException ex) {
        // "ADMIN 권한이 필요합니다" 같은 메시지도 피한다
        // 어떤 권한이 필요한지 알려주면 공격자가 권한 상승을 시도할 근거가 된다
        ErrorResponse response = new ErrorResponse(null, "접근 권한이 없습니다.");
        return ResponseEntity.status(403).body(response);
    }
}
```

인증 관련 에러에서 주의할 점이 하나 더 있다. "비밀번호가 틀렸습니다"와 "존재하지 않는 계정입니다"를 구분해서 응답하면, 공격자가 유효한 계정 목록을 수집할 수 있다. 로그인 실패 시에는 "이메일 또는 비밀번호가 일치하지 않습니다"처럼 어떤 쪽이 틀렸는지 구분하지 않는다.

---

## 보안 관점의 로깅

로그는 보안 사고 대응의 핵심 자료다. 그런데 로그 자체가 보안 문제를 일으키는 경우가 많다.

### 민감정보 마스킹

로그에 비밀번호, 카드 번호, 주민등록번호가 찍히면 로그 접근 권한을 가진 사람 전원이 그 정보를 볼 수 있다. 로그 수집 시스템(ELK, CloudWatch 등)에 저장되면 삭제도 쉽지 않다.

마스킹 대상:

- 비밀번호, 인증 토큰, API 키
- 카드 번호, CVV, 계좌 번호
- 주민등록번호, 여권 번호 같은 개인 식별 정보
- 세션 ID (탈취하면 세션 하이재킹이 가능하다)

```java
// 나쁜 예 — 요청 본문을 통째로 로그에 남긴다
log.info("회원가입 요청: {}", objectMapper.writeValueAsString(request));
// 출력: 회원가입 요청: {"email":"user@test.com","password":"mySecret123","name":"홍길동"}

// 마스킹 적용
public class LogSanitizer {
    private static final Pattern PASSWORD_PATTERN =
        Pattern.compile("(\"password\"\\s*:\\s*\")([^\"]+)(\")");
    private static final Pattern CARD_PATTERN =
        Pattern.compile("(\\d{4})(\\d{4,8})(\\d{4})");

    public static String sanitize(String logMessage) {
        String result = PASSWORD_PATTERN.matcher(logMessage)
            .replaceAll("$1****$3");
        result = CARD_PATTERN.matcher(result)
            .replaceAll("$1****$3");
        return result;
    }
}

// 사용
log.info("회원가입 요청: {}", LogSanitizer.sanitize(requestBody));
// 출력: 회원가입 요청: {"email":"user@test.com","password":"****","name":"홍길동"}
```

로그 레벨도 중요하다. DEBUG 레벨에서는 상세 정보가 나오기 쉬운데, 운영 환경에서 DEBUG를 켜놓으면 민감정보가 대량으로 로그에 쌓일 수 있다. 운영 환경의 기본 로그 레벨은 INFO 이상으로 설정한다.

### 로그 인젝션 방어

로그 인젝션은 사용자 입력이 로그에 그대로 들어갈 때 발생한다. 공격자가 입력값에 개행 문자(`\n`)를 넣으면 로그에 가짜 항목을 삽입할 수 있다.

```
// 정상 로그
2026-03-29 10:15:30 INFO  로그인 시도: user=admin

// 공격자가 username에 "admin\n2026-03-29 10:15:31 INFO  로그인 성공: user=admin" 을 입력하면
2026-03-29 10:15:30 INFO  로그인 시도: user=admin
2026-03-29 10:15:31 INFO  로그인 성공: user=admin  ← 가짜 로그

// 로그 분석 시 실제로 로그인에 성공한 것처럼 보인다
```

방어 방법은 단순하다. 로그에 넣기 전에 개행 문자와 제어 문자를 제거하거나 치환한다.

```java
public static String sanitizeForLog(String input) {
    if (input == null) return "null";
    return input.replaceAll("[\\r\\n\\t]", "_")
                .replaceAll("[^\\x20-\\x7E가-힣]", "");  // 제어 문자 제거
}

// 사용
log.info("로그인 시도: user={}", sanitizeForLog(username));
```

Logback이나 Log4j2의 최신 버전은 패턴 레이아웃에서 개행 문자를 자동으로 처리하는 옵션이 있다. 프레임워크 설정을 먼저 확인하고, 부족한 부분만 직접 처리한다.

보안 이벤트(로그인 실패, 권한 없는 접근 시도, 입력값 검증 실패)는 별도의 보안 로그로 분리해서 남기면 모니터링과 감사 추적이 수월하다. 같은 IP에서 로그인 실패가 분당 50회 이상 발생하면 알림을 보내는 식으로 활용할 수 있다.

---

## 해시 알고리즘 비교

| 알고리즘 | 출력 길이 | 용도 | 상태 |
|----------|-----------|------|------|
| MD5 | 128bit | 파일 체크섬 (보안 용도 외) | 충돌 발견됨. 보안 용도 사용 금지 |
| SHA-1 | 160bit | Git 내부 해시 (레거시) | 충돌 발견됨. 신규 사용 금지 |
| SHA-256 | 256bit | 데이터 무결성, 서명 | 현재 표준 |
| bcrypt | 184bit | 비밀번호 해시 전용 | 권장 |
| Argon2 | 가변 | 비밀번호 해시 전용 | 최신 권장. 2015 Password Hashing Competition 우승 |

MD5나 SHA-1을 비밀번호 해시에 쓰는 레거시 시스템이 아직 있다. 이런 시스템을 만나면 bcrypt나 Argon2로 마이그레이션 계획을 잡아야 한다.
