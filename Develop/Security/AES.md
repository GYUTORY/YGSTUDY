---
title: AES Advanced Encryption Standard
tags: [security, aes, encryption, cryptography]
updated: 2025-12-06
---

# AES (Advanced Encryption Standard)

## 개요

AES는 2001년 NIST에서 채택한 대칭키 암호화 알고리즘이다. 전 세계적으로 널리 사용된다.

**핵심 특징:**
- 대칭키 암호화: 암호화와 복호화에 같은 키 사용
- 블록 암호: 128비트 블록 단위로 처리
- 고성능: 하드웨어와 소프트웨어 모두에서 효율적

## 동작 원리

### 키 길이와 라운드 수

| 키 길이 | 라운드 수 | 보안 강도 | 사용 권장 |
|---------|-----------|-----------|----------|
| 128비트 | 10라운드 | 높음 | 일반적 사용 |
| 192비트 | 12라운드 | 매우 높음 | 고보안 요구 |
| 256비트 | 14라운드 | 최고 | 극비 정보 |

### 암호화 과정

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

### 라운드 함수

**1. SubBytes (바이트 치환)**
- 비선형성 제공
- S-box를 사용한 바이트 단위 치환

**2. ShiftRows (행 이동)**
- 확산성 제공
- 각 행을 다른 거리만큼 순환 이동

**3. MixColumns (열 혼합)**
- 열 간의 혼합
- Galois Field 다항식 곱셈

**4. AddRoundKey (라운드 키 추가)**
- 키와의 결합
- 상태 행렬과 라운드 키의 XOR 연산

## IV (Initialization Vector)

IV는 암호화 시 사용하는 추가 입력값이다. 같은 키로 여러 메시지를 암호화할 때 보안을 높인다.

**특징:**
- 크기: 16바이트 (128비트)
- 랜덤성: 암호학적으로 안전한 난수 생성기 사용
- 유일성: 매 암호화마다 새로운 IV 생성
- 재사용 금지: 같은 IV 재사용 시 보안 취약점 발생

**주의사항:**
IV를 재사용하면 같은 평문이 같은 암호문으로 암호화되어 패턴이 노출된다.

### 사용 예제

```javascript
const crypto = require('crypto');

// IV 생성
const iv = crypto.randomBytes(16);

// 암호화
const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
let encrypted = cipher.update(data, 'utf8', 'hex');
encrypted += cipher.final('hex');

// 복호화
const decipher = crypto.createDecipheriv('aes-256-cbc', key, iv);
let decrypted = decipher.update(encrypted, 'hex', 'utf8');
decrypted += decipher.final('utf8');
```

## Salt

Salt는 패스워드 해싱에 사용하는 랜덤 데이터다. 동일한 패스워드도 다른 해시값을 생성한다.

### IV vs Salt

| 항목 | IV | Salt |
|------|-----|------|
| 목적 | 암호화 보안 강화 | 해시 보안 강화 |
| 사용처 | 대칭키 암호화 | 패스워드 해싱 |
| 크기 | 블록 크기와 동일 | 16바이트 이상 |
| 공개 여부 | 공개 가능 | 공개 가능 |
| 재사용 | 절대 금지 | 절대 금지 |

## AES 운영 모드

### ECB (Electronic Codebook)

- 블록 단위 독립 암호화
- 가장 단순한 모드
- 보안상 취약 (사용 금지)

**문제점:**
같은 평문 블록이 같은 암호문 블록으로 암호화되어 패턴이 노출된다.

### CBC (Cipher Block Chaining)

- 이전 블록과 현재 블록을 XOR
- IV 필요
- 널리 사용됨
- 병렬 처리 불가

**주의사항:**
IV를 재사용하면 보안이 약해진다. 매번 새로운 IV를 생성해야 한다.

### CTR (Counter)

- 카운터를 암호화해 스트림 암호처럼 동작
- IV (nonce) 필요
- 병렬 처리 가능
- 빠른 속도

### GCM (Galois/Counter Mode)

- CTR + 인증 태그
- 암호화 + 무결성 검증
- 가장 안전한 모드
- 권장 사용

**장점:**
암호화와 동시에 무결성을 검증할 수 있어 변조를 감지할 수 있다.

**모드 비교:**

| 모드 | 보안성 | 속도 | 병렬 처리 | 권장 사용 |
|------|--------|------|-----------|----------|
| ECB | 낮음 | 빠름 | 가능 | 비권장 |
| CBC | 중간 | 보통 | 불가 | 일반적 |
| CTR | 높음 | 빠름 | 가능 | 권장 |
| GCM | 매우 높음 | 빠름 | 가능 | 강력 권장 |

## 구현 예제

### Node.js 기본 구현

```javascript
const crypto = require('crypto');

class AESCrypto {
  constructor(key) {
    this.key = Buffer.from(key, 'hex');
    this.algorithm = 'aes-256-gcm';
  }

  encrypt(plaintext) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(this.algorithm, this.key, iv);
    
    let encrypted = cipher.update(plaintext, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const authTag = cipher.getAuthTag();
    
    return {
      encrypted,
      iv: iv.toString('hex'),
      authTag: authTag.toString('hex')
    };
  }

  decrypt(encryptedData) {
    const decipher = crypto.createDecipheriv(
      this.algorithm,
      this.key,
      Buffer.from(encryptedData.iv, 'hex')
    );
    
    decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'hex'));
    
    let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }
}

// 사용 예시
const key = crypto.randomBytes(32).toString('hex');
const aes = new AESCrypto(key);

const encrypted = aes.encrypt('Hello, AES!');
console.log('암호화:', encrypted);

const decrypted = aes.decrypt(encrypted);
console.log('복호화:', decrypted);
```

## 보안 고려사항

### 키 관리

**키 생성:**
```javascript
// 암호학적으로 안전한 키 생성
const key = crypto.randomBytes(32); // AES-256
```

**키 저장:**
- 환경 변수 사용 (간단한 경우)
- 키 관리 시스템 (AWS KMS, Azure Key Vault)
- 하드웨어 보안 모듈 (HSM) (고보안 요구)

**주의사항:**
키를 코드에 하드코딩하면 안 된다. 환경 변수나 키 관리 시스템을 사용해야 한다.

### 공통 취약점

| 취약점 | 문제 | 해결책 |
|--------|------|--------|
| IV 재사용 | 패턴 노출 | 매번 새로운 IV 생성 |
| 약한 키 | 키 추측 가능 | crypto.randomBytes() 사용 |
| ECB 모드 | 패턴 노출 | GCM 또는 CBC 사용 |
| 키 하드코딩 | 키 노출 | 환경 변수 또는 KMS 사용 |

## 참고

### AES vs 다른 암호화

| 알고리즘 | 유형 | 속도 | 보안 | 사용 |
|---------|------|------|------|------|
| AES | 대칭키 | 빠름 | 높음 | 데이터 암호화 |
| RSA | 비대칭키 | 느림 | 높음 | 키 교환, 서명 |
| ChaCha20 | 대칭키 | 매우 빠름 | 높음 | 모바일 암호화 |

**실무 팁:**
대용량 데이터는 AES로 암호화하고, 키 교환은 RSA로 한다. 하이브리드 방식이 일반적이다.

### 관련 문서
- NIST FIPS 197 - AES Specification
- [Node.js Crypto Documentation](https://nodejs.org/api/crypto.html)
- RFC 3602 - The AES-CBC Cipher Algorithm
- RFC 5116 - An Interface and Algorithms for Authenticated Encryption
