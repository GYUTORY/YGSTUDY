
# TypeScript에서 `export default`와 `default new`

TypeScript는 모듈 시스템을 사용하여 코드 구조를 효율적으로 관리합니다. 이 문서에서는 TypeScript에서 **`export default`**와 **`default new`**의 개념과 사용법을 예제와 함께 설명합니다.

---

## 📦 `export default`

`export default`는 모듈에서 기본적으로 내보낼 값을 지정할 때 사용됩니다. 이 방식은 모듈에서 하나의 주요 객체, 함수, 또는 클래스를 내보낼 때 유용합니다.

### 기본 사용법

```typescript
// 📁 math.ts (모듈 파일)
export default function add(a: number, b: number): number { // 기본 내보내기 함수 정의
    return a + b;
}

// 📁 main.ts (모듈 가져오기)
import add from './math'; // 기본 내보내기를 가져올 때는 중괄호 없이 사용
console.log(add(2, 3)); // 5
```

#### 주석으로 설명:
- `export default`를 사용하면 모듈에서 하나의 주요 요소를 기본값으로 내보냅니다.
- 기본 내보내기를 가져올 때는 중괄호 `{}`를 사용하지 않습니다.
- 가져오는 이름은 임의로 지정할 수 있습니다.

### 클래스의 `export default`

```typescript
// 📁 Person.ts (모듈 파일)
export default class Person { // 기본 내보내기 클래스 정의
    name: string;
    constructor(name: string) {
        this.name = name;
    }
}

// 📁 main.ts (모듈 가져오기)
import Person from './Person'; // 기본 내보내기 클래스 가져오기
const john = new Person('John Doe');
console.log(john.name); // "John Doe"
```

#### 주석으로 설명:
- 클래스를 `export default`로 내보낼 수 있습니다.
- `import` 구문을 통해 클래스를 인스턴스화하여 사용할 수 있습니다.

---

## ✨ `default new`

`default new`는 TypeScript에서 기본 내보내기와 생성자를 함께 사용할 때의 패턴입니다. 모듈에서 클래스를 기본값으로 내보내고, 이를 가져오는 쪽에서 즉시 인스턴스화하여 사용하는 방식입니다.

### 기본 사용법

```typescript
// 📁 Logger.ts (모듈 파일)
export default class Logger { // 기본 내보내기 클래스 정의
    log(message: string): void {
        console.log(`[LOG]: ${message}`);
    }
}

// 📁 main.ts (모듈 가져오기와 인스턴스화)
import Logger from './Logger'; // Logger 클래스 가져오기
const logger = new Logger(); // 인스턴스화
logger.log('Hello, TypeScript!'); // [LOG]: Hello, TypeScript!
```

#### `default new`를 바로 사용하는 패턴

```typescript
// 📁 Logger.ts (모듈 파일)
export default new (class Logger { // 기본 내보내기로 클래스 인스턴스 직접 생성
    log(message: string): void {
        console.log(`[LOG]: ${message}`);
    }
})();

// 📁 main.ts (모듈 가져오기)
import logger from './Logger'; // 인스턴스화된 객체 가져오기
logger.log('This is default new!'); // [LOG]: This is default new!
```

#### 주석으로 설명:
- 클래스 자체를 기본 내보내기하는 대신, 클래스의 인스턴스를 기본 내보내기로 설정할 수 있습니다.
- 가져오는 쪽에서 별도의 `new` 키워드 없이 사용할 수 있습니다.

---

## 📊 `export default`와 `default new`의 비교

| 특징                      | `export default`                | `default new`                     |
|--------------------------|--------------------------------|-----------------------------------|
| 내보내기 내용              | 함수, 객체, 클래스 등 모든 값    | 클래스의 인스턴스                |
| 사용 패턴                  | 가져온 후 직접 인스턴스화        | 가져오는 즉시 사용 가능            |
| 코드 간결화 여부            | 적당한 간결성 제공               | 인스턴스화 코드를 줄여 더 간결함     |

---

## 🗂️ 실용적인 예제

### 예제 1: HTTP 클라이언트 (기본 클래스 내보내기)

```typescript
// 📁 HttpClient.ts
export default class HttpClient {
    get(url: string): Promise<string> {
        return Promise.resolve(`GET request to ${url}`);
    }
}

// 📁 main.ts
import HttpClient from './HttpClient';
const client = new HttpClient();
client.get('https://example.com').then(console.log);
```

### 예제 2: 싱글톤 패턴 (기본 인스턴스 내보내기)

```typescript
// 📁 SingletonLogger.ts
export default new (class Logger {
    private logs: string[] = [];
    log(message: string): void {
        this.logs.push(message);
        console.log(message);
    }
    getLogs(): string[] {
        return this.logs;
    }
})();

// 📁 main.ts
import logger from './SingletonLogger';
logger.log('First log'); // First log
logger.log('Second log'); // Second log
console.log(logger.getLogs()); // ["First log", "Second log"]
```

---

### 👉🏻 패키지 매니저와의 연관성
TypeScript의 모듈 내보내기는 패키지 매니저에서 배포된 패키지를 가져올 때 자주 사용됩니다. 예를 들어:

```typescript
// Axios 라이브러리 가져오기 (기본 내보내기 사용)
import axios from 'axios';

axios.get('https://example.com').then((response) => {
    console.log(response.data);
});
```

---
