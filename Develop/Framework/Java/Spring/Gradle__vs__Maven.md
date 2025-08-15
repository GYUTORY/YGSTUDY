---
title: Gradle vs Maven (빌드 도구 비교)
tags: [framework, java, spring, gradle, maven, build-tools]
updated: 2024-12-19
---

# Gradle vs Maven (빌드 도구 비교)

## 배경

### 빌드 도구의 필요성
Java 프로젝트에서 소스 코드를 컴파일하고, 의존성을 관리하며, 테스트를 실행하고, 배포 가능한 패키지를 생성하는 과정을 자동화하는 도구가 필요합니다.

### Gradle과 Maven의 개요
- **Gradle**: 현대적인 빌드 도구로, Groovy 또는 Kotlin DSL을 사용하여 선언적 및 스크립트 기반 빌드를 모두 지원
- **Maven**: XML 기반의 빌드 도구로, 프로젝트 관리와 빌드 프로세스를 표준화하는 데 중점

### 빌드 도구의 발전 과정
- **Ant**: 2000년대 초반, XML 기반의 빌드 도구
- **Maven**: 2004년, 의존성 관리와 표준화된 빌드 프로세스 도입
- **Gradle**: 2007년, 유연성과 성능을 중점으로 한 현대적 빌드 도구

## 핵심

### Gradle의 특징

#### 1. DSL 기반 빌드
Groovy 또는 Kotlin DSL을 사용하여 빌드 스크립트를 작성할 수 있습니다.

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.0.0'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web:3.0.0'
    testImplementation 'org.springframework.boot:spring-boot-starter-test:3.0.0'
}

tasks.named('test') {
    useJUnitPlatform()
}
```

#### 2. 병렬 빌드
Gradle은 작업을 병렬로 실행하여 빌드 속도를 크게 향상시킵니다.

```bash
# 병렬 빌드 실행
./gradlew build --parallel

# 최대 4개 스레드로 병렬 빌드
./gradlew build --parallel --max-workers=4
```

#### 3. 커스터마이징
유연한 빌드 로직을 작성할 수 있으며, 플러그인 생성을 통해 추가적인 확장이 가능합니다.

```groovy
// 커스텀 태스크 정의
task hello {
    doLast {
        println 'Hello, Gradle!'
    }
}

// 조건부 태스크 실행
task buildIfChanged {
    onlyIf {
        project.hasProperty('buildChanged')
    }
    doLast {
        println 'Building changed components...'
    }
}
```

#### 4. 캐싱
Gradle은 캐시를 사용하여 빌드 시간을 줄입니다.

```groovy
// 빌드 캐시 설정
buildCache {
    local {
        directory = new File(rootDir, 'build-cache')
        removeUnusedEntriesAfterDays = 30
    }
}
```

### Maven의 특징

#### 1. XML 기반 설정
POM(XML 파일)을 사용하여 의존성과 빌드 구성을 정의합니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <spring.boot.version>3.0.0</spring.boot.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>${spring.boot.version}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <version>${spring.boot.version}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <version>${spring.boot.version}</version>
            </plugin>
        </plugins>
    </build>
</project>
```

#### 2. 의존성 관리
중앙 저장소(Maven Central)를 통해 의존성을 쉽게 관리할 수 있습니다.

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>3.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

#### 3. 표준화된 구조
Maven은 표준 프로젝트 구조와 빌드 수명 주기(lifecycle)를 제공합니다.

```
project/
├── src/
│   ├── main/
│   │   ├── java/
│   │   └── resources/
│   └── test/
│       ├── java/
│       └── resources/
├── target/
└── pom.xml
```

#### 4. 플러그인 중심
Maven의 대부분의 작업은 플러그인을 통해 이루어집니다.

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId>
            <version>3.11.0</version>
            <configuration>
                <source>17</source>
                <target>17</target>
            </configuration>
        </plugin>
    </plugins>
</build>
```

## 예시

### Gradle 빌드 파일 예제

#### Spring Boot 프로젝트
```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.0.0'
    id 'io.spring.dependency-management' version '1.1.0'
}

group = 'com.example'
version = '1.0.0'
sourceCompatibility = '17'

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'com.h2database:h2'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}

tasks.named('test') {
    useJUnitPlatform()
}

// 커스텀 태스크
task printVersion {
    doLast {
        println "Project version: ${version}"
    }
}
```

#### 멀티 모듈 프로젝트
```groovy
// settings.gradle
rootProject.name = 'multi-module-project'
include 'api', 'service', 'web'

// build.gradle (루트)
allprojects {
    group = 'com.example'
    version = '1.0.0'
    
    repositories {
        mavenCentral()
    }
}

subprojects {
    apply plugin: 'java'
    apply plugin: 'org.springframework.boot'
    apply plugin: 'io.spring.dependency-management'
    
    sourceCompatibility = '17'
    
    dependencies {
        testImplementation 'org.springframework.boot:spring-boot-starter-test'
    }
}
```

### Maven 빌드 파일 예제

#### Spring Boot 프로젝트
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.0.0</version>
        <relativePath/>
    </parent>
    
    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>
    <name>demo</name>
    <description>Demo project for Spring Boot</description>
    
    <properties>
        <java.version>17</java.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

#### 멀티 모듈 프로젝트
```xml
<!-- pom.xml (루트) -->
<project xmlns="http://maven.apache.org/POM/4.0.0" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>parent-project</artifactId>
    <version>1.0.0</version>
    <packaging>pom</packaging>
    
    <modules>
        <module>api</module>
        <module>service</module>
        <module>web</module>
    </modules>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.0.0</version>
        <relativePath/>
    </parent>
    
    <properties>
        <java.version>17</java.version>
    </properties>
    
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>com.example</groupId>
                <artifactId>api</artifactId>
                <version>${project.version}</version>
            </dependency>
            <dependency>
                <groupId>com.example</groupId>
                <artifactId>service</artifactId>
                <version>${project.version}</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
```

## 운영 팁

### 성능 최적화

#### Gradle 성능 최적화
```groovy
// gradle.properties
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.configureondemand=true
org.gradle.jvmargs=-Xmx2048m -XX:MaxPermSize=512m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8

// 빌드 스캔 활성화
plugins {
    id 'com.gradle.build-scan' version '3.10.3'
}

buildScan {
    termsOfServiceUrl = 'https://gradle.com/terms-of-service'
    termsOfServiceAgree = 'yes'
}
```

#### Maven 성능 최적화
```xml
<!-- settings.xml -->
<settings>
    <mirrors>
        <mirror>
            <id>nexus</id>
            <mirrorOf>*</mirrorOf>
            <url>http://localhost:8081/repository/maven-public/</url>
        </mirror>
    </mirrors>
    
    <profiles>
        <profile>
            <id>jdk-17</id>
            <activation>
                <activeByDefault>true</activeByDefault>
                <jdk>17</jdk>
            </activation>
            <properties>
                <maven.compiler.source>17</maven.compiler.source>
                <maven.compiler.target>17</maven.compiler.target>
            </properties>
        </profile>
    </profiles>
</settings>
```

### 의존성 관리

#### Gradle 의존성 관리
```groovy
// 버전 카탈로그 사용
dependencyResolutionManagement {
    versionCatalogs {
        libs {
            version('spring-boot', '3.0.0')
            version('spring-cloud', '2022.0.0')
            
            library('spring-boot-starter-web', 'org.springframework.boot', 'spring-boot-starter-web').versionRef('spring-boot')
            library('spring-boot-starter-data-jpa', 'org.springframework.boot', 'spring-boot-starter-data-jpa').versionRef('spring-boot')
        }
    }
}

dependencies {
    implementation libs.spring.boot.starter.web
    implementation libs.spring.boot.starter.data.jpa
}
```

#### Maven 의존성 관리
```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>3.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2022.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### CI/CD 통합

#### Gradle CI/CD
```yaml
# GitHub Actions
name: Build with Gradle

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up JDK 17
      uses: actions/setup-java@v3
      with:
        java-version: '17'
        distribution: 'temurin'
    
    - name: Build with Gradle
      uses: gradle/gradle-build-action@v2
      with:
        arguments: build
    
    - name: Upload build reports
      uses: gradle/gradle-build-action@v2
      with:
        arguments: build
        build-root-directory: .
        github-token: ${{ secrets.GITHUB_TOKEN }}
```

#### Maven CI/CD
```yaml
# GitHub Actions
name: Build with Maven

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up JDK 17
      uses: actions/setup-java@v3
      with:
        java-version: '17'
        distribution: 'temurin'
    
    - name: Build with Maven
      run: mvn -B package --file pom.xml
    
    - name: Upload build reports
      uses: actions/upload-artifact@v3
      with:
        name: build-reports
        path: target/site/
```

## 참고

### 주요 차이점 비교

| **항목**           | **Gradle**                         | **Maven**                         |
|-------------------|----------------------------------|----------------------------------|
| **빌드 스크립트**    | Groovy/Kotlin DSL                 | XML 기반 설정                     |
| **빌드 속도**       | 빠름 (병렬 빌드 및 캐싱 지원)         | 느림 (병렬 빌드 기본 미지원)          |
| **학습 곡선**       | 비교적 가파름                      | 완만함                             |
| **유연성**          | 매우 유연                          | 제한적                             |
| **플러그인 개발**    | 간단함                             | 복잡함                             |
| **의존성 관리**     | Gradle Wrapper를 통해 간편 관리       | Maven Central을 통한 관리           |
| **IDE 지원**       | IntelliJ IDEA, Eclipse            | 모든 주요 IDE                     |
| **커뮤니티**        | 활발한 커뮤니티                     | 매우 큰 커뮤니티                   |

### 선택 가이드

#### Gradle을 선택하는 경우
- **성능이 중요한 경우**: 병렬 빌드와 캐싱으로 빠른 빌드
- **유연한 빌드 로직이 필요한 경우**: 복잡한 커스터마이징
- **Android 개발**: Android Studio의 기본 빌드 도구
- **최신 기술을 선호하는 경우**: 현대적인 DSL 사용

#### Maven을 선택하는 경우
- **표준화된 프로세스가 필요한 경우**: 엄격한 구조와 라이프사이클
- **학습 곡선을 낮추고 싶은 경우**: 간단한 XML 기반 설정
- **기존 프로젝트와의 호환성**: 레거시 시스템과의 통합
- **대규모 팀**: 명확한 구조와 표준화

### 마이그레이션 가이드

#### Maven에서 Gradle로 마이그레이션
```bash
# Gradle Wrapper 설치
gradle wrapper

# Maven 프로젝트를 Gradle로 변환
gradle init --type pom
```

#### Gradle에서 Maven으로 마이그레이션
```bash
# Maven 프로젝트 구조 생성
mvn archetype:generate -DgroupId=com.example -DartifactId=demo -DarchetypeArtifactId=maven-archetype-quickstart -DinteractiveMode=false
```

### 결론
Gradle과 Maven은 각각의 장단점이 있는 뛰어난 빌드 도구입니다.
Gradle은 성능과 유연성에서 우수하며, Maven은 표준화와 안정성에서 강점을 가집니다.
프로젝트의 요구사항과 팀의 기술 수준을 고려하여 적절한 도구를 선택하는 것이 중요합니다.
최근에는 Gradle의 사용이 증가하고 있지만, Maven도 여전히 많은 프로젝트에서 사용되고 있습니다.

