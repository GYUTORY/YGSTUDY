---
title: encodeURI / URL 인코딩
tags: [javascript, language]
updated: 2026-09-22
---

# encodeURI / URL 인코딩

브라우저는 주소창에 직접 입력한 한글을 자동으로 인코딩하지만, JavaScript 코드에서 URL 을 문자열로 직접 조립할 때는 그 처리를 손으로 해야 한다. 잘못 인코딩하면 서버가 파라미터를 다르게 파싱하거나 의도하지 않은 경로로 요청이 간다.

`encodeURI` 와 `encodeURIComponent` 는 이름이 비슷해서 혼동하기 쉬운데, 쓰임새가 완전히 다르다.

## 두 함수가 보존하는 문자

`encodeURI` 는 완성된 URI 전체를 인수로 받는다. URI 구조를 이루는 문자는 건드리지 않고 그 외의 문자만 퍼센트 인코딩한다.

보존되는 문자는 세 종류다. 영문자·숫자(`A-Z a-z 0-9`), URI 예약 문자(`: / ? # [ ] @ ! $ & ' ( ) * + , ; =`), 비예약 문자(`- _ . ~ `)가 그대로 살아남는다. 한글, 한자, 공백, `%` 를 비롯한 나머지 문자들은 UTF-8 로 변환된 뒤 퍼센트 인코딩된다.

```javascript
encodeURI('https://example.com/검색?q=한글&lang=ko');
// 'https://example.com/%EA%B2%80%EC%83%89?q=%ED%95%9C%EA%B8%80&lang=ko'
```

`?`, `&`, `=` 는 그대로 남고 한글만 바뀌었다. URL 구조 자체는 유지되는 것이 `encodeURI` 의 목적이다.

`encodeURIComponent` 는 URI 구성 요소 하나, 예를 들어 파라미터 값 하나를 받는다. 예약 문자도 포함해서 대부분을 인코딩한다. 예외는 딱 다섯 글자(`! ' ( ) *`)뿐이다.

```javascript
encodeURIComponent('https://example.com/?q=값');
// 'https%3A%2F%2Fexample.com%2F%3Fq%3D%EA%B0%92'
```

`://`, `/`, `?`, `=` 까지 전부 인코딩됐다. 완성된 URL 에 이 함수를 쓰면 URL 이 동작하지 않는다.

## 실제로 뒤통수를 치는 경우

### 쿼리 파라미터 값에 & 가 포함될 때

검색어 같은 사용자 입력을 `encodeURI` 로 인코딩하면 `&` 가 그대로 남는다.

```javascript
const keyword = 'A&B테스트';
const url = `https://example.com/search?q=${encodeURI(keyword)}`;
// 'https://example.com/search?q=A&B%ED%85%8C%EC%8A%A4%ED%8A%B8'
```

서버는 이 URL 을 `q=A` 와 `B테스트=` 두 개의 파라미터로 파싱한다. `q` 값은 `'A'` 만 들어온다. `encodeURI` 가 `&` 를 URI 구조 문자로 보존했기 때문이다.

이런 버그는 대부분의 검색어가 한글이라 로컬 테스트에서 쉽게 확인되지 않는다. `&` 가 섞인 입력을 쓴 사람만 재현할 수 있어서, "특정 검색어가 결과가 안 나온다"는 신고로 발견되는 경우가 많다.

```javascript
const url = `https://example.com/search?q=${encodeURIComponent(keyword)}`;
// 'https://example.com/search?q=A%26B%ED%85%8C%EC%8A%A4%ED%8A%B8'
```

값 하나를 URL 에 붙일 때는 `encodeURIComponent` 를 써야 한다. `encodeURI` 는 이미 완성된 URL 을 통째로 다듬을 때만 의미가 있다.

### 경로 세그먼트에 슬래시가 들어올 때

카테고리 이름 같은 값을 경로에 넣을 때 그 값 안에 슬래시가 있으면 `encodeURI` 로는 막을 수 없다.

```javascript
const category = '음식/간식';
encodeURI(`https://example.com/category/${category}`);
// 'https://example.com/category/%EC%9D%8C%EC%8B%9D/%EA%B0%84%EC%8B%9D'
```

`/` 가 예약 문자라 경로 구분자로 남는다. `음식` 디렉토리 아래 `간식` 경로가 된다. 의도한 것과 다르다면, 값은 `encodeURIComponent` 로 따로 인코딩한 뒤 경로에 붙여야 한다.

### encodeURIComponent 가 남기는 다섯 글자

`! ' ( ) *` 는 `encodeURIComponent` 도 인코딩하지 않는다. RFC 3986 기준으로는 sub-delimiters 에 해당하지만, 함수 구현이 이전 RFC 2396 을 따른 탓이다.

일반적인 URL 조립에서는 문제가 안 된다. OAuth 1.0a 처럼 서명 문자열의 퍼센트 인코딩을 정확히 정의하는 규격을 구현할 때는 이 다섯 글자를 직접 치환해야 한다.

```javascript
function strictEncode(str) {
  return encodeURIComponent(str)
    .replace(/!/g, '%21')
    .replace(/'/g, '%27')
    .replace(/\(/g, '%28')
    .replace(/\)/g, '%29')
    .replace(/\*/g, '%2A');
}
```

## decode 함수와의 짝

`encodeURI` 로 인코딩한 것은 `decodeURI` 로, `encodeURIComponent` 로 인코딩한 것은 `decodeURIComponent` 로 풀어야 한다. 각 함수는 자신이 인코딩하지 않는 문자는 디코딩도 하지 않는다.

```javascript
decodeURI('%26');            // '%26'  — 그대로 남는다
decodeURIComponent('%26');  // '&'
```

`encodeURIComponent` 로 인코딩한 값을 `decodeURI` 로 풀면 `&`, `=`, `?` 가 `%26`, `%3D`, `%3F` 로 남는다. 에러가 나지 않고 반쯤 풀린 문자열이 나오기 때문에, DB 에 `%26` 이 저장되고 나서야 발견되는 경우가 있다.

잘못 분리된 유니코드 서로게이트 쌍을 인코딩하려 하면 `URIError` 가 발생한다. 외부 데이터를 URL 에 그대로 붙이는 코드에서 만날 수 있다.

```javascript
encodeURIComponent('\uD800');  // URIError: URI malformed
```

## URLSearchParams 로 위임하기

쿼리 파라미터를 직접 이어 붙일 때 흔한 실수가 값만 인코딩하고 키는 그대로 쓰는 것이다. 키가 코드에 고정된 문자열이라면 괜찮지만, 키가 데이터에서 올 때는 같은 문제가 생긴다. `URLSearchParams` 는 키와 값을 모두 인코딩한다.

```javascript
const url = new URL('https://api.example.com/search');
url.searchParams.set('keyword', '검색어 & 특수문자');
url.searchParams.set('page', '1');
url.toString();
// 'https://api.example.com/search?keyword=%EA%B2%80%EC%83%89%EC%96%B4+%ED%8A%B9%EC%88%98%EB%AC%B8%EC%9E%90&page=1'
```

`URLSearchParams` 는 공백을 `%20` 이 아닌 `+` 로 쓴다. `application/x-www-form-urlencoded` 인코딩 방식이고, 서버 프레임워크는 대부분 둘 다 받는다.

문제는 이 문자열을 나중에 수동으로 파싱할 때다. `decodeURIComponent` 는 `+` 를 공백으로 해석하지 않는다.

```javascript
decodeURIComponent('a+b');  // 'a+b'  — 공백으로 안 돌아온다
```

`URLSearchParams` 로 만든 문자열을 `split('&')` 으로 쪼개서 `decodeURIComponent` 로 풀면 공백이 `+` 로 남는다. 파싱도 `new URLSearchParams(queryString)` 에 맡기면 이 차이가 사라진다.
