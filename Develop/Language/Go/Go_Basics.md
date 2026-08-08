---
title: Go 기본 문법
tags: [go, language]
updated: 2026-07-08
---

# Go 기본 문법

Java나 Python에서 넘어오면 Go가 처음엔 단순하다고 느낀다. 선언 방법이 두 가지이고, 클래스가 없고, 예외 처리도 없다. 쓰다 보면 그 단순함이 의도적이라는 걸 알게 된다. 언어 자체가 협업과 가독성을 강제하는 방향으로 설계됐다. 여기서는 Go를 처음 쓸 때 반드시 만나는 타입 시스템, 변수 선언, 함수 설계, 패키지 구조, 그리고 defer/panic/recover를 실무 관점에서 다룬다.

## 타입 시스템

Go는 정적 타입 언어다. 컴파일 시점에 타입이 정해지고, 암묵적 타입 변환이 없다. `int`와 `int64`도 명시적으로 변환해야 한다.

```go
var a int = 10
var b int64 = int64(a) // 명시적 변환 필수
```

타입 변환 없이 대입하면 컴파일 에러가 난다. 처음엔 불편하지만 런타임에 타입 때문에 터지는 상황이 없다.

### 기본 타입

| 분류 | 타입 |
|------|------|
| 정수 | `int`, `int8`, `int16`, `int32`, `int64`, `uint`, `uint8`, `uint16`, `uint32`, `uint64` |
| 실수 | `float32`, `float64` |
| 문자열 | `string` (UTF-8 바이트 시퀀스, 불변) |
| 불리언 | `bool` |
| 바이트 | `byte` (`uint8` 별칭), `rune` (`int32` 별칭, 유니코드 코드포인트) |

`int`의 크기는 플랫폼에 따라 32비트 또는 64비트다. 직렬화나 네트워크 통신처럼 크기가 중요한 곳에서는 `int64`를 명시하는 게 안전하다.

### 문자열과 rune

Go의 `string`은 바이트 배열이다. `len(s)`는 바이트 수를 반환하고, 인덱싱도 바이트 단위다.

```go
s := "안녕"
fmt.Println(len(s))    // 6 (UTF-8에서 한글 한 글자는 3바이트)
fmt.Println(s[0])      // 236 (첫 번째 바이트 값)
```

한글 등 멀티바이트 문자를 문자 단위로 다루려면 `[]rune`으로 변환해야 한다.

```go
r := []rune(s)
fmt.Println(len(r))    // 2 (문자 수)
fmt.Println(string(r[0])) // "안"
```

`range`로 문자열을 순회하면 자동으로 rune 단위로 처리된다.

```go
for i, ch := range s {
    fmt.Printf("index %d: %c\n", i, ch)
}
// index 0: 안
// index 3: 녕
```

`range` 없이 `for i := 0; i < len(s); i++`로 순회하면 바이트 단위라 한글이 깨진다. 문자열을 다룰 때 이 차이를 모르면 예상치 못한 버그가 생긴다.

### 구조체와 인터페이스

Go에는 클래스가 없다. 구조체에 메서드를 붙이는 방식으로 OOP를 흉내낸다.

```go
type User struct {
    ID    int64
    Name  string
    Email string
}

func (u *User) Greet() string {
    return "Hello, " + u.Name
}
```

인터페이스는 메서드 집합만 정의한다. 구현한다고 명시하지 않아도 메서드를 모두 가진 타입은 자동으로 그 인터페이스를 구현한다. 이를 덕 타이핑(duck typing)이라고 부른다.

```go
type Greeter interface {
    Greet() string
}

func PrintGreet(g Greeter) {
    fmt.Println(g.Greet())
}

u := &User{Name: "Alice"}
PrintGreet(u) // User가 Greeter를 구현
```

`implements` 같은 키워드가 없어서 인터페이스 의존성이 느슨하다. 외부 패키지의 타입에 맞는 인터페이스를 내 코드에서 새로 정의해도 된다. 이 특성 때문에 테스트 작성 시 모킹이 쉽다.

### 포인터

Go는 포인터가 있지만 포인터 연산은 없다. 값을 수정해야 하거나 큰 구조체를 복사하지 않으려면 포인터로 넘긴다.

```go
func increment(n *int) {
    *n++
}

x := 10
increment(&x)
fmt.Println(x) // 11
```

구조체를 메서드의 리시버로 넘길 때 값 리시버와 포인터 리시버를 구분한다.

- 값 리시버 `(u User)`: 복사본에 작동, 원본을 수정 못 함
- 포인터 리시버 `(u *User)`: 원본에 작동, 원본을 수정 가능

한 타입의 메서드는 값 리시버와 포인터 리시버를 혼용하지 않는 게 원칙이다. 혼용하면 인터페이스 구현에서 문제가 생길 수 있다. 구조체 필드를 수정해야 하는 메서드가 하나라도 있으면 전부 포인터 리시버로 맞춘다.

## 변수 선언: var vs :=

Go에서 변수를 선언하는 방법은 두 가지다.

```go
var name string = "Alice"   // var 키워드, 타입 명시
name := "Alice"             // 단축 선언, 타입 추론
```

규칙은 단순하다.

- `:=`는 함수 안에서만 쓸 수 있다
- 패키지 수준 변수는 반드시 `var`로 선언해야 한다
- `:=`는 새 변수를 선언하고 동시에 할당한다

```go
var globalConfig string // 패키지 수준

func main() {
    x := 10      // 함수 내부, 단축 선언 가능
    var y int    // 기본값(zero value)으로 초기화, y = 0
    fmt.Println(x, y)
}
```

### zero value

Go는 선언만 하고 초기화하지 않으면 타입의 zero value로 자동 초기화된다.

| 타입 | zero value |
|------|------------|
| 숫자 | `0` |
| `bool` | `false` |
| `string` | `""` |
| 포인터, 슬라이스, 맵, 채널, 함수 | `nil` |

Java처럼 null 참조 에러가 날 수 있는 상황을 줄여준다. `string`은 항상 `""`이라 nil 체크 없이 바로 쓸 수 있다.

### :=의 함정: 변수 가림(shadowing)

`:=`를 쓰다 보면 의도치 않게 바깥 스코프의 변수를 가리는 경우가 있다.

```go
err := doSomething()
if err != nil {
    err := fmt.Errorf("wrapped: %w", err) // 새로운 err, 바깥 err를 가림
    log.Println(err)
    // 바깥 err는 그대로 nil이 아닌 상태
}
```

`if` 블록 안에서 `:=`로 선언한 `err`는 블록 스코프에서만 산다. 바깥의 `err`와 별개다. 의도적인 경우라면 괜찮지만, 에러를 래핑해서 반환하려던 목적이라면 블록 밖에서 `= fmt.Errorf(...)` 로 재할당해야 한다.

```go
err := doSomething()
if err != nil {
    err = fmt.Errorf("wrapped: %w", err) // 재할당, 기존 err 수정
    return err
}
```

`:=`와 `=`의 차이를 의식하지 않으면 에러 처리가 의도대로 안 된다. 특히 에러 핸들링이 복잡한 코드에서 자주 나타난다.

### 멀티 반환과 _

Go 함수는 여러 값을 반환할 수 있다. 쓰지 않는 반환값은 `_`로 버린다. Go는 선언하고 쓰지 않은 변수를 컴파일 에러로 처리하기 때문에 필요 없는 값은 반드시 `_`로 명시해야 한다.

```go
value, err := strconv.Atoi("123")
if err != nil {
    return err
}

_, err = fmt.Fprintf(w, "hello") // 첫 번째 반환값(쓴 바이트 수)은 버림
```

## 함수

### 기본 구조

```go
func add(a, b int) int {
    return a + b
}

// 여러 값 반환
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("division by zero")
    }
    return a / b, nil
}
```

같은 타입의 매개변수는 마지막에 한 번만 타입을 쓴다. `func add(a, b int)`에서 `a`와 `b` 모두 `int`다.

### 이름 있는 반환값

반환값에 이름을 붙일 수 있다.

```go
func minMax(arr []int) (min, max int) {
    min, max = arr[0], arr[0]
    for _, v := range arr[1:] {
        if v < min {
            min = v
        }
        if v > max {
            max = v
        }
    }
    return // naked return
}
```

이름 있는 반환값은 함수 시작 시점에 zero value로 초기화된다. `return`만 쓰면 현재 이름 있는 반환값이 그대로 반환된다. 짧은 함수에서는 가독성을 높이지만, 함수가 길면 어디서 수정됐는지 추적하기 어려워진다. 긴 함수에서는 값을 명시적으로 반환하는 게 낫다.

### 가변 인수

```go
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

sum(1, 2, 3)

slice := []int{1, 2, 3}
sum(slice...) // 슬라이스를 펼쳐서 넘김
```

### 함수는 일급 값

Go에서 함수는 변수에 담을 수 있고, 인자로 넘길 수 있고, 반환할 수 있다.

```go
type Handler func(string) string

func apply(s string, fn Handler) string {
    return fn(s)
}

result := apply("hello", strings.ToUpper)
```

클로저도 지원한다.

```go
func counter() func() int {
    count := 0
    return func() int {
        count++
        return count
    }
}

c := counter()
c() // 1
c() // 2
c() // 3
```

클로저가 외부 변수를 캡처할 때 주의할 점이 있다. 루프 변수를 고루틴에서 캡처하면 모든 고루틴이 같은 변수를 공유해서 루프가 끝난 뒤의 값만 보게 된다.

```go
// 잘못된 예
for i := 0; i < 3; i++ {
    go func() {
        fmt.Println(i) // 항상 3이 출력될 수 있음
    }()
}

// 올바른 예: 루프 변수를 복사해서 넘김
for i := 0; i < 3; i++ {
    i := i // 루프 블록 내 새 변수로 캡처
    go func() {
        fmt.Println(i)
    }()
}
```

Go 1.22부터는 루프 변수가 매 반복마다 새로 생성되도록 변경됐다. Go 버전을 확인하고 쓰는 게 중요하다.

## 패키지 구조

Go 코드는 패키지 단위로 구성된다. 파일 첫 줄에 패키지 이름을 선언한다.

```go
package main // 실행 가능한 프로그램의 진입점

package user  // 라이브러리 패키지
```

### 이름 대소문자로 접근 제어

Go의 접근 제어는 단순하다. 이름이 대문자로 시작하면 패키지 외부에서 접근 가능(exported), 소문자면 패키지 내부에서만 쓸 수 있다(unexported). `public`, `private` 키워드가 없다.

```go
package user

type User struct {        // 외부 접근 가능
    ID    int64           // 외부 접근 가능
    email string          // 패키지 내부에서만 접근
}

func NewUser(email string) *User { // 외부 접근 가능
    return &User{email: email}
}

func (u *User) validate() error { // 패키지 내부에서만 접근
    // ...
}
```

### import와 패키지 경로

```go
import (
    "fmt"
    "net/http"
    
    "github.com/my-org/my-app/internal/user" // 모듈 경로 기반
)
```

`internal` 디렉토리에 있는 패키지는 상위 디렉토리와 그 하위에서만 임포트할 수 있다. 외부 모듈에서 임포트하면 컴파일 에러가 난다. 프로젝트 내부 전용 패키지를 격리할 때 사용한다.

쓰지 않는 임포트는 컴파일 에러다. 사이드 이펙트만 필요한 경우(예: `database/sql` 드라이버 등록)에는 `_`를 붙인다.

```go
import _ "github.com/lib/pq" // postgres 드라이버 등록
```

### 디렉토리 구조

하나의 디렉토리는 하나의 패키지다. 디렉토리 이름과 패키지 이름이 다를 수 있지만 혼란을 줄이려면 맞추는 게 낫다. 테스트 파일은 같은 패키지에서 `_test.go`로 끝나야 한다.

```
myapp/
├── main.go                  // package main
├── internal/
│   ├── user/
│   │   ├── user.go          // package user
│   │   └── user_test.go     // package user 또는 package user_test
│   └── order/
│       └── order.go         // package order
└── pkg/
    └── httpclient/
        └── client.go        // package httpclient
```

`go.mod`에 선언한 모듈 경로가 임포트 경로의 기준이 된다. `module github.com/my-org/myapp`이면 `internal/user`는 `github.com/my-org/myapp/internal/user`로 임포트한다.

## defer, panic, recover

### defer

`defer`는 함수가 반환하기 직전에 실행할 코드를 등록한다. 파일 닫기, 락 해제, 커넥션 반환 같은 정리 작업에 쓴다.

```go
func readFile(path string) ([]byte, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer f.Close() // 함수가 끝날 때 자동으로 닫힘

    return io.ReadAll(f)
}
```

`defer`가 없으면 `return` 경로마다 `f.Close()`를 호출해야 한다. 에러 분기가 많을수록 빠뜨리기 쉽다.

여러 개의 `defer`는 LIFO(Last In First Out) 순서로 실행된다.

```go
func main() {
    defer fmt.Println("first")
    defer fmt.Println("second")
    defer fmt.Println("third")
}
// 출력:
// third
// second
// first
```

#### defer와 루프

루프 안에서 `defer`를 쓰면 함수가 끝날 때까지 정리 작업이 전부 쌓인다. DB 커넥션이나 파일을 루프에서 열면 함수가 끝나기 전까지 모두 열린 상태로 있어서 리소스가 고갈된다.

```go
// 문제있는 코드: rows.Close()가 루프 끝이 아닌 함수 끝에서 실행됨
func processAll(ids []int) error {
    for _, id := range ids {
        rows, err := db.Query("SELECT * FROM t WHERE id = ?", id)
        if err != nil {
            return err
        }
        defer rows.Close() // 루프가 끝난 뒤 함수가 반환될 때까지 닫히지 않음

        // rows 처리
    }
    return nil
}
```

루프 내부에서 리소스를 정리해야 할 때는 함수를 분리하거나 명시적으로 닫는다.

```go
func processOne(id int) error {
    rows, err := db.Query("SELECT * FROM t WHERE id = ?", id)
    if err != nil {
        return err
    }
    defer rows.Close() // 이 함수가 끝날 때 닫힘
    // rows 처리
    return nil
}

func processAll(ids []int) error {
    for _, id := range ids {
        if err := processOne(id); err != nil {
            return err
        }
    }
    return nil
}
```

#### defer와 이름 있는 반환값

`defer` 함수에서 이름 있는 반환값을 수정할 수 있다. 에러를 래핑하거나 트랜잭션을 롤백하는 패턴에서 쓴다.

```go
func doTx(db *sql.DB) (err error) {
    tx, err := db.Begin()
    if err != nil {
        return
    }
    defer func() {
        if err != nil {
            tx.Rollback() // 에러가 있으면 롤백
        } else {
            err = tx.Commit() // 에러가 없으면 커밋, 커밋 에러도 반환
        }
    }()

    // tx 작업...
    return
}
```

이름 있는 반환값 `err`를 `defer` 내 클로저가 캡처해서 수정한다. `return` 이후에 `defer`가 실행되고 `err`를 바꾸면 호출자는 바뀐 값을 받는다.

### panic

`panic`은 정상적인 실행 흐름을 멈추고 콜스택을 역방향으로 전파된다.

```go
func mustPositive(n int) int {
    if n <= 0 {
        panic(fmt.Sprintf("n must be positive, got %d", n))
    }
    return n
}
```

Go에서 `panic`은 예외 대체제가 아니다. 예상 가능한 에러(파일 없음, 유효하지 않은 입력 등)는 `error` 반환으로 처리한다. `panic`은 절대로 발생해서는 안 되는 상황, 즉 프로그래밍 오류를 나타낼 때 쓴다. 슬라이스 범위 초과, nil 맵에 쓰기 등 런타임이 자동으로 발생시키는 panic도 같은 맥락이다.

서버 애플리케이션에서 `panic`이 catch되지 않으면 프로세스가 죽는다. HTTP 서버 등에서는 미들웨어 레벨에서 `recover`로 잡아서 500 에러를 반환하는 구조를 쓴다.

### recover

`recover`는 `defer` 함수 안에서만 동작한다. `panic`이 전파되는 도중 `defer`가 실행되는 시점에 `recover`를 호출하면 panic 값을 가져오고 전파를 중단한다.

```go
func safeCall(fn func()) (err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("recovered panic: %v", r)
        }
    }()
    fn()
    return nil
}
```

`recover`를 `defer` 바깥에서 직접 호출하면 항상 `nil`을 반환한다. 동작하지 않는다.

```go
// 이렇게 쓰면 recover가 동작하지 않음
defer recover() // defer 내부에서 직접 recover()만 호출, 반환값 처리 없음
```

`recover`의 반환값을 받아서 처리해야 한다.

#### recover 남용 주의

`recover`로 모든 panic을 삼키면 버그를 숨기게 된다. 패닉이 발생한 원인을 알 수 없고, 상태가 불일치한 채 프로그램이 계속 돌아간다.

실무에서 `recover`의 정당한 용도는 두 가지다.

첫째, HTTP 핸들러나 고루틴 경계에서 panic이 프로세스를 죽이지 않도록 잡아서 로그를 남기고 에러를 반환한다.

둘째, 패키지 내부에서 복잡한 재귀 로직을 단순화하려고 panic/recover를 제어 흐름으로 쓰는 경우가 있다. 단, 이 경우 panic이 패키지 경계를 절대 넘지 않도록 해야 한다. 외부로 panic을 노출하면 사용자 코드가 대처할 방법이 없다.

```go
// 패키지 내부 로직에서 panic/recover로 제어 흐름 단순화 (패키지 외부로 노출 안 함)
type ParseError struct {
    msg string
}

func parse(s string) (result Result, err error) {
    defer func() {
        if r := recover(); r != nil {
            if pe, ok := r.(ParseError); ok {
                err = fmt.Errorf("parse error: %s", pe.msg)
            } else {
                panic(r) // ParseError가 아닌 panic은 다시 전파
            }
        }
    }()
    result = doParse(s) // 내부에서 ParseError로 panic
    return
}
```

`ParseError`가 아닌 panic은 다시 `panic(r)`로 전파한다. `recover`로 잡았다고 무조건 삼키지 않는다. 이 부분을 빠뜨리면 예상치 못한 panic이 조용히 사라진다.

### defer/panic/recover 실행 순서

```go
func f() {
    defer fmt.Println("defer 1")
    defer fmt.Println("defer 2")
    panic("something wrong")
    fmt.Println("이 줄은 실행 안 됨")
}

func main() {
    defer func() {
        if r := recover(); r != nil {
            fmt.Println("recovered:", r)
        }
    }()
    f()
    fmt.Println("이 줄도 실행 안 됨")
}
// 출력:
// defer 2
// defer 1
// recovered: something wrong
```

`panic`이 발생하면 `f` 안의 `defer`들이 LIFO 순서로 실행된 뒤, `main`의 `defer`로 올라와서 `recover`가 panic을 잡는다. `main`에서도 recover 없이 panic이 전파되면 프로그램이 스택 트레이스와 함께 종료된다.
