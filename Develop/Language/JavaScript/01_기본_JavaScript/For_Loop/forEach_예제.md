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
### 설명
- `forEach`는 배열의 각 요소를 순차적으로 순회하는 메서드입니다.
- 콜백 함수는 최대 3개의 매개변수를 받을 수 있습니다:
  1. `fruit`: 현재 처리 중인 배열의 요소
  2. `index`: 현재 요소의 인덱스 (0부터 시작)
  3. `array`: forEach를 호출한 원본 배열 (이 예제에서는 사용하지 않음)
- `index + 1`을 사용하여 1부터 시작하는 번호를 출력합니다.

## 2. 배열 요소의 합계 계산
```javascript
const numbers = [1, 2, 3, 4, 5];
let sum = 0;

numbers.forEach(number => {
    sum += number;
});

console.log(`합계: ${sum}`); // 출력: 합계: 15
```
### 설명
- 배열의 모든 숫자를 더하는 간단한 예제입니다.
- `sum` 변수를 초기화하고, 각 요소를 순회하면서 누적합니다.
- 화살표 함수를 사용하여 간단하게 표현했습니다.
- 이 예제는 `reduce` 메서드로도 구현할 수 있지만, `forEach`가 더 직관적입니다.

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
### 설명
- 객체를 포함하는 배열을 처리하는 예제입니다.
- 각 학생 객체에서 `name`과 `score` 속성에 접근합니다.
- 총점을 계산하고 평균을 구하는 과정을 보여줍니다.
- 객체의 속성에 접근할 때는 점(.) 표기법을 사용합니다.

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
### 설명
- `forEach`의 두 번째 매개변수인 `thisArg`를 사용하는 예제입니다.
- `thisArg`는 콜백 함수 내부의 `this` 값을 지정합니다.
- 일반 함수에서는 `this`가 전역 객체를 가리키므로, 클래스의 `this`를 유지하기 위해 `thisArg`를 사용합니다.
- 화살표 함수를 사용하면 `thisArg`가 필요 없지만, 이 예제는 `this` 바인딩을 설명하기 위해 일반 함수를 사용했습니다.

## 5. DOM 요소 조작
```javascript
// HTML: <ul id="myList"><li>항목1</li><li>항목2</li><li>항목3</li></ul>

const listItems = document.querySelectorAll('#myList li');

listItems.forEach((item, index) => {
    item.textContent = `수정된 항목 ${index + 1}`;
    item.style.color = index % 2 === 0 ? 'blue' : 'red';
});
```
### 설명
- DOM 요소를 조작하는 실제 사용 예제입니다.
- `querySelectorAll`은 NodeList를 반환하며, 이는 `forEach`를 사용할 수 있습니다.
- 각 리스트 항목의 텍스트를 변경하고 스타일을 적용합니다.
- 인덱스를 사용하여 짝수/홀수 항목에 다른 색상을 적용합니다.

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
### 설명
- `forEach` 내부에서 에러를 처리하는 방법을 보여줍니다.
- `try-catch` 블록을 사용하여 각 요소 처리 중 발생할 수 있는 에러를 캐치합니다.
- 에러가 발생해도 `forEach`는 계속 실행되며, 다음 요소를 처리합니다.
- 이는 `forEach`의 중요한 특징으로, 한 요소의 에러가 전체 순회를 중단시키지 않습니다.

## 7. 배열 변환 예제
```javascript
const numbers = [1, 2, 3, 4, 5];
const doubled = [];

numbers.forEach(number => {
    doubled.push(number * 2);
});

console.log(doubled); // 출력: [2, 4, 6, 8, 10]
```
### 설명
- 배열의 각 요소를 변환하여 새로운 배열을 만드는 예제입니다.
- `map` 메서드로도 구현할 수 있지만, `forEach`를 사용한 방법을 보여줍니다.
- 빈 배열을 생성하고 `push` 메서드로 변환된 요소를 추가합니다.
- 각 숫자를 2배로 만드는 간단한 변환을 수행합니다.

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
### 설명
- 2차원 배열(행렬)을 처리하는 예제입니다.
- 외부 `forEach`는 각 행을 순회합니다.
- 내부 `forEach`는 각 행의 요소를 순회합니다.
- `i`와 `j` 인덱스를 사용하여 행과 열의 위치를 표시합니다.
- 이중 중첩 구조를 통해 2차원 데이터를 효과적으로 처리할 수 있습니다.

## forEach의 주요 특징
1. **원본 배열 변경**: `forEach`는 원본 배열을 직접 수정할 수 있습니다.
2. **반환값**: `forEach`는 항상 `undefined`를 반환합니다.
3. **중단 불가**: `forEach`는 `break`나 `return`으로 중단할 수 없습니다. 중단이 필요한 경우 `for...of`나 `for` 루프를 사용해야 합니다.
4. **비동기 처리**: `forEach`는 비동기 작업을 순차적으로 처리하지 않습니다. 비동기 작업이 필요한 경우 `for...of`와 `async/await`를 사용하는 것이 좋습니다.
5. **성능**: 대규모 배열에서는 `for` 루프가 더 나은 성능을 보일 수 있습니다. 