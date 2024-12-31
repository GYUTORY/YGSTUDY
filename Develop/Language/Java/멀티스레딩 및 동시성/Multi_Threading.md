# Java 멀티스레딩

Java에서 멀티스레딩은 여러 스레드가 동시에 실행되도록 하여 프로그램의 성능을 향상시키는 기법입니다. 멀티스레딩은 CPU 사용률을 높이고, 프로그램의 응답성을 개선하며, 여러 작업을 병렬로 처리하는 데 유용합니다.

## 기본 개념

### 스레드(Thread)
스레드는 프로세스 내에서 실행되는 하나의 작업 흐름입니다. Java에서 각 스레드는 독립적으로 실행되며, JVM이 스레드 스케줄링을 관리합니다.

### 멀티스레딩(Multi-threading)
멀티스레딩은 여러 스레드가 동시에 실행되어, 여러 작업을 병렬로 수행하는 것을 의미합니다. 이를 통해 애플리케이션의 성능과 효율성을 극대화할 수 있습니다.

### Java에서 스레드 구현 방법
1. **Thread 클래스 상속**
2. **Runnable 인터페이스 구현**

## 스레드 생성 및 실행

### 방법 1: Thread 클래스 상속
```java
class MyThread extends Thread {
    public void run() {
        for (int i = 0; i < 5; i++) {
            System.out.println(Thread.currentThread().getName() + " - 실행 중: " + i);
            try {
                Thread.sleep(500); // 500ms 대기
            } catch (InterruptedException e) {
                System.out.println("스레드 인터럽트 발생");
            }
        }
    }
}

public class Main {
    public static void main(String[] args) {
        MyThread thread1 = new MyThread();
        MyThread thread2 = new MyThread();

        thread1.start();
        thread2.start();
    }
}
```

### 방법 2: Runnable 인터페이스 구현
```java
class MyRunnable implements Runnable {
    public void run() {
        for (int i = 0; i < 5; i++) {
            System.out.println(Thread.currentThread().getName() + " - 실행 중: " + i);
            try {
                Thread.sleep(500); // 500ms 대기
            } catch (InterruptedException e) {
                System.out.println("스레드 인터럽트 발생");
            }
        }
    }
}

public class Main {
    public static void main(String[] args) {
        Thread thread1 = new Thread(new MyRunnable());
        Thread thread2 = new Thread(new MyRunnable());

        thread1.start();
        thread2.start();
    }
}
```

## 주요 메서드

| 메서드                     | 설명                                      |
|---------------------------|------------------------------------------|
| `start()`                 | 스레드를 시작하고, `run()` 메서드를 호출합니다. |
| `run()`                   | 스레드가 실행할 코드를 정의합니다.         |
| `sleep(milliseconds)`     | 지정된 시간 동안 스레드를 일시 정지합니다. |
| `join()`                  | 다른 스레드가 종료될 때까지 현재 스레드를 대기시킵니다. |
| `isAlive()`               | 스레드가 실행 중인지 확인합니다.           |

## 동기화(Synchronization)
멀티스레딩 환경에서는 여러 스레드가 동시에 공유 자원에 접근하면 **경쟁 상태(Race Condition)**가 발생할 수 있습니다. 이를 방지하기 위해 **동기화(Synchronization)**를 사용합니다.

### 동기화 블록
```java
class Counter {
    private int count = 0;

    public synchronized void increment() {
        count++;
    }

    public int getCount() {
        return count;
    }
}

public class Main {
    public static void main(String[] args) {
        Counter counter = new Counter();

        Thread thread1 = new Thread(() -> {
            for (int i = 0; i < 1000; i++) {
                counter.increment();
            }
        });

        Thread thread2 = new Thread(() -> {
            for (int i = 0; i < 1000; i++) {
                counter.increment();
            }
        });

        thread1.start();
        thread2.start();

        try {
            thread1.join();
            thread2.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        System.out.println("최종 카운트: " + counter.getCount());
    }
}
```

## 실행 결과 예시
```
Thread-0 - 실행 중: 0
Thread-1 - 실행 중: 0
Thread-0 - 실행 중: 1
Thread-1 - 실행 중: 1
...
최종 카운트: 2000
```

## 결론
Java의 멀티스레딩은 고성능 애플리케이션을 개발하는 데 매우 유용합니다. 그러나 동기화를 적절히 사용하지 않으면 데이터 손실이나 경쟁 상태와 같은 문제가 발생할 수 있으므로 주의해야 합니다.
