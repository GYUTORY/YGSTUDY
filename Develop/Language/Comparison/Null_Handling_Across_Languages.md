---
title: 언어별 null 처리 방식 비교
tags: [Java, Go, Rust, TypeScript, Null, Optional, Option, Pointer]
updated: 2026-07-09
---

# 언어별 null 처리 방식 비교

null은 1965년 Tony Hoare가 "10억 달러짜리 실수"라고 부른 것이다. 그 이후 각 언어는 null을 어떻게 처리할 것인지에 대한 각기 다른 답을 내놓았다. Java는 `Optional`로 감싸고, Go는 포인터와 제로값을 구분하고, Rust는 `Option<T>`를 타입 시스템에 통합하고, TypeScript는 타입 레벨에서 null 가능성을 표시한다. 같은 "값이 없는" 상황을 표현하는데 언어마다 접근이 다르고, 런타임 오류가 터지는 지점도 다르다.

## Java: NullPointerException과 Optional

Java에서 null은 모든 참조 타입에 할당 가능하다. `String`, `List`, 직접 만든 클래스 모두 null이 될 수 있다. 문제는 런타임에 null 참조를 역참조(dereference)하면 `NullPointerException`이 터진다는 것인데, 이게 컴파일 타임에는 전혀 잡히지 않는다.

```java
// 컴파일은 잘 되지만 런타임에 NPE
String name = null;
int length = name.length(); // NullPointerException

// 메서드 체이닝에서 중간에 null이 끼면
String city = user.getAddress().getCity().toUpperCase();
// user, getAddress(), getCity() 중 하나라도 null이면 NPE
```

Java 8부터 `Optional<T>`가 생겼다. "이 값은 없을 수도 있다"는 의도를 타입으로 표현한다.

```java
public Optional<User> findUser(Long id) {
    return userRepository.findById(id);
}

// 사용하는 쪽
Optional<User> user = findUser(42L);

// 값이 있으면 처리, 없으면 기본값
String name = user.map(User::getName).orElse("Unknown");

// 값이 없으면 예외
User u = user.orElseThrow(() -> new UserNotFoundException("유저 없음"));

// 조건부 처리
user.ifPresent(u -> sendEmail(u.getEmail()));
```

`Optional`의 문제는 강제성이 없다는 것이다. 반환 타입을 `Optional<User>`로 선언하지 않고 그냥 `User`로 반환하면 null이 그대로 나간다. 받는 쪽이 null 체크를 안 하면 그대로 NPE다. `Optional`을 쓸지 말지 팀 내에서 합의하지 않으면, 어떤 메서드는 `Optional`로, 어떤 메서드는 null로 반환하는 일관성 없는 코드가 된다.

`@NotNull`, `@Nullable` 어노테이션을 IDE나 정적 분석 도구(SpotBugs, NullAway)와 함께 써서 컴파일 타임에 경고를 받을 수 있지만, 이건 언어 수준의 보장이 아니라 도구 수준의 보장이다. 빌드 파이프라인에 통합하지 않으면 로컬에서만 잡히고 CI에서 놓친다.

Java 14부터는 NPE 메시지가 훨씬 구체적으로 바뀌었다. `Cannot invoke "String.length()" because "name" is null`처럼 어떤 변수가 null인지 알려준다. 이전에는 "NullPointerException" 한 줄만 나와서 스택 트레이스를 뒤져야 했다.

## Go: 제로값과 포인터

Go는 null 개념 자체를 제로값(zero value)으로 대체한다. 선언만 하고 초기화하지 않은 변수는 타입의 제로값으로 자동 초기화된다.

```go
var i int       // 0
var s string    // ""
var b bool      // false
var f float64   // 0.0
var sl []int    // nil (슬라이스)
var m map[string]int // nil (맵)
```

슬라이스와 맵은 nil이어도 읽기 연산이 동작한다. nil 슬라이스의 `len()`은 0이고, nil 맵에서 키를 조회하면 제로값이 반환된다.

```go
var sl []int
fmt.Println(len(sl)) // 0, 패닉 없음
fmt.Println(sl[0])   // 이건 패닉 — 범위 초과

var m map[string]int
fmt.Println(m["key"]) // 0, 패닉 없음
m["key"] = 1          // 이건 패닉 — nil 맵에 쓰기
```

포인터는 nil이 될 수 있다. 포인터를 역참조할 때 nil이면 런타임 패닉이 발생한다.

```go
type User struct {
    Name string
    Age  int
}

func findUser(id int) *User {
    // 없으면 nil 반환
    if id != 1 {
        return nil
    }
    return &User{Name: "Alice", Age: 30}
}

user := findUser(99)
fmt.Println(user.Name) // nil 포인터 역참조 — 런타임 패닉
```

실무에서 Go의 nil 포인터 패닉은 Java의 NPE처럼 자주 만난다. 다만 Go에서는 `(값, 에러)` 반환 패턴 덕분에 "값이 없는" 상황을 에러로 표현하는 경우가 많아서, 순수하게 nil 포인터를 반환하는 케이스는 Java보다 적다.

"값이 있을 수도 없을 수도" 있는 필드를 표현할 때는 포인터 타입을 쓴다.

```go
type Config struct {
    Host    string
    Port    int
    Timeout *int // nil이면 기본값 사용
}

cfg := Config{Host: "localhost", Port: 8080}
if cfg.Timeout != nil {
    // 명시적으로 설정된 경우만
    fmt.Println(*cfg.Timeout)
}
```

Go 1.18부터 제네릭이 생겼지만, `Optional` 타입이 표준 라이브러리에 들어오지는 않았다. 제네릭으로 구현할 수 있지만 관례적으로 쓰이지는 않는다.

## Rust: Option<T>

Rust에는 null 자체가 없다. 값이 없는 상태를 표현하려면 반드시 `Option<T>`를 써야 한다. `Option<T>`는 `Some(T)` 또는 `None`이다.

```rust
fn find_user(id: u32) -> Option<User> {
    if id == 1 {
        Some(User { name: "Alice".to_string(), age: 30 })
    } else {
        None
    }
}

let user = find_user(99);
// user.name 에 직접 접근 불가 — Option을 먼저 처리해야 함
// user.name; // 컴파일 에러
```

`Option<T>` 안의 값을 꺼내려면 반드시 `None` 케이스를 처리해야 한다. 컴파일러가 강제한다.

```rust
// match로 처리
match find_user(1) {
    Some(user) => println!("{}", user.name),
    None => println!("유저 없음"),
}

// if let으로 처리
if let Some(user) = find_user(1) {
    println!("{}", user.name);
}

// 기본값 제공
let name = find_user(99).map(|u| u.name).unwrap_or("Unknown".to_string());

// 없으면 에러로 변환
let user = find_user(99).ok_or("유저 없음")?;
```

`unwrap()`은 `Some`이면 값을 꺼내고, `None`이면 패닉한다. Go의 nil 포인터 역참조와 같은 상황이지만, 이건 개발자가 의도적으로 선택한 것이 코드에 명시된다는 점이 다르다.

```rust
let user = find_user(99).unwrap(); // None이면 패닉 — 의도적 선택
let user = find_user(99).expect("유저가 반드시 있어야 함"); // 패닉 메시지 지정
```

체이닝도 깔끔하다. Java의 `Optional`과 비슷하지만 표준 라이브러리에서 훨씬 풍부한 메서드를 제공한다.

```rust
// 중첩 Option 처리
struct Address { city: Option<String> }
struct User { address: Option<Address> }

let city = user
    .as_ref()
    .and_then(|u| u.address.as_ref())
    .and_then(|a| a.city.as_ref())
    .map(|c| c.to_uppercase())
    .unwrap_or_default();
```

Java의 메서드 체이닝에서 중간에 null이 끼면 NPE가 런타임에 터지는 것과 달리, Rust에서 이 코드는 컴파일 타임에 안전성이 보장된다. `and_then`은 `None`을 만나면 그냥 `None`을 전파한다.

## TypeScript: strict null checks

TypeScript는 JavaScript 위에 타입을 올린 것이라 null과 undefined가 모두 존재한다. `strictNullChecks` 옵션을 켜면 null/undefined가 일반 타입에 들어올 수 없게 된다.

```typescript
// strictNullChecks: false (기본값)
let name: string = null; // 허용

// strictNullChecks: true
let name: string = null; // 컴파일 에러
let name: string | null = null; // 명시적으로 null 가능 표현
```

`strict: true` 옵션에 `strictNullChecks`가 포함되어 있다. 새 프로젝트라면 처음부터 켜는 것이 맞다. 기존 프로젝트에 나중에 켜면 에러가 수백 개 터져서 한 번에 적용하기 어렵다.

```typescript
function findUser(id: number): User | null {
    return users.find(u => u.id === id) ?? null;
}

const user = findUser(42);
// user.name; // 컴파일 에러 — user가 null일 수 있음

// null 체크 후 사용
if (user !== null) {
    console.log(user.name); // 이 블록 안에서는 User 타입으로 좁혀짐
}

// Optional chaining
const city = user?.address?.city; // user나 address가 null이면 undefined 반환

// Nullish coalescing
const name = user?.name ?? "Unknown";
```

TypeScript의 타입 좁히기(type narrowing)는 꽤 강력하다. null 체크, instanceof, in 연산자 등으로 타입을 좁히면 그 블록 안에서 타입이 자동으로 변한다.

```typescript
function processUser(user: User | null | undefined) {
    if (!user) return; // null과 undefined 모두 걸러냄

    // 여기서부터 user는 User 타입
    console.log(user.name);
}
```

non-null assertion 연산자(`!`)는 "나는 이게 null 아님을 안다"고 컴파일러에게 알리는 탈출구다. 남발하면 런타임에 오류가 터질 수 있어서 조심해야 한다.

```typescript
const user = findUser(42)!; // null이 아님을 단언
user.name; // 컴파일러는 OK, 실제로 null이면 런타임 오류
```

`as unknown as T`와 `!` 남발은 TypeScript를 쓰는 이유를 반감시킨다. 타입을 믿을 수 없으면 정적 분석의 이점이 없다.

## 언어별 비교

| 항목 | Java | Go | Rust | TypeScript |
|---|---|---|---|---|
| null 존재 여부 | 있음 | nil 있음 | 없음 (Option) | null, undefined 모두 있음 |
| 컴파일 타임 보장 | 없음 (도구 의존) | 없음 | 완전 보장 | strictNullChecks 켤 때 |
| 런타임 오류 | NullPointerException | nil 포인터 패닉 | unwrap() 패닉만 | TypeError |
| 값 없음 표현 | Optional<T>, null | nil, 포인터 타입 | Option<T> | T \| null, T \| undefined |
| 안전한 체이닝 | Optional.map | if ptr != nil | and_then | optional chaining (?.) |

Java와 Go는 null/nil이 언어에 존재하고 컴파일러가 체크하지 않아서 런타임에 터진다. 차이는 Go가 제로값으로 null이 아예 필요 없는 케이스를 줄인다는 것이다. Rust는 null 자체가 없어서 컴파일 타임 보장이 가장 강하다. TypeScript는 옵션에 따라 다른데, `strict: true` 없이 쓰면 JavaScript와 다를 게 없다.

null 관련 런타임 오류는 어느 언어에서나 생긴다. Rust에서도 `unwrap()`을 쓰면 패닉이 터진다. 차이는 그 오류가 컴파일 타임에 보이는지, 런타임에서야 보이는지다. Rust는 실수를 컴파일러가 잡아주고, 나머지 언어들은 개발자 규율이나 린터에 의존한다.
