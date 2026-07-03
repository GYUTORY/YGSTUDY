---
title: Valkey — 설치·운영·마이그레이션 실무
tags: [database, nosql, valkey, redis, in-memory, cache, cluster, elasticache, memorystore]
updated: 2026-04-23
---

# Valkey

> Redis 라이선스 변경 배경과 Valkey 포크의 요약은 [Redis 심화 10장](../Redis/Redis_Advanced.md) 참고. 이 문서는 Valkey를 실제로 운영하면서 부딪히는 부분 — 설치, Redis와의 차이점, 클러스터 구성, 마이그레이션, 클라우드 전환, 모듈 대체 — 을 다룬다.

---

## 1. Valkey가 뭔가

### 1.1 포크의 배경

2024년 3월 Redis Labs(현 Redis Inc.)가 Redis 7.4부터 라이선스를 BSD에서 SSPL + RSALv2 듀얼 라이선스로 바꿨다. Redis 소스 코드를 그대로 매니지드 서비스로 판매하던 AWS, Google, Oracle 같은 클라우드 벤더가 직격탄을 맞았다. 이들이 Linux Foundation 산하로 Redis 7.2.4 마지막 BSD 버전을 포크해 만든 프로젝트가 Valkey다.

일주일도 안 되는 속도로 조직되어 움직였다. 처음부터 중립 재단 소속으로 설계했기 때문에 특정 벤더가 좌지우지할 수 없는 구조다. 거버넌스는 TSC(Technical Steering Committee) 투표로 결정되고, 초기 TSC 멤버는 AWS, Google, Alibaba, Ericsson, Huawei 등에서 나왔다.

### 1.2 이름과 포지션

"Valkey"는 Valhalla + Key의 합성어다. Redis와 호환되는 대체재를 넘어서 자체 발전 방향을 가진다는 게 프로젝트 선언이다. 실제로 7.2.5부터는 Redis에 없는 기능을 독자적으로 추가하고 있다.

현재 릴리스 라인:

```
Valkey 릴리스 히스토리:
  7.2.5  (2024-04)  최초 릴리스, Redis 7.2.4와 프로토콜 동일
  7.2.6  (2024-06)  버그 수정, 보안 패치
  7.2.7  (2024-08)  버그 수정
  8.0.0  (2024-09)  비동기 I/O, 메모리 -20%, per-slot 메트릭
  8.0.1  (2024-11)  버그 수정
  8.0.2  (2024-12)  버그 수정
  8.1.0  (2025-04)  Hash Field Expiration, 클라이언트별 maxmemory
```

8.0부터는 Redis와 코드베이스가 눈에 띄게 갈라지기 시작한다. 같은 기능 이름이어도 내부 구현이 달라질 수 있다는 점을 기억해야 한다.

---

## 2. 라이선스와 거버넌스

### 2.1 BSD 3-Clause

Valkey는 BSD 3-Clause를 유지한다. 상용 제품에 내장해도 되고, 매니지드 서비스로 제공해도 된다. 조건은 원본 저작권 표시와 라이선스 고지 포함뿐이다. Redis가 7.4 이후 걸어놓은 "경쟁 서비스로 사용 금지" 조항이 없다.

사내 서비스에서 Redis를 썼든 Valkey를 썼든 자사 제품에 내장하는 형태라면 둘 다 문제가 안 된다. 그러나 SaaS 형태로 Redis 자체를 제공하는 서비스를 만들거나, Redis 호환 API를 외부에 노출하는 제품이라면 Valkey가 안전한 선택이다.

### 2.2 기여 모델

Valkey는 CLA(Contributor License Agreement) 대신 DCO(Developer Certificate of Origin)를 쓴다. 커밋에 `Signed-off-by:` 한 줄만 추가하면 된다. Redis가 CLA를 요구하면서 기업 법무팀을 거쳐야 하는 것과 다르다. 사내 엔지니어가 업무 시간에 작은 패치를 기여하기 훨씬 쉬워진 구조다.

---

## 3. 설치와 기본 설정

### 3.1 소스 빌드

```bash
# 최신 안정 버전 클론
git clone --branch 8.1 https://github.com/valkey-io/valkey.git
cd valkey

# 의존성: Ubuntu 기준
sudo apt install -y build-essential pkg-config libssl-dev libsystemd-dev

# TLS 지원 빌드
make BUILD_TLS=yes
sudo make install PREFIX=/usr/local

# 기본 바이너리
which valkey-server   # /usr/local/bin/valkey-server
which valkey-cli      # /usr/local/bin/valkey-cli
```

`redis-server`, `redis-cli` 심볼릭 링크도 자동으로 만들어준다. 기존 스크립트가 `redis-cli`를 호출하고 있어도 그대로 돌아간다. 배포 스크립트 전부를 바꾸지 않고 단계적으로 마이그레이션할 때 유용하다.

### 3.2 패키지 설치

Ubuntu 24.04부터는 공식 APT 저장소에 Valkey 패키지가 들어있다. Red Hat 계열은 EPEL에 있다.

```bash
# Ubuntu / Debian
sudo apt install valkey-server valkey-tools

# Rocky Linux / Alma Linux
sudo dnf install epel-release
sudo dnf install valkey valkey-cli

# macOS (Homebrew)
brew install valkey
```

Homebrew의 경우 `redis`와 `valkey`가 동시에 설치 가능한데, 둘 다 기본 포트 6379를 쓰려고 해서 서비스 등록 시 충돌한다. Valkey를 주로 쓰게 되면 `brew services stop redis`로 먼저 내려야 한다.

### 3.3 설정 파일

`valkey.conf`는 Redis 7.2.4의 `redis.conf`와 키가 전부 동일하다. 파일명만 바뀌었다. 실제로 기존 `redis.conf`를 그대로 `valkey.conf`로 이름만 바꿔서 올려도 동작한다.

```conf
# /etc/valkey/valkey.conf 주요 항목
port 6379
bind 0.0.0.0 -::1
protected-mode yes
requirepass "strong-password-here"

maxmemory 4gb
maxmemory-policy allkeys-lru

appendonly yes
appendfsync everysec
aof-use-rdb-preamble yes

# Valkey 8.0+ 전용
io-threads 4
io-threads-do-reads yes
```

`io-threads`는 Redis 6.0에도 있던 설정인데, Valkey 8.0의 비동기 I/O 스레딩 구현이 더 공격적이다. CPU 코어가 많은 서버에서 체감 효과가 확실히 다르다.

---

## 4. Redis와의 차이점

### 4.1 프로토콜 호환성

Valkey 7.2.5 ~ 8.1까지 RESP2, RESP3 프로토콜을 전부 Redis와 동일하게 지원한다. 클라이언트 라이브러리 입장에서는 구분되지 않는다. `INFO server` 명령을 보내야 `redis_version` 필드와 함께 `valkey_version` 필드가 같이 내려오는 정도다.

```
> INFO server
# Server
redis_version:7.4.0            ← 호환성을 위해 유지됨
valkey_version:8.1.0           ← 실제 Valkey 버전
server_name:valkey             ← 이 필드가 새로 추가됨
```

클라이언트가 `redis_version`을 파싱해서 버전별 분기 로직을 태우고 있다면 이상한 동작이 나올 수 있다. 예를 들어 `redis_version:7.4.0`으로 보고하는데 실제로는 Valkey 8.1이라서 Redis 7.4 전용 기능(Client-side Caching v2 등)이 없을 수 있다. 서버 식별은 `server_name` 필드로 해야 안전하다.

### 4.2 Valkey에만 있는 기능

Valkey 8.0 이후 독자적으로 추가된 것들:

**Per-slot 메트릭 (8.0)**
클러스터 모드에서 슬롯별로 키 개수와 메모리 사용량을 집계한다. 특정 슬롯에 트래픽이 쏠리는 현상(Hot Slot)을 탐지하는 데 필요했다. Redis에는 아직 없다.

```
> CLUSTER COUNTKEYSINSLOT 8192
(integer) 152341
> CLUSTER SLOTSTATS SLOTSRANGE 0 1000
```

**비동기 I/O 스레딩 (8.0)**
Redis 6.0의 io-threads는 읽기/쓰기를 스레드에 분배하긴 하지만 메인 루프와 동기적으로 동작한다. Valkey 8.0은 커맨드 실행과 I/O를 완전히 분리했다. 벤치마크상 GET 처리량이 1.5~2배 증가한다. 대신 커맨드 순서 보장이 약간 달라지는 엣지 케이스가 있어서 Lua 스크립트나 트랜잭션을 많이 쓰는 환경이라면 테스트 후 투입해야 한다.

**Embedded Key (8.0)**
Redis는 키와 값을 각각 별도 할당한다. Valkey 8.0은 키 문자열을 RedisObject 구조체 안에 직접 임베드해서 포인터 하나와 할당 한 번을 절약한다. 작은 키가 많은 워크로드에서 메모리 사용량이 20% 전후로 줄어든다. 세션 스토어처럼 짧은 키와 값이 수천만 개인 경우 체감 효과가 크다.

**Hash Field Expiration (8.1)**
Redis 7.4에서 추가된 기능을 Valkey 8.1에서 자체 구현했다. 해시의 필드 단위로 TTL을 걸 수 있다.

```
> HSET user:1001 name "김철수" session "abc123"
> HEXPIRE user:1001 60 FIELDS 1 session
(integer) 1
> HTTL user:1001 FIELDS 1 session
1) (integer) 58
```

세션 데이터를 해시 하나에 담고 session 필드만 만료시키는 패턴이 가능하다. 기존에는 사용자별로 별도 키를 만들거나 애플리케이션에서 만료 시각을 관리해야 했다.

**Per-client maxmemory (8.1)**
클라이언트마다 쓸 수 있는 메모리 상한을 걸 수 있다. 배치 작업을 돌리는 클라이언트가 실수로 대량 키를 생성해서 서버 메모리를 잡아먹는 사고를 막는 용도다.

### 4.3 Redis에만 있는 기능

Redis 7.4+ 독점 기능은 Valkey에 없다.

- Client-side Caching (RESP3 TRACKING) 의 고급 옵션 일부
- Auto-tiering (RocksDB 연동 메모리 초과 시 디스크 저장)
- Active-Active 복제 (Enterprise 전용)

반대로 Enterprise 제품의 기능 대부분은 오픈소스 Redis에도 없었으니 실질적 차이는 작다.

---

## 5. 클라이언트 호환성

### 5.1 주요 라이브러리 대응 현황

프로토콜 레벨 호환이라 특별한 작업 없이 모두 돌아간다. 다만 일부 라이브러리는 Valkey 전용 릴리스를 따로 내고 있다.

| 언어 | 라이브러리 | 상태 |
|-----|----------|-----|
| Java | Lettuce | Redis 호환 — 설정 그대로 |
| Java | Jedis | Redis 호환 — 설정 그대로 |
| Java | Redisson | Redis 호환, Valkey 8.x 신기능 일부 미지원 |
| Node.js | ioredis | Redis 호환 — 설정 그대로 |
| Node.js | node-redis | Redis 호환 — 설정 그대로 |
| Python | redis-py | Redis 호환, `valkey-py` 별도 포크 존재 |
| Go | go-redis | Redis 호환, `valkey-go` 공식 클라이언트 존재 |
| Rust | fred / redis-rs | Redis 호환 |

`valkey-glide`라는 공식 멀티 언어 클라이언트가 AWS 주도로 개발 중이다. Python, Node.js, Java, Go를 지원한다. Rust로 만든 코어를 FFI로 각 언어에 바인딩한 구조라 성능이 좋고 API가 언어 간 일관성이 있다. 아직 성숙도가 높지는 않아서 신규 프로젝트라면 고려해볼 만하고 기존 프로젝트를 억지로 바꿀 이유는 없다.

### 5.2 Spring Data Redis

Spring Data Redis는 Lettuce/Jedis를 쓰기 때문에 Valkey도 그대로 동작한다. `application.yml`의 호스트, 포트만 바꾸면 된다.

```yaml
spring:
  data:
    redis:
      host: valkey-cluster.internal
      port: 6379
      password: ${VALKEY_PASSWORD}
      timeout: 2000ms
      lettuce:
        pool:
          max-active: 16
          max-idle: 8
          min-idle: 2
```

주의할 점은 `RedisTemplate`의 `keySerializer`를 `StringRedisSerializer`가 아닌 `JdkSerializationRedisSerializer`로 써온 레거시 환경이다. Valkey도 바이트 그대로 저장하니 동작은 같은데, Hash Field Expiration 같은 새 명령은 Spring Data Redis 3.3+에서만 노출된다. 구 버전 Spring Boot라면 `RedisCallback`으로 raw 명령을 직접 던져야 한다.

---

## 6. 클러스터 구성

### 6.1 기본 구성

Redis Cluster와 프로토콜, 슬롯 알고리즘(CRC16 mod 16384), 마이그레이션 절차가 전부 동일하다. `valkey-cli --cluster` 서브커맨드도 이름만 다를 뿐 옵션이 같다.

```bash
# 6노드 클러스터 생성 (Master 3, Replica 3)
valkey-cli --cluster create \
  10.0.1.10:6379 10.0.1.11:6379 10.0.1.12:6379 \
  10.0.1.13:6379 10.0.1.14:6379 10.0.1.15:6379 \
  --cluster-replicas 1

# 노드 추가
valkey-cli --cluster add-node 10.0.1.16:6379 10.0.1.10:6379

# 슬롯 리밸런싱
valkey-cli --cluster rebalance 10.0.1.10:6379
```

### 6.2 설정 차이점

Valkey 8.0부터 클러스터 구성에서 추가된 설정:

```conf
# 복제 버퍼를 공유 메모리로 관리 (Valkey 8.0+)
repl-backlog-shared yes

# per-slot 메트릭 수집
cluster-slot-stats-enabled yes

# 비동기 커넥션 핸드셰이크 타임아웃 (기본 30000ms)
cluster-node-timeout 15000
```

`repl-backlog-shared`는 실무에서 눈에 띄는 개선이다. Redis는 복제 백로그를 Replica 수만큼 복사해 들고 있었는데, Valkey 8.0은 공유 링 버퍼로 관리해서 Replica가 많을수록 메모리 절약이 커진다. 대규모 Read Replica 구성에서 유용하다.

### 6.3 Redis 클러스터와 섞어 쓰기

당장 전부 바꾸기 어려우면 일부 노드만 Valkey로 교체할 수 있다. 프로토콜이 동일하니 Gossip 메시지도 호환된다. 문제가 없는 건 아니다.

- `server_name` 필드가 노드마다 다르면 모니터링 도구가 혼란스러워한다
- Valkey 8.0+ 전용 명령을 Redis 노드가 받으면 에러
- Cluster Info의 일부 필드 네이밍이 미묘하게 다름

실무에서는 섞어 쓰는 기간을 최대한 짧게 잡고, 운영 중 발생하는 경고 로그를 무시할 수 있는지 미리 확인한 뒤 전환을 시작하는 게 낫다.

---

## 7. Redis → Valkey 마이그레이션

### 7.1 마이그레이션 전 체크포인트

실제 전환할 때 가장 먼저 확인해야 하는 건 Redis Modules 사용 여부다. RedisJSON, RediSearch, RedisGraph, RedisTimeSeries, RedisBloom은 전부 Redis Inc. 소유이고 SSPL 라이선스로 배포된다. Valkey는 이걸 로드할 수 없다.

```bash
# 현재 Redis 인스턴스에 로드된 모듈 확인
redis-cli MODULE LIST
# 1) 1) "name"
#    2) "ReJSON"
#    3) "ver"
#    4) (integer) 20608
```

모듈이 하나도 없거나 ReJSON만 쓰고 있다면 전환이 쉽다. RediSearch를 프로덕션에서 검색 엔진처럼 쓰고 있다면 다른 선택지(OpenSearch, Meilisearch, Typesense)로의 이관까지 같이 계획해야 한다.

### 7.2 데이터 이관 방법

**방법 1: 복제 기반 전환 (무중단)**

Valkey 노드를 기존 Redis 마스터의 Replica로 등록한다. 프로토콜이 같으니 복제가 정상 동작한다. 복제가 완료되면 Valkey를 마스터로 승격하고 클라이언트 접속점만 바꾼다.

```bash
# 1. Valkey 노드 준비, Replica 지정
valkey-cli SLAVEOF old-redis-master 6379

# 2. 복제 진행도 확인
valkey-cli INFO replication
# master_link_status:up
# master_sync_in_progress:0   ← 0이면 완료

# 3. Valkey를 독립 마스터로 승격
valkey-cli SLAVEOF NO ONE

# 4. 애플리케이션 접속점 전환 (DNS, 로드밸런서 등)
```

클라이언트 전환 순간에 쓰기가 유실될 수 있다. Blue-Green 전환을 쓰거나, 쓰기 트래픽을 잠시 멈춘 상태에서 스위칭하는 방식이 안전하다.

**방법 2: RDB 파일 복사**

오프라인 전환이 허용되면 RDB 파일을 그대로 옮기는 게 제일 간단하다. Valkey는 Redis 7.2.4의 RDB 포맷을 100% 읽을 수 있다.

```bash
# Redis 쪽에서 저장
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /tmp/dump.rdb

# Valkey 쪽으로 복사 후 기동
scp /tmp/dump.rdb valkey-host:/var/lib/valkey/
# valkey.conf의 dir, dbfilename 경로에 맞춰 배치
systemctl start valkey
```

**방법 3: SCAN + 애플리케이션 레이어 복제**

RDB 복사가 불가능한 환경(권한, 파일 시스템 분리)에서 쓴다. 느리고 원자성 보장도 없어서 일반적으로는 1, 2번이 낫다.

### 7.3 AOF 호환성 함정

RDB는 문제가 없는데 AOF는 주의가 필요하다. Redis 7.4 이후 추가된 커맨드가 AOF에 기록되어 있다면 Valkey가 재생할 때 알 수 없는 명령으로 실패한다. 대표적인 게 `HEXPIRE` — Redis 7.4에서 추가됐고 Valkey는 8.1부터 지원이라 7.2.5 ~ 8.0 사이 버전에서는 재생 불가다.

AOF를 가지고 이관할 때는:

1. 원본 Redis에서 `BGREWRITEAOF`로 현재 상태를 최소 AOF로 압축
2. `aof-use-rdb-preamble yes` 설정으로 RDB+AOF 하이브리드 포맷 저장
3. 이걸 Valkey에 올리면 앞부분 RDB로 초기화하고 뒷부분 AOF만 재생

### 7.4 마이그레이션 후 검증

전환 후 꼭 확인해야 할 지표:

```bash
# 키 개수 비교
redis-cli DBSIZE
valkey-cli DBSIZE

# 메모리 사용량 비교
redis-cli INFO memory | grep used_memory_human
valkey-cli INFO memory | grep used_memory_human

# 명령 처리량 비교 (애플리케이션 전환 후)
valkey-cli INFO stats | grep instantaneous_ops_per_sec

# 복제 지연 확인 (Replica 구성인 경우)
valkey-cli INFO replication | grep lag
```

Valkey로 이관하면 같은 데이터라도 메모리 사용량이 줄어드는 경우가 많다. Embedded Key 최적화 때문이다. 샘플로 10~20% 감소한다면 정상이다. 더 크게 차이나면 둘 중 하나 — 모듈이 빠지면서 내부 데이터가 없어졌거나, 설정이 달라 만료 정책이 다르게 동작하는 중이다.

---

## 8. ElastiCache / Memorystore 전환

### 8.1 AWS ElastiCache

ElastiCache for Valkey가 2024년 10월 정식 출시됐다. 기존 ElastiCache for Redis와 다음이 다르다.

가격은 Valkey 엔진이 동일 스펙 기준 20% 저렴하다. AWS가 로열티 부담 없이 제공할 수 있는 것이 반영된 것이다. 성능은 동등하거나 조금 나은데, ElastiCache 엔진 팀이 자체 최적화를 추가한 부분이 있다.

**전환 절차**

ElastiCache Redis 클러스터에서 Valkey로 in-place 업그레이드가 가능하다. AWS 콘솔 또는 CLI에서 Modify 작업을 걸면 백그라운드에서 복제 기반 전환을 진행한다. 무중단은 아니고 failover 시점에 수 초 정도 접속 끊김이 발생한다.

```bash
aws elasticache modify-replication-group \
  --replication-group-id my-cluster \
  --engine valkey \
  --engine-version 8.1 \
  --apply-immediately
```

실제로 해 보면 클러스터 규모와 데이터량에 따라 30분 ~ 2시간 정도 걸린다. 전환 중에도 읽기/쓰기는 유지된다.

**주의사항**

- ElastiCache Redis 7.1 이하에서만 전환이 지원된다. 7.4 이상은 Valkey에 대응하는 버전이 없어 다운그레이드가 필요하다
- Reserved Node는 자동으로 이관되지 않는다. 별도로 구매 전환을 해야 한다
- 모듈이 로드된 클러스터는 전환 전에 모듈을 제거해야 한다
- IAM 인증, 보안 그룹, 서브넷 그룹은 그대로 유지된다

### 8.2 Google Memorystore

Memorystore for Valkey가 2024년 9월 출시됐다. GA 기준 Valkey 7.2, 8.0을 지원한다. Redis 대비 가격이 약 30% 저렴하다. 역시 in-place 업그레이드를 제공하고 절차는 비슷하다.

```bash
gcloud memorystore instances update my-instance \
  --location=us-central1 \
  --engine=valkey \
  --engine-version=8.0
```

Memorystore는 다중 리전 복제(Cross-region replication) 기능이 Redis 엔진보다 먼저 Valkey에 들어왔다. 글로벌 서비스에서 캐시를 리전 간 복제할 때 고려할 만하다.

### 8.3 Azure Cache

Microsoft는 별도 Valkey 서비스를 내놓지 않았다. Azure Cache for Redis는 Redis Inc.와의 파트너십 관계 때문에 Redis 엔터프라이즈 버전을 제공하는 쪽이다. Azure 환경에서 Valkey를 쓰려면 AKS에 직접 Helm chart로 배포하거나, Aiven, Redis Cloud Alternative 같은 서드파티 서비스를 쓰는 선택지다.

---

## 9. Redis Modules 대체

### 9.1 JSON

**RedisJSON (ReJSON) 대체 옵션**

- **ReJSON 커뮤니티 포크**: AGPL 라이선스 이전 버전 기반 포크가 몇 개 있다. 안정적인 업데이트는 기대하기 어렵다.
- **애플리케이션 레이어 JSON**: 문자열로 저장하고 파싱해서 쓰는 방식. 부분 업데이트는 Lua 스크립트로 처리한다. 쿼리가 많지 않으면 이게 제일 단순하다.
- **Valkey JSON 모듈 (valkey-json)**: AWS가 Apache 2.0으로 공개한 대체 모듈. API가 RedisJSON과 호환된다. 2024년 말부터 사용 가능하다.

```bash
# valkey-json 로드
loadmodule /usr/local/lib/valkey/libjson.so

# RedisJSON과 동일한 API
> JSON.SET user:1 $ '{"name":"김철수","age":30}'
OK
> JSON.GET user:1 $.name
"[\"김철수\"]"
```

### 9.2 검색 (RediSearch)

RediSearch는 대체가 까다롭다. 역인덱스, 집계, 벡터 검색까지 포함하는 완성도 높은 모듈이라 간단히 포크로 해결되지 않는다.

- **valkey-search** (2025년): AWS/Google 주도로 개발 중. 초기 버전은 완전 호환되지 않고 단순 인덱싱 위주다.
- **OpenSearch / Elasticsearch**: 검색 워크로드를 아예 다른 시스템으로 분리. 가장 확실하지만 운영 부담이 늘어난다.
- **PostgreSQL + pg_trgm / pgvector**: 기존 RDBMS에서 전문 검색, 벡터 검색이 가능해졌다. 데이터량이 크지 않으면 이 선택지가 합리적이다.

실무에서 만났던 사례는 RediSearch로 상품 자동완성과 필터를 구현했던 서비스다. 트래픽이 크지 않아서 OpenSearch 도입은 과하고, 그렇다고 valkey-search의 성숙도를 기다릴 여유도 없었다. 결국 PostgreSQL의 `GIN` 인덱스 + `pg_trgm` + `ts_vector`로 옮겼다. 응답 시간이 5ms → 15ms로 늘었지만 허용 가능한 범위였다.

### 9.3 시계열 (RedisTimeSeries)

- **valkey-timeseries**: 커뮤니티 포크 초기 단계
- **InfluxDB, Prometheus**: 시계열 전용 DB로 이관
- **TimescaleDB**: PostgreSQL 위에서 시계열 처리

메트릭성 데이터라면 Prometheus가 운영 편의성이 좋다. 애플리케이션에서 쓰는 시계열(예: 사용자 행동 이벤트)은 TimescaleDB가 쿼리 유연성이 좋아 선호된다.

### 9.4 확률적 자료구조 (RedisBloom)

블룸 필터, Count-Min Sketch, Top-K, t-digest 같은 자료구조다. **valkey-bloom**이 AWS 주도로 개발되어 Apache 2.0으로 공개됐다. API 호환성이 좋아서 이관이 쉽다.

---

## 10. 성능 특성

### 10.1 벤치마크 경향

공식 벤치마크(Valkey-benchmark, memtier_benchmark)에서 Valkey 8.0이 Redis 7.2.4 대비:

- GET: 처리량 1.3~1.5배 (비동기 I/O 효과)
- SET: 처리량 1.2~1.4배
- MGET/MSET: 1.5배 이상 (파이프라이닝 최적화)
- 메모리 사용량: 동일 데이터 기준 15~25% 감소

다만 벤치마크는 마이크로 벤치마크라 실제 워크로드에서는 덜 드라마틱하다. 실서비스에서 재보면 처리량 10~20%, 메모리 10~15% 개선이 일반적인 범위다.

### 10.2 성능 차이가 나타나는 조건

비동기 I/O 효과가 크게 나오는 환경:

- CPU 코어 8개 이상
- 클라이언트 커넥션 수백 개 이상
- 작은 키-값 GET/SET 위주의 워크로드

반대로 체감이 덜한 경우:

- Lua 스크립트 중심 워크로드 (싱글 스레드 병목)
- 큰 값(수 MB) 위주의 워크로드 (네트워크 병목)
- 커넥션 풀 작게 운영하는 환경

### 10.3 튜닝 포인트

```conf
# Valkey 8.0+ 권장 튜닝
io-threads 4                  # CPU 코어 수의 절반 정도
io-threads-do-reads yes

# 큰 워크로드에서
client-output-buffer-limit replica 256mb 64mb 60
repl-backlog-size 128mb
repl-backlog-shared yes

# 메모리 단편화 완화
activedefrag yes
active-defrag-ignore-bytes 100mb
active-defrag-threshold-lower 10
active-defrag-threshold-upper 100
```

`io-threads`를 무작정 올리면 컨텍스트 스위칭이 늘어서 오히려 느려진다. 코어 수의 절반을 기준으로 실제 트래픽으로 측정하면서 조정해야 한다.

---

## 11. 운영 시 주의사항

### 11.1 모니터링

Redis용 모니터링 도구 대부분이 그대로 동작한다. `redis_exporter`(Prometheus)도 Valkey 엔드포인트를 붙이면 메트릭을 수집한다. 일부 Valkey 8.0+ 신규 메트릭은 수집되지 않으니 공식 `valkey-exporter`로 전환하거나 redis_exporter 최신 버전을 써야 한다.

```
# Valkey 8.0+ 신규 메트릭
valkey_slot_stats_key_count{slot="8192"}
valkey_slot_stats_cpu_usec_total{slot="8192"}
valkey_io_threads_active_count
```

### 11.2 백업

RDB, AOF 백업 전략은 Redis와 동일하다. 다만 백업 파일을 Redis로 복구하려 할 때 Valkey 8.0+ 전용 포맷이 들어 있으면 실패한다. Redis로 롤백 가능성을 남겨둘 계획이라면 RDB 저장 시 호환 모드를 확인해야 한다.

### 11.3 보안 업데이트

CVE 대응은 Valkey 프로젝트가 독자적으로 한다. Redis에 발견된 보안 이슈가 Valkey에 자동으로 반영되지는 않는다. 두 프로젝트 릴리스 노트를 모두 모니터링하는 게 안전하다. Valkey 쪽은 보통 Redis보다 빠르게 패치가 나오는 경향이 있다 — 기여자 수가 많고 PR 리뷰 속도가 빠르다.

### 11.4 라이선스 리스크 관리

실무에서 종종 나오는 질문이 "Redis 7.2.4 그대로 써도 되는가"다. SSPL로 변경되기 전 마지막 버전이라 법적으로는 BSD 라이선스다. 단기간 사용에는 문제없다. 다만 보안 패치가 Redis Inc.에서 더 이상 나오지 않는다. Valkey가 7.2.x 라인을 계속 패치하고 있으니 Valkey 7.2.x로 올라가는 게 안전하다.

자사 서비스에 Redis를 임베드해 쓰는 경우에도 SSPL 조항을 한 번은 읽어볼 필요가 있다. 일반적인 클라이언트-서버 사용은 문제없지만, "서비스로 제공"의 경계가 모호한 영역이 있다. 법무 검토 없이 안심하고 쓰려면 Valkey 쪽이 부담이 적다.

---

## 참고

- [Valkey 공식](https://valkey.io)
- [Valkey GitHub](https://github.com/valkey-io/valkey)
- [Valkey 8.0 릴리스 노트](https://github.com/valkey-io/valkey/releases/tag/8.0.0)
- [Valkey 8.1 릴리스 노트](https://github.com/valkey-io/valkey/releases/tag/8.1.0)
- [Redis 심화](../Redis/Redis_Advanced.md) — Redis 클러스터, 센티널, 분산락 심화
- [Redis](../Redis/Redis.md) — Redis 내부 동작 원리와 아키텍처
- [Redis 다루기](../Redis/Redis%20다루기.md) — Redis 기본 사용법
