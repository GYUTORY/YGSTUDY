---
title: 분산 추적 및 Observability (OpenTelemetry / Jaeger / Prometheus / Grafana)
tags: [distributed-tracing, opentelemetry, jaeger, zipkin, prometheus, grafana, observability]
updated: 2026-04-01
---

# 분산 추적 및 Observability

## 왜 로그만으로는 부족한가

마이크로서비스 환경에서 하나의 API 요청이 5~10개 서비스를 거치는 건 흔한 일이다. 장애가 터졌을 때 로그만 보면, 각 서비스별로 로그를 열어서 시간대를 맞추고 요청 흐름을 머릿속으로 재구성해야 한다. 서비스가 3개만 넘어가도 이 작업은 현실적이지 않다.

Observability는 로그(Log), 메트릭(Metric), 트레이스(Trace) 세 가지 신호를 조합해서 시스템 내부 상태를 파악하는 것이다. 세 가지 역할이 다르다.

| 신호 | 역할 | 예시 |
|------|------|------|
| 로그 | 특정 이벤트의 상세 기록 | `payment timeout, orderId=ORD-123` |
| 메트릭 | 시간에 따른 수치 변화 | 요청 수, 에러율, 응답 시간 p99 |
| 트레이스 | 요청 하나의 전체 경로와 소요 시간 | order-service -> payment-service -> notification-service |

장애 대응 흐름은 보통 이렇다:
1. 메트릭 알림이 먼저 온다 (에러율 급등, 응답 시간 증가)
2. 트레이스로 어떤 서비스 구간에서 느려졌는지 찾는다
3. 해당 서비스 로그에서 구체적인 에러 원인을 확인한다

세 가지 중 하나만 있으면 장애 원인 파악에 시간이 오래 걸린다.

---

## Trace와 Span 개념

### Trace

하나의 요청이 시스템을 통과하는 전체 경로다. 고유한 trace ID가 부여되고, 이 ID가 서비스 간 전파된다. HTTP 헤더나 메시지 큐 메타데이터에 실려서 다음 서비스로 넘어간다.

### Span

Trace 안에서 각 서비스가 수행한 작업 단위다. 하나의 Trace는 여러 Span으로 구성된다.

```
Trace (trace_id: abc-123)
├── Span: API Gateway (12ms)
│   ├── Span: order-service.createOrder (45ms)
│   │   ├── Span: DB query - insert order (8ms)
│   │   └── Span: payment-service.charge (320ms)  ← 여기서 느림
│   │       └── Span: PG사 API 호출 (310ms)
│   └── Span: notification-service.send (15ms)
```

각 Span에는 시작 시간, 종료 시간, 상태(OK/ERROR), 태그(attributes)가 붙는다. 장애 시 Span 트리를 보면 어디서 시간을 잡아먹었는지 바로 보인다.

### Span 간 관계

Span은 parent-child 관계를 갖는다. order-service가 payment-service를 호출하면, order-service의 Span이 parent, payment-service의 Span이 child가 된다. 이 관계가 있어야 트리 구조로 시각화할 수 있다.

---

## OpenTelemetry

### OpenTelemetry가 필요한 이유

예전에는 Jaeger용 SDK, Zipkin용 SDK, Prometheus 클라이언트를 각각 붙여야 했다. 백엔드를 바꾸려면 계측 코드를 전부 수정해야 했다. OpenTelemetry(OTel)는 계측 코드와 백엔드를 분리한다. 한 번 계측하면 Jaeger든 Zipkin이든 Datadog이든 설정만 바꿔서 보낼 수 있다.

### 구성 요소

**SDK**: 애플리케이션 코드에 넣는 라이브러리. Trace, Metric, Log를 생성한다.

**Exporter**: 생성된 데이터를 특정 백엔드로 보내는 역할. OTLP, Jaeger, Zipkin, Prometheus 등의 포맷을 지원한다.

**Collector**: 애플리케이션과 백엔드 사이에 두는 중간 프록시. 데이터를 받아서 가공하고 원하는 곳으로 보낸다. 필수는 아니지만, 운영 환경에서는 거의 항상 쓴다.

```
[서비스 A] ──OTLP──→ [OTel Collector] ──→ [Jaeger] (트레이스)
[서비스 B] ──OTLP──→ [OTel Collector] ──→ [Prometheus] (메트릭)
[서비스 C] ──OTLP──→ [OTel Collector] ──→ [Elasticsearch] (로그)
```

### Spring Boot에서 OpenTelemetry 적용

Spring Boot 3.x 기준으로 자동 계측(auto-instrumentation)을 사용하면 코드 수정 없이 트레이스가 생성된다.

**의존성 추가 (build.gradle)**

```groovy
implementation 'io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter:2.11.0'
```

**application.yml 설정**

```yaml
otel:
  service:
    name: order-service
  exporter:
    otlp:
      endpoint: http://otel-collector:4317
  traces:
    exporter: otlp
  metrics:
    exporter: otlp
  logs:
    exporter: otlp
```

이 설정만으로 HTTP 요청, JDBC 쿼리, RestTemplate/WebClient 호출에 대한 Span이 자동 생성된다.

**수동으로 Span 추가가 필요한 경우**

자동 계측은 프레임워크 레벨의 호출만 잡는다. 비즈니스 로직 내부에서 구간을 나눠서 보고 싶으면 수동 계측을 추가한다.

```java
@Service
public class OrderService {

    private final Tracer tracer;

    public OrderService(Tracer tracer) {
        this.tracer = tracer;
    }

    public Order createOrder(OrderRequest request) {
        Span span = tracer.spanBuilder("validate-stock")
            .setAttribute("orderId", request.getOrderId())
            .startSpan();

        try (Scope scope = span.makeCurrent()) {
            stockService.validate(request.getItems());
        } catch (Exception e) {
            span.setStatus(StatusCode.ERROR, e.getMessage());
            span.recordException(e);
            throw e;
        } finally {
            span.end();
        }

        // 이후 로직...
    }
}
```

`span.makeCurrent()`를 빠뜨리면 하위 호출에서 생성되는 Span이 이 Span의 child로 잡히지 않는다. 실수하기 쉬운 부분이다.

### Node.js에서 OpenTelemetry 적용

```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');

const sdk = new NodeSDK({
  serviceName: 'payment-service',
  traceExporter: new OTLPTraceExporter({
    url: 'http://otel-collector:4317',
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

이 코드는 애플리케이션 진입점(index.js 등) 최상단에 위치해야 한다. 다른 모듈이 먼저 로드되면 자동 계측이 제대로 동작하지 않는다.

---

## OpenTelemetry Collector 구성

Collector를 직접 띄우면 애플리케이션에서 백엔드로 직접 보내는 것보다 여러 가지 이점이 있다.

- 애플리케이션이 백엔드 장애에 영향받지 않는다
- 샘플링, 필터링, 배치 처리를 Collector에서 처리한다
- 백엔드를 바꿀 때 애플리케이션 재배포가 필요 없다

**otel-collector-config.yaml**

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true
  prometheus:
    endpoint: 0.0.0.0:8889
  logging:
    loglevel: warn

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

`memory_limiter`는 반드시 넣는다. 트래픽이 갑자기 몰리면 Collector가 OOM으로 죽을 수 있다. processors 배열에서 `memory_limiter`를 `batch` 앞에 둬야 메모리 초과 시 데이터를 먼저 드롭한다.

### Docker Compose로 전체 스택 구성

```yaml
version: '3.8'
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # gRPC
      - "4318:4318"   # HTTP
      - "8889:8889"   # Prometheus metrics

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317"         # OTLP gRPC

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Jaeger로 분산 추적 조회

### Jaeger vs Zipkin

둘 다 분산 추적 백엔드인데, 실무에서 Jaeger를 더 많이 본다.

- Jaeger: CNCF 졸업 프로젝트. Cassandra, Elasticsearch 스토리지 지원. 대규모 환경에 적합
- Zipkin: 가볍고 설정이 간단. MySQL 스토리지도 지원. 소규모 환경이나 빠르게 도입할 때 편함

둘 다 OpenTelemetry에서 데이터를 받을 수 있으니, 나중에 바꾸는 것도 가능하다.

### Jaeger UI에서 트레이스 분석

Jaeger UI(`http://localhost:16686`)에서 할 수 있는 것:

**서비스별 트레이스 검색**: 서비스 이름, 시간 범위, 최소 소요 시간 등으로 필터링한다. 느린 요청만 골라서 볼 때 유용하다.

**Span 트리 확인**: 하나의 트레이스를 선택하면 Span 트리가 나온다. 각 Span의 소요 시간이 바 차트로 표시되어서 병목 구간을 바로 찾을 수 있다.

**서비스 간 의존성 그래프**: 실제 호출 관계를 기반으로 서비스 간 연결을 시각화한다. 문서에 적힌 아키텍처와 실제 호출이 다른 경우를 발견할 때가 있다.

### Trace ID로 특정 요청 추적

장애 대응 시 가장 자주 하는 작업이다.

1. 에러 로그에서 trace ID를 가져온다

```
2026-04-01 11:23:45 ERROR [order-service] payment failed, traceId=7a3f2c1b9e4d
```

2. Jaeger UI 상단 검색창에 trace ID를 입력한다
3. 해당 요청의 전체 호출 체인이 나온다

이게 되려면 로그에 trace ID가 찍혀 있어야 한다. Spring Boot에서 OpenTelemetry를 쓰면 MDC에 `trace_id`, `span_id`가 자동으로 들어간다.

**logback-spring.xml**

```xml
<pattern>
  %d{yyyy-MM-dd HH:mm:ss} %-5level [%thread] [%X{trace_id}] %logger{36} - %msg%n
</pattern>
```

이 설정이 빠져 있으면 로그와 트레이스를 연결할 수 없다. 운영 환경에서 나중에 추가하면 기존 로그는 trace ID가 없어서 추적이 안 된다. 초기 세팅 때 넣어야 한다.

---

## 메트릭 수집: Prometheus + Grafana

### Prometheus 기본 구조

Prometheus는 Pull 방식이다. 각 서비스가 `/metrics` 엔드포인트를 열어두면 Prometheus가 주기적으로 가져간다.

**prometheus.yml**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']

  - job_name: 'order-service'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['order-service:8080']

  - job_name: 'payment-service'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['payment-service:8080']
```

서비스가 동적으로 늘어나는 환경(Kubernetes 등)에서는 `static_configs` 대신 서비스 디스커버리를 쓴다.

```yaml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

### 핵심 메트릭

서비스마다 수백 개의 메트릭이 나오지만, 장애 대응에서 실제로 보는 건 몇 개 안 된다.

**RED 메트릭** (요청 기준):
- **R**ate: 초당 요청 수
- **E**rror: 에러율
- **D**uration: 응답 시간 (p50, p95, p99)

**USE 메트릭** (인프라 기준):
- **U**tilization: CPU, 메모리 사용률
- **S**aturation: 큐 대기, 스레드풀 포화도
- **E**rrors: 시스템 에러 (디스크 full, OOM 등)

### Grafana 대시보드 구성

Grafana에서 Prometheus를 데이터 소스로 연결하고, 대시보드를 만든다.

**자주 쓰는 PromQL 쿼리**

에러율 (5분 기준):

```promql
sum(rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m]))
/
sum(rate(http_server_request_duration_seconds_count[5m]))
```

응답 시간 p99:

```promql
histogram_quantile(0.99, 
  sum(rate(http_server_request_duration_seconds_bucket[5m])) by (le, service_name)
)
```

서비스별 초당 요청 수:

```promql
sum(rate(http_server_request_duration_seconds_count[5m])) by (service_name)
```

### 알림 설정

Grafana에서 알림 규칙을 설정한다. Prometheus의 Alertmanager를 직접 쓸 수도 있다.

실무에서 자주 거는 알림:

- 에러율 5% 초과 (5분 지속)
- p99 응답 시간 3초 초과 (5분 지속)
- 서비스 인스턴스 다운 (1분 이상 scrape 실패)

알림 임계값을 너무 낮게 잡으면 알림 피로가 온다. 처음에는 넉넉하게 잡고, 운영하면서 줄여 나간다.

---

## Observability 3요소 연계

로그, 메트릭, 트레이스가 각각 존재하면 의미가 반감된다. 세 가지를 연결해야 장애 대응 속도가 올라간다.

### 연결 고리: Trace ID

핵심은 trace ID다. 트레이스에도 있고, 로그에도 찍히고, 메트릭의 exemplar에도 들어갈 수 있다.

```
[메트릭 알림] → 에러율 급등 감지
       ↓
[Grafana] → 해당 시간대의 exemplar에서 trace ID 확인
       ↓
[Jaeger] → trace ID로 호출 체인 확인, 병목 서비스 특정
       ↓
[로그] → 해당 서비스의 trace ID로 필터링, 에러 원인 확인
```

### Exemplar 설정

Prometheus 메트릭에 trace ID를 exemplar로 붙이면 Grafana에서 메트릭 그래프의 특정 데이터 포인트를 클릭했을 때 바로 Jaeger 트레이스로 이동할 수 있다.

Prometheus 설정에서 exemplar 지원을 활성화한다:

```yaml
global:
  scrape_interval: 15s
  
storage:
  exemplars:
    max_exemplars: 100000
```

Grafana에서 Prometheus 데이터 소스 설정 시 `Exemplars` 섹션에서 Jaeger 데이터 소스와 연결한다. `traceID` 레이블 이름을 매핑하면 된다.

### Grafana에서 데이터 소스 연결

Grafana는 여러 데이터 소스를 한 화면에서 볼 수 있다는 게 핵심이다.

- **Prometheus**: 메트릭 대시보드
- **Jaeger**: 트레이스 조회
- **Elasticsearch/Loki**: 로그 검색

Grafana Explore 탭에서 trace ID를 기준으로 세 가지를 오가면서 확인할 수 있다. Loki를 로그 백엔드로 쓰면 로그에서 trace ID를 클릭해서 바로 Jaeger로 넘어가는 것도 된다.

---

## 장애 대응 실제 흐름

구체적인 시나리오로 정리한다.

### 시나리오: 주문 API 응답 시간 급증

**1단계: 알림 수신**

Grafana 알림이 온다. "order-service p99 응답 시간 5초 초과, 5분 지속"

**2단계: 대시보드 확인**

Grafana 대시보드에서 order-service의 메트릭을 본다.
- 에러율은 정상
- p99만 급등, p50은 정상 → 일부 요청만 느린 상황

**3단계: 느린 트레이스 샘플링**

Jaeger에서 order-service를 선택하고, `minDuration=3s`로 필터링한다. 느린 요청들의 트레이스를 몇 개 열어본다.

**4단계: 병목 구간 특정**

Span 트리를 보니 `payment-service.charge` Span이 4초 이상 걸린다. 그 하위의 `PG사 API 호출` Span이 원인이다.

**5단계: 로그 확인**

payment-service 로그에서 해당 trace ID로 검색한다.

```
traceId=7a3f2c1b9e4d | payment gateway connection pool exhausted, 
active=50, waiting=23
```

커넥션 풀이 고갈된 것이다. PG사 API 응답이 느려지면서 커넥션이 반환되지 않고, 대기 중인 요청이 쌓인 것.

**6단계: 조치**

- 단기: payment-service 커넥션 풀 사이즈 증가, timeout 단축
- 중기: circuit breaker 설정 검토
- 장기: PG사 API 장애 시 대체 경로(fallback) 구현

이 과정이 메트릭 → 트레이스 → 로그 순서로 자연스럽게 이어진다. 세 가지가 연결되어 있지 않으면 각 단계에서 수동으로 시간대와 서비스를 맞춰가며 찾아야 한다.

---

## 샘플링

운영 환경에서 모든 요청을 트레이스하면 데이터 양이 감당이 안 된다. 샘플링으로 조절한다.

### Head-based 샘플링

요청이 들어올 때 트레이스 여부를 결정한다. 간단하지만, 에러가 발생한 요청이 샘플링에서 빠질 수 있다.

```yaml
# Collector 설정
processors:
  probabilistic_sampler:
    sampling_percentage: 10  # 10%만 수집
```

### Tail-based 샘플링

요청이 완료된 후에 결정한다. 에러가 발생하거나 느린 요청은 무조건 수집하고, 정상 요청만 샘플링할 수 있다.

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: error-policy
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: latency-policy
        type: latency
        latency:
          threshold_ms: 1000
      - name: probabilistic-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 5
```

Tail-based 샘플링은 Collector에서 Span을 모아야 하기 때문에 메모리를 더 쓴다. `decision_wait`를 너무 짧게 잡으면 아직 도착하지 않은 Span이 빠질 수 있고, 너무 길게 잡으면 메모리가 부족해진다. 10~30초 사이에서 시작하는 게 적당하다.

---

## 운영 시 주의사항

### trace ID 전파가 끊기는 경우

- 메시지 큐(Kafka, RabbitMQ)를 거치면 자동 전파가 안 된다. 메시지 헤더에 trace context를 명시적으로 넣어야 한다
- 비동기 스레드풀에서 실행되는 작업은 context가 전파되지 않는다. OpenTelemetry의 Context Propagation API를 써서 수동으로 전달해야 한다
- 외부 서비스(PG사, 택배사 API 등)는 trace context를 이해하지 못한다. 외부 호출 Span은 만들 수 있지만, 외부 서비스 내부는 추적할 수 없다

### 카디널리티 문제

Span attribute에 사용자 ID, 주문 ID 같은 고유 값을 넣으면 Jaeger 스토리지 인덱스가 폭발한다. 태그 기반 검색 성능이 떨어지고, 디스크 사용량이 급격히 늘어난다.

trace에서 개별 요청을 추적하는 건 trace ID로 하면 되기 때문에, Span attribute에는 서비스 이름, HTTP 메서드, 상태 코드 등 카디널리티가 낮은 값만 넣는다. 특정 주문의 트레이스를 찾고 싶으면 로그에서 주문 ID로 trace ID를 먼저 찾고, 그 trace ID로 Jaeger에서 검색하는 방식이 맞다.

### Collector 장애 대비

Collector가 SPOF(단일 장애점)가 되면 안 된다.

- Collector를 최소 2대 이상 띄우고, 앞에 로드밸런서를 둔다
- 애플리케이션 SDK에서 Collector 연결이 실패해도 요청 처리에 영향이 없도록 확인한다. OpenTelemetry SDK는 기본적으로 비동기로 데이터를 보내기 때문에 Collector가 죽어도 애플리케이션이 멈추지는 않는다. 다만 SDK 내부 버퍼가 차면 트레이스 데이터가 유실된다

### 비용

트레이스 데이터는 양이 많다. 서비스 10개, 초당 1000 요청이면 하루에 수천만 건의 Span이 쌓인다.

- 스토리지 보존 기간을 정한다. 트레이스는 보통 7~14일이면 충분하다
- Tail-based 샘플링으로 정상 요청의 수집 비율을 낮춘다
- 관리형 서비스(Datadog, AWS X-Ray 등)를 쓰면 편하지만, Span 단위로 과금하기 때문에 비용을 미리 계산해야 한다
