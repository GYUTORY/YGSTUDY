# JavaScript forEach 메서드

## forEach란?
`forEach`는 배열의 각 요소에 대해 주어진 함수를 실행하는 배열 메서드입니다. 배열의 모든 요소를 순회하면서 각 요소에 대해 콜백 함수를 실행합니다.

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

## 특징
1. **반환값이 없음**: forEach는 undefined를 반환합니다.
2. **중간에 중단할 수 없음**: break나 return으로 루프를 중단할 수 없습니다.
3. **원본 배열 변경 가능**: 콜백 함수 내에서 원본 배열을 변경할 수 있습니다.

## forEach vs for 루프
1. **가독성**: forEach가 더 명확하고 간결한 코드를 작성할 수 있게 해줍니다.
2. **this 바인딩**: forEach는 thisArg 매개변수를 통해 this 바인딩을 제어할 수 있습니다.
3. **성능**: 일반적인 for 루프가 미세하게 더 빠를 수 있습니다.

## 주의사항
1. 비동기 작업에서는 주의가 필요합니다.
2. 희소 배열의 경우 빈 요소는 순회하지 않습니다.
3. 배열이 아닌 객체에서는 사용할 수 없습니다.
4. 중간에 순회를 중단할 수 없으므로, 중단이 필요한 경우 some()이나 every() 메서드를 사용하는 것이 좋습니다. 