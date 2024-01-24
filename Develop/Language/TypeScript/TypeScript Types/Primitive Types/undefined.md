
# undefined
- 값이 할당되지 않은 변수의 상태를 나타내는 특별한 타입입니다.
- undefined는 JavaScript의 원시 타입 중 라나이며, 값이 없음을 나타냅니다.

# undefind의 특징과 사용법
1. 값이 할당되지 않은 변수
- 변수가 선언되었지만 초기화되지 않은 경우, 해당 변수의 값은 undefined가 됩니다.
- 예를 들어, 다음과 같이 변수를 선언하지만 값을 할당하지 않으면 변수는 undefined가 됩니다:

```typescript
let name: string;
console.log(name); // 출력: undefined
```

2. 함수의 반환 값
- 함수가 어떤 값을 반환하지 않는 경우, 반환 타입으로 undefined를 명시할 수 있습니다.
- 예를 들어, 다음과 같이 반환 타입으로 undefined를 명시한 함수를 정의할 수 있습니다:
```typescript
function logMessage(message: string): void {
    console.log(message);
    return undefined;
}
```

3. 선택적 속성
- 인터페이스나 타입에서 속성을 선택적으로 정의할 때, 해당 속성은 undefined일 수 있음을 나타낼 수 있습니다.
- 예를 들어, 다음과 같이 인터페이스에서 속성을 선택적으로 정의할 수 있습니다:
```typescript
interface Person {
    name: string;
    age?: number;
}
```

이 경우, age 속성은 선택적이므로 값을 할당하지 않으면 해당 속성은 undefined가 됩니다.

4. 타입 가드
- undefined인지 확인하기 위해 타입 가드를 사용할 수 있습니다.
- 예를 들어, 다음과 같이 타입 가드를 사용하여 값이 undefined인지 확인할 수 있습니다:
```typescript
function processValue(value: string | undefined) {
if (value !== undefined) {
    // value가 undefined가 아닌 경우에만 실행되는 코드
    console.log(value.toUpperCase());
    }
}
```