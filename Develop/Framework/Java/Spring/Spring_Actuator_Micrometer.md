---
title: Spring Actuator Micrometer 심화
tags: [spring, java, monitoring, observability, backend]
updated: 2026-09-22
---

# Spring Actuator Micrometer 심화

Actuator와 Micrometer 조합은 의존성 몇 줄로 `/actuator/prometheus` 엔드포인트를 열고 수십 개의 JVM 메트릭을 노출한다. 그런데 커스텀 메트릭을 붙이거나 보안 설정을 손보거나 Grafana 대시보드를 연동할 때마다 잘 안 되는 지점이 생긴다. 어노테이션이 적용 안 되는 것처럼 보이거나, 메트릭이 올라오다 갑자기 사라지거나, Prometheus가 인증 없이 열려 있거나.

## 커스텀 MeterRegistry 구현

Micrometer는 `MeterRegistry`를 추상화 계층으로 두고, 실제 저장소(Prometheus, InfluxDB, Datadog 등)가 이를 구현한다. `spring-boot-actuator`가 클래스패스에 있으면 `PrometheusMeterRegistry`를 자동 등록한다.

커스텀 `MeterRegistry`가 필요한 경우는 주로 두 가지다. 메트릭에 공통 태그를 붙이거나, 특정 메트릭만 다른 저장소로 라우팅하는 경우다.

**공통 태그 추가**

```java
@Configuration
public class MetricsConfig {

    @Bean
    public MeterRegistryCustomizer<MeterRegistry> commonTags(
        @Value("${spring.application.name}") String appName,
        @Value("${deploy.environment:local}") String env
    ) {
        return registry -> registry.config()
            .commonTags("application", appName, "environment", env);
    }
}
```

`MeterRegistryCustomizer`는 빈이 등록되는 모든 `MeterRegistry`에 적용된다. `PrometheusMeterRegistry`에만 적용하려면 제네릭 타입을 좁힌다.

```java
@Bean
public MeterRegistryCustomizer<PrometheusMeterRegistry> prometheusOnly() {
    return registry -> registry.config()
        .namingConvention(NamingConvention.snakeCase);
}
```

**복합 레지스트리**

Prometheus와 InfluxDB 두 곳에 동시에 메트릭을 보내야 할 때 `CompositeMeterRegistry`를 직접 구성한다.

```java
@Bean
public MeterRegistry compositeMeterRegistry(
    PrometheusMeterRegistry prometheus,
    InfluxMeterRegistry influx
) {
    CompositeMeterRegistry composite = new CompositeMeterRegistry();
    composite.add(prometheus);
    composite.add(influx);
    return composite;
}
```

이때 `@Primary`를 붙이지 않으면 Spring Boot가 자동 구성한 `PrometheusMeterRegistry`와 충돌해 빈 등록 오류가 난다. `CompositeMeterRegistry`를 직접 쓸 때는 자동 구성을 끄거나 `@Primary`를 명확히 지정해야 한다.

**메트릭 필터링**

특정 메트릭을 레지스트리에서 제외하거나 이름을 바꿔야 할 때 `MeterFilter`를 쓴다.

```java
@Bean
public MeterRegistryCustomizer<MeterRegistry> meterFilter() {
    return registry -> registry.config()
        .meterFilter(MeterFilter.deny(id ->
            id.getName().startsWith("jvm.gc.pause")
        ))
        .meterFilter(MeterFilter.ignoreTags("host")); // 카디널리티 폭발 방지
}
```

카디널리티 폭발은 Prometheus를 죽이는 가장 흔한 원인이다. `host`, `user_id`, `request_id` 같은 태그를 무심코 붙이면 시계열 수가 급증한다. `MeterFilter.ignoreTags()`로 레지스트리 진입 전에 잘라낸다.

## @Timed와 @Counted 함정

`@Timed`와 `@Counted`는 AOP 기반이다. Spring AOP는 프록시를 경유하는 호출에만 동작한다. 같은 클래스 내부에서 직접 메서드를 호출하면 프록시를 우회하므로 어노테이션이 동작하지 않는다.

```java
@Service
public class OrderService {

    @Timed("order.process")
    public void processOrder(Long orderId) {
        // 이 메서드는 측정된다
    }

    public void processAll(List<Long> ids) {
        for (Long id : ids) {
            processOrder(id); // 프록시 우회 — 측정 안 됨
        }
    }
}
```

`processAll`에서 호출하는 `processOrder`는 `this`를 통한 직접 호출이므로 타이머가 기록되지 않는다. `processAll` 자체에도 `@Timed`가 없으면 두 메서드 모두 메트릭이 나오지 않는다.

해결 방법은 두 가지다.

첫째, 자기 자신을 주입받는다.

```java
@Service
public class OrderService {

    @Autowired
    private OrderService self; // 순환 의존 아님 — Spring이 프록시를 주입

    @Timed("order.process")
    public void processOrder(Long orderId) { ... }

    public void processAll(List<Long> ids) {
        for (Long id : ids) {
            self.processOrder(id); // 프록시 경유
        }
    }
}
```

둘째, `MeterRegistry`를 직접 주입해서 수동으로 기록한다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final MeterRegistry meterRegistry;

    public void processAll(List<Long> ids) {
        Timer timer = meterRegistry.timer("order.process");
        for (Long id : ids) {
            timer.record(() -> processOrder(id));
        }
    }
}
```

수동 기록 방식은 프록시 여부와 무관하게 동작한다. 루프 내부에서 `Timer` 객체를 매번 조회하는 건 성능 문제가 없다 — `MeterRegistry`는 이름+태그 조합으로 캐싱하므로 매번 새 객체를 만들지 않는다.

**@Timed가 클래스 레벨에 있을 때**

`@Timed`를 클래스에 붙이면 모든 public 메서드에 적용된다고 생각하기 쉽다. 그런데 Spring AOP는 클래스 레벨 `@Timed`를 인식하는 어드바이저를 자동 등록하지 않는다. `TimedAspect` 빈을 직접 등록해야 한다.

```java
@Bean
public TimedAspect timedAspect(MeterRegistry registry) {
    return new TimedAspect(registry);
}
```

이 빈이 없으면 `@Timed`가 붙어 있어도 타이머가 전혀 기록되지 않는다. 개발 환경에서 `actuator/prometheus`에 해당 메트릭이 없을 때 가장 먼저 확인해야 한다.

`@Counted`도 마찬가지로 `CountedAspect` 빈이 필요하다.

```java
@Bean
public CountedAspect countedAspect(MeterRegistry registry) {
    return new CountedAspect(registry);
}
```

**롱태스크 타이머**

`@Timed(longTask = true)`는 일반 타이머와 다르다. 일반 타이머는 메서드가 끝난 후 기록하고, 롱태스크 타이머는 실행 중인 메서드의 수와 현재까지 소요 시간을 지속적으로 노출한다.

```java
@Timed(value = "batch.job", longTask = true)
public void runBatchJob() {
    // 수십 분짜리 배치
}
```

Prometheus에서 `batch_job_active_tasks`와 `batch_job_duration_seconds_active_sum`이 올라온다. 배치가 실행 중일 때 Grafana 알림을 걸기 좋다.

## Prometheus 엔드포인트 보안 설정

기본 설정에서 `/actuator/prometheus`는 인증 없이 열린다. 내부망에서만 노출한다면 괜찮지만, 인터넷에 노출되는 서버라면 반드시 막아야 한다.

**Spring Security로 엔드포인트 보호**

```java
@Configuration
@EnableWebSecurity
public class ActuatorSecurityConfig {

    @Bean
    public SecurityFilterChain actuatorFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/actuator/**")
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health", "/actuator/health/**").permitAll()
                .anyRequest().hasRole("ACTUATOR")
            )
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}
```

`/actuator/health`는 로드 밸런서 헬스체크용으로 열어두고 나머지는 인증을 요구한다. Prometheus 스크레이퍼에는 Basic 인증 자격증명을 prometheus.yml에 설정한다.

```yaml
scrape_configs:
  - job_name: 'spring-app'
    metrics_path: '/actuator/prometheus'
    basic_auth:
      username: 'prometheus'
      password: 'scrape-password'
    static_configs:
      - targets: ['app-host:8080']
```

**포트 분리**

관리 엔드포인트를 애플리케이션 포트와 분리하는 방법도 있다.

```yaml
management:
  server:
    port: 8090
    address: 127.0.0.1  # 루프백만 허용
```

`address: 127.0.0.1`로 설정하면 로컬호스트에서만 접근 가능하다. Prometheus가 같은 서버나 사이드카 컨테이너에서 스크레이핑하는 구성에서 쓴다. 포트 분리를 하면 Spring Security 설정과 충돌 없이 방화벽 레벨에서 차단할 수 있다.

**노출 대상 명시**

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus, metrics
        # 기본값 * 을 쓰면 heapdump, threaddump, env 같은 민감한 엔드포인트도 열린다
```

`include: "*"` 를 쓰면 `/actuator/heapdump`도 열린다. 힙덤프는 메모리에 있는 데이터를 그대로 덤프하므로 패스워드, 토큰 같은 민감 데이터가 포함될 수 있다. 필요한 엔드포인트만 명시한다.

## JVM 메트릭

`spring-boot-actuator`를 추가하면 JVM 메트릭이 자동으로 수집된다. 자동 수집 항목은 `jvm.memory.*`, `jvm.gc.*`, `jvm.threads.*`, `process.cpu.*` 등이다.

**힙 사용률 확인**

Prometheus에서 힙 사용률을 계산하는 방식이 직관적이지 않다.

```promql
# 현재 힙 사용량 / 최대 힙
jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}
```

`jvm_memory_max_bytes`가 `-1`을 반환하는 경우가 있다. 최대 메모리를 설정하지 않았을 때다. `-Xmx`를 명시하지 않으면 JVM이 최대 힙을 시스템 메모리의 25%로 잡는데, Micrometer가 이를 `-1`로 리포팅한다. 계산식이 음수가 나오면 이 경우다.

**GC 일시정지 시간**

```promql
# 1분간 GC pause 합계
increase(jvm_gc_pause_seconds_sum[1m])
```

G1GC는 Young, Mixed, Full 단계별로 레이블이 분리된다. Full GC가 발생하면 `cause="Heap Dump"` 또는 `cause="Allocation Failure"` 레이블로 구분된다. Full GC가 빈번하면 힙 튜닝이나 메모리 누수 점검이 필요하다.

**스레드 상태**

```promql
jvm_threads_states_threads{state="blocked"}
```

`blocked` 상태 스레드가 지속적으로 증가하면 락 경합이 일어나고 있다는 신호다. `deadlocked` 상태가 1 이상이면 즉시 스레드 덤프를 뜬다.

## HikariCP 메트릭

`spring-boot-starter-data-jpa`나 `spring-boot-starter-jdbc`를 사용하면 HikariCP 메트릭이 자동 수집된다.

핵심 지표는 세 가지다.

```promql
# 활성 커넥션 수
hikaricp_connections_active{pool="HikariPool-1"}

# 대기 중인 스레드 수 (커넥션 획득 대기)
hikaricp_connections_pending{pool="HikariPool-1"}

# 커넥션 획득 대기 시간 (p99)
histogram_quantile(0.99,
  rate(hikaricp_connections_acquire_seconds_bucket[5m])
)
```

`pending` 값이 0보다 크다면 커넥션 풀이 부족하다. `maximum-pool-size`를 키우거나 쿼리 성능을 개선해야 한다. 무작정 풀 크기를 키우면 DB 서버의 최대 커넥션을 초과할 수 있다.

`acquire` 시간이 갑자기 치솟으면 세 가지 중 하나다. 풀이 가득 찼거나, 커넥션 유효성 검사가 느리거나, DB 서버가 느리거나. `hikaricp_connections_timeout_total`이 함께 올라가면 타임아웃이 발생하고 있다는 뜻이다.

pool 이름은 `spring.datasource.hikari.pool-name`으로 지정한다. 여러 데이터소스를 쓸 때 이름을 명시하지 않으면 `HikariPool-1`, `HikariPool-2`처럼 나와서 어느 풀인지 구분이 안 된다.

## Kafka 메트릭

`spring-kafka`는 Micrometer를 직접 지원한다. 프로듀서와 컨슈머 메트릭이 각각 자동 수집된다.

**컨슈머 랙**

컨슈머 랙은 가장 중요한 Kafka 메트릭이다. 처리가 밀리면 랙이 쌓인다.

```promql
# 컨슈머 그룹별 랙 합계
sum by (group_id, topic) (
  kafka_consumer_fetch_manager_records_lag{client_id=~".*"}
)
```

Spring Kafka가 노출하는 `kafka_consumer_fetch_manager_records_lag`는 각 파티션의 현재 랙이다. 파티션별로 쪼개져 있으므로 `sum`으로 집계한다.

랙 알림 임계값은 토픽마다 다르다. 이벤트 유실이 허용되지 않는 주문 토픽과 단순 로그 토픽을 같은 임계값으로 설정하면 안 된다.

**프로듀서 오류율**

```promql
# 프로듀서 레코드 전송 오류율
rate(kafka_producer_record_error_total[5m]) /
rate(kafka_producer_record_send_total[5m])
```

`record_error_total`이 올라가면 브로커에 연결 문제가 있거나 직렬화 오류가 나고 있다. 로그와 함께 봐야 원인을 특정할 수 있다.

## Grafana 대시보드 프로비저닝

Grafana 대시보드를 UI에서 만들면 재현이 안 된다. 프로비저닝 파일로 관리해야 배포할 때 대시보드가 자동으로 생긴다.

**프로비저닝 설정**

```yaml
# grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

```yaml
# grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1
providers:
  - name: 'spring-metrics'
    orgId: 1
    folder: 'Spring'
    type: file
    disableDeletion: true
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/dashboards
```

`disableDeletion: true`로 설정하면 Grafana UI에서 대시보드를 삭제해도 다음 갱신 주기에 복원된다.

**JVM 대시보드 JSON 핵심 패널**

```json
{
  "title": "Heap Usage",
  "type": "timeseries",
  "targets": [
    {
      "expr": "sum(jvm_memory_used_bytes{application=\"$application\", area=\"heap\"}) / sum(jvm_memory_max_bytes{application=\"$application\", area=\"heap\"})",
      "legendFormat": "Heap Used %"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percentunit",
      "thresholds": {
        "steps": [
          {"value": 0.8, "color": "orange"},
          {"value": 0.9, "color": "red"}
        ]
      }
    }
  }
}
```

대시보드 JSON에서 `$application`처럼 변수를 쓰면 같은 대시보드를 여러 서비스에서 재사용한다. 변수는 Grafana의 `templating.list`에 선언한다.

**HikariCP + Kafka 패널 예시**

```json
{
  "title": "Connection Pool Active",
  "targets": [
    {
      "expr": "hikaricp_connections_active{application=\"$application\"}",
      "legendFormat": "{{pool}}"
    },
    {
      "expr": "hikaricp_connections_pending{application=\"$application\"}",
      "legendFormat": "{{pool}} pending"
    }
  ]
}
```

```json
{
  "title": "Kafka Consumer Lag",
  "targets": [
    {
      "expr": "sum by (topic) (kafka_consumer_fetch_manager_records_lag{application=\"$application\"})",
      "legendFormat": "{{topic}}"
    }
  ],
  "alert": {
    "conditions": [
      {
        "evaluator": {"type": "gt", "params": [10000]},
        "query": {"params": ["A", "5m", "now"]}
      }
    ]
  }
}
```

대시보드 JSON을 Git으로 관리하면 리뷰가 가능하고 인프라 변경과 묶어 커밋할 수 있다. Grafana 8 이후 대시보드 JSON 스키마가 바뀌었으므로 Grafana 버전을 올릴 때 JSON을 다시 export해서 확인한다.

## 메트릭 누락 시 점검 순서

1. `TimedAspect`, `CountedAspect` 빈이 등록돼 있는지 확인
2. 어노테이션이 붙은 메서드가 프록시를 경유하는지 확인 (같은 클래스 내 직접 호출 여부)
3. `/actuator/metrics/{메트릭이름}` 엔드포인트에서 메트릭 자체가 존재하는지 확인
4. `management.endpoints.web.exposure.include`에 `prometheus`가 포함돼 있는지 확인
5. `MeterFilter`가 해당 메트릭을 걸러내고 있지 않은지 확인

3번에서 메트릭이 존재하는데 Prometheus에서 안 보이면 레지스트리 설정 문제다. 메트릭 자체가 없으면 어노테이션 처리 문제다.
