---
title: Rust 소유권과 빌림, 라이프타임
tags:
  - Rust
  - Ownership
  - Borrowing
  - Lifetime
  - Memory
updated: 2026-06-12
---

# Rust 소유권과 빌림, 라이프타임

Rust를 처음 만지면 컴파일러가 거절하는 코드의 절반이 소유권과 빌림 규칙 위반이다. GC가 있는 언어에서 넘어오면 "왜 멀쩡한 코드를 막지?" 싶은 순간이 반복된다. 막상 규칙을 이해하고 나면 그 거절이 런타임에 터질 메모리 버그를 컴파일 타임에 잡아준 거라는 걸 알게 된다. 여기서는 규칙 자체보다 borrow checker가 실제로 어떤 코드를 막는지, 그 에러 메시지를 어떻게 읽어야 하는지를 다룬다.

## 소유권: 값에는 주인이 하나뿐이다

Rust의 모든 값은 그 값을 소유하는 변수가 정확히 하나 있다. 소유자가 스코프를 벗어나면 그 값은 즉시 해제된다. `free()`를 직접 호출하지도 않고 GC가 나중에 정리하는 것도 아니다. 스코프 끝의 `}`가 곧 해제 지점이다.

```rust
fn main() {
    let s = String::from("hello"); // s가 힙에 할당된 문자열을 소유
    // s 사용
} // 여기서 s의 소유 데이터가 drop, 힙 메모리 해제
```

`String`은 힙에 데이터를 두고 스택에는 포인터·길이·용량을 둔다. 소유자가 사라지면 `Drop` 트레이트의 `drop`이 호출되면서 힙 메모리를 반환한다. C++의 RAII와 같은 개념인데, Rust는 이걸 언어 차원에서 강제한다.

### move semantics: 대입은 복사가 아니라 이동이다

GC 언어에 익숙하면 여기서 처음 발이 걸린다. 변수를 다른 변수에 대입하면 값이 복사되는 게 아니라 소유권이 넘어간다.

```rust
let s1 = String::from("hello");
let s2 = s1;        // 소유권이 s1 -> s2로 이동(move)
println!("{}", s1); // 컴파일 에러
```

에러 메시지는 이렇게 나온다.

```
error[E0382]: borrow of moved value: `s1`
  --> src/main.rs:4:20
   |
2  |     let s1 = String::from("hello");
   |         -- move occurs because `s1` has type `String`,
   |            which does not implement the `Copy` trait
3  |     let s2 = s1;
   |              -- value moved here
4  |     println!("{}", s1);
   |                    ^^ value borrowed here after move
```

`s2 = s1`에서 힙 데이터를 통째로 복사하면 큰 문자열은 비싸다. 그래서 Rust는 스택의 포인터만 옮기고 `s1`을 무효화한다. 만약 둘 다 살아있게 두면 스코프가 끝날 때 같은 힙 메모리를 두 번 해제하는 double free가 난다. move는 이걸 원천 차단한다. 한쪽으로 소유권을 넘긴 순간 다른 쪽은 더 못 쓴다.

함수 호출도 같다. 값을 인자로 넘기면 소유권이 함수 안으로 이동한다.

```rust
fn take(s: String) {
    println!("{}", s);
} // 여기서 s drop

fn main() {
    let s = String::from("hi");
    take(s);            // 소유권이 take로 이동
    // println!("{}", s); // 에러: s는 이미 이동됨
}
```

이 때문에 "함수에 값을 넘겼더니 그 뒤로 못 쓰게 됐다"는 상황을 자주 만난다. 호출한 쪽에서도 계속 쓰고 싶으면 소유권을 넘기지 말고 빌려줘야 한다. 그게 빌림(borrowing)이다.

## 빌림: 소유권은 그대로 두고 참조만 넘긴다

`&`를 붙이면 소유권을 넘기지 않고 값을 참조하는 빌림이 된다.

```rust
fn calc_len(s: &String) -> usize {
    s.len()
} // s는 참조일 뿐이라 drop되지 않음

fn main() {
    let s = String::from("hello");
    let len = calc_len(&s); // s를 빌려줌, 소유권은 main이 유지
    println!("{} {}", s, len); // s 그대로 사용 가능
}
```

빌림에는 두 종류가 있고, 이게 Rust 메모리 안전성의 핵심 규칙이다.

- 불변 빌림 `&T`: 읽기만 가능. 동시에 여러 개 존재할 수 있다.
- 가변 빌림 `&mut T`: 읽기·쓰기 가능. 한 번에 하나만 존재할 수 있고, 그동안 불변 빌림도 같이 못 둔다.

한 문장으로 줄이면 "공유하면 불변, 변경하면 독점"이다. 같은 데이터를 여러 곳에서 읽는 건 안전하니 `&T`는 몇 개든 허용한다. 누군가 쓰는 중이면 다른 누구도 그 데이터를 건드리면 안 되니 `&mut T`는 독점이다.

```rust
let mut s = String::from("hello");

let r1 = &s;     // 불변 빌림
let r2 = &s;     // 불변 빌림 또 됨, OK
println!("{} {}", r1, r2);

let r3 = &mut s; // 가변 빌림
r3.push_str(" world");
```

위 코드가 통과하는 이유는 `r1`, `r2`가 마지막으로 쓰인 `println!` 이후로 더 안 쓰이기 때문이다. 컴파일러는 참조의 수명을 "선언부터 스코프 끝"이 아니라 "마지막 사용까지"로 본다. 이걸 NLL(Non-Lexical Lifetimes)이라고 한다. 옛날 Rust는 스코프 끝까지로 봐서 더 빡빡했는데 지금은 마지막 사용 시점 기준이라 한결 자연스럽다.

### borrow checker가 막는 첫 번째 패턴: 이중 가변 빌림

같은 값에 `&mut`를 두 개 동시에 만들면 막힌다.

```rust
let mut s = String::from("hello");
let r1 = &mut s;
let r2 = &mut s; // 에러
println!("{} {}", r1, r2);
```

```
error[E0499]: cannot borrow `s` as mutable more than once at a time
  --> src/main.rs:4:14
   |
3  |     let r1 = &mut s;
   |              ------ first mutable borrow occurs here
4  |     let r2 = &mut s;
   |              ^^^^^^ second mutable borrow occurs here
5  |     println!("{} {}", r1, r2);
   |                       -- first borrow later used here
```

가변 참조가 둘이면 한쪽이 데이터를 수정하는 동안 다른 쪽이 옛 상태를 가리킬 수 있다. C에서 흔한 data race나 iterator invalidation이 여기서 나온다. 실제로 컬렉션을 순회하면서 같은 컬렉션을 수정하려다 이 에러를 만나는 경우가 많다.

```rust
let mut v = vec![1, 2, 3];
for x in &v {           // v를 불변 빌림
    if *x == 2 {
        v.push(10);     // 에러: 순회 중 가변 빌림
    }
}
```

순회용 `&v`가 살아있는 동안 `v.push`는 `&mut v`를 요구한다. 불변 빌림과 가변 빌림이 겹치니 거절된다. 다른 언어라면 런타임에 컬렉션이 재할당되면서 순회 중인 포인터가 무효화돼 크래시가 나거나 이상한 값이 읽힌다. Rust는 이걸 컴파일 타임에 막는다. 해결은 보통 수정할 인덱스를 따로 모았다가 순회가 끝난 뒤 적용하는 식으로 푼다.

```rust
let mut v = vec![1, 2, 3];
let mut to_add = Vec::new();
for x in &v {
    if *x == 2 {
        to_add.push(10);
    }
}
v.extend(to_add); // 순회 끝난 뒤 수정
```

### borrow checker가 막는 두 번째 패턴: dangling reference

함수에서 지역 변수의 참조를 반환하려고 하면 막힌다.

```rust
fn dangle() -> &String {
    let s = String::from("hello");
    &s // 에러: s는 함수 끝에서 drop되는데 참조를 반환
}
```

```
error[E0106]: missing lifetime specifier
 --> src/main.rs:1:16
  |
1 | fn dangle() -> &String {
  |                ^ expected named lifetime parameter
  |
  = help: this function's return type contains a borrowed value,
          but there is no value for it to be borrowed from
```

`s`는 `dangle`이 끝나면 해제된다. 그 `s`를 가리키는 참조를 반환하면 호출한 쪽은 이미 해제된 메모리를 가리키게 된다. C에서 로컬 변수 주소를 반환하는 그 버그다. Rust는 컴파일을 거부한다. 이 경우 답은 간단하다. 참조 대신 값을 반환해서 소유권을 넘기면 된다.

```rust
fn no_dangle() -> String {
    let s = String::from("hello");
    s // 소유권을 호출자에게 이동
}
```

에러 메시지가 "missing lifetime specifier"라고 나오는 게 처음엔 헷갈린다. 컴파일러는 "이 반환 참조가 어디서 빌려온 건지 모르겠으니 라이프타임을 명시하라"고 말하는 건데, 실제 문제는 빌려올 출처 자체가 없다는 점이다. 라이프타임을 붙인다고 풀리는 게 아니라 설계를 바꿔야 하는 신호다.

## Copy와 Clone: 언제 move고 언제 복사인가

위에서 `String`은 대입하면 move된다고 했는데, 정수는 다르다.

```rust
let x = 5;
let y = x;          // 복사
println!("{} {}", x, y); // 둘 다 사용 가능, 에러 없음
```

`i32`처럼 스택에만 있고 크기가 고정된 타입은 `Copy` 트레이트를 구현한다. `Copy`인 타입은 대입할 때 move가 아니라 비트 복사가 일어나고 원본도 그대로 살아있다. 복사 비용이 싸고 별도 자원 해제가 필요 없기 때문에 굳이 소유권을 무효화할 이유가 없다.

`Copy`가 되는 타입은 정해져 있다. 정수·실수·불리언·문자(`char`), 그리고 이들로만 구성된 튜플·고정 크기 배열 정도다. 힙을 쓰는 `String`, `Vec`, `Box` 같은 타입은 `Copy`가 될 수 없다. 힙 데이터를 비트 복사로 얕게 복사하면 두 변수가 같은 힙을 가리키게 돼서 double free가 나기 때문이다.

`Clone`은 명시적 깊은 복사다. 힙 데이터까지 통째로 새로 복제한다.

```rust
let s1 = String::from("hello");
let s2 = s1.clone(); // 힙 데이터를 새로 복제, s1도 살아있음
println!("{} {}", s1, s2); // 둘 다 사용 가능
```

`Copy`와 `Clone`의 차이는 비용과 명시성이다. `Copy`는 암묵적이고 거의 공짜(스택 비트 복사), `Clone`은 `.clone()`을 직접 써야 하고 힙 복제라 비쌀 수 있다. `Copy`인 타입은 전부 `Clone`도 구현하지만 반대는 아니다.

### clone 남발 문제

Rust 입문자가 borrow checker 에러에 지쳐서 가장 많이 하는 게 일단 `.clone()`을 붙여 컴파일을 통과시키는 거다. 에러는 사라지지만 그때마다 힙 데이터를 통째로 복제하니 성능을 버린다.

```rust
fn process(data: Vec<i32>) -> i32 {
    data.iter().sum()
}

fn main() {
    let data = vec![1; 1_000_000];
    let a = process(data.clone()); // 100만 개 복제
    let b = process(data.clone()); // 또 100만 개 복제
    println!("{} {}", a, b);
}
```

`process`가 데이터를 읽기만 하는데도 소유권을 가져가니 호출할 때마다 `clone`해야 한다. 함수 시그니처를 `&Vec<i32>`나 `&[i32]`로 바꾸면 복제 없이 빌려주기만 하면 된다.

```rust
fn process(data: &[i32]) -> i32 {
    data.iter().sum()
}

fn main() {
    let data = vec![1; 1_000_000];
    let a = process(&data); // 복제 없음
    let b = process(&data); // 복제 없음
    println!("{} {}", a, b);
}
```

`clone`이 항상 나쁜 건 아니다. 정말 독립된 사본이 필요하거나, 빌림으로 풀면 라이프타임이 지나치게 복잡해져서 코드가 읽기 힘들어질 때는 의도적으로 `clone` 한 번 쓰는 게 낫다. 문제는 "왜 복제하는지" 모른 채 에러를 끄려고 기계적으로 붙이는 경우다. `clone`을 쓸 때는 이게 진짜 새 사본이 필요한 건지, 아니면 함수 시그니처를 참조로 바꾸면 사라질 복제인지 한 번 따져봐야 한다.

매개변수 타입을 고를 때 기준은 단순하다. 함수 안에서 값을 읽기만 하면 `&T`, 수정해야 하면 `&mut T`, 소유권을 함수가 가져가서 보관하거나 소비해야 하면 `T`로 받는다. 대부분의 함수는 읽기만 하므로 `&T`가 기본값이 된다.

## 라이프타임: 참조가 언제까지 유효한가

라이프타임은 참조가 가리키는 데이터가 살아있는 기간이다. 대부분의 경우 컴파일러가 알아서 추론하기 때문에 직접 쓸 일이 없다. 표기를 강제당하는 건 컴파일러가 추론에 실패하는 특정 상황뿐이다.

가장 흔한 건 함수가 참조를 여러 개 받아서 그중 하나를 참조로 반환할 때다.

```rust
fn longest(x: &str, y: &str) -> &str {
    if x.len() > y.len() { x } else { y }
}
```

이 코드는 컴파일이 안 된다.

```
error[E0106]: missing lifetime specifier
 --> src/main.rs:1:33
  |
1 | fn longest(x: &str, y: &str) -> &str {
  |               ----     ----     ^ expected named lifetime parameter
  |
  = help: this function's return type contains a borrowed value, but
          the signature does not say whether it is borrowed from `x` or `y`
```

컴파일러 입장에서는 반환된 참조가 `x`에서 온 건지 `y`에서 온 건지 시그니처만 봐선 알 수 없다. 반환값을 받은 쪽에서 그 참조가 얼마나 오래 유효한지 보장하려면 어느 인자와 수명을 같이 하는지 알아야 한다. 그래서 라이프타임 표기로 관계를 명시해야 한다.

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

`'a`는 라이프타임 매개변수다. "`x`, `y`, 반환값이 모두 같은 라이프타임 `'a`를 공유한다"고 선언한 것이다. 정확히는 "반환되는 참조는 `x`와 `y` 중 더 짧게 사는 쪽만큼 유효하다"는 제약을 건다. 이 표기는 실제로 수명을 바꾸지 않는다. 컴파일러에게 참조들 사이의 관계를 설명할 뿐이고, 컴파일러는 그 약속이 지켜지는지 검사한다.

이 표기가 실제로 무얼 막는지 보자.

```rust
fn main() {
    let s1 = String::from("long string");
    let result;
    {
        let s2 = String::from("short");
        result = longest(s1.as_str(), s2.as_str());
    } // s2가 여기서 drop
    println!("{}", result); // 에러: s2가 죽은 뒤 result 사용
}
```

```
error[E0597]: `s2` does not live long enough
```

`result`는 `'a` 동안 유효한데, `'a`는 `s1`과 `s2` 중 짧은 쪽인 `s2`의 수명에 맞춰진다. `s2`가 안쪽 스코프에서 죽으면 `result`도 거기까지만 유효하다. 그 뒤에 `result`를 쓰니 막힌다. 라이프타임 표기가 없었다면 이 위험을 컴파일러가 잡을 근거가 없다.

### 라이프타임 생략 규칙

참조를 받아 참조를 반환하는 함수가 전부 라이프타임을 명시해야 하는 건 아니다. 컴파일러가 명백한 경우를 자동으로 채워주기 때문이다. 이걸 lifetime elision이라고 한다. 규칙은 세 가지다.

첫째, 각 참조 매개변수는 각자 라이프타임을 받는다. 둘째, 입력 라이프타임이 정확히 하나면 그게 모든 출력 라이프타임에 적용된다. 셋째, 메서드에서 `&self`나 `&mut self`가 있으면 `self`의 라이프타임이 모든 출력에 적용된다.

```rust
fn first_word(s: &str) -> &str { // 입력 참조가 하나라 자동 추론됨
    s.split_whitespace().next().unwrap_or("")
}
```

`first_word`는 입력 참조가 `s` 하나뿐이라 반환 참조가 당연히 `s`에서 온 것으로 추론된다. 그래서 표기를 생략해도 된다. 앞의 `longest`가 표기를 요구했던 건 입력 참조가 둘이라 두 번째 규칙이 적용되지 못해서다.

### 구조체가 참조를 들고 있을 때

구조체 필드에 참조를 넣으면 라이프타임 표기가 필수가 된다.

```rust
struct Parser<'a> {
    input: &'a str,
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Parser { input, pos: 0 }
    }
}
```

`Parser`가 `input` 참조를 들고 있는 한, `Parser` 인스턴스는 그 참조가 가리키는 문자열보다 오래 살면 안 된다. 살아남으면 그 순간 dangling reference다. `<'a>` 표기는 "이 `Parser`는 `input`이 가리키는 데이터가 살아있는 동안만 유효하다"는 제약을 컴파일러에게 알린다.

실무에서는 구조체에 참조를 넣는 것보다 소유 타입(`String`, `Vec`)을 직접 넣는 쪽이 라이프타임 관리가 단순해서 그렇게 가는 경우가 많다. 참조 필드는 짧게 살다 사라지는 파서나 뷰 같은 구조에서 의미가 있지, 오래 보관할 데이터 구조에 넣으면 라이프타임이 코드 전체로 번져서 다루기 번거로워진다. 그럴 땐 소유로 가져가는 게 낫다.

## 정리

소유권·빌림·라이프타임은 결국 하나의 목표를 위한 세 장치다. "유효하지 않은 메모리를 가리키는 참조"와 "여러 곳에서 동시에 같은 데이터를 변경하는 경쟁"을 컴파일 타임에 없앤다. move는 double free를 막고, 빌림 규칙은 data race를 막고, 라이프타임은 dangling reference를 막는다.

처음엔 borrow checker가 방해물처럼 느껴진다. 익숙해지면 에러 메시지가 "이 코드는 런타임에 이런 메모리 버그가 난다"고 미리 알려주는 신호로 읽힌다. 에러를 `clone`으로 덮기 전에, 컴파일러가 무얼 막으려는 건지 한 번 더 보면 대개 설계가 잘못된 지점이 보인다.
