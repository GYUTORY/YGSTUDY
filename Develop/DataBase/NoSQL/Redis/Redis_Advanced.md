---
title: Redis 심화 가이드
tags: [redis, cluster, sentinel, streams, lua, distributed-lock, spring-data-redis, performance]
updated: 2026-03-01
---

# Redis 심화

## 1. Redis Cluster

### 1.1 아키텍처

Redis Cluster는 **데이터를 자동으로 여러 노드에 분산**하는 수평 확장 솔루션이다. 16384개의 해시 슬롯(Hash Slot)으로 키 공간을 분할한다.

```
키 → 해시 슬롯 매핑:
  HASH_SLOT = CRC16(key) mod 16384

예시 (6노드 Cluster):
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ Master A │   │ Master B │   │ Master C │
  │ 0~5460   │   │ 5461~10922│  │10923~16383│
  └────┬─────┘   └────┬─────┘   └────┬─────┘
       │              │              │
  ┌────┴─────┐   ┌────┴─────┐   ┌────┴─────┐
  │ Replica  │   │ Replica  │   │ Replica  │
  │   A'     │   │   B'     │   │   C'     │
  └──────────┘   └──────────┘   └──────────┘

  - Master 3대: 데이터 분산 저장 (각 ~5461 슬롯)
  - Replica 3대: 각 Master의 복제본 (페일오버 대비)
  - 최소 6노드 권장 (Master 3 + Replica 3)
```

### 1.2 해시 슬롯과 키 분배

```
키 분배 규칙:
  "user:1000" → CRC16("user:1000") mod 16384 → 슬롯 12345 → Master C
  "order:500"  → CRC16("order:500") mod 16384 → 슬롯 2345  → Master A

해시 태그 (Hash Tag):
  같은 슬롯에 배치하고 싶은 키들에 사용
  {user:1000}:profile  → CRC16("user:1000") → 같은 슬롯
  {user:1000}:orders   → CRC16("user:1000") → 같은 슬롯

  → MGET, 트랜잭션 등 멀티 키 연산 가능
```

```bash
# Cluster 생성 (Redis 5.0+)
redis-cli --cluster create \
  192.168.1.1:7000 192.168.1.2:7000 192.168.1.3:7000 \
  192.168.1.4:7000 192.168.1.5:7000 192.168.1.6:7000 \
  --cluster-replicas 1

# 슬롯 정보 확인
redis-cli -c -p 7000 cluster slots

# 노드 목록
redis-cli -c -p 7000 cluster nodes

# 새 노드 추가
redis-cli --cluster add-node 192.168.1.7:7000 192.168.1.1:7000

# 슬롯 리밸런싱 (리샤딩)
redis-cli --cluster reshard 192.168.1.1:7000
```

### 1.3 MOVED와 ASK 리다이렉션

클라이언트가 잘못된 노드에 요청하면 올바른 노드로 리다이렉트된다.

```
클라이언트 → Master A: GET user:1000
Master A → 클라이언트: MOVED 12345 192.168.1.3:7000
클라이언트 → Master C: GET user:1000
Master C → 클라이언트: "John"

MOVED: 슬롯이 영구적으로 다른 노드에 있음 → 라우팅 테이블 갱신
ASK:   슬롯이 마이그레이션 중 → 일시적 리다이렉트 (테이블 갱신 X)
```

### 1.4 페일오버

```
정상 상태:
  Master A (슬롯 0~5460) ←── 복제 ──→ Replica A'

Master A 장애 발생:
  1. Replica A'가 Master A 무응답 감지 (cluster-node-timeout)
  2. 다른 Master들에게 투표 요청 (과반수 필요)
  3. Replica A'가 새로운 Master로 승격
  4. 클러스터 슬롯 테이블 업데이트
  5. 기존 Master A 복구 시 → Replica로 합류

타임아웃 설정:
  cluster-node-timeout 15000  # 15초 (장애 감지)
```

### 1.5 Cluster 제약사항

| 제약 | 설명 | 해결 |
|------|------|------|
| **멀티 키 연산** | 다른 슬롯의 키를 함께 조작 불가 | 해시 태그 `{tag}` 사용 |
| **데이터베이스** | DB 0만 사용 가능 (SELECT 불가) | 키 네이밍으로 구분 |
| **Lua 스크립트** | 접근하는 모든 키가 같은 슬롯 | 해시 태그 사용 |
| **트랜잭션** | 같은 슬롯 내에서만 MULTI/EXEC | 해시 태그 사용 |
| **Pub/Sub** | 모든 노드에 브로드캐스트 → 오버헤드 | Sharded Pub/Sub (7.0+) |

### 1.6 Spring Boot Cluster 설정

```yaml
spring:
  data:
    redis:
      cluster:
        nodes:
          - 192.168.1.1:7000
          - 192.168.1.2:7000
          - 192.168.1.3:7000
        max-redirects: 3
      lettuce:
        cluster:
          refresh:
            adaptive: true          # 토폴로지 자동 갱신
            period: 30s
```

```java
@Configuration
public class RedisClusterConfig {

    @Bean
    public LettuceConnectionFactory redisConnectionFactory() {
        RedisClusterConfiguration config = new RedisClusterConfiguration(
            List.of("192.168.1.1:7000", "192.168.1.2:7000", "192.168.1.3:7000")
        );
        config.setMaxRedirects(3);

        LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
            .readFrom(ReadFrom.REPLICA_PREFERRED)  // 읽기는 Replica 우선
            .build();

        return new LettuceConnectionFactory(config, clientConfig);
    }
}
```

## 2. Redis Sentinel

### 2.1 아키텍처

Sentinel은 **자동 장애 감지와 페일오버**를 관리하는 고가용성(HA) 솔루션이다.

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│Sentinel 1│   │Sentinel 2│   │Sentinel 3│
└─────┬────┘   └─────┬────┘   └─────┬────┘
      │ 감시         │ 감시         │ 감시
      ↓              ↓              ↓
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Master   │──→│ Replica 1│   │ Replica 2│
│  :6379    │──→│  :6380   │   │  :6381   │
└──────────┘   └──────────┘   └──────────┘

Sentinel의 역할:
  1. 모니터링: Master/Replica 상태 지속 확인
  2. 알림: 장애 발생 시 관리자 알림
  3. 페일오버: Master 장애 시 Replica를 Master로 승격
  4. 설정 제공: 클라이언트에 현재 Master 주소 제공
```

### 2.2 페일오버 프로세스

```
1. SDOWN (Subjective Down):
   - 개별 Sentinel이 Master 무응답 감지
   - down-after-milliseconds 설정 기준

2. ODOWN (Objective Down):
   - 설정된 quorum 수 이상의 Sentinel이 동의
   - 예: quorum 2 → 2대 이상이 SDOWN 판정 시

3. Leader 선출:
   - Sentinel 중 1대가 리더로 선출 (Raft 합의)
   - 리더가 페일오버 수행

4. 페일오버 실행:
   - 최적의 Replica 선택 (replica-priority, 복제 오프셋)
   - 선택된 Replica에 SLAVEOF NO ONE 명령
   - 나머지 Replica를 새 Master에 연결
   - 클라이언트에 새 Master 주소 전파
```

### 2.3 설정

```conf
# sentinel.conf
sentinel monitor mymaster 192.168.1.1 6379 2    # quorum: 2
sentinel down-after-milliseconds mymaster 5000    # 5초 무응답 시 SDOWN
sentinel failover-timeout mymaster 60000          # 페일오버 타임아웃 60초
sentinel parallel-syncs mymaster 1                # 동시 복제 수
sentinel auth-pass mymaster <password>            # Master 인증
```

```yaml
# Spring Boot Sentinel 설정
spring:
  data:
    redis:
      sentinel:
        master: mymaster
        nodes:
          - 192.168.1.10:26379
          - 192.168.1.11:26379
          - 192.168.1.12:26379
        password: redis-password
      lettuce:
        sentinel:
          refresh: 10s
```

### 2.4 Sentinel vs Cluster

| 항목 | Sentinel | Cluster |
|------|----------|---------|
| **목적** | 고가용성 (HA) | HA + 수평 확장 |
| **데이터 분산** | X (단일 Master) | O (멀티 Master) |
| **자동 페일오버** | O | O |
| **최대 메모리** | 단일 노드 메모리 | 노드 수 × 메모리 |
| **멀티 키 연산** | 제약 없음 | 같은 슬롯만 가능 |
| **복잡도** | 낮음 | 높음 |
| **적합한 경우** | 10GB 이하, HA 필요 | 대용량, 높은 처리량 |

## 3. Redis Streams

### 3.1 개요

Redis Streams는 **로그 기반 메시지 스트리밍** 데이터 구조다. Kafka의 핵심 개념을 Redis 내에서 구현한다.

```
Pub/Sub vs Streams:
  Pub/Sub: 구독자 없으면 메시지 손실, 히스토리 없음
  Streams: 메시지 영구 저장, Consumer Group, ACK, 재처리 가능

Stream 구조:
  stream_key:
    1647830400000-0: {field1: value1, field2: value2}   ← 엔트리 ID (타임스탬프-시퀀스)
    1647830400001-0: {field1: value3, field2: value4}
    1647830401000-0: {field1: value5, field2: value6}
    ...
```

### 3.2 기본 연산

```redis
# 메시지 추가 (* = 자동 ID 생성)
XADD orders * user_id 1000 product "iPhone" amount 999
# → "1647830400000-0"

# 범위 조회
XRANGE orders - +                      # 전체 조회
XRANGE orders 1647830400000 +          # 특정 시점 이후
XRANGE orders - + COUNT 10            # 최근 10건

# 역순 조회
XREVRANGE orders + - COUNT 5          # 최신 5건

# 길이 확인
XLEN orders

# 자르기 (오래된 메시지 삭제)
XTRIM orders MAXLEN ~ 1000            # 대략 1000건 유지
XTRIM orders MINID 1647830400000      # 특정 ID 이전 삭제
```

### 3.3 Consumer Group

여러 Consumer가 **분업**하여 메시지를 처리한다.

```
Stream: orders
  │
  ├── Consumer Group: order-processing
  │     ├── Consumer A: 엔트리 1, 4, 7, ... 처리
  │     ├── Consumer B: 엔트리 2, 5, 8, ... 처리
  │     └── Consumer C: 엔트리 3, 6, 9, ... 처리
  │
  └── Consumer Group: analytics
        └── Consumer D: 모든 엔트리 분석
```

```redis
# Consumer Group 생성
XGROUP CREATE orders order-processing $ MKSTREAM
#   $: 새 메시지부터 소비
#   0: 처음부터 소비

# 메시지 읽기 (Consumer Group)
XREADGROUP GROUP order-processing consumer-A COUNT 10 BLOCK 2000 STREAMS orders >
#   >: 아직 전달되지 않은 메시지만 읽기
#   BLOCK 2000: 2초 대기 (새 메시지 없으면)

# ACK (처리 완료 확인)
XACK orders order-processing 1647830400000-0

# 미확인 메시지 확인 (PEL: Pending Entries List)
XPENDING orders order-processing - + 10

# 미확인 메시지 다른 Consumer에게 재할당
XCLAIM orders order-processing consumer-B 60000 1647830400000-0
#   60000: 60초 이상 미확인된 메시지만 클레임

# Consumer Group 정보
XINFO GROUPS orders
XINFO CONSUMERS orders order-processing
```

### 3.4 Spring에서 Streams 사용

```java
// 메시지 발행
@Service
public class OrderStreamPublisher {

    private final StringRedisTemplate redisTemplate;

    public String publishOrder(OrderEvent event) {
        MapRecord<String, String, String> record = StreamRecords
            .newRecord()
            .ofMap(Map.of(
                "userId", event.getUserId().toString(),
                "product", event.getProduct(),
                "amount", event.getAmount().toString()
            ))
            .withStreamKey("orders");

        return redisTemplate.opsForStream()
            .add(record)
            .getValue();
    }
}

// Consumer Group 기반 메시지 소비
@Configuration
public class StreamConsumerConfig {

    @Bean
    public Subscription orderStreamSubscription(
            RedisConnectionFactory connectionFactory) {

        StreamMessageListenerContainer.StreamMessageListenerContainerOptions<String, MapRecord<String, String, String>> options =
            StreamMessageListenerContainer.StreamMessageListenerContainerOptions.builder()
                .pollTimeout(Duration.ofSeconds(2))
                .batchSize(10)
                .build();

        StreamMessageListenerContainer<String, MapRecord<String, String, String>> container =
            StreamMessageListenerContainer.create(connectionFactory, options);

        Subscription subscription = container.receiveAutoAck(
            Consumer.from("order-processing", "consumer-1"),
            StreamOffset.create("orders", ReadOffset.lastConsumed()),
            new OrderStreamListener()
        );

        container.start();
        return subscription;
    }
}

@Component
public class OrderStreamListener
        implements StreamListener<String, MapRecord<String, String, String>> {

    @Override
    public void onMessage(MapRecord<String, String, String> message) {
        Map<String, String> body = message.getValue();
        log.info("주문 처리: userId={}, product={}, amount={}",
            body.get("userId"), body.get("product"), body.get("amount"));
    }
}
```

## 4. Lua 스크립팅

### 4.1 왜 Lua인가

Redis 명령어는 개별적으로 원자적이지만, **여러 명령어를 묶은 로직**은 원자적이지 않다. Lua 스크립트로 이 문제를 해결한다.

```
문제 상황 (Race Condition):
  스레드 A: GET stock → 1
  스레드 B: GET stock → 1
  스레드 A: DECR stock → 0 (구매 성공)
  스레드 B: DECR stock → -1 (재고 마이너스!)

해결 (Lua 원자적 실행):
  스레드 A: EVAL script → 재고 확인 + 차감 (원자적) → 0
  스레드 B: EVAL script → 재고 확인 → 0 → 구매 실패
```

### 4.2 기본 문법

```redis
# 인라인 실행
EVAL "return redis.call('GET', KEYS[1])" 1 user:1000

# 조건부 실행
EVAL "
  local stock = tonumber(redis.call('GET', KEYS[1]))
  if stock > 0 then
    redis.call('DECR', KEYS[1])
    return 1
  else
    return 0
  end
" 1 product:stock:123

# 스크립트 캐싱 (SHA 기반)
SCRIPT LOAD "return redis.call('GET', KEYS[1])"
# → "e0e1f9fabfc9d4800c877a703b823ac0578ff831"

EVALSHA e0e1f9fabfc9d4800c877a703b823ac0578ff831 1 user:1000
```

### 4.3 실전 패턴

```lua
-- 슬라이딩 윈도우 Rate Limiter
-- KEYS[1]: 키, ARGV[1]: 윈도우(초), ARGV[2]: 최대 요청수, ARGV[3]: 현재 타임스탬프
local key = KEYS[1]
local window = tonumber(ARGV[1])
local max_requests = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- 윈도우 밖의 오래된 요청 제거
redis.call('ZREMRANGEBYSCORE', key, 0, now - window * 1000)

-- 현재 윈도우 내 요청 수
local count = redis.call('ZCARD', key)

if count < max_requests then
    redis.call('ZADD', key, now, now .. '-' .. math.random(1000000))
    redis.call('PEXPIRE', key, window * 1000)
    return 1  -- 허용
else
    return 0  -- 거부
end
```

```java
// Spring에서 Lua 스크립트 실행
@Component
public class RateLimiter {

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> rateLimitScript;

    public RateLimiter(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
        this.rateLimitScript = RedisScript.of(
            new ClassPathResource("scripts/rate-limiter.lua"), Long.class);
    }

    public boolean isAllowed(String clientId, int windowSec, int maxRequests) {
        Long result = redisTemplate.execute(
            rateLimitScript,
            List.of("rate:" + clientId),
            String.valueOf(windowSec),
            String.valueOf(maxRequests),
            String.valueOf(System.currentTimeMillis())
        );
        return result != null && result == 1L;
    }
}
```

```lua
-- 재고 차감 + 주문 생성 (원자적)
-- KEYS[1]: 재고 키, KEYS[2]: 주문 키
-- ARGV[1]: 차감 수량, ARGV[2]: 주문 정보 JSON
local stock_key = KEYS[1]
local order_key = KEYS[2]
local quantity = tonumber(ARGV[1])
local order_data = ARGV[2]

local stock = tonumber(redis.call('GET', stock_key) or '0')

if stock >= quantity then
    redis.call('DECRBY', stock_key, quantity)
    redis.call('RPUSH', order_key, order_data)
    return stock - quantity  -- 남은 재고
else
    return -1  -- 재고 부족
end
```

## 5. 분산 락 (Distributed Lock)

### 5.1 단일 인스턴스 락

```redis
# 락 획득 (SET NX EX = 없을 때만 설정 + 만료 시간)
SET lock:order:123 "owner-uuid" NX EX 30
# → OK: 락 획득 성공
# → nil: 이미 락 존재

# 락 해제 (Lua로 원자적 확인 + 삭제)
EVAL "
  if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
  else
    return 0
  end
" 1 lock:order:123 "owner-uuid"
```

```
왜 Lua로 해제해야 하는가?

  ❌ 잘못된 방법:
    GET lock → "owner-A"
    (이 사이에 락 만료 → 다른 스레드가 락 획득)
    DEL lock → 다른 스레드의 락을 삭제!

  ✅ Lua: GET + DEL이 원자적으로 실행
```

### 5.2 Redlock 알고리즘

독립된 Redis 인스턴스 N대에서 **과반수 락 획득**으로 안정성을 보장한다.

```
Redlock (N=5 인스턴스):
  1. 현재 시간 T1 기록
  2. 5개 인스턴스에 순차적으로 락 요청 (짧은 타임아웃)
  3. 과반수(3개 이상) 획득 + 총 소요 시간 < 만료 시간
     → 락 획득 성공
  4. 실패 시 모든 인스턴스에서 락 해제

  Redis 1: ✅ 획득
  Redis 2: ✅ 획득
  Redis 3: ❌ 실패 (타임아웃)
  Redis 4: ✅ 획득
  Redis 5: ✅ 획득
  → 4/5 성공 → 락 획득 (유효 시간 = 원래 만료 - 소요 시간)
```

### 5.3 Redisson (Java)

```java
// build.gradle
// implementation 'org.redisson:redisson-spring-boot-starter:3.27.0'

@Configuration
public class RedissonConfig {

    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useSingleServer()
            .setAddress("redis://localhost:6379")
            .setConnectionMinimumIdleSize(5)
            .setConnectionPoolSize(10);
        return Redisson.create(config);
    }
}

@Service
public class OrderService {

    private final RedissonClient redisson;

    // 기본 락
    public void processOrder(Long orderId) {
        RLock lock = redisson.getLock("lock:order:" + orderId);

        try {
            // 10초 대기, 30초 후 자동 해제
            boolean acquired = lock.tryLock(10, 30, TimeUnit.SECONDS);
            if (!acquired) {
                throw new RuntimeException("락 획득 실패");
            }
            // 주문 처리 로직
            doProcess(orderId);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    // 페어 락 (공정 락 - FIFO 순서 보장)
    public void fairProcess(Long id) {
        RLock fairLock = redisson.getFairLock("lock:fair:" + id);
        // 사용법 동일
    }

    // 멀티 락 (여러 리소스 동시 락)
    public void transferStock(Long fromId, Long toId) {
        RLock lock1 = redisson.getLock("lock:stock:" + fromId);
        RLock lock2 = redisson.getLock("lock:stock:" + toId);
        RLock multiLock = redisson.getMultiLock(lock1, lock2);

        try {
            multiLock.lock(10, TimeUnit.SECONDS);
            // 재고 이동 로직
        } finally {
            multiLock.unlock();
        }
    }
}
```

### 5.4 AOP 기반 분산 락

```java
// 커스텀 어노테이션
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface DistributedLock {
    String key();                    // SpEL 지원
    long waitTime() default 5;      // 대기 시간(초)
    long leaseTime() default 10;    // 락 유지 시간(초)
}

// AOP 처리
@Aspect
@Component
public class DistributedLockAspect {

    private final RedissonClient redisson;

    @Around("@annotation(distributedLock)")
    public Object around(ProceedingJoinPoint pjp,
                          DistributedLock distributedLock) throws Throwable {
        String key = parseKey(distributedLock.key(), pjp);
        RLock lock = redisson.getLock("lock:" + key);

        try {
            boolean acquired = lock.tryLock(
                distributedLock.waitTime(),
                distributedLock.leaseTime(),
                TimeUnit.SECONDS
            );
            if (!acquired) {
                throw new RuntimeException("락 획득 실패: " + key);
            }
            return pjp.proceed();
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}

// 사용
@Service
public class StockService {

    @DistributedLock(key = "'stock:' + #productId")
    public void decrease(Long productId, int quantity) {
        Stock stock = stockRepository.findByProductId(productId);
        stock.decrease(quantity);
        stockRepository.save(stock);
    }
}
```

## 6. Spring Data Redis

### 6.1 기본 설정

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      password: redis-password
      lettuce:
        pool:
          max-active: 16       # 최대 커넥션
          max-idle: 8          # 최대 유휴 커넥션
          min-idle: 4          # 최소 유휴 커넥션
          max-wait: 3000ms     # 커넥션 대기 시간
```

```java
@Configuration
@EnableCaching
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(
            RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);

        // JSON 직렬화
        ObjectMapper om = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .activateDefaultTyping(
                om.getPolymorphicTypeValidator(),
                ObjectMapper.DefaultTyping.NON_FINAL
            );

        GenericJackson2JsonRedisSerializer serializer =
            new GenericJackson2JsonRedisSerializer(om);

        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(serializer);
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(serializer);

        return template;
    }

    // 캐시 매니저
    @Bean
    public CacheManager cacheManager(RedisConnectionFactory cf) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(30))
            .serializeKeysWith(
                RedisSerializationContext.SerializationPair
                    .fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair
                    .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(cf)
            .cacheDefaults(config)
            .withCacheConfiguration("users",
                config.entryTtl(Duration.ofHours(1)))
            .withCacheConfiguration("products",
                config.entryTtl(Duration.ofMinutes(10)))
            .build();
    }
}
```

### 6.2 캐싱 어노테이션

```java
@Service
public class UserService {

    // 캐시 저장/조회
    @Cacheable(value = "users", key = "#id",
               unless = "#result == null")
    public UserDto findById(Long id) {
        return userRepository.findById(id)
            .map(UserDto::from)
            .orElse(null);
    }

    // 캐시 갱신
    @CachePut(value = "users", key = "#request.id")
    public UserDto update(UpdateUserRequest request) {
        User user = userRepository.findById(request.getId())
            .orElseThrow();
        user.update(request);
        return UserDto.from(userRepository.save(user));
    }

    // 캐시 삭제
    @CacheEvict(value = "users", key = "#id")
    public void delete(Long id) {
        userRepository.deleteById(id);
    }

    // 여러 캐시 동시 삭제
    @CacheEvict(value = "users", allEntries = true)
    public void clearCache() { }

    // 복합 조건
    @Caching(
        evict = {
            @CacheEvict(value = "users", key = "#id"),
            @CacheEvict(value = "userList", allEntries = true)
        }
    )
    public void deleteWithListCache(Long id) {
        userRepository.deleteById(id);
    }
}
```

### 6.3 RedisTemplate 직접 사용

```java
@Repository
public class UserRedisRepository {

    private final RedisTemplate<String, Object> redisTemplate;

    private static final String KEY_PREFIX = "user:";

    // String 연산
    public void save(UserDto user) {
        String key = KEY_PREFIX + user.getId();
        redisTemplate.opsForValue().set(key, user, Duration.ofHours(1));
    }

    public UserDto findById(Long id) {
        return (UserDto) redisTemplate.opsForValue().get(KEY_PREFIX + id);
    }

    // Hash 연산
    public void saveAsHash(UserDto user) {
        String key = KEY_PREFIX + user.getId();
        redisTemplate.opsForHash().putAll(key, Map.of(
            "name", user.getName(),
            "email", user.getEmail(),
            "age", String.valueOf(user.getAge())
        ));
        redisTemplate.expire(key, Duration.ofHours(1));
    }

    // Sorted Set (리더보드)
    public void updateScore(Long userId, double score) {
        redisTemplate.opsForZSet().add("leaderboard", userId.toString(), score);
    }

    public Set<ZSetOperations.TypedTuple<Object>> getTopN(int n) {
        return redisTemplate.opsForZSet()
            .reverseRangeWithScores("leaderboard", 0, n - 1);
    }

    // Set (고유 방문자)
    public void trackVisitor(String date, String userId) {
        redisTemplate.opsForSet().add("visitors:" + date, userId);
    }

    public Long getUniqueVisitors(String date) {
        return redisTemplate.opsForSet().size("visitors:" + date);
    }

    // Pipeline (배치 처리)
    public List<Object> batchGet(List<Long> ids) {
        return redisTemplate.executePipelined((RedisCallback<Object>) connection -> {
            StringRedisConnection conn = (StringRedisConnection) connection;
            ids.forEach(id -> conn.get(KEY_PREFIX + id));
            return null;
        });
    }
}
```

## 7. 성능 튜닝

### 7.1 Slow Log 분석

```redis
# Slow Log 설정
CONFIG SET slowlog-log-slower-than 10000   # 10ms 이상 기록
CONFIG SET slowlog-max-len 128             # 최대 128건 저장

# Slow Log 조회
SLOWLOG GET 10        # 최근 10건
SLOWLOG LEN           # 전체 건수
SLOWLOG RESET         # 초기화

# 결과 예시:
# 1) (integer) 14          # 로그 ID
# 2) (integer) 1647830400  # 타임스탬프
# 3) (integer) 15234       # 소요 시간(μs) = 15.2ms
# 4) 1) "KEYS"             # 실행 명령어
#    2) "*"
```

### 7.2 위험한 명령어와 대체

| 위험 명령어 | 이유 | 대체 |
|-------------|------|------|
| **KEYS \*** | O(N) 전체 스캔, 블로킹 | `SCAN` (커서 기반, 점진적) |
| **FLUSHALL** | 모든 데이터 삭제 | `UNLINK` (비동기 삭제) |
| **SMEMBERS** | 대규모 Set 전체 반환 | `SSCAN` (커서 기반) |
| **HGETALL** | 대규모 Hash 전체 반환 | `HSCAN` 또는 `HMGET` |
| **LRANGE 0 -1** | 대규모 List 전체 반환 | 페이지네이션 |

```redis
# KEYS 대신 SCAN 사용
SCAN 0 MATCH user:* COUNT 100
# → 커서 + 결과 반환, 다음 커서로 이어서 조회

# SMEMBERS 대신 SSCAN
SSCAN myset 0 COUNT 100

# 위험 명령어 비활성화 (redis.conf)
rename-command KEYS ""
rename-command FLUSHALL ""
rename-command FLUSHDB ""
```

### 7.3 메모리 최적화

```redis
# 메모리 사용량 확인
INFO memory
# used_memory: 1073741824          # 실제 사용 메모리
# used_memory_rss: 1200000000      # OS가 할당한 메모리
# mem_fragmentation_ratio: 1.12    # 단편화 비율 (1.0~1.5 정상)

# 큰 키 찾기
redis-cli --bigkeys
# → 각 데이터 타입별 가장 큰 키 출력

# 특정 키의 메모리 사용량
MEMORY USAGE user:1000

# 메모리 정책 설정
CONFIG SET maxmemory 4gb
CONFIG SET maxmemory-policy allkeys-lru
```

```
메모리 정책 비교:
  noeviction:     메모리 초과 시 쓰기 거부 (기본값)
  allkeys-lru:    모든 키 대상 LRU 삭제 (캐시 용도 추천)
  volatile-lru:   TTL 설정된 키만 LRU 삭제
  allkeys-lfu:    모든 키 대상 LFU 삭제 (Redis 4.0+)
  volatile-lfu:   TTL 설정된 키만 LFU 삭제
  allkeys-random: 무작위 삭제
  volatile-random: TTL 설정된 키만 무작위 삭제
  volatile-ttl:   TTL이 짧은 키부터 삭제
```

### 7.4 Pipeline과 배치 처리

```
개별 요청:
  클라이언트 → SET a 1 → 응답 대기 → SET b 2 → 응답 대기 → ...
  총 시간: N × (명령 실행 + RTT)

Pipeline:
  클라이언트 → [SET a 1, SET b 2, GET c, ...] → 한 번에 전송
  서버 → [OK, OK, "value", ...] → 한 번에 응답
  총 시간: 1 × RTT + N × 명령 실행
```

```java
// Spring에서 Pipeline
List<Object> results = redisTemplate.executePipelined(
    (RedisCallback<Object>) connection -> {
        for (int i = 0; i < 1000; i++) {
            connection.stringCommands().set(
                ("key:" + i).getBytes(),
                ("value:" + i).getBytes()
            );
        }
        return null;  // Pipeline은 null 반환
    }
);

// Lettuce Reactive Pipeline (WebFlux 환경)
reactiveRedisTemplate.opsForValue()
    .multiSet(Map.of("k1", "v1", "k2", "v2", "k3", "v3"))
    .subscribe();
```

### 7.5 영속성 최적화

```conf
# RDB 최적화 (redis.conf)
save 900 1         # 15분 동안 1건 이상 변경 시
save 300 10        # 5분 동안 10건 이상 변경 시
save 60 10000      # 1분 동안 10000건 이상 변경 시
rdbcompression yes
rdbchecksum yes

# AOF 최적화
appendonly yes
appendfsync everysec                    # 1초마다 (권장)
no-appendfsync-on-rewrite yes           # RDB 저장 중 AOF fsync 건너뛰기
auto-aof-rewrite-percentage 100         # AOF 파일이 100% 커지면 재작성
auto-aof-rewrite-min-size 64mb          # 최소 64MB 이상일 때 재작성

# 하이브리드 (Redis 4.0+, 권장)
aof-use-rdb-preamble yes
# → AOF 재작성 시 RDB 형식 + 이후 변경분 AOF
# → 빠른 로딩 + 높은 내구성
```

```
RDB vs AOF 비교:
  ┌─────────────┬──────────────────┬──────────────────┐
  │             │      RDB         │      AOF         │
  ├─────────────┼──────────────────┼──────────────────┤
  │ 데이터 손실  │ 마지막 스냅샷 이후│ 최대 1초 (everysec)│
  │ 파일 크기    │ 작음 (압축)      │ 큼               │
  │ 복구 속도    │ 빠름            │ 느림             │
  │ 쓰기 부하    │ 포크 시 높음     │ 지속적 (낮음)     │
  │ 적합한 경우  │ 백업, 복제      │ 내구성 중시       │
  └─────────────┴──────────────────┴──────────────────┘
```

## 8. 운영 체크리스트

```
설정:
  □ maxmemory 설정 (물리 메모리의 70~80%)
  □ maxmemory-policy 설정 (용도에 맞게)
  □ 영속성 전략 선택 (RDB + AOF 하이브리드 권장)
  □ 위험 명령어 rename/비활성화

보안:
  □ requirepass 설정
  □ bind 127.0.0.1 (외부 접근 차단)
  □ protected-mode yes
  □ ACL 설정 (사용자별 권한)
  □ TLS 암호화 (프로덕션)

모니터링:
  □ INFO 명령어 주기적 수집
  □ Slow Log 모니터링
  □ 메모리 사용량 알림
  □ 연결 수 모니터링
  □ 복제 지연(lag) 모니터링

고가용성:
  □ Sentinel 또는 Cluster 구성
  □ 자동 페일오버 테스트
  □ 백업 스케줄 + 복구 테스트
  □ 장애 대응 절차 문서화
```

## 참고

- [Redis 공식 문서](https://redis.io/docs/)
- [Redis Cluster 튜토리얼](https://redis.io/docs/management/scaling/)
- [Redisson](https://github.com/redisson/redisson) — Java Redis 클라이언트
- [Redis 다루기](Redis%20다루기.md) — Redis 기본 사용법
- [Redis 개요](Redis.md) — Redis 데이터 타입과 아키텍처
- [Caching 전략](../../../Backend/Caching/Caching_Strategies.md) — 캐싱 패턴
- [분산 트랜잭션](../../../Application%20Architecture/MSA/Saga_패턴_및_분산_트랜잭션.md) — 분산 시스템 패턴
