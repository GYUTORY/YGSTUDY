---
title: Prometheus 모니터링 시스템
tags: [prometheus, monitoring, metrics, time-series, promql, alerting, observability]
updated: 2025-11-01
---

# Prometheus 모니터링 시스템

## 📋 목차

1. [Prometheus란 무엇인가?](#prometheus란-무엇인가)
2. [핵심 아키텍처](#핵심-아키텍처)
3. [메트릭 타입](#메트릭-타입)
4. [PromQL 쿼리 언어](#promql-쿼리-언어)
5. [Exporter와 데이터 수집](#exporter와-데이터-수집)
6. [Service Discovery](#service-discovery)
7. [Alerting 시스템](#alerting-시스템)
8. [스토리지와 데이터 관리](#스토리지와-데이터-관리)
9. [실무 활용 사례](#실무-활용-사례)
10. [최적화 및 베스트 프랙티스](#최적화-및-베스트-프랙티스)
11. [참고 자료](#참고-자료)

---

## Prometheus란 무엇인가?

### Prometheus의 정의

Prometheus는 **오픈소스 시스템 모니터링 및 알림 툴킷**입니다. 시계열 데이터베이스(TSDB)를 기반으로 하며, 다차원 데이터 모델과 강력한 쿼리 언어를 제공하여 시스템과 애플리케이션의 성능을 실시간으로 모니터링합니다.

**핵심 특징:**
```
1. Pull 기반 메트릭 수집
   - HTTP를 통해 타겟에서 메트릭을 가져옴
   - Push Gateway로 단기 작업 지원

2. 다차원 데이터 모델
   - 메트릭명 + 라벨(key-value)
   - 유연한 데이터 분류

3. 강력한 쿼리 언어 (PromQL)
   - 시계열 데이터 분석
   - 집계, 필터링, 연산

4. 독립적 노드
   - 분산 스토리지에 의존하지 않음
   - 단일 서버로 동작 가능

5. 시각화 및 알림
   - 내장 Expression Browser
   - Grafana 연동
   - Alertmanager 통합
```

### Prometheus의 탄생 배경

**SoundCloud의 과제 (2012년)**

```
문제 상황:
- 마이크로서비스 아키텍처로 전환
- 수백 개의 서비스 모니터링 필요
- 기존 도구의 한계
  - Nagios: 정적 설정, 확장성 부족
  - StatsD + Graphite: Push 기반, 복잡한 설정
  - 상용 솔루션: 높은 비용

요구사항:
- 동적 환경에 적합
- 간단한 설정
- 강력한 쿼리 언어
- 오픈소스
```

**Prometheus의 탄생 (2012년)**
- SoundCloud의 Matt T. Proud, Julius Volz가 시작
- Google의 Borgmon에서 영감
- 2016년: CNCF (Cloud Native Computing Foundation) 합류
- 2018년: Kubernetes 다음으로 두 번째 졸업 프로젝트

### 왜 Prometheus를 사용하는가?

**1. 클라우드 네이티브 친화적**
```
동적 환경:
├─ 자동 서비스 디스커버리
│  └─ Kubernetes, Consul, EC2 등
│
├─ 라벨 기반 데이터 모델
│  └─ 메타데이터로 유연한 쿼리
│
└─ 독립적 실행
   └─ 외부 의존성 최소화
```

**2. 강력한 쿼리 언어 (PromQL)**
```
복잡한 분석 가능:
- 비율 계산: rate(), irate()
- 백분위수: histogram_quantile()
- 예측: predict_linear()
- 집계: sum, avg, max, min
- 조인: label_join(), label_replace()
```

**3. 높은 신뢰성**
```
안정성:
- 단일 노드 동작 (SPOF 없음)
- 로컬 스토리지
- 빠른 복구
- 독립적 인스턴스
```

### Prometheus vs 경쟁 제품

| 특성 | Prometheus | InfluxDB | Graphite | Datadog |
|------|-----------|----------|----------|---------|
| **데이터 수집** | Pull (+ Push Gateway) | Push | Push | Agent Push |
| **쿼리 언어** | PromQL | InfluxQL, Flux | Functions | 웹 UI |
| **데이터 모델** | 다차원 (labels) | Tag 기반 | 계층적 | Tag 기반 |
| **스토리지** | 로컬 TSDB | TSM Engine | Whisper | 클라우드 |
| **확장성** | Federation, 원격 저장소 | 클러스터링 | 복잡함 | 완전 관리형 |
| **라이선스** | Apache 2.0 | MIT | Apache 2.0 | 상용 |
| **비용** | 무료 | 오픈소스/상용 | 무료 | 높음 |
| **알림** | Alertmanager | Kapacitor | 별도 도구 | 내장 |
| **생태계** | 매우 큼 | 중간 | 중간 | 큰 (상용) |

---

## 핵심 아키텍처

### 전체 구조

```
┌────────────────────────────────────────────────────────┐
│                  Prometheus Server                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Retrieval (메트릭 수집)               │  │
│  │  - HTTP Pull                                     │  │
│  │  - Service Discovery                             │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                     │
│  ┌────────────────▼─────────────────────────────────┐  │
│  │           TSDB (시계열 데이터베이스)            │  │
│  │  - 로컬 스토리지                                │  │
│  │  - 2시간 청크                                   │  │
│  │  - 압축 및 인덱싱                              │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                     │
│  ┌────────────────▼─────────────────────────────────┐  │
│  │           PromQL Engine                          │  │
│  │  - 쿼리 실행                                    │  │
│  │  - 집계 및 계산                                 │  │
│  └──────────┬──────────────────┬─────────────────────┘  │
│             │                  │                        │
└─────────────┼──────────────────┼────────────────────────┘
              │                  │
    ┌─────────▼──────┐   ┌──────▼────────┐
    │   Grafana      │   │ Alertmanager  │
    │  (시각화)      │   │   (알림)      │
    └────────────────┘   └───────────────┘
              ▲                  │
              │                  │
        ┌─────┴──────────────────▼─────────┐
        │                                   │
    ┌───▼────┐  ┌────────┐  ┌────────┐  ┌─▼───────┐
    │Exporter│  │App     │  │Push    │  │ Slack   │
    │        │  │/metrics│  │Gateway │  │ Email   │
    └────────┘  └────────┘  └────────┘  └─────────┘
```

### Pull vs Push 모델

**Pull 모델 (Prometheus)**

```
장점:
✓ 서비스 디스커버리 용이
  - 동적으로 타겟 추가/제거
  - 설정 변경 없이 스케일링

✓ 중앙 집중식 제어
  - Prometheus가 수집 주기 결정
  - 타겟 상태 파악 가능 (up/down)

✓ 네트워크 효율성
  - 타겟이 느리면 타임아웃
  - 불필요한 연결 최소화

단점:
✗ 방화벽 문제
  - Prometheus → Target 접근 필요
  - NAT 환경에서 복잡

✗ 단기 작업 모니터링 어려움
  - 작업 완료 전에 수집 필요
  - Push Gateway로 해결
```

**Push 모델 (InfluxDB, Graphite)**

```
장점:
✓ 단기 작업 친화적
  - 작업 완료 전 메트릭 전송

✓ 방화벽 친화적
  - Target → 서버 연결 (단방향)

단점:
✗ 서비스 디스커버리 복잡
  - 타겟이 서버 주소 알아야 함

✗ 과부하 위험
  - 타겟이 무제한 전송 가능
```

### 데이터 모델

**시계열 구조:**

```
메트릭명{라벨1="값1", 라벨2="값2"} 값 타임스탬프

예시:
http_requests_total{method="GET", status="200", instance="api-1"} 12500 1635724800

구성:
- 메트릭명: http_requests_total
- 라벨:
  - method="GET"
  - status="200"
  - instance="api-1"
- 값: 12500
- 타임스탬프: 1635724800
```

**라벨의 힘:**

```
라벨 없이:
http_requests_total_get_200
http_requests_total_get_404
http_requests_total_post_200
http_requests_total_post_404
→ 메트릭이 무한히 증가

라벨 사용:
http_requests_total{method="GET", status="200"}
http_requests_total{method="GET", status="404"}
http_requests_total{method="POST", status="200"}
http_requests_total{method="POST", status="404"}
→ 하나의 메트릭, 다차원 분석 가능

쿼리:
# GET 요청만
http_requests_total{method="GET"}

# 200번대 응답만
http_requests_total{status=~"2.."}

# 특정 인스턴스
http_requests_total{instance="api-1"}

# 집계
sum by(method) (http_requests_total)
```

### 저장 구조 (TSDB)

**청크 기반 저장:**

```
데이터 저장 주기:
└─ 2시간 청크 (메모리)
   └─ 디스크 블록 (압축)
      └─ 장기 저장소 (선택)

예시:
12:00-14:00 → 청크 1 (메모리)
14:00-16:00 → 청크 2 (메모리)
              청크 1 → 디스크 블록
16:00-18:00 → 청크 3 (메모리)
              청크 2 → 디스크 블록
```

**압축:**

```
원본 데이터:
시간       값
12:00:00   100
12:00:15   101
12:00:30   102
12:00:45   103

압축 후 (Delta encoding):
시작: 12:00:00, 값: 100
+15초, +1
+15초, +1
+15초, +1

압축률: 약 10:1
```

**인덱싱:**

```
역 인덱스 (Inverted Index):

라벨:
method="GET"  → [series1, series3, series5]
method="POST" → [series2, series4]
status="200"  → [series1, series2, series3]
status="404"  → [series4, series5]

쿼리: {method="GET", status="200"}
→ series1, series3 ∩ series1, series2, series3
→ series1, series3
```

---

## 메트릭 타입

### 1. Counter (카운터)

**특징:**
- 단조 증가하는 값
- 리셋 시 0으로 초기화
- 누적 값

**사용 사례:**
```
- HTTP 요청 수
- 에러 발생 횟수
- 처리된 작업 수
- 전송된 바이트 수
```

**예시:**

```promql
# 메트릭 정의
http_requests_total{method="GET", status="200"} 12500

# 초당 요청률 (가장 많이 사용)
rate(http_requests_total[5m])

# 순간 요청률 (민감함)
irate(http_requests_total[5m])

# 5분간 증가량
increase(http_requests_total[5m])

# 전체 요청 수
sum(http_requests_total)
```

**주의사항:**
```
❌ 직접 사용하지 말 것:
http_requests_total

✅ rate() 또는 increase() 사용:
rate(http_requests_total[5m])

이유: Counter는 누적 값이므로 변화율이 의미있음
```

### 2. Gauge (게이지)

**특징:**
- 증가/감소 가능
- 현재 상태 표현
- 스냅샷 값

**사용 사례:**
```
- 메모리 사용량
- CPU 온도
- 동시 연결 수
- 대기열 크기
```

**예시:**

```promql
# 메트릭 정의
node_memory_MemAvailable_bytes 8589934592

# 현재 값
node_memory_MemAvailable_bytes

# 평균
avg_over_time(node_memory_MemAvailable_bytes[5m])

# 최대/최소
max_over_time(node_memory_MemAvailable_bytes[1h])
min_over_time(node_memory_MemAvailable_bytes[1h])

# 예측
predict_linear(node_memory_MemAvailable_bytes[1h], 3600)
```

### 3. Histogram (히스토그램)

**특징:**
- 값의 분포 추적
- 버킷 기반 집계
- 백분위수 계산 가능

**구조:**

```
http_request_duration_seconds_bucket{le="0.1"} 1000
http_request_duration_seconds_bucket{le="0.5"} 1500
http_request_duration_seconds_bucket{le="1.0"} 1800
http_request_duration_seconds_bucket{le="2.0"} 1950
http_request_duration_seconds_bucket{le="+Inf"} 2000
http_request_duration_seconds_sum 2500
http_request_duration_seconds_count 2000

해석:
- 0.1초 이하: 1000건 (50%)
- 0.5초 이하: 1500건 (75%)
- 1.0초 이하: 1800건 (90%)
- 2.0초 이하: 1950건 (97.5%)
- 전체: 2000건
- 합계: 2500초
- 평균: 2500/2000 = 1.25초
```

**예시:**

```promql
# P95 (95번째 백분위수)
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
)

# P50, P90, P99
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.90, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# 평균 응답 시간
rate(http_request_duration_seconds_sum[5m]) /
rate(http_request_duration_seconds_count[5m])

# 1초 이상 걸린 요청 비율
(
  rate(http_request_duration_seconds_bucket{le="+Inf"}[5m]) -
  rate(http_request_duration_seconds_bucket{le="1.0"}[5m])
) /
rate(http_request_duration_seconds_bucket{le="+Inf"}[5m]) * 100
```

### 4. Summary (요약)

**특징:**
- 클라이언트 측에서 백분위수 계산
- 정확한 백분위수
- 집계 불가

**구조:**

```
http_request_duration_seconds{quantile="0.5"} 0.3
http_request_duration_seconds{quantile="0.9"} 0.8
http_request_duration_seconds{quantile="0.99"} 1.5
http_request_duration_seconds_sum 2500
http_request_duration_seconds_count 2000
```

**Histogram vs Summary:**

| 특성 | Histogram | Summary |
|------|-----------|---------|
| **계산 위치** | 서버 (Prometheus) | 클라이언트 (애플리케이션) |
| **정확도** | 근사치 | 정확 |
| **집계** | 가능 (여러 인스턴스) | 불가능 |
| **백분위수 변경** | 쿼리 시 가능 | 사전 정의 필요 |
| **성능** | 서버 부하 | 클라이언트 부하 |
| **사용 권장** | ✅ 대부분의 경우 | 정확도가 매우 중요한 경우만 |

---

## PromQL 쿼리 언어

### 기본 쿼리

**선택자 (Selector):**

```promql
# 메트릭명만
http_requests_total

# 정확한 매칭
http_requests_total{method="GET"}

# 부정 매칭
http_requests_total{method!="GET"}

# 정규표현식 매칭
http_requests_total{status=~"2.."}

# 정규표현식 부정 매칭
http_requests_total{status!~"5.."}

# 여러 조건
http_requests_total{method="GET", status=~"2.."}
```

**시간 범위:**

```promql
# 현재 값
http_requests_total

# 5분 전 값
http_requests_total offset 5m

# 1시간 전부터 5분간
http_requests_total[5m] offset 1h

# 범위 벡터 (5분간의 모든 값)
http_requests_total[5m]
```

### 집계 연산자

```promql
# 합계
sum(http_requests_total)

# 그룹별 합계
sum by(method) (http_requests_total)
sum by(method, status) (http_requests_total)

# 제외하고 합계
sum without(instance) (http_requests_total)

# 평균
avg(http_requests_total)

# 최대/최소
max(http_requests_total)
min(http_requests_total)

# 개수
count(http_requests_total)

# 표준편차
stddev(http_requests_total)

# 백분위수 (quantile)
quantile(0.95, http_requests_total)

# 상위 N개
topk(5, http_requests_total)

# 하위 N개
bottomk(5, http_requests_total)
```

### 함수

**rate 함수 (가장 중요):**

```promql
# 초당 평균 증가율
rate(http_requests_total[5m])

# 해석:
# - 5분 동안의 데이터를 기반으로
# - 선형 회귀로 추세 계산
# - 초당 증가율 반환

# irate: 순간 증가율 (민감함)
irate(http_requests_total[5m])

# 차이점:
rate()  → 평균 (안정적)
irate() → 순간 (변동성 큼)

# 사용 권장:
- rate(): 대시보드, 알림
- irate(): 급격한 변화 감지
```

**시간 관련 함수:**

```promql
# 시간 범위 함수
avg_over_time(http_requests_total[5m])
max_over_time(http_requests_total[5m])
min_over_time(http_requests_total[5m])
sum_over_time(http_requests_total[5m])
count_over_time(http_requests_total[5m])

# 변화 감지
delta(cpu_usage[5m])  # Gauge 변화량
idelta(cpu_usage[5m]) # 순간 변화량

# 증가량 (Counter 전용)
increase(http_requests_total[5m])

# 예측
predict_linear(node_memory_MemAvailable_bytes[1h], 3600)
# 1시간 데이터로 1시간 후 예측
```

**변환 함수:**

```promql
# 절대값
abs(delta(cpu_usage[5m]))

# 반올림
ceil(http_request_duration_seconds)
floor(http_request_duration_seconds)
round(http_request_duration_seconds, 0.1)

# 로그
ln(http_requests_total)
log2(http_requests_total)
log10(http_requests_total)

# 삼각 함수
sqrt(http_requests_total)

# 제한
clamp_max(cpu_usage, 100)
clamp_min(cpu_usage, 0)
```

### 실전 쿼리 예시

**1. HTTP 에러율**

```promql
# 5xx 에러율 (%)
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100

# 메서드별 에러율
sum by(method) (rate(http_requests_total{status=~"5.."}[5m])) /
sum by(method) (rate(http_requests_total[5m])) * 100
```

**2. CPU 사용률**

```promql
# CPU 사용률 (%)
100 - (avg by(instance) (
  rate(node_cpu_seconds_total{mode="idle"}[5m])
) * 100)

# 코어별 CPU 사용률
100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)
```

**3. 메모리 사용률**

```promql
# 메모리 사용률 (%)
100 * (1 - (
  node_memory_MemAvailable_bytes /
  node_memory_MemTotal_bytes
))

# 스왑 사용률
100 * (
  (node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes) /
  node_memory_SwapTotal_bytes
)
```

**4. 디스크 I/O**

```promql
# 디스크 읽기 속도 (MB/s)
rate(node_disk_read_bytes_total[5m]) / 1024 / 1024

# 디스크 쓰기 속도 (MB/s)
rate(node_disk_written_bytes_total[5m]) / 1024 / 1024

# 디스크 사용률 (%)
100 - (
  node_filesystem_avail_bytes{fstype!="tmpfs"} /
  node_filesystem_size_bytes{fstype!="tmpfs"} * 100
)
```

**5. 네트워크 트래픽**

```promql
# 네트워크 수신 속도 (Mbps)
rate(node_network_receive_bytes_total[5m]) * 8 / 1000000

# 네트워크 송신 속도 (Mbps)
rate(node_network_transmit_bytes_total[5m]) * 8 / 1000000

# 인터페이스별 총 트래픽
sum by(device) (
  rate(node_network_receive_bytes_total[5m]) +
  rate(node_network_transmit_bytes_total[5m])
) * 8 / 1000000
```

---

## Exporter와 데이터 수집

### 주요 Exporter

**1. Node Exporter (인프라)**

```bash
# 설치
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.6.1.linux-amd64.tar.gz
cd node_exporter-1.6.1.linux-amd64
./node_exporter

# 수집 메트릭:
- CPU 사용률
- 메모리 사용량
- 디스크 I/O
- 네트워크 트래픽
- 파일시스템 사용량
- 시스템 로드
```

**prometheus.yml 설정:**

```yaml
scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s
```

**2. MySQL Exporter (데이터베이스)**

```bash
# 설치
wget https://github.com/prometheus/mysqld_exporter/releases/download/v0.15.0/mysqld_exporter-0.15.0.linux-amd64.tar.gz
tar xvfz mysqld_exporter-0.15.0.linux-amd64.tar.gz
cd mysqld_exporter-0.15.0.linux-amd64

# 환경 변수 설정
export DATA_SOURCE_NAME="exporter:password@(localhost:3306)/"
./mysqld_exporter

# 수집 메트릭:
- 쿼리 성능
- 연결 수
- InnoDB 통계
- 복제 상태
- 슬로우 쿼리
```

**prometheus.yml 설정:**

```yaml
scrape_configs:
  - job_name: 'mysql'
    static_configs:
      - targets: ['localhost:9104']
```

**3. Blackbox Exporter (엔드포인트 모니터링)**

```bash
# 설치
wget https://github.com/prometheus/blackbox_exporter/releases/download/v0.24.0/blackbox_exporter-0.24.0.linux-amd64.tar.gz
tar xvfz blackbox_exporter-0.24.0.linux-amd64.tar.gz
cd blackbox_exporter-0.24.0.linux-amd64
./blackbox_exporter

# 기능:
- HTTP/HTTPS 헬스체크
- TCP 연결 테스트
- ICMP (ping)
- DNS 조회
```

**prometheus.yml 설정:**

```yaml
scrape_configs:
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://example.com
        - https://api.example.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9115
```

### 애플리케이션 계측

**Node.js (prom-client):**

```javascript
const express = require('express');
const client = require('prom-client');

// 레지스트리 생성
const register = new client.Registry();

// 기본 메트릭 수집
client.collectDefaultMetrics({ register });

// 커스텀 메트릭
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestsTotal);

// 미들웨어
app.use((req, res, next) => {
  const end = httpRequestDuration.startTimer();
  res.on('finish', () => {
    end({ 
      method: req.method, 
      route: req.route?.path || req.path,
      status_code: res.statusCode 
    });
    httpRequestsTotal.inc({ 
      method: req.method, 
      route: req.route?.path || req.path,
      status_code: res.statusCode 
    });
  });
  next();
});

// 메트릭 엔드포인트
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});
```

**Python (prometheus_client):**

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Flask, Response
import time

app = Flask(__name__)

# 메트릭 정의
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_in_progress',
    'Active HTTP Requests'
)

@app.before_request
def before_request():
    request._start_time = time.time()
    ACTIVE_REQUESTS.inc()

@app.after_request
def after_request(response):
    request_latency = time.time() - request._start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.path
    ).observe(request_latency)
    
    ACTIVE_REQUESTS.dec()
    return response

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')
```

**Go (prometheus/client_golang):**

```go
package main

import (
    "net/http"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
    httpRequestsTotal = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total number of HTTP requests",
        },
        []string{"method", "path", "status"},
    )
    
    httpRequestDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "Duration of HTTP requests",
            Buckets: prometheus.DefBuckets,
        },
        []string{"method", "path"},
    )
)

func init() {
    prometheus.MustRegister(httpRequestsTotal)
    prometheus.MustRegister(httpRequestDuration)
}

func instrumentHandler(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        timer := prometheus.NewTimer(httpRequestDuration.WithLabelValues(r.Method, r.URL.Path))
        defer timer.ObserveDuration()
        
        next(w, r)
        
        httpRequestsTotal.WithLabelValues(r.Method, r.URL.Path, "200").Inc()
    }
}

func main() {
    http.Handle("/metrics", promhttp.Handler())
    http.HandleFunc("/api", instrumentHandler(apiHandler))
    http.ListenAndServe(":8080", nil)
}
```

---

## Service Discovery

### Kubernetes Service Discovery

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    
    relabel_configs:
      # Annotation으로 스크래핑 제어
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      
      # 포트 설정
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
      
      # 경로 설정
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      
      # 라벨 추가
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
```

**Pod Annotation:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  containers:
    - name: app
      image: my-app:latest
      ports:
        - containerPort: 8080
```

### EC2 Service Discovery

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ec2'
    ec2_sd_configs:
      - region: us-east-1
        access_key: YOUR_ACCESS_KEY
        secret_key: YOUR_SECRET_KEY
        port: 9100
    
    relabel_configs:
      # 태그로 필터링
      - source_labels: [__meta_ec2_tag_Environment]
        regex: production
        action: keep
      
      # Private IP 사용
      - source_labels: [__meta_ec2_private_ip]
        target_label: __address__
        replacement: ${1}:9100
      
      # 라벨 추가
      - source_labels: [__meta_ec2_tag_Name]
        target_label: instance_name
      - source_labels: [__meta_ec2_availability_zone]
        target_label: availability_zone
```

### Consul Service Discovery

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'consul'
    consul_sd_configs:
      - server: 'localhost:8500'
        services: []
    
    relabel_configs:
      # 서비스 이름으로 필터링
      - source_labels: [__meta_consul_service]
        regex: (api|web)
        action: keep
      
      # 태그로 필터링
      - source_labels: [__meta_consul_tags]
        regex: .*,prometheus,.*
        action: keep
      
      # 주소 설정
      - source_labels: [__meta_consul_address, __meta_consul_service_port]
        target_label: __address__
        regex: ([^:]+):(.+)
        replacement: ${1}:${2}
```

---

## Alerting 시스템

### Alert 규칙 정의

```yaml
# /etc/prometheus/rules/alerts.yml
groups:
  - name: infrastructure
    interval: 30s
    rules:
      # 높은 CPU 사용률
      - alert: HighCPUUsage
        expr: |
          100 - (avg by(instance) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          ) * 100) > 80
        for: 5m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
          runbook_url: "https://wiki.example.com/runbooks/high-cpu"
      
      # 메모리 부족
      - alert: HighMemoryUsage
        expr: |
          100 * (1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          )) > 90
        for: 5m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanizePercentage }}"
      
      # 디스크 공간 부족
      - alert: DiskSpaceLow
        expr: |
          100 - (
            node_filesystem_avail_bytes{fstype!="tmpfs"} /
            node_filesystem_size_bytes{fstype!="tmpfs"} * 100
          ) > 85
        for: 10m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk usage is {{ $value | humanizePercentage }} on {{ $labels.mountpoint }}"
      
      # 인스턴스 다운
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Instance {{ $labels.instance }} down"
          description: "{{ $labels.instance }} of job {{ $labels.job }} has been down for more than 1 minute"

  - name: application
    interval: 30s
    rules:
      # 높은 에러율
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) /
          sum(rate(http_requests_total[5m])) * 100 > 5
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High HTTP error rate"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      # 느린 응답 시간
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 2
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Slow HTTP response time"
          description: "P95 latency is {{ $value }}s"
      
      # API Rate Limit 근접
      - alert: APIRateLimitApproaching
        expr: |
          api_rate_limit_remaining / api_rate_limit_total * 100 < 20
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "API rate limit approaching"
          description: "Only {{ $value | humanizePercentage }} of rate limit remaining"
```

### Alertmanager 설정

```yaml
# /etc/alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

# 템플릿
templates:
  - '/etc/alertmanager/templates/*.tmpl'

# 라우팅
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  
  routes:
    # Critical 알림
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true
    
    # 팀별 라우팅
    - match:
        team: backend
      receiver: 'slack-backend'
      continue: true
    
    - match:
        team: infrastructure
      receiver: 'slack-infrastructure'
      continue: true
    
    # 업무 시간 외
    - match_re:
        severity: ^(warning|info)$
      receiver: 'slack-non-urgent'
      active_time_intervals:
        - business_hours

# 알림 억제
inhibit_rules:
  # Instance down이면 다른 알림 억제
  - source_match:
      alertname: InstanceDown
    target_match_re:
      alertname: (HighCPU|HighMemory|DiskSpace).*
    equal: ['instance']

# Receiver 정의
receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: YOUR_PAGERDUTY_KEY
        description: '{{ .GroupLabels.alertname }}'
  
  - name: 'slack-backend'
    slack_configs:
      - channel: '#backend-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        send_resolved: true
  
  - name: 'slack-infrastructure'
    slack_configs:
      - channel: '#infrastructure-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        send_resolved: true
  
  - name: 'slack-non-urgent'
    slack_configs:
      - channel: '#alerts-non-urgent'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

# 활성 시간 정의
time_intervals:
  - name: business_hours
    time_intervals:
      - times:
          - start_time: '09:00'
            end_time: '18:00'
        weekdays: ['monday:friday']
```

---

## 스토리지와 데이터 관리

### 로컬 스토리지 관리

**디렉토리 구조:**

```
/var/lib/prometheus/
├── chunks_head/        # 최신 2시간 청크 (메모리 매핑)
├── 01234567890/       # 압축된 블록 (2시간)
│   ├── chunks/
│   ├── index
│   ├── meta.json
│   └── tombstones
├── 01234567900/
└── wal/                # Write-Ahead Log
    ├── 00000000
    ├── 00000001
    └── checkpoint/
```

**데이터 보존 설정:**

```bash
# prometheus.yml 또는 커맨드라인
prometheus \
  --storage.tsdb.path=/var/lib/prometheus/ \
  --storage.tsdb.retention.time=15d \        # 15일 보관
  --storage.tsdb.retention.size=50GB \       # 최대 50GB
  --storage.tsdb.min-block-duration=2h \     # 최소 블록 크기
  --storage.tsdb.max-block-duration=36h      # 최대 블록 크기
```

**압축 및 정리:**

```
자동 압축:
2시간 청크 → 2시간 블록 → 4시간 블록 → 8시간 블록 → ... → 최대 31일

예시:
Day 1: [00-02][02-04][04-06]...[22-24]
Day 2: [00-04][04-08][08-12]...[20-24]
Day 3: [00-08][08-16][16-24]
...

오래된 블록 자동 삭제:
- retention.time 또는 retention.size 초과 시
- 백그라운드에서 실행
```

### 원격 저장소 (Remote Storage)

**지원 백엔드:**
- InfluxDB
- Cortex
- Thanos
- M3DB
- VictoriaMetrics
- Timescale

**설정 예시 (InfluxDB):**

```yaml
# prometheus.yml
remote_write:
  - url: "http://influxdb:8086/api/v1/prom/write?db=prometheus"
    queue_config:
      capacity: 10000
      max_shards: 50
      min_shards: 1
      max_samples_per_send: 5000
      batch_send_deadline: 5s
    
remote_read:
  - url: "http://influxdb:8086/api/v1/prom/read?db=prometheus"
    read_recent: true
```

**Thanos (장기 저장소):**

```yaml
# thanos-sidecar 설정
thanos sidecar \
  --tsdb.path=/var/lib/prometheus \
  --prometheus.url=http://localhost:9090 \
  --objstore.config-file=/etc/thanos/bucket.yml \
  --grpc-address=0.0.0.0:10901 \
  --http-address=0.0.0.0:10902

# S3 버킷 설정
# /etc/thanos/bucket.yml
type: S3
config:
  bucket: "prometheus-thanos"
  endpoint: "s3.amazonaws.com"
  region: "us-east-1"
```

---

## 실무 활용 사례

### 1. 쿠버네티스 모니터링

**전체 스택:**

```yaml
# prometheus-operator를 사용한 배포
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
      # kube-apiserver
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
          - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
          - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
            action: keep
            regex: default;kubernetes;https
      
      # kubelet
      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
          - role: node
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      
      # pods
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
```

### 2. 마이크로서비스 모니터링

**서비스 메시 (Istio) 메트릭:**

```promql
# 서비스별 요청률
sum(rate(istio_requests_total[5m])) by (destination_service_name)

# 서비스별 에러율
sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service_name) /
sum(rate(istio_requests_total[5m])) by (destination_service_name) * 100

# P95 레이턴시
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le, destination_service_name)
)

# 서비스 간 트래픽 맵
sum(rate(istio_requests_total[5m])) by (source_app, destination_app)
```

### 3. 데이터베이스 모니터링

**MySQL 성능 메트릭:**

```promql
# QPS (Queries Per Second)
rate(mysql_global_status_questions[5m])

# 슬로우 쿼리
rate(mysql_global_status_slow_queries[5m])

# 연결 사용률
mysql_global_status_threads_connected / 
mysql_global_variables_max_connections * 100

# InnoDB 버퍼 풀 효율
(1 - (mysql_global_status_innodb_buffer_pool_reads / 
      mysql_global_status_innodb_buffer_pool_read_requests)) * 100

# 복제 지연
mysql_slave_status_seconds_behind_master
```

---

## 최적화 및 베스트 프랙티스

### 메트릭 네이밍

```
규칙:
<namespace>_<name>_<unit>_<suffix>

예시:
http_requests_total
http_request_duration_seconds
node_memory_MemAvailable_bytes
database_query_duration_seconds

단위:
- seconds: 초
- bytes: 바이트
- ratio: 비율 (0-1)
- percent: 백분율 (0-100)

Suffix:
- _total: Counter
- _count: Histogram/Summary 카운트
- _sum: Histogram/Summary 합계
- _bucket: Histogram 버킷
```

### 라벨 설계

```
좋은 라벨:
✅ 카디널리티가 낮음 (< 100)
   method="GET", status="200"

✅ 의미있는 그룹화
   service="api", environment="prod"

나쁜 라벨:
❌ 높은 카디널리티
   user_id="12345", session_id="abc..."
   → 시계열 폭발 (Cardinality explosion)

❌ 동적 값
   url="/user/12345/profile"
   → url="/user/:id/profile" 사용

❌ 불필요한 라벨
   timestamp="2023-10-01"
   → 시계열 데이터베이스가 이미 시간 관리
```

### 쿼리 최적화

```promql
# ❌ 비효율적
sum(rate(http_requests_total{job="api"}[5m])) by (method) * 60

# ✅ 효율적 (집계 먼저)
sum by (method) (rate(http_requests_total{job="api"}[5m])) * 60

# ❌ 비효율적 (많은 시계열)
rate(http_requests_total[5m])

# ✅ 효율적 (필터링 먼저)
rate(http_requests_total{job="api", method="GET"}[5m])

# ❌ 비효율적 (큰 범위)
rate(http_requests_total[1h])

# ✅ 효율적 (적절한 범위, 스크래핑 간격의 4배)
rate(http_requests_total[1m])  # 스크래핑 15초 가정
```

### 성능 튜닝

```bash
# prometheus.yml 설정
global:
  scrape_interval: 15s          # 기본 15초
  evaluation_interval: 15s       # 룰 평가 15초
  scrape_timeout: 10s           # 타임아웃 10초

# 메모리 설정
prometheus \
  --storage.tsdb.path=/var/lib/prometheus/ \
  --storage.tsdb.retention.time=15d \
  --query.max-concurrency=20 \           # 동시 쿼리 수
  --query.timeout=2m \                    # 쿼리 타임아웃
  --web.max-connections=512 \            # 최대 연결 수
  --storage.tsdb.max-block-duration=31d  # 최대 블록 크기
```

---

## 참고 자료

- **공식 문서**: https://prometheus.io/docs/
- **GitHub**: https://github.com/prometheus/prometheus
- **Exporter 카탈로그**: https://prometheus.io/docs/instrumenting/exporters/

---

