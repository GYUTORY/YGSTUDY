---
title: "원시 타입과 래퍼 클래스"
tags: [java, language]
updated: 2026-05-03
---

# 원시 타입과 래퍼 클래스

## 원시 타입 8종

Java의 원시 타입은 객체가 아니라 값 자체를 스택에 저장한다.

| 타입 | 크기 | 기본값 | 범위 |
|------|------|--------|------|
| `byte` | 1byte | 0 | -128 ~ 127 |
| `short` | 2byte | 0 | -32,768 ~ 32,767 |
| `int` | 4byte | 0 | 약 -21억 ~ 21억 |
| `long` | 8byte | 0L | 약 -922경 ~ 922경 |
| `float` | 4byte | 0.0f | IEEE 754 단정밀도 |
| `double` | 8byte | 0.0d | IEEE 754 배정밀도 |
| `char` | 2byte | '\u0000' | 0 ~ 65,535 |
| `boolean` | JVM 구현에 따라 다름 | false | true / false |

`boolean`의 실제 크기는 JVM 스펙에 정의되어 있지 않다. HotSpot에서는 내부적으로 1byte를 쓰지만, 배열에서는 1byte, 단독 필드에서는 4byte(int로 처리)인 경우도 있다.

## 래퍼 클래스

각 원시 타입에 대응하는 래퍼 클래스가 있다.

| 원시 타입 | 래퍼 클래스 |
|-----------|-------------|
| `byte` | `Byte` |
| `short` | `Short` |
| `int` | `Integer` |
| `long` | `Long` |
| `float` | `Float` |
| `double` | `Double` |
| `char` | `Character` |
| `boolean` | `Boolean` |

래퍼 클래스는 힙에 객체로 생성된다. 원시 타입보다 메모리를 더 쓰고, GC 대상이 된다.

## 오토박싱과 언박싱

Java 5부터 컴파일러가 원시 타입과 래퍼 사이의 변환을 자동으로 넣어준다.

```java
// 오토박싱: int → Integer
Integer a = 10; // 컴파일러가 Integer.valueOf(10)으로 변환

// 언박싱: Integer → int
int b = a; // 컴파일러가 a.intValue()로 변환
```

바이트코드를 확인하면 실제로 `Integer.valueOf()`와 `intValue()`가 호출되는 걸 볼 수 있다.

### 바이트코드 레벨에서의 박싱/언박싱

`javap -c`로 디스어셈블해보면 박싱이 어떻게 일어나는지 정확히 보인다.

```java
public int sum(Integer a, int b) {
    Integer result = a + b;
    return result;
}
```

위 코드의 바이트코드는 다음과 같이 생긴다.

```
0: aload_1                                      // a 참조 로드
1: invokevirtual Integer.intValue:()I           // a 언박싱
4: iload_2                                      // b 로드
5: iadd                                         // 정수 덧셈
6: invokestatic  Integer.valueOf:(I)LInteger;   // 결과 박싱
9: astore_3                                     // result 저장
10: aload_3
11: invokevirtual Integer.intValue:()I          // 반환을 위한 언박싱
14: ireturn
```

`Integer.valueOf()`는 `invokestatic`으로 호출된다. 정적 메서드 호출이라 가상 호출 오버헤드는 없지만, 캐시 범위 밖이면 매번 `new Integer(int)`로 객체를 생성한다. `intValue()`는 `invokevirtual`이라 가상 메서드 디스패치를 거치는데, JIT이 인라이닝하면 거의 비용이 사라진다.

이 흐름을 이해하면 반복문 안에서 박싱이 왜 그렇게 비싼지 명확해진다. 매 반복마다 객체가 새로 만들어지고, 곧바로 GC 대상이 된다.

### 언박싱 시 NullPointerException

래퍼 타입이 `null`일 때 언박싱하면 NPE가 발생한다. 이건 실무에서 자주 만나는 문제다.

```java
Integer count = null;
int result = count; // NullPointerException 발생
```

DB에서 nullable 컬럼을 조회할 때 흔히 발생한다.

```java
// MyBatis나 JPA에서 nullable int 컬럼을 조회할 때
public class Order {
    private int quantity; // DB에 NULL이 들어있으면 NPE
}

// 이렇게 해야 한다
public class Order {
    private Integer quantity; // nullable 컬럼은 래퍼 타입으로 받아야 한다
}
```

삼항 연산자에서도 예상 못한 언박싱이 일어난다.

```java
Integer a = null;
Integer b = (a != null) ? a : 0;
// 문제없어 보이지만, 오른쪽이 int 리터럴이라서
// 컴파일러가 전체를 int로 추론 → a를 언박싱 시도 → NPE
// 실제로는 조건이 false이므로 0이 반환되어 이 경우엔 괜찮지만,
// 아래처럼 조건이 true일 때 문제가 된다

Boolean flag = null;
boolean result = (flag != null) ? flag : false;
// flag가 null이 아닌 경우에도 문제없지만,
// 타입 추론 자체가 boolean이라서 flag가 null이면 NPE

// 안전한 방법
Integer a = null;
Integer b = (a != null) ? a : Integer.valueOf(0);
```

## parseInt vs valueOf

문자열을 숫자로 바꿀 때 `Integer.parseInt()`와 `Integer.valueOf()` 두 가지가 있는데, 반환 타입이 다르다.

```java
int a = Integer.parseInt("123");      // 원시 int 반환
Integer b = Integer.valueOf("123");   // Integer 객체 반환 (캐시 적용)
```

내부 구현을 보면 `valueOf(String)`은 결국 `parseInt(String)`을 호출한 뒤 `valueOf(int)`로 박싱한다. 캐시 범위에 해당하면 캐시된 객체를, 그 외에는 새 객체를 만든다.

원시 타입이 필요한 자리에는 `parseInt`를 쓰는 게 맞다. 굳이 박싱했다가 다시 언박싱하는 비용을 피할 수 있다. 반대로 컬렉션이나 제네릭에 넣을 거면 `valueOf`가 자연스럽다.

### 파싱 실패 시 예외

둘 다 파싱 실패 시 `NumberFormatException`을 던진다. 이걸 그냥 던져버리면 사용자 입력 처리 시 예상치 못한 곳에서 500 에러가 나간다.

```java
// 잘못된 입력 처리
public Long getProductId(String idParam) {
    return Long.parseLong(idParam); // "abc" → NumberFormatException
}

// 검증을 우선 하거나 try-catch로 감싸야 한다
public Optional<Long> getProductId(String idParam) {
    try {
        return Optional.of(Long.parseLong(idParam));
    } catch (NumberFormatException e) {
        return Optional.empty();
    }
}
```

### 오버플로우

`Integer.parseInt`는 int 범위를 넘으면 `NumberFormatException`을 던진다. 메시지가 "For input string: ..."으로 나가서 오버플로우인지 잘못된 문자인지 구분이 어렵다.

```java
Integer.parseInt("99999999999"); // NumberFormatException: For input string: "99999999999"
Integer.parseInt("21474836480"); // 같은 예외, 메시지로는 구분 불가
```

확실히 큰 숫자면 처음부터 `Long.parseLong`을 쓴다.

### parseUnsignedInt

unsigned 정수가 들어오는 외부 시스템(C/C++로 작성된 레거시, 네트워크 패킷)과 통신할 때 `Integer.parseUnsignedInt`가 유용하다.

```java
int signed = Integer.parseInt("4294967295");          // NumberFormatException
int unsigned = Integer.parseUnsignedInt("4294967295"); // -1로 저장됨

// 출력할 때 unsigned로 변환
System.out.println(Integer.toUnsignedString(unsigned)); // "4294967295"
```

내부적으로는 그냥 `int`(32비트)에 저장되지만, 0xFFFFFFFF 같은 비트 패턴을 다룰 수 있게 해준다. 산술 연산을 할 거면 `Integer.toUnsignedLong`으로 long으로 올려서 처리하는 게 안전하다.

## Integer 캐시 함정

`Integer.valueOf()`는 -128에서 127 사이의 값을 캐시한다. 이 범위 안의 값은 같은 객체를 반환한다.

```java
Integer a = 127;
Integer b = 127;
System.out.println(a == b); // true (같은 캐시 객체)

Integer c = 128;
Integer d = 128;
System.out.println(c == d); // false (다른 객체)
```

이게 버그의 원인이 되는 이유는, 테스트에서 작은 값으로 확인했을 때는 `==`가 잘 동작하다가 운영에서 큰 값이 들어오면 갑자기 실패하기 때문이다.

```java
// 이런 코드가 테스트는 통과하고 운영에서 터진다
public boolean isSameProduct(Integer productId1, Integer productId2) {
    return productId1 == productId2; // 128 이상이면 false
}

// 반드시 equals를 써야 한다
public boolean isSameProduct(Integer productId1, Integer productId2) {
    return Objects.equals(productId1, productId2);
}
```

캐시 범위는 JVM 옵션 `-XX:AutoBoxCacheMax`로 변경할 수 있지만, 이걸 건드리는 건 좋은 생각이 아니다. 근본적으로 래퍼 타입끼리 `==`로 비교하지 않는 게 맞다.

### Long, Short, Byte, Character도 캐시한다

`Long.valueOf()`, `Short.valueOf()`, `Byte.valueOf()`도 -128~127 범위를 캐시한다. `Character.valueOf()`는 0~127을 캐시한다. `Float`과 `Double`은 캐시하지 않는다.

```java
Long a = 127L;
Long b = 127L;
System.out.println(a == b); // true

Long c = 128L;
Long d = 128L;
System.out.println(c == d); // false
```

## == vs equals 정리

```java
int a = 100;
int b = 100;
a == b; // true (값 비교)

Integer c = 100;
Integer d = 100;
c == d;      // true (캐시 범위라서 같은 객체)
c.equals(d); // true (값 비교)

Integer e = 200;
Integer f = 200;
e == f;      // false (캐시 범위 밖이라 다른 객체)
e.equals(f); // true (값 비교)

int g = 200;
Integer h = 200;
g == h; // true (h가 언박싱되어 값 비교)
```

규칙은 단순하다.

- 원시 타입끼리 비교: `==` 사용
- 래퍼 타입끼리 비교: `equals()` 사용
- 원시 타입과 래퍼 비교: `==` 가능 (언박싱 발생), 단 래퍼가 null이면 NPE

실무에서는 `Objects.equals()`를 쓰는 게 안전하다. null-safe하기 때문이다.

## 부동소수점 박싱의 함정

`Float`, `Double`은 캐시도 없고, 비교도 까다롭다. 특히 `NaN`은 동작이 직관적이지 않다.

```java
double a = Double.NaN;
double b = Double.NaN;

System.out.println(a == b);        // false (IEEE 754 규약: NaN끼리 비교는 항상 false)
System.out.println(Double.compare(a, b)); // 0 (NaN끼리는 같다고 판단)

Double x = Double.NaN;
Double y = Double.NaN;
System.out.println(x.equals(y));   // true (Double.equals는 NaN을 같다고 본다)
System.out.println(x == y);        // false (다른 객체)
```

`==`와 `equals`가 NaN에 대해 다른 결과를 낸다. 이건 IEEE 754 규약과 자바 객체 비교 규약이 충돌하기 때문에 생기는 문제다.

`TreeMap`의 키로 `Double`을 쓸 때 NaN이 들어가면 `compareTo`가 0을 반환하지만 `==`로는 false라서, 동등성 추론이 깨진다. 일반적으로 부동소수점은 정확한 비교 자체가 부적절하다.

```java
// 안전하지 않음
if (price == 0.1 + 0.2) { ... } // false (0.30000000000000004)

// 허용 오차로 비교
if (Math.abs(price - 0.3) < 1e-9) { ... }

// 정렬 같은 곳에서는 Double.compare 사용
list.sort(Double::compare);
```

금액 계산처럼 정밀도가 중요하면 `BigDecimal`을 써야 한다. `double`로 합계를 내면 누적 오차가 쌓인다.

## Stream API에서의 박싱 비용

`Stream<Integer>`와 `IntStream`은 동작 방식이 완전히 다르다. 전자는 매 연산마다 박싱된 객체를 다루고, 후자는 원시 int 배열을 다룬다.

```java
// 박싱 발생 - Stream<Integer>
int sum1 = list.stream()
    .filter(i -> i > 100)
    .mapToInt(Integer::intValue)  // 여기서 언박싱
    .sum();

// 박싱 최소화 - IntStream
int sum2 = IntStream.range(0, 1_000_000)
    .filter(i -> i > 100)
    .sum();
```

`Stream<Integer>`는 모든 요소가 `Integer` 객체로 박싱되어 있다. `IntStream`은 내부적으로 int 배열로 동작하니 메모리도 적게 쓰고 SIMD 최적화도 가능하다.

### boxed()와 mapToInt()의 변환 비용

원시 스트림과 객체 스트림 사이 변환은 비용이 든다.

```java
// IntStream → Stream<Integer>: 모든 요소를 박싱
List<Integer> list = IntStream.range(0, 1_000_000)
    .boxed()  // 1_000_000번 박싱
    .toList();

// Stream<Integer> → IntStream: 모든 요소를 언박싱
int sum = list.stream()
    .mapToInt(Integer::intValue)  // 1_000_000번 언박싱
    .sum();
```

큰 데이터 처리에서 이 변환을 반복하면 GC가 심하게 일어난다. 한 번 원시 스트림으로 시작했으면 가능한 한 끝까지 원시 스트림으로 끌고 가는 게 맞다.

집계가 목적이면 `IntStream.sum()`, `IntStream.average()`, `IntStream.summaryStatistics()`를 쓴다. `Stream<Integer>.reduce(0, Integer::sum)`는 매 단계마다 박싱이 생긴다.

```java
// 박싱 발생
int sum = list.stream().reduce(0, Integer::sum);

// 박싱 없음
int sum = list.stream().mapToInt(Integer::intValue).sum();
```

## 컬렉션의 박싱 비용

`HashMap<Integer, ...>`, `HashSet<Integer>`처럼 래퍼를 키로 쓰면 모든 키가 박싱된다. 1000만 건 정도 들어가면 차이가 체감된다.

```java
// Integer 키: 키마다 16byte + Map.Entry 객체
Map<Integer, String> map = new HashMap<>();
for (int i = 0; i < 10_000_000; i++) {
    map.put(i, "value"); // 매 put마다 i 박싱
}

// get/containsKey도 마찬가지로 박싱이 일어난다
map.containsKey(123); // 123이 Integer로 박싱됨
```

이런 워크로드가 자주 등장하면 원시 타입 컬렉션을 쓰는 게 맞다.

- **Eclipse Collections**: `IntObjectHashMap`, `IntHashSet`, `IntArrayList` 같은 원시 타입 전용 컬렉션 제공
- **Trove**: `TIntObjectHashMap`, `TIntHashSet` (오래된 라이브러리지만 여전히 안정적)
- **HPPC** (High Performance Primitive Collections): 카르후나가 만든 원시 타입 컬렉션
- **fastutil**: Lucene/Elasticsearch에서 쓰는 원시 타입 컬렉션 라이브러리

```java
// Eclipse Collections 예시
IntObjectHashMap<String> map = new IntObjectHashMap<>();
map.put(1, "a"); // 박싱 없음
map.put(2, "b");
String value = map.get(1); // 박싱 없음
```

메모리는 절반 이하로 줄고, 캐시 적중률도 좋아진다. 다만 표준 `Map` 인터페이스를 따르지 않으니 외부 API에 노출하기에는 적합하지 않다. 내부 자료구조로만 쓰는 게 맞다.

## 동시성 환경에서의 대안

여러 스레드가 같은 카운터를 증가시키는 상황에서 `Integer`는 쓸 수 없다. 불변 객체라서 매번 새 객체로 교체해야 하고, 그 교체 자체가 원자적이지 않다.

```java
// 잘못된 코드 - race condition
private Integer counter = 0;
public void increment() {
    counter++; // 읽기 → 더하기 → 쓰기, 원자적이지 않음
}
```

이런 경우 `AtomicInteger`, `AtomicLong`을 쓴다. 내부적으로 CAS(Compare-And-Swap) 명령어로 원자성을 보장한다.

```java
private AtomicInteger counter = new AtomicInteger(0);

public void increment() {
    counter.incrementAndGet();
}
```

경쟁이 심한 환경에서는 `AtomicLong`도 한계가 있다. 같은 메모리 위치를 모든 스레드가 CAS로 두드리니 캐시 라인 경쟁이 일어난다. JDK 8부터 도입된 `LongAdder`는 여러 셀로 분산해서 갱신하고, 읽을 때만 합산한다.

```java
private LongAdder requestCount = new LongAdder();

public void onRequest() {
    requestCount.increment(); // 셀별로 분산 갱신
}

public long getCount() {
    return requestCount.sum(); // 읽을 때만 합산
}
```

처리량이 매우 높은 카운터(요청 수, 메트릭)는 `LongAdder`가 `AtomicLong`보다 월등히 빠르다. 다만 읽기가 잦으면 합산 비용이 누적되니, 쓰기 빈도가 압도적으로 높을 때 적합하다.

값을 자주 읽고 그 값으로 분기를 하는 경우(예: 동시 접속자 제한)에는 `AtomicInteger`가 맞다. `LongAdder.sum()`은 호출 시점에 다른 스레드 갱신이 반영 안 된 값을 줄 수도 있다.

## 성능 차이

래퍼 타입은 객체이므로 원시 타입보다 메모리를 많이 쓰고, GC 부담이 생긴다.

```java
// 원시 타입: 약 40ms
long start = System.nanoTime();
long sum = 0;
for (int i = 0; i < 10_000_000; i++) {
    sum += i;
}

// 래퍼 타입: 약 200ms 이상
Long sum2 = 0L;
for (int i = 0; i < 10_000_000; i++) {
    sum2 += i; // 매 반복마다 언박싱 → 연산 → 오토박싱
}
```

반복문 안에서 래퍼 타입을 쓰면 매번 박싱/언박싱이 일어나면서 불필요한 객체가 대량 생성된다.

메모리 차이도 크다.

| 타입 | 메모리 |
|------|--------|
| `int` | 4byte |
| `Integer` | 약 16byte (객체 헤더 12byte + int 4byte, 8byte 정렬) |
| `int[1000]` | 약 4KB |
| `Integer[1000]` | 약 20KB (객체 참조 + 각 Integer 객체) |

## 래퍼 타입을 써야 하는 경우

원시 타입을 쓸 수 있는 곳에서는 원시 타입을 쓴다. 래퍼를 써야 하는 경우는 정해져 있다.

**제네릭 타입 파라미터**

```java
List<int> list = new ArrayList<>();    // 컴파일 에러
List<Integer> list = new ArrayList<>(); // OK
Map<String, Integer> map = new HashMap<>();
```

제네릭은 참조 타입만 받기 때문에 래퍼를 써야 한다.

**null이 의미를 가지는 경우**

```java
// "값이 없음"을 표현해야 할 때
public class SearchCondition {
    private Integer minPrice;  // null이면 조건 없음
    private Integer maxPrice;  // null이면 조건 없음
}
```

원시 타입은 null이 될 수 없어서, "값이 설정되지 않음"을 표현할 방법이 없다. 0이나 -1 같은 매직 넘버를 쓰는 것보다 null을 쓰는 게 의도가 명확하다.

**DB 매핑에서 nullable 컬럼**

```java
// JPA Entity
@Entity
public class Product {
    private int stock;          // NOT NULL 컬럼
    private Integer discountRate; // nullable 컬럼
}
```

**Optional과 함께 쓸 때**

```java
OptionalInt optInt = OptionalInt.of(10);       // 원시 타입 전용
Optional<Integer> optInteger = Optional.of(10); // 래퍼 타입

// 원시 타입 전용 Optional이 있으니 되도록 이쪽을 쓴다
OptionalInt, OptionalLong, OptionalDouble
```

### JPA Entity의 ID는 Long으로 선언한다

JPA 엔티티의 식별자는 거의 예외 없이 `long`이 아니라 `Long`으로 선언해야 한다. 이유는 영속성 컨텍스트의 `isNew()` 판단 때문이다.

```java
@Entity
public class Order {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id; // Long으로 선언

    // ...
}
```

Spring Data JPA의 `SimpleJpaRepository.save()`는 내부적으로 ID가 null인지 검사해서 `persist`(INSERT)와 `merge`(SELECT 후 UPDATE) 중 하나를 결정한다.

```java
// SimpleJpaRepository 내부
public <S extends T> S save(S entity) {
    if (entityInformation.isNew(entity)) {
        em.persist(entity);
        return entity;
    } else {
        return em.merge(entity);
    }
}
```

`isNew()`는 ID가 null이면 새 엔티티로 본다. ID가 `long`이면 기본값이 0이라서, 새 엔티티를 저장할 때도 isNew가 false로 판정되어 `merge`가 호출된다. `merge`는 DB에서 SELECT를 먼저 날려서 기존 엔티티를 찾아보는데, 새 엔티티니까 못 찾고, 그제야 INSERT한다. 매 save마다 불필요한 SELECT가 한 번 더 나간다.

`Long`으로 선언하면 새 엔티티의 ID는 null이라서 isNew가 true가 되고, 곧장 `persist`가 호출된다.

복합키 사용 시에도 마찬가지로, 모든 필드를 래퍼 타입으로 선언하거나 `Persistable` 인터페이스를 직접 구현해야 한다.

## JSON/직렬화에서 0과 null의 차이

`int`와 `Integer`는 JSON 매핑에서 다른 의미를 가진다. `int`는 항상 값이 있고(기본값 0), `Integer`는 null일 수 있다.

```java
public class UserResponse {
    private int age;        // 미입력 시 0
    private Integer height; // 미입력 시 null
}
```

```json
// 응답 예시
{ "age": 0, "height": null }
```

이 차이를 무시하면 의도치 않은 데이터가 응답에 섞인다. 예를 들어, 검색 결과에서 점수를 안 매긴 항목과 0점인 항목이 구분되지 않는다.

### Jackson @JsonInclude

Jackson에서 null 필드를 응답에서 빼려면 `@JsonInclude`를 쓴다.

```java
@JsonInclude(JsonInclude.Include.NON_NULL)
public class UserResponse {
    private int age;        // 0이어도 응답에 포함됨 (원시 타입은 null이 될 수 없음)
    private Integer height; // null이면 응답에서 제외
}
```

`Include.NON_DEFAULT`로 설정하면 원시 타입의 기본값(0, false 등)도 제외된다. 하지만 의도적으로 0을 보내야 하는 경우와 구분이 안 되니, 가능하면 `Integer`로 선언하고 `NON_NULL`을 쓰는 게 명확하다.

```java
// 의도와 동작이 일치하는 방식
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ProductDto {
    private Integer price;        // null이면 미설정
    private Integer discountRate; // null이면 할인 없음
}
```

DTO 설계 시 "값이 없음"과 "값이 0"을 의미적으로 구분해야 하는 필드는 반드시 래퍼 타입으로 선언한다. 외부 API와 통신하는 DTO는 거의 모든 숫자 필드를 래퍼로 두는 게 안전하다.

## Project Valhalla와 미래의 박싱

박싱 비용은 자바의 오랜 숙제다. 객체로 다뤄야 하지만 객체로 다루기엔 비싸다는 모순을 해결하려는 시도가 Project Valhalla다.

핵심 아이디어는 "value class". 참조 동등성(identity) 없이, 값으로만 의미를 갖는 객체를 정의할 수 있게 한다.

```java
// 미래의 자바에서 (제안된 문법, 확정 아님)
value class Point {
    int x;
    int y;
}

Point p = new Point(3, 4);
// 객체 헤더 없이 인라인으로 저장 가능
// Point[] 배열도 int[]처럼 메모리 연속 배치
```

value class는 다음 특성을 가진다.

- 참조가 아닌 값으로 다뤄짐 (스택 할당 가능, 인라인 가능)
- `==` 비교가 필드 값 비교로 동작
- `null` 불가 (기본 인스턴스 존재)
- 불변

이게 정착되면 `Integer`도 value class로 재정의되어 박싱 비용이 사라질 가능성이 있다. JEP 401(Value Classes and Objects), JEP 402(Enhanced Primitive Boxing) 등이 관련 작업이다.

JDK 23~24 시점에 프리뷰로 일부 기능이 들어오기 시작했지만, 표준화에는 더 시간이 걸린다. 당분간은 박싱을 피하는 기존 기법(원시 스트림, 원시 타입 컬렉션)에 의존해야 한다.

## 실무에서 자주 하는 실수

### 1. Map의 getOrDefault와 언박싱

```java
Map<String, Integer> map = new HashMap<>();
int value = map.getOrDefault("key", null); // NPE
```

`getOrDefault`의 반환 타입이 `Integer`인데, null이 반환되면 `int`로 언박싱하면서 NPE가 발생한다.

### 2. 컬렉션 remove 메서드 혼동

```java
List<Integer> list = new ArrayList<>(List.of(1, 2, 3, 4, 5));
list.remove(3);           // 인덱스 3의 요소를 제거 → [1, 2, 3, 5]
list.remove(Integer.valueOf(3)); // 값 3을 제거 → [1, 2, 4, 5]
```

`remove(int index)`와 `remove(Object o)` 두 메서드가 오버로딩되어 있어서, `int` 리터럴을 넘기면 인덱스로 동작한다. 값으로 제거하려면 명시적으로 `Integer`로 변환해야 한다.

### 3. switch문에서 null

```java
Integer status = null;
switch (status) { // NPE - switch는 내부적으로 intValue()를 호출한다
    case 1: break;
    case 2: break;
}
```

Java 17 이전까지 switch에 null을 넘길 수 없다. null 체크를 먼저 해야 한다.
