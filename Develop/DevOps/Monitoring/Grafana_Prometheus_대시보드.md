---
title: Grafana + Prometheus 대시보드
tags: [grafana, prometheus, dashboard, promql, monitoring, devops]
updated: 2026-04-09
---

# Grafana + Prometheus 대시보드

Grafana 설치, Loki/Tempo 연동, 폴더 권한 같은 Grafana 자체 운영 내용은 [Grafana](Grafana.md) 문서를 참고한다. Prometheus 아키텍처와 PromQL 문법은 [Prometheus](Prometheus.md) 문서에 있다. 이 문서는 **Prometheus 데이터소스를 연결하고, PromQL로 패널을 만들고, 실제 서비스 운영에 쓸 수 있는 대시보드를 구성하는 실무 과정**에 집중한다.

---

## 데이터 소스 연결

### Provisioning으로 Prometheus 연결

GUI에서 데이터소스를 추가하면 환경마다 수동 설정이 필요하다. provisioning 파일로 관리해야 환경 간 차이가 생기지 않는다.

```yaml
# provisioning/datasources/prometheus.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"
      httpMethod: POST
      prometheusType: Prometheus
      prometheusVersion: "2.51.0"
    editable: false
```

`timeInterval`은 Prometheus의 `scrape_interval`과 반드시 일치시킨다. Grafana는 이 값을 기반으로 `$__rate_interval`을 계산하는데, 값이 다르면 `rate()` 결과가 부정확해진다. 15초 간격으로 수집하는데 `timeInterval`을 1초로 설정하면 그래프에 빈 구간이 생긴다.

`httpMethod: POST`로 설정하는 이유가 있다. PromQL 쿼리가 길어지면 GET 요청의 URL 길이 제한(약 8KB)에 걸린다. 변수가 많거나 `label_values()` 쿼리가 복잡한 대시보드에서 실제로 이 문제를 겪는다.

### 연결 확인

데이터소스 설정 페이지에서 "Save & Test"를 누르면 Prometheus API에 연결을 시도한다. 이때 실패하는 흔한 원인:

- Grafana 컨테이너에서 Prometheus 호스트명을 못 찾는 경우 — Docker Compose의 네트워크 설정 확인
- `access: proxy` 설정인데 Grafana 서버에서 Prometheus까지 네트워크가 안 되는 경우
- Prometheus 앞에 인증 프록시가 있는 경우 — `basicAuth`, `basicAuthUser`, `secureJsonData.basicAuthPassword` 설정 필요

```yaml
# 인증이 필요한 경우
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    basicAuth: true
    basicAuthUser: grafana
    secureJsonData:
      basicAuthPassword: ${PROM_PASSWORD}
```

### 여러 Prometheus 인스턴스 연결

환경별로 Prometheus가 분리된 경우 데이터소스를 여러 개 등록한다.

```yaml
datasources:
  - name: Prometheus-Production
    type: prometheus
    access: proxy
    url: http://prometheus-prod:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"

  - name: Prometheus-Staging
    type: prometheus
    access: proxy
    url: http://prometheus-staging:9090
    jsonData:
      timeInterval: "15s"
```

대시보드에서 Datasource 타입의 변수를 만들면 드롭다운으로 환경을 전환할 수 있다. 이 방식으로 대시보드 하나로 production과 staging을 모두 커버한다.

---

## PromQL 기반 패널 작성

### 패널 생성 기본 흐름

Dashboard → Add panel → Edit에서 패널을 만든다. 왼쪽 하단 쿼리 에디터에서 PromQL을 입력하고, 오른쪽 패널 옵션에서 시각화 타입과 임계값을 설정한다.

쿼리 에디터에서 "Code" 모드와 "Builder" 모드를 전환할 수 있다. Builder는 드롭다운으로 메트릭과 레이블을 선택하는 방식인데, 복잡한 쿼리는 직접 PromQL을 쓰는 Code 모드가 낫다. Builder로 시작하면 PromQL 문법에 익숙해지기 어렵다.

### 시각화 타입별 적합한 메트릭

| 시각화 타입 | 쓰는 곳 | PromQL 패턴 |
|------------|---------|------------|
| Time series | 시간에 따른 추세 | `rate()`, `increase()` |
| Stat | 현재 값 한눈에 보기 | 단일 값 반환 쿼리 |
| Gauge | 용량 대비 사용량 | 비율 계산 쿼리 |
| Table | 여러 항목 비교 | `by (label)` 그루핑 |
| Heatmap | 값 분포 시각화 | `histogram_quantile`용 bucket 데이터 |
| Bar gauge | 항목별 크기 비교 | `topk()`, 정렬된 데이터 |

### Time Series 패널 — 요청량 그래프

```promql
sum(rate(http_requests_total{job="$job"}[$__rate_interval])) by (status_code)
```

Legend 설정에서 `{{status_code}}`를 넣으면 각 라인에 상태 코드가 표시된다. Custom으로 `HTTP {{status_code}}`처럼 접두사를 붙일 수도 있다.

Override 설정으로 상태 코드별 색상을 지정한다:
- `2xx` → 초록색
- `4xx` → 노란색
- `5xx` → 빨간색

이 색상 규칙을 대시보드 전체에서 통일해야 한다. 어떤 패널은 빨간색이 에러이고 다른 패널은 빨간색이 트래픽이면 혼란스럽다.

### Stat 패널 — 현재 에러율

```promql
sum(rate(http_requests_total{job="$job", status_code=~"5.."}[$__rate_interval]))
/
sum(rate(http_requests_total{job="$job"}[$__rate_interval]))
* 100
```

패널 옵션:
- Unit: `Percent (0-100)`
- Thresholds: `0` → 초록, `1` → 노란색, `5` → 빨간색
- Color mode: `Background` — 값에 따라 패널 배경색이 바뀐다

Stat 패널에서 Thresholds를 설정하면 대시보드를 열었을 때 색상만으로 상태를 판단할 수 있다. 초록이면 정상, 빨간색이면 문제가 있다는 뜻이다. 수치를 읽지 않아도 된다.

### Heatmap 패널 — 응답 시간 분포

```promql
sum(increase(http_request_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (le)
```

Heatmap 설정:
- Data → Format: Heatmap
- Y axis → Unit: `seconds`
- Color scheme: `Spectral` 또는 `YlOrRd`

P95만 보면 놓치는 패턴이 있다. 응답 시간이 0.1초와 2초에 몰려 있는 bimodal 분포인 경우, P95는 2초로 나온다. 그런데 실제로는 90%의 요청이 0.1초에 처리되고 나머지가 느린 건데, P95 하나만 보면 "전체가 느리다"고 오해한다. Heatmap을 같이 보면 이런 분포를 잡아낸다.

---

## 변수(Variable) 활용

대시보드 하나로 여러 서비스, 여러 환경을 커버하려면 변수를 써야 한다. 변수 없이 서비스마다 대시보드를 복사하면 10개 서비스에 대시보드 10개가 생긴다. 하나를 수정하면 나머지 9개도 수정해야 한다.

### 필수 변수 3개

대부분의 서비스 대시보드에 이 3개는 기본으로 넣는다.

**datasource 변수**

```
Name: datasource
Type: Datasource
Filter: prometheus
```

환경별 Prometheus가 다를 때 드롭다운으로 전환한다. 패널 쿼리에서 데이터소스를 `$datasource`로 지정하면 변수에 따라 쿼리 대상이 바뀐다.

**job 변수**

```
Name: job
Type: Query
Datasource: $datasource
Query: label_values(up, job)
Multi-value: true
Include All option: true
```

Prometheus의 `job` label을 기준으로 서비스를 선택한다. `label_values(up, job)`은 현재 수집 중인 모든 job 목록을 가져온다. `up` 메트릭은 모든 scrape target에 자동으로 존재하므로 메트릭 이름을 모르는 상태에서도 쓸 수 있다.

**instance 변수**

```
Name: instance
Type: Query
Datasource: $datasource
Query: label_values(up{job="$job"}, instance)
Multi-value: true
Include All option: true
```

`job` 변수에 의존하는 연쇄 변수다. job을 선택하면 해당 job의 인스턴스 목록만 드롭다운에 나온다.

### 변수를 쿼리에서 쓸 때 주의점

Multi-value 변수는 `=~` 연산자로 써야 한다. `=`으로 쓰면 여러 개 선택해도 하나만 적용된다.

```promql
# 단일 선택 변수
rate(http_requests_total{job="$job"}[$__rate_interval])

# Multi-value 변수 — 반드시 =~ 사용
rate(http_requests_total{job=~"$job", instance=~"$instance"}[$__rate_interval])
```

"All"을 선택했을 때 `$job`은 `job1|job2|job3` 형태의 정규식으로 치환된다. `=`으로 비교하면 `job1|job2|job3`이라는 리터럴 문자열과 비교하게 되어 아무것도 안 나온다. 이 실수를 하면 "All 선택했는데 데이터가 안 나온다"는 상황이 된다.

### 커스텀 간격 변수

```
Name: interval
Type: Interval
Values: 1m,5m,15m,30m,1h
Auto option: true
Auto min interval: 1m
```

PromQL에서 `[$interval]`로 사용한다. 시간 범위가 넓을 때는 간격을 늘려서 쿼리 부하를 줄인다. 대부분의 경우 Grafana 내장 `$__rate_interval`을 쓰는 게 낫지만, 사용자가 직접 간격을 조절해야 할 때 이 변수를 쓴다.

---

## 단계별 대시보드 구성

대시보드를 한 장에 다 담으면 패널이 30~40개가 된다. 스크롤을 한참 내려야 원하는 정보를 찾는다. 계층 구조로 나눠야 한다.

### Level 1: 서비스 개요 대시보드

전체 서비스의 상태를 한 화면에서 파악하는 용도다. 온콜 엔지니어가 처음 보는 화면이다.

**Row 1: 핵심 지표 요약 (Stat 패널 4개)**

```promql
# 전체 RPS (Requests Per Second)
sum(rate(http_requests_total{job=~"$job"}[$__rate_interval]))

# 전체 에러율 (%)
sum(rate(http_requests_total{job=~"$job", status_code=~"5.."}[$__rate_interval]))
/ sum(rate(http_requests_total{job=~"$job"}[$__rate_interval])) * 100

# 전체 P95 응답 시간
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{job=~"$job"}[$__rate_interval])) by (le)
)

# 수집 대상 중 다운된 인스턴스 수
count(up{job=~"$job"} == 0) OR vector(0)
```

마지막 쿼리에서 `OR vector(0)`을 붙이는 이유가 있다. 다운된 인스턴스가 없으면 쿼리 결과가 비어서 패널에 "No data"가 표시된다. `vector(0)`을 붙이면 결과가 없을 때 0을 반환한다.

**Row 2: 서비스별 상태 테이블**

Table 패널에 여러 쿼리를 넣고 Transform에서 합친다.

```promql
# Query A: 서비스별 RPS
sum(rate(http_requests_total{job=~"$job"}[$__rate_interval])) by (job)

# Query B: 서비스별 에러율
sum(rate(http_requests_total{job=~"$job", status_code=~"5.."}[$__rate_interval])) by (job)
/ sum(rate(http_requests_total{job=~"$job"}[$__rate_interval])) by (job) * 100

# Query C: 서비스별 P95
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{job=~"$job"}[$__rate_interval])) by (job, le)
)
```

Transform 설정:
1. Merge — 쿼리 A, B, C를 `job` label 기준으로 합친다
2. Organize fields — 컬럼명을 "서비스", "RPS", "에러율(%)", "P95(s)"로 변경
3. Sort by — 에러율 내림차순

에러율 컬럼에 Cell display mode를 "Color background"로 설정하고 Thresholds를 걸면, 문제 있는 서비스가 빨간색으로 표시되어 바로 눈에 들어온다.

**Data Link 설정**

Table의 job 컬럼에 Data Link를 추가한다:

```
Title: 상세 보기
URL: /d/service-detail?var-job=${__data.fields.job}&${__url_time_range}
```

`${__url_time_range}`를 붙이면 현재 보고 있는 시간 범위가 그대로 상세 대시보드에 전달된다. 이걸 빠뜨리면 상세 대시보드가 기본 시간 범위(Last 6 hours)로 열려서, 장애 시점을 다시 찾아야 한다.

### Level 2: 서비스 상세 대시보드

특정 서비스 하나를 깊게 보는 대시보드다. Overview에서 문제 서비스를 클릭하면 이 대시보드로 넘어온다.

**Row 1: RED Metrics**

서비스 모니터링의 기본이다. Rate, Errors, Duration 세 가지.

```promql
# Rate — Time Series 패널
sum(rate(http_requests_total{job="$job"}[$__rate_interval])) by (route)

# Errors — Time Series 패널 (스택 영역)
sum(rate(http_requests_total{job="$job", status_code=~"5.."}[$__rate_interval])) by (route, status_code)

# Duration — Time Series 패널 (P50, P90, P95, P99)
histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (le))
histogram_quantile(0.90, sum(rate(http_request_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (le))
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (le))
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (le))
```

Duration 패널에서 P50~P99를 한 그래프에 그리면 백분위수 간 차이를 한눈에 본다. P50은 0.1초인데 P99가 5초라면 일부 요청이 극단적으로 느린 것이다.

**Row 2: 엔드포인트별 상세**

```promql
# 엔드포인트별 RPS — Table
sum(rate(http_requests_total{job="$job"}[$__rate_interval])) by (route, method)

# 느린 엔드포인트 Top 10 — Bar gauge
topk(10,
  histogram_quantile(0.95,
    sum(rate(http_request_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (route, le)
  )
)
```

`topk(10, ...)`으로 느린 엔드포인트를 뽑으면 성능 병목 지점을 바로 찾는다. 이 패널에서 특정 엔드포인트를 클릭하면 트레이스로 넘어갈 수 있게 Data Link를 걸면 디버깅이 빨라진다.

**Row 3: 의존성 (DB, 외부 API)**

```promql
# DB 쿼리 시간 P95
histogram_quantile(0.95,
  sum(rate(db_query_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (operation, le)
)

# DB 활성 커넥션
db_connections_active{job="$job"}

# 외부 API 호출 시간
histogram_quantile(0.95,
  sum(rate(external_api_duration_seconds_bucket{job="$job"}[$__rate_interval])) by (target, le)
)
```

서비스 응답 시간이 느려질 때 원인이 서비스 자체인지 의존성인지 구분하려면 이 Row가 필요하다. DB 쿼리 시간이 올라가면서 서비스 응답 시간도 올라갔다면 DB가 병목이다.

**Row 4: 런타임 메트릭 (접혀있는 Row)**

기본적으로 접어두고, 필요할 때만 펼쳐서 보는 Row다.

```promql
# Node.js 힙 메모리
nodejs_heap_size_used_bytes{job="$job"}

# GC 시간
rate(nodejs_gc_duration_seconds_sum{job="$job"}[$__rate_interval])

# 이벤트 루프 지연
nodejs_eventloop_lag_seconds{job="$job"}
```

Row를 접어두려면 Row 제목 옆 화살표를 클릭하거나, 대시보드 JSON에서 `"collapsed": true`로 설정한다. 패널 수가 많으면 대시보드 로딩이 느려지는데, 접힌 Row의 패널은 펼칠 때만 쿼리를 실행한다.

### Level 3: 인프라 대시보드

서비스가 아닌 인프라(서버, 컨테이너, 네트워크) 관점의 대시보드다. Node Exporter, cAdvisor, kube-state-metrics 메트릭을 사용한다.

**노드(서버) 리소스**

```promql
# CPU 사용률
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle", job="node-exporter"}[$__rate_interval])) * 100)

# 메모리 사용률
(1 - node_memory_MemAvailable_bytes{job="node-exporter"} / node_memory_MemTotal_bytes{job="node-exporter"}) * 100

# 디스크 사용률
(1 - node_filesystem_avail_bytes{mountpoint="/", job="node-exporter"} / node_filesystem_size_bytes{mountpoint="/", job="node-exporter"}) * 100

# 네트워크 트래픽
irate(node_network_receive_bytes_total{device!~"lo|veth.*", job="node-exporter"}[$__rate_interval]) * 8
```

CPU는 `irate()`를 쓴다. `rate()`보다 순간 변화를 잘 잡는다. 다만 그래프가 들쑥날쑥해질 수 있어서, 용도에 따라 `rate()`를 쓰기도 한다.

**Kubernetes Pod 리소스**

```promql
# Pod CPU 사용량 vs Request/Limit
sum(rate(container_cpu_usage_seconds_total{namespace="$namespace", pod=~"$pod.*"}[$__rate_interval])) by (pod)

# Pod 메모리 사용량 vs Limit
sum(container_memory_working_set_bytes{namespace="$namespace", pod=~"$pod.*"}) by (pod)

# Pod 재시작 횟수
increase(kube_pod_container_status_restarts_total{namespace="$namespace", pod=~"$pod.*"}[$__rate_interval])
```

Pod 재시작 횟수가 올라가면 OOMKill이나 Health Check 실패를 의심한다. 재시작 직전 메모리 사용량을 같이 보면 원인을 좁힐 수 있다.

---

## 알림 규칙 설정

Grafana Unified Alerting으로 Prometheus 메트릭 기반 알림을 설정한다. 알림 규칙 하나가 잘못되면 새벽 3시에 전화가 오거나, 반대로 장애를 놓친다. 신중하게 설계해야 한다.

### 서비스 알림 규칙 예시

```yaml
# provisioning/alerting/alert-rules.yaml
apiVersion: 1

groups:
  - orgId: 1
    name: service-alerts
    folder: alerts
    interval: 1m
    rules:
      # 에러율 5% 초과
      - uid: high-error-rate
        title: "에러율 5% 초과"
        condition: C
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: >
                sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (job)
          - refId: B
            datasourceUid: prometheus
            model:
              expr: >
                sum(rate(http_requests_total[5m])) by (job)
          - refId: C
            datasourceUid: __expr__
            model:
              type: math
              expression: "$A / $B * 100"
              conditions:
                - evaluator:
                    type: gt
                    params: [5]
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }} 에러율 {{ printf \"%.1f\" $values.C }}%"

      # P95 응답 시간 2초 초과
      - uid: high-latency
        title: "P95 응답 시간 2초 초과"
        condition: B
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: >
                histogram_quantile(0.95,
                  sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le)
                )
          - refId: B
            datasourceUid: __expr__
            model:
              type: threshold
              conditions:
                - evaluator:
                    type: gt
                    params: [2]
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.job }} P95 {{ printf \"%.2f\" $values.A }}s"

      # 인스턴스 다운
      - uid: instance-down
        title: "인스턴스 다운"
        condition: A
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }}/{{ $labels.instance }} 다운"
```

### for 값 설정 기준

`for`는 조건이 지속되어야 알림을 보내는 시간이다.

- `for: 0s` — 조건이 한 번이라도 충족되면 즉시 알림. 순간 스파이크에도 반응해서 노이즈가 많다
- `for: 2m` — 인스턴스 다운처럼 빠른 대응이 필요한 경우
- `for: 5m` — 에러율, 응답 시간 같은 메트릭. 일시적 변동을 걸러낸다
- `for: 15m` — 디스크 사용량 같은 느리게 변하는 메트릭

`for`를 길게 잡으면 장애 인지가 늦어진다. 짧게 잡으면 거짓 알림이 많아진다. 서비스 특성에 맞게 조절해야 하고, 운영하면서 계속 다듬어야 한다.

### 알림 피로를 줄이는 방법

알림이 하루에 20~30개씩 오면 결국 알림 채널을 음소거한다. 그러면 진짜 장애도 놓친다.

실무에서 겪는 주요 원인:

- `for` 값이 너무 짧아서 순간 스파이크에 반응하는 경우 → `for` 값을 늘린다
- 임계값이 너무 민감한 경우 → 트래픽 패턴을 보고 현실적인 값으로 조정한다. "에러율 0.1%"는 대부분의 서비스에서 평소에도 넘는다
- severity 구분 없이 모든 알림이 같은 채널로 오는 경우 → `critical`은 PagerDuty/전화, `warning`은 Slack으로 분리한다
- 한 장애에서 연쇄적으로 여러 알림이 동시에 오는 경우 → `group_by`로 알림을 묶는다

---

## Provisioning을 통한 대시보드 코드화

GUI에서 만든 대시보드는 "누가 어떤 패널을 바꿨는지" 추적이 안 된다. 코드로 관리하면 Git 히스토리로 변경 이력을 볼 수 있다.

### 작업 흐름

1. GUI에서 대시보드를 만들고 패널을 배치한다
2. Dashboard → Share → Export → Save to file로 JSON을 내보낸다
3. JSON에서 불필요한 필드를 정리한다
4. Git에 커밋한다
5. provisioning 설정으로 자동 적용한다

### JSON 정리 시 제거할 필드

Export된 JSON에는 인스턴스별 고유 값이 포함되어 있다. 다른 환경에 적용하려면 정리가 필요하다.

```bash
# jq로 불필요한 필드 제거
cat dashboard-export.json | jq '
  del(.id) |
  del(.version) |
  del(.__inputs) |
  del(.__requires) |
  del(.iteration) |
  .uid = "service-overview"
' > provisioning/dashboards/json/service-overview.json
```

- `id` — Grafana 인스턴스별 자동 부여값. 넣으면 다른 환경에서 충돌
- `version` — provisioning 시 자동 증가
- `__inputs`, `__requires` — export 전용 메타데이터
- `uid` — 직접 지정. 안 넣으면 import할 때마다 새 대시보드가 생김

### 대시보드 프로바이더 설정

```yaml
# provisioning/dashboards/dashboards.yaml
apiVersion: 1

providers:
  - name: default
    orgId: 1
    folder: "Service Monitoring"
    type: file
    disableDeletion: true
    updateIntervalSeconds: 30
    allowUiUpdates: false
    options:
      path: /etc/grafana/provisioning/dashboards/json
      foldersFromFilesStructure: true
```

`allowUiUpdates: false`가 핵심이다. GUI에서 대시보드를 수정해도 저장되지 않는다. "누가 GUI에서 바꿨는데 배포 후 원복됐다"는 사고를 방지한다. 개발 환경에서는 `true`로 두고 작업하고, 완성된 JSON을 Git에 올리는 흐름이 현실적이다.

### 파일 구조

```
provisioning/dashboards/json/
├── overview/
│   └── service-overview.json
├── services/
│   └── service-detail.json
└── infra/
    ├── node-resources.json
    └── kubernetes-pods.json
```

`foldersFromFilesStructure: true`를 설정하면 디렉토리 구조가 Grafana 폴더 구조에 그대로 반영된다. `overview/` 디렉토리의 대시보드는 Grafana에서 "overview" 폴더에 들어간다.

### Kubernetes에서 ConfigMap으로 관리

Helm Chart의 sidecar를 쓰면 ConfigMap으로 대시보드를 배포할 수 있다.

```yaml
# values.yaml
sidecar:
  dashboards:
    enabled: true
    label: grafana_dashboard
    labelValue: "1"
    folderAnnotation: grafana_folder
    provider:
      foldersFromFilesStructure: true

---
# dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-overview-dashboard
  labels:
    grafana_dashboard: "1"
  annotations:
    grafana_folder: "Service Monitoring"
data:
  service-overview.json: |
    { ... 대시보드 JSON ... }
```

ConfigMap은 1MB 크기 제한이 있다. 대시보드 JSON이 이 크기를 넘으면 패널이 너무 많다는 뜻이다. 대시보드를 분할하는 게 맞다.

---

## 실무에서 겪는 대시보드 관리 문제

### "No data" 표시 문제

패널에 "No data"가 나오는 원인은 여러 가지다.

- 메트릭 이름이 잘못된 경우 — Prometheus UI(`/graph`)에서 메트릭 이름으로 검색해서 존재하는지 먼저 확인한다
- label 필터가 데이터와 안 맞는 경우 — `up{job="myapp"}`으로 먼저 검색해서 실제 label 값을 확인한다
- 시간 범위에 데이터가 없는 경우 — Prometheus의 retention 기간(기본 15일)을 넘으면 데이터가 없다
- 변수 값이 빈 문자열인 경우 — 대시보드 로딩 시 변수 쿼리가 실패하면 빈 값이 들어간다
- 데이터소스 연결이 끊어진 경우 — Grafana 로그를 확인한다

디버깅 순서: Prometheus UI에서 쿼리 직접 실행 → 데이터 존재 확인 → Grafana 쿼리 에디터에서 변수를 실제 값으로 치환해서 테스트 → 변수 설정 확인

### 대시보드가 느리게 로딩되는 문제

패널이 많거나 쿼리가 무거우면 대시보드 열 때 10초 이상 걸린다.

원인별 대처:

- **패널 수가 너무 많다** — 한 대시보드에 20개 이상이면 분할을 고려한다. 접힌 Row의 패널은 펼칠 때만 실행되니까 Row를 접어두는 것도 방법이다
- **쿼리 range가 길다** — `[5m]`은 괜찮지만 `[1h]`면 계산할 데이터 양이 12배다. 긴 range가 필요하면 Recording Rule로 미리 계산한다
- **cardinality가 높은 label로 group by** — `by (user_id)` 같은 쿼리는 수십만 시계열을 스캔한다. 정말 필요한 경우가 아니면 제거한다
- **시간 범위가 너무 넓다** — 7일 이상이면 Prometheus 서버에 부하가 크다. 대시보드 기본 시간 범위를 "Last 1 hour"나 "Last 6 hours"로 설정한다

```promql
# Recording Rule 예시 (prometheus.yml)
groups:
  - name: precomputed
    interval: 1m
    rules:
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)

      - record: job:http_request_duration:p95_5m
        expr: >
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le)
          )
```

Recording Rule로 미리 계산한 메트릭은 `job:http_requests:rate5m`처럼 `level:metric:operations` 네이밍 규칙을 쓴다. 대시보드에서 이 메트릭을 쓰면 Prometheus가 매번 `rate()`를 계산하지 않아도 된다.

### 여러 사람이 동시에 대시보드를 수정하는 문제

GUI에서 대시보드를 수정할 때 A가 저장 → B가 저장하면 A의 변경이 사라진다. Grafana에 대시보드 버전 관리가 있긴 하지만, 실수로 덮어쓴 걸 알아차리기 어렵다.

해결 방법:
- provisioning으로 코드화하고 `allowUiUpdates: false` 설정 → PR 기반으로 변경 관리
- 개발 단계에서는 `allowUiUpdates: true`로 두고, 완성되면 export해서 Git에 올린다
- Grafana의 Dashboard versions 기능으로 이전 버전과 비교하고 필요하면 복원한다

### 환경 간 대시보드 이동

staging에서 만든 대시보드를 production에 적용할 때 데이터소스 이름이 다르면 패널이 깨진다.

대시보드 JSON에서 데이터소스를 변수로 참조하면 이 문제를 피할 수 있다:

```json
{
  "datasource": {
    "type": "prometheus",
    "uid": "${datasource}"
  }
}
```

패널마다 데이터소스를 `$datasource` 변수로 지정하면, 환경이 바뀌어도 변수만 바꾸면 된다. 데이터소스 이름을 하드코딩하면 환경마다 JSON을 수정해야 한다.

### 대시보드 URL이 바뀌는 문제

대시보드를 삭제하고 다시 import하면 `uid`가 바뀐다. 다른 대시보드에서 Data Link로 연결해놓은 URL이 깨진다. Confluence나 Slack에 공유한 링크도 죽는다.

대시보드를 처음 만들 때 `uid`를 명시적으로 지정하고, 이후에 절대 바꾸지 않는다. provisioning JSON에 `"uid": "service-overview"`처럼 넣어두면 재배포해도 URL이 유지된다.

---

## 참고

Grafana 설치, Loki/Tempo 연동, 폴더 권한, 알림 Contact Point 설정은 [Grafana](Grafana.md) 문서에 정리되어 있다. Prometheus 아키텍처, PromQL 기본 문법, 메트릭 수집 방식은 [Prometheus](Prometheus.md) 문서를 참고한다. Node.js 앱에서 prom-client로 메트릭을 정의하는 방법은 [Prometheus 메트릭 수집](Prometheus_메트릭_수집.md) 문서에 있다.

- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/) — Grafana 공식 대시보드 가이드
- [Prometheus Recording Rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/) — Recording Rule 공식 문서
- [USE Method](https://www.brendangregg.com/usemethod.html) — 인프라 모니터링 방법론 (Utilization, Saturation, Errors)
