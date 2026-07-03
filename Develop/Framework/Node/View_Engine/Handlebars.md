---
title: Handlebars (.hbs)
tags:
  - Node.js
  - Express
  - View Engine
  - Handlebars
  - Template
updated: 2026-05-11
---

# Handlebars (.hbs)

## 정의와 위치

Handlebars는 Mustache 문법을 확장한 로직리스(logic-less) 템플릿 엔진이다. 서버에서 HTML을 렌더링하던 시절에 가장 많이 쓰던 엔진 중 하나로, 지금도 관리자 페이지나 이메일 템플릿, SSR이 필요한 일부 화면에서 자주 본다. React/Vue가 자리잡은 뒤로는 신규 프로젝트에서 비중이 줄었지만, 운영 중인 Express 기반 서비스에는 아직도 많이 남아 있다.

확장자는 보통 `.hbs`를 쓴다. `.handlebars`도 똑같이 동작하지만 6글자 vs 11글자 차이라 IDE에서 다루기 편하고 URL 라우팅 디버깅할 때 눈에 잘 들어와서 `.hbs`로 통일하는 팀이 많다. 둘은 완전히 같다. 단지 Express나 express-handlebars 설정에서 `extname` 옵션을 맞춰주기만 하면 된다. 두 확장자를 섞어 쓰면 한 명은 `.hbs`를, 다른 한 명은 `.handlebars`를 만들어서 결국 못 찾는 일이 생기니 처음에 하나로 고정한다.

Mustache가 "변수 치환과 섹션"만 하는 데 비해, Handlebars는 거기에 헬퍼(helper)와 파셜(partial), 그리고 `if`/`each`/`with`/`unless` 같은 빌트인 블록을 얹었다. 그래서 "Mustache 호환되는데 조금 더 쓸 만한 버전"이라고 보면 된다.

---

## 문법

### 표현식

가장 기본은 `{{변수}}` 형태다. 내부적으로 컨텍스트(현재 데이터 객체)에서 키를 찾아 출력한다.

```handlebars
<h1>{{title}}</h1>
<p>{{user.name}}님 안녕하세요.</p>
```

점(`.`)으로 객체 속성에 접근한다. `user.profile.email` 같은 깊은 경로도 그대로 쓸 수 있다. 키가 없으면 빈 문자열이 나오지 에러가 나지 않는다. 이 동작이 처음에는 편한데, 오타를 내도 조용히 빈 값으로 렌더링되어 운영에서 "왜 안 나오지?"로 한참 헤매는 원인이 된다.

`{{}}`로 출력하면 HTML이 이스케이프된다. 즉 `<script>` 같은 문자가 들어오면 `&lt;script&gt;`로 바뀐다. 의도적으로 HTML을 그대로 박고 싶을 때만 `{{{ }}}`(triple-stash)를 쓴다. 이 차이가 XSS의 갈림길이다(보안 절에서 다시 다룬다).

```handlebars
{{content}}       <!-- 이스케이프됨, 안전 -->
{{{content}}}     <!-- 원본 그대로, 위험할 수 있음 -->
```

### 빌트인 블록 헬퍼

#### `{{#if}}`와 `{{#unless}}`

```handlebars
{{#if user.isAdmin}}
  <a href="/admin">관리자</a>
{{else}}
  <a href="/login">로그인</a>
{{/if}}

{{#unless order.paid}}
  <span>결제 대기중</span>
{{/unless}}
```

조건은 "truthy/falsy" 기반인데, Handlebars의 truthy 판정이 자바스크립트와 미묘하게 다르다. 빈 배열 `[]`은 자바스크립트에서는 truthy지만 Handlebars의 `{{#if}}`에서는 falsy로 친다. 이 동작은 `each`와의 일관성을 위한 것인데, 배열이 비었는지 따로 검사하는 코드를 안 써도 돼서 편하다. 다만 `null` vs `undefined` vs `0` 같은 값에서 동작이 직관과 어긋날 때가 있어, 진짜 비교가 필요하면 커스텀 헬퍼로 처리한다.

`if`는 단순 truthy 체크만 한다. `{{#if a === b}}` 같은 비교 연산자는 기본 문법으로 못 쓴다. 이걸 모르고 `{{#if status == 'paid'}}` 같은 코드를 짰다가 "왜 항상 true냐"로 시간 날리는 경우가 흔하다. 비교가 필요하면 `eq` 같은 헬퍼를 직접 등록하거나 `handlebars-helpers` 라이브러리를 쓴다.

#### `{{#each}}`

배열 순회는 `each`로 한다.

```handlebars
<ul>
{{#each products}}
  <li data-index="{{@index}}">
    {{name}} - {{price}}원
  </li>
{{else}}
  <li>상품이 없습니다.</li>
{{/each}}
</ul>
```

`@index`, `@first`, `@last`, `@key`(객체 순회 시) 같은 특수 변수가 자동으로 제공된다. `else` 블록은 배열이 비었을 때 실행된다.

each 안에서 컨텍스트가 각 요소로 바뀐다. 즉 `{{name}}`은 `products[i].name`이다. 바깥 컨텍스트의 값을 참조하려면 `../`로 거슬러 올라가야 한다.

```handlebars
{{#each products}}
  <p>{{../currency}} {{price}}</p>
{{/each}}
```

`../`는 한 단계 위, `../../`는 두 단계 위다. 중첩이 깊어지면 가독성이 빠르게 나빠진다. 이럴 땐 컨트롤러에서 데이터를 평탄화해서 넘기는 편이 낫다.

#### `{{#with}}`

특정 객체로 컨텍스트를 바꾼다.

```handlebars
{{#with user.address}}
  <p>{{city}} {{street}}</p>
{{/with}}
```

`user.address.city`를 매번 쓰기 싫을 때 사용한다. with 블록 안에서 `this`는 `user.address`다. 실무에서는 의외로 잘 안 쓰게 된다. `{{user.address.city}}`로 직접 쓰는 게 코드 읽을 때 더 명확해서다.

### 파셜

파셜은 다른 템플릿 파일을 끼워 넣는 기능이다.

```handlebars
{{> header }}

<main>
  {{> productCard product=item }}
</main>

{{> footer }}
```

express-handlebars 환경에서는 `views/partials/header.hbs` 같은 식으로 파일을 두면 자동으로 이름이 잡힌다. 파셜에 명시적으로 컨텍스트를 넘길 수도 있고(`{{> productCard product=item }}`), 인자 없이 호출하면 현재 컨텍스트가 그대로 전달된다.

자주 하는 실수가 파셜 등록 시점 문제다. express-handlebars는 첫 요청 때 파셜 디렉토리를 스캔해서 캐싱한다. 서버 시작 후에 파셜 파일을 새로 추가하면 `partialsDir` 옵션을 다시 로드하기 전까지는 잡히지 않는다. 개발 중 nodemon이 잘못 동작하거나 워치 옵션을 꺼두면 `Missing partial "productCard"` 에러가 난다.

---

## Express 연동

가장 흔한 조합은 `express-handlebars`다. Express의 기본 view engine 인터페이스에 맞춰 만들어진 래퍼로, layout과 partials 처리가 깔끔하다.

```js
const express = require('express');
const { engine } = require('express-handlebars');
const path = require('path');

const app = express();

app.engine(
  'hbs',
  engine({
    extname: '.hbs',
    defaultLayout: 'main',
    layoutsDir: path.join(__dirname, 'views', 'layouts'),
    partialsDir: path.join(__dirname, 'views', 'partials'),
    helpers: {
      formatDate(date) {
        return new Date(date).toISOString().slice(0, 10);
      },
      eq(a, b) {
        return a === b;
      },
    },
  })
);

app.set('view engine', 'hbs');
app.set('views', path.join(__dirname, 'views'));

app.get('/', (req, res) => {
  res.render('home', {
    title: '홈',
    user: { name: '윤기' },
    products: [{ name: '키보드', price: 120000 }],
  });
});

app.listen(3000);
```

### 디렉토리 구조

전형적으로 이렇게 잡는다.

```
views/
  layouts/
    main.hbs          # 공용 레이아웃
    admin.hbs
  partials/
    header.hbs
    footer.hbs
    product/
      card.hbs        # 하위 디렉토리는 product/card 로 호출
  home.hbs
  product/
    list.hbs
    detail.hbs
```

레이아웃 파일은 보통 `{{{ body }}}`(triple-stash)로 페이지 내용을 박는다. 여기서 이스케이프되면 HTML이 통째로 텍스트로 박혀서 화면이 깨진다. body는 신뢰 가능한 컴파일 결과물이므로 triple-stash가 맞다.

```handlebars
<!-- views/layouts/main.hbs -->
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <title>{{title}}</title>
  </head>
  <body>
    {{> header}}
    <main>{{{ body }}}</main>
    {{> footer}}
  </body>
</html>
```

### 라우트별 레이아웃 교체

```js
res.render('admin/dashboard', {
  layout: 'admin',
  stats,
});
```

`layout: false`로 넘기면 레이아웃 없이 본문만 렌더링된다. 부분 렌더링이 필요한 AJAX 응답에서 자주 쓴다.

### Express 빌트인 캐싱

Express는 `NODE_ENV=production`이면 `view cache`를 자동으로 켠다. 개발 환경에서는 매 요청마다 템플릿을 다시 읽고 컴파일하니, 운영에 올렸을 때 첫 요청 직후부터 캐싱된 결과를 보게 된다. 이 동작 차이로 "로컬에선 됐는데 운영에선 이상하다"가 종종 생긴다. 운영 환경에서 캐싱을 일시적으로 끄고 싶다면 `app.set('view cache', false)`로 명시한다. 평소엔 켜둔다.

---

## 클라이언트 사이드 컴파일 vs 사전 컴파일

브라우저에서 Handlebars를 쓸 수도 있다. 이메일 미리보기, 동적 행 추가, 댓글 영역 같은 곳에서 가끔 쓴다.

런타임 컴파일은 이렇게 한다.

```html
<script src="https://cdn.jsdelivr.net/npm/handlebars@4/dist/handlebars.min.js"></script>
<script id="row-tpl" type="text/x-handlebars-template">
  <tr><td>{{name}}</td><td>{{price}}</td></tr>
</script>
<script>
  const source = document.getElementById('row-tpl').innerHTML;
  const tpl = Handlebars.compile(source);
  document.querySelector('tbody').innerHTML = tpl({ name: '키보드', price: 120000 });
</script>
```

이 방식은 컴파일러 자체(`handlebars.min.js`, 약 80KB+)를 클라이언트로 내려보낸다. 페이로드가 크다. 운영 페이지에서는 빌드 타임에 미리 컴파일한 함수만 내려보내는 게 정석이다.

사전 컴파일은 `handlebars` CLI로 한다.

```bash
npx handlebars src/templates -f dist/templates.js
```

이렇게 만들면 `Handlebars.templates['row']` 형태로 함수가 묶여 나오고, 클라이언트에는 `handlebars.runtime.min.js`(컴파일러 빠진 런타임, 약 20KB)만 내려보내면 된다. 페이로드가 1/4 수준으로 줄고, 컴파일 비용도 빌드 타임으로 이동한다.

```html
<script src="https://cdn.jsdelivr.net/npm/handlebars@4/dist/handlebars.runtime.min.js"></script>
<script src="/dist/templates.js"></script>
<script>
  const html = Handlebars.templates['row']({ name: '키보드', price: 120000 });
</script>
```

CLI 옵션 중 `-n`(네임스페이스)과 `-m`(소스맵), `-c`(commonjs 모듈) 정도가 자주 쓰인다. 헬퍼는 사전 컴파일에 포함되지 않는다. 런타임에서 별도로 `Handlebars.registerHelper(...)`를 호출해 등록해야 한다. 이걸 빼먹으면 `Missing helper: "..."` 에러가 난다.

---

## 보안: 이스케이프와 `{{{ }}}`의 XSS

Handlebars의 기본 동작은 모든 출력을 HTML 이스케이프하는 것이다. 그래서 사용자가 `<script>alert(1)</script>`를 입력해도 화면에는 그대로 텍스트로 보이고 실행되지 않는다.

문제는 triple-stash다. `{{{ html }}}`로 출력하면 이스케이프가 빠진다. 이 자리에 사용자 입력이 들어가는 순간 XSS다.

```handlebars
<!-- 절대 이렇게 쓰지 마라 -->
<div>{{{ userComment }}}</div>
```

WYSIWYG 에디터에서 입력받은 HTML을 그대로 보여주고 싶다는 요구가 자주 들어오는데, 이 경우 서버에서 DOMPurify나 sanitize-html로 한 번 거른 다음에 triple-stash로 출력한다. "프론트에서 어차피 거를 거니까" 같은 가정은 깨진다. 누가 API를 직접 호출해 데이터를 박을지 모른다.

레이아웃의 `{{{ body }}}`처럼 신뢰 가능한 출처(템플릿 엔진 자신이 만든 결과물)에만 triple-stash를 쓴다는 원칙을 세워두면 사고가 줄어든다.

또 하나, `SafeString`이라는 우회 경로가 있다. 커스텀 헬퍼에서 `new Handlebars.SafeString(html)`을 반환하면 이스케이프되지 않는다. 헬퍼 안에서 직접 만든 마크업을 출력할 때 쓰는데, 이때도 헬퍼 인자로 들어온 사용자 입력은 반드시 이스케이프하거나 sanitize한 뒤에 끼워 넣어야 한다.

```js
Handlebars.registerHelper('badge', function (label) {
  const safe = Handlebars.escapeExpression(label);
  return new Handlebars.SafeString(`<span class="badge">${safe}</span>`);
});
```

`escapeExpression`을 안 거치고 템플릿 리터럴에 그대로 박으면 그 자리가 XSS 구멍이다.

---

## 커스텀 헬퍼

비교 연산, 날짜 포맷, 통화 포맷, i18n 같은 흔한 작업은 헬퍼로 만든다.

```js
const helpers = {
  eq: (a, b) => a === b,
  ne: (a, b) => a !== b,
  gt: (a, b) => a > b,
  formatPrice(n) {
    return new Intl.NumberFormat('ko-KR').format(n) + '원';
  },
  formatDate(d, fmt) {
    // fmt가 인자로 안 넘어오면 마지막에 options 객체가 들어온다
    if (typeof fmt !== 'string') fmt = 'YYYY-MM-DD';
    return /* ... */;
  },
};
```

여기서 자주 막히는 게 두 가지다.

### 1. 마지막 인자는 항상 options 객체

Handlebars는 헬퍼를 호출할 때 마지막 인자로 `{ hash, fn, inverse, data, ... }` 형태의 options 객체를 끼워 넣는다. 인자 개수에 가변성이 있는 헬퍼를 만들 때 이걸 잊으면 이상한 일이 일어난다.

```handlebars
{{formatDate createdAt}}
{{formatDate createdAt 'YYYY-MM-DD HH:mm'}}
```

첫 번째 호출은 `formatDate(createdAt, options)`로 들어오고, 두 번째는 `formatDate(createdAt, 'YYYY-MM-DD HH:mm', options)`로 들어온다. 인자 개수로 분기해야 한다.

### 2. 컨텍스트(`this`) 손실

화살표 함수로 헬퍼를 등록하면 `this`가 템플릿 컨텍스트가 아니라 등록 시점의 외부 스코프를 가리킨다. Handlebars는 헬퍼의 `this`를 현재 컨텍스트로 바인딩하는 규약을 쓰는데, 화살표 함수는 이걸 무시한다.

```js
// 잘못된 예: this가 현재 컨텍스트가 아님
Handlebars.registerHelper('fullName', () => `${this.firstName} ${this.lastName}`);

// 올바른 예
Handlebars.registerHelper('fullName', function () {
  return `${this.firstName} ${this.lastName}`;
});
```

"왜 헬퍼 안에서 데이터가 안 나오지?"의 90%는 이 패턴이다. 인자로 명시적으로 받아 쓰는 습관을 들이면 헬퍼 시그니처도 명확해진다.

### 3. 블록 헬퍼

`{{#myBlock}} ... {{/myBlock}}` 형태는 options 객체의 `fn`, `inverse`를 호출해 내부 콘텐츠를 렌더링한다.

```js
Handlebars.registerHelper('ifEqual', function (a, b, options) {
  if (a === b) return options.fn(this);
  return options.inverse(this);
});
```

```handlebars
{{#ifEqual status 'paid'}}
  결제 완료
{{else}}
  결제 대기
{{/ifEqual}}
```

---

## 성능 이슈

### 매 요청 컴파일 금지

Handlebars의 컴파일 비용은 작지 않다. 큰 템플릿 하나당 수 ms씩 든다. 운영 트래픽에서 매 요청마다 `Handlebars.compile(source)`를 호출하면 CPU가 무의미하게 갈린다. express-handlebars는 기본적으로 컴파일 결과를 캐시한다(`NODE_ENV=production`일 때). 직접 Handlebars 라이브러리를 쓴다면 컴파일 결과를 모듈 스코프나 LRU 캐시에 보관해 재사용해야 한다.

```js
// 잘못된 예: 매 요청마다 컴파일
app.get('/mail/preview', (req, res) => {
  const source = fs.readFileSync('mail.hbs', 'utf8');
  const tpl = Handlebars.compile(source);
  res.send(tpl(req.body));
});

// 올바른 예: 모듈 로드 시 한 번만 컴파일
const mailTpl = Handlebars.compile(fs.readFileSync('mail.hbs', 'utf8'));
app.get('/mail/preview', (req, res) => {
  res.send(mailTpl(req.body));
});
```

### 파셜 미리 등록

운영 시작 시점에 파셜을 한 번에 등록해두면 첫 요청에서 발생하는 워밍업 비용이 사라진다. express-handlebars의 `partialsDir` 설정이 이걸 자동으로 해준다.

### 큰 each 루프

수천 건 데이터를 `{{#each}}`로 렌더링하면 문자열 연결 비용이 누적된다. 이 정도 규모는 보통 페이지네이션으로 잘라야 할 시점이다. 굳이 한 화면에 뿌려야 한다면 서버에서 미리 HTML을 만들어 캐시(Redis 등)해두는 편이 낫다.

---

## .hbs vs .handlebars

기능 차이 없다. 단순한 파일 확장자 차이다. express-handlebars 설정에서 `extname: '.hbs'`로 지정하면 `.hbs` 파일을 찾고, `.handlebars`로 지정하면 그쪽을 찾는다. `res.render('home')`을 호출할 때 어느 확장자로 잡아야 하는지 결정하는 옵션이다.

운영 중 한 디렉토리에 두 확장자가 섞이면 IDE 검색, ESLint/Prettier 설정, 빌드 도구 매칭 등 모든 곳에서 패턴을 두 번씩 써야 한다. 새 프로젝트라면 처음부터 `.hbs`로 통일한다.

---

## Mustache / EJS / Pug 와의 차이

### Mustache

Handlebars는 Mustache의 상위 호환이다. Mustache 템플릿은 거의 그대로 Handlebars에서 돈다. 차이는 두 가지다.

- Mustache는 `{{#section}}`이 truthy면 한 번, 배열이면 each처럼 반복하는 식으로 컨텍스트에 따라 동작이 갈린다. Handlebars는 `{{#if}}`와 `{{#each}}`를 분리해 의도를 분명히 한다.
- Mustache는 헬퍼/파셜 인자 같은 확장이 없다. "정말 로직 없는" 템플릿이 필요할 때만 Mustache를 쓴다.

### EJS

EJS는 템플릿 안에 자바스크립트를 그대로 박는다.

```ejs
<% if (user.isAdmin) { %>
  <a href="/admin">관리자</a>
<% } %>
<% products.forEach(p => { %>
  <li><%= p.name %></li>
<% }) %>
```

자바스크립트 풀파워라 자유롭지만, 그만큼 템플릿에 비즈니스 로직이 새어 들어가기 쉽다. Handlebars는 의도적으로 표현력을 좁혀서 템플릿을 단순하게 유지한다. 트레이드오프다.

EJS의 `<%= %>`는 이스케이프, `<%- %>`는 raw다. Handlebars의 `{{}}` vs `{{{}}}`와 대응된다.

### Pug (구 Jade)

Pug는 들여쓰기 기반 문법이다.

```pug
doctype html
html
  head
    title= title
  body
    h1 안녕하세요 #{user.name}님
```

문법이 가장 다르다. HTML 작성량이 줄어드는 게 장점이지만, 디자이너/퍼블리셔와 협업하기 까다롭다. 기존 HTML을 가져와 변환해야 하는 부담이 있다. Handlebars는 HTML을 그대로 두고 `{{}}`만 추가하는 방식이라 디자이너가 만든 HTML을 거의 손대지 않고 변환할 수 있다. 외주/대행 작업이 많은 프로젝트에서 Handlebars가 선호되는 이유다.

---

## 실제 트러블슈팅 사례

### 헬퍼 컨텍스트 손실 (this가 비어 있음)

증상: 헬퍼 안에서 `this.user`를 찍는데 `undefined`만 나온다.

원인 후보:
1. 헬퍼를 화살표 함수로 등록했다.
2. `each` 안에서 호출했는데 현재 컨텍스트가 배열 요소라 `this.user`가 없다.
3. 파셜에 명시적 컨텍스트(`{{> mypartial user=u}}`)를 넘기지 않고 호출했다.

해결: 화살표 함수 대신 일반 함수로 등록하고, 헬퍼는 가급적 `this`에 의존하지 말고 인자로 명시적으로 받는다. 그러면 호출 시점에서 컨텍스트가 보여 디버깅하기 쉽다.

### `Missing partial "xxx"` 에러

증상: 운영 배포 후 일부 페이지에서 partial을 못 찾는다.

원인 후보:
1. 빌드 시 `views/partials/` 디렉토리가 통째로 누락됨(도커 `COPY` 누락, `.dockerignore` 룰 잘못).
2. 파일명 대소문자 차이. macOS 로컬은 case-insensitive지만 리눅스 컨테이너는 case-sensitive다. `ProductCard.hbs`를 만들고 `{{> productCard }}`로 호출하면 로컬은 되고 운영은 깨진다.
3. 사전 컴파일 환경에서 런타임에 `Handlebars.registerPartial`을 호출하지 않음.

해결: CI 빌드 단계에서 `views/partials/` 디렉토리 존재 여부를 한 줄 체크 스텝으로 넣는다. 파일명 컨벤션은 소문자-하이픈으로 통일한다(`product-card.hbs`).

### 레이아웃이 적용되지 않음

증상: `res.render('home')` 결과에 `<html>` 골격이 없다. body만 나온다.

원인 후보:
1. `defaultLayout` 옵션을 지정하지 않았거나 파일명 오타.
2. `layoutsDir` 경로가 잘못됨. 로컬에서 상대 경로를 썼는데 작업 디렉토리가 달라져 잡히지 않음.
3. 라우트에서 `layout: false`를 넘김(부분 렌더링용으로 추가했다가 잊은 케이스).
4. 레이아웃 파일에 `{{{ body }}}`가 빠짐. 이 경우 레이아웃은 적용되지만 본문이 안 보인다.

해결: `engine()` 호출 시 `defaultLayout`과 `layoutsDir`을 `path.join(__dirname, ...)`으로 절대 경로로 고정한다. 레이아웃이 적용은 됐는데 본문이 안 보이는 거라면 `{{{ body }}}`를 먼저 의심한다(`{{ body }}`로 이스케이프되면 HTML 소스가 텍스트로 박힌다).

### "왜 항상 false / 항상 true가 나오지"

증상: `{{#if status == 'paid'}}`로 분기했는데 상태에 관계없이 같은 분기만 탄다.

원인: `{{#if}}`는 비교 연산자를 지원하지 않는다. `status == 'paid'`라는 문자열 전체를 truthy로 평가해버린다(보통은 헬퍼 인자로 해석해 다른 동작이 나는데, 결과적으로 의도와 어긋난다).

해결: 비교 헬퍼를 등록한다.

```js
Handlebars.registerHelper('eq', (a, b) => a === b);
```

```handlebars
{{#if (eq status 'paid')}}
  결제 완료
{{/if}}
```

서브 표현식(괄호)을 쓰면 한 줄에 여러 헬퍼를 연쇄할 수 있다. `{{#if (and (eq a 1) (eq b 2))}}` 같은 식이다.

### 사전 컴파일한 템플릿이 `Missing helper` 에러를 낸다

증상: 빌드 후 `dist/templates.js`를 로드했는데 페이지에서 `Missing helper: "formatPrice"`가 뜬다.

원인: CLI로 사전 컴파일한 결과물은 헬퍼를 포함하지 않는다. 클라이언트 코드에서 따로 `Handlebars.registerHelper('formatPrice', ...)`로 등록해야 한다.

해결: 헬퍼 모듈을 별도 번들로 빼서 런타임 직후에 로드한다.

```html
<script src="/dist/handlebars.runtime.min.js"></script>
<script src="/dist/helpers.js"></script> <!-- registerHelper 호출 -->
<script src="/dist/templates.js"></script>
```

### 운영 환경에서만 템플릿 변경이 반영 안 됨

증상: `.hbs` 파일을 수정했는데 운영에선 옛날 화면이 그대로 보인다.

원인: Express의 `view cache`가 켜진 상태에서 프로세스를 재기동하지 않았다. PM2/도커 환경에서 코드 배포는 됐는데 무중단 리로드가 의도대로 안 도는 경우다.

해결: 배포 스크립트에서 프로세스 재시작이 정상적으로 이뤄지는지 확인한다. `pm2 reload`가 메모리에 올라간 컴파일된 함수를 새로 읽지는 않는다(.hbs 파일은 read 시점에 캐시된다). 정적 자산처럼 다뤄야 한다.

---

## 정리

Handlebars는 표현력을 의도적으로 좁힌 템플릿 엔진이다. EJS만큼 자유롭진 않지만, 그 제약이 템플릿을 단순하게 유지하는 데 도움이 된다. 신규 SSR 프로젝트라면 Next.js/Remix 같은 컴포넌트 기반 도구로 가는 게 일반적이지만, 이메일 템플릿, 운영 도구, 레거시 유지보수에서 Handlebars는 여전히 현실적인 선택지다.

작업할 때 가장 자주 마주치는 함정은 헬퍼 컨텍스트(`this`), 비교 연산자 부재, triple-stash로 인한 XSS, 사전 컴파일 시 헬퍼 누락, 운영/개발의 캐싱 동작 차이다. 이 다섯 가지만 의식하고 시작해도 운영 사고가 크게 줄어든다.
