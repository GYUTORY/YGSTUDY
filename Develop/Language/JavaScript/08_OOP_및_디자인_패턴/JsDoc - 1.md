---
title: JSDoc
tags: [language, javascript]
updated: 2026-01-12
---

# JSDoc
## 배경

JSDoc은 JavaScript 코드에 특별한 형태의 주석을 달아 코드의 구조와 기능을 문서화하는 표준 방식이다.

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

## 그 전에 — 켜지 않으면 그냥 주석이다

JSDoc 타입은 **기본적으로 아무것도 검사하지 않는다.** 아래 `add` 에 `@param {number}` 를 달아도 `add('1', 2)` 는 그대로 실행된다. 검사를 받으려면 타입스크립트 컴파일러에게 이 파일을 봐 달라고 명시해야 한다. 방법은 둘이다.

```javascript
// @ts-check          ← 파일 맨 위 한 줄. 그 파일만 검사한다.
```

```json
// tsconfig.json — 프로젝트 전체
{ "compilerOptions": { "allowJs": true, "checkJs": true, "strict": true, "noEmit": true } }
```

차이가 얼마나 큰지는 같은 파일을 두 번 돌려 보면 바로 나온다. 아래 문서에 실린 예제들을 그대로 넣고 컴파일한 결과다.

```
checkJs 끔 → 오류 0건
checkJs 켬 → 오류 10건
```

**켜지 않은 JSDoc 은 편집기 자동완성용 힌트**일 뿐이다. 팀에서 "JSDoc 을 달자"고 정해 놓고 `checkJs` 를 안 켜면, 시간이 지날수록 **코드와 다른 내용을 자신 있게 적어 둔 주석**이 쌓인다. 아무도 안 고치는 이유는 단순하다 — 아무도 틀렸다고 말해 주지 않기 때문이다. 그 상태의 JSDoc 은 없는 것보다 나쁘다. 없으면 코드를 읽고, 있으면 주석을 믿는다.

아래 태그 설명을 읽기 전에 이 한 줄을 먼저 켜 두는 편이 낫다. 켠 상태에서 무엇이 걸리는지는 뒤의 "실제로 검사기를 켜 보면" 절에 정리했다.

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

## 실제로 검사기를 켜 보면

위 예제들을 한 파일에 모아 `checkJs` + `strict` 로 컴파일하면 오류가 열 건 나온다. 종류별로 정리하면 여섯 가지이고, 전부 JSDoc 을 쓸 때 반복해서 걸리는 것들이다.

### 1. `{Object}` 는 "아무 객체"가 아니다

```
error TS7053: Element implicitly has an 'any' type because expression of type 'string'
  can't be used to index type 'Object'.
```

`ApiClient.get` 의 `@param {Object} [params]` 를 받아 `params[key]` 로 접근하는 줄에서 걸린다. `{Object}` 는 자바스크립트의 `Object` 생성자 타입으로 해석되고, 거기에는 `hasOwnProperty` 같은 것만 있지 **임의의 키가 없다.** 같은 이유로 `headers` 를 `fetch` 에 넘기는 줄도 막힌다.

키-값 사전이 필요하면 그렇게 적어야 한다.

```javascript
/** @param {Object<string, string>} params */
/** @param {Record<string, unknown>} options */
```

`{Object}` 는 대개 "타입을 아직 안 정했다"는 뜻으로 쓰이는데, 검사기를 켜면 그 사실이 그대로 드러난다. 정말 아무거나 받겠다면 `{*}` 나 `{any}` 를 쓰는 편이 정직하다 — 검사를 포기했다는 신호가 남는다.

### 2. `@typedef` 와 클래스는 같은 이름 공간을 쓴다

```
error TS2300: Duplicate identifier 'User'.
error TS2741: Property 'isAdult' is missing in type '{ name: string; age: number; }'
  but required in type 'User'
```

이 문서에는 `@typedef {Object} User` 와 `class User` 가 둘 다 있다. 같은 파일이면 충돌하고, **다른 파일이라도 둘 다 전역이면 나중 것이 이긴다.** 두 번째 오류가 그 결과다 — `createUser` 의 `@returns {User}` 가 typedef 가 아니라 클래스로 해석되면서, 클래스에만 있는 `isAdult` 가 없다고 지적한다.

JSDoc 은 `import`/`export` 가 없으면 타입이 전역으로 퍼진다. 파일이 늘수록 이름이 겹치고, 겹쳤을 때 나오는 오류 메시지는 원인을 가리키지 않는다. 이름을 구분하거나(`UserDTO`, `UserEntity`) 파일을 명시한다.

```javascript
/** @param {import('./models/user').User} user */
```

### 3. 선언한 반환 타입이 실제 반환값과 다르다

```
error TS2739: Type '{ ... id: string; updatedAt: Date; }' is missing the following
  properties from type 'UserModel': name, email, createdAt
```

`updateUser` 는 `@returns {Promise<UserModel>}` 라고 적어 두고 `{ id: userId, ...updates, updatedAt }` 를 반환한다. `updates` 가 `{Object}` 라 아무 필드도 보장하지 않으니 `name`·`email`·`createdAt` 이 빈다. **문서만 읽은 호출자는 `user.email` 이 당연히 있다고 믿는다.**

JSDoc 이 침묵할 때 가장 비싸게 무너지는 지점이 여기다. 반환 타입은 "함수 안을 안 봐도 된다"는 약속인데, 검사가 없으면 그 약속을 지키는 사람이 아무도 없다.

### 4. `Map.get()` 은 `undefined` 를 돌려준다

```
error TS2532: Object is possibly 'undefined'.
```

`EventEmitter.on` 의 `this.listeners.get(eventName).push(listener)` 가 걸린다. 바로 위에서 `has()` 로 확인하고 없으면 넣었으니 실제로는 안전한데, 컴파일러는 `has` 와 `get` 을 이어 주지 않는다. 흐름을 바꾸면 검사도 통과하고 Map 왕복도 준다.

```javascript
const list = this.listeners.get(eventName) ?? [];
list.push(listener);
this.listeners.set(eventName, list);
```

### 5. `@callback` 은 인자 개수까지 검사한다

```
error TS2554: Expected 2 arguments, but got 1.
```

`@callback EventListener` 는 `(event, data)` 두 개를 받는다고 선언해 놓고, `emit` 은 `listener({ name: eventName, data })` 로 하나만 넘긴다. 선언과 호출이 처음부터 어긋나 있었고 검사기를 켜기 전까지 아무도 몰랐다.

첫 인자 타입도 문제다. `@param {Event} event` 라고 쓰면 **DOM 의 `Event`** 를 가리킨다. 브라우저 타입이 로드된 환경에서는 이름이 그냥 이어져 버린다. 자기 이벤트 모양을 뜻하려면 typedef 를 따로 만들어야 한다.

```javascript
/**
 * @typedef {{ name: string, data: * }} EmitPayload
 */

/**
 * @callback EventListener
 * @param {EmitPayload} event
 */
```

`Event` 말고도 `Error`·`Element`·`Response`·`Request` 처럼 전역에 이미 있는 이름은 전부 같은 함정을 갖는다. **`{Xxx}` 안의 이름을 아무도 정의하지 않았을 때 오류가 나면 다행이고, 조용히 다른 것에 붙으면 사고다.**

### 6. `catch (error)` 의 `error` 는 `unknown` 이다

```
error TS18046: 'error' is of type 'unknown'.
```

`fetchUsers` 의 `return { success: false, error: error.message }` 가 걸린다. 던져지는 값이 `Error` 라는 보장이 없기 때문이다. 문자열이나 객체를 던지는 라이브러리는 실제로 있고, 그럴 때 `error.message` 는 `undefined` 가 되어 **에러 응답에 원인이 안 담긴다.** 응답 형식은 멀쩡한데 내용이 비는 형태라 로그를 봐도 알 수 없다.

```javascript
catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  return { success: false, error: message };
}
```

### 검사 대상이 아닌 태그도 있다

여섯 개를 고쳐도 남는 것이 있다. `@throws`·`@example`·`@deprecated`·`@since`·`@author` 는 **사람과 문서 생성기용**이고 컴파일러는 대체로 무시한다(편집기가 `@deprecated` 에 취소선을 긋는 정도다). `@throws {Error}` 를 적어 뒀다고 호출자가 잡도록 강제되지 않는다 — 자바의 검사 예외와 다르다.

그래서 태그를 두 부류로 나눠 두는 편이 낫다. **컴파일러가 지켜 주는 것**(`@param` `@returns` `@type` `@typedef` `@template` `@callback`)과 **사람이 지켜야 하는 것**(나머지)이다. 뒤쪽은 검사기를 켜도 여전히 썩는다.

## JSDoc 으로 갈지 TypeScript 로 갈지

위 여섯 개는 전부 타입스크립트에서는 안 나거나 훨씬 짧게 끝난다. 그런데도 JSDoc 을 고르는 이유는 하나다 — **빌드 단계를 만들지 않는다.** 그 하나가 값을 하는 자리가 있다.

| JSDoc + checkJs 가 맞는 자리 | TypeScript 가 맞는 자리 |
|---|---|
| 빌드 없이 그대로 실행하는 스크립트·CLI 도구 | 이미 번들러나 트랜스파일러가 있는 프로젝트 |
| 기존 JS 코드베이스에 점진 도입 | 새로 시작하는 프로젝트 |
| 배포물이 소스 그대로여야 할 때 | 선언 파일(`.d.ts`)을 배포해야 할 때 |
| 타입이 단순하고 수가 적을 때 | 제네릭·조건부 타입을 쓸 때 |

경계는 대체로 **타입 표현식이 길어지는 지점**에서 드러난다. 주석 안에 문자열로 타입을 적는 방식이라 줄바꿈이 어렵고, 오타가 나도 조용히 무시되는 경우가 있다. 아래 두 줄이 같은 뜻인데 위쪽이 읽히지 않기 시작하면 옮길 때다.

```javascript
/** @type {Map<string, Array<{ id: string, handler: (e: CustomEvent) => Promise<void> }>>} */
```

```typescript
type Handlers = Map<string, { id: string; handler: (e: CustomEvent) => Promise<void> }[]>;
```

점진 도입이라면 순서가 있다. `allowJs` 로 컴파일러부터 붙이고, 파일 하나씩 `// @ts-check` 를 달아 오류를 없앤 다음, 전부 통과하면 `checkJs: true` 로 올린다. **`strict` 는 마지막에 켠다.** 처음부터 켜면 위의 4번·6번 같은 오류가 수백 개 쏟아지고, 그러면 아무도 안 본다. 게이트는 정밀도가 재현율보다 중요하다.

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
JSDoc은 JavaScript 코드를 문서화하는 강력한 도구다.
일관된 문서화 스타일과 타입 안전성을 지키는 게 중요하다.
IDE 통합과 자동화 도구를 쓰면 개발 효율이 올라간다.
팀 프로젝트에서는 JSDoc 규칙을 정하고 ESLint로 일관성을 지켜야 한다.











