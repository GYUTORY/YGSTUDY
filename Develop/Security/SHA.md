---
title: SHA (Secure Hash Algorithm) 해시 함수 가이드
tags: [security, sha, hash, cryptography, integrity, bcrypt, argon2]
updated: 2026-03-01
---

# SHA (Secure Hash Algorithm)

## 개요

SHA는 미국 NSA가 설계하고 NIST가 표준화한 **암호학적 해시 함수** 군이다. 임의 길이의 데이터를 **고정 길이의 해시값**으로 변환한다. 일방향 함수이므로 해시값에서 원본 데이터를 역산할 수 없다.

### 해시 함수의 핵심 성질

| 성질 | 설명 |
|------|------|
| **결정성** | 같은 입력 → 항상 같은 출력 |
| **고정 길이 출력** | 입력 크기와 무관하게 일정한 길이 |
| **눈사태 효과** | 입력이 1비트만 변해도 출력이 완전히 달라짐 |
| **역상 저항성** | 해시값으로부터 원본을 찾기 불가능 |
| **충돌 저항성** | 같은 해시를 만드는 두 입력을 찾기 불가능 |

```
입력: "hello world"  →  SHA-256  →  b94d27b9934d3e08...  (64자 16진수)
입력: "hello worle"  →  SHA-256  →  3f2e7d95b319a14b...  (완전히 다름!)
```

## 핵심

### 1. SHA 계열 비교

| 알고리즘 | 출력 크기 | 상태 | 용도 |
|---------|----------|------|------|
| **SHA-1** | 160비트 | ❌ 취약 (2017년 충돌 발견) | 사용 금지 |
| **SHA-256** | 256비트 | ✅ 안전 | 일반 해싱, 블록체인 |
| **SHA-384** | 384비트 | ✅ 안전 | TLS 인증서 |
| **SHA-512** | 512비트 | ✅ 안전 | 높은 보안 요구 |
| **SHA-3** | 가변 | ✅ 안전 (최신) | SHA-2 대안 |

📌 **실무 기준**: 대부분 **SHA-256**이면 충분하다. SHA-1은 절대 사용하지 않는다.

### 2. SHA-256 동작 원리

#### 처리 과정

```
원본 데이터 → 바이너리 변환 → 패딩 → 512비트 블록 분할 → 압축 → 해시값
```

1. **바이너리 변환**: 문자열을 ASCII → 이진수로 변환
2. **패딩**: 데이터 끝에 `1` 추가 후 `0`으로 채워 448비트로 맞춤. 마지막 64비트에 원본 길이 기록
3. **블록 분할**: 512비트 단위로 분할
4. **메시지 스케줄**: 16개 워드를 64개 워드로 확장
5. **압축 함수**: 초기 해시값(H0~H7)에 대해 64라운드 압축 수행
6. **최종 해시**: 256비트(32바이트) 해시값 출력

### 3. 실무 사용 예시

#### 데이터 무결성 검증

```java
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

public class HashUtil {

    public static String sha256(String data) {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(data.getBytes(StandardCharsets.UTF_8));

        // 바이트 배열 → 16진수 문자열
        StringBuilder hexString = new StringBuilder();
        for (byte b : hash) {
            hexString.append(String.format("%02x", b));
        }
        return hexString.toString();
    }
}
```

```javascript
// Node.js
const crypto = require('crypto');

function sha256(data) {
    return crypto.createHash('sha256').update(data).digest('hex');
}

// 파일 무결성 검증
const fs = require('fs');
function fileHash(filePath) {
    const data = fs.readFileSync(filePath);
    return crypto.createHash('sha256').update(data).digest('hex');
}
```

#### HMAC (Hash-based Message Authentication Code)

SHA에 **비밀 키**를 추가하여 메시지 인증을 수행한다.

```java
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public static String hmacSha256(String data, String secret) {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(secret.getBytes(), "HmacSHA256"));
    byte[] hash = mac.doFinal(data.getBytes());
    return bytesToHex(hash);
}
```

```
SHA-256:       hash(message)                → 무결성 검증
HMAC-SHA-256:  hash(secret + message)       → 무결성 + 인증
```

### 4. 비밀번호 해싱은 SHA가 아니다

**SHA-256은 비밀번호 해싱에 부적합**하다. SHA는 속도가 빠르도록 설계되었기 때문에 brute force 공격에 취약하다.

| 알고리즘 | 용도 | 속도 | 비밀번호 해싱 |
|---------|------|------|-------------|
| **SHA-256** | 데이터 무결성 | 매우 빠름 | ❌ 부적합 |
| **BCrypt** | 비밀번호 해싱 | 의도적으로 느림 | ✅ 권장 |
| **Argon2** | 비밀번호 해싱 | 의도적으로 느림 + 메모리 사용 | ✅ 최신 권장 |
| **PBKDF2** | 비밀번호 해싱 | 반복으로 느리게 | ✅ FIPS 호환 |

```java
// ❌ 절대 이렇게 하지 않는다
String hashed = sha256(password);                     // brute force에 취약

// ✅ BCrypt 사용 (Spring Security)
String hashed = new BCryptPasswordEncoder().encode(password);

// ✅ Argon2 사용
String hashed = new Argon2PasswordEncoder(16, 32, 1, 65536, 3).encode(password);
```

### 5. SHA 사용 정리

| 용도 | 적합한 알고리즘 |
|------|---------------|
| **파일 무결성** | SHA-256 |
| **API 서명 검증** | HMAC-SHA-256 |
| **디지털 인증서** | SHA-256, SHA-384 |
| **블록체인** | SHA-256 (Bitcoin) |
| **비밀번호 저장** | BCrypt, Argon2 (SHA 사용 금지) |
| **JWT 서명** | HMAC-SHA-256, RS256 |
| **Git 커밋 해시** | SHA-1 → SHA-256 이전 중 |

## 참고

- [NIST FIPS 180-4 (SHA 표준)](https://csrc.nist.gov/publications/detail/fips/180/4/final)
- [AES 암호화](AES.md) — 대칭키 암호화
- [RSA 암호화](RSA.md) — 비대칭키 암호화
- [Spring Security](../Framework/Java/Spring/Spring_Security.md) — BCrypt 사용법
