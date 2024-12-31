
# Optional (옵셔널)

## Optional 개념

### Optional이란?
`Optional`은 Java 8에서 도입된 클래스이며, `null`로 인해 발생할 수 있는 `NullPointerException` 문제를 해결하기 위한 도구입니다. 객체의 존재 여부를 명시적으로 표현할 수 있어 코드의 가독성과 안정성을 높이는 데 도움을 줍니다.

### 주요 특징
- **`null`을 직접 사용하지 않도록 지원**: 안전한 대체제 제공
- **명시적 표현**: 값이 있거나 없는 상태를 명확히 표현
- **함수형 프로그래밍 지원**: `map`, `flatMap`, `filter` 등의 메서드를 제공

---

## Optional 생성 방법

1. **값이 있는 Optional 생성**
   ```java
   Optional<String> optional = Optional.of("Hello");
   ```

2. **값이 없을 때 (빈 Optional)**
   ```java
   Optional<String> emptyOptional = Optional.empty();
   ```

3. **null 허용 Optional 생성**
   ```java
   Optional<String> nullableOptional = Optional.ofNullable(null);
   ```

---

## Optional 주요 메서드

1. **isPresent() / isEmpty()**
    - 값이 존재하는지 확인
   ```java
   if (optional.isPresent()) {
       System.out.println("값이 존재합니다: " + optional.get());
   }
   ```

2. **get()**
    - 값을 반환 (값이 없으면 예외 발생)
   ```java
   String value = optional.get();
   ```

3. **orElse() / orElseGet()**
    - 값이 없을 때 기본값 제공
   ```java
   String defaultValue = optional.orElse("기본값");
   String lazyDefault = optional.orElseGet(() -> "기본값 생성");
   ```

4. **orElseThrow()**
    - 값이 없을 때 예외 던지기
   ```java
   String value = optional.orElseThrow(() -> new IllegalArgumentException("값이 없습니다."));
   ```

5. **map()**
    - 값을 변환
   ```java
   Optional<Integer> length = optional.map(String::length);
   ```

6. **filter()**
    - 조건에 따라 값을 필터링
   ```java
   Optional<String> filtered = optional.filter(val -> val.startsWith("H"));
   ```

7. **ifPresent() / ifPresentOrElse()**
    - 값이 있을 때 실행
   ```java
   optional.ifPresent(value -> System.out.println("값: " + value));

   optional.ifPresentOrElse(
       value -> System.out.println("값: " + value),
       () -> System.out.println("값이 없습니다.")
   );
   ```

---

## Optional 예제

### 기본 사용 예제
```java
import java.util.Optional;

public class OptionalExample {
    public static void main(String[] args) {
        Optional<String> optional = Optional.of("Hello Optional");

        optional.ifPresent(System.out::println);

        String value = optional.orElse("Default Value");
        System.out.println("Optional 값: " + value);

        String transformed = optional.map(String::toUpperCase).orElse("EMPTY");
        System.out.println("변환된 값: " + transformed);
    }
}
```

### NullPointerException 방지
```java
import java.util.Optional;

public class NullSafeExample {
    public static void main(String[] args) {
        String nullableValue = null;

        // null을 직접 처리
        if (nullableValue != null) {
            System.out.println(nullableValue.toUpperCase());
        }

        // Optional을 사용한 처리
        Optional<String> optional = Optional.ofNullable(nullableValue);
        optional.map(String::toUpperCase).ifPresent(System.out::println);
    }
}
```

---

## Optional 사용 시 주의점

1. **과도한 사용 지양**
    - 모든 필드나 매개변수에 Optional을 사용하는 것은 비효율적일 수 있음
    - Optional은 값의 부재를 나타내는 데 적합하며, 값 자체로 사용하는 것은 권장되지 않음

2. **컬렉션에 Optional 사용 금지**
    - Optional로 감싼 컬렉션은 중복적인 의미를 가지므로 비권장

3. **get() 사용 최소화**
    - 값이 없는 경우 예외가 발생하므로 `orElse`, `orElseThrow` 등을 사용하는 것이 더 안전함

---

## 결론

`Optional`은 값의 부재를 안전하고 명시적으로 표현할 수 있는 도구입니다. 이를 통해 `null`로 인한 문제를 줄이고, 더 명확하고 안전한 코드를 작성할 수 있습니다. 하지만 Optional의 사용 목적과 한계를 이해하고 적절히 사용하는 것이 중요합니다.
