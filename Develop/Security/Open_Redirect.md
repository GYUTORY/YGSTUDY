---
title: Open Redirect (오픈 리다이렉트)
tags: [security, open-redirect, oauth, redirect-uri, url-parsing, phishing]
updated: 2026-06-15
---

# Open Redirect (오픈 리다이렉트)

로그인 후 원래 보던 페이지로 돌려보내는 기능을 만들다 보면 `?returnUrl=/mypage` 같은 파라미터를 쓰게 된다. 이 값을 그대로 `Location` 헤더에 넣어 리다이렉트하면, 공격자가 `?returnUrl=https://evil.com`을 끼워넣어 사용자를 외부 사이트로 보내버린다. 이게 오픈 리다이렉트다.

서버가 직접 데이터를 유출하거나 코드를 실행하는 게 아니라서 "이게 무슨 취약점이냐"고 넘기는 경우가 많은데, 실제 피해는 피싱에서 나온다. 메일에 `https://정상도메인.com/login?next=https://evil.com`처럼 도메인 앞부분이 진짜 서비스 주소라 사용자도, 메일 필터도 의심하지 않는다. 로그인 직후 가짜 로그인 페이지로 튕기면 자격 증명이 그대로 넘어간다. OAuth 흐름에 끼면 인가 코드나 토큰까지 탈취 대상이 된다.

## 어디서 터지나

리다이렉트 대상이 되는 값을 외부 입력에서 받아오는 곳이 전부 후보다.

- 로그인 후 복귀: `returnUrl`, `next`, `redirect`, `returnTo`, `continue`, `dest`, `url`
- OAuth/OIDC: `redirect_uri`, SAML의 `RelayState`
- 결제·외부 연동 완료 후 콜백 복귀 주소
- 단축 URL, 트래킹 리다이렉트 (`/r?u=...`)

공통점은 "사용자가 준 주소로 보낸다"는 것. 그 주소를 검증하지 않으면 전부 뚫린다.

## 가장 흔한 취약 코드

Spring 기준으로 보면 이런 코드가 제일 많다.

```java
@GetMapping("/login/success")
public String loginSuccess(@RequestParam(defaultValue = "/") String returnUrl) {
    // returnUrl을 그대로 신뢰
    return "redirect:" + returnUrl;
}
```

`returnUrl=https://evil.com`이면 `redirect:https://evil.com`이 되어 외부로 나간다. Node/Express도 똑같다.

```javascript
app.get('/login/success', (req, res) => {
  const next = req.query.next || '/';
  res.redirect(next); // next가 절대 URL이면 외부로 나감
});
```

"내부 경로만 받으니까 괜찮겠지"라고 생각하고 `/`로 시작하는지만 보는 경우가 있는데, 이게 두 번째로 흔한 함정이다.

```javascript
// 취약: '/'로 시작하면 통과시킴
if (next.startsWith('/')) {
  res.redirect(next);
}
```

`//evil.com`은 `/`로 시작한다. 브라우저는 `//evil.com`을 프로토콜 상대 URL(protocol-relative URL)로 해석해서 `https://evil.com`으로 간다. `startsWith('/')` 검사는 여기서 무력화된다.

## 우회 패턴

검증을 넣었다고 해도 URL 파싱의 허점 때문에 뚫리는 경우가 많다. 자주 쓰이는 우회를 정리한다.

### 프로토콜 상대 URL

```
//evil.com
//evil.com/path
/\/evil.com      (역슬래시 섞기)
\/\/evil.com
```

`//`로 시작하면 호스트가 바뀐다. 일부 브라우저는 `/\`나 `\/`를 `//`와 동일하게 처리한다. 그래서 `startsWith('/')`만으로는 안 되고, `startsWith('//')`와 `startsWith('/\\')`까지 막아야 한다.

### 백슬래시 혼동

브라우저와 서버 측 URL 파서가 백슬래시를 다르게 본다. 서버는 `https:\\evil.com`을 정상 URL로 안 보고 통과시키는데, 브라우저는 `\`를 `/`로 바꿔 `https://evil.com`으로 간다.

```
https:/\evil.com
https:\/\/evil.com
http:\\\\evil.com
```

WHATWG URL 표준은 특수 스킴(http, https 등)에서 백슬래시를 슬래시로 정규화하라고 정해놨다. 그래서 브라우저는 `\`를 `/`처럼 처리한다. 서버 검증 로직이 이 정규화를 안 하면 둘 사이 틈이 생긴다.

### @ 를 이용한 호스트 위조

URL의 `user:password@host` 형식을 악용한다.

```
https://정상도메인.com@evil.com
https://정상도메인.com.evil.com
```

첫 번째는 `정상도메인.com`이 userinfo이고 실제 호스트는 `evil.com`이다. 문자열 매칭으로 "정상도메인.com이 들어있나"만 보면 통과한다. 두 번째는 `evil.com`의 서브도메인일 뿐이다.

### 화이트리스트 부분 매칭 우회

허용 도메인을 `contains`나 `startsWith`로 비교하면 이렇게 우회된다.

```
// 허용: example.com
example.com.evil.com      → startsWith나 contains 통과
evil.com/example.com      → contains 'example.com' 통과
evilexample.com           → contains 'example.com' 통과
example.com.evil.com:80   → 포트 섞기
```

호스트 비교는 반드시 파싱한 호스트와 정확히 일치(`equals`)하거나, 점(`.`)을 포함한 접미사 검사여야 한다. `host.equals("example.com") || host.endsWith(".example.com")` 형태가 맞다. `.`을 빼고 `endsWith("example.com")`만 쓰면 `evilexample.com`이 통과한다.

### 인코딩·제어문자

```
/%2F%2Fevil.com         (// 를 URL 인코딩)
/%09/evil.com           (탭 문자)
/%0d%0a                 (CRLF — 헤더 인젝션으로 번지기도 함)
https://evil.com%00.example.com   (널바이트로 파서 절단)
```

디코딩 시점과 검증 시점이 어긋나면 뚫린다. 검증 전에 한 번 디코딩해놓고, 디코딩된 값으로 검사해야 한다.

## OAuth redirect_uri 악용

OAuth에서 `redirect_uri`는 인가 코드나 토큰이 최종적으로 도착하는 주소다. 여기가 오픈 리다이렉트면 자격 증명이 그대로 넘어간다.

```
https://auth.example.com/authorize
  ?client_id=app123
  &redirect_uri=https://evil.com/callback   ← 등록 안 된 주소
  &response_type=code
```

인가 서버가 `redirect_uri`를 사전 등록된 값과 정확히 비교하지 않으면, 공격자가 자기 주소를 넣어 인가 코드를 가로챈다. RFC 6749와 OAuth 2.0 Security BCP는 `redirect_uri`를 부분 매칭이 아니라 정확한 문자열 일치(exact match)로 검증하라고 못박는다.

자주 나오는 실수:

- 등록값을 `https://app.example.com`으로 받고, 들어온 값이 그걸로 시작하는지만 검사 → `https://app.example.com.evil.com` 통과
- 경로 와일드카드 허용 → `https://app.example.com/callback/../../evil` 같은 경로 조작
- 서브도메인 와일드카드(`https://*.example.com`) 등록 → 서브도메인 하나만 탈취되면 토큰 전부 샌다
- 오픈 리다이렉트가 있는 정상 페이지를 `redirect_uri`로 등록 → 인가 서버는 통과시키지만, 그 페이지가 다시 `evil.com`으로 토큰을 넘김 (체이닝)

마지막 케이스가 까다롭다. `redirect_uri` 검증을 정확히 했어도, 등록된 그 주소 자체에 오픈 리다이렉트가 있으면 거기서 토큰이 샌다. 그래서 OAuth를 쓰는 서비스는 콜백 경로뿐 아니라 사이트 전체에서 오픈 리다이렉트를 없애야 한다.

```
[정상 흐름]
인가서버 → redirect_uri(등록됨, code 포함) → 앱 콜백 → 토큰 교환

[체이닝 공격]
인가서버 → redirect_uri(등록된 페이지지만 오픈 리다이렉트 있음)
        → 그 페이지가 ?next=evil.com 으로 다시 리다이렉트
        → code/token이 evil.com 으로 유출
```

## 허용 목록 기반 검증

근본 해법은 두 가지다. 우선순위 순으로 적는다.

### 1. 외부 입력으로 절대 URL을 받지 않는다

제일 안전한 건 리다이렉트 대상을 외부에서 절대 URL로 받지 않는 것이다. 페이지 키만 받고 서버가 실제 경로를 매핑한다.

```java
private static final Map<String, String> REDIRECT_TARGETS = Map.of(
    "mypage", "/user/mypage",
    "orders", "/user/orders",
    "home",   "/"
);

@GetMapping("/login/success")
public String loginSuccess(@RequestParam(defaultValue = "home") String dest) {
    String path = REDIRECT_TARGETS.getOrDefault(dest, "/");
    return "redirect:" + path;
}
```

키가 목록에 없으면 기본 경로로 보낸다. 외부 도메인이 끼어들 여지가 아예 없다. 리다이렉트 종류가 많지 않다면 이게 제일 깔끔하다.

### 2. 상대 경로만 허용한다

복귀 경로가 동적이라 1번이 안 되면, 상대 경로만 받고 절대 URL은 전부 거른다.

```java
public String safeRedirectPath(String returnUrl) {
    if (returnUrl == null || returnUrl.isBlank()) {
        return "/";
    }
    // 스킴이나 호스트가 들어있으면 거부
    // '/'로 시작하되 '//' 또는 '/\'로 시작하면 안 됨
    if (!returnUrl.startsWith("/")
            || returnUrl.startsWith("//")
            || returnUrl.startsWith("/\\")) {
        return "/";
    }
    // 백슬래시 자체를 막아 브라우저 정규화 우회 차단
    if (returnUrl.contains("\\")) {
        return "/";
    }
    // 디코딩 후 재검사 (인코딩 우회 차단)
    String decoded = URLDecoder.decode(returnUrl, StandardCharsets.UTF_8);
    if (decoded.startsWith("//") || decoded.startsWith("/\\") || decoded.contains("\\")) {
        return "/";
    }
    return returnUrl;
}
```

핵심은 `/`로 시작하는지만 보지 말고, `//`·`/\`·백슬래시·인코딩 우회까지 같이 막는 것. 디코딩한 값으로 한 번 더 검사하는 게 빠지면 인코딩 우회로 뚫린다.

### 3. 절대 URL이 꼭 필요하면 호스트를 정확히 비교한다

외부 도메인 리다이렉트가 업무상 필요하면(결제사 콜백 등), 호스트를 파싱해서 허용 목록과 정확히 비교한다. 문자열 매칭은 절대 안 된다.

```java
private static final Set<String> ALLOWED_HOSTS = Set.of(
    "example.com",
    "pay.example.com"
);

public boolean isAllowedRedirect(String target) {
    URI uri;
    try {
        uri = new URI(target);
    } catch (URISyntaxException e) {
        return false; // 파싱 실패 = 거부
    }

    String host = uri.getHost();
    if (host == null) {
        return false; // 호스트가 안 잡히면 거부 (//evil.com 등은 여기서 걸림)
    }

    String scheme = uri.getScheme();
    if (!"https".equalsIgnoreCase(scheme)) {
        return false; // https만 허용
    }

    // 정확히 일치하는 호스트만 통과
    return ALLOWED_HOSTS.contains(host.toLowerCase());
}
```

`uri.getHost()`가 `null`을 돌려주는 경우를 반드시 거부 처리해야 한다. `//evil.com`이나 `/path` 같은 입력은 호스트가 안 잡혀 `null`이 나오는데, 이걸 통과시키면 다시 뚫린다.

## URL 파싱 주의사항

검증 로직에서 가장 많이 실수하는 부분이 파서 동작이다.

`java.net.URI`와 `java.net.URL`은 동작이 다르다. `URL`은 `getHost()`가 더 관대하게 파싱해서 우회 여지가 생긴다. 검증에는 `URI`를 쓰고, 파싱 실패 예외를 거부로 처리한다.

```java
// URI: //evil.com → host=evil.com, scheme=null  (스킴 체크에서 걸림)
// URL: 생성자에서 스킴 없으면 MalformedURLException
new URI("//evil.com").getHost();   // "evil.com"
new URI("/local/path").getHost();  // null
new URI("https://a.com@evil.com").getHost(); // "evil.com" — @ 뒤가 진짜 호스트
```

마지막 줄이 중요하다. `@`가 있으면 그 뒤가 실제 호스트다. 표준 파서는 이걸 제대로 잡아주는데, 직접 정규식으로 호스트를 뽑으면 `@` 앞을 호스트로 착각하기 쉽다. 호스트 추출은 정규식 말고 표준 URL 파서를 써야 한다.

Node.js는 `URL` 객체를 쓴다. 똑같이 `hostname`을 정확 비교한다.

```javascript
function isAllowedRedirect(target) {
  let url;
  try {
    url = new URL(target);
  } catch {
    return false; // 상대 경로는 base 없이 파싱 실패 → 별도 처리
  }
  if (url.protocol !== 'https:') return false;
  const allowed = new Set(['example.com', 'pay.example.com']);
  return allowed.has(url.hostname.toLowerCase());
}
```

`new URL(target)`은 상대 경로(`/mypage`)를 base 없이 파싱하면 던진다. 상대 경로 허용 로직은 이 함수와 분리해서 처리한다. `new URL('//evil.com', 'https://example.com')`처럼 base를 주면 `//evil.com`이 `https://evil.com`으로 해석되니, base를 붙여 파싱할 때는 결과 호스트를 꼭 다시 확인한다.

호스트 정규화도 신경 써야 한다. `Example.COM`, `example.com.`(끝에 점), 퓨니코드(`xn--...`)·유니코드 도메인이 섞여 들어온다. 소문자 변환은 기본이고, 끝점 제거, 필요하면 퓨니코드 변환까지 맞춘 뒤 비교한다. 들어온 값과 허용 목록을 같은 정규화 단계를 거쳐 비교해야 틈이 안 생긴다.

## 정리

- `returnUrl`/`next`류는 가능하면 절대 URL을 받지 말고 페이지 키나 상대 경로만 받는다.
- `/`로 시작하는지만 보는 검사는 `//evil.com`에 뚫린다. `//`·`/\`·백슬래시·인코딩 우회를 같이 막는다.
- 호스트 비교는 문자열 `contains`/`startsWith`가 아니라 파싱한 호스트의 정확 일치(또는 `.도메인` 접미사)로 한다.
- 호스트 추출은 정규식이 아니라 표준 URL 파서(`URI`, `URL`)를 쓰고, 호스트가 `null`이면 거부한다.
- OAuth `redirect_uri`는 사전 등록값과 정확히 일치 비교한다. 부분 매칭·와일드카드는 금물이고, 등록한 콜백 페이지 자체에 오픈 리다이렉트가 없는지도 확인한다.
