---
title: TypeScript never 타입 완벽 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, other-types, never]
updated: 2025-08-10
---

# TypeScript never 타입 완벽 가이드

## 배경

TypeScript에서 `never` 타입은 절대로 발생하지 않는 값의 타입을 나타냅니다.

### never 타입의 필요성
- **타입 시스템 완성성**: 타입 시스템의 논리적 완성성 유지
- **예외 처리**: 함수가 예외를 던지거나 프로그램이 중단되는 경우
- **무한 반복**: 함수가 끝나지 않고 계속 반복되는 경우
- **타입 가드**: 모든 경우를 처리했을 때 남은 경우 처리

### 기본 개념
- **절대 발생하지 않음**: 해당 코드 블록이 실행되면 함수가 더 이상 진행되지 않음
- **타입 안전성**: 타입 시스템에서 논리적으로 불가능한 상황 표현
- **완전성 검사**: 모든 경우를 처리했는지 컴파일 타임에 확인

## 핵심

### 1. never 타입의 기본 사용법

#### 예외를 던지는 함수
```typescript
// 예외를 던지는 함수
function throwError(message: string): never {
    throw new Error(message);
}

// 사용 예시
function processData(data: string): string {
    if (!data) {
        throwError('데이터가 없습니다.'); // never 반환
    }
    return data.toUpperCase();
}

// 함수 호출
try {
    const result = processData('');
} catch (error) {
    console.error(error.message); // "데이터가 없습니다."
}
```

#### 무한 반복 함수
```typescript
// 무한 반복 함수
function infiniteLoop(): never {
    while (true) {
        console.log('무한 반복 중...');
        // 실제로는 break 조건이 있어야 함
    }
}

// 실제 사용 예시
function processQueue(): never {
    while (true) {
        const task = getNextTask();
        if (task) {
            executeTask(task);
        } else {
            // 작업이 없으면 잠시 대기
            sleep(1000);
        }
    }
}

function getNextTask(): any {
    // 작업 큐에서 다음 작업 가져오기
    return null;
}

function executeTask(task: any): void {
    // 작업 실행
    console.log('작업 실행:', task);
}

function sleep(ms: number): void {
    // 대기 함수
    const start = Date.now();
    while (Date.now() - start < ms) {}
}
```

### 2. never 타입과 타입 가드

#### 완전성 검사 (Exhaustive Check)
```typescript
// 유니온 타입 정의
type Status = 'loading' | 'success' | 'error';

function handleStatus(status: Status): string {
    switch (status) {
        case 'loading':
            return '로딩 중...';
        case 'success':
            return '성공!';
        case 'error':
            return '오류 발생';
        default:
            // 모든 경우를 처리했으므로 이 코드는 실행되지 않아야 함
            const exhaustiveCheck: never = status;
            throw new Error(`처리되지 않은 상태: ${exhaustiveCheck}`);
    }
}

// 사용 예시
console.log(handleStatus('loading')); // "로딩 중..."
console.log(handleStatus('success')); // "성공!"
console.log(handleStatus('error'));   // "오류 발생"
```

#### 타입 가드와 never
```typescript
function processValue(value: string | number | boolean): string {
    if (typeof value === 'string') {
        return `문자열: ${value}`;
    } else if (typeof value === 'number') {
        return `숫자: ${value}`;
    } else if (typeof value === 'boolean') {
        return `불린: ${value}`;
    } else {
        // 모든 타입을 처리했으므로 이 코드는 실행되지 않아야 함
        const exhaustiveCheck: never = value;
        throw new Error(`처리되지 않은 타입: ${exhaustiveCheck}`);
    }
}

// 사용 예시
console.log(processValue('hello'));   // "문자열: hello"
console.log(processValue(42));        // "숫자: 42"
console.log(processValue(true));      // "불린: true"
```

### 3. never 타입의 고급 패턴

#### 조건부 타입에서의 never
```typescript
// 조건부 타입에서 never 사용
type NonNullable<T> = T extends null | undefined ? never : T;

// 사용 예시
type StringOrNull = string | null;
type NonNullString = NonNullable<StringOrNull>; // string

// 실제 사용
function processNonNullValue<T>(value: NonNullable<T>): void {
    console.log('처리 중:', value);
}

// processNonNullValue(null); // 컴파일 오류
processNonNullValue('hello'); // 정상 실행
```

#### 유니온 타입에서 never 제거
```typescript
// never를 유니온에서 제거하는 유틸리티 타입
type RemoveNever<T> = T extends never ? never : T;

// 또는 더 정확한 방법
type ExcludeNever<T> = T extends never ? never : T;

// 사용 예시
type UnionWithNever = string | number | never | boolean;
type CleanUnion = ExcludeNever<UnionWithNever>; // string | number | boolean
```

## 예시

### 1. 실제 사용 사례

#### API 응답 처리
```typescript
type ApiResponse<T> = 
    | { status: 'loading' }
    | { status: 'success'; data: T }
    | { status: 'error'; error: string };

function handleApiResponse<T>(response: ApiResponse<T>): string {
    switch (response.status) {
        case 'loading':
            return '로딩 중...';
        case 'success':
            return `성공: ${JSON.stringify(response.data)}`;
        case 'error':
            return `오류: ${response.error}`;
        default:
            // 모든 경우를 처리했으므로 이 코드는 실행되지 않아야 함
            const exhaustiveCheck: never = response;
            throw new Error(`처리되지 않은 응답 상태: ${exhaustiveCheck}`);
    }
}

// 사용 예시
const loadingResponse: ApiResponse<string> = { status: 'loading' };
const successResponse: ApiResponse<string> = { status: 'success', data: 'Hello World' };
const errorResponse: ApiResponse<string> = { status: 'error', error: 'Network Error' };

console.log(handleApiResponse(loadingResponse)); // "로딩 중..."
console.log(handleApiResponse(successResponse)); // "성공: \"Hello World\""
console.log(handleApiResponse(errorResponse));   // "오류: Network Error"
```

#### 이벤트 시스템
```typescript
type EventType = 'click' | 'hover' | 'focus' | 'blur';

interface ClickEvent {
    type: 'click';
    x: number;
    y: number;
}

interface HoverEvent {
    type: 'hover';
    element: string;
}

interface FocusEvent {
    type: 'focus';
    element: string;
}

interface BlurEvent {
    type: 'blur';
    element: string;
}

type Event = ClickEvent | HoverEvent | FocusEvent | BlurEvent;

function handleEvent(event: Event): void {
    switch (event.type) {
        case 'click':
            console.log(`클릭 위치: (${event.x}, ${event.y})`);
            break;
        case 'hover':
            console.log(`호버 요소: ${event.element}`);
            break;
        case 'focus':
            console.log(`포커스 요소: ${event.element}`);
            break;
        case 'blur':
            console.log(`블러 요소: ${event.element}`);
            break;
        default:
            // 모든 이벤트 타입을 처리했으므로 이 코드는 실행되지 않아야 함
            const exhaustiveCheck: never = event;
            throw new Error(`처리되지 않은 이벤트 타입: ${exhaustiveCheck}`);
    }
}

// 사용 예시
const clickEvent: ClickEvent = { type: 'click', x: 100, y: 200 };
const hoverEvent: HoverEvent = { type: 'hover', element: 'button' };

handleEvent(clickEvent); // "클릭 위치: (100, 200)"
handleEvent(hoverEvent); // "호버 요소: button"
```

### 2. 고급 패턴

#### 타입 안전한 상태 머신
```typescript
type State = 'idle' | 'loading' | 'success' | 'error';

interface StateMachine {
    state: State;
    data?: any;
    error?: string;
}

function transitionState(machine: StateMachine, newState: State): StateMachine {
    switch (machine.state) {
        case 'idle':
            if (newState === 'loading') {
                return { state: 'loading' };
            }
            break;
        case 'loading':
            if (newState === 'success' || newState === 'error') {
                return { state: newState };
            }
            break;
        case 'success':
        case 'error':
            if (newState === 'idle') {
                return { state: 'idle' };
            }
            break;
        default:
            const exhaustiveCheck: never = machine.state;
            throw new Error(`처리되지 않은 상태: ${exhaustiveCheck}`);
    }
    
    throw new Error(`잘못된 상태 전환: ${machine.state} -> ${newState}`);
}

// 사용 예시
let machine: StateMachine = { state: 'idle' };

try {
    machine = transitionState(machine, 'loading');
    console.log('상태:', machine.state); // "상태: loading"
    
    machine = transitionState(machine, 'success');
    console.log('상태:', machine.state); // "상태: success"
    
    machine = transitionState(machine, 'idle');
    console.log('상태:', machine.state); // "상태: idle"
} catch (error) {
    console.error('상태 전환 오류:', error.message);
}
```

#### 함수 오버로드와 never
```typescript
// 함수 오버로드 정의
function processData(data: string): string;
function processData(data: number): number;
function processData(data: boolean): never; // boolean은 처리하지 않음

// 실제 구현
function processData(data: string | number | boolean): string | number | never {
    if (typeof data === 'string') {
        return data.toUpperCase();
    } else if (typeof data === 'number') {
        return data * 2;
    } else {
        // boolean 타입은 처리하지 않으므로 never 반환
        throw new Error('boolean 타입은 지원하지 않습니다.');
    }
}

// 사용 예시
console.log(processData('hello')); // "HELLO"
console.log(processData(5));       // 10
// processData(true);              // 컴파일 오류
```

## 운영 팁

### 성능 최적화

#### never 타입과 최적화
```typescript
// never 타입을 사용한 최적화된 타입 가드
function isString(value: unknown): value is string {
    return typeof value === 'string';
}

function isNumber(value: unknown): value is number {
    return typeof value === 'number';
}

function processOptimized(value: unknown): string {
    if (isString(value)) {
        return value.toUpperCase();
    } else if (isNumber(value)) {
        return value.toString();
    } else {
        // 모든 타입을 처리했으므로 이 코드는 실행되지 않아야 함
        const exhaustiveCheck: never = value;
        throw new Error(`처리되지 않은 타입: ${exhaustiveCheck}`);
    }
}
```

### 에러 처리

#### 안전한 never 타입 사용
```typescript
// 안전한 예외 처리 함수
function safeThrowError(message: string): never {
    console.error('오류 발생:', message);
    throw new Error(message);
}

// 타입 안전한 완전성 검사
function exhaustiveCheck(value: never): never {
    throw new Error(`처리되지 않은 값: ${value}`);
}

// 사용 예시
function processStatus(status: 'active' | 'inactive'): string {
    switch (status) {
        case 'active':
            return '활성';
        case 'inactive':
            return '비활성';
        default:
            return exhaustiveCheck(status); // 컴파일 타임에 완전성 검사
    }
}
```

## 참고

### never 타입 특성

| 특성 | 설명 |
|------|------|
| **절대 발생하지 않음** | 해당 값이 절대 발생할 수 없음을 나타냄 |
| **타입 시스템 완성성** | 타입 시스템의 논리적 완성성 유지 |
| **완전성 검사** | 모든 경우를 처리했는지 컴파일 타임에 확인 |
| **예외 처리** | 함수가 예외를 던지거나 프로그램이 중단되는 경우 |

### never vs void vs undefined 비교표

| 타입 | 의미 | 사용 목적 |
|------|------|-----------|
| **never** | 절대 발생하지 않는 값 | 예외, 무한 반복, 완전성 검사 |
| **void** | 반환값이 없음 | 일반적인 함수 반환 |
| **undefined** | 정의되지 않은 값 | 선택적 속성, 초기화되지 않은 변수 |

### 결론
TypeScript의 never 타입은 타입 시스템의 논리적 완성성을 유지하는 중요한 도구입니다.
예외 처리, 무한 반복, 완전성 검사 등 특정 상황에서 사용됩니다.
완전성 검사를 통해 모든 경우를 처리했는지 컴파일 타임에 확인할 수 있습니다.
never 타입을 적절히 사용하여 타입 안전성을 향상시키세요.
조건부 타입과 함께 사용하여 더욱 정교한 타입 시스템을 구축하세요.
never 타입의 특성을 이해하고 적절한 상황에서 활용하세요.

