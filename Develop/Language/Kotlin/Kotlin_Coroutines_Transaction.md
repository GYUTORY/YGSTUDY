---
title: 코루틴 환경에서의 DB 트랜잭션
tags: [kotlin, coroutine, transaction, spring, r2dbc, flow, threadlocal, transactional, suspend, jpa]
updated: 2026-07-30
---

# 코루틴 환경에서의 DB 트랜잭션

## 개요

Spring에서 `@Transactional`을 suspend 함수에 붙이면 컴파일 오류가 없다. 잘 동작하는 줄 알고 쓰다가, 특정 조건에서 트랜잭션이 묶이지 않거나 롤백이 안 되는 상황을 만난다. 문제는 Spring 트랜잭션 매니저가 ThreadLocal에 기반한다는 점에서 시작된다.

---

## 1. ThreadLocal과 코루틴의 충돌

Spring 트랜잭션 매니저는 현재 트랜잭션 정보를 `TransactionSynchronizationManager`의 ThreadLocal에 저장한다. 같은 스레드 위에서 실행되는 한 DB 커넥션이 공유되고, 트랜잭션 경계가 유지된다.

코루틴은 suspend 지점에서 현재 스레드를 반납한다. 재개될 때 같은 스레드를 받는다는 보장이 없다. `Dispatchers.IO`처럼 스레드 풀을 쓰는 디스패처에서는 일시 정지 전후로 스레드가 자주 바뀐다.

```
Thread-1: 트랜잭션 시작 → ThreadLocal에 Connection 저장
suspend 지점 도달: Thread-1 반납
Thread-2: 코루틴 재개 → Thread-2의 ThreadLocal 조회 → null
```

결과적으로 트랜잭션 컨텍스트가 없는 스레드 위에서 쿼리가 실행된다. Spring 설정에 따라 `TransactionRequiredException`이 발생하거나, 트랜잭션 없이 auto-commit으로 실행된다.

---

## 2. @Transactional을 suspend 함수에 붙이면 생기는 일

Spring 5.2부터 코루틴 지원을 일부 추가했다. `@Transactional`이 붙은 suspend 함수를 AOP 프록시가 감지하고, `CoroutinesUtils`를 거쳐 트랜잭션을 처리한다. suspend 지점 없이 단일 스레드에서 실행이 끝나는 경우에는 동작한다.

문제는 내부에서 `withContext`로 디스패처를 바꾸거나, 여러 suspend 지점을 거치는 경우다.

```kotlin
@Transactional
suspend fun createOrder(userId: Long, items: List<Item>): Order {
    val user = userRepository.findById(userId)  // 트랜잭션 있음

    val enrichedItems = withContext(Dispatchers.IO) {
        // 여기서 스레드가 바뀔 수 있음
        // 이 블록이 끝나고 돌아왔을 때 트랜잭션 컨텍스트가 있다는 보장이 없음
        items.map { enrichWithInventory(it) }
    }

    return orderRepository.save(Order(user, enrichedItems))  // 어떤 스레드?
}
```

`Dispatchers.IO` 블록 이후에 실행되는 `orderRepository.save`가 어떤 스레드에서 돌지 예측하기 어렵다. 로컬에서는 우연히 같은 스레드가 배정돼 동작하다가, 운영에서 부하가 걸리면 다른 스레드로 배정되며 트랜잭션이 끊긴다. 재현이 어렵고 원인 추적에 시간이 걸린다.

---

## 3. coroutineScope 내부에서 트랜잭션이 끊기는 사례

`coroutineScope`는 자식 코루틴들이 완료될 때까지 대기하지만, 자식 코루틴들은 각각 독립적으로 실행된다. 자식이 어떤 스레드에서 실행될지는 사용하는 디스패처와 스케줄러에 달려 있다.

```kotlin
@Transactional
suspend fun processOrders(orderIds: List<Long>) {
    coroutineScope {
        orderIds.map { id ->
            launch {
                // 각 launch는 별도 코루틴
                // 부모가 Thread-1에서 트랜잭션을 시작했어도
                // 이 코루틴은 Thread-2, Thread-3...에서 실행될 수 있음
                orderRepository.updateStatus(id, OrderStatus.PROCESSING)
            }
        }
    }
}
```

각 `launch`가 트랜잭션 없는 상태에서 실행되면 auto-commit으로 날아간다. 중간에 예외가 발생해도 이미 커밋된 항목들은 롤백되지 않는다. 일부만 상태가 바뀐 채로 남는 데이터 불일치가 생긴다.

`Dispatchers.Default`를 별도로 지정하지 않아도 `launch`가 기본적으로 부모의 디스패처를 상속받기 때문에 로컬에서 단건 테스트할 때는 통과할 수 있다. 건수가 늘어나 스레드 풀 경쟁이 생기면 터진다.

---

## 4. JDBC/JPA 환경 해결: TransactionTemplate

JDBC/JPA 환경에서 코루틴과 트랜잭션을 함께 쓸 때 가장 안전한 방법은 `TransactionTemplate`을 직접 사용하고, 트랜잭션 블록 안에서 suspend 호출을 하지 않는 것이다.

```kotlin
@Service
class OrderService(
    private val transactionTemplate: TransactionTemplate,
    private val userRepository: UserRepository,
    private val orderRepository: OrderRepository,
) {
    suspend fun createOrder(userId: Long, items: List<Item>): Order {
        return withContext(Dispatchers.IO) {
            transactionTemplate.execute {
                // 이 블록은 일반 람다 — suspend 호출 불가
                // withContext(Dispatchers.IO) 덕분에 단일 스레드에 고정
                // ThreadLocal 컨텍스트가 블록 전체에서 유지됨
                val user = userRepository.findById(userId).orElseThrow()
                orderRepository.save(Order(user = user, items = items))
            }!!
        }
    }
}
```

`withContext(Dispatchers.IO)` 안에서 `transactionTemplate.execute`를 호출하면 해당 블록은 Dispatchers.IO의 스레드에서 동기적으로 실행된다. `execute` 람다는 일반 함수라 suspend 함수를 직접 호출할 수 없고, 그 덕분에 트랜잭션 범위 안에서 스레드가 바뀔 가능성이 없다.

병렬 처리가 필요하면 트랜잭션 밖에서 처리하고, DB 쓰기만 트랜잭션으로 감싼다.

```kotlin
suspend fun createOrderWithParallelFetch(userId: Long, items: List<Item>): Order {
    // 외부 API 호출 등 트랜잭션이 필요 없는 작업은 밖에서 병렬 처리
    val (user, enrichedItems) = coroutineScope {
        val userDeferred = async { fetchUserFromApi(userId) }
        val itemsDeferred = async { enrichItemsFromInventory(items) }
        userDeferred.await() to itemsDeferred.await()
    }

    // DB 쓰기만 트랜잭션으로 묶음
    return withContext(Dispatchers.IO) {
        transactionTemplate.execute {
            orderRepository.save(Order(user = user, items = enrichedItems))
        }!!
    }
}
```

coroutineScope 안에서 여러 쿼리를 하나의 트랜잭션으로 묶어야 하는 경우라면, `withContext(Dispatchers.IO)` 안에서 순차적으로 처리해야 한다. 병렬성을 포기하거나, 각 쿼리를 독립 트랜잭션으로 분리하는 방향 중 하나를 선택해야 한다.

---

## 5. TransactionTemplate 롤백 누락 사례

`TransactionTemplate`을 코루틴 안에서 쓸 때 가장 자주 마주치는 문제는 예외를 잡아서 처리했는데 트랜잭션이 롤백되지 않고 커밋되는 것이다.

`TransactionTemplate.execute`는 람다 안에서 `RuntimeException`이나 `Error`가 던져졌을 때만 자동으로 롤백한다. 람다가 정상적으로 반환하면 — 예외를 잡아서 `null`을 돌려줬더라도 — 트랜잭션을 커밋한다.

```kotlin
suspend fun createOrder(userId: Long): Order? {
    return withContext(Dispatchers.IO) {
        transactionTemplate.execute { status ->
            try {
                val order = orderRepository.save(Order(userId = userId))
                paymentService.charge(order)  // RuntimeException 발생
                order
            } catch (e: RuntimeException) {
                log.error("결제 실패", e)
                // null을 반환하면 트랜잭션이 커밋된다
                // order 레코드가 DB에 남은 채로 커밋됨
                null
            }
        }
    }
}
```

예외를 잡아 처리하면서 롤백도 해야 하는 경우에는 `TransactionStatus.setRollbackOnly()`를 명시적으로 호출해야 한다.

```kotlin
transactionTemplate.execute { status ->
    try {
        val order = orderRepository.save(Order(userId = userId))
        paymentService.charge(order)
        order
    } catch (e: RuntimeException) {
        log.error("결제 실패", e)
        status.setRollbackOnly()  // 명시적 롤백 마킹
        null
    }
}
```

코루틴 취소(`CancellationException`)가 `execute` 블록 안에서 발생하는 경우도 조심해야 한다. `CancellationException`은 `RuntimeException`을 상속하므로 `TransactionTemplate`이 롤백한다. 하지만 `execute` 내부에서 `try-catch`로 `Exception`을 전부 잡으면 `CancellationException`도 같이 삼켜진다. 코루틴이 취소됐는데 트랜잭션이 커밋되고, 취소 처리도 전파되지 않는다.

```kotlin
// 위험한 패턴
transactionTemplate.execute { _ ->
    try {
        orderRepository.save(Order(userId = userId))
    } catch (e: Exception) {  // CancellationException도 잡힘
        log.error("실패", e)
        null  // 코루틴이 취소됐는데 커밋됨, 취소도 전파 안 됨
    }
}

// 올바른 패턴
transactionTemplate.execute { status ->
    try {
        orderRepository.save(Order(userId = userId))
    } catch (e: CancellationException) {
        status.setRollbackOnly()
        throw e  // 코루틴 취소는 반드시 재전파
    } catch (e: RuntimeException) {
        log.error("실패", e)
        status.setRollbackOnly()
        null
    }
}
```

---

## 6. withContext(Dispatchers.IO) 내 트랜잭션 경계 문제

`withContext(Dispatchers.IO)` 블록과 `transactionTemplate.execute` 블록은 범위가 다르다. `withContext`는 코루틴 디스패처를 바꾸는 장치고, `transactionTemplate.execute`는 그 안에서 실행되는 동기 람다다. `execute`가 반환되는 순간 트랜잭션이 커밋 또는 롤백된다. `withContext` 블록이 끝나지 않았어도 트랜잭션은 이미 닫혔다.

```kotlin
withContext(Dispatchers.IO) {
    transactionTemplate.execute {
        orderRepository.save(Order(userId))
    }
    // ← 여기서 트랜잭션이 이미 커밋됨

    // execute 이후에 발생하는 예외는 커밋된 트랜잭션을 롤백하지 않음
    notificationService.send(orderId)  // 실패해도 order는 DB에 남음
}
```

이 구조에서 알림 발송이 실패하면 주문은 남고 알림만 빠진다. 주문과 알림을 원자적으로 처리하려면 알림 발송을 트랜잭션 범위 안에 포함하거나, 아웃박스 패턴으로 분리해야 한다.

`execute` 람다 안에서 비동기 작업이 필요해서 `runBlocking`을 쓰는 경우가 있다. `execute` 람다는 일반 함수라서 `withContext` 같은 suspend 함수를 직접 호출할 수 없기 때문이다.

```kotlin
// 위험한 패턴
transactionTemplate.execute {
    val order = orderRepository.save(Order(userId))

    // 재고 확인이 필요해서 runBlocking으로 suspend 함수 호출
    val stock = runBlocking {
        inventoryClient.check(order.itemId)  // 네트워크 호출
    }

    if (!stock.available) throw RuntimeException("재고 없음")
    order
}
```

`runBlocking`은 현재 Dispatchers.IO 스레드를 블로킹하면서 내부적으로 새 스레드를 만든다. 스레드 풀에 여유가 없으면 `inventoryClient.check`가 실행될 스레드를 기다리는 동안 Dispatchers.IO 스레드 전체가 묶인다. 이 상황이 겹치면 데드락이 된다.

네트워크 호출처럼 I/O가 필요한 작업은 트랜잭션 블록 바깥에서 처리해야 한다.

```kotlin
suspend fun createOrder(userId: Long, itemId: Long): Order {
    // 트랜잭션 바깥에서 재고 확인
    val stock = inventoryClient.check(itemId)
    if (!stock.available) throw IllegalStateException("재고 없음")

    // 확인 후 DB 쓰기만 트랜잭션으로 처리
    return withContext(Dispatchers.IO) {
        transactionTemplate.execute {
            orderRepository.save(Order(userId = userId, itemId = itemId))
        }!!
    }
}
```

`withContext` 안에 `transactionTemplate.execute`를 두 번 쓰면 각각 독립 트랜잭션이 된다. 첫 번째 `execute`가 커밋된 뒤 두 번째 `execute`에서 예외가 나면 첫 번째 커밋은 롤백되지 않는다.

```kotlin
withContext(Dispatchers.IO) {
    transactionTemplate.execute {
        orderRepository.save(order)  // 커밋됨
    }

    transactionTemplate.execute {
        paymentRepository.save(payment)  // 여기서 실패해도 order는 남음
    }
}
```

두 쓰기를 원자적으로 처리해야 한다면 하나의 `execute` 블록으로 묶어야 한다.

---

## 7. R2DBC + Flow 트랜잭션 범위

R2DBC는 리액티브 드라이버라 ThreadLocal을 쓰지 않는다. Reactor Context로 트랜잭션을 전파하고, 코루틴 컨텍스트와 Reactor Context 사이에 브릿지가 있어서 `@Transactional`이 suspend 함수에서 의도대로 동작한다.

```kotlin
@Service
class OrderService(
    private val orderRepository: R2dbcOrderRepository,
) {
    @Transactional  // R2DBC 환경에서는 이 조합이 안전하다
    suspend fun createOrder(userId: Long): Order {
        val existing = orderRepository.findByUserId(userId)
        // withContext로 디스패처를 바꿔도 Reactor Context가 함께 전파됨
        return orderRepository.save(Order(userId = userId))
    }
}
```

Flow를 반환하는 경우에는 트랜잭션 범위를 주의해야 한다. Flow는 cold stream이라서 `collect`가 호출되는 시점에 실제 DB 쿼리가 실행된다.

```kotlin
// 위험한 패턴
@Transactional
fun getOrdersFlow(userId: Long): Flow<Order> {
    // 트랜잭션 시작 시점: 함수 호출 시
    // 쿼리 실행 시점: 호출자가 collect할 때
    // 호출자가 다른 코루틴 스코프에서 collect하면 트랜잭션 범위를 벗어남
    return orderRepository.findByUserId(userId)
}
```

한 번에 결과가 필요하면 suspend 함수 안에서 collect한다.

```kotlin
@Transactional
suspend fun getOrdersList(userId: Long): List<Order> {
    return orderRepository.findByUserId(userId).toList()
}
```

트랜잭션 범위 안에서 Flow를 유지해야 한다면 `TransactionalOperator`를 사용한다.

```kotlin
@Service
class OrderService(
    private val transactionalOperator: TransactionalOperator,
    private val orderRepository: R2dbcOrderRepository,
) {
    fun getOrdersInTransaction(userId: Long): Flow<Order> {
        return orderRepository.findByUserId(userId)
            .`as`(transactionalOperator::transactional)
    }
}
```

`transactionalOperator::transactional`은 Flow 전체를 하나의 트랜잭션으로 감싼다. collect가 완료되거나 취소될 때 트랜잭션이 커밋 또는 롤백된다.

Flow를 반환하는 서비스 메서드에 `@Transactional`을 붙이는 것은 호출 구조가 예측 가능한 경우에만 의미가 있다. 서비스 레이어에서 결과를 List로 모아서 반환하거나, `TransactionalOperator`로 Flow 자체에 트랜잭션을 결합하는 쪽이 의도가 더 명확하다.

---

## 8. JPA 지연 로딩과 코루틴

JPA는 `EntityManager`를 ThreadLocal에 저장하고, 지연 로딩도 같은 ThreadLocal의 `EntityManager`에 의존한다. suspend 지점 이후에 지연 로딩 속성에 접근하면 `LazyInitializationException`이 아니라 `TransactionRequiredException`이 나오는 경우가 있다.

에러 메시지만 보면 `@Transactional`을 안 붙인 것처럼 보인다. 실제로는 트랜잭션은 시작됐지만, 스레드가 바뀌면서 ThreadLocal의 `EntityManager`가 현재 스레드의 것과 맞지 않아 생기는 문제다.

```kotlin
@Transactional
suspend fun processOrder(orderId: Long) {
    val order = orderRepository.findById(orderId).orElseThrow()
    // order.items는 FetchType.LAZY

    delay(100)  // suspend 지점 — 스레드 바뀔 수 있음

    order.items.forEach { item ->  // LazyInitializationException 또는 TransactionRequiredException
        processItem(item)
    }
}
```

suspend 함수 안에서 JPA를 쓸 때는 `withContext(Dispatchers.IO)` 하나의 블록 안에서 조회부터 지연 로딩 접근까지 전부 끝내야 한다.

```kotlin
suspend fun processOrder(orderId: Long) {
    withContext(Dispatchers.IO) {
        transactionTemplate.execute {
            val order = orderRepository.findById(orderId).orElseThrow()
            // 트랜잭션 블록 안에서 지연 로딩까지 완료
            order.items.forEach { item ->
                processItem(item)
            }
        }
    }
}
```

블록 밖으로 엔티티를 꺼낸 뒤 다른 suspend 함수를 거치고 나서 지연 로딩을 쓰면 터진다. 필요한 데이터를 미리 다 로딩하거나(Fetch Join), 응답 DTO로 변환해서 반환하는 방식으로 이 문제를 피한다.

### suspend 함수 체인에서의 지연 로딩 오류

단일 함수 안에서는 `withContext(Dispatchers.IO)` + `transactionTemplate`으로 지연 로딩 문제를 피할 수 있다. 하지만 suspend 함수가 여러 레이어를 거치면 트랜잭션 경계 안에서 초기화된 컬렉션이 함수 반환 후에 지연 로딩을 시도하는 상황이 생긴다.

```kotlin
// UserService
suspend fun getUser(userId: Long): User {
    return withContext(Dispatchers.IO) {
        transactionTemplate.execute {
            val user = userRepository.findById(userId).orElseThrow()
            user.orders  // orders는 트랜잭션 안에서 초기화됨 (List<Order>)
            // 각 Order의 items는 아직 LAZY 상태
            user
        }!!
    }
}

// OrderService
suspend fun processUserOrders(userId: Long) {
    val user = userService.getUser(userId)  // 트랜잭션 종료 후 User 반환

    delay(50)  // 다른 작업

    user.orders.forEach { order ->
        order.items.forEach { item ->  // LazyInitializationException
            // order.items는 Hibernate 프록시, 트랜잭션이 없는 스레드에서 접근
            processItem(item)
        }
    }
}
```

스택 트레이스는 `order.items`에 접근하는 줄을 가리킨다. `UserService`는 정상적으로 동작했기 때문에 `getUser`가 문제라는 단서가 없다. `user.orders` 컬렉션은 트랜잭션 안에서 초기화됐지만(프록시가 실제 데이터로 교체됨), 각 `Order.items`는 여전히 Hibernate 프록시 상태다. 트랜잭션이 닫힌 후 다른 스레드에서 이 프록시에 접근하면 예외가 발생한다.

해결 방법은 두 가지다.

트랜잭션 안에서 필요한 연관관계를 모두 강제 초기화한다.

```kotlin
suspend fun getUser(userId: Long): User {
    return withContext(Dispatchers.IO) {
        transactionTemplate.execute {
            val user = userRepository.findById(userId).orElseThrow()
            user.orders.forEach { order ->
                order.items.size  // size 접근으로 컬렉션 강제 초기화
            }
            user
        }!!
    }
}
```

또는 엔티티 대신 DTO로 변환해서 반환한다.

```kotlin
suspend fun getUserDto(userId: Long): UserDto {
    return withContext(Dispatchers.IO) {
        transactionTemplate.execute {
            val user = userRepository.findById(userId).orElseThrow()
            UserDto(
                id = user.id,
                name = user.name,
                orders = user.orders.map { order ->
                    OrderDto(
                        id = order.id,
                        items = order.items.map { ItemDto(it.id, it.name) }
                    )
                }
            )
        }!!
    }
}
```

DTO 변환이 트랜잭션 안에서 일어나므로 지연 로딩이 정상적으로 실행된다. 트랜잭션 밖으로는 프록시가 아닌 순수 데이터 객체만 나간다. suspend 함수가 여러 레이어를 거치더라도 지연 로딩 문제가 생기지 않는다.

---
이 문서는 [트랜잭션과 동시성 허브](../../_hub/트랜잭션과_동시성.md)의 일부입니다.
