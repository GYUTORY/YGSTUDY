# JavaScript Map

## Map이란?
`Map`은 키-값 쌍을 저장하는 객체로, 어떤 데이터 타입도 키로 사용할 수 있습니다. 일반 객체와 달리 Map은 키의 타입이 문자열이나 심볼로 제한되지 않습니다.

## 문법
```javascript
new Map([iterable])
```

### 주요 메서드
1. **기본 조작**
   - `set(key, value)`: 키-값 쌍 추가
   - `get(key)`: 키에 해당하는 값 반환
   - `has(key)`: 키 존재 여부 확인
   - `delete(key)`: 키-값 쌍 삭제
   - `clear()`: 모든 키-값 쌍 삭제

2. **반복 메서드**
   - `keys()`: 모든 키를 반환
   - `values()`: 모든 값을 반환
   - `entries()`: 모든 [키, 값] 쌍을 반환
   - `forEach()`: 각 요소에 대해 콜백 함수 실행

### 속성
- `size`: Map의 키-값 쌍 개수 반환

## Map vs 일반 객체
1. **키의 타입**
   - Map: 모든 타입 가능
   - 객체: 문자열과 심볼만 가능

2. **크기 확인**
   - Map: size 속성으로 쉽게 확인
   - 객체: Object.keys(obj).length 등 필요

3. **순회**
   - Map: 삽입 순서 보장, 반복 메서드 내장
   - 객체: 순서 보장되지 않음

## 특징
1. **키 타입의 자유로움**: 함수, 객체, 원시값 등 모든 값을 키로 사용 가능
2. **순서 보장**: 삽입된 순서대로 순회 가능
3. **성능**: 잦은 키-값 쌍의 추가/제거에 최적화
4. **직렬화/역직렬화**: JSON.stringify()로 직접 직렬화 불가

## 직렬화와 역직렬화
Map 객체는 `JSON.stringify()`를 사용하여 직접 직렬화할 수 없습니다. 이는 Map이 일반 객체가 아닌 특별한 내장 객체이기 때문입니다. Map을 JSON으로 변환하려면 다음과 같은 방법을 사용해야 합니다:

### 1. Map을 배열로 변환 후 직렬화
```javascript
const map = new Map([
  ['key1', 'value1'],
  ['key2', 'value2']
]);

// Map을 배열로 변환
const array = Array.from(map);
// 또는
const array2 = [...map];

// JSON으로 직렬화
const jsonString = JSON.stringify(array);
```

### 2. Map을 객체로 변환 후 직렬화
```javascript
const map = new Map([
  ['key1', 'value1'],
  ['key2', 'value2']
]);

// Map을 객체로 변환
const obj = Object.fromEntries(map);

// JSON으로 직렬화
const jsonString = JSON.stringify(obj);
```

### 3. 역직렬화 (JSON에서 Map으로 변환)
```javascript
// JSON 문자열을 배열로 파싱
const array = JSON.parse(jsonString);

// 배열을 Map으로 변환
const map = new Map(array);

// 또는 객체에서 Map으로 변환
const obj = JSON.parse(jsonString);
const map = new Map(Object.entries(obj));
```

### 주의사항
1. Map의 키가 객체나 함수인 경우, 직렬화 과정에서 이 정보가 손실될 수 있습니다.
2. 순환 참조(circular reference)가 있는 경우 직렬화가 실패할 수 있습니다.
3. Map의 순서는 직렬화/역직렬화 과정에서 보존됩니다.

## 주의사항
1. NaN도 키로 사용 가능 (일반 객체와 다름)
2. 키 비교는 sameValueZero 알고리즘 사용
3. 체이닝 가능 (set 메서드가 Map 객체 반환)
4. 직렬화 시 별도 처리 필요내용이 너무 부실해 자세하게 좀 설명해줘 