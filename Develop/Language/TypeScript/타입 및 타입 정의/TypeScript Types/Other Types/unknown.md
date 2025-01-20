
# TypeScript `unknown`

`unknown`은 TypeScript에서 가장 안전한 타입 중 하나로, **아직 타입을 알 수 없는 값**을 나타냅니다. `unknown`은 모든 타입의 값을 할당할 수 있지만, 타입이 확실해지기 전까지는 어떤 연산도 수행할 수 없습니다.

---

## 👉🏻 `unknown`의 기본 개념

- `unknown`은 모든 타입의 **슈퍼 타입**입니다. 즉, 어떤 값도 `unknown`에 할당할 수 있습니다.
- 그러나, `unknown` 타입의 값은 **명시적으로 타입을 확인**하거나 **타입 단언(Type Assertion)**을 사용하기 전까지는 접근하거나 조작할 수 없습니다.

### 기본 사용법

```typescript
let value: unknown; // 타입이 unknown으로 설정됨

value = "Hello"; // string 할당 가능
value = 42; // number 할당 가능
value = true; // boolean 할당 가능
```

#### 주석으로 설명:
- `unknown`은 모든 타입의 값을 수용할 수 있는 유연성을 제공합니다.
- 하지만, `unknown` 값은 타입이 명확히 확인되기 전까지 안전하지 않은 동작을 허용하지 않습니다.

---

## ✨ `unknown`과 `any`의 차이점

`unknown`은 `any`와 유사해 보이지만, 훨씬 **안전한 타입**입니다.

### 비교 예제

```typescript
let anyValue: any;
let unknownValue: unknown;

anyValue = "Hello";
unknownValue = "Hello";

console.log(anyValue.toUpperCase()); // 정상 작동 (런타임 오류 가능)
// console.log(unknownValue.toUpperCase()); // 오류: unknown 타입에는 toUpperCase가 없음
```

#### 주석으로 설명:
- `any` 타입은 어떤 동작도 허용하지만, 런타임 오류가 발생할 위험이 큽니다.
- 반면, `unknown` 타입은 타입이 명확히 확인되지 않으면 위험한 작업을 금지합니다.

---

## 👉🏻 `unknown`의 타입 확인

`unknown` 값을 사용하려면 타입을 확인하거나 단언해야 합니다.

### 타입 확인 사용

```typescript
function printValue(value: unknown): void {
    if (typeof value === "string") { // 타입이 string인지 확인
        console.log(value.toUpperCase()); // string으로 안전하게 처리 가능
    } else {
        console.log("값이 문자열이 아닙니다.");
    }
}

printValue("Hello"); // HELLO
printValue(42); // 값이 문자열이 아닙니다.
```

#### 주석으로 설명:
- `typeof`와 같은 타입 보호(Type Guard)를 사용하여 `unknown` 값을 안전하게 처리합니다.

### 타입 단언 사용

```typescript
let value: unknown = "Hello";

console.log((value as string).toUpperCase()); // 타입 단언으로 string으로 변환
```

#### 주석으로 설명:
- `as` 키워드를 사용하여 `unknown` 값을 특정 타입으로 단언합니다.

---

## ✨ `unknown`과 조건부 타입

`unknown`은 조건부 타입과 함께 사용할 때 유용합니다.

```typescript
type ProcessedValue<T> = T extends string ? string : never;

function processValue<T>(value: T): ProcessedValue<T> {
    if (typeof value === "string") {
        return value.toUpperCase() as ProcessedValue<T>;
    }
    throw new Error("문자열만 처리할 수 있습니다.");
}

console.log(processValue("hello")); // HELLO
// console.log(processValue(42)); // 오류 발생
```

#### 주석으로 설명:
- 조건부 타입을 사용하여 `T`가 문자열일 때만 처리하도록 제한합니다.

---

## 🛠️ `unknown`의 실용적인 활용

### JSON 파싱

```typescript
function parseJson(json: string): unknown {
    return JSON.parse(json); // 파싱된 값은 unknown 타입으로 반환
}

const result = parseJson('{"name": "Alice", "age": 25}');

if (typeof result === "object" && result !== null) {
    console.log((result as { name: string }).name); // Alice
}
```

#### 주석으로 설명:
- JSON 데이터를 파싱한 결과는 타입이 불확실하므로 `unknown`으로 처리합니다.
- 타입 확인 후 안전하게 사용합니다.

### 사용자 입력 값 처리

```typescript
function handleInput(input: unknown): void {
    if (typeof input === "string") {
        console.log("입력은 문자열입니다:", input);
    } else if (typeof input === "number") {
        console.log("입력은 숫자입니다:", input);
    } else {
        console.log("알 수 없는 타입의 입력입니다.");
    }
}

handleInput("Hello");
handleInput(123);
handleInput(true);
```

#### 주석으로 설명:
- 사용자가 제공한 값의 타입이 불확실할 때 `unknown`을 사용하여 타입 확인을 강제합니다.

---

## 📋 `unknown`의 주요 특징 요약

| 특징                         | 설명                                            |
|-----------------------------|-----------------------------------------------|
| **모든 타입의 슈퍼 타입**       | 모든 타입의 값을 할당할 수 있음                              |
| **타입 확인이 필요**            | 값을 사용하기 전에 반드시 타입 확인 또는 단언 필요                 |
| **안전한 타입**                | `any`보다 엄격하여 런타임 오류 가능성을 줄임                     |
| **조건부 타입과 호환**          | 조건부 타입과 함께 유연하고 안전한 타입 설계 가능                  |

---

## 🛠️ `unknown` 활용 예제

`unknown`은 주로 타입이 미리 정해지지 않은 데이터를 처리할 때 사용됩니다.

```typescript
type ApiResponse = unknown;

function handleApiResponse(response: ApiResponse): void {
    if (typeof response === "object" && response !== null) {
        if ("status" in response) {
            console.log(`API 상태: ${(response as { status: string }).status}`);
        }
    } else {
        console.error("올바르지 않은 응답 형식입니다.");
    }
}

handleApiResponse({ status: "success" }); // API 상태: success
handleApiResponse("Invalid"); // 올바르지 않은 응답 형식입니다.
```

---
