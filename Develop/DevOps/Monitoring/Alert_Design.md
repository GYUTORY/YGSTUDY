---
title: 알림 설계 심화
tags: [monitoring, observability, devops]
updated: 2026-09-22
---

# 알림 설계 심화

증상 기반과 원인 기반 알림을 구분하지 않고 쌓다 보면 몇 달 뒤에 알림 채널이 쓰레기통이 된다. 원인 알림은 어디서 시작됐는지 알려주고, 증상 알림은 사용자에게 지금 어떤 영향이 가는지 알려준다. 이 둘이 뒤섞이면 대응 우선순위가 무너진다.

## 증상 기반 vs 원인 기반

원인 알림은 시스템 내부 상태다. CPU 사용률 90%, DB 슬레이브 지연 30초, 디스크 80% 도달이 여기 속한다. 증상 알림은 사용자가 실제로 겪는 것이다. 에러율 5% 초과, 응답 시간 2초 초과, 결제 실패율 증가.

원인 알림만 있으면 CPU가 90%인데 사용자 영향이 있는지 즉시 판단이 안 된다. 야간 배치 때문에 매일 밤 90%가 되는 시스템이라면 쓸모없는 호출이 반복된다. 증상 알림만 있으면 에러율 5%가 뜬 상황에서 무엇 때문인지 바닥부터 파야 한다.

원칙: 알림은 증상 기반으로 발송하고, 대시보드와 런북에서 원인 드릴다운을 제공한다. 원인 알림은 PagerDuty 같은 on-call 채널이 아니라 Slack 정보 채널로 보낸다. 받아도 즉시 대응이 필요하지 않다면 on-call을 깨워서는 안 된다.

| 알림 | 분류 | 적절한 채널 |
|---|---|---|
| CPU 사용률 90% 5분 지속 | 원인 | Slack info |
| 에러율 5% 초과 5분 지속 | 증상 | PagerDuty critical |
| DB replication lag 30s | 원인 | Slack warning |
| 결제 API latency p99 > 3s | 증상 | PagerDuty critical |
| 디스크 사용률 80% | 원인 | Slack + 티켓 |
| 로그인 성공률 95% 미만 | 증상 | PagerDuty critical |

같은 DB 슬레이브 지연이라도 읽기 전용 서비스가 slaveOK로 조회한다면 그건 증상이다. 서비스 특성에 따라 분류가 달라진다.

## Alertmanager inhibition

inhibition은 근본 원인 알림이 있을 때 파생 알림을 억제하는 기능이다. DB가 다운되면 API 에러율, 슬로우쿼리, 커넥션 풀 고갈이 한꺼번에 터지는데 이 셋은 억제 대상이다.

```yaml
inhibit_rules:
  # 노드 다운 시 해당 노드의 warning/info 전부 억제
  - source_matchers:
      - alertname="NodeDown"
    target_matchers:
      - severity=~"warning|info"
    equal: ['instance']

  # DB 클러스터 다운 시 application 레벨 파생 알림 억제
  - source_matchers:
      - alertname="DatabaseClusterDown"
      - severity="critical"
    target_matchers:
      - alertname=~"APIHighErrorRate|ConnectionPoolExhausted|SlowQuery"
    equal: ['cluster']

  # critical이 발생한 서비스의 warning 억제
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal: ['service', 'cluster']
```

`equal` 필드가 핵심이다. source와 target에서 이 레이블 값이 같아야 억제가 작동한다. `equal: ['cluster']`로 잡으면 prod-kr DB가 다운됐을 때 prod-us의 API 알림은 억제되지 않는다. `equal`을 빠뜨리면 source 하나가 전체 target을 억제해버린다.

설정 후 실제로 작동하는지 확인하는 방법:

```bash
# source 알림 직접 삽입
curl -X POST http://localhost:9093/api/v2/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "NodeDown",
      "instance": "prod-node-1",
      "severity": "critical"
    },
    "startsAt": "2026-09-22T00:00:00Z"
  }]'

# 억제된 알림 목록 확인
curl -s "http://localhost:9093/api/v2/alerts?inhibited=true" \
  | jq '.[] | select(.status.inhibitedBy | length > 0) | .labels'
```

`inhibitedBy` 필드에 억제한 source alert ID가 들어온다. 비어있으면 억제가 안 된 것이다.

한 가지 주의할 점이 있다. inhibition은 Alertmanager가 알림을 받은 시점부터 작동한다. `for` 절 때문에 source 알림이 target보다 늦게 Alertmanager에 도달하는 경우가 있다. DB 다운이 critical로 전환되는 데 5분이 걸리는데, APIHighErrorRate는 이미 2분에 도달해서 Slack에 나간 뒤인 상황이다. source의 `for`를 target보다 짧게 잡는 이유가 여기 있다.

## Silencing

Silence는 특정 레이블 조합의 알림을 일정 시간 동안 막는다. 배포 중 재시작 알림, 정기 점검, 알려진 문제 대응 중에 쓴다.

```bash
# 특정 서비스 warning 2시간 silence
curl -X POST http://localhost:9093/api/v2/silences \
  -H 'Content-Type: application/json' \
  -d '{
    "matchers": [
      {"name": "service", "value": "payment-api", "isRegex": false},
      {"name": "severity", "value": "warning", "isRegex": false}
    ],
    "startsAt": "2026-09-22T10:00:00Z",
    "endsAt": "2026-09-22T12:00:00Z",
    "createdBy": "deploy-bot",
    "comment": "payment-api v2.3.1 배포 중 — 알려진 재시작 알림"
  }'
```

`comment`에 이유를 반드시 적는다. 나중에 왜 이 시간대에 silence가 있었는지 파악이 안 되는 상황이 생긴다.

CD 파이프라인에서 배포 전 silence를 자동 생성하고 완료 후 해제하는 패턴:

```bash
# 배포 전 silence 생성 (30분)
SILENCE_ID=$(curl -s -X POST http://alertmanager:9093/api/v2/silences \
  -H 'Content-Type: application/json' \
  -d "{
    \"matchers\": [{\"name\": \"service\", \"value\": \"${SERVICE}\", \"isRegex\": false}],
    \"startsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"endsAt\": \"$(date -u -d '+30 minutes' +%Y-%m-%dT%H:%M:%SZ)\",
    \"createdBy\": \"deploy-pipeline\",
    \"comment\": \"${SERVICE} 배포 ${DEPLOY_ID}\"
  }" | jq -r '.silenceID')

# 배포 실행
deploy_service

# 완료 후 즉시 해제
curl -X DELETE "http://alertmanager:9093/api/v2/silences/${SILENCE_ID}"
```

silence를 만들고 해제를 안 하면, 배포 후 실제 문제가 생겨도 알림이 차단된다. 명시적 해제는 필수다.

## Alertmanager 라우팅 실전 패턴

### 멀티 receiver 발송

같은 알림을 PagerDuty로 보내면서 Slack에도 기록하고 싶을 때:

```yaml
receivers:
  - name: 'pagerduty-and-slack'
    pagerduty_configs:
      - routing_key: '${PD_ROUTING_KEY}'
        severity: 'critical'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK}'
        channel: '#ops-alerts'
        text: '{{ .CommonAnnotations.description }}'
```

하나의 receiver에 여러 provider를 붙이면 동시에 발송된다.

### team 레이블 기반 동적 라우팅

서비스가 늘어날수록 라우팅 규칙도 늘어난다. `team` 레이블로 묶으면 서비스가 추가돼도 라우팅 규칙을 건드릴 필요가 없다.

```yaml
receivers:
  - name: 'team-backend'
    slack_configs:
      - channel: '#backend-alerts'
        api_url: '${SLACK_BACKEND_WEBHOOK}'

  - name: 'team-infra'
    slack_configs:
      - channel: '#infra-alerts'
        api_url: '${SLACK_INFRA_WEBHOOK}'

route:
  receiver: 'default'
  routes:
    - matchers:
        - team="backend"
      receiver: 'team-backend'
    - matchers:
        - team="infra"
      receiver: 'team-infra'
```

이 구조는 알림 규칙에 `team` 레이블이 반드시 있어야 작동한다. 빠뜨리면 default로 떨어진다. 레이블 강제를 위해 prometheus-operator의 PrometheusRule에 `team` 레이블을 필수 항목으로 두는 validation webhook을 붙이는 팀도 있다.

## 런북 링크 삽입 패턴

런북이 없으면 새벽 알림을 받은 담당자가 뭘 해야 할지 모른다. 알림 발생 → Slack/PagerDuty에서 런북 클릭 → 절차 실행이 이어져야 MTTR이 줄어든다.

### annotations에 삽입

```yaml
annotations:
  summary: "API Gateway 에러율 5% 초과"
  description: |
    에러율: {{ $value | humanizePercentage }}
    대상: {{ $labels.service }} / {{ $labels.cluster }}
  runbook: "https://wiki.internal/runbooks/api-gateway-high-error-rate"
  dashboard: "https://grafana.internal/d/api-gw?var-cluster={{ $labels.cluster }}"
```

Alertmanager Slack 템플릿에서 이 값을 참조한다.

```yaml
receivers:
  - name: 'slack-ops'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK}'
        channel: '#ops-alerts'
        title: '[{{ .Status | toUpper }}] {{ .CommonAnnotations.summary }}'
        title_link: '{{ .CommonAnnotations.runbook }}'
        text: |
          {{ .CommonAnnotations.description }}
          *런북:* {{ .CommonAnnotations.runbook }}
          *Grafana:* {{ .CommonAnnotations.dashboard }}
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
        actions:
          - type: button
            text: 'Runbook'
            url: '{{ .CommonAnnotations.runbook }}'
          - type: button
            text: 'Grafana'
            url: '{{ .CommonAnnotations.dashboard }}'
          - type: button
            text: 'Silence 1h'
            url: '{{ .ExternalURL }}/#/silences/new?filter=%7Balertname%3D"{{ .CommonLabels.alertname }}"%7D'
```

`Silence 1h` 버튼은 Alertmanager UI silence 생성 폼으로 연결된다. 대응 중 추가 노이즈를 막을 때 클릭 한 번으로 된다.

### 동적 런북 URL

서비스가 많을 때 알림마다 URL을 직접 쓰면 오래된 URL이 남는다. 패턴으로 생성하는 방법:

```yaml
annotations:
  runbook: "https://wiki.internal/runbooks/{{ $labels.service }}-{{ $labels.alertname | lower }}"
```

`payment-api-highErrorRate` 같은 경로가 만들어진다. 런북이 이 경로로 존재해야 한다. 현실에서는 서비스명이 바뀌거나 알림 이름이 리팩토링되면 URL도 바뀐다. 이 경우 고정 인덱스 페이지를 두고 거기서 링크를 관리하는 방식이 더 낫다. 404가 뜨는 것보다 인덱스로 떨어지는 게 낫다.

### PagerDuty 상세에 런북 포함

```yaml
receivers:
  - name: 'pagerduty-prod'
    pagerduty_configs:
      - routing_key: '${PD_ROUTING_KEY}'
        severity: |
          {{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}
        summary: '{{ .CommonAnnotations.summary }}'
        details:
          service: '{{ .CommonLabels.service }}'
          cluster: '{{ .CommonLabels.cluster }}'
          runbook: '{{ .CommonAnnotations.runbook }}'
          value: '{{ .CommonAnnotations.description }}'
        links:
          - href: '{{ .CommonAnnotations.runbook }}'
            text: 'Runbook'
          - href: 'https://grafana.internal/d/overview?var-service={{ .CommonLabels.service }}'
            text: 'Grafana'
```

`links`는 PagerDuty incident 화면에서 버튼으로 표시된다. 런북과 Grafana 두 버튼만 있어도 담당자가 알림 열자마자 현황 파악이 된다.

## PagerDuty / Slack 연동 주의사항

### PagerDuty resolve_timeout

PagerDuty에서 `resolve_timeout`을 기본값으로 두면 문제가 생긴다. Alertmanager 기본 `resolve_timeout`은 5분이다. `scrape_interval` 30s, `evaluation_interval` 1m, `for: 5m`짜리 알림이라면 조건 해소 후 Alertmanager에 resolved가 도달하는 데 최대 6분을 넘을 수 있다. `resolve_timeout`이 5분이면 resolved가 도달하기 전에 Alertmanager가 먼저 resolve를 보내고, 그 직후 다시 firing이 오는 flapping처럼 보인다.

```yaml
# alertmanager.yml global 설정
global:
  resolve_timeout: 10m
```

`for` 절 최댓값보다 resolve_timeout이 충분히 길어야 한다.

### PagerDuty 팀별 routing_key 분리

routing_key 하나가 PagerDuty service 하나에 대응한다. 팀별로 다른 service를 쓰면 escalation policy를 따로 관리할 수 있다.

```yaml
receivers:
  - name: 'pagerduty-backend-prod'
    pagerduty_configs:
      - routing_key: '${PD_BACKEND_KEY}'

  - name: 'pagerduty-infra-prod'
    pagerduty_configs:
      - routing_key: '${PD_INFRA_KEY}'
```

on-call 로테이션이 팀마다 다르면 이렇게 분리하는 것이 낫다. 인프라 장애로 백엔드 팀이 깨어나는 상황을 막는다.

### Slack send_resolved

`send_resolved: true`를 켜면 resolved 알림도 같은 채널로 온다. firing → resolved 쌍이 보이면 언제 해소됐는지 기록이 된다. 빠른 flapping이 있으면 채널이 시끄러워진다. 이 경우 resolved는 별도 채널로 분리하거나 `group_interval`을 늘린다.

```yaml
slack_configs:
  - channel: '#ops-alerts'
    send_resolved: true
  # resolved는 별도 채널
  - channel: '#ops-resolved'
    send_resolved: true
    # firing은 보내지 않으려면 text에서 조건 처리
    text: |
      {{ if eq .Status "resolved" }}
      해소: {{ .CommonAnnotations.summary }}
      {{ end }}
```

## 알림 피로 측정과 임계값 튜닝

알림 피로를 주관적으로 판단하면 개선이 안 된다. 측정 기준이 있어야 임계값 튜닝을 할 수 있다.

**MTTA (Mean Time To Acknowledge)**: 알림 발송 ~ 담당자 acknowledgement까지 시간. PagerDuty, OpsGenie API에서 뽑을 수 있다. MTTA가 15분을 넘으면 받고도 안 보고 있다는 신호다.

**노이즈 비율**: 알림 수 대비 자동 해소 알림 수. acknowledged 후 MTTR이 5분 미만으로 끝난 건 "사람이 개입하지 않아도 해소됐다"로 분류한다.

```
노이즈 비율 = 자동 해소 알림 수 / 전체 발송 알림 수
```

이 비율이 30%를 넘으면 임계값 재검토가 필요하다.

Alertmanager 메트릭으로 발송 현황을 추적한다.

```promql
# 1주일 receiver별 알림 발송 수
increase(alertmanager_notifications_total[7d])

# 전달 실패 수
increase(alertmanager_notifications_failed_total[7d])

# 현재 억제 중인 알림 수
alertmanager_inhibited_alerts

# silenced 알림 수
alertmanager_silenced_alerts
```

Slack receiver로 1주일에 500건을 넘으면 노이즈가 심한 것이다. 팀 규모와 서비스 수에 따라 다르지만, 한 명이 소화할 수 있는 알림의 실질적 상한은 하루 20건 내외다.

### 임계값 잡는 방법

기준 없이 임계값을 잡는 패턴이 있다. "에러율 1% 넘으면 알림" — 정상 상태에서 얼마나 자주 1%가 넘는지 확인하지 않고 설정한 경우다.

올바른 순서는 지난 30일 해당 메트릭의 P99 값을 측정하고, 그 값의 1.5~2배를 임계값으로 설정하는 것이다.

```promql
# 지난 30일 에러율 P99
quantile_over_time(0.99,
  (
    sum(rate(http_requests_total{status=~"5..", service="payment-api"}[5m]))
    / sum(rate(http_requests_total{service="payment-api"}[5m]))
  )[30d:5m]
)
```

이 값이 0.008이면 임계값을 0.01~0.015로 잡는다. 0.005로 잡으면 정상적인 날도 알림이 온다.

flapping이 있으면 `for` 절을 늘린다. 단발성 스파이크인지 지속 장애인지 구분하려면 `for: 5m`이 적당한 출발점이다.

### 월간 알림 리뷰

임계값 튜닝은 한 번으로 끝나지 않는다. 트래픽 패턴이 바뀌면 기준선도 바뀐다. 월 1회 지난 달 알림 발송 내역을 보면서 세 가지를 확인한다.

한 번도 안 나간 알림은 임계값이 너무 높거나 메트릭 레이블이 달라진 것이다. 매일 발송된 알림은 임계값이 너무 낮거나 정상 동작을 잡고 있는 것이다. MTTA가 30분을 넘는 알림은 심각도 재검토가 필요하다. 이 세 분류에 걸린 알림만 추려도 실제 수정 대상은 전체의 10~20% 안에 들어온다.
