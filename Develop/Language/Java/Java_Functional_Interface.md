
# Java - Functional Interface 이해

## Functional Interface란?
Functional Interface는 **단 하나의 추상 메서드만** 가지는 인터페이스를 의미합니다. Java 8부터 도입된 **람다식**과 함께 사용되며, 함수형 프로그래밍 스타일을 Java에서 구현할 수 있도록 도와줍니다.

### 주요 특징
- 단 하나의 추상 메서드만 정의 가능 (`default` 및 `static` 메서드는 여러 개 정의 가능).
- `@FunctionalInterface` 어노테이션을 사용하여 컴파일 시점에 검증 가능.
- Java 8의 기본 제공 함수형 인터페이스(`java.util.function` 패키지)와 함께 자주 사용됨.

---

## Functional Interface 예제

### 1. 직접 정의한 Functional Interface
```java
@FunctionalInterface
public interface MyFunctionalInterface {
    void execute(); // 단 하나의 추상 메서드
}
```

람다식을 사용하여 인터페이스 구현:
```java
public class FunctionalInterfaceExample {
    public static void main(String[] args) {
        // 람다식을 이용한 구현
        MyFunctionalInterface myFunction = () -> System.out.println("람다식으로 실행!");
        myFunction.execute();
    }
}
```

### 2. Java 기본 제공 함수형 인터페이스
Java 8부터 `java.util.function` 패키지에 여러 기본 함수형 인터페이스가 포함되었습니다.

#### 주요 기본 인터페이스
1. **`Function<T, R>`**
    - 입력 값을 받아서 처리 후 반환.
   ```java
   import java.util.function.Function;

   public class FunctionExample {
       public static void main(String[] args) {
           Function<String, Integer> lengthFunction = str -> str.length();
           System.out.println("문자열 길이: " + lengthFunction.apply("Hello World"));
       }
   }
   ```

2. **`Consumer<T>`**
    - 값을 받아 처리하지만 반환값이 없음.
   ```java
   import java.util.function.Consumer;

   public class ConsumerExample {
       public static void main(String[] args) {
           Consumer<String> printConsumer = str -> System.out.println("입력값: " + str);
           printConsumer.accept("Hello Functional Interface!");
       }
   }
   ```

3. **`Supplier<T>`**
    - 값을 반환하지만 입력값은 없음.
   ```java
   import java.util.function.Supplier;

   public class SupplierExample {
       public static void main(String[] args) {
           Supplier<Double> randomSupplier = () -> Math.random();
           System.out.println("랜덤 값: " + randomSupplier.get());
       }
   }
   ```

4. **`Predicate<T>`**
    - 값을 테스트하여 `true` 또는 `false`를 반환.
   ```java
   import java.util.function.Predicate;

   public class PredicateExample {
       public static void main(String[] args) {
           Predicate<Integer> isEven = num -> num % 2 == 0;
           System.out.println("짝수 여부: " + isEven.test(10));
       }
   }
   ```

---

## @FunctionalInterface 어노테이션
`@FunctionalInterface`는 컴파일러에게 해당 인터페이스가 함수형 인터페이스임을 명시합니다. 추상 메서드가 두 개 이상 정의되면 컴파일 오류가 발생합니다.

### 예제
```java
@FunctionalInterface
public interface MyFunctionalInterface {
    void execute();
    // void anotherMethod(); // 추가하면 컴파일 에러 발생
}
```

---

## 함수형 프로그래밍의 장점
1. 코드 간결성: 람다식을 사용하여 복잡한 구현을 간결하게 표현 가능.
2. 가독성 향상: 불필요한 코드를 줄여 가독성이 향상됨.
3. 병렬 처리 지원: 스트림 API와 함께 함수형 프로그래밍 스타일을 사용하면 병렬 처리 코드 작성이 쉬워짐.

---

## 결론
Functional Interface는 Java의 함수형 프로그래밍을 가능하게 하는 핵심 요소입니다. 직접 정의하거나 Java의 기본 제공 인터페이스를 활용하여 더욱 간결하고 효율적인 코드를 작성할 수 있습니다.
