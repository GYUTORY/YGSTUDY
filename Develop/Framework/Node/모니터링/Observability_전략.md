---
title: Node.js Observability 전략
tags: [framework, node, observability, metrics, tracing, logging, prometheus, opentelemetry]
updated: 2026-03-08
---

# Node.js Observability 전략

## 개요

Observability(관찰 가능성)는 시스템의 내부 상태를 외부 출력(로그, 메트릭, 트레이스)으로 파악할 수 있는 능력이다. 장애가 발생했을 때 "뭐가 잘못됐는지"를 빠르게 파악하려면 세 가지가 갖춰져 있어야 한다.

```
Observability의 세 기둥:
  Logs    — 무슨 일이 일어났는가? (이벤트 기록)
  Metrics — 얼마나 자주/빠르게 일어났는가? (수치)
  Traces  — 어디서 느려졌는가? (요청 흐름 추적)
```

---

## 1. Logging

### 구조화된 로그 (JSON)

```typescript
// utils/logger.ts
import winston from 'winston';

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL ?? 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()           // JSON 형태로 출력 → 검색/집계 용이
  ),
  defaultMeta: {
    service: process.env.SERVICE_NAME ?? 'api',
    environment: process.env.NODE_ENV ?? 'development',
  },
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
  ],
});
```

### 요청 로깅 미들웨어

```typescript
// middleware/requestLogger.ts
import { Request, Response, NextFunction } from 'express';
import { v4 as uuid } from 'uuid';
import { logger } from '../utils/logger';

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const requestId = uuid();
  const startTime = Date.now();

  req.headers['x-request-id'] = requestId;
  res.setHeader('x-request-id', requestId);

  res.on('finish', () => {
    const duration = Date.now() - startTime;
    logger.info('HTTP Request', {
      requestId,
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      duration,
      userAgent: req.get('user-agent'),
      ip: req.ip,
    });
  });

  next();
}
```

### 로그 레벨 가이드

| 레벨 | 용도 | 예시 |
|------|------|------|
| `error` | 즉시 대응 필요 | 예외 발생, DB 연결 실패 |
| `warn` | 주의 필요 | 재시도 발생, 사용 중단 예정 API |
| `info` | 정상 흐름 기록 | 요청 처리 완료, 서비스 시작 |
| `debug` | 개발/디버깅용 | 변수 값, 내부 상태 |

---

## 2. Metrics

### Prometheus + prom-client

```typescript
// metrics/index.ts
import { Registry, Counter, Histogram, Gauge, collectDefaultMetrics } from 'prom-client';

export const registry = new Registry();

// 기본 Node.js 메트릭 수집 (CPU, 메모리, GC 등)
collectDefaultMetrics({ register: registry });

// HTTP 요청 카운터
export const httpRequestTotal = new Counter({
  name: 'http_requests_total',
  help: '전체 HTTP 요청 수',
  labelNames: ['method', 'route', 'status_code'],
  registers: [registry],
});

// 요청 처리 시간
export const httpRequestDuration = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP 요청 처리 시간 (초)',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.01, 0.05, 0.1, 0.3, 0.5, 1, 2, 5],
  registers: [registry],
});

// 현재 활성 연결 수
export const activeConnections = new Gauge({
  name: 'active_connections',
  help: '현재 활성 연결 수',
  registers: [registry],
});

// DB 쿼리 처리 시간
export const dbQueryDuration = new Histogram({
  name: 'db_query_duration_seconds',
  help: 'DB 쿼리 처리 시간',
  labelNames: ['operation', 'table'],
  buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1],
  registers: [registry],
});
```

### 메트릭 미들웨어

```typescript
// middleware/metrics.ts
import { Request, Response, NextFunction } from 'express';
import { httpRequestTotal, httpRequestDuration } from '../metrics';

export function metricsMiddleware(req: Request, res: Response, next: NextFunction) {
  const end = httpRequestDuration.startTimer();

  res.on('finish', () => {
    const route = (req.route?.path ?? req.path) as string;
    const labels = {
      method: req.method,
      route,
      status_code: String(res.statusCode),
    };
    httpRequestTotal.inc(labels);
    end(labels);
  });

  next();
}
```

### /metrics 엔드포인트

```typescript
// app.ts
import { registry } from './metrics';

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', registry.contentType);
  res.end(await registry.metrics());
});
```

---

## 3. Distributed Tracing

### OpenTelemetry 설정

```typescript
// tracing/setup.ts (앱 진입점 최상단에서 import)
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { ExpressInstrumentation } from '@opentelemetry/instrumentation-express';
import { PgInstrumentation } from '@opentelemetry/instrumentation-pg';
import { RedisInstrumentation } from '@opentelemetry/instrumentation-redis';

const sdk = new NodeSDK({
  serviceName: process.env.SERVICE_NAME ?? 'api',
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://localhost:4318/v1/traces',
  }),
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
    new PgInstrumentation(),
    new RedisInstrumentation(),
  ],
});

sdk.start();
```

### 커스텀 Span

```typescript
import { trace, SpanStatusCode } from '@opentelemetry/api';

const tracer = trace.getTracer('payment-service');

async function processPayment(orderId: string, amount: number): Promise<void> {
  return tracer.startActiveSpan('processPayment', async (span) => {
    span.setAttributes({
      'order.id': orderId,
      'payment.amount': amount,
    });

    try {
      await paymentGateway.charge(orderId, amount);
      span.setStatus({ code: SpanStatusCode.OK });
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

---

## 헬스체크 엔드포인트

```typescript
// routes/health.ts
import { Router } from 'express';
import { dataSource } from '../database';
import redis from '../cache/redis';

const router = Router();

router.get('/health', async (req, res) => {
  const checks = await Promise.allSettled([
    dataSource.query('SELECT 1'),     // DB 연결 확인
    redis.ping(),                      // Redis 연결 확인
  ]);

  const [db, cache] = checks;

  const status = checks.every(c => c.status === 'fulfilled') ? 'ok' : 'degraded';

  res.status(status === 'ok' ? 200 : 503).json({
    status,
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    checks: {
      database: db.status === 'fulfilled' ? 'ok' : 'error',
      redis: cache.status === 'fulfilled' ? 'ok' : 'error',
    },
  });
});

export default router;
```

---

## 알람 설정 기준 (Prometheus Rules 예시)

```yaml
groups:
  - name: api-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status_code=~"5.."}[5m])
          / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "5xx 에러율 5% 초과"

      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 응답 시간 1초 초과"

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes > 500 * 1024 * 1024
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "메모리 사용량 500MB 초과"
```

---

## 핵심 지표 대시보드 구성

| 지표 | 의미 | 임계치 기준 |
|------|------|------|
| P95/P99 응답 시간 | 느린 요청 탐지 | P95 < 500ms |
| 에러율 | 서비스 안정성 | < 1% |
| RPS (초당 요청) | 트래픽 현황 | 기준선 대비 급변 주의 |
| DB 쿼리 시간 | 병목 탐지 | P95 < 100ms |
| 메모리 사용량 | 누수 탐지 | 점진적 증가 주의 |
| Active Connections | 연결 고갈 탐지 | 최대치의 80% 경고 |
