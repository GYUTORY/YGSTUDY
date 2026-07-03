---
title: AWS RDS (Relational Database Service)
tags: [aws, database, rds, mysql, postgresql, aurora]
updated: 2026-06-15
---

# AWS RDS (Relational Database Service)

## RDS가 실제로 대신해주는 것

RDS는 관계형 DB를 EC2에 직접 설치하지 않고 AWS가 운영하는 매니지드 형태로 쓰는 서비스다. "완전 관리형"이라는 말이 자주 붙는데, 실무에서 이 말의 경계를 정확히 알아두지 않으면 장애 대응할 때 헷갈린다.

RDS가 대신 해주는 건 OS 패치, DB 엔진 마이너 버전 패치, 자동 백업과 스냅샷, Multi-AZ 페일오버, 스토리지 자동 확장 정도다. 반대로 RDS가 안 해주는 건 명확하다. 쿼리 튜닝, 인덱스 설계, 커넥션 수 관리, 파라미터 그룹 튜닝, 슬로우 쿼리 잡는 일은 전부 우리 몫이다. CPU가 100% 치는 건 대부분 RDS 문제가 아니라 풀스캔 쿼리 하나 때문이다. 매니지드라고 해서 DBA 역할이 사라지는 게 아니라, 인프라 잡일이 줄어드는 것뿐이다.

OS에 직접 SSH로 못 들어간다는 점도 처음엔 불편하다. `mysqld`를 직접 재시작하거나 OS 레벨 로그를 보는 게 막혀 있어서, 모든 진단을 CloudWatch 메트릭과 RDS가 노출하는 로그(슬로우 쿼리, 에러 로그), Performance Insights로만 해야 한다. 이 제약을 받아들이고 가는 서비스다.

지원 엔진은 MySQL, PostgreSQL, MariaDB, SQL Server, Oracle, 그리고 Amazon Aurora다. 이 중 Aurora는 같은 RDS 메뉴 안에 있지만 스토리지 구조가 완전히 다른 별개 엔진이라고 보는 게 맞다. Aurora 내부 동작과 RDS for MySQL과의 차이는 [Aurora_DB.md](Aurora_DB.md)에서 따로 다룬다. 이 문서는 RDS for MySQL/PostgreSQL 기준으로 쓴다.

## 인스턴스 클래스를 어떻게 고르나

인스턴스 클래스는 처음 만들 때 대충 잡았다가 나중에 바꾸는 경우가 많은데, 변경할 때 다운타임이 생기므로(Multi-AZ면 페일오버로 수십 초, Single-AZ면 그보다 길다) 처음에 한 단계 여유 있게 잡는 편이 낫다.

DB 워크로드는 거의 항상 메모리 바운드다. InnoDB buffer pool에 워킹셋이 안 들어가면 디스크 I/O가 폭증하면서 느려지기 때문에, CPU보다 메모리를 먼저 본다. 그래서 실무에서 프로덕션 DB는 범용(`db.m` 시리즈)보다 메모리 최적화(`db.r` 시리즈)를 쓰는 경우가 많다. `db.r6g`, `db.r6i` 같은 클래스가 데이터 캐싱이 중요한 OLTP에 잘 맞는다.

`db.t` 버스터블 클래스는 개발·스테이징에는 괜찮지만 프로덕션에 쓰면 위험하다. CPU 크레딧이 바닥나면 baseline 성능으로 떨어져서, 트래픽이 몰리는 정확히 그 순간에 DB가 느려진다. t 계열을 프로덕션에 쓴다면 CPU 크레딧 잔량(`CPUCreditBalance`)을 반드시 알람으로 걸어야 한다.

## 스토리지 — gp3와 IOPS 함정

스토리지 타입은 대부분 gp3로 시작한다. gp2 시절엔 용량과 IOPS가 묶여 있어서 IOPS를 늘리려고 안 쓰는 용량을 할당하는 낭비가 있었는데, gp3는 IOPS와 throughput을 용량과 별개로 지정할 수 있어 이 문제가 사라졌다. 새로 만든다면 gp2 쓸 이유가 없다.

스토리지 자동 확장(Storage Autoscaling)은 켜두는 게 안전하지만, 한 번 늘어난 스토리지는 줄일 수 없다는 점을 알고 써야 한다. 로그 테이블이 폭주해서 한 번 1TB로 늘면 그 비용을 계속 낸다. 그리고 스토리지 변경 작업 사이에는 최소 6시간 쿨다운이 있어서, 급하게 연속으로 늘릴 수 없다. 디스크 가득 차서 STORAGE_FULL로 인스턴스가 멈추는 사고를 막으려면 `FreeStorageSpace` 알람을 미리 걸어둔다.

Provisioned IOPS(io1/io2)는 정말로 일관된 고 IOPS가 필요한 경우에만 간다. 비싸기 때문에, gp3의 한계(16,000 IOPS)에 실제로 부딪히는지 메트릭으로 확인하기 전엔 안 넘어가는 게 보통이다.

## Multi-AZ는 가용성이지 성능이 아니다

Multi-AZ는 가장 흔하게 오해받는 기능이다. 다른 AZ에 standby를 동기 복제로 두고, primary가 죽으면 DNS 엔드포인트를 standby로 자동 전환한다. 페일오버는 보통 60초에서 120초 사이에 끝난다.

오해하면 안 되는 건, standby는 평소에 읽기 트래픽을 받지 않는다는 점이다. 순수하게 장애 대비용으로 놀고 있다. "Multi-AZ 켰으니 읽기 분산되겠지"는 틀린 기대다. 읽기 분산은 별도로 리드 레플리카를 만들어야 한다. (단 Aurora나 RDS Multi-AZ 클러스터 배포는 다르게 동작한다.)

페일오버가 무중단인 것도 아니다. 그 60~120초 동안 커넥션은 다 끊기고, 애플리케이션은 새 엔드포인트로 다시 붙어야 한다. 커넥션 풀이 죽은 커넥션을 오래 붙잡고 있으면 페일오버가 끝나도 한참 에러가 난다. 이 구간을 줄이려면 [DB_Proxy.md](DB_Proxy.md)의 RDS Proxy를 앞에 두거나, 애플리케이션 JDBC 설정에서 커넥션 validation과 짧은 socket timeout을 잡아야 한다.

## 리드 레플리카 — 비동기라는 전제

읽기 부하를 분산하려면 리드 레플리카를 만든다. RDS for MySQL/PostgreSQL 기준 최대 15개까지 만들 수 있고, 각 레플리카는 자체 엔드포인트를 가진다.

핵심은 비동기 복제라는 점이다. primary에 쓴 데이터가 레플리카에 바로 보이지 않는다. 평소엔 수 밀리초~수 초지만, primary에 쓰기가 몰리거나 무거운 DDL이 돌면 복제 지연이 분 단위로 벌어진다. "방금 회원가입했는데 로그인하니 없는 회원이라고 나온다" 같은 버그는 거의 다 회원가입(쓰기)은 primary에, 직후 로그인 조회(읽기)는 레플리카로 보냈는데 복제가 안 따라온 경우다.

그래서 읽기/쓰기 분리는 무조건 하는 게 아니라, 지연을 감내할 수 있는 읽기에만 적용한다. 통계, 리포트, 목록 조회처럼 몇 초 늦어도 되는 건 레플리카로, 방금 쓴 걸 바로 읽어야 하는 조회는 primary로 보낸다. `ReplicaLag` 메트릭은 항상 알람을 건다.

## 백업 — 자동 백업과 스냅샷의 차이

RDS 백업은 두 가지다. 헷갈리면 복구할 때 큰일 나므로 차이를 명확히 한다.

자동 백업은 매일 한 번 스냅샷을 뜨고 트랜잭션 로그를 계속 저장해서, 보관 기간 안의 임의 시점으로 되돌리는 Point-in-Time Recovery(PITR)를 가능하게 한다. 보관 기간은 0~35일이고, 0으로 두면 자동 백업이 꺼진다(개발용이 아니면 0은 위험하다). 프로덕션은 최소 7일 권장이다.

자동 백업의 함정은 인스턴스를 삭제하면 자동 백업도 같이 사라진다는 점이다. "실수로 DB 지웠는데 백업으로 살리면 되겠지" 했다가 자동 백업까지 날아간 사례가 있다. 장기 보관이 필요하면 수동 스냅샷을 따로 떠야 한다. 수동 스냅샷은 명시적으로 지울 때까지 남고, 다른 리전으로 복사해 DR 용도로 쓸 수 있다.

복구는 항상 기존 인스턴스를 덮어쓰는 게 아니라 새 인스턴스를 만든다. 그래서 복구 후엔 새 엔드포인트가 생기고, 애플리케이션 연결 정보를 바꾸거나 DNS를 갈아끼워야 한다. 복구 시간도 데이터 크기에 비례해서 수십 분 걸릴 수 있으니, RTO 계산할 때 이걸 빼먹으면 안 된다.

## 파라미터 그룹 튜닝

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

# 인스턴스에 적용
aws rds modify-db-instance \
  --db-instance-identifier prod-mysql \
  --db-parameter-group-name prod-mysql8-params \
  --apply-immediately
```

실무에서 손대는 빈도가 높은 파라미터만 추렸다.

| 파라미터 | 값 | 메모 |
|---------|-----|------|
| `max_connections` | 메모리에 맞게 | RDS 기본 산정식은 `메모리/12MB`. 커넥션 풀 합계가 이걸 넘으면 "Too many connections" |
| `innodb_buffer_pool_size` | 메모리의 약 75% | RDS는 `{DBInstanceClassMemory*3/4}`로 자동 표기. 워킹셋이 여기 안 들어가면 I/O 폭증 |
| `slow_query_log` | 1 | 켜두고 시작. 안 켜면 느린 쿼리를 못 잡는다 |
| `long_query_time` | 1초 | 처음엔 1초로 잡고, 잡히는 게 너무 많으면 조정 |
| `innodb_flush_log_at_trx_commit` | 1 또는 2 | 1=커밋마다 fsync(안전), 2=초당 fsync(빠르지만 장애 시 ~1초 유실). 금융성 데이터는 1 |

`max_connections`는 특히 주의한다. 애플리케이션 인스턴스마다 커넥션 풀을 띄우는데, (인스턴스 수 × 풀 크기)가 `max_connections`를 넘으면 새 커넥션이 거부되면서 장애가 난다. 오토스케일링으로 앱이 늘어나는 환경이면 이 합계가 슬금슬금 넘어가기 쉽다. 커넥션 수가 한계라면 `max_connections`를 무작정 올리기 전에 RDS Proxy로 커넥션 풀링을 앞단에 두는 걸 먼저 검토한다.

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

  # 운영 DB는 반드시 켠다 — 실수 삭제 방어
  deletion_protection = true
  skip_final_snapshot = false
}
```

`deletion_protection`과 `skip_final_snapshot = false`는 프로덕션이면 무조건 켠다. Terraform `apply` 한 번 잘못 돌려서 DB가 destroy되는 사고를 막는 마지막 안전장치다.

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

`Rows_examined`가 `Rows_sent`보다 훨씬 크면 인덱스를 안 타고 풀스캔하는 쿼리다. 이게 슬로우 쿼리의 대부분이다. Performance Insights를 켜두면 어떤 쿼리가 DB 부하(DB Load, AAS)를 가장 많이 먹는지 시각적으로 바로 보여서, 로그 파싱보다 먼저 여기를 보는 게 빠르다.

## 모니터링에서 먼저 보는 메트릭

알람 거는 메트릭은 많지만 실제로 장애 신호가 되는 건 정해져 있다.

- `CPUUtilization` — 지속적으로 높으면 거의 쿼리 문제. 80% 이상 지속 시 알람.
- `FreeableMemory` — 떨어지다 스왑 시작하면 급격히 느려진다.
- `DatabaseConnections` — `max_connections` 대비 90% 근처면 곧 커넥션 고갈.
- `FreeStorageSpace` — STORAGE_FULL로 멈추는 사고 방지. 20% 미만 알람.
- `ReplicaLag` — 리드 레플리카 쓰면 필수.
- `BurstBalance` / `CPUCreditBalance` — gp2나 t 계열 쓰면 바닥나기 전에 알람.

알람은 SNS로 받아서 Slack이나 PagerDuty로 흘린다. 임계값은 처음엔 보수적으로 잡고, 오탐이 많으면 조정한다.

## 보안 기본값

RDS는 프라이빗 서브넷에 두고 퍼블릭 액세스는 끈다. 인터넷에서 직접 닿는 DB는 그 자체로 사고 원인이다. 보안 그룹은 애플리케이션 보안 그룹에서 들어오는 3306(MySQL)/5432(PostgreSQL)만 열고, IP 대역으로 여는 건 최소화한다.

저장 데이터 암호화(`storage_encrypted`)는 생성 시점에만 켤 수 있다. 나중에 켜려면 스냅샷 뜨고 암호화해서 복원하는 번거로운 과정을 거쳐야 하므로, 만들 때 무조건 켜는 게 맞다. KMS는 고객 관리형 키(CMK)를 쓰면 키 회전과 접근 권한을 직접 통제할 수 있다. DB 접속 인증은 IAM 인증을 쓰면 비밀번호를 안 박아도 되지만, 토큰 발급 비용과 커넥션 빈도 때문에 커넥션을 자주 새로 맺는 워크로드엔 안 맞을 수 있다.

## RDS와 Aurora, 무엇을 고를까

Aurora 내부 동작과 비용 비교는 [Aurora_DB.md](Aurora_DB.md)에서 상세히 다루므로, 여기선 선택 판단만 정리한다.

흔히 "Aurora가 RDS보다 최대 5배 빠르다"는 문구를 보고 무조건 Aurora를 고르는데, 그 수치는 AWS가 특정 sysbench 조건에서 낸 마케팅 벤치마크다. 우리 워크로드에서 그대로 재현되지 않는다. 실제로 단순 OLTP에서는 잘 튜닝한 RDS for MySQL과 Aurora의 체감 차이가 크지 않은 경우도 많다. Aurora가 확실히 유리한 건 읽기 레플리카를 많이 붙여 읽기를 분산할 때(공유 스토리지라 레플리카가 복제 지연 거의 없이 붙는다)와, 페일오버를 빠르게(보통 30초 안쪽) 가져가야 할 때다.

판단 기준을 경험상 이렇게 잡는다.

RDS를 고르는 경우:
- Oracle, SQL Server, MariaDB처럼 Aurora가 지원 안 하는 엔진을 써야 할 때.
- 트래픽이 작거나 예측 가능해서 Aurora의 스토리지 I/O 과금(읽고 쓴 양만큼 따로 청구)이 오히려 비싸질 때. Aurora는 인스턴스 비용 외에 I/O 비용이 붙어서, I/O가 많으면 RDS보다 총비용이 더 나오는 경우가 있다(이 걱정을 없애려면 Aurora I/O-Optimized를 써야 하는데 인스턴스 단가가 오른다).
- 운영을 단순하게 가져가고 싶고, 클러스터·라이터/리더 엔드포인트 개념까지 안 가도 되는 규모일 때.

Aurora를 고르는 경우:
- 리드 레플리카를 3개 이상 붙여 읽기를 크게 분산해야 할 때.
- 페일오버 시간을 최대한 줄여야 하는 가용성 요구가 있을 때.
- 데이터가 빠르게 커져서 스토리지 관리(자동 확장, 줄이기 불가 문제)에서 손 떼고 싶을 때. Aurora 스토리지는 쓴 만큼 자동으로 늘고 안 쓰면 줄어든다.
- 글로벌 멀티 리전 복제가 필요할 때(Aurora Global Database).

엔진을 바꾸는 마이그레이션은 생각보다 비용이 크다. RDS for MySQL에서 Aurora MySQL로 가는 건 스냅샷 복원으로 비교적 매끄럽지만, 파라미터 디폴트값, `max_connections` 산정식, DDL 처리 방식이 미묘하게 달라서 "옮겼더니 똑같이 동작할 것"이라는 가정은 위험하다. 이 차이는 [Aurora_DB.md](Aurora_DB.md)에 정리해뒀다.

## RDS와 다른 데이터 스토어

관계형이 아닌 선택지와의 경계도 자주 묻는다.

DynamoDB는 키 기반 접근 패턴이 명확하고 무제한 확장이 필요할 때 간다. 조인이나 복잡한 SQL이 필요하면 애초에 후보가 아니다. 세션, 장바구니, 이벤트 로그처럼 단순 조회/쓰기가 대량으로 일어나는 데이터에 맞는다. RDS 앞에 읽기 캐시가 필요하면 [DynamoDB.md](DynamoDB.md) 대신 ElastiCache나 DAX를 보는 게 보통이다.

DocumentDB는 MongoDB 호환이 필요한 문서 데이터일 때다. 스키마가 자주 바뀌는 콘텐츠나 프로필 데이터에 쓴다. 정형 데이터에 관계가 얽혀 있고 트랜잭션이 중요하면 그냥 RDS다.

대부분의 일반적인 백엔드 서비스는 RDS for MySQL/PostgreSQL이 기본값이고, 특별한 이유가 생길 때만 다른 걸 검토하는 순서가 사고 비용이 가장 적다.

## 참조

- AWS RDS 사용자 가이드: https://docs.aws.amazon.com/rds/
- RDS 모범 사례: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html
- Performance Insights: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html
- RDS 가격: https://aws.amazon.com/rds/pricing/
- 관련 문서: [Aurora_DB.md](Aurora_DB.md), [DB_Proxy.md](DB_Proxy.md)
