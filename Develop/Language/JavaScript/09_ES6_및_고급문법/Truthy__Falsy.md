# JavaScript Truthy와 Falsy

JavaScript를 처음 배우는 사람들이 가장 헷갈려하는 개념 중 하나가 바로 **Truthy**와 **Falsy**입니다. 이 개념을 제대로 이해하지 못하면 조건문에서 예상과 다른 결과가 나올 수 있어요.

## 📖 기본 개념 이해하기

### Truthy와 Falsy란?

JavaScript에서는 모든 값이 조건문에서 **참(true)** 또는 **거짓(false)**으로 평가됩니다.

- **Truthy**: 조건문에서 `true`로 평가되는 값
- **Falsy**: 조건문에서 `false`로 평가되는 값

이것을 이해하기 전에 먼저 알아야 할 용어들:

**조건문**: `if`, `while`, `for` 등에서 조건을 확인하는 부분
**평가**: 값을 검사해서 참인지 거짓인지 판단하는 과정
**암시적 변환**: JavaScript가 자동으로 타입을 변환하는 것

---

## ❌ Falsy 값들 (조건문에서 false로 평가)

JavaScript에서 다음 8가지 값들은 모두 falsy입니다:

### 1. `false`
가장 직관적인 falsy 값입니다.
```javascript
let isLoggedIn = false;
if (isLoggedIn) {
    console.log("로그인됨"); // 실행되지 않음
} else {
    console.log("로그인 안됨"); // 실행됨
}
```

### 2. `0` (숫자 0)
숫자 0은 falsy입니다. 하지만 문자열 `"0"`은 truthy입니다!
```javascript
let count = 0;
if (count) {
    console.log("카운트가 있음"); // 실행되지 않음
}

let stringZero = "0";
if (stringZero) {
    console.log("문자열 0은 truthy!"); // 실행됨
}
```

### 3. `-0` (음수 0)
JavaScript에서 `0`과 `-0`은 보통 같다고 취급하지만, falsy라는 점은 동일합니다.
```javascript
let negativeZero = -0;
if (negativeZero) {
    console.log("이것도 실행되지 않음"); // 실행되지 않음
}
```

### 4. `0n` (BigInt 0)
BigInt는 큰 정수를 다루는 타입입니다. BigInt의 0도 falsy입니다.
```javascript
let bigIntZero = 0n;
if (bigIntZero) {
    console.log("BigInt 0도 falsy"); // 실행되지 않음
}
```

### 5. 빈 문자열 `""`, `''`, ``
길이가 0인 문자열은 falsy입니다.
```javascript
let emptyString = "";
if (emptyString) {
    console.log("빈 문자열은 falsy"); // 실행되지 않음
}

// 주의: 공백이 있는 문자열은 truthy입니다!
let spaceString = "   ";
if (spaceString) {
    console.log("공백 문자열은 truthy!"); // 실행됨
}
```

### 6. `null`
의도적으로 "값이 없음"을 나타낼 때 사용합니다.
```javascript
let user = null;
if (user) {
    console.log("사용자가 있음"); // 실행되지 않음
}
```

### 7. `undefined`
변수가 선언되었지만 값이 할당되지 않았을 때의 상태입니다.
```javascript
let name;
if (name) {
    console.log("이름이 있음"); // 실행되지 않음
}

// 객체의 존재하지 않는 속성에 접근할 때도 undefined
let person = {};
if (person.age) {
    console.log("나이가 있음"); // 실행되지 않음
}
```

### 8. `NaN` (Not a Number)
유효하지 않은 숫자 연산의 결과입니다.
```javascript
let invalidNumber = 0 / 0; // NaN
if (invalidNumber) {
    console.log("유효한 숫자"); // 실행되지 않음
}

// NaN은 자기 자신과도 같지 않습니다
console.log(NaN === NaN); // false
console.log(isNaN(NaN)); // true (NaN 확인하는 올바른 방법)
```

---

## ✅ Truthy 값들 (조건문에서 true로 평가)

Falsy가 아닌 모든 값은 truthy입니다. 주요 truthy 값들을 살펴보겠습니다.

### 1. `true`
가장 직관적인 truthy 값입니다.
```javascript
let isActive = true;
if (isActive) {
    console.log("활성화됨"); // 실행됨
}
```

### 2. 0이 아닌 모든 숫자
양수, 음수, 소수점 모두 truthy입니다.
```javascript
if (42) console.log("양수는 truthy"); // 실행됨
if (-1) console.log("음수도 truthy"); // 실행됨
if (3.14) console.log("소수점도 truthy"); // 실행됨
```

### 3. 빈 문자열이 아닌 모든 문자열
```javascript
if ("hello") console.log("문자열은 truthy"); // 실행됨
if ("0") console.log("문자열 '0'도 truthy"); // 실행됨
if (" ") console.log("공백 문자열도 truthy"); // 실행됨
```

### 4. 모든 배열 (빈 배열 포함)
```javascript
if ([]) console.log("빈 배열은 truthy"); // 실행됨
if ([1, 2, 3]) console.log("요소가 있는 배열도 truthy"); // 실행됨
```

### 5. 모든 객체 (빈 객체 포함)
```javascript
if ({}) console.log("빈 객체는 truthy"); // 실행됨
if ({ name: "John" }) console.log("속성이 있는 객체도 truthy"); // 실행됨
```

### 6. 모든 함수
```javascript
if (function() {}) console.log("함수는 truthy"); // 실행됨
if (() => {}) console.log("화살표 함수도 truthy"); // 실행됨
```

---

## 🔄 타입 변환 이해하기

### 명시적 변환 vs 암시적 변환

**명시적 변환**: 개발자가 직접 타입을 변환하는 것
**암시적 변환**: JavaScript가 자동으로 타입을 변환하는 것

### 명시적 변환 방법들

#### 1. `Boolean()` 함수 사용
```javascript
console.log(Boolean(0)); // false
console.log(Boolean("")); // false
console.log(Boolean(null)); // false
console.log(Boolean(undefined)); // false

console.log(Boolean(42)); // true
console.log(Boolean("hello")); // true
console.log(Boolean([])); // true
console.log(Boolean({})); // true
```

#### 2. 이중 부정 연산자 `!!` 사용
```javascript
console.log(!!0); // false
console.log(!!""); // false
console.log(!!null); // false

console.log(!!42); // true
console.log(!!"hello"); // true
console.log(!![]); // true
```

### 암시적 변환 예시

#### 조건문에서의 암시적 변환
```javascript
let value = 0;
if (value) {
    // value가 자동으로 false로 평가됨
    console.log("이 코드는 실행되지 않음");
}

let name = "John";
if (name) {
    // name이 자동으로 true로 평가됨
    console.log("이름이 있음"); // 실행됨
}
```

#### 논리 연산자에서의 암시적 변환
```javascript
// OR 연산자 (||) - 첫 번째 truthy 값을 반환
console.log(0 || "기본값"); // "기본값"
console.log("" || "기본값"); // "기본값"
console.log("실제값" || "기본값"); // "실제값"

// AND 연산자 (&&) - 첫 번째 falsy 값을 반환하거나 마지막 truthy 값
console.log(0 && "실행되지 않음"); // 0
console.log("실행됨" && "마지막값"); // "마지막값"
```

---

## ⚠️ 주의해야 할 함정들

### 1. 배열과 객체의 빈 값 체크
```javascript
// ❌ 잘못된 방법
let array = [];
if (array) {
    console.log("배열이 있음"); // 실행됨 (빈 배열도 truthy!)
}

// ✅ 올바른 방법
if (array.length > 0) {
    console.log("배열에 요소가 있음");
}

// 객체의 경우
let obj = {};
if (Object.keys(obj).length > 0) {
    console.log("객체에 속성이 있음");
}
```

### 2. 0과 문자열 "0"의 차이
```javascript
let numberZero = 0;
let stringZero = "0";

console.log(Boolean(numberZero)); // false
console.log(Boolean(stringZero)); // true

// 조건문에서
if (numberZero) {
    console.log("숫자 0은 falsy"); // 실행되지 않음
}

if (stringZero) {
    console.log("문자열 '0'은 truthy"); // 실행됨
}
```

### 3. null vs undefined vs 0
```javascript
let nullValue = null;
let undefinedValue = undefined;
let zeroValue = 0;

console.log(nullValue == undefinedValue); // true (느슨한 비교)
console.log(nullValue === undefinedValue); // false (엄격한 비교)
console.log(nullValue == zeroValue); // false
console.log(undefinedValue == zeroValue); // false
```

---

## 💡 실무에서 자주 사용하는 패턴들

### 1. 기본값 설정
```javascript
// 사용자 이름이 없으면 "게스트"로 설정
function greetUser(username) {
    username = username || "게스트";
    return `안녕하세요, ${username}님!`;
}

console.log(greetUser("김철수")); // "안녕하세요, 김철수님!"
console.log(greetUser("")); // "안녕하세요, 게스트님!"
console.log(greetUser(null)); // "안녕하세요, 게스트님!"
```

### 2. 조건부 실행
```javascript
// 사용자가 로그인되어 있을 때만 환영 메시지 표시
let user = {
    name: "김철수",
    isLoggedIn: true
};

user.isLoggedIn && console.log(`환영합니다, ${user.name}님!`);

// 사용자가 없으면 로그인 페이지로 이동
let currentUser = null;
currentUser || console.log("로그인이 필요합니다");
```

### 3. 폼 유효성 검사
```javascript
function validateForm(data) {
    let errors = [];
    
    // 사용자 이름 검사
    if (!data.username || data.username.trim() === "") {
        errors.push("사용자 이름을 입력해주세요");
    }
    
    // 이메일 검사
    if (!data.email || !data.email.includes("@")) {
        errors.push("유효한 이메일을 입력해주세요");
    }
    
    // 비밀번호 길이 검사
    if (!data.password || data.password.length < 8) {
        errors.push("비밀번호는 8자 이상이어야 합니다");
    }
    
    return errors.length === 0 ? null : errors;
}

// 사용 예시
let formData = {
    username: "",
    email: "invalid-email",
    password: "123"
};

let validationResult = validateForm(formData);
if (validationResult) {
    console.log("오류:", validationResult);
}
```

### 4. API 응답 처리
```javascript
async function getUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        
        // 데이터가 없거나 빈 객체인 경우 처리
        if (!data || Object.keys(data).length === 0) {
            throw new Error("사용자 데이터를 찾을 수 없습니다");
        }
        
        return {
            success: true,
            data: data
        };
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 5. 옵셔널 체이닝과 함께 사용
```javascript
let user = {
    profile: {
        name: "김철수",
        address: null
    }
};

// 안전한 속성 접근
let userName = user?.profile?.name || "이름 없음";
let userAddress = user?.profile?.address || "주소 없음";

console.log(userName); // "김철수"
console.log(userAddress); // "주소 없음"
```

---

## 🧪 테스트해보기

다음 코드를 실행해서 truthy/falsy를 직접 확인해보세요:

```javascript
// Falsy 값들 테스트
console.log("=== Falsy 값들 ===");
console.log(Boolean(false)); // false
console.log(Boolean(0)); // false
console.log(Boolean("")); // false
console.log(Boolean(null)); // false
console.log(Boolean(undefined)); // false
console.log(Boolean(NaN)); // false

// Truthy 값들 테스트
console.log("\n=== Truthy 값들 ===");
console.log(Boolean(true)); // true
console.log(Boolean(42)); // true
console.log(Boolean("hello")); // true
console.log(Boolean([])); // true
console.log(Boolean({})); // true
console.log(Boolean(function() {})); // true
```

---

## 📝 정리

### Falsy 값 (8개)
1. `false`
2. `0`
3. `-0`
4. `0n` (BigInt)
5. `""` (빈 문자열)
6. `null`
7. `undefined`
8. `NaN`

### Truthy 값
- Falsy가 아닌 모든 값
- 빈 배열 `[]`도 truthy
- 빈 객체 `{}`도 truthy
- 문자열 `"0"`도 truthy

### 기억할 점
- **명시적 비교**가 안전합니다: `if (value === null)`
- **타입 체크**를 함께 사용하세요: `if (typeof value === 'string')`
- **배열/객체의 빈 값**은 별도로 체크해야 합니다
- **0과 "0"**은 다릅니다!
