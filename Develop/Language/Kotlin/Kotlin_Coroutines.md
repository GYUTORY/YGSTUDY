---
title: Kotlin 코루틴
tags: [kotlin, language]
updated: 2026-07-16
---

# Kotlin 코루틴

## 개요

코루틴을 처음 접하면 "스레드가 아닌데 어떻게 동시에 실행되지?"라는 의문이 생긴다. 코루틴은 스레드 위에서 동작하는 경량 실행 단위다. 수십만 개를 만들어도 메모리 문제가 없는 이유는 OS 스레드를 점유하지 않고, 일시 정지 지점에서 스레드를 반납하기 때문이다.

핵심은 `suspend` 키워드다. `suspend` 함수는 실행 도중 일시 정지할 수 있고, 정지 시점의 상태를 저장했다가 재개된다. 이 동작이 어떻게 구현되는지 이해하면 코루틴의 나머지 개념들이 자연스럽게 따라온다.

---

## 1. suspend 함수의 실제 동작

`suspend` 함수는 컴파일 시 상태 머신으로 변환된다. 소스 코드에서는 직관적으로 보이지만 바이트코드 수준에서는 전혀 다른 구조가 된다.

```kotlin
suspend fun fetchUser(id: Long): User {
    val token = getToken()          // 일시 정지 지점 1
    val user = callApi(token, id)   // 일시 정지 지점 2
    return user
}
```

이 함수는 컴파일 후 대략 다음과 같은 구조가 된다.

```kotlin
// 컴파일 후 (개념적 표현)
fun fetchUser(id: Long, continuation: Continuation<User>): Any {
    val sm = continuation as? FetchUserStateMachine ?: FetchUserStateMachine(continuation)
    
    when (sm.label) {
        0 -> {
            sm.label = 1
            val result = getToken(sm)
            if (result == COROUTINE_SUSPENDED) return COROUTINE_SUSPENDED
            sm.token = result as String
        }
        1 -> {
            sm.token = sm.result as String
            sm.label = 2
            val result = callApi(sm.token, id, sm)
            if (result == COROUTINE_SUSPENDED) return COROUTINE_SUSPENDED
        }
        2 -> {
            return sm.result as User
        }
    }
}
```

`label`이 현재 위치를 추적한다. `getToken()`에서 일시 정지가 발생하면 `COROUTINE_SUSPENDED`를 반환하고 스레드를 반납한다. 이후 `getToken()`이 완료되면 `label = 1`인 상태로 재개된다. 스택 프레임을 다시 쌓는 게 아니라 힙에 저장된 상태 머신 객체를 통해 재개하기 때문에 스레드가 필요 없다.

`Continuation`은 "이 지점 이후에 해야 할 일"을 담은 콜백이다. 콜백 지옥 없이 순차적 코드처럼 쓸 수 있는 이유가 컴파일러가 CPS(Continuation-Passing Style) 변환을 자동으로 해주기 때문이다.

---

## 2. launch vs async

둘 다 새로운 코루틴을 시작하지만 결과 처리 방식이 다르다.

`launch`는 결과를 반환하지 않는다. `Job`을 반환하는데, 이걸로 완료 대기나 취소만 할 수 있다.

```kotlin
val job = launch {
    sendNotification(userId)  // 결과가 필요 없는 작업
}
job.join()  // 완료까지 대기
```

`async`는 결과가 필요할 때 쓴다. `Deferred<T>`를 반환하고 `.await()`로 결과를 가져온다.

```kotlin
val deferred = async {
    fetchUserProfile(userId)
}
val profile = deferred.await()
```

두 API를 병렬로 호출하는 패턴이 실무에서 자주 나온다.

```kotlin
suspend fun loadDashboard(userId: Long): Dashboard {
    val profileDeferred = async { fetchProfile(userId) }
    val ordersDeferred = async { fetchOrders(userId) }
    val notificationsDeferred = async { fetchNotifications(userId) }
    
    return Dashboard(
        profile = profileDeferred.await(),
        orders = ordersDeferred.await(),
        notifications = notificationsDeferred.await()
    )
}
```

순차 호출이면 세 API 호출의 시간이 더해지지만, 이렇게 병렬로 실행하면 가장 느린 API 하나의 시간만 걸린다.

주의할 점이 있다. `async` 블록 내부에서 예외가 발생하면 `.await()` 호출 시점까지 예외가 전파되지 않는다. `await()` 없이 `Deferred`를 버리면 예외가 조용히 사라진다.

```kotlin
// 위험한 패턴
val deferred = async { riskyOperation() }
// deferred.await()를 호출하지 않으면 예외가 무시됨

// 안전한 패턴
try {
    val result = async { riskyOperation() }.await()
} catch (e: Exception) {
    // 예외 처리
}
```

`launch`는 예외가 즉시 부모로 전파되는 반면 `async`는 `.await()` 시점에 전파된다. 이 차이를 모르면 예외가 사라지는 버그를 만나게 된다.

---

## 3. CoroutineScope와 구조적 동시성

구조적 동시성은 코루틴의 핵심 설계 원칙이다. 코루틴은 반드시 특정 스코프 안에서 시작되고, 그 스코프가 끝날 때 자식 코루틴들도 모두 완료되어야 한다.

Job 트리를 직접 보면 이해가 빠르다.

```
CoroutineScope
    └── Job (부모)
        ├── Job A (자식)
        │   └── Job A-1 (손자)
        └── Job B (자식)
```

부모 Job이 취소되면 A, A-1, B가 모두 취소된다. A-1에서 예외가 발생하면 A로 전파되고 A에서 부모로 전파되어 B도 취소된다.

```kotlin
class UserRepository(private val scope: CoroutineScope) {
    
    fun startSync() {
        scope.launch {
            while (true) {
                syncData()
                delay(60_000)
            }
        }
    }
}
```

`scope`가 취소되면 `while` 루프도 멈춘다. `delay()`는 취소 가능한 suspend 함수이기 때문에 취소 신호를 받으면 즉시 `CancellationException`을 던진다.

취소 전파에서 자주 실수하는 부분이 있다. `CancellationException`을 잡아서 무시하면 취소가 전파되지 않는다.

```kotlin
// 잘못된 패턴 - 취소를 막아버림
launch {
    try {
        longRunningOperation()
    } catch (e: Exception) {  // CancellationException도 잡힘
        logger.error("error", e)
        // 여기서 rethrow를 안 하면 취소가 무시됨
    }
}

// 올바른 패턴
launch {
    try {
        longRunningOperation()
    } catch (e: CancellationException) {
        throw e  // 반드시 재던져야 함
    } catch (e: Exception) {
        logger.error("error", e)
    }
}
```

`SupervisorJob`은 자식 중 하나가 실패해도 나머지 자식에게 영향을 주지 않는다. 독립적인 여러 작업을 동시에 실행하면서 하나가 실패해도 나머지는 계속 돌아야 할 때 쓴다.

```kotlin
val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

scope.launch { task1() }  // 실패해도
scope.launch { task2() }  // 이건 계속 실행됨
scope.launch { task3() }  // 이것도 마찬가지
```

일반 `Job`을 쓰면 `task1()`이 실패할 때 `task2()`, `task3()`도 취소된다.

---

## 4. Dispatcher별 스레드 모델

Dispatcher는 코루틴이 어느 스레드에서 실행될지 결정한다.

**Dispatchers.Default**는 CPU 집약적 작업용이다. 스레드 수가 CPU 코어 수와 같다(최소 2). 정렬, 압축, 암호화, 이미지 처리처럼 계산이 많은 작업에 쓴다. I/O 작업을 여기서 실행하면 스레드가 블로킹되어 다른 코루틴이 실행을 못 한다.

**Dispatchers.IO**는 블로킹 I/O용이다. 기본 스레드 수는 64개(또는 CPU 코어 수 중 큰 값)이고 `kotlinx.coroutines.io.parallelism` 시스템 프로퍼티로 조정 가능하다. JDBC, 파일 I/O, 레거시 블로킹 API를 쓸 때 사용한다.

**Dispatchers.Main**은 Android나 JavaFX의 UI 스레드다. 서버 사이드에서는 직접 쓸 일이 거의 없다.

**Dispatchers.Unconfined**는 호출한 스레드에서 시작하고 일시 정지 후 재개할 때 재개를 시켜준 스레드에서 계속 실행된다. 예측하기 어렵기 때문에 실무에서 쓰지 않는 것이 좋다.

```kotlin
// CPU 작업
withContext(Dispatchers.Default) {
    heavyComputation()
}

// 블로킹 I/O
withContext(Dispatchers.IO) {
    jdbcRepository.findById(id)  // JDBC는 블로킹
}

// 커스텀 Dispatcher
val customDispatcher = Executors.newFixedThreadPool(10).asCoroutineDispatcher()
withContext(customDispatcher) {
    thirdPartyBlockingLib.call()
}
```

`withContext()`는 현재 코루틴의 컨텍스트를 전환하고 블록이 끝나면 원래 컨텍스트로 돌아온다. 새 코루틴을 만들지 않기 때문에 `launch(Dispatchers.IO) { }` 보다 `withContext(Dispatchers.IO) { }` 패턴이 Dispatcher 전환에 더 적합하다.

---

## 5. Flow와 채널

**Flow**는 콜드 스트림이다. 구독자가 없으면 아무것도 실행되지 않는다. 매 구독마다 새 데이터 생산이 시작된다.

```kotlin
fun getTemperatureReadings(): Flow<Double> = flow {
    while (true) {
        emit(sensor.read())
        delay(1000)
    }
}

// 구독 전까지 sensor.read()는 호출되지 않음
val readings = getTemperatureReadings()

// 여기서 실행 시작
readings.collect { temp ->
    println("$temp°C")
}
```

Flow는 단일 소비자 패턴에 적합하다. 한 생산자의 데이터를 한 소비자가 처리하는 파이프라인 구조다.

**Channel**은 핫 스트림이다. 구독자와 무관하게 데이터가 생산된다. 여러 생산자, 여러 소비자 패턴을 지원한다.

```kotlin
val channel = Channel<Int>(capacity = 10)

// 생산자 (별도 코루틴)
launch {
    for (i in 1..100) {
        channel.send(i)
    }
    channel.close()
}

// 소비자 (별도 코루틴)
launch {
    for (value in channel) {
        processValue(value)
    }
}
```

실무에서 둘을 구분하는 기준은 단순하다. 데이터를 요청할 때마다 새로 생산해야 하면 Flow, 이미 생산된 데이터를 여러 소비자가 나눠 처리해야 하면 Channel이다.

Flow 연산자 조합은 강력하지만 함정이 있다. `collect`가 아닌 `launchIn`을 쓸 때 스코프 관리를 놓치면 메모리 누수가 생긴다.

```kotlin
// 위험한 패턴
flow.launchIn(GlobalScope)  // GlobalScope는 취소되지 않음

// 안전한 패턴
flow.launchIn(viewModelScope)  // 스코프가 취소되면 수집도 멈춤
```

`SharedFlow`와 `StateFlow`는 Flow와 Channel의 중간 형태다. `SharedFlow`는 여러 수집자에게 동시에 값을 방출하고, `StateFlow`는 마지막 값을 유지하면서 새 수집자에게 즉시 제공한다. 서버 사이드에서는 상태 공유나 이벤트 브로드캐스트에 쓴다.

---

## 6. Java 21 가상 스레드와 코루틴의 차이

Java 21 가상 스레드(Virtual Threads)가 나오면서 "코루틴 대신 가상 스레드 쓰면 되는 거 아니야?"라는 질문이 생겼다. 둘 다 블로킹 코드를 효율적으로 실행할 수 있지만 작동 방식과 적합한 상황이 다르다.

**가상 스레드**는 JVM 수준의 경량 스레드다. 기존 블로킹 코드를 수정 없이 사용할 수 있다. `Thread.sleep()`, JDBC, `InputStream.read()` 같은 블로킹 호출이 발생하면 JVM이 자동으로 플랫폼 스레드에서 분리한다.

```java
// Java - 가상 스레드
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> {
        var conn = dataSource.getConnection();  // 블로킹, 자동 처리
        // 기존 JDBC 코드 그대로
    });
}
```

**코루틴**은 언어 수준의 비동기 추상화다. `suspend` 함수로 비동기를 명시적으로 표현하고, 컴파일러가 상태 머신으로 변환한다. 취소, 구조적 동시성, Flow 같은 고수준 추상화를 제공한다.

```kotlin
// Kotlin - 코루틴
suspend fun processRequest() {
    val data = withContext(Dispatchers.IO) {
        repository.findData()  // 블로킹 JDBC
    }
    val result = computeResult(data)  // Default Dispatcher에서 실행
    saveResult(result)
}
```

실질적 차이를 정리하면:

가상 스레드는 기존 블로킹 코드 재사용이 가능하다. 레거시 코드를 거의 수정 없이 스케일링할 수 있다는 게 가장 큰 장점이다. 단, 취소 메커니즘이 코루틴보다 거칠다. `Thread.interrupt()`를 써야 하는데 블로킹 연산마다 인터럽트 처리 여부가 다르다.

코루틴은 취소가 협력적이다. `CancellationException`을 통해 취소 신호가 전파되고, `delay()`, `yield()`, `withContext()` 같은 suspend 포인트에서 취소가 발생한다. 구조적 동시성으로 리소스 누수를 방지하는 것도 코루틴이 더 체계적이다.

현실적으로 Java 21 가상 스레드는 Spring MVC 같은 스레드당 요청 모델에서 쓰기 좋고, 코루틴은 Kotlin 프로젝트에서 비동기 로직을 조합할 때 더 자연스럽다. 둘을 섞을 수도 있다. 가상 스레드 풀을 Dispatcher로 만들어서 코루틴 내에서 블로킹 코드를 실행하는 패턴도 동작한다.

```kotlin
// 가상 스레드를 코루틴 Dispatcher로 사용
val virtualThreadDispatcher = Executors
    .newVirtualThreadPerTaskExecutor()
    .asCoroutineDispatcher()

withContext(virtualThreadDispatcher) {
    legacyBlockingService.call()
}
```

---

## 7. Spring WebFlux 없이 코루틴으로 논블로킹 서버 구현 시 주의사항

Spring MVC에 코루틴을 붙이는 방식이 Spring WebFlux보다 쉬운 진입점이다. Spring 5.2부터 `suspend` 함수를 컨트롤러 메서드로 쓸 수 있다.

```kotlin
@RestController
class UserController(private val userService: UserService) {
    
    @GetMapping("/users/{id}")
    suspend fun getUser(@PathVariable id: Long): User {
        return userService.findById(id)
    }
    
    @GetMapping("/users/{id}/dashboard")
    suspend fun getDashboard(@PathVariable id: Long): Dashboard {
        return coroutineScope {
            val profile = async { userService.getProfile(id) }
            val orders = async { orderService.getOrders(id) }
            Dashboard(profile.await(), orders.await())
        }
    }
}
```

Spring MVC + 코루틴 조합에서 반드시 알아야 하는 주의사항들이 있다.

**JDBC는 여전히 블로킹이다.** Spring MVC + 코루틴을 써도 JDBC 호출은 스레드를 블로킹한다. `withContext(Dispatchers.IO) { }` 안에서 실행해야 한다. R2DBC로 바꾸거나 Dispatchers.IO를 써야 진짜 논블로킹이 된다.

```kotlin
@Service
class UserService(private val userRepository: UserRepository) {
    
    suspend fun findById(id: Long): User {
        return withContext(Dispatchers.IO) {
            userRepository.findById(id)  // JDBC - 블로킹
                ?: throw NotFoundException("User $id not found")
        }
    }
}
```

**트랜잭션 관리**는 복잡하다. Spring의 `@Transactional`은 스레드 로컬로 트랜잭션 컨텍스트를 관리한다. 코루틴은 스레드를 전환하기 때문에 스레드 로컬이 유실될 수 있다. `spring-tx` 5.2 이후에서 `TransactionSynchronizationManager`를 코루틴 컨텍스트에 연결하는 지원이 추가됐지만, `withContext()`로 Dispatcher를 바꾸면 트랜잭션이 끊길 수 있다.

```kotlin
// 위험한 패턴
@Transactional
suspend fun updateUser(id: Long, data: UserData) {
    val user = withContext(Dispatchers.IO) {  // Dispatcher 전환 시 트랜잭션 컨텍스트 유실 가능
        userRepository.findById(id)
    }
    user.update(data)
    withContext(Dispatchers.IO) {
        userRepository.save(user)  // 같은 트랜잭션이 아닐 수 있음
    }
}

// 더 안전한 패턴 - 트랜잭션 전체를 IO에서 실행
@Transactional
suspend fun updateUser(id: Long, data: UserData) {
    withContext(Dispatchers.IO) {
        val user = userRepository.findById(id)
        user.update(data)
        userRepository.save(user)
    }
}
```

**예외 처리와 컨텍스트 전파.** `CoroutineExceptionHandler`는 `launch`에서 처리되지 않은 예외를 잡는다. `async`에서는 `.await()` 호출 시점에 예외가 터지기 때문에 `CoroutineExceptionHandler`가 잡지 않는다. Spring의 `@ExceptionHandler`는 suspend 함수에서 던진 예외를 잡을 수 있지만, 코루틴 내부에서 다른 스코프로 분리된 경우에는 잡지 못한다.

**MDC(Mapped Diagnostic Context)**도 스레드 로컬 기반이라서 코루틴에서 로그에 사용자 ID나 요청 ID가 사라지는 문제가 생긴다.

```kotlin
// MDC가 코루틴에서 사라지는 문제 해결
suspend fun processWithMdc(requestId: String) {
    withContext(MDCContext()) {  // kotlinx-coroutines-slf4j 라이브러리 필요
        MDC.put("requestId", requestId)
        doWork()
    }
}
```

`kotlinx-coroutines-slf4j` 라이브러리의 `MDCContext()`를 쓰면 코루틴 컨텍스트 전환 시 MDC가 복원된다.

**무한 루프나 긴 작업에서 취소 포인트 확보.** CPU를 오래 점유하는 작업은 `yield()`나 `ensureActive()`를 중간에 넣어야 취소 신호를 받을 수 있다.

```kotlin
suspend fun processLargeDataset(items: List<Item>) {
    for ((index, item) in items.withIndex()) {
        processItem(item)
        
        if (index % 100 == 0) {
            yield()  // 취소 포인트 - 100개마다 취소 신호 확인
        }
    }
}
```

`delay(0)`도 같은 효과가 있지만 `yield()`가 의도를 더 명확하게 드러낸다.

**스코프 선택.** Spring 컨트롤러에서 `GlobalScope.launch { }`는 쓰지 말아야 한다. 요청이 취소됐거나 서버가 종료될 때도 작업이 계속 실행된다. `CoroutineScope(Dispatchers.IO + Job())`를 빈으로 등록하고 `@PreDestroy`에서 `.cancel()`을 호출하거나, Spring이 관리하는 스코프를 쓰는 것이 맞다.

```kotlin
@Configuration
class CoroutineConfig {
    
    @Bean
    fun applicationScope(): CoroutineScope {
        return CoroutineScope(SupervisorJob() + Dispatchers.Default)
    }
}

// Spring Context가 닫힐 때 자동 정리를 원한다면
@Component
class ApplicationScopeLifecycle(
    private val scope: CoroutineScope
) : DisposableBean {
    override fun destroy() {
        scope.cancel()
    }
}
```
