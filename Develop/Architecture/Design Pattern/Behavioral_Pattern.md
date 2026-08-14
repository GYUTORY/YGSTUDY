---
title: 행동 패턴 (Behavioral Patterns)
tags: [architecture, design-patterns]
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

위 두 예시는 서로 맞지 않는다. 첫 예시의 `CardPayment` 는 생성자로 카드번호를 받는다(`new CardPayment(request.getCardNumber())`). 두 번째 예시의 `@Component("CARD") CardPayment` 는 싱글턴 빈이라 요청마다 다른 카드번호를 가질 수 없다.

**전략이 요청 데이터를 필드로 들고 있으면 빈으로 만들 수 없다.** 이 충돌은 Strategy 를 DI 컨테이너에 올릴 때 거의 항상 만난다. 해법은 하나뿐이다 — 요청 데이터를 생성자가 아니라 **메서드 인자로** 옮긴다.

```java
public interface PaymentStrategy {
    PaymentResult pay(PaymentRequest request);   // 카드번호는 여기로
}
```

이렇게 하면 전략은 무상태가 되고 싱글턴 빈으로 안전해진다. 대신 인터페이스가 모든 결제 수단의 입력을 합집합으로 받아야 해서 `PaymentRequest` 가 비대해진다. 카드에만 필요한 필드, 계좌이체에만 필요한 필드가 한 DTO 에 섞이고 각 전략은 자기 것만 꺼내 쓴다. 이 부풀어 오르는 파라미터 객체가 Strategy 를 무상태로 유지한 대가다.

Map 주입에도 대가가 있다. **빈 이름이 곧 API 계약이 된다.** `@Component("KAKAO_PAY")` 의 문자열은 클라이언트가 보내는 `method` 값과 정확히 같아야 하는데, 둘을 잇는 것이 문자열뿐이라 컴파일러가 검사하지 못한다. 클래스를 리팩토링하다 어노테이션 값을 건드리거나, 프론트에서 `kakao_pay` 로 보내면 런타임에 `null` 이 나온다. 매핑을 타입으로 붙들고 싶으면 인터페이스에 판별 메서드를 두고 `List` 로 주입받는 편이 낫다.

```java
public interface PaymentStrategy {
    boolean supports(PaymentMethod method);   // enum 으로 받는다
    PaymentResult pay(PaymentRequest request);
}
```

#### 언제 사용하는가

| 상황 | 적합 여부 |
|------|----------|
| if-else/switch로 알고리즘 분기 | 적합 — Strategy로 리팩토링 |
| 알고리즘을 런타임에 교체해야 할 때 | 적합 |
| 조건이 2~3개이고 변경 가능성 없을 때 | 부적합 — 오버 엔지니어링 |

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

#### undo 는 생각만큼 자주 성립하지 않는다

Command 를 도입하는 이유의 절반이 Undo 인데, 위 코드가 보여주는 undo 는 **메모리 안의 값을 되돌리는 것**뿐이다. 실제 주문 처리에는 그 밖의 일이 붙는다.

`PlaceOrderCommand.undo()` 는 `order.cancel()` 을 부른다. 이건 원상복구가 아니라 **"취소"라는 새 비즈니스 이벤트**다. 결제가 이미 승인됐다면 취소 API 를 따로 불러야 하고, 재고 차감을 되돌려야 하고, 발송된 주문 확인 메일은 회수할 방법이 없다. undo 가 이 모두를 알아야 하는 순간 커맨드는 execute 와 거의 같은 크기의 코드를 하나 더 갖게 된다.

`CancelOrderCommand.undo()` 는 더 미묘하다. `previousStatus` 를 그대로 덮어쓰는데, execute 이후 다른 경로에서 주문 상태가 바뀌었다면 그 변경을 지운다. 이 스냅샷 되돌리기는 **그 사이에 아무도 같은 객체를 건드리지 않았을 때만** 맞다.

| undo 가 성립하는 것 | 성립하지 않는 것 |
|---|---|
| 에디터의 텍스트 편집, 도형 이동 | 결제 승인, 메일·푸시 발송 |
| 메모리 안의 상태 전이 | 외부 시스템 호출 |
| 단일 사용자가 소유한 데이터 | 여러 주체가 동시에 바꾸는 데이터 |

외부 부수효과가 있으면 undo 가 아니라 **보상 트랜잭션**을 설계해야 한다. 이름을 `undo()` 로 두면 "되돌릴 수 있다"고 읽히는 것 자체가 위험하다.

`OrderCommandInvoker` 도 그대로 쓰면 안 된다. `history` 는 상한이 없어 계속 자라고, 이 클래스를 스프링 빈으로 등록하면 기본 스코프가 싱글턴이라 **모든 사용자가 한 스택을 공유한다.** A 사용자가 `undoLast()` 를 부르면 B 사용자의 마지막 커맨드가 취소된다. 이력을 쓸 거면 스코프를 세션·주문 단위로 좁히고 크기 상한을 둔다.

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

#### State 를 쓰면 전이 규칙이 흩어진다

위 코드는 상태 5개 × 이벤트 4개 = 클래스 5개에 메서드 20개다. if-else 를 없앤 대신 **전체 상태 기계를 한눈에 볼 수 있는 자리가 사라진다.** 문서가 전이 다이어그램을 별도 코드 블록으로 그려 둔 것이 그 증거다 — 그 그림이 코드 어디에도 없기 때문에 따로 그려야 했고, 코드가 바뀌어도 그림은 따라오지 않는다.

비용은 확장할 때 드러난다. `refund` 이벤트를 추가하면 인터페이스에 메서드가 하나 늘고 **모든 상태 클래스를 고쳐야 한다.** 대부분은 "이 상태에서는 불가"를 던지는 한 줄인데, 그 한 줄을 상태 수만큼 쓴다. 상태를 추가하면 반대로 메서드 수만큼 구현해야 한다. 상태와 이벤트가 각각 늘면 구현 지점은 곱으로 늘어난다.

전이가 단순하고 부수효과가 적으면 **전이 표 하나**가 훨씬 읽기 쉽다.

```java
private static final Map<Transition, OrderStatus> TABLE = Map.of(
    new Transition(PENDING,  APPROVE), APPROVED,
    new Transition(PENDING,  REJECT),  REJECTED,
    new Transition(PENDING,  CANCEL),  CANCELLED,
    new Transition(APPROVED, SHIP),    SHIPPED,
    new Transition(APPROVED, CANCEL),  CANCELLED
);
// 표에 없는 조합 = 불가. else 를 쓸 필요가 없다.
```

표는 전이 규칙 전체가 한 화면에 들어오고, 그대로 테스트 데이터가 되며, 다이어그램 대신 읽을 수 있다. 대신 상태별 행동이 길어질수록 표 밖으로 밀려난다.

| State 클래스가 나은 경우 | 전이 표가 나은 경우 |
|---|---|
| 상태마다 실행할 로직이 길다 | 전이 자체가 관심사고 로직은 짧다 |
| 상태별로 필요한 협력 객체가 다르다 | 전이 후 하는 일이 상태 저장 정도다 |
| 상태 수가 적고 잘 안 늘어난다 | 상태·이벤트가 계속 추가된다 |

영속화도 미리 정해야 한다. `OrderContext` 는 상태를 **객체 참조**로 들고 있는데 DB 에는 문자열이나 enum 으로 저장된다. 그래서 "저장할 때 객체 → 코드, 읽을 때 코드 → 객체" 변환 계층이 반드시 생기고, 이 매핑을 빠뜨리면 재시작 후 주문이 전부 초기 상태로 돌아간다. 상태 객체를 매번 `new` 하는 것도 다시 볼 만하다 — 위 상태 클래스들은 필드가 없으므로 enum 상수나 싱글턴으로 두면 객체 생성과 매핑이 동시에 정리된다.

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

#### 위 코드는 정의대로의 CoR 이 아니다

패턴 설명에는 "처리 가능하면 처리, 아니면 다음으로 전달"이라고 적혀 있다. 처리한 핸들러가 나오면 거기서 멈춘다는 뜻이다. 그런데 `handle()` 은 `canHandle` 이 true 여서 처리한 뒤에도 **무조건** `next.handle(request)` 를 부른다. 멈추는 조건이 없다.

옮겨서 실행해 보면 세 핸들러가 전부 실행되고, 중간 핸들러가 `canHandle` 로 false 를 돌려줘도 뒤 핸들러는 그대로 돈다.

```
문서 방식 실행 순서:        [ Auth, RateLimit, InputValidation ]
중간 핸들러가 처리 거부 시:  [ Auth, Input ]   ← 체인이 끊기지 않는다
```

이건 CoR 이 아니라 **파이프라인(미들웨어)** 이다. 검증 체인이라는 용도에는 오히려 이쪽이 맞다 — 인증했다고 레이트 리밋을 건너뛰면 안 되니까. 다만 두 가지를 구분해 두는 편이 낫다.

| | Chain of Responsibility | 파이프라인 |
|---|---|---|
| 종료 조건 | 처리한 핸들러가 나오면 중단 | 전부 통과하거나 예외로 중단 |
| 각 단계의 답 | "내가 처리할 수 있나" | "다음으로 넘겨도 되나" |
| 예 | 승인 금액대별 결재선, 예외 핸들러 탐색 | Servlet Filter, 검증 체인 |

Spring Security 의 FilterChain 도 이름과 달리 파이프라인 쪽이다. 각 필터가 `chain.doFilter()` 로 직접 다음을 부르고, 부르지 않으면 거기서 끝난다. **"다음을 부를지 각 단계가 정한다"** 는 점이 위 코드와 다른 지점이고, 그래서 인증 실패 시 뒤 필터를 실행하지 않는 제어가 가능하다. 위 구조로 그렇게 하려면 `handle` 이 boolean 을 돌려주고 호출부가 그것을 보고 멈춰야 한다.

**`setNext` 의 반환값도 함정이다.** `return next` 이므로 아래 두 줄은 다른 체인을 만든다.

```java
// 문서 방식 — 의도대로 Auth → RateLimit → Input
ValidationHandler chain = new AuthenticationHandler();
chain.setNext(new RateLimitHandler()).setNext(new InputValidationHandler());

// 한 줄로 이어 쓰면 chain 이 마지막 핸들러가 된다 → Input 만 실행
ValidationHandler chain = new AuthenticationHandler()
    .setNext(new RateLimitHandler())
    .setNext(new InputValidationHandler());
```

두 번째는 실행하면 `InputValidation` 하나만 돌고 인증이 통째로 빠진다. 예외도 안 난다. 빌더식 체이닝에 익숙할수록 아래처럼 쓰기 쉬우니, 조립은 리스트를 받아 한 곳에서 엮는 정적 메서드로 감싸 두는 편이 안전하다.

### 6. 패턴 선택 기준

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
- [Observer 패턴](Observer%20Pattern.md) — 관찰자 패턴
- [생성 패턴](Creational_Pattern.md) — 객체 생성 패턴
- [클린 아키텍처](../Clean_Architecture.md) — 아키텍처 패턴
