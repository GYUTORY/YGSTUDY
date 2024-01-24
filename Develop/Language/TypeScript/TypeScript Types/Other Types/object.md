
# object
- 모든 객체 유형을 포함하는 일반적인 객체 타입입니다.
- `object`는 기본적으로 프로퍼티를 가지는 모든 JavaScript 객체를 나타냅니다.

# 예시

```typescript
let person: object = {
  name: 'John',
  age: 30,
  city: 'New York'
};

// Error: Property 'name' does not exist on type 'object'
console.log(person.name);
```

> 위 예시에서 `person` 변수의 타입을 `object`로 지정하였습니다.
- `object` 타입은 실제 프로퍼티의 구조를 알지 못하기 때문에 `name` 프로퍼티에 접근할 수 없습니다. 
- 이는 `object` 타입이 모든 객체에 대한 일반적인 유형이기 때문입니다.
- 일반적으로 `object` 타입은 객체의 구체적인 형태나 프로퍼티를 알 수 없는 경우에 사용됩니다. 
- 이는 동적으로 변하는 객체나 외부 라이브러리에서 반환되는 객체 등을 처리할 때 유용합니다. 

> 위 예시의 `person` 객체를 좀 더 구체적인 타입으로 지정할 수 있습니다:

```typescript
interface Person {
  name: string;
  age: number;
  city: string;
}

let person: Person = {
  name: 'John',
  age: 30,
  city: 'New York'
};

console.log(person.name); // 'John'
```

# 정리
- 인터페이스를 사용하여 객체의 구조를 명시적으로 지정함으로써 타입 안정성을 확보할 수 있습니다. 
- 따라서 가능하면 `object`보다는 구체적인 타입을 사용하는 것이 좋습니다.