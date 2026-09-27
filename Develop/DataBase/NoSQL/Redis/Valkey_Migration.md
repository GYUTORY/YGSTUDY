---
title: Valkey 마이그레이션
tags: [redis, cache, aws, backend]
updated: 2026-09-27
---

# Valkey 마이그레이션

## 왜 Valkey가 나왔는가

2024년 3월, Redis Ltd는 Redis 7.4부터 BSD 라이선스를 버리고 SSPL(Server Side Public License)과 RSAL(Redis Source Available License)을 선택했다. SSPL은 오픈소스 라이선스가 아니다. 이 라이선스 아래서는 Redis를 서비스로 판매하는 사업자도 소스를 공개해야 한다. AWS, Google, Oracle, Alibaba처럼 관리형 Redis 서비스를 운영하던 클라우드 벤더들이 직격탄을 맞았다.

같은 달 Linux Foundation이 Valkey 프로젝트를 설립했다. Redis 7.2.4 — BSD 라이선스가 적용된 마지막 버전 — 를 베이스로 포크했다. AWS, Google Cloud, Oracle, Alibaba Cloud, Ericsson이 초기 기여자로 참여했고 BSD 3-clause 라이선스를 유지한다.

포크 시점이 7.2.4이기 때문에 Redis 7.4에서 추가된 기능들은 Valkey 7.x에 없다.

| Redis 7.4 신기능 | Valkey 7.x |
|---|---|
| Hash field expiry (필드 단위 TTL) | 없음 |
| 클러스터 링크 압축 | 없음 |
| ACL 로그 개선 | 없음 |
| `LPOS` RANK·MAXLEN 확장 | 없음 |

Valkey는 8.0부터 자체 로드맵으로 기능을 추가하고 있다. Redis 7.4+ 기능에 의존하는 코드가 있다면 Valkey 전환 전에 반드시 확인해야 한다.

## 명령어 호환성

Redis 7.2와 Valkey 7.x는 RESP2·RESP3 프로토콜 수준에서 동일하다. 일반적인 캐싱 용도(GET, SET, DEL, EXPIRE, TTL)는 재컴파일 없이 동작한다.

### 실제로 확인해야 하는 영역

| 분류 | 상태 |
|---|---|
| 핵심 명령어 (GET, SET, DEL, EXPIRE, TTL, MGET, MSET) | 완전 호환 |
| Lua 스크립트 (`EVAL`, `EVALSHA`, `SCRIPT LOAD`) | 완전 호환 |
| Pub/Sub (`PUBLISH`, `SUBSCRIBE`, `PSUBSCRIBE`) | 완전 호환 |
| Streams (`XADD`, `XREAD`, `XGROUP`, `XACK`) | 완전 호환 |
| 분산 락 (`SET … NX EX`, `SETNX`) | 완전 호환 |
| 트랜잭션 (`MULTI`, `EXEC`, `DISCARD`, `WATCH`) | 완전 호환 |
| `WAIT` (레플리카 동기화 확인) | 완전 호환 |
| `RESET` (연결 상태 초기화) | 완전 호환 |
| Redis 모듈 (`MODULE LOAD`) | **Valkey는 모듈 시스템 미지원** |
| `DEBUG` 서브커맨드 (개발·테스트용) | 일부 제거됨 — 운영에는 무관 |
| Hash field expiry (Redis 7.4+) | Valkey 7.x에 없음 |

### Redis 모듈을 쓰고 있다면

RediSearch, RedisJSON, RedisTimeSeries, RedisBloom 같은 Redis 모듈은 Valkey에서 그대로 쓸 수 없다. 모듈에 의존하는 기능이 있다면 전환 전에 대체 방법을 먼저 확보해야 한다.

| Redis 모듈 | 대안 |
|---|---|
| RediSearch (전문 검색) | Elasticsearch, OpenSearch 분리 |
| RedisJSON | 애플리케이션에서 JSON 직렬화 후 String 저장 |
| RedisTimeSeries | Prometheus + VictoriaMetrics |
| RedisBloom | Valkey 8.x에 내장 예정 — 현재는 직접 구현 필요 |
| RedisGraph | Redis 7.x에서 이미 deprecated, Valkey에도 없음 |

## 클라이언트 설정 변경 포인트

Valkey는 RESP2·RESP3를 그대로 지원하기 때문에 클라이언트 연결 코드 자체는 거의 바꿀 게 없다. 바꿔야 하는 것은 **엔드포인트 주소**와 TLS 설정이다. 일부 모니터링 도구가 `CLIENT INFO` 응답의 `library-name`·`library-ver` 필드가 달라진 것을 경고로 올릴 수 있는데, 동작에는 영향이 없다.

### ioredis (Node.js)

ioredis 4.x 이상은 Valkey를 공식 지원한다. 3.x는 동작은 되지만 Valkey 지원을 명시하지 않는다.

```javascript
const Redis = require('ioredis');

const client = new Redis({
  host: process.env.VALKEY_HOST,
  port: 6379,
  password: process.env.VALKEY_PASSWORD,
  tls: process.env.NODE_ENV === 'production' ? {} : undefined,
  enableReadyCheck: true,       // PING 응답 확인 후 ready 전환
  maxRetriesPerRequest: 3,
  retryStrategy: (times) => Math.min(times * 50, 2000),
});

// Cluster 모드
const cluster = new Redis.Cluster(
  [{ host: process.env.VALKEY_HOST, port: 6379 }],
  {
    redisOptions: {
      password: process.env.VALKEY_PASSWORD,
      tls: {},
    },
    scaleReads: 'slave',
  }
);
```

`ioredis-mock`을 테스트에 쓰고 있다면 Valkey 전환 후에도 그대로 동작한다. RESP2 기반이라 프로토콜 차이가 없다.

### Lettuce (Java)

Lettuce 6.x 이상이면 별도 변경 없이 동작한다. `RedisURI`의 호스트만 교체하면 된다.

```java
import io.lettuce.core.RedisClient;
import io.lettuce.core.RedisURI;
import io.lettuce.core.SslVerifyMode;

RedisURI uri = RedisURI.builder()
    .withHost(System.getenv("VALKEY_HOST"))
    .withPort(6379)
    .withPassword(System.getenv("VALKEY_PASSWORD").toCharArray())
    .withSsl(true)
    .withVerifyPeer(SslVerifyMode.FULL)
    .build();

RedisClient client = RedisClient.create(uri);
```

Spring Boot에서는 `application.properties`의 호스트·비밀번호만 바꾸면 `LettuceConnectionFactory`가 Valkey를 Redis와 동일하게 처리한다.

```properties
spring.data.redis.host=${VALKEY_HOST}
spring.data.redis.port=6379
spring.data.redis.password=${VALKEY_PASSWORD}
spring.data.redis.ssl.enabled=true
```

`spring.data.redis.client-name`을 설정했다면 Valkey에서 `CLIENT SETNAME`이 동작하는지 배포 전에 확인한다. 명령어 자체는 동작하지만 일부 APM 도구가 `CLIENT INFO` 응답 파싱을 Redis 기준으로 하드코딩해 두는 경우가 있다.

### jedis (Java)

jedis 5.x 이상이면 Valkey와 동작한다. 4.x 이하는 Valkey 지원을 명시하지 않는다.

```java
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

JedisPoolConfig poolConfig = new JedisPoolConfig();
poolConfig.setMaxTotal(50);
poolConfig.setMaxIdle(20);
poolConfig.setMinIdle(5);
poolConfig.setTestOnBorrow(true);

JedisPool pool = new JedisPool(
    poolConfig,
    System.getenv("VALKEY_HOST"),
    6379,
    2000,
    System.getenv("VALKEY_PASSWORD"),
    true    // SSL
);

try (Jedis jedis = pool.getResource()) {
    jedis.set("key", "value");
}
```

Spring Boot + jedis(`spring.data.redis.client-type=jedis`) 조합이라면 host·password 교체로 충분하다.

## 무중단 마이그레이션 절차

단순히 인스턴스를 교체하면 그 순간부터 Cache Miss가 발생한다. 데이터 규모가 크거나 캐시 워밍 비용이 높은 서비스라면 아래 순서로 진행한다.

### 1단계: Valkey를 Redis 레플리카로 연결

Valkey 7.x는 `REPLICAOF` 명령어를 지원한다. Redis 7.2 → Valkey 7.x 레플리케이션은 프로토콜이 같아 동작한다.

```bash
# Valkey 인스턴스에서 실행
valkey-cli REPLICAOF <redis-master-host> 6379
```

레플리케이션 완료 여부는 `INFO replication`으로 확인한다.

```bash
valkey-cli INFO replication | grep -E "master_link_status|master_sync_in_progress"
# 기대 결과:
# master_link_status:up
# master_sync_in_progress:0
```

### 2단계: Shadow 쓰기

레플리케이션만으로 전환하면 Valkey가 레플리카 상태인 동안 Redis 장애 시 서비스가 멈춘다. 애플리케이션에서 두 곳에 동시에 쓰는 구조가 더 안전하다.

```java
@Service
public class ShadowCacheService {

    private final RedisTemplate<String, Object> redisTemplate;
    private final RedisTemplate<String, Object> valkeyTemplate;

    public void set(String key, Object value, Duration ttl) {
        redisTemplate.opsForValue().set(key, value, ttl);
        try {
            valkeyTemplate.opsForValue().set(key, value, ttl);
        } catch (Exception e) {
            // Valkey 쓰기 실패는 경고만 — Redis가 primary다
            log.warn("Valkey shadow write failed: key={}", key, e);
        }
    }

    public Object get(String key) {
        return redisTemplate.opsForValue().get(key);
    }
}
```

Shadow 쓰기 기간 동안 Valkey 오류율을 모니터링한다. 5분 내 오류율이 0.1% 이하로 안정되면 다음 단계로 넘어간다.

### 3단계: 읽기를 Valkey로 점진적 전환

설정값으로 Valkey 읽기 비율을 조절하고 캐시 히트율·레이턴시를 Redis와 비교한다.

```java
@Service
public class ShadowCacheService {

    @Value("${cache.valkey.read-percentage:0}")
    private int valkeyReadPercentage;

    public Object get(String key) {
        if (ThreadLocalRandom.current().nextInt(100) < valkeyReadPercentage) {
            Object value = valkeyTemplate.opsForValue().get(key);
            if (value != null) return value;
            // Valkey miss → Redis fallback
        }
        return redisTemplate.opsForValue().get(key);
    }
}
```

비율을 0 → 10 → 30 → 70 → 100 순서로 올린다. 각 단계에서 5분 이상 지표를 관찰한다.

### 4단계: Redis 제거

Valkey 읽기 비율이 100%로 안정되면 Redis 쓰기를 제거하고 Redis 커넥션 설정을 삭제한다.

### 롤백 기준

다음 중 하나라도 발생하면 즉시 Redis로 되돌아간다.

- 캐시 히트율이 전환 전 대비 5% 이상 하락하고 5분간 회복되지 않는다
- 캐시 작업 P99 레이턴시가 2배 이상 증가한다
- Valkey 인스턴스 오류율이 0.5%를 초과한다

롤백은 `cache.valkey.read-percentage`를 0으로 내리는 것으로 충분하다. Shadow 쓰기를 유지했기 때문에 Redis 데이터는 최신 상태다.

## AWS ElastiCache for Valkey

AWS는 2024년 11월 ElastiCache for Valkey를 GA로 발표했다. ElastiCache Redis에서 Valkey로 전환할 때 확인해야 할 사항들이 있다.

### in-place 업그레이드는 없다

ElastiCache Redis 7.x에서 Valkey로의 엔진 변경은 스냅샷 → 새 클러스터 복원 방식이다. 엔진을 Redis에서 Valkey로 직접 변경하는 방법은 없다.

```bash
# 기존 ElastiCache Redis 스냅샷 생성
aws elasticache create-snapshot \
  --replication-group-id my-redis-cluster \
  --snapshot-name migration-snapshot-$(date +%Y%m%d)

# 스냅샷을 Valkey 클러스터로 복원
aws elasticache create-replication-group \
  --replication-group-id my-valkey-cluster \
  --engine valkey \
  --engine-version 7.2 \
  --snapshot-name migration-snapshot-20241101 \
  --cache-node-type cache.r7g.large \
  --replication-group-description "Valkey migration"
```

스냅샷 복원 중에 기존 Redis 클러스터는 계속 서비스한다. 복원이 끝나면 위 Shadow 모드 절차를 적용하거나 애플리케이션 엔드포인트를 한 번에 교체한다.

### 파라미터 그룹이 다르다

ElastiCache Redis 파라미터 그룹(`default.redis7`)은 Valkey 클러스터에서 사용할 수 없다. Valkey 전용 파라미터 그룹이 필요하다.

```bash
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name my-valkey-params \
  --cache-parameter-group-family valkey7 \
  --description "Valkey 7.x parameter group"
```

기존 Redis 파라미터 값을 먼저 확인하고 동일하게 설정한다.

```bash
# Redis 기존 사용자 설정 파라미터 조회
aws elasticache describe-cache-parameters \
  --cache-parameter-group-name default.redis7 \
  --source user

# Valkey 파라미터 그룹에 적용
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-valkey-params \
  --parameter-name-values \
    ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
    ParameterName=activerehashing,ParameterValue=yes \
    ParameterName=lazyfree-lazy-eviction,ParameterValue=yes
```

`maxmemory-policy`, `hz`, `lazyfree-lazy-eviction` 같은 주요 파라미터는 Valkey에서도 이름이 동일하다. 전환 전에 `describe-engine-default-parameters --cache-parameter-group-family valkey7`로 지원 목록을 대조한다. Redis 전용 파라미터가 Valkey 그룹에 없어 설정 누락이 발생하는 경우가 있다.

Evictions이 전환 후 급증하면 `maxmemory-policy`가 파라미터 그룹에 제대로 들어가지 않아 기본값 `noeviction`이 적용된 것일 가능성이 높다. 이 상태에서는 메모리가 가득 차면 쓰기 오류가 발생한다.

### TLS 강제

ElastiCache for Valkey는 In-transit TLS를 기본으로 강제한다. 기존 Redis 클러스터가 TLS 없이 운영 중이었다면 클라이언트에 TLS 설정을 추가해야 한다.

```javascript
// ioredis + ElastiCache Valkey
const client = new Redis({
  host: process.env.VALKEY_ENDPOINT,
  port: 6379,
  tls: {
    // ElastiCache 인증서는 AWS 루트 CA를 따른다.
    // Node.js 18+ 기본 CA에 포함돼 있어 별도 인증서 파일 불필요
  },
  password: process.env.VALKEY_AUTH_TOKEN,
});
```

IAM 인증은 ElastiCache for Valkey 7.x부터 지원한다.

### 비용과 Reserved Instance 주의

ElastiCache for Valkey는 ElastiCache Redis 대비 20% 낮은 가격을 AWS가 공식 발표했다. 인스턴스 타입 표기도 `cache.valkey.*`로 분리됐다.

기존 Redis Reserved Instance는 Valkey 클러스터에 적용되지 않는다. Redis RI로 운영 중이라면 RI 만료 시점에 맞춰 전환 일정을 잡는 게 낫다. 만료 전에 강행하면 RI 요금을 내면서 Valkey On-Demand 요금도 추가로 내게 된다.

### 전환 후 CloudWatch 지표

지표 이름은 Redis와 동일하다. 네임스페이스도 `AWS/ElastiCache`로 그대로다.

```bash
# 캐시 히트율 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CacheHitRate \
  --dimensions Name=ReplicationGroupId,Value=my-valkey-cluster \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average

# Evictions 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name Evictions \
  --dimensions Name=ReplicationGroupId,Value=my-valkey-cluster \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```
