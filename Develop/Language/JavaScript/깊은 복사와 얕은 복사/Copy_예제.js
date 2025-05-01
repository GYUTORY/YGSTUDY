// 1. 얕은 복사 예제
console.log('1. 얕은 복사 예제');

// Object.assign() 사용
const originalObj = {
    name: '김철수',
    age: 25,
    hobbies: ['독서', '게임']
};

const shallowCopy1 = Object.assign({}, originalObj);
const shallowCopy2 = { ...originalObj }; // 전개 연산자 사용

// 첫 번째 레벨 속성 변경
shallowCopy1.name = '이영희';
console.log('원본 name:', originalObj.name); // 출력: 김철수
console.log('복사본 name:', shallowCopy1.name); // 출력: 이영희

// 중첩된 배열 변경
shallowCopy1.hobbies.push('운동');
console.log('원본 hobbies:', originalObj.hobbies); // 출력: ['독서', '게임', '운동']
console.log('복사본 hobbies:', shallowCopy1.hobbies); // 출력: ['독서', '게임', '운동']

// 2. 배열의 얕은 복사
console.log('\n2. 배열의 얕은 복사');

const originalArray = [1, 2, { x: 3 }];
const shallowArrayCopy1 = [...originalArray];
const shallowArrayCopy2 = originalArray.slice();
const shallowArrayCopy3 = Array.from(originalArray);

shallowArrayCopy1[2].x = 4;
console.log('원본 배열의 객체:', originalArray[2]); // 출력: { x: 4 }
console.log('복사본 배열의 객체:', shallowArrayCopy1[2]); // 출력: { x: 4 }

// 3. 깊은 복사 - JSON 방식
console.log('\n3. 깊은 복사 - JSON 방식');

const originalObj2 = {
    name: '김철수',
    age: 25,
    hobbies: ['독서', '게임'],
    address: {
        city: '서울',
        district: '강남구'
    }
};

const deepCopy1 = JSON.parse(JSON.stringify(originalObj2));

deepCopy1.hobbies.push('운동');
deepCopy1.address.city = '부산';

console.log('원본 hobbies:', originalObj2.hobbies); // 출력: ['독서', '게임']
console.log('복사본 hobbies:', deepCopy1.hobbies); // 출력: ['독서', '게임', '운동']
console.log('원본 city:', originalObj2.address.city); // 출력: 서울
console.log('복사본 city:', deepCopy1.address.city); // 출력: 부산

// 4. JSON 방식의 깊은 복사 한계
console.log('\n4. JSON 방식의 깊은 복사 한계');

const objWithSpecialValues = {
    func: function() { console.log('Hello!'); },
    undef: undefined,
    date: new Date(),
    regexp: /test/,
    infinity: Infinity,
    nan: NaN
};

const deepCopyWithLimits = JSON.parse(JSON.stringify(objWithSpecialValues));

console.log('원본:', objWithSpecialValues);
console.log('복사본:', deepCopyWithLimits);

// 5. 재귀적 깊은 복사 구현
console.log('\n5. 재귀적 깊은 복사 구현');

function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }

    // Date 객체 처리
    if (obj instanceof Date) {
        return new Date(obj.getTime());
    }

    // RegExp 객체 처리
    if (obj instanceof RegExp) {
        return new RegExp(obj);
    }

    // 배열이나 객체의 새 인스턴스 생성
    const clone = Array.isArray(obj) ? [] : {};

    Object.keys(obj).forEach(key => {
        clone[key] = deepClone(obj[key]);
    });

    return clone;
}

const complexObj = {
    string: 'Hello',
    number: 123,
    boolean: true,
    null: null,
    date: new Date(),
    regexp: /test/,
    array: [1, 2, 3],
    nested: {
        a: 1,
        b: 2,
        c: [3, 4, 5]
    },
    func: function() { return 'Hello!'; }
};

const deepCloned = deepClone(complexObj);
deepCloned.nested.a = 999;
deepCloned.nested.c.push(6);

console.log('원본 nested.a:', complexObj.nested.a); // 출력: 1
console.log('복사본 nested.a:', deepCloned.nested.a); // 출력: 999
console.log('원본 nested.c:', complexObj.nested.c); // 출력: [3, 4, 5]
console.log('복사본 nested.c:', deepCloned.nested.c); // 출력: [3, 4, 5, 6]

// 6. 순환 참조 객체 처리
console.log('\n6. 순환 참조 객체 처리');

function deepCloneWithCircular(obj, hash = new WeakMap()) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }

    if (hash.has(obj)) {
        return hash.get(obj);
    }

    const clone = Array.isArray(obj) ? [] : {};
    hash.set(obj, clone);

    Object.keys(obj).forEach(key => {
        clone[key] = deepCloneWithCircular(obj[key], hash);
    });

    return clone;
}

// 순환 참조가 있는 객체
const circular = {
    name: '순환 참조 객체'
};
circular.self = circular;

try {
    // JSON 방식으로 복사 시도 (에러 발생)
    const circularCopyError = JSON.parse(JSON.stringify(circular));
} catch (error) {
    console.log('JSON 방식 순환 참조 에러:', error.message);
}

// 커스텀 함수로 복사 (정상 작동)
const circularCopySuccess = deepCloneWithCircular(circular);
console.log('순환 참조 복사 성공:', circularCopySuccess.name);
console.log('순환 참조 유지:', circularCopySuccess.self === circularCopySuccess); 