---
title: AES Advanced Encryption Standard
tags: [security, aes]
updated: 2025-08-10
---
## AES의 주요 특징
1. 키 길이의 유연성
   - 128비트, 192비트, 256비트 키 길이 지원
   - 키 길이에 따라 라운드 수가 다름 (128비트: 10라운드, 192비트: 12라운드, 256비트: 14라운드)

2. 블록 크기
   - 고정된 128비트(16바이트) 블록 크기 사용
   - 각 블록은 4x4 바이트의 상태 행렬로 표현

3. 암호화 구조
   - SPN(Substitution-Permutation Network) 구조 사용
   - 각 라운드에서 4가지 주요 연산 수행:
     - SubBytes: 바이트 단위 치환
     - ShiftRows: 행 단위 순환 이동
     - MixColumns: 열 단위 혼합
     - AddRoundKey: 라운드 키와 XOR 연산

## IV (Initialization Vector) 상세 설명
- 초기화 벡터는 암호화 과정에서 사용되는 추가적인 입력값으로, 같은 키로 여러 메시지를 암호화할 때 보안성을 높이기 위해 사용됩니다.

### IV의 주요 특징
1. 크기와 형식
   - AES에서는 일반적으로 16바이트(128비트) 크기 사용
   - 블록 암호의 블록 크기와 동일한 크기를 가짐
   - 바이트 배열 형태로 저장 및 전송

2. 생성 방법
   - 암호학적으로 안전한 난수 생성기 사용 (예: crypto.getRandomValues)
   - 예측 불가능한 값이어야 함
   - 매 암호화마다 새로운 IV 생성 필요

3. 보안적 중요성
   - IV 재사용 시 심각한 보안 취약점 발생
   - 같은 키와 IV로 암호화된 메시지는 패턴 분석에 취약
   - 특히 CBC 모드에서 IV 재사용은 첫 번째 블록의 보안을 완전히 무력화

4. 저장 및 전송
   - 암호화된 데이터와 함께 저장/전송 필요
   - 일반적으로 암호문 앞에 붙여서 전송
   - Base64나 Hex로 인코딩하여 전송 가능

5. 사용 예시
```javascript
// IV 생성 예시
const iv = crypto.getRandomValues(new Uint8Array(16));

// IV를 Base64로 인코딩
const ivBase64 = btoa(String.fromCharCode(...iv));

// IV를 Hex로 인코딩
const ivHex = Array.from(iv)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
```

## Salt 상세 설명
- Salt는 암호화나 해싱 과정에 추가되는 랜덤 데이터로, 특히 비밀번호 저장에 사용됩니다.

### Salt의 주요 특징
1. 목적과 필요성
   - 레인보우 테이블 공격 방지
   - 같은 비밀번호라도 다른 해시값 생성
   - 사용자별 고유한 해시값 보장

2. 크기와 형식
   - 일반적으로 16바이트 이상 권장
   - 바이트 배열 형태로 저장
   - 충분한 엔트로피를 가져야 함

3. 생성 방법
   - 암호학적으로 안전한 난수 생성기 사용
   - 사용자마다 고유한 Salt 생성
   - 예측 불가능한 값이어야 함

4. 저장 및 관리
   - 해시된 비밀번호와 함께 저장
   - 일반적으로 사용자 데이터베이스에 저장
   - 암호화된 데이터와 함께 전송 가능

5. PBKDF2에서의 Salt 사용
   - 키 파생 함수에서 추가적인 보안 계층 제공
   - 반복 횟수와 함께 보안 강도 결정
   - 메모리 해시 함수(예: Argon2)와 함께 사용 가능

6. 사용 예시
```javascript
// Salt 생성 예시
const salt = crypto.getRandomValues(new Uint8Array(16));

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
            iterations: 100000,
            hash: 'SHA-256'
        },
        keyMaterial,
        { name: 'AES-CBC', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );
}
```

### IV와 Salt의 차이점
1. 목적
   - IV: 같은 키로 여러 메시지를 암호화할 때 패턴 분석 방지
   - Salt: 같은 비밀번호에 대해 다른 해시값 생성

2. 사용 시점
   - IV: 매 암호화마다 새로 생성
   - Salt: 사용자 계정 생성 시 한 번 생성하여 저장

3. 재사용
   - IV: 절대 재사용하면 안 됨
   - Salt: 사용자 계정에 대해 일관되게 유지

4. 저장 위치
   - IV: 암호문과 함께 저장
   - Salt: 사용자 데이터베이스에 저장

5. 크기
   - IV: 블록 크기와 동일 (AES: 16바이트)
   - Salt: 더 큰 크기 사용 가능 (일반적으로 16바이트 이상)

## 배경
1. IV 관련
   - 매 암호화마다 새로운 IV 생성
   - 암호학적으로 안전한 난수 생성기 사용
   - IV를 암호문과 함께 안전하게 전송
   - IV 재사용 절대 금지

2. Salt 관련
   - 충분한 길이의 Salt 사용 (16바이트 이상)
   - 사용자마다 고유한 Salt 생성
   - 암호학적으로 안전한 난수 생성기 사용
   - Salt를 안전하게 저장 및 관리

3. 일반적인 보안 원칙
   - 키, IV, Salt 모두 예측 불가능해야 함
   - 적절한 키 파생 함수 사용 (PBKDF2, Argon2 등)
   - 충분한 반복 횟수 사용
   - 모든 보안 관련 데이터의 무결성 보장

1. 키 관리
   - 안전한 키 생성 및 저장
   - 정기적인 키 교체
   - 키 백업 및 복구 절차

2. IV 관리
   - 예측 불가능한 IV 사용
   - IV 재사용 금지
   - 충분한 길이의 IV 사용

3. Salt 관리
   - 충분한 길이의 Salt 사용
   - 각 사용자마다 고유한 Salt 사용
   - 암호학적으로 안전한 난수 생성기 사용

```javascript
// AES 암호화 예시 (JavaScript - Web Crypto API)
async function encryptAES(text, key) {
    // 키 생성 (32바이트 = 256비트)
    const keyBuffer = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(key),
        { name: 'AES-CBC', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );

    // IV 생성 (16바이트)
    const iv = crypto.getRandomValues(new Uint8Array(16));

    // 데이터 암호화
    const encryptedBuffer = await crypto.subtle.encrypt(
        {
            name: 'AES-CBC',
            iv: iv
        },
        keyBuffer,
        new TextEncoder().encode(text)
    );

    // 암호화된 데이터와 IV를 Base64로 인코딩
    const encryptedArray = new Uint8Array(encryptedBuffer);
    const encryptedBase64 = btoa(String.fromCharCode(...encryptedArray));
    const ivBase64 = btoa(String.fromCharCode(...iv));

    return {
        encrypted: encryptedBase64,
        iv: ivBase64
    };
}

async function decryptAES(encryptedData, key, iv) {
    // 키 생성
    const keyBuffer = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(key),
        { name: 'AES-CBC', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );

    // Base64 디코딩
    const encryptedArray = new Uint8Array(
        atob(encryptedData)
            .split('')
            .map(char => char.charCodeAt(0))
    );
    const ivArray = new Uint8Array(
        atob(iv)
            .split('')
            .map(char => char.charCodeAt(0))
    );

    // 데이터 복호화
    const decryptedBuffer = await crypto.subtle.decrypt(
        {
            name: 'AES-CBC',
            iv: ivArray
        },
        keyBuffer,
        encryptedArray
    );

    // 복호화된 데이터를 문자열로 변환
    return new TextDecoder().decode(decryptedBuffer);
}

// 사용 예시
async function example() {
    const text = '암호화할 텍스트';
    const key = '32바이트키를여기에입력하세요'; // 32바이트 이상이어야 함

    try {
        // 암호화
        const encrypted = await encryptAES(text, key);
        console.log('암호화된 데이터:', encrypted.encrypted);
        console.log('IV:', encrypted.iv);

        // 복호화
        const decrypted = await decryptAES(encrypted.encrypted, key, encrypted.iv);
        console.log('복호화된 데이터:', decrypted);
    } catch (error) {
        console.error('암호화/복호화 중 오류 발생:', error);
    }
}

// PBKDF2를 사용한 키 파생 예시 (Salt 사용)
async function deriveKey(password, salt) {
    const iterations = 100000;
    const keyLength = 32; // 256비트

    // Salt 생성 (16바이트)
    const saltBuffer = salt || crypto.getRandomValues(new Uint8Array(16));

    // 키 파생
    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(password),
        { name: 'PBKDF2' },
        false,
        ['deriveBits', 'deriveKey']
    );

    const key = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: saltBuffer,
            iterations: iterations,
            hash: 'SHA-256'
        },
        keyMaterial,
        { name: 'AES-CBC', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );

    return {
        key,
        salt: saltBuffer
    };
}

// PBKDF2를 사용한 암호화 예시
async function encryptWithPBKDF2(text, password) {
    // 키 파생
    const { key, salt } = await deriveKey(password);

    // IV 생성
    const iv = crypto.getRandomValues(new Uint8Array(16));

    // 데이터 암호화
    const encryptedBuffer = await crypto.subtle.encrypt(
        {
            name: 'AES-CBC',
            iv: iv
        },
        key,
        new TextEncoder().encode(text)
    );

    // 결과 반환
    return {
        encrypted: btoa(String.fromCharCode(...new Uint8Array(encryptedBuffer))),
        iv: btoa(String.fromCharCode(...iv)),
        salt: btoa(String.fromCharCode(...salt))
    };
}
```









 









# AES (Advanced Encryption Standard)
- 2001년 NIST(미국 국립표준기술연구소)에 의해 채택된 대칭키 암호화 알고리즘
- 이전 표준이었던 DES를 대체한 현대적인 암호화 표준
- Rijndael 알고리즘을 기반으로 하며, 2000년에 AES로 선정됨

## AES와 SHA-256의 차이점

### SHA-256
- 단방향 해시 함수
- 임의의 길이의 입력을 256비트(32바이트) 고정 길이 출력으로 변환
- 복호화 불가능
- 주로 데이터 무결성 검증에 사용
- 특징:
  - 충돌 저항성
  - 일방향성
  - 눈사태 효과

### AES
- 양방향 대칭키 암호화 알고리즘
- 암호화와 복호화가 가능
- 주로 데이터 기밀성 보호에 사용
- 특징:
  - 대칭키 사용
  - 블록 암호화
  - 다양한 운영 모드 지원 (ECB, CBC, CFB, OFB, CTR)

## AES 운영 모드
1. ECB (Electronic Codebook)
   - 가장 단순한 모드
   - 각 블록을 독립적으로 암호화
   - 보안성이 낮아 권장되지 않음

2. CBC (Cipher Block Chaining)
   - 이전 암호문 블록이 다음 평문 블록에 영향을 미침
   - IV 필요
   - 가장 널리 사용되는 모드

3. CFB (Cipher Feedback)
   - 스트림 암호화 방식
   - 작은 단위의 데이터 암호화 가능

4. OFB (Output Feedback)
   - 스트림 암호화 방식
   - 병렬 처리 가능

5. CTR (Counter)
   - 스트림 암호화 방식
   - 병렬 처리 가능
   - IV 대신 카운터 사용

