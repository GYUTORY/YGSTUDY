---
title: Java 동시성 심화
tags: [java, concurrency, executor, completablefuture, lock, atomic, concurrent-collections, thread-pool]
updated: 2026-07-16
---

# Java 동시성 심화

## 개요

`Thread`와 `Runnable`로 직접 스레드를 다루는 방식은 실무에서 거의 쓰지 않는다. 스레드 생성 비용, 예외 처리, 리소스 정리까지 직접 챙겨야 하는데 놓치는 순간 OOM이나 데드락으로 이어진다. Java 5 이후로 `java.util.concurrent` 패키지가 이 문제를 상당 부분 해결했다.

동시성과 병렬성은 다른 개념이다. 동시성은 CPU 하나가 여러 작업을 번갈아 실행하는 것이고, 병렬성은 CPU 여러 개가 동시에 각각 작업을 실행하는 것이다. Java의 동시성 API는 둘 다 다루지만, 실무에서 마주치는 문제 대부분은 동시성에서 발생한다. 공유 자원에 여러 스레드가 접근할 때 생기는 레이스 컨디션, 데드락, 가시성 문제가 전형적인 사례다.

```
동시성 (Concurrency):
  CPU 1개가 여러 작업을 번갈아 실행 (시분할)
  Task A ──▶ ──▶     ──▶ ──▶
  Task B      ──▶ ──▶     ──▶

병렬성 (Parallelism):
  CPU 여러 개가 동시에 실행
  CPU1: Task A ──▶──▶──▶──▶
  CPU2: Task B ──▶──▶──▶──▶
```

---

## 1. ExecutorService

스레드를 직접 생성하는 코드가 루프 안에 있으면 요청마다 스레드가 생기고, 트래픽이 몰리는 순간 JVM이 OOM으로 죽는다. 스레드 하나가 기본으로 1MB 스택을 잡고 있기 때문에 수천 개 이상은 버티기 어렵다.

```java
// 스레드를 직접 생성하는 패턴 - 트래픽 몰리면 OOM
for (int i = 0; i < 1000; i++) {
    new Thread(() -> processRequest()).start();
}

// ExecutorService로 개수를 제한
ExecutorService executor = Executors.newFixedThreadPool(10);
for (int i = 0; i < 1000; i++) {
    executor.submit(() -> processRequest());
}
executor.shutdown();
```

### 팩토리 메서드 선택

| 팩토리 메서드 | 동작 | 적합한 경우 |
|-------------|------|-----------|
| `newFixedThreadPool(n)` | 고정 n개 스레드 | 일반적인 서버 워크로드 |
| `newCachedThreadPool()` | 필요 시 생성, 유휴 시 해제 | 짧은 비동기 작업 |
| `newSingleThreadExecutor()` | 스레드 1개, 순차 실행 | 순서 보장 필요 |
| `newScheduledThreadPool(n)` | 주기적/지연 실행 | 스케줄링 작업 |
| `newVirtualThreadPerTaskExecutor()` | 가상 스레드 (Java 21+) | 대량 I/O 작업 |

`newCachedThreadPool()`은 큐 크기 제한이 없고 스레드를 무제한 생성한다. 트래픽이 몰리면 결국 스레드 폭발이 일어난다. 프로덕션에서는 `ThreadPoolExecutor`를 직접 설정하는 쪽이 안전하다.

### 커스텀 ThreadPoolExecutor

```java
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10,                                      // corePoolSize: 기본 스레드 수
    50,                                      // maximumPoolSize: 최대 스레드 수
    60L, TimeUnit.SECONDS,                   // keepAliveTime: 유휴 스레드 생존 시간
    new LinkedBlockingQueue<>(100),          // 작업 큐 (크기 제한 필수)
    new ThreadPoolExecutor.CallerRunsPolicy()  // 거부 정책
);
```

큐 크기를 제한하지 않으면 작업이 무한정 쌓이다가 힙을 다 써버린다. `CallerRunsPolicy`는 큐가 가득 찼을 때 호출한 스레드가 직접 작업을 실행하게 만드는데, 이 덕분에 자연스러운 백프레셔가 걸린다. HTTP 요청을 처리하는 서블릿 스레드가 직접 실행을 떠안으면 새 요청 수락이 느려지고, 그게 연결 큐를 막아 클라이언트 쪽에서 타임아웃이 발생한다. 불쾌하지만 시스템 전체가 죽는 것보다는 낫다.

### 거부 정책

| 정책 | 동작 |
|------|------|
| `AbortPolicy` (기본) | `RejectedExecutionException` 던짐 |
| `CallerRunsPolicy` | 호출한 스레드가 직접 실행 |
| `DiscardPolicy` | 조용히 버림 |
| `DiscardOldestPolicy` | 큐에서 가장 오래된 작업 버림 |

### Spring 비동기 설정

```java
@Configuration
@EnableAsync
public class AsyncConfig {
    @Bean
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("async-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.initialize();
        return executor;
    }
}
```

`threadNamePrefix`를 설정해두면 스레드 덤프 분석 시 어느 풀인지 바로 식별된다. 설정 안 하면 `pool-1-thread-1` 같은 기본 이름이 붙어서 여러 풀이 섞인 덤프에서 구분하기 어렵다.

---

## 2. CompletableFuture

`Future.get()`은 블로킹이다. 결과가 올 때까지 스레드를 잡고 있기 때문에, 비동기 작업을 여러 개 체이닝하면 결국 스레드 자원을 낭비하게 된다. `CompletableFuture`는 콜백 기반으로 체이닝할 수 있어서 이 문제를 피할 수 있다.

```java
CompletableFuture.supplyAsync(() -> fetchUser(userId))
    .thenApply(user -> enrichWithProfile(user))
    .thenApply(user -> calculateDiscount(user))
    .thenAccept(user -> sendNotification(user))
    .exceptionally(ex -> {
        log.error("처리 실패", ex);
        return null;
    });
```

### 여러 비동기 작업 조합

```java
// 두 작업을 병렬로 실행 후 합치기
CompletableFuture<User> userFuture =
    CompletableFuture.supplyAsync(() -> fetchUser(id));
CompletableFuture<List<Order>> orderFuture =
    CompletableFuture.supplyAsync(() -> fetchOrders(id));

CompletableFuture<UserProfile> profileFuture = userFuture.thenCombine(
    orderFuture,
    (user, orders) -> new UserProfile(user, orders)
);

// 여러 작업 모두 완료 대기
CompletableFuture.allOf(task1, task2, task3).join();

// 가장 빠른 결과 사용
CompletableFuture<String> fastest = CompletableFuture.anyOf(
    fetchFromCache(), fetchFromDB(), fetchFromAPI()
).thenApply(Object::toString);
```

### 실전 예시: 주문 조회 API

```java
@Service
public class OrderService {

    public CompletableFuture<OrderDetail> getOrderDetail(Long orderId) {
        CompletableFuture<Order> orderFuture =
            CompletableFuture.supplyAsync(() -> orderRepository.findById(orderId));

        CompletableFuture<Payment> paymentFuture =
            CompletableFuture.supplyAsync(() -> paymentClient.getPayment(orderId));

        CompletableFuture<Delivery> deliveryFuture =
            CompletableFuture.supplyAsync(() -> deliveryClient.getDelivery(orderId));

        return orderFuture.thenCombine(paymentFuture, OrderDetail::withPayment)
                          .thenCombine(deliveryFuture, OrderDetail::withDelivery);
    }
}
```

### 자주 빠지는 함정

`supplyAsync()`의 기본 실행 풀은 `ForkJoinPool.commonPool()`이다. 이 풀은 CPU 코어 수에서 1을 뺀 크기로 동작한다. DB 호출이나 HTTP 호출처럼 I/O 바운드 작업을 여기 넣으면 풀을 금방 점유해버려서 다른 `CompletableFuture`들이 기다리게 된다. I/O 작업은 전용 `ExecutorService`를 두 번째 인자로 넘겨야 한다.

```java
ExecutorService ioExecutor = Executors.newFixedThreadPool(20);

CompletableFuture.supplyAsync(() -> fetchUser(id), ioExecutor)
    .thenApplyAsync(user -> callExternalApi(user), ioExecutor)
    .thenApply(result -> transform(result));  // CPU 작업은 기본 풀 사용
```

`exceptionally()`는 예외가 없으면 실행되지 않는다. 그런데 중간 단계에서 `null`을 반환하면 이후 체인에서 NPE가 터지는데, 이 NPE는 원인 예외를 감춘 채 `CompletionException`으로 포장돼서 디버깅이 까다롭다. 체인 안에서 `null`을 반환할 수 있는 상황이라면 `Optional`로 감싸거나 기본값을 두는 게 낫다.

---

## 3. Lock

`synchronized`는 메서드나 블록에 걸면 JVM이 알아서 관리해주지만, 타임아웃 설정이 불가능하고 여러 조건에 따라 대기를 나누기 어렵다. `ReentrantLock`은 이 제약을 풀어준다.

```java
private final ReentrantLock lock = new ReentrantLock();

public void transfer(Account from, Account to, long amount) {
    lock.lock();
    try {
        from.withdraw(amount);
        to.deposit(amount);
    } finally {
        lock.unlock();  // 반드시 finally에서 해제
    }
}
```

`unlock()`을 `finally` 바깥에 두면 예외 발생 시 락이 영구적으로 잡힌 채 스레드가 멈춘다. 이 상태에서 해당 락을 기다리는 스레드는 무한 대기에 빠진다. 실무에서 `finally` 없이 `unlock()`을 쓰는 코드를 보면 반드시 지적해야 한다.

### tryLock으로 데드락 방지

계좌 이체 같은 로직에서 두 락을 순서 없이 잡으면 데드락이 발생한다. `tryLock()`으로 타임아웃을 걸면 한쪽이 포기하고 재시도하는 방식으로 데드락을 깰 수 있다.

```java
if (lock.tryLock(3, TimeUnit.SECONDS)) {
    try {
        // 작업 수행
    } finally {
        lock.unlock();
    }
} else {
    log.warn("락 획득 실패, 재시도 또는 대체 로직");
}
```

### ReadWriteLock

읽기는 여러 스레드가 동시에, 쓰기는 단독으로 실행한다. 읽기가 압도적으로 많은 캐시 구조에서 효과적이다.

```java
private final ReadWriteLock rwLock = new ReentrantReadWriteLock();
private final Map<String, String> cache = new HashMap<>();

public String get(String key) {
    rwLock.readLock().lock();
    try {
        return cache.get(key);
    } finally {
        rwLock.readLock().unlock();
    }
}

public void put(String key, String value) {
    rwLock.writeLock().lock();
    try {
        cache.put(key, value);
    } finally {
        rwLock.writeLock().unlock();
    }
}
```

쓰기가 자주 발생하는 상황에서 `ReadWriteLock`을 쓰면 오히려 `synchronized`보다 느려진다. 읽기 락과 쓰기 락 전환 비용이 발생하고, 쓰기 스레드가 읽기 스레드들이 전부 빠져나가길 기다리는 동안 기아 현상이 생길 수 있다.

| 비교 | synchronized | ReentrantLock |
|------|-------------|--------------|
| 타임아웃 | 불가 | `tryLock(timeout)` |
| 공정성 | 없음 | `new ReentrantLock(true)` |
| 읽기/쓰기 분리 | 불가 | ReadWriteLock |
| 조건 대기 | wait/notify | Condition |
| 사용 편의 | 간단 | unlock 필수 |

---

## 4. Atomic

CAS(Compare-And-Swap) 기반 원자 연산이다. 락을 사용하지 않고 CPU 명령어 수준에서 원자성을 보장한다.

```java
// 동기화 없이 카운터 - 레이스 컨디션 발생
private int count = 0;
count++;  // 읽기 → 증가 → 쓰기, 비원자적

// AtomicInteger
private final AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();
count.compareAndSet(5, 10);  // 현재 값이 5이면 10으로 변경

// AtomicReference
private final AtomicReference<User> currentUser = new AtomicReference<>();
currentUser.compareAndSet(oldUser, newUser);
```

`AtomicInteger`로 단일 값을 원자적으로 바꾸는 건 안전하다. 그런데 "값을 읽고, 조건을 확인하고, 그 결과에 따라 다른 값을 바꾸는" 복합 연산은 Atomic 클래스만으로 원자성을 보장하지 못한다. 읽기와 쓰기 사이에 다른 스레드가 끼어들 수 있기 때문이다. 이런 경우엔 락을 써야 한다.

| 클래스 | 용도 |
|--------|------|
| `AtomicInteger` | 정수 카운터 |
| `AtomicLong` | 긴 정수 카운터 |
| `AtomicBoolean` | 플래그 |
| `AtomicReference<T>` | 참조 교체 |
| `LongAdder` | 고성능 카운터 |

`LongAdder`는 스레드 간 경쟁이 심할 때 `AtomicLong`보다 빠르다. 내부적으로 값을 여러 셀로 나눠 갱신하고 읽을 때 합산하기 때문에 CAS 실패 재시도가 줄어든다. 카운터 조회가 잦지 않고 증가 연산만 많은 메트릭 수집 용도에 적합하다.

---

## 5. Concurrent Collections

`Collections.synchronizedMap()`은 모든 메서드에 메서드 단위 락을 건다. 읽기와 쓰기가 섞이면 전체가 직렬화된다. `ConcurrentHashMap`은 내부를 세그먼트로 나눠 잠그기 때문에 동시 처리량이 훨씬 높다.

```java
ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();
map.put("key", 1);
map.computeIfAbsent("key", k -> expensiveCompute(k));  // 원자적 연산
```

`ConcurrentHashMap`을 쓴다고 복합 연산까지 원자적이지는 않다. `containsKey()`로 존재 여부를 확인하고 `put()`으로 삽입하는 두 줄은 그 사이에 다른 스레드가 끼어들 수 있다. `computeIfAbsent()`처럼 단일 메서드로 표현할 수 있으면 그 쪽을 써야 한다.

`CopyOnWriteArrayList`는 쓰기마다 배열 전체를 복사한다. 읽기가 수백 번인데 쓰기가 한 번 발생하는 이벤트 리스너 목록 같은 곳에는 적합하다. 쓰기가 자주 발생하는 경우 복사 비용이 급격히 커진다.

```java
// BlockingQueue - 생산자-소비자 패턴
BlockingQueue<Task> queue = new LinkedBlockingQueue<>(100);

// 생산자: 큐가 가득 차면 대기
queue.put(new Task());

// 소비자: 큐가 비면 대기
Task task = queue.take();
```

`BlockingQueue` 크기를 제한해두면 생산자가 소비자 속도를 초과했을 때 자동으로 백프레셔가 걸린다. 크기를 무제한으로 두면 처리 속도 차이만큼 힙에 작업이 쌓이다가 OOM이 발생한다.

| 컬렉션 | 특징 | 용도 |
|--------|------|------|
| `ConcurrentHashMap` | 세그먼트별 잠금 | 스레드 안전 캐시 |
| `CopyOnWriteArrayList` | 쓰기 시 복사 | 읽기 많고 쓰기 적은 경우 |
| `BlockingQueue` | 생산자-소비자 | 작업 큐 |
| `ConcurrentLinkedQueue` | Lock-free 큐 | 고성능 큐 |

---

## 6. 동기화 유틸리티

### CountDownLatch

N개 작업이 완료될 때까지 특정 스레드를 대기시킨다. 서버 초기화 시 DB 연결, 캐시 로드, 메시지 큐 연결 같은 작업을 병렬로 띄운 뒤 모두 완료된 후 서버를 시작할 때 자주 쓴다.

```java
CountDownLatch latch = new CountDownLatch(3);

executor.submit(() -> { initDB(); latch.countDown(); });
executor.submit(() -> { initCache(); latch.countDown(); });
executor.submit(() -> { initQueue(); latch.countDown(); });

latch.await();  // 3개 모두 완료될 때까지 대기
startServer();
```

`CountDownLatch`는 재사용이 불가능하다. 카운트가 0에 도달하면 그걸로 끝이다. 재사용이 필요하면 `CyclicBarrier`를 써야 한다.

### Semaphore

동시에 접근할 수 있는 스레드 수를 제한한다. 외부 API 호출 수를 제한하거나, 데이터베이스 커넥션 풀을 직접 구현할 때 쓴다.

```java
Semaphore semaphore = new Semaphore(5);  // 최대 5개 동시 접근

semaphore.acquire();
try {
    accessLimitedResource();
} finally {
    semaphore.release();
}
```

`acquire()`가 블로킹이기 때문에 허가가 날 때까지 스레드가 대기한다. 타임아웃을 줄 수 있는 `tryAcquire(timeout, unit)`을 쓰면 무한 대기 상황을 방지할 수 있다.

---

## 7. Virtual Thread (Java 21+)

기존 플랫폼 스레드는 OS 스레드와 1:1로 매핑된다. 스레드 하나가 I/O를 기다리는 동안 OS 스레드도 블로킹 상태로 묶인다. Virtual Thread는 JVM이 관리하는 경량 스레드로, I/O 대기 중에는 플랫폼 스레드에서 분리(unmount)되고 다른 작업에 플랫폼 스레드를 넘겨준다.

```java
// 플랫폼 스레드
Thread.ofPlatform().start(() -> handleRequest());

// Virtual Thread
Thread.ofVirtual().start(() -> handleRequest());

// ExecutorService와 함께
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 100_000; i++) {
        executor.submit(() -> httpClient.send(request));
    }
}
```

Spring Boot 3.2 이상에서는 `spring.threads.virtual.enabled=true` 설정 하나로 내장 서버 스레드를 Virtual Thread로 전환할 수 있다.

### 주의사항

`synchronized` 블록 안에서 I/O가 발생하면 Virtual Thread가 플랫폼 스레드에 고정(pinning)된다. 그 순간 Virtual Thread의 장점이 사라지고 플랫폼 스레드처럼 동작한다. `synchronized` 대신 `ReentrantLock`을 쓰면 핀닝이 발생하지 않는다.

CPU 바운드 작업은 Virtual Thread로 전환해도 성능이 나아지지 않는다. I/O 대기가 없으니 unmount할 이유가 없고, 오히려 JVM 스케줄링 오버헤드만 추가된다. CPU 바운드 작업은 코어 수에 맞춘 플랫폼 스레드 풀이 적합하다.

| 비교 | 플랫폼 스레드 | Virtual Thread |
|------|-------------|---------------|
| 생성 비용 | 높음 (약 1MB 스택) | 낮음 (수 KB) |
| 최대 수 | 수천 개 | 수백만 개 |
| 스케줄링 | OS | JVM |
| 적합한 작업 | CPU 바운드 | I/O 바운드 |
| synchronized | 정상 | 핀닝 발생 주의 |

---

## 참고

- [Java Concurrency in Practice — Brian Goetz](https://jcip.net/)
- [Java 21 Virtual Threads](https://openjdk.org/jeps/444)
- [멀티 스레딩 기초](Multi_Threading.md)
- [레이스 컨디션](../../../OS/Process%20%26%20Thread/레이스_컨디션.md)
- [Deadlock](../../../OS/Process%20%26%20Thread/Deadlock.md)
