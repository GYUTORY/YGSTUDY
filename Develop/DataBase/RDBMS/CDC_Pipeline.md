---
title: CDC 파이프라인
tags: [database, cdc, debezium, kafka-connect, binlog, wal, change-data-capture]
updated: 2026-04-01
---

# CDC 파이프라인

## CDC란

Change Data Capture(CDC)는 데이터베이스의 변경 사항(INSERT, UPDATE, DELETE)을 실시간으로 감지해서 다른 시스템에 전달하는 방식이다. 배치로 전체 테이블을 긁어오는 게 아니라, 변경분만 캡처해서 보낸다.

```
기존 방식 (Batch ETL):
  매 시간 SELECT * FROM orders WHERE updated_at > ?
  → 누락 가능, DB 부하, 지연 큼

CDC 방식:
  DB의 트랜잭션 로그를 실시간으로 읽음
  → 변경 즉시 전달, DB 부하 적음, 누락 없음
```

CDC가 필요한 상황:

- OLTP DB의 데이터를 검색 엔진(Elasticsearch)이나 캐시(Redis)에 동기화할 때
- 마이크로서비스 간 데이터 동기화
- 데이터 웨어하우스로 실시간 적재
- 이벤트 소싱 패턴의 이벤트 발행

## Binlog vs WAL

CDC가 읽는 트랜잭션 로그는 DBMS마다 다르다.

### MySQL - Binlog

MySQL은 Binary Log(Binlog)에 모든 데이터 변경을 기록한다. Binlog의 포맷에 따라 CDC 동작이 달라진다.

| 포맷 | 설명 | CDC 적합성 |
|------|------|-----------|
| STATEMENT | 실행된 SQL 문 자체를 기록 | 부적합. `NOW()` 같은 비결정적 함수 결과가 달라질 수 있다 |
| ROW | 변경된 행 데이터를 기록 (before/after) | CDC에 적합. 정확한 변경 데이터를 추출 가능 |
| MIXED | 상황에 따라 STATEMENT/ROW 혼합 | 비추천. 예측이 어렵다 |

CDC용으로 반드시 ROW 포맷을 써야 한다.

```sql
-- Binlog 설정 확인
SHOW VARIABLES LIKE 'log_bin';          -- ON이어야 함
SHOW VARIABLES LIKE 'binlog_format';    -- ROW여야 함
SHOW VARIABLES LIKE 'binlog_row_image'; -- FULL 권장

-- my.cnf 설정
-- [mysqld]
-- server-id=1
-- log-bin=mysql-bin
-- binlog_format=ROW
-- binlog_row_image=FULL
-- expire_logs_days=3
```

`binlog_row_image`가 `MINIMAL`이면 변경된 컬럼만 기록되는데, CDC에서 before 이미지가 필요한 경우 문제가 된다. `FULL`로 설정하는 게 안전하다.

### PostgreSQL - WAL

PostgreSQL은 Write-Ahead Log(WAL)를 사용한다. CDC를 위해서는 논리적 복제(Logical Replication) 설정이 필요하다.

```
-- postgresql.conf
wal_level = logical           -- 기본값은 replica. logical로 변경 필요
max_replication_slots = 4     -- CDC 커넥터가 슬롯을 하나 사용
max_wal_senders = 4
```

PostgreSQL에서는 Logical Replication Slot을 사용해서 WAL의 변경 사항을 디코딩한다. 슬롯은 컨슈머가 어디까지 읽었는지 위치를 추적한다.

```sql
-- 논리적 복제 슬롯 생성
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput');

-- 현재 슬롯 상태 확인
SELECT slot_name, plugin, active, restart_lsn
FROM pg_replication_slots;
```

주의할 점이 있다. CDC 커넥터가 오랜 시간 멈추면 WAL이 계속 쌓인다. 슬롯이 WAL 삭제를 막기 때문이다. 디스크가 가득 차서 DB가 멈추는 사고가 실제로 발생한다. 모니터링 필수다.

```sql
-- WAL 쌓임 모니터링
SELECT slot_name,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag
FROM pg_replication_slots;

-- lag가 수 GB 이상이면 즉시 확인해야 한다
```

### 주요 차이 정리

| 항목 | MySQL Binlog | PostgreSQL WAL |
|------|-------------|----------------|
| 로그 유형 | Binary Log | Write-Ahead Log |
| CDC 디코딩 | Binlog 직접 파싱 | Logical Decoding Plugin |
| 위치 추적 | Binlog 파일명 + offset / GTID | LSN (Log Sequence Number) |
| 로그 보존 | `expire_logs_days` 설정 | Replication Slot이 보존 관리 |
| 주의 사항 | ROW 포맷 필수 | WAL 쌓임 모니터링 필수 |

## Debezium 기반 CDC 구성

Debezium은 가장 널리 쓰이는 오픈소스 CDC 플랫폼이다. Kafka Connect 위에서 동작하는 Source Connector로, DB의 변경 사항을 Kafka 토픽으로 전달한다.

### 아키텍처

```
[MySQL/PostgreSQL]
       │
       │ Binlog / WAL
       ▼
[Debezium Connector]  ← Kafka Connect Worker에서 실행
       │
       │ 변경 이벤트
       ▼
[Kafka Topic]         ← 테이블별로 토픽이 생성됨
       │
       ▼
[Consumer]            ← Elasticsearch, Data Warehouse, 다른 서비스 등
```

### Kafka Connect 설정

Debezium은 단독으로 실행하는 게 아니라 Kafka Connect 클러스터에 배포한다.

```json
// Kafka Connect Worker 설정 (connect-distributed.properties)
{
  "bootstrap.servers": "kafka:9092",
  "group.id": "connect-cluster",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "offset.storage.topic": "connect-offsets",
  "config.storage.topic": "connect-configs",
  "status.storage.topic": "connect-status"
}
```

### MySQL 커넥터 등록

```json
// POST /connectors
{
  "name": "mysql-connector",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "database.hostname": "mysql-host",
    "database.port": "3306",
    "database.user": "debezium",
    "database.password": "password",
    "database.server.id": "184054",
    "topic.prefix": "myapp",
    "database.include.list": "mydb",
    "table.include.list": "mydb.orders,mydb.users",
    "schema.history.internal.kafka.bootstrap.servers": "kafka:9092",
    "schema.history.internal.kafka.topic": "schema-changes.mydb",
    "snapshot.mode": "initial",
    "decimal.handling.mode": "string",
    "time.precision.mode": "connect"
  }
}
```

설정에서 자주 실수하는 부분:

- `database.server.id`: MySQL 클러스터 내에서 유일해야 한다. 다른 슬레이브와 겹치면 복제가 꼬인다
- `topic.prefix`: 토픽 이름의 접두사가 된다. `{prefix}.{database}.{table}` 형태로 토픽이 생성된다
- `snapshot.mode`: `initial`은 처음 시작할 때 기존 데이터를 전부 스냅샷으로 가져온다. 대형 테이블이면 시간이 오래 걸린다

### PostgreSQL 커넥터 등록

```json
{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres-host",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "password",
    "database.dbname": "mydb",
    "topic.prefix": "myapp",
    "table.include.list": "public.orders,public.users",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_slot",
    "publication.name": "dbz_publication",
    "snapshot.mode": "initial"
  }
}
```

PostgreSQL의 경우 `plugin.name`을 `pgoutput`으로 설정한다. 예전에는 `decoderbufs`나 `wal2json`을 많이 썼는데, PostgreSQL 10 이상에서는 내장된 `pgoutput`이 표준이다.

### Debezium 이벤트 구조

Debezium이 Kafka로 보내는 메시지는 다음과 같은 구조를 가진다.

```json
{
  "schema": { "..." },
  "payload": {
    "before": {
      "id": 1001,
      "status": "pending",
      "amount": 50000
    },
    "after": {
      "id": 1001,
      "status": "completed",
      "amount": 50000
    },
    "source": {
      "version": "2.5.0.Final",
      "connector": "mysql",
      "name": "myapp",
      "ts_ms": 1711929600000,
      "db": "mydb",
      "table": "orders",
      "server_id": 184054,
      "file": "mysql-bin.000003",
      "pos": 1234
    },
    "op": "u",
    "ts_ms": 1711929600123
  }
}
```

`op` 필드의 의미:

| 값 | 의미 |
|----|------|
| `c` | CREATE (INSERT) |
| `u` | UPDATE |
| `d` | DELETE |
| `r` | READ (스냅샷 시) |

`before`와 `after`를 비교하면 정확히 어떤 필드가 바뀌었는지 알 수 있다. DELETE의 경우 `after`가 `null`이다.

## 스키마 변경 대응

CDC 운영에서 가장 까다로운 부분이 스키마 변경이다. 테이블에 컬럼을 추가하거나 타입을 바꾸면 CDC 파이프라인 전체에 영향을 미친다.

### Debezium의 스키마 변경 처리

Debezium은 `schema.history.internal.kafka.topic`에 DDL 변경 이력을 기록한다. 커넥터가 재시작되면 이 토픽에서 스키마 히스토리를 복원한다.

```
스키마 변경 흐름:

1. ALTER TABLE orders ADD COLUMN discount INT DEFAULT 0;
2. Debezium이 Binlog에서 DDL 감지
3. 내부 스키마를 갱신
4. 이후 이벤트부터 discount 필드 포함
5. 컨슈머 측에서 새 필드를 처리할 준비가 되어야 함
```

### 안전하게 스키마를 변경하는 순서

스키마 변경은 컨슈머부터 먼저 대응해야 한다.

```
1단계: 컨슈머 수정
  - 새 필드가 없어도 동작하도록 (optional 처리)
  - 타입 변경 시 양쪽 타입 모두 처리 가능하도록
  배포 완료

2단계: DB 스키마 변경
  - ALTER TABLE 실행
  - Debezium이 자동으로 감지

3단계: 확인
  - 변경 후 이벤트가 정상적으로 전달되는지 모니터링
```

반대 순서로 하면 컨슈머가 알 수 없는 필드를 받고 에러가 난다. Jackson으로 역직렬화할 때 `FAIL_ON_UNKNOWN_PROPERTIES`가 `true`면 바로 터진다.

### 호환되지 않는 스키마 변경

컬럼 타입 변경이나 컬럼 삭제는 더 신경 써야 한다.

```
위험한 변경:
  - VARCHAR → INT 타입 변경
  - 컬럼 이름 변경 (RENAME COLUMN)
  - NOT NULL 컬럼 추가 (DEFAULT 없이)

안전한 변경:
  - 새 컬럼 추가 (DEFAULT 포함)
  - 컬럼 타입 확장 (INT → BIGINT, VARCHAR(50) → VARCHAR(200))
```

컬럼 이름을 바꿔야 하는 경우, 새 컬럼을 추가하고 양쪽에 값을 쓰다가 컨슈머가 전환된 후 옛 컬럼을 삭제하는 방식이 안전하다.

### Avro와 Schema Registry 사용

프로덕션에서는 JSON 대신 Avro + Schema Registry 조합을 쓰는 경우가 많다. 스키마 호환성을 자동으로 검증해준다.

```json
// 커넥터 설정에 Avro 변환기 적용
{
  "key.converter": "io.confluent.connect.avro.AvroConverter",
  "key.converter.schema.registry.url": "http://schema-registry:8081",
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "http://schema-registry:8081"
}
```

Schema Registry의 호환성 모드:

| 모드 | 허용 | 설명 |
|------|------|------|
| BACKWARD | 필드 삭제, 기본값 있는 필드 추가 | 새 스키마로 옛 데이터 읽기 가능 |
| FORWARD | 필드 추가, 기본값 있는 필드 삭제 | 옛 스키마로 새 데이터 읽기 가능 |
| FULL | 기본값 있는 필드 추가/삭제만 허용 | 양방향 호환 |

`BACKWARD` 호환이 기본이다. 호환되지 않는 스키마 변경을 시도하면 Schema Registry가 거부하기 때문에, 실수로 파이프라인을 깨트리는 걸 방지할 수 있다.

## CDC 파이프라인 장애 대처

### 커넥터 상태 모니터링

```bash
# 커넥터 상태 확인
curl -s http://connect:8083/connectors/mysql-connector/status | jq

# 정상이면
# "state": "RUNNING"
# 문제가 있으면
# "state": "FAILED" + "trace" 필드에 에러 스택
```

```bash
# 커넥터 재시작
curl -X POST http://connect:8083/connectors/mysql-connector/restart

# 특정 Task만 재시작
curl -X POST http://connect:8083/connectors/mysql-connector/tasks/0/restart
```

### 자주 발생하는 장애와 대처

**1. Binlog가 만료되어 사라진 경우**

MySQL의 `expire_logs_days` 설정에 의해 오래된 Binlog가 삭제된다. 커넥터가 오래 멈춰 있다가 재시작하면 읽어야 할 Binlog가 이미 없는 상황이 생긴다.

```
에러: The connector is trying to read binlog starting at
      binlog file 'mysql-bin.000001', but the earliest available
      binlog file is 'mysql-bin.000005'
```

해결 방법:

```bash
# 1. 커넥터 삭제
curl -X DELETE http://connect:8083/connectors/mysql-connector

# 2. Kafka의 offset 토픽에서 해당 커넥터의 offset 삭제
# 3. 커넥터를 snapshot.mode=initial로 재등록
#    → 전체 스냅샷을 다시 찍고 현재 Binlog 위치부터 CDC 재개
```

전체 스냅샷은 테이블이 크면 수 시간 걸릴 수 있다. `snapshot.mode=when_needed`로 설정하면 Debezium이 offset을 찾을 수 없을 때 자동으로 스냅샷을 다시 수행한다.

**2. PostgreSQL WAL 디스크 풀**

Replication Slot이 WAL 소비를 멈추면 디스크가 찬다.

```sql
-- 비활성 슬롯 확인
SELECT slot_name, active, pg_size_pretty(
  pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
) AS lag
FROM pg_replication_slots
WHERE NOT active;

-- 긴급 시 슬롯 삭제 (CDC 데이터 유실 감수)
SELECT pg_drop_replication_slot('debezium_slot');
```

슬롯을 삭제하면 CDC가 끊기므로, 커넥터를 스냅샷 모드로 재설정해야 한다. 이런 사고를 예방하려면 WAL 사이즈에 대한 알림을 설정해야 한다.

```yaml
# Prometheus 알림 규칙 예시
- alert: PostgreSQLReplicationSlotLag
  expr: pg_replication_slot_lag_bytes > 1073741824  # 1GB
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Replication slot lag이 1GB를 초과했다"
```

**3. 커넥터 OOM (Out of Memory)**

대형 트랜잭션이 발생하면 Debezium이 메모리를 많이 사용한다. 한 트랜잭션에서 수백만 행을 변경하면 커넥터가 OOM으로 죽는다.

```properties
# Kafka Connect Worker의 JVM 힙 설정
KAFKA_HEAP_OPTS=-Xms1G -Xmx4G
```

근본적인 해결은 대량 변경을 배치로 나누는 것이다.

```sql
-- 한 번에 100만 행 UPDATE하지 말고
-- UPDATE orders SET status = 'archived' WHERE created_at < '2025-01-01';

-- 배치로 나눈다
UPDATE orders SET status = 'archived'
WHERE created_at < '2025-01-01'
  AND status != 'archived'
LIMIT 10000;
-- 이걸 반복
```

**4. 컨슈머 처리 지연 (Consumer Lag)**

Kafka 토픽에 이벤트가 쌓이고 컨슈머가 따라가지 못하는 상황이다.

```bash
# Consumer Lag 확인
kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --group my-consumer-group \
  --describe

# LAG 값이 계속 증가하면 문제
```

대응 방법:

- 컨슈머 인스턴스 수를 늘린다 (파티션 수 이하까지)
- 컨슈머의 처리 로직에서 병목을 찾는다 (보통 외부 API 호출이나 DB 쓰기)
- 배치 처리를 도입한다 (한 건씩이 아니라 묶어서 처리)

### 운영 시 필수 모니터링 항목

| 항목 | 확인 대상 | 임계값 기준 |
|------|----------|-----------|
| 커넥터 상태 | Kafka Connect REST API | RUNNING이 아닌 상태 |
| Binlog/WAL Lag | source 정보의 ts_ms와 현재 시간 차이 | 수 분 이상 지연 시 |
| Consumer Lag | Kafka Consumer Group의 LAG | 계속 증가하는 추세 |
| WAL 디스크 사용량 | pg_replication_slots의 lag | 1GB 초과 |
| 커넥터 JVM 메모리 | JMX 메트릭 | 힙 사용률 80% 초과 |

## 정리

CDC 파이프라인은 설정 자체보다 운영이 어렵다. 처음 구축할 때는 Debezium + Kafka Connect 조합이 간단해 보이지만, 프로덕션에서 스키마 변경, Binlog 만료, WAL 쌓임 같은 문제를 만나면 상당히 까다롭다.

핵심은 세 가지다:

1. DB별 로그 설정을 정확히 해야 한다. MySQL은 ROW 포맷, PostgreSQL은 `wal_level=logical`
2. 스키마 변경은 반드시 컨슈머 먼저 대응하고, 가능하면 Schema Registry로 호환성을 검증한다
3. 모니터링 없이 CDC를 운영하면 안 된다. 특히 WAL/Binlog 쌓임과 Consumer Lag는 반드시 알림을 걸어야 한다
