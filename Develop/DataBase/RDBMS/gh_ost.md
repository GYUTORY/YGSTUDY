---
title: gh-ost
tags: [mysql, devops, rdbms, performance]
updated: 2026-08-06
---

# gh-ost

GitHub가 만든 MySQL Online Schema Change 도구다. 트리거 없이 binlog를 읽어서 행을 복사한다. 대용량 테이블 스키마 변경을 서비스 중단 없이 처리할 때 쓴다.

---

## triggerless 방식이 왜 중요한가

pt-online-schema-change(pt-osc)는 원본 테이블에 트리거를 심어서 변경분을 ghost 테이블로 동기화한다. 트리거 방식의 문제는 DML 하나에 트리거 실행이 붙어서 쓰기 부하가 거의 두 배가 된다는 점이다. 트래픽이 많은 테이블에서는 이 부하가 체감된다.

gh-ost는 트리거를 쓰지 않는다. 대신 MySQL의 binlog를 실시간으로 읽어서 원본 테이블에 생긴 변경사항을 ghost 테이블에 반영한다. 동작 순서는 다음과 같다.

```
1. ghost 테이블 생성: _원본테이블_gho
2. 청크 단위로 원본 → ghost 행 복사 (row copy)
3. 복사 중 발생한 binlog 이벤트를 ghost에 병렬 적용 (apply events)
4. 복사 완료 후 cut-over: 원본과 ghost를 atomic RENAME으로 교체
```

binlog를 직접 소비하기 때문에 gh-ost 프로세스는 MySQL 복제 슬레이브처럼 동작한다. binlog_format이 ROW 방식이어야 행 단위 변경 내용을 파싱할 수 있다.

```sql
-- 사전 확인
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
-- binlog_format이 ROW 여야 한다 (MIXED·STATEMENT 면 거부하고, --switch-to-rbr 을 줘야 전환한다)
-- STATEMENT이면 gh-ost가 거부한다
```

---

## pt-osc와의 차이

| 항목 | gh-ost | pt-osc |
|---|---|---|
| 변경 동기화 방식 | binlog 읽기 | 트리거 |
| 원본 테이블 부하 | 낮음 | 트리거 실행만큼 추가됨 |
| 외래키 처리 | 지원 안 함 | 제한적 지원 |
| 작업 제어 | 소켓 파일로 런타임 제어 | 없음 |
| cut-over | atomic RENAME (무중단) | 테이블 락 순간 발생 |
| Aurora 지원 | binlog 활성화 필요 | 상대적으로 쉬움 |
| 재시작 | --postpone-cut-over-flag-file로 일시 중단 후 재개 가능 | 처음부터 재실행 |

외래키가 있는 테이블에는 gh-ost를 쓸 수 없다. 이 경우 pt-osc나 MySQL Online DDL을 검토한다.

---

## 실행 모드 3가지

### connect-to-master

```bash
gh-ost \
  --host=master-host \
  --port=3306 \
  --user=gh-ost \
  --password=pass \
  --database=mydb \
  --table=orders \
  --alter="ADD COLUMN memo VARCHAR(500) NULL" \
  --execute
```

마스터에 직접 붙어서 binlog를 읽고, 행 복사도 마스터에서 한다. 레플리카가 없거나 구성이 단순한 환경에서 쓴다. 마스터에 읽기/쓰기 부하가 함께 걸린다.

### migrate-on-replica

```bash
gh-ost \
  --host=replica-host \
  --port=3306 \
  --user=gh-ost \
  --password=pass \
  --database=mydb \
  --table=orders \
  --alter="ADD COLUMN memo VARCHAR(500) NULL" \
  --master-host=master-host \
  --master-port=3306 \
  --execute
```

레플리카에 붙어서 binlog를 읽고, 행 복사도 레플리카에서 한다. 마스터 부하를 줄일 수 있다. cut-over 시에는 마스터에 RENAME을 실행하므로 마스터 접근 권한이 필요하다. 프로덕션에서 가장 많이 쓰는 모드다.

### test-on-replica

```bash
gh-ost \
  --host=replica-host \
  --port=3306 \
  --user=gh-ost \
  --password=pass \
  --database=mydb \
  --table=orders \
  --alter="ADD COLUMN memo VARCHAR(500) NULL" \
  --test-on-replica
```

레플리카에서만 작업하고, cut-over까지 레플리카 테이블에 적용한다. 마스터에 실제 변경은 반영되지 않는다. 스키마 변경 전에 레플리카에서 동작을 검증하는 용도로 쓴다. 완료 후 레플리카 복제를 재개하면 마스터의 원본 스키마가 다시 덮어씌워진다.

---

## 핵심 CLI 옵션

```bash
gh-ost \
  --host=master-host \
  --port=3306 \
  --user=gh-ost \
  --password=secret \
  --database=mydb \
  --table=orders \
  --alter="ADD COLUMN memo VARCHAR(500) NULL AFTER status" \
  \
  # 실행 제어
  --execute \                          # dry-run이 아닌 실제 실행
  --initially-drop-old-table \         # 이전 실행의 _del 테이블 있으면 삭제
  --initially-drop-ghost-table \       # 이전 실행의 _gho 테이블 있으면 삭제
  \
  # cut-over 제어
  --postpone-cut-over-flag-file=/tmp/gh-ost.postpone \  # 파일 있는 동안 cut-over 지연
  --cut-over-lock-timeout-seconds=3 \  # cut-over 락 타임아웃
  \
  # 부하 제어
  --chunk-size=1000 \                  # 한 번에 복사할 행 수
  --max-lag-millis=1500 \              # 레플리카 lag 임계값 (초과 시 throttle)
  --max-load=Threads_running=25 \      # 이 값 초과 시 throttle
  --critical-load=Threads_running=80 \ # 이 값 초과 시 즉시 중단
  \
  # 소켓 제어
  --serve-socket-file=/tmp/gh-ost.orders.sock \  # 런타임 제어 소켓
  \
  # 로깅
  --verbose
```

`--initially-drop-old-table`과 `--initially-drop-ghost-table`은 이전에 실패한 실행이 남긴 임시 테이블을 정리할 때 필요하다. 명시하지 않으면 이미 테이블이 있다고 에러를 낸다.

---

## cut-over 메커니즘

가장 민감한 단계다. 행 복사가 완료된 후 원본 테이블과 ghost 테이블을 교체한다.

gh-ost는 이를 두 개의 RENAME을 묶은 단일 트랜잭션으로 처리한다.

```sql
-- gh-ost 내부 동작 (단순화)
LOCK TABLES orders WRITE, _orders_gho WRITE;
RENAME TABLE orders TO _orders_del, _orders_gho TO orders;
UNLOCK TABLES;
```

락을 잡는 시간이 짧을수록 서비스 영향이 적다. `--cut-over-lock-timeout-seconds`를 3~5초로 설정하면, 이 시간 안에 RENAME을 완료하지 못하면 cut-over가 취소된다. 취소되더라도 데이터는 안전하다. ghost 테이블이 그대로 남아 있으므로 재시도가 가능하다.

cut-over 중 원본 테이블에 들어오는 쓰기는 LOCK TABLES 동안 잠깐 대기한다. 보통 수백 밀리초 안에 끝나지만, 트랜잭션이 오래 걸리는 환경에서는 더 길어질 수 있다.

### cut-over 지연 처리

배포 직전에 cut-over를 잠깐 막고 싶을 때 flag 파일을 쓴다.

```bash
# cut-over 지연 시작
touch /tmp/gh-ost.postpone

# 준비 완료 후 지연 해제
rm /tmp/gh-ost.postpone
# 파일이 사라지면 gh-ost가 cut-over를 진행한다
```

행 복사가 완료된 상태에서 flag 파일이 있으면 gh-ost는 cut-over를 하지 않고 binlog 이벤트만 계속 소비한다. 신규 변경분이 ghost 테이블에 계속 반영되므로, 지연 시간이 길어져도 데이터 정합성에 문제없다.

---

## throttling 설정

행 복사 속도가 너무 빠르면 레플리카 lag이 커지고, 마스터 CPU도 오른다. throttle은 gh-ost가 스스로 속도를 줄이는 메커니즘이다.

```bash
--max-lag-millis=1500          # 레플리카 lag이 1500ms 초과 시 일시 정지
--max-load=Threads_running=25  # MySQL의 Threads_running이 25 초과 시 일시 정지
--critical-load=Threads_running=80  # 80 초과 시 즉시 프로세스 종료
--throttle-control-replicas=replica-host:3306  # lag 체크 대상 레플리카 지정
--nice-ratio=0                 # 0이면 최대 속도, 1이면 복사 1ms마다 1ms 쉼
```

`--throttle-control-replicas`를 명시하지 않으면 gh-ost가 자동으로 레플리카를 찾아 lag을 확인한다. 레플리카가 여럿 있으면 가장 lag이 높은 것을 기준으로 삼는다.

런타임 중에 throttle을 수동으로 켤 수 있다.

```bash
# 즉시 정지
echo "throttle" | nc -U /tmp/gh-ost.orders.sock

# 재개
echo "no-throttle" | nc -U /tmp/gh-ost.orders.sock

# 청크 크기 변경
echo "chunk-size=500" | nc -U /tmp/gh-ost.orders.sock
```

---

## Aurora에서 binlog 활성화

Aurora MySQL은 binlog가 기본으로 꺼져 있다. gh-ost는 binlog가 없으면 실행 자체가 안 된다.

파라미터 그룹에서 `binlog_format`을 ROW로 설정해야 한다.

```
Aurora 파라미터 그룹 설정:
  binlog_format = ROW
  (클러스터 파라미터 그룹이 아닌 DB 파라미터 그룹에 설정)
```

설정 후 인스턴스를 재시작해야 반영된다. 재시작 없이는 `log_bin`이 OFF 상태로 유지된다.

```sql
-- 활성화 여부 확인
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW MASTER STATUS;  -- binlog 파일과 포지션이 나오면 활성화된 것
```

Aurora는 binlog 보존 기간도 별도로 설정해야 한다. 기본값이 0이면 binlog가 즉시 삭제된다. gh-ost 실행 중에 필요한 binlog가 삭제되면 작업이 실패한다.

```sql
-- Aurora binlog 보존 시간 설정 (단위: 시간)
CALL mysql.rds_set_configuration('binlog retention hours', 24);

-- 현재 설정 확인
CALL mysql.rds_show_configuration;
```

gh-ost 실행 시간이 긴 작업이라면 보존 시간을 여유 있게 설정한다. 수억 행짜리 테이블은 하루 이상 걸릴 수 있다.

---

## 진행 상황 확인

gh-ost는 실행 중에 상태를 두 가지 방법으로 노출한다.

### 소켓으로 확인

```bash
echo "status" | nc -U /tmp/gh-ost.orders.sock
```

출력 예시:

```
# Migrating mydb.orders; Ghost table is mydb._orders_gho
# Migrating master; inspecting replica replica-host:3306
# Migration started at 2026-08-06 14:00:00
# chunk-size: 1000; max-lag-millis: 1500; max-load: map[Threads_running:25]
# Lag: 0ms
# ETA: 2h15m
# Progress: 45.32%; copied 45320000/100000000 rows
# Throttle: no
```

### 로그 파일 확인

```bash
# 실행 시 로그 파일 지정
gh-ost ... --verbose 2>&1 | tee /var/log/gh-ost-orders.log

# 실시간 확인
tail -f /var/log/gh-ost-orders.log | grep -E "(Copy|lag|Throttle|ETA)"
```

Progress 퍼센트는 테이블의 PRIMARY KEY 범위를 기준으로 계산한다. 행이 균일하게 분포하지 않으면 퍼센트와 실제 남은 행 수가 맞지 않을 수 있다. ETA도 참고 수치로만 봐야 한다.

---

## 작업 중단과 재시작

gh-ost는 중간에 Ctrl+C나 SIGTERM으로 종료해도 안전하다. ghost 테이블(`_orders_gho`)이 그대로 남아 있다.

재시작 시에는 처음부터 행을 복사하는 게 기본 동작이다. 하지만 ghost 테이블이 남아 있으면 gh-ost가 에러를 낸다.

```bash
# 이미 ghost 테이블이 있는 경우
gh-ost ... --initially-drop-ghost-table --execute
# 이 옵션을 쓰면 ghost 테이블을 삭제하고 처음부터 다시 시작한다
```

처음부터 다시 시작하는 게 부담스러울 만큼 작업이 많이 진행됐다면, ghost 테이블을 건드리지 않고 재개하는 방법은 없다. gh-ost는 체크포인트 재개를 지원하지 않는다. 행 복사 위치를 내부에서 binlog 포지션과 맞춰가기 때문에, 중간 재개 시 데이터 정합성을 보장하기 어렵다고 판단한 설계다.

작업 후 남는 임시 테이블:

```sql
-- 작업 완료 후 자동 이름 변경된 원본 테이블 (삭제 대상)
SHOW TABLES LIKE '%_del';
-- _orders_del 테이블이 남아 있다. 문제 없으면 DROP TABLE로 정리한다
DROP TABLE _orders_del;
```

---

## 실무에서 자주 겪는 문제

### row log 버퍼 초과

gh-ost는 행 복사 중 발생한 binlog 이벤트를 내부 버퍼에 쌓아두고, 주기적으로 ghost 테이블에 반영한다. 이 버퍼는 메모리에 올라간다. 트래픽이 매우 높은 환경에서 장시간 실행하면 gh-ost 프로세스 메모리 사용량이 급격히 오른다.

완화 방법은 `--chunk-size`를 줄여서 행 복사 속도를 낮추거나, throttle을 걸어 binlog 이벤트 발생 속도 대비 소비 속도를 맞추는 것이다.

MySQL Online DDL의 `innodb_online_alter_log_max_size`와는 다른 개념이다. gh-ost는 MySQL 내부 버퍼가 아닌 자체 프로세스 메모리에 이벤트를 쌓는다.

```bash
# 청크 크기를 줄여 binlog 이벤트 발생 속도를 낮춤
echo "chunk-size=200" | nc -U /tmp/gh-ost.orders.sock
```

### cut-over 타이밍

cut-over가 되는 순간 원본 테이블에 LOCK TABLES가 걸린다. 이 타이밍에 장기 트랜잭션이 실행 중이면 cut-over가 지연된다. `--cut-over-lock-timeout-seconds`를 넘기면 cut-over가 취소되고 gh-ost는 다음 기회를 기다린다.

트랜잭션이 짧은 시간대(야간 배치 이전 등)를 노려야 cut-over가 깔끔하게 끝난다.

```bash
# cut-over 전에 현재 트랜잭션 상황 확인
mysql -e "SELECT trx_id, trx_started, TIMESTAMPDIFF(SECOND, trx_started, NOW()) sec
          FROM information_schema.innodb_trx ORDER BY sec DESC LIMIT 10;"
```

긴 트랜잭션이 있다면 flag 파일로 cut-over를 지연시키고, 트랜잭션이 끝난 후 파일을 삭제해서 cut-over를 유도하는 방식이 현실적이다.

### Replica lag

`--max-lag-millis`를 넘기면 gh-ost가 자동으로 행 복사를 멈춘다. 문제는 throttle이 걸리고 나서 lag이 줄어들기까지 시간이 걸리고, 그 사이에도 binlog 이벤트는 계속 들어온다는 점이다.

lag 임계값을 너무 낮게 설정하면 throttle이 자주 걸려서 작업 완료 시간이 크게 늘어난다. 1500ms~3000ms 사이로 설정하고, 실제 레플리카 상태를 보면서 조정하는 것이 좋다.

레플리카 lag이 구조적으로 큰 환경이라면 migrate-on-replica 모드를 써서 레플리카에서 행 복사를 처리하면 마스터 부하 자체를 줄일 수 있다.

```bash
# lag 상태 모니터링
watch -n 2 "mysql -h replica-host -e 'SHOW SLAVE STATUS\G' | grep Seconds_Behind_Master"
```

---

## 권한 설정

gh-ost 전용 계정에 최소 권한을 준다.

```sql
CREATE USER 'gh-ost'@'%' IDENTIFIED BY 'strong-password';

GRANT ALTER, CREATE, DELETE, DROP, INDEX, INSERT,
      LOCK TABLES, SELECT, TRIGGER, UPDATE
ON mydb.* TO 'gh-ost'@'%';

-- binlog 읽기 권한 (REPLICATION SLAVE + REPLICATION CLIENT)
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'gh-ost'@'%';

FLUSH PRIVILEGES;
```

REPLICATION SLAVE가 없으면 gh-ost가 binlog 스트림을 열지 못한다. 계정 생성 후 반드시 확인한다.
