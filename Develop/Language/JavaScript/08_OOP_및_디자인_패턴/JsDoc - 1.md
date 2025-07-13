# JSDoc

## 📖 JSDoc이란?

JSDoc은 JavaScript 코드에 특별한 형태의 주석을 추가하여 코드의 구조와 기능을 문서화하는 표준 방식입니다. 

**왜 JSDoc을 사용할까요?**
- 코드의 가독성과 유지보수성을 크게 향상시킵니다
- IDE에서 자동완성과 타입 힌트를 제공받을 수 있습니다
- 자동으로 API 문서를 생성할 수 있습니다
- 팀원들과의 협업이 훨씬 수월해집니다

## 🎯 기본 문법

JSDoc 주석은 `/**`로 시작하고 `*/`로 끝납니다. 각 줄은 `*`로 시작하며, 특별한 태그들을 사용하여 다양한 정보를 문서화합니다.

```javascript
/**
 * 함수나 클래스에 대한 설명
 * @param {타입} 매개변수명 - 매개변수 설명
 * @returns {타입} 반환값 설명
 */
```

## 📝 주요 태그들

### 1. @param - 매개변수 문서화

함수의 매개변수(parameter)에 대한 설명을 추가합니다.

**기본 형식:**
```javascript
@param {타입} 매개변수명 - 설명
```

**실제 예시:**
```javascript
/**
 * 두 숫자를 더하는 함수
 * @param {number} a - 첫 번째 숫자 (더할 숫자)
 * @param {number} b - 두 번째 숫자 (더할 숫자)
 * @returns {number} 두 숫자의 합계
 */
function add(a, b) {
    return a + b;
}

// 사용 예시
console.log(add(5, 3)); // 8
```

**복잡한 객체 타입의 경우:**
```javascript
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

### 2. @returns - 반환값 문서화

함수가 어떤 값을 반환하는지 명시합니다.

**기본 형식:**
```javascript
@returns {타입} 설명
```

**실제 예시:**
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

### 3. @type - 변수 타입 명시

변수나 상수의 타입을 명시적으로 선언합니다.

**기본 형식:**
```javascript
@type {타입}
```

**실제 예시:**
```javascript
/**
 * 사용자 정보 객체
 * @type {{name: string, age: number, email?: string}}
 */
const user = {
    name: "김철수",
    age: 25,
    email: "kim@example.com"
};

/**
 * 숫자 배열
 * @type {number[]}
 */
const scores = [85, 92, 78, 96];

/**
 * 함수 타입
 * @type {function(string, number): boolean}
 */
const validator = (name, age) => name.length > 0 && age > 0;
```

### 4. @class - 클래스 정의

클래스를 정의할 때 사용합니다.

**실제 예시:**
```javascript
/**
 * 사람을 나타내는 클래스
 * @class
 */
class Person {
    /**
     * Person 클래스의 생성자
     * @constructor
     * @param {string} name - 사람의 이름
     * @param {number} age - 사람의 나이
     */
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
}

// 사용 예시
const person = new Person("이영희", 30);
```

### 5. @method - 클래스 메서드 문서화

클래스 내의 메서드를 설명합니다.

**실제 예시:**
```javascript
/**
 * 학생을 나타내는 클래스
 * @class
 */
class Student {
    /**
     * @constructor
     * @param {string} name - 학생 이름
     * @param {number} grade - 학년
     */
    constructor(name, grade) {
        this.name = name;
        this.grade = grade;
    }

    /**
     * 학생의 인사말을 반환하는 메서드
     * @method
     * @returns {string} 인사말 문자열
     */
    greet() {
        return `안녕하세요! 저는 ${this.grade}학년 ${this.name}입니다.`;
    }

    /**
     * 학생의 정보를 문자열로 반환하는 메서드
     * @method
     * @returns {string} 학생 정보 문자열
     */
    getInfo() {
        return `이름: ${this.name}, 학년: ${this.grade}`;
    }
}
```

### 6. @example - 사용 예제 제공

함수나 클래스의 사용 방법을 예제로 보여줍니다.

**실제 예시:**
```javascript
/**
 * 배열의 모든 요소에 함수를 적용하는 유틸리티 함수
 * @param {Array} array - 처리할 배열
 * @param {function} callback - 각 요소에 적용할 함수
 * @returns {Array} 처리된 결과 배열
 * @example
 * // 숫자 배열의 각 요소를 2배로 만들기
 * const numbers = [1, 2, 3, 4];
 * const doubled = mapArray(numbers, x => x * 2);
 * console.log(doubled); // [2, 4, 6, 8]
 * 
 * // 문자열 배열을 대문자로 변환하기
 * const names = ['alice', 'bob', 'charlie'];
 * const upperNames = mapArray(names, name => name.toUpperCase());
 * console.log(upperNames); // ['ALICE', 'BOB', 'CHARLIE']
 */
function mapArray(array, callback) {
    return array.map(callback);
}
```

## 🔧 고급 태그들

### 선택적 매개변수와 기본값

```javascript
/**
 * 사용자 정보를 생성하는 함수
 * @param {string} name - 사용자 이름 (필수)
 * @param {number} [age=18] - 사용자 나이 (선택사항, 기본값: 18)
 * @param {string} [city] - 사용자 도시 (선택사항)
 * @returns {{name: string, age: number, city: string}} 사용자 객체
 */
function createUser(name, age = 18, city) {
    return {
        name,
        age,
        city: city || '서울'
    };
}
```

### 유니온 타입과 제네릭

```javascript
/**
 * 두 값을 비교하는 함수
 * @param {string|number} a - 첫 번째 값
 * @param {string|number} b - 두 번째 값
 * @returns {boolean} 두 값이 같은지 여부
 */
function isEqual(a, b) {
    return a === b;
}

/**
 * 배열의 첫 번째 요소를 반환하는 함수
 * @template T
 * @param {T[]} array - 배열
 * @returns {T|undefined} 첫 번째 요소 또는 undefined
 */
function getFirst(array) {
    return array[0];
}
```

## 💡 실무 활용 팁

### 1. 일관성 있는 문서화
- 팀 내에서 동일한 스타일과 형식을 사용하세요
- 매개변수 설명은 간결하지만 명확하게 작성하세요

### 2. 타입 정보 활용
- IDE의 자동완성 기능을 최대한 활용하세요
- 복잡한 객체 구조는 상세히 문서화하세요

### 3. 예제 코드 포함
- 복잡한 함수는 반드시 사용 예제를 포함하세요
- 예제는 실제 사용 가능한 코드여야 합니다

### 4. 정기적인 업데이트
- 코드가 변경될 때마다 JSDoc도 함께 업데이트하세요
- 오래된 문서는 오히려 혼란을 야기할 수 있습니다






