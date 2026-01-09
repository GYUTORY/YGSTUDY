---
title: TypeScript void 타입 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, primitive-types, void]
updated: 2025-08-10
---

# TypeScript void 타입 가이드

## 배경

TypeScript에서 `void` 타입은 함수가 값을 반환하지 않는 경우의 반환 타입을 나타냅니다.

### void 타입의 필요성
- **반환값 없음 명시**: 함수가 값을 반환하지 않음을 명확히 표현
- **타입 안전성**: 반환값이 없는 함수의 타입 보장
- **코드 가독성**: 함수의 의도를 명확하게 전달
- **API 설계**: 반환값이 없는 함수의 인터페이스 정의

### 기본 개념
- **반환값 없음**: 함수가 명시적인 값을 반환하지 않음
- **undefined 반환**: JavaScript에서는 암묵적으로 undefined 반환
- **타입 추론**: 반환문이 없으면 자동으로 void로 추론
- **함수 전용**: 주로 함수의 반환 타입으로 사용

## 핵심

### 1. void 타입 기본 사용법

#### void 함수 선언
```typescript
// 명시적 void 반환 타입
function printMessage(): void {
    console.log('Hello, World!');
}

// 반환문이 없는 함수 (자동으로 void 추론)
function logInfo(): void {
    console.log('정보를 로그에 기록합니다.');
    // return 문이 없음
}

// void 함수 호출
printMessage(); // "Hello, World!"
logInfo();      // "정보를 로그에 기록합니다."

// void 함수의 반환값 사용 (undefined)
const result = printMessage();
console.log(result); // undefined
```

#### void와 return 문
```typescript
// void 함수에서 return 사용
function processData(data: string): void {
    if (!data) {
        return; // 값을 반환하지 않고 함수 종료
    }
    console.log('데이터 처리:', data);
}

// void 함수에서 return undefined
function validateInput(input: string): void {
    if (input.length === 0) {
        return undefined; // 명시적으로 undefined 반환
    }
    console.log('입력값 검증 완료:', input);
}

// 사용 예시
processData('');        // 아무것도 출력되지 않음
processData('test');    // "데이터 처리: test"

validateInput('');      // 아무것도 출력되지 않음
validateInput('hello'); // "입력값 검증 완료: hello"
```

### 2. void와 함수 타입

#### void 함수 타입 정의
```typescript
// void 함수 타입 정의
type VoidFunction = () => void;
type StringProcessor = (input: string) => void;

// void 함수 타입 사용
const logger: VoidFunction = () => {
    console.log('로그 메시지');
};

const stringHandler: StringProcessor = (str: string) => {
    console.log('문자열 처리:', str.toUpperCase());
};

// 사용 예시
logger();           // "로그 메시지"
stringHandler('hello'); // "문자열 처리: HELLO"
```

#### void와 콜백 함수
```typescript
// void 콜백 함수
function processArray<T>(
    items: T[],
    callback: (item: T, index: number) => void
): void {
    items.forEach((item, index) => {
        callback(item, index);
    });
}

// void 콜백 함수 사용
const numbers = [1, 2, 3, 4, 5];

processArray(numbers, (num, index) => {
    console.log(`인덱스 ${index}: ${num}`);
});

// 결과:
// "인덱스 0: 1"
// "인덱스 1: 2"
// "인덱스 2: 3"
// "인덱스 3: 4"
// "인덱스 4: 5"
```

### 3. void와 이벤트 핸들러

#### 이벤트 핸들러에서 void 사용
```typescript
// 이벤트 핸들러 타입 정의
type ClickHandler = (event: MouseEvent) => void;
type KeyHandler = (event: KeyboardEvent) => void;

// void 이벤트 핸들러
const handleClick: ClickHandler = (event) => {
    console.log('클릭 이벤트:', event.target);
    // 값을 반환하지 않음
};

const handleKeyPress: KeyHandler = (event) => {
    if (event.key === 'Enter') {
        console.log('Enter 키가 눌렸습니다.');
    }
    // 값을 반환하지 않음
};

// 사용 예시 (실제 DOM에서는 이렇게 사용)
// button.addEventListener('click', handleClick);
// input.addEventListener('keypress', handleKeyPress);
```

## 예시

### 1. 실제 사용 사례

#### 로깅 시스템
```typescript
interface LogLevel {
    INFO: 'info';
    WARN: 'warn';
    ERROR: 'error';
}

type LogLevelType = LogLevel[keyof LogLevel];

class Logger {
    private logs: Array<{ level: LogLevelType; message: string; timestamp: Date }> = [];

    log(level: LogLevelType, message: string): void {
        const logEntry = {
            level,
            message,
            timestamp: new Date()
        };
        
        this.logs.push(logEntry);
        console.log(`[${level.toUpperCase()}] ${message}`);
    }

    info(message: string): void {
        this.log('info', message);
    }

    warn(message: string): void {
        this.log('warn', message);
    }

    error(message: string): void {
        this.log('error', message);
    }

    getLogs(): Array<{ level: LogLevelType; message: string; timestamp: Date }> {
        return [...this.logs];
    }

    clearLogs(): void {
        this.logs = [];
    }
}

// 사용 예시
const logger = new Logger();

logger.info('애플리케이션이 시작되었습니다.');
logger.warn('메모리 사용량이 높습니다.');
logger.error('데이터베이스 연결에 실패했습니다.');

console.log('로그 개수:', logger.getLogs().length); // 3
logger.clearLogs();
console.log('로그 개수:', logger.getLogs().length); // 0
```

#### 상태 관리 시스템
```typescript
interface State {
    count: number;
    isLoading: boolean;
    error: string | null;
}

class StateManager {
    private state: State = {
        count: 0,
        isLoading: false,
        error: null
    };

    private listeners: Array<(state: State) => void> = [];

    getState(): State {
        return { ...this.state };
    }

    setState(updates: Partial<State>): void {
        this.state = { ...this.state, ...updates };
        this.notifyListeners();
    }

    subscribe(listener: (state: State) => void): void {
        this.listeners.push(listener);
    }

    unsubscribe(listener: (state: State) => void): void {
        const index = this.listeners.indexOf(listener);
        if (index > -1) {
            this.listeners.splice(index, 1);
        }
    }

    private notifyListeners(): void {
        this.listeners.forEach(listener => {
            listener(this.getState());
        });
    }

    increment(): void {
        this.setState({ count: this.state.count + 1 });
    }

    decrement(): void {
        this.setState({ count: this.state.count - 1 });
    }

    setLoading(isLoading: boolean): void {
        this.setState({ isLoading });
    }

    setError(error: string | null): void {
        this.setState({ error });
    }
}

// 사용 예시
const stateManager = new StateManager();

// 상태 변경 리스너
const stateListener = (state: State) => {
    console.log('상태 변경:', state);
};

stateManager.subscribe(stateListener);

stateManager.increment(); // 상태 변경: { count: 1, isLoading: false, error: null }
stateManager.setLoading(true); // 상태 변경: { count: 1, isLoading: true, error: null }
stateManager.setError('오류 발생'); // 상태 변경: { count: 1, isLoading: true, error: '오류 발생' }
```

### 2. 고급 패턴

#### void와 제네릭
```typescript
// void를 반환하는 제네릭 함수
class DataProcessor<T> {
    private data: T[] = [];

    add(item: T): void {
        this.data.push(item);
    }

    remove(predicate: (item: T) => boolean): void {
        this.data = this.data.filter(item => !predicate(item));
    }

    forEach(callback: (item: T, index: number) => void): void {
        this.data.forEach(callback);
    }

    clear(): void {
        this.data = [];
    }

    getItems(): T[] {
        return [...this.data];
    }
}

// 사용 예시
const processor = new DataProcessor<string>();

processor.add('item1');
processor.add('item2');
processor.add('item3');

processor.forEach((item, index) => {
    console.log(`항목 ${index}: ${item}`);
});

processor.remove(item => item === 'item2');
console.log('제거 후:', processor.getItems()); // ['item1', 'item3']

processor.clear();
console.log('클리어 후:', processor.getItems()); // []
```

#### void와 비동기 함수
```typescript
// void를 반환하는 비동기 함수
class AsyncTaskManager {
    private tasks: Array<() => Promise<void>> = [];

    addTask(task: () => Promise<void>): void {
        this.tasks.push(task);
    }

    async executeAll(): Promise<void> {
        for (const task of this.tasks) {
            try {
                await task();
            } catch (error) {
                console.error('작업 실행 오류:', error);
            }
        }
    }

    async executeSequentially(): Promise<void> {
        const results: Promise<void>[] = [];
        
        for (const task of this.tasks) {
            results.push(task());
        }
        
        await Promise.all(results);
    }

    clearTasks(): void {
        this.tasks = [];
    }
}

// 사용 예시
const taskManager = new AsyncTaskManager();

// 비동기 작업 추가
taskManager.addTask(async () => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    console.log('작업 1 완료');
});

taskManager.addTask(async () => {
    await new Promise(resolve => setTimeout(resolve, 500));
    console.log('작업 2 완료');
});

// 순차 실행
await taskManager.executeAll();
// "작업 1 완료"
// "작업 2 완료"
```

## 운영 팁

### 성능 최적화

#### void 함수 최적화
```typescript
// void 함수의 성능 최적화
class OptimizedProcessor {
    private cache = new Map<string, any>();

    // void 함수에서 캐시 활용
    processData(key: string, data: any): void {
        if (this.cache.has(key)) {
            console.log('캐시된 데이터 사용:', key);
            return; // 조기 반환으로 성능 향상
        }
        
        // 데이터 처리
        const processedData = this.processExpensive(data);
        this.cache.set(key, processedData);
        console.log('새로운 데이터 처리 완료:', key);
    }

    private processExpensive(data: any): any {
        // 비용이 큰 처리 로직
        return data;
    }

    clearCache(): void {
        this.cache.clear();
    }
}
```

### 에러 처리

#### 안전한 void 함수 사용
```typescript
// 안전한 void 함수 처리
class SafeProcessor {
    private errorHandler: (error: Error) => void = console.error;

    setErrorHandler(handler: (error: Error) => void): void {
        this.errorHandler = handler;
    }

    safeExecute<T>(operation: () => T): T | void {
        try {
            return operation();
        } catch (error) {
            this.errorHandler(error instanceof Error ? error : new Error(String(error)));
        }
    }

    async safeExecuteAsync<T>(operation: () => Promise<T>): Promise<T | void> {
        try {
            return await operation();
        } catch (error) {
            this.errorHandler(error instanceof Error ? error : new Error(String(error)));
        }
    }
}

// 사용 예시
const processor = new SafeProcessor();

processor.safeExecute(() => {
    console.log('안전한 실행');
});

processor.safeExecute(() => {
    throw new Error('테스트 오류');
}); // 오류가 안전하게 처리됨
```

## 참고

### void 타입 특성

| 특성 | 설명 |
|------|------|
| **반환값** | 명시적인 값을 반환하지 않음 |
| **실제 반환값** | JavaScript에서는 undefined |
| **사용 목적** | 함수의 반환 타입으로 주로 사용 |
| **타입 추론** | 반환문이 없으면 자동으로 void 추론 |

### void vs undefined vs never 비교표

| 타입 | 설명 | 사용 목적 |
|------|------|-----------|
| **void** | 반환값이 없음 | 함수 반환 타입 |
| **undefined** | 정의되지 않은 값 | 변수, 선택적 속성 |
| **never** | 절대 발생하지 않음 | 예외, 무한 반복 |

### 결론
TypeScript의 void 타입은 함수가 값을 반환하지 않음을 명확히 표현합니다.
함수의 의도를 명확하게 전달하여 코드의 가독성을 향상시킵니다.
이벤트 핸들러와 콜백 함수에서 주로 사용됩니다.
void 함수에서도 return 문을 사용할 수 있지만 값을 반환하지 않습니다.
비동기 함수에서도 void를 사용하여 Promise<void>를 반환할 수 있습니다.
void 타입을 적절히 사용하여 함수의 인터페이스를 명확하게 정의하세요.

