---
title: Redis 심화
tags: [redis, cluster, sentinel, streams, lua, distributed-lock, spring-data-redis, performance, valkey, redis-functions, split-brain, network-partition, quorum]
updated: 2026-04-02
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

### 2.3 Split-Brain과 네트워크 파티션

Sentinel 환경에서 가장 위험한 장애는 split-brain이다. 네트워크 파티션으로 Master가 Sentinel 과반수와 분리되면, 기존 Master는 계속 쓰기를 받는데 Sentinel은 새 Master를 승격시킨다. 이 순간 Master가 2대가 되고, 양쪽에 다른 데이터가 쓰인다.

```
정상 상태:
  [Sentinel 1] [Sentinel 2] [Sentinel 3]
       │             │             │
       └─────────────┼─────────────┘
                     │
              ┌──────────┐
              │  Master   │──→ Replica 1, Replica 2
              └──────────┘

네트워크 파티션 발생:
  ── 파티션 A ──────────        ── 파티션 B ──────────
  [Sentinel 1] [Sentinel 2]     [Sentinel 3]
       │             │                │
       │             │           ┌──────────┐
       │             │           │  Master   │ ← 클라이언트가 여전히 쓰기 중
       │             │           └──────────┘
       │             │
  ┌──────────┐       │
  │ Replica 1│ ← 새 Master로 승격
  └──────────┘

  → Master가 2대 존재하는 split-brain 상태
  → 파티션 해소 후 기존 Master는 Replica로 강등되면서 파티션 B 쪽 쓰기가 유실됨
```

이 문제를 완전히 막을 수는 없지만, 데이터 유실 범위를 줄이는 설정이 있다.

```conf
# redis.conf (Master에 설정)
min-replicas-to-write 1        # 최소 1대의 Replica가 연결되어야 쓰기 허용
min-replicas-max-lag 10        # Replica의 복제 지연이 10초 이내여야 쓰기 허용
```

```
min-replicas-to-write가 동작하는 방식:
  파티션 발생 → 기존 Master에서 Replica가 끊어짐
  → min-replicas-to-write 조건 미충족
  → 기존 Master가 쓰기를 거부 (NOREPLICAS 에러)
  → 파티션 B 쪽 데이터 유실 방지

  주의:
  - Replica가 모두 끊어지면 Master도 쓰기 불가 → 가용성이 떨어진다
  - 쓰기 가용성과 데이터 안전성 사이의 트레이드오프
  - min-replicas-to-write 1 + Replica 2대 구성이면 1대 장애까지는 쓰기 가능
```

실제로 네트워크 파티션이 발생하면 클라이언트 쪽에서도 대응해야 한다. Lettuce의 Sentinel 연결에서 `refresh` 간격을 짧게 잡아야 새 Master로 빨리 전환된다. 파티션 해소 후 `CLIENT LIST`로 기존 Master에 붙어있는 커넥션이 남아있는지 확인하고, 남아있으면 `CLIENT KILL`로 정리해야 한다.

### 2.4 Quorum 설정 실수 사례

quorum은 ODOWN 판정에 필요한 최소 Sentinel 동의 수다. 이 값을 잘못 설정하면 페일오버가 안 되거나 너무 빨리 된다.

```
사례 1: Sentinel 2대에 quorum 2

  sentinel monitor mymaster 192.168.1.1 6379 2

  Sentinel이 2대뿐인데 quorum이 2면, Sentinel 1대만 죽어도 ODOWN 판정이 불가능하다.
  Master가 장애 나도 페일오버가 실행되지 않는다.

  → Sentinel은 최소 3대, quorum은 2로 설정한다.
  → Sentinel 수가 홀수여야 리더 선출 시 과반수 계산이 깔끔하다.

사례 2: Sentinel 5대에 quorum 1

  sentinel monitor mymaster 192.168.1.1 6379 1

  Sentinel 1대만 "Master 죽었다"고 판단하면 바로 ODOWN이 된다.
  네트워크 일시 지연으로 Sentinel 1대가 Master와 통신 실패 → 불필요한 페일오버 발생
  페일오버가 잦으면 데이터 정합성 문제와 커넥션 끊김이 반복된다.

  → quorum은 (Sentinel 수 / 2) + 1 이 적정선이다.
  → 5대면 quorum 3, 3대면 quorum 2.

사례 3: quorum과 과반수 혼동

  quorum은 ODOWN 판정에만 사용된다. 실제 페일오버를 실행하려면 Sentinel 과반수의
  동의가 별도로 필요하다.

  Sentinel 5대, quorum 2:
    - ODOWN: 2대 동의면 Master를 down으로 판정 ← quorum
    - 리더 선출: 3대 이상 동의 필요 (과반수) ← quorum과 무관
    - quorum을 낮춰도 과반수 미달이면 페일오버는 실행되지 않는다
```

### 2.5 Sentinel 모니터링 명령어

Sentinel 상태를 확인하는 명령어는 redis-cli로 Sentinel 포트(기본 26379)에 접속해서 사용한다.

```bash
# Sentinel 접속
redis-cli -p 26379

# 감시 중인 Master 정보
SENTINEL masters
# → 이름, IP, 포트, 상태(flags), 연결된 Replica 수, Sentinel 수 등

# 특정 Master의 상세 정보
SENTINEL master mymaster
# → num-slaves, num-other-sentinels, quorum, failover-timeout 등 확인

# Master의 Replica 목록
SENTINEL replicas mymaster
# → 각 Replica의 IP, 포트, 상태, 복제 지연(master-link-down-time) 등

# 다른 Sentinel 목록
SENTINEL sentinels mymaster
# → 각 Sentinel의 IP, 포트, 마지막 통신 시간

# 현재 Master 주소 조회 (클라이언트가 사용)
SENTINEL get-master-addr-by-name mymaster
# → "192.168.1.1" "6379"

# 페일오버 히스토리 (로그에서 확인)
SENTINEL failover-status mymaster

# 수동 페일오버 트리거 (테스트 시)
SENTINEL failover mymaster
# → 강제로 페일오버 실행, 현재 Master를 Replica로 강등

# Sentinel 설정 변경 (런타임)
SENTINEL SET mymaster down-after-milliseconds 10000
SENTINEL SET mymaster failover-timeout 120000

# 모니터링 대상 추가/제거
SENTINEL MONITOR newmaster 192.168.1.5 6379 2
SENTINEL REMOVE mymaster
```

```
운영 시 주기적으로 확인할 항목:
  1. SENTINEL masters → flags가 "master"인지 (s_down, o_down이 붙어있으면 문제)
  2. SENTINEL replicas mymaster → 모든 Replica가 "slave" 상태인지
  3. SENTINEL sentinels mymaster → Sentinel 수가 예상과 일치하는지
  4. Master의 INFO replication → connected_slaves 수, repl_backlog_active 여부

  Sentinel 수가 예상보다 많으면 이전 Sentinel이 정리되지 않은 것이다.
  SENTINEL RESET mymaster로 Sentinel 목록을 초기화할 수 있다.
  단, 모든 Sentinel에서 실행해야 한다.
```

### 2.6 설정

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

### 2.7 Sentinel vs Cluster — 실무 선택 기준

단순 비교표로는 판단이 안 된다. 실제로 어떤 상황에서 무엇을 고르는지가 중요하다.

| 항목 | Sentinel | Cluster |
|------|----------|---------|
| **목적** | 고가용성 (HA) | HA + 수평 확장 |
| **데이터 분산** | X (단일 Master) | O (멀티 Master) |
| **자동 페일오버** | O | O |
| **최대 메모리** | 단일 노드 메모리 | 노드 수 x 메모리 |
| **멀티 키 연산** | 제약 없음 | 같은 슬롯만 가능 |
| **복잡도** | 낮음 | 높음 |
| **적합한 경우** | 10GB 이하, HA 필요 | 대용량, 높은 처리량 |

#### 데이터 크기 기준

```
데이터가 단일 서버 메모리에 들어가는가?

  10GB 이하:
    → Sentinel로 충분하다. Cluster를 쓰면 운영 복잡도만 올라간다.
    → Master 1대 + Replica 2대 + Sentinel 3대 = 총 6프로세스
    → 단순하고, 멀티 키 연산도 자유롭다.

  10~50GB:
    → 메모리에 여유가 있으면 Sentinel, 없으면 Cluster.
    → 64GB 메모리 서버에 50GB Redis를 올리면 포크 시 메모리 부족이 온다.
    → maxmemory를 물리 메모리의 50%로 잡았을 때 데이터가 들어가면 Sentinel.

  50GB 이상:
    → Cluster가 거의 필수다.
    → 단일 서버에 50GB 이상 올리면 포크 시간, RDB 저장 시간, 복제 시간이 모두 길어진다.
    → 노드당 10~20GB 수준으로 분산하는 게 운영하기 편하다.
```

#### 트래픽 패턴 기준

```
읽기 비율이 높은 경우 (읽기 80% 이상):
  → Sentinel + ReadFrom.REPLICA_PREFERRED로 읽기 분산
  → Cluster보다 구성이 간단하고 멀티 키 연산에 제약이 없다.

쓰기가 많은 경우:
  → 단일 Master의 쓰기 처리량에 한계가 있다.
  → Redis 단일 노드의 쓰기 한계는 보통 10~15만 ops/sec.
  → 이 이상이 필요하면 Cluster로 쓰기를 분산해야 한다.

MGET, 파이프라인, 트랜잭션을 많이 쓰는 경우:
  → Sentinel이 유리하다.
  → Cluster에서는 해시 태그로 같은 슬롯에 몰아야 하는데,
    데이터 분포가 편중되면 핫스팟이 생긴다.
  → 해시 태그를 과도하게 쓰면 Cluster를 쓰는 의미가 없어진다.
```

#### 운영 인력 기준

```
1~2명이 Redis를 포함한 인프라 전체를 관리하는 경우:
  → Sentinel을 쓴다.
  → Cluster는 슬롯 리밸런싱, 노드 추가/제거, MOVED 에러 대응 등 운영 포인트가 많다.
  → 장애 시 Cluster 상태를 파악하고 복구하는 데 경험이 필요하다.

전담 DBA나 인프라 팀이 있는 경우:
  → 규모에 따라 Cluster를 고려한다.
  → 클라우드 매니지드 서비스(ElastiCache, Memorystore)를 쓰면
    Cluster 운영 부담이 크게 줄어든다.
```

### 2.8 Sentinel에서 Cluster로 마이그레이션

데이터가 커지거나 트래픽이 증가해서 Sentinel에서 Cluster로 옮겨야 하는 경우가 있다. 무중단으로 하려면 단계적으로 접근해야 한다.

```
마이그레이션 순서:

1. Cluster 구축
   - 별도 서버에 Redis Cluster를 새로 구성한다.
   - Master 3대 + Replica 3대 (최소 구성).

2. 데이터 마이그레이션
   - redis-cli --cluster import 는 단건 처리라 느리다.
   - 대량 데이터는 RDB 파일 기반 마이그레이션이 빠르다.
     → Sentinel의 Replica에서 BGSAVE → RDB 파일 추출
     → redis-shake 같은 도구로 Cluster에 적재
   - 키 수가 적으면(수백만 이하) DUMP/RESTORE 조합도 가능하다.

3. 애플리케이션 코드 수정
   - Spring Boot 설정을 sentinel → cluster로 변경.
   - 멀티 키 연산이 있으면 해시 태그를 추가하거나 로직을 변경해야 한다.
     → MGET key1 key2 key3 → 같은 슬롯이 아니면 에러
     → {prefix}:key1, {prefix}:key2 형태로 변경하거나 개별 GET으로 분리
   - KEYS, SCAN 명령이 있으면 노드별로 실행하도록 변경한다.

4. 듀얼 라이트 (선택)
   - 전환 기간 동안 Sentinel과 Cluster 양쪽에 쓰기.
   - 읽기를 Cluster로 전환하면서 데이터 정합성 확인.
   - 정합성이 확인되면 Sentinel 쓰기를 중단한다.

5. 전환 완료
   - 모든 트래픽을 Cluster로 전환한다.
   - Sentinel 환경은 일정 기간 유지 후 제거한다.
```

```
주의사항:
  - SELECT (DB 번호) 사용 시: Cluster는 DB 0만 지원한다.
    Sentinel에서 DB 1, DB 2를 쓰고 있었다면 키 네이밍을 바꿔야 한다.
  - Lua 스크립트: KEYS 파라미터로 전달하는 모든 키가 같은 슬롯에 있어야 한다.
    스크립트 내에서 동적으로 키를 생성하면 CROSSSLOT 에러가 난다.
  - Pub/Sub: 기존 SUBSCRIBE/PUBLISH는 Cluster 전 노드에 브로드캐스트된다.
    Redis 7.0+면 Sharded Pub/Sub(SSUBSCRIBE/SPUBLISH)으로 변경한다.
```

### 2.9 아키텍처별 장애 패턴과 대응

#### Sentinel에서 흔히 겪는 장애

```
1. 페일오버 후 클라이언트가 기존 Master에 계속 접속

  원인: 클라이언트의 Sentinel 토폴로지 갱신이 늦음.
  증상: 새 Master로 전환됐는데 쓰기가 기존 Master에 계속 들어감.
       파티션 해소 후 기존 Master가 Replica로 강등되면서 데이터 유실.

  대응:
  - Lettuce의 sentinel refresh 간격을 짧게 잡는다 (기본 10s → 2~5s).
  - 기존 Master의 redis.conf에 min-replicas-to-write 1을 설정한다.
  - 페일오버 직후 SENTINEL get-master-addr-by-name으로 Master 주소를 확인한다.

2. Sentinel 프로세스가 Redis Master와 같은 서버에 있음

  원인: 비용 절감으로 같은 서버에 배치.
  증상: 서버 장애 시 Sentinel도 같이 죽어서 quorum 미달 → 페일오버 불가.

  대응:
  - Sentinel은 Redis와 다른 서버에 배치한다.
  - 최소한 3대의 Sentinel을 서로 다른 서버 또는 가용 영역에 둔다.

3. down-after-milliseconds가 너무 짧음

  원인: 빠른 장애 감지를 위해 1초 같은 짧은 값으로 설정.
  증상: GC pause나 네트워크 일시 지연으로 불필요한 페일오버 반복.
       페일오버마다 커넥션이 끊기고 복제가 다시 시작됨.

  대응:
  - 5~10초가 적정선이다. 너무 짧으면 false positive가 많다.
  - 페일오버 빈도가 월 1회 이상이면 값을 올려야 한다.
```

#### Cluster에서 흔히 겪는 장애

```
1. 슬롯 커버리지 실패 (CLUSTERDOWN)

  원인: Master 1대가 죽었는데 해당 Replica도 없거나 Replica까지 죽음.
  증상: 해당 슬롯 범위의 키에 접근 불가.
       cluster-require-full-coverage yes(기본값)면 클러스터 전체가 쓰기 거부.

  대응:
  - cluster-require-full-coverage no로 변경하면, 문제 슬롯을 제외한
    나머지 슬롯은 정상 동작한다. 부분 장애가 전체 장애로 번지지 않는다.
  - 각 Master에 Replica를 2대 이상 붙이면 동시 장애에 대비할 수 있다.

2. 핫스팟 (특정 노드에 트래픽 집중)

  원인: 인기 키가 특정 슬롯에 몰리거나, 해시 태그를 과도하게 사용.
  증상: 특정 Master의 CPU가 100%에 가까운데 나머지 노드는 한가함.
       해당 노드의 응답 시간이 급격히 증가.

  대응:
  - 핫키를 찾는다: redis-cli --hotkeys (Redis 4.0+, LFU 정책 필요)
  - 핫키를 여러 키로 분산한다: key → key:1, key:2, ... key:N
    클라이언트가 랜덤으로 읽으면 슬롯이 분산된다.
  - 읽기 핫스팟이면 ReadFrom.REPLICA로 Replica에서 읽게 한다.

3. 리샤딩 중 성능 저하

  원인: 슬롯 마이그레이션 시 키를 하나씩 MIGRATE하는데, 큰 키가 있으면 블로킹.
  증상: 리샤딩 중 특정 요청에서 타임아웃 발생.
       ASK 리다이렉션이 급증.

  대응:
  - 리샤딩 전에 OBJECT ENCODING과 MEMORY USAGE로 큰 키를 확인한다.
  - cluster-migration-barrier 설정으로 리샤딩 속도를 조절한다.
  - 트래픽이 적은 시간대에 리샤딩을 수행한다.
  - 노드 추가 시 처음부터 충분한 노드 수로 구성하면 리샤딩 빈도를 줄일 수 있다.

4. 노드 간 Gossip 프로토콜 부하

  원인: 클러스터 노드가 수십 대 이상으로 커짐.
  증상: cluster-node-timeout 시간 내에 모든 노드 상태를 교환하지 못함.
       불필요한 PFAIL/FAIL 판정이 발생.

  대응:
  - 노드 수를 100대 이내로 유지한다 (Redis 공식 권장).
  - cluster-node-timeout을 너무 짧게 잡지 않는다 (15초 이상 권장).
  - 노드가 더 필요하면 클러스터를 여러 개로 분리하고 애플리케이션 레벨에서 라우팅한다.
```

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

## 8. 프로덕션 트러블슈팅

### 8.1 OOM Killer 대응

Linux의 OOM Killer가 Redis 프로세스를 죽이는 경우가 있다. `dmesg | grep -i oom`에서 redis-server가 보이면 이 문제다.

```bash
# OOM Killer에 의해 종료된 로그 확인
dmesg | grep -i "oom.*redis"
# Out of memory: Kill process 12345 (redis-server) score 800

# Redis의 OOM 점수 낮추기 (우선순위 보호)
echo -17 > /proc/$(pidof redis-server)/oom_score_adj

# /etc/sysctl.conf에서 overcommit 정책 변경
# vm.overcommit_memory = 1 로 설정해야 포크(BGSAVE) 시 실패하지 않는다
sysctl vm.overcommit_memory=1
```

Redis는 `maxmemory`를 설정해도 OS 레벨에서 추가 메모리를 사용한다. 출력 버퍼, 복제 백로그, Lua 스크립트 메모리 등은 `maxmemory` 제한 밖이다. 물리 메모리의 60~70%를 `maxmemory`로 잡고, 나머지는 OS와 Redis 내부 오버헤드용으로 남겨야 한다.

### 8.2 커넥션 풀 고갈 — Lettuce vs Jedis

커넥션 풀이 고갈되면 `RedisConnectionFailureException`이나 `Cannot get Jedis connection`이 발생한다. Lettuce와 Jedis는 커넥션 관리 방식이 근본적으로 다르다.

```
Lettuce:
  - 단일 커넥션을 여러 스레드가 공유 (Netty 기반, 비동기 I/O)
  - 커넥션 풀이 기본적으로 필요 없다
  - 문제가 생기는 경우: blocking 명령(BLPOP 등)이나 트랜잭션(MULTI/EXEC) 사용 시
    → 전용 커넥션이 필요하다
  - connection sharing이 꺼져 있거나 pool 설정 없이 blocking 명령을 쓰면 커넥션 부족 발생

Jedis:
  - 요청마다 커넥션 풀에서 꺼내서 사용 (동기 I/O)
  - 풀 크기가 부족하면 바로 고갈된다
  - max-active가 너무 작거나, 커넥션 반환이 안 되면(close 누락) 풀이 마른다
```

```yaml
# Lettuce 커넥션 풀 (blocking 명령 사용 시 필요)
spring:
  data:
    redis:
      lettuce:
        pool:
          enabled: true
          max-active: 16
          max-idle: 8
          min-idle: 4
          max-wait: 3000ms    # 이 시간 안에 커넥션 못 얻으면 예외

# Jedis 커넥션 풀
spring:
  data:
    redis:
      jedis:
        pool:
          max-active: 32      # 동시 요청 수 기준으로 설정
          max-idle: 16
          min-idle: 8
          max-wait: 3000ms
```

Lettuce 환경에서 커넥션 고갈이 의심될 때는 `CLIENT LIST` 명령으로 현재 커넥션 수를 확인한다. 커넥션 수가 비정상적으로 많으면 커넥션 누수(close 누락)를 의심해야 한다.

### 8.3 메모리 단편화

`INFO memory`의 `mem_fragmentation_ratio`가 1.5를 넘으면 단편화가 심한 상태다.

```redis
INFO memory
# mem_fragmentation_ratio: 2.3   ← OS가 할당한 메모리가 실제 사용량의 2.3배
# mem_fragmentation_bytes: 524288000
```

```
단편화가 발생하는 원인:
  - 크기가 다른 키를 반복적으로 생성/삭제
  - 짧은 TTL 키가 대량으로 만료되면서 메모리 구멍이 생김
  - jemalloc 할당자가 OS에 메모리를 반환하지 못하는 경우

대응:
  1. Redis 4.0+에서는 activedefrag 사용
     CONFIG SET activedefrag yes
     CONFIG SET active-defrag-threshold-lower 10    # 단편화 10% 이상이면 시작
     CONFIG SET active-defrag-threshold-upper 100   # 100% 이상이면 최대 노력
     CONFIG SET active-defrag-cycle-min 1           # CPU 사용률 최소 1%
     CONFIG SET active-defrag-cycle-max 25          # CPU 사용률 최대 25%

  2. activedefrag로 해결 안 되면 페일오버 후 재시작
     → Replica에서 읽기 전환 후 Master 재시작하면 단편화 해소
```

`mem_fragmentation_ratio`가 1.0 미만이면 Redis가 swap을 쓰고 있다는 뜻이다. 이 경우는 메모리 부족이므로 즉시 `maxmemory`를 줄이거나 노드를 추가해야 한다.

### 8.4 포크 시 메모리 2배 사용

BGSAVE(RDB 저장)나 AOF 재작성 시 Redis는 `fork()`를 호출한다. Copy-on-Write(CoW) 방식이라 이론적으로는 메모리가 크게 늘지 않지만, 쓰기가 많은 워크로드에서는 거의 2배까지 메모리를 사용한다.

```
문제 시나리오:
  물리 메모리: 16GB
  Redis maxmemory: 12GB
  BGSAVE 시작 → fork()
  쓰기 요청이 계속 들어옴 → CoW로 페이지 복사 발생
  메모리 사용량: 12GB(부모) + 10GB(자식 CoW) = 22GB
  → OOM Killer 발동 또는 swap 폭주

대응:
  1. maxmemory를 물리 메모리의 50% 이하로 설정 (쓰기가 많은 경우)
  2. Transparent Huge Pages(THP) 비활성화 — CoW 단위가 2MB로 커져서 메모리 낭비 심해짐
     echo never > /sys/kernel/mm/transparent_hugepage/enabled
  3. Replica에서만 RDB 저장 수행하고 Master는 RDB 저장 비활성화
     # Master: save ""
     # Replica에서 BGSAVE 실행
```

### 8.5 maxmemory 설정 실수로 인한 장애

실제로 많이 겪는 장애 패턴이다.

```
사례 1: maxmemory를 설정하지 않음
  - Redis 기본값은 maxmemory 0 (무제한)
  - 메모리를 계속 써서 OS가 OOM Killer로 프로세스를 죽임
  - 운영 환경에서는 반드시 maxmemory를 명시해야 한다

사례 2: maxmemory-policy가 noeviction (기본값)
  - 메모리가 가득 차면 쓰기 명령이 전부 에러를 반환한다
  - 캐시 용도인데 noeviction이면 서비스 장애로 이어진다
  - 캐시: allkeys-lru 또는 allkeys-lfu 사용
  - 세션/큐: volatile-lru + TTL 필수 설정

사례 3: maxmemory를 CONFIG SET으로만 변경하고 redis.conf는 안 고침
  - Redis 재시작하면 redis.conf의 설정으로 돌아간다
  - CONFIG REWRITE로 현재 설정을 파일에 반영하거나, 직접 redis.conf를 수정해야 한다
```

```bash
# 현재 설정 확인
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET maxmemory-policy

# 설정 변경 + 파일 반영
redis-cli CONFIG SET maxmemory 4gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG REWRITE    # redis.conf에 반영
```

## 9. Redis 7.x 주요 변경사항

### 9.1 Redis Functions (Lua 스크립트 대체)

Redis 7.0부터 Functions가 도입됐다. Lua 스크립트는 클라이언트가 매번 보내야 하지만, Functions는 Redis에 등록해두고 이름으로 호출한다. 라이브러리 단위로 관리되고, 복제와 영속성도 지원한다.

```redis
# 함수 라이브러리 등록
FUNCTION LOAD "#!lua name=mylib
redis.register_function('my_set_and_expire', function(keys, args)
    redis.call('SET', keys[1], args[1])
    redis.call('EXPIRE', keys[1], tonumber(args[2]))
    return redis.call('GET', keys[1])
end)

redis.register_function('my_rate_check', function(keys, args)
    local current = tonumber(redis.call('INCR', keys[1]) or '0')
    if current == 1 then
        redis.call('EXPIRE', keys[1], tonumber(args[1]))
    end
    return current <= tonumber(args[2]) and 1 or 0
end)
"

# 함수 호출
FCALL my_set_and_expire 1 user:1000 "John" 3600
FCALL my_rate_check 1 rate:client:42 60 100

# 등록된 함수 목록
FUNCTION LIST
FUNCTION LIST LIBRARYNAME mylib

# 함수 삭제
FUNCTION DELETE mylib

# 함수 덤프/복원 (클러스터 간 이동)
FUNCTION DUMP
FUNCTION RESTORE <serialized-data>
```

```
Lua 스크립트 vs Functions:
  EVAL/EVALSHA:
    - 클라이언트가 스크립트를 보내야 한다
    - SCRIPT FLUSH 하면 날아간다
    - 복제/AOF에 스크립트 전체가 포함됨

  Functions:
    - Redis에 영구 등록, 이름으로 호출
    - RDB/AOF에 함수 정의 포함 → 재시작해도 유지
    - 라이브러리 단위 관리 (여러 함수를 묶을 수 있음)
    - Replica에 자동 복제
    - 기존 EVAL/EVALSHA도 계속 동작한다
```

### 9.2 Sharded Pub/Sub

기존 Pub/Sub은 클러스터 환경에서 모든 노드에 메시지를 브로드캐스트한다. 채널이 100개든 1개든 전 노드에 전파되므로 노드 수가 늘면 오버헤드도 같이 늘었다.

Redis 7.0의 Sharded Pub/Sub은 채널을 해시 슬롯에 매핑한다. 해당 슬롯을 담당하는 노드에서만 메시지가 처리된다.

```redis
# 기존 Pub/Sub (클러스터 전체 브로드캐스트)
SUBSCRIBE channel1
PUBLISH channel1 "message"

# Sharded Pub/Sub (슬롯 기반, 7.0+)
SSUBSCRIBE channel1
SPUBLISH channel1 "message"

# channel1의 해시 슬롯을 담당하는 노드에서만 처리된다
# 클러스터가 30노드여도 해당 슬롯의 Master+Replica에서만 메시지 흐름
```

```
언제 Sharded Pub/Sub을 써야 하는가:
  - 클러스터 환경에서 채널 수가 많을 때
  - 노드 수가 많아서 기존 Pub/Sub의 브로드캐스트 오버헤드가 큰 경우
  - 단일 인스턴스나 Sentinel 환경에서는 기존 Pub/Sub을 그대로 쓰면 된다
```

### 9.3 Client-side Caching

Redis 6.0에서 도입, 7.x에서 안정화됐다. 클라이언트가 키 값을 로컬 메모리에 캐시하고, 서버가 해당 키가 변경되면 무효화(invalidation) 알림을 보내는 방식이다.

```redis
# 클라이언트 추적 활성화
CLIENT TRACKING ON REDIRECT <client-id>
# 이후 GET으로 읽은 키가 변경되면 무효화 메시지 수신

# Broadcasting 모드 (접두사 기반)
CLIENT TRACKING ON BCAST PREFIX user: PREFIX product:
# user:* 또는 product:*로 시작하는 키가 변경되면 알림
```

```
동작 방식:
  1. 클라이언트가 GET user:1000 → 서버가 응답 + 키 추적 시작
  2. 클라이언트가 응답값을 로컬 메모리에 캐시
  3. 다른 클라이언트가 SET user:1000 "new" → 서버가 무효화 메시지 전송
  4. 클라이언트가 로컬 캐시에서 user:1000 삭제
  5. 다음 조회 시 서버에 다시 요청

Lettuce 6.x부터 Client-side Caching 지원:
  StatefulRedisConnection<String, String> conn = client.connect();
  CacheFrontend<String, String> frontend = ClientSideCaching.enable(
      CacheAccessor.forMap(new ConcurrentHashMap<>()),
      conn,
      TrackingArgs.Builder.enabled()
  );
  String value = frontend.get("user:1000");  // 로컬 캐시 → 미스 시 서버 조회
```

Redis에 대한 네트워크 요청 자체를 줄이므로 읽기 비율이 높은 워크로드에서 지연 시간이 크게 줄어든다. 단, 캐시 일관성은 best-effort다. 네트워크 문제로 무효화 메시지가 유실될 수 있으므로 로컬 캐시에 TTL을 함께 설정하는 게 안전하다.

### 9.4 ACL v2 (Redis 7.0+)

Redis 6.0에서 도입된 ACL이 7.0에서 크게 개선됐다. Selector 개념이 추가되어 하나의 사용자에게 여러 권한 규칙을 조합할 수 있다.

```redis
# 사용자 생성 (기본)
ACL SETUSER app-reader on >password123 ~user:* &* +get +mget +hgetall

# ACL v2 Selector — 하나의 사용자에게 복합 권한 부여
ACL SETUSER api-service on >securepass \
    ~cache:* +get +set +del +expire \
    (~queue:* +lpush +rpop +llen)

# api-service는:
#   cache:* 키에 대해 get, set, del, expire 허용
#   queue:* 키에 대해 lpush, rpop, llen 허용
#   그 외 키/명령은 차단

# ACL 목록 확인
ACL LIST
ACL GETUSER api-service

# ACL 파일로 관리
ACL LOAD        # aclfile에서 로드
ACL SAVE        # 현재 ACL을 파일에 저장
```

```conf
# redis.conf
aclfile /etc/redis/users.acl

# /etc/redis/users.acl
user default on >defaultpass ~* &* +@all
user app-reader on >readerpass ~app:* &* +@read
user app-writer on >writerpass ~app:* &* +@write +@read
user admin on >adminpass ~* &* +@all
```

운영 환경에서는 `default` 사용자의 권한을 최소화하고, 애플리케이션별로 전용 사용자를 만들어야 한다. `requirepass`만으로 관리하던 방식은 Redis 6.0 이후로는 권장하지 않는다.

## 10. Redis 라이선스 변경과 Valkey

### 10.1 라이선스 변경 (2024년 3월)

Redis Labs가 Redis 7.4부터 라이선스를 BSD에서 **SSPL + RSALv2 듀얼 라이선스**로 변경했다. 클라우드 벤더가 Redis를 그대로 서비스로 제공하는 것을 막기 위한 결정이다.

```
라이선스 변경의 영향:
  - Redis를 자사 서비스에 내장하여 사용: 영향 없음 (대부분의 경우)
  - Redis를 기반으로 매니지드 서비스 제공: SSPL/RSALv2 제약에 해당
  - AWS ElastiCache, Google Memorystore 등 클라우드 서비스에 직접 영향

  SSPL: 서비스로 제공하려면 관리 도구 포함 전체 소스코드 공개 필요
  RSALv2: Redis를 경쟁 제품의 기반으로 사용 금지
```

### 10.2 Valkey 포크

라이선스 변경 직후 Linux Foundation 주도로 **Valkey**가 Redis 7.2.4 기반으로 포크됐다. AWS, Google, Oracle, Ericsson 등이 참여하고 있다.

```
Valkey 특징:
  - BSD 3-Clause 라이선스 (오픈소스 유지)
  - Redis 7.2.4와 호환 — 기존 Redis 클라이언트, 명령어 그대로 사용 가능
  - AWS ElastiCache, Google Memorystore가 Valkey로 전환 중
  - 커뮤니티 기여가 활발하고, Redis에 없는 기능도 추가되고 있음

이관 시 확인 사항:
  - 클라이언트 라이브러리 호환성: Lettuce, Jedis, Redisson 모두 Valkey 지원
  - Redis Modules 사용 여부: RedisJSON, RediSearch 등은 Redis Ltd 소유이므로 Valkey에서 직접 사용 불가
    → 대체: RedisJSON → ReJSON 포크, RediSearch → 별도 검색엔진 고려
  - 설정 파일은 redis.conf → valkey.conf로 이름만 바뀌고 내용은 동일
```

```bash
# Valkey 설치 (소스 빌드)
git clone https://github.com/valkey-io/valkey.git
cd valkey
make
make install

# 실행 — Redis와 동일한 인터페이스
valkey-server /etc/valkey/valkey.conf
valkey-cli ping    # → PONG

# 기존 Spring Boot 설정에서 호스트만 변경하면 된다
# Lettuce/Jedis 클라이언트가 프로토콜 레벨에서 호환
```

자사 서비스에 Redis를 내장하여 사용하는 경우라면 라이선스 문제가 없으므로 당장 Valkey로 전환할 필요는 없다. 하지만 클라우드 매니지드 서비스를 사용하고 있다면 해당 벤더의 Valkey 전환 일정을 확인해야 한다.

## 11. 운영 시 주의사항

### 설정

`maxmemory`는 물리 메모리의 60~70%로 설정한다. 나머지는 포크 오버헤드, 출력 버퍼, 복제 백로그 등이 사용한다. `maxmemory-policy`는 용도에 맞게 선택해야 하며, 캐시 용도라면 `allkeys-lru`가 무난하다. 영속성은 RDB + AOF 하이브리드(`aof-use-rdb-preamble yes`)가 복구 속도와 내구성 모두 잡을 수 있다. `KEYS`, `FLUSHALL` 같은 위험 명령어는 `rename-command`로 비활성화한다.

### 보안

`requirepass` 대신 ACL로 사용자별 권한을 분리하고, `bind`로 접근 가능한 인터페이스를 제한한다. `protected-mode yes`는 기본값이지만, bind와 requirepass 없이 외부에서 접근하면 차단되는 설정이다. 프로덕션에서는 TLS 암호화를 적용해야 하며, Redis 6.0+에서 네이티브 TLS를 지원한다.

### 모니터링

`INFO` 명령으로 메모리 사용량, 커넥션 수, 초당 명령 처리량, 복제 지연 등을 주기적으로 수집한다. Slow Log는 `slowlog-log-slower-than 10000`(10ms)으로 설정하고 주기적으로 확인한다. `mem_fragmentation_ratio`가 1.5를 넘거나 1.0 미만이면 즉시 대응이 필요하다. 복제 지연(`master_repl_offset` - `slave_repl_offset`)이 크면 네트워크나 Replica 부하를 점검한다.

### 고가용성

Sentinel 또는 Cluster를 구성하고, 자동 페일오버가 정상 동작하는지 주기적으로 테스트한다. 백업 스케줄을 설정하되 Replica에서 RDB를 저장하는 것이 Master 부하를 줄인다. 장애 대응 시 확인할 항목과 복구 절차를 미리 정리해 두어야 한다.

## 참고

- [Redis 공식 문서](https://redis.io/docs/)
- [Redis Cluster 튜토리얼](https://redis.io/docs/management/scaling/)
- [Redisson](https://github.com/redisson/redisson) — Java Redis 클라이언트
- [Redis 다루기](Redis%20다루기.md) — Redis 기본 사용법
- [Redis 개요](Redis.md) — Redis 데이터 타입과 아키텍처
- [Caching 전략](../../../Backend/Caching/Caching_Strategies.md) — 캐싱 패턴
- [분산 트랜잭션](../../../Application%20Architecture/MSA/Saga_패턴_및_분산_트랜잭션.md) — 분산 시스템 패턴
