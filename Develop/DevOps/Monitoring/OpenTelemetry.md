---
title: OpenTelemetry 실무 가이드
tags: [devops, monitoring, observability, opentelemetry, otel, tracing, metrics, logs, jaeger, tempo]
updated: 2026-03-08
---

# OpenTelemetry 실무 가이드

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

## 샘플링 전략

```
트레이스 전체 수집 시 문제:
  - 초당 1,000 RPS → 하루 86,400,000 트레이스 → 스토리지 비용 폭증
  - 99%는 정상 요청 → 분석 가치 낮음

샘플링 전략:

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
