---
title: encodeURI - URI
tags: [language, javascript, java]
updated: 2025-12-21
---
# encodeURI() - URI 인코딩 함수

## 정의

`encodeURI()` 함수는 웹 주소(URI)에 포함된 특수 문자들을 안전하게 변환하는 JavaScript 내장 함수입니다.

**URI(Uniform Resource Identifier)**
- 웹에서 리소스(웹페이지, 이미지, 파일 등)를 식별하는 문자열
- URL(Uniform Resource Locator)의 상위 개념
- 예: `https://example.com/path?name=홍길동&age=25`

## 동작 원리

웹 브라우저는 ASCII 문자만 안전하게 처리할 수 있습니다. 한글이나 특수문자가 포함된 URL을 그대로 사용하면 오류가 발생할 수 있어서, 이런 문자들을 안전한 형태로 변환해야 합니다.

```javascript
// 문제가 될 수 있는 URL
const badUrl = 'https://example.com/search?query=안녕하세요&category=음식';

// 안전하게 인코딩된 URL
const goodUrl = encodeURI(badUrl);
console.log(goodUrl);
// 출력: "https://example.com/search?query=%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94&category=%EC%9D%8C%EC%8B%9D"
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
```

이 목록에서 실제로 사고를 내는 것은 예약 문자를 **남긴다**는 쪽이다. 사용자 입력에 `&` 나 `#` 가 섞이면 URL 의 구조 자체가 바뀐다.

```javascript
'q=' + encodeURI('a&b=c#d');            // 'q=a&b=c#d'
'q=' + encodeURIComponent('a&b=c#d');   // 'q=a%26b%3Dc%23d'
```

위쪽은 `q` 하나가 아니라 파라미터 두 개(`q=a`, `b=c`)에 프래그먼트 `#d` 까지 붙은 URL 이 된다. 서버는 `q` 값을 `'a'` 로만 받는다. 검색어에 `&` 하나 들어갔을 뿐인데 결과가 달라지고, 그 검색어를 넣어 본 사람만 재현할 수 있다.

**값 하나를 넣을 때는 언제나 `encodeURIComponent`** 다. `encodeURI` 는 이미 완성된 URL 전체를 통째로 다듬을 때만 쓴다.

`encodeURIComponent` 가 "예약 문자를 모두 인코딩한다"는 것도 정확하지는 않다. 여섯 글자를 남긴다.

```javascript
encodeURIComponent("!'()*");   // "!'()*"  — 그대로다
```

이 글자들은 RFC 3986 기준으로는 예약 문자(sub-delims)인데 함수는 건드리지 않는다. 대부분의 경우 문제가 없지만, 서명 문자열을 만들거나 다른 언어 구현과 결과를 대조해야 한다면 여기서 값이 어긋난다. OAuth 1.0 처럼 정확한 퍼센트 인코딩을 요구하는 규격에서는 이 여섯 글자를 따로 처리해야 한다.

## 사용법

### 기본 사용

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

### URL 파라미터 처리

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
```

## 예제

### encodeURI() vs encodeURIComponent()

| 구분 | encodeURI() | encodeURIComponent() |
|------|-------------|---------------------|
| 용도 | 전체 URI 인코딩 | URI 구성요소 인코딩 |
| 예약문자 처리 | 인코딩하지 않음 | 모두 인코딩 |
| 사용 시기 | 전체 URL 생성 시 | 쿼리 파라미터 값 인코딩 시 |

```javascript
const baseUrl = 'https://example.com/api';
const query = 'name=홍길동&age=25';

// 잘못된 사용 - 예약문자가 인코딩되지 않음
const wrongUrl = `${baseUrl}?${encodeURI(query)}`;
console.log(wrongUrl);

// 올바른 사용 - 쿼리 파라미터 값만 인코딩
const correctUrl = `${baseUrl}?name=${encodeURIComponent('홍길동')}&age=25`;
console.log(correctUrl);

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
```

쿼리 문자열을 손으로 이어 붙일 이유는 이제 없다. `URLSearchParams` 가 키와 값을 모두 인코딩하고, 같은 키가 여러 번 나오는 경우와 `undefined` 처리까지 맡는다.

```javascript
const url = new URL('https://example.com/api');
url.searchParams.set('search', 'JavaScript 강의');
url.searchParams.set('category', '프로그래밍');
url.toString();
```

문서의 `createSafeUrl` 은 **값만** 인코딩하고 키는 그대로 붙인다. 키가 코드에 고정된 문자열이라면 괜찮지만, 키가 데이터에서 온다면 같은 문제가 생긴다.

다만 `URLSearchParams` 에는 알아 둘 차이가 하나 있다. **공백을 `%20` 이 아니라 `+` 로 쓴다.**

```javascript
encodeURIComponent('a b');                       // 'a%20b'
new URLSearchParams({ q: 'a b' }).toString();    // 'q=a+b'
```

둘 다 유효하다. `+` 는 `application/x-www-form-urlencoded` 방식이고 서버 프레임워크는 대개 둘 다 받아준다. 문제는 **직접 디코딩할 때**다.

```javascript
decodeURIComponent('a+b');   // 'a+b'   ← 공백으로 안 돌아온다
```

`decodeURIComponent` 는 `+` 를 모른다. `URLSearchParams` 로 만든 문자열을 손으로 쪼개서 `decodeURIComponent` 로 풀면 공백이 `+` 로 남는다. 파싱도 `new URLSearchParams(queryString)` 에 맡기면 이 차이가 사라진다.

`decodeURI` 와 `decodeURIComponent` 도 짝을 맞춰야 한다. 각자 자기가 인코딩하지 않는 것은 디코딩도 하지 않는다.

```javascript
decodeURI('%26');            // '%26'   ← 그대로 둔다
decodeURIComponent('%26');   // '&'
```

`encodeURIComponent` 로 인코딩한 값을 `decodeURI` 로 풀면 예약 문자만 인코딩된 채 남는다. 에러가 아니라 반쯤 풀린 문자열이 나와서, DB 에 `%26` 같은 것이 저장되고 나서야 발견된다.

### 주의사항

**1. 잘못된 유니코드 문자 처리**
```javascript
// 올바른 유니코드 쌍
console.log(encodeURIComponent("\uD800\uDFFF")); // 정상 작동

// 잘못된 유니코드 (단일 대리 문자)
try {
    console.log(encodeURIComponent("\uD800")); // URIError 발생
} catch (error) {
    console.error('유니코드 오류:', error.message);
}
```

**2. HTTP 요청에서의 올바른 사용**
```javascript
const searchParams = {
    name: '김철수',
    email: 'kim@example.com',
    message: '안녕하세요! 반갑습니다.'
};

// 올바른 방법
const goodQuery = Object.entries(searchParams)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&');
console.log('올바른 쿼리:', goodQuery);
```

## 참고

### 관련 함수

**decodeURI()**
```javascript
const original = 'https://example.com/한글페이지';
const encoded = encodeURI(original);
const decoded = decodeURI(encoded);

console.log('원본:', original);
console.log('인코딩:', encoded);
console.log('디코딩:', decoded);
console.log('일치 여부:', original === decoded); // true
```

**encodeURIComponent() / decodeURIComponent()**
```javascript
const component = 'user@example.com';
const encoded = encodeURIComponent(component);
const decoded = decodeURIComponent(encoded);

console.log('원본:', component);
console.log('인코딩:', encoded); // user%40example.com
console.log('디코딩:', decoded);
```

### 폼 데이터 처리

```javascript
function serializeForm(formData) {
    const params = {};
    
    for (let [key, value] of formData.entries()) {
        if (params[key]) {
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
```
