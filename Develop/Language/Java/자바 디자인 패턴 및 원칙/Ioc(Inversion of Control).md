---
title: Java IoC Inversion of Control DI Dependency Injection
tags: [language, java, 자바-디자인-패턴-및-원칙, ioc-inversion-of-control]
updated: 2025-08-10
---

# Java IoC (Inversion of Control) 및 DI (Dependency Injection)

## IoC란 무엇인가?
IoC(Inversion of Control, 제어의 역전)는 객체의 생성, 생명주기 관리, 의존성 주입 등의 작업을 개발자가 아닌 컨테이너(예: Spring Framework)가 대신 수행하도록 하는 디자인 원칙입니다.  
이 원칙은 객체 간의 결합도를 낮추고 코드의 유연성과 재사용성을 높이는 데 도움을 줍니다.

### IoC의 주요 개념
- **제어의 역전**: 객체의 제어권을 개발자가 아닌 프레임워크 또는 컨테이너에 위임.
- **컨테이너**: 객체의 생성 및 관리를 담당하는 IoC 구현체. 예: Spring Container.

## DI란 무엇인가?
DI(Dependency Injection, 의존성 주입)는 IoC의 구현 방식 중 하나로, 객체 간의 의존 관계를 코드 내부에서 직접 설정하지 않고 외부에서 주입받는 방법입니다.  
이를 통해 객체 간 결합도를 낮추고 유연한 설계를 가능하게 합니다.

### DI의 주요 유형
1. **Constructor Injection**: 생성자를 통해 의존성을 주입.
2. **Setter Injection**: Setter 메서드를 통해 의존성을 주입.
3. **Field Injection**: 필드에 직접 주입(주로 `@Autowired`와 같은 어노테이션 사용).

## IoC와 DI의 특징과 장점
1. **결합도 감소**: 객체 간의 강한 결합을 피하고 유연성을 제공.
2. **테스트 용이성**: 의존성 주입을 통해 Mock 객체를 사용한 단위 테스트가 용이.
3. **유지보수성 증가**: 코드 변경 시 영향 범위가 최소화.

## Java에서 IoC 및 DI 적용
Java에서는 주로 **Spring Framework**를 사용하여 IoC 및 DI를 구현합니다.

### 예제: DI를 활용한 의존성 주입

#### 1. 의존성 추가 (`pom.xml`)
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>
```

#### 2. 의존성 클래스 작성
```java
package com.example.component;

import org.springframework.stereotype.Component;

@Component
public class ExampleComponent {
    public void sayHello() {
        System.out.println("Hello, Spring DI!");
    }
}
```

#### 3. 서비스 클래스 작성
```java
package com.example.service;

import com.example.component.ExampleComponent;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class ExampleService {

    private final ExampleComponent exampleComponent;

    @Autowired
    public ExampleService(ExampleComponent exampleComponent) {
        this.exampleComponent = exampleComponent;
    }

    public void execute() {
        exampleComponent.sayHello();
    }
}
```

#### 4. 메인 클래스 작성
```java
package com.example;

import com.example.service.ExampleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application implements CommandLineRunner {

    @Autowired
    private ExampleService exampleService;

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        exampleService.execute();
    }
}
```

#### 5. 실행 결과
```text
Hello, Spring DI!
```

## IoC와 DI를 사용해야 하는 경우
- 애플리케이션의 복잡성이 증가하는 경우.
- 객체 간의 의존 관계를 명확히 정의하고 싶을 때.
- 단위 테스트 및 유지보수성을 강화하고자 할 때.

## 배경
IoC와 DI는 현대 Java 애플리케이션 개발에서 필수적인 개념입니다.  
Spring Framework와 같은 도구를 활용하면 의존성 관리와 객체 생성을 손쉽게 처리할 수 있어 개발 생산성과 코드 품질을 동시에 높일 수 있습니다.










