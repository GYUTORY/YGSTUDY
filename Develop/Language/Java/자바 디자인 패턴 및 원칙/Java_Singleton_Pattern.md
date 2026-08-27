---
title: Java 싱글톤 — 멀티스레드·직렬화·ClassLoader 문제
tags: [java, spring, design-patterns]
updated: 2026-08-27
---

# Java 싱글톤 — 멀티스레드·직렬화·ClassLoader 문제

Java에서 싱글톤을 구현하는 방법은 여러 가지인데, 멀티스레드 환경에서 정확히 동작하면서 직렬화·리플렉션까지 방어하는 구현은 생각보다 까다롭다. 그리고 "JVM에서 하나"라는 보장은 ClassLoader가 하나일 때만 성립한다.

## double-checked locking은 volatile 없이 틀렸다

멀티스레드 환경에서 lazy initialization을 구현할 때 자주 시도하는 패턴이다.

```java
public class Config {
    private static Config instance;

    private Config() {}

    public static Config getInstance() {
        if (instance == null) {           // 첫 번째 체크
            synchronized (Config.class) {
                if (instance == null) {   // 두 번째 체크
                    instance = new Config();
                }
            }
        }
        return instance;
    }
}
```

`instance = new Config()`는 JVM 수준에서 세 단계다. 메모리 할당, 생성자 실행, 참조 저장. 문제는 JIT 컴파일러와 CPU가 이 순서를 최적화할 수 있다는 점이다. 참조 저장이 생성자 실행보다 먼저 일어날 수 있다. 그러면 다른 스레드가 첫 번째 체크에서 null이 아님을 확인하고 반환받은 객체는 아직 생성자가 완료되지 않은 상태다.

`volatile`이 이 문제를 막는다. Java 5에서 재정의된 `volatile` 메모리 모델은 `volatile` 쓰기 이전의 모든 동작이 그 쓰기가 보이는 시점에 함께 보임을 보장한다. `instance = new Config()`가 `volatile` 필드에 쓰는 것이므로, 다른 스레드가 null이 아닌 `instance`를 볼 때는 생성자까지 완료된 상태다.

```java
public class Config {
    private static volatile Config instance;  // volatile 필수

    private Config() {}

    public static Config getInstance() {
        if (instance == null) {
            synchronized (Config.class) {
                if (instance == null) {
                    instance = new Config();
                }
            }
        }
        return instance;
    }
}
```

`volatile`이 없는 double-checked locking은 Java 4까지 그냥 버그다. Java 5 이상에서 `volatile`을 붙여야 정확히 동작한다. 그런데 이 구현보다 static holder가 훨씬 단순하다.

## static holder가 나은 이유

Initialization-on-demand holder 패턴이라고도 한다. JVM 클래스 로딩 보장을 직접 활용한다.

```java
public class Config {
    private Config() {}

    private static class Holder {
        private static final Config INSTANCE = new Config();
    }

    public static Config getInstance() {
        return Holder.INSTANCE;
    }
}
```

`Holder` 클래스는 `getInstance()`가 처음 호출될 때 로드된다. JLS §12.4.1이 보장하는 클래스 초기화 직렬화 덕분에, `synchronized`나 `volatile` 없이도 스레드 안전하다. ClassLoader 레벨의 잠금이 이미 직렬화를 처리하기 때문이다.

lazy initialization이 자연스럽게 구현된다. `Config` 클래스 자체가 로드될 때 `Holder`는 로드되지 않는다. `getInstance()`를 처음 호출하는 시점에 `Holder`가 로드되고 `INSTANCE`가 초기화된다.

한 가지 주의점이 있다. `Config`에 다른 static 메서드나 static 필드가 있으면, 그것을 쓰기 위해 `Config` 클래스가 로드되더라도 `Holder`는 로드되지 않는다. `getInstance()`를 처음 호출하는 시점에 `Holder`가 초기화된다. 이 lazy 타이밍이 의도한 것인지 확인해야 한다.

## enum 싱글톤 — 직렬화·리플렉션 방어

Effective Java에서 권장하는 방식이다. 직렬화와 리플렉션 공격을 JVM이 자동으로 처리한다.

```java
public enum Config {
    INSTANCE;

    private final String apiUrl;

    Config() {
        this.apiUrl = System.getenv().getOrDefault("API_URL", "http://localhost:3000");
    }

    public String getApiUrl() { return apiUrl; }
}

// 사용
Config.INSTANCE.getApiUrl();
```

### 직렬화가 싱글톤을 깨는 방식

일반 클래스에서 `Serializable`을 구현하면 역직렬화할 때 새 인스턴스가 만들어진다. JVM이 스트림에서 객체를 복원할 때 생성자를 거치지 않고 바이트를 직접 인스턴스로 변환하기 때문이다.

```java
Config c1 = Config.getInstance();

ByteArrayOutputStream baos = new ByteArrayOutputStream();
new ObjectOutputStream(baos).writeObject(c1);

Config c2 = (Config) new ObjectInputStream(
    new ByteArrayInputStream(baos.toByteArray())
).readObject();

System.out.println(c1 == c2); // false — 다른 인스턴스
```

`readResolve()`를 구현하면 막을 수 있다. 역직렬화 직후 이 메서드가 호출되어 반환값이 실제로 역직렬화된 인스턴스를 대체한다.

```java
protected Object readResolve() {
    return INSTANCE;
}
```

빠뜨리기 쉽고 상속 관계에서 추가로 신경 써야 한다. enum은 JVM이 직렬화를 특수 처리해서 이 과정이 필요 없다. enum 상수는 이름으로 직렬화·역직렬화되므로 항상 같은 인스턴스가 반환된다.

### 리플렉션이 싱글톤을 깨는 방식

`private` 생성자도 리플렉션으로 우회할 수 있다.

```java
Constructor<Config> ctor = Config.class.getDeclaredConstructor();
ctor.setAccessible(true);
Config c2 = ctor.newInstance(); // 싱글톤이 깨진다
```

생성자 안에서 방어하는 방법이 있다.

```java
private Config() {
    if (INSTANCE != null) {
        throw new IllegalStateException("이미 인스턴스가 존재한다");
    }
}
```

그런데 eager initialization에서만 동작한다. `INSTANCE` 초기화가 생성자 호출 전이어야 하는데, static 필드 초기화와 생성자 호출은 같은 클래스 초기화 과정에서 일어나므로 순서가 보장되지 않는 경우가 있다.

enum은 `Constructor.newInstance()`가 `IllegalArgumentException: Cannot reflectively create enum objects`를 던진다. JVM 레벨에서 막힌다.

### enum의 한계

lazy initialization이 없다. enum 클래스가 처음 참조될 때 바로 초기화된다. 초기화 비용이 크거나 쓰이지 않을 수도 있는 경우엔 static holder가 낫다.

상속도 안 된다. enum은 암묵적으로 `java.lang.Enum`을 상속하므로 다른 클래스를 상속할 수 없다. 인터페이스는 구현할 수 있다.

`Config.INSTANCE`로 전역 접근을 강제해서 테스트에서 가짜 구현으로 교체하기 어렵다. 테스트에서 설정을 바꿔야 하는 경우엔 인터페이스를 두고 DI 방식을 쓰는 것이 낫다.

## ClassLoader가 여러 개면 "JVM에서 하나"가 아니다

싱글톤이 JVM 전체에서 하나라는 보장은 ClassLoader가 하나일 때만 성립한다. Java 프로세스 안에서도 ClassLoader가 여러 개면 같은 클래스가 여러 번 로드될 수 있다.

```
ClassLoader A가 로드한 com.example.Config → 인스턴스 A
ClassLoader B가 로드한 com.example.Config → 인스턴스 B

ClassLoaderA의 Config.getInstance() != ClassLoaderB의 Config.getInstance()
```

이 두 Class 객체는 같은 이름이지만 다른 타입이다. 한쪽에서 얻은 인스턴스를 다른 쪽에서 `instanceof`로 체크하면 false가 나온다.

Tomcat 같은 서블릿 컨테이너는 webapp마다 별도의 ClassLoader를 쓴다. 격리가 목적이므로 의도된 동작이다. 이 환경에서 싱글톤은 webapp 범위다. webapp A의 설정 싱글톤을 변경해도 webapp B에는 영향이 없다.

OSGi 환경도 마찬가지다. 번들마다 ClassLoader가 다르다. 두 번들이 같은 라이브러리를 참조해도, 각 번들이 로드한 클래스는 서로 다른 타입이다. 번들 간에 객체를 공유하려면 OSGi 서비스 레지스트리를 써야 한다.

플러그인 시스템에서 동적 클래스 로딩을 쓰는 경우도 동일하다. 플러그인마다 ClassLoader를 분리하면 플러그인 안의 싱글톤은 플러그인 범위다.

문제는 이 경계를 모르고 설계할 때 생긴다. ClassLoader 경계를 넘어 실제로 공유해야 한다면 Bootstrap ClassLoader나 System ClassLoader에 로드된 클래스를 통하거나, JNDI 같은 공유 레지스트리를 써야 한다. 현실적으로는 Redis나 데이터베이스처럼 프로세스 외부의 공유 저장소가 더 다루기 쉽다.

## Spring 싱글톤은 컨테이너 범위다

Spring에서 `@Component`, `@Service`, `@Repository` 등의 기본 스코프는 싱글톤이다. GoF 싱글톤과 혼동하기 쉬운데 다르다.

GoF 싱글톤은 클래스 자체가 인스턴스 수를 통제한다. `getInstance()`를 어디서 호출해도 같은 인스턴스가 온다. `new`로 직접 생성하는 것을 막는다.

Spring 싱글톤은 ApplicationContext가 인스턴스 수를 관리한다. 같은 ApplicationContext 안에서 하나다. 클래스 자체는 제약이 없다.

```java
@Service
public class UserService {
    // 일반 생성자. new UserService()를 여러 번 호출하면 여러 인스턴스가 생긴다.
    public UserService() {}
}
```

```java
// 테스트에서 직접 인스턴스를 만들 수 있다
UserService s1 = new UserService();
UserService s2 = new UserService();
System.out.println(s1 == s2); // false — 당연히 다르다
```

ApplicationContext가 여러 개면 빈도 여러 개가 된다. Spring Test에서 설정이 다른 테스트 클래스를 여러 개 만들면 컨텍스트도 여러 개 뜬다. 각 컨텍스트의 `UserService`는 다른 인스턴스다.

이 차이가 테스트 설계에서 중요하다. GoF 싱글톤을 쓰면 테스트에서 `getInstance()`를 거쳐야 하고 가짜 구현으로 교체하기 어렵다. Spring 빈은 생성자 주입으로 만들어지므로 테스트에서 `new UserService(mockRepo)`처럼 직접 인스턴스를 만들어 주입할 수 있다.

### prototype 빈이 singleton 빈에서 singleton처럼 동작하는 문제

```java
@Component
@Scope("prototype")
public class RequestTracer {
    private final List<String> steps = new ArrayList<>();
    public void trace(String step) { steps.add(step); }
    public List<String> getSteps() { return steps; }
}

@Service
public class OrderService {
    @Autowired
    private RequestTracer tracer;  // 주입 시점에 한 번만 생성된다

    public void processOrder(Long id) {
        tracer.trace("start");     // 의도: 요청마다 새 tracer
        // ...                     // 실제: 모든 요청이 같은 tracer를 쓴다
    }
}
```

`OrderService`는 싱글톤이고 `RequestTracer`는 prototype이다. `tracer` 필드는 `OrderService` 생성 시점에 한 번만 주입된다. 그 이후 `processOrder()`를 호출할 때마다 같은 `RequestTracer` 인스턴스가 쓰인다. prototype 스코프를 선언했지만 싱글톤처럼 동작하는 것이다. steps 리스트가 모든 요청에 걸쳐 누적된다.

매번 새 prototype 인스턴스가 필요하면 `@Lookup`을 쓴다.

```java
@Service
public abstract class OrderService {

    @Lookup
    protected abstract RequestTracer createTracer();

    public void processOrder(Long id) {
        RequestTracer tracer = createTracer();  // 매번 새 인스턴스
        tracer.trace("start");
        // ...
    }
}
```

Spring이 `createTracer()`를 오버라이드한 서브클래스를 동적으로 생성한다. `abstract`로 선언해야 하고, `final` 메서드에는 적용할 수 없다. CGLIB이 서브클래스를 만들어야 하기 때문이다.

`ObjectProvider`를 쓰는 방법도 있다. 추상 클래스가 부담스럽고 테스트에서 mock이 필요한 경우에 낫다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final ObjectProvider<RequestTracer> tracerProvider;

    public void processOrder(Long id) {
        RequestTracer tracer = tracerProvider.getObject();  // 매번 새 인스턴스
        tracer.trace("start");
    }
}
```
