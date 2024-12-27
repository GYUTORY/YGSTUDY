
# Gradle vs Maven

## 1. Gradle
Gradle은 현대적인 빌드 도구로, Groovy 또는 Kotlin DSL을 사용하여 선언적 및 스크립트 기반 빌드를 모두 지원합니다. 고성능과 유연성을 중점으로 설계되었습니다.

### 주요 특징
1. **DSL 기반 빌드**  
   Groovy 또는 Kotlin DSL을 사용하여 빌드 스크립트를 작성할 수 있습니다.

   ```groovy
   plugins {
       id 'java'
   }

   repositories {
       mavenCentral()
   }

   dependencies {
       implementation 'org.springframework.boot:spring-boot-starter:3.0.0'
   }
   ```

2. **병렬 빌드**  
   Gradle은 작업을 병렬로 실행하여 빌드 속도를 크게 향상시킵니다.

3. **커스터마이징**  
   유연한 빌드 로직을 작성할 수 있으며, 플러그인 생성을 통해 추가적인 확장이 가능합니다.

4. **캐싱**  
   Gradle은 캐시를 사용하여 빌드 시간을 줄입니다.

---

## 2. Maven
Maven은 XML 기반의 빌드 도구로, 프로젝트 관리와 빌드 프로세스를 표준화하는 데 중점을 둡니다. Java 프로젝트에서 널리 사용되며, 정형화된 구조와 간단한 설정이 특징입니다.

### 주요 특징
1. **XML 기반 설정**  
   POM(XML 파일)을 사용하여 의존성과 빌드 구성을 정의합니다.

   ```xml
   <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
       <modelVersion>4.0.0</modelVersion>
       <groupId>com.example</groupId>
       <artifactId>demo</artifactId>
       <version>1.0.0</version>
       <dependencies>
           <dependency>
               <groupId>org.springframework.boot</groupId>
               <artifactId>spring-boot-starter</artifactId>
               <version>3.0.0</version>
           </dependency>
       </dependencies>
   </project>
   ```

2. **의존성 관리**  
   중앙 저장소(Maven Central)를 통해 의존성을 쉽게 관리할 수 있습니다.

3. **수직적 표준화**  
   Maven은 표준 프로젝트 구조와 빌드 수명 주기(lifecycle)를 제공합니다.

4. **플러그인 중심**  
   Maven의 대부분의 작업은 플러그인을 통해 이루어집니다.

---

## 3. 주요 차이점
| **항목**           | **Gradle**                         | **Maven**                         |
|-------------------|----------------------------------|----------------------------------|
| **빌드 스크립트**    | Groovy/Kotlin DSL                 | XML 기반 설정                     |
| **빌드 속도**       | 빠름 (병렬 빌드 및 캐싱 지원)         | 느림 (병렬 빌드 기본 미지원)          |
| **학습 곡선**       | 비교적 가파름                      | 완만함                             |
| **유연성**          | 매우 유연                          | 제한적                             |
| **플러그인 개발**    | 간단함                             | 복잡함                             |
| **의존성 관리**     | Gradle Wrapper를 통해 간편 관리       | Maven Central을 통한 관리           |

---

## 4. 사용 예시
### Gradle 빌드 파일 예제
```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.0.0'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter:3.0.0'
    testImplementation 'org.springframework.boot:spring-boot-starter-test:3.0.0'
}
```

### Maven POM 파일 예제
```xml
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter</artifactId>
            <version>3.0.0</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <version>3.0.0</version>
        </dependency>
    </dependencies>
</project>
```

---

## 5. 결론
Gradle은 현대적인 빌드 시스템으로 고성능과 유연성을 제공하며, 복잡한 빌드 요구사항에 적합합니다. Maven은 표준화된 빌드와 간단한 설정을 선호하는 프로젝트에 적합합니다. 프로젝트의 요구사항에 따라 적합한 빌드 도구를 선택하는 것이 중요합니다.
