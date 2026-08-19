---
title: JavaScript & TypeScript 허브
tags: [javascript, typescript, java, language]
updated: 2026-08-03
---

# JavaScript & TypeScript 허브

## 이 주제를 언제 찾게 되는가

- `var` / `let` / `const` 차이, 호이스팅이 왜 일어나는지 다시 정리하고 싶을 때
- 클로저가 "왜" 동작하는지, 렉시컬 스코프가 무엇인지 헷갈릴 때
- `this`가 상황마다 달라져서 당혹스러울 때 (일반 함수 vs 화살표 함수 vs 메서드 호출)
- Promise / async-await 내부가 어떻게 실행되는지, 실행 순서가 헷갈릴 때
- TypeScript에서 제네릭·유틸리티 타입·고급 타입 패턴을 적용하려 할 때
- Java와 JS/TS의 타입 시스템·동시성 모델 차이를 비교 정리하고 싶을 때
- 성능 문제로 메모이제이션·디바운싱·스로틀링을 적용해야 할 때
- 프로젝트에 tsconfig / ESLint / Prettier / tsc-alias를 설정할 때
- Proxy·Reflect로 객체 동작을 커스터마이징해야 할 때
- 제너레이터·이터레이터로 지연 평가 패턴을 구현하려 할 때

---

## 문서 지도

### JavaScript — 기본 개념

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Scope / var · let · const](../Language/JavaScript/01_기본_JavaScript/Scope_var_let_const.md) | 스코프 규칙, var의 함수 스코프·호이스팅, let·const의 TDZ | 입문 |
| [Hoisting](../Language/JavaScript/01_기본_JavaScript/Hoisting.md) | 변수·함수 선언이 끌어올려지는 메커니즘 | 입문 |
| [Closure](../Language/JavaScript/01_기본_JavaScript/Closure/Closure.md) | 클로저와 렉시컬 스코프 심화 | 입문 |
| [렉시컬 스코프와 클로저의 관계](../Language/JavaScript/01_기본_JavaScript/Closure/렉시컬%20스코프와%20클로저의%20관계.md) | 렉시컬 환경이 클로저를 어떻게 만드는지 시각적으로 정리 | 실무 |
| [Closure Practical Patterns](../Language/JavaScript/01_기본_JavaScript/Closure/Closure_Practical_Patterns.md) | 모듈 패턴·커링·부분 적용 등 클로저 실전 활용법 | 실무 |
| [Closure Lexical Scope Deep Dive](../Language/JavaScript/01_기본_JavaScript/Closure/Closure_Lexical_Scope_Deep_Dive.md) | 실행 컨텍스트·스코프 체인까지 파고드는 심층 분석 | 심화 |
| [This Binding](../Language/JavaScript/01_기본_JavaScript/This_Binding.md) | 암시적·명시적·new 바인딩, 화살표 함수의 this | 입문 |
| [일반 함수와 Arrow 함수](../Language/JavaScript/01_기본_JavaScript/function/일반%20함수와%20Arrow%20함수.md) | 두 함수 형태의 this·arguments·prototype 차이 | 입문 |
| [Prototype](../Language/JavaScript/01_기본_JavaScript/Object/Prototype.md) | 프로토타입 체인, 상속 구현 원리 | 실무 |
| [Constructor 개념](../Language/JavaScript/01_기본_JavaScript/Constructor/Constructor_개념.md) | new 연산자와 생성자 함수 동작 원리 | 입문 |

#### this 바인딩 케이스 비교

`this`는 함수가 정의된 위치가 아니라 호출되는 방식으로 결정된다. 화살표 함수만 예외다.

```javascript
const obj = {
  name: 'target',
  regular() { return this.name; },    // 메서드 호출: this === obj
  arrow: () => this?.name,            // 선언 시점 상위 스코프 캡처 (모듈 레벨이면 undefined)
};

obj.regular();          // 'target'
obj.arrow();            // undefined

// 메서드를 변수에 담으면 this가 사라진다 — 흔한 실수
const fn = obj.regular;
fn();                   // undefined (strict mode) / window.name (non-strict)

// call / apply / bind — 명시적으로 this를 지정
function greet() { return this.name; }
greet.call({ name: 'bar' });          // 'bar'
greet.apply({ name: 'baz' }, []);    // 'baz'
const bound = greet.bind({ name: 'qux' });
bound();                              // 'qux'

// new — 새 인스턴스가 this
function Person(name) { this.name = name; }
const p = new Person('alice');        // p.name === 'alice'

// 이벤트 핸들러: 일반 함수는 이벤트 대상 요소, 화살표 함수는 상위 this
btn.addEventListener('click', function() { console.log(this); }); // btn 요소
btn.addEventListener('click', () => { console.log(this); });      // 상위 스코프 this
```

---

### JavaScript — 함수형 프로그래밍

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Functional Programming](../Language/JavaScript/01_기본_JavaScript/function/Functional_Programming.md) | 순수 함수·불변성·고차 함수 기초 | 입문 |
| [Functional Programming Advanced](../Language/JavaScript/01_기본_JavaScript/function/Functional_Programming_Advanced.md) | 함수 합성·모나드·파이프라인 패턴 | 심화 |
| [forEach 개념](../Language/JavaScript/01_기본_JavaScript/For_Loop/forEach_개념.md) | forEach와 for-of·map·filter 비교 | 입문 |
| [forEach Deep Dive](../Language/JavaScript/01_기본_JavaScript/For_Loop/for_Each_Deep_Dive.md) | forEach의 동작 방식, 비동기와의 함정 | 실무 |

---

### JavaScript — 비동기 & 이벤트 루프

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Async/Await & Promise](../Language/JavaScript/05_이벤트_루프_비동기/Async_Await_and_Promise.md) | async-await와 Promise의 내부 실행 흐름, 에러 핸들링 | 실무 |
| [Promise 내부 동작 과정](../Language/JavaScript/04_심화_JavaScript/Promise%20내부%20동작%20과정.md) | Microtask Queue, Promise 상태 전이, chaining 원리 | 심화 |
| [실행 순서 이해](../Language/JavaScript/05_이벤트_루프_비동기/실행%20순서%20이해.md) | 콜 스택·Macrotask·Microtask 실행 순서를 예제로 추적 | 실무 |

#### Promise / async-await 실행 순서

콜 스택이 비워진 직후 Microtask Queue(Promise 콜백)를 전부 소진하고, 그 다음에 Macrotask(setTimeout 등) 하나를 꺼낸다.

```javascript
console.log('1');                                  // 동기: 즉시
setTimeout(() => console.log('4'), 0);             // Macrotask: 마지막
Promise.resolve()
  .then(() => console.log('2'))                    // Microtask: 콜 스택 비운 직후
  .then(() => console.log('3'));                   // 바로 이어서
console.log('1.5');                                // 동기: 즉시
// 출력: 1 → 1.5 → 2 → 3 → 4
```

`async/await`는 `await` 지점에서 실행을 중단하고 Microtask Queue에 재개를 등록한다.

```javascript
async function run() {
  console.log('A');
  await Promise.resolve();  // 여기서 현재 실행 중단, Microtask로 등록
  console.log('C');         // 콜 스택이 비워진 뒤 재개
}

run();
console.log('B');
// 출력: A → B → C
```

중첩 Promise에서 `.then` 체인이 길수록 Microtask가 쌓인다. CPU를 오래 점유하는 연산이 Microtask 안에 있으면 렌더링 블록이 발생한다.

---

### JavaScript — 복사 & 스프레드

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Copy 개념](../Language/JavaScript/02_복사_및_스프레드/Copy_개념.md) | 얕은 복사·깊은 복사의 차이와 문제 상황 | 입문 |
| [Copy Deep Dive](../Language/JavaScript/02_복사_및_스프레드/Copy_Deep_Dive.md) | structuredClone, Lodash cloneDeep, 직렬화 한계 | 실무 |
| [Spread](../Language/JavaScript/02_복사_및_스프레드/Spread.md) | 스프레드 문법 기본 사용 패턴 | 입문 |
| [Spread Deep Dive](../Language/JavaScript/02_복사_및_스프레드/Spread_Deep_Dive.md) | 스프레드의 얕은 복사 함정, Rest와의 차이 | 실무 |
| [Destructuring & Template Literals](../Language/JavaScript/04_심화_JavaScript/Destructuring_and_Template_Literals.md) | 구조 분해 할당과 템플릿 리터럴 패턴 | 입문 |

---

### JavaScript — 성능 최적화

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Memoization](../Language/JavaScript/03_성능_최적화/Memoization.md) | 계산 결과 캐싱, WeakMap 활용 패턴 | 실무 |
| [Debouncing](../Language/JavaScript/03_성능_최적화/Debouncing.md) | 입력 이벤트 디바운스 구현과 적용 시점 | 실무 |
| [Throttling](../Language/JavaScript/03_성능_최적화/Throttling.md) | 스크롤·리사이즈 이벤트 스로틀링 | 실무 |
| [Garbage Collection](../Language/JavaScript/03_성능_최적화/Garbage_Collection.md) | V8 GC 알고리즘, 메모리 누수 패턴 진단 | 심화 |

---

### JavaScript — 심화 & 제너레이터

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [제너레이터 함수의 사용](../Language/JavaScript/06_제너레이터_이터레이터/제너레이터%20함수의%20사용.md) | function* 문법, yield, next() 동작 원리 | 실무 |
| [무한 시퀀스 생성](../Language/JavaScript/06_제너레이터_이터레이터/무한%20시퀀스%20생성.md) | 제너레이터로 지연 평가·무한 스트림 구현 | 심화 |
| [객체 동작 가로채기 (Proxy)](../Language/JavaScript/07_프록시_리플렉션/객체%20동작%20가로채기.md) | Proxy의 트랩 구조, 유효성 검사·로깅 활용 | 실무 |
| [속성 접근 제어 (Reflect)](../Language/JavaScript/07_프록시_리플렉션/속성%20접근%20제어.md) | Reflect API로 프로퍼티 접근 제어 | 실무 |
| [Map 개념](../Language/JavaScript/01_기본_JavaScript/Map/Map_개념.md) | Map vs Object, 키 타입·순서 보장·성능 차이 | 입문 |
| [Stack](../Language/JavaScript/04_심화_JavaScript/Stack.md) | 콜 스택과 메모리 스택 자료구조 | 입문 |
| [Child Process Spawn](../Language/JavaScript/04_심화_JavaScript/Child_Process_Spawn.md) | Node.js에서 자식 프로세스 생성·통신 | 실무 |
| [모듈 시스템](../Framework/Node/모듈 시스템/CommonJS vs ESM.md) | CommonJS vs ESM 차이, .cjs/.mjs 확장자 문제, 동적 import(), Top-level await | 실무 |

---

### JavaScript — 웹 & 보안

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [NodeJs Buffer와 TCP](../Language/JavaScript/10_웹_개발_및_보안/TCP/NodeJs%20Buffer와%20TCP.md) | Node.js Buffer 클래스와 TCP 소켓 연동 | 실무 |
| [Socket Manage](../Language/JavaScript/10_웹_개발_및_보안/TCP/Socket%20Manage.md) | TCP 소켓 연결 관리·재연결 전략 | 실무 |
| [pbkdf2](../Language/JavaScript/10_웹_개발_및_보안/pbkdf2.md) | 비밀번호 해싱 — PBKDF2 알고리즘과 Node.js 구현 | 실무 |

---

### TypeScript — 기본 개념 & 컴파일러

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [TypeScript 개요](../Language/TypeScript/TypeScript%20기본%20개념/TypeScript.md) | TS의 핵심 철학, JS와의 차이, 도입 근거 | 입문 |
| [tsc vs ts-node](../Language/TypeScript/TypeScript%20기본%20개념/tsc%20vs%20ts-node.md) | 컴파일 방식 vs 즉시 실행 방식의 차이와 선택 기준 | 입문 |
| [tsconfig](../Language/TypeScript/프로젝트%20설정%20및%20컴파일러/tsconfig/tsconfig.md) | compilerOptions 주요 항목 해설, strict 모드 | 실무 |
| [tsc](../Language/TypeScript/프로젝트%20설정%20및%20컴파일러/tsc.md) | tsc CLI 플래그, 증분 컴파일, watch 모드 | 실무 |
| [tsc-alias](../Language/TypeScript/TypeScript%20기본%20개념/tsc-alias.md) | 경로 별칭(alias)을 컴파일 후에도 유지하는 방법 | 실무 |
| [데코레이터](../Language/TypeScript/TypeScript%20기본%20개념/Decorator.md) | experimentalDecorators vs TC39 Stage 3, NestJS @Controller/@Injectable/@Guard 내부 동작 | 실무 |
| [tsc-alias와 workspace 함께 사용하기](../Language/TypeScript/프로젝트%20설정%20및%20컴파일러/tsc-alias와%20workspace%20함께%20사용하기.md) | 모노레포 환경에서 tsc-alias 적용 시 주의점 | 심화 |
| [Workspace와 ts_paths](../Language/TypeScript/타입%20유틸리티/module과%20moduleResolution.md) | module / moduleResolution 옵션 선택 기준 | 실무 |
| [ESLint와 Prettier](../Language/TypeScript/프로젝트%20설정%20및%20컴파일러/ESLint와%20Prettier.md) | TS 프로젝트에서 린터·포매터 설정 통합 | 실무 |

---

### TypeScript — 타입 시스템

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Interface](../Language/TypeScript/타입%20및%20타입%20정의/Object%20Types/Interface.md) | interface 선언, 확장, 구조적 타이핑 | 입문 |
| [Interface Deep Dive](../Language/TypeScript/타입%20및%20타입%20정의/Object%20Types/Interface_Deep_Dive.md) | 병합 선언, 함수 오버로드, 인덱스 시그니처 | 심화 |
| [Abstract Class vs Interface](../Language/TypeScript/타입%20및%20타입%20정의/Object%20Types/추상%20클래스.md) | 추상 클래스와 인터페이스 선택 기준 | 실무 |
| [Class](../Language/TypeScript/타입%20및%20타입%20정의/Object%20Types/Class.md) | TS 클래스 — 접근 제어자·생성자 단축 선언·readonly | 입문 |
| [접근 제어자](../Language/TypeScript/타입%20및%20타입%20정의/Object%20Types/접근%20제어자.md) | public · private · protected · readonly 동작 범위 | 입문 |
| [고급 타입 기법](../Language/TypeScript/타입%20및%20타입%20정의/고급%20타입%20기법.md) | 조건부 타입, 매핑 타입, 템플릿 리터럴 타입 | 심화 |
| [Type Assertion](../Language/TypeScript/타입%20및%20타입%20정의/Type_Assertion.md) | as 키워드의 올바른 사용법과 남용 방지 | 실무 |
| [any vs unknown vs never](../Language/TypeScript/타입%20및%20타입%20정의/Other%20Types/Any_Type_Deep_Dive.md) | 세 타입의 타입 안전성 차이와 실용적 선택 기준 | 실무 |
| [타입 정의 파일 (.d.ts)](../Language/TypeScript/타입%20및%20타입%20정의/타입%20정의%20파일.md) | @types 패키지와 직접 선언 파일 작성법 | 실무 |

---

### TypeScript — 타입 유틸리티 & 제네릭

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Generics](../Language/TypeScript/타입%20유틸리티/Generics.md) | 제네릭 기본 문법, 타입 파라미터 제약(extends) | 입문 |
| [유틸리티 타입](../Language/TypeScript/타입%20유틸리티/유틸리티%20타입.md) | Partial · Required · Pick · Omit · Record · Readonly 실용 예시 | 실무 |
| [Advanced Type Patterns](../Language/TypeScript/타입%20유틸리티/Advanced_Type_Patterns.md) | infer, 재귀 타입, 브랜딩, 빌더 패턴 타입화 | 심화 |

#### 제네릭 제약 패턴

타입 파라미터를 제약 없이 쓰면 속성 접근 시 컴파일 에러가 난다. `extends`로 필요한 구조를 명시한다.

```typescript
// extends: T는 length를 가진 타입만 허용
function getLength<T extends { length: number }>(arg: T): number {
  return arg.length;
}
getLength('hello');    // 5 — string은 length를 가진다
getLength([1, 2, 3]);  // 3
getLength(42);         // Error: number는 length가 없다

// keyof 조합: K는 T에 실제로 존재하는 키여야 한다
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
const user = { id: 1, name: 'alice' };
getProperty(user, 'name');   // 'alice'
getProperty(user, 'email');  // Error: 'email'은 keyof typeof user가 아니다

// 여러 제약 조합: & 인터섹션으로 묶는다
function merge<T extends object, U extends object>(a: T, b: U): T & U {
  return { ...a, ...b };
}

// 조건부 타입 + infer: 배열 요소 타입 추출
type ElementOf<T> = T extends Array<infer U> ? U : never;
type A = ElementOf<string[]>;   // string
type B = ElementOf<number[][]>; // number[]
type C = ElementOf<number>;     // never
```

유틸리티 타입은 내부적으로 이 패턴들의 조합이다. `Partial<T>`는 `{ [K in keyof T]?: T[K] }`, `ReturnType<T>`는 `T extends (...args: any[]) => infer R ? R : never`로 구현된다.

---

### Java — 핵심 개념 (JS/TS와 비교 참조용)

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [OOP](../Language/Java/객체지향%20프로그래밍%20(OOP)/OOP.md) | 객체지향 4대 원칙과 Java 구현 | 입문 |
| [Interface](../Language/Java/객체지향%20프로그래밍%20(OOP)/interface/Interface.md) | Java interface와 default 메서드 | 입문 |
| [Functional Interface](../Language/Java/객체지향%20프로그래밍%20(OOP)/interface/Functional_Interface.md) | @FunctionalInterface, 람다와의 연결 | 실무 |
| [Java Functional Programming](../Language/Java/함수형%20프로그래밍/Java_Functional_Programming.md) | 람다·스트림·Optional을 활용한 함수형 스타일 | 실무 |
| [Generics (Java)](../Language/Java/자바%20디자인%20패턴%20및%20원칙/Generics.md) | Java 제네릭 — 와일드카드·바운드·타입 소거 | 실무 |
| [Stream API](../Language/Java/컬렉션%20및%20데이터%20처리/Stream_API.md) | Java 스트림 파이프라인과 병렬 스트림 | 실무 |
| [Multi Threading](../Language/Java/멀티스레딩%20및%20동시성/Multi_Threading.md) | Thread·Runnable·synchronized 기본 | 입문 |
| [Java Concurrency Deep Dive](../Language/Java/멀티스레딩%20및%20동시성/Java_Concurrency_Deep_Dive.md) | CompletableFuture, Fork-Join, 동시성 패턴 심화 | 심화 |

### 언어 간 비교

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [타입 시스템 비교](../Language/Comparison/Type_System_Comparison.md) | Java·TS·Go·Rust 타입 시스템 차이 — 구조적 vs 명목적 타이핑 | 실무 |
| [동시성 모델 비교](../Language/Comparison/Concurrency_Models_Comparison.md) | Java 스레드 vs JS 이벤트 루프 vs Go 고루틴 비교 | 심화 |
| [에러 핸들링 비교](../Language/Comparison/Error_Handling_Across_Languages.md) | try-catch(Java·JS), Result(Rust), Go의 다중 반환 비교 | 실무 |
| [Null 처리 비교](../Language/Comparison/Null_Handling_Across_Languages.md) | Java Optional vs TS 옵셔널 체이닝 vs Kotlin Null Safety | 실무 |

---

## 읽는 순서

### JS 입문 → 중급 경로

1. **Scope / var·let·const** — 스코프 규칙부터 확실히 잡는다
2. **Hoisting** — 변수·함수 선언이 왜 끌어올려지는지 이해한다
3. **Closure → 렉시컬 스코프와 클로저의 관계** — 렉시컬 환경을 시각화한 뒤 클로저 개념을 고착시킨다
4. **This Binding → 일반 함수와 Arrow 함수** — this가 달라지는 네 가지 맥락을 정리한다
5. **Prototype → Constructor 개념** — 프로토타입 체인이 클래스 문법 뒤에서 어떻게 작동하는지 파악한다

### 비동기 심화 경로

6. **실행 순서 이해** — 콜 스택과 Microtask/Macrotask Queue의 처리 순서를 먼저 그림으로 이해한다
7. **Async/Await & Promise** — 실용적인 패턴과 에러 핸들링을 익힌다
8. **Promise 내부 동작 과정** — Microtask Queue와 상태 전이를 파고들어 심화 이해를 완성한다

### 성능 최적화 경로

9. **Debouncing → Throttling** — 이벤트 빈도 제어 두 기법을 대조 학습한다
10. **Memoization** — 계산 결과 캐싱 패턴을 익힌다
11. **Garbage Collection** — 메모리 누수 원인을 GC 관점에서 진단한다

### TypeScript 진입 경로

12. **TypeScript 개요 → tsc vs ts-node** — TS를 왜 쓰는지와 실행 방법을 파악한다
13. **tsconfig** — strict 옵션부터 paths까지 프로젝트 설정을 잡는다
14. **Interface → Class → 접근 제어자** — 타입 구조를 설계하는 기본 도구를 익힌다
15. **Generics → 유틸리티 타입** — 재사용 가능한 타입 작성법을 익힌다
16. **고급 타입 기법 → Advanced Type Patterns** — 조건부 타입·infer·브랜딩까지 확장한다

### Java↔JS/TS 비교 경로

17. **타입 시스템 비교** — 구조적 타이핑(TS)과 명목적 타이핑(Java)의 차이를 체감한다
18. **동시성 모델 비교** — 이벤트 루프와 스레드 모델 중 어느 쪽이 언제 유리한지 판단 기준을 세운다
19. **Null 처리 비교** — 언어마다 다른 Null 안전 전략을 한 눈에 비교한다

---

## 아직 없는 것

- **이벤트 루프 전용 문서** (`../Language/JavaScript/05_이벤트_루프_비동기/Event_Loop.md`) — Task Queue·Microtask Queue·rAF 큐의 처리 순서를 다이어그램과 함께 정리한 단독 문서
- **Symbol·WeakRef·FinalizationRegistry** (`../Language/JavaScript/04_심화_JavaScript/Symbol_WeakRef.md`) — ES2021+ 메모리 관리 API 문서
- **JavaScript 모듈 시스템** (`../Framework/Node/모듈 시스템/CommonJS vs ESM.md`) — CommonJS vs ESM, 동적 import(), Top-level await 비교
- **TS 프로젝트 레퍼런스(Project References)** (`../Language/TypeScript/프로젝트%20설정%20및%20컴파일러/Project_References.md`) — 모노레포에서 tsc --build로 증분 빌드 구성
- **JSDoc 심화** (`../Language/TypeScript/TypeScript%20기본%20개념/JSDoc.md`) — `@template`, `@overload`, `@satisfies` 등 TS 호환 JSDoc 전용 문서
- **Proxy 심화** (`../Language/JavaScript/07_프록시_리플렉션/Proxy_Reactive.md`) — Proxy로 반응형(Reactive) 시스템 구현하는 패턴 (Vue Reactivity 원리 등)
- **Web Worker / SharedArrayBuffer** (`../Language/JavaScript/08_모듈_시스템/Web_Worker.md`) — 멀티스레드 JS 활용 패턴
