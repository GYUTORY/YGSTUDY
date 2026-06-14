---
title: JavaScript Truthy와 Falsy
tags: [language, javascript, 09es6및고급문법, truthy, falsy, boolean-conversion]
updated: 2026-06-14
---

# JavaScript Truthy와 Falsy

## 정의

JavaScript는 조건문이나 논리 연산자에 들어온 값을 boolean이 아니어도 boolean으로 변환해서 판단한다. 이때 `true`로 변환되는 값을 truthy, `false`로 변환되는 값을 falsy라고 부른다.

falsy로 평가되는 값은 정확히 8가지뿐이다. 나머지는 전부 truthy다. 이 8개만 외우면 된다.

```javascript
const falsyValues = [
    false,      // boolean false
    0,          // 숫자 0
    -0,         // 음수 0
    0n,         // BigInt 0
    '',         // 빈 문자열
    null,       // null
    undefined,  // undefined
    NaN         // Not a Number
];

falsyValues.forEach(value => {
    console.log(value, '→ falsy:', !value); // 전부 true
});
```

여기서 사고가 나는 지점은 "falsy처럼 보이는데 truthy인 값"이다. 실무에서 터지는 버그는 거의 다 이쪽이다.

```javascript
if ('0') console.log('문자열 "0"은 truthy');     // 실행됨
if (' ') console.log('공백 한 칸도 truthy');      // 실행됨
if ('false') console.log('문자열 "false"도 truthy'); // 실행됨
if ([]) console.log('빈 배열도 truthy');          // 실행됨
if ({}) console.log('빈 객체도 truthy');          // 실행됨
```

빈 배열과 빈 객체가 truthy라는 건 다른 언어 쓰다 온 사람이 가장 많이 틀리는 부분이다. Python에서 `if []`는 false지만 JavaScript에서는 true다.

## `||` 기본값 패턴이 만드는 버그

`name || '손님'` 같은 기본값 패턴은 오래 써왔지만 함정이 있다. `||`는 왼쪽이 falsy면 오른쪽을 반환한다. 문제는 falsy가 8개나 된다는 점이다. `0`, `''`, `false`도 falsy라서, 이 값들이 유효한 입력일 때 의도치 않게 기본값으로 덮인다.

```javascript
function createUser(input) {
    return {
        name: input.name || '이름 없음',
        age: input.age || 20,        // 나이 0이면 20으로 덮임
        retryCount: input.retryCount || 3, // 0번 재시도가 3번이 됨
        isAdmin: input.isAdmin || true     // false가 true로 뒤집힘
    };
}

console.log(createUser({ name: '', age: 0, retryCount: 0, isAdmin: false }));
// { name: '이름 없음', age: 20, retryCount: 3, isAdmin: true }
// 입력값을 하나도 안 살림
```

`age: 0`은 유효한 나이일 수 있고, `retryCount: 0`은 "재시도 안 함"이라는 명확한 의도다. `isAdmin: false`를 `true`로 뒤집는 건 권한 버그라 더 심각하다. 그런데 `||`는 셋 다 falsy로 보고 오른쪽 값으로 갈아치운다.

이럴 때 `??`(nullish coalescing)로 바꿔야 한다. `??`는 falsy 8개가 아니라 `null`과 `undefined` 두 개일 때만 오른쪽을 반환한다.

```javascript
function createUser(input) {
    return {
        name: input.name ?? '이름 없음',
        age: input.age ?? 20,
        retryCount: input.retryCount ?? 3,
        isAdmin: input.isAdmin ?? true
    };
}

console.log(createUser({ name: '', age: 0, retryCount: 0, isAdmin: false }));
// { name: '', age: 0, retryCount: 0, isAdmin: false }
// 입력값 그대로 보존, null/undefined만 기본값 적용
```

전환 기준은 단순하다. "0, 빈 문자열, false가 유효한 값인가?"를 따져서, 유효하면 `??`, 진짜로 비어있다고 보고 기본값을 넣고 싶으면 `||`를 쓴다. 숫자·boolean·사용자 입력 문자열은 거의 `??`가 맞다. 이름이 빈 문자열일 때 "이름 없음"으로 바꾸고 싶은 표시용 로직 정도가 `||`가 어울리는 경우다.

`??`는 `||`나 `&&`와 같은 줄에서 괄호 없이 섞으면 문법 에러가 난다. 의도를 명확히 하라는 의미라 괄호로 묶어야 한다.

```javascript
// const x = a || b ?? c;  // SyntaxError
const x = (a || b) ?? c;   // 괄호 필요
```

## `if (response.count)` — 0이 유효값인데 falsy로 빠지는 장애

실제로 겪은 장애 하나. 알림 개수를 내려주는 API 응답을 받아서 처리하는 코드였다.

```javascript
function renderBadge(response) {
    if (response.count) {
        showBadge(response.count);
    } else {
        hideBadge(); // 알림 없음으로 처리
    }
}
```

`count`가 0일 때 배지를 숨기는 게 맞으니 멀쩡해 보인다. 문제는 응답에 `count` 자체가 빠지는 경우(서버 에러로 필드 누락)와 `count: 0`(정상적으로 알림 0개)을 이 코드가 구분하지 못한다는 점이다. 둘 다 falsy라 같은 `else`로 빠진다.

진짜 사고는 그다음이었다. 어느 날 집계 로직이 바뀌면서 "처리 중"일 때 `count: 0`을 먼저 내려주고 나중에 갱신하는 구조가 됐다. `if (response.count)`가 0을 falsy로 보고 매번 `hideBadge()`를 호출하니, 실제 알림이 쌓여도 배지가 안 뜨는 상황이 생겼다. 0과 "값 없음"을 구분했어야 했다.

```javascript
function renderBadge(response) {
    // 필드 존재 여부와 값 0을 명확히 구분
    if (response.count == null) {
        return; // 응답 이상, 이전 상태 유지
    }
    if (response.count > 0) {
        showBadge(response.count);
    } else {
        hideBadge(); // count === 0, 진짜 알림 없음
    }
}
```

숫자는 `if (x)`로 검사하지 않는다. `x > 0`, `x != null`, `Number.isInteger(x)`처럼 무엇을 확인하려는지 명시한다. 0이 의미 있는 값인 도메인(개수, 잔액, 좌표, 인덱스, 온도)에서는 거의 항상 `if (x)`가 버그다.

## 빈 배열·빈 객체는 truthy — 컬렉션 비어있음 판별

`if (arr)`로 배열이 비었는지 확인하려는 코드를 종종 본다. 빈 배열은 truthy라 이 검사는 의미가 없다. `arr`이 존재하기만 하면 비었든 아니든 통과한다.

```javascript
const items = [];

if (items) console.log('빈 배열도 통과함'); // 실행됨

// 비어있음을 확인하려면 length를 본다
if (items.length === 0) console.log('비어있음'); // 실행됨
if (items.length) console.log('원소 있음');      // 빈 배열이면 length 0 → 실행 안 됨
```

객체는 더 골치 아프다. `{}`도 truthy고, 객체에는 `.length`가 없어서 `Object.keys()`로 키 개수를 봐야 한다. 그런데 객체가 `null`일 수 있으면 `Object.keys(null)`이 던지는 에러부터 막아야 한다.

```javascript
function isEmptyObject(obj) {
    // obj가 null/undefined면 Object.keys가 TypeError를 던진다
    return obj != null && Object.keys(obj).length === 0;
}

// 흔히 쓰는 가드 패턴
const hasData = obj && Object.keys(obj).length > 0;
```

`obj && Object.keys(obj).length` 패턴에서 한 가지 주의할 게 있다. 이 식의 결과는 boolean이 아니라 `obj`가 falsy면 그 falsy 값, 아니면 `length` 숫자다. boolean을 기대하고 어딘가 넘기면 또 다른 곳에서 0이 falsy로 터질 수 있다. boolean이 필요하면 `> 0`이나 `Boolean()`으로 명시적으로 닫는다.

```javascript
const obj = null;
console.log(obj && Object.keys(obj).length);       // null (boolean 아님)
console.log(!!(obj && Object.keys(obj).length));   // false (명시적 boolean)
```

## `document.all` — falsy인 예외 객체

falsy 8개에 들어가지 않는데 falsy로 동작하는 유일한 예외가 `document.all`이다. 객체인데 조건문에서 false로 평가된다. 표준 8개만 외운 사람을 당황시키는 함정이다.

```javascript
console.log(typeof document.all);  // 'undefined' (이것도 거짓말)
console.log(Boolean(document.all)); // false
if (document.all) {
    console.log('실행 안 됨'); // document.all은 객체인데 falsy
}
```

이건 옛날 IE 시절 `if (document.all)`로 브라우저를 분기하던 코드들이 너무 많아서, 그 코드들이 모던 브라우저에서 IE 분기를 타지 않도록 일부러 falsy로 만든 하위 호환 장치다. 실무에서 직접 마주칠 일은 거의 없지만, "falsy는 8개"라고 했는데 9개째가 있는 이유를 알아두면 좋다. 코드에서 `document.all`을 쓸 일은 없다.

## 래퍼 객체는 전부 truthy

`new Boolean(false)`, `new Number(0)`, `new String('')`처럼 생성자로 만든 래퍼 객체는 안에 falsy 값을 담고 있어도 truthy다. 객체이기 때문이다. 객체는 빈 객체조차 truthy니까 당연하지만, 코드만 보면 false 같아서 헷갈린다.

```javascript
const wrapped = new Boolean(false);

if (wrapped) {
    console.log('실행됨 — new Boolean(false)는 truthy'); // 실행됨
}

console.log(Boolean(new Boolean(false))); // true
console.log(Boolean(new Number(0)));      // true
console.log(Boolean(new String('')));     // true

// 안에 든 원시값을 꺼내야 falsy가 된다
console.log(wrapped.valueOf());           // false
```

그래서 `new Boolean()`은 쓰지 않는다. boolean이 필요하면 `Boolean(x)`(new 없이) 또는 `!!x`를 쓴다. JSON 파싱이나 외부 라이브러리에서 어쩌다 래퍼 객체가 흘러들어오면 항상 truthy라 조건 분기가 통째로 어긋난다.

## `==`와 truthy 평가는 다른 규칙이다

`if (x)`의 truthy 판정과 `x == false` 같은 느슨한 비교(`==`)는 변환 규칙이 다르다. 같은 값이 두 검사에서 반대로 나올 수 있어서 헷갈린다.

```javascript
// '0'은 truthy다
if ('0') console.log('"0"은 truthy'); // 실행됨

// 그런데 '' == false는 true다
console.log('' == false);   // true
console.log('0' == false);  // true  (?!)
console.log(0 == false);    // true
console.log([] == false);   // true  (빈 배열은 truthy인데 == false는 true)
```

`if ('0')`은 truthy 규칙으로 "문자열이 비어있지 않음 → true"를 본다. 반면 `'0' == false`는 양쪽을 숫자로 강제 변환해서 `0 == 0`을 본다. 두 평가가 서로 다른 경로를 타기 때문에 결과가 어긋난다.

`[] == false`가 true인 게 압권이다. 빈 배열은 if문에서 truthy인데, `== false` 비교에서는 `[]`가 `''`로, `''`가 `0`으로, `false`가 `0`으로 변환되어 `0 == 0` → true가 된다. truthy/falsy로 추론하면 절대 못 맞힌다.

결론은 `== false`, `== true` 같은 비교를 쓰지 않는 것이다. boolean 판단은 `if (x)`나 `if (!x)`로 하고, 값 비교는 `===`로 한다. `== false`는 도저히 직관으로 예측 못 하는 결과만 낳는다.

## JSON·폼 입력의 문자열 함정

서버에서 오는 JSON이나 HTML 폼에서 받는 값은 거의 다 문자열이다. 그리고 비어있지 않은 문자열은 무조건 truthy다. `'0'`, `'false'`, `'null'`, `'undefined'` 전부 truthy라 그대로 if문에 넣으면 의도와 정반대로 동작한다.

```javascript
// 폼 체크박스 값이 문자열 'false'로 들어온 경우
const formValue = 'false';

if (formValue) {
    console.log('체크 해제했는데 실행됨'); // 실행됨 — 'false'는 truthy
}

// 쿼리스트링에서 온 숫자
const page = '0'; // ?page=0
if (page) {
    console.log('0페이지인데 truthy로 통과'); // 실행됨
}
```

문자열로 온 boolean·숫자는 비교 전에 실제 타입으로 변환해야 한다. boolean은 `=== 'true'`로 명시 변환하고, 숫자는 `Number()`로 바꾼 뒤 판단한다.

```javascript
const isChecked = formValue === 'true';      // 명시적으로 'true'만 true
const pageNum = Number(page);                // '0' → 0
if (Number.isInteger(pageNum) && pageNum >= 0) {
    loadPage(pageNum); // 0페이지도 정상 처리
}
```

`JSON.parse('false')`는 boolean `false`를 주지만, 폼 input의 `.value`는 항상 문자열이라 `JSON.parse`를 안 거치면 `'false'` 문자열 그대로다. 어디서 온 값인지에 따라 타입이 다르니 if문에 넣기 전에 타입부터 확인하는 습관이 안전하다.

## `&&`/`||`의 반환값은 boolean이 아니다 — JSX의 0 노출 버그

`&&`와 `||`는 boolean을 돌려주지 않는다. 피연산자 자체를 그대로 반환한다. `&&`는 왼쪽이 falsy면 왼쪽 값을, 아니면 오른쪽 값을 준다. `||`는 그 반대다.

```javascript
console.log(0 && '실행 안 됨');   // 0   (boolean 아님)
console.log('a' && 'b');         // 'b'
console.log(0 || '기본값');       // '기본값'
console.log('a' || 'b');         // 'a'
console.log(null && foo());      // null (foo 호출 안 됨)
```

이 성질이 React JSX 조건부 렌더링에서 자주 사고를 낸다. `condition && <Component />`로 "조건이 참이면 렌더링" 패턴을 쓰는데, `condition`이 숫자 `0`이면 `&&`가 `0`을 반환하고 React는 `0`을 falsy로 무시하지 않고 화면에 텍스트 "0"으로 그려버린다.

```jsx
function CartIcon({ count }) {
    // count가 0이면 화면에 "0"이 그대로 노출된다
    return (
        <div>
            {count && <Badge>{count}</Badge>}
        </div>
    );
}
// count === 0 → {0 && <Badge/>} → 0 → React가 "0"을 렌더링
```

React가 렌더링을 건너뛰는 값은 `false`, `null`, `undefined`, `true`다. `0`과 `NaN`은 건너뛰지 않고 그대로 출력한다. `&&`가 0을 반환하니 화면에 0이 찍힌다. 빈 장바구니 아이콘 옆에 덩그러니 "0"이 떠 있는 버그가 이렇게 나온다.

해결은 왼쪽을 명확한 boolean으로 만드는 것이다.

```jsx
// 비교로 boolean을 강제
{count > 0 && <Badge>{count}</Badge>}

// 삼항으로 falsy 분기를 null로 닫기
{count ? <Badge>{count}</Badge> : null}

// 명시적 boolean 변환
{!!count && <Badge>{count}</Badge>}
```

`count > 0`이 가장 깔끔하다. 의도("개수가 있을 때만 표시")도 드러나고 0이 새지 않는다. JSX 안에서 `&&` 왼쪽에 숫자나 `.length`를 직접 넣는 건 항상 의심해야 한다. `arr.length && <List/>`도 배열이 비면 `0`을 그려서 같은 버그가 난다. `arr.length > 0 && ...`로 닫는다.

## 정리

falsy 8개(`false`, `0`, `-0`, `0n`, `''`, `null`, `undefined`, `NaN`)와 예외인 `document.all`을 빼면 전부 truthy다. 빈 배열·빈 객체·문자열 `'0'`·`'false'`·래퍼 객체가 truthy라는 걸 놓치면 버그가 난다.

실무에서 반복해서 터지는 지점은 정해져 있다. 0·빈 문자열·false가 유효한 값인데 `||`나 `if (x)`로 falsy 취급해서 덮거나 건너뛰는 경우다. 숫자는 `> 0`이나 `!= null`로, 컬렉션은 `.length`나 `Object.keys().length`로, 기본값은 `??`로, JSX 조건부는 `> 0`으로 닫는 습관이 이 버그들을 대부분 막는다.
