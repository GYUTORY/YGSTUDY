---
title: TypeScript null 타입 심화
tags: [language, typescript, 타입-및-타입-정의, typescript-types, primitive-types, "null", strictNullChecks]
updated: 2026-06-07
---

# TypeScript null 타입 심화

## 들어가며

`null`이라는 단어는 단순해 보이지만, TypeScript에서 null을 다루는 일은 절대 단순하지 않다. `strictNullChecks` 옵션 하나를 켰을 뿐인데 빌드 에러가 수백 개씩 쏟아지는 광경, API에서 받아온 값이 `null`인지 `undefined`인지 헷갈려 런타임에서 터지는 버그, `||` 대신 `??`를 써야 하는데 모르고 썼다가 `0`이 사라지는 사건. 5년 정도 TypeScript를 만지다 보면 이런 일은 한 번씩 다 겪는다.

이 문서는 `null` 타입 자체의 기본 사용법이 아니라, 그 주변에서 실제로 사고가 나는 지점을 다룬다. strictNullChecks의 좁히기 동작, `??`와 `||`의 차이로 인한 미묘한 버그, `?:` 옵셔널과 `| undefined` 유니온의 차이, exactOptionalPropertyTypes 옵션, JSON 직렬화에서 undefined가 조용히 사라지는 동작, NonNullable 유틸리티의 한계, 단언 연산자(`!`) 남용의 함정 같은 것들이다.

## null과 undefined: 그 미묘한 차이

자바스크립트에는 "값이 없음"을 표현하는 두 가지 방법이 있다. `null`과 `undefined`다. 둘 다 거짓 값(falsy)이고, `==`로 비교하면 서로 같다고 나오지만, TypeScript는 이 둘을 완전히 다른 타입으로 본다.

```typescript
let a: null = null;
let b: undefined = undefined;

a === b;  // false
a == b;   // true (헷갈리는 비교)
```

실무에서 두 값을 구분하는 가장 명확한 기준은 "누가 그 값을 만들었는가"다. `undefined`는 자바스크립트 런타임이 만들어내는 값이다. 변수를 선언만 하고 초기화하지 않았을 때, 함수에 인자를 빠뜨렸을 때, 객체에 존재하지 않는 프로퍼티를 접근했을 때, 함수가 명시적으로 값을 반환하지 않을 때 모두 `undefined`가 나온다. 반면 `null`은 개발자가 직접 적어 넣어야만 등장한다. 누군가가 의도적으로 "여기에는 값이 없다"라고 표시한 결과다.

```typescript
function user() {
  return; // 반환문 없음 → undefined
}

const u = user();      // undefined
const obj: any = {};
const x = obj.foo;     // 존재하지 않는 프로퍼티 접근 → undefined

let intentionallyEmpty: string | null = null; // null은 의도적
```

이 구분이 중요한 이유는 API 응답 설계에서 드러난다. 백엔드에서 "값이 아직 계산되지 않았다"는 의미로 `undefined`를, "계산했지만 값이 없다"는 의미로 `null`을 사용하기도 한다. 하지만 이 구분을 강제할 방법이 없어서 팀마다, 프로젝트마다 컨벤션이 갈린다. 그래서 한 쪽으로 통일하는 게 운영상 편하다. 개인적으로는 외부 경계(API 응답, DB 결과)에서는 `null`로 통일하고, 내부 코드에서는 `undefined`를 쓰는 방식을 선호한다. JSON 직렬화 때문이다.

```typescript
JSON.stringify({ a: null, b: undefined });
// '{"a":null}' — undefined는 사라진다
```

`undefined`는 JSON에 존재하지 않는 값이라 직렬화 과정에서 키 자체가 빠진다. 그래서 클라이언트로 응답을 내려보낼 때 `undefined`를 쓰면, 받는 쪽에서는 "이 키가 없음"으로 받는다. 반면 `null`을 쓰면 키가 존재하고 값이 `null`로 들어온다. 이 차이는 클라이언트가 PATCH 요청을 보낼 때 특히 문제가 된다. "필드를 비워달라"는 요청과 "필드를 그대로 두라"는 요청을 구분해야 하는데, `undefined`가 사라지는 동작 때문에 `null`로만 표현이 가능하다.

## strictNullChecks의 실제 동작

`strictNullChecks` 옵션은 TypeScript 2.0부터 추가된 옵션이고, 지금은 `strict: true`에 포함되어 사실상 표준이다. 이 옵션이 꺼져 있을 때와 켜져 있을 때의 차이는 단순히 "null 체크를 강제하느냐"가 아니다. 타입 시스템 전체의 동작이 바뀐다.

옵션이 꺼져 있으면 모든 타입에 암묵적으로 `null`과 `undefined`가 포함된다. `string` 타입 변수에 `null`을 넣어도 통과한다. 함수 매개변수에 `undefined`를 넣어도 문제가 없다. 즉, 컴파일러가 `null`로 인한 사고를 막아주지 못한다.

옵션을 켜면 `null`과 `undefined`는 자기 자신의 타입에만 속하게 된다. `string` 타입 변수에 `null`을 넣으려면 명시적으로 `string | null`로 선언해야 한다. 그리고 좁히기(narrowing)가 본격적으로 작동하기 시작한다.

```typescript
function getLength(s: string | null): number {
  // 여기서 s는 string | null
  if (s === null) {
    return 0;
  }
  // 여기서 s는 string으로 좁혀진다
  return s.length;
}
```

control flow analysis라고 부르는 이 동작은 if 문, switch 문, 삼항 연산자, 단축 평가, 할당 등 흐름이 바뀌는 거의 모든 지점에서 작동한다. 그래서 적절히 좁히기만 하면 `null` 체크 후에는 깔끔하게 `string` 메서드를 호출할 수 있다.

문제는 좁히기가 항상 의도대로 동작하지 않는다는 점이다. 가장 자주 겪는 함정은 함수 호출이 끼어들 때다.

```typescript
class User {
  name: string | null = null;

  greet() {
    if (this.name === null) return;
    // 여기서 this.name은 string으로 좁혀짐
    
    this.updateSomething(); // 이 호출이 name을 바꿀 수도 있다
    
    // 여기서도 여전히 string으로 보지만, 실제로는 null일 수 있다
    console.log(this.name.length);
  }
  
  updateSomething() {
    this.name = null;
  }
}
```

TypeScript는 함수 호출 후에 인스턴스 프로퍼티가 변경됐을 가능성을 추적하지 못한다. 보수적으로 동작하지 않고, 좁혀진 타입을 유지한다. 그래서 `null`이 되었는데도 컴파일러는 `string`으로 본다. 클래스 멤버를 다룰 때는 일찍 지역 변수로 꺼내서 쓰는 패턴이 안전하다.

```typescript
greet() {
  const name = this.name;
  if (name === null) return;
  
  this.updateSomething();
  console.log(name.length); // 이건 안전하다
}
```

또 다른 함정은 콜백 안에서 좁히기가 사라진다는 점이다.

```typescript
function process(value: string | null) {
  if (value === null) return;
  
  setTimeout(() => {
    // 여기서 value는 다시 string | null로 보일 수도 있다
    // (TypeScript 버전과 설정에 따라 다름)
    console.log(value.length);
  });
}
```

콜백 안에서는 비동기로 실행되는 시점이 다르기 때문에, 좁힌 타입을 그대로 신뢰하지 않는다. 이때도 외부에서 변수에 담아두는 패턴이 깔끔하다.

## strictNullChecks 마이그레이션의 현실

오래된 코드베이스에서 `strictNullChecks: true`로 옮기는 작업은 진짜 고통이다. 옵션을 켜자마자 빌드 에러가 수천 개씩 뜨는 광경을 보면 그냥 끄고 싶어진다. 이때 쓰는 우회 전략 몇 가지가 있는데, 각각 장단이 있다.

첫째, 파일 단위 점진적 활성화다. `// @ts-strict`나 `// @ts-nocheck` 주석으로 파일 단위로 검사 강도를 조절하는 방법인데, 공식적으로 strictNullChecks만 끄는 주석은 없다. 대신 `// @ts-expect-error`로 개별 라인만 무시할 수는 있다. 그래서 보통은 별도 tsconfig 파일을 만들어 점진적으로 영역을 좁히는 방식을 쓴다.

```json
// tsconfig.strict.json — 새로 작성하는 영역만 strict
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "strictNullChecks": true
  },
  "include": ["src/new-module/**/*"]
}
```

둘째, 단언 연산자(`!`) 남용이다. `value!.length`처럼 `!`를 붙이면 컴파일러에게 "이 값은 절대 null/undefined가 아니다"라고 약속하는 셈이 된다. 마이그레이션 초기에는 빠르게 빌드를 통과시키려고 이걸 남발하기 쉽다. 문제는 런타임에서는 아무 보장도 하지 않는다는 점이다. 컴파일러만 속이는 거고, 실제 값이 `null`이면 그대로 폭발한다.

```typescript
function getName(u: User | null): string {
  return u!.name; // u가 null이면 런타임 에러
}
```

마이그레이션 시점에는 어쩔 수 없이 쓰더라도, 코드 리뷰에서 `!`가 보이면 정말 이게 필요한지 한 번 더 본다. 좁히기를 추가하거나, 기본값을 주거나, 함수 시그니처를 바꾸는 방향이 거의 항상 더 낫다.

셋째, 타입 단언으로 회피하는 패턴이다. `as string`처럼 강제로 캐스팅해서 null 가능성을 지워버리는 방식인데, 이것도 `!`와 본질적으로 같다. 런타임 안전성은 없다.

마이그레이션을 그나마 덜 고통스럽게 하는 실용적인 순서는 이렇다. 외부 경계(API 호출, DB 쿼리, 사용자 입력)부터 정확한 타입을 부여한다. 거기서 들어오는 값이 정말로 `null`이 될 수 있는지 한 번에 정의해두면, 그 이후로는 컴파일러가 알아서 추적해준다. 내부 함수들은 그 시그니처를 따라가며 좁히기를 추가하면 된다.

## ?? 와 || 의 진짜 차이

`??`(Nullish Coalescing) 연산자는 ES2020에서 도입됐다. 표면적으로는 `||`와 비슷해 보인다. 둘 다 "왼쪽 값이 비어 있으면 오른쪽 값을 쓴다"는 의미다. 하지만 "비어 있다"의 정의가 다르다.

`||`는 좌변이 falsy일 때 우변을 반환한다. JavaScript에서 falsy는 `false`, `0`, `-0`, `0n`, `""`, `null`, `undefined`, `NaN`이다. 그러니까 `0`이나 빈 문자열도 falsy다.

`??`는 좌변이 `null` 또는 `undefined`일 때만 우변을 반환한다. 그 외의 값은 모두 그대로 둔다.

이 차이가 운영 버그로 이어지는 전형적인 사례가 있다.

```typescript
interface Config {
  timeout?: number;
  retries?: number;
  prefix?: string;
}

function applyDefaults(c: Config) {
  return {
    timeout: c.timeout || 3000,    // 위험
    retries: c.retries || 3,       // 위험
    prefix: c.prefix || "default", // 위험
  };
}

applyDefaults({ timeout: 0, retries: 0, prefix: "" });
// { timeout: 3000, retries: 3, prefix: "default" }
// 사용자가 명시적으로 0과 ""을 지정했는데 무시된다
```

사용자가 타임아웃을 `0`(무한대 또는 비활성)으로 설정하고 싶었는데, `||`가 falsy로 보고 기본값 `3000`으로 덮어쓴다. 빈 문자열을 prefix로 쓰고 싶었는데도 마찬가지다. 이런 동작 차이는 코드 리뷰에서 잡기 어렵고, QA가 명시적으로 `0`을 테스트하지 않으면 그대로 운영에 나간다.

`??`로 바꾸면 정확하게 동작한다.

```typescript
function applyDefaults(c: Config) {
  return {
    timeout: c.timeout ?? 3000,
    retries: c.retries ?? 3,
    prefix: c.prefix ?? "default",
  };
}

applyDefaults({ timeout: 0, retries: 0, prefix: "" });
// { timeout: 0, retries: 0, prefix: "" }
```

`||`가 `??`보다 적절한 경우도 있다. "비어 있는 문자열이나 0도 사용자가 입력을 안 한 걸로 본다"는 의도가 명확할 때다. 예를 들어 폼 입력값에서 빈 문자열을 "값 없음"으로 취급하고 싶다면 `||`가 맞다. 의도를 명확히 하려면 빈 문자열을 직접 체크하는 게 가장 안전하다.

```typescript
const username = input.trim() === "" ? "anonymous" : input.trim();
```

문법적으로 주의할 점도 있다. `??`는 `||`나 `&&`와 우선순위가 같지 않아서, 한 표현식에 섞어 쓰면 컴파일 에러가 난다.

```typescript
const x = a || b ?? c; // 컴파일 에러
const x = (a || b) ?? c; // OK
const x = a || (b ?? c); // OK
```

명시적으로 괄호를 쓰지 않으면 TypeScript가 막아준다. 가독성을 위해서라도 괄호로 묶는 습관이 좋다.

## Optional Chaining과 단축 평가

`?.` 연산자는 `??`와 자주 같이 쓰인다. 객체 체인을 따라가다가 중간에 `null`이나 `undefined`를 만나면 즉시 `undefined`를 반환하고 멈춘다. 핵심은 "멈춘다"는 부분이다.

```typescript
interface User {
  profile?: {
    name?: string;
    avatar?: { url: string };
  };
}

const u: User = { profile: undefined };

const url = u.profile?.avatar?.url;
// u.profile이 undefined라 거기서 멈춤
// url은 undefined
```

`?.`가 작동하는 시점은 좌변이 정확히 `null` 또는 `undefined`일 때다. 다른 falsy 값(`0`, `""`, `false`)은 통과시킨다. 이 점은 `??`와 일관성이 있다. 둘 다 "nullish" 개념을 사용한다.

`?.`에는 세 가지 형태가 있다. 프로퍼티 접근, 메서드 호출, 인덱스 접근이다.

```typescript
obj?.prop      // 프로퍼티 접근
obj?.method()  // 메서드 호출 — obj가 nullish면 호출하지 않음
obj?.[key]     // 인덱스 접근 — 배열이나 동적 키에 사용
```

메서드 호출 형태 `?.()`는 함수 자체가 `null`이거나 `undefined`일 수 있을 때 쓴다. 콜백을 옵셔널로 받는 함수에서 유용하다.

```typescript
function fetchData(onProgress?: (n: number) => void) {
  // ...
  onProgress?.(50); // onProgress가 undefined면 호출 안 함
}
```

`onProgress && onProgress(50)`보다 깔끔하다. 단, 주의할 점이 있다. `?.()`는 좌변이 함수가 아닌 다른 값일 때는 에러를 던진다. `null`이나 `undefined`만 통과시키지, "함수가 아닌 객체"는 통과시키지 않는다.

```typescript
const x: unknown = "not a function";
x?.(); // TypeError: x is not a function
```

인덱스 형태 `?.[key]`는 배열 인덱싱이나 동적 키 접근에 쓴다.

```typescript
const arr: number[] | undefined = getArray();
const first = arr?.[0]; // arr이 undefined면 first도 undefined

const map: Record<string, string> | null = getMap();
const value = map?.[someKey];
```

`?.` 체인을 길게 이어가다 보면 "어디까지가 옵셔널인지" 헷갈리기 쉽다. 짧고 명확하게 쓰는 게 좋고, 4단계 이상 이어진다면 중간에 변수로 빼는 걸 고려한다.

## 옵셔널 프로퍼티와 | undefined의 차이

TypeScript 인터페이스에서 옵셔널 프로퍼티는 두 가지 방식으로 표현할 수 있다.

```typescript
interface A {
  name?: string;
}

interface B {
  name: string | undefined;
}
```

겉보기에 비슷하지만, 사용 시 차이가 있다.

`A`의 `name?:` 형태는 "이 프로퍼티 자체가 없어도 된다"는 뜻이다. 객체에 `name` 키가 아예 없어도 통과한다.

```typescript
const a1: A = {}; // OK
const a2: A = { name: undefined }; // OK
const a3: A = { name: "hello" }; // OK
```

`B`의 `name: string | undefined`는 "이 프로퍼티는 반드시 있어야 하고, 값이 undefined일 수 있다"는 뜻이다. 키 자체를 빼면 에러다.

```typescript
const b1: B = {}; // 에러: name 누락
const b2: B = { name: undefined }; // OK
const b3: B = { name: "hello" }; // OK
```

표면적으로는 사소한 차이로 보이지만, 객체를 생성하는 측에서 코드가 달라진다. 옵셔널 프로퍼티는 "값을 정하지 않았으면 그냥 키를 안 쓰면 된다"는 자연스러운 사용을 허용한다. `| undefined`는 매번 "undefined를 명시적으로 적어야 한다"고 강제한다. 그래서 의미적으로 "있어도 되고 없어도 되는 값"이라면 `?:`가 적절하고, "이 키는 반드시 있지만 값이 미정일 수 있다"는 의미라면 `| undefined`가 맞다.

이 둘이 같아 보이는 이유는 `exactOptionalPropertyTypes` 옵션이 꺼져 있을 때다. 옵션이 꺼져 있으면 `?:`로 선언한 프로퍼티에 `undefined`를 명시적으로 넣어도 통과한다. 켜면 동작이 엄격해진다.

## exactOptionalPropertyTypes의 의미

`exactOptionalPropertyTypes` 옵션은 TypeScript 4.4에서 도입됐다. 이름이 길지만 동작은 단순하다. 옵셔널 프로퍼티(`?:`)에 명시적으로 `undefined`를 할당하는 걸 금지한다.

옵션이 꺼져 있을 때(기본):

```typescript
interface User {
  name?: string;
}

const u: User = { name: undefined }; // OK
u.name = undefined; // OK
```

옵션이 켜져 있을 때:

```typescript
const u: User = { name: undefined }; // 에러
u.name = undefined; // 에러
delete u.name; // OK (키 자체를 제거)
```

이 옵션을 켜면 "키가 없음"과 "키가 있지만 값이 undefined"가 의미적으로 구분된다. 이건 굉장히 큰 변화다. PATCH 요청처럼 "이 필드를 건드리지 않음" vs "이 필드를 null로 비움" vs "이 필드를 undefined로 설정함"을 구분해야 하는 API에서 의미를 정확하게 표현할 수 있다.

다만 실무에서 켜기는 부담스러운 옵션이다. 기존 코드에서 `obj.foo = undefined`로 키를 비우는 패턴을 흔하게 쓰는데, 옵션을 켜면 이게 전부 에러로 잡힌다. `delete obj.foo`로 바꾸거나, 타입을 `| undefined`로 명시해야 한다. 새 프로젝트라면 켜는 걸 추천하지만, 오래된 코드베이스에서는 도입 비용이 크다.

## NonNullable 유틸리티의 동작과 한계

TypeScript는 표준 유틸리티 타입으로 `NonNullable<T>`를 제공한다. 정의는 단순하다.

```typescript
type NonNullable<T> = T extends null | undefined ? never : T;
```

조건부 타입으로 `null`과 `undefined`를 분배해서 제거한다. 사용 예시는 이렇다.

```typescript
type A = string | null | undefined;
type B = NonNullable<A>; // string

type C = number | null;
type D = NonNullable<C>; // number
```

자주 쓰이는 패턴은 함수 반환값에서 null을 걸러낸 결과를 표현할 때다.

```typescript
function findOrNull<T>(arr: T[], pred: (x: T) => boolean): T | null {
  return arr.find(pred) ?? null;
}

type Found = NonNullable<ReturnType<typeof findOrNull>>;
```

한계도 있다. `NonNullable`은 최상위 레벨만 다룬다. 객체 내부의 옵셔널 프로퍼티는 그대로 둔다.

```typescript
interface User {
  name: string;
  email?: string;
}

type T = NonNullable<User>;
// T는 여전히 { name: string; email?: string }
// email의 옵셔널은 그대로 남음
```

깊이 들어가서 모든 nullish를 제거하고 싶다면 직접 재귀 매핑 타입을 만들어야 한다.

```typescript
type DeepNonNullable<T> = T extends object
  ? { [K in keyof T]-?: DeepNonNullable<NonNullable<T[K]>> }
  : T;
```

`-?` 수식어가 옵셔널 표시를 제거하는 부분이다. 이런 변환을 자주 쓴다면 라이브러리(type-fest 같은)에서 가져다 쓰는 게 안전하다.

## 좁히기가 안 되는 순간들

control flow analysis는 강력하지만 완벽하지 않다. 위에서 언급한 함수 호출과 콜백 외에도 좁히기가 풀리는 상황이 몇 가지 더 있다.

배열 인덱스 접근은 항상 검사되지 않는다. 기본적으로 `arr[0]`은 `arr`의 요소 타입을 그대로 반환한다. 빈 배열에서 인덱스 접근을 해도 컴파일러는 모른다.

```typescript
const arr: number[] = [];
const x = arr[0]; // 타입은 number지만 실제 값은 undefined
x.toFixed(2); // 런타임 에러
```

이걸 잡으려면 `noUncheckedIndexedAccess` 옵션을 켜야 한다. 켜면 모든 인덱스 접근 결과에 `| undefined`가 자동으로 붙는다.

```typescript
const x = arr[0]; // 타입이 number | undefined가 됨
if (x !== undefined) {
  x.toFixed(2); // OK
}
```

배열을 많이 다루는 코드에서는 코드량이 늘어나지만, 런타임 안정성은 확실히 올라간다. 마이크로 서비스 API 응답 파싱이나 사용자 입력 처리에서 특히 가치가 있다.

또 다른 함정은 객체 비구조화에서다.

```typescript
function process(data: { value?: number }) {
  const { value } = data;
  if (value !== undefined) {
    // value는 number
    data.value = undefined; // 원본은 바뀌었지만
    console.log(value.toFixed(2)); // 이건 좁혀진 지역 변수라 안전
  }
}
```

비구조화로 떼어내면 좁히기가 지역 변수에만 적용되어, 원본 객체가 바뀌어도 영향을 받지 않는다. 이건 오히려 안전한 패턴이다.

문제는 인덱스 시그니처를 가진 객체다.

```typescript
const obj: Record<string, string | null> = { a: "hello" };
if (obj["a"] !== null) {
  // obj["a"]는 string으로 좁혀짐
  console.log(obj["a"].length);
}
```

이건 동작한다. 하지만 변수에 담아두지 않고 매번 인덱스 접근을 하면 좁히기가 풀린다.

```typescript
if (obj["a"] !== null) {
  doSomething();
  console.log(obj["a"].length); // 에러: obj["a"]는 string | null
}
```

함수 호출 후에 인덱스 접근이 다시 풀리는 거다. 이때도 일찍 변수에 담아두는 패턴이 정답이다.

## 단언 연산자(!)의 진짜 위험

`!`는 컴파일러에게 "이건 절대 nullish가 아니야"라고 약속하는 연산자다. 컴파일러는 그 말을 그대로 믿는다. 검증은 하지 않는다.

```typescript
function find(arr: User[], id: number): User {
  return arr.find(u => u.id === id)!; // 못 찾으면 undefined인데 !로 무시
}

const u = find([], 1); // u는 User로 추론되지만 실제로는 undefined
u.name; // 런타임 에러
```

`find`는 결과를 못 찾으면 `undefined`를 반환한다. `!`를 붙여서 `User`로 단언했지만, 실제로는 `undefined`다. 호출한 쪽에서 `u.name`을 접근하면 TypeError가 난다.

`!`를 정당하게 쓸 수 있는 경우는 컴파일러가 추적할 수 없지만 개발자가 확신할 수 있는 상황뿐이다. 예를 들어 비동기 초기화 패턴이나, 라이브러리 안전성에 의존하는 경우다.

```typescript
class Service {
  private db!: Database; // 생성자에서 안 만들지만, init에서 만들 거란 약속
  
  async init() {
    this.db = await connectDb();
  }
}
```

이건 합리적인 사용이다. 그래도 `init()`이 호출되기 전에 `db`를 쓰면 런타임 에러가 난다. 그래서 `!`를 쓸 때는 항상 "이 시점에 정말 값이 있다는 걸 코드 구조가 보장하는가"를 생각해봐야 한다.

대부분의 경우에는 `!`보다 좁히기, 기본값, 타입 가드를 쓰는 게 낫다.

```typescript
// !! 대신
const u = arr.find(u => u.id === id);
if (!u) throw new Error("user not found");
return u;
```

런타임에서 명확한 에러 메시지로 실패하는 게 정체불명의 `undefined.name` 에러보다 디버깅이 백 배 쉽다.

## void 0 과 undefined 리터럴

가끔 코드베이스에서 `void 0`이라는 표현을 본다. 이건 `undefined`와 같은 값이지만, 왜 굳이 이렇게 쓰는지 헷갈릴 수 있다.

자바스크립트의 `undefined`는 사실 키워드가 아니라 전역 변수다. 옛날 JavaScript에서는 `undefined`를 덮어쓸 수 있었다. 그래서 안전하게 `undefined` 값을 얻기 위해 `void` 연산자를 사용했다. `void`는 어떤 표현식이든 평가한 후 `undefined`를 반환한다. `void 0`은 "숫자 0을 평가하고 undefined를 반환"한다.

ES5부터는 전역 `undefined`를 덮어쓸 수 없게 막혔다. 그래서 현대 코드에서 `void 0`을 쓸 이유는 거의 없다. 다만 미니파이된 번들에서는 `undefined`(9글자)보다 `void 0`(6글자)이 짧아서 종종 등장한다. 자체 코드를 작성할 때는 그냥 `undefined`를 쓰면 된다.

TypeScript에서는 `void`가 또 다른 의미로 쓰인다. 함수의 반환 타입 `void`는 "이 함수는 값을 반환하지 않는다"는 의미인데, 실제로는 `undefined`를 반환할 수도 있고, 다른 값을 반환해도 호출 측에서 그 값을 쓰지 않겠다는 약속이다. 이 부분은 별도 문서가 있으니 깊이 다루지 않는다.

## JSON.parse 결과와 null 처리

`JSON.parse`의 반환 타입은 `any`다. 그래서 strictNullChecks 옵션이 켜져 있어도 `JSON.parse` 결과에 대해서는 컴파일러가 도움을 주지 못한다. 외부에서 받아온 JSON을 처리할 때는 검증 단계가 반드시 필요하다.

```typescript
function parseUser(json: string): User | null {
  try {
    const data = JSON.parse(json);
    if (
      typeof data === "object" &&
      data !== null &&
      typeof data.id === "number" &&
      typeof data.name === "string"
    ) {
      return data as User;
    }
    return null;
  } catch {
    return null;
  }
}
```

직접 검증하는 게 번거롭다면 zod, io-ts, valibot 같은 런타임 검증 라이브러리를 쓰는 게 낫다.

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().nullable(),
});

type User = z.infer<typeof UserSchema>;

function parseUser(json: string): User | null {
  try {
    return UserSchema.parse(JSON.parse(json));
  } catch {
    return null;
  }
}
```

JSON에서 또 하나 짚고 갈 점은, JSON 표준에 `undefined`가 없다는 사실이다. `null`은 있다. 그래서 직렬화 과정에서 차이가 생긴다.

```typescript
JSON.stringify({ a: null, b: undefined, c: 1 });
// '{"a":null,"c":1}'

JSON.stringify([null, undefined, 1]);
// '[null,null,1]' — 배열에서는 undefined가 null로 변환됨
```

객체에서는 키가 사라지고, 배열에서는 `null`로 변환된다. 이 비대칭은 직렬화 한 번 거치고 받는 쪽에서 "왜 키가 없지?"하는 혼란을 만든다. 그래서 백엔드 API 응답을 설계할 때 처음부터 `null`로 통일하는 게 운영상 깔끔하다.

```typescript
type ApiResponse<T> = {
  data: T | null;
  error: string | null;
};
```

옵셔널 프로퍼티(`?:`)를 외부 API 스키마에 쓰면 응답마다 키 존재 여부가 들쭉날쭉해진다. 키는 항상 있고, 값이 `null`일 수 있다는 식으로 잡으면 클라이언트 측 코드가 단순해진다.

## 타입 가드 함수와 NonNullable

좁히기를 함수 단위로 추상화할 수 있다. type predicate를 반환하는 함수를 만들면 된다.

```typescript
function isNotNull<T>(value: T | null): value is T {
  return value !== null;
}

function isNotNullish<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

const arr: (string | null)[] = ["a", null, "b", null];
const filtered = arr.filter(isNotNull); // 타입은 string[]
```

`Array.prototype.filter`는 표준 시그니처로는 좁히기를 인식하지 못한다. type predicate를 받는 오버로드가 정의되어 있어서 type predicate 함수를 넘기면 결과 타입이 좁혀진다.

`Boolean`을 직접 넘기는 패턴은 작동하지 않는다.

```typescript
const filtered = arr.filter(Boolean); // 타입은 여전히 (string | null)[]
```

`Boolean`은 type predicate 시그니처가 아니라서 컴파일러가 좁히기를 적용하지 못한다. 운영에서 자주 만나는 함정이다. 실제 값은 잘 걸러지는데 타입은 그대로라서, 이후에 `.length` 같은 메서드를 쓸 때 다시 에러가 난다. type predicate 헬퍼를 만들어 두고 쓰는 게 가장 깔끔하다.

## 그래서 어떻게 쓰는가

여기까지 본 내용을 실무 관점에서 정리하면 이렇다. `strictNullChecks`는 켜야 한다. 옵션이 꺼져 있는 TypeScript는 TypeScript의 절반만 쓰는 것과 같다. 새 프로젝트라면 `noUncheckedIndexedAccess`와 `exactOptionalPropertyTypes`도 같이 켜는 걸 고려해 볼 만하다.

`||`와 `??`는 의미적으로 다른 연산자다. 기본값을 넣을 때는 거의 항상 `??`가 맞다. `||`를 쓸 때는 "0과 빈 문자열도 비어있는 것으로 본다"는 의도가 명확해야 한다.

`!`는 가급적 쓰지 않는다. 좁히기, 기본값, 명시적 에러 던지기가 거의 항상 더 안전하다. 정말 필요한 경우에는 그 위치에 짧은 주석으로 왜 안전한지 적어둔다.

옵셔널 프로퍼티(`?:`)와 `| undefined`는 의도에 따라 골라 쓴다. "값을 정하지 않으면 키를 안 써도 된다"는 의미라면 `?:`가, "키는 반드시 있지만 값이 미정"이라면 `| undefined`가 맞다.

API 경계에서는 `null`로 통일하는 게 운영상 편하다. JSON 직렬화에서 `undefined`가 사라지는 동작 때문에 클라이언트와 서버 간 일관성을 유지하기 어렵다.

`JSON.parse` 결과는 신뢰하지 않는다. zod 같은 런타임 검증을 거치거나, 직접 타입 가드 함수로 검증한 다음에 좁힌 타입으로 다룬다.

`null`을 잘 다루는 것이 TypeScript를 잘 쓰는 것의 절반이다. 컴파일러가 도와주는 부분과 도와주지 못하는 부분을 정확히 알아야 한다. 도와주지 못하는 지점에서 사고가 난다.
