---
title: Spring Boot 로깅 실무
tags: [Spring Boot, Logback, Log4j2, MDC, 로깅, 모니터링]
updated: 2026-03-29
---

# Spring Boot 로깅 실무

## 1. Spring Boot 기본 로깅 구조

Spring Boot는 SLF4J + Logback 조합을 기본으로 사용한다. `spring-boot-starter`에 이미 포함되어 있어 별도 의존성 추가 없이 바로 쓸 수 있다.

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    public void createOrder(OrderRequest request) {
        log.info("주문 생성 요청: userId={}, itemCount={}", request.getUserId(), request.getItems().size());
        // ...
    }
}
```

Lombok의 `@Slf4j`를 쓰면 `log` 변수 선언을 생략할 수 있다. 다만 팀 컨벤션에 따라 명시적 선언을 선호하는 곳도 있으니 확인이 필요하다.

로그 레벨은 `TRACE < DEBUG < INFO < WARN < ERROR` 순서다. 운영 환경에서는 보통 INFO 이상만 출력하고, 장애 대응 시 DEBUG로 임시 변경하는 패턴이 일반적이다.


## 2. Logback 설정: logback-spring.xml 프로파일별 분리

`application.yml`에서 간단한 설정은 가능하지만, 운영 환경에서는 `logback-spring.xml`을 직접 작성해야 하는 경우가 대부분이다. 파일 롤링 정책, 패턴 커스터마이징, 프로파일별 분리 등은 XML 설정이 필수다.

`logback-spring.xml`은 Spring Boot 전용 파일명이다. `logback.xml`과 달리 `<springProfile>` 태그를 사용할 수 있다. `logback.xml`을 쓰면 Spring 프로파일 기반 분기가 안 되니 반드시 `logback-spring.xml`로 만들어야 한다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <!-- 공통 변수 -->
    <property name="LOG_PATH" value="./logs"/>
    <property name="LOG_PATTERN" value="%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"/>

    <!-- 콘솔 출력: 전 환경 공통 -->
    <appender name="CONSOLE" class="ch.qos.logback.classic.encoder.PatternLayoutEncoder">
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <!-- 파일 출력: 일별 롤링 -->
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>${LOG_PATH}/application.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>${LOG_PATH}/application.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxFileSize>100MB</maxFileSize>
            <maxHistory>30</maxHistory>
            <totalSizeCap>3GB</totalSizeCap>
        </rollingPolicy>
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <!-- ERROR 전용 파일: 장애 대응 시 이 파일만 보면 된다 -->
    <appender name="ERROR_FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>${LOG_PATH}/error.log</file>
        <filter class="ch.qos.logback.classic.filter.LevelFilter">
            <level>ERROR</level>
            <onMatch>ACCEPT</onMatch>
            <onMismatch>DENY</onMismatch>
        </filter>
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>${LOG_PATH}/error.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxFileSize>50MB</maxFileSize>
            <maxHistory>90</maxHistory>
        </rollingPolicy>
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <!-- 로컬 환경: 콘솔만, DEBUG 레벨 -->
    <springProfile name="local">
        <root level="DEBUG">
            <appender-ref ref="CONSOLE"/>
        </root>
    </springProfile>

    <!-- 개발 환경 -->
    <springProfile name="dev">
        <root level="DEBUG">
            <appender-ref ref="CONSOLE"/>
            <appender-ref ref="FILE"/>
        </root>
    </springProfile>

    <!-- 운영 환경 -->
    <springProfile name="prod">
        <root level="INFO">
            <appender-ref ref="FILE"/>
            <appender-ref ref="ERROR_FILE"/>
        </root>
        <!-- SQL 로그는 운영에서 끈다. 트래픽 많으면 디스크가 빠르게 찬다 -->
        <logger name="org.hibernate.SQL" level="OFF"/>
    </springProfile>
</configuration>
```

### 실무에서 자주 하는 실수

**`totalSizeCap` 미설정**: `maxHistory`만 걸어두면 파일 개수는 제한되지만, 각 파일이 큰 경우 디스크를 다 채울 수 있다. `totalSizeCap`을 반드시 설정한다.

**로그 파일 경로를 절대경로로 하드코딩**: 컨테이너 환경에서는 `/var/log/app` 같은 절대경로를 쓰면 볼륨 마운트 설정과 꼬인다. 환경변수로 주입받는 게 낫다.

```xml
<property name="LOG_PATH" value="${LOG_DIR:-./logs}"/>
```

이렇게 하면 환경변수 `LOG_DIR`이 있으면 그 값을, 없으면 `./logs`를 사용한다.


## 3. Log4j2로 전환하기

Logback 대신 Log4j2를 써야 하는 경우가 있다. 비동기 로깅 성능이 Log4j2가 확실히 낫고, LMAX Disruptor 기반 AsyncLogger가 필요하면 Log4j2가 맞다.

```xml
<!-- build.gradle -->
dependencies {
    implementation('org.springframework.boot:spring-boot-starter') {
        exclude group: 'org.springframework.boot', module: 'spring-boot-starter-logging'
    }
    implementation 'org.springframework.boot:spring-boot-starter-log4j2'
}
```

설정 파일은 `log4j2-spring.xml`로 만든다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
    <Properties>
        <Property name="LOG_PATTERN">%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n</Property>
    </Properties>

    <Appenders>
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="${LOG_PATTERN}"/>
        </Console>

        <RollingFile name="File" fileName="./logs/application.log"
                     filePattern="./logs/application.%d{yyyy-MM-dd}.%i.log.gz">
            <PatternLayout pattern="${LOG_PATTERN}"/>
            <Policies>
                <TimeBasedTriggeringPolicy/>
                <SizeBasedTriggeringPolicy size="100MB"/>
            </Policies>
            <DefaultRolloverStrategy max="30"/>
        </RollingFile>
    </Appenders>

    <Loggers>
        <Root level="INFO">
            <AppenderRef ref="Console"/>
            <AppenderRef ref="File"/>
        </Root>
    </Loggers>
</Configuration>
```

주의할 점: `spring-boot-starter-logging`을 exclude하지 않으면 Logback과 Log4j2가 동시에 클래스패스에 올라간다. 이 상태에서 어떤 구현체가 바인딩될지 예측이 안 되고, 실행 시 SLF4J 경고 메시지가 출력된다.


## 4. MDC를 활용한 요청 추적

MDC(Mapped Diagnostic Context)는 스레드 로컬 기반으로 로그에 컨텍스트 정보를 넣는 방법이다. HTTP 요청마다 고유 ID를 부여하면 수십만 줄의 로그에서 특정 요청의 흐름을 추적할 수 있다.

### 필터로 traceId 주입

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MdcFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        try {
            String traceId = generateTraceId((HttpServletRequest) request);
            MDC.put("traceId", traceId);

            // 응답 헤더에도 넣어두면 프론트엔드에서 에러 리포트할 때 같이 보내줄 수 있다
            ((HttpServletResponse) response).setHeader("X-Trace-Id", traceId);

            chain.doFilter(request, response);
        } finally {
            MDC.clear(); // 반드시 clear 해야 한다. 스레드 풀에서 재사용되면 이전 요청의 traceId가 남는다
        }
    }

    private String generateTraceId(HttpServletRequest request) {
        // 게이트웨이에서 이미 traceId를 넣어줬으면 그걸 쓴다
        String existing = request.getHeader("X-Trace-Id");
        if (existing != null && !existing.isBlank()) {
            return existing;
        }
        return UUID.randomUUID().toString().substring(0, 8);
    }
}
```

로그 패턴에 `%X{traceId}`를 넣어두면 모든 로그에 traceId가 찍힌다.

```
2026-03-29 14:23:01.123 [http-nio-8080-exec-1] [a3f2b1c9] INFO  OrderService - 주문 생성 요청: userId=1234, itemCount=3
2026-03-29 14:23:01.456 [http-nio-8080-exec-1] [a3f2b1c9] INFO  PaymentService - 결제 요청: orderId=5678
2026-03-29 14:23:02.789 [http-nio-8080-exec-1] [a3f2b1c9] ERROR PaymentService - 결제 실패: PG 타임아웃
```

이렇게 같은 traceId로 묶여 있으면 `grep a3f2b1c9 application.log`만으로 해당 요청의 전체 흐름을 볼 수 있다.

### MDC와 비동기 처리

MDC는 ThreadLocal 기반이라 `@Async`, `CompletableFuture`, 별도 스레드에서는 값이 전파되지 않는다. 이걸 모르고 비동기 처리를 추가했다가 traceId가 null로 찍히는 경우가 많다.

해결 방법은 TaskDecorator를 사용하는 것이다.

```java
public class MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
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
public class AsyncConfig {

    @Bean
    public TaskExecutor taskExecutor() {
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

`@Async`를 사용하는 모든 곳에서 이 executor를 쓰면 MDC 값이 자식 스레드로 복사된다.


## 5. 비동기 로깅 설정과 주의점

### Logback AsyncAppender

```xml
<appender name="ASYNC_FILE" class="ch.qos.logback.classic.AsyncAppender">
    <queueSize>1024</queueSize>
    <discardingThreshold>0</discardingThreshold>
    <neverBlock>false</neverBlock>
    <appender-ref ref="FILE"/>
</appender>
```

각 설정의 의미를 정확히 알아야 한다.

- `queueSize`: 내부 큐 크기. 기본값 256은 트래픽이 몰리면 금방 찬다. 운영에서는 최소 1024 이상.
- `discardingThreshold`: 큐가 이 비율 이하로 남으면 TRACE, DEBUG, INFO 로그를 버린다. 기본값 20(%)이다. 0으로 설정하면 로그를 절대 버리지 않는다. ERROR 로그가 유실되면 장애 분석이 불가능하니, 0으로 설정하거나 최소한 ERROR는 동기 appender로도 보내는 게 안전하다.
- `neverBlock`: `true`면 큐가 꽉 찼을 때 로그를 버린다. `false`면 큐에 빈자리가 날 때까지 호출 스레드가 블록된다. 운영 환경에서 `true`로 하면 로그가 유실될 수 있고, `false`로 하면 로깅이 애플리케이션 성능에 영향을 준다. 상황에 맞게 선택해야 한다.

### Log4j2 AsyncLogger

Log4j2의 비동기 로깅이 성능상 유리하다. LMAX Disruptor 기반이라 lock-free 구조다.

```xml
<!-- log4j2-spring.xml -->
<Configuration>
    <Loggers>
        <AsyncLogger name="com.example" level="INFO" additivity="false">
            <AppenderRef ref="File"/>
        </AsyncLogger>
        <Root level="INFO">
            <AppenderRef ref="Console"/>
        </Root>
    </Loggers>
</Configuration>
```

전체 로거를 비동기로 돌리려면 시스템 프로퍼티를 설정한다.

```properties
# JVM 옵션
-Dlog4j2.contextSelector=org.apache.logging.log4j.core.async.AsyncLoggerContextSelector
```

주의: 비동기 로깅에서는 로그가 실제 기록되는 시점이 지연된다. 애플리케이션이 비정상 종료되면 큐에 남아있던 로그가 유실된다. `ShutdownHook`이 제대로 동작하도록 graceful shutdown 설정을 확인해야 한다.

```xml
<Configuration shutdownHook="disable">
    <!-- Spring Boot의 shutdown hook과 충돌 방지 -->
</Configuration>
```

Spring Boot 2.x 이상에서는 Log4j2의 shutdownHook을 disable하고 Spring의 shutdown 과정에서 로그 시스템을 정리하도록 맡기는 게 맞다.


## 6. 로그 레벨 런타임 변경 (Actuator)

운영 중에 서버를 재시작하지 않고 로그 레벨을 바꿔야 하는 상황이 자주 생긴다. Spring Boot Actuator의 `/loggers` 엔드포인트가 이걸 지원한다.

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: loggers
  endpoint:
    loggers:
      enabled: true
```

현재 로그 레벨 확인:

```bash
curl http://localhost:8080/actuator/loggers/com.example.order
```

```json
{
  "configuredLevel": null,
  "effectiveLevel": "INFO"
}
```

런타임 변경:

```bash
curl -X POST http://localhost:8080/actuator/loggers/com.example.order \
  -H "Content-Type: application/json" \
  -d '{"configuredLevel": "DEBUG"}'
```

이 변경은 메모리에만 반영된다. 서버가 재시작되면 원래 설정으로 돌아간다. 디버깅 끝나면 원래 레벨로 되돌리는 걸 잊지 않아야 한다. DEBUG 로그를 켜놓은 채로 방치하면 디스크 사용량이 급격히 늘어난다.

### 보안 주의사항

Actuator 엔드포인트를 외부에 노출하면 누구나 로그 레벨을 바꿀 수 있다. 운영 환경에서는 반드시 인증을 걸어야 한다.

```yaml
# 관리 포트를 분리하는 방법
management:
  server:
    port: 9090  # 내부 네트워크에서만 접근 가능하게
```

또는 Spring Security로 Actuator 경로에 인증을 추가한다.

```java
@Configuration
public class ActuatorSecurityConfig {

    @Bean
    public SecurityFilterChain actuatorFilterChain(HttpSecurity http) throws Exception {
        http.securityMatcher("/actuator/**")
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health").permitAll()
                .anyRequest().hasRole("ADMIN")
            )
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}
```


## 7. 민감정보 마스킹 패턴

로그에 개인정보나 인증 토큰이 그대로 찍히면 보안 사고다. PCI DSS, 개인정보보호법 등 규정 위반에 해당할 수 있다.

### Logback 커스텀 컨버터 방식

```java
public class MaskingPatternLayout extends PatternLayout {

    private Pattern multilinePattern;
    private List<String> maskPatterns = new ArrayList<>();

    public void addMaskPattern(String maskPattern) {
        maskPatterns.add(maskPattern);
        multilinePattern = Pattern.compile(
            String.join("|", maskPatterns),
            Pattern.MULTILINE
        );
    }

    @Override
    public String doLayout(ILoggingEvent event) {
        return maskMessage(super.doLayout(event));
    }

    private String maskMessage(String message) {
        if (multilinePattern == null) {
            return message;
        }
        StringBuilder sb = new StringBuilder(message);
        Matcher matcher = multilinePattern.matcher(sb);
        while (matcher.find()) {
            if (matcher.group().length() > 4) {
                // 앞 2자리만 남기고 나머지는 마스킹
                int start = matcher.start() + 2;
                int end = matcher.end();
                for (int i = start; i < end; i++) {
                    sb.setCharAt(i, '*');
                }
            }
        }
        return sb.toString();
    }
}
```

```xml
<appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="ch.qos.logback.core.encoder.LayoutWrappingEncoder">
        <layout class="com.example.logging.MaskingPatternLayout">
            <maskPattern>\d{3}-\d{2}-\d{4}</maskPattern>         <!-- SSN -->
            <maskPattern>\d{4}-\d{4}-\d{4}-\d{4}</maskPattern>   <!-- 카드번호 -->
            <maskPattern>[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+</maskPattern>  <!-- 이메일 -->
            <pattern>${LOG_PATTERN}</pattern>
        </layout>
    </encoder>
</appender>
```

### 로그 출력 전에 마스킹하는 방식

정규식 마스킹보다는 애초에 로그에 찍을 때 마스킹된 값을 넘기는 게 더 안전하다.

```java
@Slf4j
@Service
public class UserService {

    public void updateEmail(Long userId, String email) {
        log.info("이메일 변경: userId={}, email={}", userId, maskEmail(email));
    }

    private String maskEmail(String email) {
        int atIndex = email.indexOf('@');
        if (atIndex <= 2) return "***" + email.substring(atIndex);
        return email.substring(0, 2) + "***" + email.substring(atIndex);
    }
}
```

출력 결과: `이메일 변경: userId=1234, email=te***@example.com`

정규식 기반 마스킹은 패턴에 안 잡히는 형태의 민감정보가 빠져나갈 수 있다. 코드 레벨에서 마스킹하는 것과 로그 레이어에서 마스킹하는 것을 병행하는 게 현실적이다.


## 8. 멀티모듈 프로젝트에서의 로깅 설정 충돌

멀티모듈 프로젝트에서 각 모듈이 자체 `logback-spring.xml`을 가지고 있으면 어떤 파일이 적용될지 예측할 수 없다. 클래스패스에서 먼저 발견되는 파일이 적용되는데, 이 순서는 빌드 도구와 의존성 선언 순서에 따라 달라진다.

### 문제 상황

```
project-root/
├── module-core/
│   └── src/main/resources/logback-spring.xml   ← 이게 적용될 수도 있고
├── module-api/
│   └── src/main/resources/logback-spring.xml   ← 이게 적용될 수도 있다
└── module-batch/
    └── src/main/resources/logback-spring.xml
```

### 해결 방법 1: 실행 모듈에만 설정 파일 배치

가장 깔끔한 방법이다. 라이브러리 성격의 모듈(core, common)에는 로깅 설정 파일을 두지 않는다. 실행 가능한 모듈(api, batch)에만 `logback-spring.xml`을 둔다.

```
project-root/
├── module-core/
│   └── (로깅 설정 파일 없음)
├── module-api/
│   └── src/main/resources/logback-spring.xml
└── module-batch/
    └── src/main/resources/logback-spring.xml
```

### 해결 방법 2: include로 공통 설정 분리

공통 설정을 별도 파일로 빼고 각 실행 모듈에서 include하는 방법이다.

```xml
<!-- module-core/src/main/resources/logback-common.xml -->
<included>
    <property name="LOG_PATTERN" value="%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"/>

    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>
</included>
```

```xml
<!-- module-api/src/main/resources/logback-spring.xml -->
<configuration>
    <include resource="logback-common.xml"/>

    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <!-- API 모듈 전용 설정 -->
    </appender>

    <springProfile name="prod">
        <root level="INFO">
            <appender-ref ref="CONSOLE"/>
            <appender-ref ref="FILE"/>
        </root>
    </springProfile>
</configuration>
```

공통 XML 파일명은 `logback-spring.xml`이나 `logback.xml`이 아닌 다른 이름으로 해야 한다. `logback-common.xml` 같은 이름을 쓴다. 그래야 Logback이 자동으로 읽어들이지 않는다.

### 해결 방법 3: 설정 파일 경로 지정

`application.yml`에서 명시적으로 설정 파일 경로를 지정할 수 있다.

```yaml
logging:
  config: classpath:logging/logback-api.xml
```

이 방법은 파일 이름 충돌 자체를 피할 수 있다. 다만 팀원들이 이 설정을 모르면 "왜 logback-spring.xml을 수정해도 반영이 안 되지?"라는 문제를 겪게 된다.


## 9. 운영 환경 로깅 설정 시 고려할 점

### 로그 출력량 관리

운영에서 DEBUG 로그를 전부 남기면 하루에 수십 GB가 쌓이는 경우가 있다. 특히 HTTP 요청/응답 본문을 로그로 남기는 경우가 심하다.

```yaml
# 프레임워크 로거는 레벨을 높게 잡는다
logging:
  level:
    root: INFO
    com.example: INFO
    org.springframework.web: WARN
    org.hibernate.SQL: WARN
    org.apache.kafka: WARN
```

### 로그 포맷: JSON 구조화

ELK, Datadog, CloudWatch 같은 로그 수집 시스템을 쓴다면 JSON 포맷이 파싱에 유리하다.

```xml
<!-- Logstash Logback Encoder 사용 -->
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>7.4</version>
</dependency>
```

```xml
<appender name="JSON_FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <file>${LOG_PATH}/application.json</file>
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
        <includeMdcKeyName>traceId</includeMdcKeyName>
        <includeMdcKeyName>userId</includeMdcKeyName>
    </encoder>
    <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
        <fileNamePattern>${LOG_PATH}/application.%d{yyyy-MM-dd}.%i.json.gz</fileNamePattern>
        <maxFileSize>100MB</maxFileSize>
        <maxHistory>7</maxHistory>
    </rollingPolicy>
</appender>
```

출력 예시:

```json
{
  "@timestamp": "2026-03-29T14:23:01.123+09:00",
  "level": "ERROR",
  "logger_name": "com.example.PaymentService",
  "message": "결제 실패: PG 타임아웃",
  "thread_name": "http-nio-8080-exec-1",
  "traceId": "a3f2b1c9",
  "stack_trace": "com.example.exception.PaymentException: PG timeout\n\tat ..."
}
```

### 로그와 메트릭은 다르다

"분당 에러 발생 횟수"를 알고 싶다면 로그를 파싱하는 것보다 Micrometer 카운터를 쓰는 게 맞다. 로그는 디버깅용이고, 메트릭은 모니터링용이다. 목적이 다른 것을 하나의 도구로 해결하려 하면 둘 다 어중간해진다.

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final MeterRegistry meterRegistry;

    public void processPayment(PaymentRequest request) {
        try {
            // 결제 처리
        } catch (PaymentException e) {
            log.error("결제 실패: {}", e.getMessage(), e);
            meterRegistry.counter("payment.failure", "reason", e.getReason()).increment();
            throw e;
        }
    }
}
```

로그에는 상세 에러 내용을, 메트릭에는 집계 가능한 수치를 남긴다. Grafana 대시보드에서 에러율 급증을 감지하고, 구체적인 원인은 로그에서 찾는 흐름이 실무에서 잘 동작한다.
