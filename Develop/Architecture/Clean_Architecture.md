---
title: 클린 아키텍처
tags: [architecture, clean-architecture, hexagonal, layered, ports-and-adapters, ddd, solid]
updated: 2026-03-25
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
전통적 구조 (프레임워크 종속):
  Controller → Service → Repository → DB
  - Service가 JPA Entity에 직접 의존
  - DB 변경 시 Service 코드도 수정
  - 프레임워크 업그레이드 시 비즈니스 로직도 영향

클린 아키텍처:
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
                      │아웃바운드 포트 (Repository 인터페이스)
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

### 5. NestJS에서 클린 아키텍처 적용

Node.js/NestJS 프로젝트에서도 같은 원칙을 적용한다. TypeScript의 인터페이스와 NestJS의 DI 컨테이너를 활용한다.

#### 패키지 구조

```
src/order/
├── domain/
│   ├── order.entity.ts            # 순수 TypeScript 클래스
│   ├── order-item.value-object.ts
│   └── order.repository.ts        # 아웃바운드 포트 (추상 클래스)
│
├── application/
│   ├── create-order.use-case.ts   # 유스케이스
│   ├── get-order.use-case.ts
│   └── dto/
│       ├── create-order.command.ts
│       └── order.result.ts
│
├── adapter/
│   ├── in/
│   │   └── order.controller.ts    # 인바운드 어댑터
│   └── out/
│       ├── order.typeorm.entity.ts # TypeORM 엔티티 (DB 매핑용)
│       └── order.repository.impl.ts # 아웃바운드 어댑터
│
└── order.module.ts
```

#### 도메인 레이어

```typescript
// domain/order.entity.ts
// 순수 TypeScript. NestJS, TypeORM 의존 없음.
export class Order {
  constructor(
    private readonly id: string | null,
    private readonly userId: string,
    private items: OrderItem[],
    private status: OrderStatus,
  ) {}

  place(): void {
    if (this.items.length === 0) {
      throw new Error('주문 항목이 비어있다');
    }
    const total = this.calculateTotal();
    if (total < 1000) {
      throw new Error('최소 주문 금액은 1,000원이다');
    }
    this.status = OrderStatus.PLACED;
  }

  cancel(): void {
    if (this.status !== OrderStatus.PLACED) {
      throw new Error('배송 시작 후에는 취소할 수 없다');
    }
    this.status = OrderStatus.CANCELLED;
  }

  calculateTotal(): number {
    return this.items.reduce((sum, item) => sum + item.subtotal(), 0);
  }

  // getter
  getId(): string | null { return this.id; }
  getStatus(): OrderStatus { return this.status; }
  getItems(): OrderItem[] { return [...this.items]; }
}
```

#### 포트 (아웃바운드)

```typescript
// domain/order.repository.ts
// NestJS에서는 인터페이스 대신 추상 클래스를 쓴다.
// TypeScript 인터페이스는 런타임에 사라지기 때문에 DI 토큰으로 쓸 수 없다.
export abstract class OrderRepository {
  abstract save(order: Order): Promise<Order>;
  abstract findById(id: string): Promise<Order | null>;
}
```

#### UseCase 구현

```typescript
// application/create-order.use-case.ts
import { Injectable } from '@nestjs/common';
import { OrderRepository } from '../domain/order.repository';

@Injectable()
export class CreateOrderUseCase {
  constructor(private readonly orderRepository: OrderRepository) {}

  async execute(command: CreateOrderCommand): Promise<OrderResult> {
    const order = new Order(
      null,
      command.userId,
      command.items.map(i => new OrderItem(i.productId, i.price, i.quantity)),
      OrderStatus.DRAFT,
    );

    order.place();

    const saved = await this.orderRepository.save(order);
    return OrderResult.from(saved);
  }
}
```

#### 어댑터 (구현체)

```typescript
// adapter/out/order.repository.impl.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OrderRepository } from '../../domain/order.repository';
import { OrderTypeormEntity } from './order.typeorm.entity';

@Injectable()
export class OrderRepositoryImpl extends OrderRepository {
  constructor(
    @InjectRepository(OrderTypeormEntity)
    private readonly ormRepo: Repository<OrderTypeormEntity>,
  ) {
    super();
  }

  async save(order: Order): Promise<Order> {
    const entity = OrderTypeormEntity.fromDomain(order);
    const saved = await this.ormRepo.save(entity);
    return saved.toDomain();
  }

  async findById(id: string): Promise<Order | null> {
    const entity = await this.ormRepo.findOne({ where: { id } });
    return entity ? entity.toDomain() : null;
  }
}
```

#### 모듈 등록 (DI 바인딩)

```typescript
// order.module.ts
@Module({
  imports: [TypeOrmModule.forFeature([OrderTypeormEntity])],
  controllers: [OrderController],
  providers: [
    CreateOrderUseCase,
    GetOrderUseCase,
    {
      provide: OrderRepository,       // 추상 클래스를 토큰으로
      useClass: OrderRepositoryImpl,  // 구현체를 바인딩
    },
  ],
})
export class OrderModule {}
```

NestJS에서 주의할 점은 TypeScript 인터페이스를 DI 토큰으로 쓸 수 없다는 것이다. 런타임에 인터페이스가 존재하지 않기 때문이다. 추상 클래스를 쓰거나, 문자열/Symbol 토큰을 `@Inject()` 데코레이터와 함께 써야 한다.

### 6. 도메인 모델 매핑

클린 아키텍처에서는 도메인 엔티티와 영속성 엔티티를 분리한다.

```
Controller ←→ Request/Response DTO
    ↕
UseCase ←→ Command/Result DTO
    ↕
Domain Entity (순수 객체)
    ↕ (매핑)
JPA/TypeORM Entity (@Entity, @Table)
    ↕
Database
```

| 방식 | 설명 | 적합한 경우 |
|------|------|-----------|
| **No Mapping** | 도메인 = 영속성 엔티티 (같은 클래스) | 소규모 프로젝트, CRUD 위주 |
| **Two-Way Mapping** | 도메인 ↔ 영속성 양방향 변환 | 클린 아키텍처 적용 시 |
| **Full Mapping** | 각 레이어마다 별도 모델 | 대규모 엔터프라이즈 |

### 7. 테스트

클린 아키텍처의 가장 큰 장점은 도메인 로직을 프레임워크 없이 테스트할 수 있다는 것이다.

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

### 8. 언제 어떤 아키텍처를 쓸까

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

## 실무에서 자주 겪는 문제

### 매핑 보일러플레이트 폭증

도메인 엔티티와 영속성 엔티티를 분리하면 `toDomain()`, `fromDomain()` 같은 매핑 코드가 쏟아진다. 엔티티에 필드가 20개면 매핑 메서드도 20줄씩 늘어난다. 연관 엔티티가 3~4개 물려있으면 매핑 코드만으로 파일 하나가 채워지는 경우가 있다.

**실제로 일어나는 일:**

```java
// OrderJpaEntity.java — 이런 매핑이 엔티티마다 필요하다
public Order toDomain() {
    return Order.builder()
        .id(this.id)
        .userId(this.userId)
        .status(OrderStatus.valueOf(this.status))
        .items(this.items.stream()
            .map(OrderItemJpaEntity::toDomain)  // 자식 엔티티도 매핑
            .collect(Collectors.toList()))
        .totalPrice(Money.of(this.totalPrice))
        .createdAt(this.createdAt)
        .updatedAt(this.updatedAt)
        .build();
}

public static OrderJpaEntity from(Order order) {
    OrderJpaEntity entity = new OrderJpaEntity();
    entity.id = order.getId();
    entity.userId = order.getUserId();
    entity.status = order.getStatus().name();
    entity.items = order.getItems().stream()
        .map(OrderItemJpaEntity::from)          // 자식 엔티티도 매핑
        .collect(Collectors.toList());
    entity.totalPrice = order.getTotalPrice().getValue();
    entity.createdAt = order.getCreatedAt();
    entity.updatedAt = order.getUpdatedAt();
    return entity;
}
```

**대처 방법:**

- MapStruct 같은 매핑 라이브러리를 쓰면 필드명이 같은 경우 자동 매핑된다. 다만 커스텀 변환 규칙이 많아지면 MapStruct 설정 자체가 복잡해진다.
- 프로젝트 초기에는 No Mapping(도메인 = 영속성 엔티티)으로 시작하고, 도메인 로직이 복잡해지는 시점에 분리하는 게 현실적이다.
- 모든 엔티티를 분리하지 말고, 비즈니스 규칙이 복잡한 애그리거트만 분리한다. 단순 CRUD 엔티티까지 분리하면 매핑 코드만 늘어나고 얻는 게 없다.

### 과도한 추상화로 디버깅이 어렵다

인터페이스 → 구현체 → 어댑터 → 도메인 변환 경로가 길어지면, 에러가 터졌을 때 콜스택을 따라가기가 힘들다. IDE에서 "Go to Implementation"을 3~4번 눌러야 실제 코드에 도달하는 경우가 생긴다.

**자주 발생하는 상황:**

```
NullPointerException at OrderPersistenceAdapter.save()
  → OrderJpaEntity.from() 에서 매핑 누락
    → 도메인 Order에 새 필드를 추가했는데 JPA 매핑을 안 고침
```

도메인 엔티티에 필드를 하나 추가하면 수정해야 할 곳이 많다:
1. Domain Entity — 필드 추가
2. JPA Entity — 컬럼 추가
3. 매핑 코드 — toDomain(), fromDomain() 둘 다
4. Command/Result DTO — 필요하면 추가
5. Request/Response DTO — 필요하면 추가

**대처 방법:**

- 매핑 코드에 대한 테스트를 반드시 작성한다. 필드가 추가됐을 때 매핑 누락을 잡아주는 테스트가 없으면 런타임에 터진다.
- 아키텍처 계층을 4단계까지 나누지 말고, 프로젝트 규모에 맞게 2~3단계로 줄이는 것도 방법이다.

### 트랜잭션 경계 처리

클린 아키텍처에서 트랜잭션은 어디에 둬야 하는가? 도메인 레이어는 DB를 모르니까 `@Transactional`을 달 수 없다. UseCase(Application Service)에 다는 게 일반적인데, 여러 아웃바운드 포트를 걸쳐야 하는 경우 문제가 생긴다.

**자주 발생하는 상황:**

```java
@Service
@Transactional
public class TransferMoneyService implements TransferMoneyUseCase {

    private final AccountRepository accountRepository;
    private final NotificationPort notificationPort;  // 외부 알림 서비스

    @Override
    public void transfer(TransferCommand command) {
        Account from = accountRepository.findById(command.getFromId());
        Account to = accountRepository.findById(command.getToId());

        from.withdraw(command.getAmount());
        to.deposit(command.getAmount());

        accountRepository.save(from);
        accountRepository.save(to);

        // 여기서 문제: 알림 전송이 실패하면 이체도 롤백되는가?
        notificationPort.sendTransferNotification(from, to, command.getAmount());
    }
}
```

DB 저장과 외부 API 호출이 하나의 트랜잭션에 묶여있으면 외부 API 실패 시 DB 작업도 롤백된다. 이체는 성공해야 하는데 알림 실패 때문에 롤백되면 안 된다.

**대처 방법:**

- 외부 시스템 호출은 트랜잭션 밖으로 뺀다. `@TransactionalEventListener`를 쓰거나, 트랜잭션 커밋 후 별도로 호출한다.
- 이벤트 기반으로 분리한다. 도메인 이벤트를 발행하고, 이벤트 리스너에서 외부 API를 호출하면 트랜잭션 경계가 자연스럽게 나뉜다.

```java
@Service
@Transactional
public class TransferMoneyService implements TransferMoneyUseCase {

    private final AccountRepository accountRepository;
    private final ApplicationEventPublisher eventPublisher;

    @Override
    public void transfer(TransferCommand command) {
        Account from = accountRepository.findById(command.getFromId());
        Account to = accountRepository.findById(command.getToId());

        from.withdraw(command.getAmount());
        to.deposit(command.getAmount());

        accountRepository.save(from);
        accountRepository.save(to);

        // 트랜잭션 커밋 후 이벤트가 발행된다
        eventPublisher.publishEvent(new TransferCompletedEvent(from, to, command.getAmount()));
    }
}

// 트랜잭션 커밋 후 실행
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onTransferCompleted(TransferCompletedEvent event) {
    notificationPort.sendTransferNotification(event.getFrom(), event.getTo(), event.getAmount());
}
```

## Layered에서 클린 아키텍처로 마이그레이션

기존 Layered 프로젝트를 한 번에 클린 아키텍처로 전환하면 높은 확률로 실패한다. 코드 변경량이 많아서 리뷰가 불가능하고, 기능 개발이 멈춘다. 점진적으로 옮겨야 한다.

### 순서

**1단계: 도메인 로직을 Service에서 Entity로 이동**

가장 먼저 할 일이고, 아키텍처 변경 없이 할 수 있다. Service에 흩어진 비즈니스 규칙을 Entity 메서드로 옮긴다.

```java
// Before: Service에 비즈니스 로직이 있다
public class OrderService {
    public void cancelOrder(Long orderId) {
        Order order = orderRepository.findById(orderId);
        if (order.getStatus() != OrderStatus.PLACED) {
            throw new IllegalStateException("취소 불가");
        }
        order.setStatus(OrderStatus.CANCELLED);
        orderRepository.save(order);
    }
}

// After: Entity에 비즈니스 로직이 있다
public class Order {
    public void cancel() {
        if (this.status != OrderStatus.PLACED) {
            throw new IllegalStateException("취소 불가");
        }
        this.status = OrderStatus.CANCELLED;
    }
}

public class OrderService {
    public void cancelOrder(Long orderId) {
        Order order = orderRepository.findById(orderId);
        order.cancel();
        orderRepository.save(order);
    }
}
```

이 단계에서 부딪히는 문제: JPA Entity에 비즈니스 로직을 넣으면 `@Transient` 필드, 지연 로딩, 프록시 객체 등 JPA 특성과 충돌하는 경우가 있다. 예를 들어 `order.getItems()`를 호출했는데 LazyInitializationException이 터지면, 비즈니스 로직이 영속성 컨텍스트에 의존하게 되는 것이다. 이 문제가 빈번하다면 2단계로 넘어가야 할 시점이다.

**2단계: 아웃바운드 포트 도입 (Repository 인터페이스 분리)**

Service가 JPA Repository 구현체에 직접 의존하는 것을 인터페이스로 바꾼다. Spring Data JPA를 쓰고 있다면 이미 인터페이스 기반이라서 비교적 쉽다. 핵심은 도메인 패키지 안에 Repository 인터페이스를 두는 것이다.

```
# Before
service/ → repository/ (Spring Data JPA 인터페이스)

# After
domain/
  └── OrderRepository.java   ← 도메인 패키지에 인터페이스
adapter/out/
  └── OrderRepositoryImpl.java  ← 구현체는 adapter 패키지
```

이 단계에서 부딪히는 문제: Spring Data JPA의 `JpaRepository<OrderJpaEntity, Long>`을 도메인 인터페이스로 감싸야 하는데, 기존에 `findByStatusAndCreatedAtBetween()` 같은 쿼리 메서드를 20개씩 만들어둔 경우가 있다. 이걸 전부 도메인 인터페이스로 옮기면 도메인이 쿼리 중심 인터페이스가 된다. 조회용 쿼리는 CQRS 패턴으로 분리하거나, 복잡한 조회는 별도의 ReadModel로 처리하는 방법을 쓴다.

**3단계: 도메인 엔티티와 JPA 엔티티 분리**

비즈니스 규칙이 복잡한 애그리거트부터 분리한다. 한꺼번에 모든 엔티티를 분리하지 않는다.

이 단계에서 부딪히는 문제: 기존 코드가 JPA Entity의 연관관계(`@OneToMany`, `@ManyToOne`)에 강하게 의존하고 있으면, 도메인 엔티티로 분리할 때 연관 탐색 방식을 바꿔야 한다. JPA의 `order.getCustomer().getName()`을 도메인에서는 ID 참조(`order.getCustomerId()`)로 바꾸고, 필요할 때 별도로 조회하는 식이다.

**4단계: 인바운드 포트 도입 (UseCase 인터페이스)**

Controller가 Service 구현체를 직접 쓰는 것을 UseCase 인터페이스로 바꾼다. 이 단계는 꼭 필요한 건 아니다. 인바운드 포트가 주는 실질적인 이점은, 같은 유스케이스를 REST와 gRPC 등 여러 진입점에서 호출할 때이다. REST API만 있으면 생략해도 된다.

### 마이그레이션 할 때 흔한 실수

- **한 번에 전체 구조를 바꾸려고 한다.** 1~2개 도메인에 먼저 적용하고, 팀원들이 익숙해진 후 확장해야 한다.
- **패키지 구조만 바꾸고 끝낸다.** 폴더를 `domain/`, `application/`, `adapter/`로 나눠도 Service에 비즈니스 로직이 그대로면 의미가 없다. 패키지 구조가 아니라 의존성 방향이 핵심이다.
- **모든 엔티티를 분리한다.** 비즈니스 규칙이 없는 단순 CRUD 엔티티까지 분리하면 매핑 코드만 늘어난다.

## 클린 아키텍처가 맞지 않는 경우

클린 아키텍처는 만능이 아니다. 오히려 프로젝트를 느리게 만드는 경우가 있다.

### CRUD 위주 서비스

관리자 페이지, 내부 운영 도구, 데이터 조회 API처럼 비즈니스 규칙이 거의 없는 서비스가 있다. 이런 곳에 클린 아키텍처를 적용하면 파일 하나 추가에 5개 파일(Controller, UseCase, Service, Port, Adapter)을 만들어야 한다. 필드 하나 추가하면 DTO 3개, 매핑 코드 2곳을 고쳐야 한다. 비즈니스 로직이 `save(entity)` 한 줄인 UseCase를 인터페이스로 감싸는 건 의미가 없다.

```java
// 이런 UseCase가 대부분이면 클린 아키텍처가 과하다
@Override
public ProductResult createProduct(CreateProductCommand command) {
    Product product = new Product(command.getName(), command.getPrice());
    return ProductResult.from(productRepository.save(product));
}
```

이런 서비스는 Layered Architecture로 충분하다. Spring Data JPA + Controller + Service 3계층이면 된다.

### 소규모 팀 (1~2명)

팀원이 1~2명이면 "누군가 잘못된 의존성을 추가하는 것"을 아키텍처로 막을 필요가 없다. 코드 리뷰에서 잡으면 된다. 클린 아키텍처의 계층 분리는 팀 규모가 커서 서로의 코드를 다 볼 수 없을 때 의미가 커진다.

소규모 팀에서 클린 아키텍처를 쓰면 생기는 문제:
- 기능 하나 구현하는데 건드릴 파일이 너무 많다
- 새 기능 개발 속도가 Layered 대비 1.5~2배 느려진다
- 팀원이 퇴사하면 아키텍처를 이해하는 사람이 없어진다

### 프로토타입 / MVP 단계

제품이 시장에 맞는지 검증하는 단계에서는 빠르게 만들고 빠르게 버리는 게 중요하다. 아키텍처에 시간을 쓰면 검증 속도가 떨어진다. MVP가 성공해서 제품이 커지면 그때 리팩토링하는 게 낫다.

### DB 변경 가능성이 사실상 없는 경우

클린 아키텍처를 쓰는 이유로 "나중에 DB를 바꿀 수 있으니까"를 드는 경우가 많다. 실제로 운영 중인 서비스에서 MySQL을 MongoDB로 바꾸는 일이 얼마나 자주 있는지 생각해보면, 대부분의 프로젝트에서 이 이유는 성립하지 않는다. DB 교체보다는 "도메인 로직을 격리해서 테스트하기 쉽게 만드는 것"이 클린 아키텍처를 도입하는 실질적인 이유다. 테스트 필요성이 낮으면 도입 이유가 약해진다.

## 참고

- [Clean Architecture — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture — Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [DDD (Domain-Driven Design)](DDD.md) — 도메인 주도 설계
- [Design Pattern](Design Pattern/Creational_Pattern.md) — 생성 패턴
- [Spring Boot](../Framework/Java/Spring/Bean.md) — Spring 프레임워크
