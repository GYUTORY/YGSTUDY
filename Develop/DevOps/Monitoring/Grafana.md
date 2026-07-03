---
title: Grafana
tags: [devops, monitoring, grafana, visualization, dashboard, alerting, loki, tempo]
updated: 2026-04-08
---

# Grafana

## 정의

Grafana는 메트릭, 로그, 트레이스를 시각화하는 오픈소스 모니터링 플랫폼이다. Prometheus에서 수집한 메트릭을 보여주는 용도로 시작했지만, 지금은 Loki(로그), Tempo(트레이스)까지 하나의 UI에서 다룬다.

Grafana 자체는 데이터를 저장하지 않는다. 데이터소스에 쿼리를 날려서 결과를 시각화하는 프론트엔드 역할이다. 이 점을 처음에 혼동하면 "Grafana에 메트릭이 안 쌓인다"는 식의 실수를 한다.

## 설치

### Docker Compose

운영 환경에서는 볼륨 마운트 없이 띄우면 컨테이너 재시작할 때 대시보드가 전부 날아간다. 최소한 `/var/lib/grafana`는 반드시 마운트한다.

```yaml
version: "3.8"
services:
  grafana:
    image: grafana/grafana:11.2.0
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PW}
      GF_SERVER_ROOT_URL: https://grafana.example.com
      GF_DATABASE_TYPE: postgres
      GF_DATABASE_HOST: postgres:5432
      GF_DATABASE_NAME: grafana
      GF_DATABASE_USER: grafana
      GF_DATABASE_PASSWORD: ${DB_PW}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./provisioning:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  grafana-data:
```

내장 SQLite를 그대로 쓰면 팀 규모가 커질 때 동시 쓰기 문제가 생긴다. 팀원이 5명 넘으면 PostgreSQL이나 MySQL로 백엔드 DB를 바꾸는 게 낫다.

### Helm Chart (Kubernetes)

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana \
  --namespace monitoring \
  --set persistence.enabled=true \
  --set persistence.size=10Gi \
  --set adminPassword=${GRAFANA_ADMIN_PW} \
  --values custom-values.yaml
```

Helm values에서 `sidecar.dashboards.enabled=true`로 설정하면 ConfigMap으로 대시보드를 배포할 수 있다. 이 방식이 provisioning과 함께 GitOps에 가장 잘 맞는다.

## Provisioning as Code

GUI에서 대시보드를 만들면 "누가 뭘 바꿨는지" 추적이 안 된다. 실 서비스 환경에서는 provisioning 파일을 Git에 넣고 관리한다.

Grafana는 `/etc/grafana/provisioning/` 아래 디렉토리 구조를 읽어서 데이터소스, 대시보드, 알림 설정을 자동으로 적용한다.

```
provisioning/
├── datasources/
│   └── datasources.yaml
├── dashboards/
│   ├── dashboards.yaml        # 프로바이더 설정
│   └── json/
│       ├── overview.json       # 대시보드 JSON
│       └── service-detail.json
├── alerting/
│   ├── contact-points.yaml
│   ├── notification-policies.yaml
│   └── alert-rules.yaml
└── plugins/
    └── plugins.yaml
```

### 데이터소스 Provisioning

```yaml
# provisioning/datasources/datasources.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"        # scrape interval과 맞춰야 한다
      httpMethod: POST           # GET은 URL 길이 제한에 걸릴 수 있다
      exemplarTraceIdDestinations:
        - name: traceID
          datasourceUid: tempo    # Exemplar 클릭 시 Tempo로 이동

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: "traceID=(\\w+)"
          url: "$${__value.raw}"
          datasourceUid: tempo    # 로그에서 트레이스로 점프

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    uid: tempo
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        filterByTraceID: true
      tracesToMetrics:
        datasourceUid: prometheus
        queries:
          - name: "Request rate"
            query: "sum(rate(http_server_request_duration_seconds_count{$$__tags}[5m]))"
```

`timeInterval`을 Prometheus의 `scrape_interval`과 다르게 설정하면 `rate()` 계산이 이상해진다. 15초 간격으로 수집하는데 Grafana에서 1초로 설정하면 그래프에 빈 구간이 생긴다.

### 대시보드 Provisioning

```yaml
# provisioning/dashboards/dashboards.yaml
apiVersion: 1

providers:
  - name: default
    orgId: 1
    folder: "Provisioned"
    type: file
    disableDeletion: true         # GUI에서 실수로 삭제 방지
    updateIntervalSeconds: 30     # 파일 변경 감지 주기
    allowUiUpdates: false         # GUI 수정 차단 (코드로만 관리)
    options:
      path: /etc/grafana/provisioning/dashboards/json
      foldersFromFilesStructure: true  # 하위 폴더 구조 그대로 반영
```

`allowUiUpdates: false`로 설정하면 GUI에서 대시보드를 수정해도 저장되지 않는다. 처음에는 불편하지만 "누가 GUI에서 대시보드 바꿨는데 배포하니까 원복됐다"는 사고를 방지한다.

대시보드 JSON은 GUI에서 만들고 → Export(Share → Export → Save to file) → Git에 커밋하는 흐름이 현실적이다. 처음부터 JSON을 손으로 쓰는 건 비효율적이다.

## 변수와 템플릿

대시보드 하나로 여러 서비스, 여러 환경을 커버하려면 변수(Variable)를 쓴다. 변수 없이 서비스마다 대시보드를 복사하면 관리가 안 된다.

### 변수 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| Query | 데이터소스에서 값 목록을 가져온다 | `label_values(up, job)` |
| Custom | 직접 값을 지정한다 | `production,staging,development` |
| Datasource | 데이터소스 목록을 가져온다 | 타입별 필터링 가능 |
| Interval | 시간 간격을 선택한다 | `1m,5m,15m,1h` |
| Text box | 자유 입력 필드 | 검색어 입력 등 |

### 실제 변수 설정 예시

대시보드 Settings → Variables에서 설정한다.

```
# 변수: namespace
Type: Query
Datasource: Prometheus
Query: label_values(kube_pod_info, namespace)
Multi-value: true
Include All option: true
```

```
# 변수: service
Type: Query
Datasource: Prometheus
Query: label_values(http_server_request_duration_seconds_count{namespace="$namespace"}, service_name)
Multi-value: true
```

두 번째 변수 `service`는 `$namespace`를 참조한다. 이렇게 연쇄 의존(chained variable)을 걸면 namespace를 선택할 때 해당 namespace의 서비스만 드롭다운에 나온다.

### 패널에서 변수 사용

```promql
# 단일 선택 변수
rate(http_server_request_duration_seconds_count{namespace="$namespace", service_name="$service"}[5m])

# Multi-value 변수 (정규식 매칭)
rate(http_server_request_duration_seconds_count{namespace=~"$namespace", service_name=~"$service"}[5m])
```

Multi-value를 켰으면 쿼리에서 `=` 대신 `=~`를 써야 한다. `=`으로 쓰면 여러 개 선택해도 하나만 적용된다. 이걸 놓쳐서 "멀티 선택이 안 먹는다"는 질문이 자주 나온다.

### 반복 패널(Repeat)

변수의 Multi-value 옵션과 함께 패널의 Repeat 기능을 쓰면, 선택한 값마다 패널이 자동으로 복제된다.

패널 편집 → Repeat options → Repeat by variable에서 변수를 지정한다. 서비스 3개를 선택하면 같은 패널이 3개 생긴다.

Row 단위로 Repeat를 걸 수도 있다. 서비스별로 "요청량 + 응답시간 + 에러율" 행을 한꺼번에 반복시킬 때 쓴다.

## Unified Alerting

Grafana 9부터 기존 Legacy Alerting이 Unified Alerting으로 통합됐다. 구버전에서 마이그레이션할 때 alert rule 형식이 완전히 달라지니까 주의해야 한다.

### 구조

Unified Alerting은 세 계층으로 나뉜다:

```
Alert Rule → Notification Policy → Contact Point
    │              │                     │
    │              │                     └─ 실제 알림 전송 (Slack, PagerDuty 등)
    │              └─ 어떤 알림을 어디로 보낼지 라우팅
    └─ 조건 정의 (PromQL, LogQL 등)
```

### Alert Rule

```yaml
# provisioning/alerting/alert-rules.yaml
apiVersion: 1

groups:
  - orgId: 1
    name: service-alerts
    folder: alerts
    interval: 1m               # 평가 주기
    rules:
      - uid: high-error-rate
        title: "서비스 에러율 5% 초과"
        condition: C             # refId C의 결과로 판단
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: sum(rate(http_server_request_duration_seconds_count{status_code=~"5.."}[5m])) by (service_name)
              intervalMs: 1000
              maxDataPoints: 43200
          - refId: B
            datasourceUid: prometheus
            model:
              expr: sum(rate(http_server_request_duration_seconds_count[5m])) by (service_name)
          - refId: C
            datasourceUid: __expr__
            model:
              type: math
              expression: "$A / $B * 100"
              conditions:
                - evaluator:
                    type: gt
                    params: [5]    # 5% 초과 시 firing
        for: 5m                    # 5분 동안 지속되면 알림
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "{{ $labels.service_name }} 에러율 {{ $values.C }}%"
```

`for` 값을 너무 짧게 잡으면 순간 스파이크에도 알림이 온다. 5분 정도가 적당하다. 반대로 너무 길면 장애 인지가 늦어진다.

### Contact Point

```yaml
# provisioning/alerting/contact-points.yaml
apiVersion: 1

contactPoints:
  - orgId: 1
    name: slack-critical
    receivers:
      - uid: slack-backend
        type: slack
        settings:
          recipient: "#backend-alerts"
          token: ${SLACK_BOT_TOKEN}
          title: |
            [{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}
          text: |
            *서비스:* {{ .CommonLabels.service_name }}
            *심각도:* {{ .CommonLabels.severity }}
            *내용:* {{ .CommonAnnotations.summary }}
            *시작:* {{ .StartsAt.Format "2006-01-02 15:04:05" }}

  - orgId: 1
    name: pagerduty-critical
    receivers:
      - uid: pd-backend
        type: pagerduty
        settings:
          integrationKey: ${PD_INTEGRATION_KEY}
          severity: "{{ .CommonLabels.severity }}"
```

Slack 알림의 템플릿에서 Go template 문법을 쓴다. `{{ .CommonLabels.xxx }}`로 label에 접근하고 `{{ .CommonAnnotations.xxx }}`로 annotation에 접근한다.

### Notification Policy

```yaml
# provisioning/alerting/notification-policies.yaml
apiVersion: 1

policies:
  - orgId: 1
    receiver: slack-default           # 기본 수신자
    group_by:
      - alertname
      - service_name
    group_wait: 30s                   # 그룹 첫 알림 대기
    group_interval: 5m                # 같은 그룹 재알림 간격
    repeat_interval: 4h               # 미해결 알림 반복 간격
    routes:
      - receiver: pagerduty-critical
        matchers:
          - severity = critical
        continue: false               # 매칭되면 하위 라우트 무시
        mute_time_intervals:
          - maintenance-window

      - receiver: slack-critical
        matchers:
          - severity = warning
          - team = backend
        group_by:
          - service_name
```

`group_by`를 잘 설정해야 한다. 서비스 10개에서 동시에 알림이 뜨면 Slack 채널이 도배된다. `service_name`으로 그루핑하면 서비스별로 하나의 메시지로 묶인다.

`repeat_interval`이 너무 짧으면 알림 피로(alert fatigue)가 온다. 이미 인지한 장애에 대해 계속 알림이 오면 결국 알림 채널을 음소거하게 된다. 4시간 정도면 적당하다.

### Silence와 Mute Timing

점검 시간이나 배포 중에는 알림을 끄고 싶을 때 두 가지 방법이 있다.

**Silence**: 수동으로 특정 label 매칭 알림을 일정 시간 동안 끈다. GUI에서 Alerting → Silences → Create에서 설정한다. 배포 전에 걸고 배포 후에 해제하는 식으로 쓴다.

**Mute Timing**: 반복되는 점검 시간대를 미리 정의한다.

```yaml
# provisioning/alerting/mute-timings.yaml
apiVersion: 1

muteTimes:
  - orgId: 1
    name: maintenance-window
    time_intervals:
      - times:
          - start_time: "02:00"
            end_time: "04:00"
        weekdays: ["sunday"]
        location: "Asia/Seoul"
```

Silence는 임시 조치, Mute Timing은 정기 점검용이다. 배포 자동화에서 Silence를 API로 생성/해제하면 배포 중 불필요한 알림을 막을 수 있다.

```bash
# 배포 전 Silence 생성
curl -X POST http://grafana:3000/api/alertmanager/grafana/api/v2/silences \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "service_name", "value": "my-service", "isRegex": false}],
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "endsAt": "'$(date -u -d "+30 minutes" +%Y-%m-%dT%H:%M:%SZ)'",
    "createdBy": "deploy-pipeline",
    "comment": "배포 중 알림 차단"
  }'
```

## Loki 연동 (로그)

Loki는 Prometheus의 로그 버전이라고 보면 된다. label 기반으로 로그를 인덱싱하고, LogQL로 쿼리한다. 로그 본문은 인덱싱하지 않아서 Elasticsearch보다 저장 비용이 낮다.

### 데이터소스 설정

Provisioning의 데이터소스 섹션에서 이미 설정했지만, 핵심은 `derivedFields` 설정이다. 로그에서 traceID를 추출해서 Tempo로 연결한다. 이게 없으면 로그에서 트레이스로 넘어갈 때 ID를 수동으로 복사해야 한다.

### Explore에서 LogQL 사용

```logql
# 특정 서비스의 에러 로그
{namespace="production", service_name="payment-service"} |= "error"

# JSON 로그 파싱 후 필터
{namespace="production"} | json | level="error" | status_code >= 500

# 에러 로그 발생 빈도 (메트릭 쿼리)
sum(rate({namespace="production"} |= "error" [5m])) by (service_name)

# 로그에서 응답 시간 추출 후 p95 계산
quantile_over_time(0.95, 
  {namespace="production"} | json | unwrap response_time_ms [5m]
) by (service_name)
```

로그 검색 시 `|=` (포함), `!=` (미포함), `|~` (정규식 매칭)을 쓴다. label 필터로 범위를 좁힌 다음 파이프라인으로 본문을 필터링하는 순서가 성능에 좋다. label 없이 바로 `|= "error"`만 쓰면 전체 로그를 스캔한다.

### 대시보드에서 로그 패널

대시보드에 Logs 패널을 추가하면 해당 시간대의 로그를 바로 볼 수 있다. 메트릭 그래프에서 에러 스파이크가 보이면 같은 시간대의 로그를 바로 확인하는 패턴이다.

패널 설정에서 "Enable log details"를 켜면 각 로그 라인을 클릭했을 때 파싱된 필드를 볼 수 있다. JSON 로그라면 자동으로 필드를 추출해준다.

## Tempo 연동 (트레이스)

Tempo는 분산 트레이싱 백엔드다. Jaeger/Zipkin 프로토콜을 지원하니까 기존에 Jaeger를 쓰고 있었으면 Tempo로 바꾸기 쉽다.

### 메트릭 → 트레이스 연결

Prometheus의 Exemplar 기능을 쓰면 메트릭 데이터 포인트에 traceID가 붙는다. Grafana에서 그래프의 특정 지점에 마우스를 올리면 Exemplar 아이콘이 보이고, 클릭하면 해당 요청의 트레이스로 바로 이동한다.

이걸 쓰려면 애플리케이션에서 메트릭 수집 시 Exemplar를 포함해야 한다.

```go
// Go + Prometheus client에서 Exemplar 추가
histogram.With(labels).Observe(
    duration.Seconds(),
    prometheus.Labels{"traceID": span.SpanContext().TraceID().String()},
)
```

데이터소스 설정에서 `exemplarTraceIdDestinations`를 Tempo uid로 연결하면 자동으로 동작한다.

### 트레이스 → 로그, 메트릭 연결

Tempo 데이터소스에서 `tracesToLogsV2`, `tracesToMetrics`를 설정하면:

- 트레이스 뷰에서 특정 span 선택 → "Logs for this span" 버튼 → Loki에서 해당 시간대, 해당 서비스의 로그가 열린다
- 트레이스 뷰에서 "Related metrics" → Prometheus 쿼리 결과를 바로 본다

이 세 데이터소스의 상호 연결이 Grafana의 핵심 가치다. 메트릭에서 이상 징후 발견 → 트레이스로 원인 span 확인 → 로그로 상세 에러 메시지 확인, 이 흐름이 하나의 UI에서 끊김 없이 된다.

## 대시보드 설계 패턴

대시보드를 무작정 만들면 패널이 수십 개인 거대한 대시보드가 된다. 아무도 안 보게 된다.

### Overview → Detail 드릴다운

계층 구조로 대시보드를 나누는 게 핵심이다.

**Level 1: 시스템 Overview**

전체 서비스의 상태를 한눈에 보는 대시보드. 이 대시보드만 보고 "지금 문제 있나 없나"를 판단한다.

- Stat 패널: 전체 에러율, 전체 요청량, 전체 P95 응답시간
- Table 패널: 서비스별 상태 요약 (이름, 요청량, 에러율, P95)
- 각 서비스 이름에 Data Link를 걸어서 서비스 상세 대시보드로 연결

```promql
# Table 패널 - 서비스별 상태 요약
# Transform에서 여러 쿼리를 Merge로 합친다

# 쿼리 A: 서비스별 요청량
sum(rate(http_server_request_duration_seconds_count{namespace="$namespace"}[5m])) by (service_name)

# 쿼리 B: 서비스별 에러율
sum(rate(http_server_request_duration_seconds_count{namespace="$namespace", status_code=~"5.."}[5m])) by (service_name)
/ sum(rate(http_server_request_duration_seconds_count{namespace="$namespace"}[5m])) by (service_name) * 100

# 쿼리 C: 서비스별 P95
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_seconds_bucket{namespace="$namespace"}[5m])) by (service_name, le)
)
```

**Level 2: 서비스 Detail**

특정 서비스의 상세 메트릭. Overview에서 문제 있는 서비스를 클릭하면 이 대시보드로 온다.

Row 구성:
- RED Metrics: 요청량, 에러율, 응답시간 (Rate, Errors, Duration)
- Resource: CPU, Memory, Network I/O
- Dependencies: DB 커넥션 풀, 외부 API 호출 현황
- Logs: 에러 로그 실시간 스트림

```
# Data Link 설정 (Overview → Detail)
URL: /d/service-detail?var-service=${__data.fields.service_name}&var-namespace=${namespace}
```

**Level 3: 디버깅용**

DB 쿼리 성능, 캐시 히트율, GC 동작 같은 세부 메트릭. 평소에는 안 보고, 문제의 원인을 좁힐 때만 본다.

### RED Method 패널 구성

서비스 모니터링의 기본은 RED Method다.

- **Rate**: 초당 요청 수
- **Errors**: 에러율 (%)
- **Duration**: 응답 시간 분포

```promql
# Rate
sum(rate(http_server_request_duration_seconds_count{service_name="$service"}[$__rate_interval])) 

# Errors (%)
sum(rate(http_server_request_duration_seconds_count{service_name="$service", status_code=~"5.."}[$__rate_interval]))
/ sum(rate(http_server_request_duration_seconds_count{service_name="$service"}[$__rate_interval])) * 100

# Duration (P50, P90, P95, P99)
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_seconds_bucket{service_name="$service"}[$__rate_interval])) by (le)
)
```

`$__rate_interval`은 Grafana가 자동으로 계산하는 변수다. `[5m]`을 하드코딩하면 대시보드의 시간 범위를 바꿨을 때 그래프가 이상해진다. `$__rate_interval`을 쓰면 시간 범위에 맞게 자동 조정된다.

### Heatmap으로 응답 시간 분포 보기

P95 같은 단일 백분위수는 분포를 숨긴다. 응답 시간이 bimodal 분포(빠른 요청 + 느린 요청)인 경우 P95만 보면 놓친다.

```promql
# Heatmap 패널용 쿼리
sum(increase(http_server_request_duration_seconds_bucket{service_name="$service"}[$__rate_interval])) by (le)
```

패널 타입을 Heatmap으로 설정하고, Format을 "Heatmap"으로, Calculate를 false로 설정한다. 색상이 진할수록 해당 구간에 요청이 몰려 있다는 뜻이다.

## Annotation

대시보드 위에 이벤트를 표시하는 기능이다. 배포 시점, 장애 시작/종료, 설정 변경 같은 이벤트를 그래프 위에 수직선으로 표시한다.

메트릭 그래프에서 "이 시점에 뭐가 바뀌었길래 트래픽 패턴이 달라졌지?"라는 질문에 답을 준다.

### API로 Annotation 추가

CI/CD 파이프라인에서 배포할 때마다 annotation을 추가한다.

```bash
# 배포 완료 시 annotation 추가
curl -X POST http://grafana:3000/api/annotations \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "dashboardUID": "overview",
    "time": '$(date +%s000)',
    "tags": ["deploy", "payment-service"],
    "text": "payment-service v2.3.1 deployed by CI #1234"
  }'
```

### 데이터소스 기반 Annotation

Prometheus에서 특정 이벤트를 annotation으로 가져올 수도 있다.

Dashboard Settings → Annotations → New에서:

```promql
# Kubernetes 배포 이벤트
changes(kube_deployment_status_observed_generation{namespace="$namespace"}[1m]) > 0
```

이렇게 설정하면 deployment가 업데이트될 때마다 그래프에 표시된다.

## 폴더와 권한 관리

팀이 커지면 "누가 어떤 대시보드를 수정할 수 있는가"가 중요해진다.

### 폴더 구조

```
Grafana
├── Platform/               # 플랫폼 팀 전용
│   ├── Kubernetes Overview
│   └── Infrastructure
├── Backend/                 # 백엔드 팀
│   ├── Service Overview
│   └── Payment Service Detail
├── Frontend/                # 프론트엔드 팀
│   └── Web Vitals
└── Shared/                  # 전체 공유 (읽기 전용)
    ├── SLO Dashboard
    └── Incident Response
```

### 팀별 권한 설정

Grafana의 권한 모델:

| 역할 | 대시보드 보기 | 대시보드 편집 | 데이터소스 관리 | 사용자 관리 |
|------|:---:|:---:|:---:|:---:|
| Viewer | O | X | X | X |
| Editor | O | O | X | X |
| Admin | O | O | O | O |

폴더 단위로 팀 권한을 설정한다:

- Backend 폴더: backend-team에 Editor, 나머지 Viewer
- Shared 폴더: 전체 Viewer, Platform 팀만 Editor
- Provisioned 폴더: 코드로만 관리하므로 전체 Viewer

API로 폴더 권한을 관리하면 provisioning과 함께 자동화할 수 있다.

```bash
# 폴더 권한 설정
curl -X POST http://grafana:3000/api/folders/backend/permissions \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"role": "Viewer", "permission": 1},
      {"teamId": 2, "permission": 2}
    ]
  }'
```

`permission` 값: 1 = View, 2 = Edit, 4 = Admin

### 서비스 계정

CI/CD나 자동화에서 Grafana API를 호출할 때는 개인 계정 대신 Service Account를 쓴다. Administration → Service accounts에서 생성하고, 필요한 최소 권한만 부여한다.

## 장애 대응 시 대시보드 활용

장애가 발생하면 대시보드를 이렇게 쓴다.

### 1단계: 영향 범위 파악

Overview 대시보드에서 어떤 서비스에 문제가 있는지 확인한다. Stat 패널의 색상이 빨간색으로 바뀌었거나, Table에서 에러율이 높은 서비스를 찾는다.

이때 시간 범위를 "Last 1 hour"로 놓고 보면 "언제부터 문제가 시작됐는지"를 알 수 있다. Annotation이 있으면 배포 시점과 장애 시작 시점이 일치하는지 바로 확인한다.

### 2단계: 원인 서비스 특정

문제 서비스의 Detail 대시보드로 이동한다. RED 메트릭을 보면서:

- 에러율만 올라갔다 → 로직 버그나 의존 서비스 장애
- 응답 시간이 올라가면서 에러도 올라갔다 → 리소스 부족이나 DB 병목
- 요청량이 갑자기 늘었다 → 트래픽 스파이크

### 3단계: 상세 원인 분석

Explore에서 Loki 로그를 뒤진다. 에러 로그에서 traceID를 찾고 Tempo에서 트레이스를 열면 어떤 span에서 시간이 오래 걸렸는지 보인다.

```logql
# 에러 로그 + 트레이스 ID 확인
{service_name="payment-service"} |= "error" | json | line_format "{{.traceID}} {{.message}}"
```

### 실수하기 쉬운 부분

- 시간 범위를 너무 넓게 잡으면 평소 패턴에 묻혀서 이상 징후를 놓친다. 장애 시점 전후 30분~1시간이 적당하다.
- 여러 대시보드를 돌아다니다 보면 시간 범위가 제각각이 된다. 브라우저 URL의 `from`, `to` 파라미터를 통일하거나 Grafana의 time sync 기능을 쓴다.
- 장애 중에 대시보드를 수정하지 마라. "지금 이 패널 추가하면 원인 찾을 수 있을 텐데"라는 유혹이 오는데, 장애 대응 중에 대시보드를 건드리면 돌이킬 수 없는 실수를 한다. Explore에서 ad-hoc 쿼리를 날려라.

### 장애 사후 분석(Postmortem)

장애가 끝나면 해당 시간대의 대시보드 스냅샷을 저장한다.

Dashboard → Share → Snapshot에서 저장하면 데이터소스 없이도 당시 상태를 볼 수 있다. Postmortem 문서에 스냅샷 링크를 첨부하면 "그때 그래프가 어떻게 생겼는지" 기억에 의존하지 않아도 된다.

## 실전 팁

### grafana.ini 자주 쓰는 설정

```ini
[server]
root_url = https://grafana.example.com
serve_from_sub_path = false

[auth]
disable_login_form = false
oauth_auto_login = false

[auth.google]
enabled = true
client_id = xxx
client_secret = xxx
allowed_domains = example.com

[dashboards]
default_home_dashboard_path = /etc/grafana/provisioning/dashboards/json/overview.json

[alerting]
enabled = true
execute_alerts = true

[unified_alerting]
enabled = true

[log]
mode = console
level = warn
```

Google OAuth를 설정하면 회사 계정으로 로그인할 수 있다. `allowed_domains`로 도메인을 제한해야 외부 사람이 접근 못 한다.

### 대시보드 JSON 관리 팁

- 대시보드 JSON에 `id`는 넣지 마라. `id`는 Grafana 인스턴스별로 자동 부여되는 값이다. Git에 `id`가 포함되면 다른 환경에 적용할 때 충돌난다.
- `uid`는 직접 정해서 넣어야 한다. `uid`가 없으면 import할 때마다 새 대시보드가 생긴다.
- `__inputs`과 `__requires` 필드는 export용이니까 provisioning용 JSON에서는 제거한다.
- `version` 필드도 제거한다. provisioning으로 적용할 때 자동으로 올라간다.

### 쿼리 성능

패널이 느리게 로딩되면:

- `rate()` 안의 range를 줄인다. `[5m]` 대신 `[1m]`으로 바꾸면 빨라지지만 그래프가 들쑥날쑥해진다.
- `by` 절의 label 수를 줄인다. cardinality가 높은 label(예: user_id, request_id)로 group by하면 쿼리가 느려진다.
- 시간 범위가 7일 이상이면 Recording Rule을 만들어서 미리 계산된 메트릭을 쓴다.
- Mixed 데이터소스로 여러 소스를 하나의 패널에 넣으면 각각 쿼리하느라 느려진다. 꼭 필요한 경우에만 쓴다.
