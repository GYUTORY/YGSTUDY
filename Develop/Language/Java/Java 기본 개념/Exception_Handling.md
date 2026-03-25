---
title: "Java 예외 처리"
tags: [java, exception, error-handling, try-with-resources]
updated: 2026-03-25
---

# Java 예외 처리

## 예외 계층 구조

Java의 예외는 `Throwable`을 최상위로 두고 두 갈래로 나뉜다.

```
Throwable
├── Error          → OutOfMemoryError, StackOverflowError (잡으면 안 됨)
└── Exception
    ├── IOException, SQLException 등  → Checked Exception
    └── RuntimeException
        ├── NullPointerException
        ├── IllegalArgumentException
        └── IndexOutOfBoundsException  → Unchecked Exception
```

`Error`는 JVM 레벨 문제라 애플리케이션에서 처리할 수 없다. `catch (Throwable t)` 같은 코드는 `OutOfMemoryError`까지 잡아버리니 쓰면 안 된다.

## Checked vs Unchecked

### Checked Exception

컴파일러가 처리를 강제한다. `throws` 선언이나 `try-catch`가 없으면 컴파일 에러가 난다.

```java
// 호출하는 쪽에서 반드시 처리해야 한다
public String readFile(String path) throws IOException {
    return Files.readString(Path.of(path));
}
```

Checked Exception은 "호출자가 복구할 수 있는 상황"에 쓴다. 파일이 없으면 다른 경로를 시도하거나, DB 연결이 끊기면 재시도하는 식이다.

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

프로그래밍 오류(잘못된 인자, null 참조)에 해당하는 예외다. 호출자가 매번 `try-catch`로 감싸는 건 의미가 없다.

### 실무에서의 선택 기준

Spring 기반 웹 애플리케이션에서는 대부분 Unchecked Exception을 쓴다. 이유는 단순하다.

1. 컨트롤러 → 서비스 → 리포지토리 체인에서 Checked Exception을 쓰면 모든 레이어에 `throws`가 전파된다
2. 결국 대부분의 예외는 `@ExceptionHandler`에서 HTTP 응답으로 변환한다
3. 복구 불가능한 상황이 대부분이라 catch해봐야 할 수 있는 게 없다

```java
// 이렇게 되면 서비스 인터페이스가 구현 기술에 종속된다
public interface UserService {
    User findById(Long id) throws SQLException;  // 하면 안 되는 패턴
}
```

## try-with-resources

Java 7에서 추가됐다. `AutoCloseable`을 구현한 리소스를 자동으로 닫아준다.

### 기본 사용법

```java
// try 블록이 끝나면 reader가 자동으로 닫힌다
try (BufferedReader reader = new BufferedReader(new FileReader(path))) {
    String line;
    while ((line = reader.readLine()) != null) {
        process(line);
    }
} catch (IOException e) {
    log.error("파일 읽기 실패: {}", path, e);
}
```

### 여러 리소스 사용

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

### Suppressed Exception

리소스를 닫는 과정에서 예외가 발생하면 `suppressed exception`으로 붙는다.

```java
try (MyResource resource = new MyResource()) {
    throw new RuntimeException("본래 예외");
    // resource.close()에서도 예외가 발생하면
    // 본래 예외의 suppressed에 추가된다
} catch (RuntimeException e) {
    // e.getMessage() → "본래 예외"
    // e.getSuppressed()[0] → close()에서 발생한 예외
}
```

이전의 try-finally 방식에서는 close() 예외가 원래 예외를 덮어써서 디버깅이 어려웠다. try-with-resources는 이 문제를 해결한다.

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
        if (!committed) {
            conn.rollback();
        }
        conn.close();
    }
}

// 사용
try (DatabaseTransaction tx = new DatabaseTransaction(dataSource)) {
    userRepository.save(conn, user);
    orderRepository.save(conn, order);
    tx.commit();
}
// commit() 호출 전에 예외가 나면 자동으로 rollback된다
```

## 커스텀 예외

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

### 계층 구조 설계

도메인별로 최상위 예외를 두고 하위에 구체적인 예외를 만든다.

```java
// 도메인 최상위 예외
public abstract class OrderException extends RuntimeException {
    protected OrderException(String message) {
        super(message);
    }
    protected OrderException(String message, Throwable cause) {
        super(message, cause);
    }
}

// 구체적인 예외들
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

`@ExceptionHandler`에서 `OrderException`으로 한번에 잡을 수 있어서 편하다.

```java
@ExceptionHandler(OrderException.class)
public ResponseEntity<ErrorResponse> handleOrderException(OrderException e) {
    return ResponseEntity.badRequest()
            .body(new ErrorResponse(e.getMessage()));
}
```

### 커스텀 예외를 만들어야 하는 경우

아무 때나 만들면 클래스만 늘어난다. 다음 조건에 해당할 때만 만든다.

- 예외에 추가 정보(주문 ID, 실패 사유 코드 등)를 담아야 할 때
- 특정 예외만 골라서 catch해야 할 때
- `@ExceptionHandler`에서 HTTP 상태 코드를 다르게 매핑해야 할 때

단순히 메시지만 다른 경우라면 `IllegalStateException`이나 `IllegalArgumentException`으로 충분하다.

## 예외 번역 (Exception Translation)

하위 레이어의 예외를 상위 레이어에 맞는 예외로 변환하는 패턴이다.

```java
public class UserRepository {

    public User findById(Long id) {
        try {
            return jdbcTemplate.queryForObject(sql, mapper, id);
        } catch (EmptyResultDataAccessException e) {
            throw new UserNotFoundException(id);  // 원인을 담지 않아도 되는 경우
        }
    }

    public void save(User user) {
        try {
            jdbcTemplate.update(sql, user.getName(), user.getEmail());
        } catch (DuplicateKeyException e) {
            throw new DuplicateEmailException(user.getEmail(), e);  // 원인을 담아야 하는 경우
        }
    }
}
```

핵심은 `cause`를 넘기느냐 마느냐다.

- **원인 예외가 디버깅에 필요하면** `cause`를 넘긴다 (DB 에러, 외부 API 에러)
- **원인 예외가 구현 세부사항이면** 넘기지 않아도 된다 (빈 결과를 도메인 예외로 바꾸는 경우)

Spring의 `DataAccessException` 계층이 대표적인 예외 번역 사례다. JDBC의 벤더별 `SQLException`을 Spring의 통일된 예외로 변환한다.

## 실무에서 흔한 실수와 안티패턴

### 1. 예외를 삼켜버리기

```java
// 절대 하면 안 된다
try {
    riskyOperation();
} catch (Exception e) {
    // 아무것도 안 함
}

// 최소한 로그는 남겨야 한다
try {
    riskyOperation();
} catch (Exception e) {
    log.error("작업 실패", e);
}
```

예외를 삼키면 문제가 발생해도 원인을 추적할 수 없다. 운영 환경에서 이런 코드가 있으면 장애 원인 파악에 시간이 몇 배로 걸린다.

### 2. catch (Exception e) 남용

```java
// 너무 넓게 잡으면 예상치 못한 예외까지 같은 방식으로 처리된다
try {
    User user = findUser(id);
    Order order = createOrder(user, items);
    sendNotification(order);
} catch (Exception e) {
    return ResponseEntity.badRequest().body("요청 처리 실패");
}
```

`NullPointerException`이 발생해도 "요청 처리 실패"로 응답한다. 프로그래밍 오류인지 비즈니스 예외인지 구분이 안 된다. 잡아야 할 예외만 구체적으로 잡아야 한다.

### 3. 예외를 리턴값처럼 사용

```java
// 예외를 흐름 제어에 쓰면 안 된다
public boolean isValidEmail(String email) {
    try {
        new InternetAddress(email).validate();
        return true;
    } catch (AddressException e) {
        return false;
    }
}
```

예외는 비용이 크다. 스택 트레이스를 생성하는 데 수백 나노초가 걸린다. 정상적인 흐름 제어에 예외를 쓰면 성능 문제가 생긴다. 위 코드처럼 외부 라이브러리가 예외를 던지는 구조라서 어쩔 수 없는 경우도 있지만, 직접 만드는 코드에서는 피해야 한다.

### 4. 원인 예외 누락

```java
// cause를 빠뜨리면 원래 스택 트레이스가 사라진다
try {
    externalApi.call();
} catch (HttpClientException e) {
    throw new ServiceException("외부 API 호출 실패");  // e가 빠졌다
}

// 반드시 cause를 포함시킨다
try {
    externalApi.call();
} catch (HttpClientException e) {
    throw new ServiceException("외부 API 호출 실패", e);  // 원인 포함
}
```

### 5. catch에서 로그 남기고 다시 throw

```java
// 같은 예외가 로그에 여러 번 찍힌다
try {
    process();
} catch (Exception e) {
    log.error("처리 실패", e);  // 여기서 한번
    throw e;                    // 상위에서 또 한번
}
```

예외를 다시 던질 거면 로그를 남기지 않는다. 로그를 남길 거면 다시 던지지 않는다. 둘 다 하면 같은 에러 로그가 중복으로 쌓여서 로그 분석이 어려워진다.

### 6. finally에서 예외 던지기

```java
// finally에서 예외가 발생하면 try의 예외가 사라진다
try {
    return process();
} finally {
    cleanup();  // 여기서 예외가 나면 process()의 예외를 덮어쓴다
}
```

try-with-resources를 쓰면 이 문제가 자동으로 해결된다. finally를 직접 쓸 때는 cleanup 코드에서 예외가 발생하지 않도록 방어 코드를 넣어야 한다.

### 7. 로그에 e.getMessage()만 남기기

```java
// 스택 트레이스가 없으면 발생 위치를 알 수 없다
log.error("실패: " + e.getMessage());

// 예외 객체를 마지막 인자로 넘겨야 스택 트레이스가 출력된다
log.error("실패: {}", e.getMessage(), e);
```

SLF4J에서 마지막 인자가 `Throwable`이면 자동으로 스택 트레이스를 출력한다. `e.getMessage()`만 남기면 어디서 예외가 발생했는지 알 수 없다.

## Spring에서의 예외 처리 구조

실무에서 가장 많이 쓰는 구조다.

```java
// 1. 서비스에서 비즈니스 예외를 던진다
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

// 2. @RestControllerAdvice에서 예외를 HTTP 응답으로 변환한다
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

    // 예상하지 못한 예외는 500으로 처리한다
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception e) {
        log.error("예상하지 못한 에러", e);
        return ResponseEntity.status(500)
                .body(new ErrorResponse("INTERNAL_ERROR", "서버 내부 오류"));
    }
}
```

서비스 레이어에서는 비즈니스 규칙 위반을 예외로 표현하고, 예외 핸들러에서 HTTP 응답으로 변환한다. 서비스가 HTTP 상태 코드를 알 필요가 없다.
