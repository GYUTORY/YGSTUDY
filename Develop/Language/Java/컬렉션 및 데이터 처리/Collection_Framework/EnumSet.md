---
title: Enum EnumSet EnumMap
tags: [language, java, 컬렉션-및-데이터-처리, collectionframework, enumset]
updated: 2025-08-10
---

# Enum과 EnumSet/EnumMap

## Enum 개념

### Enum이란?
`Enum`은 열거형(Enum type)으로, 서로 연관된 상수들의 집합을 정의할 때 사용됩니다. 상수를 보다 읽기 쉽고 안전하게 사용할 수 있도록 제공되며, Java에서는 `enum` 키워드를 사용해 정의합니다.

## 배경
- **타입 안전성 제공**: 잘못된 값을 컴파일 단계에서 방지 가능
- **코드 가독성 향상**: 상수들의 의미를 명확하게 표현
- **내장 메서드 제공**: `values()`, `ordinal()`, `name()` 등의 메서드

```java
public enum Day {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY;
}

public class EnumExample {
    public static void main(String[] args) {
        Day today = Day.WEDNESDAY;
        System.out.println("Today is: " + today);

        for (Day day : Day.values()) {
            System.out.println(day + " at position " + day.ordinal());
        }
    }
}
```

---

- Enum 값만 저장 가능
- 순서 보장 (Enum 선언 순서)
- null 값 허용하지 않음

```java
import java.util.EnumSet;

public enum Day {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY;
}

public class EnumSetExample {
    public static void main(String[] args) {
        EnumSet<Day> weekend = EnumSet.of(Day.SATURDAY, Day.SUNDAY);
        System.out.println("Weekend: " + weekend);

        EnumSet<Day> weekdays = EnumSet.complementOf(weekend);
        System.out.println("Weekdays: " + weekdays);
    }
}
```

---

- Enum 값만 키로 사용 가능
- null 키 허용하지 않음
- 순서 보장 (Enum 선언 순서)

```java
import java.util.EnumMap;

public enum Day {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY;
}

public class EnumMapExample {
    public static void main(String[] args) {
        EnumMap<Day, String> schedule = new EnumMap<>(Day.class);

        schedule.put(Day.MONDAY, "Gym");
        schedule.put(Day.TUESDAY, "Swimming");
        schedule.put(Day.WEDNESDAY, "Work");
        schedule.put(Day.THURSDAY, "Study");
        schedule.put(Day.FRIDAY, "Relax");

        System.out.println("Schedule: " + schedule);
    }
}
```

---


| 특징          | EnumSet                        | EnumMap                        |
|---------------|--------------------------------|--------------------------------|
| 내부 구현      | 비트 벡터                     | 배열                           |
| 저장 가능한 값 | Enum 값(Set 형태로 저장)       | Enum 값을 키로 하는 (Key-Value)|
| null 허용      | 불허                          | 키는 불허, 값은 허용           |
| 순서          | Enum 선언 순서 유지            | Enum 선언 순서 유지            |

---


`Enum`, `EnumSet`, 그리고 `EnumMap`은 각각 열거형 데이터를 효율적으로 다루기 위한 도구입니다.
- `Enum`: 열거형 상수를 정의하여 타입 안정성을 제공
- `EnumSet`: Enum 집합 데이터를 처리하는 고성능 Set
- `EnumMap`: Enum을 키로 사용하여 고성능 Map 생성

적절한 상황에 맞게 이 도구들을 활용하면 코드의 가독성과 효율성을 크게 향상시킬 수 있습니다.










## EnumSet

### EnumSet이란?
`EnumSet`은 Enum 값만을 위한 고성능의 집합(Set) 구현체입니다. 내부적으로 비트 벡터를 사용하여 효율적이고 빠르게 동작합니다.

## EnumMap

### EnumMap이란?
`EnumMap`은 Enum 값을 키로 사용하는 고성능의 Map 구현체입니다. 내부적으로 배열을 사용하여 빠르고 메모리 효율적으로 동작합니다.

