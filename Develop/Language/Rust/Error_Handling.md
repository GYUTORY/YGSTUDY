---
title: Rust 에러 처리
tags:
  - Rust
  - Error Handling
  - Result
  - Option
  - thiserror
  - anyhow
updated: 2026-06-12
---

# Rust 에러 처리

Rust에는 예외(exception)가 없다. try/catch도 없고, 함수가 던지는 에러를 잡으려고 호출부를 감싸는 일도 없다. 에러는 값이다. 함수가 실패할 수 있으면 그 실패를 반환 타입에 박아 넣는다. 자바나 파이썬에서 넘어오면 처음엔 이게 불편하다. 모든 실패 가능 지점마다 반환값을 풀어야 하니까. 그런데 한두 달 지나면 "이 함수가 실패할 수 있는지"가 시그니처만 봐도 보인다는 게 얼마나 편한지 알게 된다.

실무에서 에러 처리로 고생하는 지점은 문법이 아니다. `Result`를 어떻게 읽는지는 하루면 익힌다. 진짜 골치 아픈 건 에러 타입 설계, 서로 다른 에러를 하나로 합치는 변환, 그리고 라이브러리와 애플리케이션에서 다른 도구를 써야 한다는 점이다. 여기서는 그 실무 지점 위주로 정리한다.

## Result와 Option: 실패와 부재는 다르다

`Result<T, E>`는 "성공하면 T, 실패하면 E"를 표현한다. `Option<T>`는 "값이 있으면 T, 없으면 아무것도 없음"을 표현한다. 둘 다 enum이라 패턴 매칭으로 푼다.

```rust
enum Result<T, E> {
    Ok(T),
    Err(E),
}

enum Option<T> {
    Some(T),
    None,
}
```

이 둘을 헷갈려서 잘못 쓰는 경우가 꽤 있다. 기준은 명확하다. **실패에 이유가 있으면 Result, 없으면 Option**이다.

파일을 여는 건 실패할 수 있고 그 실패에는 이유가 있다. 파일이 없거나, 권한이 없거나, 디스크가 꽉 찼거나. 그래서 `File::open`은 `Result<File, io::Error>`를 반환한다. 반면 `HashMap`에서 키를 찾는 건 "있거나 없거나"지 실패가 아니다. 키가 없는 게 에러는 아니니까 `get`은 `Option<&V>`를 반환한다.

```rust
use std::collections::HashMap;

fn lookup(map: &HashMap<String, i32>, key: &str) -> Option<i32> {
    map.get(key).copied() // 없으면 None, 그게 정상
}

fn read_config(path: &str) -> Result<String, std::io::Error> {
    std::fs::read_to_string(path) // 실패하면 이유가 담긴 Err
}
```

`Option`을 `Result`로 바꿔야 할 때가 자주 생긴다. 어떤 함수 안에서는 "값이 없음"이 곧 "실패"인 경우다. 이럴 때 `ok_or`나 `ok_or_else`를 쓴다.

```rust
fn get_port(config: &HashMap<String, String>) -> Result<u16, ConfigError> {
    config.get("port")              // Option<&String>
        .ok_or(ConfigError::MissingPort)?  // Option -> Result로 변환 후 전파
        .parse()
        .map_err(|_| ConfigError::InvalidPort)
}
```

반대로 `Result`를 `Option`으로 떨어뜨리는 `.ok()`도 있다. 에러 내용을 버리고 성공 여부만 남길 때 쓴다. 다만 에러를 버리는 거라 디버깅할 때 정보가 사라진다. 남발하면 나중에 "왜 None이 나왔지?"를 추적하기 어려워진다.

## ? 연산자: 에러 전파의 핵심

`?`가 없던 시절 Rust 에러 처리 코드는 정말 장황했다. `match`로 매번 풀어서 `Err`이면 early return 하는 보일러플레이트가 함수마다 반복됐다.

```rust
// ? 없이 쓰면 이 꼴이 된다
fn read_username_old() -> Result<String, std::io::Error> {
    let mut file = match std::fs::File::open("user.txt") {
        Ok(f) => f,
        Err(e) => return Err(e),
    };
    let mut s = String::new();
    match std::io::Read::read_to_string(&mut file, &mut s) {
        Ok(_) => Ok(s),
        Err(e) => Err(e),
    }
}
```

`?`는 이 패턴을 한 글자로 줄인다. `Result`가 `Ok`면 안의 값을 꺼내고, `Err`이면 그 자리에서 함수를 빠져나가며 에러를 반환한다.

```rust
use std::io::Read;

fn read_username() -> Result<String, std::io::Error> {
    let mut file = std::fs::File::open("user.txt")?;
    let mut s = String::new();
    file.read_to_string(&mut s)?;
    Ok(s)
}
```

`?`는 `Option`에도 쓴다. `None`이면 그 자리에서 `None`을 반환한다.

```rust
fn first_char_upper(s: &str) -> Option<char> {
    let c = s.chars().next()?; // 빈 문자열이면 여기서 None 반환
    Some(c.to_ascii_uppercase())
}
```

`?`를 쓰면서 처음 막히는 지점이 있다. `?`는 함수의 반환 타입과 에러 타입이 호환될 때만 동작한다. `io::Error`를 반환하는 함수 안에서 `parse()`(에러 타입이 `ParseIntError`)를 `?`로 전파하려고 하면 컴파일이 안 된다. 타입이 다르니까. 이 변환을 해결하는 게 뒤에 나오는 `From` 트레잇이다.

`?`를 `main`에서 쓰려면 `main`의 반환 타입을 `Result`로 바꿔야 한다.

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string("config.toml")?;
    println!("{content}");
    Ok(())
}
```

## panic, unwrap, expect: 언제 쓰고 언제 피하나

`panic!`은 복구 불가능한 상황에서 프로그램을 중단시킨다. 스택을 되감으며(unwind) 정리하고 죽는다. `unwrap`과 `expect`는 `Result`나 `Option`을 강제로 푸는데, `Err`이나 `None`이면 panic을 일으킨다.

```rust
let n: i32 = "42".parse().unwrap();        // 실패하면 panic
let n: i32 = "42".parse().expect("숫자여야 함"); // 메시지 붙은 panic
```

여기서 실무자가 가장 많이 하는 실수가 `unwrap` 남발이다. 빨리 돌려보려고 `.unwrap()`을 박아두고 그대로 커밋한다. 그러다 운영에서 예상 못 한 입력이 들어오면 서버가 통째로 죽는다. `Result`를 반환해서 호출부가 처리할 수 있는 상황인데 `unwrap`으로 panic을 내버리면 에러 처리의 의미가 없다.

`unwrap`을 써도 되는 경우는 정해져 있다.

- **그 값이 절대 실패할 수 없다는 게 코드로 보장될 때.** 리터럴 `"42".parse::<i32>()`는 실패할 수 없다. 다만 이런 경우도 `expect`로 이유를 적어두는 게 낫다.
- **테스트 코드.** 테스트에서는 실패가 곧 테스트 실패니까 `unwrap`이 자연스럽다.
- **프로토타입이나 예제 코드.** 단, 운영 코드로 넘어가기 전에 걷어내야 한다.
- **초기화 단계에서 실패하면 어차피 못 돌아가는 설정.** 설정 파일이 없으면 서버가 뜰 이유가 없을 때 `expect("config.toml 필요")`로 죽이는 건 합리적이다.

`unwrap`보다 `expect`를 쓰는 습관을 들이는 게 좋다. panic 메시지에 "왜 여기서 죽었는지"가 남으니까 운영 로그에서 원인을 빨리 찾는다. `unwrap`은 그냥 `called Option::unwrap() on a None value`만 남겨서 어느 `unwrap`인지 찾느라 시간을 쓴다.

panic을 써야 하는 진짜 경우는 "프로그램의 불변식(invariant)이 깨졌을 때"다. 배열 인덱스가 범위를 벗어나거나, 절대 일어나면 안 되는 상태에 도달했을 때다. 이건 버그지 처리할 에러가 아니다. 호출자가 복구할 방법이 없는 논리 오류는 panic으로 빨리 죽여서 드러내는 게 맞다.

라이브러리를 만든다면 panic은 더 조심해야 한다. 라이브러리가 멋대로 panic을 내면 그걸 쓰는 애플리케이션이 통제할 수 없이 죽는다. 라이브러리의 공개 함수는 실패를 `Result`로 돌려주고, panic은 진짜 호출자 잘못(잘못된 인자로 불변식을 깬 경우)일 때만 내는 게 관례다.

## From 트레잇: 에러 변환의 기초

앞에서 `?`가 타입이 다르면 막힌다고 했다. 이걸 푸는 게 `From` 트레잇이다. `?`는 에러를 전파할 때 `From::from`을 자동으로 호출한다. 즉 함수의 에러 타입이 `From<하위에러>`를 구현하고 있으면 `?` 한 줄로 변환과 전파가 동시에 일어난다.

직접 만든 에러 타입에 여러 종류의 하위 에러를 모으는 상황을 보자.

```rust
use std::fmt;

#[derive(Debug)]
enum AppError {
    Io(std::io::Error),
    Parse(std::num::ParseIntError),
}

// io::Error -> AppError 변환 정의
impl From<std::io::Error> for AppError {
    fn from(e: std::io::Error) -> Self {
        AppError::Io(e)
    }
}

// ParseIntError -> AppError 변환 정의
impl From<std::num::ParseIntError> for AppError {
    fn from(e: std::num::ParseIntError) -> Self {
        AppError::Parse(e)
    }
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            AppError::Io(e) => write!(f, "IO 오류: {e}"),
            AppError::Parse(e) => write!(f, "파싱 오류: {e}"),
        }
    }
}

impl std::error::Error for AppError {}
```

이렇게 `From`을 구현해두면 서로 다른 에러를 내는 호출을 한 함수에서 `?`로 묶을 수 있다.

```rust
fn read_number(path: &str) -> Result<i32, AppError> {
    let content = std::fs::read_to_string(path)?; // io::Error -> AppError 자동 변환
    let n: i32 = content.trim().parse()?;          // ParseIntError -> AppError 자동 변환
    Ok(n)
}
```

`std::fs::read_to_string`은 `io::Error`를, `parse`는 `ParseIntError`를 내는데, `?`가 각각의 `From` 구현을 찾아서 `AppError`로 바꿔준다. 이 메커니즘이 Rust 에러 처리의 핵심이다. 나중에 나올 `thiserror`는 이 `From`과 `Display` 구현을 매크로로 대신 써주는 도구다.

직접 `From`을 손으로 쓰다 보면 에러 종류가 늘어날 때마다 variant 추가, `From` 구현 추가, `Display` 분기 추가를 매번 해야 해서 지루하다. 그래서 실무에서는 거의 매크로를 쓴다.

## Box<dyn Error>: 편하지만 한계가 있다

에러 타입을 일일이 정의하기 귀찮을 때 `Box<dyn std::error::Error>`를 쓴다. "Error 트레잇을 구현한 무언가"를 박스에 담아 반환하는 거다. `Error`를 구현한 타입은 전부 여기로 `?` 전파가 된다.

```rust
fn process() -> Result<i32, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string("data.txt")?; // io::Error도 OK
    let n: i32 = content.trim().parse()?;                // ParseIntError도 OK
    Ok(n * 2)
}
```

별도 에러 타입 정의 없이 종류가 다른 에러를 다 받아주니 편하다. 그래서 `main`이나 빠른 스크립트, 예제에서 많이 쓴다.

문제는 한계가 분명하다는 거다.

**호출자가 에러 종류를 구분하기 어렵다.** `Box<dyn Error>`는 타입 정보가 지워진 상태라 "이게 IO 에러인지 파싱 에러인지"를 알려면 `downcast`로 일일이 원래 타입을 복원해야 한다. 이게 번거롭고 깨지기 쉽다.

```rust
fn handle() {
    if let Err(e) = process() {
        // 어떤 에러인지 구분하려면 다운캐스트
        if let Some(io_err) = e.downcast_ref::<std::io::Error>() {
            eprintln!("IO 문제: {io_err}");
        } else {
            eprintln!("기타 오류: {e}");
        }
    }
}
```

호출부에서 에러 종류에 따라 다르게 처리해야 하는 코드라면 `Box<dyn Error>`는 맞지 않는다. 분기 처리가 필요하면 enum 기반 에러 타입을 쓰는 게 맞다.

**Send/Sync가 기본으로 안 붙는다.** `Box<dyn Error>`는 스레드 간 이동이 보장되지 않는다. 비동기 코드(`tokio` 등)나 멀티스레드에서 에러를 넘기려면 `Box<dyn Error + Send + Sync>`라고 명시해야 하는데, 이게 타입이 길어지고 여기저기서 트레잇 바운드가 안 맞아 컴파일 에러가 난다. 이 지점에서 막히면 보통 `anyhow`로 갈아탄다.

정리하면 `Box<dyn Error>`는 "에러를 그냥 위로 올려서 출력하고 죽으면 그만"인 곳에서만 쓴다. 호출부가 에러를 들여다보고 분기해야 하면 부적합하다.

## thiserror vs anyhow: 라이브러리냐 애플리케이션이냐

실무 Rust 에러 처리는 사실상 이 두 크레이트로 수렴한다. 핵심 구분은 **라이브러리는 thiserror, 애플리케이션은 anyhow**다. 이유가 있다.

### 라이브러리에는 thiserror

라이브러리는 자기가 내는 에러를 구체적인 타입으로 노출해야 한다. 그래야 그 라이브러리를 쓰는 쪽이 에러 종류를 보고 분기할 수 있다. 라이브러리가 `anyhow::Error`(타입이 지워진 에러)를 반환하면, 쓰는 쪽은 무슨 에러인지 알 수 없어서 대응할 수가 없다.

`thiserror`는 앞에서 손으로 쓴 `From`, `Display`, `Error` 구현을 매크로로 대신 생성해준다. 코드가 확 줄어든다.

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("설정 파일을 읽을 수 없음")]
    Io(#[from] std::io::Error),   // #[from]이 From 구현을 자동 생성

    #[error("포트 값이 올바르지 않음: {0}")]
    InvalidPort(String),

    #[error("필수 항목 누락: {key}")]
    MissingField { key: String },
}
```

`#[error("...")]`가 `Display`를 만들고, `#[from]`이 `From` 변환을 만든다. 앞 절에서 손으로 30줄 쓰던 걸 이걸로 대체한다. variant마다 메시지를 붙일 수 있고, `{0}`이나 `{key}`로 필드를 메시지에 넣는다.

이렇게 정의한 `ConfigError`는 구체 타입이라 라이브러리 사용자가 `match`로 분기할 수 있다.

```rust
match load_config("app.toml") {
    Ok(cfg) => { /* ... */ }
    Err(ConfigError::Io(_)) => { /* 파일 문제니까 기본 설정으로 */ }
    Err(ConfigError::MissingField { key }) => { /* 어떤 필드가 빠졌는지 알림 */ }
    Err(e) => eprintln!("{e}"),
}
```

### 애플리케이션에는 anyhow

애플리케이션 최상위(바이너리, `main` 근처)에서는 에러 종류별로 분기할 일이 별로 없다. 대부분 "에러 났으면 로그 남기고 적당히 죽거나 응답 코드 내려주면" 끝이다. 이럴 때 매 함수마다 에러 타입을 정의하는 건 과하다. `anyhow`는 "아무 에러나 받아서 위로 올리는" 용도다.

```rust
use anyhow::{Context, Result};

fn run() -> Result<()> {
    let config = std::fs::read_to_string("app.toml")
        .context("설정 파일 읽기 실패")?; // 에러에 맥락을 덧붙임

    let port: u16 = config.trim().parse()
        .context("포트 파싱 실패")?;

    println!("포트 {port}로 시작");
    Ok(())
}
```

`anyhow::Result<()>`는 `Result<(), anyhow::Error>`의 별칭이다. `anyhow::Error`는 어떤 `Error` 타입이든 다 받는다. `Box<dyn Error>`와 비슷한데, 결정적인 차이가 `.context()`다. 에러가 올라가는 각 단계에서 맥락을 붙일 수 있어서, 최종적으로 출력하면 "포트 파싱 실패 → invalid digit found in string" 식으로 에러 체인이 쌓인다. 운영에서 원인 추적할 때 이게 크다. `Box<dyn Error>`는 맨 아래 에러 메시지만 덜렁 나와서 어느 단계에서 터졌는지 모른다.

`anyhow`는 backtrace도 자동으로 잡아준다(`RUST_BACKTRACE=1`). 그래서 빠르게 짜는 CLI나 서버 핸들러에서 잘 맞는다.

### 같이 쓰는 패턴

실제로는 한 프로젝트에서 둘을 같이 쓴다. 내부 모듈/크레이트는 `thiserror`로 구체 에러 타입을 만들고, 그걸 최상위 애플리케이션에서 `anyhow`로 받아 올린다. `thiserror`로 만든 에러는 `Error` 트레잇을 구현하니까 `anyhow`가 그대로 받아서 `?`로 전파된다.

```rust
// 내부 모듈: thiserror로 구체 타입
fn load_config(path: &str) -> Result<Config, ConfigError> { /* ... */ }

// 최상위: anyhow로 받아서 맥락 추가
fn main() -> anyhow::Result<()> {
    let cfg = load_config("app.toml")
        .context("앱 초기화 실패")?; // ConfigError -> anyhow::Error 자동
    Ok(())
}
```

거꾸로는 안 된다. 라이브러리가 `anyhow::Error`를 공개 API로 내보내면 그걸 쓰는 쪽이 타입을 잃어서 분기를 못 한다. 그래서 라이브러리 공개 경계에는 `anyhow`를 두지 않는다는 원칙을 지킨다.

## 에러 타입 설계에서 실제로 겪는 문제

### enum이 비대해진다

프로젝트가 커지면 에러 enum의 variant가 계속 늘어난다. 처음엔 5개였는데 어느새 30개가 된다. 모든 실패 경로를 하나의 거대한 enum에 욱여넣으면 어디서 쓰는지 모를 variant가 쌓이고, `match` 분기도 비대해진다.

이걸 모듈별로 에러 타입을 쪼개서 푼다. `db` 모듈은 `DbError`, `http` 모듈은 `HttpError`를 따로 두고, 상위에서 필요하면 묶는다. `thiserror`의 `#[from]`으로 하위 에러를 상위 에러로 자동 변환하니 계층 구조를 만들기 쉽다.

```rust
#[derive(Error, Debug)]
pub enum AppError {
    #[error(transparent)]
    Db(#[from] DbError),      // 하위 에러를 그대로 감쌈

    #[error(transparent)]
    Http(#[from] HttpError),
}
```

`#[error(transparent)]`는 자기 메시지를 만들지 않고 감싼 에러의 메시지를 그대로 노출한다. 단순히 하위 에러를 위로 올리기만 할 때 쓴다.

### 에러에 들어갈 정보를 얼마나 담을지

variant에 데이터를 너무 적게 담으면 나중에 디버깅할 때 정보가 부족하다. `InvalidPort`만 있으면 "어떤 값이 잘못됐는지" 모른다. `InvalidPort(String)`으로 실제 값을 담아둬야 로그에서 원인이 보인다.

반대로 너무 많이 담으면 에러를 만드는 쪽 코드가 지저분해지고, 에러 타입에 라이프타임이나 무거운 타입이 끼면서 전파가 까다로워진다. 경험상 "이 에러를 봤을 때 원인을 재현하거나 알아낼 최소 정보"만 담는 게 적당하다. 잘못된 입력값, 관련 키 이름, 실패한 단계 정도다.

### 에러 변환의 의미가 사라지는 경우

`#[from]`으로 자동 변환을 깔아두면 편하지만, 가끔 같은 하위 에러 타입이 서로 다른 맥락에서 발생하는데 다 같은 variant로 뭉뚱그려진다. 예를 들어 `io::Error`가 설정 읽기에서도 나고 캐시 쓰기에서도 나는데, 둘 다 `AppError::Io(io::Error)`로 합쳐지면 로그만 봐서는 어느 쪽인지 구분이 안 된다.

이럴 땐 `#[from]` 자동 변환을 빼고, 호출 지점에서 `.map_err`로 맥락이 담긴 variant를 명시적으로 만든다.

```rust
let config = std::fs::read_to_string(path)
    .map_err(|e| AppError::ConfigRead { path: path.into(), source: e })?;
```

또는 `anyhow`를 쓰는 코드라면 `.context()`로 맥락을 붙이는 걸로 해결한다. 어느 쪽이든 "에러를 합칠 때 맥락이 사라지지 않는지"를 신경 써야 운영에서 디버깅이 된다.

### 라이브러리 에러 타입은 깨지기 쉬운 공개 API다

`thiserror`로 만든 public enum은 그 자체가 공개 API다. variant를 추가하거나 이름을 바꾸면 그걸 쓰는 코드의 `match`가 깨질 수 있다. 그래서 외부에 노출하는 에러 enum에는 `#[non_exhaustive]`를 붙이는 경우가 많다. 그러면 사용자 쪽 `match`가 `_ =>` 분기를 강제하게 돼서, 나중에 variant를 추가해도 사용자 코드가 컴파일 에러 없이 견딘다.

```rust
#[derive(Error, Debug)]
#[non_exhaustive]
pub enum ConfigError {
    #[error("IO 오류")]
    Io(#[from] std::io::Error),
    // 나중에 variant를 추가해도 사용자 match가 안 깨짐
}
```

## 정리하면서 한 번 더

에러 종류별로 호출자가 다르게 처리해야 하면 구체 타입(thiserror enum)을, 그냥 위로 올려 출력만 하면 되면 `anyhow`를 쓴다. 라이브러리는 전자, 애플리케이션 최상위는 후자다. `Box<dyn Error>`는 빠른 스크립트나 예제까지만, 호출부가 에러를 들여다봐야 하는 순간 한계가 온다. `unwrap`은 "절대 실패 못 함"이 코드로 보장되거나 테스트일 때만 쓰고, 운영 코드에는 `expect`로 이유를 남기거나 `Result`로 돌려준다. 이 정도 기준만 지켜도 에러 처리로 고생할 일의 절반은 사라진다.
