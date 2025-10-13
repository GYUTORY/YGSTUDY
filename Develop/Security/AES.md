---
title: AES Advanced Encryption Standard
tags: [security, aes, encryption, cryptography]
updated: 2025-10-13
---

# AES (Advanced Encryption Standard)

## 📋 목차
1. [AES 기본 개념](#aes-기본-개념)
2. [AES 알고리즘 구조](#aes-알고리즘-구조)
3. [IV (Initialization Vector) 완전 이해](#iv-initialization-vector-완전-이해)
4. [Salt 완전 이해](#salt-완전-이해)
5. [AES 운영 모드](#aes-운영-모드)
6. [보안 고려사항](#보안-고려사항)
7. [실제 구현 예시](#실제-구현-예시)
8. [다른 암호화 알고리즘과의 비교](#다른-암호화-알고리즘과의-비교)

---

## AES 기본 개념

### AES란 무엇인가?
**AES (Advanced Encryption Standard)**는 2001년 NIST(미국 국립표준기술연구소)에 의해 채택된 현대적인 대칭키 암호화 알고리즘입니다.

#### 핵심 특징
- **대칭키 암호화**: 암호화와 복호화에 같은 키 사용
- **블록 암호**: 128비트 블록 단위로 데이터 처리
- **표준 알고리즘**: 전 세계적으로 널리 사용되는 암호화 표준
- **고성능**: 하드웨어와 소프트웨어 모두에서 효율적

### 역사적 배경
```
1997년 → NIST가 DES 대체 알고리즘 공모
1998년 → 15개 후보 알고리즘 제출
1999년 → 5개 최종 후보 선정 (MARS, RC6, Rijndael, Serpent, Twofish)
2000년 → Rijndael 알고리즘이 AES로 선정
2001년 → NIST 표준으로 공식 채택
```

### 왜 AES가 중요한가?
1. **DES의 한계 극복**: 56비트 키의 약한 보안성 해결
2. **현대적 보안**: 128/192/256비트 키로 강력한 보안 제공
3. **광범위한 사용**: 정부, 금융, IT 기업에서 표준으로 사용
4. **지속적 검증**: 20년 이상 공격에 저항하며 검증됨

---

## AES 알고리즘 구조

### 키 길이와 라운드 수
| 키 길이 | 라운드 수 | 보안 강도 | 사용 권장도 |
|---------|-----------|-----------|-------------|
| 128비트 | 10라운드 | 높음 | 일반적 사용 |
| 192비트 | 12라운드 | 매우 높음 | 고보안 요구 |
| 256비트 | 14라운드 | 최고 | 극비 정보 |

### 블록 구조
- **블록 크기**: 고정 128비트 (16바이트)
- **상태 행렬**: 4x4 바이트 배열로 표현
- **데이터 흐름**: 평문 → 상태 행렬 → 암호문

### 암호화 과정 (SPN 구조)
```
평문 입력
    ↓
초기 라운드 (AddRoundKey)
    ↓
라운드 1~9 (SubBytes → ShiftRows → MixColumns → AddRoundKey)
    ↓
최종 라운드 (SubBytes → ShiftRows → AddRoundKey)
    ↓
암호문 출력
```

### 라운드 함수 상세

#### 1. SubBytes (바이트 치환)
- **목적**: 비선형성 제공
- **방법**: S-box를 사용한 바이트 단위 치환
- **특징**: 대수적 구조 기반, 역연산 가능

#### 2. ShiftRows (행 이동)
- **목적**: 확산성 제공
- **방법**: 각 행을 다른 거리만큼 순환 이동
  - 1행: 0바이트 이동
  - 2행: 1바이트 왼쪽 이동
  - 3행: 2바이트 왼쪽 이동
  - 4행: 3바이트 왼쪽 이동

#### 3. MixColumns (열 혼합)
- **목적**: 열 간의 혼합
- **방법**: Galois Field GF(2^8)에서의 다항식 곱셈
- **예외**: 마지막 라운드에서는 생략

#### 4. AddRoundKey (라운드 키 추가)
- **목적**: 키와의 결합
- **방법**: 상태 행렬과 라운드 키의 XOR 연산
- **특징**: 각 라운드마다 다른 키 사용

---

## IV (Initialization Vector) 완전 이해

### IV란 무엇인가?
**IV (Initialization Vector)**는 암호화 과정에서 사용되는 추가적인 입력값으로, **같은 키로 여러 메시지를 암호화할 때 보안성을 높이기 위해 사용**됩니다.

### 🤔 왜 IV가 필요한가?

#### 문제 상황: IV가 없다면?
```
같은 키로 암호화:
"Hello World" → "A1B2C3D4E5F6..."
"Hello World" → "A1B2C3D4E5F6..."  ← 동일한 결과!

공격자가 알 수 있는 것:
- 같은 평문이 같은 암호문을 만든다
- 패턴 분석이 가능하다
- 암호화의 보안성이 크게 약화된다
```

#### 해결책: IV 사용
```
같은 키, 다른 IV로 암호화:
"Hello World" + IV1 → "X9Y8Z7W6V5U4..."
"Hello World" + IV2 → "M3N4O5P6Q7R8..."  ← 다른 결과!

결과:
- 같은 평문도 다른 암호문 생성
- 패턴 분석 불가능
- 보안성 크게 향상
```

### IV의 핵심 특징

#### 1. 크기와 형식
- **AES 표준**: 16바이트 (128비트)
- **이유**: AES 블록 크기와 동일
- **형식**: 바이트 배열 (Uint8Array, byte[] 등)

#### 2. 생성 원칙
- **암호학적 안전성**: 예측 불가능한 난수 생성기 사용
- **유일성**: 매 암호화마다 새로운 IV 생성
- **랜덤성**: 완전히 랜덤한 값이어야 함

#### 3. 보안적 중요성
- **IV 재사용 금지**: 같은 IV 재사용 시 심각한 보안 취약점
- **패턴 방지**: 같은 평문이 다른 암호문을 생성하도록 보장
- **공격 방어**: 선택 평문 공격(CPA) 방어

### IV 사용 시나리오

#### 시나리오 1: 파일 암호화
```
파일 A: "중요한 문서 내용"
파일 B: "중요한 문서 내용"  ← 같은 내용

IV 없이:
파일 A → "ABC123..."
파일 B → "ABC123..."  ← 동일! 위험!

IV 사용:
파일 A + IV1 → "XYZ789..."
파일 B + IV2 → "DEF456..."  ← 안전!
```

#### 시나리오 2: 데이터베이스 암호화
```
사용자 테이블:
ID | 이름 (암호화)
1  | "김철수" + IV1 → "A1B2C3..."
2  | "김철수" + IV2 → "X9Y8Z7..."  ← 같은 이름, 다른 암호문
```

### IV 저장 및 전송 방법

#### 방법 1: 암호문 앞에 붙이기 (권장)
```
최종 데이터 = IV + 암호문
[16바이트 IV][암호문 데이터]
```

#### 방법 2: 별도 전송
```
전송 1: IV (16바이트)
전송 2: 암호문
```

#### 방법 3: 인코딩하여 전송
```javascript
// Base64 인코딩
const ivBase64 = btoa(String.fromCharCode(...iv));

// Hex 인코딩
const ivHex = Array.from(iv)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
```

### IV 생성 코드 예시

#### JavaScript (Web Crypto API)
```javascript
// 안전한 IV 생성
const iv = crypto.getRandomValues(new Uint8Array(16));

// Base64로 인코딩
const ivBase64 = btoa(String.fromCharCode(...iv));
console.log('IV (Base64):', ivBase64);

// Hex로 인코딩
const ivHex = Array.from(iv)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
console.log('IV (Hex):', ivHex);
```

#### Python
```python
import os
import base64

# 안전한 IV 생성
iv = os.urandom(16)

# Base64로 인코딩
iv_base64 = base64.b64encode(iv).decode('utf-8')
print(f'IV (Base64): {iv_base64}')

# Hex로 인코딩
iv_hex = iv.hex()
print(f'IV (Hex): {iv_hex}')
```

#### Java
```java
import java.security.SecureRandom;
import java.util.Base64;

// 안전한 IV 생성
byte[] iv = new byte[16];
new SecureRandom().nextBytes(iv);

// Base64로 인코딩
String ivBase64 = Base64.getEncoder().encodeToString(iv);
System.out.println("IV (Base64): " + ivBase64);

// Hex로 인코딩
StringBuilder ivHex = new StringBuilder();
for (byte b : iv) {
    ivHex.append(String.format("%02x", b));
}
System.out.println("IV (Hex): " + ivHex.toString());
```

### ⚠️ IV 사용 시 주의사항

#### 1. 절대 하지 말아야 할 것
- ❌ IV 재사용
- ❌ 예측 가능한 IV (시간, 카운터 등)
- ❌ 고정된 IV 값
- ❌ 다른 키와 같은 IV 사용

#### 2. 반드시 해야 할 것
- ✅ 매번 새로운 IV 생성
- ✅ 암호학적으로 안전한 난수 생성기 사용
- ✅ IV를 암호문과 함께 저장/전송
- ✅ IV의 무결성 보장

### IV와 관련된 공격

#### 1. IV 재사용 공격
```
같은 키 + 같은 IV로 암호화:
평문1: "Hello" → 암호문1: "ABC123"
평문2: "World" → 암호문2: "DEF456"

공격자가 알 수 있는 것:
- 평문1 ⊕ 평문2 = 암호문1 ⊕ 암호문2
- 패턴 분석으로 원문 추측 가능
```

#### 2. 선택 IV 공격
```
공격자가 IV를 선택할 수 있는 경우:
- 특정 IV로 암호화 요청
- 결과를 분석하여 키 정보 추출
- 점진적으로 키 복원
```

### IV 모범 사례

#### 1. 생성
```javascript
// ✅ 올바른 방법
const iv = crypto.getRandomValues(new Uint8Array(16));

// ❌ 잘못된 방법
const iv = new Uint8Array(16).fill(0);  // 고정값
const iv = new Uint8Array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]);  // 예측 가능
```

#### 2. 저장
```javascript
// ✅ 올바른 방법: IV + 암호문
const result = {
    iv: ivBase64,
    ciphertext: ciphertextBase64
};

// ❌ 잘못된 방법: IV 없이 암호문만
const result = {
    ciphertext: ciphertextBase64  // IV 누락!
};
```

#### 3. 전송
```javascript
// ✅ 올바른 방법: 함께 전송
const encryptedData = ivBase64 + ':' + ciphertextBase64;

// ❌ 잘못된 방법: 별도 전송 (동기화 문제)
// IV를 먼저 보내고, 암호문을 나중에 보내면 순서 문제 발생 가능
```

---

## Salt 완전 이해

### Salt란 무엇인가?
**Salt**는 암호화나 해싱 과정에 추가되는 랜덤 데이터로, **특히 비밀번호 저장 시 보안성을 크게 향상**시키는 핵심 요소입니다.

### 🤔 왜 Salt가 필요한가?

#### 문제 상황: Salt가 없다면?
```
사용자들의 비밀번호:
사용자A: "password123" → SHA256 → "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
사용자B: "password123" → SHA256 → "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
사용자C: "password123" → SHA256 → "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"

공격자가 알 수 있는 것:
- 같은 비밀번호는 같은 해시값을 가진다
- 레인보우 테이블로 쉽게 역추적 가능
- 한 번 해킹하면 모든 같은 비밀번호가 노출
```

#### 해결책: Salt 사용
```
사용자들의 비밀번호 + Salt:
사용자A: "password123" + Salt1 → "a1b2c3d4e5f6..."
사용자B: "password123" + Salt2 → "x9y8z7w6v5u4..."
사용자C: "password123" + Salt3 → "m3n4o5p6q7r8..."

결과:
- 같은 비밀번호도 다른 해시값 생성
- 레인보우 테이블 공격 무력화
- 개별 사용자별 고유한 보안
```

### Salt의 핵심 특징

#### 1. 목적과 필요성
- **레인보우 테이블 공격 방지**: 미리 계산된 해시 테이블 공격 차단
- **해시값 다양화**: 같은 입력도 다른 출력 생성
- **사용자별 고유성**: 각 사용자마다 다른 Salt로 개별 보안
- **전역 공격 방지**: 한 번의 공격으로 모든 사용자 노출 방지

#### 2. 크기와 형식
- **권장 크기**: 16바이트 이상 (128비트 이상)
- **최소 크기**: 8바이트 (64비트)
- **형식**: 바이트 배열 (Uint8Array, byte[] 등)
- **엔트로피**: 충분한 랜덤성 보장

#### 3. 생성 원칙
- **암호학적 안전성**: 예측 불가능한 난수 생성기 사용
- **사용자별 유일성**: 각 사용자마다 고유한 Salt
- **일관성**: 한 번 생성되면 계정 생명주기 동안 유지
- **랜덤성**: 완전히 랜덤한 값이어야 함

### Salt 사용 시나리오

#### 시나리오 1: 비밀번호 저장
```
사용자 등록 시:
1. 사용자가 "mypassword123" 입력
2. 시스템이 Salt 생성: "a1b2c3d4e5f6g7h8"
3. 비밀번호 + Salt 해싱: hash("mypassword123" + "a1b2c3d4e5f6g7h8")
4. 데이터베이스에 저장: { userId, salt, hashedPassword }

로그인 시:
1. 사용자가 "mypassword123" 입력
2. 데이터베이스에서 해당 사용자의 Salt 조회
3. 입력 비밀번호 + Salt 해싱
4. 저장된 해시값과 비교
```

#### 시나리오 2: 키 파생 (PBKDF2)
```
AES 암호화 키 생성:
1. 사용자 비밀번호: "mysecretkey"
2. Salt 생성: "x9y8z7w6v5u4t3s2"
3. PBKDF2(비밀번호, Salt, 반복횟수, 해시함수)
4. 결과: AES 암호화에 사용할 키
```

### Salt 저장 및 관리

#### 방법 1: 데이터베이스에 함께 저장 (권장)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50),
    salt BINARY(16),           -- Salt 저장
    password_hash BINARY(32)   -- 해시된 비밀번호 저장
);
```

#### 방법 2: 해시값에 포함
```
방법: Salt + 해시값을 하나의 필드에 저장
저장 형식: [16바이트 Salt][32바이트 해시값]
장점: 하나의 필드로 관리
단점: Salt 추출 시 파싱 필요
```

#### 방법 3: 별도 테이블 관리
```sql
CREATE TABLE user_salts (
    user_id INT,
    salt BINARY(16),
    created_at TIMESTAMP
);
```

### Salt 생성 코드 예시

#### JavaScript (Web Crypto API)
```javascript
// Salt 생성
const salt = crypto.getRandomValues(new Uint8Array(16));

// Base64로 인코딩
const saltBase64 = btoa(String.fromCharCode(...salt));
console.log('Salt (Base64):', saltBase64);

// Hex로 인코딩
const saltHex = Array.from(salt)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
console.log('Salt (Hex):', saltHex);

// PBKDF2를 사용한 키 파생
async function deriveKeyWithSalt(password, salt) {
    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(password),
        { name: 'PBKDF2' },
        false,
        ['deriveKey']
    );

    return crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: salt,
            iterations: 100000,  // 반복 횟수
            hash: 'SHA-256'
        },
        keyMaterial,
        { name: 'AES-CBC', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );
}
```

#### Python
```python
import os
import hashlib
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Salt 생성
salt = os.urandom(16)

# Base64로 인코딩
salt_base64 = base64.b64encode(salt).decode('utf-8')
print(f'Salt (Base64): {salt_base64}')

# Hex로 인코딩
salt_hex = salt.hex()
print(f'Salt (Hex): {salt_hex}')

# PBKDF2를 사용한 키 파생
def derive_key_with_salt(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256비트 키
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    return key

# 사용 예시
password = "mysecretpassword"
key = derive_key_with_salt(password, salt)
print(f'Derived Key: {key.hex()}')
```

#### Java
```java
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.SecretKeyFactory;
import java.security.SecureRandom;
import java.security.spec.KeySpec;
import java.util.Base64;

public class SaltExample {
    
    // Salt 생성
    public static byte[] generateSalt() {
        byte[] salt = new byte[16];
        new SecureRandom().nextBytes(salt);
        return salt;
    }
    
    // PBKDF2를 사용한 키 파생
    public static byte[] deriveKey(String password, byte[] salt) throws Exception {
        KeySpec spec = new PBEKeySpec(password.toCharArray(), salt, 100000, 256);
        SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
        return factory.generateSecret(spec).getEncoded();
    }
    
    public static void main(String[] args) throws Exception {
        // Salt 생성
        byte[] salt = generateSalt();
        String saltBase64 = Base64.getEncoder().encodeToString(salt);
        System.out.println("Salt (Base64): " + saltBase64);
        
        // 키 파생
        String password = "mysecretpassword";
        byte[] key = deriveKey(password, salt);
        String keyHex = bytesToHex(key);
        System.out.println("Derived Key: " + keyHex);
    }
    
    private static String bytesToHex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte b : bytes) {
            result.append(String.format("%02x", b));
        }
        return result.toString();
    }
}
```

### ⚠️ Salt 사용 시 주의사항

#### 1. 절대 하지 말아야 할 것
- ❌ 모든 사용자에게 같은 Salt 사용
- ❌ 예측 가능한 Salt (사용자명, 이메일 등)
- ❌ 너무 짧은 Salt (8바이트 미만)
- ❌ Salt 재사용

#### 2. 반드시 해야 할 것
- ✅ 각 사용자마다 고유한 Salt 생성
- ✅ 충분한 길이의 Salt 사용 (16바이트 이상)
- ✅ 암호학적으로 안전한 난수 생성기 사용
- ✅ Salt를 안전하게 저장

### Salt와 관련된 공격

#### 1. 레인보우 테이블 공격
```
Salt 없이:
공격자가 미리 계산한 테이블:
"password123" → "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
"123456" → "e10adc3949ba59abbe56e057f20f883e"
...

Salt 사용 시:
각 사용자마다 다른 Salt로 인해 미리 계산된 테이블 무용지물
```

#### 2. 사전 공격 (Dictionary Attack)
```
Salt 없이:
공격자가 일반적인 비밀번호로 해시 계산 후 비교

Salt 사용 시:
각 사용자마다 다른 Salt로 인해 개별적으로 공격해야 함
공격 비용이 사용자 수만큼 증가
```

### Salt 모범 사례

#### 1. 생성
```javascript
// ✅ 올바른 방법
const salt = crypto.getRandomValues(new Uint8Array(16));

// ❌ 잘못된 방법
const salt = new Uint8Array(16).fill(0);  // 고정값
const salt = new TextEncoder().encode(username);  // 예측 가능
```

#### 2. 저장
```javascript
// ✅ 올바른 방법: Salt와 해시값 분리 저장
const userRecord = {
    id: userId,
    username: username,
    salt: saltBase64,
    passwordHash: hashBase64
};

// ❌ 잘못된 방법: Salt 없이 해시값만 저장
const userRecord = {
    id: userId,
    username: username,
    passwordHash: hashBase64  // Salt 누락!
};
```

#### 3. 검증
```javascript
// ✅ 올바른 방법: 저장된 Salt 사용
async function verifyPassword(inputPassword, storedSalt, storedHash) {
    const inputHash = await hashPassword(inputPassword, storedSalt);
    return inputHash === storedHash;
}

// ❌ 잘못된 방법: 새로운 Salt 생성
async function verifyPassword(inputPassword, storedHash) {
    const newSalt = crypto.getRandomValues(new Uint8Array(16));  // 잘못!
    const inputHash = await hashPassword(inputPassword, newSalt);
    return inputHash === storedHash;  // 항상 false
}
```

### Salt vs IV 비교

| 특징 | Salt | IV |
|------|------|-----|
| **목적** | 해시값 다양화, 레인보우 테이블 방지 | 암호화 패턴 방지 |
| **사용 시점** | 사용자 계정 생성 시 | 매 암호화마다 |
| **재사용** | 계정 생명주기 동안 유지 | 절대 재사용 금지 |
| **저장 위치** | 사용자 데이터베이스 | 암호문과 함께 |
| **크기** | 16바이트 이상 권장 | 16바이트 (AES) |
| **주요 용도** | 비밀번호 해싱, 키 파생 | 블록 암호화 |

---

## AES 운영 모드

### 운영 모드란?
AES는 블록 암호이므로 128비트 블록 단위로만 암호화할 수 있습니다. **운영 모드**는 더 큰 데이터를 안전하게 암호화하기 위한 방법을 제공합니다.

### 주요 운영 모드

#### 1. ECB (Electronic Codebook) - ⚠️ 사용 금지
```
특징:
- 각 블록을 독립적으로 암호화
- 가장 단순한 모드
- 패턴 노출 위험

문제점:
- 같은 평문 블록 → 같은 암호문 블록
- 이미지나 문서의 패턴이 그대로 노출
```

#### 2. CBC (Cipher Block Chaining) - ✅ 권장
```
특징:
- 이전 암호문 블록이 다음 평문 블록에 영향
- IV 필요
- 가장 널리 사용되는 모드

장점:
- 패턴 노출 방지
- 안전성 검증됨
```

#### 3. GCM (Galois/Counter Mode) - ✅ 최고 권장
```
특징:
- 인증 암호화 (Authenticated Encryption)
- 암호화와 무결성 검증을 동시에 수행
- 성능 우수

장점:
- 추가 인증 태그 제공
- CTR 모드 기반으로 병렬 처리 가능
```

#### 4. CTR (Counter Mode) - ✅ 권장
```
특징:
- 스트림 암호화 방식
- IV 대신 카운터 사용
- 병렬 처리 가능

장점:
- 하드웨어 가속에 최적화
- 임의 접근 가능
```

### 운영 모드 선택 가이드

| 용도 | 권장 모드 | 이유 |
|------|-----------|------|
| **일반적인 파일 암호화** | CBC | 안전하고 널리 지원 |
| **네트워크 통신** | GCM | 인증 암호화로 무결성 보장 |
| **대용량 데이터** | CTR | 병렬 처리로 성능 우수 |
| **실시간 스트리밍** | CTR | 임의 접근 가능 |
| **레거시 시스템** | CBC | 호환성 우수 |

---

## 보안 고려사항

### 1. 키 관리
#### 키 생성
- **암호학적 안전성**: 충분한 엔트로피를 가진 키 생성
- **키 길이**: 최소 128비트, 권장 256비트
- **생성 방법**: 암호학적으로 안전한 난수 생성기 사용

#### 키 저장
- **암호화 저장**: 키를 암호화하여 저장
- **HSM 사용**: 하드웨어 보안 모듈 활용
- **메모리 보호**: 사용 후 즉시 메모리에서 삭제

#### 키 교체
- **정기 교체**: 1-2년마다 키 교체
- **무중단 서비스**: 키 교체 시 서비스 중단 최소화
- **안전한 폐기**: 이전 키의 완전한 삭제

### 2. 패딩 (Padding)
#### PKCS#7 패딩 (권장)
```
원리:
- 블록 크기에 맞춰 패딩 추가
- 패딩 길이를 패딩 값으로 사용
- 복호화 시 패딩 자동 제거

예시:
"Hello" (5바이트) → "Hello\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B"
```

#### Zero 패딩 (비권장)
```
문제점:
- 원본 데이터에 0이 포함된 경우 구분 불가
- 패딩 제거 시 원본 데이터 손실 가능
```

### 3. 공격 방어
#### 부채널 공격 (Side-Channel Attacks)
- **타이밍 공격**: 상수 시간 연산으로 방어
- **전력 분석**: 노이즈 추가로 방어
- **메모리 분석**: 민감한 데이터 즉시 삭제

#### 선택 평문 공격 (CPA)
- **IV 무작위성**: 예측 불가능한 IV 사용
- **키 재사용 금지**: 각 세션마다 새로운 키
- **충분한 엔트로피**: 키와 IV의 랜덤성 보장

---

## 실제 구현 예시

### 완전한 AES 암호화 시스템

#### JavaScript (Web Crypto API)
```javascript
class AESCrypto {
    constructor() {
        this.algorithm = 'AES-GCM';
        this.keyLength = 256;
    }
    
    // 키 생성
    async generateKey() {
        return await crypto.subtle.generateKey(
            {
                name: this.algorithm,
                length: this.keyLength
            },
            true, // extractable
            ['encrypt', 'decrypt']
        );
    }
    
    // 암호화
    async encrypt(plaintext, key) {
        const iv = crypto.getRandomValues(new Uint8Array(12)); // GCM은 12바이트 권장
        const encodedText = new TextEncoder().encode(plaintext);
        
        const ciphertext = await crypto.subtle.encrypt(
            {
                name: this.algorithm,
                iv: iv
            },
            key,
            encodedText
        );
        
        // IV + 암호문 결합
        const result = new Uint8Array(iv.length + ciphertext.byteLength);
        result.set(iv, 0);
        result.set(new Uint8Array(ciphertext), iv.length);
        
        return btoa(String.fromCharCode(...result));
    }
    
    // 복호화
    async decrypt(encryptedData, key) {
        const data = new Uint8Array(
            atob(encryptedData)
                .split('')
                .map(char => char.charCodeAt(0))
        );
        
        const iv = data.slice(0, 12);
        const ciphertext = data.slice(12);
        
        const plaintext = await crypto.subtle.decrypt(
            {
                name: this.algorithm,
                iv: iv
            },
            key,
            ciphertext
        );
        
        return new TextDecoder().decode(plaintext);
    }
}

// 사용 예시
async function example() {
    const crypto = new AESCrypto();
    const key = await crypto.generateKey();
    
    const plaintext = "안전한 암호화 테스트";
    const encrypted = await crypto.encrypt(plaintext, key);
    const decrypted = await crypto.decrypt(encrypted, key);
    
    console.log('원본:', plaintext);
    console.log('암호화:', encrypted);
    console.log('복호화:', decrypted);
}
```

#### Python (cryptography 라이브러리)
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64

class AESCrypto:
    def __init__(self):
        self.algorithm = AESGCM
    
    def generate_key(self):
        """256비트 키 생성"""
        return os.urandom(32)
    
    def derive_key_from_password(self, password, salt):
        """비밀번호에서 키 파생"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def encrypt(self, plaintext, key):
        """AES-GCM 암호화"""
        aesgcm = self.algorithm(key)
        nonce = os.urandom(12)  # GCM은 12바이트 권장
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        # nonce + ciphertext 결합
        result = nonce + ciphertext
        return base64.b64encode(result).decode('utf-8')
    
    def decrypt(self, encrypted_data, key):
        """AES-GCM 복호화"""
        data = base64.b64decode(encrypted_data)
        nonce = data[:12]
        ciphertext = data[12:]
        
        aesgcm = self.algorithm(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

# 사용 예시
def example():
    crypto = AESCrypto()
    key = crypto.generate_key()
    
    plaintext = "안전한 암호화 테스트"
    encrypted = crypto.encrypt(plaintext, key)
    decrypted = crypto.decrypt(encrypted, key)
    
    print(f'원본: {plaintext}')
    print(f'암호화: {encrypted}')
    print(f'복호화: {decrypted}')

# 비밀번호 기반 암호화 예시
def password_example():
    crypto = AESCrypto()
    password = "mysecretpassword"
    salt = os.urandom(16)
    
    key = crypto.derive_key_from_password(password, salt)
    
    plaintext = "비밀번호로 암호화된 데이터"
    encrypted = crypto.encrypt(plaintext, key)
    decrypted = crypto.decrypt(encrypted, key)
    
    print(f'원본: {plaintext}')
    print(f'암호화: {encrypted}')
    print(f'복호화: {decrypted}')
    print(f'Salt: {base64.b64encode(salt).decode()}')
```

---

## 다른 암호화 알고리즘과의 비교

### AES vs DES
| 특징 | AES | DES |
|------|-----|-----|
| **키 길이** | 128/192/256비트 | 56비트 |
| **블록 크기** | 128비트 | 64비트 |
| **라운드 수** | 10/12/14 | 16 |
| **보안성** | 높음 | 낮음 (현재) |
| **성능** | 빠름 | 느림 |
| **상태** | 현재 표준 | 사용 중단 권장 |

### AES vs RSA
| 특징 | AES | RSA |
|------|-----|-----|
| **암호화 방식** | 대칭키 | 공개키 |
| **키 길이** | 128/192/256비트 | 1024/2048/4096비트 |
| **성능** | 빠름 | 느림 |
| **용도** | 대용량 데이터 | 키 교환, 디지털 서명 |
| **키 관리** | 복잡 | 상대적으로 간단 |

### AES vs ChaCha20
| 특징 | AES | ChaCha20 |
|------|-----|----------|
| **구조** | 블록 암호 | 스트림 암호 |
| **하드웨어 가속** | AES-NI | 없음 |
| **부채널 공격 저항성** | 보통 | 높음 |
| **구현 복잡도** | 높음 | 낮음 |
| **성능 (소프트웨어)** | 보통 | 빠름 |
