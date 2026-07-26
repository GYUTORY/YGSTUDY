---
title: SLF4J (Simple Logging Facade for Java)
tags: [framework, java, spring, slf4j, logging, logback, log4j2, mdc]
updated: 2026-07-26
---

# SLF4J (Simple Logging Facade for Java)

## SLF4J가 필요한 이유

로깅 라이브러리는 java.util.logging, Log4j, Logback, Log4j2 등 여러 종류가 있다. 라이브러리를 직접 사용하면 나중에 구현체를 바꿔야 할 때 호출 코드를 전부 수정해야 한다.

SLF4J는 이 문제를 해결하는 퍼사드(facade)다. 코드는 SLF4J API만 참조하고, 실제 로그 처리는 바인딩된 구현체(Logback, Log4j2 등)가 담당한다. 구현체를 교체해도 비즈니스 코드는 손댈 필요가 없다.

Spring Boot는 `spring-boot-starter`에 `slf4j-api` + `logback-classic`을 기본으로 포함한다. 별도 의존성 없이 바로 쓸 수 있다.

### 바인딩 방식

SLF4J 1.x는 클래스패스에서 `StaticLoggerBinder`를 검색한다. 여러 구현체가 동시에 클래스패스에 있으면 어떤 것이 선택될지 예측할 수 없다. SLF4J 2.x는 Java ServiceLoader로 전환됐다. `META-INF/services/org.slf4j.spi.SLF4JServiceProvider` 파일을 통해 구현체를 명시한다.

구현체가 두 개 이상 클래스패스에 올라가면 아래 경고가 출력된다.

```
SLF4J: Class path contains multiple SLF4J providers.
SLF4J: Found provider [ch.qos.logback.classic.spi.LogbackServiceProvider@...]
SLF4J: Found provider [org.apache.logging.slf4j.SLF4JServiceProvider@...]
```

이 경우 `./gradlew dependencies | grep 'slf4j\|logback\|log4j'`로 의존성 트리를 확인하고 불필요한 구현체를 exclude해야 한다.

## Logger 선언 방식

```java
// 명시적 선언
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);
}
```

```java
// Lombok @Slf4j
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class OrderService {
    // 컴파일 타임에 위와 동일한 코드가 생성됨
}
```

`static final`로 선언하는 이유가 있다. Logger는 클래스당 하나면 충분하고, 인스턴스마다 생성할 이유가 없다. Logger는 Serializable을 구현하지 않아서 인스턴스 변수로 선언하면 직렬화 시 문제가 생긴다.

`getLogger(OrderService.class)` 대신 `getLogger("com.example.order")`처럼 문자열로 이름을 줄 수도 있지만, 클래스 기반이 리팩토링에 안전하다. 문자열 방식은 패키지 경로로 로그 레벨을 세밀하게 조정하는 기능과도 맞추기 까다롭다.

## 로그 레벨 사용 기준

레벨 순서는 `TRACE < DEBUG < INFO < WARN < ERROR`다. 설정된 레벨 이상의 로그만 출력된다.

**TRACE**: 메서드 진입/종료, 루프 내부 상태처럼 극도로 상세한 정보. 운영에서 켜면 로그 양이 폭발적으로 늘어난다. 하루에 수십 GB가 쌓이는 경우도 있어서 사실상 켜지 않는다.

**DEBUG**: 개발 중 유용한 정보. 요청 파라미터, 중간 계산값, 쿼리 파라미터 등. 장애 대응 시 임시로 켜고 끝나면 바로 되돌린다. DEBUG를 켜놓은 채 방치하면 디스크가 빠르게 찬다.

**INFO**: 정상 흐름에서 기록할 만한 이벤트. 요청 처리 시작/완료, 중요 비즈니스 이벤트, 배치 시작/종료. INFO가 너무 촘촘하면 정작 중요한 로그가 묻힌다.

**WARN**: 비정상이지만 서비스는 계속 동작하는 상황. 재시도 발생, 설정값 부재로 기본값 사용, deprecated API 호출, 응답 지연 임계치 초과 등.

**ERROR**: 처리 실패로 서비스에 영향이 생기는 상황. 예외를 잡아서 fallback 처리하더라도 나중에 추적해야 하는 경우는 ERROR로 남긴다.

흔한 실수는 모든 예외를 ERROR로 처리하는 것이다. 사용자 입력 오류(400), 인증 실패(401), 리소스 없음(404)는 WARN이 적절하다. ERROR가 너무 많으면 실제 장애 로그를 놓치게 된다.

## 파라미터 치환과 문자열 연결

SLF4J의 `{}` 플레이스홀더는 단순한 편의 문법이 아니다.

```java
// 문자열 연결 - 로그 레벨에 관계없이 항상 문자열 생성
log.debug("주문 정보: " + order.toString());

// 파라미터 치환 - 출력이 필요한 경우에만 toString() 호출
log.debug("주문 정보: {}", order);
```

첫 번째 방식은 현재 레벨이 INFO여서 DEBUG 로그가 출력되지 않더라도 문자열 연결 연산은 항상 실행된다. `order.toString()`이 무거운 작업이거나 루프 안에서 반복된다면 불필요한 연산이 쌓인다.

`{}` 방식에서는 SLF4J가 먼저 레벨을 확인하고, 출력이 필요한 경우에만 `toString()`을 호출한다. 다만 파라미터 자체의 평가는 막지 못한다.

```java
// expensiveMethod()는 레벨에 관계없이 항상 호출된다
log.debug("결과: {}", expensiveMethod());

// 완전히 막으려면 isDebugEnabled()로 감싸야 한다
if (log.isDebugEnabled()) {
    log.debug("결과: {}", expensiveMethod());
}
```

예외 로깅에도 주의가 필요하다.

```java
// 올바른 방법 - 마지막 인수로 Throwable 전달하면 스택 트레이스가 출력됨
log.error("결제 실패: userId={}", userId, e);

// 잘못된 방법 - 어느 라인에서 발생했는지 알 수 없음
log.error("결제 실패: userId={}, error={}", userId, e.getMessage());
```

SLF4J는 마지막 파라미터가 `Throwable`이면 자동으로 스택 트레이스를 출력한다. `e.getMessage()`만 넣으면 메시지는 보이지만 원인을 추적할 수 없다.

## Spring Boot 자동 설정 흐름

Spring Boot는 로깅 초기화를 ApplicationContext 생성 전에 처리한다. `@Bean`이나 `@Configuration`보다 먼저 로깅 시스템이 세팅된다는 뜻이다.

초기화 순서는 다음과 같다.

1. `spring-boot-starter-logging`의 `LoggingSystem`이 로드됨
2. 클래스패스에서 Logback 또는 Log4j2 구현체 탐색
3. 구현체별 설정 파일 탐색 순서 적용
    - Logback: `logback-spring.xml` → `logback.xml`
    - Log4j2: `log4j2-spring.xml` → `log4j2.xml`
4. 설정 파일이 없으면 Spring Boot 기본 설정 적용
5. `application.yml`의 `logging.*` 프로퍼티 추가 반영

`logback-spring.xml`을 쓰는 이유는 Spring Boot 전용 `<springProfile>` 태그와 `${}` 프로퍼티 치환을 사용할 수 있어서다. `logback.xml`은 순수 Logback 파일이라 이 기능이 없다.

`application.yml`에서 기본 설정:

```yaml
logging:
  level:
    root: INFO
    com.example: DEBUG
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql: TRACE  # SQL 바인딩 파라미터 출력
  pattern:
    console: "%d{HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"
  file:
    name: logs/app.log
  logback:
    rollingpolicy:
      max-file-size: 100MB
      max-history: 30
      total-size-cap: 3GB
```

`logging.file.name`만 설정해도 파일 출력이 활성화된다. 복잡한 롤링 정책이나 프로파일별 appender 분리가 필요하면 `logback-spring.xml`을 직접 작성해야 한다.

## MDC 실사용 패턴

MDC(Mapped Diagnostic Context)는 ThreadLocal에 키-값 쌍을 저장하고, 로그 패턴에서 `%X{key}` 형태로 꺼내 쓰는 기능이다. 주로 HTTP 요청마다 고유 ID를 부여해서 모든 로그에 자동으로 포함시키는 데 쓴다.

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MdcFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;

        // 게이트웨이에서 이미 traceId를 넣어줬으면 그걸 그대로 이어받는다
        String traceId = Optional.ofNullable(httpRequest.getHeader("X-Trace-Id"))
                .filter(s -> !s.isBlank())
                .orElse(UUID.randomUUID().toString().replace("-", "").substring(0, 8));

        MDC.put("traceId", traceId);
        ((HttpServletResponse) response).setHeader("X-Trace-Id", traceId);

        try {
            chain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }
}
```

로그 패턴에 `%X{traceId}`를 넣어두면 이 필터를 거치는 모든 요청의 로그에 traceId가 자동으로 찍힌다.

```
2026-07-26 15:23:01 [http-nio-8080-exec-3] [a3f2b1c9] INFO  OrderService - 주문 생성: orderId=5678
2026-07-26 15:23:01 [http-nio-8080-exec-3] [a3f2b1c9] INFO  PaymentService - 결제 요청: amount=50000
2026-07-26 15:23:02 [http-nio-8080-exec-3] [a3f2b1c9] ERROR PaymentService - 결제 실패: PG 응답 없음
```

`grep a3f2b1c9 app.log`만으로 해당 요청의 전체 흐름을 볼 수 있다. 수십만 줄의 로그에서 특정 요청을 추적할 때 차이가 크다.

## 멀티스레드 환경에서 MDC 누수

MDC가 ThreadLocal 기반이라는 점에서 두 가지 문제가 생긴다.

### 스레드 풀 재사용 시 잔류값

서블릿 컨테이너는 스레드 풀을 쓴다. 요청 처리 후 `MDC.clear()`를 호출하지 않으면 스레드가 재사용될 때 이전 요청의 traceId가 남아 있는 채로 다음 요청 로그에 찍힌다.

```java
// 예외가 발생해도 반드시 clear되도록 finally 블록에 위치시켜야 한다
try {
    MDC.put("traceId", traceId);
    chain.doFilter(request, response);
} finally {
    MDC.clear(); // 이 줄이 없으면 누수 발생
}
```

기존에 MDC 값이 있던 경우를 고려해서 복원 패턴을 쓰기도 한다.

```java
Map<String, String> previousContext = MDC.getCopyOfContextMap();
try {
    MDC.clear();
    MDC.put("traceId", traceId);
    chain.doFilter(request, response);
} finally {
    MDC.clear();
    if (previousContext != null) {
        MDC.setContextMap(previousContext);
    }
}
```

### 비동기 처리에서 MDC 미전파

`@Async`, `CompletableFuture`, `ExecutorService`를 쓰면 새로운 스레드가 생성된다. 새 스레드에는 부모 스레드의 MDC가 없다.

```java
@Async
public void sendNotification(Long userId) {
    // 이 시점 MDC는 비어있다. traceId가 null로 찍힌다
    log.info("알림 발송: userId={}", userId);
}
```

`TaskDecorator`를 사용하면 부모 스레드의 MDC 스냅샷을 자식 스레드로 복사할 수 있다.

```java
public class MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // decorate() 호출 시점(부모 스레드)의 MDC 값을 캡처한다
        Map<String, String> contextMap = MDC.getCopyOfContextMap();
        return () -> {
            try {
                if (contextMap != null) {
                    MDC.setContextMap(contextMap);
                }
                runnable.run();
            } finally {
                MDC.clear();
            }
        };
    }
}
```

```java
@Configuration
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(20);
        executor.setQueueCapacity(100);
        executor.setTaskDecorator(new MdcTaskDecorator());
        executor.initialize();
        return executor;
    }
}
```

복사되는 값은 `decorate()` 호출 시점의 스냅샷이다. 자식 스레드에서 MDC를 수정해도 부모 스레드에 영향을 주지 않는다. `CompletableFuture.runAsync()`를 직접 쓰는 경우에는 이 decorator가 적용되지 않아서 별도로 처리해야 한다.

## 바인딩 구현체 설정

### Logback

Spring Boot 기본 구현체다. `spring-boot-starter`에 포함되어 있어 추가 의존성이 필요 없다.

```xml
<!-- logback-spring.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="LOG_PATH" value="${LOG_DIR:-./logs}"/>
    <property name="LOG_PATTERN"
              value="%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"/>

    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>${LOG_PATH}/app.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>${LOG_PATH}/app.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxFileSize>100MB</maxFileSize>
            <maxHistory>30</maxHistory>
            <totalSizeCap>3GB</totalSizeCap>
        </rollingPolicy>
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <springProfile name="local">
        <root level="DEBUG">
            <appender-ref ref="CONSOLE"/>
        </root>
    </springProfile>

    <springProfile name="prod">
        <root level="INFO">
            <appender-ref ref="FILE"/>
        </root>
        <logger name="org.hibernate.SQL" level="OFF"/>
        <logger name="org.springframework.web" level="WARN"/>
    </springProfile>
</configuration>
```

`totalSizeCap`을 설정하지 않으면 `maxHistory`로 파일 개수는 제한되지만, 파일이 클 경우 디스크가 차도 롤링이 지워주지 않는다. 운영 환경에서는 반드시 설정한다.

`LOG_PATH`에 `${LOG_DIR:-./logs}` 패턴을 쓰면 환경변수 `LOG_DIR`이 있으면 그 값을, 없으면 `./logs`를 사용한다. 컨테이너 환경에서 절대경로를 하드코딩하면 볼륨 마운트 설정과 충돌하는 경우가 있어서 이 방식이 낫다.

### Log4j2로 전환

비동기 로깅 처리량이 Logback보다 높아야 하는 경우 Log4j2를 쓴다. LMAX Disruptor 기반 AsyncLogger는 lock-free 구조여서 고트래픽 환경에서 유리하다.

```groovy
// build.gradle
dependencies {
    implementation('org.springframework.boot:spring-boot-starter') {
        exclude group: 'org.springframework.boot', module: 'spring-boot-starter-logging'
    }
    implementation 'org.springframework.boot:spring-boot-starter-log4j2'
}
```

`spring-boot-starter-logging`을 명시적으로 exclude하지 않으면 Logback과 Log4j2가 동시에 클래스패스에 올라간다. SLF4J 경고가 출력되고, 어떤 구현체가 실제로 바인딩됐는지 확인해야 하는 상황이 된다.

설정 파일은 `log4j2-spring.xml`로 만든다. `log4j2.xml`을 쓰면 `<springProfile>` 태그를 사용할 수 없다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN" shutdownHook="disable">
    <!-- shutdownHook="disable": Spring Boot의 shutdown lifecycle에 로그 정리를 위임 -->
    <Properties>
        <Property name="LOG_PATTERN">
            %d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n
        </Property>
    </Properties>

    <Appenders>
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="${LOG_PATTERN}"/>
        </Console>

        <RollingFile name="File" fileName="./logs/app.log"
                     filePattern="./logs/app.%d{yyyy-MM-dd}.%i.log.gz">
            <PatternLayout pattern="${LOG_PATTERN}"/>
            <Policies>
                <TimeBasedTriggeringPolicy/>
                <SizeBasedTriggeringPolicy size="100MB"/>
            </Policies>
            <DefaultRolloverStrategy max="30"/>
        </RollingFile>
    </Appenders>

    <Loggers>
        <AsyncLogger name="com.example" level="INFO" additivity="false">
            <AppenderRef ref="File"/>
        </AsyncLogger>
        <Root level="INFO">
            <AppenderRef ref="Console"/>
            <AppenderRef ref="File"/>
        </Root>
    </Loggers>
</Configuration>
```

비동기 로깅에서 애플리케이션이 비정상 종료되면 큐에 남아있던 로그가 유실된다. Spring Boot 2.x 이상에서는 Log4j2의 shutdownHook을 `disable`로 설정하고 Spring의 shutdown 과정에서 정리하도록 맡기는 게 맞다. 그래야 bean들을 정리하는 도중에도 로그가 정상적으로 출력된다.
