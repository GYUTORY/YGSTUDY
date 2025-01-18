
# 📦 TypeScript란?

**TypeScript**는 Microsoft에서 개발한 **정적 타입을 지원하는 JavaScript의 상위 집합**입니다.  
JavaScript에 **타입 시스템과 최신 ECMAScript 기능**을 추가하여, 보다 안정적이고 확장 가능한 코드를 작성할 수 있도록 도와줍니다.

> 💡 **TypeScript는 JavaScript의 상위 집합**이므로, 기존 JavaScript 코드를 그대로 사용할 수 있습니다.

---

## 🎯 TypeScript의 주요 특징

### ✅ 1. 정적 타입 지원
TypeScript는 **정적 타입 시스템**을 제공합니다.  
변수, 함수, 객체 등의 **데이터 타입을 명시적으로 선언**할 수 있습니다.

```typescript
let age: number = 25;
let name: string = "홍길동";
let isStudent: boolean = true;
```

- **장점:** 컴파일 단계에서 오류를 사전에 감지하여 **런타임 오류를 방지**할 수 있습니다.

---

### ✅ 2. JavaScript와의 하위 호환성
- **TypeScript는 JavaScript의 상위 집합**입니다.
- 기존 JavaScript 코드를 그대로 사용하면서, 점진적으로 TypeScript 기능을 추가할 수 있습니다.

```typescript
function greet(name: string) {
    console.log("Hello, " + name);
}
greet("TypeScript");
```

---

### ✅ 3. 개선된 개발자 도구 지원
- **자동 완성:** 코드 작성 시 타입 기반의 자동 완성을 제공
- **오류 강조:** IDE에서 컴파일 오류를 실시간으로 강조
- **리팩토링 도구:** 안전한 코드 리팩토링 지원

---

### ✅ 4. 대규모 애플리케이션 개발에 적합
- **강력한 타입 시스템**과 **모듈 관리**를 통해 대규모 프로젝트에 적합합니다.
- 코드의 **일관성 유지**와 **유지보수**를 용이하게 합니다.

---

# 🚀 TypeScript 설치 및 실행
### **1. TypeScript 설치하기**
```bash
npm install -g typescript
```

### **2. 프로젝트 초기화**
```bash
npx tsc --init
```

---

### **3. TypeScript 코드 작성 (`app.ts`)**
```typescript
const message: string = "Hello, TypeScript!";
console.log(message);
```

---

### **4. TypeScript 코드 컴파일**
```bash
npx tsc app.ts
```

- **결과:** `app.js`라는 JavaScript 파일이 생성됩니다.

---

### **5. JavaScript 실행**
```bash
node app.js
```

---

# 🌟 ts-node: TypeScript 직접 실행 도구
**ts-node**는 **TypeScript 코드를 직접 실행**할 수 있게 해주는 도구입니다.

### ✅ ts-node 설치
```bash
npm install -g ts-node
```

### ✅ TypeScript 파일 직접 실행
```bash
ts-node app.ts
```

---

## 🔥 ts-node의 장점
- **즉시 실행:** TypeScript 코드를 **별도 컴파일 없이** 바로 실행
- **빠른 테스트:** 코드를 빠르게 실행하고 테스트 가능
- **REPL 지원:** 대화형 TypeScript 실행 환경 제공

---

## 🛠️ REPL이란? (Read-Eval-Print Loop)
**REPL**은 **대화형 프로그래밍 환경**으로, 코드를 바로 입력하고 결과를 확인할 수 있는 개발 도구입니다.

### **REPL의 동작 방식:**
1. **Read (읽기)**: 사용자가 코드를 입력합니다.
2. **Eval (평가)**: 입력된 코드를 실행합니다.
3. **Print (출력)**: 실행 결과를 출력합니다.
4. **Loop (반복)**: 다음 입력을 대기합니다.
5. 
---

# 📊 TypeScript vs JavaScript 비교

| 기능                          | JavaScript        | TypeScript         |
|------------------------------|--------------------|--------------------|
| **타입 시스템**               | 없음              | 정적 타입 지원 ✅   |
| **IDE 지원**                  | 기본 코드 완성     | 강화된 코드 완성 🚀 |
| **컴파일러 필요**              | 필요 없음         | 필요함             |
| **대규모 프로젝트 적합성**      | 낮음              | 높음 ✅             |

---

# 🎯 결론
TypeScript는 **정적 타입 검사, 향상된 코드 도구 지원, 대규모 프로젝트 관리 기능**을 제공하는 강력한 언어입니다.  
특히, **ts-node**를 활용하면 더욱 빠르고 편리하게 TypeScript 코드를 실행할 수 있습니다.

> **🚀 TypeScript를 사용하여 더 안전하고 유지보수 가능한 코드를 작성해보세요!**
