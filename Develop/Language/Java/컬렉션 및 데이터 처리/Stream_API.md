---
title: Java Stream API 심화 가이드
tags: [java, stream, lambda, functional-programming, collectors, parallel-stream]
updated: 2026-03-01
---

# Java Stream API 심화

## 개요

Stream API는 Java 8에서 도입된 **컬렉션 데이터를 선언적으로 처리**하는 API이다. for 루프 대신 파이프라인 방식으로 필터링, 변환, 집계를 체이닝하여 가독성과 생산성을 높인다.

### 왜 Stream을 쓰는가

```java
// ❌ 명령형 (어떻게 처리할지 직접 지시)
List<String> result = new ArrayList<>();
for (User user : users) {
    if (user.getAge() >= 20) {
        result.add(user.getName());
    }
}
Collections.sort(result);

// ✅ 선언형 (무엇을 원하는지 기술)
List<String> result = users.stream()
    .filter(user -> user.getAge() >= 20)
    .map(User::getName)
    .sorted()
    .toList();
```

### Stream 특징

| 특징 | 설명 |
|------|------|
| **지연 평가 (Lazy)** | 최종 연산 호출 전까지 중간 연산 실행 안 함 |
| **일회성** | 한 번 소비하면 재사용 불가 |
| **원본 불변** | 원본 컬렉션을 변경하지 않음 |
| **내부 반복** | 반복 로직을 라이브러리가 처리 |

## 핵심

### 1. Stream 파이프라인 구조

```
소스 → 중간 연산 → 중간 연산 → ... → 최종 연산 → 결과

List<User> users → .filter()  → .map()  → .collect()  → List<String>
                   (중간 연산)  (중간 연산)  (최종 연산)
```

#### Stream 생성

```java
// 컬렉션에서
List<String> list = List.of("a", "b", "c");
list.stream();

// 배열에서
Arrays.stream(new int[]{1, 2, 3});

// 직접 생성
Stream.of("x", "y", "z");
Stream.empty();

// 무한 스트림
Stream.iterate(0, n -> n + 2);          // 0, 2, 4, 6, ...
Stream.generate(Math::random);           // 랜덤 값 무한

// 범위
IntStream.range(1, 10);                  // 1~9
IntStream.rangeClosed(1, 10);            // 1~10

// 파일에서
Files.lines(Path.of("data.txt"));        // 파일을 한 줄씩 Stream
```

### 2. 중간 연산 (Intermediate Operations)

지연 평가(Lazy). 최종 연산이 호출될 때 실행된다.

```java
// filter: 조건에 맞는 요소만 통과
users.stream()
    .filter(u -> u.getAge() >= 20)
    .filter(u -> u.isActive())

// map: 요소 변환
users.stream()
    .map(User::getName)              // User → String
    .map(String::toUpperCase)        // String → String

// flatMap: 중첩 컬렉션 평탄화
// [[1,2], [3,4], [5]] → [1, 2, 3, 4, 5]
orders.stream()
    .flatMap(order -> order.getItems().stream())

// distinct: 중복 제거 (equals/hashCode 기반)
numbers.stream().distinct()

// sorted: 정렬
users.stream()
    .sorted(Comparator.comparing(User::getAge))
    .sorted(Comparator.comparing(User::getName).reversed())

// peek: 디버깅용 (부수 효과)
users.stream()
    .filter(u -> u.getAge() >= 20)
    .peek(u -> log.debug("필터 통과: {}", u))
    .map(User::getName)

// limit / skip: 개수 제한
users.stream().skip(10).limit(20)    // 11~30번째 요소

// takeWhile / dropWhile (Java 9+)
Stream.of(1, 2, 3, 4, 5, 1, 2)
    .takeWhile(n -> n < 4)           // [1, 2, 3] (조건 실패 시 중단)
    .dropWhile(n -> n < 3)           // [3, 4, 5, 1, 2] (조건 실패 전까지 버림)
```

#### flatMap 상세

```java
// 1:N 변환 시 사용
// 주문 목록에서 모든 상품 추출
List<Product> allProducts = orders.stream()
    .flatMap(order -> order.getProducts().stream())
    .distinct()
    .toList();

// 문자열 → 단어 분리
List<String> words = sentences.stream()
    .flatMap(sentence -> Arrays.stream(sentence.split(" ")))
    .toList();

// Optional과 함께 (null 안전 평탄화)
List<String> emails = users.stream()
    .map(User::getEmail)             // Stream<Optional<String>>
    .flatMap(Optional::stream)       // Stream<String> (빈 Optional 제거)
    .toList();
```

### 3. 최종 연산 (Terminal Operations)

파이프라인을 실행하고 결과를 반환한다.

```java
// collect: 결과를 컬렉션으로 수집
List<String> names = users.stream()
    .map(User::getName)
    .collect(Collectors.toList());    // 또는 .toList() (Java 16+, 불변)

// forEach: 각 요소에 대해 작업 수행
users.stream().forEach(System.out::println);

// count: 요소 개수
long count = users.stream().filter(User::isActive).count();

// reduce: 요소를 하나로 합침
int sum = numbers.stream().reduce(0, Integer::sum);
Optional<Integer> max = numbers.stream().reduce(Integer::max);

// findFirst / findAny
Optional<User> first = users.stream()
    .filter(u -> u.getAge() > 30)
    .findFirst();

// anyMatch / allMatch / noneMatch
boolean hasAdmin = users.stream().anyMatch(u -> u.getRole().equals("ADMIN"));
boolean allActive = users.stream().allMatch(User::isActive);

// min / max
Optional<User> youngest = users.stream()
    .min(Comparator.comparing(User::getAge));

// toArray
String[] nameArray = users.stream()
    .map(User::getName)
    .toArray(String[]::new);
```

### 4. Collectors (수집기)

`collect()`에서 사용하는 다양한 수집 전략.

```java
// ── 기본 수집 ──
List<String> list = stream.collect(Collectors.toList());
Set<String> set = stream.collect(Collectors.toSet());
Map<Long, User> map = stream.collect(Collectors.toMap(User::getId, Function.identity()));

// ── 그룹핑 ──
// 나이대별 그룹
Map<String, List<User>> byAgeGroup = users.stream()
    .collect(Collectors.groupingBy(u -> {
        if (u.getAge() < 20) return "10대";
        if (u.getAge() < 30) return "20대";
        return "30대 이상";
    }));

// 부서별 인원 수
Map<String, Long> countByDept = users.stream()
    .collect(Collectors.groupingBy(User::getDepartment, Collectors.counting()));

// 부서별 평균 나이
Map<String, Double> avgAgeByDept = users.stream()
    .collect(Collectors.groupingBy(
        User::getDepartment,
        Collectors.averagingInt(User::getAge)
    ));

// ── 분할 ──
// 조건에 따라 true/false 그룹으로 분할
Map<Boolean, List<User>> partition = users.stream()
    .collect(Collectors.partitioningBy(u -> u.getAge() >= 20));

// ── 문자열 결합 ──
String names = users.stream()
    .map(User::getName)
    .collect(Collectors.joining(", ", "[", "]"));
// 결과: [홍길동, 김철수, 이영희]

// ── 통계 ──
IntSummaryStatistics stats = users.stream()
    .collect(Collectors.summarizingInt(User::getAge));
// stats.getAverage(), stats.getMax(), stats.getMin(), stats.getCount()

// ── 다운스트림 수집 ──
// 부서별 → 이름 목록
Map<String, List<String>> namesByDept = users.stream()
    .collect(Collectors.groupingBy(
        User::getDepartment,
        Collectors.mapping(User::getName, Collectors.toList())
    ));

// ── 불변 컬렉션 (Java 10+) ──
List<String> immutable = stream.collect(Collectors.toUnmodifiableList());
Set<String> immutableSet = stream.collect(Collectors.toUnmodifiableSet());
```

#### Collectors 요약

| Collector | 용도 | 결과 타입 |
|-----------|------|----------|
| `toList()` | 리스트 수집 | `List<T>` |
| `toSet()` | 세트 수집 | `Set<T>` |
| `toMap()` | 맵 수집 | `Map<K, V>` |
| `groupingBy()` | 그룹핑 | `Map<K, List<T>>` |
| `partitioningBy()` | true/false 분할 | `Map<Boolean, List<T>>` |
| `joining()` | 문자열 결합 | `String` |
| `counting()` | 개수 | `Long` |
| `summarizingInt()` | 통계 | `IntSummaryStatistics` |
| `mapping()` | 다운스트림 변환 | 다운스트림 타입 |

### 5. 기본형 특화 Stream

박싱/언박싱 오버헤드를 피하기 위한 기본형 전용 Stream.

```java
// IntStream, LongStream, DoubleStream
IntStream intStream = IntStream.of(1, 2, 3);
LongStream longStream = LongStream.rangeClosed(1, 100);

// 변환: 객체 Stream → 기본형 Stream
IntStream ages = users.stream()
    .mapToInt(User::getAge);

// 기본형 전용 메서드
int sum = ages.sum();
OptionalDouble avg = ages.average();
OptionalInt max = ages.max();
IntSummaryStatistics stats = ages.summaryStatistics();

// 기본형 → 객체 Stream
Stream<Integer> boxed = IntStream.range(1, 10).boxed();
```

| 메서드 | `Stream<T>` | `IntStream` |
|--------|------------|-------------|
| `sum()` | 없음 | ✅ |
| `average()` | 없음 | ✅ |
| `max()` | `Comparator` 필요 | ✅ (바로 호출) |
| `range()` | 없음 | ✅ |
| `boxed()` | 불필요 | ✅ |

### 6. 실전 예시

#### 주문 데이터 분석

```java
List<Order> orders = orderRepository.findAll();

// 1. 이번 달 총 매출
BigDecimal totalRevenue = orders.stream()
    .filter(o -> o.getOrderDate().getMonth() == LocalDate.now().getMonth())
    .map(Order::getTotalAmount)
    .reduce(BigDecimal.ZERO, BigDecimal::add);

// 2. 카테고리별 판매량 TOP 5
Map<String, Long> topCategories = orders.stream()
    .flatMap(o -> o.getItems().stream())
    .collect(Collectors.groupingBy(
        Item::getCategory,
        Collectors.counting()
    ))
    .entrySet().stream()
    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
    .limit(5)
    .collect(Collectors.toMap(
        Map.Entry::getKey,
        Map.Entry::getValue,
        (a, b) -> a,
        LinkedHashMap::new     // 순서 유지
    ));

// 3. 고객별 총 구매액 (높은 순)
List<CustomerSummary> vipCustomers = orders.stream()
    .collect(Collectors.groupingBy(
        Order::getCustomerId,
        Collectors.reducing(BigDecimal.ZERO, Order::getTotalAmount, BigDecimal::add)
    ))
    .entrySet().stream()
    .sorted(Map.Entry.<Long, BigDecimal>comparingByValue().reversed())
    .limit(10)
    .map(e -> new CustomerSummary(e.getKey(), e.getValue()))
    .toList();
```

#### DTO 변환 패턴

```java
// Entity → DTO 변환
List<UserResponse> responses = userRepository.findAll().stream()
    .map(user -> UserResponse.builder()
        .id(user.getId())
        .name(user.getName())
        .email(user.getEmail())
        .role(user.getRole().name())
        .build())
    .toList();

// 메서드 참조로 더 깔끔하게
List<UserResponse> responses = userRepository.findAll().stream()
    .map(UserResponse::from)     // static factory method
    .toList();
```

#### 중첩 데이터 처리

```java
// 부서 → 팀 → 직원 3단 중첩
List<String> allEmployeeNames = departments.stream()
    .flatMap(dept -> dept.getTeams().stream())
    .flatMap(team -> team.getMembers().stream())
    .map(Employee::getName)
    .distinct()
    .sorted()
    .toList();
```

### 7. Parallel Stream

멀티코어를 활용한 병렬 처리. 단, **항상 빠른 것은 아니다**.

```java
// 순차 → 병렬
users.parallelStream()
    .filter(User::isActive)
    .map(User::getName)
    .toList();

// 또는
users.stream().parallel()
    .filter(User::isActive)
    .toList();
```

#### 언제 써야 하는가

```
✅ 사용 적합:
  - 대용량 데이터 (수만 건 이상)
  - 각 요소 처리가 독립적 (상태 공유 없음)
  - CPU 바운드 작업 (계산 위주)
  - 데이터 소스가 분할 용이 (ArrayList, 배열)

❌ 사용 부적합:
  - 소량 데이터 (스레드 생성 오버헤드 > 이득)
  - I/O 바운드 작업 (DB, 네트워크)
  - 순서가 중요한 처리
  - 공유 상태를 수정하는 경우
  - LinkedList (분할 비용 높음)
```

#### 성능 비교

```java
// ArrayList (분할 우수) vs LinkedList (분할 불리)
List<Integer> arrayList = new ArrayList<>(IntStream.range(0, 10_000_000).boxed().toList());
List<Integer> linkedList = new LinkedList<>(arrayList);

// ArrayList: parallel이 약 3~4배 빠름
arrayList.parallelStream().reduce(0, Integer::sum);

// LinkedList: parallel이 오히려 느릴 수 있음
linkedList.parallelStream().reduce(0, Integer::sum);
```

| 데이터 소스 | 분할 용이성 | 병렬 효과 |
|------------|-----------|----------|
| `ArrayList` | 매우 좋음 | 높음 |
| `배열` | 매우 좋음 | 높음 |
| `IntStream.range` | 매우 좋음 | 높음 |
| `HashSet` | 좋음 | 보통 |
| `TreeSet` | 좋음 | 보통 |
| `LinkedList` | 나쁨 | 낮음 |
| `Stream.iterate` | 나쁨 | 낮음 |

#### 주의사항

```java
// ❌ 공유 상태 변경 (레이스 컨디션!)
List<String> results = new ArrayList<>();
users.parallelStream()
    .filter(User::isActive)
    .forEach(u -> results.add(u.getName()));  // 동시 접근 → 데이터 손실

// ✅ collect 사용 (스레드 안전)
List<String> results = users.parallelStream()
    .filter(User::isActive)
    .map(User::getName)
    .collect(Collectors.toList());             // 내부적으로 안전하게 합침
```

### 8. 성능 고려사항

```
1. 불필요한 boxing 피하기
   ❌ stream.map(x -> x * 2).reduce(0, Integer::sum)
   ✅ stream.mapToInt(x -> x * 2).sum()

2. 단순 반복은 for가 빠를 수 있다
   - 요소 10개 이하: for 루프가 빠름
   - Stream은 파이프라인 셋업 비용이 있음

3. 중간 연산 순서 최적화
   ❌ stream.sorted().filter(x -> x > 5)     // 전체 정렬 후 필터
   ✅ stream.filter(x -> x > 5).sorted()     // 필터 후 적은 수만 정렬

4. findFirst/anyMatch 활용
   - 조건에 맞는 첫 요소만 필요하면 전체를 처리하지 않음 (short-circuit)
```

### 9. Java 버전별 추가 기능

| 버전 | 기능 | 예시 |
|------|------|------|
| **Java 9** | `takeWhile`, `dropWhile` | `stream.takeWhile(n -> n < 5)` |
| **Java 9** | `Stream.ofNullable` | `Stream.ofNullable(nullableValue)` |
| **Java 9** | `iterate` 오버로드 | `Stream.iterate(0, n -> n < 10, n -> n + 1)` |
| **Java 10** | `Collectors.toUnmodifiableList` | 불변 리스트 수집 |
| **Java 12** | `Collectors.teeing` | 두 Collector 결과 합침 |
| **Java 16** | `Stream.toList()` | `.collect(Collectors.toList())` 대체 |
| **Java 16** | `mapMulti` | flatMap의 명령형 대안 |

```java
// Java 9: iterate with predicate (for 루프 대체)
Stream.iterate(0, n -> n < 100, n -> n + 1)
    .filter(n -> n % 3 == 0)
    .toList();

// Java 12: teeing (두 결과 동시 수집)
var result = users.stream().collect(Collectors.teeing(
    Collectors.counting(),                                // 총 인원
    Collectors.averagingInt(User::getAge),                // 평균 나이
    (count, avgAge) -> new TeamStats(count, avgAge)       // 결합
));

// Java 16: toList() (불변 리스트 반환)
List<String> names = users.stream()
    .map(User::getName)
    .toList();    // Collectors.toList() 대신 (더 간결, 불변)

// Java 16: mapMulti (flatMap 대안)
users.stream()
    .<String>mapMulti((user, consumer) -> {
        if (user.getAge() >= 20) {
            consumer.accept(user.getName());
            consumer.accept(user.getEmail());
        }
    })
    .toList();
```

## 참고

- [Java Stream API Documentation](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html)
- [Optional](Optional_Concept.md) — null 안전 처리
- [Functional Interface](../자바 디자인 패턴 및 원칙/Java_Functional_Interface.md) — 람다와 함수형 인터페이스
- [Collection Framework](Collection_Framework/Collection_Framework.md) — 컬렉션 기초
- [Java 동시성](../멀티스레딩 및 동시성/Java_Concurrency.md) — Parallel Stream과 동시성
