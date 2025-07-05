# JavaScript 메모이제이션 (Memoization)

## 📖 개요

메모이제이션은 **동일한 계산을 반복할 때, 이전에 계산한 결과를 기억해두고 재사용하는 최적화 기법**입니다.

쉽게 말해서, "이미 계산한 건 다시 계산하지 말고 기억해둔 걸 써라"는 개념입니다.

### 🎯 왜 메모이제이션이 필요한가?

**예시로 이해해보기**

```javascript
// 피보나치 수열 계산 (메모이제이션 없이)
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// fibonacci(5)를 계산할 때:
// fibonacci(5) → fibonacci(4) + fibonacci(3)
// fibonacci(4) → fibonacci(3) + fibonacci(2)  
// fibonacci(3) → fibonacci(2) + fibonacci(1)
// fibonacci(2) → fibonacci(1) + fibonacci(0)
// 
// 같은 fibonacci(3)이 여러 번 계산됨!
// fibonacci(2)도 여러 번 계산됨!
```

**문제점**: 같은 값을 계속 계산해서 시간이 오래 걸림

**해결책**: 한 번 계산한 값은 기억해두고 재사용

## 🔧 기본 개념

### 순수 함수 (Pure Function)
메모이제이션을 적용하려면 함수가 **순수 함수**여야 합니다.

**순수 함수란?**
- 같은 입력에 항상 같은 출력을 반환
- 외부 상태를 변경하지 않음
- 부수 효과(side effect)가 없음

```javascript
// ✅ 순수 함수 - 메모이제이션 가능
function add(a, b) {
    return a + b;
}

// ❌ 순수 함수 아님 - 메모이제이션 불가
let counter = 0;
function increment() {
    counter++;
    return counter;
}
```

### 캐시 (Cache)
계산 결과를 임시로 저장해두는 공간입니다.

```javascript
// 간단한 캐시 예시
const cache = {
    "2+3": 5,
    "10+20": 30
};
```

## 🛠️ 기본 메모이제이션 구현

### 1단계: 가장 간단한 메모이제이션

```javascript
function memoize(fn) {
    const cache = {}; // 결과를 저장할 객체
    
    return function (...args) {
        const key = JSON.stringify(args); // 인자를 문자열로 변환
        
        // 이미 계산한 적이 있으면 캐시에서 가져오기
        if (cache[key] !== undefined) {
            console.log('캐시에서 가져옴!');
            return cache[key];
        }
        
        // 처음 계산하는 경우
        console.log('새로 계산함!');
        const result = fn(...args);
        cache[key] = result; // 결과를 캐시에 저장
        return result;
    };
}
```

### 2단계: Map을 사용한 개선된 버전

```javascript
function memoize(fn) {
    const cache = new Map(); // Map 사용 (더 효율적)
    
    return function (...args) {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            console.log('캐시 히트!');
            return cache.get(key);
        }
        
        console.log('캐시 미스!');
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
}
```

## 📝 실제 사용 예시

### 예시 1: 피보나치 수열

```javascript
// 메모이제이션 적용 전 (매우 느림)
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// 메모이제이션 적용 후 (매우 빠름)
const memoizedFibonacci = memoize(function(n) {
    if (n <= 1) return n;
    return memoizedFibonacci(n - 1) + memoizedFibonacci(n - 2);
});

// 성능 비교
console.time('일반 피보나치');
console.log(fibonacci(35)); // 몇 초 걸림
console.timeEnd('일반 피보나치');

console.time('메모이제이션 피보나치');
console.log(memoizedFibonacci(35)); // 거의 즉시
console.timeEnd('메모이제이션 피보나치');
```

### 예시 2: 팩토리얼 계산

```javascript
// 일반 팩토리얼
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

// 메모이제이션 팩토리얼
const memoizedFactorial = memoize(function(n) {
    if (n <= 1) return 1;
    return n * memoizedFactorial(n - 1);
});

// 테스트
console.log(factorial(5));     // 120
console.log(factorial(5));     // 다시 계산 (캐시 없음)

console.log(memoizedFactorial(5)); // 120
console.log(memoizedFactorial(5)); // 캐시에서 가져옴!
```

### 예시 3: 복잡한 계산 (배열 합계)

```javascript
function expensiveCalculation(arr) {
    // 복잡한 계산을 시뮬레이션
    let result = 0;
    for (let i = 0; i < arr.length; i++) {
        result += arr[i] * Math.sqrt(i + 1);
    }
    return result;
}

const memoizedCalculation = memoize(expensiveCalculation);

const data = [1, 2, 3, 4, 5];

console.time('일반 계산');
console.log(expensiveCalculation(data));
console.timeEnd('일반 계산');

console.time('메모이제이션 계산');
console.log(memoizedCalculation(data));
console.timeEnd('메모이제이션 계산');

// 같은 데이터로 다시 계산
console.time('메모이제이션 재계산');
console.log(memoizedCalculation(data)); // 캐시에서 가져옴!
console.timeEnd('메모이제이션 재계산');
```

## 🔍 고급 기법

### 1. 캐시 크기 제한

메모리 사용량을 제한하는 방법입니다.

```javascript
function memoizeWithLimit(fn, limit = 100) {
    const cache = new Map();
    const keys = [];
    
    return function (...args) {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            // 사용된 키를 맨 뒤로 이동 (LRU 방식)
            const index = keys.indexOf(key);
            keys.splice(index, 1);
            keys.push(key);
            return cache.get(key);
        }
        
        // 캐시가 가득 찬 경우 가장 오래된 항목 제거
        if (keys.length >= limit) {
            const oldestKey = keys.shift();
            cache.delete(oldestKey);
        }
        
        const result = fn.apply(this, args);
        cache.set(key, result);
        keys.push(key);
        return result;
    };
}
```

### 2. 시간 제한 (TTL - Time To Live)

캐시된 결과에 만료 시간을 설정합니다.

```javascript
function memoizeWithTTL(fn, ttl = 60000) { // 기본 1분
    const cache = new Map();
    
    return function (...args) {
        const key = JSON.stringify(args);
        const now = Date.now();
        
        if (cache.has(key)) {
            const { value, timestamp } = cache.get(key);
            
            // 아직 유효한 경우
            if (now - timestamp < ttl) {
                return value;
            }
            
            // 만료된 경우 제거
            cache.delete(key);
        }
        
        const result = fn.apply(this, args);
        cache.set(key, { value: result, timestamp: now });
        return result;
    };
}
```

### 3. WeakMap 사용

객체를 키로 사용할 때 메모리 누수를 방지합니다.

```javascript
function memoizeWithWeakMap(fn) {
    const cache = new WeakMap();
    
    return function(obj) {
        if (!cache.has(obj)) {
            cache.set(obj, fn(obj));
        }
        return cache.get(obj);
    };
}

// 사용 예시
const processUser = memoizeWithWeakMap(function(user) {
    return {
        id: user.id,
        name: user.name.toUpperCase(),
        age: user.age
    };
});

const user1 = { id: 1, name: 'john', age: 25 };
const user2 = { id: 2, name: 'jane', age: 30 };

console.log(processUser(user1)); // 새로 계산
console.log(processUser(user1)); // 캐시에서 가져옴
console.log(processUser(user2)); // 새로 계산
```

## ⚖️ 장단점

### ✅ 장점

1. **성능 향상**
   - 동일한 계산 반복 방지
   - 특히 재귀 함수에서 큰 효과

2. **사용자 경험 개선**
   - 응답 시간 단축
   - 애플리케이션 반응성 향상

3. **자원 효율성**
   - CPU 사용량 감소
   - 계산 비용 절약

### ❌ 단점

1. **메모리 사용량 증가**
   - 캐시 저장을 위한 추가 메모리 필요
   - 입력값이 많을 때 메모리 부족 가능

2. **적용 제한**
   - 순수 함수에만 적용 가능
   - 부수 효과가 있는 함수에는 부적합

3. **복잡성 증가**
   - 디버깅이 어려울 수 있음
   - 메모리 관리 필요

## 🎯 언제 사용해야 할까?

### ✅ 메모이제이션을 사용하면 좋은 경우

1. **복잡한 계산이 반복되는 경우**
   ```javascript
   // 수학적 계산, 데이터 변환 등
   ```

2. **재귀 함수의 성능이 중요한 경우**
   ```javascript
   // 피보나치, 팩토리얼, 조합 계산 등
   ```

3. **API 호출 결과를 캐시하고 싶은 경우**
   ```javascript
   // 동일한 파라미터로 API 호출 시
   ```

4. **렌더링 성능이 중요한 경우**
   ```javascript
   // React의 useMemo, Vue의 computed 등
   ```

### ❌ 메모이제이션을 사용하지 말아야 할 경우

1. **간단한 계산**
   ```javascript
   // 덧셈, 곱셈 등 단순 연산
   ```

2. **매번 다른 결과가 나오는 함수**
   ```javascript
   // 랜덤 값 생성, 현재 시간 반환 등
   ```

3. **부수 효과가 있는 함수**
   ```javascript
   // DOM 조작, 파일 쓰기, API 호출 등
   ```

## 🔧 실전 활용 팁

### 1. 성능 측정하기

```javascript
function measurePerformance(fn, ...args) {
    const start = performance.now();
    const result = fn(...args);
    const end = performance.now();
    
    console.log(`실행 시간: ${(end - start).toFixed(2)}ms`);
    return result;
}

// 사용 예시
measurePerformance(fibonacci, 35);
measurePerformance(memoizedFibonacci, 35);
```

### 2. 캐시 상태 확인하기

```javascript
function memoizeWithDebug(fn) {
    const cache = new Map();
    let hitCount = 0;
    let missCount = 0;
    
    const memoizedFn = function (...args) {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            hitCount++;
            console.log(`캐시 히트! (${hitCount}번째)`);
            return cache.get(key);
        }
        
        missCount++;
        console.log(`캐시 미스! (${missCount}번째)`);
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
    
    // 캐시 통계 확인 메서드
    memoizedFn.getStats = () => ({
        hits: hitCount,
        misses: missCount,
        hitRate: hitCount / (hitCount + missCount) * 100
    });
    
    return memoizedFn;
}
```

### 3. 캐시 초기화하기

```javascript
function memoizeWithClear(fn) {
    const cache = new Map();
    
    const memoizedFn = function (...args) {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            return cache.get(key);
        }
        
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
    
    // 캐시 초기화 메서드
    memoizedFn.clearCache = () => {
        cache.clear();
        console.log('캐시가 초기화되었습니다.');
    };
    
    return memoizedFn;
}
```

## 📚 정리

메모이제이션은 **"계산 결과를 기억해서 재사용하는 최적화 기법"**입니다.

### 핵심 포인트

1. **순수 함수에만 적용 가능**
2. **메모리와 성능의 트레이드오프**
3. **적절한 상황에서만 사용**
4. **캐시 관리가 중요**

### 기억할 점

- 메모이제이션은 만능 해결책이 아닙니다
- 항상 성능 측정을 통해 효과를 확인하세요
- 메모리 사용량을 고려해서 사용하세요
- 복잡한 계산이나 재귀 함수에서 가장 효과적입니다

메모이제이션을 잘 활용하면 JavaScript 애플리케이션의 성능을 크게 향상시킬 수 있습니다! 