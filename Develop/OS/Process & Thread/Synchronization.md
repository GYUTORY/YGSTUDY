---
title: "동기화 프리미티브 심화"
tags: [OS, Process, Thread, Synchronization, Mutex, Semaphore, Spinlock, RWLock, futex]
updated: 2026-03-25
---

# 동기화 프리미티브 심화

멀티스레드 프로그래밍에서 공유 자원 접근을 제어하는 동기화 프리미티브들의 내부 구현 원리를 다룬다. Mutex, Semaphore, Condition Variable, Monitor, Spinlock, RWLock 각각이 커널 수준에서 어떻게 동작하는지, 실제 코드에서 어떻게 사용하는지, 그리고 락 경합이 발생했을 때 어떻게 측정하고 대응하는지 정리한다.

---

## Mutex (Mutual Exclusion)

한 번에 하나의 스레드만 임계 영역에 진입하게 한다. 소유권 개념이 있어서 락을 잡은 스레드만 해제할 수 있다.

### 구현 원리

내부적으로 상태 변수 하나와 대기 큐로 구성된다.

```
state: 0(unlocked) / 1(locked)
owner: 락을 잡은 스레드 ID
wait_queue: 대기 중인 스레드 목록
```

`lock()` 호출 시 `state`를 atomic하게 0→1로 바꾸려고 시도한다. 이미 1이면 호출 스레드를 `wait_queue`에 넣고 sleep 상태로 전환한다. `unlock()` 호출 시 `wait_queue`에서 스레드 하나를 꺼내 깨운다.

### C (pthread) 예제

```c
#include <stdio.h>
#include <pthread.h>

pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;
int counter = 0;

void *increment(void *arg) {
    for (int i = 0; i < 1000000; i++) {
        pthread_mutex_lock(&mtx);
        counter++;
        pthread_mutex_unlock(&mtx);
    }
    return NULL;
}

int main() {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, increment, NULL);
    pthread_create(&t2, NULL, increment, NULL);

    pthread_join(t1, NULL);
    pthread_join(t2, NULL);

    printf("counter = %d\n", counter); // 항상 2000000
    pthread_mutex_destroy(&mtx);
    return 0;
}
```

`PTHREAD_MUTEX_INITIALIZER`는 정적 초기화 매크로다. 동적 초기화가 필요하면 `pthread_mutex_init`을 쓴다. 이 경우 반드시 `pthread_mutex_destroy`로 해제해야 한다. 정적 초기화는 destroy를 안 해도 문제없지만, 습관적으로 해제하는 게 좋다.

### Java 예제

Java에서 `synchronized`가 사실상 Mutex다. 명시적으로 사용하려면 `ReentrantLock`을 쓴다.

```java
import java.util.concurrent.locks.ReentrantLock;

public class Counter {
    private final ReentrantLock lock = new ReentrantLock();
    private int count = 0;

    public void increment() {
        lock.lock();
        try {
            count++;
        } finally {
            lock.unlock(); // 예외 발생해도 반드시 해제
        }
    }
}
```

`ReentrantLock`은 이름 그대로 같은 스레드가 여러 번 `lock()`을 호출할 수 있다. 호출한 횟수만큼 `unlock()`을 해야 실제로 풀린다. `synchronized`도 재진입 가능하다.

### 주의사항

- `unlock()`을 빠뜨리면 다른 스레드가 영원히 대기한다. C에서는 `finally`가 없으니 에러 처리 경로에서 unlock을 놓치기 쉽다
- pthread의 `PTHREAD_MUTEX_ERRORCHECK` 타입을 쓰면, 같은 스레드가 두 번 lock하거나 소유하지 않은 mutex를 unlock하면 에러를 반환한다. 디버깅할 때 유용하다

```c
pthread_mutexattr_t attr;
pthread_mutexattr_init(&attr);
pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ERRORCHECK);

pthread_mutex_t mtx;
pthread_mutex_init(&mtx, &attr);
pthread_mutexattr_destroy(&attr);
```

---

## Semaphore

Mutex가 "1개 스레드만 진입"이라면, Semaphore는 "N개 스레드까지 진입"을 허용한다. 내부에 카운터를 갖고 있고, `wait()`하면 카운터가 감소, `signal()`하면 증가한다. 카운터가 0이면 `wait()` 호출 스레드는 block된다.

### 이진 세마포어 vs 카운팅 세마포어

- **이진 세마포어**: 카운터 값이 0 또는 1. Mutex와 비슷하지만 소유권 개념이 없다. 잡은 스레드가 아닌 다른 스레드가 signal할 수 있다
- **카운팅 세마포어**: 카운터 값이 N. 동시 접근 가능 수를 제한할 때 사용한다. DB 커넥션 풀 크기 제한이 대표적인 사용처다

### C (POSIX) 예제 — 생산자/소비자

```c
#include <stdio.h>
#include <pthread.h>
#include <semaphore.h>

#define BUFFER_SIZE 5

int buffer[BUFFER_SIZE];
int in = 0, out = 0;

sem_t empty; // 빈 슬롯 수
sem_t full;  // 채워진 슬롯 수
pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;

void *producer(void *arg) {
    for (int i = 0; i < 20; i++) {
        sem_wait(&empty); // 빈 슬롯이 있을 때까지 대기
        pthread_mutex_lock(&mtx);

        buffer[in] = i;
        printf("Produced: %d\n", i);
        in = (in + 1) % BUFFER_SIZE;

        pthread_mutex_unlock(&mtx);
        sem_post(&full); // 채워진 슬롯 수 증가
    }
    return NULL;
}

void *consumer(void *arg) {
    for (int i = 0; i < 20; i++) {
        sem_wait(&full); // 채워진 슬롯이 있을 때까지 대기
        pthread_mutex_lock(&mtx);

        int item = buffer[out];
        printf("Consumed: %d\n", item);
        out = (out + 1) % BUFFER_SIZE;

        pthread_mutex_unlock(&mtx);
        sem_post(&empty); // 빈 슬롯 수 증가
    }
    return NULL;
}

int main() {
    sem_init(&empty, 0, BUFFER_SIZE); // 초기값: 빈 슬롯 5개
    sem_init(&full, 0, 0);            // 초기값: 채워진 슬롯 0개

    pthread_t prod, cons;
    pthread_create(&prod, NULL, producer, NULL);
    pthread_create(&cons, NULL, consumer, NULL);

    pthread_join(prod, NULL);
    pthread_join(cons, NULL);

    sem_destroy(&empty);
    sem_destroy(&full);
    pthread_mutex_destroy(&mtx);
    return 0;
}
```

세마포어 2개와 뮤텍스 1개를 같이 사용한다. `empty`와 `full` 세마포어가 버퍼의 빈 칸과 찬 칸 수를 추적하고, 뮤텍스가 버퍼 배열 자체의 동시 접근을 막는다. 세마포어만으로는 버퍼 접근의 원자성을 보장할 수 없어서 뮤텍스가 필요하다.

### Java 예제

```java
import java.util.concurrent.Semaphore;

public class ConnectionPool {
    private final Semaphore semaphore;

    public ConnectionPool(int maxConnections) {
        this.semaphore = new Semaphore(maxConnections);
    }

    public Connection acquire() throws InterruptedException {
        semaphore.acquire(); // 가용 커넥션이 없으면 대기
        return createConnection();
    }

    public void release(Connection conn) {
        closeConnection(conn);
        semaphore.release(); // 가용 커넥션 수 복구
    }
}
```

`Semaphore(maxConnections, true)`로 생성하면 fair 모드가 된다. 대기 중인 스레드 중 가장 오래 기다린 스레드가 먼저 획득한다. fair 모드는 처리량이 떨어지니 기아(starvation)가 문제될 때만 쓴다.

### macOS에서 POSIX 세마포어 주의

macOS는 `sem_init`이 동작하지 않는다(`errno = ENOSYS`). 이름 있는 세마포어(`sem_open`)를 사용해야 한다.

```c
sem_t *sem = sem_open("/my_semaphore", O_CREAT, 0644, 1);
// 사용 후
sem_close(sem);
sem_unlink("/my_semaphore");
```

Linux에서 개발하다가 macOS에서 빌드하면 세마포어 코드에서 바로 터진다.

---

## Condition Variable

"특정 조건이 만족될 때까지 기다리다가, 조건이 만족되면 깨어나는" 메커니즘이다. 반드시 뮤텍스와 함께 사용한다.

### 동작 원리

1. 스레드가 뮤텍스를 잡는다
2. 조건을 검사한다
3. 조건이 안 맞으면 `wait()`을 호출한다 — 이때 뮤텍스가 자동으로 해제되고 스레드는 sleep
4. 다른 스레드가 조건을 변경하고 `signal()`이나 `broadcast()`를 호출한다
5. 대기 중인 스레드가 깨어나면서 뮤텍스를 다시 자동으로 잡는다
6. 조건을 다시 검사한다 (spurious wakeup 때문에 반드시 루프 안에서 확인)

### C (pthread) 예제

```c
#include <stdio.h>
#include <pthread.h>
#include <stdbool.h>

pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
bool data_ready = false;

void *producer(void *arg) {
    pthread_mutex_lock(&mtx);
    // 데이터 준비 작업
    data_ready = true;
    pthread_cond_signal(&cond); // 대기 중인 스레드 하나를 깨운다
    pthread_mutex_unlock(&mtx);
    return NULL;
}

void *consumer(void *arg) {
    pthread_mutex_lock(&mtx);
    while (!data_ready) {         // 반드시 while로 감싼다
        pthread_cond_wait(&cond, &mtx); // mtx 해제 + sleep, 깨어나면 mtx 재획득
    }
    printf("Data received\n");
    pthread_mutex_unlock(&mtx);
    return NULL;
}
```

`if (!data_ready)`가 아니라 `while (!data_ready)`을 쓰는 이유: **spurious wakeup**이 발생할 수 있다. POSIX 표준에서 `pthread_cond_wait`은 signal 없이도 깨어날 수 있다고 명시하고 있다. 커널 구현의 효율성 때문인데, 실제로 Linux에서 futex 기반 구현을 쓸 때 드물게 발생한다. while 루프로 조건을 다시 확인해야 안전하다.

### Java 예제

```java
public class BlockingQueue<T> {
    private final Queue<T> queue = new LinkedList<>();
    private final int capacity;
    private final Object lock = new Object();

    public BlockingQueue(int capacity) {
        this.capacity = capacity;
    }

    public void put(T item) throws InterruptedException {
        synchronized (lock) {
            while (queue.size() == capacity) {
                lock.wait(); // 큐가 가득 차면 대기
            }
            queue.add(item);
            lock.notifyAll(); // 대기 중인 consumer를 깨운다
        }
    }

    public T take() throws InterruptedException {
        synchronized (lock) {
            while (queue.isEmpty()) {
                lock.wait(); // 큐가 비어있으면 대기
            }
            T item = queue.poll();
            lock.notifyAll(); // 대기 중인 producer를 깨운다
            return item;
        }
    }
}
```

`notify()`는 대기 중인 스레드 중 하나만 깨우고, `notifyAll()`은 전부 깨운다. 생산자와 소비자가 같은 condition에서 대기하는 구조에서 `notify()`를 쓰면 소비자가 소비자를 깨우는 문제가 생길 수 있다. `notifyAll()`이 안전하다.

### signal vs broadcast

- `signal` (`notify`): 대기 중인 스레드 하나만 깨운다. 깨울 스레드를 OS가 선택한다
- `broadcast` (`notifyAll`): 대기 중인 스레드 전부를 깨운다. 전부 깨어나서 조건을 확인하고, 하나만 뮤텍스를 잡고 나머지는 다시 대기한다

대기 중인 스레드들이 모두 같은 조건을 기다리면 `signal`로 충분하다. 조건이 다르면 `broadcast`를 써야 한다.

---

## Monitor

Mutex + Condition Variable을 하나로 묶은 고수준 동기화 구조다. Java의 모든 객체가 Monitor다.

### Java 객체의 내부 구조

JVM에서 모든 객체는 헤더에 Mark Word를 가지고 있다. 이 Mark Word에 락 상태가 저장된다.

```
|----------------------------------------------|
|  Mark Word (64bit on 64-bit JVM)             |
|----------------------------------------------|
| biased_lock:1 | lock:2 | ... | thread_id     |  Biased Lock
| ptr_to_lock_record      | 00                 |  Lightweight Lock
| ptr_to_heavyweight_mon  | 10                 |  Heavyweight Lock
|----------------------------------------------|
```

`synchronized` 블록에 진입하면 JVM이 순서대로 시도한다:

1. **Biased Locking**: 처음 락을 잡은 스레드 ID를 Mark Word에 기록한다. 같은 스레드가 다시 진입할 때 CAS 연산 없이 바로 통과한다. 단일 스레드가 반복 접근하는 패턴에서 빠르다. (JDK 15부터 기본 비활성화, JDK 18에서 제거)
2. **Lightweight Lock (Thin Lock)**: 경합이 적을 때 CAS로 스택의 Lock Record 포인터를 Mark Word에 기록한다. 커널 진입 없이 유저 스페이스에서 처리한다
3. **Heavyweight Lock (Fat Lock)**: 경합이 심해지면 OS의 mutex로 전환한다. 커널 진입이 필요해서 느리다

경합이 없는 상황에서 `synchronized`가 생각보다 빠른 이유가 이것이다. 경합이 생겨야 비로소 heavyweight로 전환된다.

### C에서 Monitor 패턴 구현

C에는 Monitor가 없으니 직접 만들어야 한다.

```c
typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
    int buffer[100];
    int count;
    int in;
    int out;
} Monitor;

void monitor_init(Monitor *m) {
    pthread_mutex_init(&m->mutex, NULL);
    pthread_cond_init(&m->not_empty, NULL);
    pthread_cond_init(&m->not_full, NULL);
    m->count = 0;
    m->in = 0;
    m->out = 0;
}

void monitor_put(Monitor *m, int item) {
    pthread_mutex_lock(&m->mutex);
    while (m->count == 100) {
        pthread_cond_wait(&m->not_full, &m->mutex);
    }
    m->buffer[m->in] = item;
    m->in = (m->in + 1) % 100;
    m->count++;
    pthread_cond_signal(&m->not_empty);
    pthread_mutex_unlock(&m->mutex);
}

int monitor_get(Monitor *m) {
    pthread_mutex_lock(&m->mutex);
    while (m->count == 0) {
        pthread_cond_wait(&m->not_empty, &m->mutex);
    }
    int item = m->buffer[m->out];
    m->out = (m->out + 1) % 100;
    m->count--;
    pthread_cond_signal(&m->not_full);
    pthread_mutex_unlock(&m->mutex);
    return item;
}
```

뮤텍스 하나에 컨디션 변수를 여러 개 붙여서 조건별로 분리했다. `not_empty`와 `not_full`을 분리하면 `broadcast` 대신 `signal`을 쓸 수 있어서 불필요한 wakeup이 줄어든다.

---

## Spinlock

락을 못 잡으면 sleep하지 않고, CPU를 돌리면서(spin) 락이 풀릴 때까지 반복 시도한다.

### 언제 쓰는가

- 임계 영역이 매우 짧을 때 (수십 나노초 수준)
- 컨텍스트 스위칭 비용이 임계 영역 실행 비용보다 클 때
- 커널 코드에서 인터럽트 핸들러 내부 등 sleep이 불가능한 컨텍스트

유저 스페이스에서 Spinlock을 쓸 일은 거의 없다. 임계 영역이 길면 CPU를 낭비만 한다. 커널 내부에서 주로 사용한다.

### CAS 기반 구현

```c
#include <stdatomic.h>

typedef struct {
    atomic_flag flag;
} spinlock_t;

void spinlock_init(spinlock_t *lock) {
    atomic_flag_clear(&lock->flag);
}

void spinlock_lock(spinlock_t *lock) {
    while (atomic_flag_test_and_set_explicit(&lock->flag, memory_order_acquire)) {
        // spin — CPU를 계속 사용한다
    }
}

void spinlock_unlock(spinlock_t *lock) {
    atomic_flag_clear_explicit(&lock->flag, memory_order_release);
}
```

`atomic_flag_test_and_set`은 하드웨어의 atomic instruction(x86의 `XCHG`, ARM의 `LDXR/STXR`)으로 구현된다. 한 번의 명령으로 읽기와 쓰기를 원자적으로 수행한다.

### Test-and-Test-and-Set (TTAS) 개선

단순 TAS 스핀락은 여러 코어가 동시에 spin하면 캐시 라인 바운싱이 심해진다. TTAS는 먼저 로컬 캐시에서 값을 읽고, 풀린 것 같을 때만 TAS를 시도한다.

```c
void spinlock_lock_ttas(spinlock_t *lock) {
    while (1) {
        // Test: 로컬 캐시에서 읽기 (캐시 라인 공유, 버스 트래픽 없음)
        while (atomic_flag_test_and_set_explicit(&lock->flag, memory_order_relaxed)) {
            __builtin_ia32_pause(); // x86 PAUSE 힌트
        }
        // Test-and-Set: 실제 획득 시도
        if (!atomic_flag_test_and_set_explicit(&lock->flag, memory_order_acquire)) {
            return; // 획득 성공
        }
    }
}
```

`__builtin_ia32_pause()`(x86의 `PAUSE` 명령)는 스핀 루프에서 파이프라인 낭비를 줄이고 전력 소비를 낮춘다. 하이퍼스레딩 환경에서 다른 논리 코어에게 자원을 양보하는 역할도 한다.

### pthread_spinlock

```c
pthread_spinlock_t slock;
pthread_spin_init(&slock, PTHREAD_PROCESS_PRIVATE);
pthread_spin_lock(&slock);
// 매우 짧은 임계 영역
pthread_spin_unlock(&slock);
pthread_spin_destroy(&slock);
```

macOS에서는 `pthread_spinlock_t`를 지원하지 않는다. `os_unfair_lock`을 대신 사용한다.

---

## Read-Write Lock (RWLock)

읽기 연산이 쓰기보다 훨씬 많을 때 유용하다. 읽기끼리는 동시 접근을 허용하고, 쓰기는 독점 접근한다.

### 동작 규칙

| 현재 상태 | 읽기 요청 | 쓰기 요청 |
|-----------|-----------|-----------|
| 아무도 안 잡음 | 허용 | 허용 |
| 읽기 락 N개 잡힘 | 허용 | 대기 |
| 쓰기 락 잡힘 | 대기 | 대기 |

### C (pthread) 예제

```c
#include <stdio.h>
#include <pthread.h>

pthread_rwlock_t rwlock = PTHREAD_RWLOCK_INITIALIZER;
int shared_data = 0;

void *reader(void *arg) {
    pthread_rwlock_rdlock(&rwlock);
    printf("Reader %ld: data = %d\n", (long)arg, shared_data);
    pthread_rwlock_unlock(&rwlock);
    return NULL;
}

void *writer(void *arg) {
    pthread_rwlock_wrlock(&rwlock);
    shared_data++;
    printf("Writer %ld: data = %d\n", (long)arg, shared_data);
    pthread_rwlock_unlock(&rwlock);
    return NULL;
}

int main() {
    pthread_t threads[10];
    // 8개 reader, 2개 writer
    for (long i = 0; i < 8; i++)
        pthread_create(&threads[i], NULL, reader, (void *)i);
    for (long i = 8; i < 10; i++)
        pthread_create(&threads[i], NULL, writer, (void *)i);

    for (int i = 0; i < 10; i++)
        pthread_join(threads[i], NULL);

    pthread_rwlock_destroy(&rwlock);
    return 0;
}
```

### Java 예제

```java
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

public class Cache {
    private final ReadWriteLock rwLock = new ReentrantReadWriteLock();
    private final Map<String, String> map = new HashMap<>();

    public String get(String key) {
        rwLock.readLock().lock();
        try {
            return map.get(key);
        } finally {
            rwLock.readLock().unlock();
        }
    }

    public void put(String key, String value) {
        rwLock.writeLock().lock();
        try {
            map.put(key, value);
        } finally {
            rwLock.writeLock().unlock();
        }
    }
}
```

### Writer Starvation 문제

Reader가 계속 들어오면 Writer가 영원히 대기할 수 있다. 이걸 writer starvation이라고 한다. pthread에서는 `PTHREAD_RWLOCK_PREFER_WRITER_NONRECURSIVE_NP` 속성으로 writer 우선 정책을 설정한다.

```c
pthread_rwlockattr_t attr;
pthread_rwlockattr_init(&attr);
pthread_rwlockattr_setkind_np(&attr, PTHREAD_RWLOCK_PREFER_WRITER_NONRECURSIVE_NP);

pthread_rwlock_t rwlock;
pthread_rwlock_init(&rwlock, &attr);
pthread_rwlockattr_destroy(&attr);
```

Java의 `ReentrantReadWriteLock(true)` (fair 모드)는 가장 오래 기다린 스레드에게 우선권을 준다. 하지만 처리량이 떨어진다.

### StampedLock (Java 8+)

`ReadWriteLock`의 성능 한계를 개선한 락이다. optimistic read를 지원한다.

```java
import java.util.concurrent.locks.StampedLock;

public class Point {
    private final StampedLock sl = new StampedLock();
    private double x, y;

    public void move(double deltaX, double deltaY) {
        long stamp = sl.writeLock();
        try {
            x += deltaX;
            y += deltaY;
        } finally {
            sl.unlockWrite(stamp);
        }
    }

    public double distanceFromOrigin() {
        long stamp = sl.tryOptimisticRead(); // 락을 잡지 않는다
        double currentX = x, currentY = y;
        if (!sl.validate(stamp)) {
            // 읽는 동안 쓰기가 발생했다면 읽기 락으로 재시도
            stamp = sl.readLock();
            try {
                currentX = x;
                currentY = y;
            } finally {
                sl.unlockRead(stamp);
            }
        }
        return Math.sqrt(currentX * currentX + currentY * currentY);
    }
}
```

`tryOptimisticRead`는 실제 락을 잡지 않고 stamp만 받는다. 읽기 후 `validate`로 그 사이에 쓰기가 있었는지 확인한다. 쓰기가 없었으면 락 없이 읽기가 완료된다. 읽기가 압도적으로 많은 상황에서 `ReadWriteLock`보다 성능이 좋다.

---

## futex: Linux 동기화의 핵심

Linux에서 pthread의 mutex, semaphore, condition variable, rwlock은 모두 내부적으로 **futex** (Fast Userspace muTEX)를 사용한다.

### 기본 아이디어

경합이 없으면 커널에 들어가지 않는다. 유저 스페이스의 atomic 연산만으로 처리한다. 경합이 발생할 때만 `futex()` 시스템콜로 커널에 진입해서 스레드를 sleep/wakeup 시킨다.

```
// 경합 없는 경우 (fast path)
lock():
    if (atomic_compare_exchange(&state, 0, 1))  // CAS 성공
        return;  // 커널 진입 없이 완료

// 경합 발생 (slow path)
lock():
    while (!atomic_compare_exchange(&state, 0, 1)) {
        futex(&state, FUTEX_WAIT, 1, ...);  // 커널에서 sleep
    }

unlock():
    atomic_store(&state, 0);
    futex(&state, FUTEX_WAKE, 1, ...);  // 대기 중인 스레드 하나 깨우기
```

### futex 시스템콜

```c
#include <linux/futex.h>
#include <sys/syscall.h>

// addr: 감시할 유저 스페이스 주소
// FUTEX_WAIT: *addr == val이면 sleep
// FUTEX_WAKE: 최대 val개의 대기 스레드를 깨운다
long futex(uint32_t *addr, int op, uint32_t val,
           const struct timespec *timeout, uint32_t *addr2, uint32_t val3);
```

실제로 직접 쓸 일은 없다. pthread 라이브러리가 감싸고 있다. 하지만 락 관련 성능 문제를 디버깅할 때 `strace`나 `perf`에서 futex 호출이 보이면, 경합이 심하다는 의미다.

### glibc의 pthread_mutex 구현

glibc에서 `pthread_mutex_lock`은 대략 이런 구조다:

```
1. state를 atomic CAS로 0→1 시도 (fast path)
2. 성공하면 바로 리턴
3. 실패하면 state를 2로 세팅 (2 = "대기자 있음")
4. futex(FUTEX_WAIT, 2) 호출 → 커널에서 sleep
5. 깨어나면 다시 CAS 시도
6. unlock 시 state가 2였으면 futex(FUTEX_WAKE, 1) 호출
```

state 값의 의미:
- `0`: unlocked
- `1`: locked, 대기자 없음
- `2`: locked, 대기자 있음

`1`과 `2`를 구분하는 이유: unlock 시 대기자가 없으면 `futex(FUTEX_WAKE)` 시스템콜을 생략해서 성능을 높인다.

---

## 락 경합 측정 및 대응

동기화 코드를 작성하는 것보다 운영 환경에서 경합 문제를 찾고 대응하는 게 더 어렵다.

### Linux에서 측정

**perf로 futex 경합 확인**

```bash
# futex 관련 시스템콜 추적
perf trace -e futex -p <PID> -- sleep 5

# 락 경합으로 인한 스케줄링 이벤트
perf lock record -p <PID> -- sleep 10
perf lock report
```

`perf lock report` 출력에서 `wait_total`과 `wait_max` 값이 크면 경합이 심한 것이다.

**mutex 경합 통계 (pthread)**

```c
// 락 경합 디버깅용: mutex를 ERRORCHECK 타입으로 바꾸고 trylock 실패 횟수를 세는 방법
int contention_count = 0;

void counted_lock(pthread_mutex_t *mtx) {
    if (pthread_mutex_trylock(mtx) != 0) {
        __atomic_add_fetch(&contention_count, 1, __ATOMIC_RELAXED);
        pthread_mutex_lock(mtx); // 실제 대기
    }
}
```

이 카운터가 빠르게 증가하면 해당 뮤텍스에서 경합이 발생하고 있다는 뜻이다.

### Java에서 측정

**JFR (Java Flight Recorder)**

```bash
# JFR 기록 시작
jcmd <PID> JFR.start duration=60s filename=recording.jfr

# JFR 파일 분석 — JDK Mission Control에서 열기
```

JFR에서 `Java Monitor Blocked` 이벤트를 확인한다. 어떤 스레드가 어떤 모니터에서 얼마나 오래 대기했는지 나온다.

**jstack으로 BLOCKED 스레드 확인**

```bash
# 3초 간격으로 10번 스레드 덤프
for i in $(seq 1 10); do
    jstack <PID> >> thread_dumps.txt
    sleep 3
done
```

덤프를 여러 번 떠서 같은 스레드가 계속 `BLOCKED` 상태이면 경합이 심한 것이다.

### 경합 대응 방법

**1. 임계 영역 줄이기**

가장 먼저 해야 할 것이다. 락 안에서 하는 일을 최소화한다.

```java
// 나쁜 예: 락 안에서 로그 출력, 계산 다 한다
synchronized (lock) {
    data = computeExpensiveResult();
    logger.info("computed: " + data);
    map.put(key, data);
}

// 개선: 락 밖에서 할 수 있는 건 밖에서 한다
Data data = computeExpensiveResult();
String logMsg = "computed: " + data;
synchronized (lock) {
    map.put(key, data);
}
logger.info(logMsg);
```

**2. 락 분할 (Lock Striping)**

하나의 락으로 전체 자료구조를 보호하는 대신, 여러 락으로 나눈다. `ConcurrentHashMap`이 내부적으로 이 방식을 쓴다.

```java
public class StripedMap<K, V> {
    private static final int STRIPE_COUNT = 16;
    private final Object[] locks = new Object[STRIPE_COUNT];
    private final Map<K, V>[] buckets;

    @SuppressWarnings("unchecked")
    public StripedMap() {
        buckets = new HashMap[STRIPE_COUNT];
        for (int i = 0; i < STRIPE_COUNT; i++) {
            locks[i] = new Object();
            buckets[i] = new HashMap<>();
        }
    }

    private int stripeIndex(K key) {
        return Math.abs(key.hashCode() % STRIPE_COUNT);
    }

    public V get(K key) {
        int idx = stripeIndex(key);
        synchronized (locks[idx]) {
            return buckets[idx].get(key);
        }
    }

    public void put(K key, V value) {
        int idx = stripeIndex(key);
        synchronized (locks[idx]) {
            buckets[idx].put(key, value);
        }
    }
}
```

서로 다른 stripe에 속하는 키들은 동시에 접근 가능하다. stripe 수가 많을수록 경합이 줄어들지만 메모리 사용량이 늘어난다.

**3. Lock-Free 자료구조 사용**

`java.util.concurrent.atomic` 패키지의 `AtomicInteger`, `AtomicReference`, `LongAdder` 등은 락 없이 CAS 연산으로 동작한다.

```java
// AtomicLong 대신 LongAdder — 경합이 심할 때 훨씬 빠르다
private final LongAdder requestCount = new LongAdder();

public void handleRequest() {
    // 락 없이 카운트 증가
    requestCount.increment();
}

public long getCount() {
    return requestCount.sum();
}
```

`LongAdder`는 내부적으로 여러 Cell에 분산해서 카운트하고, `sum()` 호출 시 합산한다. 쓰기가 많고 읽기가 가끔인 카운터에 적합하다. `AtomicLong`은 단일 변수에 CAS를 하니까 경합이 심하면 재시도가 많아진다.

**4. 락 대신 메시지 패싱**

공유 자원 자체를 없애고, 스레드 간 메시지로 통신하는 방식이다. Go의 채널, Java의 `BlockingQueue`, Actor 모델 등이 해당된다. 락 경합 자체가 사라지지만, 설계를 처음부터 다시 해야 할 수 있다.

---

## 동기화 프리미티브 선택 기준

| 상황 | 선택 |
|------|------|
| 단순 상호 배제 | Mutex (`synchronized`, `pthread_mutex`) |
| 동시 접근 수 제한 | Semaphore |
| 조건 기반 대기/통지 | Condition Variable (`wait`/`notify`) |
| 읽기 많고 쓰기 적음 | RWLock, StampedLock |
| 임계 영역이 수십 ns 이하 | Spinlock (커널 코드 한정) |
| 카운터 업데이트 | `LongAdder`, `AtomicLong` |
| 경합 자체를 없애고 싶음 | 메시지 패싱, Lock-Free 자료구조 |

어떤 동기화 프리미티브를 쓰든, 임계 영역을 최소화하는 게 성능에 가장 큰 영향을 준다. 락 자체가 느린 게 아니라 경합이 느린 것이다. 경합이 없으면 mutex lock/unlock은 수십 나노초면 끝난다.
