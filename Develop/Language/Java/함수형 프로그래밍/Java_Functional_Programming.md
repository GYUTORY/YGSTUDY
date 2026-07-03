---
title: Java 함수형 프로그래밍 - Stream, Optional, Collectors
tags: [java, functional-programming, stream, optional, collectors, parallel-stream, lazy-evaluation]
updated: 2026-06-15
---

# Java 함수형 프로그래밍 - Stream, Optional, Collectors

순수 함수, 불변성, 고차 함수, 합성, 모나드 같은 일반 개념은 [[Functional_Programming]]에서 다룬다. JavaScript/Node 런타임에서 함수형 스타일이 어떻게 동작하고 깨지는지는 [[Functional_Programming_Advanced]]를 본다. 이 문서는 Java에서 함수형 스타일을 실제로 굴리는 세 축, Stream API·Optional·Collectors를 실무에서 마주치는 문제 위주로 정리한다.

`Function`, `Supplier`, `Predicate` 같은 함수형 인터페이스 자체는 [[Java_Functional_Interface]]에서 다룬다. 람다와 함수형 인터페이스는 문법 토대일 뿐이고, 그걸 실제로 어디에 쓰느냐가 Stream과 Optional이다. 람다를 배웠는데 `map`, `filter`만 쓰고 끝난다면 함수형 인터페이스의 절반밖에 안 쓰는 셈이다.

## Stream은 지연 평가된다

Stream에서 제일 먼저 막히는 지점이 이거다. 중간 연산(intermediate operation)은 호출해도 아무 일도 안 일어난다. 최종 연산(terminal operation)이 붙는 순간에야 파이프라인 전체가 한 번 돈다.

```java
Stream<String> s = Stream.of("a", "bb", "ccc")
        .filter(x -> {
            System.out.println("filter: " + x);
            return x.length() > 1;
        })
        .map(x -> {
            System.out.println("map: " + x);
            return x.toUpperCase();
        });

System.out.println("아직 아무것도 안 찍힘");
List<String> result = s.collect(Collectors.toList());  // 여기서부터 출력 시작
```

`collect`를 호출하기 전까지 `filter`, `map` 안의 `println`은 한 줄도 안 찍힌다. 이걸 모르면 "왜 로그가 안 나오지" 하면서 시간을 버린다.

지연 평가 때문에 생기는 실용적인 결과가 두 가지 있다.

첫째, 원소 단위로 파이프라인을 통과한다(loop fusion). `filter` 전체를 돌고 나서 `map` 전체를 도는 게 아니라, `"bb"` 하나가 `filter` → `map`을 거치고 나서 `"ccc"`가 들어간다. 위 코드의 출력 순서를 보면 `filter: a`, `filter: bb`, `map: bb`, `filter: ccc`, `map: ccc` 순이다. 중간 단계마다 임시 리스트가 안 생기니까 메모리에 유리하다.

둘째, `findFirst`나 `anyMatch` 같은 short-circuit 연산은 조건을 만족하는 순간 멈춘다.

```java
Optional<String> first = Stream.of("a", "bb", "ccc", "dddd")
        .filter(x -> x.length() > 1)
        .findFirst();   // "bb"를 찾는 순간 "ccc", "dddd"는 건드리지도 않음
```

이 특성 덕분에 무한 스트림에 `limit`이나 `findFirst`를 걸어도 끝난다(아래에서 다룬다).

## Stream은 한 번 쓰면 끝이다

Stream은 재사용이 안 된다. 최종 연산을 한 번 호출한 Stream에 또 최종 연산을 걸면 `IllegalStateException: stream has already been operated upon or closed`가 터진다.

```java
Stream<String> s = Stream.of("a", "b", "c");
long count = s.count();          // 최종 연산 1회
List<String> list = s.collect(Collectors.toList());  // IllegalStateException
```

실무에서 이 예외를 만나는 전형적인 패턴은 Stream을 필드나 변수에 담아서 돌려쓰려는 경우다.

```java
// 안티패턴: Stream을 캐싱하려는 시도
private final Stream<Order> orderStream = loadOrders().stream();

public long countPending() {
    return orderStream.filter(o -> o.isPending()).count();  // 두 번째 호출에서 터짐
}
```

Stream은 데이터를 담는 컬렉션이 아니라 "한 번 흘려보내는 파이프"다. 재사용이 필요하면 `Supplier<Stream<T>>`로 매번 새로 만들거나, 그냥 원본 컬렉션(`List`)을 들고 있다가 필요할 때 `.stream()`을 호출한다.

```java
Supplier<Stream<String>> streamSupplier = () -> Stream.of("a", "bb", "ccc");
long c1 = streamSupplier.get().count();
long c2 = streamSupplier.get().filter(x -> x.length() > 1).count();  // 새 스트림이라 OK
```

## peek는 디버깅용으로 믿으면 안 된다

`peek`은 각 원소가 흘러갈 때 부수효과(주로 로깅)를 넣으라고 만든 중간 연산이다. 그런데 두 가지 함정이 있다.

하나는 최종 연산이 없으면 `peek`도 실행이 안 된다는 점이다. 지연 평가 규칙을 그대로 따른다.

```java
Stream.of("a", "b", "c").peek(System.out::println);  // 아무것도 안 찍힘. 최종 연산이 없음
```

다른 하나가 더 까다롭다. JIT이 최종 연산 결과에 영향을 안 주는 중간 연산을 최적화로 건너뛸 수 있다. `count()`는 Java 9부터 소스 크기를 알 수 있으면 원소를 실제로 순회하지 않는다. 그래서 `count` 앞에 `peek`을 걸면 `peek`이 한 번도 실행 안 되는 경우가 있다.

```java
long n = Stream.of("a", "b", "c")
        .peek(System.out::println)   // Java 9+에서 안 찍힐 수 있음
        .count();
```

중간에 `filter`가 끼면 크기를 미리 알 수 없으니 다시 `peek`이 돈다. 동작이 JVM 버전과 파이프라인 구성에 따라 달라진다는 게 문제다. `peek`은 개발 중 임시 확인용으로만 쓰고, 운영 코드에 로깅 목적으로 남기지 않는다. 로깅이 필요하면 `map` 안에서 로그를 찍고 원소를 그대로 반환하는 쪽이 차라리 예측 가능하다.

## 무한 스트림은 limit이나 short-circuit으로만 끝낸다

`Stream.generate`와 `Stream.iterate`는 무한 스트림을 만든다. 지연 평가라서 무한해도 문제가 안 되지만, 반드시 끝을 잘라줘야 한다.

```java
// generate: 인자 없는 Supplier로 같은 종류 값을 계속 생성
List<UUID> ids = Stream.generate(UUID::randomUUID)
        .limit(5)
        .collect(Collectors.toList());

// iterate: 이전 값으로 다음 값을 계산
List<Integer> powers = Stream.iterate(1, x -> x * 2)
        .limit(10)
        .collect(Collectors.toList());   // 1, 2, 4, 8, ...
```

`limit`을 빼먹으면 그대로 무한 루프다. `collect`나 `forEach` 같은 끝까지 다 돌아야 하는 최종 연산은 영영 안 끝난다. 반면 `findFirst`, `anyMatch` 같은 short-circuit 연산은 무한 스트림이어도 멈춘다.

Java 9부터는 종료 조건을 받는 `iterate` 오버로드가 있어서 `for` 루프처럼 쓸 수 있다.

```java
// Java 9+: predicate가 false가 되면 끝
List<Integer> nums = Stream.iterate(1, x -> x <= 100, x -> x * 2)
        .collect(Collectors.toList());
```

실무에서 `generate`로 무한 스트림을 만들 때 주의할 점이 있다. Supplier가 부수효과를 가지면(예: 큐에서 메시지를 꺼내는 경우) 병렬 스트림에서 순서가 깨지고 예측 불가능해진다. 무한 스트림은 순차로만 쓰는 게 안전하다.

## Optional을 Maybe 모나드로 본다

`Optional<T>`는 "값이 있을 수도, 없을 수도 있는 컨테이너"다. 함수형 언어의 `Maybe`/`Option` 모나드와 같은 발상이다. 핵심은 `Optional`을 꺼내서 `if`로 검사하는 게 아니라, 컨테이너 안에서 변환을 체이닝하는 거다.

`isPresent()` + `get()` 조합은 `Optional`을 쓰는 의미가 거의 없다. null 체크를 이름만 바꾼 꼴이다.

```java
// 안티패턴: Optional을 null 체크처럼 사용
Optional<User> opt = findUser(id);
if (opt.isPresent()) {
    User u = opt.get();
    return u.getEmail();
}
return "unknown";
```

`map`과 `orElse` 계열로 체이닝하면 분기 없이 한 흐름으로 표현된다.

```java
String email = findUser(id)
        .map(User::getEmail)
        .orElse("unknown");
```

### map과 flatMap을 구분한다

`map`은 일반 값을 반환하는 함수를, `flatMap`은 `Optional`을 반환하는 함수를 받는다. 이걸 헷갈리면 `Optional<Optional<T>>`라는 중첩이 생긴다.

```java
// getAddress()가 Optional<Address>를 반환한다고 하자
Optional<Optional<Address>> wrong = findUser(id).map(User::getAddress);   // 중첩됨
Optional<Address> right = findUser(id).flatMap(User::getAddress);          // 평탄화됨

String city = findUser(id)
        .flatMap(User::getAddress)   // Optional<Address>
        .map(Address::getCity)       // 일반 String 반환 → map
        .orElse("미지정");
```

### orElse와 orElseGet의 차이가 버그를 만든다

`orElse(T)`는 인자를 항상 평가한다. `orElseGet(Supplier)`는 값이 없을 때만 Supplier를 호출한다. 기본값을 만드는 비용이 클 때 `orElse`를 쓰면 값이 있어도 매번 그 비용을 치른다.

```java
// loadDefaultFromDb()가 DB를 친다고 하자
User u1 = findUser(id).orElse(loadDefaultFromDb());      // 값이 있어도 DB를 항상 호출
User u2 = findUser(id).orElseGet(() -> loadDefaultFromDb());  // 값이 없을 때만 호출
```

`orElse(new ArrayList<>())`처럼 가벼운 상수면 `orElse`가 읽기 편하다. 부수효과가 있거나 비용이 큰 경우만 `orElseGet`을 쓴다. 실제로 운영에서 `orElse(repository.findDefault())` 같은 코드가 캐시 히트율을 떨어뜨리는 걸 본 적이 있다. 값이 멀쩡히 있는데도 매 호출마다 default를 조회하고 있었다.

값이 없을 때 예외를 던져야 하면 `orElseThrow`를 쓴다.

```java
User u = findUser(id)
        .orElseThrow(() -> new UserNotFoundException(id));
```

### Optional을 쓰지 말아야 할 곳

`Optional`은 메서드 반환 타입 용도다. 필드, 메서드 파라미터, 컬렉션 원소 타입으로는 쓰지 않는다. `Optional`은 직렬화가 안 되고(`Serializable` 미구현), 필드로 쓰면 객체마다 래퍼 하나가 더 붙어 메모리를 먹는다. `List<Optional<String>>` 같은 건 그냥 빈 값을 거른 `List<String>`으로 만드는 게 맞다.

## Collectors로 집계한다

`collect`는 Stream의 최종 결과를 어떻게 모을지 `Collector`로 받는다. `toList`, `toSet`, `toMap`이 기본이고, 집계는 `groupingBy`가 주력이다.

### groupingBy

SQL의 `GROUP BY`와 같다. 분류 함수로 키를 뽑아 `Map<K, List<V>>`를 만든다.

```java
Map<Department, List<Employee>> byDept = employees.stream()
        .collect(Collectors.groupingBy(Employee::getDepartment));
```

두 번째 인자로 downstream collector를 넣으면 그룹별로 다시 집계한다. 부서별 인원 수, 부서별 평균 급여 같은 게 한 줄로 나온다.

```java
Map<Department, Long> countByDept = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                Collectors.counting()));

Map<Department, Double> avgSalary = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                Collectors.averagingDouble(Employee::getSalary)));
```

`groupingBy`의 함정 하나. 분류 함수가 `null`을 반환하면 `NullPointerException`이 터진다. `TreeMap`을 쓰는 `groupingBy`라면 키 정렬 중에 null이 들어가서 깨진다. 키가 될 값이 nullable이면 분류 함수 안에서 기본값으로 치환하거나 미리 걸러낸다.

### partitioningBy

`Predicate`로 `true`/`false` 두 그룹으로 나눈다. `groupingBy`로도 되지만, `partitioningBy`는 `false` 그룹이 비어도 키가 항상 존재한다는 게 다르다.

```java
Map<Boolean, List<Employee>> partitioned = employees.stream()
        .collect(Collectors.partitioningBy(e -> e.getSalary() > 5000));

List<Employee> highPaid = partitioned.get(true);
List<Employee> rest = partitioned.get(false);   // 항상 존재. 비어 있어도 null 아님
```

`groupingBy(e -> e.getSalary() > 5000)`로 하면 한쪽 그룹에 원소가 하나도 없을 때 그 키가 Map에 없어서 `get(false)`가 `null`을 준다. boolean 분류라면 `partitioningBy`가 안전하다.

### teeing

Java 12부터 들어온 `teeing`은 같은 스트림을 두 collector에 동시에 흘리고 결과를 합친다. 한 번 순회로 최솟값과 최댓값을 같이 구하거나, 합과 개수로 평균을 직접 계산하는 데 쓴다.

```java
// 합과 개수를 한 번에 모아서 평균 계산
record Stats(double sum, long count, double avg) {}

Stats stats = employees.stream()
        .collect(Collectors.teeing(
                Collectors.summingDouble(Employee::getSalary),
                Collectors.counting(),
                (sum, count) -> new Stats(sum, count, count == 0 ? 0 : sum / count)));
```

스트림을 두 번 돌지 않고 한 번에 두 통계를 뽑아야 할 때 유용하다. 다만 merger 함수에서 0 나눗셈 같은 경계 처리를 직접 해야 한다.

### toMap의 키 충돌

`toMap`은 키가 중복되면 `IllegalStateException: Duplicate key`를 던진다. 데이터에 중복이 있을 수 있으면 세 번째 인자로 merge 함수를 반드시 넣는다.

```java
// 중복 키 처리 안 하면 데이터에 같은 email이 둘 있는 순간 터짐
Map<String, User> byEmail = users.stream()
        .collect(Collectors.toMap(
                User::getEmail,
                u -> u,
                (existing, replacement) -> existing));   // 충돌 시 기존 값 유지
```

운영 데이터는 거의 항상 어딘가에 중복이 있다. `toMap`을 쓸 때는 merge 함수를 기본으로 넣는 습관을 들이는 게 낫다.

## 병렬 스트림의 함정

`stream()`을 `parallelStream()`으로 바꾸거나 `.parallel()`을 붙이면 ForkJoinPool로 작업이 쪼개져 돌아간다. 한 줄 바꿔서 성능이 오를 것 같지만, 실무에서는 손해 보는 경우가 더 많다. 몇 가지를 짚는다.

### 공유 상태를 건드리면 깨진다

병렬 스트림의 람다 안에서 외부 가변 상태를 건드리면 race condition이 생긴다. `forEach`로 일반 `ArrayList`에 `add` 하는 게 대표적인 실수다.

```java
// 안티패턴: 병렬 스트림에서 공유 컬렉션에 add
List<Integer> result = new ArrayList<>();
IntStream.range(0, 10000).parallel()
        .forEach(result::add);   // ArrayList는 thread-safe 아님. 누락/예외 발생
```

`ArrayList`는 동기화가 안 되니까 원소가 누락되거나 `ArrayIndexOutOfBoundsException`이 튀어나온다. 결과를 모을 때는 `collect`를 쓴다. `Collector`는 병렬 처리에서 부분 결과를 안전하게 합치도록(combiner) 설계돼 있다.

```java
List<Integer> result = IntStream.range(0, 10000).parallel()
        .boxed()
        .collect(Collectors.toList());   // 이건 병렬에서도 안전
```

### 공용 ForkJoinPool을 점유한다

병렬 스트림은 기본적으로 `ForkJoinPool.commonPool()`을 쓴다. JVM 하나에 공용 풀이 하나뿐이고 크기는 보통 `CPU 코어 수 - 1`이다. 여기서 블로킹 작업(DB 호출, HTTP 호출)을 병렬 스트림으로 돌리면 공용 풀의 스레드를 다 잡아먹는다. 그러면 같은 JVM의 다른 병렬 스트림, `CompletableFuture` 기본 실행도 같이 굶는다.

```java
// 위험: 블로킹 I/O를 공용 풀에서 병렬로
List<Response> responses = urls.parallelStream()
        .map(url -> httpClient.get(url))   // 각 호출이 수백 ms 블로킹
        .collect(Collectors.toList());     // 공용 풀이 이 작업에 묶임
```

병렬 스트림은 CPU 바운드 작업, 그것도 원소가 충분히 많을 때만 의미가 있다. I/O 바운드는 `CompletableFuture`에 전용 `ExecutorService`를 줘서 처리하는 게 맞다. 굳이 병렬 스트림을 전용 풀에서 돌리고 싶으면 `ForkJoinPool`을 직접 만들어 `submit` 안에서 실행하는 우회법이 있긴 하지만, 그 시점이면 그냥 다른 도구를 쓰는 게 낫다.

### 박싱 비용과 자료구조

병렬화가 이득을 보려면 스트림을 균등하게 쪼갤 수 있어야 한다(splittable). `ArrayList`나 배열은 인덱스로 반씩 자르기 쉽지만, `LinkedList`는 순회해야 자를 수 있어서 병렬화 이득이 거의 없다. 데이터 양이 적으면 작업을 쪼개고 합치는 오버헤드가 병렬 처리 이득보다 커서 순차보다 느려진다.

기본형 박싱도 비용이다. `Stream<Integer>`로 정수를 다루면 원소마다 `Integer` 객체가 생긴다. 박싱/언박싱과 GC 부담이 누적된다. 정수, 실수 연산은 `IntStream`, `LongStream`, `DoubleStream` 같은 기본형 특화 스트림을 쓴다.

```java
// 박싱 발생
int sum1 = numbers.stream()
        .filter(n -> n > 0)
        .reduce(0, Integer::sum);   // Integer 박싱/언박싱 반복

// 기본형 스트림
int sum2 = numbers.stream()
        .mapToInt(Integer::intValue)   // IntStream으로 전환
        .filter(n -> n > 0)
        .sum();
```

`mapToInt`, `mapToLong`, `mapToDouble`로 기본형 스트림으로 내려보내면 `sum()`, `average()`, `summaryStatistics()` 같은 전용 집계도 쓸 수 있다.

정리하면 병렬 스트림은 "원소가 수만 개 이상, CPU 바운드, splittable한 자료구조, 공유 상태 없음" 조건이 모두 맞을 때만 켠다. 하나라도 어긋나면 `parallel()`을 빼는 게 거의 항상 옳다. 성능이 의심되면 추측하지 말고 `parallel()` 있고 없고를 실제 데이터로 측정해서 비교한다.

## 관련 문서

- 함수형 일반 개념(순수 함수, 합성, 모나드): [[Functional_Programming]]
- JavaScript/Node 함수형 스타일: [[Functional_Programming_Advanced]]
- 함수형 인터페이스(`Function`, `Supplier`, `Predicate` 등): [[Java_Functional_Interface]]
