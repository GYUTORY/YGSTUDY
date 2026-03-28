---
title: 보안 기초 개념
tags: [security, CIA-triad, authentication, authorization, encryption, hash, defense-in-depth]
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

## 해시 알고리즘 비교

| 알고리즘 | 출력 길이 | 용도 | 상태 |
|----------|-----------|------|------|
| MD5 | 128bit | 파일 체크섬 (보안 용도 외) | 충돌 발견됨. 보안 용도 사용 금지 |
| SHA-1 | 160bit | Git 내부 해시 (레거시) | 충돌 발견됨. 신규 사용 금지 |
| SHA-256 | 256bit | 데이터 무결성, 서명 | 현재 표준 |
| bcrypt | 184bit | 비밀번호 해시 전용 | 권장 |
| Argon2 | 가변 | 비밀번호 해시 전용 | 최신 권장. 2015 Password Hashing Competition 우승 |

MD5나 SHA-1을 비밀번호 해시에 쓰는 레거시 시스템이 아직 있다. 이런 시스템을 만나면 bcrypt나 Argon2로 마이그레이션 계획을 잡아야 한다.
