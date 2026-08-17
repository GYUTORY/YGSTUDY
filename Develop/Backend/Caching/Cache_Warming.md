---
title: Cache Warming
tags: [cache, redis, monitoring, backend]
updated: 2026-08-17
---

# 캐시 워밍

캐시 워밍은 서버가 트래픽을 받기 전에 캐시를 미리 채우는 작업이다. 배포 직후 빈 캐시 상태에서 요청이 들어오면 모든 쿼리가 DB로 직접 떨어진다. 이 구간을 Cold Start라고 부른다.

## Cold Start 문제

새 서버 인스턴스가 뜨거나 Redis가 재시작되면 캐시는 비어있다. 평소 Redis 히트율이 95%였다면 배포 직후 수 분간 DB 쿼리가 수십 배로 치솟는다. 트래픽이 작으면 DB가 버티지만, 피크 타임에 배포했거나 Redis 노드 장애 후 복구 직후라면 DB가 응답을 못하기 시작한다.

실제로 겪은 패턴은 이렇다. 새벽 2시에 배포하고, 아침 9시 출근 트래픽 급증 전에 워밍이 완료되어야 한다. 그 사이에 사전 적재가 실패하면 9시 정각에 DB가 죽는다.

더 심각한 상황은 Cache Stampede다. 캐시가 비어있을 때 같은 키를 요청하는 수백 개의 스레드가 동시에 DB를 조회한다. Lock이나 PER(Probabilistic Early Recomputation) 없이는 워밍 전에 DB가 다운될 수 있다. Cache Stampede 방지 구현은 [Node Cache Advanced](../../Framework/Node/캐싱/Node_Cache_Advanced.md)에 코드로 정리돼 있다.

## Lazy Warming vs Eager Warming

Lazy Warming은 요청이 들어올 때 캐시 미스가 발생하면 그 시점에 DB에서 읽어 캐시를 채우는 방식이다. Cache-Aside 패턴 자체가 Lazy Warming이다.

구현이 단순하고 실제로 요청되는 데이터만 캐시에 들어간다. 단점은 Cold Start 구간에서 Cache Stampede에 노출된다는 점이다.

Eager Warming은 서버가 트래픽을 받기 전에 미리 캐시를 채우는 방식이다. 배치 스크립트나 애플리케이션 초기화 로직에서 DB를 읽어 Redis에 적재한다. 트래픽을 받기 전에 준비가 완료된다.

단점은 무엇을 얼마나 미리 채울지 결정하기 어렵다는 점이다. 전체 데이터를 다 넣으면 Redis 메모리가 부족할 수 있고, 너무 조금 넣으면 효과가 없다. 적재할 키 목록을 관리하는 비용도 든다.

실무에서는 두 방식을 섞어서 쓴다. 조회 빈도 상위 N개(예: 상품 TOP 500)는 Eager Warming으로 미리 채우고, 나머지는 Lazy Warming에 맡긴다.

## 사전 적재 스크립트 패턴

### 배치 방식

배포 파이프라인에 캐시 워밍 단계를 추가하는 방식이다. 애플리케이션 서버가 뜨기 전에 별도 스크립트가 Redis를 채운다.

```bash
# deploy.sh
echo "Starting cache warming..."
java -jar cache-warmer.jar --spring.profiles.active=prod

if [ $? -ne 0 ]; then
  echo "Cache warming failed. Aborting deployment."
  exit 1
fi

echo "Starting app server..."
./start-app.sh
```

```java
@SpringBootApplication
public class CacheWarmerApplication implements CommandLineRunner {

    @Autowired
    private ProductCacheWarmer productWarmer;

    @Autowired
    private CategoryCacheWarmer categoryWarmer;

    @Override
    public void run(String... args) {
        categoryWarmer.warmUp();
        productWarmer.warmTopN(500);
    }
}
```

```java
@Component
public class ProductCacheWarmer {

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    public void warmTopN(int limit) {
        List<Product> topProducts = productRepository.findTopByViewCount(limit);

        // Pipeline으로 묶지 않으면 500개 상품에 500번 네트워크 왕복이 발생한다
        redisTemplate.executePipelined((RedisCallback<Object>) conn -> {
            for (Product p : topProducts) {
                String key = "product::" + p.getId();
                byte[] value = serialize(p);
                conn.setEx(key.getBytes(), 3600, value);
            }
            return null;
        });
    }
}
```

Pipeline 없이 500개를 개별로 넣으면 네트워크 왕복이 500번이다. Pipeline으로 묶으면 단일 왕복으로 처리된다.

### API 호출 방식

서버 기동 후 내부 서비스 메서드를 순차 호출해 캐시를 채우는 방식이다. 별도 배치 JAR 없이 `@EventListener`로 처리한다.

```java
@Component
public class ApplicationReadyWarmer {

    @Autowired
    private ProductService productService;

    @Autowired
    private ProductRepository productRepository;

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        List<Long> topIds = productRepository.findTopIdsByViewCount(500);
        for (Long id : topIds) {
            // @Cacheable이 붙어있으면 이 호출이 Redis를 채워준다
            productService.getProduct(id);
        }
    }
}
```

`ApplicationReadyEvent`는 HTTP 포트가 열린 후에 발생한다. 워밍이 끝나기 전에 로드밸런서가 트래픽을 보내면 Cold Start 상태에서 요청을 처리하게 된다. 헬스체크 연동이 없으면 이 방식만으로는 Cold Start를 막을 수 없다.

## 동시 워밍 충돌

Rolling deploy나 HPA에 의한 스케일아웃으로 인스턴스 여러 대가 동시에 뜨면, 각 인스턴스가 독립적으로 워밍 로직을 실행한다. Redis는 공유 저장소라 최종적으로 같은 키가 들어가지만 DB 쿼리는 인스턴스 수만큼 중복으로 나간다.

인스턴스 5대가 동시에 뜨면서 각자 상품 500개를 DB에서 읽으면 2,500번의 쿼리가 거의 동시에 발생한다. 아무 조치 없이 스케일아웃하다가 DB 커넥션 풀이 바닥나는 상황이 이렇게 만들어진다.

### 분산 락으로 단일 인스턴스만 워밍

```java
@Component
public class DistributedCacheWarmer {

    private static final String WARMING_LOCK_KEY = "cache:warming:lock";
    private static final long LOCK_TTL_SECONDS = 300; // 워밍 최대 소요 시간의 2배

    @Autowired
    private StringRedisTemplate redisTemplate;

    public void warmWithLock() throws InterruptedException {
        Boolean acquired = redisTemplate.opsForValue()
            .setIfAbsent(WARMING_LOCK_KEY, "locked", LOCK_TTL_SECONDS, TimeUnit.SECONDS);

        if (!Boolean.TRUE.equals(acquired)) {
            log.info("Cache warming skipped — another instance holds the lock");
            waitForWarmingComplete();
            return;
        }

        try {
            warmCache();
        } finally {
            redisTemplate.delete(WARMING_LOCK_KEY);
        }
    }

    private void waitForWarmingComplete() throws InterruptedException {
        int attempts = 0;
        while (Boolean.TRUE.equals(redisTemplate.hasKey(WARMING_LOCK_KEY)) && attempts < 60) {
            Thread.sleep(5_000);
            attempts++;
        }
    }
}
```

락 TTL은 워밍 최대 소요 시간보다 충분히 길게 잡는다. 10초 워밍에 TTL을 15초로 잡으면, 서버가 워밍 도중 죽었을 때 락이 해제되기까지 15초 동안 다른 인스턴스들이 Readiness를 올리지 못한다. 반대로 TTL이 너무 짧으면 워밍이 끝나기 전에 다른 인스턴스가 락을 다시 잡고 중복 워밍이 시작된다. 실측 워밍 시간의 2배를 TTL로 쓰는 것이 실용적이다.

### 키 존재 여부 확인 후 스킵

```java
public void warmIfEmpty() {
    // 대표 키가 이미 존재하면 다른 인스턴스가 워밍을 완료한 것
    Boolean exists = redisTemplate.hasKey("product::warming-done");
    if (Boolean.TRUE.equals(exists)) {
        log.info("Cache already warmed by another instance, skipping");
        return;
    }
    warmCache();
    redisTemplate.opsForValue().set("product::warming-done", "1", 3600, TimeUnit.SECONDS);
}
```

락보다 단순하지만 인스턴스 수십 대가 거의 동시에 `hasKey`를 확인하면 모두 "없다"고 판단하고 동시에 워밍을 시작할 수 있다. 인스턴스가 2~3대이고 워밍이 멱등성을 가진다면(같은 키를 덮어써도 무방하다면) 이 방식으로 충분하다.

### 쿠버네티스 Init Container 분리

```yaml
initContainers:
- name: cache-warmer
  image: myapp:latest
  command: ["java", "-jar", "app.jar", "--spring.profiles.active=warmer"]
  resources:
    limits:
      memory: "512Mi"
```

Init Container는 메인 컨테이너보다 먼저 실행되고, 종료 코드가 0이어야 메인 컨테이너가 시작된다. 파드가 여러 개여도 Init Container는 각 파드 안에서 실행되므로 중복 워밍 문제 자체는 남는다. 분산 락과 조합하거나, 아예 워밍 전용 Job을 Deployment 이전에 실행하는 방식으로 풀어야 한다.

## Redis SCAN 기반 키 재적재

Redis 장애 복구 후 기존 키 패턴을 기반으로 재적재할 때 쓰는 방식이다.

`KEYS *`는 Redis를 블로킹한다. 프로덕션에서는 반드시 `SCAN`을 써야 한다.

```java
public List<String> scanKeys(String pattern) {
    List<String> result = new ArrayList<>();
    ScanOptions options = ScanOptions.scanOptions()
        .match(pattern)
        .count(100) // 한 번에 처리할 힌트값. 정확한 개수를 보장하지 않는다
        .build();

    try (Cursor<byte[]> cursor = redisTemplate.getConnectionFactory()
            .getConnection()
            .scan(options)) {
        while (cursor.hasNext()) {
            result.add(new String(cursor.next()));
        }
    }
    return result;
}
```

```java
public void reloadProductCache() {
    List<String> existingKeys = scanKeys("product::*");

    List<Long> ids = existingKeys.stream()
        .map(key -> Long.parseLong(key.replace("product::", "")))
        .collect(Collectors.toList());

    List<Product> products = productRepository.findAllById(ids);

    redisTemplate.executePipelined((RedisCallback<Object>) conn -> {
        for (Product p : products) {
            String key = "product::" + p.getId();
            conn.setEx(key.getBytes(), 3600, serialize(p));
        }
        return null;
    });
}
```

`count` 옵션은 Redis가 한 번에 반환할 개수의 힌트일 뿐 정확한 값이 아니다. Cursor를 끝까지 소진해야 전체 키셋 탐색이 완료된다.

키가 수십만 개라면 SCAN 자체도 Redis에 부하를 준다. 새벽 트래픽이 적은 시간에 돌리거나, 처리 속도를 조절한다. 처리 속도 조절이 필요하면 루프마다 짧은 sleep을 넣거나 배치 크기를 줄인다.

### maxmemory eviction과의 충돌

SCAN으로 키를 수집한 뒤 Pipeline으로 대량 적재할 때 Redis가 `maxmemory`에 걸려 있으면 두 가지 방식으로 실패한다.

`maxmemory-policy`가 `noeviction`이면 메모리가 꽉 찬 상태에서 쓰기 명령은 에러를 반환한다. Pipeline으로 보낸 명령은 서버 측에서 에러로 처리되지만 `executePipelined`가 예외를 던지지 않는 경우가 있다(Spring Data Redis 버전에 따라 다르다). 워밍이 정상적으로 완료됐다고 판단했는데 실제로는 하나도 적재되지 않은 상황이 만들어진다.

`allkeys-lru`면 Redis가 자동으로 오래된 키를 제거하며 공간을 만든다. 문제는 방금 워밍해서 넣은 키들이 아직 접근된 적이 없어 LRU 스코어가 낮다는 점이다. 기존에 자주 쓰이던 키들 대신 방금 넣은 키들이 먼저 제거되는 상황이 발생한다.

적재 전 메모리 여유를 먼저 확인한다:

```java
public void reloadWithMemoryCheck() {
    Properties info = redisTemplate.execute(
        (RedisCallback<Properties>) conn -> conn.info("memory")
    );

    long usedMemory = Long.parseLong(info.getProperty("used_memory"));
    long maxMemory = Long.parseLong(info.getProperty("maxmemory")); // 0이면 무제한

    if (maxMemory > 0) {
        long available = maxMemory - usedMemory;
        long estimatedNeeded = estimateWarmingBytes();

        if (available < estimatedNeeded * 1.2) { // 20% 여유 포함
            log.warn("Redis memory too tight. available={}MB, needed={}MB",
                available / 1024 / 1024, estimatedNeeded / 1024 / 1024);
            // 전체가 아닌 적재 가능한 수만 워밍
            warmTopN(estimateFittableCount(available));
            return;
        }
    }

    reloadProductCache();
}

private long estimateWarmingBytes() {
    // 대표 키 1개의 실제 메모리 사용량으로 전체 추정
    // redis-cli에서: MEMORY USAGE product::1
    Long sampleSize = redisTemplate.execute(
        (RedisCallback<Long>) conn -> conn.memoryUsage("product::1".getBytes())
    );
    long perKey = (sampleSize != null) ? sampleSize : 4096L; // 측정 불가 시 4KB 가정
    return perKey * warmingTargetCount;
}
```

`volatile-lru`나 `volatile-ttl`을 쓰는 환경에서 워밍 시 TTL을 설정하지 않으면 해당 키는 eviction 대상에서 제외된다. 메모리 압박 시 TTL 있는 다른 키들이 먼저 제거되고 워밍 키는 남는다. 의도적으로 쓸 수 있는 방법이지만, TTL 없이 남은 키는 데이터가 변경돼도 캐시가 갱신되지 않는다. 이벤트 기반 무효화나 별도 갱신 주기 없이는 오래된 데이터를 계속 서빙하게 된다.

워밍 전후 eviction 발생 여부를 확인한다:

```bash
# 워밍 전 기록
redis-cli info stats | grep evicted_keys

# 워밍 후 비교 — evicted_keys가 크게 늘었으면 메모리 계획을 재검토한다
redis-cli info stats | grep evicted_keys
```

## 워밍 완료 여부 헬스체크 연동

API 호출 방식으로 워밍할 때 로드밸런서에 "아직 준비 안 됐음"을 알리려면 헬스체크 엔드포인트와 연동해야 한다.

```java
@Component
public class CacheWarmingHealthIndicator implements HealthIndicator {

    private volatile boolean warmed = false;

    public void markWarmed() {
        this.warmed = true;
    }

    @Override
    public Health health() {
        if (warmed) {
            return Health.up().build();
        }
        return Health.down()
            .withDetail("reason", "cache warming in progress")
            .build();
    }
}
```

```java
@Component
public class ApplicationReadyWarmer {

    @Autowired
    private CacheWarmingHealthIndicator healthIndicator;

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        try {
            warmCache();
        } catch (Exception e) {
            log.error("Cache warming failed", e);
            alertingService.warn("Cache warming failed on startup");
            // 워밍이 실패해도 서버를 죽이지 않는다. UP으로 올린 뒤 모니터링이 대응한다
        } finally {
            healthIndicator.markWarmed();
        }
    }
}
```

```yaml
# application.yml
management:
  endpoint:
    health:
      show-details: always
```

AWS ALB나 Kubernetes readiness probe는 헬스체크가 `UP`을 반환할 때까지 트래픽을 보내지 않는다.

```yaml
readinessProbe:
  httpGet:
    path: /actuator/health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 30  # 150초 동안 대기
```

`failureThreshold * periodSeconds`가 워밍에 필요한 최대 시간보다 길어야 한다. 짧게 잡으면 워밍이 끝나기 전에 `Unhealthy`로 판정돼 파드가 재시작된다. 워밍 실측 시간을 배포 로그에서 측정해 이 값을 결정한다.

## 워밍이 실패하는 사례

### 배포 타이밍 미스

배포 완료 시각과 트래픽 피크 사이에 워밍 시간이 충분하지 않은 경우다. Redis Pipeline으로 500개 상품을 적재하면 통상 1~2초면 끝난다. DB가 느리거나 워밍 대상이 수만 건이면 수십 초에서 수 분이 걸린다.

피크 1시간 전에 배포가 끝나도록 배포 윈도우를 잡는다. 워밍에 걸리는 실측 시간을 배포 파이프라인 로그에서 측정해 관리한다.

### 워밍 대상이 너무 많은 경우

"전체 상품을 워밍하자"는 결정은 대부분 틀린다. 상품 100만 건을 전부 Redis에 올리면 메모리가 부족하거나 워밍에만 수십 분이 걸린다.

Redis의 `maxmemory-policy`가 `allkeys-lru`라면 자주 안 쓰이는 키는 어차피 밀려난다. 처음부터 실측 데이터 기반으로 상위 N개만 워밍하는 게 낫다.

```java
// 전체 상품 조회 — OOM 가능
List<Product> all = productRepository.findAll();

// 최근 7일 조회수 상위 500개만
List<Product> top = productRepository.findTopByViewCountLastDays(500, 7);
```

### 키 포맷 불일치

배치 스크립트가 `product:123` 형식으로 넣었는데 서버가 `product::123` (Spring Cache 기본 키 포맷)으로 읽으면 캐시 미스가 발생한다.

Spring Cache의 키 형식은 `cacheName::cacheKey`다. `RedisSerializer` 설정에 따라 JSON 직렬화 여부도 달라진다. 워밍 스크립트는 서버와 동일한 키 생성 로직을 써야 한다.

실제 Redis에 들어간 키를 `redis-cli --scan --pattern 'product*'`로 확인한 뒤 스크립트를 맞추는 게 가장 확실하다.

### Redis 장애 후 워밍 재시도 없음

서버 기동 시점에 Redis가 응답을 못하면 워밍이 실패하고 그 상태로 운영이 시작된다. 이후 Redis가 복구돼도 서버는 워밍 재시도를 하지 않는다.

```java
@Scheduled(fixedDelay = 60_000)
public void checkAndWarmIfNeeded() {
    if (!redisAvailable()) return;

    double hitRate = cacheMetrics.getHitRate();
    if (hitRate > 0.8) return;

    log.warn("Cache hit rate={}, re-warming...", hitRate);
    warmCache();
}
```

프로메테우스로 캐시 히트율을 모니터링하고 있다면 히트율이 임계값 아래로 떨어질 때 워밍을 트리거하는 방식도 쓸 수 있다. 다만 히트율 저하 원인이 워밍 실패가 아닌 경우(예: 트래픽 패턴 변화)에도 불필요한 재적재가 발생할 수 있다. 원인을 구분하는 지표(최근 배포 여부, Redis 재시작 이벤트)를 함께 보고 판단한다.
