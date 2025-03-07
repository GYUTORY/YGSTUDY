자# TypeScript Tuples 개념 및 사용법

## ✨ TypeScript의 Tuple(튜플)이란?
TypeScript에서 **튜플(Tuple)**은 **길이와 타입이 고정된 배열**입니다.  
일반적인 배열과 달리, **각 요소의 타입이 사전에 정해져 있으며, 순서까지 고정**됩니다.

---

## 👉🏻 왜 튜플을 사용할까?
- 배열보다 **더 엄격한 타입 검사를 제공**하여, 특정 위치에 특정 타입만 허용할 수 있음
- 함수의 반환값을 **여러 개의 값으로 받고 싶을 때 유용**
- 구조적인 데이터를 다룰 때 **명확한 타입을 제공**

---

## 📌 기본적인 튜플 선언
```ts
// 문자열과 숫자를 포함하는 튜플 선언
let userInfo: [string, number];

// 값 할당 (순서와 타입을 정확히 맞춰야 함)
userInfo = ["홍길동", 30];  // ✅ 올바른 사용
// userInfo = [30, "홍길동"]; // ❌ 오류 발생 (순서가 다름)

// 튜플 값 접근
console.log(userInfo[0]); // "홍길동"
console.log(userInfo[1]); // 30
```

**✔️ 튜플을 선언하면, 반드시 지정된 타입과 순서에 맞춰 값을 할당해야 합니다.**

---

## 🎯 튜플의 다양한 활용법

### 1️⃣ **선언과 초기화 함께 하기**
```ts
let person: [string, number] = ["김철수", 28];
```
- 선언과 동시에 값을 할당하면 타입이 자동으로 적용됨

### 2️⃣ **선언 후 값 변경하기**
```ts
let user: [string, boolean];
user = ["관리자", true]; // ✅ 올바른 사용
// user = [false, "관리자"]; // ❌ 타입 순서 오류 발생
```
- 값 변경 시에도 반드시 선언된 타입과 순서를 유지해야 함

### 3️⃣ **튜플을 반환하는 함수**
```ts
// 여러 개의 값을 반환하는 함수
function getUser(): [string, number] {
    return ["김영희", 25];
}

let userData = getUser();
console.log(userData); // ["김영희", 25]
```
- **튜플을 사용하면 함수의 반환값이 명확해지고 가독성이 향상됨**

---

## 🚀 튜플과 배열의 차이점
| 구분 | 배열(Array) | 튜플(Tuple) |
|------|------------|-------------|
| **길이** | 가변적 | 고정됨 |
| **타입** | 동일한 타입 가능 | 각 요소의 타입이 다를 수 있음 |
| **인덱스 순서** | 순서 상관 없음 | 특정 위치에 특정 타입 필요 |

```ts
// 배열 예제
let numbers: number[] = [1, 2, 3, 4];

// 튜플 예제
let tupleExample: [string, number, boolean] = ["홍길동", 35, true];
```

---

## 🛠️ 튜플과 `push()` 문제
튜플은 고정된 길이를 갖지만, **`push()`를 사용하면 값을 추가할 수 있음**  
그러나, **추가된 값의 타입 검사는 제대로 이루어지지 않음**

```ts
let data: [string, number] = ["TypeScript", 2024];

data.push(100);  // 🚨 오류 발생하지 않음 (BUT 튜플 길이가 변경됨)
console.log(data); // ["TypeScript", 2024, 100] ❌ (원래 길이보다 많아짐)
```
- **💡 해결 방법**: `readonly` 키워드를 사용하여 값 변경을 방지할 수 있음

```ts
let fixedData: readonly [string, number] = ["TypeScript", 2024];
// fixedData.push(100); // ❌ 오류 발생 (읽기 전용)
```

---

## 🔥 튜플을 활용한 구조 분해 할당
튜플을 사용하면 **배열 구조 분해 할당(Destructuring)도 가능**

```ts
let person: [string, number] = ["홍길동", 30];

let [name, age] = person;  // 구조 분해 할당
console.log(name); // "홍길동"
console.log(age);  // 30
```
- **💡 객체 대신 튜플을 사용하면 메모리 절약이 가능**

---

## ✅ 튜플과 `enum` 함께 사용하기
튜플과 `enum`을 조합하면 **더 가독성 좋은 코드**를 작성할 수 있음

```ts
enum Role { Admin, User, Guest }

let member: [string, Role] = ["박지성", Role.Admin];

console.log(member); // ["박지성", 0]
```
- `enum`을 사용하면 숫자 대신 의미 있는 값을 가질 수 있음
