---
title: Java Serialization & Deserialization
tags: [language, java]
updated: 2026-07-15
---

# Java 직렬화 / 역직렬화

Java 객체를 바이트 스트림으로 변환해 파일 저장, 네트워크 전송, 캐시 저장에 쓰는 것이 직렬화다. 역직렬화는 그 바이트 스트림을 다시 객체로 복원하는 과정이다.

실무에서 Java 기본 직렬화(`Serializable`)를 쓰는 경우는 드물다. Redis 캐시, 세션 클러스터링, 레거시 시스템 연동 정도다. 대부분은 Jackson으로 JSON을 다루는데, Jackson에서 터지는 문제가 훨씬 많다.

## Java 기본 직렬화와 serialVersionUID

`java.io.Serializable`을 구현하면 직렬화 대상이 된다. 메서드가 없는 마커 인터페이스다.

```java
class Person implements Serializable {
    private static final long serialVersionUID = 1L;

    private String name;
    private int age;
    private transient String password; // 직렬화에서 제외

    public Person(String name, int age, String password) {
        this.name = name;
        this.age = age;
        this.password = password;
    }
}
```

`transient` 필드는 직렬화 대상에서 빠진다. 역직렬화 후 해당 필드는 기본값(참조 타입은 `null`, 숫자는 `0`)으로 복원된다.

### serialVersionUID 없이 배포했다가 InvalidClassException 터진 상황

`serialVersionUID`를 명시하지 않으면 JVM이 클래스 구조를 기반으로 자동 생성한다. 필드 하나만 추가해도 이 값이 달라지고, 기존에 직렬화해둔 데이터를 읽을 때 `InvalidClassException`이 발생한다.

```
java.io.InvalidClassException: com.example.User;
  local class incompatible: stream classdesc serialVersionUID = -1234567890123456789,
  local class serialVersionUID = 9876543210987654321
```

Redis에 세션 데이터를 Java 직렬화로 저장하는 서비스에서 자주 겪는 일이다. `User` 클래스에 필드 하나 추가하고 배포했더니, 기존 세션을 가진 사용자들이 요청할 때마다 500 에러가 터진다. 세션 데이터 전체가 무효화되는 것과 마찬가지라 로그인한 사용자를 강제 로그아웃시키게 된다.

```java
// serialVersionUID 없이 배포했던 클래스
class User implements Serializable {
    private String name;
    private String email;
    // 여기에 필드 추가 시 자동 생성 UID 변경 → 기존 데이터 읽기 불가
}

// 명시적 선언으로 해결
class User implements Serializable {
    private static final long serialVersionUID = 1L;

    private String name;
    private String email;
    private String role; // 추가해도 UID가 같으므로 기존 데이터 읽기 가능
    // 단, 새 필드는 null로 복원됨
}
```

`serialVersionUID = 1L`로 고정해두면 필드를 추가하거나 삭제해도 기존 데이터를 읽는다. 단, 기존 필드의 타입을 바꾸는 건 UID가 같아도 역직렬화에 실패한다. `int age`를 `String age`로 바꾸면 깨진다.

## writeObject / readObject 커스텀 직렬화

기본 직렬화 동작을 바꿔야 할 때 `writeObject`와 `readObject`를 직접 정의한다.

실제로 쓰는 케이스는 두 가지다. 민감한 필드를 암호화해서 저장해야 하는 경우, 그리고 직렬화가 불가능한 필드(DB 커넥션, 스레드 풀 등)를 `transient`로 빼면서 역직렬화 후 재초기화가 필요한 경우다.

### 암호화 필드 저장

```java
class Account implements Serializable {
    private static final long serialVersionUID = 1L;

    private String username;
    private transient String secretKey; // 암호화 후 저장할 필드

    private void writeObject(ObjectOutputStream oos) throws IOException {
        oos.defaultWriteObject(); // transient 아닌 필드는 기본 직렬화
        String encrypted = encrypt(secretKey); // 실제로는 AES 같은 암호화 적용
        oos.writeObject(encrypted);
    }

    private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
        ois.defaultReadObject();
        String encrypted = (String) ois.readObject();
        this.secretKey = decrypt(encrypted);
    }

    private String encrypt(String value) {
        // 실제 구현에서는 AES/GCM 등 사용
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private String decrypt(String encoded) {
        return new String(Base64.getDecoder().decode(encoded), StandardCharsets.UTF_8);
    }
}
```

### 직렬화 불가 필드 처리

`ExecutorService`, `Connection` 같은 필드는 직렬화할 수 없다. `transient`로 빼고, 역직렬화 후 `readObject`에서 재초기화한다.

```java
class TaskProcessor implements Serializable {
    private static final long serialVersionUID = 1L;

    private String processorName;
    private transient ExecutorService executor; // 직렬화 불가 → transient 처리

    public TaskProcessor(String processorName) {
        this.processorName = processorName;
        this.executor = Executors.newFixedThreadPool(4);
    }

    private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
        ois.defaultReadObject();
        // 역직렬화 후 executor 재초기화
        this.executor = Executors.newFixedThreadPool(4);
    }
}
```

`writeObject`와 `readObject`는 반드시 `private`으로 선언한다. JVM이 리플렉션으로 호출하기 때문에 접근 제어자가 `private`이 아니면 무시된다. 쓰는 순서와 읽는 순서도 반드시 일치해야 한다.

## Jackson JSON 직렬화

실무에서 직렬화 문제의 대부분은 Jackson에서 발생한다.

### FAIL_ON_UNKNOWN_PROPERTIES 기본값과 롤링 배포 문제

Jackson `ObjectMapper`의 `FAIL_ON_UNKNOWN_PROPERTIES` 기본값은 `true`다. 이 설정이 켜져 있으면 JSON에 모르는 필드가 있을 때 역직렬화가 실패한다.

롤링 배포 중에 이게 문제가 된다. 신버전 인스턴스가 응답 JSON에 `newField`를 추가했는데, 아직 배포 중인 구버전 인스턴스가 그 응답을 받으면 `UnrecognizedPropertyException`이 터진다.

```
com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException:
  Unrecognized field "newField" (class com.example.Response),
  not marked as ignorable (3 known properties: ...)
```

구버전 인스턴스들이 신버전이 내려주는 응답을 파싱하지 못해 줄줄이 500을 반환하게 된다. 배포 중에 에러율이 치솟아서 롤백하는 상황이 생긴다.

```java
// 개별 클래스에 적용
@JsonIgnoreProperties(ignoreUnknown = true)
public class UserResponse {
    private String name;
    private String email;
    // newField가 JSON에 있어도 무시
}

// ObjectMapper 전역 설정
ObjectMapper mapper = new ObjectMapper();
mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
```

API 응답을 파싱하는 클라이언트 코드에는 `@JsonIgnoreProperties(ignoreUnknown = true)`를 붙이거나 `FAIL_ON_UNKNOWN_PROPERTIES`를 `false`로 설정해야 한다. 특히 마이크로서비스 간 통신에서 API가 발전하면서 필드가 추가될 경우 필수적이다.

### Spring Boot에서 ObjectMapper Bean 커스터마이징

Spring Boot는 기본 `ObjectMapper`를 자동 구성한다. 이 설정을 바꾸는 방법이 두 가지다.

**Jackson2ObjectMapperBuilderCustomizer 사용 (권장)**

Spring Boot의 기본 `ObjectMapper` 설정을 유지하면서 추가 설정만 덮어쓸 때 쓴다. `@Primary` 방식보다 사이드 이펙트가 적다.

```java
@Configuration
public class JacksonConfig {

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer customizer() {
        return builder -> builder
            .featuresToDisable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .featuresToEnable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
            .serializationInclusion(JsonInclude.Include.NON_NULL) // null 필드 제외
            .timeZone(TimeZone.getTimeZone("Asia/Seoul"));
    }
}
```

**@Primary ObjectMapper Bean 등록**

Spring Boot의 자동 구성을 완전히 대체할 때 쓴다. `MappingJackson2HttpMessageConverter` 등 Spring MVC 내부 컴포넌트가 이 Bean을 사용한다.

```java
@Configuration
public class JacksonConfig {

    @Bean
    @Primary
    public ObjectMapper objectMapper() {
        return new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false)
            .setSerializationInclusion(JsonInclude.Include.NON_NULL)
            .registerModule(new JavaTimeModule());
    }
}
```

`@Primary` Bean을 등록하면 Spring Boot의 `ObjectMapper` 자동 구성이 override된다. 직접 `ObjectMapper`를 만들면 `JavaTimeModule`처럼 기본으로 등록되는 모듈을 수동으로 등록해야 한다는 점을 놓치기 쉽다.

`LocalDateTime`을 JSON으로 직렬화할 때 `JavaTimeModule` 없이 `@Primary ObjectMapper`를 만들면 `[2026,7,15,10,30,0]` 같은 배열 형태로 출력된다. 자동 구성 `ObjectMapper`에는 이미 `JavaTimeModule`이 등록되어 있어서 `Jackson2ObjectMapperBuilderCustomizer`로 커스터마이징하면 이런 문제가 없다.

### 자주 쓰는 Jackson 어노테이션

```java
public class OrderResponse {

    @JsonProperty("order_id") // JSON 필드명 변경
    private Long orderId;

    @JsonIgnore // 직렬화/역직렬화에서 완전 제외
    private String internalNote;

    @JsonInclude(JsonInclude.Include.NON_NULL) // null이면 필드 자체를 제외
    private String optionalField;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Seoul")
    private LocalDateTime createdAt;

    @JsonAlias({"user_name", "userName"}) // 역직렬화 시 여러 이름을 허용
    private String username;
}
```

## 역직렬화 보안 이슈

신뢰할 수 없는 데이터를 `ObjectInputStream`으로 역직렬화하면 안 된다. Java 역직렬화 취약점의 단골 원인이다.

역직렬화 과정에서 `readObject`가 실행되는데, 공격자가 조작한 바이트 스트림을 넣으면 의도하지 않은 코드가 실행된다. Apache Commons Collections의 가젯 체인을 이용한 RCE 공격이 대표적이다. 2015년에 WebLogic, JBoss 등 주요 WAS가 이 방식으로 원격 코드 실행 공격에 노출됐다.

Java 9부터 `ObjectInputFilter`로 역직렬화할 클래스를 화이트리스트로 제한할 수 있다.

```java
ObjectInputStream ois = new ObjectInputStream(new FileInputStream("data.ser"));
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "com.myapp.model.*;!*"  // com.myapp.model 패키지만 허용, 나머지 거부
);
ois.setObjectInputFilter(filter);
Object obj = ois.readObject();
```

외부에서 받은 데이터(네트워크, 사용자 업로드 파일)를 `ObjectInputStream`으로 읽는 구조는 만들면 안 된다. 그 경로에는 JSON이나 Protobuf를 써야 한다.

직렬화가 필요 없는 클래스에서 역직렬화를 아예 차단하는 방법도 있다.

```java
class InternalConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    private void readObject(ObjectInputStream ois) throws IOException {
        throw new InvalidObjectException("역직렬화 허용하지 않음");
    }
}
```

## Java 직렬화 vs 현대적 대안

| 상황 | 포맷 |
|------|------|
| REST API 통신 | JSON (Jackson) |
| 마이크로서비스 내부 통신 (gRPC) | Protobuf |
| 설정 파일, 로그 | JSON |
| JVM 내부 캐시 (레거시) | Java 직렬화 |
| 외부로부터 받는 데이터 | JSON 또는 Protobuf — Java 직렬화 사용 금지 |

Java 기본 직렬화는 클래스 변경에 취약하고 보안 위험이 있다. Redis 캐시나 HTTP 세션에 객체를 저장할 때 Java 직렬화 대신 JSON으로 직렬화해서 저장하는 방식이 운영하기 훨씬 편하다. 클래스가 바뀌어도 `@JsonIgnoreProperties(ignoreUnknown = true)`로 필드 추가에 대응할 수 있고, Redis에 저장된 값을 눈으로 확인할 수 있다.
