---
title: PBKDF2 (Password-Based Key Derivation Function 2)
tags: [language, javascript, 10웹개발및보안, pbkdf2, password-security, cryptography]
updated: 2025-11-01
---

# PBKDF2 (Password-Based Key Derivation Function 2)

## 배경

PBKDF2(Password-Based Key Derivation Function 2)는 비밀번호를 안전하게 저장하기 위한 암호화 표준입니다. RSA Security가 2000년 RFC 2898에서 처음 발표했으며, 현재까지도 널리 사용되는 표준 방식입니다.

### 비밀번호 저장의 역사적 문제

#### 평문 저장의 위험성
초기 시스템들은 비밀번호를 그대로 데이터베이스에 저장했습니다. 이는 데이터베이스가 유출되면 모든 사용자의 비밀번호가 그대로 노출되는 심각한 문제를 가지고 있었습니다. 시스템 관리자조차 사용자의 비밀번호를 볼 수 있어 프라이버시 침해 위험도 존재했습니다.

#### 단순 해시의 한계
그 다음 단계로 MD5, SHA-1 같은 해시 함수를 사용하기 시작했습니다. 해시는 단방향 함수로 원본 값을 알 수 없다는 장점이 있었습니다. 하지만 두 가지 치명적인 약점이 있었습니다.

첫째, 같은 입력은 항상 같은 출력을 생성합니다. 예를 들어 "password123"이라는 비밀번호는 언제 어디서 해시해도 같은 값이 나옵니다. 이는 공격자가 미리 계산한 해시값과 비교할 수 있다는 의미입니다.

둘째, 해시 계산이 매우 빠릅니다. MD5는 초당 수십억 개의 해시를 계산할 수 있어서, 공격자가 모든 가능한 비밀번호 조합을 빠르게 시도할 수 있습니다.

### 레인보우 테이블 공격의 실체

레인보우 테이블은 미리 계산된 해시값들의 거대한 데이터베이스입니다. 작동 방식을 이해하면 왜 이것이 위협인지 알 수 있습니다.

#### 공격 시나리오
공격자는 자주 사용되는 비밀번호 수백만 개를 미리 해시해서 테이블을 만들어 둡니다. 예를 들면:
- "password" → 5f4dcc3b5aa765d61d8327deb882cf99 (MD5)
- "123456" → e10adc3949ba59abbe56e057f20f883e (MD5)
- "qwerty" → d8578edf8458ce06fbc5bb76a58c5ca4 (MD5)

데이터베이스가 유출되면 저장된 해시값을 이 테이블과 비교하여 즉시 원본 비밀번호를 찾아냅니다. 실제로 8자 이하의 모든 조합을 저장한 레인보우 테이블은 수백 GB 크기로 인터넷에서 구할 수 있습니다.

더 심각한 것은 시간-메모리 트레이드오프(Time-Memory Tradeoff) 기법입니다. 모든 해시값을 저장하는 대신, 체인 형태로 압축해서 저장 공간을 줄이면서도 빠르게 검색할 수 있습니다. 이렇게 하면 몇백 GB의 테이블로 수조 개의 비밀번호를 커버할 수 있습니다.

### 솔트의 필요성과 작동 원리

솔트는 레인보우 테이블 공격을 무력화하는 핵심 개념입니다.

#### 솔트가 없을 때의 문제
사용자 A와 사용자 B가 모두 "password123"을 비밀번호로 사용한다면, 단순 해시에서는 두 사용자의 해시값이 완전히 동일합니다. 공격자가 한 사용자의 비밀번호를 알아내면, 같은 해시값을 가진 모든 사용자의 비밀번호도 동시에 알아낼 수 있습니다.

#### 솔트의 작동 원리
솔트는 각 사용자마다 생성되는 고유한 무작위 값입니다. 비밀번호를 해시하기 전에 이 솔트를 결합합니다:

```
해시값 = Hash(비밀번호 + 솔트)
```

이제 같은 "password123"을 사용해도:
- 사용자 A: Hash("password123" + "a8f5c2d1") = 결과1
- 사용자 B: Hash("password123" + "7e3b9f42") = 결과2

완전히 다른 해시값이 생성됩니다. 공격자는 각 사용자의 솔트에 맞춰 레인보우 테이블을 새로 만들어야 하는데, 이는 현실적으로 불가능합니다. 16바이트 솔트를 사용하면 2^128 가지의 서로 다른 조합이 생기므로, 각각에 대한 레인보우 테이블을 만드는 것은 지구상의 모든 저장 공간을 합쳐도 부족합니다.

### 반복 해싱의 원리

#### 시간 복잡도를 공격자의 적으로
단순 해시는 너무 빠르다는 것이 문제입니다. 최신 GPU는 초당 수십억 번의 MD5 해시를 계산할 수 있습니다. 반복 해싱은 의도적으로 계산을 느리게 만들어 공격자의 시간을 소비하게 합니다.

#### 작동 방식
PBKDF2는 해시 함수를 반복적으로 적용합니다:

```
첫 번째: Hash(비밀번호 + 솔트)
두 번째: Hash(첫 번째 결과)
세 번째: Hash(두 번째 결과)
...
100,000번째: Hash(99,999번째 결과)
```

정상 사용자는 로그인할 때 한 번만 계산하면 되므로 0.1~0.2초 정도 걸려도 괜찮습니다. 하지만 공격자가 100만 개의 비밀번호를 시도하려면 수만 시간이 필요하게 됩니다.

#### 무차별 대입 공격(Brute Force)의 비용 증가
반복 횟수가 100,000회일 때와 1,000회일 때를 비교하면:
- 1,000회: 8자리 비밀번호 전체 탐색 - 약 30일
- 100,000회: 8자리 비밀번호 전체 탐색 - 약 8년

반복 횟수가 100배 증가하면 공격 시간도 100배 증가합니다. 기술이 발전하면서 CPU/GPU 성능이 향상되면, 반복 횟수도 함께 늘려야 합니다. 2000년에는 10,000회가 충분했지만, 2025년 현재는 100,000~200,000회를 권장합니다.

### 키 유도 함수(Key Derivation Function)의 개념

PBKDF2의 "Key Derivation Function"은 비밀번호라는 상대적으로 약한 입력에서 암호학적으로 강력한 키를 생성한다는 의미입니다.

#### 비밀번호와 암호화 키의 차이
비밀번호는 사람이 기억할 수 있는 문자열입니다. 보통 엔트로피가 낮고(정보량이 적고), 패턴이 있으며, 사전에 나오는 단어를 포함합니다. 반면 암호화 키는 완전히 무작위이며, 높은 엔트로피를 가져야 합니다.

PBKDF2는 "password123" 같은 약한 비밀번호를 256비트나 512비트의 강력한 키로 변환합니다. 이 키는 암호학적으로 안전한 무작위 데이터처럼 보이며, 원본 비밀번호의 패턴을 전혀 드러내지 않습니다.

#### 슬로우 해시(Slow Hash)의 철학
PBKDF2는 "슬로우 해시" 또는 "적응형 해시 함수"라고 불립니다. 일반 해시 함수의 목표가 "빠른 계산"이라면, 슬로우 해시의 목표는 "계산 시간 조절"입니다. 반복 횟수라는 매개변수를 통해 보안 수준을 하드웨어 성능에 맞춰 조정할 수 있습니다.

이는 미래 지향적 설계입니다. 하드웨어가 발전해도 반복 횟수만 늘리면 동일한 보안 수준을 유지할 수 있습니다.

## 핵심

### 1. 솔트(Salt)

#### 정의와 특징
솔트는 비밀번호에 추가하는 무작위 데이터입니다. 각 사용자마다 고유한 값으로, 같은 비밀번호라도 다른 해시 결과를 생성하여 레인보우 테이블 공격을 방지합니다.

#### 솔트의 암호학적 역할
솔트는 단순히 "추가 문자열"이 아닙니다. 암호학적으로 안전한 난수 생성기(CSPRNG - Cryptographically Secure Pseudo-Random Number Generator)를 통해 생성되어야 합니다. 일반 `Math.random()`은 예측 가능하므로 절대 사용해서는 안 됩니다.

솔트의 주요 역할:
1. **사전 계산 공격 방어**: 공격자가 미리 계산한 해시 테이블을 무용지물로 만듭니다
2. **동일 비밀번호 식별 방지**: 시스템 내에서 같은 비밀번호를 사용하는 사용자들을 찾을 수 없게 합니다
3. **병렬 공격 방어**: 공격자가 여러 사용자를 동시에 공격하더라도, 각각을 독립적으로 계산해야 합니다

#### 솔트 길이의 중요성
솔트 길이는 보안에 직접적인 영향을 미칩니다. 너무 짧으면 공격자가 모든 가능한 솔트 값에 대해 레인보우 테이블을 만들 수 있습니다.

- **8바이트(64비트)**: 2^64 = 약 1,800경 가지. 이론적으로는 많아 보이지만, 현대 기준으로는 부족합니다
- **16바이트(128비트)**: 2^128 = 약 3.4×10^38 가지. 현재 권장되는 최소 크기입니다
- **32바이트(256비트)**: 2^256 가지. 극도로 높은 보안이 필요한 경우 사용합니다

실무에서는 16바이트를 표준으로 사용합니다. 이는 전 세계 모든 컴퓨터를 동원해도 수십억 년이 걸리는 수준입니다.

#### 솔트 저장 방식
많은 사람들이 솔트를 별도로 숨겨야 한다고 오해하지만, 솔트는 비밀이 아닙니다. 해시값과 함께 평문으로 저장해도 됩니다. 솔트의 보안성은 "비밀"이 아니라 "무작위성"과 "고유성"에서 나옵니다.

일반적인 데이터베이스 구조:
```
users 테이블
- id: 사용자 ID
- email: 이메일
- password_hash: PBKDF2로 생성된 해시 (Base64 인코딩)
- password_salt: 해당 해시에 사용된 솔트 (Base64 인코딩)
- created_at: 생성 시각
```

일부 시스템은 해시와 솔트를 하나의 문자열로 결합하기도 합니다:
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
반복 해싱은 해시 함수를 여러 번 반복 적용하는 과정입니다. 해킹 시도를 어렵게 만드는 핵심 요소로, 반복 횟수가 많을수록 보안성이 증가합니다. 권장 반복 횟수는 100,000회 이상입니다.

#### 작업 증명(Proof of Work) 개념
반복 해싱은 일종의 "작업 증명" 메커니즘입니다. 비밀번호를 해시하려면 실제로 계산 작업을 수행해야 하며, 이를 건너뛸 방법이 없습니다. 비트코인의 채굴과 유사한 개념이지만, 목적은 다릅니다:
- **비트코인**: 네트워크 참여 비용을 만들어 스팸 방지
- **PBKDF2**: 공격자의 시간을 소비시켜 무차별 대입 공격 방지

#### 반복 횟수 선택 기준
반복 횟수는 시스템의 성능과 사용자 경험 사이의 균형점을 찾아야 합니다.

**사용자 관점**:
- 로그인 시 0.1~0.5초 정도의 지연은 거의 느껴지지 않습니다
- 1초 이상 걸리면 사용자가 불편함을 느끼기 시작합니다
- 서버에서 처리하므로 클라이언트 기기 성능은 크게 영향 없습니다

**공격자 관점**:
- 한 번의 해시에 0.1초가 걸린다면, 100만 개 시도에 27.7시간 필요
- 한 번의 해시에 0.01초가 걸린다면, 100만 개 시도에 2.7시간 필요
- 이 차이가 공격의 성공 여부를 결정합니다

**시대별 권장 반복 횟수**:
- 2000년 (RFC 2898 발표): 1,000~10,000회
- 2010년: 10,000~50,000회
- 2020년: 100,000~200,000회
- 2025년 현재: 100,000~600,000회

매년 하드웨어 성능이 향상되므로, 기존 시스템도 주기적으로 반복 횟수를 늘려야 합니다.

#### GPU/ASIC 공격 대응
단순 해시 함수는 GPU나 ASIC에서 병렬로 수백만 번 계산할 수 있습니다. 반복 해싱도 이런 공격에 노출되지만, 계산 비용이 선형적으로 증가합니다:

- SHA-256 단일 해시: GPU에서 초당 10억 회
- PBKDF2 (100,000회 반복): GPU에서 초당 10,000회

100,000배의 속도 저하를 만들어냅니다. 공격자의 하드웨어 투자 대비 효율을 크게 떨어뜨리는 것이 목표입니다.

#### 적응형 비용 함수
PBKDF2의 강력한 장점은 반복 횟수를 나중에 변경할 수 있다는 점입니다. 이를 "적응형 비용 함수(Adaptive Cost Function)"라고 합니다.

마이그레이션 전략:
1. 새로운 사용자는 높은 반복 횟수(예: 200,000회)로 해시 생성
2. 기존 사용자가 로그인할 때마다 반복 횟수 확인
3. 낮은 반복 횟수를 사용 중이면, 로그인 성공 시 새로운 반복 횟수로 재해시
4. 점진적으로 전체 시스템의 보안 수준 향상

이는 사용자에게 비밀번호 재설정을 강요하지 않고도 보안을 강화할 수 있는 방법입니다.

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
키 길이는 최종 해시 결과의 길이입니다. 보안성과 성능의 균형을 고려하여 선택하며, 일반적으로 64바이트(512비트)를 사용합니다. 너무 짧으면 보안성 저하, 너무 길면 성능 저하가 발생합니다.

#### 출력 길이와 내부 해시 함수의 관계
PBKDF2의 출력 길이는 사용하는 내부 해시 함수와 밀접한 관련이 있습니다:

- **SHA-1**: 160비트(20바이트) 출력
- **SHA-256**: 256비트(32바이트) 출력
- **SHA-512**: 512비트(64바이트) 출력

요청한 키 길이가 해시 함수의 출력 길이보다 길면, PBKDF2는 내부적으로 여러 블록을 생성하고 연결합니다. 예를 들어 SHA-256(32바이트)을 사용하면서 64바이트 키를 요청하면, 두 번의 해시 블록이 계산됩니다.

#### 키 길이가 보안에 미치는 영향
키 길이는 "얼마나 많은 정보를 해시에 담을 것인가"를 결정합니다.

**충돌 저항성(Collision Resistance)**:
해시 충돌은 서로 다른 입력이 같은 해시값을 만드는 현상입니다. 생일 역설(Birthday Paradox)에 의해, n비트 해시의 충돌 확률은 2^(n/2) 정도에서 발생합니다:
- 128비트: 2^64 (약 184억 번) 시도 후 충돌 가능
- 256비트: 2^128 시도 후 충돌 가능
- 512비트: 2^256 시도 후 충돌 가능

비밀번호 해싱에서 충돌은 큰 문제가 되지 않지만(각 사용자가 다른 솔트를 가지므로), 이론적인 보안 강도를 나타냅니다.

**역상 저항성(Preimage Resistance)**:
주어진 해시값에서 원본 입력을 찾는 것이 얼마나 어려운가를 나타냅니다. n비트 해시는 평균적으로 2^n번의 시도가 필요합니다:
- 256비트: 2^256 = 우주의 원자 수보다 많음
- 512비트: 2^512 = 상상을 초월하는 수

실질적으로 256비트 이상이면 현재 기술로는 절대 깨지지 않습니다.

#### 저장 공간과 성능 고려사항
키 길이는 데이터베이스 저장 공간에도 영향을 미칩니다:

**Base64 인코딩 기준**:
- 32바이트(256비트): 44자
- 64바이트(512비트): 88자
- 128바이트(1024비트): 172자

데이터베이스에서 VARCHAR(100)로는 64바이트 해시를 저장하기에 부족하므로, VARCHAR(255) 또는 TEXT 타입을 사용해야 합니다.

**네트워크 전송 비용**:
API를 통해 해시값을 전송한다면, 키 길이가 네트워크 대역폭에 영향을 줍니다. 하지만 64바이트(88자)는 JSON 응답에서 무시할 만한 크기입니다.

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
bcrypt는 Blowfish 암호화 알고리즘 기반으로 설계되었습니다. PBKDF2와 마찬가지로 반복 해싱을 사용하지만, "비용 인자(cost factor)"라는 지수적 개념을 사용합니다.

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
- bcrypt가 GPU 저항성이 더 높지만, PBKDF2가 더 유연함

#### scrypt
**작동 원리**:
scrypt는 메모리와 CPU를 모두 많이 소비하도록 설계된 알고리즘입니다. 병렬화가 어려운 메모리 하드(Memory-hard) 함수입니다.

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
- scrypt가 보안성은 높지만, 자원 관리가 더 복잡함

#### Argon2
**작동 원리**:
2015년 Password Hashing Competition 우승작입니다. scrypt의 개선판으로, 메모리 하드 함수이면서도 DDoS 공격에 대한 방어 메커니즘을 포함합니다.

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
PBKDF2는 HMAC(Hash-based Message Authentication Code)을 의사 난수 함수(PRF - Pseudo-Random Function)로 사용합니다.

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
PBKDF2가 요청받은 키 길이를 생성하는 과정:

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
각 반복의 결과를 단순히 마지막 값만 사용하지 않고 XOR로 결합합니다. 이는 "키 강화(Key Stretching)"의 핵심입니다. 공격자가 중간 단계를 건너뛸 수 없게 만듭니다.

#### 왜 단순 반복이 아닌가?
단순히 `Hash(Hash(Hash(...)))` 형태로 반복하지 않는 이유:

1. **확장 공격(Extension Attack) 방지**: 각 반복이 이전 결과에만 의존하면, 공격자가 중간 상태를 저장해두고 재사용할 수 있습니다

2. **모든 반복의 엔트로피 보존**: XOR 결합으로 모든 반복의 정보가 최종 결과에 반영됩니다

3. **병렬 처리 어려움**: 마지막 블록을 계산하려면 모든 이전 블록을 알아야 합니다

### 실전 보안 고려사항

#### 타이밍 공격(Timing Attack) 방어
비밀번호 검증 시 타이밍 공격에 주의해야 합니다:

**취약한 코드**:
```javascript
if (hash1 === hash2) {  // 문자열 비교는 첫 불일치에서 중단
    return true;
}
```

공격자는 응답 시간 차이로 해시의 일부를 알아낼 수 있습니다.

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

모든 문자를 항상 비교하므로 타이밍 정보가 유출되지 않습니다.

#### 비밀번호 정책과의 관계
PBKDF2는 약한 비밀번호를 강하게 만들어주지 않습니다. "123456"을 PBKDF2로 해싱해도, 공격자가 "123456"을 먼저 시도하면 뚫립니다.

**필수 비밀번호 정책**:
- 최소 8자 이상 (권장 12자)
- 대소문자, 숫자, 특수문자 조합
- 일반적인 단어 금지 (사전 공격 방지)
- 이전 비밀번호 재사용 금지
- 정기적인 변경 권장

PBKDF2는 "강한 비밀번호를 더 안전하게 저장"하는 도구입니다.

#### 레이트 리미팅(Rate Limiting)
PBKDF2만으로는 부족합니다. 로그인 시도 제한도 필수입니다:

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
솔트 외에 "페퍼(Pepper)"라는 추가 보안 계층을 사용할 수 있습니다:

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

데이터베이스가 유출되어도 페퍼를 모르면 해시를 검증할 수 없습니다.

### 결론

PBKDF2는 2000년부터 사용된 검증된 비밀번호 해싱 표준입니다. 최신 알고리즘(Argon2, scrypt)보다는 보안성이 낮을 수 있지만, 충분한 반복 횟수를 사용하면 여전히 안전합니다.

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

PBKDF2는 단독으로 완벽한 보안을 제공하지 않습니다. 다층 방어(Defense in Depth) 전략의 한 부분으로, 다른 보안 수단들과 함께 사용해야 합니다.
