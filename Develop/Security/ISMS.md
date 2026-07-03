---
title: ISMS / ISMS-P
tags: [security, isms, isms-p, certification, compliance, kisa, access-control, logging, encryption]
updated: 2026-04-08
---

# ISMS / ISMS-P 인증 체계

ISMS(정보보호 관리체계)는 KISA(한국인터넷진흥원)가 운영하는 국내 정보보호 인증 제도다. 2018년부터 기존 ISMS와 PIMS가 통합되면서 ISMS-P(개인정보보호 포함)라는 인증이 추가됐다.

ISO 27001이 국제 표준이라면, ISMS는 한국 법률(정보통신망법, 개인정보보호법)에 직접 연결된 인증이다. ISO 27001 인증을 받았다고 ISMS 의무가 면제되지 않는다. 별개의 인증이고, 통제 항목도 다르다.

실제 심사를 받아보면 ISO 27001보다 기술적 통제 항목이 구체적이다. "접근통제 정책을 수립하라"가 아니라 "비밀번호는 일방향 암호화하고, 8자 이상, 영문/숫자/특수문자 조합이어야 한다" 같은 수준으로 요구한다. 그래서 개발팀이 직접 대응해야 하는 항목이 많다.

---

## 인증 의무 대상

ISMS 인증은 아무나 받는 게 아니라, 법적으로 의무 대상이 정해져 있다. 정보통신망법 제47조에 근거한다.

**의무 대상 기준:**

- ISP(인터넷 서비스 제공자): KT, SK브로드밴드 같은 사업자
- IDC(호스팅 업체): 서버 호스팅, 클라우드 서비스 사업자
- 정보통신서비스 매출 100억 원 이상
- 일평균 이용자 수 100만 명 이상
- 의료, 교육 등 특정 분야 사업자

의무 대상이 아니라도 자발적으로 인증받을 수 있다. 공공 입찰이나 대기업 협력사 요건으로 ISMS 인증을 요구하는 경우가 늘고 있어서, 규모가 작아도 인증을 준비하는 회사가 많아졌다.

---

## ISMS vs ISMS-P 차이

둘 다 같은 인증 체계 안에 있다. ISMS-P는 ISMS에 개인정보 관련 통제 항목이 추가된 확장판이다.

| 구분 | ISMS | ISMS-P |
|------|------|--------|
| 통제 항목 수 | 80개 | 101개 (80 + 21) |
| 개인정보 처리 항목 | 없음 | 21개 추가 |
| 대상 | 정보보호가 필요한 서비스 | 개인정보를 대량 처리하는 서비스 |
| 인증 유효기간 | 3년 (매년 사후심사) | 3년 (매년 사후심사) |

개인정보를 다루는 서비스라면 ISMS-P로 받는 게 일반적이다. ISMS만 받으면 개인정보보호법 관련 항목은 별도로 점검해야 한다.

---

## ISMS vs ISO 27001

같은 "정보보호 관리체계" 인증이지만 운영 방식이 상당히 다르다.

| 구분 | ISMS | ISO 27001 |
|------|------|-----------|
| 운영 기관 | KISA | ISO/IEC (국제기구) |
| 법적 구속력 | 있음 (과태료 최대 3천만 원) | 없음 (자발적 인증) |
| 통제 항목 | 80개 (ISMS-P는 101개) | 93개 (2022 개정 기준) |
| 심사 방식 | 현장 심사 중심, 기술적 검증 포함 | 프로세스/문서 중심 |
| 특징 | 한국 법률 기반, 기술 항목이 구체적 | 국제 호환성, 프레임워크 중심 |

ISO 27001은 "위험 관리 프레임워크를 갖추고 있느냐"를 보고, ISMS는 "실제로 이렇게 구현했느냐"를 본다. 심사 현장에서 서버에 접속해서 설정값을 직접 확인하는 일이 흔하다.

---

## 심사 절차

인증 심사는 크게 서류 심사와 현장 심사로 나뉜다. 전체 과정은 보통 3~6개월 걸린다.

1. **인증 신청**: KISA 또는 인증기관에 신청서 제출
2. **서류 심사**: 정보보호 정책서, 위험평가 보고서, 각종 절차서 검토
3. **현장 심사**: 실제 시스템 점검, 담당자 인터뷰, 증적 확인
4. **보완 조치**: 결함 사항 시정 및 증적 제출
5. **인증 심의**: 인증위원회 최종 심의
6. **인증서 발급**: 3년 유효, 매년 사후심사

현장 심사에서 심사원이 직접 서버 화면을 보면서 확인한다. "비밀번호 정책이 어떻게 되어 있나요?" 물어보면 코드나 설정 화면을 보여줘야 한다. 문서만 있고 실제 구현이 안 되어 있으면 결함으로 잡힌다.

---

## 백엔드 개발자가 대응해야 하는 주요 통제 항목

80개(또는 101개) 통제 항목 중에서 개발팀이 직접 코드로 대응해야 하는 항목들이 있다. 심사에서 가장 자주 지적되는 항목을 중심으로 정리한다.

### 1. 접근통제 — 비밀번호 정책

ISMS 통제 항목에서 비밀번호 관련 요구사항은 꽤 구체적이다.

- 최소 8자 이상, 영문/숫자/특수문자 중 2종류 이상 조합 (10자 이상이면 2종류, 8자 이상이면 3종류)
- 일방향 암호화 저장 (SHA-256 단독 사용은 부적합, bcrypt/scrypt/PBKDF2 사용)
- 비밀번호 변경 주기 설정 (보통 90일)
- 최근 사용한 비밀번호 재사용 제한
- 초기 비밀번호 발급 시 변경 강제

```java
@Component
public class PasswordPolicyValidator {

    // ISMS 기준: 8자 이상 3종류 조합 또는 10자 이상 2종류 조합
    private static final String PATTERN_8CHAR_3TYPE =
        "^(?=.*[a-zA-Z])(?=.*\\d)(?=.*[!@#$%^&*()_+\\-=]).{8,}$";
    private static final String PATTERN_10CHAR_2TYPE =
        "^((?=.*[a-zA-Z])(?=.*\\d)|(?=.*[a-zA-Z])(?=.*[!@#$%^&*()_+\\-=])|(?=.*\\d)(?=.*[!@#$%^&*()_+\\-=])).{10,}$";

    public void validate(String password, Long userId) {
        if (!Pattern.matches(PATTERN_8CHAR_3TYPE, password)
            && !Pattern.matches(PATTERN_10CHAR_2TYPE, password)) {
            throw new InvalidPasswordException(
                "비밀번호는 8자 이상(영문/숫자/특수문자 조합) 또는 10자 이상(2종류 조합)이어야 합니다");
        }

        // 연속된 문자/숫자 3자리 이상 금지 (abc, 123 같은 패턴)
        if (hasSequentialChars(password, 3)) {
            throw new InvalidPasswordException("연속된 문자 또는 숫자를 3자리 이상 사용할 수 없습니다");
        }

        // 아이디와 동일한 비밀번호 금지
        if (isSameAsUserId(password, userId)) {
            throw new InvalidPasswordException("아이디와 동일한 비밀번호는 사용할 수 없습니다");
        }
    }

    private boolean hasSequentialChars(String password, int length) {
        for (int i = 0; i <= password.length() - length; i++) {
            boolean sequential = true;
            for (int j = 1; j < length; j++) {
                if (password.charAt(i + j) - password.charAt(i + j - 1) != 1) {
                    sequential = false;
                    break;
                }
            }
            if (sequential) return true;
        }
        return false;
    }

    private boolean isSameAsUserId(String password, Long userId) {
        // 실제 구현에서는 사용자 로그인 ID와 비교
        return false;
    }
}
```

비밀번호 암호화는 Spring Security의 `BCryptPasswordEncoder`를 쓰면 된다. SHA-256으로 저장하고 있었다면 심사에서 지적받는다. bcrypt는 salt가 내장되어 있고 work factor 조절이 가능해서 ISMS 요건을 충족한다.

```java
@Configuration
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        // strength 기본값 10, 운영 환경에서는 12 이상 권장
        return new BCryptPasswordEncoder(12);
    }
}
```

### 2. 접근통제 — 세션 관리

심사에서 세션 관련 질문은 거의 빠지지 않는다.

- 세션 타임아웃 설정 (보통 30분 이내)
- 동시 세션 제한 (같은 계정으로 여러 곳에서 동시 로그인 차단)
- 로그인 실패 시 계정 잠금 (5~10회 실패 시)

```java
@Configuration
@EnableWebSecurity
public class SessionSecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
                .invalidSessionUrl("/login?expired")
                .maximumSessions(1)                          // 동시 세션 1개 제한
                .maxSessionsPreventsLogin(false)              // 기존 세션 만료 처리
                .expiredUrl("/login?duplicated")
            );

        return http.build();
    }
}
```

```yaml
# application.yml
server:
  servlet:
    session:
      timeout: 30m    # 세션 타임아웃 30분
      cookie:
        http-only: true
        secure: true   # HTTPS 환경 필수
```

로그인 실패 잠금은 별도로 구현해야 한다. Spring Security의 `AuthenticationFailureHandler`를 구현하거나, DB에 실패 횟수를 기록하는 방식이 일반적이다.

```java
@Service
@RequiredArgsConstructor
public class LoginAttemptService {

    private final LoginAttemptRepository attemptRepository;
    private static final int MAX_ATTEMPTS = 5;
    private static final Duration LOCK_DURATION = Duration.ofMinutes(30);

    public void loginFailed(String username) {
        LoginAttempt attempt = attemptRepository.findByUsername(username)
            .orElse(new LoginAttempt(username));

        attempt.incrementFailCount();
        attempt.setLastAttempt(LocalDateTime.now());

        if (attempt.getFailCount() >= MAX_ATTEMPTS) {
            attempt.setLockedUntil(LocalDateTime.now().plus(LOCK_DURATION));
        }

        attemptRepository.save(attempt);
    }

    public void loginSucceeded(String username) {
        attemptRepository.findByUsername(username)
            .ifPresent(attempt -> {
                attempt.resetFailCount();
                attemptRepository.save(attempt);
            });
    }

    public boolean isLocked(String username) {
        return attemptRepository.findByUsername(username)
            .map(attempt -> attempt.getLockedUntil() != null
                && attempt.getLockedUntil().isAfter(LocalDateTime.now()))
            .orElse(false);
    }
}
```

### 3. 로깅과 감사 추적

ISMS 심사에서 로그 관련 항목은 까다롭다. "로그를 남기고 있습니까?"가 아니라 "어떤 로그를, 얼마나 보관하고, 위변조 방지는 어떻게 합니까?"를 물어본다.

**필수 기록 대상:**

- 사용자 로그인/로그아웃
- 개인정보 조회/수정/삭제
- 관리자 권한 행위
- 시스템 설정 변경
- 접근 권한 변경

**보관 기간:** 최소 6개월 (개인정보 관련 로그는 3년 요구하는 경우도 있다)

```java
@Aspect
@Component
@RequiredArgsConstructor
public class AuditLogAspect {

    private final AuditLogRepository auditLogRepository;

    @Around("@annotation(auditable)")
    public Object audit(ProceedingJoinPoint joinPoint, Auditable auditable) throws Throwable {
        HttpServletRequest request =
            ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes())
                .getRequest();

        String username = SecurityContextHolder.getContext()
            .getAuthentication().getName();

        AuditLog log = AuditLog.builder()
            .username(username)
            .action(auditable.action())
            .resource(auditable.resource())
            .clientIp(getClientIp(request))
            .userAgent(request.getHeader("User-Agent"))
            .timestamp(LocalDateTime.now())
            .build();

        try {
            Object result = joinPoint.proceed();
            log.setStatus("SUCCESS");
            return result;
        } catch (Exception e) {
            log.setStatus("FAILURE");
            log.setErrorMessage(e.getMessage());
            throw e;
        } finally {
            auditLogRepository.save(log);
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty()) {
            ip = request.getRemoteAddr();
        }
        return ip.split(",")[0].trim();
    }
}
```

```java
// 사용 예시
@RestController
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @Auditable(action = "USER_INFO_VIEW", resource = "USER")
    @GetMapping("/users/{userId}")
    public UserResponse getUser(@PathVariable Long userId) {
        return userService.getUser(userId);
    }

    @Auditable(action = "USER_INFO_UPDATE", resource = "USER")
    @PutMapping("/users/{userId}")
    public UserResponse updateUser(@PathVariable Long userId, @RequestBody UserUpdateRequest req) {
        return userService.updateUser(userId, req);
    }
}
```

커스텀 어노테이션 정의:

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Auditable {
    String action();
    String resource();
}
```

AWS 환경에서는 CloudWatch Logs나 S3에 로그를 저장하는데, 심사에서는 로그 보관 정책과 삭제 방지 설정을 확인한다. S3에 저장한다면 Object Lock 설정으로 위변조를 방지할 수 있다.

```java
@Configuration
public class S3AuditLogConfig {

    @Bean
    public S3Client s3Client() {
        return S3Client.builder()
            .region(Region.AP_NORTHEAST_2)
            .build();
    }

    // 감사 로그를 S3에 저장할 때 Object Lock 적용
    public void uploadAuditLog(S3Client s3Client, String bucket, String key, byte[] logData) {
        s3Client.putObject(
            PutObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .objectLockMode(ObjectLockMode.COMPLIANCE)    // 삭제/수정 불가
                .objectLockRetainUntilDate(
                    Instant.now().plus(Duration.ofDays(365))  // 1년 보관
                )
                .build(),
            RequestBody.fromBytes(logData)
        );
    }
}
```

### 4. 암호화

ISMS에서 암호화 관련 요구사항은 명확하다.

**전송 구간 암호화:**

- 모든 통신은 TLS 1.2 이상
- TLS 1.0, 1.1은 비활성화해야 한다
- 내부 서비스 간 통신도 암호화 대상 (마이크로서비스 간 통신 포함)

**저장 데이터 암호화:**

- 개인정보(이름, 전화번호, 이메일 등)는 양방향 암호화
- 비밀번호는 일방향 암호화 (위에서 다룸)
- 주민등록번호, 카드번호 같은 민감정보는 반드시 암호화

```java
@Component
public class PersonalInfoEncryptor {

    // AES-256 사용 — 키는 AWS KMS나 별도 키 관리 시스템에서 관리
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_TAG_LENGTH = 128;
    private static final int IV_LENGTH = 12;

    private final SecretKey secretKey;

    public PersonalInfoEncryptor(@Value("${encryption.key}") String base64Key) {
        byte[] decodedKey = Base64.getDecoder().decode(base64Key);
        this.secretKey = new SecretKeySpec(decodedKey, "AES");
    }

    public String encrypt(String plainText) {
        try {
            byte[] iv = new byte[IV_LENGTH];
            SecureRandom.getInstanceStrong().nextBytes(iv);

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey,
                new GCMParameterSpec(GCM_TAG_LENGTH, iv));

            byte[] encrypted = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));

            // IV + 암호문을 합쳐서 Base64로 반환
            byte[] combined = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(encrypted, 0, combined, iv.length, encrypted.length);

            return Base64.getEncoder().encodeToString(combined);
        } catch (Exception e) {
            throw new EncryptionException("암호화 실패", e);
        }
    }

    public String decrypt(String cipherText) {
        try {
            byte[] combined = Base64.getDecoder().decode(cipherText);

            byte[] iv = new byte[IV_LENGTH];
            byte[] encrypted = new byte[combined.length - IV_LENGTH];
            System.arraycopy(combined, 0, iv, 0, IV_LENGTH);
            System.arraycopy(combined, IV_LENGTH, encrypted, 0, encrypted.length);

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.DECRYPT_MODE, secretKey,
                new GCMParameterSpec(GCM_TAG_LENGTH, iv));

            return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new EncryptionException("복호화 실패", e);
        }
    }
}
```

JPA Entity에서 개인정보 필드에 암호화를 적용하는 방식:

```java
@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String loginId;

    // 개인정보 필드는 AttributeConverter로 자동 암호화/복호화
    @Convert(converter = EncryptConverter.class)
    private String name;

    @Convert(converter = EncryptConverter.class)
    private String phone;

    @Convert(converter = EncryptConverter.class)
    private String email;

    // 비밀번호는 일방향 암호화이므로 별도 처리
    private String password;
}
```

```java
@Converter
@RequiredArgsConstructor
public class EncryptConverter implements AttributeConverter<String, String> {

    private final PersonalInfoEncryptor encryptor;

    @Override
    public String convertToDatabaseColumn(String attribute) {
        if (attribute == null) return null;
        return encryptor.encrypt(attribute);
    }

    @Override
    public String convertToEntityAttribute(String dbData) {
        if (dbData == null) return null;
        return encryptor.decrypt(dbData);
    }
}
```

암호화 키 관리가 중요한데, application.yml에 키를 직접 넣으면 심사에서 지적받는다. AWS KMS를 사용하거나, HashiCorp Vault 같은 별도 키 관리 시스템을 써야 한다.

```yaml
# 잘못된 예 — 설정 파일에 키를 직접 넣으면 안 된다
encryption:
  key: "dGhpcyBpcyBhIHRlc3Qga2V5MTIzNDU2Nzg="

# AWS KMS 사용 시
encryption:
  kms-key-id: "arn:aws:kms:ap-northeast-2:123456789:key/abcd-1234"
```

### 5. 개인정보 처리 (ISMS-P 추가 항목)

ISMS-P 인증을 받으려면 개인정보 라이프사이클 전체를 관리해야 한다.

**개인정보 수집 시:**

- 필수/선택 항목 구분
- 동의 기록 보관
- 수집 목적 명시

**개인정보 파기:**

- 보유 기간 경과 시 지체 없이 파기
- 파기 기록 남기기
- DB에서 단순 DELETE가 아니라 복구 불가능하게 처리

```java
@Service
@RequiredArgsConstructor
public class PersonalDataDestroyService {

    private final UserRepository userRepository;
    private final DestroyLogRepository destroyLogRepository;

    /**
     * 보유기간 만료된 개인정보 파기 처리
     * 스케줄러로 매일 실행
     */
    @Scheduled(cron = "0 0 2 * * *")  // 매일 새벽 2시
    @Transactional
    public void destroyExpiredPersonalData() {
        LocalDate cutoffDate = LocalDate.now().minusYears(1);  // 1년 경과

        List<User> expiredUsers = userRepository
            .findByLastLoginDateBeforeAndStatus(cutoffDate, UserStatus.INACTIVE);

        for (User user : expiredUsers) {
            // 파기 기록 먼저 저장
            DestroyLog log = DestroyLog.builder()
                .userId(user.getId())
                .destroyedFields("name, phone, email")
                .reason("보유기간 만료 (1년 미로그인)")
                .destroyedAt(LocalDateTime.now())
                .build();
            destroyLogRepository.save(log);

            // 개인정보 필드를 랜덤 값으로 덮어쓰기 (복구 방지)
            user.setName(generateRandomString(10));
            user.setPhone(generateRandomString(11));
            user.setEmail(generateRandomString(20));
            user.setStatus(UserStatus.DESTROYED);

            userRepository.save(user);
        }
    }

    private String generateRandomString(int length) {
        return UUID.randomUUID().toString().replace("-", "").substring(0, length);
    }
}
```

단순히 `null`로 바꾸는 건 파기로 인정되지 않는 경우가 있다. 랜덤 값으로 덮어쓰거나, 별도 파기 테이블로 이동 후 원본 테이블에서 삭제하는 방식을 쓴다.

---

## AWS 환경에서의 ISMS 대응

AWS에서 서비스를 운영하는 경우, 인프라 레벨에서 대응해야 하는 항목이 있다.

### 네트워크 접근통제

```
# VPC 구성 — 심사에서 네트워크 분리를 확인한다

Public Subnet (10.0.1.0/24)
  └── ALB (Application Load Balancer)

Private Subnet (10.0.2.0/24)
  └── EC2 / ECS (애플리케이션 서버)

Private Subnet (10.0.3.0/24)
  └── RDS (데이터베이스)
  └── ElastiCache
```

DB가 Public Subnet에 있으면 심사에서 바로 지적된다. RDS는 반드시 Private Subnet에 배치하고, Security Group으로 애플리케이션 서버에서만 접근 가능하도록 설정한다.

### CloudTrail 설정

AWS 계정 레벨의 모든 API 호출을 기록해야 한다. CloudTrail을 활성화하지 않으면 "시스템 접근 기록 관리" 항목에서 결함이 나온다.

```yaml
# CloudFormation 예시
Resources:
  AuditTrail:
    Type: AWS::CloudTrail::Trail
    Properties:
      TrailName: isms-audit-trail
      S3BucketName: !Ref AuditLogBucket
      IsLogging: true
      IsMultiRegionTrail: true
      EnableLogFileValidation: true   # 로그 무결성 검증
      EventSelectors:
        - ReadWriteType: All
          IncludeManagementEvents: true

  AuditLogBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: company-isms-audit-logs
      ObjectLockEnabled: true           # 삭제 방지
      LifecycleConfiguration:
        Rules:
          - Id: RetainLogs
            Status: Enabled
            ExpirationInDays: 365       # 1년 보관
```

### AWS WAF 설정

웹 애플리케이션 방화벽 운영 여부도 심사 항목이다. AWS WAF를 ALB 앞단에 붙여서 기본적인 공격을 차단한다.

SQL Injection, XSS 같은 공격은 코드 레벨에서도 방어해야 하지만, WAF를 운영하고 있다는 것 자체가 심사에서 긍정적으로 평가된다. AWS Managed Rules 중 `AWSManagedRulesCommonRuleSet`과 `AWSManagedRulesSQLiRuleSet`은 기본으로 적용하는 게 좋다.

---

## 인증 준비 시 개발팀이 흔히 놓치는 부분

### 에러 메시지에 시스템 정보 노출

심사원이 API를 호출해서 에러를 발생시킨 다음, 응답에 스택 트레이스나 DB 정보가 포함되어 있는지 확인한다. Spring Boot 기본 설정으로 운영하면 에러 응답에 내부 정보가 노출된다.

```yaml
# application.yml — 운영 환경 설정
server:
  error:
    include-stacktrace: never
    include-message: never
    include-binding-errors: never
    include-exception: false
```

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    // 클라이언트에 내부 정보를 절대 노출하지 않는다
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleException(Exception e) {
        // 내부 로그에는 상세 정보 기록
        log.error("Unhandled exception", e);

        // 클라이언트에는 일반적인 메시지만 반환
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ErrorResponse("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."));
    }
}
```

### 관리자 페이지 접근통제 미흡

관리자 페이지를 `/admin` 경로에 두고 IP 제한 없이 운영하는 경우가 많다. 심사에서 관리자 페이지 접근 방식을 확인하는데, 최소한 IP 기반 접근 제한은 있어야 한다.

```java
@Configuration
public class AdminSecurityConfig {

    @Bean
    @Order(1)
    public SecurityFilterChain adminFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/admin/**")
            .authorizeHttpRequests(auth -> auth
                .anyRequest().access(new WebExpressionAuthorizationManager(
                    "hasRole('ADMIN') and hasIpAddress('10.0.0.0/8')"))
            );

        return http.build();
    }
}
```

실제 운영에서는 VPN을 통해서만 관리자 페이지에 접근할 수 있게 하는 경우가 대부분이다.

### 개발/운영 환경 분리

개발 서버에서 운영 DB에 직접 접근할 수 있는 구조로 되어 있으면 결함이다. 환경 분리가 안 되어 있다는 지적을 받는다. DB 접속 정보가 개발자 로컬에 하드코딩되어 있는 것도 문제가 된다.

```yaml
# 환경별 설정 분리 — Spring Profile 사용
# application-prod.yml
spring:
  datasource:
    url: jdbc:mysql://${DB_HOST}:3306/${DB_NAME}   # 환경변수로 관리
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}

# AWS Systems Manager Parameter Store 사용 시
aws:
  ssm:
    parameters:
      db-host: /prod/database/host
      db-username: /prod/database/username
      db-password: /prod/database/password
```

### 로그에 개인정보 기록

디버깅하려고 로그에 요청 바디를 그대로 찍는 경우가 있다. 개인정보가 포함된 요청이 로그에 평문으로 남으면 심사에서 지적된다.

```java
// 잘못된 예
log.info("회원가입 요청: {}", request);  // name, phone, email 등이 평문으로 기록됨

// 개인정보 마스킹 처리
log.info("회원가입 요청: name={}, phone={}", 
    maskName(request.getName()),       // 김*영
    maskPhone(request.getPhone()));    // 010-****-5678
```

```java
@Component
public class PersonalInfoMasker {

    public String maskName(String name) {
        if (name == null || name.length() < 2) return "**";
        return name.charAt(0) + "*".repeat(name.length() - 2) + name.charAt(name.length() - 1);
    }

    public String maskPhone(String phone) {
        if (phone == null) return "***";
        return phone.replaceAll("(\\d{3})-?(\\d{4})-?(\\d{4})", "$1-****-$3");
    }

    public String maskEmail(String email) {
        if (email == null) return "***";
        int atIndex = email.indexOf('@');
        if (atIndex <= 2) return "**" + email.substring(atIndex);
        return email.substring(0, 2) + "***" + email.substring(atIndex);
    }
}
```

### 테스트 데이터에 실제 개인정보 사용

개발/테스트 환경에서 운영 DB를 복사해서 사용하는 경우가 있다. 실제 고객 데이터가 개발 환경에 있으면 ISMS-P 심사에서 바로 결함이다. 테스트 데이터는 가명 처리하거나, Faker 라이브러리로 생성한 가짜 데이터를 써야 한다.

---

## 심사 증적 준비

심사에서는 문서뿐 아니라 실제 동작 증거(증적)를 요구한다. 개발팀이 준비해야 하는 증적 목록이다.

| 통제 항목 | 증적 예시 |
|-----------|-----------|
| 비밀번호 정책 | 비밀번호 유효성 검증 코드, 테스트 결과 스크린샷 |
| 세션 관리 | 세션 타임아웃 설정 화면, 동시 접속 차단 테스트 결과 |
| 접근통제 | Security Group 설정, VPC 구성도, 관리자 페이지 접근 제한 설정 |
| 암호화 | TLS 인증서 정보, DB 암호화 설정, 키 관리 시스템 화면 |
| 로그 관리 | 로그 저장 화면, 보관 정책 설정, 위변조 방지 설정 |
| 개인정보 파기 | 파기 스케줄러 코드, 파기 기록 테이블, 실행 로그 |
| 취약점 점검 | 최근 모의해킹 보고서, 조치 내역 |

심사 2~3개월 전부터 증적을 준비하는 게 좋다. 심사 직전에 몰아서 하면 실제 운영 이력이 없어서 형식적이라는 지적을 받을 수 있다.

---

## 정리

ISMS 인증은 문서 작업이 반이고, 기술적 구현이 반이다. 보안팀이 정책 문서를 만들면, 개발팀은 그 정책이 코드에 반영되었다는 걸 증명해야 한다.

심사원이 가장 많이 보는 포인트는 다음과 같다:

- 비밀번호가 bcrypt/scrypt로 저장되고 있는가
- 개인정보가 DB에 암호화되어 있는가
- 로그인/개인정보 접근 로그가 남고 있는가
- 세션 타임아웃과 로그인 실패 잠금이 동작하는가
- 운영 환경과 개발 환경이 분리되어 있는가
- 에러 응답에 시스템 내부 정보가 노출되지 않는가

코드를 짜는 시점에서 이 항목들을 고려하면, 심사 준비 기간에 급하게 고치는 일을 줄일 수 있다. 신규 프로젝트라면 처음부터 반영하는 게 공수가 훨씬 적다.
