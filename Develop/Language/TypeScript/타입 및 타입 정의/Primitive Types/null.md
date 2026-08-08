---
title: TypeScript null 타입
tags: [language, typescript, javascript]
updated: 2026-07-27
---

# TypeScript null 타입

## null이란

TypeScript에서 `null`은 개발자가 직접 "값이 없다"고 표시할 때 쓰는 타입이다. `undefined`가 자바스크립트 런타임이 자동으로 만들어내는 값이라면, `null`은 코드에 직접 써야만 나온다. 선언만 하고 초기화하지 않은 변수에는 `undefined`가 들어가지만, `null`은 누군가가 의도적으로 집어넣어야 한다.

`strictNullChecks` 옵션이 꺼져 있으면 `null`은 모든 타입에 할당할 수 있어서 컴파일러가 null 관련 버그를 잡아주지 못한다. 켜면 `null`은 `null` 타입에만 속하고, 다른 타입 변수에 넣으려면 유니온으로 명시해야 한다. `strict: true`를 쓰면 `strictNullChecks`가 자동으로 켜진다. 프로젝트 초기에 켜두지 않으면 나중에 옵션을 추가할 때 빌드 에러가 수백 개씩 쏟아지므로, 시작할 때 설정해두는 게 낫다.

```json
{
  "compilerOptions": {
    "strict": true
  }
}
```

## null과 undefined의 실무적 차이

`undefined`는 런타임이 만들고, `null`은 개발자가 만든다는 원칙으로 구분하면 된다. 자바스크립트 엔진은 초기화하지 않은 변수, 함수 반환 없음, 존재하지 않는 객체 키 접근 같은 상황에서 자동으로 `undefined`를 만들어낸다. `null`은 코드에 직접 작성하지 않으면 나오지 않는다.

이 차이가 실제 문제로 이어지는 건 JSON 직렬화 때다.

```typescript
JSON.stringify({ a: null, b: undefined, c: 1 });
// '{"a":null,"c":1}' — b 키가 아예 사라진다
```

`undefined`는 JSON 표준에 없는 값이라 직렬화하면 키 자체가 빠진다. 객체에서는 키가 사라지고, 배열에서는 `null`로 변환된다.

```typescript
JSON.stringify([null, undefined, 1]);
// '[null,null,1]' — 배열에서는 null로 바뀐다
```

PATCH 요청에서 "이 필드를 null로 비워달라"는 의도와 "이 필드를 건드리지 않는다"를 구분해야 할 때, `undefined`가 사라지는 동작 때문에 구분 자체가 불가능해진다. 그래서 외부 API 경계에서는 `null`로 통일하는 게 운영 편의상 낫다.

## 선언과 기본 사용

null을 허용하는 변수는 유니온 타입으로 선언한다. `strictNullChecks`가 켜져 있으면 `string` 타입 변수에 `null`을 넣으면 컴파일 에러가 나므로, 허용할 타입을 명시적으로 선언해야 한다.

```typescript
let name: string | null = null;
let userId: number | null = null;

name = "홍길동";
name = null; // 다시 null로 설정 가능
```

함수 반환값도 마찬가지다.

```typescript
function findUser(id: number): User | null {
    return users.find(u => u.id === id) ?? null;
}
```

`Array.prototype.find`는 결과가 없으면 `undefined`를 반환하는데, `?? null`로 `null`로 변환했다. 반환 타입을 `User | undefined`로 두면 API 응답 직렬화 시 키가 사라지는 문제가 생기기 때문이다.

## 인터페이스에서 null과 옵셔널의 차이

인터페이스에서 null 허용 필드와 옵셔널 필드는 의미가 다르다.

```typescript
interface User {
    id: number;
    email: string | null;  // 키는 반드시 있고, 값이 null일 수 있다
    phone?: string;        // 키 자체가 없어도 된다
}
```

`email: string | null`은 객체를 만들 때 `email` 키를 반드시 써야 한다. `phone?: string`은 키를 아예 생략해도 통과한다.

```typescript
const u1: User = {
    id: 1,
    email: null,    // OK — 키는 있고 값이 null
    // phone 없어도 OK
};

// email 키를 생략하면 컴파일 에러
const u2: User = {
    id: 2,
    email: "user@example.com",
};
```

데이터베이스 컬럼처럼 "필드는 항상 존재하지만 값이 비어 있을 수 있는" 경우는 `string | null`이 맞다. "이 속성 자체가 없어도 되는" 경우는 옵셔널(`?:`)이 맞다. 이 둘을 혼용하면 객체를 만드는 쪽에서 어느 필드를 써야 하는지 헷갈린다.

## null 체크 패턴

`strictNullChecks`가 켜져 있으면 null 체크 없이 메서드를 호출하면 컴파일 에러가 난다. TypeScript의 control flow analysis가 if 문 안에서 타입을 좁혀주기 때문에, 체크 이후에는 null 없이 쓸 수 있다.

```typescript
function getLength(s: string | null): number {
    if (s === null) {
        return 0;
    }
    return s.length; // 여기서 s는 string으로 좁혀진다
}
```

`== null`로 체크하면 `undefined`도 같이 걸러진다. 의도적으로 null과 undefined를 한 번에 처리하고 싶을 때 쓰기도 하지만, 읽는 사람이 의도를 오해할 수 있어서 `=== null`과 `=== undefined`를 분리해서 쓰는 게 더 명확하다.

기본값을 넣을 때 `??`와 `||`를 혼용하면 버그가 생긴다. `||`는 falsy 값(0, "", false)을 모두 걸러내고, `??`는 null과 undefined만 걸러낸다.

```typescript
// 사용자가 timeout을 0으로 설정하면
const timeout = config.timeout ?? 3000; // 0 그대로 유지
const timeout = config.timeout || 3000; // 0이 falsy라서 3000으로 덮어씀
```

설정값에 0이나 빈 문자열이 유효한 값으로 들어올 수 있다면 `??`를 써야 한다. `||`는 0과 빈 문자열도 "값 없음"으로 취급한다는 의도가 명확한 경우에만 쓴다.

## API 응답에서 null 처리

실무에서 null을 가장 자주 만나는 건 외부 API나 데이터베이스 쿼리 결과다.

```typescript
interface ApiResponse<T> {
    data: T | null;
    error: string | null;
}

async function fetchUser(id: number): Promise<ApiResponse<User>> {
    try {
        const response = await fetch(`/api/users/${id}`);
        const data = await response.json();

        if (response.ok) {
            return { data, error: null };
        }
        return { data: null, error: data.message ?? "요청 실패" };
    } catch {
        return { data: null, error: "네트워크 오류" };
    }
}

const result = await fetchUser(1);
if (result.data !== null) {
    console.log(result.data.name); // null 체크 후 안전하게 접근
}
```

응답 타입에 옵셔널 프로퍼티(`?:`)를 쓰면 키 존재 여부도 확인해야 해서 처리 코드가 복잡해진다. 키는 항상 있되 값이 `null`인 구조로 잡으면 null 체크 한 번으로 끝난다.

## 배열에서 null 걸러내기

배열에서 null을 제거할 때 `filter(Boolean)`을 자주 쓰는데, 이 방법은 실제 값은 걸러지지만 타입이 좁혀지지 않는다.

```typescript
const arr: (string | null)[] = ["a", null, "b"];

const wrong = arr.filter(Boolean);
// 타입: (string | null)[] — 좁혀지지 않음
```

`Boolean`은 type predicate 시그니처가 아니라서 컴파일러가 결과 타입을 좁히지 못한다. 이후에 `.length`를 쓰면 다시 에러가 난다. type predicate 함수를 만들어 두고 쓰는 게 깔끔하다.

```typescript
function isNotNull<T>(value: T | null): value is T {
    return value !== null;
}

const correct = arr.filter(isNotNull);
// 타입: string[] — 올바르게 좁혀짐
```

nullish까지 걸러내야 한다면 조건을 추가한다.

```typescript
function isNotNullish<T>(value: T | null | undefined): value is T {
    return value !== null && value !== undefined;
}
```

## Optional Chaining과 null

중첩 객체를 다룰 때 null 체크를 if 문으로 반복하면 코드가 길어진다. `?.`는 null이나 undefined를 만나는 시점에 멈추고 `undefined`를 반환한다.

```typescript
interface User {
    profile: {
        name: string;
        avatar: string | null;
    } | null;
}

function getAvatar(user: User): string {
    return user.profile?.avatar ?? "default.webp";
}
```

`user.profile`이 null이면 `?.` 시점에 멈추고 undefined가 된다. `?? "default.webp"`가 undefined를 기본값으로 대체한다. `?.`는 null과 undefined만 멈추게 하고, 다른 falsy 값(0, "")은 그대로 통과시킨다는 점을 기억해두면 예상치 못한 동작을 피할 수 있다.
