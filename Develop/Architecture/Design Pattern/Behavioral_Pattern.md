---
title: 행동 디자인 패턴 가이드
tags: [architecture, design-pattern, behavioral, strategy, template-method, command, state, observer, chain-of-responsibility]
updated: 2026-03-01
---

# 행동 디자인 패턴 (Behavioral Patterns)

## 개요

행동 패턴은 **객체 간 책임 분배와 알고리즘 캡슐화**에 관한 패턴이다. 객체가 어떻게 상호작용하고, 어떤 순서로 작업을 수행할지를 정의한다.

### 행동 패턴 한눈에 보기

| 패턴 | 핵심 | 한줄 요약 |
|------|------|----------|
| **Strategy** | 알고리즘 교체 | "결제 방식을 런타임에 바꾼다" |
| **Template Method** | 알고리즘 골격 | "순서는 고정, 세부 구현만 바꾼다" |
| **Command** | 요청 캡슐화 | "실행할 작업을 객체로 만든다" |
| **State** | 상태별 행동 | "상태가 바뀌면 행동이 바뀐다" |
| **Chain of Responsibility** | 처리 체인 | "처리할 수 있는 핸들러를 찾을 때까지 전달" |
| **Observer** | 이벤트 알림 | "상태 변경 시 구독자에게 알린다" |

## 핵심

### 1. Strategy 패턴

**알고리즘(전략)**을 캡슐화하고 런타임에 교체할 수 있게 한다.

```
Context (서비스) ──사용──▶ Strategy (인터페이스)
                           ├── ConcreteStrategyA
                           ├── ConcreteStrategyB
                           └── ConcreteStrategyC
```

#### 예시: 결제 수단 선택

```java
// Strategy 인터페이스
public interface PaymentStrategy {
    PaymentResult pay(Money amount);
}

// 구체 전략들
public class CardPayment implements PaymentStrategy {
    private final String cardNumber;

    @Override
    public PaymentResult pay(Money amount) {
        // 카드 결제 처리
        return cardApi.charge(cardNumber, amount);
    }
}

public class KakaoPayPayment implements PaymentStrategy {
    @Override
    public PaymentResult pay(Money amount) {
        return kakaoPayApi.pay(amount);
    }
}

public class BankTransferPayment implements PaymentStrategy {
    @Override
    public PaymentResult pay(Money amount) {
        return bankApi.transfer(amount);
    }
}

// Context: 전략을 사용하는 클래스
public class PaymentService {
    public PaymentResult processPayment(PaymentStrategy strategy, Money amount) {
        // 결제 전 공통 로직 (로깅, 검증)
        validate(amount);
        PaymentResult result = strategy.pay(amount);  // 전략 실행
        log(result);
        return result;
    }
}

// 사용
PaymentStrategy strategy = switch (request.getMethod()) {
    case "CARD" -> new CardPayment(request.getCardNumber());
    case "KAKAO_PAY" -> new KakaoPayPayment();
    case "BANK" -> new BankTransferPayment();
    default -> throw new IllegalArgumentException("지원하지 않는 결제 수단");
};
paymentService.processPayment(strategy, Money.of(50000));
```

#### Spring에서의 Strategy

```java
// 전략을 Bean으로 등록하고 Map으로 주입
@Component("CARD")
public class CardPayment implements PaymentStrategy { ... }

@Component("KAKAO_PAY")
public class KakaoPayPayment implements PaymentStrategy { ... }

@Service
public class PaymentService {
    private final Map<String, PaymentStrategy> strategies;

    // Spring이 자동으로 Bean 이름을 키로 Map 구성
    public PaymentService(Map<String, PaymentStrategy> strategies) {
        this.strategies = strategies;
    }

    public PaymentResult pay(String method, Money amount) {
        PaymentStrategy strategy = strategies.get(method);
        if (strategy == null) throw new IllegalArgumentException("지원하지 않는 결제");
        return strategy.pay(amount);
    }
}
```

#### 언제 사용하는가

| 상황 | 적합 여부 |
|------|----------|
| if-else/switch로 알고리즘 분기 | ✅ Strategy로 리팩토링 |
| 알고리즘을 런타임에 교체해야 할 때 | ✅ |
| 조건이 2~3개이고 변경 가능성 없을 때 | ❌ 오버 엔지니어링 |

### 2. Template Method 패턴

알고리즘의 **골격(순서)**은 부모 클래스에서 정의하고, 세부 단계만 하위 클래스에서 구현한다.

```
AbstractClass (추상 클래스)
  templateMethod()     ← 알고리즘 순서 고정 (final)
    step1()            ← 공통 구현
    step2()            ← 추상 메서드 (하위 클래스에서 구현)
    step3()            ← 추상 메서드
    │
    ├── ConcreteClassA (step2, step3 구현)
    └── ConcreteClassB (step2, step3 구현)
```

#### 예시: 데이터 내보내기

```java
public abstract class DataExporter {

    // 템플릿 메서드: 순서가 고정됨
    public final void export(List<Data> data) {
        validate(data);           // 1. 검증 (공통)
        List<Data> filtered = filter(data);  // 2. 필터링 (하위에서 구현)
        String formatted = format(filtered);  // 3. 포매팅 (하위에서 구현)
        write(formatted);         // 4. 출력 (하위에서 구현)
        log(data.size());         // 5. 로깅 (공통)
    }

    // 공통 구현
    private void validate(List<Data> data) {
        if (data == null || data.isEmpty()) {
            throw new IllegalArgumentException("데이터가 비어있습니다");
        }
    }

    // 하위 클래스에서 구현
    protected abstract List<Data> filter(List<Data> data);
    protected abstract String format(List<Data> data);
    protected abstract void write(String content);

    // Hook 메서드: 필요 시 오버라이드 (기본 구현 제공)
    protected void log(int count) {
        System.out.println(count + "건 내보내기 완료");
    }
}

public class CsvExporter extends DataExporter {
    @Override
    protected List<Data> filter(List<Data> data) {
        return data.stream().filter(Data::isActive).toList();
    }

    @Override
    protected String format(List<Data> data) {
        return data.stream()
            .map(d -> d.getName() + "," + d.getValue())
            .collect(Collectors.joining("\n"));
    }

    @Override
    protected void write(String content) {
        Files.writeString(Path.of("export.csv"), content);
    }
}

public class JsonExporter extends DataExporter {
    @Override
    protected List<Data> filter(List<Data> data) {
        return data;  // 전체 내보내기
    }

    @Override
    protected String format(List<Data> data) {
        return objectMapper.writeValueAsString(data);
    }

    @Override
    protected void write(String content) {
        Files.writeString(Path.of("export.json"), content);
    }
}
```

#### Strategy vs Template Method

| 항목 | Strategy | Template Method |
|------|---------|----------------|
| **구현** | 합성 (인터페이스) | 상속 (추상 클래스) |
| **교체** | 런타임에 전략 교체 가능 | 컴파일 타임에 결정 |
| **알고리즘 구조** | 전체를 교체 | 골격 고정, 일부만 변경 |
| **유연성** | 더 유연 | 덜 유연 |
| **사용처** | 알고리즘 전체가 다를 때 | 순서는 같고 세부만 다를 때 |

### 3. Command 패턴

요청을 **객체로 캡슐화**하여 매개변수화, 큐잉, 로깅, 실행 취소(Undo)를 가능하게 한다.

```
Client → Invoker → Command(인터페이스) → Receiver
                     ├── ConcreteCommandA
                     └── ConcreteCommandB
```

#### 예시: 주문 처리 시스템

```java
// Command 인터페이스
public interface OrderCommand {
    void execute();
    void undo();       // 실행 취소
}

// 구체 커맨드
public class PlaceOrderCommand implements OrderCommand {
    private final Order order;
    private final OrderRepository repository;

    @Override
    public void execute() {
        order.place();
        repository.save(order);
    }

    @Override
    public void undo() {
        order.cancel();
        repository.save(order);
    }
}

public class CancelOrderCommand implements OrderCommand {
    private final Order order;
    private OrderStatus previousStatus;

    @Override
    public void execute() {
        this.previousStatus = order.getStatus();
        order.cancel();
    }

    @Override
    public void undo() {
        order.setStatus(previousStatus);  // 이전 상태로 복원
    }
}

// Invoker: 커맨드를 실행하고 이력을 관리
public class OrderCommandInvoker {
    private final Deque<OrderCommand> history = new ArrayDeque<>();

    public void execute(OrderCommand command) {
        command.execute();
        history.push(command);
    }

    public void undoLast() {
        if (!history.isEmpty()) {
            OrderCommand last = history.pop();
            last.undo();
        }
    }
}
```

| 활용 | 설명 |
|------|------|
| **Undo/Redo** | 커맨드 히스토리로 실행 취소 |
| **큐잉** | 커맨드를 큐에 넣어 비동기 처리 |
| **로깅** | 실행된 커맨드를 기록하여 감사 추적 |
| **트랜잭션** | 여러 커맨드를 하나의 트랜잭션으로 묶기 |
| **매크로** | 여러 커맨드를 순서대로 실행 |

### 4. State 패턴

객체의 **상태에 따라 행동을 변경**한다. if-else 상태 분기를 제거한다.

```
Context ──현재 상태──▶ State (인터페이스)
                        ├── DraftState
                        ├── PendingState
                        ├── ApprovedState
                        └── RejectedState
```

#### 예시: 주문 상태 머신

```java
// State 인터페이스
public interface OrderState {
    void approve(OrderContext context);
    void reject(OrderContext context);
    void ship(OrderContext context);
    void cancel(OrderContext context);
}

// 구체 상태들
public class PendingState implements OrderState {
    @Override
    public void approve(OrderContext context) {
        System.out.println("주문 승인됨");
        context.setState(new ApprovedState());
    }

    @Override
    public void reject(OrderContext context) {
        System.out.println("주문 거부됨");
        context.setState(new RejectedState());
    }

    @Override
    public void ship(OrderContext context) {
        throw new IllegalStateException("승인 전에는 배송할 수 없습니다");
    }

    @Override
    public void cancel(OrderContext context) {
        System.out.println("주문 취소됨");
        context.setState(new CancelledState());
    }
}

public class ApprovedState implements OrderState {
    @Override
    public void approve(OrderContext context) {
        throw new IllegalStateException("이미 승인된 주문입니다");
    }

    @Override
    public void ship(OrderContext context) {
        System.out.println("배송 시작");
        context.setState(new ShippedState());
    }

    @Override
    public void cancel(OrderContext context) {
        System.out.println("승인 후 취소 → 환불 처리 시작");
        context.setState(new CancelledState());
    }
    // ...
}

// Context
public class OrderContext {
    private OrderState state;

    public OrderContext() {
        this.state = new PendingState();  // 초기 상태
    }

    public void setState(OrderState state) {
        this.state = state;
    }

    public void approve() { state.approve(this); }
    public void reject()  { state.reject(this); }
    public void ship()    { state.ship(this); }
    public void cancel()  { state.cancel(this); }
}
```

```
상태 전이 다이어그램:

  Pending ──approve──▶ Approved ──ship──▶ Shipped ──deliver──▶ Delivered
    │                    │
    ├──reject──▶ Rejected
    │                    │
    └──cancel──▶ Cancelled ◀──cancel──┘
```

#### State vs Strategy

| 항목 | State | Strategy |
|------|-------|---------|
| **목적** | 상태에 따른 행동 변경 | 알고리즘 교체 |
| **전환** | 상태가 스스로 다음 상태를 결정 | 클라이언트가 전략 선택 |
| **관계** | 상태 간 전이 관계 있음 | 전략 간 관계 없음 |
| **사용처** | 주문 상태, 게임 캐릭터 상태 | 결제 방식, 정렬 알고리즘 |

### 5. Chain of Responsibility 패턴

요청을 **체인으로 연결된 핸들러**에 전달하여, 처리할 수 있는 핸들러가 처리한다.

```
Request → Handler A → Handler B → Handler C → ...
          (처리 가능하면 처리, 아니면 다음으로 전달)
```

#### 예시: 요청 검증 체인

```java
public abstract class ValidationHandler {
    private ValidationHandler next;

    public ValidationHandler setNext(ValidationHandler next) {
        this.next = next;
        return next;  // 체이닝 지원
    }

    public final void handle(Request request) {
        if (canHandle(request)) {
            doHandle(request);
        }
        if (next != null) {
            next.handle(request);
        }
    }

    protected abstract boolean canHandle(Request request);
    protected abstract void doHandle(Request request);
}

public class AuthenticationHandler extends ValidationHandler {
    @Override
    protected boolean canHandle(Request request) { return true; }

    @Override
    protected void doHandle(Request request) {
        if (request.getToken() == null) {
            throw new UnauthorizedException("인증 토큰이 없습니다");
        }
        // 토큰 검증
    }
}

public class RateLimitHandler extends ValidationHandler {
    @Override
    protected boolean canHandle(Request request) { return true; }

    @Override
    protected void doHandle(Request request) {
        if (rateLimiter.isExceeded(request.getIp())) {
            throw new TooManyRequestsException("요청 한도 초과");
        }
    }
}

public class InputValidationHandler extends ValidationHandler {
    @Override
    protected boolean canHandle(Request request) {
        return request.getBody() != null;
    }

    @Override
    protected void doHandle(Request request) {
        // 입력값 검증
    }
}

// 체인 구성
ValidationHandler chain = new AuthenticationHandler();
chain.setNext(new RateLimitHandler())
     .setNext(new InputValidationHandler());

chain.handle(request);  // 순서대로 검증
```

실무에서는 **Spring Security의 FilterChain**, **Servlet Filter**, **Spring Interceptor**가 이 패턴이다.

### 6. 패턴 선택 가이드

```
"여러 알고리즘 중 하나를 선택해야 한다"
  → if 전체 알고리즘이 다르다 → Strategy
  → if 순서는 같고 세부만 다르다 → Template Method

"요청을 객체로 캡슐화해야 한다"
  → if Undo/Redo가 필요하다 → Command
  → if 큐잉/로깅이 필요하다 → Command

"객체의 상태에 따라 행동이 달라진다"
  → if 상태 전이가 있다 → State
  → if if-else 분기가 5개 이상이다 → State

"요청을 순서대로 여러 핸들러에 전달한다"
  → Chain of Responsibility

"상태 변경을 여러 객체에 알려야 한다"
  → Observer
```

## 참고

- [Design Patterns — GoF](https://www.amazon.com/Design-Patterns-Elements-Reusable-Object-Oriented/dp/0201633612)
- [Refactoring.Guru — Behavioral Patterns](https://refactoring.guru/design-patterns/behavioral-patterns)
- [Observer 패턴](Observer Pattern.md) — 관찰자 패턴
- [생성 패턴](Creational_Pattern.md) — 객체 생성 패턴
- [클린 아키텍처](../Clean_Architecture.md) — 아키텍처 패턴
