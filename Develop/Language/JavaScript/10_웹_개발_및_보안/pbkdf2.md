# PBKDF2 (Password-Based Key Derivation Function 2)

## 📖 개요
PBKDF2는 비밀번호를 안전하게 저장하기 위한 암호화 표준입니다. 단순히 비밀번호를 해시하는 것보다 훨씬 강력한 보안을 제공합니다.

### 왜 PBKDF2가 필요한가?

**단순 해시의 문제점**
- 비밀번호를 그대로 해시하면 레인보우 테이블 공격에 취약합니다
- 레인보우 테이블: 미리 계산된 해시값들의 데이터베이스로, 해시값을 역추적하여 원본 비밀번호를 찾는 공격 방법

**솔트의 필요성**
- 같은 비밀번호라도 다른 결과를 만들어내는 무작위 값
- 각 사용자마다 고유한 솔트를 사용하여 동일한 비밀번호도 다른 해시값 생성

**반복 해싱**
- 해킹 시도를 어렵게 만드는 핵심 요소
- 해시 함수를 여러 번 반복 적용하여 무차별 대입 공격에 대한 저항력 증가

## 🔧 핵심 개념

### 1. 솔트(Salt)

**정의**: 비밀번호에 추가하는 무작위 데이터

**왜 필요한가?**
- 각 사용자마다 고유한 값
- 같은 비밀번호라도 다른 해시 결과 생성
- 레인보우 테이블 공격 방지

**솔트 생성 예시**
```javascript
const crypto = require('crypto');

// 16바이트 무작위 데이터 생성
const salt = crypto.randomBytes(16);
console.log('생성된 솔트:', salt.toString('hex'));
// 출력 예시: 8f7d3a2b1c9e4f5a6b7c8d9e0f1a2b3c

// 솔트 길이별 비교
const shortSalt = crypto.randomBytes(8);  // 8바이트 (64비트)
const longSalt = crypto.randomBytes(32);  // 32바이트 (256비트)

console.log('짧은 솔트:', shortSalt.toString('hex'));
console.log('긴 솔트:', longSalt.toString('hex'));
```

### 2. 반복 해싱(Iteration)

**정의**: 해시 함수를 여러 번 반복 적용하는 과정

**왜 반복하는가?**
- 해킹 시도를 어렵게 만드는 핵심
- 반복 횟수가 많을수록 보안성 증가
- 권장: 100,000회 이상

**반복 횟수에 따른 시간 차이**
```javascript
const crypto = require('crypto');

const testIterations = [1000, 10000, 100000];

testIterations.forEach(iterations => {
    const start = Date.now();
    crypto.pbkdf2Sync('password', 'salt', iterations, 64, 'sha512');
    const end = Date.now();
    console.log(`${iterations}회 반복: ${end - start}ms`);
});

// 출력 예시:
// 1000회 반복: 2ms
// 10000회 반복: 15ms
// 100000회 반복: 150ms
```

### 3. 키 길이(Key Length)

**정의**: 최종 해시 결과의 길이

**길이 선택 기준**
- 보안성과 성능의 균형
- 일반적으로 64바이트(512비트) 사용
- 너무 짧으면 보안성 저하, 너무 길면 성능 저하

```javascript
// 키 길이별 비교
const lengths = [32, 64, 128]; // 바이트 단위

lengths.forEach(length => {
    const start = Date.now();
    const key = crypto.pbkdf2Sync('password', 'salt', 100000, length, 'sha512');
    const end = Date.now();
    
    console.log(`${length}바이트 키 생성: ${end - start}ms`);
    console.log(`키 길이: ${key.length}바이트`);
    console.log(`해시값: ${key.toString('hex').substring(0, 32)}...`);
    console.log('---');
});
```

## 🛠️ JavaScript 구현

### 기본 비밀번호 해싱 함수

```javascript
const crypto = require('crypto');

async function hashPassword(password) {
    // 1. 솔트 생성 (16바이트)
    const salt = crypto.randomBytes(16);
    
    // 2. PBKDF2로 키 생성
    const key = await new Promise((resolve, reject) => {
        crypto.pbkdf2(
            password,           // 원본 비밀번호
            salt,              // 솔트
            100000,           // 반복 횟수
            64,               // 키 길이 (바이트)
            'sha512',         // 해시 알고리즘
            (err, derivedKey) => {
                if (err) reject(err);
                resolve(derivedKey);
            }
        );
    });

    // 3. 결과를 저장 가능한 형태로 변환
    return {
        salt: salt.toString('base64'),
        hash: key.toString('base64')
    };
}

// 사용 예시
async function example() {
    const password = "mySecurePassword123";
    const result = await hashPassword(password);
    
    console.log('저장할 솔트:', result.salt);
    console.log('저장할 해시:', result.hash);
    
    // 같은 비밀번호로 다시 해싱하면 다른 결과
    const result2 = await hashPassword(password);
    console.log('두 번째 해시:', result2.hash);
    console.log('해시가 다른가?', result.hash !== result2.hash); // true
}

example();
```

### 비밀번호 검증 함수

```javascript
async function verifyPassword(password, storedHash, storedSalt) {
    // 저장된 솔트를 Buffer로 변환
    const salt = Buffer.from(storedSalt, 'base64');
    
    // 입력된 비밀번호로 해시 생성
    const key = await new Promise((resolve, reject) => {
        crypto.pbkdf2(
            password,
            salt,
            100000,
            64,
            'sha512',
            (err, derivedKey) => {
                if (err) reject(err);
                resolve(derivedKey);
            }
        );
    });

    // 저장된 해시와 비교
    return key.toString('base64') === storedHash;
}

// 검증 예시
async function loginExample() {
    // 회원가입 시 저장된 정보 (실제로는 데이터베이스에서 가져옴)
    const storedHash = "이전에 저장된 해시값";
    const storedSalt = "이전에 저장된 솔트값";
    
    // 로그인 시도
    const inputPassword = "mySecurePassword123";
    const isValid = await verifyPassword(inputPassword, storedHash, storedSalt);
    
    console.log('비밀번호 일치:', isValid);
    
    // 잘못된 비밀번호로 시도
    const wrongPassword = "wrongPassword";
    const isInvalid = await verifyPassword(wrongPassword, storedHash, storedSalt);
    console.log('잘못된 비밀번호:', isInvalid);
}
```

## 🔒 보안 설정 가이드

### 솔트 설정

```javascript
// 권장 설정
const saltLength = 16; // 최소 16바이트
const salt = crypto.randomBytes(saltLength);

// 솔트 길이별 보안성 비교
const saltLengths = {
    '8바이트': 8,    // 64비트 - 취약
    '16바이트': 16,  // 128비트 - 권장
    '32바이트': 32   // 256비트 - 고보안
};

Object.entries(saltLengths).forEach(([name, length]) => {
    const salt = crypto.randomBytes(length);
    console.log(`${name}: ${salt.toString('hex')}`);
});
```

### 반복 횟수 설정

```javascript
// 시스템 성능에 따른 권장값
const iterations = {
    개발환경: 10000,      // 빠른 테스트용
    일반서비스: 100000,   // 기본 권장값
    고보안서비스: 200000  // 높은 보안 요구사항
};

// 현재 시스템 성능 측정
function measurePerformance() {
    const testPassword = "testPassword";
    const testSalt = crypto.randomBytes(16);
    
    Object.entries(iterations).forEach(([env, iter]) => {
        const start = Date.now();
        crypto.pbkdf2Sync(testPassword, testSalt, iter, 64, 'sha512');
        const end = Date.now();
        
        console.log(`${env}: ${iter}회 반복 - ${end - start}ms`);
    });
}

measurePerformance();
```

### 해시 알고리즘 선택

```javascript
// 지원하는 해시 알고리즘들
const algorithms = ['sha1', 'sha256', 'sha512'];

// 알고리즘별 성능 비교
function compareAlgorithms() {
    const password = "testPassword";
    const salt = crypto.randomBytes(16);
    const iterations = 10000;
    
    algorithms.forEach(algorithm => {
        const start = Date.now();
        const key = crypto.pbkdf2Sync(password, salt, iterations, 64, algorithm);
        const end = Date.now();
        
        console.log(`${algorithm}: ${end - start}ms`);
        console.log(`해시값: ${key.toString('hex').substring(0, 32)}...`);
        console.log('---');
    });
}

compareAlgorithms();
```

## ⚠️ 주의사항

### 1. 솔트 관리

**절대 재사용 금지**
- 각 사용자마다 고유한 솔트 사용
- 같은 솔트를 여러 사용자에게 사용하면 보안성 크게 저하

```javascript
// 잘못된 예시 - 같은 솔트 재사용
const sharedSalt = crypto.randomBytes(16);

async function wrongHashPassword(password) {
    const key = await new Promise((resolve, reject) => {
        crypto.pbkdf2(password, sharedSalt, 100000, 64, 'sha512', (err, key) => {
            if (err) reject(err);
            resolve(key);
        });
    });
    return key.toString('base64');
}

// 올바른 예시 - 매번 새로운 솔트
async function correctHashPassword(password) {
    const salt = crypto.randomBytes(16); // 매번 새로운 솔트
    const key = await new Promise((resolve, reject) => {
        crypto.pbkdf2(password, salt, 100000, 64, 'sha512', (err, key) => {
            if (err) reject(err);
            resolve(key);
        });
    });
    return {
        salt: salt.toString('base64'),
        hash: key.toString('base64')
    };
}
```

**안전한 저장**
- 솔트는 해시와 함께 저장해도 됨
- 솔트는 공개되어도 안전 (비밀번호가 아니므로)

**충분한 길이**
- 최소 16바이트 이상 권장
- 8바이트 이하는 취약

### 2. 반복 횟수 조정

**성능 고려**
- 서버 부하와 사용자 경험의 균형
- 너무 많으면 로그인 시간이 길어짐

```javascript
// 반복 횟수별 로그인 시간 측정
async function measureLoginTime(iterations) {
    const password = "userPassword";
    const salt = crypto.randomBytes(16);
    
    const start = Date.now();
    await new Promise((resolve, reject) => {
        crypto.pbkdf2(password, salt, iterations, 64, 'sha512', (err, key) => {
            if (err) reject(err);
            resolve(key);
        });
    });
    const end = Date.now();
    
    return end - start;
}

// 권장 반복 횟수 테스트
[50000, 100000, 200000].forEach(async (iter) => {
    const time = await measureLoginTime(iter);
    console.log(`${iter}회 반복: ${time}ms`);
});
```

**점진적 증가**
- 시간이 지날수록 증가 권장
- 하드웨어 성능 향상에 따라 조정

**하드웨어 고려**
- 서버 성능에 맞게 조정
- 모바일 환경에서는 낮은 값 사용 가능

### 3. 에러 처리

```javascript
async function safeHashPassword(password) {
    try {
        // 입력 검증
        if (!password) {
            throw new Error('비밀번호가 입력되지 않았습니다.');
        }
        
        if (password.length < 8) {
            throw new Error('비밀번호는 최소 8자 이상이어야 합니다.');
        }
        
        if (password.length > 128) {
            throw new Error('비밀번호는 128자 이하여야 합니다.');
        }
        
        // 특수문자 포함 여부 확인 (선택사항)
        const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        if (!hasSpecialChar) {
            console.warn('특수문자를 포함하는 것을 권장합니다.');
        }
        
        return await hashPassword(password);
    } catch (error) {
        console.error('비밀번호 해싱 실패:', error.message);
        throw error;
    }
}

// 에러 처리 테스트
async function testErrorHandling() {
    const testCases = [
        '',                    // 빈 문자열
        '123',                 // 너무 짧음
        'a'.repeat(200),       // 너무 김
        'validPassword123'     // 정상
    ];
    
    for (const password of testCases) {
        try {
            const result = await safeHashPassword(password);
            console.log(`성공: ${password.substring(0, 10)}...`);
        } catch (error) {
            console.log(`실패: ${error.message}`);
        }
    }
}

testErrorHandling();
```

## 📊 성능 비교

### 다른 해싱 방법과의 비교

```javascript
const crypto = require('crypto');

function compareHashingMethods(password) {
    console.log('=== 해싱 방법 비교 ===');
    
    // MD5 (취약 - 사용 금지)
    const md5Start = Date.now();
    const md5Hash = crypto.createHash('md5').update(password).digest('hex');
    const md5Time = Date.now() - md5Start;
    console.log(`MD5: ${md5Time}ms - ${md5Hash.substring(0, 32)}...`);
    
    // SHA-256 (단순 해시 - 솔트 없음)
    const shaStart = Date.now();
    const sha256Hash = crypto.createHash('sha256').update(password).digest('hex');
    const shaTime = Date.now() - shaStart;
    console.log(`SHA-256: ${shaTime}ms - ${sha256Hash.substring(0, 32)}...`);
    
    // PBKDF2 (권장)
    const pbkdf2Start = Date.now();
    const salt = crypto.randomBytes(16);
    const pbkdf2Hash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512');
    const pbkdf2Time = Date.now() - pbkdf2Start;
    console.log(`PBKDF2: ${pbkdf2Time}ms - ${pbkdf2Hash.toString('hex').substring(0, 32)}...`);
    
    console.log('\n=== 보안성 비교 ===');
    console.log('MD5: 취약 (레인보우 테이블 공격에 취약)');
    console.log('SHA-256: 보통 (솔트 없음, 빠른 해싱)');
    console.log('PBKDF2: 강력 (솔트 + 반복 해싱)');
}

compareHashingMethods('myPassword123');
```

## 🔄 마이그레이션 가이드

### 기존 해시에서 PBKDF2로 전환

```javascript
// 기존 MD5 해시 검증 함수 (예시)
function verifyOldHash(password, oldHash) {
    const hash = crypto.createHash('md5').update(password).digest('hex');
    return hash === oldHash;
}

// PBKDF2로 마이그레이션
async function migrateToPBKDF2(oldHash, password) {
    try {
        // 1. 기존 해시로 로그인 확인
        if (verifyOldHash(password, oldHash)) {
            // 2. PBKDF2로 새 해시 생성
            const newHash = await hashPassword(password);
            
            // 3. 데이터베이스 업데이트 (실제 구현에서는 DB 업데이트)
            console.log('마이그레이션 완료');
            console.log('새 솔트:', newHash.salt);
            console.log('새 해시:', newHash.hash);
            
            return newHash;
        } else {
            console.log('기존 비밀번호가 일치하지 않습니다.');
            return null;
        }
    } catch (error) {
        console.error('마이그레이션 실패:', error.message);
        return null;
    }
}

// 마이그레이션 테스트
async function testMigration() {
    const password = "userPassword";
    const oldHash = crypto.createHash('md5').update(password).digest('hex');
    
    console.log('기존 해시:', oldHash);
    const newHash = await migrateToPBKDF2(oldHash, password);
    
    if (newHash) {
        // 새 해시로 검증
        const isValid = await verifyPassword(password, newHash.hash, newHash.salt);
        console.log('마이그레이션 후 검증:', isValid);
    }
}

testMigration();
```

## 💡 실제 사용 시나리오

### 회원가입 프로세스

```javascript
async function registerUser(email, password) {
    try {
        // 1. 입력 검증
        if (!email || !password) {
            throw new Error('이메일과 비밀번호를 모두 입력해주세요.');
        }
        
        if (password.length < 8) {
            throw new Error('비밀번호는 8자 이상이어야 합니다.');
        }
        
        // 2. 비밀번호 해싱
        const { salt, hash } = await hashPassword(password);
        
        // 3. 사용자 객체 생성
        const user = {
            id: Date.now().toString(), // 실제로는 UUID 사용
            email: email,
            passwordHash: hash,
            passwordSalt: salt,
            createdAt: new Date(),
            lastLogin: null
        };
        
        // 4. 데이터베이스에 저장 (실제 구현에서는 DB에 저장)
        console.log('사용자 등록 완료:', {
            id: user.id,
            email: user.email,
            createdAt: user.createdAt
        });
        
        return user;
    } catch (error) {
        console.error('회원가입 실패:', error.message);
        throw error;
    }
}

// 회원가입 테스트
async function testRegistration() {
    const users = [
        { email: 'user1@example.com', password: 'password123' },
        { email: 'user2@example.com', password: 'password123' } // 같은 비밀번호
    ];
    
    for (const userData of users) {
        try {
            const user = await registerUser(userData.email, userData.password);
            console.log(`사용자 ${user.email} 등록됨`);
        } catch (error) {
            console.log(`사용자 ${userData.email} 등록 실패: ${error.message}`);
        }
    }
}

testRegistration();
```

### 로그인 프로세스

```javascript
// 사용자 저장소 (실제로는 데이터베이스)
const userStore = new Map();

async function loginUser(email, password) {
    try {
        // 1. 사용자 정보 조회 (실제로는 DB에서 조회)
        const user = userStore.get(email);
        
        if (!user) {
            throw new Error('사용자를 찾을 수 없습니다.');
        }
        
        // 2. 비밀번호 검증
        const isValid = await verifyPassword(
            password, 
            user.passwordHash, 
            user.passwordSalt
        );
        
        if (!isValid) {
            throw new Error('비밀번호가 일치하지 않습니다.');
        }
        
        // 3. 로그인 성공 처리
        user.lastLogin = new Date();
        userStore.set(email, user);
        
        console.log('로그인 성공:', {
            email: user.email,
            lastLogin: user.lastLogin
        });
        
        return user;
    } catch (error) {
        console.error('로그인 실패:', error.message);
        throw error;
    }
}

// 로그인 테스트
async function testLogin() {
    // 먼저 사용자 등록
    const user = await registerUser('test@example.com', 'password123');
    userStore.set(user.email, user);
    
    // 정상 로그인
    try {
        await loginUser('test@example.com', 'password123');
    } catch (error) {
        console.log('로그인 실패:', error.message);
    }
    
    // 잘못된 비밀번호
    try {
        await loginUser('test@example.com', 'wrongpassword');
    } catch (error) {
        console.log('잘못된 비밀번호:', error.message);
    }
    
    // 존재하지 않는 사용자
    try {
        await loginUser('nonexistent@example.com', 'password123');
    } catch (error) {
        console.log('존재하지 않는 사용자:', error.message);
    }
}

testLogin();
```

## 📝 요약

PBKDF2는 비밀번호 보안의 핵심 요소들을 모두 포함한 강력한 해싱 방법입니다:

**핵심 구성 요소**
- **솔트**: 레인보우 테이블 공격 방지
- **반복 해싱**: 무차별 대입 공격 저항
- **표준화**: 널리 검증된 알고리즘
- **구현 용이성**: 대부분의 언어에서 지원

**보안 강화 포인트**
- 각 사용자마다 고유한 솔트 사용
- 충분한 반복 횟수 설정 (100,000회 이상 권장)
- 적절한 키 길이 선택 (64바이트 권장)
- 강력한 해시 알고리즘 사용 (SHA-512 권장)

웹 애플리케이션에서 사용자 비밀번호를 안전하게 저장하려면 PBKDF2를 사용하는 것이 좋습니다.

