---
title: Loki 로그 집계
tags: [monitoring, observability, devops, kubernetes, docker]
updated: 2026-08-16
---

# Loki 로그 집계

Loki는 로그 내용을 인덱싱하지 않는다. 레이블만 인덱싱하고 내용은 청크로 압축해 오브젝트 스토리지에 저장한다. 쿼리할 때 청크를 읽어 각 줄을 필터링하는 방식이라 풀텍스트 검색 속도는 Elasticsearch보다 느리지만, 저장 비용이 낮고 Grafana와 통합이 자연스럽다.

이 구조의 핵심 함의는 레이블 조합이 스트림을 결정한다는 것이다. 레이블 설계를 잘못하면 Loki가 유지해야 하는 스트림 수가 폭발적으로 늘어나 메모리 부족으로 인제스터가 죽는다.

## 레이블 설계

### 무엇이 레이블이 되는가

레이블 조합 하나가 로그 스트림 하나다. `{app="order-service", env="production", level="error"}`와 `{app="order-service", env="production", level="info"}`는 다른 스트림이다. 스트림마다 별도 청크가 열리고 인제스터 메모리에 올라간다.

레이블로 쓸 수 있는 기준은 카디널리티다. 값의 종류가 적을수록 좋은 레이블이다.

```
카디널리티 낮음 (레이블로 적합):
  env: production | staging | dev           # 값 3개
  app: order-service | payment-service ...  # 서비스 수만큼
  namespace: backend | frontend | infra     # 수십 개
  level: error | warn | info | debug        # 값 4개
  region: ap-northeast-2 | us-east-1       # 리전 수만큼

카디널리티 높음 (레이블로 쓰면 안 됨):
  traceId     # 요청마다 새 값 → 스트림 수 = 총 요청 수
  userId      # 사용자마다 새 값
  requestId
  sessionId
  hostname    # 오토스케일링 환경에서 파드마다 새 값
```

traceId를 레이블로 설정했다가 Loki 인제스터가 OOM으로 죽는 사고를 실제로 겪었다. 일평균 100만 요청이 들어오는 서비스에서 traceId 레이블을 달자마자 메모리가 몇 시간 만에 32GB를 넘었다. 재시작해도 트래픽이 들어오는 한 계속 올라갔다. 레이블을 제거하고 재배포하기 전까지 로그 수집이 전면 중단됐다.

### hostname 레이블 처리

쿠버네티스에서 파드 이름을 레이블로 달면 파드가 재시작하거나 오토스케일링으로 늘어날 때마다 스트림이 새로 생긴다. 오래된 스트림은 남고 새 스트림이 쌓여 카디널리티가 계속 올라간다.

파드별 구분이 필요하면 레이블 대신 로그 내용에 포함하거나, 노드 이름(node)만 레이블로 쓰고 파드 이름은 제외한다.

```yaml
# Promtail relabel_configs — 파드 이름은 제외
relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_app]
    target_label: app
  - source_labels: [__meta_kubernetes_namespace]
    target_label: namespace
  - source_labels: [__meta_kubernetes_pod_node_name]
    target_label: node
  # __meta_kubernetes_pod_name은 레이블로 올리지 않음
```

## 수집 파이프라인

### Promtail

Promtail은 현재 maintenance mode다. 기존에 쓰고 있다면 교체 급한 건 아니지만, 신규 프로젝트는 Grafana Alloy로 시작하는 게 낫다.

쿠버네티스 환경 기본 설정:

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml
  # /tmp는 컨테이너 재시작 시 사라진다.
  # 볼륨 마운트 안 하면 재시작마다 로그를 처음부터 다시 읽어 중복 수집된다.

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    pipeline_stages:
      - docker: {}        # Docker JSON 래퍼 제거
      - json:
          expressions:
            level: level
      - labels:
          level:          # 카디널리티 낮은 필드만
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_node_name]
        target_label: node
      - source_labels: [__meta_kubernetes_pod_uid, __meta_kubernetes_pod_container_name]
        separator: /
        replacement: /var/log/pods/*$1/*.log
        target_label: __path__
```

Java 스택 트레이스처럼 여러 줄에 걸친 로그는 `multiline` 스테이지로 합쳐야 한다. 없으면 각 줄이 별개 로그 엔트리로 들어간다.

```yaml
pipeline_stages:
  - multiline:
      firstline: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
      max_wait_time: 3s
      max_lines: 256      # 스택 트레이스가 256줄 넘으면 잘림
```

특정 서비스에만 다른 파이프라인을 적용할 때 `match` 스테이지를 쓴다.

```yaml
pipeline_stages:
  - json:
      expressions:
        level: level
  - match:
      selector: '{app="payment-service"}'
      stages:
        - json:
            expressions:
              amount: amount
              currency: currency
        - labels:
            currency:     # 통화 단위는 카디널리티 낮음 (KRW, USD 등)
```

### Grafana Alloy

Alloy는 Promtail과 Grafana Agent를 통합한 에이전트다. OpenTelemetry 컬렉터도 내장해서 로그·메트릭·트레이스를 하나의 프로세스로 수집할 수 있다.

설정 파일 형식이 River/Alloy(`.alloy`)로 바뀌었다. HCL과 비슷한 블록 구조다.

```alloy
// 쿠버네티스 파드 디스커버리
discovery.kubernetes "pods" {
  role = "pod"
}

// 파드 로그 수집
loki.source.kubernetes "pods" {
  targets    = discovery.kubernetes.pods.targets
  forward_to = [loki.process.pipeline.receiver]
}

// 파이프라인 처리
loki.process "pipeline" {
  forward_to = [loki.write.loki_backend.receiver]

  // 쿠버네티스 메타데이터 레이블로 변환
  stage.kubernetes {}

  // 정적 레이블 추가
  stage.static_labels {
    values = {
      cluster = "production-k8s",
    }
  }

  // JSON 로그 파싱
  stage.json {
    expressions = {
      level = "level",
    }
  }

  // 파싱된 필드를 레이블로 승격
  stage.labels {
    values = {
      level = "level",
    }
  }
}

// Loki로 전송
loki.write "loki_backend" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

Alloy는 `http://localhost:12345`에 UI를 제공한다. 컴포넌트 상태, 데이터 흐름, 파이프라인 처리 결과를 시각적으로 확인할 수 있다. Promtail에는 없는 기능이라 설정 디버깅이 훨씬 수월하다.

멀티라인 처리는 `stage.multiline`으로 쓴다.

```alloy
stage.multiline {
  firstline     = "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
  max_wait_time = "3s"
  max_lines     = 256
}
```

OTel 로그를 받아서 Loki로 보내는 구성도 가능하다.

```alloy
// OTel 컬렉터 수신기
otelcol.receiver.otlp "default" {
  grpc { endpoint = "0.0.0.0:4317" }
  output {
    logs = [otelcol.exporter.loki.default.input]
  }
}

// OTel 로그를 Loki 형식으로 변환해 전송
otelcol.exporter.loki "default" {
  forward_to = [loki.write.loki_backend.receiver]
}
```

## LogQL 쿼리

LogQL은 레이블 선택자 없이 쓸 수 없다. `{}`만 쓰거나 선택자를 너무 넓게 잡으면 읽어야 할 청크 수가 늘어나 타임아웃이 난다.

### 필터

```logql
# 문자열 포함
{app="order-service", env="production"} |= "ERROR"

# 문자열 제외 — 헬스체크 로그 제거
{app="api"} |= "ERROR" != "GET /health" != "GET /metrics"

# 정규식 — 여러 패턴 중 하나
{app="api"} |~ "timeout|connection refused|deadline exceeded"

# 정규식 제외
{app="api"} !~ "DEBUG|TRACE"
```

파이프라인은 왼쪽에서 오른쪽으로 순서대로 실행된다. 범위를 좁히는 필터를 앞에 두고 파싱은 뒤에 넣어야 불필요한 처리를 줄인다.

```logql
# 권장: 먼저 필터 → 그 다음 JSON 파싱
{app="api"} |= "ERROR" | json | duration > 1000

# 비권장: 먼저 JSON 파싱 → 그 다음 필터 (모든 로그를 파싱)
{app="api"} | json | level="error" | duration > 1000
```

### 파싱

```logql
# JSON 전체 파싱
{app="api"} | json

# 특정 필드만 파싱
{app="api"} | json level, duration, path, status

# logfmt 파싱 (key=value 형식)
{job="nginx"} | logfmt

# 패턴 파싱 — nginx 접근 로그
{job="nginx"} | pattern `<ip> - - [<_>] "<method> <path> HTTP/<_>" <status> <bytes>`
             | status >= 500

# regex 파싱
{app="api"} | regexp `(?P<method>GET|POST|PUT|DELETE) (?P<path>/\S+) (?P<status>\d{3})`
```

`json` 파싱은 로그 라인 전체가 JSON이어야 동작한다. 앞에 타임스탬프나 로그 레벨 텍스트가 붙어 있으면 파싱에 실패하고 `__error__="JSONParserErr"` 레이블이 붙는다.

```logql
# 파싱 실패한 로그 확인
{app="api"} | json | __error__ != ""
```

파싱 실패 로그가 많으면 로그 형식이 섞여 있는 것이다. `match` 스테이지로 조건을 나누거나, LogQL에서 `json | __error__="" ` 조건으로 성공한 것만 집계한다.

### 메트릭 집계

로그 쿼리 결과를 Grafana 시계열 그래프로 그릴 때는 `rate()`나 `count_over_time()`을 쓴다.

```logql
# 5분 단위 에러 발생 속도 (초당)
sum by (app) (
  rate({env="production"} |= "ERROR" [5m])
)

# 서비스별 5분 에러 건수
sum by (app) (
  count_over_time({env="production"} |= "ERROR" [5m])
)

# 에러율 — 전체 대비 에러 비율
sum by (app) (rate({env="production"} |= "ERROR" [5m]))
/
sum by (app) (rate({env="production"} [5m]))

# duration 필드로 p95 응답시간
quantile_over_time(0.95,
  {app="order-service"} | json | unwrap duration [5m]
) by (app)

# HTTP 상태 코드별 p99
quantile_over_time(0.99,
  {app="api"} | json | status >= 200 | unwrap responseTime [5m]
) by (status)
```

`unwrap`은 파싱된 필드를 숫자로 변환한다. 값이 문자열이거나 숫자가 아니면 그 로그 라인은 집계에서 빠진다. `unwrap duration | __error__=""` 조건으로 파싱 실패 로그를 명시적으로 제외하면 집계 결과가 안정적이다.

Grafana 시계열 패널에서 쿼리가 띄엄띄엄 나오면 범위 벡터(`[5m]`)가 패널 새로고침 간격보다 짧은 것이다. 새로고침 간격이 1분이면 범위는 최소 `[1m]` 이상이어야 겹치는 구간이 생긴다.

트레이스 ID로 특정 요청의 로그를 추적할 때:

```logql
# 레이블 없이 내용 검색
{env="production", app="order-service"} |= "trace-abc123"

# JSON 파싱 후 필드 검색 (더 정확하지만 느림)
{env="production", app="order-service"} | json | traceId="trace-abc123"

# 여러 서비스에 걸쳐 추적
{env="production", app=~"order-service|payment-service|inventory-service"}
  | json
  | traceId="trace-abc123"
```

## 카디널리티 문제 진단

카디널리티 문제는 세 가지 증상으로 나타난다. 인제스터 메모리가 계속 오른다, `/loki/api/v1/push`에 429가 뜬다, `max_streams_per_user` 초과 오류가 발생한다.

스트림 수를 직접 확인하는 방법:

```bash
# 현재 존재하는 레이블 목록
curl -s "http://loki:3100/loki/api/v1/label" | jq '.data[]'

# 특정 레이블의 고유 값 개수 (1시간 범위)
START=$(date -d '1 hour ago' +%s)000000000
END=$(date +%s)000000000
curl -s "http://loki:3100/loki/api/v1/label/traceId/values?start=${START}&end=${END}" \
  | jq '.data | length'
```

traceId 레이블이 달려 있다면 이 결과가 수백만이 나온다. Grafana의 Explore 탭에서 "Label Browser"를 열면 레이블별 값 목록을 시각적으로 볼 수 있다. 값이 수천 개를 넘는 레이블이 있으면 그게 원인이다.

### Loki 설정으로 임시 제한

레이블 설계를 고치는 게 근본 해결이다. 고치는 동안 임시로 스트림 수를 제한한다.

```yaml
limits_config:
  max_streams_per_user: 10000
  max_line_size: 256000           # 단일 로그 라인 최대 크기
  max_entries_limit_per_query: 5000
  reject_old_samples: true
  reject_old_samples_max_age: 1h  # 1시간 이상 지난 로그 거부

ingester:
  max_chunk_age: 2h
  chunk_idle_period: 30m
  chunk_target_size: 1536000      # 1.5MB — 너무 작으면 S3 객체가 너무 많아짐
```

`reject_old_samples: true`는 주의가 필요하다. 서비스가 로그를 버퍼에 쌓았다가 한꺼번에 보내는 구조면 오래된 로그가 거부된다. 배치 처리나 장시간 실행 작업의 로그가 유실될 수 있다.

### traceId를 레이블 없이 Grafana에서 연결하기

traceId 레이블을 제거했을 때 Grafana에서 Tempo 트레이스로 바로 이동하고 싶으면 "Derived Fields"를 설정한다.

```yaml
# Grafana Loki datasource provisioning
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    url: http://loki:3100
    jsonData:
      derivedFields:
        - datasourceUid: tempo   # Tempo datasource UID
          matcherRegex: "traceId=(\\w+)"  # 로그 내용에서 추출
          name: TraceID
          url: "$${__value.raw}"          # Tempo 트레이스 쿼리로 연결
```

로그 내용에 `traceId=abc123` 형식이 있으면 Grafana가 자동으로 링크를 만들어 준다. traceId가 레이블에 없어도 로그 → 트레이스 이동이 된다.

Loki 쿼리 결과가 느릴 때 Grafana Explore의 "Query Inspector"를 열면 실제로 몇 개의 청크를 읽었는지 나온다. 청크 수가 수만 개를 넘으면 레이블 선택자를 좁히거나 시간 범위를 줄여야 한다.
