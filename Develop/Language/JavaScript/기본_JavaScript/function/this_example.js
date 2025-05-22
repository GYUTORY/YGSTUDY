// 1. 일반 함수에서의 this
const exampleObj = {
    value: 42,
    regularFunction: function() {
        const self = this; // this를 보존하기 위해 self에 할당
        setTimeout(function() {
            console.log('일반 함수 내부 this:', this); // window/global 객체를 가리킴
            console.log('self를 통한 접근:', self.value); // 42
        }, 1000);
    }
};

// 2. 화살표 함수에서의 this
const arrowExampleObj = {
    value: 42,
    arrowFunction: function() {
        setTimeout(() => {
            console.log('화살표 함수 내부 this:', this); // 상위 스코프의 this를 가리킴
            console.log('this.value:', this.value); // 42
        }, 1000);
    }
};

// 3. 메서드 호출에서의 this
const person = {
    name: 'John',
    greet: function() {
        console.log('안녕하세요, ' + this.name + '입니다!');
    }
};

// 4. 생성자 함수에서의 this
function Person(name) {
    this.name = name;
    this.sayHello = function() {
        console.log('안녕하세요, ' + this.name + '입니다!');
    };
}

// 5. 이벤트 핸들러에서의 this
const button = {
    text: '클릭하세요',
    click: function() {
        console.log('버튼 텍스트:', this.text);
    }
};

// 6. call, apply, bind를 사용한 this 바인딩
const user = {
    name: 'Alice',
    sayHi: function(greeting) {
        console.log(greeting + ', ' + this.name + '!');
    }
};

// 실행 예시
console.log('=== 일반 함수 예제 ===');
exampleObj.regularFunction();

console.log('\n=== 화살표 함수 예제 ===');
arrowExampleObj.arrowFunction();

console.log('\n=== 메서드 호출 예제 ===');
person.greet();

console.log('\n=== 생성자 함수 예제 ===');
const john = new Person('John');
john.sayHello();

console.log('\n=== 이벤트 핸들러 예제 ===');
button.click();

console.log('\n=== call, apply, bind 예제 ===');
const greeting = '안녕하세요';
user.sayHi.call({ name: 'Bob' }, greeting);
user.sayHi.apply({ name: 'Charlie' }, [greeting]);
const boundSayHi = user.sayHi.bind({ name: 'David' });
boundSayHi(greeting);
