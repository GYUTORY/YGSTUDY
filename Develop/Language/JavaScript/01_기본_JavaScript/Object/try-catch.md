---
title: JavaScript try-catch 에러 처리
tags: [language, javascript, 01기본javascript, object, try-catch, error-handling]
updated: 2025-08-10
---

# JavaScript try-catch 에러 처리

## 배경

JavaScript에서 try-catch는 예외 처리를 위한 핵심 구문입니다. 프로그램 실행 중 발생할 수 있는 오류를 안전하게 처리하고, 애플리케이션의 안정성을 보장하는 데 사용됩니다.

### try-catch의 필요성
- **오류 처리**: 예상치 못한 오류로 인한 프로그램 중단 방지
- **사용자 경험**: 오류 발생 시에도 애플리케이션이 계속 동작
- **디버깅**: 오류 정보를 수집하여 문제 해결 지원
- **리소스 정리**: finally 블록을 통한 정리 작업 보장

### 기본 개념
- **try 블록**: 오류가 발생할 수 있는 코드를 포함
- **catch 블록**: 오류가 발생했을 때 실행될 코드를 포함
- **finally 블록**: 오류 발생 여부와 관계없이 항상 실행되는 코드를 포함
- **throw**: 의도적으로 오류를 발생시키는 구문

## 핵심

### 1. 기본 문법

#### try-catch 기본 구조
```javascript
try {
    // 오류가 발생할 수 있는 코드
    const result = riskyOperation();
    console.log(result);
} catch (error) {
    // 오류 처리
    console.error('오류가 발생했습니다:', error.message);
} finally {
    // 항상 실행되는 코드 (선택사항)
    console.log('작업이 완료되었습니다.');
}
```

#### 간단한 예제
```javascript
try {
    const result = 10 / 0;
    console.log(result);
} catch (error) {
    console.log('오류가 발생했습니다:', error.message);
    // "오류가 발생했습니다: Infinity"
}
```

#### 변수 접근 오류 처리
```javascript
try {
    console.log(undefinedVariable);
} catch (error) {
    console.log('변수 오류:', error.message);
    // "변수 오류: undefinedVariable is not defined"
}
```

### 2. 에러 객체

#### 주요 에러 타입
```javascript
// 1. Error: 기본 에러 객체
throw new Error('기본 오류');

// 2. SyntaxError: 구문 오류
// throw new SyntaxError('구문 오류');

// 3. TypeError: 타입 오류
const obj = null;
obj.property; // TypeError: Cannot read property 'property' of null

// 4. ReferenceError: 참조 오류
console.log(undefinedVariable); // ReferenceError: undefinedVariable is not defined

// 5. RangeError: 범위 오류
const arr = new Array(-1); // RangeError: Invalid array length

// 6. URIError: URI 처리 오류
decodeURIComponent('%'); // URIError: URI malformed

// 7. EvalError: eval() 함수 관련 오류 (현재는 거의 사용되지 않음)
```

#### 에러 객체의 주요 속성
```javascript
try {
    throw new Error('테스트 에러');
} catch (error) {
    console.log('에러 이름:', error.name); // "Error"
    console.log('에러 메시지:', error.message); // "테스트 에러"
    console.log('스택 트레이스:', error.stack); // 호출 스택 정보
    console.log('에러 타입:', error.constructor.name); // "Error"
}
```

#### 커스텀 에러 생성
```javascript
class CustomError extends Error {
    constructor(message, code) {
        super(message);
        this.name = 'CustomError';
        this.code = code;
        this.timestamp = new Date();
    }
}

try {
    throw new CustomError('커스텀 에러 발생!', 'CUSTOM_001');
} catch (error) {
    if (error instanceof CustomError) {
        console.log('커스텀 에러 처리:', error.message);
        console.log('에러 코드:', error.code);
        console.log('발생 시간:', error.timestamp);
    } else {
        console.log('일반 에러 처리:', error.message);
    }
}
```

### 3. throw 문

#### throw new Error vs throw err
```javascript
// 1. 새로운 에러 생성
function processData(data) {
    if (!data) {
        throw new Error('데이터가 없습니다.');
    }
    return data.toUpperCase();
}

// 2. 기존 에러를 다시 던지기
function validateUser(user) {
    try {
        if (!user.name) {
            throw new Error('사용자 이름이 필요합니다.');
        }
        if (!user.email) {
            throw new Error('이메일이 필요합니다.');
        }
    } catch (error) {
        // 에러 정보를 추가하여 다시 던지기
        error.message = `사용자 검증 실패: ${error.message}`;
        throw error; // 기존 에러를 다시 던지기
    }
}

// 사용 예시
try {
    validateUser({});
} catch (error) {
    console.log(error.message); // "사용자 검증 실패: 사용자 이름이 필요합니다."
}
```

#### 조건부 에러 발생
```javascript
function divide(a, b) {
    if (typeof a !== 'number' || typeof b !== 'number') {
        throw new TypeError('두 인수 모두 숫자여야 합니다.');
    }
    
    if (b === 0) {
        throw new Error('0으로 나눌 수 없습니다.');
    }
    
    return a / b;
}

try {
    const result = divide(10, 0);
    console.log(result);
} catch (error) {
    if (error instanceof TypeError) {
        console.log('타입 오류:', error.message);
    } else {
        console.log('일반 오류:', error.message);
    }
}
```

### 4. finally 블록

#### finally 블록의 특징
```javascript
function riskyOperation() {
    let resource = null;
    
    try {
        resource = acquireResource();
        const result = processResource(resource);
        return result;
    } catch (error) {
        console.error('오류 발생:', error.message);
        throw error; // 에러를 다시 던져도 finally는 실행됨
    } finally {
        // 리소스 정리 (항상 실행됨)
        if (resource) {
            releaseResource(resource);
            console.log('리소스가 정리되었습니다.');
        }
    }
}

// 가상의 함수들
function acquireResource() {
    console.log('리소스 획득');
    return { id: 1, data: 'test' };
}

function processResource(resource) {
    // 가끔 오류 발생
    if (Math.random() > 0.5) {
        throw new Error('처리 중 오류 발생');
    }
    return `처리된 ${resource.data}`;
}

function releaseResource(resource) {
    console.log(`리소스 ${resource.id} 해제`);
}
```

#### finally와 return의 관계
```javascript
function testFinally() {
    try {
        console.log('try 블록 실행');
        return 'try에서 반환';
    } catch (error) {
        console.log('catch 블록 실행');
        return 'catch에서 반환';
    } finally {
        console.log('finally 블록 실행');
        // finally에서 return하면 try/catch의 return을 덮어씀
        // return 'finally에서 반환';
    }
}

console.log(testFinally());
// 출력:
// "try 블록 실행"
// "finally 블록 실행"
// "try에서 반환"
```

### 5. 중첩된 try-catch

#### 중첩 구조
```javascript
function outerFunction() {
    try {
        console.log('외부 함수 시작');
        innerFunction();
    } catch (error) {
        console.log('외부 함수에서 오류 처리:', error.message);
    }
}

function innerFunction() {
    try {
        console.log('내부 함수 시작');
        riskyOperation();
    } catch (error) {
        console.log('내부 함수에서 오류 처리:', error.message);
        // 내부에서 처리하지 않고 외부로 전파
        throw error;
    }
}

function riskyOperation() {
    throw new Error('위험한 작업에서 오류 발생');
}

outerFunction();
```

#### 특정 오류만 처리
```javascript
function processUserData(userData) {
    try {
        // 데이터 파싱
        const parsedData = JSON.parse(userData);
        
        try {
            // 데이터 검증
            validateUserData(parsedData);
        } catch (validationError) {
            console.log('검증 오류:', validationError.message);
            // 검증 오류는 복구 가능하므로 기본값 사용
            return getDefaultUserData();
        }
        
        return parsedData;
    } catch (parseError) {
        console.log('파싱 오류:', parseError.message);
        // 파싱 오류는 복구 불가능하므로 에러 전파
        throw new Error('사용자 데이터를 처리할 수 없습니다.');
    }
}

function validateUserData(data) {
    if (!data.name || !data.email) {
        throw new Error('필수 필드가 누락되었습니다.');
    }
}

function getDefaultUserData() {
    return { name: 'Unknown', email: 'unknown@example.com' };
}
```

## 예시

### 1. 실제 사용 사례

#### API 호출 에러 처리
```javascript
async function fetchUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const userData = await response.json();
        return userData;
    } catch (error) {
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('네트워크 오류:', error.message);
            throw new Error('서버에 연결할 수 없습니다.');
        } else if (error.message.includes('HTTP 404')) {
            console.error('사용자를 찾을 수 없습니다.');
            throw new Error('존재하지 않는 사용자입니다.');
        } else {
            console.error('알 수 없는 오류:', error.message);
            throw new Error('사용자 정보를 가져오는 중 오류가 발생했습니다.');
        }
    }
}

// 사용 예시
fetchUserData(123)
    .then(user => console.log('사용자 정보:', user))
    .catch(error => console.error('오류:', error.message));
```

#### 파일 처리 에러 처리
```javascript
function readFileContent(filePath) {
    let fileHandle = null;
    
    try {
        // 파일 열기 시도
        fileHandle = openFile(filePath);
        
        if (!fileHandle) {
            throw new Error('파일을 열 수 없습니다.');
        }
        
        const content = readFromHandle(fileHandle);
        return content;
    } catch (error) {
        if (error.message.includes('파일을 찾을 수 없습니다')) {
            console.error('파일이 존재하지 않습니다:', filePath);
            throw new Error(`파일을 찾을 수 없습니다: ${filePath}`);
        } else if (error.message.includes('권한이 없습니다')) {
            console.error('파일 접근 권한이 없습니다:', filePath);
            throw new Error('파일 접근 권한이 없습니다.');
        } else {
            console.error('파일 읽기 오류:', error.message);
            throw new Error('파일을 읽는 중 오류가 발생했습니다.');
        }
    } finally {
        // 파일 핸들 정리
        if (fileHandle) {
            closeFile(fileHandle);
            console.log('파일이 닫혔습니다.');
        }
    }
}

// 가상의 파일 처리 함수들
function openFile(path) {
    if (path.includes('nonexistent')) {
        throw new Error('파일을 찾을 수 없습니다.');
    }
    if (path.includes('restricted')) {
        throw new Error('권한이 없습니다.');
    }
    return { path, isOpen: true };
}

function readFromHandle(handle) {
    return `파일 내용: ${handle.path}`;
}

function closeFile(handle) {
    handle.isOpen = false;
}
```

### 2. 고급 패턴

#### 에러 래핑 패턴
```javascript
class DatabaseError extends Error {
    constructor(message, originalError, query) {
        super(message);
        this.name = 'DatabaseError';
        this.originalError = originalError;
        this.query = query;
        this.timestamp = new Date();
    }
}

class ValidationError extends Error {
    constructor(message, field, value) {
        super(message);
        this.name = 'ValidationError';
        this.field = field;
        this.value = value;
    }
}

function executeQuery(query) {
    try {
        // 데이터베이스 쿼리 실행
        const result = performDatabaseQuery(query);
        return result;
    } catch (error) {
        // 데이터베이스 오류를 래핑
        throw new DatabaseError(
            '데이터베이스 쿼리 실행 중 오류가 발생했습니다.',
            error,
            query
        );
    }
}

function validateUser(user) {
    const errors = [];
    
    if (!user.name || user.name.trim().length === 0) {
        errors.push(new ValidationError('이름은 필수입니다.', 'name', user.name));
    }
    
    if (!user.email || !user.email.includes('@')) {
        errors.push(new ValidationError('유효한 이메일이 필요합니다.', 'email', user.email));
    }
    
    if (errors.length > 0) {
        const errorMessage = errors.map(e => e.message).join(', ');
        const combinedError = new Error(errorMessage);
        combinedError.errors = errors;
        throw combinedError;
    }
}

// 사용 예시
try {
    const user = { name: '', email: 'invalid-email' };
    validateUser(user);
    
    const query = 'SELECT * FROM users WHERE id = 1';
    const result = executeQuery(query);
    console.log('결과:', result);
} catch (error) {
    if (error instanceof DatabaseError) {
        console.error('데이터베이스 오류:', error.message);
        console.error('원본 오류:', error.originalError.message);
        console.error('쿼리:', error.query);
    } else if (error.errors) {
        console.error('검증 오류들:');
        error.errors.forEach(err => {
            console.error(`- ${err.field}: ${err.message} (값: ${err.value})`);
        });
    } else {
        console.error('일반 오류:', error.message);
    }
}
```

#### 비동기 에러 처리
```javascript
// Promise 기반 에러 처리
function asyncOperation() {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            const random = Math.random();
            if (random > 0.7) {
                reject(new Error('비동기 작업 실패'));
            } else {
                resolve('비동기 작업 성공');
            }
        }, 1000);
    });
}

// async/await와 try-catch 사용
async function handleAsyncOperation() {
    try {
        const result = await asyncOperation();
        console.log('성공:', result);
        return result;
    } catch (error) {
        console.error('비동기 오류:', error.message);
        throw error;
    }
}

// Promise 체인에서 에러 처리
asyncOperation()
    .then(result => {
        console.log('성공:', result);
        return result;
    })
    .catch(error => {
        console.error('오류:', error.message);
        // 기본값 반환
        return '기본값';
    })
    .then(finalResult => {
        console.log('최종 결과:', finalResult);
    });

// 여러 비동기 작업의 에러 처리
async function processMultipleOperations() {
    const operations = [
        asyncOperation(),
        asyncOperation(),
        asyncOperation()
    ];
    
    try {
        const results = await Promise.all(operations);
        console.log('모든 작업 성공:', results);
        return results;
    } catch (error) {
        console.error('일부 작업 실패:', error.message);
        // 실패한 작업들을 개별적으로 처리
        const results = await Promise.allSettled(operations);
        const successful = results.filter(r => r.status === 'fulfilled');
        const failed = results.filter(r => r.status === 'rejected');
        
        console.log('성공한 작업:', successful.length);
        console.log('실패한 작업:', failed.length);
        
        return successful.map(r => r.value);
    }
}
```

## 운영 팁

### 성능 최적화

#### 에러 처리 성능 고려사항
```javascript
// 비효율적인 방법: try-catch를 너무 자주 사용
function inefficientFunction() {
    try {
        const result = simpleOperation();
        return result;
    } catch (error) {
        // 단순한 연산에서 오류가 발생할 가능성이 낮음
        console.error(error);
        return null;
    }
}

// 효율적인 방법: 예측 가능한 오류만 처리
function efficientFunction() {
    const result = simpleOperation();
    return result;
}

// 예측 가능한 오류가 있는 경우에만 try-catch 사용
function riskyFunction(data) {
    try {
        return JSON.parse(data);
    } catch (error) {
        // JSON 파싱은 실패할 가능성이 있음
        console.error('JSON 파싱 오류:', error.message);
        return null;
    }
}
```

### 에러 처리

#### 일반적인 에러 처리 패턴
```javascript
// 1. 오류 로깅
function logError(error, context = {}) {
    console.error('오류 발생:', {
        message: error.message,
        name: error.name,
        stack: error.stack,
        timestamp: new Date().toISOString(),
        context: context
    });
}

// 2. 오류 복구
function recoverFromError(error) {
    if (error instanceof NetworkError) {
        return retryOperation();
    } else if (error instanceof ValidationError) {
        return useDefaultValue();
    } else {
        throw error; // 복구 불가능한 오류는 다시 던지기
    }
}

// 3. 사용자 친화적 오류 메시지
function getUserFriendlyMessage(error) {
    const errorMessages = {
        'NetworkError': '네트워크 연결을 확인해주세요.',
        'ValidationError': '입력한 정보를 다시 확인해주세요.',
        'PermissionError': '권한이 없습니다. 관리자에게 문의하세요.',
        'default': '오류가 발생했습니다. 다시 시도해주세요.'
    };
    
    return errorMessages[error.name] || errorMessages.default;
}

// 사용 예시
try {
    const result = riskyOperation();
    console.log('결과:', result);
} catch (error) {
    logError(error, { operation: 'riskyOperation' });
    
    try {
        const recovered = recoverFromError(error);
        console.log('복구된 결과:', recovered);
    } catch (recoveryError) {
        const message = getUserFriendlyMessage(recoveryError);
        console.error('사용자 메시지:', message);
    }
}
```

## 참고

### 에러 타입별 처리 방법

| 에러 타입 | 발생 원인 | 처리 방법 |
|-----------|-----------|-----------|
| **SyntaxError** | 구문 오류 | 코드 수정 필요 |
| **TypeError** | 타입 불일치 | 타입 검증 추가 |
| **ReferenceError** | 변수 미정의 | 변수 선언 확인 |
| **RangeError** | 범위 초과 | 입력값 검증 |
| **URIError** | URI 형식 오류 | URI 인코딩 확인 |
| **NetworkError** | 네트워크 오류 | 재시도 로직 |
| **ValidationError** | 데이터 검증 실패 | 기본값 사용 |

### try-catch 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **외부 API 호출** | 항상 사용 | 네트워크 오류 가능성 |
| **파일/데이터베이스 작업** | 항상 사용 | 리소스 오류 가능성 |
| **사용자 입력 처리** | 권장 | 예상치 못한 입력 |
| **단순한 연산** | 불필요 | 오류 발생 가능성 낮음 |
| **성능이 중요한 부분** | 최소화 | 오버헤드 발생 |

### 결론
try-catch는 JavaScript에서 예외 처리를 위한 핵심 구문입니다.
적절한 에러 타입을 사용하여 구체적인 오류 정보를 제공하세요.
finally 블록을 활용하여 리소스 정리를 보장하세요.
중첩된 try-catch를 사용하여 세분화된 오류 처리를 구현하세요.
비동기 작업에서는 async/await와 함께 사용하여 깔끔한 에러 처리를 하세요.
오류 로깅과 사용자 친화적 메시지를 제공하여 디버깅과 사용자 경험을 개선하세요.

