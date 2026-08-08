---
title: Kotlin Null Safety
tags: [kotlin, language]
updated: 2026-07-27
---

# Kotlin Null Safety

Kotlin이 Java의 NPE 문제를 타입 시스템으로 해결했다는 말은 맞지만, 완벽하지는 않다. Java 코드와 섞거나, `!!`를 무심코 쓰거나, `var`로 선언한 필드를 스마트 캐스트에 기대면 런타임에 NPE가 그대로 터진다. 컴파일러가 막아주는 구간과 개발자가 직접 챙겨야 하는 구간을 정확히 구분해야 한다.

---

## 1. nullable 타입과 non-null 타입

Kotlin의 모든 타입은 기본이 non-null이다. null을 허용하려면 `?`를 명시해야 한다.

```kotlin
val name: String = "Alice"   // non-null — null 대입 불가
val name: String? = null     // nullable — null 가능

var age: Int = 0
var age: Int? = null
```

nullable 타입에 직접 메서드를 호출하면 컴파일 에러가 난다.

```kotlin
val name: String? = getName()
println(name.length)   // 컴파일 에러 — name이 null일 수 있음
```

이 제약이 Kotlin null 안전성의 핵심이다. null 가능성을 타입에 묶어버리면, 컴파일러가 null 체크 없이 접근하는 코드를 거부한다.

null 체크 방법은 크게 세 가지다: `if` 직접 체크, safe call(`?.`), non-null assertion(`!!`). 각각 용도와 위험이 다르다.

---

## 2. safe call (`?.`)

null이면 전체 표현식을 null로 단락(short-circuit)시킨다.

```kotlin
val city: String? = user?.address?.city

// user가 null이면 city = null
// user가 non-null이지만 address가 null이면 city = null
// 둘 다 non-null이면 city = address.city 값
```

safe call의 반환 타입은 항상 nullable이다. `user?.address?.city`의 타입은 `String?`이 된다. 나중에 이 값을 쓸 때 또 null 처리를 해야 한다.

safe call은 읽기 연산에서만 쓸 수 있는 게 아니라 쓰기에도 쓸 수 있다.

```kotlin
user?.address?.city = "Seoul"   // user나 address가 null이면 조용히 무시
```

메서드 호출도 마찬가지다.

```kotlin
user?.sendEmail()   // user가 null이면 sendEmail()이 호출되지 않음
```

`let`과 조합하면 null이 아닌 경우에만 블록을 실행할 수 있다.

```kotlin
user?.let { u ->
    sendEmail(u.email)
    updateLastSeen(u.id)
}
```

`if (user != null)` 블록과 동일하지만, 블록 안에서 `user`가 non-null임이 보장된다. 직접 `if` 체크를 쓰는 것과 차이는 없고 스타일 문제다. 다만 `var` 필드라면 `?.let`이 더 안전하다. 이유는 스마트 캐스트 섹션에서 설명한다.

---

## 3. Elvis 연산자 (`?:`)

null일 때 대신 쓸 값이나 동작을 지정한다.

```kotlin
val name = user?.name ?: "Unknown"
val port = config?.port ?: 8080
```

`throw`도 쓸 수 있다. null 허용 불가인 상황에서 즉시 예외를 던지는 패턴이다.

```kotlin
val user = findUser(id) ?: throw UserNotFoundException("$id")
val token = request.headers["Authorization"] ?: throw UnauthorizedException()
```

`return`도 가능하다.

```kotlin
fun processUser(id: Long) {
    val user = findUser(id) ?: return
    // 이하 코드에서 user는 non-null
    sendWelcomeEmail(user.email)
}
```

Elvis 연산자의 오른쪽은 표현식이기 때문에 복잡한 로직도 쓸 수 있지만, 길어지면 읽기 어려워진다. 오른쪽이 세 단어 이상이 되면 `if-else`로 풀어 쓰는 것이 낫다.

---

## 4. non-null assertion (`!!`)

`!!`는 컴파일러에게 "이 값은 null이 아님을 보장한다"고 단언하는 연산자다. null이면 `NullPointerException`이 발생한다. Java의 NPE와 동일하다.

```kotlin
val name = user!!.name   // user가 null이면 NullPointerException
```

`!!`가 필요한 상황은 있다. 논리적으로 null이 불가능하지만 타입 시스템이 그 사실을 증명하지 못하는 경우다.

```kotlin
val list = mutableListOf<String>()
list.add("first")
val first = list.firstOrNull()!!   // 방금 추가했으므로 null 불가능
```

문제는 이런 "논리적 보장"이 나중에 코드가 바뀌면 틀어진다는 것이다. `list.add()` 호출이 조건부로 바뀌거나 삭제되면 `!!`가 즉시 지뢰가 된다. `!!`를 쓸 때는 왜 null이 아닌지를 코드에 남겨야 한다.

실무에서 `!!` 남발이 일어나는 패턴 몇 가지다.

```kotlin
// 패턴 1: nullable 반환 메서드인데 "항상 있을 것"이라고 믿는 경우
val user = userRepository.findById(id)!!

// 패턴 2: Java interop에서 플랫폼 타입 처리가 귀찮아서
val name = javaObject.getName()!!

// 패턴 3: 테스트 코드에서 @BeforeEach로 초기화하는 필드
private lateinit var service: UserService   // 이건 lateinit을 쓰는 게 맞다
private var service: UserService? = null    // 매번 !!를 쓰는 잘못된 패턴
```

패턴 1은 운영 중 해당 ID가 존재하지 않는 경우가 생기면 NPE가 터진다. `?: throw NotFoundException()`이 맞다.

---

## 5. 스마트 캐스트가 풀리는 조건

null 체크 후 Kotlin 컴파일러는 해당 변수를 non-null 타입으로 자동 캐스트한다.

```kotlin
val name: String? = getName()

if (name != null) {
    println(name.length)   // 여기서 name은 String으로 스마트 캐스트
}
```

스마트 캐스트가 작동하지 않는 경우가 두 가지다.

**`var` 필드**

`var`로 선언된 변수는 null 체크 이후에도 다른 스레드가 변경할 수 있다. 컴파일러가 이를 알기 때문에 스마트 캐스트를 거부한다.

```kotlin
var name: String? = "Alice"

if (name != null) {
    println(name.length)   // 컴파일 에러 — var는 체크 이후 바뀔 수 있음
}
```

`val`로 바꾸면 해결된다. `val`은 재할당이 불가능해서 null 체크 이후 값이 변하지 않음을 보장한다.

```kotlin
val snapshot = name   // val에 복사
if (snapshot != null) {
    println(snapshot.length)   // OK
}
```

또는 `?.let`을 쓴다.

```kotlin
name?.let { println(it.length) }
```

`var`이어도 로컬 변수라면 단일 스레드에서는 스마트 캐스트가 될 때가 있다. 하지만 클래스 프로퍼티(`var`)는 다른 스레드 접근 가능성이 있어서 컴파일러가 보수적으로 거부한다.

**람다 캡처**

람다 안에서 캡처한 변수는 람다가 나중에 실행될 수 있어서 스마트 캐스트가 풀린다.

```kotlin
val name: String? = getName()

val lambda = {
    if (name != null) {
        println(name.length)   // 컴파일 에러
        // 람다가 언제 실행될지 모르기 때문에 name이 그 시점에 null일 수 있음
    }
}
```

인라인 람다(`let`, `run`, `apply` 등)는 예외다. 인라인 람다는 즉시 실행되고 컴파일러가 이를 알기 때문에 스마트 캐스트가 동작한다.

```kotlin
name?.let {
    println(it.length)   // OK — let은 inline이라 즉시 실행
}
```

`synchronized` 블록처럼 실행 시점이 보장되지 않는 람다는 스마트 캐스트가 안 된다.

---

## 6. Java 상호운용과 platform type

Java에서 넘어오는 타입은 Kotlin에서 플랫폼 타입(platform type)으로 처리된다. IDE에서 `String!`처럼 느낌표가 붙은 형태로 보인다. null 가능 여부를 Kotlin이 알 수 없는 상태다.

```java
// Java
public class UserRepository {
    public String findName(Long id) {
        if (id == null) return null;   // null 반환 가능
        return db.getName(id);
    }
}
```

```kotlin
val repo = UserRepository()
val name: String = repo.findName(1L)   // 컴파일 에러 없음
println(name.length)                   // 런타임 NPE — null이 String에 들어왔음
```

Kotlin 컴파일러가 경고를 주지 않는다. 플랫폼 타입을 `String`으로 받으면 non-null로 간주하는데, 실제로 null이 들어오면 런타임에 NPE가 터진다.

안전하게 처리하는 방법은 두 가지다.

첫 번째는 nullable로 받는 것이다.

```kotlin
val name: String? = repo.findName(1L)   // nullable로 명시적 수령
val length = name?.length ?: 0
```

두 번째는 Java 코드에 어노테이션을 추가하는 것이다. JetBrains의 `@NotNull`/`@Nullable`, JSR-305의 `@Nonnull`, Android의 어노테이션 등을 붙이면 Kotlin이 인식한다.

```java
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class UserRepository {
    public @NotNull String findName(@NotNull Long id) { ... }
    public @Nullable String findNickname(@NotNull Long id) { ... }
}
```

```kotlin
val name: String = repo.findName(1L)        // OK — @NotNull을 인식
val nick: String? = repo.findNickname(1L)   // nullable로 처리
```

외부 라이브러리를 Java로 쓸 때는 해당 라이브러리의 어노테이션 여부를 먼저 확인해야 한다. Spring Framework는 `@NonNull`/`@Nullable`이 잘 달려 있어서 Kotlin에서 쓸 때 비교적 안전하다. 어노테이션이 없는 레거시 라이브러리는 모든 반환값을 nullable로 받는 것이 기본 원칙이다.

플랫폼 타입의 또 다른 함정은 컬렉션이다. Java의 `List<String>`은 Kotlin에서 `List<String!>!`로 나온다. 리스트 자체도 null 가능, 원소도 null 가능이다.

```java
// Java
public List<String> getNames() {
    return Arrays.asList("Alice", null, "Bob");   // 원소에 null 포함
}
```

```kotlin
val names: List<String> = repo.getNames()   // 컴파일 OK
names.forEach { println(it.length) }        // "null"에서 NPE
```

이런 경우 filterNotNull()을 쓰거나 명시적으로 `List<String?>` 타입을 지정해야 한다.

---

## 7. `lateinit var`와 UninitializedPropertyAccessException

`lateinit`은 non-null 타입의 프로퍼티를 선언 시점에 초기화하지 않고 나중에 초기화할 때 쓴다. 주로 의존성 주입이나 테스트 `@BeforeEach`에서 쓰인다.

```kotlin
class UserService {
    @Autowired
    lateinit var userRepository: UserRepository

    fun findUser(id: Long): User {
        return userRepository.findById(id)   // 초기화 후라면 OK
    }
}
```

초기화 전에 접근하면 `UninitializedPropertyAccessException`이 발생한다. NPE와 달리 메시지가 명확하다: `lateinit property userRepository has not been initialized`.

```kotlin
class UserService {
    lateinit var repo: UserRepository

    fun getUser(): User {
        return repo.findFirst()   // UninitializedPropertyAccessException
    }
}

val service = UserService()
service.getUser()   // 초기화 없이 접근 — 예외 발생
```

초기화 여부를 확인하려면 `::프로퍼티.isInitialized`를 쓴다.

```kotlin
if (::repo.isInitialized) {
    repo.doSomething()
}
```

`lateinit`은 `var`에만 쓸 수 있고 `val`에는 쓸 수 없다. 원시 타입(`Int`, `Boolean` 등)에도 쓸 수 없다. 원시 타입은 nullable(`Int?`)로 쓰거나, 생성자에서 초기화하거나, `Delegates.notNull()`을 쓴다.

```kotlin
// 원시 타입에 lateinit 불가
lateinit var count: Int   // 컴파일 에러

// 대안
var count: Int by Delegates.notNull()   // 초기화 전 접근 시 IllegalStateException
```

`lateinit` 남발은 결국 `var`을 넓게 쓰는 것과 같아서 불변성을 해친다. `@Autowired` 같은 DI 프레임워크 필드나 테스트 픽스처 정도에만 한정해서 쓰는 것이 맞다.

---

## 정리

Kotlin null 안전성은 컴파일러가 강제하지만, 빠져나갈 구멍이 세 군데 있다.

첫째, `!!`. "null 아님을 안다"고 단언했는데 실제로는 null인 경우 NPE가 그대로 터진다. 쓸 때마다 이유가 명확해야 한다.

둘째, 플랫폼 타입. Java API를 Kotlin에서 non-null로 받으면 컴파일러가 경고하지 않는다. 외부 Java 코드의 모든 반환값은 nullable로 받거나 어노테이션이 붙어 있음을 확인한 뒤 써야 한다.

셋째, `lateinit`. 초기화 전 접근은 예외가 난다. 스프링 컨텍스트가 올라오기 전에 접근하거나, 테스트에서 `@BeforeEach`를 빠뜨리면 바로 터진다.
