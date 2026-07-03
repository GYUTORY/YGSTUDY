---
title: Java EnumSet 심화 (비트 벡터 구현, RegularEnumSet/JumboEnumSet, EnumMap 비교)
tags: [language, java, 컬렉션-및-데이터-처리, collectionframework, enumset, enummap]
updated: 2026-04-17
---

# EnumSet 심화 — 비트 벡터로 구현된 Set

## 왜 EnumSet을 따로 다루는가

`EnumSet`은 `AbstractSet`을 상속한 추상 클래스다. `new EnumSet<>()`처럼 직접 생성할 수 없고 반드시 정적 팩토리 메서드(`of`, `noneOf`, `allOf`, `range`, `copyOf`, `complementOf`)로만 만들 수 있다. 이 제약 자체가 EnumSet의 정체를 잘 보여준다. EnumSet은 "원소가 enum이라는 사실을 안다"는 전제를 가지고 비트 연산만으로 모든 집합 연산을 수행하는, 사실상 일반 Set이 아닌 비트 마스크다.

`HashSet<MyEnum>`도 같은 일을 할 수는 있다. 하지만 `HashSet`은 각 원소마다 `Entry` 객체와 해시 버킷, 링크드 리스트(또는 트리) 노드를 둔다. 원소가 7개짜리 enum이라면 64비트 long 하나로 표현 가능한 정보를 위해 객체 십수 개를 만드는 셈이다. EnumSet은 이걸 long 한두 개로 압축하고, 합집합·교집합·여집합 같은 연산을 단일 비트 연산으로 처리한다. 작은 차이가 아니라 메모리는 한두 자릿수, 연산 속도는 두 자릿수 배 차이가 난다.

## 비트 벡터 내부 구현 원리

EnumSet의 핵심 아이디어는 단순하다. `enum`은 컴파일 타임에 모든 인스턴스가 결정되고 `ordinal()`로 0부터 시작하는 고유 정수를 가진다. 그러므로 enum 상수 하나는 비트 한 개에 대응시킬 수 있다.

```java
public enum Status {
    PENDING,    // ordinal = 0  → bit 0  (0b0001)
    APPROVED,   // ordinal = 1  → bit 1  (0b0010)
    REJECTED,   // ordinal = 2  → bit 2  (0b0100)
    CANCELED;   // ordinal = 3  → bit 3  (0b1000)
}
```

`{APPROVED, CANCELED}`라는 집합은 비트 마스크로 `0b1010`, 즉 long 값 10이다. 이 표현 위에서 모든 Set 연산은 비트 연산으로 환원된다.

| 집합 연산 | 비트 연산 |
|-----------|-----------|
| `add(e)` | `bits |= (1L << e.ordinal())` |
| `remove(e)` | `bits &= ~(1L << e.ordinal())` |
| `contains(e)` | `(bits & (1L << e.ordinal())) != 0` |
| `addAll(other)` | `bits |= other.bits` |
| `retainAll(other)` | `bits &= other.bits` |
| `removeAll(other)` | `bits &= ~other.bits` |
| `complementOf(other)` | `bits = universeMask & ~other.bits` |
| `size()` | `Long.bitCount(bits)` |
| `isEmpty()` | `bits == 0` |

`HashSet.contains()`는 해시 계산, 버킷 인덱싱, equals 비교를 거친다. EnumSet은 시프트 한 번과 AND 한 번이다. 이 차이가 실제 워크로드에서 그대로 드러난다.

## RegularEnumSet과 JumboEnumSet

EnumSet은 추상 클래스이고 실제 구현체는 두 개다. `java.util.RegularEnumSet`과 `java.util.JumboEnumSet`. 둘 다 `package-private`이라 외부에서는 존재 자체가 보이지 않는다.

### 분기 로직 — `noneOf`의 내부

```java
public static <E extends Enum<E>> EnumSet<E> noneOf(Class<E> elementType) {
    Enum<?>[] universe = getUniverse(elementType);
    if (universe == null)
        throw new ClassCastException(elementType + " not an enum");

    if (universe.length <= 64)
        return new RegularEnumSet<>(elementType, universe);
    else
        return new JumboEnumSet<>(elementType, universe);
}
```

`getUniverse()`는 `SharedSecrets`를 통해 enum 클래스의 `values()` 결과를 캐시 형태로 가져온다. 매번 배열 복사를 하지 않으려는 최적화다. `EnumSet.of(...)`, `allOf(...)`, `range(...)`도 결국 `noneOf`를 호출한 뒤 비트만 채워 넣는다.

분기 기준은 enum 상수의 개수다. 64개 이하면 long 하나에 다 들어가므로 `RegularEnumSet`을 쓰고, 65개 이상이면 `long[]` 배열이 필요하므로 `JumboEnumSet`을 쓴다.

### RegularEnumSet — 단일 long

```java
class RegularEnumSet<E extends Enum<E>> extends EnumSet<E> {
    private long elements = 0L;

    public boolean add(E e) {
        typeCheck(e);
        long oldElements = elements;
        elements |= (1L << ((Enum<?>)e).ordinal());
        return elements != oldElements;
    }

    public boolean contains(Object e) {
        if (e == null) return false;
        Class<?> eClass = e.getClass();
        if (eClass != elementType && eClass.getSuperclass() != elementType)
            return false;
        return (elements & (1L << ((Enum<?>)e).ordinal())) != 0;
    }

    public int size() {
        return Long.bitCount(elements);
    }
}
```

필드는 `long elements` 단 하나다. 인스턴스 자체의 크기가 객체 헤더 + long 하나 + 부모가 가진 elementType 참조 정도라 수십 바이트 수준이다.

### JumboEnumSet — long 배열

enum 상수가 64개를 넘으면 long 하나로 표현이 안 된다. `JumboEnumSet`은 `long[] elements`를 두고 ordinal을 64로 나눠 어느 칸의 어느 비트에 저장할지 계산한다.

```java
class JumboEnumSet<E extends Enum<E>> extends EnumSet<E> {
    private long elements[];
    private int size = 0;

    public boolean add(E e) {
        typeCheck(e);
        int eOrdinal = e.ordinal();
        int eWordNum = eOrdinal >>> 6;          // ordinal / 64
        long oldElements = elements[eWordNum];
        elements[eWordNum] |= (1L << eOrdinal); // long shift는 mod 64 자동 적용
        boolean result = (elements[eWordNum] != oldElements);
        if (result) size++;
        return result;
    }
}
```

여기서 한 가지 미묘한 트릭이 있다. `1L << eOrdinal`에서 `eOrdinal`이 64 이상이어도 자바의 long shift는 하위 6비트만 사용한다. 즉 `1L << 65`는 `1L << 1`과 같다. 이 동작을 활용해 word 인덱스만 바깥에서 계산하고 비트 위치는 컴파일러/CPU에 맡긴다.

`size`를 별도로 유지하는 이유는, 배열 전체에 `Long.bitCount()`를 매번 돌리면 O(n/64)이지만 변경 시점에 미리 갱신해두면 `size()` 호출이 O(1)이 되기 때문이다. RegularEnumSet은 long 하나라 매번 bitCount를 호출해도 명령어 한 개라 굳이 캐시할 필요가 없다.

### 실제로 64개 넘는 enum이 있나

거의 없다. 그래서 보통의 코드에서는 항상 `RegularEnumSet`이 만들어진다. `JumboEnumSet`은 자동 생성된 코드(예: 프로토콜 정의에서 enum으로 변환된 거대한 상수 목록)나 ASCII 문자 enum 같은 특수한 경우에만 등장한다. 그래도 분기가 존재하기 때문에 enum 크기가 임계값을 넘는 순간 메모리 레이아웃과 일부 연산의 비용이 바뀐다는 점은 알아둬야 한다.

## add/remove/contains의 실제 비용과 HashSet 비교

`HashSet.add(e)`는 다음을 거친다.
- `e.hashCode()` 호출
- 해시값을 테이블 크기로 모듈로 → 버킷 인덱스
- 버킷의 링크드 리스트(또는 트리)를 순회하며 `equals` 비교
- 새 노드 객체 할당, 링크 갱신
- 필요 시 리사이징

EnumSet은 `e.ordinal()` 호출 한 번, 시프트와 OR 한 번씩이다. JIT가 인라이닝하면 사실상 두 명령어 수준으로 줄어든다. 마이크로벤치마크를 돌려보면 EnumSet이 HashSet보다 add/contains가 5~20배 빠르고, 합집합/교집합 같은 집합 연산은 두 자릿수 배 차이까지 벌어진다.

```java
// 100만 번 contains 호출 비교 (의사 코드)
EnumSet<Status> es = EnumSet.of(Status.APPROVED);
HashSet<Status> hs = new HashSet<>(Set.of(Status.APPROVED));

// es.contains(Status.APPROVED) → 단일 AND 연산
// hs.contains(Status.APPROVED) → 해시 + equals
```

다만 EnumSet의 진짜 강점은 단일 원소 연산이 아니라 집합 연산에 있다. 두 EnumSet의 합집합은 long 하나의 OR이지만, 두 HashSet의 `addAll`은 한쪽을 전부 순회하며 다른 쪽에 add를 호출한다. 권한 체크처럼 "사용자 권한과 필요 권한의 교집합이 비어있지 않은가" 같은 코드는 EnumSet으로 짜면 한 줄로 끝난다.

```java
EnumSet<Permission> required = EnumSet.of(Permission.READ, Permission.WRITE);
EnumSet<Permission> userPerms = user.getPermissions();

// 교집합이 required와 같은지 = required가 userPerms의 부분집합인지
boolean allowed = userPerms.containsAll(required);
// 내부적으로는 (userPerms.elements & required.elements) == required.elements
```

### 이터레이터도 비트 연산이다

```java
// RegularEnumSet의 이터레이터 핵심부
private class EnumSetIterator<E extends Enum<E>> implements Iterator<E> {
    long unseen;       // 아직 반환하지 않은 비트
    long lastReturned;

    public E next() {
        if (unseen == 0) throw new NoSuchElementException();
        lastReturned = unseen & -unseen;   // 가장 낮은 set 비트만 추출
        unseen -= lastReturned;
        return (E) universe[Long.numberOfTrailingZeros(lastReturned)];
    }
}
```

`unseen & -unseen`은 비트 트릭의 고전이다. 가장 낮은 1비트만 남기고 나머지를 모두 0으로 만든다. 그 비트의 인덱스를 `numberOfTrailingZeros`로 얻으면 ordinal이 되고, 미리 캐시된 `universe` 배열에서 enum 인스턴스를 꺼낸다. 분기 없이 ordinal 순서대로 순회되며, 각 next() 호출은 명령어 몇 개로 끝난다.

## EnumMap과의 설계 철학 비교

EnumMap도 enum 전용 컬렉션이지만 내부는 비트 벡터가 아닌 배열이다.

```java
public class EnumMap<K extends Enum<K>, V> {
    private transient K[] keyUniverse;  // values() 캐시
    private transient Object[] vals;    // 길이 = enum 상수 개수
    private transient int size = 0;
    private static final Object NULL = new Object();  // null 값 마커

    public V put(K key, V value) {
        typeCheck(key);
        int index = key.ordinal();
        Object oldValue = vals[index];
        vals[index] = maskNull(value);
        if (oldValue == null) size++;
        return unmaskNull(oldValue);
    }
}
```

`vals`는 enum 상수 개수만큼의 길이를 가진 배열이다. `put(key, value)`는 `key.ordinal()`을 인덱스로 써서 직접 배열에 꽂는다. 해시 계산도, 버킷 충돌도 없다. `get(key)`도 마찬가지로 단일 배열 접근이다.

왜 EnumSet은 비트 벡터고 EnumMap은 배열인가. 답은 단순하다. Set은 "있다/없다" 한 비트면 충분하지만 Map은 임의의 값 객체를 저장해야 한다. 값을 비트로 표현할 방법이 없으니 슬롯마다 참조를 둘 수밖에 없다. 그래서 EnumMap의 메모리는 `enum 상수 수 × 참조 크기`로 고정된다. 키가 하나만 있어도 전체 크기의 배열이 할당된다.

이 둘은 같은 철학을 공유한다. "원소가 enum이라는 사실을 컴파일 타임에 알고 있으니 ordinal을 인덱스로 직접 쓰자". HashSet/HashMap이 임의의 객체를 위해 해시 함수를 거치는 일반화 비용을 내는 반면, EnumSet/EnumMap은 enum이라는 제약을 받아들이는 대신 그 비용을 0으로 만든다.

### null 처리의 차이

EnumSet은 null을 절대 허용하지 않는다. `add(null)`은 즉시 NullPointerException을 던진다. 비트 벡터에 null을 표현할 비트가 없기 때문이다. 추가하려면 universe를 65개로 확장하고 마지막 비트를 null로 약속해야 하는데, 그러면 분기와 특수 케이스가 늘어 성능 이점을 까먹는다.

EnumMap은 키는 null 불허지만 값은 null 허용이다. 다만 내부 배열의 `null`은 "이 키가 매핑되지 않았다"는 의미라, 실제 null 값을 저장하려면 sentinel 객체로 마스킹한다(`maskNull`/`unmaskNull`). 코드가 약간 지저분해지지만 외부 API는 일반 Map과 동일하게 동작한다.

## copyOf, complementOf, range의 비트 단위 구현

### copyOf

```java
public static <E extends Enum<E>> EnumSet<E> copyOf(EnumSet<E> s) {
    return s.clone();
}
```

같은 EnumSet 타입이면 그냥 clone이다. RegularEnumSet의 clone은 long 하나만 복사하고 끝난다. JumboEnumSet은 `long[]`을 `Arrays.copyOf`로 복사한다. 어느 쪽이든 원본 크기에 비례하는 작은 배열 복사다.

다른 Collection을 받는 오버로드도 있다.

```java
public static <E extends Enum<E>> EnumSet<E> copyOf(Collection<E> c) {
    if (c instanceof EnumSet) {
        return ((EnumSet<E>)c).clone();
    } else {
        if (c.isEmpty())
            throw new IllegalArgumentException("Collection is empty");
        Iterator<E> i = c.iterator();
        E first = i.next();
        EnumSet<E> result = EnumSet.of(first);
        while (i.hasNext())
            result.add(i.next());
        return result;
    }
}
```

빈 컬렉션을 거부하는 이유는 elementType을 모르기 때문이다. EnumSet은 universe(enum 클래스의 모든 상수 배열)를 알아야 하는데, 빈 컬렉션에서는 어떤 enum인지 추론할 방법이 없다. 그래서 `noneOf(Class)`처럼 명시적으로 클래스를 받는 팩토리만 빈 집합을 만들 수 있다.

### complementOf

여집합 연산은 universe의 비트 마스크에서 원본 비트를 빼는 것과 같다.

```java
// RegularEnumSet의 complement (단순화)
void complement() {
    if (universe.length != 0) {
        elements = ~elements;
        elements &= -1L >>> -universe.length;  // universe 범위 밖 비트 제거
    }
}
```

`-1L >>> -universe.length`는 universe 크기만큼의 하위 비트만 1인 마스크를 만드는 트릭이다. 음수로 시프트하면 자바는 하위 6비트만 쓰므로 `-7`은 `57`로 해석되고 `-1L >>> 57`은 하위 7비트가 1인 long이 된다.

이 마스킹이 없으면 universe에 없는 비트(예: enum 상수가 4개인데 5번째 비트 이상)도 1이 되어 size 계산이나 이터레이션이 깨진다.

### range

```java
public static <E extends Enum<E>> EnumSet<E> range(E from, E to) {
    if (from.compareTo(to) > 0)
        throw new IllegalArgumentException(from + " > " + to);
    EnumSet<E> result = noneOf(from.getDeclaringClass());
    result.addRange(from, to);
    return result;
}

// RegularEnumSet의 addRange
void addRange(E from, E to) {
    elements = (-1L >>> (from.ordinal() - to.ordinal() - 1)) << from.ordinal();
}
```

`from.ordinal()`부터 `to.ordinal()`까지 비트가 1인 마스크를 단일 식으로 만든다. 이 한 줄 안에 시프트와 비트 트릭이 압축되어 있다. for 루프로 한 비트씩 채우는 것과 결과는 같지만 명령어 수가 비교가 안 된다.

## 동시성 제약과 직렬화

### 동시성

EnumSet은 동기화되지 않는다. 멀티스레드에서 한쪽이 add하고 다른 쪽이 contains하면 데이터 레이스가 발생할 수 있다. 동시 접근이 필요하면 `Collections.synchronizedSet(EnumSet.of(...))`로 감싸야 한다.

다만 한 가지 함정이 있다. EnumSet 자체는 final 필드가 아니므로 happens-before 보장이 없다. 한 스레드에서 만든 EnumSet을 다른 스레드에 그냥 넘기면 비트가 보이지 않을 수 있다. volatile 참조로 게시하거나 동기화 블록 안에서 전달해야 한다. 이 문제는 실무에서 잘 안 보이는데, 보통 EnumSet은 정적 상수처럼 초기화 시점에 만들어 final 필드에 박아두기 때문이다. 그러면 final의 안전 게시 보장이 적용된다.

### SerializationProxy 패턴

EnumSet은 직접 직렬화되지 않는다. `writeReplace()`로 `SerializationProxy`라는 내부 클래스를 대신 직렬화한다.

```java
private static class SerializationProxy<E extends Enum<E>>
        implements java.io.Serializable {
    private final Class<E> elementType;
    private final Enum<?>[] elements;

    SerializationProxy(EnumSet<E> set) {
        elementType = set.elementType;
        elements = set.toArray(ZERO_LENGTH_ENUM_ARRAY);
    }

    private Object readResolve() {
        EnumSet<E> result = EnumSet.noneOf(elementType);
        for (Enum<?> e : elements)
            result.add((E)e);
        return result;
    }
}

Object writeReplace() {
    return new SerializationProxy<>(this);
}
```

이 패턴이 왜 필요한가. 두 가지 이유다.

첫째, RegularEnumSet과 JumboEnumSet은 내부 표현이 다르다. 직접 직렬화하면 역직렬화 측에서 어느 구현체를 만들지 결정해야 하고, enum 크기가 64를 넘나드는 경계에서 호환성이 깨진다. SerializationProxy는 "enum 클래스와 원소 목록"이라는 추상적 형태로 직렬화하므로 역직렬화 시 `noneOf`가 적절한 구현체를 다시 선택한다.

둘째, 역직렬화 공격 방어다. 직접 직렬화하면 공격자가 비트 필드를 임의로 조작한 데이터를 보낼 수 있다. universe 범위 밖 비트가 1로 설정되면 `iterator()`가 ArrayIndexOutOfBoundsException을 던지거나 잘못된 enum을 반환한다. SerializationProxy는 enum 인스턴스 배열을 받아 정상 경로(`add`)로 다시 채우므로 잘못된 비트가 끼어들 여지가 없다.

또 하나, EnumSet은 `readObject`를 정의하면서 `InvalidObjectException`을 던지도록 한다. 누군가 SerializationProxy를 우회하려 해도 막힌다.

```java
private void readObject(java.io.ObjectInputStream stream)
        throws java.io.InvalidObjectException {
    throw new java.io.InvalidObjectException("Proxy required");
}
```

Effective Java가 권장하는 직렬화 프록시 패턴의 교과서적 사례다.

## 실무에서 마주치는 함정

### enum 순서를 바꾸면 깨진다

EnumSet의 비트 위치는 ordinal에 묶여 있다. enum 선언 순서를 바꾸면 모든 ordinal이 재배치된다. 메모리 안의 EnumSet은 같은 비트 패턴을 가지지만 그 비트가 가리키는 enum 상수가 달라진다.

JVM 안에서만 사용한다면 큰 문제가 없다. 같은 클래스 파일을 공유하므로 ordinal 변화가 동시에 일어난다. 문제는 외부에 저장하거나 전송할 때다.

```java
// 안티패턴 — DB에 ordinal로 저장
@Entity
class User {
    @Column
    private long permissions;  // EnumSet의 비트 마스크를 저장

    public EnumSet<Permission> getPermissions() {
        // 비트로부터 EnumSet 복원
    }
}
```

이렇게 비트 마스크를 저장한 상태에서 `Permission` enum의 순서를 바꾸거나 중간에 새 상수를 끼워넣으면 기존 데이터가 모두 틀어진다. ordinal 2번이 `WRITE`였다가 `DELETE`가 되어 있으면 권한 시스템이 조용히 망가진다.

### 외부 저장은 name 기반으로

DB나 JSON에 저장할 때는 EnumSet의 비트 마스크나 ordinal 배열이 아니라 enum의 `name()`을 써야 한다.

```java
// 권장 — 이름 기반 저장
String stored = userPerms.stream()
    .map(Enum::name)
    .collect(Collectors.joining(","));

// 복원
EnumSet<Permission> restored = Arrays.stream(stored.split(","))
    .map(Permission::valueOf)
    .collect(Collectors.toCollection(() -> EnumSet.noneOf(Permission.class)));
```

이름으로 저장하면 enum 순서가 바뀌어도 영향이 없다. 상수가 삭제되면 `valueOf`가 예외를 던져 즉시 알 수 있다(조용한 데이터 손상보다 훨씬 낫다). 새 상수를 추가하는 것도 무리 없이 호환된다.

JPA/Hibernate에서 컬렉션 매핑을 할 때도 `@ElementCollection`과 `@Enumerated(EnumType.STRING)`을 함께 써서 이름으로 저장하는 게 맞다. `EnumType.ORDINAL`은 이름이 ORDINAL이라 안전해 보이지만 위에서 말한 함정을 그대로 가진다.

### 타입 안전성 우회

EnumSet은 `elementType`을 인스턴스 필드로 가지고 있어서 잘못된 enum을 add하면 런타임에 ClassCastException이 난다. raw 타입이나 `Object` 컬렉션 경유로 다른 enum 인스턴스를 넣으려는 코드가 있을 수 있는데, 컴파일러는 못 잡고 typeCheck가 실행 중에 잡는다. 일반적인 사용에서는 문제될 일이 없지만 리플렉션이나 raw 타입을 다루는 라이브러리를 거치면 사고가 난다.

### 거대 enum의 메모리

JumboEnumSet은 enum 크기에 비례하는 long 배열을 항상 할당한다. 상수가 1000개인 enum이 있다면 EnumSet 인스턴스 하나가 16개의 long, 즉 128바이트 정도를 쓴다. 원소가 한두 개만 들어 있어도 마찬가지다. EnumSet 인스턴스를 수백만 개 만드는 코드라면 차라리 `Set.of(singleEnum)`이나 단순한 enum 참조 하나가 더 가볍다.

## 정리

EnumSet은 "원소가 enum"이라는 단 하나의 제약을 받아들이는 대신 다른 모든 Set 구현이 가질 수 없는 성능을 얻는다. 비트 벡터 표현은 단순하지만, RegularEnumSet/JumboEnumSet 분기, 비트 트릭으로 짠 이터레이터와 range 연산, SerializationProxy를 통한 안전한 직렬화까지 디테일이 촘촘하다. EnumMap도 같은 철학으로 배열 기반 구현을 택한다.

실무에서 가장 중요한 건 두 가지다. enum 기반의 권한·상태·플래그 집합은 EnumSet으로 짜는 게 거의 항상 옳다는 것, 그리고 그 비트 표현이나 ordinal을 외부에 노출시키지 말아야 한다는 것이다. ordinal 의존을 끊고 name 기반으로 외부 경계를 그으면 EnumSet의 성능 이점만 가져갈 수 있다.
