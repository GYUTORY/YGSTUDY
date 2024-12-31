
# JSDoc
- JavaScript 코드에 주석을 추가하여 코드의 구조와 기능을 문서화하는 도구입니다. 
- JSDoc을 사용하면 코드의 가독성을 높이고, 자동으로 API 문서를 생성할 수 있습니다. 

### 1. @param

- 매개변수에 대한 설명을 추가합니다.
- 형식: @param {타입} 매개변수명 - 설명

```javascript
/**
 * 두 수를 더합니다.
 * @param {number} a - 첫 번째 숫자
 * @param {number} b - 두 번째 숫자
 * @returns {number} 두 수의 합
 */
function add(a, b) {
    return a + b;
}
```

### 2. @returns

- 함수의 반환값에 대한 설명을 추가합니다.
- 형식: @returns {타입} 설명

```javascript
/**
 * 문자열을 대문자로 변환합니다.
 * @param {string} str - 변환할 문자열
 * @returns {string} 대문자로 변환된 문자열
 */
function toUpperCase(str) {
    return str.toUpperCase();
}
```

### 3. @type

- 변수의 타입을 명시합니다.
- 형식: @type {타입}

```javascript
/**
 * 사용자 객체
 * @type {{name: string, age: number}}
 */
const user = {
    name: "Alice",
    age: 30
};
```

### 4. @class

- 클래스를 정의할 때 사용합니다.

```javascript
/**
 * 사람 클래스
 * @class
 */
class Person {
    /**
     * @constructor
     * @param {string} name - 이름
     * @param {number} age - 나이
     */
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
}
```

### 5. @method

- 클래스의 메서드를 설명합니다.

```javascript
/**
 * 사람 클래스
 * @class
 */
class Person {
    /**
     * @method greet
     * @returns {string} 인사말
     */
    greet() {
        return `안녕하세요, 제 이름은 ${this.name}입니다.`;
    }
}
```

### 7. @example

- 사용 예제를 추가합니다.

```javascript
/**
 * 두 수를 더합니다.
 * @param {number} a - 첫 번째 숫자
 * @param {number} b - 두 번째 숫자
 * @returns {number} 두 수의 합
 * @example
 * // 사용 예
 * add(2, 3); // 5
 */
function add(a, b) {
    return a + b;
}
```






