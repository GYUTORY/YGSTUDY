---
title: Java Static 개념 (Static 변수, 메서드, 블록, 내부 클래스)
tags: [language, java, 객체지향-프로그래밍-oop, static, jvm, metaspace]
updated: 2026-04-24
---

# Java Static 개념

## static이 뭔가

`static`은 멤버를 인스턴스가 아니라 클래스에 묶는 키워드다. 인스턴스를 만들지 않아도 접근할 수 있고, 프로그램이 종료될 때까지 한 곳에 살아있다. 설명만 보면 단순하지만, 실제로는 JVM 메모리 구조, 클래스 로딩 순서, 스레드 안전성, 테스트 격리까지 다 엮여 있어서 실무에서 생각보다 자주 발목을 잡는다.

5년 넘게 Java를 쓰면서 배운 건, `static`을 "편해서" 쓰면 거의 예외 없이 나중에 문제가 된다는 점이다. 특히 상태를 가진 static 변수와 싱글톤 남용, 테스트에서의 상태 공유는 반복적으로 팀을 괴롭힌다. 이 문서는 네 가지 static 형태(변수, 메서드, 블록, 내부 클래스)를 각각 언제 써야 하고, 언제 쓰면 안 되는지를 JVM 관점에서 풀어본다.

## JVM 메모리 관점에서 static이 어디에 있나

자바 8 이전에는 static 변수와 클래스 메타데이터가 모두 PermGen에 있었지만, 자바 8부터는 구조가 바뀌었다. 이 차이를 모르면 "static 많이 쓰면 OOM 난다"는 옛날 얘기를 그대로 믿게 된다.

자바 8 이후 기준으로 정리하면 이렇다.

- 클래스 메타데이터(Class 객체의 내부 구조, 바이트코드, 메서드 정보 등): **Metaspace** (네이티브 메모리 영역)
- static 변수 자체(참조든 값이든): **Heap** (Class 객체 안에 저장되며, Class 객체 자체는 Heap에 있음)
- static 메서드의 바이트코드: **Metaspace**

즉, `static String BIG_STRING = ...` 의 `BIG_STRING`이 가리키는 문자열 객체는 Heap에 있고, 그 참조를 담고 있는 필드 슬롯도 Class 객체를 통해 Heap에서 관리된다. 이 때문에 "static 변수는 GC 대상이 아니다"라는 말은 절반만 맞다. static 필드가 참조하는 객체는 **클래스가 언로드되지 않는 한** GC 루트로 취급된다. 일반적인 애플리케이션 클래스로더에서 로드된 클래스는 거의 언로드되지 않기 때문에, static 필드에 캐시를 무심코 쌓으면 그대로 메모리 누수가 된다.

예전에 큰 Map을 static으로 선언해두고 거기에 사용자 세션 데이터를 캐싱하던 코드가 있었는데, 세션이 끝나도 엔트리를 안 지워서 며칠 돌고 나면 Old 영역이 차 버리는 일이 있었다. 일반 인스턴스 필드였으면 객체가 GC되면서 같이 없어졌을 텐데, static은 클래스랑 수명이 같으니까 계속 누적된 거다. static + 컬렉션은 언제나 경계해야 한다.

## static 변수

### 동작 방식

클래스가 JVM에 처음 로드될 때 static 필드가 기본값으로 초기화되고, 이후 static 초기화자(필드 초기화 표현식 + static 블록)가 선언된 순서대로 실행된다. 이 과정은 **클래스당 한 번만, JVM이 보장하는 동기화 상태로** 실행된다. 그래서 static 필드에 초기값을 대입하는 그 순간 자체는 스레드 안전하다.

```java
public class AppConfig {
    static int maxRetry = 3;
    static String region = System.getenv("AWS_REGION");
    static Map<String, String> cache = new ConcurrentHashMap<>();
}
```

여기서 `maxRetry`, `region`, `cache`는 클래스가 처음 참조될 때 한 번 세팅되고, JVM이 초기화 락을 잡아주기 때문에 여러 스레드가 동시에 `AppConfig`를 건드려도 한 스레드만 초기화를 수행하고 나머지는 완료될 때까지 대기한다.

### 멀티스레드 환경에서의 함정

초기화는 안전하지만, 초기화 이후에 static 변수를 **읽고 쓰는 것**은 전혀 안전하지 않다. 이걸 헷갈리는 경우가 많다.

```java
public class RequestCounter {
    static int count = 0;

    public static void increment() {
        count++;
    }
}
```

`count++`는 읽기-증가-쓰기 세 동작으로 나뉜다. 스레드 여러 개가 동시에 호출하면 카운트가 유실된다. 이 코드는 고전적인 레이스 컨디션의 예시인데, 실무에서 너무 쉽게 등장한다. 다음 중 하나로 바꿔야 한다.

```java
public class RequestCounter {
    static final AtomicLong count = new AtomicLong();

    public static void increment() {
        count.incrementAndGet();
    }
}
```

`AtomicLong`, `AtomicInteger`, `LongAdder` 같은 걸 쓰거나, 정말 단순 플래그라면 `volatile`로 가시성만 확보하면 된다. 다만 `volatile`은 가시성만 보장하고 복합 연산의 원자성은 보장하지 않으니, 증감 연산에는 쓰지 말아야 한다.

static HashMap을 여러 스레드가 공유하는 경우도 마찬가지다. `HashMap`은 동시에 쓰면 내부 링크가 꼬여 무한 루프가 돌거나 데이터가 사라진다. 이런 공유 자료구조는 반드시 `ConcurrentHashMap`을 쓴다.

### final static 상수 패턴

변하지 않는 값은 `public static final`로 선언한다. 컴파일러가 상수 폴딩(constant folding)까지 해주는 경우도 있어서 성능상 이점이 있고, 무엇보다 동시성 이슈가 원천 차단된다.

```java
public final class TimeConstants {
    public static final long ONE_MINUTE_MS = 60_000L;
    public static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(30);

    private TimeConstants() {}
}
```

주의할 점 두 가지가 있다.

첫째, `final`이 걸려 있어도 참조 타입이면 **객체 내부 상태는 바꿀 수 있다**. `public static final List<String> NAMES = new ArrayList<>();` 는 참조는 못 바꾸지만 `NAMES.add(...)`는 가능하다. 진짜 불변이 필요하면 `List.of(...)`나 `Collections.unmodifiableList(...)`로 감싸야 한다.

둘째, 상수 클래스는 인스턴스화할 이유가 없으니 private 생성자로 막는다. 안 그러면 누군가 실수로 `new TimeConstants()`를 하게 된다.

## static 메서드

### this와 super를 쓸 수 없는 이유

static 메서드는 클래스 자체에 속하기 때문에 호출될 때 어떤 인스턴스도 연결되어 있지 않다. `this`는 "현재 이 메서드를 호출한 인스턴스에 대한 참조"인데, 인스턴스가 없으니 `this`도 없다. `super`도 마찬가지로 인스턴스 기반이라 쓸 수 없다.

```java
public class Calculator {
    private int memory;

    public static int add(int a, int b) {
        // memory += a;  // 컴파일 에러. static 컨텍스트에서 인스턴스 필드 접근 불가
        return a + b;
    }
}
```

이게 static 메서드를 "유틸리티 함수"로만 쓰게 되는 이유다. 인스턴스 상태에 의존할 수 없기 때문에 자연스럽게 순수 함수 형태가 된다.

### 오버라이딩이 아니라 숨김(hiding)

static 메서드도 하위 클래스에서 같은 시그니처로 선언할 수 있지만, 이건 **오버라이딩이 아니라 숨김(method hiding)**이다. 호출 시점에 참조 타입에 따라 어떤 메서드가 불릴지 정해진다.

```java
class Parent {
    static void hello() { System.out.println("parent"); }
}
class Child extends Parent {
    static void hello() { System.out.println("child"); }
}

Parent p = new Child();
p.hello();  // "parent" 출력. 런타임 타입이 아니라 선언 타입 기준
```

다형성이 안 먹는다는 뜻이다. static 메서드는 다형성이 필요한 곳에 쓰면 안 된다. 인터페이스 기반 설계를 해야 하는 곳에 static 메서드를 박아두면 나중에 테스트 대역(mock)으로 갈아 끼우기도 어렵고 확장도 막힌다.

### 언제 static 메서드로 만드나

경험상 기준은 이렇다.

- 인스턴스 상태를 전혀 건드리지 않는다
- 입력과 출력만으로 동작이 결정된다 (순수 함수에 가깝다)
- 확장하거나 목킹할 일이 없다

이 세 가지가 다 만족되면 static으로 둔다. 하나라도 애매하면 인스턴스 메서드로 두고 DI로 주입받는 게 장기적으로 낫다.

## static 블록

### 초기화 순서

static 필드 초기화와 static 블록은 **소스 코드에 선언된 순서대로** 실행된다. 이걸 잊으면 NPE가 난다.

```java
public class Config {
    static String name;

    static {
        System.out.println(name.length());  // NPE. 아직 아래 블록이 실행되기 전
    }

    static {
        name = "app";
    }
}
```

JIT나 최적화와는 관계 없이, 선언 순서가 곧 실행 순서다. 필드 초기화 표현식과 static 블록이 섞여 있어도 똑같다.

### ExceptionInInitializerError

static 블록이나 static 필드 초기화에서 예외가 던져지면 JVM은 그걸 `ExceptionInInitializerError`로 감싸서 다시 던진다. 한 번 이 에러가 나면 해당 클래스는 **초기화 실패 상태**로 JVM에 기록되고, 이후 그 클래스에 접근하는 모든 시도가 `NoClassDefFoundError`로 실패한다. 같은 JVM 프로세스 내에서는 복구가 안 된다.

```java
public class DangerousConfig {
    static final String CONFIG_PATH = loadConfigPath();

    private static String loadConfigPath() {
        return System.getenv("CONFIG_PATH").trim();  // CONFIG_PATH 미설정 시 NPE
    }
}
```

환경변수가 없으면 `trim()`에서 NPE가 나고, JVM은 이걸 `ExceptionInInitializerError`로 던진다. 이 클래스는 이제 죽은 클래스가 된다. 스프링 같은 프레임워크에서 이런 일이 벌어지면 컨텍스트 로딩부터 깨져서 원인 추적도 번거롭다.

static 초기화에서 외부 자원에 의존하는 로직(파일 읽기, 네트워크, 환경변수 등)은 가능하면 피하고, 꼭 필요하면 기본값과 방어 코드를 넣는다. 아니면 지연 초기화로 미뤄서 실제 사용 시점에 실패하고 복구 가능하게 만든다.

### 순서 보장이 필요한 복합 초기화

여러 static 값이 서로 의존할 때는 선언 순서를 조심해서 맞추거나, 아예 한 번의 static 블록으로 묶는다.

```java
public class Crypto {
    private static final KeyFactory KEY_FACTORY;
    private static final Cipher CIPHER;

    static {
        try {
            KEY_FACTORY = KeyFactory.getInstance("RSA");
            CIPHER = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        } catch (GeneralSecurityException e) {
            throw new ExceptionInInitializerError(e);
        }
    }
}
```

static 블록 안에서 체크드 예외가 던져질 수 있으면 반드시 잡아서 런타임 예외나 `ExceptionInInitializerError`로 변환해야 한다. static 초기화자 선언부에서는 `throws`를 쓸 수 없기 때문이다.

## static 내부 클래스

### static inner class vs non-static inner class

자바의 내부 클래스는 두 종류다. `static` 키워드가 붙은 **정적 중첩 클래스(static nested class)**와, 붙지 않은 **내부 클래스(inner class)**다. 이 둘은 겉보기엔 비슷하지만 내부적으로 완전히 다르게 동작한다.

non-static inner class는 컴파일 시점에 외부 클래스의 인스턴스 참조(`Outer.this`)를 **자동으로 갖는 숨겨진 필드**를 포함한다. 그래서 내부 클래스 인스턴스는 반드시 외부 클래스 인스턴스가 있어야 만들 수 있다.

```java
public class Outer {
    private int value = 10;

    // non-static, 외부 인스턴스 참조를 암묵적으로 보유
    class Inner {
        int read() { return value; }  // 숨겨진 Outer.this.value
    }

    // static, 외부 인스턴스 참조 없음
    static class StaticInner {
        // int read() { return value; }  // 컴파일 에러
    }
}

Outer outer = new Outer();
Outer.Inner in = outer.new Inner();           // non-static는 외부 인스턴스 필요
Outer.StaticInner sin = new Outer.StaticInner();  // static은 독립적으로 생성
```

### 메모리 누수 이슈

이 숨겨진 외부 참조가 바로 **메모리 누수의 원인**이 된다. 내부 클래스 인스턴스가 어딘가에 오래 살아 있으면 외부 클래스 인스턴스도 같이 살아 있게 된다.

```java
public class ReportService {
    private LargeReport report;  // 수백 MB짜리

    public Runnable asyncTask() {
        return new Runnable() {  // 익명 내부 클래스. ReportService.this를 보유
            @Override
            public void run() {
                System.out.println("done");
            }
        };
    }
}
```

이 `Runnable`은 `report`를 전혀 쓰지 않는데도, `ReportService` 인스턴스 전체를 붙들고 있다. 이 Runnable이 큐나 스케줄러에 들어가서 오래 살아남으면 `ReportService`와 그 안의 `LargeReport`까지 GC되지 않는다. 안드로이드에서 `Activity` 메모리 누수로 악명 높은 그 패턴이다.

해결 방법은 두 가지다.

```java
// 1. static 중첩 클래스로 만들고 필요한 값만 받는다
private static class CleanTask implements Runnable {
    @Override
    public void run() {
        System.out.println("done");
    }
}

// 2. 람다를 쓰되, 외부 인스턴스 필드를 참조하지 않는다
Runnable task = () -> System.out.println("done");
```

람다는 외부 변수를 캡처하지 않으면 외부 인스턴스 참조도 만들지 않는다. 하지만 `this`를 캡처하는 람다는 여전히 외부 인스턴스를 붙든다. `() -> someInstanceField.toString()`도 `this.someInstanceField`로 해석되기 때문에 위의 익명 내부 클래스와 똑같은 문제가 생긴다.

원칙은 "외부 인스턴스 상태가 필요하지 않다면 static 중첩 클래스로 만든다"다. IntelliJ나 SpotBugs 같은 정적 분석 도구도 이걸 경고한다.

### Holder 패턴으로 싱글톤 지연 초기화

static 중첩 클래스의 고전적인 활용이 싱글톤의 Lazy Initialization Holder 패턴이다. 자바의 클래스 로딩 규약을 이용해 동기화 블록 없이 스레드 안전한 지연 초기화를 구현한다.

```java
public class HeavyService {
    private HeavyService() {
        // 무거운 초기화
    }

    private static class Holder {
        private static final HeavyService INSTANCE = new HeavyService();
    }

    public static HeavyService getInstance() {
        return Holder.INSTANCE;
    }
}
```

`HeavyService` 클래스가 로드되어도 `Holder` 클래스는 로드되지 않는다. `getInstance()`가 처음 호출될 때 비로소 `Holder`가 로드되고, 그 시점에 JVM이 클래스 초기화 락을 잡아주기 때문에 `INSTANCE`는 정확히 한 번만 생성된다. `synchronized`도 `volatile`도 필요 없다.

다른 싱글톤 구현(double-checked locking, enum 싱글톤 등)도 있지만, 지연 초기화가 필요하고 스프링 같은 DI 컨테이너를 쓰지 않는 상황이라면 Holder 패턴이 가장 간결하다.

## static import 주의점

`import static`을 쓰면 클래스명 없이 static 멤버를 바로 쓸 수 있다.

```java
import static java.lang.Math.*;
import static org.assertj.core.api.Assertions.*;

double r = sqrt(pow(x, 2) + pow(y, 2));
assertThat(result).isEqualTo(expected);
```

편하긴 한데, 남용하면 읽기 어려워진다. 코드에서 `sqrt`, `pow`가 자기 클래스의 메서드인지 어디서 온 건지 구분이 안 된다. 특히 프로젝트 내부의 도메인 유틸리티까지 static import하면 리팩터링할 때 호출부를 찾기도 힘들다.

팀에서 정한 기준 예시:

- 테스트 프레임워크의 assertion 메서드는 static import OK (AssertJ, JUnit, Mockito)
- `java.lang.Math`, `java.util.Collections` 같은 표준 라이브러리의 잘 알려진 메서드는 OK
- 프로젝트 내부 클래스의 static 메서드는 원칙적으로 전체 경로로 호출

이 정도 기준만 잡아도 리뷰할 때 부담이 없다.

## 테스트에서 static 상태가 만드는 플레이키 테스트

실무에서 static이 가장 골치 아프게 나타나는 지점이 테스트다. static 변수는 JVM이 떠 있는 동안 살아있고, JUnit은 보통 하나의 JVM에서 모든 테스트를 실행한다. 그래서 테스트 간에 static 상태가 새어나간다.

```java
public class UserCache {
    static final Map<Long, User> CACHE = new HashMap<>();

    public static void put(long id, User u) { CACHE.put(id, u); }
    public static User get(long id) { return CACHE.get(id); }
}
```

테스트 A가 `UserCache.put(1L, userA)`를 하고, 테스트 B가 `UserCache.get(1L)`을 했을 때 `null`을 기대했다면, 실행 순서에 따라 통과하거나 실패한다. 전형적인 flaky test다.

대처 방법은 크게 세 가지다.

**@BeforeEach에서 초기화**. 가장 단순하지만 누락하기 쉽다.

```java
@BeforeEach
void clearCache() {
    UserCache.CACHE.clear();
}
```

**static을 걷어내고 인스턴스 기반으로 바꾸기**. 가장 확실한 해법이다. 테스트마다 새 인스턴스를 주입받으니 격리가 자동으로 된다.

```java
public class UserCache {
    private final Map<Long, User> cache = new HashMap<>();
    public void put(long id, User u) { cache.put(id, u); }
}
```

**PowerMock이나 Mockito의 mockStatic 사용**. 최후의 수단이다. 이게 필요하다는 건 설계가 static에 너무 의존한다는 신호다.

static 로거(Slf4j `private static final Logger log`)처럼 상태 없는 싱글톤은 문제가 없지만, **상태를 가진 static**은 거의 항상 테스트 격리를 깨뜨린다. 새 코드를 짤 때 static 변수를 선언하려 한다면, "이거 테스트에서 어떻게 초기화할까"를 먼저 생각하는 습관을 들이는 게 좋다.

## 실무에서 static을 쓸 때 내가 따르는 기준

정리하면, static은 다음 경우에만 쓰는 쪽이 유지보수가 편하다.

상수 정의(`public static final`), 상태 없는 순수 유틸리티 메서드(수학 계산, 포맷 변환, 문자열 파싱 등), 외부 인스턴스 참조가 필요 없는 중첩 클래스, 싱글톤의 Holder 패턴 정도다.

반대로 이런 곳에 static을 쓰면 나중에 거의 후회한다. 가변 상태(카운터, 캐시, 세션, 설정 플래그 중 런타임에 바뀌는 것들), 외부 자원 의존 초기화(DB 커넥션, 환경변수 파싱), 다형성이나 목킹이 필요한 비즈니스 로직. 이런 건 인스턴스로 두고 DI로 해결하는 편이 훨씬 깔끔하다.

static은 자바가 제공하는 기본 기능이지만, "클래스 수명 = 값 수명"이라는 특성 때문에 메모리, 동시성, 테스트 세 방면에서 모두 함정을 만든다. 편의를 위해 무심코 쓰지 말고, 왜 static이어야 하는지 한 번씩 점검하는 게 결과적으로 디버깅 시간을 아낀다.
