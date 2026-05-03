---
title: "Java 예외 처리"
tags: [java, exception, error-handling, try-with-resources]
updated: 2026-05-03
---

# Java 예외 처리

## Throwable / Error / Exception 계층

Java의 모든 던질 수 있는(throwable) 객체는 `java.lang.Throwable`을 상속한다. 두 갈래로 나뉜다.

```
Throwable
├── Error                              → JVM 레벨 문제 (잡으면 안 됨)
│   ├── OutOfMemoryError
│   ├── StackOverflowError
│   └── NoClassDefFoundError
└── Exception
    ├── IOException, SQLException ...   → Checked Exception
    └── RuntimeException                 → Unchecked Exception
        ├── NullPointerException
        ├── IllegalArgumentException
        ├── IllegalStateException
        └── IndexOutOfBoundsException
```

`Error`는 애플리케이션이 복구할 수 없는 상황이다. `OutOfMemoryError`가 발생한 시점에 catch해서 뭔가 처리하려 해도 그 처리 코드 자체가 추가 메모리를 요구할 가능성이 크다. 그래서 `Error`는 잡으면 안 되고, `catch (Throwable t)`도 쓰면 안 된다. 굳이 잡고 싶다면 로그만 남기고 즉시 다시 던지거나 프로세스를 종료시키는 정도가 한계다.

한 가지 예외는 프레임워크 코드다. 톰캣처럼 요청당 스레드가 도는 환경에서는 워커 스레드가 죽어도 다른 요청은 살아남아야 하니 최상단에서 `Throwable`까지 잡아 로깅한 뒤 스레드만 정리하는 패턴이 존재한다. 일반 비즈니스 코드에서 따라할 게 아니다.

`Throwable`이 최상위인 이유는 `getStackTrace()`, `getCause()`, `addSuppressed()` 같은 메서드가 모두 여기에 정의돼 있기 때문이다. catch 블록에서 다루는 모든 객체는 결국 `Throwable`이다.

## Checked vs Unchecked

### Checked Exception

컴파일러가 처리를 강제한다. `throws` 선언이나 `try-catch`가 없으면 컴파일 에러다.

```java
public String readFile(String path) throws IOException {
    return Files.readString(Path.of(path));
}
```

Checked Exception은 "호출자가 의미 있게 복구할 수 있는 상황"에 쓴다. 파일이 없으면 다른 경로를 시도하거나, 네트워크가 끊기면 재시도하는 식이다.

### Unchecked Exception

`RuntimeException`의 하위 클래스다. 컴파일러가 강제하지 않는다.

```java
public User findById(Long id) {
    if (id == null) {
        throw new IllegalArgumentException("id는 null일 수 없다");
    }
    return userRepository.findById(id)
            .orElseThrow(() -> new NoSuchElementException("존재하지 않는 사용자: " + id));
}
```

프로그래밍 오류(잘못된 인자, null 참조, 잘못된 상태 전이)에 해당한다. 호출자가 매번 `try-catch`로 감싸는 건 의미가 없다.

### 실무에서의 선택 기준

Spring 기반 웹 애플리케이션에서는 거의 Unchecked Exception만 쓴다. 이유는 단순하다.

1. 컨트롤러 → 서비스 → 리포지토리 체인에서 Checked Exception을 던지면 모든 레이어에 `throws`가 전파된다
2. 결국 대부분의 예외는 `@ExceptionHandler`에서 HTTP 응답으로 변환한다
3. 복구 불가능한 상황이 대부분이라 catch해봐야 할 수 있는 게 없다

```java
// 서비스 인터페이스가 구현 기술(JDBC)에 종속되는 잘못된 패턴
public interface UserService {
    User findById(Long id) throws SQLException;
}
```

만약 인터페이스에 `throws SQLException`이 박히면 구현체를 MongoDB로 바꾸는 순간 인터페이스 시그니처가 무너진다. Spring의 `JdbcTemplate`이 `SQLException`을 `DataAccessException`(RuntimeException)으로 번역해 던지는 이유다.

## try-with-resources

Java 7에서 추가됐다. `AutoCloseable`을 구현한 리소스를 자동으로 닫아준다.

### 기본 사용법

```java
try (BufferedReader reader = new BufferedReader(new FileReader(path))) {
    String line;
    while ((line = reader.readLine()) != null) {
        process(line);
    }
} catch (IOException e) {
    log.error("파일 읽기 실패: {}", path, e);
}
```

### 동작 원리

`try-with-resources`는 컴파일러가 try-finally 형태로 변환한다. 위 코드는 대략 이런 바이트코드를 만든다.

```java
BufferedReader reader = new BufferedReader(new FileReader(path));
Throwable primary = null;
try {
    String line;
    while ((line = reader.readLine()) != null) {
        process(line);
    }
} catch (Throwable t) {
    primary = t;
    throw t;
} finally {
    if (reader != null) {
        if (primary != null) {
            try {
                reader.close();
            } catch (Throwable suppressed) {
                primary.addSuppressed(suppressed);  // 핵심
            }
        } else {
            reader.close();
        }
    }
}
```

핵심은 `addSuppressed()`다. 이전의 try-finally 방식에서는 close()에서 예외가 나면 try 본문의 원래 예외를 덮어써서 디버깅이 어려웠다. try-with-resources는 원래 예외를 살리고 close 예외는 suppressed에 붙인다.

### 여러 리소스

```java
try (
    Connection conn = dataSource.getConnection();
    PreparedStatement stmt = conn.prepareStatement(sql);
    ResultSet rs = stmt.executeQuery()
) {
    while (rs.next()) {
        // 처리
    }
}
// rs → stmt → conn 순서로 닫힌다 (선언의 역순)
```

선언의 역순으로 닫는 이유는 자원 의존성 때문이다. `ResultSet`은 `PreparedStatement`에 종속이고, `PreparedStatement`는 `Connection`에 종속이다. 부모 자원을 먼저 닫으면 자식이 좀비가 된다.

### Java 9의 effectively final 지원

Java 9부터는 try 헤더 바깥에서 선언된 변수도 `effectively final`이면 그대로 쓸 수 있다.

```java
BufferedReader reader = new BufferedReader(new FileReader(path));
try (reader) {
    // ...
}
```

이 형태는 자원 생성과 try 사용 시점이 분리되는 경우(생성자 인자로 받은 리소스 등)에 유용하다.

### 직접 만든 클래스에 적용

```java
public class DatabaseTransaction implements AutoCloseable {
    private final Connection conn;
    private boolean committed = false;

    public DatabaseTransaction(DataSource ds) throws SQLException {
        this.conn = ds.getConnection();
        this.conn.setAutoCommit(false);
    }

    public void commit() throws SQLException {
        conn.commit();
        committed = true;
    }

    @Override
    public void close() throws SQLException {
        try {
            if (!committed) {
                conn.rollback();
            }
        } finally {
            conn.close();
        }
    }
}

try (DatabaseTransaction tx = new DatabaseTransaction(dataSource)) {
    userRepository.save(conn, user);
    orderRepository.save(conn, order);
    tx.commit();
}
```

`close()` 안에서도 try-finally를 쓴 이유는 rollback이 실패해도 connection은 반드시 닫혀야 하기 때문이다. 커넥션 누수가 생기면 풀이 고갈돼서 서비스 전체가 멈춘다.

## 예외 체이닝

원인 예외(`cause`)를 함께 넘기는 패턴이다. `Throwable`의 두 번째 인자가 `cause`다.

```java
try {
    externalApi.call();
} catch (HttpClientException e) {
    throw new PaymentFailedException("결제 API 호출 실패", e);
}
```

스택 트레이스에 `Caused by:` 섹션이 추가된다.

```
PaymentFailedException: 결제 API 호출 실패
    at com.example.PaymentService.process(PaymentService.java:42)
    ...
Caused by: HttpClientException: 503 Service Unavailable
    at com.example.HttpClient.send(HttpClient.java:118)
    ...
```

`cause`를 누락하면 진짜 원인이 어디인지 알 수 없다. 운영 장애 분석에서 가장 답답한 상황이 이거다. "결제 실패"라는 메시지만 보고 무엇이 실패했는지 추적할 수 없다.

체이닝은 두 가지로 갈린다.

- **원인 예외가 디버깅에 필요하면** `cause`를 넘긴다 (DB 에러, 외부 API 에러)
- **원인 예외가 구현 세부사항이고 호출자에게 노출되면 안 되면** 넘기지 않을 수도 있다 (빈 결과를 도메인 예외로 변환)

JDK 자체도 체이닝을 지원하지 않던 시절(Java 1.3 이전)에는 `cause`를 출력하려면 별도 메서드를 직접 만들어야 했다. Java 1.4부터 `Throwable`에 정식 도입됐다.

## 멀티 catch

Java 7부터 `|` 연산자로 여러 예외를 한 catch 블록에서 처리할 수 있다.

```java
try {
    Class.forName(className).getDeclaredConstructor().newInstance();
} catch (ClassNotFoundException | NoSuchMethodException
       | InstantiationException | IllegalAccessException e) {
    throw new ReflectionException("리플렉션 호출 실패: " + className, e);
}
```

처리 로직이 동일한데 예외 타입만 여러 개일 때 코드 중복을 없앨 수 있다.

### 제약 사항

멀티 catch에서 예외 변수는 암묵적으로 `final`이다. 재할당이 불가능하다.

```java
} catch (IOException | SQLException e) {
    e = new RuntimeException();  // 컴파일 에러
}
```

또한 부모-자식 관계인 예외는 함께 쓸 수 없다.

```java
} catch (IOException | FileNotFoundException e) {  // 컴파일 에러
    // FileNotFoundException은 IOException의 하위 클래스
}
```

### 멀티 catch에서 변수 타입

`e`의 정적 타입은 가장 가까운 공통 부모 타입이 된다. 위 예시에서는 `Exception`이 된다. 그래서 `IOException`이나 `SQLException`에만 있는 메서드를 호출하려면 `instanceof`로 구분해야 한다. 이런 상황이라면 멀티 catch가 아니라 별도 catch로 분리하는 게 맞다.

## 예외 재던지기

catch한 예외를 다시 던지는 패턴이다. 로깅, 변환, 부분 처리 후 위로 전파해야 할 때 쓴다.

### 같은 예외 그대로 던지기

```java
public void process() throws IOException {
    try {
        doWork();
    } catch (IOException e) {
        metrics.increment("io.error");
        throw e;  // 메트릭만 남기고 그대로 던짐
    }
}
```

Java 6까지는 catch 변수의 정적 타입이 그대로 `throws`에 전파됐다. catch (Exception e)로 잡으면 무조건 throws Exception을 선언해야 했다.

### Java 7의 더 정밀한 재던지기

Java 7부터 컴파일러가 catch 블록 안에서 실제로 던질 수 있는 예외 타입을 추론한다.

```java
public void process() throws IOException, SQLException {  // Exception 아님
    try {
        readFile();   // throws IOException
        querySql();   // throws SQLException
    } catch (Exception e) {
        log.error("처리 실패", e);
        throw e;  // IOException 또는 SQLException으로 추론됨
    }
}
```

`catch (Exception e)`로 잡았어도 try 본문에서 실제로 발생 가능한 예외가 `IOException`과 `SQLException` 둘 뿐이라면, throws 절에 그 둘만 적어도 된다. 컴파일러가 흐름 분석을 한다. 단, catch 변수에 다른 값을 재할당하면 이 추론이 깨진다.

### 변환해서 던지기

```java
} catch (SQLException e) {
    throw new DataAccessException("쿼리 실행 실패: " + sql, e);
}
```

이 경우 원본 `SQLException`을 `cause`로 넘겨야 한다. 그렇지 않으면 진짜 원인 정보가 사라진다.

### 재던지기와 로깅의 충돌

```java
try {
    process();
} catch (Exception e) {
    log.error("처리 실패", e);  // 여기서 한번
    throw e;                    // 상위에서 또 한번
}
```

같은 예외가 로그에 여러 번 찍힌다. 운영 환경에서 동일 에러가 5단계에 걸쳐 5번 로깅되면 ELK에서 같은 에러로 보일지 다른 에러로 보일지 헷갈린다. 원칙은 하나다.

- 다시 던진다 → 로그를 남기지 않는다 (최종 핸들러에서만 로깅)
- 로그를 남긴다 → 다시 던지지 않는다 (여기서 처리가 끝남)

## finally 블록의 함정

`finally`는 try 블록이 어떻게 끝나든(정상 리턴, 예외, break, continue) 반드시 실행된다. 이 강제성이 함정의 원인이 된다.

### return 충돌

`finally`에 `return`이 있으면 try의 `return`을 덮어쓴다.

```java
public int compute() {
    try {
        return 1;
    } finally {
        return 2;  // 이게 리턴된다
    }
}
// 호출 결과: 2
```

더 위험한 건 try가 예외를 던지는 상황이다.

```java
public int compute() {
    try {
        throw new RuntimeException("실패");
    } finally {
        return -1;  // 예외가 사라지고 -1이 리턴된다
    }
}
```

`finally`의 `return`이 try의 예외를 삼켜버린다. 호출자는 에러를 모른 채 `-1`을 받는다. 운영 환경에서 가장 추적하기 어려운 종류의 버그다. `finally`에서는 절대 `return`을 쓰지 않는다.

### finally에서 예외 던지기

```java
try {
    return process();  // RuntimeException("A") 발생
} finally {
    cleanup();          // RuntimeException("B") 발생
}
// 호출자는 "B"만 받는다. "A"는 사라진다.
```

`finally`에서 던진 예외가 try의 예외를 덮어쓴다. try-with-resources가 `addSuppressed()`로 해결하는 문제를 finally는 그냥 잃어버린다. cleanup 코드는 자체적으로 try-catch로 방어해야 한다.

```java
try {
    return process();
} finally {
    try {
        cleanup();
    } catch (Exception cleanupError) {
        log.warn("정리 작업 실패", cleanupError);
    }
}
```

### finally에서 try의 지역 변수 변경

```java
public int getValue() {
    int result = 10;
    try {
        return result;  // 이미 10이 리턴값으로 결정됨
    } finally {
        result = 20;    // 영향 없음. 여전히 10이 리턴된다
    }
}
```

원시 타입은 try의 `return result`가 실행되는 시점에 값이 복사된다. 하지만 객체 참조의 경우 참조 자체는 동일하므로, 객체 내부 상태를 변경하면 호출자가 받는 객체에도 반영된다.

```java
public List<String> getList() {
    List<String> list = new ArrayList<>();
    list.add("a");
    try {
        return list;
    } finally {
        list.add("b");  // 호출자는 ["a", "b"]를 받는다
    }
}
```

이런 코드는 의도적으로 쓰면 안 된다. 디버깅이 거의 불가능하다.

## 커스텀 예외 설계

### 기본 구조

```java
public class OrderNotFoundException extends RuntimeException {

    private final Long orderId;

    public OrderNotFoundException(Long orderId) {
        super("주문을 찾을 수 없음: " + orderId);
        this.orderId = orderId;
    }

    public Long getOrderId() {
        return orderId;
    }
}
```

`orderId`를 필드로 들고 있는 이유는 `@ExceptionHandler`에서 응답 본문에 ID를 넣거나, 메트릭 태그로 쓸 때 유용하기 때문이다. 메시지를 정규식으로 파싱해서 ID를 빼내는 코드는 만들면 안 된다.

### 계층 구조 설계

도메인별로 최상위 예외를 두고 하위에 구체적인 예외를 만든다.

```java
public abstract class OrderException extends RuntimeException {
    protected OrderException(String message) {
        super(message);
    }
    protected OrderException(String message, Throwable cause) {
        super(message, cause);
    }
}

public class OrderNotFoundException extends OrderException {
    public OrderNotFoundException(Long id) {
        super("주문을 찾을 수 없음: " + id);
    }
}

public class OrderAlreadyCancelledException extends OrderException {
    public OrderAlreadyCancelledException(Long id) {
        super("이미 취소된 주문: " + id);
    }
}
```

`@ExceptionHandler(OrderException.class)`로 한번에 잡으면서 필요한 곳에서는 구체 타입으로 골라 잡을 수 있다.

### 커스텀 예외를 만들어야 하는 경우

아무 때나 만들면 클래스만 늘어난다. 다음 조건 중 하나에 해당할 때만 만든다.

- 예외에 추가 정보(주문 ID, 실패 사유 코드 등)를 담아야 할 때
- 특정 예외만 골라서 catch해야 할 때
- HTTP 상태 코드를 다르게 매핑해야 할 때

단순히 메시지만 다르면 `IllegalStateException`이나 `IllegalArgumentException`으로 충분하다. JDK 표준 예외를 쓰는 게 별도 클래스를 만드는 것보다 가독성이 좋다.

### 스택 트레이스 비활성화

성능에 민감한 경로에서 흐름 제어용 예외를 던질 일이 있다면 스택 트레이스 생성을 끌 수 있다.

```java
public class FastException extends RuntimeException {
    public FastException(String message) {
        super(message, null, false, false);  // writableStackTrace = false
    }
}
```

스택 트레이스 생성이 예외 비용의 대부분이다. 끄면 거의 공짜로 쓸 수 있다. 이름을 `FastException`처럼 짓고 명시적으로 표시해 쓴다. 일반 비즈니스 예외에는 적용하지 않는다.

## NullPointerException 처리 패턴

NPE는 가장 자주 마주치는 런타임 예외다. catch로 처리할 게 아니라 발생 자체를 막는 게 원칙이다.

### Optional로 null 가능성 표현

```java
public Optional<User> findById(Long id) {
    return Optional.ofNullable(userMap.get(id));
}

User user = findById(id)
        .orElseThrow(() -> new UserNotFoundException(id));
```

`Optional`은 리턴 타입에만 쓴다. 필드, 매개변수에는 쓰지 않는다. 컬렉션에는 쓰지 않는다(빈 컬렉션을 리턴하면 된다).

### Objects.requireNonNull로 빠르게 실패

```java
public OrderService(UserRepository userRepository, ProductRepository productRepository) {
    this.userRepository = Objects.requireNonNull(userRepository, "userRepository는 null일 수 없다");
    this.productRepository = Objects.requireNonNull(productRepository, "productRepository는 null일 수 없다");
}
```

생성자에서 null을 검증하면 객체가 잘못된 상태로 만들어지는 것 자체를 막는다. 나중에 메서드를 호출할 때 NPE가 나는 것보다 생성 시점에 실패하는 게 디버깅이 훨씬 쉽다.

### 컬렉션은 빈 컬렉션으로 리턴

```java
public List<Order> findByUserId(Long userId) {
    if (userId == null) {
        return Collections.emptyList();  // null이 아니라 빈 리스트
    }
    return orderRepository.findByUserId(userId);
}
```

호출자가 매번 null 체크를 하지 않아도 된다. `for (Order o : findByUserId(id))`가 안전하게 동작한다.

### Java 14+의 도움말 NPE

Java 14부터 `-XX:+ShowCodeDetailsInExceptionMessages`(JDK 15부터 기본 활성화)가 적용되면 NPE 메시지가 친절해진다.

```
java.lang.NullPointerException: Cannot invoke "User.getEmail()" because "user" is null
```

어떤 변수가 null이었는지 알려준다. JDK 14 이전에는 `NullPointerException`만 적혀 있어서 디스어셈블링하지 않으면 어느 위치인지 추측해야 했다.

### NPE를 catch하면 안 되는 경우

```java
// 이런 코드는 안티패턴이다
try {
    return user.getProfile().getEmail();
} catch (NullPointerException e) {
    return "unknown";
}
```

`user`가 null인지 `profile`이 null인지 모른 채로 처리한다. `Optional` 체이닝이나 명시적 null 체크로 바꿔야 한다.

```java
return Optional.ofNullable(user)
        .map(User::getProfile)
        .map(Profile::getEmail)
        .orElse("unknown");
```

NPE를 catch하는 건 외부 라이브러리가 명백한 버그로 NPE를 던질 때 정도가 한계다.

## IllegalStateException 처리 패턴

`IllegalStateException`은 "메서드 호출은 형식적으로 맞지만, 객체의 현재 상태에서는 호출할 수 없다"는 의미다.

### 상태 전이 검증

```java
public class Order {
    private OrderStatus status;

    public void cancel() {
        if (status == OrderStatus.SHIPPED) {
            throw new IllegalStateException(
                "배송 시작된 주문은 취소할 수 없음: orderId=" + id);
        }
        if (status == OrderStatus.CANCELLED) {
            throw new IllegalStateException("이미 취소된 주문: orderId=" + id);
        }
        this.status = OrderStatus.CANCELLED;
    }
}
```

도메인 로직에서 상태 머신이 잘못 전이되는 걸 막는다. 호출자(컨트롤러, 다른 서비스)는 이 예외를 catch하지 않는다. 비즈니스적으로 의미 있는 예외라면 `OrderAlreadyCancelledException` 같은 도메인 예외로 변환해서 던지는 게 더 명확하다.

### IllegalState vs IllegalArgument

기준은 단순하다.

- 메서드에 들어온 인자가 잘못됐다 → `IllegalArgumentException`
- 인자는 맞지만 객체 상태가 호출을 받을 수 없다 → `IllegalStateException`

```java
public void deposit(BigDecimal amount) {
    if (amount == null || amount.signum() < 0) {
        throw new IllegalArgumentException("amount는 양수여야 함: " + amount);
    }
    if (status == AccountStatus.CLOSED) {
        throw new IllegalStateException("닫힌 계좌에는 입금 불가: " + id);
    }
    this.balance = balance.add(amount);
}
```

이 구분을 지키면 호출자가 예외를 보고 무엇을 고쳐야 할지 안다. `IllegalArgumentException`이면 호출 인자를 고치면 된다. `IllegalStateException`이면 객체 라이프사이클을 따라가야 한다.

### Iterator나 Stream의 IllegalStateException

JDK 자체에서도 자주 던진다.

```java
Iterator<String> it = list.iterator();
it.remove();  // IllegalStateException: next()를 먼저 호출해야 함

Stream<String> s = list.stream();
s.forEach(System.out::println);
s.count();  // IllegalStateException: stream has already been operated upon
```

이런 예외는 catch하지 않는다. 코드 흐름이 잘못된 거라 catch로 우회하지 말고 흐름을 고친다.

## 예외 번역 (Exception Translation)

하위 레이어의 예외를 상위 레이어에 맞는 예외로 변환하는 패턴이다.

```java
public class UserRepository {

    public User findById(Long id) {
        try {
            return jdbcTemplate.queryForObject(sql, mapper, id);
        } catch (EmptyResultDataAccessException e) {
            throw new UserNotFoundException(id);  // cause 안 넘겨도 됨
        }
    }

    public void save(User user) {
        try {
            jdbcTemplate.update(sql, user.getName(), user.getEmail());
        } catch (DuplicateKeyException e) {
            throw new DuplicateEmailException(user.getEmail(), e);  // cause 필수
        }
    }
}
```

핵심은 `cause`를 넘기느냐다.

- 원인이 디버깅에 필요하면 cause 포함 (DB 에러, 외부 API 에러)
- 원인이 구현 세부사항이면 생략 가능 (EmptyResultDataAccessException 같은 경우)

Spring의 `DataAccessException` 계층이 대표적인 사례다. JDBC의 벤더별 `SQLException`(MySQL, PostgreSQL 코드가 다 다르다)을 Spring의 통일된 예외(`DuplicateKeyException`, `DataIntegrityViolationException` 등)로 번역한다. 덕분에 서비스 레이어가 DB 벤더에 종속되지 않는다.

## 흔한 안티패턴

### 예외 삼키기

```java
try {
    riskyOperation();
} catch (Exception e) {
    // 아무것도 안 함 - 절대 금지
}
```

운영 환경에서 이런 코드가 한 줄만 있어도 장애 원인 추적에 시간이 몇 배로 걸린다. 최소한 로그는 남긴다. 의도적으로 무시하는 거라면 주석으로 이유를 남긴다.

### catch (Exception e) 남용

```java
try {
    User user = findUser(id);
    Order order = createOrder(user, items);
    sendNotification(order);
} catch (Exception e) {
    return ResponseEntity.badRequest().body("요청 처리 실패");
}
```

NPE가 발생해도 "요청 처리 실패"로 응답한다. 프로그래밍 오류인지 비즈니스 예외인지 구분이 안 된다. 잡아야 할 예외만 구체적으로 잡는다.

### 예외를 흐름 제어에 사용

```java
public boolean isValidEmail(String email) {
    try {
        new InternetAddress(email).validate();
        return true;
    } catch (AddressException e) {
        return false;
    }
}
```

예외 객체 생성과 스택 트레이스 채우기가 일반 메서드 호출보다 100~1000배 느리다. 외부 라이브러리가 강제하는 경우가 아니면 흐름 제어에 예외를 쓰지 않는다.

### 로그에 e.getMessage()만 남기기

```java
log.error("실패: " + e.getMessage());  // 스택 트레이스 없음
```

발생 위치를 알 수 없다. SLF4J에서는 마지막 인자가 `Throwable`이면 자동으로 스택 트레이스를 출력한다.

```java
log.error("실패: {}", context, e);  // 마지막 인자가 예외
```

## Spring에서의 전체 구조

실무에서 가장 많이 쓰는 패턴이다.

```java
@Service
public class OrderService {

    public Order cancel(Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new OrderNotFoundException(orderId));

        if (order.isShipped()) {
            throw new OrderAlreadyShippedException(orderId);
        }

        order.cancel();
        return orderRepository.save(order);
    }
}

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(OrderNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(OrderNotFoundException e) {
        return ResponseEntity.status(404)
                .body(new ErrorResponse("NOT_FOUND", e.getMessage()));
    }

    @ExceptionHandler(OrderAlreadyShippedException.class)
    public ResponseEntity<ErrorResponse> handleConflict(OrderAlreadyShippedException e) {
        return ResponseEntity.status(409)
                .body(new ErrorResponse("CONFLICT", e.getMessage()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponse> handleBadRequest(IllegalArgumentException e) {
        return ResponseEntity.status(400)
                .body(new ErrorResponse("BAD_REQUEST", e.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception e) {
        log.error("예상하지 못한 에러", e);
        return ResponseEntity.status(500)
                .body(new ErrorResponse("INTERNAL_ERROR", "서버 내부 오류"));
    }
}
```

서비스 레이어는 비즈니스 규칙 위반을 도메인 예외로 표현한다. HTTP 상태 코드를 알 필요가 없다. 예외 핸들러가 도메인 예외를 HTTP 응답으로 변환한다. 이 분리가 무너지면 서비스 코드에 `ResponseEntity`나 `HttpStatus`가 섞여 들어가서 테스트하기 어려워진다.

마지막 `@ExceptionHandler(Exception.class)`는 예상하지 못한 예외용 안전망이다. 실제 운영에서는 여기에 걸린 예외를 모니터링해서 매주 분석한다. 이 핸들러에 자주 잡히는 예외가 있다면 도메인 예외로 승격시켜 명시적으로 처리해야 한다는 신호다.
