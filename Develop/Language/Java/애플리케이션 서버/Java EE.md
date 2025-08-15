---
title: Java EE Jakarta EE
tags: [language, java, 애플리케이션-서버, java-ee]
updated: 2025-08-10
---

## 1️⃣ Java EE란?

Java EE는 **Java Platform, Enterprise Edition**의 약자로, 대규모 **엔터프라이즈 애플리케이션** 개발을 지원하는 Java 플랫폼입니다.  
2020년부터는 **Jakarta EE**라는 이름으로 변경되어 계속 발전하고 있습니다.

## 배경
- 안정적이고 확장 가능한 대규모 애플리케이션 개발 지원.
- 다양한 표준 API와 컴포넌트 제공.
- 플랫폼 독립성과 높은 생산성.

---

1. **표준화**: 표준 API로 구현되어 코드 이식성이 높음.
2. **확장성**: 대규모 애플리케이션에 적합.
3. **다양한 기술 스택**: Servlet, JSP, EJB, JPA 등 풍부한 기능 제공.

1. 복잡한 구조로 인한 학습 곡선.
2. 경량 프레임워크(Spring 등)에 비해 초기 설정이 다소 어려움.

---

- **Servlet**: HTTP 요청 처리.
- **JPA**: 데이터베이스 연동.
- **JAX-RS**: RESTful API 제공.

```java
// User 엔티티
@Entity
public class User {
    @Id @GeneratedValue
    private Long id;
    private String name;

    // Getter와 Setter 생략
}

// JPA를 이용한 데이터베이스 액세스
@Stateless
public class UserService {
    @PersistenceContext
    private EntityManager em;

    public void addUser(String name) {
        User user = new User();
        user.setName(name);
        em.persist(user);
    }

    public List<User> getUsers() {
        return em.createQuery("SELECT u FROM User u", User.class).getResultList();
    }
}

// RESTful 웹 서비스
@Path("/users")
public class UserResource {
    @Inject
    private UserService userService;

    @POST
    public void addUser(String name) {
        userService.addUser(name);
    }

    @GET
    @Produces(MediaType.APPLICATION_JSON)
    public List<User> getUsers() {
        return userService.getUsers();
    }
}
```

---

💡 **참고**: Java EE는 대규모 애플리케이션 개발에 강력한 도구를 제공하지만, 최근에는 Spring Framework와 같은 경량 프레임워크와 함께 사용하거나 대체하는 경우도 많습니다.






---





# Java EE (Jakarta EE)

## ✨ Java EE의 주요 구성 요소

### 1. Servlet (서블릿)
- **HTTP 요청**과 **응답**을 처리하는 서버 측 컴포넌트.
- 동적인 콘텐츠 생성.

```java
@WebServlet("/example")
public class ExampleServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        response.setContentType("text/html");
        response.getWriter().println("<h1>Welcome to Java EE Servlet!</h1>");
    }
}
```

### 2. JSP (JavaServer Pages)
- HTML에 Java 코드를 삽입해 동적 웹 페이지를 생성.
- 서블릿보다 가독성이 좋고 UI 개발에 적합.

```jsp
<%@ page language="java" contentType="text/html; charset=UTF-8" %>
<html>
<body>
    <h1>현재 시간: <%= new java.util.Date() %></h1>
</body>
</html>
```

### 3. EJB (Enterprise Java Beans)
- 트랜잭션, 보안, 데이터 처리 등의 **비즈니스 로직** 구현을 지원.
- 종류:
    - **Stateless**: 상태를 유지하지 않는 비즈니스 로직.
    - **Stateful**: 클라이언트와 상태를 유지.
    - **Message-Driven**: 메시징 시스템과 연동.

```java
@Stateless
public class CalculatorBean {
    public int add(int a, int b) {
        return a + b;
    }
}
```

### 4. JPA (Java Persistence API)
- 객체-관계 매핑(ORM)을 지원하는 API.
- 데이터베이스 연동을 간소화.

```java
@Entity
public class User {
    @Id @GeneratedValue
    private Long id;
    private String name;
    private String email;
}
```

### 5. CDI (Context and Dependency Injection)
- 의존성 주입을 통해 컴포넌트 간의 결합도를 낮추는 기술.

```java
@Named
@RequestScoped
public class HelloBean {
    public String getMessage() {
        return "Hello from CDI!";
    }
}
```

### 6. JAX-RS (RESTful 웹 서비스)
- RESTful API 개발을 위한 표준 API.

```java
@Path("/hello")
public class HelloService {
    @GET
    @Produces(MediaType.TEXT_PLAIN)
    public String sayHello() {
        return "Hello, REST!";
    }
}
```

---

## 📂 Java EE 애플리케이션 서버

Java EE는 다음과 같은 서버에서 실행됩니다:
1. **WildFly (JBoss)**: 빠르고 확장 가능한 서버.
2. **GlassFish**: Java EE의 참조 구현.
3. **Payara**: GlassFish의 상업적 버전.
4. **WebLogic**: Oracle의 엔터프라이즈급 서버.
5. **Apache TomEE**: Tomcat 기반의 Java EE 서버.

---

## 🎯 Java EE의 장단점

## 📜 전체 예제: 간단한 Java EE 애플리케이션

