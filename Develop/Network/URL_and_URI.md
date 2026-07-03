---
title: URL과 URI의 차이 - 구조, 인코딩, 실무 활용
tags: [network, url, uri, urn, rfc3986, http, web]
updated: 2026-04-28
---

# URL과 URI의 차이 - 구조, 인코딩, 실무 활용

5년 정도 백엔드를 짜다 보면 URL과 URI라는 단어를 무의식적으로 섞어 쓴다. 코드 리뷰에서 "이거 URI인가 URL인가"라는 질문을 받으면 대답이 잘 안 나온다. Java의 `java.net.URL`과 `java.net.URI`의 차이를 모르고 쓰다가 운영 장애를 낸 사례, 한글 도메인이 들어오면 갑자기 죽는 코드, 쿼리 파라미터로 배열을 넘겼더니 다른 언어 백엔드에서 못 받는 사례 — 결국 RFC 3986을 한 번은 정독해야 한다.

이 문서는 그 RFC 3986과 WHATWG URL Standard를 실무 관점에서 풀어낸다. 인코딩 규칙은 별도 문서(URL_Encoding.md)로 분리되어 있으니 여기서는 핵심만 짧게 다룬다.

## URI, URL, URN의 관계

가장 많이 헷갈리는 부분부터 정리한다. **URI가 상위 개념이고 URL과 URN이 그 하위 분류**다. 이 관계는 RFC 3986에 명시되어 있다.

- URI (Uniform Resource Identifier): 자원을 식별하는 문자열 전부
- URL (Uniform Resource Locator): 자원의 위치(접근 방법)를 포함한 URI
- URN (Uniform Resource Name): 위치와 무관하게 자원의 이름을 나타내는 URI

```
URI
├── URL (https://example.com/a, mailto:foo@bar.com, ftp://...)
└── URN (urn:isbn:9788966262281, urn:uuid:550e8400-e29b-...)
```

URN의 실제 사례는 생각보다 적다. 자주 보는 것은 두 가지 정도다.

```
urn:isbn:9788966262281
urn:uuid:550e8400-e29b-41d4-a716-446655440000
```

`urn:` 스킴은 위치 정보를 담지 않으므로 그 자체로 자원에 접근할 수는 없다. 단지 식별자로만 쓴다. SAML, XML 네임스페이스, OASIS 표준 문서에서 종종 나타난다.

URL인데 위치(locator) 역할이 모호한 것도 있다. `data:`, `mailto:`, `file:` 같은 스킴이다.

```
data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==
mailto:user@example.com?subject=hello&body=test
file:///Users/kkyung/Documents/note.txt
```

`data:` URI는 자원을 직접 임베드하므로 위치라는 단어가 어울리지 않는다. `mailto:`는 메일 클라이언트에 동작을 트리거할 뿐 자원을 가리키지는 않는다. 그래서 RFC 3986 이후로는 URL/URN을 구분하기보다 **URI라는 단일 용어를 쓰자**는 입장이 우세하다. WHATWG URL Standard도 이 흐름을 따라가며 그냥 "URL"로 통칭한다.

실무에서는 다음 정도로 정리하면 된다.

- 명세나 RFC를 인용할 때는 URI
- 브라우저 주소창의 그 문자열을 가리킬 때는 URL
- API 클래스 이름은 라이브러리가 정한 그대로 (Java는 URI 권장, Node WHATWG는 URL)

## RFC 3986 ABNF로 본 URI 구조

RFC 3986은 URI를 ABNF 문법으로 정확히 정의한다. 외울 필요는 없지만 한 번 읽어두면 파싱 버그를 잡을 때 도움이 된다.

```
URI         = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
hier-part   = "//" authority path-abempty
            / path-absolute
            / path-rootless
            / path-empty
authority   = [ userinfo "@" ] host [ ":" port ]
```

핵심은 `:`, `//`, `?`, `#`이 구분자라는 점이다. 자체 파싱을 짤 때 흔한 실수는 fragment가 query보다 뒤에 온다는 사실을 놓치는 것이다. `?a=1#b?c=2`에서 `?c=2`는 query가 아니라 fragment의 일부다.

전체 컴포넌트를 다 채운 URL은 다음과 같다.

```
https://user:pass@www.example.com:8080/path/to/resource?key=value#section
\___/   \_______/ \___________/ \__/\_______________/ \_______/ \_____/
scheme  userinfo  host          port path              query     fragment
```

## scheme - 프로토콜 식별자

scheme은 ASCII 영문자로 시작하고 영문/숫자/`+ - .`만 허용한다. **대소문자 구분 없음** (RFC 3986 §3.1). 정규화 시 소문자로 바꾸는 것이 관례다.

자주 쓰는 scheme은 IANA에 등록되어 있다.

| scheme | 기본 포트 | 비고 |
|--------|-----------|------|
| http   | 80        | 평문 |
| https  | 443       | TLS |
| ws     | 80        | WebSocket |
| wss    | 443       | WebSocket over TLS |
| ftp    | 21        | 거의 안 씀 |
| ssh    | 22        | git+ssh:// 같은 형태로 등장 |

custom scheme도 가능하다. 모바일 앱의 deep link(`myapp://`), VS Code(`vscode://`), Slack(`slack://`)이 그 예다. iOS/Android 모두 OS 레벨에서 scheme 기반 라우팅을 지원한다.

## userinfo - 폐기된 영역

`https://user:password@host`처럼 인증 정보를 URL에 넣는 형식은 RFC 3986에 살아 있긴 하지만 **HTTP에서는 폐기 권고**다 (RFC 3986 §3.2.1, RFC 7230). 이유:

- URL은 로그, 브라우저 히스토리, Referer 헤더로 새어나간다
- 비밀번호가 평문으로 노출
- 피싱에 악용 (`https://www.bank.com@evil.com`처럼 보이게)

크롬은 한참 전부터 `user:pass@` 형식 URL을 입력하면 경고를 띄우고, fetch API에서 자격증명을 거부한다. Git의 HTTPS 클론처럼 신뢰된 도구 안에서만 제한적으로 쓴다.

## host - DNS 이름, IPv4, IPv6

host는 세 가지 형태를 가진다.

- reg-name: `www.example.com` 같은 도메인 (DNS resolution)
- IPv4: `192.168.1.1`
- IPv6: `[::1]`, `[2001:db8::1]` — **반드시 대괄호로 감싼다**

IPv6를 대괄호로 감싸지 않으면 포트의 콜론과 IP의 콜론이 섞여 파싱이 안 된다. 그래서 RFC 3986이 IP-literal을 대괄호로 강제한다.

```
http://[::1]:8080/api/health    (정상)
http://::1:8080/api/health      (불가)
```

Java에서 `URI.create("http://::1:8080/")`을 호출하면 그대로 예외가 난다. Node `new URL("http://::1:8080/")`도 마찬가지. Docker 컨테이너에서 IPv6 주소로 헬스체크 URL을 조립할 때 이 부분에서 자주 깨진다.

host는 scheme과 마찬가지로 **대소문자 구분 없음**. `WWW.EXAMPLE.COM`과 `www.example.com`은 같다. 정규화 시 소문자로 통일한다.

## port - 생략 시 기본값

port를 생략하면 scheme의 기본값을 쓴다. `https://example.com:443/`과 `https://example.com/`은 같은 자원이다. 정규화 시 기본 포트는 제거하는 것이 표준이다.

```
http://example.com:80/  →  http://example.com/
https://example.com:443/ →  https://example.com/
```

`http://example.com:80/`을 그대로 두면 캐시 키, OAuth 리다이렉트 URI 정확 일치 검증, 동일 출처(same-origin) 정책에서 문제가 된다. OAuth 2.0 리다이렉트 URI 검증은 문자열 정확 일치를 요구하는 IdP가 많아서, 등록된 URI는 `:80` 없이 했는데 클라이언트가 `:80`을 붙여 보내면 거부당한다.

## path - 자원의 경로

path는 `/`로 구분되는 세그먼트의 나열이다. **path는 대소문자 구분**한다 (RFC 3986 §6.2.2.1). scheme/host와 다르다.

- `/api/Users/123` ≠ `/api/users/123`

운영 서버가 리눅스라 대소문자 구분하는데 윈도우 개발자가 만든 클라이언트가 대문자를 섞어 보내 404가 나는 사례가 흔하다. 백엔드에서 path 매칭 시 대소문자 구분 여부는 프레임워크 기본값을 따른다 (Spring은 기본 구분, IIS는 기본 미구분). 라우팅 충돌이 의심되면 가장 먼저 봐야 할 부분.

### dot-segment 처리

`.`과 `..`은 상대 경로의 현재/상위를 가리킨다. RFC 3986 §5.2.4에 정규화 알고리즘이 있다.

```
/a/b/c/./../../g  →  /a/g
/a/b/../c         →  /a/c
/a/./b            →  /a/b
```

dot-segment가 정리되지 않은 채로 백엔드에 들어오면 path traversal 취약점이 된다. `/api/files/../../../etc/passwd` 같은 요청이 그대로 파일 시스템 호출로 이어지는 케이스. 정상적인 웹서버는 정규화한 후 라우팅하지만, 직접 path를 다룰 때는 항상 정규화부터 한다. Java `Paths.get(path).normalize()`, Node `path.posix.normalize()`.

### trailing slash

`/users`와 `/users/`는 다른 URI다 (RFC 3986 입장). 그러나 실무에서는 같이 다루는 경우가 많다.

- Spring `application.properties`에 `spring.mvc.pathmatch.matching-strategy=ant_path_matcher` (이전 기본) 시 둘을 같게 처리. 5.3+ PathPattern은 다르게 처리.
- Express는 라우터 옵션 `strict`로 제어
- nginx는 `/users`로 들어오면 디렉토리 인덱스를 찾기 위해 301 redirect로 `/users/`를 만드는 기본 동작

REST API라면 둘 중 하나로 통일한다. 보통 trailing slash 없이. 검색 엔진은 정규 URL이 둘이면 페이지 랭크가 분산되므로 canonical URL을 명시하거나 301로 합친다.

### matrix parameter (`;`)

거의 안 쓰지만 RFC 3986이 path 안에 `;`로 파라미터를 넣는 것을 허용한다.

```
/users;v=2/profiles;detail=full
```

JAX-RS, Spring `@MatrixVariable`이 이 문법을 지원하긴 한다. 그러나:

- 캐시 키 다루기 까다로움
- 프레임워크별 지원 편차
- 쿼리스트링이 훨씬 보편적이고 직관적

운영 환경에서 만나면 99% 이상 쿼리로 마이그레이션하는 게 답이다. Spring Boot는 기본적으로 matrix variable을 비활성화한다.

## query - 동적 파라미터

`?` 이후 `#` 전까지가 query. 실제로는 `key=value&key=value` 패턴이지만 RFC 3986은 그 내부 구조를 강제하지 않는다. 따라서 **배열 표기 같은 것은 표준이 아니다**. 프레임워크별로 다르다.

다음은 모두 다른 문자열이다.

```
?ids=1&ids=2&ids=3       # 같은 키 반복 (Spring, ASP.NET, Express qs)
?ids[]=1&ids[]=2&ids[]=3 # PHP, Rails, qs 라이브러리
?ids=1,2,3               # 콤마 구분
?ids=%5B1%2C2%2C3%5D     # JSON array를 인코딩
```

WHATWG `URLSearchParams.getAll('ids')`는 첫 번째 형식만 다룬다. PHP `$_GET['ids']`는 두 번째 형식에서 배열로 받아준다. Node의 `qs` 라이브러리는 두 번째 형식이 기본이지만 옵션을 바꿀 수 있다. 프론트와 백엔드가 다른 라이브러리를 쓰면 여기서 깨진다.

```javascript
// 프론트 (axios + qs)
axios.get('/api/items', { params: { ids: [1, 2, 3] }, paramsSerializer: qs.stringify });
// 결과: /api/items?ids%5B0%5D=1&ids%5B1%5D=2&ids%5B2%5D=3

// 백엔드 (Spring) — 기본 binding은 ids=1&ids=2&ids=3 만 받음
@GetMapping("/items")
public List<Item> get(@RequestParam List<Long> ids) { ... }
```

위 조합은 실패한다. 시작할 때 양쪽 표기를 정해놓고 시작해야 한다.

## fragment - 클라이언트 전용

`#` 이후 부분. 가장 중요한 사실: **fragment는 서버로 전송되지 않는다**. 브라우저 주소창에는 보이지만 HTTP 요청 라인에는 들어가지 않는다.

이 특성을 활용하는 대표적 사례가 OAuth 2.0 implicit flow다. 액세스 토큰을 fragment에 담아 리다이렉트하면 서버 로그/Referer에 토큰이 새지 않는다.

```
https://app.example.com/callback#access_token=xxx&token_type=Bearer
```

다만 implicit flow는 보안 권고에서 제외된 지 오래고 (OAuth 2.0 BCP, RFC 9700), PKCE를 쓴 authorization code flow가 표준이 되었다. fragment 트릭 자체는 SPA의 hash routing(`/#/users/123`)에 그대로 살아 있다. 라우팅이 fragment에서 일어나면 서버는 항상 같은 HTML을 내려보내고 클라이언트가 화면을 그린다.

## 절대 URL과 상대 URL

HTTP 응답에 `Location: /next`가 오면 클라이언트는 어떻게 절대 URL을 만들까. RFC 3986 §5.3 reference resolution 알고리즘을 따른다. 기본 URL과 상대 URL을 결합한다.

```
base:    https://example.com/a/b/c
"/x"    → https://example.com/x          (host-relative)
"x"     → https://example.com/a/b/x      (path-relative)
"../x"  → https://example.com/a/x
"//cdn.example.com/x" → https://cdn.example.com/x  (scheme-relative)
"?q=1"  → https://example.com/a/b/c?q=1  (query-only)
"#sec"  → https://example.com/a/b/c#sec  (fragment-only)
```

scheme-relative URL(`//cdn.example.com`)은 현재 페이지의 scheme을 그대로 따라간다. CDN 자원을 임베드할 때 HTTP/HTTPS 페이지 모두에서 동작하라고 자주 썼다. 요즘은 모두 HTTPS이므로 굳이 안 쓴다. 오히려 mixed content 문제로 더 위험할 수 있다.

HTML `<base href="...">` 태그는 페이지 안의 모든 상대 URL의 기준점을 바꾼다. SSR에서 라우터 prefix를 줄 때 가끔 쓰지만, 라우팅과 자원 경로 모두 영향을 받아 사이드 이펙트가 크다. 가능하면 안 쓰는 쪽이 안전하다.

리다이렉트 처리에서 흔한 버그: 상대 URL을 잘못된 base로 결합. 예를 들어 게이트웨이가 `Location: /v2/users/1`을 받았는데 게이트웨이의 base와 백엔드의 base가 달라 결합 결과가 깨지는 경우. nginx `proxy_redirect` 설정이 이런 상황을 다룬다.

## URL 정규화

같은 자원을 가리키는 URL은 여러 형태로 표현될 수 있다. 캐시 키, 동일 출처 검사, 검색 엔진 인덱싱은 정규화된 형태를 비교해야 한다. RFC 3986 §6에 정규화 단계가 정리되어 있다.

1. scheme/host를 소문자로
2. percent-encoding을 대문자로 (`%2f` → `%2F`)
3. unreserved 문자는 디코드 (`%41` → `A`)
4. dot-segment 제거
5. 기본 포트 제거 (`:80`, `:443`)
6. 빈 path는 `/`로 (`http://example.com` → `http://example.com/`)

```
HTTP://Example.com:80/a/./b/../c/%41  →  http://example.com/a/c/A
```

Java `URI.normalize()`는 4번까지만 한다. host 소문자화, 기본 포트 제거는 직접 해야 한다. `org.apache.http.client.utils.URIUtils.resolve` 같은 라이브러리를 쓰는 편이 안전하다.

## URL 길이 제한

RFC는 길이 제한을 명시하지 않는다. 그러나 실무에는 한계가 있다.

| 위치 | 한계 (대략) |
|------|------|
| IE 11 | 2,083자 |
| Chrome | 32,768자 (주소창), 2MB (내부) |
| Firefox | 65,536자 |
| Edge | 2,083자 |
| Safari | 80,000자 |
| nginx | `large_client_header_buffers` 기본 8KB |
| Apache | `LimitRequestLine` 기본 8KB |
| Tomcat | `maxHttpHeaderSize` 기본 8KB |
| AWS ALB | 16KB (request line + headers 합) |
| CloudFront | 8KB |

브라우저보다 미들웨어/프록시가 더 빠듯하다. nginx 8KB를 넘기면 414 URI Too Long. ALB는 같은 상황에서 400을 반환한다. 보통 아래에서 터진다.

- 검색 필터로 ID 100개를 query string에 넘기는 GET
- JWT를 query string에 담는 (anti-pattern, 보통 헤더로 보낸다)
- base64 인코딩한 데이터를 GET으로 전송

해결책은 GET 대신 POST로 바꾸거나, 필터를 압축하거나(짧은 ID), 클라이언트에서 페이지네이션을 잘게 쪼개는 것. nginx 설정을 늘리는 것은 마지막 수단이다.

```nginx
http {
    large_client_header_buffers 4 16k;
    client_header_buffer_size 16k;
}
```

## Java의 URI vs URL

Java 표준 라이브러리에는 두 클래스가 있다.

- `java.net.URI`: 단순 파싱/정규화, RFC 3986 준수, 권장
- `java.net.URL`: 네트워크 연결까지 포함, **`equals()`/`hashCode()`가 DNS lookup을 함**, 비권장

`URL.equals()`가 DNS lookup을 한다는 사실이 자바 입문자에게는 함정이다. `Set<URL>`을 만들고 거기에 URL을 넣을 때마다 DNS 쿼리가 날아간다. 운영 환경에서 외부 DNS 서버를 막아놓으면 그대로 멈춘다.

```java
URL a = new URL("http://example.com/");
URL b = new URL("http://example.com/");
a.equals(b);  // 호스트의 IP를 resolve해서 비교 → 네트워크 호출
```

해결: `URI`를 쓴다. URL이 필요하면 마지막에 `uri.toURL()`로 변환.

```java
URI uri = URI.create("https://api.example.com:443/v1/users?id=1#frag");
uri.getScheme();      // "https"
uri.getHost();        // "api.example.com"
uri.getPort();        // 443
uri.getRawPath();     // "/v1/users"  (인코딩된 형태)
uri.getPath();        // "/v1/users"  (디코딩된 형태)
uri.getRawQuery();    // "id=1"
uri.getFragment();    // "frag"

// 정규화
URI base = URI.create("https://example.com/a/b/");
URI resolved = base.resolve("../c/d");  // https://example.com/a/c/d
URI relativized = base.relativize(URI.create("https://example.com/a/b/c/d")); // c/d
```

Spring에서는 `UriComponentsBuilder`가 사실상 표준이다. 인코딩까지 자동으로 처리한다.

```java
URI uri = UriComponentsBuilder.newInstance()
    .scheme("https")
    .host("api.example.com")
    .path("/v1/items/{id}")
    .queryParam("category", "books")
    .queryParam("tag", "java", "spring")  // tag=java&tag=spring
    .fragment("section1")
    .buildAndExpand(123)
    .encode()
    .toUri();
// https://api.example.com/v1/items/123?category=books&tag=java&tag=spring#section1
```

`encode()`를 빠뜨리면 한글이나 특수문자가 그대로 들어간다. RestTemplate/WebClient가 알아서 인코딩하지 않으므로 빌더 단계에서 명시한다.

## Node.js URL 파싱

Node 10부터 `url.parse()`(레거시)와 `new URL()`(WHATWG) 두 API가 공존한다. **레거시 API는 deprecated**이지만 여전히 코드베이스에 남아 있을 수 있다.

```javascript
// 레거시 (사용 금지)
const url = require('url');
const parsed = url.parse('https://example.com:8080/path?x=1#y');

// WHATWG (권장)
const u = new URL('https://example.com:8080/path?x=1#y');
u.protocol;      // 'https:'  (콜론 포함, 주의)
u.hostname;      // 'example.com'
u.port;          // '8080'    (문자열, 주의)
u.pathname;      // '/path'
u.search;        // '?x=1'    (물음표 포함)
u.hash;          // '#y'      (샵 포함)
u.searchParams;  // URLSearchParams 객체
```

WHATWG API의 차이점.

- `protocol`은 `https:` (콜론 포함). 비교 시 헷갈림
- `port`는 문자열. 기본 포트면 빈 문자열
- 자동 정규화 (소문자화, percent-encoding 정리)

상대 URL 결합은 두 번째 인자로 base를 준다.

```javascript
new URL('/api/users', 'https://example.com').href;
// 'https://example.com/api/users'

new URL('../v2/users', 'https://example.com/api/v1/items').href;
// 'https://example.com/api/v2/users'
```

`URLSearchParams`는 query string 빌드/파싱의 표준이지만 배열 처리에 한계가 있다.

```javascript
const params = new URLSearchParams();
params.append('ids', '1');
params.append('ids', '2');
params.toString();         // 'ids=1&ids=2'
params.getAll('ids');      // ['1', '2']

// 객체에서 만들기 — 배열 값은 문자열화됨 (의도와 다름)
new URLSearchParams({ ids: [1, 2] }).toString();  // 'ids=1%2C2'
```

배열이 필요하면 `qs` 라이브러리를 쓴다. 단, 백엔드와 표기를 맞춘다.

## 한글 도메인과 IDN

`한글도메인.kr` 같은 IDN(Internationalized Domain Name)은 DNS 레벨에서는 ASCII로 변환되어 처리된다. 변환 알고리즘이 Punycode(RFC 3492)이고, 변환 결과는 `xn--`로 시작한다.

```
한글.kr  →  xn--bj0bj06e.kr
한글도메인.kr  →  xn--bj0bj06ec0it7c.kr
```

브라우저 주소창에는 한글로 보이지만 실제 HTTP 호스트 헤더와 TLS SNI는 Punycode 형태를 쓴다. 서버 인증서 발급 시 SAN에 Punycode를 넣어야 한다.

Java `IDN.toASCII()`로 변환한다. URL 빌더가 자동으로 해주지 않는다.

```java
String host = IDN.toASCII("한글.kr");  // xn--bj0bj06e.kr
URI uri = URI.create("https://" + host + "/");
```

Node `new URL('https://한글.kr/')`은 자동으로 Punycode 변환을 한다.

```javascript
new URL('https://한글.kr/').hostname;  // 'xn--bj0bj06e.kr'
```

운영 환경 트러블슈팅에서 자주 만나는 사례:

- 사용자가 한글 도메인을 입력 → 브라우저는 Punycode로 변환 → 백엔드 Host 헤더에 `xn--`이 들어옴 → 화이트리스트 검증이 한글 문자열로 되어 있어 실패
- 메일 발송 시 From 주소 도메인이 IDN인데 SMTP 서버가 Punycode를 요구

## URL 인코딩 (요약)

자세한 내용은 별도 문서(URL_Encoding.md)로 미룬다. 여기서는 기억할 만한 부분만.

- path와 query에서 허용되는 문자 집합이 다르다 (RFC 3986 §3.3 vs §3.4)
- `+`는 query에서 공백으로 해석되는 관습이 있다 (HTML form 인코딩, RFC 1866). path에서는 그냥 `+`다
- percent-encoding 대상은 unreserved(A-Z a-z 0-9 `- _ . ~`)를 제외한 문자
- 동일한 byte 시퀀스라도 인코딩 여부에 따라 다른 URI가 된다 (`/a/b`와 `/a%2Fb`는 다른 path)

`/a%2Fb`는 한 세그먼트 안에 슬래시가 들어간 형태. 라우터가 디코드한 후 라우팅하면 `/a/b`로 잘못 잡는다. Tomcat은 보안상 기본적으로 `%2F`를 거부한다 (`org.apache.tomcat.util.buf.UDecoder.ALLOW_ENCODED_SLASH=false`). S3 객체 키에 슬래시가 들어가는 경우 이 문제로 자주 막힌다.

## RESTful URL 설계

회사 와서 처음 짜는 API 가이드는 거의 같다.

- 자원은 명사, 복수형: `/users`, `/orders`
- 단일 자원은 ID로: `/users/{id}`
- 계층 관계는 path: `/users/{id}/orders`
- 동사는 안 씀: `/users/{id}/delete` (X) → `DELETE /users/{id}`
- 필터링/정렬/페이지네이션은 query: `/users?role=admin&sort=-createdAt&page=2`
- 액션은 자원으로 모델링: `POST /orders/{id}/refund` 같이 동사가 필요하면 컬렉션을 만든다

세부 규칙보다 중요한 것은 **일관성**. 한 서비스 안에서 같은 패턴을 쓴다. 프로젝트 중간에 `/users/{id}`와 `/user/{id}` 둘 다 있는 코드는 결국 한쪽이 죽거나 양쪽 모두 유지보수 비용이 든다.

API 버전은 path 또는 헤더로 다룬다.

```
/v1/users          (path versioning, 가장 간단)
Accept: application/vnd.example.v1+json   (media type versioning)
```

path 버저닝이 디버깅이 쉬워서 대부분 이쪽을 고른다. media type 버저닝은 캐시 키가 헤더로 들어가야 하므로 CDN 설정이 까다롭다.

## 트러블슈팅 사례 모음

### 사례 1: OAuth 리다이렉트 URI 검증 실패

OAuth IdP에 등록한 redirect_uri는 `https://app.example.com/callback`인데, 클라이언트가 `https://app.example.com:443/callback`으로 보내서 거부됨. IdP가 문자열 정확 일치를 요구. 클라이언트에서 URL 정규화(기본 포트 제거) 후 전송.

### 사례 2: 한글 파일명 다운로드

S3에서 한글 파일명 객체 다운로드 URL을 그대로 백엔드가 받아서 클라이언트에 내려주는데, 일부 브라우저에서 깨짐. 원인은 한글이 percent-encoding된 URL을 또 한 번 인코딩해서 이중 인코딩. presigned URL은 그대로 패스스루해야 한다.

### 사례 3: trailing slash로 인한 308 redirect 루프

API 게이트웨이가 trailing slash를 자동으로 추가하는 설정과 백엔드가 자동으로 제거하는 설정이 동시에 켜져 있어서 무한 루프. 서킷브레이커가 도는 시점에서 발견. 한쪽으로 통일.

### 사례 4: query string의 `+`와 공백

검색어 `C++`을 그대로 query에 넣었더니 백엔드에서 `C  `(공백 두 칸)으로 받음. 클라이언트가 `+`를 percent-encoding하지 않고 보냈고, 백엔드 form 디코더가 `+`를 공백으로 해석. `%2B`로 인코딩하거나 path로 보냈어야 한다.

### 사례 5: URL.equals()의 DNS lookup

크론잡에서 외부 URL 목록을 `Set<URL>`에 넣어 중복 제거. 회사망 DNS 서버 점검 중에 잡이 멈춤. `Set<URI>`로 변경.

## 정리

- URI는 상위 개념, URL은 위치 정보를 가진 URI, URN은 위치 정보가 없는 URI
- RFC 3986이 표준. WHATWG URL Standard는 브라우저 동작을 더 엄밀히 규정
- scheme/host는 대소문자 구분 없음, path는 구분 있음
- IPv6 host는 대괄호 필수
- userinfo는 폐기, fragment는 서버로 안 감
- Java는 URI 권장 (URL.equals는 DNS 호출), Node는 WHATWG URL 권장
- query 배열 표기는 표준이 없으니 양쪽 합의 필수
- 한글 도메인은 Punycode 자동/수동 변환에 따라 동작이 달라짐
- 길이 제한은 RFC가 아니라 미들웨어가 정한다 (보통 8KB)

## 참조

- RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
- RFC 3987: Internationalized Resource Identifiers (IRIs)
- RFC 3492: Punycode
- RFC 7230 §2.7: URI references in HTTP
- WHATWG URL Living Standard (https://url.spec.whatwg.org/)
- Spring Framework: UriComponentsBuilder
- Node.js Documentation: URL
