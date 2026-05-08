---
title: Node.js Observability 전략
tags: [framework, node, observability, metrics, tracing, logging, prometheus, opentelemetry]
updated: 2026-05-08
---

# Node.js Observability 전략

## 개요

Observability(관찰 가능성)는 시스템 내부 상태를 외부 출력(로그, 메트릭, 트레이스)으로 파악하는 능력이다. 장애가 났을 때 "뭐가 잘못됐는지"를 빠르게 알아내려면 세 가지가 모두 갖춰져 있어야 한다.

```
Observability의 세 기둥:
  Logs    — 무슨 일이 일어났는가? (이벤트 기록)
  Metrics — 얼마나 자주/빠르게 일어났는가? (수치)
  Traces  — 어디서 느려졌는가? (요청 흐름 추적)
```

세 기둥이 따로 놀면 의미가 반감된다. 알람이 울려서 메트릭 대시보드를 보면 P99이 튀었다는 사실은 알 수 있지만, "그 시각에 어떤 요청들이 느렸는지"는 모른다. 트레이스를 보면 느린 요청은 찾는데, 그 요청 안에서 무슨 로그가 찍혔는지 모른다. 결국 세 데이터를 `trace_id` 하나로 엮어야 디버깅이 끝난다. 이 문서는 단순히 셋을 따로 설정하는 방법이 아니라, 셋을 어떻게 한 줄로 꿰는지를 다룬다.

---

## 1. Three Pillars 상관관계

### trace_id를 로그에 주입한다

OpenTelemetry SDK가 활성화되면 현재 활성 Span의 `trace_id`와 `span_id`를 가져올 수 있다. 로그를 찍을 때 이 값을 같이 박아주면, Loki나 Elasticsearch에서 로그를 검색하다가 `trace_id` 클릭 한 번으로 Tempo/Jaeger의 트레이스로 점프할 수 있다.

```typescript
// utils/logger.ts (pino 기반)
import pino from 'pino';
import { trace, context } from '@opentelemetry/api';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  base: {
    service: process.env.SERVICE_NAME ?? 'api',
    env: process.env.NODE_ENV ?? 'development',
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  // 모든 로그에 현재 Span의 trace_id 자동 주입
  mixin() {
    const span = trace.getSpan(context.active());
    if (!span) return {};
    const { traceId, spanId, traceFlags } = span.spanContext();
    return { trace_id: traceId, span_id: spanId, trace_flags: traceFlags };
  },
});
```

`mixin`은 로그가 찍힐 때마다 호출돼서 추가 필드를 합쳐주는 훅이다. 활성 Span이 없으면 빈 객체를 반환해서 로그에 trace 필드가 안 붙는다. 이게 중요한 이유는 SDK가 아직 시작 안 된 부트스트랩 단계 로그까지 깔끔하게 처리되기 때문이다.

### AsyncLocalStorage로 요청 컨텍스트 전파

Express 미들웨어에서 `requestId`, `userId`를 잡았다고 해서 그 값을 모든 함수에 인자로 넘기는 건 비현실적이다. Node 14부터 들어온 `AsyncLocalStorage`를 쓰면 비동기 콜체인 안에서 컨텍스트를 자동으로 따라가게 만들 수 있다.

```typescript
// context/requestContext.ts
import { AsyncLocalStorage } from 'node:async_hooks';

type RequestContext = {
  requestId: string;
  userId?: string;
  ip?: string;
};

export const requestContext = new AsyncLocalStorage<RequestContext>();

export function getRequestContext(): RequestContext | undefined {
  return requestContext.getStore();
}
```

```typescript
// middleware/contextMiddleware.ts
import { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'node:crypto';
import { requestContext } from '../context/requestContext';

export function contextMiddleware(req: Request, res: Response, next: NextFunction) {
  const ctx = {
    requestId: (req.header('x-request-id') as string) ?? randomUUID(),
    userId: (req as any).user?.id,
    ip: req.ip,
  };
  res.setHeader('x-request-id', ctx.requestId);
  // run() 안에서 호출되는 모든 비동기 코드는 ctx에 접근 가능
  requestContext.run(ctx, () => next());
}
```

logger의 mixin도 여기서 값을 꺼내 쓰게 만들면 모든 로그에 `requestId`가 자동으로 박힌다.

```typescript
mixin() {
  const span = trace.getSpan(context.active());
  const reqCtx = requestContext.getStore();
  return {
    ...(span ? { trace_id: span.spanContext().traceId, span_id: span.spanContext().spanId } : {}),
    ...(reqCtx ?? {}),
  };
}
```

주의할 점이 있다. `setImmediate`, `setTimeout`, Promise 콜백은 `AsyncLocalStorage`가 자동으로 따라가지만, EventEmitter 기반 코드(특히 일부 라이브러리의 reuse된 connection)에서는 컨텍스트가 끊긴다. BullMQ Job worker나 Kafka consumer 같은 곳에서 컨텍스트가 사라지는 문제는 뒤에서 따로 다룬다.

---

## 2. Logging

### winston 대신 pino를 쓴다

처음에는 winston으로 시작했다가 P99이 비정상적으로 튀는 현상을 추적해보면, JSON 직렬화에 시간이 꽤 잡아먹히는 경우가 있다. 벤치마크 기준으로 pino가 winston보다 5~10배 정도 빠르다. 이유는 두 가지다.

- pino는 기본적으로 worker thread에 직렬화·전송을 위임할 수 있어 메인 스레드를 막지 않는다(`pino.transport`).
- pino는 자식 logger를 만들어 컨텍스트를 미리 직렬화해두고 재사용한다.

초당 수천 건 이상 로그가 찍히는 서비스라면 차이가 체감된다. 작은 서비스에서도 굳이 winston을 고집할 이유가 없다. 다만 winston이 가진 transports 생태계가 더 넓어서, 특수한 출력처(예: 사내 syslog 서버)가 필요하면 winston을 써야 할 때도 있다.

### pino 기본 설정

```typescript
// utils/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  base: { service: 'api', pid: process.pid },
  timestamp: pino.stdTimeFunctions.isoTime,
  // 운영 환경에서는 별도 transport(=worker thread)로 stdout 처리 위임
  ...(process.env.NODE_ENV === 'production'
    ? {
        transport: {
          target: 'pino/file',
          options: { destination: 1 }, // 1 = stdout
        },
      }
    : {
        transport: { target: 'pino-pretty', options: { colorize: true } },
      }),
});
```

운영에서 `pino-pretty`를 쓰면 다시 메인 스레드에서 직렬화가 일어나 성능 이점을 잃는다. 개발 환경에서만 적용한다.

### 동기 로깅이 이벤트 루프를 막는다

`process.stdout.write`는 콘솔이 TTY일 때는 동기, 파이프(컨테이너 환경 stdout)일 때는 비동기다. 그런데 로그를 파일에 직접 쓰려고 `fs.writeSync`를 쓴 코드를 본 적이 있다. 한 번에 수 KB짜리 stack trace가 찍히면 그 동안 이벤트 루프가 멈춘다. P99이 갑자기 100ms씩 튀길래 strace로 확인했더니 write 시스템콜에서 막혀 있었다. pino transport나 stdout으로 넘긴 후 fluent-bit/Vector가 파일로 떨구는 구조가 정답이다.

### 요청 로깅 미들웨어

```typescript
// middleware/requestLogger.ts
import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const startTime = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - startTime;
    logger.info(
      {
        method: req.method,
        path: req.route?.path ?? req.path,
        status: res.statusCode,
        duration_ms: duration,
        ua: req.get('user-agent'),
      },
      'http_request'
    );
  });

  next();
}
```

Express의 `req.url`은 쿼리스트링까지 포함해서 그대로 찍으면 카디널리티가 폭발한다. `req.route?.path`(예: `/users/:id`)를 쓰는 게 핵심이다. 이 얘기는 메트릭 절에서 더 다룬다.

### 로그 수집 파이프라인

세 가지 조합이 흔하다.

| 조합 | 특징 | 운영 부담 |
|------|------|------|
| Pino → stdout → Promtail → Loki | 가장 가볍다. Grafana에서 바로 LogQL로 검색 | Loki 설정 단순, Promtail은 K8s DaemonSet로 끝 |
| Pino → stdout → Vector → ClickHouse/Loki | Vector가 라우팅·변환·샘플링까지 가능 | Vector config가 다소 까다롭다 |
| Pino → stdout → Fluent Bit → Elasticsearch | 검색 강력, 한국어 분석기 활용 가능 | ES 운영 비용·복잡도 큼 |

쿠버네티스라면 컨테이너 stdout이 노드 파일에 쌓이고 그걸 Promtail/Fluent Bit이 tail해서 보낸다. 앱에서 직접 네트워크로 쏘지 마라. Loki/ES가 죽으면 앱까지 영향받는다.

Vector를 쓸 때 자주 쓰는 패턴 하나.

```toml
# vector.toml
[sources.app_logs]
type = "kubernetes_logs"

# trace_id 없는 INFO 로그는 1/10만 통과시킴 (샘플링)
[transforms.sample_info]
type = "filter"
inputs = ["app_logs"]
condition = '''
  .level != "info" || exists(.trace_id) || random_float(0.0, 1.0) < 0.1
'''

[sinks.loki]
type = "loki"
inputs = ["sample_info"]
endpoint = "http://loki:3100"
labels.app = "{{ kubernetes.pod_labels.app }}"
labels.namespace = "{{ kubernetes.namespace }}"
```

에러나 trace_id가 박힌 로그는 100% 보내고, 그 외 INFO 로그만 10%로 줄이는 식이다. 로그 비용이 부담스러울 때 쓰는 흔한 절약법이다.

---

## 3. Metrics

### Prometheus + prom-client

```typescript
// metrics/index.ts
import { Registry, Counter, Histogram, Gauge, collectDefaultMetrics } from 'prom-client';

export const registry = new Registry();
collectDefaultMetrics({ register: registry, prefix: 'nodejs_' });

export const httpRequestTotal = new Counter({
  name: 'http_requests_total',
  help: '전체 HTTP 요청 수',
  labelNames: ['method', 'route', 'status_code'],
  registers: [registry],
});

export const httpRequestDuration = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP 요청 처리 시간 (초)',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [registry],
});
```

### 카디널리티 폭발 문제

라벨에 `user_id`를 넣었다가 사고 친 적이 있다. 사용자가 10만 명이면 메트릭 시리즈가 10만 개 × 메서드 × 경로 × 상태코드만큼 곱해진다. Prometheus가 6시간 만에 OOM으로 죽었고, 새벽에 호출됐다. 그 뒤로 라벨 룰이 명확해졌다.

라벨에 절대 들어가면 안 되는 것:
- `user_id`, `session_id`, `request_id` 같은 사용자 단위 식별자
- 쿼리 파라미터 원문, 검색어
- IP 주소(특히 NAT 안 거친 클라이언트 IP)
- timestamp, UUID, 자동 증가 ID

라벨에 들어가도 되는 것:
- HTTP method (GET/POST/...): 10개 미만
- 정규화된 라우트 경로 (`/users/:id`): 라우트 수만큼
- 상태 코드 (200/404/500/...): 수십 개
- region, instance, version: 운영 차원 라벨

라우트 정규화가 핵심이다. Express면 `req.route?.path`를 쓰는데, 매칭 안 된 경로(404)에서는 `req.route`가 undefined라 `req.path` 원문이 들어간다. 봇이 `/wp-admin/index.php` 같은 걸 두드리면 그게 그대로 시리즈로 박힌다.

```typescript
// middleware/metrics.ts
import { Request, Response, NextFunction } from 'express';
import { httpRequestTotal, httpRequestDuration } from '../metrics';

export function metricsMiddleware(req: Request, res: Response, next: NextFunction) {
  const end = httpRequestDuration.startTimer();

  res.on('finish', () => {
    // 라우트 미매칭 요청은 'unknown'으로 묶어 카디널리티 차단
    const route = req.route?.path ?? (res.statusCode === 404 ? 'unknown' : req.path);
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

운영 중에 카디널리티를 모니터링하는 쿼리도 알아두면 좋다.

```promql
# 메트릭별 시리즈 개수 상위 10개
topk(10, count by (__name__)({__name__=~".+"}))

# 특정 메트릭의 라벨 값 폭발 감지
count(count by (route) (http_requests_total))
```

라우트 수가 1000개를 넘어가면 라벨에 뭔가 잘못 들어간 거다.

### Histogram bucket 잘못 잡으면 P99이 거짓말한다

`buckets: [0.1, 0.5, 1, 5]`처럼 듬성듬성 잡았다고 하자. 대부분 요청이 50ms에 끝나는 서비스에서는 0.1초 이하 버킷이 하나뿐이라 P99이 50ms든 99ms든 똑같이 100ms로 보고된다. 반대로 1초 넘게 걸리는 요청이 늘어나도 5초 버킷 안이면 다 5초로 처리되어 SLO 위반이 가려진다.

기준은 두 가지다.

- 실제 응답시간 분포의 중간값(median) 주변에 버킷을 촘촘히 둔다.
- SLO 임계치(예: 500ms)를 버킷 경계로 반드시 포함시킨다.

```typescript
// 일반 API 서버에 잘 맞는 기본값
buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
```

SLO가 500ms라면 0.5가 경계로 들어가 있어야 `histogram_quantile(0.99, ...) > 0.5`로 정확하게 판정된다.

### Node.js 특화 메트릭

`collectDefaultMetrics`가 잡아주는 것 외에 직접 추가해야 할 게 있다. 그중 가장 중요한 게 Event Loop Lag다.

```typescript
// metrics/nodejs.ts
import { monitorEventLoopDelay } from 'node:perf_hooks';
import { Gauge } from 'prom-client';
import { registry } from './index';

const histogram = monitorEventLoopDelay({ resolution: 20 });
histogram.enable();

export const eventLoopLagP50 = new Gauge({
  name: 'nodejs_event_loop_lag_p50_seconds',
  help: 'Event loop lag P50',
  registers: [registry],
  collect() {
    this.set(histogram.percentile(50) / 1e9);
  },
});

export const eventLoopLagP99 = new Gauge({
  name: 'nodejs_event_loop_lag_p99_seconds',
  help: 'Event loop lag P99',
  registers: [registry],
  collect() {
    this.set(histogram.percentile(99) / 1e9);
  },
});

export const activeHandles = new Gauge({
  name: 'nodejs_active_handles_total',
  help: 'Active handles count (sockets, timers, etc.)',
  registers: [registry],
  collect() {
    this.set((process as any)._getActiveHandles().length);
  },
});

export const activeRequests = new Gauge({
  name: 'nodejs_active_requests_total',
  help: 'Active async requests count',
  registers: [registry],
  collect() {
    this.set((process as any)._getActiveRequests().length);
  },
});

export const heapUsed = new Gauge({
  name: 'nodejs_heap_used_bytes',
  help: 'V8 heap used',
  registers: [registry],
  collect() {
    const m = process.memoryUsage();
    this.set(m.heapUsed);
  },
});
```

Event Loop Lag P99이 50ms를 넘으면 동기 작업으로 루프가 막힌다는 신호다. CPU 바운드 작업(JSON 파싱, 큰 배열 정렬, bcrypt)이 메인 스레드에서 도는지 의심해야 한다. Active Handles는 천천히 증가하면 connection leak일 가능성이 크다. setInterval을 clearInterval 안 하고 두는 코드, keep-alive socket을 닫지 않는 코드 등이 흔한 원인이다.

`_getActiveHandles`/`_getActiveRequests`는 비공개 API라 메이저 버전 업그레이드 때 깨질 수 있다. Node 22 기준으로는 동작하고, 같은 정보를 OS에서 가져오려면 `lsof` 떠야 해서 현장에서 그냥 쓴다.

### RED와 USE

메트릭을 설계할 때 머리가 복잡해지면 두 모델로 정리하면 깔끔하다.

RED는 서비스(요청 처리하는 모든 것)에 적용한다.

- Rate: 초당 요청 수
- Errors: 초당 실패 수 (또는 에러율)
- Duration: 응답 시간 분포

USE는 리소스(CPU, 메모리, 디스크, 네트워크 인터페이스)에 적용한다.

- Utilization: 사용률 (CPU 70%, 메모리 60% 같은)
- Saturation: 대기열·큐 (Run queue 길이, swap 사용량)
- Errors: 하드웨어/커널 단 오류 (NIC drop, 디스크 I/O error)

Node.js 앱 한 대 기준으로 보면:

| 모델 | 대상 | 메트릭 |
|------|------|------|
| RED | HTTP API | `http_requests_total`, `http_requests_total{status=~"5.."}`, `http_request_duration_seconds` |
| RED | DB 호출 | `db_query_duration_seconds`, `db_query_errors_total` |
| RED | 외부 API | `outbound_http_duration_seconds`, `outbound_http_errors_total` |
| USE | CPU | `process_cpu_seconds_total`, `nodejs_event_loop_lag_p99_seconds` |
| USE | 메모리 | `nodejs_heap_used_bytes`, `process_resident_memory_bytes` |
| USE | DB 커넥션 풀 | `db_pool_active`, `db_pool_waiting` (대기 큐 = saturation) |

대시보드를 RED 패널과 USE 패널로 나눠 두면 장애 대응 때 어디부터 봐야 할지 흐트러지지 않는다.

---

## 4. SLI / SLO / Error Budget

SLO는 "99.9% 가용성을 보장한다"고 선언하는 것이고, SLI는 그걸 측정 가능한 메트릭으로 풀어낸 식이다. Availability SLI를 가장 흔하게 쓴다.

```promql
# Availability SLI: 5xx 아닌 요청 / 전체 요청
sum(rate(http_requests_total{status_code!~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
```

Latency SLI도 비슷한 형태다.

```promql
# Latency SLI: 500ms 이하 처리된 요청 비율
sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
/
sum(rate(http_request_duration_seconds_count[5m]))
```

SLO를 99.9%로 잡으면 한 달(약 43,200분) 기준 약 43분의 다운타임이 허용된다. 이게 Error Budget이다. Error Budget을 다 태워버리면 신규 배포를 멈추고 안정화에 집중한다는 게 SRE의 기본 약속이다.

### Burn Rate Alert

문제는 다운된 직후 알람을 정확히 받는 게 어렵다는 거다. 너무 짧은 윈도우(1분 평균)로 알람을 걸면 잠깐의 스파이크에 매번 호출되고, 너무 긴 윈도우(1시간)로 걸면 사고가 30분 진행되도록 모른다. 구글 SRE 책의 멀티 윈도우 burn rate가 표준이다.

```yaml
# 빠른 알람: 1시간 안에 한 달치 예산의 2%를 태우면 발화
- alert: ErrorBudgetBurnFast
  expr: |
    (
      sum(rate(http_requests_total{status_code=~"5.."}[5m]))
      / sum(rate(http_requests_total[5m]))
    ) > (14.4 * 0.001)
    and
    (
      sum(rate(http_requests_total{status_code=~"5.."}[1h]))
      / sum(rate(http_requests_total[1h]))
    ) > (14.4 * 0.001)
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Error budget 빠르게 소진 중 (14.4x burn rate)"

# 느린 알람: 6시간 평균이 누적적으로 위험할 때
- alert: ErrorBudgetBurnSlow
  expr: |
    (
      sum(rate(http_requests_total{status_code=~"5.."}[30m]))
      / sum(rate(http_requests_total[30m]))
    ) > (6 * 0.001)
    and
    (
      sum(rate(http_requests_total{status_code=~"5.."}[6h]))
      / sum(rate(http_requests_total[6h]))
    ) > (6 * 0.001)
  for: 15m
  labels:
    severity: warning
```

SLO가 99.9%면 허용 에러율은 0.1% = 0.001이다. burn rate 14.4x는 "지금 이 속도면 한 달 예산을 2시간에 다 태운다"는 뜻이다. 짧은 윈도우(5m)와 긴 윈도우(1h)를 동시 조건으로 걸어 진짜 지속적 사고일 때만 발화시키는 게 핵심이다.

---

## 5. Distributed Tracing

### OpenTelemetry SDK 설정

```typescript
// tracing/setup.ts (앱 진입점에서 가장 먼저 import해야 instrumentation이 작동)
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { ParentBasedSampler, TraceIdRatioBasedSampler } from '@opentelemetry/sdk-trace-base';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: process.env.SERVICE_NAME ?? 'api',
    [SemanticResourceAttributes.SERVICE_VERSION]: process.env.GIT_SHA ?? 'unknown',
    [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV ?? 'development',
  }),
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://otel-collector:4318/v1/traces',
  }),
  sampler: new ParentBasedSampler({
    root: new TraceIdRatioBasedSampler(0.1), // 루트 스팬 10% 샘플링
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();

process.on('SIGTERM', () => {
  sdk.shutdown().finally(() => process.exit(0));
});
```

`getNodeAutoInstrumentations`는 http, express, pg, ioredis, kafkajs 등 흔한 라이브러리를 자동으로 패치한다. 처음에는 이걸로 시작하고, 필요한 것만 골라 쓸 수도 있다.

### Sampling 전략

전 트래픽을 다 트레이싱하면 storage 비용과 collector 부담이 감당 안 된다. 고로 샘플링이 필수다. 두 갈래가 있다.

Head sampling은 스팬을 만들기 전에 결정한다. `TraceIdRatioBasedSampler(0.1)`처럼 10%만 통과시키는 식이다. 결정이 빠르고 SDK가 가볍지만, "에러난 요청만 보고 싶다"가 안 된다. 이미 시작 시점에 버려졌기 때문이다.

Tail sampling은 트레이스가 끝난 후 결정한다. OTel Collector의 `tail_sampling` 프로세서를 통해 "에러 있는 트레이스 100%, 5초 이상 걸린 트레이스 100%, 나머지 5%"처럼 정책을 짤 수 있다. 단점은 모든 스팬을 일단 collector까지 보내야 해서 네트워크 비용이 크고, collector가 트레이스 단위로 메모리에 쌓아둬야 해서 RAM이 많이 든다.

현실적으로는 둘을 조합한다.

- 앱 SDK는 ParentBased + 낮은 ratio(예: 5~10%)로 head sampling
- collector에서 tail sampling으로 에러·느린 트레이스 100% 보존
- 헬스체크·메트릭 엔드포인트는 SDK 단에서 강제로 drop

ParentBased 샘플러가 중요한 이유는 분산 환경에서 일관성을 보장하기 때문이다. 서비스 A가 트레이스를 시작해서 sample=true 결정을 내리면, 그 컨텍스트가 traceparent 헤더에 실려 서비스 B로 전달된다. B는 A의 결정을 따라야 한다. 그래야 트레이스 그래프에 구멍이 안 생긴다.

### 에러는 강제로 샘플링한다

10% sampling으로 잡으면 90%의 에러 트레이스가 버려진다. 운영 중에 "1시간 전 그 에러 트레이스 좀 보자" 했을 때 없으면 답답하다. OTel Collector의 tail sampling 정책으로 처리하는 게 표준이다.

```yaml
# otel-collector-config.yaml
processors:
  tail_sampling:
    decision_wait: 10s   # 트레이스가 완료될 시간을 기다림
    num_traces: 100000
    expected_new_traces_per_sec: 1000
    policies:
      - name: errors-policy
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow-traces
        type: latency
        latency: { threshold_ms: 1000 }
      - name: probabilistic
        type: probabilistic
        probabilistic: { sampling_percentage: 5 }
      - name: drop-health
        type: string_attribute
        string_attribute:
          key: http.target
          values: ["/health", "/metrics"]
          invert_match: false
        # 헬스체크는 어떤 정책에도 안 걸리면 자동으로 drop
```

`decision_wait: 10s`는 트레이스의 모든 스팬이 도착하기를 기다리는 시간이다. 너무 짧으면 늦게 도착한 스팬이 누락된다. 너무 길면 collector 메모리 부담이 커진다.

### W3C Trace Context 수동 전파

자동 instrumentation이 잘 잡아주는 라이브러리는 문제없는데, 그렇지 않은 경우엔 직접 헤더를 넣어줘야 한다.

```typescript
// 외부 HTTP 호출 (auto-instrumentation 없는 경우)
import { context, propagation } from '@opentelemetry/api';

async function callExternal(url: string) {
  const headers: Record<string, string> = {};
  propagation.inject(context.active(), headers);
  // headers = { traceparent: '00-...-...-01', tracestate: '...' }
  return fetch(url, { headers });
}
```

Kafka는 메시지 헤더에 박는다.

```typescript
// Kafka producer
import { context, propagation } from '@opentelemetry/api';

async function sendKafka(topic: string, message: any) {
  const headers: Record<string, string> = {};
  propagation.inject(context.active(), headers);
  await producer.send({
    topic,
    messages: [
      {
        value: JSON.stringify(message),
        headers, // traceparent 등이 자동으로 들어감
      },
    ],
  });
}

// Kafka consumer 쪽에서 받기
import { context, propagation, trace } from '@opentelemetry/api';

await consumer.run({
  eachMessage: async ({ message }) => {
    const headers = Object.fromEntries(
      Object.entries(message.headers ?? {}).map(([k, v]) => [k, v?.toString() ?? ''])
    );
    const parentCtx = propagation.extract(context.active(), headers);
    await context.with(parentCtx, async () => {
      const span = trace.getTracer('kafka-consumer').startSpan('process_message');
      try {
        await handleMessage(message);
      } finally {
        span.end();
      }
    });
  },
});
```

BullMQ도 똑같다. Job data에 traceparent를 넣어두고 worker에서 꺼내 컨텍스트를 복원한다.

```typescript
// BullMQ Producer
const headers: Record<string, string> = {};
propagation.inject(context.active(), headers);
await queue.add('email', { to, body, _trace: headers });

// BullMQ Worker
new Worker('email', async (job) => {
  const parentCtx = propagation.extract(context.active(), job.data._trace ?? {});
  await context.with(parentCtx, async () => {
    const span = tracer.startSpan('process_email');
    try {
      await sendEmail(job.data);
    } finally {
      span.end();
    }
  });
});
```

이렇게 해두면 HTTP API 요청 → BullMQ 큐잉 → Worker 처리 → DB 저장이 한 트레이스로 묶인다.

### 비동기 작업에서 컨텍스트가 끊긴다

`AsyncLocalStorage`와 OpenTelemetry context는 보통 잘 따라가는데, 다음 패턴에서 끊긴다.

- `setTimeout`/`setInterval`로 등록한 콜백이 한참 후에 실행될 때
- 외부 라이브러리가 내부적으로 EventEmitter를 reuse하는 경우
- worker_threads로 보내는 작업

해결법은 `context.with()`로 명시적으로 묶는 것이다.

```typescript
import { context, trace } from '@opentelemetry/api';

const currentCtx = context.active();
setTimeout(() => {
  context.with(currentCtx, () => {
    const span = trace.getTracer('bg').startSpan('delayed_task');
    try {
      doWork();
    } finally {
      span.end();
    }
  });
}, 5000);
```

자주 끊기는 곳을 일일이 처리해야 한다. 어디서 끊겼는지 파악하는 가장 빠른 방법은 로그에 trace_id가 안 찍히는 함수를 찾는 거다. mixin이 빈 객체를 반환하면 그 컨텍스트는 끊긴 것이다.

### 커스텀 Span

```typescript
import { trace, SpanStatusCode } from '@opentelemetry/api';

const tracer = trace.getTracer('payment-service');

async function processPayment(orderId: string, amount: number) {
  return tracer.startActiveSpan('processPayment', async (span) => {
    span.setAttributes({
      'order.id': orderId,
      'payment.amount': amount,
    });
    try {
      await paymentGateway.charge(orderId, amount);
      span.setStatus({ code: SpanStatusCode.OK });
    } catch (err) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: (err as Error).message });
      span.recordException(err as Error);
      throw err;
    } finally {
      span.end();
    }
  });
}
```

`startActiveSpan`은 span을 active context에 자동으로 넣어주기 때문에, 안에서 호출되는 모든 자식 span이 부모를 정확히 잡는다. `startSpan`은 그러지 않으므로 직접 `context.with()`로 묶어야 한다. 헷갈리면 startActiveSpan을 쓰자.

---

## 6. Continuous Profiling

메트릭과 트레이스로도 안 잡히는 게 있다. "P99이 1초인데 어디서 시간을 쓰는지 모르겠다", "CPU 100% 치는데 어떤 함수가 범인인지 모르겠다" 같은 경우다. 이럴 때 들어오는 게 Continuous Profiling이다. 운영 환경에서 항상 낮은 오버헤드로 CPU·heap 프로파일을 떠서 저장해두고, 사고난 시각의 프로파일을 사후에 들여다본다.

도구는 두 갈래가 흔하다. Pyroscope(Grafana 진영)와 Parca다. 둘 다 pprof 포맷을 쓴다.

```typescript
// Pyroscope SDK
import Pyroscope from '@pyroscope/nodejs';

Pyroscope.init({
  serverAddress: process.env.PYROSCOPE_URL ?? 'http://pyroscope:4040',
  appName: process.env.SERVICE_NAME ?? 'api',
  tags: {
    env: process.env.NODE_ENV ?? 'development',
    region: process.env.REGION ?? 'kr',
  },
});

Pyroscope.start();
```

Pyroscope SDK는 `--perf-basic-prof` 옵션으로 V8 perf 데이터를 떠서 보낸다. CPU 오버헤드는 보통 1~3% 수준이라 운영에 그대로 켜둔다.

대시보드에서 시간 범위를 좁히면 그 시간 동안의 flame graph를 볼 수 있다. "P99 튄 시각의 flame graph"를 확인하면 어떤 함수가 시간을 잡아먹었는지 바로 보인다. JSON.parse가 비정상적으로 점유하고 있다면 큰 페이로드 들어왔다는 신호고, GC가 큰 비중이라면 메모리 압박 신호다.

heap profile도 같이 떠두면 메모리 누수 디버깅이 한결 쉽다. 누적된 heap 프로파일에서 retainer chain이 보인다.

---

## 7. APM 도구 선택

### 자체 구축 vs 상용

| 항목 | 자체 구축 (OTel + Tempo + Prometheus + Grafana + Loki) | 상용 (Datadog, New Relic, Elastic APM) |
|------|------|------|
| 초기 비용 | 인프라 비용만 (서버, 스토리지) | 월정액, agent당 또는 host당 과금 |
| 운영 비용 | 엔지니어 시간이 큰 비중 | 거의 없음, 다만 지표 폭발 시 청구 폭발 |
| 데이터 보관 | 직접 정책 결정 | 보통 15일~30일 기본, 연장은 추가 비용 |
| 통합 깊이 | 직접 대시보드 만들어야 함 | 라이브러리 자동 인식, 즉시 인사이트 |
| 조직 규모 | 5명 이상 SRE/플랫폼 팀 필요 | 1~2명도 운영 가능 |
| 한계 | Tempo 트레이스 검색이 ElasticSearch만 못함 | vendor lock-in, 비용 통제 필요 |

작은 조직이고 사람이 부족하면 상용으로 시작해라. Datadog 한 달 비용이 엔지니어 한 명 인건비보다 훨씬 적다. 다만 트래픽이 늘면 비용이 가파르게 오른다. 한 host당 월 $30이라도 1000대면 월 3만 달러다.

OpenTelemetry 표준을 쓰면 나중에 자체 구축으로 갈아타기 쉽다. 그래서 처음부터 OTel SDK를 쓰고 exporter만 Datadog용으로 두는 식의 구성이 안전하다. vendor 종속 SDK를 쓰면 나중에 갈아탈 때 모든 코드를 갈아엎어야 한다.

자체 구축 스택으로 가면 보통 이 조합이다.

- Metrics: Prometheus + Thanos(장기 보관) 또는 Mimir
- Logs: Loki(가벼움) 또는 Elasticsearch(검색 강력)
- Traces: Tempo 또는 Jaeger
- Visualization: Grafana
- Collector: OpenTelemetry Collector (한 곳에서 라우팅·샘플링·변환)

이 조합의 장점은 각 컴포넌트가 다른 걸로 갈아끼우기 쉽다는 것이다. Tempo가 마음에 안 들면 Jaeger로 바꿔도 OTel Collector exporter만 변경하면 된다.

---

## 8. 트러블슈팅 시나리오

### Histogram bucket 잘못 잡아 P99이 부정확했던 사례

P99이 항상 1초로 보고되어 SLO 위반 알람이 매일 뜨는데, 사용자가 느림을 호소한 적은 없는 상황. Grafana에서 `histogram_quantile`을 봤더니 모든 P99이 정확히 1.0s로 박혀 있었다. 버킷이 `[0.1, 0.5, 1, 5]`로 듬성듬성 잡혀 있어서, 실제 응답시간이 0.6~1.0s 사이에 분포해도 P99이 무조건 1로 보였다. 버킷을 조정하고 나서야 진짜 P99이 0.7s 부근이라는 게 드러났다.

교훈: Histogram을 만들 때는 SLO 임계치 주변에 반드시 버킷을 두고, 실제 응답시간 분포의 중간값 근처를 촘촘히 잡는다.

### OTel SDK가 메모리 누수 일으킨 사례

OTel SDK 1.x 초창기, BatchSpanProcessor의 큐가 export 실패 시 무한히 쌓이는 버그가 있었다. collector가 일시적으로 다운되자 앱의 heap이 분당 수 MB씩 늘어나 결국 OOM. heap snapshot으로 보면 `Span` 객체들이 BatchSpanProcessor의 내부 배열에 retain되어 있었다.

해결은 두 가지였다. 첫째, SDK 버전 업그레이드(1.20+에서 max queue size 초과시 drop 정책 들어감). 둘째, BatchSpanProcessor의 `maxQueueSize`, `maxExportBatchSize`를 명시적으로 작게 잡는 것.

```typescript
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';

new BatchSpanProcessor(exporter, {
  maxQueueSize: 2048,         // 초과시 drop
  maxExportBatchSize: 512,
  scheduledDelayMillis: 5000,
  exportTimeoutMillis: 30000,
});
```

교훈: collector가 죽었을 때 앱이 같이 죽지 않도록 큐 사이즈를 반드시 제한한다. 트레이스 일부를 잃는 게 앱 OOM보다 낫다.

### 동기 로깅이 이벤트 루프를 막은 사례

stack trace를 그대로 stdout에 dump하면 파이프 buffer가 차서 write가 block되는 케이스가 있다. 컨테이너 환경에서 stdout은 보통 파이프인데, 컨테이너 런타임이 받아주지 못하면 앱 쪽 write가 동기적으로 멈춘다. P99이 100~500ms씩 튀고, Event Loop Lag P99도 같이 튄다.

해결은 pino transport(worker thread로 위임)로 옮기거나, `pino.multistream`으로 비동기 write를 보장하는 것. 그리고 stack trace는 풀어쓴 multi-line 대신 한 줄 JSON으로 박는다.

교훈: 운영에서는 어떤 경로로도 메인 스레드에서 동기 I/O가 일어나면 안 된다. Event Loop Lag P99이 평소보다 튀면 동기 I/O를 의심한다.

### DB 커넥션 풀 saturation을 놓친 사례

서비스 응답시간 P99이 1초 넘게 튀는데 DB 쿼리 자체는 50ms로 빨랐다. 한참을 못 찾다가 Pyroscope flame graph에서 `Pool.acquire()`에서 시간을 다 쓰고 있는 걸 봤다. `pg`의 pool size가 10인데 동시 요청이 50개씩 들어오면 40개는 acquire 대기였다.

이후로 메트릭에 풀 상태를 반드시 박는다.

```typescript
import { Gauge } from 'prom-client';

new Gauge({
  name: 'db_pool_total',
  help: 'Total connections in pool',
  registers: [registry],
  collect() { this.set(pool.totalCount); },
});

new Gauge({
  name: 'db_pool_idle',
  help: 'Idle connections',
  registers: [registry],
  collect() { this.set(pool.idleCount); },
});

new Gauge({
  name: 'db_pool_waiting',
  help: 'Queued requests waiting for a connection',
  registers: [registry],
  collect() { this.set(pool.waitingCount); },
});
```

`waitingCount`가 0보다 자주 크게 잡히면 풀 사이즈를 키우거나 쿼리를 빠르게 하거나 트래픽을 줄여야 한다는 뜻이다. USE 모델의 saturation 항목이 바로 이런 메트릭을 가리킨다.

---

## 9. 헬스체크 엔드포인트

```typescript
// routes/health.ts
import { Router } from 'express';
import { dataSource } from '../database';
import redis from '../cache/redis';

const router = Router();

// 가벼운 liveness — 프로세스가 살아있기만 하면 200
router.get('/livez', (_req, res) => {
  res.status(200).json({ status: 'ok' });
});

// 의존성까지 확인하는 readiness — 503이면 트래픽 받지 말 것
router.get('/readyz', async (_req, res) => {
  const checks = await Promise.allSettled([
    dataSource.query('SELECT 1'),
    redis.ping(),
  ]);
  const [db, cache] = checks;
  const allOk = checks.every((c) => c.status === 'fulfilled');

  res.status(allOk ? 200 : 503).json({
    status: allOk ? 'ok' : 'degraded',
    uptime: process.uptime(),
    checks: {
      database: db.status === 'fulfilled' ? 'ok' : 'error',
      redis: cache.status === 'fulfilled' ? 'ok' : 'error',
    },
  });
});

export default router;
```

쿠버네티스에서 livenessProbe와 readinessProbe를 분리하는 게 표준이다. liveness는 프로세스가 죽었는지만 확인한다. liveness가 503을 뱉으면 K8s가 컨테이너를 재시작한다. readiness는 의존성 포함 정상 동작 여부다. readiness가 503이면 K8s는 Service 엔드포인트에서 빼서 트래픽을 안 보낸다. 둘을 같이 쓰면 DB가 잠깐 끊겼을 때 컨테이너가 재시작되며 로그도 다 잃는 사고가 난다.

`/metrics` 엔드포인트도 함께 깔아둔다.

```typescript
import { registry } from './metrics';

app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', registry.contentType);
  res.end(await registry.metrics());
});
```

---

## 10. 알람 룰

```yaml
groups:
  - name: api-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "5xx 에러율 5% 초과"

      - alert: SlowP95
        expr: |
          histogram_quantile(0.95,
            sum by (le, route) (rate(http_request_duration_seconds_bucket[5m]))
          ) > 1
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "라우트별 P95 1초 초과: {{ $labels.route }}"

      - alert: EventLoopBlocked
        expr: nodejs_event_loop_lag_p99_seconds > 0.1
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Event loop P99 lag 100ms 초과 — 동기 작업 의심"

      - alert: HeapGrowing
        expr: |
          deriv(nodejs_heap_used_bytes[30m]) > 0
          and avg_over_time(nodejs_heap_used_bytes[30m]) > 500 * 1024 * 1024
        for: 30m
        labels: { severity: warning }
        annotations:
          summary: "Heap이 30분 연속 증가 중 — 누수 의심"

      - alert: DbPoolSaturated
        expr: db_pool_waiting > 0
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "DB 커넥션 풀 대기열 발생 — 풀 사이즈/쿼리 점검"
```

`for: 2m` 같은 grace period가 중요하다. 짧은 스파이크에 매번 호출되면 알람 피로도 때문에 진짜 사고를 놓친다.

---

## 핵심 지표 대시보드

| 지표 | 의미 | 임계치 기준 |
|------|------|------|
| P95/P99 응답 시간 | 느린 요청 탐지 | P95 < 500ms |
| 에러율 (5xx 비율) | 서비스 안정성 | < 0.1% (SLO 99.9%) |
| RPS (초당 요청) | 트래픽 현황 | 기준선 대비 급변 시 알람 |
| DB 쿼리 P95 | DB 병목 탐지 | P95 < 100ms |
| DB pool waiting | 풀 saturation | 0 유지 |
| Event Loop Lag P99 | 동기 작업 탐지 | < 50ms |
| Heap used | 누수 탐지 | 점진 증가 패턴 주시 |
| Active Handles | connection leak | 일정 범위 유지 |
| Error Budget Burn Rate | SLO 소진 속도 | 14.4x 단기 / 6x 장기 |

대시보드는 RED 패널, USE 패널, SLO 패널 세 묶음으로 분리해서 만들어두면 사고 대응이 빨라진다. RED 패널은 사용자 영향, USE 패널은 원인 탐색, SLO 패널은 의사결정 근거다.
