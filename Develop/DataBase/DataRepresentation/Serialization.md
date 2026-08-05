---
title: "직렬화(Serialization)"
tags: [serialization, deserialization, json, protobuf, messagepack, avro, schema-registry, java]
updated: 2026-06-05
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

JSON 스키마를 그대로 쓸 수 있어서 도입 비용이 낮다. Redis에 객체를 캐시할 때 JSON 대신 MessagePack을 쓰면 메모리를 아낀다.

### Avro

Apache Hadoop 진영에서 나온 바이너리 포맷이다. Kafka 생태계에서 가장 많이 쓰는 포맷이기도 하다. Protobuf와 달리 스키마를 JSON으로 정의한다.

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example.user",
  "fields": [
    {"name": "userId", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": ["null", "string"], "default": null},
    {"name": "roles", "type": {"type": "array", "items": "string"}}
  ]
}
```

Avro의 가장 큰 특징은 **reader/writer 스키마 분리**다. 데이터를 쓸 때 사용한 스키마(writer schema)와 읽을 때 사용하는 스키마(reader schema)가 달라도 된다. Avro 런타임이 두 스키마를 비교해서 자동으로 변환한다.

```
Producer가 v1 스키마로 직렬화 → 바이트
Consumer가 v2 스키마로 역직렬화 → Avro가 v1과 v2를 매칭해서 필드 변환
```

이게 동작하려면 Consumer가 writer 스키마를 알아야 한다. 매번 메시지에 스키마를 통째로 붙이면 Avro의 작은 크기 장점이 사라진다. 그래서 보통 **Schema Registry**를 따로 둔다.

```
Producer:
  1. Schema Registry에 스키마 등록 → schema ID 받음
  2. 메시지 = [schema ID 4바이트] + [Avro 바이너리]

Consumer:
  1. 메시지에서 schema ID 추출
  2. Schema Registry에서 해당 스키마 조회 (캐시함)
  3. writer 스키마와 자기 reader 스키마로 역직렬화
```

Kafka에서 Confluent Schema Registry를 쓰는 일반적인 흐름이다. 메시지 본문에는 1바이트 magic byte와 4바이트 schema ID만 추가된다.

**장점:**

- 필드 이름을 바이트에 포함하지 않아서 Protobuf보다도 작은 경우가 있다
- 스키마 진화 규칙이 엄격하게 정의되어 있다
- reader/writer 스키마 분리로 호환성 처리가 자연스럽다
- 동적 스키마 처리가 쉽다. 코드 생성 없이도 GenericRecord로 다룰 수 있다

**단점:**

- Schema Registry라는 별도 인프라가 필요하다
- Protobuf 대비 학습 곡선이 있다
- 위치 기반 인코딩이라서 필드 순서가 의미를 가진다. 스키마 없이는 디코딩이 절대 불가능하다

### 포맷 비교 정리

| 항목 | JSON | Protobuf | MessagePack | Avro |
|------|------|----------|-------------|------|
| 형식 | 텍스트 | 바이너리 | 바이너리 | 바이너리 |
| 사람 읽기 | 가능 | 불가 | 불가 | 불가 |
| 스키마 | 없음 | 필수(.proto) | 없음 | 필수(.avsc, JSON) |
| 스키마 위치 | 메시지 내부(필드명) | 외부 공유 | 메시지 내부(필드명) | 외부 + Schema Registry |
| 크기 | 큼 | 작음 | 중간 | 가장 작음 |
| 속도 | 느림 | 빠름 | 중간 | 빠름 |
| 식별 방식 | 필드명 | 필드 번호 | 필드명 | 위치 + 스키마 매칭 |
| 동적 처리 | 쉬움 | 어려움(코드 생성) | 쉬움 | 쉬움(GenericRecord) |
| 언어 지원 | 거의 전부 | 코드 생성 필요 | 대부분 지원 | JVM 중심, 다른 언어 지원도 있음 |
| 대표 사용처 | REST API | gRPC | Redis 캐시 | Kafka, 빅데이터 파이프라인 |


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

Protobuf는 양쪽이 같은 .proto 파일을 공유한다는 전제가 깔려 있다. .proto만 잘 관리하면 호환성이 따라온다. 반대로 말하면, .proto 파일을 한 군데서 단일 진실로 관리하지 않으면 호환성이 깨진다. monorepo로 .proto를 모아두거나, BSR(Buf Schema Registry) 같은 별도 registry로 배포하는 방식이 일반적이다.

### Avro에서의 호환성

Avro는 reader 스키마와 writer 스키마가 다를 수 있다는 전제로 설계됐다. 호환성 규칙도 그 전제 위에서 정의된다.

```json
// v1 writer schema
{"type": "record", "name": "User", "fields": [
  {"name": "userId", "type": "int"},
  {"name": "name", "type": "string"}
]}

// v2 writer schema - email 필드 추가
{"type": "record", "name": "User", "fields": [
  {"name": "userId", "type": "int"},
  {"name": "name", "type": "string"},
  {"name": "email", "type": ["null", "string"], "default": null}
]}
```

새 필드를 추가할 때는 반드시 **default 값**을 지정해야 한다. v1으로 직렬화된 데이터를 v2 reader가 읽으면 email 필드가 없는데, default가 없으면 어떤 값을 채울지 모르기 때문이다.

지켜야 할 규칙:

- 새 필드는 default 값 필수
- 필드를 삭제할 때도 원래 스키마에 default가 있어야 한다 (옛날 데이터를 새 스키마로 읽을 때 사용됨)
- 필드 이름 변경은 alias로 처리한다
- 타입 변경은 promotion 규칙 안에서만 허용된다 (int → long, int → float 등)

### Confluent Schema Registry 호환성 모드

Kafka + Avro를 쓸 때 Schema Registry가 자동으로 호환성 검사를 해준다. 호환성 모드를 토픽별로 설정할 수 있는데, 각 모드의 의미를 정확히 알아야 한다.

| 모드 | 새 스키마가 만족해야 할 조건 | 안전하게 할 수 있는 변경 |
|------|------------------------------|--------------------------|
| `BACKWARD` (기본) | 새 reader가 직전 writer 데이터를 읽을 수 있어야 한다 | optional 필드 추가, default 있는 필드 삭제 |
| `BACKWARD_TRANSITIVE` | 새 reader가 **모든 이전 버전** writer 데이터를 읽을 수 있어야 한다 | BACKWARD와 동일하지만 모든 과거 버전과 호환 |
| `FORWARD` | 직전 reader가 새 writer 데이터를 읽을 수 있어야 한다 | required 필드 추가, optional 필드 삭제 |
| `FORWARD_TRANSITIVE` | 모든 이전 reader가 새 writer 데이터를 읽을 수 있어야 한다 | FORWARD와 동일하지만 모든 과거 버전과 호환 |
| `FULL` | BACKWARD + FORWARD 둘 다 | default 있는 optional 필드 추가/삭제만 |
| `FULL_TRANSITIVE` | 모든 이전 버전과 양방향 호환 | 가장 엄격, 변경 자유도가 낮다 |
| `NONE` | 검사 안 함 | 자유롭지만 위험하다 |

배포 순서가 어떻게 되느냐에 따라 모드를 골라야 한다.

- **Consumer를 먼저 배포하고 Producer를 나중에 배포**: `BACKWARD` (새 Consumer가 옛 Producer 데이터를 읽어야 함)
- **Producer를 먼저 배포하고 Consumer를 나중에 배포**: `FORWARD` (옛 Consumer가 새 Producer 데이터를 읽어야 함)
- **배포 순서를 통제 못 함**: `FULL`
- **이전 모든 버전과의 호환성이 필요**: `_TRANSITIVE` 접미사 붙은 모드 사용

기본값이 `BACKWARD`인 이유는 Kafka 운영에서 Consumer를 먼저 배포하는 패턴이 가장 흔하기 때문이다. Consumer 코드를 새 스키마로 먼저 바꾸고, 그 다음 Producer가 새 포맷으로 메시지를 보내기 시작한다.

```java
// Spring Kafka에서 KafkaAvroSerializer 사용 예
Map<String, Object> props = new HashMap<>();
props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, KafkaAvroSerializer.class);
props.put("schema.registry.url", "http://schema-registry:8081");
props.put("auto.register.schemas", false); // 운영에선 false 권장
```

`auto.register.schemas=true`로 두면 Producer가 띄울 때마다 스키마를 자동 등록하는데, 실수로 호환되지 않는 스키마가 올라가서 Registry 자체가 망가지는 경우가 있다. CI/CD에서 명시적으로 등록하는 방식이 안전하다.

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
- **내부 마이크로서비스 간 통신**: Protobuf + gRPC. 타입 안전성과 성능 둘 다 잡힌다
- **Kafka 메시지, 이벤트 스트리밍**: Avro + Schema Registry. 스키마 진화 규칙이 가장 정리되어 있다
- **캐시 저장**: MessagePack이나 Protobuf. JSON보다 크기가 작아서 메모리가 절약된다
- **빅데이터 파일 포맷**: Avro(행 기반) 또는 Parquet(열 기반). Avro는 Hadoop, Spark, Flink와 잘 맞는다
- **로그 저장**: JSON. 검색과 분석이 쉽다
- **Java 기본 직렬화**: 쓰지 않는다. 보안 문제가 심각하고, 언어 종속적이라 다른 시스템과 호환이 안 된다

## 더 읽기

- [직렬화 포맷 심화 — JSON·Protobuf·MessagePack·Avro 비교, 스키마 진화, 성능·보안](Serialization_Formats_Deep_Dive.md): 같은 페이로드를 4종 포맷으로 직접 인코딩해 바이트 크기·인코딩 속도를 비교하고, 운영에서 겪은 호환성 사고와 역직렬화 공격 사례를 다룬다.
