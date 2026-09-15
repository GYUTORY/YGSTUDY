---
title: Redis 캐시 운영 패턴
tags: [redis, cache, nosql, backend, performance, monitoring]
updated: 2026-09-15
---

# Redis 캐시 운영 패턴

## maxmemory-policy — 무엇이 지워지는지가 결정한다

메모리가 가득 찼을 때 Redis가 어떤 키를 삭제하는지는 정책마다 다르다. 틀린 정책을 골랐을 때 증상이 드러나는 방식도 각기 다르다.

`allkeys-lru`는 TTL 여부와 관계없이 전체 키 중 가장 오랫동안 접근하지 않은 것을 지운다. 순수 캐시 용도라면 이게 맞다. 모든 키가 지워질 수 있다는 사실을 알고 쓰는 전제다.

`volatile-lru`는 TTL이 설정된 키에서만 LRU를 적용한다. TTL 없는 키는 건드리지 않는다. 세션 데이터나 분산 락처럼 삭제되면 안 되는 키를 캐시 데이터와 같은 인스턴스에 넣을 때 이 정책을 선택한다. 주의할 점은 TTL 없는 키가 메모리를 점유하고 있으면, TTL 있는 키가 아무리 많아도 그 공간을 돌려받지 못한다. 메모리 가득 찼는데 삭제할 `volatile` 키가 없으면 `allkeys-lru`처럼 전체로 확장하지 않고 그냥 에러를 반환한다.

`allkeys-lfu`는 접근 빈도가 낮은 것을 지운다. 특정 키에 접근이 집중되는 상황에서 LRU보다 낫다. 최근에 막 생성됐지만 이후 접근이 없는 키가 LRU에서는 한참 살아남는데, LFU는 빠르게 걸러낸다.

```conf
maxmemory 8gb
maxmemory-policy allkeys-lru

# LFU 파라미터 — 빈도 감쇠 속도 조정
# 값이 클수록 최근 접근에 더 민감하게 반응한다
lfu-decay-time 1
lfu-log-factor 10
```

`noeviction`은 기본값인데 캐시에 쓰면 안 된다. 가득 차는 순간 `SET`이 에러를 반환한다. 놓치는 경우가 많은 건 스프링 부트가 Redis 오류를 `CacheErrorHandler`로 삼키는 경우다. 에러는 조용히 무시되고 매 요청이 DB에 떨어진다.

### volatile-lru를 선택할 때 주의사항

같은 인스턴스에 캐시 데이터와 영속 데이터를 섞으면 복잡해진다. 메모리 압박이 생겼을 때 지워지는 것이 캐시인지 확인하는 방법이 없어진다. 인스턴스를 분리하는 것이 더 명확하다. 분리가 어려운 상황이라면 캐시 키에는 반드시 TTL을 붙이고 영속 키에는 붙이지 않는 규칙을 엄수해야 한다.

---

## 데이터 타입 선택 — 내부 인코딩이 메모리를 결정한다

어떤 타입을 쓸지는 기능이 아니라 메모리 효율로 판단할 때가 많다.

### String vs Hash

사용자 프로필처럼 필드가 여러 개인 데이터를 저장할 때, String에 JSON을 직렬화해서 넣는 방식과 Hash로 필드별로 쪼개는 방식을 비교해야 한다.

Hash는 필드 수가 128개 이하이고 값이 64바이트 이하면 `ziplist`(Redis 7.0 이후 `listpack`) 인코딩으로 저장된다. 이 상태에서는 Hash 하나가 String 하나보다 메모리를 적게 쓴다. 임계값을 넘으면 `hashtable`로 바뀌고 메모리 효율이 역전된다.

```bash
# 현재 인코딩 확인
OBJECT ENCODING user:1001

# "ziplist" 또는 "listpack" → 압축 상태
# "hashtable" → 일반 해시 테이블

# Hash 설정 (redis.conf)
hash-max-listpack-entries 128  # 필드 수 임계값
hash-max-listpack-value 64     # 필드 값 크기 임계값
```

Hash 방식의 단점은 필드 일부만 가져올 때는 편하지만(`HGET`), 전체를 읽을 때는 `HGETALL` 하나로도 큰 Hash면 블로킹이 생길 수 있다. 필드가 수백 개 이상이면 String + JSON 직렬화가 더 단순하다.

### SortedSet 캐싱 시나리오

SortedSet은 랭킹, 최근 조회 목록, 시간순 이벤트 로그를 캐싱할 때 쓴다. score 기반 범위 조회가 O(log N)이라 레이턴시가 예측 가능하다.

```bash
# 랭킹 캐싱
ZADD leaderboard:weekly 9870 user:1001
ZADD leaderboard:weekly 7230 user:1002

# 상위 10명
ZREVRANGE leaderboard:weekly 0 9 WITHSCORES

# 특정 점수 범위
ZRANGEBYSCORE leaderboard:weekly 5000 10000 WITHSCORES
```

SortedSet도 내부적으로 `ziplist`/`listpack` vs `skiplist` 인코딩이 전환된다. 멤버 수 128개 이하, 값 크기 64바이트 이하면 압축 상태다. 랭킹 보드에 수만 명을 넣으면 skiplist로 전환되고 메모리가 확 올라간다. 전체 랭킹을 캐시에 다 넣지 말고 상위 N명만 넣는 것이 현실적이다.

```bash
# 멤버 수가 많아질 때 — 하위 제거
ZREMRANGEBYRANK leaderboard:weekly 0 -10001  # 상위 10000명만 유지
```

---

## hot key — 감지부터 분산까지

하나의 키에 초당 수만 건 이상의 요청이 몰리면 그 키를 담당하는 단일 노드가 병목이 된다. Cluster 구성이어도 hot key 문제를 해결하지 못한다.

### 감지

`redis-cli --hotkeys` 명령은 LFU 정책 하에서만 동작한다.

```bash
redis-cli --hotkeys -i 0.1  # 0.1초 간격으로 샘플링

# 특정 키 패턴의 접근 빈도
redis-cli --scan --pattern "product:*" | xargs -I {} redis-cli OBJECT FREQ {}
```

LRU 정책이라면 `MONITOR` 명령으로 확인할 수 있지만, 프로덕션에서 `MONITOR`는 Redis의 출력을 두 배로 늘려 성능을 크게 떨어뜨린다. 짧게만 사용해야 한다. `redis-cli --stat`으로 ops/sec 추이를 보면서 특정 시점에 급등하는 패턴이 있는지 먼저 확인하는 것이 낫다.

```bash
redis-cli --stat -i 1
```

### 로컬 캐시로 분산

hot key의 가장 일반적인 해결은 애플리케이션 로컬 캐시다. Redis를 거치지 않고 JVM 힙 또는 프로세스 메모리에 짧은 TTL로 캐시를 한 겹 더 두는 방식이다.

```java
// Caffeine 로컬 캐시 + Redis 2단계 캐시
private final Cache<String, Product> localCache = Caffeine.newBuilder()
    .expireAfterWrite(5, TimeUnit.SECONDS)
    .maximumSize(1000)
    .build();

public Product getProduct(String id) {
    return localCache.get(id, key -> {
        Product cached = redisTemplate.opsForValue().get("product:" + key);
        if (cached != null) return cached;
        Product product = productRepository.findById(key).orElseThrow();
        redisTemplate.opsForValue().set("product:" + key, product, Duration.ofMinutes(10));
        return product;
    });
}
```

로컬 캐시 TTL을 5~10초로 짧게 잡는다. 업데이트 반영이 그만큼 늦어지는 걸 감수하는 것이다. 인스턴스가 여러 개면 각자의 로컬 캐시가 일시적으로 다른 값을 가질 수 있다.

### 키 복제로 분산

로컬 캐시 대신 Redis 안에서 hot key를 여러 개로 복제하는 방식도 있다.

```java
// hot key를 N개의 샤드로 분산
private static final int SHARD_COUNT = 10;

public String getShardedKey(String baseKey) {
    int shard = ThreadLocalRandom.current().nextInt(SHARD_COUNT);
    return baseKey + ":" + shard;
}

public Product getProduct(String id) {
    String key = getShardedKey("product:" + id);
    Product cached = redisTemplate.opsForValue().get(key);
    if (cached != null) return cached;

    Product product = productRepository.findById(id).orElseThrow();
    // 모든 샤드에 쓰거나, 쓴 샤드만 채우고 나머지는 miss 시 채움
    for (int i = 0; i < SHARD_COUNT; i++) {
        redisTemplate.opsForValue().set("product:" + id + ":" + i, product, Duration.ofMinutes(10));
    }
    return product;
}
```

쓰기가 빈번하면 모든 샤드를 갱신하는 비용이 문제가 된다. 읽기 비율이 압도적으로 높은 상황에서만 유효하다.

---

## keyspace notification — 만료 이벤트 감지

키가 만료되거나 삭제될 때 애플리케이션이 이벤트를 받으려면 keyspace notification을 활성화해야 한다. 기본값은 비활성이다.

```conf
# redis.conf
# K: keyspace 이벤트, E: keyevent 이벤트
# x: 만료 이벤트, g: 범용(del, expire 등)
notify-keyspace-events "Ex"
```

런타임으로 켤 수도 있다.

```bash
CONFIG SET notify-keyspace-events Ex
```

만료 이벤트는 `__keyevent@{db}__:expired` 채널로 발행된다.

```java
// Spring Data Redis Pub/Sub
@Component
public class KeyExpirationListener extends KeyExpirationEventMessageListener {

    public KeyExpirationListener(RedisMessageListenerContainer container) {
        super(container);
    }

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String expiredKey = message.toString();
        // 만료된 키에 대한 후처리
        if (expiredKey.startsWith("session:")) {
            sessionCleanupService.cleanup(expiredKey);
        }
    }
}

@Bean
public RedisMessageListenerContainer redisMessageListenerContainer(
        RedisConnectionFactory connectionFactory) {
    RedisMessageListenerContainer container = new RedisMessageListenerContainer();
    container.setConnectionFactory(connectionFactory);
    return container;
}
```

### 주의사항

keyspace notification은 Redis에 부하를 준다. 키가 많거나 만료가 잦으면 알림 트래픽이 상당해진다. 전체 키가 아니라 특정 패턴에만 관심 있다면 keyevent 채널을 구독하고 이름으로 필터링하는 것이 낫다.

더 중요한 것은 **만료 이벤트가 보장되지 않는다**는 점이다. Redis의 지연 삭제 때문에 키가 TTL 시점에 즉시 삭제되지 않을 수 있다. 만료된 키는 접근될 때 또는 주기적 정리 사이클에서 실제로 지워지는데, 이때 이벤트가 발행된다. 즉, 만료 이벤트를 실시간 비즈니스 로직의 트리거로 쓰면 타이밍이 어긋날 수 있다.

Redis Cluster에서는 각 노드가 자신이 담당하는 슬롯의 이벤트만 발행한다. 모든 만료 이벤트를 받으려면 클러스터의 모든 노드를 개별적으로 구독해야 한다.

---

## Redis Cluster에서 캐시 키 슬롯 분포 확인

Cluster를 운영하다 보면 특정 노드에 슬롯이 쏠려 있거나 키 분포가 불균등한 상황이 생긴다.

### 슬롯과 키 분포 확인

```bash
# 클러스터 전체 슬롯 분배 확인
redis-cli --cluster info 192.168.1.10:6379

# 각 노드의 키 수와 슬롯 수
redis-cli -c -h 192.168.1.10 CLUSTER NODES | awk '{print $2, $9}'

# 특정 노드의 키 수
redis-cli -h 192.168.1.10 -p 6379 DBSIZE
```

`cluster info` 출력의 `cluster_stats_messages_sent`와 `cluster_stats_messages_received`를 노드별로 비교하면 리다이렉트 빈도를 알 수 있다. 리다이렉트가 많은 노드는 클라이언트의 슬롯 캐시가 낡았거나, 최근 Resharding이 있었던 것이다.

### 특정 키의 슬롯 계산

```bash
# 키가 어느 슬롯에 들어가는지
redis-cli --cluster keyslot product:1001

# 해당 슬롯을 어느 노드가 담당하는지
redis-cli -c -h 192.168.1.10 CLUSTER KEYSLOT product:1001
redis-cli -c -h 192.168.1.10 CLUSTER SHARDS
```

슬롯 번호를 직접 계산해서 hash tag 설계에 반영할 수 있다.

```python
# CRC16 슬롯 계산
def crc16_redis(data):
    crc = 0
    for byte in data.encode():
        crc = ((crc << 8) & 0xFFFF) ^ CRC16_TABLE[(crc >> 8) ^ byte]
    return crc % 16384
```

### 슬롯 불균형 감지

Resharding 후 키 수 분포가 이상하다면 hash tag를 과하게 쓰고 있는 것이 원인인 경우가 많다.

```bash
# 특정 슬롯의 키 수
redis-cli -c CLUSTER COUNTKEYSINSLOT 5000

# 슬롯 범위의 샘플 키 (슬롯 5000에서 10개)
redis-cli -c CLUSTER GETKEYSINSLOT 5000 10
```

`{}` hash tag를 쓰는 키가 많으면 `{}` 안 값이 같은 키들이 전부 같은 슬롯에 몰린다. `product:{category_id}:*` 패턴에서 특정 카테고리만 트래픽이 많으면 그 슬롯을 담당하는 노드 하나만 과부하가 된다. hash tag를 카테고리 단위보다 더 세분화하거나, 앞서 설명한 key sharding을 적용한다.

### 클라이언트 슬롯 캐시 갱신

Lettuce는 내부적으로 슬롯-노드 매핑을 캐싱한다. Resharding 직후 잠깐 `MOVED` 에러가 나는 건 이 캐시가 갱신되기 전이다. 정상 동작이지만, 에러율이 높다면 캐시 갱신을 강제할 수 있다.

```java
// Lettuce 슬롯 캐시 수동 갱신
if (redisConnectionFactory instanceof LettuceConnectionFactory lettuceFactory) {
    ClusterCommandExecutor executor = lettuceFactory.getClusterCommandExecutor();
    // 다음 요청 시 토폴로지를 새로 읽는다
    lettuceFactory.resetConnection();
}
```

Resharding 중 `ASK` 에러는 슬롯 캐시 갱신으로 해결되지 않는다. 마이그레이션이 완전히 끝날 때까지 일시적으로 발생하는 정상 응답이다. Cluster-aware 클라이언트는 `ASK` 응답을 받으면 해당 노드에 `ASKING` 커맨드를 먼저 보내고 재시도한다.
