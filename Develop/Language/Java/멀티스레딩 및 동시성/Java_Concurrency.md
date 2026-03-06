---
title: Java 동시성 심화 가이드
tags: [java, concurrency, executor, completablefuture, lock, atomic, concurrent-collections, thread-pool]
updated: 2026-03-01
---

# Java 동시성 심화

## 개요

Java 동시성(Concurrency)은 **여러 작업을 동시에 처리**하는 프로그래밍 기법이다. `Thread`와 `Runnable` 기초를 넘어, 실무에서는 **ExecutorService, CompletableFuture, Lock, Atomic** 등 고수준 동시성 API를 사용한다.

### 동시성 vs 병렬성

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

## 핵심

### 1. ExecutorService (스레드 풀)

스레드를 직접 생성/관리하지 않고, **스레드 풀**에 작업을 제출한다.

```java
// ❌ 직접 스레드 생성 (위험)
for (int i = 0; i < 1000; i++) {
    new Thread(() -> processRequest()).start();  // 스레드 1000개 → OOM
}

// ✅ 스레드 풀 사용
ExecutorService executor = Executors.newFixedThreadPool(10);
for (int i = 0; i < 1000; i++) {
    executor.submit(() -> processRequest());  // 10개 스레드가 작업 나눠 처리
}
executor.shutdown();
```

#### 스레드 풀 유형

| 팩토리 메서드 | 동작 | 적합한 경우 |
|-------------|------|-----------|
| `newFixedThreadPool(n)` | 고정 n개 스레드 | 일반적인 서버 워크로드 |
| `newCachedThreadPool()` | 필요 시 생성, 유휴 시 해제 | 짧은 비동기 작업 |
| `newSingleThreadExecutor()` | 스레드 1개 (순차 실행) | 순서 보장 필요 |
| `newScheduledThreadPool(n)` | 주기적/지연 실행 | 스케줄링 작업 |
| `newVirtualThreadPerTaskExecutor()` | 가상 스레드 (Java 21+) | 대량 I/O 작업 |

#### 커스텀 ThreadPoolExecutor

```java
// 프로덕션에서는 직접 설정 권장
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10,                          // corePoolSize: 기본 스레드 수
    50,                          // maximumPoolSize: 최대 스레드 수
    60L, TimeUnit.SECONDS,       // keepAliveTime: 유휴 스레드 생존 시간
    new LinkedBlockingQueue<>(100),  // 작업 큐 (크기 제한!)
    new ThreadPoolExecutor.CallerRunsPolicy()  // 거부 정책
);

// Spring에서 비동기 설정
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

#### 거부 정책

| 정책 | 동작 | 적합한 경우 |
|------|------|-----------|
| `AbortPolicy` (기본) | RejectedExecutionException | 작업 유실 불가 |
| `CallerRunsPolicy` | 호출한 스레드가 직접 실행 | **가장 안전 (권장)** |
| `DiscardPolicy` | 조용히 버림 | 로그, 메트릭 등 |
| `DiscardOldestPolicy` | 큐에서 가장 오래된 작업 버림 | 최신 데이터 우선 |

### 2. CompletableFuture (비동기 프로그래밍)

**비동기 작업을 체이닝**하여 콜백 지옥 없이 비동기 로직을 작성한다.

```java
// 기본 사용
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    return fetchUserFromDB(userId);  // 비동기 실행
});

String user = future.get();  // 결과 대기 (블로킹)
```

#### 체이닝

```java
CompletableFuture.supplyAsync(() -> fetchUser(userId))        // 1. 사용자 조회
    .thenApply(user -> enrichWithProfile(user))               // 2. 프로필 보강
    .thenApply(user -> calculateDiscount(user))               // 3. 할인 계산
    .thenAccept(user -> sendNotification(user))               // 4. 알림 전송
    .exceptionally(ex -> {                                    // 에러 처리
        log.error("처리 실패", ex);
        return null;
    });
```

#### 여러 비동기 작업 조합

```java
// 두 작업을 병렬로 실행 후 합치기
CompletableFuture<User> userFuture = CompletableFuture.supplyAsync(() -> fetchUser(id));
CompletableFuture<List<Order>> orderFuture = CompletableFuture.supplyAsync(() -> fetchOrders(id));

CompletableFuture<UserProfile> profileFuture = userFuture.thenCombine(orderFuture,
    (user, orders) -> new UserProfile(user, orders)
);

// 여러 작업 모두 완료 대기
CompletableFuture<Void> allDone = CompletableFuture.allOf(
    task1, task2, task3
);
allDone.join();  // 모두 완료될 때까지 대기

// 가장 빠른 결과 사용
CompletableFuture<String> fastest = CompletableFuture.anyOf(
    fetchFromCache(), fetchFromDB(), fetchFromAPI()
).thenApply(Object::toString);
```

#### 실전 예시: 주문 조회 API

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

        // 3개 API를 병렬 호출 후 합침
        return orderFuture.thenCombine(paymentFuture, OrderDetail::withPayment)
                          .thenCombine(deliveryFuture, OrderDetail::withDelivery);
    }
}
```

### 3. Lock (명시적 잠금)

`synchronized`보다 유연한 잠금 메커니즘.

```java
// ReentrantLock: 재진입 가능한 락
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

// tryLock: 타임아웃 지원 (Deadlock 방지)
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

#### ReadWriteLock

읽기는 여러 스레드가 동시에, 쓰기는 단독으로 실행한다.

```java
private final ReadWriteLock rwLock = new ReentrantReadWriteLock();
private final Map<String, String> cache = new HashMap<>();

public String get(String key) {
    rwLock.readLock().lock();       // 읽기 락 (동시 접근 가능)
    try {
        return cache.get(key);
    } finally {
        rwLock.readLock().unlock();
    }
}

public void put(String key, String value) {
    rwLock.writeLock().lock();      // 쓰기 락 (단독 접근)
    try {
        cache.put(key, value);
    } finally {
        rwLock.writeLock().unlock();
    }
}
```

| 비교 | synchronized | ReentrantLock |
|------|-------------|--------------|
| **타임아웃** | 불가 | `tryLock(timeout)` |
| **공정성** | 없음 | `new ReentrantLock(true)` |
| **읽기/쓰기 분리** | 불가 | ReadWriteLock |
| **조건 대기** | wait/notify | Condition |
| **사용 편의** | 간단 | 유연하지만 unlock 필수 |

### 4. Atomic (원자적 연산)

**Lock 없이** 스레드 안전한 연산을 수행한다. CAS(Compare-And-Swap) 기반.

```java
// ❌ 동기화 없이 카운터 (레이스 컨디션)
private int count = 0;
count++;  // 읽기 → 증가 → 쓰기 (비원자적!)

// ✅ AtomicInteger
private final AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();  // 원자적 증가
count.compareAndSet(5, 10);  // 5이면 10으로 변경

// AtomicReference
private final AtomicReference<User> currentUser = new AtomicReference<>();
currentUser.compareAndSet(oldUser, newUser);
```

| 클래스 | 용도 |
|--------|------|
| `AtomicInteger` | 정수 카운터 |
| `AtomicLong` | 긴 정수 카운터 |
| `AtomicBoolean` | 플래그 |
| `AtomicReference<T>` | 참조 교체 |
| `LongAdder` | 고성능 카운터 (AtomicLong보다 빠름) |

### 5. Concurrent Collections

스레드 안전한 컬렉션.

| 컬렉션 | 특징 | 용도 |
|--------|------|------|
| `ConcurrentHashMap` | 세그먼트별 잠금 | 스레드 안전 캐시 |
| `CopyOnWriteArrayList` | 쓰기 시 복사 | 읽기 많고 쓰기 적을 때 |
| `BlockingQueue` | 생산자-소비자 | 작업 큐 |
| `ConcurrentLinkedQueue` | Lock-free 큐 | 고성능 큐 |

```java
// ConcurrentHashMap (synchronized Map보다 훨씬 빠름)
ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();
map.put("key", 1);
map.computeIfAbsent("key", k -> expensiveCompute(k));  // 원자적 연산

// BlockingQueue (생산자-소비자)
BlockingQueue<Task> queue = new LinkedBlockingQueue<>(100);

// 생산자
queue.put(new Task());  // 큐가 가득 차면 대기

// 소비자
Task task = queue.take();  // 큐가 비면 대기
```

### 6. 동기화 유틸리티

```java
// CountDownLatch: N개 작업 완료 대기
CountDownLatch latch = new CountDownLatch(3);

executor.submit(() -> { initDB(); latch.countDown(); });
executor.submit(() -> { initCache(); latch.countDown(); });
executor.submit(() -> { initQueue(); latch.countDown(); });

latch.await();  // 3개 모두 완료될 때까지 대기
startServer();

// Semaphore: 동시 접근 수 제한
Semaphore semaphore = new Semaphore(5);  // 최대 5개 동시 접근

semaphore.acquire();  // 허가 획득 (없으면 대기)
try {
    accessLimitedResource();
} finally {
    semaphore.release();  // 허가 반환
}
```

### 7. Virtual Thread (Java 21+)

경량 스레드. 수백만 개 생성 가능. I/O 바운드 작업에 최적.

```java
// 기존: 플랫폼 스레드 (OS 스레드 1:1 매핑)
Thread.ofPlatform().start(() -> handleRequest());

// Virtual Thread: JVM이 관리하는 경량 스레드
Thread.ofVirtual().start(() -> handleRequest());

// ExecutorService와 함께
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 100_000; i++) {
        executor.submit(() -> {
            // I/O 작업 (DB 조회, HTTP 호출 등)
            return httpClient.send(request);
        });
    }
}

// Spring Boot 3.2+
spring.threads.virtual.enabled=true  // application.properties
```

| 비교 | 플랫폼 스레드 | Virtual Thread |
|------|-------------|---------------|
| **생성 비용** | 높음 (~1MB 스택) | 낮음 (~KB) |
| **최대 수** | 수천 개 | **수백만 개** |
| **스케줄링** | OS | JVM |
| **적합한 작업** | CPU 바운드 | **I/O 바운드** |
| **synchronized** | 핀닝 발생 주의 | ReentrantLock 권장 |

## 참고

- [Java Concurrency in Practice — Brian Goetz](https://jcip.net/)
- [Java 21 Virtual Threads](https://openjdk.org/jeps/444)
- [멀티 스레딩 기초](Multi_Threading.md) — Thread, Runnable 기본
- [레이스 컨디션](../../OS/Process & Thread/레이스_컨디션.md) — 동기화 문제
- [Deadlock](../../OS/Deadlock.md) — 교착 상태
