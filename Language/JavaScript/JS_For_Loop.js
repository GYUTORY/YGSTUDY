
// for 루프

for (let i = 0; i < 5; i++) {
    console.log(i);
}

// for of 루프
const arr = ['apple', 'banana', 'cherry'];
for (const element of arr) {
    console.log(element);
}

// for in 루프
const obj = { a: 1, b: 2, c: 3 };
for (const key in obj) {
    console.log(key, obj[key]);
}

// > 예시 설명: for...in 구문은 객체의 열거 가능한 속성을 순회하는 데 사용됩니다.
// 반복마다 객체의 속성 이름이 key 변수에 할당되고 해당 속성 이름과 값을 출력합니다. 이 예시에서는 객체 obj의 속성 이름과 값을 순차적으로 출력합니다.


// forEach

const arr2 = ['apple', 'banana', 'cherry'];
arr2.forEach((element, index) => {
    console.log(index, element);
});


// 예시 설명: forEach() 메서드는 배열의 각 요소에 대해 콜백 함수를 실행합니다.
// 콜백 함수는 요소와 인덱스를 인수로 받아 실행됩니다. 이 예시에서는 배열 arr의 각 요소와 인덱스를 출력합니다.