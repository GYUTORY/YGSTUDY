---
title: JavaScript 메모이제이션(Memoization)
tags: [language, javascript, 03성능최적화, memoization, performance-optimization]
updated: 2025-08-10
---

# JavaScript 메모이제이션(Memoization)

## 배경

메모이제이션(Memoization)은 **함수의 결과를 캐시하여 동일한 입력에 대해 중복 계산을 방지하는 최적화 기법**입니다.

### 메모이제이션의 필요성
복잡한 계산이나 API 호출이 필요한 함수에서:
- 동일한 입력값으로 함수가 여러 번 호출될 때
- 매번 계산을 수행하는 대신 이전 결과를 재사용
- 성능 향상과 리소스 절약 효과

### 메모이제이션의 동작 원리
1. **함수 호출**: 새로운 입력값으로 함수 호출
2. **캐시 확인**: 해당 입력값의 결과가 캐시에 있는지 확인
3. **결과 반환**: 캐시에 있으면 저장된 결과 반환
4. **계산 수행**: 캐시에 없으면 계산 수행 후 결과 저장
5. **재사용**: 다음 동일한 입력값 호출 시 캐시된 결과 사용

## 핵심

### 1. 기본 메모이제이션 구현

#### 간단한 메모이제이션 함수
```javascript
// 기본 메모이제이션 함수
function memoize(func) {
    const cache = new Map();
    
    return function(...args) {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            console.log('캐시된 결과 사용');
            return cache.get(key);
        }
        
        console.log('새로운 계산 수행');
        const result = func.apply(this, args);
        cache.set(key, result);
        
        return result;
    };
}

// 사용 예시
const expensiveCalculation = memoize((n) => {
    console.log(`${n}의 팩토리얼 계산 중...`);
    let result = 1;
    for (let i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
});

console.log(expensiveCalculation(5)); // 새로운 계산 수행
console.log(expensiveCalculation(5)); // 캐시된 결과 사용
```

#### 고급 메모이제이션 함수
```javascript
// 고급 메모이제이션 함수 (TTL, 크기 제한 등)
function advancedMemoize(func, options = {}) {
    const {
        ttl = Infinity,           // 캐시 유효 시간 (밀리초)
        maxSize = Infinity,       // 최대 캐시 크기
        keyGenerator = null       // 커스텀 키 생성 함수
    } = options;
    
    const cache = new Map();
    const timestamps = new Map();
    
    return function(...args) {
        const key = keyGenerator ? keyGenerator(...args) : JSON.stringify(args);
        const now = Date.now();
        
        // 캐시에서 결과 확인
        if (cache.has(key)) {
            const timestamp = timestamps.get(key);
            
            // TTL 확인
            if (now - timestamp < ttl) {
                console.log('캐시된 결과 사용');
                return cache.get(key);
            } else {
                // 만료된 캐시 삭제
                cache.delete(key);
                timestamps.delete(key);
            }
        }
        
        // 캐시 크기 제한 확인
        if (cache.size >= maxSize) {
            const firstKey = cache.keys().next().value;
            cache.delete(firstKey);
            timestamps.delete(firstKey);
        }
        
        console.log('새로운 계산 수행');
        const result = func.apply(this, args);
        
        cache.set(key, result);
        timestamps.set(key, now);
        
        return result;
    };
}

// 사용 예시
const memoizedWithOptions = advancedMemoize(
    (a, b) => {
        console.log(`${a} + ${b} 계산 중...`);
        return a + b;
    },
    {
        ttl: 5000,        // 5초 유효
        maxSize: 10,      // 최대 10개 캐시
        keyGenerator: (a, b) => `${a}-${b}`  // 커스텀 키
    }
);
```

### 2. 클래스 기반 메모이제이션

#### 메모이제이션 관리자 클래스
```javascript
// 메모이제이션 관리자 클래스
class MemoizationManager {
    constructor() {
        this.caches = new Map();
        this.stats = new Map();
    }
    
    // 함수를 메모이제이션으로 래핑
    memoize(key, func, options = {}) {
        if (this.caches.has(key)) {
            return this.caches.get(key);
        }
        
        const memoizedFunc = this.createMemoizedFunction(func, options);
        this.caches.set(key, memoizedFunc);
        this.stats.set(key, { hits: 0, misses: 0 });
        
        return memoizedFunc;
    }
    
    // 메모이제이션 함수 생성
    createMemoizedFunction(func, options = {}) {
        const {
            ttl = Infinity,
            maxSize = Infinity,
            keyGenerator = null
        } = options;
        
        const cache = new Map();
        const timestamps = new Map();
        const key = func.name || 'anonymous';
        
        const memoizedFunc = function(...args) {
            const cacheKey = keyGenerator ? keyGenerator(...args) : JSON.stringify(args);
            const now = Date.now();
            
            // 캐시 히트 확인
            if (cache.has(cacheKey)) {
                const timestamp = timestamps.get(cacheKey);
                
                if (now - timestamp < ttl) {
                    this.updateStats(key, 'hit');
                    return cache.get(cacheKey);
                } else {
                    cache.delete(cacheKey);
                    timestamps.delete(cacheKey);
                }
            }
            
            // 캐시 크기 제한
            if (cache.size >= maxSize) {
                const firstKey = cache.keys().next().value;
                cache.delete(firstKey);
                timestamps.delete(firstKey);
            }
            
            this.updateStats(key, 'miss');
            const result = func.apply(this, args);
            
            cache.set(cacheKey, result);
            timestamps.set(cacheKey, now);
            
            return result;
        }.bind(this);
        
        // 메서드 추가
        memoizedFunc.clearCache = () => {
            cache.clear();
            timestamps.clear();
        };
        
        memoizedFunc.getCacheSize = () => cache.size;
        
        memoizedFunc.getStats = () => {
            const stats = this.stats.get(key);
            const hitRate = stats.hits / (stats.hits + stats.misses) * 100;
            return {
                ...stats,
                hitRate: `${hitRate.toFixed(2)}%`
            };
        };
        
        return memoizedFunc;
    }
    
    // 통계 업데이트
    updateStats(key, type) {
        const stats = this.stats.get(key);
        if (stats) {
            stats[type === 'hit' ? 'hits' : 'misses']++;
        }
    }
    
    // 특정 캐시 삭제
    clearCache(key) {
        const memoizedFunc = this.caches.get(key);
        if (memoizedFunc && memoizedFunc.clearCache) {
            memoizedFunc.clearCache();
        }
    }
    
    // 모든 캐시 삭제
    clearAllCaches() {
        for (const [key, memoizedFunc] of this.caches) {
            if (memoizedFunc.clearCache) {
                memoizedFunc.clearCache();
            }
        }
    }
    
    // 전체 통계
    getAllStats() {
        const allStats = {};
        for (const [key, stats] of this.stats) {
            allStats[key] = {
                ...stats,
                hitRate: `${(stats.hits / (stats.hits + stats.misses) * 100).toFixed(2)}%`
            };
        }
        return allStats;
    }
}

// 사용 예시
const memoManager = new MemoizationManager();

const fibonacci = memoManager.memoize('fibonacci', (n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
});

const factorial = memoManager.memoize('factorial', (n) => {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
});

console.log(fibonacci(10)); // 계산 수행
console.log(fibonacci(10)); // 캐시 사용
console.log(factorial(5));  // 계산 수행
console.log(factorial(5));  // 캐시 사용

console.log(memoManager.getAllStats());
```

## 예시

### 1. 실제 사용 사례

#### API 호출 메모이제이션
```javascript
// API 호출 메모이제이션
class APICache {
    constructor() {
        this.cache = new Map();
        this.pendingRequests = new Map();
    }
    
    // API 호출을 메모이제이션으로 래핑
    async memoizedFetch(url, options = {}) {
        const cacheKey = `${url}-${JSON.stringify(options)}`;
        
        // 캐시된 응답이 있는지 확인
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < 300000) { // 5분 유효
                console.log('캐시된 API 응답 사용');
                return cached.data;
            } else {
                this.cache.delete(cacheKey);
            }
        }
        
        // 진행 중인 요청이 있는지 확인
        if (this.pendingRequests.has(cacheKey)) {
            console.log('진행 중인 요청 대기');
            return this.pendingRequests.get(cacheKey);
        }
        
        // 새로운 요청 시작
        console.log('새로운 API 요청 시작');
        const requestPromise = fetch(url, options)
            .then(response => response.json())
            .then(data => {
                // 캐시에 저장
                this.cache.set(cacheKey, {
                    data: data,
                    timestamp: Date.now()
                });
                
                // 진행 중인 요청 제거
                this.pendingRequests.delete(cacheKey);
                
                return data;
            })
            .catch(error => {
                this.pendingRequests.delete(cacheKey);
                throw error;
            });
        
        this.pendingRequests.set(cacheKey, requestPromise);
        return requestPromise;
    }
    
    // 캐시 정리
    clearCache() {
        this.cache.clear();
    }
    
    // 만료된 캐시 정리
    clearExpiredCache(maxAge = 300000) { // 기본 5분
        const now = Date.now();
        for (const [key, value] of this.cache) {
            if (now - value.timestamp > maxAge) {
                this.cache.delete(key);
            }
        }
    }
}

// 사용 예시
const apiCache = new APICache();

async function fetchUserData(userId) {
    return apiCache.memoizedFetch(`/api/users/${userId}`);
}

// 동일한 사용자 데이터를 여러 번 요청
fetchUserData(1).then(data => console.log('첫 번째 요청:', data));
fetchUserData(1).then(data => console.log('두 번째 요청:', data)); // 캐시 사용
```

#### 계산 집약적 함수 최적화
```javascript
// 계산 집약적 함수들의 메모이제이션
class MathCalculator {
    constructor() {
        this.memoManager = new MemoizationManager();
        this.initMemoizedFunctions();
    }
    
    initMemoizedFunctions() {
        // 피보나치 수열
        this.fibonacci = this.memoManager.memoize('fibonacci', (n) => {
            if (n <= 1) return n;
            return this.fibonacci(n - 1) + this.fibonacci(n - 2);
        });
        
        // 팩토리얼
        this.factorial = this.memoManager.memoize('factorial', (n) => {
            if (n <= 1) return 1;
            return n * this.factorial(n - 1);
        });
        
        // 소수 판별
        this.isPrime = this.memoManager.memoize('isPrime', (n) => {
            if (n < 2) return false;
            if (n === 2) return true;
            if (n % 2 === 0) return false;
            
            for (let i = 3; i <= Math.sqrt(n); i += 2) {
                if (n % i === 0) return false;
            }
            return true;
        });
        
        // 최대공약수
        this.gcd = this.memoManager.memoize('gcd', (a, b) => {
            return b === 0 ? a : this.gcd(b, a % b);
        });
    }
    
    // 성능 테스트
    performanceTest() {
        console.log('=== 메모이제이션 성능 테스트 ===');
        
        // 피보나치 테스트
        const start1 = performance.now();
        for (let i = 0; i < 10; i++) {
            this.fibonacci(30);
        }
        const end1 = performance.now();
        console.log(`피보나치 30 (10회): ${(end1 - start1).toFixed(2)}ms`);
        
        // 팩토리얼 테스트
        const start2 = performance.now();
        for (let i = 0; i < 10; i++) {
            this.factorial(20);
        }
        const end2 = performance.now();
        console.log(`팩토리얼 20 (10회): ${(end2 - start2).toFixed(2)}ms`);
        
        // 소수 판별 테스트
        const start3 = performance.now();
        for (let i = 0; i < 100; i++) {
            this.isPrime(1000003);
        }
        const end3 = performance.now();
        console.log(`소수 판별 1000003 (100회): ${(end3 - start3).toFixed(2)}ms`);
        
        console.log('캐시 통계:', this.memoManager.getAllStats());
    }
}

// 사용 예시
const calculator = new MathCalculator();

console.log(calculator.fibonacci(10)); // 55
console.log(calculator.factorial(5));  // 120
console.log(calculator.isPrime(17));   // true
console.log(calculator.gcd(48, 18));   // 6

calculator.performanceTest();
```

### 2. 고급 메모이제이션 패턴

#### WeakMap을 사용한 객체 키 메모이제이션
```javascript
// WeakMap을 사용한 객체 키 메모이제이션
function memoizeWithWeakMap(func) {
    const cache = new WeakMap();
    
    return function(obj, ...args) {
        if (!cache.has(obj)) {
            cache.set(obj, new Map());
        }
        
        const objCache = cache.get(obj);
        const key = JSON.stringify(args);
        
        if (objCache.has(key)) {
            return objCache.get(key);
        }
        
        const result = func.call(this, obj, ...args);
        objCache.set(key, result);
        
        return result;
    };
}

// 사용 예시
const expensiveObjectOperation = memoizeWithWeakMap((obj, operation) => {
    console.log(`${operation} 연산 수행 중...`);
    // 복잡한 객체 연산
    return Object.keys(obj).length * operation.length;
});

const user1 = { name: 'Alice', age: 30 };
const user2 = { name: 'Bob', age: 25 };

console.log(expensiveObjectOperation(user1, 'count')); // 새로운 계산
console.log(expensiveObjectOperation(user1, 'count')); // 캐시 사용
console.log(expensiveObjectOperation(user2, 'count')); // 새로운 계산
```

#### 비동기 함수 메모이제이션
```javascript
// 비동기 함수 메모이제이션
function memoizeAsync(func) {
    const cache = new Map();
    const pendingRequests = new Map();
    
    return async function(...args) {
        const key = JSON.stringify(args);
        
        // 캐시된 결과 확인
        if (cache.has(key)) {
            const cached = cache.get(key);
            if (Date.now() - cached.timestamp < 300000) { // 5분 유효
                return cached.data;
            } else {
                cache.delete(key);
            }
        }
        
        // 진행 중인 요청 확인
        if (pendingRequests.has(key)) {
            return pendingRequests.get(key);
        }
        
        // 새로운 비동기 작업 시작
        const promise = func.apply(this, args)
            .then(result => {
                cache.set(key, {
                    data: result,
                    timestamp: Date.now()
                });
                pendingRequests.delete(key);
                return result;
            })
            .catch(error => {
                pendingRequests.delete(key);
                throw error;
            });
        
        pendingRequests.set(key, promise);
        return promise;
    };
}

// 사용 예시
const asyncCalculation = memoizeAsync(async (n) => {
    console.log(`${n}의 비동기 계산 시작...`);
    await new Promise(resolve => setTimeout(resolve, 1000));
    return n * n;
});

// 동시에 여러 요청
Promise.all([
    asyncCalculation(5),
    asyncCalculation(5),
    asyncCalculation(5)
]).then(results => {
    console.log('결과:', results); // 모든 결과가 동일
});
```

## 운영 팁

### 성능 최적화

#### 메모리 사용량 관리
```javascript
// 메모리 효율적인 메모이제이션
class MemoryEfficientMemoization {
    constructor(maxSize = 100) {
        this.maxSize = maxSize;
        this.cache = new Map();
        this.accessOrder = [];
    }
    
    memoize(func) {
        return (...args) => {
            const key = JSON.stringify(args);
            
            if (this.cache.has(key)) {
                // 접근 순서 업데이트 (LRU)
                this.updateAccessOrder(key);
                return this.cache.get(key);
            }
            
            // 캐시 크기 제한 확인
            if (this.cache.size >= this.maxSize) {
                this.evictLRU();
            }
            
            const result = func.apply(this, args);
            this.cache.set(key, result);
            this.accessOrder.push(key);
            
            return result;
        };
    }
    
    updateAccessOrder(key) {
        const index = this.accessOrder.indexOf(key);
        if (index > -1) {
            this.accessOrder.splice(index, 1);
        }
        this.accessOrder.push(key);
    }
    
    evictLRU() {
        const oldestKey = this.accessOrder.shift();
        if (oldestKey) {
            this.cache.delete(oldestKey);
        }
    }
    
    getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            hitRate: this.calculateHitRate()
        };
    }
    
    calculateHitRate() {
        // 실제 구현에서는 히트/미스 카운터 추가 필요
        return 'N/A';
    }
}

// 사용 예시
const memoryEfficientMemo = new MemoryEfficientMemoization(10);
const optimizedFunc = memoryEfficientMemo.memoize((n) => {
    console.log(`${n} 계산 중...`);
    return n * n;
});

for (let i = 0; i < 15; i++) {
    optimizedFunc(i);
}

console.log(memoryEfficientMemo.getCacheStats());
```

#### 캐시 무효화 전략
```javascript
// 캐시 무효화 전략
class CacheInvalidation {
    constructor() {
        this.cache = new Map();
        this.dependencies = new Map();
        this.timestamps = new Map();
    }
    
    memoize(func, dependencies = []) {
        return (...args) => {
            const key = JSON.stringify(args);
            
            // 의존성 변경 확인
            if (this.hasDependencyChanged(key, dependencies)) {
                this.cache.delete(key);
                this.timestamps.delete(key);
            }
            
            if (this.cache.has(key)) {
                return this.cache.get(key);
            }
            
            const result = func.apply(this, args);
            this.cache.set(key, result);
            this.timestamps.set(key, Date.now());
            this.dependencies.set(key, dependencies);
            
            return result;
        };
    }
    
    hasDependencyChanged(key, dependencies) {
        const oldDeps = this.dependencies.get(key);
        if (!oldDeps) return false;
        
        return JSON.stringify(oldDeps) !== JSON.stringify(dependencies);
    }
    
    // 특정 조건으로 캐시 무효화
    invalidateByCondition(condition) {
        for (const [key, value] of this.cache) {
            if (condition(key, value)) {
                this.cache.delete(key);
                this.timestamps.delete(key);
                this.dependencies.delete(key);
            }
        }
    }
    
    // 시간 기반 무효화
    invalidateByTime(maxAge) {
        const now = Date.now();
        for (const [key, timestamp] of this.timestamps) {
            if (now - timestamp > maxAge) {
                this.cache.delete(key);
                this.timestamps.delete(key);
                this.dependencies.delete(key);
            }
        }
    }
}

// 사용 예시
const cacheInvalidation = new CacheInvalidation();

const userDataFunc = cacheInvalidation.memoize(
    (userId) => {
        console.log(`사용자 ${userId} 데이터 로드 중...`);
        return { id: userId, name: `User${userId}` };
    },
    ['userData'] // 의존성
);

console.log(userDataFunc(1)); // 계산 수행
console.log(userDataFunc(1)); // 캐시 사용

// 의존성 변경으로 캐시 무효화
cacheInvalidation.invalidateByCondition((key, value) => 
    key.includes('1')
);
```

## 참고

### 메모이제이션 사용 권장 사례

#### 적합한 사용 시나리오
```javascript
// 메모이제이션이 적합한 경우들
const memoizationUseCases = {
    fibonacci: {
        description: '피보나치 수열 계산',
        reason: '중복 계산이 많은 재귀 함수'
    },
    factorial: {
        description: '팩토리얼 계산',
        reason: '반복적인 계산 패턴'
    },
    apiCall: {
        description: 'API 호출 결과',
        reason: '동일한 요청의 중복 방지'
    },
    expensiveCalculation: {
        description: '복잡한 수학 계산',
        reason: '계산 비용이 높은 함수'
    },
    dataProcessing: {
        description: '데이터 처리 결과',
        reason: '동일한 데이터에 대한 반복 처리 방지'
    }
};

// 사용 예시
Object.entries(memoizationUseCases).forEach(([useCase, config]) => {
    console.log(`${useCase}: ${config.description} - ${config.reason}`);
});
```

### 성능 측정

#### 메모이제이션 성능 측정
```javascript
// 메모이제이션 성능 측정 도구
class MemoizationPerformanceTester {
    static testPerformance(originalFunc, memoizedFunc, testCases, iterations = 1000) {
        console.log('=== 메모이제이션 성능 테스트 ===');
        
        // 원본 함수 테스트
        const originalStart = performance.now();
        for (let i = 0; i < iterations; i++) {
            testCases.forEach(testCase => {
                originalFunc(...testCase);
            });
        }
        const originalEnd = performance.now();
        const originalTime = originalEnd - originalStart;
        
        // 메모이제이션 함수 테스트
        const memoizedStart = performance.now();
        for (let i = 0; i < iterations; i++) {
            testCases.forEach(testCase => {
                memoizedFunc(...testCase);
            });
        }
        const memoizedEnd = performance.now();
        const memoizedTime = memoizedEnd - memoizedStart;
        
        // 결과 출력
        console.log(`원본 함수 실행 시간: ${originalTime.toFixed(2)}ms`);
        console.log(`메모이제이션 함수 실행 시간: ${memoizedTime.toFixed(2)}ms`);
        console.log(`성능 향상: ${((originalTime - memoizedTime) / originalTime * 100).toFixed(2)}%`);
        
        return {
            originalTime,
            memoizedTime,
            improvement: (originalTime - memoizedTime) / originalTime * 100
        };
    }
}

// 성능 테스트 예시
const fibonacci = (n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
};

const memoizedFibonacci = memoize(fibonacci);

const testCases = [5, 10, 15, 20];
MemoizationPerformanceTester.testPerformance(fibonacci, memoizedFibonacci, testCases, 100);
```

### 결론
메모이제이션은 반복적인 계산을 최적화하는 강력한 기법입니다.
적절한 캐시 크기와 TTL 설정이 메모리 효율성의 핵심입니다.
WeakMap을 사용하여 객체 키에 대한 메모이제이션을 구현할 수 있습니다.
비동기 함수에도 메모이제이션을 적용하여 중복 요청을 방지할 수 있습니다.
캐시 무효화 전략을 통해 데이터 일관성을 유지해야 합니다.
메모이제이션은 성능 향상을 가져오지만, 메모리 사용량 증가의 트레이드오프를 고려해야 합니다. 






