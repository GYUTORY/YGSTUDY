
# never
- 절대로 발생하지 않는 값의 타입을 나타냅니다.
- never는 주로 예외 처리, 무한 반복 또는 함수의 반환 유형으로 사용됩니다.

> never 타입은 아래와 같은 상황에서 사용됩니다.

예외 처리
- 예외가 발생할 때 함수가 예외를 던지고 프로그램이 중단될 수 있다는 것을 나타내기 위해 never를 사용할 수 있습니다.
```typescript
function throwError(message: string): never {
throw new Error(message);
}
```

무한 반복
- 함수가 끝나지 않고 계속해서 반복되는 경우 never를 반환하는 것이 적합합니다.
```typescript
function infiniteLoop(): never {
    while (true) {
    // Do something indefinitely
    }
}
```

타입 가드
- 타입 가드를 사용하여 모든 경우를 처리하고 남은 경우에 never를 반환할 수 있습니다.
```typescript
function processValue(value: string | number): void {
    if (typeof value === 'string') {
    // Handle string case
    } else if (typeof value === 'number') {
    // Handle number case
    } else {
    // Value can never be anything other than string or number
    const exhaustiveCheck: never = value;
    // ...
    }
}
```

# 정리
- never 타입은 타입 시스템의 논리적인 완성성을 유지하기 위해 사용됩니다. 
- 즉, 해당 코드 블록이 실행되면 함수가 더 이상 진행되지 않거나 예외가 발생하므로 다른 타입은 절대로 나타날 수 없다는 것을 나타냅니다.
- never 타입은 일반적으로 특정한 상황에 사용되며, 보통 프로그램의 일반적인 흐름에서는 잘 사용되지 않습니다.