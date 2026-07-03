---
title: 헥사고날 아키텍처
tags: [backend, architecture, hexagonal, ports-and-adapters, clean-architecture, spring-boot, nestjs, ddd, testing]
updated: 2026-05-11
---

# 헥사고날 아키텍처

## 시작하기 전에

Alistair Cockburn이 2005년에 제안한 헥사고날 아키텍처는 한 줄로 요약하면 "비즈니스 로직 안과 외부 세계 밖을 분리하고, 그 경계를 포트라는 인터페이스로 막아라"는 얘기다. 이름이 헥사고날(육각형)인 이유는 단순하다. 사각형으로 그리면 사람들이 "위는 UI, 아래는 DB"라고 해석해서 또 계층 구조로 받아들이기 때문이다. 육각형은 모든 변이 동등하다는 의미고, 컨트롤러든 DB든 메시지 큐든 외부 세계라는 점에서는 모두 같은 위치에 있다.

이 패턴이 실무에서 다시 주목받기 시작한 건 모놀리스 코드베이스가 5년쯤 지나면서 JPA 엔티티가 도메인 모델 행세를 하고, 컨트롤러가 Repository를 직접 호출하고, 비즈니스 로직이 Service에 흩어지면서 단위 테스트는 사실상 Spring 컨텍스트 통합 테스트가 되는 상황이 흔해진 시점이다. 누군가 "이렇게 만들면 DB 못 바꿉니다"라고 말하면 회의실이 조용해진다. 그러면서 헥사고날 얘기가 나온다.

문제는 헥사고날을 잘못 도입하면 단순 CRUD 한 줄 만들려고 인터페이스 4개와 어댑터 클래스 6개를 만들게 된다는 거다. 이 문서는 헥사고날이 진짜 가치를 발휘하는 지점, 잘못 적용했을 때 생기는 비대화 문제, 그리고 클린 아키텍처와 어떻게 다른지를 정리한다. Spring Boot와 NestJS 양쪽 예제를 모두 다룬다.

## 안과 밖이라는 단순한 이분법

헥사고날의 핵심은 4계층, 5계층이 아니라 단 두 영역만 구분한다는 점이다. 안(Application Core)과 밖(Adapters). 안에는 도메인과 유스케이스가 있고, 밖에는 컨트롤러, DB, 외부 API, CLI, 메시지 큐 같은 외부와 닿는 모든 것이 있다.

```
                ┌─────────── 밖 (Adapters) ───────────┐
                │                                     │
       REST  ───┤                                     ├─── JPA
       gRPC  ───┤    ┌─── 안 (Application Core) ──┐   ├─── MongoDB
       CLI   ───┤    │                            │   ├─── Redis
       Kafka ───┤    │   Domain + UseCase         │   ├─── Kafka
       Cron  ───┤    │                            │   ├─── External API
                │    └────────────────────────────┘   │
                │                                     │
                └─────────────────────────────────────┘
```

이 그림에서 왼쪽이 입력 측, 오른쪽이 출력 측처럼 보이지만 사실 본질은 같다. 양쪽 다 외부 세계고, 양쪽 다 어댑터로 분리된다. 왼쪽은 외부가 내부를 호출하는 방향이고, 오른쪽은 내부가 외부를 호출하는 방향이다. 호출 방향만 다를 뿐 둘 다 같은 종류의 분리다.

이 이분법이 강력한 이유는 "이건 안인가 밖인가"라는 질문 하나로 모든 코드의 위치가 결정되기 때문이다. 컨트롤러? 밖이다. JPA 엔티티? 밖이다. `OrderService`의 결제 처리 로직? 안이다. `PaymentGateway` 인터페이스? 안이다(포트는 안쪽에 정의). 결제 게이트웨이 호출 코드? 밖이다(어댑터는 바깥쪽 구현).

판단이 어려운 건 보통 도메인 객체에 프레임워크 어노테이션을 붙일지 말지 같은 경계 문제다. `@Entity`를 도메인 객체에 붙이는 순간 그 객체는 안과 밖 양쪽에 발을 걸친 상태가 된다. 헥사고날을 엄격하게 적용하면 도메인 객체와 JPA 엔티티는 분리되고, 어댑터에서 둘 사이를 변환한다. 이 변환 비용이 헥사고날의 가장 큰 부담이다.

## 포트와 어댑터의 네 가지 조합

헥사고날에서 가장 헷갈리는 용어가 포트와 어댑터, 그리고 driving과 driven, inbound와 outbound다. 셋이 거의 같은 뜻처럼 쓰이지만 미세하게 다르다. 정리하면 이렇다.

**Driving 어댑터 / Inbound 어댑터 / Primary 어댑터**: 외부에서 애플리케이션을 호출하는 쪽이다. 사용자가 REST API를 호출하면 컨트롤러가 유스케이스를 부른다. 컨트롤러가 driving 어댑터다. "이 시스템을 움직이게 하는(driving)" 측면이라는 의미다.

**Driven 어댑터 / Outbound 어댑터 / Secondary 어댑터**: 애플리케이션이 외부를 호출하는 쪽이다. 유스케이스가 DB에 저장하려고 Repository 인터페이스를 호출하면, 그 구현체인 JPA 어댑터가 실제 DB에 INSERT한다. 이 JPA 어댑터가 driven 어댑터다. "애플리케이션에 의해 구동되는(driven)" 측면이다.

**Inbound 포트**: driving 어댑터가 호출하는 인터페이스다. 유스케이스 인터페이스(`CreateOrderUseCase`)가 여기 해당한다. 애플리케이션 안쪽에 정의되고, 안에서 구현된다.

**Outbound 포트**: 애플리케이션이 외부에 의존할 때 정의하는 인터페이스다. `OrderRepository`, `PaymentGateway` 같은 것들이다. 인터페이스는 안쪽에 정의되지만, 구현체는 바깥쪽 어댑터에 있다.

이 네 조합을 코드로 보면 명확해진다.

```java
// === 안 (Application Core) ===

// Inbound 포트 (유스케이스 인터페이스)
public interface CreateOrderUseCase {
    OrderResult createOrder(CreateOrderCommand command);
}

// Inbound 포트 구현 (유스케이스 본체)
@Service
public class CreateOrderService implements CreateOrderUseCase {
    private final LoadOrderPort loadOrderPort;       // outbound 포트
    private final SaveOrderPort saveOrderPort;       // outbound 포트
    private final PaymentPort paymentPort;           // outbound 포트

    @Override
    public OrderResult createOrder(CreateOrderCommand command) {
        Order order = Order.create(command.userId(), command.items());
        paymentPort.charge(order.totalAmount());
        Order saved = saveOrderPort.save(order);
        return OrderResult.from(saved);
    }
}

// Outbound 포트 (인터페이스만 안쪽에 정의)
public interface LoadOrderPort {
    Optional<Order> load(OrderId id);
}

public interface SaveOrderPort {
    Order save(Order order);
}

public interface PaymentPort {
    PaymentResult charge(Money amount);
}

// === 밖 (Adapters) ===

// Driving / Inbound 어댑터 (REST Controller)
@RestController
@RequestMapping("/api/orders")
public class OrderRestController {
    private final CreateOrderUseCase createOrder;

    @PostMapping
    public OrderResponse create(@RequestBody OrderRequest req) {
        return OrderResponse.from(createOrder.createOrder(req.toCommand()));
    }
}

// Driven / Outbound 어댑터 (JPA 구현)
@Component
class OrderPersistenceAdapter implements LoadOrderPort, SaveOrderPort {
    private final OrderJpaRepository repo;
    private final OrderMapper mapper;

    @Override
    public Optional<Order> load(OrderId id) {
        return repo.findById(id.value()).map(mapper::toDomain);
    }

    @Override
    public Order save(Order order) {
        OrderJpaEntity entity = mapper.toJpaEntity(order);
        return mapper.toDomain(repo.save(entity));
    }
}
```

이 구조에서 주목할 점은 `CreateOrderService`가 `JpaRepository`, `RestTemplate`, `HttpClient` 같은 외부 기술 클래스를 단 하나도 임포트하지 않는다는 거다. import 문이 자기 패키지 내부와 도메인 객체뿐이다. 이게 헥사고날의 핵심 지표다. 유스케이스의 import 문에 외부 기술 클래스가 보이는 순간 어딘가에서 포트를 우회하고 있다는 신호다.

## 인바운드 포트가 정말 필요한가

여기서 자주 생기는 논쟁이 있다. 인바운드 포트(`CreateOrderUseCase` 같은 인터페이스)가 정말 필요한가 하는 거다. 어차피 구현체가 하나뿐인데 인터페이스를 만들 이유가 있냐는 얘기다.

실무 관점에서 답은 두 가지다.

첫째, 인바운드 포트는 "유스케이스의 시그니처를 명시적으로 선언"하는 효과가 있다. 컨트롤러가 `CreateOrderService`를 직접 참조하면 그 서비스 클래스의 모든 public 메서드에 의존하게 된다. 인터페이스로 좁히면 컨트롤러는 자기가 진짜 부르는 한 메서드만 본다. 이 차이는 유스케이스가 10개씩 모인 서비스 클래스를 리팩터링할 때 드러난다.

둘째, 테스트에서 의미가 있다. 컨트롤러를 단위 테스트할 때 인바운드 포트만 모킹하면 된다. 구현체를 모킹하려면 그 구현체가 의존하는 outbound 포트들까지 알아야 한다. 인터페이스가 모킹 표면을 좁혀준다.

다만 이게 항상 필요한 건 아니다. 작은 프로젝트나 유스케이스가 단순한 CRUD라면 인바운드 포트 인터페이스를 생략하고 서비스 클래스를 바로 쓰는 게 합리적이다. 헥사고날을 도입했다고 모든 유스케이스에 인터페이스 두 개씩 박을 필요는 없다. Spring 생태계에서는 인바운드 포트를 생략하고 outbound 포트만 정의하는 절충형이 흔하다.

## Spring Boot로 헥사고날 구성하기

실제 패키지 구조부터 보자. 헥사고날을 채택한 Spring Boot 프로젝트의 전형적인 모양이다.

```
src/main/java/com/example/order/
├── domain/                          # 순수 도메인 (Spring/JPA 어노테이션 없음)
│   ├── model/
│   │   ├── Order.java
│   │   ├── OrderItem.java
│   │   ├── OrderStatus.java
│   │   ├── OrderId.java             # 값 객체
│   │   └── Money.java
│   └── event/
│       └── OrderPlacedEvent.java
│
├── application/                     # 유스케이스 (안)
│   ├── port/
│   │   ├── in/                      # 인바운드 포트
│   │   │   ├── CreateOrderUseCase.java
│   │   │   ├── CancelOrderUseCase.java
│   │   │   └── GetOrderQuery.java
│   │   └── out/                     # 아웃바운드 포트
│   │       ├── LoadOrderPort.java
│   │       ├── SaveOrderPort.java
│   │       ├── PaymentPort.java
│   │       └── OrderEventPublisher.java
│   └── service/
│       ├── CreateOrderService.java
│       ├── CancelOrderService.java
│       └── GetOrderService.java
│
└── adapter/                         # 어댑터 (밖)
    ├── in/
    │   ├── web/
    │   │   ├── OrderRestController.java
    │   │   ├── OrderRequest.java
    │   │   └── OrderResponse.java
    │   └── messaging/
    │       └── OrderEventConsumer.java
    └── out/
        ├── persistence/
        │   ├── OrderJpaEntity.java
        │   ├── OrderJpaRepository.java
        │   ├── OrderMapper.java
        │   └── OrderPersistenceAdapter.java
        ├── payment/
        │   └── StripePaymentAdapter.java
        └── messaging/
            └── KafkaOrderEventPublisher.java
```

이 구조에서 도메인 객체는 Spring과 JPA 어노테이션이 없는 순수 Java다. 도메인 모델을 JPA 엔티티로 그대로 쓰는 게 흔한 단축이지만, 헥사고날을 엄격히 적용하면 둘을 분리한다.

```java
// domain/model/Order.java — 순수 도메인
public class Order {
    private final OrderId id;
    private final UserId userId;
    private final List<OrderItem> items;
    private OrderStatus status;
    private final Money totalAmount;
    private final Instant placedAt;

    private Order(OrderId id, UserId userId, List<OrderItem> items, Money total, Instant placedAt) {
        this.id = id;
        this.userId = userId;
        this.items = List.copyOf(items);
        this.status = OrderStatus.CREATED;
        this.totalAmount = total;
        this.placedAt = placedAt;
    }

    public static Order create(UserId userId, List<OrderItem> items) {
        if (items.isEmpty()) {
            throw new DomainException("주문 항목이 비어있다");
        }
        Money total = items.stream()
            .map(OrderItem::subtotal)
            .reduce(Money.ZERO, Money::add);
        if (total.isLessThan(Money.of(1000))) {
            throw new DomainException("최소 주문 금액 1,000원 미만");
        }
        return new Order(OrderId.generate(), userId, items, total, Instant.now());
    }

    public void place() {
        if (status != OrderStatus.CREATED) {
            throw new DomainException("CREATED 상태에서만 주문 확정 가능");
        }
        this.status = OrderStatus.PLACED;
    }

    public void cancel() {
        if (status != OrderStatus.PLACED) {
            throw new DomainException("PLACED 상태에서만 취소 가능");
        }
        this.status = OrderStatus.CANCELLED;
    }

    // getter만 노출, setter 없음
    public OrderId id() { return id; }
    public OrderStatus status() { return status; }
    public Money totalAmount() { return totalAmount; }
}
```

JPA 엔티티는 어댑터 패키지 안에 따로 둔다.

```java
// adapter/out/persistence/OrderJpaEntity.java
@Entity
@Table(name = "orders")
public class OrderJpaEntity {
    @Id
    private String id;

    @Column(name = "user_id")
    private String userId;

    @Column(name = "status")
    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    @Column(name = "total_amount", precision = 19, scale = 4)
    private BigDecimal totalAmount;

    @Column(name = "placed_at")
    private Instant placedAt;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "order_id")
    private List<OrderItemJpaEntity> items = new ArrayList<>();

    protected OrderJpaEntity() {} // JPA 요구사항
    // ...
}
```

매퍼가 둘 사이를 변환한다.

```java
// adapter/out/persistence/OrderMapper.java
@Component
public class OrderMapper {

    public Order toDomain(OrderJpaEntity entity) {
        List<OrderItem> items = entity.getItems().stream()
            .map(this::toDomainItem)
            .toList();
        return Order.reconstitute(
            new OrderId(entity.getId()),
            new UserId(entity.getUserId()),
            items,
            entity.getStatus(),
            Money.of(entity.getTotalAmount()),
            entity.getPlacedAt()
        );
    }

    public OrderJpaEntity toJpaEntity(Order order) {
        OrderJpaEntity entity = new OrderJpaEntity();
        entity.setId(order.id().value());
        entity.setUserId(order.userId().value());
        entity.setStatus(order.status());
        entity.setTotalAmount(order.totalAmount().value());
        entity.setPlacedAt(order.placedAt());
        entity.setItems(order.items().stream()
            .map(this::toJpaItem)
            .toList());
        return entity;
    }
}
```

여기서 `Order.reconstitute()`는 "이미 저장된 주문을 복원할 때 쓰는 생성자"다. `Order.create()`는 신규 생성, `reconstitute()`는 영속화된 상태에서 복원. 둘을 구분하는 이유는 신규 생성에는 도메인 규칙(최소 금액, 항목 존재 여부)이 적용되지만, 이미 저장된 주문은 그 시점에 이미 검증을 통과했기 때문이다. DB에 저장된 데이터를 도메인으로 복원할 때 다시 검증을 돌리면 과거 데이터가 현재 규칙에 어긋나는 경우 시스템이 깨진다.

매퍼와 별도 엔티티가 부담스러워 보일 수 있는데, 이게 헥사고날의 비용이다. 이 비용을 지불할 가치가 있는지가 도입 결정의 핵심이다. CRUD가 80%인 시스템에서는 이 분리가 과잉이고, 도메인 로직이 풍부한 시스템에서는 이 분리가 도메인을 프레임워크로부터 지키는 유일한 방법이다.

## NestJS로 헥사고날 구성하기

NestJS는 의존성 주입과 모듈 시스템이 있어서 헥사고날을 적용하기에 자연스럽다. 다만 TypeScript는 런타임에 인터페이스가 사라지기 때문에, NestJS의 DI에서 포트를 주입하려면 토큰을 써야 한다.

```
src/order/
├── domain/
│   ├── order.ts
│   ├── order-item.ts
│   └── order-id.ts
├── application/
│   ├── port/
│   │   ├── in/
│   │   │   ├── create-order.use-case.ts
│   │   │   └── cancel-order.use-case.ts
│   │   └── out/
│   │       ├── order.repository.ts
│   │       └── payment.gateway.ts
│   └── service/
│       ├── create-order.service.ts
│       └── cancel-order.service.ts
├── adapter/
│   ├── in/
│   │   └── web/
│   │       ├── order.controller.ts
│   │       └── dto/
│   │           └── create-order.request.ts
│   └── out/
│       ├── persistence/
│       │   ├── order.entity.ts
│       │   ├── order.repository.adapter.ts
│       │   └── order.mapper.ts
│       └── payment/
│           └── stripe-payment.adapter.ts
└── order.module.ts
```

포트는 TypeScript에서 인터페이스로 정의하고, DI 토큰을 같이 export한다.

```typescript
// application/port/out/order.repository.ts
import { Order } from '../../../domain/order';
import { OrderId } from '../../../domain/order-id';

export interface OrderRepository {
  save(order: Order): Promise<Order>;
  findById(id: OrderId): Promise<Order | null>;
}

export const ORDER_REPOSITORY = Symbol('ORDER_REPOSITORY');
```

유스케이스 구현에서 토큰으로 포트를 주입받는다.

```typescript
// application/service/create-order.service.ts
import { Inject, Injectable } from '@nestjs/common';
import { CreateOrderUseCase } from '../port/in/create-order.use-case';
import { ORDER_REPOSITORY, OrderRepository } from '../port/out/order.repository';
import { PAYMENT_GATEWAY, PaymentGateway } from '../port/out/payment.gateway';
import { Order } from '../../domain/order';

@Injectable()
export class CreateOrderService implements CreateOrderUseCase {
  constructor(
    @Inject(ORDER_REPOSITORY)
    private readonly orderRepository: OrderRepository,
    @Inject(PAYMENT_GATEWAY)
    private readonly paymentGateway: PaymentGateway,
  ) {}

  async createOrder(command: CreateOrderCommand): Promise<OrderResult> {
    const order = Order.create(command.userId, command.items);
    await this.paymentGateway.charge(order.totalAmount);
    const saved = await this.orderRepository.save(order);
    return OrderResult.from(saved);
  }
}
```

모듈에서 토큰과 구현체를 연결한다.

```typescript
// order.module.ts
import { Module } from '@nestjs/common';
import { OrderController } from './adapter/in/web/order.controller';
import { CreateOrderService } from './application/service/create-order.service';
import { CREATE_ORDER_USE_CASE } from './application/port/in/create-order.use-case';
import { ORDER_REPOSITORY } from './application/port/out/order.repository';
import { OrderRepositoryAdapter } from './adapter/out/persistence/order.repository.adapter';
import { PAYMENT_GATEWAY } from './application/port/out/payment.gateway';
import { StripePaymentAdapter } from './adapter/out/payment/stripe-payment.adapter';

@Module({
  controllers: [OrderController],
  providers: [
    { provide: CREATE_ORDER_USE_CASE, useClass: CreateOrderService },
    { provide: ORDER_REPOSITORY, useClass: OrderRepositoryAdapter },
    { provide: PAYMENT_GATEWAY, useClass: StripePaymentAdapter },
  ],
})
export class OrderModule {}
```

NestJS에서 헥사고날을 적용할 때 가장 흔하게 빠뜨리는 게 도메인 객체에 TypeORM이나 Mongoose 데코레이터를 그대로 박는 거다. `@Entity`, `@Column`을 도메인에 붙이는 순간 그 도메인은 ORM에 묶인다. 모듈을 분리해도 의존성 그래프는 그대로다. 도메인을 순수 클래스로 유지하고, ORM 엔티티는 어댑터 패키지에 따로 두는 게 헥사고날의 약속이다.

## 어댑터 교체로 외부 시스템 전환하기

헥사고날의 가장 잘 알려진 장점이 어댑터 교체만으로 외부 시스템을 바꿀 수 있다는 점이다. 다만 이게 마케팅 문구처럼 매끈하게 되는 건 아니다. 실제 어댑터를 교체할 때 부딪히는 현실을 본다.

### MySQL에서 MongoDB로

도메인 객체가 순수 Java/TypeScript이고 outbound 포트가 잘 정의돼 있다면 DB 교체는 어댑터 교체로 끝난다. 도메인과 유스케이스는 한 줄도 바뀌지 않는다.

```java
// 기존 어댑터 (MySQL + JPA)
@Component
class OrderJpaPersistenceAdapter implements LoadOrderPort, SaveOrderPort {
    private final OrderJpaRepository jpa;
    private final OrderMapper mapper;

    @Override
    public Order save(Order order) {
        OrderJpaEntity entity = mapper.toJpaEntity(order);
        return mapper.toDomain(jpa.save(entity));
    }
}

// 새 어댑터 (MongoDB)
@Component
class OrderMongoPersistenceAdapter implements LoadOrderPort, SaveOrderPort {
    private final OrderMongoRepository mongo;
    private final OrderDocumentMapper mapper;

    @Override
    public Order save(Order order) {
        OrderDocument doc = mapper.toDocument(order);
        return mapper.toDomain(mongo.save(doc));
    }
}
```

Spring 설정에서 어떤 어댑터를 쓸지만 결정한다.

```java
@Configuration
public class PersistenceConfig {
    @Bean
    @ConditionalOnProperty(name = "persistence", havingValue = "mongo")
    public LoadOrderPort mongoLoadOrderPort(OrderMongoPersistenceAdapter adapter) {
        return adapter;
    }

    @Bean
    @ConditionalOnProperty(name = "persistence", havingValue = "jpa", matchIfMissing = true)
    public LoadOrderPort jpaLoadOrderPort(OrderJpaPersistenceAdapter adapter) {
        return adapter;
    }
}
```

이게 가능하려면 두 가지 전제가 필요하다. 첫째, 포트가 SQL 특유의 개념(예: 페이지네이션 offset/limit, JOIN 결과)을 직접 노출하지 않아야 한다. `findByUserIdWithOrderItemsAndPaymentInfo` 같은 SQL-flavored 메서드가 포트에 있으면 MongoDB로 옮길 때 사실상 새로 짜야 한다. 둘째, 트랜잭션 경계가 단일 애그리거트 안에 있어야 한다. 여러 애그리거트에 걸친 트랜잭션을 RDB의 `@Transactional`로 묶고 있었다면 MongoDB(다중 문서 트랜잭션이 가능은 하지만 제약이 많다)로 옮길 때 새 트랜잭션 모델이 필요하다.

실무에서 DB를 통째로 교체하는 사례는 드물지만, 자주 일어나는 건 부분 교체다. "주문 본문은 MySQL, 주문 이력은 ElasticSearch", "사용자 본문은 MySQL, 세션은 Redis" 같은 폴리글랏 구성. 이때 헥사고날의 포트 분리가 잘 돼 있으면 각 포트마다 다른 어댑터를 붙이는 게 자연스럽다.

### REST에서 gRPC로

외부 결제 게이트웨이가 REST에서 gRPC로 바뀌는 시나리오를 본다. 포트가 결제 도메인 언어로 정의돼 있으면 어댑터만 갈아끼우면 끝난다.

```java
// 포트는 결제 도메인 언어로
public interface PaymentPort {
    PaymentResult charge(OrderId orderId, Money amount);
    PaymentResult refund(PaymentId paymentId, Money amount);
}

// 기존 REST 어댑터
@Component
class StripeRestPaymentAdapter implements PaymentPort {
    private final RestClient restClient;

    @Override
    public PaymentResult charge(OrderId orderId, Money amount) {
        ChargeRequest req = new ChargeRequest(orderId.value(), amount.value());
        ChargeResponse res = restClient.post()
            .uri("/v1/charges")
            .body(req)
            .retrieve()
            .body(ChargeResponse.class);
        return new PaymentResult(res.id(), res.status());
    }
}

// 새 gRPC 어댑터
@Component
class StripeGrpcPaymentAdapter implements PaymentPort {
    private final PaymentServiceGrpc.PaymentServiceBlockingStub stub;

    @Override
    public PaymentResult charge(OrderId orderId, Money amount) {
        ChargeRequest req = ChargeRequest.newBuilder()
            .setOrderId(orderId.value())
            .setAmount(amount.value().toString())
            .build();
        ChargeResponse res = stub.charge(req);
        return new PaymentResult(res.getId(), res.getStatus());
    }
}
```

여기서 함정이 있다. REST와 gRPC는 에러 처리 모델이 완전히 다르다. REST는 HTTP 상태 코드와 응답 바디로 에러를 표현하고, gRPC는 `Status` 코드와 트레일러 메타데이터로 에러를 표현한다. 어댑터에서 이걸 도메인 예외로 변환할 때 매핑 규칙이 다르다. 포트의 메서드 시그니처는 같아도, 어댑터 내부의 에러 처리 코드는 거의 새로 짠다고 봐야 한다. 통신 프로토콜이 다르면 타임아웃 모델, 재시도 정책도 다르다.

또 하나 자주 놓치는 건 직렬화 비용이다. JSON과 Protobuf는 페이로드 크기와 직렬화 속도가 다르다. 도메인 객체 → DTO 변환 비용은 같지만, DTO → 와이어 포맷 변환 비용은 다르다. gRPC로 바꾼 직후 P99 레이턴시가 갑자기 빨라지면 그게 직렬화 비용 차이일 수 있다. 반대로 메시지 크기가 큰 경우 gRPC가 더 느릴 수도 있다.

### 모든 어댑터 교체가 매끈하지는 않다

헥사고날을 도입한 시스템이라도 어댑터 교체가 한 줄도 안 바뀌고 끝나는 경우는 드물다. 잘 분리된 시스템에서도 보통 다음이 함께 변경된다.

- 포트의 에러 타입(외부 시스템 고유의 에러를 도메인 예외로 매핑하는 규칙)
- 트랜잭션 경계(RDB → NoSQL로 옮길 때)
- 일관성 모델(강한 일관성 → 최종 일관성으로 옮길 때 도메인 로직에 영향)
- 페이지네이션 방식(offset → cursor 기반으로 옮길 때 포트 시그니처 변경 필요)

헥사고날의 가치는 "0줄 변경"이 아니라 "변경 범위가 어댑터에 국한된다"는 거다. 도메인과 유스케이스 코드를 손대지 않는다는 것만으로도 충분한 가치가 있다.

## 통합 테스트에서 어댑터 모킹

헥사고날의 두 번째 큰 가치가 테스트 용이성이다. outbound 포트가 인터페이스로 분리돼 있으니 유스케이스 테스트는 가짜 어댑터를 주입해서 빠르게 돌릴 수 있다.

### 단위 테스트: 가짜 어댑터로 유스케이스 검증

```java
@Test
void 주문_생성_성공() {
    // 가짜 어댑터
    var fakeOrderRepo = new InMemoryOrderRepository();
    var fakePayment = new FakePaymentAdapter();
    
    var service = new CreateOrderService(fakeOrderRepo, fakeOrderRepo, fakePayment);
    
    var command = new CreateOrderCommand(
        new UserId("user-1"),
        List.of(new OrderItem("product-1", 2, Money.of(10000)))
    );
    
    OrderResult result = service.createOrder(command);
    
    assertThat(result.status()).isEqualTo(OrderStatus.PLACED);
    assertThat(fakeOrderRepo.savedOrders).hasSize(1);
    assertThat(fakePayment.chargedAmount).isEqualTo(Money.of(20000));
}

// 가짜 구현 (도메인 객체를 메모리에 보관)
class InMemoryOrderRepository implements LoadOrderPort, SaveOrderPort {
    final List<Order> savedOrders = new ArrayList<>();
    
    @Override
    public Order save(Order order) {
        savedOrders.add(order);
        return order;
    }
    
    @Override
    public Optional<Order> load(OrderId id) {
        return savedOrders.stream()
            .filter(o -> o.id().equals(id))
            .findFirst();
    }
}

class FakePaymentAdapter implements PaymentPort {
    Money chargedAmount;
    
    @Override
    public PaymentResult charge(OrderId orderId, Money amount) {
        this.chargedAmount = amount;
        return new PaymentResult(new PaymentId("test-payment"), PaymentStatus.SUCCESS);
    }
}
```

이 테스트는 Spring 컨텍스트가 필요 없다. JPA, RestTemplate, Stripe SDK가 메모리에 로드되지 않는다. 1초 미만에 수백 개를 돌릴 수 있다. Mockito도 굳이 필요 없다. 도메인이 풍부할수록 이런 빠른 테스트의 가치가 커진다.

Mockito를 쓰는 게 더 익숙하다면 인터페이스를 모킹하면 된다. 다만 stub 코드가 길어지고 가짜 구현보다 가독성이 떨어지는 경우가 많다. 어차피 포트가 잘 정의돼 있으면 가짜 구현이 짧다.

### 통합 테스트: 일부만 진짜로

실제 어댑터를 일부만 진짜로 쓰고 나머지는 가짜로 두는 게 통합 테스트의 핵심이다. Spring Boot에서는 `@SpringBootTest`와 프로파일을 조합해서 처리한다.

```java
@SpringBootTest
@ActiveProfiles("test")
class CreateOrderIntegrationTest {

    @Autowired
    private CreateOrderUseCase createOrder;

    @MockBean
    private PaymentPort paymentPort;  // 결제는 가짜로

    // OrderPersistenceAdapter는 실제로 H2/Testcontainers DB와 함께 동작

    @Test
    void 결제_성공_시_주문이_DB에_저장됨() {
        given(paymentPort.charge(any(), any()))
            .willReturn(new PaymentResult(new PaymentId("p-1"), PaymentStatus.SUCCESS));
        
        var command = new CreateOrderCommand(
            new UserId("user-1"),
            List.of(new OrderItem("product-1", 2, Money.of(10000)))
        );
        
        OrderResult result = createOrder.createOrder(command);
        
        // 실제 DB에서 조회
        var saved = orderJpaRepository.findById(result.orderId().value());
        assertThat(saved).isPresent();
        assertThat(saved.get().getStatus()).isEqualTo(OrderStatus.PLACED);
    }
}
```

여기서 어떤 어댑터를 진짜로 쓰고 어떤 걸 가짜로 둘지의 기준이 명확하다. **우리 코드 안에 있는 어댑터는 진짜, 외부 시스템과 통신하는 어댑터는 가짜.** DB 어댑터는 우리가 작성한 매퍼와 쿼리가 맞는지 검증해야 하니까 Testcontainers로 진짜 DB를 띄운다. 결제 게이트웨이 어댑터는 외부 시스템이라 테스트에서 호출하면 안 된다. 가짜로 둔다.

NestJS에서는 `@nestjs/testing`의 `Test.createTestingModule`로 같은 작업을 한다.

```typescript
describe('CreateOrderService', () => {
  let service: CreateOrderService;
  let fakeRepo: InMemoryOrderRepository;
  let fakePayment: FakePaymentGateway;

  beforeEach(async () => {
    fakeRepo = new InMemoryOrderRepository();
    fakePayment = new FakePaymentGateway();

    const module = await Test.createTestingModule({
      providers: [
        CreateOrderService,
        { provide: ORDER_REPOSITORY, useValue: fakeRepo },
        { provide: PAYMENT_GATEWAY, useValue: fakePayment },
      ],
    }).compile();

    service = module.get(CreateOrderService);
  });

  it('주문이 PLACED 상태로 저장된다', async () => {
    const command = new CreateOrderCommand('user-1', [
      { productId: 'p-1', quantity: 2, price: 10000 },
    ]);

    const result = await service.createOrder(command);

    expect(result.status).toBe('PLACED');
    expect(fakeRepo.saved).toHaveLength(1);
    expect(fakePayment.chargedAmount).toBe(20000);
  });
});
```

### 어댑터 자체의 테스트는 별도

가짜 어댑터로 유스케이스를 테스트하는 것과는 별개로, 진짜 어댑터 자체도 테스트해야 한다. `OrderPersistenceAdapter`의 매퍼가 도메인과 JPA 엔티티 사이를 정확히 변환하는지, 쿼리가 의도한 결과를 돌려주는지는 별도 테스트가 검증해야 한다. 보통 Testcontainers로 진짜 DB를 띄운 어댑터 슬라이스 테스트로 처리한다.

```java
@DataJpaTest
@Testcontainers
class OrderPersistenceAdapterTest {

    @Container
    static MySQLContainer<?> mysql = new MySQLContainer<>("mysql:8.0");

    @Autowired private OrderJpaRepository jpaRepo;
    private OrderPersistenceAdapter adapter;

    @BeforeEach
    void setUp() {
        adapter = new OrderPersistenceAdapter(jpaRepo, new OrderMapper());
    }

    @Test
    void 도메인_객체를_저장하고_복원하면_상태가_같다() {
        Order original = Order.create(
            new UserId("user-1"),
            List.of(new OrderItem("p-1", 2, Money.of(10000)))
        );
        original.place();

        Order saved = adapter.save(original);
        Order loaded = adapter.load(saved.id()).orElseThrow();

        assertThat(loaded.id()).isEqualTo(original.id());
        assertThat(loaded.status()).isEqualTo(OrderStatus.PLACED);
        assertThat(loaded.totalAmount()).isEqualTo(Money.of(20000));
    }
}
```

이 두 종류 테스트를 합쳐야 시스템 전체가 검증된다. 유스케이스 테스트는 비즈니스 규칙을, 어댑터 테스트는 외부 시스템과의 변환·통신을 검증한다.

## 클린 아키텍처와의 실무적 차이

클린 아키텍처와 헥사고날은 같은 사상을 공유한다. 도메인을 가장 안쪽에 두고, 의존성은 안쪽으로만 향하게 하고, 외부 기술은 인터페이스로 추상화한다. 다만 실무에서 코드를 짤 때 두 접근의 차이가 분명히 드러난다.

**클린 아키텍처는 4계층 의존성 규칙이다.** Entity, Use Case, Interface Adapter, Framework & Driver 네 개의 동심원. 각 계층은 자기보다 안쪽 계층만 알 수 있고, 바깥쪽은 모른다. 이 규칙이 강한 만큼 계층 수가 많고, 계층 간 변환 객체(Boundary 객체)가 명시적으로 등장한다. Use Case는 Entity를 알지만, Entity는 Use Case를 모른다. Interface Adapter는 Use Case의 입출력 모델을 Framework가 다루는 모델(예: HTTP Request, DB Row)로 변환한다.

**헥사고날은 안과 밖 두 영역이다.** Application Core(안)와 Adapter(밖). 두 영역 사이는 포트라는 인터페이스로 막힌다. 안에서 밖을 부를 때는 outbound 포트, 밖에서 안을 부를 때는 inbound 포트. 계층이 더 적고 개념이 단순하다.

이 구조 차이가 실무에서 만드는 차이는 다음과 같다.

### 1. 계층의 수

클린은 도메인 객체(Entity)와 유스케이스(Use Case)를 별개 계층으로 본다. 헥사고날에서는 둘 다 "안"이다. 헥사고날에서는 도메인과 유스케이스의 분리가 같은 패키지 안에서 일어나고, 계층 사이를 넘나드는 변환 객체가 따로 필요하지 않다.

클린 아키텍처를 엄격히 적용하면 컨트롤러 → 유스케이스 입력 모델 → 도메인 → 유스케이스 출력 모델 → 컨트롤러 응답으로 다섯 번 변환된다. 헥사고날에서는 컨트롤러 → Command(유스케이스 입력) → 도메인 → 유스케이스 결과 → 응답으로 네 번 변환된다. 한 번 차이지만 계층이 깊어질수록 변환 객체가 곱해진다.

### 2. 의존성 방향의 명시성

클린은 "의존성은 항상 안쪽으로"라는 규칙이 핵심이다. 어떤 방향으로 호출이 일어나든 의존(import)은 안쪽으로만 향해야 한다. 외부 어댑터가 유스케이스를 호출할 때도, 유스케이스가 어댑터를 호출할 때도(이때는 DIP로 인터페이스를 안쪽에 둔다), import 방향은 항상 안쪽이다.

헥사고날은 같은 원칙을 갖지만, "안과 밖"이라는 비유 자체가 더 시각적이다. 그래서 사람들에게 설명할 때 빠르다. "이건 안인가 밖인가" 한 문장으로 결정이 난다.

### 3. 도메인 객체와 ORM 엔티티의 분리

둘 다 도메인 객체를 ORM 엔티티와 분리할 것을 권장한다. 다만 클린은 이 분리를 거의 종교적으로 강제하는 경향이 있고(Entity 계층의 순수성), 헥사고날은 더 실용적이다. 헥사고날에서도 분리를 권장하지만, 실무에서 도메인 객체에 JPA 어노테이션이 한두 개 붙은 절충형을 두는 경우가 흔하다. 분리의 비용을 감당하기 어려운 작은 프로젝트라면 절충해도 헥사고날의 본질(포트와 어댑터 분리)은 유지된다.

### 4. 입출력 모델의 위치

클린에서 유스케이스의 입출력 모델(`Boundary`라고 부른다)은 유스케이스 계층 안에 있고, 어댑터가 이걸 변환해서 쓴다. 헥사고날에서는 Command/Query 객체로 부르는 게 일반적이고, 위치는 같다.

차이는 출력 처리에서 나온다. 클린의 정통은 출력도 인터페이스로 추상화한다. 유스케이스가 결과를 반환하지 않고, `OutputBoundary` 인터페이스를 통해 어댑터에 결과를 전달한다(Presenter 패턴). 이 구조는 화면 표시 로직을 어댑터로 빼는 데 유리하지만, 코드량이 많아진다.

```java
// 클린 정통: Output Boundary
public interface CreateOrderOutputBoundary {
    void present(OrderResult result);
    void presentError(String errorCode);
}

public class CreateOrderInteractor implements CreateOrderInputBoundary {
    private final CreateOrderOutputBoundary presenter;
    
    @Override
    public void create(CreateOrderInputData data) {
        // ... 비즈니스 로직
        presenter.present(result);  // 반환이 아니라 호출
    }
}
```

헥사고날에서는 보통 유스케이스가 결과를 직접 반환한다. 컨트롤러가 그 결과를 HTTP 응답으로 변환한다. 간결하고 일반적인 Spring/NestJS 패턴과 잘 맞는다.

```java
// 헥사고날: 직접 반환
public interface CreateOrderUseCase {
    OrderResult createOrder(CreateOrderCommand command);
}
```

### 어느 쪽을 선택하나

실무에서는 두 접근이 섞여서 적용되는 경우가 대부분이다. 헥사고날의 포트와 어댑터 개념을 가져오되, 클린의 4계층 중 Entity와 Use Case를 같이 두는 헥사고날 스타일을 따른다. 그리고 출력 처리는 클린의 Output Boundary가 아니라 헥사고날의 단순 반환을 쓴다.

순수 클린 아키텍처를 엄격히 따르는 게 가치가 있는 경우는 정해져 있다. 비즈니스 로직이 매우 복잡하고, UI/외부 시스템이 자주 바뀌고, 팀에 클린 아키텍처에 대한 합의가 강한 경우. 일반적인 백엔드 서비스에서는 헥사고날 변형이 더 자연스럽다.

## 포트 인터페이스 비대화 문제

헥사고날을 도입하고 6개월쯤 지나면 거의 모든 팀이 겪는 문제가 있다. outbound 포트 인터페이스가 비대해진다는 거다. 처음에는 `OrderRepository`에 `save`, `findById` 두 개로 시작하지만, 시간이 지나면 다음 같은 모양이 된다.

```java
public interface OrderRepository {
    Order save(Order order);
    Optional<Order> findById(OrderId id);
    List<Order> findByUserId(UserId userId);
    List<Order> findByStatus(OrderStatus status);
    Page<Order> findByUserIdAndStatusOrderByPlacedAtDesc(UserId userId, OrderStatus status, Pageable pageable);
    List<Order> findOrdersForReport(LocalDate from, LocalDate to);
    int countByUserIdAndPlacedAtAfter(UserId userId, Instant since);
    void deleteByPlacedAtBefore(Instant cutoff);
    List<OrderSummary> findOrderSummariesByUserId(UserId userId);
    // ... 30개 더
}
```

이 인터페이스를 가짜로 구현해서 테스트하려면 30개 메서드를 다 만들어야 한다. 안 쓰는 메서드까지 stub으로 채워야 한다. 어댑터를 교체하려면 30개를 다 다시 구현해야 한다. 헥사고날의 장점이 비용으로 바뀌는 순간이다.

이 문제를 해결하는 분리 기준 몇 가지를 본다.

### 1. CQRS 스타일로 Command와 Query를 분리한다

쓰기 포트와 읽기 포트를 나눈다. 도메인 객체를 다루는 쓰기는 도메인 의미가 강하고, 화면 표시를 위한 읽기는 다양한 변형이 필요하다. 둘을 같은 인터페이스에 두면 자연히 비대해진다.

```java
// 쓰기 포트 (도메인 객체 단위)
public interface SaveOrderPort {
    Order save(Order order);
}

public interface LoadOrderPort {
    Optional<Order> load(OrderId id);
}

public interface DeleteOrderPort {
    void delete(OrderId id);
}

// 읽기 포트 (조회 모델 단위, 별도 인터페이스)
public interface OrderListQuery {
    Page<OrderSummary> listByUserId(UserId userId, OrderStatus status, Pageable pageable);
}

public interface OrderReportQuery {
    List<OrderReportRow> findForReport(LocalDate from, LocalDate to);
}
```

읽기는 도메인 객체 `Order`가 아니라 화면용 DTO(`OrderSummary`, `OrderReportRow`)를 반환한다. JPA 엔티티 거치지 않고 Projection이나 JOOQ로 바로 DTO를 가져오면 성능도 좋아진다. 자세한 분리 기준은 [CQRS 패턴](CQRS_Pattern.md) 문서를 참고한다.

### 2. 유스케이스 단위로 포트를 나눈다 (ISP 적용)

인터페이스 분리 원칙(ISP)을 적용해서 각 유스케이스가 필요한 것만 가진 포트를 정의한다.

```java
// 주문 생성 유스케이스가 쓰는 포트
public interface NewOrderPersistencePort {
    Order save(Order order);
    boolean existsActiveOrderByUserId(UserId userId);
}

// 주문 취소 유스케이스가 쓰는 포트
public interface OrderCancellationPort {
    Order loadForCancellation(OrderId id);
    Order save(Order order);
}

// 주문 조회 유스케이스가 쓰는 포트
public interface OrderQueryPort {
    Optional<OrderDetail> findDetail(OrderId id);
}
```

같은 어댑터 클래스가 여러 포트를 구현해도 된다.

```java
@Component
class OrderPersistenceAdapter 
    implements NewOrderPersistencePort, OrderCancellationPort, OrderQueryPort {
    // ...
}
```

이 방식의 장점은 유스케이스 테스트할 때 작은 포트만 가짜로 만들면 된다는 거다. 단점은 포트 인터페이스가 늘어나서 도메인을 처음 본 사람이 헷갈릴 수 있다는 점이다.

### 3. 도메인 의미 단위로 포트를 나눈다

같은 외부 시스템이라도 도메인 의미가 다르면 다른 포트로 분리한다. 결제 게이트웨이를 예로 들면 결제 처리, 환불 처리, 결제 수단 조회는 도메인 의미가 다르다.

```java
public interface PaymentChargePort {
    PaymentResult charge(OrderId orderId, Money amount, PaymentMethod method);
}

public interface PaymentRefundPort {
    RefundResult refund(PaymentId paymentId, Money amount, RefundReason reason);
}

public interface PaymentMethodQueryPort {
    List<PaymentMethod> findByUserId(UserId userId);
}
```

세 포트가 결국 같은 Stripe SDK를 호출하더라도, 도메인 입장에서는 분리된 의미를 갖는다. 결제 처리 유스케이스는 Charge만, 환불 유스케이스는 Refund만 의존한다.

### 어느 기준이 맞나

세 기준이 배타적이지 않다. 보통 다음 순서로 적용된다.

먼저 Command/Query를 나눈다. 이게 가장 큰 효과를 본다. 도메인 객체를 다루는 쓰기는 안정적인 반면, 화면용 읽기는 자주 추가되고 변형된다. 둘을 섞어두면 안정적인 쓰기 포트가 매번 읽기 추가 때문에 흔들린다.

그 다음으로 도메인 의미가 분명히 다른 경우 도메인 단위로 분리한다(결제 처리/환불처럼). ISP를 미세하게 적용하는 건 마지막 단계다. 미리 잘게 쪼개기보다, 인터페이스가 너무 커진다고 느낄 때 분리하는 게 실무적이다.

핵심은 "헥사고날을 한다고 모든 포트를 잘게 나눈다"가 아니라, "포트가 비대해지는 신호를 인지하고 적절한 기준으로 분리한다"이다. 잘게 나누는 데도 비용이 있다. 인터페이스가 많아질수록 코드베이스를 처음 만나는 사람이 의존 관계를 추적하기 어려워진다.

## 헥사고날을 도입하지 말아야 할 때

마지막으로 헥사고날을 도입하지 말아야 할 경우를 정리한다. 헥사고날은 도구지 종교가 아니다.

**도메인 로직이 거의 없는 시스템.** CRUD가 90% 이상인 어드민 도구, 데이터 입출력만 하는 게이트웨이 서비스. 이런 경우 헥사고날의 변환 비용이 도메인 보호의 이득보다 크다.

**프로토타입이나 단명 서비스.** 6개월 안에 다시 짤 가능성이 높은 코드에 매퍼와 어댑터를 분리해두면, 그 분리에 들인 시간이 회수되지 않는다.

**팀이 헥사고날에 합의되지 않은 경우.** 한 사람이 헥사고날을 도입하면 다른 사람들이 "왜 컨트롤러에서 Repository를 바로 못 부르냐"고 묻기 시작한다. 결국 어댑터를 우회하는 코드가 들어오고, 헥사고날을 부분적으로 적용한 상태가 가장 나쁜 상태다. 도입 전에 팀 전체의 합의가 필요하다.

**Spring Data JPA에 강하게 의존하는 작은 서비스.** Spring Data의 `JpaRepository`는 사실 이미 일종의 포트다. 추가로 outbound 포트 인터페이스를 만들고 어댑터로 다시 감싸는 게 과잉인 경우가 많다. 도메인이 단순하면 `JpaRepository`를 그대로 쓰는 게 합리적이다.

반대로 헥사고날이 가치를 발휘하는 경우는 도메인 로직이 풍부하고, 외부 시스템 의존이 많고(DB + 결제 + 메시지 큐 + 외부 API), 시스템 수명이 길고, 팀이 합의된 시스템이다. 이 조건이 갖춰진 곳에서는 헥사고날이 코드를 외부 변화로부터 지키는 가장 검증된 방법 중 하나다.

## 정리

헥사고날은 "안과 밖" 이분법으로 클린 아키텍처를 단순화한 패턴이다. 4계층 의존성 규칙 대신 두 영역과 포트라는 인터페이스로 의존성을 막는다. 클린이 출력 처리까지 추상화하는 반면, 헥사고날은 유스케이스가 결과를 직접 반환하는 실용적 접근을 택한다.

도입 효과는 어댑터 교체 비용을 어댑터 안에 가둔다는 점이다. DB를 바꾸거나 외부 프로토콜이 변할 때 도메인과 유스케이스 코드는 손대지 않는다. 단위 테스트가 빨라지고, 통합 테스트는 어떤 어댑터를 진짜로 둘지 명확하게 결정할 수 있다.

비용은 매퍼와 변환 객체가 늘어나는 거다. 도메인이 단순한 시스템에서는 이 비용이 이득을 초과한다. 그리고 포트 인터페이스가 비대해지는 문제를 인지하고 Command/Query, 유스케이스 단위, 도메인 의미 단위로 분리할 줄 알아야 한다.

함께 읽으면 좋은 문서:

- [백엔드 레이아웃](Backend_Layout.md)
- [CQRS 패턴](CQRS_Pattern.md)
- [이벤트 기반 아키텍처](Event_Driven_Architecture.md)
- [마이크로서비스 아키텍처](Microservices_Architecture.md)
