---
title: Java Servlet
tags: [language, java, 애플리케이션-서버, java-servlet]
updated: 2026-03-28
---

# Java Servlet

Servlet은 Java로 HTTP 요청을 받아 처리하는 서버 사이드 컴포넌트다. CGI(Common Gateway Interface)의 대안으로 등장했고, 요청마다 프로세스를 생성하는 CGI와 달리 하나의 JVM 안에서 스레드로 요청을 처리한다.

Servlet 자체를 직접 작성하는 일은 줄었지만, Spring MVC가 내부적으로 Servlet 위에서 돌아가기 때문에 동작 원리를 이해해야 문제가 생겼을 때 원인을 찾을 수 있다.

---

## Servlet 생명주기

Servlet 인스턴스는 개발자가 아니라 **Servlet Container**(Tomcat, Jetty 등)가 관리한다. 생명주기는 세 단계로 나뉜다.

### init()

컨테이너가 Servlet 클래스를 로드하고 인스턴스를 생성한 뒤 **딱 한 번** 호출한다. DB 커넥션 풀 참조를 잡거나, 설정 파일을 읽는 등 초기화 작업을 여기서 한다.

```java
@WebServlet("/order")
public class OrderServlet extends HttpServlet {

    private DataSource dataSource;

    @Override
    public void init(ServletConfig config) throws ServletException {
        super.init(config);
        try {
            Context ctx = new InitialContext();
            this.dataSource = (DataSource) ctx.lookup("java:comp/env/jdbc/orderDB");
        } catch (NamingException e) {
            throw new ServletException("DataSource lookup 실패", e);
        }
    }
}
```

`init()`에서 예외가 발생하면 해당 Servlet은 서비스 불가 상태가 된다. 컨테이너는 이후 요청에 대해 해당 Servlet을 호출하지 않는다.

`load-on-startup` 값을 설정하면 서버 시작 시점에 미리 로드할 수 있다. 설정하지 않으면 첫 번째 요청이 들어올 때 로드되므로, 첫 요청의 응답 시간이 길어지는 경우가 있다.

### service()

모든 요청마다 호출된다. `HttpServlet`을 상속하면 `service()`가 HTTP 메서드(GET, POST, PUT, DELETE 등)에 따라 `doGet()`, `doPost()` 등으로 분기한다. 직접 `service()`를 오버라이드할 일은 거의 없다.

```java
@Override
protected void doGet(HttpServletRequest req, HttpServletResponse resp)
        throws ServletException, IOException {
    String orderId = req.getParameter("id");
    // orderId로 주문 조회 처리
}

@Override
protected void doPost(HttpServletRequest req, HttpServletResponse resp)
        throws ServletException, IOException {
    // 주문 생성 처리
}
```

### destroy()

컨테이너가 Servlet을 제거할 때 한 번 호출한다. 서버 종료 시, 또는 웹 애플리케이션을 언디플로이할 때 실행된다. 리소스 정리가 필요하면 여기서 한다.

```java
@Override
public void destroy() {
    // 열어둔 리소스가 있으면 정리
    log("OrderServlet 종료");
}
```

주의할 점: `destroy()` 호출 시점에 아직 `service()` 스레드가 실행 중일 수 있다. 컨테이너가 모든 요청 완료를 보장하지 않으므로, 종료 시 진행 중인 작업을 고려해야 한다.

---

## Servlet Container 동작 구조

### 요청 처리 흐름

1. 클라이언트가 HTTP 요청을 보낸다
2. 컨테이너가 요청 URL을 보고 매핑된 Servlet을 찾는다
3. 스레드 풀에서 스레드 하나를 꺼내 해당 Servlet의 `service()` 메서드를 호출한다
4. `HttpServletRequest`, `HttpServletResponse` 객체를 생성해서 파라미터로 넘긴다
5. Servlet이 응답을 작성하면 컨테이너가 클라이언트에게 전송한다
6. 스레드는 풀로 반환된다

### 스레드 풀

Tomcat 기준으로 기본 스레드 풀 크기는 200이다(`server.xml`의 `maxThreads`). 요청이 200개를 넘으면 큐에 대기하게 되고, 큐마저 차면 요청이 거부된다.

Servlet 인스턴스는 기본적으로 **하나만 생성**된다. 200개의 스레드가 동시에 같은 인스턴스의 `service()`를 호출하는 구조다. 이 부분이 thread-safety 문제의 원인이 된다.

### URL 매핑 규칙

컨테이너는 URL 패턴을 다음 우선순위로 매칭한다:

1. **정확한 경로 매칭**: `/order/detail` — URL이 정확히 일치
2. **경로 접두사 매칭**: `/order/*` — `/order/`로 시작하는 모든 URL
3. **확장자 매칭**: `*.do` — `.do`로 끝나는 모든 URL
4. **기본 매칭**: `/` — 위 규칙에 해당하지 않는 모든 요청

Spring MVC의 `DispatcherServlet`이 `/`로 매핑되는 이유가 여기 있다. 다른 Servlet에 매핑되지 않은 모든 요청을 받아서 내부적으로 다시 라우팅하는 구조다.

---

## Filter와 FilterChain

Filter는 Servlet 앞단에서 요청/응답을 가로채 공통 처리를 수행한다. 여러 Filter가 체인 형태로 연결되고, 순서대로 실행된 뒤 마지막에 Servlet이 호출된다.

### 기본 구조

```java
public class LoggingFilter implements Filter {

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        // 필터 초기화
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {
        long start = System.currentTimeMillis();
        HttpServletRequest req = (HttpServletRequest) request;

        // 다음 필터 또는 Servlet으로 진행
        chain.doFilter(request, response);

        long duration = System.currentTimeMillis() - start;
        System.out.println(req.getRequestURI() + " - " + duration + "ms");
    }

    @Override
    public void destroy() {
        // 필터 정리
    }
}
```

`chain.doFilter()`를 호출하지 않으면 요청이 Servlet까지 도달하지 않는다. 인증 필터에서 권한이 없을 때 이 방식으로 요청을 차단한다.

### 인코딩 필터

Tomcat에서 POST 요청의 한글 파라미터가 깨지는 문제는 흔하다. 캐릭터 인코딩 필터로 해결한다.

```java
@WebFilter("/*")
public class EncodingFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {
        request.setCharacterEncoding("UTF-8");
        response.setCharacterEncoding("UTF-8");
        chain.doFilter(request, response);
    }
}
```

Spring Boot에서는 `CharacterEncodingFilter`가 자동 등록되어 있어서 직접 만들 필요가 없다. 하지만 순수 Servlet 환경이나 레거시 프로젝트에서는 직접 등록해야 한다.

### 인증 필터

```java
@WebFilter("/api/*")
public class AuthFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {
        HttpServletRequest req = (HttpServletRequest) request;
        HttpServletResponse resp = (HttpServletResponse) response;

        HttpSession session = req.getSession(false);
        if (session == null || session.getAttribute("userId") == null) {
            resp.sendError(HttpServletResponse.SC_UNAUTHORIZED);
            return; // chain.doFilter()를 호출하지 않으므로 여기서 끝
        }

        chain.doFilter(request, response);
    }
}
```

`req.getSession(false)`에서 `false`를 넘기는 이유: 세션이 없을 때 새로 만들지 않기 위해서다. `getSession()` 또는 `getSession(true)`를 쓰면 세션이 없는 경우 빈 세션을 생성하는데, 인증 확인 목적이면 불필요하다.

### Filter 순서

`web.xml`에서는 선언 순서가 실행 순서다. 어노테이션 기반에서는 순서를 보장하지 않는다. 순서가 중요한 경우(인코딩 필터를 인증 필터보다 먼저 실행해야 하는 경우 등) `web.xml`로 명시하거나, Spring의 `FilterRegistrationBean`에서 `setOrder()`를 사용한다.

---

## HttpSession과 Cookie

### 세션 동작 방식

HTTP는 stateless 프로토콜이므로 요청 간 상태를 유지하려면 세션이 필요하다. Servlet의 세션 관리 방식은 다음과 같다:

1. 서버가 `getSession()`을 호출하면 세션 ID를 생성한다
2. 응답 헤더에 `Set-Cookie: JSESSIONID=ABC123` 형태로 쿠키를 내려보낸다
3. 이후 클라이언트 요청마다 `Cookie: JSESSIONID=ABC123` 헤더가 포함된다
4. 서버는 이 ID로 서버 메모리에 저장된 세션 데이터를 찾는다

```java
// 세션에 데이터 저장
HttpSession session = request.getSession();
session.setAttribute("userId", "user123");
session.setAttribute("loginTime", System.currentTimeMillis());

// 세션에서 데이터 조회
HttpSession session = request.getSession(false);
if (session != null) {
    String userId = (String) session.getAttribute("userId");
}

// 세션 무효화 (로그아웃)
session.invalidate();
```

### 세션 타임아웃

기본 세션 타임아웃은 컨테이너마다 다르지만 Tomcat은 30분이다. `web.xml`에서 변경할 수 있다.

```xml
<session-config>
    <session-timeout>60</session-timeout> <!-- 분 단위 -->
</session-config>
```

코드에서 개별 세션의 타임아웃을 지정할 수도 있다:

```java
session.setMaxInactiveInterval(1800); // 초 단위, 30분
```

### 세션 사용 시 주의사항

**세션에 큰 객체를 넣지 않는다.** 세션은 서버 메모리에 저장된다. 사용자가 1만 명이고 세션 하나에 1MB를 넣으면 10GB 메모리가 필요하다. 세션에는 사용자 ID, 권한 정보 같은 최소한의 데이터만 넣고, 나머지는 DB에서 조회한다.

**세션에 넣는 객체는 Serializable을 구현한다.** 세션 클러스터링(여러 서버 간 세션 공유)을 사용하면 세션 데이터를 직렬화해서 전송해야 한다. Serializable을 구현하지 않은 객체를 넣으면 클러스터링 시점에 `NotSerializableException`이 발생한다.

**분산 환경에서 세션은 문제가 된다.** 서버가 2대 이상이면 로드밸런서가 요청을 분산하므로, 세션이 없는 서버로 요청이 갈 수 있다. Sticky Session(같은 사용자를 같은 서버로 보냄), Session Replication(세션을 서버 간 복제), 외부 세션 저장소(Redis) 중 하나를 선택해야 한다. Spring Session + Redis 조합이 실무에서 많이 쓰인다.

### Cookie 직접 다루기

```java
// 쿠키 생성
Cookie cookie = new Cookie("theme", "dark");
cookie.setMaxAge(60 * 60 * 24 * 30); // 30일
cookie.setPath("/");
cookie.setHttpOnly(true);  // JavaScript에서 접근 불가
cookie.setSecure(true);    // HTTPS에서만 전송
response.addCookie(cookie);

// 쿠키 읽기
Cookie[] cookies = request.getCookies();
if (cookies != null) {
    for (Cookie c : cookies) {
        if ("theme".equals(c.getName())) {
            String theme = c.getValue();
        }
    }
}
```

`HttpOnly`와 `Secure` 플래그는 보안상 반드시 설정한다. `HttpOnly`를 빠뜨리면 XSS 공격으로 쿠키를 탈취당할 수 있다.

---

## forward vs redirect

### forward (서버 내부 이동)

```java
RequestDispatcher dispatcher = request.getRequestDispatcher("/result.jsp");
dispatcher.forward(request, response);
```

- 서버 내부에서 처리가 넘어간다. 클라이언트는 URL 변경을 모른다.
- request 객체가 그대로 전달되므로 `setAttribute()`로 넣은 데이터를 다음 페이지에서 꺼낼 수 있다.
- 같은 웹 애플리케이션 내에서만 가능하다.
- URL은 처음 요청한 주소 그대로 유지된다.

### redirect (클라이언트 재요청)

```java
response.sendRedirect("/order/complete?id=123");
```

- 서버가 302 응답을 보내면 클라이언트가 새 URL로 다시 요청한다.
- 요청이 2번 발생하므로 request 객체는 새로 생성된다. 이전 request에 넣은 데이터는 없어진다.
- 다른 도메인으로도 이동할 수 있다.
- 브라우저 주소창의 URL이 바뀐다.

### 언제 무엇을 쓰는가

POST 요청 처리 후에는 redirect를 쓴다. forward를 쓰면 사용자가 새로고침할 때 POST 요청이 다시 전송된다(중복 주문 같은 문제). 이걸 **PRG(Post-Redirect-Get) 패턴**이라고 한다.

```java
@Override
protected void doPost(HttpServletRequest req, HttpServletResponse resp)
        throws ServletException, IOException {
    // 주문 처리
    String orderId = orderService.createOrder(req);

    // redirect로 GET 요청으로 전환
    resp.sendRedirect("/order/complete?id=" + orderId);
}
```

서버 내부에서 데이터를 전달하며 페이지를 렌더링할 때는 forward를 쓴다. JSP에서 많이 보이는 패턴이다.

---

## web.xml vs 어노테이션 설정

### web.xml 방식

Servlet 3.0 이전에는 `web.xml`이 유일한 설정 방법이었다.

```xml
<web-app>
    <servlet>
        <servlet-name>orderServlet</servlet-name>
        <servlet-class>com.example.OrderServlet</servlet-class>
        <load-on-startup>1</load-on-startup>
    </servlet>
    <servlet-mapping>
        <servlet-name>orderServlet</servlet-name>
        <url-pattern>/order/*</url-pattern>
    </servlet-mapping>

    <filter>
        <filter-name>encodingFilter</filter-name>
        <filter-class>com.example.EncodingFilter</filter-class>
    </filter>
    <filter-mapping>
        <filter-name>encodingFilter</filter-name>
        <url-pattern>/*</url-pattern>
    </filter-mapping>
</web-app>
```

### 어노테이션 방식 (Servlet 3.0+)

```java
@WebServlet(urlPatterns = "/order/*", loadOnStartup = 1)
public class OrderServlet extends HttpServlet { }

@WebFilter("/*")
public class EncodingFilter implements Filter { }

@WebListener
public class AppContextListener implements ServletContextListener { }
```

### 어떤 방식을 쓰는가

현실적으로 두 방식이 섞여서 쓰인다. 어노테이션이 간편하지만, Filter 실행 순서를 제어해야 하거나 외부 라이브러리의 Servlet/Filter를 등록해야 할 때는 `web.xml`을 써야 한다.

Spring Boot에서는 `web.xml` 없이 `@Bean`으로 `FilterRegistrationBean`, `ServletRegistrationBean`을 등록하는 방식을 쓴다.

```java
@Bean
public FilterRegistrationBean<EncodingFilter> encodingFilter() {
    FilterRegistrationBean<EncodingFilter> registration = new FilterRegistrationBean<>();
    registration.setFilter(new EncodingFilter());
    registration.addUrlPatterns("/*");
    registration.setOrder(1);
    return registration;
}
```

---

## 비동기 처리 (Servlet 3.0+)

Servlet은 기본적으로 하나의 요청에 하나의 스레드를 점유한다. 외부 API 호출이나 대용량 파일 처리처럼 오래 걸리는 작업이 있으면 스레드 풀이 금방 고갈된다. Servlet 3.0에서 추가된 `AsyncContext`로 요청 처리 스레드를 먼저 반환하고, 별도 스레드에서 작업을 완료할 수 있다.

```java
@WebServlet(urlPatterns = "/async/report", asyncSupported = true)
public class AsyncReportServlet extends HttpServlet {

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {

        // 비동기 모드 시작 — 현재 스레드는 반환된다
        AsyncContext asyncContext = req.startAsync();
        asyncContext.setTimeout(30000); // 30초 타임아웃

        asyncContext.start(() -> {
            try {
                // 오래 걸리는 작업 (별도 스레드에서 실행)
                String report = reportService.generateLargeReport();

                HttpServletResponse response = (HttpServletResponse) asyncContext.getResponse();
                response.setContentType("application/json");
                response.setCharacterEncoding("UTF-8");
                response.getWriter().write(report);

                asyncContext.complete(); // 응답 완료
            } catch (Exception e) {
                asyncContext.complete();
            }
        });
    }
}
```

`asyncSupported = true`를 빠뜨리면 `IllegalStateException`이 발생한다. 해당 Servlet에 연결된 Filter가 있다면 Filter에도 `asyncSupported = true`를 설정해야 한다.

`asyncContext.start()`에 넘긴 Runnable은 컨테이너의 스레드 풀에서 실행된다. 비동기 처리의 이점을 제대로 살리려면 별도의 스레드 풀(ExecutorService)을 만들어서 사용하는 게 낫다.

```java
private final ExecutorService executor = Executors.newFixedThreadPool(10);

@Override
protected void doGet(HttpServletRequest req, HttpServletResponse resp)
        throws ServletException, IOException {
    AsyncContext asyncContext = req.startAsync();
    executor.submit(() -> {
        try {
            // 작업 처리
            asyncContext.getResponse().getWriter().write("done");
            asyncContext.complete();
        } catch (Exception e) {
            asyncContext.complete();
        }
    });
}
```

---

## Thread-Safety 문제

Servlet 인스턴스는 컨테이너에 **하나만** 존재한다. 동시에 들어오는 요청은 같은 인스턴스의 `service()` 메서드를 서로 다른 스레드에서 호출한다. 이 구조에서 인스턴스 변수를 사용하면 동시성 문제가 발생한다.

### 문제가 되는 코드

```java
@WebServlet("/counter")
public class CounterServlet extends HttpServlet {

    private int count = 0; // 인스턴스 변수 — 모든 스레드가 공유

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        count++; // Race condition 발생
        resp.getWriter().write("count: " + count);
    }
}
```

스레드 A와 B가 동시에 `count++`를 실행하면 값이 1만 증가하는 경우가 생긴다. `count++`는 읽기-수정-쓰기 3단계 연산이기 때문이다.

### 해결 방법

**인스턴스 변수를 쓰지 않는다.** 가장 간단하고 확실한 방법이다. 요청 처리에 필요한 데이터는 지역 변수로 선언하면 스레드마다 별도의 스택 프레임에 저장되므로 안전하다.

```java
@Override
protected void doGet(HttpServletRequest req, HttpServletResponse resp)
        throws ServletException, IOException {
    // 지역 변수는 스레드마다 독립적
    int requestCount = calculateCount();
    resp.getWriter().write("count: " + requestCount);
}
```

인스턴스 변수가 꼭 필요하다면(초기화 시 설정한 읽기 전용 값 등) `final`로 선언하거나, `AtomicInteger` 같은 동시성 도구를 사용한다.

```java
@WebServlet("/counter")
public class SafeCounterServlet extends HttpServlet {

    private final AtomicInteger count = new AtomicInteger(0);

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        int current = count.incrementAndGet();
        resp.getWriter().write("count: " + current);
    }
}
```

`synchronized`로 `doGet()` 전체를 감싸는 건 동시 처리 성능을 포기하는 것이므로 실무에서는 쓰지 않는다.

---

## Spring DispatcherServlet과의 관계

Spring MVC는 Servlet 위에 구축된 프레임워크다. 그 진입점이 `DispatcherServlet`이다.

### 구조

```
클라이언트 요청
    ↓
Servlet Container (Tomcat)
    ↓
Filter Chain (인코딩, 보안, 로깅 등)
    ↓
DispatcherServlet (url-pattern: "/")
    ↓
HandlerMapping → 어떤 Controller가 처리할지 결정
    ↓
HandlerAdapter → Controller 메서드 호출
    ↓
Controller (@RequestMapping 메서드)
    ↓
ViewResolver → 응답 생성
    ↓
클라이언트 응답
```

`DispatcherServlet`은 `HttpServlet`을 상속한 하나의 Servlet이다. `/`로 매핑되어 있어서 다른 Servlet에 매핑되지 않은 모든 요청을 받는다. 내부에서 URL 패턴, HTTP 메서드 등을 보고 적절한 Controller 메서드에 라우팅한다.

### Spring Boot에서의 자동 설정

Spring Boot는 내장 Tomcat을 사용하고, `DispatcherServlet`을 자동으로 등록한다. `web.xml`이 없어도 되는 이유다.

```java
// Spring Boot가 내부적으로 하는 일 (자동 설정)
@Bean
public DispatcherServlet dispatcherServlet() {
    return new DispatcherServlet();
}

@Bean
public ServletRegistrationBean<DispatcherServlet> dispatcherServletRegistration(
        DispatcherServlet dispatcherServlet) {
    ServletRegistrationBean<DispatcherServlet> registration =
            new ServletRegistrationBean<>(dispatcherServlet, "/");
    registration.setLoadOnStartup(1);
    return registration;
}
```

Spring MVC를 쓰면서 Servlet을 직접 다룰 일은 드물다. 하지만 Filter는 여전히 Servlet Filter 기반이고(`OncePerRequestFilter` 등), `HttpServletRequest`와 `HttpServletResponse`를 Controller 파라미터로 받아서 직접 조작하는 경우도 있다. Servlet의 동작 원리를 이해하면 Spring이 내부에서 무슨 일을 하는지 파악할 수 있다.
