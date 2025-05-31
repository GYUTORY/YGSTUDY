// JavaScript의 다양한 반복문(For Loop) 예제

// 1. 기본 for 루프
// 가장 기본적인 반복문으로, 초기값, 조건, 증감식을 사용합니다.
console.log('=== 기본 for 루프 ===');
for (let i = 0; i < 5; i++) {
    console.log(`현재 숫자: ${i}`);
}

// 중첩 for 루프 예제
console.log('\n=== 중첩 for 루프 ===');
for (let i = 1; i <= 3; i++) {
    for (let j = 1; j <= 3; j++) {
        console.log(`i: ${i}, j: ${j}`);
    }
}

// 2. for...of 루프
// 배열이나 이터러블 객체의 요소를 순회할 때 사용합니다.
console.log('\n=== for...of 루프 ===');
const fruits = ['apple', 'banana', 'cherry', 'orange', 'grape'];
for (const fruit of fruits) {
    console.log(`과일: ${fruit}`);
}

// 문자열 순회 예제
console.log('\n=== 문자열 순회 ===');
const message = 'Hello';
for (const char of message) {
    console.log(`문자: ${char}`);
}

// 3. for...in 루프
// 객체의 열거 가능한 속성을 순회할 때 사용합니다.
console.log('\n=== for...in 루프 ===');
const person = {
    name: 'John',
    age: 30,
    city: 'New York',
    job: 'Developer'
};

for (const key in person) {
    console.log(`${key}: ${person[key]}`);
}

// 배열에서의 for...in 사용 (권장하지 않음)
console.log('\n=== 배열에서의 for...in (권장하지 않음) ===');
const numbers = [1, 2, 3, 4, 5];
for (const index in numbers) {
    console.log(`인덱스 ${index}: ${numbers[index]}`);
}

// 4. forEach 메서드
// 배열의 각 요소에 대해 콜백 함수를 실행합니다.
console.log('\n=== forEach 메서드 ===');
const colors = ['red', 'green', 'blue', 'yellow', 'purple'];
colors.forEach((color, index, array) => {
    console.log(`색상 ${index + 1}: ${color}`);
    console.log(`전체 배열: ${array}`);
});

// 객체 배열에서의 forEach 사용
console.log('\n=== 객체 배열에서의 forEach ===');
const users = [
    { id: 1, name: 'Alice' },
    { id: 2, name: 'Bob' },
    { id: 3, name: 'Charlie' }
];

users.forEach((user, index) => {
    console.log(`사용자 ${index + 1}: ID ${user.id}, 이름 ${user.name}`);
});

// 5. while 루프
// 조건이 참인 동안 계속 실행됩니다.
console.log('\n=== while 루프 ===');
let count = 0;
while (count < 3) {
    console.log(`카운트: ${count}`);
    count++;
}

// 6. do...while 루프
// 최소 한 번은 실행되고, 그 후 조건을 검사합니다.
console.log('\n=== do...while 루프 ===');
let num = 0;
do {
    console.log(`숫자: ${num}`);
    num++;
} while (num < 3);

// 7. break와 continue 사용 예제
console.log('\n=== break와 continue 사용 ===');
for (let i = 0; i < 5; i++) {
    if (i === 2) {
        continue; // 2를 건너뜁니다
    }
    if (i === 4) {
        break; // 4에서 루프를 종료합니다
    }
    console.log(`현재 숫자: ${i}`);
}

// 8. 레이블 사용 예제
console.log('\n=== 레이블 사용 ===');
outerLoop: for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
        if (i === 1 && j === 1) {
            break outerLoop; // 외부 루프를 종료합니다
        }
        console.log(`i: ${i}, j: ${j}`);
    }
}