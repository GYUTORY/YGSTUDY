---
title: Cloud SQL 마이그레이션
tags: [gcp, devops, database, cloud]
updated: 2026-08-05
---

# Cloud SQL 마이그레이션

온프렘 MySQL/PostgreSQL, AWS RDS에서 Cloud SQL로 이전할 때 선택지는 크게 두 가지다. Database Migration Service(DMS)를 쓰는 온라인 방식과, mysqldump/pg_dump를 쓰는 오프라인 방식. 어떤 방법을 고르느냐에 따라 다운타임이 결정된다.

## DMS vs 오프라인 덤프 — 선택 기준

| 항목 | DMS (온라인) | 덤프/복원 (오프라인) |
|---|---|---|
| 다운타임 | 수십 초~수 분 (컷오버 시점만) | DB 크기에 비례, 수 시간 가능 |
| 복잡도 | 설정이 많고 사전 점검 필요 | 절차가 단순하고 예측 가능 |
| 데이터 크기 | 수 TB 이상도 처리 가능 | 수백 GB 넘으면 전송 시간이 길어진다 |
| 적합 대상 | 24시간 운영 서비스, SLA 요구 낮은 다운타임 | 배치성 DB, 야간 점검창이 충분한 경우 |
| 비용 | DMS 인스턴스 비용 별도 발생 | 네트워크 전송 비용만 |

DB 크기가 100GB 미만이고 야간 점검창이 2시간 이상 확보된다면 덤프 방식이 훨씬 간단하다. 반면 운영 중인 서비스라 다운타임을 최소화해야 한다면 DMS가 현실적인 선택이다.

## DMS 온라인 마이그레이션

### 전체 흐름

DMS 마이그레이션은 두 단계로 구분된다. 초기 전체 로드(Full Load)와 그 이후 지속 복제(CDC). 둘을 명확히 구분해야 컷오버 타이밍을 잡을 수 있다.

```
소스 DB → [Full Load] → 대상 Cloud SQL (데이터 동기화)
              ↓
소스 DB → [CDC 복제] → 대상 Cloud SQL (실시간 변경 반영)
              ↓
          [컷오버] → 애플리케이션을 대상 DB로 전환
```

**Full Load**: DMS가 소스 DB의 현재 스냅샷을 Cloud SQL로 복사한다. 대용량 테이블은 이 단계에서 수 시간이 소요된다.

**CDC**: Full Load가 끝난 시점부터 소스 DB의 변경사항(INSERT/UPDATE/DELETE)을 binlog(MySQL) 또는 WAL(PostgreSQL)에서 읽어 실시간으로 반영한다. CDC가 안정적으로 작동하는 것을 확인한 뒤에야 컷오버를 고려한다.

### 사전 요구사항

MySQL 소스 기준으로 반드시 확인해야 할 사항들이 있다.

```sql
-- binlog 활성화 여부 확인
SHOW VARIABLES LIKE 'log_bin';
-- 반드시 ON이어야 한다

-- binlog 포맷 확인
SHOW VARIABLES LIKE 'binlog_format';
-- ROW 포맷이어야 CDC가 작동한다. STATEMENT나 MIXED면 변경 필요

-- binlog 보존 기간 확인
SHOW VARIABLES LIKE 'expire_logs_days';
-- DMS 복제 지연을 고려해 최소 3일 이상 설정한다
```

AWS RDS MySQL이라면 파라미터 그룹에서 `binlog_format=ROW`, `binlog_retention_hours` 를 설정하고 인스턴스를 재시작해야 한다. 온프렘이면 `my.cnf`를 수정하고 MySQL 재시작이 필요하다.

PostgreSQL 소스라면 `wal_level=logical`이 필수다.

```sql
-- PostgreSQL WAL 레벨 확인
SHOW wal_level;
-- logical이어야 한다. minimal이나 replica면 마이그레이션 불가
```

RDS PostgreSQL은 파라미터 그룹 변경 후 재부팅이 필요하고, 온프렘은 `postgresql.conf`에서 `wal_level = logical`로 변경한다.

### DMS 마이그레이션 잡 구성

GCP 콘솔에서 DMS > 마이그레이션 잡 생성 순서로 진행한다.

1. **연결 프로필 생성**: 소스 DB 연결 정보(호스트, 포트, 계정). 소스가 AWS RDS라면 공개 접근 허용 또는 VPN/VPC 피어링이 필요하다.
2. **대상 Cloud SQL 인스턴스 지정**: 마이그레이션 잡에서 대상 인스턴스를 새로 만들거나 기존 인스턴스를 지정한다.
3. **마이그레이션 유형 선택**: "연속"을 선택해야 Full Load + CDC가 모두 동작한다. "1회성"은 Full Load만 수행하고 종료된다.
4. **객체 매핑**: 특정 스키마나 테이블만 선택적으로 마이그레이션하거나 제외할 수 있다.

마이그레이션 잡을 시작하면 상태가 `FULL_DUMP` → `CDC` 순으로 전환된다. CDC 상태가 되면 복제 지연(Replication Lag)을 모니터링한다. 라그가 0에 가까워지면 컷오버 준비가 된 것이다.

## 컷오버 전 데이터 정합성 검증

컷오버 직전, 소스와 대상 DB의 데이터가 실제로 일치하는지 확인해야 한다. DMS 콘솔에서 제공하는 "데이터 검증" 기능을 사용하거나 직접 쿼리로 확인한다.

### 테이블 행 수 비교

```sql
-- 소스 DB에서 실행
SELECT table_name, table_rows
FROM information_schema.tables
WHERE table_schema = 'your_database'
ORDER BY table_name;

-- 대상 Cloud SQL에서 동일하게 실행 후 비교
```

`table_rows`는 InnoDB 기준 근사값이라 정확하지 않다. 핵심 테이블은 `COUNT(*)`로 직접 확인한다.

```sql
-- 중요 테이블 정확한 행 수 비교
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM users;
```

### 체크섬 비교

행 수가 같아도 데이터 내용이 다를 수 있다. 핵심 컬럼의 합계나 체크섬을 비교한다.

```sql
-- 금액 컬럼 합계 비교
SELECT SUM(amount), MAX(created_at) FROM orders;

-- 특정 범위의 레코드 해시 비교 (MySQL)
SELECT MD5(GROUP_CONCAT(id, name, email ORDER BY id))
FROM users
WHERE id BETWEEN 1 AND 10000;
```

모든 테이블을 검증하는 것은 현실적으로 어렵다. 비즈니스 임팩트가 큰 테이블, 최근 1주일 내 변경이 많은 테이블 위주로 집중 확인한다.

### 복제 지연 확인

```sql
-- MySQL DMS 소스에서 현재 binlog 위치 확인
SHOW MASTER STATUS;

-- Cloud SQL에서 복제 상태 확인 (DMS가 관리하지만 참고용)
SHOW REPLICA STATUS\G
-- Seconds_Behind_Source: 0이어야 안전하다
```

DMS 콘솔의 "복제 지연" 지표가 60초 이하, 이상적으로는 10초 이하일 때 컷오버를 진행한다.

## 컷오버 절차

```
1. 애플리케이션 트래픽 차단 (읽기 전용 모드 또는 점검 페이지)
2. 소스 DB 추가 쓰기 금지 확인
3. DMS 복제 지연이 0이 될 때까지 대기 (보통 10~30초)
4. 소스/대상 최종 데이터 정합성 검증
5. DMS 마이그레이션 잡 중지
6. 애플리케이션 연결 문자열을 Cloud SQL로 변경
7. 애플리케이션 재시작 및 트래픽 재개
8. 기능 정상 동작 확인
```

2번에서 소스 DB를 읽기 전용으로 전환하는 방법은 DB마다 다르다.

```sql
-- MySQL: 전체 플러시 및 읽기 전용 전환
FLUSH TABLES WITH READ LOCK;
SET GLOBAL read_only = ON;

-- PostgreSQL: 새 연결 차단
UPDATE pg_database SET datallowconn = false WHERE datname = 'your_db';
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'your_db';
```

## 컷오버 실패 시 롤백

컷오버 후 문제가 발생했을 때 롤백 절차는 사전에 반드시 준비해두어야 한다.

### 롤백 기준 설정

컷오버 전에 "X분 내에 Y 오류가 발생하면 롤백"이라는 기준을 명확히 정해야 한다. 기준 없이 진행하면 컷오버 후 혼란 상황에서 판단이 흐려진다.

### 롤백 절차

```
1. 애플리케이션 트래픽 재차단
2. Cloud SQL에서 소스 DB로 연결 문자열 원복
3. 소스 DB 읽기 전용 해제

-- MySQL 읽기 전용 해제
SET GLOBAL read_only = OFF;
UNLOCK TABLES;

-- PostgreSQL 연결 재허용
UPDATE pg_database SET datallowconn = true WHERE datname = 'your_db';

4. 애플리케이션 재시작 및 트래픽 재개
```

컷오버 실패 후 롤백 시 가장 큰 문제는 컷오버 시점 이후에 Cloud SQL에 기록된 데이터다. 서비스가 Cloud SQL로 전환된 시간이 길수록 그 사이 생성된 데이터를 소스 DB로 다시 동기화해야 한다.

롤백이 발생했다는 것은 컷오버 전 검증이 부족했다는 의미다. 원인 분석 후 재시도 일정을 잡는다.

## 오프라인 마이그레이션 — mysqldump/pg_dump

다운타임이 허용되는 상황이라면 훨씬 단순하다.

### MySQL

```bash
# 소스에서 덤프
mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --set-gtid-purged=OFF \
  -h source-host \
  -u root -p \
  your_database > dump.sql

# Cloud SQL로 임포트
# GCS에 업로드 후 Cloud SQL 콘솔에서 임포트하거나 Cloud SQL Proxy로 직접 복원
gcloud sql import sql your-instance-name gs://your-bucket/dump.sql \
  --database=your_database
```

`--single-transaction`은 MyISAM 테이블이 없는 경우에만 유효하다. MyISAM 테이블이 섞여 있으면 `--lock-all-tables`를 써야 한다.

`--set-gtid-purged=OFF`는 Cloud SQL이 GTID 모드로 운영될 때 충돌을 피하기 위해 필요하다.

### PostgreSQL

```bash
# 소스에서 커스텀 포맷 덤프 (병렬 복원 가능)
pg_dump \
  -h source-host \
  -U postgres \
  -Fc \
  -f dump.dump \
  your_database

# Cloud SQL Proxy를 통해 복원
pg_restore \
  -h 127.0.0.1 \
  -p 5432 \
  -U postgres \
  -d your_database \
  -j 4 \  # 병렬 작업 수 (Cloud SQL vCPU 수에 맞춰 조정)
  dump.dump
```

`-j 4` 옵션으로 병렬 복원이 가능한데, Cloud SQL 인스턴스 크기에 맞게 조정한다. 과도하게 높이면 CPU 부하로 오히려 느려진다.

## 대용량 테이블 마이그레이션 주의사항

### 트랜잭션 로그 크기

DMS Full Load 중 소스 DB의 binlog(MySQL) 또는 WAL(PostgreSQL) 크기가 급증할 수 있다. Full Load가 진행되는 동안 소스 DB의 변경사항을 모두 binlog에 보존해야 하기 때문이다.

MySQL의 경우 `binlog_cache_size`와 디스크 여유 공간을 사전에 확인한다. Full Load가 10시간 걸리는 DB라면 그 10시간 동안 쌓이는 binlog를 저장할 공간이 필요하다. 예상보다 binlog가 크게 쌓이면 소스 DB의 디스크가 꽉 차서 서비스 장애로 이어진다.

```sql
-- MySQL binlog 현황 확인
SHOW BINARY LOGS;
-- 각 binlog 파일 크기의 합이 가용 디스크의 50% 이하여야 안전하다

-- binlog 자동 삭제 주기 확인 (너무 짧으면 CDC 복제가 끊긴다)
SHOW VARIABLES LIKE 'expire_logs_days';
```

### 복제 지연 누적

단일 트랜잭션이 수백만 건을 변경하는 배치 작업이 소스에서 실행되면 CDC 복제가 순간적으로 크게 벌어진다. 마이그레이션 기간 중에는 소스 DB에서 대규모 배치 작업을 피해야 한다.

피할 수 없다면 배치를 작은 단위로 쪼갠다.

```sql
-- 나쁜 예: 한 번에 수백만 건 업데이트
UPDATE orders SET status = 'archived' WHERE created_at < '2023-01-01';

-- 나은 예: 1만 건씩 나눠서 처리
UPDATE orders SET status = 'archived'
WHERE created_at < '2023-01-01'
LIMIT 10000;
-- 이를 반복 실행
```

### 대용량 테이블의 Full Load 시간 예측

DMS가 처리하는 속도는 네트워크 대역폭, 소스 DB 부하, 대상 Cloud SQL 스펙에 따라 크게 달라진다. 일반적으로 100GB 기준 1~3시간 정도를 예상하지만, 실제로는 더 오래 걸리는 경우가 많다.

테이블별로 행 수와 평균 행 크기를 사전에 확인해 두면 예측이 쉬워진다.

```sql
-- MySQL: 테이블별 크기 확인
SELECT
  table_name,
  table_rows,
  ROUND(data_length / 1024 / 1024, 2) AS data_mb,
  ROUND(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.tables
WHERE table_schema = 'your_database'
ORDER BY data_length DESC;
```

데이터 크기가 큰 테이블일수록 Full Load가 오래 걸린다. 가능하다면 마이그레이션 전에 불필요한 데이터를 정리(아카이빙)해 두는 게 낫다.

## 마이그레이션 후 확인

컷오버 완료 후 바로 확인해야 하는 항목들이 있다.

Cloud SQL의 슬로우 쿼리 로그를 켜두고, 소스 DB에서는 정상이었던 쿼리가 Cloud SQL에서 느려지는 경우를 확인한다. 인덱스가 누락됐거나 파라미터 설정이 다른 경우다.

```sql
-- Cloud SQL에서 슬로우 쿼리 확인 (MySQL)
SELECT *
FROM mysql.slow_log
ORDER BY start_time DESC
LIMIT 50;
```

소스 DB의 커넥션 풀 크기와 Cloud SQL의 `max_connections` 설정이 다르면 연결 오류가 발생한다. 마이그레이션 전에 맞춰두거나, Cloud SQL Proxy/Pgbouncer를 앞에 두는 것을 권장한다.

마이그레이션이 성공적으로 완료된 후에도 소스 DB는 최소 1~2주는 유지해두는 것이 좋다. 문제 발생 시 롤백 또는 데이터 비교 참조용으로 필요하다.
