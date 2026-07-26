---
title: Spring Boot 로깅
tags: [spring, spring-boot, logging, logback, slf4j, mdc, actuator, json-logging]
updated: 2026-07-26
---

# Spring Boot 로깅

## Spring Boot 로깅 자동설정

`spring-boot-starter`를 의존성에 추가하면 `spring-boot-starter-logging`이 함께 딸려온다. 이 모듈이 SLF4J + Logback을 클래스패스에 넣고 초기화까지 처리한다.

중요한 점은 로깅 시스템이 `ApplicationContext` 생성 이전에 초기화된다는 것이다. `@Bean`이나 `@Configuration`보다 먼저 로깅이 세팅된다. 그래서 `@PostConstruct`에서 로깅 설정을 바꾸려고 해도 이미 늦다.

초기화 순서:

1. `LoggingSystem`이 클래스패스에서 구현체 탐색 (Logback 또는 Log4j2)
2. 구현체별 설정 파일 탐색
   - Logback: `logback-spring.xml` → `logback.xml`
   - Log4j2: `log4j2-spring.xml` → `log4j2.xml`
3. 설정 파일 없으면 Spring Boot 기본 설정 적용
4. `application.yml`의 `logging.*` 프로퍼티 추가 반영

`logback-spring.xml`을 써야 하는 이유가 있다. `logback.xml`은 순수 Logback 파일이라 `<springProfile>` 태그와 Spring Boot의 `${}` 프로퍼티 치환을 쓸 수 없다. 운영/로컬 환경을 분리해야 한다면 반드시 `logback-spring.xml`로 만들어야 한다.

`application.yml`로만 처리할 수 있는 기본 설정:

```yaml
logging:
  level:
    root: INFO
    com.example: DEBUG
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql.BasicBinder: TRACE  # SQL 파라미터 값 출력
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

파일 롤링 정책이나 프로파일별 appender 분리가 필요하면 `logback-spring.xml`을 직접 작성해야 한다. `application.yml`만으로는 제어 범위에 한계가 있다.


## logback-spring.xml 설정

### 기본 구조

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <!-- 환경변수 LOG_DIR이 있으면 사용, 없으면 ./logs -->
    <property name="LOG_PATH" value="${LOG_DIR:-./logs}"/>
    <property name="LOG_PATTERN"
              value="%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"/>

    <!-- 콘솔 출력 -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <!-- 일별 + 크기별 롤링 파일 -->
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

    <!-- ERROR 전용 파일 - 장애 대응 시 이 파일만 grep하면 된다 -->
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
            <totalSizeCap>1GB</totalSizeCap>
        </rollingPolicy>
        <encoder>
            <pattern>${LOG_PATTERN}</pattern>
        </encoder>
    </appender>

    <!-- 로컬 환경 -->
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
        <logger name="org.hibernate.SQL" level="OFF"/>
        <logger name="org.springframework.web" level="WARN"/>
        <logger name="org.apache.kafka" level="WARN"/>
    </springProfile>
</configuration>
```

### 자주 나오는 실수

**CONSOLE appender 클래스를 잘못 지정하는 경우가 있다.** `ch.qos.logback.classic.encoder.PatternLayoutEncoder`를 appender class로 쓰면 콘솔 출력이 안 된다. CONSOLE appender는 반드시 `ch.qos.logback.core.ConsoleAppender`다. `PatternLayoutEncoder`는 `<encoder>` 태그 안에서 쓰는 클래스다.

**`totalSizeCap` 미설정**: `maxHistory`만 걸면 파일 개수는 제한되지만, 파일 하나가 클 경우 디스크를 채울 수 있다. 운영 환경에서는 반드시 설정한다.

**로그 파일 경로 하드코딩**: 컨테이너 환경에서 `/var/log/app` 같은 절대경로를 쓰면 볼륨 마운트 설정과 충돌한다. `${LOG_DIR:-./logs}` 패턴으로 환경변수에서 주입받는 게 낫다.


## 롤링 정책

### SizeAndTimeBasedRollingPolicy

날짜가 바뀌거나 파일 크기가 한계를 넘으면 롤링한다. 파일명 패턴에 `%i`가 있어야 같은 날 여러 파일이 생긴다.

```xml
<rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
    <!-- %d{yyyy-MM-dd}는 일별 롤링, %i는 같은 날 파일 번호 -->
    <fileNamePattern>${LOG_PATH}/app.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
    <maxFileSize>100MB</maxFileSize>   <!-- 파일 하나의 최대 크기 -->
    <maxHistory>30</maxHistory>         <!-- 보관 파일 수 (일별이면 30일치) -->
    <totalSizeCap>3GB</totalSizeCap>   <!-- 모든 아카이브 파일 합산 최대 용량 -->
    <cleanHistoryOnStart>false</cleanHistoryOnStart>  <!-- 앱 시작 시 오래된 파일 정리 여부 -->
</rollingPolicy>
```

`fileNamePattern`에 `.gz`를 붙이면 롤링 시 자동 압축한다. 압축률이 높아서 텍스트 로그 파일은 10분의 1 이하로 줄어드는 경우도 있다. 비용 부담 없이 보관 기간을 늘릴 수 있다.

`maxHistory`는 단위가 `fileNamePattern`의 날짜 패턴에 따라 달라진다. `%d{yyyy-MM-dd}`면 일 수, `%d{yyyy-MM}`면 월 수다. 착각하기 쉬운 부분이다.

### TimeBasedRollingPolicy

크기 제한 없이 날짜 기준으로만 롤링할 때 쓴다. 로그 양이 일정하고 예측 가능한 경우에 적합하다.

```xml
<rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
    <fileNamePattern>${LOG_PATH}/app.%d{yyyy-MM-dd}.log.gz</fileNamePattern>
    <maxHistory>30</maxHistory>
    <totalSizeCap>3GB</totalSizeCap>
</rollingPolicy>
```

### 비동기 Appender

로그를 동기로 쓰면 I/O가 애플리케이션 응답 시간에 직접 영향을 준다. 트래픽이 많은 서비스라면 AsyncAppender를 고려한다.

```xml
<appender name="ASYNC_FILE" class="ch.qos.logback.classic.AsyncAppender">
    <queueSize>1024</queueSize>        <!-- 기본값 256은 트래픽 몰릴 때 부족하다 -->
    <discardingThreshold>0</discardingThreshold>  <!-- 0: 로그 유실 없음, 기본값 20%는 INFO 이하 버림 -->
    <neverBlock>false</neverBlock>     <!-- true면 큐 꽉 찼을 때 로그 버림, false면 블록 -->
    <appender-ref ref="FILE"/>
</appender>
```

`discardingThreshold` 기본값이 20이다. 큐가 20% 이하로 남으면 TRACE, DEBUG, INFO 로그를 버린다. 장애 상황에서 DEBUG 로그가 필요한데 이미 버려진 경우가 있어서 운영에서는 0으로 설정하는 편이다. 다만 0으로 설정하면 큐가 꽉 찼을 때 `neverBlock` 설정에 따라 블록되거나 ERROR 로그까지 버릴 수 있다.

비동기 로깅에서 애플리케이션이 비정상 종료되면 큐에 남은 로그가 유실된다. 장애 발생 시 마지막 로그가 없어서 원인 파악이 어려워지는 경우가 있다.


## 구조화 로그 (JSON)

ELK, Datadog, CloudWatch Logs 같은 로그 수집 시스템을 쓴다면 JSON 포맷이 파싱에 유리하다. 텍스트 패턴 로그는 Logstash grok 패턴 같은 별도 파싱 설정이 필요하지만, JSON은 그대로 인덱싱할 수 있다.

### logstash-logback-encoder 사용

```xml
<!-- build.gradle 또는 pom.xml -->
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>7.4</version>
</dependency>
```

```xml
<!-- logback-spring.xml -->
<appender name="JSON_FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <file>${LOG_PATH}/application.json</file>
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
        <!-- MDC에서 특정 키만 JSON 필드로 포함 -->
        <includeMdcKeyName>traceId</includeMdcKeyName>
        <includeMdcKeyName>userId</includeMdcKeyName>
        <!-- 추가 고정 필드 -->
        <customFields>{"app":"order-service","env":"prod"}</customFields>
    </encoder>
    <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
        <fileNamePattern>${LOG_PATH}/application.%d{yyyy-MM-dd}.%i.json.gz</fileNamePattern>
        <maxFileSize>100MB</maxFileSize>
        <maxHistory>7</maxHistory>
        <totalSizeCap>2GB</totalSizeCap>
    </rollingPolicy>
</appender>
```

출력 예시:

```json
{
  "@timestamp": "2026-07-26T14:23:01.123+09:00",
  "level": "ERROR",
  "logger_name": "com.example.PaymentService",
  "message": "결제 실패: PG 타임아웃",
  "thread_name": "http-nio-8080-exec-1",
  "traceId": "a3f2b1c9",
  "userId": "1234",
  "app": "order-service",
  "env": "prod",
  "stack_trace": "com.example.exception.PaymentException: PG timeout\n\tat ..."
}
```

### 환경별 분리

로컬에서는 JSON보다 텍스트가 읽기 편하다. 프로파일로 분리한다.

```xml
<springProfile name="local,dev">
    <root level="DEBUG">
        <appender-ref ref="CONSOLE"/>
    </root>
</springProfile>

<springProfile name="prod">
    <root level="INFO">
        <appender-ref ref="JSON_FILE"/>
        <appender-ref ref="ERROR_FILE"/>
    </root>
</springProfile>
```

### StructuredArguments로 필드 추가

일반 메시지 인자와 달리 JSON 출력에서 별도 필드로 분리된다.

```java
import static net.logstash.logback.argument.StructuredArguments.*;

log.info("주문 생성", kv("orderId", orderId), kv("userId", userId), kv("amount", amount));
```

텍스트 출력: `주문 생성 orderId=5678 userId=1234 amount=50000`
JSON 출력: `{"message": "주문 생성", "orderId": 5678, "userId": 1234, "amount": 50000, ...}`

ELK에서 `orderId` 필드로 검색하거나 집계할 수 있게 된다.


## MDC를 활용한 요청 추적

MDC(Mapped Diagnostic Context)는 ThreadLocal에 키-값을 저장하고 로그 패턴에서 `%X{key}` 형태로 꺼낸다. HTTP 요청마다 고유 ID를 부여해서 모든 로그에 자동으로 포함시키는 데 주로 쓴다.

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MdcFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;

        // 게이트웨이에서 이미 traceId를 넣어줬으면 그걸 이어받는다
        String traceId = Optional.ofNullable(httpRequest.getHeader("X-Trace-Id"))
                .filter(s -> !s.isBlank())
                .orElse(UUID.randomUUID().toString().replace("-", "").substring(0, 8));

        MDC.put("traceId", traceId);
        ((HttpServletResponse) response).setHeader("X-Trace-Id", traceId);

        try {
            chain.doFilter(request, response);
        } finally {
            MDC.clear();  // 스레드 풀에서 재사용 시 이전 요청 값이 남는 것을 방지
        }
    }
}
```

`grep a3f2b1c9 application.log`만으로 해당 요청의 전체 흐름을 볼 수 있다. 수십만 줄 로그에서 특정 요청을 추적할 때 이게 없으면 힘들다.

### 비동기 처리에서 MDC 전파

MDC는 ThreadLocal 기반이라 `@Async`, `CompletableFuture`, `ExecutorService`로 새 스레드가 생기면 값이 전파되지 않는다. traceId가 null로 찍히기 시작하면 이 문제다.

`TaskDecorator`로 부모 스레드의 MDC 스냅샷을 자식 스레드로 복사한다.

```java
public class MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // decorate()는 부모 스레드에서 호출된다. 이 시점의 MDC를 캡처한다
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

`CompletableFuture.runAsync()`를 직접 쓰는 경우에는 이 decorator가 적용되지 않는다. 별도로 처리해야 한다.


## 운영 환경 로그 레벨 동적 변경 (Actuator)

운영 중 서버 재시작 없이 로그 레벨을 바꿔야 하는 상황이 자주 생긴다. Spring Boot Actuator의 `/loggers` 엔드포인트가 이걸 지원한다.

```yaml
management:
  endpoints:
    web:
      exposure:
        include: loggers, health
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

`configuredLevel`이 null이면 상위 로거에서 상속받은 것이다. `effectiveLevel`이 실제 적용 레벨이다.

런타임 변경:

```bash
curl -X POST http://localhost:8080/actuator/loggers/com.example.order \
  -H "Content-Type: application/json" \
  -d '{"configuredLevel": "DEBUG"}'
```

변경 사항은 메모리에만 반영된다. 서버가 재시작되면 원래 설정으로 돌아간다. 디버깅 끝나고 DEBUG를 켜놓은 채로 방치하면 디스크 사용량이 급격히 늘어난다.

원래 레벨로 되돌리기:

```bash
curl -X POST http://localhost:8080/actuator/loggers/com.example.order \
  -H "Content-Type: application/json" \
  -d '{"configuredLevel": null}'
```

### Actuator 보안

Actuator 엔드포인트를 외부에 노출하면 누구나 로그 레벨을 바꿀 수 있다. 운영 환경에서는 인증이 필수다.

관리 포트를 내부 네트워크 전용으로 분리하는 방법:

```yaml
management:
  server:
    port: 9090  # 내부 네트워크에서만 접근 가능하게 방화벽 설정
```

Spring Security로 Actuator 경로에 인증을 추가하는 방법:

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


## 멀티모듈 프로젝트에서의 설정 충돌

멀티모듈 프로젝트에서 여러 모듈이 자체 `logback-spring.xml`을 가지면 어떤 파일이 적용될지 예측할 수 없다. 클래스패스에서 먼저 발견되는 파일이 적용되는데, 이 순서는 빌드 도구와 의존성 선언 순서에 따라 달라진다.

가장 깔끔한 해결은 실행 모듈에만 설정 파일을 두는 것이다. 라이브러리 성격의 모듈(core, common)에는 `logback-spring.xml`을 두지 않는다. 실행 가능한 모듈(api, batch)에만 둔다.

공통 설정이 필요하면 `include`로 분리한다:

```xml
<!-- module-core/src/main/resources/logback-common.xml -->
<!-- 파일명이 logback-spring.xml이 아니어야 한다. 그래야 자동으로 로드되지 않는다 -->
<included>
    <property name="LOG_PATTERN"
              value="%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"/>

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
            <appender-ref ref="FILE"/>
        </root>
    </springProfile>
</configuration>
```

또는 `application.yml`에서 명시적으로 설정 파일 경로를 지정한다:

```yaml
logging:
  config: classpath:logging/logback-api.xml
```

이 방법은 파일 이름 충돌을 피할 수 있다. 팀원이 이 설정을 모르면 "왜 logback-spring.xml을 수정해도 반영이 안 되지?"라는 혼란이 생기니 문서화가 필요하다.


## Log4j2로 전환

Logback 대신 Log4j2가 필요한 경우는 주로 비동기 로깅 성능이다. LMAX Disruptor 기반 AsyncLogger는 lock-free 구조라 고트래픽 환경에서 Logback보다 처리량이 높다.

```groovy
dependencies {
    implementation('org.springframework.boot:spring-boot-starter') {
        exclude group: 'org.springframework.boot', module: 'spring-boot-starter-logging'
    }
    implementation 'org.springframework.boot:spring-boot-starter-log4j2'
}
```

`spring-boot-starter-logging`을 명시적으로 exclude하지 않으면 Logback과 Log4j2가 동시에 클래스패스에 올라간다. SLF4J 경고가 출력되고 어떤 구현체가 바인딩됐는지 확인이 필요한 상황이 된다.

설정 파일은 `log4j2-spring.xml`로 만든다. `<springProfile>` 태그를 쓰려면 `log4j2.xml`이 아닌 `log4j2-spring.xml`이어야 한다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN" shutdownHook="disable">
    <!-- Spring Boot의 shutdown lifecycle에 로그 정리를 위임하기 위해 disable -->
    <Properties>
        <Property name="LOG_PATTERN">
            %d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n
        </Property>
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

`shutdownHook="disable"`로 설정하는 이유가 있다. Spring Boot 2.x 이상에서 Log4j2의 shutdown hook이 Spring의 shutdown lifecycle보다 먼저 실행되면, bean들을 정리하는 도중에 로그가 출력되지 않는다. Spring이 로그 시스템 정리를 담당하게 맡기면 이 문제를 피할 수 있다.
