
# Java 컬렉션 프레임워크

## 개념

**컬렉션 프레임워크(Collection Framework)** 는 데이터를 효율적으로 저장하고 관리하기 위해 제공되는 Java 표준 라이브러리입니다.  
컬렉션은 데이터의 그룹(예: 리스트, 집합, 맵)을 의미하며, 컬렉션 프레임워크는 이를 처리하기 위한 인터페이스와 클래스들의 집합입니다.

---

## 주요 인터페이스

1. **List**
    - 순서가 있는 데이터의 집합으로, 중복을 허용합니다.
    - 구현 클래스: `ArrayList`, `LinkedList`, `Vector` 등

2. **Set**
    - 순서를 유지하지 않는 데이터의 집합으로, 중복을 허용하지 않습니다.
    - 구현 클래스: `HashSet`, `LinkedHashSet`, `TreeSet` 등

3. **Map**
    - 키와 값의 쌍으로 이루어진 데이터 구조로, 키는 중복을 허용하지 않지만 값은 중복 가능합니다.
    - 구현 클래스: `HashMap`, `TreeMap`, `LinkedHashMap` 등

4. **Queue**
    - FIFO(First-In-First-Out) 구조를 따르는 데이터 구조입니다.
    - 구현 클래스: `PriorityQueue`, `LinkedList` 등

---

## 주요 클래스와 예시

### 1. ArrayList (List 인터페이스 구현)

```java
import java.util.ArrayList;

public class ArrayListExample {
    public static void main(String[] args) {
        ArrayList<String> list = new ArrayList<>();

        // 요소 추가
        list.add("사과");
        list.add("바나나");
        list.add("체리");

        // 요소 접근
        System.out.println("첫 번째 요소: " + list.get(0));

        // 반복문으로 출력
        for (String fruit : list) {
            System.out.println(fruit);
        }
    }
}
```

**특징:**
- 배열 기반 구현으로 인덱스를 통해 빠르게 접근 가능
- 크기가 자동으로 조정됨

---

### 2. HashSet (Set 인터페이스 구현)

```java
import java.util.HashSet;

public class HashSetExample {
    public static void main(String[] args) {
        HashSet<String> set = new HashSet<>();

        // 요소 추가
        set.add("사과");
        set.add("바나나");
        set.add("사과"); // 중복된 요소 추가 시 무시

        // 반복문으로 출력
        for (String fruit : set) {
            System.out.println(fruit);
        }
    }
}
```

**특징:**
- 순서를 유지하지 않음
- 중복 요소 허용하지 않음

---

### 3. HashMap (Map 인터페이스 구현)

```java
import java.util.HashMap;

public class HashMapExample {
    public static void main(String[] args) {
        HashMap<String, Integer> map = new HashMap<>();

        // 키-값 추가
        map.put("사과", 10);
        map.put("바나나", 20);
        map.put("체리", 30);

        // 키를 사용하여 값 출력
        System.out.println("사과의 수량: " + map.get("사과"));

        // 키-값 쌍 출력
        for (String key : map.keySet()) {
            System.out.println(key + ": " + map.get(key));
        }
    }
}
```

**특징:**
- 키-값 쌍으로 데이터를 저장
- 키는 중복을 허용하지 않음

---

## 컬렉션 프레임워크의 장점

1. **코드 재사용성**: 다양한 데이터 구조를 위한 클래스 제공
2. **성능 최적화**: 효율적인 데이터 처리 알고리즘 제공
3. **표준화**: 일관된 API를 통해 작업 단순화
4. **유연성**: 다양한 요구에 따라 구현 클래스 선택 가능

---

## 결론

Java 컬렉션 프레임워크는 데이터 구조와 알고리즘을 제공하여 개발자의 생산성을 크게 향상시킵니다.  
필요에 따라 적절한 인터페이스와 클래스를 선택하여 효율적인 코드를 작성할 수 있습니다.
