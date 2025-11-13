---
title: Grafana 시각화 및 대시보드
tags: [grafana, monitoring, visualization, dashboard, prometheus, metrics, alerting]
updated: 2025-11-01
---

# Grafana 시각화 및 대시보드

## 📋 목차

1. [Grafana란 무엇인가?](#grafana란-무엇인가)
2. [핵심 개념](#핵심-개념)
3. [데이터 소스 연동](#데이터-소스-연동)
4. [대시보드 구축](#대시보드-구축)
5. [패널과 시각화](#패널과-시각화)
6. [쿼리와 변환](#쿼리와-변환)
7. [알림 설정](#알림-설정)
8. [실무 활용 사례](#실무-활용-사례)
9. [최적화 및 베스트 프랙티스](#최적화-및-베스트-프랙티스)
10. [참고 자료](#참고-자료)

---

## Grafana란 무엇인가?

### Grafana의 정의

Grafana는 **오픈소스 메트릭 분석 및 시각화 플랫폼**입니다. 시계열 데이터를 아름답고 직관적인 대시보드로 변환하여, 시스템 상태를 실시간으로 모니터링하고 분석할 수 있게 해줍니다.

**핵심 특징:**
```
1. 다양한 데이터 소스 지원
   - Prometheus, InfluxDB, Elasticsearch
   - MySQL, PostgreSQL, ClickHouse
   - CloudWatch, Azure Monitor
   - 50+ 공식 플러그인

2. 강력한 시각화
   - 그래프, 히트맵, 테이블, 게이지
   - 맞춤형 패널 생성
   - 실시간 업데이트

3. 유연한 대시보드
   - 드래그 앤 드롭 인터페이스
   - 변수를 통한 동적 대시보드
   - 템플릿 공유

4. 알림 시스템
   - 다양한 알림 채널 (Slack, Email, PagerDuty)
   - 복잡한 알림 규칙
   - 알림 히스토리
```

### Grafana의 탄생 배경

**문제 상황:**
```
기존 모니터링 도구의 한계:
- Kibana: Elasticsearch 전용
- Prometheus UI: 기본적인 그래프만
- 상용 도구: 높은 비용, 제한된 커스터마이징

필요성:
- 여러 데이터 소스를 하나의 대시보드에
- 아름답고 직관적인 UI
- 오픈소스, 무료
- 쉬운 공유 및 협업
```

**Grafana의 탄생 (2014년):**
- Torkel Ödegaard가 시작
- Kibana 3의 포크로 시작
- 현재: Grafana Labs에서 관리
- 100만+ 설치, 2000+ 기여자

### 왜 Grafana를 사용하는가?

**1. 통합 모니터링**
```
하나의 대시보드에서:
├─ 애플리케이션 메트릭 (Prometheus)
├─ 인프라 메트릭 (CloudWatch)
├─ 로그 데이터 (Loki)
├─ 데이터베이스 성능 (PostgreSQL)
└─ 비즈니스 메트릭 (ClickHouse)

→ 통합된 관찰 가능성 (Observability)
```

**2. 실시간 의사결정**
```
대시보드를 통해:
- 시스템 이상 징후 즉시 감지
- 성능 병목 지점 파악
- 트래픽 패턴 분석
- 비즈니스 KPI 추적

→ 데이터 기반 의사결정
```

**3. 팀 협업**
```
공유 가능:
- 대시보드 링크 공유
- 스냅샷 생성
- JSON 모델 내보내기
- 폴더 권한 관리

→ 모두가 같은 데이터를 봄
```

### Grafana vs 경쟁 제품

| 특성 | Grafana | Kibana | Datadog | Prometheus UI |
|------|---------|--------|---------|---------------|
| **라이선스** | 오픈소스 (Apache 2.0) | 오픈소스 | 상용 | 오픈소스 |
| **데이터 소스** | 50+ | Elasticsearch 중심 | 자체 에이전트 | Prometheus만 |
| **시각화** | 매우 강력 | 강력 | 강력 | 기본적 |
| **비용** | 무료 (클라우드 유료) | 무료 | 높음 | 무료 |
| **학습 곡선** | 중간 | 중간 | 낮음 | 낮음 |
| **커스터마이징** | 매우 높음 | 중간 | 낮음 | 낮음 |
| **알림** | 강력 | 강력 | 매우 강력 | 기본적 |

---

## 핵심 개념

### 아키텍처 구조

```
┌─────────────────────────────────────────┐
│          사용자 (브라우저)              │
└──────────────┬──────────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼──────────────────────────┐
│         Grafana Server                  │
│  ┌──────────────────────────────────┐   │
│  │      대시보드 관리               │   │
│  ├──────────────────────────────────┤   │
│  │      쿼리 프로세서               │   │
│  ├──────────────────────────────────┤   │
│  │      알림 엔진                   │   │
│  ├──────────────────────────────────┤   │
│  │      사용자 관리                 │   │
│  └──────────────────────────────────┘   │
└─────┬────────┬────────┬────────┬─────────┘
      │        │        │        │
┌─────▼──┐ ┌──▼────┐ ┌─▼─────┐ ┌▼────────┐
│Promethe│ │InfluxDB│ │MySQL │ │CloudWatch│
│us      │ │        │ │      │ │         │
└────────┘ └────────┘ └──────┘ └─────────┘
```

### 주요 구성 요소

**1. 데이터 소스 (Data Source)**
```
역할: 메트릭 데이터를 제공하는 백엔드

종류:
- 시계열 DB: Prometheus, InfluxDB, Graphite
- 로그: Loki, Elasticsearch
- RDBMS: PostgreSQL, MySQL
- NoSQL: ClickHouse, MongoDB
- 클라우드: CloudWatch, Azure Monitor

설정:
- 연결 정보 (URL, 인증)
- 기본 쿼리 타임아웃
- 캐시 설정
```

**2. 대시보드 (Dashboard)**
```
역할: 여러 패널을 포함하는 시각화 컨테이너

구성:
- 메타데이터 (이름, 태그, 설명)
- 패널 배열 (Grid Layout)
- 변수 (Variables)
- 시간 범위 (Time Range)
- 자동 새로고침 설정

특징:
- JSON 형식으로 저장
- 버전 관리 가능
- 폴더로 구조화
- 권한 관리
```

**3. 패널 (Panel)**
```
역할: 개별 시각화 요소

종류:
- Time Series (선 그래프)
- Bar Chart (막대 그래프)
- Stat (단일 값)
- Gauge (게이지)
- Table (테이블)
- Heatmap (히트맵)
- Pie Chart (파이 차트)

설정:
- 쿼리 (Query)
- 변환 (Transform)
- 표시 옵션 (Display)
- 임계값 (Threshold)
```

**4. 쿼리 (Query)**
```
역할: 데이터 소스에서 데이터를 가져오는 표현식

Prometheus 예시:
rate(http_requests_total[5m])

InfluxQL 예시:
SELECT mean("value") FROM "cpu" WHERE time > now() - 1h

SQL 예시:
SELECT time, AVG(response_time) 
FROM metrics 
WHERE time > NOW() - INTERVAL 1 HOUR
GROUP BY time
```

**5. 변수 (Variables)**
```
역할: 대시보드를 동적으로 만드는 매개변수

종류:
- Query: 데이터 소스에서 값 가져오기
- Custom: 수동으로 값 지정
- Constant: 고정 값
- Interval: 시간 간격
- Data source: 데이터 소스 선택
- Text box: 사용자 입력

예시:
$environment = {prod, staging, dev}
$server = {server1, server2, server3}

쿼리에서 사용:
rate(http_requests_total{env="$environment", instance="$server"}[5m])
```

---

## 데이터 소스 연동

### Prometheus 연동

**설정 방법:**

```yaml
# Grafana 데이터 소스 설정
# /etc/grafana/provisioning/datasources/prometheus.yaml

apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      httpMethod: POST
      timeInterval: 30s
```

**웹 UI에서 추가:**
```
1. Configuration → Data Sources → Add data source
2. Prometheus 선택
3. URL 입력: http://localhost:9090
4. Access: Server (기본)
5. Save & Test
```

**기본 쿼리 예시:**

```promql
# CPU 사용률
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 메모리 사용률
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# HTTP 요청률
rate(http_requests_total[5m])

# HTTP 응답 시간 (P95)
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# 에러율
rate(http_requests_total{status=~"5.."}[5m]) / 
rate(http_requests_total[5m]) * 100
```

### InfluxDB 연동

```yaml
# /etc/grafana/provisioning/datasources/influxdb.yaml

apiVersion: 1

datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://influxdb:8086
    database: mydb
    user: admin
    secureJsonData:
      password: password
    jsonData:
      httpMode: POST
      timeInterval: 10s
```

**InfluxQL 쿼리 예시:**

```sql
-- CPU 사용률
SELECT mean("usage_idle") FROM "cpu" 
WHERE time > now() - 1h 
GROUP BY time(1m), "host"

-- 디스크 I/O
SELECT derivative(mean("read_bytes"), 1s) FROM "diskio" 
WHERE time > now() - 1h 
GROUP BY time(10s), "name"

-- 네트워크 트래픽
SELECT non_negative_derivative(mean("bytes_recv"), 1s) * 8 / 1000000 AS "mbps" 
FROM "net" 
WHERE time > now() - 1h 
GROUP BY time(10s), "interface"
```

### MySQL/PostgreSQL 연동

```yaml
# /etc/grafana/provisioning/datasources/mysql.yaml

apiVersion: 1

datasources:
  - name: MySQL
    type: mysql
    url: mysql-host:3306
    database: mydb
    user: grafana
    secureJsonData:
      password: password
    jsonData:
      maxOpenConns: 100
      maxIdleConns: 100
      connMaxLifetime: 14400
```

**SQL 쿼리 예시:**

```sql
-- 시계열 데이터
SELECT
  UNIX_TIMESTAMP(timestamp) as time_sec,
  value as value,
  metric as metric
FROM metrics
WHERE $__timeFilter(timestamp)
ORDER BY timestamp ASC

-- 집계 쿼리
SELECT
  $__timeGroup(timestamp, '5m') as time,
  AVG(response_time) as avg_response_time
FROM api_metrics
WHERE $__timeFilter(timestamp)
GROUP BY 1
ORDER BY 1

-- 상태 카운트
SELECT
  status,
  COUNT(*) as count
FROM orders
WHERE $__timeFilter(created_at)
GROUP BY status
```

### ClickHouse 연동

```yaml
# /etc/grafana/provisioning/datasources/clickhouse.yaml

apiVersion: 1

datasources:
  - name: ClickHouse
    type: vertamedia-clickhouse-datasource
    url: http://clickhouse:8123
    access: proxy
    isDefault: false
    jsonData:
      defaultDatabase: default
      timeout: 10
```

**ClickHouse 쿼리 예시:**

```sql
-- 시계열 집계
SELECT
  toStartOfInterval(timestamp, INTERVAL 5 MINUTE) as time,
  COUNT() as requests,
  AVG(duration) as avg_duration
FROM web_logs
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time

-- 상위 N 쿼리
SELECT
  url,
  COUNT() as visits,
  uniq(user_id) as unique_users
FROM web_logs
WHERE $__timeFilter(timestamp)
GROUP BY url
ORDER BY visits DESC
LIMIT 10

-- 히트맵 데이터
SELECT
  toStartOfInterval(timestamp, INTERVAL 1 MINUTE) as time,
  toInt32(duration / 100) * 100 as duration_bucket,
  COUNT() as count
FROM api_logs
WHERE $__timeFilter(timestamp)
GROUP BY time, duration_bucket
ORDER BY time
```

---

## 대시보드 구축

### 대시보드 구조 설계

**계층적 구조:**

```
조직 (Organization)
  └─ 폴더 (Folders)
      ├─ Infrastructure
      │   ├─ System Overview
      │   ├─ CPU & Memory
      │   └─ Network & Disk
      │
      ├─ Application
      │   ├─ API Performance
      │   ├─ Database Metrics
      │   └─ Error Tracking
      │
      └─ Business
          ├─ User Analytics
          ├─ Revenue Metrics
          └─ Conversion Funnel
```

**대시보드 생성:**

```json
{
  "dashboard": {
    "title": "System Overview",
    "tags": ["infrastructure", "monitoring"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "variables": [
      {
        "name": "environment",
        "type": "query",
        "datasource": "Prometheus",
        "query": "label_values(up, environment)",
        "multi": true,
        "includeAll": true
      }
    ]
  }
}
```

### 변수 활용

**1. Query 변수 (가장 많이 사용)**

```
설정:
- Name: server
- Type: Query
- Data source: Prometheus
- Query: label_values(up, instance)
- Multi-value: Yes
- Include All: Yes

사용:
rate(cpu_usage{instance=~"$server"}[5m])
```

**2. Custom 변수**

```
설정:
- Name: environment
- Type: Custom
- Values: production,staging,development
- Multi-value: Yes

사용:
rate(http_requests_total{env="$environment"}[5m])
```

**3. Interval 변수**

```
설정:
- Name: interval
- Type: Interval
- Values: 1m,5m,10m,30m,1h

사용:
rate(http_requests_total[$interval])
```

**4. 변수 체이닝**

```
Region 변수:
label_values(up, region)

Server 변수 (Region에 의존):
label_values(up{region="$region"}, instance)

사용:
rate(cpu_usage{region="$region", instance="$server"}[5m])
```

### 레이아웃 설계

**그리드 시스템:**

```
24 컬럼 그리드
├─ Row 1: 제목 및 요약 (24 컬럼)
│   └─ Panel: Stat (6x3 각각)
│       ├─ Total Requests
│       ├─ Error Rate
│       ├─ Avg Response Time
│       └─ Active Users
│
├─ Row 2: 주요 메트릭 (24 컬럼)
│   ├─ Panel: Time Series (12x8)
│   │   └─ HTTP Requests Rate
│   └─ Panel: Time Series (12x8)
│       └─ Response Time P95
│
└─ Row 3: 상세 분석 (24 컬럼)
    ├─ Panel: Table (12x8)
    │   └─ Top Endpoints
    └─ Panel: Heatmap (12x8)
        └─ Response Time Distribution
```

**반응형 디자인:**

```javascript
// 패널 크기 자동 조정
{
  "gridPos": {
    "h": 8,      // 높이
    "w": 12,     // 너비 (24 중 12)
    "x": 0,      // X 위치
    "y": 0       // Y 위치
  }
}
```

---

## 패널과 시각화

### Time Series (시계열 그래프)

**용도:**
- 시간에 따른 메트릭 변화
- 여러 시리즈 비교
- 트렌드 분석

**설정 예시:**

```json
{
  "type": "timeseries",
  "title": "HTTP Request Rate",
  "targets": [
    {
      "expr": "rate(http_requests_total[5m])",
      "legendFormat": "{{method}} {{status}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "color": {
        "mode": "palette-classic"
      },
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 10,
        "gradientMode": "none",
        "showPoints": "never"
      },
      "unit": "reqps"
    }
  }
}
```

**고급 옵션:**

```
표시 옵션:
- Line width: 선 두께
- Fill opacity: 영역 채우기
- Point size: 데이터 포인트 크기
- Stacking: 스택 차트
- Gradient: 그라데이션

축 옵션:
- Scale: Linear, Log, Symlog
- Soft min/max: 자동 범위
- Unit: 단위 (reqps, ms, bytes)

범례:
- Position: Bottom, Right, Hidden
- Mode: List, Table
- Values: Min, Max, Avg, Current
```

### Stat (통계 패널)

**용도:**
- 단일 값 표시
- KPI 대시보드
- 임계값 경고

**예시:**

```json
{
  "type": "stat",
  "title": "Error Rate",
  "targets": [
    {
      "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percent",
      "decimals": 2,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"value": 0, "color": "green"},
          {"value": 1, "color": "yellow"},
          {"value": 5, "color": "red"}
        ]
      }
    }
  },
  "options": {
    "graphMode": "area",
    "colorMode": "background",
    "textMode": "value_and_name",
    "orientation": "horizontal"
  }
}
```

### Table (테이블)

**용도:**
- 상세 데이터 표시
- 여러 메트릭 비교
- Top N 조회

**예시:**

```json
{
  "type": "table",
  "title": "Top Endpoints by Request Count",
  "targets": [
    {
      "expr": "topk(10, sum by(path) (rate(http_requests_total[5m])))",
      "format": "table",
      "instant": true
    }
  ],
  "fieldConfig": {
    "overrides": [
      {
        "matcher": {"id": "byName", "options": "Value"},
        "properties": [
          {"id": "displayName", "value": "Requests/sec"},
          {"id": "unit", "value": "reqps"},
          {"id": "decimals", "value": 2}
        ]
      }
    ]
  },
  "options": {
    "showHeader": true,
    "sortBy": [
      {"displayName": "Requests/sec", "desc": true}
    ]
  }
}
```

### Gauge (게이지)

**용도:**
- 백분율 표시
- 용량 모니터링
- 임계값 시각화

**예시:**

```json
{
  "type": "gauge",
  "title": "CPU Usage",
  "targets": [
    {
      "expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percent",
      "min": 0,
      "max": 100,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"value": 0, "color": "green"},
          {"value": 70, "color": "yellow"},
          {"value": 90, "color": "red"}
        ]
      }
    }
  },
  "options": {
    "showThresholdLabels": true,
    "showThresholdMarkers": true
  }
}
```

### Heatmap (히트맵)

**용도:**
- 분포 시각화
- 레이턴시 분석
- 패턴 발견

**예시:**

```json
{
  "type": "heatmap",
  "title": "Response Time Distribution",
  "targets": [
    {
      "expr": "sum(increase(http_request_duration_seconds_bucket[5m])) by (le)",
      "format": "heatmap",
      "legendFormat": "{{le}}"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "custom": {
        "hideFrom": {
          "tooltip": false,
          "viz": false,
          "legend": false
        }
      }
    }
  },
  "options": {
    "calculate": true,
    "cellGap": 2,
    "color": {
      "exponent": 0.5,
      "scheme": "Spectral",
      "steps": 128
    },
    "yAxis": {
      "unit": "s",
      "decimals": 2
    }
  }
}
```

---

## 쿼리와 변환

### 쿼리 빌더

**Prometheus 쿼리 예시:**

```promql
# 기본 메트릭
up

# 레이블 필터
up{job="api", instance=~"prod-.*"}

# 시간 범위
rate(http_requests_total[5m])

# 집계
sum(rate(http_requests_total[5m])) by (method, status)

# 수식
rate(http_requests_total{status=~"5.."}[5m]) / 
rate(http_requests_total[5m]) * 100

# 함수
- avg_over_time()
- max_over_time()
- min_over_time()
- quantile()
- histogram_quantile()
```

### 데이터 변환 (Transformations)

**1. Group by**

```
용도: 시리즈를 그룹화하여 집계

예시:
Before:
server1: 10
server2: 20
server3: 15

After (Group by region):
us-east: 30
us-west: 15
```

**2. Merge**

```
용도: 여러 쿼리 결과를 하나로 병합

설정:
- Transformation: Merge
- Mode: Outer join

결과: 시간축 기준으로 모든 시리즈 병합
```

**3. Filter by value**

```
용도: 조건에 맞는 값만 표시

설정:
- Transformation: Filter data by values
- Conditions:
  - Field: cpu_usage
  - Match: Greater than
  - Value: 80

결과: CPU 사용률 80% 이상만 표시
```

**4. Add field from calculation**

```
용도: 계산된 필드 추가

예시:
원본: requests, errors
계산: error_rate = (errors / requests) * 100

설정:
- Transformation: Add field from calculation
- Mode: Binary operation
- Operation: errors / requests * 100
- Alias: error_rate
```

**5. Organize fields**

```
용도: 컬럼 순서 변경, 숨기기, 이름 변경

설정:
- Hide: instance, job
- Rename: Value → Request Rate
- Reorder: 시간, 메서드, Request Rate
```

---

## 알림 설정

### 알림 규칙 생성

**Contact Point 설정:**

```yaml
# /etc/grafana/provisioning/alerting/contactpoints.yaml

apiVersion: 1

contactPoints:
  - orgId: 1
    name: slack-alerts
    receivers:
      - uid: slack-webhook
        type: slack
        settings:
          url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
          text: |
            🚨 Alert: {{ .Labels.alertname }}
            Status: {{ .Status }}
            {{ range .Annotations.SortedPairs }}
            {{ .Name }}: {{ .Value }}
            {{ end }}
          title: Grafana Alert

  - orgId: 1
    name: email-alerts
    receivers:
      - uid: email-oncall
        type: email
        settings:
          addresses: oncall@company.com
          subject: "[{{ .Status | toUpper }}] {{ .Labels.alertname }}"
```

**알림 규칙 예시:**

```yaml
# /etc/grafana/provisioning/alerting/rules.yaml

apiVersion: 1

groups:
  - orgId: 1
    name: infrastructure-alerts
    folder: Infrastructure
    interval: 1m
    rules:
      - uid: high-cpu-alert
        title: High CPU Usage
        condition: B
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
              interval: ""
              refId: A
          - refId: B
            datasourceUid: __expr__
            model:
              expression: $A
              reducer: last
              conditions:
                - evaluator:
                    params: [80]
                    type: gt
                  operator:
                    type: and
                  query:
                    params: [B]
                  type: query
        noDataState: NoData
        execErrState: Error
        for: 5m
        annotations:
          description: "CPU usage is {{ $value }}% on instance {{ $labels.instance }}"
          summary: High CPU usage detected
        labels:
          severity: warning
        isPaused: false
```

**알림 라우팅:**

```yaml
# /etc/grafana/provisioning/alerting/policies.yaml

apiVersion: 1

policies:
  - orgId: 1
    receiver: default-receiver
    routes:
      - receiver: slack-critical
        matchers:
          - severity = critical
        continue: true
        
      - receiver: slack-warning
        matchers:
          - severity = warning
        group_by: ['alertname', 'instance']
        group_wait: 10s
        group_interval: 5m
        repeat_interval: 4h
        
      - receiver: email-oncall
        matchers:
          - severity = critical
          - team = backend
        group_by: ['alertname']
        group_wait: 30s
```

### 알림 템플릿

**Slack 템플릿:**

```
{{ define "slack.title" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "slack.text" }}
{{ range .Alerts }}
*Alert:* {{ .Labels.alertname }}
*Severity:* {{ .Labels.severity }}
*Instance:* {{ .Labels.instance }}
*Description:* {{ .Annotations.description }}
*Value:* {{ .Values.B }}
{{ end }}
{{ end }}
```

**이메일 템플릿:**

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .alert { padding: 10px; margin: 10px 0; }
        .critical { background-color: #f44336; color: white; }
        .warning { background-color: #ff9800; color: white; }
    </style>
</head>
<body>
    <h2>Grafana Alert Notification</h2>
    {{ range .Alerts }}
    <div class="alert {{ .Labels.severity }}">
        <h3>{{ .Labels.alertname }}</h3>
        <p><strong>Status:</strong> {{ .Status }}</p>
        <p><strong>Instance:</strong> {{ .Labels.instance }}</p>
        <p><strong>Description:</strong> {{ .Annotations.description }}</p>
        <p><strong>Value:</strong> {{ .Values.B }}</p>
        <p><strong>Started at:</strong> {{ .StartsAt }}</p>
    </div>
    {{ end }}
</body>
</html>
```

---

## 실무 활용 사례

### 1. 인프라 모니터링 대시보드

**System Overview Dashboard:**

```json
{
  "dashboard": {
    "title": "Infrastructure Overview",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "timeseries",
        "targets": [{
          "expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
        }]
      },
      {
        "title": "Memory Usage",
        "type": "timeseries",
        "targets": [{
          "expr": "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))"
        }]
      },
      {
        "title": "Disk I/O",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(node_disk_read_bytes_total[5m]) + rate(node_disk_written_bytes_total[5m])"
        }]
      },
      {
        "title": "Network Traffic",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(node_network_receive_bytes_total[5m]) * 8 / 1000000",
          "legendFormat": "Receive"
        }, {
          "expr": "rate(node_network_transmit_bytes_total[5m]) * 8 / 1000000",
          "legendFormat": "Transmit"
        }]
      }
    ]
  }
}
```

### 2. 애플리케이션 성능 모니터링 (APM)

**API Performance Dashboard:**

```json
{
  "dashboard": {
    "title": "API Performance",
    "variables": [
      {
        "name": "endpoint",
        "type": "query",
        "query": "label_values(http_request_duration_seconds_count, path)"
      }
    ],
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [{
          "expr": "sum(rate(http_requests_total{path=\"$endpoint\"}[5m]))"
        }]
      },
      {
        "title": "Response Time (P95)",
        "type": "gauge",
        "targets": [{
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{path=\"$endpoint\"}[5m])) by (le))"
        }],
        "thresholds": [
          {"value": 0, "color": "green"},
          {"value": 0.5, "color": "yellow"},
          {"value": 1, "color": "red"}
        ]
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(http_requests_total{path=\"$endpoint\",status=~\"5..\"}[5m]) / rate(http_requests_total{path=\"$endpoint\"}[5m]) * 100"
        }]
      },
      {
        "title": "Status Code Distribution",
        "type": "piechart",
        "targets": [{
          "expr": "sum by(status) (rate(http_requests_total{path=\"$endpoint\"}[5m]))"
        }]
      }
    ]
  }
}
```

### 3. 데이터베이스 모니터링

**Database Performance Dashboard:**

```json
{
  "dashboard": {
    "title": "Database Monitoring",
    "panels": [
      {
        "title": "Query Performance",
        "type": "timeseries",
        "targets": [{
          "datasource": "MySQL",
          "rawSql": "SELECT timestamp, AVG(query_time) as avg_time FROM slow_log WHERE $__timeFilter(timestamp) GROUP BY timestamp"
        }]
      },
      {
        "title": "Connection Pool",
        "type": "stat",
        "targets": [{
          "expr": "mysql_global_status_threads_connected"
        }],
        "fieldConfig": {
          "max": 100,
          "thresholds": [
            {"value": 0, "color": "green"},
            {"value": 70, "color": "yellow"},
            {"value": 90, "color": "red"}
          ]
        }
      },
      {
        "title": "Slow Queries",
        "type": "table",
        "targets": [{
          "datasource": "MySQL",
          "rawSql": "SELECT query_time, sql_text, rows_examined FROM slow_log WHERE $__timeFilter(start_time) ORDER BY query_time DESC LIMIT 10"
        }]
      }
    ]
  }
}
```

### 4. 비즈니스 메트릭 대시보드

**Business KPI Dashboard:**

```json
{
  "dashboard": {
    "title": "Business Metrics",
    "panels": [
      {
        "title": "Daily Revenue",
        "type": "timeseries",
        "targets": [{
          "datasource": "ClickHouse",
          "rawSql": "SELECT toStartOfDay(timestamp) as time, SUM(amount) as revenue FROM orders WHERE $__timeFilter(timestamp) GROUP BY time ORDER BY time"
        }]
      },
      {
        "title": "Active Users",
        "type": "stat",
        "targets": [{
          "datasource": "ClickHouse",
          "rawSql": "SELECT uniq(user_id) FROM events WHERE $__timeFilter(timestamp) AND event_type = 'active'"
        }]
      },
      {
        "title": "Conversion Funnel",
        "type": "bargauge",
        "targets": [{
          "datasource": "ClickHouse",
          "rawSql": "SELECT stage, COUNT(DISTINCT user_id) as users FROM funnel WHERE $__timeFilter(timestamp) GROUP BY stage ORDER BY stage"
        }]
      },
      {
        "title": "Top Products",
        "type": "table",
        "targets": [{
          "datasource": "ClickHouse",
          "rawSql": "SELECT product_name, SUM(quantity) as sold, SUM(amount) as revenue FROM order_items WHERE $__timeFilter(timestamp) GROUP BY product_name ORDER BY revenue DESC LIMIT 10"
        }]
      }
    ]
  }
}
```

---

## 최적화 및 베스트 프랙티스

### 성능 최적화

**1. 쿼리 최적화**

```promql
# ❌ 비효율적
sum(rate(metric[5m])) * 100

# ✅ 효율적 (집계 먼저)
sum(rate(metric[5m]) * 100)

# ❌ 비효율적 (많은 시계열)
rate(metric{label=~".*"}[5m])

# ✅ 효율적 (필터링 먼저)
rate(metric{label="specific-value"}[5m])
```

**2. 데이터 소스 캐싱**

```yaml
# datasource 설정
jsonData:
  timeInterval: 30s  # 최소 스크래핑 간격
  queryTimeout: 60s  # 쿼리 타임아웃
  httpMethod: POST   # POST 사용 (긴 쿼리)
```

**3. 대시보드 최적화**

```
권장사항:
- 패널 수: 20개 이하
- 쿼리 수: 패널당 3개 이하
- 시간 범위: 기본 6시간
- 새로고침: 30초 이상
- 변수: 5개 이하
```

### 보안 설정

**1. 인증 설정**

```ini
# /etc/grafana/grafana.ini

[auth]
disable_login_form = false
disable_signout_menu = false

[auth.anonymous]
enabled = false

[auth.basic]
enabled = true

[auth.ldap]
enabled = true
config_file = /etc/grafana/ldap.toml
```

**2. 권한 관리**

```
조직 (Organization):
├─ Admin: 모든 권한
├─ Editor: 대시보드 편집
└─ Viewer: 읽기 전용

폴더 권한:
├─ Infrastructure (Admin only)
├─ Application (Team A: Editor)
└─ Business (Team B: Viewer)
```

**3. API 토큰 관리**

```bash
# API 토큰 생성
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"monitoring-script", "role": "Viewer"}' \
  http://admin:password@localhost:3000/api/auth/keys

# API 사용
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:3000/api/dashboards/uid/abc123
```

### 대시보드 버전 관리

**1. JSON 내보내기**

```bash
# 대시보드 내보내기
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:3000/api/dashboards/uid/abc123 \
  | jq '.dashboard' > dashboard.json

# Git에 커밋
git add dashboard.json
git commit -m "Update system overview dashboard"
git push
```

**2. Provisioning 사용**

```yaml
# /etc/grafana/provisioning/dashboards/default.yaml

apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

**3. Terraform 관리**

```hcl
resource "grafana_dashboard" "system_overview" {
  config_json = file("${path.module}/dashboards/system-overview.json")
  folder      = grafana_folder.infrastructure.id
  
  lifecycle {
    ignore_changes = [
      config_json  # UI에서 변경 허용
    ]
  }
}
```

### 알림 베스트 프랙티스

**1. 알림 피로도 방지**

```
원칙:
- Actionable: 조치 가능한 알림만
- Meaningful: 의미있는 임계값
- Grouped: 관련 알림 그룹화
- Suppressed: 유지보수 중 알림 억제

예시:
❌ CPU > 50% (너무 자주 발생)
✅ CPU > 90% for 5 minutes (실제 문제)
```

**2. 알림 계층화**

```
Severity 레벨:
├─ Critical (즉시 대응)
│   └─ Page: 24/7 on-call
│
├─ Warning (업무 시간 내 대응)
│   └─ Slack: 팀 채널
│
└─ Info (참고용)
    └─ 로그 기록
```

**3. 알림 문서화**

```yaml
annotations:
  description: |
    CPU usage is {{ $value }}% on {{ $labels.instance }}.
    
    Possible causes:
    - High traffic
    - Memory leak
    - Inefficient query
    
    Actions:
    1. Check application logs
    2. Review recent deployments
    3. Scale horizontally if needed
    
    Runbook: https://wiki.company.com/runbooks/high-cpu
```

---

## 참고 자료

- **공식 문서**: https://grafana.com/docs/grafana/latest/
- **GitHub**: https://github.com/grafana/grafana
- **대시보드 라이브러리**: https://grafana.com/grafana/dashboards/

---


