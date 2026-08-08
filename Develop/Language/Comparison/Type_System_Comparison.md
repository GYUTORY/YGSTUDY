---
title: 타입 시스템 비교
tags: [java, typescript, go, rust]
updated: 2026-07-09
---

# 타입 시스템 비교

여러 언어를 오가며 작업하다 보면 타입 시스템의 차이가 생각보다 크다는 걸 느낀다. 같은 "정적 타입 언어"여도 Java와 Go는 인터페이스를 완전히 다른 방식으로 다루고, TypeScript의 타입은 런타임에서 완전히 사라진다. 이 차이를 제대로 이해하지 못하면 다른 언어로 이전할 때 같은 실수를 반복하게 된다.

---

## 명목적 타이핑 vs 구조적 타이핑

### 명목적 타이핑 (Java, TypeScript)

명목적 타이핑(Nominal Typing)은 타입의 이름으로 호환성을 판단한다. 같은 구조를 가진 두 타입이 있어도, 이름이 다르면 서로 다른 타입이다.

Java에서는 이게 명확하다. 클래스 `A`와 클래스 `B`가 같은 메서드를 구현했어도, `A` 타입 변수에 `B` 인스턴스를 넣으려면 명시적인 상속이나 인터페이스 구현이 필요하다.

```java
interface Printable {
    void print();
}

class Document implements Printable {
    public void print() { System.out.println("Document"); }
}

class Report {
    // print() 메서드가 있어도 Printable을 implements 하지 않으면
    public void print() { System.out.println("Report"); }
}

void process(Printable p) { p.print(); }

process(new Document()); // OK
process(new Report());   // 컴파일 에러 — Report는 Printable이 아님
```

TypeScript는 기본적으로 구조적 타이핑이지만, 클래스는 명목적 타이핑에 가깝게 동작하는 경우가 있다. 특히 `private` 필드가 있는 클래스끼리는 같은 구조여도 호환되지 않는다.

```typescript
class Dog {
    private name: string;
    constructor(name: string) { this.name = name; }
}

class Cat {
    private name: string;
    constructor(name: string) { this.name = name; }
}

let dog: Dog = new Cat("야옹"); // 에러
// private 필드가 있는 클래스는 구조가 같아도 호환 안 됨
```

반면 인터페이스는 순수하게 구조적으로 동작한다.

```typescript
interface Printable {
    print(): void;
}

class Report {
    print() { console.log("Report"); }
}

// Report가 Printable을 명시적으로 구현하지 않아도 통과
const p: Printable = new Report(); // OK
```

이 차이가 헷갈리는 이유는 TypeScript가 "구조적 타이핑 언어"라고 알려져 있는데, 클래스 레벨에서는 그렇지 않은 케이스가 존재하기 때문이다.

---

### 구조적 타이핑 (Go, Rust)

구조적 타이핑(Structural Typing)은 타입의 이름이 아니라 구조, 즉 가진 메서드나 필드의 집합으로 호환성을 판단한다.

Go의 인터페이스가 대표적이다. 인터페이스를 `implements` 하겠다고 선언할 필요 없이, 해당 메서드를 가지고 있으면 자동으로 인터페이스를 구현한 것으로 취급한다.

```go
type Printer interface {
    Print()
}

type Document struct{}

func (d Document) Print() {
    fmt.Println("Document")
}

// Document는 Printer를 명시적으로 구현하지 않았음
// 하지만 Print() 메서드가 있으므로 Printer로 사용 가능
func process(p Printer) {
    p.Print()
}

process(Document{}) // OK
```

이 방식의 실질적인 장점은 외부 패키지 타입에 대한 어댑터를 따로 만들 필요 없다는 점이다. `io.Reader` 인터페이스를 구현해야 한다면, 기존 타입에 `Read(p []byte) (n int, err error)` 메서드만 추가하면 된다. Java처럼 원본 클래스를 수정하거나 래퍼 클래스를 만들 필요가 없다.

반면 단점도 있다. 의도치 않은 인터페이스 구현이 발생할 수 있다. 어떤 struct가 특정 인터페이스를 구현하고 있는지 코드만 봐서는 바로 알기 어렵다. IDE 지원 없이는 추적이 힘들다.

Rust의 트레이트(trait)는 다르다. 구조적으로 보이지만, 실제로는 명시적으로 `impl Trait for Type`을 선언해야 한다. Go처럼 자동으로 되지 않는다.

```rust
trait Printable {
    fn print(&self);
}

struct Document;

impl Printable for Document {
    fn print(&self) {
        println!("Document");
    }
}

// 명시적 impl 없이는 트레이트로 사용 불가
```

Rust의 트레이트는 Go 인터페이스보다 명목적 타이핑에 더 가깝다. 외부 크레이트 타입에 트레이트를 구현하려면 "orphan rule" 제한이 걸린다. 내 크레이트에서 정의한 타입이나 내 크레이트에서 정의한 트레이트 중 하나는 반드시 내 크레이트 소속이어야 한다.

---

### 동적 타이핑 (JavaScript)

JavaScript는 런타임에 타입이 결정된다. 같은 변수에 문자열을 넣었다가 숫자를 넣어도 에러가 나지 않는다. 타입 체크가 없으므로 실수가 런타임까지 숨어있다가 터진다.

```javascript
function process(obj) {
    return obj.print(); // obj에 print가 없으면 런타임 에러
}

process({ print: () => console.log("OK") }); // 동작
process({ write: () => console.log("OK") }); // TypeError: obj.print is not a function
```

덕 타이핑(Duck Typing)이라고 부르는 이유가 여기 있다. `print()`를 호출하는 시점에 해당 메서드가 있으면 타입에 상관없이 동작한다. 구조적 타이핑과 비슷해 보이지만, 컴파일 타임이 아닌 런타임에 검증된다는 점이 다르다.

---

## 제네릭 구현 방식 차이

### Java: 타입 소거 (Type Erasure)

Java 제네릭은 컴파일 타임에만 존재하고 런타임에는 사라진다. 컴파일러가 타입 파라미터를 체크한 뒤, 바이트코드에는 `Object`로 변환해 버린다.

```java
List<String> strings = new ArrayList<>();
List<Integer> ints = new ArrayList<>();

// 런타임에는 둘 다 같은 타입
System.out.println(strings.getClass() == ints.getClass()); // true
```

이 구현 방식 때문에 몇 가지 제한이 생긴다.

```java
// 불가: 타입 파라미터로 인스턴스 생성
T obj = new T(); // 컴파일 에러

// 불가: instanceof 체크
if (list instanceof List<String>) {} // 컴파일 에러

// 불가: 기본 타입 사용
List<int> list; // 불가, List<Integer> 써야 함
```

기본 타입(`int`, `double` 등)을 제네릭 파라미터로 쓸 수 없는 것도 타입 소거 때문이다. `Object`로 변환되는 과정에서 기본 타입은 처리할 방법이 없다. 그래서 `Integer`, `Double` 같은 박싱 타입을 써야 하고, 박싱/언박싱 오버헤드가 발생한다.

성능 측면에서도 단형화된 코드보다 느리다. 런타임에 캐스팅이 계속 일어나고, 컴파일러 최적화도 덜 일어난다.

### Rust: 단형화 (Monomorphization)

Rust는 제네릭을 사용할 때 컴파일 타임에 각 타입에 대한 전용 코드를 생성한다. `Vec<i32>`와 `Vec<String>`은 런타임에 완전히 별개의 코드로 존재한다.

```rust
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];
    for item in list {
        if item > largest {
            largest = item;
        }
    }
    largest
}

// 컴파일 시 i32용 버전과 f64용 버전이 별도로 생성됨
largest(&[1, 2, 3]);      // i32 버전
largest(&[1.0, 2.0, 3.0]); // f64 버전
```

장점은 성능이다. 런타임 캐스팅이 없고 컴파일러가 각 타입에 맞게 최적화한다. Java처럼 박싱 타입을 쓸 필요도 없다.

단점은 바이너리 크기다. 타입별로 코드가 복제되므로 제네릭을 많이 쓸수록 바이너리가 커진다. 빌드 시간도 길어진다.

트레이트 객체(`dyn Trait`)를 쓰면 Java의 타입 소거와 비슷하게 동적 디스패치를 쓸 수 있다. 이 경우 단형화를 포기하는 대신 바이너리 크기를 줄일 수 있다.

```rust
// 정적 디스패치 (단형화)
fn process<T: Printable>(item: T) { item.print(); }

// 동적 디스패치 (트레이트 객체)
fn process(item: &dyn Printable) { item.print(); }
```

### Go: 진짜 제네릭 (Go 1.18+)

Go는 1.18에서 제네릭을 도입했다. 구현 방식은 두 방법의 중간 어딘가다. 컴파일러가 단형화와 딕셔너리 기반 공유 코드를 섞어서 사용한다.

```go
func Map[T, U any](slice []T, fn func(T) U) []U {
    result := make([]U, len(slice))
    for i, v := range slice {
        result[i] = fn(v)
    }
    return result
}

nums := Map([]int{1, 2, 3}, func(n int) string {
    return fmt.Sprintf("%d", n)
})
```

제약 조건은 인터페이스로 표현한다.

```go
type Number interface {
    ~int | ~float64
}

func Sum[T Number](nums []T) T {
    var total T
    for _, n := range nums {
        total += n
    }
    return total
}
```

Go 제네릭은 Rust만큼 표현력이 강하지 않다. 고차 타입(higher-kinded types)이 없고, 제약 조건도 상대적으로 단순하다. 그래도 제네릭 도입 전보다 `interface{}`를 남발하거나 타입 어서션을 반복하는 코드가 많이 줄었다.

---

## 인터페이스, 트레이트, 프로토콜

### Java 인터페이스

Java 인터페이스는 계약(contract)이다. 무엇을 해야 하는지 명세하고, 이를 구현하는 클래스는 반드시 선언한다.

Java 8 이후 `default` 메서드가 추가되면서 인터페이스에 구현을 넣을 수 있게 됐다. 이로 인해 추상 클래스와의 경계가 흐려졌다.

```java
interface Collection<E> {
    int size();
    boolean isEmpty();

    // default 구현 제공
    default boolean contains(Object o) {
        for (E e : this) {
            if (e.equals(o)) return true;
        }
        return false;
    }
}
```

다중 상속이 안 되는 Java에서 인터페이스는 여러 개를 동시에 구현할 수 있다. 이게 Java에서 인터페이스를 자주 쓰는 이유 중 하나다.

### Go 인터페이스

Go 인터페이스는 메서드 집합이다. 작게 유지하는 게 관행이다. 표준 라이브러리의 `io.Reader`는 메서드가 하나뿐이다.

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

// 조합
type ReadWriter interface {
    Reader
    Writer
}
```

인터페이스를 작게 쪼개고 필요할 때 조합하는 패턴이 Go 코드베이스 전반에 걸쳐 나타난다. 구현 측에서는 신경 쓸 필요가 없고, 사용 측에서 필요한 것만 정의한다.

실무에서 자주 쓰는 패턴은 테스트용 모킹이다. 외부 서비스 클라이언트를 인터페이스로 받으면, 구체 타입을 건드리지 않고 테스트용 구현체를 주입할 수 있다.

```go
type UserStore interface {
    Get(id string) (User, error)
    Save(user User) error
}

type UserService struct {
    store UserStore
}

// 테스트에서는 MockUserStore를 넣어도 UserService가 모름
```

### Rust 트레이트

Rust 트레이트는 Go 인터페이스보다 훨씬 많은 걸 표현할 수 있다. 연관 타입(associated type), 기본 구현, 트레이트 컴포지션, 트레이트 경계(bounds)를 지원한다.

```rust
trait Iterator {
    type Item; // 연관 타입

    fn next(&mut self) -> Option<Self::Item>;

    // 기본 구현 제공
    fn count(self) -> usize where Self: Sized {
        self.fold(0, |cnt, _| cnt + 1)
    }
}
```

트레이트 경계를 사용하면 함수 파라미터에 여러 트레이트를 동시에 요구할 수 있다.

```rust
fn process<T: Display + Clone + Debug>(item: T) {
    println!("{}", item);
    let cloned = item.clone();
    println!("{:?}", cloned);
}

// where 절로 가독성 향상
fn process<T>(item: T)
where
    T: Display + Clone + Debug,
{
    // ...
}
```

Go와 달리 외부 타입에 트레이트를 구현할 때 orphan rule이 걸린다. 표준 라이브러리 타입에 외부 크레이트 트레이트를 구현하거나, 그 반대가 안 된다. 이 제한이 처음엔 불편하지만, 라이브러리 간 충돌을 막는 역할을 한다.

### TypeScript 인터페이스

TypeScript 인터페이스는 순수하게 컴파일 타임 개념이다. 런타임에 흔적이 없다.

```typescript
interface Repository<T> {
    findById(id: string): Promise<T | null>;
    save(entity: T): Promise<void>;
    delete(id: string): Promise<void>;
}

// 구현 측에서 implements 선언 가능하지만
class UserRepository implements Repository<User> {
    async findById(id: string): Promise<User | null> { /* ... */ }
    async save(user: User): Promise<void> { /* ... */ }
    async delete(id: string): Promise<void> { /* ... */ }
}

// 선언 없이 구조만 맞춰도 통과
const repo: Repository<User> = {
    findById: async (id) => null,
    save: async (user) => {},
    delete: async (id) => {},
};
```

`type`과 `interface`를 선택해야 할 때가 자주 있다. 객체 형태를 정의할 때는 둘 다 쓸 수 있다. 차이는 `interface`는 선언 병합(declaration merging)이 되고, `type`은 유니온·인터섹션 같은 복잡한 타입 조합이 자유롭다는 점이다.

```typescript
// interface 선언 병합 — 같은 이름으로 여러 번 선언하면 합쳐짐
interface User { name: string; }
interface User { age: number; }
// 결과: { name: string; age: number; }

// type으로는 불가
type User = { name: string; };
type User = { age: number; }; // 에러: 중복 식별자
```

---

## 타입 추론 수준 차이

타입 추론의 깊이는 언어마다 다르다. 얼마나 추론해 주는지가 코드 작성 경험에 영향을 준다.

### Java

Java는 자바 10부터 `var`를 지원하지만, 지역 변수에만 쓸 수 있고 메서드 반환 타입이나 필드 타입은 명시해야 한다.

```java
// 지역 변수 추론 (Java 10+)
var list = new ArrayList<String>(); // ArrayList<String> 추론
var user = userService.findById(id); // 반환 타입 추론

// 메서드 시그니처에는 불가
var getUserById(String id) { ... } // 에러
```

제네릭 메서드 호출 시에는 타입 인자를 추론한다.

```java
// 명시적 타입 인자 없이도 추론
List<String> result = Collections.emptyList();
```

### Go

Go는 짧은 변수 선언(`:=`)으로 타입 추론을 쓴다. 함수 시그니처에는 타입을 명시해야 한다.

```go
// 타입 추론
name := "hello"           // string
count := 42              // int
ratio := 3.14            // float64
users := []User{}        // []User

// 함수에는 명시 필요
func process(users []User) (int, error) { ... }
```

Go는 추론 범위가 제한적이다. 복잡한 체인을 타고 들어가거나 크로스 패키지 추론은 안 된다. 단순하게 유지하는 게 Go의 설계 철학이기도 하다.

### Rust

Rust의 타입 추론은 범위가 넓다. 변수 선언 시점이 아니라 이후에 어떻게 쓰이는지까지 보고 타입을 결정한다.

```rust
// 나중에 collect하는 타입을 보고 Vec<i32>로 추론
let nums: Vec<i32> = (1..=5).collect();

// 타입 어노테이션 없이도 동작
let mut v = Vec::new();
v.push(1i32); // 여기서 Vec<i32>로 확정
v.push(2);    // 이후 push도 i32만 가능

// 클로저 파라미터도 추론
let doubled: Vec<i32> = nums.iter().map(|x| x * 2).collect();
```

함수 시그니처는 반드시 명시해야 한다. 추론 의존도가 높아지면 코드를 읽을 때 타입을 역추적해야 하는 문제가 생기는데, Rust는 경계를 함수 시그니처로 잡는다.

### TypeScript

TypeScript는 초기화 값에서 타입을 추론하고, 반환 타입도 추론한다. 하지만 복잡한 제네릭 함수에서는 추론이 실패해서 수동으로 타입을 넣어야 하는 경우가 있다.

```typescript
// 기본 추론
const name = "hello";    // string
const count = 42;        // number
const list = [1, 2, 3]; // number[]

// 반환 타입 추론
function greet(name: string) {
    return `Hello, ${name}`; // string으로 추론
}

// 제네릭 추론
function identity<T>(arg: T): T { return arg; }
const result = identity("hello"); // T = string으로 추론

// 추론 실패 케이스
const emptyArr = []; // any[]로 추론 — 나중에 문제 생김
```

`tsconfig.json`의 `noImplicitAny` 옵션을 켜면 `any`로 추론되는 케이스를 에러로 잡아준다. 이 옵션 없이 작성한 코드는 타입 안전성이 낮다.

---

## 언어별 타입 시스템 특징 요약

| 특성 | Java | TypeScript | Go | Rust | JavaScript |
|------|------|-----------|-----|------|-----------|
| 타이핑 방식 | 명목적 | 구조적 (인터페이스) | 구조적 | 명시적 구조적 | 동적 |
| 제네릭 구현 | 타입 소거 | 컴파일 타임만 | 부분 단형화 | 단형화 | 없음 |
| 런타임 타입 정보 | 있음 (Reflection) | 없음 | 제한적 | 없음 (기본) | 있음 |
| 기본 타입 제네릭 | 불가 (박싱 필요) | 해당 없음 | 가능 | 가능 | 해당 없음 |
| 외부 타입 확장 | 상속/래퍼 | 인터페이스 병합 | 암묵적 구현 | orphan rule 제한 | 프로토타입 체인 |

---

언어를 선택할 때 타입 시스템의 특성이 중요한 이유는, 타입 시스템이 코드의 구조 자체를 결정하기 때문이다. Go로 작성하면 작은 인터페이스를 많이 쓰는 구조가 자연스럽게 나오고, Java로 작성하면 상속 계층이나 구현 선언이 명확하게 드러난다. Rust는 트레이트 경계 설계가 아키텍처를 이끈다. 같은 기능을 구현해도 언어마다 코드 모양이 다른 게 단순한 문법 차이가 아니라 타입 시스템의 차이에서 오는 경우가 많다.
