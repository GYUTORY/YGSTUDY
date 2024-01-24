
# unknown
- 모든 타입의 상위 타입으로, 어떤 값이든 할당할 수 있습니다. 
- unknown은 JavaScript의 any와 비슷한 역할을 하지만, 타입 안정성을 제공하기 위해 명시적으로 사용됩니다.

# 특징

1. 할당 가능성
- unknown은 어떤 값이든 할당할 수 있습니다.

```typescript
let value: unknown;

value = 123; // OK
value = 'hello'; // OK
value = true; // OK
```


2. 타입 안전성
- unknown을 다른 타입으로 할당하려면 명시적인 타입 확인이 필요합니다.
- 이는 값의 타입을 검사하고 타입을 추론할 때 안전한 작업을 보장하기 위해 사용됩니다.

```typescript
let value: unknown;

let numberValue: number = value; // Error: Type 'unknown' is not assignable to type 'number'

if (typeof value === 'number') {
    numberValue = value; // OK, 타입 가드를 사용하여 타입 확인
}
```


3. 타입 검사
- unknown 타입의 값에 대해서는 거의 모든 작업이 허용되지 않습니다. 
- 값을 사용하기 전에 타입을 검사하고 필요한 작업을 수행해야 합니다.

```typescript
let value: unknown;

let length: number;

// Error: Object is of type 'unknown'
length = value.length;

if (typeof value === 'string') {
length = value.length; // OK, 타입 가드를 사용하여 타입 확인
}
```

# 정리
- unknown은 타입 안전성을 강화하기 위해 사용되는 타입이며, 타입이 정확히 알려지지 않은 값을 다룰 때 유용합니다. 
- 하지만 unknown은 사용하기 전에 타입 검사를 수행해야 하므로 가능하면 더 구체적인 타입을 사용하는 것이 좋습니다.




