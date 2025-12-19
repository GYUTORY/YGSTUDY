---
title: Grafana
tags: [devops, monitoring, grafana, visualization, dashboard]
updated: 2025-12-19
---

# Grafana

## 정의

Grafana는 메트릭 데이터를 시각화하고 모니터링하기 위한 오픈소스 플랫폼입니다.

### 주요 기능
- 다양한 데이터 소스 지원 (Prometheus, MySQL, PostgreSQL 등)
- 대시보드 생성 및 공유
- 알림 및 경고
- 플러그인 생태계

## 설치 및 설정

### Docker로 설치

```bash
docker run -d \
  -p 3000:3000 \
  --name=grafana \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana:latest
```

### Kubernetes로 설치

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "admin"
```

## 데이터 소스 연동

### Prometheus 연동

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      access: proxy
      url: http://prometheus:9090
      isDefault: true
```

## 대시보드 구축

### 기본 패널 예제

```json
{
  "dashboard": {
    "title": "Node.js Application Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

### PromQL 쿼리 예제

```promql
# CPU 사용률
rate(process_cpu_seconds_total[5m])

# 메모리 사용량
process_resident_memory_bytes

# 요청 수
rate(http_requests_total[5m])

# 에러율
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

## 알림 설정

### Slack 알림

```yaml
apiVersion: 1
alerting:
  contactpoints:
  - name: Slack
    type: slack
    settings:
      url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL

policies:
- receiver: Slack
  group_by: ['alertname']
  routes:
  - match:
      severity: critical
    receiver: Slack
```

### 알림 규칙

```yaml
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
```

## 실전 대시보드

### Node.js 애플리케이션 모니터링

**주요 패널:**
- Request Rate (요청 수)
- Response Time (응답 시간)
- Error Rate (에러율)
- CPU Usage (CPU 사용률)
- Memory Usage (메모리 사용량)
- Active Connections (활성 연결 수)

**PromQL 쿼리:**
```promql
# Request Rate
rate(http_requests_total[5m])

# P95 Response Time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error Rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# CPU Usage
rate(process_cpu_seconds_total[5m]) * 100

# Memory Usage
process_resident_memory_bytes / 1024 / 1024
```

## 참고

### 데이터 소스 지원

| 데이터 소스 | 유형 | 사용 사례 |
|-----------|------|----------|
| Prometheus | 시계열 | 메트릭 모니터링 |
| MySQL | 관계형 DB | 비즈니스 데이터 |
| PostgreSQL | 관계형 DB | 비즈니스 데이터 |
| Elasticsearch | 로그 | 로그 분석 |
| InfluxDB | 시계열 | IoT 데이터 |

### 패널 타입

| 타입 | 설명 | 사용 사례 |
|------|------|----------|
| Graph | 시계열 그래프 | 추세 분석 |
| Stat | 단일 값 표시 | 현재 상태 |
| Table | 테이블 형식 | 상세 데이터 |
| Heatmap | 히트맵 | 분포 분석 |
| Gauge | 게이지 | 사용률 표시 |

### 관련 문서
- [Grafana Official Documentation](https://grafana.com/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)
