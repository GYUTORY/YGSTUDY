---
title: Project Lombok Java
tags: [framework, java, spring, lombok]
updated: 2025-12-13
---
# Project Lombok: Java 개발자의 필수 도구

## 배경
1. [Lombok 소개](#1-lombok-소개)
2. [환경 설정](#2-환경-설정)
3. [핵심 어노테이션](#3-핵심-어노테이션)
4. [실전 활용](#4-실전-활용)
5. [모범 사례와 주의사항](#5-모범-사례와-주의사항)

- [Project Lombok 공식 문서](https://projectlombok.org/features/all)
- [Spring Boot with Lombok](https://spring.io/blog/2018/12/12/spring-boot-with-lombok)
- [Lombok Best Practices](https://www.baeldung.com/lombok-ide)










## 1. Lombok 소개

### 1.1 Lombok이란?

Project Lombok은 Java 생태계에서 **반복적인 보일러플레이트 코드를 획기적으로 줄여주는 라이브러리**입니다. 
개발자의 생산성을 극대화하고 코드의 가독성을 높이는 것이 주요 목적입니다.

### 1.2 주요 특징

- ✨ **코드 간소화**: getter/setter, constructor 등 자동 생성
- 🛡️ **안정성**: 컴파일 시점에 코드 생성으로 런타임 오버헤드 없음
- 🔄 **유지보수성**: 보일러플레이트 코드 감소로 유지보수 용이
- ⚡ **생산성**: 반복 작업 최소화로 개발 시간 단축

## 2. 환경 설정

### 2.1 의존성 추가

#### 📦 Gradle (build.gradle.kts)
```kotlin
dependencies {
    implementation("org.projectlombok:lombok:1.18.30")
    annotationProcessor("org.projectlombok:lombok:1.18.30")
    
    // Spring Boot 사용 시
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
}
```

#### 📦 Maven (pom.xml)
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

### 2.2 IDE 설정

#### IntelliJ IDEA
1. `Settings/Preferences` → `Plugins` → `Marketplace`
2. "Lombok" 검색 및 설치
3. `Settings/Preferences` → `Build, Execution, Deployment` → `Compiler` → `Annotation Processors`
4. "Enable annotation processing" 활성화

#### Eclipse
1. lombok.jar 파일 다운로드
2. jar 파일 실행 후 IDE 위치 지정
3. IDE 재시작

## 3. 핵심 어노테이션

### 3.1 기본 어노테이션

#### @Getter / @Setter
```java
@Getter @Setter
public class User {
    private String username;
    private String email;
    
    @Getter(AccessLevel.PROTECTED) // 접근 제어 설정 가능
    private String password;
}
```

#### @ToString
```java
@ToString(exclude = "password") // 특정 필드 제외 가능
public class User {
    private String username;
    private String email;
    private String password;
}
```

### 3.2 생성자 관련 어노테이션

#### @NoArgsConstructor / @AllArgsConstructor / @RequiredArgsConstructor
```java
@NoArgsConstructor(access = AccessLevel.PROTECTED) // 접근 제어 설정
@AllArgsConstructor
public class User {
    private final String username;  // final 필드는 @RequiredArgsConstructor에 포함
    private String email;
    private String password;
}
```

### 3.3 유틸리티 어노테이션

#### @Data
```java
@Data  // @Getter, @Setter, @ToString, @EqualsAndHashCode, @RequiredArgsConstructor 통합
public class User {
    private final String username;
    private String email;
    private String password;
}
```

## 4. 실전 활용

### 4.1 Spring Boot에서의 활용

#### JPA Entity 클래스
```java
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@EntityListeners(AuditingEntityListener.class)
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String username;
    
    @CreatedDate
    private LocalDateTime createdAt;
    
    @Builder  // 빌더 패턴 적용
    public User(String username) {
        this.username = username;
    }
}
```

#### Service 계층
```java
@Service
@RequiredArgsConstructor  // final 필드 생성자 주입
@Slf4j  // 로깅 기능 추가
public class UserService {
    private final UserRepository userRepository;
    
    public User createUser(String username) {
        log.info("Creating user: {}", username);
        return userRepository.save(
            User.builder()
                .username(username)
                .build()
        );
    }
}
```

## 5. 모범 사례와 주의사항

### 5.1 권장 사항
- ✅ `@Data` 대신 필요한 어노테이션만 명시적 사용
- ✅ `@Builder` 패턴 활용으로 객체 생성 안정성 확보
- ✅ JPA Entity에는 `@Setter` 지양
- ✅ 생성자 접근 제어에 주의

### 5.2 안티 패턴
- ❌ 무분별한 `@Data` 사용
- ❌ `@ToString`에서 양방향 연관관계 필드 미제외
- ❌ `@EqualsAndHashCode`에서 모든 필드 포함
- ❌ 순환 참조가 발생할 수 있는 구조에서 `@ToString` 사용

### 5.3 성능 최적화
```java
@ToString(onlyExplicitlyIncluded = true)
@EqualsAndHashCode(of = "id")
public class OptimizedEntity {
    @ToString.Include
    private Long id;
    
    private String heavyField1;
    private String heavyField2;
}
```

