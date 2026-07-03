---
title: Java EnumSet 심화 가이드
tags: [language, java, 컬렉션-및-데이터-처리, collectionframework, enumset, enummap]
updated: 2026-04-25
---

# EnumSet과 EnumMap 실용 가이드

`EnumSet`과 `EnumMap`은 enum을 다룰 때 거의 항상 정답이다. 그런데 실무에서 이 둘을 제대로 쓰는 코드를 보기는 의외로 어렵다. `Set<Status> set = new HashSet<>()`처럼 무심코 일반 컬렉션을 쓰거나, `Map<Status, Handler>`를 `HashMap`으로 만들어 두는 코드가 훨씬 많다. 동작은 한다. 다만 enum이라는 정보를 활용하지 못해 메모리는 몇 배, 연산 속도는 한 자릿수 배 더 나쁘게 동작할 뿐이다.

이 문서는 EnumSet/EnumMap을 실제로 어떻게 쓰는지에 집중한다. 비트 벡터 내부 구현이나 RegularEnumSet/JumboEnumSet 분기 같은 깊은 이야기는 [Enum_Set_Deep_Dive.md](./Enum_Set_Deep_Dive.md)에 따로 있다. 여기서는 정적 팩토리 메서드를 언제 어떤 걸 쓰는지, 권한 플래그·feature toggle·상태 머신 같은 실무 패턴, 자주 빠지는 함정을 다룬다. Enum 자체에 대한 설명은 별도 enum 문서를 참고한다. 이 문서는 enum을 이미 정의해 놨다는 전제로 시작한다.

## EnumSet을 선택하는 이유

5~10개짜리 enum 상수를 `HashSet<MyEnum>`에 담으면 어떻게 될까. 각 상수마다 `HashMap.Node` 객체가 생기고, 내부 배열의 버킷에 매달린다. 객체 헤더 16바이트, hash·key·value·next 필드 32바이트, 거기에 enum 상수 자체 참조까지 합치면 원소 하나당 50바이트 안팎이다. enum이 7개라면 350바이트가 넘는다. 같은 정보를 `EnumSet`은 long 하나, 즉 8바이트로 표현한다. 64개 이하 enum은 항상 long 한 개에 담긴다.

성능은 더 큰 차이가 난다. `contains`는 HashSet의 경우 hashCode 계산, 버킷 인덱싱, equals 비교를 거치는데 EnumSet은 `(bits & (1L << ordinal)) != 0` 한 줄로 끝난다. `addAll`, `retainAll` 같은 집합 연산은 더 극단적이다. HashSet은 원소를 하나씩 순회하지만 EnumSet은 두 long을 비트 OR/AND 한 번에 끝낸다. 합집합·교집합이 자주 일어나는 권한 검사 같은 곳에서는 두 자릿수 배 차이가 난다.

성능 수치는 어디까지나 "그래서 EnumSet을 쓰자"는 결정의 근거 정도면 충분하다. 이걸 매번 벤치마크할 필요는 없다. enum이면 EnumSet, enum 키 Map이면 EnumMap. 이 규칙을 외워두는 게 결과적으로 가장 빠르다.

## 정적 팩토리 메서드 여섯 가지

EnumSet은 `new`로 만들 수 없다. `EnumSet`이 추상 클래스라서다. 정적 팩토리 메서드 여섯 개로만 인스턴스를 얻는다. 각각 쓰임새가 명확히 다르므로 어떤 상황에 어떤 걸 쓰는지 익혀두면 코드가 훨씬 직관적이 된다.

### `of(...)` — 알고 있는 원소 몇 개로 시작

가장 흔히 쓰는 팩토리다. 컴파일 타임에 어떤 상수를 넣을지 정해져 있을 때 쓴다.

```java
public enum HttpMethod { GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS }

EnumSet<HttpMethod> readOnly = EnumSet.of(HttpMethod.GET, HttpMethod.HEAD, HttpMethod.OPTIONS);
EnumSet<HttpMethod> mutating = EnumSet.of(HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH, HttpMethod.DELETE);
```

`of`는 1개부터 5개까지 오버로드가 있고, 6개 이상은 가변 인자 버전을 쓴다. 가변 인자는 배열을 만들어 넘기는 비용이 약간 있는데, 캐시되어 평생 쓰는 상수면 무시해도 된다. 매 요청마다 만들어지는 코드라면 그냥 5개 이하로 끊거나 정적 상수로 빼면 된다.

### `noneOf(EnumClass.class)` — 빈 집합으로 시작

런타임에 원소를 동적으로 채워야 할 때 쓴다. `EnumSet`은 원소가 없으면 어느 enum 타입인지 알 수 없으므로 반드시 `Class<E>`를 넘겨야 한다.

```java
public EnumSet<Permission> resolvePermissions(User user) {
    EnumSet<Permission> result = EnumSet.noneOf(Permission.class);
    if (user.isAdmin()) result.add(Permission.MANAGE_USERS);
    if (user.isAuthor()) result.add(Permission.PUBLISH_POST);
    if (user.isModerator()) result.add(Permission.DELETE_COMMENT);
    return result;
}
```

`noneOf` + `add` 조합은 빈 컬렉션부터 빌드업하는 패턴 어디에서나 쓴다. `new HashSet<>()`을 쓰던 자리는 거의 다 `EnumSet.noneOf`로 바꿀 수 있다.

### `allOf(EnumClass.class)` — 전체 상수로 시작

모든 enum 상수가 들어 있는 집합을 한 번에 만든다. "기본은 전부 허용, 일부를 제외"하는 패턴에 잘 어울린다.

```java
EnumSet<HttpMethod> blockedForGuest = EnumSet.of(HttpMethod.DELETE);
EnumSet<HttpMethod> guestAllowed = EnumSet.allOf(HttpMethod.class);
guestAllowed.removeAll(blockedForGuest);
```

`allOf` 다음에 `removeAll`로 빼는 방식은 의도가 명확해서 코드 리뷰에서 다툴 일이 없다. `complementOf`로 한 번에 처리할 수도 있는데 그건 다음 항목에서 다룬다.

### `complementOf(EnumSet)` — 여집합

특정 집합의 보집합을 만든다. 인자는 같은 enum 타입의 EnumSet이어야 한다.

```java
EnumSet<HttpMethod> readOnly = EnumSet.of(HttpMethod.GET, HttpMethod.HEAD, HttpMethod.OPTIONS);
EnumSet<HttpMethod> mutating = EnumSet.complementOf(readOnly);
// mutating = {POST, PUT, PATCH, DELETE}
```

원본을 건드리지 않고 새 집합을 만들기 때문에 안전하다. 인자가 빈 집합이면 `allOf`와 같고, 전체 집합이면 빈 집합이 나온다. 다만 `complementOf`도 인자에서 enum 타입을 추론하므로 빈 EnumSet을 넘겨도 동작한다는 점은 유의한다(`Collection`이 아니라 `EnumSet` 타입을 받는다는 건 시그니처에서 확인하면 된다).

### `range(from, to)` — 연속 구간

ordinal 순서상 연속된 구간을 잘라낸다. 호출 빈도는 가장 낮지만, 한 번 잘 맞는 자리에서는 대안이 없다.

```java
public enum LogLevel { TRACE, DEBUG, INFO, WARN, ERROR, FATAL }

EnumSet<LogLevel> warnAndAbove = EnumSet.range(LogLevel.WARN, LogLevel.FATAL);
// {WARN, ERROR, FATAL}
```

`range`는 enum 선언 순서에 의존하므로, 새 상수가 중간에 끼어들면 의미가 깨질 수 있다. 로그 레벨처럼 이미 순서 자체가 의미를 가지는 경우가 아니면 차라리 `of`로 명시하는 편이 안전하다. 실무에서는 로그 레벨, HTTP 상태 코드 그룹(2xx, 4xx 같은 범주를 enum으로 모델링한 경우) 정도가 대표적이다.

### `copyOf(...)` — 기존 컬렉션 복제

같은 enum 타입의 컬렉션을 받아 새 EnumSet을 만든다. 두 가지 오버로드가 있다.

```java
EnumSet<HttpMethod> source = EnumSet.of(HttpMethod.GET, HttpMethod.POST);
EnumSet<HttpMethod> copy1 = EnumSet.copyOf(source);                         // EnumSet → EnumSet
EnumSet<HttpMethod> copy2 = EnumSet.copyOf(List.of(HttpMethod.GET, HttpMethod.POST));  // Collection → EnumSet
```

`Collection`을 받는 버전은 빈 컬렉션에 대해 `IllegalArgumentException`을 던진다. 컬렉션이 비면 enum 타입을 알 수 없기 때문이다. 이 동작은 처음 보면 항상 한 번씩 깜짝 놀란다. 이런 코드를 본 적이 있다.

```java
List<Status> filtered = source.stream()
    .filter(s -> s.isActive())
    .toList();
EnumSet<Status> set = EnumSet.copyOf(filtered);  // filtered가 비면 IllegalArgumentException
```

방어 로직은 둘 중 하나다. 미리 비어 있는지 검사하거나, 처음부터 `noneOf`로 빈 EnumSet을 만들어 두고 `addAll`로 채운다.

```java
EnumSet<Status> set = EnumSet.noneOf(Status.class);
set.addAll(filtered);  // 빈 컬렉션이어도 안전
```

`copyOf(EnumSet)` 오버로드는 빈 EnumSet에서도 enum 타입 정보를 들고 있으므로 예외가 안 난다. 같은 메서드 이름이지만 두 오버로드의 동작이 미묘하게 다르다는 게 함정이다.

## 실무 사용 패턴

### 권한·상태 플래그

가장 전형적인 용도다. 사용자 역할이나 리소스 상태를 비트 플래그처럼 다루는 자리에 EnumSet이 들어간다.

```java
public enum Permission {
    READ_POST, WRITE_POST, DELETE_POST,
    READ_USER, MANAGE_USER,
    ACCESS_ADMIN
}

public class AccessControl {
    private static final EnumSet<Permission> AUTHOR_PERMS =
        EnumSet.of(Permission.READ_POST, Permission.WRITE_POST, Permission.READ_USER);

    private static final EnumSet<Permission> ADMIN_PERMS =
        EnumSet.allOf(Permission.class);

    public boolean canDelete(EnumSet<Permission> userPerms) {
        return userPerms.contains(Permission.DELETE_POST);
    }

    public boolean hasAll(EnumSet<Permission> userPerms, EnumSet<Permission> required) {
        return userPerms.containsAll(required);
    }
}
```

`containsAll`도 EnumSet 사이에서는 비트 연산 한 번이다. 권한 체크가 핫패스에 있는 서비스라면 이 차이가 누적되어 의미 있는 수치로 나타난다. 정적 상수로 자주 쓰는 권한 셋을 미리 만들어 두면 GC 압박도 줄어든다.

권한 셋을 외부에 노출할 때는 EnumSet을 그대로 반환하지 말고 `Collections.unmodifiableSet`으로 감싸거나 호출자가 변경하지 않는다는 약속을 분명히 한다. EnumSet은 변경 가능 컬렉션이고, 누군가 받아서 `add`/`remove`를 하면 정적 상수가 오염된다.

### Feature Toggle

기능 플래그를 enum으로 정의하고 활성화된 것만 EnumSet으로 들고 있는 패턴이다.

```java
public enum Feature {
    NEW_CHECKOUT, DARK_MODE, AB_TEST_PRICING,
    ASYNC_NOTIFICATION, EXPERIMENTAL_SEARCH
}

public class FeatureToggle {
    private final EnumSet<Feature> enabled;

    public FeatureToggle(Set<String> enabledNames) {
        this.enabled = EnumSet.noneOf(Feature.class);
        for (String name : enabledNames) {
            try {
                enabled.add(Feature.valueOf(name));
            } catch (IllegalArgumentException ignore) {
                // 설정에 오타가 있어도 서비스는 죽지 않게 무시
            }
        }
    }

    public boolean isOn(Feature f) {
        return enabled.contains(f);
    }
}
```

설정 파일이나 환경 변수에서 문자열로 들어온 플래그 이름을 enum으로 변환할 때, 알 수 없는 이름은 무시할지 예외를 던질지 정해야 한다. 실무에서는 무시하는 쪽이 안전한 경우가 많다. enum에 없는 이름이 운영 환경에서 갑자기 나타났다고 서비스가 멈추면 곤란하다.

### HTTP 메서드 화이트리스트

엔드포인트별로 허용 메서드를 정의할 때 EnumSet이 잘 맞는다.

```java
public class EndpointPolicy {
    private final EnumSet<HttpMethod> allowed;

    public EndpointPolicy(HttpMethod... methods) {
        this.allowed = methods.length == 0
            ? EnumSet.noneOf(HttpMethod.class)
            : EnumSet.of(methods[0], Arrays.copyOfRange(methods, 1, methods.length));
    }

    public boolean accepts(HttpMethod method) {
        return allowed.contains(method);
    }
}
```

`EnumSet.of(E first, E... rest)` 가변 인자 형태가 따로 있어서 빈 배열을 그냥 넘길 수가 없다. 빈 케이스는 `noneOf`로 분기해야 한다. 이런 자잘한 시그니처 차이가 EnumSet을 처음 다룰 때 손에 잘 안 익는 부분이다.

## EnumMap — enum을 키로 쓰는 Map

EnumSet이 비트 벡터라면 EnumMap은 배열이다. enum의 ordinal을 인덱스로 쓰는 단순 배열이다. 키 해시 계산도, 버킷 분기도 없다. 그냥 `array[key.ordinal()]`이다. 그래서 빠르고, 메모리는 enum 상수 개수만큼의 참조 슬롯이면 끝이다.

### 기본 패턴

```java
EnumMap<HttpMethod, Handler> handlers = new EnumMap<>(HttpMethod.class);
handlers.put(HttpMethod.GET, new GetHandler());
handlers.put(HttpMethod.POST, new PostHandler());

Handler h = handlers.get(method);
if (h != null) h.handle(request);
```

`new EnumMap<>(EnumClass.class)`처럼 키 enum의 Class를 생성자에 넘겨야 한다. 이 정보가 있어야 내부 배열 크기를 결정할 수 있다.

### `computeIfAbsent`로 그룹핑

스트림의 `groupingBy`에서 EnumMap을 쓰면 깔끔하다.

```java
List<Order> orders = ...;
Map<Status, List<Order>> byStatus = orders.stream()
    .collect(Collectors.groupingBy(
        Order::getStatus,
        () -> new EnumMap<>(Status.class),
        Collectors.toList()
    ));
```

수동으로 만들 때는 `computeIfAbsent`가 손에 익는다.

```java
EnumMap<Status, List<Order>> byStatus = new EnumMap<>(Status.class);
for (Order o : orders) {
    byStatus.computeIfAbsent(o.getStatus(), k -> new ArrayList<>()).add(o);
}
```

`computeIfAbsent`는 키가 없을 때만 람다를 실행한다. 그룹핑·캐싱 자리에서 거의 모든 if-else를 대체할 수 있다.

### 상태 머신

EnumMap의 진가는 상태 머신을 표현할 때 드러난다. 현재 상태와 이벤트를 enum으로 두고, 전이 규칙을 EnumMap으로 들고 있는다.

```java
public enum OrderState { CREATED, PAID, SHIPPED, DELIVERED, CANCELED }
public enum OrderEvent { PAY, SHIP, DELIVER, CANCEL }

public class OrderStateMachine {
    private final EnumMap<OrderState, EnumMap<OrderEvent, OrderState>> transitions;

    public OrderStateMachine() {
        transitions = new EnumMap<>(OrderState.class);
        transitions.put(OrderState.CREATED, transitionsFrom(
            Map.of(OrderEvent.PAY, OrderState.PAID,
                   OrderEvent.CANCEL, OrderState.CANCELED)));
        transitions.put(OrderState.PAID, transitionsFrom(
            Map.of(OrderEvent.SHIP, OrderState.SHIPPED,
                   OrderEvent.CANCEL, OrderState.CANCELED)));
        transitions.put(OrderState.SHIPPED, transitionsFrom(
            Map.of(OrderEvent.DELIVER, OrderState.DELIVERED)));
    }

    private EnumMap<OrderEvent, OrderState> transitionsFrom(Map<OrderEvent, OrderState> src) {
        EnumMap<OrderEvent, OrderState> m = new EnumMap<>(OrderEvent.class);
        m.putAll(src);
        return m;
    }

    public OrderState next(OrderState current, OrderEvent event) {
        EnumMap<OrderEvent, OrderState> table = transitions.get(current);
        if (table == null) return current;
        return table.getOrDefault(event, current);
    }
}
```

전이표를 코드로 풀어 쓰는 방식보다 이 구조가 훨씬 안정적이다. 새 상태나 이벤트가 추가되면 컴파일러가 enum을 통해 거의 모든 누락을 잡아준다. switch-case로 쓴 상태 머신은 새 상태를 추가했을 때 어디를 고쳐야 할지 IDE가 일일이 알려주지 않는다.

## 자주 빠지는 함정

### `copyOf` 빈 컬렉션 예외

앞서 다뤘던 그 문제다. `EnumSet.copyOf(Collection)`은 빈 컬렉션이면 `IllegalArgumentException`이다. `Collection.stream().filter(...).toList()` 같은 파이프라인 끝에 `copyOf`를 붙이면 운영 환경에서 어느 날 갑자기 터질 수 있다. 빈 케이스가 가능한 자리에서는 `noneOf` + `addAll`을 쓴다.

### null을 허용하지 않는다

`EnumSet`은 `add(null)`이 `NullPointerException`이다. `EnumMap`도 키로 null을 못 쓴다. 값은 EnumMap도 null을 허용한다. 일반 Set/Map처럼 `null` 키를 슬쩍 넣어두는 코드가 EnumSet/EnumMap으로 옮기는 순간 깨진다. 마이그레이션 시점에 한 번씩 만난다.

### 동기화되지 않는다

EnumSet과 EnumMap 모두 thread-safe가 아니다. `HashSet`, `HashMap`과 같은 정책이다. 동시 수정이 일어나는 자리에서는 `Collections.synchronizedSet`/`synchronizedMap`으로 감싸거나, 변경 빈도가 낮다면 변경 시점마다 새 EnumSet/EnumMap을 통째로 교체하는 식으로 immutable처럼 다룬다. 권한이나 feature toggle처럼 거의 읽기만 하는 워크로드에서는 후자가 GC와 락 경합 모두에 유리하다.

### iterator 순서는 ordinal 순서

EnumSet/EnumMap의 순회 순서는 enum 선언 순서다. 보장된 동작이라 의도적으로 의지할 수 있다. 단, 누군가 enum 상수의 순서를 바꾸면 이 순서도 바뀐다. ordinal 자체를 직렬화에 쓰지 말라는 일반적인 권고와 같은 맥락이다. 외부 API 응답의 순서가 의미를 가진다면 enum 순서에 의존하지 말고 명시적으로 정렬한다.

### `Collections.emptySet()`을 EnumSet 자리에 쓰면

`Collections.emptySet()`은 타입이 `Set<Object>`로 캐스팅된다. EnumSet 메서드 시그니처에 그대로 넣으면 컴파일은 되지만 EnumSet으로의 다운캐스트나 합집합 연산에서 의도치 않은 동작이 나올 수 있다. 빈 EnumSet이 필요하면 `EnumSet.noneOf(MyEnum.class)`를 쓴다.

## EnumSet vs Set.of vs EnumMap vs Map.of

JDK 9에 들어온 `Set.of(...)`, `Map.of(...)` 같은 불변 컬렉션 팩토리가 있다 보니 enum과 함께 어느 쪽을 써야 하는지 헷갈릴 때가 있다. 기준은 명확하다.

`Set.of(MyEnum.A, MyEnum.B)`는 불변, 순서 없음, 일반 해시 기반 Set이다. enum이라는 사실을 활용하지 않으므로 메모리·연산 모두 EnumSet보다 비싸다. 다만 불변이고 한 번 만들고 끝이라면 차이가 무시할 만큼 작다. "이 권한 셋은 절대 변하지 않는다"는 의도를 코드로 드러내고 싶을 때는 `Set.of`가 더 나은 신호일 수 있다. 단, 합집합·교집합·여집합 같은 집합 연산을 자주 한다면 그 신호보다 비트 연산의 이점이 훨씬 크다. 정적 상수로 만들어 두고 `Collections.unmodifiableSet(EnumSet.of(...))`로 감싸는 절충안이 자주 보인다.

`Map.of(KEY1, V1, KEY2, V2)`도 같은 맥락이다. 키가 enum이고 lookup이 잦으면 EnumMap이 거의 항상 빠르다. `Map.of`는 키가 enum이 아닌 경우, 또는 5쌍 이하의 작은 매핑을 컴파일 타임에 박아 넣고 끝낼 때 어울린다.

판단 기준을 한 줄로 정리하면 이렇다. 키나 원소가 enum이고 변경 가능성이 있거나 집합 연산이 오가면 EnumSet/EnumMap. enum이지만 절대 변하지 않고 단순 lookup만 한다면 `Set.of`/`Map.of`도 무방하다. enum이 아니면 선택지에서 EnumSet/EnumMap은 빠진다.

## 마무리

EnumSet과 EnumMap은 "enum이라는 사실을 모르는 일반 컬렉션"보다 거의 항상 낫다. 비트 벡터·배열 기반이라 메모리도 적고, 연산도 빠르고, 순회 순서도 enum 선언 순서로 자연스럽다. 단점이라 할 만한 건 null을 못 쓴다는 것, 동기화가 안 된다는 것 정도인데 이건 일반 컬렉션과 같은 정책이다.

손에 안 익는 건 정적 팩토리 메서드 여섯 개와 EnumMap 생성자에 `Class`를 넘기는 것뿐이다. 한두 번 써보면 금방 익숙해진다. 비트 벡터 내부 구현이나 RegularEnumSet/JumboEnumSet 분기, 64비트 경계에서 무슨 일이 일어나는지가 궁금하면 [Enum_Set_Deep_Dive.md](./Enum_Set_Deep_Dive.md)를 본다. 실무 코드를 쓸 때는 이 문서로 충분하다.
