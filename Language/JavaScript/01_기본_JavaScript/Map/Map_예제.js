// 1. 기본적인 Map 생성과 조작
console.log('1. 기본적인 Map 생성과 조작');
const map = new Map();

// 키-값 쌍 추가
map.set('name', '김철수');
map.set('age', 25);
map.set('job', '개발자');

// 값 가져오기
console.log(map.get('name')); // 출력: 김철수
console.log(map.get('age')); // 출력: 25

// 키 존재 여부 확인
console.log(map.has('job')); // 출력: true
console.log(map.has('address')); // 출력: false

// Map의 크기
console.log(map.size); // 출력: 3

// 키-값 쌍 삭제
map.delete('age');
console.log(map.size); // 출력: 2

// 2. 다양한 타입의 키 사용
console.log('\n2. 다양한 타입의 키 사용');
const map2 = new Map();

// 객체를 키로 사용
const user = { id: 1 };
map2.set(user, '사용자 정보');

// 함수를 키로 사용
function greeting() { console.log('Hello!'); }
map2.set(greeting, '인사 함수');

// 숫자를 키로 사용
map2.set(42, '답');

console.log(map2.get(user)); // 출력: 사용자 정보
console.log(map2.get(greeting)); // 출력: 인사 함수
console.log(map2.get(42)); // 출력: 답

// 3. Map 순회하기
console.log('\n3. Map 순회하기');
const userMap = new Map([
    ['user1', { name: '김철수', age: 25 }],
    ['user2', { name: '이영희', age: 28 }],
    ['user3', { name: '박민수', age: 30 }]
]);

// forEach 사용
userMap.forEach((value, key) => {
    console.log(`${key}: ${value.name}, ${value.age}세`);
});

// for...of로 entries() 순회
for (let [key, value] of userMap.entries()) {
    console.log(`${key}: ${value.name}, ${value.age}세`);
}

// 키만 순회
for (let key of userMap.keys()) {
    console.log(key);
}

// 값만 순회
for (let value of userMap.values()) {
    console.log(`${value.name}, ${value.age}세`);
}

// 4. Map 체이닝
console.log('\n4. Map 체이닝');
const chainMap = new Map()
    .set('user1', '김철수')
    .set('user2', '이영희')
    .set('user3', '박민수');

console.log(chainMap.size); // 출력: 3

// 5. 배열과 Map 변환
console.log('\n5. 배열과 Map 변환');
const arr = [
    ['key1', 'value1'],
    ['key2', 'value2']
];
const mapFromArray = new Map(arr);

// Map에서 배열로 변환
const arrayFromMap = Array.from(mapFromArray);
console.log(arrayFromMap);

// 6. 객체와 Map 변환
console.log('\n6. 객체와 Map 변환');
const userObj = {
    name: '김철수',
    age: 25,
    job: '개발자'
};
const mapFromObj = new Map(Object.entries(userObj));

// Map에서 객체로 변환
const objFromMap = Object.fromEntries(mapFromObj);
console.log(objFromMap);

// 7. Map을 사용한 캐시 구현
console.log('\n7. Map을 사용한 캐시 구현');
class Cache {
    constructor() {
        this.cache = new Map();
    }

    set(key, value, timeoutInMs) {
        const expiryTime = Date.now() + timeoutInMs;
        this.cache.set(key, { value, expiryTime });

        setTimeout(() => {
            if (this.cache.has(key)) {
                this.cache.delete(key);
            }
        }, timeoutInMs);
    }

    get(key) {
        const data = this.cache.get(key);
        if (!data) return null;
        
        if (Date.now() > data.expiryTime) {
            this.cache.delete(key);
            return null;
        }
        
        return data.value;
    }
}

// 사용 예
const cache = new Cache();
cache.set('user', { name: '김철수' }, 5000); // 5초 후 만료

console.log(cache.get('user')); // 출력: { name: '김철수' }

setTimeout(() => {
    console.log(cache.get('user')); // 출력: null
}, 5500);

// 8. WeakMap 사용 예제
console.log('\n8. WeakMap 사용 예제');
const weakMap = new WeakMap();
let weakMapObj = { data: '임시 데이터' };

// WeakMap에 객체를 키로 저장
weakMap.set(weakMapObj, '비밀 데이터');
console.log(weakMap.get(weakMapObj)); // 출력: 비밀 데이터

// weakMapObj 참조 제거
weakMapObj = null;
// weakMapObj가 가비지 컬렉션의 대상이 되며, WeakMap에서도 자동으로 제거됨 