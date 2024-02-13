

## 암호화에 사용하는 요소들에 대해 알아보자

### Padding
- 암호화 함수에 입력되는 데이터의 크기를 일정한 블록 크기로 맞추기 위해 사용되는 방법입니다. 패딩은 데이터의 크기를 블록 크기에 맞게 조정하는 역할을 합니다. 예를 들어, 블록 크기가 64비트인 경우, 데이터의 크기가 50비트라면 14비트의 패딩이 추가되어 블록 크기에 맞게 조정됩니다.

- 가장 일반적인 패딩 방식 중 하나는 PKCS#7입니다. 
- 예를 들어, 블록 크기가 8바이트(64비트)인 경우, 데이터의 크기가 10바이트라면 6바이트의 패딩이 추가되어야 합니다. 
- 이를 PKCS#7 방식으로 패딩하면 다음과 같습니다:

    - 원래 데이터: 10 20 30 40 50 60 70 80 90 A0
    - 패딩 데이터: 10 20 30 40 50 60 70 80 90 A0 06 06 06 06 06 06

### Code Example
```typescript
    const crypto = require('crypto');
    
    // PKCS#7 패딩을 적용하는 함수
    function applyPKCS7Padding(data, blockSize) {
    // 패딩 길이 계산
    const paddingLength = blockSize - (data.length % blockSize);
    
    // 패딩 값 생성
    const paddingValue = Buffer.from([paddingLength]);
    
    // 패딩된 데이터를 저장할 버퍼 생성
    const paddedData = Buffer.alloc(data.length + paddingLength);
    
    // 기존 데이터를 패딩된 데이터로 복사
    data.copy(paddedData);
    
    // 패딩 값을 추가하여 패딩 적용
    paddingValue.fill(paddingLength, data.length);
    
    // 패딩된 데이터 반환
    return paddedData;
    }
    
    // 예시 데이터와 블록 크기
    const data = Buffer.from('Hello, world!', 'utf8');
    const blockSize = 16; // AES의 블록 크기는 16바이트입니다.
    
    // PKCS#7 패딩 적용
    const paddedData = applyPKCS7Padding(data, blockSize);
    console.log(paddedData);
```

---

# Salt
- Salt는 암호화 과정에서 추가되는 임의의 데이터입니다. Salt를 사용하면 동일한 비밀번호에 대해 항상 동일한 암호화 결과가 나오지 않기 때문에 레인보우 테이블 등의 공격을 방지할 수 있습니다. Salt는 보안성을 높이기 위해 사용자마다 다른 값을 가지며, 일반적으로 무작위로 생성됩니다.

## Salt를 적용한 비밀번호 저장 과정
- 사용자가 비밀번호를 생성 또는 변경할 때, 무작위로 Salt 값을 생성합니다. 이 Salt 값은 각 사용자마다 다르게 생성됩니다.
- Salt 값과 사용자의 비밀번호를 결합하여 하나의 문자열로 만듭니다.
- 결합된 문자열을 해시 함수에 입력으로 제공하여 해시 값을 생성합니다.
- Salt 값과 생성된 해시 값을 함께 저장합니다.

```typescript
const crypto = require('crypto');

// 사용자 정보를 저장할 객체
const users = {};

// 비밀번호 설정 함수
function setPassword(username, password) {
  // Salt 생성
  const salt = crypto.randomBytes(16).toString('hex');
  
  // Salt와 비밀번호를 결합하여 해시 값 생성
  const hash = crypto.pbkdf2Sync(password, salt, 1000, 64, 'sha512').toString('hex');
  
  // 사용자 정보에 Salt와 해시 값을 저장
  users[username] = {
    salt,
    hash
  };
}

// 로그인 함수
function login(username, password) {
  const user = users[username];
  
  if (user) {
    // 입력된 비밀번호와 저장된 Salt를 사용하여 해시 값 생성
    const hash = crypto.pbkdf2Sync(password, user.salt, 1000, 64, 'sha512').toString('hex');
    
    // 저장된 해시 값과 비교
    if (hash === user.hash) {
      console.log('로그인 성공!');
    } else {
      console.log('잘못된 비밀번호입니다.');
    }
  } else {
    console.log('사용자를 찾을 수 없습니다.');
  }
}

// 사용자 비밀번호 설정 예시
setPassword('alice', 'p@ssw0rd');
setPassword('bob', '123456');

// 사용자 로그인 예시
login('alice', 'p@ssw0rd');
login('bob', 'password');

```

# Iteration
- Iteration은 암호화 함수를 몇 번 반복할지를 결정하는 값입니다. 높은 iteration 값을 사용할수록 암호화에 소요되는 시간이 증가하므로, 암호를 해독하려는 공격자에게 시간적인 부담을 주는 역할을 합니다. 즉, iteration 값이 높을수록 보안성이 향상됩니다.


# Digest
- Digest는 암호화 결과로 출력되는 해시 함수의 크기를 말합니다. 
- 더 긴 digest 값은 더 많은 비트를 가지므로 해독하기 어렵습니다. 일반적으로 안전한 해시 함수인 SHA-256 등이 사용됩니다.


## Digest를 왜 해야될까?
### 가독성
- 16진수는 0부터 9까지의 숫자와 A부터 F까지의 문자로 표현되기 때문에 사람이 읽기 쉬운 형태입니다. 
- 이진 데이터는 일반적으로 표현이 어렵고 복잡하므로, 16진수로 변환하면 가독성이 향상됩니다. 
- 이를 통해 해시값을 쉽게 확인하고 비교할 수 있습니다.
### 일관성
- 해시 함수의 출력은 고정된 길이를 가지는 이진 데이터입니다.
- 이진 데이터를 그대로 사용하면 길이가 길고 복잡한 문자열이 될 수 있으며, 서로 다른 플랫폼이나 시스템에서 이진 데이터를 처리하는 방식이 다를 수 있습니다. 
- 그러나 16진수로 변환하면 일관된 길이와 형식을 가지기 때문에 데이터의 호환성과 일관성을 보장할 수 있습니다.
### 편의성
- 16진수는 많은 프로그래밍 언어에서 내장된 기능을 통해 쉽게 처리할 수 있습니다. 
- 예를 들어, 문자열 비교, 검색, 저장 등의 작업을 수행할 때 16진수 형식을 사용하면 간단하게 구현할 수 있습니다. 
- 또한, 다이제스트를 파일 이름이나 URL 파라미터 등으로 사용할 때도 편리합니다.

```typescript
    const crypto = require('crypto');
    
    function generateDigest(data) {
      const algorithm = 'sha256';
      
      // 지정된 알고리즘으로 해시 객체를 생성합니다.
      // sha256 알고리즘으로 해시 객체를 생성하면 생성되는 해시 객체는 256비트(32바이트) 길이의 이진 데이터입니다.
      const hash = crypto.createHash(algorithm);
      
      // 데이터로 해시 객체를 업데이트합니다.
      hash.update(data);
  
      // hash.digest('hex') 메서드를 사용하여 해시 객체의 다이제스트를 16진수 형식으로 생성합니다.
      const digest = hash.digest('hex');
      
      return digest;
    }
    
    // 예시 사용법
    const data = '안녕하세요, 세계!';
    
    // 데이터의 다이제스트를 생성합니다.
    const digest = generateDigest(data);
    
    // 다이제스트를 출력합니다.
    console.log('다이제스트:', digest);
```


