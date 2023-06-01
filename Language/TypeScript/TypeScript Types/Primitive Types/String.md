
# String
- TypeScript에서의 기본 데이터 타입으로, 텍스트 데이터를 나타냅니다.
- 16비트 유니코드 문자 집합의 요소들로 이루어져 있습니다.

```typescript
let name: string = 'John Doe';
```

> string 타입은 따옴표(`'` 또는 `"` 기호)로 둘러싸인 텍스트 값을 나타냅니다. 문자열은 단일 문자, 단어, 문장, 문단 등과 같은 텍스트 데이터를 포함할 수 있습니다.


string 타입은 문자열 조작, 템플릿 리터럴, 문자열 검색 등 다양한 상황에서 사용됩니다. 예를 들어:

```typescript
let greeting: string = 'Hello, ';
let person: string = 'John Doe';

let message: string = greeting + person; // 문자열 연결

let template: string = `My name is ${person}`; // 템플릿 리터럴

let searchResult: number = message.indexOf('John'); // 문자열 검색
```

- 위의 예시에서는 문자열 연결을 위해 `+` 연산자를 사용하고, 템플릿 리터럴을 사용하여 문자열을 생성합니다.
- 또한, `indexOf` 메서드를 사용하여 특정 문자열을 검색합니다.
- string 타입은 TypeScript에서 자주 사용되는 기본 데이터 타입 중 하나이며, 텍스트 데이터 처리 및 템플릿 작성 등 다양한 상황에서 활용됩니다.
