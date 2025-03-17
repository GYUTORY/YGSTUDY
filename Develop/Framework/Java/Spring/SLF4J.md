
# 📝 SLF4J (Simple Logging Facade for Java)

## 1. SLF4J란?

**SLF4J(Simple Logging Facade for Java)** 는 **로깅을 위한 추상화 인터페이스**입니다.  
Spring Boot에서는 기본적으로 SLF4J와 함께 **Logback**을 사용하여 로깅을 관리합니다.

✔️ **SLF4J의 역할**
- 다양한 로깅 프레임워크 (Logback, Log4j, java.util.logging) 를 추상화하여 통합된 방식으로 사용할 수 있음
- 성능이 뛰어나고 가볍게 동작
- Spring Boot에서는 기본적으로 **Logback**을 사용함

---

## 2. SLF4J 설정 방법

### 👉🏻 1) Gradle / Maven 의존성 추가

#### **Gradle (build.gradle.kts)**
```kotlin
dependencies {
    implementation("org.slf4j:slf4j-api:1.7.36") // SLF4J API 추가
    implementation("ch.qos.logback:logback-classic:1.2.11") // Logback 사용
}
```

#### **Maven (pom.xml)**
```xml
<dependencies>
    <dependency>
        <groupId>org.slf4j</groupId>
        <artifactId>slf4j-api</artifactId>
        <version>1.7.36</version>
    </dependency>
    <dependency>
        <groupId>ch.qos.logback</groupId>
        <artifactId>logback-classic</artifactId>
        <version>1.2.11</version>
    </dependency>
</dependencies>
```

✔️ `slf4j-api`를 추가하면 SLF4J를 사용할 수 있음  
✔️ `logback-classic`을 추가하면 SLF4J와 함께 Logback을 사용할 수 있음

---

## 3. SLF4J 사용 예제

### ✨ 1) @Slf4j 어노테이션 사용 (Lombok)

```java
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j // Logger 자동 생성
@Service
public class LoggingService {

    public void logExample() {
        log.info("INFO 로그입니다!");
        log.debug("DEBUG 로그입니다!");
        log.warn("WARN 로그입니다!");
        log.error("ERROR 로그입니다!");
    }
}
```

✔️ `@Slf4j` 어노테이션을 사용하면 **자동으로 `log` 객체가 생성됨**  
✔️ `log.info()`, `log.debug()`, `log.warn()`, `log.error()` 등을 사용할 수 있음

```java
LoggingService service = new LoggingService();
service.logExample();
```

출력 예제:
```
INFO : INFO 로그입니다!
DEBUG: DEBUG 로그입니다!
WARN : WARN 로그입니다!
ERROR: ERROR 로그입니다!
```

---

### ✨ 2) SLF4J 직접 사용

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class LoggingService {

    private static final Logger log = LoggerFactory.getLogger(LoggingService.class);

    public void logExample() {
        log.info("INFO 로그입니다!");
        log.debug("DEBUG 로그입니다!");
        log.warn("WARN 로그입니다!");
        log.error("ERROR 로그입니다!");
    }
}
```

✔️ `LoggerFactory.getLogger(클래스명.class)` 를 사용하여 Logger 객체 생성  
✔️ `log.info()`, `log.debug()`, `log.warn()`, `log.error()` 등을 사용할 수 있음

---

## 4. 로그 레벨 (Log Level)

SLF4J에서는 로그 레벨을 **중요도 순서대로** 사용할 수 있습니다.

| 로그 레벨  | 설명 |
|------------|--------------------------------|
| `TRACE`  | 가장 상세한 디버깅 정보 |
| `DEBUG`  | 개발 단계에서 유용한 디버깅 정보 |
| `INFO`   | 일반적인 실행 흐름 정보 (기본) |
| `WARN`   | 경고 메시지 (비정상적인 상황 가능성) |
| `ERROR`  | 심각한 오류 발생 |

✔️ 기본적으로 `INFO` 이상의 로그만 출력됨  
✔️ `application.properties`에서 로그 레벨을 조정할 수 있음

```properties
# application.properties
logging.level.root=DEBUG
logging.level.com.example=TRACE
```

✔️ `logging.level.root=DEBUG` → 전체 로그를 `DEBUG` 레벨로 설정  
✔️ `logging.level.com.example=TRACE` → 특정 패키지의 로그 레벨을 `TRACE`로 설정

---

## 5. 로그 파일 저장

기본적으로 로그는 콘솔에 출력됩니다. 하지만 **파일로 저장할 수도 있습니다.**

### **logback.xml 설정** (Logback 사용 시)

```xml
<configuration>
    <appender name="FILE" class="ch.qos.logback.core.FileAppender">
        <file>logs/app.log</file>
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss} [%level] %msg%n</pattern>
        </encoder>
    </appender>

    <root level="info">
        <appender-ref ref="FILE" />
    </root>
</configuration>
```

✔️ 로그가 `logs/app.log` 파일에 저장됨  
✔️ `pattern`을 설정하여 로그 포맷을 조정할 수 있음