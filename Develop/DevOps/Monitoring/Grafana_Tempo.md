---
title: Grafana Tempo
tags: [devops, monitoring, observability, aws]
updated: 2026-07-31
---

# Grafana Tempo

## Tempo가 무엇인지

Grafana Tempo는 분산 트레이스를 저장하고 검색하는 백엔드다. OTel Collector나 앱에서 직접 OTLP로 트레이스를 받아 오브젝트 스토리지(S3, GCS 등)에 저장한다.

Jaeger가 Elasticsearch 같은 검색 엔진을 붙여 트레이스 전체를 인덱싱하는 방식이라면, Tempo는 기본적으로 Trace ID만 인덱싱한다. 나머지는 오브젝트 스토리지에 블록으로 쌓고, 검색이 들어오면 블록 전체를 스캔한다. 이 구조 덕분에 스토리지 비용이 낮지만, Trace ID 없이 서비스명·스팬 속성으로 검색하려면 별도 설정이 필요하다.

Grafana Cloud나 자체 Loki·Prometheus 스택을 이미 운영 중이라면 Tempo를 붙이는 게 자연스럽다. Grafana UI 하나에서 메트릭→트레이스→로그를 넘나드는 흐름이 가능해진다. Jaeger만 단독으로 쓰면 이 연결이 안 된다.

---

## Jaeger와 선택 기준

Tempo와 Jaeger 중 하나를 선택해야 하는 상황이 자주 온다. 선택 기준을 정리하면 아래와 같다.

Jaeger를 선택하는 경우:
- Grafana 스택 없이 트레이스만 독립적으로 운영할 때
- Jaeger UI에 익숙한 팀원이 있고 셋업 부담을 줄이고 싶을 때
- 소규모 서비스라 로컬 스토리지로도 충분할 때

Tempo를 선택하는 경우:
- Grafana + Loki + Prometheus를 이미 쓰고 있을 때
- Grafana Explore에서 메트릭과 트레이스를 같이 보고 싶을 때
- 트레이스 볼륨이 커서 S3 비용이 Elasticsearch 운영 비용보다 쌀 때
- TraceQL로 조건 기반 트레이스 검색이 필요할 때

Jaeger는 all-in-one 바이너리로 로컬에 바로 뜨는 게 편하다. 프로덕션에서 Elasticsearch 없이 버티는 건 금방 한계가 온다. Tempo는 처음 설정이 조금 더 복잡하지만, 오브젝트 스토리지와 붙이면 운영 부담이 줄어든다.

---

## 아키텍처

```
앱 (OTel SDK)
   │ OTLP/HTTP or gRPC
   ▼
OTel Collector
   │ OTLP/gRPC
   ▼
Grafana Tempo
   │ 블록 저장
   ▼
S3 (or local)
```

앱에서 직접 Tempo로 OTLP를 보내는 것도 가능하지만, OTel Collector를 중간에 두는 게 낫다. Collector에서 샘플링, 필터링, 배치 처리를 조절할 수 있고, Tempo를 교체해도 앱 설정을 건드리지 않아도 된다.

---

## Tempo 설치 및 기본 설정

### docker-compose로 로컬 셋업

```yaml
version: '3.8'
services:
  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo-data:/var/tempo
    ports:
      - "3200:3200"   # Tempo HTTP API
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP

volumes:
  tempo-data:
```

### tempo.yaml — 로컬 스토리지

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

ingester:
  max_block_bytes: 1_000_000
  max_block_duration: 5m

compactor:
  compaction:
    block_retention: 48h

storage:
  trace:
    backend: local
    local:
      path: /var/tempo/blocks
    wal:
      path: /var/tempo/wal

query_frontend:
  search:
    duration_slo: 5s
    throughput_bytes_slo: 1.073741824e+09
  trace_by_id:
    duration_slo: 5s
```

로컬 스토리지는 개발·스테이징 환경에서 쓴다. `block_retention`을 짧게 잡지 않으면 디스크가 금방 찬다. 프로덕션에서 로컬 스토리지를 쓰는 것은 재시작 시 데이터 유실 위험이 있어서 권장하지 않는다.

---

## S3 스토리지 구성

프로덕션에서는 S3나 GCS를 백엔드로 쓴다.

```yaml
storage:
  trace:
    backend: s3
    s3:
      bucket: my-tempo-traces
      endpoint: s3.ap-northeast-2.amazonaws.com
      region: ap-northeast-2
      # IAM Role로 인증할 때는 access_key/secret_key 생략
      # access_key: <KEY>
      # secret_key: <SECRET>
    wal:
      path: /var/tempo/wal
```

S3를 쓸 때 주의할 점:

- WAL(Write-Ahead Log)은 로컬 디스크에 둔다. Tempo는 트레이스를 받으면 WAL에 먼저 쓰고, 이후 S3로 플러시한다. WAL 경로가 없거나 디스크가 꽉 차면 트레이스가 유실된다.
- S3 버킷 라이프사이클 정책을 `block_retention`과 맞춰야 한다. Tempo가 블록을 지워도 S3에 남아있으면 비용이 나오고, S3가 먼저 지우면 Tempo가 블록을 못 찾아 오류가 난다.
- IAM Role 기반 인증을 쓰면 `access_key`/`secret_key` 노출 위험이 없다. Kubernetes라면 IRSA(IAM Roles for Service Accounts)를 쓴다.
- 멀티 테넌시가 필요 없으면 `multitenancy_enabled: false`(기본값)로 둔다. 켜면 요청마다 `X-Scope-OrgID` 헤더가 필요해진다.

---

## OTel Collector → Tempo 연동

OTel Collector 설정에서 exporter를 Tempo의 OTLP 엔드포인트로 지정한다.

```yaml
# otel-collector-config.yaml

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

  # 샘플링: 에러 트레이스는 100%, 나머지는 10%
  probabilistic_sampler:
    sampling_percentage: 10

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/tempo]
```

샘플링 설정은 Collector에서 하는 게 좋다. 앱에서 100% 트레이스를 보내고 Collector가 걸러내면, 앱 코드를 바꾸지 않아도 샘플링 비율을 조절할 수 있다.

`probabilistic_sampler`는 무작위로 비율을 정하는 헤드 샘플링이다. 에러 트레이스를 놓치는 문제가 있다. 에러는 반드시 잡고 싶다면 `tail_sampling` 프로세서를 써야 한다. 단, tail sampling은 Collector가 스팬을 모아서 판단해야 하므로 메모리 사용량이 올라간다.

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors-policy
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow-traces-policy
        type: latency
        latency: {threshold_ms: 1000}
      - name: probabilistic-policy
        type: probabilistic
        probabilistic: {sampling_percentage: 5}
```

---

## TraceQL로 트레이스 검색

Tempo 2.0부터 TraceQL이 도입됐다. Trace ID 없이 조건으로 트레이스를 검색할 수 있다.

기본 문법은 `{}` 안에 조건을 쓰는 것이다.

```
# 에러가 발생한 트레이스
{ status = error }

# payment-service에서 1초 이상 걸린 트레이스
{ resource.service.name = "payment-service" && duration > 1s }

# HTTP 500 응답이 있는 트레이스
{ span.http.response.status_code = 500 }

# 특정 사용자 ID가 포함된 트레이스
{ span.user.id = "user-123" }

# 특정 DB 쿼리가 포함된 트레이스
{ span.db.statement =~ ".*SELECT.*users.*" }
```

스팬 집계도 가능하다.

```
# payment-service 스팬의 p99 지연 시간
{ resource.service.name = "payment-service" } | rate() by (span.http.route)

# 에러율이 높은 엔드포인트 찾기
{ status = error } | rate() by (resource.service.name, span.http.route)
```

TraceQL 검색은 Tempo의 블록 전체를 스캔하기 때문에 범위가 넓을수록 느리다. 시간 범위를 좁히거나 `resource.service.name`을 지정하면 스캔 범위가 줄어든다. Grafana Explore에서 "Search" 탭을 쓰면 UI로 조건을 조합할 수 있고, "TraceQL" 탭에서 직접 쿼리를 쓸 수도 있다.

---

## Grafana Tempo 데이터 소스 설정

Grafana에서 Tempo 데이터 소스를 추가한다.

```yaml
# grafana/provisioning/datasources/tempo.yaml

apiVersion: 1
datasources:
  - name: Tempo
    type: tempo
    url: http://tempo:3200
    access: proxy
    uid: tempo
    jsonData:
      httpMethod: GET
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: '-1m'
        spanEndTimeShift: '1m'
        tags:
          - key: service.name
            value: service_name
        filterByTraceID: true
        filterBySpanID: false
      tracesToMetrics:
        datasourceUid: prometheus
        spanStartTimeShift: '-5m'
        spanEndTimeShift: '5m'
        tags:
          - key: service.name
            value: service
        queries:
          - name: Request Rate
            query: rate(http_server_request_duration_seconds_count{$$__tags}[5m])
          - name: Error Rate
            query: rate(http_server_request_duration_seconds_count{$$__tags,status_code=~"5.."}[5m])
      serviceMap:
        datasourceUid: prometheus
      search:
        hide: false
      nodeGraph:
        enabled: true
      lokiSearch:
        datasourceUid: loki
```

`tracesToLogsV2` 설정이 트레이스→로그 연결의 핵심이다. 스팬의 `service.name` 속성을 Loki의 `service_name` 레이블로 매핑해서, 트레이스 뷰에서 "Logs" 버튼을 누르면 해당 서비스의 로그가 시간 범위에 맞게 자동으로 열린다.

`spanStartTimeShift`와 `spanEndTimeShift`를 넉넉하게 잡아야 한다. 스팬 시작 시각과 로그 타임스탬프가 정확히 일치하지 않는 경우가 있어서, 너무 좁게 잡으면 관련 로그가 안 보일 수 있다.

---

## Prometheus Exemplar 연동

Exemplar는 메트릭 데이터 포인트에 Trace ID를 붙여두는 것이다. Grafana에서 응답 시간 그래프의 특정 시점을 클릭하면 그 시점의 트레이스로 바로 이동할 수 있다.

앱에서 Exemplar를 붙이려면 Prometheus Histogram 메트릭에 Trace ID를 같이 기록해야 한다. NestJS/Node.js 기준으로 `prom-client`와 OTel을 같이 쓰는 경우:

```typescript
import { Histogram } from 'prom-client';
import { context, trace } from '@opentelemetry/api';

const httpRequestDuration = new Histogram({
  name: 'http_server_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
  enableExemplars: true,
});

// 요청 처리 후
function recordRequestDuration(method: string, route: string, statusCode: number, durationSec: number) {
  const span = trace.getActiveSpan();
  const traceId = span?.spanContext().traceId;

  httpRequestDuration.observe(
    { method, route, status_code: statusCode },
    durationSec,
    traceId ? { traceID: traceId } : undefined,
  );
}
```

Prometheus 설정에서 Exemplar 수집을 켜야 한다.

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

feature_flags:
  - exemplar-storage

scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['app:3000']
    # Exemplar 수집을 위해 OpenMetrics 포맷 사용
    scrape_protocols: ['OpenMetricsText1.0.0', 'PrometheusText0.0.4']
```

Grafana의 Prometheus 데이터 소스 설정에서 Exemplar 활성화 여부를 확인한다. Grafana UI에서 Histogram 패널에 "Exemplars" 토글이 있고, 이걸 켜면 그래프 위에 트레이스 링크 점이 표시된다.

주의할 점: `prom-client` v14 이상에서 `enableExemplars: true` 옵션이 추가됐다. 이전 버전은 Exemplar를 지원하지 않는다.

---

## Loki derivedFields 설정

derivedFields는 로그 라인에서 정규식으로 값을 추출해 외부 링크를 만드는 Loki 기능이다. 로그에 Trace ID가 찍혀 있으면 Tempo 트레이스로 바로 넘어가는 링크를 자동으로 붙일 수 있다.

```yaml
# Loki 데이터 소스 provisioning

datasources:
  - name: Loki
    type: loki
    url: http://loki:3100
    uid: loki
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: '"traceId":"(\w+)"'
          url: '$${__value.raw}'
          urlDisplayLabel: View Trace
          datasourceUid: tempo
```

`matcherRegex`는 로그 라인에서 Trace ID를 추출하는 정규식이다. 구조화 로그(JSON)라면 `"traceId":"(\w+)"`로 잡을 수 있고, 텍스트 로그라면 `traceId=(\w+)` 형태로 조정한다.

`datasourceUid: tempo`를 지정하면 URL로 Jaeger 같은 외부 URL 대신 Grafana 내의 Tempo 데이터 소스로 연결된다. 로그 패널에서 Trace ID 옆에 "View Trace" 링크가 생기고, 클릭하면 Tempo에서 해당 트레이스를 바로 연다.

이 기능이 동작하려면 애플리케이션 로그에 Trace ID가 찍혀야 한다. OTel SDK를 쓰면 현재 활성 스팬의 Trace ID를 꺼낼 수 있다.

```typescript
import { trace } from '@opentelemetry/api';

function getTraceId(): string | undefined {
  const span = trace.getActiveSpan();
  return span?.spanContext().traceId;
}

// 로거에 Trace ID 주입 (winston 예시)
logger.info('결제 처리 시작', {
  traceId: getTraceId(),
  orderId: order.id,
  amount: order.amount,
});
```

---

## 자주 마주치는 문제

**트레이스가 Tempo에 들어오지 않는 경우**

먼저 OTel Collector 로그를 확인한다. `failed to export traces` 같은 오류가 있으면 Tempo 엔드포인트가 잘못됐거나 네트워크 문제다. Tempo가 정상 동작하는지 `curl http://tempo:3200/ready`로 확인한다.

앱에서 Collector로 데이터가 가는지 확인하려면 Collector에 `debug` exporter를 임시로 추가하면 된다.

```yaml
exporters:
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/tempo, debug]
```

**TraceQL 검색이 느린 경우**

검색 시간 범위를 좁힌다. Tempo는 블록 단위로 스캔하기 때문에 시간 범위가 길면 스캔 대상이 많아진다. `resource.service.name`을 조건에 넣으면 Tempo가 해당 서비스 블록만 스캔한다.

Tempo 설정에서 `query_frontend.search.max_duration`으로 최대 검색 범위를 제한할 수 있다.

**S3 블록이 쌓이는 속도가 예상보다 빠른 경우**

샘플링 비율을 확인한다. 100% 트레이스를 저장하면 볼륨이 크다. 스팬 하나에 키워드 속성을 너무 많이 붙여도 블록 크기가 커진다. `span.db.statement`에 쿼리 전체를 넣으면 특히 크다.

`compactor`가 정상 동작하는지 확인한다. Tempo는 주기적으로 작은 블록을 큰 블록으로 합치고 `block_retention`이 지난 블록을 삭제한다. compactor가 멈추면 블록이 계속 쌓인다.

**Exemplar가 Grafana에서 안 보이는 경우**

Prometheus 설정에 `feature_flags: [exemplar-storage]`가 있는지 확인한다. Grafana Prometheus 데이터 소스 설정에서 "Exemplars" 탭을 확인한다. 패널이 Histogram 타입이어야 Exemplar 점이 표시된다. Time Series 패널에서도 Exemplar 토글이 있지만, 데이터가 Histogram이어야 한다.
