# PBKDF2 (Password-Based Key Derivation Function 2)

## 개요
PBKDF2는 비밀번호 기반 키 유도 함수로, 비밀번호를 안전하게 저장하고 관리하기 위한 암호화 표준입니다. 이 알고리즘은 비밀번호를 단순히 해시하는 것보다 더 강력한 보안을 제공합니다.

## 작동 원리
1. **비밀번호와 솔트(Salt) 결합**
   - 비밀번호와 무작위로 생성된 솔트를 결합
   - 솔트는 각 사용자마다 고유한 값을 가짐

2. **반복적 해싱**
   - 설정된 반복 횟수만큼 해시 함수를 반복 적용
   - 이 과정을 통해 무차별 대입 공격에 대한 저항성 강화

## JavaScript 구현

```javascript
const crypto = require('crypto');

// 비밀번호 해싱 함수
async function hashPassword(password) {
    // 솔트 생성 (16바이트)
    const salt = crypto.randomBytes(16);
    
    // PBKDF2를 사용한 키 생성
    const key = await new Promise((resolve, reject) => {
        crypto.pbkdf2(
            password,           // 비밀번호
            salt,              // 솔트
            100000,           // 반복 횟수 (권장: 100,000 이상)
            64,               // 키 길이 (바이트)
            'sha512',         // 해시 알고리즘
            (err, derivedKey) => {
                if (err) reject(err);
                resolve(derivedKey);
            }
        );
    });

    // 결과를 Base64로 인코딩하여 저장
    return {
        salt: salt.toString('base64'),
        hash: key.toString('base64')
    };
}

// 비밀번호 검증 함수
async function verifyPassword(password, storedHash, storedSalt) {
    const salt = Buffer.from(storedSalt, 'base64');
    
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

    return key.toString('base64') === storedHash;
}
```

## 보안 고려사항

### 1. 솔트(Salt)
- 각 사용자마다 고유한 솔트 사용
- 최소 16바이트 이상의 길이 권장
- 암호학적으로 안전한 난수 생성기 사용

### 2. 반복 횟수
- 최소 100,000회 이상 권장
- 시스템 성능을 고려하여 조정 가능
- 시간이 지날수록 증가시키는 것이 좋음

### 3. 해시 알고리즘
- SHA-256, SHA-512 등 강력한 알고리즘 사용
- 시스템 요구사항에 따라 선택

## 장점
- 무차별 대입 공격에 대한 강력한 저항성
- 레인보우 테이블 공격 방지
- 구현이 비교적 간단
- 널리 사용되는 표준 알고리즘

## 단점
- GPU 기반 공격에 취약할 수 있음
- 계산 비용이 높음
- 메모리 사용량이 많을 수 있음

## 대안
- Argon2: 메모리 하드 알고리즘으로, GPU 공격에 더 강력
- bcrypt: 계산 비용이 높아 무차별 대입 공격에 강함
- scrypt: 메모리 하드 알고리즘으로, GPU/ASIC 공격에 강함

## 결론
PBKDF2는 여전히 안전한 비밀번호 해싱 방법이지만, 가능한 경우 Argon2나 scrypt와 같은 더 현대적인 알고리즘을 사용하는 것이 권장됩니다. 시스템의 보안 요구사항과 성능 제약을 고려하여 적절한 알고리즘을 선택해야 합니다.

