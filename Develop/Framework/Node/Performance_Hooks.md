---
title: Node.js perf_hooks 모듈 심화
tags:
  - nodejs
  - perf_hooks
  - performance
  - event-loop
  - profiling
  - apm
updated: 2026-06-03
---

# Node.js perf_hooks 모듈 심화

`perf_hooks`는 Node 프로세스 안에서 시간과 이벤트 루프 상태를 들여다보는 코어 모듈이다. 외부 APM 없이도 "이 함수 진짜 느린가", "지금 이벤트 루프 막힌 거 맞나"를 숫자로 답할 수 있다. APM을 쓰더라도 어떻게 데이터가 수집되는지 알면 대시보드만 보고 추측하는 일을 줄인다.

운영에서 부딪힌 케이스를 중심으로 정리한다. 단순 API 나열보다는 어떤 상황에서 어떤 도구를 꺼내야 하는지가 중요하다.

---

## 1. performance.now와 Date.now 차이

가장 먼저 마주치는 함수다.

```javascript
const { performance } = require('node:perf_hooks');

const start = performance.now();
await doSomething();
const elapsed = performance.now() - start;
```

`Date.now()`로도 비슷한 측정이 되는데 굳이 `performance.now()`를 쓰는 이유가 있다.

- `Date.now()`는 시스템 시계라 NTP 동기화나 사용자 시계 변경에 영향을 받는다. 측정 중에 시계가 뒤로 가면 음수가 나올 수 있다.
- `performance.now()`는 단조 증가(monotonic)다. 프로세스가 시작된 시점을 기준으로 한 상대 시간이라 뒤로 가지 않는다.
- 해상도가 마이크로초 수준이다. `Date.now()`는 밀리초 정수다.

벤치마크나 SLA 측정에는 무조건 `performance.now()`다. 로그 타임스탬프처럼 절대 시간이 필요한 곳은 `Date.now()`나 `new Date()`를 쓴다. 둘을 섞어 쓰면 한쪽은 ms, 한쪽은 fractional ms를 반환하니 단위가 깨진다.

---

## 2. mark와 measure로 코드 구간 측정

`mark`는 시점을 찍고, `measure`는 두 mark 사이의 간격을 계산한다.

```javascript
const { performance, PerformanceObserver } = require('node:perf_hooks');

performance.mark('db-query-start');
const rows = await db.query('SELECT ...');
performance.mark('db-query-end');

performance.measure('db-query', 'db-query-start', 'db-query-end');
```

이렇게만 쓰면 측정 결과를 어디서도 볼 수 없다. `PerformanceObserver`를 붙여야 값이 나온다.

```javascript
const observer = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    console.log(`${entry.name}: ${entry.duration.toFixed(2)}ms`);
  }
});

observer.observe({ entryTypes: ['measure'] });
```

처음 써보면 "왜 이렇게 번거롭게 만들었나" 싶은데, 옵저버 패턴이 강제되어 있어서 측정 코드와 수집 코드가 분리된다. 라이브러리에서 mark만 찍어두고 사용자가 옵저버를 붙여 수집하는 식으로 설계할 수 있다.

### mark/measure를 쓸 때 주의할 점

엔트리가 메모리에 계속 쌓인다. 기본 버퍼는 무제한이고, 옵저버가 처리한 뒤에도 `performance.getEntries()`로 조회 가능한 상태가 유지된다. 장시간 실행되는 서버에서 mark를 막 찍으면 서서히 메모리가 늘어난다.

```javascript
performance.clearMarks();
performance.clearMeasures();
```

옵저버 콜백에서 처리가 끝났다면 비워줘야 한다. 아니면 옵저버 옵션에 `buffered: true`를 빼고, 자동으로 쌓이지 않게 한다. 운영 서버에서는 측정 후 즉시 비우는 패턴이 안전하다.

```javascript
const observer = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    sendMetric(entry.name, entry.duration);
  }
  performance.clearMarks();
  performance.clearMeasures();
});
observer.observe({ entryTypes: ['measure'], buffered: false });
```

### startTime을 직접 지정하는 측정

`measure`의 세 번째 인자로 옵션 객체를 넘기면 mark 없이도 측정이 가능하다. 외부에서 받은 타임스탬프 기준으로 구간을 표시할 때 쓴다.

```javascript
const requestStart = performance.now();
// ... 작업 수행 ...
performance.measure('request', {
  start: requestStart,
  end: performance.now(),
  detail: { route: '/api/users', method: 'GET' },
});
```

`detail`로 임의의 메타데이터를 실어 보낼 수 있다. 옵저버 콜백에서 `entry.detail`로 받는다. 라우트별로 태그를 붙여 분류할 때 자주 쓴다.

---

## 3. PerformanceObserver로 GC와 함수 호출 추적

`entryTypes`에 무엇을 넣느냐에 따라 추적 대상이 달라진다.

| entryType | 추적 대상 |
|---|---|
| `measure` | 직접 만든 측정 |
| `mark` | 직접 찍은 마크 |
| `gc` | V8 가비지 컬렉션 사이클 |
| `function` | `performance.timerify`로 감싼 함수 |
| `http` | 들어오는 HTTP 요청 (server) |
| `http2` | HTTP/2 세션 |
| `dns` | DNS 조회 |
| `net` | TCP 소켓 연결 |

### GC 추적

```javascript
const { PerformanceObserver, constants } = require('node:perf_hooks');

const gcObserver = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    const kind = {
      [constants.NODE_PERFORMANCE_GC_MAJOR]: 'major',
      [constants.NODE_PERFORMANCE_GC_MINOR]: 'minor',
      [constants.NODE_PERFORMANCE_GC_INCREMENTAL]: 'incremental',
      [constants.NODE_PERFORMANCE_GC_WEAKCB]: 'weak-callback',
    }[entry.detail.kind];

    console.log(`GC ${kind}: ${entry.duration.toFixed(2)}ms`);
  }
});
gcObserver.observe({ entryTypes: ['gc'] });
```

GC 시간이 한 사이클에 100ms 넘어가면 의심해야 한다. major GC가 자주 일어나거나 한 번에 길게 멈춘다면 메모리 누수나 큰 오브젝트 할당 패턴을 봐야 한다. heap 스냅샷을 떠서 분석하는 단계로 넘어간다.

운영에서 한 번은 Promise 체인을 깊게 만든 코드가 minor GC를 분당 수천 번 발생시킨 적이 있다. 이런 케이스는 평균 응답시간으로는 안 보이고 p99에서만 튄다.

### timerify로 함수 호출 시간 자동 측정

```javascript
const slowFn = (n) => {
  let sum = 0;
  for (let i = 0; i < n; i++) sum += i;
  return sum;
};

const timed = performance.timerify(slowFn);

const observer = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    console.log(`${entry.name}: ${entry.duration.toFixed(3)}ms`);
  }
});
observer.observe({ entryTypes: ['function'] });

timed(1_000_000);
```

`timerify`는 함수를 감싸 호출할 때마다 자동으로 entry를 만든다. 매번 mark를 찍기 귀찮은 핫 경로에 쓰면 편하다. 단 함수 식별이 이름으로 되니까 익명 함수는 의미 없는 이름이 찍힌다.

### HTTP 추적

```javascript
const observer = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    console.log(`HTTP ${entry.name}: ${entry.duration}ms`);
  }
});
observer.observe({ entryTypes: ['http'] });
```

내장 `http` 모듈이 만든 요청만 잡힌다. Express나 Fastify가 결국 같은 모듈을 쓰니까 잡히기는 하는데, 라우트 정보가 없어서 활용도가 떨어진다. 라우트별 측정은 프레임워크 미들웨어 단에서 직접 mark/measure를 박는 편이 낫다.

---

## 4. eventLoopUtilization으로 이벤트 루프 포화 감지

이벤트 루프가 얼마나 바쁜지 0~1 사이 값으로 보여준다. CPU 사용률과 비슷한 개념인데 이벤트 루프 관점이다.

```javascript
const { performance } = require('node:perf_hooks');

let prev = performance.eventLoopUtilization();

setInterval(() => {
  const current = performance.eventLoopUtilization();
  const utilization = performance.eventLoopUtilization(current, prev);
  console.log(`ELU: ${(utilization.utilization * 100).toFixed(1)}%`);
  prev = current;
}, 1000);
```

`utilization.idle`은 루프가 idle 상태에 있던 시간, `active`는 일하고 있던 시간이다. `utilization`은 `active / (active + idle)`이다.

ELU가 0.7 이상이면 곧 응답 지연이 시작된다고 봐도 된다. 0.9 넘어가면 새 요청 처리가 거의 불가능해진다. 로드밸런서의 헬스체크에 ELU를 반영하면 포화된 인스턴스로 트래픽이 더 가는 걸 막을 수 있다.

```javascript
// 헬스체크 예시
app.get('/health', (req, res) => {
  const elu = performance.eventLoopUtilization(current, prev);
  if (elu.utilization > 0.85) {
    return res.status(503).json({ status: 'overloaded', elu: elu.utilization });
  }
  res.json({ status: 'ok' });
});
```

CPU 사용률만 보면 안 되는 이유는, Node 프로세스는 싱글 스레드라 CPU 코어 하나만 쓴다. 8코어 머신에서 CPU 12% 쓰고 있어도 그 코어 하나는 100%일 수 있다. ELU는 그 코어가 실제로 얼마나 일하는지를 보여준다.

### 워커 스레드와 ELU

`worker_threads`로 만든 워커도 자기 ELU를 가진다.

```javascript
const { Worker } = require('node:worker_threads');
const worker = new Worker('./worker.js');

setInterval(() => {
  const elu = worker.performance.eventLoopUtilization();
  console.log(`Worker ELU: ${elu.utilization}`);
}, 1000);
```

CPU 바운드 작업을 워커로 분리했을 때 메인 루프와 워커 루프를 따로 봐야 한다. 메인은 한가한데 워커가 포화 상태면 워커 풀을 늘려야 한다는 판단이 가능하다.

---

## 5. monitorEventLoopDelay 히스토그램

ELU가 "얼마나 바쁜지"라면 `monitorEventLoopDelay`는 "한 번 깰 때 얼마나 늦었는지"를 본다. 평균만 보면 의미가 없고 히스토그램으로 분포를 봐야 한다.

```javascript
const { monitorEventLoopDelay } = require('node:perf_hooks');

const histogram = monitorEventLoopDelay({ resolution: 20 });
histogram.enable();

setInterval(() => {
  console.log({
    min: histogram.min / 1e6,
    max: histogram.max / 1e6,
    mean: histogram.mean / 1e6,
    p50: histogram.percentile(50) / 1e6,
    p99: histogram.percentile(99) / 1e6,
    p999: histogram.percentile(99.9) / 1e6,
  });
  histogram.reset();
}, 10_000);
```

값은 나노초 단위로 나온다. 1e6으로 나눠서 밀리초로 본다.

`resolution`은 샘플링 간격이다. 기본 10ms인데 너무 짧으면 그 자체로 부하가 된다. 운영에서는 20~50ms 정도가 적당하다.

### 무엇을 보아야 하는가

- p50이 1ms 아래라면 건강한 상태
- p99가 10ms를 넘어가면 어딘가 블로킹 코드가 있다
- p99.9가 100ms를 넘어가면 사용자가 체감하는 응답 지연이 시작된 것

평균(mean)만 보면 안 된다. 평균은 1ms인데 p99는 200ms인 경우를 자주 본다. 한두 번의 블로킹 호출이 전체 분포를 망치는데, 평균에 묻혀서 안 보인다. SLA 측정은 항상 p99, p99.9로 한다.

### 블로킹 코드 찾기

p99가 튀는데 어디서 막히는지 모를 때는 `--inspect`로 프로파일을 뜬다. 히스토그램이 튀는 시점과 프로파일의 long task를 맞춰보면 원인이 보인다.

```bash
node --inspect=0.0.0.0:9229 app.js
```

Chrome DevTools에서 Performance 탭을 열고 Record를 누른 뒤 부하를 준다. 50ms 이상 걸리는 long task가 빨갛게 표시된다. 보통 동기 JSON 파싱, `crypto.pbkdf2Sync`처럼 sync로 끝나는 API, 큰 정규식, 동기 zlib 호출이 범인이다.

---

## 6. 실제 운영에서 쓰는 조합

세 가지를 동시에 돌리는 게 기본이다.

```javascript
const { performance, PerformanceObserver, monitorEventLoopDelay } = require('node:perf_hooks');

// 1. ELU 1초 단위
let prevElu = performance.eventLoopUtilization();
setInterval(() => {
  const current = performance.eventLoopUtilization();
  const delta = performance.eventLoopUtilization(current, prevElu);
  metrics.gauge('node.eventloop.utilization', delta.utilization);
  prevElu = current;
}, 1000);

// 2. 이벤트 루프 지연 히스토그램, 10초마다 플러시
const loopDelay = monitorEventLoopDelay({ resolution: 20 });
loopDelay.enable();
setInterval(() => {
  metrics.gauge('node.eventloop.delay.p50', loopDelay.percentile(50) / 1e6);
  metrics.gauge('node.eventloop.delay.p99', loopDelay.percentile(99) / 1e6);
  metrics.gauge('node.eventloop.delay.p999', loopDelay.percentile(99.9) / 1e6);
  loopDelay.reset();
}, 10_000);

// 3. GC 추적
const gcObserver = new PerformanceObserver((items) => {
  for (const entry of items.getEntries()) {
    metrics.histogram('node.gc.duration', entry.duration, {
      kind: entry.detail.kind,
    });
  }
});
gcObserver.observe({ entryTypes: ['gc'] });
```

이 세 가지만 잘 봐도 Node 프로세스의 건강 상태를 90% 이상 진단할 수 있다. 메모리는 별도로 `process.memoryUsage()`를 같이 본다.

---

## 7. APM 도구와의 연동 지점

Datadog, New Relic, Elastic APM 같은 도구도 결국 `perf_hooks`와 `async_hooks`를 기반으로 만들어졌다. 직접 만든 측정과 APM이 어떻게 어울리는지 알아두면 좋다.

### Datadog dd-trace

dd-trace는 `async_hooks`로 컨텍스트를 전파하고, 자체 트레이서로 span을 만든다. 사용자 코드에서 `performance.measure`를 호출해도 dd-trace의 span에는 자동으로 합쳐지지 않는다. 이 둘을 연결하려면 직접 span을 만들어야 한다.

```javascript
const tracer = require('dd-trace');

async function fetchUser(id) {
  return tracer.trace('db.fetchUser', async (span) => {
    span.setTag('user.id', id);
    const start = performance.now();
    const user = await db.findById(id);
    span.setTag('duration_ms', performance.now() - start);
    return user;
  });
}
```

dd-trace가 자동 계측하는 모듈(express, mongodb, redis 등) 밖의 커스텀 로직은 이렇게 직접 span을 박는다. `perf_hooks`로 따로 측정하면 APM 대시보드에는 안 보이고 자체 로그에만 남는다.

### New Relic newrelic 모듈

비슷하게 `newrelic.startSegment` 같은 API로 직접 세그먼트를 만든다. New Relic 에이전트는 내부적으로 V8의 inspector 프로토콜을 쓰는 부분이 있어서 `--inspect`와 같이 켜면 충돌할 때가 있다. 운영 환경에서 `--inspect`는 보통 끄고, 프로파일링이 필요할 때만 별도로 띄운다.

### OpenTelemetry

표준 트레이싱 스펙이다. `@opentelemetry/sdk-node`를 쓰면 자체 측정과 자동 계측을 한 곳에 모을 수 있다.

```javascript
const { trace } = require('@opentelemetry/api');
const tracer = trace.getTracer('my-app');

async function fetchUser(id) {
  return tracer.startActiveSpan('db.fetchUser', async (span) => {
    span.setAttribute('user.id', id);
    try {
      return await db.findById(id);
    } finally {
      span.end();
    }
  });
}
```

`perf_hooks`의 `measure`를 OpenTelemetry span으로 자동 변환하는 라이브러리는 없다. 두 시스템을 동시에 운영하면 측정 코드를 두 번 쓰게 된다. 보통 OpenTelemetry로 통일하고 `perf_hooks`는 ELU나 loop delay 같은 프로세스 레벨 지표 수집에만 쓴다.

### Prometheus 노출

APM 없이 Prometheus만 쓸 때는 `prom-client`와 조합한다.

```javascript
const client = require('prom-client');

const eluGauge = new client.Gauge({
  name: 'nodejs_eventloop_utilization',
  help: 'Event loop utilization (0-1)',
});

const loopDelayHistogram = new client.Summary({
  name: 'nodejs_eventloop_delay_seconds',
  help: 'Event loop delay',
  percentiles: [0.5, 0.9, 0.99, 0.999],
});

let prev = performance.eventLoopUtilization();
const histogram = monitorEventLoopDelay({ resolution: 20 });
histogram.enable();

setInterval(() => {
  const current = performance.eventLoopUtilization();
  eluGauge.set(performance.eventLoopUtilization(current, prev).utilization);
  prev = current;
}, 1000);
```

`prom-client`에는 `prom-client.collectDefaultMetrics()`라는 게 있어서 GC, heap, ELU를 기본으로 수집해준다. 직접 짜기 전에 이걸 먼저 확인한다.

---

## 8. 프로덕션에서 자주 빠지는 함정

### 옵저버를 등록만 하고 disconnect 안 함

테스트 코드나 짧게 도는 스크립트에서는 문제 없는데, 모듈을 동적으로 로드/언로드하는 환경에서는 옵저버가 계속 쌓인다. `observer.disconnect()`를 명시적으로 호출해야 한다.

### `buffered: true`로 무한히 쌓기

옵저버 옵션에 `buffered: true`를 주면 콜백이 호출되기 전 모든 엔트리를 버퍼링한다. 빈번한 이벤트(GC, http)에서 이걸 쓰면 콜백이 한 번에 거대한 배열을 받는다. 콜백 호출이 늦어지는 사이에 메모리가 폭증한다.

### timerify를 async 함수에 쓸 때

`timerify`는 함수 호출부터 반환까지를 잰다. async 함수면 Promise 객체 반환까지의 시간만 잰다. 실제 await가 끝날 때까지가 아니다. async 함수 측정은 mark/measure로 직접 박는 게 정확하다.

```javascript
// 잘못된 측정
const timedAsync = performance.timerify(async () => {
  await sleep(1000);
  return 'done';
});
// 측정값은 ~0ms로 나온다. Promise 객체 만드는 시간만 재기 때문이다.
```

### 운영에 mark를 너무 자주 찍을 때

요청마다 mark를 10개씩 찍으면 초당 만 요청 환경에서 분당 600만 개의 엔트리가 생긴다. 옵저버가 처리하는 속도보다 생성 속도가 빠르면 백프레셔가 걸린다. 핵심 구간만 찍고, 나머지는 샘플링한다. 1%만 측정해도 통계적으로 충분한 경우가 많다.

### --inspect를 운영에 켜둠

`--inspect=0.0.0.0:9229`로 켜놓으면 외부에서 디버거 접속이 된다. 코드 실행, 변수 조회, 메모리 덤프가 다 된다. 외부에 노출되면 그대로 RCE다. 운영 컨테이너에서는 끄고, 문제가 생기면 그때만 SSH 터널로 띄운다.

---

## 9. 마무리

`perf_hooks`는 익숙해지면 운영의 시야가 넓어진다. APM 대시보드가 보여주는 숫자가 어떻게 만들어지는지 알게 되고, APM이 못 잡는 영역(워커 풀, 자체 큐, 도메인 로직)을 직접 들여다볼 수 있다. 처음에는 ELU와 monitorEventLoopDelay 두 개만 노출시키는 것부터 시작해도 충분하다. 평균 응답시간이 멀쩡한데 가끔 사용자가 느리다고 하는 케이스의 절반은 이 두 지표만 봐도 원인이 보인다.
