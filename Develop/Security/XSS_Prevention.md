---
title: XSS 방어 실무
tags: [security, frontend, web-server]
updated: 2026-09-22
---

# XSS 방어 실무

[공격 원리](XSS.md)와 별개로 방어는 층위가 다르다. 입력 시점 검증, 출력 시점 이스케이프, 브라우저 정책(CSP), 라이브러리 sanitize까지 네 줄이 겹쳐 있어야 한 줄이 뚫려도 나머지가 버텨낸다. 하나만 믿으면 반드시 뚫린다.

---

## Stored / Reflected / DOM XSS별 막는 지점이 다르다

세 유형은 공격 경로가 달라서 방어 위치도 달라진다.

**Stored XSS** — 서버 DB에서 나오는 데이터가 HTML로 렌더링될 때 발생한다. 막는 위치는 두 곳이다. 저장 전 sanitize(악성 태그 제거)하거나, 출력 시 HTML 이스케이프해서 브라우저가 마크업으로 해석하지 못하게 막는다. 댓글, 게시글 본문, 사용자 프로필 소개란이 주된 공격 지점이다.

**Reflected XSS** — 쿼리 파라미터, 폼 데이터를 서버가 응답에 그대로 반영할 때 발생한다. 서버 템플릿에서 변수를 자동 이스케이프하는 것이 첫 번째 방어선이다. Jinja2는 `{{ value }}`가 기본으로 이스케이프한다. `{{ value | safe }}` 같은 필터를 붙이는 순간 방어가 사라진다.

**DOM XSS** — 서버를 거치지 않는다. `location.hash`, `document.referrer`, `postMessage` 같은 브라우저 API에서 읽은 값을 `innerHTML`로 쓸 때 발생한다. 서버 측 이스케이프가 전혀 도움이 되지 않는다. 클라이언트 코드에서 직접 막아야 한다.

```javascript
// DOM XSS — 서버와 무관하게 발생
const name = new URLSearchParams(location.search).get('name');
document.getElementById('greeting').innerHTML = 'Hello, ' + name; // 위험

// ?name=<img src=x onerror=alert(1)> 로 공격 가능
```

---

## innerHTML 대신 textContent를 쓰는 이유

`innerHTML`은 문자열을 HTML 파서가 처리한다. `<script>alert(1)</script>` 를 넣으면 파서가 태그로 인식한다. 반면 `textContent`는 문자열 전체를 텍스트 노드로 만든다. 태그 문자 자체가 화면에 그대로 출력된다.

```javascript
const el = document.getElementById('output');

// 위험 — HTML 파서가 처리
el.innerHTML = userInput;

// 안전 — 텍스트 노드로 처리, 태그가 화면에 문자로 표시됨
el.textContent = userInput;
```

단순 텍스트를 표시하는 경우라면 `textContent`로 충분하다. 문제는 사용자가 입력한 내용에 볼드·이탤릭·링크 같은 서식을 허용해야 하는 경우다. 그때 `innerHTML`을 쓰고 싶어지는데, 그 판단을 내리는 순간 sanitize 라이브러리 없이는 안전하지 않다.

`innerHTML`이 아예 필요 없는 곳에서 쓰이는 경우도 많다. `element.innerHTML = '<b>' + name + '</b>'` 처럼 동적으로 태그를 만드는 코드는 `createElement` + `appendChild`로 대체하면 된다.

```javascript
// innerHTML 쓰던 코드
container.innerHTML = '<b>' + userName + '</b>';

// DOM API로 대체
const bold = document.createElement('b');
bold.textContent = userName; // 사용자 입력은 textContent로
container.appendChild(bold);
```

---

## DOMPurify — 클라이언트 sanitize

사용자가 입력한 HTML을 그대로 렌더링해야 할 때 DOMPurify를 쓴다. 허용 태그 목록을 기반으로 위험한 속성과 이벤트 핸들러를 제거한다.

```javascript
import DOMPurify from 'dompurify';

// 기본 사용
const clean = DOMPurify.sanitize(dirtyHTML);
document.getElementById('output').innerHTML = clean;

// 허용 태그를 제한하고 싶을 때
const clean = DOMPurify.sanitize(dirtyHTML, {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'ul', 'li'],
  ALLOWED_ATTR: ['href', 'title'],
});

// href에 javascript: 프로토콜 차단 — 기본값이라 명시 안 해도 되지만 확인용
const clean = DOMPurify.sanitize(dirtyHTML, {
  FORBID_ATTR: ['onerror', 'onload', 'onclick'],
});
```

DOMPurify의 기본 설정은 꽤 엄격하다. `<script>`, `<iframe>`, 이벤트 핸들러 속성을 전부 제거한다. `javascript:` 프로토콜도 차단한다. 기본 설정에서 허용 태그를 줄이는 방향으로 쓰는 것이 맞다. 반대로 기본보다 더 허용하는 설정을 추가하는 것은 신중해야 한다.

주의할 점은 DOMPurify가 클라이언트 전용이라는 것이다. SSR(서버사이드 렌더링) 환경에서 서버 코드에 `require('dompurify')`를 그냥 쓰면 동작하지 않는다. `jsdom`과 같이 써야 한다.

```javascript
// Node.js 환경에서 DOMPurify 사용할 때
const createDOMPurify = require('dompurify');
const { JSDOM } = require('jsdom');
const window = new JSDOM('').window;
const DOMPurify = createDOMPurify(window);

const clean = DOMPurify.sanitize(dirtyHTML);
```

---

## sanitize-html — 서버 사이드 sanitize

Node.js 서버에서 HTML을 sanitize할 때 `sanitize-html`을 쓴다. 허용 태그와 속성을 명시적으로 지정하고, 나머지는 전부 제거한다.

```javascript
const sanitizeHtml = require('sanitize-html');

const clean = sanitizeHtml(dirty, {
  allowedTags: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
  allowedAttributes: {
    'a': ['href', 'title', 'target'],
  },
  // href에 javascript: 허용하지 않음
  allowedSchemes: ['http', 'https', 'mailto'],
  allowedSchemesByTag: {
    'a': ['http', 'https', 'mailto'],
  },
});
```

`allowedTags`에 아무것도 없으면 모든 태그를 제거한다. 태그만 제거하고 내용은 남긴다는 점을 기억해야 한다. `<script>alert(1)</script>`를 sanitize하면 `<script>` 태그만 제거되고 `alert(1)`은 텍스트로 남는다. 이 동작이 기대와 다를 수 있으니 확인이 필요하다.

`disallowedTagsMode: 'discard'`로 태그와 내용 모두 제거할 수 있다.

```javascript
const clean = sanitizeHtml(dirty, {
  allowedTags: [],
  disallowedTagsMode: 'discard', // 태그와 내용 모두 제거
});
```

---

## CSP 헤더 설정

CSP(Content Security Policy)는 브라우저에게 어떤 출처의 리소스를 실행할 수 있는지 알려주는 HTTP 헤더다. XSS 공격이 삽입에 성공해도 브라우저가 실행을 거부하면 피해가 없다.

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'
```

각 지시어가 하는 일:

- `default-src 'self'` — 별도 지정 없는 리소스는 같은 출처만 허용
- `script-src 'self'` — 스크립트는 같은 출처만. 인라인 스크립트 차단
- `object-src 'none'` — `<object>`, `<embed>`, `<applet>` 전부 차단. Flash 시대 유물이지만 명시하는 것이 좋다
- `base-uri 'self'` — `<base>` 태그로 상대 URL 기준을 바꾸는 공격 차단

`script-src`에서 가장 자주 실수하는 부분이 `'unsafe-inline'`이다. 인라인 스크립트를 허용하면 XSS 공격으로 삽입된 `<script>` 태그도 실행되므로 CSP의 의미가 상당히 퇴색된다. 레거시 코드 때문에 `'unsafe-inline'`을 추가하고 싶은 경우가 생기는데, 그 대신 nonce를 쓰는 것이 낫다.

```
Content-Security-Policy: script-src 'self' 'nonce-랜덤값'
```

```html
<!-- 응답마다 새 랜덤값을 nonce로 -->
<script nonce="랜덤값">
  // 이 스크립트만 실행 허용
</script>
```

nonce는 요청마다 다른 랜덤값이어야 한다. 고정값을 쓰면 공격자가 그 값을 알고 인라인 스크립트에 붙여 우회한다.

**CSP 배포 전 테스트 방법** — `Content-Security-Policy-Report-Only` 헤더를 먼저 쓴다. 차단하지 않고 위반만 보고한다.

```
Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-report
```

`/csp-report`로 들어오는 요청을 수집해 실제 차단이 발생할 곳을 파악한 뒤 운영 헤더로 전환한다.

**Express에서 helmet으로 설정:**

```javascript
const helmet = require('helmet');

app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"], // 인라인 스타일이 있다면
    imgSrc: ["'self'", "data:"],
    objectSrc: ["'none'"],
    baseUri: ["'self'"],
    formAction: ["'self'"],
  },
}));
```

---

## React의 dangerouslySetInnerHTML

이름에 "dangerously"가 붙어 있는 이유가 있다. `dangerouslySetInnerHTML={{ __html: value }}`는 React의 자동 이스케이프를 우회하고 브라우저 `innerHTML`로 직접 넣는다.

```jsx
// React의 자동 이스케이프 — 안전
function Greeting({ name }) {
  return <div>Hello, {name}</div>; // <script>가 텍스트로 출력됨
}

// dangerouslySetInnerHTML — 이스케이프 없음
function RichContent({ html }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />; // 위험
}
```

`dangerouslySetInnerHTML`을 쓸 수밖에 없는 경우라면 반드시 DOMPurify로 sanitize한 값만 넣어야 한다.

```jsx
import DOMPurify from 'dompurify';

function RichContent({ html }) {
  const clean = DOMPurify.sanitize(html);
  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

CMS에서 가져온 HTML, 마크다운을 변환한 HTML이 이 경로를 타는 경우가 많다. 신뢰할 수 있는 출처라도 변환 과정에서 스크립트가 들어갈 수 있으니 sanitize를 생략하지 않는다.

---

## Vue의 v-html

Vue에서도 같은 문제가 있다. `v-html` 디렉티브는 `innerHTML`로 동작한다.

```vue
<!-- 자동 이스케이프 — 안전 -->
<template>
  <div>{{ userInput }}</div>
</template>

<!-- v-html — 이스케이프 없음 -->
<template>
  <div v-html="userInput"></div>
</template>
```

`v-html`과 DOMPurify를 같이 쓰는 방법:

```vue
<template>
  <div v-html="sanitized"></div>
</template>

<script>
import DOMPurify from 'dompurify';

export default {
  props: ['rawHtml'],
  computed: {
    sanitized() {
      return DOMPurify.sanitize(this.rawHtml);
    },
  },
};
</script>
```

Vue 3 Composition API 버전:

```vue
<template>
  <div v-html="sanitized"></div>
</template>

<script setup>
import { computed } from 'vue';
import DOMPurify from 'dompurify';

const props = defineProps(['rawHtml']);
const sanitized = computed(() => DOMPurify.sanitize(props.rawHtml));
</script>
```

`v-html`이 쓰인 컴포넌트를 코드 리뷰할 때 "이 값이 어디서 오는가"를 추적하는 것이 기본이다. 서버에서 오는 데이터라면 서버 쪽에서도 sanitize가 이미 됐는지 확인한다.

---

## 방어 층위 정리

방어 하나를 믿으면 안 된다는 점을 구체적으로 설명하면 이렇다.

서버 sanitize만 있을 때 — 클라이언트에서 API 응답을 `innerHTML`로 직접 쓰면 뚫린다.

CSP만 있을 때 — 잘못된 설정(`'unsafe-inline'` 허용, nonce 재사용)이나 JSONP 엔드포인트를 통한 우회가 가능하다.

프레임워크 자동 이스케이프만 믿을 때 — `dangerouslySetInnerHTML`, `v-html`, `bypassSecurityTrustHtml`(Angular) 중 하나라도 쓰는 순간 방어가 사라진다.

실제로 효과가 있었던 구성은 이렇다:

1. 서버 출력 — 템플릿 자동 이스케이프 활성화 (Jinja2 기본, Handlebars 기본)
2. DB 저장 전 — `sanitize-html`로 허용 태그만 남기고 저장
3. 클라이언트 렌더 — `innerHTML` 쓰는 곳에서 DOMPurify 통과 후 삽입
4. 브라우저 — CSP 헤더로 인라인 스크립트 차단, `Report-Only`로 먼저 테스트

4층이 다 있어도 각 층을 잘못 설정하면 의미 없다. 층 수보다 각 층이 제대로 동작하는지 확인하는 것이 먼저다.
