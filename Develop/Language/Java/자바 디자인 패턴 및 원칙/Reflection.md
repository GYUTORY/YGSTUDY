---
title: Java Reflection
tags: [language, java, 자바-디자인-패턴-및-원칙, reflection]
updated: 2026-03-31
---

# Java Reflection

## 리플렉션이 하는 일

리플렉션은 런타임에 클래스의 메타데이터(필드, 메서드, 생성자, 어노테이션)를 읽고, 그 멤버를 호출하거나 값을 바꾸는 API다. 컴파일 타임에 타입을 모르는 상황에서 객체를 다뤄야 할 때 쓴다.

`java.lang.reflect` 패키지의 `Class`, `Field`, `Method`, `Constructor`가 핵심이고, JVM이 클래스를 로드할 때 만드는 `Class` 객체가 진입점이다.

```java
Class<?> clazz = Class.forName("com.example.UserService");
// 또는
Class<?> clazz = UserService.class;
// 또는
Class<?> clazz = userService.getClass();
```

세 가지 방식의 차이가 있다. `Class.forName()`은 클래스를 아직 로드하지 않았으면 로드하면서 static 블록을 실행한다. `.class`는 이미 컴파일 타임에 알고 있는 타입의 메타데이터를 가져오고, `getClass()`는 인스턴스의 실제 런타임 타입을 반환한다. 다형성을 쓰는 경우 `getClass()`가 선언 타입이 아닌 실제 구현 타입을 돌려주는 점을 기억해야 한다.

---

## getMethods() vs getDeclaredMethods()

이 둘의 차이를 모르면 버그가 생긴다.

| 메서드 | 범위 | 접근 제한자 |
|--------|------|-------------|
| `getMethods()` | 현재 클래스 + 상위 클래스 + 인터페이스의 **public** 메서드 | public만 |
| `getDeclaredMethods()` | 현재 클래스에 **직접 선언된** 모든 메서드 | private, protected, package-private 포함 |

같은 규칙이 `getFields()` / `getDeclaredFields()`, `getConstructors()` / `getDeclaredConstructors()`에도 적용된다.

실무에서 자주 겪는 실수:

```java
// 부모 클래스
public class BaseEntity {
    public Long getId() { return id; }
}

// 자식 클래스
public class User extends BaseEntity {
    private String email;
    public String getEmail() { return email; }
}
```

```java
// User.class.getDeclaredMethods()의 결과에 getId()는 없다
Method[] methods = User.class.getDeclaredMethods();
// [getEmail] — getId()를 찾으려면 getMethods()를 써야 한다

// 반대로 private 메서드를 찾으려면 getDeclaredMethods()를 써야 한다
// getMethods()는 public만 반환하므로 private helper는 나오지 않는다
```

프레임워크를 만들거나 커스텀 어노테이션 프로세서를 짤 때, 상속 계층 전체를 탐색해야 하면 `getDeclaredMethods()`를 재귀적으로 호출하면서 `getSuperclass()`를 타고 올라가는 패턴을 쓴다. `getMethods()`로 퉁치면 private/protected 메서드를 놓치고, `getDeclaredMethods()`만 쓰면 부모 메서드를 놓친다.

---

## setAccessible(true)로 private 멤버 접근하기

`setAccessible(true)`는 Java의 접근 제어를 런타임에 무시하는 호출이다.

```java
public class Config {
    private String secretKey = "abc123";
}
```

```java
Config config = new Config();
Field field = Config.class.getDeclaredField("secretKey");
// field.get(config); // IllegalAccessException 발생

field.setAccessible(true);
String value = (String) field.get(config); // "abc123"
field.set(config, "newSecret"); // 값 변경도 가능
```

Spring이 `@Autowired`로 private 필드에 의존성을 주입하는 게 이 방식이다. setter나 생성자 없이도 private 필드에 값을 넣을 수 있는 이유가 리플렉션 + `setAccessible(true)` 조합이다.

### 주의할 점

**final 필드 수정은 예측 불가능하다.** Java 12 이전에는 `setAccessible(true)` 후 final 필드를 바꿀 수 있었지만, JIT 컴파일러가 final 필드를 상수로 인라이닝해버리면 리플렉션으로 바꿔도 이전 값이 읽히는 현상이 발생한다. Java 12부터는 `Field.set()`이 final 필드에 대해 `IllegalAccessException`을 던진다.

```java
public class Settings {
    private final int timeout = 3000;
}

// Java 11까지
Field f = Settings.class.getDeclaredField("timeout");
f.setAccessible(true);
f.set(settings, 5000); // 동작은 하지만...
System.out.println(settings.timeout); // 3000이 출력될 수 있다 (JIT 인라이닝)

// Java 12+
f.set(settings, 5000); // IllegalAccessException
```

**테스트에서의 사용.** 테스트 코드에서 private 필드를 세팅해야 할 때 리플렉션을 직접 쓰기도 하는데, Spring 프로젝트라면 `ReflectionTestUtils.setField()`를 쓰는 게 낫다. 내부적으로 같은 일을 하지만 에러 메시지가 명확하다.

```java
// 리플렉션 직접 사용 대신
ReflectionTestUtils.setField(userService, "maxRetry", 5);
```

---

## 동적 프록시 (java.lang.reflect.Proxy)

`Proxy.newProxyInstance()`는 런타임에 인터페이스의 구현체를 동적으로 만든다. 컴파일 시점에 구현 클래스가 없어도 된다.

```java
public interface UserRepository {
    User findById(Long id);
    List<User> findAll();
}
```

```java
UserRepository proxy = (UserRepository) Proxy.newProxyInstance(
    UserRepository.class.getClassLoader(),
    new Class<?>[]{ UserRepository.class },
    (proxyObj, method, args) -> {
        System.out.println("호출된 메서드: " + method.getName());

        if (method.getName().equals("findById")) {
            // 실제로는 여기서 DB 쿼리를 만들어 실행
            return new User((Long) args[0], "test");
        }
        return null;
    }
);

User user = proxy.findById(1L); // "호출된 메서드: findById" 출력
```

### 이걸 쓰는 곳

**Spring AOP.** `@Transactional`, `@Cacheable` 같은 어노테이션이 동작하는 원리다. Spring은 빈을 생성할 때 인터페이스가 있으면 JDK 동적 프록시를, 없으면 CGLIB(바이트코드 조작)을 써서 프록시 객체를 만든다. 메서드 호출 전후에 트랜잭션 시작/커밋, 캐시 조회/저장 로직을 `InvocationHandler`에서 끼워넣는 구조다.

```java
// Spring이 내부적으로 하는 일의 단순화된 버전
public class TransactionHandler implements InvocationHandler {
    private final Object target;
    private final PlatformTransactionManager txManager;

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        if (method.isAnnotationPresent(Transactional.class)) {
            TransactionStatus status = txManager.getTransaction(new DefaultTransactionDefinition());
            try {
                Object result = method.invoke(target, args);
                txManager.commit(status);
                return result;
            } catch (Exception e) {
                txManager.rollback(status);
                throw e;
            }
        }
        return method.invoke(target, args);
    }
}
```

**JPA 지연 로딩.** `@ManyToOne(fetch = FetchType.LAZY)`로 설정한 연관 엔티티는 실제 객체가 아닌 프록시다. 해당 필드에 처음 접근하는 시점에 프록시의 `InvocationHandler`가 SQL을 날린다. `getClass()`로 확인하면 `User$HibernateProxy$abc123` 같은 클래스명이 보이는 이유다. `instanceof` 체크가 실패하거나, `equals()` 구현에서 `getClass()` 비교를 하면 프록시와 실제 엔티티가 다르게 나와서 버그가 생기는 경우가 흔하다.

**MyBatis Mapper.** `@Mapper` 인터페이스의 구현체를 직접 만들지 않아도 되는 이유가 동적 프록시다. 인터페이스의 메서드명과 XML/어노테이션의 SQL을 매핑해서 호출 시점에 쿼리를 실행한다.

### JDK 동적 프록시의 제약

인터페이스 기반으로만 동작한다. 구체 클래스를 프록시로 만들 수 없다. 이 제약 때문에 Spring은 인터페이스가 없는 빈에 CGLIB을 쓴다. Spring Boot 2.x부터는 기본값이 CGLIB 프록시로 바뀌었다(`spring.aop.proxy-target-class=true`).

---

## 리플렉션이 느린 이유

"리플렉션은 느리다"는 말을 많이 하지만, 구체적으로 왜 느린지 아는 개발자는 적다.

### 1. JIT 인라이닝 불가

일반 메서드 호출은 JIT 컴파일러가 호출 대상을 컴파일 타임에 확정하고, 자주 호출되는 메서드는 호출 지점에 코드를 인라이닝한다. 리플렉션 호출은 `Method.invoke()`를 통하기 때문에 실제 대상 메서드가 뭔지 JIT가 판단할 수 없다. 인라이닝이 안 되면 메서드 호출 오버헤드(스택 프레임 생성, 파라미터 전달)가 매번 발생한다.

### 2. 타입 체크와 박싱/언박싱

`Method.invoke(Object obj, Object... args)`의 시그니처를 보면, 파라미터가 `Object...`다. primitive 타입을 넘기면 박싱이 일어나고, 반환값이 primitive면 언박싱이 일어난다. 인자 배열 생성(varargs)도 매 호출마다 새 배열을 만든다.

```java
// 직접 호출 — 박싱 없음
int result = calculator.add(1, 2);

// 리플렉션 호출 — int → Integer 박싱, Object[] 배열 생성
Method addMethod = Calculator.class.getMethod("add", int.class, int.class);
Object result = addMethod.invoke(calculator, 1, 2); // 1, 2가 Integer로 박싱
```

### 3. SecurityManager 체크

`setAccessible(true)`를 호출하지 않은 경우, 매 접근마다 호출자에게 해당 멤버에 접근할 권한이 있는지 검사한다. SecurityManager가 설정된 환경에서는 추가 보안 체크까지 들어간다. (Java 17에서 SecurityManager가 deprecated 됐고 제거 예정이지만, 여전히 접근 제어 검사 자체는 남아있다.)

### 4. 메서드 탐색 비용

`getMethod()` 호출 시 클래스 계층을 따라 올라가며 메서드를 탐색한다. 매번 문자열 비교로 메서드명을 찾고, 파라미터 타입을 비교한다. 반복 호출할 거라면 `Method` 객체를 캐싱해야 한다.

```java
// 잘못된 방식 — 루프마다 메서드를 매번 탐색
for (Object item : items) {
    Method m = item.getClass().getMethod("process");
    m.invoke(item);
}

// 올바른 방식 — Method 객체를 캐싱
Method m = ItemProcessor.class.getMethod("process");
for (Object item : items) {
    m.invoke(item);
}
```

### MethodHandle 대안

Java 7에서 추가된 `java.lang.invoke.MethodHandle`은 리플렉션의 성능 문제를 일부 해결한다. JIT 컴파일러가 MethodHandle 호출을 인라이닝할 수 있고, 접근 권한 체크를 lookup 시점에 한 번만 수행한다.

```java
MethodHandles.Lookup lookup = MethodHandles.lookup();
MethodType mt = MethodType.methodType(String.class); // 반환타입
MethodHandle handle = lookup.findVirtual(User.class, "getName", mt);

String name = (String) handle.invoke(user);
```

`MethodHandle`은 한 번 만들어두면 반복 호출 시 일반 메서드 호출에 가까운 성능이 나온다. Jackson 같은 라이브러리가 내부적으로 리플렉션에서 MethodHandle로 전환하고 있는 이유다.

다만 MethodHandle의 API가 리플렉션보다 번거롭고, 동적으로 메서드명을 결정하는 시나리오에서는 여전히 리플렉션이 더 쓰기 편하다. 성능이 중요한 핫 패스에서 반복 호출이 필요하면 MethodHandle, 한두 번 호출이면 리플렉션으로 충분하다.

---

## Java 9+ 모듈 시스템과 리플렉션 제한

Java 9에서 도입된 모듈 시스템(JPMS)은 리플렉션의 동작을 크게 바꿨다. 모듈이 명시적으로 `exports`하지 않은 패키지의 클래스에 리플렉션으로 접근하면 `InaccessibleObjectException`이 발생한다.

```
java.lang.reflect.InaccessibleObjectException:
  Unable to make field private final byte[] java.lang.String.value accessible:
  module java.base does not "opens java.lang" to unnamed module
```

Java 8까지는 `setAccessible(true)`만 하면 JDK 내부 클래스의 private 필드도 마음대로 접근할 수 있었다. Java 9부터는 모듈 경계를 넘는 리플렉션이 기본적으로 차단된다.

### --add-opens

JVM 실행 시 `--add-opens` 옵션으로 특정 모듈의 패키지를 열 수 있다.

```bash
java --add-opens java.base/java.lang=ALL-UNNAMED \
     --add-opens java.base/java.lang.reflect=ALL-UNNAMED \
     -jar myapp.jar
```

문제는 이게 한두 개가 아니라는 거다. 라이브러리마다 접근하는 JDK 내부 패키지가 다르기 때문에, Java 8에서 11/17로 마이그레이션할 때 `--add-opens`를 하나씩 추가하면서 삽질하는 경우가 흔하다.

### 실무에서 겪는 상황

**Gradle/Maven 빌드에서의 설정.** 테스트나 애플리케이션 실행 시 JVM 인자로 넘겨야 한다.

```groovy
// build.gradle
tasks.withType(Test) {
    jvmArgs = [
        '--add-opens', 'java.base/java.lang=ALL-UNNAMED',
        '--add-opens', 'java.base/java.util=ALL-UNNAMED'
    ]
}
```

```xml
<!-- pom.xml (maven-surefire-plugin) -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <argLine>
            --add-opens java.base/java.lang=ALL-UNNAMED
            --add-opens java.base/java.util=ALL-UNNAMED
        </argLine>
    </configuration>
</plugin>
```

**Lombok과의 충돌.** Lombok은 컴파일러 내부 API에 리플렉션으로 접근하는데, Java 16부터 이 접근이 막혀서 `--add-opens`를 javac에 넘겨야 한다. `lombok.config`에 `lombok.addOpens = false`를 설정하면 경고를 끌 수 있지만 근본적인 해결은 아니다.

**Docker 이미지에서.** Dockerfile의 `ENTRYPOINT`나 `CMD`에 `--add-opens`를 넣어야 하는데, 라이브러리 업데이트할 때마다 필요한 옵션이 바뀔 수 있어서 관리가 번거롭다. 환경변수 `JDK_JAVA_OPTIONS`를 쓰면 한 곳에서 관리할 수 있다.

```dockerfile
ENV JDK_JAVA_OPTIONS="--add-opens java.base/java.lang=ALL-UNNAMED \
    --add-opens java.base/java.util=ALL-UNNAMED"
```

---

## Jackson/Gson의 리플렉션 사용과 record 클래스 문제

### JSON 라이브러리가 리플렉션을 쓰는 구조

Jackson이 JSON을 Java 객체로 역직렬화하는 과정:

1. 대상 클래스의 `Class` 객체를 얻는다
2. `getDeclaredFields()`로 필드 목록을 가져온다
3. JSON 키와 필드명을 매핑한다
4. 기본 생성자로 인스턴스를 만든다 (`Constructor.newInstance()`)
5. `setAccessible(true)`로 private 필드에 값을 넣거나, setter를 리플렉션으로 호출한다

Gson도 비슷한 구조인데, Gson은 기본적으로 필드 기반 접근을 한다. getter/setter 없이 private 필드에 직접 `setAccessible(true)` 후 값을 넣는다.

### record 클래스에서 깨지는 케이스

Java 16에서 정식 도입된 record는 기존 리플렉션 기반 직렬화와 충돌하는 경우가 있다.

```java
public record UserDto(String name, int age) {}
```

record의 특성:
- 기본 생성자가 없다. canonical 생성자(모든 필드를 받는 생성자)만 있다
- 필드가 `private final`이다
- setter가 없다

**Gson 문제.** Gson 2.10 이전 버전은 기본 생성자를 찾아서 인스턴스를 만든 뒤 필드에 값을 넣는 방식인데, record에는 기본 생성자가 없으므로 `RuntimeException`이 발생한다. Gson 2.10부터 record를 지원하지만, 이전 버전을 쓰는 프로젝트에서 record로 DTO를 바꾸면 런타임에 터진다.

```java
Gson gson = new Gson();
// Gson 2.9 이하에서
UserDto dto = gson.fromJson("{\"name\":\"kim\",\"age\":30}", UserDto.class);
// RuntimeException: Unable to create instance of class UserDto
```

**Jackson 문제.** Jackson은 2.12부터 record를 지원한다. 단, `jackson-module-parameter-names` 모듈을 등록하거나 컴파일 시 `-parameters` 옵션을 줘야 생성자 파라미터명을 읽을 수 있다. 이게 없으면 `arg0`, `arg1`로 인식돼서 JSON 키 매핑이 실패한다.

```java
// -parameters 없이 컴파일하면
// record UserDto(String name, int age)의 생성자 파라미터가
// arg0, arg1로 보여서 {"name":"kim","age":30}과 매핑 실패

// 해결 방법 1: 컴파일러 옵션
// javac -parameters UserDto.java

// 해결 방법 2: @JsonProperty로 명시
public record UserDto(
    @JsonProperty("name") String name,
    @JsonProperty("age") int age
) {}
```

### Java 17+ 모듈 시스템과의 조합

record + Java 17 모듈 시스템 + Gson의 조합이 특히 까다롭다. Gson이 record의 private final 필드에 `setAccessible(true)`를 시도하면 모듈 시스템이 차단한다. `--add-opens`를 추가하거나, Gson 버전을 올려서 canonical 생성자 기반 역직렬화를 쓰도록 해야 한다.

---

## Mockito/JUnit의 리플렉션 사용

### Mockito

`Mockito.mock(UserService.class)`를 호출하면 내부적으로 일어나는 일:

1. 대상 클래스의 `Class` 객체에서 모든 메서드를 리플렉션으로 읽는다
2. ByteBuddy(바이트코드 생성 라이브러리)로 대상 클래스를 상속한 서브클래스를 런타임에 만든다
3. 모든 메서드를 오버라이드해서 mock 동작(기본값 반환, 호출 기록)을 끼워넣는다
4. `when(...).thenReturn(...)`의 스텁 정보를 저장하고, 호출 시 매칭한다

`@InjectMocks`도 리플렉션이다. 대상 클래스의 생성자/필드를 리플렉션으로 읽고, `@Mock` 필드와 타입을 매칭해서 주입한다. 생성자 주입 → setter 주입 → 필드 주입 순서로 시도한다.

**final 클래스/메서드 mock.** Mockito 2.x부터 final 클래스도 mock할 수 있지만, `src/test/resources/mockito-extensions/org.mockito.plugins.MockMaker` 파일에 `mock-maker-inline`을 설정하거나, Mockito 5.x에서는 기본값으로 켜져있다. 이게 내부적으로 Java Agent를 사용해서 바이트코드를 조작하는 방식이라, Java 16+에서 `--add-opens` 이슈가 생긴다.

### JUnit 5

JUnit 5의 테스트 실행 과정에서 리플렉션이 쓰이는 부분:

- `@Test` 어노테이션이 붙은 메서드를 찾을 때 `getDeclaredMethods()`로 탐색
- 테스트 인스턴스를 만들 때 `Constructor.newInstance()`로 생성
- `@BeforeEach`, `@AfterEach` 같은 라이프사이클 메서드를 리플렉션으로 호출
- `@ParameterizedTest`에서 `@MethodSource`가 가리키는 static 메서드를 리플렉션으로 찾아 실행

private 메서드에 `@Test`를 붙여도 JUnit이 `setAccessible(true)` 후 실행하기 때문에 동작한다. 다만 테스트 메서드를 private으로 만들 이유는 없으므로 관례상 package-private이나 public을 쓴다.

---

## 리플렉션의 내부 동작

### invoke()가 실제로 하는 일

`Method.invoke()`를 처음 호출하면 네이티브 코드로 구현된 `NativeMethodAccessorImpl`이 사용된다. 같은 메서드를 반복 호출해서 `ReflectionFactory.inflationThreshold`(기본값 15) 횟수를 넘으면, JVM이 바이트코드를 동적으로 생성해서 `GeneratedMethodAccessor`로 교체한다. 이 과정을 "inflation"이라고 부른다.

```
// 첫 15번 호출: NativeMethodAccessorImpl (느림)
// 16번째부터: GeneratedMethodAccessorXXX (바이트코드 생성, 빠름)
```

이 최적화 덕분에 반복 호출 시에는 성능이 개선되지만, 최초 바이트코드 생성 비용이 있다. `-Dsun.reflect.inflationThreshold=0`으로 설정하면 처음부터 바이트코드를 생성하는데, 한 번만 호출하는 메서드가 많으면 오히려 느려진다.

### 리플렉션과 제네릭

리플렉션에서 제네릭 타입 정보를 읽을 수 있다. Java의 제네릭은 컴파일 타임에 소거(erasure)되지만, 클래스 선언부나 필드/메서드 시그니처의 제네릭 정보는 클래스 파일에 남아있다.

```java
public class UserService {
    private List<User> users;

    public Optional<User> findById(Long id) { ... }
}
```

```java
Field field = UserService.class.getDeclaredField("users");
Type genericType = field.getGenericType(); // java.util.List<com.example.User>

if (genericType instanceof ParameterizedType pt) {
    Type[] typeArgs = pt.getActualTypeArguments();
    System.out.println(typeArgs[0]); // class com.example.User
}
```

Jackson이 `List<User>`와 `List<Order>`를 구분해서 역직렬화할 수 있는 게 이 메커니즘 덕분이다. `TypeReference<List<User>>(){}`를 넘기면 내부에서 `getGenericSuperclass()`를 호출해서 타입 파라미터를 읽는다.

---

## 리플렉션을 써야 하는 상황과 피해야 하는 상황

리플렉션이 적절한 경우:

- 프레임워크/라이브러리 내부 — 사용자가 정의한 클래스를 런타임에 다뤄야 하는 경우
- 테스트 코드 — private 멤버에 접근해서 테스트 셋업을 해야 하는 경우
- 직렬화/역직렬화 — 범용 JSON/XML 변환기를 만드는 경우
- 플러그인 시스템 — 외부 jar에서 클래스를 로드하는 경우

리플렉션을 피해야 하는 경우:

- 일반 애플리케이션 비즈니스 로직 — 타입 안정성을 포기할 이유가 없다
- 성능이 중요한 핫 패스 — 매 요청마다 리플렉션으로 메서드를 찾고 호출하면 안 된다
- 컴파일 타임에 타입을 알 수 있는 경우 — 인터페이스나 추상 클래스로 다형성을 쓰면 된다

리플렉션 코드는 컴파일러가 타입 체크를 못 하므로, 필드명이나 메서드명을 문자열로 지정하는 부분에서 오타가 나면 런타임에야 발견된다. 리팩토링 도구(IDE의 이름 변경)도 리플렉션의 문자열 인자는 변경하지 못한다. 리플렉션을 쓰는 코드는 테스트를 반드시 작성해야 하는 이유다.
