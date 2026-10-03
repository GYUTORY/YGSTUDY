---
title: 프로토타입 오염 - 환경설정 PATCH 한 번으로 다른 사용자가 관리자가 되는 경로
tags: [security, javascript, nodejs, backend]
updated: 2026-10-03
---

# 프로토타입 오염 - 환경설정 PATCH 한 번으로 다른 사용자가 관리자가 되는 경로

프로토타입 오염의 원리 자체는 한 문단이면 설명된다. `Object.prototype`에 속성을 심으면 모든 객체가 그 속성을 상속한다. 개념은 [보안 심화 및 취약점 분석](보안_심화_및_취약점_분석.md)에 정리돼 있다. 이 문서는 개념 대신 "내 코드가 실제로 터지는가"를 확인하는 방법에 집중한다. 실제로 돌려 보면 같은 페이로드가 어떤 병합 구현에서는 터지고 어떤 구현에서는 안 터지며, 흔히 권하는 방어책 중 몇 개는 조건이 맞아야만 동작한다. 환경은 Node.js 20.20.0이고, 라이브러리 수치는 npm에서 해당 버전을 직접 설치해 돌린 결과다.

## 요청 한 번으로 다른 사용자의 권한이 바뀐다

사용자별 환경설정을 PATCH로 받아 깊은 병합하는 서버다. 환경설정이라는 게 중첩 객체이기 때문에 `Object.assign` 대신 재귀 병합을 직접 짜거나 라이브러리를 쓰는 경우가 흔하다.

```javascript
// server.js - SAFE=1 이면 위험한 키를 건너뛴다
const http = require('http');
const SAFE = process.env.SAFE === '1';

function merge(target, src) {
  for (const key in src) {
    if (SAFE && (key === '__proto__' || key === 'constructor' || key === 'prototype')) continue;
    if (typeof src[key] === 'object' && src[key] !== null) {
      if (typeof target[key] !== 'object' || target[key] === null) target[key] = {};
      merge(target[key], src[key]);
    } else target[key] = src[key];
  }
  return target;
}

const users = { alice: { name: 'alice', prefs: {} }, bob: { name: 'bob', prefs: {} } };

http.createServer((req, res) => {
  const [, who, action] = req.url.split('/');              // /alice/prefs , /bob/admin
  const user = users[who];
  if (!user) { res.statusCode = 404; return res.end('no user\n'); }
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    if (action === 'prefs' && req.method === 'PATCH') {
      merge(user.prefs, JSON.parse(body));                  // 사용자 환경설정 병합
      return res.end('saved\n');
    }
    if (action === 'admin') {
      if (user.isAdmin) return res.end(`${who}: 관리자 화면\n`);
      res.statusCode = 403; return res.end(`${who}: 403\n`);
    }
    res.statusCode = 404; res.end();
  });
}).listen(3110);
```

alice가 자기 환경설정을 저장하는 척하면서 `__proto__` 키를 보낸다. 이후 bob이 관리자 화면에 접근해 본다.

```bash
curl -s -X PATCH -d '{"theme":"dark"}' localhost:3110/alice/prefs
curl -s -X PATCH -d '{"__proto__":{"isAdmin":true}}' localhost:3110/alice/prefs
curl -s -w 'http=%{http_code}\n' localhost:3110/bob/admin
```

```text
== SAFE=0
  bob /admin 전: http=403
  alice 정상 저장: saved
  alice 악성 저장: saved
  bob /admin 후: http=200
  본문: bob: 관리자 화면
== SAFE=1
  bob /admin 전: http=403
  alice 정상 저장: saved
  alice 악성 저장: saved
  bob /admin 후: http=403
  본문: bob: 403
```

alice는 자기 환경설정에만 쓴 것처럼 보이고 응답도 `saved`로 똑같다. 그런데 bob의 권한 판정이 바뀌었다. `user.isAdmin`은 bob 객체에 정의된 적이 없으니 프로토타입 체인을 타고 올라가고, `Object.prototype.isAdmin`이 `true`이기 때문이다. 오염은 프로세스가 재시작될 때까지 남는다. 서버를 그대로 두면 이후 들어오는 모든 요청에서 `{}`로 만든 어떤 객체든 `isAdmin`이 참이다. 로그에는 PATCH 한 건과 정상 응답밖에 없어서 사후에 원인을 찾기도 어렵다.

JSON 본문의 `__proto__`가 왜 통과하느냐는 점도 짚고 가야 한다. `JSON.parse`는 `__proto__`를 특별 취급하지 않고 일반 own 속성으로 만든다. 코드에서 `{ __proto__: x }`라고 쓰면 프로토타입이 바뀌지만, JSON 텍스트에서 파싱된 `"__proto__"`는 그냥 문자열 키다.

```javascript
Object.keys(JSON.parse('{"__proto__": {"isAdmin": true}}'))   // [ '__proto__' ]
```

문제는 이 own 속성을 가진 객체를 병합 함수가 `for...in`이나 `Object.keys`로 훑는 순간, 키 이름이 `__proto__`인 소스 속성을 대상 객체에 읽고 쓰는 일이 생긴다는 것이다. 대상 객체에서 `target['__proto__']`를 읽으면 own 속성이 아니라 접근자(getter)를 통해 `Object.prototype` 자체가 돌아온다. 병합이 그 객체 안으로 재귀해 들어가면 쓰기가 전부 `Object.prototype`에 일어난다.

## 같은 페이로드가 어떤 병합에서는 안 터진다

병합 함수를 조금씩 다르게 짜서 같은 페이로드 두 개를 넣었다. 페이로드 하나는 `{"__proto__":{"hit":1}}`, 다른 하나는 `{"constructor":{"prototype":{"hit":1}}}`다. 객체인지 판단하는 방법만 다르다.

- M1: `typeof v === 'object' && v !== null`
- M2: `v instanceof Object`

각 칸은 새 Node 프로세스에서 실행해 앞 칸의 오염이 다음 칸에 번지지 않게 했다. "오염"은 병합 뒤 `({}).hit === 1`이 된 경우다.

| 병합 | 경로 | 방어 없음 | `__proto__`만 건너뜀 | 3개 키 건너뜀 | null 프로토타입 루트 | own일 때만 재귀 | reviver | `Object.freeze` | `--disable-proto=delete` |
|---|---|---|---|---|---|---|---|---|---|
| M1 | `__proto__` | 오염 | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 |
| M1 | `constructor.prototype` | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 |
| M2 | `__proto__` | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 | 안전 |
| M2 | `constructor.prototype` | 오염 | 오염 | 안전 | 안전 | 안전 | 오염 | 안전 | 오염 |

표에서 읽을 점이 몇 가지 있다.

1. 오염 경로는 병합 구현에 따라 다르다. M1은 `__proto__` 경로로만 뚫린다. `target.constructor`가 함수여서 `typeof`가 `'function'`이 되므로 재귀하지 않고 `{}`로 덮어쓰기 때문이다. M2는 반대로 `__proto__` 경로가 안전하다. `Object.prototype instanceof Object`가 `false`이기 때문에 역시 `{}`로 대체된다. 그런데 `Object`(함수)는 `instanceof Object`가 참이라 `constructor.prototype` 경로로 `Object.prototype`까지 재귀해 들어간다.
2. 그래서 "`__proto__`만 막는다"는 방어는 M2 구현에서 소용이 없다. 위 표에서 M2의 `__proto__만 건너뜀` 열이 `constructor.prototype`에서 여전히 오염인 이유다. 3개 키(`__proto__`, `constructor`, `prototype`)를 다 건너뛰면 막힌다.
3. JSON.parse의 `reviver`로 `__proto__`만 지워도 같은 문제가 생긴다. reviver 열을 보면 M2의 `constructor.prototype`은 그대로 뚫린다.
4. `node --disable-proto=delete`는 `Object.prototype.__proto__` 접근자를 지울 뿐이다. `constructor.prototype` 경로는 막지 못한다. 이 플래그는 `__proto__` 경로의 보조 수단이다.
5. 방어 없음 칸이 "안전"인 M1/constructor 같은 조합은 안전한 게 아니라 이 구현 모양에서 우연히 안 풀린 것이다. 병합 함수를 리팩터링해서 객체 판정 방식이 바뀌면 열린다.

null 프로토타입 객체(`Object.create(null)`)를 병합 대상 루트로 쓰는 방어는 표에서 모든 칸이 안전했지만, 이것도 조건이 있다. 루트에만 적용되기 때문이다. 중첩된 키 아래에서 병합이 `{}`를 새로 만들면 그 객체는 일반 프로토타입을 가진다.

```javascript
function m(t, s) { for (const k in s) { if (typeof s[k]==='object' && s[k]!==null) { if (typeof t[k]!=='object'||t[k]===null) t[k]={}; m(t[k], s[k]); } else t[k]=s[k]; } return t; }
m(Object.create(null), JSON.parse('{"a":{"__proto__":{"hit":1}}}'));
({}).hit    // 1  -> 오염
```

루트가 null 프로토타입이어도 `a` 아래로 들어가면 병합이 만든 `{}`에서 같은 일이 벌어진다. 루트만 바꾸는 방어는 평평한 객체에만 통한다.

## 라이브러리는 버전별로 고쳐진 경로가 다르다

lodash를 버전별로 설치해 다섯 가지 호출을 시험했다. 각 호출이 `Object.prototype`에 속성을 남기는지 본 결과다. 같은 페이로드이고 호출만 다르다.

```javascript
const _ = require('lodash');
_.merge({}, JSON.parse('{"__proto__": {"isAdmin": true}}'));
_.merge({}, JSON.parse('{"constructor": {"prototype": {"viaCtor": 1}}}'));
_.defaultsDeep({}, JSON.parse('{"constructor": {"prototype": {"viaDD": 1}}}'));
_.zipObjectDeep(['__proto__.zz'], [1]);
_.set({}, '__proto__.ss', 1);
```

| lodash | merge `__proto__` | merge `constructor.prototype` | defaultsDeep | zipObjectDeep | set |
|---|---|---|---|---|---|
| 4.17.4 | 오염 | 오염 | 오염 | 오염 | 오염 |
| 4.17.5 | 안전 | 오염 | 오염 | 오염 | 오염 |
| 4.17.10 | 안전 | 오염 | 오염 | 오염 | 오염 |
| 4.17.11 | 안전 | 안전 | 오염 | 오염 | 오염 |
| 4.17.15 | 안전 | 안전 | 안전 | 오염 | 오염 |
| 4.17.19 | 안전 | 안전 | 안전 | 안전 | 안전 |
| 4.17.21 | 안전 | 안전 | 안전 | 안전 | 안전 |
| 4.18.1 (측정 시점 최신) | 안전 | 안전 | 안전 | 안전 | 안전 |

경로가 하나씩 차례로 막혀 왔다. `__proto__`를 막은 버전에서 `constructor.prototype`이 남았고, 그걸 막은 버전에서 `defaultsDeep`이 남았고, 다시 `zipObjectDeep`과 `set`이 남았다. 4.17.15는 `merge`와 `defaultsDeep`이 막혀 있는데도 `zipObjectDeep`과 `set`은 열려 있다. "병합 취약점은 패치했다"는 확인으로는 모자란 이유다. 점검 대상은 병합 함수 하나가 아니라 사용자 입력을 키 경로로 쓰는 모든 호출(`set`, `setWith`, `zipObjectDeep`, 경로 문자열 기반 업데이트 등)이다.

이 표는 이 환경에서 위 다섯 가지 호출만 돌린 결과다. 다른 함수나 다른 라이브러리(deepmerge, minimist 같은 CLI 파서 등)가 같은 상태라는 뜻은 아니다. 의존성 목록은 `npm audit`와 [의존성 취약점 선별](Dependency_Vulnerability_Triage.md)에서 다루는 방식으로 확인하는 게 맞다.

## 병합 말고도 객체가 "복사"되는 곳

JSON을 받아 객체로 옮기는 방법은 병합만이 아니다. 같은 `{"__proto__": {"isAdmin": true}}`를 세 가지 방식으로 옮겨 보았다.

```javascript
const parsed = JSON.parse('{"__proto__": {"isAdmin": true}}');

Object.assign({}, parsed).isAdmin      // true       - 대상 객체의 프로토타입만 바뀐다
({}).isAdmin                           // undefined  - 전역 오염은 아니다
({ ...parsed }).isAdmin                // undefined  - 스프레드는 own 속성 '__proto__' 를 만든다
structuredClone(parsed).isAdmin        // undefined  - own 속성으로 복제된다
```

`Object.assign`은 `target.__proto__ = value`처럼 대입 연산을 쓰기 때문에 대상 객체의 프로토타입이 공격자 객체로 바뀐다. 이 객체에서만 `isAdmin`이 참이 된다. 전역 오염은 아니지만 "그 사용자 객체에 권한 필드가 상속된다"는 점에서 같은 종류의 문제다. 스프레드와 `structuredClone`은 `__proto__`를 일반 own 속성으로 취급해서 프로토타입이 바뀌지 않는다. 다만 그 객체를 나중에 재귀 병합에 넘기면 다시 문제가 된다.

## 방어는 어디에 두느냐에 따라 효과가 달랐다

위 표에서 나온 결과를 방어 수단별로 정리한다.

**키 거부 목록.** `__proto__`, `constructor`, `prototype` 세 개를 모두 병합 단계에서 건너뛰는 방법이 표의 모든 구현에서 막혔다. 하나라도 빠지면 구현에 따라 뚫린다. 직접 짠 병합 함수를 고칠 때 가장 단순하다. 라이브러리를 쓴다면 위 버전표처럼 최신 버전으로 올리는 것이 같은 일이다.

**`Object.hasOwn`으로 확인 후 재귀.** 대상에 own 속성이 있을 때만 그 안으로 들어가고 없으면 새 `{}`를 만든다. `target['__proto__']`가 접근자로 `Object.prototype`을 돌려주는 경로를 끊는다. 표의 "own일 때만 재귀" 열이 모두 안전이었다.

**`Object.freeze(Object.prototype)`.** 표에서 모두 안전했다. 대입이 조용히 무시되기 때문이다. 이 설정은 `'use strict'` 코드에서 쓰기 시도가 `TypeError`를 던지는 것으로 바뀐다.

```text
sloppy 모드: o.toString = () => 'x'   -> 대입이 조용히 무시됨
strict 모드: o.toString = () => 'x'   -> TypeError: Cannot assign to read only property 'toString' of object '#<Object>'
```

그래서 의존하는 코드 중 `Object.prototype`에 속성을 추가하거나 그 메서드를 덮어쓰는 것이 있으면 깨진다. 어떤 의존성이 그런지는 이 문서에서 확인하지 않았으므로, 운영에 넣기 전에 테스트 스위트를 이 설정으로 돌려 확인해야 한다. 그리고 막는 것이 아니라 침묵시키는 방어라 오염 시도가 있었는지는 알려 주지 않는다.

**`node --disable-proto=delete`.** `__proto__` 경로만 막는다. 표에서 M2의 `constructor.prototype`이 그대로 오염이었다. `--disable-proto=throw`는 접근 시 예외를 던지게 하는 변형이다(`Error: Accessing Object.prototype.__proto__ has been disallowed with --disable-proto=throw`). 보조 수단으로만 쓰는 게 맞다.

**스키마 검증으로 키를 제한.** 환경설정에 받을 수 있는 키가 `theme`, `lang`처럼 정해져 있다면 병합에 넘기기 전에 허용 목록으로 걸러 내는 것이 가장 확실하다. 알 수 없는 키가 아예 병합에 도달하지 않는다. [API 입력 검증](API_Input_Validation.md)에서 다루는 스키마 검증이 이 역할을 한다.

**`Map` 사용.** 키가 사용자 입력이고 임의여서 객체 대신 사전이 필요하면 `Map`이 맞다. `Map`은 키를 프로토타입 체인과 무관하게 저장한다. 위 실험에서 `new Map(Object.entries(parsed))`의 키 목록은 `[ '__proto__' ]`였고 `Object.prototype`은 영향받지 않았다.

## 오염됐는지 운영에서 확인하는 법

방어를 다 걸었어도 의존성 하나가 뚫려 있을 수 있다. 시작 시점의 `Object.prototype` 키 목록을 기억해 두고 이후에 달라졌는지 확인하는 카나리를 둘 수 있다.

```javascript
const baseline = new Set(Reflect.ownKeys(Object.prototype));
function protoCanary() {
  return Reflect.ownKeys(Object.prototype).filter((k) => !baseline.has(k));
}
console.log('오염 전:', protoCanary());     // []
Object.prototype.isAdmin = true;
console.log('오염 후:', protoCanary());     // [ 'isAdmin' ]
```

이 함수를 헬스 체크 엔드포인트나 요청 후처리에서 주기적으로 호출해 결과가 비어 있지 않으면 경보를 보내고 해당 프로세스를 재시작한다. 오염은 프로세스 메모리 안에서만 존재하니 재시작이 복구다. 어떤 요청이 원인인지 알려면 요청 본문을 로그에 남겨야 하는데, 본문에 개인정보가 있을 수 있으니 `__proto__`, `constructor` 키가 들어 있는 요청만 선택해서 남기는 쪽이 낫다.

CI에서는 병합 함수에 대한 회귀 테스트로 위 페이로드를 넣고 병합 뒤에 `({}).hit`이 `undefined`인지만 확인해도 충분하다. 테스트 끝에 `delete Object.prototype.hit`을 잊으면 다음 테스트가 오염된 상태로 돈다. 그래서 오염 확인 테스트는 별도 프로세스에서 돌리는 것이 안전하다. 위 표도 칸마다 자식 프로세스를 띄워서 만들었다.

## 정리

- JSON의 `__proto__`는 own 속성이다. 병합 함수가 그 키를 대상 객체에 읽고 쓰는 순간 `Object.prototype`에 닿는다.
- 같은 페이로드가 구현에 따라 `__proto__` 경로나 `constructor.prototype` 경로로만 터진다. 한 경로를 막았다고 안전한 게 아니다.
- 직접 짠 병합은 세 키를 모두 거르거나 own 속성만 재귀하게 고치고, 라이브러리는 버전을 올린다. lodash는 4.17.19 이전 버전에서 `set`과 `zipObjectDeep`이 열려 있었다.
- 루트만 `Object.create(null)`로 만드는 방어는 중첩 객체에 통하지 않는다.
- `Object.freeze(Object.prototype)`은 효과가 크지만 strict 모드 코드와 일부 의존성이 깨질 수 있으니 테스트 후에 쓴다.
- 오염 여부는 `Object.prototype`의 키 목록을 시작 시점과 비교해서 확인할 수 있다.
