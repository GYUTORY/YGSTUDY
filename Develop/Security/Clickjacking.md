---
title: Clickjacking (클릭재킹)
tags: [security, clickjacking, x-frame-options, csp, frame-ancestors, samesite, iframe]
updated: 2026-06-15
---

# Clickjacking (클릭재킹)

사용자가 보고 있는 화면과 실제로 클릭되는 대상이 다른 공격이다. 공격자 페이지 위에 투명한 iframe으로 우리 사이트를 띄워 놓고, 사용자가 "이벤트 응모" 버튼인 줄 알고 누른 좌표에서 실제로는 우리 사이트의 "계정 삭제"나 "송금" 버튼이 눌리게 만든다. 입력값 검증이나 인증으로는 막을 수 없다. 사용자가 자기 세션으로 직접 클릭한 정상 요청이기 때문이다.

XSS는 스크립트를 주입하고 CSRF는 요청을 위조한다. 클릭재킹은 둘 다 아니다. 사용자의 진짜 클릭을 가로채는 거라서 UI 레벨 공격(UI redressing)으로 분류한다.

```
[공격자 페이지]  "지금 가입하면 상품권 지급! [응모하기]" 버튼 표시
        ↓ (위에 투명 iframe 겹침)
[우리 사이트 iframe]  opacity:0 으로 안 보이지만 같은 위치에 "계정 삭제" 버튼
        ↓
사용자가 "응모하기"를 누름 → 좌표상 실제로는 iframe의 "계정 삭제" 클릭됨
        ↓
우리 서버는 로그인된 사용자의 정상 클릭으로 처리
```

## 공격 원리

### iframe 오버레이

기본 형태는 우리 사이트를 iframe으로 띄우고 CSS로 투명하게 만든 뒤, 그 위 혹은 아래에 미끼 UI를 배치하는 방식이다.

```html
<style>
  iframe {
    position: absolute;
    top: 0; left: 0;
    width: 500px; height: 500px;
    opacity: 0;            /* 완전히 투명하게 */
    z-index: 2;            /* 미끼보다 위에 둬서 클릭을 가로챔 */
  }
  .decoy {
    position: absolute;
    top: 220px; left: 180px;   /* iframe의 실제 버튼 좌표에 맞춤 */
    z-index: 1;
  }
</style>

<button class="decoy">무료 상품권 받기</button>
<iframe src="https://victim.example.com/account/settings"></iframe>
```

사용자 눈에는 "무료 상품권 받기"만 보인다. iframe은 투명하지만 클릭 이벤트는 받는다(`pointer-events`를 끄지 않는 한). z-index를 미끼보다 높게 두면 사용자 클릭은 iframe으로 전달된다. 공격자는 iframe 안에서 위험한 버튼이 화면 어디에 그려지는지 미리 확인하고, 미끼 버튼을 그 좌표에 정확히 겹친다.

### UI redressing 변형

투명 오버레이만 있는 게 아니다. 실무에서 본 변형들:

- **드래그 앤 드롭 탈취**: 사용자가 색깔 블록을 드래그하게 유도하면서, 실제로는 iframe 안의 텍스트(예: OAuth 인증 코드, 토큰이 박힌 URL)를 드래그해 공격자 입력창에 떨어뜨리게 한다.
- **커서재킹(cursorjacking)**: CSS로 가짜 커서를 그려서 사용자가 인식하는 마우스 위치와 실제 클릭 위치를 어긋나게 만든다.
- **부분 노출**: iframe 전체를 숨기지 않고, 위험 버튼 부분만 미끼 위로 살짝 노출시켜 자연스러운 UI처럼 보이게 한다.
- **좋아요재킹(likejacking)**: SNS의 좋아요/공유 버튼을 투명 iframe으로 겹쳐, 사용자가 무심코 누르면 공격자 콘텐츠가 확산된다.

핵심은 전부 "사용자에게 보이는 것"과 "실제 클릭 대상"의 분리다. 그래서 방어도 입력값이 아니라 "우리 페이지가 다른 사이트의 iframe 안에 들어갈 수 있는가"를 통제하는 쪽으로 간다.

## 방어 1: X-Frame-Options

가장 오래된 방어 헤더다. 우리 페이지가 iframe/frame/object 안에 들어갈 수 있는지를 브라우저에 알린다.

```
X-Frame-Options: DENY          # 어떤 사이트에서도 iframe 금지
X-Frame-Options: SAMEORIGIN    # 같은 출처에서만 iframe 허용
```

`DENY`가 제일 안전하다. iframe으로 우리 페이지를 띄우는 것 자체를 차단하면 오버레이 공격이 성립하지 않는다. 같은 도메인 안에서 자기 페이지를 iframe으로 쓰는 경우가 있으면 `SAMEORIGIN`을 쓴다.

주의할 점이 몇 가지 있다.

`ALLOW-FROM uri` 옵션이 과거에 있었지만 지금은 쓰면 안 된다. Chrome, Safari는 처음부터 무시했고 Firefox만 일부 지원했다. 단일 출처만 지정 가능했고 여러 출처를 나열할 수도 없었다. 특정 출처에만 iframe을 허용하려면 X-Frame-Options 대신 CSP `frame-ancestors`를 써야 한다.

X-Frame-Options는 HTTP 응답 헤더로만 동작한다. `<meta>` 태그로 넣으면 무시된다. 아래는 효과가 없다.

```html
<!-- 동작 안 함. 메타 태그로 X-Frame-Options를 설정할 수 없다 -->
<meta http-equiv="X-Frame-Options" content="DENY">
```

## 방어 2: CSP frame-ancestors

CSP(Content-Security-Policy)의 `frame-ancestors` 디렉티브가 X-Frame-Options의 후속이다. 표준이고 표현력이 더 좋다. 여러 출처를 지정할 수 있고, 와일드카드도 된다.

```
Content-Security-Policy: frame-ancestors 'none'
Content-Security-Policy: frame-ancestors 'self'
Content-Security-Policy: frame-ancestors 'self' https://partner.example.com
Content-Security-Policy: frame-ancestors https://*.example.com
```

- `'none'` → X-Frame-Options DENY에 대응
- `'self'` → SAMEORIGIN에 대응
- 출처 나열 → ALLOW-FROM이 못 하던 다중 출처 허용

`frame-ancestors`는 `default-src` 같은 다른 디렉티브의 영향을 받지 않는다. 별도로 명시해야 적용된다. `default-src 'self'`만 있다고 frame 통제가 되는 게 아니다.

둘 다 보내야 하나? 최신 브라우저는 frame-ancestors만 있으면 충분하다. 그런데 둘 다 있으면 CSP를 지원하는 브라우저는 frame-ancestors를 우선하고, 아주 오래된 브라우저(IE11 등)는 X-Frame-Options를 본다. 호환성을 챙기려면 둘 다 보내는 게 안전하다. 단, 두 헤더의 정책이 서로 모순되지 않게 맞춰야 한다.

```
# 정책 일치 — 권장
X-Frame-Options: DENY
Content-Security-Policy: frame-ancestors 'none'
```

```
# 모순 — 브라우저마다 동작이 갈려서 디버깅이 어려워진다
X-Frame-Options: SAMEORIGIN
Content-Security-Policy: frame-ancestors 'none'
```

## 방어 3: frame-busting 스크립트의 한계

헤더가 표준화되기 전에는 JS로 직접 막았다. "내가 최상위 창이 아니면 탈출한다"는 코드다.

```javascript
// 전통적인 frame-busting — 지금은 신뢰하면 안 된다
if (top !== self) {
  top.location = self.location;
}
```

이 방식은 우회 수단이 너무 많다.

`sandbox` 속성으로 무력화된다. 공격자가 iframe에 `sandbox="allow-forms allow-scripts"`를 주고 `allow-top-navigation`을 빼면, 스크립트는 실행되지만 `top.location` 변경이 차단된다. 탈출 코드가 막힌다.

```html
<!-- allow-top-navigation 없음 → frame-busting의 top.location 변경 차단됨 -->
<iframe src="https://victim.example.com" sandbox="allow-forms allow-scripts"></iframe>
```

`onbeforeunload`로도 우회된다. 페이지가 빠져나가려 할 때 confirm 창을 띄워 사용자가 취소하게 유도하거나, 공격자 쪽에서 네비게이션을 가로챈다. 과거에는 IE의 `security=restricted` 같은 속성으로 스크립트 자체를 꺼버리는 방법도 있었다.

게다가 frame-busting 코드는 스크립트가 로드되고 실행되기 전 짧은 순간에 페이지가 그대로 노출된다. 그 사이 클릭이 발생할 수 있다.

결론은 frame-busting은 헤더를 못 쓰는 환경의 마지막 수단일 뿐이고, 단독 방어로는 안 된다. X-Frame-Options나 frame-ancestors를 1차 방어로 두고, 굳이 쓴다면 보조로만 둔다. 그나마 쓸 거면 아래처럼 기본을 숨기고 최상위일 때만 보이게 하는 형태가 노출 순간을 줄인다.

```html
<head>
  <style id="antiClickjack">body { display: none !important; }</style>
</head>
<script>
  if (self === top) {
    // 최상위 창이면 정상 표시
    document.getElementById('antiClickjack').remove();
  } else {
    // iframe 안이면 탈출 시도
    top.location = self.location;
  }
</script>
```

## 방어 4: SameSite 쿠키 연계

클릭재킹 자체를 SameSite 쿠키가 막아주진 않는다. 사용자가 우리 사이트(iframe)를 직접 클릭하는 거라서 요청은 우리 도메인으로 가고, 그건 same-site 맥락이 아니라 cross-site 맥락이다. 여기서 SameSite가 의미를 가진다.

iframe 안의 우리 페이지는 공격자 도메인(top-level) 아래에 임베드된 상태다. 이 iframe에서 발생하는 요청은 cross-site로 분류된다. 쿠키를 `SameSite=Lax`나 `Strict`로 설정하면, cross-site 맥락에서 세션 쿠키가 자동 첨부되지 않는다. 세션 쿠키가 안 붙으면 클릭이 가로채여도 인증된 요청으로 처리되지 않는다.

```
Set-Cookie: sessionId=abc123; HttpOnly; Secure; SameSite=Lax
```

- `SameSite=Lax` (요즘 브라우저 기본값): cross-site iframe에서 보내는 요청에 쿠키 미첨부. 클릭재킹으로 발생하는 POST류 요청은 쿠키 없이 나간다.
- `SameSite=Strict`: 더 강하게 막는다. 단, 외부에서 우리 사이트로 정상 진입할 때도 쿠키가 안 붙어서 UX가 깨질 수 있다.
- `SameSite=None; Secure`: cross-site에서도 쿠키 첨부. iframe 임베드 위젯이 세션을 필요로 할 때 쓰는데, 이러면 클릭재킹 방어 효과가 사라진다. 꼭 필요한 경우만 쓰고, 이땐 frame-ancestors로 임베드 출처를 좁혀야 한다.

정리하면 방어는 헤더(frame-ancestors / X-Frame-Options)로 iframe 임베드 자체를 막는 게 1차다. SameSite는 혹시 임베드가 허용된 경로가 있어도 세션이 안 붙게 하는 2차 방어다. 둘은 대체재가 아니라 같이 쓰는 거다.

## Node 헤더 설정

### Express에서 직접 설정

```javascript
const express = require('express');
const app = express();

app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Content-Security-Policy', "frame-ancestors 'none'");
  next();
});
```

특정 페이지만 파트너 임베드를 허용해야 하는 경우, 라우트별로 분리한다.

```javascript
// 기본은 전부 차단
app.use((req, res, next) => {
  res.setHeader('Content-Security-Policy', "frame-ancestors 'none'");
  next();
});

// 위젯 페이지만 특정 파트너 임베드 허용
app.get('/widget', (req, res) => {
  res.setHeader(
    'Content-Security-Policy',
    "frame-ancestors 'self' https://partner.example.com"
  );
  // X-Frame-Options는 다중 출처를 표현 못 하므로 이 라우트에선 빼거나 SAMEORIGIN로만
  res.removeHeader('X-Frame-Options');
  res.render('widget');
});
```

여기서 자주 실수하는 게, 위쪽 공통 미들웨어에서 `X-Frame-Options: DENY`를 박아놓고 `/widget`에서 frame-ancestors만 바꾸는 경우다. 그러면 X-Frame-Options DENY가 그대로 남아서 파트너 임베드가 여전히 차단된다. 위 코드처럼 해당 라우트에서 X-Frame-Options를 제거해야 한다.

### helmet 사용

helmet을 쓰면 헤더를 일관되게 관리할 수 있다. helmet은 기본으로 `X-Frame-Options: SAMEORIGIN`을 설정한다.

```javascript
const helmet = require('helmet');

app.use(
  helmet({
    // X-Frame-Options를 DENY로 (기본은 SAMEORIGIN)
    frameguard: { action: 'deny' },
    contentSecurityPolicy: {
      directives: {
        'frame-ancestors': ["'none'"],
      },
    },
  })
);
```

helmet의 기본 CSP에는 `frame-ancestors`가 `'self'`로 들어있다. 위처럼 명시적으로 `'none'`을 주거나, 아니면 기본값을 유지하려면 directives를 통째로 덮어쓰지 않게 조심한다. `useDefaults`가 켜진 상태(기본)에서 일부 디렉티브만 덮어쓰면 나머지는 helmet 기본값이 유지된다.

## Nginx 헤더 설정

리버스 프록시 단에서 한 번에 거는 방법이 운영하기 편하다. 애플리케이션을 안 건드리고 전체 응답에 헤더가 붙는다.

```nginx
server {
    listen 443 ssl;
    server_name app.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;

        # always를 붙여야 4xx/5xx 응답에도 헤더가 붙는다
        add_header X-Frame-Options "DENY" always;
        add_header Content-Security-Policy "frame-ancestors 'none'" always;
    }
}
```

`always`가 핵심이다. 안 붙이면 200 응답에만 헤더가 나가고, 404나 500 에러 페이지에는 안 붙는다. 에러 페이지도 iframe에 띄울 수 있으니 always를 꼭 넣는다.

### add_header 상속 함정

Nginx에서 가장 많이 당하는 부분이다. `add_header`는 같은 블록 레벨에서 하나라도 새로 선언하면, 상위 블록에서 선언한 add_header가 전부 무시된다. 상속이 누적이 아니라 덮어쓰기다.

```nginx
server {
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "frame-ancestors 'none'" always;

    location /api {
        # 여기서 add_header를 새로 선언하면
        # 위 server 블록의 두 add_header가 /api에선 전부 사라진다
        add_header Cache-Control "no-store" always;
    }
}
```

위 설정에서 `/api` 경로는 X-Frame-Options와 CSP 헤더가 안 나간다. `/api`에서 Cache-Control을 추가하는 순간 상위 add_header가 날아간 거다. 해결은 location 안에서 필요한 헤더를 전부 다시 선언하는 거다.

```nginx
location /api {
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "frame-ancestors 'none'" always;
    add_header Cache-Control "no-store" always;
}
```

include 파일로 공통 헤더를 묶어두고 각 location에서 `include`하는 방식이 관리하기 낫다.

```nginx
# /etc/nginx/snippets/security-headers.conf
add_header X-Frame-Options "DENY" always;
add_header Content-Security-Policy "frame-ancestors 'none'" always;
```

```nginx
location /api {
    include snippets/security-headers.conf;
    add_header Cache-Control "no-store" always;
}
```

### 백엔드가 보낸 헤더와 중복

또 하나 흔한 문제. 백엔드(Express 등)에서 이미 X-Frame-Options를 보내는데 Nginx에서도 add_header로 추가하면, 응답에 같은 헤더가 두 번 나갈 수 있다. 브라우저가 둘을 어떻게 처리할지는 헤더마다 다르고, X-Frame-Options가 중복되면 브라우저가 "둘 다 만족해야 한다"로 보거나 아예 무효 처리하는 경우가 있다. 헤더는 한 군데서만 책임지고 거는 게 맞다. 보통은 프록시 단으로 통일하고 애플리케이션에선 빼거나, 반대로 애플리케이션에서만 걸고 프록시는 안 건드린다.

`proxy_pass`로 백엔드 헤더를 그대로 전달하면서 프록시에서 add_header를 또 하면 중복이 잘 생긴다. 백엔드 헤더를 지우고 프록시에서만 걸려면 `proxy_hide_header`를 쓴다.

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;

    # 백엔드가 보낸 헤더를 숨기고
    proxy_hide_header X-Frame-Options;
    proxy_hide_header Content-Security-Policy;

    # 프록시에서만 건다
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "frame-ancestors 'none'" always;
}
```

## 응답 헤더 검증 트러블슈팅

헤더를 걸었으면 실제로 나가는지 확인해야 한다. 설정만 하고 검증 안 하면 위의 상속 함정이나 중복 때문에 막상 안 나가는 경우가 흔하다.

`curl -I`로 응답 헤더만 본다.

```bash
curl -I https://app.example.com/

# 출력 예시에서 아래 두 줄이 있어야 한다
# X-Frame-Options: DENY
# Content-Security-Policy: frame-ancestors 'none'
```

`-I`는 HEAD 요청이라 서버가 GET과 HEAD에서 헤더를 다르게 줄 수도 있다. 정확히 보려면 GET으로 헤더만 뽑는다.

```bash
curl -sS -D - -o /dev/null https://app.example.com/
```

에러 페이지에도 헤더가 붙는지 확인한다. always 누락을 여기서 잡는다.

```bash
# 일부러 없는 경로를 쳐서 404 응답 헤더 확인
curl -I https://app.example.com/this-path-does-not-exist
```

헤더가 중복으로 나가는지도 본다. 같은 헤더가 두 줄이면 프록시와 백엔드가 동시에 걸고 있는 거다.

```bash
curl -sS -D - -o /dev/null https://app.example.com/ | grep -i x-frame-options
# X-Frame-Options: DENY 가 두 줄 나오면 중복. 한 곳으로 정리해야 한다
```

자주 마주치는 증상과 원인:

- **헤더가 아예 안 나감**: Nginx location에서 다른 add_header를 선언해 상위 블록 헤더가 무시됐다. 해당 location에 헤더를 다시 선언하거나 include로 묶는다.
- **200에선 나오는데 404/500에선 안 나옴**: `always` 누락. add_header에 always를 붙인다.
- **헤더가 두 번 나옴**: 프록시와 애플리케이션이 둘 다 건다. 한 곳으로 정리하고 다른 쪽은 `proxy_hide_header`로 지운다.
- **frame-ancestors는 있는데 iframe이 여전히 차단**: 같이 보낸 X-Frame-Options가 DENY/SAMEORIGIN이라 우선 적용됐다. 다중 출처를 허용하려면 그 라우트에서 X-Frame-Options를 빼야 한다.
- **`<meta>`로 넣었는데 안 먹힘**: X-Frame-Options와 frame-ancestors는 HTTP 응답 헤더로만 동작한다. meta 태그는 무시된다.

브라우저 개발자도구의 Network 탭에서 해당 문서 요청의 Response Headers를 봐도 된다. 그리고 실제로 클릭재킹이 막히는지 확인하려면, 로컬에 테스트용 HTML을 만들어 우리 페이지를 iframe으로 띄워본다. 차단되면 콘솔에 `Refused to display ... in a frame because it set 'X-Frame-Options' to 'deny'` 또는 CSP frame-ancestors 위반 메시지가 찍힌다.

```html
<!-- iframe-test.html — 로컬에서 열어 차단 여부 확인 -->
<!DOCTYPE html>
<html>
<body>
  <h1>iframe 임베드 테스트</h1>
  <iframe src="https://app.example.com/" width="600" height="400"></iframe>
</body>
</html>
```

이 파일을 브라우저로 열었을 때 iframe 영역이 비어 있고 콘솔에 거부 메시지가 뜨면 정상적으로 막힌 거다. 페이지가 그대로 보이면 헤더가 안 걸렸거나 정책이 임베드를 허용한 상태다.

## 정리

방어 우선순위는 분명하다. CSP `frame-ancestors`를 1차로 걸고, 오래된 브라우저 호환을 위해 X-Frame-Options를 같이 보낸다. 두 헤더 정책은 모순 없이 맞춘다. 세션 쿠키는 `SameSite=Lax` 이상으로 설정해 임베드 맥락에서 세션이 안 붙게 한다. frame-busting 스크립트는 헤더를 못 거는 환경의 보조 수단일 뿐, 단독 방어로 신뢰하지 않는다. 마지막으로 설정 후 `curl -I`로 200·404·에러 페이지 모두에서 헤더가 나가는지, 중복은 없는지 검증한다. Nginx의 add_header 상속 덮어쓰기와 always 누락이 실무에서 가장 자주 헤더를 누락시키는 원인이다.
