---
title: Redis 운영 — Persistence, Replication, Sentinel, Cluster
tags: [redis, cache, nosql, backend, performance, monitoring]
updated: 2026-08-18
---

# Redis 운영

## Persistence — RDB와 AOF

Redis는 메모리 데이터베이스라서 프로세스가 죽으면 데이터가 사라진다. Persistence를 설정하면 재시작 후 디스크에서 복구할 수 있다.

### RDB

특정 시점의 스냅샷을 `.rdb` 파일로 저장한다. `BGSAVE` 명령이 실행되면 Redis가 `fork()`로 자식 프로세스를 만들고 그 자식이 디스크에 쓴다. 부모는 계속 요청을 처리한다.

```conf
# redis.conf
save 900 1     # 900초 안에 1개 이상 변경되면 저장
save 300 10    # 300초 안에 10개 이상 변경되면 저장
save 60 10000  # 60초 안에 10000개 이상 변경되면 저장

dbfilename dump.rdb
dir /var/lib/redis
```

문제는 `fork()` 비용이다. 메모리가 30GB인 Redis에서 `fork()`를 호출하면 Linux가 Copy-on-Write 테이블을 복제하는 데만 수백 밀리초가 걸린다. 이 시간 동안 Redis가 멈춘다. 메모리 사용량이 클수록, 쓰기가 많을수록 fork() 비용이 올라간다. 레이턴시 스파이크의 원인을 찾다가 RDB 스냅샷이 주기적으로 이걸 유발하는 경우가 있다.

스냅샷 주기도 문제다. `save 300 10` 설정이면 최대 300초치 데이터가 손실될 수 있다.

### AOF

모든 쓰기 명령을 로그 파일에 순서대로 기록한다. 재시작하면 이 로그를 처음부터 재실행해 상태를 복원한다.

```conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec  # 1초마다 fsync
```

`appendfsync` 옵션이 핵심이다.

- `always`: 쓰기마다 fsync. 데이터 손실 없음. 처리량이 크게 떨어진다.
- `everysec`: 1초마다 fsync. 최대 1초 손실. 대부분의 경우 이 값을 쓴다.
- `no`: OS가 알아서 fsync. 빠르지만 손실 범위가 불명확하다.

AOF 파일은 계속 커진다. Redis는 `BGREWRITEAOF`로 현재 상태를 표현하는 최소 명령셋으로 파일을 재작성한다. 이 과정도 `fork()`를 쓴다.

```conf
auto-aof-rewrite-percentage 100  # 파일 크기가 기준치의 2배가 되면 rewrite
auto-aof-rewrite-min-size 64mb   # 최소 64MB 이상일 때만 rewrite
```

### 무엇을 선택할 것인가

캐시 전용이라면 Persistence 자체를 끄는 것이 맞다. 재시작하면 DB에서 다시 채우면 된다. 데이터 손실이 용납되지 않는다면 AOF `everysec`에 RDB를 병행한다. AOF는 복구 정밀도, RDB는 빠른 재시작 속도를 담당한다. AOF로만 복구하면 명령 재실행이라 큰 데이터셋은 시간이 오래 걸리는데, RDB는 바이너리 로드라 훨씬 빠르다.

```conf
# 둘 다 켠 경우 재시작 시 AOF를 우선 사용한다
# AOF 앞에 RDB 스냅샷을 임베드해 복구 속도를 높인다
aof-use-rdb-preamble yes
```

---

## Replication — Master-Replica 구성

단일 Redis 인스턴스는 장애 시 서비스가 멈춘다. Replica를 두면 Master가 죽었을 때 교체할 수 있고, 읽기 부하도 분산할 수 있다.

```conf
# replica 측 redis.conf
replicaof 192.168.1.10 6379

replica-read-only yes           # replica에 쓰기 차단
repl-backlog-size 1mb           # 부분 동기화 버퍼 크기
repl-diskless-sync yes          # 디스크 거치지 않고 소켓으로 직접 RDB 전송
repl-diskless-sync-delay 5      # 5초 대기 후 전송 시작 (다른 replica가 붙을 여유를 준다)
```

처음 Replica가 붙으면 Master가 RDB를 만들어 전송한다(전체 동기화). 이후에는 명령 스트림을 복제한다(부분 동기화, PSYNC).

### 복제 지연과 replication buffer

네트워크 문제나 Replica가 느릴 때 Master의 replication buffer에 명령이 쌓인다. 버퍼 용량을 초과하면 Master가 연결을 끊고 전체 재동기화를 강제한다. 이때 Master는 또 RDB를 만들어야 한다.

```conf
# Master 측 설정
# 256MB 즉시 초과, 또는 60초간 64MB 초과 시 연결 종료
client-output-buffer-limit replica 256mb 64mb 60
```

트래픽이 많은 상황에서 Replica가 재연결과 전체 동기화를 반복하는 루프에 빠지는 경우가 있다. 그 구간 동안 Master에서 RDB fork()가 계속 발생해 레이턴시가 치솟는다. `repl-backlog-size`를 충분히 크게 잡거나 버퍼 한도를 늘려야 한다.

Replica는 기본적으로 읽기 전용이다. 배치 쿼리나 분석 쿼리를 Replica로 돌릴 수 있다. 단, Replica 데이터가 Master보다 약간 오래됐을 수 있다. 정합성이 중요한 읽기는 Master에서 해야 한다.

---

## Sentinel — 장애 감지와 Failover

Sentinel은 Master 장애를 감지하고 Replica 중 하나를 새 Master로 승격시킨다. 클라이언트는 Sentinel에게 현재 Master 주소를 물어보는 방식으로 동작한다.

### 구성

Sentinel 프로세스를 최소 3개 이상 홀수로 둔다. 장애 판정에 과반수 동의(quorum)가 필요하기 때문이다.

```conf
# sentinel.conf
sentinel monitor mymaster 192.168.1.10 6379 2
# 이름: mymaster, Master IP/Port, quorum 수

sentinel down-after-milliseconds mymaster 5000
# 5초간 응답 없으면 주관적 장애(SDOWN) 판정

sentinel failover-timeout mymaster 60000
# Failover 전체 과정에 허용하는 최대 시간(ms)

sentinel parallel-syncs mymaster 1
# Failover 후 한 번에 새 Master와 동기화할 Replica 수
```

### Failover 흐름

1. Sentinel이 Master에 `PING`을 보내고 `down-after-milliseconds` 이상 응답이 없으면 **SDOWN(주관적 장애)** 선언
2. 다른 Sentinel들에게 의견을 구해 quorum이 충족되면 **ODOWN(객관적 장애)** 선언
3. Sentinel끼리 리더를 선출한다(Raft 기반)
4. 리더 Sentinel이 Replica 중 하나를 새 Master로 선택한다. 복제 offset이 가장 크고(`replica-priority`가 높은) 것을 고른다

Failover 완료까지 보통 10~30초가 걸린다(`down-after-milliseconds` + 선출 + 동기화 시간). 그 사이 쓰기는 실패한다. 애플리케이션에서 재시도 로직이 없으면 에러가 그대로 사용자에게 전달된다.

### 클라이언트 연결

클라이언트 라이브러리가 Sentinel-aware해야 Failover 후 자동으로 새 Master를 찾는다.

```java
// Spring Boot + Jedis Sentinel 설정
@Bean
public RedisConnectionFactory redisConnectionFactory() {
    RedisSentinelConfiguration sentinelConfig = new RedisSentinelConfiguration()
        .master("mymaster")
        .sentinel("192.168.1.20", 26379)
        .sentinel("192.168.1.21", 26379)
        .sentinel("192.168.1.22", 26379);

    JedisPoolConfig poolConfig = new JedisPoolConfig();
    poolConfig.setMaxTotal(100);
    poolConfig.setMaxWait(Duration.ofSeconds(3));

    return new JedisConnectionFactory(sentinelConfig, poolConfig);
}
```

### 구 Master 복구 시 데이터 손실

Master가 네트워크 분리 후 복구되면 자동으로 Replica로 강등된다. 분리된 동안 구 Master에 쓴 데이터는 이 시점에 버려진다. `min-replicas-to-write`를 설정하면 Replica가 없을 때 Master 쓰기 자체를 거부해 손실 범위를 줄일 수 있다.

```conf
# Master 설정
min-replicas-to-write 1   # 최소 1개의 replica가 있어야 쓰기 허용
min-replicas-max-lag 10   # replica 복제 지연이 10초 이하여야 쓰기 허용
```

이 설정이 없으면 네트워크 분리 구간 동안 클라이언트는 구 Master에 계속 쓰고, 복구 시 그 데이터가 전부 날아간다.

---

## Cluster — 샤딩과 운영 문제

Sentinel은 고가용성을 제공하지만 데이터를 여러 노드에 분산하지는 않는다. 메모리나 처리량이 한계에 달하면 Cluster가 필요하다.

### Hash Slot

Redis Cluster는 데이터를 16384개의 hash slot으로 나눈다. 각 노드가 일부 slot을 담당한다. 키는 `CRC16(key) mod 16384`로 slot이 결정된다.

```
노드 A: slot 0 ~ 5460
노드 B: slot 5461 ~ 10922
노드 C: slot 10923 ~ 16383
```

키 이름의 `{}` 안 내용으로 slot을 고정할 수 있다(hash tag). 같은 slot에 있는 키들은 멀티키 연산이 가능하다.

```
user:{1001}:profile  →  CRC16("1001") mod 16384
user:{1001}:session  →  CRC16("1001") mod 16384
# 두 키가 같은 slot에 들어간다 → MGET 사용 가능
```

hash tag 없이 멀티키 연산(`MGET`, `MSET`)을 쓰면 `CROSSSLOT` 에러가 난다. 단일 Redis에서 잘 동작하던 코드를 Cluster에 올리면 이 에러가 다발하는 경우가 있다.

### MOVED와 ASK

클라이언트가 잘못된 노드에 요청을 보내면 그 노드가 `MOVED` 응답으로 올바른 노드 주소를 알려준다. Cluster-aware 클라이언트는 이 응답을 보고 자동으로 올바른 노드에 재시도한다.

Resharding 중에는 `ASK` 응답도 나온다. slot 마이그레이션이 진행 중인 시점에 대상 키가 원래 노드에도, 새 노드에도 있을 수 있다. `ASK`는 이 일회성 리다이렉트를 처리한다.

```java
// Spring + Lettuce Cluster 설정
@Bean
public RedisConnectionFactory redisConnectionFactory() {
    RedisClusterConfiguration clusterConfig = new RedisClusterConfiguration(
        List.of(
            "192.168.1.10:6379",
            "192.168.1.11:6379",
            "192.168.1.12:6379"
        )
    );
    clusterConfig.setMaxRedirects(3);

    LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
        .readFrom(ReadFrom.REPLICA_PREFERRED)  // 읽기는 Replica 우선
        .build();

    return new LettuceConnectionFactory(clusterConfig, clientConfig);
}
```

### Split-Brain

네트워크 파티션으로 노드 간 통신이 끊기면 각 파티션이 독립적으로 동작할 수 있다. Cluster는 과반수 Master 노드가 있는 파티션만 쓰기를 허용한다. 소수 파티션은 쓰기를 거부한다.

Master 3개, Replica 3개 구성에서 노드가 [A, B] | [C, A_replica, B_replica, C_replica]로 분리되면, A와 B가 있는 파티션은 quorum 부족으로 쓰기가 막힌다. 반대 파티션에서 A_replica, B_replica가 새 Master로 승격된다. 네트워크가 복구되면 구 Master(A, B)는 Replica로 강등되며 분리 동안 쓴 데이터는 버려진다.

```conf
cluster-node-timeout 15000  # 15초 응답 없으면 장애 판정
```

`cluster-node-timeout` 이내에 파티션이 복구되면 Failover 없이 정상 상태로 돌아온다.

### Resharding

노드를 추가하거나 제거할 때 slot을 재분배한다. 서비스 중단 없이 진행되지만 성능에 영향을 준다.

```bash
# 노드 추가
redis-cli --cluster add-node 192.168.1.13:6379 192.168.1.10:6379

# Resharding — 대화형으로 이동할 slot 수, 목적지 노드, 소스 노드를 입력한다
redis-cli --cluster reshard 192.168.1.10:6379

# 상태 확인
redis-cli --cluster check 192.168.1.10:6379
redis-cli --cluster info 192.168.1.10:6379
```

Resharding 중 해당 slot의 키를 마이그레이션하는 동안 레이턴시가 오른다. 키가 많을수록, 키 크기가 클수록 오래 걸린다. 트래픽이 적은 시간대에 실행하고, 이동할 slot 수를 작게 나눠 여러 번 하는 것이 낫다.

### Hot Slot

특정 hash slot에 트래픽이 몰리면 그 slot을 담당하는 노드 하나가 병목이 된다. Cluster로 샤딩해도 hot slot 문제가 있으면 수평 확장 효과가 없다.

`{popular_product}:*` 처럼 특정 값으로 hash tag를 고정하면 그 slot이 과부하 상태가 된다. 해결은 키에 랜덤 suffix를 붙여 여러 slot에 분산하는 것이다.

```
popular_product:detail:1   (shard 1)
popular_product:detail:2   (shard 2)
...
popular_product:detail:10  (shard 10)
```

읽기 시 `1~10` 중 랜덤으로 선택한다. 쓰기 시 전체 shard를 갱신하거나 이벤트로 전파하는 방식을 결정해야 한다.

---

## 메모리 관리 — Eviction Policy

`maxmemory` 한도에 도달하면 Redis는 `maxmemory-policy`에 따라 키를 삭제한다.

```conf
maxmemory 4gb
maxmemory-policy allkeys-lru
```

| 정책 | 동작 |
|---|---|
| `noeviction` | 메모리 가득 차면 쓰기 에러 반환. 기본값. 캐시 용도로는 부적절 |
| `allkeys-lru` | 전체 키 중 최근에 덜 쓴 것부터 삭제. 범용 캐시에 적합 |
| `volatile-lru` | TTL 있는 키 중 LRU. TTL 없는 키는 삭제하지 않는다 |
| `allkeys-lfu` | 사용 빈도 낮은 것부터 삭제. 접근 패턴이 불균등할 때 유리 |
| `allkeys-random` | 무작위 삭제 |

캐시 전용 Redis라면 `allkeys-lru`가 기본 선택이다. 삭제되면 안 되는 키(세션, 분산 락 등)가 캐시 데이터와 섞여 있으면 `volatile-lru`로 분리하거나 인스턴스 자체를 분리해야 한다.

`noeviction`으로 두면 메모리가 가득 찼을 때 `SET`, `LPUSH` 같은 쓰기 명령이 OOM 에러를 반환한다. 애플리케이션이 이 에러를 처리하지 못하면 서비스가 멈춘다.

### 메모리 진단

```bash
# 개별 키의 메모리 사용량과 내부 자료구조 확인
redis-cli MEMORY USAGE user:1001:profile
redis-cli OBJECT ENCODING user:1001:profile

# 전반적인 메모리 상태 진단
redis-cli MEMORY DOCTOR
```

`maxmemory`는 Redis 프로세스 전체 메모리가 아니라 데이터 메모리 기준이다. 복제 버퍼, AOF 버퍼, 클라이언트 버퍼는 별도다. 서버 물리 메모리의 50~70%로 `maxmemory`를 잡고 나머지는 OS와 Redis 내부 구조가 쓸 여유를 남겨야 한다. 실제 메모리 사용량은 `INFO memory`의 `used_memory_rss`로 확인한다. `used_memory`와 `used_memory_rss`의 차이가 크면 메모리 단편화가 발생한 것이다.

```bash
redis-cli INFO memory | grep -E "used_memory|mem_fragmentation"
```

단편화 비율(`mem_fragmentation_ratio`)이 1.5를 넘으면 `MEMORY PURGE` 또는 재시작을 검토한다.
