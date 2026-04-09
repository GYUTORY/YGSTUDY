---
title: JVM 구조 및 메모리 관리
tags: [language, java, jvm, memory, class-loader, runtime-data-area, monitoring]
updated: 2026-04-09
---

# JVM 구조 및 메모리 관리

## 1. JVM(Java Virtual Machine)

JVM은 Java 바이트코드(.class)를 실행하는 가상 머신이다. `javac`로 컴파일된 바이트코드를 OS와 하드웨어에 맞게 해석하고 실행한다. "Write Once, Run Anywhere"가 가능한 이유가 JVM 때문이다.

JVM이 하는 일은 크게 세 가지다:

- .class 파일을 메모리에 올리고 실행한다
- 메모리를 할당하고, 안 쓰는 객체를 GC로 정리한다
- 바이트코드를 인터프리팅하거나 JIT 컴파일로 네이티브 코드로 변환한다

---

## 2. JVM 전체 구조

```
┌──────────────────────────────────────────────────────────┐
│                        JVM                               │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                  Class Loader                      │  │
│  │  Loading → Linking(Verify/Prepare/Resolve) → Init  │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │ 클래스 로드                      │
│                         ▼                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Runtime Data Area                     │  │
│  │                                                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │  │
│  │  │ Method   │ │   Heap   │ │  Per-Thread 영역    │ │  │
│  │  │ Area     │ │          │ │ ┌────────────────┐ │ │  │
│  │  │ (메타    │ │ Young/Old│ │ │ JVM Stack      │ │ │  │
│  │  │  데이터) │ │   Gen    │ │ │ PC Register    │ │ │  │
│  │  │          │ │          │ │ │ Native Method  │ │ │  │
│  │  │          │ │          │ │ │ Stack          │ │ │  │
│  │  └──────────┘ └──────────┘ │ └────────────────┘ │ │  │
│  │                            └────────────────────┘ │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │ 바이트코드 실행                   │
│                         ▼                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Execution Engine                      │  │
│  │  ┌──────────────┐ ┌──────────┐ ┌───────────────┐  │  │
│  │  │ Interpreter  │ │ JIT      │ │ GC            │  │  │
│  │  │              │ │ Compiler │ │ (Garbage      │  │  │
│  │  │              │ │          │ │  Collector)   │  │  │
│  │  └──────────────┘ └──────────┘ └───────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │           Native Interface (JNI)                   │  │
│  │         C/C++ 네이티브 라이브러리 호출               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Class Loader 동작 과정

Class Loader는 .class 파일을 찾아서 메모리에 올리는 역할을 한다. 세 단계를 거친다.

### 3.1 Loading (로딩)

.class 파일의 바이트코드를 읽어서 `java.lang.Class` 객체를 생성한다. 클래스를 찾을 때는 **위임 모델(Parent Delegation Model)**을 따른다.

```
클래스 로딩 요청
    │
    ▼
Application ClassLoader (classpath의 클래스)
    │ 못 찾으면 부모에게 위임
    ▼
Platform ClassLoader (JDK 확장 모듈, JDK 9+)
    │ 못 찾으면 부모에게 위임
    ▼
Bootstrap ClassLoader (java.lang.*, java.util.* 등 핵심 클래스)
    │ 여기서도 못 찾으면
    ▼
ClassNotFoundException 발생
```

Bootstrap ClassLoader부터 찾기 시작해서, 못 찾으면 하위 ClassLoader로 내려온다. 이 구조 때문에 핵심 클래스(String, Object 등)를 사용자가 임의로 교체할 수 없다.

**ClassLoader 관련 실제 문제 상황:**

애플리케이션 서버(Tomcat 등)에 WAR를 여러 개 배포하면, 각 WAR마다 별도의 ClassLoader를 사용한다. 같은 라이브러리의 다른 버전이 각 WAR에 들어 있으면, ClassLoader별로 다른 클래스가 로드된다. 이 때문에 `ClassCastException`이나 `LinkageError`가 뜬다. 같은 클래스 이름이더라도 ClassLoader가 다르면 JVM은 다른 클래스로 취급한다.

```java
// WAR-A의 ClassLoader로 로드한 com.example.User와
// WAR-B의 ClassLoader로 로드한 com.example.User는
// JVM 입장에서 완전히 다른 클래스다.
// 이 둘 사이에 캐스팅하면 ClassCastException이 발생한다.
```

### 3.2 Linking (링킹)

링킹은 세 단계로 나뉜다.

**Verification (검증)**: 바이트코드가 JVM 스펙에 맞는지 검사한다. 잘못된 바이트코드가 JVM을 망가뜨리는 걸 방지한다. 직접 바이트코드를 조작했을 때 `VerifyError`가 발생하는 이유다.

**Preparation (준비)**: 클래스의 static 필드에 대해 메모리를 할당하고 기본값(0, null, false)으로 초기화한다. 코드에서 지정한 값은 아직 대입되지 않는다.

**Resolution (해석)**: 심볼릭 레퍼런스(문자열로 된 클래스/메서드 이름)를 실제 메모리 주소로 변환한다. 이 시점에 참조하는 클래스가 없으면 `NoClassDefFoundError`가 발생한다.

### 3.3 Initialization (초기화)

static 블록 실행, static 필드에 코드에서 지정한 값을 대입한다. 이 단계에서 클래스가 처음 사용 가능한 상태가 된다.

```java
public class Config {
    // Preparation 단계: value = null
    // Initialization 단계: value = "production"
    static String value = "production";

    static {
        // Initialization 단계에서 실행
        System.out.println("Config 클래스 초기화");
    }
}
```

---

## 4. Runtime Data Area

JVM이 프로그램을 실행하면서 데이터를 저장하는 메모리 영역이다. 스레드 간 공유 영역과 스레드 전용 영역으로 나뉜다.

```
┌──────────────────────────────────────────────────────┐
│                  공유 영역 (모든 스레드)                │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │               Method Area                    │    │
│  │  클래스 메타데이터, static 변수, 상수 풀         │    │
│  │  JDK 8+: Metaspace (Native Memory)           │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │                  Heap                         │    │
│  │  ┌───────────────────┐ ┌──────────────────┐  │    │
│  │  │    Young Gen      │ │    Old Gen       │  │    │
│  │  │ ┌─────┐┌───┐     │ │                  │  │    │
│  │  │ │Eden ││S0 │     │ │  장기 생존 객체    │  │    │
│  │  │ │     ││S1 │     │ │                  │  │    │
│  │  │ └─────┘└───┘     │ │                  │  │    │
│  │  └───────────────────┘ └──────────────────┘  │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│             스레드 전용 영역 (스레드마다 독립)           │
│                                                      │
│  Thread-1              Thread-2          Thread-N    │
│  ┌──────────────┐     ┌──────────────┐              │
│  │ JVM Stack    │     │ JVM Stack    │    ...       │
│  │ PC Register  │     │ PC Register  │              │
│  │ Native Stack │     │ Native Stack │              │
│  └──────────────┘     └──────────────┘              │
└──────────────────────────────────────────────────────┘
```

### 4.1 Method Area (메서드 영역)

클래스 수준의 정보를 저장한다. 클래스 메타데이터, static 변수, 런타임 상수 풀(Runtime Constant Pool)이 여기에 들어간다. 모든 스레드가 공유한다.

JDK 7까지는 Heap 내부의 PermGen(Permanent Generation)이라는 고정 크기 영역이었다. JDK 8부터 **Metaspace**로 바뀌면서 Native Memory로 이동했다.

```java
class Example {
    // "hello"는 Runtime Constant Pool에 저장 (Method Area)
    static final String GREETING = "hello";

    // count는 Method Area의 static 필드 영역에 저장
    static int count = 0;

    // 메서드 바이트코드도 Method Area에 저장
    public void doSomething() { }
}
```

**PermGen에서 Metaspace로 바뀐 이유:**

PermGen은 `-XX:MaxPermSize`로 크기가 고정되어 있었다. 클래스가 많은 애플리케이션(Spring, Hibernate 등)에서 `java.lang.OutOfMemoryError: PermGen space`가 자주 발생했다. Metaspace는 Native Memory를 쓰기 때문에 기본적으로 OS가 허용하는 만큼 늘어난다. 다만 상한을 안 잡으면 메모리를 무한정 사용할 수 있어서, 운영 환경에서는 `-XX:MaxMetaspaceSize`를 반드시 설정해야 한다.

**Metaspace OOM 실제 사례:**

Spring Boot 애플리케이션에서 개발 중 hot reload(spring-devtools)를 반복하면, 이전 ClassLoader가 해제되지 않고 남아 있는 경우가 있다. 매번 새 ClassLoader로 클래스를 로드하면서 Metaspace가 계속 증가한다.

```sh
# Metaspace OOM 발생 시 로그
java.lang.OutOfMemoryError: Metaspace
    at java.lang.ClassLoader.defineClass1(Native Method)
    at java.lang.ClassLoader.defineClass(ClassLoader.java:756)
```

이런 경우 `jcmd`로 로드된 클래스 수를 확인하면 비정상적으로 많은 수의 클래스가 로드되어 있다.

```sh
jcmd <PID> VM.classloader_stats
```

### 4.2 Heap (힙)

객체 인스턴스가 저장되는 영역이다. `new` 키워드로 생성한 모든 객체가 여기에 들어간다. GC의 주요 대상이다.

Heap은 **Young Generation**과 **Old Generation**으로 나뉜다.

**Young Gen**: 새로 생성된 객체가 먼저 들어간다. Eden 영역에서 시작해서, Minor GC를 살아남으면 Survivor 영역(S0, S1)으로 이동한다. 일정 횟수 이상 GC를 살아남으면 Old Gen으로 승격(promotion)된다.

**Old Gen**: 오래 살아남은 객체가 저장된다. 이 영역이 가득 차면 Major GC(Full GC)가 발생하고, 이때 Stop-The-World로 애플리케이션이 멈춘다.

```java
public class HeapExample {
    public static void main(String[] args) {
        // person 참조 변수 → Stack
        // Person 객체 자체 → Heap (Young Gen의 Eden)
        Person person = new Person("홍길동", 30);

        // names 참조 변수 → Stack
        // ArrayList 객체와 내부 String 객체들 → Heap
        List<String> names = new ArrayList<>();
        names.add("김철수");
        names.add("이영희");
    }
}
```

**Heap 관련 자주 겪는 문제:**

`java.lang.OutOfMemoryError: Java heap space`가 발생하면 두 가지를 확인해야 한다.

1. **메모리 누수**: 더 이상 쓰지 않는 객체인데 참조가 남아 있어서 GC가 수거하지 못한다. static Map에 데이터를 계속 넣으면서 삭제하지 않는 패턴이 대표적이다.

2. **Heap 크기 부족**: 실제로 필요한 메모리에 비해 Heap이 작다. 대량 데이터를 한 번에 메모리에 올리는 경우(예: DB에서 수백만 건을 List로 조회)에 발생한다.

```java
// 메모리 누수 패턴 - 캐시에 만료 정책이 없다
public class LeakyCache {
    // static이라 GC 대상이 안 됨. 계속 쌓인다.
    private static final Map<String, byte[]> cache = new HashMap<>();

    public void put(String key, byte[] data) {
        cache.put(key, data);  // 삭제 로직이 없다
    }
}
```

### 4.3 JVM Stack (스택)

스레드마다 하나씩 생성된다. 메서드를 호출하면 **스택 프레임(Stack Frame)**이 push되고, 메서드가 끝나면 pop된다.

스택 프레임에는 지역 변수, 피연산자 스택, 메서드 리턴 주소가 들어간다.

```java
public class StackExample {
    public static void main(String[] args) {
        // main 스택 프레임 push
        int result = factorial(5);
        System.out.println(result);
        // main 스택 프레임 pop
    }

    public static int factorial(int n) {
        // factorial 스택 프레임 push (재귀 호출마다 새로 생성)
        if (n <= 1) return 1;
        return n * factorial(n - 1);
        // factorial 스택 프레임 pop
    }
}
```

**StackOverflowError 실제 사례:**

재귀 호출에 종료 조건이 없거나, 종료 조건에 도달하기 전에 스택이 가득 차면 발생한다.

```java
// 종료 조건이 없는 재귀 - StackOverflowError 발생
public int badRecursion(int n) {
    return badRecursion(n + 1);
}
```

실무에서 더 자주 겪는 케이스는 **양방향 참조에서의 무한 루프**다. JPA Entity에서 `toString()`이나 JSON 직렬화할 때 양방향 관계가 서로를 계속 호출하는 경우다.

```java
@Entity
public class Order {
    @ManyToOne
    private Customer customer;

    @Override
    public String toString() {
        // customer.toString()이 다시 order.toString()을 호출 → 무한 재귀
        return "Order{customer=" + customer + "}";
    }
}

@Entity
public class Customer {
    @OneToMany(mappedBy = "customer")
    private List<Order> orders;

    @Override
    public String toString() {
        return "Customer{orders=" + orders + "}";
    }
}
```

Stack 크기는 `-Xss` 옵션으로 조정한다. 기본값은 플랫폼마다 다르지만 보통 512KB~1MB다. StackOverflowError가 나면 스택 크기를 늘리기 전에 재귀 구조부터 점검해야 한다.

### 4.4 PC Register

각 스레드가 현재 실행 중인 바이트코드 명령어의 주소를 가리킨다. 스레드마다 독립적으로 존재한다. Java 메서드 실행 중에는 현재 바이트코드 주소를 저장하고, Native 메서드 실행 중에는 undefined 상태가 된다.

멀티스레드 환경에서 컨텍스트 스위칭이 발생할 때, 각 스레드가 어디까지 실행했는지 기억하는 데 PC Register를 사용한다.

### 4.5 Native Method Stack

JNI(Java Native Interface)를 통해 호출되는 C/C++ 네이티브 코드를 위한 스택이다. Java 코드에서 `native` 키워드가 붙은 메서드를 호출하면 이 영역을 사용한다.

```java
// System.currentTimeMillis()는 native 메서드다
// 이 메서드 실행 시 Native Method Stack을 사용한다
public static native long currentTimeMillis();
```

---

## 5. Execution Engine

바이트코드를 실제로 실행하는 부분이다.

**Interpreter**: 바이트코드를 한 줄씩 해석해서 실행한다. 시작은 빠르지만, 같은 코드를 반복 실행할 때 매번 해석하므로 느리다.

**JIT(Just-In-Time) Compiler**: 자주 실행되는 코드(Hot Spot)를 네이티브 코드로 컴파일해서 캐싱한다. 이후 같은 코드를 실행할 때는 컴파일된 네이티브 코드를 바로 실행하므로 빠르다.

```
바이트코드 실행 흐름:

처음 실행 → Interpreter로 한 줄씩 실행
    │
    │  반복 실행 감지 (invocation counter 임계값 초과)
    ▼
JIT Compiler가 네이티브 코드로 컴파일
    │
    ▼
이후 실행 → 컴파일된 네이티브 코드 직접 실행 (빠름)
```

JIT 컴파일된 코드는 **Code Cache**라는 별도 메모리 영역에 저장된다. Code Cache가 가득 차면 JIT 컴파일이 중단되고 성능이 떨어진다. `-XX:ReservedCodeCacheSize`로 크기를 조정할 수 있다.

---

## 6. Garbage Collection (GC)

Heap에서 더 이상 참조되지 않는 객체를 자동으로 제거한다.

### GC 기본 동작

GC는 "살아있는 객체"를 판별하기 위해 **GC Roots**에서 시작해서 참조 체인을 따라간다. GC Roots에서 도달할 수 없는 객체는 수거 대상이다.

GC Roots가 되는 것들:
- 실행 중인 스레드의 Stack에 있는 지역 변수
- static 변수
- JNI 참조

```
GC Roots                  Heap
  │
  ├──→ 객체A ──→ 객체B        ← 도달 가능, 살아 있음
  │
  ├──→ 객체C                  ← 도달 가능, 살아 있음
  │
  │    객체D ──→ 객체E        ← 도달 불가, GC 대상
  │    객체F                  ← 도달 불가, GC 대상
```

### Stop-The-World

GC가 실행될 때 애플리케이션 스레드가 일시 정지된다. Minor GC는 보통 수~수십 ms 수준이지만, Full GC는 수 초까지 걸릴 수 있다. 이 시간 동안 요청 처리가 멈추기 때문에, 운영 환경에서 Full GC 빈도와 시간을 줄이는 게 중요하다.

```java
// System.gc()는 GC를 요청만 할 뿐, 즉시 실행을 보장하지 않는다.
// 운영 코드에서는 호출하면 안 된다.
System.gc();
```

GC 알고리즘별 특성, GC 로그 읽는 법, 튜닝 방법은 [JVM 옵션 및 메모리 관리](JVM_Options_and_Memory_Management.md) 문서에서 다룬다.

---

## 7. JVM 모니터링 도구

운영 환경에서 JVM 상태를 확인할 때 쓰는 도구들이다. JDK에 기본 포함되어 있어서 별도 설치가 필요 없다.

### 7.1 jps — JVM 프로세스 목록

현재 실행 중인 JVM 프로세스를 확인한다.

```sh
$ jps -l
12345 com.example.MyApplication
12346 org.apache.catalina.startup.Bootstrap
12400 jdk.jcmd/sun.tools.jps.Jps
```

`-l` 옵션을 붙이면 메인 클래스의 전체 패키지명이 표시된다. 여기서 확인한 PID를 다른 도구에서 사용한다.

### 7.2 jstat — GC 통계 모니터링

GC 상태를 실시간으로 확인하는 도구다. 메모리 누수를 의심할 때 가장 먼저 실행한다.

```sh
# 1초 간격으로 GC 통계 출력 (10번 반복)
$ jstat -gcutil <PID> 1000 10

  S0     S1     E      O      M     CCS    YGC   YGCT    FGC   FGCT    CGC   CGCT     GCT
  0.00  67.45  23.11  45.67  96.12  93.25   234   2.145    2   1.567     5   0.089   3.801
  0.00  67.45  38.22  45.67  96.12  93.25   234   2.145    2   1.567     5   0.089   3.801
  0.00  67.45  55.89  45.67  96.12  93.25   234   2.145    2   1.567     5   0.089   3.801
 48.33   0.00   5.12  46.78  96.12  93.25   235   2.158    2   1.567     5   0.089   3.814
```

각 컬럼의 의미:

| 컬럼 | 의미 | 주의해서 볼 때 |
|------|------|---------------|
| S0, S1 | Survivor 영역 사용률(%) | — |
| E | Eden 영역 사용률(%) | 빠르게 100%에 도달하면 객체 생성량이 많다는 뜻 |
| O | Old Gen 사용률(%) | **지속적으로 올라가면 메모리 누수 의심** |
| M | Metaspace 사용률(%) | 계속 올라가면 클래스 로더 누수 의심 |
| YGC/YGCT | Young GC 횟수/총 소요 시간 | — |
| FGC/FGCT | Full GC 횟수/총 소요 시간 | **FGC가 증가하면 문제 신호** |

**메모리 누수 판별법**: `jstat -gcutil`을 일정 시간 동안 관찰해서, Full GC가 발생한 직후에도 O(Old Gen) 사용률이 계속 높아지면 누수다. 정상적인 경우 Full GC 후 Old Gen 사용률이 떨어져야 한다.

```sh
# Heap 영역별 실제 용량을 바이트 단위로 확인
$ jstat -gc <PID> 1000

 S0C    S1C    S0U    S1U      EC       EU        OC         OU       MC      MU
2048.0 2048.0  0.0   1382.4  16384.0   9543.2   40960.0   18734.5  52480.0  50423.8
```

`-gc` 옵션은 비율이 아닌 실제 KB 단위 수치를 보여준다. C는 Capacity(할당량), U는 Used(사용량)다.

### 7.3 jstack — 스레드 덤프

현재 실행 중인 모든 스레드의 상태와 스택 트레이스를 출력한다. 애플리케이션이 멈추거나 느려졌을 때 원인을 파악하는 데 쓴다.

```sh
$ jstack <PID>
```

```
"http-nio-8080-exec-15" #45 daemon prio=5 os_prio=0 tid=0x00007f... nid=0x1a23 waiting for monitor entry [0x00007f...]
   java.lang.Thread.State: BLOCKED (on object monitor)
	at com.example.service.OrderService.processOrder(OrderService.java:45)
	- waiting to lock <0x00000000c2a4b6d0> (a java.lang.Object)
	at com.example.controller.OrderController.create(OrderController.java:28)

"http-nio-8080-exec-7" #37 daemon prio=5 os_prio=0 tid=0x00007f... nid=0x1a1b runnable [0x00007f...]
   java.lang.Thread.State: RUNNABLE
	at com.example.service.OrderService.processOrder(OrderService.java:42)
	- locked <0x00000000c2a4b6d0> (a java.lang.Object)
```

위 결과를 읽으면:

- `exec-7` 스레드가 `OrderService.java:42`에서 락을 잡고 있다
- `exec-15` 스레드가 같은 락을 기다리며 BLOCKED 상태다
- 두 스레드가 같은 객체(`0x00000000c2a4b6d0`)를 두고 경합하고 있다

**데드락 감지**: jstack은 데드락이 있으면 출력 하단에 자동으로 알려준다.

```
Found one Java-level deadlock:
=============================
"Thread-1":
  waiting to lock monitor 0x00007f..., which is held by "Thread-2"
"Thread-2":
  waiting to lock monitor 0x00007f..., which is held by "Thread-1"
```

**실무 팁**: 스레드 덤프는 한 번만 떠서는 판단하기 어렵다. 3~5초 간격으로 3번 정도 떠서 비교해야 한다. 같은 스레드가 같은 위치에서 계속 멈춰 있으면 문제가 확실하다.

```sh
# 3초 간격으로 스레드 덤프 3번 생성
for i in 1 2 3; do
    jstack <PID> > /tmp/threaddump_$i.txt
    sleep 3
done
```

### 7.4 jcmd — 만능 진단 도구

JDK 7부터 제공되는 도구로, jmap, jstack의 기능을 모두 포함한다. Oracle에서도 jmap 대신 jcmd 사용을 권장한다.

```sh
# 사용 가능한 명령 목록 확인
$ jcmd <PID> help

# VM 정보 확인 (JVM 옵션, 시스템 프로퍼티 등)
$ jcmd <PID> VM.info

# 현재 적용된 JVM 플래그 확인
$ jcmd <PID> VM.flags

# Heap 영역별 사용량 요약
$ jcmd <PID> GC.heap_info

# Heap Dump 생성 (jmap -dump 대체)
$ jcmd <PID> GC.heap_dump /tmp/heapdump.hprof

# 스레드 덤프 (jstack 대체)
$ jcmd <PID> Thread.print

# 클래스 히스토그램 (메모리를 많이 쓰는 클래스 확인)
$ jcmd <PID> GC.class_histogram
```

**GC.class_histogram 활용 예시:**

메모리 누수가 의심될 때, 어떤 클래스의 인스턴스가 많은지 확인할 수 있다.

```sh
$ jcmd <PID> GC.class_histogram | head -20

 num     #instances         #bytes  class name (module)
-------------------------------------------------------
   1:       2845231      136571088  [B (java.base@17)
   2:       2340156       56163744  java.lang.String (java.base@17)
   3:        456789       29234496  com.example.dto.OrderDTO
   4:        456789       21925872  com.example.entity.Order
```

`OrderDTO`와 `Order`가 비정상적으로 많다면, 이 객체를 생성하는 코드를 추적하면 된다. 시간 간격을 두고 두 번 실행해서 인스턴스 수가 계속 증가하는 클래스가 누수 원인이다.

### 7.5 jmap — 메모리 맵

Heap 정보를 확인하거나 Heap Dump를 생성한다. JDK 9 이후로는 jcmd 사용이 권장되지만, 아직 많이 쓰인다.

```sh
# Heap 사용량 요약
$ jmap -heap <PID>

# Heap Dump 생성
$ jmap -dump:format=b,file=/tmp/heapdump.hprof <PID>
```

주의: `jmap -dump`는 실행 중에 JVM을 잠시 멈추게 한다(Stop-The-World). Heap이 클수록 오래 걸린다. 운영 서버에서 피크 시간에 실행하면 장애로 이어질 수 있다. dump 파일 크기는 Heap 크기와 비슷하므로 디스크 여유 공간도 확인해야 한다.

---

## 8. 실제 문제 사례와 진단

### 사례 1: StackOverflowError — JPA 양방향 관계

**증상**: 특정 API 호출 시 StackOverflowError 발생.

**원인**: JPA Entity 간 양방향 관계에서 JSON 직렬화 시 무한 재귀 호출.

**진단**: 스택 트레이스를 보면 `Jackson`의 serialize 메서드가 `Order` → `Customer` → `Order` → ... 을 반복한다.

**해결**: `@JsonIgnore` 또는 `@JsonManagedReference` / `@JsonBackReference`로 직렬화 순환을 끊는다. 근본적으로는 Entity를 직접 반환하지 말고 DTO로 변환해야 한다.

### 사례 2: Metaspace OOM — 동적 프록시 과다 생성

**증상**: 서비스 운영 중 수 시간 후 `OutOfMemoryError: Metaspace` 발생.

**진단 과정**:

```sh
# 1. Metaspace 사용률 확인
$ jstat -gcutil <PID> 1000
# M 컬럼이 99%에 가까움

# 2. 로드된 클래스 수 확인
$ jcmd <PID> VM.classloader_stats
# 비정상적으로 많은 클래스 수

# 3. 어떤 클래스가 많이 로드되었는지 확인
$ jcmd <PID> GC.class_histogram | grep "GeneratedMethodAccessor\|$$\|CGLIB\|Proxy"
# CGLIB로 생성된 프록시 클래스가 수만 개
```

**원인**: 리플렉션 기반 라이브러리가 매 요청마다 새로운 프록시 클래스를 생성하고 있었다.

**해결**: 프록시 객체를 캐싱하도록 수정하고, `-XX:MaxMetaspaceSize=512m`을 설정해서 무제한 증가를 방지했다.

### 사례 3: Old Gen 메모리 누수

**증상**: 서비스 실행 후 며칠이 지나면 Full GC가 빈번하게 발생하고 응답이 느려진다.

**진단 과정**:

```sh
# 1. GC 상태 모니터링 — O(Old Gen)가 Full GC 후에도 내려가지 않음
$ jstat -gcutil <PID> 5000
  S0     S1     E      O      M      FGC   FGCT
  0.00  45.00  33.21  87.45  95.12    15   12.345
  0.00  45.00  55.67  88.12  95.12    15   12.345
  0.00  45.00  12.34  85.23  95.12    16   15.678  ← Full GC 발생
  0.00  45.00  28.90  84.89  95.12    16   15.678  ← 회수량이 적다

# 2. Heap Dump 생성
$ jcmd <PID> GC.heap_dump /tmp/heapdump.hprof

# 3. Eclipse MAT로 분석
# Leak Suspects Report에서 HashMap이 Heap의 60%를 차지
# HashMap 안에 세션 객체가 수십만 개 쌓여 있었음
```

**원인**: 자체 구현한 세션 저장소에 만료 로직이 없었다. 사용자 세션이 생성만 되고 삭제되지 않아서 계속 쌓였다.

**해결**: 세션에 TTL을 설정하고, `ConcurrentHashMap` + `ScheduledExecutorService`로 주기적 만료 처리를 추가했다.
