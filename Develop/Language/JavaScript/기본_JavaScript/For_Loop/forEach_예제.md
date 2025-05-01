# forEach 사용 예제

## 1. 기본적인 배열 순회
```javascript
const fruits = ['사과', '바나나', '오렌지'];

fruits.forEach((fruit, index) => {
    console.log(`${index + 1}번째 과일: ${fruit}`);
});

// 출력:
// 1번째 과일: 사과
// 2번째 과일: 바나나
// 3번째 과일: 오렌지
```

## 2. 배열 요소의 합계 계산
```javascript
const numbers = [1, 2, 3, 4, 5];
let sum = 0;

numbers.forEach(number => {
    sum += number;
});

console.log(`합계: ${sum}`); // 출력: 합계: 15
```

## 3. 객체 배열 처리
```javascript
const students = [
    { name: '김철수', score: 90 },
    { name: '이영희', score: 85 },
    { name: '박민수', score: 95 }
];

let totalScore = 0;
students.forEach(student => {
    totalScore += student.score;
    console.log(`${student.name}의 점수: ${student.score}`);
});

const averageScore = totalScore / students.length;
console.log(`평균 점수: ${averageScore}`);

// 출력:
// 김철수의 점수: 90
// 이영희의 점수: 85
// 박민수의 점수: 95
// 평균 점수: 90
```

## 4. thisArg 활용 예제
```javascript
class Counter {
    constructor() {
        this.count = 0;
    }

    add(array) {
        array.forEach(function(value) {
            this.count += value;
        }, this); // thisArg로 this를 전달
    }
}

const counter = new Counter();
counter.add([1, 2, 3, 4, 5]);
console.log(counter.count); // 출력: 15
```

## 5. DOM 요소 조작
```javascript
// HTML: <ul id="myList"><li>항목1</li><li>항목2</li><li>항목3</li></ul>

const listItems = document.querySelectorAll('#myList li');

listItems.forEach((item, index) => {
    item.textContent = `수정된 항목 ${index + 1}`;
    item.style.color = index % 2 === 0 ? 'blue' : 'red';
});
```

## 6. 에러 처리
```javascript
const numbers = [1, 2, 3, 4, 5];

numbers.forEach((number, index) => {
    try {
        if (number === 3) {
            throw new Error('3은 처리할 수 없습니다!');
        }
        console.log(`숫자 ${number} 처리 중...`);
    } catch (error) {
        console.error(`${index}번째 요소 처리 중 에러 발생:`, error.message);
    }
});

// 출력:
// 숫자 1 처리 중...
// 숫자 2 처리 중...
// 2번째 요소 처리 중 에러 발생: 3은 처리할 수 없습니다!
// 숫자 4 처리 중...
// 숫자 5 처리 중...
```

## 7. 배열 변환 예제
```javascript
const numbers = [1, 2, 3, 4, 5];
const doubled = [];

numbers.forEach(number => {
    doubled.push(number * 2);
});

console.log(doubled); // 출력: [2, 4, 6, 8, 10]
```

## 8. 중첩 배열 처리
```javascript
const matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];

matrix.forEach((row, i) => {
    row.forEach((element, j) => {
        console.log(`matrix[${i}][${j}] = ${element}`);
    });
});

// 출력:
// matrix[0][0] = 1
// matrix[0][1] = 2
// matrix[0][2] = 3
// matrix[1][0] = 4
// ...
``` 