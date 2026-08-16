---
title: Alerting 규칙 설계
tags: [monitoring, observability, devops]
updated: 2026-08-16
---

# Alerting 규칙 설계

알림이 많으면 아무 알림도 안 보인다. 처음 Prometheus + Alertmanager를 붙이면 "이것도, 저것도" 하다가 석 달 뒤에 새벽 3시 Slack 알림을 습관적으로 무시하는 팀이 된다. 진짜 장애가 나도 마찬가지로 무시한다. 알림 피로(alert fatigue)의 끝은 항상 거기다.

알림을 보낼지 판단하는 기준은 하나다. "지금 사람이 해야 할 일이 있는가." 자동 복구되거나, 담당자가 봐도 할 수 있는 게 없거나, 이미 다른 알림으로 알고 있는 상황이면 보내지 않는다.

## YAML 구조와 설계 결정

Prometheus는 groups 단위로 알림 규칙을 관리한다. group 이름은 책임 영역으로 나눈다. 서비스명이나 팀명이 적당하다.

```yaml
groups:
  - name: api-gateway.alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{job="api-gateway", status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{job="api-gateway"}[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
          team: backend
          service: api-gateway
        annotations:
          summary: "API Gateway 5xx 에러율 5% 초과"
          description: |
            현재 에러율: {{ $value | humanizePercentage }}
            runbook: https://wiki.internal/runbooks/api-gateway-errors
```

`interval`은 group 단위로 지정 가능하다. 빠른 감지가 필요한 알림은 15~30s, 리소스 트렌드 알림은 2m으로 나누면 평가 부하를 낮출 수 있다.

`annotations.description`에 runbook URL을 넣는 건 생산성에 직접 영향을 준다. 새벽 3시 알림에 URL이 있으면 담당자가 뭘 봐야 하는지 즉시 파악된다. 없으면 코드 뒤지고 동료를 깨우는 것부터 시작해야 한다.

### recording rule 분리

고비용 쿼리를 alert expr에 직접 쓰면 Prometheus가 평가할 때마다 전체 scan을 돌린다. recording rule에서 중간 집계를 저장해두고 alert에서 참조하는 게 맞다.

```yaml
groups:
  - name: api-gateway.recording
    interval: 30s
    rules:
      - record: job:http_request_errors:rate5m
        expr: |
          sum by (job) (
            rate(http_requests_total{status=~"5.."}[5m])
          )

      - record: job:http_requests:rate5m
        expr: |
          sum by (job) (rate(http_requests_total[5m]))

  - name: api-gateway.alerts
    rules:
      - alert: HighErrorRate
        expr: |
          job:http_request_errors:rate5m{job="api-gateway"}
          / job:http_requests:rate5m{job="api-gateway"}
          > 0.05
        for: 5m
        labels:
          severity: critical
```

recording rule 이름 관례는 `level:metric:operations` 형식이다. `job:http_request_errors:rate5m`은 job 단위 집계, 5분 rate라는 의미다. 이 관례를 따르면 어떤 집계인지 이름만 봐도 파악된다.

## `for` 절 설정 기준

`for`는 조건이 지속되는 시간이다. 이 시간 동안 pending 상태를 유지하다가 조건이 계속 참이면 firing으로 전환된다. 중간에 조건이 해소되면 pending이 초기화된다.

| 상황 | for 값 |
|---|---|
| 노드 다운, 서비스 완전 중단 | 없거나 30s~1m |
| 에러율·latency 악화 | 2~5m |
| 디스크 용량, 메모리 누수 트렌드 | 15~30m |
| SLO burn rate warning | 15~30m |

`for`를 길게 잡으면 실제 문제를 늦게 잡는다. 짧으면 flapping이 심해진다. 트래픽 패턴을 먼저 보고 정상 상태에서 임계값을 얼마나 자주 넘는지 확인하고 잡는다.

임계값도 같은 방식으로 잡는다. 지난 7일 P99를 먼저 측정하고 그 1.5~2배를 임계값으로 쓴다.

```promql
# 지난 7일 에러율 P99 — 임계값 설정 전에 먼저 본다
quantile_over_time(0.99,
  (
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))
  )[7d:5m]
)
```

이 값이 0.02이면 임계값 0.01은 너무 낮다.

## Alertmanager 라우팅 설계

팀이 작으면 severity 기준 라우팅으로 충분하다. 클러스터가 여러 개거나 팀이 나뉘면 계층적 라우팅이 필요하다.

```yaml
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 3h

  routes:
    # prod-kr 클러스터
    - matchers:
        - cluster="prod-kr"
      routes:
        - matchers:
            - severity="critical"
          receiver: 'pagerduty-prod-kr'
          group_wait: 10s
          repeat_interval: 1h

        - matchers:
            - severity="warning"
          receiver: 'slack-prod-warning'

    # 개발 환경 알림은 Slack만, 반복은 24시간
    - matchers:
        - cluster=~"dev|staging"
      receiver: 'slack-dev'
      repeat_interval: 24h
```

`group_wait`를 critical만 10s로 낮추면 심각한 상황에서 알림이 빨리 나간다. warning은 30s를 유지해서 관련 알림들이 묶이게 한다.

`repeat_interval`은 환경마다 다르게 잡는다. production critical은 1시간마다 재발송해서 놓치지 않게 하고, dev는 24시간으로 잡아 노이즈를 줄인다.

### 에스컬레이션

Alertmanager 자체는 에스컬레이션 체인(1차 → 2차 → 팀장)을 직접 지원하지 않는다. PagerDuty나 OpsGenie의 escalation policy를 receiver와 연결해서 구현한다. Alertmanager에서 PagerDuty로 보내고, 15분 내 미응답 시 PagerDuty가 다음 담당자로 에스컬레이션하는 구조다.

```yaml
receivers:
  - name: 'pagerduty-prod'
    pagerduty_configs:
      - routing_key: '${PD_ROUTING_KEY}'
        severity: |
          {{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}
        description: '{{ .CommonAnnotations.summary }}'
        details:
          cluster: '{{ .CommonLabels.cluster }}'
          service: '{{ .CommonLabels.service }}'
          runbook: '{{ .CommonAnnotations.runbook }}'
        links:
          - href: 'https://grafana.internal/d/abc?var-service={{ .CommonLabels.service }}'
            text: 'Grafana Dashboard'
```

`details`에 Grafana 대시보드 링크를 넣으면 담당자가 알림 받자마자 현황 파악이 된다. `links` 필드는 PagerDuty 알림 상세에 버튼으로 표시된다.

### 비업무 시간 라우팅

새벽 2시 warning 알림은 대응도 못하고 수면만 방해된다. time-based routing으로 비업무 시간 warning을 묶어서 처리한다.

```yaml
routes:
  - matchers:
      - severity="warning"
    active_time_intervals:
      - business-hours
    receiver: 'slack-warning-immediate'

  - matchers:
      - severity="warning"
    receiver: 'slack-warning-delayed'
    group_wait: 4h
    repeat_interval: 12h

time_intervals:
  - name: business-hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '18:00'
```

business hours 외에 발생한 warning은 `slack-warning-delayed`로 가서 4시간마다 묶어 발송한다. 업무 시작 때 한 번에 확인할 수 있다. critical은 시간 구분 없이 즉시 발송한다. critical인데 새벽 알림이 부담스러우면, critical 기준을 다시 정의해야 하는 것이다.

## Burn Rate 수학

에러율 고정 임계값 알림의 문제는 시간을 고려하지 않는다는 점이다. 에러율 5%가 1분 지속되는 것과 30분 지속되는 건 에러 버짓 소진량이 30배 차이다.

Burn rate는 SLO 기간(보통 30일) 동안 에러 버짓을 다 쓰는 속도를 1로 정의한다.

```
burn_rate = actual_error_rate / allowed_error_rate
```

SLO 99.9%면 `allowed_error_rate = 0.001`이다. 실제 에러율이 0.01이면 burn rate는 10이다. 이 속도가 유지되면 30일 버짓을 3일 만에 소진한다.

### 멀티 윈도우 AND 조건

단일 윈도우는 트레이드오프가 있다. 짧은 윈도우(1h)는 순간 스파이크에 반응하고, 긴 윈도우(6h)는 빠른 장애를 늦게 잡는다. 두 윈도우를 AND 조건으로 묶으면 둘 다 해결된다.

```yaml
groups:
  - name: slo-recording
    interval: 30s
    rules:
      - record: slo:http_error_rate:rate1h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1h]))
          / sum(rate(http_requests_total[1h]))

      - record: slo:http_error_rate:rate6h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[6h]))
          / sum(rate(http_requests_total[6h]))

      - record: slo:http_error_rate:rate3d
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[3d]))
          / sum(rate(http_requests_total[3d]))

  - name: slo-alerts
    rules:
      # SLO: 99.9% → allowed_error_rate = 0.001
      # critical: 1시간에 에러 버짓 2% 소진
      #   burn_rate = (버짓 비율 / 윈도우 비율) = 0.02 / (1h/720h) = 14.4
      - alert: SLOBurnRateCritical
        expr: |
          slo:http_error_rate:rate1h > (14.4 * 0.001)
          and
          slo:http_error_rate:rate6h > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          slo: "99.9"
        annotations:
          summary: "SLO 에러 버짓 급속 소진 (14.4x)"
          description: |
            1h 에러율: {{ $value | humanizePercentage }}
            이 속도가 유지되면 50분 내에 월간 버짓 2%를 소진한다.

      # warning: 6시간에 에러 버짓 5% 소진
      #   burn_rate = 0.05 / (6h/720h) = 6
      - alert: SLOBurnRateWarning
        expr: |
          slo:http_error_rate:rate1h > (6 * 0.001)
          and
          slo:http_error_rate:rate6h > (6 * 0.001)
        for: 15m
        labels:
          severity: warning
          slo: "99.9"
        annotations:
          summary: "SLO 에러 버짓 소진 증가 (6x)"
          description: |
            6h 에러율: {{ $value | humanizePercentage }}
            이 속도가 유지되면 5일 내에 월간 버짓을 소진한다.

      # slow burn: 낮은 에러율이 장기간 지속되는 경우
      #   burn_rate = 0.10 / (3d/30d) = 1 → 3d 에 버짓 10% 소진
      - alert: SLOSlowBurn
        expr: slo:http_error_rate:rate3d > (3 * 0.001)
        for: 1h
        labels:
          severity: warning
          slo: "99.9"
        annotations:
          summary: "SLO 에러 버짓 장기 소진"
          description: "3일 평균 에러율: {{ $value | humanizePercentage }}"
```

burn rate 계산 공식은 `(버짓에서 허용하는 소진 비율) / (윈도우 비율)`이다. 720은 30일을 시간 단위로 환산한 값이다.

SLO 목표값이 바뀌면 이 수치가 전부 바뀐다. 99.9% → 99.5%로 완화하면 `allowed_error_rate`가 0.001 → 0.005가 되고, 같은 burn rate 값에서 임계값이 5배 높아진다. SLO 값을 레이블로 관리하면 추적하기 편하다.

## Dead Man's Switch

알림 시스템 자체가 죽었을 때를 감지하는 방법이다. "항상 firing이어야 하는 알림"이 사라지면 알림 파이프라인에 문제가 생긴 것이다.

```yaml
- alert: Watchdog
  expr: vector(1)
  labels:
    severity: none
  annotations:
    summary: "Alertmanager 연결 확인용"
    description: "이 알림이 끊기면 alerting pipeline 점검"
```

Alertmanager에서 이 알림을 받으면 PagerDuty나 OpsGenie의 heartbeat 기능으로 forwarding한다. heartbeat가 끊기면 해당 서비스가 에스컬레이션을 시작한다.

Prometheus나 Alertmanager가 재시작되거나 설정 오류로 내려갔을 때 이 watchdog가 없으면 아무 알림도 안 나간다. 장애가 났는데 알림이 없어서 모르는 상황이 발생한다.

## Inhibition 설계

인프라 장애가 나면 연쇄 알림이 쏟아진다. DB가 다운되면 API 에러율, 커넥션 풀 고갈, 응답 시간 초과가 한꺼번에 터진다. 근본 원인 하나에서 파생된 알림들이다.

```yaml
inhibit_rules:
  # 노드 다운 시 해당 노드의 하위 알림 억제
  - source_matchers:
      - alertname="NodeDown"
    target_matchers:
      - severity=~"warning|info"
    equal: ['instance']

  # DB 클러스터 장애 시 application 레벨 알림 억제
  - source_matchers:
      - alertname="DatabaseClusterDown"
      - severity="critical"
    target_matchers:
      - alertname=~"APIHighErrorRate|SlowResponse|ConnectionPoolExhausted"
    equal: ['cluster']

  # critical이 있으면 같은 서비스 warning 억제
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal: ['service', 'cluster']
```

`equal` 필드에 넣은 레이블이 source와 target에서 같아야 억제가 작동한다. `equal: ['cluster']`면 같은 클러스터 내 파생 알림만 억제하고, 다른 클러스터 알림은 그대로 나간다.

`equal`을 빠뜨리면 source 알림 하나가 전체 target 알림을 억제한다. DB가 prod-kr에서 다운됐는데 prod-us의 API 에러 알림까지 억제되면 안 된다.

inhibition 설정 후 반드시 테스트해야 한다. Alertmanager의 `/api/v2/alerts?silenced=true&inhibited=true` 엔드포인트로 억제 중인 알림 목록을 확인한다.

## Flapping 알림 처리

조건이 경계값 근처에서 왔다 갔다 하면 firing → resolved → firing이 반복된다. 두 가지 방법으로 해결한다.

첫째, `for` 시간을 늘린다. 이미 2m이면 5m으로 늘린다.

둘째, recording rule에서 smoothed 값을 만든다. 직전 구간 평균을 내서 순간 변동을 줄인다.

```yaml
- record: job:http_error_rate:smoothed5m
  expr: |
    (
      job:http_error_rate:rate5m
      + job:http_error_rate:rate5m offset 5m
    ) / 2
```

어떤 알림이 flapping인지 확인하는 방법:

```promql
# 1시간 내에 firing → resolved 전환이 2회 이상 발생한 알림
changes(ALERTS{alertstate="firing"}[1h]) > 2
```

메트릭 자체가 불안정한 경우도 있다. 집계 레이블에 고유값이 많은 레이블이 섞여있거나, 수집 간격이 너무 길면 rate() 계산이 튄다. 이 경우 집계 윈도우를 늘리거나 레이블을 정리해야 한다.

## 알림 규칙 파일 관리

규모가 커지면 알림 규칙 파일이 수십 개가 된다. 관리 기준 없이 쌓이면 어디 뭐가 있는지 파악하기 어렵다.

```
alerts/
  recording/
    api-gateway.recording.yaml
    database.recording.yaml
    infra.recording.yaml
  alerts/
    api-gateway.alerts.yaml
    database.alerts.yaml
    infra.alerts.yaml
    slo.alerts.yaml
```

recording과 alert을 분리하고 서비스 단위로 나눈다. Prometheus에서 glob으로 불러온다.

```yaml
rule_files:
  - "alerts/recording/*.yaml"
  - "alerts/alerts/*.yaml"
```

변경할 때 `promtool check rules alerts/**/*.yaml`로 문법 검사를 먼저 돌린다. 문법 오류가 있으면 Prometheus가 해당 파일 전체를 무시한다. 무시된 걸 모르면 알림이 없는 상태가 조용히 유지된다.

레이블 카디널리티도 주의해야 한다. `user_id`, `request_id` 같은 레이블을 알림 규칙에 쓰면 알림 수가 폭발한다.

```yaml
# 잘못된 예 — user_id가 수천 개면 알림도 수천 개
- alert: UserRequestError
  expr: rate(http_requests_total{status="500", user_id=~".+"}[5m]) > 0

# 서비스 단위로 집계
- alert: ServiceRequestError
  expr: |
    sum by (service) (rate(http_requests_total{status="500"}[5m])) > 0.1
```

`prometheus_tsdb_head_series` 메트릭으로 시리즈 수를 모니터링한다. 급격히 늘어나면 어떤 레이블이 원인인지 찾는다.
