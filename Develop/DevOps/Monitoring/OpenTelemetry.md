---
title: OpenTelemetry
tags: [devops, monitoring, observability, opentelemetry, otel, tracing, metrics, logs, jaeger, tempo, collector, kubernetes, baggage]
updated: 2026-03-26
---

# OpenTelemetry

## 개요

OpenTelemetry(OTel)는 **로그·메트릭·트레이스** 세 가지 관찰 데이터를 수집하고 내보내는 **벤더 중립적 오픈소스 표준**이다. 특정 모니터링 벤더에 종속되지 않고, 데이터를 Jaeger·Tempo·Prometheus·Datadog 등 원하는 백엔드로 보낼 수 있다.

```
수집 대상:
  Traces  — 요청이 여러 서비스를 거치는 전체 경로 추적
  Metrics — 수치 기반 상태 측정 (RPS, 오류율, 응답 시간)
  Logs    — 이벤트 기록 (OTel Logs는 기존 로거와 연동)

내보낼 수 있는 백엔드:
  Jaeger / Tempo  — 분산 트레이싱
  Prometheus      — 메트릭
  Loki            — 로그
  Datadog / Dynatrace / New Relic — 상용 APM
```

---

## 아키텍처

```
┌────────────┐   OTLP   ┌─────────────────────┐   ┌──────────┐
│  서비스 A   │ ────────▶│  OTel Collector      │──▶│  Jaeger  │
│ (Node.js)  │          │  - 수신 (OTLP)       │   └──────────┘
└────────────┘          │  - 처리 (필터/샘플링) │   ┌──────────┐
┌────────────┐   OTLP   │  - 내보내기           │──▶│Prometheus│
│  서비스 B   │ ────────▶│                      │   └──────────┘
│ (Java)     │          └─────────────────────┘   ┌──────────┐
└────────────┘                                     │   Loki   │
                                                   └──────────┘
```

---

## OTel Collector 설정

```yaml
# otel-collector.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

  # 샘플링 — 트래픽 많을 때 전체 수집하면 비용/성능 부담
  probabilistic_sampler:
    sampling_percentage: 10   # 10%만 수집 (tail-based 권장)

  # 민감 정보 제거
  attributes:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: db.statement
        action: hash   # SQL 해시 처리

  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  prometheus:
    endpoint: "0.0.0.0:8889"

  loki:
    endpoint: http://loki:3100/loki/api/v1/push

  # 디버깅용
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, probabilistic_sampler]
      exporters: [otlp/jaeger]

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loki]
```

---

## Collector 운영 — Gateway vs Agent 모드

Collector를 어떤 모드로 배포하느냐에 따라 운영 방식이 완전히 달라진다.

### Agent 모드

각 서비스(또는 노드)마다 Collector를 하나씩 붙인다. 서비스와 같은 호스트에서 돌아가므로 네트워크 지연이 없다.

```
┌──────────────────────────────┐
│ Node 1                       │
│  ┌─────────┐  ┌───────────┐  │
│  │ 서비스 A │──│ Collector │──│──▶ 백엔드
│  └─────────┘  │ (Agent)   │  │
│               └───────────┘  │
└──────────────────────────────┘
```

- 서비스가 localhost로 데이터를 보내면 되니까 설정이 단순하다
- 노드별로 Collector가 있어서 한 노드의 Collector가 죽어도 다른 노드에 영향 없음
- 노드 수만큼 Collector가 뜨니까 리소스 총량은 커진다

### Gateway 모드

중앙에 Collector 클러스터를 두고, 모든 서비스가 여기로 데이터를 보낸다.

```
┌─────────┐
│ 서비스 A │──┐
└─────────┘  │   ┌───────────────┐
┌─────────┐  ├──▶│ Collector     │──▶ 백엔드
│ 서비스 B │──┤   │ (Gateway)     │
└─────────┘  │   │ - LB 뒤에 배포│
┌─────────┐  │   └───────────────┘
│ 서비스 C │──┘
└─────────┘
```

- 라우팅, 필터링, 샘플링 같은 처리를 한 곳에서 관리할 수 있다
- tail-based 샘플링은 같은 trace의 span이 한 곳에 모여야 하므로 Gateway에서 하는 게 맞다
- Gateway가 죽으면 모든 텔레메트리 데이터가 유실된다. 반드시 HA 구성 필요

### 실제로는 둘 다 쓴다

프로덕션에서는 Agent + Gateway 2단 구조를 많이 쓴다.

```
서비스 → Agent Collector (로컬) → Gateway Collector (중앙) → 백엔드
```

Agent에서 배치 처리와 기본 필터링을 하고, Gateway에서 tail 샘플링과 라우팅을 담당한다. Agent에서 `otlp` exporter로 Gateway 주소를 잡아주면 된다.

```yaml
# Agent Collector — exporter만 Gateway를 가리키면 됨
exporters:
  otlp/gateway:
    endpoint: otel-gateway.monitoring.svc.cluster.local:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/gateway]
```

### 스케일링 시 주의점

**Gateway 스케일링**에서 가장 많이 실수하는 부분은 tail-based 샘플링이다. 같은 trace의 span이 여러 Gateway 인스턴스에 흩어지면 일부 span만 보고 샘플링 결정을 내린다. 이를 방지하려면 `load_balancing` exporter를 Agent에 설정해서 같은 trace ID의 span이 같은 Gateway로 가게 해야 한다.

```yaml
# Agent Collector — trace ID 기반 로드밸런싱
exporters:
  loadbalancing:
    protocol:
      otlp:
        tls:
          insecure: true
    resolver:
      dns:
        hostname: otel-gateway-headless.monitoring.svc.cluster.local
        port: 4317
```

### Collector 디버깅

문제가 생겼을 때 확인하는 순서:

**1. debug exporter 켜기** — 데이터가 들어오는지 확인

```yaml
exporters:
  debug:
    verbosity: detailed    # basic → normal → detailed 순으로 상세

service:
  pipelines:
    traces:
      exporters: [debug, otlp/jaeger]  # 기존 exporter와 함께 추가
```

**2. zpages 확인** — Collector 내부 상태를 웹으로 볼 수 있다

```yaml
extensions:
  zpages:
    endpoint: 0.0.0.0:55679

service:
  extensions: [zpages]
```

`http://localhost:55679/debug/tracez`로 접속하면 Collector가 처리 중인 span 정보가 나온다. `pipelinez`에서는 파이프라인 상태를 확인할 수 있다.

**3. 내부 메트릭 확인** — Collector 자체의 Prometheus 메트릭

```yaml
service:
  telemetry:
    metrics:
      address: 0.0.0.0:8888
```

`otelcol_receiver_accepted_spans`, `otelcol_exporter_sent_spans` 같은 메트릭으로 데이터가 어디서 막히는지 파악한다. accepted는 있는데 sent가 0이면 exporter 쪽 문제다.

---

## Node.js 계측

### 설치

```bash
npm install \
  @opentelemetry/sdk-node \
  @opentelemetry/api \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-http \
  @opentelemetry/exporter-metrics-otlp-http
```

### 초기화 (앱 진입점 최상단)

```typescript
// tracing/setup.ts — 반드시 앱보다 먼저 임포트
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { Resource } from '@opentelemetry/resources';
import { SEMRESATTRS_SERVICE_NAME, SEMRESATTRS_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';

const sdk = new NodeSDK({
  resource: new Resource({
    [SEMRESATTRS_SERVICE_NAME]: process.env.SERVICE_NAME ?? 'api',
    [SEMRESATTRS_SERVICE_VERSION]: process.env.APP_VERSION ?? '1.0.0',
    'deployment.environment': process.env.NODE_ENV ?? 'development',
  }),

  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://otel-collector:4318/v1/traces',
  }),

  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://otel-collector:4318/v1/metrics',
    }),
    exportIntervalMillis: 10_000,
  }),

  // Express, HTTP, pg, ioredis, kafkajs 등 자동 계측
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs': { enabled: false }, // 파일 시스템 노이즈 제거
    }),
  ],
});

sdk.start();

process.on('SIGTERM', () => sdk.shutdown());

// index.ts
import './tracing/setup';  // 반드시 첫 번째 import
import express from 'express';
// ...
```

### 커스텀 Span — 비즈니스 로직 추적

```typescript
import { trace, SpanStatusCode, context, propagation } from '@opentelemetry/api';

const tracer = trace.getTracer('payment-service', '1.0.0');

async function processPayment(orderId: string, amount: number): Promise<PaymentResult> {
  return tracer.startActiveSpan('payment.process', async (span) => {
    // Span 속성 (Jaeger에서 검색 가능)
    span.setAttributes({
      'order.id': orderId,
      'payment.amount': amount,
      'payment.currency': 'KRW',
    });

    try {
      // 중첩 Span — 하위 작업 추적
      const result = await tracer.startActiveSpan('payment.gateway.charge', async (childSpan) => {
        childSpan.setAttribute('gateway', 'stripe');
        const r = await stripeClient.charge(orderId, amount);
        childSpan.setStatus({ code: SpanStatusCode.OK });
        childSpan.end();
        return r;
      });

      span.setStatus({ code: SpanStatusCode.OK });
      span.setAttribute('payment.transaction_id', result.transactionId);
      return result;

    } catch (err) {
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: (err as Error).message,
      });
      span.recordException(err as Error);
      throw err;
    } finally {
      span.end();
    }
  });
}
```

### 컨텍스트 전파 — 서비스 간 트레이스 연결

```typescript
// 발신 서비스: HTTP 헤더에 트레이스 컨텍스트 주입
import { context, propagation } from '@opentelemetry/api';

async function callDownstreamService(url: string) {
  const headers: Record<string, string> = {};
  propagation.inject(context.active(), headers);
  // → headers에 'traceparent', 'tracestate' 자동 추가

  const response = await fetch(url, { headers });
  return response.json();
}

// 수신 서비스: 헤더에서 컨텍스트 추출 (자동 계측이 처리)
// Express instrumentation이 자동으로 traceparent 헤더를 읽어
// 부모 Span과 연결함 → Jaeger에서 전체 흐름 확인 가능
```

---

## Trace-Log 연동

Jaeger에서 트레이스를 보다가 "이 span에서 뭐가 찍혔지?" 할 때, 로그에 trace ID가 없으면 로그를 시간대로 뒤져야 한다. trace ID를 로그에 박아두면 Grafana에서 트레이스 → 로그로 바로 점프할 수 있다.

### Winston에 trace ID 주입

```typescript
import winston from 'winston';
import { trace, context } from '@opentelemetry/api';

// trace 컨텍스트를 로그에 추가하는 포맷
const traceFormat = winston.format((info) => {
  const span = trace.getSpan(context.active());
  if (span) {
    const spanContext = span.spanContext();
    info.trace_id = spanContext.traceId;
    info.span_id = spanContext.spanId;
    info.trace_flags = spanContext.traceFlags;
  }
  return info;
});

const logger = winston.createLogger({
  format: winston.format.combine(
    traceFormat(),
    winston.format.timestamp(),
    winston.format.json(),
  ),
  transports: [new winston.transports.Console()],
});

// 사용 — 별도 작업 없이 trace context가 자동으로 들어감
logger.info('결제 처리 시작', { orderId: 'ORD-123', amount: 50000 });
// 출력:
// {
//   "message": "결제 처리 시작",
//   "orderId": "ORD-123",
//   "amount": 50000,
//   "trace_id": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
//   "span_id": "1a2b3c4d5e6f7a8b",
//   "trace_flags": 1,
//   "timestamp": "2026-03-26T10:30:00.000Z"
// }
```

### Pino에 trace ID 주입

pino는 mixin 옵션으로 더 깔끔하게 처리된다.

```typescript
import pino from 'pino';
import { trace, context } from '@opentelemetry/api';

const logger = pino({
  mixin() {
    const span = trace.getSpan(context.active());
    if (!span) return {};

    const { traceId, spanId, traceFlags } = span.spanContext();
    return { trace_id: traceId, span_id: spanId, trace_flags: traceFlags };
  },
});

// Express 미들웨어에서 사용하면 요청 단위로 trace가 자동 연결됨
app.use((req, res, next) => {
  req.log = logger;  // pino-http 쓰면 이 과정 필요 없음
  next();
});
```

### Grafana에서 Trace → Log 연결

Loki에 로그를 보내고 있다면, Grafana 데이터소스 설정에서 Tempo와 Loki를 연결한다.

```
Tempo 데이터소스 설정:
  Trace to logs:
    Data source: Loki
    Tags: trace_id → trace_id
    Filter by span ID: span_id

Loki 데이터소스 설정:
  Derived fields:
    Name: TraceID
    Regex: "trace_id":"(\w+)"
    Internal link → Tempo
```

이 설정이 끝나면 Tempo에서 트레이스를 클릭했을 때 "Logs for this span" 버튼이 생기고, Loki 로그에서 trace ID를 클릭하면 Tempo 트레이스로 이동한다.

### 주의할 점

- trace context는 `sdk.start()` 이후에만 존재한다. SDK 초기화 전에 찍은 로그에는 trace ID가 빈 값이다
- 비동기 작업에서 context가 유실되는 경우가 있다. `setTimeout`, `setInterval` 안에서 로그를 찍으면 trace ID가 없을 수 있는데, `context.with(context.active(), () => { ... })`로 컨텍스트를 명시적으로 전달해야 한다
- JSON 로그 포맷을 써야 한다. 텍스트 포맷이면 Loki에서 trace_id 필드를 파싱할 수 없다

---

## OTel Metrics API — prom-client 대체

prom-client를 쓰면 Prometheus에 종속된다. OTel Metrics API로 메트릭을 생성하면 Prometheus, Datadog, OTLP 어디든 보낼 수 있다. 이미 OTel SDK를 쓰고 있다면 prom-client를 별도로 관리할 이유가 없다.

### Counter — 누적값 (요청 수, 에러 수)

```typescript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('payment-service', '1.0.0');

const paymentCounter = meter.createCounter('payment.count', {
  description: '결제 처리 횟수',
  unit: '1',
});

const paymentErrorCounter = meter.createCounter('payment.error.count', {
  description: '결제 실패 횟수',
  unit: '1',
});

async function processPayment(orderId: string, method: string) {
  try {
    await executePayment(orderId);
    paymentCounter.add(1, { method, status: 'success' });
  } catch (err) {
    paymentCounter.add(1, { method, status: 'failure' });
    paymentErrorCounter.add(1, { method, error_type: (err as Error).name });
    throw err;
  }
}
```

### Histogram — 분포값 (응답 시간, 요청 크기)

```typescript
const paymentDuration = meter.createHistogram('payment.duration', {
  description: '결제 처리 소요 시간',
  unit: 'ms',
});

async function processPayment(orderId: string) {
  const start = performance.now();
  try {
    const result = await executePayment(orderId);
    return result;
  } finally {
    paymentDuration.record(performance.now() - start, {
      method: 'card',
    });
  }
}
```

### Gauge — 현재 상태값 (큐 크기, 커넥션 수)

OTel에서 gauge는 `ObservableGauge`로, 콜백 방식으로 동작한다. 값을 직접 set하는 게 아니라 수집 시점에 콜백이 호출된다.

```typescript
const activeConnections = meter.createObservableGauge('db.connections.active', {
  description: '현재 활성 DB 커넥션 수',
  unit: '1',
});

activeConnections.addCallback((result) => {
  result.observe(pool.totalCount, { state: 'total' });
  result.observe(pool.idleCount, { state: 'idle' });
  result.observe(pool.waitingCount, { state: 'waiting' });
});
```

### UpDownCounter — 증감하는 값 (동시 처리 수)

gauge와 비슷하지만, 이벤트 기반으로 값을 올리고 내린다.

```typescript
const activeJobs = meter.createUpDownCounter('worker.active_jobs', {
  description: '현재 처리 중인 작업 수',
  unit: '1',
});

async function handleJob(job: Job) {
  activeJobs.add(1, { queue: job.queue });
  try {
    await processJob(job);
  } finally {
    activeJobs.add(-1, { queue: job.queue });
  }
}
```

### prom-client에서 마이그레이션할 때

| prom-client | OTel Metrics API |
|---|---|
| `new Counter({ name, help })` | `meter.createCounter(name, { description })` |
| `counter.inc(1)` | `counter.add(1)` |
| `new Histogram({ name, buckets })` | `meter.createHistogram(name)` |
| `histogram.observe(value)` | `histogram.record(value)` |
| `new Gauge({ name })` | `meter.createObservableGauge(name)` |
| `gauge.set(value)` | `addCallback((r) => r.observe(value))` |
| `/metrics` 엔드포인트 | Collector의 prometheus exporter가 노출 |

prom-client에서는 `/metrics` 엔드포인트를 서비스에서 직접 노출했지만, OTel에서는 Collector의 prometheus exporter가 이 역할을 한다. 서비스 코드에 메트릭 엔드포인트를 만들 필요가 없다.

---

## Baggage — 서비스 간 키-값 전달

Baggage는 서비스 간 호출에서 임의의 키-값 쌍을 전달하는 메커니즘이다. trace context와 함께 전파되지만, trace에 기록되는 건 아니다. "이 요청은 어떤 사용자의 것" 같은 정보를 downstream 서비스에 알려줄 때 쓴다.

### 사용법

```typescript
import { propagation, context, ROOT_CONTEXT, BaggageEntry } from '@opentelemetry/api';

// 1. Baggage 설정 — 보통 API Gateway나 첫 번째 서비스에서
function setRequestBaggage(userId: string, tenantId: string) {
  const baggage = propagation.createBaggage({
    'user.id': { value: userId },
    'tenant.id': { value: tenantId },
    'request.priority': { value: 'high' },
  });
  return propagation.setBaggage(context.active(), baggage);
}

// Express 미들웨어 예시
app.use((req, res, next) => {
  const ctx = setRequestBaggage(req.user.id, req.user.tenantId);
  context.with(ctx, () => next());
});

// 2. Baggage 읽기 — downstream 서비스 어디서든
function getRequestBaggage() {
  const baggage = propagation.getBaggage(context.active());
  if (!baggage) return null;

  return {
    userId: baggage.getEntry('user.id')?.value,
    tenantId: baggage.getEntry('tenant.id')?.value,
  };
}

// downstream 서비스에서
app.get('/internal/process', (req, res) => {
  const { userId, tenantId } = getRequestBaggage();
  // userId, tenantId를 사용해서 처리
});
```

### Baggage를 Span 속성으로 복사

Baggage 값은 Jaeger에 자동으로 안 찍힌다. Span에서 검색하고 싶으면 명시적으로 속성에 복사해야 한다.

```typescript
import { trace, context, propagation } from '@opentelemetry/api';

function copyBaggageToSpanAttributes() {
  const span = trace.getSpan(context.active());
  const baggage = propagation.getBaggage(context.active());

  if (span && baggage) {
    for (const [key, entry] of baggage.getAllEntries()) {
      span.setAttribute(`baggage.${key}`, entry.value);
    }
  }
}
```

### 주의사항

- **Baggage는 HTTP 헤더로 전파된다.** 값이 커지면 모든 HTTP 요청의 헤더가 커진다. 큰 데이터를 넣으면 안 된다. 키-값 합쳐서 수백 바이트 이내로 유지해야 한다
- **외부 서비스에도 전파된다.** W3C Baggage 스펙을 따르므로 외부 API 호출 시에도 `baggage` 헤더가 나간다. 민감 정보(토큰, PII)를 절대 넣으면 안 된다
- **Baggage는 trace와 독립적이다.** 샘플링되지 않은 요청에도 Baggage는 전파된다. 트레이스 수집 여부와 관계없이 downstream에서 읽을 수 있다
- `W3CBaggagePropagator`가 기본으로 등록돼 있어야 한다. `NodeSDK` 기본 설정에 포함되어 있지만, propagator를 직접 설정한 경우 빠뜨리기 쉽다

---

## Java (Spring Boot) 계측

```xml
<!-- pom.xml: OTel Java Agent 사용 (코드 수정 없음) -->
```

```bash
# JVM 시작 시 Java Agent 추가 — 코드 수정 없이 자동 계측
java \
  -javaagent:/opt/opentelemetry-javaagent.jar \
  -Dotel.service.name=order-service \
  -Dotel.exporter.otlp.endpoint=http://otel-collector:4317 \
  -Dotel.exporter.otlp.protocol=grpc \
  -Dotel.traces.sampler=parentbased_traceidratio \
  -Dotel.traces.sampler.arg=0.1 \
  -jar app.jar
```

```yaml
# application.yaml
management:
  tracing:
    sampling:
      probability: 0.1  # Spring Boot 3 + Micrometer Tracing
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
```

---

## Docker Compose 환경 구성

```yaml
# docker-compose.yaml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    volumes:
      - ./otel-collector.yaml:/etc/otel-collector.yaml
    command: ["--config=/etc/otel-collector.yaml"]
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8889:8889"   # Prometheus metrics 노출

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686" # Jaeger UI
      - "4317:4317"   # OTLP gRPC (collector → jaeger)
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yaml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
    volumes:
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
```

---

## Kubernetes 배포

### DaemonSet 패턴 — 노드당 1개 Collector

모든 노드에 Collector가 하나씩 배포된다. 같은 노드의 Pod들이 로컬 Collector로 데이터를 보낸다.

```yaml
# otel-collector-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-collector-agent
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: otel-collector-agent
  template:
    metadata:
      labels:
        app: otel-collector-agent
    spec:
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.96.0
          args: ["--config=/etc/otel/config.yaml"]
          ports:
            - containerPort: 4317  # gRPC
              hostPort: 4317
            - containerPort: 4318  # HTTP
              hostPort: 4318
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: config
              mountPath: /etc/otel
      volumes:
        - name: config
          configMap:
            name: otel-agent-config
---
# 서비스 Pod에서 Collector 접근 — 환경변수로 노드 IP 사용
# env:
#   - name: NODE_IP
#     valueFrom:
#       fieldRef:
#         fieldPath: status.hostIP
#   - name: OTEL_EXPORTER_OTLP_ENDPOINT
#     value: "http://$(NODE_IP):4317"
```

**DaemonSet을 쓰는 경우:**
- 노드 수가 적고 고정적일 때 (10~50대)
- 서비스 수가 많아서 sidecar를 일일이 붙이기 번거로울 때
- 노드 레벨 메트릭(kubelet 등)도 같이 수집하고 싶을 때

### Sidecar 패턴 — Pod당 1개 Collector

각 서비스 Pod에 Collector 컨테이너를 sidecar로 같이 띄운다.

```yaml
# 서비스 Deployment에 sidecar 추가
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      containers:
        # 메인 애플리케이션
        - name: app
          image: payment-service:latest
          env:
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://localhost:4317"  # sidecar는 localhost
          ports:
            - containerPort: 8080

        # OTel Collector sidecar
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:0.96.0
          args: ["--config=/etc/otel/config.yaml"]
          ports:
            - containerPort: 4317
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
          volumeMounts:
            - name: otel-config
              mountPath: /etc/otel
      volumes:
        - name: otel-config
          configMap:
            name: otel-sidecar-config
```

**Sidecar를 쓰는 경우:**
- 서비스별로 다른 Collector 설정이 필요할 때 (서비스별 샘플링 비율 등)
- 서비스 간 텔레메트리 격리가 중요할 때 (멀티테넌트)
- 서비스 수가 적고 각각 설정이 다를 때

### Gateway Deployment

중앙 Gateway는 일반 Deployment + HPA로 배포한다.

```yaml
# otel-collector-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector-gateway
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector-gateway
  template:
    metadata:
      labels:
        app: otel-collector-gateway
    spec:
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.96.0
          args: ["--config=/etc/otel/config.yaml"]
          ports:
            - containerPort: 4317
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2
              memory: 4Gi
          volumeMounts:
            - name: config
              mountPath: /etc/otel
      volumes:
        - name: config
          configMap:
            name: otel-gateway-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-gateway
  namespace: monitoring
spec:
  ports:
    - port: 4317
      targetPort: 4317
      name: grpc
  selector:
    app: otel-collector-gateway
---
# tail sampling 쓸 때 headless service 필요 (load_balancing exporter용)
apiVersion: v1
kind: Service
metadata:
  name: otel-gateway-headless
  namespace: monitoring
spec:
  clusterIP: None
  ports:
    - port: 4317
      targetPort: 4317
  selector:
    app: otel-collector-gateway
```

### 패턴 선택 기준

```
DaemonSet:
  - 노드당 리소스 고정 → 예측 가능한 비용
  - 노드 수가 많으면 낭비 (트래픽 없는 노드에도 Collector가 뜸)
  - hostPort 사용 → 서비스가 노드 IP로 접근

Sidecar:
  - 서비스별 독립 설정 가능
  - Pod 수에 비례해 리소스 증가 → 서비스가 많으면 오버헤드
  - localhost 접근 → 네트워크 설정 단순

실무에서 많이 쓰는 조합:
  DaemonSet (Agent) + Deployment (Gateway)
  → Agent가 노드에서 수집, Gateway가 중앙에서 처리/라우팅
```

---

## 샘플링

```
트레이스 전체 수집 시 문제:
  - 초당 1,000 RPS → 하루 86,400,000 트레이스 → 스토리지 비용 폭증
  - 99%는 정상 요청 → 분석 가치 낮음

Head-based (앞단 결정):
  - 요청 시작 시 수집 여부 결정
  - 구현 단순, 오류 요청도 미수집될 수 있음
  - 예: 10% 무작위 수집

Tail-based (뒷단 결정, 권장):
  - 요청 완료 후 오류·느린 요청 기준으로 결정
  - OTel Collector의 tail_sampling processor 사용
  - 오류(5xx)는 100%, 정상은 1~5% 수집
```

```yaml
# Tail-based 샘플링 예시 (otel-collector.yaml)
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors-policy
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow-policy
        type: latency
        latency: {threshold_ms: 1000}
      - name: sampling-policy
        type: probabilistic
        probabilistic: {sampling_percentage: 5}
```

---

## 주요 지표

| 신호 | 확인 방법 | 주요 활용 |
|------|----------|----------|
| Traces | Jaeger UI / Grafana Tempo | 어느 서비스에서 느려지는가? |
| Metrics | Grafana + Prometheus | RPS, 오류율, P95 응답 시간 |
| Logs | Grafana Loki | 특정 요청의 상세 로그 |
| Trace + Log 연결 | Trace ID를 로그에 포함 | 트레이스에서 로그로 바로 이동 |

---

## 실무 트러블슈팅

### SDK 초기화 순서 문제

가장 흔한 실수다. OTel SDK는 **다른 모든 모듈보다 먼저** 초기화해야 한다. HTTP, Express, pg 같은 라이브러리가 먼저 import되면 자동 계측이 걸리지 않는다.

```typescript
// 잘못된 예 — express가 먼저 로드돼서 자동 계측 실패
import express from 'express';
import './tracing/setup';

// 맞는 예
import './tracing/setup';
import express from 'express';
```

ESM(import)을 쓰면 import 순서와 실제 실행 순서가 다를 수 있다. Node.js는 ESM을 정적 분석 후 실행하기 때문에, `--require` 또는 `--import` 플래그로 강제 선행 로드하는 게 확실하다.

```bash
# CommonJS
node --require ./tracing/setup.js app.js

# ESM (Node.js 18.19+)
node --import ./tracing/setup.mjs app.js
```

ts-node나 tsx를 쓸 때도 마찬가지다.

```bash
# ts-node
node --require ts-node/register --require ./tracing/setup.ts app.ts

# tsx
node --import tsx --import ./tracing/setup.ts app.ts
```

### Span이 안 보일 때

Jaeger에서 서비스는 뜨는데 span이 하나도 없거나 일부만 보이는 경우.

**1. span.end()를 호출하지 않았다**

```typescript
// end() 빠뜨리면 span이 export되지 않는다
tracer.startActiveSpan('my-operation', (span) => {
  doSomething();
  // span.end(); ← 이걸 빼먹으면 Jaeger에 안 나옴
});
```

`startActiveSpan` 콜백이 Promise를 반환하면 await 없이 지나가면서 finally 블록이 나중에 실행되는 경우도 있다. async 함수는 반드시 await 해야 한다.

**2. 비동기 컨텍스트 유실**

`context.active()`가 빈 컨텍스트를 반환하면 부모 span과 연결이 안 된다.

```typescript
// 잘못된 예 — setTimeout 안에서 context 유실
tracer.startActiveSpan('parent', (span) => {
  setTimeout(() => {
    // 여기서 context.active()는 ROOT_CONTEXT
    tracer.startActiveSpan('child', (child) => {
      child.end();
    });
  }, 100);
  span.end();
});

// 맞는 예 — context를 명시적으로 전달
tracer.startActiveSpan('parent', (span) => {
  const ctx = context.active();
  setTimeout(() => {
    context.with(ctx, () => {
      tracer.startActiveSpan('child', (child) => {
        child.end();
      });
    });
  }, 100);
  span.end();
});
```

**3. 샘플링에 걸려서 안 보이는 것**

`AlwaysOnSampler`로 바꿔서 확인해보면 된다.

```typescript
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';

const sdk = new NodeSDK({
  sampler: new AlwaysOnSampler(), // 디버깅 시에만
  // ...
});
```

### Collector 메모리 초과 (OOMKill)

Collector가 자꾸 재시작되면 대부분 메모리 부족이다.

**1. memory_limiter 설정 확인**

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 400            # 컨테이너 limit의 80% 수준
    spike_limit_mib: 100      # 급증 허용 범위
    # limit에 도달하면 데이터를 드롭한다. 유실되는 것.
```

`limit_mib`는 컨테이너의 memory limit보다 낮아야 한다. 컨테이너 limit이 512Mi면 `limit_mib: 400` 정도로 잡는다. 나머지는 Go 런타임과 버퍼용.

**2. batch processor 튜닝**

```yaml
processors:
  batch:
    send_batch_size: 512        # 기본값 8192는 너무 큼
    send_batch_max_size: 1024
    timeout: 1s
```

`send_batch_size`가 크면 메모리에 많은 span을 들고 있어야 한다. 트래픽이 급증하면 이게 OOM의 원인이 된다.

**3. tail_sampling의 메모리 사용**

tail sampling은 `decision_wait` 시간 동안 모든 span을 메모리에 보관한다. `decision_wait: 30s`에 초당 10,000 span이면 300,000개의 span이 메모리에 쌓인다.

```yaml
processors:
  tail_sampling:
    decision_wait: 10s    # 30s → 10s로 줄이면 메모리 사용량 1/3
    num_traces: 50000     # 동시에 보관하는 trace 수 제한
```

### Exporter 연결 실패

```
2024/03/26 10:30:00 exporter/otlp: failed to export: rpc error: connection refused
```

이 에러가 계속 뜨면:

- Collector → 백엔드 연결을 확인한다. DNS 해석이 되는지, 포트가 맞는지
- TLS 설정을 확인한다. 백엔드가 TLS를 쓰는데 `insecure: true`로 보내거나, 그 반대인 경우
- `retry_on_failure` 설정으로 일시적 장애에 대응한다

```yaml
exporters:
  otlp/backend:
    endpoint: tempo.monitoring.svc.cluster.local:4317
    tls:
      insecure: true
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 5000     # 메모리와 트레이드오프
```

### gRPC vs HTTP 선택

서비스 → Collector 구간에서 어떤 프로토콜을 쓸지 헷갈릴 때:

- **gRPC (4317)**: 바이너리 직렬화로 페이로드가 작고 빠르다. Collector 간 통신이나 같은 클러스터 내에서 쓴다
- **HTTP (4318)**: 프록시, 로드밸런서를 거쳐야 할 때. ALB는 gRPC를 지원하지만 설정이 필요하다. 디버깅 시 curl로 테스트할 수 있어 편하다

```bash
# HTTP로 Collector에 테스트 데이터 보내기
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"test"}}]},"scopeSpans":[{"spans":[{"traceId":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4","spanId":"1a2b3c4d5e6f7a8b","name":"test-span","kind":1,"startTimeUnixNano":"1700000000000000000","endTimeUnixNano":"1700000001000000000"}]}]}]}'
```
