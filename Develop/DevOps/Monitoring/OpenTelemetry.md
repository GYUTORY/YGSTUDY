---
title: OpenTelemetry
tags: [devops, monitoring, observability, opentelemetry, otel, tracing, metrics, logs, jaeger, tempo, collector, kubernetes, baggage, otlp, semantic-conventions, propagator, spankind]
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

## 핵심 개념 모델

### Resource

Resource는 텔레메트리 데이터를 생성하는 **엔티티의 정체성**이다. "이 데이터가 어디서 왔는가"를 나타내는 속성 집합으로, 서비스 이름, 버전, 배포 환경, 호스트 정보 등이 포함된다.

```typescript
import { Resource } from '@opentelemetry/resources';
import {
  SEMRESATTRS_SERVICE_NAME,
  SEMRESATTRS_SERVICE_VERSION,
} from '@opentelemetry/semantic-conventions';

const resource = new Resource({
  [SEMRESATTRS_SERVICE_NAME]: 'payment-service',
  [SEMRESATTRS_SERVICE_VERSION]: '2.1.0',
  'deployment.environment': 'production',
  'service.namespace': 'checkout',
  'service.instance.id': process.env.HOSTNAME ?? 'local',
});
```

Resource는 SDK 초기화 시 한 번 설정되면 해당 프로세스에서 생성되는 모든 trace, metric, log에 자동으로 붙는다. Jaeger에서 서비스를 드롭다운으로 선택할 수 있는 것도 `service.name` Resource 속성 덕분이다.

실무에서 자주 빠뜨리는 것:

- `service.namespace` — 같은 이름의 서비스가 여러 팀에 있을 때 구분이 안 된다. 네임스페이스를 넣어야 Jaeger에서 구분된다
- `service.instance.id` — 인스턴스별 문제를 추적하려면 필수다. Kubernetes라면 Pod 이름을 넣는다
- `deployment.environment` — staging과 production 데이터가 같은 백엔드에 들어갈 때 이걸로 필터링한다

### Instrumentation Scope

Instrumentation Scope는 텔레메트리를 생성하는 **계측 라이브러리의 이름과 버전**이다. `getTracer('payment-service', '1.0.0')`에서 넘기는 인자가 바로 Instrumentation Scope다.

```typescript
// 각 모듈/라이브러리별로 별도의 tracer를 만드는 게 맞다
const paymentTracer = trace.getTracer('payment-module', '1.0.0');
const notificationTracer = trace.getTracer('notification-module', '1.2.0');

// meter도 마찬가지
const paymentMeter = metrics.getMeter('payment-module', '1.0.0');
```

Jaeger나 Grafana에서 span을 볼 때 "이 span이 어떤 계측 라이브러리에서 만들어졌는가"를 확인할 수 있다. 자동 계측 라이브러리(`@opentelemetry/instrumentation-express` 등)가 만든 span과 직접 만든 span을 구분할 때 쓰인다.

Resource가 "어느 서비스"를 나타낸다면, Instrumentation Scope는 "그 서비스 안에서 어느 모듈/라이브러리"를 나타낸다.

### Semantic Conventions

Semantic Conventions는 속성 이름에 대한 **공통 네이밍 규칙**이다. 팀마다 HTTP 상태 코드를 `status_code`, `http_status`, `response_code` 등 다르게 쓰면 대시보드와 쿼리를 서비스별로 따로 만들어야 한다. OTel은 이걸 `http.response.status_code`로 통일한다.

주요 네이밍 패턴:

```
http.request.method          — GET, POST 등
http.response.status_code    — 200, 500 등
http.route                   — /api/users/:id (패턴)
url.full                     — https://api.example.com/users/123

db.system                    — postgresql, mysql, redis
db.statement                 — SELECT * FROM users WHERE id = $1
db.operation.name            — SELECT, INSERT

messaging.system             — kafka, rabbitmq
messaging.operation.type     — publish, receive
messaging.destination.name   — orders-topic

rpc.system                   — grpc
rpc.method                   — GetUser
rpc.service                  — UserService
```

`@opentelemetry/semantic-conventions` 패키지에서 상수로 제공한다.

```typescript
import {
  SEMRESATTRS_SERVICE_NAME,
  SEMATTRS_HTTP_METHOD,
  SEMATTRS_HTTP_STATUS_CODE,
  SEMATTRS_DB_SYSTEM,
} from '@opentelemetry/semantic-conventions';
```

자동 계측 라이브러리는 이 규칙을 따르지만, 커스텀 span에서 속성을 직접 지정할 때는 이 규칙을 의식적으로 따라야 한다. `order_id`보다 `order.id`처럼 dot-separated namespace를 쓰는 게 관례다.

주의: Semantic Conventions는 버전별로 속성 이름이 바뀌는 경우가 있다. 예를 들어 `http.method`는 `http.request.method`로 변경됐다. OTel SDK 버전을 올릴 때 속성 이름이 달라져서 기존 대시보드가 깨질 수 있으니, Collector의 `transform` processor로 마이그레이션 기간에 양쪽 이름을 모두 내보내는 방법을 쓰기도 한다.

### Trace 내부 구조

#### Trace와 Span의 관계

Trace는 하나의 요청이 시스템을 통과하는 전체 경로를 나타낸다. Trace 자체는 독립적인 데이터 객체가 아니라, **같은 trace ID를 공유하는 Span들의 집합**이다. Span은 하나의 작업 단위를 나타내고, Span들이 부모-자식 관계로 연결되어 트리 구조를 형성한다.

```
Trace (trace_id: abc123)
│
├── Span A: "POST /api/orders" (parent_span_id: 없음 = root span)
│   ├── Span B: "OrderService.create" (parent_span_id: A)
│   │   ├── Span C: "DB INSERT orders" (parent_span_id: B)
│   │   └── Span D: "Redis SET order_cache" (parent_span_id: B)
│   └── Span E: "PaymentService.charge" (parent_span_id: A)
│       └── Span F: "HTTP POST stripe.com/charge" (parent_span_id: E)
```

Jaeger UI에서 보는 워터폴 차트가 이 구조를 시간축 위에 펼친 것이다.

#### Span의 구성 요소

각 Span은 다음 필드를 가진다.

```
trace_id         — 이 span이 속한 trace의 고유 ID (128-bit, 32자 hex)
                   같은 요청에서 만들어진 모든 span이 이 값을 공유한다

span_id          — 이 span 자체의 고유 ID (64-bit, 16자 hex)

parent_span_id   — 부모 span의 ID. root span이면 비어 있다
                   이 값으로 span 간 트리 구조가 만들어진다

name             — span 이름. "HTTP GET /users", "DB SELECT users" 같은 형태
                   나중에 Jaeger에서 검색하는 단위이므로 변수값을 넣으면 안 된다
                   "GET /users/123" (X) → "GET /users/:id" (O)

kind             — CLIENT, SERVER, PRODUCER, CONSUMER, INTERNAL (아래 SpanKind 섹션 참고)

start_time       — span 시작 시각 (nanosecond 정밀도)
end_time         — span 종료 시각. end()를 호출해야 기록된다

status           — UNSET, OK, ERROR 중 하나
                   에러가 아닌 한 UNSET으로 두면 된다. OK를 명시적으로 찍을 필요는 없다

attributes       — 키-값 쌍. Jaeger에서 검색과 필터링에 사용된다
                   예: { "http.method": "GET", "http.status_code": 200 }

events           — span 실행 중 발생한 특정 시점의 기록
                   예외 발생, 재시도 시작 같은 이벤트를 타임스탬프와 함께 남긴다

links            — 다른 trace나 span과의 참조 관계
                   부모-자식이 아닌 "관련 있음" 수준의 연결에 사용한다
```

#### Events — Span 안의 시점 기록

Span이 "구간"을 나타낸다면, Event는 그 구간 안의 **특정 시점**을 나타낸다. 예외가 발생했거나, 재시도를 했거나, 캐시를 히트/미스한 순간을 기록할 때 쓴다.

```typescript
span.addEvent('cache.miss', {
  'cache.key': 'user:123',
});

// 예외 기록도 내부적으로 Event다
span.recordException(new Error('connection timeout'));
// → name: "exception", attributes: { "exception.message": "connection timeout", ... }
```

`recordException()`은 `addEvent('exception', ...)`의 편의 메서드다. 예외를 기록하면 Jaeger에서 해당 span에 에러 마크가 표시된다.

#### Links — 인과 관계가 아닌 연결

부모-자식 관계는 "A가 B를 호출했다"는 인과 관계다. 반면 Link는 인과 관계 없이 "관련 있음"을 나타낸다.

Link가 필요한 상황:

- 배치 처리 — 하나의 consumer span이 여러 producer span에서 온 메시지를 처리할 때, 각 producer span을 link로 연결한다. 부모는 하나밖에 못 두니까 link를 쓴다
- 재처리 — 실패한 요청을 재처리할 때, 원래 trace를 link로 걸어두면 "이건 저 요청의 재시도"라는 맥락이 남는다

```typescript
const link = {
  context: originalSpan.spanContext(),
  attributes: { 'link.reason': 'retry' },
};

tracer.startActiveSpan('order.retry', { links: [link] }, (span) => {
  // 재처리 로직
  span.end();
});
```

#### Span 간 관계 — 트리와 DAG

일반적인 동기 호출에서는 span들이 **트리 구조**를 형성한다. 하나의 부모가 여러 자식을 가지고, 자식은 부모를 하나만 가진다.

비동기 메시징이나 배치 처리가 섞이면 Link 때문에 관계가 **DAG(Directed Acyclic Graph)**로 확장된다. 부모-자식 관계는 여전히 트리지만, Link를 포함하면 하나의 span이 여러 trace의 span들과 연결될 수 있다.

```
Trace 1: [Producer A] ──publish──▶ [message queue]
Trace 2: [Producer B] ──publish──▶ [message queue]
                                        │
Trace 3: [Consumer] ◀──consume──────────┘
          links: [Producer A의 span, Producer B의 span]
```

Jaeger에서 Link가 있는 span을 클릭하면 연결된 trace로 점프할 수 있다. 다만 모든 트레이싱 백엔드가 Link를 잘 시각화하지는 않는다. Tempo는 지원하고, Jaeger는 버전에 따라 다르다.

### Context와 Context Propagation

#### Context가 뭔가

Context는 현재 실행 중인 코드의 **부가 정보를 담는 불변 객체**다. 가장 중요한 역할은 "지금 활성화된 span이 뭔지"를 들고 다니는 것이다.

함수 A가 span을 시작하고 함수 B를 호출하면, 함수 B는 어떻게 "내 부모 span이 A다"라는 걸 아는가? 매번 span을 파라미터로 넘길 수는 없으니까, OTel은 Context라는 **암묵적 저장소**에 현재 span을 넣어두고, 하위 코드에서 `context.active()`로 꺼내 쓴다.

```
함수 호출 흐름:

handleRequest()                    context = { activeSpan: spanA }
  └── processOrder()               context = { activeSpan: spanA }  ← 자동 전파
        └── chargePayment()         context = { activeSpan: spanB }  ← spanB의 parent = spanA
              └── callStripe()      context = { activeSpan: spanC }  ← spanC의 parent = spanB
```

`startActiveSpan()`을 호출하면 새 span을 만들고, 그 span을 담은 새 Context를 현재 실행 범위에 설정한다. 콜백이 끝나면 이전 Context로 복원된다.

#### 프로세스 내 전파 — Zone, AsyncLocalStorage

같은 프로세스 안에서 Context가 비동기 코드를 따라가야 한다. Node.js에서는 `AsyncLocalStorage`가 이 역할을 한다. OTel Node.js SDK는 내부적으로 `AsyncLocalStorage`를 사용해서, `await` 체인을 따라 Context가 자동으로 전파된다.

문제는 `AsyncLocalStorage`의 추적이 끊기는 경우다.

```typescript
// AsyncLocalStorage가 추적하는 경우 (context 전파됨)
await someAsyncFunction();        // OK
new Promise((resolve) => { ... }) // OK
fs.readFile(path, callback);      // OK (Node.js 16+)

// AsyncLocalStorage 추적이 끊기는 경우 (context 유실)
setTimeout(() => { ... });        // 콜백이 다른 실행 컨텍스트
setInterval(() => { ... });       // 마찬가지
EventEmitter.on('event', () => { ... });  // 이벤트 핸들러
```

`setTimeout` 안에서 `context.active()`를 호출하면 root context가 반환된다. 부모 span 정보가 없으니 고아 span이 만들어지고, Jaeger에서 트레이스가 끊겨 보인다. 이때는 `context.with()`로 명시적으로 전달해야 한다.

```typescript
const ctx = context.active();
setTimeout(() => {
  context.with(ctx, () => {
    // 여기서 context.active() === ctx
  });
}, 100);
```

Java에서는 `ThreadLocal`이 같은 역할을 하는데, 스레드 풀에서 작업이 다른 스레드로 넘어가면 Context가 유실된다. 그래서 `ExecutorService`를 `Context.taskWrapping(executor)`으로 감싸야 한다.

#### 프로세스 간 전파 — Propagation

서비스 A에서 서비스 B를 HTTP로 호출할 때, Context를 HTTP 헤더에 실어 보내야 한다. 이게 Context Propagation이다.

과정은 세 단계다:

```
1. Inject (주입)  — 서비스 A가 현재 Context에서 trace_id, span_id를 꺼내
                    HTTP 요청 헤더에 넣는다
                    propagation.inject(context.active(), headers)

2. Transfer (전송) — HTTP 요청이 네트워크를 통해 서비스 B로 전달된다
                    traceparent: 00-abc123-def456-01 (W3C 포맷)

3. Extract (추출) — 서비스 B가 수신한 헤더에서 trace_id, span_id를 꺼내
                    새 Context를 만들고, 이후 생성되는 span의 부모로 설정한다
                    propagation.extract(context.active(), headers)
```

자동 계측(`@opentelemetry/instrumentation-http` 등)이 이 inject/extract를 알아서 처리한다. HTTP client 라이브러리(axios, fetch)로 요청을 보내면 자동으로 `traceparent` 헤더가 추가되고, Express/Fastify 서버에서 요청을 받으면 자동으로 헤더를 읽어 부모 span을 설정한다.

수동으로 해야 하는 경우는 자동 계측이 지원하지 않는 전송 수단을 쓸 때다. 예를 들어 커스텀 메시지 큐, gRPC metadata, WebSocket 등.

#### Propagator 종류와 선택

Propagation에서 "어떤 포맷으로 직렬화하느냐"를 결정하는 게 Propagator다. 아래 Propagator 섹션에서 W3C TraceContext, B3 등 구체적인 포맷을 다룬다.

### SDK 내부 파이프라인

NodeSDK 래퍼를 쓰면 초기화 코드가 간단하지만, 내부에서 어떤 일이 일어나는지 모르면 문제가 생겼을 때 원인을 못 찾는다.

#### TracerProvider → Tracer → Span

```
TracerProvider (SDK 초기화 시 1개 생성)
  │
  ├── Resource 설정 (service.name, environment 등)
  ├── SpanProcessor 등록 (Simple 또는 Batch)
  ├── Sampler 설정
  │
  └── getTracer('module-name', 'version')
        │
        └── Tracer (모듈/라이브러리별로 1개씩)
              │
              └── startActiveSpan('operation-name')
                    │
                    └── Span 생성
                          │
                          ├── Sampler에게 "이 span 수집할까?" 물어봄
                          │   └── YES → 정상 span, 속성/이벤트 기록
                          │   └── NO  → NoOp span, 아무것도 안 함
                          │
                          └── span.end() 호출 시 → SpanProcessor로 전달
```

`TracerProvider`는 프로세스당 하나다. `trace.getTracer()`로 Tracer를 여러 개 만들 수 있지만, 이건 Instrumentation Scope를 구분하기 위한 것이지 별도의 설정을 가지는 건 아니다. 모든 Tracer가 같은 TracerProvider의 Sampler, Processor, Exporter를 공유한다.

`NodeSDK`는 이 TracerProvider 생성과 글로벌 등록을 한 줄로 해주는 래퍼다. 내부적으로는 `TracerProvider`를 만들고 `trace.setGlobalTracerProvider()`를 호출한다.

#### SpanProcessor — Simple vs Batch

Span이 `end()`되면 SpanProcessor에게 전달된다. Processor가 Exporter를 호출해서 실제로 데이터를 보낸다.

```
Span.end()
  │
  ▼
SpanProcessor.onEnd(span)
  │
  ├── SimpleSpanProcessor
  │     └── 즉시 Exporter.export([span]) 호출
  │         span이 끝날 때마다 바로 전송
  │         개발 환경에서 디버깅할 때 쓴다
  │         프로덕션에서 쓰면 요청마다 네트워크 호출이 발생해서 성능이 나빠진다
  │
  └── BatchSpanProcessor
        └── 내부 큐에 span을 쌓아둔다
            일정 시간(scheduledDelayMillis, 기본 5초) 또는
            일정 개수(maxExportBatchSize, 기본 512개)가 되면
            한 번에 Exporter.export(spans[]) 호출
            프로덕션에서는 이걸 써야 한다
```

```typescript
import { BatchSpanProcessor, SimpleSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

const exporter = new OTLPTraceExporter({ url: 'http://collector:4318/v1/traces' });

// 프로덕션
const batchProcessor = new BatchSpanProcessor(exporter, {
  scheduledDelayMillis: 5000,    // 5초마다 내보내기
  maxExportBatchSize: 512,       // 한 번에 최대 512개
  maxQueueSize: 2048,            // 큐에 최대 2048개 대기
  exportTimeoutMillis: 30000,    // 내보내기 타임아웃 30초
});

// 개발
const simpleProcessor = new SimpleSpanProcessor(exporter);
```

`NodeSDK`에 `traceExporter`만 넘기면 내부적으로 `BatchSpanProcessor`로 감싸준다. `spanProcessors`를 직접 넘기면 원하는 Processor를 쓸 수 있다.

`maxQueueSize`에 도달하면 새 span이 버려진다. 트래픽이 많은 서비스에서 이 값이 작으면 span 유실이 생기는데, Collector 메트릭의 `otelcol_exporter_send_failed_spans`가 아니라 SDK 쪽에서 조용히 drop되는 거라 모르고 지나가는 경우가 있다.

#### Exporter — 데이터를 어디로 보내나

SpanProcessor가 Exporter를 호출하면, Exporter가 실제 네트워크 전송을 담당한다.

```
Exporter 종류:
  OTLPTraceExporter (HTTP)  — http://collector:4318/v1/traces 로 전송
  OTLPTraceExporter (gRPC)  — collector:4317 로 전송
  ConsoleSpanExporter       — 콘솔에 JSON 출력 (디버깅용)
  InMemorySpanExporter      — 메모리에 저장 (테스트용)
```

Exporter는 바꿔 끼울 수 있다. Collector로 보내다가 Jaeger로 직접 보내고 싶으면 Exporter만 바꾸면 된다. 하지만 실무에서는 항상 Collector를 거치는 게 맞다. Collector에서 배치 처리, 필터링, 샘플링을 하니까.

#### 전체 흐름 정리

```
[애플리케이션 코드]
     │
     │ tracer.startActiveSpan('op')
     ▼
[Sampler] ─── 수집 여부 결정
     │
     │ span.setAttribute(), span.addEvent()
     │ span.end()
     ▼
[SpanProcessor]
     │ Simple: 즉시 전송
     │ Batch: 큐에 모아서 전송
     ▼
[Exporter]
     │ OTLP HTTP/gRPC
     ▼
[Collector] ─── receivers → processors → exporters
     │
     ▼
[Backend] ─── Jaeger, Tempo, Datadog 등
```

### Sampler 종류와 동작 원리

현재 문서의 샘플링 섹션에서 head/tail 구분만 간략히 다뤘는데, SDK에서 설정하는 Sampler의 구체적인 종류와 조합 방식이 빠져 있다.

#### Head-based Sampler (SDK에서 설정)

Head-based 샘플링은 **span이 만들어지는 시점**에 수집 여부를 결정한다. SDK의 `Sampler` 인터페이스가 이 역할을 한다.

**AlwaysOnSampler** — 모든 span을 수집한다. 디버깅이나 트래픽이 적은 서비스에서 쓴다. 프로덕션에서 트래픽이 많은 서비스에 걸면 스토리지 비용이 감당이 안 된다.

**AlwaysOffSampler** — 아무것도 수집하지 않는다. span 자체는 생성되지만 NoOp 상태라 속성이나 이벤트가 기록되지 않고 export도 안 된다. 특정 서비스의 트레이싱을 완전히 끄고 싶을 때 쓴다.

**TraceIdRatioBasedSampler** — trace ID의 해시값을 기준으로 비율 샘플링한다. `ratio: 0.1`이면 10%의 trace를 수집한다. 중요한 점은, 같은 trace ID는 어떤 서비스에서든 같은 결정이 나온다는 것이다. trace ID 자체가 랜덤이고, 그 값의 하위 비트를 비율과 비교하기 때문이다. 그래서 서비스 A에서 샘플링된 trace는 서비스 B에서도 샘플링된다(같은 ratio를 쓴다면).

```typescript
import { TraceIdRatioBasedSampler } from '@opentelemetry/sdk-trace-base';

// 10% 샘플링 — trace ID 해시 기반이라 서비스 간 일관성 보장
const sampler = new TraceIdRatioBasedSampler(0.1);
```

**ParentBasedSampler** — 부모 span의 샘플링 결정을 따른다. 부모가 샘플링됐으면 자식도 샘플링하고, 안 됐으면 자식도 안 한다. 부모가 없는 root span에 대해서만 별도 Sampler를 적용한다.

이게 왜 필요한가: 서비스 A가 10% 샘플링으로 trace를 시작했는데, 서비스 B가 별도로 20% 샘플링을 하면 A에서는 수집되는 trace가 B에서는 버려지는 경우가 생긴다. trace가 중간에 끊기는 것이다. `ParentBasedSampler`는 upstream의 결정을 존중해서 이 문제를 방지한다.

```typescript
import { ParentBasedSampler, TraceIdRatioBasedSampler, AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';

const sampler = new ParentBasedSampler({
  root: new TraceIdRatioBasedSampler(0.1),         // root span은 10% 샘플링
  remoteParentSampled: new AlwaysOnSampler(),       // upstream이 수집 결정 → 따른다
  remoteParentNotSampled: new AlwaysOffSampler(),   // upstream이 미수집 결정 → 따른다
  localParentSampled: new AlwaysOnSampler(),        // 같은 프로세스 내 부모가 수집 → 따른다
  localParentNotSampled: new AlwaysOffSampler(),    // 같은 프로세스 내 부모가 미수집 → 따른다
});
```

`NodeSDK`의 기본 Sampler는 `ParentBasedSampler(root: AlwaysOnSampler)`다. 즉, root span은 전부 수집하고, 부모가 있으면 부모 결정을 따른다. 프로덕션에서 root의 AlwaysOn을 TraceIdRatio로 바꾸는 게 일반적이다.

#### 조합 방식

실무에서 쓰는 패턴:

```
패턴 1: ParentBased + TraceIdRatio (가장 흔함)
  → root span은 10% 샘플링, 나머지는 부모를 따름
  → 서비스 간 trace가 끊기지 않음

패턴 2: 서비스별 다른 비율
  → 결제 서비스: 100% (장애 추적 중요)
  → 상품 목록 서비스: 1% (트래픽 많고 대부분 정상)
  → ParentBased는 그대로 적용해서 upstream 결정을 존중

패턴 3: Head + Tail 조합
  → SDK(Head): ParentBased + TraceIdRatio(0.2)로 20% 수집
  → Collector(Tail): 그 20% 중에서 에러/느린 것만 최종 저장
  → 수집 비용과 장애 추적 사이의 균형점
```

Sampler는 SDK(head-based)와 Collector(tail-based)에서 각각 다른 레이어로 동작한다. SDK Sampler는 span 생성 시점에 결정하고, Collector의 `tail_sampling` processor는 trace 전체가 도착한 후에 결정한다. 둘을 조합하면 SDK에서 대략적으로 걸러내고, Collector에서 정밀하게 선별하는 2단 구조가 된다.

### Instrumentation — 자동과 수동

#### Auto Instrumentation의 동작 원리

`@opentelemetry/auto-instrumentations-node`를 설치하고 `getNodeAutoInstrumentations()`을 호출하면, Express, HTTP, pg, ioredis 같은 라이브러리에 자동으로 계측이 걸린다. 이게 어떻게 되는 건가?

내부적으로 **monkey-patching** 방식으로 동작한다. 라이브러리가 export하는 함수나 메서드를 SDK가 가로채서, 원래 함수 실행 전후에 span 생성/종료 코드를 끼워 넣는다.

```
원래 동작:
  http.request(options) → 네트워크 요청 → 응답

패치 후 동작:
  http.request(options)
    → span 생성 (name: "HTTP GET", kind: CLIENT)
    → headers에 traceparent 주입
    → 원래 http.request 실행
    → 응답 수신
    → span에 status_code 속성 추가
    → span.end()
```

이게 SDK를 다른 모듈보다 먼저 초기화해야 하는 이유다. `require('http')`가 먼저 실행되면 원본 모듈이 이미 캐시에 올라간 상태라 패치할 타이밍을 놓친다. Node.js의 `require` 캐시 특성상, 한번 로드된 모듈은 다시 로드하지 않는다.

Java Agent(`-javaagent:opentelemetry-javaagent.jar`)는 더 저수준에서 동작한다. JVM의 bytecode instrumentation을 사용해서 클래스 로딩 시점에 바이트코드를 수정한다. 그래서 코드 수정 없이 JVM 옵션 하나로 계측이 가능하다.

#### Auto vs Manual 트레이드오프

```
Auto Instrumentation:
  장점
  - 코드 수정 없이 HTTP, DB, 메시지 큐 등 인프라 레벨 계측이 된다
  - 라이브러리 업데이트 시 계측도 자동으로 맞춰진다
  - 설정 몇 줄로 서비스 간 호출 관계가 Jaeger에 보인다

  한계
  - 비즈니스 로직의 의미를 모른다
    "결제 승인 단계"와 "포인트 적립 단계"를 구분 못 한다
    DB 쿼리가 느린 건 보이지만, 왜 그 쿼리가 실행됐는지는 모른다
  - 속성을 마음대로 못 붙인다
    order_id, user_tier 같은 비즈니스 속성이 없으면
    "느린 요청이 누구 건지" 파악할 수가 없다
  - monkey-patching이라 라이브러리 내부 구현이 바뀌면 깨질 수 있다
    실제로 OTel SDK 버전과 계측 대상 라이브러리 버전 사이에
    호환성 문제가 생기는 경우가 있다

Manual Instrumentation:
  장점
  - 비즈니스 로직 단위로 span을 만들 수 있다
    "장바구니 계산", "쿠폰 적용", "재고 확인" 각각을 span으로 분리
  - 원하는 속성을 자유롭게 추가할 수 있다
  - 코드에서 직접 제어하니까 동작이 예측 가능하다

  한계
  - 코드에 OTel 의존성이 들어간다
  - span 시작/종료를 빠뜨리면 트레이스가 깨진다
  - 코드 변경이 필요하다
```

#### 실무에서는 둘 다 쓴다

Auto로 인프라 레벨(HTTP, DB, 큐)을 깔고, 비즈니스 로직에 Manual로 커스텀 span을 추가하는 게 일반적이다.

```typescript
// Auto: Express 요청 진입, HTTP 클라이언트 호출, DB 쿼리가 자동으로 잡힌다
// Manual: 비즈니스 로직 단위를 직접 계측

async function processOrder(orderId: string) {
  // 이 span은 Express 요청 span의 자식으로 자동 연결된다
  return tracer.startActiveSpan('order.process', async (span) => {
    span.setAttribute('order.id', orderId);

    const items = await getOrderItems(orderId);    // auto: DB 쿼리 span 자동 생성
    const total = calculateTotal(items);            // manual 불필요 — 빠르고 단순한 로직

    // 결제는 중요하니까 manual span 추가
    await tracer.startActiveSpan('order.payment', async (paySpan) => {
      paySpan.setAttribute('payment.amount', total);
      await chargePayment(orderId, total);          // auto: HTTP 클라이언트 span 자동 생성
      paySpan.end();
    });

    span.end();
  });
}
```

Auto Instrumentation을 끌 때 — `getNodeAutoInstrumentations()`에서 특정 라이브러리를 비활성화할 수 있다. 파일 시스템(`fs`) 계측은 span이 너무 많이 생겨서 끄는 경우가 많다. DNS 계측도 마찬가지다.

```typescript
getNodeAutoInstrumentations({
  '@opentelemetry/instrumentation-fs': { enabled: false },
  '@opentelemetry/instrumentation-dns': { enabled: false },
});
```

---

## OTel과 기존 모니터링 도구의 관계

OTel은 Prometheus, Jaeger, Datadog 같은 도구를 **대체하는 게 아니다.** OTel의 역할은 데이터를 수집하고 전송하는 **계층**이고, 저장·쿼리·시각화는 기존 도구가 담당한다.

```
┌─────────────────────────────────────────────────────┐
│                    OTel의 영역                       │
│  계측 (SDK) → 수집/처리 (Collector) → 전송 (OTLP)   │
└──────────────────────────┬──────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌───────────┐    ┌──────────┐
    │ Jaeger   │    │Prometheus │    │ Datadog  │
    │ Tempo    │    │ Mimir     │    │ New Relic│
    │ Zipkin   │    │ Thanos    │    │ Dynatrace│
    └──────────┘    └───────────┘    └──────────┘
      트레이싱         메트릭          상용 APM
      저장/조회        저장/조회       저장/조회/알림
```

각 도구와의 관계를 정리하면:

**Prometheus** — OTel 이전에는 각 서비스에서 `/metrics` 엔드포인트를 노출하고 Prometheus가 pull 방식으로 수집했다. OTel을 쓰면 서비스는 OTLP로 Collector에 push하고, Collector의 prometheus exporter가 `/metrics`를 대신 노출하거나, `prometheusremotewrite` exporter로 직접 Prometheus에 쓴다. Prometheus 자체를 버리는 게 아니라, 수집 경로만 OTel로 통일하는 것이다.

**Jaeger / Tempo / Zipkin** — 분산 트레이싱 백엔드다. 예전에는 Jaeger client SDK로 직접 트레이스를 보냈지만, Jaeger가 공식적으로 자체 SDK를 deprecated하고 OTel SDK를 쓰라고 권장한다. Jaeger는 OTLP를 네이티브로 수신할 수 있어서 Collector에서 OTLP로 바로 보내면 된다.

**Datadog / New Relic / Dynatrace** — 상용 APM은 자체 에이전트와 SDK가 있지만, OTel로 데이터를 보내는 것도 지원한다. 벤더를 바꿀 때 코드 수정 없이 Collector의 exporter 설정만 변경하면 된다. 이게 OTel을 쓰는 가장 현실적인 이유다.

**Grafana** — 시각화 레이어다. OTel과 직접적인 관계는 없지만, Grafana가 Tempo(트레이스)·Mimir(메트릭)·Loki(로그) 스택을 밀고 있어서 OTel + Grafana 스택 조합을 많이 쓴다.

정리하면, OTel은 "데이터를 어떻게 만들고 보낼 것인가"를 표준화한 것이고, "데이터를 어디에 저장하고 어떻게 볼 것인가"는 각자 선택이다. 한 벤더에 종속되지 않는 것이 핵심이다.

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

## OTLP (OpenTelemetry Protocol)

OTLP는 OTel에서 텔레메트리 데이터를 전송하는 **표준 프로토콜**이다. SDK에서 Collector로, Collector에서 백엔드로 데이터를 보낼 때 사용한다.

### 직렬화 구조

OTLP는 **Protocol Buffers(protobuf)** 기반이다. `.proto` 파일로 메시지 스키마가 정의되어 있고, trace·metric·log 각각에 대한 메시지 타입이 있다. protobuf 바이너리 직렬화 덕분에 JSON보다 페이로드가 작고 파싱이 빠르다.

HTTP 전송에서는 protobuf 바이너리(`Content-Type: application/x-protobuf`)가 기본이고, JSON(`application/json`)도 지원한다. JSON은 디버깅 용도로 쓰고, 프로덕션에서는 protobuf를 쓴다.

### 전송 방식: gRPC vs HTTP

| | gRPC (포트 4317) | HTTP (포트 4318) |
|---|---|---|
| 직렬화 | protobuf 바이너리 | protobuf 바이너리 또는 JSON |
| 커넥션 | HTTP/2 멀티플렉싱 | HTTP/1.1 또는 HTTP/2 |
| 스트리밍 | 지원 | 미지원 |
| 프록시 통과 | HTTP/2 지원 필요 | 대부분의 프록시에서 동작 |
| 디버깅 | 바이너리라 curl 불가 | JSON 모드로 curl 가능 |

같은 Kubernetes 클러스터 안이라면 gRPC가 낫다. ALB나 Nginx 같은 L7 프록시를 거쳐야 하는 환경이면 HTTP가 설정이 단순하다.

### Signal별 엔드포인트 경로

HTTP 전송에서 각 signal 타입은 별도의 경로를 사용한다.

```
POST /v1/traces      — trace 데이터
POST /v1/metrics     — metric 데이터
POST /v1/logs        — log 데이터
```

gRPC에서는 경로 대신 protobuf 서비스 정의로 구분한다.

```
opentelemetry.proto.collector.trace.v1.TraceService/Export
opentelemetry.proto.collector.metrics.v1.MetricsService/Export
opentelemetry.proto.collector.logs.v1.LogsService/Export
```

SDK에서 exporter를 설정할 때 이 경로를 알아야 하는 경우가 있다. `OTEL_EXPORTER_OTLP_ENDPOINT`를 `http://collector:4318`로 설정하면 SDK가 signal별로 `/v1/traces`, `/v1/metrics`를 자동으로 붙인다. 하지만 `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`처럼 signal별 환경변수를 쓰면 전체 URL을 직접 지정해야 한다.

```bash
# 기본 엔드포인트 — SDK가 경로를 붙임
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318

# signal별 엔드포인트 — 전체 경로를 직접 지정
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://collector:4318/v1/traces
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://collector:4318/v1/metrics
```

이 차이를 모르면 exporter가 `/v1/traces/v1/traces` 같은 경로로 요청을 보내서 404 에러가 나는 경우가 있다.

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

### SpanKind — Span의 역할 구분

Span을 만들 때 `kind`를 지정할 수 있다. Jaeger나 Tempo에서 span을 시각화할 때 이 정보로 요청의 방향과 역할을 파악한다.

```
CLIENT   — 외부 서비스를 호출하는 쪽. HTTP 요청을 보내거나 gRPC call을 하는 span
SERVER   — 외부에서 들어온 요청을 처리하는 쪽. Express 핸들러, gRPC 서버 메서드
PRODUCER — 메시지를 큐에 넣는 쪽. Kafka produce, RabbitMQ publish
CONSUMER — 큐에서 메시지를 꺼내 처리하는 쪽. Kafka consume, RabbitMQ subscribe
INTERNAL — 서비스 내부 로직. 외부 호출이 아닌 비즈니스 로직 span (기본값)
```

자동 계측 라이브러리는 이걸 알아서 설정한다. Express instrumentation은 들어온 요청에 SERVER를, HTTP client instrumentation은 나가는 요청에 CLIENT를 붙인다. 직접 span을 만들 때만 신경 쓰면 된다.

```typescript
import { SpanKind } from '@opentelemetry/api';

// 다른 서비스를 호출하는 span — CLIENT
tracer.startActiveSpan('user-service.getUser', { kind: SpanKind.CLIENT }, async (span) => {
  const user = await fetch('http://user-service/api/users/123');
  span.end();
});

// Kafka에 메시지를 보내는 span — PRODUCER
tracer.startActiveSpan('orders.publish', { kind: SpanKind.PRODUCER }, async (span) => {
  await kafka.producer.send({ topic: 'orders', messages: [{ value: orderJson }] });
  span.end();
});

// 서비스 내부 계산 — INTERNAL (기본값이라 생략 가능)
tracer.startActiveSpan('payment.calculateFee', async (span) => {
  const fee = calculateFee(amount);
  span.end();
  return fee;
});
```

CLIENT와 SERVER span은 짝을 이룬다. 서비스 A의 CLIENT span과 서비스 B의 SERVER span이 같은 trace 안에서 부모-자식 관계로 연결되면, Jaeger에서 서비스 간 호출 관계를 그릴 수 있다. PRODUCER와 CONSUMER도 마찬가지로 짝을 이룬다.

kind를 잘못 지정하면 Jaeger의 서비스 의존성 그래프(DAG)가 엉뚱하게 나온다. 내부 로직인데 CLIENT로 지정하면 존재하지 않는 외부 서비스 호출처럼 보인다.

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

### Propagator — 컨텍스트 전파 포맷

위 코드에서 `propagation.inject()`가 HTTP 헤더에 트레이스 컨텍스트를 넣는데, 어떤 헤더 포맷을 쓸지 결정하는 게 **Propagator**다.

**W3C TraceContext (기본값)**

OTel SDK의 기본 propagator다. `traceparent`와 `tracestate` 두 개의 헤더를 사용한다.

```
traceparent: 00-a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4-1a2b3c4d5e6f7a8b-01
             │   │                                  │                  │
             버전  trace-id (32자)                    span-id (16자)     샘플링 플래그
```

W3C 표준이라 대부분의 APM 도구와 클라우드 서비스가 지원한다. 특별한 이유가 없으면 이걸 쓰면 된다.

**B3 (Zipkin 호환)**

Zipkin에서 시작된 포맷이다. 기존에 Zipkin 기반 트레이싱을 쓰고 있는 환경에서 마이그레이션할 때 필요하다.

```
# B3 Multi-header (각각 별도 헤더)
X-B3-TraceId: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
X-B3-SpanId: 1a2b3c4d5e6f7a8b
X-B3-ParentSpanId: 0000000000000000
X-B3-Sampled: 1

# B3 Single-header (한 줄)
b3: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4-1a2b3c4d5e6f7a8b-1
```

**Propagator 설정**

NodeSDK는 기본으로 W3C TraceContext + W3C Baggage propagator를 등록한다. B3가 필요하면 직접 추가해야 한다.

```typescript
import { CompositePropagator } from '@opentelemetry/core';
import { W3CTraceContextPropagator } from '@opentelemetry/core';
import { W3CBaggagePropagator } from '@opentelemetry/core';
import { B3Propagator, B3InjectEncoding } from '@opentelemetry/propagator-b3';

const sdk = new NodeSDK({
  textMapPropagator: new CompositePropagator({
    propagators: [
      new W3CTraceContextPropagator(),
      new W3CBaggagePropagator(),
      new B3Propagator({ injectEncoding: B3InjectEncoding.MULTI_HEADER }),
    ],
  }),
  // ...
});
```

`CompositePropagator`를 쓰면 여러 포맷을 동시에 주입/추출한다. Zipkin 기반 서비스와 OTel 기반 서비스가 공존하는 마이그레이션 기간에 유용하다. inject 시에는 모든 포맷의 헤더를 넣고, extract 시에는 있는 헤더를 순서대로 찾아서 읽는다.

선택 기준은 단순하다:

- 새 프로젝트: W3C TraceContext만 쓴다
- 기존 Zipkin 환경 마이그레이션 중: B3 + W3C 둘 다 쓰다가 B3를 뺀다
- AWS X-Ray 연동: `AWSXRayPropagator`를 추가한다 (`@opentelemetry/propagator-aws-xray`)

propagator를 직접 설정하면서 `W3CBaggagePropagator`를 빠뜨리는 실수가 잦다. 이러면 Baggage 전파가 안 돼서 downstream 서비스에서 baggage를 읽을 수 없다.

---

## OTel Logs 모델

OTel의 Logs는 Traces, Metrics와 접근 방식이 다르다. Traces와 Metrics는 OTel API로 직접 생성하지만, Logs는 **기존 로거(winston, pino, log4j 등)를 그대로 쓰면서 OTel 파이프라인에 연결하는 방식**이다. 이걸 Log Bridge API라고 한다.

### 왜 Log Bridge인가

대부분의 애플리케이션에는 이미 로거가 있다. winston이든 pino든 이미 로그를 찍고 있는데, OTel을 도입했다고 로거를 전부 교체하는 건 비현실적이다. 그래서 OTel은 로그 생성 자체를 맡지 않고, 기존 로거가 만든 로그를 OTel의 LogRecord로 변환해서 Collector로 보내는 **브릿지** 역할만 한다.

```
기존 방식:
  winston → console/file → Fluentd → Loki

OTel 방식:
  winston → Log Bridge → OTLP → Collector → Loki
            (OTel SDK)
```

### LogRecord 구조

OTel의 LogRecord는 다음 필드로 구성된다.

```
Timestamp           — 로그 발생 시각 (nanosecond 정밀도)
ObservedTimestamp   — OTel이 로그를 수집한 시각
SeverityNumber      — 로그 레벨 (1~24, INFO=9, ERROR=17)
SeverityText        — "INFO", "ERROR" 같은 문자열
Body                — 로그 메시지 본문
Attributes          — 키-값 쌍 (orderId, userId 등)
Resource            — 서비스 정보 (service.name 등, SDK에서 자동 설정)
InstrumentationScope — 로거 이름/버전
TraceId             — 연관된 trace ID (있으면 자동 연결)
SpanId              — 연관된 span ID
TraceFlags          — 샘플링 플래그
```

`TraceId`와 `SpanId`가 LogRecord에 포함되기 때문에, 로그와 트레이스를 자동으로 연결할 수 있다. 이게 기존 로깅 파이프라인(Fluentd 등)으로는 직접 구현해야 했던 부분이다.

### Node.js에서 Log Bridge 설정

```typescript
import { logs, SeverityNumber } from '@opentelemetry/api-logs';
import { LoggerProvider, SimpleLogRecordProcessor } from '@opentelemetry/sdk-logs';
import { OTLPLogExporter } from '@opentelemetry/exporter-logs-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SEMRESATTRS_SERVICE_NAME } from '@opentelemetry/semantic-conventions';

const loggerProvider = new LoggerProvider({
  resource: new Resource({
    [SEMRESATTRS_SERVICE_NAME]: 'payment-service',
  }),
});

loggerProvider.addLogRecordProcessor(
  new SimpleLogRecordProcessor(
    new OTLPLogExporter({
      url: 'http://otel-collector:4318/v1/logs',
    })
  )
);

logs.setGlobalLoggerProvider(loggerProvider);
```

### winston과 연동

`@opentelemetry/winston-transport`를 쓰면 winston 로그가 OTel LogRecord로 변환돼서 Collector로 전송된다. 기존 winston 설정은 그대로 두고 transport만 추가하면 된다.

```typescript
import winston from 'winston';
import { OpenTelemetryTransportV3 } from '@opentelemetry/winston-transport';

const logger = winston.createLogger({
  transports: [
    new winston.transports.Console(),           // 기존 콘솔 출력 유지
    new OpenTelemetryTransportV3(),              // OTel로도 전송
  ],
});

// 기존 코드 수정 없이 그대로 사용
logger.info('결제 처리 시작', { orderId: 'ORD-123', amount: 50000 });
// → 콘솔에도 출력되고, Collector에 LogRecord로도 전송됨
// → 현재 active span이 있으면 TraceId, SpanId가 자동으로 붙음
```

### pino와 연동

pino는 `pino-opentelemetry-transport`를 사용한다.

```typescript
import pino from 'pino';

const logger = pino({
  transport: {
    targets: [
      { target: 'pino-pretty', level: 'info' },   // 기존 출력
      {
        target: 'pino-opentelemetry-transport',     // OTel 전송
        options: {
          resourceAttributes: { 'service.name': 'payment-service' },
        },
      },
    ],
  },
});
```

### Collector에서 Logs 파이프라인

Collector는 OTLP로 받은 로그를 처리해서 Loki, Elasticsearch 등으로 보낸다.

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
  # 로그에서 민감 정보 제거
  attributes/logs:
    actions:
      - key: user.email
        action: hash
      - key: db.statement
        action: delete

exporters:
  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [batch, attributes/logs]
      exporters: [loki]
```

### 기존 로깅 파이프라인과의 비교

기존에 Fluentd/Fluent Bit로 로그를 수집하고 있었다면, OTel Logs로 당장 전부 교체할 필요는 없다. OTel Logs의 장점은 trace context가 자동으로 연결된다는 것과, Collector 하나로 trace·metric·log를 모두 처리할 수 있다는 점이다. 반면 Fluentd 생태계의 플러그인이 더 풍부하고, 파일 기반 로그 수집은 Fluent Bit가 더 성숙하다.

실무에서는 OTel SDK에서 Log Bridge로 Collector에 보내는 것과, 파일 로그를 Fluent Bit로 수집하는 것을 병행하다가 점진적으로 OTel로 옮기는 경우가 많다.

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
