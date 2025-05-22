// 1. 기본적인 화살표 함수 문법
const add = (a, b) => a + b;
console.log(add(5, 3)); // 8

// 2. 매개변수가 하나일 때는 괄호 생략 가능
const square = x => x * x;
console.log(square(4)); // 16

// 3. 매개변수가 없을 때는 빈 괄호 필요
const sayHello = () => console.log('Hello!');
sayHello(); // Hello!

// 4. 여러 줄의 코드가 필요할 때는 중괄호와 return 필요
const calculate = (a, b) => {
    const sum = a + b;
    const product = a * b;
    return { sum, product };
};
console.log(calculate(3, 4)); // { sum: 7, product: 12 }

// 5. this 바인딩 차이
{
    let value = 32;
    const exampleObj = {
        value: 42,
        regularFunction: function() {
            console.log(this.value); // 42
        },
        arrowFunction: () => {
            console.log(value); // 32
        }
    };

    exampleObj.regularFunction(); // 42
    exampleObj.arrowFunction(); // 32
}

// 6. 화살표 함수와 콜백
const numbers = [1, 2, 3, 4, 5];

// 일반 함수를 사용한 map
const doubled1 = numbers.map(function(num) {
    return num * 2;
});

// 화살표 함수를 사용한 map
const doubled2 = numbers.map(num => num * 2);

console.log(doubled1); // [2, 4, 6, 8, 10]
console.log(doubled2); // [2, 4, 6, 8, 10]

// 7. 화살표 함수와 Promise
const fetchData = () => {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            resolve('데이터를 성공적으로 가져왔습니다!');
        }, 1000);
    });
};

fetchData()
    .then(data => console.log(data))
    .catch(error => console.error(error));

// 8. 화살표 함수와 이벤트 핸들러
const button = {
    clicked: false,
    click: function() {
        this.clicked = true;
        console.log('버튼이 클릭되었습니다!');
    }
};

// 9. 화살표 함수의 제한사항
// - arguments 객체를 사용할 수 없음
// - 생성자로 사용할 수 없음 (new 키워드 사용 불가)
// - prototype 속성이 없음

const regularFunction = function() {
    console.log(arguments); // [1, 2, 3]
};

const arrowFunction = () => {
    // console.log(arguments); // ReferenceError: arguments is not defined
};

regularFunction(1, 2, 3);
arrowFunction(1, 2, 3);
