---
title: AWS RDS (Relational Database Service)
tags: [aws, database, mysql, postgresql]
updated: 2026-07-24
---

# AWS RDS (Relational Database Service)

## RDS가 실제로 대신해주는 것

RDS는 관계형 DB를 EC2에 직접 설치하지 않고 AWS가 운영하는 매니지드 형태로 쓰는 서비스다. "완전 관리형"이라는 말이 자주 붙는데, 실무에서 이 말의 경계를 정확히 알아두지 않으면 장애 대응할 때 헷갈린다.

RDS가 대신 해주는 건 OS 패치, DB 엔진 마이너 버전 패치, 자동 백업과 스냅샷, Multi-AZ 페일오버, 스토리지 자동 확장 정도다. 반대로 RDS가 안 해주는 건 명확하다. 쿼리 튜닝, 인덱스 설계, 커넥션 수 관리, 파라미터 그룹 튜닝, 슬로우 쿼리 잡는 일은 전부 우리 몫이다. CPU가 100% 치는 건 대부분 RDS 문제가 아니라 풀스캔 쿼리 하나 때문이다. 매니지드라고 해서 DBA 역할이 사라지는 게 아니라, 인프라 잡일이 줄어드는 것뿐이다.

OS에 직접 SSH로 못 들어간다는 점도 처음엔 불편하다. `mysqld`를 직접 재시작하거나 OS 레벨 로그를 보는 게 막혀 있어서, 모든 진단을 CloudWatch 메트릭과 RDS가 노출하는 로그(슬로우 쿼리, 에러 로그), Performance Insights로만 해야 한다. 이 제약을 받아들이고 가는 서비스다.

지원 엔진은 MySQL, PostgreSQL, MariaDB, SQL Server, Oracle, 그리고 Amazon Aurora다. 이 중 Aurora는 같은 RDS 메뉴 안에 있지만 스토리지 구조가 완전히 다른 별개 엔진이라고 보는 게 맞다. Aurora 내부 동작과 RDS for MySQL과의 차이는 [Aurora_DB.md](Aurora_DB.md)에서 따로 다룬다. 이 문서는 RDS for MySQL/PostgreSQL/MariaDB/Oracle/SQL Server 기준으로 쓴다.

## 지원 엔진별 특성

엔진마다 제약과 주의사항이 다르다. 프로젝트 초기에 엔진을 정할 때 이 차이를 모르면 나중에 마이그레이션 비용이 생긴다.

### MySQL

RDS에서 가장 많이 쓰는 엔진이다. MySQL 8.0이 현재 주력이고, 5.7은 이미 EOL이 지나서 신규 프로젝트에 쓸 이유가 없다.

MySQL에서 주의할 점 두 가지다. 첫째, `max_connections` 기본값이 생각보다 낮다. RDS가 `DBInstanceClassMemory / 12MB`로 자동 계산하는데, db.r6g.large(메모리 16GB)면 약 1365가 한도다. 앱 인스턴스마다 커넥션 풀 20개씩 50대가 뜨면 이미 한도를 넘는다. 둘째, DDL이 락을 유발한다. 대용량 테이블에 ALTER TABLE을 날리면 온라인 DDL이라도 실제 운영에서 장기 락이 잡히는 상황이 있다. gh-ost나 pt-online-schema-change 같은 무중단 DDL 툴을 쓰거나, RDS [Blue/Green Deployment](RDS_Blue_Green_Deployment.md)로 우회하는 게 안전하다.

### PostgreSQL

오픈소스 DB 중 기능이 가장 풍부한 엔진이다. JSON, 배열, 전문 검색, 파티셔닝, 논리 복제 등 MySQL이 못 하거나 늦게 지원한 기능을 일찍 갖췄다.

RDS for PostgreSQL 특이사항이 있다. `rds_superuser` 역할이 있지만 실제 OS 레벨 superuser는 아니다. 일부 확장 기능(pg_cron 등)은 파라미터 그룹에서 `shared_preload_libraries`에 명시해야 활성화된다. `pg_stat_statements`도 마찬가지라 슬로우 쿼리 분석 전에 먼저 이걸 확인한다.

```sql
-- pg_stat_statements 확인
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

논리 복제(Logical Replication)를 쓰려면 `rds.logical_replication = 1` 파라미터와 `wal_level = logical`이 필요하다. 기본값은 꺼져 있고, 적용하려면 재부팅이 필요하다.

### MariaDB

MySQL 5.5 포크에서 시작한 엔진이다. 문법은 MySQL과 거의 같지만, 스토리지 엔진(Aria), JSON 처리 방식, 복제 구현이 MySQL과 미묘하게 다르다. MySQL을 쓰다가 MariaDB로 전환했더니 함수 동작이 다른 경우가 가끔 있다.

새 프로젝트에서 MariaDB를 고를 이유는 많지 않다. MariaDB를 써야 하는 레거시 시스템을 올릴 때 쓰는 정도다. 신규라면 MySQL 8.0이나 PostgreSQL이 더 낫다.

### Oracle

RDS for Oracle은 라이선스가 두 종류다. License Included(AWS가 라이선스 포함한 비용 청구)와 Bring Your Own License(BYOL, 기존 Oracle 라이선스 사용). BYOL 쪽이 인스턴스 비용이 낮지만 라이선스 이전 절차가 있고 Oracle의 지원 범위 문제가 생기는 경우가 있으니 계약 확인이 먼저다.

Oracle은 옵션 그룹(Option Group)을 반드시 다룬다. Oracle Statspack, TDE(투명한 데이터 암호화), S3 연동 같은 기능이 옵션 그룹으로 활성화된다. MySQL/PostgreSQL은 파라미터 그룹으로 대부분 제어하지만, Oracle은 파라미터 그룹 + 옵션 그룹 두 가지를 관리한다.

멀티 테넌트(CDB/PDB) 구조도 쓸 수 있다. 2021년에 PDB 하나짜리 CDB 가 먼저 들어왔고, 2023년부터 19c·21c(EE·SE2)에서 여러 PDB 를 한 CDB 에 올릴 수 있다. 기존 비-CDB 인스턴스를 CDB 로 전환하는 것도 된다.

### SQL Server

RDS for SQL Server는 에디션이 여러 개다. Express, Web, Standard, Enterprise 중 선택하는데, 에디션마다 지원 기능과 요금이 다르다. RDS가 대신 라이선스 비용을 포함하므로 별도 구매는 없지만, 이미 Software Assurance가 있으면 BYOL로 비용을 줄일 수 있다.

SQL Server도 옵션 그룹을 쓴다. SQL Server Audit, Mirroring, Transparent Data Encryption 같은 기능을 옵션 그룹에서 활성화한다.

SQL Server는 Multi-AZ 구성 시 내부적으로 SQL Server Database Mirroring 또는 Always On을 쓴다. 페일오버 동작은 다른 엔진의 Multi-AZ와 비슷하지만, 특정 시나리오에서 드라이버 재연결이 느리게 되는 경우가 있다. SQL Server 전용 JDBC 드라이버의 `loginTimeout` 설정을 잘 잡아야 한다.

SQL Server는 Windows 인증 연동(Kerberos)을 지원하는데, 이 기능을 쓰려면 AWS Directory Service와 연동해야 한다.

## 인스턴스 클래스별 특성

인스턴스 클래스는 처음 만들 때 대충 잡았다가 나중에 바꾸는 경우가 많은데, 변경할 때 다운타임이 생기므로(Multi-AZ면 페일오버로 수십 초, Single-AZ면 그보다 길다) 처음에 한 단계 여유 있게 잡는 편이 낫다.

| 계열 | 특성 | 주 용도 |
|------|------|---------|
| `db.t4g`, `db.t3` | 버스터블 CPU, 크레딧 소진 시 baseline으로 떨어짐 | 개발, 스테이징 |
| `db.m7g`, `db.m6g`, `db.m6i` | 범용, vCPU/메모리 균형 | 소규모 프로덕션, 읽기 비중이 낮은 서비스 |
| `db.r7g`, `db.r6g`, `db.r6i` | 메모리 최적화, vCPU 대비 메모리 2배 | OLTP 프로덕션, 캐시 히트율 중요한 워크로드 |
| `db.x2g` | 극단적 메모리, 최대 수 TB | 인메모리 집약적 워크로드 |

DB 워크로드는 거의 항상 메모리 바운드다. InnoDB buffer pool에 워킹셋이 안 들어가면 디스크 I/O가 폭증하면서 느려지기 때문에, CPU보다 메모리를 먼저 본다. 그래서 실무에서 프로덕션 DB는 범용(`db.m` 시리즈)보다 메모리 최적화(`db.r` 시리즈)를 쓰는 경우가 많다.

`db.t` 버스터블 클래스는 개발·스테이징에는 괜찮지만 프로덕션에 쓰면 위험하다. CPU 크레딧이 바닥나면 baseline 성능으로 떨어져서, 트래픽이 몰리는 정확히 그 순간에 DB가 느려진다. t 계열을 프로덕션에 쓴다면 CPU 크레딧 잔량(`CPUCreditBalance`)을 반드시 알람으로 걸어야 한다.

Graviton 기반 클래스(`db.r6g`, `db.m7g`)는 x86 대비 가격이 낮으면서 성능이 동급이거나 높다. Oracle, SQL Server는 Graviton 미지원이라 강제로 x86 계열을 써야 하지만, MySQL/PostgreSQL/MariaDB는 Graviton을 선택하지 않을 이유가 없다.

## 스토리지

스토리지 타입은 대부분 gp3로 시작한다. gp2 시절엔 용량과 IOPS가 묶여 있어서 IOPS를 늘리려고 안 쓰는 용량을 할당하는 낭비가 있었는데, gp3는 IOPS와 throughput을 용량과 별개로 지정할 수 있어 이 문제가 사라졌다. 새로 만든다면 gp2 쓸 이유가 없다.

스토리지 자동 확장(Storage Autoscaling)은 켜두는 게 안전하지만, 한 번 늘어난 스토리지는 줄일 수 없다는 점을 알고 써야 한다. 로그 테이블이 폭주해서 한 번 1TB로 늘면 그 비용을 계속 낸다. 그리고 스토리지 변경 작업 사이에는 최소 6시간 쿨다운이 있어서, 급하게 연속으로 늘릴 수 없다. 디스크 가득 차서 STORAGE_FULL로 인스턴스가 멈추는 사고를 막으려면 `FreeStorageSpace` 알람을 미리 걸어둔다.

Provisioned IOPS(io1/io2)는 정말로 일관된 고 IOPS가 필요한 경우에만 간다. 비싸기 때문에, gp3의 한계(16,000 IOPS)에 실제로 부딪히는지 메트릭으로 확인하기 전엔 안 넘어가는 게 보통이다.

## Multi-AZ vs Read Replica

가장 많이 혼동하는 구조 차이다. 한 줄로 정리하면, Multi-AZ는 **가용성**을 위한 구조고 Read Replica는 **읽기 부하 분산**을 위한 구조다.

```
Multi-AZ 구조

  [Primary - AZ-a]  ──동기 복제──>  [Standby - AZ-b]
       |                                    |
    (읽기/쓰기)                         (평소 유휴)
       |
  페일오버 발생 시 DNS 자동 전환
```

```
Read Replica 구조

  [Primary - AZ-a]
       |
       |──비동기 복제──>  [Replica 1]  (읽기 전용)
       |──비동기 복제──>  [Replica 2]  (읽기 전용)
       |──비동기 복제──>  [Replica 3]  (읽기 전용)
```

**Multi-AZ**는 다른 AZ에 standby를 동기 복제로 두고, primary가 죽으면 DNS 엔드포인트를 standby로 자동 전환한다. 페일오버는 보통 60~120초 사이에 끝난다. standby는 평소에 읽기 트래픽을 받지 않는다. 순수하게 장애 대비용으로 유휴 상태다. "Multi-AZ 켰으니 읽기 분산되겠지"는 틀린 기대다.

페일오버가 무중단인 것도 아니다. 그 60~120초 동안 커넥션은 다 끊기고, 애플리케이션은 새 엔드포인트로 다시 붙어야 한다. 커넥션 풀이 죽은 커넥션을 오래 붙잡고 있으면 페일오버가 끝나도 한참 에러가 난다. 이 구간을 줄이려면 [DB_Proxy.md](DB_Proxy.md)의 RDS Proxy를 앞에 두거나, 애플리케이션 JDBC 설정에서 커넥션 validation과 짧은 socket timeout을 잡아야 한다.

**Read Replica**는 읽기 부하를 분산한다. RDS for MySQL/PostgreSQL 기준 최대 15개까지 만들 수 있고, 각 레플리카는 자체 엔드포인트를 가진다. 핵심은 비동기 복제라는 점이다. primary에 쓴 데이터가 레플리카에 바로 보이지 않는다. 평소엔 수 밀리초~수 초지만, primary에 쓰기가 몰리거나 무거운 DDL이 돌면 복제 지연이 분 단위로 벌어진다.

"방금 회원가입했는데 로그인하니 없는 회원이라고 나온다" 같은 버그는 거의 다 회원가입(쓰기)은 primary에, 직후 로그인 조회(읽기)는 레플리카로 보냈는데 복제가 안 따라온 경우다. 읽기/쓰기 분리는 지연을 감내할 수 있는 읽기에만 적용한다. 통계, 리포트, 목록 조회처럼 몇 초 늦어도 되는 건 레플리카로, 방금 쓴 걸 바로 읽어야 하는 조회는 primary로 보낸다. `ReplicaLag` 메트릭은 항상 알람을 건다.

Read Replica는 장애 대비 수단이 아니다. Multi-AZ 없이 Read Replica만 있는 구성에서 primary가 죽으면, 레플리카를 수동으로 승격시켜야 한다. 자동 페일오버가 없다. 가용성이 필요하면 Multi-AZ를 켜야 한다.

| 비교 항목 | Multi-AZ | Read Replica |
|-----------|----------|--------------|
| 주 목적 | 가용성 (HA) | 읽기 부하 분산 |
| 복제 방식 | 동기 | 비동기 |
| 읽기 처리 | 불가 (standby 유휴) | 가능 (읽기 전용) |
| 자동 페일오버 | 있음 (60~120초) | 없음 (수동 승격) |
| 비용 | 인스턴스 2배 | 레플리카 수만큼 추가 |

## 파라미터 그룹과 옵션 그룹

### 파라미터 그룹

RDS는 OS 접근이 막혀 있어서 DB 엔진 설정을 파라미터 그룹으로만 바꾼다. 기본 파라미터 그룹은 수정이 안 되므로, 처음에 커스텀 파라미터 그룹을 하나 만들어 붙이고 시작한다.

파라미터에는 `immediate`로 바로 적용되는 것과 재부팅해야 적용되는 `pending-reboot`짜리가 섞여 있다. `innodb_buffer_pool_size`처럼 재부팅이 필요한 걸 바꾸면 적용하려고 reboot할 때 다운타임이 생기므로, 변경 시점을 미리 잡아야 한다.

```bash
# 커스텀 파라미터 그룹 생성
aws rds create-db-parameter-group \
  --db-parameter-group-name prod-mysql8-params \
  --db-parameter-group-family mysql8.0 \
  --description "Production MySQL 8.0 parameter group"

# 파라미터 설정
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-mysql8-params \
  --parameters \
    "ParameterName=max_connections,ParameterValue=500,ApplyMethod=immediate" \
    "ParameterName=innodb_buffer_pool_size,ParameterValue={DBInstanceClassMemory*3/4},ApplyMethod=pending-reboot" \
    "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=long_query_time,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=log_queries_not_using_indexes,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=innodb_flush_log_at_trx_commit,ParameterValue=2,ApplyMethod=pending-reboot" \
    "ParameterName=character_set_server,ParameterValue=utf8mb4,ApplyMethod=immediate" \
    "ParameterName=collation_server,ParameterValue=utf8mb4_unicode_ci,ApplyMethod=immediate"
```

실무에서 손대는 빈도가 높은 파라미터만 추렸다.

| 파라미터 | 값 | 메모 |
|---------|-----|------|
| `max_connections` | 메모리에 맞게 | RDS 기본 산정식은 `메모리/12MB`. 커넥션 풀 합계가 이걸 넘으면 "Too many connections" |
| `innodb_buffer_pool_size` | 메모리의 약 75% | `{DBInstanceClassMemory*3/4}`로 자동 표기. 워킹셋이 여기 안 들어가면 I/O 폭증 |
| `slow_query_log` | 1 | 켜두고 시작. 안 켜면 느린 쿼리를 못 잡는다 |
| `long_query_time` | 1초 | 처음엔 1초로 잡고, 잡히는 게 너무 많으면 조정 |
| `innodb_flush_log_at_trx_commit` | 1 또는 2 | 1=커밋마다 fsync(안전), 2=초당 fsync(빠르지만 장애 시 ~1초 유실). 금융성 데이터는 1 |

PostgreSQL 파라미터는 이름이 다르다.

| 파라미터 | 값 | 메모 |
|---------|-----|------|
| `shared_buffers` | 메모리의 25% | `{DBInstanceClassMemory/4}`로 표기 |
| `work_mem` | 4~64MB | 쿼리당 정렬·해시에 쓰는 메모리. 너무 크면 OOM |
| `log_min_duration_statement` | 1000ms | 슬로우 쿼리 로깅 임계값 |
| `max_connections` | 적절히 제한 | PostgreSQL은 커넥션 하나당 메모리를 많이 쓰므로 MySQL보다 보수적으로 잡는다 |

### 옵션 그룹

파라미터 그룹이 DB 엔진 파라미터를 제어한다면, 옵션 그룹은 추가 기능(옵션)을 활성화하는 개념이다. MySQL/PostgreSQL은 옵션 그룹이 거의 필요 없지만, Oracle과 SQL Server는 옵션 그룹으로 핵심 기능을 켜야 한다.

MySQL에서 옵션 그룹이 필요한 경우는 `MARIADB_AUDIT_PLUGIN`(MySQL 호환 감사 로그)이나 `MEMCACHED`(InnoDB Memcached 플러그인) 활성화 정도다. Oracle은 TDE, Statspack, S3 연동이 옵션 그룹 항목이다.

```bash
# Oracle용 옵션 그룹 생성 예시
aws rds create-option-group \
  --option-group-name prod-oracle-options \
  --engine-name oracle-ee \
  --major-engine-version "19" \
  --option-group-description "Production Oracle EE options"

# TDE 옵션 추가
aws rds add-option-to-option-group \
  --option-group-name prod-oracle-options \
  --options OptionName=TDE

# 인스턴스에 옵션 그룹 연결
aws rds modify-db-instance \
  --db-instance-identifier prod-oracle \
  --option-group-name prod-oracle-options \
  --apply-immediately
```

옵션 그룹 변경도 파라미터 그룹처럼 즉시 적용되는 것과 재부팅이 필요한 것이 섞여 있다. TDE처럼 영구적 변경이 수반되는 옵션은 되돌리기 어려우므로 적용 전에 스냅샷을 먼저 뜬다.

### Terraform으로 관리

파라미터 그룹과 인스턴스는 콘솔에서 만들지 말고 IaC로 관리하는 게 운영상 편하다. 누가 언제 뭘 바꿨는지 추적되고, 재현이 된다.

```hcl
resource "aws_db_parameter_group" "mysql_prod" {
  name   = "prod-mysql8-params"
  family = "mysql8.0"

  parameter {
    name  = "max_connections"
    value = "500"
  }

  parameter {
    name         = "innodb_buffer_pool_size"
    value        = "{DBInstanceClassMemory*3/4}"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "long_query_time"
    value = "1"
  }

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }
}

resource "aws_db_instance" "mysql_prod" {
  identifier        = "prod-mysql"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = "db.r6g.large"
  allocated_storage = 100
  storage_type      = "gp3"

  parameter_group_name = aws_db_parameter_group.mysql_prod.name

  multi_az = true

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # 프로덕션에는 무조건 켠다 — 실수 삭제 방어
  deletion_protection = true
  skip_final_snapshot = false
}
```

`deletion_protection`과 `skip_final_snapshot = false`는 프로덕션이면 무조건 켠다. Terraform `apply` 한 번 잘못 돌려서 DB가 destroy되는 사고를 막는 마지막 안전장치다.

## 실제 운영 문제와 해결

### 연결 수 초과 (Too many connections)

"Too many connections" 에러는 RDS를 운영하다 가장 자주 만나는 문제다. 원인은 단순하다. `max_connections` 한도를 넘겼다.

보통 이렇게 터진다. 오토스케일링으로 앱 인스턴스가 늘어나면서 (앱 인스턴스 수 × 커넥션 풀 크기)가 슬금슬금 `max_connections`를 넘어선다. 새벽 트래픽이 적을 땐 괜찮다가 낮에 스케일아웃이 되면서 갑자기 터진다.

```bash
# 현재 활성 커넥션 수 확인 (MySQL)
SELECT user, host, COUNT(*) as count
FROM information_schema.processlist
GROUP BY user, host
ORDER BY count DESC;

# 커넥션 상태 상세 확인
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';
```

즉각 대응은 두 가지다. 하나는 슬리핑 커넥션을 강제로 끊는 것이고(`KILL CONNECTION <id>`), 다른 하나는 `max_connections`를 즉시 올리는 것이다.

```bash
# max_connections 즉시 변경 (immediate 적용 파라미터)
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-mysql8-params \
  --parameters "ParameterName=max_connections,ParameterValue=1000,ApplyMethod=immediate"
```

근본 해결은 `max_connections`를 무작정 올리는 게 아니다. DB 인스턴스 메모리를 넘어설 정도로 커넥션을 늘리면 메모리 압박이 생긴다. 앱 쪽 커넥션 풀 크기를 줄이거나, [RDS Proxy](DB_Proxy.md)를 앞에 두어 커넥션 풀링을 위임하는 게 맞는 방향이다. RDS Proxy는 앱에서 오는 커넥션을 대신 모아 DB에는 적은 수의 커넥션만 유지하기 때문에, 스케일아웃 환경에서 특히 효과가 크다.

커넥션 수를 모니터링할 때 `DatabaseConnections` CloudWatch 메트릭이 `max_connections`의 80% 선에서 알람을 걸면, 터지기 전에 대응할 수 있다.

### 스토리지 꽉 참 (STORAGE_FULL)

`STORAGE_FULL` 상태가 되면 RDS 인스턴스가 읽기 전용으로 전환되거나 완전히 응답을 멈춘다. 쓰기가 안 되므로 서비스 장애다.

주요 원인은 세 가지다. 로그 테이블이 폭증했거나, 바이너리 로그(binlog)가 쌓였거나, 의도치 않게 대용량 데이터가 INSERT된 경우다.

즉각 대응은 스토리지를 수동으로 늘리는 것이다.

```bash
# 스토리지 즉시 확장
aws rds modify-db-instance \
  --db-instance-identifier prod-mysql \
  --allocated-storage 500 \
  --apply-immediately
```

스토리지 확장은 다운타임 없이 온라인으로 된다. 단, 6시간 쿨다운 제한이 있어서 방금 확장했으면 바로 또 늘릴 수 없다.

공간 확보를 빠르게 하려면 불필요한 테이블이나 데이터를 삭제하는 게 맞는데, MySQL에서 `DELETE`나 `DROP TABLE`을 해도 OS 공간이 즉시 반환되지 않는 경우가 있다. InnoDB는 `innodb_file_per_table`이 켜져 있으면 테이블별로 별도 파일을 쓰는데, `DROP TABLE`은 파일을 지우지만 `DELETE`는 내부 여유 공간으로만 남고 파일 크기는 그대로다. 이때 `OPTIMIZE TABLE`을 하면 파일 크기가 줄어들지만 전체 테이블 락이 걸리므로 주의한다.

```sql
-- 테이블 크기 상위 20개 확인 (MySQL)
SELECT
  table_name,
  ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = 'your_database'
ORDER BY size_mb DESC
LIMIT 20;
```

예방은 `FreeStorageSpace` 알람이다. 전체 스토리지의 20% 미만이면 알람 발송, 10% 미만이면 긴급 알람으로 두 단계로 잡는다. Storage Autoscaling을 켜두면 자동으로 늘어나지만, 마지막 확장 후 6시간 내에 다시 급증하는 상황은 자동 확장이 동작하지 않을 수 있으므로 알람 자체를 안 없애야 한다.

### 유지보수 창 다운타임

RDS 유지보수 창(Maintenance Window)은 AWS가 엔진 패치, OS 패치, 하드웨어 교체 등을 수행하는 시간대다. 설정하지 않으면 AWS가 자동으로 잡는다.

```bash
# 유지보수 창 설정 (월요일 새벽 2~3시 UTC)
aws rds modify-db-instance \
  --db-instance-identifier prod-mysql \
  --maintenance-window "Mon:02:00-Mon:03:00"
```

유지보수 유형에 따라 동작이 다르다.

OS 패치나 소규모 엔진 패치는 Multi-AZ 환경에서 standby에 먼저 적용하고 페일오버 후 primary에 적용하는 방식이라 서비스 중단 시간이 짧다(60초 내외). Single-AZ면 그 동안 인스턴스가 내려간다.

메이저 엔진 버전 업그레이드는 자동으로 안 된다. `allow-major-version-upgrade` 플래그를 명시해야 하고, 이 경우 상당한 다운타임이 발생한다. 마이너 버전 자동 업그레이드(`auto_minor_version_upgrade`)를 켜두면 마이너 패치는 유지보수 창에 자동으로 들어온다. 예상치 못한 패치가 부담스러우면 이 옵션을 끄고 수동으로 관리한다.

유지보수 창에 실제로 작업이 들어오는지는 이벤트 알람으로 미리 알 수 있다.

```bash
# RDS 유지보수 관련 이벤트 구독
aws rds create-event-subscription \
  --subscription-name rds-maintenance-alerts \
  --sns-topic-arn arn:aws:sns:ap-northeast-2:123456789:alerts \
  --source-type db-instance \
  --event-categories maintenance notification
```

유지보수 창을 설정할 때 백업 창과 겹치지 않게 해야 한다. 백업 중에 유지보수가 들어오면 백업이 연장되거나 유지보수가 밀린다. 주로 서비스 트래픽이 가장 적은 새벽 시간대로 잡되, 백업 창을 먼저 배치하고 유지보수 창을 그 뒤로 잡는 게 일반적이다.

```
[백업 창]         03:00 - 04:00
[유지보수 창]     04:00 - 05:00
```

메이저 버전 업그레이드처럼 다운타임이 긴 작업은 유지보수 창을 기다리지 않고 직접 실행 시점을 잡는 게 낫다. `apply-immediately`로 지금 당장 시작하거나, 다음 유지보수 창에 예약하거나 선택할 수 있다.

## 백업

RDS 백업은 두 가지다. 헷갈리면 복구할 때 큰일 나므로 차이를 명확히 한다.

자동 백업은 매일 한 번 스냅샷을 뜨고 트랜잭션 로그를 계속 저장해서, 보관 기간 안의 임의 시점으로 되돌리는 Point-in-Time Recovery(PITR)를 가능하게 한다. 보관 기간은 0~35일이고, 0으로 두면 자동 백업이 꺼진다. 프로덕션은 최소 7일 권장이다.

자동 백업의 함정은 인스턴스를 삭제하면 자동 백업도 같이 사라진다는 점이다. "실수로 DB 지웠는데 백업으로 살리면 되겠지" 했다가 자동 백업까지 날아간 사례가 있다. 장기 보관이 필요하면 수동 스냅샷을 따로 떠야 한다. 수동 스냅샷은 명시적으로 지울 때까지 남고, 다른 리전으로 복사해 DR 용도로 쓸 수 있다.

복구는 항상 기존 인스턴스를 덮어쓰는 게 아니라 새 인스턴스를 만든다. 그래서 복구 후엔 새 엔드포인트가 생기고, 애플리케이션 연결 정보를 바꾸거나 DNS를 갈아끼워야 한다. 복구 시간도 데이터 크기에 비례해서 수십 분 걸릴 수 있으니, RTO 계산할 때 이걸 빼먹으면 안 된다.

## 슬로우 쿼리 잡기

RDS에서 성능 문제는 결국 슬로우 쿼리 추적으로 귀결된다. OS에 못 들어가니 슬로우 로그를 CloudWatch Logs로 내보내거나 API로 받아서 본다.

```bash
# 슬로우 쿼리 로그 받기
aws rds download-db-log-file-portion \
  --db-instance-identifier prod-mysql \
  --log-file-name slowquery/mysql-slowquery.log \
  --output text
```

CloudWatch Logs로 내보내고 있으면 Logs Insights에서 정렬해서 본다.

```
fields @timestamp, @message
| filter @message like /Query_time/
| parse @message "Query_time: * Lock_time: * Rows_sent: * Rows_examined: *" as query_time, lock_time, rows_sent, rows_examined
| filter query_time > 1
| sort query_time desc
| limit 20
```

`Rows_examined`가 `Rows_sent`보다 훨씬 크면 인덱스를 안 타고 풀스캔하는 쿼리다. 이게 슬로우 쿼리의 대부분이다. Performance Insights를 켜두면 어떤 쿼리가 DB 부하(DB Load, AAS)를 가장 많이 먹는지 시각적으로 바로 보여서, 로그 파싱보다 먼저 여기를 보는 게 빠르다. Performance Insights 상세 분석은 [RDS_Performance_Insights.md](RDS_Performance_Insights.md)에서 다룬다.

## 모니터링 메트릭

알람 거는 메트릭은 많지만 실제로 장애 신호가 되는 건 정해져 있다.

- `CPUUtilization` — 지속적으로 높으면 거의 쿼리 문제. 80% 이상 지속 시 알람.
- `FreeableMemory` — 떨어지다 스왑 시작하면 급격히 느려진다.
- `DatabaseConnections` — `max_connections` 대비 80% 근처면 곧 커넥션 고갈.
- `FreeStorageSpace` — STORAGE_FULL로 멈추는 사고 방지. 20% 미만 알람.
- `ReplicaLag` — 리드 레플리카 쓰면 필수.
- `BurstBalance` / `CPUCreditBalance` — gp2나 t 계열 쓰면 바닥나기 전에 알람.
- `ReadIOPS` / `WriteIOPS` — 스토리지 IOPS 한도 근처에서 지연이 폭증한다.

알람은 SNS로 받아서 Slack이나 PagerDuty로 흘린다. 임계값은 처음엔 보수적으로 잡고, 오탐이 많으면 조정한다.

## 보안 기본값

RDS는 프라이빗 서브넷에 두고 퍼블릭 액세스는 끈다. 인터넷에서 직접 닿는 DB는 그 자체로 사고 원인이다. 보안 그룹은 애플리케이션 보안 그룹에서 들어오는 3306(MySQL)/5432(PostgreSQL)만 열고, IP 대역으로 여는 건 최소화한다.

저장 데이터 암호화(`storage_encrypted`)는 생성 시점에만 켤 수 있다. 나중에 켜려면 스냅샷 뜨고 암호화해서 복원하는 번거로운 과정을 거쳐야 하므로, 만들 때 무조건 켜는 게 맞다. KMS는 고객 관리형 키(CMK)를 쓰면 키 회전과 접근 권한을 직접 통제할 수 있다. DB 접속 인증은 IAM 인증을 쓰면 비밀번호를 안 박아도 되지만, 토큰 발급 비용과 커넥션 빈도 때문에 커넥션을 자주 새로 맺는 워크로드엔 안 맞을 수 있다.

## RDS vs Aurora 선택

Aurora 내부 동작과 비용 비교는 [Aurora_DB.md](Aurora_DB.md)에서 상세히 다루므로, 여기선 선택 판단만 정리한다.

흔히 "Aurora가 RDS보다 최대 5배 빠르다"는 문구를 보고 무조건 Aurora를 고르는데, 그 수치는 AWS가 특정 sysbench 조건에서 낸 마케팅 벤치마크다. 우리 워크로드에서 그대로 재현되지 않는다. 단순 OLTP에서는 잘 튜닝한 RDS for MySQL과 Aurora의 체감 차이가 크지 않은 경우도 많다. Aurora가 확실히 유리한 건 읽기 레플리카를 많이 붙여 읽기를 분산할 때(공유 스토리지라 레플리카가 복제 지연 거의 없이 붙는다)와, 페일오버를 빠르게(보통 30초 안쪽) 가져가야 할 때다.

RDS를 고르는 경우:
- Oracle, SQL Server, MariaDB처럼 Aurora가 지원 안 하는 엔진을 써야 할 때.
- 트래픽이 작거나 예측 가능해서 Aurora의 스토리지 I/O 과금이 오히려 비쌀 때. Aurora는 인스턴스 비용 외에 I/O 비용이 붙어서, I/O가 많으면 RDS보다 총비용이 더 나오는 경우가 있다.
- 운영을 단순하게 가져가고 싶고, 클러스터·라이터/리더 엔드포인트 개념까지 안 가도 되는 규모일 때.

Aurora를 고르는 경우:
- 리드 레플리카를 3개 이상 붙여 읽기를 크게 분산해야 할 때.
- 페일오버 시간을 최대한 줄여야 하는 가용성 요구가 있을 때.
- 데이터가 빠르게 커져서 스토리지 관리에서 손 떼고 싶을 때. Aurora 스토리지는 쓴 만큼 자동으로 늘고 안 쓰면 줄어든다.
- 글로벌 멀티 리전 복제가 필요할 때(Aurora Global Database).

엔진을 바꾸는 마이그레이션은 생각보다 비용이 크다. RDS for MySQL에서 Aurora MySQL로 가는 건 스냅샷 복원으로 비교적 매끄럽지만, 파라미터 디폴트값, `max_connections` 산정식, DDL 처리 방식이 미묘하게 달라서 "옮겼더니 똑같이 동작할 것"이라는 가정은 위험하다.

## 참조

- AWS RDS 사용자 가이드: https://docs.aws.amazon.com/rds/
- RDS 모범 사례: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html
- Performance Insights: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html
- RDS 가격: https://aws.amazon.com/rds/pricing/
- 관련 문서: [Aurora_DB.md](Aurora_DB.md), [DB_Proxy.md](DB_Proxy.md), [RDS_Blue_Green_Deployment.md](RDS_Blue_Green_Deployment.md), [RDS_Performance_Insights.md](RDS_Performance_Insights.md)
