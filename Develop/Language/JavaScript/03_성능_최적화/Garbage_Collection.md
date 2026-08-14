---
title: JavaScript 가비지 컬렉션(Garbage Collection)
tags: [language, javascript]
updated: 2025-08-10
---

# JavaScript 가비지 컬렉션(Garbage Collection)

## 배경

가비지 컬렉션(GC)은 **더 이상 사용되지 않는 메모리를 자동으로 해제하는 메모리 관리 기법**입니다.

### 가비지 컬렉션의 필요성
JavaScript는 메모리 관리를 개발자가 직접 하지 않아도 되는 언어입니다:
- 메모리 할당과 해제를 자동으로 처리
- 메모리 누수 방지
- 개발자가 메모리 관리에 신경 쓰지 않아도 됨

### 가비지 컬렉션의 동작 원리
1. **메모리 할당**: 변수나 객체 생성 시 메모리 할당
2. **참조 추적**: 객체 간의 참조 관계를 추적
3. **도달 가능성 판단**: 루트에서 접근 가능한 객체 식별
4. **메모리 해제**: 도달 불가능한 객체의 메모리 해제

## 핵심

### 실제 자바스크립트에서 확인해보기

아래 시뮬레이션 코드를 보기 전에, 진짜 엔진이 어떻게 동작하는지 먼저 재보면 이해가 빠르다. Node 를 `--expose-gc` 로 띄우면 `global.gc()` 로 수집을 강제할 수 있다.

**순환 참조는 새지 않는다.** 참조 카운팅 방식이라면 서로를 가리키는 두 객체는 카운트가 0이 되지 않아 영원히 남는다. 하지만 자바스크립트는 **루트에서 도달 가능한가**로 판단하기 때문에, 둘이 서로를 붙들고 있어도 바깥에서 아무도 안 가리키면 통째로 회수된다.

```javascript
(() => {
  let a = { payload: new Array(200000).fill('x') };
  let b = { payload: new Array(200000).fill('x') };
  a.ref = b;
  b.ref = a;          // 서로 참조
})();                 // 스코프를 벗어나는 순간 둘 다 도달 불가능

global.gc();          // 증가량 0MB — 순환이어도 회수된다
```

**`= null` 은 해제가 아니라 참조를 끊는 것이다.** 대입한 그 순간에는 메모리가 그대로 남아 있고, 실제 회수는 GC 가 자기 판단으로 돌 때 일어난다.

```
할당 직후        2MB
null 대입 직후    2MB   ← 아직 그대로다
GC 실행 후        0MB
```

그래서 "메모리가 안 줄어든다"고 `null` 을 여기저기 넣는 건 대개 헛수고다. 의미가 있는 경우는 **오래 사는 객체가 큰 것을 붙잡고 있을 때**뿐이다 — 캐시 엔트리, 전역 배열, 클로저에 잡힌 변수처럼.

### 1. 가비지 컬렉션 알고리즘

#### Mark and Sweep 알고리즘
```javascript
// Mark and Sweep 알고리즘 시뮬레이션
class GarbageCollector {
    constructor() {
        this.heap = new Map();
        this.roots = new Set();
    }
    
    // 객체 할당
    allocate(id, data) {
        this.heap.set(id, {
            data: data,
            marked: false,
            references: new Set()
        });
        console.log(`객체 ${id} 할당됨`);
    }
    
    // 참조 설정
    addReference(fromId, toId) {
        if (this.heap.has(fromId) && this.heap.has(toId)) {
            this.heap.get(fromId).references.add(toId);
            console.log(`참조 추가: ${fromId} → ${toId}`);
        }
    }
    
    // 루트 설정
    addRoot(id) {
        this.roots.add(id);
        console.log(`루트 추가: ${id}`);
    }
    
    // 루트 제거
    removeRoot(id) {
        this.roots.delete(id);
        console.log(`루트 제거: ${id}`);
    }
    
    // Mark 단계: 도달 가능한 객체들을 마킹
    mark() {
        console.log('=== Mark 단계 시작 ===');
        
        // 루트에서 시작하여 모든 도달 가능한 객체 마킹
        for (const rootId of this.roots) {
            this.markObject(rootId);
        }
    }
    
    markObject(id) {
        if (!this.heap.has(id)) return;
        
        const object = this.heap.get(id);
        if (object.marked) return; // 이미 마킹된 객체는 건너뛰기
        
        object.marked = true;
        console.log(`객체 ${id} 마킹됨`);
        
        // 참조된 객체들도 마킹
        for (const refId of object.references) {
            this.markObject(refId);
        }
    }
    
    // Sweep 단계: 마킹되지 않은 객체들 제거
    sweep() {
        console.log('=== Sweep 단계 시작 ===');
        const toDelete = [];
        
        for (const [id, object] of this.heap) {
            if (!object.marked) {
                toDelete.push(id);
                console.log(`객체 ${id} 제거 예정`);
            } else {
                object.marked = false; // 마킹 초기화
            }
        }
        
        // 가비지 객체들 제거
        for (const id of toDelete) {
            this.heap.delete(id);
            console.log(`객체 ${id} 메모리 해제됨`);
        }
        
        return toDelete.length;
    }
    
    // 가비지 컬렉션 실행
    collect() {
        console.log('가비지 컬렉션 시작...');
        this.mark();
        const freedCount = this.sweep();
        console.log(`가비지 컬렉션 완료. ${freedCount}개 객체 해제됨`);
        return freedCount;
    }
    
    // 힙 상태 출력
    printHeap() {
        console.log('=== 힙 상태 ===');
        for (const [id, object] of this.heap) {
            const isRoot = this.roots.has(id);
            console.log(`객체 ${id}: ${JSON.stringify(object.data)} ${isRoot ? '(루트)' : ''}`);
        }
    }
}

// 사용 예시
const gc = new GarbageCollector();

// 객체들 할당
gc.allocate('A', { name: 'Alice' });
gc.allocate('B', { name: 'Bob' });
gc.allocate('C', { name: 'Charlie' });

// 참조 관계 설정
gc.addReference('A', 'B');
gc.addReference('B', 'C');

// 루트 설정
gc.addRoot('A');

gc.printHeap();
gc.collect();

// 루트 제거
gc.removeRoot('A');
gc.collect();
```

#### Generational Garbage Collection
```javascript
// Generational GC 시뮬레이션
class GenerationalGC {
    constructor() {
        this.youngGeneration = new Map(); // 새 객체들
        this.oldGeneration = new Map();   // 오래된 객체들
        this.roots = new Set();
        this.ageMap = new Map(); // 객체별 나이 추적
    }
    
    // 객체 할당 (항상 Young Generation에)
    allocate(id, data) {
        this.youngGeneration.set(id, {
            data: data,
            marked: false,
            references: new Set()
        });
        this.ageMap.set(id, 0);
        console.log(`새 객체 ${id} 할당됨 (Young Generation)`);
    }
    
    // 참조 설정
    addReference(fromId, toId) {
        const fromObject = this.youngGeneration.get(fromId) || this.oldGeneration.get(fromId);
        if (fromObject) {
            fromObject.references.add(toId);
        }
    }
    
    // Minor GC (Young Generation만)
    minorGC() {
        console.log('=== Minor GC 시작 ===');
        
        // Young Generation 마킹
        for (const rootId of this.roots) {
            this.markObject(rootId, this.youngGeneration);
        }
        
        // 살아남은 객체들을 Old Generation으로 이동
        const survivors = [];
        for (const [id, object] of this.youngGeneration) {
            if (object.marked) {
                survivors.push(id);
                this.oldGeneration.set(id, object);
                this.ageMap.set(id, (this.ageMap.get(id) || 0) + 1);
                console.log(`객체 ${id} Old Generation으로 이동 (나이: ${this.ageMap.get(id)})`);
            }
        }
        
        // Young Generation 클리어
        this.youngGeneration.clear();
        
        console.log(`Minor GC 완료. ${survivors.length}개 객체 생존`);
        return survivors.length;
    }
    
    // Major GC (Old Generation)
    majorGC() {
        console.log('=== Major GC 시작 ===');
        
        // Old Generation 마킹
        for (const rootId of this.roots) {
            this.markObject(rootId, this.oldGeneration);
        }
        
        // 마킹되지 않은 객체들 제거
        const toDelete = [];
        for (const [id, object] of this.oldGeneration) {
            if (!object.marked) {
                toDelete.push(id);
            } else {
                object.marked = false;
            }
        }
        
        for (const id of toDelete) {
            this.oldGeneration.delete(id);
            this.ageMap.delete(id);
            console.log(`오래된 객체 ${id} 제거됨`);
        }
        
        console.log(`Major GC 완료. ${toDelete.length}개 객체 제거`);
        return toDelete.length;
    }
    
    markObject(id, generation) {
        if (!generation.has(id)) return;
        
        const object = generation.get(id);
        if (object.marked) return;
        
        object.marked = true;
        
        for (const refId of object.references) {
            // Young Generation에서 참조 확인
            if (this.youngGeneration.has(refId)) {
                this.markObject(refId, this.youngGeneration);
            }
            // Old Generation에서 참조 확인
            if (this.oldGeneration.has(refId)) {
                this.markObject(refId, this.oldGeneration);
            }
        }
    }
    
    // 통합 GC 실행
    collect() {
        const minorFreed = this.minorGC();
        const majorFreed = this.majorGC();
        
        console.log(`GC 완료: Minor=${minorFreed}, Major=${majorFreed}`);
        return { minorFreed, majorFreed };
    }
}

// 사용 예시
const genGC = new GenerationalGC();

// 객체들 할당
genGC.allocate('A', { name: 'Alice' });
genGC.allocate('B', { name: 'Bob' });
genGC.allocate('C', { name: 'Charlie' });

genGC.addReference('A', 'B');
genGC.addReference('B', 'C');
genGC.roots.add('A');

genGC.collect();
```

### 2. 메모리 누수 방지

정리하면, 자바스크립트에서 메모리가 새는 경우는 대부분 **"엔진이 회수를 못 하는 것"이 아니라 "코드가 참조를 놓지 않는 것"**이다. 아래 네 가지가 실제로 자주 나온다.

| 패턴 | 왜 안 풀리나 |
|------|-------------|
| 이벤트 리스너 | 핸들러가 `this` 를 통해 컴포넌트 전체를 붙잡는다 |
| 타이머 | `setInterval` 은 취소 전까지 콜백과 그 클로저를 살려 둔다 |
| 전역 캐시 | 상한이 없으면 프로세스 수명 내내 자란다 |
| 분리된 DOM | 화면에서 지워도 JS 변수가 노드를 들고 있으면 회수 안 된다 |

**키를 계속 붙잡는 자료구조도 같은 부류다.** `Map` 은 키를 강하게 참조해서, 키로 쓴 객체를 바깥에서 다 버려도 `Map` 이 살아 있는 한 값까지 통째로 남는다. `WeakMap` 은 키가 도달 불가능해지면 항목째 사라진다.

```
객체 40개를 키로 큰 값을 넣고 키를 전부 버린 뒤 GC:
  WeakMap →  0MB   (키가 사라지면 값도 회수)
  Map     → 61MB   (키를 강하게 잡아 그대로 남음)
```

객체에 부가 정보를 매달아 두는 용도(메타데이터, 캐시)라면 `WeakMap` 이 맞다. 반대로 **목록을 순회해야 한다면 `WeakMap` 은 못 쓴다** — 열거가 안 되기 때문이고, 이건 회수 가능성과 맞바꾼 대가다.

#### 일반적인 메모리 누수 패턴
```javascript
// 메모리 누수 예시와 해결책
class MemoryLeakExamples {
    constructor() {
        this.listeners = new Map();
        this.timers = new Set();
        this.data = new Map();
    }
    
    // 1. 이벤트 리스너 누수
    addEventListenerLeak(element, eventType, handler) {
        element.addEventListener(eventType, handler);
        // 문제: 이벤트 리스너가 제거되지 않음
    }
    
    // 해결책: 적절한 제거
    addEventListenerSafe(element, eventType, handler) {
        element.addEventListener(eventType, handler);
        
        // 제거 함수 반환
        return () => {
            element.removeEventListener(eventType, handler);
        };
    }
    
    // 2. 타이머 누수
    createTimerLeak() {
        const timer = setInterval(() => {
            console.log('타이머 실행 중...');
        }, 1000);
        // 문제: clearInterval이 호출되지 않음
    }
    
    // 해결책: 타이머 관리
    createTimerSafe() {
        const timer = setInterval(() => {
            console.log('타이머 실행 중...');
        }, 1000);
        
        this.timers.add(timer);
        
        return () => {
            clearInterval(timer);
            this.timers.delete(timer);
        };
    }
    
    // 3. 클로저 누수
    createClosureLeak() {
        const largeData = new Array(1000000).fill('data');
        
        return function() {
            console.log('클로저에서 largeData 참조');
            // 문제: largeData가 계속 메모리에 유지됨
        };
    }
    
    // 해결책: 필요 없을 때 null 설정
    createClosureSafe() {
        let largeData = new Array(1000000).fill('data');
        
        const closure = function() {
            console.log('클로저에서 largeData 참조');
        };
        
        // 필요 없을 때 메모리 해제
        closure.cleanup = function() {
            largeData = null;
        };
        
        return closure;
    }
    
    // 4. DOM 참조 누수
    createDOMLeak() {
        const elements = document.querySelectorAll('.some-class');
        const data = new Array(10000).fill('data');
        
        elements.forEach((element, index) => {
            element.data = data[index]; // DOM에 직접 데이터 저장
        });
        // 문제: DOM 요소가 제거되어도 data가 메모리에 남음
    }
    
    // 해결책: WeakMap 사용
    createDOMSafe() {
        const elements = document.querySelectorAll('.some-class');
        const dataMap = new WeakMap();
        const data = new Array(10000).fill('data');
        
        elements.forEach((element, index) => {
            dataMap.set(element, data[index]); // WeakMap 사용
        });
        // 장점: DOM 요소가 제거되면 자동으로 메모리 해제
    }
    
    // 5. 전역 변수 누수
    createGlobalLeak() {
        window.globalData = new Array(1000000).fill('data');
        // 문제: 전역 변수로 인한 메모리 누수
    }
    
    // 해결책: 모듈 패턴 사용
    createGlobalSafe() {
        const module = (function() {
            const privateData = new Array(1000000).fill('data');
            
            return {
                getData: function() {
                    return privateData;
                },
                cleanup: function() {
                    // 필요 없을 때 정리
                    privateData.length = 0;
                }
            };
        })();
        
        return module;
    }
    
    // 모든 타이머 정리
    cleanup() {
        for (const timer of this.timers) {
            clearInterval(timer);
        }
        this.timers.clear();
        console.log('모든 타이머 정리됨');
    }
}

// 사용 예시
const leakExamples = new MemoryLeakExamples();

// 안전한 이벤트 리스너
const removeListener = leakExamples.addEventListenerSafe(
    document.body, 
    'click', 
    () => console.log('클릭됨')
);

// 안전한 타이머
const stopTimer = leakExamples.createTimerSafe();

// 정리
setTimeout(() => {
    removeListener();
    stopTimer();
    leakExamples.cleanup();
}, 5000);
```

## 예시

### 1. 실제 사용 사례

#### 메모리 누수 디버깅 도구
```javascript
// 메모리 누수 디버깅 도구
class MemoryLeakDetector {
    constructor() {
        this.snapshots = [];
        this.observers = new Set();
    }
    
    // 메모리 스냅샷 생성
    takeSnapshot() {
        if (performance.memory) {
            const snapshot = {
                timestamp: Date.now(),
                usedJSHeapSize: performance.memory.usedJSHeapSize,
                totalJSHeapSize: performance.memory.totalJSHeapSize,
                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
            };
            
            this.snapshots.push(snapshot);
            console.log('메모리 스냅샷 생성:', snapshot);
            
            return snapshot;
        } else {
            console.warn('performance.memory를 사용할 수 없습니다.');
            return null;
        }
    }
    
    // 메모리 사용량 분석
    analyzeMemoryUsage() {
        if (this.snapshots.length < 2) {
            console.log('분석을 위해 최소 2개의 스냅샷이 필요합니다.');
            return;
        }
        
        const latest = this.snapshots[this.snapshots.length - 1];
        const previous = this.snapshots[this.snapshots.length - 2];
        
        const usedDiff = latest.usedJSHeapSize - previous.usedJSHeapSize;
        const totalDiff = latest.totalJSHeapSize - previous.totalJSHeapSize;
        
        console.log('=== 메모리 사용량 분석 ===');
        console.log(`사용된 힙 크기 변화: ${this.formatBytes(usedDiff)}`);
        console.log(`전체 힙 크기 변화: ${this.formatBytes(totalDiff)}`);
        console.log(`메모리 사용률: ${(latest.usedJSHeapSize / latest.totalJSHeapSize * 100).toFixed(2)}%`);
        
        // 메모리 누수 의심 지점
        if (usedDiff > 1024 * 1024) { // 1MB 이상 증가
            console.warn('⚠️ 메모리 누수가 의심됩니다!');
        }
    }
    
    // 바이트 단위 포맷팅
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
        
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
    }
    
    // 메모리 모니터링 시작
    startMonitoring(interval = 5000) {
        console.log(`메모리 모니터링 시작 (${interval}ms 간격)`);
        
        const monitor = setInterval(() => {
            this.takeSnapshot();
            this.analyzeMemoryUsage();
        }, interval);
        
        return () => {
            clearInterval(monitor);
            console.log('메모리 모니터링 중지');
        };
    }
    
    // 힙 스냅샷 비교
    compareSnapshots() {
        if (this.snapshots.length < 2) return;
        
        const first = this.snapshots[0];
        const last = this.snapshots[this.snapshots.length - 1];
        
        console.log('=== 전체 기간 메모리 변화 ===');
        console.log(`초기 사용량: ${this.formatBytes(first.usedJSHeapSize)}`);
        console.log(`최종 사용량: ${this.formatBytes(last.usedJSHeapSize)}`);
        console.log(`총 증가량: ${this.formatBytes(last.usedJSHeapSize - first.usedJSHeapSize)}`);
    }
}

// 사용 예시
const detector = new MemoryLeakDetector();

// 메모리 모니터링 시작
const stopMonitoring = detector.startMonitoring(3000);

// 30초 후 모니터링 중지
setTimeout(() => {
    stopMonitoring();
    detector.compareSnapshots();
}, 30000);
```

#### 메모리 효율적인 데이터 구조
```javascript
// 메모리 효율적인 데이터 구조들
class MemoryEfficientDataStructures {
    constructor() {
        this.weakMap = new WeakMap();
        this.weakSet = new WeakSet();
        this.objectPool = new Map();
    }
    
    // WeakMap을 사용한 객체 캐시
    createObjectCache() {
        return {
            cache: new WeakMap(),
            
            set(key, value) {
                this.cache.set(key, value);
            },
            
            get(key) {
                return this.cache.get(key);
            },
            
            has(key) {
                return this.cache.has(key);
            }
        };
    }
    
    // WeakSet을 사용한 중복 체크
    createDuplicateChecker() {
        return {
            seen: new WeakSet(),
            
            isDuplicate(obj) {
                if (this.seen.has(obj)) {
                    return true;
                }
                this.seen.add(obj);
                return false;
            },
            
            clear() {
                this.seen = new WeakSet();
            }
        };
    }
    
    // 객체 풀링 (Object Pooling)
    createObjectPool(factory, maxSize = 100) {
        return {
            pool: [],
            factory: factory,
            maxSize: maxSize,
            
            acquire() {
                if (this.pool.length > 0) {
                    const obj = this.pool.pop();
                    console.log('객체 풀에서 재사용');
                    return obj;
                } else {
                    console.log('새 객체 생성');
                    return this.factory();
                }
            },
            
            release(obj) {
                if (this.pool.length < this.maxSize) {
                    // 객체 초기화
                    if (obj.reset) {
                        obj.reset();
                    }
                    this.pool.push(obj);
                    console.log('객체 풀에 반환');
                } else {
                    console.log('풀이 가득 참, 객체 폐기');
                }
            },
            
            getPoolSize() {
                return this.pool.length;
            }
        };
    }
    
    // 메모리 효율적인 배열
    createEfficientArray() {
        return {
            data: [],
            
            add(item) {
                this.data.push(item);
            },
            
            remove(item) {
                const index = this.data.indexOf(item);
                if (index > -1) {
                    this.data.splice(index, 1);
                }
            },
            
            // 배열 크기 최적화
            optimize() {
                if (this.data.length < this.data.capacity * 0.5) {
                    this.data.length = this.data.length;
                    console.log('배열 크기 최적화됨');
                }
            },
            
            clear() {
                this.data.length = 0;
            }
        };
    }
    
    // 메모리 효율적인 문자열 처리
    createStringBuilder() {
        return {
            parts: [],
            
            append(str) {
                this.parts.push(str);
            },
            
            toString() {
                return this.parts.join('');
            },
            
            clear() {
                this.parts.length = 0;
            }
        };
    }
}

// 사용 예시
const efficient = new MemoryEfficientDataStructures();

// 객체 캐시 사용
const cache = efficient.createObjectCache();
const obj1 = { id: 1 };
const obj2 = { id: 2 };

cache.set(obj1, 'data1');
cache.set(obj2, 'data2');

console.log(cache.get(obj1)); // 'data1'

// 객체 풀 사용
const pool = efficient.createObjectPool(() => ({
    id: Math.random(),
    reset() {
        this.id = null;
    }
}));

const pooledObj1 = pool.acquire();
const pooledObj2 = pool.acquire();

pool.release(pooledObj1);
pool.release(pooledObj2);

console.log('풀 크기:', pool.getPoolSize()); // 2
```

### 2. 성능 최적화 패턴

#### 메모리 사용량 최적화
```javascript
// 메모리 사용량 최적화 도구
class MemoryOptimizer {
    constructor() {
        this.optimizations = new Map();
    }
    
    // 큰 객체 분할
    splitLargeObject(largeObject, chunkSize = 1000) {
        const keys = Object.keys(largeObject);
        const chunks = [];
        
        for (let i = 0; i < keys.length; i += chunkSize) {
            const chunk = {};
            const chunkKeys = keys.slice(i, i + chunkSize);
            
            chunkKeys.forEach(key => {
                chunk[key] = largeObject[key];
            });
            
            chunks.push(chunk);
        }
        
        return chunks;
    }
    
    // 객체 압축
    compressObject(obj) {
        const compressed = {};
        
        for (const [key, value] of Object.entries(obj)) {
            if (value !== null && value !== undefined) {
                compressed[key] = value;
            }
        }
        
        return compressed;
    }
    
    // 배열 최적화
    optimizeArray(array) {
        // 중복 제거
        const unique = [...new Set(array)];
        
        // 정렬 (필요한 경우)
        unique.sort();
        
        return unique;
    }
    
    // 메모리 사용량 측정
    measureMemoryUsage() {
        if (performance.memory) {
            return {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit,
                usage: (performance.memory.usedJSHeapSize / performance.memory.totalJSHeapSize * 100).toFixed(2) + '%'
            };
        }
        return null;
    }
    
    // 메모리 정리
    cleanup() {
        // 가비지 컬렉션 강제 실행 (가능한 경우)
        if (window.gc) {
            window.gc();
            console.log('가비지 컬렉션 강제 실행');
        }
        
        // 메모리 사용량 출력
        const memory = this.measureMemoryUsage();
        if (memory) {
            console.log('메모리 사용량:', memory);
        }
    }
}

// 사용 예시
const optimizer = new MemoryOptimizer();

// 큰 객체 분할
const largeObject = {};
for (let i = 0; i < 5000; i++) {
    largeObject[`key${i}`] = `value${i}`;
}

const chunks = optimizer.splitLargeObject(largeObject, 1000);
console.log(`큰 객체를 ${chunks.length}개 청크로 분할`);

// 메모리 정리
optimizer.cleanup();
```

## 운영 팁

### 성능 최적화

#### 메모리 사용량 모니터링
```javascript
// 메모리 사용량 모니터링 도구
class MemoryMonitor {
    constructor() {
        this.history = [];
        this.maxHistory = 100;
        this.threshold = 0.8; // 80% 사용률 경고
    }
    
    // 메모리 상태 체크
    checkMemory() {
        if (!performance.memory) {
            console.warn('메모리 정보를 사용할 수 없습니다.');
            return null;
        }
        
        const memory = {
            timestamp: Date.now(),
            used: performance.memory.usedJSHeapSize,
            total: performance.memory.totalJSHeapSize,
            limit: performance.memory.jsHeapSizeLimit,
            usage: performance.memory.usedJSHeapSize / performance.memory.totalJSHeapSize
        };
        
        this.history.push(memory);
        
        // 히스토리 크기 제한
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        }
        
        // 경고 체크
        if (memory.usage > this.threshold) {
            console.warn(`⚠️ 메모리 사용률이 높습니다: ${(memory.usage * 100).toFixed(2)}%`);
        }
        
        return memory;
    }
    
    // 메모리 사용량 추이 분석
    analyzeTrend() {
        if (this.history.length < 2) return;
        
        const recent = this.history.slice(-10);
        const older = this.history.slice(-20, -10);
        
        const recentAvg = recent.reduce((sum, m) => sum + m.usage, 0) / recent.length;
        const olderAvg = older.reduce((sum, m) => sum + m.usage, 0) / older.length;
        
        const trend = recentAvg - olderAvg;
        
        if (trend > 0.1) {
            console.warn('⚠️ 메모리 사용량이 증가하는 추세입니다.');
        } else if (trend < -0.1) {
            console.log('✅ 메모리 사용량이 감소하는 추세입니다.');
        }
        
        return { trend, recentAvg, olderAvg };
    }
    
    // 메모리 누수 감지
    detectLeak() {
        if (this.history.length < 10) return false;
        
        const recent = this.history.slice(-5);
        const older = this.history.slice(-10, -5);
        
        const recentGrowth = recent[recent.length - 1].used - recent[0].used;
        const olderGrowth = older[older.length - 1].used - older[0].used;
        
        // 지속적인 메모리 증가 감지
        if (recentGrowth > 1024 * 1024 && olderGrowth > 1024 * 1024) {
            console.error('🚨 메모리 누수가 의심됩니다!');
            return true;
        }
        
        return false;
    }
    
    // 주기적 모니터링 시작
    startMonitoring(interval = 5000) {
        console.log(`메모리 모니터링 시작 (${interval}ms 간격)`);
        
        const monitor = setInterval(() => {
            this.checkMemory();
            this.analyzeTrend();
            this.detectLeak();
        }, interval);
        
        return () => {
            clearInterval(monitor);
            console.log('메모리 모니터링 중지');
        };
    }
    
    // 히스토리 출력
    printHistory() {
        console.log('=== 메모리 사용량 히스토리 ===');
        this.history.forEach((memory, index) => {
            console.log(`${index + 1}: ${(memory.usage * 100).toFixed(2)}% 사용`);
        });
    }
}

// 사용 예시
const monitor = new MemoryMonitor();
const stopMonitoring = monitor.startMonitoring(3000);

// 30초 후 모니터링 중지 및 분석
setTimeout(() => {
    stopMonitoring();
    monitor.printHistory();
}, 30000);
```

#### 메모리 효율적인 코딩 패턴
```javascript
// 메모리 효율적인 코딩 패턴들
class MemoryEfficientPatterns {
    constructor() {
        this.patterns = new Map();
    }
    
    // 1. 객체 재사용
    createObjectReuser() {
        return {
            pool: [],
            
            get() {
                if (this.pool.length > 0) {
                    return this.pool.pop();
                }
                return {};
            },
            
            release(obj) {
                // 객체 초기화
                for (const key in obj) {
                    delete obj[key];
                }
                this.pool.push(obj);
            }
        };
    }
    
    // 2. 함수 메모이제이션
    createMemoizer() {
        const cache = new Map();
        
        return function(func) {
            return function(...args) {
                const key = JSON.stringify(args);
                
                if (cache.has(key)) {
                    return cache.get(key);
                }
                
                const result = func.apply(this, args);
                cache.set(key, result);
                
                return result;
            };
        };
    }
    
    // 3. 지연 로딩
    createLazyLoader() {
        return {
            data: null,
            loader: null,
            
            setLoader(loader) {
                this.loader = loader;
            },
            
            get() {
                if (this.data === null && this.loader) {
                    this.data = this.loader();
                }
                return this.data;
            },
            
            clear() {
                this.data = null;
            }
        };
    }
    
    // 4. 스트림 처리
    createStreamProcessor() {
        return {
            process(data, processor, chunkSize = 1000) {
                const results = [];
                
                for (let i = 0; i < data.length; i += chunkSize) {
                    const chunk = data.slice(i, i + chunkSize);
                    const processed = processor(chunk);
                    results.push(...processed);
                    
                    // 청크 처리 후 잠시 대기 (메모리 해제 시간)
                    if (i % (chunkSize * 10) === 0) {
                        yield new Promise(resolve => setTimeout(resolve, 0));
                    }
                }
                
                return results;
            }
        };
    }
    
    // 5. 메모리 효율적인 반복문
    createEfficientIterator() {
        return {
            // 배열 대신 제너레이터 사용
            *range(start, end, step = 1) {
                for (let i = start; i < end; i += step) {
                    yield i;
                }
            },
            
            // 큰 배열 처리
            processLargeArray(array, processor, chunkSize = 1000) {
                for (let i = 0; i < array.length; i += chunkSize) {
                    const chunk = array.slice(i, i + chunkSize);
                    processor(chunk, i);
                }
            }
        };
    }
}

// 사용 예시
const patterns = new MemoryEfficientPatterns();

// 객체 재사용
const reuser = patterns.createObjectReuser();
const obj1 = reuser.get();
obj1.name = 'test';
reuser.release(obj1);

// 지연 로딩
const lazyData = patterns.createLazyLoader();
lazyData.setLoader(() => {
    console.log('데이터 로딩 중...');
    return new Array(1000000).fill('data');
});

// 실제 사용할 때만 로딩
console.log(lazyData.get().length);
```

## 참고

### 가비지 컬렉션 최적화 가이드

#### 성능 최적화 권장사항
```javascript
// 가비지 컬렉션 최적화 가이드
const GCOptimizationGuide = {
    // 1. 객체 생성 최소화
    minimizeObjectCreation: {
        description: '불필요한 객체 생성 방지',
        examples: [
            '문자열 연결 시 배열 사용',
            '객체 풀링 활용',
            '제너레이터 함수 사용'
        ]
    },
    
    // 2. 메모리 누수 방지
    preventMemoryLeaks: {
        description: '메모리 누수 패턴 회피',
        examples: [
            '이벤트 리스너 적절한 제거',
            '타이머 정리',
            'DOM 참조 해제'
        ]
    },
    
    // 3. 데이터 구조 최적화
    optimizeDataStructures: {
        description: '메모리 효율적인 데이터 구조 사용',
        examples: [
            'WeakMap/WeakSet 활용',
            '배열 크기 최적화',
            '객체 압축'
        ]
    },
    
    // 4. 비동기 처리 최적화
    optimizeAsyncProcessing: {
        description: '비동기 작업의 메모리 관리',
        examples: [
            'Promise 체인 최적화',
            '스트림 처리',
            '청크 단위 처리'
        ]
    }
};

// 사용 예시
Object.entries(GCOptimizationGuide).forEach(([key, guide]) => {
    console.log(`${key}: ${guide.description}`);
    guide.examples.forEach(example => {
        console.log(`  - ${example}`);
    });
});
```

### 성능 측정

#### 가비지 컬렉션 성능 측정
```javascript
// 가비지 컬렉션 성능 측정 도구
class GCPerformanceTester {
    static testMemoryAllocation(allocator, iterations = 1000) {
        console.log('=== 메모리 할당 성능 테스트 ===');
        
        const startTime = performance.now();
        const startMemory = performance.memory?.usedJSHeapSize || 0;
        
        const objects = [];
        
        for (let i = 0; i < iterations; i++) {
            objects.push(allocator());
        }
        
        const endTime = performance.now();
        const endMemory = performance.memory?.usedJSHeapSize || 0;
        
        console.log(`할당 시간: ${(endTime - startTime).toFixed(2)}ms`);
        console.log(`메모리 사용량: ${((endMemory - startMemory) / 1024 / 1024).toFixed(2)}MB`);
        console.log(`평균 할당 시간: ${((endTime - startTime) / iterations).toFixed(4)}ms`);
        
        return {
            totalTime: endTime - startTime,
            memoryUsed: endMemory - startMemory,
            averageTime: (endTime - startTime) / iterations
        };
    }
    
    static testGarbageCollection() {
        console.log('=== 가비지 컬렉션 테스트 ===');
        
        const initialMemory = performance.memory?.usedJSHeapSize || 0;
        
        // 많은 객체 생성
        const objects = [];
        for (let i = 0; i < 100000; i++) {
            objects.push({ id: i, data: new Array(100).fill('data') });
        }
        
        const peakMemory = performance.memory?.usedJSHeapSize || 0;
        
        // 객체 참조 해제
        objects.length = 0;
        
        // 가비지 컬렉션 강제 실행 (가능한 경우)
        if (window.gc) {
            window.gc();
        }
        
        const finalMemory = performance.memory?.usedJSHeapSize || 0;
        
        console.log(`초기 메모리: ${(initialMemory / 1024 / 1024).toFixed(2)}MB`);
        console.log(`최대 메모리: ${(peakMemory / 1024 / 1024).toFixed(2)}MB`);
        console.log(`최종 메모리: ${(finalMemory / 1024 / 1024).toFixed(2)}MB`);
        console.log(`메모리 해제: ${((peakMemory - finalMemory) / 1024 / 1024).toFixed(2)}MB`);
        
        return {
            initialMemory,
            peakMemory,
            finalMemory,
            freedMemory: peakMemory - finalMemory
        };
    }
}

// 성능 테스트 실행
const testResults = GCPerformanceTester.testMemoryAllocation(() => ({
    id: Math.random(),
    data: new Array(100).fill('test')
}));

GCPerformanceTester.testGarbageCollection();
```

### 결론
가비지 컬렉션은 JavaScript의 메모리 관리를 자동화하는 핵심 메커니즘입니다.
Mark and Sweep 알고리즘과 Generational GC가 주요 가비지 컬렉션 방식입니다.
메모리 누수를 방지하기 위해 이벤트 리스너, 타이머, DOM 참조를 적절히 정리해야 합니다.
WeakMap과 WeakSet을 사용하여 메모리 효율적인 데이터 구조를 구현할 수 있습니다.
메모리 사용량을 모니터링하고 최적화하여 애플리케이션 성능을 향상시킬 수 있습니다.
가비지 컬렉션은 자동으로 동작하지만, 개발자가 메모리 사용 패턴을 최적화하면 성능을 크게 향상시킬 수 있습니다.

