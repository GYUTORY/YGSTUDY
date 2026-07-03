---
title: Base64 · encodeURIComponent · URLSearchParams — 세 도구 중 뭘 쓸지
tags: [language, javascript, 09es6및고급문법, encoding, base64, url, urlsearchparams]
updated: 2026-04-23
---

# Base64 · encodeURIComponent · URLSearchParams — 세 도구 중 뭘 쓸지

## 이 문서의 범위

각 도구의 상세는 다른 문서에 이미 있다. Base64의 문자셋/패딩/변형은 [Base64 인코딩](../../../DataRepresentation/Encoding/Base64.md), `encodeURIComponent`/`decodeURIComponent`의 예약문자·URIError·보안 이슈는 [encodeURIComponent / decodeURIComponent](./Encode_URI_Component_Decode_URI_Component.md), 퍼센트 인코딩 자체의 개념은 [URL 인코딩](../../../DataRepresentation/Encoding/URL_Encoding.md)에 정리해 뒀다.

이 문서는 그 위에서 하나만 다룬다. **"지금 내 손에 있는 값을 URL에 실을 때, base64/`encodeURIComponent`/`URLSearchParams` 중 뭘 어떤 순서로 써야 하는가"**다. 세 도구는 해결하는 문제가 겹치는 듯하면서도 실제 입력/출력 도메인이 전혀 다르다. 그걸 뭉뚱그리다가 이중 인코딩, 서명 깨짐, 복원 불가 같은 버그가 나온다.

## 세 도구의 입력/출력 도메인

먼저 각 도구가 무엇을 무엇으로 바꾸는지를 정확히 떼어놓고 본다. 이게 헷갈려서 생기는 버그가 태반이다.

| 도구 | 입력 | 출력 | 변환 단위 | 복원 방법 |
|------|------|------|----------|----------|
| `btoa` / `atob` | Latin-1 문자열 | ASCII 문자열 (base64) | 바이트 | `atob` |
| `Buffer.from(str).toString('base64')` | 문자열 + 인코딩 | ASCII 문자열 (base64) | 바이트 | `Buffer.from(b64, 'base64').toString(enc)` |
| `Buffer.from(...).toString('base64url')` | 위와 동일 | ASCII 문자열 (base64url) | 바이트 | 대칭 |
| `encodeURIComponent` | 유니코드 문자열 | ASCII 문자열 (퍼센트) | UTF-8 바이트별 `%XX` | `decodeURIComponent` |
| `URLSearchParams` | `{key: value}` 또는 기존 쿼리스트링 | `key=value&...` 문자열 | 엔트리 단위 | `new URLSearchParams(str)` |

가장 중요한 구분은 이것이다.

- **base64는 "바이너리를 ASCII로"** 바꾸는 도구다. 입력은 원칙적으로 바이트다. 문자열을 받는 `btoa`나 `Buffer.from(str, 'utf8')`도 내부에서는 문자열을 바이트로 바꾼 뒤 base64화한다.
- **`encodeURIComponent`는 "하나의 값 문자열을 URL에 안전하게"** 바꾸는 도구다. 입력은 문자열, 출력도 문자열이지만 값 하나를 위한 것이다.
- **`URLSearchParams`는 "여러 키-값 쌍을 쿼리스트링 문자열로 묶는"** 도구다. 개별 값 인코딩은 내부에서 알아서 한다.

셋은 서로 교체 가능한 도구가 아니라, 체인의 서로 다른 층에서 쓰는 도구다. 바이너리/임의 바이트 → base64 → 이제 "ASCII 문자열"이 되었으니 → `encodeURIComponent` 또는 `URLSearchParams` → URL에 삽입. 거꾸로 "그냥 문자열 값"을 URL에 실을 때는 base64가 필요 없고 `encodeURIComponent` 하나면 된다.

## 의사결정: 지금 내 손에 있는 건 뭔가

실무에서 고민이 되는 순간 판단 포인트는 딱 하나다. **"내가 지금 들고 있는 값이 URL에 직접 실을 수 있는 형태인가?"**

값이 유니코드 문자열(사람이 읽는 텍스트, 숫자, UUID, 보통의 식별자)이라면 base64는 불필요한 층이다. `encodeURIComponent` 또는 `URLSearchParams`로 충분하다. base64를 끼워넣으면 로그에서 읽을 수 없고, 길이가 33% 늘고, 서버 쪽에서 디코드 한 단계가 더 필요해진다. 오히려 손해다.

값이 임의 바이너리(이미지 바이트, 암호화 결과, 해시, 프로토콜 버퍼 직렬화 결과)라면 그대로 `encodeURIComponent`에 넣으면 안 된다. `encodeURIComponent`의 입력은 "유효한 UTF-16 문자열"이고, 바이너리를 문자열로 가장하면 surrogate 문제가 난다. 이때는 먼저 base64(또는 base64url)로 바꿔 ASCII 문자열로 만든 뒤, 그 결과를 `encodeURIComponent`에 넣거나 `URLSearchParams`에 넣는다.

값이 JSON 같은 구조화 데이터라면 선택의 여지가 있다. 평면적인 키-값이면 `URLSearchParams`로 전개하는 게 자연스럽다. 중첩이 있거나 구조 전체를 하나의 토큰처럼 주고받고 싶다면 `JSON.stringify` → UTF-8 바이트 → base64url → URL 삽입 순서가 표준적이다. JWT가 정확히 이 패턴이다.

## 공백 처리: %20 vs +

이게 셋 중 가장 많은 버그의 원인이다. 세 도구가 공백을 다르게 쓴다.

```javascript
encodeURIComponent("hello world");               // "hello%20world"
new URLSearchParams({q: "hello world"}).toString(); // "q=hello+world"
Buffer.from("hello world").toString("base64");   // "aGVsbG8gd29ybGQ=" — 공백은 base64 안에 숨음
```

`encodeURIComponent`는 RFC 3986을 따라 공백을 `%20`으로 쓴다. `URLSearchParams`는 `application/x-www-form-urlencoded` 스펙을 따라 공백을 `+`로 쓴다. 둘 다 웹 서버 프레임워크에서는 보통 해석되지만, 서명을 검증하는 계층(AWS SigV4, OAuth 1.0, 일부 CDN presigned URL)에서는 문제가 된다. SigV4는 공백이 반드시 `%20`이어야 서명이 맞는다.

`URLSearchParams`로 만든 문자열을 서명용으로 쓰려면 `+`를 `%20`으로 바꿔야 한다.

```javascript
const qs = new URLSearchParams({ q: "hello world" })
  .toString()
  .replace(/\+/g, "%20");
```

역방향도 함정이다. 서버에서 폼 인코딩된 쿼리를 받았는데 `decodeURIComponent`만 돌리면 `+`가 그대로 남는다. `+`를 먼저 `%20`으로 치환한 뒤 디코딩해야 한다. 이 쪽 얘기는 [encodeURIComponent 문서의 '+ 기호 함정' 절](./Encode_URI_Component_Decode_URI_Component.md)에서 더 다룬다.

## base64를 URL에 실을 때의 함정

base64 결과를 그대로 URL에 넣으면 깨진다. 표준 base64 문자셋에 포함된 `+`, `/`, `=`이 URL에서 특수한 의미를 가지기 때문이다.

- `+`는 폼 디코더가 공백으로 해석한다.
- `/`는 경로 구분자다. 쿼리 값에는 넣을 수 있지만 경로에 넣으면 분절된다.
- `=`은 쿼리 `key=value`의 구분자다. 값 뒤에 붙으면 모호해진다.

해결 방법은 두 가지다. 어떤 걸 택하느냐에 따라 복원 코드가 달라진다.

**방법 1: base64url을 쓴다.** `+`를 `-`로, `/`를 `_`로 바꾸고 `=` 패딩은 생략한다. RFC 4648 §5에서 정한 URL-safe 변형이다. 결과가 이미 URL-safe하므로 `encodeURIComponent`를 추가로 걸 필요가 없다.

```javascript
// Node.js 16+
const token = Buffer.from(JSON.stringify({ userId: 1 }))
  .toString("base64url");
// "eyJ1c2VySWQiOjF9"

const url = `https://example.com/verify?token=${token}`;
```

**방법 2: 표준 base64를 만들고 `encodeURIComponent`로 감싼다.** 하지만 이건 거의 쓸 이유가 없다. `+`가 `%2B`, `/`가 `%2F`, `=`이 `%3D`로 바뀌어 문자열이 더 길어지고, 복원 시에도 두 단계를 거쳐야 한다.

```javascript
// 권장하지 않음
const b64 = Buffer.from(payload).toString("base64");
const url = `https://example.com/t?x=${encodeURIComponent(b64)}`;
```

혼합 환경에서 base64url을 지원하지 않는 구버전 Node(14 이하)나 특정 라이브러리를 쓸 때만 방법 2가 정당화된다. 그 외에는 무조건 base64url이 낫다.

브라우저에는 `base64url` 직접 변환이 없다. `btoa`로 표준 base64를 만든 뒤 치환한다.

```javascript
function toBase64Url(str) {
  const bytes = new TextEncoder().encode(str);
  const bin = Array.from(bytes, (b) => String.fromCodePoint(b)).join("");
  return btoa(bin)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
```

## URLSearchParams와 encodeURIComponent를 같이 쓰다 생기는 이중 인코딩

가장 흔한 오용 패턴이다. `URLSearchParams`가 이미 인코딩을 해주는데 값에 또 `encodeURIComponent`를 걸어서 넘긴다.

```javascript
// 잘못됨: 이중 인코딩
const q = encodeURIComponent("안녕 하세요");
new URLSearchParams({ q }).toString();
// "q=%25EC%2595%2588%25EB%2585%2595%2520%25ED%2595%2598%25EC%2584%25B8%25EC%259A%2594"

// 정상
new URLSearchParams({ q: "안녕 하세요" }).toString();
// "q=%EC%95%88%EB%85%95+%ED%95%98%EC%84%B8%EC%9A%94"
```

서버가 한 번 디코딩하면 정상 케이스는 `안녕 하세요`를 받지만, 잘못된 케이스는 `%EC%95%88%EB%85%95%20%ED%95%98%EC%84%B8%EC%9A%94`라는 퍼센트 문자가 섞인 문자열을 값으로 받는다. 한 번 더 디코딩해주는 계층이 없으면 그대로 저장되거나 검색에 실패한다.

반대 케이스도 있다. `URLSearchParams.toString()` 결과 전체를 다시 `encodeURIComponent`에 넣는 경우다.

```javascript
// 잘못됨
const qs = new URLSearchParams({ q: "김철수" }).toString();
// "q=%EA%B9%80%EC%B2%A0%EC%88%98"

const url = `https://api.example.com/search?${encodeURIComponent(qs)}`;
// "https://api.example.com/search?q%3D%25EA%25B9%2580..."
```

`encodeURIComponent`가 `=`와 `%`까지 다시 인코딩해서 쿼리 구조 자체가 깨진다. `URLSearchParams.toString()`의 출력은 이미 쿼리스트링이므로 `?`나 `&` 뒤에 그대로 붙이면 된다. 더 감싸지 않는다.

판단 기준은 단순하다. **인코딩 책임을 지는 계층이 하나여야 한다.** `URLSearchParams`를 쓰기로 했으면 값은 원본 그대로 넘기고 `toString()` 결과를 그대로 쓴다. 직접 문자열로 조립한다면 각 값에 `encodeURIComponent`를 걸고 `&`/`=`로 이어 붙인다. 둘을 섞지 않는다.

axios처럼 클라이언트 라이브러리가 내부에서 `URLSearchParams`를 쓰는 경우도 같은 문제가 난다. `params` 옵션에 `encodeURIComponent`로 감싼 값을 넘기면 이중 인코딩이다. 이 얘기는 [encodeURIComponent 문서의 axios/fetch 절](./Encode_URI_Component_Decode_URI_Component.md)에서 자세히 다룬다.

## atob/btoa의 Latin-1 한계

브라우저의 `btoa`/`atob`는 오래된 함수라 **Latin-1(ISO 8859-1) 문자열만** 받는다. 입력 문자 하나가 정확히 1바이트로 매핑되어야 한다는 의미다. 한글, 이모지, 악센트가 붙은 유럽 문자 등은 모두 코드 포인트가 256을 넘기 때문에 그대로 넣으면 예외가 난다.

```javascript
btoa("안녕");   // InvalidCharacterError
btoa("café");  // InvalidCharacterError (é가 U+00E9이긴 한데 엔진에 따라 동작 다름)
btoa("😀");    // InvalidCharacterError
```

문자열을 UTF-8 바이트로 먼저 바꾼 뒤, 그 바이트들을 Latin-1처럼 가장해 `btoa`에 넣어야 한다. 이게 `TextEncoder`를 거치는 이유다.

```javascript
function utf8ToBase64(str) {
  const bytes = new TextEncoder().encode(str);
  const bin = Array.from(bytes, (b) => String.fromCodePoint(b)).join("");
  return btoa(bin);
}

function base64ToUtf8(b64) {
  const bin = atob(b64);
  const bytes = Uint8Array.from(bin, (ch) => ch.codePointAt(0));
  return new TextDecoder().decode(bytes);
}
```

`String.fromCodePoint(b)`로 바이트 하나를 0~255 범위의 코드 포인트 문자로 바꾸면, 그게 Latin-1 문자열 하나처럼 보인다. 여기서 `btoa`가 바이트 단위 base64를 만든다. 역방향은 반대다.

Node에서는 이 고민이 필요 없다. `Buffer.from(str, 'utf8').toString('base64')` 한 줄로 끝난다. Node 16 이후는 `'base64url'` 인코딩도 직접 지원한다.

```javascript
Buffer.from("안녕").toString("base64");     // "7JWI64WV"
Buffer.from("안녕").toString("base64url");  // "7JWI64WV"
Buffer.from("7JWI64WV", "base64").toString(); // "안녕"
```

Node와 브라우저에서 동일한 결과가 나오게 하려면, 브라우저 쪽은 위의 `utf8ToBase64` 같은 래퍼를 두고, Node 쪽은 Buffer를 쓰되 **원본 문자열을 UTF-8로 해석한다는 가정을 명시적으로** 써주는 게 안전하다. 디폴트 인코딩 논쟁으로 시간 낭비하는 경우가 종종 있다.

## 조합 순서의 표준형: JSON → UTF-8 바이트 → base64url → URL 삽입

구조화된 데이터를 URL 하나에 실어 보내는 패턴은 정해져 있다. 순서를 외워두는 게 낫다.

```
객체
  ↓ JSON.stringify
JSON 문자열
  ↓ UTF-8 인코딩 (TextEncoder 또는 Buffer)
바이트 배열
  ↓ base64url
ASCII 문자열 (URL-safe)
  ↓ `?token=${...}` 삽입 (추가 인코딩 불필요)
URL
```

역순으로 풀 때도 같은 순서의 역이다.

```javascript
// 인코딩
const payload = { userId: 1, scope: ["read", "write"] };
const token = Buffer.from(JSON.stringify(payload)).toString("base64url");
const url = `https://example.com/verify?t=${token}`;

// 디코딩
const t = new URL(url).searchParams.get("t");
const restored = JSON.parse(Buffer.from(t, "base64url").toString("utf8"));
```

이 순서에서 실수하기 쉬운 지점이 두 가지 있다.

첫째, **JSON을 건너뛰고 객체를 바로 넘기는 실수**. `Buffer.from({userId: 1})`은 예외는 안 나지만 원하는 결과가 아니다. 객체 → 문자열 변환은 반드시 `JSON.stringify`로 명시해야 한다.

둘째, **base64url 대신 base64를 쓰고 `encodeURIComponent`로 감싸는 경우**. 결과가 동작은 하지만 토큰이 필요 이상으로 길어지고, URL 로그를 볼 때 `%2B`, `%2F`, `%3D`가 섞여 사람이 읽기 나빠진다. base64url로 바꾸면 알파벳·숫자·`-`·`_`만 남아 깔끔하다.

## 서명 깨짐: 인코딩 순서가 의미를 가질 때

서명(HMAC, RSA) 과정이 끼어 있으면 인코딩 순서가 결과물 자체에 영향을 준다. 이 순서를 틀리면 "서버에서 서명 검증이 안 된다"는 버그가 난다.

JWT가 전형적인 예다. 서명 대상은 `header.payload`(base64url된 헤더와 페이로드를 `.`으로 이어붙인 문자열)이다. 이 문자열에 HMAC을 걸어 서명을 만든다.

```
signing_input = base64url(header) + "." + base64url(payload)
signature = HMAC-SHA256(key, signing_input)
jwt = signing_input + "." + base64url(signature)
```

여기서 인코딩 순서를 섞으면 안 된다. 예를 들어 payload를 `encodeURIComponent`로 먼저 감쌌다가 base64url하면 전혀 다른 토큰이 나오고, 검증 서버가 해독하지 못한다. 표준대로 `JSON → UTF-8 → base64url → HMAC` 순서를 지켜야 한다.

AWS SigV4도 비슷하다. Canonical Request를 만들 때 각 파라미터를 `encodeURIComponent`에 준하는 방식(공백 `%20`, `~` 유지)으로 인코딩한 뒤, 정렬하고 `&`로 이어붙여 해시한다. 이 단계에서 `URLSearchParams.toString()`을 그대로 쓰면 공백이 `+`로 나와 서명이 깨진다. 이런 케이스는 `URLSearchParams`가 아니라 직접 조립해야 한다.

## 실무에서 자주 보는 오용 패턴

지금까지 얘기한 걸 패턴 레벨로 정리하면 아래 케이스가 반복된다.

**1) base64를 "암호화"로 쓰는 경우**. base64는 누구나 1초에 복원할 수 있는 인코딩이다. URL에 민감 정보를 실으면 로그에도 남고, 브라우저 history에도 남고, 중간 프록시도 본다. base64 때문에 안 보일 거라고 생각하면 안 된다. 민감값은 서명된 토큰으로 감싸거나, 서버 세션에 저장하고 키만 넘기는 구조를 쓴다.

**2) 이중 인코딩**. 위에서 본 `URLSearchParams` + `encodeURIComponent` 조합이 대표 사례다. 축약하면 "인코딩은 경계마다 한 번"이다. 클라이언트에서 한 번, 서버에서 한 번 디코딩이 원칙이다. 중간에 한 계층이 더 인코딩·디코딩하면 전체 체인이 어긋난다.

**3) 복원 불가 변환**. 가장 질 나쁜 버그다. `decodeURIComponent` 대신 URL 파서가 해준 디코딩을 또 한 번 하거나, 원본이 이미 base64url인데 표준 base64 디코더로 해독을 시도하는 경우다. 둘 다 "동작하는 것처럼 보이다가" 특정 입력에서만 다른 결과가 나온다. 로그에서 원본 바이트를 반드시 남겨둬야 디버깅 가능하다.

**4) 서명 입력과 전송 값 불일치**. 서명할 때 쓴 인코딩과 실제로 URL에 실은 인코딩이 다르면 서명 검증이 실패한다. `+`/`%20` 문제가 여기에 집약된다. 서명 대상 문자열과 전송 문자열이 **바이트 수준으로 동일**한지 점검해야 한다.

**5) 브라우저·Node 결과 차이**. 같은 입력에 대해 두 런타임이 다른 base64를 내놓는 것처럼 보이는 경우, 십중팔구 문자 인코딩(UTF-8 가정) 처리 부재다. 브라우저 `btoa`는 Latin-1을 가정하고, Node의 `Buffer.from(str)`은 디폴트가 `'utf8'`이다. 이 비대칭을 잊으면 한글이 포함된 값에서만 깨진다.

## 빠른 의사결정 요약

값이 지금 어떤 모양인지만 파악하면 선택은 자동이다.

- **키-값 쌍 여러 개를 쿼리로 묶는다** → `URLSearchParams`. 개별 값에 `encodeURIComponent`를 또 걸지 않는다. 서명이 필요하면 `+`를 `%20`으로 후처리.
- **값 하나를 경로 세그먼트나 쿼리에 넣는다** → `encodeURIComponent`. 값이 유니코드 문자열이면 이걸로 끝이다.
- **값이 임의 바이너리거나, 구조화된 객체 전체를 토큰화한다** → `JSON.stringify` → UTF-8 → `base64url` → URL 삽입. `encodeURIComponent`는 불필요하다.
- **값이 표준 base64(`+`,`/`,`=` 포함)로 이미 만들어졌다** → 새로 만들 수 있으면 `base64url`로 다시 만든다. 못 만드는 상황이면 `encodeURIComponent`로 감싼다.
- **서명을 만드는 중이다** → 서명 입력과 전송 URL이 완전히 같은 바이트가 되도록 인코딩 규칙을 맞춘다. 애매하면 `URLSearchParams` 대신 수동 조립.
