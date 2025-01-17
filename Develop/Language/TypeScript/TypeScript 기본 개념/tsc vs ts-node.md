
# 🌐 tsc와 ts-node 완벽 가이드

`tsc`와 `ts-node`는 모두 **TypeScript 코드를 실행 및 변환**하는 데 사용되는 도구입니다.  
하지만 **사용 목적과 동작 방식**에서 중요한 차이가 있습니다.

---

## ✅ tsc (TypeScript Compiler)

**tsc**는 **TypeScript의 공식 컴파일러**로, TypeScript 코드를 **JavaScript 코드로 변환**하는 역할을 합니다.  
TypeScript 코드는 브라우저나 Node.js 같은 **JavaScript 실행 환경에서 직접 실행할 수 없기 때문**에, **tsc**를 사용하여 먼저 JavaScript로 변환해야 합니다.

---

### 📦 tsc 설치 방법
```bash
npm install -g typescript
```

---

### 🚀 tsc 사용 방법
```bash
# TypeScript 코드를 JavaScript로 변환
tsc your-typescript-file.ts
```

- `your-typescript-file.ts`를 **JavaScript 파일**로 변환
- 결과적으로 `your-typescript-file.js`가 생성됩니다.
- 해당 파일은 Node.js 또는 브라우저 환경에서 실행할 수 있습니다.

---

### 📦 예제 코드 (`app.ts`)
```typescript
const greeting: string = "Hello, TypeScript!";
console.log(greeting);
```

#### 1. **컴파일**
```bash
tsc app.ts
```

#### 2. **JavaScript 파일 실행**
```bash
node app.js
```

---

## ✅ ts-node (TypeScript Node.js 실행기)

**ts-node**는 **TypeScript 코드를 직접 실행**할 수 있도록 도와주는 도구입니다.  
`tsc`와 다르게, **별도의 컴파일 과정 없이** TypeScript 코드를 **메모리 상에서 직접 실행**합니다.

---

### 📦 ts-node 설치 방법
```bash
npm install -g ts-node
```

---

### 🚀 ts-node 사용 방법
```bash
# TypeScript 코드를 바로 실행
ts-node your-typescript-file.ts
```

- **JavaScript 파일을 생성하지 않고**, TypeScript 코드를 **메모리에서 직접 실행**합니다.
- **개발 단계**에서 사용하기 편리하며, **빠른 피드백 루프**를 제공합니다.

---

### 📦 예제 코드 (`app.ts`)
```typescript
const greeting: string = "Hello, ts-node!";
console.log(greeting);
```

#### 1. **ts-node로 직접 실행**
```bash
ts-node app.ts
```

---

## 📊 tsc와 ts-node 비교

| 특징                        | tsc                          | ts-node                   |
|-----------------------------|------------------------------|---------------------------|
| **주요 목적**               | TypeScript → JavaScript 변환 | TypeScript 직접 실행      |
| **컴파일 파일 생성 여부**   | JavaScript 파일 생성         | 메모리 내에서 직접 실행   |
| **사용 사례**               | 프로덕션 빌드, 정적 코드 변환 | 개발 환경, 빠른 테스트    |
| **속도**                    | 느림 (컴파일 필요)          | 빠름 (컴파일 없이 실행)    |
| **장점**                    | 정적 코드 변환, 안정성 보장 | 빠른 개발 루프, REPL 지원 |
| **설치 명령어**             | `npm install -g typescript` | `npm install -g ts-node` |

---

## 🔥 tsc와 ts-node 함께 사용하기
### 📦 프로젝트 설정 (`tsconfig.json`)
```json
{
  "compilerOptions": {
    "target": "ES6",
    "module": "CommonJS",
    "strict": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

### 🚀 프로젝트 예제
1. **TypeScript 프로젝트 초기화**
```bash
npm init -y
npx tsc --init
```

2. **프로젝트 구조**
```plaintext
src/
 └── index.ts
tsconfig.json
package.json
```

3. **`index.ts` 파일 작성**
```typescript
const add = (a: number, b: number): number => {
    return a + b;
};
console.log(add(5, 3));
```

4. **tsc로 컴파일 및 실행**
```bash
npx tsc
node dist/index.js
```

5. **ts-node로 직접 실행**
```bash
npx ts-node src/index.ts
```

---

## 🎯 결론
- **`tsc`**는 **정적 컴파일러**로 TypeScript를 JavaScript로 변환하는 공식 도구입니다.
- **`ts-node`**는 **개발 환경**에서 TypeScript 코드를 **직접 실행**할 수 있는 도구입니다.
- **개발 단계**에서는 `ts-node`를 사용하고, **배포 시**에는 `tsc`로 코드를 컴파일하는 것이 일반적입니다.

> **🚀 효율적인 TypeScript 개발을 위해 `tsc`와 `ts-node`를 함께 활용해보세요!**
