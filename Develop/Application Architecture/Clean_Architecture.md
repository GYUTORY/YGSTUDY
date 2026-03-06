---
title: 클린 아키텍처 가이드
tags: [architecture, clean-architecture, hexagonal, layered, ports-and-adapters, ddd, solid]
updated: 2026-03-01
---

# 클린 아키텍처 (Clean Architecture)

## 개요

클린 아키텍처는 **비즈니스 로직을 외부 기술(프레임워크, DB, UI)로부터 독립**시키는 아키텍처 원칙이다. Robert C. Martin(Uncle Bob)이 제안했으며, Hexagonal Architecture, Onion Architecture 등과 핵심 사상을 공유한다.

### 핵심 원칙

```
"의존성은 바깥에서 안쪽으로만 향한다"

┌─────────────────────────────────────────┐
│  Frameworks & Drivers (외부)            │
│  ┌──────────────────────────────────┐   │
│  │  Interface Adapters (어댑터)      │   │
│  │  ┌───────────────────────────┐   │   │
│  │  │  Application (유스케이스)   │   │   │
│  │  │  ┌────────────────────┐   │   │   │
│  │  │  │  Entity (도메인)    │   │   │   │
│  │  │  └────────────────────┘   │   │   │
│  │  └───────────────────────────┘   │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘

안쪽 레이어는 바깥쪽 레이어를 모른다.
Entity는 DB가 MySQL인지 MongoDB인지 모른다.
```

### 왜 필요한가

```
❌ 전통적 구조 (프레임워크 종속):
  Controller → Service → Repository → DB
  - Service가 JPA Entity에 직접 의존
  - DB 변경 시 Service 코드도 수정
  - 프레임워크 업그레이드 시 비즈니스 로직도 영향

✅ 클린 아키텍처:
  Controller → UseCase → Entity
                  ↓ (인터페이스)
              Repository (구현체)
  - UseCase는 Repository 인터페이스에만 의존
  - DB를 바꿔도 UseCase 코드는 변경 없음
  - 비즈니스 로직을 프레임워크 없이 단위 테스트 가능
```

## 핵심

### 1. 아키텍처 스타일 비교

| 항목 | Layered | Hexagonal | Clean | Onion |
|------|---------|-----------|-------|-------|
| **제안자** | 전통적 | Alistair Cockburn | Robert C. Martin | Jeffrey Palermo |
| **핵심 개념** | 계층 분리 | 포트 & 어댑터 | 의존성 규칙 | 도메인 중심 계층 |
| **의존 방향** | 위→아래 | 바깥→안 | 바깥→안 | 바깥→안 |
| **도메인 위치** | 중간 계층 | 중심 (Hexagon 내부) | 중심 (Entity) | 중심 (Core) |
| **외부 교체** | 어려움 | 쉬움 (어댑터 교체) | 쉬움 | 쉬움 |
| **테스트 용이성** | 보통 | 높음 | 높음 | 높음 |

### 2. Layered Architecture (전통적 계층 구조)

가장 보편적인 아키텍처. 대부분의 Spring Boot 프로젝트가 이 구조이다.

```
┌─────────────────┐
│  Presentation   │  Controller, DTO
├─────────────────┤
│   Application   │  Service (비즈니스 로직)
├─────────────────┤
│    Domain       │  Entity
├─────────────────┤
│ Infrastructure  │  Repository, 외부 API
└─────────────────┘
```

```
src/
├── controller/
│   └── OrderController.java
├── service/
│   └── OrderService.java
├── entity/
│   └── Order.java
└── repository/
    └── OrderRepository.java
```

| 장점 | 단점 |
|------|------|
| 직관적, 학습 곡선 낮음 | Service가 Repository 구현체에 직접 의존 |
| 대부분의 프로젝트에 충분 | 도메인 로직이 Service에 흩어짐 |
| 프레임워크와 자연스럽게 맞음 | 계층 건너뛰기 유혹 (Controller → Repository) |

### 3. Hexagonal Architecture (포트 & 어댑터)

비즈니스 로직(Application Core)과 외부 세계를 **포트(인터페이스)**와 **어댑터(구현체)**로 분리한다.

```
           ┌──── 인바운드 어댑터 ────┐
           │  REST Controller       │
           │  GraphQL Resolver      │
           │  CLI Command           │
           └──────────┬─────────────┘
                      │ 인바운드 포트 (UseCase 인터페이스)
              ┌───────▼───────┐
              │               │
              │  Application  │  ← 비즈니스 로직
              │     Core      │
              │               │
              └───────┬───────┘
                      │ 아웃바운드 포트 (Repository 인터페이스)
           ┌──────────▼─────────────┐
           │  아웃바운드 어댑터       │
           │  JPA Repository        │
           │  Redis Client          │
           │  External API Client   │
           └────────────────────────┘
```

#### 포트와 어댑터

| 구분 | 포트 (Port) | 어댑터 (Adapter) |
|------|------------|----------------|
| **역할** | 인터페이스 정의 | 인터페이스 구현 |
| **위치** | Application Core 내부 | 외부 |
| **인바운드** | UseCase 인터페이스 | Controller, CLI |
| **아웃바운드** | Repository 인터페이스 | JPA, MongoDB, HTTP Client |

### 4. Spring Boot에서 클린 아키텍처 적용

#### 패키지 구조

```
src/main/java/com/example/order/
├── domain/                        # Entity + 도메인 서비스
│   ├── Order.java                 # 핵심 엔티티 (순수 Java, 프레임워크 의존 없음)
│   ├── OrderItem.java
│   ├── OrderStatus.java
│   └── OrderValidator.java        # 도메인 규칙
│
├── application/                   # UseCase (유스케이스)
│   ├── port/
│   │   ├── in/                    # 인바운드 포트
│   │   │   ├── CreateOrderUseCase.java
│   │   │   └── GetOrderUseCase.java
│   │   └── out/                   # 아웃바운드 포트
│   │       ├── OrderRepository.java
│   │       └── PaymentGateway.java
│   ├── service/
│   │   └── OrderService.java      # UseCase 구현
│   └── dto/
│       ├── CreateOrderCommand.java
│       └── OrderResult.java
│
└── adapter/                       # 어댑터 (인프라)
    ├── in/                        # 인바운드 어댑터
    │   └── web/
    │       ├── OrderController.java
    │       └── OrderRequest.java
    └── out/                       # 아웃바운드 어댑터
        ├── persistence/
        │   ├── OrderJpaEntity.java
        │   ├── OrderJpaRepository.java
        │   └── OrderPersistenceAdapter.java
        └── external/
            └── PaymentApiAdapter.java
```

#### 도메인 레이어 (Entity)

```java
// 순수 Java 객체. Spring, JPA 어노테이션 없음.
public class Order {
    private Long id;
    private Long userId;
    private List<OrderItem> items;
    private OrderStatus status;
    private Money totalPrice;

    // 비즈니스 규칙이 도메인 안에 있다
    public void place() {
        if (items.isEmpty()) {
            throw new IllegalStateException("주문 항목이 비어있습니다");
        }
        if (totalPrice.isLessThan(Money.of(1000))) {
            throw new IllegalStateException("최소 주문 금액은 1,000원입니다");
        }
        this.status = OrderStatus.PLACED;
    }

    public void cancel() {
        if (status != OrderStatus.PLACED) {
            throw new IllegalStateException("배송 시작 후에는 취소할 수 없습니다");
        }
        this.status = OrderStatus.CANCELLED;
    }

    public Money calculateTotal() {
        return items.stream()
            .map(OrderItem::getSubtotal)
            .reduce(Money.ZERO, Money::add);
    }
}
```

#### 포트 (인터페이스)

```java
// 인바운드 포트: 외부에서 Application Core를 호출할 때 사용
public interface CreateOrderUseCase {
    OrderResult createOrder(CreateOrderCommand command);
}

public interface GetOrderUseCase {
    OrderResult getOrder(Long orderId);
}

// 아웃바운드 포트: Application Core가 외부 인프라를 사용할 때
public interface OrderRepository {
    Order save(Order order);
    Optional<Order> findById(Long id);
}

public interface PaymentGateway {
    PaymentResult processPayment(Long orderId, Money amount);
}
```

#### UseCase 구현 (Application Service)

```java
@Service
@Transactional
public class OrderService implements CreateOrderUseCase, GetOrderUseCase {

    private final OrderRepository orderRepository;   // 아웃바운드 포트 (인터페이스)
    private final PaymentGateway paymentGateway;

    public OrderService(OrderRepository orderRepository, PaymentGateway paymentGateway) {
        this.orderRepository = orderRepository;
        this.paymentGateway = paymentGateway;
    }

    @Override
    public OrderResult createOrder(CreateOrderCommand command) {
        // 도메인 객체 생성
        Order order = Order.builder()
            .userId(command.getUserId())
            .items(command.toOrderItems())
            .build();

        // 도메인 규칙 실행 (비즈니스 로직은 Entity 안에)
        order.place();

        // 결제 처리 (아웃바운드 포트 사용)
        paymentGateway.processPayment(order.getId(), order.getTotalPrice());

        // 저장 (아웃바운드 포트 사용)
        Order saved = orderRepository.save(order);
        return OrderResult.from(saved);
    }
}
```

#### 어댑터 (구현체)

```java
// 인바운드 어댑터: REST Controller
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final CreateOrderUseCase createOrderUseCase;  // 인바운드 포트
    private final GetOrderUseCase getOrderUseCase;

    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@RequestBody OrderRequest request) {
        CreateOrderCommand command = request.toCommand();
        OrderResult result = createOrderUseCase.createOrder(command);
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(OrderResponse.from(result));
    }
}

// 아웃바운드 어댑터: JPA 구현
@Component
public class OrderPersistenceAdapter implements OrderRepository {

    private final OrderJpaRepository jpaRepository;

    @Override
    public Order save(Order order) {
        OrderJpaEntity entity = OrderJpaEntity.from(order);  // 도메인 → JPA 변환
        OrderJpaEntity saved = jpaRepository.save(entity);
        return saved.toDomain();  // JPA → 도메인 변환
    }

    @Override
    public Optional<Order> findById(Long id) {
        return jpaRepository.findById(id)
            .map(OrderJpaEntity::toDomain);
    }
}

// 아웃바운드 어댑터: 외부 결제 API
@Component
public class PaymentApiAdapter implements PaymentGateway {

    private final RestTemplate restTemplate;

    @Override
    public PaymentResult processPayment(Long orderId, Money amount) {
        PaymentApiRequest request = new PaymentApiRequest(orderId, amount.getValue());
        PaymentApiResponse response = restTemplate.postForObject(
            "https://payment-api.example.com/pay", request, PaymentApiResponse.class
        );
        return PaymentResult.from(response);
    }
}
```

### 5. 도메인 모델 매핑 전략

클린 아키텍처에서는 도메인 엔티티와 JPA 엔티티를 분리한다.

```
Controller ←→ Request/Response DTO
    ↕
UseCase ←→ Command/Result DTO
    ↕
Domain Entity (순수 Java)
    ↕ (매핑)
JPA Entity (@Entity, @Table)
    ↕
Database
```

| 전략 | 설명 | 적합한 경우 |
|------|------|-----------|
| **No Mapping** | 도메인 = JPA 엔티티 (같은 클래스) | 소규모 프로젝트, CRUD 위주 |
| **Two-Way Mapping** | 도메인 ↔ JPA 양방향 변환 | 클린 아키텍처 적용 시 |
| **Full Mapping** | 각 레이어마다 별도 모델 | 대규모 엔터프라이즈 |

```
소규모 프로젝트 → No Mapping (Layered Architecture로 충분)
중규모 프로젝트 → Two-Way Mapping (도메인/JPA 분리)
대규모 프로젝트 → Full Mapping (모든 레이어 분리)
```

### 6. 테스트 전략

클린 아키텍처의 가장 큰 장점: **도메인 로직을 프레임워크 없이 테스트** 가능.

```java
// 도메인 단위 테스트 (Spring 컨텍스트 불필요, 매우 빠름)
class OrderTest {
    @Test
    void 최소_주문금액_미만이면_주문_실패() {
        Order order = Order.builder()
            .items(List.of(new OrderItem("상품A", 500, 1)))
            .build();

        assertThatThrownBy(order::place)
            .isInstanceOf(IllegalStateException.class)
            .hasMessage("최소 주문 금액은 1,000원입니다");
    }
}

// UseCase 테스트 (Mock으로 포트 대체)
class OrderServiceTest {
    @Test
    void 주문_생성_성공() {
        OrderRepository mockRepo = mock(OrderRepository.class);
        PaymentGateway mockPayment = mock(PaymentGateway.class);
        OrderService service = new OrderService(mockRepo, mockPayment);

        when(mockRepo.save(any())).thenReturn(testOrder());
        when(mockPayment.processPayment(any(), any())).thenReturn(PaymentResult.success());

        OrderResult result = service.createOrder(testCommand());
        assertThat(result.getStatus()).isEqualTo("PLACED");
    }
}
```

### 7. 언제 어떤 아키텍처를 쓸까

```
프로젝트 규모에 따른 선택:

소규모 (CRUD 위주, 1~3명)
  → Layered Architecture
  → 단순하고 빠르게 개발

중규모 (비즈니스 로직 복잡, 3~10명)
  → Hexagonal / Clean Architecture
  → 도메인과 인프라 분리

대규모 (MSA, 도메인 복잡, 10명+)
  → Clean Architecture + DDD
  → 바운디드 컨텍스트별 독립 아키텍처
```

| 신호 | 추천 |
|------|------|
| JPA 엔티티에 비즈니스 로직이 없다 | Layered 유지 |
| Service 클래스가 500줄 이상이다 | 도메인 모델 분리 검토 |
| DB를 바꿀 가능성이 있다 | Hexagonal 고려 |
| 외부 API 연동이 많다 | 포트 & 어댑터 적용 |
| 테스트 커버리지를 높이고 싶다 | 클린 아키텍처 적용 |

## 참고

- [Clean Architecture — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture — Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [DDD (Domain-Driven Design)](DDD.md) — 도메인 주도 설계
- [Design Pattern](Design Pattern/Creational_Pattern.md) — 생성 패턴
- [Spring Boot](../Framework/Java/Spring/Bean.md) — Spring 프레임워크
