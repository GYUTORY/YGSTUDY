---
title: CommonJS vs ESM (ECMAScript Modules)
tags: [framework, node, 모듈-시스템, commonjs, esm, nodejs]
updated: 2025-10-13
---

# CommonJS vs ESM (ECMAScript Modules)

## 모듈 시스템이란?

JavaScript에서 **모듈 시스템**은 코드를 독립적인 단위로 분리하고, 이들 간의 의존성을 관리하는 메커니즘입니다. 마치 레고 블록처럼 각각의 기능을 독립적인 모듈로 만들어 필요할 때 조합하여 사용할 수 있게 해줍니다.

### 모듈 시스템이 필요한 이유

초기 JavaScript는 모듈 시스템이 없어서 모든 코드가 전역 스코프에 노출되었습니다. 이로 인해 발생하는 문제들:

1. **전역 변수 오염**: 서로 다른 스크립트에서 같은 변수명을 사용하면 충돌 발생
2. **의존성 관리 어려움**: 스크립트 로딩 순서에 따라 오류 발생 가능
3. **코드 재사용성 저하**: 기능을 분리하고 재사용하기 어려움
4. **네임스페이스 부재**: 코드 구조화가 어려움

### CommonJS와 ESM의 등장

| 모듈 시스템 | 출현 시기 | 특징 |
|------------|-----------|------|
| **CommonJS** | 2009년 | Node.js 환경을 위해 설계된 모듈 시스템 |
| **ESM** | 2015년 (ES6) | JavaScript 표준으로 제정된 모듈 시스템 |

CommonJS는 Node.js 생태계에서 널리 사용되었고, ESM은 브라우저와 Node.js 모두에서 사용할 수 있는 표준이 되었습니다.

## CommonJS (Common JavaScript) 상세 분석

### CommonJS의 핵심 개념

CommonJS는 **서버 사이드 JavaScript**를 위한 모듈 시스템으로, Node.js의 기본 모듈 시스템입니다. 이 시스템의 핵심은 **동기적 모듈 로딩**과 **런타임 모듈 해석**입니다.

#### CommonJS의 작동 원리

1. **모듈 래핑**: 모든 CommonJS 모듈은 함수로 래핑됩니다
2. **동기적 로딩**: `require()` 호출 시 즉시 모듈을 로드하고 실행
3. **캐싱**: 한 번 로드된 모듈은 메모리에 캐시되어 재사용
4. **환경 변수 제공**: `module`, `exports`, `require`, `__filename`, `__dirname` 자동 주입

```javascript
// Node.js가 내부적으로 하는 일 (의사코드)
function (exports, require, module, __filename, __dirname) {
    // 여기에 우리가 작성한 모듈 코드가 들어감
    const add = (a, b) => a + b;
    module.exports = { add };
}
```

#### CommonJS의 특징과 장단점

**장점:**
- **단순함**: 직관적인 `require()`/`module.exports` 문법
- **안정성**: Node.js 생태계에서 오랜 기간 검증됨
- **동기적**: 예측 가능한 로딩 순서
- **호환성**: 대부분의 Node.js 라이브러리가 지원

**단점:**
- **브라우저 미지원**: 브라우저에서 직접 사용 불가
- **동기적 로딩**: 대용량 모듈 로딩 시 블로킹 발생
- **트리 쉐이킹 불가**: 사용하지 않는 코드도 번들에 포함
- **정적 분석 어려움**: 런타임에 의존성 결정

### CommonJS 사용 패턴

#### 1. 기본 내보내기/가져오기
```javascript
// math.js - 모듈 내보내기
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;

// 방법 1: 객체로 내보내기
module.exports = { add, subtract };

// 방법 2: 개별 속성 할당
module.exports.add = add;
module.exports.subtract = subtract;

// 방법 3: exports 단축 사용
exports.add = add;
exports.subtract = subtract;
```

```javascript
// main.js - 모듈 가져오기
// 전체 모듈 가져오기
const math = require('./math');
console.log(math.add(5, 3)); // 8

// 구조분해 할당으로 가져오기
const { add, subtract } = require('./math');
console.log(add(5, 3)); // 8
```

#### 2. 기본 내보내기 (Default Export)
```javascript
// calculator.js
class Calculator {
    add(a, b) { return a + b; }
    subtract(a, b) { return a - b; }
}

module.exports = Calculator; // 기본 내보내기
```

```javascript
// main.js
const Calculator = require('./calculator');
const calc = new Calculator();
console.log(calc.add(5, 3)); // 8
```

#### 3. 동적 require와 조건부 로딩
```javascript
// 환경에 따른 조건부 모듈 로딩
let config;
if (process.env.NODE_ENV === 'production') {
    config = require('./config.prod');
} else {
    config = require('./config.dev');
}

// 함수 내에서 동적 로딩
function loadModule(moduleName) {
    return require(`./modules/${moduleName}`);
}
```

## ECMAScript Modules (ESM) 상세 분석

### ESM의 핵심 개념

ESM은 **JavaScript 표준 모듈 시스템**으로, ES6(ES2015)에서 도입되었습니다. ESM의 핵심은 **정적 모듈 구조**와 **컴파일 타임 의존성 분석**입니다.

#### ESM의 작동 원리

1. **정적 분석**: 모듈의 의존성이 코드 실행 전에 결정됨
2. **비동기 로딩**: 모듈을 비동기적으로 로드 가능
3. **트리 쉐이킹**: 사용하지 않는 코드 제거 가능
4. **순환 의존성 해결**: 정적 분석으로 순환 의존성 문제 해결

```javascript
// ESM의 정적 구조 예시
import { add } from './math.js'; // 컴파일 타임에 의존성 결정
export const result = add(5, 3); // 정적 분석 가능
```

#### ESM의 특징과 장단점

**장점:**
- **표준화**: JavaScript 공식 표준
- **브라우저 지원**: 네이티브 브라우저 지원
- **트리 쉐이킹**: 번들 크기 최적화
- **정적 분석**: IDE 지원 및 도구 활용 가능
- **비동기 로딩**: 성능 최적화 가능

**단점:**
- **복잡성**: 상대적으로 복잡한 문법
- **호환성**: 일부 구형 환경에서 지원 제한
- **설정 필요**: Node.js에서 추가 설정 필요
- **순환 의존성**: 복잡한 순환 의존성 처리

### ESM 사용 패턴

#### 1. Named Export/Import (이름 있는 내보내기/가져오기)
```javascript
// math.js - Named Export
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
export const multiply = (a, b) => a * b;

// 또는 마지막에 한 번에 내보내기
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;
const multiply = (a, b) => a * b;

export { add, subtract, multiply };
```

```javascript
// main.js - Named Import
// 개별 가져오기
import { add, subtract } from './math.js';

// 모든 것 가져오기
import * as math from './math.js';

// 별칭 사용
import { add as addition, subtract as subtraction } from './math.js';

console.log(add(5, 3)); // 8
console.log(math.multiply(4, 5)); // 20
```

#### 2. Default Export/Import (기본 내보내기/가져오기)
```javascript
// calculator.js - Default Export
class Calculator {
    add(a, b) { return a + b; }
    subtract(a, b) { return a - b; }
}

export default Calculator; // 기본 내보내기

// 또는 함수를 기본 내보내기
export default function createCalculator() {
    return new Calculator();
}
```

```javascript
// main.js - Default Import
import Calculator from './calculator.js';
import createCalculator from './calculator.js';

const calc = new Calculator();
const calc2 = createCalculator();
```

#### 3. 혼합 사용 (Default + Named)
```javascript
// utils.js
export const formatDate = (date) => date.toISOString();
export const formatCurrency = (amount) => `$${amount}`;

const defaultFormatter = {
    formatDate,
    formatCurrency
};

export default defaultFormatter;
```

```javascript
// main.js
import formatter, { formatDate, formatCurrency } from './utils.js';

// 또는
import defaultFormatter, * as utils from './utils.js';
```

#### 4. 동적 Import (Dynamic Import)
```javascript
// 동적 import - 비동기 함수 내에서만 사용 가능
async function loadModule() {
    const math = await import('./math.js');
    return math.add(5, 3);
}

// 조건부 동적 로딩
async function loadConditionalModule() {
    if (process.env.NODE_ENV === 'production') {
        const { productionConfig } = await import('./config.prod.js');
        return productionConfig;
    } else {
        const { developmentConfig } = await import('./config.dev.js');
        return developmentConfig;
    }
}

// 지연 로딩 (Lazy Loading)
const loadHeavyModule = () => import('./heavy-module.js');
```

### ESM 설정 방법

#### 1. package.json 설정
```json
{
  "type": "module",
  "main": "index.js",
  "exports": {
    ".": "./index.js",
    "./utils": "./utils.js"
  }
}
```

#### 2. 파일 확장자 사용
```javascript
// .mjs 확장자 사용
// math.mjs
export const add = (a, b) => a + b;

// main.mjs
import { add } from './math.mjs';
```

#### 3. Node.js에서 ESM 사용 시 주의사항
```javascript
// ESM에서는 __dirname, __filename 사용 불가
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// require() 사용 불가 - createRequire 사용
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const oldModule = require('./old-module.js');
```

## CommonJS vs ESM 상세 비교

### 핵심 차이점 분석

| 비교 항목 | CommonJS (CJS) | ESM (ECMAScript Modules) |
|-----------|----------------|-------------------------|
| **문법** | `require()` / `module.exports` | `import` / `export` |
| **로딩 시점** | 런타임 (동적) | 컴파일 타임 (정적) |
| **로딩 방식** | 동기적 (Synchronous) | 비동기적 (Asynchronous) |
| **브라우저 지원** | ❌ 번들러 필요 | ✅ 네이티브 지원 |
| **트리 쉐이킹** | ❌ 불가능 | ✅ 가능 |
| **순환 의존성** | 런타임 해결 | 정적 분석으로 해결 |
| **호이스팅** | `require()` 호이스팅 안됨 | `import` 호이스팅됨 |
| **조건부 로딩** | ✅ 런타임 조건 가능 | ❌ 정적 조건만 가능 |

### 실제 성능 차이

#### 번들 크기 비교
```javascript
// CommonJS - 전체 모듈 로드
const lodash = require('lodash');
console.log(lodash.add(1, 2)); // add만 사용하지만 전체 lodash 로드

// ESM - 트리 쉐이킹으로 필요한 부분만 로드
import { add } from 'lodash-es';
console.log(add(1, 2)); // add 함수만 번들에 포함
```

#### 로딩 성능 비교
```javascript
// CommonJS - 동기적 로딩
const start = Date.now();
const heavyModule = require('./heavy-module'); // 블로킹
const end = Date.now();
console.log(`로딩 시간: ${end - start}ms`);

// ESM - 비동기적 로딩
const start = Date.now();
const heavyModule = await import('./heavy-module.js'); // 논블로킹
const end = Date.now();
console.log(`로딩 시간: ${end - start}ms`);
```

## 실제 사용 시나리오와 패턴

### 순환 의존성 처리

#### CommonJS에서의 순환 의존성
```javascript
// a.js
const b = require('./b');
console.log('a.js에서 b:', b.value);
module.exports = { value: 'A' };

// b.js
const a = require('./a');
console.log('b.js에서 a:', a.value);
module.exports = { value: 'B' };

// 실행 시: a.js에서 b: undefined (아직 로드되지 않음)
```

#### ESM에서의 순환 의존성
```javascript
// a.js
import { value as bValue } from './b.js';
console.log('a.js에서 b:', bValue);
export const value = 'A';

// b.js
import { value as aValue } from './a.js';
console.log('b.js에서 a:', aValue);
export const value = 'B';

// 실행 시: 정적 분석으로 올바른 값 출력
```

### 조건부 모듈 로딩 패턴

#### CommonJS - 런타임 조건부 로딩
```javascript
// 유연한 조건부 로딩
function getDatabase() {
    const dbType = process.env.DB_TYPE || 'sqlite';
    
    switch (dbType) {
        case 'mysql':
            return require('./mysql-db');
        case 'postgres':
            return require('./postgres-db');
        default:
            return require('./sqlite-db');
    }
}

const db = getDatabase();
```

#### ESM - 정적 조건부 로딩
```javascript
// 정적 조건부 로딩 (동적 import 사용)
async function getDatabase() {
    const dbType = process.env.DB_TYPE || 'sqlite';
    
    switch (dbType) {
        case 'mysql':
            const { MySQLDatabase } = await import('./mysql-db.js');
            return new MySQLDatabase();
        case 'postgres':
            const { PostgresDatabase } = await import('./postgres-db.js');
            return new PostgresDatabase();
        default:
            const { SQLiteDatabase } = await import('./sqlite-db.js');
            return new SQLiteDatabase();
    }
}

const db = await getDatabase();
```

### 모듈 캐싱과 성능

#### CommonJS 모듈 캐싱
```javascript
// 첫 번째 require - 파일 시스템에서 로드
const math1 = require('./math');
console.log('첫 번째 로드 완료');

// 두 번째 require - 캐시에서 반환
const math2 = require('./math');
console.log('두 번째 로드 완료');

console.log(math1 === math2); // true (같은 객체)
```

#### ESM 모듈 캐싱
```javascript
// 첫 번째 import - 모듈 그래프 구축
import { add } from './math.js';
console.log('첫 번째 로드 완료');

// 두 번째 import - 캐시에서 반환
import { add as add2 } from './math.js';
console.log('두 번째 로드 완료');

console.log(add === add2); // true (같은 함수)
```

## 실무에서의 모듈 시스템 활용

### 하이브리드 프로젝트 구성

현실적으로 많은 프로젝트에서는 CommonJS와 ESM을 혼용해야 합니다. 특히 기존 프로젝트를 점진적으로 마이그레이션할 때 자주 발생하는 상황입니다.

#### CommonJS에서 ESM 모듈 사용하기
```javascript
// CommonJS 환경에서 ESM 모듈 로드
async function loadESMModule() {
    try {
        // 동적 import는 CommonJS에서도 사용 가능
        const { add, subtract } = await import('./math.mjs');
        return { add, subtract };
    } catch (error) {
        console.error('ESM 모듈 로드 실패:', error);
        // 폴백으로 CommonJS 모듈 사용
        return require('./math-fallback');
    }
}

// 사용 예시
(async () => {
    const math = await loadESMModule();
    console.log(math.add(5, 3));
})();
```

#### ESM에서 CommonJS 모듈 사용하기
```javascript
// ESM 환경에서 CommonJS 모듈 로드
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// CommonJS 모듈 로드
const legacyModule = require('./legacy-module.js');
const config = require(join(__dirname, 'config.json'));

console.log(legacyModule.someFunction());
```

### 프로젝트 마이그레이션 전략

#### 1단계: 점진적 마이그레이션
```json
// package.json - 하이브리드 설정
{
  "name": "my-project",
  "type": "module",
  "main": "index.js",
  "exports": {
    ".": {
      "import": "./index.js",
      "require": "./index.cjs"
    },
    "./legacy": {
      "require": "./legacy/index.js"
    }
  }
}
```

#### 2단계: 파일별 마이그레이션
```javascript
// 새로운 파일들은 ESM으로 작성
// utils.mjs
export const formatDate = (date) => date.toISOString();
export const formatCurrency = (amount) => `$${amount}`;

// 기존 파일들은 CommonJS 유지
// legacy-utils.js
const formatDate = (date) => date.toISOString();
const formatCurrency = (amount) => `$${amount}`;
module.exports = { formatDate, formatCurrency };
```

#### 3단계: 라이브러리 호환성 처리
```javascript
// wrapper.mjs - CommonJS 라이브러리를 ESM으로 래핑
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

// CommonJS 라이브러리 래핑
const legacyLib = require('legacy-commonjs-library');

export const { function1, function2 } = legacyLib;
export default legacyLib;
```

### 성능 최적화 기법

#### ESM 트리 쉐이킹 최적화
```javascript
// 좋은 예: 개별 함수 export
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
export const multiply = (a, b) => a * b;

// 나쁜 예: 객체로 묶어서 export
const math = {
    add: (a, b) => a + b,
    subtract: (a, b) => a - b,
    multiply: (a, b) => a * b
};
export default math; // 트리 쉐이킹 불가
```

#### 동적 import 최적화
```javascript
// 코드 스플리팅을 위한 동적 import
const loadFeature = async (featureName) => {
    switch (featureName) {
        case 'chart':
            const { ChartComponent } = await import('./components/chart.js');
            return ChartComponent;
        case 'table':
            const { TableComponent } = await import('./components/table.js');
            return TableComponent;
        default:
            throw new Error(`Unknown feature: ${featureName}`);
    }
};

// 사용 시
const Chart = await loadFeature('chart');
```

### 디버깅과 문제 해결

#### 모듈 로딩 오류 디버깅
```javascript
// 모듈 로딩 상태 확인
console.log('현재 모듈:', import.meta.url);
console.log('모듈 경로:', new URL('.', import.meta.url).pathname);

// 동적 import 오류 처리
async function safeImport(modulePath) {
    try {
        const module = await import(modulePath);
        console.log(`모듈 로드 성공: ${modulePath}`);
        return module;
    } catch (error) {
        console.error(`모듈 로드 실패: ${modulePath}`, error.message);
        return null;
    }
}
```

#### 순환 의존성 감지
```javascript
// CommonJS 순환 의존성 감지
const Module = require('module');
const originalRequire = Module.prototype.require;
const loadingModules = new Set();

Module.prototype.require = function(id) {
    if (loadingModules.has(id)) {
        console.warn(`순환 의존성 감지: ${id}`);
    }
    loadingModules.add(id);
    const result = originalRequire.call(this, id);
    loadingModules.delete(id);
    return result;
};
```

## 모듈 시스템 선택 가이드

### 프로젝트 유형별 권장사항

| 프로젝트 유형 | 권장 모듈 시스템 | 주요 이유 |
|---------------|----------------|-----------|
| **새로운 웹 애플리케이션** | ESM | 브라우저 네이티브 지원, 트리 쉐이킹 |
| **새로운 Node.js 프로젝트** | ESM | 미래 지향적, 표준 준수 |
| **기존 Node.js 프로젝트** | CommonJS 유지 | 안정성, 호환성, 마이그레이션 비용 |
| **라이브러리/패키지** | 하이브리드 지원 | 사용자 호환성 최대화 |
| **마이크로프론트엔드** | ESM | 모듈 공유, 동적 로딩 |
| **레거시 시스템** | CommonJS | 기존 코드베이스와의 호환성 |

### 실무 고려사항

#### 팀 역량과 학습 곡선
- **CommonJS**: 직관적이고 학습하기 쉬움
- **ESM**: 상대적으로 복잡하지만 표준화된 방식

#### 생태계 지원
- **CommonJS**: Node.js 생태계에서 완벽 지원
- **ESM**: 최신 도구들이 우선 지원, 일부 레거시 도구는 제한적

#### 성능 요구사항
- **번들 크기 중요**: ESM (트리 쉐이킹)
- **로딩 속도 중요**: ESM (비동기 로딩)
- **메모리 효율성**: 둘 다 비슷한 캐싱 메커니즘

### 마이그레이션 로드맵

#### 단계별 마이그레이션 전략
1. **평가 단계**: 현재 코드베이스 분석, 의존성 검토
2. **준비 단계**: 빌드 도구 업데이트, 테스트 환경 구축
3. **점진적 마이그레이션**: 새 파일부터 ESM으로 작성
4. **호환성 레이어**: CommonJS와 ESM 간 브리지 구축
5. **완전 마이그레이션**: 모든 파일을 ESM으로 변환

#### 마이그레이션 시 주의사항
- **의존성 호환성**: 사용 중인 라이브러리의 ESM 지원 여부 확인
- **빌드 도구**: Webpack, Rollup 등 번들러 설정 업데이트
- **테스트 환경**: Jest, Mocha 등 테스트 프레임워크 설정 변경
- **CI/CD 파이프라인**: 빌드 스크립트 및 배포 프로세스 수정

## 결론

CommonJS와 ESM은 각각 고유한 장점을 가진 모듈 시스템입니다. 

**CommonJS**는 Node.js 생태계에서 검증된 안정성과 단순함을 제공하며, 기존 프로젝트에서 신뢰할 수 있는 선택입니다. 동기적 로딩과 런타임 의존성 해결은 예측 가능한 동작을 보장합니다.

**ESM**은 JavaScript의 미래를 대표하는 표준으로, 브라우저와 Node.js를 아우르는 통합된 모듈 시스템을 제공합니다. 정적 분석, 트리 쉐이킹, 비동기 로딩 등의 현대적인 기능들은 성능과 개발자 경험을 크게 향상시킵니다.

실무에서는 프로젝트의 요구사항, 팀의 역량, 생태계 지원 상황을 종합적으로 고려하여 적절한 모듈 시스템을 선택해야 합니다. 새로운 프로젝트라면 ESM을, 기존 프로젝트라면 점진적 마이그레이션을 통해 ESM으로 전환하는 것이 장기적으로 유리할 것입니다.

---

## 참조

- [Node.js Modules Documentation](https://nodejs.org/api/modules.html)
- [ECMAScript Modules in Node.js](https://nodejs.org/api/esm.html)
- [MDN - JavaScript Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [CommonJS Specification](https://wiki.commonjs.org/wiki/Modules/1.1)
- [ES6 Modules Specification](https://tc39.es/ecma262/#sec-modules)
- [Webpack Module Federation](https://webpack.js.org/concepts/module-federation/)
- [Rollup ESM Guide](https://rollupjs.org/guide/en/#es-modules)
- [TypeScript Module Resolution](https://www.typescriptlang.org/docs/handbook/module-resolution.html)
