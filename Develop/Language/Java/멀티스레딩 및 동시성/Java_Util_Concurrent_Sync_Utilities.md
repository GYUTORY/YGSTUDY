---
title: java.util.concurrent 동기화 유틸리티 심화
tags: [java, concurrency, juc, aqs, countdownlatch, cyclicbarrier, semaphore, phaser, exchanger, blockingqueue, concurrenthashmap, copyonwritearraylist]
updated: 2026-06-05
---

# java.util.concurrent 동기화 유틸리티 심화

`synchronized`와 `Lock`만으로도 동시성 코드를 짤 수는 있다. 그런데 실무에서 마주치는 패턴 — "N개 작업이 끝날 때까지 기다리기", "동시 접근을 K개로 제한", "여러 라운드에 걸쳐 스레드를 모았다가 풀기" — 을 직접 구현하다 보면 코드가 더러워지고 버그가 새어 들어간다. `java.util.concurrent`(이하 JUC)의 유틸리티 클래스는 그런 패턴을 미리 만들어 둔 것이다.

이 문서는 사용법보다 **내부 구현이 어떻게 다른지**, **왜 어떤 클래스는 재사용이 되고 어떤 클래스는 안 되는지**, **컬렉션의 동기화 구조가 어떻게 짜여 있어서 어떤 코드가 위험한지**에 집중한다. 기존 `Java_Concurrency_Deep_Dive`가 JMM·락·CAS·스레드 풀의 메커니즘을 다뤘다면, 이 문서는 그 위에 올라간 유틸리티 레이어의 내부를 본다.

---

## AQS — 모든 동기화 유틸리티의 뼈대

`CountDownLatch`, `Semaphore`, `ReentrantLock`, `ReadWriteLock`, `FutureTask`까지 — JUC의 거의 모든 동기화 클래스는 `AbstractQueuedSynchronizer`(AQS) 위에 얹혀 있다. 이 사실을 알고 있으면 동작이 헷갈릴 때 가설을 세우기 쉽다.

AQS의 핵심은 두 가지다.

- `volatile int state` — 동기화의 의미를 담는 정수 한 개. 락이면 `0=unlocked, 1=locked`, 카운트다운이면 남은 카운트, 세마포어면 남은 퍼밋.
- FIFO 대기 큐 — 자원을 못 얻은 스레드가 노드로 매달리는 이중 연결 리스트.

서브클래스는 `tryAcquire(int)`, `tryRelease(int)`, `tryAcquireShared(int)`, `tryReleaseShared(int)`만 구현하면 된다. 대기 큐 관리, park/unpark, 인터럽트 처리는 AQS가 알아서 한다.

```java
// CountDownLatch의 Sync (AQS 서브클래스) 구현 골자
private static final class Sync extends AbstractQueuedSynchronizer {
    Sync(int count) { setState(count); }

    // 카운트가 0이면 통과, 아니면 대기
    protected int tryAcquireShared(int acquires) {
        return (getState() == 0) ? 1 : -1;
    }

    // 카운트 1 감소, 0이 되는 순간 true 반환 → 대기 스레드 전부 깨움
    protected boolean tryReleaseShared(int releases) {
        for (;;) {
            int c = getState();
            if (c == 0) return false;
            int nextc = c - 1;
            if (compareAndSetState(c, nextc))
                return nextc == 0;
        }
    }
}
```

`acquire`와 `acquireShared`의 차이는 자원을 한 명만 가져가느냐, 여러 명이 동시에 통과할 수 있느냐다. `ReentrantLock`은 한 명, `CountDownLatch`와 `Semaphore`(공평/비공평 모두)는 여러 명이 통과 가능하므로 shared 계열을 쓴다.

내부 큐는 CLH 변형이다. 자원을 못 얻은 스레드는 노드로 큐에 매달리고 `LockSupport.park()`로 잠든다. 앞 노드가 자원을 놓으면 `unpark`해서 깨운다. `park`/`unpark`는 OS 스케줄러 호출이라 비용이 있다 — 짧은 임계구역에서 락 경합이 심하면 AQS 기반 락보다 `synchronized`(JIT가 lock elision, biased lock 같은 최적화를 거는)가 빠른 경우도 있다.

---

## CountDownLatch — 한 번만 쓸 수 있는 카운터

가장 단순한 동기화 유틸리티. 생성자에서 카운트를 받고, `countDown()`이 호출될 때마다 1씩 줄어든다. 0이 되는 순간 `await()`로 대기 중이던 모든 스레드가 풀린다.

```java
CountDownLatch ready = new CountDownLatch(3);

executor.submit(() -> { warmupDb();     ready.countDown(); });
executor.submit(() -> { warmupCache();  ready.countDown(); });
executor.submit(() -> { warmupQueue();  ready.countDown(); });

ready.await();
startAcceptingTraffic();
```

내부적으로 카운트는 AQS의 `state`다. `countDown()`은 CAS로 state를 1 감소시키고, 0이 된 순간 `tryReleaseShared`가 true를 반환해 큐에 매달린 스레드를 전부 깨운다.

### 재사용 불가능하다

`CountDownLatch`는 state가 0에 도달하면 끝이다. 다시 1로 올리는 API가 없다. 1회용이다. "주기적으로 N개를 모았다가 풀고 싶다"면 `CyclicBarrier`나 `Phaser`를 봐야 한다.

처음 JUC를 쓸 때 흔히 하는 실수가 `CountDownLatch`를 멤버 변수로 두고 라운드마다 재활용하려는 것이다. 동작하지 않는다. 매 라운드 새 인스턴스를 만들거나 다른 유틸리티를 써야 한다.

### 카운트가 처음부터 0이면

`new CountDownLatch(0)`을 만들면 `await()`는 즉시 반환한다. 디버깅 중에 헷갈릴 수 있는데, 0이 곧 "끝난 상태"기 때문이다.

### await의 인터럽트와 타임아웃

`await()`는 인터럽트 가능하다. `awaitNanos`처럼 동작하는 타임아웃 버전(`await(long, TimeUnit)`)도 있다. 운영에서 서버 시작 같은 곳에 무한 `await()`만 걸어두면, 한 작업이 영원히 끝나지 않을 때 진단하기 어렵다. 30초나 1분 타임아웃을 걸고 어느 카운트가 못 내려갔는지 로깅하는 편이 낫다.

---

## CyclicBarrier — 라운드를 모았다가 풀기

`CountDownLatch`와 자주 비교되는데, 사용 시나리오가 정반대다. `CountDownLatch`는 "한 스레드가 N개의 다른 스레드 작업 완료를 기다린다", `CyclicBarrier`는 "N개의 스레드가 서로를 기다린다".

```java
CyclicBarrier barrier = new CyclicBarrier(4, () -> {
    System.out.println("4명 모두 도착, 다음 라운드 시작");
});

for (int i = 0; i < 4; i++) {
    int idx = i;
    executor.submit(() -> {
        for (int round = 0; round < 10; round++) {
            doRoundWork(idx, round);
            barrier.await();   // 4명 모두 await 호출하면 한꺼번에 풀린다
        }
    });
}
```

`CountDownLatch`와 달리 라운드가 끝나면 barrier가 자동으로 리셋된다. `await()`를 호출하는 스레드 수가 parties에 도달할 때마다 풀리고 다시 처음 상태로 돌아간다.

### 내부 구현 차이

`CyclicBarrier`는 AQS가 아니라 **`ReentrantLock` + `Condition`** 으로 구현된다. AQS가 단일 정수 state로는 표현하기 어려운 "라운드 번호 + 도착한 스레드 수 + 생성 시점" 같은 복합 상태가 필요하기 때문이다. 내부에 `Generation` 객체가 있어서 현재 라운드를 추적한다.

```java
// CyclicBarrier 내부 (간략화)
private static class Generation {
    boolean broken = false;
}

private final ReentrantLock lock = new ReentrantLock();
private final Condition trip = lock.newCondition();
private final int parties;
private int count;
private Generation generation = new Generation();

public int await() throws InterruptedException, BrokenBarrierException {
    lock.lock();
    try {
        Generation g = generation;
        if (g.broken) throw new BrokenBarrierException();
        int index = --count;
        if (index == 0) {
            runBarrierAction();
            nextGeneration();   // count 리셋, 새 Generation
            return 0;
        }
        for (;;) {
            trip.await();
            if (g.broken) throw new BrokenBarrierException();
            if (g != generation) return index;
        }
    } finally {
        lock.unlock();
    }
}
```

### BrokenBarrierException

가장 골치 아픈 부분이다. 한 스레드가 `await()`에서 인터럽트되거나 타임아웃되면, 그 라운드의 barrier는 깨진(broken) 상태가 된다. 같은 라운드에서 `await()` 중이던 다른 스레드들은 모두 `BrokenBarrierException`을 받고 빠져나온다.

이게 무서운 이유는 한 명이 죽으면 그 라운드 전체가 무효가 된다는 것이다. 운영에서 "병렬 배치 잡 N개를 모아서 다음 단계 가는" 패턴에 `CyclicBarrier`를 쓰다 보면, 한 잡이 GC 스파이크로 인터럽트되어서 전체가 죽는 사고가 난다. 복구하려면 `reset()`을 호출해 새 Generation으로 넘기는 로직이 별도로 필요하다.

### barrier action

생성자에 Runnable을 넣으면 마지막 스레드가 도착한 순간 그 Runnable이 실행되고, 그 다음에 모든 대기 스레드가 풀린다. 라운드 사이에 끼는 후처리(병합·집계)에 쓴다. 단, 이 action이 예외를 던지면 barrier가 broken 상태가 된다.

---

## Semaphore — 퍼밋 K개로 동시 접근 제한

이름은 어렵게 들리지만 동작은 단순하다. 퍼밋 K개를 들고 시작해서, `acquire()`로 1개 빌리고 `release()`로 반납한다. 퍼밋이 0이면 대기.

```java
// 외부 API 호출을 동시에 10개까지만 허용
Semaphore quota = new Semaphore(10);

void callExternalApi() {
    try {
        quota.acquire();
        try {
            httpClient.send(request);
        } finally {
            quota.release();
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}
```

### 공평/비공평 모드

`new Semaphore(10, true)`로 만들면 공평 모드다. 큐에 매달린 순서대로 퍼밋을 받는다. 디폴트는 비공평(false). 비공평 모드는 새로 들어온 스레드가 큐를 거치지 않고 바로 시도하기 때문에(barging) 처리량이 높지만, 운이 나쁘면 굶는다.

실무에서 외부 API 호출 같은 곳에 공평 모드를 쓰면 동시성 처리량이 떨어진다는 게 체감된다. 비공평이 디폴트인 이유다. 정말 공정한 순서가 필요한 곳(예: 같은 사용자의 요청을 순서대로 처리해야 하는 큐)에서만 공평을 켠다.

### 내부 구현

AQS shared 모드 그대로다. `state`가 남은 퍼밋 수다. `tryAcquireShared(int permits)`는 state에서 permits만큼 빼고 결과가 음수면 실패(대기), 양수면 성공. `tryReleaseShared`는 더하고 깨운다. `CountDownLatch`와의 차이는 카운트가 0이 되어도 끝이 아니라 계속 증감이 가능하다는 것.

### 누락된 release가 영구 데드락이 된다

`acquire()`만 호출하고 예외 경로에서 `release()`를 빼먹으면 퍼밋이 영구히 사라진다. 한두 번 누락되어도 당장은 처리량만 떨어진 것처럼 보이고, 며칠 뒤 모든 퍼밋이 사라져서 시스템이 멈춘다. 진단하기 어려우니 반드시 `try-finally`로 감싸야 한다.

### 음수 퍼밋과 reducePermits

생성자에 음수도 받는다(`new Semaphore(-3)`). 이 경우 누가 3번 release를 해야 0이 되고, 그 후 acquire가 가능해진다. 시스템 워밍업 중 일정 횟수만큼 release가 호출되기를 기다리는 패턴에 쓰인다. `reducePermits(int)`로 사후에 퍼밋을 줄일 수도 있는데 protected 메서드라 서브클래스에서만 노출된다.

---

## Phaser — 동적이고 계층적인 barrier

`CyclicBarrier`는 parties 수가 고정이고, `CountDownLatch`는 1회용이다. 둘 다 안 맞는 시나리오가 있다 — 라운드마다 참여자가 늘었다 줄었다 하는 작업. `Phaser`는 그걸 위해 만들어졌다.

```java
Phaser phaser = new Phaser(1);   // 메인 스레드 등록

for (int i = 0; i < 5; i++) {
    phaser.register();           // 워커 등록
    int idx = i;
    executor.submit(() -> {
        for (int round = 0; round < 3; round++) {
            doWork(idx, round);
            phaser.arriveAndAwaitAdvance();
        }
        phaser.arriveAndDeregister();   // 빠질 때 deregister
    });
}

phaser.arriveAndDeregister();    // 메인은 더 이상 참여 안 함
```

### CyclicBarrier와의 차이

- **동적 참여자**: `register()`/`arriveAndDeregister()`로 라운드 도중에 참여자 수를 바꿀 수 있다.
- **계층화**: parent Phaser를 줘서 자식 Phaser들을 묶을 수 있다. 워커가 수만 명일 때 단일 큐 경합을 피하려고 계층으로 나눈다.
- **phase 번호**: 라운드마다 phase가 증가한다(`getPhase()`). 누가 어느 라운드에 있는지 외부에서 확인 가능.
- **종료 가능**: 등록된 참여자가 모두 deregister하면 자동으로 terminate된다. `onAdvance(int phase, int parties)`를 오버라이드해 종료 조건을 커스텀할 수도 있다.

### 내부 구현

`Phaser`는 AQS도 `ReentrantLock`도 안 쓴다. 64비트 long 한 개에 phase(32비트) + unarrived count(16비트) + parties(16비트)를 패킹해서 CAS로 갱신한다. 대기는 `Treiber stack`(lock-free LIFO) 위에 노드를 쌓는다. 락 없이 돌아가서 경합이 심한 환경에서 빠르다.

### 운영 주의

- `register()` 호출이 안 된 스레드가 `arrive()`를 부르면 IllegalStateException이 난다.
- 참여자 수와 실제 작업 스레드 수를 일치시키지 않으면 다음 phase로 진행이 안 된다. deregister를 빠뜨리면 무한 대기로 직행한다.
- 메인 스레드 자신도 참여자로 등록해 둬야, 워커들이 도중에 모두 deregister해버려서 phaser가 죽는 사고를 막을 수 있다. 위 예제의 `new Phaser(1)`이 그 역할이다.

---

## Exchanger — 두 스레드 사이의 자료 교환

가장 덜 알려진 클래스. 정확히 두 스레드가 만나 데이터를 맞바꾼다.

```java
Exchanger<Buffer> exchanger = new Exchanger<>();

// 생산자
executor.submit(() -> {
    Buffer empty = new Buffer();
    while (running) {
        fillBuffer(empty);
        empty = exchanger.exchange(empty);   // 가득찬 버퍼를 넘기고 빈 버퍼를 받는다
    }
});

// 소비자
executor.submit(() -> {
    Buffer full = new Buffer();
    while (running) {
        full = exchanger.exchange(full);     // 빈 버퍼를 넘기고 가득찬 버퍼를 받는다
        consumeBuffer(full);
    }
});
```

생산자-소비자 패턴에서 더블 버퍼링을 락 없이 구현할 때 유용하다. 그런데 정확히 둘만 만나는 시나리오가 흔치 않아서 실무에서 자주 보이지는 않는다. `BlockingQueue`를 쓰는 편이 보통은 더 직관적이다.

내부적으로 슬롯 배열에 도착한 스레드가 자기 슬롯을 점유하고, 다음 도착자가 그 슬롯에서 만나는 방식이다. 경합이 심하면 슬롯 수를 늘려서 충돌을 줄이는 arena 구조를 쓴다. SynchronousQueue 내부와 닮았다.

---

## BlockingQueue 구현체 비교

JUC에서 가장 많이 쓰는 인터페이스다. 그런데 구현체마다 락 구조, 용량, 순서 정책이 다르다. 잘못 고르면 처리량이 반으로 떨어지거나 메모리가 새거나 한다.

### LinkedBlockingQueue

링크드 리스트 기반, 옵션으로 용량 제한. 가장 흔히 쓴다.

내부에 **putLock과 takeLock 두 개의 락**이 있다. head 쪽 take와 tail 쪽 put이 동시에 진행 가능하다. 생산자와 소비자가 같은 락을 두고 경합하지 않으니 처리량이 좋다.

```java
// LinkedBlockingQueue 골자
private final ReentrantLock putLock = new ReentrantLock();
private final Condition notFull = putLock.newCondition();
private final ReentrantLock takeLock = new ReentrantLock();
private final Condition notEmpty = takeLock.newCondition();
private final AtomicInteger count = new AtomicInteger();
```

**용량을 안 주면 Integer.MAX_VALUE다.** 이게 가장 흔한 사고 원인. `Executors.newFixedThreadPool()`이 내부적으로 무제한 LinkedBlockingQueue를 쓰기 때문에, 큐에 작업이 쌓이다가 OOM이 난다. 직접 `ThreadPoolExecutor`를 만들 때는 반드시 용량을 명시해야 한다.

### ArrayBlockingQueue

배열 기반 원형 버퍼, 용량 고정.

락이 하나다(put과 take가 같은 락). 처리량은 LinkedBlockingQueue보다 살짝 떨어진다. 대신 노드 객체를 안 만들어서 GC 압박이 적고, 메모리 사용이 예측 가능하다.

용량이 고정이고 변경이 불가능하다. 시스템 부하가 변동성이 있을 때는 LinkedBlockingQueue가 유연하지만, 절대 일정 크기를 초과하면 안 되는 메시지 버퍼에는 ArrayBlockingQueue가 더 안전하다.

공평 모드(`new ArrayBlockingQueue<>(cap, true)`)도 지원한다. Semaphore와 마찬가지로 켜면 처리량은 떨어진다.

### SynchronousQueue

용량 0. 저장 공간이 없다. put이 호출되면 take를 기다리는 누군가가 있을 때만 직접 전달이 일어난다. 둘 중 한쪽이 없으면 블록.

이상하게 보이지만 핸드오프(hand-off) 큐로 유용하다. `Executors.newCachedThreadPool()`이 SynchronousQueue를 쓴다. 작업이 들어오면 대기 중인 스레드에 즉시 넘기고, 없으면 새 스레드를 만든다. 큐에 쌓을 자리가 없으니 풀이 무한히 늘어날 위험이 있다 — 이게 `newCachedThreadPool`을 운영에서 쓰지 말라는 이유다.

내부는 두 가지 모드(공평=TransferQueue, 비공평=TransferStack)가 있다. 락 없이 CAS와 park/unpark로만 돌아가는 lock-free 자료구조다.

### PriorityBlockingQueue

힙 기반 우선순위 큐. 용량 무제한(필요시 자동 확장).

원소가 `Comparable`이거나 생성자에 `Comparator`를 줘야 한다. 들어간 순서가 아니라 우선순위 순서로 나온다.

주의할 점이 몇 개 있다.

- **용량 제한이 안 된다.** 무한히 쌓을 수 있어서 백프레셔가 필요한 곳에는 부적합하다.
- **iterator 순서가 정렬 순서가 아니다.** 힙은 부분 순서만 보장한다. 디버깅 로그에서 보고 헷갈리지 말자.
- **drainTo도 정렬 순서로 안 빠진다.** 정렬 순서로 비우려면 반복적으로 poll해야 한다.

### DelayQueue

원소가 `Delayed` 인터페이스를 구현해야 한다. `getDelay()`가 0 이하인 원소만 꺼낼 수 있다. 내부적으로 PriorityBlockingQueue로 만료 시간 순으로 정렬되어 있다.

`ScheduledThreadPoolExecutor`가 내부적으로 이걸 쓴다. 스케줄링이 필요한 큐, 예를 들어 "5분 후에 처리할 작업" 같은 곳에 직접 쓰기도 한다.

```java
class Task implements Delayed {
    private final long executeAt;

    public long getDelay(TimeUnit unit) {
        return unit.convert(executeAt - System.currentTimeMillis(), TimeUnit.MILLISECONDS);
    }

    public int compareTo(Delayed o) {
        return Long.compare(this.executeAt, ((Task) o).executeAt);
    }
}
```

함정: `take()`는 만료된 원소를 기다린다. 큐에 만료 안 된 원소만 있으면 영원히 안 나온다. 처음 쓸 때 헷갈리는 부분이다.

### LinkedTransferQueue

Java 7부터 추가된 비교적 새 구현체. TransferQueue 인터페이스를 구현한다.

`put`/`offer`(전형적인 큐), `take`/`poll`(전형적인 큐) 외에 **`transfer(e)`** 가 핵심이다. 소비자가 이 원소를 받아갈 때까지 블록한다. 즉, 큐에 쌓는 게 아니라 직접 전달을 보장한다.

```java
LinkedTransferQueue<String> q = new LinkedTransferQueue<>();

// 소비자가 take할 때까지 블록
q.transfer("urgent message");

// 대기 중인 소비자가 있으면 즉시 전달, 없으면 큐에 쌓는다
q.put("normal message");
```

내부적으로 lock-free 알고리즘(dual queue)을 쓴다. 경합이 심한 환경에서 LinkedBlockingQueue보다 빠르다. 우선순위가 다른 메시지가 섞인 시스템에서 "이 메시지는 반드시 즉시 처리되어야 한다"는 시맨틱을 만들 때 쓰인다.

### 정리: 언제 무엇을 쓸까

| 구현체 | 락 | 용량 | 쓸 곳 |
|--------|----|------|-------|
| LinkedBlockingQueue | put/take 분리 | 옵션(미지정시 무한) | 일반적인 생산자-소비자, 처리량 우선 |
| ArrayBlockingQueue | 단일 락 | 고정 | 메모리 예측, 부하 상한 보장 |
| SynchronousQueue | lock-free | 0 | 핸드오프, cached pool |
| PriorityBlockingQueue | 단일 락 | 무한 | 우선순위 처리 |
| DelayQueue | 단일 락 | 무한 | 스케줄링, 만료 처리 |
| LinkedTransferQueue | lock-free | 무한 | transfer 시맨틱 필요시 |

---

## ConcurrentHashMap의 내부 동기화 구조

`Collections.synchronizedMap()`은 모든 연산을 객체 단위 락으로 묶는다. 읽기조차 락을 잡는다. 쓸 일이 거의 없다. 실무에서는 `ConcurrentHashMap`이 디폴트다.

### Java 7까지: 세그먼트 기반

Java 7의 ConcurrentHashMap은 내부적으로 Segment 배열을 가졌다. 각 Segment가 작은 해시테이블이고, 자기만의 `ReentrantLock`을 가진다. 기본 16개 세그먼트. 쓰기 연산은 키의 해시로 세그먼트를 골라 그 락만 잡았기 때문에 16개 스레드까지 동시 쓰기가 가능했다.

세그먼트 수가 부족하면 경합이 심하고, 너무 많으면 메모리 낭비였다. 그리고 size()나 isEmpty() 같은 전체 연산은 모든 세그먼트 락을 잡아야 해서 느렸다.

### Java 8 이후: 노드 단위 + CAS

Java 8에서 구조가 완전히 바뀌었다. 세그먼트 개념을 버리고, **버킷(노드) 단위로 동기화**한다.

- 빈 버킷에 첫 노드를 넣을 때는 CAS 한 번으로 끝낸다. 락 없음.
- 이미 노드가 있는 버킷에 충돌이 나면, 그 첫 노드를 `synchronized` 모니터로 잡고 체인을 수정한다.
- 한 버킷의 충돌이 8을 넘으면 그 버킷만 트리(red-black tree)로 바꾼다. 검색이 O(log n)으로 떨어진다.

```java
// putVal 골자 (Java 8+)
final V putVal(K key, V value, boolean onlyIfAbsent) {
    int hash = spread(key.hashCode());
    for (Node<K,V>[] tab = table;;) {
        Node<K,V> f; int n, i, fh;
        if (tab == null || (n = tab.length) == 0)
            tab = initTable();
        else if ((f = tabAt(tab, i = (n - 1) & hash)) == null) {
            // 빈 버킷: CAS만으로 노드 삽입
            if (casTabAt(tab, i, null, new Node<>(hash, key, value, null)))
                break;
        }
        else if ((fh = f.hash) == MOVED)
            tab = helpTransfer(tab, f);   // resize 진행 중이면 도와준다
        else {
            // 충돌: 버킷 헤드 노드에 synchronized
            synchronized (f) {
                // ... 체인 또는 트리에 삽입
            }
        }
    }
}
```

핵심은 락 granularity가 버킷 단위라는 것. 동시 쓰기 한계가 사실상 버킷 수와 같아진다(기본 16부터 resize되며 늘어남).

### size()는 정확하지 않다

Java 8 이후 size()는 `LongAdder` 같은 분산 카운터를 쓴다. 정확한 값이 아니라 "어느 시점의 근사값"이다. 동시에 쓰기가 일어나면 값이 살짝 어긋날 수 있다. 정확한 카운트가 필요하면 외부에서 별도 카운터를 두거나 다른 자료구조를 써야 한다.

### computeIfAbsent의 락 범위

이 메서드가 가장 자주 사고를 부른다.

```java
Map<String, ExpensiveValue> cache = new ConcurrentHashMap<>();

ExpensiveValue v = cache.computeIfAbsent(key, k -> buildExpensiveValue(k));
```

문서상으로 `computeIfAbsent`는 키가 없을 때만 람다를 실행하고, 같은 키에 대해 람다가 동시에 실행되지 않도록 보장한다. 매력적이다. 그런데 **이 람다는 해당 버킷의 락을 잡은 상태에서 실행된다.**

여기서 두 가지 문제가 생긴다.

**문제 1: 람다 안에서 같은 맵에 접근하면 데드락 또는 무한 루프.**

```java
// 절대 금지 — Java 9 미만에서는 무한 루프, 9+에서는 IllegalStateException
ConcurrentHashMap<String, String> m = new ConcurrentHashMap<>();
m.computeIfAbsent("a", k -> {
    return m.computeIfAbsent("b", k2 -> "v");   // 같은 맵에 다시 들어간다
});
```

같은 버킷에 들어가면 데드락이고, 다른 버킷이라도 resize 중이면 깨질 수 있다. Java 9부터는 일부 경우에 IllegalStateException을 던지지만 모든 경우가 잡히지는 않는다.

**문제 2: 람다가 오래 걸리면 그 버킷의 다른 키도 막힌다.**

해시가 같은 버킷에 떨어진 다른 키도 락을 기다린다. 외부 API 호출이나 DB 쿼리를 람다 안에서 하면, 그 동안 같은 버킷의 다른 키 접근이 전부 블록된다. 캐시 워밍에서 자주 본다.

해결책은 람다를 짧게 유지하고, 무거운 계산은 락 밖에서 한 다음 putIfAbsent로 넣는 것이다.

```java
// 락 안에서 계산하지 않는 패턴
ExpensiveValue v = cache.get(key);
if (v == null) {
    ExpensiveValue computed = buildExpensiveValue(key);   // 락 밖에서 계산
    v = cache.putIfAbsent(key, computed);
    if (v == null) v = computed;
}
```

물론 이건 "같은 키에 대해 동시에 두 번 계산될 수 있음"을 받아들이는 트레이드오프다. 계산이 멱등하면 괜찮지만, 외부 자원 점유나 비용이 큰 작업이면 람다 락을 받아들이거나 별도 락 매니저를 둬야 한다.

### compute, merge도 같은 락 범위

`compute`, `merge`, `computeIfPresent` 전부 동일하게 버킷 락을 잡는다. 그 안에서 다른 맵 연산이나 외부 호출을 넣을 때 같은 주의가 필요하다.

### 읽기는 락이 없다

`get()`은 락을 안 잡는다. volatile 필드와 happens-before에 기댄다. 다만 약한 일관성(weakly consistent)이다. iterator도 마찬가지로 락 없이 동작하고, 순회 도중에 일어난 변경을 일부 반영할 수 있고 일부는 못 반영할 수도 있다. ConcurrentModificationException은 안 던진다.

---

## CopyOnWriteArrayList의 쓰기 비용

이름이 모든 걸 말해준다. 쓰기가 일어날 때마다 내부 배열을 통째로 복사한다.

```java
// add 골자
public boolean add(E e) {
    synchronized (lock) {
        Object[] es = getArray();
        int len = es.length;
        Object[] newElements = Arrays.copyOf(es, len + 1);
        newElements[len] = e;
        setArray(newElements);
        return true;
    }
}
```

쓰기는 O(n)이다. n이 1000이면 1000개 원소 복사. 빈번한 쓰기에는 절대 쓰면 안 된다.

대신 읽기는 락이 전혀 없고, iterator도 스냅샷에 대해 도는 거라 ConcurrentModificationException이 절대 안 난다.

### 적합한 시나리오

- **읽기가 압도적으로 많고 쓰기가 거의 없는 경우.** 리스너 콜백 리스트, 설정값 캐시, 인터셉터 체인 같은 곳.
- **iterator 순회 중에 컬렉션이 바뀌어도 예외 없이 끝까지 가야 하는 경우.** 이벤트 디스패처에서 자주 본다.

### 부적합한 시나리오

- **쓰기가 자주 있는 경우.** 한 요청마다 한 번씩 add하는 로그 버퍼 같은 곳에 쓰면 GC가 폭주한다.
- **컬렉션이 큰 경우.** 1만 개 리스트에 add 한 번이 1만 개 복사다.
- **모든 변경이 일관되게 보여야 하는 경우.** iterator는 스냅샷이라서 시작 시점의 데이터만 본다.

### CopyOnWriteArraySet

같은 자료구조를 Set으로 감싼 것. 안에서 contains를 호출해서 중복을 거른다. add가 O(n²)에 가까워진다. 이름값을 한다고 보기 어려워서, 작은 Set이고 거의 안 바뀐다는 게 보장될 때만 쓴다.

---

## 실무 트러블슈팅 사례

### 사례 1: computeIfAbsent 안에서 외부 API 호출

캐시 미스 시 외부 API로 값을 가져오는 코드. 처음엔 잘 돌다가 트래픽이 늘자 갑자기 응답시간이 폭증했다.

```java
// 문제 코드
Map<String, Profile> cache = new ConcurrentHashMap<>();

public Profile getProfile(String id) {
    return cache.computeIfAbsent(id, k -> profileApi.fetch(k));  // API 호출이 락 안에서
}
```

같은 버킷에 떨어진 다른 키들이 줄줄이 막혔다. profileApi.fetch가 200ms 걸리는데, 같은 버킷에 20개 키가 들어 있으면 마지막 요청은 4초 대기.

해결은 caffeine 같은 외부 캐시 라이브러리로 옮기거나(자체 비동기 로딩), 락 밖에서 계산 후 putIfAbsent로 바꾸거나, 키별 락을 별도로 관리하는 방식.

### 사례 2: newFixedThreadPool의 무제한 큐

배치 잡 처리에 `Executors.newFixedThreadPool(20)`을 썼다. 어느 날 갑자기 OOM. 힙 덤프를 보니 LinkedBlockingQueue에 작업 객체가 수십만 개 쌓여 있었다.

`Executors.newFixedThreadPool`은 내부적으로 `new LinkedBlockingQueue<>()`를 쓴다. 용량 Integer.MAX_VALUE. 생산 속도가 소비 속도를 초과하면 큐가 무한히 부푼다.

해결은 직접 ThreadPoolExecutor를 만들어 용량을 명시하고, RejectedExecutionHandler를 두는 것.

```java
new ThreadPoolExecutor(
    20, 20, 0L, TimeUnit.MILLISECONDS,
    new LinkedBlockingQueue<>(1000),         // 명시적 용량
    new ThreadPoolExecutor.CallerRunsPolicy() // 백프레셔
);
```

### 사례 3: CyclicBarrier가 한 번 깨지면 복구가 안 됐다

여러 워커가 매분 데이터를 모아서 집계하는 잡. CyclicBarrier로 동기화. 어느 워커가 인터럽트되면 BrokenBarrierException이 나면서 그 분의 집계가 실패했는데, 다음 분도 계속 실패했다.

barrier가 broken 상태로 남아 있어서다. `reset()`을 명시적으로 호출하지 않으면 다음 라운드도 broken으로 시작한다. catch 블록에서 reset()을 호출하고 다음 라운드부터 새로 시작하는 로직을 넣어 해결.

### 사례 4: PriorityBlockingQueue에 무한히 쌓였다

알림 처리에 PriorityBlockingQueue를 썼다. 우선순위 높은 알림을 먼저 처리하고 싶었다. 외부 SMS 게이트웨이가 느려지자 큐에 쌓이기 시작했고, 용량 제한이 없으니 메모리가 계속 늘다 OOM.

PriorityBlockingQueue는 용량 제한이 없다는 점이 명확하지 않으면 놓치기 쉽다. 해결은 사이즈를 주기적으로 측정해서 임계치를 넘으면 우선순위 낮은 작업을 버리는 로직 추가. 또는 두 단계로 나눠 1차 큐는 우선순위 큐(작은 용량), 2차 처리는 ArrayBlockingQueue로 백프레셔.

### 사례 5: CopyOnWriteArrayList에 로그를 쌓았다

스레드 안전한 리스트가 필요해서 CopyOnWriteArrayList를 쓴 사례. 한 요청마다 add 한 번. 트래픽이 늘자 GC 시간이 폭증.

CopyOnWriteArrayList는 쓰기마다 배열 복사. 5만 개 원소가 쌓인 상태에서 add 한 번이 5만 개 객체 복사. 게다가 이전 배열은 GC 대상이 되어 압박이 가중.

용도가 잘못된 것. 로그 누적은 일반 큐(LinkedBlockingQueue 등)로 받고 별도 스레드가 비우는 구조로 변경.

### 사례 6: Phaser deregister 누락

동적 워커 풀에서 Phaser로 라운드 동기화. 워커가 예외로 죽었는데 deregister를 안 했더니, 다음 라운드에서 phaser가 영원히 advance를 안 했다.

`arriveAndDeregister()`는 finally 블록에서 호출해야 한다. 예외 경로에서 빠뜨리면 phase가 멈춘다.

```java
try {
    while (!phaser.isTerminated()) {
        doWork();
        phaser.arriveAndAwaitAdvance();
    }
} finally {
    phaser.arriveAndDeregister();
}
```

---

## 정리

JUC 유틸리티의 차이는 결국 내부 동기화 메커니즘의 차이다.

- AQS 기반(`CountDownLatch`, `Semaphore`)은 단일 정수 state로 모델링되는 동기화에 쓴다. 단순하고 빠르다.
- `ReentrantLock + Condition` 기반(`CyclicBarrier`)은 복합 상태가 필요할 때.
- Lock-free CAS 기반(`Phaser`, `SynchronousQueue`, `LinkedTransferQueue`)은 경합이 극심한 환경에서 처리량이 좋다.

컬렉션은 락 granularity의 차이다. `Collections.synchronizedMap`은 객체 단위, `ConcurrentHashMap`은 버킷 단위, `CopyOnWriteArrayList`는 락 대신 불변 스냅샷.

실무에서 사고는 대부분 **이 메커니즘을 모르고 쓸 때** 난다. computeIfAbsent 안에서 외부 호출을 한다든가, LinkedBlockingQueue 용량을 안 준다든가, CyclicBarrier가 broken 상태 복구 안 된다든가, CopyOnWriteArrayList에 매 요청 쓴다든가. 사용법만 알고 쓰면 운영에서 한 번씩은 데인다.
