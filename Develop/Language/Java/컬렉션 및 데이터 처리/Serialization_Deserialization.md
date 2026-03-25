---
title: Java Serialization & Deserialization
tags: [language, java, 컬렉션-및-데이터-처리, serialization, deserialization]
updated: 2026-03-25
---

# Java 직렬화(Serialization) / 역직렬화(Deserialization)

## 직렬화란

Java 객체를 바이트 스트림으로 변환하는 것이다. 파일 저장, 네트워크 전송, 캐시 저장 등에 쓴다. 역직렬화는 바이트 스트림을 다시 객체로 복원하는 과정이다.

객체를 직렬화하려면 `java.io.Serializable` 인터페이스를 구현해야 한다. 이 인터페이스는 메서드가 없는 마커 인터페이스다.

## 기본 사용법

### 직렬화

```java
import java.io.*;

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

    @Override
    public String toString() {
        return "Person{name='" + name + "', age=" + age + ", password='" + password + "'}";
    }
}

public class SerializationExample {
    public static void main(String[] args) {
        Person person = new Person("홍길동", 30, "secret123");

        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("person.ser"))) {
            oos.writeObject(person);
            System.out.println("직렬화 완료: " + person);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 역직렬화

```java
public class DeserializationExample {
    public static void main(String[] args) {
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream("person.ser"))) {
            Person person = (Person) ois.readObject();
            System.out.println("역직렬화 완료: " + person);
            // password는 transient이므로 null로 복원된다
        } catch (IOException | ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
```

출력:

```
직렬화 완료: Person{name='홍길동', age=30, password='secret123'}
역직렬화 완료: Person{name='홍길동', age=30, password='null'}
```

`transient` 필드는 직렬화 대상에서 빠진다. 비밀번호, DB 커넥션 같은 민감하거나 직렬화 불가능한 필드에 붙인다.

## serialVersionUID와 호환성 문제

`serialVersionUID`를 명시하지 않으면 JVM이 클래스 구조를 기반으로 자동 생성한다. 문제는 클래스를 조금만 바꿔도 이 값이 달라져서 기존에 직렬화한 데이터를 역직렬화할 때 `InvalidClassException`이 터진다.

```java
// v1: serialVersionUID 미지정
class User implements Serializable {
    private String name;
}

// v2: 필드 하나 추가 → 자동 생성 UID가 달라짐
class User implements Serializable {
    private String name;
    private String email; // 추가
}
```

v1에서 직렬화한 데이터를 v2로 역직렬화하면 `InvalidClassException`이 발생한다.

### 해결 방법

`serialVersionUID`를 명시적으로 선언한다.

```java
class User implements Serializable {
    private static final long serialVersionUID = 1L;

    private String name;
    private String email; // 나중에 추가해도 UID가 같으므로 역직렬화 가능
}
```

필드를 추가하는 것은 괜찮다. 역직렬화 시 해당 필드는 기본값(null, 0 등)으로 채워진다. 하지만 **기존 필드의 타입을 바꾸면** UID가 같아도 역직렬화에 실패한다. `int age`를 `String age`로 바꾸면 깨진다.

실무에서 직렬화된 객체를 장기 저장하거나 캐시에 쓸 때 클래스 변경이 잦으면 골치가 아프다. 이런 경우 Java 직렬화 대신 JSON이나 Protobuf를 쓰는 게 낫다.

## writeObject / readObject 커스텀 직렬화

기본 직렬화 동작을 바꿔야 할 때 `writeObject`와 `readObject` 메서드를 직접 정의한다. 대표적인 경우:

- `transient` 필드를 암호화해서 저장하고 싶을 때
- 직렬화 시점에 유효성 검증이 필요할 때
- 직렬화 포맷을 최적화하고 싶을 때

```java
class Account implements Serializable {
    private static final long serialVersionUID = 1L;

    private String username;
    private transient String password;

    public Account(String username, String password) {
        this.username = username;
        this.password = password;
    }

    // 커스텀 직렬화: password를 인코딩해서 저장
    private void writeObject(ObjectOutputStream oos) throws IOException {
        oos.defaultWriteObject(); // transient 아닌 필드는 기본 직렬화
        // 실제로는 암호화 라이브러리를 쓴다. 여기서는 단순 인코딩 예시
        String encoded = Base64.getEncoder().encodeToString(password.getBytes());
        oos.writeObject(encoded);
    }

    // 커스텀 역직렬화: 디코딩해서 복원
    private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
        ois.defaultReadObject();
        String encoded = (String) ois.readObject();
        this.password = new String(Base64.getDecoder().decode(encoded));
    }

    @Override
    public String toString() {
        return "Account{username='" + username + "', password='" + password + "'}";
    }
}
```

주의할 점:

- `writeObject`와 `readObject`는 반드시 `private`으로 선언한다. JVM이 리플렉션으로 호출하기 때문에 접근 제어자가 `private`이 아니면 무시된다.
- `defaultWriteObject()`와 `defaultReadObject()`를 먼저 호출해서 기본 필드를 처리한 다음, 추가 데이터를 쓰거나 읽는다.
- 쓰는 순서와 읽는 순서가 반드시 일치해야 한다.

## 역직렬화 보안 이슈

**신뢰할 수 없는 데이터를 역직렬화하면 안 된다.** 이건 Java 보안 취약점의 단골 원인이다.

### 왜 위험한가

역직렬화 과정에서 객체가 생성되고, 해당 클래스의 `readObject` 메서드가 실행된다. 공격자가 조작한 바이트 스트림을 넣으면 의도하지 않은 코드가 실행될 수 있다. Apache Commons Collections의 `InvokerTransformer` 같은 가젯 체인(gadget chain)을 이용한 RCE(Remote Code Execution) 공격이 대표적이다.

2015년에 터진 Apache Commons Collections 역직렬화 취약점으로 WebLogic, JBoss 등 주요 WAS가 원격 코드 실행 공격에 노출됐다.

### 방어 방법

**1. ObjectInputFilter 사용 (Java 9+)**

역직렬화할 클래스를 화이트리스트로 제한한다.

```java
ObjectInputStream ois = new ObjectInputStream(new FileInputStream("data.ser"));
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "com.myapp.model.*;!*"  // com.myapp.model 패키지만 허용, 나머지 거부
);
ois.setObjectInputFilter(filter);
Object obj = ois.readObject();
```

**2. 외부 입력에 Java 직렬화를 쓰지 않는다**

네트워크로 받은 데이터, 사용자가 업로드한 파일 등 외부 소스의 데이터를 `ObjectInputStream`으로 읽으면 안 된다. JSON, Protobuf 같은 포맷을 쓴다.

**3. 직렬화가 필요 없는 클래스는 명시적으로 차단**

```java
class InternalConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    private void readObject(ObjectInputStream ois) throws IOException {
        throw new InvalidObjectException("역직렬화 허용하지 않음");
    }
}
```

## Java 직렬화 vs 현대적 대안

실무에서 Java 기본 직렬화(`Serializable`)를 쓰는 경우는 점점 줄어들고 있다. 주요 대안과 비교하면 다음과 같다.

### JSON (Jackson, Gson)

```java
// Jackson 예시
ObjectMapper mapper = new ObjectMapper();

// 직렬화
String json = mapper.writeValueAsString(person);
// {"name":"홍길동","age":30}

// 역직렬화
Person restored = mapper.readValue(json, Person.class);
```

- 사람이 읽을 수 있다. 디버깅이 쉽다.
- 언어에 종속되지 않는다. 다른 언어로 만든 서비스와 통신할 때 문제가 없다.
- `Serializable` 구현이 필요 없다.
- 바이너리 대비 데이터 크기가 크고 파싱 속도가 느리다.
- REST API, 설정 파일, 로그 저장 등 대부분의 상황에서 적합하다.

### Protocol Buffers (Protobuf)

```protobuf
// person.proto
syntax = "proto3";

message Person {
    string name = 1;
    int32 age = 2;
}
```

```java
// 직렬화
PersonProto.Person person = PersonProto.Person.newBuilder()
    .setName("홍길동")
    .setAge(30)
    .build();
byte[] bytes = person.toByteArray();

// 역직렬화
PersonProto.Person restored = PersonProto.Person.parseFrom(bytes);
```

- 바이너리 포맷이라 크기가 작고 빠르다.
- `.proto` 파일로 스키마를 명확하게 정의한다. 필드 번호 기반이라 필드 추가/삭제 시 하위 호환성이 보장된다.
- gRPC에서 기본 직렬화 포맷으로 쓴다.
- 사람이 읽을 수 없고, 빌드 단계에서 코드 생성이 필요하다.

### 어떤 걸 쓸지

| 상황 | 권장 포맷 |
|------|-----------|
| REST API 통신 | JSON |
| 마이크로서비스 간 내부 통신 (gRPC) | Protobuf |
| 설정 파일, 로그 | JSON |
| JVM 내부에서만 쓰는 캐시 (Redis, 세션) | Java 직렬화 or JSON |
| 외부로부터 받는 데이터 | JSON 또는 Protobuf (Java 직렬화 금지) |

Java 직렬화는 JVM 내부에서만 쓰이고, 클래스 변경에 취약하고, 보안 문제가 있다. 새로 만드는 시스템에서는 JSON이나 Protobuf를 기본으로 쓰고, Java 직렬화는 레거시 호환이 필요한 경우에만 쓰는 게 맞다.
