---
title: Go 인터페이스와 타입 시스템
tags: [Go, Golang, interface, 타입어서션, 타입스위치]
updated: 2026-08-02
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

인터페이스가 충족되는지 컴파일 타임에 확인하려면 명시적 확인 관용구를 써야 한다.

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

포인터 수신자가 있는 메서드는 값 타입 변수에서도 `.`으로 호출할 수 있다. Go가 자동으로 주소를 취해준다. 그래서 값 타입으로 메서드를 호출할 수 있다는 사실이 인터페이스도 된다는 착각을 만든다. 인터페이스에 값 타입을 할당할 때만 컴파일 에러가 난다는 점을 명심해야 한다.

## nil interface 함정

Go에서 가장 혼란을 주는 부분이다. 인터페이스 값은 두 개의 필드로 구성된다: 타입 정보(type)와 값 포인터(value). 둘 다 nil일 때만 인터페이스가 nil이다.

```go
var p *os.File = nil
var w io.Writer = p

fmt.Println(p == nil)  // true
fmt.Println(w == nil)  // false (!)
```

`w`는 타입 정보(`*os.File`)를 가지고 있기 때문에 nil이 아니다. 값은 nil이지만 타입이 있다.

### 서비스 레이어에서 자주 만나는 패턴

실무에서 이 함정은 에러 반환에서 가장 자주 나타난다.

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

func validateAge(age int) error {
    var err *ValidationError

    if age < 0 {
        err = &ValidationError{Field: "age", Message: "음수는 안 된다"}
    }

    return err  // 함정: age >= 0이면 *ValidationError nil을 error로 반환
}

func main() {
    err := validateAge(25)
    if err != nil {
        // age가 25인데도 여기에 들어온다
        log.Println("validation failed:", err) // 출력: validation failed: <nil>
    }
}
```

`validateAge(25)`는 `nil`을 반환할 의도였지만, `*ValidationError` 타입의 nil 포인터를 `error` 인터페이스로 변환해서 반환했다. 타입이 세팅되어 있으므로 nil 비교가 false가 된다.

올바른 패턴은 에러가 없을 때 `nil` 리터럴을 직접 반환하는 것이다.

```go
func validateAge(age int) error {
    if age < 0 {
        return &ValidationError{Field: "age", Message: "음수는 안 된다"}
    }
    return nil  // 타입 없는 nil 반환
}
```

### 리포지토리 패턴에서의 함정

데이터베이스 레이어에서도 똑같이 발생한다.

```go
type DBError struct {
    Code    int
    Message string
}
func (e *DBError) Error() string { return e.Message }

func findUser(id int64) (*User, error) {
    var dbErr *DBError

    user, err := db.QueryRow(...)
    if err != nil {
        dbErr = &DBError{Code: 500, Message: err.Error()}
    }

    return user, dbErr  // err가 nil이어도 dbErr를 반환하면 nil이 아닌 error가 된다
}
```

이 함수를 호출하는 쪽에서 `err != nil`로 체크하면, 실제 에러가 없는 경우에도 에러가 있다고 판단한다. 구체 타입 변수를 인터페이스 반환 타입에 담아 반환할 때는 항상 의심해야 한다.

### 인터페이스 내부 nil 확인

인터페이스 내부의 값이 nil인지 확인해야 하는 경우는 리플렉션을 써야 한다.

```go
func isNilValue(i any) bool {
    if i == nil {
        return true
    }
    v := reflect.ValueOf(i)
    switch v.Kind() {
    case reflect.Ptr, reflect.Interface, reflect.Slice,
         reflect.Map, reflect.Chan, reflect.Func:
        return v.IsNil()
    }
    return false
}
```

실무에서 이게 필요한 경우는 보통 설계가 잘못된 신호다. 인터페이스를 받는 함수가 내부 값의 nil 여부까지 검사해야 한다면 API를 다시 보는 것이 맞다.

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

### 타입 어서션 체이닝 함정

타입 어서션을 연달아 쓰다가 패닉 나는 경우가 있다.

```go
// 위험한 패턴
data := getConfig().(map[string]any)["database"].(map[string]any)["host"].(string)

// 안전하게 쓰려면
raw := getConfig()
m, ok := raw.(map[string]any)
if !ok {
    return errors.New("config is not a map")
}
dbRaw, ok := m["database"].(map[string]any)
if !ok {
    return errors.New("database config is not a map")
}
host, ok := dbRaw["host"].(string)
if !ok {
    return errors.New("host is not a string")
}
```

JSON 설정 파일을 `any`로 파싱할 때 이 패턴이 자주 나온다. 어디서 실패했는지 알 수 없는 패닉보다 명확한 에러가 낫다.

### 타입 스위치

여러 타입을 한 번에 처리할 때 쓴다.

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

### 에러 타입 판별

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

HTTP 핸들러에서 에러 종류에 따라 응답 코드를 다르게 내려야 할 때 타입 스위치가 유용하다.

```go
type NotFoundError struct{ Resource string }
func (e *NotFoundError) Error() string { return e.Resource + " not found" }

type UnauthorizedError struct{ Reason string }
func (e *UnauthorizedError) Error() string { return "unauthorized: " + e.Reason }

func handleError(w http.ResponseWriter, err error) {
    var notFound *NotFoundError
    var unauthorized *UnauthorizedError

    switch {
    case errors.As(err, &notFound):
        http.Error(w, err.Error(), http.StatusNotFound)
    case errors.As(err, &unauthorized):
        http.Error(w, err.Error(), http.StatusUnauthorized)
    default:
        http.Error(w, "internal server error", http.StatusInternalServerError)
    }
}
```

타입 스위치로 에러를 처리할 수도 있지만, 래핑된 에러를 고려하면 `errors.As`를 쓰는 패턴이 더 견고하다.

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

`io.ReadWriter`는 `Read`와 `Write` 메서드를 모두 요구한다. 인터페이스를 작게 유지하면서 필요할 때 조합해 쓸 수 있다.

표준 라이브러리의 `io` 패키지가 이 패턴의 전형이다. `io.Reader`, `io.Writer`, `io.Closer`를 각각 작게 만들고, `io.ReadWriteCloser`처럼 조합 인터페이스를 제공한다.

### 리포지토리 패턴에서의 임베딩

실무에서 자주 쓰는 패턴은 기존 인터페이스에 메서드를 추가한 확장 인터페이스다.

```go
type UserRepository interface {
    FindByID(ctx context.Context, id int64) (*User, error)
    Save(ctx context.Context, user *User) error
}

// 트랜잭션이 필요한 경우의 확장
type TransactionalUserRepository interface {
    UserRepository
    WithTx(tx *sql.Tx) UserRepository
}
```

이렇게 하면 트랜잭션이 필요 없는 코드는 `UserRepository`만 받으면 된다. 테스트 목업을 만들 때도 필요한 메서드만 구현하면 된다.

임베딩 시 중복 메서드가 있으면 컴파일 에러가 난다.

```go
type A interface {
    Foo() string
}

type B interface {
    Foo() string
}

type C interface {
    A
    B  // Go 1.14 이전: 컴파일 에러
       // Go 1.14 이후: 시그니처가 동일하면 허용
}
```

Go 1.14부터는 메서드 시그니처가 동일하면 중복을 허용한다. 하지만 시그니처가 다르면 여전히 에러다.

### 인터페이스는 작게

인터페이스는 작게 만드는 것이 좋다. `io.Reader`가 `Read` 하나만 가진 것처럼, 메서드가 하나인 인터페이스도 충분히 유용하다. 메서드가 많은 인터페이스는 구현하기 어렵고, 목업을 만들기도 번거롭다.

```go
// 메서드가 너무 많은 인터페이스
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

인터페이스는 구현하는 쪽이 아니라 사용하는 쪽에서 정의하는 것이 Go의 관행이다. 패키지 A가 인터페이스를 정의하고 패키지 B가 구현하는 것이 아니라, 패키지 B가 구체 타입을 제공하고 패키지 A가 자신에게 필요한 인터페이스를 직접 정의한다. 패키지 간 의존성이 줄어든다.

## 제네릭과 인터페이스

Go 1.18에서 제네릭이 도입되면서 인터페이스의 역할이 확장됐다. 제네릭에서 인터페이스는 타입 제약(type constraint)으로도 쓰인다.

```go
// 일반 인터페이스: 메서드 집합 정의
type Stringer interface {
    String() string
}

// 타입 제약으로 쓰이는 인터페이스: 타입 집합 정의
type Number interface {
    int | int8 | int16 | int32 | int64 |
    float32 | float64
}

func Sum[T Number](nums []T) T {
    var total T
    for _, n := range nums {
        total += n
    }
    return total
}
```

`Number`는 일반 인터페이스처럼 변수 타입으로 쓸 수 없다. 타입 파라미터 제약으로만 쓰인다.

```go
var n Number = 42  // 컴파일 에러: 타입 집합 인터페이스는 변수 타입으로 못 쓴다
```

### 언제 제네릭을 쓰고 언제 인터페이스를 쓰는가

이 판단이 실무에서 제일 헷갈린다.

인터페이스가 맞는 경우: 런타임에 다른 구현체로 교체해야 하거나, 외부 패키지가 구현을 제공해야 할 때.

```go
// DB 드라이버를 교체할 수 있어야 한다
type DB interface {
    QueryRow(query string, args ...any) *sql.Row
    Exec(query string, args ...any) (sql.Result, error)
}
```

제네릭이 맞는 경우: 타입만 다를 뿐 동일한 로직을 처리해야 할 때.

```go
// any를 쓰던 방식 — 런타임 타입 에러 위험
func Contains(slice []any, item any) bool {
    for _, v := range slice {
        if v == item {
            return true
        }
    }
    return false
}

// 제네릭으로 타입 안전하게
func Contains[T comparable](slice []T, item T) bool {
    for _, v := range slice {
        if v == item {
            return true
        }
    }
    return false
}
```

`any`로 받아서 타입 어서션이 필요한 코드라면 제네릭으로 바꿀 수 있는지 먼저 확인한다.

### 제네릭 제약에 메서드 포함

타입 집합과 메서드 요구를 함께 쓸 수 있다.

```go
type Ordered interface {
    int | float64 | string
}

// Stringer이면서 비교 가능한 타입
type PrintableOrdered interface {
    ~int | ~float64 | ~string
    String() string
}
```

`~int`는 int를 기반으로 하는 타입도 포함한다는 의미다.

```go
type Celsius float64
func (c Celsius) String() string { return fmt.Sprintf("%.1f°C", c) }

// Celsius는 ~float64를 만족한다
func PrintMin[T PrintableOrdered](a, b T) {
    if a < b {
        fmt.Println(a.String())
    } else {
        fmt.Println(b.String())
    }
}
```

### 제네릭 인터페이스

인터페이스 자체에 타입 파라미터를 넣을 수 있다.

```go
type Repository[T any] interface {
    FindByID(ctx context.Context, id int64) (T, error)
    Save(ctx context.Context, entity T) error
    Delete(ctx context.Context, id int64) error
}

type UserRepository struct{ db *sql.DB }

func (r *UserRepository) FindByID(ctx context.Context, id int64) (*User, error) { ... }
func (r *UserRepository) Save(ctx context.Context, user *User) error { ... }
func (r *UserRepository) Delete(ctx context.Context, id int64) error { ... }

// UserRepository는 Repository[*User]를 구현한다
var _ Repository[*User] = (*UserRepository)(nil)
```

반복적인 CRUD 패턴을 제네릭 인터페이스로 통일할 수 있다. 단, 이 방식은 인터페이스를 변수 타입으로 쓸 때 타입 파라미터를 명시해야 해서 코드가 다소 장황해질 수 있다.

## 인터페이스 성능

인터페이스 호출은 구체 타입 직접 호출보다 느리다. 내부적으로 vtable 룩업이 발생하기 때문이다. 핫패스에서 빡빡하게 성능을 짜야 한다면 고려해야 한다.

```go
// 벤치마크에서 차이가 나는 구간
type Adder interface {
    Add(a, b int) int
}

type ConcreteAdder struct{}
func (c ConcreteAdder) Add(a, b int) int { return a + b }

// 인터페이스를 통한 호출
func BenchmarkInterface(b *testing.B) {
    var adder Adder = ConcreteAdder{}
    for i := 0; i < b.N; i++ {
        adder.Add(1, 2)
    }
}

// 구체 타입 직접 호출
func BenchmarkConcrete(b *testing.B) {
    adder := ConcreteAdder{}
    for i := 0; i < b.N; i++ {
        adder.Add(1, 2)
    }
}
```

실제로는 메서드 내부 로직이 인터페이스 오버헤드보다 훨씬 크기 때문에, 대부분의 경우 차이는 무시할 수 있는 수준이다. 마이크로벤치마크로 확인하기 전에 인터페이스를 제거하는 최적화는 섣부르다.
