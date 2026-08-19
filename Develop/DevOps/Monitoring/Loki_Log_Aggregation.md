---
title: Loki 수집 구성과 운영
tags: [monitoring, observability, devops]
updated: 2026-07-31
---

# Loki 수집 구성과 운영

> 이 문서는 **로그를 어떻게 받아서 굴리는가**를 다룬다 — Promtail 설정, pipeline_stages, 스토리지·보존·멀티테넌시. 무엇을 레이블로 삼을지와 카디널리티가 터졌을 때의 대응은 [레이블 설계와 카디널리티](Loki_레이블_설계와_카디널리티.md)에 있다.


Loki는 Prometheus와 동일한 레이블 모델을 로그에 적용한다. 로그 내용 자체를 인덱싱하지 않고 레이블만 인덱싱하기 때문에 Elasticsearch에 비해 인덱스 크기가 훨씬 작다. 대신 LogQL로 쿼리할 때 로그 내용 검색은 전체 청크를 읽어 필터링하므로, 레이블 선택자를 얼마나 잘 쓰느냐가 쿼리 성능에 직결된다.

## 아키텍처 개요

```
애플리케이션 → Promtail → Loki → Grafana
```

Promtail은 로컬 파일을 tail하거나 systemd 저널을 읽어 Loki로 전송한다. Kubernetes 환경에서는 DaemonSet으로 배포해 노드의 `/var/log/pods/` 경로를 수집한다. Loki는 수신한 로그를 청크 단위로 묶어 오브젝트 스토리지(S3, GCS 등)에 저장하고, 인덱스만 로컬 혹은 별도 테이블(BoltDB, DynamoDB 등)에 유지한다.

## Promtail 설정

### 기본 구조

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: backend-api
    static_configs:
      - targets:
          - localhost
        labels:
          job: backend-api
          env: production
          __path__: /var/log/backend/*.log
```

`positions.yaml`은 Promtail이 어느 위치까지 읽었는지 기록하는 파일이다. 컨테이너를 재시작했을 때 이 파일이 사라지면 로그를 처음부터 다시 읽는다. 볼륨 마운트로 영속화하지 않으면 재시작할 때마다 로그가 중복으로 들어온다.

### Kubernetes 환경 설정

```yaml
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    pipeline_stages:
      - docker: {}
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_container_name]
        target_label: container
      - replacement: /var/log/pods/*$1/*.log
        separator: /
        source_labels:
          - __meta_kubernetes_pod_uid
          - __meta_kubernetes_pod_container_name
        target_label: __path__
```

`relabel_configs`에서 `__meta_kubernetes_*` 레이블을 실제 레이블로 변환한다. `__path__`는 수집할 파일 경로를 지정하는 특수 레이블이다.

## pipeline_stages로 로그 파싱

pipeline_stages는 Promtail이 로그 라인을 수집한 후 Loki로 전송하기 전에 처리하는 파이프라인이다. 주요 용도는 구조화된 로그에서 레이블 추출, 타임스탬프 파싱, 로그 레벨 분류다.

### JSON 로그 파싱

스프링 부트나 Node.js에서 JSON 형식으로 로그를 출력하는 경우가 많다.

```yaml
pipeline_stages:
  - json:
      expressions:
        level: level
        traceId: traceId
        message: message
        duration: duration
  - labels:
      level:
      traceId:
  - timestamp:
      source: timestamp
      format: RFC3339Nano
```

`json` 스테이지로 필드를 추출하고, `labels` 스테이지에서 레이블로 승격시킨다. **레이블 카디널리티 문제에 주의해야 한다.** `traceId`처럼 값이 무한히 다양한 필드를 레이블로 만들면 Loki 인덱스가 폭발적으로 커진다. traceId는 레이블이 아니라 로그 내용으로 검색해야 한다.

```yaml
# 잘못된 예 - 카디널리티 폭발
- labels:
    traceId:
    userId:
    requestId:

# 올바른 예 - 카디널리티가 낮은 필드만 레이블로
- labels:
    level:
    service:
    env:
```

### regex 파싱

JSON이 아닌 일반 텍스트 로그는 regex로 파싱한다.

```yaml
pipeline_stages:
  - regex:
      expression: '(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>\w+) (?P<message>.*)'
  - labels:
      level:
  - timestamp:
      source: timestamp
      format: "2006-01-02 15:04:05"
```

Go의 time 패키지 형식을 사용한다. `2006-01-02 15:04:05`는 Go 기준 시각으로, 자바의 `yyyy-MM-dd HH:mm:ss`에 해당한다.

### multiline 처리

Java 스택 트레이스처럼 여러 줄에 걸친 로그를 하나의 로그 엔트리로 합쳐야 할 때 `multiline` 스테이지를 쓴다.

```yaml
pipeline_stages:
  - multiline:
      firstline: '^\d{4}-\d{2}-\d{2}'
      max_wait_time: 3s
      max_lines: 128
```

`firstline` 패턴에 매칭되는 줄이 새 로그 엔트리의 시작이다. `max_wait_time`이 지나거나 `max_lines`에 도달하면 강제로 플러시한다. 스택 트레이스가 128줄을 넘으면 잘리므로 운영 환경에서 값을 조정해야 한다.

### match 스테이지로 조건부 파이프라인

특정 조건에 맞는 로그에만 다른 처리를 적용할 때 사용한다.

```yaml
pipeline_stages:
  - json:
      expressions:
        level: level
  - match:
      selector: '{job="backend-api"}'
      stages:
        - json:
            expressions:
              httpMethod: httpMethod
              httpPath: httpPath
              duration: duration
        - labels:
            httpMethod:
```

## LogQL 쿼리 작성

LogQL은 두 부분으로 구성된다. 로그 스트림 선택자와 파이프라인이다.

```
{레이블 선택자} | 파이프라인
```

### 로그 스트림 선택자

레이블로 로그 스트림을 좁힌다. 선택자가 넓을수록 읽어야 할 청크가 많아져 쿼리가 느려진다.

```logql
# 특정 서비스의 에러 로그
{app="order-service", env="production", level="error"}

# 연산자: =, !=, =~(정규식), !~(정규식 제외)
{app=~"order-.*", env="production"}
{namespace="backend", container!="sidecar"}
```

### filter expression

스트림 선택자로 걸러낸 로그를 내용으로 추가 필터링한다.

```logql
# 문자열 포함
{app="api"} |= "ERROR"

# 문자열 제외
{app="api"} != "health-check"

# 정규식
{app="api"} |~ "timeout|connection refused"

# 정규식 제외
{app="api"} !~ "DEBUG|TRACE"

# 조합
{app="api"} |= "ERROR" != "expected error"
```

### label filter

파싱된 레이블 값으로 필터링한다. `json` 또는 `regex` 파이프라인 스테이지 이후에 사용한다.

```logql
# JSON 파싱 후 duration 필드로 필터
{app="api"} | json | duration > 1000

# 문자열 레이블 필터
{app="api"} | json | level="error"

# 복합 조건
{app="api"} | json | duration > 500 | level!="debug"
```

### 파싱 파이프라인 내장

Promtail에서 파싱하지 않고 쿼리 시점에 파싱할 수도 있다.

```logql
# JSON 파싱
{app="api"} | json | line_format "{{.level}} {{.message}}"

# logfmt 파싱
{app="api"} | logfmt | duration > 200ms

# regex 파싱
{app="api"} | regexp "(?P<status>\\d{3}) (?P<path>/\\S+)"
```

## 실무에서 자주 쓰는 쿼리 패턴

### 에러 집계

특정 시간 동안 서비스별 에러 수를 집계한다.

```logql
# 5분 단위 에러 발생 수 (메트릭 쿼리)
sum by (app) (
  count_over_time({env="production", level="error"}[5m])
)

# 에러 비율 계산
sum by (app) (rate({env="production", level="error"}[5m]))
/
sum by (app) (rate({env="production"}[5m]))
```

`count_over_time`은 지정한 범위 내 로그 라인 수를 반환한다. `rate`는 초당 평균으로 환산한다. Grafana에서 시계열 그래프로 그릴 때 `rate`를 쓰는 게 일반적이다.

### 응답시간 추출

JSON 로그에서 duration 필드를 추출해 분위수를 계산한다.

```logql
# 응답시간 분위수
quantile_over_time(0.95,
  {app="order-service"} | json | unwrap duration [5m]
) by (app)

# 평균 응답시간
avg_over_time(
  {app="order-service"} | json | unwrap duration [1m]
) by (app)
```

`unwrap`은 레이블 값을 숫자형으로 변환해 메트릭 함수에 쓸 수 있게 한다. duration이 밀리초 단위 숫자로 로그에 찍혀 있어야 동작한다. 단위 변환이 필요하면 `unwrap duration | __error__=""` 이후 `/ 1000` 같은 추가 연산을 붙인다.

```logql
# HTTP 상태 코드별 p99 응답시간
quantile_over_time(0.99,
  {app="api"} | json | unwrap responseTime [5m]
) by (statusCode)
```

### correlationId로 요청 추적

분산 시스템에서 특정 요청을 전체 서비스에 걸쳐 추적할 때 쓴다.

```logql
# 특정 traceId를 가진 로그 전체
{env="production"} |= "trace-id-abc123"

# JSON에서 traceId 파싱 후 필터
{env="production"} | json | traceId="trace-id-abc123"

# correlationId로 여러 서비스 로그를 한 번에 보기
{env="production", app=~"order-service|payment-service|inventory-service"}
  | json
  | correlationId="req-20240115-xyz"
```

Grafana에서 Explore 화면을 열고 로그 라인 클릭 시 correlationId 값으로 바로 쿼리를 실행하는 파생 쿼리를 설정해 놓으면 편하다. Grafana의 "Data links" 기능으로 Loki 쿼리 링크를 만들 수 있다.

### 특정 시간대 로그 추출

인시던트 발생 시점 전후 로그를 추출할 때 쓴다.

```logql
# 특정 경로에 대한 5xx 에러
{app="api"} | json | status >= 500 | path="/api/orders"

# 에러 메시지 패턴별 집계
sum by (errorCode) (
  count_over_time(
    {app="api"} | json | level="error" [10m]
  )
)
```

## Loki 스토리지 구성 시 주의사항

### 청크 설정

```yaml
chunk_store_config:
  max_look_back_period: 0s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: s3
      schema: v11
      index:
        prefix: loki_index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/index_cache
    shared_store: s3
  aws:
    s3: s3://my-loki-bucket
    region: ap-northeast-2
```

`period: 24h`는 인덱스를 24시간 단위로 분리 저장한다는 의미다. 보존 기간이 30일이면 30개의 인덱스 파일이 생긴다. 운영 중에 스키마를 변경하면 새 스키마는 `from` 날짜 이후 데이터에만 적용된다. 과거 데이터는 구 스키마로 읽어야 하므로 두 스키마를 동시에 지원해야 한다.

### 보존 기간 설정

```yaml
limits_config:
  retention_period: 720h  # 30일

compactor:
  working_directory: /loki/compactor
  shared_store: s3
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
```

`retention_enabled: true`와 `retention_period` 설정을 동시에 해야 실제로 오래된 데이터가 삭제된다. Compactor가 인덱스를 압축하고 보존 기간을 초과한 청크를 삭제하는 역할을 한다. Compactor를 별도로 실행하지 않으면 데이터가 계속 쌓인다.

### 인제스터 설정

```yaml
ingester:
  lifecycler:
    ring:
      replication_factor: 1
  chunk_idle_period: 30m
  chunk_retain_period: 1m
  max_chunk_age: 1h
  chunk_target_size: 1536000  # 1.5MB
```

`chunk_idle_period`는 새 로그가 들어오지 않을 때 청크를 플러시하는 대기 시간이다. 트래픽이 낮은 환경에서 이 값이 크면 로그 조회 시 청크가 아직 메모리에 있어 Loki 재시작 시 손실될 수 있다.

`chunk_target_size`는 청크 하나의 목표 크기다. 너무 작으면 S3에 작은 파일이 많이 생겨 API 호출 비용이 높아진다. 너무 크면 메모리 사용량이 늘어난다. 1MB~2MB가 일반적인 값이다.

### 쿼리 성능 문제

레이블을 너무 많이 만들거나 카디널리티가 높은 레이블을 쓸 때 주로 문제가 발생한다.

```yaml
limits_config:
  # 스트림 수 제한
  max_streams_per_user: 10000
  
  # 쿼리 타임아웃
  query_timeout: 1m
  
  # 반환할 최대 엔트리 수
  max_entries_limit_per_query: 5000
  
  # 청크 저장소 쿼리 제한
  max_chunks_per_query: 2000000
```

`max_chunks_per_query` 초과 오류가 자주 발생하면 스트림 선택자가 너무 넓은 것이다. 레이블을 더 세분화하거나 시간 범위를 줄여야 한다.

Grafana에서 Loki 쿼리가 느릴 때는 먼저 Explore 탭에서 쿼리 결과의 "Query Inspector"를 열어 실제로 몇 개의 청크를 읽었는지 확인한다. 청크 수가 수만 개를 넘어가면 레이블 설계를 다시 검토해야 한다.

### 멀티테넌시

단일 Loki 인스턴스를 여러 팀이 공유하는 경우 테넌트 ID로 격리할 수 있다.

```yaml
auth_enabled: true
```

Promtail에서 테넌트 ID를 설정한다.

```yaml
clients:
  - url: http://loki:3100/loki/api/v1/push
    tenant_id: team-backend
```

`auth_enabled: false`이면 테넌트 ID 없이 모든 로그가 `fake` 테넌트 하나에 저장된다. 개발 환경에서는 `false`로 놓고 쓰는 경우가 많지만, 운영 환경에서 여러 프로젝트가 공유하면 격리가 필요하다.
