// JavaScript Object 메서드 상세 설명 및 예제

// 1. Object.keys(obj): 객체의 모든 열거 가능한 프로퍼티 키를 배열로 반환
// - 객체의 키만 필요할 때 유용
// - 열거 가능한 프로퍼티만 반환 (enumerable: true)
const user = {
    name: 'John',
    age: 30,
    job: 'Developer',
    [Symbol('id')]: 123 // 심볼은 열거되지 않음
};
console.log(Object.keys(user)); // ['name', 'age', 'job']

// 실제 사용 예시: 객체의 모든 키를 순회하며 처리
Object.keys(user).forEach(key => {
    console.log(`${key}: ${user[key]}`);
});

// 2. Object.values(obj): 객체의 모든 열거 가능한 프로퍼티 값을 배열로 반환
// - 객체의 값만 필요할 때 유용
// - 열거 가능한 프로퍼티의 값만 반환
const product = {
    name: 'Laptop',
    price: 1000,
    inStock: true,
    [Symbol('sku')]: 'LP001' // 심볼은 열거되지 않음
};
console.log(Object.values(product)); // ['Laptop', 1000, true]

// 실제 사용 예시: 모든 가격의 합계 계산
const prices = {
    item1: 100,
    item2: 200,
    item3: 300
};
const total = Object.values(prices).reduce((sum, price) => sum + price, 0);
console.log(`Total: $${total}`); // Total: $600

// 3. Object.entries(obj): 객체의 모든 열거 가능한 프로퍼티를 [키, 값] 쌍의 배열로 반환
// - 객체를 배열로 변환하여 반복 처리가 필요할 때 유용
const settings = {
    theme: 'dark',
    language: 'ko',
    notifications: true
};
console.log(Object.entries(settings)); // [['theme', 'dark'], ['language', 'ko'], ['notifications', true]]

// 실제 사용 예시: 객체를 Map으로 변환
const map = new Map(Object.entries(settings));
console.log(map.get('theme')); // 'dark'

// 4. Object.assign(target, ...sources): 하나 이상의 소스 객체에서 대상 객체로 프로퍼티를 복사
// - 객체 병합, 복사, 기본값 설정 등에 사용
// - 얕은 복사만 수행 (중첩된 객체는 참조만 복사)
const defaultConfig = {
    apiKey: 'default-key',
    timeout: 5000,
    retries: 3
};
const userConfig = {
    apiKey: 'user-key',
    timeout: 3000
};
const finalConfig = Object.assign({}, defaultConfig, userConfig);
console.log(finalConfig); // { apiKey: 'user-key', timeout: 3000, retries: 3 }

// 실제 사용 예시: 객체 복사
const original = { a: 1, b: { c: 2 } };
const copy = Object.assign({}, original);
console.log(copy); // { a: 1, b: { c: 2 } }
copy.b.c = 3; // 원본 객체도 변경됨 (얕은 복사)

// 5. Object.freeze(obj): 객체를 완전히 불변하게 만듦
// - 프로퍼티 추가, 수정, 삭제가 모두 불가능
// - 중첩된 객체는 동결되지 않음 (얕은 동결)
const config = Object.freeze({
    apiKey: '123',
    endpoints: {
        users: '/api/users',
        posts: '/api/posts'
    }
});
config.apiKey = '456'; // 무시됨
config.endpoints.users = '/api/new-users'; // 중첩 객체는 수정 가능
console.log(config); // { apiKey: '123', endpoints: { users: '/api/new-users', posts: '/api/posts' } }

// 실제 사용 예시: 설정 객체 보호
const appConfig = Object.freeze({
    version: '1.0.0',
    debug: false,
    settings: {
        theme: 'light',
        language: 'en'
    }
});

// 6. Object.seal(obj): 객체를 밀봉하여 프로퍼티 추가/삭제는 불가능하지만 값 수정은 가능
// - 기존 프로퍼티의 값은 수정 가능
// - 프로퍼티 추가/삭제는 불가능
const userProfile = Object.seal({
    name: 'John',
    age: 30,
    email: 'john@example.com'
});
userProfile.age = 31; // 가능
userProfile.job = 'Developer'; // 무시됨
delete userProfile.email; // 무시됨
console.log(userProfile); // { name: 'John', age: 31, email: 'john@example.com' }

// 실제 사용 예시: 사용자 프로필 수정 제한
const profile = Object.seal({
    username: 'john_doe',
    email: 'john@example.com',
    preferences: {
        theme: 'dark',
        notifications: true
    }
});

// 7. Object.defineProperty(obj, prop, descriptor): 객체의 프로퍼티를 상세하게 정의
// - 프로퍼티의 특성(writable, enumerable, configurable)을 제어
// - getter/setter 정의 가능
const person = {};
Object.defineProperty(person, 'name', {
    value: 'John',
    writable: false, // 값 수정 불가
    enumerable: true, // 열거 가능
    configurable: false // 삭제 및 재정의 불가
});
console.log(person.name); // 'John'
person.name = 'Jane'; // 무시됨
console.log(person.name); // 'John'

// 실제 사용 예시: getter/setter 정의
const temperature = {
    _celsius: 0
};
Object.defineProperty(temperature, 'celsius', {
    get() {
        return this._celsius;
    },
    set(value) {
        if (value < -273.15) {
            throw new Error('Temperature cannot be below absolute zero');
        }
        this._celsius = value;
    }
});
temperature.celsius = 25;
console.log(temperature.celsius); // 25

// 8. Object.create(proto, [propertiesObject]): 지정된 프로토타입을 가진 새 객체 생성
// - 프로토타입 상속을 구현할 때 유용
// - 프로퍼티를 추가로 정의 가능
const animal = {
    makeSound() {
        console.log('Some sound');
    }
};
const dog = Object.create(animal, {
    name: {
        value: 'Rex',
        enumerable: true
    },
    breed: {
        value: 'German Shepherd',
        enumerable: true
    }
});
dog.makeSound(); // 'Some sound'
console.log(dog.name); // 'Rex'

// 실제 사용 예시: 프로토타입 체인 구현
const vehicle = {
    start() {
        console.log('Vehicle starting...');
    }
};
const car = Object.create(vehicle, {
    wheels: {
        value: 4,
        enumerable: true
    }
});
car.start(); // 'Vehicle starting...'

// 9. Object.getPrototypeOf(obj)와 Object.setPrototypeOf(obj, prototype)
// - 객체의 프로토타입을 가져오거나 설정
const animal2 = { type: 'animal' };
const dog2 = { name: 'Rex' };
Object.setPrototypeOf(dog2, animal2);
console.log(Object.getPrototypeOf(dog2) === animal2); // true
console.log(dog2.type); // 'animal'

// 실제 사용 예시: 프로토타입 체인 확인
const mammal = { type: 'mammal' };
const dog3 = Object.create(mammal);
console.log(Object.getPrototypeOf(dog3) === mammal); // true

// 10. Object.is(value1, value2): 두 값이 같은지 여부를 비교
// - === 연산자와 달리 NaN과 -0, +0을 정확하게 비교
console.log(Object.is(NaN, NaN)); // true
console.log(NaN === NaN); // false
console.log(Object.is(-0, +0)); // false
console.log(-0 === +0); // true

// 실제 사용 예시: 특수한 값 비교
const compareValues = (a, b) => {
    if (Object.is(a, b)) {
        console.log('Values are exactly the same');
    } else {
        console.log('Values are different');
    }
};
compareValues(NaN, NaN); // 'Values are exactly the same'
compareValues(-0, +0); // 'Values are different'






