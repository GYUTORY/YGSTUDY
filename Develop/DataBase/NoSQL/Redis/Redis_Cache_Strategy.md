---
title: Redis 캐시 설계 실무
tags: [redis, cache, ttl, memory, monitoring, deployment, key-design]
updated: 2026-04-08
---

# Redis 캐시 설계 실무

> 캐시 패턴(Cache-Aside, Stampede 방어 등)은 [Redis 다루기](Redis%20다루기.md), eviction 정책과 내부 동작은 [Redis](Redis.md), 클러스터 운영은 [Redis 심화](Redis_Advanced.md) 참고.

---

## 1. 데이터 유형별 TTL 설계

TTL을 "대충 30분"으로 잡는 경우가 많다. 문제는 데이터 성격에 따라 적절한 TTL이 크게 다르다는 점이다. TTL이 너무 짧으면 캐시 히트율이 떨어지고 DB 부하가 올라간다. 너무 길면 사용자가 오래된 데이터를 보게 된다.

### 1.1 도메인별 TTL 산정 기준

TTL을 결정할 때 고려하는 요소는 세 가지다.

- **변경 빈도**: 데이터가 얼마나 자주 바뀌는가
- **stale 허용 범위**: 오래된 데이터를 보여줘도 되는 시간이 얼마인가
- **원본 조회 비용**: DB 쿼리가 무거울수록 TTL을 길게 잡는 게 유리하다

```
도메인별 TTL 예시:

  상품 목록          5~10분     변경이 드물고, 몇 분 정도 stale해도 괜찮다
  상품 상세          30분~1시간  가격 변경 시 캐시 무효화를 별도로 건다
  상품 재고          캐시 안 함  실시간 정합성이 필요하다. 캐시하면 초과 판매 발생
  사용자 세션        30분       세션 타임아웃과 맞춘다
  사용자 프로필      1시간      본인이 수정하면 즉시 무효화
  검색 자동완성      24시간     일 1회 배치로 갱신
  집계/통계 데이터    5~15분     실시간이 아닌 "근사치"로 충분한 경우
  설정값/코드 테이블  1~6시간    거의 안 바뀌지만 바뀌면 무효화 처리
  외부 API 응답      1~5분      rate limit 회피 목적. 외부 서비스 장애 시 fallback 역할도 한다
```

### 1.2 TTL에 랜덤 지터 추가

같은 시간에 생성된 캐시가 동시에 만료되면 DB에 요청이 몰린다. 이걸 **Cache Stampede**라고 부르는데, TTL에 랜덤 편차를 주면 만료 시점이 분산된다.

```java
// TTL 지터 적용
public Duration ttlWithJitter(Duration baseTtl, double jitterRatio) {
    long baseSeconds = baseTtl.getSeconds();
    long jitterRange = (long) (baseSeconds * jitterRatio);
    long jitter = ThreadLocalRandom.current().nextLong(-jitterRange, jitterRange);
    return Duration.ofSeconds(baseSeconds + jitter);
}

// 사용 예: 기본 TTL 10분, +-20% 지터 → 8분~12분 사이에서 랜덤
Duration ttl = ttlWithJitter(Duration.ofMinutes(10), 0.2);
redisTemplate.opsForValue().set(key, value, ttl);
```

### 1.3 조건부 TTL

데이터 상태에 따라 TTL을 다르게 설정하는 패턴이다.

```java
// 빈 결과 캐싱: DB에 데이터가 없는 경우 짧은 TTL로 캐시
// → Cache Penetration 방어
public ProductDto getProduct(Long productId) {
    String key = "product:" + productId;
    String cached = redisTemplate.opsForValue().get(key);

    if (cached != null) {
        if ("EMPTY".equals(cached)) return null;
        return deserialize(cached);
    }

    ProductDto product = productRepository.findById(productId).orElse(null);

    if (product == null) {
        // 존재하지 않는 상품 → 30초만 캐시
        redisTemplate.opsForValue().set(key, "EMPTY", Duration.ofSeconds(30));
        return null;
    }

    // 정상 데이터 → 1시간 캐시
    redisTemplate.opsForValue().set(key, serialize(product), Duration.ofHours(1));
    return product;
}
```

```java
// 완료된 주문은 변경되지 않으므로 TTL을 길게
public Duration orderTtl(Order order) {
    if (order.getStatus() == OrderStatus.COMPLETED
        || order.getStatus() == OrderStatus.CANCELLED) {
        return Duration.ofHours(24);  // 완료/취소된 주문은 바뀔 일이 없다
    }
    return Duration.ofMinutes(5);  // 진행 중 주문은 자주 바뀐다
}
```

---

## 2. 캐시 키 설계

키 설계를 대충 하면 나중에 키를 찾기 어렵고, 클러스터에서 데이터가 한쪽 노드에 몰리는 문제가 생긴다.

### 2.1 네임스페이스 분리

키에 서비스명, 도메인, 식별자를 콜론으로 구분해서 넣는다.

```
키 구조: {서비스}:{도메인}:{식별자}

  order-api:product:12345
  order-api:user:profile:9876
  batch:ranking:daily:2026-04-08
  gateway:rate-limit:client:abc123
```

콜론(`:`)은 Redis에서 관례적으로 쓰는 구분자다. RedisInsight 같은 도구가 콜론 기준으로 트리 구조를 만들어주기 때문에 디버깅이 편해진다.

서비스 접두사를 넣는 이유는 하나의 Redis 인스턴스를 여러 서비스가 공유하는 경우 키 충돌을 방지하기 위해서다. 서비스별로 Redis를 분리하면 접두사 없이 도메인부터 시작해도 된다.

### 2.2 버전 접두사

캐시 데이터 구조가 바뀔 때 기존 캐시와 충돌하는 문제가 있다. 키에 버전을 넣으면 구조 변경 시 새 키를 쓰게 되고, 기존 캐시는 TTL이 지나면 자연스럽게 사라진다.

```
버전 포함 키:
  v2:product:12345

버전 관리 방법:
  1. 상수로 관리: private static final String CACHE_VERSION = "v2";
  2. 해시로 관리: DTO 필드 목록의 해시를 버전으로 사용 (자동화 가능하지만 복잡)
  3. 설정 파일로 관리: application.yml에서 cache.version 값을 읽는 방식
```

```java
// 버전 접두사를 코드에서 관리하는 예
@Component
public class CacheKeyGenerator {

    private static final String VERSION = "v3";

    public String productKey(Long productId) {
        return VERSION + ":product:" + productId;
    }

    public String userProfileKey(Long userId) {
        return VERSION + ":user:profile:" + userId;
    }
}
```

### 2.3 클러스터 환경에서 해시 태그

Redis Cluster에서 멀티 키 연산(MGET, 파이프라인 등)을 하려면 키들이 같은 슬롯에 있어야 한다. 해시 태그 `{}`를 쓰면 중괄호 안의 문자열로만 슬롯을 계산한다.

```
해시 태그 적용:
  {user:1000}:profile    → CRC16("user:1000") → 같은 슬롯
  {user:1000}:settings   → CRC16("user:1000") → 같은 슬롯

해시 태그 주의사항:
  1. 해시 태그가 같은 키가 너무 많으면 특정 슬롯에 데이터가 몰린다 (hotspot)
  2. 해시 태그를 쓸 필요가 없는 키에는 쓰지 않는다
  3. 빈 해시 태그 {} 는 무시된다 — {가 있으면 반드시 } 도 있어야 한다
```

실무에서 해시 태그를 써야 하는 상황은 생각보다 적다. 사용자 관련 데이터를 한 번에 가져와야 하는 경우 정도다. 무분별하게 쓰면 슬롯 불균형이 생기니까 꼭 필요한 경우에만 사용한다.

### 2.4 키 길이와 메모리

키도 메모리를 차지한다. 키가 수억 개인 시스템에서는 키 길이 차이가 GB 단위로 벌어진다.

```
키 길이 비교:
  "order-service:v2:user:profile:1234567890"  → 41바이트
  "os:v2:u:p:1234567890"                      → 21바이트
  → 1억 개 키 기준 약 2GB 차이

권장: 가독성과 길이 사이에서 타협한다.
  - 네임스페이스는 약어를 쓰되 팀 내에서 약어 규칙을 정한다
  - 식별자 부분은 줄이지 않는다 (디버깅할 때 필요)
  - 키 규칙 문서를 반드시 만든다
```

---

## 3. 캐시 메모리 산정

### 3.1 MEMORY USAGE로 개별 키 크기 측정

Redis 4.0부터 `MEMORY USAGE` 명령으로 키 하나가 차지하는 메모리를 바이트 단위로 확인할 수 있다.

```bash
# 키 하나의 메모리 사용량 확인
redis-cli MEMORY USAGE product:12345
# (integer) 128

# 중첩 구조가 있는 경우 샘플 수 지정 (기본 5)
redis-cli MEMORY USAGE large-hash:1 SAMPLES 0
# SAMPLES 0 → 모든 필드를 검사 (정확하지만 느리다)
```

이 값에는 키 자체, 값, Redis 내부 메타데이터(dictEntry, robj 등)가 모두 포함된다. 실제 데이터보다 크게 나오는 게 정상이다.

### 3.2 전체 캐시 메모리 예측

서비스 도입 전에 캐시가 얼마나 메모리를 잡을지 미리 계산해야 한다.

```
메모리 예측 공식:
  필요 메모리 = 키 수 x 키당 평균 크기

계산 예시:
  상품 캐시:
    상품 수: 50만 개
    키당 크기: 256바이트 (MEMORY USAGE로 측정한 값)
    → 500,000 x 256 = 128MB

  사용자 세션:
    동시 접속자: 10만 명
    세션당 크기: 512바이트
    → 100,000 x 512 = 51.2MB

  합계: 약 180MB
  오버헤드 포함 (x 1.2~1.5): 216MB ~ 270MB
```

```bash
# 개발 환경에서 실측하는 방법
# 1. 빈 Redis에 테스트 데이터 100개 넣기
# 2. INFO memory로 used_memory 확인
redis-cli INFO memory | grep used_memory_human
# used_memory_human:2.50M

# 3. 데이터 100개 더 넣고 다시 확인
redis-cli INFO memory | grep used_memory_human
# used_memory_human:2.85M
# → 키 100개당 약 0.35MB → 키 1개당 약 3.5KB
```

### 3.3 maxmemory 설정

`maxmemory`를 물리 메모리와 같게 설정하면 안 된다. Redis 자체 오버헤드, 포크 시 copy-on-write, 출력 버퍼, 복제 백로그 등이 추가 메모리를 사용한다.

```
maxmemory 설정 기준:
  캐시 전용 (RDB/AOF 안 씀):    물리 메모리의 70~80%
  캐시 + 영속성 (RDB 사용):      물리 메모리의 50~60%
  복제 활성화:                   물리 메모리의 50~60%

  예: 16GB 서버, 캐시 전용
    maxmemory 12gb

  예: 16GB 서버, RDB 스냅샷 사용
    maxmemory 8gb
    → 포크 시 최악의 경우 used_memory만큼 추가 필요
```

`INFO memory`의 `used_memory`와 `maxmemory`를 정기적으로 비교하는 모니터링을 걸어야 한다. 80%를 넘으면 알림을 보내고, 90%를 넘으면 바로 대응해야 한다.

---

## 4. 배포 시 캐시 호환성

코드를 배포할 때 캐시 데이터의 구조가 바뀌면 역직렬화 실패, 데이터 불일치 같은 문제가 생긴다. 특히 무중단 배포 환경에서 구버전과 신버전이 동시에 동작하는 시간이 있기 때문에 주의가 필요하다.

### 4.1 스키마 변경 시 처리

캐시에 저장하는 객체의 필드가 바뀔 때 호환성 문제가 발생한다.

```
필드 추가: 비교적 안전
  - 구버전 코드가 새 필드가 포함된 JSON을 읽으면 → 새 필드를 무시 (Jackson 기본 동작)
  - 신버전 코드가 기존 캐시를 읽으면 → 새 필드가 null

필드 삭제: 위험
  - 구버전 코드가 삭제된 필드를 참조하면 → NullPointerException
  - 2단계 배포가 필요:
    1차 배포: 필드를 읽지 않는 코드 배포 (필드는 아직 캐시에 남아있음)
    2차 배포: 캐시 TTL이 지난 후 필드를 DTO에서 제거

필드 타입 변경: 가장 위험
  - int → long, String → enum 같은 변경
  - 구버전과 신버전이 동시에 동작하면 역직렬화 실패
  - 캐시 키 버전을 올려서 분리하는 수밖에 없다
```

```java
// Jackson에서 모르는 필드를 무시하도록 설정
// 이 설정이 없으면 필드가 추가될 때마다 역직렬화가 깨진다
ObjectMapper mapper = new ObjectMapper();
mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
```

### 4.2 롤백 시 캐시 처리

배포 후 문제가 생겨서 롤백할 때 캐시가 걸림돌이 되는 경우가 있다.

```
시나리오: v2 배포 → v2 형식으로 캐시 저장 → 문제 발견 → v1으로 롤백
  → v1 코드가 v2 형식 캐시를 읽으려다 실패

대응 방법:
  1. 버전 키 분리: v1과 v2가 다른 키를 쓰면 롤백 시 v1 캐시가 아직 남아있다
     - 단, TTL이 짧은 경우 v1 캐시가 이미 만료됐을 수 있다
     - 롤백 직후에는 캐시 미스가 많이 발생해서 DB 부하가 올라간다

  2. 역직렬화 실패 시 캐시 무효화: 읽기 실패하면 캐시를 삭제하고 DB에서 다시 읽는다
     - 가장 안전하지만, 대량 캐시 미스가 동시에 발생할 수 있다

  3. 스키마를 항상 하위 호환: 필드 삭제/변경을 하지 않고 추가만 한다
     - 현실적으로 가장 좋은 방법이다
```

```java
// 역직렬화 실패 시 캐시 삭제 후 DB 조회하는 패턴
public ProductDto getProduct(Long id) {
    String key = "product:" + id;
    String cached = redisTemplate.opsForValue().get(key);

    if (cached != null) {
        try {
            return objectMapper.readValue(cached, ProductDto.class);
        } catch (Exception e) {
            // 역직렬화 실패 → 캐시 삭제
            log.warn("캐시 역직렬화 실패, 삭제: key={}", key, e);
            redisTemplate.delete(key);
        }
    }

    ProductDto product = productRepository.findById(id);
    redisTemplate.opsForValue().set(key, serialize(product), Duration.ofHours(1));
    return product;
}
```

### 4.3 Blue-Green 배포에서의 캐시 전환

Blue-Green 배포에서는 Blue(현재)와 Green(신규) 환경이 동시에 동작하는 시점이 있다.

```
Redis를 공유하는 경우:
  Blue(v1)와 Green(v2)이 같은 Redis를 바라본다
  → 두 버전이 같은 키에 다른 형식의 데이터를 읽고 쓴다
  → 스키마 변경이 있으면 문제

  대응:
  - 키에 버전 접두사를 포함: "v1:product:123", "v2:product:123"
  - 전환 후 구버전 키는 TTL 만료로 자연 삭제
  - TTL이 긴 키는 배포 스크립트에서 SCAN + UNLINK로 정리

Redis를 분리하는 경우:
  Blue와 Green이 각각 별도 Redis를 쓴다
  → 스키마 호환성 문제는 없다
  → 전환 직후 Green의 Redis가 비어있어서 캐시 미스 폭증 (cold start)

  대응:
  - 전환 전에 Green 환경에서 웜업 요청을 보낸다
  - 또는 공유 Redis를 쓰되 키 버전으로 분리하는 게 더 현실적이다
```

### 4.4 캐시 일괄 무효화

배포 시 캐시를 통째로 날려야 하는 경우가 있다. `FLUSHDB`는 전체 키를 삭제하기 때문에 운영 환경에서 쓰면 안 된다. 도메인별로 무효화하려면 키 패턴으로 삭제한다.

```bash
# SCAN으로 패턴에 맞는 키를 찾아서 삭제 (KEYS는 절대 쓰지 않는다)
redis-cli --scan --pattern "v2:product:*" | xargs -L 100 redis-cli UNLINK

# Lua 스크립트로 원자적 삭제 (키가 많으면 주의)
redis-cli EVAL "
  local cursor = '0'
  repeat
    local result = redis.call('SCAN', cursor, 'MATCH', ARGV[1], 'COUNT', 100)
    cursor = result[1]
    for _, key in ipairs(result[2]) do
      redis.call('UNLINK', key)
    end
  until cursor == '0'
" 0 "v2:product:*"
```

---

## 5. 캐시 모니터링과 디버깅

### 5.1 Hit Rate 추적

캐시가 제대로 동작하는지 확인하는 가장 기본적인 지표다.

```bash
redis-cli INFO stats | grep keyspace
# keyspace_hits:1234567
# keyspace_misses:12345
```

```
hit rate 계산:
  hit rate = keyspace_hits / (keyspace_hits + keyspace_misses)

  위 예시: 1234567 / (1234567 + 12345) = 99.0%

hit rate 기준:
  95% 이상:  정상
  90~95%:    TTL이 너무 짧거나, 캐시 대상이 아닌 데이터를 캐시하고 있다
  90% 미만:  키 설계를 다시 봐야 한다. 캐시 키가 너무 세분화되어 있거나,
             데이터 변경이 잦아서 무효화가 너무 자주 발생하는 경우가 많다
```

`INFO stats`의 hit/miss는 Redis 시작 이후 누적값이다. 구간별 hit rate를 보려면 주기적으로 값을 수집해서 차이를 계산해야 한다.

```java
// Spring Boot Actuator + Micrometer로 hit rate를 Prometheus에 내보내는 방법은
// RedisTemplate을 감싸서 hit/miss를 카운터로 기록한다
public class MonitoredCacheService {

    private final StringRedisTemplate redisTemplate;
    private final Counter hitCounter;
    private final Counter missCounter;

    public MonitoredCacheService(StringRedisTemplate redisTemplate,
                                 MeterRegistry registry) {
        this.redisTemplate = redisTemplate;
        this.hitCounter = registry.counter("cache.hit");
        this.missCounter = registry.counter("cache.miss");
    }

    public String get(String key) {
        String value = redisTemplate.opsForValue().get(key);
        if (value != null) {
            hitCounter.increment();
        } else {
            missCounter.increment();
        }
        return value;
    }
}
```

### 5.2 Keyspace 분석

Redis에 어떤 키가 얼마나 있는지, 메모리를 얼마나 쓰는지 파악하는 작업이다.

```bash
# DB별 키 개수와 평균 TTL
redis-cli INFO keyspace
# db0:keys=150000,expires=120000,avg_ttl=1800000

# expires/keys 비율이 낮으면 TTL 없는 키가 많다는 뜻이다
# 캐시 용도인데 TTL이 없으면 메모리 누수의 원인이 된다

# 키 패턴별 개수 파악 (SCAN 기반, 운영 환경에서 사용 가능)
redis-cli --scan --pattern "product:*" | wc -l
redis-cli --scan --pattern "session:*" | wc -l

# 큰 키 찾기 (메모리를 많이 쓰는 키)
redis-cli --bigkeys
# [00.00%] Biggest string found so far 'product:detail:999' with 15234 bytes
# [00.00%] Biggest hash found so far 'user:session:abc' with 42 fields
```

`--bigkeys`는 SCAN 기반이라 운영 환경에서 돌려도 된다. 다만 키가 수백만 개면 시간이 오래 걸린다. 피크 시간을 피해서 돌리는 게 좋다.

### 5.3 느린 캐시 조회 원인 추적

캐시를 쓰는데도 응답이 느리다면 원인은 보통 다음 중 하나다.

```
원인 1: 큰 값 (Big Value)
  - 수 MB짜리 JSON을 캐시에 넣으면 네트워크 전송과 직렬화에 시간이 걸린다
  - MEMORY USAGE로 확인하고, 필요한 필드만 캐시하도록 구조를 변경한다

원인 2: 네트워크 왕복 횟수
  - 루프 안에서 Redis 명령을 하나씩 보내면 RTT가 누적된다
  - MGET이나 파이프라인으로 한 번에 보낸다

원인 3: O(N) 명령
  - HGETALL로 필드가 수천 개인 Hash를 조회하면 느리다
  - HSCAN으로 나눠서 읽거나, 필요한 필드만 HMGET으로 가져온다

원인 4: 직렬화/역직렬화 비용
  - Java의 기본 직렬화는 느리다. JSON도 객체가 크면 무시할 수 없다
  - MessagePack, Protobuf 같은 바이너리 포맷으로 바꾸면 줄어든다
```

```bash
# SLOWLOG로 Redis 서버 측 느린 명령 확인
redis-cli SLOWLOG GET 10
# 1) 1) (integer) 1          # 로그 ID
#    2) (integer) 1712600000  # 타임스탬프
#    3) (integer) 15000       # 실행 시간 (마이크로초, 15ms)
#    4) 1) "HGETALL"
#       2) "user:session:large"

# 기본 임계값은 10ms (10000 마이크로초)
redis-cli CONFIG SET slowlog-log-slower-than 5000  # 5ms로 낮추기
redis-cli CONFIG SET slowlog-max-len 256           # 최근 256개 보관
```

### 5.4 메모리 사용 추이 모니터링

```bash
# 현재 메모리 상태 한눈에 보기
redis-cli INFO memory

# 주요 지표:
#   used_memory_human:        실제 사용 중인 메모리
#   used_memory_peak_human:   피크 메모리 (최대치)
#   used_memory_rss_human:    OS가 Redis에 할당한 물리 메모리
#   mem_fragmentation_ratio:  RSS / used_memory
#     1.0~1.5: 정상
#     1.5 이상: 단편화가 심하다 → MEMORY PURGE 또는 activedefrag 활성화
#     1.0 미만: swap을 쓰고 있다 → 즉시 대응 필요
```

```bash
# 메모리 단편화가 심할 때
redis-cli CONFIG SET activedefrag yes
redis-cli CONFIG SET active-defrag-enabled yes

# 수동 단편화 해소 (Redis 4.0+)
redis-cli MEMORY PURGE
```

---

## 6. String vs Hash 선택 기준

객체를 캐시할 때 String에 JSON을 통째로 넣을지, Hash에 필드별로 나눠서 넣을지 결정해야 한다. 정답은 없고, 접근 패턴에 따라 다르다.

### 6.1 String (JSON 직렬화)

```bash
SET product:123 '{"id":123,"name":"노트북","price":1500000,"stock":10}'
GET product:123
```

**특성:**

- 객체를 통째로 읽고 쓴다. 부분 수정이 필요하면 전체를 읽고 → 수정하고 → 다시 쓴다.
- JSON 직렬화/역직렬화를 애플리케이션에서 처리한다.
- 키 하나당 메타데이터 오버헤드가 한 번만 발생한다.

**적합한 경우:**

- 항상 전체 데이터를 읽는 경우 (상품 상세, 사용자 프로필 전체 조회)
- 필드 수가 적은 경우 (10개 이하)
- 캐시 패턴이 단순한 경우 (읽기 → 쓰기 → 만료)

### 6.2 Hash (필드별 저장)

```bash
HSET product:123 name "노트북" price 1500000 stock 10
HGET product:123 price          # 특정 필드만 조회
HINCRBY product:123 stock -1    # 특정 필드만 원자적 수정
```

**특성:**

- 필드 단위로 읽고 쓸 수 있다. 재고만 수정할 때 전체를 읽지 않아도 된다.
- `HINCRBY`로 숫자 필드를 원자적으로 변경할 수 있다.
- 필드가 적으면(`hash-max-ziplist-entries` 이하) ziplist로 저장되어 메모리를 적게 쓴다.

**적합한 경우:**

- 특정 필드만 자주 읽는 경우 (가격만, 재고만)
- 필드를 원자적으로 수정하는 경우 (조회수 증가, 재고 감소)
- 필드 수가 많고 전체를 읽는 일이 드문 경우

### 6.3 메모리 비교

```
동일한 데이터를 저장했을 때 메모리 비교 (Redis 7.0 기준):

  방식 1: String — 키 1개에 JSON 전체
    키: product:123
    값: {"id":123,"name":"노트북","price":1500000,"stock":10}
    MEMORY USAGE: ~120바이트

  방식 2: Hash — 키 1개에 필드 4개
    키: product:123
    필드: id, name, price, stock
    MEMORY USAGE: ~160바이트 (ziplist 인코딩)

  방식 3: String 분리 — 필드마다 키 1개씩
    키: product:123:name, product:123:price, ...
    MEMORY USAGE: ~400바이트 (키마다 메타데이터 오버헤드)

  → 전체 읽기가 대부분이면 String이 메모리를 적게 쓴다
  → 부분 읽기/수정이 잦으면 Hash가 네트워크 비용을 줄인다
  → 필드를 개별 키로 분리하는 건 메모리 낭비가 크니까 피한다
```

### 6.4 ziplist 임계값

Hash가 메모리를 적게 쓰는 건 ziplist(Redis 7.0부터 listpack) 인코딩 덕분이다. 필드 수나 값 크기가 임계값을 넘으면 hashtable로 전환되면서 메모리 사용량이 급증한다.

```bash
# 기본 설정 확인
redis-cli CONFIG GET hash-max-ziplist-entries
# "128"  ← 필드 수가 128개를 넘으면 hashtable로 전환

redis-cli CONFIG GET hash-max-ziplist-value
# "64"   ← 필드 값이 64바이트를 넘으면 hashtable로 전환

# 인코딩 확인
redis-cli OBJECT ENCODING product:123
# "ziplist" 또는 "hashtable"
```

Hash를 쓸 때는 필드 수와 값 크기를 이 임계값 안에 들도록 설계해야 한다. 임계값을 넘기면 String에 JSON을 넣는 것보다 메모리를 더 쓸 수 있다.

### 6.5 실무에서의 판단 흐름

```
질문 1: 데이터를 항상 통째로 읽고 쓰는가?
  → YES: String + JSON
  → NO: 질문 2로

질문 2: 특정 필드를 원자적으로 수정해야 하는가? (HINCRBY 같은)
  → YES: Hash
  → NO: 질문 3으로

질문 3: 필드 수가 128개 미만이고 값이 64바이트 미만인가?
  → YES: Hash (ziplist로 메모리 절약)
  → NO: String + JSON (hashtable 오버헤드 회피)
```

대부분의 캐시 사용 사례에서는 String + JSON이 단순하고 충분하다. Hash는 부분 읽기/수정이 자주 필요하거나 원자적 카운터가 필요한 경우에 쓴다.
