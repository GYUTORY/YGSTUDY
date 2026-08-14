---
title: Java Stream API 심화
tags: [java, language, aws]
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

**위 두 주석은 각 연산을 원본에 따로 적용했을 때의 결과지, 이 코드의 결과가 아니다.** 코드는 둘을 체이닝하고 있으므로 `dropWhile` 이 받는 입력은 원본이 아니라 `takeWhile` 이 걸러낸 `[1, 2, 3]` 이다. 실제로 실행하면 `[3]` 이 나온다.

```
takeWhile 단독 : [1, 2, 3]
dropWhile 단독 : [3, 4, 5, 1, 2]
둘을 체이닝    : [3]          ← 이 코드의 실제 결과
```

두 연산이 **정렬되지 않은 스트림에서 조건 실패 지점에 멈춘다**는 점도 자주 오해받는다. `filter` 는 전체를 훑지만 `takeWhile` 은 처음 실패한 순간 끝낸다. 위 원본의 뒤쪽 `1, 2` 는 `n < 4` 를 만족하는데도 `takeWhile` 결과에 없다 — 앞의 `4` 에서 이미 중단됐기 때문이다. 순서에 의존하는 연산이라 정렬 상태를 모르는 데이터에 쓰면 결과를 예측할 수 없다.

`peek` 에도 함정이 있다. **최종 연산이 원소를 실제로 훑지 않아도 되면 `peek` 이 아예 실행되지 않는다.**

```java
long c = Stream.of("a","b","c").peek(s -> System.out.println("peek: " + s)).count();
// 출력: 아무것도 없음. c = 3
```

`count()` 는 크기를 알 수 있으면 파이프라인을 건너뛴다. 그래서 `peek` 은 디버깅 로그 용도로만 쓰고, **부수 효과를 일으키는 실제 로직을 넣으면 안 된다.** 실행이 보장되지 않는다.

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

#### Collectors 에서 실제로 터지는 것들

`Collectors.toMap` 은 표만 보면 순한 API 같지만 **두 가지 경우에 예외를 던진다.** 둘 다 운영 데이터에서 흔하다.

```java
// 1. 키가 중복되면 예외 — 위 예제의 toMap(User::getId, identity()) 가 그대로 해당된다
List.of(new U(1,"a"), new U(1,"b")).stream()
    .collect(Collectors.toMap(U::getId, Function.identity()));
// java.lang.IllegalStateException: Duplicate key 1 (attempted merging values U@... and U@...)

// 2. 값이 null 이면 NullPointerException
Arrays.asList(new U(1, null)).stream()
    .collect(Collectors.toMap(U::getId, U::getName));
// java.lang.NullPointerException
```

키 중복은 병합 함수를 세 번째 인자로 주면 해결된다. **어느 쪽을 남길지 정하는 건 도메인 결정**이라 라이브러리가 기본값을 정해 주지 않는 것이다.

```java
Collectors.toMap(User::getId, Function.identity(), (oldV, newV) -> newV)
```

값이 `null` 인 경우는 병합 함수로도 못 막는다. `HashMap` 자체는 `null` 값을 허용하는데 `toMap` 이 내부적으로 `merge` 를 쓰기 때문에 거절된다. `null` 이 나올 수 있으면 `toMap` 전에 걸러내거나 `groupingBy` 를 쓴다 — **`groupingBy` 는 같은 데이터를 문제없이 처리한다.**

반대로 `groupingBy` 는 **키가 `null` 이면 터진다.**

```java
users.stream().collect(Collectors.groupingBy(User::getDepartment));
// 부서가 null 인 사용자가 하나라도 있으면 NullPointerException
```

정리하면 **`toMap` 은 값의 null 에, `groupingBy` 는 키의 null 에 취약하다.** 분류 기준이 선택적 필드(부서·카테고리·태그)면 기본값으로 치환하고 넘긴다.

```java
Collectors.groupingBy(u -> Optional.ofNullable(u.getDepartment()).orElse("미지정"))
```

`distinct()` 도 표의 설명대로 `equals`/`hashCode` 에 의존하는데, **재정의하지 않으면 아무것도 걸러내지 않는다.** 예외가 아니라 조용한 무동작이라 알아채기 어렵다.

```java
// P 가 equals/hashCode 를 재정의하지 않은 클래스일 때
Stream.of(new P(1), new P(1), new P(2)).distinct()   // [P1, P1, P2] — 중복이 남는다
```

기본 `equals` 는 참조 동일성이라 `new` 로 만든 두 객체는 값이 같아도 다른 것으로 본다. `record` 를 쓰면 `equals`/`hashCode` 가 자동 생성돼 이 문제가 사라진다.

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

**위 블록의 `ages` 를 네 번 쓰는 코드는 실행하면 두 번째 줄에서 죽는다.** 표에 적힌 "일회성"이 바로 이것이고, 변수에 담아 두면 재사용하고 싶어지는 게 사람 심리라 실제로 자주 걸린다.

```java
IntStream ages = users.stream().mapToInt(User::getAge);
int sum = ages.sum();              // 90 — 정상
OptionalDouble avg = ages.average();
// java.lang.IllegalStateException: stream has already been operated upon or closed
```

`sum()` 이 최종 연산이라 그 시점에 스트림이 닫힌다. 뒤의 `average()` · `max()` · `summaryStatistics()` 는 도달하지 못한다. 스트림은 컬렉션이 아니라 **한 번 흘려보내는 파이프**다.

여러 통계가 필요하면 소스에서 스트림을 매번 새로 만들거나, 한 번에 다 계산하는 `summaryStatistics()` 하나만 쓴다.

```java
// 소스에서 매번 새로 만든다
int sum = users.stream().mapToInt(User::getAge).sum();
OptionalDouble avg = users.stream().mapToInt(User::getAge).average();

// 또는 한 번 훑어 전부 얻는다 (권장 — 순회 1회)
IntSummaryStatistics stats = users.stream().mapToInt(User::getAge).summaryStatistics();
stats.getSum(); stats.getAverage(); stats.getMax(); stats.getMin(); stats.getCount();
```

아래쪽이 낫다. 위 방식은 같은 컬렉션을 두 번 순회한다.

이 성질 때문에 **메서드 파라미터나 필드로 `Stream` 을 주고받는 설계는 피한다.** 받은 쪽이 이미 소비된 스트림인지 알 방법이 없고, 두 곳에서 쓰면 한쪽이 예외를 맞는다. 재사용이 필요하면 `List` 로 받고 쓰는 쪽에서 `stream()` 을 부르게 한다.

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

"데이터 손실"이 어느 정도인지 감이 안 오면 실제로 돌려 보는 게 빠르다. 원소 100,000 개를 `parallelStream().forEach` 로 `ArrayList` 에 담은 결과다(같은 코드, 세 번 실행).

```
trial 0: size=31843   (기대: 100000)
trial 1: size=56410
trial 2: size=16998

collect(): size=100000
```

**절반 넘게 사라지는데 예외는 하나도 안 난다.** 실행할 때마다 결과가 달라지는 것도 중요하다. 재현이 안 되니 테스트로 잡히지 않고, 운영에서 "가끔 데이터가 빈다"는 형태로 나타난다.

`ArrayList.add` 는 내부 배열 크기 확장과 인덱스 증가가 원자적이지 않아서 여러 스레드가 같은 칸에 쓰거나 크기 갱신을 덮어쓴다. 같은 코드를 40회 반복하면 손실 외에 다른 증상도 함께 나온다.

```
40회 실행 → 예외 발생 4회, 결과에 null 원소가 섞인 실행 35회
```

즉 **원소가 사라지는 것보다 `null` 이 끼어드는 쪽이 훨씬 흔하다.** 그 `null` 은 한참 뒤 다른 코드에서 `NullPointerException` 으로 터지므로 원인 지점과 증상 지점이 멀어진다.

`Collections.synchronizedList` 로 감싸면 손실은 막히지만 매 `add` 마다 락을 잡느라 **병렬로 만든 이득이 사라진다.** `collect` 는 스레드마다 별도 컨테이너에 모은 뒤 합치는 방식이라 락 경합이 없다. 병렬 스트림에서 결과를 모으는 정답은 언제나 `collect` 다.

같은 이유로 `forEach` 는 병렬에서 **순서를 보장하지 않는다.**

```java
IntStream.range(0,8).parallel().forEach(sb::append);         // 5460273  — 실행마다 다름
IntStream.range(0,8).parallel().forEachOrdered(sb2::append); // 01234567 — 원본 순서
IntStream.range(0,8).parallel().mapToObj(String::valueOf)
                    .collect(Collectors.toList());           // [0..7]   — collect 는 순서 유지
```

`collect` 가 순서까지 지켜 준다는 점이 중요하다. **순서와 스레드 안전을 동시에 원하면 `collect` 하나로 해결된다.** `forEachOrdered` 는 순서를 위해 다시 직렬화하므로 병렬의 이득 상당 부분을 반납한다.

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
- [Functional Interface](../자바%20디자인%20패턴%20및%20원칙/Java_Functional_Interface.md) — 람다와 함수형 인터페이스
- [Collection Framework](Collection_Framework/Collection_Framework.md) — 컬렉션 기초
- [Java 동시성](../멀티스레딩%20및%20동시성/Java_Concurrency.md) — Parallel Stream과 동시성
