---
title: Java - Proxy Pattern (프록시 패턴)
tags: [language, java, design-pattern, proxy, dynamic-proxy, CGLIB, spring-aop]
updated: 2026-07-19
---

# Java - Proxy Pattern (프록시 패턴)
## 프록시 패턴이란

프록시 패턴은 실제 객체 앞에 대리 객체를 두어 호출을 가로채는 구조다. 클라이언트는 프록시를 실제 객체라고 믿고 호출하고, 프록시는 전처리·후처리를 끼워 넣은 뒤 실제 객체에 위임한다.

이 패턴이 쓰이는 상황은 대부분 세 가지다. 접근 제어(인증·권한 체크), 부가 기능 추가(로깅·트랜잭션·캐싱), 지연 초기화(비용이 큰 객체를 처음 사용 시점까지 생성 미루기). Spring AOP가 내부적으로 프록시를 생성해 트랜잭션이나 캐싱을 처리하는 것도 같은 원리다.

Java에서 프록시를 구현하는 방법은 크게 세 가지다. 인터페이스를 직접 구현하는 정적 프록시, `java.lang.reflect.Proxy`를 쓰는 동적 프록시, 그리고 CGLIB으로 서브클래스를 생성하는 방법이다.

---

## 정적 프록시

인터페이스를 직접 구현해서 만드는 가장 단순한 방식이다.

```java
public interface OrderService {
    Order createOrder(Long userId, Long itemId);
    Order findOrder(Long orderId);
}

public class OrderServiceImpl implements OrderService {
    @Override
    public Order createOrder(Long userId, Long itemId) {
        // 실제 주문 생성 로직
        return new Order(userId, itemId);
    }

    @Override
    public Order findOrder(Long orderId) {
        return orderRepository.findById(orderId);
    }
}

public class OrderServiceLoggingProxy implements OrderService {
    private final OrderService target;

    public OrderServiceLoggingProxy(OrderService target) {
        this.target = target;
    }

    @Override
    public Order createOrder(Long userId, Long itemId) {
        long start = System.currentTimeMillis();
        try {
            Order order = target.createOrder(userId, itemId);
            long elapsed = System.currentTimeMillis() - start;
            log.info("createOrder userId={} itemId={} elapsed={}ms", userId, itemId, elapsed);
            return order;
        } catch (Exception e) {
            log.error("createOrder failed userId={} itemId={}", userId, itemId, e);
            throw e;
        }
    }

    @Override
    public Order findOrder(Long orderId) {
        return target.findOrder(orderId);
    }
}
```

사용할 때는 실제 구현체를 프록시로 감싸서 주입한다.

```java
OrderService proxy = new OrderServiceLoggingProxy(new OrderServiceImpl());
```

정적 프록시의 단점은 인터페이스 메서드가 늘어날 때마다 프록시에도 같은 메서드를 추가해야 한다는 점이다. `OrderService`에 메서드가 10개라면 프록시에도 10개를 전부 작성해야 한다. 부가 기능은 `createOrder` 하나에만 필요한데 나머지 9개는 단순 위임 코드만 있는 구조가 된다. 서비스가 많아지면 프록시 클래스 수가 그만큼 늘어난다.

---

## 동적 프록시 (java.lang.reflect.Proxy)

JDK가 런타임에 프록시 클래스를 생성하는 방식이다. `InvocationHandler`를 구현하면 모든 메서드 호출이 `invoke` 하나로 들어온다.

```java
public class LoggingInvocationHandler implements InvocationHandler {
    private final Object target;

    public LoggingInvocationHandler(Object target) {
        this.target = target;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            Object result = method.invoke(target, args);
            long elapsed = System.currentTimeMillis() - start;
            log.info("method={} elapsed={}ms", method.getName(), elapsed);
            return result;
        } catch (InvocationTargetException e) {
            // method.invoke는 실제 예외를 InvocationTargetException으로 감싼다
            throw e.getCause();
        }
    }
}

// 프록시 생성
OrderService proxy = (OrderService) Proxy.newProxyInstance(
    OrderService.class.getClassLoader(),
    new Class[]{OrderService.class},
    new LoggingInvocationHandler(new OrderServiceImpl())
);
```

`InvocationHandler` 하나로 모든 메서드를 처리하므로 메서드가 늘어도 핸들러를 수정할 필요가 없다. 같은 핸들러를 `PaymentService`, `UserService` 등 다른 인터페이스에도 재사용할 수 있다.

### 인터페이스 필수 제약

JDK 동적 프록시는 인터페이스 기반으로만 동작한다. 인터페이스 없이 구체 클래스만 있는 경우에는 사용할 수 없다.

```java
// 이렇게 하면 예외 발생
public class ConcreteService {
    public void doSomething() {}
}

// Proxy.newProxyInstance에 인터페이스 없이 구체 클래스 넘기면 IllegalArgumentException
Object proxy = Proxy.newProxyInstance(
    ConcreteService.class.getClassLoader(),
    new Class[]{ConcreteService.class}, // ConcreteService는 인터페이스가 아니므로 실패
    handler
);
```

Spring은 이 제약을 피하기 위해 인터페이스가 있을 때는 JDK 동적 프록시를, 없을 때는 CGLIB을 선택한다.

### InvocationTargetException 처리 주의

`method.invoke()`는 실제 메서드에서 던진 예외를 `InvocationTargetException`으로 감싸서 던진다. 핸들러에서 `e.getCause()`를 꺼내지 않으면 호출 측에서 전혀 다른 예외 타입을 받게 된다. 로그 출력이나 예외 변환 로직이 있는 핸들러에서 이 부분을 빠뜨리는 실수가 많다.

---

## CGLIB 기반 프록시

CGLIB(Code Generation Library)은 바이트코드를 조작해 대상 클래스의 서브클래스를 동적으로 생성한다. 인터페이스 없이도 구체 클래스에 프록시를 적용할 수 있다.

```java
// 인터페이스 없는 구체 클래스
public class ProductService {
    public Product findProduct(Long id) {
        return productRepository.findById(id);
    }

    public void updatePrice(Long id, BigDecimal price) {
        productRepository.updatePrice(id, price);
    }
}

// CGLIB 프록시 생성
Enhancer enhancer = new Enhancer();
enhancer.setSuperclass(ProductService.class);
enhancer.setCallback(new MethodInterceptor() {
    @Override
    public Object intercept(Object obj, Method method, Object[] args, MethodProxy methodProxy) throws Throwable {
        log.info("before method={}", method.getName());
        // methodProxy.invokeSuper()로 실제 메서드 호출
        Object result = methodProxy.invokeSuper(obj, args);
        log.info("after method={}", method.getName());
        return result;
    }
});

ProductService proxy = (ProductService) enhancer.create();
```

`methodProxy.invokeSuper()`를 써야 한다는 점이 JDK 동적 프록시와 다르다. `method.invoke(obj, args)`를 쓰면 프록시 자신을 대상으로 재귀 호출이 발생해 스택 오버플로우가 난다.

### final 클래스·메서드 제약

CGLIB은 서브클래스를 만드는 방식이므로 `final`로 선언된 클래스나 메서드에는 프록시를 적용할 수 없다.

```java
public final class PaymentService {  // final 클래스
    public void pay() {}
}

// CGLIB이 서브클래스를 만들 수 없어 예외 발생
// Cannot subclass final class ...
```

메서드 단위도 마찬가지다. `final`로 선언한 메서드는 서브클래스에서 오버라이드할 수 없으므로 CGLIB 프록시가 해당 메서드를 가로챌 수 없다.

Spring에서 `@Transactional`을 붙인 클래스나 메서드를 `final`로 선언했을 때 트랜잭션이 적용되지 않는 문제가 여기서 나온다. 컴파일 오류가 아니고 런타임에서도 예외 없이 그냥 트랜잭션 없이 실행되는 경우도 있어서 찾기 어렵다.

### Spring AOP와 CGLIB

Spring Boot 2.0부터 기본 AOP 프록시 방식이 JDK 동적 프록시에서 CGLIB으로 바뀌었다. `spring.aop.proxy-target-class=false`로 변경하면 JDK 동적 프록시로 돌아가지만, 그러면 인터페이스 없는 빈에 AOP가 적용되지 않는 문제가 생긴다.

---

## 세 방식 비교

| | 정적 프록시 | JDK 동적 프록시 | CGLIB |
|---|---|---|---|
| 대상 | 인터페이스 | 인터페이스 | 구체 클래스 |
| 생성 시점 | 컴파일 타임 | 런타임 | 런타임 |
| 코드 양 | 메서드마다 작성 | 핸들러 하나로 처리 | 인터셉터 하나로 처리 |
| final 제약 | 없음 | 없음 | 있음 |
| 성능 | 빠름 | 리플렉션 오버헤드 | 리플렉션보다 빠름 |

새로운 서비스를 만들 때 로깅이나 권한 체크를 직접 붙여야 한다면 정적 프록시가 가장 직관적이다. 프록시 대상이 여러 클래스에 걸쳐 있고 코드 중복이 문제라면 JDK 동적 프록시나 CGLIB을 고려한다. Spring AOP를 쓰면 이 선택을 프레임워크가 대신 해준다.

---

## 실무에서 자주 만나는 문제

### this 호출 시 AOP 미적용

Spring AOP에서 가장 많이 마주치는 문제다. 같은 클래스 안에서 `this.method()`로 호출하면 프록시를 거치지 않아 AOP 어드바이스가 적용되지 않는다.

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder(Long userId) {
        // 재고 확인 후 결제
        validateStock(userId);
        pay(userId);
        // 내부에서 this.sendNotification()을 호출하면
        // 트랜잭션 없이 실행됨
        this.sendNotification(userId);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(Long userId) {
        // createOrder에서 this.sendNotification()으로 호출하면
        // REQUIRES_NEW가 동작하지 않는다
        notificationService.send(userId);
    }
}
```

`createOrder`에서 `this.sendNotification()`을 호출하면 프록시가 아닌 실제 객체의 메서드가 바로 실행된다. `REQUIRES_NEW`로 별도 트랜잭션을 열어야 하는 상황인데 같은 트랜잭션 안에서 실행되는 것이다.

해결 방법은 두 가지다. 하나는 `sendNotification`을 별도 빈으로 분리하는 것이다.

```java
@Service
public class NotificationService {
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(Long userId) {
        // 이제 별도 빈이므로 프록시를 거쳐 호출된다
    }
}

@Service
@RequiredArgsConstructor
public class OrderService {
    private final NotificationService notificationService;

    @Transactional
    public void createOrder(Long userId) {
        // ...
        notificationService.sendNotification(userId);  // 프록시를 거친다
    }
}
```

다른 방법은 `ApplicationContext`나 `AopContext`에서 현재 프록시를 꺼내서 호출하는 것이다.

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder(Long userId) {
        // ...
        // AopContext.currentProxy()로 프록시 참조를 얻어서 호출
        ((OrderService) AopContext.currentProxy()).sendNotification(userId);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(Long userId) {
        notificationService.send(userId);
    }
}
```

`AopContext.currentProxy()`를 쓰려면 `@EnableAspectJAutoProxy(exposeProxy = true)`를 설정에 추가해야 한다. 코드가 지저분해지므로 별도 빈으로 분리하는 것이 더 낫다.

### 트랜잭션 프록시와 예외 처리

`@Transactional`이 붙은 메서드에서 예외를 catch해서 삼키면 트랜잭션이 롤백되지 않는다. 프록시가 예외를 받아야 롤백을 결정하는데, 메서드 안에서 잡아버리면 프록시까지 예외가 전달되지 않기 때문이다.

```java
@Transactional
public void processOrder(Long orderId) {
    try {
        orderRepository.save(order);
        paymentService.pay(order);
    } catch (PaymentException e) {
        log.error("payment failed", e);
        // 예외를 삼키면 트랜잭션은 커밋된다
        // order는 저장되고 결제는 실패한 상태로 남는다
    }
}
```

롤백을 원한다면 예외를 다시 던지거나 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`를 호출해야 한다.
