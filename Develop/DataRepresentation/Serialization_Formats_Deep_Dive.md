---
title: 직렬화 포맷 심화 — JSON·Protobuf·MessagePack·Avro 비교, 스키마 진화, 성능·보안
tags:
  - serialization
  - json
  - protobuf
  - messagepack
  - avro
  - schema-evolution
  - kafka
  - grpc
  - security
updated: 2026-06-05
---

## 들어가기 전에

직렬화 포맷 선택은 보통 "JSON 쓰면 되지 뭐"로 끝난다. 그러다 트래픽이 늘고, Kafka에 메시지가 쌓이고, gRPC로 마이크로서비스가 갈라지면 그제야 바이트 크기·스키마 진화·역직렬화 보안이 한꺼번에 문제로 튀어나온다.

이 문서는 4종 포맷(JSON, Protobuf, MessagePack, Avro)을 같은 페이로드로 비교하고, 운영하면서 실제로 터졌던 호환성 사고와 보안 이슈를 정리한다. 포맷 자체의 문법은 짧게 넘기고, 실제 장애 사례와 그 원인을 중심으로 다룬다.

---

## 1. 4종 포맷 한눈에 보기

| 포맷 | 스키마 | 인코딩 | 사람이 읽음 | 자기기술(self-describing) | 주 사용처 |
|------|--------|--------|-------------|---------------------------|-----------|
| JSON | 없음 | 텍스트 | 가능 | 부분 (필드명 포함) | REST API, 설정 파일 |
| MessagePack | 없음 | 바이너리 | 불가 | 부분 (필드명 포함) | Redis 캐시, IPC |
| Protobuf | 있음 (.proto) | 바이너리 (tag-value) | 불가 | 아니오 (스키마 필요) | gRPC, Kafka |
| Avro | 있음 (.avsc, JSON) | 바이너리 (위치 기반) | 불가 | 메시지에 포함 가능 | Kafka + Schema Registry, 빅데이터 |

여기서 중요한 분기점은 두 가지다.

- **스키마 유무**: 스키마가 없으면 필드 이름을 모든 메시지에 같이 보내야 한다. 바이트가 커지고, 스키마 진화 규칙도 약하다.
- **자기기술 여부**: Avro는 reader/writer schema가 다를 수 있다는 전제로 설계됐다. Protobuf는 같은 .proto를 양쪽이 공유한다는 전제로 설계됐다. 이 철학 차이가 호환성 모드 차이로 이어진다.

---

## 2. 같은 페이로드 비교 — 바이트 크기와 성능

다음 페이로드를 4종 포맷으로 인코딩했을 때 크기 차이를 보자.

```json
{
  "userId": 12345678,
  "name": "김개발",
  "email": "dev@example.com",
  "isActive": true,
  "tags": ["backend", "kafka"],
  "createdAt": 1717545600
}
```

### 2.1 바이트 크기 비교

| 포맷 | 크기(byte) | 비고 |
|------|-----------|------|
| JSON (공백 없음) | 약 130 | 필드명·따옴표·콤마가 절반 이상 차지 |
| MessagePack | 약 95 | 필드명은 그대로지만 정수/불리언이 1~5바이트로 줄어듦 |
| Protobuf | 약 55 | 필드명 없음, varint로 정수 압축 |
| Avro (스키마 별도) | 약 45 | 필드명·태그 둘 다 없음, 위치 기반 |
| Avro (Single-Object Encoding) | 약 55 | 메시지에 schema fingerprint 10바이트 포함 |

JSON 130바이트가 Avro 45바이트로 줄면 약 65% 감소다. 1초에 10만 건 처리하는 Kafka 토픽이면 일 단위로 수십 GB 차이가 난다. 디스크보다 네트워크 비용(AWS 같은 클라우드의 cross-AZ traffic)에서 먼저 체감된다.

### 2.2 정수 인코딩 차이 — 왜 Protobuf가 작은가

JSON은 정수를 ASCII 문자열로 직렬화한다. `12345678`은 8바이트다. Protobuf의 varint는 7비트씩 끊어서 가변 길이로 인코딩하니 `12345678`은 4바이트면 된다. 작은 정수일수록 차이가 크다.

```
JSON:        "12345678"           → 8 bytes
MessagePack: 0xCE 00 BC 61 4E     → 5 bytes (uint32)
Protobuf:    0xCE C2 F1 05        → 4 bytes (varint)
Avro:        0x9C 85 A6 0B        → 4 bytes (zigzag varint)
```

**조심할 점**: varint는 음수에 비효율적이다. `-1`은 64비트 음수로 보면 모든 비트가 1이라 varint로 10바이트가 된다. Protobuf의 `int32`/`int64`로 음수를 자주 쓰면 이 함정에 빠진다. 음수가 자주 나오면 `sint32`/`sint64`(zigzag 인코딩)를 써야 한다. Avro는 정수에 기본적으로 zigzag varint를 쓰니 신경 안 써도 된다.

### 2.3 인코딩/디코딩 속도 (참고치)

벤치마크는 JVM 환경, 같은 페이로드 100만 건 기준 대략값이다(라이브러리·하드웨어에 따라 다르다).

| 포맷 | 인코딩(μs/op) | 디코딩(μs/op) | 비고 |
|------|---------------|---------------|------|
| Jackson JSON | 약 2.5 | 약 3.0 | 리플렉션 캐시 따뜻한 상태 |
| Jackson Smile (binary JSON) | 약 1.8 | 약 2.0 | |
| MessagePack (jackson-dataformat-msgpack) | 약 1.6 | 약 1.8 | |
| Protobuf (생성 코드) | 약 0.6 | 약 0.8 | 리플렉션 안 씀 |
| Avro (SpecificRecord) | 약 0.7 | 약 1.0 | 코드 생성 사용 시 |
| Avro (GenericRecord) | 약 1.5 | 약 2.0 | 리플렉션·맵 사용 시 |

JSON이 느린 이유는 문자열 파싱이다. 숫자 하나를 만들려고 8바이트를 한 글자씩 읽고 곱셈으로 누적해야 한다. Protobuf는 4바이트를 비트 시프트로 읽는다. 같은 정수를 만드는데 명령어 수가 한 자릿수 차이 난다.

### 2.4 CPU·메모리

JSON 파싱은 임시 String 객체를 많이 만든다. JVM에서는 이게 GC 압력으로 돌아온다. p99 레이턴시가 튀는 서비스에서 JSON을 Protobuf로 바꿨더니 young GC 빈도가 절반 이하로 떨어진 경우가 있다.

반대로 Protobuf의 약점은 디버깅이다. tcpdump로 패킷을 떠도 바이트 덤프만 나온다. `protoc --decode_raw`로 추측은 할 수 있지만 필드 이름이 안 보인다. 운영 중에 페이로드가 이상해서 잡으려고 하면 JSON이 훨씬 편하다.

---

## 3. 스키마 진화 — 진짜 사고가 나는 곳

### 3.1 진화의 두 방향

스키마 변경은 두 방향이 있다.

- **Backward 호환**: 새 스키마로 옛 메시지를 읽을 수 있다. (= 컨슈머를 먼저 배포)
- **Forward 호환**: 옛 스키마로 새 메시지를 읽을 수 있다. (= 프로듀서를 먼저 배포)

운영 환경에서는 보통 Backward가 기본이다. 컨슈머를 먼저 새 스키마로 올리고, 그다음 프로듀서를 올린다. 카나리 배포 중에는 두 버전이 동시에 흐르니 Full(양방향) 호환이 안전하다.

### 3.2 JSON — 사실상 스키마가 없으니 "관행"으로 진화

JSON은 스키마가 없으니 "필드 추가는 무시되고, 필드 삭제는 null로 처리한다"는 관행에 의존한다. Jackson은 `@JsonIgnoreProperties(ignoreUnknown = true)`를 안 붙이면 새 필드가 추가됐을 때 컨슈머가 `UnrecognizedPropertyException`을 던지며 뻗는다.

실무 사고 패턴은 이렇다.

1. 백엔드가 응답에 `couponCode` 필드를 추가한다.
2. iOS 앱은 `ignoreUnknown` 기본값이 false로 빌드돼 있다.
3. 구버전 앱 사용자가 결제 화면에서 전부 죽는다.
4. 핫픽스로 백엔드가 필드를 다시 빼고, 다음 앱 출시에 옵션을 켠다.

JSON 쓰는 곳은 항상 컨슈머가 알 수 없는 필드를 무시하도록 강제해야 한다. 그렇지 않으면 backward 호환이 깨진다.

### 3.3 Protobuf — 필드 번호가 전부다

Protobuf는 메시지를 `tag(field number) + wire type + value` 시퀀스로 직렬화한다. 필드 이름은 바이트에 들어가지 않는다. 호환성을 결정하는 건 오직 **필드 번호와 wire type**이다.

#### 허용되는 변경

- 새 필드 추가 (기존에 없던 번호 사용): backward·forward 모두 안전.
- 필드 삭제: 단, 그 번호는 영구히 `reserved`로 막아야 한다.
- `optional` 필드를 `repeated`로 변경 (proto3에서, packed=false인 경우): 같은 wire type이라 가능.
- `int32`, `uint32`, `int64`, `uint64`, `bool` 사이의 변경: 같은 varint wire type이라 바이트가 다시 해석된다(다만 의미가 망가지니 사실상 위험).

#### 금지되는 변경

- 필드 번호 재사용 — 가장 큰 사고 원인.
- 필드 타입을 다른 wire type으로 변경 (`int32` → `string` 같은 것).
- `required` 추가 (proto2에서 — proto3는 `required` 자체가 없음).

#### reserved를 안 쓴 사고

```protobuf
// v1
message Order {
  int64 order_id = 1;
  string product_code = 2;
  int32 quantity = 3;
}

// v2 — 누군가 product_code를 빼고 그 번호를 재사용
message Order {
  int64 order_id = 1;
  int32 discount_percent = 2;  // 사고
  int32 quantity = 3;
}
```

옛 프로듀서가 보낸 `product_code = "ABC-001"` 메시지를 새 컨슈머가 받으면, wire type이 length-delimited(2)이고 새 스키마의 `discount_percent`는 varint(0)다. wire type 미스매치라 파서가 그냥 무시하거나 에러를 던진다. 더 운 나쁘면 wire type이 우연히 맞아서 `discount_percent`에 쓰레기 값이 들어간다.

이걸 막으려면 항상 다음과 같이 reserved를 박아야 한다.

```protobuf
message Order {
  reserved 2;
  reserved "product_code";
  int64 order_id = 1;
  int32 quantity = 3;
  int32 discount_percent = 4;  // 새 번호 사용
}
```

`reserved`는 컴파일 타임에 번호·이름 재사용을 막아준다. PR 리뷰에서 사람의 눈에 기대지 말고 컴파일러에게 시켜라.

### 3.4 Avro — reader/writer schema라는 발상

Avro는 메시지에 필드 번호도 없고 필드 이름도 없다. 그냥 스키마에 정의된 순서대로 값만 나열한다. 그래서 메시지를 읽을 때는 반드시 두 개의 스키마가 필요하다.

- **Writer schema**: 메시지를 쓸 때 사용한 스키마.
- **Reader schema**: 메시지를 읽을 때 사용하는 스키마.

둘이 다를 수 있다는 게 Avro 설계의 핵심이다. Avro의 resolution rules가 두 스키마를 맞춰서 변환해준다.

```
writer:   {name: string, age: int}
reader:   {name: string, age: int, email: string = "unknown"}
```

reader에 추가된 `email` 필드에 기본값이 있으면 옛 메시지를 읽어도 `"unknown"`이 채워진다. 기본값 없는 필드를 추가하면 옛 메시지를 못 읽는다(backward 호환 깨짐).

#### Avro에서 허용되는 변경

- 기본값 있는 필드 추가/삭제: 양방향 호환.
- 필드 이름 변경: `aliases` 사용 시 가능.
- 타입 promotion: `int` → `long` → `float` → `double`, `string` ↔ `bytes` 등 일부 허용.

#### Avro에서 금지/위험

- 기본값 없는 필드 추가: backward 깨짐.
- 필드 이름 변경하면서 aliases 안 단 경우.
- enum 값 추가: reader에 없는 enum 심볼이 오면 `AvroTypeException`. Avro 1.10부터 기본값이 있으면 fallback 가능.
- `union [null, T]` → `T`로 변경: null이던 옛 메시지를 못 읽음.

### 3.5 Schema Registry 호환성 모드

Confluent Schema Registry, AWS Glue Schema Registry 같은 곳에서 스키마 등록 시 강제하는 호환성 모드가 있다. 이게 실제로 운영에서 가장 중요한 설정이다.

| 모드 | 의미 | 컨슈머/프로듀서 배포 순서 |
|------|------|---------------------------|
| BACKWARD | 새 스키마로 옛 메시지를 읽을 수 있다 (기본값) | 컨슈머 먼저 |
| BACKWARD_TRANSITIVE | 새 스키마가 모든 과거 버전 메시지를 읽을 수 있다 | 컨슈머 먼저 |
| FORWARD | 옛 스키마로 새 메시지를 읽을 수 있다 | 프로듀서 먼저 |
| FORWARD_TRANSITIVE | 모든 과거 스키마가 새 메시지를 읽을 수 있다 | 프로듀서 먼저 |
| FULL | BACKWARD + FORWARD (직전 버전과) | 순서 무관 |
| FULL_TRANSITIVE | BACKWARD + FORWARD (모든 과거 버전과) | 순서 무관 |
| NONE | 호환성 검사 안 함 | 사고 책임 본인 |

**TRANSITIVE의 의미**: 그냥 BACKWARD는 "직전 버전과만" 호환되면 통과시킨다. v1 → v2 → v3로 갈 때 v3가 v1과 호환되지 않아도 v2와만 호환되면 통과한다. 그런데 운영 환경에는 v1 메시지가 토픽에 남아있을 수 있다. 컨슈머는 retention 기간 안의 모든 메시지를 처리할 수 있어야 한다. 그래서 정말로 안전한 건 `BACKWARD_TRANSITIVE`다.

**FULL_TRANSITIVE를 강제하면 안 되는 경우**: 너무 엄격해서 거의 어떤 변경도 안 받아준다. 예를 들어 신규 필드를 default 없이 추가하는 건 forward 깨짐이라 FULL에서 막힌다. 신규 필드를 도입하려면 default를 반드시 설정해야 한다.

실무에서는 `BACKWARD_TRANSITIVE`를 기본으로 깔고, 결제·정산처럼 절대 망가지면 안 되는 토픽만 `FULL_TRANSITIVE`로 올린다.

### 3.6 MessagePack의 스키마 진화

MessagePack은 JSON처럼 자기기술이지만 스키마는 따로 정의하지 않는다. 그래서 진화 규칙도 JSON과 비슷하다. 객체(map)를 쓰면 필드 이름이 키로 들어가 있어서 추가/삭제는 컨슈머가 알아서 처리해야 한다.

배열(array) 기반으로 쓰면 더 작아지지만(필드 이름 없음), 위치 기반이라 필드 순서·개수 변경이 전부 깨진다. msgpack-python의 `use_list=True` 같은 옵션을 켜면 array가 list로 매핑된다. Redis에 캐시할 때 array를 쓰면 나중에 클래스 필드 순서가 바뀌어서 캐시가 다 깨지는 사고를 본 적 있다. **MessagePack은 무조건 map 인코딩으로 써라.** 바이트 좀 더 크더라도 그게 살길이다.

---

## 4. 보안 이슈 — 역직렬화는 코드 실행이다

직렬화 포맷의 가장 큰 함정은 "데이터를 읽는 것"이 사실 "코드를 실행하는 것"이라는 점이다. 신뢰할 수 없는 입력을 역직렬화하면 RCE로 이어진다.

### 4.1 Java ObjectInputStream — 역사상 최악의 패턴

Java 기본 직렬화는 `Serializable` 인터페이스만 구현하면 임의 객체를 바이트로 변환한다. 문제는 역직렬화 시점에 `readObject()`가 호출되는데, 이게 임의 코드 실행 지점이다.

```java
// 절대 하면 안 되는 코드
ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
Object obj = ois.readObject();
```

`commons-collections` 같은 라이브러리에 있는 `InvokerTransformer` 체인을 조합하면 임의 명령어 실행이 된다. ysoserial이라는 도구로 페이로드가 양산된다. 2015년 Apache Commons Collections RCE(CVE-2015-7501) 이후 거의 모든 Java 직렬화 RCE가 같은 패턴이다.

**대응**:

- `ObjectInputStream`을 외부 입력에 절대 쓰지 마라.
- 어쩔 수 없이 써야 하면 Java 9+의 `ObjectInputFilter`로 클래스 화이트리스트를 강제하라.
- RMI, JMX, JNDI(LDAP/RMI lookup)가 내부에서 ObjectInputStream을 쓴다. 외부 노출하지 마라.
- Log4Shell(CVE-2021-44228)도 본질은 JNDI를 통한 역직렬화 체인이다. 패턴은 같다.

### 4.2 Jackson Polymorphic Typing

Jackson은 다형성(polymorphism)을 처리하려고 `@JsonTypeInfo`로 클래스 이름을 JSON에 넣는 기능이 있다. `enableDefaultTyping()`을 켜면 모든 필드에 클래스명이 들어간다.

```json
{"@class": "com.example.Cat", "name": "Tom"}
```

문제는 공격자가 `@class`에 임의 클래스를 넣을 수 있다는 것이다. JNDI lookup이 가능한 클래스를 지정하면 RCE로 이어진다(CVE-2017-7525, CVE-2019-12384 등 수십 건).

**대응**:

- `enableDefaultTyping()` 절대 쓰지 마라.
- 다형성이 필요하면 `@JsonTypeInfo`로 명시하되, `PolymorphicTypeValidator`로 허용 클래스를 화이트리스트화하라.
- Jackson 2.10+의 `BasicPolymorphicTypeValidator`를 써라.
- `@JsonTypeInfo(use = Id.CLASS)` 대신 `Id.NAME`을 쓰고 `@JsonSubTypes`로 명시하라.

### 4.3 Protobuf Decoder DoS

Protobuf는 RCE는 거의 없지만 DoS는 흔하다.

#### Recursion Depth Attack

중첩된 메시지를 깊게 보내면 디코더가 재귀적으로 파싱하다 스택 오버플로우가 난다. Protobuf C++ 구현은 기본 100단계로 제한하지만, Java 구현은 한참 더 깊다.

대응: `CodedInputStream.setRecursionLimit()`로 제한하라.

#### Repeated Field Bomb

```protobuf
message X {
  repeated int32 numbers = 1;
}
```

`numbers` 필드를 수십만 개 넣은 메시지를 보내면 메모리가 폭증한다. `CodedInputStream.setSizeLimit()`로 메시지 전체 크기를 제한해야 한다(기본 64MB).

#### Hash Map Collision

map 필드의 키로 해시 충돌이 나는 문자열을 대량으로 보내면 O(n²)가 된다. 자바 HashMap이 트리화되면서 완화되긴 했지만, 다른 언어 구현은 여전히 취약하다.

### 4.4 JSON — Billion Laughs와 깊은 중첩

JSON 자체는 XML의 entity expansion 같은 공격은 없지만, 비슷한 패턴이 있다.

#### 깊은 중첩 (Stack Overflow)

```json
[[[[[[[[...]]]]]]]]
```

Jackson은 기본적으로 `StreamReadConstraints.maxNestingDepth = 1000`로 막는다. Jackson 2.15부터 기본값이 들어왔다. 그 이전 버전은 명시적으로 설정해야 한다.

#### 거대 문자열·숫자

```json
{"a": "AAAAAAAA...(100MB)"}
```

Jackson 2.15+는 `maxStringLength = 20MB`, `maxNumberLength = 1000`이 기본이다. 이전 버전은 메모리가 폭발한다.

#### Number Parsing DoS

긴 숫자 문자열을 `BigDecimal`로 파싱하면 O(n²)다. 100KB 숫자 문자열 하나로 서비스가 멈춘다. 외부 입력의 숫자에 `BigDecimal` 쓰는 코드는 위험하다.

### 4.5 Avro — 임의 코드 실행 패턴

Avro는 Java의 SpecificRecord 모드에서 위험한 패턴이 있다. SpecificDatumReader가 schema의 `java-class` 프로퍼티를 읽어서 임의 클래스를 로드한다.

```json
{
  "type": "record",
  "name": "Evil",
  "fields": [
    {"name": "x", "type": {"type": "string", "java-class": "악성클래스"}}
  ]
}
```

writer schema를 신뢰할 수 없는 곳에서 받아서 그대로 reader로 쓰면 클래스 로딩이 일어난다. 외부로부터 writer schema를 받지 마라. Schema Registry에서 받아오거나, 양쪽 모두 빌드 타임에 고정된 스키마만 써라.

또 Avro의 `GenericData.Record`로 풀어서 `Map<String, Object>` 형태로 다룰 때, 키에 `null`이나 예기치 못한 타입이 들어오면 NPE로 컨슈머 그룹 전체가 멈출 수 있다. 이건 보안이라기보다 가용성 이슈인데, 결과적으로는 DoS다.

---

## 5. 실무 트러블슈팅 케이스

### 5.1 Kafka Consumer 호환성 깨짐

**상황**: 결제 도메인 팀이 `payment.completed` 이벤트에 `merchantCategory` 필드를 추가했다. Avro 스키마였고 Schema Registry는 BACKWARD 모드였다. 새 필드에 default도 줬다. 등록 통과.

프로듀서를 먼저 배포했는데, 정산 팀 컨슈머가 갑자기 `Schema parse error`를 뱉으며 멈췄다. 컨슈머 그룹의 lag이 분당 수만 건씩 쌓이기 시작했다.

**원인**: 정산 팀은 Avro `SpecificRecord`(생성 코드) 기반이었다. 새 필드가 추가된 writer schema로 메시지가 왔는데, 그들이 빌드한 reader class에는 그 필드가 없었다. Avro resolution은 writer에만 있고 reader에 없는 필드는 그냥 무시한다 — 이론적으로는. 하지만 SpecificRecord는 reader schema를 자기 클래스에서 가져와서 fingerprint mismatch로 거부했다.

**해결**:

- 정산 팀이 새 .avsc를 받아서 코드 재생성·재배포.
- 이후 Schema Registry 모드를 `BACKWARD_TRANSITIVE`로 올리고, 컨슈머 빌드 파이프라인에서 매일 새벽 schema 폴링을 돌리도록 변경.
- 운영 룰: **프로듀서는 절대 컨슈머보다 먼저 배포하지 않는다.** BACKWARD 호환은 컨슈머가 새 스키마를 먼저 알고 있어야 한다는 뜻이다.

### 5.2 Redis 캐시 직렬화 실패

**상황**: Spring Boot 앱이 `RedisTemplate`으로 사용자 세션 객체를 캐싱했다. 직렬화는 `Jackson2JsonRedisSerializer`. 새 버전 배포 후 일부 인스턴스에서 `Could not read JSON: Unrecognized field "preferredLanguage"` 에러로 세션 조회 실패.

**원인**: 새 버전이 `User` 클래스에 `preferredLanguage` 필드를 추가했고, 새 인스턴스가 캐시에 저장. 그런데 롤링 배포 중이라 옛 인스턴스도 같은 캐시를 읽었다. 옛 인스턴스의 Jackson은 알 수 없는 필드를 만나자 그대로 죽었다.

**해결**:

- `objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)` 적용.
- 더 근본적으로: **캐시 키에 스키마 버전을 포함**시켰다. `user:v2:{id}` 형태로. 배포 시 새 버전은 새 키를 쓰니 옛 인스턴스와 안 부딪힌다. 옛 캐시는 TTL로 자연 소멸.

JSON으로 캐시할 때 알 수 없는 필드 무시는 기본값으로 깔고, 클래스가 크게 바뀌면 키 prefix를 바꾸는 게 안전하다.

### 5.3 gRPC 필드 번호 재사용 사고

**상황**: 마이크로서비스 A가 B에게 gRPC로 `UpdateProduct` 요청을 보낸다. 어느 날부터 B의 DB에 `price`가 엉뚱한 값으로 저장되는 현상.

```protobuf
// 6개월 전 v1
message UpdateProductRequest {
  int64 product_id = 1;
  int32 price = 2;
  int32 stock = 3;
}

// 누군가 price를 빼고 그 번호를 string으로 재사용 — reserved 안 박음
message UpdateProductRequest {
  int64 product_id = 1;
  string category = 2;  // 사고
  int32 stock = 3;
}
```

A는 옛 .proto로 빌드된 채로 돌고 있었다. A는 `price = 12000`을 varint로 인코딩해서 보냈다. B는 새 .proto로 컴파일됐고 필드 2번을 string으로 디코딩했다. wire type 미스매치라 보통은 에러가 나야 하는데, varint(0)와 length-delimited(2)의 차이를 일부 Protobuf 구현은 관대하게 무시한다. 결과적으로 `price`는 어디에도 안 들어가고 무시됐고, `price` 필드는 0으로 DB에 들어갔다.

**해결**:

- 즉시 옛 번호를 reserved로 박고 새 필드는 새 번호로 추가.
- 빌드 시 `buf breaking` 같은 도구로 호환성 검사를 자동화.
- gRPC API에서는 **필드 번호 변경/재사용은 단방향 화살표**다. 한번 쓴 번호는 영원히 reserved.

```protobuf
message UpdateProductRequest {
  reserved 2;
  reserved "price";  // 옛 이름까지 차단
  int64 product_id = 1;
  int32 stock = 3;
  string category = 4;
}
```

### 5.4 Avro Logical Type timestamp 정밀도 문제

**상황**: 주문 시각을 Avro로 직렬화해서 Kafka로 보내고, 컨슈머가 BigQuery에 적재. 어느 날 분석 팀이 "주문 시각이 1ms씩 어긋난다"고 제보.

**원인**: Avro의 timestamp logical type은 두 가지가 있다.

- `timestamp-millis`: long, 밀리초 단위.
- `timestamp-micros`: long, 마이크로초 단위.

프로듀서는 Java `Instant`에서 `toEpochMilli()`로 long을 만들어 `timestamp-millis`로 직렬화. 그런데 BigQuery 적재 단계의 컨슈머는 같은 long 값을 `timestamp-micros`로 해석. 1ms 차이가 아니라 1000배 차이다.

분석 팀은 "1ms 차이"라고 했지만, 실제로는 1970년에 가까운 어떤 시각으로 찍히고 있어야 했다. 데이터가 우연히 합리적인 범위에 떨어진 이유는 BigQuery가 마이크로초 단위 long을 받으면 1970년 근처로 가는데, 일부 레코드가 timestamp 변환 단계에서 보정됐기 때문이었다. 정확한 원인은 별개 이슈로 잡혔다.

**해결**:

- 스키마에 logical type을 명시적으로 박고, reader/writer가 같은 logical type을 쓰는지 매번 확인.
- Avro 1.9+는 `GenericData.setConversions()`로 logical type을 자동 변환. Java `Instant`로 그대로 받게 설정.
- 사내 표준: **모든 timestamp는 `timestamp-micros`로 통일.** 차후 정밀도 부족으로 다시 마이그레이션하는 비용이 더 크다.

또 하나 흔한 함정: Avro `decimal` logical type. `bytes`로 인코딩되는데 scale을 잘못 맞추면 `123.45`가 `12345`나 `1.2345`로 읽힌다. logical type은 Avro의 "보너스" 같은 기능이지만, reader와 writer가 같은 conversion을 안 쓰면 silent corruption이 난다.

---

## 6. 포맷 선택 기준

상황별로 어떤 걸 골라야 하는지 정리하자.

### REST API (외부 공개)

JSON. 의심의 여지가 없다. 인간 가독성, 디버깅 편의, 모든 언어 지원. 성능이 정말 문제면 그때 Protobuf + REST gateway 고려.

### 내부 마이크로서비스 RPC

gRPC + Protobuf. 빠르고, 코드 생성으로 타입 안전성 확보, 스트리밍 지원. 단, .proto 관리 체계와 호환성 검사 자동화는 필수.

### Kafka 이벤트 스트리밍

Avro + Schema Registry. 스키마 진화가 잦은 환경에서 가장 안전. JSON으로 시작했다가 트래픽이 커지면 거의 반드시 후회한다.

Protobuf + Schema Registry도 가능하지만, Confluent Schema Registry의 Avro 지원이 가장 성숙하다. 새로 시작한다면 Avro가 무난.

### Redis 캐시

JSON 또는 MessagePack. 캐시는 어차피 ephemeral하니 스키마 진화 부담이 적다. 바이트가 중요하면 MessagePack(map 인코딩), 디버깅이 중요하면 JSON.

Java Serializable은 **절대 쓰지 마라.** 캐시 클러스터에 RCE 페이로드가 한 번이라도 흘러들면 전체 노드가 함락된다.

### 빅데이터 (Hadoop, Spark, BigQuery)

Avro 또는 Parquet. Avro는 row-oriented(이벤트 스트리밍에 적합), Parquet은 columnar(분석 쿼리에 적합). 보통 Kafka에서 Avro로 받아서 Parquet으로 저장한다.

---

## 7. 운영 시 챙길 것

- **호환성 검사를 빌드 파이프라인에 박아라.** `buf breaking`(Protobuf), Avro tools `recursive`, Schema Registry의 `--compatibility` 검사. 사람이 PR 리뷰로 잡는 건 한계가 있다.
- **컨슈머가 먼저, 프로듀서가 나중에 배포.** BACKWARD 호환이 기본인 이상 이 순서는 절대 깨면 안 된다.
- **외부 입력을 절대 그대로 역직렬화하지 마라.** Jackson polymorphic typing, Java ObjectInputStream, Avro writer schema 외부 수신은 RCE 입구다.
- **메시지 크기·중첩 깊이 제한을 명시적으로 설정하라.** 라이브러리 기본값에 의존하지 말고 코드에서 박아라. DoS 입구를 막는 가장 싼 방법이다.
- **스키마는 코드처럼 버전 관리하라.** .proto, .avsc는 별도 레포 또는 monorepo의 schemas 디렉토리에서 관리. 빌드 산출물(.jar)로 배포해서 컨슈머가 의존성으로 가져가게 만든다.

직렬화 포맷은 한번 정하면 바꾸기 굉장히 어렵다. 트래픽 1만 RPS 넘어가는 시점에 JSON에서 Protobuf로 갈아탄 프로젝트는 거의 모두 6개월 이상 걸린다. 처음 설계할 때 트래픽·진화 빈도·디버깅 요구사항을 같이 보고 골라라.
