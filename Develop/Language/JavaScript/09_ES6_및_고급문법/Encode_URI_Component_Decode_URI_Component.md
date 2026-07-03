---
title: encodeURIComponent / decodeURIComponent
tags: [language, javascript, 09es6및고급문법, encoding, url, security]
updated: 2026-04-23
---

# encodeURIComponent / decodeURIComponent

## 이 문서의 범위

퍼센트 인코딩의 일반적인 개념은 [URL 인코딩](../../../DataRepresentation/Encoding/URL_Encoding.md) 문서에서 다룬다. `encodeURI` 전반적인 설명은 [encodeURI](./encodeURI.md) 문서에 있다. 이 문서는 `encodeURIComponent`/`decodeURIComponent` 쌍에서 실무에서 자주 문제가 되는 부분만 다룬다. 예약문자 처리 범위 차이, 사용 위치별 함정, URIError, 이중 디코딩 공격, HTTP 클라이언트와의 충돌, 폼 인코딩과의 차이 같은 것들이다.

## encodeURI와 encodeURIComponent의 경계선

둘의 차이를 한 문장으로 요약하면 "`encodeURI`는 URL 구조를 깨지 않으려고 예약문자를 남겨두는 반면, `encodeURIComponent`는 값이니까 예약문자까지 전부 인코딩한다"다. 이 차이를 정확히 이해하지 못하면 서비스가 동작은 하는데 간헐적으로 `&`, `=`, `#`이 포함된 값에서만 깨지는 버그를 만나게 된다.

`encodeURIComponent`가 인코딩하지 않는 문자는 아래 11개뿐이다.

```
A-Z a-z 0-9 - _ . ! ~ * ' ( )
```

`encodeURI`는 여기에 더해서 URL 구조에 쓰이는 예약문자 `; , / ? : @ & = + $ #`까지 유지한다. 즉 값을 감싸는 용도(하나의 파라미터 값, 경로 세그먼트 하나)라면 `encodeURIComponent`를, URL 전체를 한 번에 다룬다면 `encodeURI`를 쓴다.

```javascript
const value = "a&b=c/d?e#f";

encodeURI(value);          // "a&b=c/d?e#f"  — 그대로
encodeURIComponent(value); // "a%26b%3Dc%2Fd%3Fe%23f"
```

실무에서는 `encodeURI`를 쓸 일이 생각보다 적다. 직접 문자열을 조립해 URL을 만드는 경우가 대부분이고, 그때 값 부분만 `encodeURIComponent`로 감싸는 패턴이 일반적이다. `encodeURI`는 "유저가 입력한 완성된 URL을 한 번 정리해서 사용하고 싶다" 같은 드문 케이스 정도다.

## 인코딩되는 문자와 유지되는 문자

RFC 3986의 unreserved set은 `A-Z a-z 0-9 - _ . ~`이지만, `encodeURIComponent`는 여기에 RFC 2396 시절의 mark 문자 `! ~ * ' ( )`까지 안 건드린다. 표준 변경 과정에서 뒤처진 것이고, 이게 실무에서 종종 문제를 일으킨다.

```javascript
encodeURIComponent("!*'()"); // "!*'()"  — 인코딩 안 됨
```

`(`, `)`가 그대로 남으면 HTML이나 CSS 컨텍스트에서 문제가 된다. 대표적으로 OG 이미지 URL을 CSS `url()`에 넣거나, 마크다운 링크에 값을 삽입할 때 괄호가 파싱을 깨뜨린다. 이런 경우 `encodeURIComponent` 결과에 대해 추가 치환을 하는 패턴을 자주 쓴다.

```javascript
function strictEncode(value) {
  return encodeURIComponent(value).replace(/[!*'()]/g, (c) =>
    "%" + c.charCodeAt(0).toString(16).toUpperCase()
  );
}
```

RFC 3986에 엄격히 맞추려면 위처럼 해야 하지만, 보통은 기본 동작으로도 충분하다. 괄호가 문제가 되는 컨텍스트(Markdown, CSS url, 정규식)를 다룰 때만 한 번 더 감싸는 식으로 대응하면 된다.

## 어디에 쓰느냐에 따라 인코딩 범위가 다르다

값을 URL에 넣는다고 뭉뚱그려 생각하면 실수가 나온다. URL은 위치마다 허용 문자가 다르다.

- **경로 세그먼트(path segment)**: `/users/홍길동` 같은 곳. `/`는 세그먼트 구분자라 값에 들어가면 안 된다. 값에 슬래시가 포함될 수 있다면 반드시 `encodeURIComponent`로 감싸야 경로가 쪼개지지 않는다.
- **쿼리 파라미터 값(query value)**: `?key=value`의 value. `&`와 `=`이 구분자이므로 값에 들어가면 파싱이 깨진다.
- **쿼리 파라미터 키(query key)**: 의외로 키도 인코딩 대상이다. 키에 `=`이나 `&`이 섞이는 경우는 드물지만 한글 키를 쓰는 경우가 있다.
- **프래그먼트(fragment)**: `#` 뒤. 서버에는 전송되지 않고 클라이언트에서만 쓰인다. 프래그먼트 안에서는 `#`을 다시 쓸 수 없지만 `?`, `/`는 비교적 자유롭다. 그래도 값으로 넣을 거면 `encodeURIComponent`로 감싸는 게 안전하다.

경로 세그먼트에 유저 입력을 그대로 끼워넣는 아래 코드가 왜 위험한지 생각해 보자.

```javascript
// 위험: name에 "/" 들어가면 path가 달라진다
const url = `https://api.example.com/users/${name}/profile`;

// 안전
const url = `https://api.example.com/users/${encodeURIComponent(name)}/profile`;
```

`name = "../admin"` 같은 값이 들어오면 첫 번째 코드는 `/users/../admin/profile`이 되고, 서버 혹은 프록시에서 path normalization을 하면 `/admin/profile`로 바뀐다. 이게 Path Traversal의 시작점이다.

## URLSearchParams와 비교

직접 `encodeURIComponent`로 조립하는 대신 `URLSearchParams`를 쓰면 대부분의 실수를 피할 수 있다. 다만 한 가지 차이가 있는데, `URLSearchParams`는 공백을 `%20`이 아니라 `+`로 인코딩한다.

```javascript
const params = new URLSearchParams({ q: "hello world" });
params.toString(); // "q=hello+world"

encodeURIComponent("hello world"); // "hello%20world"
```

`application/x-www-form-urlencoded` 스펙에서는 공백을 `+`로 쓰도록 되어 있고, `URLSearchParams`가 그 스펙을 따른다. 서버 쪽 프레임워크(Express, Spring, FastAPI)는 둘 다 해석하니까 실무에서는 문제가 되지 않는다. 다만 URL 문자열을 눈으로 비교하거나 서명 검증에 쓸 때(예: AWS SigV4, OAuth 1.0 서명)는 문제가 된다. AWS SigV4는 공백이 `%20`이어야 서명이 맞는다. 이 경우 `URLSearchParams`의 출력을 `.replace(/\+/g, "%20")`으로 고쳐주거나 직접 `encodeURIComponent`로 만드는 편이 안전하다.

반대로 키와 값에 들어 있는 `+` 기호 자체는 `URLSearchParams`가 `%2B`로 잘 인코딩한다.

```javascript
new URLSearchParams({ math: "1+1" }).toString(); // "math=1%2B1"
```

순수 문자열로 URL을 만들 때 값에 포함된 `+`를 깜빡하고 인코딩하지 않으면 서버에서 공백으로 해석되어 엉뚱한 버그가 생긴다. 이 이야기는 아래 "+ 기호 함정" 절에서 자세히 본다.

## decodeURIComponent의 URIError

`decodeURIComponent`는 입력이 유효한 퍼센트 인코딩 형식이 아닐 때 `URIError`를 던진다. 대표적으로 두 가지 경우다.

**잘못된 퍼센트 시퀀스**: `%` 뒤에 16진수 두 자리가 오지 않은 경우.

```javascript
decodeURIComponent("%"); // URIError: URI malformed
decodeURIComponent("%ZZ"); // URIError
decodeURIComponent("%2"); // URIError
```

**단일 UTF-8 바이트만 디코딩된 경우**: UTF-8로는 유효하지 않은 바이트 시퀀스.

```javascript
decodeURIComponent("%C3"); // URIError — C3은 UTF-8에서 2바이트의 시작 바이트
decodeURIComponent("%C3%A9"); // "é" — 정상
```

유저 입력이나 외부에서 들어온 URL 쿼리스트링을 디코딩할 때 이 예외를 막지 않으면 서버 전체가 500으로 내려간다. Express 미들웨어나 Next.js 라우트 핸들러에서 한 번은 만나게 되는 패턴이다. 방어적으로 감싸는 헬퍼를 두는 게 좋다.

```javascript
function safeDecode(value) {
  if (value == null) return value;
  try {
    return decodeURIComponent(value);
  } catch {
    return value; // 혹은 null, 혹은 원본 바이트 그대로 처리
  }
}
```

Node.js의 `querystring.parse`, `URL` 클래스의 `searchParams`는 내부적으로 `decodeURIComponent`를 쓰므로 같은 문제가 있다. `URL` 생성 단계에서 `TypeError`가 나지는 않지만, 쿼리 값을 꺼낼 때 잘못된 퍼센트 시퀀스가 있으면 예외가 발생한다.

## 단일 대리 유니코드 문제

UTF-16 surrogate pair로 표현되는 문자(예: 이모지, 일부 한자)를 반쪽만 넘기면 `encodeURIComponent`가 `URIError`를 던진다.

```javascript
encodeURIComponent("😀"); // "%F0%9F%98%80" — 웃는 이모지
encodeURIComponent("\uD83D"); // URIError: URI malformed
```

이게 실무에서 왜 문제냐면, 문자열을 바이트/문자 단위로 자르는 로직(예: 닉네임 최대 10자 자르기)이 surrogate pair 중간을 잘라버리면 그 뒤 어딘가에서 인코딩하다가 터진다. `string.slice(0, 10)`은 UTF-16 코드 유닛 기준이라 이 문제가 흔하게 생긴다. 해결은 보통 두 가지 중 하나다.

- `Array.from(str).slice(0, 10).join("")` — 코드 포인트 기준
- `Intl.Segmenter`로 grapheme 단위 분할

어느 쪽이든 저장/전송 전에 정규화된 문자열만 `encodeURIComponent`에 넘기는 게 안전하다.

## 이중 디코딩과 보안

이게 이 문서에서 가장 중요한 부분이다. `decodeURIComponent`를 같은 값에 두 번 적용하는 코드는 공격자에게 필터 우회 경로를 준다.

대표적인 시나리오를 보자. 어떤 서비스가 유저 입력을 받아서 외부 API에 프록시한다. 서비스는 보안을 위해 요청 경로에 `..`이 포함되어 있으면 거부한다.

```javascript
function proxyRequest(userPath) {
  const decoded = decodeURIComponent(userPath);
  if (decoded.includes("..")) throw new Error("traversal");

  // 내부 fetch가 또 디코딩한다고 가정
  return fetch(`https://internal.api/${userPath}`);
}
```

공격자가 `%252e%252e%252fadmin`을 보낸다. `%25`는 `%`의 퍼센트 인코딩이다.

1. `decodeURIComponent("%252e%252e%252fadmin")` → `%2e%2e%2fadmin`. 필터에 `..`이 없으니 통과.
2. `fetch` 내부에서 한 번 더 디코딩되면 → `../admin`. 실제 요청은 traversal이 된 상태로 나간다.

이 패턴은 Path Traversal뿐 아니라 SSRF에서도 자주 보인다. `http://internal` 같은 내부 호스트 차단 필터를 `%2568%2574%2574%2570%253a%252f%252finternal` 같은 이중 인코딩으로 우회한다. 방어의 원칙은 두 가지다.

첫째, **디코딩은 한 번만 한다.** 동일한 값에 대해 여러 계층이 디코딩하는 구조면 가장 안쪽 계층으로 검증을 미루거나, 가장 바깥에서 한 번만 디코딩하고 이후로는 원본을 그대로 전달한다.

둘째, **검증은 항상 최종 디코딩된 값에 대해 한다.** 원본에 `..`이 없다는 것은 의미가 없다. 실제로 서버가 파일 시스템이나 URL로 해석할 문자열 기준으로 검사해야 한다.

Node.js에서 `path.resolve`로 정규화한 뒤 `startsWith(allowedRoot)`로 검사하는 패턴이 이래서 중요하다. 문자열 레벨의 `includes("..")`는 항상 우회 가능하다고 보면 된다.

## + 기호 함정 (폼 인코딩 vs URI 인코딩)

가장 헷갈리는 부분이다. 결론부터 쓰면 이렇다.

- `encodeURIComponent("a b")` → `"a%20b"`
- `decodeURIComponent("a+b")` → `"a+b"` — `+`를 공백으로 바꾸지 **않는다**
- `decodeURIComponent("a%20b")` → `"a b"`

즉 `decodeURIComponent`는 `+`를 리터럴 플러스 기호로 본다. 반면 `application/x-www-form-urlencoded` 스펙에서는 `+`가 공백이다. 브라우저가 폼을 제출할 때, jQuery의 `$.param`, `URLSearchParams`, Python `urllib.parse.urlencode`는 전부 공백을 `+`로 보낸다.

그래서 서버에서 쿼리스트링을 받아 수동으로 `decodeURIComponent`만 돌리면 `+`가 그대로 남아서 "홍길동+김철수" 같은 이름이 이상하게 파싱된다. 반대로 `encodeURIComponent`로 만든 URL을 서버가 폼 디코더로 해석하면 `+`(리터럴)가 공백으로 잘못 해석된다. 이 불일치는 실제 운영 중인 API에서 "검색어에 플러스 들어가면 공백으로 바뀌어요" 같은 버그로 드러난다.

실무 해법은 간단하다.

```javascript
function decodeFormValue(v) {
  return decodeURIComponent(v.replace(/\+/g, "%20"));
}
```

폼 인코딩된 값을 받는다는 걸 알면 `+`를 `%20`으로 먼저 치환한 뒤 디코딩한다. 반대로 값을 URL에 실을 때 `+`가 리터럴이어야 한다면 `encodeURIComponent`를 쓰되, 서버 쪽이 폼 디코더라면 `+`를 명시적으로 `%2B`로 바꿔주는 게 안전하다.

## axios, fetch의 자동 인코딩과 충돌

`fetch`는 URL 문자열을 그대로 보내는 쪽이라 개발자가 인코딩을 책임진다. `fetch("/users/${name}")`에서 name에 한글이 들어가면 크롬은 알아서 퍼센트 인코딩하지만, 이건 `URL` 파서가 자동으로 해주는 최소한의 인코딩이지 값 경계 인식이 아니다. 예약문자는 그대로 간다.

axios는 `params` 옵션으로 객체를 넘기면 내부에서 직렬화한다. 기본 `paramsSerializer`가 `URLSearchParams`를 쓰기 때문에 공백이 `+`로 인코딩된다. AWS 서명 같은 곳에서 쓰면 서명이 깨진다. axios 1.x에서는 `paramsSerializer: { serialize: (params) => ... }` 형태로 커스터마이징한다.

흔한 버그 패턴이 "값에 직접 `encodeURIComponent`를 걸어서 `params`로 넘기는 것"이다.

```javascript
// 이중 인코딩된다
axios.get("/search", {
  params: { q: encodeURIComponent("안녕 하세요") },
});
// 실제 요청: /search?q=%25EC%2595%2588%25EB%2585%2595%2520%25ED%2595%2598%25EC%2584%25B8%25EC%259A%2594
```

라이브러리가 이미 인코딩을 해주는 경우에는 원본 값을 그대로 넘겨야 한다. 이중 인코딩은 서버에서 디코딩을 한 번만 하면 `%EC%95%88...` 같은 원본 인코딩 문자열을 값으로 받게 되어 한글이 아니라 퍼센트 문자가 섞인 이상한 문자열이 된다. 반대로 `URL` 문자열에 직접 값을 박을 때는 `encodeURIComponent`가 필요하다. 라이브러리별로 "누가 인코딩을 책임지는가"를 한 번씩 확인해야 한다.

## Buffer, TextEncoder와 바이트 레벨 동작

`encodeURIComponent`는 입력 문자열을 UTF-8로 바이트화한 뒤 각 바이트를 `%XX`로 바꾼다. 이게 기본이자 유일한 동작이다. EUC-KR 같은 다른 인코딩을 쓰고 싶다면 함수로는 불가능하고 직접 바이트를 만들어야 한다.

```javascript
// Node.js 환경
const buf = Buffer.from("한글", "utf8");
const percentEncoded = [...buf]
  .map((b) => "%" + b.toString(16).toUpperCase().padStart(2, "0"))
  .join("");
// "%ED%95%9C%EA%B8%80"

// encodeURIComponent와 결과 같음
encodeURIComponent("한글"); // "%ED%95%9C%EA%B8%80"
```

구형 서버가 EUC-KR 쿼리스트링을 받는 경우(일부 국내 레거시 시스템), 브라우저 기본 인코딩으로는 못 만든다. 서버에서 `iconv`로 디코딩하게 두거나, 클라이언트에서 `Buffer.from(str, "binary")` 같은 트릭을 쓰는데 이건 환경 제약이 크다. 가능하면 서버 쪽을 UTF-8로 올려달라고 협의하는 게 낫다.

반대로 디코딩 쪽에서도, 서버가 올려준 값이 UTF-8이 아니라 CP949로 인코딩되어 있는데 `decodeURIComponent`에 그대로 먹이면 `URIError` 또는 깨진 문자열이 나온다. 이런 경우 `decodeURIComponent` 대신 바이트로 뽑아서 적절한 코덱으로 디코딩한다.

## JWT payload를 URL에 실을 때: base64url vs encodeURIComponent

JWT나 서명된 토큰을 URL 쿼리 파라미터에 실어 보내는 시나리오가 흔하다. 이메일 링크, SSO 리다이렉트, 매직 링크 로그인 같은 곳이다. 두 선택지가 있다.

첫 번째는 `encodeURIComponent(jwt)`다. JWT는 `xxxx.yyyy.zzzz` 형태에 base64url 문자만 있다. base64url은 이미 URL-safe 문자(`A-Z a-z 0-9 - _`)만 쓰는 인코딩이라 이론적으로는 인코딩이 필요 없다. 하지만 `.`도 unreserved라 `encodeURIComponent`에서도 인코딩되지 않는다.

```javascript
const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc-def_xyz";
encodeURIComponent(jwt); // "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc-def_xyz" — 바뀐 게 없다
```

그래서 JWT를 쿼리에 실을 때 `encodeURIComponent`를 호출해도 호출 안 해도 결과가 같다. 그럼에도 **호출하는 걸 권장**한다. 이유는 두 가지다.

1. JWT 라이브러리가 미래에 base64(url이 아닌) 출력을 섞어 쓰게 되면 `+`, `/`, `=`이 끼어들 수 있는데, `encodeURIComponent`를 걸어두면 알아서 안전해진다.
2. 코드 리뷰 시 "URL에 값 실으면 인코딩한다"는 원칙을 지키는 게 일관성 측면에서 낫다. 예외를 두면 나중에 비슷한 패턴에서 인코딩을 빼먹는 실수가 생긴다.

두 번째는 "base64url로 인코딩하고 끝"이다. JWT가 아닌 임의의 바이너리 payload를 URL에 실을 때 선택지가 된다. base64(`+`, `/`, `=` 포함)로 인코딩하면 URL에 바로 못 넣는다. base64url(`-`, `_`, 패딩 생략)로 인코딩하면 URL에 그대로 넣을 수 있다. 노드에서는 아래처럼 쓴다.

```javascript
// Node.js 16+
const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
// URL에 그대로 붙여도 됨
const url = `https://example.com/verify?token=${encoded}`;

// 디코딩
const decoded = JSON.parse(Buffer.from(token, "base64url").toString("utf8"));
```

요컨대 "원본이 ASCII 문자열이고 URL에 넣고 싶다"면 `encodeURIComponent`, "원본이 임의 바이너리거나 객체를 직렬화한 결과"라면 base64url이 자연스럽다. JWT는 이미 base64url이 적용된 형태라 `encodeURIComponent`가 실질적으로는 noop이지만 습관적으로 거는 편이 안전하다.

## 트러블슈팅 체크 순서

실무에서 퍼센트 인코딩 관련 버그를 만나면 아래 순서로 확인한다.

**1) 어느 계층에서 인코딩/디코딩이 일어나는지 전부 파악한다.** 브라우저(URL 파서), HTTP 클라이언트(axios/fetch), 게이트웨이(nginx, ALB), 서버 프레임워크(Express, Spring), 애플리케이션 코드. 각 계층이 한 번씩 디코딩한다고 생각하면 어디서 이중 디코딩이 일어나는지 보인다.

**2) `+` 기호가 원인인지 본다.** 값에 `+`가 들어가는 검색, 수식, 전화번호 등에서 문제가 생기면 대부분 이 이슈다. 클라이언트와 서버 중 한쪽이 폼 인코딩, 다른 쪽이 URI 인코딩으로 해석하고 있다.

**3) 원본 바이트를 로그로 남긴다.** 서버에서 받은 raw 쿼리스트링(디코딩 전)을 먼저 찍어본다. 인코딩 값이 정상으로 왔는데 프레임워크가 잘못 해석하는 건지, 클라이언트부터 잘못 만든 건지 구분된다.

**4) 유니코드 정규화를 의심한다.** 동일해 보이는 한글도 NFC/NFD로 다르면 바이트가 다르고, 그러면 퍼센트 인코딩 결과도 다르다. 특히 macOS 파일명(NFD)과 윈도우(NFC) 사이를 오가는 시스템에서 발생한다. `str.normalize("NFC")`로 정규화한 뒤 인코딩한다.

**5) 서드파티 문서를 신뢰하지 말고 직접 만들어본다.** OAuth, S3 presigned URL, CDN 서명 등 서명이 관련되면 공백/`+`/`*`/`~` 처리 규칙이 각각 다르다. 문서에 RFC 3986이라고 적혀 있어도 실제 구현이 다른 경우가 많다. 작은 스크립트로 알려진 입력/출력 쌍을 재현해보는 게 가장 빠르다.
