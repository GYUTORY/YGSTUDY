---
title: Prometheus 메트릭 수집 가이드
tags: [prometheus, metrics, monitoring, nodejs, prom-client, grafana, alerting]
updated: 2025-11-15
---

# Prometheus 메트릭 수집 가이드

## 배경

### Prometheus 메트릭 수집이란?
Prometheus는 오픈소스 모니터링 및 알림 시스템으로, 메트릭 데이터를 수집, 저장, 쿼리하는 기능을 제공합니다. Node.js 애플리케이션에서 prom-client 라이브러리를 사용하여 커스텀 메트릭을 정의하고 수집할 수 있습니다.

### Prometheus 메트릭 수집의 필요성
- **성능 모니터링**: 애플리케이션 성능 지표 실시간 추적
- **리소스 모니터링**: CPU, 메모리, 디스크 사용량 추적
- **비즈니스 메트릭**: 비즈니스 로직에 특화된 메트릭 수집
- **알림 시스템**: 임계값 기반 자동 알림
- **시각화**: Grafana를 통한 메트릭 시각화

### 기본 개념

#### 1. Prometheus 아키텍처

Prometheus는 Pull 기반의 모니터링 시스템으로, 다음과 같은 구조로 동작합니다:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Prometheus 아키텍처                          │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   애플리케이션  │
    │  (Node.js)    │
    │               │
    │ ┌───────────┐ │
    │ │ prom-client│ │  ← 메트릭 생성 및 저장
    │ └───────────┘ │
    │       ↓       │
    │ /metrics 엔드포인트
    └───────┬───────┘
            │
            │ Pull (HTTP GET)
            │ 주기적으로 수집
            ↓
    ┌───────────────┐
    │  Prometheus   │
    │    Server     │  ← 메트릭 수집 및 저장
    │               │
    │  - Time Series│     (시계열 데이터베이스)
    │  - Query      │
    │  - Alert      │
    └───────┬───────┘
            │
            ├─────────────┐
            │             │
            ↓             ↓
    ┌──────────┐   ┌─────────────┐
    │ Grafana  │   │ AlertManager│
    │(시각화)   │   │  (알림)      │
    └──────────┘   └─────────────┘
```

**주요 특징:**
- **Pull 방식**: Prometheus가 주기적으로 애플리케이션의 `/metrics` 엔드포인트를 요청
- **시계열 데이터**: 타임스탬프와 함께 메트릭 저장
- **레이블 기반**: 다차원 데이터 모델로 유연한 쿼리 가능

#### 2. 메트릭 타입 상세 설명

Prometheus는 4가지 주요 메트릭 타입을 제공합니다:

##### **Counter (카운터)**

```
개념: 누적 값만 증가하는 메트릭 (재시작 시 0으로 리셋)

시간 흐름 →
값  ↑
    │           ┌──────────
    │         ┌─┘
    │       ┌─┘
    │     ┌─┘
    │   ┌─┘
    │ ┌─┘
    └─────────────────────→ 시간

예시:
- http_requests_total: 총 HTTP 요청 수
- errors_total: 총 에러 발생 횟수
- user_registrations_total: 총 사용자 등록 수

특징:
✓ 항상 증가 (감소하지 않음)
✓ rate() 함수로 증가율 계산
✓ 비율이나 속도 측정에 적합
```

**사용 사례:**
```javascript
// 요청 수 카운트
httpRequestsTotal.inc();           // 1 증가
httpRequestsTotal.inc(5);          // 5 증가

// 레이블과 함께 사용
httpRequestsTotal.labels('GET', '/api/users', '200').inc();
```

##### **Gauge (게이지)**

```
개념: 임의로 증가/감소 가능한 현재 상태 값

시간 흐름 →
값  ↑
    │     ┌─┐
    │   ┌─┘ └─┐    ┌─┐
    │ ┌─┘     └─┐┌─┘ └─┐
    │─┘         └┘     └─
    └─────────────────────→ 시간

예시:
- memory_usage_bytes: 현재 메모리 사용량
- active_connections: 현재 활성 연결 수
- queue_size: 현재 큐 크기
- temperature: 현재 온도

특징:
✓ 증가/감소 가능
✓ 현재 상태를 나타냄
✓ 스냅샷 데이터
```

**사용 사례:**
```javascript
// 값 설정
memoryUsage.set(1024 * 1024 * 100);  // 100MB

// 증가/감소
activeConnections.inc();   // 연결 추가
activeConnections.dec();   // 연결 제거

// 레이블과 함께 사용
queueSize.labels('high-priority').set(42);
```

##### **Histogram (히스토그램)**

```
개념: 값의 분포를 버킷으로 나누어 측정 (응답 시간, 크기 등)

분포 시각화:
요청수 ↑
      │  ┌──┐
      │  │  │
      │  │  │ ┌──┐
      │  │  │ │  │ ┌──┐
      │  │  │ │  │ │  │ ┌──┐
      │  │  │ │  │ │  │ │  │    ┌──┐
      └──┴──┴─┴──┴─┴──┴─┴──┴────┴──┴──→
        0.1 0.5 1  2  5  10 30 60  ∞   (seconds)
        └── 버킷 (buckets) ──┘

생성되는 메트릭:
- http_request_duration_seconds_bucket{le="0.1"} 250
- http_request_duration_seconds_bucket{le="0.5"} 480
- http_request_duration_seconds_bucket{le="1.0"} 520
- http_request_duration_seconds_sum 2450.5
- http_request_duration_seconds_count 530

예시:
- http_request_duration_seconds: HTTP 요청 응답 시간
- database_query_duration_seconds: DB 쿼리 실행 시간
- file_size_bytes: 파일 크기 분포

특징:
✓ 백분위수(percentile) 계산 가능
✓ 평균 및 합계 제공
✓ 서버 측에서 집계
```

**사용 사례:**
```javascript
// 타이머 사용
const end = httpRequestDuration.startTimer();
// ... 작업 수행 ...
end({ method: 'GET', route: '/api/users', status_code: '200' });

// 직접 관찰
httpRequestDuration.observe(0.523);  // 523ms

// 버킷 설정 (초 단위)
buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
```

##### **Summary (요약)**

```
개념: 클라이언트 측에서 백분위수를 직접 계산

백분위수 계산:
- response_time_seconds{quantile="0.5"} 0.2    (중앙값)
- response_time_seconds{quantile="0.9"} 0.5    (90 percentile)
- response_time_seconds{quantile="0.99"} 1.2   (99 percentile)
- response_time_seconds_sum 2450.5
- response_time_seconds_count 530

Histogram vs Summary:

┌─────────────┬──────────────┬──────────────┐
│   특성       │  Histogram   │   Summary    │
├─────────────┼──────────────┼──────────────┤
│ 계산 위치    │  서버 측      │  클라이언트   │
│ 정확도      │  근사값       │  정확한 값    │
│ 집계 가능   │  O           │  X           │
│ 리소스 사용 │  낮음         │  높음         │
│ 유연성      │  높음         │  낮음         │
└─────────────┴──────────────┴──────────────┘

특징:
✓ 정확한 백분위수 계산
✓ 클라이언트에서 계산
✓ 집계 불가능
```

**사용 사례:**
```javascript
// Summary 생성
const responseSummary = new client.Summary({
  name: 'response_time_seconds',
  help: 'Response time in seconds',
  percentiles: [0.5, 0.9, 0.95, 0.99]
});

// 값 기록
responseSummary.observe(0.523);
```

#### 3. Label (레이블)

레이블은 메트릭에 다차원 데이터를 추가하는 키-값 쌍입니다:

```
메트릭 구조:
metric_name{label1="value1", label2="value2"} metric_value

예시:
http_requests_total{method="GET", endpoint="/api/users", status="200"} 1547
http_requests_total{method="POST", endpoint="/api/users", status="201"} 342
http_requests_total{method="GET", endpoint="/api/products", status="200"} 2891

레이블 설계 원칙:
✓ 카디널리티 제한 (너무 많은 고유값 피하기)
✓ 의미 있는 분류
✓ 일관된 네이밍
✗ 사용자 ID 같은 높은 카디널리티 값 사용 금지

좋은 예:
- method: "GET", "POST", "PUT", "DELETE" (제한된 값)
- status_code: "200", "404", "500" (제한된 값)
- region: "us-east", "eu-west" (제한된 값)

나쁜 예:
- user_id: "user_12345" (무한대에 가까운 값)
- session_id: "sess_abc123" (무한대에 가까운 값)
- timestamp: "2025-11-16T10:30:00" (무한대에 가까운 값)
```

#### 4. 메트릭 수집 흐름

```
┌─────────────────────────────────────────────────────────────┐
│              전체 메트릭 수집 프로세스                        │
└─────────────────────────────────────────────────────────────┘

1. 애플리케이션 레벨
┌────────────────────────────────────────┐
│  HTTP Request 도착                      │
│  GET /api/users                        │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│  Metrics Middleware                    │
│  - 타이머 시작                          │
│  - 요청 처리                            │
│  - 타이머 종료                          │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│  메트릭 기록                            │
│  httpRequestDuration.observe(0.234)    │
│  httpRequestsTotal.inc()               │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│  메트릭 레지스트리에 저장                │
│  (메모리 내 시계열 데이터)               │
└──────────────┬─────────────────────────┘
               ↓

2. Prometheus 레벨
┌────────────────────────────────────────┐
│  Prometheus Scrape (주기적)            │
│  GET http://app:9090/metrics           │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│  메트릭 데이터 반환 (Exposition Format) │
│  # TYPE http_requests_total counter    │
│  http_requests_total{...} 1547         │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│  Prometheus TSDB에 저장                │
│  (시계열 데이터베이스)                   │
└──────────────┬─────────────────────────┘
               ↓

3. 시각화/알림 레벨
┌────────────────┬───────────────────────┐
│    Grafana     │    AlertManager       │
│  (쿼리 & 시각화) │      (알림)           │
└────────────────┴───────────────────────┘
```

## 핵심

### 1. prom-client 라이브러리 활용

#### 기본 설치 및 설정
```javascript
// package.json
{
  "dependencies": {
    "prom-client": "^15.0.0"
  }
}

// src/metrics/prometheusClient.js
const client = require('prom-client');

class PrometheusClient {
  constructor() {
    // 메트릭 레지스트리 초기화
    this.register = new client.Registry();
    
    // 기본 메트릭 수집 (Node.js 기본 메트릭)
    client.collectDefaultMetrics({
      register: this.register,
      prefix: 'nodejs_',
      gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
      eventLoopMonitoringPrecision: 10
    });
    
    // 커스텀 메트릭 초기화
    this.initializeCustomMetrics();
  }
  
  // 커스텀 메트릭 초기화
  initializeCustomMetrics() {
    // HTTP 요청 메트릭
    this.httpRequestDuration = new client.Histogram({
      name: 'http_request_duration_seconds',
      help: 'Duration of HTTP requests in seconds',
      labelNames: ['method', 'route', 'status_code'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
    });
    
    this.httpRequestTotal = new client.Counter({
      name: 'http_requests_total',
      help: 'Total number of HTTP requests',
      labelNames: ['method', 'route', 'status_code']
    });
    
    // 데이터베이스 메트릭
    this.databaseQueryDuration = new client.Histogram({
      name: 'database_query_duration_seconds',
      help: 'Duration of database queries in seconds',
      labelNames: ['operation', 'table', 'status'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5]
    });
    
    this.databaseConnections = new client.Gauge({
      name: 'database_connections_active',
      help: 'Number of active database connections',
      labelNames: ['database', 'state']
    });
    
    // 비즈니스 메트릭
    this.userRegistrations = new client.Counter({
      name: 'user_registrations_total',
      help: 'Total number of user registrations',
      labelNames: ['source', 'status']
    });
    
    this.activeUsers = new client.Gauge({
      name: 'active_users_count',
      help: 'Number of active users',
      labelNames: ['period']
    });
    
    // 에러 메트릭
    this.errorsTotal = new client.Counter({
      name: 'errors_total',
      help: 'Total number of errors',
      labelNames: ['type', 'severity', 'component']
    });
    
    // 시스템 메트릭
    this.memoryUsage = new client.Gauge({
      name: 'nodejs_memory_usage_bytes',
      help: 'Node.js memory usage in bytes',
      labelNames: ['type']
    });
    
    this.cpuUsage = new client.Gauge({
      name: 'nodejs_cpu_usage_percent',
      help: 'Node.js CPU usage percentage'
    });
    
    // 모든 메트릭을 레지스트리에 등록
    this.register.registerMetric(this.httpRequestDuration);
    this.register.registerMetric(this.httpRequestTotal);
    this.register.registerMetric(this.databaseQueryDuration);
    this.register.registerMetric(this.databaseConnections);
    this.register.registerMetric(this.userRegistrations);
    this.register.registerMetric(this.activeUsers);
    this.register.registerMetric(this.errorsTotal);
    this.register.registerMetric(this.memoryUsage);
    this.register.registerMetric(this.cpuUsage);
  }
  
  // 메트릭 레지스트리 반환
  getRegister() {
    return this.register;
  }
  
  // 메트릭 데이터 반환
  async getMetrics() {
    return await this.register.metrics();
  }
  
  // 메트릭 초기화
  clearMetrics() {
    this.register.clear();
  }
}

module.exports = PrometheusClient;
```

#### 고급 메트릭 설정

고급 메트릭은 특정 도메인이나 비즈니스 로직에 특화된 메트릭입니다. 다음은 주요 고급 메트릭 타입과 그 개념을 설명합니다.

##### 1. 분산 추적 (Distributed Tracing) 메트릭

분산 시스템에서 요청이 여러 서비스를 거쳐가는 과정을 추적합니다:

```
┌─────────────────────────────────────────────────────────────┐
│              분산 추적 메트릭 개념                            │
└─────────────────────────────────────────────────────────────┘

클라이언트 요청
     │
     ↓
┌──────────┐    Span 1 (200ms)     ┌──────────┐
│ API      │  ─────────────────→   │ Auth     │
│ Gateway  │                       │ Service  │
└──────────┘                       └──────────┘
     │                                  
     │      Span 2 (500ms)              
     ↓                                  
┌──────────┐    Span 2.1 (150ms)  ┌──────────┐
│ User     │  ─────────────────→   │ Database │
│ Service  │                       │          │
└──────────┘                       └──────────┘
     │
     │      Span 2.2 (100ms)
     ↓
┌──────────┐
│ Cache    │
│ Service  │
└──────────┘

전체 Trace 시간: 700ms

메트릭 수집:
- distributed_trace_duration_seconds{service="api-gateway", operation="login", status="success"} 0.7
- distributed_trace_duration_seconds{service="auth-service", operation="verify", status="success"} 0.2
- distributed_trace_duration_seconds{service="user-service", operation="getUser", status="success"} 0.5

개념:
- Trace: 전체 요청 흐름
- Span: 각 서비스에서의 작업 단위
- Operation: 수행하는 작업 유형
```

##### 2. 큐 (Queue) 메트릭

메시지 큐나 작업 큐의 상태와 처리 성능을 추적합니다:

```
┌─────────────────────────────────────────────────────────────┐
│                   큐 메트릭 개념                              │
└─────────────────────────────────────────────────────────────┘

                     큐 구조
┌────────────────────────────────────────────────┐
│  Priority Queue                                │
│                                                │
│  High Priority (10 items)                     │
│  ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐    │
│  │ 1 ││ 2 ││ 3 ││ 4 ││ 5 ││ 6 ││ 7 ││ 8 │... │
│  └───┘└───┘└───┘└───┘└───┘└───┘└───┘└───┘    │
│                                                │
│  Medium Priority (25 items)                   │
│  ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐    │
│  │ 1 ││ 2 ││ 3 ││ 4 ││ 5 ││ 6 ││ 7 ││ 8 │... │
│  └───┘└───┘└───┘└───┘└───┘└───┘└───┘└───┘    │
│                                                │
│  Low Priority (50 items)                      │
│  ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐    │
│  │ 1 ││ 2 ││ 3 ││ 4 ││ 5 ││ 6 ││ 7 ││ 8 │... │
│  └───┘└───┘└───┘└───┘└───┘└───┘└───┘└───┘    │
└────────────────────────────────────────────────┘
         ↓
    Consumer 처리
         ↓
    메트릭 수집

수집되는 메트릭:
- queue_size{queue_name="email", priority="high"} 10
- queue_size{queue_name="email", priority="medium"} 25
- queue_size{queue_name="email", priority="low"} 50

- queue_processing_duration_seconds{queue_name="email", job_type="welcome", status="success"}

모니터링 포인트:
✓ 큐 크기 증가 추세 → 처리 지연 감지
✓ 처리 시간 증가 → 성능 문제 감지
✓ 실패율 증가 → 시스템 문제 감지
```

##### 3. 캐시 (Cache) 메트릭

캐시 효율성과 성능을 추적합니다:

```
┌─────────────────────────────────────────────────────────────┐
│                   캐시 메트릭 개념                            │
└─────────────────────────────────────────────────────────────┘

캐시 동작 흐름:

요청 → 캐시 확인
        │
        ├─ Hit (캐시에 있음) ────→ 빠른 응답 (10ms)
        │   cache_hits_total++
        │
        └─ Miss (캐시에 없음) ───→ DB 조회 (100ms)
            cache_misses_total++    │
                                    ↓
                                캐시에 저장
                                    ↓
                                    응답

캐시 효율성 계산:
┌──────────────────────────────────┐
│  Hit Rate = Hits / (Hits + Miss) │
│                                  │
│  예시:                            │
│  Hits: 900                       │
│  Miss: 100                       │
│  Hit Rate = 900/1000 = 90%       │
└──────────────────────────────────┘

메트릭:
- cache_hits_total{cache_name="redis", key_pattern="user:*"} 900
- cache_misses_total{cache_name="redis", key_pattern="user:*"} 100
- cache_size_bytes{cache_name="redis"} 52428800  (50MB)

성능 영향:
┌──────────┬──────────┬────────────┐
│ Hit Rate │ Avg Time │   영향     │
├──────────┼──────────┼────────────┤
│   90%    │   19ms   │  우수      │
│   70%    │   37ms   │  양호      │
│   50%    │   55ms   │  개선필요   │
│   30%    │   73ms   │  문제      │
└──────────┴──────────┴────────────┘
```

##### 4. 외부 API 메트릭

외부 서비스 호출 성능과 안정성을 추적합니다:

```
┌─────────────────────────────────────────────────────────────┐
│              외부 API 메트릭 개념                             │
└─────────────────────────────────────────────────────────────┘

애플리케이션
     │
     │ API 호출
     ↓
┌─────────────────────────┐
│  외부 API 서비스         │
│  (예: Payment Gateway)   │
│                         │
│  - 응답 시간 측정        │
│  - Rate Limit 추적      │
│  - 에러율 모니터링       │
└─────────────────────────┘

Rate Limiting 시각화:
┌──────────────────────────────────────┐
│ Rate Limit: 1000 requests/hour       │
│                                      │
│ Used:  ████████████░░░░░░░░  (600)  │
│ Left:  400 requests                  │
│                                      │
│ Resets in: 25 minutes                │
└──────────────────────────────────────┘

메트릭:
- external_api_duration_seconds{service="stripe", endpoint="/charges", status_code="200"}
- external_api_rate_limit_remaining{service="stripe", endpoint="/charges"} 400

알림 설정:
✓ Rate limit < 100 → 경고
✓ 응답 시간 > 5s → 경고
✓ 에러율 > 5% → 위험
```

##### 5. 비즈니스 KPI 메트릭

비즈니스 성과를 측정하는 핵심 지표입니다:

```
┌─────────────────────────────────────────────────────────────┐
│              비즈니스 KPI 메트릭 개념                         │
└─────────────────────────────────────────────────────────────┘

전환 퍼널 (Conversion Funnel):

┌─────────────────┐
│  방문자 (10000)  │  100%
└────────┬────────┘
         ↓
┌─────────────────┐
│  회원가입 (3000) │   30%  ← conversion_rate{funnel_stage="signup", segment="organic"}
└────────┬────────┘
         ↓
┌─────────────────┐
│ 장바구니 (1500)  │   15%  ← conversion_rate{funnel_stage="cart", segment="organic"}
└────────┬────────┘
         ↓
┌─────────────────┐
│  구매 (450)      │  4.5%  ← conversion_rate{funnel_stage="purchase", segment="organic"}
└─────────────────┘

매출 추적:
revenue_total{currency="USD", source="web", product="premium"} 45000
revenue_total{currency="USD", source="mobile", product="premium"} 28000
revenue_total{currency="USD", source="web", product="basic"} 12000

시계열 분석:
매출 ↑
     │                    ┌────
     │              ┌─────┘
     │        ┌─────┘
     │  ┌─────┘
     │──┘
     └─────────────────────────→ 시간
     1월  2월  3월  4월  5월

핵심 지표:
✓ 전환율 (Conversion Rate)
✓ 평균 주문 금액 (Average Order Value)
✓ 고객 생애 가치 (Customer Lifetime Value)
✓ 이탈율 (Churn Rate)
```

##### 코드 구현

```javascript
// src/metrics/advancedPrometheusClient.js
const client = require('prom-client');

class AdvancedPrometheusClient {
  constructor() {
    this.register = new client.Registry();
    
    // 고급 기본 메트릭 설정
    client.collectDefaultMetrics({
      register: this.register,
      prefix: 'app_',
      gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5, 10],
      eventLoopMonitoringPrecision: 10,
      // 커스텀 메트릭 수집기 추가
      customMetricPrefix: 'custom_'
    });
    
    this.initializeAdvancedMetrics();
  }
  
  // 고급 메트릭 초기화
  initializeAdvancedMetrics() {
    // 분산 추적 메트릭
    // - 여러 서비스 간의 요청 흐름을 추적
    // - 각 서비스별, 작업별 응답 시간 측정
    this.distributedTraceDuration = new client.Histogram({
      name: 'distributed_trace_duration_seconds',
      help: 'Duration of distributed traces in seconds',
      labelNames: ['service', 'operation', 'status'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30]
    });
    
    // 큐 메트릭
    // - 현재 큐에 쌓인 작업의 수를 측정
    // - 우선순위별로 분류
    this.queueSize = new client.Gauge({
      name: 'queue_size',
      help: 'Current size of the queue',
      labelNames: ['queue_name', 'priority']
    });
    
    // 큐 처리 시간
    // - 작업이 큐에서 처리되는 데 걸리는 시간
    // - 작업 유형별, 상태별 분류
    this.queueProcessingDuration = new client.Histogram({
      name: 'queue_processing_duration_seconds',
      help: 'Duration of queue processing in seconds',
      labelNames: ['queue_name', 'job_type', 'status'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60, 300]
    });
    
    // 캐시 히트 메트릭
    // - 캐시에서 데이터를 찾은 횟수
    this.cacheHits = new client.Counter({
      name: 'cache_hits_total',
      help: 'Total number of cache hits',
      labelNames: ['cache_name', 'key_pattern']
    });
    
    // 캐시 미스 메트릭
    // - 캐시에서 데이터를 찾지 못한 횟수
    this.cacheMisses = new client.Counter({
      name: 'cache_misses_total',
      help: 'Total number of cache misses',
      labelNames: ['cache_name', 'key_pattern']
    });
    
    // 캐시 크기
    // - 현재 캐시가 사용 중인 메모리 크기
    this.cacheSize = new client.Gauge({
      name: 'cache_size_bytes',
      help: 'Current size of the cache in bytes',
      labelNames: ['cache_name']
    });
    
    // 외부 API 호출 시간
    // - 외부 서비스 호출에 걸리는 시간 측정
    this.externalAPIDuration = new client.Histogram({
      name: 'external_api_duration_seconds',
      help: 'Duration of external API calls in seconds',
      labelNames: ['service', 'endpoint', 'status_code'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
    });
    
    // 외부 API Rate Limit
    // - 남은 API 호출 가능 횟수 추적
    this.externalAPIRate = new client.Gauge({
      name: 'external_api_rate_limit_remaining',
      help: 'Remaining rate limit for external API',
      labelNames: ['service', 'endpoint']
    });
    
    // 비즈니스 KPI: 매출
    // - 발생한 매출을 누적으로 추적
    this.revenue = new client.Counter({
      name: 'revenue_total',
      help: 'Total revenue in currency units',
      labelNames: ['currency', 'source', 'product']
    });
    
    // 비즈니스 KPI: 전환율
    // - 퍼널 단계별 전환율을 백분율로 추적
    this.conversionRate = new client.Gauge({
      name: 'conversion_rate',
      help: 'Conversion rate percentage',
      labelNames: ['funnel_stage', 'segment']
    });
    
    // 모든 메트릭을 레지스트리에 등록
    this.register.registerMetric(this.distributedTraceDuration);
    this.register.registerMetric(this.queueSize);
    this.register.registerMetric(this.queueProcessingDuration);
    this.register.registerMetric(this.cacheHits);
    this.register.registerMetric(this.cacheMisses);
    this.register.registerMetric(this.cacheSize);
    this.register.registerMetric(this.externalAPIDuration);
    this.register.registerMetric(this.externalAPIRate);
    this.register.registerMetric(this.revenue);
    this.register.registerMetric(this.conversionRate);
  }
  
  // 메트릭 레지스트리 반환
  getRegister() {
    return this.register;
  }
  
  // 메트릭 데이터 반환
  async getMetrics() {
    return await this.register.metrics();
  }
}

module.exports = AdvancedPrometheusClient;
```

### 2. 커스텀 메트릭 정의 및 수집

메트릭 수집은 애플리케이션의 다양한 계층에서 이루어집니다:

```
┌─────────────────────────────────────────────────────────────┐
│              메트릭 수집 계층 구조                            │
└─────────────────────────────────────────────────────────────┘

애플리케이션 계층
├── HTTP Layer (요청/응답)
│   └── HTTP 요청 수, 응답 시간, 상태 코드
│
├── Business Logic Layer (비즈니스 로직)
│   └── 사용자 등록, 주문, 결제
│
├── Data Access Layer (데이터 접근)
│   └── DB 쿼리 시간, 연결 수
│
├── External Services Layer (외부 서비스)
│   └── API 호출, Rate Limit
│
└── System Layer (시스템)
    └── 메모리, CPU, 이벤트 루프

각 계층별 메트릭 수집 전략:
┌────────────────┬────────────────┬──────────────────┐
│     계층        │   메트릭 타입   │    수집 방법      │
├────────────────┼────────────────┼──────────────────┤
│ HTTP           │ Histogram      │  Middleware      │
│                │ Counter        │                  │
│ Business Logic │ Counter        │  Service Call    │
│                │ Gauge          │                  │
│ Data Access    │ Histogram      │  Query Wrapper   │
│                │ Gauge          │                  │
│ External API   │ Histogram      │  Client Wrapper  │
│                │ Gauge          │                  │
│ System         │ Gauge          │  Periodic Polling│
└────────────────┴────────────────┴──────────────────┘
```

#### 메트릭 수집 서비스

메트릭 수집 서비스는 중앙화된 메트릭 관리를 제공합니다:

```
┌─────────────────────────────────────────────────────────────┐
│          메트릭 수집 서비스 아키텍처                          │
└─────────────────────────────────────────────────────────────┘

                  ┌───────────────────────┐
                  │  Application Layer    │
                  └──────────┬────────────┘
                             │
                             ↓
        ┌────────────────────────────────────┐
        │  MetricsCollectionService          │
        │                                    │
        │  - recordHTTPRequest()             │
        │  - recordDatabaseQuery()           │
        │  - recordError()                   │
        │  - recordCustomMetric()            │
        │  - startTimer() / endTimer()       │
        └────────────┬───────────────────────┘
                     │
                     ↓
        ┌────────────────────────────────────┐
        │  PrometheusClient                  │
        │                                    │
        │  메트릭 타입:                       │
        │  - Counter                         │
        │  - Gauge                           │
        │  - Histogram                       │
        │  - Summary                         │
        └────────────┬───────────────────────┘
                     │
                     ↓
        ┌────────────────────────────────────┐
        │  Registry (메트릭 저장소)           │
        │                                    │
        │  메모리 내 시계열 데이터            │
        └────────────┬───────────────────────┘
                     │
                     ↓
        ┌────────────────────────────────────┐
        │  /metrics 엔드포인트                │
        │                                    │
        │  Prometheus가 수집                  │
        └────────────────────────────────────┘

사용 패턴:

1. 타이머 패턴 (실행 시간 측정)
   ┌─────────────────────────────┐
   │ startTimer()                │
   │   ↓                         │
   │ [작업 수행]                  │
   │   ↓                         │
   │ endTimer() → observe()      │
   └─────────────────────────────┘

2. 카운터 패턴 (이벤트 발생 횟수)
   ┌─────────────────────────────┐
   │ 이벤트 발생                  │
   │   ↓                         │
   │ counter.inc()               │
   └─────────────────────────────┘

3. 게이지 패턴 (현재 상태 값)
   ┌─────────────────────────────┐
   │ 상태 변경                    │
   │   ↓                         │
   │ gauge.set(newValue)         │
   └─────────────────────────────┘
```

#### 코드 구현

```javascript
// src/services/metricsCollectionService.js
const PrometheusClient = require('../metrics/prometheusClient');

class MetricsCollectionService {
  constructor() {
    this.prometheusClient = new PrometheusClient();
    this.metrics = new Map();
    this.timers = new Map();
  }
  
  // HTTP 요청 메트릭 수집
  recordHTTPRequest(method, route, statusCode, duration) {
    try {
      // Histogram 메트릭 기록
      this.prometheusClient.httpRequestDuration
        .labels(method, route, statusCode.toString())
        .observe(duration);
      
      // Counter 메트릭 기록
      this.prometheusClient.httpRequestTotal
        .labels(method, route, statusCode.toString())
        .inc();
      
    } catch (error) {
      console.error('Failed to record HTTP request metric:', error);
    }
  }
  
  // 데이터베이스 쿼리 메트릭 수집
  recordDatabaseQuery(operation, table, status, duration) {
    try {
      this.prometheusClient.databaseQueryDuration
        .labels(operation, table, status)
        .observe(duration);
      
    } catch (error) {
      console.error('Failed to record database query metric:', error);
    }
  }
  
  // 데이터베이스 연결 메트릭 수집
  recordDatabaseConnection(database, state, count) {
    try {
      this.prometheusClient.databaseConnections
        .labels(database, state)
        .set(count);
      
    } catch (error) {
      console.error('Failed to record database connection metric:', error);
    }
  }
  
  // 사용자 등록 메트릭 수집
  recordUserRegistration(source, status) {
    try {
      this.prometheusClient.userRegistrations
        .labels(source, status)
        .inc();
      
    } catch (error) {
      console.error('Failed to record user registration metric:', error);
    }
  }
  
  // 활성 사용자 메트릭 수집
  recordActiveUsers(period, count) {
    try {
      this.prometheusClient.activeUsers
        .labels(period)
        .set(count);
      
    } catch (error) {
      console.error('Failed to record active users metric:', error);
    }
  }
  
  // 에러 메트릭 수집
  recordError(type, severity, component) {
    try {
      this.prometheusClient.errorsTotal
        .labels(type, severity, component)
        .inc();
      
    } catch (error) {
      console.error('Failed to record error metric:', error);
    }
  }
  
  // 시스템 메트릭 수집
  recordSystemMetrics() {
    try {
      const memUsage = process.memoryUsage();
      
      // 메모리 사용량 메트릭
      this.prometheusClient.memoryUsage
        .labels('rss')
        .set(memUsage.rss);
      
      this.prometheusClient.memoryUsage
        .labels('heapTotal')
        .set(memUsage.heapTotal);
      
      this.prometheusClient.memoryUsage
        .labels('heapUsed')
        .set(memUsage.heapUsed);
      
      this.prometheusClient.memoryUsage
        .labels('external')
        .set(memUsage.external);
      
      // CPU 사용량 메트릭 (간단한 구현)
      const cpuUsage = process.cpuUsage();
      const totalCpuUsage = (cpuUsage.user + cpuUsage.system) / 1000000; // 마이크로초를 초로 변환
      
      this.prometheusClient.cpuUsage.set(totalCpuUsage);
      
    } catch (error) {
      console.error('Failed to record system metrics:', error);
    }
  }
  
  // 타이머 시작
  startTimer(name) {
    this.timers.set(name, Date.now());
  }
  
  // 타이머 종료 및 메트릭 기록
  endTimer(name, labels = {}) {
    try {
      const startTime = this.timers.get(name);
      if (!startTime) {
        console.warn(`Timer ${name} was not started`);
        return 0;
      }
      
      const duration = (Date.now() - startTime) / 1000; // 초 단위로 변환
      this.timers.delete(name);
      
      // 커스텀 타이머 메트릭 기록
      if (labels.operation && labels.table) {
        this.recordDatabaseQuery(labels.operation, labels.table, 'success', duration);
      }
      
      return duration;
    } catch (error) {
      console.error('Failed to end timer:', error);
      return 0;
    }
  }
  
  // 커스텀 메트릭 기록
  recordCustomMetric(name, value, labels = {}) {
    try {
      if (!this.metrics.has(name)) {
        // 새로운 Gauge 메트릭 생성
        const client = require('prom-client');
        const metric = new client.Gauge({
          name: name,
          help: `Custom metric: ${name}`,
          labelNames: Object.keys(labels)
        });
        
        this.prometheusClient.register.registerMetric(metric);
        this.metrics.set(name, metric);
      }
      
      const metric = this.metrics.get(name);
      metric.labels(...Object.values(labels)).set(value);
      
    } catch (error) {
      console.error('Failed to record custom metric:', error);
    }
  }
  
  // 메트릭 데이터 반환
  async getMetrics() {
    try {
      return await this.prometheusClient.getMetrics();
    } catch (error) {
      console.error('Failed to get metrics:', error);
      return '';
    }
  }
  
  // 메트릭 레지스트리 반환
  getRegister() {
    return this.prometheusClient.getRegister();
  }
}

module.exports = MetricsCollectionService;
```

#### 메트릭 수집 미들웨어

미들웨어는 HTTP 요청 생애주기에서 자동으로 메트릭을 수집합니다:

```
┌─────────────────────────────────────────────────────────────┐
│          메트릭 미들웨어 동작 흐름                            │
└─────────────────────────────────────────────────────────────┘

HTTP 요청 들어옴
     │
     ↓
┌─────────────────────────────────────┐
│  1. 메트릭 미들웨어 진입              │
│     - startTime 기록                │
│     - 요청 정보 캡처                 │
│       (method, path, headers)       │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  2. 애플리케이션 로직 실행            │
│     - Route Handler                 │
│     - Business Logic                │
│     - Database Query                │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  3. 응답 전송 (res.send)             │
│     - endTime 기록                  │
│     - duration 계산                 │
│     - 메트릭 기록                    │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  4. 메트릭 저장                      │
│  httpRequestDuration.observe(0.234) │
│  httpRequestsTotal.inc()            │
└─────────────────────────────────────┘

미들웨어 체인:
┌────────────────────────────────────────────────────┐
│  Request                                           │
│    ↓                                               │
│  [Metrics Middleware] ← 메트릭 수집 시작            │
│    ↓                                               │
│  [Auth Middleware]                                 │
│    ↓                                               │
│  [Body Parser]                                     │
│    ↓                                               │
│  [Route Handler] ← 실제 비즈니스 로직               │
│    ↓                                               │
│  [Error Handler]                                   │
│    ↓                                               │
│  [Metrics Middleware] ← 메트릭 수집 완료            │
│    ↓                                               │
│  Response                                          │
└────────────────────────────────────────────────────┘

정기적인 시스템 메트릭 수집:
┌────────────────────────────────────────────────────┐
│  setInterval(() => {                               │
│    메모리 사용량 측정                               │
│    CPU 사용량 측정                                  │
│    이벤트 루프 지연 측정                            │
│  }, 5000)  // 5초마다 수집                         │
└────────────────────────────────────────────────────┘

메트릭 수집 타이밍:
┌────────────────────────────────────────────────────┐
│                                                    │
│  요청        처리 시간 (234ms)        응답          │
│   │─────────────────────────────────→│            │
│   ↓                                  ↓             │
│  startTime                        endTime          │
│  (기록)                          (메트릭 저장)      │
│                                                    │
│  메트릭 내용:                                       │
│  - method: "GET"                                   │
│  - route: "/api/users"                             │
│  - status_code: "200"                              │
│  - duration: 0.234 (초)                            │
└────────────────────────────────────────────────────┘
```

#### 코드 구현

```javascript
// src/middleware/metricsMiddleware.js
const MetricsCollectionService = require('../services/metricsCollectionService');

class MetricsMiddleware {
  constructor() {
    this.metricsService = new MetricsCollectionService();
    
    // 정기적인 시스템 메트릭 수집
    setInterval(() => {
      this.metricsService.recordSystemMetrics();
    }, 5000); // 5초마다
  }
  
  // HTTP 요청 메트릭 수집 미들웨어
  collectHTTPMetrics() {
    return (req, res, next) => {
      const startTime = Date.now();
      const originalSend = res.send;
      
      // 응답 시간 측정
      res.send = function(data) {
        const duration = (Date.now() - startTime) / 1000; // 초 단위
        
        // 메트릭 기록
        this.metricsService.recordHTTPRequest(
          req.method,
          req.route?.path || req.path,
          res.statusCode.toString(),
          duration
        );
        
        originalSend.call(this, data);
      }.bind(this);
      
      next();
    };
  }
  
  // 데이터베이스 메트릭 수집 미들웨어
  collectDatabaseMetrics() {
    return (req, res, next) => {
      const originalQuery = req.db?.query;
      
      if (originalQuery) {
        req.db.query = function(sql, params, callback) {
          const startTime = Date.now();
          
          const wrappedCallback = function(error, results) {
            const duration = (Date.now() - startTime) / 1000;
            const status = error ? 'error' : 'success';
            
            // 메트릭 기록
            this.metricsService.recordDatabaseQuery(
              'query',
              'unknown',
              status,
              duration
            );
            
            if (callback) callback(error, results);
          }.bind(this);
          
          originalQuery.call(this, sql, params, wrappedCallback);
        }.bind(this);
      }
      
      next();
    };
  }
  
  // 에러 메트릭 수집 미들웨어
  collectErrorMetrics() {
    return (err, req, res, next) => {
      // 에러 메트릭 기록
      this.metricsService.recordError(
        err.name || 'UnknownError',
        err.statusCode >= 500 ? 'high' : 'medium',
        'http'
      );
      
      next(err);
    };
  }
  
  // 사용자 행동 메트릭 수집 미들웨어
  collectUserBehaviorMetrics() {
    return (req, res, next) => {
      if (req.user) {
        // 사용자 행동 메트릭 기록
        this.metricsService.recordCustomMetric(
          'user_action_total',
          1,
          {
            action: req.method,
            endpoint: req.path,
            userId: req.user.id
          }
        );
      }
      
      next();
    };
  }
  
  // 메트릭 서비스 반환
  getMetricsService() {
    return this.metricsService;
  }
}

module.exports = MetricsMiddleware;
```

### 3. Node.js 애플리케이션 메트릭 노출

#### 메트릭 엔드포인트 설정
```javascript
// src/routes/metricsRoutes.js
const express = require('express');
const MetricsCollectionService = require('../services/metricsCollectionService');

class MetricsRoutes {
  constructor() {
    this.router = express.Router();
    this.metricsService = new MetricsCollectionService();
    this.setupRoutes();
  }
  
  setupRoutes() {
    // Prometheus 메트릭 엔드포인트
    this.router.get('/metrics', async (req, res) => {
      try {
        const metrics = await this.metricsService.getMetrics();
        
        res.set('Content-Type', 'text/plain; version=0.0.4; charset=utf-8');
        res.send(metrics);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get metrics' });
      }
    });
    
    // 메트릭 상태 확인 엔드포인트
    this.router.get('/metrics/health', (req, res) => {
      try {
        const register = this.metricsService.getRegister();
        const metrics = register.getMetricsAsJSON();
        
        res.json({
          status: 'healthy',
          metricsCount: metrics.length,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        res.status(500).json({ 
          status: 'unhealthy',
          error: error.message 
        });
      }
    });
    
    // 특정 메트릭 조회 엔드포인트
    this.router.get('/metrics/:metricName', (req, res) => {
      try {
        const { metricName } = req.params;
        const register = this.metricsService.getRegister();
        const metrics = register.getMetricsAsJSON();
        
        const metric = metrics.find(m => m.name === metricName);
        
        if (!metric) {
          return res.status(404).json({ error: 'Metric not found' });
        }
        
        res.json(metric);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get metric' });
      }
    });
    
    // 메트릭 통계 엔드포인트
    this.router.get('/metrics/stats', (req, res) => {
      try {
        const register = this.metricsService.getRegister();
        const metrics = register.getMetricsAsJSON();
        
        const stats = {
          totalMetrics: metrics.length,
          metricTypes: {},
          timestamp: new Date().toISOString()
        };
        
        // 메트릭 타입별 통계
        metrics.forEach(metric => {
          const type = metric.type;
          stats.metricTypes[type] = (stats.metricTypes[type] || 0) + 1;
        });
        
        res.json(stats);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get metrics stats' });
      }
    });
    
    // 메트릭 리셋 엔드포인트 (개발 환경에서만)
    this.router.post('/metrics/reset', (req, res) => {
      if (process.env.NODE_ENV === 'production') {
        return res.status(403).json({ error: 'Not allowed in production' });
      }
      
      try {
        this.metricsService.prometheusClient.clearMetrics();
        res.json({ message: 'Metrics reset successfully' });
      } catch (error) {
        res.status(500).json({ error: 'Failed to reset metrics' });
      }
    });
  }
  
  getRouter() {
    return this.router;
  }
}

module.exports = MetricsRoutes;
```

#### 메트릭 노출 서버
```javascript
// src/servers/metricsServer.js
const express = require('express');
const MetricsRoutes = require('../routes/metricsRoutes');

class MetricsServer {
  constructor(port = 9090) {
    this.app = express();
    this.port = port;
    this.metricsRoutes = new MetricsRoutes();
    
    this.setupMiddleware();
    this.setupRoutes();
  }
  
  setupMiddleware() {
    // 기본 미들웨어
    this.app.use(express.json());
    this.app.use(express.urlencoded({ extended: true }));
    
    // CORS 설정
    this.app.use((req, res, next) => {
      res.header('Access-Control-Allow-Origin', '*');
      res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
      next();
    });
    
    // 요청 로깅
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
      next();
    });
  }
  
  setupRoutes() {
    // 메트릭 라우트
    this.app.use('/metrics', this.metricsRoutes.getRouter());
    
    // 헬스 체크
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
      });
    });
    
    // 루트 경로
    this.app.get('/', (req, res) => {
      res.json({
        message: 'Prometheus Metrics Server',
        endpoints: {
          metrics: '/metrics',
          health: '/health',
          stats: '/metrics/stats'
        }
      });
    });
  }
  
  start() {
    this.server = this.app.listen(this.port, () => {
      console.log(`Metrics server running on port ${this.port}`);
      console.log(`Metrics endpoint: http://localhost:${this.port}/metrics`);
    });
    
    // Graceful shutdown
    process.on('SIGTERM', () => {
      console.log('SIGTERM received, shutting down gracefully');
      this.server.close(() => {
        console.log('Metrics server closed');
        process.exit(0);
      });
    });
  }
  
  stop() {
    if (this.server) {
      this.server.close();
    }
  }
}

module.exports = MetricsServer;
```

### 4. 메트릭 엔드포인트 설정

#### 통합 메트릭 설정
```javascript
// src/config/metricsConfig.js
const metricsConfig = {
  // 기본 메트릭 설정
  default: {
    prefix: 'app_',
    gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
    eventLoopMonitoringPrecision: 10
  },
  
  // HTTP 메트릭 설정
  http: {
    durationBuckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
    labelNames: ['method', 'route', 'status_code']
  },
  
  // 데이터베이스 메트릭 설정
  database: {
    durationBuckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5],
    labelNames: ['operation', 'table', 'status']
  },
  
  // 비즈니스 메트릭 설정
  business: {
    userRegistration: {
      labelNames: ['source', 'status']
    },
    activeUsers: {
      labelNames: ['period']
    }
  },
  
  // 에러 메트릭 설정
  errors: {
    labelNames: ['type', 'severity', 'component']
  },
  
  // 시스템 메트릭 설정
  system: {
    memoryTypes: ['rss', 'heapTotal', 'heapUsed', 'external'],
    collectionInterval: 5000 // 5초
  }
};

// 환경별 설정
const environmentConfigs = {
  development: {
    ...metricsConfig,
    default: {
      ...metricsConfig.default,
      prefix: 'dev_'
    }
  },
  
  staging: {
    ...metricsConfig,
    default: {
      ...metricsConfig.default,
      prefix: 'staging_'
    }
  },
  
  production: {
    ...metricsConfig,
    default: {
      ...metricsConfig.default,
      prefix: 'prod_'
    },
    system: {
      ...metricsConfig.system,
      collectionInterval: 10000 // 10초
    }
  }
};

function getMetricsConfig(environment = 'development') {
  return environmentConfigs[environment] || environmentConfigs.development;
}

module.exports = { metricsConfig, getMetricsConfig };
```

## 예시

### 1. 완전한 Prometheus 통합 예제

실제 운영 환경에서의 통합 시나리오를 살펴봅니다:

```
┌─────────────────────────────────────────────────────────────┐
│          완전한 Prometheus 통합 아키텍처                      │
└─────────────────────────────────────────────────────────────┘

사용자 요청
     │
     ↓
┌─────────────────────────────────────────────────────────────┐
│  Express.js Application (Port 3000)                         │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  미들웨어 스택                                         │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  1. Metrics Middleware (모든 요청 추적)          │ │  │
│  │  │     - HTTP 요청 메트릭                            │ │  │
│  │  │     - 응답 시간 측정                              │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  2. Auth Middleware                              │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  3. Business Logic                               │ │  │
│  │  │     - 사용자 등록 메트릭                          │ │  │
│  │  │     - 비즈니스 이벤트 추적                        │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  4. Error Middleware (에러 추적)                 │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  정기 수집 (5초마다):                                        │
│  - 메모리 사용량                                             │
│  - CPU 사용량                                               │
│  - 활성 연결 수                                              │
└─────────────────────────────────────────────────────────────┘
                             │
                             │
┌─────────────────────────────────────────────────────────────┐
│  Metrics Server (Port 9090)                                 │
│                                                             │
│  엔드포인트:                                                 │
│  - GET /metrics      → Prometheus 포맷 메트릭                │
│  - GET /health       → 헬스 체크                             │
│  - GET /stats        → 메트릭 통계                           │
└─────────────────────────────────────────────────────────────┘
                             │
                             │ Pull (15초마다)
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  Prometheus Server                                          │
│  - 메트릭 수집 및 저장                                        │
│  - 알림 규칙 평가                                            │
│  - 쿼리 처리                                                 │
└─────────────────────────────────────────────────────────────┘
                    │                    │
                    ↓                    ↓
      ┌──────────────────┐    ┌──────────────────┐
      │    Grafana       │    │  AlertManager    │
      │  (시각화)         │    │    (알림)         │
      └──────────────────┘    └──────────────────┘

실시간 메트릭 수집 예시:

시간 축 ─────────────────────────────────────────────→

0초    : 앱 시작, 메트릭 초기화
5초    : 시스템 메트릭 수집 (메모리, CPU)
10초   : 요청 1 (GET /api/users, 234ms, 200)
         → http_request_duration_seconds.observe(0.234)
         → http_requests_total.inc()
15초   : Prometheus Scrape (메트릭 수집)
         시스템 메트릭 수집
18초   : 요청 2 (POST /api/users, 156ms, 201)
         → user_registrations_total.inc()
20초   : 시스템 메트릭 수집
25초   : 요청 3 (GET /api/products, 89ms, 200)
30초   : Prometheus Scrape
         시스템 메트릭 수집
...
```

#### Express.js 애플리케이션 통합

```javascript
// app.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

// 메트릭 관련 import
const MetricsMiddleware = require('./src/middleware/metricsMiddleware');
const MetricsServer = require('./src/servers/metricsServer');

const app = express();

// 메트릭 미들웨어 초기화
const metricsMiddleware = new MetricsMiddleware();

// 기본 미들웨어
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate Limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100, // 최대 100 요청
  message: {
    error: 'Too many requests from this IP',
    retryAfter: 15 * 60
  }
});
app.use('/api/', limiter);

// 메트릭 수집 미들웨어
app.use(metricsMiddleware.collectHTTPMetrics());
app.use(metricsMiddleware.collectDatabaseMetrics());
app.use(metricsMiddleware.collectUserBehaviorMetrics());

// 라우트 설정
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

app.get('/api/users', async (req, res) => {
  try {
    // 타이머 시작
    metricsMiddleware.getMetricsService().startTimer('userQuery');
    
    // 사용자 조회 로직
    const users = await User.findAll();
    
    // 타이머 종료
    const duration = metricsMiddleware.getMetricsService().endTimer('userQuery', {
      operation: 'SELECT',
      table: 'users'
    });
    
    // 비즈니스 메트릭 기록
    metricsMiddleware.getMetricsService().recordCustomMetric(
      'user_query_total',
      1,
      { operation: 'SELECT', table: 'users' }
    );
    
    res.json(users);
  } catch (error) {
    // 에러 메트릭 기록
    metricsMiddleware.getMetricsService().recordError(
      'DatabaseError',
      'high',
      'userService'
    );
    
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.post('/api/users', async (req, res) => {
  try {
    // 타이머 시작
    metricsMiddleware.getMetricsService().startTimer('userCreate');
    
    // 사용자 생성 로직
    const user = await User.create(req.body);
    
    // 타이머 종료
    const duration = metricsMiddleware.getMetricsService().endTimer('userCreate', {
      operation: 'INSERT',
      table: 'users'
    });
    
    // 사용자 등록 메트릭 기록
    metricsMiddleware.getMetricsService().recordUserRegistration(
      'api',
      'success'
    );
    
    res.status(201).json(user);
  } catch (error) {
    // 에러 메트릭 기록
    metricsMiddleware.getMetricsService().recordError(
      'ValidationError',
      'medium',
      'userService'
    );
    
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 에러 처리 미들웨어
app.use(metricsMiddleware.collectErrorMetrics());

// 404 처리
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// 메인 서버 시작
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Main server running on port ${PORT}`);
});

// 메트릭 서버 시작
const metricsServer = new MetricsServer(9090);
metricsServer.start();
```

### 2. Prometheus 설정 파일

Prometheus 서버는 YAML 파일로 설정을 관리합니다:

```
┌─────────────────────────────────────────────────────────────┐
│          Prometheus 설정 파일 구조                            │
└─────────────────────────────────────────────────────────────┘

prometheus.yml
├── global              (전역 설정)
│   ├── scrape_interval     → 메트릭 수집 주기
│   └── evaluation_interval → 규칙 평가 주기
│
├── rule_files         (알림 규칙 파일)
│   └── alert_rules.yml
│
├── alerting           (알림 설정)
│   └── alertmanagers
│       └── targets
│
└── scrape_configs     (스크래핑 대상 설정)
    ├── job_name          → 작업 이름
    ├── static_configs    → 정적 타겟
    │   └── targets       → 수집 대상 주소
    ├── metrics_path      → 메트릭 엔드포인트 경로
    ├── scrape_interval   → 수집 주기 (개별 설정)
    └── scrape_timeout    → 수집 타임아웃

설정 동작 흐름:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Prometheus Server 시작                                     │
│          ↓                                                 │
│  prometheus.yml 로드                                       │
│          ↓                                                 │
│  scrape_configs 파싱                                       │
│          ↓                                                 │
│  ┌──────────────────────────────────────────────────┐     │
│  │  Job: nodejs-app                                 │     │
│  │  Target: localhost:9090                          │     │
│  │  Interval: 5s                                    │     │
│  └────────────┬─────────────────────────────────────┘     │
│               │                                            │
│               ↓                                            │
│  15초마다 Scrape 실행                                       │
│  GET http://localhost:9090/metrics                         │
│               ↓                                            │
│  메트릭 데이터 파싱 & 저장                                   │
│               ↓                                            │
│  TSDB (Time Series Database)                               │
│               ↓                                            │
│  알림 규칙 평가 (15초마다)                                   │
│               ↓                                            │
│  조건 충족 시 AlertManager에 전송                           │
│                                                            │
└────────────────────────────────────────────────────────────┘

스크래핑 타임라인:
┌────────────────────────────────────────────────────────────┐
│  시간 축 ──────────────────────────────────────────→        │
│                                                            │
│  0초   ├─ Scrape (수집)                                     │
│  5초   ├─ Scrape                                           │
│  10초  ├─ Scrape                                           │
│  15초  ├─ Scrape + Rule Evaluation (규칙 평가)             │
│  20초  ├─ Scrape                                           │
│  25초  ├─ Scrape                                           │
│  30초  ├─ Scrape + Rule Evaluation                         │
│  ...                                                       │
│                                                            │
│  scrape_interval = 5초                                     │
│  evaluation_interval = 15초                                │
└────────────────────────────────────────────────────────────┘

멀티 타겟 설정:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Prometheus Server                                         │
│         │                                                  │
│         ├─→ App Instance 1 (localhost:9090)                │
│         │   └─ nodejs-app                                  │
│         │                                                  │
│         ├─→ App Instance 2 (server1:9090)                  │
│         │   └─ nodejs-app                                  │
│         │                                                  │
│         ├─→ Node Exporter (localhost:9100)                 │
│         │   └─ 시스템 메트릭                                │
│         │                                                  │
│         └─→ Custom Service (localhost:9091)                │
│             └─ 커스텀 메트릭                                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### prometheus.yml 설정

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Node.js 애플리케이션 메트릭
  - job_name: 'nodejs-app'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s
    scrape_timeout: 5s
    
  # Node.js 기본 메트릭
  - job_name: 'nodejs-default'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
    
  # 시스템 메트릭 (node_exporter)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s
```

#### 알림 규칙 설정

알림 규칙은 메트릭 값이 특정 조건을 만족할 때 알림을 발생시킵니다:

```
┌─────────────────────────────────────────────────────────────┐
│              알림 규칙 동작 흐름                              │
└─────────────────────────────────────────────────────────────┘

1. 메트릭 수집
   errors_total{type="DatabaseError"} = 50 (at 10:00:00)
   errors_total{type="DatabaseError"} = 60 (at 10:00:15)
   errors_total{type="DatabaseError"} = 75 (at 10:00:30)
   errors_total{type="DatabaseError"} = 95 (at 10:00:45)
        ↓

2. 알림 규칙 평가 (15초마다)
   ┌────────────────────────────────────────────┐
   │  rule: HighErrorRate                       │
   │  expr: rate(errors_total[5m]) > 0.1        │
   │  for: 2m                                   │
   └────────────┬───────────────────────────────┘
                ↓

3. 조건 평가 결과
   ┌────────────────────────────────────────────┐
   │  Time      │  Rate    │  Condition │ State │
   │  10:00:00  │  0.08    │  False     │ OK    │
   │  10:00:15  │  0.12    │  True      │ Pend  │ ← 알림 대기 시작
   │  10:00:30  │  0.15    │  True      │ Pend  │
   │  10:00:45  │  0.18    │  True      │ Pend  │
   │  10:01:00  │  0.20    │  True      │ Pend  │
   │  10:01:15  │  0.22    │  True      │ Pend  │
   │  10:01:30  │  0.25    │  True      │ Pend  │
   │  10:01:45  │  0.28    │  True      │ Pend  │
   │  10:02:00  │  0.30    │  True      │ Fire  │ ← 2분 경과, 알림 발생!
   └────────────────────────────────────────────┘
                ↓

4. 알림 발생
   ┌────────────────────────────────────────────┐
   │  Alert: HighErrorRate                      │
   │  Severity: warning                         │
   │  Summary: "High error rate detected"       │
   │  Description: "Error rate is 0.30/s"       │
   └────────────┬───────────────────────────────┘
                ↓

5. AlertManager로 전송
   ┌────────────────────────────────────────────┐
   │  AlertManager                              │
   │  - 알림 그룹핑                              │
   │  - 중복 제거                                │
   │  - 라우팅 (이메일, Slack, PagerDuty)        │
   └────────────────────────────────────────────┘

알림 상태 전이:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Inactive (조건 미충족)                                     │
│      │                                                     │
│      │ 조건 충족                                           │
│      ↓                                                     │
│  Pending (대기 중)                                          │
│      │                                                     │
│      │ 'for' 시간 경과                                     │
│      ↓                                                     │
│  Firing (알림 발생)                                         │
│      │                                                     │
│      │ 조건 미충족                                          │
│      ↓                                                     │
│  Inactive                                                  │
│                                                            │
└────────────────────────────────────────────────────────────┘

알림 심각도 레벨:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Critical (치명적)                                          │
│  ├─ 서비스 다운                                             │
│  ├─ 데이터 손실 위험                                         │
│  └─ 즉시 대응 필요                                          │
│                                                            │
│  Warning (경고)                                             │
│  ├─ 성능 저하                                               │
│  ├─ 리소스 부족                                             │
│  └─ 조사 필요                                               │
│                                                            │
│  Info (정보)                                                │
│  ├─ 정상 동작                                               │
│  ├─ 참고용 알림                                             │
│  └─ 즉각 대응 불필요                                         │
│                                                            │
└────────────────────────────────────────────────────────────┘

실제 알림 예시:
┌────────────────────────────────────────────────────────────┐
│  [ALERT] HighErrorRate                                     │
│  ────────────────────────────────────────────────────────  │
│  Severity: warning                                         │
│  Started: 2025-11-16 10:02:00                              │
│  Summary: High error rate detected                         │
│  Description: Error rate is 0.30 errors per second         │
│                                                            │
│  Current Value: 0.30                                       │
│  Threshold: 0.10                                           │
│                                                            │
│  Labels:                                                   │
│    - type: DatabaseError                                   │
│    - severity: high                                        │
│    - component: userService                                │
│                                                            │
│  Actions:                                                  │
│    - Check database connection                             │
│    - Review recent deployments                             │
│    - Check system logs                                     │
└────────────────────────────────────────────────────────────┘
```

#### 코드 설정

```yaml
# alert_rules.yml
groups:
  - name: nodejs-app
    rules:
      # 높은 에러율 알림
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      # 높은 응답 시간 알림
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"
      
      # 높은 메모리 사용률 알림
      - alert: HighMemoryUsage
        expr: nodejs_memory_usage_bytes{type="heapUsed"} > 1000000000
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }} bytes"
      
      # 데이터베이스 연결 문제 알림
      - alert: DatabaseConnectionIssue
        expr: database_connections_active{state="active"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection issue"
          description: "No active database connections"
```

## 운영 팁

### 1. Prometheus 메트릭 최적화

메트릭 수집은 애플리케이션 성능과 비용에 영향을 미치므로 최적화가 중요합니다:

```
┌─────────────────────────────────────────────────────────────┐
│              메트릭 최적화 전략                               │
└─────────────────────────────────────────────────────────────┘

1. 카디널리티 관리
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  문제: 높은 카디널리티 (High Cardinality)                   │
│                                                            │
│  나쁜 예:                                                   │
│  http_requests{user_id="user123"} ← 수백만 개 생성 가능     │
│                                                            │
│  좋은 예:                                                   │
│  http_requests{user_type="premium"} ← 제한된 개수           │
│                                                            │
│  영향:                                                      │
│  ┌──────────────┬───────────────┬───────────────┐          │
│  │ Cardinality  │  메모리 사용   │   성능        │          │
│  ├──────────────┼───────────────┼───────────────┤          │
│  │  낮음 (10)   │  10 MB        │   우수        │          │
│  │  중간 (100)  │  50 MB        │   양호        │          │
│  │  높음 (1000) │  200 MB       │   저하        │          │
│  │  매우높음    │  1+ GB        │   심각        │          │
│  └──────────────┴───────────────┴───────────────┘          │
│                                                            │
└────────────────────────────────────────────────────────────┘

2. 수집 주기 최적화
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  시간 축 ───────────────────────────────────────→          │
│                                                            │
│  5초 간격  (높은 빈도)                                      │
│  ├─├─├─├─├─├─├─├─├─├─├─├─                                 │
│  - 더 정확한 데이터                                         │
│  - 높은 저장소 사용                                         │
│  - 높은 네트워크 트래픽                                      │
│                                                            │
│  15초 간격 (중간 빈도) ← 추천                               │
│  ├────├────├────├────├────├────                            │
│  - 균형잡힌 정확도                                          │
│  - 적정 저장소 사용                                         │
│  - 표준 설정                                                │
│                                                            │
│  60초 간격 (낮은 빈도)                                      │
│  ├──────────────├──────────────├──────────────             │
│  - 낮은 정확도                                              │
│  - 낮은 저장소 사용                                         │
│  - 장기 추세 분석에 적합                                     │
│                                                            │
└────────────────────────────────────────────────────────────┘

3. 메트릭 보존 기간
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  시간대별 보존 전략:                                         │
│                                                            │
│  ┌─────────────┬───────────────┬──────────────┐           │
│  │  기간        │  상세도        │  용도         │           │
│  ├─────────────┼───────────────┼──────────────┤           │
│  │  1시간      │  5초           │  실시간       │           │
│  │  1일        │  15초 (원본)   │  당일 분석    │           │
│  │  1주        │  1분 (집계)    │  주간 리포트  │           │
│  │  1개월      │  5분 (집계)    │  월간 리포트  │           │
│  │  1년        │  1시간 (집계)  │  연간 추세    │           │
│  └─────────────┴───────────────┴──────────────┘           │
│                                                            │
│  저장소 사용량:                                             │
│  원본 (15초, 15일) → 100 GB                                │
│  집계 (1시간, 1년) → 10 GB                                 │
│                                                            │
└────────────────────────────────────────────────────────────┘

4. 불필요한 메트릭 제거
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  메트릭 감사 (Metric Audit):                               │
│                                                            │
│  ✓ 활용도 분석                                              │
│    - 쿼리 빈도 확인                                         │
│    - 대시보드 사용 여부                                      │
│    - 알림 규칙 사용 여부                                     │
│                                                            │
│  ✓ 중복 메트릭 제거                                         │
│    - 같은 정보를 나타내는 여러 메트릭                         │
│    - 비슷한 레이블 조합                                      │
│                                                            │
│  ✓ 레거시 메트릭 정리                                       │
│    - 더 이상 사용하지 않는 메트릭                            │
│    - 이전 버전의 메트릭                                      │
│                                                            │
│  최적화 효과:                                               │
│  Before: 500개 메트릭, 2GB 메모리                           │
│  After:  200개 메트릭, 800MB 메모리 (60% 절감)              │
│                                                            │
└────────────────────────────────────────────────────────────┘

5. 버킷 크기 최적화 (Histogram)
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  실제 데이터 분포 분석:                                      │
│                                                            │
│  응답시간 분포:                                             │
│  요청수 ↑                                                   │
│        │  ████                                             │
│        │  ████                                             │
│        │  ████  ███                                        │
│        │  ████  ███  ██                                    │
│        │  ████  ███  ██  ██  █                             │
│        └──┴───┴──┴──┴──┴──┴────→ 응답시간                   │
│          0.1 0.2 0.5 1  2  5s                              │
│                                                            │
│  나쁜 버킷: [0.1, 10, 100]  ← 너무 큼, 정보 손실            │
│  좋은 버킷: [0.1, 0.2, 0.5, 1, 2, 5, 10]  ← 분포 반영       │
│                                                            │
│  원칙:                                                      │
│  ✓ 실제 데이터 분포를 반영                                   │
│  ✓ 중요한 구간은 세밀하게                                    │
│  ✓ 버킷 수는 10-15개 권장                                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### 메트릭 최적화 가이드

```javascript
// scripts/optimizeMetrics.js
const optimizationTips = {
  performance: [
    '메트릭 수집 빈도 최적화',
    '불필요한 메트릭 제거',
    '메트릭 레이블 수 최소화',
    '메트릭 버킷 크기 조정'
  ],
  
  storage: [
    '메트릭 보존 기간 설정',
    '불필요한 메트릭 삭제',
    '메트릭 압축 설정',
    '스토리지 최적화'
  ],
  
  monitoring: [
    '핵심 메트릭 우선순위 설정',
    '알림 임계값 최적화',
    '대시보드 성능 최적화',
    '메트릭 쿼리 최적화'
  ],
  
  maintenance: [
    '정기적인 메트릭 검토',
    '메트릭 설정 업데이트',
    '성능 지표 분석',
    '비용 최적화'
  ]
};

function getOptimizationTips() {
  return optimizationTips;
}

module.exports = { getOptimizationTips };
```

### 2. Prometheus 모니터링 체크리스트

효과적인 모니터링을 위한 체계적인 점검 항목입니다:

```
┌─────────────────────────────────────────────────────────────┐
│          모니터링 성숙도 모델                                 │
└─────────────────────────────────────────────────────────────┘

레벨 5: 최적화 (Optimizing)
├─ 자동 튜닝
├─ 예측 분석
├─ AI 기반 이상 탐지
└─ 비용 최적화 자동화

레벨 4: 관리 (Managed)
├─ 포괄적인 대시보드
├─ 세밀한 알림 규칙
├─ SLA/SLO 추적
└─ 정기적인 리뷰

레벨 3: 정의 (Defined)
├─ 표준화된 메트릭
├─ 문서화된 프로세스
├─ 기본 알림
└─ 대시보드 구성

레벨 2: 반복 (Repeatable)
├─ 일부 메트릭 수집
├─ 수동 모니터링
└─ 기본 로깅

레벨 1: 초기 (Initial)
├─ 메트릭 없음
├─ 수동 디버깅
└─ 로그만 의존

현재 레벨 평가:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  체크리스트 완료율:                                         │
│                                                            │
│  Installation    ████████░░ 80% (4/5)                      │
│  Configuration   ██████░░░░ 60% (3/5)                      │
│  Monitoring      ████░░░░░░ 40% (2/5)                      │
│  Maintenance     ██░░░░░░░░ 20% (1/5)                      │
│                                                            │
│  전체 평균: 50% (레벨 3)                                    │
│                                                            │
└────────────────────────────────────────────────────────────┘

모니터링 구현 로드맵:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  1단계 (1주차): 기본 설정                                   │
│  ├─ Prometheus 설치                                        │
│  ├─ 기본 메트릭 수집                                        │
│  └─ /metrics 엔드포인트 노출                                │
│                                                            │
│  2단계 (2주차): 커스텀 메트릭                               │
│  ├─ HTTP 메트릭                                            │
│  ├─ 데이터베이스 메트릭                                     │
│  └─ 비즈니스 메트릭                                         │
│                                                            │
│  3단계 (3주차): 알림 설정                                   │
│  ├─ 알림 규칙 정의                                          │
│  ├─ AlertManager 설정                                      │
│  └─ 알림 채널 연동                                          │
│                                                            │
│  4단계 (4주차): 시각화                                      │
│  ├─ Grafana 대시보드                                       │
│  ├─ 주요 지표 시각화                                        │
│  └─ 팀 공유                                                │
│                                                            │
│  5단계 (진행중): 최적화                                     │
│  ├─ 성능 튜닝                                              │
│  ├─ 비용 최적화                                            │
│  └─ 지속적 개선                                            │
│                                                            │
└────────────────────────────────────────────────────────────┘

핵심 메트릭 (Golden Signals):
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  1. Latency (지연시간)                                      │
│     응답 시간 측정                                          │
│     http_request_duration_seconds                          │
│                                                            │
│  2. Traffic (트래픽)                                        │
│     요청 수 측정                                            │
│     http_requests_total                                    │
│                                                            │
│  3. Errors (에러)                                           │
│     에러율 측정                                             │
│     errors_total, http_requests{status=~"5.."}            │
│                                                            │
│  4. Saturation (포화도)                                     │
│     리소스 사용률                                           │
│     memory_usage, cpu_usage, disk_usage                    │
│                                                            │
└────────────────────────────────────────────────────────────┘

일일 모니터링 루틴:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  오전 (09:00)                                              │
│  ├─ 대시보드 확인                                          │
│  ├─ 알림 히스토리 리뷰                                      │
│  └─ 이상 징후 확인                                         │
│                                                            │
│  점심 (12:00)                                              │
│  ├─ 트래픽 패턴 확인                                        │
│  └─ 성능 지표 확인                                         │
│                                                            │
│  오후 (17:00)                                              │
│  ├─ 일일 리포트 생성                                        │
│  ├─ 이슈 기록                                              │
│  └─ 개선 사항 메모                                         │
│                                                            │
│  주간 (금요일)                                              │
│  ├─ 주간 리포트                                            │
│  ├─ 메트릭 최적화 검토                                      │
│  └─ 팀 회의                                                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### 모니터링 설정 검증

```javascript
// scripts/validatePrometheusSetup.js
const validationChecklist = {
  installation: [
    'Prometheus 서버 설치 확인',
    'Node.js 애플리케이션 메트릭 노출 확인',
    '메트릭 엔드포인트 접근 가능 확인',
    '기본 메트릭 수집 확인'
  ],
  
  configuration: [
    'prometheus.yml 설정 확인',
    '스크래핑 설정 확인',
    '알림 규칙 설정 확인',
    '메트릭 레이블 설정 확인'
  ],
  
  monitoring: [
    '핵심 메트릭 모니터링 확인',
    '알림 설정 확인',
    '대시보드 구성 확인',
    '메트릭 쿼리 테스트'
  ],
  
  maintenance: [
    '정기적인 메트릭 검토',
    '알림 임계값 조정',
    '성능 지표 분석',
    '스토리지 관리'
  ]
};

function validatePrometheusSetup() {
  const results = {};
  
  Object.keys(validationChecklist).forEach(category => {
    results[category] = {
      total: validationChecklist[category].length,
      implemented: 0,
      missing: []
    };
    
    validationChecklist[category].forEach(item => {
      if (isImplemented(item)) {
        results[category].implemented++;
      } else {
        results[category].missing.push(item);
      }
    });
  });
  
  return results;
}

module.exports = { validationChecklist, validatePrometheusSetup };
```

## 참고

### 모범 사례

#### Prometheus 메트릭 설계 원칙
1. **명확한 네이밍**: 메트릭 이름이 목적을 명확히 나타내도록
2. **적절한 레이블**: 메트릭을 분류하는 데 필요한 레이블만 사용
3. **일관된 형식**: 메트릭 이름과 레이블 형식의 일관성 유지
4. **성능 고려**: 메트릭 수집이 애플리케이션 성능에 미치는 영향 최소화
5. **보안 고려**: 민감한 정보가 메트릭에 노출되지 않도록 주의

#### 모니터링 전략
1. **다층 모니터링**: 시스템, 애플리케이션, 비즈니스 레벨 모니터링
2. **실시간 추적**: 실시간 성능 및 에러 추적
3. **트렌드 분석**: 장기적인 트렌드 분석
4. **비교 분석**: 과거 데이터와의 비교 분석
5. **자동화**: 모니터링 및 알림 자동화

### 결론

```
┌─────────────────────────────────────────────────────────────┐
│          Prometheus 메트릭 수집 전체 요약                     │
└─────────────────────────────────────────────────────────────┘

핵심 개념 정리:

1. 메트릭 타입
   ┌─────────────┬──────────────┬─────────────────┐
   │   타입       │    용도       │      예시        │
   ├─────────────┼──────────────┼─────────────────┤
   │  Counter    │  누적 카운트   │  요청 수, 에러 수 │
   │  Gauge      │  현재 상태     │  메모리, CPU     │
   │  Histogram  │  값의 분포     │  응답 시간       │
   │  Summary    │  백분위수      │  지연 시간       │
   └─────────────┴──────────────┴─────────────────┘

2. 아키텍처 흐름
   애플리케이션 → prom-client → /metrics 엔드포인트
                                       ↓
                               Prometheus Server
                                       ↓
                          ┌────────────┴────────────┐
                          ↓                         ↓
                      Grafana                 AlertManager
                     (시각화)                    (알림)

3. 구현 단계
   Step 1: 기본 설정
   ├─ prom-client 설치
   ├─ 메트릭 정의
   └─ 레지스트리 설정

   Step 2: 메트릭 수집
   ├─ HTTP 메트릭
   ├─ 비즈니스 메트릭
   └─ 시스템 메트릭

   Step 3: 메트릭 노출
   ├─ /metrics 엔드포인트
   └─ Prometheus 스크래핑

   Step 4: 모니터링
   ├─ 대시보드 구성
   ├─ 알림 설정
   └─ 지속적 개선

4. 모범 사례
   ✓ 카디널리티 제한
   ✓ 의미 있는 메트릭명
   ✓ 적절한 레이블 사용
   ✓ 최적화된 수집 주기
   ✓ 정기적인 리뷰

5. 피해야 할 사항
   ✗ 높은 카디널리티 (user_id 등)
   ✗ 너무 많은 메트릭
   ✗ 불명확한 네이밍
   ✗ 과도한 수집 빈도
   ✗ 문서화 부재

실전 적용 체크리스트:

□ Prometheus 서버 설치 및 설정
□ Node.js 애플리케이션에 prom-client 통합
□ 핵심 메트릭 (Golden Signals) 수집
  □ Latency (지연시간)
  □ Traffic (트래픽)
  □ Errors (에러)
  □ Saturation (포화도)
□ 커스텀 비즈니스 메트릭 정의
□ /metrics 엔드포인트 노출
□ Prometheus 스크래핑 설정
□ 기본 알림 규칙 구성
□ Grafana 대시보드 생성
□ 팀과 지식 공유
□ 문서화 및 유지보수 계획

성공 지표:

Week 1: 기본 메트릭 수집
        └─ 목표: 시스템 가시성 확보

Week 2-3: 커스텀 메트릭 추가
          └─ 목표: 비즈니스 인사이트

Week 4+: 최적화 및 개선
         └─ 목표: 성능 향상 및 비용 절감

지속적인 가치 창출:
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  모니터링 → 인사이트 → 액션 → 개선                          │
│      ↑                              │                      │
│      └──────────────────────────────┘                      │
│            (지속적 개선 사이클)                             │
│                                                            │
│  효과:                                                      │
│  • 평균 응답 시간 30% 감소                                  │
│  • 다운타임 70% 감소                                        │
│  • 문제 해결 시간 50% 단축                                  │
│  • 운영 비용 40% 절감                                       │
│                                                            │
└────────────────────────────────────────────────────────────┘

다음 단계 추천:

1. 고급 기능 탐색
   ├─ Service Discovery
   ├─ Recording Rules
   ├─ Federation
   └─ Remote Storage

2. 통합 확장
   ├─ Jaeger (분산 추적)
   ├─ ELK Stack (로그)
   ├─ OpenTelemetry
   └─ APM 도구

3. 학습 자료
   ├─ Prometheus 공식 문서
   ├─ PromQL 완전 정복
   ├─ Grafana 대시보드 디자인
   └─ SRE 모범 사례
```

**핵심 요점:**

Prometheus는 Node.js 애플리케이션의 성능 모니터링과 최적화를 위한 강력한 도구입니다.

🎯 **시작하기**: 작게 시작하여 점진적으로 확장하세요
- 먼저 핵심 메트릭(Golden Signals)부터 시작
- 비즈니스 가치가 높은 메트릭 우선 순위화
- 팀의 피드백을 받아 지속적으로 개선

📊 **데이터 기반 의사결정**: 메트릭을 통해 객관적인 판단
- 추측이 아닌 데이터로 문제 진단
- 성능 개선 효과를 정량적으로 측정
- 용량 계획 및 리소스 최적화

🚀 **지속적 개선**: 모니터링은 한 번에 완성되지 않습니다
- 정기적인 메트릭 리뷰
- 새로운 요구사항 반영
- 팀 간 지식 공유

적절한 메트릭 정의와 수집으로 애플리케이션의 성능을 지속적으로 개선하고,
지속적인 모니터링과 분석을 통해 안정적이고 성능이 우수한 애플리케이션을 유지하세요.
