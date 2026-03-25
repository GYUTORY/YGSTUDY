---
title: Java 컬렉션 프레임워크
tags: [language, java, 컬렉션-및-데이터-처리, collectionframework]
updated: 2026-03-25
---

# Java 컬렉션 프레임워크

Java에서 데이터를 다루려면 컬렉션 프레임워크를 피할 수 없다. `List`, `Set`, `Map`, `Queue` 인터페이스와 그 구현체들로 구성된다. 문제는 "어떤 걸 쓰느냐"에 따라 성능 차이가 크고, 멀티스레드 환경에서 터지는 버그가 대부분 컬렉션에서 나온다는 점이다.

---

## List 구현체 비교: ArrayList vs LinkedList

둘 다 `List` 인터페이스를 구현하지만 내부 구조가 완전히 다르다.

### ArrayList

내부적으로 `Object[]` 배열을 사용한다. 인덱스 기반 접근이 O(1)이라 조회가 빠르다.

```java
ArrayList<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("C");

// 인덱스 접근 - O(1)
String value = list.get(1); // "B"
```

문제는 중간 삽입/삭제다. 배열 중간에 요소를 넣으면 뒤쪽 요소를 전부 한 칸씩 밀어야 한다. `System.arraycopy`가 내부에서 호출된다.

```java
// 인덱스 0에 삽입 - O(n), 뒤의 모든 요소가 이동
list.add(0, "Z");
```

초기 용량을 지정하지 않으면 기본 10개로 시작한다. 데이터가 많을 걸 알면 미리 잡아두는 게 맞다.

```java
// 10만 건 넣을 거면 미리 용량 지정
ArrayList<Order> orders = new ArrayList<>(100_000);
```

용량이 찰 때마다 기존 크기의 1.5배로 새 배열을 만들고 복사한다. 이 과정이 반복되면 GC 부담이 생긴다.

### LinkedList

이중 연결 리스트(doubly linked list)다. 각 노드가 이전/다음 노드의 참조를 갖고 있다.

```java
LinkedList<String> linked = new LinkedList<>();
linked.add("A");
linked.add("B");
linked.add("C");

// 앞뒤 삽입/삭제 - O(1)
linked.addFirst("Z");
linked.removeLast();
```

인덱스로 접근하면 처음부터 순회해야 해서 O(n)이다. `linked.get(50000)` 같은 호출은 5만 번 노드를 타고 가야 한다.

### 성능 비교 정리

| 연산 | ArrayList | LinkedList |
|------|-----------|------------|
| `get(index)` | O(1) | O(n) |
| `add(E)` (끝에 추가) | 평균 O(1), 리사이징 시 O(n) | O(1) |
| `add(0, E)` (앞에 삽입) | O(n) | O(1) |
| `remove(index)` (중간 삭제) | O(n) | O(n) — 탐색 O(n) + 삭제 O(1) |
| 메모리 | 연속 메모리, 캐시 친화적 | 노드마다 prev/next 참조 추가, 메모리 분산 |

실무에서는 거의 ArrayList를 쓴다. LinkedList가 이론적으로 빠른 경우(앞쪽 삽입/삭제가 빈번한 경우)에도, CPU 캐시 지역성 때문에 ArrayList가 더 빠른 경우가 많다. LinkedList는 `Deque`로 쓸 때 정도가 적당하다.

---

## Set 구현체

### HashSet

내부적으로 `HashMap`을 사용한다. 값은 더미 `Object`를 넣고, 키 자리에 실제 데이터를 저장한다.

```java
Set<String> set = new HashSet<>();
set.add("A");
set.add("B");
set.add("A"); // 무시됨

// 순서 보장 안 됨
for (String s : set) {
    System.out.println(s);
}
```

`equals()`와 `hashCode()`를 제대로 구현하지 않으면 중복 제거가 안 된다. 커스텀 객체를 Set에 넣을 때 흔히 실수하는 부분이다.

```java
public class User {
    private Long id;
    private String name;

    // 이걸 빼먹으면 같은 id의 User가 Set에 여러 개 들어간다
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof User user)) return false;
        return Objects.equals(id, user.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
```

### LinkedHashSet

삽입 순서를 유지하는 Set이다. 내부적으로 `LinkedHashMap`을 사용한다. 순서가 필요하면서 중복은 제거해야 할 때 쓴다.

### TreeSet

정렬된 상태를 유지하는 Set이다. 내부적으로 `TreeMap`(Red-Black Tree)을 사용한다. 삽입/조회가 O(log n)이라 HashSet의 O(1)보다 느리다. 정렬이 필요한 경우에만 쓴다.

---

## Map 구현체

### HashMap

가장 많이 쓰는 Map 구현체다. 해시 테이블 기반이고, Java 8부터 한 버킷에 충돌이 8개 이상 쌓이면 연결 리스트에서 Red-Black Tree로 변환한다.

```java
Map<String, Integer> map = new HashMap<>();
map.put("apple", 10);
map.put("banana", 20);

// getOrDefault - NullPointerException 방지
int count = map.getOrDefault("cherry", 0);

// putIfAbsent - 키가 없을 때만 삽입
map.putIfAbsent("apple", 99); // 이미 있으므로 무시

// compute 계열 - 값 갱신 시 유용
map.merge("apple", 5, Integer::sum); // apple: 15
```

`HashMap`은 스레드 안전하지 않다. 멀티스레드에서 동시에 `put`하면 데이터가 유실되거나, Java 7 이하에서는 무한 루프에 빠지는 버그가 있었다.

### LinkedHashMap

삽입 순서를 유지한다. LRU 캐시를 직접 만들 때 유용하다.

```java
// accessOrder=true로 설정하면 접근 순서 기반으로 정렬
// removeEldestEntry를 오버라이드해서 LRU 캐시 구현
Map<String, String> lruCache = new LinkedHashMap<>(16, 0.75f, true) {
    @Override
    protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
        return size() > 100; // 최대 100개
    }
};
```

### TreeMap

키가 정렬된 상태를 유지한다. `NavigableMap` 인터페이스를 구현하므로 범위 검색이 가능하다.

```java
TreeMap<Integer, String> treeMap = new TreeMap<>();
treeMap.put(3, "C");
treeMap.put(1, "A");
treeMap.put(5, "E");
treeMap.put(2, "B");

// 범위 검색
SortedMap<Integer, String> sub = treeMap.subMap(2, 5); // {2=B, 3=C}
Integer firstKey = treeMap.firstKey(); // 1
Integer floorKey = treeMap.floorKey(4); // 3 (4 이하에서 가장 큰 키)
```

---

## 동시성 컬렉션

멀티스레드 환경에서 일반 컬렉션을 쓰면 문제가 생긴다. `Collections.synchronizedList()` 같은 래퍼도 있지만, 모든 메서드에 `synchronized`를 거는 방식이라 성능이 나쁘다.

### ConcurrentHashMap

`HashMap`의 스레드 안전 버전이다. Java 8부터는 버킷 단위 잠금(CAS + synchronized)을 사용해서 `Hashtable`이나 `Collections.synchronizedMap()`보다 훨씬 빠르다.

```java
ConcurrentHashMap<String, AtomicInteger> counter = new ConcurrentHashMap<>();

// 여러 스레드에서 동시에 호출해도 안전
counter.computeIfAbsent("pageView", k -> new AtomicInteger(0))
       .incrementAndGet();
```

주의할 점: `ConcurrentHashMap`은 개별 연산은 원자적이지만, 복합 연산은 아니다.

```java
// 이 코드는 스레드 안전하지 않다
if (!map.containsKey(key)) {
    map.put(key, value);
}

// 대신 이렇게 쓴다
map.putIfAbsent(key, value);

// 또는 compute 계열 사용
map.compute(key, (k, v) -> v == null ? 1 : v + 1);
```

`ConcurrentHashMap`에서 `null` 키와 `null` 값은 허용되지 않는다. `HashMap`에서는 되는데 `ConcurrentHashMap`에서 안 돼서 마이그레이션할 때 NPE가 터지는 경우가 있다.

### CopyOnWriteArrayList

읽기가 압도적으로 많고 쓰기가 드문 경우에 쓴다. 쓰기 시 내부 배열 전체를 복사하므로, 쓰기가 빈번하면 성능이 심하게 나빠진다.

```java
// 설정값 목록처럼 읽기 위주인 경우에 적합
CopyOnWriteArrayList<String> configs = new CopyOnWriteArrayList<>();
configs.add("config1");

// 순회 중 수정해도 ConcurrentModificationException 안 남
// 순회 시점의 스냅샷을 사용하기 때문
for (String config : configs) {
    configs.add("newConfig"); // 현재 순회에는 반영 안 됨
}
```

### ConcurrentLinkedQueue

비차단(non-blocking) 큐다. `CAS` 연산 기반이라 락 없이 동작한다. 생산자-소비자 패턴에서 사용한다.

### BlockingQueue 구현체

스레드가 큐에서 데이터를 꺼낼 때 데이터가 없으면 대기한다.

```java
BlockingQueue<Task> queue = new LinkedBlockingQueue<>(1000);

// 생산자
queue.put(new Task("job1")); // 큐가 가득 차면 대기

// 소비자
Task task = queue.take(); // 큐가 비면 대기
```

| 구현체 | 특징 |
|--------|------|
| `ArrayBlockingQueue` | 고정 크기, 배열 기반 |
| `LinkedBlockingQueue` | 가변 크기(기본 Integer.MAX_VALUE), 연결 리스트 기반 |
| `PriorityBlockingQueue` | 우선순위 기반 정렬 |

---

## Iterator와 ListIterator

### Iterator

컬렉션을 순회하는 표준 방법이다. `for-each` 문도 내부적으로 `Iterator`를 사용한다.

```java
List<String> list = new ArrayList<>(List.of("A", "B", "C", "D"));

// Iterator로 순회하면서 삭제 - 안전한 방법
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    String value = it.next();
    if ("B".equals(value)) {
        it.remove(); // Iterator의 remove()를 사용해야 한다
    }
}
```

### ListIterator

`List` 전용 Iterator로, 양방향 순회와 삽입이 가능하다.

```java
List<String> list = new ArrayList<>(List.of("A", "B", "C"));

ListIterator<String> lit = list.listIterator();
while (lit.hasNext()) {
    String value = lit.next();
    if ("B".equals(value)) {
        lit.set("B_MODIFIED"); // 현재 요소 교체
        lit.add("B2");         // 현재 위치 뒤에 삽입
    }
}
// 결과: [A, B_MODIFIED, B2, C]

// 역방향 순회
while (lit.hasPrevious()) {
    System.out.println(lit.previous());
}
```

---

## 방어적 복사와 불변 컬렉션

외부에 컬렉션을 반환할 때 원본이 수정되는 걸 막아야 하는 경우가 있다.

### Collections.unmodifiableList

원본 리스트의 읽기 전용 뷰를 반환한다. 수정하려고 하면 `UnsupportedOperationException`이 발생한다.

```java
public class Team {
    private final List<String> members;

    public Team(List<String> members) {
        // 방어적 복사 - 외부에서 전달된 리스트를 그대로 쓰면
        // 외부에서 원본을 수정할 수 있다
        this.members = new ArrayList<>(members);
    }

    public List<String> getMembers() {
        // 읽기 전용 뷰 반환
        return Collections.unmodifiableList(members);
    }
}
```

주의: `unmodifiableList`는 원본 리스트를 감싸는 래퍼일 뿐이다. 원본 리스트를 직접 수정하면 뷰에도 반영된다.

```java
List<String> original = new ArrayList<>(List.of("A", "B"));
List<String> unmodifiable = Collections.unmodifiableList(original);

original.add("C"); // 원본 수정
System.out.println(unmodifiable); // [A, B, C] - 뷰에도 반영됨
```

그래서 생성자에서 `new ArrayList<>(members)`로 복사한 뒤 `unmodifiableList`로 감싸는 패턴을 같이 쓴다.

### List.of / Map.of (Java 9+)

Java 9부터 제공되는 팩토리 메서드로, 진짜 불변 컬렉션을 만든다.

```java
List<String> immutable = List.of("A", "B", "C");
// immutable.add("D"); // UnsupportedOperationException

Map<String, Integer> map = Map.of("a", 1, "b", 2);
// map.put("c", 3); // UnsupportedOperationException
```

`List.of()`는 `null`을 허용하지 않는다. `null`을 넣으면 `NullPointerException`이 터진다.

### List.copyOf (Java 10+)

기존 컬렉션을 불변으로 복사한다.

```java
List<String> mutable = new ArrayList<>(List.of("A", "B"));
List<String> immutableCopy = List.copyOf(mutable);

mutable.add("C");
System.out.println(immutableCopy); // [A, B] - 영향 없음
```

---

## ConcurrentModificationException 트러블슈팅

실무에서 가장 자주 마주치는 컬렉션 관련 예외다. 컬렉션을 순회하는 도중에 구조가 변경되면 발생한다.

### 발생하는 코드

```java
List<String> list = new ArrayList<>(List.of("A", "B", "C"));

// for-each 순회 중 remove - ConcurrentModificationException 발생
for (String item : list) {
    if ("B".equals(item)) {
        list.remove(item); // 여기서 터진다
    }
}
```

`for-each`는 내부적으로 `Iterator`를 사용하는데, `list.remove()`를 직접 호출하면 Iterator가 모르는 사이에 구조가 바뀌어서 `modCount` 불일치로 예외가 발생한다.

### 해결 방법 1: Iterator.remove()

```java
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if ("B".equals(it.next())) {
        it.remove(); // Iterator를 통한 삭제는 안전
    }
}
```

### 해결 방법 2: removeIf (Java 8+)

가장 깔끔하다.

```java
list.removeIf(item -> "B".equals(item));
// 또는
list.removeIf("B"::equals);
```

### 해결 방법 3: 역순 인덱스 순회

인덱스를 뒤에서부터 순회하면 삭제해도 앞쪽 인덱스에 영향이 없다.

```java
for (int i = list.size() - 1; i >= 0; i--) {
    if ("B".equals(list.get(i))) {
        list.remove(i);
    }
}
```

### 해결 방법 4: 새 리스트에 필터링

원본을 수정하지 않고 새 리스트를 만드는 방법이다. Stream과 함께 쓰면 자연스럽다.

```java
List<String> filtered = list.stream()
    .filter(item -> !"B".equals(item))
    .collect(Collectors.toList());
```

### 멀티스레드에서의 ConcurrentModificationException

싱글 스레드에서도 발생하지만, 멀티스레드에서는 한 스레드가 순회하는 동안 다른 스레드가 수정해서 터지는 경우가 더 많다. 이 경우 `ConcurrentHashMap`, `CopyOnWriteArrayList` 같은 동시성 컬렉션을 사용하거나, 외부 동기화를 해야 한다.

```java
// 방법 1: 동시성 컬렉션 사용
List<String> safeList = new CopyOnWriteArrayList<>();

// 방법 2: 외부 동기화
List<String> syncList = Collections.synchronizedList(new ArrayList<>());
synchronized (syncList) {
    for (String item : syncList) {
        // 순회 중 다른 스레드의 수정 차단
    }
}
```

`synchronizedList`를 쓰더라도 순회할 때는 반드시 `synchronized` 블록으로 감싸야 한다. 개별 `add`, `get`은 동기화되지만, 순회는 여러 번의 호출이므로 별도로 잠금이 필요하다.

---

## 실무에서 자주 하는 실수

### HashMap의 키로 가변 객체 사용

`HashMap`에 넣은 뒤 키 객체의 필드를 바꾸면, `hashCode`가 달라져서 해당 엔트리를 찾을 수 없게 된다.

```java
List<String> key = new ArrayList<>(List.of("A"));
Map<List<String>, String> map = new HashMap<>();
map.put(key, "value");

key.add("B"); // 키의 hashCode가 변경됨
System.out.println(map.get(key)); // null - 찾을 수 없음
```

키로는 `String`, `Integer` 같은 불변 객체를 쓰는 게 안전하다.

### Arrays.asList의 함정

`Arrays.asList()`가 반환하는 리스트는 고정 크기 리스트다. `add`, `remove`가 안 된다.

```java
List<String> list = Arrays.asList("A", "B", "C");
// list.add("D"); // UnsupportedOperationException

// 수정 가능한 리스트가 필요하면 감싸야 한다
List<String> mutable = new ArrayList<>(Arrays.asList("A", "B", "C"));
mutable.add("D"); // 정상 동작
```

### subList 반환값의 원본 연결

`subList()`는 원본 리스트의 뷰를 반환한다. 원본이 바뀌면 subList도 깨진다.

```java
List<String> original = new ArrayList<>(List.of("A", "B", "C", "D"));
List<String> sub = original.subList(1, 3); // [B, C]

original.add("E"); // 원본 구조 변경
// sub.get(0); // ConcurrentModificationException 발생
```

독립적인 리스트가 필요하면 `new ArrayList<>(original.subList(1, 3))`으로 복사해야 한다.
