---
title: TPS와 RPS
tags:
  - Backend
  - Performance
  - TPS
  - RPS
  - Database
  - Capacity_Planning
updated: 2026-05-21
---

# TPS (Transactions Per Second)와 RPS의 관계

서비스 성능 회의에서 "TPS 3000 받아야 합니다"라는 요건이 떨어졌을 때, 그게 무슨 뜻인지 정확히 잡지 못하면 캐파 산정이 통째로 어긋난다. RPS만 다뤄본 사람은 TPS도 비슷한 줄 알고 같은 방식으로 계산하다가, DB가 먼저 무너지는 상황을 겪는다. 이 문서는 TPS가 RPS와 어떻게 다른지, 측정은 어떻게 하는지, 어디서 병목이 생기고 어떻게 산정해야 하는지 정리한다. RPS 자체에 대한 설명은 [RPS](RPS.md) 문서를 따로 본다.

## TPS의 진짜 의미

TPS는 단순히 "초당 트랜잭션 수"인데, 문제는 "트랜잭션"이 문맥마다 다르다는 점이다.

- DB TPS: `BEGIN`부터 `COMMIT`/`ROLLBACK`까지 한 번 끝난 횟수
- 결제 시스템 TPS: 결제 요청 한 건이 승인 또는 거절로 종결된 횟수
- 메시지 큐 TPS: 메시지 한 건이 produce 또는 consume된 횟수
- 비즈니스 TPS: "주문 한 건", "송금 한 건" 같은 도메인 단위 완료 수

같은 시스템에서도 어느 층에서 보느냐에 따라 숫자가 다르다. 사용자가 "송금" 한 번 누른 게 비즈니스 TPS 1인데, 그 안에서 DB 트랜잭션은 출금 계좌 차변, 입금 계좌 대변, 거래 로그 저장, 한도 차감 같은 식으로 4~5개가 발생한다. 그러면 DB TPS는 4~5다. 어느 숫자를 보고 캐파를 잡느냐가 완전히 다르다.

요건을 받을 때 "트랜잭션 한 건의 정의가 뭐냐"부터 짚어야 한다. 그러지 않으면 4배짜리 서버를 잡거나, 4배 부족한 서버를 잡는다.

### RPS와 TPS가 1:1이 아닌 이유

HTTP 요청 한 번에 DB 트랜잭션이 몇 개 발생하는지가 핵심이다.

가장 단순한 GET 요청은 트랜잭션이 0개일 수도 있다. 캐시에서 응답하면 DB를 안 친다. 그러면 RPS는 잡히는데 TPS는 0이다.

조회 API라도 SELECT 한 방이면 트랜잭션 1개. 다만 READ ONLY 트랜잭션은 일반적으로 TPS 카운팅에서 분리해서 본다. 쓰기 트랜잭션과는 비용이 완전히 다르기 때문이다.

쓰기 API는 더 복잡하다. 예시로 주문 생성 API를 보면 다음 흐름이 흔하다.

```
POST /orders
  ├─ BEGIN
  ├─  재고 차감 UPDATE
  ├─  주문 INSERT
  ├─  주문 아이템 INSERT (n건)
  ├─  포인트 사용 UPDATE
  └─ COMMIT
```

여기서 HTTP 요청은 1번, DB 트랜잭션은 1번이다. 그래서 RPS:TPS = 1:1.

그런데 이런 API도 있다.

```
POST /transfer
  ├─ [출금 DB] BEGIN ~ COMMIT (계좌 차변)
  ├─ [입금 DB] BEGIN ~ COMMIT (계좌 대변)
  └─ [로그 DB] BEGIN ~ COMMIT (감사 로그)
```

은행 송금처럼 데이터 소스가 분리되어 있고 트랜잭션을 묶어서 처리하면 RPS 1당 DB TPS 3이다. 이걸 모르고 RPS만 기준으로 DB 용량을 잡으면 DB가 3배 빨리 한계에 닿는다.

반대 케이스도 있다. 배치성 요청은 RPS 1에 트랜잭션 N개가 들어간다.

```
POST /bulk-import
  ├─ BEGIN
  ├─  10000 rows INSERT
  └─ COMMIT
```

RPS는 1인데 한 트랜잭션이 1만 row를 처리한다. 이 경우 TPS 카운트는 1이지만 DB가 받는 실제 부하는 일반 트랜잭션 1만 배다. TPS만 보면 한가해 보이는데 IOPS, lock, WAL은 폭발한다. 그래서 TPS는 단독 지표로는 거짓말을 한다. 트랜잭션 크기 분포를 같이 봐야 한다.

### 변환 공식

실무에서 캐파 산정할 때 쓰는 식.

```
DB TPS = RPS × (요청당 평균 쓰기 트랜잭션 수)
DB QPS = RPS × (요청당 평균 쿼리 수)
```

쇼핑몰 주문 API 예시:

| 항목 | 값 |
|---|---|
| 목표 RPS | 1000 |
| 요청당 평균 쓰기 트랜잭션 | 2 (주문 생성, 재고 차감) |
| 요청당 평균 SELECT | 5 (상품, 사용자, 쿠폰, 배송지, 결제수단) |
| 결과 TPS | 2000 |
| 결과 QPS | 7000 (5 + 트랜잭션 내부 쿼리 2) |

RPS 1000짜리 서비스인데 DB는 TPS 2000과 QPS 7000을 받아야 한다. DB 인스턴스 스펙을 RPS 기준으로 잡으면 모자란다.

## TPS의 라이프사이클과 자원 점유

RPS는 요청-응답이 짧은 사이클로 끝난다고 가정해도 큰 무리가 없다. 그런데 TPS는 트랜잭션이 열려 있는 동안 자원이 계속 잡혀 있다는 점에서 다르다.

```
BEGIN
   ↓                  ← 여기서부터 자원 점유 시작
   ├─ UPDATE          ← row lock 획득
   ├─ 외부 API 호출   ← 트랜잭션 안에서 네트워크 대기 (안티패턴)
   ├─ INSERT          ← WAL 버퍼 점유
   ↓
COMMIT                ← fsync 발생, lock 해제
```

트랜잭션 한 건이 100ms 동안 열려 있다면, 그 100ms 동안 DB 커넥션 1개, 잠긴 row, undo segment, WAL 버퍼가 점유된다. Little's Law를 DB에 그대로 적용하면 동시 열린 트랜잭션 수 = TPS × 평균 트랜잭션 시간이다.

TPS 1000에 평균 트랜잭션 시간 50ms면 동시 열린 트랜잭션이 50개. 이게 PostgreSQL `max_connections`, MySQL `innodb_thread_concurrency` 같은 값과 직결된다. RPS와 동일한 식이지만 평균 시간 단위가 응답시간이 아니라 "트랜잭션 길이"라는 점이 다르다. 트랜잭션 안에서 외부 API를 부르는 코드가 있으면 트랜잭션 길이가 수백 ms로 늘어나서 동시성이 폭증한다.

이 부분을 놓치면 TPS 자체는 그대로인데 DB가 connection 거절을 시작하는 상황이 생긴다.

### 트랜잭션 안에서 절대 하지 말아야 하는 것

운영 중 자주 봤던 안티패턴.

- HTTP 호출 (외부 결제 PG 호출 같은 것)
- 큰 파일 I/O
- 슬립이나 백오프
- Redis 호출인데 timeout이 긴 경우

이런 코드가 한 줄 들어가면 평소 50ms짜리 트랜잭션이 1초로 늘어난다. TPS는 그대로 1000이어도 동시 열린 트랜잭션이 1000개로 뛴다. DB 커넥션 풀과 max_connections를 그만큼 잡고 있을 자신이 없으면 트랜잭션 밖으로 빼야 한다.

## 측정 도구별 명령

### pgbench (PostgreSQL)

PostgreSQL 기본 내장. 표준 TPC-B 벤치마크 시나리오를 돌린다.

```bash
# 초기 데이터 세팅 (scale 100 = 1000만 row 정도)
pgbench -i -s 100 -h db.example.com -U postgres bench

# 측정: 동시 50 클라이언트, 4 스레드, 60초
pgbench -h db.example.com -U postgres \
        -c 50 -j 4 -T 60 \
        -P 5 bench
```

결과는 이런 식으로 나온다.

```
number of transactions actually processed: 184523
latency average = 16.252 ms
tps = 3075.42 (without initial connection time)
tps = 3074.81 (including initial connection time)
```

`-c`(동시 클라이언트)와 `-j`(스레드)를 늘려가면서 TPS 곡선이 꺾이는 지점을 찾는 게 일반적인 측정 방법이다.

기본 TPC-B 시나리오 말고 자체 쿼리로 측정하려면 `.sql` 파일을 따로 만들어서 `-f` 옵션으로 넘긴다.

```sql
-- custom.sql
\set aid random(1, 100000)
\set delta random(-5000, 5000)
BEGIN;
UPDATE accounts SET balance = balance + :delta WHERE aid = :aid;
INSERT INTO history (aid, delta, mtime) VALUES (:aid, :delta, now());
END;
```

```bash
pgbench -h db.example.com -U postgres -c 50 -j 4 -T 60 -f custom.sql bench
```

### sysbench (MySQL/PostgreSQL OLTP)

DB 종류 가리지 않고 OLTP 워크로드 측정에 많이 쓴다.

```bash
# 데이터 준비
sysbench oltp_read_write \
  --db-driver=mysql \
  --mysql-host=db.example.com \
  --mysql-user=root --mysql-password=*** \
  --mysql-db=bench \
  --tables=10 --table-size=1000000 \
  prepare

# 실행
sysbench oltp_read_write \
  --db-driver=mysql --mysql-host=db.example.com \
  --mysql-user=root --mysql-password=*** \
  --mysql-db=bench \
  --tables=10 --table-size=1000000 \
  --threads=64 --time=120 --report-interval=10 \
  run
```

`oltp_read_write`는 SELECT/UPDATE/INSERT/DELETE가 섞인 표준 워크로드. 읽기만 측정하려면 `oltp_read_only`, 쓰기만 보려면 `oltp_write_only`로 바꾼다.

리포트에 `transactions per sec`와 `queries per sec`이 따로 찍힌다. 이 둘의 비율을 보면 트랜잭션당 평균 쿼리 수가 나온다.

```
SQL statistics:
    queries performed:
        read:                            1740250
        write:                           497214
        other:                           248607
        total:                           2486071
    transactions:                        124303  (1035.81 per sec.)
    queries:                             2486071 (20716.30 per sec.)
```

여기서 TPS 1035, QPS 20716. 트랜잭션당 쿼리 20개꼴. 실서비스에서 이 비율이 너무 높으면 N+1 쿼리 의심.

### JMeter로 비즈니스 TPS 측정

DB가 아니라 "송금 1건 완료" 같은 비즈니스 트랜잭션 TPS를 측정할 때.

JMeter는 Thread Group으로 가상 사용자를 잡고, Transaction Controller로 여러 요청을 묶어서 한 트랜잭션으로 본다.

```
Thread Group (200 users, ramp-up 30s, loop forever)
  └─ Transaction Controller: "Send Money Transaction"
       ├─ HTTP Request: POST /auth/login
       ├─ HTTP Request: POST /transfer/init
       ├─ HTTP Request: POST /transfer/verify
       └─ HTTP Request: POST /transfer/confirm
```

JMeter 결과에서 `Transactions/sec`가 비즈니스 TPS. 하나의 트랜잭션 안에서 HTTP 요청은 4번 발생하므로 RPS는 TPS의 4배가 된다. 이 비율을 모르고 RPS만으로 사이즈 잡으면 서버 부족.

명령행으로 돌릴 때:

```bash
jmeter -n -t transfer-scenario.jmx \
       -l results.jtl \
       -e -o report/ \
       -Jthreads=200 -Jrampup=30 -Jduration=300
```

## TPS가 안 오르는 전형적 병목

TPS 측정하다 보면 부하 늘려도 어느 선부터 TPS가 안 늘고 latency만 치솟는다. 원인 패턴은 RPS와 비슷해 보이지만 DB 쪽 특유의 항목이 더 있다.

### Disk IOPS와 fsync

가장 흔한 병목. 쓰기 트랜잭션은 COMMIT 시점에 WAL/redo log를 disk에 fsync한다. 이게 disk IOPS 한계에 묶인다.

- 일반 SATA SSD: 수만 IOPS
- NVMe: 수십~수백만 IOPS
- 클라우드 gp3 (기본): 3000 IOPS, 옵션으로 16000까지
- 클라우드 io2: 64000 IOPS 이상도 가능

PostgreSQL의 경우 트랜잭션마다 fsync가 발생하므로 TPS 상한이 IOPS / (트랜잭션당 fsync 횟수)다. AWS gp3 기본(3000 IOPS) DB에서 단일 쓰기 트랜잭션 TPS가 2500~3000에서 안 올라가는 건 거의 이 원인.

확인 방법:

```bash
# 디스크 사용량과 await 시간
iostat -xz 1

# await가 ms 단위로 치솟고 %util이 100% 근처면 디스크 병목
```

PostgreSQL에서 `synchronous_commit = off`로 바꾸면 fsync를 묶어서 처리해서 TPS는 올라가지만 장애 시 마지막 몇 ms의 데이터 유실 위험이 생긴다. 결제, 금융 같은 도메인에선 못 쓰고, 로그성 데이터 정도에만 적용한다.

### WAL 버퍼와 그룹 커밋

WAL은 메모리에 먼저 쓰고 주기적으로 disk로 내려쓴다. WAL 버퍼가 작으면 트랜잭션이 자주 flush를 기다린다.

PostgreSQL `wal_buffers`, MySQL `innodb_log_buffer_size`를 너무 작게 두면 TPS가 안 오르고 wait event에 WAL 관련 이벤트가 쌓인다.

```sql
-- PostgreSQL: 현재 대기 중인 wait event 확인
SELECT wait_event_type, wait_event, count(*)
FROM pg_stat_activity
WHERE state = 'active'
GROUP BY wait_event_type, wait_event
ORDER BY count(*) DESC;
```

`WALWriteLock`, `WALSync` 같은 게 상위에 보이면 WAL 쪽 병목.

### Lock wait

Row lock이 길게 잡히면 후속 트랜잭션이 대기한다. TPS가 안 오르는데 CPU도 디스크도 한가하면 대부분 lock 문제.

```sql
-- PostgreSQL: blocking 관계 확인
SELECT
  blocked.pid AS blocked_pid,
  blocked.query AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));
```

전형적인 lock 병목 케이스.

- 인기 상품 재고 row를 모두가 UPDATE → 그 row에 직렬화
- `SELECT ... FOR UPDATE` 범위가 너무 큼
- 인덱스가 없어서 row lock이 아닌 사실상 테이블 락처럼 동작
- 트랜잭션이 길어서 lock 점유 시간이 길어짐

해결 방법은 케이스마다 다른데 대표적인 것만 추리면, 재고 row를 N개로 분산(샤딩) 시키거나, 낙관적 락(version 컬럼)으로 바꾸거나, 트랜잭션을 잘게 쪼개거나, Redis 같은 외부 카운터로 빼는 식이다.

### Replication lag

읽기 부하를 read replica로 분산할 때 replication lag이 TPS에 묶인다. primary TPS가 너무 높으면 replica가 못 따라가서 lag이 늘어난다.

```sql
-- PostgreSQL: replica에서 lag 확인
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

lag이 일정 임계치를 넘으면 애플리케이션이 replica 사용을 멈추고 primary로 fallback해야 한다. 이때 primary 부하가 갑자기 늘어서 TPS가 무너지는 연쇄 장애가 흔하다. read-after-write 일관성이 필요한 트랜잭션은 항상 primary로 보내야 한다는 것도 같은 맥락.

### Connection 한계

DB max_connections를 다 써도 TPS는 안 오른다. 커넥션이 더 늘어나봤자 CPU/IOPS가 같으면 처리량은 같고 컨텍스트 스위칭만 늘어난다.

PostgreSQL의 경우 connection 1개당 메모리도 추가로 잡아먹기 때문에 (`work_mem`, `temp_buffers`) connection을 무한정 늘리는 게 답이 아니다. pgbouncer 같은 connection pooler를 앞에 두고 백엔드 연결 수는 CPU 코어 수의 2~4배 정도로 제한하는 게 일반적이다.

## 트랜잭션 격리 수준이 TPS에 미치는 영향

격리 수준은 데이터 정합성 보장 강도이자 동시성 비용이다. 격리 수준이 높을수록 lock이나 MVCC 비용이 커져서 TPS가 떨어진다.

| 격리 수준 | 비용 | TPS 영향 | 주 사용처 |
|---|---|---|---|
| READ UNCOMMITTED | 최소 | 가장 높음 | 거의 안 씀 |
| READ COMMITTED | 낮음 | 높음 | 일반 OLTP 기본값 (PostgreSQL 기본) |
| REPEATABLE READ | 중간 | 중간 | MySQL InnoDB 기본 |
| SERIALIZABLE | 높음 | 낮음 | 금융 정합성 중요 케이스 |

PostgreSQL의 SERIALIZABLE은 SSI(Serializable Snapshot Isolation)로 구현되어 lock보다는 충돌 감지 후 retry 방식이다. 충돌이 잦으면 retry가 늘어서 TPS가 크게 떨어진다. 부하가 높을수록 `could not serialize access due to read/write dependencies` 에러가 자주 뜨고, 애플리케이션이 retry 로직을 구현해야 한다.

MySQL InnoDB의 REPEATABLE READ는 next-key lock으로 phantom read를 막는데, 이게 의도치 않게 더 넓은 range를 잠그는 부작용이 있다. 인덱스가 약하면 사실상 큰 범위가 잠겨서 동시성이 망가진다.

실무에서는 대부분 READ COMMITTED로 운영하고, 정합성이 중요한 일부 트랜잭션만 SERIALIZABLE이나 명시적 lock(`SELECT ... FOR UPDATE`)으로 격상하는 방식을 쓴다. 전체를 SERIALIZABLE로 두면 TPS가 30~70%까지 떨어지는 경우도 있다.

격리 수준을 바꿀 때는 측정으로 확인해야 한다. pgbench로 같은 시나리오를 격리 수준 바꿔가며 돌려보면 차이가 바로 보인다.

```sql
-- 세션 격리 수준 변경
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

## 메시지 큐의 TPS는 의미가 다르다

Kafka, RabbitMQ 같은 MQ에서 TPS라는 단어를 쓰면 DB TPS와는 의미가 다르다. 메시지 한 건의 produce/consume이 한 트랜잭션 단위다.

### Kafka

Kafka의 "트랜잭션"은 두 가지가 섞여서 쓰인다.

1. **단순 메시지 처리량**: produce/consume된 메시지 수. 이게 일반적으로 말하는 Kafka TPS. 단일 broker에서 수십만 msg/s도 가능.
2. **Kafka Transaction (Exactly Once Semantics)**: producer가 여러 파티션에 atomically write할 때 쓰는 진짜 트랜잭션. `initTransactions()`, `beginTransaction()`, `commitTransaction()`. 이건 훨씬 비싸고 단일 broker TPS가 수천~수만 수준으로 떨어진다.

Kafka에서 TPS 요건을 받으면 EOS인지 아닌지를 먼저 확인해야 한다. 일반 produce TPS 50만 받을 수 있는 broker가 EOS transaction TPS는 5천도 못 받을 수 있다.

```bash
# Kafka producer 성능 측정
kafka-producer-perf-test.sh \
  --topic test-topic \
  --num-records 1000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props bootstrap.servers=kafka:9092 acks=all

# acks=all, replication=3 조합에서 throughput 측정. 
# acks=1로 바꾸면 TPS 2~3배 차이남
```

`acks=all`은 모든 ISR replica가 확인할 때까지 기다린다. `acks=1`은 leader만 확인. 정합성과 TPS의 트레이드오프가 여기서 발생한다.

### RabbitMQ

RabbitMQ에서 "transactional channel"을 켜면 모든 publish가 트랜잭션 단위로 묶인다. AMQP transaction은 publisher confirm보다 훨씬 느려서 TPS가 수십 분의 1 수준으로 떨어진다.

```python
# 이건 느림 (transactional)
channel.tx_select()
channel.basic_publish(...)
channel.tx_commit()

# 이건 빠름 (publisher confirm)
channel.confirm_delivery()
channel.basic_publish(...)
```

운영에서 RabbitMQ TPS 요건을 받으면 거의 publisher confirm 기준으로 본다. transactional channel은 진짜 atomic이 필요한 일부 경로에만 쓴다.

### MQ TPS와 DB TPS의 관계

MQ를 앞에 두는 시스템에서 RPS, MQ TPS, DB TPS 셋이 따로 움직인다.

```
클라이언트 → API 서버 → Kafka → Consumer → DB
          RPS         MQ TPS    DB TPS
```

API 서버가 받는 RPS와 Kafka에 produce되는 메시지 TPS는 거의 같지만, consumer가 메시지 1개당 DB에 쓰는 트랜잭션 수에 따라 DB TPS가 다르다. 또 consumer가 batch로 묶어서 처리하면 DB TPS는 MQ TPS보다 훨씬 낮을 수 있다.

이게 캐파 산정의 함정인데, MQ 도입한 시스템에서 "RPS 5000 받아야 한다" 했을 때 DB TPS도 5000일 거라고 가정하면 안 된다. consumer 동작에 따라 1배일 수도, 5배일 수도, 0.1배일 수도 있다.

## 분산 트랜잭션과 Saga의 TPS 산정

마이크로서비스에서 여러 서비스에 걸친 트랜잭션을 처리하는 방식은 크게 두 가지.

### 2PC (XA Transaction)

리소스 매니저 여러 개를 한 트랜잭션 코디네이터가 묶는다. prepare-commit 두 단계. 한 번의 비즈니스 트랜잭션을 위해 모든 참여자에 prepare, commit 두 번씩 메시지가 오간다.

부하 산정할 때 비즈니스 TPS 1을 위해 각 DB에는 트랜잭션 1개씩, 추가로 코디네이터-참여자 간 네트워크 RTT가 2번 더 든다. 비즈니스 TPS 1000을 받으려면 각 참여 DB가 1000 TPS, 코디네이터는 4000건 이상의 메시지 처리. 게다가 prepare 후 commit까지 lock이 잡혀 있어서 트랜잭션 길이가 평소의 2~5배.

운영에서 2PC TPS가 비분산 TPS의 1/5 정도로 떨어지는 건 흔하다. 그래서 2PC를 쓰는 시스템에서 캐파 산정은 보수적으로 잡아야 한다.

### Saga

Saga는 보상 트랜잭션을 통한 결과적 일관성. 각 단계는 독립 로컬 트랜잭션이고, 실패하면 역방향 보상.

```
주문 Saga:
  Step1: 주문 생성 (Order DB TPS +1)
  Step2: 재고 차감 (Inventory DB TPS +1)
  Step3: 결제 (Payment DB TPS +1)
  Step4: 배송 요청 (Shipping DB TPS +1)
```

비즈니스 TPS 1당 각 서비스 DB TPS 1. 실패하면 보상 트랜잭션이 추가로 발생하므로 TPS 산정할 때 실패율을 곱해야 한다.

```
서비스별 DB TPS = 비즈니스 TPS × (1 + 보상 발생률)
```

평균 실패율이 5%면 각 서비스 DB는 비즈니스 TPS의 1.05배 정도 받는다. 그런데 결제 실패율이 갑자기 30%로 튀면 보상 트랜잭션이 30% 더 발생해서 후속 서비스 DB의 부하가 비대칭적으로 늘어난다.

Saga 시스템 캐파 산정의 함정은 정상 상태 TPS만 계산하고 실패 시 보상 폭증을 안 잡는 것. 실패율이 평소의 5배로 치솟는 장애 상황에서 보상 트랜잭션 처리로 시스템 전체가 더 막히는 경우가 있다. 헤드룸을 평소보다 더 둬야 한다.

## TPS와 RPS를 함께 모니터링하기

대시보드에는 RPS, TPS, QPS를 같은 보드에 띄워놓는 게 좋다. 셋의 비율이 평소와 달라지면 어딘가 변화가 생긴 거다.

### Prometheus 메트릭 예시

```promql
# 애플리케이션 RPS
rate(http_requests_total[1m])

# DB 트랜잭션 TPS (PostgreSQL exporter)
rate(pg_stat_database_xact_commit{datname="prod"}[1m])
  + rate(pg_stat_database_xact_rollback{datname="prod"}[1m])

# DB 쿼리 QPS
rate(pg_stat_database_tup_fetched{datname="prod"}[1m])
  + rate(pg_stat_database_tup_returned{datname="prod"}[1m])

# 요청당 트랜잭션 비율
(rate(pg_stat_database_xact_commit{datname="prod"}[1m]))
  / rate(http_requests_total[1m])
```

마지막 비율 메트릭이 핵심이다. 정상 상태에서 이 비율이 2 정도였는데 갑자기 5로 튀면, 누군가 코드를 잘못 짜서 트랜잭션이 N+1 형태로 쪼개졌거나, 의도치 않은 retry 루프가 도는 신호다. 절대값보다 비율 변화가 빠른 이상 감지를 가능하게 한다.

### 대시보드 구성 패턴

한 화면에 같이 띄워야 의미가 있는 메트릭 묶음.

- 좌상: RPS (1분 평균, 1분 p99 burst)
- 우상: DB TPS (commit + rollback 분리)
- 좌하: RPS:TPS 비율, RPS:QPS 비율
- 우하: 트랜잭션 평균 길이, lock wait time

이렇게 같이 보면 "RPS는 그대로인데 TPS는 늘었다" → 트랜잭션 분할 의심, "RPS와 TPS는 그대로인데 lock wait이 올라간다" → 락 컨텐션 의심 같은 식으로 이상 패턴을 빠르게 잡을 수 있다.

### Alert 기준

TPS 단독으로는 알람 걸기 애매한 경우가 많다. 대신 비율을 알람으로 거는 게 효과적이다.

```promql
# 평소 트랜잭션당 평균 길이가 50ms인데 200ms 넘으면 알람
(rate(pg_stat_database_xact_commit{datname="prod"}[1m]) > 0)
  and 
(rate(pg_xact_total_time[1m]) / rate(pg_stat_database_xact_commit[1m]) > 0.2)

# RPS:TPS 비율이 평소의 2배 이상 벌어지면 알람
abs(
  (rate(pg_stat_database_xact_commit[1m]) / rate(http_requests_total[1m]))
  - 
  (rate(pg_stat_database_xact_commit[1h] offset 1d) / rate(http_requests_total[1h] offset 1d))
) > 1
```

두 번째 식은 어제 같은 시간대와 비교해서 비율이 1 이상 벌어지면 알람. 코드 배포 후 의도치 않은 트랜잭션 패턴 변화 잡는 데 유용하다.

## 캐파 산정에서 TPS와 RPS의 다른 점

같은 시스템이라도 RPS 기준 캐파와 TPS 기준 캐파를 따로 잡아야 한다는 게 핵심이다.

서비스 레이어는 RPS 기준으로 잡는다. 응답시간이 짧고 stateless에 가깝다. Little's Law로 동시성 산정하고 헤드룸 30~50%.

DB 레이어는 TPS 기준으로 잡는다. 트랜잭션이 열려 있는 동안 자원 점유가 일어나므로, 트랜잭션 평균 길이까지 같이 봐야 한다. 또 쓰기 TPS와 읽기 QPS를 분리해서 본다. 쓰기는 IOPS와 WAL에 묶이고 읽기는 buffer cache, replica 분산으로 처리량이 다르다.

여유율도 다르게 잡는다. 서비스 서버는 무상태라 빠르게 늘릴 수 있어서 30~50% 헤드룸이면 충분하지만, DB는 vertical scaling이 보통이고 페일오버 시간도 길어서 50~100% 헤드룸을 두는 경우도 많다. 또 replication, backup, vacuum/optimize 같은 작업이 평소에도 자원을 먹어서 실제 가용 TPS는 측정 최대치의 60~70% 정도로 보는 게 안전하다.

마지막으로, "TPS 5000"이라는 요건을 받았을 때 항상 다시 물어볼 질문 목록을 정리해두면 좋다.

- 트랜잭션 한 건의 정의 (DB 트랜잭션, 비즈니스 트랜잭션, MQ 메시지)
- 읽기/쓰기 비율
- 트랜잭션당 평균 쿼리 수
- 평균 트랜잭션 길이 (ms)
- 피크와 평균의 비율
- 어느 시점의 TPS (정상 운영, 피크, SLA 한계)
- 일관성 요구 수준 (격리 수준, EOS, 2PC 여부)

이 답들이 안 나오면 캐파 산정은 그냥 추측이다. 측정 전에 정의부터 합의하는 게 결국 시간을 아낀다.
