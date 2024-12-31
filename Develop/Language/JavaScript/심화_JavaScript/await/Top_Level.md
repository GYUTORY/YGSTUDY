
# Node.js 14에서의 Top-Level Await

Node.js 14 버전에서는 ECMAScript 모듈(ESM) 환경에서 **Top-Level Await**이 도입되어 비동기 코드를 작성할 때 더욱 간편해졌습니다. 이 기능은 ES 모듈 파일의 최상위 수준에서 `await` 키워드를 사용할 수 있도록 허용합니다.

## Top-Level Await란?

기존에는 JavaScript에서 `await` 키워드를 사용하려면 반드시 `async` 함수 내부에서 호출해야 했습니다. 하지만 Top-Level Await을 사용하면 모듈의 최상위 코드에서도 `await`을 사용할 수 있어 비동기 작업을 더 직관적으로 작성할 수 있습니다.

### 기존 방식
```javascript
// 기존 방식: async 함수 내부에서 await 사용
async function fetchData() {
    const response = await fetch('https://api.example.com/data');
    const data = await response.json();
    console.log(data);
}
fetchData();
```

### Top-Level Await 방식
```javascript
// Top-Level Await 사용
const response = await fetch('https://api.example.com/data');
const data = await response.json();
console.log(data);
```

## Node.js 14에서의 Top-Level Await 사용법

### 1. ES 모듈 환경 설정
Top-Level Await은 **ESM(ECMAScript Module)** 환경에서만 작동합니다. Node.js에서 ESM을 활성화하려면 다음 중 하나를 선택해야 합니다:
1. 파일 확장자를 `.mjs`로 설정
2. `package.json` 파일에 `type: "module"` 추가

예:
```json
{
  "type": "module"
}
```

### 2. 비동기 코드 작성
Top-Level Await은 비동기 초기화 코드 작성 시 유용합니다.

#### 예제: 데이터 가져오기
```javascript
// main.mjs
import fetch from 'node-fetch';

const url = 'https://api.example.com/data';

try {
    const response = await fetch(url);
    const data = await response.json();
    console.log('Fetched Data:', data);
} catch (error) {
    console.error('Error fetching data:', error);
}
```

#### 예제: 동적 모듈 가져오기
```javascript
// dynamicImport.mjs
if (process.env.LOAD_MODULE === 'true') {
    const module = await import('./myModule.mjs');
    module.run();
}
```

### 3. 주의사항
- **블로킹 문제**: Top-Level Await을 사용할 경우, 해당 모듈이 완료될 때까지 다른 모듈이 블로킹될 수 있습니다. 이는 애플리케이션 시작 속도에 영향을 미칠 수 있습니다.
- **ESM 환경에서만 사용 가능**: CommonJS 환경에서는 사용할 수 없습니다.

## Top-Level Await의 장점
1. **가독성 향상**: 비동기 코드가 더 간단하고 읽기 쉬워집니다.
2. **직관적인 모듈 초기화**: 비동기 작업이 필요한 모듈 초기화를 간단하게 구현할 수 있습니다.
3. **코드 구조 단순화**: 불필요한 함수 래핑 없이 비동기 작업을 처리할 수 있습니다.

## Node.js 14에서의 실용적인 사용 예제

### 예제 1: 데이터베이스 연결
```javascript
// db.mjs
import { createConnection } from 'mysql2/promise';

const connection = await createConnection({
    host: 'localhost',
    user: 'root',
    database: 'test'
});

console.log('Database connected successfully!');

export default connection;
```

### 예제 2: 초기 설정 파일 로드
```javascript
// config.mjs
import fs from 'fs/promises';

const config = JSON.parse(await fs.readFile('./config.json', 'utf-8'));
console.log('Configuration Loaded:', config);

export default config;
```

## 주요 고려 사항
1. **블로킹 방지**: Top-Level Await은 모듈 수준에서 실행되므로, 비효율적인 코드 작성 시 애플리케이션 성능 저하를 초래할 수 있습니다.
2. **호환성**: Node.js 14 이상 및 ESM 환경에서만 사용할 수 있으므로 환경 설정을 확인해야 합니다.

---

Top-Level Await은 비동기 코드 작성의 복잡성을 줄이고, 모듈 초기화 과정을 간소화하는 데 매우 유용한 기능입니다. Node.js 14 이상에서 이 기능을 활용해보세요!
