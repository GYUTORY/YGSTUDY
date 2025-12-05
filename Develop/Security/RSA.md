---
title: RSA
tags: [security, rsa]
updated: 2025-12-06
---

# RSA (Rivest-Shamir-Adleman)

## 개요

RSA는 공개 키 암호화 알고리즘이다. 안전한 데이터 전송과 디지털 서명에 사용한다. 1977년 Ron Rivest, Adi Shamir, Leonard Adleman이 개발했다.

**특징:**
- 비대칭 키 암호화 (공개 키 & 개인 키)
- 소인수분해의 어려움을 이용한 보안
- 데이터 암호화 & 디지털 서명에 활용

## 동작 원리

### 비대칭 암호화

- 공개 키(Public Key): 데이터를 암호화하는 데 사용
- 개인 키(Private Key): 데이터를 복호화하는 데 사용

누구나 공개 키로 데이터를 암호화할 수 있지만, 개인 키 없이는 복호화할 수 없다.

### 키 생성 과정

1. 두 개의 큰 소수 p와 q를 선택
2. 두 소수의 곱 n = p × q를 계산
3. 오일러 함수 계산: φ(n) = (p-1) × (q-1)
4. 공개 키(e)와 개인 키(d) 계산

**키 생성 예제:**
```python
# 두 개의 큰 소수 선택
p = 61
q = 53

# 오일러 함수 계산
phi = (p - 1) * (q - 1)  # 3120

# n 계산
n = p * q  # 3233

# 공개 키 e 선택
e = 17

# 개인 키 d 계산
def mod_inverse(e, phi):
    for d in range(2, phi):
        if (e * d) % phi == 1:
            return d
    return None

d = mod_inverse(e, phi)  # 2753

print(f"공개 키: (n={n}, e={e})")
print(f"개인 키: (n={n}, d={d})")
```

## 사용법

### 암호화 및 복호화

**암호화 공식:**
```
C = M^e mod n
```

**복호화 공식:**
```
M = C^d mod n
```

**예제:**
```python
# 메시지 암호화
M = 65
C = (M ** e) % n

# 메시지 복호화
decrypted_M = (C ** d) % n

print(f"원본 메시지: {M}")
print(f"암호화된 메시지: {C}")
print(f"복호화된 메시지: {decrypted_M}")
```

### Node.js 구현

```javascript
const crypto = require('crypto');

// RSA 키 쌍 생성
const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048,
  publicKeyEncoding: {
    type: 'spki',
    format: 'pem'
  },
  privateKeyEncoding: {
    type: 'pkcs8',
    format: 'pem'
  }
});

// 암호화
const message = 'Hello, RSA!';
const encrypted = crypto.publicEncrypt(publicKey, Buffer.from(message));

// 복호화
const decrypted = crypto.privateDecrypt(privateKey, encrypted);
console.log(decrypted.toString()); // 'Hello, RSA!'
```

## 활용 분야

### 1. 암호화 (Encryption)
- HTTPS (SSL/TLS)
- VPN
- 이메일 암호화

### 2. 디지털 서명 (Digital Signature)
- 블록체인
- 전자 서명 시스템
- 코드 서명

### 3. 인증 (Authentication)
- SSH 키 기반 로그인
- 보안 토큰
- API 키 관리

## 보안 고려사항

### 키 길이 권장사항

| 키 길이 | 보안 수준 | 사용 권장 |
|---------|-----------|----------|
| 1024비트 | 낮음 | 사용 금지 |
| 2048비트 | 충분 | 일반 사용 |
| 3072비트 | 높음 | 민감 정보 |
| 4096비트 | 매우 높음 | 극비 정보 |

**실무 팁:**
일반적으로 2048비트면 충분하다. 민감한 정보는 3072비트 이상을 사용한다.

### 보안 위협

**1. 소인수분해 공격**
큰 숫자를 소인수분해해 개인 키를 계산한다. 대응: 2048비트 이상의 키 길이 사용.

**2. 타이밍 공격**
연산 시간 차이를 이용해 키를 추측한다. 대응: 타이밍 공격 방지 알고리즘 사용.

**3. 양자 컴퓨팅**
Shor 알고리즘으로 RSA 키를 파괴할 수 있다. 대응: 양자 내성 암호화 연구 중.

## 참고

### RSA vs AES

| 항목 | RSA | AES |
|------|-----|-----|
| 방식 | 비대칭 (공개키) | 대칭 |
| 속도 | 느림 | 빠름 |
| 용도 | 키 교환, 디지털 서명 | 데이터 암호화 |
| 키 관리 | 공개키 배포 쉬움 | 키 공유 어려움 |

### 하이브리드 암호화

실무에서는 RSA와 AES를 함께 사용한다.

**동작 방식:**
1. RSA로 AES 키를 암호화해 전송
2. AES로 실제 데이터를 암호화
3. 빠른 속도 + 안전한 키 교환

**이유:**
RSA는 느리지만 키 교환이 쉽고, AES는 빠르지만 키 공유가 어렵다. 두 방식을 조합하면 장점을 모두 활용할 수 있다.

**예제:**
```javascript
// 1. AES 키 생성
const aesKey = crypto.randomBytes(32);

// 2. RSA로 AES 키 암호화
const encryptedKey = crypto.publicEncrypt(publicKey, aesKey);

// 3. AES로 데이터 암호화
const cipher = crypto.createCipheriv('aes-256-cbc', aesKey, iv);
let encrypted = cipher.update(data, 'utf8', 'hex');
encrypted += cipher.final('hex');

// 전송: encryptedKey + encrypted
```

### 관련 문서
- RFC 8017 - PKCS #1: RSA Cryptography
- NIST FIPS 186-4 - Digital Signature Standard
- [Node.js Crypto Documentation](https://nodejs.org/api/crypto.html)
