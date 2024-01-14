
// 1. Object.keys(obj): 주어진 객체의 열거 가능한 프로퍼티 키를 배열로 반환합니다.

const obj = { a: 1, b: 2, c: 3 };
const keys = Object.keys(obj);
console.log(keys); // ["a", "b", "c"]


// 2. Object.values(obj): 주어진 객체의 열거 가능한 프로퍼티 값들을 배열로 반환합니다.

const obj2 = { a: 1, b: 2, c: 3 };
const values = Object.values(obj2);
console.log(values); // [1, 2, 3]


// 3. Object.entries(obj): 주어진 객체의 열거 가능한 프로퍼티 키와 값들을 [키, 값] 쌍의 배열로 반환합니다.

const obj3 = { a: 1, b: 2, c: 3 };
const entries = Object.entries(obj3);
console.log(entries); // [["a", 1], ["b", 2], ["c", 3]]


// 4. Object.assign(target, ...sources): 하나 이상의 소스 객체에서 대상 객체로 프로퍼티들을 복사합니다.

const target = { a: 1 };
const source = { b: 2 };
const result = Object.assign(target, source);
console.log(result); // { a: 1, b: 2 }


// 5. Object.hasOwnProperty(prop): 객체가 주어진 프로퍼티를 직접 소유하고 있는지 여부를 확인합니다.

const obj4 = { a: 1 };
console.log(obj4.hasOwnProperty('a')); // true
console.log(obj4.hasOwnProperty('b')); // false


// 6. Object.freeze(obj): 주어진 객체를 변경할 수 없도록 동결합니다. 프로퍼티의 추가, 수정, 삭제가 불가능해집니다.

const obj5 = { a: 1 };
Object.freeze(obj5);
obj5.b = 2; // 변경이 불가능하므로 무시됩니다.
console.log(obj5); // { a: 1 }


// 7. Object.seal(obj): 주어진 객체를 밀봉하여 프로퍼티의 추가와 삭제는 불가능하지만 값의 수정은 가능하도록 합니다.
const obj6 = { a: 1 };
Object.seal(obj6);
obj6.a = 2; // 값의 수정은 가능합니다.
obj6.b = 3; // 프로퍼티의 추가는 불가능하므로 무시됩니다.
console.log(obj6); // { a: 2 }


// 8. Object.getOwnPropertyDescriptor(obj, prop): 주어진 객체의 특정 프로퍼티에 대한 속성 디스크립터를 반환합니다. 디스크립터에는 해당 프로퍼티의 속성 정보가 포함됩니다.
const obj7 = { a: 1 };
const descriptor = Object.getOwnPropertyDescriptor(obj7, 'a');
console.log(descriptor);
// { value: 1, writable: true, enumerable: true, configurable: true }


// 9. Object.defineProperty(obj, prop, descriptor): 주어진 객체에 새로운 프로퍼티를 정의하거나 기존 프로퍼티의 속성을 수정합니다.
const obj9 = {};
Object.defineProperty(obj, 'a', {
    value: 1,
    writable: false,
    enumerable: true,
    configurable: false
});
console.log(obj9); // { a: 1 }
obj9.a = 2; // writable이 false이므로 값 수정이 불가능합니다.
console.log(obj9); // { a: 1 }



// 10. Object.create(proto, [propertiesObject]): 주어진 프로토타입을 가지는 새로운 객체를 생성합니다. 선택적으로 프로퍼티를 지정하여 추가적인 설정을 할 수 있습니다.
const person = {
    greeting() {
        console.log('Hello!');
    }
};
const john = Object.create(person);
john.name = 'John';
console.log(john.name); // John
john.greeting(); // Hello!


// 11. Object.getPrototypeOf(obj): 주어진 객체의 프로토타입을 반환합니다.
const person2 = { name: 'John' };
const john2 = Object.create(person2);
console.log(Object.getPrototypeOf(john2)); // { name: 'John' }


// 12. Object.setPrototypeOf(obj, prototype): 주어진 객체의 프로토타입을 설정합니다.
const person3 = { name: 'John' };
const john3 = {};
Object.setPrototypeOf(john3, person3);
console.log(john3.name); // John


// 13. Object.is(value1, value2): 두 값이 같은지 여부를 비교합니다. 일치 연산자(===)와 유사하지만 몇 가지 특별한 경우에 다른 결과를 반환할 수 있습니다.
console.log(Object.is(5, 5)); // true
console.log(Object.is('abc', 'abc')); // true
console.log(Object.is([], [])); // false (각각 다른 객체)

// 14. JavaScript에서 객체의 키를 만드는 방법
// 객체 리터럴 문법을 사용하여 객체와 문자열 키를 생성할 수 있습니다.
const obj14 = {
    key1: 'value1',
    'key2': 'value2',
    "key3": 'value3'
};

// 변수를 사용하여 동적으로 키를 생성할 수도 있습니다.
const dynamicKey = 'dynamicKey';
const obj14_2 = {
    [dynamicKey]: 'dynamicValue'
};

console.log(obj14_2);

// 15. 심볼을 생성하고 객체의 키로 사용할 수 있습니다.
const key = Symbol('uniqueKey');
const obj15 = {
    [key]: 'value'
};

console.log(obj15)

// 16. 표현식을 사용하여 키를 동적으로 계산할 수 있습니다.
const prefix = 'pre';
const suffix = 'suf';
const obj16 = {
   [`${prefix}fix`]: 'value'
};
console.log(obj16)






