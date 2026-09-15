---
title: 캐시 모니터링 실무
tags: [redis, cache, monitoring, observability, backend, performance]
updated: 2026-09-15
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

## Redis INFO stats 해석

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
4. 연결 수 (rejected_connections 포함)
5. 엔드포인트별 hit/miss 분포 (하단, 애플리케이션 메트릭)

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

## 알림 임계값 설정

운영하면서 쓰는 임계값이다. 서비스 특성마다 다르므로 절대적인 수치는 아니다.

| 메트릭 | warning | critical | 비고 |
|---|---|---|---|
| hit ratio (5m) | < 75% | < 60% | 최초 설정은 평상시 값의 -15%, -25% |
| eviction 발생률 | > 10/min | > 100/min | 0이 정상. 발생 자체가 경고 신호 |
| mem_fragmentation_ratio | > 1.5 | > 2.0 | 1.0 미만도 critical |
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
```

`for: 5m`은 5분 이상 지속될 때만 알림을 보낸다는 뜻이다. 순간적인 스파이크로 새벽에 호출되는 걸 막기 위해서다. eviction은 1분으로 짧게 잡는다. 발생 자체가 심각하기 때문이다.
