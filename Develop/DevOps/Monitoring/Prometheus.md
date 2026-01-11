---
title: Prometheus
tags: [devops, monitoring, prometheus, metrics, observability]
updated: 2026-01-11
---

# Prometheus

## 정의

Prometheus는 시계열 데이터 기반의 오픈소스 모니터링 및 알림 시스템입니다.

### 주요 특징
- Pull 기반 메트릭 수집
- 다차원 데이터 모델
- 강력한 쿼리 언어 (PromQL)
- 서비스 디스커버리 지원

## 아키텍처

### 핵심 구성 요소

```
[애플리케이션] → [Exporter] ← [Prometheus] → [Grafana]
                                    ↓
                              [Alertmanager]
```

| 구성 요소 | 역할 |
|---------|------|
| Prometheus Server | 메트릭 수집 및 저장 |
| Exporter | 메트릭 노출 |
| Pushgateway | 단기 작업 메트릭 수집 |
| Alertmanager | 알림 관리 |

## 설치 및 설정

### Docker로 설치

```bash
docker run -d \
  -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### 기본 설정 (prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'nodejs-app'
    static_configs:
      - targets: ['nodejs-app:3000']
```

## 메트릭 타입

### Counter (카운터)

누적 값을 표현합니다 (증가만 가능).

```javascript
const promClient = require('prom-client');

const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'status']
});

// 사용
httpRequestsTotal.inc({ method: 'GET', status: '200' });
```

### Gauge (게이지)

현재 값을 표현합니다 (증가/감소 가능).

```javascript
const activeConnections = new promClient.Gauge({
  name: 'active_connections',
  help: 'Number of active connections'
});

// 사용
activeConnections.set(50);
activeConnections.inc();  // 51
activeConnections.dec();  // 50
```

### Histogram (히스토그램)

값의 분포를 측정합니다.

```javascript
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  buckets: [0.1, 0.5, 1, 2, 5]
});

// 사용
const end = httpRequestDuration.startTimer();
// ... request processing ...
end();
```

### Summary (요약)

분위수를 계산합니다.

```javascript
const httpRequestDuration = new promClient.Summary({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  percentiles: [0.5, 0.9, 0.95, 0.99]
});
```

## PromQL 쿼리

### 기본 쿼리

```promql
# 현재 값
http_requests_total

# 레이블 필터
http_requests_total{method="GET",status="200"}

# 초당 증가율
rate(http_requests_total[5m])

# 합계
sum(http_requests_total)

# 평균
avg(http_response_time_seconds)
```

### 고급 쿼리

```promql
# P95 응답 시간
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 에러율
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# 그룹별 합계
sum by (method) (rate(http_requests_total[5m]))
```

## Node.js 통합

### 기본 설정

```javascript
const express = require('express');
const promClient = require('prom-client');

const app = express();

// 기본 메트릭 수집
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

// 커스텀 메트릭
const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status'],
  registers: [register]
});

const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status'],
  registers: [register]
});

// 미들웨어
app.use((req, res, next) => {
  const end = httpRequestDuration.startTimer();
  
  res.on('finish', () => {
    httpRequestsTotal.inc({
      method: req.method,
      route: req.route?.path || req.path,
      status: res.statusCode
    });
    
    end({
      method: req.method,
      route: req.route?.path || req.path,
      status: res.statusCode
    });
  });
  
  next();
});

// 메트릭 엔드포인트
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.listen(3000);
```

## 알림 설정

### Alertmanager 설정

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'slack'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h

receivers:
- name: 'slack'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#alerts'
    title: 'Alert: {{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### 알림 규칙

```yaml
# alert.rules.yml
groups:
- name: example
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }}"

  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes / 1024 / 1024 > 512
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
```

## Service Discovery

### Kubernetes Service Discovery

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
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

## 실전 예제

### Node.js 애플리케이션 모니터링

```javascript
const promClient = require('prom-client');
const register = new promClient.Registry();

// 기본 메트릭
promClient.collectDefaultMetrics({ register });

// HTTP 메트릭
const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'route', 'status'],
  registers: [register]
});

const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.1, 0.5, 1, 2, 5],
  registers: [register]
});

// 비즈니스 메트릭
const ordersTotal = new promClient.Counter({
  name: 'orders_total',
  help: 'Total number of orders',
  labelNames: ['status'],
  registers: [register]
});

const activeUsers = new promClient.Gauge({
  name: 'active_users',
  help: 'Number of active users',
  registers: [register]
});
```

## 참고

### Prometheus vs 다른 모니터링 도구

| 항목 | Prometheus | Graphite | InfluxDB |
|------|-----------|----------|----------|
| 데이터 모델 | 다차원 | 계층적 | 태그 기반 |
| 쿼리 언어 | PromQL | Graphite 함수 | InfluxQL |
| 저장 방식 | 로컬 시계열 DB | Whisper | TSM |
| 알림 | 내장 | 외부 | 외부 |
| 서비스 디스커버리 | 내장 | 없음 | 없음 |

### 메트릭 네이밍 가이드

```
<namespace>_<name>_<unit>

예시:
http_requests_total
http_request_duration_seconds
process_cpu_seconds_total
node_memory_bytes
```

### 관련 문서
- [Prometheus Official Documentation](https://prometheus.io/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Best Practices](https://prometheus.io/docs/practices/naming/)
