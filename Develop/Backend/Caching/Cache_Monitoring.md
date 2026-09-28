---
title: 캐시 모니터링 실무
tags: [redis, cache, monitoring, observability, backend, performance]
updated: 2026-09-28
---

# 캐시 모니터링 실무

캐시가 제대로 동작하는지 확인할 방법 없이 운영하다 보면, 어느 날 DB 커넥션 풀이 가득 차서야 캐시가 죽어있었다는 걸 알게 된다. hit ratio가 30% 아래로 내려가도 에러는 나지 않는다. 느려질 뿐이다. 그 느림은 원인을 모르는 상태에서 DB 쿼리 최적화로 삽질하게 만든다.

## hit ratio 계산

Redis는 인스턴스 시작 이후 누적 통계를 `INFO stats`에 담는다.

```bash
redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
keyspace_hits:1247893
keyspace_misses:234561
```

hit ratio 계산은 단순하다.

```
hit ratio = keyspace_hits / (keyspace_hits + keyspace_misses)
```

문제는 이 수치가 인스턴스 전체 누적이라는 점이다. 새벽에 배치가 캐시를 워밍했고 낮 피크에 트래픽이 몰렸다면, 전체 hit ratio는 실제 서비스 품질과 동떨어진 숫자가 된다.

더 심각한 건 API별 편차다. 상품 상세 페이지는 hit ratio 95%인데 추천 목록은 20%일 수 있다. 전체 평균 70%는 두 API 모두 '보통'으로 보이게 만든다.

### 전체 hit ratio vs 엔드포인트별

전체 hit ratio는 대세를 보는 용도다. 갑자기 60%에서 40%로 내려갔다면 뭔가 달라진 게 있다는 신호다. 어디서 문제가 생겼는지는 이 수치만으로 알 수 없다.

엔드포인트별 hit ratio는 애플리케이션 레이어에서 계산해야 한다. Redis 자체는 어느 엔드포인트가 요청했는지 모른다.

Spring Boot에서 Micrometer로 엔드포인트별 hit/miss를 추적하는 방식이다.

```java
@Component
public class CacheMetrics {
    private final MeterRegistry registry;
    private final Map<String, Counter> hitCounters = new ConcurrentHashMap<>();
    private final Map<String, Counter> missCounters = new ConcurrentHashMap<>();

    public CacheMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    public void recordHit(String cacheName, String endpoint) {
        hitCounters.computeIfAbsent(
            cacheName + ":" + endpoint,
            k -> Counter.builder("cache.requests")
                .tag("cache", cacheName)
                .tag("endpoint", endpoint)
                .tag("result", "hit")
                .register(registry)
        ).increment();
    }

    public void recordMiss(String cacheName, String endpoint) {
        missCounters.computeIfAbsent(
            cacheName + ":" + endpoint,
            k -> Counter.builder("cache.requests")
                .tag("cache", cacheName)
                .tag("endpoint", endpoint)
                .tag("result", "miss")
                .register(registry)
        ).increment();
    }
}
```

이걸 `@Cacheable`이 붙은 메서드 앞뒤에 AOP로 감싸거나, 캐시 구현체의 `get`/`put` 호출 지점에 심는다.

## Redis INFO 주요 수치

`INFO stats` 외에도 봐야 하는 항목들이 있다.

```bash
redis-cli INFO all
```

주요 수치:

```
# Memory
used_memory_human:1.23G
maxmemory_human:2.00G
mem_fragmentation_ratio:1.34

# Stats
keyspace_hits:1247893
keyspace_misses:234561
evicted_keys:0
expired_keys:892341
rejected_connections:0

# Keyspace
db0:keys=48291,expires=41823,avg_ttl=3601000
```

**mem_fragmentation_ratio**: 1.0~1.5가 정상이다. 1.5를 넘으면 메모리 단편화가 심한 것이고, 1.0 미만이면 swap을 쓰고 있다는 뜻이다. 둘 다 성능에 직접 영향을 준다.

**evicted_keys**: 0이 아니면 maxmemory에 도달해서 키를 강제 삭제하고 있다는 뜻이다. maxmemory-policy 설정에 따라 어떤 키가 날아가는지 다르지만, eviction이 발생한다는 건 캐시가 원하는 데이터를 갖고 있지 못하다는 거다.

**expired_keys**: TTL이 다 된 키의 누적 삭제 수다. 이 자체는 문제가 아니다. 짧은 시간에 급증한다면 TTL 집중 만료가 발생한 것이다.

**rejected_connections**: 0이 아니면 maxclients 한도에 걸렸다는 뜻이다. 이 상태에서는 새 요청이 Redis에 아예 연결되지 못한다.

## 연결 수 모니터링

connected_clients는 생각보다 자주 문제를 일으킨다. 애플리케이션이 connection pool을 제대로 반납하지 않거나, 배포 중에 구버전과 신버전이 동시에 떠있을 때 연결 수가 급증한다.

```bash
redis-cli INFO clients
```

```
connected_clients:1234
maxclients:10000
client_recent_max_input_buffer:24936
client_recent_max_output_buffer:0
blocked_clients:5
```

connected_clients가 maxclients의 80% 이상에 도달하면 경고다. 100%가 되는 순간 새 연결을 거부한다.

`blocked_clients`가 증가하고 있다면 BLPOP, BRPOP 같은 블로킹 명령어를 쓰는 클라이언트가 대기 중인 것이다. 큐 소비가 느려졌거나 컨슈머에 문제가 생긴 경우다.

Prometheus에서 연결 수 비율을 추적하는 쿼리다.

```promql
redis_connected_clients / redis_config_maxclients
```

이 값이 0.8을 넘으면 warning, 0.95를 넘으면 즉시 확인이 필요하다.

## slowlog 분석

Redis는 싱글 스레드 모델이라 명령 하나가 느리면 그 뒤로 오는 요청이 전부 대기한다. hit ratio와 무관하게 응답 시간이 튀는 상황이 발생한다면 slowlog부터 본다.

```bash
# 현재 임계값 확인 (단위: 마이크로초)
redis-cli CONFIG GET slowlog-log-slower-than
# 기본값: 10000 (= 10ms)

# 저장 개수 확인
redis-cli CONFIG GET slowlog-max-len
# 기본값: 128

# slowlog에 쌓인 항목 수
redis-cli SLOWLOG LEN

# 최근 10개 조회
redis-cli SLOWLOG GET 10
```

SLOWLOG GET 출력은 다음 형식이다.

```
1) 1) (integer) 142             # 고유 ID
   2) (integer) 1726123456      # 타임스탬프 (unix)
   3) (integer) 15234           # 실행 시간 (마이크로초)
   4) 1) "SMEMBERS"             # 명령어
      2) "user:tags:9012"       # 인자
   5) "10.0.1.23:52341"         # 클라이언트 주소
   6) ""                        # 클라이언트 이름
```

실행 시간이 마이크로초 단위라는 걸 잊지 않는 게 중요하다. 15234는 15.2ms다.

slowlog에서 SMEMBERS, LRANGE, KEYS, HGETALL 같은 명령이 자주 보인다면 set이나 list에 원소가 너무 많이 쌓인 것이다. KEYS는 프로덕션에서 절대 쓰면 안 된다. 전체 키스페이스를 순회해서 수백만 개의 키가 있으면 Redis가 수초간 멈춘다.

임계값을 낮춰서 더 많은 slowlog를 잡고 싶을 때는 `CONFIG SET`으로 변경한다.

```bash
# 5ms 이상인 명령을 기록
redis-cli CONFIG SET slowlog-log-slower-than 5000

# 이전 slowlog 초기화
redis-cli SLOWLOG RESET
```

SLOWLOG RESET은 원인 파악 전에 하면 안 된다. 먼저 SLOWLOG GET으로 내용을 저장해두고 초기화한다.

## LATENCY 히스토리

LATENCY는 slowlog와 다르게 이벤트 유형별로 지연을 추적한다. Redis 내부 이벤트(AOF 쓰기, fork, RDB 저장 등)의 지연을 잡을 때 유용하다.

기본적으로 비활성 상태다. 임계값을 설정해야 기록을 시작한다.

```bash
# 100ms 이상 지연 이벤트 기록
redis-cli CONFIG SET latency-monitor-threshold 100

# 최근 발생한 이벤트 목록
redis-cli LATENCY LATEST
```

```
1) 1) "command"               # 이벤트 유형
   2) (integer) 1726123890    # 마지막 발생 타임스탬프
   3) (integer) 234           # 마지막 지연 (ms)
   4) (integer) 512           # 최대 지연 (ms)
```

특정 이벤트의 시계열 히스토리는 LATENCY HISTORY로 조회한다.

```bash
redis-cli LATENCY HISTORY command
```

LATENCY LATEST에서 볼 수 있는 이벤트 유형들이다.

| 이벤트 | 의미 |
|---|---|
| command | 명령 처리 지연 |
| fast-command | O(1) 명령 지연 (이게 느리면 심각) |
| aof-stat | AOF 쓰기 지연 |
| rdb-unlink-temp-file | RDB 파일 삭제 지연 |
| fork | BGSAVE/BGREWRITEAOF 중 fork() 호출 지연 |

`fork` 지연이 높다면 BGSAVE나 BGREWRITEAOF가 느린 것이다. Copy-on-Write 때문에 메모리 사용량이 많을수록 fork 시간이 길어진다. 메모리 4GB 인스턴스에서 BGSAVE가 2초 걸리는 경우가 있었다. 그 2초 동안 Redis는 다른 클라이언트 요청도 처리하지만, fork 자체는 메인 스레드를 잠깐 멈춘다.

LATENCY 히스토리를 초기화하려면:

```bash
redis-cli LATENCY RESET
redis-cli LATENCY RESET command  # 특정 이벤트만
```

## big key 감지

big key는 두 가지 문제를 만든다. 하나는 그 키를 접근할 때 Redis가 오래 잡혀있는 것이고, 다른 하나는 그 키 때문에 메모리를 예상보다 훨씬 많이 쓰는 것이다.

### redis-cli --bigkeys

```bash
redis-cli --bigkeys
```

출력 예시:

```
Biggest string found so far '"product:cache:9012"' with 45678 bytes
Biggest hash   found so far '"user:profile:8834"' with 1234 fields

-------- summary -------
Sampled 48291 keys in the keyspace!
Biggest string found '"product:cache:9012"' has 45678 bytes
Biggest hash   found '"user:profile:8834"' has 1234 fields
```

프로덕션에서 실행하면 전체 키를 SCAN으로 순회하기 때문에 CPU 부하가 생긴다. `-i 0.1` 옵션을 붙이면 100번의 SCAN 호출마다 100ms씩 쉬어가며 부하를 줄인다.

```bash
redis-cli --bigkeys -i 0.1
```

키 수백만 개 이상인 인스턴스는 새벽 트래픽 최저점에 실행하거나 읽기 전용 복제본에서 실행한다.

### MEMORY USAGE

특정 키의 메모리 사용량을 정확히 재려면 MEMORY USAGE를 쓴다.

```bash
# 기본 사용량 (바이트)
redis-cli MEMORY USAGE product:cache:9012

# SAMPLES 0은 중첩 구조를 전체 탐색 (기본값 5는 샘플 기반 추정)
redis-cli MEMORY USAGE user:profile:8834 SAMPLES 0
```

`SAMPLES 0`은 정확하지만 원소가 많은 hash나 set에서는 느릴 수 있다.

### SCAN + OBJECT ENCODING

특정 패턴의 키들이 어떤 인코딩을 쓰고 있는지 확인할 때 쓴다.

```bash
# cursor 0에서 시작, 100개씩 스캔
redis-cli SCAN 0 MATCH "session:*" COUNT 100

# 특정 키의 내부 인코딩
redis-cli OBJECT ENCODING session:user:1234
```

인코딩이 바뀌는 지점이 메모리 사용량이 급증하는 지점이다.

| 자료형 | 압축 인코딩 | 해제 인코딩 |
|---|---|---|
| hash | listpack | hashtable |
| zset | listpack | skiplist |
| set | listpack / intset | hashtable |
| list | listpack | quicklist |

hash가 listpack에서 hashtable로 전환되는 임계값은 `hash-max-listpack-entries` (기본 128)다. 이 값 근처의 hash들은 원소 하나 추가로 메모리가 수배 늘어날 수 있다.

big key를 발견했을 때 처방은 키 분산이다. `product:cache:9012` 하나에 전체 상품 정보를 담는 대신 `product:cache:9012:meta`, `product:cache:9012:images`, `product:cache:9012:stock`으로 쪼갠다.

## Prometheus + Grafana 구성

### redis_exporter 설치

```yaml
# docker-compose.yml
services:
  redis-exporter:
    image: oliver006/redis_exporter:v1.55.0
    environment:
      REDIS_ADDR: redis://redis:6379
    ports:
      - "9121:9121"
```

redis_exporter가 `/metrics` 엔드포인트에서 Redis INFO의 모든 값을 Prometheus 형식으로 변환한다.

### Prometheus 설정

```yaml
scrape_configs:
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 15s
```

### hit ratio 계산 쿼리

```promql
# 전체 hit ratio (5분 이동 구간)
rate(redis_keyspace_hits_total[5m]) /
(rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
```

`rate()`를 쓰는 이유는 누적 카운터를 초당 증가율로 변환해서 시간 축으로 비교 가능하게 만들기 위해서다. 그냥 카운터 값을 쓰면 인스턴스 재시작 전후로 값이 튀어서 그래프가 엉망이 된다.

eviction 모니터링:

```promql
# eviction 발생률 (5분 기준)
rate(redis_evicted_keys_total[5m])

# expired_keys 변화율
rate(redis_expired_keys_total[5m])
```

### Grafana 패널 구성

패널은 이 순서로 배치한다.

1. hit ratio 시계열 (상단, 크게)
2. eviction/expired 비율 (중단)
3. 메모리 사용량과 단편화 비율 (중단)
4. connected_clients / maxclients 비율
5. blocked_clients 추이
6. 엔드포인트별 hit/miss 분포 (하단, 애플리케이션 메트릭)

hit ratio 패널에는 임계선을 같이 그린다.

```
Grafana → Panel → Thresholds:
  75% → yellow
  60% → red
```

선이 빨간 영역으로 들어오면 눈으로 바로 보인다. 숫자만 보는 것과 차이가 크다.

## 이상 패턴 감지

### eviction 급증

eviction은 서서히 늘지 않는다. 갑자기 터진다. maxmemory에 도달하는 순간부터 요청마다 키를 날리기 시작하기 때문이다.

```promql
# eviction이 분당 100건 이상 발생하면 발동
increase(redis_evicted_keys_total[1m]) > 100
```

eviction이 발생하면 hit ratio가 동시에 떨어진다. 두 그래프가 같은 시점에 움직인다면 메모리 부족이 원인이다. hit ratio만 떨어지고 eviction은 없다면 TTL 만료나 캐시 무효화 쪽을 봐야 한다.

### TTL 집중 만료

같은 시간에 캐시를 채웠고 TTL을 동일하게 설정했다면, TTL 만료도 같은 시간에 몰린다. 트래픽 피크와 TTL 만료가 겹치면 DB에 순간적으로 요청이 쏠린다. thundering herd라고 부른다.

expired_keys 변화율 그래프에서 뾰족하게 솟아오르는 구간이 있다면 이 패턴이다.

```bash
# Redis의 lazy expiration 설정 확인
redis-cli CONFIG GET lazyfree-lazy-expire
# 기본값은 no (동기 삭제)
```

TTL에 랜덤 지터를 추가하는 게 기본 처방이다.

```java
// TTL 고정
redisTemplate.expire(key, Duration.ofSeconds(3600));

// TTL 지터 추가 (±10%)
long baseTtl = 3600;
long jitter = (long) (baseTtl * 0.1 * Math.random());
redisTemplate.expire(key, Duration.ofSeconds(baseTtl + jitter));
```

## hit ratio 하락 시 디버깅 순서

hit ratio 하락 알림이 왔을 때 바로 DB를 의심하거나 캐시 코드를 뜯어보기 전에, 다음 순서로 Redis 상태를 먼저 확인한다.

**1단계: eviction 발생 여부**

```bash
redis-cli INFO stats | grep evicted_keys
```

`evicted_keys`가 증가하고 있다면 maxmemory 한도에 걸린 것이다. hit ratio 하락이 eviction과 시간이 겹친다면 여기서 원인이 결정된다. `INFO memory`로 현재 메모리 사용량을 확인하고, 필요하면 maxmemory를 늘리거나 maxmemory-policy를 검토한다.

eviction이 없다면 2단계로 넘어간다.

**2단계: slowlog 확인**

```bash
redis-cli SLOWLOG LEN
redis-cli SLOWLOG GET 20
```

특정 명령이 반복적으로 나타난다면 그 키나 자료형이 문제다. SMEMBERS, LRANGE, HGETALL은 원소 수에 비례해 느려진다. 이 명령들이 slowlog에 자주 보인다면 big key 확인으로 넘어간다.

slowlog가 깨끗하다면 3단계로 넘어간다.

**3단계: big key 확인**

```bash
redis-cli --bigkeys -i 0.1
```

예상보다 큰 키가 있다면 해당 키에 접근하는 요청이 Redis를 오래 잡고 있는 것이다. MEMORY USAGE로 정확한 크기를 확인하고 키 분산을 검토한다.

big key 문제가 없다면 4단계로 넘어간다.

**4단계: TTL 분포 확인**

```bash
redis-cli INFO keyspace
```

```
db0:keys=48291,expires=41823,avg_ttl=3601000
```

`avg_ttl`이 급격히 낮아졌다면 곧 대규모 만료가 예정된 상황이다. `expires` 비율이 높은데 `avg_ttl`이 낮다면 특정 시점에 TTL이 집중된 것이다.

더 정밀하게 TTL 분포를 보려면 SCAN으로 키를 샘플링하고 TTL을 확인한다.

```bash
# 샘플 100개의 TTL 분포 확인
redis-cli SCAN 0 COUNT 100 | tail -n +2 | while read key; do
  redis-cli TTL "$key"
done | sort -n | uniq -c
```

TTL이 특정 값에 몰려있다면 jitter 적용이 필요하다.

이 4단계를 다 거쳐도 원인이 안 잡힌다면, 애플리케이션 레이어에서 캐시 무효화 로직 변경이나 최근 배포 이력을 확인한다.

## 알림 임계값 설정

운영하면서 쓰는 임계값이다. 서비스 특성마다 다르므로 절대적인 수치는 아니다.

| 메트릭 | warning | critical | 비고 |
|---|---|---|---|
| hit ratio (5m) | < 75% | < 60% | 최초 설정은 평상시 값의 -15%, -25% |
| eviction 발생률 | > 10/min | > 100/min | 0이 정상. 발생 자체가 경고 신호 |
| mem_fragmentation_ratio | > 1.5 | > 2.0 | 1.0 미만도 critical |
| connected_clients 비율 | > 80% | > 95% | maxclients 대비 |
| blocked_clients | > 10 | > 50 | 블로킹 명령 대기 |
| rejected_connections | > 0 | > 10 | - |
| expired_keys 변화율 | 평소 3배 | 평소 5배 | 절대값보다 상대 변화 기준이 유용 |

critical이 떴을 때 대응 순서:

1. eviction이 발생 중이면 메모리 확인 먼저. maxmemory 조정 또는 키 분산이 필요하다.
2. hit ratio만 떨어졌으면 최근 배포나 TTL 설정 변경 이력을 본다.
3. rejected_connections가 있으면 maxclients와 connection pool 설정을 점검한다.

Alertmanager 룰 예시:

```yaml
groups:
  - name: redis
    rules:
      - alert: RedisCacheHitRatioLow
        expr: |
          rate(redis_keyspace_hits_total[5m]) /
          (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) < 0.75
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis hit ratio {{ $value | humanizePercentage }}"

      - alert: RedisEvictionHigh
        expr: rate(redis_evicted_keys_total[1m]) > 100
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis eviction rate {{ $value }}/min"

      - alert: RedisConnectionsHigh
        expr: redis_connected_clients / redis_config_maxclients > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis connections at {{ $value | humanizePercentage }} of max"
```

`for: 5m`은 5분 이상 지속될 때만 알림을 보낸다는 뜻이다. 순간적인 스파이크로 새벽에 호출되는 걸 막기 위해서다. eviction은 1분으로 짧게 잡는다. 발생 자체가 심각하기 때문이다.
