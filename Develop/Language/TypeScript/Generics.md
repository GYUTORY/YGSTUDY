

## TypeScript 제너릭 (Generics)란?
- TypeScript의 제너릭은 코드의 재사용성을 높이고, 타입 안전성을 강화하는 기능입니다.
- 제너릭을 사용하면 특정 타입에 의존하지 않고, 다양한 타입을 처리할 수 있는 유연한 함수를 작성할 수 있습니다.


### 1. 기본 개념
- 제너릭은 함수, 클래스, 인터페이스에서 사용할 수 있으며, 타입 매개변수를 통해 다양한 타입을 매개변수로 받을 수 있습니다. 기본 문법은 다음과 같습니다.

```typescript
function identity<T>(arg: T): T {
  return arg;
}
```

- 위의 예에서 T는 타입 매개변수로, 함수가 호출될 때 구체적인 타입으로 대체됩니다.


### 2. 제너릭 함수
- 제너릭 함수를 사용하면 다양한 타입의 인자를 받을 수 있습니다. 예를 들어, 다음은 숫자와 문자열 모두를 처리할 수 있는 함수입니다.

```typescript
function log<T>(value: T): void {
    console.log(value);
}

log<number>(123); // 숫자
log<string>('Hello'); // 문자열
```

- 타입 매개변수를 명시하지 않으면 TypeScript가 자동으로 타입을 추론합니다.

```typescript
log(true); // boolean
```

### 3. 제너릭 인터페이스
- 인터페이스에서도 제너릭을 사용할 수 있습니다. 다음은 제너릭 인터페이스의 예입니다.

```typescript
interface Pair<K, V> {
  key: K;
  value: V;
}자

const pair: Pair<number, string> = {
  key: 1,
  value: 'One',
};
```

- 이 인터페이스는 키와 값의 타입을 유연하게 지정할 수 있습니다.

### 4. 제너릭 클래스
- 제너릭은 클래스에서도 사용할 수 있습니다. 아래는 제너릭 클래스를 사용하는 예제입니다.

```typescript
class Box<T> {
  private contents: T;

  constructor(value: T) {
    this.contents = value;
  }

  getContents(): T {
    return this.contents;
  }
}

const numberBox = new Box<number>(123);
const stringBox = new Box<string>('Hello');
```

- 이 클래스는 다양한 타입의 내용을 담을 수 있는 박스를 생성합니다.

### 5. 제너릭 제약조건
- 제너릭 타입에 제약을 추가하여 특정 타입만 사용할 수 있도록 제한할 수 있습니다. 이를 통해 더 안전한 코드를 작성할 수 있습니다.

```typescript
function logLength<T extends { length: number }>(arg: T): void {
  console.log(arg.length);
}

logLength('Hello'); // 문자열의 길이
logLength([1, 2, 3]); // 배열의 길이
```


### 6. 결론
- TypeScript의 제너릭은 코드의 재사용성과 타입 안전성을 높이는 데 매우 유용한 기능입니다.
- 이를 통해 다양한 타입을 유연하게 처리할 수 있으며, 코드 작성 시 더욱 안전한 타입 검사를 제공합니다. 제너릭을 잘 활용하면 더 깔끔하고 유지보수하기 쉬운 코드를 작성할 수 있습니다.

