---
title: 상태 머신 (State Machine)
tags: [architecture, design-pattern, state-machine, fsm, spring-state-machine, behavioral]
updated: 2026-08-03
---

# 상태 머신 (State Machine)

## 개념

상태 머신은 시스템이 가질 수 있는 상태와 상태 간 전이 규칙을 명시적으로 정의한 모델이다. 주문, 결제, 배송 같은 도메인에서 "지금 이 객체가 어떤 상태인가"와 "이 상태에서 어떤 동작이 허용되는가"를 코드로 표현하는 방법이다.

if-else나 switch로 상태 전이를 처리하다 보면 조건이 쌓여가면서 어느 순간부터 상태 변경 하나 추가하는 게 두려워진다. 상태 머신은 이 문제를 구조적으로 푼다.

## FSM의 구성 요소

**상태(State)**: 시스템이 머무를 수 있는 특정 시점의 상황. 주문 도메인에서는 `PENDING`, `PAID`, `SHIPPED`, `DELIVERED`, `CANCELLED` 같은 것들이다.

**이벤트(Event)**: 상태 전이를 일으키는 트리거. `PAY`, `SHIP`, `DELIVER`, `CANCEL` 처럼 외부에서 들어오는 신호다.

**전이(Transition)**: 특정 상태에서 특정 이벤트가 발생했을 때 이동하는 다음 상태. `PENDING --PAY--> PAID` 같은 규칙이다.

**액션(Action)**: 전이가 발생할 때 실행되는 부수 효과. 결제 완료 시 이메일 발송, 재고 차감 같은 것들이다.

**가드(Guard)**: 전이가 발생하기 전에 검사하는 조건. 재고가 있을 때만 SHIP 이벤트를 허용하는 식이다.

**초기 상태(Initial State)**: 시스템이 시작할 때의 상태. 보통 하나지만 계층적 상태 머신에서는 복수일 수 있다.

```
전이 규칙 표현:
source state + event [guard] / action -> target state
```

## Enum 기반 전이 테이블 구현

가장 단순한 방식이다. 전이 규칙을 Enum과 Map으로 명시적으로 선언한다.

```java
public enum OrderState {
    PENDING, PAID, SHIPPED, DELIVERED, CANCELLED
}

public enum OrderEvent {
    PAY, SHIP, DELIVER, CANCEL
}
```

전이 테이블을 Map으로 구성한다.

```java
public class OrderStateMachine {
    
    // (현재상태, 이벤트) -> 다음상태
    private static final Map<OrderState, Map<OrderEvent, OrderState>> TRANSITIONS =
        Map.of(
            OrderState.PENDING, Map.of(
                OrderEvent.PAY,    OrderState.PAID,
                OrderEvent.CANCEL, OrderState.CANCELLED
            ),
            OrderState.PAID, Map.of(
                OrderEvent.SHIP,   OrderState.SHIPPED,
                OrderEvent.CANCEL, OrderState.CANCELLED
            ),
            OrderState.SHIPPED, Map.of(
                OrderEvent.DELIVER, OrderState.DELIVERED
            )
        );
    
    private OrderState currentState;
    
    public OrderStateMachine(OrderState initialState) {
        this.currentState = initialState;
    }
    
    public OrderState transition(OrderEvent event) {
        Map<OrderEvent, OrderState> stateTransitions = TRANSITIONS.get(currentState);
        if (stateTransitions == null || !stateTransitions.containsKey(event)) {
            throw new InvalidTransitionException(
                String.format("Cannot apply %s in state %s", event, currentState)
            );
        }
        OrderState nextState = stateTransitions.get(event);
        currentState = nextState;
        return currentState;
    }
    
    public OrderState getState() {
        return currentState;
    }
}
```

전이 테이블 방식의 장점은 가능한 전이 경로가 코드 한 곳에 모여 있다는 것이다. 규칙이 어디서 어디로 가는지 파악하기 쉽고, 허용되지 않은 전이는 자동으로 예외가 난다.

단점도 있다. 전이마다 액션을 추가하거나 가드 조건을 붙이려면 Map 구조가 복잡해진다. 그 한계에서 State 패턴이 나온다.

## State 패턴 기반 구현

State 패턴은 각 상태를 별도 클래스로 분리한다. 상태별로 허용되는 이벤트와 액션을 그 클래스 안에서 처리한다.

```java
public interface OrderState {
    OrderState pay(Order order);
    OrderState ship(Order order);
    OrderState deliver(Order order);
    OrderState cancel(Order order);
}
```

각 상태 구현체에서 허용되지 않는 이벤트는 예외를 던진다.

```java
public class PendingState implements OrderState {

    @Override
    public OrderState pay(Order order) {
        order.recordPayment();
        order.notifyPaymentComplete();
        return new PaidState();
    }

    @Override
    public OrderState ship(Order order) {
        throw new InvalidTransitionException("PENDING 상태에서는 배송할 수 없습니다.");
    }

    @Override
    public OrderState deliver(Order order) {
        throw new InvalidTransitionException("PENDING 상태에서는 배달 완료할 수 없습니다.");
    }

    @Override
    public OrderState cancel(Order order) {
        order.refundIfPaid();
        return new CancelledState();
    }
}

public class PaidState implements OrderState {

    @Override
    public OrderState pay(Order order) {
        throw new InvalidTransitionException("이미 결제된 주문입니다.");
    }

    @Override
    public OrderState ship(Order order) {
        if (!order.hasStock()) {
            throw new InsufficientStockException("재고가 부족합니다.");
        }
        order.decreaseStock();
        order.assignTrackingNumber();
        return new ShippedState();
    }

    @Override
    public OrderState deliver(Order order) {
        throw new InvalidTransitionException("배송 중이 아닌 주문은 배달 완료할 수 없습니다.");
    }

    @Override
    public OrderState cancel(Order order) {
        order.refund();
        return new CancelledState();
    }
}
```

Order 객체는 현재 상태를 위임해서 처리한다.

```java
public class Order {
    private OrderState state;
    private String trackingNumber;
    
    public Order() {
        this.state = new PendingState();
    }
    
    public void pay() {
        this.state = state.pay(this);
    }
    
    public void ship() {
        this.state = state.ship(this);
    }
    
    public String getStateName() {
        return state.getClass().getSimpleName();
    }
    
    // 도메인 로직들
    public void recordPayment() { /* ... */ }
    public void notifyPaymentComplete() { /* ... */ }
    public boolean hasStock() { /* ... */ return true; }
    public void decreaseStock() { /* ... */ }
    public void assignTrackingNumber() { this.trackingNumber = UUID.randomUUID().toString(); }
    public void refund() { /* ... */ }
    public void refundIfPaid() { /* ... */ }
}
```

### 전이 테이블 vs State 패턴 비교

전이 테이블 방식은 규칙이 단순하고 상태 수가 적을 때 좋다. 전이 경로를 한눈에 파악하기 쉽다.

State 패턴은 각 상태의 액션이 복잡하거나 가드 조건이 상태마다 다를 때 적합하다. 상태가 늘어날 때 기존 코드를 건드리지 않고 새 클래스만 추가하면 된다. 하지만 상태 클래스가 많아지면 파일이 흩어져서 전체 흐름 파악이 어렵다.

실무에서는 초반에 전이 테이블로 시작하다가 복잡도가 올라가면 State 패턴으로 리팩터링하는 경우가 많다.

## Spring State Machine

Spring State Machine은 FSM을 프레임워크 수준에서 지원한다. Guard, Action, Persist를 별도 빈으로 관리할 수 있어서 Spring 환경에서는 꽤 유용하다.

의존성 추가:

```gradle
implementation 'org.springframework.statemachine:spring-statemachine-core:3.2.1'
```

상태와 이벤트 Enum을 정의하고 Configuration으로 전이 규칙을 선언한다.

```java
@Configuration
@EnableStateMachine
public class OrderStateMachineConfig
        extends StateMachineConfigurerAdapter<OrderState, OrderEvent> {

    @Override
    public void configure(StateMachineStateConfigurer<OrderState, OrderEvent> states)
            throws Exception {
        states
            .withStates()
            .initial(OrderState.PENDING)
            .states(EnumSet.allOf(OrderState.class));
    }

    @Override
    public void configure(StateMachineTransitionConfigurer<OrderState, OrderEvent> transitions)
            throws Exception {
        transitions
            .withExternal()
                .source(OrderState.PENDING).target(OrderState.PAID)
                .event(OrderEvent.PAY)
                .guard(paymentGuard())
                .action(paymentAction())
            .and()
            .withExternal()
                .source(OrderState.PAID).target(OrderState.SHIPPED)
                .event(OrderEvent.SHIP)
                .guard(stockGuard())
                .action(shipAction())
            .and()
            .withExternal()
                .source(OrderState.SHIPPED).target(OrderState.DELIVERED)
                .event(OrderEvent.DELIVER)
                .action(deliverAction())
            .and()
            .withExternal()
                .source(OrderState.PENDING).target(OrderState.CANCELLED)
                .event(OrderEvent.CANCEL)
            .and()
            .withExternal()
                .source(OrderState.PAID).target(OrderState.CANCELLED)
                .event(OrderEvent.CANCEL)
                .action(refundAction());
    }

    @Bean
    public Guard<OrderState, OrderEvent> paymentGuard() {
        return context -> {
            Order order = (Order) context.getMessageHeader("order");
            return order != null && order.getAmount() > 0;
        };
    }

    @Bean
    public Guard<OrderState, OrderEvent> stockGuard() {
        return context -> {
            Order order = (Order) context.getMessageHeader("order");
            return order != null && order.hasStock();
        };
    }

    @Bean
    public Action<OrderState, OrderEvent> paymentAction() {
        return context -> {
            Order order = (Order) context.getMessageHeader("order");
            order.recordPayment();
            // 이메일 발송, 이벤트 발행 등
        };
    }

    @Bean
    public Action<OrderState, OrderEvent> shipAction() {
        return context -> {
            Order order = (Order) context.getMessageHeader("order");
            order.decreaseStock();
            order.assignTrackingNumber();
        };
    }

    @Bean
    public Action<OrderState, OrderEvent> deliverAction() {
        return context -> {
            Order order = (Order) context.getMessageHeader("order");
            order.markDelivered();
        };
    }

    @Bean
    public Action<OrderState, OrderEvent> refundAction() {
        return context -> {
            Order order = (Order) context.getMessageHeader("order");
            order.refund();
        };
    }
}
```

이벤트 발행은 `stateMachine.sendEvent()`로 한다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    
    private final StateMachine<OrderState, OrderEvent> stateMachine;
    
    public void payOrder(Order order) {
        Message<OrderEvent> message = MessageBuilder
            .withPayload(OrderEvent.PAY)
            .setHeader("order", order)
            .build();
        
        boolean accepted = stateMachine.sendEvent(message);
        if (!accepted) {
            throw new InvalidTransitionException("결제 처리를 할 수 없는 상태입니다: " + stateMachine.getState().getId());
        }
    }
}
```

### Guard와 Action 사용 시 주의사항

Guard가 false를 반환해도 예외가 아니라 단순히 전이가 거부된다. `sendEvent()`가 false를 반환하는 것으로 확인해야 한다. Guard 실패와 Invalid Transition을 애플리케이션에서 구분해서 처리해야 클라이언트에게 적절한 에러 메시지를 줄 수 있다.

Action 안에서 예외가 발생하면 Spring State Machine은 기본적으로 상태 전이를 롤백하지 않는다. Action이 실패했는데 상태는 이미 바뀐 상황이 생길 수 있다. Action 안에서 예외 처리를 직접 해주거나, `StateMachineListener`로 에러를 감지해야 한다.

### 상태 영속성 (Persist)

Spring State Machine의 StateMachine 빈은 기본적으로 인메모리다. 서버를 재시작하거나 여러 인스턴스로 분산 처리할 때 상태가 날아간다. DB에 저장하고 복원하는 방법이 필요하다.

`StateMachinePersist` 인터페이스를 구현해서 상태를 저장한다.

```java
@Component
@RequiredArgsConstructor
public class OrderStateMachinePersist
        implements StateMachinePersist<OrderState, OrderEvent, String> {
    
    private final OrderRepository orderRepository;
    private final StateMachineSerializer<OrderState, OrderEvent> serializer;
    
    @Override
    public void write(StateMachineContext<OrderState, OrderEvent> context, String orderId) {
        Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new OrderNotFoundException(orderId));
        order.setMachineState(context.getState().name());
        orderRepository.save(order);
    }
    
    @Override
    public StateMachineContext<OrderState, OrderEvent> read(String orderId) {
        Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new OrderNotFoundException(orderId));
        OrderState state = OrderState.valueOf(order.getMachineState());
        return new DefaultStateMachineContext<>(state, null, null, null);
    }
}
```

요청마다 StateMachine을 DB에서 복원해서 사용한다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    
    private final StateMachineFactory<OrderState, OrderEvent> factory;
    private final StateMachinePersister<OrderState, OrderEvent, String> persister;
    
    public void payOrder(String orderId, Order order) throws Exception {
        StateMachine<OrderState, OrderEvent> sm = factory.getStateMachine(orderId);
        persister.restore(sm, orderId);  // DB에서 상태 복원
        
        sm.start();
        boolean accepted = sm.sendEvent(MessageBuilder
            .withPayload(OrderEvent.PAY)
            .setHeader("order", order)
            .build());
        
        if (!accepted) {
            throw new InvalidTransitionException("결제할 수 없는 상태입니다.");
        }
        
        persister.persist(sm, orderId);  // 변경된 상태를 DB에 저장
        sm.stop();
    }
}
```

StateMachine 인스턴스를 재사용하면 상태가 꼬인다. 요청마다 새로 만들고 복원하고 저장하는 패턴을 유지해야 한다.

## 계층적 상태 머신 (Hierarchical State Machine)

상태 수가 늘어나면 공통 동작을 반복 정의하게 된다. 계층적 상태 머신은 상위 상태(super state)를 두고 하위 상태들이 공통 전이를 상속받는 구조다.

예를 들어 `ACTIVE`라는 상위 상태 아래 `PENDING`, `PAID`, `SHIPPED`가 있으면, `CANCEL` 이벤트는 `ACTIVE` 상태 수준에서 한 번만 정의하면 하위 상태 모두에 적용된다.

```java
@Override
public void configure(StateMachineStateConfigurer<OrderState, OrderEvent> states)
        throws Exception {
    states
        .withStates()
        .initial(OrderState.PENDING)
        .state(OrderState.ACTIVE)    // 상위 상태
        .end(OrderState.DELIVERED)
        .end(OrderState.CANCELLED)
        .and()
        .withStates()
        .parent(OrderState.ACTIVE)   // ACTIVE의 하위 상태들
        .initial(OrderState.PENDING)
        .states(EnumSet.of(
            OrderState.PENDING,
            OrderState.PAID,
            OrderState.SHIPPED
        ));
}

@Override
public void configure(StateMachineTransitionConfigurer<OrderState, OrderEvent> transitions)
        throws Exception {
    transitions
        // ACTIVE 상위 상태에서 CANCEL 이벤트 -> 모든 하위 상태에 적용
        .withExternal()
            .source(OrderState.ACTIVE).target(OrderState.CANCELLED)
            .event(OrderEvent.CANCEL)
            .action(cancelAction())
        .and()
        // 하위 상태 전이들
        .withExternal()
            .source(OrderState.PENDING).target(OrderState.PAID)
            .event(OrderEvent.PAY)
        .and()
        .withExternal()
            .source(OrderState.PAID).target(OrderState.SHIPPED)
            .event(OrderEvent.SHIP)
        .and()
        .withExternal()
            .source(OrderState.SHIPPED).target(OrderState.DELIVERED)
            .event(OrderEvent.DELIVER);
}
```

계층 구조가 깊어지면 상태 머신 설정 자체가 복잡해진다. 3단계 이상 중첩은 거의 대부분 실수다.

## 실무에서 자주 겪는 함정

### Invalid Transition 처리

허용되지 않은 전이가 발생했을 때 예외를 던지는 것은 당연하다. 문제는 그 예외를 어디서 잡고 어떻게 처리하느냐다.

클라이언트가 "이미 취소된 주문에 결제를 시도"했을 때, 500 에러가 아니라 409 Conflict로 돌려줘야 한다. 상태 머신 예외를 그대로 올리면 글로벌 예외 핸들러에서 500으로 처리될 수 있다.

```java
public class InvalidTransitionException extends RuntimeException {
    private final OrderState currentState;
    private final OrderEvent event;
    
    public InvalidTransitionException(OrderState currentState, OrderEvent event) {
        super(String.format("'%s' 상태에서 '%s' 이벤트를 처리할 수 없습니다.", currentState, event));
        this.currentState = currentState;
        this.event = event;
    }
}

@ExceptionHandler(InvalidTransitionException.class)
public ResponseEntity<ErrorResponse> handleInvalidTransition(InvalidTransitionException e) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(new ErrorResponse(e.getMessage()));
}
```

### 동시성 문제

두 요청이 동시에 같은 주문의 상태를 바꾸려 할 때 문제가 생긴다. 낙관적 락이 없으면 둘 다 `PENDING` 상태를 읽고 둘 다 `PAID`로 바꿔 저장한다.

DB 레벨에서 낙관적 락을 걸어야 한다.

```java
@Entity
public class Order {
    @Id
    private String id;
    
    @Enumerated(EnumType.STRING)
    private OrderState state;
    
    @Version  // 낙관적 락
    private Long version;
}
```

충돌이 나면 `OptimisticLockingFailureException`이 발생한다. 재시도 로직이 필요한지 아니면 그냥 실패로 처리할지는 비즈니스 요구사항에 따라 다르다. 결제처럼 중복 처리되면 안 되는 경우는 재시도 없이 실패로 처리하는 편이 안전하다.

Spring State Machine 자체는 thread-safe하지 않다. 요청마다 StateMachine 인스턴스를 새로 생성하거나 `@Scope("prototype")`으로 관리해야 한다.

### 상태 폭발

상태 머신을 도입하면서 "이 경우도 상태로 표현하자"는 유혹이 생긴다. 결국 상태가 20개, 이벤트가 15개가 되고 전이 규칙이 수백 개가 되면 상태 머신 자체가 관리 불가능해진다.

상태 폭발이 느껴질 때 점검할 것들:

상태를 두 개 이상의 Enum으로 분리할 수 있는지 본다. 주문 상태와 결제 상태, 배송 상태를 하나의 Enum에 담으려다 폭발하는 경우가 많다. 도메인을 분리하면 각각의 상태 머신이 훨씬 단순해진다.

특정 상태가 다른 상태와 전이 관계가 전혀 없다면, 그것은 상태가 아니라 별도 엔티티일 가능성이 높다.

### DB 저장 시 상태 불일치

Action에서 예외가 났는데 상태는 이미 변경된 경우, DB에는 새 상태가 저장되고 실제 액션(이메일 발송, 재고 차감 등)은 실패한 상태가 된다.

상태 전이와 액션을 하나의 트랜잭션으로 묶어야 한다. Spring State Machine의 Action은 트랜잭션을 자동으로 관리하지 않는다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    
    @Transactional
    public void payOrder(String orderId, Order order) throws Exception {
        StateMachine<OrderState, OrderEvent> sm = factory.getStateMachine(orderId);
        persister.restore(sm, orderId);
        sm.start();
        
        boolean accepted = sm.sendEvent(MessageBuilder
            .withPayload(OrderEvent.PAY)
            .setHeader("order", order)
            .build());
        
        if (!accepted) {
            throw new InvalidTransitionException(sm.getState().getId(), OrderEvent.PAY);
        }
        
        // 여기서 예외 나면 persist도 롤백됨
        persister.persist(sm, orderId);
        sm.stop();
    }
}
```

액션 안에서 외부 API를 호출하거나 메시지 큐에 발행하는 경우는 트랜잭션 범위 밖이다. 이 경우 상태 저장 성공 후 실패한 액션을 재처리할 방법(아웃박스 패턴, 이벤트 발행 후 소비자 재시도 등)을 따로 마련해야 한다.
