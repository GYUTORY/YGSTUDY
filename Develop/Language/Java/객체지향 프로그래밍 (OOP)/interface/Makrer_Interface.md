---
title: Marker Interface
tags: [language, java, 객체지향-프로그래밍-oop, interface, marker-interface]
updated: 2026-05-03
---

# 마커 인터페이스 (Marker Interface)

메서드도 상수도 없는 빈 인터페이스다. 클래스 정의에 `implements XxxMarker` 한 줄을 붙이는 것만으로 JVM이나 라이브러리가 그 클래스를 다른 길로 처리하게 만든다. 첫인상은 "이게 왜 필요해?" 싶지만, 실제로 직렬화 캐시가 깨지거나 컬렉션 알고리즘이 100배 느려지는 사고를 한 번 겪고 나면 빈 인터페이스 한 줄의 무게를 다시 보게 된다.

이 문서는 JDK가 표준으로 제공하는 마커 인터페이스 세 가지(`Serializable`, `Cloneable`, `RandomAccess`)를 실무에서 마주칠 트러블슈팅 관점으로 정리한다. JVM 내부 동작 원리나 제네릭과의 조합 같은 깊은 주제는 [Marker_Interface_Deep_Dive.md](Marker_Interface_Deep_Dive.md)에 따로 정리해 두었다.

## 마커 인터페이스가 뭐고 왜 빈 채로 두나

마커 인터페이스는 클래스 메타데이터에 "이 클래스는 X 타입이다"라는 라벨을 붙이는 용도다. `instanceof XxxMarker`나 `Class.getInterfaces()`로 검사하면 빈 인터페이스라도 분기 조건으로 쓸 수 있다.

```java
public interface Serializable {
}
```

`java.io.Serializable`의 실제 소스가 정확히 이 모양이다. 메서드가 한 줄도 없는데 `ObjectOutputStream`은 이 인터페이스를 보고 직렬화 가능 여부를 결정한다. 동작은 라벨을 검사하는 쪽 코드가 다 책임지고, 라벨을 붙이는 쪽은 의도만 표시한다.

빈 인터페이스로 두는 이유는 단순하다. 메서드가 있으면 구현 클래스가 그 메서드를 채워야 하는데, 마커는 "특정 행동을 강제하지 않으면서 이 타입에 속한다는 사실만 표시"하는 게 목적이다. 메서드를 추가하는 순간 마커가 아니라 일반 인터페이스가 된다.

## Serializable: 빠지면 NotSerializableException

가장 자주 쓰이고 가장 자주 사고 나는 마커다. 객체를 바이트 스트림으로 변환하려면 그 객체의 클래스가 `Serializable`을 구현하고 있어야 한다.

```java
public class UserDto implements Serializable {
    private static final long serialVersionUID = 1L;
    private String name;
    private int age;
}
```

`Serializable`을 빼고 `ObjectOutputStream.writeObject()`에 넘기면 즉시 예외가 터진다.

```
java.io.NotSerializableException: com.example.UserDto
    at java.base/java.io.ObjectOutputStream.writeObject0(ObjectOutputStream.java:1197)
    at java.base/java.io.ObjectOutputStream.writeObject(ObjectOutputStream.java:354)
```

`ObjectOutputStream` 내부에 `obj instanceof Serializable` 체크가 박혀 있고, 통과하지 못하면 바로 던진다. 메서드가 없는 마커지만 JVM이 `instanceof`로 분기하기 때문에 이 한 줄이 직렬화 가능 여부를 갈라놓는다.

### 컬렉션 필드가 한 군데라도 빠지면 전부 실패한다

자주 놓치는 함정 하나. 부모 클래스는 `Serializable`을 구현했어도 그 안에 들어 있는 필드가 직렬화 불가능 객체면 그 시점에 예외가 터진다.

```java
public class Order implements Serializable {
    private static final long serialVersionUID = 1L;
    private String orderId;
    private Customer customer;
}

public class Customer {
    private String name;
}
```

`Order`를 직렬화하려고 하면 `Customer`에서 `NotSerializableException`이 난다. 직렬화는 객체 그래프 전체를 따라가기 때문에 참조하는 모든 필드의 타입이 직렬화 가능해야 한다. DTO 트리 어딘가에 `Serializable`을 빼먹은 클래스 하나가 있으면 그 시점부터 막힌다.

해결 방법은 두 가지다. 직렬화에서 제외해도 되면 `transient`로 표시하고, 진짜로 직렬화해야 하면 그 타입에도 `Serializable`을 붙인다.

```java
public class Order implements Serializable {
    private static final long serialVersionUID = 1L;
    private String orderId;
    private transient Connection dbConnection;
}
```

DB 커넥션이나 스레드처럼 본질적으로 직렬화가 의미 없는 자원은 `transient`로 막고, 역직렬화 후에 다시 초기화하는 패턴을 쓴다.

### serialVersionUID를 안 박으면 운영 중에 캐시가 터진다

`Serializable`을 구현했다면 `serialVersionUID`를 반드시 직접 선언해야 한다. 빠뜨리면 컴파일러가 클래스 구조를 해시해서 자동 생성하는데, 이 값이 매우 민감하다. 필드 추가, 메서드 시그니처 변경, 접근 제어자 수정 같은 사소한 변경에도 값이 달라진다.

운영 중인 서비스에서 DTO에 필드를 하나 추가했더니 Redis에 캐시된 직렬화 객체를 역직렬화할 때 다음 예외가 나는 시나리오는 흔하다.

```
java.io.InvalidClassException: com.example.UserDto;
    local class incompatible:
    stream classdesc serialVersionUID = 8273469873214,
    local class serialVersionUID = 1029384756102
```

스트림에 박혀 있는 UID와 현재 JVM에 로드된 클래스의 UID가 안 맞아서 나는 에러다. 캐시를 비우거나 새 키로 옮기지 않으면 영원히 풀리지 않는다.

```java
public class UserDto implements Serializable {
    private static final long serialVersionUID = 1L;
    private String name;
    private int age;
    private String email;  // 새로 추가
}
```

`serialVersionUID`만 고정되어 있으면 필드 추가는 호환된다. 자바 직렬화는 스트림에 누락된 필드는 기본값(int면 0, 객체면 null)으로 채워서 역직렬화한다. 반대로 필드를 삭제하거나 타입을 바꾸면 호환성이 깨지므로 deprecated 처리만 하고 남겨두는 편이 안전하다.

## Cloneable: 빠지면 CloneNotSupportedException

`Cloneable`은 마커 인터페이스 중에서도 가장 이상하게 동작하는 녀석이다. 인터페이스에는 메서드가 없는데 `Object.clone()`의 동작을 바꾼다.

```java
public class Point implements Cloneable {
    private int x, y;

    @Override
    public Point clone() {
        try {
            return (Point) super.clone();
        } catch (CloneNotSupportedException e) {
            throw new AssertionError(e);
        }
    }
}
```

`Cloneable`을 빼고 `super.clone()`을 호출하면 다음 예외가 난다.

```
java.lang.CloneNotSupportedException: com.example.Point
    at java.base/java.lang.Object.clone(Native Method)
```

`Object.clone()`은 네이티브 메서드인데 내부에서 호출 객체가 `Cloneable`인지 검사하고 아니면 예외를 던진다. 메서드를 정의하지도 않으면서 메서드의 동작을 변경하는 구조라 Effective Java Item 13은 아예 `Cloneable` 자체를 쓰지 말라고 권한다.

신규 코드에서는 복사 생성자나 정적 팩터리 메서드가 정답이다.

```java
public class Point {
    private final int x, y;

    public Point(int x, int y) {
        this.x = x;
        this.y = y;
    }

    public Point(Point original) {
        this(original.x, original.y);
    }
}
```

이미 `Cloneable`을 구현한 라이브러리 클래스를 다룰 때만 위의 함정을 인지하고 사용한다. 새로 만드는 도메인 객체에 `Cloneable`을 다는 건 거의 항상 잘못된 선택이다.

## RandomAccess: 빠지면 알고리즘이 O(n²)이 된다

`RandomAccess`는 동작이 깨지지 않는다. 대신 성능이 조용히 망가진다. 예외가 안 나는 만큼 잡기 어려운 문제다.

```java
public interface RandomAccess {
}
```

`ArrayList`는 이 마커를 구현하고 `LinkedList`는 구현하지 않는다. `Collections` 유틸리티 메서드들이 이 차이를 보고 알고리즘을 바꾼다.

```java
public static <T> int binarySearch(List<? extends Comparable<? super T>> list, T key) {
    if (list instanceof RandomAccess || list.size() < BINARYSEARCH_THRESHOLD) {
        return Collections.indexedBinarySearch(list, key);
    } else {
        return Collections.iteratorBinarySearch(list, key);
    }
}
```

`indexedBinarySearch`는 `list.get(mid)`로 인덱스 접근을 한다. `ArrayList`라면 O(1)이지만 `LinkedList`에서 같은 호출은 매번 처음부터 노드를 따라가므로 O(n)이 된다. 이진 탐색 전체가 O(n log n)으로 커지는 것이다. 그래서 `LinkedList`처럼 `RandomAccess`가 아닌 컬렉션은 `ListIterator`로 순차 접근하는 `iteratorBinarySearch`를 쓴다.

`Collections.shuffle`, `Collections.reverse`, `Collections.fill` 같은 유틸리티에도 같은 패턴이 들어 있다. `LinkedList`를 모르고 던지면 데이터가 커질수록 처리 시간이 비선형으로 폭발한다.

본인이 직접 컬렉션을 순회하는 코드를 짤 때도 이 마커를 활용할 수 있다.

```java
public <T> T pickMiddle(List<T> list) {
    int mid = list.size() / 2;
    if (list instanceof RandomAccess) {
        return list.get(mid);
    }
    Iterator<T> it = list.iterator();
    for (int i = 0; i < mid; i++) it.next();
    return it.next();
}
```

`LinkedList`에 `get(mid)`를 그대로 쓰면 매번 절반씩 순회한다. 마커를 보고 분기하면 둘 다 안전하게 처리된다.

## 마커 인터페이스 vs 애노테이션

자바 5에서 애노테이션이 들어온 뒤로 "마커 인터페이스는 끝났다"는 말이 한동안 돌았는데, 실제로는 둘이 푸는 문제가 다르다.

| 항목 | 마커 인터페이스 | 마커 애노테이션 |
| --- | --- | --- |
| 검사 시점 | 컴파일 타임 + 런타임 | 주로 런타임 |
| 타입 시스템 통합 | `instanceof`, 제네릭 bound 가능 | 불가능 |
| 메타데이터 첨부 | 매개변수 없음 | 요소 값으로 가능 |
| 적용 대상 | 클래스/인터페이스만 | 클래스, 메서드, 필드, 매개변수 등 |
| 구현 강제력 | 강함 (컴파일러가 검증) | 약함 (런타임 검사 필요) |

선택 기준은 한 줄로 요약된다. **타입을 구분해야 하면 마커 인터페이스, 정보를 첨부해야 하면 애노테이션이다.**

```java
// 컴파일 타임에 타입 안전성이 필요한 경우
public interface Cacheable {}

public <T extends Cacheable> void cacheAll(List<T> items) {
    for (T item : items) cache.put(item.toString(), item);
}
```

위 메서드는 `Cacheable`을 구현하지 않은 클래스의 리스트를 넘기면 컴파일 단계에서 에러가 난다. 런타임에 검사할 필요가 없다.

```java
// 메타데이터로 동작 파라미터를 전달해야 하는 경우
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface Cacheable {
    int ttlSeconds() default 3600;
    String region() default "default";
}
```

`ttlSeconds`나 `region` 같은 부가 정보를 마커 인터페이스로 표현할 방법은 없다. 이런 경우는 애노테이션이 답이다.

Effective Java Item 41이 더 구체적인 기준을 준다. 마커가 클래스나 인터페이스에만 적용되고, 매개변수 타입으로 받거나 컴파일 타임 타입 검사를 활용할 의도가 있다면 마커 인터페이스를 쓴다. 단순히 메타데이터를 다는 용도라면 애노테이션이 가볍다.

## 직접 마커 인터페이스를 만들 때 주의점

서비스 코드에서 사용자 정의 마커를 도입하기 전에 점검할 항목이 몇 개 있다.

타입 시스템 차원의 구분이 진짜 필요한지 먼저 자문한다. 단순히 "이 클래스는 캐시 가능하다" 같은 표시라면 애노테이션이 가볍다. 매개변수 타입에 제약을 걸거나 제네릭 bound로 사용할 일이 없다면 마커 인터페이스의 이점이 거의 없다.

마커 인터페이스는 한번 도입하면 빼기 어렵다. 외부에 공개된 API 클래스에 `implements MyMarker`를 추가하면 그 클래스의 모든 사용자가 영향을 받는다. 핵심 도메인 클래스에 신중하게 적용해야 한다.

마커를 검사하는 코드는 한 곳에 모은다. `instanceof Cacheable` 같은 분기가 여러 모듈에 흩어지면 의도가 흐려지고 변경 영향도가 추적되지 않는다. 디스패처나 핸들러 한 곳에서만 분기하고 도메인 코드는 마커만 다는 식이 깔끔하다.

여러 마커를 동시에 다는 건 자연스럽다. `Cacheable`, `Auditable`, `Versionable`을 한 클래스가 동시에 구현해도 메서드 충돌이 없다. 다중 상속의 함정 없이 직교적인 속성을 쌓아올릴 수 있는 게 마커 인터페이스의 실용성이다.

마커 인터페이스는 1990년대 자바의 흔적처럼 보일 때가 있지만, 표준 라이브러리가 여전히 적극적으로 쓰고 있다. 새로 만드는 코드에서 무턱대고 도입할 건 아니지만, `Serializable`이 빠져서 캐시가 터지거나 `LinkedList`를 잘못 넘겨서 알고리즘이 느려지는 상황을 만났을 때 원인을 짚으려면 이 셋의 동작은 머릿속에 정리되어 있어야 한다.
