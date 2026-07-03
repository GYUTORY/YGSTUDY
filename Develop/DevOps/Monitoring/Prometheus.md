---
title: Prometheus
tags: [devops, monitoring, prometheus, metrics, observability, promql, micrometer]
updated: 2026-04-09
---

# Prometheus

## 정의

Prometheus는 시계열 데이터 기반 오픈소스 모니터링 시스템이다. SoundCloud에서 시작해 CNCF 졸업 프로젝트가 됐다. Pull 방식으로 메트릭을 수집하고, PromQL이라는 자체 쿼리 언어로 데이터를 조회한다.

모니터링 시스템을 처음 도입할 때 Prometheus를 선택하는 이유는 단순하다. 설정이 YAML 파일 하나고, 별도 외부 DB 없이 자체 시계열 DB로 돌아가고, Kubernetes와 연동이 잘 된다.

## 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Prometheus 아키텍처                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐            │
│  │ Spring Boot  │   │  Node.js     │   │  PostgreSQL  │            │
│  │ /actuator/   │   │  /metrics    │   │  exporter    │            │
│  │ prometheus   │   │              │   │  :9187       │            │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘            │
│         │                  │                   │                    │
│         │    HTTP GET (Pull 방식)               │                    │
│         └──────────────────┼───────────────────┘                    │
│                            │                                        │
│                            ▼                                        │
│                   ┌─────────────────┐                               │
│                   │   Prometheus    │                                │
│                   │     Server      │                                │
│                   │                 │                                │
│                   │ ┌─────────────┐ │      ┌──────────────────┐     │
│                   │ │  Retrieval  │ │      │  Service         │     │
│                   │ │  (scrape)   │◄├──────│  Discovery       │     │
│                   │ └──────┬──────┘ │      │  (K8s, Consul,   │     │
│                   │        ▼        │      │   file_sd, DNS)  │     │
│                   │ ┌─────────────┐ │      └──────────────────┘     │
│                   │ │   TSDB      │ │                               │
│                   │ │ (로컬 저장소)│ │───────┐                       │
│                   │ └──────┬──────┘ │       │ Remote Write          │
│                   │        │        │       ▼                       │
│                   │ ┌─────────────┐ │  ┌──────────────┐            │
│                   │ │  Rule       │ │  │  Thanos /    │            │
│                   │ │  Engine     │ │  │  Cortex /    │            │
│                   │ │ (alert+rec) │ │  │  Mimir       │            │
│                   │ └──────┬──────┘ │  └──────────────┘            │
│                   └────────┼────────┘                               │
│                            │                                        │
│              ┌─────────────┼─────────────┐                          │
│              ▼                           ▼                          │
│     ┌─────────────────┐        ┌─────────────────┐                 │
│     │  Alertmanager   │        │    Grafana       │                 │
│     │                 │        │  (시각화)         │                 │
│     │  Slack, Email,  │        └─────────────────┘                 │
│     │  PagerDuty 등   │                                            │
│     └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Pull 방식 수집 흐름

Prometheus의 핵심은 Pull 방식이다. Push 방식(애플리케이션이 모니터링 서버로 데이터를 보내는 것)과 비교하면 큰 차이가 있다.

```
Pull 방식 (Prometheus)
──────────────────────────────────────────────

1. 앱이 /metrics 엔드포인트를 노출한다
2. Prometheus가 scrape_interval마다 HTTP GET 요청을 보낸다
3. 응답 본문의 메트릭 텍스트를 파싱해서 TSDB에 저장한다

    ┌─────────────┐     GET /metrics      ┌─────────────┐
    │ Prometheus  │ ──────────────────────>│   Target    │
    │   Server    │ <──────────────────────│   (앱)      │
    │             │   text/plain 응답       │             │
    └─────────────┘   (메트릭 데이터)       └─────────────┘

    이 과정이 scrape_interval (기본 15초)마다 반복된다.


Push 방식 (Datadog, InfluxDB 등)
──────────────────────────────────────────────

    ┌─────────────┐     POST /write       ┌─────────────┐
    │   Target    │ ──────────────────────>│ Monitoring  │
    │   (앱)      │                        │   Server    │
    └─────────────┘                        └─────────────┘

    앱이 직접 데이터를 보낸다.
```

Pull 방식의 실무적 장점:

- **타겟이 죽으면 바로 안다.** scrape 요청이 실패하면 `up` 메트릭이 0이 된다. Push 방식은 "데이터가 안 오는 것"이 장애인지 메트릭이 없는 건지 구분이 어렵다.
- **방화벽 설정이 단순하다.** Prometheus에서 타겟으로 나가는 방향만 열면 된다. Push 방식은 모든 앱에서 모니터링 서버로 들어오는 인바운드를 열어야 한다.
- **타겟을 교체해도 Prometheus 설정만 바꾸면 된다.** 앱 코드에 모니터링 서버 주소를 넣을 필요가 없다.

단, 단기 실행 배치 작업은 scrape 전에 종료될 수 있다. 이 경우 Pushgateway를 쓴다.

```yaml
# Pushgateway는 이렇게 등록한다
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true   # 원본 job 레이블 유지
    static_configs:
      - targets: ['pushgateway:9091']
```

### 구성 요소 정리

| 구성 요소 | 역할 | 언제 필요한가 |
|---------|------|------------|
| Prometheus Server | 메트릭 수집(scrape), 저장(TSDB), 쿼리(PromQL) 처리 | 항상 |
| Exporter | Prometheus 형식이 아닌 시스템의 메트릭을 변환해서 노출 | DB, 미들웨어 등 직접 계측 못하는 대상 |
| Pushgateway | 단기 작업의 메트릭을 임시 보관 | 배치 잡, CronJob |
| Alertmanager | 알림 라우팅, 그룹핑, 억제(silencing) | 알림이 필요할 때 |
| Service Discovery | 타겟 목록을 자동으로 갱신 | K8s, 클라우드 환경 |

## 메트릭 타입

Prometheus 메트릭은 4가지 타입이 있다.

### Counter

단조 증가하는 값. 재시작 시 0으로 리셋된다. 요청 수, 에러 수 같은 누적 값에 쓴다.

`rate()` 함수와 같이 써야 의미가 있다. Counter 값 자체는 "지금까지 총 몇 건"이라 그래프로 보면 계속 올라가기만 한다.

```
# 메트릭 예시 (텍스트 형식)
http_requests_total{method="GET", status="200"} 1027
http_requests_total{method="POST", status="500"} 3
```

### Gauge

증가/감소 가능한 현재 값. 메모리 사용량, 활성 커넥션 수, 큐 크기에 쓴다.

```
# 메트릭 예시
node_memory_MemAvailable_bytes 4.123456e+09
active_connections 42
```

### Histogram

값의 분포를 버킷별로 측정한다. 응답 시간 분포를 파악할 때 쓴다.

내부적으로 3개의 시계열이 만들어진다:

- `_bucket{le="..."}` : 각 버킷별 누적 카운트
- `_sum` : 관측값의 합계
- `_count` : 관측 횟수

```
# 메트릭 예시
http_request_duration_seconds_bucket{le="0.1"} 24054
http_request_duration_seconds_bucket{le="0.5"} 33444
http_request_duration_seconds_bucket{le="1"}   33444
http_request_duration_seconds_bucket{le="+Inf"} 33444
http_request_duration_seconds_sum 6841.3
http_request_duration_seconds_count 33444
```

주의할 점: 버킷 설정이 중요하다. 버킷이 너무 적으면 분포를 정확히 알 수 없고, 너무 많으면 카디널리티가 커진다. 대부분의 HTTP API는 `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]` 정도면 된다.

### Summary

Histogram과 비슷하지만 클라이언트 측에서 분위수를 계산한다. 서버 측에서 집계가 안 되는 게 단점이다. 여러 인스턴스의 p99를 합칠 수 없다. 대부분의 경우 Histogram을 쓰는 게 낫다.

## PromQL

### 기본 쿼리

```promql
# 현재 값 조회
http_requests_total

# 레이블 필터
http_requests_total{method="GET", status="200"}

# 정규식 필터
http_requests_total{status=~"5.."}

# 범위 벡터 (최근 5분 데이터)
http_requests_total[5m]

# 초당 증가율 (Counter에는 반드시 rate()을 써야 한다)
rate(http_requests_total[5m])
```

### 실무에서 자주 쓰는 쿼리

```promql
# 에러율 (%)
sum(rate(http_requests_total{status=~"5.."}[5m]))
/ sum(rate(http_requests_total[5m])) * 100

# P95 응답 시간
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# 메서드별 초당 요청 수 (QPS)
sum by (method) (rate(http_requests_total[5m]))

# 메모리 사용률 (%)
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# CPU 사용률 (1분 평균)
1 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m]))

# 디스크 사용률
(1 - node_filesystem_avail_bytes{mountpoint="/"} 
     / node_filesystem_size_bytes{mountpoint="/"}) * 100
```

### rate() vs irate()

```promql
# rate: 범위 전체의 평균 증가율. 알림 조건에 적합하다.
rate(http_requests_total[5m])

# irate: 마지막 두 데이터 포인트 사이의 순간 증가율. 그래프에서 스파이크를 보고 싶을 때 쓴다.
irate(http_requests_total[5m])
```

`rate()`의 범위 벡터(`[5m]`)는 scrape_interval의 4배 이상을 권장한다. scrape_interval이 15초면 최소 `[1m]`을 써야 한다.

## Recording Rules

PromQL 쿼리 중에 자주 쓰이거나 계산 비용이 큰 것은 Recording Rule로 미리 계산해둘 수 있다. Grafana 대시보드가 열릴 때마다 복잡한 쿼리를 실행하는 대신, Prometheus가 주기적으로 결과를 새 시계열로 저장한다.

```yaml
# recording_rules.yml
groups:
  - name: http_rules
    interval: 30s   # evaluation_interval과 다르게 설정 가능
    rules:
      # 서비스별 초당 요청 수
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))

      # 서비스별 에러율
      - record: job:http_errors:ratio5m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
          / sum by (job) (rate(http_requests_total[5m]))

      # P99 응답 시간
      - record: job:http_request_duration:p99
        expr: |
          histogram_quantile(0.99,
            sum by (job, le) (rate(http_request_duration_seconds_bucket[5m]))
          )
```

Recording Rule 네이밍 관례: `level:metric:operations` 형식이다. `job:http_requests:rate5m`처럼 집계 레벨, 원본 메트릭, 적용한 함수를 쓴다.

Recording Rule을 쓰면 알림 규칙에서 미리 계산된 시계열을 참조할 수 있어서 Alertmanager 평가 시간이 줄어든다.

```yaml
# alert_rules.yml에서 recording rule 참조
groups:
  - name: http_alerts
    rules:
      - alert: HighErrorRate
        expr: job:http_errors:ratio5m > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "에러율 5% 초과 (현재: {{ $value | humanizePercentage }})"
```

prometheus.yml에 rule 파일을 등록한다:

```yaml
rule_files:
  - "recording_rules.yml"
  - "alert_rules.yml"
```

## Java / Spring Boot 연동 (Micrometer)

Spring Boot 2.x 이상에서는 Micrometer가 기본 메트릭 라이브러리다. Micrometer는 JVM 메트릭, HTTP 요청, DB 커넥션 풀 같은 메트릭을 자동으로 수집한다.

### 의존성 추가

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```groovy
// build.gradle
implementation 'org.springframework.boot:spring-boot-starter-actuator'
implementation 'io.micrometer:micrometer-registry-prometheus'
```

### application.yml 설정

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus
  endpoint:
    prometheus:
      enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
    distribution:
      percentiles-histogram:
        http.server.requests: true
      sla:
        http.server.requests: 10ms, 50ms, 100ms, 200ms, 500ms
```

이렇게 설정하면 `/actuator/prometheus` 엔드포인트에서 메트릭이 노출된다.

### 자동 수집되는 메트릭

별도 코드 없이 아래 메트릭이 수집된다:

| 메트릭 | 설명 |
|-------|------|
| `jvm_memory_used_bytes` | JVM 메모리 사용량 (heap/non-heap 구분) |
| `jvm_gc_pause_seconds` | GC 일시 정지 시간 |
| `jvm_threads_live_threads` | 현재 활성 스레드 수 |
| `http_server_requests_seconds` | HTTP 요청 처리 시간 (method, uri, status별) |
| `hikaricp_connections_active` | HikariCP 활성 커넥션 수 |
| `hikaricp_connections_idle` | HikariCP 유휴 커넥션 수 |
| `system_cpu_usage` | 시스템 CPU 사용률 |
| `process_cpu_usage` | JVM 프로세스 CPU 사용률 |

### 커스텀 메트릭 등록

```java
@Component
public class OrderMetrics {

    private final Counter orderCounter;
    private final Timer orderProcessingTimer;
    private final AtomicInteger activeOrders;

    public OrderMetrics(MeterRegistry registry) {
        // Counter: 주문 건수
        this.orderCounter = Counter.builder("orders.created.total")
                .description("Total number of orders created")
                .tag("type", "online")
                .register(registry);

        // Timer: 주문 처리 시간
        this.orderProcessingTimer = Timer.builder("orders.processing.duration")
                .description("Order processing duration")
                .publishPercentileHistogram()
                .register(registry);

        // Gauge: 현재 처리 중인 주문 수
        this.activeOrders = registry.gauge("orders.active",
                new AtomicInteger(0));
    }

    public void processOrder(Order order) {
        activeOrders.incrementAndGet();
        try {
            orderProcessingTimer.record(() -> {
                // 주문 처리 로직
                doProcess(order);
            });
            orderCounter.increment();
        } finally {
            activeOrders.decrementAndGet();
        }
    }
}
```

### @Timed로 메서드 단위 측정

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @Timed(value = "api.orders.list", 
           percentiles = {0.5, 0.95, 0.99})
    @GetMapping
    public List<Order> listOrders() {
        return orderService.findAll();
    }
}
```

`@Timed`를 쓰려면 `TimedAspect` 빈이 등록돼야 한다:

```java
@Configuration
public class MetricsConfig {
    @Bean
    public TimedAspect timedAspect(MeterRegistry registry) {
        return new TimedAspect(registry);
    }
}
```

### prometheus.yml에 타겟 추가

```yaml
scrape_configs:
  - job_name: 'spring-boot-app'
    metrics_path: '/actuator/prometheus'
    scrape_interval: 15s
    static_configs:
      - targets: ['spring-app:8080']
        labels:
          env: 'production'
```

## 알림 설정

### Alertmanager 설정

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'default-slack'
  group_by: ['alertname', 'job']
  group_wait: 30s        # 같은 그룹의 알림을 모아서 보내는 대기 시간
  group_interval: 5m     # 같은 그룹의 새 알림을 보내는 간격
  repeat_interval: 4h    # 같은 알림을 반복 전송하는 간격

  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      repeat_interval: 1h

    - match_re:
        alertname: ^(DeadMansSwitch)$
      receiver: 'null'

receivers:
  - name: 'default-slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: >-
          {{ range .Alerts }}
          *{{ .Labels.severity }}* - {{ .Annotations.summary }}
          {{ end }}

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_SERVICE_KEY'

  - name: 'null'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'job']
```

`inhibit_rules`는 critical 알림이 발생하면 같은 alertname의 warning 알림을 억제한다. 알림 폭풍을 막는 데 쓴다.

### 알림 규칙

```yaml
# alert_rules.yml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: job:http_errors:ratio5m > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "에러율 5% 초과 ({{ $labels.job }})"
          description: "현재 에러율: {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le)
          ) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 응답시간 1초 초과 ({{ $labels.job }})"

      - alert: InstanceDown
        expr: up == 0
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "인스턴스 다운 ({{ $labels.instance }})"

  - name: infra
    rules:
      - alert: HighMemoryUsage
        expr: |
          (1 - node_memory_MemAvailable_bytes 
               / node_memory_MemTotal_bytes) > 0.9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "메모리 사용률 90% 초과 ({{ $labels.instance }})"

      - alert: DiskSpaceRunningLow
        expr: |
          (1 - node_filesystem_avail_bytes{mountpoint="/"} 
               / node_filesystem_size_bytes{mountpoint="/"}) > 0.85
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "디스크 사용률 85% 초과 ({{ $labels.instance }})"
```

## Service Discovery

### Kubernetes Service Discovery

K8s 환경에서는 Pod annotation으로 scrape 대상을 지정한다.

```yaml
# Pod annotation
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/actuator/prometheus"
```

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
```

### File-based Service Discovery

K8s가 아닌 환경에서는 JSON/YAML 파일로 타겟을 관리할 수 있다. 파일이 변경되면 Prometheus가 자동으로 다시 읽는다.

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s
```

```json
// /etc/prometheus/targets/apps.json
[
  {
    "targets": ["app1:8080", "app2:8080"],
    "labels": {
      "env": "production",
      "team": "backend"
    }
  }
]
```

Ansible이나 Terraform으로 인프라를 관리한다면 타겟 파일을 자동 생성하는 방식이 잘 맞는다.

## 운영

### Storage Retention

Prometheus의 로컬 TSDB는 기본적으로 15일간 데이터를 보관한다.

```bash
# 시간 기반 보관 (기본 15d)
prometheus --storage.tsdb.retention.time=30d

# 크기 기반 보관 (디스크 공간이 한정적일 때)
prometheus --storage.tsdb.retention.size=50GB

# 둘 다 설정하면 먼저 도달하는 조건으로 삭제된다
prometheus \
  --storage.tsdb.retention.time=30d \
  --storage.tsdb.retention.size=50GB
```

실무에서 디스크 용량 계산:

```
필요 디스크 = 수집 시계열 수 * scrape_interval당 샘플 크기 * 보관 기간

대략적인 기준:
- 시계열 1개당 샘플은 약 1~2 bytes (압축 후)
- 10,000개 시계열, 15초 간격, 30일 보관 시:
  10000 * (86400/15) * 30 * 1.5 bytes ≈ 2.6 GB
```

TSDB 상태는 `/api/v1/status/tsdb` 엔드포인트에서 확인할 수 있다.

### Remote Write / Remote Read

로컬 TSDB의 한계(단일 노드, 보관 기간 제한)를 넘으려면 Remote Write를 사용한다.

```yaml
# prometheus.yml
remote_write:
  - url: "http://mimir:9009/api/v1/push"
    queue_config:
      max_samples_per_send: 1000
      batch_send_deadline: 5s
      max_shards: 200
    write_relabel_configs:
      # 특정 메트릭만 remote write (비용 절감)
      - source_labels: [__name__]
        regex: "go_.*"
        action: drop

remote_read:
  - url: "http://mimir:9009/prometheus/api/v1/read"
    read_recent: false   # 최근 데이터는 로컬 TSDB에서 읽는다
```

Remote Write 대상으로 많이 쓰는 것:

| 솔루션 | 특징 |
|-------|------|
| Thanos | 사이드카 방식, S3/GCS에 장기 저장 |
| Cortex / Mimir | 멀티테넌트 지원, 수평 확장 |
| VictoriaMetrics | 리소스 효율이 좋음, 단일 바이너리로 실행 가능 |

### HA 구성

Prometheus 자체는 클러스터링을 지원하지 않는다. HA를 구성하는 방법은 두 가지다.

**방법 1: 동일한 설정의 Prometheus 2대 운영**

```
┌──────────────┐     ┌──────────────┐
│ Prometheus A │     │ Prometheus B │
│ (primary)    │     │ (replica)    │
└──────┬───────┘     └──────┬───────┘
       │                    │
       │  동일한 target을     │
       │  동일한 설정으로 scrape │
       ▼                    ▼
┌──────────────────────────────────┐
│          Alertmanager            │
│   (중복 알림 자동 dedup)           │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│           Grafana                │
│ (데이터 소스 2개 등록, 둘 다 조회)  │
└──────────────────────────────────┘
```

두 Prometheus가 같은 타겟을 수집하므로 하나가 죽어도 데이터 유실이 없다. Alertmanager는 `--cluster.peer` 플래그로 클러스터를 구성하면 중복 알림을 자동으로 제거한다.

```bash
# Alertmanager HA
alertmanager --cluster.peer=alertmanager-1:9094
alertmanager --cluster.peer=alertmanager-0:9094
```

**방법 2: Thanos 사이드카**

```
┌────────────────────┐   ┌────────────────────┐
│ Prometheus A       │   │ Prometheus B       │
│ + Thanos Sidecar   │   │ + Thanos Sidecar   │
└────────┬───────────┘   └────────┬───────────┘
         │                        │
         │   블록 업로드            │
         ▼                        ▼
    ┌─────────────────────────────────┐
    │         Object Storage          │
    │         (S3, GCS 등)            │
    └─────────────┬───────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────┐
    │        Thanos Query             │
    │  (전체 데이터를 통합 조회)         │
    └─────────────────────────────────┘
```

Thanos Query가 여러 Prometheus의 데이터를 통합해서 조회한다. 장기 보관은 Object Storage에서 처리한다.

### Federation

여러 Prometheus 서버의 메트릭을 상위 Prometheus가 수집하는 구조다. 팀별로 Prometheus를 운영하면서 글로벌 뷰가 필요할 때 쓴다.

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Prometheus   │  │ Prometheus   │  │ Prometheus   │
│ (팀 A)       │  │ (팀 B)       │  │ (팀 C)       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │ /federate 엔드포인트
                         ▼
              ┌────────────────────┐
              │ Global Prometheus  │
              │ (집계 메트릭만 수집)  │
              └────────────────────┘
```

```yaml
# Global Prometheus 설정
scrape_configs:
  - job_name: 'federation'
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job=~".+"}'                    # 모든 job의 메트릭
        - 'job:http_requests:rate5m'       # recording rule 결과만 가져오기
    static_configs:
      - targets:
          - 'prometheus-team-a:9090'
          - 'prometheus-team-b:9090'
          - 'prometheus-team-c:9090'
```

주의: Federation으로 모든 원본 메트릭을 가져오면 글로벌 Prometheus에 부하가 걸린다. Recording Rule로 집계한 결과만 가져오는 게 일반적이다.

## 설치

### Docker Compose로 전체 스택 구성

```yaml
# docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./rules:/etc/prometheus/rules
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'       # /-/reload로 설정 리로드 가능

  alertmanager:
    image: prom/alertmanager:v0.27.0
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml

  node-exporter:
    image: prom/node-exporter:v1.8.0
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'

  grafana:
    image: grafana/grafana:10.4.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  prometheus-data:
  grafana-data:
```

### 설정 리로드

`--web.enable-lifecycle` 플래그를 켜두면 재시작 없이 설정을 리로드할 수 있다.

```bash
# HTTP로 리로드
curl -X POST http://localhost:9090/-/reload

# 또는 SIGHUP 시그널
kill -HUP $(pidof prometheus)
```

## 실무에서 겪는 문제들

### 카디널리티 폭발

레이블 값의 조합이 너무 많아지면 메모리와 디스크를 빠르게 소진한다.

```
# 나쁜 예: user_id를 레이블에 넣으면 사용자 수만큼 시계열이 생긴다
http_requests_total{user_id="12345", method="GET"}  # 시계열 수 = 사용자 수 * method 수

# 좋은 예: user_id는 로그에 남기고, 메트릭은 집계 단위로 쓴다
http_requests_total{method="GET", endpoint="/api/orders"}
```

카디널리티가 높은 메트릭을 찾으려면:

```promql
# 시계열 수가 많은 메트릭 이름 상위 10개
topk(10, count by (__name__) ({__name__=~".+"}))
```

### scrape timeout

타겟이 메트릭을 생성하는 데 시간이 오래 걸리면 scrape가 실패한다.

```yaml
scrape_configs:
  - job_name: 'slow-exporter'
    scrape_interval: 60s
    scrape_timeout: 30s    # 기본값은 10s
    static_configs:
      - targets: ['slow-exporter:9100']
```

### relabel_configs 디버깅

relabel이 의도대로 동작하는지 확인하려면 Prometheus UI의 `Status > Targets` 페이지에서 타겟별 레이블을 확인한다. `metric_relabel_configs`는 scrape 후 메트릭에 적용되고, `relabel_configs`는 scrape 전 타겟에 적용된다. 순서가 헷갈리기 쉽다.

## 메트릭 네이밍 규칙

```
<namespace>_<name>_<unit>_total  (Counter는 _total 접미사 필수)
<namespace>_<name>_<unit>        (Gauge, Histogram, Summary)

예시:
http_requests_total                       # Counter
http_request_duration_seconds             # Histogram
node_memory_MemAvailable_bytes            # Gauge
process_cpu_seconds_total                 # Counter
```

단위는 기본 단위를 쓴다: seconds(milliseconds 아님), bytes(megabytes 아님).

## Prometheus vs 다른 모니터링 도구

| 항목 | Prometheus | Datadog | InfluxDB |
|------|-----------|---------|----------|
| 수집 방식 | Pull | Agent (Push) | Push |
| 비용 | 무료 (인프라 비용만) | 호스트/메트릭당 과금 | 커뮤니티 무료 / 클라우드 과금 |
| 쿼리 언어 | PromQL | 자체 쿼리 | InfluxQL / Flux |
| 장기 저장 | 외부 연동 필요 | SaaS 기본 제공 | 자체 지원 |
| K8s 연동 | 네이티브 수준 | Agent 설치 | 별도 구성 |
| 러닝커브 | PromQL 학습 필요 | 낮음 (GUI 중심) | 중간 |

## 관련 문서

- [Prometheus 메트릭 수집](../Monitoring/Prometheus_메트릭_수집.md) - Node.js prom-client 연동 상세
- [Grafana](../Monitoring/Grafana.md) - 대시보드 시각화
- [OpenTelemetry](../Monitoring/OpenTelemetry.md) - 분산 추적과의 통합
