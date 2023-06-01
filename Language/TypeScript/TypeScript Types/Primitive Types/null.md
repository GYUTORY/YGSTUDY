
# null
- TypeScript에서 null은 값이 없음을 명시적으로 나타내기 위해 사용되는 특별한 타입입니다. 
- null은 JavaScript의 원시 타입 중 하나이며, 변수에 의도적으로 할당됩니다.

# null의 특징과 사용법

1. 값이 없는 변수
- 변수에 null을 할당하여 값이 없음을 나타낼 수 있습니다.
- 예를 들어, 다음과 같이 변수를 null로 초기화할 수 있습니다:
```typescript
let name: string | null = null;
console.log(name); // 출력: null
```

2. 의도적으로 값이 없음을 나타내는 경우:
- 변수에 null을 할당하여 의도적으로 값이 없음을 나타낼 수 있습니다.
- 예를 들어, 데이터베이스에서 값이 없는 경우를 나타내기 위해 null을 사용할 수 있습니다.

3. 선택적 속성
- 인터페이스나 타입에서 속성을 선택적으로 정의할 때, 해당 속성은 null일 수 있음을 나타낼 수 있습니다.
- 예를 들어, 다음과 같이 인터페이스에서 속성을 선택적으로 정의할 수 있습니다:
```typescript
interface Person {
    name: string;
    age: number | null;
}
```

이 경우, age 속성은 선택적이므로 값이 할당되지 않으면 해당 속성은 null이 될 수 있습니다.


4. 타입 가드
- null인지 확인하기 위해 타입 가드를 사용할 수 있습니다.
- 예를 들어, 다음과 같이 타입 가드를 사용하여 값이 null인지 확인할 수 있습니다:
```typescript
function processValue(value: string | null) {
    if (value !== null) {
    // value가 null이 아닌 경우에만 실행되는 코드
    console.log(value.toUpperCase());
    }
}
```
- null은 값이 없음을 나타내는 타입으로 사용됩니다.
- 변수에 의도적으로 null을 할당하거나 선택적 속성으로 정의할 수 있습니다.
- null은 undefined와 다르게 값이 명시적으로 없음을 나타내는 용도로 사용됩니다.


# 그렇다면, null과 undefined의 정확한 차이가 뭘까?
1. 값의 할당
undefined
- 변수가 선언되었지만 초기화되지 않거나, 함수가 반환 값을 가지지 않을 때 자동으로 할당됩니다.
null
- 의도적으로 값이 없음을 나타내기 위해 할당되는 값입니다.


2. 타입
undefined
- 타입으로서 undefined 타입을 가집니다.
null
- 타입으로서 null 타입을 가집니다.

3. 할당 가능성
undefined
- 모든 타입에 할당될 수 있습니다. 즉, undefined는 다른 모든 값에 할당될 수 있습니다.
null
- null 타입이나 any 타입에만 할당될 수 있습니다.

4. 엄격한 할당 검사
- TypeScript 컴파일러의 strictNullChecks 옵션이 활성화되어 있다면, undefined와 null을 다른 타입에 할당하는 것은 엄격히 검사됩니다. 
- 이 옵션이 비활성화되어 있다면, undefined와 null이 다른 타입에 자동으로 할당될 수 있습니다.

5. 타입 가드
- undefined를 체크하기 위한 타입 가드로 typeof 또는 strictNullChecks 옵션이 활성화되어 있을 때 x === undefined를 사용할 수 있습니다.
- null을 체크하기 위해서는 명시적으로 x === null을 사용해야 합니다.

