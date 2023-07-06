// 명령형 코드와 함수형 코드를 준비해보자.. 너무 어렵다

// 명령형 코드

// 리스트에서 홀수를 length 만큼 뽑아서 제곱한 후 모두 더하기
function command_f(list, length) {
    let i = 0;
    let acc = 0;
    for (const a of list) {
        if (a % 2) {
            acc = acc + a * a
            if (++i === length) break;
        }
    }
    console.log(acc);
}

function command_main() {
    command_f([1, 2, 3, 4, 5], 1)
    command_f([1, 2, 3, 4, 5], 2)
    command_f([1, 2, 3, 4, 5], 3)
}

// command_main();


// 함수형 코드
// function*은 JavaScript에서 제너레이터 함수를 선언하기 위한 문법입니다.
// 제너레이터 함수는 일반 함수와는 다르게 동작하며, 함수 실행 도중에 일시적으로 중지하고 다시 시작할 수 있는 기능을 제공
// filter 함수: 주어진 함수(f)에 대해 iterable(iter)에서 조건을 만족하는 요소를 필터링하여 반환
function *filter(f, iter) {
    for (const a of iter) {
        // yield 키워드는 함수의 실행을 일시 중단하고 현재 값을 반환
        if (f(a)) yield a;
    }
}

// map 함수: 주어진 함수(f)를 iterable(iter)의 각 요소에 적용하여 새로운 값을 생성하여 반환
function *map(f, iter) {
    for (const a of iter) {
        yield f(a);
    }
}

// take 함수: iterable(iter)에서 지정한 개수(length) 만큼의 요소를 반환
function take(length, iter) {
    let res = [];
    for (const a of iter) {
        res.push(a);
        if (res.length == length) return res;
    }
    return res;
}

// reduce 함수: iterable(iter)의 요소를 주어진 함수(f)를 사용하여 하나의 값으로 축소하여 반환
function reduce(f, acc, iter) {
    for (const a of iter) {
        acc = f(acc, a);
    }
    return acc;
}


// add 함수: 두 개의 값을 더하는 함수
const add = (a, b) => a + b;

const go = (a, ...fs) => reduce((a, f) => f(a), a, fs);

go(10, a => a + 1, a => a + 10, console.log);


// f 함수: 주어진 리스트(list)에서 홀수를 length만큼 필터링하여 제곱한 후 모두 더한 값을 반환
function f(list, length) {
    return reduce(
        add,
        0,
        take(length, map((a) => a * a, filter((a) => a % 2, list)))
    );
}

// function_main 함수: f 함수를 테스트하기 위해 예시 입력으로 실행하여 결과를 출력
function function_main() {
    console.log(f([1, 2, 3, 4, 5], 1));
    console.log(f([1, 2, 3, 4, 5], 2));
    console.log(f([1, 2, 3, 4, 5], 3));
}

function_main();

