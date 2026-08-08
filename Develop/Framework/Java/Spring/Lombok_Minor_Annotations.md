---
title: Lombok 보조 어노테이션
tags: [java, spring]
updated: 2026-07-02
---

# Lombok 보조 어노테이션

`@Getter`, `@Setter`, `@Builder`, `@Data` 같은 주력 어노테이션은 [Lombok.md](Lombok.md)와 [Lombok_Deep_Dive.md](Lombok_Deep_Dive.md)에서 다뤘다. 이 문서는 그 외에 프로젝트에 슬쩍 들어와 있지만 정확한 동작을 모르고 쓰다가 사고를 내는 보조 어노테이션들을 모았다. `@NonNull`, `@SneakyThrows`, `@Cleanup`, `@With`, `@Accessors`, `@Synchronized`, `@Jacksonized`, 그리고 프로젝트 전역을 제어하는 `lombok.config`까지 정리한다.

이 어노테이션들은 대부분 "편해서" 붙였다가 나중에 디버깅할 때 생성된 코드가 어디에 뭘 끼워 넣었는지 몰라서 시간을 잡아먹는 경우가 많다. 각 어노테이션이 정확히 어떤 코드로 풀리는지, 그리고 언제 문제가 되는지를 중심으로 본다.

참고 문서:
- [Lombok @NonNull](https://projectlombok.org/features/NonNull)
- [Lombok @SneakyThrows](https://projectlombok.org/features/SneakyThrows)
- [Lombok configuration](https://projectlombok.org/features/configuration)

## 1. @NonNull — null 체크 코드 삽입 위치가 핵심

`@NonNull`은 파라미터나 필드에 붙이면 컴파일 시점에 null 체크 코드를 자동으로 넣어준다. 문제는 "어디에" 넣어주느냐다. 붙이는 위치에 따라 삽입되는 코드가 완전히 달라진다.

### 1.1 생성자 파라미터에 붙였을 때

```java
public class Order {
    private final String orderNo;

    public Order(@NonNull String orderNo) {
        this.orderNo = orderNo;
    }
}
```

컴파일하면 생성자 본문 맨 앞에 이런 코드가 박힌다.

```java
public Order(String orderNo) {
    if (orderNo == null) {
        throw new NullPointerException("orderNo is marked non-null but is null");
    }
    this.orderNo = orderNo;
}
```

여기서 첫 번째 함정. `@NonNull`이 던지는 건 `IllegalArgumentException`이 아니라 `NullPointerException`이다. null 파라미터는 "잘못된 인자"니까 `IllegalArgumentException`이 자연스럽다고 생각하는 사람이 많은데, Lombok 기본값은 NPE다. 그래서 파라미터 검증 로직에서

```java
try {
    orderService.create(null);
} catch (IllegalArgumentException e) {
    // @NonNull이 던진 예외는 여기 안 잡힌다
}
```

이렇게 `IllegalArgumentException`만 잡는 코드는 `@NonNull`의 예외를 그냥 통과시킨다. 이 예외 타입은 `lombok.config`로 바꿀 수 있는데, 뒤에서 다룬다.

### 1.2 필드에 붙였을 때

필드에 `@NonNull`을 붙이면 그 자체로는 아무 일도 안 한다. Lombok이 생성하는 다른 코드(생성자, setter)에서만 효과가 있다.

```java
public class Order {
    @NonNull
    private String orderNo;
}
```

이 상태로는 null 체크가 어디에도 안 생긴다. 필드에 붙인 `@NonNull`은 Lombok이 만드는 코드에만 반영되기 때문이다.

```java
@RequiredArgsConstructor
public class Order {
    @NonNull
    private String orderNo;   // 이제 RequiredArgsConstructor 대상에 포함되고,
                              // 생성자에 null 체크가 들어간다
}
```

`@RequiredArgsConstructor`와 `@NonNull`을 같이 쓰면, `final`이 아니어도 `@NonNull` 필드가 생성자 파라미터에 포함된다. 그리고 그 생성자 안에 null 체크가 들어간다. `@Setter`가 있으면 setter 안에도 체크가 들어간다. 이걸 모르면 "왜 이 필드가 생성자 인자에 들어가 있지?" 하고 헷갈린다.

### 1.3 실무에서 조심할 점

`@NonNull`은 방어 로직을 코드 첫 줄에 강제로 넣어주는 것뿐이다. Bean Validation(`@NotNull`)과는 완전히 다르다. `@NotNull`은 런타임에 Validator가 검사하고 검증 결과를 모아서 돌려주지만, `@NonNull`은 그냥 즉시 예외를 던진다. Controller 파라미터 검증을 `@NonNull`로 하려고 하면 안 된다. 그건 `@Valid` + `@NotNull`의 영역이다.

## 2. @SneakyThrows — checked 예외를 몰래 던지는 위험

`@SneakyThrows`는 checked 예외를 `throws` 선언 없이 던질 수 있게 해준다. 컴파일러를 속여서 checked 예외를 unchecked처럼 통과시킨다.

```java
@SneakyThrows
public String read(File file) {
    return Files.readString(file.toPath());  // IOException을 throws 안 해도 됨
}
```

Lombok이 생성하는 코드는 대략 이렇다.

```java
public String read(File file) {
    try {
        return Files.readString(file.toPath());
    } catch (Throwable t) {
        throw Lombok.sneakyThrow(t);   // 타입 지우고 그대로 다시 던짐
    }
}
```

`Lombok.sneakyThrow`는 제네릭 트릭으로 예외 타입 정보를 지우고 원래 예외를 그대로 던진다. 그래서 런타임에는 여전히 `IOException`이 날아가는데, 컴파일러는 그 사실을 모른다.

### 2.1 호출부가 catch를 못 하는 문제

여기서 진짜 문제가 생긴다. 호출부에서 `IOException`을 잡으려고 하면 컴파일이 안 된다.

```java
try {
    fileService.read(file);
} catch (IOException e) {   // 컴파일 에러: IOException은 여기서 절대 안 던져진다고 컴파일러가 판단
    log.error("파일 읽기 실패", e);
}
```

컴파일러 입장에서 `read()`는 `throws IOException`이 없으니 "이 메서드는 `IOException`을 던지지 않는다"고 본다. 그래서 `catch (IOException e)`를 "도달 불가능한 catch"로 판단하고 컴파일을 거부한다. 실제로는 런타임에 `IOException`이 날아오는데도 말이다.

이걸 잡으려면 `catch (Exception e)`나 `catch (IOException e)`를 억지로 우회하는 방법밖에 없다. 결국 `@SneakyThrows`를 쓴 메서드의 예외는 호출부에서 타입으로 구분해서 처리하기가 어려워진다. 라이브러리 내부나 정말 예외가 날 수 없는 자리(예: `UTF-8` 인코딩 지정하는 데 `UnsupportedEncodingException`)에나 제한적으로 쓰는 게 맞다.

### 2.2 트랜잭션 롤백 오작동

Spring `@Transactional`은 기본적으로 unchecked 예외(`RuntimeException`, `Error`)에서만 롤백하고, checked 예외에서는 롤백하지 않는다. `@SneakyThrows`는 이 규칙과 미묘하게 얽힌다.

```java
@Transactional
public void process() {
    repository.save(entity);
    doSomething();   // 여기서 @SneakyThrows로 IOException이 몰래 날아옴
}
```

`doSomething()`이 `@SneakyThrows`로 `IOException`을 던지면, 실제 던져지는 예외 객체는 `IOException`이다. Spring의 트랜잭션 인터셉터는 던져진 예외 객체의 실제 타입을 보고 롤백 여부를 정하는데, `IOException`은 checked 예외라 기본 규칙상 **롤백하지 않는다**. 컴파일러는 "이 메서드가 checked 예외를 던진다"는 걸 몰라도, 런타임에 실제로 날아오는 건 checked 예외 그 자체이기 때문이다.

그래서 `@SneakyThrows`로 checked 예외를 던지는 코드가 트랜잭션 안에 있으면, 개발자는 "예외 났으니 롤백됐겠지" 생각하는데 실제로는 커밋되는 사고가 난다. 이걸 막으려면 `@Transactional(rollbackFor = Exception.class)`를 명시하거나, 애초에 `@SneakyThrows`를 트랜잭션 메서드 안에서 쓰지 않아야 한다. 후자가 낫다.

## 3. @Cleanup — try-with-resources의 오래된 대체재

`@Cleanup`은 자원을 자동으로 닫아준다. try-with-resources가 나오기 전에 유용했던 어노테이션이다.

```java
public void copy(String src, String dst) throws IOException {
    @Cleanup InputStream in = new FileInputStream(src);
    @Cleanup OutputStream out = new FileOutputStream(dst);
    byte[] buf = new byte[1024];
    int r;
    while ((r = in.read(buf)) != -1) {
        out.write(buf, 0, r);
    }
}
```

메서드가 끝날 때 `in.close()`, `out.close()`가 역순으로 호출되는 코드가 생성된다. 동작은 try-with-resources와 거의 같다.

### 3.1 실무에서 안 쓰는 이유

`@Cleanup`은 요즘 거의 안 쓴다. Java 7에서 try-with-resources가 나온 뒤로 존재 이유가 사라졌다. try-with-resources는 언어 문법이라 IDE도, 코드 리뷰어도, 정적 분석 도구도 전부 이해한다. `@Cleanup`은 Lombok을 모르는 사람이 보면 "이 스트림 언제 닫히지?" 하고 헷갈린다.

또 `@Cleanup`은 `close()`가 예외를 던졌을 때 처리가 애매하다. 본문에서 예외가 났고 `close()`에서도 예외가 나면, try-with-resources는 close 쪽 예외를 suppressed exception으로 붙여주지만 `@Cleanup`이 만드는 코드는 그 처리가 버전에 따라 다르고 명확하지 않다. 굳이 문법으로 해결되는 걸 어노테이션으로 대체할 이유가 없다.

새 코드에서는 try-with-resources를 쓰고, `@Cleanup`은 legacy 코드에서 보이면 그냥 두거나 리팩터링할 때 걷어내면 된다.

## 4. @With — 불변 객체 필드 하나만 바꾼 복사본

`@With`는 불변 객체에서 필드 하나만 바꾼 새 객체를 만드는 메서드를 생성한다. 원본은 그대로 두고 지정한 필드만 교체한 복사본을 돌려준다.

```java
@With
@AllArgsConstructor
@Getter
public class Money {
    private final String currency;
    private final long amount;
}
```

`@With`는 `withCurrency`, `withAmount` 메서드를 만든다.

```java
public Money withCurrency(String currency) {
    return this.currency == currency ? this : new Money(currency, this.amount);
}
```

생성된 코드를 보면 값이 같으면 `this`를 그대로 돌려주고, 다르면 새 객체를 만든다. 사용은 이렇게 한다.

```java
Money usd = new Money("USD", 100);
Money krw = usd.withCurrency("KRW");   // amount는 그대로, currency만 KRW
```

### 4.1 record, 수동 copy와 비교

Java 16부터 `record`가 정식으로 들어왔지만, `record`에는 `@With` 같은 부분 복사 메서드가 기본으로 없다. record로 같은 걸 하려면 직접 만들어야 한다.

```java
public record Money(String currency, long amount) {
    public Money withCurrency(String currency) {
        return new Money(currency, this.amount);
    }
}
```

필드가 두 개면 이렇게 손으로 써도 되지만, 필드가 열 개쯤 되면 `withXxx` 메서드를 다 손으로 쓰는 건 지겹다. 그럴 때 record에도 `@With`를 붙일 수 있다. Lombok 1.18.20부터 record를 지원한다.

```java
@With
public record Money(String currency, long amount) {}
```

수동 copy 생성자 방식(`new Money(newCurrency, old.amount())`)과 비교하면, `@With`는 필드가 많을 때 어느 필드를 바꾸는지가 메서드 이름에 드러나서 읽기 편하다. `new Money(a, b, c, d, e)` 방식은 인자 순서를 헷갈리면 조용히 잘못된 객체가 만들어진다. 다만 `@With`는 필드마다 메서드를 하나씩 만들기 때문에, 여러 필드를 동시에 바꿀 때는 `withA(x).withB(y).withC(z)`처럼 중간 객체가 계속 생긴다. 성능이 민감한 자리에서 필드 여러 개를 한꺼번에 바꿔야 하면 `toBuilder()`가 더 맞다.

## 5. @Accessors — getter/setter 규칙을 바꿨다가 JPA·Jackson과 충돌

`@Accessors`는 getter/setter의 이름 규칙과 반환 방식을 바꾼다. `chain`, `fluent`, `prefix` 세 옵션이 있는데, 이게 JPA와 Jackson의 프로퍼티 인식 규칙과 정면으로 충돌하는 경우가 많다.

### 5.1 chain — setter가 this를 반환

```java
@Setter
@Accessors(chain = true)
public class UserDto {
    private String name;
    private String email;
}
```

`chain = true`면 setter가 `void` 대신 `this`를 반환한다.

```java
public UserDto setName(String name) {
    this.name = name;
    return this;
}
```

그래서 `new UserDto().setName("kim").setEmail("kim@x.com")`처럼 이어 쓸 수 있다. 이 정도는 큰 문제가 안 되지만, `fluent`부터가 위험하다.

### 5.2 fluent — getter/setter에서 get/set 접두어 제거

```java
@Getter
@Setter
@Accessors(fluent = true)
public class UserDto {
    private String name;
}
```

`fluent = true`면 접두어가 사라진다. getter는 `name()`, setter는 `name(String)`이 된다. `getName()`이 아니라 `name()`이다. 여기서 문제가 터진다.

Jackson은 기본적으로 `getXxx()` 형태의 메서드를 프로퍼티로 인식해서 JSON 필드를 만든다. `@Accessors(fluent = true)`를 붙이면 getter가 `name()`이 되니까 Jackson이 "이건 getter가 아니다"라고 판단해서 직렬화 대상에서 빠진다. 그 결과 JSON에 `name` 필드가 통째로 안 나온다.

```java
@Getter
@Accessors(fluent = true)
public class UserDto {
    private String name = "kim";
}
// 이 객체를 ObjectMapper로 직렬화하면 {} 가 나온다. name 필드가 사라진다.
```

JPA도 마찬가지다. Hibernate가 프로퍼티 접근 방식(`AccessType.PROPERTY`)을 쓸 때는 `getXxx`/`setXxx` 규칙에 의존하는데, `fluent`로 접두어를 없애면 Hibernate가 프로퍼티를 못 찾는다. 그래서 JPA 엔티티에는 `@Accessors(fluent = true)`를 절대 붙이면 안 된다.

### 5.3 실무 원칙

`@Accessors`는 편해 보여서 DTO에 무심코 붙이는데, 그 DTO가 나중에 API 응답으로 직렬화되거나 엔티티로 매핑되는 순간 조용히 깨진다. 특히 `fluent`는 Jackson 직렬화를 통째로 망가뜨린다. 프로젝트 전역에서 아예 금지하는 게 낫고, 이건 `lombok.config`로 강제할 수 있다(6절).

`chain`은 그나마 덜 위험하지만, 팀 전체가 setter 체이닝을 쓰는 게 아니면 일관성만 깨진다. 굳이 쓰려면 DTO에만 제한적으로 쓰고 엔티티에는 안 쓰는 게 맞다.

## 6. @Synchronized — this 락 대신 전용 락 객체

`synchronized` 키워드를 메서드에 붙이면 인스턴스 메서드는 `this`를, static 메서드는 클래스 객체를 락으로 쓴다. 이게 문제인 건, 외부 코드가 그 객체 참조를 들고 있으면 같은 락을 잡을 수 있어서 데드락이나 예상 못 한 블로킹이 생길 수 있다는 점이다.

`@Synchronized`는 이걸 피하려고 전용 락 객체를 자동으로 만들어서 그걸로 동기화한다.

```java
public class Counter {
    private int count;

    @Synchronized
    public void increment() {
        count++;
    }
}
```

생성되는 코드는 이렇다.

```java
public class Counter {
    private final Object $lock = new Object[0];
    private int count;

    public void increment() {
        synchronized ($lock) {
            count++;
        }
    }
}
```

`$lock`이라는 private 필드를 만들고 그걸로 동기화한다. static 메서드에 붙이면 `$LOCK`이라는 static 필드를 만든다. 외부에서 이 락 객체에 접근할 수 없으니 `synchronized(this)`보다 안전하다.

락 필드 이름을 직접 지정할 수도 있다.

```java
private final Object readLock = new Object();

@Synchronized("readLock")
public int getCount() {
    synchronized (readLock) {  // 지정한 필드로 동기화
        return count;
    }
}
```

다만 요즘은 `synchronized` 자체를 잘 안 쓴다. `ReentrantLock`, `ConcurrentHashMap`, `AtomicInteger` 같은 `java.util.concurrent` 도구가 락 범위를 더 세밀하게 제어하고 성능도 낫다. `@Synchronized`는 "`synchronized`를 쓰긴 써야 하는데 `this` 락은 피하고 싶다"는 좁은 상황에서만 의미가 있다. 그런 경우도 사실 락 객체를 직접 선언해서 `synchronized(lock)`으로 쓰면 되니까, `@Synchronized`가 꼭 필요한 자리는 실무에서 드물다.

## 7. @Jacksonized — @Builder와 Jackson 역직렬화 연동

`@Builder`로 만든 클래스를 Jackson으로 역직렬화하려고 하면 바로 깨진다. 이게 실무에서 정말 자주 겪는 문제다.

### 7.1 @Builder만 있을 때 역직렬화가 안 되는 이유

```java
@Builder
@Getter
public class OrderRequest {
    private String orderNo;
    private long amount;
}
```

이 클래스로 JSON을 역직렬화하려고 하면 Jackson이 실패한다. Jackson은 기본적으로 기본 생성자(no-args constructor)로 객체를 만들고 setter나 필드로 값을 채우는데, `@Builder`는 기본 생성자를 없애고 모든 필드를 받는 생성자만 만든다. 그래서 Jackson이 객체를 만들 방법을 못 찾는다.

```
com.fasterxml.jackson.databind.exc.InvalidDefinitionException:
Cannot construct instance of OrderRequest (no Creators, like default constructor, exist)
```

이 에러를 만나면 보통 `@NoArgsConstructor`, `@AllArgsConstructor`를 덧붙이거나, 빌더에 `@JsonDeserialize(builder = ...)`, `@JsonPOJOBuilder`를 손으로 설정한다. 수동으로 하면 이렇게 된다.

```java
@Builder
@Getter
@JsonDeserialize(builder = OrderRequest.OrderRequestBuilder.class)
public class OrderRequest {
    private String orderNo;
    private long amount;

    @JsonPOJOBuilder(withPrefix = "")
    public static class OrderRequestBuilder {}
}
```

빌더 클래스 이름을 정확히 알아야 하고, `withPrefix`도 Lombok 빌더 규칙에 맞춰야 하고, 코드가 지저분하다.

### 7.2 @Jacksonized가 대신 해주는 것

`@Jacksonized`는 이 수동 설정을 전부 대신 해준다. `@Builder`(또는 `@SuperBuilder`)와 같이 붙이기만 하면 된다.

```java
@Jacksonized
@Builder
@Getter
public class OrderRequest {
    private String orderNo;
    private long amount;
}
```

이것만으로 Jackson이 빌더를 통해 역직렬화한다. `@Jacksonized`가 컴파일 시점에 `@JsonDeserialize`와 `@JsonPOJOBuilder`를 빌더에 자동으로 붙여준다. 수동 설정할 때 이름을 틀리거나 `withPrefix`를 잘못 맞춰서 나던 실수가 사라진다.

주의할 점은 `@Jacksonized`는 반드시 `@Builder`나 `@SuperBuilder`와 함께 써야 한다는 것이다. 단독으로는 아무 효과가 없다. 그리고 `@JsonProperty` 같은 필드 매핑 어노테이션은 여전히 필드에 직접 붙여야 한다. `@Jacksonized`는 빌더 연동만 처리하지 필드 이름 매핑까지 해주진 않는다.

```java
@Jacksonized
@Builder
@Getter
public class OrderRequest {
    @JsonProperty("order_no")   // snake_case 매핑은 여전히 직접
    private String orderNo;
    private long amount;
}
```

`@Value`로 만든 불변 객체를 역직렬화할 때도 `@Jacksonized`가 잘 맞는다. `@Value`는 모든 필드를 `final`로 만들어서 setter 기반 역직렬화가 불가능한데, 빌더 기반이면 문제가 없기 때문이다.

## 8. lombok.config — 프로젝트 전역 설정

`@Accessors`를 금지하고 싶다거나, `@NonNull`의 예외 타입을 바꾸고 싶다거나, 커버리지 측정에서 Lombok 생성 코드를 빼고 싶을 때, 이걸 파일마다 손보는 건 불가능하다. `lombok.config` 파일로 프로젝트 전역 설정을 건다.

프로젝트 루트(또는 특정 소스 디렉터리)에 `lombok.config` 파일을 두면, 그 디렉터리 하위 전체에 설정이 적용된다. 상위에서 하위로 상속되고, 하위 디렉터리에 또 파일을 두면 덮어쓴다.

```properties
# 이 디렉터리가 설정의 최상위임을 표시. 상위 디렉터리 설정을 더 안 찾음
config.stopBubbling = true

# @Accessors를 프로젝트 전역에서 금지 (붙이면 컴파일 에러)
lombok.accessors.flagUsage = error

# @NonNull이 던지는 예외를 NPE에서 IllegalArgumentException으로 변경
lombok.nonNull.exceptionType = IllegalArgumentException

# 생성된 메서드에 @lombok.Generated 어노테이션을 붙임 (커버리지 도구가 제외 가능)
lombok.addLombokGeneratedAnnotation = true
```

### 8.1 flagUsage로 특정 어노테이션 금지

`lombok.accessors.flagUsage = error`를 걸면 누군가 `@Accessors`를 붙이는 순간 컴파일이 깨진다. `error` 대신 `warning`으로 하면 경고만 뜬다. `@Accessors`처럼 팀 규칙상 쓰면 안 되는 어노테이션을 이렇게 막으면, 코드 리뷰에서 매번 지적하지 않아도 컴파일러가 걸러준다.

`@SneakyThrows`도 같은 방식으로 막을 수 있다.

```properties
lombok.sneakyThrows.flagUsage = error
```

트랜잭션 롤백 사고(2.2절)를 원천 차단하고 싶으면 이걸 걸어두는 게 낫다.

### 8.2 nonNull.exceptionType으로 예외 타입 변경

1.3절에서 봤듯이 `@NonNull`은 기본으로 `NullPointerException`을 던진다. 팀에서 파라미터 검증 실패를 `IllegalArgumentException`으로 통일하고 싶으면 이 설정 하나로 프로젝트 전체의 `@NonNull` 예외 타입이 바뀐다.

```properties
lombok.nonNull.exceptionType = IllegalArgumentException
```

이걸 걸어두면 앞에서 봤던 "`IllegalArgumentException`으로 잡으려는데 `@NonNull`이 NPE를 던져서 안 잡히던" 문제가 해결된다. `JDK`(기본, NPE), `IllegalArgumentException`, `Assertion` 중에 고를 수 있다.

### 8.3 addLombokGeneratedAnnotation으로 커버리지 제외

JaCoCo 같은 커버리지 도구는 Lombok이 생성한 getter/setter/equals까지 다 측정 대상으로 잡는다. 그래서 실제로는 잘 만든 코드인데 커버리지 숫자가 억울하게 깎인다. `@Getter`가 만든 getter를 테스트에서 일일이 호출할 이유는 없으니까.

```properties
lombok.addLombokGeneratedAnnotation = true
```

이걸 켜면 Lombok이 생성하는 모든 메서드에 `@lombok.Generated` 어노테이션이 붙는다. JaCoCo는 0.8.0부터 `@Generated`가 붙은 요소를 커버리지 측정에서 자동으로 제외한다. 별도 설정 없이 이 한 줄만 켜면 생성 코드가 커버리지에서 빠진다. 새 프로젝트를 시작하면 거의 항상 켜두는 설정이다.

### 8.4 설정이 안 먹을 때

`lombok.config`를 고쳤는데 반영이 안 되면 대부분 빌드 캐시 문제다. Lombok 설정은 컴파일 시점에 읽히기 때문에, 증분 컴파일이 캐시된 상태에서는 새 설정이 적용된 재컴파일이 안 일어난다. `./gradlew clean build`로 전체 재컴파일을 강제하면 반영된다. IDE에서는 프로젝트를 rebuild 하거나 Lombok 플러그인을 다시 로드해야 하는 경우가 있다.

또 `config.stopBubbling = true`를 안 걸어두면 Lombok이 상위 디렉터리로 계속 올라가면서 다른 `lombok.config`를 찾는다. 모노레포에서 여러 모듈이 각자 설정을 가질 때, 최상위 모듈 설정에 `stopBubbling = true`를 걸지 않으면 예상 못 한 상위 설정이 섞여 들어올 수 있다. 각 설정 최상단에 이걸 명시하는 습관을 들이는 게 안전하다.

## 9. 정리

이 문서에서 다룬 보조 어노테이션은 대부분 "필요할 때만, 아는 상태에서" 써야 하는 것들이다.

- `@NonNull`: null 체크를 코드 첫 줄에 강제로 넣는다. 던지는 예외는 기본 NPE, `lombok.config`로 바꾼다. Bean Validation과는 다르다.
- `@SneakyThrows`: checked 예외를 몰래 던진다. 호출부가 타입으로 못 잡고, 트랜잭션 롤백이 안 도는 사고가 난다. 트랜잭션 메서드 안에서는 쓰지 않는다.
- `@Cleanup`: try-with-resources가 대체했다. 새 코드에서 쓸 이유가 없다.
- `@With`: 불변 객체 부분 복사. record와 조합 가능하고, 여러 필드를 동시에 바꿀 땐 빌더가 낫다.
- `@Accessors`: `fluent`는 Jackson·JPA 프로퍼티 규칙을 깬다. 전역 금지가 안전하다.
- `@Synchronized`: `this` 락 대신 전용 락 객체. 요즘은 `java.util.concurrent`가 대안이라 쓸 자리가 좁다.
- `@Jacksonized`: `@Builder` 클래스의 Jackson 역직렬화를 자동 연동한다. 반드시 `@Builder`와 함께.
- `lombok.config`: 어노테이션 금지, 예외 타입 변경, 커버리지 제외를 프로젝트 전역으로 건다. `stopBubbling`과 `addLombokGeneratedAnnotation`은 새 프로젝트에서 기본으로 켜둔다.
