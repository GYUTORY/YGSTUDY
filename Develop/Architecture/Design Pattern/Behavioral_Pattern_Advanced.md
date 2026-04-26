---
title: 행동 패턴 심화 (Behavioral Pattern Advanced)
tags: [architecture, design-pattern, behavioral, visitor, mediator, memento, iterator, interpreter, observer, double-dispatch]
updated: 2026-04-18
---

# 행동 패턴 심화

기본 문서인 [Behavioral_Pattern.md](Behavioral_Pattern.md)가 Strategy, Template Method, Command, State, Chain of Responsibility의 입문 수준 사용법을 다룬다면, 이 문서는 GoF 행위 패턴 11개 중 기본 문서에서 빠진 Visitor·Mediator·Memento·Iterator·Interpreter의 내부 동작, 패턴들이 JVM에서 어떻게 실행되는지의 저수준 동작, 그리고 실무에서 패턴을 잘못 고르거나 람다·리플렉션으로 해체되는 경우를 다룬다.

5년 정도 백엔드 코드를 보면, 책에서 말하는 "패턴"이 실제로는 JDK나 Spring, Jackson, Netty 안에 이미 구현되어 있는 경우가 많다. 직접 Visitor 클래스를 만드는 일보다는 Jackson의 `TreeNode.traverse()`를 디버깅하거나, Netty ChannelPipeline이 왜 N+1번의 메서드 호출로 동작하는지 이해하는 일이 훨씬 자주 발생한다. 이 문서의 목표는 그 관점에서 행위 패턴을 다시 보는 것이다.

## 1. 기본 문서에서 빠진 5가지 패턴

### 1.1 Visitor — Double Dispatch와 타입 시스템의 한계

Visitor는 객체 구조에서 **연산(알고리즘)과 데이터 구조를 분리**하는 패턴이다. 핵심은 Java/C++ 같이 **Single Dispatch만 지원하는 언어에서 Double Dispatch를 흉내내는** 것이다.

#### Single Dispatch가 왜 문제인가

Java는 메서드 호출 시 **수신자(receiver) 객체의 런타임 타입**으로만 메서드를 선택한다. 즉 `a.method(b)`에서 `method`가 오버로딩되어 있어도 `b`의 **컴파일 타임 타입**으로 메서드가 결정된다. 이게 Single Dispatch다.

```java
class Shape {}
class Circle extends Shape {}
class Square extends Shape {}

class Renderer {
    void render(Shape s) { System.out.println("Shape"); }
    void render(Circle c) { System.out.println("Circle"); }
    void render(Square s) { System.out.println("Square"); }
}

Shape shape = new Circle();
Renderer r = new Renderer();
r.render(shape);  // "Shape" 출력. "Circle"이 아니다.
```

`shape`의 런타임 타입은 `Circle`이지만, 컴파일러는 `shape`의 **정적 타입**인 `Shape`를 보고 `render(Shape)`를 선택한다. 이걸 해결하려면 `instanceof` 체인을 쓰거나 Visitor를 쓴다.

#### Visitor의 Double Dispatch 원리

```java
interface ShapeVisitor<R> {
    R visit(Circle c);
    R visit(Square s);
}

abstract class Shape {
    abstract <R> R accept(ShapeVisitor<R> v);  // 첫 번째 dispatch
}

class Circle extends Shape {
    @Override
    <R> R accept(ShapeVisitor<R> v) {
        return v.visit(this);  // 두 번째 dispatch: this는 Circle로 고정됨
    }
}

class Square extends Shape {
    @Override
    <R> R accept(ShapeVisitor<R> v) {
        return v.visit(this);
    }
}
```

호출 흐름을 보면:

1. `shape.accept(visitor)` — `shape`의 런타임 타입(`Circle`)으로 `Circle.accept`가 선택된다. (첫 dispatch)
2. `Circle.accept` 내부에서 `v.visit(this)` 호출 — `this`의 **컴파일 타임 타입이 `Circle`로 고정**이므로 `visit(Circle)`이 선택된다. (두 번째 dispatch)

두 번의 단일 디스패치를 연쇄하여 `(shape 타입, visitor 타입)` 두 축으로 메서드를 고르는 효과를 만든다. 이게 Double Dispatch의 전부다.

#### 실무 사례: Jackson의 JsonNode.traverse()

Jackson의 `JsonNode`는 Visitor 대신 `JsonParser`를 사용한 **스트리밍 순회**를 하지만, `com.fasterxml.jackson.databind.jsonFormatVisitors` 패키지에는 진짜 Visitor 구현이 있다. `JsonFormatVisitorWrapper`가 Visitor 역할을 하고, 각 `JsonSerializer`가 `acceptJsonFormatVisitor(JsonFormatVisitorWrapper v, JavaType t)`를 구현한다. 이걸로 스키마 생성기(JSON Schema, Avro Schema)가 동작한다.

ANTLR이 생성하는 파서는 더 교과서적이다. `.g4` 파일로부터 파서 트리의 각 노드(`ExprContext`, `StmtContext` 등)가 자동 생성되고, `Visitor`와 `Listener` 두 가지 순회 방식을 제공한다. `Visitor`는 **반환값이 있고 순회 흐름을 직접 제어**하는 반면, `Listener`는 **반환값 없이 enter/exit 이벤트만 받는다**. 큰 AST를 변환할 때는 Visitor, 단순 집계나 로깅은 Listener를 쓴다.

#### Java 타입 시스템의 한계

Visitor의 가장 큰 문제는 **새로운 Element 타입을 추가할 때 모든 Visitor를 수정**해야 한다는 점이다. 이걸 표현 문제(Expression Problem)라고 한다:

- 클래스 계층에 메서드 추가 = OO 언어에서 쉬움 (새 Visitor 작성)
- 클래스 계층에 타입 추가 = 함수형 언어에서 쉬움 (새 타입 + 새 case 추가)
- 둘 다 쉬운 언어는 드물다

Java 21의 sealed class + pattern matching이 Visitor를 부분적으로 대체한다:

```java
sealed interface Shape permits Circle, Square, Triangle {}
record Circle(double r) implements Shape {}
record Square(double s) implements Shape {}
record Triangle(double a, double b, double c) implements Shape {}

double area(Shape shape) {
    return switch (shape) {
        case Circle(double r) -> Math.PI * r * r;
        case Square(double s) -> s * s;
        case Triangle(double a, double b, double c) -> {
            double p = (a + b + c) / 2;
            yield Math.sqrt(p * (p-a) * (p-b) * (p-c));
        }
    };
}
```

`sealed` 덕분에 컴파일러가 **switch의 exhaustiveness**를 검사한다. 새 구현체를 `permits`에 추가하면 모든 switch가 컴파일 에러를 내므로, Visitor 없이도 새 타입 추가 시 누락된 처리를 찾아준다. 이게 Visitor를 죽이진 않지만, 새 코드에서 Visitor를 쓸 이유는 크게 줄었다.

### 1.2 Mediator — 객체 간 결합을 중재자로 흡수

Mediator는 **N개의 객체가 서로 직접 통신하는 대신 중재자 하나를 거치게 하는** 패턴이다. N^2 관계를 N개로 줄인다.

대표적인 실무 사례가 `java.util.concurrent.Executor`다. 스레드(워커)와 태스크(요청)가 직접 통신하지 않고 `ThreadPoolExecutor`라는 중재자를 거친다. 태스크는 스레드의 존재를 모르고, 스레드는 태스크를 큐에서 가져갈 뿐이다.

Spring의 `ApplicationEventPublisher`도 넓은 의미의 Mediator다. 발행자와 구독자가 서로를 모르고, `ApplicationContext`가 중간에서 이벤트를 라우팅한다. 채팅방 구현에서 각 사용자가 서로 참조하지 않고 `ChatRoom`을 거쳐 메시지를 주고받는 것도 전형적인 Mediator 예시다.

```java
public interface ChatMediator {
    void send(String message, User sender);
    void register(User user);
}

public class ChatRoom implements ChatMediator {
    private final List<User> users = new ArrayList<>();

    @Override
    public void send(String message, User sender) {
        for (User u : users) {
            if (u != sender) u.receive(message);
        }
    }

    @Override
    public void register(User user) { users.add(user); }
}

public abstract class User {
    protected final ChatMediator mediator;
    protected final String name;

    public abstract void receive(String message);
    public void send(String msg) { mediator.send(msg, this); }
}
```

주의할 점은 **Mediator가 God Object가 되기 쉽다**는 것이다. 모든 객체의 상호작용이 Mediator를 지나가면, Mediator 안에 분기와 조건이 계속 늘어난다. 실무에서 Mediator를 유지할 때는 **도메인별로 Mediator를 쪼개거나, 이벤트 기반으로 전환**하는 게 좋다.

### 1.3 Memento — 상태 캡처와 외부 참조의 캡슐화

Memento는 **객체의 내부 상태를 외부로 노출하지 않고 저장/복원하게 하는** 패턴이다. 핵심은 캡슐화를 깨지 않는 것이다.

세 개의 역할이 있다:

- **Originator**: 상태를 가진 객체. `createMemento()`로 자기 상태를 Memento로 포장하고, `restore(Memento)`로 복원한다.
- **Memento**: 상태의 스냅샷. 외부에서는 불투명하다(내부를 볼 수 없다).
- **Caretaker**: Memento를 저장/관리한다. 스택, 리스트, DB 등이 될 수 있다.

```java
public class Editor {
    private String content;
    private int cursorPos;

    public Memento save() {
        return new Memento(content, cursorPos);
    }

    public void restore(Memento m) {
        this.content = m.content;
        this.cursorPos = m.cursorPos;
    }

    // 정적 중첩 클래스로 캡슐화. Memento의 필드는 Editor만 볼 수 있다.
    public static class Memento {
        private final String content;
        private final int cursorPos;
        private Memento(String content, int cursorPos) {
            this.content = content;
            this.cursorPos = cursorPos;
        }
    }
}
```

Java에서 Memento를 "정말로" 캡슐화하려면 중첩 클래스의 생성자와 필드를 private으로 두고, 외부에서는 opaque 토큰으로만 다룬다. 실무에서는 이 수준까지 엄격히 하는 경우는 드물고, 보통 record나 DTO로 단순하게 만든다.

실제 적용 사례로 **Hibernate의 Session snapshot**이 있다. 엔티티를 영속화할 때 원본 상태를 `EntityEntry`에 저장해두고, `flush` 시점에 변경 감지(dirty checking)에 사용한다. `EntityEntry`는 외부에서 접근할 수 없는 Memento다.

주의할 점은 **상태가 크거나 자주 캡처되면 메모리 문제**가 생긴다는 것이다. 에디터에서 키 입력마다 전체 문서를 스냅샷으로 저장하면 100KB 문서에서 수백 MB 메모리를 쓴다. 실무에서는 diff 기반 저장(Operational Transformation, CRDT), 또는 일정 간격/행동 단위 스냅샷을 쓴다.

### 1.4 Iterator — JDK의 fail-fast와 spliterator

Iterator 자체는 이제 너무 당연해서 패턴으로 언급되는 일이 드물지만, JDK의 구현은 의외로 복잡하다.

`ArrayList.iterator()`가 반환하는 `Itr`은 `modCount`를 매 호출마다 비교한다:

```java
// ArrayList.Itr 내부
final void checkForComodification() {
    if (modCount != expectedModCount)
        throw new ConcurrentModificationException();
}
```

`modCount`는 리스트가 **구조적으로 변경될 때마다** 증가한다. 이터레이터 생성 시점의 값을 `expectedModCount`로 저장하고, `next()`나 `remove()` 호출 때마다 비교한다. 이게 **fail-fast** 동작이다. 주의할 점은 이게 **best-effort**라는 것이다. 멀티스레드 환경에서는 검출을 보장하지 않고, `CopyOnWriteArrayList`는 아예 fail-safe(스냅샷 이터레이터)를 사용한다.

Java 8부터는 `Spliterator`가 Iterator의 병렬화 버전으로 추가됐다. 핵심 차이는 `trySplit()`으로 **절반으로 나눠서 다른 스레드에 넘길 수 있다**는 점이다. `Stream.parallel()`의 내부 구현이 `Spliterator`의 분할 특성을 이용한다.

실무에서 Iterator를 직접 구현할 때는 `hasNext()`가 **side effect가 없어야** 한다는 점을 지키는 게 어렵다. DB 커서를 감싸는 Iterator를 만들 때 `hasNext()` 안에서 다음 레코드를 pre-fetch하면, `hasNext()`를 두 번 호출했을 때 레코드를 건너뛰거나 중복 읽는 버그가 생긴다. 해결책은 **1개짜리 버퍼**를 유지하는 것이다.

```java
class PrefetchingIterator<T> implements Iterator<T> {
    private final Supplier<T> source;
    private T next;
    private boolean hasNext;
    private boolean fetched;

    @Override
    public boolean hasNext() {
        if (!fetched) {
            next = source.get();
            hasNext = next != null;
            fetched = true;
        }
        return hasNext;
    }

    @Override
    public T next() {
        if (!hasNext()) throw new NoSuchElementException();
        T result = next;
        fetched = false;
        next = null;
        return result;
    }
}
```

### 1.5 Interpreter — ANTLR와 Spring SpEL 내부

Interpreter는 언어를 정의하고 문장을 해석하는 패턴이다. 실무에서 이걸 손으로 구현하는 일은 거의 없다. 대신 **Spring SpEL**, **ANTLR**, **JavaCC** 같은 도구가 이걸 대신 한다. 그래서 이 패턴을 이해하는 목적은 "만드는 법"보다 "내가 쓰는 도구가 뭘 하는지" 파악하는 것이다.

Spring SpEL(`#{...}`)은 내부적으로 AST를 만들고, 각 노드가 `getValue(ExpressionState)` 메서드로 자기를 평가한다. 예를 들어 `#{user.age > 18}`은 다음과 같이 평가된다:

```
GreaterThan
├── PropertyOrFieldReference("age")
│   └── PropertyOrFieldReference("user")
└── IntLiteral(18)
```

각 노드가 재귀적으로 `getValue`를 호출하면서 값을 조립한다. 이게 가장 순수한 형태의 Interpreter 패턴이다.

다만 Interpreter는 **성능이 느리다**. AST 재귀는 메서드 호출이 많고, JIT가 인라이닝하기 어렵다. SpEL은 처음에는 해석(interpreted) 모드로 동작하다가, 같은 표현식이 N번 이상 평가되면 내부적으로 **컴파일 모드**로 전환된다(`SpelCompilerMode.MIXED`). 이러면 바이트코드를 생성해서 직접 실행한다. ANTLR도 비슷하게 파서 생성 시 **테이블 기반 해석**이 아닌 **예측 가능한 코드 경로**로 생성한다.

Interpreter 패턴 자체를 손으로 쓰는 상황은 거의 없지만, 이 도구들이 왜 특정 구문에서 느린지, 왜 파싱 후 캐시가 중요한지를 이해하려면 내부 구조를 알아야 한다.

## 2. Observer 심화 — Push/Pull, 디스패치 모델, 이벤트 루프

기본 문서의 Observer는 "관찰자에게 알림을 보낸다"까지만 다룬다. 실무에서 Observer가 깨지는 지점은 **알림을 어떻게 전달하는가**에 있다.

### 2.1 Push 모델 vs Pull 모델

- **Push**: Subject가 변경 데이터를 Observer에게 직접 전달 (`observer.onUpdate(newData)`)
- **Pull**: Subject가 변경 사실만 알리고, Observer가 필요한 데이터를 다시 조회 (`observer.onChange(); observer.fetch()`)

Push는 빠르지만 **Observer가 원하는 데이터가 고정되지 않은 경우** 매번 다 보내느라 낭비가 크다. Pull은 유연하지만 네트워크/DB 조회가 추가로 발생한다.

Spring의 `@EventListener`는 기본적으로 Push다. 이벤트 객체에 필요한 데이터를 담아 보낸다. 반면 RxJava/Reactor의 backpressure는 Pull에 가깝다. 구독자가 `request(n)`으로 요청한 만큼만 publisher가 보낸다.

### 2.2 동기 디스패치 vs 비동기 디스패치

Observer 호출을 **Subject의 스레드에서 그대로** 할지, **별도 스레드/큐로 넘겨서** 할지에 따라 동작이 크게 달라진다.

동기 디스패치의 함정은 **Observer 중 하나가 느리면 Subject 전체가 막힌다**는 것이다. 더 심각한 건, Observer 안에서 Subject의 상태를 다시 변경하면 **재진입(reentrancy)**이 발생한다. 순회 중 리스트를 수정하면 `ConcurrentModificationException`이 터지거나, 심한 경우 무한 루프에 빠진다.

비동기 디스패치는 이 문제를 해결하지만, **순서 보장**이 사라진다. 이벤트 A, B를 순서대로 발행해도 별도 스레드에서 실행되면 B가 먼저 처리될 수 있다. 또한 **실패 처리**가 어렵다. Observer가 예외를 던졌을 때 어떻게 복구할지가 Subject에서 분리된다.

Spring의 `@Async @EventListener` 조합은 비동기 디스패치지만, 내부적으로 `TaskExecutor`가 단일 스레드면 순서가 유지되고, 풀이 여러 개면 유지되지 않는다. 이 디테일을 모르고 쓰면 "로컬에서는 됐는데 운영에서 순서가 어긋난다"는 버그가 난다.

### 2.3 이벤트 루프 통합 (Netty, Node.js, Vert.x)

Netty 같은 이벤트 루프 기반 프레임워크에서 Observer는 **이벤트 루프 스레드에서 실행된다는 제약**이 있다. `ChannelHandler`가 일종의 Observer인데, 여기서 blocking 호출을 하면 이벤트 루프가 통째로 멈춘다.

```java
public class BadHandler extends ChannelInboundHandlerAdapter {
    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) {
        // 이벤트 루프 스레드에서 JDBC 호출. 절대 하면 안 됨.
        String result = jdbcTemplate.queryForObject(...);
        ctx.writeAndFlush(result);
    }
}
```

이벤트 루프 하나가 수천 개의 커넥션을 담당하므로, 한 Observer가 10ms 블로킹하면 그동안 모든 커넥션이 멈춘다. 해결책은 별도 `EventExecutorGroup`을 써서 blocking 작업을 옮기거나, 아예 non-blocking 드라이버(R2DBC 등)를 쓰는 것이다.

### 2.4 Spring ApplicationEvent vs Reactor Sinks

실무에서 이벤트 시스템을 고를 때 선택지가 둘이다.

| 항목 | ApplicationEvent | Reactor Sinks |
|------|-----------------|---------------|
| **동기/비동기** | 기본 동기, `@Async`로 비동기 | 기본 비동기 (Schedulers 기반) |
| **순서 보장** | 동기 모드는 보장, 비동기는 Executor에 따라 다름 | backpressure 설정에 따라 다름 |
| **backpressure** | 없음 | 있음 (`Sinks.Many.onBackpressureBuffer`) |
| **구독자 관리** | `ApplicationContext`가 Bean으로 관리 | 명시적 `subscribe()` 호출 |
| **에러 처리** | `ErrorHandler` 또는 Observer 내부 try-catch | `onErrorXxx()` 오퍼레이터 |
| **용도** | Application 내부 이벤트, 트랜잭션 연계 | 스트리밍, 비동기 파이프라인 |

`ApplicationEvent`는 트랜잭션 연계(`@TransactionalEventListener`)가 강점이고, Reactor는 **backpressure**가 필요한 스트리밍에서 유리하다. 이벤트가 초당 수천 건 이상 쏟아지는 경우 `ApplicationEvent`의 `ApplicationEventMulticaster`가 병목이 된다. 이땐 Reactor Sinks나 전용 메시지 브로커(Kafka, RabbitMQ)를 써야 한다.

Observer가 Spring Bean이고 영속성 레이어와 엮이면, `@TransactionalEventListener(phase = AFTER_COMMIT)`를 쓰는 일이 많다. 이벤트가 **트랜잭션 커밋 후에만** 발행된다. 이걸 안 쓰면 "롤백됐는데 외부 시스템엔 이미 알림이 갔다"는 사고가 난다.

## 3. Strategy vs State vs Command 내부 비교

겉으로 비슷해 보이는 세 패턴을 **스택 프레임, 상태 머신, 객체 수명** 관점에서 비교한다.

### 3.1 스택 프레임 관점

Strategy는 **스택 프레임이 한 번 쌓이고 끝난다**. `strategy.execute()`를 호출하면 호출 시점에 어떤 Strategy인지 결정되고, 그 호출이 끝나면 Strategy 객체는 용도를 다한다. 호출 사이에 상태를 유지할 필요가 없다.

State는 **연속된 호출 사이에 상태를 유지**한다. `context.doAction1()`, `context.doAction2()`를 연달아 호출했을 때, 두 번째 호출이 첫 번째 결과에 영향을 받는다. 스택 프레임은 매번 새로 쌓이지만, Context의 필드에 상태가 남는다.

Command는 **호출을 데이터로 저장**한다. Strategy의 `execute()`는 즉시 호출되지만, Command의 `execute()`는 **나중에 호출할 수 있는 객체로 포장**된다. 스택 프레임이 지금 쌓이지 않고, 나중에(혹은 다른 스레드에서, 또는 여러 번) 쌓일 수 있다.

### 3.2 상태 머신 관점

State는 **명시적 상태 머신**이다. 상태 객체 안에서 다음 상태로 전이하는 로직이 있다. State를 쓴다는 건 FSM(유한 상태 머신)을 쓴다는 것과 거의 같은 의미다.

Strategy에는 상태 머신이 없다. 알고리즘 선택은 외부(클라이언트)에서 하고, Strategy 자신은 스스로 다음 Strategy로 전이하지 않는다. Strategy 내부에서 "이 조건이면 다음엔 B 전략을 써야 해"를 하면 그건 이미 State로 변질된 것이다.

Command는 상태 머신의 **전이 트리거**로 쓰일 수 있다. Command 패턴과 State 패턴을 조합하면 "사용자 입력 → Command 객체 → Context에 적용 → 상태 전이"의 파이프라인이 된다. Redux의 action + reducer가 정확히 이 조합이다.

### 3.3 객체 수명 관점

- **Strategy**: 호출 직전에 생성되고, 호출 끝나면 GC. 또는 Bean으로 싱글톤 유지 (Spring 패턴).
- **State**: Context에 소속됨. Context 생존 기간 동안 유지되며, 전이할 때마다 새 State로 교체.
- **Command**: 독립적으로 존재. 히스토리 큐나 undo 스택에 담기면 수명이 길다. 직렬화해서 DB/메시지 큐에 보낼 수도 있다.

Command가 직렬화되면 프로세스 경계를 넘을 수 있다. Celery, RabbitMQ, Kafka에 던져지는 메시지가 사실상 Command다. Strategy를 직렬화해서 보내는 건 가능은 하지만 이상하다 — 실행 컨텍스트가 원격에 있을 이유가 없다. State를 직렬화하는 건 스냅샷(Memento) 얘기에 가깝다.

## 4. Chain of Responsibility 심화 — Servlet Filter와 Netty Pipeline

### 4.1 두 가지 구현 스타일

CoR은 크게 **포인터 체인**과 **리스트 순회** 두 가지로 구현된다.

**포인터 체인 (전통적 GoF)**:

```java
abstract class Handler {
    private Handler next;
    public void handle(Request r) {
        if (canHandle(r)) doHandle(r);
        if (next != null) next.handle(r);
    }
}
```

각 핸들러가 다음 핸들러 포인터를 가진다. 체인 수정이 어렵다 (순서 바꾸려면 포인터를 다시 연결해야 함).

**리스트 순회 (Servlet Filter 스타일)**:

```java
class FilterChain {
    private final List<Filter> filters;
    private int index = 0;

    public void doFilter(Request r, Response resp) {
        if (index < filters.size()) {
            filters.get(index++).doFilter(r, resp, this);
        }
    }
}

interface Filter {
    void doFilter(Request r, Response resp, FilterChain chain);
    // 구현에서 chain.doFilter(r, resp)를 호출하면 다음 필터로 진행
}
```

체인 자체가 상태(`index`)를 가지고, 핸들러가 `chain.doFilter()`를 명시적으로 호출해야 다음으로 넘어간다. **중간에서 종료**가 자연스럽다 (그냥 안 부르면 됨). Spring Security의 `FilterChainProxy`도 이 스타일이다.

### 4.2 Netty ChannelPipeline — 더블 링크드 리스트

Netty의 `ChannelPipeline`은 **양방향 링크드 리스트**다. 각 `ChannelHandlerContext`가 이전/다음 컨텍스트를 가리킨다. 왜 양방향이냐면, 이벤트가 **inbound(읽기)**와 **outbound(쓰기)** 두 방향으로 흐르기 때문이다.

- Inbound: 소켓에서 데이터가 들어오면 HEAD → TAIL 방향으로 전파 (`ChannelInboundHandler`)
- Outbound: 애플리케이션이 `writeAndFlush()` 하면 TAIL → HEAD 방향으로 전파 (`ChannelOutboundHandler`)

```
HEAD ◀──── Decoder ◀──── BusinessHandler ◀──── Encoder ◀──── TAIL
           (inbound)      (inbound)              (outbound)
                                ▲                      │
                         ctx.fireChannelRead()  ctx.write()
```

핵심은 `ctx.fireChannelRead(msg)`가 **다음 inbound 핸들러로 이벤트를 전파**하는 호출이라는 것이다. 이걸 호출하지 않으면 이벤트가 거기서 멈춘다. `ctx.write(msg)`는 반대로 이전 outbound 핸들러로 전파한다.

성능 관점에서 Netty는 핸들러마다 `ChannelHandlerContext`를 미리 만들어서 포인터를 연결해둔다. `pipeline.addLast()`가 O(1)이고, 메시지 전파는 포인터 따라가는 단순 호출이라 JIT가 잘 인라이닝한다.

### 4.3 성능 특성

CoR의 성능 문제는 두 가지다.

**메서드 호출 비용**: N개 핸들러면 N번의 가상 메서드 호출이 발생한다. 대부분 인라이닝되지만, **인터페이스 기반 다형성**은 JIT가 구현체를 확정하기 어려워서 인라이닝 실패하기 쉽다. 핸들러가 많은 체인(20개 이상)에서는 이게 눈에 보인다.

**조기 종료 vs 전체 순회**: 체인이 "처음 match된 핸들러가 처리" 세만틱이면 조기 종료로 평균 O(N/2)지만, "모든 핸들러가 처리" 세만틱이면 항상 O(N)이다. Servlet Filter는 후자에 가깝다. 로그 필터, 인증 필터, CORS 필터가 모두 모든 요청에 대해 실행된다.

**분기 예측 실패**: 핸들러의 `canHandle()` 결과가 요청마다 다르게 분기되면 CPU의 분기 예측이 실패한다. 실무에서 문제가 되는 경우는 드물지만, 초당 수십만 요청을 처리하는 체인에서는 핸들러 순서를 **선택률이 높은 것부터** 배치하는 게 도움이 된다.

## 5. Template Method의 Hook 메서드와 JIT 최적화

### 5.1 Hook 메서드

Template Method에는 세 종류의 메서드가 있다:

1. **추상 메서드**: 하위 클래스에서 반드시 구현 (`abstract`)
2. **최종 메서드**: 하위 클래스에서 바꿀 수 없음 (`final`)
3. **Hook 메서드**: 기본 구현이 있고 선택적으로 오버라이드 (`protected`, 비 final)

Hook은 확장 지점이다. `HttpServlet.service()`가 좋은 예시로, `doGet`, `doPost`가 Hook이다. 기본 구현은 405 Method Not Allowed를 반환하고, 하위 클래스가 필요한 것만 오버라이드한다.

실수하기 쉬운 지점은 **Hook이 공개(public)되면 외부에서 직접 호출할 수 있다**는 것이다. Template Method의 계약은 "외부는 `execute()`만 호출, 내부는 hook을 통해 확장"인데, Hook이 public이면 이 계약이 깨진다. `protected`로 두는 게 맞다.

### 5.2 JIT 인라이닝 실패

JVM은 가상 메서드 호출을 인라이닝해서 최적화한다. 하지만 Template Method는 **추상 메서드 호출**이 필수이고, 이게 런타임에 여러 구현체를 만나면 **bimorphic/megamorphic call site**가 되어 인라이닝이 실패한다.

JIT는 call site의 타입 프로파일을 기록한다:

- 1개 타입만 보였음 → monomorphic. 인라이닝됨.
- 2개 타입이 보였음 → bimorphic. 둘 다 인라이닝 가능 (HotSpot은 최대 2개).
- 3개 이상 → megamorphic. 인라이닝 실패. vtable lookup.

Template Method를 쓰는 부모 클래스가 하나의 인스턴스로만 쓰이면 monomorphic이다. 하지만 `DataExporter` 같은 클래스가 CSV, JSON, XML 세 가지 구현체로 실행되는 테스트를 돌리면 megamorphic이 된다. 이러면 알고리즘 골격(`export()`)의 호출은 인라이닝되지만, 그 안의 `filter()`, `format()`, `write()` 호출은 vtable lookup이 된다.

보통은 이게 문제가 안 된다. 진짜 hot path가 아닌 이상 메서드 호출 몇 번으로 성능이 망가지진 않는다. 문제가 되는 경우는:

- **Tight loop 안에서 Template Method를 호출** (수백만 번/초)
- **구현체가 5개 이상**인 계층
- **micro-benchmark에서만 티가 나는 경우**가 대부분이라 실제 운영에서 보이는 일은 드물다

실측 없이 Template Method를 걷어내는 건 과한 최적화다. 다만 hot path에서 JMH로 측정했을 때 인라이닝 실패가 병목으로 나오면, `final` 클래스로 만들거나 아예 Strategy(인터페이스 1개 + lambda)로 바꾸는 게 대안이다.

## 6. 패턴 간 조합

패턴은 혼자 쓰이지 않는다. 실무에서 유용한 조합 몇 가지.

### 6.1 Command + Memento = Undo 스택

Command의 `undo()`를 구현하려면, 실행 전 상태를 어딘가 저장해야 한다. 단순한 경우는 Command 내부에 이전 값을 보관하면 되지만, 상태가 복잡하면 Memento를 같이 쓴다.

```java
class EditCommand implements Command {
    private final Editor editor;
    private final String newText;
    private Editor.Memento snapshot;

    @Override
    public void execute() {
        snapshot = editor.save();  // Memento 생성
        editor.setText(newText);
    }

    @Override
    public void undo() {
        editor.restore(snapshot);  // Memento로 복원
    }
}
```

Caretaker 역할은 Command 히스토리 스택이 겸한다. 브라우저의 텍스트 에디터, 포토샵의 History 패널이 이 구조다.

### 6.2 Observer + Mediator = Event Bus

채널 기반 Event Bus는 Observer의 분산 버전 + Mediator다. Publisher는 "채널 X에 이벤트를 던진다"만 알고, Subscriber는 "채널 X를 구독한다"만 안다. 중간의 Event Bus가 라우팅을 맡는다.

Kafka, RabbitMQ, Redis Pub/Sub가 이 구조를 네트워크 레벨로 올린 것이다. Spring `ApplicationEventMulticaster`도 프로세스 내 Event Bus다. EventBridge, SNS, EventGrid 같은 클라우드 서비스도 동일 패턴이다.

### 6.3 Strategy + Factory = 플러그인 아키텍처

런타임에 Strategy를 고르되, Factory가 **어떤 Strategy 구현체를 쓸지 결정**한다. Spring의 `Map<String, PaymentStrategy>` 주입이 가장 흔한 형태다.

이걸 확장하면 클래스패스 스캔 기반 플러그인 아키텍처가 된다. Java의 `ServiceLoader`가 딱 이 용도다:

```
META-INF/services/com.example.PaymentStrategy
  com.plugin.TossPayStrategy
  com.plugin.KakaoPayStrategy
```

`ServiceLoader.load(PaymentStrategy.class)`로 모든 구현체를 찾아 Factory에 등록. JDBC 드라이버, SLF4J 바인딩, Spring Boot auto-configuration이 비슷한 메커니즘이다.

### 6.4 Chain of Responsibility + Command = 미들웨어

HTTP 미들웨어는 CoR 위에 Command를 태운 구조다. Request가 Command처럼 객체로 포장되어 체인을 따라 흐르고, 각 핸들러가 필요한 처리를 한다. Express.js의 `app.use()`, ASP.NET Core의 `IMiddleware`, Spring의 `HandlerInterceptor`가 모두 이 구조다.

## 7. 실무 트레이드오프

### 7.1 패턴을 쓰지 말아야 할 때

"이건 Strategy 패턴이에요"라고 말한다고 코드가 좋아지진 않는다. 오히려 다음 상황에서는 패턴을 안 쓰는 게 낫다.

- **구현체가 2개 이하이고, 추가될 가능성이 없는 경우**: if-else가 더 읽기 쉽다.
- **한 번 실행되고 끝나는 스크립트성 코드**: 추상화 비용 > 얻는 것.
- **타입이 없는 동적 언어**: 인터페이스의 역할이 약해서 패턴이 주는 이점이 적다.
- **상태가 극도로 단순한 경우**: State 패턴보다 enum + switch가 낫다.
- **프레임워크가 이미 해결하는 경우**: Spring이 이미 CoR을 제공하는데 손으로 또 만들 필요 없다.

과한 패턴화는 **Pattern Disease**라고 불린다. 모든 걸 `XxxFactory`, `XxxStrategy`, `XxxHandler`로 쪼개면 로직을 추적하려고 5개 파일을 열어야 한다. 패턴을 쓰는 이유는 **변경 가능성**이다. 변경될 일이 없으면 패턴이 비용만 된다.

### 7.2 함수형 대체

Java 8+ 람다는 많은 행위 패턴을 평범한 함수 값으로 대체한다.

```java
// Strategy — 인터페이스 + 구현 클래스 → Function<T, R>
Function<Money, PaymentResult> cardPayment = amount -> cardApi.charge(amount);
Function<Money, PaymentResult> kakaoPayment = amount -> kakaoPayApi.pay(amount);

Map<String, Function<Money, PaymentResult>> strategies = Map.of(
    "CARD", cardPayment,
    "KAKAO", kakaoPayment
);

// Command — 클래스 → Runnable
Deque<Runnable> history = new ArrayDeque<>();
history.push(() -> repository.save(order));

// Observer — 인터페이스 → Consumer<Event>
List<Consumer<OrderEvent>> listeners = new ArrayList<>();
listeners.add(event -> logger.info("Order: {}", event));

// Template Method — 상속 → 고차 함수
public <T> void export(List<T> data, Function<T, String> formatter, Consumer<String> writer) {
    validate(data);
    String content = data.stream().map(formatter).collect(joining("\n"));
    writer.accept(content);
}
```

람다로 쓰면 **클래스 선언이 사라지고** 의도가 코드에 직접 드러난다. 다만 상태가 있는 경우(State 패턴), 복잡한 로직(Visitor), 여러 메서드를 가진 계약(Mediator)은 람다로 표현하기 어렵다.

Scala/Kotlin의 sealed class + pattern matching, Rust/Swift의 enum associated values는 Visitor/State 패턴을 거의 대체한다. Java도 21부터 따라잡는 중이다.

### 7.3 리플렉션/어노테이션으로 인한 패턴 해체

Spring의 `@EventListener`, `@RequestMapping`, `@Scheduled` 같은 어노테이션은 원래 Observer/Strategy/Command 패턴이 하던 일을 **리플렉션으로 대체**한다.

전통적 Observer라면:

```java
applicationContext.registerListener(new MyListener());
```

Spring은:

```java
@Component
public class MyService {
    @EventListener
    public void onOrderCreated(OrderCreatedEvent event) { ... }
}
```

클래스가 `ApplicationListener`를 구현하지 않아도 되고, 명시적 등록도 필요 없다. 대신 Spring이 **리플렉션으로 `@EventListener` 메서드를 스캔**해서 내부적으로 Observer처럼 연결한다.

이걸 두고 "패턴이 해체됐다"고 표현하기도 한다. 외형상으로는 POJO지만, 프레임워크가 뒤에서 패턴의 배선을 대신한다. 장점은 **비침투적(non-invasive)**이라는 것이고, 단점은 **컴파일 시점에 연결이 드러나지 않는다**는 것이다. IDE의 "Find Usages"로 이벤트 흐름을 추적하기 어려워진다. 운영에서 이벤트가 안 날아온다는 버그가 생기면, 리스너가 등록됐는지, 트랜잭션 phase가 맞는지, 비동기 설정은 어떤지를 코드가 아니라 **런타임 설정**에서 찾아야 한다.

어노테이션 기반 패턴 해체가 주는 교훈은, **패턴이 언어의 한계를 극복하기 위한 장치**였다는 점이다. Java에 이벤트 시스템이 내장되어 있었다면 Observer 패턴이 이렇게 교과서에 실리지 않았을 것이다. Kotlin의 `delegate`, Scala의 `implicit`, C#의 `event` 키워드는 각자의 방식으로 행위 패턴을 언어 레벨로 흡수한 예시다.

## 참고

- [기본 행동 패턴 가이드](Behavioral_Pattern.md) — Strategy/Template Method/Command/State/CoR 기본 사용법
- [Observer 패턴](Observer Pattern.md) — Observer 패턴 상세
- [Design Patterns — GoF](https://www.amazon.com/Design-Patterns-Elements-Reusable-Object-Oriented/dp/0201633612)
- [Refactoring.Guru — Behavioral Patterns](https://refactoring.guru/design-patterns/behavioral-patterns)
- [Effective Java 3rd — Item 22, 42, 43, 44](https://www.oreilly.com/library/view/effective-java-3rd/9780134686097/) — 인터페이스, 람다, 메서드 참조
- [JEP 441: Pattern Matching for switch](https://openjdk.org/jeps/441) — Visitor의 대안
