---
title: Java 멀티스레딩
tags: [language, java, 멀티스레딩, thread, 동시성, volatile, deadlock]
updated: 2026-03-25
---

# Java 멀티스레딩

## 스레드 생성

Java에서 스레드를 만드는 방법은 두 가지다.

### Thread 클래스 상속

```java
class MyThread extends Thread {
    @Override
    public void run() {
        for (int i = 0; i < 5; i++) {
            System.out.println(getName() + " - " + i);
        }
    }
}

MyThread t = new MyThread();
t.start(); // run()이 아니라 start()를 호출해야 새 스레드에서 실행된다
```

Thread를 상속하면 다른 클래스를 상속할 수 없다. 실무에서는 거의 사용하지 않는다.

### Runnable 인터페이스 구현

```java
class MyTask implements Runnable {
    @Override
    public void run() {
        System.out.println(Thread.currentThread().getName() + " 실행");
    }
}

Thread t = new Thread(new MyTask());
t.start();
```

람다로 줄이면 이렇게 된다.

```java
Thread t = new Thread(() -> System.out.println("실행"));
t.start();
```

대부분의 경우 Runnable 구현이나 람다를 사용한다. 직접 Thread를 만들기보다는 ExecutorService를 쓰는 게 일반적이다.


## 스레드 상태 (Thread State)

Java 스레드는 `Thread.State` enum으로 정의된 6가지 상태를 가진다. `t.getState()`로 확인할 수 있다.

```
NEW ──start()──> RUNNABLE ──run() 종료──> TERMINATED
                    │  ↑
                    │  │
     synchronized   │  │  lock 획득
     진입 대기      ↓  │
                 BLOCKED

                 RUNNABLE
                    │  ↑
                    │  │
     wait()         │  │  notify()/notifyAll()
     join()         ↓  │
                 WAITING

                 RUNNABLE
                    │  ↑
                    │  │
     sleep(ms)      │  │  시간 만료 / notify()
     wait(ms)       ↓  │
              TIMED_WAITING
```

### 각 상태 설명

| 상태 | 진입 조건 | 빠져나오는 조건 |
|------|----------|---------------|
| **NEW** | `new Thread()` 호출 직후 | `start()` 호출 |
| **RUNNABLE** | `start()` 호출 후. OS 스레드 스케줄러에 의해 실행 대기 또는 실행 중 | run() 종료, 또는 다른 상태로 전이 |
| **BLOCKED** | `synchronized` 블록/메서드 진입 시 다른 스레드가 lock을 갖고 있을 때 | lock 획득 |
| **WAITING** | `wait()`, `join()`, `LockSupport.park()` 호출 | `notify()`, `notifyAll()`, join 대상 종료, `unpark()` |
| **TIMED_WAITING** | `sleep(ms)`, `wait(ms)`, `join(ms)` 호출 | 시간 만료 또는 `notify()` |
| **TERMINATED** | `run()` 정상 종료 또는 예외로 종료 | 되돌릴 수 없다 |

주의할 점: RUNNABLE은 실제로 CPU에서 실행 중인 상태와 실행 대기 상태를 구분하지 않는다. OS 레벨에서는 다르지만 Java에서는 둘 다 RUNNABLE이다.

```java
Thread t = new Thread(() -> {
    try {
        Thread.sleep(1000);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
});

System.out.println(t.getState()); // NEW
t.start();
System.out.println(t.getState()); // RUNNABLE (또는 TIMED_WAITING — 타이밍에 따라 다름)
```

한 번 TERMINATED된 스레드는 다시 `start()`를 호출하면 `IllegalThreadStateException`이 발생한다.


## synchronized와 동기화

여러 스레드가 같은 데이터를 읽고 쓰면 경쟁 상태(Race Condition)가 발생한다.

```java
class Counter {
    private int count = 0;

    public synchronized void increment() {
        count++; // read-modify-write가 원자적으로 실행된다
    }

    public synchronized int getCount() {
        return count;
    }
}
```

`synchronized` 메서드는 `this` 객체의 모니터 lock을 사용한다. 같은 인스턴스에 대해 한 번에 하나의 스레드만 진입한다.

### synchronized 블록

메서드 전체가 아니라 필요한 부분만 잠글 수 있다.

```java
class UserService {
    private final Object lock = new Object();
    private Map<String, User> cache = new HashMap<>();

    public User getUser(String id) {
        synchronized (lock) {
            return cache.get(id);
        }
        // lock 범위 밖에서는 다른 스레드가 동시에 접근 가능
    }
}
```

lock 객체를 분리하면 서로 다른 자원에 대한 동기화를 독립적으로 할 수 있다. `this`를 lock으로 쓰면 외부에서 같은 객체로 `synchronized(obj)`를 걸 수 있어서, 의도하지 않은 락 경합이 생길 수 있다.


## volatile 키워드와 메모리 가시성

Java 메모리 모델에서 각 스레드는 CPU 캐시에 변수의 복사본을 가질 수 있다. 한 스레드가 값을 변경해도 다른 스레드가 그 변경을 못 볼 수 있다.

```java
class StopFlag {
    private boolean running = true; // volatile 없음

    public void stop() {
        running = false;
    }

    public void run() {
        while (running) {
            // JIT 컴파일러가 running을 레지스터에 캐싱하면
            // stop()을 호출해도 이 루프가 안 끝날 수 있다
        }
    }
}
```

`volatile`을 붙이면 해당 변수의 읽기/쓰기가 항상 메인 메모리에서 수행된다.

```java
class StopFlag {
    private volatile boolean running = true;

    public void stop() {
        running = false; // 메인 메모리에 즉시 반영
    }

    public void run() {
        while (running) { // 매번 메인 메모리에서 읽음
            // 정상적으로 종료된다
        }
    }
}
```

### volatile이 해결하는 것과 못 하는 것

- **해결**: 메모리 가시성. 한 스레드의 쓰기를 다른 스레드가 확실히 볼 수 있게 한다.
- **못 해결**: 원자성. `count++` 같은 복합 연산은 volatile만으로 안전하지 않다.

```java
private volatile int count = 0;

// 이건 안전하지 않다. read → increment → write 사이에 다른 스레드가 끼어들 수 있다.
public void increment() {
    count++;
}

// 원자적 증가가 필요하면 AtomicInteger를 쓴다
private AtomicInteger count = new AtomicInteger(0);

public void increment() {
    count.incrementAndGet();
}
```

volatile은 플래그 변수(boolean)처럼 단순 읽기/쓰기만 하는 경우에 적합하다. 복합 연산이 필요하면 `synchronized`나 `Atomic*` 클래스를 써야 한다.


## wait / notify / notifyAll

`Object` 클래스에 정의된 메서드로, `synchronized` 블록 안에서만 사용할 수 있다. 스레드 간 협업에 사용한다.

### 기본 패턴: 생산자-소비자

```java
class MessageQueue {
    private final List<String> queue = new ArrayList<>();
    private final int capacity;

    public MessageQueue(int capacity) {
        this.capacity = capacity;
    }

    public synchronized void put(String message) throws InterruptedException {
        while (queue.size() == capacity) {
            wait(); // 큐가 가득 차면 대기. lock을 놓고 WAITING 상태로 들어간다.
        }
        queue.add(message);
        notifyAll(); // 대기 중인 소비자를 깨운다
    }

    public synchronized String take() throws InterruptedException {
        while (queue.isEmpty()) {
            wait(); // 큐가 비어있으면 대기
        }
        String message = queue.remove(0);
        notifyAll(); // 대기 중인 생산자를 깨운다
        return message;
    }
}
```

### wait()를 반드시 while로 감싸야 하는 이유

```java
// 잘못된 코드
synchronized (lock) {
    if (queue.isEmpty()) { // if를 쓰면 안 된다
        lock.wait();
    }
    // spurious wakeup이 발생하면 큐가 비어있는데도 여기 도달한다
    queue.remove(0); // NoSuchElementException
}

// 올바른 코드
synchronized (lock) {
    while (queue.isEmpty()) { // while로 조건을 다시 확인한다
        lock.wait();
    }
    queue.remove(0);
}
```

JVM 명세상 `wait()`는 `notify()`/`notifyAll()` 없이도 깨어날 수 있다(spurious wakeup). while로 조건을 다시 확인하지 않으면 버그가 발생한다.

### notify() vs notifyAll()

- `notify()`: 대기 중인 스레드 중 하나만 깨운다. 어떤 스레드가 깨어날지 보장되지 않는다.
- `notifyAll()`: 대기 중인 모든 스레드를 깨운다. 깨어난 스레드들이 lock을 다시 경쟁한다.

실무에서는 거의 항상 `notifyAll()`을 쓴다. `notify()`는 대기 중인 스레드가 모두 같은 조건을 기다리는 경우에만 안전하다. 조건이 다르면 엉뚱한 스레드가 깨어나고, 정작 처리해야 할 스레드는 계속 잠들어 있을 수 있다.

> 실무에서는 wait/notify 대신 `java.util.concurrent`의 `BlockingQueue`, `Condition`, `CountDownLatch` 등을 쓰는 게 일반적이다. wait/notify는 동작 원리를 이해하기 위해 알아두면 된다.


## Thread.interrupt() 처리

`interrupt()`는 스레드를 강제 종료하는 게 아니다. 대상 스레드에 "중단 요청"을 보내는 것이다. 대상 스레드가 이 요청을 확인하고 적절히 처리해야 한다.

### 동작 방식

1. 대상 스레드가 `sleep()`, `wait()`, `join()` 중이면 → `InterruptedException` 발생하고 인터럽트 플래그가 초기화(false)된다.
2. 대상 스레드가 실행 중이면 → 인터럽트 플래그만 true로 설정된다. 스레드가 `Thread.interrupted()`나 `isInterrupted()`로 확인해야 한다.

```java
class Worker implements Runnable {
    @Override
    public void run() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                // 작업 수행
                doWork();
                Thread.sleep(100);
            } catch (InterruptedException e) {
                // sleep 중 interrupt가 오면 여기로 온다
                // 이 시점에서 인터럽트 플래그는 이미 false로 초기화됨
                // 루프를 빠져나가려면 다시 설정하거나 break 한다
                Thread.currentThread().interrupt(); // 플래그 복원
                break;
            }
        }
        System.out.println("정상 종료");
    }
}
```

### 흔한 실수: InterruptedException을 삼켜버리기

```java
// 잘못된 코드 — interrupt 신호가 사라진다
try {
    Thread.sleep(1000);
} catch (InterruptedException e) {
    // 아무것도 안 하거나 로그만 찍으면
    // 호출자가 인터럽트 상태를 확인할 수 없다
}

// 올바른 처리 — 둘 중 하나를 해야 한다
// 방법 1: 인터럽트 플래그를 복원한다
try {
    Thread.sleep(1000);
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
}

// 방법 2: InterruptedException을 다시 던진다
public void doWork() throws InterruptedException {
    Thread.sleep(1000);
}
```

### Thread.interrupted() vs isInterrupted()

```java
// static 메서드 — 현재 스레드의 인터럽트 상태를 확인하고 플래그를 초기화한다
boolean wasInterrupted = Thread.interrupted(); // 호출 후 플래그 = false

// 인스턴스 메서드 — 대상 스레드의 인터럽트 상태만 확인한다. 플래그를 바꾸지 않는다
boolean isInterrupted = t.isInterrupted();
```


## 데드락 (Deadlock)

두 개 이상의 스레드가 서로 상대방이 가진 lock을 기다리면서 무한히 멈춘 상태다.

### 발생 조건 (4가지가 동시에 성립해야 한다)

1. **상호 배제(Mutual Exclusion)**: 자원을 한 번에 하나의 스레드만 사용할 수 있다.
2. **점유 대기(Hold and Wait)**: lock을 하나 잡은 상태에서 다른 lock을 기다린다.
3. **비선점(No Preemption)**: 다른 스레드가 가진 lock을 강제로 빼앗을 수 없다.
4. **순환 대기(Circular Wait)**: 스레드 A → B → C → A 순서로 서로의 lock을 기다린다.

### 데드락 예제

```java
class DeadlockExample {
    private final Object lockA = new Object();
    private final Object lockB = new Object();

    public void method1() {
        synchronized (lockA) {
            System.out.println(Thread.currentThread().getName() + ": lockA 획득");
            try { Thread.sleep(100); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }

            synchronized (lockB) { // lockB를 기다림
                System.out.println("method1 완료");
            }
        }
    }

    public void method2() {
        synchronized (lockB) { // lockA와 lockB의 순서가 반대다
            System.out.println(Thread.currentThread().getName() + ": lockB 획득");
            try { Thread.sleep(100); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }

            synchronized (lockA) { // lockA를 기다림 — 데드락 발생
                System.out.println("method2 완료");
            }
        }
    }
}
```

Thread-0이 lockA를 잡고 lockB를 기다리고, Thread-1이 lockB를 잡고 lockA를 기다리면서 둘 다 영원히 멈춘다.

### 데드락 예방

가장 간단한 방법은 **lock 획득 순서를 통일**하는 것이다. 순환 대기 조건을 깨면 데드락이 발생하지 않는다.

```java
// 수정된 코드 — lockA → lockB 순서를 모든 메서드에서 통일
public void method1() {
    synchronized (lockA) {
        synchronized (lockB) {
            System.out.println("method1 완료");
        }
    }
}

public void method2() {
    synchronized (lockA) { // lockB가 아니라 lockA를 먼저 잡는다
        synchronized (lockB) {
            System.out.println("method2 완료");
        }
    }
}
```

lock 대상이 동적으로 결정되는 경우(예: 계좌 이체에서 두 계좌 객체), `System.identityHashCode()`로 순서를 결정하는 방법이 있다.

```java
public void transfer(Account from, Account to, int amount) {
    Account first = from;
    Account second = to;
    if (System.identityHashCode(from) > System.identityHashCode(to)) {
        first = to;
        second = from;
    }
    synchronized (first) {
        synchronized (second) {
            from.withdraw(amount);
            to.deposit(amount);
        }
    }
}
```

### 데드락 진단

프로덕션에서 애플리케이션이 멈추면 데드락을 의심해야 한다.

**1. jstack으로 스레드 덤프 확인**

```bash
# Java 프로세스 ID 확인
jps

# 스레드 덤프 생성
jstack <pid>
```

데드락이 있으면 jstack 출력 하단에 이런 메시지가 나온다.

```
Found one Java-level deadlock:
=============================
"Thread-1":
  waiting to lock monitor 0x00007f8b3c003f08 (object 0x000000076ab2c6a0, a java.lang.Object),
  which is held by "Thread-0"
"Thread-0":
  waiting to lock monitor 0x00007f8b3c006008 (object 0x000000076ab2c6b0, a java.lang.Object),
  which is held by "Thread-1"
```

**2. 코드에서 프로그래밍 방식으로 감지**

```java
ThreadMXBean mxBean = ManagementFactory.getThreadMXBean();
long[] deadlockedThreads = mxBean.findDeadlockedThreads();

if (deadlockedThreads != null) {
    ThreadInfo[] threadInfos = mxBean.getThreadInfo(deadlockedThreads, true, true);
    for (ThreadInfo info : threadInfos) {
        System.out.println(info);
    }
}
```

이 코드를 주기적으로 실행하는 모니터링 스레드를 만들어두면 데드락 발생 시 빠르게 인지할 수 있다.

**3. tryLock으로 타임아웃 적용**

`synchronized` 대신 `ReentrantLock`의 `tryLock()`을 사용하면 lock 획득에 타임아웃을 줄 수 있다. 타임아웃이 발생하면 데드락 상태에서 빠져나올 수 있다.

```java
ReentrantLock lockA = new ReentrantLock();
ReentrantLock lockB = new ReentrantLock();

public void safeMethod() {
    boolean gotA = false;
    boolean gotB = false;
    try {
        gotA = lockA.tryLock(1, TimeUnit.SECONDS);
        gotB = lockB.tryLock(1, TimeUnit.SECONDS);
        if (gotA && gotB) {
            // 작업 수행
        } else {
            // lock 획득 실패 처리
            System.out.println("lock 획득 타임아웃 — 재시도 또는 포기");
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    } finally {
        if (gotB) lockB.unlock();
        if (gotA) lockA.unlock();
    }
}
```


## 주요 메서드 정리

| 메서드 | 설명 |
|--------|------|
| `start()` | 새 스레드를 생성하고 `run()`을 실행한다 |
| `run()` | 스레드가 실행할 코드. 직접 호출하면 새 스레드가 아닌 현재 스레드에서 실행된다 |
| `sleep(ms)` | 현재 스레드를 지정 시간만큼 일시 정지한다. lock을 놓지 않는다 |
| `join()` | 대상 스레드가 종료될 때까지 현재 스레드를 대기시킨다 |
| `interrupt()` | 대상 스레드에 중단 요청을 보낸다 |
| `isInterrupted()` | 인터럽트 플래그를 확인한다. 플래그를 바꾸지 않는다 |
| `Thread.interrupted()` | 현재 스레드의 인터럽트 플래그를 확인하고 초기화한다 |
| `wait()` | 현재 스레드를 WAITING으로 전환한다. lock을 놓는다. synchronized 블록 안에서만 호출 가능 |
| `notify()` | 같은 객체에서 wait 중인 스레드 하나를 깨운다 |
| `notifyAll()` | 같은 객체에서 wait 중인 모든 스레드를 깨운다 |
| `getState()` | 스레드의 현재 상태(NEW, RUNNABLE 등)를 반환한다 |
