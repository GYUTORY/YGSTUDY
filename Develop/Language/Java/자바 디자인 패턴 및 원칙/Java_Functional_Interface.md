---
title: "Java 함수형 인터페이스 실무 활용"
tags: [Java, FunctionalInterface, Spring, JDK, 실무활용]
updated: 2026-04-09
---

# Java 함수형 인터페이스 실무 활용

> 함수형 인터페이스의 기본 개념과 `java.util.function` 패키지 설명은 [Functional Interface 기초](../../객체지향 프로그래밍 (OOP)/interface/Functional_Interface.md)를 참고한다.

이 문서는 JDK와 Spring 프레임워크에서 함수형 인터페이스가 실제로 어떻게 쓰이는지, 그리고 커스텀 함수형 인터페이스를 설계할 때 어떤 점을 신경 써야 하는지를 다룬다.

---

## 1. JDK 내장 함수형 인터페이스

`java.util.function` 외에도 JDK 곳곳에 함수형 인터페이스가 숨어 있다. 대부분 Java 8 이전부터 존재했지만 람다식과 함께 쓸 수 있게 된 것들이다.

### Comparator\<T\>

정렬 로직을 분리할 때 쓴다. `java.util.function`에 속하지 않지만, 추상 메서드가 `compare(T, T)` 하나라 함수형 인터페이스다.

```java
// Java 8 이전
Collections.sort(users, new Comparator<User>() {
    @Override
    public int compare(User a, User b) {
        return a.getName().compareTo(b.getName());
    }
});

// 람다식
users.sort((a, b) -> a.getName().compareTo(b.getName()));

// Comparator 유틸리티 메서드 활용
users.sort(Comparator.comparing(User::getName));

// 여러 조건으로 정렬
users.sort(
    Comparator.comparing(User::getAge)
        .thenComparing(User::getName)
        .reversed()
);
```

`Comparator.comparing()`이 `Function<T, U>`를 받아서 `Comparator<T>`를 만들어준다. 직접 비교 로직을 짜는 것보다 이 방식을 쓰는 게 실수가 적다. `a - b` 같은 산술 비교는 오버플로우 위험이 있어서 `Integer.compare(a, b)`나 `Comparator.comparingInt()`를 써야 한다.

```java
// 이런 코드는 오버플로우가 날 수 있다
users.sort((a, b) -> a.getAge() - b.getAge());

// 이렇게 한다
users.sort(Comparator.comparingInt(User::getAge));
```

### Callable\<V\>

`Runnable`과 비슷하지만 반환값이 있고 체크 예외를 던질 수 있다. `ExecutorService`에서 비동기 작업을 제출할 때 쓴다.

```java
ExecutorService executor = Executors.newFixedThreadPool(4);

// Callable<String>을 람다식으로
Future<String> future = executor.submit(() -> {
    Thread.sleep(1000);
    return "작업 완료";
});

String result = future.get();  // 블로킹 대기
```

`Supplier<T>`와 시그니처가 비슷한데, `Callable`은 `throws Exception`이 선언되어 있다는 점이 다르다. 체크 예외를 던져야 하는 비동기 작업에서는 `Callable`을 쓴다.

```java
// Supplier<T>: T get()              — 체크 예외 불가
// Callable<V>: V call() throws Exception — 체크 예외 가능
```

### Runnable

스레드 실행 단위로 쓰이는 가장 오래된 함수형 인터페이스다. `() -> void` 시그니처를 갖는다.

```java
// 스레드 생성
new Thread(() -> System.out.println("별도 스레드")).start();

// CompletableFuture
CompletableFuture.runAsync(() -> {
    // 비동기로 실행할 코드
    sendNotification(userId);
});
```

### FileFilter / FilenameFilter

파일 I/O에서 쓴다. `Predicate`와 비슷한 역할인데, 파일 시스템 API에 특화된 인터페이스다.

```java
File dir = new File("/logs");

// Java 8 이전
File[] logs = dir.listFiles(new FileFilter() {
    @Override
    public boolean accept(File f) {
        return f.getName().endsWith(".log");
    }
});

// 람다식
File[] logs = dir.listFiles(f -> f.getName().endsWith(".log"));
```

---

## 2. Spring에서의 함수형 인터페이스

Spring 프레임워크는 콜백 패턴을 많이 쓰는데, 이 콜백들 대부분이 함수형 인터페이스다.

### JdbcTemplate 콜백

`JdbcTemplate`의 콜백 인터페이스들은 함수형 인터페이스로 되어 있다.

```java
// RowMapper<T> — ResultSet의 각 행을 객체로 변환
List<User> users = jdbcTemplate.query(
    "SELECT id, name, email FROM users WHERE active = ?",
    (rs, rowNum) -> new User(
        rs.getLong("id"),
        rs.getString("name"),
        rs.getString("email")
    ),
    true
);

// ResultSetExtractor<T> — ResultSet 전체를 하나의 결과로 변환
Map<Long, List<Order>> ordersByUser = jdbcTemplate.query(
    "SELECT user_id, order_id, amount FROM orders",
    rs -> {
        Map<Long, List<Order>> map = new HashMap<>();
        while (rs.next()) {
            long userId = rs.getLong("user_id");
            Order order = new Order(rs.getLong("order_id"), rs.getInt("amount"));
            map.computeIfAbsent(userId, k -> new ArrayList<>()).add(order);
        }
        return map;
    }
);
```

`RowMapper`와 `ResultSetExtractor`의 차이를 모르고 쓰면 혼란이 생긴다. `RowMapper`는 행 단위로 호출되고, `ResultSetExtractor`는 `ResultSet` 전체를 직접 순회해야 한다. 단순 매핑은 `RowMapper`, 그루핑이나 집계가 필요하면 `ResultSetExtractor`를 쓴다.

```java
// PreparedStatementSetter — 파라미터 바인딩
jdbcTemplate.update(
    "UPDATE users SET name = ? WHERE id = ?",
    ps -> {
        ps.setString(1, "홍길동");
        ps.setLong(2, 1L);
    }
);
```

### TransactionTemplate 콜백

프로그래밍 방식의 트랜잭션 관리에서 `TransactionCallback<T>`을 쓴다.

```java
@RequiredArgsConstructor
@Service
public class OrderService {

    private final TransactionTemplate transactionTemplate;
    private final OrderRepository orderRepository;

    public Order createOrder(OrderRequest request) {
        return transactionTemplate.execute(status -> {
            Order order = Order.from(request);
            orderRepository.save(order);

            if (order.getAmount() > 1_000_000) {
                status.setRollbackOnly();  // 조건부 롤백
                return null;
            }
            return order;
        });
    }
}
```

`@Transactional`을 쓰면 되는 상황에서 굳이 `TransactionTemplate`을 쓸 필요는 없다. 하나의 메서드 안에서 트랜잭션 범위를 세밀하게 나눠야 할 때 사용한다.

### EventListener

Spring의 이벤트 처리에서 함수형 인터페이스 패턴이 쓰인다.

```java
// ApplicationListener<E>는 함수형 인터페이스
@Bean
public ApplicationListener<OrderCreatedEvent> orderEventListener() {
    return event -> {
        log.info("주문 생성됨: {}", event.getOrderId());
        notificationService.sendOrderConfirmation(event);
    };
}
```

실무에서는 `@EventListener` 어노테이션을 더 많이 쓰지만, 이벤트 리스너를 동적으로 등록해야 하는 경우에 이 방식이 필요하다.

### WebFlux 함수형 엔드포인트

Spring WebFlux의 함수형 라우팅 모델은 함수형 인터페이스를 기반으로 한다.

```java
// HandlerFunction<T>: ServerRequest → Mono<ServerResponse>
// RouterFunction<T>: ServerRequest → Mono<HandlerFunction<T>>

@Configuration
public class RouterConfig {

    @Bean
    public RouterFunction<ServerResponse> routes(UserHandler handler) {
        return RouterFunctions.route()
            .GET("/users/{id}", handler::getUser)
            .GET("/users", handler::listUsers)
            .POST("/users", handler::createUser)
            .filter((request, next) -> {
                log.info("요청: {} {}", request.method(), request.path());
                return next.handle(request);
            })
            .build();
    }
}

@Component
public class UserHandler {

    public Mono<ServerResponse> getUser(ServerRequest request) {
        String id = request.pathVariable("id");
        return userService.findById(id)
            .flatMap(user -> ServerResponse.ok().bodyValue(user))
            .switchIfEmpty(ServerResponse.notFound().build());
    }
}
```

`HandlerFunction`은 `Function<ServerRequest, Mono<ServerResponse>>`와 사실상 같다. 어노테이션 기반 `@RestController`와 기능 차이는 없지만, 라우팅 로직을 코드로 직접 조합할 수 있다는 점이 다르다. 라우트가 동적으로 변해야 하거나, 라우팅 자체에 조건 분기가 복잡한 경우에 함수형 엔드포인트가 유리하다.

### RestClient / WebClient 콜백

Spring 6의 `RestClient`에서도 함수형 인터페이스 패턴이 보인다.

```java
RestClient restClient = RestClient.create();

// ResponseSpec의 body()에 ParameterizedTypeReference 대신
// exchange()를 쓰면 응답 처리를 직접 제어할 수 있다
String result = restClient.get()
    .uri("https://api.example.com/data")
    .exchange((request, response) -> {
        if (response.getStatusCode().is4xxClientError()) {
            throw new CustomApiException("API 호출 실패: " + response.getStatusCode());
        }
        return response.bodyTo(String.class);
    });
```

---

## 3. 커스텀 함수형 인터페이스 설계

### 만들기 전에 확인할 것

커스텀 함수형 인터페이스를 만들기 전에 `java.util.function`에 이미 있는지 확인한다. 대부분의 경우 기존 인터페이스로 충분하다.

| 하려는 것 | 이미 있는 인터페이스 |
|---|---|
| 값 변환 | `Function<T, R>` |
| 조건 검사 | `Predicate<T>` |
| 값 소비 | `Consumer<T>` |
| 값 생성 | `Supplier<T>` |
| 두 값으로 하나 만들기 | `BiFunction<T, U, R>` |
| 같은 타입 입출력 | `UnaryOperator<T>` |

커스텀 인터페이스를 만드는 게 맞는 경우는 다음과 같다.

- 체크 예외를 던져야 할 때
- 파라미터가 3개 이상일 때
- 도메인 의미를 명확히 드러내야 할 때

### 체크 예외를 던지는 함수형 인터페이스

`java.util.function`의 인터페이스들은 체크 예외를 선언하지 않는다. DB 접근이나 파일 I/O처럼 체크 예외가 발생하는 코드를 람다로 쓰려면 직접 만들어야 한다.

```java
@FunctionalInterface
public interface ThrowingFunction<T, R, E extends Exception> {
    R apply(T t) throws E;
}
```

이걸 `Function<T, R>`으로 변환하는 유틸리티를 같이 만들어두면 편하다.

```java
public class LambdaUtils {

    public static <T, R> Function<T, R> unchecked(ThrowingFunction<T, R, ?> f) {
        return t -> {
            try {
                return f.apply(t);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        };
    }
}

// 사용
List<String> contents = filePaths.stream()
    .map(LambdaUtils.unchecked(path -> Files.readString(Path.of(path))))
    .toList();
```

주의할 점: `RuntimeException`으로 감싸면 호출자가 예외 처리를 놓칠 수 있다. 예외가 발생했을 때 어떻게 처리할지 명확한 상황에서만 이 패턴을 쓴다. 예외 처리가 중요한 로직이면 람다식 안에서 직접 try-catch 하는 게 낫다.

### 도메인 의미를 드러내는 인터페이스

`Function<Order, BigDecimal>` 같은 타입은 코드만 봐서는 무슨 역할인지 알기 어렵다. 도메인 의미가 중요한 경우 커스텀 인터페이스를 만든다.

```java
@FunctionalInterface
public interface PricingPolicy {
    BigDecimal calculatePrice(Order order);
}
```

```java
public class PricingPolicies {

    public static PricingPolicy standard() {
        return order -> order.getItems().stream()
            .map(item -> item.getPrice().multiply(BigDecimal.valueOf(item.getQuantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    public static PricingPolicy discounted(BigDecimal rate) {
        return order -> standard().calculatePrice(order)
            .multiply(BigDecimal.ONE.subtract(rate));
    }
}
```

```java
@Service
public class OrderService {

    public BigDecimal calculate(Order order, PricingPolicy policy) {
        return policy.calculatePrice(order);
    }
}

// 호출
BigDecimal price = orderService.calculate(order, PricingPolicies.discounted(new BigDecimal("0.1")));
```

이 방식의 장점은 타입 시그니처만으로 의도가 드러난다는 것이다. `Function<Order, BigDecimal>`을 파라미터로 받으면 "주문을 받아서 BigDecimal을 반환하는 함수"라는 정보밖에 없지만, `PricingPolicy`를 받으면 "가격 정책"이라는 의미가 명확하다.

### default 메서드로 조합 지원

함수형 인터페이스에 `default` 메서드를 추가하면 조합이 가능해진다. `Predicate`의 `and()`, `or()`, `negate()` 같은 패턴이다.

```java
@FunctionalInterface
public interface Validator<T> {
    ValidationResult validate(T target);

    default Validator<T> and(Validator<T> other) {
        return target -> {
            ValidationResult result = this.validate(target);
            if (result.isFailed()) {
                return result;
            }
            return other.validate(target);
        };
    }
}
```

```java
Validator<Order> amountCheck = order -> {
    if (order.getAmount() <= 0) {
        return ValidationResult.fail("주문 금액은 0보다 커야 한다");
    }
    return ValidationResult.ok();
};

Validator<Order> itemCheck = order -> {
    if (order.getItems().isEmpty()) {
        return ValidationResult.fail("주문 항목이 비어 있다");
    }
    return ValidationResult.ok();
};

Validator<Order> fullValidator = amountCheck.and(itemCheck);
ValidationResult result = fullValidator.validate(order);
```

`default` 메서드를 너무 많이 넣으면 인터페이스가 비대해진다. 조합이 실제로 필요한 경우에만 추가한다.

---

## 4. 주의할 점 정리

### 람다식 디버깅

람다식은 스택 트레이스에서 `lambda$메서드명$0` 같은 이름으로 나온다. 람다가 중첩되면 어디서 에러가 났는지 찾기 어렵다.

```
java.lang.NullPointerException
    at com.example.OrderService.lambda$process$0(OrderService.java:25)
    at java.util.stream.ReferencePipeline$3$1.accept(ReferencePipeline.java:197)
```

복잡한 로직이면 람다식 대신 메서드 참조나 별도 메서드로 분리한다. 스택 트레이스가 읽기 쉬워진다.

```java
// 디버깅하기 어려움
orders.stream()
    .map(order -> {
        // 20줄짜리 변환 로직
    })
    .collect(toList());

// 디버깅하기 편함
orders.stream()
    .map(this::toOrderDto)
    .collect(toList());

private OrderDto toOrderDto(Order order) {
    // 20줄짜리 변환 로직 — 메서드 이름이 스택 트레이스에 나옴
}
```

### 타입 추론 실패

컴파일러가 타입을 추론하지 못하는 경우가 있다. 오버로딩된 메서드에 람다식을 넘길 때 자주 발생한다.

```java
// 오버로딩된 메서드
void process(Function<String, String> f) { }
void process(UnaryOperator<String> f) { }

// 컴파일 에러: 어떤 process를 호출할지 모호함
process(s -> s.toUpperCase());

// 명시적 캐스팅으로 해결
process((Function<String, String>) s -> s.toUpperCase());

// 또는 변수에 타입을 명시
Function<String, String> upper = s -> s.toUpperCase();
process(upper);
```

메서드 오버로딩을 설계할 때 함수형 인터페이스 파라미터가 겹치지 않도록 신경 써야 한다. 시그니처가 같은 함수형 인터페이스를 두 개의 오버로딩에 쓰면 호출하는 쪽에서 항상 캐스팅이 필요해진다.

### 성능 관련

람다식은 내부적으로 `invokedynamic`을 사용해서 익명 클래스보다 초기화 비용이 낮다. 매번 새로운 클래스를 만드는 게 아니라 런타임에 한 번만 바이트코드를 생성한다.

다만 상태를 캡처하는 람다식(외부 변수를 참조하는 경우)은 매 호출마다 새 인스턴스가 생긴다. 상태를 캡처하지 않는 람다식은 싱글턴으로 재사용된다.

```java
// 캡처 없음 — 싱글턴으로 재사용됨
Function<String, String> upper = String::toUpperCase;

// 캡처 있음 — 매번 새 인스턴스
String prefix = getPrefix();
Function<String, String> addPrefix = s -> prefix + s;
```

성능 차이가 체감되는 경우는 거의 없다. 다만 루프 안에서 매번 같은 람다식을 생성하는 코드가 있으면, 루프 밖으로 빼는 게 좋다.
