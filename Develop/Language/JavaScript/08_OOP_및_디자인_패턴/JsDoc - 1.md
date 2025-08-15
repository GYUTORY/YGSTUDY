---
title: JSDoc 완벽 가이드
tags: [language, javascript, 08oop및디자인패턴, jsdoc, documentation]
updated: 2025-08-10
---

# JSDoc 완벽 가이드

## 배경

JSDoc은 JavaScript 코드에 특별한 형태의 주석을 추가하여 코드의 구조와 기능을 문서화하는 표준 방식입니다.

### JSDoc의 필요성
- **코드 가독성 향상**: 함수와 클래스의 목적과 사용법을 명확히 문서화
- **IDE 지원**: 자동완성과 타입 힌트 제공
- **API 문서 자동 생성**: 코드에서 직접 문서 생성
- **팀 협업 개선**: 코드 이해도와 유지보수성 향상

### JSDoc 주석 형식
```javascript
/**
 * 함수나 클래스에 대한 설명
 * @param {타입} 매개변수명 - 매개변수 설명
 * @returns {타입} 반환값 설명
 */
```

## 핵심

### 1. 기본 태그들

#### @param - 매개변수 문서화
```javascript
/**
 * 두 숫자를 더하는 함수
 * @param {number} a - 첫 번째 숫자
 * @param {number} b - 두 번째 숫자
 * @returns {number} 두 숫자의 합계
 */
function add(a, b) {
    return a + b;
}

/**
 * 사용자 정보를 출력하는 함수
 * @param {Object} user - 사용자 객체
 * @param {string} user.name - 사용자 이름
 * @param {number} user.age - 사용자 나이
 * @param {string} [user.email] - 사용자 이메일 (선택사항)
 */
function printUserInfo(user) {
    console.log(`이름: ${user.name}, 나이: ${user.age}`);
    if (user.email) {
        console.log(`이메일: ${user.email}`);
    }
}
```

#### @returns - 반환값 문서화
```javascript
/**
 * 문자열을 대문자로 변환하는 함수
 * @param {string} str - 변환할 문자열
 * @returns {string} 대문자로 변환된 문자열
 */
function toUpperCase(str) {
    return str.toUpperCase();
}

/**
 * 배열에서 최대값을 찾는 함수
 * @param {number[]} numbers - 숫자 배열
 * @returns {number|null} 최대값, 배열이 비어있으면 null
 */
function findMax(numbers) {
    if (numbers.length === 0) return null;
    return Math.max(...numbers);
}
```

#### @type - 타입 정의
```javascript
/**
 * @type {string}
 */
let userName = '홍길동';

/**
 * @type {number[]}
 */
const scores = [85, 92, 78, 96];

/**
 * @type {{name: string, age: number, email?: string}}
 */
const user = {
    name: '김철수',
    age: 25
};
```

### 2. 고급 태그들

#### @typedef - 커스텀 타입 정의
```javascript
/**
 * 사용자 정보 타입
 * @typedef {Object} User
 * @property {string} name - 사용자 이름
 * @property {number} age - 사용자 나이
 * @property {string} [email] - 사용자 이메일 (선택사항)
 * @property {string[]} [hobbies] - 사용자 취미 목록
 */

/**
 * 사용자 정보를 생성하는 함수
 * @param {string} name - 사용자 이름
 * @param {number} age - 사용자 나이
 * @returns {User} 생성된 사용자 객체
 */
function createUser(name, age) {
    return { name, age };
}
```

#### @template - 제네릭 타입
```javascript
/**
 * 배열의 첫 번째 요소를 반환하는 함수
 * @template T
 * @param {T[]} array - 배열
 * @returns {T|undefined} 첫 번째 요소 또는 undefined
 */
function getFirst(array) {
    return array[0];
}

/**
 * 두 값을 비교하는 함수
 * @template T
 * @param {T} a - 첫 번째 값
 * @param {T} b - 두 번째 값
 * @returns {boolean} 두 값이 같은지 여부
 */
function isEqual(a, b) {
    return a === b;
}
```

#### @throws - 예외 문서화
```javascript
/**
 * 숫자를 나누는 함수
 * @param {number} a - 피제수
 * @param {number} b - 제수
 * @returns {number} 나눗셈 결과
 * @throws {Error} 제수가 0일 때 에러 발생
 */
function divide(a, b) {
    if (b === 0) {
        throw new Error('0으로 나눌 수 없습니다.');
    }
    return a / b;
}
```

### 3. 클래스와 메서드 문서화

#### 클래스 문서화
```javascript
/**
 * 사용자 클래스
 * @class
 * @classdesc 사용자 정보를 관리하는 클래스
 */
class User {
    /**
     * 사용자 객체 생성
     * @param {string} name - 사용자 이름
     * @param {number} age - 사용자 나이
     * @param {string} [email] - 사용자 이메일
     */
    constructor(name, age, email) {
        this.name = name;
        this.age = age;
        this.email = email;
    }

    /**
     * 사용자 정보를 문자열로 반환
     * @returns {string} 사용자 정보 문자열
     */
    toString() {
        return `${this.name} (${this.age}세)`;
    }

    /**
     * 사용자가 성인인지 확인
     * @returns {boolean} 성인 여부
     */
    isAdult() {
        return this.age >= 20;
    }

    /**
     * 사용자 정보를 업데이트
     * @param {Object} updates - 업데이트할 정보
     * @param {string} [updates.name] - 새로운 이름
     * @param {number} [updates.age] - 새로운 나이
     * @param {string} [updates.email] - 새로운 이메일
     */
    update(updates) {
        Object.assign(this, updates);
    }
}
```

#### 정적 메서드 문서화
```javascript
/**
 * 유틸리티 클래스
 */
class Utils {
    /**
     * 두 숫자의 최대공약수를 계산
     * @param {number} a - 첫 번째 숫자
     * @param {number} b - 두 번째 숫자
     * @returns {number} 최대공약수
     */
    static gcd(a, b) {
        return b === 0 ? a : Utils.gcd(b, a % b);
    }

    /**
     * 배열을 섞는 함수
     * @template T
     * @param {T[]} array - 섞을 배열
     * @returns {T[]} 섞인 배열
     */
    static shuffle(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }
}
```

## 예시

### 1. 실제 사용 사례

#### API 클라이언트 문서화
```javascript
/**
 * HTTP API 클라이언트
 * @class
 */
class ApiClient {
    /**
     * API 클라이언트 생성
     * @param {string} baseUrl - 기본 URL
     * @param {Object} [options] - 옵션 객체
     * @param {number} [options.timeout=5000] - 타임아웃 (밀리초)
     * @param {Object} [options.headers] - 기본 헤더
     */
    constructor(baseUrl, options = {}) {
        this.baseUrl = baseUrl;
        this.timeout = options.timeout || 5000;
        this.headers = options.headers || {};
    }

    /**
     * GET 요청 수행
     * @param {string} endpoint - 엔드포인트
     * @param {Object} [params] - 쿼리 파라미터
     * @returns {Promise<Object>} 응답 데이터
     * @throws {Error} 네트워크 에러 또는 HTTP 에러
     */
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, this.baseUrl);
        Object.keys(params).forEach(key => 
            url.searchParams.append(key, params[key])
        );

        const response = await fetch(url, {
            method: 'GET',
            headers: this.headers,
            signal: AbortSignal.timeout(this.timeout)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * POST 요청 수행
     * @param {string} endpoint - 엔드포인트
     * @param {Object} data - 전송할 데이터
     * @returns {Promise<Object>} 응답 데이터
     */
    async post(endpoint, data) {
        const response = await fetch(new URL(endpoint, this.baseUrl), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...this.headers
            },
            body: JSON.stringify(data),
            signal: AbortSignal.timeout(this.timeout)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }
}
```

#### 데이터베이스 모델 문서화
```javascript
/**
 * 사용자 모델
 * @typedef {Object} UserModel
 * @property {string} id - 사용자 ID
 * @property {string} name - 사용자 이름
 * @property {string} email - 사용자 이메일
 * @property {Date} createdAt - 생성일
 * @property {Date} updatedAt - 수정일
 */

/**
 * 데이터베이스 관리자
 * @class
 */
class DatabaseManager {
    /**
     * 사용자 목록 조회
     * @param {Object} [filters] - 필터 조건
     * @param {string} [filters.name] - 이름으로 필터링
     * @param {number} [filters.minAge] - 최소 나이
     * @param {number} [filters.maxAge] - 최대 나이
     * @param {number} [limit=10] - 조회할 개수
     * @param {number} [offset=0] - 시작 위치
     * @returns {Promise<UserModel[]>} 사용자 목록
     */
    async getUsers(filters = {}, limit = 10, offset = 0) {
        // 실제 구현...
        return [];
    }

    /**
     * 사용자 생성
     * @param {Object} userData - 사용자 데이터
     * @param {string} userData.name - 사용자 이름
     * @param {string} userData.email - 사용자 이메일
     * @returns {Promise<UserModel>} 생성된 사용자
     * @throws {Error} 이메일 중복 시 에러
     */
    async createUser(userData) {
        // 실제 구현...
        return {
            id: '1',
            ...userData,
            createdAt: new Date(),
            updatedAt: new Date()
        };
    }

    /**
     * 사용자 정보 업데이트
     * @param {string} userId - 사용자 ID
     * @param {Object} updates - 업데이트할 정보
     * @returns {Promise<UserModel>} 업데이트된 사용자
     * @throws {Error} 사용자를 찾을 수 없을 때 에러
     */
    async updateUser(userId, updates) {
        // 실제 구현...
        return {
            id: userId,
            ...updates,
            updatedAt: new Date()
        };
    }
}
```

### 2. 고급 활용 패턴

#### 이벤트 시스템 문서화
```javascript
/**
 * 이벤트 리스너 함수 타입
 * @callback EventListener
 * @param {Event} event - 이벤트 객체
 * @param {*} data - 이벤트 데이터
 */

/**
 * 이벤트 에미터
 * @class
 */
class EventEmitter {
    constructor() {
        /** @type {Map<string, EventListener[]>} */
        this.listeners = new Map();
    }

    /**
     * 이벤트 리스너 등록
     * @param {string} eventName - 이벤트 이름
     * @param {EventListener} listener - 리스너 함수
     * @returns {Function} 리스너 제거 함수
     */
    on(eventName, listener) {
        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, []);
        }
        this.listeners.get(eventName).push(listener);

        // 리스너 제거 함수 반환
        return () => this.off(eventName, listener);
    }

    /**
     * 이벤트 리스너 제거
     * @param {string} eventName - 이벤트 이름
     * @param {EventListener} listener - 제거할 리스너
     */
    off(eventName, listener) {
        const listeners = this.listeners.get(eventName);
        if (listeners) {
            const index = listeners.indexOf(listener);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    /**
     * 이벤트 발생
     * @param {string} eventName - 이벤트 이름
     * @param {*} data - 이벤트 데이터
     */
    emit(eventName, data) {
        const listeners = this.listeners.get(eventName);
        if (listeners) {
            listeners.forEach(listener => {
                try {
                    listener({ name: eventName, data });
                } catch (error) {
                    console.error('이벤트 리스너 에러:', error);
                }
            });
        }
    }
}
```

#### 플러그인 시스템 문서화
```javascript
/**
 * 플러그인 인터페이스
 * @interface
 */
class Plugin {
    /**
     * 플러그인 초기화
     * @param {Object} context - 플러그인 컨텍스트
     * @returns {Promise<void>}
     */
    async init(context) {
        throw new Error('init 메서드를 구현해야 합니다.');
    }

    /**
     * 플러그인 실행
     * @param {*} data - 처리할 데이터
     * @returns {*} 처리된 데이터
     */
    execute(data) {
        throw new Error('execute 메서드를 구현해야 합니다.');
    }

    /**
     * 플러그인 정리
     * @returns {Promise<void>}
     */
    async cleanup() {
        throw new Error('cleanup 메서드를 구현해야 합니다.');
    }
}

/**
 * 플러그인 매니저
 * @class
 */
class PluginManager {
    constructor() {
        /** @type {Map<string, Plugin>} */
        this.plugins = new Map();
    }

    /**
     * 플러그인 등록
     * @param {string} name - 플러그인 이름
     * @param {Plugin} plugin - 플러그인 인스턴스
     */
    register(name, plugin) {
        this.plugins.set(name, plugin);
    }

    /**
     * 플러그인 실행
     * @param {string} name - 플러그인 이름
     * @param {*} data - 처리할 데이터
     * @returns {*} 처리된 데이터
     * @throws {Error} 플러그인을 찾을 수 없을 때 에러
     */
    execute(name, data) {
        const plugin = this.plugins.get(name);
        if (!plugin) {
            throw new Error(`플러그인 '${name}'을 찾을 수 없습니다.`);
        }
        return plugin.execute(data);
    }
}
```

## 운영 팁

### 문서화 모범 사례

#### 일관된 문서화 스타일
```javascript
/**
 * 사용자 정보를 처리하는 유틸리티 함수들
 * @namespace UserUtils
 */
const UserUtils = {
    /**
     * 사용자 이름을 검증
     * @param {string} name - 검증할 이름
     * @returns {boolean} 유효한 이름인지 여부
     * @example
     * const isValid = UserUtils.validateName('홍길동');
     * console.log(isValid); // true
     */
    validateName(name) {
        return typeof name === 'string' && name.length >= 2 && name.length <= 50;
    },

    /**
     * 이메일 주소를 검증
     * @param {string} email - 검증할 이메일
     * @returns {boolean} 유효한 이메일인지 여부
     * @example
     * const isValid = UserUtils.validateEmail('user@example.com');
     * console.log(isValid); // true
     */
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
};
```

#### 타입 안전성 확보
```javascript
/**
 * API 응답 타입
 * @template T
 * @typedef {Object} ApiResponse
 * @property {boolean} success - 성공 여부
 * @property {T} [data] - 응답 데이터 (성공 시)
 * @property {string} [error] - 에러 메시지 (실패 시)
 */

/**
 * 사용자 목록 조회 API
 * @returns {Promise<ApiResponse<UserModel[]>>} 사용자 목록 응답
 */
async function fetchUsers() {
    try {
        const response = await fetch('/api/users');
        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 자동화 도구

#### JSDoc 설정 파일
```javascript
// jsdoc.config.js
module.exports = {
    source: {
        include: ['src'],
        exclude: ['node_modules', 'dist']
    },
    opts: {
        destination: './docs',
        template: 'node_modules/docdash',
        readme: './README.md'
    },
    plugins: [
        'plugins/markdown'
    ],
    templates: {
        cleverLinks: true,
        monospaceLinks: true
    }
};
```

#### ESLint JSDoc 규칙
```javascript
// .eslintrc.js
module.exports = {
    plugins: ['jsdoc'],
    extends: [
        'plugin:jsdoc/recommended'
    ],
    rules: {
        'jsdoc/require-jsdoc': [
            'error',
            {
                publicOnly: true,
                require: {
                    FunctionDeclaration: true,
                    MethodDefinition: true,
                    ClassDeclaration: true
                }
            }
        ],
        'jsdoc/require-param-type': 'error',
        'jsdoc/require-returns-type': 'error'
    }
};
```

## 참고

### JSDoc 태그 참조

#### 주요 태그 목록
```javascript
/**
 * @param {string} name - 매개변수 설명
 * @returns {number} 반환값 설명
 * @throws {Error} 예외 설명
 * @deprecated 사용하지 않음
 * @since 1.0.0
 * @version 1.0.0
 * @author 작성자
 * @license MIT
 * @see {@link 다른함수}
 * @example
 * const result = myFunction('test');
 * console.log(result);
 */
```

### IDE 통합

#### VS Code 설정
```json
{
    "javascript.suggest.jsdoc.generateReturns": true,
    "typescript.suggest.jsdoc.generateReturns": true,
    "jsdoc.author": "Your Name",
    "jsdoc.license": "MIT"
}
```

### 결론
JSDoc은 JavaScript 코드의 문서화를 위한 강력한 도구입니다.
일관된 문서화 스타일과 타입 안전성을 확보하는 것이 중요합니다.
IDE 통합과 자동화 도구를 활용하여 개발 효율성을 향상시킬 수 있습니다.
팀 프로젝트에서는 JSDoc 규칙을 정하고 ESLint를 통해 일관성을 유지해야 합니다.











