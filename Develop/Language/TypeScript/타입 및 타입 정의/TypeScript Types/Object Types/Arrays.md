
# Arrays
- 여러 개의 값들을 순서대로 저장하는 데이터 구조입니다.
- 배열은 동일한 유형의 값을 담을 수 있는 인덱스로 접근할 수 있는 컬렉션입니다. 
- TypeScript에서 배열은 특정 유형(type)의 요소로 구성되며, 배열의 길이는 동적으로 확장할 수 있습니다.



# 주요 개념과 사용 방법
배열 선언하기
- 배열을 선언할 때는 유형[] 형태의 구문을 사용합니다. 
- 유형은 배열에 포함될 요소들의 유형을 나타냅니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
let names: string[] = ['John', 'Jane', 'Mike'];
```

배열 요소 접근하기
- 배열은 0부터 시작하는 인덱스를 사용하여 요소에 접근할 수 있습니다.
- 인덱스에 대괄호([])를 사용하여 접근하거나, 배열명[인덱스] 형태로 접근합니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
console.log(numbers[0]); // 출력: 1
console.log(numbers[2]); // 출력: 3
```


배열 길이
- 배열의 길이는 배열명.length를 통해 확인할 수 있습니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
console.log(numbers.length); // 출력: 5
```

배열 메서드
- 다양한 내장 메서드를 활용하여 배열을 조작하고 변경할 수 있습니다.
- 예를 들어, push(), pop(), slice(), splice(), concat() 등을 사용할 수 있습니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];

// push(): 배열의 끝에 요소를 추가합니다
numbers.push(6, 7);
console.log(numbers); // 출력: [1, 2, 3, 4, 5, 6, 7]

// pop(): 배열에서 마지막 요소를 제거하고 반환합니다
let lastNumber = numbers.pop();
console.log(lastNumber); // 출력: 7
console.log(numbers); // 출력: [1, 2, 3, 4, 5, 6]

// slice(): 배열의 일부분을 새 배열로 반환합니다
let subArray = numbers.slice(2, 4);
console.log(subArray); // 출력: [3, 4]

// splice(): 배열의 내용을 변경하여 요소를 제거, 교체 또는 추가합니다
numbers.splice(1, 2, 8, 9);
console.log(numbers); // 출력: [1, 8, 9, 4, 5, 6]

// concat(): 두 개 이상의 배열을 연결하여 새 배열을 반환합니다
let moreNumbers: number[] = [10, 11, 12];
let combinedArray = numbers.concat(moreNumbers);
console.log(combinedArray); // 출력: [1, 8, 9, 4, 5, 6, 10, 11, 12]
```

다차원 배열
- TypeScript에서는 다차원 배열도 지원됩니다.
- 이는 배열의 요소로 또 다른 배열을 포함하는 배열을 의미합니다.

```typescript
let matrix: number[][] = [[1, 2, 3], [4, 5, 6], [7, 8, 9]];
console.log(matrix[0][1]); // 출력: 2
```

* 배열은 데이터를 집합적으로 저장하고 조작하는 데 유용한 도구입니다. 
* 다양한 배열 메서드를 활용하여 데이터를 필터링, 변환, 정렬 등 다양한 작업을 수행할 수 있습니다.
* TypeScript는 배열의 유형을 추론하고 유형 검사를 수행하여 유효성을 보장합니다.