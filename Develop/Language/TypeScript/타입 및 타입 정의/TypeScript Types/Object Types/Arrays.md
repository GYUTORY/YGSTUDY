---
title: TypeScript 배열 타입
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, arrays]
updated: 2026-04-20
---

# TypeScript 배열 타입

## 배경

TypeScript에서 배열은 런타임에는 JavaScript의 `Array` 그대로지만, 컴파일 타임에는 요소 타입이 하나로 제한되는 구조다. 자주 쓰는 자료구조라 별거 없어 보이지만, 선언 방식이 세 가지나 되고 각각 의미가 미묘하게 다르다. 튜플과 헷갈리는 경우도 많고, `readonly`를 붙이느냐 마느냐에 따라 함수 시그니처 설계가 완전히 달라진다.

실무에서 배열 타입을 잘못 쓰면 대부분 런타임까지 문제가 안 보인다. `any[]`로 받아놓고 나중에 속성 접근하다가 깨지거나, 함수에 배열을 넘겼는데 안에서 `push`로 수정해 버려서 호출부 상태가 바뀌는 식이다. 이런 문제는 배열 타입을 제대로 선언하는 것만으로도 대부분 컴파일 단계에서 걸린다.

## T[] vs Array\<T\>

동일한 타입이다. 다음 두 선언은 컴파일러 입장에서 완전히 같다.

```typescript
const a: number[] = [1, 2, 3];
const b: Array<number> = [1, 2, 3];
```

그러면 왜 두 가지가 존재하는가. 역사적으로 `Array<T>`가 제네릭 표기 그대로의 정식 형태이고, `T[]`는 그 숏핸드다. 팀 컨벤션 문서를 만들 거라면 대부분 `T[]`를 기본으로 쓰고 특정 상황에서만 `Array<T>`를 쓰는 방식을 택한다.

`T[]` 숏핸드가 부자연스러워지는 순간이 있다. 유니온 타입을 넣으면 괄호 누락으로 뜻이 완전히 달라진다.

```typescript
// 의도: string 또는 number가 들어가는 배열
let xs: string | number[];        // 실수. string 아니면 number[]라는 뜻
let ys: (string | number)[];      // 정확하지만 괄호가 지저분함
let zs: Array<string | number>;   // 가독성 좋음
```

함수 타입이나 조건부 타입을 요소로 둘 때도 `Array<T>` 쪽이 읽기 낫다. 반대로 단일 기본 타입이면 `T[]`가 간결하다. 이 기준만 지키면 섞여 있어도 일관성 문제는 거의 없다.

또 한 가지, `Array<T>`는 타입 별칭처럼 보이지만 사실 `lib.es5.d.ts`에 선언된 인터페이스다. 그래서 `Array` 프로토타입을 확장하는 `declare global` 코드와 상호작용할 때 `Array<T>` 쪽이 의도가 명확하다. 실무에서 흔한 경우는 아니지만, 라이브러리 d.ts를 들여다볼 때 알고 있어야 한다.

## readonly 배열

`readonly`는 배열의 내용 수정 가능 여부를 타입 레벨에서 막는다. 런타임 동작을 바꾸는 게 아니라, `push`, `pop`, `splice`, 인덱스 할당 같은 mutable 메서드/연산을 타입 시스템에서 거부한다.

```typescript
const xs: readonly number[] = [1, 2, 3];
xs.push(4);       // 오류: Property 'push' does not exist on type 'readonly number[]'
xs[0] = 10;       // 오류: Index signature in type 'readonly number[]' only permits reading
```

`Array<T>` 형태는 `ReadonlyArray<T>`로 쓴다. 의미는 같다.

```typescript
const ys: ReadonlyArray<number> = [1, 2, 3];
```

문제는 언제 readonly를 쓰느냐다. 실무 기준으로 세 가지 상황이 반복해서 나온다.

첫째, 함수 파라미터. 함수가 배열을 받아서 내용만 읽는다면 파라미터 타입을 `readonly T[]`로 선언해야 한다. 이렇게 해두면 함수 안에서 실수로 `sort`, `reverse`, `push` 같은 파괴적 메서드를 호출하는 순간 컴파일 에러가 난다. 호출부가 기대하지 않는 부작용을 원천 차단하는 용도다.

```typescript
function sum(xs: readonly number[]): number {
    // xs.sort();  // 오류로 막힘
    return xs.reduce((acc, x) => acc + x, 0);
}
```

둘째, 반환값. 내부 상태를 노출하는 getter가 배열을 그대로 돌려주는 경우, `readonly`로 반환해야 외부에서 수정해도 내부 상태가 오염되지 않는다. 방어적 복사를 매번 하는 비용을 피할 수 있다.

```typescript
class Cart {
    private _items: string[] = [];
    get items(): readonly string[] {
        return this._items;
    }
}
```

셋째, 상수 데이터. `as const`와 결합하면 리터럴 타입을 유지하면서 전체를 readonly로 만든다. enum 대체로 자주 쓰인다.

```typescript
const STATUSES = ['pending', 'active', 'done'] as const;
// type: readonly ['pending', 'active', 'done']
type Status = typeof STATUSES[number];  // 'pending' | 'active' | 'done'
```

`readonly`의 한계도 짚어야 한다. 얕은 수준만 막는다. 배열 자체는 못 바꿔도 요소가 객체면 그 객체의 속성은 바꿀 수 있다. 깊은 불변성이 필요하면 `readonly`를 재귀적으로 적용하는 유틸리티 타입이 따로 필요하다.

```typescript
const users: readonly { name: string }[] = [{ name: 'Alice' }];
users.push({ name: 'Bob' });   // 오류
users[0].name = 'Alice2';      // 통과. 깊은 readonly가 아니기 때문
```

그리고 `readonly T[]`는 `T[]`의 슈퍼타입이다. 즉 `T[]`를 `readonly T[]` 매개변수에 넘기는 건 되지만 반대는 안 된다. 이 방향성 덕분에 라이브러리 함수를 readonly로 설계해도 기존 호출부가 깨지지 않는다.

## 튜플과의 차이

배열과 튜플은 자주 혼동되지만 타입 시스템이 보는 관점은 완전히 다르다.

배열 `T[]`는 길이가 가변이고 모든 요소가 같은 타입이다. 튜플 `[A, B, C]`는 길이가 고정이고 각 위치의 타입이 따로 정해진다.

```typescript
const arr: string[] = ['a', 'b', 'c', 'd'];              // 길이 자유
const tup: [string, number, boolean] = ['x', 1, true];   // 정확히 3개

arr[10];         // 타입: string (실제로는 undefined일 수 있지만 타입은 string)
tup[0];          // 타입: string
tup[1];          // 타입: number
tup[3];          // 오류: 튜플 범위 밖
```

언뜻 보면 튜플이 더 엄격해 보이지만 함정이 있다. 기본 튜플은 `push` 같은 길이 확장 메서드를 여전히 허용한다.

```typescript
const t: [string, number] = ['a', 1];
t.push('b');          // 통과. 런타임에 길이 3이 됨
console.log(t);       // ['a', 1, 'b']
t[2];                 // 오류로 막힘. 타입 시스템은 여전히 길이 2로 인식
```

이게 타입과 런타임이 어긋나는 대표적 상황이다. 실무에서는 튜플을 선언할 때 거의 항상 `readonly`를 붙여 길이까지 잠근다.

```typescript
const t: readonly [string, number] = ['a', 1];
t.push('b');   // 오류
```

튜플을 언제 쓰는가. React의 `useState` 반환값, 좌표·색상처럼 위치가 의미를 갖는 값, 여러 값을 반환하는 함수의 결과를 구조 분해로 받고 싶을 때. 반대로 "같은 종류의 것이 여러 개"면 튜플이 아니라 배열이다. 역할이 다른 값을 묶는다면 튜플보다는 객체가 가독성이 훨씬 낫다. `[string, number]`가 무엇을 의미하는지 호출부만 보고는 알 수 없기 때문이다.

가변 인자 튜플(variadic tuple)은 함수의 나머지 파라미터를 타입 레벨에서 다룰 때 쓴다. 고급 기능이라 여기서 깊게 들어가지 않지만, `[string, ...number[]]` 같은 표기가 가능하다는 것만 기억해 두면 된다.

## 제네릭 배열 실전 예제

배열을 받고 배열을 반환하는 유틸리티 함수는 제네릭으로 잡아야 타입이 유지된다. `any[]`로 받으면 반환 타입도 무너진다.

### chunk: 고정 크기로 쪼개기

```typescript
function chunk<T>(xs: readonly T[], size: number): T[][] {
    if (size <= 0) throw new Error('size must be > 0');
    const result: T[][] = [];
    for (let i = 0; i < xs.length; i += size) {
        result.push(xs.slice(i, i + size));
    }
    return result;
}

const groups = chunk([1, 2, 3, 4, 5], 2);
// 타입: number[][]
// 값: [[1, 2], [3, 4], [5]]
```

파라미터를 `readonly T[]`로 받는 이유는 앞서 말한 방어적 설계다. 함수 안에서 `slice`만 쓰지 `push`로 원본을 건드리지 않겠다는 계약을 타입으로 선언한다.

### groupBy: 키 함수로 그룹화

```typescript
function groupBy<T, K extends string | number | symbol>(
    xs: readonly T[],
    keyOf: (item: T) => K
): Record<K, T[]> {
    const result = {} as Record<K, T[]>;
    for (const item of xs) {
        const key = keyOf(item);
        (result[key] ??= []).push(item);
    }
    return result;
}

interface Order { userId: number; amount: number; }
const orders: Order[] = [
    { userId: 1, amount: 1000 },
    { userId: 2, amount: 500 },
    { userId: 1, amount: 300 },
];

const byUser = groupBy(orders, o => o.userId);
// 타입: Record<number, Order[]>
```

`K extends string | number | symbol`로 제약을 거는 이유는 객체 키로 쓸 수 있는 타입으로 좁히기 위해서다. 제약을 안 걸면 `keyOf`가 `boolean`을 반환해도 컴파일러가 받아버려서 `Record`가 깨진다.

### 튜플을 반환하는 함수

배열 요소를 두 그룹으로 나누는 `partition`은 튜플 반환의 전형적인 예다.

```typescript
function partition<T>(
    xs: readonly T[],
    pred: (item: T) => boolean
): [T[], T[]] {
    const yes: T[] = [];
    const no: T[] = [];
    for (const x of xs) {
        (pred(x) ? yes : no).push(x);
    }
    return [yes, no];
}

const [evens, odds] = partition([1, 2, 3, 4, 5], n => n % 2 === 0);
// evens: number[], odds: number[]
```

반환 타입을 `T[][]`로 하면 `[evens, odds]` 분해 시 둘 다 `number[]`가 맞긴 하지만, 호출부에서 "정확히 두 개가 나온다"는 보장이 사라진다. 튜플로 선언하는 게 정확하다.

### 읽기 전용 함수 시그니처 관례

라이브러리를 쓰다 보면 내부에서 입력을 건드리는 것처럼 보이는 함수가 있다. 예를 들어 배열을 정렬해서 반환한다고 해놓고 원본 배열도 정렬해 버리는 경우다. 이런 동작은 직접 작성하는 함수에서는 `readonly T[]` 시그니처로 원천 차단한다.

```typescript
function sortedCopy<T>(
    xs: readonly T[],
    compare: (a: T, b: T) => number
): T[] {
    return [...xs].sort(compare);
}
```

호출자는 `sortedCopy`가 원본을 건드리지 않는다는 걸 시그니처만 보고 알 수 있다. 내부에서 실수로 `xs.sort()`를 쓰려 해도 컴파일 에러가 난다.

## 주의사항

배열 타입을 쓸 때 반복적으로 발생하는 문제들을 정리한다.

첫째, 인덱스 접근은 타입 시스템이 `undefined`를 반환하지 않는다고 본다. `xs[10]`은 배열 길이를 넘어도 타입상 `T`다. 이게 의외로 런타임 오류의 주범이다. `tsconfig.json`에서 `noUncheckedIndexedAccess: true`를 켜면 인덱스 접근 결과가 `T | undefined`로 바뀐다. 새 프로젝트는 켜고 시작하는 게 낫고, 기존 프로젝트는 켜는 순간 오류가 수백 개 뜰 수 있어서 팀 논의가 필요하다.

둘째, 빈 배열 리터럴의 타입 추론. `const xs = []`의 타입은 `never[]`가 되는데, 이후 어떤 요소를 `push`해도 타입이 넓혀지지 않는 함정이 있다. 명시적으로 타입을 달아야 한다.

```typescript
const xs = [];           // never[]
xs.push(1);              // 오류: Argument of type 'number' is not assignable to 'never'

const ys: number[] = []; // 정상
ys.push(1);
```

셋째, `Array.from`과 제네릭. 이터러블에서 배열을 만들 때 타입 추론이 의도와 다르게 나올 때가 있다. 특히 `Map`, `Set`에서 변환할 때는 제네릭을 명시하는 쪽이 안전하다.

넷째, `any[]`는 `unknown[]`로 바꿔라. `any[]`를 받으면 내부에서 아무 메서드나 호출해도 통과돼서 타입 시스템이 마비된다. 외부 입력이라 타입을 모르겠다면 `unknown[]`로 받고 사용 지점에서 좁히는 게 원칙이다.

## 참고

TypeScript Handbook의 해당 섹션은 Everyday Types > Arrays에서 기본을 다루고, Object Types > Tuple Types에서 튜플 문법을 정리한다. `ReadonlyArray<T>`의 정확한 인터페이스는 `lib.es5.d.ts`를 직접 열어보는 게 가장 빠르다. `Array<T>` 인터페이스에서 mutable 메서드가 빠진 형태로 정의돼 있다.
