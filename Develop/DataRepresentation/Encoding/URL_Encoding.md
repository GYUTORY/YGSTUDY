---
title: URL 인코딩 (Percent Encoding) 심화
tags: [encoding, url, percent-encoding, web, rfc-3986, whatwg, utf-8]
updated: 2026-06-09
---

# URL 인코딩 (Percent Encoding)

## URL에서 쓸 수 있는 문자는 정해져 있다

RFC 3986 기준으로 URL에 그대로 쓸 수 있는 문자(Unreserved Characters)는 다음뿐이다.

```
A-Z a-z 0-9 - _ . ~
```

이 외의 문자는 퍼센트 인코딩 처리를 해야 한다. `%` 뒤에 해당 바이트의 16진수 값 두 자리를 붙이는 방식이다.

```
공백 → %20
/ → %2F
? → %3F
# → %23
& → %26
= → %3D
```

예약 문자(Reserved Characters)인 `:`, `/`, `?`, `#`, `&`, `=` 등은 URL 구조에서 구분자 역할을 한다. 이 문자들을 데이터 값으로 쓰려면 반드시 인코딩해야 한다.


## RFC 3986 BNF 문법으로 본 percent-encoding

RFC 3986은 URL 문법을 ABNF로 정의한다. 퍼센트 인코딩의 핵심 규칙은 다음 한 줄이다.

```
pct-encoded = "%" HEXDIG HEXDIG
```

`HEXDIG`는 `0-9`, `A-F`, `a-f` 모두 허용한다. 즉 `%2f`와 `%2F`는 동등하지만, RFC 3986 §6.2.2.1은 대문자 사용을 권장한다. 디코딩은 두 형태 다 받지만 인코딩 출력은 대문자가 표준이다.

문자 범주는 unreserved와 reserved로 나뉘고, reserved는 다시 gen-delims와 sub-delims로 갈라진다.

```
unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
reserved    = gen-delims / sub-delims
gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
            / "*" / "+" / "," / ";" / "="
```

이 분류가 왜 중요하냐면, URL 컴포넌트마다 허용하는 문자 범주가 다르기 때문이다. gen-delims는 URL의 큰 구조(스킴, 호스트, 경로, 쿼리, 프래그먼트)를 나누고, sub-delims는 컴포넌트 안에서 의미를 갖는 구분자다. 예를 들어 쿼리 스트링의 `&`, `=`는 sub-delims에 속해서 쿼리 컴포넌트에서는 인코딩 없이 쓸 수 있지만, 파라미터 값으로 쓰려면 인코딩해야 한다.

| 범주 | 문자 | URL에서 역할 |
|------|------|--------------|
| unreserved | `A-Z a-z 0-9 - _ . ~` | 어디서든 그대로 사용 가능. 인코딩 금지(권장) |
| gen-delims | `: / ? # [ ] @` | URL 컴포넌트 구분자 |
| sub-delims | `! $ & ' ( ) * + , ; =` | 컴포넌트 내부 구분자 (쿼리·경로 세그먼트) |
| 그 외 | 공백·제어문자·non-ASCII | 반드시 percent-encoding |

```mermaid
flowchart TD
    A["RFC 3986 문자 집합"] --> B["unreserved<br/>(인코딩 금지 권장)"]
    A --> C["reserved"]
    C --> D["gen-delims<br/>: / ? # [ ] @"]
    C --> E["sub-delims<br/>! $ & ' ( ) * + , ; ="]
    A --> F["그 외 모든 문자<br/>(pct-encoded 필수)"]

    D --> G["URL 컴포넌트 경계"]
    E --> H["컴포넌트 내부 구분자"]

    style B fill:#e8f5e9,stroke:#2e7d32
    style D fill:#fff3e0,stroke:#e65100
    style E fill:#fff3e0,stroke:#e65100
    style F fill:#ffebee,stroke:#c62828
```

unreserved 문자를 인코딩한 URL은 동등한 것으로 간주해야 한다(RFC 3986 §6.2.2.2). 즉 `%41`은 `A`와 같다. 정규화 단계에서 unreserved의 pct-encoded는 원형으로 되돌리는 게 표준 동작이다. 캐시 키나 URL 비교 로직을 짤 때 이 규칙을 놓치면 같은 리소스인데 캐시 미스가 난다.


## URL 컴포넌트별 허용 문자 매트릭스

같은 `&`라도 쿼리 안에서는 구분자, 경로 안에서는 일반 문자로 쓸 수 있다. RFC 3986이 정의한 컴포넌트별 허용 문자를 정리하면 다음과 같다.

```
URI = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
hier-part = "//" authority path-abempty
authority = [ userinfo "@" ] host [ ":" port ]
```

| 컴포넌트 | 허용 문자 (ABNF 요약) | gen-delims 중 인코딩 필요 | 비고 |
|----------|----------------------|---------------------------|------|
| scheme | `ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )` | 모두 | 대소문자 무시, 첫 글자는 ALPHA |
| userinfo | unreserved / pct-encoded / sub-delims / `:` | `@ / ? #` 필수 | `:`로 user/password 분리 |
| host (reg-name) | unreserved / pct-encoded / sub-delims | `: / ? # [ ] @` | IPv6는 `[ ]` 사이 |
| path (segment) | unreserved / pct-encoded / sub-delims / `:` / `@` | `/ ? #` 필수 | `/`는 세그먼트 구분자 |
| query | unreserved / pct-encoded / sub-delims / `:` / `@` / `/` / `?` | `#` 필수 | `&`, `=`는 sub-delims라 허용되지만 값에 쓰려면 인코딩 |
| fragment | query와 동일 | 없음(맨 뒤) | `#` 자체는 시작 표시라 본문에 못 씀 |

실무에서 가장 헷갈리는 부분이 path와 query의 차이다.

- path 세그먼트에서 `:`와 `@`는 인코딩 없이 써도 되지만 `/`는 세그먼트를 갈라 버리니까 인코딩해야 한다.
- query에서 `/`, `?`는 그대로 써도 되고, 이 사실 덕분에 쿼리 값에 다른 URL을 넣을 수 있다. 단 `#`은 프래그먼트 시작이므로 반드시 `%23`로 인코딩한다.

```javascript
// 콜백 URL을 쿼리 파라미터로 넘기는 흔한 케이스
const callback = 'https://app.example.com/result?id=123';
const url = `https://auth.example.com/login?return=${encodeURIComponent(callback)}`;
// return=https%3A%2F%2Fapp.example.com%2Fresult%3Fid%3D123
```

이때 `encodeURI`를 쓰면 안 된다. 콜백 URL 안의 `?`와 `=`가 인코딩되지 않아서 외부 URL의 쿼리가 현재 URL의 쿼리에 섞여 들어간다.

userinfo 자리의 `:`도 흔한 함정이다. 비밀번호에 `:`이나 `@`가 들어가면 반드시 인코딩해야 호스트 파싱이 깨지지 않는다.

```
https://user:p@ss@example.com/  ← 호스트가 ss@example.com으로 해석될 수 있다
https://user:p%40ss@example.com/  ← 올바른 형태
```


## 한글은 어떻게 인코딩되는가

한글은 UTF-8로 인코딩하면 한 글자가 3바이트다. 퍼센트 인코딩은 바이트 단위로 처리하므로, 한글 한 글자가 `%XX%XX%XX` 형태로 변환된다.

```
"가" → UTF-8 바이트: 0xEA 0xB0 0x80 → %EA%B0%80
"서울" → %EC%84%9C%EC%9A%B8
```

아래 다이어그램은 한글 "가"가 퍼센트 인코딩되는 전체 흐름이다.

```mermaid
flowchart LR
    A["문자: 가"] --> B["UTF-8 변환"]
    B --> C["0xEA"]
    B --> D["0xB0"]
    B --> E["0x80"]
    C --> F["%EA"]
    D --> G["%B0"]
    E --> H["%80"]
    F --> I["%EA%B0%80"]
    G --> I
    H --> I

    style A fill:#f9f9f9,stroke:#333
    style I fill:#e8f5e9,stroke:#2e7d32
```

각 바이트 앞에 `%`를 붙여서 16진수로 표현하는 것이 퍼센트 인코딩의 전부다. 한글은 UTF-8에서 3바이트이므로 `%XX` 3개가 나온다. 영문 알파벳은 1바이트이므로 `%XX` 1개로 끝난다.

브라우저 주소창에 `https://example.com/검색?q=서울` 이라고 입력하면, 실제 요청은 이렇게 나간다.

```
GET /%EA%B2%80%EC%83%89?q=%EC%84%9C%EC%9A%B8 HTTP/1.1
```

브라우저 주소창에서는 사용자 편의를 위해 디코딩된 한글을 보여주지만, 실제 HTTP 요청에서는 퍼센트 인코딩된 형태로 전송된다.


## UTF-8 멀티바이트 구조와 percent-encoding의 길이

percent-encoding은 바이트 단위 처리라서 UTF-8 바이트 길이가 그대로 `%XX` 개수가 된다. UTF-8은 코드포인트 범위에 따라 1~4바이트로 가변 길이 인코딩한다.

| 코드포인트 범위 | 바이트 수 | 비트 레이아웃 | 예시 |
|-----------------|-----------|---------------|------|
| `U+0000 ~ U+007F` (ASCII) | 1 | `0xxxxxxx` | `A` → `0x41` → `%41` (그러나 unreserved라 인코딩 안 함) |
| `U+0080 ~ U+07FF` (라틴 확장, 그리스, 키릴 등) | 2 | `110xxxxx 10xxxxxx` | `é` → `0xC3 0xA9` → `%C3%A9` |
| `U+0800 ~ U+FFFF` (한글·한자·BMP 대부분) | 3 | `1110xxxx 10xxxxxx 10xxxxxx` | `가` → `0xEA 0xB0 0x80` → `%EA%B0%80` |
| `U+10000 ~ U+10FFFF` (이모지·고대 문자) | 4 | `11110xxx 10xxxxxx 10xxxxxx 10xxxxxx` | `😀` → `0xF0 0x9F 0x98 0x80` → `%F0%9F%98%80` |

리딩 바이트의 비트 패턴(`0`, `110`, `1110`, `11110`)으로 시퀀스 길이를 판단하고, 후속 바이트는 모두 `10`으로 시작한다. 이 자기 동기화(self-synchronizing) 구조 덕분에 어떤 바이트에서 디코딩을 시작해도 다음 문자 경계를 찾을 수 있다.

이모지는 거의 다 4바이트라서 한 문자가 `%XX%XX%XX%XX`로 12자가 된다. URL 길이 제한(보통 2048~8192바이트)을 잡을 때 이 점을 잊으면 안 된다. 이모지가 섞인 검색어를 GET으로 보내면 의외로 빠르게 한계에 닿는다.

### 이모지와 surrogate pair 처리

JavaScript 문자열은 UTF-16 기반이라서, BMP를 벗어난 코드포인트(U+10000 이상)는 surrogate pair 두 개로 저장된다. 이 차이가 percent-encoding 결과에는 영향을 안 주지만, 문자열 길이 계산이나 부분 추출에서 함정이 된다.

```javascript
const emoji = '😀';
emoji.length;                          // 2 (surrogate pair)
[...emoji].length;                     // 1 (실제 코드포인트 수)
emoji.codePointAt(0).toString(16);     // "1f600"

encodeURIComponent(emoji);             // "%F0%9F%98%80" (UTF-8 4바이트)
```

`encodeURIComponent`는 내부적으로 UTF-8 변환을 거치므로 surrogate pair를 정상적으로 4바이트로 묶어 인코딩한다. 다만 깨진 surrogate(예: high surrogate 단독)는 `URIError`를 던진다.

```javascript
encodeURIComponent('\uD83D');
// URIError: URI malformed
```

사용자 입력을 받아서 인코딩할 때, 깨진 문자열이 들어올 가능성이 있으면 try/catch로 감싸거나, 인코딩 전에 `\uD800-\uDFFF` 범위의 고아 surrogate를 제거·치환해 두는 게 안전하다.


## encodeURI vs encodeURIComponent

JavaScript에서 URL 인코딩을 다룰 때 이 두 함수의 차이를 혼동하면 버그가 생긴다.

### encodeURI

URL 전체를 인코딩할 때 쓴다. URL 구조를 유지해야 하므로 `:`, `/`, `?`, `#`, `&`, `=` 같은 예약 문자는 인코딩하지 않는다.

```javascript
encodeURI('https://example.com/path?q=서울&page=1')
// "https://example.com/path?q=%EC%84%9C%EC%9A%B8&page=1"
// ?, &, = 는 그대로 남아있다
```

### encodeURIComponent

쿼리 파라미터의 값처럼, URL의 일부분을 인코딩할 때 쓴다. 예약 문자까지 전부 인코딩한다.

```javascript
encodeURIComponent('서울&부산')
// "%EC%84%9C%EC%9A%B8%26%EB%B6%80%EC%82%B0"
// & 도 %26으로 인코딩된다
```

### 잘못 쓰면 생기는 문제

쿼리 파라미터 값에 `encodeURI`를 쓰면 값 안의 `&`가 파라미터 구분자로 해석된다.

```javascript
const query = 'A&B';

// 잘못된 방법
const bad = `https://example.com/search?q=${encodeURI(query)}`;
// "https://example.com/search?q=A&B"
// 서버는 q=A, B=(빈값) 두 개의 파라미터로 해석한다

// 올바른 방법
const good = `https://example.com/search?q=${encodeURIComponent(query)}`;
// "https://example.com/search?q=A%26B"
// 서버는 q=A&B 하나의 파라미터로 해석한다
```

URL 전체에 `encodeURIComponent`를 쓰면 `://`과 `/`까지 인코딩되어 URL 자체가 깨진다.

```javascript
encodeURIComponent('https://example.com/path')
// "https%3A%2F%2Fexample.com%2Fpath"
// URL로 사용할 수 없다
```

정리하면, URL 전체는 `encodeURI`, 파라미터 값은 `encodeURIComponent`를 쓴다.

### encodeURIComponent의 RFC 2396 호환성 구멍

`encodeURIComponent`는 RFC 2396 시절 스펙을 따른다. RFC 2396은 "mark" 문자라는 범주를 두고 `! * ' ( )`를 unreserved로 분류했는데, RFC 3986에서는 이들 중 일부가 sub-delims로 재분류됐다. ECMAScript 명세는 하위 호환성을 위해 옛 분류를 그대로 둬서, 다음 문자들은 `encodeURIComponent`로도 인코딩되지 않는다.

```javascript
encodeURIComponent("!*'()");  // "!*'()"  ← 그대로 통과
```

대부분의 경우 문제가 없지만, OAuth 1.0a 서명, AWS Signature v4 같은 엄격한 캐노니컬라이제이션 규약이나, `(` `)`를 자체 구분자로 쓰는 일부 검색 API에서는 이 문자들이 인코딩되어야 한다. 이럴 때 쓰는 패턴이 strictEncode다.

```javascript
function strictEncode(str) {
    return encodeURIComponent(str).replace(/[!*'()]/g, (c) =>
        '%' + c.charCodeAt(0).toString(16).toUpperCase()
    );
}

strictEncode("hello (world)!");
// "hello%20%28world%29%21"
```

RFC 3986에 완전히 맞춰서 인코딩해야 하는 시그니처 계산이나, 외부 시스템과의 정확한 호환이 필요한 자리에서 이 패턴을 쓴다. 반대로 브라우저에서 콜백 URL을 만들거나 일반 쿼리 파라미터를 만들 때는 표준 `encodeURIComponent`로 충분하다.


## URLSearchParams를 쓰면 직접 인코딩할 일이 줄어든다

직접 `encodeURIComponent`를 호출하는 대신 `URLSearchParams`를 쓰면 인코딩 실수를 줄일 수 있다.

```javascript
const params = new URLSearchParams();
params.set('q', '서울&부산');
params.set('page', '1');

console.log(params.toString());
// "q=%EC%84%9C%EC%9A%B8%26%EB%B6%80%EC%82%B0&page=1"

const url = `https://example.com/search?${params}`;
```

주의할 점이 하나 있다. `URLSearchParams`는 공백을 `%20`이 아니라 `+`로 인코딩한다. 이건 `application/x-www-form-urlencoded` 스펙을 따르기 때문이다.

```javascript
const params = new URLSearchParams({ q: 'hello world' });
params.toString(); // "q=hello+world"  (%20이 아니다)
```

대부분의 서버는 `+`와 `%20` 둘 다 공백으로 해석하지만, 일부 API에서 `+`를 리터럴 플러스로 처리하는 경우가 있다. 그런 API와 연동할 때는 `toString()` 결과에서 `+`를 `%20`으로 치환해야 한다.


## application/x-www-form-urlencoded vs RFC 3986

URL 인코딩 스펙이 두 개라는 사실은 실무 버그의 절반쯤을 만든다. 둘은 비슷해 보이지만 처리 규칙이 다르다.

| 항목 | RFC 3986 (URI) | WHATWG URL Standard / form-urlencoded |
|------|----------------|----------------------------------------|
| 공백 | `%20` | `+` (인코딩), `+` 또는 `%20` (디코딩 모두 허용) |
| `+` 리터럴 | 그대로 둬도 됨 | 반드시 `%2B`로 인코딩해야 공백과 구분됨 |
| unreserved 범위 | `A-Z a-z 0-9 - _ . ~` | `A-Z a-z 0-9 * - . _` (`~`는 인코딩됨) |
| 문자 집합 | 컴포넌트별로 다름 | 항상 UTF-8 가정 |
| 대상 | URL 전 영역 | HTML 폼 제출, `application/x-www-form-urlencoded` 본문, `URLSearchParams` |

스펙 차이가 만드는 실제 결과는 다음과 같다.

```javascript
encodeURIComponent('hello world');           // "hello%20world"
new URLSearchParams({a: 'hello world'}).toString();  // "a=hello+world"

encodeURIComponent('~');                     // "~"  (RFC 3986: unreserved)
new URLSearchParams({a: '~'}).toString();    // "a=~"  (WHATWG는 ~를 인코딩 대상에서 빼서 결과 동일)

encodeURIComponent('a+b');                   // "a%2Bb"
new URLSearchParams({a: 'a+b'}).toString();  // "a=a%2Bb"
```

WHATWG URL Standard는 RFC 3986을 대체하는 게 아니라, 브라우저 환경의 실제 동작을 명세화한 스펙이다. WHATWG는 컴포넌트별로 "encode set"을 정의한다.

- `C0 control percent-encode set`: 제어문자 + `%` (가장 좁은 집합)
- `fragment percent-encode set`: 위 + 공백, `"`, `<`, `>`, `` ` ``
- `query percent-encode set`: fragment + `#`
- `special-query percent-encode set`: query + `'` (http/https 같은 special scheme용)
- `path percent-encode set`: query + `?`, `` ` ``, `{`, `}`
- `userinfo percent-encode set`: path + `/`, `:`, `;`, `=`, `@`, `[`, `]`, `\`, `^`, `|`
- `component percent-encode set`: userinfo + `$`, `%`, `&`, `+`, `,`
- `application/x-www-form-urlencoded percent-encode set`: component + 모든 ASCII 영숫자가 아니거나 `*`, `-`, `.`, `_`가 아닌 문자

이 분류 때문에 같은 `:`도 path에서는 인코딩 안 하지만 form-urlencoded에서는 인코딩한다. JavaScript의 `new URL(...)` 생성자는 WHATWG 명세를 따르고, `encodeURI`/`encodeURIComponent`는 RFC 2396/3986 기반이다. 둘이 만나면 의도치 않은 결과가 나온다.

```javascript
const u = new URL('https://example.com/path');
u.searchParams.set('q', 'a b');
u.toString();
// "https://example.com/path?q=a+b"  ← URLSearchParams는 +

const u2 = new URL('https://example.com/path');
u2.search = '?q=' + encodeURIComponent('a b');
u2.toString();
// "https://example.com/path?q=a%20b"  ← encodeURIComponent는 %20
```

서버가 어떤 디코더를 쓰느냐에 따라 결과가 달라진다. 표준적인 폼 디코더(Express의 `body-parser`, Spring의 `@RequestParam`)는 둘 다 공백으로 받지만, 직접 만든 디코더나 정규식 기반 파서를 통과시키면 차이가 난다.

```mermaid
flowchart LR
    A["입력: 'a b'"] --> B{"인코딩 방식"}
    B -->|"RFC 3986<br/>encodeURIComponent"| C["a%20b"]
    B -->|"form-urlencoded<br/>URLSearchParams"| D["a+b"]
    C --> E["디코더"]
    D --> E
    E -->|"표준 폼 디코더"| F["'a b' (동일)"]
    E -->|"엄격한 URI 디코더"| G["+를 리터럴로 처리하면<br/>'a+b'로 남음"]

    style C fill:#e8f5e9,stroke:#2e7d32
    style D fill:#fff3e0,stroke:#e65100
    style G fill:#ffebee,stroke:#c62828
```


## + 와 %20 차이

공백을 인코딩하는 방식이 두 가지인 게 위에서 본 두 스펙의 결과다.

| 스펙 | 공백 표현 | 사용 위치 |
|------|-----------|-----------|
| RFC 3986 (URL) | `%20` | URL 경로, 프래그먼트 |
| application/x-www-form-urlencoded (HTML 폼) | `+` | 쿼리 스트링 (폼 전송 시) |

Java의 `URLEncoder.encode`는 폼 인코딩 스펙을 따르므로 공백을 `+`로 인코딩한다.

```java
URLEncoder.encode("hello world", StandardCharsets.UTF_8);
// "hello+world"
```

URL 경로에 쓸 값을 인코딩할 때 `URLEncoder`를 쓰면 `+`가 그대로 들어가서 문제가 된다. 경로에서는 `+`가 공백이 아니라 리터럴 플러스이기 때문이다.

```java
String value = URLEncoder.encode("hello world", StandardCharsets.UTF_8)
    .replace("+", "%20");
// "hello%20world"
```

Spring의 `UriUtils.encodePathSegment`를 쓰면 이런 처리를 알아서 해준다.

```java
UriUtils.encodePathSegment("hello world", StandardCharsets.UTF_8);
// "hello%20world"
```


## Spring에서의 URL 디코딩

### 자동 디코딩

Spring MVC는 요청이 들어오면 서블릿 컨테이너(Tomcat 등)가 URL을 자동으로 디코딩해서 넘겨준다. 컨트롤러에서 받는 값은 이미 디코딩된 상태다.

```java
// 요청: GET /search?q=%EC%84%9C%EC%9A%B8
@GetMapping("/search")
public String search(@RequestParam String q) {
    // q = "서울" (이미 디코딩된 상태)
    return q;
}
```

`@PathVariable`도 마찬가지다.

```java
// 요청: GET /cities/%EC%84%9C%EC%9A%B8
@GetMapping("/cities/{name}")
public String city(@PathVariable String name) {
    // name = "서울"
    return name;
}
```

### 수동으로 디코딩해야 하는 경우

쿠키 값이나 헤더 값은 자동 디코딩 대상이 아니다. 직접 디코딩해야 한다.

```java
String raw = request.getHeader("X-Custom-Value");
String decoded = URLDecoder.decode(raw, StandardCharsets.UTF_8);
```

`URLDecoder.decode`에 charset을 지정하지 않으면 플랫폼 기본 인코딩을 쓰는데, 운영 환경에 따라 달라질 수 있으므로 반드시 `UTF_8`을 명시한다.


## Express(Node.js)에서의 URL 디코딩

Express도 쿼리 파라미터와 경로 파라미터를 자동으로 디코딩해서 넘겨준다.

```javascript
// 요청: GET /search?q=%EC%84%9C%EC%9A%B8
app.get('/search', (req, res) => {
    console.log(req.query.q); // "서울"
});

// 요청: GET /cities/%EC%84%9C%EC%9A%B8
app.get('/cities/:name', (req, res) => {
    console.log(req.params.name); // "서울"
});
```

`req.path`도 디코딩된 값이지만, `req.originalUrl`은 디코딩 전 원본 URL이다.

```javascript
// 요청: GET /cities/%EC%84%9C%EC%9A%B8
app.get('/cities/:name', (req, res) => {
    console.log(req.path);        // "/cities/서울"
    console.log(req.originalUrl); // "/cities/%EC%84%9C%EC%9A%B8"
});
```


## 이중 인코딩 문제

실무에서 가장 흔하게 겪는 인코딩 버그다. 이미 인코딩된 문자열을 한 번 더 인코딩하면 `%`가 `%25`로 변환되면서 원본 복원이 안 된다.

```
원본: 서울
1차 인코딩: %EC%84%9C%EC%9A%B8
2차 인코딩: %25EC%2584%259C%25EC%259A%25B8  (% → %25)
```

아래 흐름도로 보면 이중 인코딩이 왜 문제인지 한눈에 보인다.

```mermaid
flowchart TD
    A["원본: 서울"] -->|"1차 인코딩"| B["%EC%84%9C%EC%9A%B8"]
    B -->|"2차 인코딩 (% → %25)"| C["%25EC%2584%259C%25EC%259A%25B8"]
    C -->|"서버 디코딩 (1회)"| D["%EC%84%9C%EC%9A%B8 ← 문자열 그대로"]
    D -.->|"한글 복원 안 됨"| E["서울 ✗"]

    B -->|"정상 경로: 서버 디코딩"| F["서울 ← 정상 복원"]

    style A fill:#f9f9f9,stroke:#333
    style C fill:#ffebee,stroke:#c62828
    style D fill:#fff3e0,stroke:#e65100
    style F fill:#e8f5e9,stroke:#2e7d32
```

서버는 보통 디코딩을 한 번만 수행한다. 이중 인코딩된 값은 1회 디코딩 후에도 퍼센트 인코딩 문자열이 남아서, 원본 한글로 돌아오지 않는다.

### 자주 발생하는 상황

**1. 프론트엔드에서 인코딩하고, HTTP 클라이언트가 다시 인코딩하는 경우**

```javascript
// 프론트엔드
const keyword = encodeURIComponent('서울');
// keyword = "%EC%84%9C%EC%9A%B8"

// axios는 파라미터를 자동으로 인코딩한다
axios.get('/search', { params: { q: keyword } });
// 실제 요청: /search?q=%25EC%2584%259C%25EC%259A%25B8
// 이중 인코딩 발생
```

axios, fetch, RestTemplate 같은 HTTP 클라이언트는 파라미터를 자동 인코딩한다. 직접 인코딩한 값을 파라미터로 넣으면 이중 인코딩이 된다.

```javascript
// 올바른 방법: 원본 문자열을 넣고 클라이언트에 맡긴다
axios.get('/search', { params: { q: '서울' } });
```

**2. Spring의 RestTemplate에서 발생하는 경우**

```java
// 이중 인코딩 발생
String encoded = URLEncoder.encode("서울", StandardCharsets.UTF_8);
String url = "https://api.example.com/search?q=" + encoded;
restTemplate.getForObject(url, String.class);
// RestTemplate이 URL을 다시 인코딩한다

// 해결 방법 1: UriComponentsBuilder 사용
URI uri = UriComponentsBuilder
    .fromHttpUrl("https://api.example.com/search")
    .queryParam("q", "서울")  // 원본 문자열
    .build()
    .encode()
    .toUri();
restTemplate.getForObject(uri, String.class);

// 해결 방법 2: 이미 인코딩된 URL은 URI 객체로 감싸서 재인코딩 방지
URI uri = URI.create("https://api.example.com/search?q=" + encoded);
restTemplate.getForObject(uri, String.class);
```

**3. 리다이렉트 체인에서 발생하는 경우**

서비스 A → 서비스 B → 서비스 C로 리다이렉트되면서, 각 서비스가 URL 파라미터를 인코딩하면 단계마다 `%25`가 누적된다. 리다이렉트 URL을 만들 때는 이미 인코딩된 파라미터를 다시 인코딩하지 않도록 주의해야 한다.

### 이중 인코딩 디버깅

URL에 `%25`가 보이면 이중 인코딩을 의심한다.

```
정상: q=%EC%84%9C%EC%9A%B8
이중 인코딩: q=%25EC%2584%259C%25EC%259A%25B8
```

서버 로그에서 파라미터 값이 `%EC%84%9C%EC%9A%B8` 같은 문자열로 찍히면(한글로 안 나오면), 어딘가에서 이중 인코딩이 일어나고 있는 것이다.


## 언어별 표준 라이브러리 동작 차이

같은 입력을 줘도 언어마다, 같은 언어 안에서도 함수마다 결과가 다르다. 외부 시스템과 시그니처를 맞춰야 할 때는 이 차이를 외워둬야 한다.

| 함수 | 공백 | `+` 입력 | `/` 입력 | mark 문자 `( ) ! *` | unreserved `~` | 비고 |
|------|------|---------|---------|---------------------|----------------|------|
| JS `encodeURI` | `%20` | `+` | `/` | 그대로 | 그대로 | URL 전체용 |
| JS `encodeURIComponent` | `%20` | `%2B` | `%2F` | 그대로 | 그대로 | RFC 2396 기반 |
| JS `URLSearchParams.toString` | `+` | `%2B` | `%2F` | 그대로 | 그대로 | WHATWG form |
| Java `URLEncoder.encode` | `+` | `%2B` | `%2F` | 그대로(`*` 제외) | 그대로 | form-urlencoded |
| Java `URI` 생성자 | 인코딩 안 함 | 그대로 | 그대로 | 그대로 | 그대로 | 멀티 인자 생성자만 인코딩 |
| Java `UriUtils.encodePathSegment` | `%20` | `%2B` | `%2F` | 그대로 | 그대로 | RFC 3986 |
| Java `UriUtils.encodeQueryParam` | `%20` | `%2B` | `/` | 그대로 | 그대로 | RFC 3986 query |
| Python `urllib.parse.quote` | `%20` | `%2B` | `/` (기본) | `%XX` | 그대로 | `safe='/'` 기본값 |
| Python `urllib.parse.quote_plus` | `+` | `%2B` | `%2F` | `%XX` | 그대로 | form 호환 |
| Python `urllib.parse.urlencode` | `+` | `%2B` | `%2F` | `%XX` | 그대로 | quote_plus 사용 |
| Go `net/url.QueryEscape` | `+` | `%2B` | `%2F` | `%XX` (`*` 제외) | 그대로 | form 호환 |
| Go `net/url.PathEscape` | `%20` | `%2B` | `%2F` | `%XX` (`*` 제외) | 그대로 | 경로 세그먼트용 |

함수 선택 기준을 한 줄로 정리하면 이렇다.

- 경로 세그먼트: Python `quote`, Java `UriUtils.encodePathSegment`, Go `PathEscape`, JS `encodeURIComponent`
- 쿼리 값(폼 호환): Python `quote_plus`, Java `URLEncoder`, Go `QueryEscape`, JS `URLSearchParams`
- 쿼리 값(엄격 RFC 3986): Python `quote(s, safe='')`, Java `UriUtils.encodeQueryParam`, JS `encodeURIComponent`

Java의 `URI` 클래스는 헷갈리는 부분이 많다. 단일 문자열 생성자(`new URI(uriString)`)는 인코딩을 안 하고 검증만 한다. 다중 인자 생성자(`new URI(scheme, userInfo, host, port, path, query, fragment)`)는 컴포넌트별로 알아서 인코딩한다. 인코딩 의도가 있을 때는 후자나 `UriComponentsBuilder`를 써야 한다.

Python의 `quote`는 `safe` 파라미터가 기본 `/`라서 슬래시가 인코딩되지 않는다. 한 글자 검색어에 `/`가 들어가면 의도와 다르게 동작하니까, 쿼리 값에 쓸 때는 `quote(s, safe='')`로 명시한다.

Go의 `QueryEscape`와 `PathEscape`는 결과가 미묘하게 다르다. 같은 입력 `a b/c`를 줘도 `QueryEscape`는 `a+b%2Fc`, `PathEscape`는 `a%20b%2Fc`다. 경로에 쓸 값을 `QueryEscape`로 만들면 `+`가 문제가 된다.


## 게이트웨이·프록시 계층의 디코딩 함정

요청이 클라이언트에서 애플리케이션까지 도달하는 동안 보통 두세 번 이상 파싱·정규화를 거친다. 각 계층의 디코딩 정책이 다르면 같은 URL이 계층마다 다르게 해석된다.

```mermaid
sequenceDiagram
    participant C as Client
    participant N as nginx
    participant A as ALB
    participant S as Spring Boot

    C->>N: GET /api/file%2Fname?q=a%20b
    Note over N: location 매칭, $uri는 디코딩됨<br/>$request_uri는 원본
    N->>A: GET /api/file%2Fname?q=a%20b<br/>(proxy_pass 형태에 따라 다름)
    Note over A: 헬스체크 외엔 보통 원본 전달<br/>일부 룰에서 디코딩 후 매칭
    A->>S: GET /api/file%2Fname?q=a%20b
    Note over S: Tomcat이 디코딩<br/>@PathVariable: "file/name"
```

### nginx

nginx는 `$uri`와 `$request_uri` 변수를 구분해서 쓴다.

- `$request_uri`: 원본 URL(인코딩 포함)
- `$uri`: 디코딩되고 정규화된 경로

`proxy_pass`의 동작이 URI 끝에 슬래시가 붙냐 안 붙냐로 갈리는 게 함정이다.

```nginx
# 1. proxy_pass에 URI가 없는 경우 → $request_uri 그대로 전달
location /api/ {
    proxy_pass http://backend;
    # 클라이언트가 /api/file%2Fname 보내면 백엔드에 /api/file%2Fname 그대로 전달
}

# 2. proxy_pass에 URI가 있는 경우 → 매칭된 부분이 디코딩되어 치환
location /api/ {
    proxy_pass http://backend/v2/;
    # 클라이언트가 /api/file%2Fname 보내면 백엔드에 /v2/file/name 으로 전달
    # %2F가 /로 디코딩되어 경로 의미가 바뀜
}
```

이 차이로 인해 경로 세그먼트에 인코딩된 `/`가 포함된 URL이 nginx를 거치면서 일반 슬래시로 펴지는 사고가 발생한다. 슬래시를 보존해야 하면 `proxy_pass`에 URI를 두지 말거나, 명시적으로 `rewrite ... break;`로 원본을 전달한다.

또 한 가지, nginx 기본 설정은 `merge_slashes on`이라서 연속된 슬래시(`//`)를 하나로 합친다. 일부 라우팅이 빈 세그먼트에 의미를 두는 경우 이걸 꺼야 한다.

### AWS ALB

ALB는 기본적으로 경로의 percent-encoding을 보존해서 백엔드에 전달한다. 하지만 라우팅 룰(Listener Rule)의 path-pattern은 디코딩 후 매칭 동작에 가깝다. 따라서 `/api/file%2Fname`이 `/api/file/name`으로 매칭되는 일이 일어난다. WAF 룰을 짤 때 이걸 모르면 인코딩 우회 공격에 뚫린다.

ALB는 또 RFC에서 허용하지 않는 일부 문자를 거부한다. 예전에는 URL에 `{`, `}`, `|` 같은 문자가 raw로 들어오면 400을 던졌고, 지금도 attribute 설정에 따라 동작이 달라진다. 이런 문자를 받아야 한다면 클라이언트에서 인코딩하든지, 라우팅 룰을 우회하든지 한다.

### X-Forwarded-* 헤더의 인코딩 함정

프록시 계층이 원본 정보를 보존하려고 추가하는 헤더(`X-Forwarded-For`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Uri`)는 HTTP 헤더 값 규칙(RFC 7230)을 따른다. 헤더 값은 ASCII 가시 문자와 공백, 탭만 허용하므로 한글 같은 non-ASCII는 percent-encoding한 상태로 넣어야 한다.

대부분의 프록시는 원본 URL을 그대로 베껴서 넣지만, 일부 게이트웨이는 `X-Forwarded-Uri`에 디코딩된 경로를 넣는다. 그러면 백엔드가 이 헤더를 신뢰해서 redirect URL을 만들 때 다시 인코딩하지 않으면 `%2F`가 `/`로 펴진 채로 위치 헤더가 나간다.

```java
// 위험한 패턴: 헤더를 그대로 신뢰
String forwardedUri = request.getHeader("X-Forwarded-Uri");
// forwardedUri = "/files/report (1).pdf"  ← 이미 디코딩됨
response.setHeader("Location", baseUrl + forwardedUri);
// Location: https://example.com/files/report (1).pdf
// 공백, 괄호가 raw로 들어가서 클라이언트가 잘못 해석
```

`X-Forwarded-*` 헤더는 원본 인코딩 상태가 보장되지 않으므로, 헤더 값을 그대로 응답에 쓰지 말고 컴포넌트별로 다시 인코딩한다. Spring `UriComponentsBuilder.fromHttpUrl(...).path(decodedPath).encode().build()` 같은 형태로 한 번 검증·재인코딩을 거쳐야 안전하다.

또 한 가지 흔한 함정은 `Host` 헤더에 IDN(국제화 도메인)이 들어오는 경우다. 대부분의 클라이언트는 IDN을 punycode로 변환해서 보내지만, 일부 환경에서 UTF-8 호스트가 그대로 들어오면 라우팅 미스가 발생한다.


## IRI와 punycode: URL과 다른 인코딩 영역

URL은 ASCII 기반이라서 한글 도메인이나 한글 경로를 그대로 못 담는다. 이걸 풀려고 두 개의 별도 스펙이 있다.

### IRI (RFC 3987)

IRI(Internationalized Resource Identifier)는 URL의 확장 형태로, 경로·쿼리·프래그먼트에 유니코드 문자를 직접 허용한다. 브라우저 주소창에서 한글 URL을 보여줄 때, 실제로는 IRI를 사용자에게 표시하고 내부적으로 URI로 변환해서 전송한다.

```
IRI:  https://example.com/검색?q=서울
URI:  https://example.com/%EA%B2%80%EC%83%89?q=%EC%84%9C%EC%9A%B8
```

IRI → URI 변환은 RFC 3987 §3.1에 정의되어 있고, 다음 순서로 진행된다.

1. IRI의 호스트 부분만 따로 떼서 punycode 변환
2. 나머지 경로·쿼리·프래그먼트의 non-ASCII 문자를 UTF-8 바이트로 변환 후 percent-encoding
3. 결과를 합쳐서 ASCII URI 생성

호스트 부분과 경로·쿼리는 서로 다른 변환 알고리즘을 쓴다는 점이 핵심이다. 호스트는 percent-encoding을 못 쓰고, 경로·쿼리는 punycode를 못 쓴다.

### punycode (RFC 3492)와 IDNA

도메인 이름은 DNS 프로토콜 제약 때문에 ASCII만 허용한다(LDH 규칙: Letter, Digit, Hyphen). 그래서 한글 도메인은 punycode라는 별도 알고리즘으로 ASCII로 변환된다.

```
한글 도메인: 한글.kr
IDNA 변환: xn--bj0bj06e.kr
```

`xn--` 접두사가 punycode 라벨이라는 표시다. 변환 알고리즘은 ASCII 문자만 먼저 출력하고, 나머지 코드포인트들을 어디에 끼워넣을지를 압축 인코딩하는 방식이다. percent-encoding과는 완전히 다른 알고리즘이다.

| 측면 | percent-encoding | punycode |
|------|------------------|----------|
| 대상 | URL의 경로·쿼리·프래그먼트 | 도메인 호스트 |
| 변환 단위 | UTF-8 바이트 단위 | 유니코드 코드포인트 |
| 결과 길이 | non-ASCII 1문자당 3~12자 | 보통 더 짧음 (Bootstring 압축) |
| 가역성 | 1:1 (UTF-8 확정) | 1:1 (IDNA 정규화 후) |
| 표시 형태 | `%EC%84%9C` | `xn--bj0bj06e` |

브라우저는 보안상 호모그래프 공격을 막으려고 punycode를 그대로 보여주기도 한다. 예를 들어 `apple.com`처럼 보이지만 일부 글자가 키릴 문자인 도메인은 주소창에 `xn--...` 형태로 표시된다.

IDN을 다뤄야 하면 언어별 표준 라이브러리가 있다.

- Java: `java.net.IDN.toASCII("한글.kr")` → `"xn--bj0bj06e.kr"`
- Python: `"한글.kr".encode("idna").decode()`
- Node.js: `require('url').domainToASCII("한글.kr")` 또는 `new URL("https://한글.kr/").hostname`

직접 만든 URL 파서로 도메인을 자르고 percent-encoding을 시도하면, 호스트 부분이 `%EA%B0%80%EB%82%98.kr` 같은 형태가 되어 DNS 조회가 실패한다. 호스트는 무조건 IDN 라이브러리를 거쳐야 한다.


## 파일 업로드 시 파일명 인코딩

`Content-Disposition` 헤더에 한글 파일명을 넣을 때도 인코딩 문제가 발생한다. HTTP 헤더 값은 ASCII만 허용하므로, RFC 5987이 정의한 확장 파라미터 문법을 써야 한다.

```java
@GetMapping("/download")
public ResponseEntity<Resource> download() {
    String filename = "보고서.pdf";
    String encoded = UriUtils.encode(filename, StandardCharsets.UTF_8);

    return ResponseEntity.ok()
        .header(HttpHeaders.CONTENT_DISPOSITION,
            "attachment; filename*=UTF-8''" + encoded)
        .body(resource);
}
```

`filename*=UTF-8''`은 RFC 5987 규격이다. 형식은 `charset'language'percent-encoded-value`로, language는 비워둘 수 있다. 오래된 브라우저는 이 형식을 못 읽을 수 있어서, `filename`과 `filename*`을 같이 보내는 게 안전하다.

```
Content-Disposition: attachment; filename="report.pdf"; filename*=UTF-8''%EB%B3%B4%EA%B3%A0%EC%84%9C.pdf
```

RFC 5987에서 허용하는 문자 집합은 RFC 3986의 unreserved에 일부 sub-delims(`! # $ & + - . ^ _ ` | ~`)를 더한 형태다. 따옴표나 공백, `*` 같은 문자는 반드시 percent-encoding해야 한다. `UriUtils.encode`는 이 규격에 맞춰 인코딩하므로 직접 알고리즘을 짤 필요는 없다.
