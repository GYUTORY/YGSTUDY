
- 문득, 서버개발자라면 암호화에 대해서 더 자세히 알아야 될 필요가 있다고 생각이 든다.
- 보통 외부회사와 연동을 하거나, 암호화된 데이터를 주고받을 때, 해당 pbkdf2 함수를 많이 사용하는 것 같다.
- 따라서, pbkdf2에 대해 자세히 알아보고자 한다.


--- 
## 사전 지식 
### 솔트 (Salt)
- 해시 함수를 사용하여 단방향 암호화를 했을때, 언제나 같은 값을 같게 된다. 해커는 잘 알려진 해시값의 원문을 저장해두고 쉽게 원문을 유추할 수 있다
- 솔트는 이러한 꼼수를 피하기 위해 해시된 값에 추가적으로 들어가는 랜덤 데이터

1. 솔트전 : qwerty1234 > SHA256
> 17F80754644D33AC685B0842A402229ADBB43FC9312F7BDF36BA24237A1F1FFB

2. 임의의 랜덤 데이터 : "LOU"를 통한 salting(qwerty1234LOU) 
> C556DC7BF3122C4AB228892A4DE67A1896F1CB0B32A1CEB667513F057ED6AA14

---
# pbkdf2
- 암호화와 관련된 함수 중 하나로, "Password-Based Key Derivation Function 2"를 의미합니다.
- 이 함수는 주어진 비밀번호를 기반으로 키를 생성하기 위해 사용됩니다.
- 해당 "pbkdf2" 함수는 안전한 비밀번호 저장 및 인증에 사용되며, 일반적으로 사용자의 비밀번호를 해시화하여 저장하고, 인증 시에 비밀번호를
검증하는 용도로 활용됩니다.

--- 

### pbkdf2 함수는 다음과 같은 요소를 필요로 합니다:
- 비밀번호 (또는 평문)
- 솔트 (salt): 무작위로 생성된 값을 의미하며, 같은 비밀번호에 대해 다른 솔트 값을 사용함으로써 보안을 강화합니다.
- 반복 횟수 (iteration count): 알고리즘을 실행하는 반복 횟수로, 값이 클수록 보안이 강화되지만 처리 시간이 더 소요됩니다.
- 출력 길이 (output length): 생성되는 키의 길이를 지정합니다.

---

# pbkdf2 함수
- 주어진 비밀번호와 솔트를 사용하여 지정된 반복 횟수만큼 알고리즘을 반복 실행하고, 최종적으로 출력 길이만큼의 키를 생성합니다.
- 이렇게 생성된 키는 일방향 해시 함수를 통해 저장된 비밀번호와 비교하여 인증을 수행하거나, 다른 암호화 작업에 사용될 수 있습니다.
---

Node.js에서 pbkdf2 함수를 사용하기 위해 "crypto" 모듈을 사용해야 합니다. 

## 다음은 pbkdf2 함수의 기본적인 사용 방법

```javascript
    const crypto = require('crypto');
    
    const password = 'myPassword';
    const salt = crypto.randomBytes(16).toString('hex'); // 무작위로 생성된 솔트 값
    const iterations = 100000; // 반복 횟수
    const keyLength = 64; // 출력 길이
    
    crypto.pbkdf2(password, salt, iterations, keyLength, 'sha512', (err, derivedKey) => {
    if (err) throw err;
    const hashedPassword = derivedKey.toString('hex');
    console.log('Hashed Password:', hashedPassword);
    });
```


의 코드에서 crypto.pbkdf2 함수는 다음과 같은 인자를 받습니다.

- password: 해시화할 비밀번호입니다.
- digest: 해시 알고리즘으로, 일반적으로 'sha1', 'sha256', 'sha512' 등을 사용합니다.
- callback: 비동기 콜백 함수로, 해시화된 키가 생성되면 호출됩니다.

---

## 비밀번호를 검증하는 방법
```javascript
    const storedHashedPassword = '...'; // 저장된 해시화된 비밀번호
    const userEnteredPassword = '...'; // 사용자가 입력한 비밀번호
    
    crypto.pbkdf2(userEnteredPassword, salt, iterations, keyLength, 'sha512', (err, derivedKey) => {
        if (err) throw err;
        const hashedPasswordToCompare = derivedKey.toString('hex');
    
        if (storedHashedPassword === hashedPasswordToCompare) {
            console.log('Passwords match!');
        } else {
        console.log('Passwords do not match!');
        }
    });
```


