---
title: "Deadlock"
tags: [OS, Process, Thread, Deadlock, 동기화]
updated: 2026-03-24
---

# Deadlock

프로세스나 스레드가 서로 상대방이 가진 자원을 기다리면서, 어느 쪽도 진행하지 못하는 상태다. 멀티스레드 애플리케이션에서 락을 2개 이상 사용하기 시작하면 데드락을 만날 확률이 급격히 올라간다.

---

## 데드락 발생 조건 4가지

데드락은 아래 4가지 조건이 **동시에** 성립할 때 발생한다. 하나라도 깨면 데드락은 일어나지 않는다.

### 1. 상호 배제 (Mutual Exclusion)

자원을 한 번에 하나의 스레드만 사용할 수 있다. `synchronized` 블록이나 `mutex`가 대표적이다. 공유 자원 자체의 특성이라 이 조건을 깨기는 어렵다.

### 2. 점유 대기 (Hold and Wait)

자원을 하나 이상 점유한 상태에서, 다른 자원을 추가로 요청하며 대기한다. 락 A를 잡은 채로 락 B를 기다리는 상황이다.

### 3. 비선점 (No Preemption)

다른 스레드가 점유한 자원을 강제로 뺏을 수 없다. `synchronized`는 타임아웃이 없어서 한번 대기에 들어가면 상대방이 놓을 때까지 영원히 기다린다.

### 4. 순환 대기 (Circular Wait)

스레드 A → 락 B 대기, 스레드 B → 락 A 대기처럼 대기 관계가 원형으로 형성된다. 실제 데드락의 직접적인 원인이 되는 조건이다.

---

## 코드로 데드락 재현하기

### Java 예제

가장 흔한 패턴이다. 두 스레드가 서로 반대 순서로 락을 잡는다.

```java
public class DeadlockDemo {
    private static final Object lockA = new Object();
    private static final Object lockB = new Object();

    public static void main(String[] args) {
        Thread t1 = new Thread(() -> {
            synchronized (lockA) {
                System.out.println("Thread-1: lockA 획득");
                try { Thread.sleep(100); } catch (InterruptedException e) {}

                synchronized (lockB) {
                    System.out.println("Thread-1: lockB 획득");
                }
            }
        });

        Thread t2 = new Thread(() -> {
            synchronized (lockB) {
                System.out.println("Thread-2: lockB 획득");
                try { Thread.sleep(100); } catch (InterruptedException e) {}

                synchronized (lockA) {
                    System.out.println("Thread-2: lockA 획득");
                }
            }
        });

        t1.start();
        t2.start();
    }
}
```

`Thread.sleep(100)`은 타이밍을 맞추기 위한 것이다. 실제 운영 환경에서는 sleep 없이도 부하가 걸리면 자연스럽게 발생한다. 이 코드를 실행하면 두 스레드 모두 멈추고 프로그램이 종료되지 않는다.

### C (pthread) 예제

```c
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

pthread_mutex_t mutex_a = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t mutex_b = PTHREAD_MUTEX_INITIALIZER;

void *thread1_func(void *arg) {
    pthread_mutex_lock(&mutex_a);
    printf("Thread-1: mutex_a 획득\n");
    usleep(100000);

    pthread_mutex_lock(&mutex_b);
    printf("Thread-1: mutex_b 획득\n");

    pthread_mutex_unlock(&mutex_b);
    pthread_mutex_unlock(&mutex_a);
    return NULL;
}

void *thread2_func(void *arg) {
    pthread_mutex_lock(&mutex_b);
    printf("Thread-2: mutex_b 획득\n");
    usleep(100000);

    pthread_mutex_lock(&mutex_a);
    printf("Thread-2: mutex_a 획득\n");

    pthread_mutex_unlock(&mutex_a);
    pthread_mutex_unlock(&mutex_b);
    return NULL;
}

int main() {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, thread1_func, NULL);
    pthread_create(&t2, NULL, thread2_func, NULL);

    pthread_join(t1, NULL);
    pthread_join(t2, NULL);

    pthread_mutex_destroy(&mutex_a);
    pthread_mutex_destroy(&mutex_b);
    return 0;
}
```

C에서는 `pthread_mutex_trylock`이나 `pthread_mutex_timedlock`으로 타임아웃을 줄 수 있다. Java의 `synchronized`와 달리 대기 시간을 제한할 수 있어서 데드락을 회피하는 데 쓸 수 있다.

---

## 데드락 탐지 방법

### jstack으로 Java 스레드 덤프 뜨기

운영 중인 JVM에서 데드락이 의심되면 `jstack`을 쓴다.

```bash
# PID 확인
jps -l

# 스레드 덤프
jstack <PID> > thread_dump.txt
```

덤프 파일 마지막 부분에 데드락이 있으면 이런 메시지가 나온다:

```
Found one Java-level deadlock:
=============================
"Thread-2":
  waiting to lock monitor 0x00007f8b2c003a00 (object 0x000000076ab2c6a0, a java.lang.Object),
  which is held by "Thread-1"
"Thread-1":
  waiting to lock monitor 0x00007f8b2c006800 (object 0x000000076ab2c6b0, a java.lang.Object),
  which is held by "Thread-2"
```

JVM이 자동으로 데드락을 감지해서 어떤 스레드가 어떤 모니터를 기다리는지 알려준다. 스레드 이름에 의미 있는 이름을 넣어두면 디버깅이 훨씬 수월하다.

### Thread dump 읽는 법

```
"Thread-1" #12 prio=5 os_prio=0 tid=0x00007f8b... nid=0x1a03 waiting for monitor entry [0x00007f8b...]
   java.lang.Thread.State: BLOCKED (on object monitor)
        at DeadlockDemo.lambda$main$0(DeadlockDemo.java:14)
        - waiting to lock <0x000000076ab2c6b0> (a java.lang.Object)
        - locked <0x000000076ab2c6a0> (a java.lang.Object)
```

확인해야 할 것:

- `BLOCKED` 상태인 스레드를 찾는다
- `waiting to lock`과 `locked`의 객체 주소를 비교한다
- 스레드 A가 대기하는 객체를 스레드 B가 들고 있고, 반대도 마찬가지면 데드락이다

### VisualVM, IntelliJ 활용

`jstack`을 직접 쓰기 번거로우면 VisualVM의 Thread 탭에서 "Detect Deadlock" 버튼을 누르면 된다. IntelliJ에서는 디버그 모드로 실행 후 카메라 아이콘(Dump Threads)을 클릭하면 같은 결과를 볼 수 있다.

---

## 락 순서 규칙으로 예방하기

데드락을 예방하는 가장 확실한 방법은 **모든 스레드가 같은 순서로 락을 잡게 하는 것**이다.

### 전역 락 순서 정하기

```java
public class TransferService {
    // 계좌 이체: 항상 ID가 작은 계좌의 락을 먼저 잡는다
    public void transfer(Account from, Account to, long amount) {
        Account first = from.getId() < to.getId() ? from : to;
        Account second = from.getId() < to.getId() ? to : from;

        synchronized (first) {
            synchronized (second) {
                if (from.getBalance() >= amount) {
                    from.withdraw(amount);
                    to.deposit(amount);
                }
            }
        }
    }
}
```

어떤 스레드가 `transfer(A, B)`를 호출하든 `transfer(B, A)`를 호출하든, ID 비교를 통해 항상 같은 순서로 락을 잡는다. 순환 대기 조건이 성립하지 않으므로 데드락이 발생하지 않는다.

### ID가 같은 경우 대비

```java
public void transfer(Account from, Account to, long amount) {
    if (from.getId() == to.getId()) {
        throw new IllegalArgumentException("같은 계좌로 이체할 수 없다");
    }

    Account first = from.getId() < to.getId() ? from : to;
    Account second = from.getId() < to.getId() ? to : from;

    synchronized (first) {
        synchronized (second) {
            from.withdraw(amount);
            to.deposit(amount);
        }
    }
}
```

### ReentrantLock으로 타임아웃 걸기

`synchronized`는 타임아웃이 없다. `ReentrantLock`의 `tryLock`을 쓰면 일정 시간 안에 락을 못 잡으면 포기하고 재시도할 수 있다.

```java
public class SafeTransfer {
    private static final long TIMEOUT = 1000;

    public boolean transfer(Account from, Account to, long amount)
            throws InterruptedException {

        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(TIMEOUT);

        while (true) {
            if (from.getLock().tryLock()) {
                try {
                    if (to.getLock().tryLock()) {
                        try {
                            from.withdraw(amount);
                            to.deposit(amount);
                            return true;
                        } finally {
                            to.getLock().unlock();
                        }
                    }
                } finally {
                    from.getLock().unlock();
                }
            }

            if (System.nanoTime() >= deadline) {
                return false; // 타임아웃
            }
            Thread.sleep(10); // 잠깐 대기 후 재시도
        }
    }
}
```

이 방식은 데드락 자체를 예방하는 건 아니고, 데드락 상황에서 빠져나올 수 있게 해준다. 재시도 로직이 복잡해질 수 있으니, 가능하면 락 순서를 정하는 방식을 먼저 적용한다.

---

## 실무에서 만나는 데드락

### DB 데드락

애플리케이션 코드에 `synchronized`가 없어도 DB 수준에서 데드락이 발생한다.

```sql
-- 트랜잭션 1
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- row 1 잠금
UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- row 2 대기

-- 트랜잭션 2 (동시에)
BEGIN;
UPDATE accounts SET balance = balance - 50 WHERE id = 2;   -- row 2 잠금
UPDATE accounts SET balance = balance + 50 WHERE id = 1;   -- row 1 대기
```

MySQL InnoDB는 데드락을 자동으로 감지하고, 비용이 적은 트랜잭션을 롤백시킨다. 에러 코드 `1213 (ER_LOCK_DEADLOCK)`이 발생한다.

```
ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction
```

대응 방법:

- 트랜잭션에서 UPDATE 순서를 통일한다 (항상 ID 오름차순으로 접근)
- `SHOW ENGINE INNODB STATUS`로 마지막 데드락 정보를 확인한다
- 트랜잭션을 짧게 유지한다. 트랜잭션 안에서 외부 API를 호출하거나 오래 걸리는 작업을 하면 락 보유 시간이 길어져서 데드락 확률이 올라간다

```sql
SHOW ENGINE INNODB STATUS\G
```

`LATEST DETECTED DEADLOCK` 섹션에서 어떤 쿼리가 어떤 인덱스의 어떤 row를 잡고 있었는지 볼 수 있다.

### 애플리케이션 데드락

코드 레벨에서 흔히 만나는 패턴들이다.

**1. 중첩 synchronized에서 순서 불일치**

서비스 레이어에서 여러 컴포넌트를 조합할 때 발생한다. 각 컴포넌트가 내부적으로 락을 잡고 있고, 호출 순서에 따라 데드락이 생긴다.

```java
// OrderService.java
public void processOrder(Order order) {
    synchronized (inventoryLock) {
        synchronized (paymentLock) {
            // 재고 확인 후 결제
        }
    }
}

// RefundService.java
public void processRefund(Order order) {
    synchronized (paymentLock) {
        synchronized (inventoryLock) {
            // 환불 처리 후 재고 복구
        }
    }
}
```

`processOrder`와 `processRefund`가 동시에 호출되면 데드락이 발생한다. 해결은 두 메서드 모두 `inventoryLock → paymentLock` 순서로 통일하는 것이다.

**2. 스레드 풀 고갈에 의한 데드락**

락은 없지만, 스레드 풀 자원이 부족해서 생기는 데드락이다.

```java
ExecutorService pool = Executors.newFixedThreadPool(2);

pool.submit(() -> {
    // 작업 A: 내부에서 다시 pool에 작업을 넣고 결과를 기다린다
    Future<?> result = pool.submit(() -> {
        return doSomething();
    });
    result.get(); // 여기서 블록
});

pool.submit(() -> {
    Future<?> result = pool.submit(() -> {
        return doSomethingElse();
    });
    result.get(); // 여기서 블록
});
```

풀 크기가 2인데, 2개 스레드가 모두 내부 작업의 완료를 기다린다. 내부 작업은 풀에 빈 스레드가 없어서 실행되지 못한다. 락 기반 데드락이 아니라서 `jstack`의 데드락 감지에 안 잡힌다. 스레드 상태가 `WAITING`인데 원인이 불분명하면 이 패턴을 의심해야 한다.

**3. Connection Pool 데드락**

하나의 요청에서 DB 커넥션을 2개 이상 사용하는 경우, 커넥션 풀이 고갈되면서 데드락과 비슷한 상황이 된다.

```java
@Transactional
public void outerMethod() {
    // 커넥션 1개 사용 중
    innerService.doSomething(); // @Transactional(REQUIRES_NEW) → 커넥션 1개 더 필요
}
```

커넥션 풀 크기가 10이고, 동시 요청이 10개 들어오면 모든 커넥션이 `outerMethod`에 할당된다. `innerService.doSomething()`은 새 커넥션이 필요한데 풀이 비어있어서 대기한다. 모든 스레드가 같은 상태에 빠진다.

`REQUIRES_NEW`를 남발하면 이런 상황이 생긴다. 커넥션 풀 크기를 넉넉하게 잡거나, 트랜잭션 전파 설정을 재검토해야 한다.

---

## 정리

데드락은 "락 2개 이상 + 순서 불일치"에서 시작한다. 예방이 탐지보다 낫다.

- 락 순서를 전역으로 정하고, 모든 코드에서 지킨다
- `jstack`과 `SHOW ENGINE INNODB STATUS`는 운영 환경에서 데드락 원인을 찾는 기본 도구다
- 스레드 풀 고갈, 커넥션 풀 고갈 같은 리소스 기반 데드락은 락 기반 탐지에 안 잡히니 따로 주의한다
- DB 트랜잭션은 짧게 유지하고, UPDATE 순서를 통일한다
