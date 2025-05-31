/**
 * 📝 JavaScript의 깊은 복사(Deep Copy)와 얕은 복사(Shallow Copy)
 * 
 * JavaScript에서 객체를 복사할 때는 깊은 복사와 얕은 복사라는 두 가지 방식을 사용할 수 있습니다.
 * 이 글에서는 각각의 복사 방식과 그 차이점, 그리고 실제 사용 예시를 살펴보겠습니다.
 */

// ===== 1. 얕은 복사 (Shallow Copy) =====
console.log('1️⃣ 얕은 복사 (Shallow Copy)');

/**
 * 얕은 복사는 객체의 최상위 수준의 속성만 복사하는 방식입니다.
 * 중첩된 객체나 배열은 참조만 복사되어 원본과 복사본이 같은 메모리 주소를 공유하게 됩니다.
 */

// 예시 객체 생성
const originalObj = {
    name: '김철수',
    age: 25,
    hobbies: ['독서', '게임']
};

// 얕은 복사 방법 1: Object.assign() 사용
const shallowCopy1 = Object.assign({}, originalObj);

// 얕은 복사 방법 2: 전개 연산자(Spread Operator) 사용
const shallowCopy2 = { ...originalObj };

// 얕은 복사의 특징 확인
console.log('\n📌 얕은 복사의 특징');

// 1. 최상위 속성 변경 시 독립적으로 동작
shallowCopy1.name = '이영희';
console.log('원본 name:', originalObj.name);     // 출력: 김철수
console.log('복사본 name:', shallowCopy1.name);  // 출력: 이영희

// 2. 중첩된 객체/배열은 참조 공유
shallowCopy1.hobbies.push('운동');
console.log('원본 hobbies:', originalObj.hobbies);    // 출력: ['독서', '게임', '운동']
console.log('복사본 hobbies:', shallowCopy1.hobbies); // 출력: ['독서', '게임', '운동']

// ===== 2. 배열의 얕은 복사 =====
console.log('\n2️⃣ 배열의 얕은 복사');

/**
 * 배열도 객체이므로 얕은 복사의 특성을 그대로 가집니다.
 * 배열을 복사하는 여러 방법을 살펴보겠습니다.
 */

const originalArray = [1, 2, { x: 3 }];

// 배열 얕은 복사 방법들
const shallowArrayCopy1 = [...originalArray];        // 전개 연산자
const shallowArrayCopy2 = originalArray.slice();     // slice() 메서드
const shallowArrayCopy3 = Array.from(originalArray); // Array.from()

// 중첩된 객체 수정 시 참조 공유 확인
shallowArrayCopy1[2].x = 4;
console.log('원본 배열의 객체:', originalArray[2]);     // 출력: { x: 4 }
console.log('복사본 배열의 객체:', shallowArrayCopy1[2]); // 출력: { x: 4 }

// ===== 3. 깊은 복사 (Deep Copy) =====
console.log('\n3️⃣ 깊은 복사 (Deep Copy)');

/**
 * 깊은 복사는 객체의 모든 중첩 수준을 완전히 새로운 복사본으로 만듭니다.
 * 가장 간단한 방법은 JSON을 이용하는 것입니다.
 */

const originalObj2 = {
    name: '김철수',
    age: 25,
    hobbies: ['독서', '게임'],
    address: {
        city: '서울',
        district: '강남구'
    }
};

// JSON을 이용한 깊은 복사
const deepCopy1 = JSON.parse(JSON.stringify(originalObj2));

// 깊은 복사의 특징 확인
console.log('\n📌 깊은 복사의 특징');

deepCopy1.hobbies.push('운동');
deepCopy1.address.city = '부산';

console.log('원본 hobbies:', originalObj2.hobbies);    // 출력: ['독서', '게임']
console.log('복사본 hobbies:', deepCopy1.hobbies);     // 출력: ['독서', '게임', '운동']
console.log('원본 city:', originalObj2.address.city);  // 출력: 서울
console.log('복사본 city:', deepCopy1.address.city);   // 출력: 부산

// ===== 4. JSON 방식의 깊은 복사 한계 =====
console.log('\n4️⃣ JSON 방식의 깊은 복사 한계');

/**
 * JSON 방식의 깊은 복사는 다음과 같은 한계가 있습니다:
 * - 함수는 복사되지 않음
 * - undefined는 null로 변환됨
 * - Date 객체는 문자열로 변환됨
 * - RegExp 객체는 빈 객체로 변환됨
 * - 순환 참조가 있는 객체는 처리할 수 없음
 */

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

// ===== 5. 재귀적 깊은 복사 구현 =====
console.log('\n5️⃣ 재귀적 깊은 복사 구현');

/**
 * JSON 방식의 한계를 극복하기 위해 재귀적으로 깊은 복사를 구현할 수 있습니다.
 * 이 방식은 Date, RegExp 등 특수한 객체들도 올바르게 처리할 수 있습니다.
 */

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

// 복잡한 객체로 테스트
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

console.log('원본 nested.a:', complexObj.nested.a);    // 출력: 1
console.log('복사본 nested.a:', deepCloned.nested.a);  // 출력: 999
console.log('원본 nested.c:', complexObj.nested.c);    // 출력: [3, 4, 5]
console.log('복사본 nested.c:', deepCloned.nested.c);  // 출력: [3, 4, 5, 6]

// ===== 6. 순환 참조 처리 =====
console.log('\n6️⃣ 순환 참조 처리');

/**
 * 순환 참조가 있는 객체의 경우, WeakMap을 사용하여 이미 복사된 객체를 추적하고
 * 재귀 호출을 방지할 수 있습니다.
 */

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

// 순환 참조가 있는 객체 생성
const circular = {
    name: '순환 참조 객체'
};
circular.self = circular;

// JSON 방식으로 복사 시도 (에러 발생)
try {
    const circularCopyError = JSON.parse(JSON.stringify(circular));
} catch (error) {
    console.log('JSON 방식 순환 참조 에러:', error.message);
}

// 커스텀 함수로 복사 (정상 작동)
const circularCopySuccess = deepCloneWithCircular(circular);
console.log('순환 참조 복사 성공:', circularCopySuccess.name);
console.log('순환 참조 유지:', circularCopySuccess.self === circularCopySuccess);

/**
 * 🎯 결론
 * 
 * 1. 얕은 복사는 간단하지만 중첩된 객체의 참조를 공유합니다.
 * 2. JSON 방식의 깊은 복사는 간단하지만 특수한 객체들을 처리할 수 없습니다.
 * 3. 재귀적 깊은 복사는 모든 경우를 처리할 수 있지만, 구현이 복잡합니다.
 * 4. 순환 참조가 있는 경우 WeakMap을 사용하여 처리할 수 있습니다.
 * 
 * 상황에 따라 적절한 복사 방식을 선택하는 것이 중요합니다.
 */ 