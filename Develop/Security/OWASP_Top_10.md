---
title: OWASP Top 10
tags: [security, owasp, access-control, injection, authentication, misconfiguration, vulnerable-components, integrity, logging]
updated: 2026-04-07
---

# OWASP Top 10 (2021)

OWASP Top 10은 웹 애플리케이션에서 가장 빈번하게 발생하는 보안 취약점 10가지를 정리한 목록이다. 2021년 기준으로 마지막 업데이트되었고, 2017년 대비 순위와 항목이 상당히 바뀌었다.

실무에서 보안 감사나 모의해킹 리포트를 받으면 대부분 이 Top 10 항목 중 하나에 해당한다. 각 항목별로 실제로 어떤 식으로 터지는지, 어떻게 막아야 하는지를 정리한다.

---

## A01: Broken Access Control

2017년에 5위였다가 2021년에 1위로 올라왔다. 그만큼 실무에서 가장 많이 터지는 취약점이다.

권한 검증이 빠져 있거나 불완전해서, 인가되지 않은 사용자가 다른 사용자의 데이터에 접근하거나 관리자 기능을 호출하는 문제다.

### IDOR (Insecure Direct Object Reference)

URL이나 파라미터에 있는 ID 값을 바꿔서 다른 사용자의 리소스에 접근하는 공격이다. 가장 흔하고, 가장 놓치기 쉽다.

```java
// 취약한 코드 - 주문 조회 API
@GetMapping("/orders/{orderId}")
public Order getOrder(@PathVariable Long orderId) {
    // orderId만 검증하고, 이 주문이 현재 사용자의 것인지 확인하지 않는다
    return orderRepository.findById(orderId)
            .orElseThrow(() -> new NotFoundException("Order not found"));
}

// 수정된 코드
@GetMapping("/orders/{orderId}")
public Order getOrder(@PathVariable Long orderId, @AuthenticationPrincipal User user) {
    Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new NotFoundException("Order not found"));

    if (!order.getUserId().equals(user.getId())) {
        throw new ForbiddenException("Access denied");
    }
    return order;
}
```

실제 프로젝트에서 겪는 상황: API가 수십 개 되면 하나둘 빠진다. 특히 관리자 페이지에서 사용하던 내부 API가 인증 필터를 우회하는 경로로 노출되는 경우가 있다.

### 수평적/수직적 권한 상승

수평적 권한 상승은 같은 권한 레벨의 다른 사용자 데이터에 접근하는 것이고, 수직적 권한 상승은 관리자 같은 상위 권한을 획득하는 것이다.

```java
// 수직적 권한 상승 - 취약한 관리자 엔드포인트
@PostMapping("/admin/users/{userId}/role")
public void changeRole(@PathVariable Long userId, @RequestBody RoleRequest request) {
    // @PreAuthorize 같은 권한 검증이 없다
    // 일반 사용자가 이 URL을 알면 바로 호출 가능
    userService.changeRole(userId, request.getRole());
}

// 수정된 코드
@PreAuthorize("hasRole('ADMIN')")
@PostMapping("/admin/users/{userId}/role")
public void changeRole(@PathVariable Long userId, @RequestBody RoleRequest request) {
    userService.changeRole(userId, request.getRole());
}
```

URL 패턴으로 `/admin/**` 전체에 권한을 거는 방식은 새 엔드포인트 추가 시 빠뜨리는 경우가 있다. 메서드 레벨 어노테이션을 기본으로 쓰고, URL 패턴은 2차 방어선으로 두는 게 낫다.

### 경로 탐색 (Path Traversal)

파일 다운로드 기능에서 경로를 조작해 시스템 파일에 접근하는 공격이다.

```java
// 취약한 파일 다운로드
@GetMapping("/download")
public ResponseEntity<Resource> download(@RequestParam String filename) {
    // ../../../etc/passwd 같은 입력이 들어올 수 있다
    Path filePath = Paths.get("/uploads/" + filename);
    Resource resource = new FileSystemResource(filePath.toFile());
    return ResponseEntity.ok().body(resource);
}

// 수정된 코드
@GetMapping("/download")
public ResponseEntity<Resource> download(@RequestParam String filename) {
    Path basePath = Paths.get("/uploads").toAbsolutePath().normalize();
    Path filePath = basePath.resolve(filename).normalize();

    // 기준 디렉토리를 벗어나는지 검증
    if (!filePath.startsWith(basePath)) {
        throw new BadRequestException("Invalid file path");
    }

    Resource resource = new FileSystemResource(filePath.toFile());
    return ResponseEntity.ok().body(resource);
}
```

`normalize()`를 반드시 호출해야 한다. `../` 같은 상대 경로를 정규화하지 않으면 `startsWith` 검증을 우회할 수 있다.

### 대응 방법

- 기본 정책은 "거부(deny)"로 설정하고, 필요한 것만 열어준다
- 모든 API에 소유권 검증 로직을 넣는다. 리포지토리 쿼리에 userId 조건을 포함시키는 것이 가장 확실하다
- JWT 토큰의 클레임만 믿지 말고, 서버 측에서 권한을 재확인한다
- CORS 설정을 느슨하게 열어두면 프론트엔드에서의 접근 제어 의미가 없어진다

---

## A02: Cryptographic Failures

이전에는 "Sensitive Data Exposure"라는 이름이었는데, 2021년에 원인 중심으로 이름이 바뀌었다. 암호화를 안 하거나, 약한 알고리즘을 쓰거나, 키 관리를 잘못하는 문제다.

### 흔히 발생하는 실수

```java
// 1. MD5나 SHA-1으로 비밀번호 해싱 - 절대 하면 안 된다
String hashedPassword = DigestUtils.md5Hex(password); // 취약

// bcrypt나 argon2를 사용해야 한다
String hashedPassword = BCrypt.hashpw(password, BCrypt.gensalt(12));
```

```yaml
# 2. application.yml에 평문 비밀번호
spring:
  datasource:
    password: mydbpassword123  # 이 상태로 Git에 올라가는 경우가 많다

# 환경변수나 Vault 같은 시크릿 관리 도구를 써야 한다
spring:
  datasource:
    password: ${DB_PASSWORD}
```

```java
// 3. HTTP로 민감 데이터 전송
// 내부 서비스 간 통신이라도 mTLS를 적용하는 것이 맞다
// 특히 쿠버네티스 클러스터 내부 트래픽도 암호화해야 한다
```

### 주의할 점

- AES-ECB 모드는 동일 평문이 동일 암호문을 만들어서 패턴이 드러난다. AES-GCM을 쓴다
- 암호화 키를 소스코드에 하드코딩하면 Git 히스토리에 남는다. 한 번이라도 커밋했으면 키를 교체해야 한다
- TLS 1.0, 1.1은 이미 폐기되었다. TLS 1.2 이상만 허용한다
- 로그에 민감 데이터(카드번호, 주민번호)가 찍히는 경우가 많다. 로깅 필터를 반드시 적용한다

---

## A03: Injection

SQL Injection, XSS, Command Injection 등이 이 항목에 포함된다. 사용자 입력이 서버 측 명령어나 쿼리의 일부로 해석되는 문제다.

SQL Injection과 XSS는 별도 문서에서 상세하게 다루고 있으므로 여기서는 핵심만 정리한다.

**SQL Injection** - 파라미터 바인딩(PreparedStatement, ORM의 쿼리 파라미터)을 사용하면 근본적으로 차단된다. 동적 쿼리 빌딩이 필요한 경우에도 문자열 연결이 아닌 Criteria API나 QueryDSL을 사용한다. → [SQL 인젝션 상세](../Security/Basic.md)

**XSS** - 서버에서 렌더링하는 경우 출력 시점에 이스케이핑 처리가 핵심이다. React 같은 프레임워크는 기본적으로 이스케이핑을 해주지만, `dangerouslySetInnerHTML`이나 `v-html` 사용 시 취약해진다. → [XSS 상세](../Security/XSS.md)

### Command Injection

간과하기 쉬운 영역이다. 파일 변환, 이미지 리사이징 등에서 시스템 명령어를 호출할 때 발생한다.

```java
// 취약한 코드 - 이미지 리사이징
@PostMapping("/resize")
public void resizeImage(@RequestParam String filename, @RequestParam int width) {
    // filename에 "; rm -rf /" 같은 입력이 들어올 수 있다
    Runtime.getRuntime().exec("convert " + filename + " -resize " + width + " output.jpg");
}

// 수정된 코드 - ProcessBuilder로 인자를 분리
@PostMapping("/resize")
public void resizeImage(@RequestParam String filename, @RequestParam int width) {
    // 파일명 검증
    if (!filename.matches("[a-zA-Z0-9._-]+")) {
        throw new BadRequestException("Invalid filename");
    }

    ProcessBuilder pb = new ProcessBuilder(
        "convert", filename, "-resize", String.valueOf(width), "output.jpg"
    );
    pb.directory(new File("/uploads"));
    pb.start();
}
```

가능하면 시스템 명령어를 호출하지 않고 라이브러리를 사용한다. Java의 경우 ImageIO나 Thumbnailator 같은 라이브러리로 대체할 수 있다.

---

## A04: Insecure Design

2021년에 새로 추가된 항목이다. 코드 레벨의 버그가 아니라, 설계 단계에서의 보안 결함을 다룬다. 코드를 아무리 잘 짜도 설계 자체가 잘못되면 취약하다.

### 비즈니스 로직 결함

```java
// 할인 쿠폰 중복 적용 - 설계 단계에서 막아야 하는 문제
@PostMapping("/orders")
public Order createOrder(@RequestBody OrderRequest request) {
    double totalDiscount = 0;
    for (String couponCode : request.getCouponCodes()) {
        Coupon coupon = couponService.validate(couponCode);
        totalDiscount += coupon.getDiscountRate();
    }
    // totalDiscount가 100%를 넘을 수 있다
    double finalPrice = request.getTotalPrice() * (1 - totalDiscount);
    // finalPrice가 음수가 될 수 있다 → 환불 공격
    return orderService.create(request, finalPrice);
}

// 수정된 코드
@PostMapping("/orders")
public Order createOrder(@RequestBody OrderRequest request) {
    double totalDiscount = 0;
    Set<String> usedCouponTypes = new HashSet<>();

    for (String couponCode : request.getCouponCodes()) {
        Coupon coupon = couponService.validate(couponCode);

        // 같은 타입의 쿠폰 중복 적용 차단
        if (!usedCouponTypes.add(coupon.getType())) {
            throw new BadRequestException("Same type coupon already applied");
        }
        totalDiscount += coupon.getDiscountRate();
    }

    // 최대 할인율 제한
    totalDiscount = Math.min(totalDiscount, 0.8); // 최대 80%
    double finalPrice = Math.max(request.getTotalPrice() * (1 - totalDiscount), 0);
    return orderService.create(request, finalPrice);
}
```

### 위협 모델링

설계 단계에서 "이 기능이 악용되면 어떻게 되는가?"를 미리 따져보는 과정이다. 거창한 방법론보다는, 기능 설계 시 다음을 항상 검토하는 것만으로도 많은 문제를 예방한다.

기능을 설계할 때 아래 질문을 던져본다:

1. **이 API를 반복 호출하면?** - Rate Limiting 없이 인증 코드 확인 API를 열어두면 브루트포스가 가능하다
2. **순서를 바꿔서 호출하면?** - 결제 완료 전에 상품 발송 API를 직접 호출할 수 있는지 확인한다
3. **파라미터를 변조하면?** - 클라이언트가 보내는 가격 정보를 서버에서 그대로 사용하면 안 된다. 서버에서 가격을 다시 조회한다
4. **동시에 호출하면?** - 포인트 차감, 재고 감소 같은 로직에서 Race Condition이 발생할 수 있다

```java
// Race Condition 예시 - 포인트 중복 사용
// 동시에 두 요청이 들어오면 잔액 확인 후 차감까지 사이에 다른 요청이 끼어든다
@Transactional
public void usePoints(Long userId, int amount) {
    User user = userRepository.findById(userId).get();
    if (user.getPoints() >= amount) {
        user.setPoints(user.getPoints() - amount);  // Lost Update 발생 가능
        userRepository.save(user);
    }
}

// 비관적 락 적용
@Transactional
public void usePoints(Long userId, int amount) {
    User user = userRepository.findByIdForUpdate(userId); // SELECT ... FOR UPDATE
    if (user.getPoints() >= amount) {
        user.setPoints(user.getPoints() - amount);
        userRepository.save(user);
    }
}
```

---

## A05: Security Misconfiguration

디폴트 설정을 그대로 쓰거나, 불필요한 기능이 켜져 있거나, 에러 메시지에 내부 정보가 노출되는 문제다. 설정 실수는 코드 리뷰에서 잡히지 않는 경우가 많아서 별도로 점검해야 한다.

### 디폴트 설정 문제

```yaml
# Spring Boot - 운영 환경에서 확인해야 할 설정들

# Actuator 엔드포인트가 전부 열려 있으면 내부 정보가 노출된다
management:
  endpoints:
    web:
      exposure:
        include: health,info  # 필요한 것만 열어둔다. "*"은 절대 안 된다
  endpoint:
    health:
      show-details: never  # 운영에서는 상세 정보를 숨긴다

# H2 Console - 개발용 설정이 운영에 올라가는 경우가 있다
spring:
  h2:
    console:
      enabled: false  # 운영에서는 반드시 꺼야 한다
```

```nginx
# Nginx - 서버 버전 노출 차단
server_tokens off;

# 디렉토리 리스팅 비활성화
autoindex off;
```

### 에러 메시지 노출

```java
// 취약한 에러 처리 - 스택트레이스가 클라이언트에 노출된다
@ExceptionHandler(Exception.class)
public ResponseEntity<String> handleError(Exception e) {
    return ResponseEntity.status(500).body(e.getMessage() + "\n" + 
        Arrays.toString(e.getStackTrace()));
}

// 수정된 코드 - 내부 에러는 로그로만 남기고, 클라이언트에는 일반 메시지만 반환
@ExceptionHandler(Exception.class)
public ResponseEntity<ErrorResponse> handleError(Exception e) {
    String errorId = UUID.randomUUID().toString();
    log.error("Internal error [{}]", errorId, e);

    return ResponseEntity.status(500)
            .body(new ErrorResponse("Internal Server Error", errorId));
    // 클라이언트에게는 에러 ID만 주고, 이 ID로 로그를 추적한다
}
```

### 불필요한 기능 노출

- Swagger UI가 운영 환경에서 접근 가능한 경우가 많다. 프로파일로 분리하거나 인증을 건다
- 디버그 모드가 켜져 있으면 상세 에러 정보, SQL 쿼리가 응답에 포함될 수 있다
- 사용하지 않는 HTTP 메서드(TRACE, OPTIONS)가 열려 있으면 XST(Cross-Site Tracing) 공격에 악용될 수 있다
- 기본 관리자 계정(admin/admin)이 변경되지 않은 채 운영에 배포되는 경우가 있다

```java
// Spring Security - 불필요한 HTTP 메서드 차단
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers(HttpMethod.TRACE, "/**").denyAll()
            .requestMatchers(HttpMethod.OPTIONS, "/**").denyAll()
            // ... 나머지 설정
        );
    return http.build();
}
```

---

## A06: Vulnerable and Outdated Components

사용 중인 라이브러리, 프레임워크에 알려진 취약점이 있는 경우다. Log4Shell(CVE-2021-44228)이 대표적인 사례로, log4j 2.x의 JNDI 룩업 취약점 하나 때문에 전 세계 서버가 영향을 받았다.

### 의존성 취약점 탐지

```xml
<!-- Maven - OWASP Dependency Check 플러그인 -->
<plugin>
    <groupId>org.owasp</groupId>
    <artifactId>dependency-check-maven</artifactId>
    <version>9.0.9</version>
    <configuration>
        <failBuildOnCVSS>7</failBuildOnCVSS> <!-- CVSS 7 이상이면 빌드 실패 -->
    </configuration>
    <executions>
        <execution>
            <goals>
                <goal>check</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

```groovy
// Gradle - dependency-check 플러그인
plugins {
    id 'org.owasp.dependencycheck' version '9.0.9'
}

dependencyCheck {
    failBuildOnCVSS = 7.0f
    suppressionFile = 'dependency-check-suppression.xml' // 오탐 억제 파일
}
```

### SCA(Software Composition Analysis) 도구

빌드 도구 플러그인 외에 CI/CD 파이프라인에 통합할 수 있는 SCA 도구들이 있다.

| 도구 | 특징 |
|------|------|
| Snyk | GitHub 연동이 편하다. PR마다 자동으로 취약점을 스캔하고 수정 PR도 만들어준다 |
| Trivy | 컨테이너 이미지, 파일시스템, Git 저장소를 스캔한다. 오픈소스이고 CI에 넣기 쉽다 |
| GitHub Dependabot | GitHub 내장 기능. 취약한 의존성을 자동으로 감지하고 업데이트 PR을 생성한다 |
| OWASP Dependency-Track | 자체 호스팅 가능한 SBOM 관리 플랫폼. 조직 전체의 의존성을 중앙 관리할 수 있다 |

```yaml
# GitHub Actions에서 Trivy 스캔 예시
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    severity: 'HIGH,CRITICAL'
    exit-code: '1'  # 취약점 발견 시 빌드 실패
```

### 의존성 관리 시 주의할 점

- 직접 사용하지 않는 전이 의존성(transitive dependency)에서 취약점이 나오는 경우가 많다. `mvn dependency:tree`나 `gradle dependencies`로 전체 트리를 확인한다
- 취약점이 발견되어도 바로 업데이트할 수 없는 경우가 있다. 이때는 WAF 규칙 추가 같은 임시 대응을 먼저 적용한다
- EOL(End of Life)된 프레임워크를 계속 사용하면 보안 패치 자체가 나오지 않는다. Java 8에서 17로의 마이그레이션을 미루는 프로젝트가 많은데, 보안 관점에서도 리스크다

---

## A07: Identification and Authentication Failures

인증과 세션 관리의 결함을 다룬다. 세션 하이재킹, 크리덴셜 스터핑, 세션 고정 공격 등이 여기에 해당한다.

### 세션 관리 실수

```java
// 세션 고정 공격 방어 - 로그인 성공 시 세션 ID를 재발급한다
@PostMapping("/login")
public void login(HttpServletRequest request, @RequestBody LoginRequest loginRequest) {
    // 인증 처리
    authService.authenticate(loginRequest);

    // 기존 세션을 무효화하고 새 세션을 생성
    HttpSession oldSession = request.getSession(false);
    if (oldSession != null) {
        oldSession.invalidate();
    }
    HttpSession newSession = request.getSession(true);
    newSession.setAttribute("user", loginRequest.getUsername());
}
```

```java
// Spring Security에서는 세션 고정 방어가 기본으로 켜져 있다
// 하지만 커스텀 인증 로직을 직접 구현하면 이 보호가 적용되지 않으므로 주의
http.sessionManagement(session -> session
    .sessionFixation().changeSessionId()  // 기본값
    .maximumSessions(1)                   // 동시 세션 수 제한
    .maxSessionsPreventsLogin(true)       // 초과 시 새 로그인 차단
);
```

### 크리덴셜 스터핑 (Credential Stuffing)

다른 사이트에서 유출된 ID/비밀번호 조합을 대량으로 시도하는 공격이다. 사용자가 여러 사이트에서 같은 비밀번호를 사용하기 때문에 성공률이 높다.

```java
// 로그인 시도 제한
@Service
public class LoginAttemptService {
    private final LoadingCache<String, Integer> attemptsCache;

    public LoginAttemptService() {
        attemptsCache = CacheBuilder.newBuilder()
                .expireAfterWrite(30, TimeUnit.MINUTES)
                .build(new CacheLoader<>() {
                    @Override
                    public Integer load(String key) {
                        return 0;
                    }
                });
    }

    public void loginFailed(String key) {
        int attempts = attemptsCache.getUnchecked(key);
        attemptsCache.put(key, attempts + 1);
    }

    public boolean isBlocked(String key) {
        return attemptsCache.getUnchecked(key) >= 5;
    }
}

// 로그인 처리에서 사용
@PostMapping("/login")
public ResponseEntity<?> login(@RequestBody LoginRequest request, HttpServletRequest httpRequest) {
    String clientIp = httpRequest.getRemoteAddr();
    String key = clientIp + ":" + request.getUsername();

    if (loginAttemptService.isBlocked(key)) {
        return ResponseEntity.status(429)
                .body("Too many login attempts. Try again later.");
    }

    try {
        authService.authenticate(request);
        return ResponseEntity.ok().build();
    } catch (AuthenticationException e) {
        loginAttemptService.loginFailed(key);
        // 로그인 실패 시 "아이디 또는 비밀번호가 틀렸습니다" 형태로
        // 어떤 것이 틀렸는지 알려주지 않는다
        return ResponseEntity.status(401).body("Invalid credentials");
    }
}
```

### 인증 관련 주의사항

- 비밀번호 찾기 기능에서 "해당 이메일로 가입된 계정이 없습니다" 같은 메시지를 주면 이메일 열거(enumeration)가 가능하다. 존재 여부와 관계없이 같은 메시지를 보여준다
- JWT 토큰의 `alg` 필드를 `none`으로 바꾸는 공격이 있다. JWT 라이브러리에서 알고리즘을 명시적으로 지정해야 한다
- Refresh Token은 데이터베이스에 저장하고, 로그아웃 시 반드시 삭제한다. Access Token만 무효화하고 Refresh Token을 그대로 두면 재인증이 가능하다

---

## A08: Software and Data Integrity Failures

2021년에 새로 추가되었다. 소프트웨어 업데이트, CI/CD 파이프라인, 역직렬화 과정에서 무결성이 검증되지 않는 문제다.

### 안전하지 않은 역직렬화

Java의 `ObjectInputStream`, Python의 `pickle`, PHP의 `unserialize()`로 신뢰할 수 없는 데이터를 역직렬화하면 임의 코드가 실행될 수 있다. 2015년 Apache Commons Collections 취약점이 대표적이다.

```java
// 취약한 코드 - Java 역직렬화
@PostMapping("/import")
public void importData(@RequestBody byte[] data) {
    ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
    Object obj = ois.readObject();  // 임의 클래스의 객체가 생성될 수 있다
    processData(obj);
}

// 수정된 코드 - JSON 같은 구조화된 포맷을 사용한다
@PostMapping("/import")
public void importData(@RequestBody ImportDataRequest request) {
    // Jackson이 지정된 타입으로만 역직렬화한다
    processData(request);
}
```

Java 직렬화를 반드시 써야 하는 경우, `ObjectInputFilter`(Java 9+)로 허용할 클래스를 화이트리스트로 제한한다.

```java
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "com.myapp.model.*;!*"  // com.myapp.model 패키지만 허용, 나머지 거부
);
ObjectInputStream ois = new ObjectInputStream(inputStream);
ois.setObjectInputFilter(filter);
```

### CI/CD 파이프라인 변조

빌드 파이프라인이 침해되면 정상적인 코드 리뷰를 우회해서 악성 코드가 배포될 수 있다. SolarWinds 사건이 대표적이다.

주의할 지점:

- **의존성 무결성 검증**: `package-lock.json`, `gradle.lockfile` 같은 락 파일을 커밋하고, CI에서 락 파일과 실제 설치된 의존성이 일치하는지 확인한다
- **빌드 환경 격리**: 빌드 서버에서 외부 네트워크 접근을 제한한다. 빌드 중에 악성 스크립트가 외부 서버에서 페이로드를 다운로드하는 것을 막는다
- **코드 서명**: 빌드 산출물(JAR, Docker 이미지)에 서명하고, 배포 시 서명을 검증한다

```yaml
# GitHub Actions - 의존성 무결성 검증 예시
- name: Verify lockfile integrity
  run: |
    npm ci  # npm install 대신 npm ci를 사용하면
            # package-lock.json과 불일치 시 실패한다
```

```yaml
# Docker 이미지 서명 검증
# Cosign으로 이미지 서명
- name: Sign container image
  run: cosign sign --key cosign.key ${{ env.IMAGE_NAME }}:${{ env.TAG }}

# 배포 시 검증
- name: Verify image signature
  run: cosign verify --key cosign.pub ${{ env.IMAGE_NAME }}:${{ env.TAG }}
```

---

## A09: Security Logging and Monitoring Failures

공격이 발생해도 로그가 없거나, 로그가 있어도 모니터링하지 않아 탐지하지 못하는 문제다. 침해 사고 발생 후 평균 탐지 시간이 200일이 넘는다는 통계가 있다.

### 로그에 남겨야 하는 이벤트

- 로그인 성공/실패 (특히 실패 횟수)
- 권한 변경 (역할 부여, 권한 상승)
- 인증 토큰 발급/만료/무효화
- 데이터 접근 (민감 데이터 조회, 대량 데이터 다운로드)
- 설정 변경 (보안 설정, 시스템 설정)

```java
// 보안 이벤트 로깅 예시
@Component
public class SecurityEventLogger {

    private static final Logger securityLog = LoggerFactory.getLogger("SECURITY");

    public void logLoginFailure(String username, String ip, String reason) {
        securityLog.warn("LOGIN_FAILED user={} ip={} reason={}", username, ip, reason);
    }

    public void logPrivilegeEscalation(String username, String oldRole, String newRole, String changedBy) {
        securityLog.info("PRIVILEGE_CHANGE user={} from={} to={} by={}", 
                username, oldRole, newRole, changedBy);
    }

    public void logSensitiveDataAccess(String username, String resource, int recordCount) {
        securityLog.info("DATA_ACCESS user={} resource={} records={}", 
                username, resource, recordCount);
    }
}
```

### 로그 인젝션

로그에 사용자 입력이 그대로 들어가면, 공격자가 가짜 로그 엔트리를 삽입할 수 있다.

```java
// 취약한 로깅 - 개행 문자로 가짜 로그를 삽입할 수 있다
// 입력값: "admin\n2026-04-07 INFO LOGIN_SUCCESS user=admin"
log.info("LOGIN_FAILED user=" + username);
// 로그에 성공한 것처럼 보이는 가짜 라인이 추가된다

// 수정된 코드 - 파라미터화된 로깅 + 개행 제거
log.info("LOGIN_FAILED user={}", username.replaceAll("[\\r\\n]", "_"));
```

SLF4J의 `{}` 플레이스홀더를 사용하면 로그 인젝션의 일부 형태를 막을 수 있지만, 개행 문자까지 제거하는 것이 확실하다.

### 탐지 누락 패턴

로그를 쌓기만 하고 모니터링하지 않으면 의미가 없다. 다음과 같은 패턴이 감지되면 경고를 발생시켜야 한다.

| 패턴 | 의미 |
|------|------|
| 동일 IP에서 짧은 시간 내 다수의 로그인 실패 | 브루트포스 또는 크리덴셜 스터핑 시도 |
| 하나의 계정으로 여러 IP에서 동시 접속 | 세션 탈취 가능성 |
| 비정상적인 시간대 관리자 접속 | 계정 탈취 가능성 |
| 대량 데이터 다운로드 | 데이터 유출 시도 |
| 연속적인 403/401 응답 | 권한 탐색(fuzzing) 시도 |

```yaml
# ELK Stack 기반 탐지 규칙 예시 (Elasticsearch Watcher)
# 5분 내 동일 IP에서 10회 이상 로그인 실패 시 알림
trigger:
  schedule:
    interval: "1m"
condition:
  compare:
    ctx.payload.hits.total: { gte: 10 }
input:
  search:
    request:
      indices: ["security-logs-*"]
      body:
        query:
          bool:
            must:
              - match: { event: "LOGIN_FAILED" }
              - range:
                  "@timestamp":
                    gte: "now-5m"
            must_not: []
        aggs:
          by_ip:
            terms:
              field: "client_ip"
              min_doc_count: 10
actions:
  notify:
    slack:
      message:
        text: "Brute force attempt detected"
```

---

## A10: Server-Side Request Forgery (SSRF)

서버가 외부 입력을 기반으로 HTTP 요청을 보내는 경우, 공격자가 내부 네트워크의 리소스에 접근하는 공격이다. 클라우드 환경에서 메타데이터 API(169.254.169.254)에 접근하면 IAM 인증 정보가 유출될 수 있다.

SSRF의 상세한 공격 유형과 대응 방법은 별도 문서에서 다루고 있다. → [SSRF 상세](../Security/SSRF.md)

핵심 대응:

- 사용자 입력 URL을 서버에서 요청하는 기능은 최소화한다
- URL 파싱 후 내부 IP 대역(10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x)을 차단한다
- DNS Rebinding 공격을 막기 위해, DNS 조회 후 IP를 다시 검증한다
- 클라우드 환경에서는 IMDSv2(토큰 기반)를 사용해 메타데이터 API 접근을 제한한다

---

## 정리

| 순위 | 항목 | 핵심 |
|------|------|------|
| A01 | Broken Access Control | 모든 API에 소유권/권한 검증을 넣는다 |
| A02 | Cryptographic Failures | 민감 데이터 암호화, 강한 해싱, 키 관리 |
| A03 | Injection | 파라미터 바인딩, 출력 이스케이핑 |
| A04 | Insecure Design | 설계 단계에서 악용 시나리오를 검토한다 |
| A05 | Security Misconfiguration | 디폴트 설정 변경, 불필요한 기능 비활성화 |
| A06 | Vulnerable Components | 의존성 스캔을 CI에 넣고 주기적으로 업데이트 |
| A07 | Auth Failures | 세션 관리, 로그인 시도 제한, 토큰 관리 |
| A08 | Integrity Failures | 역직렬화 제한, CI/CD 파이프라인 보호 |
| A09 | Logging Failures | 보안 이벤트 로깅, 탐지 규칙 설정 |
| A10 | SSRF | 내부 IP 차단, 메타데이터 API 보호 |

운영 중인 서비스가 있다면 A01(Broken Access Control)부터 점검하는 것이 맞다. 가장 빈번하게 발생하고, 영향도가 크다. 그 다음은 A05(Security Misconfiguration)를 확인한다. 설정 문제는 코드 수정 없이 빠르게 조치할 수 있는 항목이 많다.
