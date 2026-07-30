---
title: Redisson 분산 락 심화
tags: [redis, redisson, distributed-lock, rlock, rreadwritelock, rsemaphore, redlock, watchdog]
updated: 2026-07-30
---

# Redisson 분산 락 심화

단일 서버라면 `synchronized`나 `ReentrantLock`으로 임계 구역을 보호할 수 있다. 서버가 여러 대면 JVM 레벨의 락은 의미가 없다. 각 서버가 독립적인 메모리 공간을 갖기 때문에 A 서버에서 락을 잡아도 B 서버는 알 수 없다.

Redisson은 Redis를 락 저장소로 쓰는 Java 분산 락 라이브러리다. `spring-boot-starter-data-redis`로 `SET NX PX`를 직접 구현하는 방법도 있지만, 워치독, 재진입, 공정 락, 락 해제 알림 등 edge case를 모두 직접 처리해야 한다. Redisson은 이것들을 구현해둔 것이다.

## 락 종류 비교

### RLock

재진입 가능한 상호 배제 락으로, `java.util.concurrent.locks.Lock` 인터페이스를 구현한다.

```java
RLock lock = redissonClient.getLock("order:lock:" + orderId);
try {
    // waitTime: 락 획득을 포기하기 전 대기 시간
    // leaseTime: 락 보유 최대 시간. -1이면 워치독 활성화
    boolean acquired = lock.tryLock(5, 30, TimeUnit.SECONDS);
    if (!acquired) {
        throw new LockAcquisitionException("락 획득 실패");
    }
    processOrder(orderId);
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

재진입이 가능하다는 점을 주의해야 한다. 같은 스레드가 이미 락을 보유한 상태에서 다시 `lock()`을 호출하면 즉시 성공한다. 카운터가 Redis에 저장되기 때문에 `unlock()` 호출 횟수가 `lock()` 횟수와 일치해야 락이 실제로 해제된다. 재진입이 중첩된 상황에서 중간에 예외가 발생하면 락이 해제되지 않는 경우가 생긴다.

### RReadWriteLock

읽기-쓰기 구분이 필요할 때 쓴다. 읽기 락은 여러 스레드가 동시에 보유할 수 있고, 쓰기 락은 단독으로 보유해야 한다. 읽기 락이 잡혀 있으면 쓰기 락 획득은 블로킹되고, 쓰기 락이 잡혀 있으면 읽기 락도 블로킹된다.

```java
RReadWriteLock rwLock = redissonClient.getReadWriteLock("product:rwlock:" + productId);

// 읽기 - 여러 스레드가 동시에 진입 가능
RLock readLock = rwLock.readLock();
readLock.lock();
try {
    return productRepository.findById(productId);
} finally {
    readLock.unlock();
}

// 쓰기 - 단독 진입만 허용
RLock writeLock = rwLock.writeLock();
writeLock.lock();
try {
    productRepository.save(product);
} finally {
    writeLock.unlock();
}
```

읽기가 쓰기보다 압도적으로 많은 경우에 유효하다. 읽기와 쓰기 비율이 비슷하거나 쓰기가 많으면 일반 RLock 대비 이점이 없다. 캐시 갱신이나 설정 리로드처럼 빈도가 낮은 쓰기 작업에 적합하다.

### RSemaphore

동시 실행 개수를 제한할 때 쓴다. 특정 외부 API가 동시 10개 요청까지만 허용하는 경우, 서버가 여러 대여도 전체 동시 요청 수를 10개로 제한할 수 있다.

```java
RSemaphore semaphore = redissonClient.getSemaphore("external-api:permits");
semaphore.trySetPermits(10);  // 이미 값이 있으면 무시된다

try {
    boolean acquired = semaphore.tryAcquire(3, TimeUnit.SECONDS);
    if (!acquired) {
        throw new TooManyRequestsException("외부 API 요청 한도 초과");
    }
    return externalApiClient.call();
} finally {
    semaphore.release();
}
```

`trySetPermits`는 이미 값이 있으면 무시된다. 애플리케이션 재시작 시 이전 값을 유지한다는 뜻인데, 장애 상황에서 permit이 반납되지 않으면 세마포어가 영구 고갈될 수 있다. 이 경우 `semaphore.addPermits(n)`으로 수동 복구해야 한다.

### RPermitExpirableSemaphore

RSemaphore와 거의 동일하지만 각 permit에 TTL을 붙일 수 있다. 보유자가 죽어도 TTL이 지나면 자동 반납된다.

```java
RPermitExpirableSemaphore semaphore = redissonClient.getPermitExpirableSemaphore("batch:semaphore");
semaphore.trySetPermits(5);

// waitTime=2초, leaseTime=60초
String permitId = semaphore.tryAcquire(2, 60, TimeUnit.SECONDS);
if (permitId == null) {
    throw new SemaphoreException("permit 획득 실패");
}
try {
    runBatchJob();
} finally {
    semaphore.release(permitId);
}
```

permitId를 키로 관리하기 때문에 어떤 스레드든 해당 permitId로 반납할 수 있다. 비동기 처리나 스레드 간 permit 전달이 필요한 경우에 쓴다. RSemaphore보다 Redis 내부 연산이 더 복잡하기 때문에 TTL 기반 자동 반납이 필요한 경우에만 선택한다.

---

| 종류 | 동시 접근 | 재진입 | TTL 자동 반납 | 주 사용 사례 |
|---|---|---|---|---|
| RLock | 단독 | O | 워치독 설정 시 | 임계 구역 보호 |
| RReadWriteLock | 읽기 다수 / 쓰기 단독 | O | 워치독 설정 시 | 읽기 다수 환경 |
| RSemaphore | N개 동시 허용 | X | X | 동시 실행 수 제한 |
| RPermitExpirableSemaphore | N개 동시 허용 | X | O (per-permit TTL) | 비동기 작업 수 제한 |

## 워치독 동작 방식

leaseTime을 -1로 설정하거나 `lock()`을 인수 없이 호출하면 워치독이 활성화된다.

```java
lock.lock();  // leaseTime 지정 없음 -> 워치독 활성화
// 또는
lock.tryLock(5, -1, TimeUnit.SECONDS);  // leaseTime=-1 -> 워치독 활성화
```

워치독은 Redisson 내부의 별도 타이머 스레드로 동작한다. 기본 TTL(`lockWatchdogTimeout`)은 30초이고, 이 값의 1/3 주기(10초)마다 락 TTL을 30초로 갱신한다. 락을 보유한 JVM이 살아있는 한 락이 만료되지 않는다.

워치독의 한계는 GC stop-the-world나 스레드 일시 중단에 있다. JVM이 수십 초 멈추면 워치독도 같이 멈춰서 TTL 갱신을 못 한다. Redis TTL이 만료되면 다른 서버가 락을 획득하고, 원래 보유자가 재개되면 두 프로세스가 동시에 임계 구역에 진입하는 상황이 발생한다.

leaseTime을 명시적으로 설정하면 워치독이 비활성화된다. 임계 구역 실행 시간이 leaseTime을 초과하면 락이 먼저 해제되고 다른 스레드가 진입할 수 있다. leaseTime은 "최악의 경우 임계 구역 실행 시간"보다 충분히 길게 설정해야 하고, 그 시간을 예측하기 어려우면 워치독을 쓰는 편이 낫다.

## tryLock 타임아웃 설정 실수

**waitTime을 0으로 설정하고 재시도 없이 실패 처리**

```java
boolean acquired = lock.tryLock(0, 30, TimeUnit.SECONDS);
if (!acquired) {
    throw new RuntimeException("처리 중인 요청입니다");
}
```

락 경합이 조금이라도 있으면 대부분 실패한다. 중복 방지를 의도한 경우라면 문제없지만, 반드시 처리되어야 하는 작업(재고 차감, 결제)에서 이 패턴을 쓰면 요청이 유실된다.

**finally 없이 unlock() 호출**

```java
lock.lock();
doWork();
lock.unlock();  // doWork()에서 예외 발생 시 실행 안 됨
```

예외가 발생하면 워치독이 없는 경우 Redis TTL(기본 30초) 만료까지 다른 프로세스가 블로킹된다. 반드시 try-finally로 감싸야 한다.

**isHeldByCurrentThread 확인 없이 unlock**

```java
finally {
    lock.unlock();  // TTL 만료 후 호출하거나 이미 해제된 락을 해제하면 예외
}
```

`IllegalMonitorStateException`이 발생한다. TTL이 만료되어 다른 스레드가 락을 가져간 상황에서 원래 보유자가 unlock을 시도하면, Redis에 저장된 락 보유자 식별자가 다르기 때문에 Redisson이 예외를 던진다.

```java
// 올바른 패턴
try {
    boolean acquired = lock.tryLock(5, 30, TimeUnit.SECONDS);
    if (!acquired) {
        throw new LockAcquisitionException("락 획득 실패");
    }
    doWork();
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

## Redlock 알고리즘과 Martin Kleppmann 논쟁

Redis 창시자 antirez(Salvatore Sanfilippo)가 2016년에 제안한 알고리즘이다. 단일 Redis 노드 장애 시 락 안전성을 확보하기 위해 N개(보통 5개)의 독립 Redis 노드에 과반수(N/2+1) 획득을 조건으로 한다.

알고리즘 순서:
1. 현재 시간을 ms 단위로 기록한다
2. 동일한 키와 랜덤 값으로 N개 노드 모두에 락 획득을 시도한다. 각 노드당 짧은 타임아웃을 적용해 느린 노드에서 블로킹되지 않도록 한다
3. N/2+1개 이상에서 성공하고, 경과 시간이 TTL 미만이면 락 획득으로 간주한다
4. 실패하면 모든 노드에서 락을 해제한다

Martin Kleppmann(DDIA 저자)은 같은 해 블로그 포스트에서 이 알고리즘이 안전하지 않다고 주장했다.

**GC pause로 인한 안전성 파괴**

클라이언트 A가 락을 획득했다. GC stop-the-world가 30초 발생했다. 그 사이 TTL이 만료되어 클라이언트 B가 락을 획득했다. A가 재개되어 작업을 계속 수행한다. A와 B 모두 락을 보유한 상태에서 임계 구역에 진입하는 상황이 된다.

```
Client A: [lock acquired] ... [GC pause 30s] ... [continues work]
Redis TTL:                    [TTL expired]
Client B:                                   [lock acquired] [begins work]

-> A와 B 동시에 임계 구역 진입
```

Kleppmann은 이 문제를 해결하려면 펜싱 토큰이 필요하다고 주장했다. 락 획득 시마다 단조 증가하는 토큰을 발급하고, 스토리지에 쓸 때 토큰 값이 현재 저장된 것보다 큰 경우만 허용하면 된다. Redis는 이 메커니즘을 기본 제공하지 않는다.

**시스템 클럭 의존성**

Redlock은 TTL 계산에 클럭을 사용한다. Redis 노드 중 하나의 시스템 클럭이 앞으로 점프하면(NTP 동기화, VM 클럭 조정 등), 그 노드에서 TTL이 조기 만료된다. 과반수 노드의 락이 살아있어도 일부 노드에서는 다른 클라이언트가 락을 획득할 수 있다.

antirez는 대부분의 클럭 점프는 관리자가 막을 수 있다고 반박했다. 하지만 "운영자가 잘 관리하면 안전하다"는 가정은 분산 시스템 설계의 기본 원칙인 "노드는 언제든 실패할 수 있다"와 상충한다.

**실무에서의 선택**

Redlock을 실제로 5개 Redis 노드로 구성해서 운영하는 경우는 많지 않다. Redlock이 해결하려는 문제(Redis 단일 노드 장애)는 Sentinel이나 Cluster로 가용성을 높이는 방향이 현실적이다. 진정한 선형화 보장이 필요하면 ZooKeeper나 etcd 기반 락을 써야 한다.

Redisson은 `RedissonRedLock`으로 Redlock을 구현했지만 4.x 이후 deprecated됐다. 단일 노드 RLock 또는 Cluster 환경의 RLock 사용을 권장한다.

## Redis 장애 시 폴백 패턴

Redis가 다운되면 분산 락을 쓸 수 없다. 선택지는 크게 두 가지다.

**락 획득 실패를 서비스 불가로 처리**

정합성이 필수인 경우 적합하다. Redis 장애 시 해당 기능이 동작하지 않는 것을 감수한다.

```java
try {
    boolean acquired = lock.tryLock(3, 30, TimeUnit.SECONDS);
    if (!acquired) {
        throw new ServiceUnavailableException("잠시 후 재시도");
    }
    processOrder();
} catch (RedisConnectionFailureException e) {
    log.error("Redis 연결 실패 - 분산 락 불가", e);
    throw new ServiceUnavailableException("분산 락 서비스 불가");
}
```

**DB 기반 폴백 락**

Redis 장애 시 DB 레벨 락으로 폴백하는 방식이다. 성능은 떨어지지만 Redis 없이도 정합성을 유지한다.

```java
@Service
public class DistributedLockService {
    private final RedissonClient redissonClient;
    private final EntityManager entityManager;

    public <T> T executeWithLock(String lockKey, Supplier<T> supplier) {
        try {
            return executeWithRedisLock(lockKey, supplier);
        } catch (RedisConnectionFailureException e) {
            log.warn("Redis 락 실패, DB 락으로 폴백: {}", lockKey);
            return executeWithDatabaseLock(lockKey, supplier);
        }
    }

    private <T> T executeWithRedisLock(String lockKey, Supplier<T> supplier) {
        RLock lock = redissonClient.getLock(lockKey);
        boolean acquired;
        try {
            acquired = lock.tryLock(5, 30, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new LockAcquisitionException("락 대기 중단");
        }
        if (!acquired) {
            throw new LockAcquisitionException("Redis 락 획득 실패");
        }
        try {
            return supplier.get();
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    private <T> T executeWithDatabaseLock(String lockKey, Supplier<T> supplier) {
        // MySQL GET_LOCK() 사용
        Query lockQuery = entityManager.createNativeQuery(
            "SELECT GET_LOCK(:key, 10)"
        ).setParameter("key", lockKey);

        Number result = (Number) lockQuery.getSingleResult();
        if (result.intValue() != 1) {
            throw new LockAcquisitionException("DB 락 획득 실패");
        }
        try {
            return supplier.get();
        } finally {
            entityManager.createNativeQuery("SELECT RELEASE_LOCK(:key)")
                .setParameter("key", lockKey)
                .executeUpdate();
        }
    }
}
```

폴백 패턴의 단점은 두 락 구현을 모두 관리해야 한다는 점이다. DB 락 구현이 올바르지 않으면 폴백이 오히려 더 위험하다. Redis 가용성을 Sentinel이나 Cluster로 충분히 높이면 폴백 없이 운영하는 경우도 많다.

**Redis Sentinel Failover 시 주의점**

Sentinel이 마스터 장애를 감지하고 슬레이브를 새 마스터로 승격하는 데 수 초가 걸린다. 이 구간에서 마스터에 저장된 락 정보가 슬레이브에 복제되지 않은 상태에서 failover가 발생하면, 새 마스터에서 다른 클라이언트가 같은 키로 락을 획득해 두 클라이언트가 동시에 락을 보유하게 된다.

이 문제는 Redlock이 해결하려 했던 시나리오와 동일하다. Sentinel 환경에서도 이 짧은 failover 구간의 위험은 존재한다. 실무에서는 이 구간의 위험을 감수하거나, 임계 구역 내 DB 레벨 제약(UNIQUE 제약, CAS 업데이트)으로 최종 안전망을 구성한다.

```java
// DB UNIQUE 제약을 최종 안전망으로 사용하는 패턴
@Transactional
public void createOrder(CreateOrderRequest request) {
    // 분산 락으로 1차 보호
    RLock lock = redissonClient.getLock("order:lock:" + request.getUserId());
    // ...

    // DB UNIQUE 제약으로 2차 보호 - 분산 락 구간에 중복이 생겨도 여기서 걸린다
    // orders 테이블의 (user_id, idempotency_key) UNIQUE 제약
    orderRepository.save(new Order(request));
}
```
