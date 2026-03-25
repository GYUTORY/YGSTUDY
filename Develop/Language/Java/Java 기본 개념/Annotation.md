---
title: "Java Annotation"
tags: [java, annotation, reflection, spring, custom-annotation]
updated: 2026-03-25
---

# Java Annotation

## 어노테이션이란

어노테이션은 코드에 메타데이터를 붙이는 방법이다. 컴파일러가 읽거나, 런타임에 리플렉션으로 읽거나, 컴파일 시점에 코드를 생성하는 데 쓴다.

```java
@Override
public String toString() {
    return "example";
}
```

`@Override`는 컴파일러가 부모 클래스에 해당 메서드가 있는지 확인한다. 없으면 컴파일 에러가 난다. 이게 어노테이션의 가장 기본적인 동작이다.

---

## 어노테이션의 동작 원리

어노테이션 자체는 아무 동작도 하지 않는다. 그냥 마커일 뿐이다. 누군가가 이 마커를 읽고 처리해야 의미가 생�다.

처리하는 주체는 크게 세 가지다.

| 처리 주체 | 시점 | 예시 |
|-----------|------|------|
| 컴파일러 | 컴파일 타임 | `@Override`, `@Deprecated`, `@SuppressWarnings` |
| Annotation Processor | 컴파일 타임 | Lombok `@Getter`, MapStruct `@Mapper` |
| 리플렉션 | 런타임 | Spring `@Autowired`, JPA `@Entity` |

Lombok의 `@Getter`는 런타임에 동작하는 게 아니다. 컴파일 시점에 Annotation Processor가 getter 메서드를 바이트코드에 추가한다. 디컴파일해보면 실제로 `getXxx()` 메서드가 들어가 있다.

Spring의 `@Autowired`는 반대다. 런타임에 Spring 컨테이너가 리플렉션으로 필드를 읽고 빈을 주입한다.

---

## RetentionPolicy — 어노테이션의 생존 범위

어노테이션이 어디까지 살아남는지 결정한다.

```java
@Retention(RetentionPolicy.SOURCE)   // 소스 코드까지만. 컴파일하면 사라진다.
@Retention(RetentionPolicy.CLASS)    // .class 파일까지. 런타임엔 못 읽는다. (기본값)
@Retention(RetentionPolicy.RUNTIME)  // 런타임까지. 리플렉션으로 읽을 수 있다.
```

실무에서 커스텀 어노테이션을 만들 때 `RUNTIME`을 가장 많이 쓴다. Spring이나 직접 만든 프레임워크 코드에서 리플렉션으로 읽어야 하기 때문이다.

`CLASS`가 기본값인데, 직접 쓸 일은 거의 없다. 바이트코드 조작 라이브러리(ByteBuddy 같은)에서 쓴다.

`SOURCE`는 컴파일러 경고 제어(`@SuppressWarnings`) 정도에만 쓰인다.

---

## @Target — 어노테이션을 붙일 수 있는 위치

```java
@Target(ElementType.METHOD)           // 메서드에만
@Target(ElementType.TYPE)             // 클래스, 인터페이스, enum에
@Target(ElementType.FIELD)            // 필드에
@Target(ElementType.PARAMETER)        // 메서드 파라미터에
@Target({ElementType.TYPE, ElementType.METHOD})  // 복수 지정
```

`@Target`을 아예 안 붙이면 어디든 다 붙일 수 있다. 하지만 명시적으로 지정하는 게 맞다. 안 그러면 의도하지 않은 곳에 붙여서 혼란이 생긴다.

---

## 커스텀 어노테이션 만들기

### 기본 구조

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface LogExecutionTime {
}
```

`@interface`가 어노테이션 선언이다. `interface`가 아니라 `@interface`다. 처음에 헷갈리기 쉽다.

### 속성 추가

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface RateLimit {
    int maxRequests() default 100;
    long windowSeconds() default 60;
}
```

```java
@RateLimit(maxRequests = 10, windowSeconds = 30)
public ResponseEntity<?> sendVerification() {
    // ...
}
```

어노테이션 속성의 타입은 제한이 있다. 기본형, String, Class, enum, 다른 어노테이션, 그리고 이들의 배열만 된다. `List`나 `Map` 같은 건 못 쓴다.

### value 속성

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.FIELD)
public @interface Column {
    String value();
}
```

속성 이름이 `value`이면 사용할 때 이름을 생략할 수 있다.

```java
@Column("user_name")   // value = "user_name"
private String userName;
```

속성이 `value` 하나만 있을 때 이 패턴을 쓴다. 속성이 여러 개인데 `value`를 쓰면, 다른 속성도 같이 지정할 때 `value =`를 명시해야 해서 오히려 번거롭다.

---

## 리플렉션으로 어노테이션 읽기

`RUNTIME` 보존 정책이어야 리플렉션으로 읽을 수 있다. `CLASS`나 `SOURCE`는 런타임에 안 보인다.

### 메서드에 붙은 어노테이션 읽기

```java
public class AnnotationReader {

    public static void main(String[] args) throws Exception {
        Method method = OrderService.class.getMethod("createOrder", OrderRequest.class);

        if (method.isAnnotationPresent(RateLimit.class)) {
            RateLimit rateLimit = method.getAnnotation(RateLimit.class);
            System.out.println("maxRequests: " + rateLimit.maxRequests());
            System.out.println("windowSeconds: " + rateLimit.windowSeconds());
        }
    }
}
```

### 클래스의 모든 메서드에서 특정 어노테이션 찾기

```java
for (Method method : clazz.getDeclaredMethods()) {
    LogExecutionTime annotation = method.getAnnotation(LogExecutionTime.class);
    if (annotation != null) {
        // 이 메서드에 @LogExecutionTime이 붙어 있다
    }
}
```

`getAnnotation()`은 해당 어노테이션이 없으면 `null`을 반환한다. `isAnnotationPresent()`로 먼저 확인하든, `null` 체크를 하든 결과는 같다.

### 필드에 붙은 어노테이션 읽기

```java
for (Field field : clazz.getDeclaredFields()) {
    Column column = field.getAnnotation(Column.class);
    if (column != null) {
        String columnName = column.value();
        // columnName으로 SQL 매핑 처리
    }
}
```

`getDeclaredFields()`는 상속받은 필드는 포함하지 않는다. 상속 구조까지 포함하려면 부모 클래스를 순회해야 한다.

---

## @Inherited

```java
@Inherited
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface Auditable {
}

@Auditable
public class BaseEntity { }

public class UserEntity extends BaseEntity { }
// UserEntity에도 @Auditable이 적용된다
```

`@Inherited`가 없으면 자식 클래스에 어노테이션이 전파되지 않는다. 클래스에만 동작하고, 메서드 오버라이딩에는 적용되지 않는다.

---

## Spring에서 커스텀 어노테이션 활용

### AOP와 조합 — 실행 시간 로깅

실무에서 가장 흔한 패턴이다.

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface LogExecutionTime {
    String description() default "";
}
```

```java
@Aspect
@Component
public class LogExecutionTimeAspect {

    private static final Logger log = LoggerFactory.getLogger(LogExecutionTimeAspect.class);

    @Around("@annotation(logExecutionTime)")
    public Object logTime(ProceedingJoinPoint joinPoint, LogExecutionTime logExecutionTime) throws Throwable {
        long start = System.currentTimeMillis();

        try {
            return joinPoint.proceed();
        } finally {
            long elapsed = System.currentTimeMillis() - start;
            String desc = logExecutionTime.description().isEmpty()
                    ? joinPoint.getSignature().toShortString()
                    : logExecutionTime.description();
            log.info("{} 실행 시간: {}ms", desc, elapsed);
        }
    }
}
```

```java
@Service
public class OrderService {

    @LogExecutionTime(description = "주문 생성")
    public Order createOrder(OrderRequest request) {
        // 주문 처리 로직
    }
}
```

`@Around("@annotation(logExecutionTime)")`에서 소문자로 시작하는 `logExecutionTime`은 메서드 파라미터 이름과 일치해야 한다. 이걸 틀리면 Spring이 바인딩을 못 해서 에러가 난다.

### 메타 어노테이션으로 Spring 어노테이션 조합

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Service
@Transactional(readOnly = true)
public @interface ReadOnlyService {
}
```

```java
@ReadOnlyService
public class ProductQueryService {
    // @Service + @Transactional(readOnly = true)가 같이 적용된다
    public Product findById(Long id) {
        return productRepository.findById(id).orElseThrow();
    }
}
```

Spring은 메타 어노테이션을 재귀적으로 탐색한다. `@ReadOnlyService`에 `@Service`가 붙어 있으면, Spring이 이 클래스를 빈으로 등록한다. `@SpringBootApplication`도 이 원리다. 안에 `@Configuration`, `@EnableAutoConfiguration`, `@ComponentScan`이 들어 있다.

### HandlerMethodArgumentResolver와 조합 — 커스텀 파라미터 바인딩

컨트롤러 메서드 파라미터에 현재 로그인 사용자를 주입하는 패턴이다.

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.PARAMETER)
public @interface CurrentUser {
}
```

```java
@Component
public class CurrentUserArgumentResolver implements HandlerMethodArgumentResolver {

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return parameter.hasParameterAnnotation(CurrentUser.class)
                && parameter.getParameterType().equals(User.class);
    }

    @Override
    public Object resolveArgument(MethodParameter parameter,
                                  ModelAndViewContainer mavContainer,
                                  NativeWebRequest webRequest,
                                  WebDataBinderFactory binderFactory) {
        HttpServletRequest request = webRequest.getNativeRequest(HttpServletRequest.class);
        String token = request.getHeader("Authorization");
        // 토큰에서 사용자 정보 추출
        return userService.findByToken(token);
    }
}
```

```java
@GetMapping("/me")
public ResponseEntity<UserResponse> getMyInfo(@CurrentUser User user) {
    return ResponseEntity.ok(UserResponse.from(user));
}
```

`WebMvcConfigurer`에 resolver를 등록하는 걸 빠뜨리면 동작하지 않는다.

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final CurrentUserArgumentResolver currentUserArgumentResolver;

    public WebConfig(CurrentUserArgumentResolver currentUserArgumentResolver) {
        this.currentUserArgumentResolver = currentUserArgumentResolver;
    }

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(currentUserArgumentResolver);
    }
}
```

---

## 자주 겪는 실수

**RetentionPolicy를 안 붙이면 기본값이 CLASS다.** 리플렉션으로 읽으려고 만든 어노테이션인데 `@Retention(RUNTIME)`을 빠뜨리면 런타임에 `null`이 나온다. 디버깅이 까다로운데, 어노테이션이 분명히 붙어 있는데 왜 안 읽히는지 감이 안 오기 때문이다.

**AOP 어노테이션은 프록시 기반이라 self-invocation에서 안 먹힌다.** 같은 클래스 안에서 `this.method()`로 호출하면 프록시를 안 타서 어노테이션 처리가 안 된다. Spring AOP의 고질적인 문제다.

```java
@Service
public class OrderService {

    public void process() {
        this.createOrder();  // @LogExecutionTime이 동작하지 않는다
    }

    @LogExecutionTime
    public Order createOrder() { ... }
}
```

**Annotation Processor 기반 어노테이션과 리플렉션 기반 어노테이션을 혼동하지 말 것.** Lombok의 `@Getter`는 컴파일 타임에 코드를 생성한다. 런타임에 리플렉션으로 `@Getter`를 읽어서 뭔가 하려는 코드를 짜면, `@Getter`의 RetentionPolicy가 `SOURCE`라서 아무것도 안 읽힌다.
