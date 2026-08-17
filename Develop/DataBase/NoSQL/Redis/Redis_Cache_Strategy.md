---
title: Redis 캐시 설계 실무
tags: [redis, cache, os, monitoring]
updated: 2026-08-17
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

```typescript
// TTL 지터 적용
function ttlWithJitter(baseSeconds: number, jitterRatio: number): number {
    const jitterRange = Math.floor(baseSeconds * jitterRatio);
    const jitter = Math.floor(Math.random() * (jitterRange * 2 + 1)) - jitterRange;
    return baseSeconds + jitter;
}

// 사용 예: 기본 TTL 10분(600초), +-20% 지터 → 480초~720초 사이에서 랜덤
const ttl = ttlWithJitter(600, 0.2);
await redis.set(key, value, 'EX', ttl);
```

### 1.3 조건부 TTL

데이터 상태에 따라 TTL을 다르게 설정하는 패턴이다.

```typescript
// 빈 결과 캐싱: DB에 데이터가 없는 경우 짧은 TTL로 캐시
// → Cache Penetration 방어
async getProduct(productId: number): Promise<ProductDto | null> {
    const key = `product:${productId}`;
    const cached = await this.redis.get(key);

    if (cached !== null) {
        if (cached === 'EMPTY') return null;
        return JSON.parse(cached) as ProductDto;
    }

    const product = await this.productRepository.findById(productId);

    if (product === null) {
        // 존재하지 않는 상품 → 30초만 캐시
        await this.redis.set(key, 'EMPTY', 'EX', 30);
        return null;
    }

    // 정상 데이터 → 1시간 캐시
    await this.redis.set(key, JSON.stringify(product), 'EX', 3600);
    return product;
}
```

```typescript
// 완료된 주문은 변경되지 않으므로 TTL을 길게
function orderTtl(order: Order): number {
    if (order.status === 'COMPLETED' || order.status === 'CANCELLED') {
        return 86400;  // 24시간 — 완료/취소된 주문은 바뀔 일이 없다
    }
    return 300;  // 5분 — 진행 중 주문은 자주 바뀐다
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

```typescript
// 버전 접두사를 코드에서 관리하는 예
const CACHE_VERSION = 'v3';

export const CacheKey = {
    product: (productId: number) => `${CACHE_VERSION}:product:${productId}`,
    userProfile: (userId: number) => `${CACHE_VERSION}:user:profile:${userId}`,
};
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

```typescript
// JSON.parse는 기본적으로 모르는 필드를 무시한다
// TypeScript 타입 캐스팅 시 추가 필드는 자동으로 무시됨
const product = JSON.parse(cached) as ProductDto;
// ProductDto에 없는 필드가 JSON에 있어도 오류 없이 파싱됨
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

```typescript
// 역직렬화 실패 시 캐시 삭제 후 DB 조회하는 패턴
async getProduct(id: number): Promise<ProductDto> {
    const key = `product:${id}`;
    const cached = await this.redis.get(key);

    if (cached !== null) {
        try {
            return JSON.parse(cached) as ProductDto;
        } catch (e) {
            // 역직렬화 실패 → 캐시 삭제
            logger.warn(`캐시 역직렬화 실패, 삭제: key=${key}`, e);
            await this.redis.del(key);
        }
    }

    const product = await this.productRepository.findById(id);
    await this.redis.set(key, JSON.stringify(product), 'EX', 3600);
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

```typescript
// Prometheus 클라이언트 라이브러리(prom-client)로 hit/miss를 카운터로 기록한다
import { Counter } from 'prom-client';

export class MonitoredCacheService {
    private readonly hitCounter: Counter;
    private readonly missCounter: Counter;

    constructor(private readonly redis: Redis) {
        this.hitCounter = new Counter({ name: 'cache_hit_total', help: 'Cache hits' });
        this.missCounter = new Counter({ name: 'cache_miss_total', help: 'Cache misses' });
    }

    async get(key: string): Promise<string | null> {
        const value = await this.redis.get(key);
        if (value !== null) {
            this.hitCounter.inc();
        } else {
            this.missCounter.inc();
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

---

## 7. Eviction Policy

Redis는 `maxmemory`에 도달하면 `maxmemory-policy` 설정에 따라 키를 삭제하거나 쓰기를 거부한다. 이 설정을 잘못 고르면 무음 장애가 난다.

### 7.1 정책 목록과 실제 동작

| 정책 | 삭제 대상 | 알고리즘 |
|---|---|---|
| `noeviction` | 없음 — 쓰기 거부 | — |
| `allkeys-lru` | 전체 키 | 최근 접근 시간 기준 |
| `volatile-lru` | TTL 있는 키 | 최근 접근 시간 기준 |
| `allkeys-lfu` | 전체 키 | 접근 빈도 기준 |
| `volatile-lfu` | TTL 있는 키 | 접근 빈도 기준 |
| `allkeys-random` | 전체 키 | 랜덤 |
| `volatile-random` | TTL 있는 키 | 랜덤 |
| `volatile-ttl` | TTL 있는 키 | TTL이 짧은 키 우선 |

LRU는 "최근에 접근한 키를 남긴다"는 논리다. LFU는 "자주 접근한 키를 남긴다"는 논리다. 이 둘의 차이가 실무에서 드러나는 건 이벤트·프로모션 기간이다. 특정 상품 페이지에 트래픽이 몰렸다가 빠지면, LRU 기준으로는 그 키가 오랫동안 살아남는다. LFU는 이벤트 이후 접근이 줄면 자연스럽게 밀려난다.

Redis의 LRU/LFU는 근사 알고리즘이다. `maxmemory-samples` 설정(기본 5)만큼 키를 샘플링해서 그 중 교체 대상을 고른다. 값을 높이면 정밀도가 오르지만 CPU 부하도 올라간다.

### 7.2 캐시 전용이면 allkeys-lru나 allkeys-lfu

캐시 목적이라면 `allkeys-lru`가 안전하다. `volatile-lru`를 쓰다가 실수로 TTL 없는 키가 들어가면 그 키는 메모리가 꽉 차도 절대 삭제되지 않는다.

```bash
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET maxmemory 8gb

# 현재 설정 확인
redis-cli CONFIG GET maxmemory-policy
redis-cli CONFIG GET maxmemory
```

`volatile-lru`가 적합한 경우는 Redis 하나에 영속 데이터(TTL 없는 키)와 캐시(TTL 있는 키)를 같이 쓸 때다. 영속 키는 지우면 안 되니까 volatile 계열을 써야 한다. 다만 이 구조 자체가 문제가 생기기 쉬워서, 가능하면 Redis 인스턴스를 분리하는 쪽이 낫다.

### 7.3 noeviction의 함정

`noeviction`은 기본값이다. `maxmemory`를 설정하지 않으면 메모리 제한이 없어서 noeviction 정책이 의미가 없다. 문제는 `maxmemory`를 설정하고 policy를 바꾸지 않은 경우다.

메모리가 꽉 차면 SET, LPUSH 같은 쓰기 명령이 에러를 반환한다.

```
OOM command not allowed when used memory > 'maxmemory'
```

애플리케이션에서 이 에러를 처리하지 않으면 캐시 쓰기 실패가 조용히 발생한다. Cache-Aside 패턴이면 DB 부하가 올라가면서 알게 되지만, 캐시 갱신 실패로 오래된 데이터를 서빙하는 경우는 눈치채기 어렵다.

의도적으로 noeviction을 쓰는 경우도 있다. 세션 저장소처럼 삭제되면 안 되는 데이터를 Redis에 넣을 때다. 이때는 메모리 모니터링이 필수다.

### 7.4 evicted_keys 추세로 OOM 예측

```bash
redis-cli INFO stats | grep evicted_keys
# evicted_keys:0
```

이 값이 올라가기 시작하면 Redis가 메모리 압박을 받고 있다는 신호다. eviction이 발생한다는 건 캐시 히트율이 저하될 수 있다는 뜻이기도 하다 — 아직 접근 중인 키가 삭제될 수 있다.

```bash
# 1분 간격으로 evicted_keys 추이를 확인하는 방법
while true; do
    ts=$(date '+%H:%M:%S')
    ev=$(redis-cli INFO stats | grep evicted_keys | cut -d: -f2 | tr -d '\r')
    mem=$(redis-cli INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r ')
    echo "${ts} evicted=${ev} mem=${mem}"
    sleep 60
done
```

분당 evicted_keys 증가분이 1,000을 넘어가면 maxmemory를 늘리거나, 캐시 대상 데이터를 줄이거나, TTL을 조정해야 한다. 증가분이 0이어도 used_memory가 maxmemory의 80%를 넘으면 미리 대응한다.

Prometheus + Grafana로 수집한다면 `redis_evicted_keys_total`을 rate로 보는 것이 추세 파악에 낫다. 절대값보다 증가율이 중요하다.

---

## 8. Hot Key 문제

Hot Key는 특정 키에 요청이 집중되는 현상이다. Redis는 싱글 스레드로 명령을 처리하기 때문에 한 키에 초당 수만 건이 들어오면 그 처리가 다른 명령을 지연시킨다. 클러스터를 써도 해당 슬롯을 담당하는 노드에만 부하가 몰린다.

### 8.1 감지

LFU 정책을 쓰면 `--hotkeys` 옵션으로 직접 확인할 수 있다.

```bash
redis-cli --hotkeys
# Sampled 1000000 commands in 10.00 seconds
# hot key found with counter: 950000  keyname: product:featured:top10
# hot key found with counter: 32000   keyname: config:site-settings
```

`allkeys-lru`나 `volatile-lru`를 쓰고 있으면 `--hotkeys`가 동작하지 않는다. 이 경우엔 `MONITOR`로 실시간 명령을 잠깐 캡처하거나, 애플리케이션 APM에서 Redis 호출 패턴을 확인하는 수밖에 없다.

```bash
# MONITOR는 모든 명령을 출력하므로 운영 환경에서는 5초 이하로만 쓴다
# 트래픽이 많으면 Redis 성능에 영향을 준다
timeout 5 redis-cli MONITOR | grep "GET\|HGET" | awk '{print $NF}' | sort | uniq -c | sort -rn | head -20
```

`INFO stats`의 `keyspace_hits`와 `keyspace_misses`는 전체 통계라 특정 키를 찾는 데는 쓸 수 없다. 히트율이 99%여도 그 대부분이 한 키에서 온 것일 수 있다.

### 8.2 키 샤딩

핫키의 값을 N개 복사본으로 분산한다. 읽을 때 랜덤하게 고르면 요청이 N개 키에 분산된다.

```typescript
const SHARD_COUNT = 8;

function hotKeyShardKey(base: string): string {
    const shard = Math.floor(Math.random() * SHARD_COUNT);
    return `${base}:shard:${shard}`;
}

// 쓸 때: 모든 샤드 갱신
async function setFeaturedProducts(data: ProductList): Promise<void> {
    const serialized = JSON.stringify(data);
    const pipeline = redis.pipeline();
    for (let i = 0; i < SHARD_COUNT; i++) {
        pipeline.set(`product:featured:top10:shard:${i}`, serialized, 'EX', 300);
    }
    await pipeline.exec();
}

// 읽을 때: 랜덤 샤드
async function getFeaturedProducts(): Promise<ProductList | null> {
    const key = hotKeyShardKey('product:featured:top10');
    const cached = await redis.get(key);
    return cached ? JSON.parse(cached) : null;
}
```

샤드 수를 높이면 분산 효과가 크지만, 갱신 시 모든 샤드를 업데이트해야 한다. 샤드 갱신 중에 일부 샤드는 새 데이터, 일부는 구 데이터를 서빙하는 짧은 구간이 생긴다. 캐시 특성상 이 정도 불일치는 보통 허용된다.

### 8.3 로컬 캐시 앞단 배치

애플리케이션 프로세스 메모리 내에 인메모리 캐시를 두고, Redis는 L2로 쓰는 패턴이다. 로컬 캐시 히트 시 Redis 요청이 발생하지 않아 핫키 압력이 완전히 사라진다.

```java
// Java + Caffeine 예시
Cache<String, String> localCache = Caffeine.newBuilder()
    .expireAfterWrite(30, TimeUnit.SECONDS)
    .maximumSize(200)
    .build();

public ProductList getFeaturedProducts() {
    String cached = localCache.getIfPresent("product:featured:top10");
    if (cached != null) {
        return deserialize(cached);
    }

    String fromRedis = redis.get("product:featured:top10");
    if (fromRedis != null) {
        localCache.put("product:featured:top10", fromRedis);
        return deserialize(fromRedis);
    }

    return null;
}
```

```typescript
// Node.js + node-cache 예시
import NodeCache from 'node-cache';

const localCache = new NodeCache({ stdTTL: 30, checkperiod: 60 });

async function getFeaturedProducts(): Promise<ProductList | null> {
    const LOCAL_KEY = 'product:featured:top10';
    const local = localCache.get<string>(LOCAL_KEY);
    if (local !== undefined) {
        return JSON.parse(local);
    }

    const fromRedis = await redis.get(LOCAL_KEY);
    if (fromRedis) {
        localCache.set(LOCAL_KEY, fromRedis);
        return JSON.parse(fromRedis);
    }

    return null;
}
```

주의할 점은 인스턴스마다 로컬 캐시가 따로 존재한다는 것이다. 배포 중에 일부 인스턴스는 새 로컬 캐시, 일부는 구 로컬 캐시를 갖게 된다. TTL을 30초~1분으로 짧게 두는 이유가 이 때문이다. 무효화 이벤트(Redis Pub/Sub, 카프카)로 로컬 캐시를 강제 만료시키면 정합성을 더 잘 맞출 수 있다.

---

## 9. Valkey 마이그레이션

Redis 7.4부터 SSPL 라이선스로 전환됐다. 상업 서비스에서 쓰려면 라이선스를 검토해야 하는데, 그 대안으로 Valkey가 부상했다. Valkey는 Redis 7.2 코드베이스에서 포크한 LF(Linux Foundation) 프로젝트다.

### 9.1 호환성

클라이언트 라이브러리는 그대로 쓸 수 있다. Jedis, Lettuce, ioredis, go-redis 모두 TCP 프로토콜 수준에서 호환된다. 연결 URL이나 host 설정만 Valkey 인스턴스를 가리키도록 바꾸면 된다.

`redis-cli`도 Valkey에 그대로 접속 가능하다. `valkey-cli`가 별도로 있지만 기능은 동일하다.

명령어 호환성은 7.2 기준이므로, Redis 7.2 이전에 추가된 명령은 대부분 동작한다. Redis 7.4 이후 추가된 기능은 Valkey에 없다.

### 9.2 설정 파일

`redis.conf`를 그대로 사용할 수 있다. Valkey는 설정 형식과 키 이름을 Redis와 동일하게 유지한다. `maxmemory`, `maxmemory-policy`, `appendonly`, `save`, `requirepass` 등 모두 동일하다.

### 9.3 Valkey 8.x에서 달라지는 설정 포인트

**멀티스레드 I/O**

Redis 6.0에서도 `io-threads` 설정이 있었지만 실제 성능 향상이 미미했다. Valkey 8.x는 I/O 스레딩을 개선해서 `io-threads`를 CPU 코어 수의 절반 정도로 설정하면 처리량이 유의미하게 올라간다.

```
# redis.conf (Valkey에서 그대로 사용)
io-threads 4
io-threads-do-reads yes
```

**latency-tracking 기본값 변경**

Redis에서는 `latency-tracking`이 `no`가 기본이었다. Valkey에서는 `yes`가 기본이다. `LATENCY HISTORY`, `LATENCY LATEST` 명령으로 지연 이력을 바로 확인할 수 있다.

```bash
valkey-cli LATENCY LATEST
# command       event_time      latency(ms) max_latency(ms)
# command       1720000000      1           15
```

**active-expire-effort**

만료 키를 적극적으로 정리하는 설정이다. Redis 기본값은 1(소극적)인데, Valkey에서도 1이 기본이다. 메모리 회수가 느리다고 느껴지면 5 정도로 올려본다. CPU 사용률이 올라가므로 피크 타임에 바꾸면 안 된다.

```bash
valkey-cli CONFIG SET active-expire-effort 5
```

### 9.4 Redis 모듈이 있으면 사전 확인 필수

RedisJSON, RediSearch, RedisTimeSeries 같은 Redis 공식 모듈은 Valkey에서 동작하지 않는다. 이 모듈들은 Redis-specific API를 쓰기 때문에 별도 포팅이 필요하다.

대안:
- RedisJSON → ValkeyJSON (FalkorDB 제공, Apache 2.0)
- RediSearch → 현재 Valkey용 공식 대안 없음. PostgreSQL의 full-text search나 Elasticsearch를 고려해야 한다.

`MODULE LIST` 명령으로 현재 Redis에 로드된 모듈을 확인한다.

```bash
redis-cli MODULE LIST
# 1) 1) "name"
#    2) "ReJSON"
#    3) "ver"
#    4) (integer) 20009
```

모듈이 있으면 마이그레이션 전에 대체 방안을 먼저 확정해야 한다.

### 9.5 Sentinel과 Cluster 전환

Valkey Sentinel은 Redis Sentinel 프로토콜을 그대로 유지한다. Redis Sentinel을 쓰던 클라이언트는 Sentinel 주소만 Valkey Sentinel로 바꾸면 동작한다.

Cluster도 마찬가지다. 클러스터 재구성 없이 노드를 교체하는 방식으로 마이그레이션하거나, 새 Valkey 클러스터로 데이터를 마이그레이션하면 된다.

데이터 마이그레이션은 `redis-cli --cluster import` 또는 `DUMP`/`RESTORE` 명령으로 할 수 있다. AOF 파일을 Valkey로 재생하는 것도 가능하다.

---
이 문서는 [캐싱 허브](../../../_hub/캐싱.md)의 일부입니다.
