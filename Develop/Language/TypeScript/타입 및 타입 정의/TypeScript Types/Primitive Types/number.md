
# number
- TypeScript에서의 기본 데이터 타입으로, 숫자 값을 나타냅니다.
- 정수와 소수점을 포함한 숫자 값을 표현할 수 있습니다.

```typescript
let intValue: number = 42;
let floatValue: number = 3.14;
```

- number 타입은 양수, 음수, 0을 포함한 모든 숫자 값을 표현할 수 있습니다. 
- TypeScript는 JavaScript와 마찬가지로 숫자 값을 64비트 부동소수점 형태로 처리합니다.

```typescript
let sum: number = 10 + 5; // 덧셈 연산
let product: number = 8 * 4; // 곱셈 연산

for (let i: number = 0; i < 5; i++) { // 반복문의 카운터로 사용
  console.log(i);
}
```

위의 예시에서는 숫자 값을 사용하여 덧셈, 곱셈 연산을 수행하고, 반복문에서 카운터로 사용합니다.

number 타입은 TypeScript에서 자주 사용되는 기본 데이터 타입 중 하나이며, 수치 연산이 필요한 다양한 상황에서 활용됩니다.

