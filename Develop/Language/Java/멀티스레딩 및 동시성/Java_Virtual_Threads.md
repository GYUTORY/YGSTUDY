---
title: Java 가상 스레드 (Virtual Threads)
tags: [language, java, os]
updated: 2026-07-26
---

# Java 가상 스레드 (Virtual Threads)

Java 21에서 정식 릴리즈된 가상 스레드는 Project Loom의 결과물이다. 기존 Java 스레드 모델의 핵심 문제인 OS 스레드와 Java 스레드의 1:1 매핑을 끊어낸 것이다.

## 플랫폼 스레드와 가상 스레드의 차이

플랫폼 스레드(Platform Thread)는 OS 스레드와 1:1로 매핑된다. 스레드를 하나 만들면 OS 수준의 스레드가 하나 생기고, 여기에 메모리(기본 512KB~1MB 스택)가 할당된다. 스레드가 블로킹 I/O로 대기 중이어도 OS 스레드는 점유된 상태다.

이 구조 때문에 톰캣 같은 스레드-퍼-리퀘스트(thread-per-request) 서버는 동시 처리량이 스레드 수에 묶인다. 100개 스레드면 최대 100개 요청을 동시에 처리하는데, 각 요청이 DB 쿼리를 기다리는 동안 스레드는 놀고 있다.

가상 스레드는 JVM이 관리하는 경량 스레드다. 내부적으로 캐리어 스레드(carrier thread)라 부르는 ForkJoinPool 기반의 플랫폼 스레드 풀 위에서 동작한다. 가상 스레드가 블로킹 I/O를 만나면 JVM이 해당 가상 스레드를 캐리어 스레드에서 분리(unmount)하고, 캐리어 스레드는 다른 가상 스레드를 실행한다.

메모리도 다르다. 플랫폼 스레드 스택은 고정 크기지만, 가상 스레드 스택은 힙에 저장되고 필요에 따라 늘어난다. 시작 크기는 수백 바이트 수준이다.

```
플랫폼 스레드 구조:
Java Thread 1 -> OS Thread 1 (512KB 스택)
Java Thread 2 -> OS Thread 2 (512KB 스택)
Java Thread N -> OS Thread N (512KB 스택)

가상 스레드 구조:
Virtual Thread 1 --+
Virtual Thread 2   +--> Carrier Thread 1 (ForkJoinPool)
Virtual Thread 3 --+
Virtual Thread 4 --+
Virtual Thread N --+--> Carrier Thread 2 (ForkJoinPool)
```

## 가상 스레드 생성

```java
// 단일 가상 스레드 생성
Thread vt = Thread.ofVirtual().start(() -> {
    System.out.println("virtual: " + Thread.currentThread().isVirtual()); // true
});

// 이름 지정 후 나중에 시작
Thread vt2 = Thread.ofVirtual()
    .name("my-vt")
    .unstarted(() -> doWork());
vt2.start();

// ExecutorService로 사용 (권장 방식)
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> handleRequest(req1));
    executor.submit(() -> handleRequest(req2));
    // try-with-resources 종료 시 모든 작업 완료 대기
}
```

`newVirtualThreadPerTaskExecutor()`는 작업마다 새 가상 스레드를 만든다. 가상 스레드는 생성 비용이 낮으므로 풀링하지 않아도 된다.

## 기존 ThreadPoolExecutor와 동작 방식 비교

ThreadPoolExecutor는 스레드 수를 직접 결정해야 했다. 스레드를 너무 적게 만들면 처리량이 떨어지고, 너무 많이 만들면 메모리와 컨텍스트 스위칭 비용이 문제가 된다.

```java
// 기존 방식 — 스레드 수를 직접 결정해야 한다
ExecutorService executor = new ThreadPoolExecutor(
    10, 200,
    60L, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(1000)
);

// 가상 스레드 방식 — 개수를 신경 쓰지 않아도 된다
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
```

가상 스레드 방식에서는 블로킹 I/O 중에 캐리어 스레드가 다른 작업을 처리하기 때문에, 스레드 수 튜닝 없이도 높은 동시성을 얻는다. 캐리어 스레드 수는 기본적으로 CPU 코어 수와 같다.

I/O 집약적인 작업(HTTP 요청, DB 쿼리, 파일 읽기)에서 가상 스레드는 플랫폼 스레드풀 대비 훨씬 많은 동시 작업을 처리할 수 있다. 스레드가 블로킹으로 대기하는 시간이 길수록 효과가 크다.

## 핀닝(Pinning) 문제

가상 스레드가 블로킹 상태가 되어도 캐리어 스레드를 점유하는 상황을 핀닝이라 한다. 핀닝이 발생하면 가상 스레드가 일반 스레드처럼 동작한다.

핀닝이 발생하는 두 가지 경우가 있다. 첫 번째는 `synchronized` 블록/메서드 안에서 블로킹 작업을 실행할 때, 두 번째는 JNI 코드 실행 중일 때다.

```java
// 핀닝 발생 — synchronized 안에서 블로킹 I/O
class DatabaseClient {
    synchronized ResultSet query(String sql) {
        // 블로킹 I/O가 발생하면 캐리어 스레드가 핀닝된다
        return connection.executeQuery(sql);
    }
}

// 핀닝 회피 — ReentrantLock으로 교체
class DatabaseClient {
    private final ReentrantLock lock = new ReentrantLock();

    ResultSet query(String sql) {
        lock.lock();
        try {
            // 블로킹이 발생해도 캐리어 스레드를 해제한다
            return connection.executeQuery(sql);
        } finally {
            lock.unlock();
        }
    }
}
```

`ReentrantLock`은 가상 스레드가 대기 중일 때 캐리어 스레드를 해제한다. `synchronized`는 JVM 구현 특성상 Java 21 기준으로는 이를 지원하지 않는다. Java 24에서 이 제한이 개선되었지만, Java 21 환경에서는 `synchronized` 내부에서 블로킹 I/O를 피해야 한다.

핀닝 발생 여부는 JVM 플래그로 확인할 수 있다.

```
-Djdk.tracePinnedThreads=full
```

이 플래그를 켜면 핀닝이 발생할 때마다 스택 트레이스를 출력한다. 마이그레이션 초기에 이 플래그로 확인하면서 문제를 찾는 것이 낫다.

## Structured Concurrency

Java 21에서 preview로 포함된 Structured Concurrency(구조적 동시성)는 여러 비동기 작업의 수명 주기를 하나의 스코프로 묶는다.

기존에는 여러 작업을 동시에 실행할 때 실패 처리가 복잡했다.

```java
// 기존 방식 — 실패 시 취소 처리가 번거롭다
Future<User> userFuture = executor.submit(() -> fetchUser(id));
Future<Order> orderFuture = executor.submit(() -> fetchOrder(id));

try {
    User user = userFuture.get();
    Order order = orderFuture.get();
} catch (ExecutionException e) {
    // userFuture가 실패했을 때 orderFuture 취소를 직접 해야 한다
    userFuture.cancel(true);
    orderFuture.cancel(true);
    throw new RuntimeException(e);
}
```

Structured Concurrency를 쓰면 이 과정이 단순해진다.

```java
// Java 21 preview — StructuredTaskScope
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    StructuredTaskScope.Subtask<User> userTask = scope.fork(() -> fetchUser(id));
    StructuredTaskScope.Subtask<Order> orderTask = scope.fork(() -> fetchOrder(id));

    scope.join().throwIfFailed(); // 하나라도 실패하면 나머지 취소 후 예외 던짐

    return new Response(userTask.get(), orderTask.get());
}
```

하나가 실패하면 나머지 작업을 자동으로 취소한다. 스코프를 벗어나면 모든 작업이 정리되어 누수가 없다.

`ShutdownOnSuccess`는 반대 방향이다. 하나가 성공하면 나머지를 취소한다.

```java
// 여러 서버 중 먼저 응답하는 것을 택하는 경우
try (var scope = new StructuredTaskScope.ShutdownOnSuccess<String>()) {
    scope.fork(() -> fetchFromServer("asia-northeast1"));
    scope.fork(() -> fetchFromServer("us-central1"));

    scope.join();
    return scope.result(); // 먼저 성공한 결과
}
```

## 기존 ExecutorService 코드 마이그레이션

기존 스레드풀 코드를 가상 스레드로 전환하는 것은 대부분 단순하다.

```java
// 마이그레이션 전
ExecutorService executor = Executors.newFixedThreadPool(100);

// 마이그레이션 후
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
```

스프링 부트 3.2부터는 설정 하나로 가상 스레드를 활성화할 수 있다.

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true
```

이 설정을 켜면 스프링이 내부적으로 `Executors.newVirtualThreadPerTaskExecutor()`를 사용한다. Tomcat, 스케줄러 등 스프링이 관리하는 스레드풀이 모두 가상 스레드로 교체된다.

마이그레이션 시 확인해야 할 것들이 있다.

`synchronized`를 쓰는 라이브러리가 있으면 핀닝이 발생한다. Hibernate, 일부 JDBC 드라이버, 레거시 라이브러리가 여기에 해당한다. `-Djdk.tracePinnedThreads=full`로 먼저 확인하고, 문제가 되는 부분은 해당 라이브러리 버전을 올리거나 `ReentrantLock`으로 감싸야 한다.

ThreadLocal 사용은 가상 스레드에서도 동작하지만, 가상 스레드 수가 수만~수십만 개가 되면 ThreadLocal 데이터가 힙에 쌓인다. Java 21의 ScopedValue가 대안이다.

```java
// ThreadLocal 대신 ScopedValue (Java 21 preview)
static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

ScopedValue.where(CURRENT_USER, user).run(() -> {
    processRequest(); // 이 스코프 안에서 CURRENT_USER.get()으로 접근
});
```

ScopedValue는 불변이고 스코프가 명확해서 가상 스레드 환경에서 ThreadLocal보다 안전하다.

## 가상 스레드가 적합한 경우

I/O 바운드 작업에 적합하다.

- REST API 서버에서 외부 API 호출이 많은 경우
- DB 쿼리 대기 시간이 긴 서비스
- 파일 업로드/다운로드 처리
- 메시지 브로커(Kafka, RabbitMQ) 컨슈머

이런 작업은 스레드가 대부분의 시간을 I/O 대기로 보낸다. 가상 스레드는 대기 중에 캐리어 스레드를 반환하므로, 같은 수의 캐리어 스레드로 훨씬 많은 요청을 처리한다.

## 가상 스레드가 적합하지 않은 경우

CPU 바운드 작업에는 가상 스레드가 도움이 되지 않는다.

이미지 처리, 암호화, 압축, 행렬 연산 같은 작업은 스레드가 블로킹 없이 CPU를 계속 쓴다. 가상 스레드를 만들어도 캐리어 스레드를 해제할 시점이 없다. 결국 CPU 코어 수만큼의 스레드만 실제로 동시에 실행된다.

```java
// CPU 바운드 작업 — 가상 스레드의 이점이 없다
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 1000; i++) {
        executor.submit(() -> computeHash(largeData)); // 블로킹 없는 순수 CPU 작업
    }
    // 실제로는 캐리어 스레드 수(=코어 수)만큼만 병렬로 실행된다
}

// CPU 바운드에는 ForkJoinPool이나 병렬 스트림이 낫다
ForkJoinPool pool = new ForkJoinPool(Runtime.getRuntime().availableProcessors());
List<byte[]> results = data.parallelStream()
    .map(item -> computeHash(item))
    .collect(Collectors.toList());
```

가상 스레드 풀링도 하면 안 된다. `Executors.newFixedThreadPool(10)` 방식으로 가상 스레드를 풀링하면 오히려 성능이 떨어진다. 가상 스레드는 작업마다 하나씩 만드는 게 기본 패턴이다.

## JDBC 커넥션 풀과 함께 쓸 때 주의사항

HikariCP 같은 커넥션 풀과 함께 쓸 때 주의가 필요하다. 가상 스레드 수가 늘어나면 커넥션 풀 경쟁이 심해진다. 스레드 수 제한 없이 요청을 처리하면 모든 가상 스레드가 DB 커넥션을 기다리며 풀을 포화시킬 수 있다.

```java
// 세마포어로 DB 동시 접근 수를 제한
private final Semaphore dbSemaphore = new Semaphore(50); // 커넥션 풀 크기와 맞춤

void queryWithLimit(String sql) throws InterruptedException {
    dbSemaphore.acquire();
    try {
        jdbcTemplate.query(sql, rowMapper);
    } finally {
        dbSemaphore.release();
    }
}
```

커넥션 풀 크기보다 세마포어 허용 수를 작게 잡는 것이 낫다. 커넥션 대기 큐가 쌓이면 지연 시간이 급격히 늘어난다.

모니터링도 달라진다. 가상 스레드는 수만 개가 생성되므로 스레드 수로 부하를 측정하던 방식이 의미 없어진다. 캐리어 스레드 사용률, 커넥션 풀 대기 시간, 요청 응답 시간 기반으로 모니터링해야 한다.
