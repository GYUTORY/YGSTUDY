---
title: encodeURI - URI
tags: [language, javascript, 09es6및고급문법, encodeuri, java]
updated: 2025-08-10
---
# encodeURI() - URI 인코딩 함수

## 배경
`encodeURI()` 함수는 웹 주소(URI)에 포함된 특수 문자들을 안전하게 변환하는 JavaScript 내장 함수입니다. 

**URI(Uniform Resource Identifier)**란?
- 웹에서 리소스(웹페이지, 이미지, 파일 등)를 식별하는 문자열
- URL(Uniform Resource Locator)의 상위 개념
- 예: `https://example.com/path?name=홍길동&age=25`


웹 브라우저는 ASCII 문자만 안전하게 처리할 수 있습니다. 한글이나 특수문자가 포함된 URL을 그대로 사용하면 오류가 발생할 수 있어서, 이런 문자들을 안전한 형태로 변환해야 합니다.

```javascript
// 문제가 될 수 있는 URL
const badUrl = 'https://example.com/search?query=안녕하세요&category=음식';

// 안전하게 인코딩된 URL
const goodUrl = encodeURI(badUrl);
console.log(goodUrl);
// 출력: "https://example.com/search?query=%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94&category=%EC%9D%8C%EC%8B%9D"
```


### 기본 예제
```javascript
const uri = 'https://mozilla.org/?x=шеллы';
const encoded = encodeURI(uri);
console.log(encoded);
// 출력: "https://mozilla.org/?x=%D1%88%D0%B5%D0%BB%D0%BB%D1%8B"

// 디코딩 (원래 형태로 복원)
try {
    console.log(decodeURI(encoded));
    // 출력: "https://mozilla.org/?x=шеллы"
} catch (e) {
    console.error('잘못된 URI입니다:', e);
}
```

### 실제 활용 예제
```javascript
// 검색어가 포함된 URL 생성
const searchTerm = 'JavaScript 강의';
const baseUrl = 'https://example.com/search';

const searchUrl = `${baseUrl}?q=${encodeURI(searchTerm)}`;
console.log(searchUrl);
// 출력: "https://example.com/search?q=JavaScript%20%EA%B0%95%EC%9D%98"

// 복잡한 쿼리 파라미터
const params = {
    name: '김철수',
    city: '서울시 강남구',
    hobby: '프로그래밍'
};

const queryString = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURI(value)}`)
    .join('&');

console.log(`https://example.com/user?${queryString}`);
// 출력: "https://example.com/user?name=%EA%B9%80%EC%B2%A0%EC%88%98&city=%EC%84%9C%EC%9A%B8%EC%8B%9C%20%EA%B0%95%EB%82%A8%EA%B5%AC&hobby=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D"
```

```javascript
const uri = 'https://mozilla.org/?x=шеллы';
const encoded = encodeURI(uri);
console.log(encoded);
// 출력: "https://mozilla.org/?x=%D1%88%D0%B5%D0%BB%D0%BB%D1%8B"

// 디코딩 (원래 형태로 복원)
try {
    console.log(decodeURI(encoded));
    // 출력: "https://mozilla.org/?x=шеллы"
} catch (e) {
    console.error('잘못된 URI입니다:', e);
}
```

```javascript
// 검색어가 포함된 URL 생성
const searchTerm = 'JavaScript 강의';
const baseUrl = 'https://example.com/search';

const searchUrl = `${baseUrl}?q=${encodeURI(searchTerm)}`;
console.log(searchUrl);
// 출력: "https://example.com/search?q=JavaScript%20%EA%B0%95%EC%9D%98"

// 복잡한 쿼리 파라미터
const params = {
    name: '김철수',
    city: '서울시 강남구',
    hobby: '프로그래밍'
};

const queryString = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURI(value)}`)
    .join('&');

console.log(`https://example.com/user?${queryString}`);
// 출력: "https://example.com/user?name=%EA%B9%80%EC%B2%A0%EC%88%98&city=%EC%84%9C%EC%9A%B8%EC%8B%9C%20%EA%B0%95%EB%82%A8%EA%B5%AC&hobby=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D"
```


### 인코딩하지 않는 문자들
`encodeURI()`는 다음 문자들을 그대로 유지합니다:

**예약 문자 (URI 구조에 필요한 문자)**
- `; , / ? : @ & = + $ #`

**비예약 문자 (안전한 문자)**
- `A-Z a-z 0-9 - _ . ! ~ * ' ( )`

**공백은 `%20`으로 변환됩니다**

```javascript
const testCases = {
    reserved: ";,/?:@&=+$#",
    unreserved: "-_.!~*'()",
    alphanumeric: "ABC abc 123",
    korean: "안녕하세요",
    special: "!@#$%^&*()"
};

Object.entries(testCases).forEach(([name, value]) => {
    console.log(`${name}: "${value}" → "${encodeURI(value)}"`);
});

// 출력:
// reserved: ";,/?:@&=+$#" → ";,/?:@&=+$#"
// unreserved: "-_.!~*'()" → "-_.!~*'()"
// alphanumeric: "ABC abc 123" → "ABC%20abc%20123"
// korean: "안녕하세요" → "%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94"
// special: "!@#$%^&*()" → "!@#$%^&*()"
```

`encodeURI()`는 다음 문자들을 그대로 유지합니다:

**예약 문자 (URI 구조에 필요한 문자)**
- `; , / ? : @ & = + $ #`

**비예약 문자 (안전한 문자)**
- `A-Z a-z 0-9 - _ . ! ~ * ' ( )`

**공백은 `%20`으로 변환됩니다**

```javascript
const testCases = {
    reserved: ";,/?:@&=+$#",
    unreserved: "-_.!~*'()",
    alphanumeric: "ABC abc 123",
    korean: "안녕하세요",
    special: "!@#$%^&*()"
};

Object.entries(testCases).forEach(([name, value]) => {
    console.log(`${name}: "${value}" → "${encodeURI(value)}"`);
});

// 출력:
// reserved: ";,/?:@&=+$#" → ";,/?:@&=+$#"
// unreserved: "-_.!~*'()" → "-_.!~*'()"
// alphanumeric: "ABC abc 123" → "ABC%20abc%20123"
// korean: "안녕하세요" → "%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94"
// special: "!@#$%^&*()" → "!@#$%^&*()"
```


| 구분 | encodeURI() | encodeURIComponent() |
|------|-------------|---------------------|
| **용도** | 전체 URI 인코딩 | URI 구성요소 인코딩 |
| **예약문자 처리** | 인코딩하지 않음 | 모두 인코딩 |
| **사용 시기** | 전체 URL 생성 시 | 쿼리 파라미터 값 인코딩 시 |

```javascript
const baseUrl = 'https://example.com/api';
const query = 'name=홍길동&age=25';

// ❌ 잘못된 사용 - 예약문자가 인코딩되지 않음
const wrongUrl = `${baseUrl}?${encodeURI(query)}`;
console.log(wrongUrl);
// 출력: "https://example.com/api?name=홍길동&age=25" (문제!)

// ✅ 올바른 사용 - 쿼리 파라미터 값만 인코딩
const correctUrl = `${baseUrl}?name=${encodeURIComponent('홍길동')}&age=25`;
console.log(correctUrl);
// 출력: "https://example.com/api?name=%ED%99%8D%EA%B8%B8%EB%8F%99&age=25"

// 전체 URL 구조를 유지하면서 특정 값만 인코딩
const params = {
    search: 'JavaScript 강의',
    category: '프로그래밍',
    level: '초급'
};

const queryString = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&');

const finalUrl = `${baseUrl}?${queryString}`;
console.log(finalUrl);
// 출력: "https://example.com/api?search=JavaScript%20%EA%B0%95%EC%9D%98&category=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D&level=%EC%B4%88%EA%B8%89"
```


### 1. 잘못된 유니코드 문자 처리
```javascript
// 올바른 유니코드 쌍
console.log(encodeURIComponent("\uD800\uDFFF")); // 정상 작동

// 잘못된 유니코드 (단일 대리 문자)
try {
    console.log(encodeURIComponent("\uD800")); // URIError 발생
} catch (error) {
    console.error('유니코드 오류:', error.message);
}

try {
    console.log(encodeURIComponent("\uDFFF")); // URIError 발생
} catch (error) {
    console.error('유니코드 오류:', error.message);
}
```

### 2. HTTP 요청에서의 주의사항
```javascript
// GET 요청에서 문제가 될 수 있는 경우
const searchParams = {
    name: '김철수',
    email: 'kim@example.com',
    message: '안녕하세요! 반갑습니다.'
};

// ❌ 잘못된 방법
const badQuery = `name=${searchParams.name}&email=${searchParams.email}&message=${searchParams.message}`;
console.log('잘못된 쿼리:', badQuery);
// 출력: "name=김철수&email=kim@example.com&message=안녕하세요! 반갑습니다."

// ✅ 올바른 방법
const goodQuery = Object.entries(searchParams)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&');
console.log('올바른 쿼리:', goodQuery);
// 출력: "name=%EA%B9%80%EC%B2%A0%EC%88%98&email=kim%40example.com&message=%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94!%20%EB%B0%98%EA%B0%91%EC%8A%B5%EB%8B%88%EB%8B%A4."
```


### decodeURI()
인코딩된 URI를 원래 형태로 복원합니다.

```javascript
const original = 'https://example.com/한글페이지';
const encoded = encodeURI(original);
const decoded = decodeURI(encoded);

console.log('원본:', original);
console.log('인코딩:', encoded);
console.log('디코딩:', decoded);
console.log('일치 여부:', original === decoded); // true
```

### encodeURIComponent() / decodeURIComponent()
URI 구성요소를 인코딩/디코딩합니다.

```javascript
const component = 'user@example.com';
const encoded = encodeURIComponent(component);
const decoded = decodeURIComponent(encoded);

console.log('원본:', component);
console.log('인코딩:', encoded); // user%40example.com
console.log('디코딩:', decoded);
```


### 1. URL 파라미터 안전하게 처리하기
```javascript
function createSafeUrl(baseUrl, params) {
    const queryString = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null)
        .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
        .join('&');
    
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
}

// 사용 예제
const apiUrl = createSafeUrl('https://api.example.com/users', {
    name: '김철수',
    age: 25,
    city: '서울시 강남구',
    hobby: '프로그래밍, 독서'
});

console.log(apiUrl);
// 출력: "https://api.example.com/users?name=%EA%B9%80%EC%B2%A0%EC%88%98&age=25&city=%EC%84%9C%EC%9A%B8%EC%8B%9C%20%EA%B0%95%EB%82%A8%EA%B5%AC&hobby=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D%2C%20%EB%8F%85%EC%84%9C"
```

### 2. 폼 데이터 처리
```javascript
function serializeForm(formData) {
    const params = {};
    
    for (let [key, value] of formData.entries()) {
        if (params[key]) {
            // 같은 키가 여러 개 있는 경우 배열로 처리
            if (Array.isArray(params[key])) {
                params[key].push(value);
            } else {
                params[key] = [params[key], value];
            }
        } else {
            params[key] = value;
        }
    }
    
    return Object.entries(params)
        .map(([key, value]) => {
            if (Array.isArray(value)) {
                return value.map(v => `${key}=${encodeURIComponent(v)}`).join('&');
            }
            return `${key}=${encodeURIComponent(value)}`;
        })
        .join('&');
}

// 사용 예제
const formData = new FormData();
formData.append('name', '홍길동');
formData.append('interests', '프로그래밍');
formData.append('interests', '독서');

const queryString = serializeForm(formData);
console.log(queryString);
// 출력: "name=%ED%99%8D%EA%B8%B8%EB%8F%99&interests=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D&interests=%EB%8F%85%EC%84%9C"
```






```javascript
const uri = 'https://mozilla.org/?x=шеллы';
const encoded = encodeURI(uri);
console.log(encoded);
// 출력: "https://mozilla.org/?x=%D1%88%D0%B5%D0%BB%D0%BB%D1%8B"

// 디코딩 (원래 형태로 복원)
try {
    console.log(decodeURI(encoded));
    // 출력: "https://mozilla.org/?x=шеллы"
} catch (e) {
    console.error('잘못된 URI입니다:', e);
}
```

```javascript
// 검색어가 포함된 URL 생성
const searchTerm = 'JavaScript 강의';
const baseUrl = 'https://example.com/search';

const searchUrl = `${baseUrl}?q=${encodeURI(searchTerm)}`;
console.log(searchUrl);
// 출력: "https://example.com/search?q=JavaScript%20%EA%B0%95%EC%9D%98"

// 복잡한 쿼리 파라미터
const params = {
    name: '김철수',
    city: '서울시 강남구',
    hobby: '프로그래밍'
};

const queryString = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURI(value)}`)
    .join('&');

console.log(`https://example.com/user?${queryString}`);
// 출력: "https://example.com/user?name=%EA%B9%80%EC%B2%A0%EC%88%98&city=%EC%84%9C%EC%9A%B8%EC%8B%9C%20%EA%B0%95%EB%82%A8%EA%B5%AC&hobby=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D"
```

```javascript
const uri = 'https://mozilla.org/?x=шеллы';
const encoded = encodeURI(uri);
console.log(encoded);
// 출력: "https://mozilla.org/?x=%D1%88%D0%B5%D0%BB%D0%BB%D1%8B"

// 디코딩 (원래 형태로 복원)
try {
    console.log(decodeURI(encoded));
    // 출력: "https://mozilla.org/?x=шеллы"
} catch (e) {
    console.error('잘못된 URI입니다:', e);
}
```

```javascript
// 검색어가 포함된 URL 생성
const searchTerm = 'JavaScript 강의';
const baseUrl = 'https://example.com/search';

const searchUrl = `${baseUrl}?q=${encodeURI(searchTerm)}`;
console.log(searchUrl);
// 출력: "https://example.com/search?q=JavaScript%20%EA%B0%95%EC%9D%98"

// 복잡한 쿼리 파라미터
const params = {
    name: '김철수',
    city: '서울시 강남구',
    hobby: '프로그래밍'
};

const queryString = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURI(value)}`)
    .join('&');

console.log(`https://example.com/user?${queryString}`);
// 출력: "https://example.com/user?name=%EA%B9%80%EC%B2%A0%EC%88%98&city=%EC%84%9C%EC%9A%B8%EC%8B%9C%20%EA%B0%95%EB%82%A8%EA%B5%AC&hobby=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D"
```


`encodeURI()`는 다음 문자들을 그대로 유지합니다:

**예약 문자 (URI 구조에 필요한 문자)**
- `; , / ? : @ & = + $ #`

**비예약 문자 (안전한 문자)**
- `A-Z a-z 0-9 - _ . ! ~ * ' ( )`

**공백은 `%20`으로 변환됩니다**

```javascript
const testCases = {
    reserved: ";,/?:@&=+$#",
    unreserved: "-_.!~*'()",
    alphanumeric: "ABC abc 123",
    korean: "안녕하세요",
    special: "!@#$%^&*()"
};

Object.entries(testCases).forEach(([name, value]) => {
    console.log(`${name}: "${value}" → "${encodeURI(value)}"`);
});

// 출력:
// reserved: ";,/?:@&=+$#" → ";,/?:@&=+$#"
// unreserved: "-_.!~*'()" → "-_.!~*'()"
// alphanumeric: "ABC abc 123" → "ABC%20abc%20123"
// korean: "안녕하세요" → "%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94"
// special: "!@#$%^&*()" → "!@#$%^&*()"
```

`encodeURI()`는 다음 문자들을 그대로 유지합니다:

**예약 문자 (URI 구조에 필요한 문자)**
- `; , / ? : @ & = + $ #`

**비예약 문자 (안전한 문자)**
- `A-Z a-z 0-9 - _ . ! ~ * ' ( )`

**공백은 `%20`으로 변환됩니다**

```javascript
const testCases = {
    reserved: ";,/?:@&=+$#",
    unreserved: "-_.!~*'()",
    alphanumeric: "ABC abc 123",
    korean: "안녕하세요",
    special: "!@#$%^&*()"
};

Object.entries(testCases).forEach(([name, value]) => {
    console.log(`${name}: "${value}" → "${encodeURI(value)}"`);
});

// 출력:
// reserved: ";,/?:@&=+$#" → ";,/?:@&=+$#"
// unreserved: "-_.!~*'()" → "-_.!~*'()"
// alphanumeric: "ABC abc 123" → "ABC%20abc%20123"
// korean: "안녕하세요" → "%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94"
// special: "!@#$%^&*()" → "!@#$%^&*()"
```


| 구분 | encodeURI() | encodeURIComponent() |
|------|-------------|---------------------|
| **용도** | 전체 URI 인코딩 | URI 구성요소 인코딩 |
| **예약문자 처리** | 인코딩하지 않음 | 모두 인코딩 |
| **사용 시기** | 전체 URL 생성 시 | 쿼리 파라미터 값 인코딩 시 |

```javascript
const baseUrl = 'https://example.com/api';
const query = 'name=홍길동&age=25';

// ❌ 잘못된 사용 - 예약문자가 인코딩되지 않음
const wrongUrl = `${baseUrl}?${encodeURI(query)}`;
console.log(wrongUrl);
// 출력: "https://example.com/api?name=홍길동&age=25" (문제!)

// ✅ 올바른 사용 - 쿼리 파라미터 값만 인코딩
const correctUrl = `${baseUrl}?name=${encodeURIComponent('홍길동')}&age=25`;
console.log(correctUrl);
// 출력: "https://example.com/api?name=%ED%99%8D%EA%B8%B8%EB%8F%99&age=25"

// 전체 URL 구조를 유지하면서 특정 값만 인코딩
const params = {
    search: 'JavaScript 강의',
    category: '프로그래밍',
    level: '초급'
};

const queryString = Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&');

const finalUrl = `${baseUrl}?${queryString}`;
console.log(finalUrl);
// 출력: "https://example.com/api?search=JavaScript%20%EA%B0%95%EC%9D%98&category=%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D&level=%EC%B4%88%EA%B8%89"
```






## ⚖️ encodeURI() vs encodeURIComponent()

