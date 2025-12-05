---
title: 보안 기본 개념 가이드
tags: [security, cryptography, padding, salt, iteration, digest, hash, encryption]
updated: 2025-12-06
---

# 보안 기본 개념 가이드

## 개요

보안은 데이터의 기밀성, 무결성, 가용성을 보장하는 핵심 요소다.

**보안의 필요성:**
- 데이터 기밀성: 민감한 정보의 무단 접근 방지
- 데이터 무결성: 데이터의 변경이나 손상 방지
- 인증 및 인가: 사용자 신원 확인 및 권한 관리
- 안전한 통신: 네트워크를 통한 안전한 데이터 전송

**기본 개념:**
- 암호화: 평문을 암호문으로 변환
- 해시: 데이터를 고정 길이의 값으로 변환하는 일방향 함수
- 패딩: 블록 암호화에서 데이터 크기를 맞추는 기법
- 솔트: 해시 함수에 추가하는 랜덤 데이터
- 다이제스트: 해시 함수의 출력값

## 동작 원리

### Padding (패딩)

패딩은 블록 암호화에서 데이터 크기를 블록 크기에 맞추기 위해 사용한다.

```javascript
const crypto = require('crypto');

// PKCS#7 패딩을 적용하는 함수
function addPKCS7Padding(data, blockSize = 16) {
    const paddingLength = blockSize - (data.length % blockSize);
    const padding = Buffer.alloc(paddingLength, paddingLength);
    return Buffer.concat([data, padding]);
}

// PKCS#7 패딩을 제거하는 함수
function removePKCS7Padding(data) {
    const paddingLength = data[data.length - 1];
    
    if (paddingLength > data.length) {
        throw new Error('Invalid padding');
    }
    
    for (let i = data.length - paddingLength; i < data.length; i++) {
        if (data[i] !== paddingLength) {
            throw new Error('Invalid padding');
        }
    }
    
    return data.slice(0, data.length - paddingLength);
}
```

### Salt (솔트)

솔트는 해시 함수에 추가하는 랜덤 데이터다. 동일한 입력에 대해 항상 다른 출력을 생성한다.

```javascript
// 솔트 없이 해시 (위험)
const password1 = 'password123';
const hash1 = crypto.createHash('sha256').update(password1).digest('hex');

// 솔트를 사용한 해시 (안전)
const salt = crypto.randomBytes(16);
const hash2 = crypto.pbkdf2Sync(password1, salt, 10000, 64, 'sha512').toString('hex');

class SaltGenerator {
    static generateSalt(length = 16) {
        return crypto.randomBytes(length);
    }
    
    static combineSaltAndHash(salt, hash) {
        return salt.toString('hex') + ':' + hash;
    }
    
    static separateSaltAndHash(combined) {
        const parts = combined.split(':');
        return {
            salt: Buffer.from(parts[0], 'hex'),
            hash: parts[1]
        };
    }
}
```

### Iteration (반복)

해시 함수를 여러 번 반복 적용해 무차별 대입 공격에 대한 저항성을 높인다.

```javascript
const password = 'weakpassword';
const salt = crypto.randomBytes(16);

// 1회 반복 (약함)
const hash1 = crypto.pbkdf2Sync(password, salt, 1, 64, 'sha512');

// 10,000회 반복 (권장)
const hash2 = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512');

// 100,000회 반복 (강함, 느림)
const hash3 = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512');
```

### Digest (다이제스트)

해시 함수의 출력값이다. 고정된 길이의 이진 데이터를 16진수로 표현한다.

```javascript
const data = 'Hello, World!';

// SHA-256 (안전)
const sha256Hash = crypto.createHash('sha256').update(data).digest('hex');

// SHA-512 (더 안전)
const sha512Hash = crypto.createHash('sha512').update(data).digest('hex');
```

## 사용법

### 비밀번호 해시 시스템

```javascript
class PasswordManager {
    constructor(iterations = 10000) {
        this.iterations = iterations;
    }
    
    hashPassword(password) {
        const salt = crypto.randomBytes(16);
        const hash = crypto.pbkdf2Sync(
            password, 
            salt, 
            this.iterations, 
            64, 
            'sha512'
        );
        
        return {
            hash: hash.toString('hex'),
            salt: salt.toString('hex'),
            iterations: this.iterations
        };
    }
    
    verifyPassword(password, storedHash, storedSalt, storedIterations) {
        const saltBuffer = Buffer.from(storedSalt, 'hex');
        const testHash = crypto.pbkdf2Sync(
            password, 
            saltBuffer, 
            storedIterations, 
            64, 
            'sha512'
        );
        
        return crypto.timingSafeEqual(
            Buffer.from(storedHash, 'hex'), 
            testHash
        );
    }
    
    serializeHash(hashInfo) {
        return `${hashInfo.iterations}:${hashInfo.salt}:${hashInfo.hash}`;
    }
    
    deserializeHash(serialized) {
        const [iterations, salt, hash] = serialized.split(':');
        return {
            iterations: parseInt(iterations),
            salt: salt,
            hash: hash
        };
    }
}

// 사용 예시
const passwordManager = new PasswordManager();
const password = 'mySecurePassword123';
const hashInfo = passwordManager.hashPassword(password);
const serialized = passwordManager.serializeHash(hashInfo);

console.log('저장할 해시 정보:', serialized);
```

## 예제

### 키 파생 함수 (KDF)

```javascript
class KeyDerivation {
    static deriveKey(password, salt, iterations = 100000, keyLength = 32) {
        return crypto.pbkdf2Sync(password, salt, iterations, keyLength, 'sha512');
    }
    
    static stretchKey(key, salt, rounds = 1000) {
        let stretchedKey = key;
        for (let i = 0; i < rounds; i++) {
            stretchedKey = crypto.createHash('sha256')
                .update(stretchedKey)
                .update(salt)
                .digest();
        }
        return stretchedKey;
    }
}
```

### 보안 토큰 생성

```javascript
class SecureTokenGenerator {
    static generateToken(length = 32) {
        return crypto.randomBytes(length).toString('hex');
    }
    
    static generateUrlSafeToken(length = 32) {
        return crypto.randomBytes(length).toString('base64url');
    }
}
```

## 참고

### 해시 알고리즘 비교

| 알고리즘 | 출력 길이 | 보안 수준 | 권장도 |
|----------|-----------|-----------|--------|
| MD5 | 128비트 | 취약 | 사용 금지 |
| SHA-1 | 160비트 | 취약 | 사용 금지 |
| SHA-256 | 256비트 | 안전 | 권장 |
| SHA-512 | 512비트 | 매우 안전 | 권장 |
| bcrypt | 60문자 | 안전 | 권장 |
| Argon2 | 가변 | 매우 안전 | 권장 |

### 보안 모범 사례

| 항목 | 권장사항 | 이유 |
|------|----------|------|
| 비밀번호 해시 | bcrypt, Argon2, PBKDF2 | 전용 비밀번호 해시 알고리즘 |
| 솔트 길이 | 최소 16바이트 | 무차별 대입 공격 방지 |
| 반복 횟수 | 최소 10,000회 | 계산 비용 증가 |
| 키 길이 | AES-256 이상 | 충분한 보안 강도 |
| 랜덤 생성 | crypto.randomBytes() | 암호학적으로 안전한 난수 |

**실무 팁:**
패딩, 솔트, 반복, 다이제스트를 적절히 조합해야 한다. 비밀번호 해싱에는 bcrypt나 Argon2 같은 전용 알고리즘을 사용하는 게 좋다.
