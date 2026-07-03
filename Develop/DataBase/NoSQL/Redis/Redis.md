---
title: Redis — 내부 동작 원리와 아키텍처
tags: [database, nosql, redis, architecture, internals]
updated: 2026-03-27
---

# Redis (Remote Dictionary Server)

## Redis가 뭔가

Redis는 인메모리 데이터 구조 저장소다. 2009년 Salvatore Sanfilippo가 LiveJournal의 실시간 통계 처리를 위해 만들었다. MySQL로는 실시간 집계가 불가능했고, 메모리에 데이터를 올려서 처리하는 방식으로 문제를 풀었다.

키-값 저장소라고 단순하게 보기 쉬운데, 정확히는 "데이터 구조 서버"다. String, Hash, List, Set, Sorted Set 같은 자료구조를 서버 측에서 직접 제공하고, 각 자료구조에 대한 원자적 연산을 지원한다. 클라이언트가 복잡한 로직을 짤 필요 없이 Redis 명령 하나로 처리할 수 있다는 점이 핵심이다.

> 데이터 타입별 사용법과 실제 적용 패턴은 [Redis 다루기](Redis%20다루기.md), 클러스터/센티널/분산락 등 심화 내용은 [Redis 심화](Redis_Advanced.md) 참고.

![Redis.png](..%2F..%2F..%2F..%2Fetc%2Fimage%2FDataBase%2FNoSQL%2FRedis%2FRedis.png)

---

## 싱글 스레드 이벤트 루프

Redis가 빠른 이유를 "인메모리라서"로만 설명하면 절반만 맞다. 핵심은 싱글 스레드 이벤트 루프 구조다.

### 왜 싱글 스레드인가

멀티스레드 서버는 락, 컨텍스트 스위칭, 캐시 라인 경합 같은 오버헤드가 생긴다. Redis는 이걸 아예 피했다. 스레드 하나가 모든 명령을 순차 처리하기 때문에:

- 락이 필요 없다. 모든 명령이 원자적으로 실행된다.
- 컨텍스트 스위칭이 없다. CPU 사이클을 순수하게 명령 처리에 쓴다.
- 코드가 단순하다. 동시성 버그가 구조적으로 발생하지 않는다.

### I/O 멀티플렉싱: epoll과 kqueue

싱글 스레드인데 어떻게 수만 개 커넥션을 처리하는가? 답은 I/O 멀티플렉싱이다.

```
클라이언트 연결 흐름:

  Client A ──┐
  Client B ──┼── epoll/kqueue ── 이벤트 루프 ── 명령 처리
  Client C ──┘     (I/O 멀티플렉서)     (싱글 스레드)

  1. 소켓에서 읽을 데이터가 있는지 OS 커널에 물어본다
  2. 준비된 소켓만 골라서 순차적으로 처리한다
  3. 다 처리하면 다시 1로 돌아간다
```

Redis는 OS에 따라 다른 멀티플렉서를 쓴다:

- **Linux**: `epoll` — O(1) 이벤트 감지. fd 수와 무관하게 일정한 성능.
- **macOS/BSD**: `kqueue` — epoll과 비슷한 성능. 파일 시스템 이벤트도 감지 가능.
- **fallback**: `select` — fd 1024개 제한. 실서비스에서는 안 쓴다.

Redis 소스코드의 `ae.c`(Abstract Event library)가 이걸 추상화한다. 컴파일 시점에 OS에 맞는 구현체가 선택된다.

### 이벤트 루프의 실제 동작

```
aeMain() 루프 한 사이클:

  ┌─────────────────────────────────┐
  │ 1. beforesleep()                │ ← AOF flush, 만료 키 삭제 등
  ├─────────────────────────────────┤
  │ 2. aeApiPoll()                  │ ← epoll_wait/kevent 호출, 블로킹 대기
  ├─────────────────────────────────┤
  │ 3. 파일 이벤트 처리              │ ← 클라이언트 읽기/쓰기
  ├─────────────────────────────────┤
  │ 4. 타임 이벤트 처리              │ ← serverCron (100ms 주기)
  └─────────────────────────────────┘
```

`beforesleep()`에서 하는 일이 중요하다:

- 만료된 키를 lazy하게 삭제한다
- AOF 버퍼를 디스크에 플러시한다
- 클러스터 모드면 슬롯 마이그레이션 처리를 한다

`serverCron()`은 100ms마다 실행되는 타이머 콜백이다:

- 메모리 사용량 확인 및 eviction 처리
- 클라이언트 타임아웃 검사
- RDB/AOF 백그라운드 작업 상태 확인
- 복제(replication) 상태 체크

### Redis 6.0 이후: I/O 스레드

Redis 6.0에서 `io-threads` 설정이 추가됐다. 주의할 점은, **명령 실행은 여전히 싱글 스레드**라는 것이다. I/O 스레드가 하는 일은 소켓에서 데이터를 읽고 쓰는 것뿐이다.

```
io-threads 동작:

  I/O 스레드 1 ── 소켓 읽기 ──┐
  I/O 스레드 2 ── 소켓 읽기 ──┼── 메인 스레드: 명령 파싱 + 실행 ──┐
  I/O 스레드 3 ── 소켓 읽기 ──┘                                   │
                                                                   ▼
  I/O 스레드 1 ── 소켓 쓰기 ──┐
  I/O 스레드 2 ── 소켓 쓰기 ──┤◀── 응답 데이터 ────────────────────┘
  I/O 스레드 3 ── 소켓 쓰기 ──┘
```

```conf
# redis.conf
io-threads 4          # I/O 스레드 수 (CPU 코어 수의 절반 이하 권장)
io-threads-do-reads yes  # 읽기도 I/O 스레드에서 처리
```

네트워크 I/O가 병목인 경우(초당 10만+ 요청, 큰 값 전송)에만 효과가 있다. 대부분의 경우 기본값(1, 비활성)으로 충분하다.

---

## 메모리 아키텍처

### 메모리 할당기: jemalloc

Redis는 기본 메모리 할당기로 `jemalloc`을 쓴다. glibc의 `malloc`은 메모리 단편화가 심해서 장시간 운영하면 실제 데이터보다 훨씬 많은 메모리를 잡아먹는 문제가 있다.

jemalloc이 Redis에 맞는 이유:

- **크기별 분류(size class)**: 할당 요청을 미리 정해진 크기 단위로 올림한다. 8, 16, 32, 48, 64, ... 바이트. 비슷한 크기의 할당이 같은 페이지에 모여서 단편화가 줄어든다.
- **스레드 로컬 캐시**: 싱글 스레드인 Redis에서는 큰 의미가 없지만, 백그라운드 스레드(RDB, AOF rewrite)에서 할당할 때 경합을 피한다.
- **arena 기반 관리**: 메모리 영역을 독립적으로 관리해서 한 영역의 단편화가 다른 영역에 영향을 주지 않는다.

```bash
# 메모리 할당기 정보 확인
redis-cli INFO memory

# used_memory: 실제 데이터 크기
# used_memory_rss: OS가 할당한 물리 메모리
# mem_fragmentation_ratio: rss / used_memory
#   - 1.0~1.5: 정상
#   - 1.5 이상: 단편화 발생. activedefrag 검토
#   - 1.0 미만: 스왑 사용 중. 문제 있음

# jemalloc 상세 통계
redis-cli MEMORY MALLOC-STATS
```

`mem_fragmentation_ratio`가 1.5를 넘기면 `activedefrag`을 켜볼 수 있다:

```conf
activedefrag yes
active-defrag-threshold-lower 10   # 단편화 10% 이상일 때 시작
active-defrag-threshold-upper 100  # 단편화 100% 이상이면 최대 속도로
active-defrag-cycle-min 1          # CPU 사용률 하한 (%)
active-defrag-cycle-max 25         # CPU 사용률 상한 (%)
```

실서비스에서는 `active-defrag-cycle-max`를 25 이상으로 올리지 않는 게 좋다. 이벤트 루프에 끼어들어서 응답 지연이 생긴다.

### 내부 인코딩과 메모리 절약

Redis는 같은 데이터 타입이라도 크기에 따라 내부 인코딩을 바꾼다. 이걸 모르면 메모리 낭비를 잡기 어렵다.

```
데이터 타입별 내부 인코딩 전환:

  Hash:
    필드 수 ≤ 128 AND 값 크기 ≤ 64B → ziplist (연속 메모리 블록)
    그 외                           → hashtable

  List:
    항상 quicklist (ziplist 노드들의 연결 리스트)

  Set:
    원소 수 ≤ 128 AND 모두 정수     → intset
    그 외                           → hashtable

  Sorted Set:
    원소 수 ≤ 128 AND 값 크기 ≤ 64B → ziplist
    그 외                           → skiplist + hashtable

  (임계값은 redis.conf에서 변경 가능)
```

```bash
# 특정 키의 내부 인코딩 확인
redis-cli OBJECT ENCODING mykey

# 키가 차지하는 메모리 확인
redis-cli MEMORY USAGE mykey SAMPLES 0
```

ziplist는 포인터 오버헤드가 없어서 메모리를 많이 아끼지만, 원소가 많아지면 O(n) 탐색이 된다. Redis가 자동으로 전환하기 때문에 직접 관리할 필요는 없지만, 임계값을 너무 높이면 성능이 떨어진다.

---

## Copy-on-Write와 포크 동작

Redis가 RDB 스냅샷을 뜨거나 AOF를 재작성할 때 `fork()`를 호출한다. 이 과정이 운영에서 문제를 일으키는 경우가 잦다.

### fork()가 하는 일

```
fork() 시점:

  부모 프로세스 (Redis)          자식 프로세스
  ┌──────────────────┐          ┌──────────────────┐
  │ 페이지 테이블      │─── 복사 ──→│ 페이지 테이블      │
  │ (가상 → 물리 매핑) │          │ (같은 물리 메모리)  │
  └──────────────────┘          └──────────────────┘
         │                              │
         └──── 같은 물리 메모리 공유 ────────┘

  → 페이지 테이블만 복사. 실제 데이터는 복사하지 않는다.
  → fork() 자체는 빠르다. 메모리 10GB여도 수 ms.
```

### Copy-on-Write가 일으키는 문제

fork() 직후에는 부모와 자식이 같은 물리 메모리를 공유한다. 부모가 데이터를 수정하면 그 페이지만 복사된다(Copy-on-Write). 문제는 **쓰기가 많으면 메모리가 두 배 가까이 필요할 수 있다**는 점이다.

```
쓰기 발생 시:

  부모가 Page 3 수정
    ↓
  OS가 Page 3을 복사해서 새 물리 페이지 할당
    ↓
  부모: 새 Page 3 (수정된 데이터)
  자식: 원본 Page 3 (스냅샷 시점 데이터)

  → 쓰기가 모든 페이지에 발생하면 전체 메모리의 2배 필요
```

실서비스에서 주의할 점:

```bash
# 1. maxmemory를 물리 메모리의 절반 이하로 설정
#    CoW로 인한 메모리 피크를 감당할 여유가 있어야 한다
maxmemory 8gb  # 16GB 서버인 경우

# 2. Transparent Huge Pages(THP) 끄기
#    THP가 켜져 있으면 2MB 페이지 단위로 CoW가 발생한다
#    4KB 페이지보다 512배 많은 메모리가 복사될 수 있다
echo never > /sys/kernel/mm/transparent_hugepage/enabled

# 3. overcommit_memory 설정
#    fork() 시점에 OS가 메모리 할당을 거부하면 RDB 저장이 실패한다
echo 1 > /proc/sys/vm/overcommit_memory
```

`INFO persistence`에서 `rdb_last_cow_size`를 확인하면 마지막 RDB 저장 시 CoW로 실제로 복사된 메모리 양을 볼 수 있다. 이 값이 크면 RDB 저장 중 쓰기 부하가 높다는 뜻이다.

### fork() 지연 문제

fork()는 페이지 테이블을 복사해야 해서, 메모리가 클수록 시간이 걸린다. 25GB 인스턴스 기준으로 fork()에 수십 ms가 소요되는 경우가 있다. 이 시간 동안 Redis는 모든 요청을 처리하지 못한다.

```bash
# fork 지연시간 확인
redis-cli INFO persistence | grep rdb_last_fork_usec

# 이 값이 수백 ms를 넘기면:
# - 인스턴스 크기를 줄이거나
# - RDB 저장 주기를 늘리거나
# - AOF만 사용하는 걸 검토한다
```

---

## 데이터 지속성: RDB vs AOF

### RDB 동작 방식

```
BGSAVE 실행 흐름:

  1. fork() 호출 → 자식 프로세스 생성
  2. 자식: 메모리 전체를 순회하며 temp-<pid>.rdb 파일에 직렬화
  3. 자식: 작업 완료 후 rename으로 dump.rdb 교체
  4. 부모: 자식 종료 감지, 완료 상태 업데이트

  → 자식이 쓰는 동안 부모는 정상적으로 요청 처리
  → CoW 덕분에 자식은 fork 시점의 일관된 스냅샷을 가진다
```

```conf
# RDB 트리거 조건 (여러 개 설정 가능)
save 3600 1       # 3600초 동안 1개 이상 변경
save 300 100      # 300초 동안 100개 이상 변경
save 60 10000     # 60초 동안 10000개 이상 변경

# RDB 파일 압축
rdbcompression yes    # LZF 압축. CPU를 약간 쓰지만 파일 크기가 줄어든다
rdbchecksum yes       # CRC64 체크섬. 파일 무결성 검증
```

### AOF 동작 방식

AOF는 쓰기 명령을 텍스트로 기록한다. RESP 프로토콜 형식 그대로 저장하기 때문에 사람이 읽을 수 있다.

```
AOF 쓰기 흐름:

  명령 실행 → aof_buf에 추가 → fsync 정책에 따라 디스크 쓰기

  fsync 정책:
  - always:   매 명령마다 fsync. 데이터 손실 없음. 느림.
  - everysec: 1초마다 fsync. 최대 1초 데이터 손실. 권장값.
  - no:       OS에 맡김. 빠르지만 데이터 손실 범위가 큼.
```

AOF 파일은 계속 커지기 때문에 주기적으로 재작성(rewrite)한다:

```
AOF Rewrite 흐름:

  1. fork() 호출
  2. 자식: 현재 메모리 상태를 최소 명령 세트로 변환, 새 AOF 파일 생성
  3. 부모: rewrite 중 들어온 명령을 aof_rewrite_buf에 추가 저장
  4. 자식: 완료 후 부모에 시그널
  5. 부모: aof_rewrite_buf를 새 AOF 파일에 추가, rename으로 교체

  → 이 과정에서도 fork()와 CoW가 관여한다
```

### Redis 7.0: Multi-part AOF

Redis 7.0부터 AOF가 여러 파일로 분리됐다:

```
appendonlydir/
├── appendonly.aof.1.base.rdb      ← rewrite 시점의 RDB 스냅샷
├── appendonly.aof.1.incr.aof      ← rewrite 이후의 증분 명령
├── appendonly.aof.2.incr.aof      ← 추가 증분
└── appendonly.aof.manifest        ← 파일 목록과 순서 관리
```

이전 방식(단일 파일)보다 rewrite 중 디스크 사용량이 줄고, 파일 교체가 안전해졌다.

---

## Eviction 정책과 키 만료

### 키 만료 처리 방식

Redis의 키 만료는 두 가지 방식으로 동작한다:

- **Lazy 삭제**: 클라이언트가 키에 접근할 때 만료 여부를 확인하고 삭제한다. 접근하지 않는 키는 메모리에 남아있다.
- **Active 삭제**: `serverCron()`에서 100ms마다 만료된 키를 샘플링해서 삭제한다. 매번 만료된 키 중 일부만 처리하기 때문에 이벤트 루프를 오래 점유하지 않는다.

```
Active 만료 알고리즘 (hz 10 기준, 100ms마다 실행):

  1. 만료 시간이 설정된 키 중 20개를 랜덤 샘플링
  2. 만료된 키 삭제
  3. 삭제 비율이 25% 이상이면 → 1로 돌아감 (최대 25ms)
  4. 25% 미만이면 → 이번 사이클 종료

  → 만료된 키가 많으면 공격적으로 삭제하고,
    적으면 빠르게 넘어간다.
```

### Eviction 정책

`maxmemory`에 도달하면 eviction 정책에 따라 키를 삭제한다:

| 정책 | 대상 | 알고리즘 | 사용 시점 |
|------|------|---------|----------|
| `noeviction` | 없음 | 쓰기 거부 | 캐시가 아닌 저장소로 쓸 때 |
| `allkeys-lru` | 전체 키 | 근사 LRU | 범용 캐시 (가장 많이 씀) |
| `volatile-lru` | TTL 있는 키 | 근사 LRU | 캐시+영구 데이터 혼용 |
| `allkeys-lfu` | 전체 키 | 근사 LFU | 접근 빈도 편차가 큰 경우 |
| `volatile-lfu` | TTL 있는 키 | 근사 LFU | 위와 동일, TTL 키만 대상 |
| `allkeys-random` | 전체 키 | 랜덤 | 접근 패턴이 균일할 때 |
| `volatile-random` | TTL 있는 키 | 랜덤 | 위와 동일, TTL 키만 대상 |
| `volatile-ttl` | TTL 있는 키 | TTL 짧은 순 | TTL을 우선순위로 쓰는 경우 |

Redis의 LRU는 정확한 LRU가 아니다. 샘플링 기반 근사 LRU를 쓴다:

```conf
# 샘플 수 (기본 5). 높일수록 정확하지만 CPU를 더 쓴다
maxmemory-samples 5

# 10으로 올리면 거의 정확한 LRU에 가까워지지만, 5로도 충분한 경우가 대부분이다
```

---

## 싱글 스레드의 적: 느린 명령

싱글 스레드 구조에서 한 명령이 오래 걸리면 그 동안 다른 모든 요청이 밀린다. 운영 중 레이턴시 스파이크의 대부분은 이 패턴이다.

### 주의해야 하는 명령들

```bash
# 위험한 명령들 (O(n) 이상)
KEYS *              # 전체 키 스캔. 절대 프로덕션에서 쓰지 말 것. SCAN으로 대체.
SMEMBERS largeSet   # Set 전체 반환. SSCAN으로 대체.
HGETALL largeHash   # Hash 전체 반환. HSCAN으로 대체.
LRANGE list 0 -1    # List 전체 반환. 범위를 제한할 것.
SORT                # O(n+m*log(m)). 대량 데이터에 쓰면 안 됨.
```

```bash
# Slow Log로 느린 명령 추적
redis-cli CONFIG SET slowlog-log-slower-than 10000  # 10ms 이상
redis-cli CONFIG SET slowlog-max-len 128
redis-cli SLOWLOG GET 10
```

### DEL vs UNLINK

큰 키를 `DEL`로 삭제하면 메인 스레드에서 메모리 해제가 일어나서 블로킹된다. Hash가 100만 필드면 수백 ms 걸릴 수 있다.

```bash
# DEL: 동기 삭제. 작은 키에만 사용.
DEL small_key

# UNLINK: 비동기 삭제. 큰 키는 반드시 이걸 써야 한다.
UNLINK large_hash

# 4.0+에서는 lazyfree 설정으로 DEL도 비동기로 동작시킬 수 있다
lazyfree-lazy-expire yes        # TTL 만료 시 비동기 해제
lazyfree-lazy-server-del yes    # RENAME 등 내부 삭제 시 비동기
lazyfree-lazy-user-del yes      # DEL을 UNLINK처럼 동작
```

---

## 복제(Replication) 내부 동작

### 전체 동기화(Full Sync)

레플리카가 처음 연결되거나 연결이 오래 끊어졌으면 전체 동기화가 발생한다:

```
전체 동기화 흐름:

  1. 레플리카 → 마스터: PSYNC ? -1 (첫 연결)
  2. 마스터: BGSAVE 실행 (fork + RDB 생성)
  3. 마스터: RDB 생성 중 들어온 명령을 replication buffer에 저장
  4. 마스터 → 레플리카: RDB 파일 전송
  5. 레플리카: 기존 데이터 삭제, RDB 로드
  6. 마스터 → 레플리카: replication buffer의 명령 전송
  7. 이후: 실시간 명령 전파 (partial sync)
```

문제가 되는 경우:

- 마스터 메모리가 크면 RDB 생성에 오래 걸린다
- 전송 중에 replication buffer가 넘치면 다시 전체 동기화를 해야 한다
- 여러 레플리카가 동시에 연결하면 fork()가 여러 번 발생할 수 있다

### 부분 동기화(Partial Sync)

레플리카가 잠깐 끊어졌다 다시 연결되면 부분 동기화를 시도한다:

```
부분 동기화 조건:
  - 마스터의 repl_backlog에 끊긴 시점 이후의 데이터가 남아있어야 한다
  - replication ID가 일치해야 한다

repl-backlog-size 256mb  # 기본 1MB는 너무 작다. 쓰기 부하에 맞게 늘릴 것.
```

`repl-backlog-size`가 작으면 짧은 네트워크 끊김에도 전체 동기화가 발생한다. 쓰기 QPS * 평균 명령 크기 * 예상 끊김 시간으로 계산해서 설정한다.

---

## Redis의 한계

**메모리 비용**: 모든 데이터가 메모리에 있어야 한다. 100GB 데이터면 100GB+ 메모리가 필요하다. 비용이 디스크 기반 DB보다 수십 배 높다.

**싱글 스레드 병목**: CPU 하나만 쓴다. KEYS, SORT 같은 무거운 명령 하나가 전체 서비스를 멈출 수 있다. 코어가 많아도 의미 없다.

**fork() 오버헤드**: RDB/AOF rewrite 시 fork()가 발생한다. 메모리가 클수록 fork 지연과 CoW 메모리 사용이 커진다. 쓰기가 많은 인스턴스에서는 메모리의 2배까지 필요할 수 있다.

**데이터 구조 제약**: 조인, 집계, 범위 쿼리 같은 복잡한 질의가 안 된다. 관계형 데이터를 다루려면 애플리케이션에서 처리해야 한다.

**대규모 클러스터 운영**: 클러스터 노드가 많아지면 gossip 프로토콜 트래픽이 증가한다. 멀티 키 연산은 같은 슬롯에 있는 키끼리만 가능해서 데이터 모델링에 제약이 생긴다.

---

## 참조

- Redis 소스코드 (ae.c, server.c): https://github.com/redis/redis
- Redis 내부 구조 문서: https://redis.io/docs/reference/internals/
- Redis 설정 레퍼런스: https://redis.io/docs/management/config/
- jemalloc: https://github.com/jemalloc/jemalloc
