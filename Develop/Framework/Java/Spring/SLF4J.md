---
title: SLF4J (Simple Logging Facade for Java) 완벽 가이드
tags: [framework, java, spring, slf4j, logging, logback]
updated: 2024-12-19
---

# SLF4J (Simple Logging Facade for Java) 완벽 가이드

## 배경

### SLF4J란?
SLF4J(Simple Logging Facade for Java)는 로깅을 위한 추상화 인터페이스입니다. Spring Boot에서는 기본적으로 SLF4J와 함께 Logback을 사용하여 로깅을 관리합니다.

### SLF4J의 역할
- 다양한 로깅 프레임워크(Logback, Log4j, java.util.logging)를 추상화하여 통합된 방식으로 사용
- 성능이 뛰어나고 가볍게 동작
- Spring Boot에서는 기본적으로 Logback을 사용

### 기본 개념
- **Facade Pattern**: 복잡한 로깅 시스템을 단순한 인터페이스로 제공
- **Logging Framework**: 실제 로그를 처리하는 구현체
- **Log Level**: 로그의 중요도를 나타내는 레벨
- **Appender**: 로그 출력 대상을 정의

## 핵심

### 1. SLF4J 설정 방법

#### Gradle 의존성 추가
```kotlin
dependencies {
    implementation("org.slf4j:slf4j-api:1.7.36") // SLF4J API 추가
    implementation("ch.qos.logback:logback-classic:1.2.11") // Logback 사용
}
```

#### Maven 의존성 추가
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

### 2. SLF4J 사용 예제

#### @Slf4j 어노테이션 사용 (Lombok)
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

#### SLF4J 직접 사용
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

### 3. 로그 레벨 (Log Level)

SLF4J에서는 로그 레벨을 중요도 순서대로 사용할 수 있습니다.

| 로그 레벨 | 설명 |
|-----------|------|
| **TRACE** | 가장 상세한 디버깅 정보 |
| **DEBUG** | 개발 단계에서 유용한 디버깅 정보 |
| **INFO** | 일반적인 실행 흐름 정보 (기본) |
| **WARN** | 경고 메시지 (비정상적인 상황 가능성) |
| **ERROR** | 심각한 오류 발생 |

#### application.properties에서 로그 레벨 설정
```properties
# 전체 로그 레벨 설정
logging.level.root=DEBUG

# 특정 패키지의 로그 레벨 설정
logging.level.com.example=TRACE

# 특정 클래스의 로그 레벨 설정
logging.level.com.example.service.UserService=DEBUG
```

## 예시

### 1. 실제 사용 사례

#### 서비스 클래스에서 로깅
```java
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class UserService {

    public User createUser(UserDto userDto) {
        log.info("사용자 생성 시작: {}", userDto.getEmail());
        
        try {
            // 사용자 생성 로직
            User user = userRepository.save(userDto.toEntity());
            log.info("사용자 생성 완료: {}", user.getId());
            return user;
        } catch (Exception e) {
            log.error("사용자 생성 실패: {}", userDto.getEmail(), e);
            throw new RuntimeException("사용자 생성에 실패했습니다.", e);
        }
    }

    public User findUserById(Long id) {
        log.debug("사용자 조회: id={}", id);
        
        return userRepository.findById(id)
            .orElseThrow(() -> {
                log.warn("사용자를 찾을 수 없음: id={}", id);
                return new UserNotFoundException("사용자를 찾을 수 없습니다.");
            });
    }
}
```

#### 컨트롤러에서 로깅
```java
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping
    public ResponseEntity<User> createUser(@RequestBody UserDto userDto) {
        log.info("사용자 생성 요청: {}", userDto.getEmail());
        
        User user = userService.createUser(userDto);
        
        log.info("사용자 생성 응답: {}", user.getId());
        return ResponseEntity.ok(user);
    }

    @GetMapping("/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        log.debug("사용자 조회 요청: id={}", id);
        
        User user = userService.findUserById(id);
        
        log.debug("사용자 조회 응답: id={}", id);
        return ResponseEntity.ok(user);
    }
}
```

### 2. 고급 로깅 패턴

#### 조건부 로깅
```java
@Slf4j
public class PerformanceService {

    public void processData(List<String> data) {
        if (log.isDebugEnabled()) {
            log.debug("데이터 처리 시작: {} 개 항목", data.size());
        }

        // 데이터 처리 로직
        for (String item : data) {
            if (log.isTraceEnabled()) {
                log.trace("항목 처리: {}", item);
            }
            // 처리 로직
        }

        log.info("데이터 처리 완료: {} 개 항목", data.size());
    }
}
```

#### MDC (Mapped Diagnostic Context) 사용
```java
import org.slf4j.MDC;

@Slf4j
public class TransactionService {

    public void processTransaction(String transactionId, BigDecimal amount) {
        // MDC에 트랜잭션 ID 설정
        MDC.put("transactionId", transactionId);
        
        try {
            log.info("트랜잭션 처리 시작: {}", amount);
            
            // 트랜잭션 처리 로직
            if (amount.compareTo(BigDecimal.ZERO) < 0) {
                log.warn("음수 금액 감지: {}", amount);
            }
            
            log.info("트랜잭션 처리 완료");
        } finally {
            // MDC 정리
            MDC.clear();
        }
    }
}
```

## 운영 팁

### 1. 로그 파일 저장

#### logback.xml 설정 (Logback 사용 시)
```xml
<configuration>
    <!-- 콘솔 출력 -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <!-- 파일 출력 -->
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>logs/app.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>logs/app.%d{yyyy-MM-dd}.log</fileNamePattern>
            <maxHistory>30</maxHistory>
        </rollingPolicy>
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <!-- 루트 로거 설정 -->
    <root level="info">
        <appender-ref ref="CONSOLE" />
        <appender-ref ref="FILE" />
    </root>
</configuration>
```

### 2. 로그 포맷 설정

#### 로그 패턴 설명
- `%d{yyyy-MM-dd HH:mm:ss}`: 날짜와 시간
- `[%thread]`: 스레드 이름
- `%-5level`: 로그 레벨 (5자리 고정)
- `%logger{36}`: 로거 이름 (최대 36자)
- `%msg`: 로그 메시지
- `%n`: 줄바꿈

### 3. 성능 최적화

#### 로그 레벨별 성능 고려사항
```java
@Slf4j
public class PerformanceOptimizedService {

    public void processWithOptimizedLogging(List<String> data) {
        // INFO 레벨은 항상 실행
        log.info("데이터 처리 시작: {} 개 항목", data.size());

        // DEBUG 레벨은 조건부 실행
        if (log.isDebugEnabled()) {
            log.debug("상세 처리 정보: {}", data);
        }

        // TRACE 레벨은 가장 상세한 정보
        if (log.isTraceEnabled()) {
            for (String item : data) {
                log.trace("개별 항목 처리: {}", item);
            }
        }

        log.info("데이터 처리 완료");
    }
}
```

## 참고

### SLF4J vs 다른 로깅 프레임워크

| 특징 | SLF4J | Log4j | java.util.logging |
|------|-------|-------|-------------------|
| **추상화** | ✅ | ❌ | ❌ |
| **성능** | 높음 | 보통 | 낮음 |
| **Spring Boot 통합** | 기본 | 별도 설정 | 별도 설정 |
| **설정 복잡도** | 낮음 | 보통 | 높음 |

### 로그 레벨 선택 가이드

| 환경 | 권장 로그 레벨 | 이유 |
|------|---------------|------|
| **개발** | DEBUG | 상세한 디버깅 정보 필요 |
| **테스트** | INFO | 기본적인 실행 흐름 확인 |
| **운영** | WARN | 성능과 보안을 위한 최소 로그 |
| **디버깅** | TRACE | 가장 상세한 정보 필요 |

### 결론
SLF4J는 Java 애플리케이션에서 로깅을 위한 표준적인 솔루션으로, Spring Boot와 함께 사용하면 효과적인 로그 관리가 가능합니다. 적절한 로그 레벨 설정과 구조화된 로그 메시지를 통해 애플리케이션의 모니터링과 디버깅을 효율적으로 수행할 수 있습니다.
