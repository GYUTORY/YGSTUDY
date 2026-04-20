---
title: Java Optional 심화
tags: [language, java, 컬렉션-및-데이터-처리, optional, npe]
updated: 2026-04-20
---

# Java Optional 심화

`Optional`은 Java 8에서 함수형 스타일의 API(Stream, CompletableFuture)와 함께 도입된 컨테이너 타입이다. 값이 있을 수도 있고 없을 수도 있다는 사실을 타입 시스템에 명시적으로 드러내기 위한 반환 타입이다. 실무에서 자주 오해받는 API이기도 한데, 필드에 박아 쓰거나 `get()`을 남발하면 오히려 null 체크보다 못한 코드가 된다. 내부 구조부터 평가 시점 차이, 설계 의도까지 정리한다.

---

## 1. Optional 내부 구조

### 1.1 클래스 선언과 value 필드

`java.util.Optional`은 다음과 같이 선언되어 있다.

```java
public final class Optional<T> {
    private static final Optional<?> EMPTY = new Optional<>();

    private final T value;

    private Optional() {
        this.value = null;
    }

    private Optional(T value) {
        this.value = Objects.requireNonNull(value);
    }

    public static <T> Optional<T> empty() {
        @SuppressWarnings("unchecked")
        Optional<T> t = (Optional<T>) EMPTY;
        return t;
    }

    public static <T> Optional<T> of(T value) {
        return new Optional<>(value);
    }

    public static <T> Optional<T> ofNullable(T value) {
        return value == null ? empty() : of(value);
    }
}
```

핵심은 `value`라는 **단일 필드 하나**로 모든 상태를 표현한다는 점이다. 값이 있으면 `value`에 참조가, 값이 없으면 `null`이 들어간다. 즉 내부적으로는 여전히 null이다. `Optional` 자체가 null을 대체하는 마법 같은 게 아니라 null 체크를 API로 감싼 얇은 래퍼일 뿐이다.

### 1.2 EMPTY 싱글톤

값이 없는 `Optional`은 타입마다 따로 만들지 않는다. `EMPTY`라는 `Optional<?>` 싱글톤을 캐스팅해서 재사용한다. 제네릭은 타입 소거(type erasure)되기 때문에 런타임에는 `Optional<String>`이든 `Optional<User>`이든 동일한 EMPTY 인스턴스다. `Optional.empty()`를 수억 번 호출해도 객체 생성 비용은 0이다.

반대로 값이 있는 `Optional`은 호출할 때마다 새로 `new Optional<>(value)`를 만든다. 이게 뒤에서 얘기할 메모리 오버헤드의 원인이다.

### 1.3 final 클래스와 private 생성자

`final class`로 선언되어 상속이 막혀 있고, 생성자가 전부 `private`이다. 이유는 두 가지다.

- **불변성 보장**: 서브클래스가 `value`를 mutable하게 만들거나 동등성 규칙을 깨뜨릴 여지를 차단한다.
- **값 기반 클래스(value-based class)**: Java가 value-based 타입으로 지정한 몇 안 되는 JDK 클래스다. `==` 비교, synchronized 사용, identity 의존 코드가 금지된다. Project Valhalla의 primitive class로 전환될 후보이기도 하다.

인스턴스 생성을 정적 팩토리 메서드(`of`, `ofNullable`, `empty`)로 강제하는 건 의도적이다. 사용자가 `new Optional(null)`로 빈 Optional을 만들 수 없게 막아둔 거다.

### 1.4 Serializable을 구현하지 않은 이유

`Optional`은 `Serializable`을 구현하지 않는다. 이게 실무에서 중요한 제약이다.

```java
public class UserDto implements Serializable {
    private Optional<String> nickname;  // NotSerializableException 발생 가능
}
```

DTO 필드에 `Optional`을 넣고 RMI/세션 직렬화/캐시 저장을 시도하면 `NotSerializableException`이 터진다. 설계자 Brian Goetz가 Stack Overflow에 직접 답변한 바에 따르면, "Optional은 라이브러리 메서드 반환 타입으로만 쓰라고 만든 거지 범용 Maybe 타입이 아니다". 직렬화는 장기 보관되는 데이터 포맷인데 Optional은 그 용도로 설계되지 않았다는 뜻이다.

---

## 2. NPE 방지 패턴

### 2.1 of vs ofNullable

둘의 차이는 명확하다. `of`는 null이면 `NullPointerException`을 바로 던지고, `ofNullable`은 null이면 `empty()`를 돌려준다.

```java
Optional<String> a = Optional.of(name);          // name이 null이면 즉시 NPE
Optional<String> b = Optional.ofNullable(name);  // name이 null이면 empty
```

실무에서 언제 뭘 쓸까. 값이 null일 리가 없다고 확신할 때(불변 상수, 방금 계산한 결과)는 `of`가 낫다. null이 넘어오면 그건 버그니까 조기에 터트리는 게 맞다. 외부에서 받은 값, DB 조회 결과처럼 null 가능성이 있는 입력은 `ofNullable`을 쓴다.

실수하기 쉬운 패턴이 하나 있다. 

```java
return Optional.of(userRepository.findByEmail(email));
```

`findByEmail`이 null을 반환할 수 있는데 `of`로 감싸면 이 코드는 null 대신 NPE를 던지는 코드가 된다. null 방지하려고 Optional을 썼는데 오히려 NPE를 던지는 셈이다. Repository가 nullable을 반환할 때는 반드시 `ofNullable`을 써야 한다.

### 2.2 체이닝 패턴

Optional의 진가는 체이닝에 있다. 명령형으로 null 체크를 중첩하던 코드를 납작하게 펼 수 있다.

```java
// 명령형: 중첩 if
public String getCityName(User user) {
    if (user != null) {
        Address address = user.getAddress();
        if (address != null) {
            City city = address.getCity();
            if (city != null) {
                return city.getName();
            }
        }
    }
    return "UNKNOWN";
}

// Optional 체이닝
public String getCityName(User user) {
    return Optional.ofNullable(user)
            .map(User::getAddress)
            .map(Address::getCity)
            .map(City::getName)
            .orElse("UNKNOWN");
}
```

`map` 내부에서 null을 반환하면 자동으로 `empty()`로 변환된다. 중간에 하나라도 null이면 체인이 끊기고 `orElse`로 떨어진다. 이 동작 덕분에 null 체크 보일러플레이트가 사라진다.

### 2.3 반환 메서드 설계 원칙

Optional을 반환 타입으로 설계할 때 지켜야 할 규칙이 있다.

- **Optional 자체를 null로 반환하지 않는다.** `return null;` 대신 항상 `Optional.empty()`를 쓴다. Optional을 쓰는 이유는 null을 없애려는 건데 Optional이 null이면 그냥 NPE를 한 단계 더 숨긴 거다.
- **Collection/Array/Map 반환에는 쓰지 않는다.** 빈 컬렉션을 반환하는 게 관례다. `Optional<List<T>>`보다 빈 `List<T>`가 낫다.
- **primitive 전용 Optional을 고려한다.** `OptionalInt`, `OptionalLong`, `OptionalDouble`이 있다. 박싱 비용을 피할 수 있다.
- **find/lookup 스타일 메서드에 쓴다.** `findById`, `findByEmail`처럼 "없을 수도 있다"가 정상 시나리오인 메서드 반환 타입으로 적합하다.

---

## 3. orElse vs orElseGet 평가 시점 차이

실무에서 가장 자주 실수하는 지점이다. 두 메서드의 동작은 비슷해 보이지만 평가 시점이 다르다.

### 3.1 동작 차이

```java
public T orElse(T other) {
    return value != null ? value : other;
}

public T orElseGet(Supplier<? extends T> supplier) {
    return value != null ? value : supplier.get();
}
```

`orElse`는 인자로 값 자체를 받는다. 메서드를 호출하는 시점에 인자 식이 **무조건 먼저 평가**된다. Optional에 값이 있어도 인자는 이미 계산된 상태다. 이게 eager evaluation이다.

`orElseGet`은 `Supplier`를 받는다. Optional이 비어 있을 때만 `supplier.get()`이 호출된다. 값이 있으면 Supplier 본문은 실행조차 되지 않는다. 이게 lazy evaluation이다.

### 3.2 성능 차이가 큰 경우

기본값이 리터럴이나 이미 있는 객체라면 어느 쪽을 쓰든 의미 있는 차이는 없다.

```java
String name = optional.orElse("UNKNOWN");            // OK
String name = optional.orElseGet(() -> "UNKNOWN");   // OK, 그러나 과잉
```

문제는 기본값 생성 비용이 클 때다.

```java
// 실제로 겪은 사례: 캐시 미스 시 DB 재조회하도록 fallback 설계
User user = cache.get(userId)
        .orElse(userRepository.findById(userId).orElseThrow());
```

이 코드는 cache에 값이 있어도 `userRepository.findById(userId)`가 **항상 호출**된다. 캐시의 의미가 사라진다. `orElseGet`으로 바꿔야 한다.

```java
User user = cache.get(userId)
        .orElseGet(() -> userRepository.findById(userId).orElseThrow());
```

비슷한 함정이 new 객체를 기본값으로 쓸 때 나타난다.

```java
// 매 호출마다 new LinkedList() 생성
List<Order> orders = userOrders.orElse(new LinkedList<>());

// 비어 있을 때만 생성
List<Order> orders = userOrders.orElseGet(LinkedList::new);
```

루프에서 이 코드가 돌아가면 GC 압박이 늘어난다. 한 번은 프로덕션에서 초당 수천 번 호출되는 API에 `orElse(new ArrayList<>())`가 들어가 있어서 YoungGen GC가 유발되는 걸 본 적 있다. 빈 컬렉션 기본값은 `Collections.emptyList()`나 `orElseGet(ArrayList::new)`로 바꿔야 한다.

### 3.3 판단 기준

단순하게 외워두면 된다. `orElse` 인자에 **부작용이 있거나, 비용이 큰 식**을 넣지 않는다. new, 메서드 호출, 로깅, DB 접근이 들어간다면 `orElseGet`을 쓴다. 상수나 이미 존재하는 필드 참조라면 `orElse`로 충분하다.

`orElseThrow` 역시 `Supplier`를 받아서 lazy하게 동작한다. 예외 객체 생성 비용(stack trace 생성)도 무시하기 어려우니 이쪽은 항상 lazy 버전이 맞다.

---

## 4. get() 안티패턴

### 4.1 isPresent + get 조합의 문제

```java
Optional<User> user = userRepository.findById(id);
if (user.isPresent()) {
    return user.get().getName();
}
return "UNKNOWN";
```

이 코드는 일반 null 체크와 기능적으로 동일하다. Optional을 쓴 의미가 없다.

```java
User u = userRepository.findByIdOrNull(id);
if (u != null) {
    return u.getName();
}
return "UNKNOWN";
```

둘은 바이트코드 수준에서도 비슷하게 동작하는 명령형 코드다. Optional의 존재 이유인 "값이 없을 수 있다"는 타입 정보를 활용하지 못하고 있다. `map`과 `orElse`로 선언적으로 바꿔야 한다.

```java
return userRepository.findById(id)
        .map(User::getName)
        .orElse("UNKNOWN");
```

### 4.2 get() 자체의 위험

`get()`은 값이 없으면 `NoSuchElementException`을 던진다. null 체크 없이 `get()`을 부르는 건 null 체크 없이 역참조하는 것과 동일한 수준의 실수다. Java 10부터는 `get()`의 대안으로 `orElseThrow()` 무인자 버전이 추가됐다.

```java
// 기존
T value = optional.get();

// Java 10+ 권장
T value = optional.orElseThrow();
```

두 메서드는 동일하게 `NoSuchElementException`을 던지지만, `orElseThrow`라는 이름이 "없으면 던진다"는 의도를 명시한다. `get()`은 언뜻 보면 값이 항상 있을 것 같은 이름이라 리뷰할 때 놓치기 쉽다. 팀 컨벤션으로 `get()` 사용을 금지하고 `orElseThrow()`로 통일하는 게 안전하다.

### 4.3 의미 있는 예외로 변환

진짜로 값이 없으면 안 되는 상황에서는 비즈니스 예외로 바꿔야 한다.

```java
User user = userRepository.findById(id)
        .orElseThrow(() -> new UserNotFoundException(id));
```

`NoSuchElementException`은 스택 트레이스만 보면 어디서 터졌는지 알기 어렵다. 도메인 예외로 감싸면 로그만 봐도 무슨 리소스가 없었는지 바로 파악된다.

---

## 5. Stream과의 조합

### 5.1 map이 Optional을 반환할 때 - flatMap

`Optional.map`은 함수의 반환값을 Optional로 감싼다. 함수 자체가 이미 Optional을 반환하면 `Optional<Optional<T>>`가 되어 버린다.

```java
public Optional<Address> findAddress(User user) { ... }

// 잘못된 조합: Optional<Optional<Address>>
Optional<Optional<Address>> nested = userOptional.map(this::findAddress);

// flatMap으로 평탄화
Optional<Address> address = userOptional.flatMap(this::findAddress);
```

`flatMap`은 함수가 반환한 Optional을 그대로 사용한다. 이중 래핑을 한 단계 벗긴다고 기억하면 된다. `Stream.flatMap`과 정확히 같은 개념이다.

메서드 체이닝에서 Optional 반환 메서드가 섞일 때는 `map`과 `flatMap`을 구분해서 써야 한다.

```java
return userRepository.findById(id)     // Optional<User>
        .flatMap(this::findPrimaryEmail)  // 내부도 Optional<Email> 반환
        .map(Email::getAddress)           // 일반 String 반환
        .orElse("no-email");
```

### 5.2 Stream.flatMap(Optional::stream) (Java 9+)

Java 9에서 `Optional.stream()`이 추가됐다. 값이 있으면 단일 원소 Stream, 없으면 빈 Stream을 돌려준다. 이 메서드 덕분에 Optional 컬렉션을 평탄화하는 관용구가 간단해졌다.

```java
// Java 8: filter + map + get 조합
List<Address> addresses = users.stream()
        .map(this::findAddress)       // Stream<Optional<Address>>
        .filter(Optional::isPresent)
        .map(Optional::get)
        .collect(Collectors.toList());

// Java 9+
List<Address> addresses = users.stream()
        .map(this::findAddress)       // Stream<Optional<Address>>
        .flatMap(Optional::stream)
        .collect(Collectors.toList());
```

전자는 `get()`이 들어가 있어 불안해 보이고(실제로는 filter 덕분에 안전하지만) 의도도 덜 명확하다. 후자는 "있는 것만 펼친다"는 의도가 타입으로 드러난다.

### 5.3 findFirst / findAny

Stream의 종단 연산 중 `findFirst`, `findAny`는 Optional을 반환한다. 스트림이 비어 있을 수 있다는 사실을 타입으로 표현한 거다.

```java
Optional<User> admin = users.stream()
        .filter(User::isAdmin)
        .findFirst();

String name = admin.map(User::getName).orElse("NO_ADMIN");
```

이걸 `.get()`으로 바로 까면 빈 Stream일 때 런타임 예외가 터진다. 반드시 `orElse`, `orElseThrow`, `ifPresent` 중 하나로 처리해야 한다.

---

## 6. 필드/파라미터에 Optional을 쓰면 안 되는 이유

### 6.1 Brian Goetz의 설계 의도

Optional을 만든 Brian Goetz의 답변은 명확하다.

> "Optional is intended to provide a limited mechanism for library method return types where there is a clear need to represent 'no result'. Using it for something else, like a field or a method parameter, is misuse."

즉 Optional은 **반환 타입 전용**이다. 필드/파라미터/컬렉션 요소로 쓰는 건 설계 의도에서 벗어난 오용이다.

### 6.2 직렬화 문제

앞서 언급했듯 Optional은 `Serializable`을 구현하지 않는다. 필드에 Optional을 쓰면 이 클래스는 직렬화 가능한 DTO가 될 수 없다.

```java
public class UserDto implements Serializable {
    private String name;
    private Optional<String> nickname;  // 직렬화 실패
}
```

Jackson은 잭슨 모듈(`jackson-datatype-jdk8`)을 쓰면 JSON 직렬화는 되지만, JPA Entity, RMI, 세션 저장 같은 JVM 직렬화 의존 기능에서는 깨진다. 필드는 그냥 nullable String으로 두고 getter만 `Optional<String>`을 반환하는 패턴이 관례다.

```java
public class User {
    private String nickname;  // 필드는 nullable

    public Optional<String> getNickname() {
        return Optional.ofNullable(nickname);
    }
}
```

### 6.3 메모리 오버헤드

Optional은 객체다. 값 하나를 래핑하려고 별도 힙 객체를 하나 더 만든다. 필드 1000개를 가진 엔티티에 Optional을 쓰면 헤더(12~16바이트) × 1000만큼 추가 메모리가 든다.

단일 필드에서는 무시할 수준이지만 컬렉션 요소로 쓰면 상황이 다르다.

```java
List<Optional<User>> users = ...;  // User 수만큼 Optional 객체 추가
```

`List<User>`에 null을 허용하거나, 애초에 null을 넣지 않는 설계가 낫다.

### 6.4 파라미터로 받으면 안 되는 이유

```java
// 안티패턴
public void updateUser(Long id, Optional<String> nickname) { ... }
```

호출자에게 "Optional을 만들어서 넘기라"고 강제하는 꼴이다. 다음과 같은 문제가 있다.

- 호출자가 `null`을 넘길 수 있다. `updateUser(1L, null)`은 컴파일 에러가 아니다. Optional 파라미터라서 null-safe하다고 생각한 순간 NPE가 난다.
- `Optional.of(x)`를 감싸서 호출하는 번거로움이 생긴다.
- 메서드 오버로딩(`updateUser(Long)`, `updateUser(Long, String)`)이 더 자연스러운 표현이다.

선택적 파라미터는 오버로딩이나 Builder 패턴으로 해결하는 게 Java의 관례다.

### 6.5 생성자 파라미터도 마찬가지

```java
public User(String name, Optional<String> nickname) {  // 안티패턴
    this.name = name;
    this.nickname = nickname;  // 필드로 Optional 저장 - 이중 안티패턴
}
```

생성자에는 nullable을 그대로 받고, 필요하면 오버로딩하거나 Builder를 쓴다. 외부에 "nickname이 선택적"이라는 정보를 노출하고 싶다면 getter를 `Optional`로 돌려주면 된다.

---

## 7. 실무 주의사항

### 7.1 Collection 반환은 빈 컬렉션이 관례

`List`, `Set`, `Map`, 배열은 빈 상태로 "값 없음"을 표현할 수 있다. Optional로 감쌀 필요가 없다.

```java
// 안티패턴
public Optional<List<Order>> findOrders(Long userId) { ... }

// 관례
public List<Order> findOrders(Long userId) {
    // 없으면 Collections.emptyList() 반환
}
```

Optional로 감싸면 호출자가 `if (opt.isPresent())`와 `if (!list.isEmpty())` 두 번 체크해야 한다. 이중 null 체크와 똑같은 구조다.

### 7.2 primitive 전용 Optional

`Optional<Integer>`는 박싱된 Integer를 래핑한다. 박싱 비용과 힙 할당이 두 번 일어난다. JDK는 primitive 전용 Optional을 따로 제공한다.

- `OptionalInt` - `getAsInt()`, `orElse(int)`, `orElseGet(IntSupplier)`
- `OptionalLong` - `getAsLong()`
- `OptionalDouble` - `getAsDouble()`

```java
OptionalInt count = users.stream()
        .mapToInt(User::getAge)
        .max();

int age = count.orElse(0);
```

`IntStream.max()`, `LongStream.average()` 같은 primitive Stream의 종단 연산이 이 타입을 반환한다. API가 이미 갖다주는 거라면 그대로 쓰면 된다. 직접 반환 타입으로 설계할 때도 박싱 비용이 신경 쓰이면 primitive 전용을 고려한다.

### 7.3 Optional.equals 동작

값 기반 동등성이다. 내부 `value`를 `Objects.equals`로 비교한다.

```java
Optional.of("a").equals(Optional.of("a"));        // true
Optional.of("a").equals(Optional.of("b"));        // false
Optional.empty().equals(Optional.empty());        // true
Optional.of("a").equals("a");                     // false (타입이 다름)
```

`equals`는 `Optional` 래퍼 대 래퍼로 비교하는 거지, 래퍼와 내부 값을 비교하는 게 아니다. Map 키로 쓰거나 assertEquals로 검증할 때 헷갈리기 쉬운 지점이다.

### 7.4 Optional의 복사 비용

앞서 EMPTY는 싱글톤이지만 값이 있는 Optional은 매번 새로 만든다고 언급했다. 반복 호출되는 핫패스에서는 Optional 생성 비용도 체감된다.

```java
// 루프 1000만 번 - Optional 1000만 개 생성
for (User u : users) {
    Optional.ofNullable(u.getName())
            .map(String::toUpperCase)
            .ifPresent(this::process);
}
```

대부분은 JIT이 escape analysis로 스택 할당하거나 인라인해서 문제되지 않는다. 하지만 프로파일러에서 Optional이 핫스팟으로 잡힌다면 해당 루프에서는 null 체크로 되돌리는 것도 선택지다. Optional은 가독성 향상 도구지 성능 도구가 아니다.

### 7.5 빈 Optional에 map/filter를 호출하면

빈 Optional에 `map`, `filter`, `flatMap`을 걸어도 예외가 나지 않는다. 그냥 아무것도 안 하고 빈 Optional이 연쇄된다.

```java
Optional<String> result = Optional.<String>empty()
        .map(String::toUpperCase)     // 호출 안 됨
        .filter(s -> s.length() > 3); // 호출 안 됨
// result == Optional.empty()
```

이 덕분에 긴 체인을 짜도 안전하다. 대신 `map` 안쪽 코드가 실행되지 않는다는 사실 때문에 로깅이나 부작용을 넣으면 디버깅이 어려워진다. `map`/`filter`에는 순수 함수만 넣는 게 원칙이다.

---

## 정리

Optional은 "값 없음"을 타입으로 드러내기 위한 **반환 타입 전용** 도구다. 내부는 단일 value 필드와 EMPTY 싱글톤으로 이뤄진 얇은 래퍼이고, final 클래스에 private 생성자, Serializable 미구현이라는 제약은 설계 의도를 반영한다.

실무에서 기억할 포인트는 다음과 같다. `of`와 `ofNullable`의 의미를 구분해서 쓴다. `orElse`는 인자를 항상 평가하니 비용이 큰 기본값은 `orElseGet`을 쓴다. `isPresent + get` 조합과 무인자 `get()`은 쓰지 않고 `map/orElse/orElseThrow`로 선언적으로 작성한다. `Optional<Optional<T>>`가 되면 `flatMap`을, Stream과 조합할 때는 `Optional::stream`을 활용한다. 필드/파라미터/컬렉션 요소로는 절대 쓰지 않는다. 컬렉션 반환은 빈 컬렉션으로, primitive는 전용 Optional로 처리한다. 이 원칙만 지키면 Optional이 NPE 방지와 API 가독성 두 마리를 같이 잡아주는 도구로 기능한다.
