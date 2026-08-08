---
title: Noisy Neighbor
tags: [architecture, kubernetes, performance]
updated: 2026-08-04
---

# Noisy Neighbor

공유 인프라에서 특정 테넌트가 리소스를 과도하게 소비해 같은 호스트에 있는 다른 테넌트 성능이 떨어지는 현상이다. 멀티테넌트 SaaS에서 가장 흔하게 마주치는 운영 문제 중 하나인데, 문제를 일으키는 테넌트는 자기가 문제를 일으키는지조차 모르는 경우가 대부분이다.

## 리소스 유형별 발생 양상

### CPU

배치 작업이나 대용량 리포트 집계를 돌리는 테넌트가 CPU를 순간적으로 포화시키면, 같은 노드에 있는 다른 파드의 응답 지연이 수백 ms 단위로 튄다. CPU는 공유 자원이기 때문에 throttling이 발생하기 전까지 OS 스케줄러가 제어한다. Kubernetes에서 `limits.cpu`를 설정하지 않으면 파드가 노드의 여유 CPU를 전부 먹을 수 있다.

CFS(Completely Fair Scheduler) 기반 throttling이 걸리면 `/sys/fs/cgroup/cpu/cpu.stat`에서 `throttled_time`이 증가하는 걸 확인할 수 있다. 애플리케이션 P99 지연이 갑자기 오르는데 서비스 자체 처리량은 정상이면, 이 값을 먼저 보는 게 빠르다.

### 메모리

JVM 기반 서비스에서 특정 테넌트 요청이 대용량 데이터를 힙에 올리면 GC 압박이 생긴다. GC가 길게 돌면 STW(Stop-The-World) 구간 동안 같은 프로세스 내 다른 테넌트의 요청도 멈춘다. 단일 프로세스에서 여러 테넌트를 처리하는 구조라면 메모리 격리가 본질적으로 어렵다.

컨테이너 수준에서는 메모리 `limits`를 초과하면 OOMKilled가 발생한다. 문제는 OOM이 발생한 컨테이너의 다른 테넌트 요청도 함께 죽는다는 점이다. 메모리 사용이 많은 테넌트를 별도 파드로 격리하지 않으면 이 문제를 피하기 어렵다.

### I/O

디스크 I/O는 Kubernetes만으로 제어하기 까다롭다. 컨테이너 런타임이 blkio cgroup을 지원하더라도 실제 클라우드 환경에서 EBS 같은 네트워크 스토리지는 IOPS 한도를 볼륨 단위로 공유한다. 특정 테넌트가 대량 로그를 쓰거나 대용량 파일을 읽으면 같은 볼륨을 쓰는 다른 파드 전체의 I/O 레이턴시가 올라간다.

`iostat -x 1` 또는 `iotop`으로 디바이스 단위 utilization과 await 값을 보면 I/O 포화 상태를 빠르게 파악할 수 있다.

### DB 커넥션

RDS나 Aurora는 인스턴스 타입별로 max_connections 한도가 있다. 특정 테넌트가 커넥션 풀을 다 잡고 놓지 않으면 다른 테넌트는 커넥션 획득 대기 상태에 빠진다. 이 상태에서 타임아웃이 발생하면 DB 에러가 아닌 connection timeout 에러로 보이기 때문에 원인 파악이 늦어진다.

```sql
-- 테넌트별 DB 커넥션 점유 현황 (PostgreSQL)
SELECT
    usename,
    application_name,
    client_addr,
    state,
    COUNT(*) AS connection_count,
    MAX(EXTRACT(EPOCH FROM (now() - state_change))) AS max_idle_seconds
FROM pg_stat_activity
WHERE datname = 'your_database'
GROUP BY usename, application_name, client_addr, state
ORDER BY connection_count DESC;
```

PgBouncer 같은 커넥션 풀러를 쓰는 경우라면 `SHOW POOLS;` 명령으로 테넌트별 커넥션 풀 상태를 확인한다.

### 네트워크 대역폭

같은 노드에서 특정 파드가 대용량 데이터를 전송하면 노드 NIC 대역폭을 포화시켜 다른 파드의 패킷 손실과 재전송이 발생한다. Kubernetes는 네트워크 대역폭 QoS를 기본 제공하지 않아서, `kubernetes.io/egress-bandwidth` 어노테이션을 지원하는 CNI 플러그인이 필요하다.

## 탐지 방법

### 메트릭 기반 탐지

Prometheus에서 테넌트 ID를 레이블로 붙이면 테넌트별 리소스 사용량을 추적할 수 있다. CPU throttling 탐지 쿼리:

```promql
# 파드별 CPU throttling 비율
rate(container_cpu_cfs_throttled_periods_total[5m])
  / rate(container_cpu_cfs_periods_total[5m])
```

이 값이 특정 파드에서 0.3 이상으로 올라가면 CPU limits 설정이 실제 부하보다 낮게 잡혀 있다는 신호다.

메모리 압박 탐지:

```promql
# 컨테이너 메모리 사용률
container_memory_working_set_bytes
  / container_spec_memory_limit_bytes
```

0.85 이상이면 OOMKilled 위험 구간이다.

### 슬로우 쿼리 기반 탐지

특정 테넌트 요청이 DB를 오래 잡고 있는 경우 `pg_stat_statements`로 찾는다:

```sql
-- 최근 1시간 기준 총 실행 시간 상위 쿼리
SELECT
    query,
    calls,
    total_exec_time / 1000 AS total_sec,
    mean_exec_time / 1000 AS mean_sec,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

멀티테넌트 구조에서는 WHERE 조건에 tenant_id가 없는 쿼리가 풀 스캔을 타는 경우가 대표적인 원인이다.

## Kubernetes 격리

### ResourceQuota와 LimitRange

네임스페이스 단위로 테넌트를 격리할 때 ResourceQuota로 총량을 제한하고 LimitRange로 개별 파드의 상한을 강제한다.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    count/pods: "20"
```

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limitrange
  namespace: tenant-a
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: 512Mi
    defaultRequest:
      cpu: "100m"
      memory: 128Mi
    max:
      cpu: "2"
      memory: 4Gi
```

LimitRange를 설정하지 않으면 limits 없는 파드가 배포될 수 있고, 그 파드가 노드 리소스를 무제한으로 사용한다. requests만 있고 limits가 없는 파드는 Burstable QoS 클래스에 해당하며, 메모리 압박 시 Guaranteed 파드보다 먼저 축출된다.

### PriorityClass

중요도가 높은 테넌트(프리미엄 플랜)의 파드가 리소스 부족 상황에서 먼저 스케줄링되도록 PriorityClass를 설정한다.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: premium-tenant
value: 1000
globalDefault: false
description: "프리미엄 테넌트 파드 우선순위"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: standard-tenant
value: 100
globalDefault: true
```

파드 스펙에 `priorityClassName: premium-tenant`를 지정하면 스케줄러가 리소스 경합 시 이 파드를 먼저 배치하고, 필요한 경우 낮은 우선순위 파드를 축출(preempt)한다.

### Node Affinity와 전용 노드 풀

특정 대형 테넌트를 전용 노드에 격리하는 방법이 가장 확실하다. 노드에 taint를 걸고, 해당 테넌트 파드에만 toleration을 준다.

```yaml
# 노드 taint 설정 (kubectl)
# kubectl taint nodes node-1 tenant=enterprise-a:NoSchedule

# 파드 스펙
spec:
  tolerations:
  - key: "tenant"
    operator: "Equal"
    value: "enterprise-a"
    effect: "NoSchedule"
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: tenant
            operator: In
            values:
            - enterprise-a
```

비용이 올라가는 대신 noisy neighbor 문제가 근본적으로 차단된다. 엔터프라이즈 고객이 SLA를 요구하면 결국 이 방향으로 간다.

## DB 커넥션 풀 제한

PgBouncer를 테넌트별로 분리하거나, 단일 PgBouncer에서 `max_user_connections`를 설정해 테넌트별 커넥션 상한을 건다.

```ini
# pgbouncer.ini
[databases]
tenant_a = host=db port=5432 dbname=tenant_a pool_size=20 max_db_connections=20
tenant_b = host=db port=5432 dbname=tenant_b pool_size=10 max_db_connections=10

[pgbouncer]
max_client_conn = 500
default_pool_size = 20
pool_mode = transaction
```

공유 DB를 쓰면서 테넌트를 schema로 분리한 경우라면, 애플리케이션 레벨 커넥션 풀에서 테넌트별로 별도 DataSource를 만들고 풀 크기를 다르게 설정하는 방법도 있다.

```java
// Spring Boot + HikariCP 기준
HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:postgresql://db/mydb");
config.setMaximumPoolSize(planTier.equals("enterprise") ? 20 : 5);
config.setConnectionTimeout(3000);
HikariDataSource dataSource = new HikariDataSource(config);
```

## Rate Limiting

API 레이어에서 테넌트별 요청 수를 제한하는 게 CPU/네트워크 noisy neighbor를 막는 첫 번째 방어선이다. Redis를 사용한 슬라이딩 윈도우 Rate Limiter:

```python
import redis
import time

def check_rate_limit(tenant_id: str, limit: int, window_seconds: int) -> bool:
    r = redis.Redis()
    now = time.time()
    key = f"rate:{tenant_id}"
    
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds)
    results = pipe.execute()
    
    current_count = results[2]
    return current_count <= limit
```

플랜 등급별로 limit 값을 다르게 주면 프리미엄 테넌트는 더 많은 요청을 허용하면서 무료 플랜 테넌트의 과도한 요청은 429로 차단할 수 있다.

Nginx나 Envoy를 API Gateway로 쓰는 경우라면 테넌트 ID를 키로 한 rate limiting 설정이 더 간단하다.

```yaml
# Envoy rate limit descriptor
descriptors:
- key: tenant_id
  rate_limit:
    unit: MINUTE
    requests_per_unit: 1000
```

## 실제 트러블슈팅 사례

### 사례 1: 배치 리포트가 전체 API를 죽인 경우

한 테넌트가 월말 정산 리포트를 생성하는 배치를 오후 2시에 돌렸다. 이 배치가 DB에서 수백만 건의 트랜잭션을 집계하면서 RDS CPU를 95%까지 올렸다. 같은 DB를 쓰는 다른 테넌트의 일반 API 응답 지연이 200ms에서 8초로 튀었다.

원인은 집계 쿼리에 적절한 인덱스가 없어서 풀 스캔이 발생한 것이었다. 인덱스 추가 외에도, 배치 작업용 read replica를 별도로 두고 리포트 쿼리를 replica로 유도해서 프라이머리 DB 부하를 분리했다.

재발 방지로 배치 작업에는 `SET statement_timeout = '30s'`를 걸어서 단일 쿼리가 DB를 장시간 점유하지 못하게 했다.

### 사례 2: 파일 업로드로 네트워크 포화

스토리지 서비스를 공유하는 멀티테넌트 환경에서 특정 테넌트가 수십 GB 파일을 업로드하면서 같은 노드의 다른 서비스 네트워크 레이턴시가 급격히 올라갔다. `nethogs`로 프로세스별 네트워크 사용량을 보니 파일 업로드 처리 파드 하나가 NIC 대역폭의 80%를 사용하고 있었다.

해결은 업로드 처리 파드를 별도 노드 풀로 격리하고, 업로드 속도를 애플리케이션 레벨에서 제한하는 것이었다.

```python
# 업로드 속도 제한 (bytes/sec)
MAX_UPLOAD_RATE = 10 * 1024 * 1024  # 10MB/s per tenant

async def rate_limited_write(file_obj, data: bytes, tenant_id: str):
    chunk_size = 64 * 1024  # 64KB chunks
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        file_obj.write(chunk)
        await asyncio.sleep(chunk_size / MAX_UPLOAD_RATE)
```

### 사례 3: 커넥션 풀 고갈

트래픽이 많은 테넌트가 트랜잭션을 오래 열어두는 코드 버그가 있었다. 커넥션이 반환되지 않고 쌓이면서 커넥션 풀이 고갈되었고, 다른 테넌트 요청이 커넥션 대기 상태에서 타임아웃으로 실패했다.

`pg_stat_activity`에서 state가 `idle in transaction`인 커넥션이 수십 개 있는 걸 발견했다. `idle_in_transaction_session_timeout`을 DB 레벨에서 설정해서 오래된 유휴 트랜잭션을 자동으로 종료하게 했다.

```sql
-- postgresql.conf 또는 ALTER SYSTEM
ALTER SYSTEM SET idle_in_transaction_session_timeout = '60s';
SELECT pg_reload_conf();
```

## 격리 수준 선택 기준

| 상황 | 격리 방법 |
|---|---|
| 무료/소규모 테넌트 | ResourceQuota + LimitRange + Rate Limiting |
| 중간 규모 (성장 플랜) | 전용 네임스페이스 + 커넥션 풀 제한 |
| 대형/엔터프라이즈 | 전용 노드 풀 + 전용 DB 인스턴스 |
| SLA 보장 계약 | 완전 격리 (DB, 컴퓨팅, 네트워크 모두) |

격리 수준을 높일수록 인프라 비용이 올라간다. 무료 플랜 테넌트에게 전용 노드를 줄 수는 없으니, 플랜 등급별로 허용 리소스 한도를 설계하고 그에 맞는 격리 수준을 적용하는 게 현실적이다.

ResourceQuota와 Rate Limiting 없이 "일단 배포"하고 나면, 나중에 noisy neighbor 문제가 터진 다음에야 급하게 제한을 거는 상황이 된다. 이미 서비스 중인 환경에 갑자기 CPU limits를 걸면 기존에 limits 없이 돌던 파드들이 throttling 걸려서 장애가 날 수 있다. 처음부터 limits를 설계에 넣는 게 훨씬 수월하다.
