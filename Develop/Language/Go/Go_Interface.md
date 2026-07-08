---
title: Go 인터페이스와 타입 시스템
tags:
  - Go
  - Golang
  - Interface
  - 타입어서션
  - 타입스위치
updated: 2026-07-08
---

# Go 인터페이스와 타입 시스템

## 암묵적 구현

Go 인터페이스는 명시적으로 구현을 선언하지 않는다. 자바의 `implements` 키워드 같은 것 없이, 인터페이스가 요구하는 메서드를 모두 가진 타입이 자동으로 그 인터페이스를 구현한다.

```go
type Writer interface {
    Write(p []byte) (n int, err error)
}

type FileWriter struct {
    path string
}

// Writer 인터페이스를 구현한다는 선언 없이,
// Write 메서드만 정의하면 FileWriter는 Writer다.
func (f *FileWriter) Write(p []byte) (n int, err error) {
    // ...
    return len(p), nil
}
```

이 방식의 실질적인 장점은 외부 패키지의 타입도 내 인터페이스를 만족시킬 수 있다는 점이다. `os.File`은 `io.Writer`를 "구현"하겠다고 선언한 적 없지만, `Write` 메서드가 있으므로 `io.Writer`로 쓸 수 있다.

반면 인터페이스가 충족되는지 컴파일 타임에 확인하려면 명시적 확인 관용구를 써야 한다.

```go
// 컴파일 타임에 FileWriter가 Writer를 구현하는지 검증
var _ Writer = (*FileWriter)(nil)
```

이 패턴은 빈 식별자에 타입 체크용 nil 포인터를 할당하는 것으로, 실제 값을 생성하지 않고 구현 여부만 확인한다. 구현이 빠진 경우 컴파일 에러가 바로 난다.

메서드 수신자가 포인터인지 값인지도 중요하다. 포인터 수신자로 정의된 메서드는 값 타입으로는 인터페이스를 충족하지 못한다.

```go
type Stringer interface {
    String() string
}

type Point struct{ X, Y int }

func (p *Point) String() string {
    return fmt.Sprintf("(%d, %d)", p.X, p.Y)
}

var s Stringer = &Point{1, 2}  // OK
var s2 Stringer = Point{1, 2}  // 컴파일 에러
```

## interface{} vs any

Go 1.18부터 `any`는 `interface{}`의 타입 별칭이다. 완전히 동일하다.

```go
var v1 interface{} = 42
var v2 any = 42
// v1과 v2는 동일한 타입
```

`any`를 쓰면 코드가 짧아지고, 제네릭 도입 이후 Go 표준 라이브러리도 `any`를 사용한다. 새 코드에서는 `any`를 쓰는 것이 현재 관행이다.

`any`/`interface{}`는 모든 타입을 담을 수 있지만, 꺼낼 때 타입 정보가 없으므로 반드시 타입 어서션이나 타입 스위치를 써야 한다. 남발하면 컴파일 타임 타입 안전성을 버리는 것이므로, 정말 필요한 경우에만 쓴다.

실무에서 `any`를 자주 보게 되는 곳은 JSON 파싱이다.

```go
var result map[string]any
json.Unmarshal(data, &result)

// 꺼낼 때마다 타입 어서션이 필요하다
name, ok := result["name"].(string)
if !ok {
    return errors.New("name is not a string")
}
```

제네릭 도입 이후에는 `any`를 쓰는 대신 타입 파라미터로 해결할 수 있는 경우가 많아졌다.

```go
// any를 쓰던 방식
func Map(slice []any, fn func(any) any) []any { ... }

// 제네릭으로 타입 안전하게
func Map[T, R any](slice []T, fn func(T) R) []R { ... }
```

## 타입 어서션과 타입 스위치

타입 어서션은 인터페이스 값에서 구체 타입을 꺼낸다.

```go
var w io.Writer = os.Stdout

// 단일 반환: 실패하면 패닉
f := w.(*os.File)

// 두 값 반환: ok가 false면 f는 제로값, 패닉 없음
f, ok := w.(*os.File)
if !ok {
    // w는 *os.File이 아니다
}
```

프로덕션 코드에서 ok 없는 단일 어서션은 거의 쓰지 않는다. 인터페이스 값이 예상과 다른 타입이면 패닉이 나고, 이건 런타임 크래시다.

타입 스위치는 여러 타입을 한 번에 처리할 때 쓴다.

```go
func describe(i any) string {
    switch v := i.(type) {
    case int:
        return fmt.Sprintf("int: %d", v)
    case string:
        return fmt.Sprintf("string: %q", v)
    case []byte:
        return fmt.Sprintf("bytes: %d bytes", len(v))
    case nil:
        return "nil"
    default:
        return fmt.Sprintf("unknown: %T", v)
    }
}
```

타입 스위치에서 `v := i.(type)` 구문은 타입 스위치 블록 밖에서는 쓸 수 없다. `.(type)`은 타입 스위치 전용 문법이다.

한 case에 여러 타입을 묶을 수 있는데, 이 경우 `v`는 원래 인터페이스 타입이 된다.

```go
switch v := i.(type) {
case int, int64:
    // v의 타입은 any (또는 i의 원래 인터페이스 타입)
    // int인지 int64인지 여기서는 알 수 없다
    fmt.Println(v)
}
```

에러 처리에서 타입 어서션을 자주 쓴다.

```go
if pathErr, ok := err.(*os.PathError); ok {
    fmt.Println("path:", pathErr.Path)
}

// errors.As를 쓰면 래핑된 에러도 처리된다
var pathErr *os.PathError
if errors.As(err, &pathErr) {
    fmt.Println("path:", pathErr.Path)
}
```

에러 체인을 다룰 때는 타입 어서션보다 `errors.As`를 써야 한다. `fmt.Errorf("...: %w", err)`로 래핑된 에러에서 타입 어서션은 실패하지만 `errors.As`는 체인을 따라가며 찾는다.

## nil interface 함정

Go에서 가장 혼란을 주는 부분 중 하나다. 인터페이스 값은 두 개의 필드로 구성된다: 타입 정보(type)와 값 포인터(value). 둘 다 nil일 때만 인터페이스가 nil이다.

```go
var p *os.File = nil
var w io.Writer = p

fmt.Println(p == nil)  // true
fmt.Println(w == nil)  // false (!)
```

`w`는 타입 정보(`*os.File`)를 가지고 있기 때문에 nil이 아니다. 값은 nil이지만 타입이 있다.

이게 문제가 되는 전형적인 패턴이 있다.

```go
type MyError struct{ msg string }
func (e *MyError) Error() string { return e.msg }

func doSomething() error {
    var err *MyError = nil
    // ... 뭔가 처리
    return err  // 함정: *MyError nil을 error 인터페이스로 반환
}

func main() {
    err := doSomething()
    if err != nil {
        // 여기에 들어온다. err는 nil이 아니다.
        fmt.Println("error:", err)
    }
}
```

`doSomething`이 `nil`을 반환할 의도였지만, `*MyError` 타입의 nil 포인터를 `error` 인터페이스로 변환해서 반환했다. 인터페이스 값에 타입이 세팅되어 있으므로 nil 비교가 false가 된다.

올바른 패턴은 에러가 없을 때 명시적으로 nil을 반환하는 것이다.

```go
func doSomething() error {
    var err *MyError = nil
    if someCondition {
        err = &MyError{"something went wrong"}
    }
    if err != nil {
        return err  // *MyError가 있을 때만 인터페이스로 변환
    }
    return nil  // 타입 없는 nil 반환
}
```

함수의 반환 타입이 인터페이스이면, 구체 타입의 nil 변수를 반환하지 말고 `nil` 리터럴을 직접 반환해야 한다.

인터페이스 내부의 nil 값을 확인해야 하는 경우는 리플렉션을 써야 한다.

```go
func isNilInterface(i any) bool {
    if i == nil {
        return true
    }
    v := reflect.ValueOf(i)
    return v.Kind() == reflect.Ptr && v.IsNil()
}
```

## 인터페이스 임베딩으로 조합

Go는 인터페이스를 다른 인터페이스에 임베딩해서 조합할 수 있다.

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type ReadWriter interface {
    Reader
    Writer
}
```

`io.ReadWriter`는 `Read`와 `Write` 메서드를 모두 요구한다. 이 방식으로 인터페이스를 작게 유지하면서 필요할 때 조합해 쓸 수 있다.

표준 라이브러리의 `io` 패키지가 이 패턴의 전형이다. `io.Reader`, `io.Writer`, `io.Closer`를 각각 작게 만들고, `io.ReadWriteCloser`처럼 조합 인터페이스를 제공한다.

실무에서 자주 쓰는 패턴은 기존 인터페이스에 메서드를 추가한 확장 인터페이스다.

```go
type Repository interface {
    FindByID(ctx context.Context, id int64) (*User, error)
    Save(ctx context.Context, user *User) error
}

// 트랜잭션이 필요한 경우의 확장
type TransactionalRepository interface {
    Repository
    WithTx(tx *sql.Tx) Repository
}
```

인터페이스 임베딩 시 중복 메서드가 있으면 컴파일 에러가 난다.

```go
type A interface {
    Foo() string
}

type B interface {
    Foo() string
}

type C interface {
    A
    B  // 컴파일 에러: Foo 중복
}
```

Go 1.14부터는 메서드 시그니처가 동일하면 중복을 허용한다. 하지만 시그니처가 다르면 여전히 에러다.

인터페이스는 작게 만드는 것이 좋다. Go 철학상 하나의 메서드만 가진 인터페이스도 충분히 유용하다. `io.Reader`가 `Read` 하나만 가진 것처럼. 메서드가 많은 인터페이스는 구현하기 어렵고, 목업을 만들기도 번거롭다.

```go
// 나쁜 예: 너무 많은 메서드
type UserService interface {
    Create(ctx context.Context, req CreateUserReq) (*User, error)
    Update(ctx context.Context, id int64, req UpdateUserReq) (*User, error)
    Delete(ctx context.Context, id int64) error
    FindByID(ctx context.Context, id int64) (*User, error)
    FindByEmail(ctx context.Context, email string) (*User, error)
    List(ctx context.Context, page, size int) ([]*User, error)
}

// 특정 기능만 필요한 쪽에서 작은 인터페이스를 정의
type UserFinder interface {
    FindByID(ctx context.Context, id int64) (*User, error)
}
```

인터페이스는 구현하는 쪽이 아니라 사용하는 쪽에서 정의하는 것이 Go의 관행이다. 패키지 A가 인터페이스를 정의하고 패키지 B가 구현하는 것이 아니라, 패키지 B가 구체 타입을 제공하고 패키지 A가 자신에게 필요한 인터페이스를 직접 정의한다. 이렇게 하면 패키지 간 의존성이 줄어든다.
