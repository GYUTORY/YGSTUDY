
# ✨ Lombok 개념과 예제

## 1. Lombok이란?

**Lombok**은 Java 코드에서 **반복적인 보일러플레이트 코드(Boilerplate Code)를 줄여주는 라이브러리**입니다.  
`@Getter`, `@Setter`, `@ToString`, `@EqualsAndHashCode`, `@NoArgsConstructor`, `@AllArgsConstructor` 등의 어노테이션을 제공하여 개발자의 생산성을 높입니다.

---

## 2. Lombok 설정 방법

### 👉🏻 1) Lombok 의존성 추가 (Gradle / Maven)

#### **Gradle (build.gradle.kts)**
```kotlin
dependencies {
    implementation("org.projectlombok:lombok:1.18.30")
    annotationProcessor("org.projectlombok:lombok:1.18.30")
}
```

#### **Maven (pom.xml)**
```xml
<dependencies>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <version>1.18.30</version>
        <scope>provided</scope>
    </dependency>
</dependencies>
```

✔️ **설치 후 IDE에서 Lombok Plugin을 활성화해야 합니다.**
- **IntelliJ IDEA**: `Preferences > Plugins > Lombok` 검색 후 설치
- **Eclipse**: `Help > Eclipse Marketplace > Lombok` 검색 후 설치

---

## 3. Lombok 주요 어노테이션

### ✨ 1) @Getter / @Setter

```java
import lombok.Getter;
import lombok.Setter;

@Getter // 모든 필드에 대한 Getter 메서드 자동 생성
@Setter // 모든 필드에 대한 Setter 메서드 자동 생성
public class User {
    private String name;
    private int age;
}
```

✔️ `@Getter`와 `@Setter`를 사용하면, **자동으로 Getter / Setter 메서드를 생성**합니다.

```java
User user = new User();
user.setName("홍길동");
System.out.println(user.getName()); // 홍길동
```

---

### ✨ 2) @ToString

```java
import lombok.ToString;

@ToString // toString() 메서드 자동 생성
public class User {
    private String name;
    private int age;
}
```

```java
User user = new User("홍길동", 30);
System.out.println(user.toString());
// User(name=홍길동, age=30)
```

✔️ `@ToString`은 객체의 내용을 문자열로 출력할 때 유용합니다.

---

### ✨ 3) @NoArgsConstructor / @AllArgsConstructor

```java
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;

@NoArgsConstructor  // 기본 생성자 생성
@AllArgsConstructor // 모든 필드를 포함하는 생성자 생성
public class User {
    private String name;
    private int age;
}
```

```java
User user1 = new User(); // 기본 생성자 사용
User user2 = new User("홍길동", 30); // 모든 필드를 받는 생성자 사용
```

✔️ `@NoArgsConstructor`는 매개변수가 없는 생성자를 생성합니다.  
✔️ `@AllArgsConstructor`는 모든 필드를 매개변수로 받는 생성자를 생성합니다.

---

### ✨ 4) @EqualsAndHashCode

```java
import lombok.EqualsAndHashCode;

@EqualsAndHashCode // equals()와 hashCode() 자동 생성
public class User {
    private String name;
    private int age;
}
```

✔️ `@EqualsAndHashCode`는 객체의 동등성 비교를 위한 `equals()`와 `hashCode()` 메서드를 자동 생성합니다.

---

### ✨ 5) @Data (포괄적인 Lombok 어노테이션)

```java
import lombok.Data;

@Data // @Getter, @Setter, @ToString, @EqualsAndHashCode, @RequiredArgsConstructor 포함
public class User {
    private String name;
    private int age;
}
```

✔️ `@Data`는 **가장 많이 사용되는 Lombok 어노테이션**으로,  
`@Getter`, `@Setter`, `@ToString`, `@EqualsAndHashCode`, `@RequiredArgsConstructor` 를 포함합니다.

---

## 4. Lombok과 Spring 사용 예제

### 1️⃣ Lombok을 활용한 Service 클래스

```java
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor // final 필드만 포함한 생성자 자동 생성 (DI에 유용)
public class UserService {
    
    private final UserRepository userRepository; // 생성자를 통한 의존성 주입

    public User getUserById(Long id) {
        return userRepository.findById(id).orElse(null);
    }
}
```

✔️ `@RequiredArgsConstructor`는 `final` 필드를 매개변수로 받는 생성자를 자동으로 생성합니다.  
✔️ Spring에서 **의존성 주입(DI)** 시 매우 유용하게 사용됩니다.
