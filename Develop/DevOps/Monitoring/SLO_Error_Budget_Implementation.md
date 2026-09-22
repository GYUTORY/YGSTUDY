---
title: SLO와 에러 버짓 구현
tags: [monitoring, observability, devops]
updated: 2026-09-22
---

# SLO와 에러 버짓 구현

SLO를 "99.9% 가용성 목표"로 문서에 적는 팀은 많다. 그게 실제로 Prometheus에 구현돼 알림까지 연결된 팀은 드물다. 대부분 Grafana 대시보드에 에러율 그래프 하나 걸어두고 SLO를 달성하고 있다고 착각한다.

SLO 구현에서 핵심은 세 가지다. 무엇을 측정할지(SLI), 얼마나 허용할지(에러 버짓), 언제 알릴지(번 레이트). 이 세 가지가 PromQL로 연결되지 않으면 SLO는 보고서용 숫자에 불과하다.

## SLI 정의와 recording rule

SLI(Service Level Indicator)는 "좋은 이벤트 수 / 전체 이벤트 수"로 정의한다. 단순 비율이다.

직접 알림 규칙에 복잡한 PromQL을 넣으면 매 평가 주기마다 계산이 반복된다. recording rule로 사전 계산하면 알림 규칙은 단순한 임계값 비교만 한다. 멀티윈도우 알림에서 같은 계산을 여러 번 참조할 때 비용 차이가 크다.

recording rule 이름은 `sli:` 접두어를 관례로 사용한다. Prometheus의 네임스페이스가 없으니 접두어로 구분하는 수밖에 없다.

### 가용성 SLI

HTTP 서비스 기준으로 5xx를 나쁜 이벤트로 정의한다.

```yaml
# prometheus-recording-rules.yaml
groups:
  - name: sli.availability
    interval: 30s
    rules:
      # 5분 윈도우 - 빠른 번 레이트 감지용
      - record: sli:http_availability:ratio_rate5m
        expr: |
          sum(rate(http_requests_total{job="api",status!~"5.."}[5m]))
          /
          sum(rate(http_requests_total{job="api"}[5m]))

      # 30분 윈도우
      - record: sli:http_availability:ratio_rate30m
        expr: |
          sum(rate(http_requests_total{job="api",status!~"5.."}[30m]))
          /
          sum(rate(http_requests_total{job="api"}[30m]))

      # 1시간 윈도우
      - record: sli:http_availability:ratio_rate1h
        expr: |
          sum(rate(http_requests_total{job="api",status!~"5.."}[1h]))
          /
          sum(rate(http_requests_total{job="api"}[1h]))

      # 6시간 윈도우
      - record: sli:http_availability:ratio_rate6h
        expr: |
          sum(rate(http_requests_total{job="api",status!~"5.."}[6h]))
          /
          sum(rate(http_requests_total{job="api"}[6h]))
```

`status!~"5.."` 대신 `status=~"2..|3.."` 을 쓰는 팀도 있다. 차이가 있다. 4xx를 나쁜 이벤트로 볼지 여부가 다르다. 클라이언트 에러(400, 401, 404)를 SLI에 포함하면 클라이언트 버그가 SLO를 갉아먹는다. 서버 측 가용성만 보려면 5xx만 나쁜 이벤트로 잡는 게 맞다.

### 레이턴시 SLI

레이턴시 SLI는 "목표 레이턴시 내에 처리된 요청 비율"이다. "평균 응답시간 200ms 이하"가 아니다.

histogram_quantile로 p99를 알림에 쓰면 안 된다. `histogram_quantile`은 근삿값이고, rate + histogram_quantile 조합은 비율 계산이 아니라 분위수 계산이라 에러 버짓 수학과 맞지 않는다.

올바른 방법은 histogram의 버킷을 직접 쓰는 것이다.

```yaml
  - name: sli.latency
    interval: 30s
    rules:
      # 300ms 이내 처리된 요청 비율 - 5분 윈도우
      - record: sli:http_latency_300ms:ratio_rate5m
        expr: |
          sum(rate(http_request_duration_seconds_bucket{job="api",le="0.3"}[5m]))
          /
          sum(rate(http_request_duration_seconds_count{job="api"}[5m]))

      - record: sli:http_latency_300ms:ratio_rate30m
        expr: |
          sum(rate(http_request_duration_seconds_bucket{job="api",le="0.3"}[30m]))
          /
          sum(rate(http_request_duration_seconds_count{job="api"}[30m]))

      - record: sli:http_latency_300ms:ratio_rate1h
        expr: |
          sum(rate(http_request_duration_seconds_bucket{job="api",le="0.3"}[1h]))
          /
          sum(rate(http_request_duration_seconds_count{job="api"}[1h]))

      - record: sli:http_latency_300ms:ratio_rate6h
        expr: |
          sum(rate(http_request_duration_seconds_bucket{job="api",le="0.3"}[6h]))
          /
          sum(rate(http_request_duration_seconds_count{job="api"}[6h]))
```

`le="0.3"` 은 histogram 버킷 경계값이다. `http_request_duration_seconds_bucket`에 실제로 0.3 버킷이 있어야 한다. 계측 코드에서 버킷을 `[0.05, 0.1, 0.25, 0.5, 1.0, 2.5]` 처럼 잡았다면 0.3 버킷이 없으니 0.25 버킷을 쓰거나 목표 레이턴시를 버킷 경계에 맞춰야 한다.

## 에러 버짓 계산

SLO 99.9%라면 에러 버짓은 0.1%다. 30일 기준으로 43.2분이다.

```
에러 버짓 = (1 - SLO) × 기간
```

현재 에러 버짓 소진량은 recording rule에서 바로 계산할 수 있다.

```yaml
  - name: error_budget
    interval: 30s
    rules:
      # 30일 롤링 윈도우 에러 버짓 잔량 (0~1 사이 값)
      - record: slo:error_budget_remaining:availability_30d
        expr: |
          (
            sum(increase(http_requests_total{job="api",status!~"5.."}[30d]))
            /
            sum(increase(http_requests_total{job="api"}[30d]))
            - 0.999
          ) / 0.001
```

이 값이 0이면 에러 버짓을 전부 소진한 것이고, 음수면 초과 소진이다. 1이면 에러가 하나도 없었다는 뜻이다.

`increase` 대신 `rate`를 써도 되지만 30일 윈도우에서는 `increase`가 더 직관적이다. 에러 건수의 누적합이니까.

## 번 레이트 알림

번 레이트(burn rate)는 에러 버짓 소진 속도다. 번 레이트 1.0은 SLO 기간(30일) 동안 에러 버짓을 정확히 다 쓴다는 뜻이다. 번 레이트 2.0이면 15일 만에 소진된다.

단일 윈도우 알림의 문제가 있다. 짧은 윈도우(1h)만 쓰면 민감도가 높아 오탐이 많고, 긴 윈도우(6h)만 쓰면 빠른 장애를 놓친다. Google SRE 워크북의 멀티윈도우 알림이 이 문제를 해결한다.

**멀티윈도우 원리:** 짧은 윈도우와 긴 윈도우를 AND로 묶는다. 짧은 윈도우는 지금 문제가 있는지 감지하고, 긴 윈도우는 이게 일시적인 스파이크인지 지속적인 문제인지 판단한다.

```yaml
# alerting-rules-slo.yaml
groups:
  - name: slo.burn_rate.availability
    rules:
      # Page 알림 - 즉시 대응 필요
      # 1h 번 레이트 14x + 5m 번 레이트 14x → 에러 버짓 5% 소진 예상
      - alert: SLOBurnRateCritical
        expr: |
          (
            (1 - sli:http_availability:ratio_rate1h{job="api"}) / (1 - 0.999) > 14
            and
            (1 - sli:http_availability:ratio_rate5m{job="api"}) / (1 - 0.999) > 14
          )
          or
          (
            (1 - sli:http_availability:ratio_rate6h{job="api"}) / (1 - 0.999) > 6
            and
            (1 - sli:http_availability:ratio_rate30m{job="api"}) / (1 - 0.999) > 6
          )
        for: 2m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "SLO 에러 버짓 빠른 소진 중"
          description: |
            번 레이트: {{ $value | humanize }}x
            현재 속도 지속 시 에러 버짓 조기 소진 예상
            runbook: https://wiki.internal/runbooks/slo-burn-rate

      # Ticket 알림 - 당일 내 확인
      # 3d 번 레이트 3x + 1h 번 레이트 3x → 에러 버짓 10% 소진 예상
      - alert: SLOBurnRateWarning
        expr: |
          (1 - sli:http_availability:ratio_rate6h{job="api"}) / (1 - 0.999) > 3
          and
          (1 - sli:http_availability:ratio_rate30m{job="api"}) / (1 - 0.999) > 3
        for: 15m
        labels:
          severity: warning
          slo: availability
        annotations:
          summary: "SLO 에러 버짓 완만한 소진 중"
```

번 레이트 계산식인 `(1 - SLI) / (1 - SLO)` 를 풀어보면: 현재 에러율이 SLO 허용 에러율의 몇 배인지다. SLO 99.9%면 허용 에러율은 0.001이다. 현재 에러율이 0.014라면 번 레이트는 14가 된다.

임계값 14와 6은 Google SRE 워크북의 권고값이다. 30일 SLO 기준으로 계산한 것이다.

| 번 레이트 | 알림 타입 | 에러 버짓 소진 시나리오 |
|---|---|---|
| 14x (1h+5m) | Page | 2시간 내 버짓 5% 소진 |
| 6x (6h+30m) | Page | 5시간 내 버짓 5% 소진 |
| 3x (6h+30m) | Ticket | 5일 내 버짓 10% 소진 |

## 레이턴시 SLO 알림

가용성과 구조는 같다.

```yaml
  - name: slo.burn_rate.latency
    rules:
      - alert: SLOLatencyBurnRateCritical
        expr: |
          (
            (1 - sli:http_latency_300ms:ratio_rate1h{job="api"}) / (1 - 0.999) > 14
            and
            (1 - sli:http_latency_300ms:ratio_rate5m{job="api"}) / (1 - 0.999) > 14
          )
          or
          (
            (1 - sli:http_latency_300ms:ratio_rate6h{job="api"}) / (1 - 0.999) > 6
            and
            (1 - sli:http_latency_300ms:ratio_rate30m{job="api"}) / (1 - 0.999) > 6
          )
        for: 2m
        labels:
          severity: critical
          slo: latency
        annotations:
          summary: "레이턴시 SLO 에러 버짓 빠른 소진 중"
```

## 실제로 걸리는 것들

**트래픽이 없을 때 SLI가 NaN이 된다.** `rate()` 분모가 0이면 Prometheus는 NaN을 반환한다. NaN은 알림 조건에서 false로 평가되니 알림은 안 뜨지만, Grafana에서 그래프가 끊긴다. 새벽 트래픽이 거의 없는 서비스는 이게 자주 발생한다.

해결은 `or on() vector(1)` 패턴으로 트래픽 없을 때 기본값을 주거나, 최소 트래픽 조건을 추가하는 것이다.

```promql
# 분당 10개 이상 요청이 있을 때만 SLI 평가
(1 - sli:http_availability:ratio_rate1h) / (1 - 0.999) > 14
and
sum(rate(http_requests_total{job="api"}[1h])) > 10/60
```

**멀티서비스 SLO는 job 레이블을 유지해야 한다.** recording rule에서 `sum without(job)` 하면 job 레이블이 사라지고, 알림에서 어떤 서비스가 문제인지 모른다. `sum by(job)` 또는 `sum without(instance)` 처럼 job을 살린다.

```yaml
      - record: sli:http_availability:ratio_rate1h
        expr: |
          sum by(job) (rate(http_requests_total{status!~"5.."}[1h]))
          /
          sum by(job) (rate(http_requests_total[1h]))
```

**에러 버짓 정책을 먼저 정해야 알림이 의미있다.** 번 레이트 14x 알림이 울렸을 때 팀이 뭘 해야 하는지 사전에 합의가 없으면, 알림을 보고도 "일단 지켜보자"가 된다. 에러 버짓이 몇 퍼센트 이하로 내려가면 기능 개발을 멈추고 신뢰성 작업에 집중한다는 기준을 미리 팀과 합의해두어야 한다.

**30일 롤링 윈도우와 달력 월의 차이.** 많은 팀이 SLO를 "이번 달" 기준으로 말하지만 Prometheus recording rule은 30일 롤링 윈도우다. 달력 월은 28~31일이 섞이고 Prometheus의 range selector로 정확히 표현하기 어렵다. 롤링 윈도우를 쓰면 "30일 내 에러 버짓"이 항상 계산된다. 월 초에 리셋되는 방식이 필요하면 Thanos Ruler나 외부 도구를 써야 한다.
