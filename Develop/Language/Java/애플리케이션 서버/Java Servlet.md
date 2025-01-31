
# Java Servlet

---

## 1️⃣ Java Servlet이란?
Java Servlet은 **Java 기반의 서버 사이드 기술**로, 클라이언트의 요청을 처리하고 동적인 웹 콘텐츠를 생성하는 데 사용됩니다.  
**HTTP 프로토콜**을 기반으로 동작하며, Java EE (Jakarta EE)의 일부로 제공됩니다.

### 👉🏻 주요 역할
- 클라이언트(웹 브라우저 또는 애플리케이션)로부터의 요청을 처리.
- 데이터베이스와 상호 작용.
- 동적인 HTML, JSON, XML 등의 콘텐츠를 생성.

---

## ✨ Java Servlet의 동작 원리

### 1. 클라이언트 요청
- 클라이언트(웹 브라우저 또는 애플리케이션)가 URL을 통해 요청을 보냅니다.

### 2. 요청 처리
- **Servlet Container**(예: Apache Tomcat)가 요청을 받아 Servlet 클래스에 전달.

### 3. 응답 생성
- Servlet이 요청을 처리한 뒤 클라이언트에게 HTML, JSON 등의 형식으로 응답을 반환.

---

## 📜 Java Servlet 예제

### 예제: 간단한 HelloServlet 구현

```java
import java.io.IOException;  // IOException 처리를 위해 필요
import javax.servlet.ServletException;  // Servlet 예외 처리를 위한 라이브러리
import javax.servlet.annotation.WebServlet;  // URL 매핑을 위한 애너테이션
import javax.servlet.http.HttpServlet;  // HttpServlet 클래스 상속
import javax.servlet.http.HttpServletRequest;  // HTTP 요청 객체
import javax.servlet.http.HttpServletResponse;  // HTTP 응답 객체

// 👉🏻 @WebServlet 애너테이션으로 URL 매핑 설정
@WebServlet("/hello")
public class HelloServlet extends HttpServlet {  // HttpServlet 클래스를 상속

    // ✨ GET 요청 처리 메서드 (doGet)
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        // 응답 콘텐츠 타입 설정 (HTML 형식)
        response.setContentType("text/html");

        // 클라이언트로 보낼 응답 작성
        response.getWriter().println("<h1>Hello, Servlet!</h1>");
    }
}
```

---

## 🔍 코드 주석 설명

### 👉🏻 주요 코드와 설명
1. **`@WebServlet("/hello")`**
    - 이 서블릿을 URL `/hello`로 매핑. 클라이언트가 `/hello`로 요청을 보내면 이 서블릿이 호출됩니다.

2. **`doGet` 메서드**
    - HTTP GET 요청을 처리하는 메서드로, 클라이언트의 요청을 처리하고 응답을 생성합니다.

3. **`response.setContentType("text/html")`**
    - 응답의 콘텐츠 타입을 HTML로 설정. 브라우저가 이를 HTML로 렌더링합니다.

4. **`response.getWriter().println("<h1>Hello, Servlet!</h1>");`**
    - 클라이언트에게 `<h1>` 태그로 감싼 "Hello, Servlet!" 메시지를 응답으로 보냅니다.

---

## 📂 Java Servlet의 주요 인터페이스 및 클래스

### 1. **HttpServlet**
- 모든 Servlet 클래스가 상속해야 하는 기본 클래스입니다.
- HTTP 요청(`GET`, `POST`, `PUT`, `DELETE`)을 처리하기 위한 메서드 제공.

### 2. **HttpServletRequest**
- 클라이언트의 HTTP 요청 정보를 담고 있습니다.
- 주요 메서드:
    - `getParameter(String name)`: 요청 파라미터 값 가져오기.
    - `getHeader(String name)`: HTTP 헤더 값 가져오기.

### 3. **HttpServletResponse**
- 서버가 클라이언트로 보낼 HTTP 응답을 처리합니다.
- 주요 메서드:
    - `setContentType(String type)`: 응답 콘텐츠 타입 설정.
    - `getWriter()`: 응답 데이터를 쓰기 위한 출력 스트림 가져오기.

---

## 🎯 Servlet의 장단점

### **장점**
1. Java의 안정성과 플랫폼 독립성을 활용.
2. HTTP 요청과 응답을 정밀하게 제어 가능.
3. 서블릿 컨테이너(Tomcat 등)와의 연동으로 강력한 확장성 제공.

### **단점**
1. HTML 코드를 직접 작성해야 하므로 생산성이 낮을 수 있음.
2. 비즈니스 로직과 프레젠테이션 로직이 섞이는 경우가 많음.

---

## 🔗 Servlet을 사용하는 주요 프레임워크
- **Spring Framework**: Spring MVC는 Servlet을 기반으로 동작하며, MVC 패턴을 통해 개발 생산성을 극대화.
- **Struts**: Java 기반의 웹 애플리케이션 프레임워크로 Servlet과 JSP를 사용.

---

**💡 참고**: Servlet은 웹 애플리케이션의 기본 기술이지만, 최근에는 Spring과 같은 고수준 프레임워크와 함께 사용하여 효율적인 웹 애플리케이션을 개발하는 것이 일반적입니다.
