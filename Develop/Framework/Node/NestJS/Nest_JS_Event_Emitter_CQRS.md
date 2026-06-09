---
title: NestJS Event Emitter / CQRS 심화
tags:
  - nestjs
  - event-driven
  - cqrs
  - event-emitter
  - saga
  - outbox-pattern
  - domain-event
updated: 2026-06-09
---

# NestJS Event Emitter / CQRS 심화

서비스가 커지면 컨트롤러 한 함수에 "주문 저장 → 재고 차감 → 포인트 적립 → 알림 발송 → 분석 로그 기록"이 다 들어가는 순간이 온다. 처음에는 그냥 await으로 쭉 늘어놓다가, 알림 서버가 1초 늦으면 주문 API 응답이 1초 늦어지고, 포인트 적립이 실패하면 주문이 롤백되어야 하느냐는 질문이 나오기 시작한다. 이 시점에서 이벤트 기반 분리와 CQRS가 등장한다.

NestJS는 두 가지 도구를 따로 제공한다. 가벼운 in-process pub/sub이면 `@nestjs/event-emitter`, 도메인 모델과 핸들러를 분리하고 Saga까지 쓰려면 `@nestjs/cqrs`. 둘 다 "이벤트"라는 단어를 쓰지만 책임 범위가 다르다. 모르고 쓰면 EventEmitter2 위에 EventBus를 한 번 더 얹는 이상한 구조가 나온다.

## Event Emitter — 가장 가벼운 인-프로세스 디커플링

`@nestjs/event-emitter`는 EventEmitter2를 NestJS DI에 붙여놓은 얇은 래퍼다. 모듈 등록 후 어디서나 `EventEmitter2`를 주입해 `emit`을 호출하면, `@OnEvent` 데코레이터가 붙은 메서드가 호출된다.

```ts
// app.module.ts
@Module({
  imports: [
    EventEmitterModule.forRoot({
      wildcard: true,
      delimiter: '.',
      maxListeners: 20,
      verboseMemoryLeak: true,
    }),
  ],
})
export class AppModule {}
```

`wildcard: true`를 켜면 `order.*`, `order.**` 같은 패턴 구독이 가능하다. delimiter를 `.`으로 잡으면 `order.created`, `order.cancelled` 같은 네이밍이 자연스럽게 풀린다. `maxListeners` 기본값(10)에 걸려서 production에서 경고가 뜨는 경우가 종종 있는데, 도메인이 커지면 한 이벤트에 5~6개 핸들러가 붙는 건 흔해서 처음부터 넉넉히 잡아두는 편이 낫다.

### 동기 vs 비동기 이벤트의 함정

가장 헷갈리는 부분이 "emit이 동기냐 비동기냐"다. EventEmitter2의 기본 동작은 **동기**다. `emitter.emit('order.created', payload)`를 호출하면 같은 이벤트 루프 틱에서 등록된 모든 리스너가 순차적으로 실행되고, 마지막 리스너가 끝나야 emit이 반환된다. 리스너가 Promise를 반환해도 emit은 그걸 기다리지 않는다. 따라서 핸들러 안에서 `await someAsyncWork()`를 하면, emit은 즉시 반환되고 핸들러는 백그라운드에서 fire-and-forget으로 떨어진다.

이게 문제가 되는 경우가 있다. 트랜잭션 안에서 이벤트를 발행하고, 핸들러가 같은 DB 연결로 추가 작업을 해야 한다면, fire-and-forget으로 떨어지는 순간 트랜잭션 컨텍스트가 깨진다. 이럴 때는 `emitAsync`를 써야 한다.

```ts
const results = await this.emitter.emitAsync('order.created', event);
```

`emitAsync`는 등록된 모든 리스너의 Promise를 `Promise.all`로 기다린다. 한 핸들러가 5초 걸리면 emit도 5초 멈춘다. 동기와 비동기 중 뭘 쓸지는 "이벤트 발행자가 핸들러 결과나 완료 여부에 의존하느냐"로 결정한다. 의존하면 `emitAsync`, 아니면 `emit`. 알림 발송이나 분석 로그 같은 진짜 사이드이펙트는 `emit`으로 흘려보내는 게 맞다.

한 가지 더, `emitAsync`의 Promise.all 동작 때문에 핸들러 하나가 throw하면 다른 핸들러의 결과까지 reject로 묶여서 받게 된다. 발행자가 핸들러 실패를 어떻게 처리할지 정해두지 않으면, 알림 실패 때문에 주문 생성 API가 500을 뱉는 사고가 난다.

### @OnEvent 데코레이터와 옵션

```ts
@Injectable()
export class NotificationListener {
  @OnEvent('order.created', { async: true, promisify: true })
  async handleOrderCreated(event: OrderCreatedEvent) {
    await this.sendEmail(event.userId, event.orderId);
  }

  @OnEvent('order.**', { suppressErrors: false })
  handleAnyOrder(event: BaseOrderEvent) {
    this.metrics.increment(`order.${event.type}`);
  }
}
```

`async: true`는 핸들러를 `setImmediate`로 던져서 발행자 스택에서 빼낸다. `promisify: true`는 핸들러 반환을 Promise로 감싸서 `emitAsync`의 Promise.all 체인에 정상적으로 합류시킨다. 이 두 옵션 조합이 헷갈리는데, 보통 "발행자와 격리하면서도 await으로 결과를 받고 싶다"는 경우는 거의 없어서, 둘 중 하나만 쓰는 게 일반적이다. fire-and-forget이면 `async: true`만, await으로 받으려면 둘 다 빼고 그냥 async 메서드로 쓴다.

`suppressErrors`는 기본 true다. 즉 핸들러가 throw해도 emit 측은 모른 채 넘어간다. 이게 의도된 격리지만, 디버깅 중 핸들러가 조용히 실패하는 게 보이지 않아서 한참 헤매는 일이 많다. development 환경에서는 `suppressErrors: false`로 두거나, 모든 핸들러를 try/catch + 로거로 감싸는 규칙을 두는 편이 낫다.

### 와일드카드 구독의 실제 쓰임

```ts
@OnEvent('user.**')
async auditUserEvent(event: any, eventName?: string) {
  await this.auditLog.write({ type: eventName, payload: event });
}
```

와일드카드는 감사 로그, 메트릭 수집, 디버그 트레이서에서 거의 항상 쓰인다. `*`는 한 단계, `**`는 여러 단계를 매칭한다. `order.*`는 `order.created`는 잡지만 `order.payment.failed`는 못 잡는다. `order.**`가 둘 다 잡는다. 한 가지 주의할 점은, 와일드카드 핸들러가 두 번째 인자로 이벤트 이름을 받아야 어떤 이벤트인지 구분 가능하다는 점이다. 단일 이벤트 구독에서는 굳이 받을 필요가 없는 인자라서 잊기 쉽다.

### EventEmitter의 한계

`@nestjs/event-emitter`는 **같은 프로세스 안의 in-memory** pub/sub이다. 인스턴스가 두 대면 한 인스턴스에서 발행한 이벤트는 다른 인스턴스의 핸들러에 도달하지 않는다. 또 프로세스가 죽으면 큐잉된 이벤트는 사라진다. "주문 생성 이벤트는 절대 유실되면 안 된다" 같은 보장이 필요한 순간 이 도구로는 부족해진다. 그때는 Kafka, RabbitMQ, Redis Streams 같은 외부 브로커로 가야 하고, 이게 뒤에 나올 Outbox 패턴과 연결된다.

## CQRS — 명령과 조회를 분리한다

`@nestjs/cqrs`는 이름 그대로 Command Query Responsibility Segregation 패턴을 구현체로 제공한다. 핵심은 세 가지 버스다. `CommandBus`, `QueryBus`, `EventBus`. 각각에 핸들러를 등록하고 dispatch하면 핸들러가 호출된다. EventEmitter와 비슷해 보이지만 의도가 다르다.

- **Command**: 상태를 변경하는 의도. 보통 1:1로 핸들러가 매핑된다. `CreateOrderCommand`는 `CreateOrderHandler` 딱 하나가 처리한다.
- **Query**: 상태를 읽는 의도. 역시 1:1. 부수효과 없이 데이터만 반환한다.
- **Event**: 이미 일어난 사실. 1:N. 여러 핸들러가 관심을 가질 수 있다.

EventEmitter는 모든 걸 이벤트로 본다. CQRS는 "이건 명령이고 저건 사건이다"라고 의도를 코드 타입으로 못박는다. 이 구분이 강제되어야 도메인 로직을 깔끔하게 유지할 수 있다.

### Command와 Handler

```ts
export class CreateOrderCommand {
  constructor(
    public readonly userId: string,
    public readonly items: OrderItem[],
  ) {}
}

@CommandHandler(CreateOrderCommand)
export class CreateOrderHandler implements ICommandHandler<CreateOrderCommand> {
  constructor(
    private readonly orderRepo: OrderRepository,
    private readonly publisher: EventPublisher,
  ) {}

  async execute(command: CreateOrderCommand): Promise<string> {
    const order = this.publisher.mergeObjectContext(
      Order.create(command.userId, command.items),
    );
    await this.orderRepo.save(order);
    order.commit();
    return order.id;
  }
}
```

`mergeObjectContext`가 CQRS의 도메인 이벤트 발행 메커니즘이다. 도메인 객체(`Order`)가 `AggregateRoot`를 상속하면 내부에 발행 대기 이벤트 목록을 가진다. 비즈니스 로직 안에서 `this.apply(new OrderCreatedEvent(...))`를 호출하면 그 이벤트가 큐에 쌓이고, `commit()` 호출 시점에 EventBus로 흘러간다.

이 구조가 중요한 이유는 **도메인 모델이 인프라(EventBus)를 직접 알지 못해도 된다**는 점이다. `Order.create()`는 순수 도메인 함수고, 이벤트는 그냥 객체 큐에 쌓는다. 발행은 핸들러가 책임진다. 그래서 도메인 로직 단위 테스트가 깔끔하게 된다. EventBus를 mock할 필요가 없다.

### Query와 Read Model

```ts
export class GetOrderQuery {
  constructor(public readonly orderId: string) {}
}

@QueryHandler(GetOrderQuery)
export class GetOrderHandler implements IQueryHandler<GetOrderQuery> {
  constructor(private readonly readDb: OrderReadRepository) {}

  async execute(query: GetOrderQuery): Promise<OrderView> {
    return this.readDb.findById(query.orderId);
  }
}
```

Query 핸들러는 별도의 read repository를 쓰는 경우가 많다. 쓰기는 정규화된 도메인 모델, 읽기는 denormalized된 view 테이블에서 한다. 같은 DB를 써도 되고, 읽기를 Elasticsearch나 Redis로 분리해도 된다. 분리 정도는 트래픽 패턴이 정한다. 작은 서비스에서 read model을 따로 두는 건 오버엔지니어링이지만, 주문 목록 조회가 복잡한 join 12개를 거치고 있다면 read view 하나로 정리하는 게 답이 된다.

### EventBus와 EventHandler

Command 핸들러가 `order.commit()`을 호출하면 누적된 도메인 이벤트가 EventBus로 흘러간다. EventBus 입장에서는 등록된 `@EventsHandler(OrderCreatedEvent)`를 모두 찾아 `handle(event)`를 호출한다.

```ts
@EventsHandler(OrderCreatedEvent)
export class SendOrderConfirmationHandler implements IEventHandler<OrderCreatedEvent> {
  constructor(private readonly mailer: MailerService) {}

  async handle(event: OrderCreatedEvent) {
    await this.mailer.sendOrderConfirmation(event.userId, event.orderId);
  }
}

@EventsHandler(OrderCreatedEvent)
export class GrantOrderPointsHandler implements IEventHandler<OrderCreatedEvent> {
  async handle(event: OrderCreatedEvent) {
    await this.pointService.grant(event.userId, event.totalAmount);
  }
}
```

한 이벤트에 여러 핸들러가 붙는 게 자연스럽다. 핸들러끼리는 서로의 존재를 모른다. 새 핸들러를 추가해도 기존 코드는 한 줄도 안 바뀐다. 이게 도메인 이벤트의 핵심 가치다.

### Saga — 이벤트 오케스트레이션

도메인 이벤트가 또 다른 명령을 유발해야 할 때가 있다. "주문이 생성되면 → 재고 차감 명령을 발행한다"처럼. Command 핸들러 안에서 다른 Command를 dispatch하면 결합도가 높아지고, 트랜잭션 경계가 흐려진다. Saga는 이 흐름을 별도 객체로 빼낸다.

```ts
@Injectable()
export class OrderSaga {
  @Saga()
  orderCreated = (events$: Observable<any>): Observable<ICommand> => {
    return events$.pipe(
      ofType(OrderCreatedEvent),
      map((event) => new DeductInventoryCommand(event.orderId, event.items)),
    );
  };

  @Saga()
  inventoryFailed = (events$: Observable<any>): Observable<ICommand> => {
    return events$.pipe(
      ofType(InventoryDeductionFailedEvent),
      map((event) => new CancelOrderCommand(event.orderId, 'OUT_OF_STOCK')),
    );
  };
}
```

Saga는 RxJS 스트림이다. EventBus에 흘러간 모든 이벤트가 이 Observable로 들어오고, `ofType`으로 관심 있는 이벤트만 필터해서 다음 Command를 만들어 dispatch한다. 메서드 형태로 보이지만 실제로는 모듈 부팅 시 한 번만 subscribe된다.

Saga의 강력함은 이벤트 시퀀스를 한 곳에서 본다는 점이다. "주문 생성 → 재고 차감 → 결제 → 배송 시작 → 알림" 같은 흐름이 Saga 파일 하나에 정리된다. Command/Event 핸들러는 각자 자기 일만 한다. 단, 이름과 달리 진짜 분산 트랜잭션 Saga(보상 트랜잭션 포함)를 구현해주지는 않는다. 보상 로직은 직접 짜야 한다. "inventoryFailed → CancelOrderCommand" 같은 보상 흐름도 직접 코딩하는 식이다.

### CQRS 이벤트의 동기·비동기 동작

`@nestjs/cqrs`의 EventBus는 기본적으로 **동기적**으로 publish한다. `commandBus.execute()` 안에서 `order.commit()`이 호출되면, EventBus는 등록된 모든 핸들러를 즉시 호출하고 await한다. 이 동작이 EventEmitter와 다른 점이다.

그래서 Command 핸들러의 응답 시간에 모든 EventHandler 시간이 합산된다. 알림 발송이 느리면 주문 생성 API도 느려진다. 이걸 피하려면 EventHandler 안에서 직접 외부 큐로 던지거나, 동기 처리가 필수가 아닌 핸들러는 `@nestjs/event-emitter`로 따로 빼는 식의 분기가 필요하다. 또는 다음에 나올 Outbox 패턴으로 진짜 비동기 발행을 구현한다.

## 트랜잭션 경계와 이벤트 발행 시점 — Outbox 패턴

CQRS를 처음 쓰면 거의 모두가 이 함정에 빠진다.

```ts
async execute(command: CreateOrderCommand) {
  const order = this.publisher.mergeObjectContext(Order.create(...));
  await this.orderRepo.save(order);  // DB 트랜잭션 커밋
  order.commit();                    // 이벤트 발행
}
```

이 코드의 문제는 **DB 커밋과 이벤트 발행이 같은 트랜잭션이 아니라는 점**이다. 시나리오를 보자.

1. `orderRepo.save()`가 성공해서 DB에 주문이 저장됐다.
2. `order.commit()`이 호출되어 `SendOrderConfirmationHandler`가 동기로 실행된다.
3. 메일 발송 중 프로세스가 죽거나, 이메일 서버가 응답하지 않는다.
4. 주문은 DB에 있는데 메일은 안 갔다. 사용자는 주문 완료 화면을 봤는데 확인 메일이 안 온다.

반대로 순서를 바꾸면:

1. `order.commit()`이 먼저 호출되어 메일이 발송됐다.
2. `orderRepo.save()`가 DB 제약조건 위반으로 실패했다.
3. 메일은 갔는데 주문은 없다. 사용자는 "주문하지도 않았는데 왜 메일이 오냐"고 문의한다.

이 문제는 EventBus를 동기로 쓰든 비동기로 쓰든, in-memory든 외부 브로커든 본질적으로 같다. **로컬 DB 트랜잭션과 외부 시스템 호출(메시지 발행)을 원자적으로 묶을 수 없기 때문**이다. 2PC를 쓰면 가능하지만 현대 분산 시스템에서는 거의 안 쓴다. 그래서 Outbox 패턴이 표준이 됐다.

### Outbox의 핵심 아이디어

이벤트를 외부 브로커로 바로 보내지 않고, **같은 DB의 outbox 테이블에 INSERT**한다. 주문 INSERT와 outbox INSERT가 같은 트랜잭션 안에서 일어나므로 둘 다 커밋되거나 둘 다 롤백된다. 그 다음 별도 프로세스(또는 같은 프로세스의 별도 워커)가 outbox 테이블을 폴링하면서 미발행 이벤트를 외부 브로커로 보낸다.

```ts
@CommandHandler(CreateOrderCommand)
export class CreateOrderHandler implements ICommandHandler<CreateOrderCommand> {
  constructor(
    private readonly dataSource: DataSource,
    private readonly publisher: EventPublisher,
  ) {}

  async execute(command: CreateOrderCommand) {
    return this.dataSource.transaction(async (manager) => {
      const order = this.publisher.mergeObjectContext(
        Order.create(command.userId, command.items),
      );

      await manager.getRepository(Order).save(order);

      const pendingEvents = order.getUncommittedEvents();
      const outboxRows = pendingEvents.map((e) => ({
        aggregateType: 'Order',
        aggregateId: order.id,
        eventType: e.constructor.name,
        payload: JSON.stringify(e),
        createdAt: new Date(),
        publishedAt: null,
      }));

      await manager.getRepository(OutboxEvent).save(outboxRows);

      order.uncommit();
      return order.id;
    });
  }
}
```

여기서 `order.commit()`을 호출하지 않는 게 핵심이다. 도메인 이벤트는 outbox 테이블에 직렬화되어 들어가고, 인메모리 EventBus는 거치지 않는다. 트랜잭션이 커밋되면 outbox row가 영구화된다.

### Outbox Relay

별도 워커가 outbox 테이블을 폴링한다.

```ts
@Injectable()
export class OutboxRelay {
  constructor(
    private readonly outboxRepo: Repository<OutboxEvent>,
    private readonly broker: KafkaProducer,
  ) {}

  @Interval(1000)
  async relay() {
    const batch = await this.outboxRepo.find({
      where: { publishedAt: IsNull() },
      take: 100,
      order: { createdAt: 'ASC' },
    });

    for (const row of batch) {
      try {
        await this.broker.publish(row.eventType, row.payload, {
          key: row.aggregateId,
        });
        row.publishedAt = new Date();
        await this.outboxRepo.save(row);
      } catch (err) {
        this.logger.error(`relay failed for ${row.id}`, err);
        break;
      }
    }
  }
}
```

이 단순한 폴링도 알아야 할 함정이 있다.

**중복 발행은 피할 수 없다.** Relay가 publish는 성공했는데 publishedAt 업데이트 직전에 죽으면, 다음 사이클에서 같은 이벤트를 다시 발행한다. 그래서 consumer 쪽은 항상 idempotent해야 한다. 이벤트에 unique한 event_id를 박고, consumer가 이미 처리한 event_id를 기록해두는 식으로 처리한다.

**순서 보장이 까다롭다.** Aggregate ID를 Kafka 파티션 키로 쓰면 같은 주문의 이벤트는 순서대로 도착한다. 하지만 outbox에서 select할 때 createdAt만 보고 정렬하면, 동시에 들어온 이벤트의 순서가 흔들릴 수 있다. 보통 outbox PK(auto increment)나 sequence를 보조 키로 같이 정렬한다.

**여러 워커가 동시에 polling하면 같은 row를 두 번 처리한다.** 단일 워커만 띄우거나, `SELECT ... FOR UPDATE SKIP LOCKED`로 row 단위 락을 잡고 가져오는 방식을 쓴다. PostgreSQL이 표준이고, MySQL은 8.0+에서 지원한다.

**outbox 테이블이 무한히 자란다.** publishedAt이 일정 시간 지난 row를 별도 잡으로 삭제하거나, partitioned table로 운영한다. 한 달치 outbox가 수억 건이 되면 select 성능이 떨어지기 시작한다.

### CDC 방식의 Outbox

폴링이 부담스러우면 Debezium 같은 CDC(Change Data Capture) 도구로 outbox 테이블의 WAL을 직접 Kafka로 흘려보내는 방법도 있다. 애플리케이션은 그냥 INSERT만 하면 되고, 발행은 인프라 레이어에서 처리한다. Polling latency도 줄고 부하도 줄지만, 운영 복잡도가 한 단계 올라간다. 트래픽이 충분히 크고 latency 요구가 빡빡할 때 검토할 옵션이다.

## Event Emitter와 CQRS, 언제 뭘 쓰나

| 상황 | 도구 |
|---|---|
| 같은 모듈 안에서 사이드이펙트 분리 | EventEmitter |
| 인증 로그, 메트릭, 디버그 트레이서 | EventEmitter (wildcard) |
| 트랜잭션 내부에서 일관성 있게 실행돼야 함 | CQRS (동기 EventBus) |
| 도메인 모델과 인프라 분리가 필요한 복잡한 비즈니스 로직 | CQRS |
| 여러 단계의 이벤트 시퀀스를 한 곳에서 보고 싶음 | CQRS Saga |
| 이벤트가 절대 유실되면 안 되고 다른 서비스도 받아야 함 | CQRS + Outbox + 외부 브로커 |

둘을 같이 쓰는 게 자연스러운 경우도 있다. CQRS로 도메인 이벤트를 발행하고, 그중 일부는 outbox로 외부에 흘리고, 일부는 EventEmitter로 같은 모듈 내 가벼운 후처리를 시키는 식이다. 한 가지 안티패턴은 EventEmitter로 도메인 이벤트를 발행하고 그걸 받아서 또 다른 EventEmitter 이벤트를 발행하는 체인을 만드는 것이다. 이런 흐름은 디버깅이 지옥이 된다. 도메인 이벤트는 도메인 객체에 묶고 CQRS로 발행하라.

## 실무에서 자주 마주치는 문제들

**EventBus.publish가 silent하게 실패한다.** CQRS EventBus는 핸들러 에러를 기본적으로 swallow한다. 핸들러 안에서 throw가 발생해도 dispatch 측은 모른다. Saga가 같은 이벤트를 구독하고 있다면 Command까지 영향이 갈 수 있어서 더 헷갈린다. 모든 EventHandler를 try/catch로 감싸서 명시적으로 로깅하는 규칙을 두는 게 안전하다.

**`@Saga()`가 동작하지 않는다.** Saga 클래스가 모듈 providers에 등록 안 됐거나, `CqrsModule.forRoot()`를 import 안 한 경우다. CqrsModule은 한 번만 등록하면 되지만 깜빡 잊기 쉽다.

**`mergeObjectContext` 없이 `apply()`가 호출되면 이벤트가 사라진다.** `Order.create()`가 인스턴스를 그냥 반환하면 `publisher`가 모르는 객체라서 commit해도 EventBus에 안 흘러간다. 도메인 객체 생성은 반드시 `publisher.mergeObjectContext()` 또는 `publisher.mergeClassContext()`로 감싸야 한다.

**Outbox 테이블이 hot spot이 된다.** 모든 트랜잭션이 outbox에 INSERT하므로 동시성이 높으면 인덱스 락 경합이 생긴다. publishedAt 컬럼에 partial index(WHERE published_at IS NULL)를 걸면 relay 쿼리는 빠르지만 INSERT 비용은 그대로다. 트래픽이 정말 많으면 outbox 테이블을 aggregate type별로 분리하거나 sharding한다.

**Saga에서 무한 루프가 생긴다.** "OrderCreated → DeductInventory → InventoryDeducted → UpdateOrderStatus → OrderUpdated"가 다시 어떤 핸들러를 트리거하면서 OrderCreated가 또 발행되는 흐름. RxJS 스트림 특성상 디버깅하기 어렵다. Saga에서 발행한 Command가 다시 같은 Saga의 입력 이벤트를 만들지 않는지 확인하는 게 첫걸음이다.

이 정도가 NestJS 이벤트/CQRS 스택에서 실제로 마주치는 문제들이다. 도구 자체는 깔끔한데, 도메인 이벤트의 의미론과 트랜잭션 경계를 머릿속에 정리해두지 않으면 어디서 무엇이 발행되고 누가 받는지 추적이 안 되는 상태로 빠진다. Outbox 패턴은 처음에는 과해 보여도, 한 번 데이터 정합성 사고가 나고 나면 결국 그 자리에 도착한다.
