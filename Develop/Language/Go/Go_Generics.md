---
title: Go 제네릭
tags: [Go, Golang, generics, 타입파라미터, 타입제약]
---

# Go 제네릭

Go 1.18에서 추가됐다. 릴리즈 당시 커뮤니티 반응은 극과 극이었다. 10년 넘게 기다렸던 기능이라 환영하는 쪽도 있었고, Go 철학(단순함)을 해친다는 비판도 있었다. 지금은 표준 라이브러리에서도 쓰이고(`slices`, `maps` 패키지), 실무에서도 점점 자리를 잡아가고 있다.

## 타입 파라미터 기본

함수나 타입에 타입 파라미터를 추가해서 여러 타입에서 동작하는 코드를 작성한다. 대괄호 안에 파라미터 이름과 제약(constraint)을 쓴다.

```go
func Map[T, U any](slice []T, f func(T) U) []U {
    result := make([]U, len(slice))
    for i, v := range slice {
        result[i] = f(v)
    }
    return result
}

// 사용
nums := []int{1, 2, 3}
strs := Map(nums, strconv.Itoa)  // []string{"1", "2", "3"}
```

타입 파라미터가 여러 개면 쉼표로 구분한다. 위 예제에서 `T`는 입력 슬라이스 원소 타입, `U`는 출력 슬라이스 원소 타입이다.

## 타입 제약

### any와 comparable

`any`는 모든 타입을 허용한다. `interface{}`의 타입 별칭이다. `any`를 제약으로 쓰면 실제로 할 수 있는 연산이 없다. 값을 받고 넘기는 것 외에는 아무것도 못 한다.

`comparable`은 `==`와 `!=` 연산이 가능한 타입만 허용한다. 맵 키로 쓸 수 있는 타입 전체가 여기 해당된다.

```go
func Contains[T comparable](slice []T, item T) bool {
    for _, v := range slice {
        if v == item {
            return true
        }
    }
    return false
}
```

슬라이스, 맵, 함수는 `comparable`을 만족하지 않는다. 이 타입들은 `==`로 비교할 수 없기 때문이다.

### union 제약

파이프(`|`)로 여러 타입을 나열하면 그 타입들만 허용한다.

```go
type Number interface {
    int | int8 | int16 | int32 | int64 |
        uint | uint8 | uint16 | uint32 | uint64 |
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

union 제약을 가진 인터페이스는 타입 파라미터 제약으로만 쓸 수 있다. 일반 변수 타입으로 쓰면 컴파일 에러가 난다.

```go
var n Number = 42  // 컴파일 에러
```

### 틸드(~) 제약

`~T`는 `T`를 기반 타입(underlying type)으로 하는 모든 타입을 포함한다. 정의한 타입도 제약을 만족시키려면 틸드가 필요한 경우가 많다.

```go
type Celsius float64
type Fahrenheit float64

type Float interface {
    ~float32 | ~float64
}

func Abs[T Float](x T) T {
    if x < 0 {
        return -x
    }
    return x
}

// Celsius와 Fahrenheit 모두 ~float64를 만족한다
c := Celsius(-10.5)
fmt.Println(Abs(c))  // 10.5
```

`float64`만 쓰면 `Celsius`는 제약을 통과하지 못한다. 기반 타입이 같아도 Go는 이를 다른 타입으로 본다.

### 메서드와 타입 집합 조합

제약 인터페이스에 메서드와 타입 집합을 함께 쓸 수 있다.

```go
type Stringer interface {
    String() string
}

type PrintableNumber interface {
    ~int | ~float64
    Stringer
}
```

이 제약은 기반 타입이 `int`나 `float64`이면서 `String() string` 메서드를 가진 타입만 허용한다. 실무에서는 이렇게 복잡한 제약을 쓸 일이 많지는 않다.

## constraints 패키지

`golang.org/x/exp/constraints` 패키지에 자주 쓰는 제약들이 미리 정의되어 있다. 표준 라이브러리에 아직 포함되지 않은 실험적 패키지다.

```go
import "golang.org/x/exp/constraints"

// constraints.Ordered: < > <= >= 비교가 가능한 타입
// int, float, string 계열 전부 포함
func Min[T constraints.Ordered](a, b T) T {
    if a < b {
        return a
    }
    return b
}

// constraints.Integer: 정수 타입만
// constraints.Float: 부동소수점만
// constraints.Signed: 부호 있는 정수만
// constraints.Unsigned: 부호 없는 정수만
// constraints.Complex: 복소수 타입
```

Go 1.21에서 표준 라이브러리에 `slices`와 `maps` 패키지가 추가됐는데, 내부적으로 이와 유사한 제약을 직접 정의해서 쓴다. 외부 의존성이 부담스러우면 제약 인터페이스를 직접 정의해도 된다.

```go
// 직접 정의하는 경우
type Ordered interface {
    ~int | ~int8 | ~int16 | ~int32 | ~int64 |
        ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
        ~float32 | ~float64 |
        ~string
}
```

## 타입 추론

타입 파라미터를 명시하지 않아도 인수에서 추론할 수 있으면 컴파일러가 알아서 채운다.

```go
func Keys[K comparable, V any](m map[K]V) []K {
    keys := make([]K, 0, len(m))
    for k := range m {
        keys = append(keys, k)
    }
    return keys
}

m := map[string]int{"a": 1, "b": 2}

// 명시적 타입 파라미터
keys1 := Keys[string, int](m)

// 타입 추론 — 대부분의 경우 이쪽을 쓴다
keys2 := Keys(m)
```

추론이 되는 경우에도 명시적으로 타입을 쓸 수 있다. 코드가 복잡해서 어떤 타입이 들어오는지 불분명할 때는 명시하는 편이 읽기 쉽다.

타입 추론이 실패하는 경우도 있다. 반환 타입만으로는 추론이 안 된다.

```go
func Zero[T any]() T {
    var zero T
    return zero
}

// 반환 타입으로는 추론 불가 — 명시해야 한다
z := Zero[int]()
```

## 제네릭 구조체

함수뿐 아니라 구조체에도 타입 파라미터를 쓸 수 있다.

```go
type Stack[T any] struct {
    items []T
}

func (s *Stack[T]) Push(item T) {
    s.items = append(s.items, item)
}

func (s *Stack[T]) Pop() (T, bool) {
    if len(s.items) == 0 {
        var zero T
        return zero, false
    }
    item := s.items[len(s.items)-1]
    s.items = s.items[:len(s.items)-1]
    return item, true
}

func (s *Stack[T]) Len() int {
    return len(s.items)
}
```

메서드에서 타입 파라미터를 쓸 때는 수신자에 `[T]`를 붙인다. 메서드 자체에 새로운 타입 파라미터를 추가할 수는 없다.

```go
// 컴파일 에러: 메서드에 새 타입 파라미터 추가 불가
func (s *Stack[T]) Map[U any](f func(T) U) []U { ... }
```

메서드에 새 타입이 필요하면 패키지 레벨 함수로 만들어야 한다.

```go
func StackMap[T, U any](s *Stack[T], f func(T) U) []U {
    result := make([]U, s.Len())
    for i, item := range s.items {
        result[i] = f(item)
    }
    return result
}
```

## 제네릭 함수 패턴

### 필터

```go
func Filter[T any](slice []T, pred func(T) bool) []T {
    var result []T
    for _, v := range slice {
        if pred(v) {
            result = append(result, v)
        }
    }
    return result
}

// 사용
evens := Filter([]int{1, 2, 3, 4, 5}, func(n int) bool { return n%2 == 0 })
```

### Reduce

```go
func Reduce[T, U any](slice []T, init U, f func(U, T) U) U {
    acc := init
    for _, v := range slice {
        acc = f(acc, v)
    }
    return acc
}

total := Reduce([]int{1, 2, 3, 4}, 0, func(acc, n int) int { return acc + n })
```

### 제네릭 캐시

```go
type Cache[K comparable, V any] struct {
    mu    sync.RWMutex
    items map[K]V
}

func NewCache[K comparable, V any]() *Cache[K, V] {
    return &Cache[K, V]{items: make(map[K]V)}
}

func (c *Cache[K, V]) Get(key K) (V, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    v, ok := c.items[key]
    return v, ok
}

func (c *Cache[K, V]) Set(key K, value V) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = value
}
```

`any`를 쓰던 시절에는 꺼낼 때마다 타입 어서션이 필요했다. 제네릭으로 바꾸면 컴파일 타임에 타입이 보장된다.

## 언제 제네릭을 쓰고 언제 안 쓰는가

### 제네릭이 맞는 상황

컨테이너나 유틸리티 함수에서 타입만 다를 뿐 로직이 동일할 때다. 슬라이스, 맵, 큐 같은 자료구조나 앞서 본 Map/Filter/Reduce 같은 함수가 여기 해당된다.

```go
// 제네릭 전: 타입별로 함수를 따로 만들거나 any를 써야 했다
func ContainsInt(slice []int, item int) bool { ... }
func ContainsString(slice []string, item string) bool { ... }

// 제네릭: 하나로 통합
func Contains[T comparable](slice []T, item T) bool { ... }
```

### 인터페이스가 맞는 상황

런타임에 다른 구현체로 교체해야 하는 경우, 또는 외부 패키지가 구현을 제공해야 하는 경우에는 인터페이스가 맞다.

```go
// 테스트에서 목업으로 교체하거나, 다른 DB 드라이버로 바꿔야 한다
type UserRepository interface {
    FindByID(ctx context.Context, id int64) (*User, error)
    Save(ctx context.Context, user *User) error
}
```

제네릭은 컴파일 타임에 타입이 확정된다. 런타임 다형성이 필요하면 인터페이스를 써야 한다.

### 코드 중복이 나은 상황

로직이 비슷해 보여도 타입에 따라 미묘하게 다른 경우가 있다. 억지로 제네릭으로 통합하다가 코드가 더 복잡해지는 경우도 있다. 두세 줄짜리 함수를 제네릭으로 만들어서 타입 제약 인터페이스를 새로 정의하고 제약을 쓰는 것이 코드 양이 더 많아지기도 한다.

다음 상황에서는 중복을 남겨두는 것이 낫다.

- 각 타입별 로직에 차이가 있어서 분기가 필요한 경우
- 제네릭 버전이 오히려 읽기 어려워지는 경우
- 타입이 두 개뿐이고 앞으로도 늘어날 가능성이 없는 경우

### interface{}를 쓰는 상황

`encoding/json`처럼 런타임에 타입을 알 수 없는 경우다. JSON 역직렬화할 때 스키마가 가변적이거나, 리플렉션 기반 라이브러리를 만들 때는 `any`가 피할 수 없는 선택이다.

```go
// 타입을 미리 알 수 없는 경우
var raw map[string]any
json.Unmarshal(data, &raw)
```

## 타입 파라미터 제약 설계

자주 저지르는 실수가 제약을 너무 좁게 잡는 것이다. 제약은 함수 내부에서 실제로 필요한 연산만큼만 좁히면 된다.

```go
// 잘못된 제약: Sum 함수인데 왜 comparable이 필요한가?
func Sum[T interface{ comparable; ~int | ~float64 }](nums []T) T { ... }

// 맞는 제약: 덧셈만 필요하다
type Numeric interface {
    ~int | ~int8 | ~int16 | ~int32 | ~int64 |
        ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 |
        ~float32 | ~float64
}

func Sum[T Numeric](nums []T) T { ... }
```

반대로 너무 넓게 잡으면 함수 내부에서 아무것도 할 수 없다. `any`로 받으면 대입과 반환 외에 할 수 있는 게 없다.

## 제네릭 남용 주의

제네릭이 생겼다고 해서 모든 곳에 쓰는 것은 오히려 코드를 복잡하게 만든다. Go 코드 리뷰를 하다 보면 이런 패턴을 가끔 본다.

```go
// 과도한 제네릭: 이 함수에서 제네릭이 실제로 필요한가?
func ProcessUser[T UserLike](u T) error {
    // 내부에서 T의 특성을 거의 안 쓴다
    return doSomething(u)
}

// 인터페이스로 충분하다
type UserLike interface {
    GetID() int64
    GetName() string
}

func ProcessUser(u UserLike) error {
    return doSomething(u)
}
```

제네릭은 타입이 다를 때 동일한 로직을 재사용하는 도구다. 인터페이스로 충분한 곳에 제네릭을 쓰면 코드만 복잡해진다.

## 제네릭 코드의 성능

제네릭 함수는 컴파일 타임에 타입별로 특수화(specialization)되거나, 딕셔너리(GC shape stenciling) 방식으로 구현된다. Go 컴파일러는 현재 완전한 단형화(monomorphization)를 하지 않고, 같은 GC shape를 가진 타입끼리 코드를 공유한다.

실무에서 체감 가능한 성능 차이는 거의 없다. 핫패스에서 정말 문제가 되면 벤치마크로 확인하면 된다. 제네릭 도입을 성능 이유로 거부하는 경우는 대부분 과도한 걱정이다.

## 실무에서 제네릭으로 교체한 패턴

제네릭 이전에 `any`를 쓰던 유틸리티 함수들이 교체 대상이다.

```go
// 기존: any 반환, 꺼낼 때마다 어서션
func GetOrDefault(m map[string]any, key string, defaultVal any) any {
    if v, ok := m[key]; ok {
        return v
    }
    return defaultVal
}

// 제네릭: 타입 안전
func GetOrDefault[K comparable, V any](m map[K]V, key K, defaultVal V) V {
    if v, ok := m[key]; ok {
        return v
    }
    return defaultVal
}

timeout := GetOrDefault(config, "timeout", 30)  // int로 바로 쓸 수 있다
```

Go 1.21부터 표준 라이브러리의 `maps` 패키지에 이런 유틸리티들이 포함됐다. 직접 만들기 전에 표준 라이브러리에 있는지 먼저 확인하는 것이 좋다.
