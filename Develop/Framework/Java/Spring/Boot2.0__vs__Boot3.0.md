---
title: Spring Boot 2.0 vs Spring Boot 3.0 완벽 비교 가이드
tags: [framework, java, spring, spring-boot, migration, jakarta-ee, graalvm]
updated: 2024-12-19
---

# Spring Boot 2.0 vs Spring Boot 3.0 완벽 비교 가이드

## 배경

### Spring Boot 버전 개요
Spring Boot는 Java 기반의 웹 애플리케이션 개발을 위한 프레임워크로, Spring Boot 2.0은 2018년에, Spring Boot 3.0은 2022년 말에 릴리스되었습니다. 두 버전은 각각 다른 시대의 요구사항과 기술 트렌드를 반영하여 설계되었습니다.

### 버전 선택의 중요성
- **기술 스택 호환성**: Java 버전, 데이터베이스, 미들웨어와의 호환성
- **성능 요구사항**: 애플리케이션의 성능과 확장성 요구사항
- **개발 생산성**: 개발자 경험과 생산성 향상
- **유지보수성**: 장기적인 유지보수와 업그레이드 계획

### 기본 개념
- **Spring Framework**: Spring Boot의 기반이 되는 핵심 프레임워크
- **Java EE/Jakarta EE**: 엔터프라이즈 Java 표준
- **GraalVM**: 네이티브 이미지 생성을 위한 JVM
- **Micrometer**: 애플리케이션 메트릭 수집 라이브러리

## 핵심

### 1. Spring Boot 2.0 특징

#### 리액티브 프로그래밍 지원
Spring WebFlux를 통해 리액티브 애플리케이션 개발이 가능해졌습니다.

```java
@RestController
public class ReactiveController {
    
    @GetMapping("/reactive")
    public Mono<String> reactiveEndpoint() {
        return Mono.just("Hello, Reactive World!");
    }
    
    @GetMapping("/users")
    public Flux<User> getUsers() {
        return userRepository.findAll();
    }
}
```

#### Actuator 개선
애플리케이션의 상태와 메트릭을 모니터링하는 Actuator가 강화되었습니다.

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"
  endpoint:
    health:
      show-details: always
```

#### Kotlin 지원 강화
Kotlin 언어 지원이 추가되어 현대적인 애플리케이션 개발이 가능해졌습니다.

```kotlin
@RestController
class UserController(private val userService: UserService) {
    
    @GetMapping("/users/{id}")
    fun getUser(@PathVariable id: Long): User {
        return userService.findById(id)
    }
}
```

### 2. Spring Boot 3.0 특징

#### Jakarta EE 전환
Java EE에서 Jakarta EE로 전환되어 패키지명이 변경되었습니다.

```java
// Spring Boot 2.0 (Java EE)
import javax.persistence.Entity;
import javax.persistence.Id;

// Spring Boot 3.0 (Jakarta EE)
import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class User {
    @Id
    private Long id;
    private String name;
}
```

#### Java 17 이상 필수
Java 17 이상을 요구하며, 최신 언어 기능을 활용할 수 있습니다.

```java
// Record 클래스 사용
public record UserDTO(String name, int age) {}

// Pattern Matching 사용
public String processUser(Object obj) {
    return switch (obj) {
        case User user -> "User: " + user.getName();
        case String str -> "String: " + str;
        default -> "Unknown";
    };
}
```

#### Native 지원
GraalVM을 사용한 네이티브 이미지 빌드를 공식 지원합니다.

```bash
# 네이티브 이미지 빌드
./mvnw native:compile

# 또는 Gradle
./gradlew nativeCompile
```

#### 관찰 가능성(Observability) 개선
Micrometer와 통합하여 메트릭, 추적 및 로그의 통합 모니터링이 용이합니다.

```java
@RestController
public class MetricsController {
    
    private final MeterRegistry meterRegistry;
    
    public MetricsController(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }
    
    @GetMapping("/api/data")
    public String getData() {
        Timer.Sample sample = Timer.start(meterRegistry);
        try {
            // 비즈니스 로직
            return "Data";
        } finally {
            sample.stop(Timer.builder("api.request.duration")
                .tag("endpoint", "getData")
                .register(meterRegistry));
        }
    }
}
```

### 3. 주요 차이점 비교

| 항목 | Spring Boot 2.0 | Spring Boot 3.0 |
|------|-----------------|-----------------|
| **기반 플랫폼** | Java 8 이상, Java EE | Java 17 이상, Jakarta EE |
| **Spring Framework** | 5.x | 6.x |
| **리액티브 지원** | Spring WebFlux | Spring WebFlux (개선) |
| **네이티브 지원** | 제한적 (실험적) | 공식 지원 (GraalVM) |
| **관찰 가능성** | Actuator 기반 | Micrometer 통합 |
| **패키지** | javax.* | jakarta.* |
| **성능** | 표준 JVM | 네이티브 이미지 지원 |

## 예시

### 1. 실제 마이그레이션 사례

#### 의존성 업데이트
```xml
<!-- Spring Boot 2.0 -->
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version>
</parent>

<!-- Spring Boot 3.0 -->
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
</parent>
```

#### 패키지 변경 예시
```java
// Spring Boot 2.0
import javax.persistence.*;
import javax.validation.constraints.*;
import javax.servlet.http.HttpServletRequest;

// Spring Boot 3.0
import jakarta.persistence.*;
import jakarta.validation.constraints.*;
import jakarta.servlet.http.HttpServletRequest;
```

#### 네이티브 이미지 설정
```xml
<!-- Spring Boot 3.0 네이티브 지원 -->
<plugin>
    <groupId>org.graalvm.buildtools</groupId>
    <artifactId>native-maven-plugin</artifactId>
    <configuration>
        <classesDirectory>${project.build.outputDirectory}</classesDirectory>
        <metadataRepository>
            <enabled>true</enabled>
        </metadataRepository>
    </configuration>
</plugin>
```

### 2. 성능 비교

#### 시작 시간 비교
```bash
# Spring Boot 2.0 (JVM)
time java -jar app.jar
# 실제 시간: 2.5초

# Spring Boot 3.0 (네이티브)
time ./app
# 실제 시간: 0.05초
```

#### 메모리 사용량 비교
```bash
# Spring Boot 2.0 (JVM)
ps aux | grep java
# 메모리: ~150MB

# Spring Boot 3.0 (네이티브)
ps aux | grep app
# 메모리: ~50MB
```

## 운영 팁

### 1. 마이그레이션 전략

#### 단계적 마이그레이션
```bash
# 1단계: Java 17 업그레이드
# 2단계: Spring Boot 2.7로 업그레이드
# 3단계: Jakarta EE 패키지 변경
# 4단계: Spring Boot 3.0으로 업그레이드
# 5단계: 네이티브 이미지 테스트
```

#### 호환성 검사
```bash
# Spring Boot 3.0 마이그레이션 가이드 실행
./mvnw spring-boot:run -Dspring-boot.run.arguments="--debug"

# 의존성 호환성 검사
./mvnw dependency:tree | grep -E "(javax|jakarta)"
```

### 2. 성능 최적화

#### 네이티브 이미지 최적화
```java
// 네이티브 이미지에서 사용할 리플렉션 설정
@NativeHint(
    types = @TypeHint(types = User.class),
    resources = @ResourceHint(patterns = "application.yml")
)
public class NativeConfig {
}
```

#### 메트릭 수집 최적화
```yaml
# application.yml
management:
  metrics:
    export:
      prometheus:
        enabled: true
    tags:
      application: ${spring.application.name}
      version: ${app.version}
```

### 3. 문제 해결

#### 일반적인 마이그레이션 이슈
```java
// 문제: javax 패키지 사용
// 해결: jakarta 패키지로 변경
import jakarta.persistence.Entity;
import jakarta.validation.constraints.NotNull;

// 문제: Java 8 특정 API 사용
// 해결: Java 17 호환 코드로 변경
List<String> list = List.of("item1", "item2"); // Java 9+
```

## 참고

### 버전별 권장 사용 사례

| 사용 사례 | 권장 버전 | 이유 |
|-----------|-----------|------|
| **레거시 시스템** | Spring Boot 2.0 | 안정성과 호환성 |
| **새 프로젝트** | Spring Boot 3.0 | 최신 기능과 성능 |
| **마이크로서비스** | Spring Boot 3.0 | 네이티브 이미지 지원 |
| **대용량 트래픽** | Spring Boot 3.0 | 성능 최적화 |

### 마이그레이션 체크리스트

#### 사전 준비
- [ ] Java 17 이상 설치
- [ ] 의존성 호환성 검사
- [ ] 테스트 코드 준비
- [ ] 백업 및 롤백 계획

#### 마이그레이션 과정
- [ ] 패키지명 변경 (javax → jakarta)
- [ ] API 변경사항 적용
- [ ] 설정 파일 업데이트
- [ ] 테스트 실행 및 검증

#### 사후 검증
- [ ] 성능 테스트
- [ ] 기능 테스트
- [ ] 모니터링 설정
- [ ] 문서 업데이트

### 결론
Spring Boot 2.0은 안정성과 호환성을 중시하는 버전이며, Spring Boot 3.0은 최신 Java 기능과 네이티브 지원을 통해 성능과 개발 생산성을 크게 향상시킨 버전입니다. 새로운 프로젝트나 성능이 중요한 시스템에서는 Spring Boot 3.0을 권장하며, 기존 시스템의 마이그레이션 시에는 단계적 접근을 통해 안전하게 업그레이드하는 것이 중요합니다.

