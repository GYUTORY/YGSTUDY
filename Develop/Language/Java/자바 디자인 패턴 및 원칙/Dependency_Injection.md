---
title: Java - Dependency Injection
tags: [language, java, 자바-디자인-패턴-및-원칙, dependencyinjection]
updated: 2025-12-29
---

## 의존성 주입 (Dependency Injection, DI)이란?
**의존성 주입(Dependency Injection, DI)** 은 **객체가 필요한 다른 객체를 직접 생성하지 않고 외부에서 주입받는 프로그래밍 기법**입니다.

## 배경
- **의존성 주입 없이:** `QuoteController`가 `QuoteService`를 직접 생성
- **의존성 주입 사용:** `QuoteService`를 외부에서 전달받아 사용

---



- `@Service`: `QuoteService` 클래스를 **빈(Bean)**으로 등록합니다.
- `@Autowired`: `QuoteService` 객체를 **자동으로 주입**합니다.
- `@RestController`: `QuoteController`가 RESTful 웹 서비스임을 선언.

---

```java
package com.example.dependencyinjection.controller;

import com.example.dependencyinjection.service.QuoteService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

// @RestController: 이 클래스가 REST API를 제공하는 컨트롤러임을 나타냅니다.
@RestController
public class QuoteController {

    private final QuoteService quoteService;

    // 생성자 기반 의존성 주입 (권장 방식)
    @Autowired
    public QuoteController(QuoteService quoteService) {
        this.quoteService = quoteService;
    }

    // HTTP GET 요청을 처리하는 엔드포인트
    @GetMapping("/quote")
    public ResponseEntity<String> getQuote() {
        // 비즈니스 로직 호출 후 결과 반환
        return ResponseEntity.ok(quoteService.getQuote());
    }
}
```

---

1. **생성자 기반 주입을 사용하세요.**
2. **필드 주입과 세터 주입은 지양하세요.**
3. **`@Autowired`는 생성자 주입에서는 생략 가능하지만 명시적으로 사용하는 것도 가능.**
4. **`@Service`, `@Repository`와 같은 스프링 어노테이션을 이해하고 사용하세요.**

---

📩 **질문이나 추가 예제 요청이 있으시면 언제든 문의 주세요!** 😊






---





# Java - 의존성 주입 (Dependency Injection) 가이드

## 의존성 주입을 사용하지 않은 경우 (Bad Case)
- 아래 코드는 의존성 주입을 사용하지 않은 경우입니다.
- QuoteController 클래스 내부에서 QuoteService 객체를 직접 생성(new QuoteService())하여 사용하고 있습니다.

```java
@RestController
public class QuoteController {

    private final QuoteService quoteService = new QuoteService(); // ❌ 직접 객체 생성

    @GetMapping("/quote")
    public String getQuote() {
        return quoteService.getQuote();
    }
}
```

🔴 문제점 왜 의존성 주입이 왜 필요한가?
### 1. 강한 결합 (Tightly Coupled)
- QuoteController가 QuoteService에 직접 의존하므로, QuoteService의 구현이 변경되면 QuoteController도 변경해야 합니다.
- 예를 들어, QuoteService를 AdvancedQuoteService로 변경하려면 QuoteController의 코드도 수정해야 합니다.

### 2. 테스트 어려움
- QuoteService를 Mock 객체로 대체할 수 없기 때문에 단위 테스트(Unit Test)가 어렵습니다.
- 예를 들어, 실제 QuoteService가 데이터베이스를 사용한다면, 테스트 시에도 데이터베이스 연결이 필요합니다.

### 3. 유지보수성 저하
- QuoteService의 변경이 있을 때마다 QuoteController도 수정해야 하므로 유지보수가 어려워집니다.

---

## 의존성 주입 방식 3가지
Java와 Spring Boot에서 사용하는 의존성 주입 방식은 크게 3가지입니다:

---

### 📦 1. **필드 주입 (Field Injection)**
```java
@RestController
public class QuoteController {

    @Autowired
    private QuoteService quoteService; // 필드 직접 주입
}
```
**🔴 단점:**
- **테스트가 어려움:** `Mock` 객체를 주입하기 힘듦
- **결합도가 높아짐:** 외부 객체에 강하게 의존

**⚠️ 권장되지 않는 방식입니다.**

---

### 📦 2. **세터 주입 (Setter Injection)**
```java
@RestController
public class QuoteController {

    private QuoteService quoteService;

    @Autowired
    public void setQuoteService(QuoteService quoteService) {
        this.quoteService = quoteService;
    }
}
```
**🔵 장점:**
- 필요할 때만 의존성을 주입할 수 있음

**⚠️ 단점:**
- **객체의 불변성(immutability)을 보장하지 않음.**

---

### 📦 3. **생성자 기반 주입 (Constructor Injection) (권장)**
```java
@RestController
public class QuoteController {

    private final QuoteService quoteService;

    // 생성자를 통한 의존성 주입
    @Autowired
    public QuoteController(QuoteService quoteService) {
        this.quoteService = quoteService;
    }
}
```

**✅ 장점:**
- **불변성 보장:** `final` 키워드를 통해 의존성 불변성 유지 가능
- **테스트 용이:** `Mock` 객체를 주입할 수 있음
- **권장되는 베스트 프랙티스!**

---

## `@Autowired`의 역할
`@Autowired`는 **의존성 자동 주입**을 위한 **스프링 어노테이션**입니다.

```java
@Service
public class QuoteService {

    public String getQuote() {
        return "Success is not final, failure is not fatal.";
    }
}
```

```java
@RestController
public class QuoteController {

    private final QuoteService quoteService;

    @Autowired
    public QuoteController(QuoteService quoteService) {
        this.quoteService = quoteService;
    }

    @GetMapping("/quote")
    public String getQuote() {
        return quoteService.getQuote();
    }
}
```

## `@Component` vs. `@Service` vs. `@Repository`의 차이
| 어노테이션         | 역할                                      | 사용 예 |
|--------------------|------------------------------------------|---------|
| `@Component`       | **기본 빈(Bean) 등록**                   | 일반적인 클래스 |
| `@Service`         | **비즈니스 로직을 담은 클래스**         | `UserService` |
| `@Repository`      | **데이터베이스 접근을 담당하는 클래스** | `UserRepository` |

---

