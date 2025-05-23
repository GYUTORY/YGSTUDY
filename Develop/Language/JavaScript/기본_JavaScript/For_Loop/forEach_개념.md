# JavaScript forEach 메서드

## forEach란?
`forEach`는 배열의 각 요소에 대해 주어진 함수를 실행하는 배열 메서드입니다. 배열의 모든 요소를 순회하면서 각 요소에 대해 콜백 함수를 실행합니다. 이는 전통적인 for 루프를 더 선언적이고 함수형 프로그래밍 스타일로 작성할 수 있게 해줍니다.

## 문법
```javascript
array.forEach(callback(currentValue[, index[, array]])[, thisArg])
```

### 매개변수
1. `callback`: 각 요소에 대해 실행할 함수로, 다음 세 가지 매개변수를 가질 수 있습니다:
   - `currentValue`: 처리할 현재 요소
   - `index` (선택사항): 처리할 현재 요소의 인덱스
   - `array` (선택사항): forEach를 호출한 배열

2. `thisArg` (선택사항): callback을 실행할 때 this로 사용할 값

## 기본 사용 예제
```javascript
// 기본적인 사용법
const numbers = [1, 2, 3, 4, 5];
numbers.forEach((number) => {
    console.log(number);
});

// 인덱스와 배열 사용
const fruits = ['apple', 'banana', 'orange'];
fruits.forEach((fruit, index, array) => {
    console.log(`${index}: ${fruit}`);
    console.log('전체 배열:', array);
});

// thisArg 사용 예제
class Counter {
    constructor() {
        this.count = 0;
    }
    
    increment() {
        this.count++;
    }
}

const counter = new Counter();
const items = [1, 2, 3];
items.forEach(function() {
    this.increment();
}, counter);
console.log(counter.count); // 3
```

## 특징
1. **반환값이 없음**: forEach는 undefined를 반환합니다. 따라서 체이닝이 불가능합니다.
   ```javascript
   const result = [1, 2, 3].forEach(x => x * 2);
   console.log(result); // undefined
   ```

2. **중간에 중단할 수 없음**: break나 return으로 루프를 중단할 수 없습니다.
   ```javascript
   // 이렇게 해도 중단되지 않습니다
   [1, 2, 3, 4, 5].forEach(num => {
       if (num === 3) return; // 중단되지 않고 계속 실행됨
       console.log(num);
   });
   ```

3. **원본 배열 변경 가능**: 콜백 함수 내에서 원본 배열을 변경할 수 있습니다.
   ```javascript
   const numbers = [1, 2, 3];
   numbers.forEach((num, index, arr) => {
       arr[index] = num * 2;
   });
   console.log(numbers); // [2, 4, 6]
   ```

## forEach vs for 루프
1. **가독성**: forEach가 더 명확하고 간결한 코드를 작성할 수 있게 해줍니다.
   ```javascript
   // for 루프
   const numbers = [1, 2, 3];
   for (let i = 0; i < numbers.length; i++) {
       console.log(numbers[i]);
   }

   // forEach
   numbers.forEach(number => console.log(number));
   ```

2. **this 바인딩**: forEach는 thisArg 매개변수를 통해 this 바인딩을 제어할 수 있습니다.

3. **성능**: 일반적인 for 루프가 미세하게 더 빠를 수 있습니다. 특히 대용량 데이터 처리 시 차이가 발생할 수 있습니다.

## 주의사항
1. **비동기 작업**: forEach는 비동기 작업을 기다리지 않습니다.
   ```javascript
   // 잘못된 사용
   const urls = ['url1', 'url2', 'url3'];
   urls.forEach(async url => {
       const response = await fetch(url);
       console.log(response);
   });
   console.log('완료!'); // 비동기 작업이 완료되기 전에 실행됨

   // 올바른 사용
   async function processUrls() {
       for (const url of urls) {
           const response = await fetch(url);
           console.log(response);
       }
   }
   ```

2. **희소 배열**: 빈 요소는 순회하지 않습니다.
   ```javascript
   const arr = [1, , 3];
   arr.forEach(x => console.log(x)); // 1, 3만 출력
   ```

3. **배열이 아닌 객체**: 배열이 아닌 객체에서는 사용할 수 없습니다.
   ```javascript
   const obj = { a: 1, b: 2 };
   // obj.forEach(x => console.log(x)); // TypeError
   ```

4. **중단이 필요한 경우**: some()이나 every() 메서드를 사용하는 것이 좋습니다.
   ```javascript
   // forEach로는 중단이 불가능
   [1, 2, 3, 4, 5].forEach(num => {
       if (num === 3) return; // 중단되지 않음
       console.log(num);
   });

   // some()으로 중단 가능
   [1, 2, 3, 4, 5].some(num => {
       if (num === 3) return true; // true를 반환하면 순회 중단
       console.log(num);
       return false;
   });
   ```

## 적절한 사용 사례
1. 배열의 각 요소에 대해 부수 효과(side effect)를 실행할 때
2. 간단한 데이터 변환이나 로깅
3. DOM 요소 조작
4. 다른 배열 메서드(map, filter 등)와 함께 사용할 때

## 부적절한 사용 사례
1. 비동기 작업이 필요한 경우
2. 중간에 순회를 중단해야 하는 경우
3. 반환값이 필요한 경우
4. 대용량 데이터 처리 시 성능이 중요한 경우 