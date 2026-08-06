---
title: pt-online-schema-change
tags: [mysql, pt-osc, online-schema-change, percona, trigger, shadow-table, migration, aurora, galera, throttling, replica]
updated: 2026-08-06
---

# pt-online-schema-change

Percona Toolkit에 포함된 MySQL 온라인 스키마 변경 도구다. 원본 테이블에 INSERT/UPDATE/DELETE 트리거를 심어서 shadow 테이블과 변경분을 동기화하고, 데이터 복사가 끝나면 테이블을 교체한다. binlog 없이 동작하고 외래키 처리 옵션이 있다는 점이 gh-ost와 다르다.

---

## 트리거 기반 동작 원리

pt-osc는 스키마 변경을 다음 순서로 처리한다.

```
1. shadow 테이블 생성: _원본테이블_new
2. 원본 테이블에 AFTER INSERT / AFTER UPDATE / AFTER DELETE 트리거 3개 설치
3. 청크 단위로 원본 → shadow 행 복사 (row copy)
4. 복사 중 발생한 DML은 트리거가 shadow 테이블에 실시간 반영
5. 복사 완료 후 RENAME으로 테이블 교체
6. 트리거 제거, 원본 테이블은 _원본테이블_old로 보존
```

트리거가 변경분을 처리하는 내부 로직은 이렇다.

```sql
-- pt-osc가 내부적으로 생성하는 트리거 (단순화)
CREATE TRIGGER pt_osc_orders_ins AFTER INSERT ON orders
FOR EACH ROW
  REPLACE INTO _orders_new (...) VALUES (...);

CREATE TRIGGER pt_osc_orders_upd AFTER UPDATE ON orders
FOR EACH ROW
  REPLACE INTO _orders_new (...) VALUES (...);

CREATE TRIGGER pt_osc_orders_del AFTER DELETE ON orders
FOR EACH ROW
  DELETE FROM _orders_new WHERE id = OLD.id;
```

DML 하나에 트리거 실행이 따라붙는다. INSERT 한 건이 들어오면 원본 테이블에 INSERT 한 번, shadow 테이블에 REPLACE 한 번이 실행된다. 쓰기 트래픽이 높은 테이블에서 부하가 체감되는 이유가 여기 있다.

테이블에 이미 트리거가 있으면 기본 설정으로 실행을 거부한다. MySQL 5.7 이하에서는 같은 이벤트에 트리거를 여러 개 달 수 없기 때문이다. MySQL 8.0부터는 multiple trigger를 지원하지만 pt-osc는 기존 트리거가 있으면 경고를 낸다.

---

## DSN 포맷

pt-osc는 DSN(Data Source Name) 형식으로 접속 정보를 받는다.

```bash
# 기본 형식
pt-online-schema-change h=host,u=user,p=pass,D=database,t=table \
  --alter "..." --execute
```

DSN 키 목록:

| 키 | 설명 |
|---|---|
| h | 호스트명 또는 IP |
| P | 포트 (기본 3306) |
| u | 사용자 |
| p | 비밀번호 |
| D | 데이터베이스 |
| t | 테이블명 |
| S | 소켓 파일 경로 |

비밀번호에 특수문자가 있으면 DSN 파싱이 깨진다. `~/.my.cnf`에 분리해서 관리하는 편이 안전하다.

```ini
# ~/.my.cnf
[pt-online-schema-change]
user=pt-osc
password=p@ssw0rd!special
```

---

## 핵심 CLI 옵션

```bash
pt-online-schema-change \
  h=master-host,u=pt-osc,p=secret,D=mydb,t=orders \
  --alter "ADD COLUMN memo VARCHAR(500) NULL AFTER status" \
  \
  --execute \                        # dry-run이 아닌 실제 실행
  --no-drop-old-table \              # 완료 후 _orders_old를 자동 삭제하지 않음
  --no-drop-new-table \              # 실패 시 _orders_new를 삭제하지 않음
  \
  --chunk-size=1000 \                # 한 번에 복사할 행 수
  --chunk-size-limit=4 \             # chunk-size의 N배 초과 시 해당 청크 경고
  --sleep=0.1 \                      # 각 청크 사이 대기 시간 (초)
  \
  --max-lag=1s \                     # 레플리카 lag 임계값 (초과 시 일시 정지)
  --max-load "Threads_running=25" \  # 이 값 초과 시 일시 정지
  --critical-load "Threads_running=80" \  # 이 값 초과 시 즉시 중단
  \
  --alter-foreign-keys-method=rebuild_constraints \  # 외래키 shadow 기준 재생성
  \
  --progress time,30 \              # 30초마다 진행 상황 출력
  --statistics \                    # 완료 후 통계 출력
  --print                           # 실행할 SQL 출력
```

`--execute` 없이 `--dry-run`을 쓰면 실제 변경 없이 실행 가능 여부만 확인한다. 트리거 충돌이나 권한 문제를 미리 잡을 수 있다.

```bash
pt-online-schema-change \
  h=master-host,u=pt-osc,p=secret,D=mydb,t=orders \
  --alter "ADD COLUMN memo VARCHAR(500) NULL" \
  --dry-run
```

---

## chunk 크기와 throttle

기본 청크 크기는 1000이다. 실무에서는 500~2000 사이에서 시작해 DB 부하를 보며 조정한다. VARCHAR, TEXT, BLOB 컬럼이 많은 테이블은 청크 하나의 데이터 크기가 크므로 줄여야 한다.

```bash
--chunk-size=500    # 보수적 시작
--chunk-size=2000   # 여유가 있을 때
```

`--sleep`으로 청크 사이 대기를 준다. 0.1초면 초당 최대 10개 청크 복사다. 야간이나 DB 여유가 충분하면 0으로 줄여도 된다.

`--max-load`와 `--critical-load`는 MySQL 상태 변수를 기준으로 throttle을 건다.

```bash
--max-load "Threads_running=25"         # 초과 시 청크 복사 일시 정지
--critical-load "Threads_running=80"    # 초과 시 즉시 프로세스 종료
```

`critical-load`에 걸려 종료되면 shadow 테이블과 트리거가 남는다. 재실행 전에 수동으로 정리해야 한다.

---

## replica lag 처리

`--max-lag`은 `SHOW SLAVE STATUS`의 `Seconds_Behind_Master`를 읽어서 lag을 확인한다. 임계값을 초과하면 청크 복사를 멈추고 내려오면 재개한다.

```bash
--max-lag=1s

# 핵심 레플리카를 명시적으로 지정
--check-slave-lag h=replica1.internal,P=3306
```

`--check-slave-lag`을 명시하지 않으면 pt-osc가 자동으로 레플리카를 찾는다. 자동 탐지가 잘못 동작하는 경우가 있으므로, 모니터링하는 레플리카는 명시적으로 지정하는 편이 안전하다.

`Seconds_Behind_Master`가 NULL을 반환하면 pt-osc는 lag을 0으로 간주한다. 레플리카 복제가 중단된 상태인데도 복사가 계속 진행된다. pt-osc 실행 중에는 레플리카 상태를 별도로 모니터링해야 한다.

```bash
# 실행 중 레플리카 lag 감시
watch -n 2 "mysql -h replica-host -e 'SHOW SLAVE STATUS\G' | grep Seconds_Behind_Master"
```

---

## 진행 상황 모니터링

pt-osc는 표준 출력으로 진행률을 출력한다.

```
Copying `mydb`.`orders`: 43% 00:12:34 remain
Copying `mydb`.`orders`: 44% 00:12:01 remain
```

로그 파일로 저장해서 모니터링한다.

```bash
pt-online-schema-change \
  h=master-host,u=pt-osc,p=secret,D=mydb,t=orders \
  --alter "ADD COLUMN memo VARCHAR(500) NULL" \
  --execute \
  --progress time,30 \
  2>&1 | tee /var/log/pt-osc-orders.log

# 실시간 확인
tail -f /var/log/pt-osc-orders.log
```

`--progress` 옵션:

| 값 | 의미 |
|---|---|
| `time,N` | N초마다 출력 |
| `percentage,N` | N% 마다 출력 |
| `iterations,N` | N개 청크마다 출력 |

별도 터미널에서 shadow 테이블 행 수를 직접 세서 진행률을 확인할 수도 있다.

```sql
-- 원본 테이블 추정 행 수 (빠름, 정확하지 않음)
SELECT TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mydb' AND TABLE_NAME = 'orders';

-- shadow 테이블 실제 행 수 (느림, 정확함)
SELECT COUNT(*) FROM _orders_new;
```

진행률 퍼센트는 PRIMARY KEY 범위를 기준으로 계산한다. 행이 균일하게 분포하지 않으면 퍼센트와 실제 남은 행 수가 맞지 않을 수 있다.

---

## 외래키 처리

pt-osc는 외래키가 걸린 테이블도 처리할 수 있다. gh-ost와 다른 점이다.

```bash
--alter-foreign-keys-method=rebuild_constraints   # 권장
--alter-foreign-keys-method=drop_swap             # 빠르지만 정합성 위험
--alter-foreign-keys-method=none                  # 외래키 무시 (정합성 깨짐)
--alter-foreign-keys-method=auto                  # pt-osc가 방법 자동 선택
```

`rebuild_constraints`는 shadow 테이블 교체 시 자식 테이블의 외래키를 새 테이블 기준으로 재생성한다. 자식 테이블 수가 많으면 이 과정에서 시간이 걸린다.

`drop_swap`은 외래키를 삭제하고 테이블을 교체한 뒤 외래키를 다시 건다. 짧은 순간 참조 무결성이 깨진 상태가 된다. 해당 순간에 관련 트랜잭션이 없다는 확신이 있을 때만 쓴다.

---

## 오류 복구

작업이 중간에 실패하면 shadow 테이블(`_orders_new`)과 트리거 3개가 남는다.

```sql
-- 남은 트리거 확인
SHOW TRIGGERS IN mydb LIKE 'pt_osc_%';

-- 남은 테이블 확인
SHOW TABLES IN mydb LIKE '%_new';
SHOW TABLES IN mydb LIKE '%_old';
```

재실행 전에 수동으로 정리한다.

```sql
-- 트리거 삭제
DROP TRIGGER IF EXISTS mydb.pt_osc_orders_ins;
DROP TRIGGER IF EXISTS mydb.pt_osc_orders_upd;
DROP TRIGGER IF EXISTS mydb.pt_osc_orders_del;

-- shadow 테이블 삭제
DROP TABLE IF EXISTS mydb._orders_new;
```

정리 후 재실행하면 처음부터 다시 시작한다. pt-osc는 중간 재개를 지원하지 않는다. 행 복사가 많이 진행된 상태에서 실패했다면 처음부터 다시 돌려야 한다.

작업 완료 후 남는 임시 테이블도 직접 정리한다.

```sql
-- 완료 후 보존된 원본 테이블 삭제 (문제 없음을 확인 후)
SHOW TABLES LIKE '%_old';
DROP TABLE IF EXISTS mydb.orders_old;
```

`--no-drop-old-table`을 쓰지 않았다면 pt-osc가 자동으로 삭제한다. 롤백 여지를 남기려면 이 옵션을 붙이고, 정상 동작 확인 후 수동으로 삭제한다.

---

## Aurora 환경 제약

Aurora MySQL에서 pt-osc는 binlog 없이 동작한다. 트리거 기반이라 binlog 설정이 필요 없다.

레플리카 lag 확인에 주의가 필요하다. `Seconds_Behind_Master`는 Aurora에서 항상 신뢰하기 어렵다. Aurora의 실제 복제 지연은 CloudWatch의 `AuroraReplicaLag` 메트릭이 정확하다.

```bash
# Aurora Reader 엔드포인트를 직접 지정
--check-slave-lag h=aurora-reader.cluster.rds.amazonaws.com,P=3306
```

Aurora Serverless v1에서는 pt-osc 사용을 피해야 한다. Auto Pause 기능이 활성화된 상태에서 트리거가 예상대로 동작하지 않는 사례가 있다. Aurora Serverless v2는 일반 Aurora와 동일하게 동작한다.

---

## Galera Cluster 환경 제약

Percona XtraDB Cluster나 MariaDB Galera Cluster 환경에서는 추가 옵션이 필요하다.

Galera는 DDL을 클러스터 전체에 동기로 전파한다. pt-osc의 트리거 생성/삭제, shadow 테이블 생성/삭제 모두 DDL이기 때문에 클러스터 전체에 영향을 준다.

```bash
--no-check-replication-filters   # Galera는 binlog 필터 방식이 다름
--no-version-check               # 버전 호환성 경고 무시
```

Galera의 `wsrep_OSU_method`가 TOI(Total Order Isolation)로 설정되어 있으면 DDL 실행 시 클러스터 전체 노드가 잠깐 멈춘다. RSU(Rolling Schema Upgrade)로 바꾸면 노드별 순차 적용이 가능하지만, pt-osc가 스키마 불일치 상태에서 동작해야 해서 설정이 복잡해진다.

Galera 환경에서는 pt-osc보다 MariaDB의 Instant DDL이나 백업 후 복원 방식을 먼저 검토한다.

---

## 트리거 충돌 트러블슈팅

원본 테이블에 이미 트리거가 있을 때 pt-osc는 기본 설정으로 실행을 거부한다.

```
Error: Table `mydb`.`orders` has triggers which pt-online-schema-change cannot handle.
Triggers:
  `orders_audit_trigger` (AFTER INSERT)
```

MySQL 5.7 이하에서는 같은 이벤트에 트리거 두 개를 달 수 없다. pt-osc가 AFTER INSERT 트리거를 달려는데 이미 AFTER INSERT 트리거가 있으면 충돌한다.

```sql
-- 기존 트리거 목록과 실행 순서 확인
SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_TIMING, ACTION_ORDER
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = 'mydb' AND EVENT_OBJECT_TABLE = 'orders'
ORDER BY ACTION_ORDER;
```

현실적인 해결 방법은 두 가지다.

첫째, 기존 트리거를 일시 제거하고 pt-osc를 실행한 다음 다시 붙인다. 트리거가 감사 로그나 비즈니스 로직에 연결되어 있으면 제거한 사이에 들어온 이벤트가 누락된다. 서비스 점검 시간이 없으면 쓸 수 없다.

둘째, pt-osc 대신 gh-ost나 MySQL Online DDL을 쓴다. gh-ost는 트리거를 사용하지 않으므로 기존 트리거와 충돌하지 않는다.

MySQL 8.0에서는 같은 이벤트에 트리거를 여러 개 달 수 있지만, pt-osc 트리거와 기존 트리거의 실행 순서가 맞물리면 예상치 못한 결과가 생긴다. 기존 트리거가 있는 테이블에서 pt-osc를 쓸 때는 트리거 실행 순서를 반드시 검증한다.

---

## gh-ost와 실무 선택 기준

| 상황 | 선택 |
|---|---|
| 외래키 없음, binlog ROW 모드, 레플리카 있음 | gh-ost |
| 외래키 있음 | pt-osc |
| binlog 없음 또는 STATEMENT 모드 | pt-osc |
| 원본 테이블에 기존 트리거 있음 | gh-ost |
| cut-over를 flag 파일로 정밀 제어해야 함 | gh-ost |
| 레플리카 없는 단순 환경 | pt-osc |
| Aurora Serverless v1 | MySQL Online DDL 검토 |
| Galera Cluster | 별도 검토 |

binlog ROW 모드를 쓰고 레플리카가 있고 외래키가 없다면 gh-ost가 낫다. 트리거 없이 동작하고 런타임 제어가 세밀하다.

pt-osc는 binlog 의존성이 없고 설정이 단순하다. binlog 설정을 바꿀 수 없는 환경, 외래키가 있는 테이블, 레플리카 없는 환경에서 선택한다.

두 도구 모두 테이블 교체 직전에 짧은 락이 발생한다. 완전히 무중단은 아니다. 락 시간을 줄이려면 장기 트랜잭션이 없는 시간대에 cut-over를 유도해야 한다.

---

## 권한 설정

```sql
CREATE USER 'pt-osc'@'%' IDENTIFIED BY 'strong-password';

GRANT ALTER, CREATE, DELETE, DROP, INDEX, INSERT,
      LOCK TABLES, SELECT, TRIGGER, UPDATE
ON mydb.* TO 'pt-osc'@'%';

-- 레플리카 lag 확인 (SHOW SLAVE STATUS)
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'pt-osc'@'%';

FLUSH PRIVILEGES;
```

TRIGGER 권한이 없으면 트리거를 설치하지 못해 실행 초반에 실패한다. REPLICATION CLIENT는 `SHOW SLAVE STATUS` 실행에 필요하다.
