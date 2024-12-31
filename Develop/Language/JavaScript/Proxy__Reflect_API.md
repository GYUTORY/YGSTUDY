
# JavaScript의 Proxy와 Reflect API

## 1. Proxy와 Reflect API란?
`Proxy`는 객체의 기본 동작(읽기, 쓰기, 삭제 등)을 가로채고 이를 커스터마이징할 수 있는 강력한 도구입니다.  
`Reflect`는 객체의 기본 작업을 수행하는 정적 메서드를 제공하며, Proxy와 함께 사용하면 효과적입니다.

---

## 2. Proxy의 기본 구조
Proxy는 두 가지 주요 구성 요소로 이루어집니다:
- **target**: Proxy가 감싸는 원본 객체.
- **handler**: 객체 동작을 가로채기 위해 정의된 메서드 집합.

### 기본 예제
```javascript
const target = { name: 'Alice' };

const handler = {
    get: (obj, prop) => {
        return prop in obj ? obj[prop] : 'Property does not exist';
    }
};

const proxy = new Proxy(target, handler);

console.log(proxy.name); // Alice
console.log(proxy.age);  // Property does not exist
```

---

## 3. Proxy를 활용한 주요 기능

### 3.1 동적 데이터 바인딩
Proxy를 사용하여 객체의 속성 변경 시 동적으로 작업을 수행할 수 있습니다.

#### 예제
```javascript
const target = { name: 'Alice', age: 25 };

const handler = {
    set: (obj, prop, value) => {
        console.log(`${prop} 속성이 ${value}로 설정되었습니다.`);
        obj[prop] = value;
        return true;
    }
};

const proxy = new Proxy(target, handler);

proxy.age = 30; // 콘솔: age 속성이 30로 설정되었습니다.
console.log(proxy.age); // 30
```

### 3.2 유효성 검사
객체 속성에 대해 유효성 검사를 구현할 수 있습니다.

#### 예제
```javascript
const target = { age: 25 };

const handler = {
    set: (obj, prop, value) => {
        if (prop === 'age' && (typeof value !== 'number' || value < 0)) {
            throw new Error('유효한 나이를 입력하세요.');
        }
        obj[prop] = value;
        return true;
    }
};

const proxy = new Proxy(target, handler);

proxy.age = 30; // 성공
console.log(proxy.age); // 30

proxy.age = -5; // 오류: 유효한 나이를 입력하세요.
```

### 3.3 함수 호출 로깅
Proxy를 함수와 함께 사용하여 호출 동작을 추적할 수 있습니다.

#### 예제
```javascript
const target = function(name) {
    return `Hello, ${name}`;
};

const handler = {
    apply: (func, thisArg, args) => {
        console.log(`함수가 호출되었습니다. 인수: ${args}`);
        return func(...args);
    }
};

const proxy = new Proxy(target, handler);

console.log(proxy('Alice')); // 콘솔: 함수가 호출되었습니다. 인수: Alice
                            // 반환: Hello, Alice
```

---

## 4. Reflect API

`Reflect`는 Proxy에서 작업을 수행할 때 원본 동작을 재현하거나 보조 작업을 처리하는 데 유용합니다.

### Reflect 메서드 사용
```javascript
const target = { name: 'Alice' };

const handler = {
    get: (obj, prop) => {
        console.log(`${prop} 속성을 읽고 있습니다.`);
        return Reflect.get(obj, prop);
    }
};

const proxy = new Proxy(target, handler);

console.log(proxy.name); // 콘솔: name 속성을 읽고 있습니다.
                         // 반환: Alice
```

---

## 5. Proxy와 Reflect의 조합 활용

### 예제: 기본 값 설정
```javascript
const target = { name: 'Alice' };

const handler = {
    get: (obj, prop) => {
        return Reflect.get(obj, prop) || '기본값';
    }
};

const proxy = new Proxy(target, handler);

console.log(proxy.name);    // Alice
console.log(proxy.age);     // 기본값
```

### 예제: 속성 삭제 로깅
```javascript
const target = { name: 'Alice' };

const handler = {
    deleteProperty: (obj, prop) => {
        console.log(`${prop} 속성이 삭제되었습니다.`);
        return Reflect.deleteProperty(obj, prop);
    }
};

const proxy = new Proxy(target, handler);

delete proxy.name; // 콘솔: name 속성이 삭제되었습니다.
console.log(target); // {}
```

---

## 6. 요약
- Proxy는 객체의 동작을 가로채는 유연한 도구로, 동적 데이터 바인딩, 유효성 검사 등에 활용됩니다.
- Reflect는 Proxy와 함께 객체의 기본 동작을 효율적으로 처리할 수 있도록 돕습니다.
- Proxy와 Reflect를 조합하여 동작을 커스터마이징하면서도 예측 가능한 코드를 작성할 수 있습니다.

Proxy와 Reflect를 활용해 JavaScript 코드의 유연성과 제어력을 극대화하세요!
