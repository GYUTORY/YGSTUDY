---
title: Alerting Rules
tags: [monitoring, devops]
updated: 2026-07-31
---

# Alerting Rules

Prometheus에서 알림 규칙을 잘못 설계하면 온콜 담당자가 새벽마다 쓸데없는 알림에 시달린다. Alertmanager를 처음 붙이는 팀이 흔히 저지르는 실수는 모든 지표에 알림을 달고 임계값을 너무 낮게 잡는 것이다. 알림이 쏟아지면 진짜 장애를 놓친다. 알림 피로(alert fatigue)는 기술 문제가 아니라 설계 문제다.

## 알림 규칙 기본 구조

recording rule과 alert rule은 파일을 분리해서 관리한다. 같은 파일에 섞으면 어떤 게 알림이고 어떤 게 집계용인지 파악하기 어렵다.

```yaml
# alerts/api-alerts.yaml
groups:
  - name: api.alerts
    interval: 30s
    rules:
      - alert: APIHighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "API 5xx 에러율 5% 초과"
          description: "현재 에러율: {{ $value | humanizePercentage }}"
```

`for: 5m`은 조건이 5분 동안 지속될 때만 알림을 발송한다는 의미다. 없으면 순간적인 스파이크에도 알림이 나간다. 대부분의 알림에는 최소 2분 이상을 설정해야 한다. for 없이 쓰는 경우는 `TargetDown` 같이 즉시 알려야 하는 상황 정도다.

## 알림 피로 줄이기

알림 피로의 원인은 크게 세 가지다. 임계값이 너무 낮거나, 같은 원인에서 여러 알림이 동시에 발송되거나, 알림이 발생했다 사라졌다를 반복(flapping)하는 경우다.

### Grouping

Alertmanager의 grouping은 같은 원인에서 발생한 알림을 묶어서 보낸다.

```yaml
# alertmanager.yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

`group_wait`는 첫 알림 발송 전 대기 시간이다. 30초를 두면 같은 시간대에 발생한 관련 알림들이 묶인다. `group_interval`은 같은 그룹에 새 알림이 추가됐을 때 재발송하는 간격이다. `repeat_interval`은 변화 없이 알림이 지속될 때 재발송하는 주기다.

인프라 장애가 나면 수십 개의 알림이 동시에 올라온다. DB 연결이 끊기면 API 에러율, latency, DB 연결 수 알림이 한꺼번에 터진다. grouping 없이는 Slack에 메시지 50개가 쏟아진다.

### Inhibition

더 심각한 알림이 활성화됐을 때 덜 심각한 관련 알림을 억제한다. 노드가 다운됐을 때 그 노드의 모든 서비스 알림이 따라오는 걸 막는 데 쓴다.

```yaml
inhibit_rules:
  - source_matchers:
      - alertname="NodeDown"
    target_matchers:
      - severity=~"warning|info"
    equal: ['instance']

  - source_matchers:
      - alertname="ClusterDown"
    target_matchers:
      - severity=~"critical|warning|info"
    equal: ['cluster']
```

`equal`은 source와 target 알림에서 값이 같아야 하는 레이블이다. `instance`를 지정하면 `node-01`이 다운됐을 때 `node-02`의 warning 알림은 그대로 발송된다.

`equal`을 빠뜨리면 source 알림 하나가 모든 target 알림을 억제한다. inhibition 설정 후 반드시 테스트해야 한다.

### Silencing

계획된 배포나 점검 시간에 알림을 임시로 막는다. Alertmanager UI에서 직접 만들거나 `amtool`로 생성한다.

```bash
# 30분 동안 payment-service 관련 알림 무음
amtool silence add \
  alertname=~"Payment.*" \
  --duration=30m \
  --comment="payment-service v2.1.0 배포"

# silence 목록 확인
amtool silence query

# silence 해제
amtool silence expire <silence-id>
```

배포 파이프라인에 silence 생성/삭제를 끼워 넣으면 배포 중 알림 폭탄을 막을 수 있다. 배포 시작 전에 silence 만들고, 배포 완료 후 삭제하는 식이다. silence를 만들어두고 삭제를 잊으면 진짜 장애도 무음 처리된다. 만료 시간은 배포 예상 시간의 1.5배 정도로 잡는다.

## 에스컬레이션 정책

severity 레이블로 심각도를 구분하고, 각 심각도마다 다른 receiver로 라우팅한다.

```yaml
route:
  receiver: 'slack-general'
  routes:
    - matchers:
        - severity="critical"
      receiver: 'pagerduty-critical'
      continue: true

    - matchers:
        - severity="critical"
      receiver: 'slack-critical'

    - matchers:
        - severity="warning"
      receiver: 'slack-warning'

    - matchers:
        - severity="info"
      receiver: 'slack-info'
      group_wait: 5m
      repeat_interval: 24h
```

`continue: true`는 해당 route 처리 후 다음 route도 계속 평가한다는 의미다. critical 알림을 PagerDuty로 보내면서 Slack에도 함께 보낼 때 쓴다.

severity 기준은 팀마다 다르지만 실무에서 쓰는 기준은 아래와 같다.

- critical: 현재 사용자가 영향받고 있거나 5분 내에 받을 상황. 즉시 대응.
- warning: 지금은 괜찮지만 방치하면 critical로 발전할 가능성. 업무 시간 내 대응.
- info: 인지는 해야 하지만 자동 복구되거나 즉각 조치가 필요없는 상황.

info 알림은 처음엔 다 넣고 싶지만, 실제로 100개가 쌓이면 아무도 안 읽는다. 주기적으로 확인해야 하는 것만 남겨야 한다.

## PagerDuty·Slack 채널 분리

```yaml
receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - routing_key: '${PAGERDUTY_INTEGRATION_KEY}'
        severity: 'critical'
        description: '{{ .CommonAnnotations.summary }}'
        details:
          cluster: '{{ .CommonLabels.cluster }}'
          service: '{{ .CommonLabels.service }}'

  - name: 'slack-critical'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts-critical'
        title: '[CRITICAL] {{ .CommonAnnotations.summary }}'
        text: |
          *설명:* {{ .CommonAnnotations.description }}
          *서비스:* {{ .CommonLabels.service }}
          *클러스터:* {{ .CommonLabels.cluster }}
        send_resolved: true

  - name: 'slack-warning'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts-warning'
        title: '[WARNING] {{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
        send_resolved: true

  - name: 'slack-info'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts-info'
        title: '[INFO] {{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
        send_resolved: false
```

`send_resolved: true`는 알림이 해소됐을 때 resolved 메시지를 발송한다. info는 resolved까지 받으면 채널이 너무 시끄러워지므로 false로 둔다.

채널을 분리하면 온콜 담당자가 `#alerts-critical`만 모니터링하고, `#alerts-warning`은 다음 날 확인하는 식으로 운영할 수 있다. 한 채널에 다 섞으면 critical이 warning에 묻힌다.

## Burn Rate 기반 알림

SLO 기반 알림에서 단순 임계값 방식은 에러 버짓 소진 속도를 반영하지 못한다. 에러율이 1%여도 지속 시간에 따라 버짓 소진 속도가 달라진다.

Burn rate는 에러 버짓 소진 속도다. burn rate 1은 SLO 기간(보통 30일) 동안 에러 버짓을 정확히 다 쓰는 속도다. burn rate 14면 30일 분량을 약 2일 만에 소진한다.

### 1h/6h 복합 burn rate

단일 시간 윈도우 burn rate는 짧으면 flapping이 심하고, 길면 감지가 늦다. 두 윈도우를 AND 조건으로 함께 쓰면 이 트레이드오프를 줄인다.

```yaml
# SLO: 99.9% availability (30일 에러 버짓 = 43.2분)
# 허용 에러율 = 1 - 0.999 = 0.001

groups:
  - name: slo-burn-rate
    rules:
      - record: job:http_requests_errors:rate1h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1h]))
          / sum(rate(http_requests_total[1h]))

      - record: job:http_requests_errors:rate6h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[6h]))
          / sum(rate(http_requests_total[6h]))

      # 1h AND 6h 모두 14.4x 초과 → 에러 버짓 2%를 약 1시간 안에 소진
      - alert: SLOBurnRateCritical
        expr: |
          job:http_requests_errors:rate1h > (14.4 * 0.001)
          and
          job:http_requests_errors:rate6h > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "SLO 에러 버짓 급속 소진"
          description: "1h 에러율: {{ $value | humanizePercentage }}, 약 2시간 내 버짓 소진 예상"

      # 1h AND 6h 모두 6x 초과 → 에러 버짓 5%를 약 5시간 안에 소진
      - alert: SLOBurnRateWarning
        expr: |
          job:http_requests_errors:rate1h > (6 * 0.001)
          and
          job:http_requests_errors:rate6h > (6 * 0.001)
        for: 15m
        labels:
          severity: warning
          slo: availability
        annotations:
          summary: "SLO 에러 버짓 소진 속도 증가"
          description: "현재 속도가 유지되면 30일 버짓을 5일 안에 소진"
```

`14.4`는 1시간 내에 에러 버짓 2%를 소진할 때의 burn rate 값이다. 계산식은 `(2% / (1h / 720h)) = 14.4`다. 720은 30일을 시간 단위로 환산한 값이다.

두 윈도우의 AND 조건이 핵심이다. 1h만 보면 순간 스파이크에 알림이 나가고, 6h만 보면 빠른 장애를 늦게 잡는다. 둘 다 높아야 실제 문제로 판단한다.

## 알림이 너무 많을 때 트러블슈팅

운영하다 보면 어느 순간 알림이 100개 넘게 쌓인 걸 발견한다. 원인을 찾는 순서가 있다.

**어떤 알림이 가장 많이 발생하는지 파악**

```bash
# firing 중인 알림 전체 조회
amtool alert query

# silenced, inhibited 포함 전체 상태 확인
amtool alert query --silenced --inhibited

# 특정 알림만 필터
amtool alert query alertname="APIHighErrorRate"
```

Alertmanager UI의 `/api/v2/alerts` 엔드포인트에서 JSON을 받아 `jq`로 파싱하면 alertname별 firing 수를 빠르게 파악할 수 있다.

**Flapping 알림 찾기**

`for` 조건을 넘었다가 사라졌다가를 반복하는 알림은 pending → firing → resolved 사이클이 짧게 반복된다. Prometheus의 ALERTS 메트릭에서 확인한다.

```promql
changes(ALERTS{alertstate="firing"}[1h]) > 2
```

flapping이 잡히면 임계값을 높이거나 `for` 시간을 늘려서 해결한다. 메트릭 자체가 불안정한 경우도 있다. 그럴 때는 더 긴 집계 범위를 쓰거나 recording rule에서 smoothing을 추가한다.

**임계값 재검토**

처음 설정할 때 적당히 잡은 값이 트래픽이 늘거나 서비스 특성이 바뀌면서 맞지 않게 된다.

```promql
# 최근 7일 P95 에러율로 정상 범위 파악
quantile_over_time(0.95,
  (
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))
  )[7d:5m]
)
```

이 값이 0.03이면 임계값을 0.01로 잡은 건 너무 낮다. 정상 범위를 먼저 파악하고 임계값을 조정한다.

**레이블 카디널리티 폭발**

알림 규칙에 고유한 값이 많은 레이블을 포함하면 알림 수가 폭발한다. `user_id`, `request_id` 같은 레이블을 알림 규칙에 쓰면 안 된다.

```yaml
# 잘못된 예 — user_id가 수천 개면 알림도 수천 개
- alert: UserRequestError
  expr: rate(http_requests_total{status="500", user_id=~".+"}[5m]) > 0

# 서비스 단위로 집계
- alert: ServiceRequestError
  expr: |
    sum by (service) (rate(http_requests_total{status="500"}[5m])) > 0.1
```

카디널리티 문제는 Prometheus 성능에도 영향을 준다. `prometheus_tsdb_head_series` 메트릭으로 시리즈 수를 모니터링하고, 급격히 늘어나면 어떤 레이블이 원인인지 찾는다.

**알림 개수 자체를 모니터링**

```yaml
- alert: TooManyAlerts
  expr: count(ALERTS{alertstate="firing"}) > 20
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "firing 알림 20개 초과"
    description: "알림 규칙 점검 필요. 현재 firing: {{ $value }}개"
```

이 알림이 울리면 누군가 알림 규칙을 다시 검토해야 한다는 신호다. 임계값은 평소 운영 상황에 맞게 잡는다. 정상 상태에서 3~5개면 10개로, 10개 언저리면 25개로 잡는 식이다.
