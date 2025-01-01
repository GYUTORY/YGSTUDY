
# TypeScript 타입 단언 (Type Assertion)

TypeScript에서 **타입 단언 (Type Assertion)**은 개발자가 특정 값의 타입을 "알려주는" 방식으로 사용됩니다.
즉, 컴파일러가 타입 추론을 제대로 하지 못하거나, 개발자가 타입을 명확히 알고 있는 경우에 사용합니다.

타입 단언은 두 가지 형태로 작성할 수 있습니다:
1. `as` 키워드 사용
2. 꺾쇠 괄호(`<>`) 사용 (React JSX 문법과 충돌 가능성 때문에 권장되지 않음)

## 타입 단언의 기본 문법

```typescript
// as 키워드 사용
let someValue: unknown = "Hello, TypeScript";
let strLength: number = (someValue as string).length;

// 꺾쇠 괄호 사용
let someValue2: unknown = "Hello, TypeScript";
let strLength2: number = (<string>someValue2).length;
```

## 타입 단언이 필요한 상황

### 1. 컴파일러가 타입을 제대로 추론하지 못할 때
TypeScript 컴파일러는 `unknown` 또는 `any` 타입으로 추론된 변수의 타입을 명확히 알지 못합니다. 이럴 때 타입 단언을 사용하여 특정 타입으로 명시할 수 있습니다.

```typescript
let someValue: any = "Hello, TypeScript";

// 컴파일러가 someValue를 문자열로 간주하지 않음
console.log(someValue.length); // 오류 발생

// 타입 단언으로 해결
let strLength: number = (someValue as string).length;
console.log(strLength); // 17
```

### 2. DOM 요소를 다룰 때
DOM 요소를 가져올 때 TypeScript는 기본적으로 `HTMLElement | null` 타입을 반환합니다. 이를 구체적인 요소 타입으로 변환해야 할 때 타입 단언을 사용할 수 있습니다.

```typescript
let inputElement = document.getElementById("myInput") as HTMLInputElement;

// inputElement가 HTMLInputElement 타입임을 명시
inputElement.value = "Hello!";
```

### 3. API 응답 처리
외부 API에서 데이터를 받아올 때, TypeScript는 데이터를 `any`로 간주할 수 있습니다.
타입 단언을 사용하여 데이터를 원하는 타입으로 변환할 수 있습니다.

```typescript
interface User {
  id: number;
  name: string;
}

let apiResponse: any = { id: 1, name: "John Doe" };
let user = apiResponse as User;

console.log(user.name); // John Doe
```

## 타입 단언의 주의사항

- **타입 강제**: 타입 단언은 컴파일러가 타입 검사를 건너뛰도록 하기 때문에, 잘못된 단언은 런타임 에러를 유발할 수 있습니다.

```typescript
let someValue: any = 42;

// 잘못된 타입 단언
let strValue: string = someValue as string;
console.log(strValue.length); // 런타임 에러 발생
```

- **타입 안전성 확보**: 타입 단언은 필요할 때만 사용하며, 타입 검증을 우선적으로 고려하는 것이 좋습니다.

## 결론

타입 단언은 TypeScript에서 강력한 도구이지만, 신중하게 사용해야 합니다.
타입 단언을 사용하기 전에 타입 검증을 통해 안전성을 확보하거나,
TypeScript가 제공하는 타입 시스템을 최대한 활용하는 것이 권장됩니다.
