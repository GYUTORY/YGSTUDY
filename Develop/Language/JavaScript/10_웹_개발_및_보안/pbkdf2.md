---
title: PBKDF2 — 비밀번호 키 유도 함수
tags: [language, javascript]
updated: 2025-11-01
---

# PBKDF2 — 비밀번호 키 유도 함수

## 배경

PBKDF2(Password-Based Key Derivation Function 2)는 비밀번호를 안전하게 저장하는 암호화 표준이다. RSA Security가 2000년 RFC 2898로 처음 내놨고, 지금도 널리 쓰인다.

### 비밀번호 저장의 역사적 문제

#### 평문 저장의 위험성
초기 시스템은 비밀번호를 그대로 데이터베이스에 저장했다. 데이터베이스가 한 번 유출되면 모든 사용자의 비밀번호가 그대로 노출된다. 시스템 관리자조차 사용자 비밀번호를 볼 수 있으니 프라이버시 침해 위험도 있었다.

#### 단순 해시의 한계
그 다음이 MD5, SHA-1 같은 해시 함수다. 해시는 단방향이라 원본 값을 되돌릴 수 없다는 장점이 있었다. 대신 치명적인 약점이 둘 있었다.

첫째, 같은 입력은 언제나 같은 출력을 낸다. "password123"이라는 비밀번호는 언제 어디서 해시해도 같은 값이 나온다. 공격자가 미리 계산해 둔 해시값과 그대로 대조할 수 있다는 말이다.

둘째, 해시 계산이 너무 빠르다. MD5는 초당 수십억 개를 계산하니, 공격자가 가능한 비밀번호 조합을 전부 훑는 데 오래 걸리지 않는다.

### 레인보우 테이블 공격의 실체

레인보우 테이블은 미리 계산해 둔 해시값을 모아 놓은 거대한 데이터베이스다. 작동 방식을 보면 왜 위협인지 바로 보인다.

#### 공격 시나리오
공격자는 흔히 쓰이는 비밀번호 수백만 개를 미리 해시해 테이블로 쌓아 둔다. 예를 들면:
- "password" → 5f4dcc3b5aa765d61d8327deb882cf99 (MD5)
- "123456" → e10adc3949ba59abbe56e057f20f883e (MD5)
- "qwerty" → d8578edf8458ce06fbc5bb76a58c5ca4 (MD5)

데이터베이스가 유출되면 저장된 해시값을 이 테이블과 맞춰 보는 것만으로 원본 비밀번호가 나온다. 8자 이하의 모든 조합을 저장한 레인보우 테이블은 수백 GB 크기로 인터넷에 굴러다닌다.

더 고약한 건 시간-메모리 트레이드오프(Time-Memory Tradeoff) 기법이다. 해시값을 전부 저장하는 대신 체인 형태로 압축하면 저장 공간은 줄이면서 검색은 그대로 빠르다. 이렇게 하면 몇백 GB짜리 테이블 하나로 수조 개의 비밀번호를 커버한다.

### 솔트의 필요성과 작동 원리

솔트는 레인보우 테이블 공격을 무력화하는 핵심이다.

#### 솔트가 없을 때의 문제
사용자 A와 사용자 B가 똑같이 "password123"을 쓰면, 단순 해시에서는 두 사람의 해시값이 완전히 같다. 공격자가 한 사용자의 비밀번호를 알아내는 순간 같은 해시값인 사용자 전원이 함께 뚫린다.

#### 솔트의 작동 원리
솔트는 사용자마다 따로 만드는 고유한 무작위 값이다. 비밀번호를 해시하기 전에 이 솔트를 붙인다:

```
해시값 = Hash(비밀번호 + 솔트)
```

이제 같은 "password123"이라도:
- 사용자 A: Hash("password123" + "a8f5c2d1") = 결과1
- 사용자 B: Hash("password123" + "7e3b9f42") = 결과2

해시값이 완전히 갈린다. 공격자는 사용자별 솔트에 맞춰 레인보우 테이블을 새로 만들어야 하는데, 현실적으로 불가능하다. 16바이트 솔트를 쓰면 조합이 2^128 가지라, 각각에 맞는 테이블을 만들자면 지구상의 저장 공간을 다 긁어모아도 모자란다.

### 반복 해싱의 원리

#### 시간 복잡도를 공격자의 적으로
단순 해시는 너무 빠른 게 문제다. 최신 GPU는 초당 수십억 번의 MD5 해시를 돌린다. 반복 해싱은 계산을 일부러 느리게 만들어 공격자의 시간을 잡아먹는다.

#### 작동 방식
PBKDF2는 해시 함수를 반복해서 적용한다:

```
첫 번째: Hash(비밀번호 + 솔트)
두 번째: Hash(첫 번째 결과)
세 번째: Hash(두 번째 결과)
...
100,000번째: Hash(99,999번째 결과)
```

정상 사용자는 로그인할 때 한 번만 계산하니 0.1~0.2초 정도 걸려도 괜찮다. 반면 공격자가 100만 개의 비밀번호를 시도하려면 수만 시간이 든다.

#### 무차별 대입 공격(Brute Force)의 비용 증가
반복 횟수가 100,000회일 때와 1,000회일 때를 비교하면:
- 1,000회: 8자리 비밀번호 전체 탐색 - 약 30일
- 100,000회: 8자리 비밀번호 전체 탐색 - 약 8년

반복 횟수를 100배 올리면 공격 시간도 100배로 뛴다. CPU/GPU 성능이 좋아지는 만큼 반복 횟수도 같이 올려야 한다. 2000년에는 10,000회로 충분했지만 2025-11 기준 권장치는 100,000~200,000회다.

### 키 유도 함수(Key Derivation Function)의 개념

PBKDF2의 "Key Derivation Function"은 비밀번호라는 상대적으로 약한 입력에서 암호학적으로 강한 키를 뽑아낸다는 뜻이다.

#### 비밀번호와 암호화 키의 차이
비밀번호는 사람이 외울 수 있는 문자열이다. 대개 엔트로피가 낮고(정보량이 적고), 패턴이 보이고, 사전에 나오는 단어가 섞인다. 암호화 키는 반대다. 완전히 무작위여야 하고 엔트로피가 높아야 한다.

PBKDF2는 "password123" 같은 약한 비밀번호를 256비트나 512비트의 강력한 키로 바꾼다. 결과물은 암호학적으로 안전한 무작위 데이터처럼 보이고, 원본 비밀번호의 패턴을 전혀 드러내지 않는다.

#### 슬로우 해시(Slow Hash)의 철학
PBKDF2는 "슬로우 해시" 또는 "적응형 해시 함수"라고 부른다. 일반 해시 함수의 목표가 "빠른 계산"이라면, 슬로우 해시의 목표는 "계산 시간 조절"이다. 반복 횟수라는 매개변수 하나로 보안 수준을 하드웨어 성능에 맞춰 조정한다.

미래를 염두에 둔 설계다. 하드웨어가 발전해도 반복 횟수만 늘리면 동일한 보안 수준이 유지된다.

## 핵심

### 1. 솔트(Salt)

#### 정의와 특징
솔트는 비밀번호에 덧붙이는 무작위 데이터다. 사용자마다 고유한 값이라 같은 비밀번호여도 해시 결과가 달라지고, 그래서 레인보우 테이블 공격이 막힌다.

#### 솔트의 암호학적 역할
솔트는 그냥 "추가 문자열"이 아니다. 암호학적으로 안전한 난수 생성기(CSPRNG - Cryptographically Secure Pseudo-Random Number Generator)로 만들어야 한다. 일반 `Math.random()`은 예측이 가능하니 절대 쓰면 안 된다.

솔트의 주요 역할:
1. **사전 계산 공격 방어**: 공격자가 미리 계산한 해시 테이블이 무용지물이 된다
2. **동일 비밀번호 식별 방지**: 시스템 안에서 같은 비밀번호를 쓰는 사용자를 골라낼 수 없다
3. **병렬 공격 방어**: 여러 사용자를 한꺼번에 노려도 각각 독립적으로 계산해야 한다

#### 솔트 길이의 중요성
솔트 길이는 보안에 그대로 반영된다. 너무 짧으면 공격자가 가능한 솔트 값을 전부 훑어 레인보우 테이블을 만들어 버린다.

- **8바이트(64비트)**: 2^64 = 약 1,800경 가지. 이론상 많아 보여도 요즘 기준으로는 모자란다
- **16바이트(128비트)**: 2^128 = 약 3.4×10^38 가지. 현재 권장하는 최소 크기다
- **32바이트(256비트)**: 2^256 가지. 보안 요구가 극단적으로 높을 때 쓴다

실무 표준은 16바이트다. 전 세계 컴퓨터를 다 끌어와도 수십억 년이 걸리는 수준이다.

#### 솔트 저장 방식
솔트를 따로 숨겨야 한다고 오해하는 사람이 많은데, 솔트는 비밀이 아니다. 해시값 옆에 평문으로 저장해도 된다. 솔트의 보안성은 "비밀"이 아니라 "무작위성"과 "고유성"에서 나온다.

흔한 데이터베이스 구조:
```
users 테이블
- id: 사용자 ID
- email: 이메일
- password_hash: PBKDF2로 생성된 해시 (Base64 인코딩)
- password_salt: 해당 해시에 사용된 솔트 (Base64 인코딩)
- created_at: 생성 시각
```

해시와 솔트를 한 문자열로 합쳐 두는 시스템도 있다:
```
$pbkdf2-sha256$100000$솔트값$해시값
```

#### 솔트 생성 예시
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

#### 정의와 목적
반복 해싱은 해시 함수를 여러 번 되풀이해 적용하는 과정이다. 해킹 시도를 어렵게 만드는 핵심이고 반복 횟수가 많을수록 보안성이 올라간다. 권장 반복 횟수는 100,000회 이상.

#### 작업 증명(Proof of Work) 개념
반복 해싱은 일종의 "작업 증명" 장치다. 비밀번호를 해시하려면 실제로 계산 작업을 수행해야 하고, 건너뛸 방법이 없다. 비트코인의 채굴과 비슷한 개념인데 목적은 다르다:
- **비트코인**: 네트워크 참여 비용을 만들어 스팸 방지
- **PBKDF2**: 공격자의 시간을 소비시켜 무차별 대입 공격 방지

#### 반복 횟수 선택 기준
반복 횟수는 시스템 성능과 사용자 경험 사이에서 접점을 찾는 문제다.

**사용자 관점**:
- 로그인 시 0.1~0.5초 정도의 지연은 거의 못 느낀다
- 1초를 넘기면 그때부터 불편해한다
- 서버에서 처리하니 클라이언트 기기 성능은 거의 상관없다

**공격자 관점**:
- 한 번의 해시에 0.1초가 걸린다면, 100만 개 시도에 27.7시간 필요
- 한 번의 해시에 0.01초가 걸린다면, 100만 개 시도에 2.7시간 필요
- 이 차이가 공격의 성패를 가른다

**시대별 권장 반복 횟수**:
- 2000년 (RFC 2898 발표): 1,000~10,000회
- 2010년: 10,000~50,000회
- 2020년: 100,000~200,000회
- 2025-11 기준: 100,000~600,000회

하드웨어는 해마다 빨라지니, 이미 돌아가는 시스템도 주기적으로 반복 횟수를 늘려야 한다.

#### GPU/ASIC 공격 대응
단순 해시 함수는 GPU나 ASIC에서 병렬로 수백만 번 돌아간다. 반복 해싱도 이런 공격에서 자유롭진 않지만 계산 비용이 선형으로 늘어난다:

- SHA-256 단일 해시: GPU에서 초당 10억 회
- PBKDF2 (100,000회 반복): GPU에서 초당 10,000회

속도가 100,000배 떨어진다. 공격자가 하드웨어에 투자한 만큼 효율을 못 뽑게 하는 게 목표다.

#### 적응형 비용 함수
PBKDF2의 큰 장점은 반복 횟수를 나중에 바꿀 수 있다는 것이다. 이걸 "적응형 비용 함수(Adaptive Cost Function)"라고 한다.

마이그레이션 전략:
1. 새로운 사용자는 높은 반복 횟수(예: 200,000회)로 해시 생성
2. 기존 사용자가 로그인할 때마다 반복 횟수 확인
3. 낮은 반복 횟수를 사용 중이면, 로그인 성공 시 새로운 반복 횟수로 재해시
4. 점진적으로 전체 시스템의 보안 수준 향상

사용자에게 비밀번호 재설정을 강요하지 않고도 보안을 끌어올리는 방법이다.

#### 반복 횟수에 따른 시간 차이
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

#### 정의와 선택 기준
키 길이는 최종 해시 결과의 길이다. 보안성과 성능을 저울질해 고르는데, 보통 64바이트(512비트)를 쓴다. 너무 짧으면 보안성이 떨어지고, 너무 길면 성능이 깎인다.

#### 출력 길이와 내부 해시 함수의 관계
PBKDF2의 출력 길이는 내부에서 쓰는 해시 함수와 맞물린다:

- **SHA-1**: 160비트(20바이트) 출력
- **SHA-256**: 256비트(32바이트) 출력
- **SHA-512**: 512비트(64바이트) 출력

요청한 키 길이가 해시 함수의 출력 길이보다 길면, PBKDF2가 내부에서 블록을 여러 개 만들어 이어 붙인다. SHA-256(32바이트)을 쓰면서 64바이트 키를 요청하면 해시 블록을 두 번 계산한다.

#### 키 길이가 보안에 미치는 영향
키 길이는 "얼마나 많은 정보를 해시에 담을 것인가"를 정한다.

**충돌 저항성(Collision Resistance)**:
해시 충돌은 서로 다른 입력이 같은 해시값을 내놓는 현상이다. 생일 역설(Birthday Paradox)을 따르면 n비트 해시는 2^(n/2) 언저리에서 충돌이 나온다:
- 128비트: 2^64 (약 184억 번) 시도 후 충돌 가능
- 256비트: 2^128 시도 후 충돌 가능
- 512비트: 2^256 시도 후 충돌 가능

비밀번호 해싱에서 충돌 자체는 큰 문제가 아니지만(사용자마다 솔트가 다르니까), 이론적인 보안 강도를 보여주는 지표는 된다.

**역상 저항성(Preimage Resistance)**:
해시값만 놓고 원본 입력을 찾아내기가 얼마나 어려운지를 말한다. n비트 해시는 평균 2^n번의 시도가 필요하다:
- 256비트: 2^256 = 우주의 원자 수보다 많음
- 512비트: 2^512 = 상상을 초월하는 수

256비트 이상이면 현재 기술로는 사실상 안 깨진다.

#### 저장 공간과 성능 고려사항
키 길이는 데이터베이스 저장 공간에도 영향을 준다:

**Base64 인코딩 기준**:
- 32바이트(256비트): 44자
- 64바이트(512비트): 88자
- 128바이트(1024비트): 172자

VARCHAR(100)으로는 64바이트 해시가 안 들어간다. VARCHAR(255)나 TEXT 타입을 써야 한다.

**네트워크 전송 비용**:
API로 해시값을 실어 보낸다면 키 길이가 네트워크 대역폭에 영향을 준다. 그래도 64바이트(88자)는 JSON 응답에서 무시할 만한 크기다.

#### 실무 권장사항
**일반적인 웹 애플리케이션**:
- SHA-256 사용 시: 32바이트
- SHA-512 사용 시: 64바이트 (권장)

**높은 보안이 필요한 시스템**:
- 64바이트 또는 그 이상
- 하지만 128바이트 이상은 실질적인 보안 향상이 거의 없음

**레거시 시스템**:
- 최소 16바이트 이상 (128비트)
- 이보다 짧으면 보안 위험이 있음

#### 키 길이별 비교
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

## 예시

### 기본 PBKDF2 구현

#### 비밀번호 해싱 함수
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

#### 비밀번호 검증 함수
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

### 고급 설정 예제

#### 솔트 설정
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

#### 반복 횟수 설정
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

#### 해시 알고리즘 선택
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

### 완전한 사용자 인증 시스템

#### 사용자 등록 및 로그인 시스템
```javascript
const crypto = require('crypto');

// 간단한 사용자 저장소 (실제로는 데이터베이스 사용)
const userStore = new Map();

// 사용자 등록
async function registerUser(email, password) {
    try {
        // 비밀번호 해싱
        const result = await hashPassword(password);
        
        const user = {
            email: email,
            passwordHash: result.hash,
            passwordSalt: result.salt,
            createdAt: new Date(),
            lastLogin: null
        };
        
        userStore.set(email, user);
        
        console.log('사용자 등록 성공:', {
            email: user.email,
            createdAt: user.createdAt
        });
        
        return user;
    } catch (error) {
        console.error('사용자 등록 실패:', error.message);
        throw error;
    }
}

// 사용자 로그인
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

## 운영 팁

### 보안 강화 방법

#### 솔트 관리
```javascript
// 절대 재사용 금지
// 각 사용자마다 고유한 솔트 사용
// 같은 솔트를 여러 사용자에게 사용하면 보안성 크게 저하

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

#### 반복 횟수 조정
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

#### 에러 처리
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
    try {
        await safeHashPassword(''); // 빈 비밀번호
    } catch (error) {
        console.log('에러:', error.message);
    }
    
    try {
        await safeHashPassword('123'); // 너무 짧은 비밀번호
    } catch (error) {
        console.log('에러:', error.message);
    }
    
    try {
        await safeHashPassword('validPassword123'); // 정상 비밀번호
        console.log('정상 처리됨');
    } catch (error) {
        console.log('에러:', error.message);
    }
}

testErrorHandling();
```

### 성능 최적화

#### 해싱 방법 비교
```javascript
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

## 참고

### 기존 해시에서 PBKDF2로 전환

#### 마이그레이션 전략
```javascript
// 기존 MD5 해시 검증 함수 (예시)
function verifyOldHash(password, oldHash) {
    const hash = crypto.createHash('md5').update(password).digest('hex');
    return hash === oldHash;
}

// PBKDF2로 마이그레이션
async function migrateToPBKDF2(user) {
    // 1. 기존 해시로 로그인 확인
    const isValidOldHash = verifyOldHash(user.inputPassword, user.oldHash);
    
    if (isValidOldHash) {
        // 2. PBKDF2로 새 해시 생성
        const newHashResult = await hashPassword(user.inputPassword);
        
        // 3. 데이터베이스 업데이트
        user.passwordHash = newHashResult.hash;
        user.passwordSalt = newHashResult.salt;
        user.hashAlgorithm = 'pbkdf2';
        user.migratedAt = new Date();
        
        console.log('마이그레이션 완료:', user.email);
        return user;
    } else {
        throw new Error('기존 비밀번호가 일치하지 않습니다.');
    }
}

// 점진적 마이그레이션
async function gradualMigration() {
    const users = [
        { email: 'user1@example.com', oldHash: 'oldHash1', inputPassword: 'password123' },
        { email: 'user2@example.com', oldHash: 'oldHash2', inputPassword: 'password456' }
    ];
    
    for (const user of users) {
        try {
            await migrateToPBKDF2(user);
        } catch (error) {
            console.error(`마이그레이션 실패 (${user.email}):`, error.message);
        }
    }
}
```

### PBKDF2와 다른 비밀번호 해싱 방법 비교

#### bcrypt
**작동 원리**:
bcrypt는 Blowfish 암호화 알고리즘을 바탕으로 설계했다. PBKDF2와 마찬가지로 반복 해싱을 쓰지만 반복량을 "비용 인자(cost factor)"라는 지수 단위로 다룬다.

**장점**:
- 메모리 집약적 설계로 GPU 공격에 더 강함
- 솔트가 자동으로 생성되고 해시에 포함됨
- 비용 인자를 1 증가시키면 시간이 2배로 늘어남 (지수적 증가)

**단점**:
- 최대 72바이트 비밀번호 길이 제한
- 8비트 문자만 완벽히 지원 (일부 구현에서 유니코드 문제)
- 출력 길이가 고정 (60자)

**PBKDF2와의 차이**:
- PBKDF2는 선형적 반복 (100,000회 → 200,000회 = 2배)
- bcrypt는 지수적 반복 (cost 10 → cost 11 = 2배)
- bcrypt가 GPU 저항성이 더 높지만 PBKDF2가 더 유연함

#### scrypt
**작동 원리**:
scrypt는 메모리와 CPU를 둘 다 많이 쓰도록 설계한 알고리즘이다. 병렬화가 까다로운 메모리 하드(Memory-hard) 함수다.

**장점**:
- 메모리 사용량을 매개변수로 조절 가능
- GPU/ASIC 공격에 매우 강함 (메모리 비용 때문)
- 고급 하드웨어의 병렬 처리 이점을 크게 감소

**단점**:
- 메모리 소비가 커서 서버 자원에 부담
- DDoS 공격에 취약할 수 있음 (메모리 고갈)
- 상대적으로 복잡한 설정

**PBKDF2와의 차이**:
- PBKDF2는 CPU만 사용
- scrypt는 CPU + 메모리 사용
- scrypt가 보안성은 높지만 자원 관리가 더 복잡함

#### Argon2
**작동 원리**:
2015년 Password Hashing Competition 우승작이다. scrypt를 개선한 알고리즘으로, 메모리 하드 함수이면서 DDoS 공격 방어 메커니즘까지 넣었다.

**장점**:
- 메모리, 시간, 병렬화 정도를 독립적으로 조절 가능
- 최신 공격 기법에 대한 저항성
- 3가지 변형 제공 (Argon2d, Argon2i, Argon2id)

**단점**:
- 상대적으로 최신 알고리즘 (검증 기간이 짧음)
- 일부 언어/플랫폼에서 기본 지원 부족
- 설정이 복잡함

**PBKDF2와의 차이**:
- 현재 가장 권장되는 알고리즘
- 하지만 PBKDF2가 더 널리 지원되고 검증됨

#### 실무 선택 기준
**PBKDF2를 선택하는 경우**:
- 표준 준수가 중요한 경우 (NIST, FIPS 인증)
- 레거시 시스템과의 호환성
- 간단한 설정과 이식성
- 충분한 반복 횟수로 적절한 보안 확보

**bcrypt를 선택하는 경우**:
- GPU 공격 저항성이 중요한 경우
- 간단한 API 선호
- 짧은 비밀번호만 사용

**scrypt를 선택하는 경우**:
- 매우 높은 보안 요구사항
- 서버 자원이 충분한 경우
- GPU/ASIC 공격이 주요 위협

**Argon2를 선택하는 경우**:
- 새로운 프로젝트
- 최신 보안 표준 적용
- 세밀한 성능 조정 필요

### PBKDF2의 내부 동작 원리

#### HMAC 기반 의사 난수 함수
PBKDF2는 HMAC(Hash-based Message Authentication Code)을 의사 난수 함수(PRF - Pseudo-Random Function)로 쓴다.

**HMAC의 역할**:
```
HMAC(key, message) = Hash((key ⊕ opad) || Hash((key ⊕ ipad) || message))
```

여기서:
- `opad`와 `ipad`는 고정된 패딩 값
- `⊕`는 XOR 연산
- `||`는 연결(concatenation)

PBKDF2에서는:
- `key` = 비밀번호
- `message` = 솔트 + 블록 인덱스

#### 블록 생성 과정
PBKDF2가 요청받은 키 길이를 만들어 내는 과정:

```
DK = T₁ || T₂ || ... || T_dkLen/hLen

여기서 각 블록 Tᵢ는:
T₁ = F(Password, Salt, iterations, 1)
T₂ = F(Password, Salt, iterations, 2)
...

F 함수의 내부:
U₁ = PRF(Password, Salt || INT_32_BE(i))
U₂ = PRF(Password, U₁)
U₃ = PRF(Password, U₂)
...
Uₙ = PRF(Password, Uₙ₋₁)

Tᵢ = U₁ ⊕ U₂ ⊕ U₃ ⊕ ... ⊕ Uₙ
```

**XOR 연결의 의미**:
마지막 값만 쓰지 않고 반복마다 나온 결과를 XOR로 묶는다. "키 강화(Key Stretching)"의 핵심이다. 공격자가 중간 단계를 건너뛸 수 없게 만든다.

#### 왜 단순 반복이 아닌가?
단순히 `Hash(Hash(Hash(...)))` 형태로 반복하지 않는 이유:

1. **확장 공격(Extension Attack) 방지**: 각 반복이 이전 결과에만 의존하면, 공격자가 중간 상태를 저장해두고 재사용할 수 있다

2. **모든 반복의 엔트로피 보존**: XOR 결합으로 모든 반복의 정보가 최종 결과에 반영된다

3. **병렬 처리 어려움**: 마지막 블록을 계산하려면 모든 이전 블록을 알아야 한다

### 실전 보안 고려사항

#### 타이밍 공격(Timing Attack) 방어
비밀번호를 검증할 때는 타이밍 공격을 조심해야 한다:

**취약한 코드**:
```javascript
if (hash1 === hash2) {  // 문자열 비교는 첫 불일치에서 중단
    return true;
}
```

응답 시간 차이만으로 해시의 일부가 새어 나간다.

**안전한 코드**:
```javascript
// 상수 시간 비교 (Constant-time comparison)
function secureCompare(a, b) {
    if (a.length !== b.length) {
        return false;
    }
    let result = 0;
    for (let i = 0; i < a.length; i++) {
        result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return result === 0;
}
```

언제나 모든 문자를 비교하니 타이밍 정보가 유출되지 않는다.

#### 비밀번호 정책과의 관계
PBKDF2가 약한 비밀번호를 강하게 만들어 주지는 않는다. "123456"을 PBKDF2로 해싱해도, 공격자가 "123456"을 먼저 시도하면 그대로 뚫린다.

**필수 비밀번호 정책**:
- 최소 8자 이상 (권장 12자)
- 대소문자, 숫자, 특수문자 조합
- 일반적인 단어 금지 (사전 공격 방지)
- 이전 비밀번호 재사용 금지
- 정기적인 변경 권장

PBKDF2는 "강한 비밀번호를 더 안전하게 저장"하는 도구다.

#### 레이트 리미팅(Rate Limiting)
PBKDF2만으로는 부족하다. 로그인 시도 제한도 같이 걸어야 한다:

```javascript
// IP당 시간당 로그인 시도 제한
const loginAttempts = new Map();

function checkRateLimit(ip) {
    const now = Date.now();
    const attempts = loginAttempts.get(ip) || [];
    
    // 1시간 이내 시도만 필터링
    const recentAttempts = attempts.filter(t => now - t < 3600000);
    
    if (recentAttempts.length >= 5) {
        throw new Error('너무 많은 로그인 시도. 1시간 후 다시 시도하세요.');
    }
    
    recentAttempts.push(now);
    loginAttempts.set(ip, recentAttempts);
}
```

#### 페퍼(Pepper) 추가
솔트 말고 "페퍼(Pepper)"라는 보안 계층을 하나 더 둘 수도 있다:

**솔트 vs 페퍼**:
- **솔트**: 각 비밀번호마다 다름, 데이터베이스에 저장
- **페퍼**: 모든 비밀번호에 동일, 환경변수나 별도 저장소에 보관

```javascript
const PEPPER = process.env.PASSWORD_PEPPER; // 환경변수에서 로드

async function hashPasswordWithPepper(password) {
    const pepperedPassword = password + PEPPER;
    const salt = crypto.randomBytes(16);
    
    const key = await new Promise((resolve, reject) => {
        crypto.pbkdf2(pepperedPassword, salt, 100000, 64, 'sha512', (err, key) => {
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

데이터베이스가 통째로 새어도 페퍼를 모르면 해시를 검증하지 못한다.

### 결론

PBKDF2는 2000년부터 굴러온 검증된 비밀번호 해싱 표준이다. 최신 알고리즘(Argon2, scrypt)보다 보안성이 낮을 수는 있어도, 반복 횟수만 충분히 주면 지금도 안전하다.

**핵심 구성 요소**:
- **솔트**: 각 사용자마다 고유한 무작위 값으로 레인보우 테이블 공격 방지
- **반복 해싱**: 계산 비용을 늘려 무차별 대입 공격을 시간적으로 불가능하게 만듦
- **적응성**: 하드웨어 발전에 따라 반복 횟수를 조정하여 보안 수준 유지
- **표준화**: NIST, FIPS 승인으로 규제 준수가 필요한 시스템에 적합

**2025년 권장 설정**:
- 솔트: 16바이트 이상
- 반복 횟수: 100,000~600,000회 (시스템 성능에 따라)
- 키 길이: 64바이트 (512비트)
- 해시 알고리즘: SHA-512

**추가 보안 계층**:
- 강력한 비밀번호 정책
- 레이트 리미팅 (시도 횟수 제한)
- 타이밍 공격 방어
- 선택적으로 페퍼 사용

PBKDF2 하나로 보안이 완성되지는 않는다. 다층 방어(Defense in Depth) 전략의 한 부분이니, 다른 보안 수단들과 함께 써야 한다.
