---
title: AES Advanced Encryption Standard
tags: [security, aes, encryption, cryptography, java, spring-boot]
updated: 2026-04-09
---

# AES (Advanced Encryption Standard)

## 개요

AES는 2001년 NIST에서 채택한 대칭키 암호화 알고리즘이다. 암호화와 복호화에 같은 키를 사용하고, 128비트 블록 단위로 데이터를 처리한다.

## 키 길이와 라운드 수

| 키 길이 | 라운드 수 | 용도 |
|---------|-----------|------|
| 128비트 | 10라운드 | 일반 서비스 |
| 192비트 | 12라운드 | 금융/의료 데이터 |
| 256비트 | 14라운드 | 군사/기밀 정보 |

실무에서는 AES-256을 기본으로 쓰는 경우가 많다. AES-128도 현재 기준으로 충분히 안전하지만, 규정이나 감사에서 256비트를 요구하는 경우가 있다.

## 블록 암호화 과정

### 전체 흐름

```
┌─────────────────────────────────────────────────────┐
│                    평문 (128비트)                      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   AddRoundKey       │ ← 초기 라운드 키
            │  (평문 XOR 키)       │
            └──────────┬──────────┘
                       │
          ┌────────────▼────────────┐
          │   라운드 1 ~ N-1 반복     │
          │                         │
          │  ┌───────────────────┐  │
          │  │ 1. SubBytes       │  │  S-box로 바이트 치환
          │  │    (바이트 치환)    │  │  → 비선형성 확보
          │  └────────┬──────────┘  │
          │           ▼             │
          │  ┌───────────────────┐  │
          │  │ 2. ShiftRows      │  │  행별로 순환 이동
          │  │    (행 이동)       │  │  → 블록 내 확산
          │  └────────┬──────────┘  │
          │           ▼             │
          │  ┌───────────────────┐  │
          │  │ 3. MixColumns     │  │  열 단위 다항식 곱셈
          │  │    (열 혼합)       │  │  → 바이트 간 혼합
          │  └────────┬──────────┘  │
          │           ▼             │
          │  ┌───────────────────┐  │
          │  │ 4. AddRoundKey    │  │  라운드 키 XOR
          │  │    (키 결합)       │  │
          │  └────────┬──────────┘  │
          └────────────┼────────────┘
                       │
          ┌────────────▼────────────┐
          │   최종 라운드 (N번째)     │
          │                         │
          │  SubBytes → ShiftRows   │  MixColumns 없음
          │  → AddRoundKey          │
          └────────────┬────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   암호문 (128비트)    │
            └─────────────────────┘
```

최종 라운드에서 MixColumns를 빼는 이유가 있다. 복호화 과정에서 라운드 함수의 역변환 구조를 맞추기 위해서다. MixColumns가 있으면 암복호화 대칭 구조가 깨진다.

### 라운드 함수 상세

**SubBytes** — 4x4 상태 행렬의 각 바이트를 S-box 테이블로 치환한다.

```
입력 상태 행렬         S-box 치환 후
┌────┬────┬────┬────┐   ┌────┬────┬────┬────┐
│ 19 │ a0 │ 9a │ e9 │   │ d4 │ e0 │ b8 │ 1e │
│ 3d │ f4 │ c6 │ f8 │ → │ 27 │ bf │ b4 │ 41 │
│ e3 │ e2 │ 8d │ 48 │   │ 11 │ 98 │ 5d │ 52 │
│ be │ 2b │ 2a │ 08 │   │ ae │ f1 │ e5 │ 30 │
└────┴────┴────┴────┘   └────┴────┴────┴────┘
```

**ShiftRows** — 각 행을 왼쪽으로 순환 이동한다.

```
행 0: 이동 없음     [d4, e0, b8, 1e] → [d4, e0, b8, 1e]
행 1: 1칸 이동      [27, bf, b4, 41] → [bf, b4, 41, 27]
행 2: 2칸 이동      [11, 98, 5d, 52] → [5d, 52, 11, 98]
행 3: 3칸 이동      [ae, f1, e5, 30] → [30, ae, f1, e5]
```

**MixColumns** — 각 열을 GF(2^8) 위의 다항식 곱셈으로 혼합한다. 한 바이트가 바뀌면 같은 열의 4바이트 전부가 바뀐다.

**AddRoundKey** — 상태 행렬과 라운드 키를 XOR한다. 키 스케줄링으로 원래 키에서 각 라운드 키를 파생한다.

## 패딩 (Padding)

AES는 128비트(16바이트) 블록 단위로 처리한다. 평문 길이가 16바이트의 배수가 아니면 패딩을 붙여야 한다.

### PKCS5 vs PKCS7

```
평문: "Hello" (5바이트)
블록 크기: 16바이트
부족한 바이트: 11바이트

PKCS7 패딩 결과:
[H][e][l][l][o][0B][0B][0B][0B][0B][0B][0B][0B][0B][0B][0B]
                └── 부족한 바이트 수(11 = 0x0B)를 값으로 채움 ──┘

평문이 정확히 16바이트인 경우:
→ 16바이트짜리 패딩 블록을 하나 더 추가한다
[원본 16바이트][10][10][10]...[10]  (0x10 = 16)
```

| 항목 | PKCS5 | PKCS7 |
|------|-------|-------|
| 블록 크기 | 8바이트 고정 | 1~255바이트 |
| 규격 출처 | PKCS#5 (패스워드 기반) | PKCS#7 (CMS) |
| AES에서 사용 | 불가 (블록 크기 불일치) | 사용 |

Java에서 `PKCS5Padding`이라고 써도 내부적으로 PKCS7과 동일하게 동작한다. Java의 JCE가 이름만 PKCS5로 쓰고 실제로는 PKCS7 로직을 적용하기 때문이다. 헷갈리는 부분이지만, Java에서는 `AES/CBC/PKCS5Padding`으로 쓰면 된다.

### GCM 모드와 패딩

GCM 모드는 스트림 암호 방식(CTR 기반)이라 패딩이 필요 없다. Java에서 GCM을 쓸 때 `NoPadding`을 지정한다.

```
AES/GCM/NoPadding   ← 맞음
AES/GCM/PKCS5Padding ← 틀림, 예외 발생
```

## AES 운영 모드

### 모드별 동작 도식

**ECB (Electronic Codebook) — 사용 금지**

```
평문 블록1    평문 블록2    평문 블록3
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────┐
│AES 암호화│  │AES 암호화│  │AES 암호화│   ← 전부 같은 키
└────┬───┘  └────┬───┘  └────┬───┘
     │            │            │
     ▼            ▼            ▼
암호문 블록1  암호문 블록2  암호문 블록3

문제: 평문 블록1 == 평문 블록2이면 암호문도 동일
→ 이미지 암호화 시 윤곽이 그대로 보이는 현상 발생
```

ECB로 이미지를 암호화하면 원본 이미지의 패턴이 암호문에서도 보인다. 유명한 "ECB 펭귄" 예시가 이 문제를 잘 보여준다. 실무에서 ECB를 쓸 이유는 없다.

**CBC (Cipher Block Chaining)**

```
    IV          암호문 블록1     암호문 블록2
    │               │               │
    ▼               ▼               ▼
평문 블록1─→XOR  평문 블록2─→XOR  평문 블록3─→XOR
              │               │               │
              ▼               ▼               ▼
         ┌────────┐     ┌────────┐     ┌────────┐
         │AES 암호화│     │AES 암호화│     │AES 암호화│
         └────┬───┘     └────┬───┘     └────┬───┘
              │               │               │
              ▼               ▼               ▼
         암호문 블록1     암호문 블록2     암호문 블록3

특징: 이전 암호문 블록을 다음 블록의 입력에 섞음
→ 같은 평문이라도 다른 암호문 생성
→ 병렬 암호화 불가 (순차 처리)
→ 병렬 복호화는 가능
```

**GCM (Galois/Counter Mode) — 실무 권장**

```
     Nonce(96비트) + Counter
              │
              ▼
         ┌────────┐
         │AES 암호화│
         └────┬───┘
              │
              ▼
평문 블록──→XOR──→ 암호문 블록 ──┐
                                │
                                ▼
                         ┌────────────┐
              AAD ──────→│ GHASH 연산  │
                         └──────┬─────┘
                                │
                                ▼
                         인증 태그 (128비트)

AAD: Additional Authenticated Data
→ 암호화하지 않지만 무결성은 검증하는 데이터
→ HTTP 헤더 등을 AAD로 넣는 경우가 있다
```

### 모드 비교

| 모드 | IV/Nonce | 인증 | 병렬 암호화 | 병렬 복호화 | 패딩 |
|------|----------|------|------------|------------|------|
| ECB | 불필요 | 없음 | 가능 | 가능 | 필요 |
| CBC | IV 16바이트 | 없음 | 불가 | 가능 | 필요 |
| CTR | Nonce | 없음 | 가능 | 가능 | 불필요 |
| GCM | Nonce 12바이트 | 있음 | 가능 | 가능 | 불필요 |

GCM이 실무에서 표준이 된 이유: 암호화와 무결성 검증을 한 번에 처리하고, 병렬 처리가 가능해서 성능도 좋다. 별도로 HMAC을 붙일 필요가 없다.

## IV (Initialization Vector)

IV는 암호화 시 사용하는 추가 입력값이다. 같은 키로 여러 메시지를 암호화할 때 결과가 달라지도록 만든다.

- CBC: 16바이트 IV, 암호학적 난수 생성기로 생성
- GCM: 12바이트 Nonce, 카운터나 난수로 생성

IV를 재사용하면 같은 평문이 같은 암호문으로 나온다. GCM에서 Nonce를 재사용하면 인증 키가 노출되어 전체 보안이 무너진다. Nonce 재사용은 GCM에서 치명적이다.

## Salt

Salt는 패스워드 기반 키 유도(PBKDF2 등)에서 사용하는 랜덤 데이터다. 같은 패스워드라도 다른 키를 만들어낸다.

| 항목 | IV | Salt |
|------|-----|------|
| 목적 | 암호화 랜덤성 | 키 유도 랜덤성 |
| 사용처 | AES 블록 암호화 | PBKDF2, scrypt 등 |
| 크기 | 블록/모드에 따라 결정 | 16바이트 이상 |
| 공개 여부 | 공개 가능 | 공개 가능 |
| 재사용 | 금지 | 금지 |

## Java 구현

### AES-GCM (권장)

```java
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

public class AesGcmCrypto {

    private static final int GCM_TAG_LENGTH = 128; // 비트
    private static final int GCM_NONCE_LENGTH = 12; // 바이트

    // 키 생성
    public static SecretKey generateKey() throws Exception {
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(256);
        return keyGen.generateKey();
    }

    // 암호화
    public static byte[] encrypt(byte[] plaintext, SecretKey key) throws Exception {
        byte[] nonce = new byte[GCM_NONCE_LENGTH];
        SecureRandom random = new SecureRandom();
        random.nextBytes(nonce);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, nonce);
        cipher.init(Cipher.ENCRYPT_MODE, key, spec);

        byte[] ciphertext = cipher.doFinal(plaintext);

        // nonce + ciphertext(암호문 + 인증태그)를 합쳐서 반환
        byte[] result = new byte[nonce.length + ciphertext.length];
        System.arraycopy(nonce, 0, result, 0, nonce.length);
        System.arraycopy(ciphertext, 0, result, nonce.length, ciphertext.length);
        return result;
    }

    // 복호화
    public static byte[] decrypt(byte[] encrypted, SecretKey key) throws Exception {
        // 앞 12바이트가 nonce
        byte[] nonce = new byte[GCM_NONCE_LENGTH];
        System.arraycopy(encrypted, 0, nonce, 0, nonce.length);

        byte[] ciphertext = new byte[encrypted.length - nonce.length];
        System.arraycopy(encrypted, nonce.length, ciphertext, 0, ciphertext.length);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, nonce);
        cipher.init(Cipher.DECRYPT_MODE, key, spec);

        return cipher.doFinal(ciphertext); // 인증 실패 시 AEADBadTagException 발생
    }

    public static void main(String[] args) throws Exception {
        SecretKey key = generateKey();

        String message = "민감한 개인정보 데이터";
        byte[] encrypted = encrypt(message.getBytes("UTF-8"), key);
        byte[] decrypted = decrypt(encrypted, key);

        System.out.println("원문: " + message);
        System.out.println("암호문: " + Base64.getEncoder().encodeToString(encrypted));
        System.out.println("복호문: " + new String(decrypted, "UTF-8"));
    }
}
```

`doFinal()`에서 인증 태그 검증에 실패하면 `AEADBadTagException`이 발생한다. 이 예외를 잡아서 "복호화 실패"로 처리해야 한다. 구체적인 오류 원인을 클라이언트에 노출하면 안 된다 (Padding Oracle Attack 참고).

### AES-CBC (레거시 시스템 호환)

```java
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;

public class AesCbcCrypto {

    public static byte[] encrypt(byte[] plaintext, byte[] keyBytes) throws Exception {
        SecretKeySpec key = new SecretKeySpec(keyBytes, "AES");

        byte[] iv = new byte[16];
        new SecureRandom().nextBytes(iv);
        IvParameterSpec ivSpec = new IvParameterSpec(iv);

        // Java에서 PKCS5Padding이라고 써도 내부적으로 PKCS7 동작
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key, ivSpec);
        byte[] ciphertext = cipher.doFinal(plaintext);

        // IV + 암호문을 합쳐서 반환
        byte[] result = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, result, 0, iv.length);
        System.arraycopy(ciphertext, 0, result, iv.length, ciphertext.length);
        return result;
    }

    public static byte[] decrypt(byte[] encrypted, byte[] keyBytes) throws Exception {
        SecretKeySpec key = new SecretKeySpec(keyBytes, "AES");

        byte[] iv = new byte[16];
        System.arraycopy(encrypted, 0, iv, 0, iv.length);

        byte[] ciphertext = new byte[encrypted.length - iv.length];
        System.arraycopy(encrypted, iv.length, ciphertext, 0, ciphertext.length);

        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher.init(Cipher.DECRYPT_MODE, key, new IvParameterSpec(iv));
        return cipher.doFinal(ciphertext);
    }
}
```

새로 만드는 시스템이면 CBC 대신 GCM을 쓴다. CBC는 암호화만 하고 무결성 검증은 하지 않는다. 암호문이 변조되어도 복호화 자체는 진행되고, 잘못된 평문이 나올 수 있다.

### 패스워드 기반 키 유도 (PBKDF2)

사용자가 입력한 패스워드에서 AES 키를 만들어야 하는 경우:

```java
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;

public class PasswordBasedKey {

    public static SecretKeySpec deriveKey(String password, byte[] salt) throws Exception {
        PBEKeySpec spec = new PBEKeySpec(
            password.toCharArray(),
            salt,
            310_000,  // 반복 횟수 — OWASP 2023 권장값
            256       // 키 길이 (비트)
        );

        SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
        byte[] keyBytes = factory.generateSecret(spec).getEncoded();
        spec.clearPassword(); // 메모리에서 패스워드 제거

        return new SecretKeySpec(keyBytes, "AES");
    }

    public static byte[] generateSalt() {
        byte[] salt = new byte[16];
        new SecureRandom().nextBytes(salt);
        return salt;
    }
}
```

`PBEKeySpec.clearPassword()`를 반드시 호출한다. GC 전까지 메모리에 패스워드가 남아있으면 힙 덤프 공격에 취약하다.

## Spring Boot에서 AES 적용

### 설정 관리

```yaml
# application.yml
encryption:
  aes:
    key: ${AES_ENCRYPTION_KEY}  # 환경 변수로 주입
```

```java
@Configuration
@ConfigurationProperties(prefix = "encryption.aes")
public class EncryptionConfig {

    private String key;

    public SecretKeySpec getSecretKey() {
        byte[] keyBytes = Base64.getDecoder().decode(key);
        if (keyBytes.length != 32) {
            throw new IllegalStateException(
                "AES 키는 32바이트(256비트)여야 한다. 현재: " + keyBytes.length + "바이트"
            );
        }
        return new SecretKeySpec(keyBytes, "AES");
    }

    // getter, setter
    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }
}
```

### 암복호화 서비스

```java
@Service
public class EncryptionService {

    private final SecretKeySpec secretKey;

    public EncryptionService(EncryptionConfig config) {
        this.secretKey = config.getSecretKey();
    }

    public String encrypt(String plaintext) {
        try {
            byte[] encrypted = AesGcmCrypto.encrypt(
                plaintext.getBytes(StandardCharsets.UTF_8), secretKey
            );
            return Base64.getEncoder().encodeToString(encrypted);
        } catch (Exception e) {
            throw new EncryptionException("암호화 실패", e);
        }
    }

    public String decrypt(String encryptedBase64) {
        try {
            byte[] encrypted = Base64.getDecoder().decode(encryptedBase64);
            byte[] decrypted = AesGcmCrypto.decrypt(encrypted, secretKey);
            return new String(decrypted, StandardCharsets.UTF_8);
        } catch (AEADBadTagException e) {
            // 인증 실패 — 원인을 구체적으로 노출하지 않는다
            throw new EncryptionException("복호화 실패");
        } catch (Exception e) {
            throw new EncryptionException("복호화 실패", e);
        }
    }
}
```

### 주의사항

**Cipher 인스턴스 재사용 금지**

`Cipher` 객체는 스레드 안전하지 않다. `@Service`에서 필드로 `Cipher`를 잡아두고 여러 요청에서 재사용하면 데이터가 꼬인다.

```java
// 잘못된 예 — 멀티스레드 환경에서 문제 발생
@Service
public class BadEncryptionService {
    private final Cipher cipher; // 필드로 보관하면 안 됨

    public BadEncryptionService() throws Exception {
        this.cipher = Cipher.getInstance("AES/GCM/NoPadding");
    }
}

// 올바른 예 — 매번 새로 생성
public byte[] encrypt(byte[] data) throws Exception {
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    // ...
}
```

**키 로테이션**

운영 환경에서 암호화 키를 교체해야 하는 상황이 온다. 키 버전을 암호문 앞에 붙여두면 교체가 수월하다.

```java
// 암호문 형식: [키버전 1바이트][nonce 12바이트][암호문+태그]
public byte[] encryptWithVersion(byte[] plaintext, int keyVersion) throws Exception {
    SecretKey key = getKeyByVersion(keyVersion);
    byte[] encrypted = AesGcmCrypto.encrypt(plaintext, key);

    byte[] result = new byte[1 + encrypted.length];
    result[0] = (byte) keyVersion;
    System.arraycopy(encrypted, 0, result, 1, encrypted.length);
    return result;
}

public byte[] decryptWithVersion(byte[] data) throws Exception {
    int keyVersion = data[0] & 0xFF;
    byte[] encrypted = new byte[data.length - 1];
    System.arraycopy(data, 1, encrypted, 0, encrypted.length);

    SecretKey key = getKeyByVersion(keyVersion);
    return AesGcmCrypto.decrypt(encrypted, key);
}
```

**JPA AttributeConverter 적용**

DB 컬럼 단위로 암호화할 때 `AttributeConverter`를 쓸 수 있다.

```java
@Converter
public class EncryptedStringConverter implements AttributeConverter<String, String> {

    // ApplicationContext에서 가져오거나 직접 주입
    // JPA Converter는 Spring Bean 주입이 까다로움 — 아래 참고
    private final EncryptionService encryptionService;

    public EncryptedStringConverter() {
        this.encryptionService = ApplicationContextHolder.getBean(EncryptionService.class);
    }

    @Override
    public String convertToDatabaseColumn(String attribute) {
        if (attribute == null) return null;
        return encryptionService.encrypt(attribute);
    }

    @Override
    public String convertToEntityAttribute(String dbData) {
        if (dbData == null) return null;
        return encryptionService.decrypt(dbData);
    }
}
```

```java
@Entity
public class User {
    @Convert(converter = EncryptedStringConverter.class)
    @Column(length = 512) // 암호문은 원문보다 길다 — 컬럼 크기 넉넉히
    private String phoneNumber;
}
```

JPA `@Converter`에는 Spring의 `@Autowired`가 기본적으로 동작하지 않는다. `ApplicationContextAware`를 구현한 유틸 클래스를 만들어서 빈을 가져오거나, Hibernate 5.3+ `@Converter(autoApply = false)`와 Spring의 `SpringBeanContainer`를 설정해야 한다.

암호화된 컬럼은 DB에서 `LIKE` 검색이 안 된다. 검색이 필요한 필드는 별도 해시 컬럼을 만들어 인덱싱하는 방식을 쓴다.

## 실무 트러블슈팅

### Padding Oracle Attack

CBC 모드에서 발생하는 공격이다. 서버가 패딩 오류와 다른 오류를 구분해서 응답하면, 공격자가 이 차이를 이용해 암호문을 한 바이트씩 복호화할 수 있다.

```
공격 원리:

1. 공격자가 변조된 암호문을 서버에 보냄
2. 서버가 복호화 시도
3-a. 패딩이 올바르면 → "복호화 성공" 또는 "데이터 오류"
3-b. 패딩이 틀리면 → "패딩 오류"           ← 이 차이가 문제

공격자는 3-a와 3-b의 응답 차이를 이용해
암호문의 중간값(intermediate value)을 알아낸다.
중간값을 알면 평문을 역산할 수 있다.
```

**대응 방법:**

1. GCM 모드를 사용한다 — 인증 태그가 먼저 검증되므로 패딩 단계까지 가지 않는다
2. CBC를 써야 하는 경우, 복호화 실패 시 원인과 무관하게 동일한 오류를 반환한다

```java
// 잘못된 예 — 패딩 오류를 구분해서 응답
try {
    return cipher.doFinal(ciphertext);
} catch (BadPaddingException e) {
    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "잘못된 패딩");
} catch (Exception e) {
    throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "서버 오류");
}

// 올바른 예 — 모든 복호화 실패를 동일하게 처리
try {
    return cipher.doFinal(ciphertext);
} catch (Exception e) {
    // 로그에만 상세 원인 기록
    log.warn("복호화 실패: {}", e.getMessage());
    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "복호화 실패");
}
```

응답 시간도 일정해야 한다. 패딩 검증 실패가 다른 오류보다 빠르게 응답하면 타이밍 공격이 가능하다.

### 키가 바뀌었을 때 기존 데이터 복호화 실패

운영 중에 키를 교체하면 기존 암호문을 복호화할 수 없다. 키 로테이션 시 기존 데이터를 새 키로 재암호화하는 배치 작업이 필요하다. 키 버전 관리를 처음부터 해두면 이 과정이 간단해진다.

### Base64 인코딩 불일치

서버와 클라이언트 간에 Base64 변형이 다른 경우가 있다. 표준 Base64와 URL-safe Base64(`+/` → `-_`)가 섞이면 복호화가 실패한다.

```java
// 표준 Base64
Base64.getEncoder().encodeToString(data);

// URL-safe Base64
Base64.getUrlEncoder().withoutPadding().encodeToString(data);

// 어느 쪽인지 API 문서에 명시하고, 양쪽이 같은 방식을 써야 한다
```

### SecureRandom 초기화 지연

Linux에서 `SecureRandom`이 `/dev/random`을 읽으면 엔트로피 부족으로 블로킹될 수 있다. 컨테이너 환경에서 서버 기동 시간이 느려지는 원인이 되기도 한다.

```bash
# JVM 옵션으로 /dev/urandom 사용 (실무에서 일반적)
-Djava.security.egd=file:/dev/./urandom
```

`/dev/urandom`은 블로킹하지 않으면서도 암호학적으로 충분히 안전하다. `/dev/random`과의 보안 차이는 현대 Linux 커널에서 사실상 없다.

## Node.js 구현

```javascript
const crypto = require('crypto');

class AesGcmCrypto {
    constructor(key) {
        // key: 32바이트 Buffer
        this.key = Buffer.isBuffer(key) ? key : Buffer.from(key, 'hex');
    }

    encrypt(plaintext) {
        const nonce = crypto.randomBytes(12);
        const cipher = crypto.createCipheriv('aes-256-gcm', this.key, nonce);

        let encrypted = cipher.update(plaintext, 'utf8');
        encrypted = Buffer.concat([encrypted, cipher.final()]);
        const authTag = cipher.getAuthTag();

        // nonce(12) + authTag(16) + ciphertext
        return Buffer.concat([nonce, authTag, encrypted]);
    }

    decrypt(data) {
        const buf = Buffer.isBuffer(data) ? data : Buffer.from(data, 'base64');

        const nonce = buf.subarray(0, 12);
        const authTag = buf.subarray(12, 28);
        const ciphertext = buf.subarray(28);

        const decipher = crypto.createDecipheriv('aes-256-gcm', this.key, nonce);
        decipher.setAuthTag(authTag);

        let decrypted = decipher.update(ciphertext);
        decrypted = Buffer.concat([decrypted, decipher.final()]);
        return decrypted.toString('utf8');
    }
}

const key = crypto.randomBytes(32);
const aes = new AesGcmCrypto(key);

const encrypted = aes.encrypt('Hello, AES-GCM!');
console.log('암호문:', encrypted.toString('base64'));
console.log('복호문:', aes.decrypt(encrypted));
```

## 보안 고려사항

### 키 관리

| 방식 | 적합한 상황 | 주의점 |
|------|------------|--------|
| 환경 변수 | 개발/소규모 서비스 | 프로세스 목록에서 노출 가능 |
| AWS KMS / GCP KMS | 클라우드 운영 | API 호출 비용, 레이턴시 |
| HashiCorp Vault | 온프레미스/멀티클라우드 | 운영 복잡도 |
| HSM | 금융/규제 환경 | 비용 높음 |

키를 코드에 하드코딩하면 Git 히스토리에 남는다. 한번 커밋된 키는 히스토리를 정리하더라도 이미 노출된 것으로 간주하고 교체해야 한다.

### AES vs 다른 암호화

| 알고리즘 | 유형 | 특징 | 용도 |
|---------|------|------|------|
| AES | 대칭키 | 빠름, 하드웨어 가속(AES-NI) | 데이터 암호화 |
| RSA | 비대칭키 | 느림, 키 크기 큼 | 키 교환, 서명 |
| ChaCha20-Poly1305 | 대칭키 | AES-NI 없는 환경에서 빠름 | 모바일, TLS |

실무에서는 대용량 데이터를 AES로 암호화하고, AES 키를 RSA로 암호화하는 하이브리드 방식을 쓴다. TLS가 이 방식으로 동작한다.

## 참고

- NIST FIPS 197 — AES Specification
- RFC 5116 — An Interface and Algorithms for Authenticated Encryption
- RFC 3602 — The AES-CBC Cipher Algorithm
- OWASP Cryptographic Storage Cheat Sheet
