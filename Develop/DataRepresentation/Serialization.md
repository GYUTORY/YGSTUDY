---
title: "직렬화(Serialization)"
tags: [serialization, deserialization, json, protobuf, messagepack, java]
updated: 2026-03-24
---

# 직렬화(Serialization)

## 직렬화가 뭔가

메모리에 있는 객체를 바이트 스트림으로 변환하는 과정이다. 네트워크로 데이터를 보내거나, 파일에 저장하거나, 캐시에 넣을 때 반드시 거치는 단계다.

반대로 바이트 스트림을 다시 객체로 복원하는 과정을 **역직렬화(Deserialization)**라고 한다.

```
객체 → [직렬화] → 바이트 스트림 → [역직렬화] → 객체
```

단순해 보이지만, 실제로는 포맷 선택, 성능, 보안, 버전 호환성까지 신경 써야 할 게 많다.


## 포맷별 차이

### JSON

가장 널리 쓰이는 텍스트 기반 포맷이다. 사람이 읽을 수 있고 디버깅이 쉽다.

```json
{
  "userId": 12345,
  "name": "홍길동",
  "roles": ["ADMIN", "USER"]
}
```

**장점:**

- 거의 모든 언어에서 지원한다
- 디버깅할 때 눈으로 바로 확인 가능하다
- REST API 표준처럼 쓰인다

**단점:**

- 바이너리 대비 크기가 크다. 필드명이 매번 반복되니까
- 파싱 속도가 느리다
- 타입 정보가 없다. 숫자가 int인지 long인지 구분 못 한다

실무에서 JSON은 외부 API 통신용으로 쓰고, 내부 서비스 간 통신에는 바이너리 포맷을 고려하는 경우가 많다.

### Protocol Buffers (Protobuf)

Google이 만든 바이너리 직렬화 포맷이다. `.proto` 파일에 스키마를 정의한다.

```protobuf
syntax = "proto3";

message User {
  int32 user_id = 1;
  string name = 2;
  repeated string roles = 3;
}
```

필드 번호(1, 2, 3)가 핵심이다. 이 번호로 필드를 식별하기 때문에 필드명을 바꿔도 호환성이 유지된다.

**장점:**

- JSON 대비 크기가 3~10배 작다
- 파싱 속도가 빠르다
- 스키마가 있어서 타입 안전성이 보장된다
- 하위 호환성 관리가 잘 된다

**단점:**

- `.proto` 파일 관리와 코드 생성 과정이 필요하다
- 바이너리라서 사람이 읽을 수 없다. 디버깅할 때 별도 도구가 필요하다
- 스키마 없이는 디코딩이 안 된다

gRPC를 쓰면 자연스럽게 Protobuf를 사용하게 된다.

### MessagePack

JSON과 호환되는 바이너리 포맷이다. JSON의 구조를 그대로 쓰면서 크기만 줄인다.

```java
// Java - MessagePack 사용 예
ObjectMapper mapper = new ObjectMapper(new MessagePackFactory());
byte[] bytes = mapper.writeValueAsBytes(user);
User restored = mapper.readValue(bytes, User.class);
```

JSON 스키마를 그대로 쓸 수 있어서 도입 비용이 낮다. Redis에 객체를 캐시할 때 JSON 대신 MessagePack을 쓰면 메모리를 아낄 수 있다.

### 포맷 비교 정리

| 항목 | JSON | Protobuf | MessagePack |
|------|------|----------|-------------|
| 형식 | 텍스트 | 바이너리 | 바이너리 |
| 사람 읽기 | 가능 | 불가 | 불가 |
| 스키마 | 없음 | 필수 | 없음 |
| 크기 | 큼 | 작음 | 중간 |
| 속도 | 느림 | 빠름 | 중간 |
| 언어 지원 | 거의 전부 | 코드 생성 필요 | 대부분 지원 |


## Java의 직렬화

### ObjectOutputStream (기본 직렬화)

Java에 내장된 직렬화 방식이다. `Serializable` 인터페이스를 구현하면 된다.

```java
public class User implements Serializable {
    private static final long serialVersionUID = 1L;
    private int userId;
    private String name;
    private transient String password; // 직렬화에서 제외
}

// 직렬화
try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("user.dat"))) {
    oos.writeObject(user);
}

// 역직렬화
try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream("user.dat"))) {
    User restored = (User) ois.readObject();
}
```

`serialVersionUID`를 명시하지 않으면 컴파일러가 자동 생성한다. 클래스 구조가 바뀌면 이 값이 달라져서 `InvalidClassException`이 터진다. 반드시 직접 선언해야 한다.

`transient` 키워드를 붙이면 해당 필드는 직렬화에서 빠진다. 비밀번호 같은 민감 정보에 사용한다.

**실무에서는 Java 기본 직렬화를 쓰지 않는다.** 이유는 아래에서 설명한다.

### Jackson (JSON 직렬화)

실무에서 가장 많이 쓰는 Java JSON 라이브러리다. Spring Boot의 기본 JSON 처리기이기도 하다.

```java
ObjectMapper mapper = new ObjectMapper();

// 직렬화
String json = mapper.writeValueAsString(user);

// 역직렬화
User user = mapper.readValue(json, User.class);

// 날짜 처리 - 기본값이 timestamp라서 명시적으로 설정해야 한다
mapper.registerModule(new JavaTimeModule());
mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
```

자주 겪는 문제들:

```java
// 1. 알 수 없는 필드가 오면 에러 발생 → 무시 설정
mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

// 2. null 필드 제외
@JsonInclude(JsonInclude.Include.NON_NULL)
public class User { ... }

// 3. 필드명 변환
@JsonProperty("user_id")
private int userId;
```

`ObjectMapper`는 생성 비용이 크다. 매번 새로 만들지 말고 싱글톤으로 재사용해야 한다. thread-safe하니까 걱정 안 해도 된다.


## 역직렬화 보안 취약점

### 왜 위험한가

Java 기본 직렬화(`ObjectInputStream`)는 바이트 스트림을 받아서 객체를 복원한다. 이 과정에서 **클래스의 생성자가 아니라 내부 메커니즘으로 객체가 만들어진다.** 공격자가 조작된 바이트 스트림을 보내면 서버에서 임의 코드가 실행될 수 있다.

2015년 Apache Commons Collections 라이브러리의 역직렬화 취약점이 공개되면서 대규모 보안 사고가 발생했다. WebLogic, JBoss, Jenkins 등 Java 기반 서비스들이 영향을 받았다.

### 공격 원리

```java
// 이런 코드가 있으면 공격 대상이 된다
ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
Object obj = ois.readObject(); // 여기서 임의 코드 실행 가능
```

공격자는 `readObject()` 시점에 호출되는 메서드 체인(gadget chain)을 조합해서 `Runtime.exec()`까지 도달하는 페이로드를 만든다. ysoserial 같은 도구로 이런 페이로드를 자동 생성할 수 있다.

### 방어 방법

**1. Java 기본 직렬화를 쓰지 않는다**

가장 확실한 방법이다. JSON이나 Protobuf 같은 데이터 전용 포맷을 쓰면 임의 코드 실행 자체가 불가능하다.

**2. 어쩔 수 없이 써야 한다면 화이트리스트를 적용한다**

```java
// Java 9+ ObjectInputFilter
ObjectInputStream ois = new ObjectInputStream(input);
ois.setObjectInputFilter(filterInfo -> {
    Class<?> clazz = filterInfo.serialClass();
    if (clazz != null) {
        // 허용된 클래스만 역직렬화
        if (clazz == User.class || clazz == Address.class) {
            return ObjectInputFilter.Status.ALLOWED;
        }
        return ObjectInputFilter.Status.REJECTED;
    }
    return ObjectInputFilter.Status.UNDECIDED;
});
```

**3. 의존성 라이브러리 점검**

classpath에 gadget chain으로 악용 가능한 라이브러리가 있으면 위험하다. Apache Commons Collections 3.x, Spring Framework의 일부 클래스 등이 해당한다. 최신 버전으로 업데이트하거나 사용하지 않는 라이브러리는 제거한다.

### Jackson도 안전하지 않은 경우

Jackson에서 `enableDefaultTyping()`을 켜면 JSON에 타입 정보가 포함된다. 이 상태에서 다형성 역직렬화를 하면 Java 기본 직렬화와 비슷한 공격이 가능하다.

```java
// 이렇게 하면 안 된다
mapper.enableDefaultTyping(); // deprecated된 이유가 있다

// 다형성이 필요하면 명시적으로 허용할 타입을 지정한다
mapper.activateDefaultTyping(
    mapper.getPolymorphicTypeValidator(),
    ObjectMapper.DefaultTyping.NON_FINAL,
    JsonTypeInfo.As.PROPERTY
);
```


## 버전 호환성 문제

서비스가 운영되면 직렬화 포맷은 반드시 변경된다. 필드가 추가되고, 삭제되고, 타입이 바뀐다. 이때 구버전과 신버전이 공존하는 상황을 처리해야 한다.

### 하위 호환성(Backward Compatibility)

새 코드가 옛날 데이터를 읽을 수 있어야 한다.

### 상위 호환성(Forward Compatibility)

옛날 코드가 새 데이터를 읽을 수 있어야 한다.

### JSON에서의 호환성

```java
// 필드 추가: 새 필드에 기본값을 넣으면 하위 호환 유지
public class User {
    private int userId;
    private String name;
    private String email = ""; // 새로 추가된 필드
}

// 필드 삭제: FAIL_ON_UNKNOWN_PROPERTIES = false면 상위 호환 유지
// 옛날 데이터에 있는 필드를 새 코드가 모르면 무시한다
```

JSON은 스키마가 없어서 유연하지만, 그만큼 실수하기도 쉽다. 필드 타입을 바꾸면(int → string) 양쪽 다 깨진다.

### Protobuf에서의 호환성

Protobuf는 필드 번호 기반이라서 호환성 관리가 상대적으로 수월하다.

```protobuf
message User {
  int32 user_id = 1;
  string name = 2;
  string email = 3;     // 새로 추가 - 구버전은 이 필드를 무시한다
  // string phone = 4;  // 삭제할 때는 필드 번호를 reserved로 막는다
  reserved 4;
}
```

지켜야 할 규칙:

- 이미 사용 중인 필드 번호를 다른 필드에 재사용하면 안 된다
- 필드 타입을 바꾸면 안 된다 (int32 → int64는 호환되지만 int32 → string은 안 된다)
- `required` 필드는 쓰지 않는다 (proto3에서는 아예 제거됨)
- 삭제한 필드는 `reserved`로 번호를 잠근다

### 실무에서 자주 발생하는 문제

**캐시 역직렬화 실패**: Redis에 캐시된 데이터가 클래스 변경 후 역직렬화에 실패하는 경우가 흔하다. 배포할 때 캐시 키에 버전을 포함시키거나, 배포 전에 캐시를 비우는 절차가 필요하다.

```java
// 캐시 키에 버전 포함
String cacheKey = "user:v2:" + userId;
```

**Kafka 메시지 호환성**: Producer가 먼저 배포되고 Consumer가 나중에 배포되는 경우, Consumer가 새 포맷을 모르면 처리가 멈춘다. Schema Registry를 사용해서 호환성을 검증하는 게 안전하다.

**DB 컬럼 변경**: JPA 엔티티의 필드 타입을 바꿀 때 DB 마이그레이션과 코드 배포 순서를 잘못 잡으면 장애가 난다. 필드 추가 → 코드 배포 → 기존 필드 제거 순서로 진행해야 한다.


## 어떤 포맷을 쓸지 판단하는 기준

- **외부 API, 프론트엔드 통신**: JSON. 다른 선택지가 없다
- **내부 마이크로서비스 간 통신**: Protobuf + gRPC. 타입 안전성과 성능 둘 다 잡을 수 있다
- **캐시 저장**: MessagePack이나 Protobuf. JSON보다 크기가 작아서 메모리 절약된다
- **로그 저장**: JSON. 검색과 분석이 쉽다
- **Java 기본 직렬화**: 쓰지 않는다. 보안 문제가 심각하고, 언어 종속적이라 다른 시스템과 호환이 안 된다
