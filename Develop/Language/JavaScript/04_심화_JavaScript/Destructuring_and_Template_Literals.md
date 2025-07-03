# JavaScript 디스트럭처링과 템플릿 리터럴

> 💡 **이 글을 읽기 전에 알아야 할 것들**
> - JavaScript 기본 문법 (변수, 배열, 객체)
> - ES6 문법에 대한 기본 이해

---

## 📚 목차
1. [디스트럭처링이란?](#디스트럭처링이란)
2. [배열 디스트럭처링](#배열-디스트럭처링)
3. [객체 디스트럭처링](#객체-디스트럭처링)
4. [템플릿 리터럴이란?](#템플릿-리터럴이란)
5. [실전 활용 예제](#실전-활용-예제)

---

## 🎯 디스트럭처링이란?

**디스트럭처링(Destructuring)**은 "구조 분해 할당"이라고도 불립니다. 쉽게 말해서 **복잡한 데이터 구조(배열, 객체)를 개별 변수로 분해해서 사용하는 방법**입니다.

### 왜 디스트럭처링을 사용할까요?

**기존 방식 (디스트럭처링 없이):**
```javascript
const person = { name: '김철수', age: 25, city: '서울' };

// 각 값을 개별 변수로 할당하려면...
const name = person.name;
const age = person.age;
const city = person.city;

console.log(name); // 김철수
console.log(age);  // 25
console.log(city); // 서울
```

**디스트럭처링 사용:**
```javascript
const person = { name: '김철수', age: 25, city: '서울' };

// 한 줄로 모든 값을 변수에 할당!
const { name, age, city } = person;

console.log(name); // 김철수
console.log(age);  // 25
console.log(city); // 서울
```

> 🎉 **장점**: 코드가 훨씬 간결해지고, 가독성이 좋아집니다!

---

## 📦 배열 디스트럭처링

배열의 각 요소를 순서대로 변수에 할당하는 방법입니다.

### 기본 사용법

```javascript
// 배열 생성
const fruits = ['사과', '바나나', '오렌지'];

// 배열의 각 요소를 변수에 할당
const [first, second, third] = fruits;

console.log(first);  // 사과
console.log(second); // 바나나
console.log(third);  // 오렌지
```

### 실용적인 예제들

#### 1. 필요한 요소만 가져오기
```javascript
const colors = ['빨강', '파랑', '초록', '노랑', '보라'];

// 첫 번째와 세 번째 요소만 필요하다면
const [primary, , tertiary] = colors;

console.log(primary);  // 빨강
console.log(tertiary); // 초록
```

#### 2. 기본값 설정하기
```javascript
const scores = [85, 92];

// 세 번째 점수가 없을 때 기본값 설정
const [math, english, science = 0] = scores;

console.log(math);    // 85
console.log(english); // 92
console.log(science); // 0 (기본값)
```

#### 3. 나머지 요소 모두 가져오기 (Rest 연산자)
```javascript
const numbers = [1, 2, 3, 4, 5];

// 첫 번째는 따로, 나머지는 배열로
const [first, ...rest] = numbers;

console.log(first); // 1
console.log(rest);  // [2, 3, 4, 5]
```

#### 4. 변수 값 교환하기
```javascript
let a = 10;
let b = 20;

// 기존 방식
// let temp = a;
// a = b;
// b = temp;

// 디스트럭처링으로 한 줄에!
[a, b] = [b, a];

console.log(a); // 20
console.log(b); // 10
```

---

## 🏠 객체 디스트럭처링

객체의 프로퍼티를 변수로 추출하는 방법입니다.

### 기본 사용법

```javascript
const user = {
  name: '이영희',
  age: 28,
  email: 'younghee@example.com'
};

// 객체의 프로퍼티를 변수로 추출
const { name, age, email } = user;

console.log(name);  // 이영희
console.log(age);   // 28
console.log(email); // younghee@example.com
```

### 실용적인 예제들

#### 1. 프로퍼티 이름을 다른 변수명으로 사용하기 (별칭)
```javascript
const product = {
  name: '노트북',
  price: 1500000,
  brand: '삼성'
};

// name을 productName으로, price를 productPrice로 사용
const { name: productName, price: productPrice } = product;

console.log(productName);  // 노트북
console.log(productPrice); // 1500000
```

#### 2. 기본값 설정하기
```javascript
const student = {
  name: '박민수',
  grade: 'A'
};

// address가 없으면 기본값 설정
const { name, grade, address = '주소 없음' } = student;

console.log(name);    // 박민수
console.log(grade);   // A
console.log(address); // 주소 없음
```

#### 3. 중첩된 객체 디스트럭처링
```javascript
const company = {
  name: '테크컴퍼니',
  address: {
    city: '서울',
    district: '강남구',
    street: '테헤란로 123'
  },
  employees: 100
};

// 중첩된 객체도 한 번에 추출
const { 
  name, 
  address: { city, district }, 
  employees 
} = company;

console.log(name);     // 테크컴퍼니
console.log(city);     // 서울
console.log(district); // 강남구
console.log(employees); // 100
```

#### 4. 함수 매개변수에서 사용하기
```javascript
// 기존 방식
function printUserInfo(user) {
  console.log(`이름: ${user.name}, 나이: ${user.age}`);
}

// 디스트럭처링 사용
function printUserInfo({ name, age }) {
  console.log(`이름: ${name}, 나이: ${age}`);
}

const user = { name: '김철수', age: 25 };
printUserInfo(user); // 이름: 김철수, 나이: 25
```

---

## 📝 템플릿 리터럴이란?

**템플릿 리터럴(Template Literal)**은 ES6에서 도입된 새로운 문자열 작성 방식입니다. 기존의 따옴표(`"`, `'`) 대신 **백틱(`)**을 사용합니다.

### 왜 템플릿 리터럴을 사용할까요?

**기존 방식 (문자열 연결):**
```javascript
const name = '김철수';
const age = 25;

// 문자열 연결로 복잡하고 읽기 어려움
const message = '안녕하세요, ' + name + '님! 당신은 ' + age + '살입니다.';
console.log(message); // 안녕하세요, 김철수님! 당신은 25살입니다.
```

**템플릿 리터럴 사용:**
```javascript
const name = '김철수';
const age = 25;

// 훨씬 간결하고 읽기 쉬움
const message = `안녕하세요, ${name}님! 당신은 ${age}살입니다.`;
console.log(message); // 안녕하세요, 김철수님! 당신은 25살입니다.
```

### 템플릿 리터럴의 강력한 기능들

#### 1. 변수 삽입 (Interpolation)
```javascript
const product = '노트북';
const price = 1500000;
const discount = 0.1;

const totalPrice = price * (1 - discount);
const receipt = `
구매 상품: ${product}
정가: ${price.toLocaleString()}원
할인율: ${discount * 100}%
최종 가격: ${totalPrice.toLocaleString()}원
`;

console.log(receipt);
/*
구매 상품: 노트북
정가: 1,500,000원
할인율: 10%
최종 가격: 1,350,000원
*/
```

#### 2. 여러 줄 문자열
```javascript
// 기존 방식 (줄바꿈이 어려움)
const oldWay = '첫 번째 줄\n두 번째 줄\n세 번째 줄';

// 템플릿 리터럴 (자연스러운 줄바꿈)
const newWay = `
첫 번째 줄
두 번째 줄
세 번째 줄
`;

console.log(newWay);
```

#### 3. 표현식 삽입
```javascript
const a = 10;
const b = 20;

// 수학 연산도 가능
const result = `${a} + ${b} = ${a + b}`;
console.log(result); // 10 + 20 = 30

// 조건문도 가능
const score = 85;
const grade = `점수: ${score}, 등급: ${score >= 90 ? 'A' : score >= 80 ? 'B' : 'C'}`;
console.log(grade); // 점수: 85, 등급: B
```

#### 4. 함수 호출 결과 삽입
```javascript
function getCurrentTime() {
  return new Date().toLocaleTimeString();
}

function formatPrice(price) {
  return price.toLocaleString() + '원';
}

const product = {
  name: '스마트폰',
  price: 800000
};

const message = `
현재 시간: ${getCurrentTime()}
상품명: ${product.name}
가격: ${formatPrice(product.price)}
`;

console.log(message);
// 현재 시간: 오후 2:30:45
// 상품명: 스마트폰
// 가격: 800,000원
```

---

## 🚀 실전 활용 예제

### 1. API 응답 데이터 처리
```javascript
// 서버에서 받은 사용자 데이터
const apiResponse = {
  success: true,
  data: {
    user: {
      id: 1,
      name: '김철수',
      email: 'kim@example.com',
      profile: {
        avatar: 'https://example.com/avatar.jpg',
        bio: '안녕하세요!'
      }
    }
  }
};

// 디스트럭처링으로 필요한 데이터만 추출
const {
  data: {
    user: { name, email, profile: { avatar, bio } }
  }
} = apiResponse;

// 템플릿 리터럴로 사용자 정보 출력
const userInfo = `
👤 사용자 정보
이름: ${name}
이메일: ${email}
프로필 사진: ${avatar}
소개: ${bio}
`;

console.log(userInfo);
```

### 2. 함수에서 여러 값 반환하기
```javascript
function calculateCircle(radius) {
  const area = Math.PI * radius * radius;
  const circumference = 2 * Math.PI * radius;
  
  return { area, circumference };
}

function calculateRectangle(width, height) {
  const area = width * height;
  const perimeter = 2 * (width + height);
  
  return { area, perimeter };
}

// 디스트럭처링으로 결과 받기
const { area: circleArea, circumference } = calculateCircle(5);
const { area: rectArea, perimeter } = calculateRectangle(4, 6);

// 템플릿 리터럴로 결과 출력
const result = `
📐 도형 계산 결과

🔵 원 (반지름: 5)
면적: ${circleArea.toFixed(2)}
둘레: ${circumference.toFixed(2)}

🟦 직사각형 (가로: 4, 세로: 6)
면적: ${rectArea}
둘레: ${perimeter}
`;

console.log(result);
```

### 3. 배열과 객체를 함께 활용하기
```javascript
const students = [
  { name: '김철수', scores: [85, 90, 78] },
  { name: '이영희', scores: [92, 88, 95] },
  { name: '박민수', scores: [76, 85, 80] }
];

// 각 학생의 평균 점수 계산
const studentAverages = students.map(({ name, scores }) => {
  const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  return { name, average: average.toFixed(1) };
});

// 결과를 템플릿 리터럴로 출력
const report = `
📊 학생 성적 보고서

${studentAverages.map(({ name, average }) => 
  `• ${name}: 평균 ${average}점`
).join('\n')}

🏆 최고 성적: ${Math.max(...studentAverages.map(s => parseFloat(s.average)))}점
`;

console.log(report);
```

---

## 💡 핵심 정리

### 디스트럭처링
- **배열 디스트럭처링**: `const [a, b, c] = array`
- **객체 디스트럭처링**: `const { name, age } = object`
- **기본값 설정**: `const { name = '기본값' } = object`
- **별칭 사용**: `const { name: userName } = object`

