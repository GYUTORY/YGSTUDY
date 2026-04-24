---
title: Java Queue
tags: [language, java, 컬렉션-및-데이터-처리, collectionframework, queue, blockingqueue, deque, concurrentlinkedqueue]
updated: 2026-04-24
---

# Java Queue

## Queue 인터페이스 개요

`Queue`는 FIFO(First-In-First-Out) 구조를 정의하는 인터페이스다. `java.util.Collection`을 확장하며, 추가/조회/제거 연산을 각각 두 가지 방식으로 제공한다. 두 방식의 차이는 단 하나 — 실패 시 예외를 던지느냐, 특수값을 반환하느냐다.

| 연산 | 예외 발생 | 특수값 반환 |
|------|-----------|-------------|
| 삽입 | `add(e)` | `offer(e)` |
| 제거 | `remove()` | `poll()` |
| 조회 | `element()` | `peek()` |

`add()`는 용량 초과 시 `IllegalStateException`을 던진다. `offer()`는 `false`를 반환한다. `remove()`와 `element()`는 큐가 비었을 때 `NoSuchElementException`을 던진다. `poll()`과 `peek()`은 `null`을 반환한다.

대부분의 경우 `offer()`와 `poll()`을 쓴다. 예외로 분기를 처리하는 것보다 반환값으로 처리하는 편이 코드가 단순해진다.

### BlockingQueue가 추가하는 메서드

`java.util.concurrent.BlockingQueue`는 여기에 블로킹 연산 두 개를 추가한다.

| 연산 | 메서드 | 동작 |
|------|--------|------|
| 삽입 | `put(e)` | 공간이 생길 때까지 스레드 블로킹 |
| 제거 | `take()` | 요소가 생길 때까지 스레드 블로킹 |

`put()`/`take()`는 `InterruptedException`을 던진다. 생산자-소비자 패턴 구현 시 핵심 메서드다.

---

## 구현체 선택

### ArrayDeque vs LinkedList

단순 큐로 쓸 때는 `ArrayDeque`를 선택한다.

`LinkedList`는 각 노드에 이전/다음 포인터를 저장하는 이중 연결 리스트다. 삽입/삭제는 O(1)이지만 노드마다 추가 메모리를 할당한다. 요소 100만 개를 넣으면 노드 객체 100만 개가 힙에 올라간다. GC 압박이 생기고 CPU 캐시 미스가 잦아진다.

`ArrayDeque`는 내부적으로 원형 배열을 쓴다. 배열이 꽉 차면 2배 크기로 재할당한다. 연속된 메모리에 요소가 있어서 캐시 효율이 좋다. Oracle 공식 문서도 "ArrayDeque is likely to be faster than Stack when used as a stack, and faster than LinkedList when used as a queue"라고 명시한다.

`LinkedList`를 선택해야 하는 경우는 드물다. 중간 삽입/삭제가 빈번하고, 그 인덱스를 직접 들고 있는 경우 정도다.

```java
// Queue로만 쓸 때는 ArrayDeque
Queue<String> queue = new ArrayDeque<>();

// Deque 기능도 필요할 때도 ArrayDeque
Deque<String> deque = new ArrayDeque<>();
```

### Deque 인터페이스와 Queue의 관계

`Deque`(Double-Ended Queue)는 `Queue`를 확장한 인터페이스다. 양 끝에서 삽입/삭제가 가능하다. `ArrayDeque`와 `LinkedList`는 둘 다 `Deque`를 구현한다.

```
Queue
  └── Deque
        ├── ArrayDeque
        └── LinkedList
```

큐 전용 메서드와 덱 전용 메서드가 섞여 있어 혼란스러울 수 있다.

| Queue 메서드 | Deque 대응 메서드 |
|------------|-----------------|
| `offer(e)` | `offerLast(e)` |
| `poll()` | `pollFirst()` |
| `peek()` | `peekFirst()` |

변수 타입을 `Queue<T>`로 선언하면 `Deque` 전용 메서드를 실수로 호출하는 일이 없다. 양방향이 필요할 때만 `Deque<T>`로 선언한다.

---

## BlockingQueue 계열

멀티스레드 환경에서 큐를 공유할 때 쓴다. `synchronized` 없이 스레드 안전하게 동작한다.

### ArrayBlockingQueue

내부 배열 크기가 고정된다. 생성 시 반드시 용량을 지정해야 한다.

```java
BlockingQueue<String> queue = new ArrayBlockingQueue<>(1000);
```

용량을 초과하면 `put()`은 블로킹되고, `offer()`는 `false`를 반환한다. 메모리 사용량이 예측 가능해서 부하가 큰 시스템에서 배압(backpressure) 제어 용도로 많이 쓴다.

공정성(fairness) 옵션도 있다. `new ArrayBlockingQueue<>(1000, true)`로 생성하면 대기 중인 스레드가 순서대로 접근한다. 처리량이 떨어지지만 스레드 기아 현상을 막는다.

### LinkedBlockingQueue

기본 용량은 `Integer.MAX_VALUE`다. 용량을 지정하지 않으면 사실상 무제한이다. 이게 운영 중 메모리 문제를 일으키는 흔한 원인이다.

```java
// 위험 - 메모리 무제한 소모 가능
BlockingQueue<Task> queue = new LinkedBlockingQueue<>();

// 안전 - 용량 명시
BlockingQueue<Task> queue = new LinkedBlockingQueue<>(10_000);
```

`ArrayBlockingQueue`와 달리 락이 두 개다. 삽입 락과 제거 락을 분리해서 생산자와 소비자가 동시에 접근할 수 있다. 생산자-소비자의 처리 속도가 비슷하고 처리량이 중요한 경우 `ArrayBlockingQueue`보다 빠를 수 있다.

### PriorityBlockingQueue

`PriorityQueue`의 스레드 안전 버전이다. 내부적으로 힙 구조를 쓴다. 용량 상한이 없다 — `put()`이 블로킹되지 않는다. 메모리가 허락하는 한 계속 삽입된다.

요소는 반드시 `Comparable`을 구현하거나, 생성자에 `Comparator`를 넘겨야 한다. 그렇지 않으면 `ClassCastException`이 런타임에 발생한다.

```java
PriorityBlockingQueue<Task> queue = new PriorityBlockingQueue<>(
    100,
    Comparator.comparingInt(Task::getPriority)
);
```

### 생산자-소비자 패턴 구현

```java
public class TaskProcessor {
    private final BlockingQueue<Runnable> taskQueue = new LinkedBlockingQueue<>(5000);

    // 생산자 - 여러 스레드에서 동시 호출 가능
    public boolean submit(Runnable task) {
        return taskQueue.offer(task); // 꽉 찼으면 false 반환
    }

    // 소비자 - 별도 스레드에서 실행
    public void startWorker() {
        Thread worker = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Runnable task = taskQueue.take(); // 요소가 없으면 대기
                    task.run();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt(); // 인터럽트 상태 복원
                    break;
                }
            }
        });
        worker.setDaemon(true);
        worker.start();
    }
}
```

`take()`에서 `InterruptedException`이 발생하면 인터럽트 상태를 반드시 복원해야 한다. 그냥 삼키면 종료 신호를 놓쳐서 스레드가 멈추지 않는다.

---

## ConcurrentLinkedQueue

`BlockingQueue`가 아니다. 블로킹 없이 스레드 안전한 큐가 필요할 때 쓴다.

내부 구현은 CAS(Compare-And-Swap) 연산 기반이다. 락을 사용하지 않고 원자적 연산만으로 삽입/제거를 처리한다. 락 경합이 없어서 스레드가 많을수록 `synchronized` 기반 구현보다 처리량이 높다.

```java
ConcurrentLinkedQueue<Event> eventQueue = new ConcurrentLinkedQueue<>();

// 여러 스레드에서 동시에 안전하게 호출 가능
eventQueue.offer(new Event("user.login", userId));

// 처리 스레드
Event event = eventQueue.poll(); // null 반환 가능 - 블로킹 없음
if (event != null) {
    handle(event);
}
```

주의할 점이 있다. `size()`가 O(n)이다. 내부적으로 전체를 순회한다. `isEmpty()`는 O(1)이므로 크기 확인이 필요하면 카운터를 별도로 관리하거나 `isEmpty()`로 대체한다.

`BlockingQueue`와 달리 배압 제어가 없다. 소비자가 느리면 큐가 계속 커진다. 생산-소비 속도 균형이 맞지 않는 상황에서는 `LinkedBlockingQueue`에 용량을 지정하는 편이 낫다.

---

## PriorityQueue 사용 시 주의사항

### equals와 compareTo 불일치 버그

`PriorityQueue`는 `compareTo()`(또는 `Comparator`)로 순서를 결정하지만, `contains()`나 `remove(Object)`는 `equals()`를 쓴다. 둘이 일치하지 않으면 예상과 다르게 동작한다.

```java
class Task implements Comparable<Task> {
    String name;
    int priority;

    @Override
    public int compareTo(Task other) {
        return Integer.compare(this.priority, other.priority);
    }

    // equals를 재정의하지 않음 - Object.equals() 사용 (참조 비교)
}

PriorityQueue<Task> queue = new PriorityQueue<>();
Task task = new Task("A", 1);
queue.offer(task);

Task sameTask = new Task("A", 1); // 다른 객체, 같은 값
queue.contains(sameTask); // false - equals가 참조 비교라서
queue.remove(sameTask);   // 제거 안 됨
```

`compareTo()`에서 같다고 판단되는 두 객체가 `equals()`에서 다르다면, `Set`이나 `Map`에 넣을 때도 의도치 않게 중복이 허용된다. `compareTo()`와 `equals()`의 일관성은 `Comparable` 계약의 권고사항이지만, `PriorityQueue`에서는 실질적인 버그 원인이 된다.

---

## 실무 사용 사례

### Spring 비동기 이벤트 큐

Spring의 `ApplicationEventPublisher`와 `@Async`를 쓰면 내부적으로 태스크 큐를 사용한다. `ThreadPoolTaskExecutor`의 `queueCapacity` 설정이 이 큐의 용량이다.

```java
@Bean
public Executor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(20);
    executor.setQueueCapacity(500); // 명시적 설정 필수
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
    executor.initialize();
    return executor;
}
```

`queueCapacity`를 설정하지 않으면 기본값이 `Integer.MAX_VALUE`다. 요청이 몰릴 때 메모리가 급격히 증가한다. 거부 정책(`RejectedExecutionHandler`)도 함께 설정해야 큐가 꽉 찼을 때의 동작을 제어할 수 있다.

### 이벤트 처리 파이프라인

여러 스테이지를 거치는 처리 파이프라인에서 스테이지 간 버퍼로 `BlockingQueue`를 쓴다.

```java
public class Pipeline {
    private final BlockingQueue<RawEvent> rawQueue = new ArrayBlockingQueue<>(1000);
    private final BlockingQueue<ParsedEvent> parsedQueue = new ArrayBlockingQueue<>(1000);

    // 1단계: 수집
    public void ingest(RawEvent event) {
        if (!rawQueue.offer(event)) {
            // 큐가 가득 찼을 때 처리 - 드롭, 로깅, 배압 신호 등
            log.warn("Raw queue full, dropping event: {}", event.getId());
        }
    }

    // 2단계: 파싱 워커
    // 3단계: 저장 워커
}
```

각 큐에 용량을 지정하면 특정 스테이지가 느려졌을 때 파이프라인 전체가 멈추는 대신, 그 앞 스테이지에서 배압이 발생한다.

---

## 자주 겪는 문제

### capacity 미지정으로 인한 메모리 이슈

`LinkedBlockingQueue`를 용량 없이 쓰다가 소비자가 느려지면 큐에 수십만 건이 쌓인다. 힙 사용량이 급증하고 GC가 빈번해지며 결국 OOM이 발생한다. 운영에 올리기 전에 반드시 용량을 명시한다.

### poll과 take 혼용으로 인한 스레드 블로킹

`poll()`은 비블로킹이고 `take()`는 블로킹이다. 메인 스레드나 요청 처리 스레드에서 `take()`를 잘못 호출하면 해당 스레드가 큐에 요소가 생길 때까지 멈춘다. 타임아웃이 있는 `poll(timeout, unit)`이 더 안전한 경우가 많다.

```java
// 위험 - 요소가 없으면 무한 대기
Runnable task = taskQueue.take();

// 안전 - 1초 대기 후 null 반환
Runnable task = taskQueue.poll(1, TimeUnit.SECONDS);
if (task != null) {
    task.run();
}
```

### PriorityQueue null 삽입 금지

`PriorityQueue`는 `null`을 허용하지 않는다. `offer(null)` 시 `NullPointerException`이 발생한다. `LinkedList`로 구현된 큐는 `null`을 허용하기 때문에, 구현체를 교체할 때 버그가 생기는 경우가 있다.
