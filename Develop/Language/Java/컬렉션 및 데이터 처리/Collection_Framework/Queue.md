---
title: Java Queue
tags: [language, java, 컬렉션-및-데이터-처리, collectionframework, queue]
updated: 2025-08-10
---

# Java Queue

## 배경

**Queue(큐)** 는 FIFO(First-In-First-Out, 선입선출) 구조를 따르는 데이터 구조입니다.  
먼저 들어온 데이터가 먼저 나가며, 줄을 서서 기다리는 것과 유사한 개념입니다.

Java 컬렉션 프레임워크에서는 `Queue` 인터페이스로 정의되며, 여러 구현체를 제공합니다.  
큐는 보통 데이터의 순차적인 처리를 위해 사용됩니다.

---


1. **PriorityQueue**
    - 우선순위에 따라 요소를 정렬하며, 기본적으로 자연 순서를 따릅니다.
    - 우선순위를 커스터마이징하려면 `Comparator`를 제공해야 합니다.

2. **LinkedList**
    - FIFO 구조를 유지하면서 큐를 구현합니다.
    - 이중 연결 리스트로 구현되어 큐와 Deque(양방향 큐)로 사용 가능합니다.

3. **ArrayDeque**
    - `LinkedList`보다 성능이 우수한 큐 구현체입니다.
    - 메모리 효율성과 빠른 성능을 제공하며, FIFO와 LIFO(Last-In-First-Out) 모두 지원합니다.

---


- **`offer(E e)`**: 큐의 끝에 요소 추가 (성공 여부를 반환).
- **`poll()`**: 큐의 맨 앞 요소 제거 및 반환. 큐가 비어 있으면 `null` 반환.
- **`peek()`**: 큐의 맨 앞 요소를 반환하지만 제거하지 않음. 큐가 비어 있으면 `null` 반환.

---


### 1. PriorityQueue 예제

```java
import java.util.PriorityQueue;

public class PriorityQueueExample {
    public static void main(String[] args) {
        PriorityQueue<Integer> queue = new PriorityQueue<>();

        // 요소 추가
        queue.offer(10);
        queue.offer(5);
        queue.offer(20);

        // 우선순위에 따라 요소가 정렬됨
        System.out.println("큐에서 제거되는 순서:");
        while (!queue.isEmpty()) {
            System.out.println(queue.poll());
        }
    }
}
```

**출력 결과:**  
요소가 우선순위(오름차순)에 따라 출력됩니다.

---

### 2. LinkedList 예제

```java
import java.util.LinkedList;
import java.util.Queue;

public class LinkedListQueueExample {
    public static void main(String[] args) {
        Queue<String> queue = new LinkedList<>();

        // 요소 추가
        queue.offer("첫 번째");
        queue.offer("두 번째");
        queue.offer("세 번째");

        // 큐의 맨 앞 요소 접근 및 제거
        System.out.println("처음 요소: " + queue.peek()); // 제거하지 않고 반환
        System.out.println("처음 제거된 요소: " + queue.poll()); // 제거 후 반환

        // 나머지 요소 출력
        System.out.println("남은 요소들: " + queue);
    }
}
```

**특징:**
- FIFO 구조로 처리됩니다.
- 요소 추가와 제거가 간단하게 이루어짐.

---

### 3. ArrayDeque 예제

```java
import java.util.ArrayDeque;
import java.util.Queue;

public class ArrayDequeExample {
    public static void main(String[] args) {
        Queue<String> queue = new ArrayDeque<>();

        // 요소 추가
        queue.offer("A");
        queue.offer("B");
        queue.offer("C");

        // 요소 제거 및 출력
        while (!queue.isEmpty()) {
            System.out.println("제거된 요소: " + queue.poll());
        }
    }
}
```

**장점:**
- `LinkedList`보다 빠르고 메모리 효율적.

---


1. **프로세스 스케줄링**  
   운영체제에서 프로세스를 순서대로 실행하는 데 사용됩니다.

2. **데이터 스트리밍**  
   네트워크 데이터 처리에서 순차적인 데이터 스트리밍 관리.

3. **프린터 작업 관리**  
   인쇄 대기열처럼 먼저 들어온 작업이 먼저 처리됨.

---


Java에서 `Queue`는 데이터를 순차적으로 처리해야 할 때 매우 유용한 데이터 구조입니다.  
`PriorityQueue`, `LinkedList`, `ArrayDeque`와 같은 다양한 구현체를 상황에 맞게 선택하여 사용하면 효율적인 프로그램을 작성할 수 있습니다.










