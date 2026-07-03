---
title: Java 멀티스레딩과 동시성 제어 심화
tags: [java, concurrency, jmm, happens-before, lock, atomic, cas, threadpool, forkjoin, completablefuture, threadlocal, virtual-thread, pinning]
updated: 2026-04-24
---

# Java 멀티스레딩과 동시성 제어 심화

기본 문법(스레드 생성, synchronized, volatile, wait/notify)과 고수준 API(ExecutorService, CompletableFuture, Lock, Atomic)는 따로 정리되어 있다. 이 문서는 그 둘을 관통하는 메커니즘, 즉 **JVM이 어떻게 동시성을 보장하는지**, **도구들의 경계가 어디인지**, **실무에서 터지는 문제가 왜 터지는지**를 다룬다.

실제로 5년 정도 서버를 운영하다 보면 `synchronized`를 잘 쓰는 것보다, 락 경합으로 스레드 풀이 고갈되거나 `CompletableFuture`가 공용 풀을 먹어치워서 장애가 번지는 경우를 훨씬 더 자주 만난다. 아래 내용은 그런 상황을 피하기 위한 것들이다.

---

## Java 메모리 모델 (JMM)과 happens-before

### 왜 JMM이 필요한가

멀티코어 CPU에서 각 코어는 자기만의 레지스터와 L1/L2 캐시를 가진다. 스레드가 변수를 변경해도 그 값은 일단 캐시에 머물고, 언제 메인 메모리에 flush되는지는 CPU 아키텍처와 JIT 컴파일러의 최적화에 달려 있다. 거기에 컴파일러와 CPU는 **명령어 재배치(reordering)**까지 한다. 단일 스레드에서 결과가 같으면 순서를 바꿔도 문제가 없기 때문이다.

```java
class Example {
    int x = 0;
    int y = 0;

    void thread1() {
        x = 1;       // (1)
        int r1 = y;  // (2)
    }

    void thread2() {
        y = 1;       // (3)
        int r2 = x;  // (4)
    }
}
```

직관적으로는 `r1 = 0, r2 = 0`이 나올 수 없을 것 같지만, 실제로는 나온다. CPU가 (1)과 (2)의 순서를 바꿀 수도 있고, 스토어 버퍼에 값이 머물러 다른 코어가 아직 못 볼 수도 있다. JMM이 없으면 멀티스레드 코드는 어떤 값이든 나올 수 있는 카오스가 된다.

JMM은 **어떤 경우에 한 스레드의 쓰기가 다른 스레드에서 반드시 보이는지**를 규정한 규칙이다. 그 핵심이 happens-before 관계다.

### happens-before의 의미

A happens-before B라고 하면, A의 결과가 B에서 반드시 관찰 가능하고, A의 효과가 B보다 먼저 일어난 것처럼 보여야 한다. JMM이 보장하는 주요 happens-before 관계는 다음과 같다.

- **프로그램 순서 규칙**: 같은 스레드 안에서 앞에 있는 문장은 뒤 문장에 happens-before.
- **모니터 락 규칙**: `synchronized` 블록 해제(unlock)는 같은 락의 획득(lock)에 happens-before.
- **volatile 변수 규칙**: volatile 변수의 쓰기는 이어지는 그 변수의 읽기에 happens-before.
- **스레드 시작 규칙**: `Thread.start()`는 해당 스레드 안의 모든 문장에 happens-before.
- **스레드 종료 규칙**: 스레드 안의 모든 문장은 다른 스레드가 관찰하는 `join()` 반환에 happens-before.
- **전이성**: A → B, B → C면 A → C.

실무에서 가장 유용한 규칙은 락과 volatile이다. 이 두 개를 사용하면 "내가 쓴 값이 다른 스레드에서 보이는가"를 고민하지 않아도 된다.

```java
class PublishExample {
    private Config config;  // 일반 필드
    private volatile boolean ready = false;

    void publish() {
        config = loadConfig();  // (1)
        ready = true;           // (2) volatile write
    }

    void consume() {
        if (ready) {            // (3) volatile read
            config.apply();     // (4) (1)의 결과가 여기서 반드시 보인다
        }
    }
}
```

`config`는 volatile이 아니지만, (2)의 volatile 쓰기가 (3)의 volatile 읽기에 happens-before이고, (1)은 프로그램 순서로 (2) 이전이므로, 전이성에 의해 (1)이 (4)에 happens-before가 된다. 이게 JMM의 진짜 힘이다.

### 메모리 배리어 (Memory Barrier)

happens-before는 추상 개념이고, JVM은 이를 **메모리 배리어** 명령어로 구현한다. x86에서는 volatile 쓰기 뒤에 `StoreLoad` 배리어(보통 `mfence` 또는 `lock` 접두어)가 들어간다. 배리어는 두 가지 일을 한다.

- CPU가 배리어 앞뒤 명령을 재배치하지 못하게 막는다.
- 스토어 버퍼를 flush해서 다른 코어가 최신 값을 보게 한다.

x86은 원래부터 스토어 순서가 강한 아키텍처라 배리어 비용이 낮지만, ARM은 메모리 모델이 느슨해서 배리어 비용이 훨씬 크다. 애플 실리콘(M1/M2)에서 동시성 테스트를 돌리면 x86과 다른 결과가 나오는 경우가 종종 있는데, 대부분 이 차이 때문이다.

---

## synchronized vs volatile vs Lock vs Atomic

네 가지 모두 "여러 스레드가 공유 데이터를 건드려도 깨지지 않게" 만드는 도구지만, 보장 범위와 성능 특성이 다르다. 무엇을 고를지 헷갈리면 **원자성이 필요한가, 가시성만 필요한가**를 먼저 묻는다.

### 비교표

| 도구 | 원자성 | 가시성 | 재진입 | 타임아웃 | 조건 대기 | 주 용도 |
|------|--------|--------|--------|----------|-----------|---------|
| `volatile` | X | O | - | - | - | 단일 변수의 플래그 |
| `synchronized` | O | O | O | X | wait/notify | 간단한 임계 구역 |
| `ReentrantLock` | O | O | O | O | Condition | 복잡한 락 제어 |
| `Atomic*` | O (단일 연산) | O | - | - | - | 카운터, 상태 교체 |

### 선택 기준

**volatile**: 상태 플래그처럼 **쓰기는 한 스레드만, 읽기는 여러 스레드**가 하는 경우. 복합 연산(read-modify-write)에는 절대 쓰면 안 된다. `running = false` 같은 종료 플래그, `initialized = true` 같은 초기화 플래그가 전형적이다.

**synchronized**: 크리티컬 섹션이 짧고, 타임아웃이나 공정성이 필요 없는 경우. 가장 단순하고, JIT가 락 생략(lock elision), 편향 락(biased locking, Java 15까지), 경량 락(lightweight locking)으로 최적화해주기 때문에 대부분 충분하다. 자바 15 이후 편향 락은 제거됐다.

**ReentrantLock**: `tryLock(timeout)`이 필요하거나, 여러 조건 변수를 다루거나, 공정성을 강제해야 하는 경우. `synchronized`와 성능 차이는 거의 없지만, `unlock`을 빼먹으면 바로 데드락이 나서 실수 여지가 크다.

**Atomic**: 단일 변수의 증감, 참조 교체처럼 CAS로 해결되는 경우. 락을 안 쓰니 컨텍스트 스위칭이 없어 경합이 적을 때 가장 빠르다. 경합이 심해지면 CAS 실패가 반복되어 오히려 느려질 수 있다.

### 자주 하는 실수

```java
// 잘못된 이중 체크
class Lazy {
    private Resource resource;

    public Resource get() {
        if (resource == null) {        // (1) lock 밖 확인
            synchronized (this) {
                if (resource == null) {
                    resource = new Resource();  // (2)
                }
            }
        }
        return resource;
    }
}
```

`resource`에 volatile이 없으면 (2)의 생성과 참조 대입이 재배치될 수 있다. 다른 스레드는 (1)에서 null이 아닌 참조를 보지만, 생성자가 끝나지 않은 반쪽짜리 객체를 볼 수 있다. 이 패턴을 **Double-Checked Locking**이라 부르는데, 반드시 volatile을 붙여야 안전하다.

```java
class Lazy {
    private volatile Resource resource;

    public Resource get() {
        Resource r = resource;
        if (r == null) {
            synchronized (this) {
                r = resource;
                if (r == null) {
                    resource = r = new Resource();
                }
            }
        }
        return r;
    }
}
```

지역 변수 `r`로 받아두는 이유는 volatile 읽기 횟수를 줄이기 위해서다. volatile 읽기는 일반 읽기보다 비싸기 때문에, 안전한 범위에서 캐싱해서 쓴다.

---

## 락 종류별 실제 성능 차이

### ReentrantLock

가장 범용적인 락. 내부적으로 `AbstractQueuedSynchronizer`(AQS) 위에 만들어졌다. 경합이 없을 때는 CAS 한 번으로 락을 잡고, 경합이 있으면 큐에 들어가 대기한다.

```java
private final ReentrantLock lock = new ReentrantLock();

public void transfer(Account from, Account to, long amount) {
    lock.lock();
    try {
        from.withdraw(amount);
        to.deposit(amount);
    } finally {
        lock.unlock();
    }
}
```

공정성을 켜면(`new ReentrantLock(true)`) 먼저 대기한 스레드가 먼저 락을 얻는다. 하지만 공정 락은 비공정 락보다 10배 이상 느린 경우도 있어서, **굶주림(starvation)이 실제로 문제가 되지 않는 한 비공정 락을 쓴다**.

### ReadWriteLock

읽기는 동시에, 쓰기는 독점으로. 읽기가 쓰기보다 훨씬 많은 캐시나 조회 서비스에서 유리하다.

```java
private final ReadWriteLock rw = new ReentrantReadWriteLock();
private final Map<String, Data> cache = new HashMap<>();

public Data get(String key) {
    rw.readLock().lock();
    try {
        return cache.get(key);
    } finally {
        rw.readLock().unlock();
    }
}

public void put(String key, Data data) {
    rw.writeLock().lock();
    try {
        cache.put(key, data);
    } finally {
        rw.writeLock().unlock();
    }
}
```

ReadWriteLock의 함정은 **쓰기가 섞이기 시작하면 기대만큼 성능이 안 난다**는 점이다. 쓰기 락이 들어오면 이후 읽기 요청이 전부 대기하고, 쓰기가 끝나면 다시 읽기들이 몰려든다. 쓰기 비율이 10%만 넘어가도 일반 `ReentrantLock`과 비슷하거나 더 느려질 때가 있다.

그리고 읽기 락은 쓰기 락으로 **업그레이드되지 않는다**. 읽기 락을 잡은 상태에서 쓰기 락을 요청하면 데드락이다. 쓰기로 바꾸려면 반드시 읽기 락을 먼저 풀어야 한다.

### StampedLock (Java 8+)

ReadWriteLock의 대안. 낙관적 읽기(optimistic read)를 지원한다.

```java
private final StampedLock lock = new StampedLock();
private double x, y;

public double distanceFromOrigin() {
    long stamp = lock.tryOptimisticRead();  // 락을 안 잡는다
    double curX = x, curY = y;
    if (!lock.validate(stamp)) {            // 중간에 쓰기가 있었나 확인
        stamp = lock.readLock();            // 쓰기가 있었으면 진짜 읽기 락
        try {
            curX = x;
            curY = y;
        } finally {
            lock.unlockRead(stamp);
        }
    }
    return Math.sqrt(curX * curX + curY * curY);
}
```

낙관적 읽기는 아예 락을 안 잡기 때문에 경합이 거의 없을 때는 ReadWriteLock보다 몇 배 빠르다. 다만 **재진입이 안 되고**, **Condition도 없고**, 잘못 쓰면 값이 inconsistent 상태로 읽힌다. 실수 여지가 많아서 정말 핫 패스에서 성능이 필요한 경우가 아니면 권장하지 않는다.

### 언제 무엇을 쓸까

- 읽기/쓰기 구분 없음 → `synchronized` 또는 `ReentrantLock`.
- 읽기 >> 쓰기, 데이터가 자주 바뀌지 않음 → `StampedLock` 낙관적 읽기.
- 읽기 > 쓰기지만 쓰기 비율이 낮지 않음 → `ReadWriteLock`을 쓸 거면 측정부터 하고, 의외로 그냥 `ReentrantLock`이 빠를 때가 많다.
- 캐시용이면 대부분 `ConcurrentHashMap` 한 방으로 해결된다.

---

## CAS와 ABA 문제

### CAS (Compare-And-Swap)

Atomic 클래스의 핵심은 CAS라는 CPU 원자 명령이다. "현재 값이 expected와 같으면 new로 바꾼다"를 한 번의 원자적 연산으로 실행한다.

```java
AtomicInteger counter = new AtomicInteger(0);

// 내부 동작을 의사 코드로 표현
// do {
//     int current = counter.get();
//     int next = current + 1;
// } while (!counter.compareAndSet(current, next));

counter.incrementAndGet();
```

경합이 없으면 CAS 한 번으로 끝난다. 경합이 생기면 CAS가 실패하고 루프를 돈다. 경합이 심하면 CAS 실패가 누적되어 오히려 락보다 느려질 수 있는데, 이때는 `LongAdder`가 답이다. `LongAdder`는 여러 셀로 값을 분산시켜 CAS 경합을 줄이고, 합계가 필요할 때만 합친다. 단순 카운터라면 `AtomicLong`보다 `LongAdder`가 훨씬 빠르다.

### ABA 문제

CAS는 "값이 기대한 것과 같은가"만 확인한다. 하지만 값이 A → B → A로 바뀌었다면, CAS는 변경이 없었다고 판단한다. 단순한 카운터에서는 문제가 없지만, 참조를 교체하는 경우에는 심각한 버그가 된다.

```java
class Node { Node next; int value; }

AtomicReference<Node> head = new AtomicReference<>(A);

// 스레드 1: head = A를 읽고 다음에 CAS로 head = B로 바꾸려 함
// 스레드 2: head를 A → B로 바꾸고, B를 pop해서 메모리 풀로 반환
// 스레드 2: 메모리 풀에서 다시 같은 주소를 꺼내 C를 만들고 head에 push (head = A' 주소는 같지만 다른 노드)
// 스레드 1: CAS(A, B) 성공. 하지만 head는 이미 꼬여 있다.
```

Lock-free 자료구조를 직접 만들지 않는 한 ABA 문제를 마주칠 일은 드물지만, 객체 풀링을 직접 구현하거나 메모리를 재사용하는 로직에서는 언제든 터질 수 있다.

### AtomicStampedReference

ABA를 막으려면 참조에 버전(stamp)을 함께 저장한다. stamp가 같아야만 CAS가 성공한다.

```java
AtomicStampedReference<Node> head = new AtomicStampedReference<>(A, 0);

int[] stampHolder = new int[1];
Node current = head.get(stampHolder);
int stamp = stampHolder[0];

Node next = new Node(current);
// 참조와 stamp 둘 다 일치해야 성공
head.compareAndSet(current, next, stamp, stamp + 1);
```

비슷한 용도로 `AtomicMarkableReference`는 참조에 boolean 마크를 붙인다. 주로 "이 노드는 삭제 예정" 같은 플래그용이다.

---

## ThreadPoolExecutor 내부 동작

### 생성자 파라미터

```java
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    corePoolSize,        // 항상 유지하는 스레드 수
    maximumPoolSize,     // 최대 스레드 수
    keepAliveTime,       // corePoolSize 초과 스레드의 유휴 시간
    TimeUnit.SECONDS,
    workQueue,           // 대기 큐
    threadFactory,       // 스레드 생성 방식 (이름, 데몬 여부 등)
    rejectedHandler      // 큐와 풀이 다 찼을 때 정책
);
```

### 작업 제출 시 동작 순서

많은 사람이 "corePoolSize가 꽉 차면 maximumPoolSize까지 늘어난다"고 오해한다. 실제는 다르다.

1. 현재 스레드 수 < corePoolSize: **새 스레드를 만들어** 작업을 실행한다.
2. 현재 스레드 수 >= corePoolSize: **큐에 넣는다**.
3. 큐가 가득 차고, 현재 스레드 수 < maximumPoolSize: **새 스레드를 만들어** 작업을 실행한다.
4. 큐도 가득 차고 스레드도 maximumPoolSize: **거부 정책(RejectedExecutionHandler)** 실행.

즉, **큐가 무제한(`LinkedBlockingQueue`의 기본)이면 maximumPoolSize는 의미가 없다**. 스레드는 corePoolSize까지만 늘어나고 나머지는 전부 큐에 쌓인다. `Executors.newFixedThreadPool`이 이런 구조이고, OOM의 흔한 원인이다.

### 큐 선택이 동작을 결정한다

| 큐 종류 | 동작 |
|---------|------|
| `SynchronousQueue` | 저장 안 함. 소비자가 없으면 즉시 새 스레드 생성 또는 거부. `newCachedThreadPool`이 이걸 쓴다. |
| `LinkedBlockingQueue` (무제한) | 무한정 쌓임. maximumPoolSize 의미 없음. |
| `LinkedBlockingQueue(N)` | N개까지 쌓이다가 maximumPoolSize로 스레드가 증가. |
| `ArrayBlockingQueue(N)` | 위와 비슷하지만 고정 크기 배열 기반. |

프로덕션에서는 **반드시 큐 크기를 제한한다**. 큐가 무제한이면 서버가 죽기 전까지 문제를 모르고, 죽을 때는 힙 덤프가 수 GB로 나와 분석도 힘들어진다.

### 거부 정책

- `AbortPolicy` (기본): `RejectedExecutionException`을 던진다. 호출자가 예외 처리를 해야 한다.
- `CallerRunsPolicy`: 호출한 스레드가 직접 실행한다. 자연스러운 역압(backpressure)이 걸린다. 요청을 받는 톰캣 스레드가 막히게 되므로 유입이 줄어든다.
- `DiscardPolicy`: 조용히 버린다. 실수로 쓰면 장애를 모른다.
- `DiscardOldestPolicy`: 큐에서 가장 오래된 작업을 버린다. 순서가 의미 있으면 위험하다.

대부분의 서버 워크로드에서는 `CallerRunsPolicy`가 가장 무난하다. 메트릭 수집이나 로그처럼 손실 허용이 되는 작업만 `DiscardPolicy`를 고려한다.

### 흔한 튜닝 실수

```java
// 잘못된 예: 큐 무제한 + 큰 max
new ThreadPoolExecutor(
    10, 200, 60L, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>()  // 무제한 → max=200은 절대 도달 안 함
);
```

이 설정은 10개 스레드로만 처리하고 나머지는 전부 큐에 쌓는다. 트래픽 스파이크에 대응도 못 하고, 역압도 없어서 OOM으로 직행한다. 최소 `new LinkedBlockingQueue<>(500)` 수준으로 제한을 걸어야 한다.

---

## ForkJoinPool과 work-stealing

### 일반 스레드 풀과의 차이

`ThreadPoolExecutor`는 작업 큐가 하나다. 모든 스레드가 같은 큐에서 작업을 꺼내기 때문에 큐에 접근할 때 락 경합이 생긴다. `ForkJoinPool`은 **스레드마다 자기 데크(deque)를 가진다**. 자기 작업이 떨어지면 다른 스레드의 데크 꼬리에서 작업을 훔쳐온다(work-stealing).

이 구조는 **큰 작업을 작은 작업으로 계속 쪼개는 재귀 분할**에 최적화되어 있다. 쪼갠 서브태스크를 자기 데크에 넣으면 자기 스레드가 먼저 처리하고, 노는 스레드가 있으면 꼬리에서 훔쳐간다. 머지소트, 병렬 스트림, 재귀적 집계가 전형적인 예다.

### 공용 ForkJoinPool (common pool)

Java 8부터 JVM에 기본 내장된 풀이 있다. `ForkJoinPool.commonPool()`로 접근한다. 병렬 스트림(`.parallelStream()`)과 `CompletableFuture`의 기본 실행자가 이 공용 풀이다.

공용 풀의 기본 크기는 **CPU 코어 수 - 1**이다. 4코어면 3, 8코어면 7. 이 숫자는 매우 작다. 그리고 모든 병렬 스트림과 CompletableFuture가 같은 풀을 공유한다.

```java
// A 서비스의 코드
List<Integer> result = bigList.parallelStream()
    .map(this::callRemoteAPI)  // I/O 호출 (30초 걸림)
    .collect(Collectors.toList());
```

```java
// B 서비스의 코드
CompletableFuture.supplyAsync(() -> doImportantWork());  // 실행자 지정 안 함
```

A가 공용 풀의 스레드를 전부 점유하면 B는 실행을 기다려야 한다. **I/O 작업을 공용 풀에서 돌리면 절대 안 된다**. 공용 풀은 CPU 바운드 연산을 빠르게 끝내기 위한 것이다.

---

## CompletableFuture 주의사항

### 실행자를 반드시 지정한다

`supplyAsync`, `thenApplyAsync` 같은 Async 메서드는 실행자를 안 주면 공용 풀을 쓴다. 실무에서는 **전용 풀을 만들어서 항상 전달한다**.

```java
private static final ExecutorService IO_EXECUTOR =
    Executors.newFixedThreadPool(50, namedThreadFactory("io-"));

CompletableFuture.supplyAsync(() -> callExternalAPI(id), IO_EXECUTOR)
    .thenApplyAsync(data -> process(data), IO_EXECUTOR)
    .thenAccept(result -> save(result));
```

주의해야 할 건 **Async가 붙지 않은 메서드의 실행 스레드**다. `thenApply`, `thenAccept`는 **이전 단계의 완료 스레드**에서 실행된다. 이전 단계가 공용 풀에서 돌았으면 이 콜백도 공용 풀에서 돈다. 제어가 필요하면 Async 버전을 쓰고 실행자를 명시한다.

### 예외 전파

CompletableFuture는 예외가 나도 체인이 끊기지 않는다. 예외는 **캡슐화되어 다음 단계로 전달**된다.

```java
CompletableFuture.supplyAsync(() -> fetchUser(id))
    .thenApply(user -> user.getName())  // user가 null이면 NPE
    .thenApply(name -> name.toUpperCase())
    .exceptionally(ex -> {              // 앞에서 난 예외 전부 여기서 잡힘
        log.error("처리 실패", ex);
        return "UNKNOWN";
    });
```

`exceptionally`는 Throwable을 받아 정상 값을 반환한다. 복구가 목적이다. 로깅만 하고 예외는 그대로 전파하고 싶으면 `whenComplete`나 `handle`을 쓴다.

```java
future
    .whenComplete((result, ex) -> {
        if (ex != null) log.error("실패", ex);
    })
    .thenApply(result -> result.toUpperCase());  // 여기서 예외가 그대로 전파
```

`whenComplete`는 부수 효과만 수행하고 값/예외를 그대로 넘긴다. `handle`은 예외를 받아 새 값을 만들 수 있다.

### get() vs join()

`future.get()`은 체크드 예외 `InterruptedException`과 `ExecutionException`을 던진다. `future.join()`은 언체크드 `CompletionException`을 던진다. 스트림이나 람다 안에서는 `join()`이 편하다.

```java
List<String> results = futures.stream()
    .map(CompletableFuture::join)  // get()이면 try-catch 필요
    .collect(Collectors.toList());
```

다만 `join()`도 블로킹이라는 사실은 변하지 않는다. 비동기 체인의 끝에서만 쓰고, 중간에 넣지 않는다.

### 타임아웃 걸기

외부 API 호출은 반드시 타임아웃을 걸어야 한다. Java 9+에서는 `orTimeout`, `completeOnTimeout`을 지원한다.

```java
CompletableFuture.supplyAsync(() -> slowAPI())
    .orTimeout(3, TimeUnit.SECONDS)        // 3초 넘으면 TimeoutException
    .exceptionally(ex -> fallbackValue());

// 또는 타임아웃 시 기본값 반환
CompletableFuture.supplyAsync(() -> slowAPI())
    .completeOnTimeout(fallbackValue(), 3, TimeUnit.SECONDS);
```

Java 8을 쓴다면 직접 스케줄러로 타임아웃을 구현해야 한다.

---

## ThreadLocal의 함정

### 기본 사용과 메모리 모델

`ThreadLocal`은 스레드마다 독립된 값을 가진다. 내부적으로 `Thread` 객체가 `ThreadLocal.ThreadLocalMap`을 필드로 들고 있고, 이 맵의 key가 ThreadLocal 인스턴스(약한 참조), value가 실제 저장값(강한 참조)이다.

```java
private static final ThreadLocal<UserContext> USER_CONTEXT = new ThreadLocal<>();

public void handleRequest(Request req) {
    USER_CONTEXT.set(loadUser(req));
    try {
        businessLogic();  // USER_CONTEXT.get()으로 어디서든 접근
    } finally {
        USER_CONTEXT.remove();  // 반드시 제거
    }
}
```

### 메모리 누수

ThreadLocal은 스레드 풀과 조합되면 메모리 누수의 주범이 된다. 핵심은 **key는 weak reference지만 value는 strong reference**라는 점이다.

1. ThreadLocal 인스턴스를 더 이상 참조하지 않으면 key는 GC된다.
2. 그런데 value는 ThreadLocalMap에서 여전히 강하게 참조된다.
3. 스레드 풀의 스레드는 수명이 길기 때문에 맵이 계속 살아있다.
4. 결과: key는 사라졌지만 value는 메모리에 남는다.

ThreadLocal이 스레드에 남아있는 상태로 스레드 풀에서 같은 스레드를 재사용하면, 이전 요청의 값이 새 요청에 보인다. 인증 컨텍스트, 트랜잭션 정보가 섞이는 장애가 발생한다.

해결은 간단하다. **반드시 `remove()`로 정리한다**. Spring MVC라면 `HandlerInterceptor`의 `afterCompletion`에서 정리하는 게 안전하다. 라이브러리를 만들 때는 스스로 정리해주는 래퍼(try-with-resources)를 제공한다.

```java
public class ScopedContext implements AutoCloseable {
    public ScopedContext(UserContext ctx) { USER_CONTEXT.set(ctx); }
    public void close() { USER_CONTEXT.remove(); }
}

try (ScopedContext ignored = new ScopedContext(ctx)) {
    businessLogic();
}
```

### InheritableThreadLocal

자식 스레드가 부모의 값을 상속받게 한다. `Thread.init`에서 부모의 맵을 복사한다.

```java
private static final InheritableThreadLocal<String> TRACE_ID = new InheritableThreadLocal<>();
```

주의할 점은 **복사는 스레드 생성 시점에 한 번만** 일어난다는 것. 부모가 값을 나중에 바꿔도 자식에게 반영되지 않는다. 그리고 **스레드 풀의 스레드는 재사용되므로 첫 생성 시점의 값만 반영**된다. 로깅 MDC(trace_id) 같은 건 풀 환경에서는 직접 전파해야 한다.

### ScopedValue (Java 21+, preview)

`ThreadLocal`의 구조적 대안. 값이 특정 스코프 안에서만 유효하고, 불변이다.

```java
static final ScopedValue<User> USER = ScopedValue.newInstance();

ScopedValue.where(USER, currentUser).run(() -> {
    businessLogic();  // USER.get()으로 접근
});
// 스코프 종료 시 자동 정리
```

재할당이 없고, 스코프가 명확하며, 구조적 동시성(structured concurrency)과 잘 맞는다. ThreadLocal의 메모리 누수와 상속 문제가 없다. 앞으로는 이쪽이 표준이 될 가능성이 크다.

---

## 가상 스레드와 핀닝(pinning)

Java 21에서 정식 출시된 가상 스레드는 OS 스레드에 묶이지 않는 경량 스레드다. I/O에서 블로킹되면 OS 스레드에서 떨어져 나오고, 다른 가상 스레드가 그 OS 스레드를 쓴다. 수십만 개의 가상 스레드를 운용할 수 있다.

하지만 가상 스레드가 **특정 상황에서는 OS 스레드에 고정(pin)되어 떨어지지 못한다**. 이 상태를 핀닝이라 한다. 가상 스레드의 장점이 사라지고, 캐리어 스레드(OS 스레드)를 점유해서 다른 가상 스레드의 실행을 막는다.

### 핀닝이 발생하는 경우

- `synchronized` 블록 안에서 블로킹 호출: Java 21까지는 synchronized가 캐리어 스레드를 붙잡아둔다. Java 24에서 개선되어 대부분 해제됐다.
- JNI로 네이티브 코드 호출 중 블로킹: 예나 지금이나 이건 피할 수 없다.
- 파일 I/O: 커널이 비동기 API를 제공하지 않는 영역이라 캐리어에 묶인다.

### 실무 주의

Java 21 환경에서 가상 스레드로 마이그레이션할 때 가장 먼저 봐야 할 건 **라이브러리 내부의 `synchronized`**다. HTTP 클라이언트, JDBC 드라이버 같은 데 `synchronized`가 쓰여 있으면 가상 스레드의 장점이 사라진다. JVM 옵션 `-Djdk.tracePinnedThreads=full`을 켜면 핀닝이 일어날 때 스택 트레이스가 찍혀서 원인 파악이 된다.

`ReentrantLock`은 핀닝을 일으키지 않는다. 라이브러리를 새로 만든다면 가상 스레드 시대를 대비해 `synchronized` 대신 `ReentrantLock`을 쓰는 게 안전하다.

---

## 실제 트러블슈팅 사례

### 사례 1: 스레드 풀 고갈

증상: 서비스 응답이 갑자기 멈춘다. GC도 정상이고 CPU도 낮은데 요청이 처리되지 않는다.

원인 파악: 스레드 덤프를 뜨면 스레드 풀의 스레드 전체가 `WAITING` 또는 `TIMED_WAITING` 상태로 외부 API 응답을 기다리고 있다. 외부 API가 느려졌고, 클라이언트에 타임아웃이 없어서 풀이 전부 점유됐다.

```
"async-pool-1-thread-10" #42 WAITING
  at sun.nio.ch.NioSocketImpl$1.read
  ...
  at com.example.ExternalClient.call
```

해결:
- 모든 외부 호출에 타임아웃을 건다. HTTP 클라이언트, DB 커넥션, Redis, 전부.
- 스레드 풀을 기능별로 분리한다. 결제, 알림, 조회를 같은 풀로 묶으면 하나가 죽을 때 나머지도 죽는다.
- 서킷 브레이커를 붙여서 장애가 퍼지지 않게 한다.

### 사례 2: 공용 ForkJoinPool 오염

증상: A API가 평소엔 빠른데 가끔 응답이 몇 초로 튄다. B 팀이 배치를 돌리는 시간과 겹친다.

원인: B의 배치 코드가 `.parallelStream()`으로 대량 데이터를 처리한다. A의 다른 코드도 `CompletableFuture.supplyAsync()`를 실행자 없이 쓰고 있어서 공용 풀을 공유한다.

해결:
- 배치에서 병렬 스트림을 쓰지 않거나, 전용 ForkJoinPool을 만들어서 실행한다.
  ```java
  ForkJoinPool pool = new ForkJoinPool(8);
  pool.submit(() -> bigList.parallelStream().map(...).toList()).get();
  ```
- CompletableFuture는 항상 실행자를 명시한다.

### 사례 3: 무한 대기 (wait 조건 놓침)

증상: 생산자-소비자 큐에서 소비자가 가끔 영원히 멈춘다. 재시작하면 풀린다.

원인: `if (queue.isEmpty()) wait()` 패턴을 썼다. spurious wakeup 때문에 큐가 비어있는데도 깨어나거나, `notifyAll` 대신 `notify`를 써서 다른 스레드가 깨어나는 바람에 놓쳤다.

해결:
- `wait()`는 반드시 `while`로 감싼다.
- 대기 조건이 여러 종류면 `notifyAll`을 쓰거나, `ReentrantLock` + 여러 개의 `Condition`으로 분리한다.

### 사례 4: ThreadLocal 누수로 인한 세션 섞임

증상: 간헐적으로 다른 사용자의 정보가 응답에 섞여 나간다. 재현이 안 된다.

원인: 인증 정보를 ThreadLocal에 넣었는데 `remove()`를 빼먹었다. 톰캣 스레드 풀이 재사용되면서 이전 요청의 ThreadLocal 값이 남아 있었다. 특정 요청이 인증 정보를 set 하기 전에 이전 값을 읽는 경우가 생겼다.

해결:
- `try-finally`로 무조건 `remove()`.
- 커스텀 필터나 `HandlerInterceptor.afterCompletion`에서 강제 정리.
- AutoCloseable 래퍼로 감싸 누수 가능성 자체를 제거.

### 사례 5: 가상 스레드 핀닝

증상: 가상 스레드로 전환했는데 부하 테스트에서 기대만큼 처리량이 안 올라간다. 캐리어 스레드가 수십 개로 빠르게 늘어난다.

원인: 쓰고 있던 HTTP 클라이언트 라이브러리 내부에 `synchronized`가 있었다. 매 요청마다 락을 잡는 동안 캐리어가 붙잡혔다.

해결:
- `-Djdk.tracePinnedThreads=full`로 핀닝 지점 확인.
- 라이브러리를 `ReentrantLock` 기반으로 교체하거나 최신 버전으로 업그레이드.
- Java 24로 업그레이드하면 synchronized 핀닝 대부분이 해결된다.

---

## 정리

동시성 코드는 "돌긴 돈다"와 "언제나 맞다"의 간격이 크다. 단일 테스트에서 안 나타난 버그가 프로덕션 트래픽에서 하루에 한 번씩 터지는 일이 흔하다. 아래 정도만 지켜도 대부분의 재앙은 피할 수 있다.

- 메모리 가시성은 JMM의 happens-before로 설명되고, 실무에서는 synchronized/volatile/Lock 중 하나만 걸려 있으면 대체로 안전하다.
- 도구는 목적에 맞게. volatile은 플래그에만, synchronized는 단순 임계구역에, ReentrantLock은 제어가 필요할 때, Atomic은 CAS가 자연스러운 곳에만.
- ThreadPoolExecutor는 corePoolSize와 큐 크기 조합으로 동작이 결정된다. 무제한 큐는 피한다.
- 공용 ForkJoinPool에는 I/O를 올리지 않고, CompletableFuture는 항상 실행자를 명시한다.
- ThreadLocal은 써야 한다면 반드시 remove. 가능하면 ScopedValue로 넘어간다.
- 외부 호출에는 타임아웃을. 서킷 브레이커도 같이.
- 가상 스레드 환경에서는 synchronized와 JNI 블로킹을 조심한다.
