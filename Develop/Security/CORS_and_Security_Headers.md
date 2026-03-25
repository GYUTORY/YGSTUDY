---
title: "브라우저 보안 헤더 종합 정리"
tags: [security, http-headers, csp, hsts, nginx, spring-boot]
updated: 2026-03-25
---

# 브라우저 보안 헤더 종합 정리

## 왜 보안 헤더를 신경 써야 하는가

서버가 응답할 때 붙이는 HTTP 헤더 몇 줄이 XSS, 클릭재킹, MIME 스니핑 같은 클라이언트 사이드 공격을 차단한다. 코드 한 줄 안 고치고 헤더만 추가해도 공격 표면이 줄어든다. [securityheaders.com](https://securityheaders.com)에서 자기 도메인을 찍어보면 현재 상태를 바로 확인할 수 있다.

---

## Content-Security-Policy (CSP)

브라우저에게 "이 페이지에서 허용하는 리소스 출처는 여기뿐이다"라고 알려주는 헤더다. XSS 공격의 실질적인 방어선이 된다.

### 기본 구조

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com; style-src 'self' 'unsafe-inline'; img-src *; connect-src 'self' https://api.example.com
```

각 디렉티브는 세미콜론(`;`)으로 구분한다. `default-src`는 명시하지 않은 리소스 타입의 폴백이다.

### 자주 쓰는 디렉티브

| 디렉티브 | 역할 |
|-----------|------|
| `default-src` | 다른 디렉티브에서 명시하지 않은 모든 리소스의 기본 출처 |
| `script-src` | JavaScript 로드 허용 출처 |
| `style-src` | CSS 로드 허용 출처 |
| `img-src` | 이미지 로드 허용 출처 |
| `connect-src` | XHR, fetch, WebSocket 연결 허용 출처 |
| `frame-ancestors` | 이 페이지를 iframe으로 포함할 수 있는 출처 (X-Frame-Options 대체) |
| `form-action` | form 태그의 action 속성에 허용할 출처 |
| `base-uri` | `<base>` 태그에 허용할 출처 |

### nonce 방식

인라인 스크립트를 허용해야 하는데 `'unsafe-inline'`은 쓰기 싫을 때 nonce를 쓴다. 서버가 매 요청마다 랜덤 nonce를 생성해서 헤더와 스크립트 태그 양쪽에 넣는다.

```
Content-Security-Policy: script-src 'nonce-abc123def456'
```

```html
<script nonce="abc123def456">
  // 이 스크립트는 실행된다
</script>
<script>
  // nonce가 없으므로 브라우저가 차단한다
</script>
```

Spring Boot에서 nonce를 요청마다 생성하는 예시:

```java
@Component
public class CspNonceFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {
        String nonce = Base64.getEncoder().encodeToString(
            SecureRandom.getInstanceStrong().generateSeed(16)
        );
        request.setAttribute("cspNonce", nonce);
        response.setHeader("Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'nonce-" + nonce + "'; style-src 'self' 'nonce-" + nonce + "'");
        filterChain.doFilter(request, response);
    }
}
```

Thymeleaf 템플릿에서:

```html
<script th:attr="nonce=${cspNonce}">
  console.log("nonce가 자동으로 붙는다");
</script>
```

### hash 방식

스크립트 내용이 고정되어 있으면 hash가 더 간단하다. 스크립트 내용의 SHA-256 해시를 CSP에 넣는다.

```bash
echo -n 'console.log("hello")' | openssl dgst -sha256 -binary | openssl base64
# 출력: sEaFBswe0TGjKJqu/dEKoE24HxLJdKUzqHLQfp0gWdc=
```

```
Content-Security-Policy: script-src 'sha256-sEaFBswe0TGjKJqu/dEKoE24HxLJdKUzqHLQfp0gWdc='
```

주의할 점: 스크립트 내용이 공백 하나라도 바뀌면 해시가 달라진다. 빌드 타임에 해시를 자동 생성하는 파이프라인을 만들어두지 않으면 운영에서 깨진다.

### CSP 적용 시 실수하는 것들

**`'unsafe-inline'`과 nonce를 동시에 쓰는 경우** — CSP Level 2 이상 브라우저에서는 nonce가 있으면 `'unsafe-inline'`을 무시한다. 하지만 오래된 브라우저 호환을 위해 둘 다 넣는 경우가 있다. 의도한 거라면 상관없지만, nonce를 넣었으니 안전하다고 착각하면서 `'unsafe-eval'`까지 열어두는 실수를 하면 의미가 없어진다.

**report-uri로 위반 로그 수집** — 처음부터 `Content-Security-Policy`를 박으면 서비스가 깨질 수 있다. `Content-Security-Policy-Report-Only`로 먼저 배포해서 위반 로그를 모아야 한다.

```
Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-report
```

```java
@PostMapping("/csp-report")
public ResponseEntity<Void> handleCspReport(@RequestBody String report) {
    log.warn("CSP violation: {}", report);
    return ResponseEntity.ok().build();
}
```

한 달 정도 Report-Only로 돌리면서 위반 로그를 확인한 뒤, 문제없는 것부터 점진적으로 적용하는 게 현실적이다.

---

## Strict-Transport-Security (HSTS)

브라우저에게 "이 도메인은 앞으로 HTTPS로만 접속해라"라고 알려준다. HTTP로 접속하면 브라우저가 서버에 요청을 보내기도 전에 자체적으로 HTTPS로 리다이렉트한다.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

| 속성 | 의미 |
|------|------|
| `max-age` | 초 단위. 31536000은 1년. 이 기간 동안 HTTPS만 사용 |
| `includeSubDomains` | 서브도메인까지 적용 |
| `preload` | 브라우저의 HSTS preload list에 등록 요청 |

### HSTS가 막는 공격

카페 와이파이 같은 공용 네트워크에서 공격자가 중간에 끼어들어 HTTP 응답을 조작하는 SSL 스트리핑 공격을 막는다. HSTS가 없으면 사용자가 `http://bank.com`으로 접속할 때 공격자가 HTTPS 리다이렉트를 가로채고 평문 HTTP로 통신하게 만들 수 있다.

### 주의사항

- HTTPS 설정이 완전히 끝나기 전에 HSTS를 켜면 사이트 접속이 안 된다. 인증서 만료나 갱신 실패 시에도 접속 불가 상태가 `max-age` 동안 지속된다.
- 처음에는 `max-age=300` 같이 짧게 시작해서 문제가 없으면 점차 늘려야 한다.
- `preload`를 한번 등록하면 해제하는 데 몇 달이 걸린다. 확신이 없으면 넣지 않는다.

---

## X-Content-Type-Options

```
X-Content-Type-Options: nosniff
```

값은 `nosniff` 하나뿐이다. 브라우저가 MIME 타입을 추측(sniffing)하지 않도록 막는다.

### 이걸 안 넣으면 생기는 일

공격자가 이미지 업로드 기능에 JavaScript가 포함된 파일을 `.jpg` 확장자로 올린다. 서버가 `Content-Type: image/jpeg`로 응답하지만, 브라우저가 내용을 보고 "이건 JavaScript인데?"라고 판단해서 스크립트로 실행해버린다. `nosniff`가 있으면 서버가 내려준 Content-Type을 그대로 따르므로 이런 공격이 차단된다.

설정 한 줄이니까 무조건 넣는다.

---

## X-Frame-Options

```
X-Frame-Options: DENY
```

이 페이지를 `<iframe>`, `<frame>`, `<object>` 안에 넣을 수 있는지 제어한다.

| 값 | 의미 |
|----|------|
| `DENY` | 어떤 사이트에서도 iframe으로 포함 불가 |
| `SAMEORIGIN` | 같은 출처에서만 iframe 허용 |

### 클릭재킹 공격 차단

공격자가 자기 사이트에 투명 iframe으로 은행 사이트를 띄운다. 사용자는 공격자 사이트의 "경품 받기" 버튼을 누르지만, 실제로는 투명한 은행 사이트의 "송금" 버튼을 누르게 된다. `X-Frame-Options: DENY`가 있으면 브라우저가 iframe 렌더링 자체를 거부한다.

CSP의 `frame-ancestors` 디렉티브가 더 세밀한 제어가 가능하지만, 오래된 브라우저 호환을 위해 둘 다 넣는 경우가 많다.

---

## Referrer-Policy

```
Referrer-Policy: strict-origin-when-cross-origin
```

다른 사이트로 이동할 때 Referer 헤더에 어디까지 보낼지 정한다.

| 값 | 동작 |
|----|------|
| `no-referrer` | Referer 헤더를 아예 보내지 않는다 |
| `origin` | 출처(프로토콜 + 호스트 + 포트)만 보낸다. 경로는 제거 |
| `strict-origin-when-cross-origin` | 같은 출처에는 전체 URL, 다른 출처에는 origin만, HTTPS→HTTP는 안 보냄 |
| `same-origin` | 같은 출처에만 보냄 |

`strict-origin-when-cross-origin`이 대부분의 상황에서 적당하다. 내부 URL 경로에 토큰이나 세션 ID가 포함된 경우(이런 설계 자체가 문제지만 레거시에서 종종 보인다) Referer를 통해 외부로 유출될 수 있으므로 `no-referrer`나 `origin`을 쓴다.

---

## Permissions-Policy

```
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

브라우저 API(카메라, 마이크, 위치 정보 등)의 사용 권한을 제어한다. 빈 괄호 `()`는 모든 출처에서 차단한다는 의미다.

```
Permissions-Policy: camera=(self), microphone=(self "https://meeting.example.com"), geolocation=()
```

- `camera=(self)` — 같은 출처에서만 카메라 사용 가능
- `microphone=(self "https://meeting.example.com")` — 같은 출처와 지정된 도메인에서만 마이크 사용 가능
- `geolocation=()` — 위치 정보 완전 차단

써드파티 스크립트가 사용자 동의 없이 카메라나 마이크에 접근하는 걸 원천 차단할 수 있다. 서비스에서 쓰지 않는 브라우저 API는 전부 막아두는 게 맞다.

---

## Nginx 설정 예제

실서비스에서 바로 사용할 수 있는 수준의 설정이다.

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # CSP — Report-Only로 먼저 테스트할 때는 헤더 이름만 바꾸면 된다
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

    # MIME 스니핑 차단
    add_header X-Content-Type-Options "nosniff" always;

    # 클릭재킹 차단
    add_header X-Frame-Options "DENY" always;

    # Referer 제어
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 브라우저 API 제한
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

    # ... SSL, proxy 설정 등
}
```

**`always` 파라미터를 빠뜨리면 안 된다.** Nginx는 기본적으로 2xx, 3xx 응답에만 `add_header`를 적용한다. 4xx, 5xx 에러 페이지에서도 보안 헤더가 빠지지 않으려면 `always`가 필요하다.

**location 블록에서 `add_header`를 쓰면 server 블록의 `add_header`가 전부 사라진다.** Nginx의 `add_header`는 상속이 아니라 오버라이드다. location 블록에 헤더를 하나라도 추가하면 server 블록에서 설정한 보안 헤더가 전부 무시된다. 이걸 모르고 특정 경로에 캐시 헤더만 추가했다가 보안 헤더가 통째로 날아가는 경우가 있다. `include` 디렉티브로 공통 헤더 파일을 만들어서 모든 블록에서 불러오는 방식으로 해결한다.

```nginx
# /etc/nginx/snippets/security-headers.conf
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
```

```nginx
server {
    include /etc/nginx/snippets/security-headers.conf;

    location /api/ {
        include /etc/nginx/snippets/security-headers.conf;
        proxy_pass http://backend;
    }
}
```

---

## Spring Boot 설정 예제

Spring Security를 사용하는 경우:

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .headers(headers -> headers
                // HSTS — Spring Security는 HTTPS 요청에 대해 기본 활성화
                .httpStrictTransportSecurity(hsts -> hsts
                    .maxAgeInSeconds(31536000)
                    .includeSubDomains(true)
                )
                // CSP
                .contentSecurityPolicy(csp -> csp
                    .policyDirectives("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
                )
                // X-Content-Type-Options — Spring Security 기본 활성화
                .contentTypeOptions(Customizer.withDefaults())
                // X-Frame-Options
                .frameOptions(frame -> frame.deny())
                // Referrer-Policy
                .referrerPolicy(referrer -> referrer
                    .policy(ReferrerPolicyHeaderWriter.ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN)
                )
                // Permissions-Policy
                .permissionsPolicy(permissions -> permissions
                    .policy("camera=(), microphone=(), geolocation=(), payment=()")
                )
            );

        return http.build();
    }
}
```

Spring Security 없이 필터로 직접 설정하는 경우:

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class SecurityHeaderFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {
        response.setHeader("X-Content-Type-Options", "nosniff");
        response.setHeader("X-Frame-Options", "DENY");
        response.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
        response.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()");
        response.setHeader("Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'");

        if (request.isSecure()) {
            response.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
        }

        filterChain.doFilter(request, response);
    }
}
```

HSTS는 HTTPS 요청일 때만 설정하는 게 맞다. HTTP 응답에 HSTS를 넣으면 공격자가 조작할 수 있으므로 브라우저가 무시한다.

---

## securityheaders.com 점수 개선 실무

[securityheaders.com](https://securityheaders.com)에 도메인을 입력하면 A+부터 F까지 등급을 매겨준다. 점수를 올리는 순서:

### F → D: 기본 헤더 추가

`X-Content-Type-Options`, `X-Frame-Options` 두 개만 넣어도 F에서 벗어난다. 설정이 단순하고 사이드 이펙트가 거의 없으니 바로 적용해도 된다.

### D → B: HSTS, Referrer-Policy 추가

HSTS는 HTTPS 설정이 확실한 경우에만 넣는다. `max-age`를 짧게 시작해서 늘려간다. Referrer-Policy는 `strict-origin-when-cross-origin`으로 넣으면 대부분 문제없다.

### B → A: CSP 추가

CSP가 가장 까다롭다. 인라인 스크립트, 외부 CDN, 분석 도구(Google Analytics 등) 때문에 한 번에 적용하기 어렵다.

1. `Content-Security-Policy-Report-Only`로 배포
2. 위반 로그를 수집해서 허용이 필요한 출처 목록을 정리
3. 점진적으로 디렉티브 추가
4. 안정화되면 `Content-Security-Policy`로 전환

### A → A+: Permissions-Policy 추가

`Permissions-Policy`를 넣으면 A+가 나온다. 서비스에서 쓰지 않는 브라우저 API를 전부 `()`로 막으면 된다.

### 실무에서 자주 막히는 부분

**Google Analytics, GTM** — `script-src`에 `https://www.googletagmanager.com`을 허용해야 하고, GTM이 동적으로 스크립트를 삽입하기 때문에 `'unsafe-inline'`을 요구하는 경우가 있다. nonce 방식으로 우회할 수 있지만, GTM 컨테이너 내부의 커스텀 HTML 태그까지 nonce를 적용하려면 GTM의 Custom Template 기능을 써야 한다.

**CDN에서 받는 라이브러리** — `script-src`에 CDN 도메인을 추가해야 한다. 특정 경로까지 제한하고 싶으면 CSP Level 3의 `strict-dynamic`과 nonce를 조합한다.

**웹소켓** — `connect-src`에 `wss://` 스킴을 포함한 주소를 넣어야 한다. `ws://`는 평문이므로 프로덕션에서 쓰면 안 된다.

**서비스 워커** — `worker-src`를 별도로 설정해야 한다. `default-src`나 `script-src`를 폴백으로 사용하지만, 명시적으로 `worker-src 'self'`를 넣는 게 명확하다.

---

## 헤더별 공격 차단 요약

| 헤더 | 차단하는 공격 |
|------|---------------|
| Content-Security-Policy | XSS (인라인 스크립트 삽입, 외부 스크립트 로드) |
| Strict-Transport-Security | SSL 스트리핑, 중간자 공격(MITM)에서의 다운그레이드 |
| X-Content-Type-Options | MIME 스니핑을 이용한 스크립트 실행 |
| X-Frame-Options | 클릭재킹 (투명 iframe 오버레이) |
| Referrer-Policy | URL 경로에 포함된 민감 정보 유출 |
| Permissions-Policy | 써드파티 스크립트의 브라우저 API 무단 접근 |

---

## 헤더 점검 자동화

CI/CD 파이프라인에서 배포 후 보안 헤더를 자동으로 체크하는 스크립트:

```bash
#!/bin/bash
URL="https://example.com"
REQUIRED_HEADERS=(
    "strict-transport-security"
    "content-security-policy"
    "x-content-type-options"
    "x-frame-options"
    "referrer-policy"
    "permissions-policy"
)

MISSING=0
HEADERS=$(curl -sI "$URL")

for header in "${REQUIRED_HEADERS[@]}"; do
    if ! echo "$HEADERS" | grep -qi "$header"; then
        echo "MISSING: $header"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo "Security header check failed: $MISSING header(s) missing"
    exit 1
fi

echo "All security headers present"
```

배포 파이프라인에 이 스크립트를 넣어두면 누군가 Nginx 설정을 수정하다가 보안 헤더를 날려먹어도 바로 잡힌다.
