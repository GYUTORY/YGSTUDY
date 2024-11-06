


// 클로저 사용
function outerFunction() {
    let outerVariable = 'I am from outer function';

    function innerFunction() {
        console.log(outerVariable); // 외부 변수에 접근
    }

    return innerFunction; // innerFunction을 반환
}

const closure = outerFunction(); // outerFunction 실행
closure(); // innerFunction 호출


// 클로저 미사용
function outerFunctionWithoutClosure(outerVariable) {
    function innerFunction(value) {
        console.log(value); // 매개변수를 통해 외부 변수에 접근
    }

    // innerFunction을 호출하면서 outerVariable을 전달
    innerFunction(outerVariable);
}

// 호출할 때 outerVariable의 값을 직접 전달
outerFunctionWithoutClosure('I am from outer function without closure'); // 출력: "I am from outer function without closure"