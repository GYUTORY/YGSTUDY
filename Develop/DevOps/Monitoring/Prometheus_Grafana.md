---
title: Prometheus + Grafana 모니터링 스택
tags: [infra, monitoring, prometheus, grafana, Alertmanager, thanos, cortex, relabeling, recording-rule]
updated: 2026-07-25
---

# Prometheus + Grafana 모니터링 스택

## 1. 전체 구조

Prometheus는 pull 방식으로 동작한다. 모니터링 대상이 `/metrics` 엔드포인트를 노출하면 Prometheus가 주기적으로 가져간다. 이 구조 덕에 스크레이프 대상 목록만 관리하면 되고, 대상이 죽어도 Prometheus 자체는 영향받지 않는다.

```
┌─────────────────────────────────────────────────────────────┐
│                    Prometheus Server                         │
│                                                             │
│  scrape_configs → targets → TSDB (로컬 저장)               │
│  recording rules → 집계 메트릭 생성                         │
│  alerting rules → Alertmanager로 발송                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼──────────────┐
          ▼                ▼              ▼
   Alertmanager       Grafana        Thanos/Cortex
   (라우팅/억제)    (시각화/대시보드)  (장기 보존)
```

운영 환경에서 Prometheus 단일 인스턴스는 데이터 보존 기간이 15일 수준이다. 그 이상 필요하면 Thanos나 Cortex를 붙여야 하고, 고가용성도 단독으로는 불가능하다.

---

## 2. scrape_config 작성

### 2.1 기본 구조

```yaml
# prometheus.yml
global:
  scrape_interval: 15s       # 기본 수집 주기
  evaluation_interval: 15s   # rule 평가 주기
  scrape_timeout: 10s

scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

`scrape_interval`을 너무 짧게 잡으면 TSDB 쓰기 부하가 올라간다. 15s가 대부분의 경우에 적당하고, 중요하지 않은 메트릭은 60s로 늘려도 된다. 반대로 SLO 연산에 쓰이는 메트릭은 10s까지 줄이는 경우도 있다.

### 2.2 서비스 디스커버리

정적 설정(`static_configs`)은 대상이 고정된 소규모 환경에 쓴다. Kubernetes 환경에서는 `kubernetes_sd_configs`로 자동 탐색한다.

```yaml
scrape_configs:
  # 정적 설정 - 고정 IP 서버
  - job_name: 'node-exporter'
    static_configs:
      - targets:
          - '10.0.1.10:9100'
          - '10.0.1.11:9100'
        labels:
          env: production
          region: ap-northeast-2

  # Kubernetes pods 자동 탐색
  - job_name: 'kubernetes-service-endpoints'
    kubernetes_sd_configs:
      - role: endpoints
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_service_name]
        target_label: service
```

---

## 3. relabeling으로 불필요한 메트릭 제거

relabeling은 두 단계에서 일어난다. 스크레이프 전에 대상 자체를 필터링하는 `relabel_configs`와, 수집된 메트릭의 레이블을 조작하는 `metric_relabel_configs`다.

### 3.1 대상 필터링 (relabel_configs)

```yaml
relabel_configs:
  # 특정 namespace만 수집
  - source_labels: [__meta_kubernetes_namespace]
    action: keep
    regex: 'production|staging'

  # kube-system은 제외
  - source_labels: [__meta_kubernetes_namespace]
    action: drop
    regex: 'kube-system'

  # 레이블 복사
  - source_labels: [__meta_kubernetes_pod_name]
    target_label: pod
  - source_labels: [__meta_kubernetes_namespace]
    target_label: namespace
```

### 3.2 메트릭 필터링 (metric_relabel_configs)

```yaml
metric_relabel_configs:
  # go runtime 메트릭 제거 - 대부분 쓸 일 없음
  - source_labels: [__name__]
    action: drop
    regex: 'go_gc_.*|go_memstats_.*'

  # 버킷이 너무 세분화된 히스토그램 정리
  - source_labels: [__name__, le]
    action: drop
    regex: 'http_request_duration_seconds_bucket;(0\.001|0\.002|0\.003)'

  # 특정 레이블 값 제거 (카디널리티 축소)
  - source_labels: [url]
    action: labeldrop
    regex: 'url'

  # 레이블 값 정규화
  - source_labels: [status_code]
    regex: '(2\d\d)'
    replacement: '2xx'
    target_label: status_class
```

실제로 가장 많이 쓰는 패턴은 `go_gc_*`, `go_memstats_*`, `process_*` 제거다. Go 애플리케이션 하나당 이 메트릭이 수백 개 붙는데 실제로 쓰는 경우가 드물다. TSDB 시계열 수를 줄이는 가장 빠른 방법이다.

---

## 4. recording rule로 쿼리 최적화

PromQL에서 비용이 큰 쿼리는 대부분 `rate()`, `histogram_quantile()`, 여러 레이블 조합 집계다. 이 쿼리를 Grafana 대시보드에서 매번 실행하면 Prometheus CPU가 상당히 올라간다.

recording rule은 결과를 미리 계산해서 새 메트릭으로 저장한다. 복잡한 쿼리를 실시간 실행하는 대신 5분마다 집계된 값을 읽어오는 방식이다.

### 4.1 recording rule 작성

```yaml
# rules/recording.yml
groups:
  - name: http_requests
    interval: 60s  # 기본 evaluation_interval과 다르게 설정 가능
    rules:
      # 서비스별 RPS 사전 집계
      - record: job:http_requests_total:rate5m
        expr: |
          sum by (job, status_code) (
            rate(http_requests_total[5m])
          )

      # p99 레이턴시 사전 집계
      - record: job:http_request_duration_seconds:p99
        expr: |
          histogram_quantile(0.99,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

      # 에러율 사전 집계
      - record: job:http_error_rate:rate5m
        expr: |
          sum by (job) (rate(http_requests_total{status_code=~"5.."}[5m]))
          /
          sum by (job) (rate(http_requests_total[5m]))
```

네이밍 컨벤션은 `{레이블 집합}:{원본 메트릭}:{함수 및 기간}` 형태를 쓴다. `job:http_requests_total:rate5m`처럼 쓰면 어디서 집계됐는지 바로 파악할 수 있다.

### 4.2 Grafana에서 recording rule 활용

```
# 느린 쿼리 (Grafana에서 직접 실행)
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# 빠른 쿼리 (recording rule 결과 조회)
job:http_request_duration_seconds:p99
```

대시보드 패널이 30개 넘는 경우, recording rule 없이 운영하면 Grafana 대시보드 로딩에 10초 이상 걸리는 경우가 있다. 복잡한 집계는 recording rule로 미리 계산하는 게 낫다.

---

## 5. Alertmanager 라우팅과 중복 알림 억제

### 5.1 기본 라우팅 구조

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.example.com:587'
  slack_api_url: 'https://hooks.slack.com/services/...'

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s      # 알림 그룹 형성 대기 시간
  group_interval: 5m   # 같은 그룹 재발송 간격
  repeat_interval: 4h  # 동일 알림 반복 발송 간격

  routes:
    # 심각도별 라우팅
    - match:
        severity: critical
      receiver: 'pagerduty'
      repeat_interval: 1h

    - match:
        severity: warning
      receiver: 'slack-warnings'
      repeat_interval: 12h

    # 팀별 라우팅
    - match_re:
        service: '^(payment|billing).*'
      receiver: 'payment-team'

receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - routing_key: 'XXXXXXXXXXXXXXXX'

  - name: 'slack-warnings'
    slack_configs:
      - channel: '#alerts-warning'
        title: '{{ .CommonLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}'

  - name: 'payment-team'
    email_configs:
      - to: 'payment-oncall@example.com'
```

`group_wait`는 같은 알림 그룹이 처음 발생했을 때 묶어서 보내기 위한 대기 시간이다. 30초 안에 같은 그룹의 다른 알림이 오면 함께 묶인다. 30초가 너무 길다면 10s로 줄인다.

### 5.2 inhibit_rules로 알림 억제

인프라 장애 시 상위 컴포넌트 알림 때문에 하위 컴포넌트 알림이 수십 개 쏟아지는 경우가 있다. 노드가 죽으면 그 위에서 돌던 Pod 알림이 전부 따라 나온다.

```yaml
inhibit_rules:
  # 노드 다운 시 Pod 알림 억제
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: '^Pod.*'
    equal: ['cluster', 'node']

  # critical이 발생하면 같은 서비스의 warning 억제
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'service', 'cluster']

  # DB 장애 시 애플리케이션 오류율 알림 억제
  - source_match:
      alertname: DatabaseDown
    target_match:
      alertname: HighErrorRate
    equal: ['cluster', 'env']
```

`equal` 필드가 핵심이다. source와 target 알림에서 `equal`에 지정한 레이블 값이 동일할 때만 억제가 동작한다. `cluster`와 `env`를 같이 쓰면 같은 클러스터, 같은 환경에서 나온 알림에만 억제가 적용된다.

### 5.3 silences

계획된 점검 시간에 알림을 막을 때는 `amtool`로 silence를 만든다.

```bash
# 2시간짜리 silence 생성
amtool silence add \
  alertname="NodeDown" \
  cluster="production-ap" \
  --duration=2h \
  --comment="scheduled maintenance"

# silence 목록 확인
amtool silence query

# silence 해제
amtool silence expire <silence-id>
```

---

## 6. 고카디널리티 레이블이 성능에 미치는 영향

카디널리티(cardinality)는 레이블 조합의 고유 값 수다. `{job="api", status_code="200"}`처럼 레이블 조합이 하나의 시계열을 만든다.

문제가 되는 경우는 대부분 레이블 값으로 유저 ID, 트랜잭션 ID, URL 전체 경로, 요청 본문 같은 고유한 값을 넣었을 때다.

```
# 괜찮은 경우 - status_code는 몇 가지 값만 있음
http_requests_total{job="api", status_code="200"}  → 시계열 1개

# 문제가 되는 경우 - user_id는 수백만 가지 값
http_requests_total{job="api", user_id="12345678"}  → 유저 수만큼 시계열 생성
```

시계열이 백만 개를 넘어가면 Prometheus가 버벅이기 시작한다. 메모리 사용량이 급격히 올라가고 쿼리 응답 시간이 수 초로 늘어난다.

### 6.1 카디널리티 확인

```promql
# 메트릭별 시계열 수 상위 20개
topk(20, count by (__name__)({__name__=~".+"}))

# 특정 메트릭의 레이블별 고유 값 수
count(count by (url) (http_requests_total))
```

```bash
# Prometheus API로 TSDB 상태 확인
curl http://localhost:9090/api/v1/status/tsdb | jq '.data.headStats'

# 카디널리티 높은 레이블 목록
curl http://localhost:9090/api/v1/status/tsdb | jq '.data.seriesCountByLabelValuePair[:10]'
```

### 6.2 해결 방법

URL 전체 경로를 레이블로 쓰는 경우 `/api/users/12345`처럼 ID가 경로에 포함되면 각 요청이 별도 시계열이 된다. `metric_relabel_configs`로 경로를 정규화한다.

```yaml
metric_relabel_configs:
  # /api/users/12345 → /api/users/:id
  - source_labels: [url]
    regex: '/api/users/\d+'
    replacement: '/api/users/:id'
    target_label: url

  # /api/orders/uuid-xxx → /api/orders/:id
  - source_labels: [url]
    regex: '/api/orders/[a-f0-9-]+'
    replacement: '/api/orders/:id'
    target_label: url
```

---

## 7. Grafana 대시보드 변수 활용

### 7.1 변수 정의

Grafana 대시보드 변수를 쓰면 같은 대시보드로 여러 환경, 서비스, 클러스터를 전환하며 볼 수 있다.

대시보드 Settings → Variables에서 설정한다.

```
# 클러스터 변수
Name: cluster
Type: Query
Query: label_values(up, cluster)
Multi-value: true
Include All option: true

# namespace 변수 (cluster 변수에 연동)
Name: namespace
Type: Query
Query: label_values(up{cluster="$cluster"}, namespace)

# 서비스 변수
Name: service
Type: Query
Query: label_values(up{cluster="$cluster", namespace="$namespace"}, job)
```

변수를 연쇄적으로 참조하면 cluster 선택 시 해당 cluster의 namespace 목록이 자동으로 필터링된다.

### 7.2 변수를 쿼리에 적용

```promql
# 단일 선택 변수
rate(http_requests_total{cluster="$cluster", job="$service"}[5m])

# 멀티 선택 변수 (regex match 방식)
rate(http_requests_total{cluster=~"$cluster", job=~"$service"}[5m])
```

멀티 선택 변수는 `=~`로 처리해야 한다. 변수 값이 여러 개일 때 `cluster=~"prod|staging"` 형태로 변환된다.

### 7.3 템플릿 변수 활용 패턴

```promql
# 선택한 서비스의 에러율
sum(rate(http_requests_total{
  cluster=~"$cluster",
  job=~"$service",
  status_code=~"5.."
}[$__rate_interval]))
/
sum(rate(http_requests_total{
  cluster=~"$cluster",
  job=~"$service"
}[$__rate_interval]))

# $__rate_interval은 Grafana가 패널 시간 범위에 맞게 자동 설정
```

`$__rate_interval`은 Grafana 7.2부터 지원하는 변수다. 패널의 시간 범위에 맞춰 `rate()` 간격을 자동으로 조정해준다. 직접 `[5m]`으로 고정하면 시간 범위를 1시간으로 늘렸을 때 그래프가 뭉개진다.

---

## 8. Thanos로 장기 보존 구성

Prometheus 단독으로는 고가용성과 장기 보존을 동시에 할 수 없다. Thanos는 이 두 문제를 해결하기 위해 Prometheus 위에 덧붙이는 구조다.

### 8.1 Thanos 구성 요소

```
┌──────────────┐    ┌──────────────┐
│ Prometheus A │    │ Prometheus B │  ← 동일한 데이터를 수집하는 HA 쌍
│ + Sidecar   │    │ + Sidecar   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └──────┬────────────┘
              │ gRPC
       ┌──────▼───────┐
       │  Thanos Query │  ← 중복 제거 후 단일 쿼리 엔드포인트 제공
       └──────────────┘
              │
       ┌──────▼───────┐
       │  Object Store │  ← S3/GCS/Azure Blob
       │  (장기 보존)  │
       └──────────────┘
       ┌──────────────┐
       │ Thanos Store  │  ← Object Store 데이터를 쿼리 API로 노출
       └──────────────┘
       ┌──────────────┐
       │ Thanos Compact│  ← 오래된 블록 압축 및 다운샘플링
       └──────────────┘
```

### 8.2 Sidecar 설정

Prometheus와 같은 Pod에 Thanos sidecar를 붙인다.

```yaml
# Kubernetes Deployment 예시
containers:
  - name: prometheus
    image: prom/prometheus:v2.45.0
    args:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.min-block-duration=2h
      - --storage.tsdb.max-block-duration=2h  # Sidecar가 업로드하기 위해 필수

  - name: thanos-sidecar
    image: thanosio/thanos:v0.32.0
    args:
      - sidecar
      - --tsdb.path=/prometheus
      - --prometheus.url=http://localhost:9090
      - --objstore.config-file=/etc/thanos/objstore.yml
    volumeMounts:
      - name: prometheus-data
        mountPath: /prometheus
```

`--storage.tsdb.max-block-duration=2h`는 Thanos sidecar 사용 시 반드시 설정해야 한다. Prometheus가 TSDB 블록을 최대 2시간 단위로 만들어야 sidecar가 Object Store에 업로드할 수 있다.

```yaml
# objstore.yml
type: S3
config:
  bucket: my-thanos-metrics
  endpoint: s3.ap-northeast-2.amazonaws.com
  region: ap-northeast-2
```

### 8.3 Thanos Query 설정

```yaml
# Thanos Query Deployment
args:
  - query
  - --http-address=0.0.0.0:9090
  - --store=prometheus-a:10901      # Sidecar gRPC 주소
  - --store=prometheus-b:10901
  - --store=thanos-store:10901      # 장기 보존 데이터
  - --query.replica-label=replica   # 중복 제거 기준 레이블
```

HA 쌍으로 구성한 Prometheus A, B가 동일한 데이터를 수집한다. Thanos Query는 `replica` 레이블로 중복을 제거해서 하나의 결과만 반환한다.

### 8.4 Cortex와의 차이점

Cortex는 Thanos와 유사한 문제를 해결하지만 아키텍처가 다르다. Prometheus가 Cortex에 remote write로 밀어 넣는 방식이라 Prometheus 설정이 단순하다.

```yaml
# prometheus.yml - Cortex remote write
remote_write:
  - url: http://cortex:9009/api/prom/push
    queue_config:
      capacity: 10000
      max_samples_per_send: 5000
      batch_send_deadline: 5s
```

Cortex는 Kubernetes 환경에서 각 컴포넌트(Distributor, Ingester, Querier, Store Gateway 등)를 독립적으로 스케일할 수 있다. 대규모 멀티 테넌트 환경에 적합하다. 소규모 팀에서는 운영 복잡도 때문에 Thanos를 더 많이 선택한다.

---

## 9. 운영 중 자주 만나는 문제

**TSDB가 너무 많은 디스크를 쓸 때**

Prometheus가 갑자기 디스크를 많이 쓰기 시작하면 카디널리티 폭발일 가능성이 높다. 새로 배포된 서비스에서 고유 값을 레이블로 내보내는 경우가 많다.

```promql
# 시계열 수가 많은 메트릭 상위 10개
topk(10, count by (__name__)({__name__=~".+"}))
```

**rate() 쿼리가 빈 결과를 반환할 때**

`rate()` 함수는 대상 구간에 최소 두 개의 샘플이 있어야 한다. `rate(metric[5m])`인데 scrape_interval이 5m이면 정확히 하나의 샘플만 포함될 수 있어서 빈 결과가 나온다. 구간을 `scrape_interval`의 2배 이상으로 잡는 게 안전하다.

**Alertmanager 알림이 중복으로 오는 경우**

`group_by`에 카디널리티 높은 레이블을 포함하면 그룹이 너무 세분화된다. `pod` 레이블을 `group_by`에 넣으면 Pod마다 별도 알림이 간다. `service`나 `job` 수준으로 집계하는 게 낫다.

**Thanos Store에서 쿼리가 느릴 때**

Thanos Store는 Object Store에서 index를 캐싱해서 쿼리를 처리한다. 캐시가 비어있는 콜드 스타트 상황이나 시간 범위가 넓은 쿼리는 느릴 수 있다. `--store.grpc.series-max-concurrency`와 `--index-cache-size` 설정으로 조정한다.

---
이 문서는 [관측성 허브](../../_hub/관측성.md)의 일부입니다.
