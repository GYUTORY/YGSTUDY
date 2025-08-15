---
title: 보안 기본 개념 완벽 가이드
tags: [security, cryptography, padding, salt, iteration, digest, hash, encryption]
updated: 2025-08-10
---

# 보안 기본 개념 완벽 가이드

## 배경

보안은 현대 디지털 시스템의 핵심 요소로, 데이터의 기밀성, 무결성, 가용성을 보장하는 중요한 역할을 합니다. 암호화와 해시 함수에서 사용되는 기본적인 개념들을 이해하는 것은 안전한 시스템을 구축하는 데 필수적입니다.

### 보안의 필요성
- **데이터 기밀성**: 민감한 정보의 무단 접근 방지
- **데이터 무결성**: 데이터의 변경이나 손상 방지
- **인증 및 인가**: 사용자 신원 확인 및 권한 관리
- **안전한 통신**: 네트워크를 통한 안전한 데이터 전송
- **규정 준수**: 개인정보보호법, GDPR 등 법적 요구사항 충족

### 기본 개념
- **암호화**: 평문을 암호문으로 변환하는 과정
- **해시**: 데이터를 고정 길이의 값으로 변환하는 일방향 함수
- **패딩**: 블록 암호화에서 데이터 크기를 맞추는 기법
- **솔트**: 해시 함수에 추가하는 랜덤 데이터
- **다이제스트**: 해시 함수의 출력값

## 핵심

### 1. Padding (패딩)

패딩은 블록 암호화에서 데이터의 크기를 블록 크기에 맞추기 위해 사용되는 방법입니다.

#### PKCS#7 패딩
가장 일반적인 패딩 방식으로, 블록 크기가 16바이트(128비트)인 경우를 예로 들면:

```javascript
// PKCS#7 패딩 예시
const originalData = Buffer.from('Hello, World!', 'utf8');
// 길이: 13바이트

// 패딩 적용 후 (16바이트로 맞춤)
// 원본: 48 65 6C 6C 6F 2C 20 57 6F 72 6C 64 21
// 패딩: 48 65 6C 6C 6F 2C 20 57 6F 72 6C 64 21 03 03 03
// 마지막 3바이트에 패딩 길이(3)를 채움
```

#### 패딩 구현
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
    
    // 패딩 유효성 검사
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

// 사용 예시
const originalData = Buffer.from('Hello, World!', 'utf8');
console.log('원본 데이터:', originalData.toString());

const paddedData = addPKCS7Padding(originalData);
console.log('패딩된 데이터:', paddedData);

const unpaddedData = removePKCS7Padding(paddedData);
console.log('패딩 제거된 데이터:', unpaddedData.toString());
```

### 2. Salt (솔트)

솔트는 해시 함수에 추가되는 랜덤 데이터로, 동일한 입력에 대해 항상 다른 출력을 생성하도록 합니다.

#### 솔트의 필요성
```javascript
// 솔트 없이 해시 (위험)
const password1 = 'password123';
const hash1 = crypto.createHash('sha256').update(password1).digest('hex');
// 항상 같은 해시값 생성

// 솔트를 사용한 해시 (안전)
const salt = crypto.randomBytes(16);
const hash2 = crypto.pbkdf2Sync(password1, salt, 10000, 64, 'sha512').toString('hex');
// 매번 다른 해시값 생성
```

#### 솔트 구현
```javascript
class SaltGenerator {
    // 암호학적으로 안전한 솔트 생성
    static generateSalt(length = 16) {
        return crypto.randomBytes(length);
    }
    
    // 솔트와 해시를 결합하여 저장
    static combineSaltAndHash(salt, hash) {
        return salt.toString('hex') + ':' + hash;
    }
    
    // 저장된 값에서 솔트와 해시 분리
    static separateSaltAndHash(combined) {
        const parts = combined.split(':');
        return {
            salt: Buffer.from(parts[0], 'hex'),
            hash: parts[1]
        };
    }
}
```

### 3. Iteration (반복)

해시 함수를 여러 번 반복 적용하여 무차별 대입 공격에 대한 저항성을 높입니다.

#### 반복의 효과
```javascript
// 반복 횟수에 따른 보안성 증가
const password = 'weakpassword';
const salt = crypto.randomBytes(16);

// 1회 반복 (약함)
const hash1 = crypto.pbkdf2Sync(password, salt, 1, 64, 'sha512');

// 10,000회 반복 (권장)
const hash2 = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512');

// 100,000회 반복 (강함, 느림)
const hash3 = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512');
```

#### 적응형 반복
```javascript
class AdaptiveIteration {
    // 시스템 성능에 따른 반복 횟수 조정
    static calculateOptimalIterations() {
        const startTime = Date.now();
        crypto.pbkdf2Sync('test', Buffer.alloc(16), 1000, 64, 'sha512');
        const endTime = Date.now();
        
        // 1초에 1000회 실행되는 경우, 1초에 100회가 되도록 조정
        const targetTime = 1000; // 1초
        const currentTime = endTime - startTime;
        const optimalIterations = Math.floor((1000 * targetTime) / currentTime);
        
        return Math.max(10000, Math.min(optimalIterations, 100000));
    }
}
```

### 4. Digest (다이제스트)

해시 함수의 출력으로, 고정된 길이의 이진 데이터를 16진수로 표현합니다.

#### 다이제스트 생성
```javascript
// 다양한 해시 알고리즘
const data = 'Hello, World!';

// MD5 (취약, 사용 금지)
const md5Hash = crypto.createHash('md5').update(data).digest('hex');

// SHA-1 (취약, 사용 금지)
const sha1Hash = crypto.createHash('sha1').update(data).digest('hex');

// SHA-256 (안전)
const sha256Hash = crypto.createHash('sha256').update(data).digest('hex');

// SHA-512 (더 안전)
const sha512Hash = crypto.createHash('sha512').update(data).digest('hex');
```

## 예시

### 1. 실제 사용 사례

#### 비밀번호 해시 시스템
```javascript
class PasswordManager {
    constructor(iterations = 10000) {
        this.iterations = iterations;
    }
    
    // 비밀번호 해시 생성
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
    
    // 비밀번호 검증
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
    
    // 해시 정보를 문자열로 저장
    serializeHash(hashInfo) {
        return `${hashInfo.iterations}:${hashInfo.salt}:${hashInfo.hash}`;
    }
    
    // 저장된 문자열에서 해시 정보 추출
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

// 비밀번호 등록
const password = 'mySecurePassword123';
const hashInfo = passwordManager.hashPassword(password);
const serialized = passwordManager.serializeHash(hashInfo);

console.log('저장할 해시 정보:', serialized);

// 비밀번호 검증
const isValid = passwordManager.verifyPassword(
    password, 
    hashInfo.hash, 
    hashInfo.salt, 
    hashInfo.iterations
);

console.log('비밀번호 검증 결과:', isValid);
```

#### 데이터 암호화 시스템
```javascript
class DataEncryptor {
    constructor(key) {
        this.key = crypto.scryptSync(key, 'salt', 32);
    }
    
    // 데이터 암호화
    encrypt(data) {
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipher('aes-256-cbc', this.key);
        
        let encrypted = cipher.update(data, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        return {
            iv: iv.toString('hex'),
            encrypted: encrypted
        };
    }
    
    // 데이터 복호화
    decrypt(encryptedData) {
        const iv = Buffer.from(encryptedData.iv, 'hex');
        const decipher = crypto.createDecipher('aes-256-cbc', this.key);
        
        let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        
        return decrypted;
    }
    
    // 파일 암호화
    async encryptFile(inputPath, outputPath) {
        const fs = require('fs').promises;
        const data = await fs.readFile(inputPath);
        const encrypted = this.encrypt(data.toString());
        
        await fs.writeFile(outputPath, JSON.stringify(encrypted));
    }
    
    // 파일 복호화
    async decryptFile(inputPath, outputPath) {
        const fs = require('fs').promises;
        const encryptedData = JSON.parse(await fs.readFile(inputPath, 'utf8'));
        const decrypted = this.decrypt(encryptedData);
        
        await fs.writeFile(outputPath, decrypted);
    }
}

// 사용 예시
const encryptor = new DataEncryptor('mySecretKey');

const sensitiveData = 'This is sensitive information that needs to be encrypted.';
const encrypted = encryptor.encrypt(sensitiveData);
console.log('암호화된 데이터:', encrypted);

const decrypted = encryptor.decrypt(encrypted);
console.log('복호화된 데이터:', decrypted);
```

### 2. 고급 패턴

#### 키 파생 함수 (KDF)
```javascript
class KeyDerivation {
    // PBKDF2를 사용한 키 파생
    static deriveKey(password, salt, iterations = 100000, keyLength = 32) {
        return crypto.pbkdf2Sync(password, salt, iterations, keyLength, 'sha512');
    }
    
    // Argon2 시뮬레이션 (Node.js에서는 argon2 모듈 사용 권장)
    static deriveKeyWithArgon2(password, salt, timeCost = 3, memoryCost = 65536, parallelism = 4) {
        // 실제로는 argon2 모듈 사용
        return crypto.pbkdf2Sync(password, salt, timeCost * 1000, 32, 'sha512');
    }
    
    // 키 스트레칭
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

#### 보안 토큰 생성
```javascript
class SecureTokenGenerator {
    // 암호학적으로 안전한 토큰 생성
    static generateToken(length = 32) {
        return crypto.randomBytes(length).toString('hex');
    }
    
    // URL 안전한 토큰 생성
    static generateUrlSafeToken(length = 32) {
        return crypto.randomBytes(length).toString('base64url');
    }
    
    // 시간 기반 토큰 (TOTP 시뮬레이션)
    static generateTimeBasedToken(secret, timeStep = 30) {
        const time = Math.floor(Date.now() / 1000 / timeStep);
        const timeBuffer = Buffer.alloc(8);
        timeBuffer.writeBigUInt64BE(BigInt(time), 0);
        
        const hmac = crypto.createHmac('sha1', secret);
        hmac.update(timeBuffer);
        const hash = hmac.digest();
        
        const offset = hash[hash.length - 1] & 0xf;
        const code = ((hash[offset] & 0x7f) << 24) |
                    ((hash[offset + 1] & 0xff) << 16) |
                    ((hash[offset + 2] & 0xff) << 8) |
                    (hash[offset + 3] & 0xff);
        
        return (code % 1000000).toString().padStart(6, '0');
    }
}
```

## 운영 팁

### 성능 최적화

#### 비동기 해시 처리
```javascript
// 동기 처리 (블로킹)
const hash = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512');

// 비동기 처리 (논블로킹)
crypto.pbkdf2(password, salt, 10000, 64, 'sha512', (err, hash) => {
    if (err) {
        console.error('해시 생성 오류:', err);
        return;
    }
    console.log('해시 생성 완료:', hash.toString('hex'));
});

// Promise 기반 비동기 처리
const hashAsync = util.promisify(crypto.pbkdf2);
const hash = await hashAsync(password, salt, 10000, 64, 'sha512');
```

#### 메모리 효율성
```javascript
// 스트림을 사용한 대용량 파일 해시
const fs = require('fs');
const hash = crypto.createHash('sha256');

fs.createReadStream('large-file.txt')
    .on('data', (data) => {
        hash.update(data);
    })
    .on('end', () => {
        console.log('파일 해시:', hash.digest('hex'));
    });
```

### 에러 처리

#### 보안 예외 처리
```javascript
class SecurityException extends Error {
    constructor(message, code) {
        super(message);
        this.name = 'SecurityException';
        this.code = code;
    }
}

class SecureValidator {
    static validatePassword(password) {
        if (password.length < 8) {
            throw new SecurityException('비밀번호는 최소 8자 이상이어야 합니다.', 'PASSWORD_TOO_SHORT');
        }
        
        if (!/[A-Z]/.test(password)) {
            throw new SecurityException('비밀번호는 대문자를 포함해야 합니다.', 'PASSWORD_NO_UPPERCASE');
        }
        
        if (!/[a-z]/.test(password)) {
            throw new SecurityException('비밀번호는 소문자를 포함해야 합니다.', 'PASSWORD_NO_LOWERCASE');
        }
        
        if (!/\d/.test(password)) {
            throw new SecurityException('비밀번호는 숫자를 포함해야 합니다.', 'PASSWORD_NO_NUMBER');
        }
        
        return true;
    }
    
    static validateSalt(salt) {
        if (salt.length < 16) {
            throw new SecurityException('솔트는 최소 16바이트 이상이어야 합니다.', 'SALT_TOO_SHORT');
        }
        
        return true;
    }
}
```

## 참고

### 해시 알고리즘 비교

| 알고리즘 | 출력 길이 | 보안 수준 | 권장도 |
|----------|-----------|-----------|--------|
| **MD5** | 128비트 | 취약 | ❌ 사용 금지 |
| **SHA-1** | 160비트 | 취약 | ❌ 사용 금지 |
| **SHA-256** | 256비트 | 안전 | ⭐⭐⭐⭐ |
| **SHA-512** | 512비트 | 매우 안전 | ⭐⭐⭐⭐⭐ |
| **bcrypt** | 60문자 | 안전 | ⭐⭐⭐⭐⭐ |
| **Argon2** | 가변 | 매우 안전 | ⭐⭐⭐⭐⭐ |

### 보안 모범 사례

| 항목 | 권장사항 | 이유 |
|------|----------|------|
| **비밀번호 해시** | bcrypt, Argon2, PBKDF2 | 전용 비밀번호 해시 알고리즘 |
| **솔트 길이** | 최소 16바이트 | 무차별 대입 공격 방지 |
| **반복 횟수** | 최소 10,000회 | 계산 비용 증가 |
| **키 길이** | AES-256 이상 | 충분한 보안 강도 |
| **랜덤 생성** | crypto.randomBytes() | 암호학적으로 안전한 난수 |

### 결론
보안은 시스템 설계의 핵심 요소로, 기본 개념을 정확히 이해하는 것이 중요합니다.
패딩, 솔트, 반복, 다이제스트를 적절히 조합하여 강력한 보안 시스템을 구축하세요.
최신 보안 알고리즘과 모범 사례를 따라 안전한 시스템을 구현하세요.
정기적인 보안 감사와 업데이트를 통해 시스템의 보안성을 유지하세요.
