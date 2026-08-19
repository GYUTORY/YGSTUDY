---
title: RDS Blue/Green Deployment
tags: [aws, devops, mysql, postgresql]
updated: 2026-07-24
---

# RDS Blue/Green Deployment

운영 중인 RDS 인스턴스를 다운타임 없이 바꿔야 하는 상황이 있다. 메이저 버전 업그레이드, 대형 파라미터 변경, 대용량 테이블 DDL 작업이 그런 경우다. Blue/Green Deployment는 운영 인스턴스(blue)를 복제한 별도 환경(green)을 만들고, 거기서 변경을 먼저 적용해 검증한 뒤 DNS 교체로 트래픽을 넘기는 방식이다. RDS에서 2022년 말부터 지원한다.

## 1. 동작 방식

Blue/Green은 binlog 기반 복제로 돌아간다. green은 blue의 논리적 복제본으로 생성되고, 생성 이후에도 blue의 변경사항을 binlog로 계속 받아 적용한다. 애플리케이션은 switchover 전까지 blue만 바라보고, green은 뒤에서 따라잡으며 대기한다.

switchover는 DNS 엔드포인트 이름을 교체하는 방식으로 트래픽을 전환한다. blue의 엔드포인트(예: `mydb.xxxxx.ap-northeast-2.rds.amazonaws.com`)를 green이 가져가고, blue는 다른 이름으로 밀려난다. 애플리케이션 접속 문자열을 바꾸지 않아도 자동으로 green을 바라보게 된다.

```
[앱] → mydb.xxxxx.ap-northeast-2.rds.amazonaws.com (blue, MySQL 5.7)
                            ↓ binlog 복제
                     (green, MySQL 8.0)

switchover 후:

[앱] → mydb.xxxxx.ap-northeast-2.rds.amazonaws.com (green, MySQL 8.0)
         (옛 blue는 접미사가 붙은 이름으로 남음)
```

복제는 단방향이다. switchover 이후 green에 들어간 쓰기는 blue로 흘러가지 않는다. 이 점이 롤백 조건을 제약한다.

## 2. 생성 조건

Blue/Green Deployment를 쓰려면 blue 인스턴스에 binlog가 켜져 있어야 한다. binlog가 꺼진 상태면 green 생성 자체가 실패한다.

RDS에서 binlog가 활성화되려면 두 조건을 충족해야 한다. 첫째, 자동 백업 보존 기간(`backup_retention_period`)이 1일 이상이어야 한다. 이 값이 0이면 자동 백업이 꺼진 것이고, binlog도 켜지지 않는다. 둘째, `binlog_format` 설정이다. RDS for MySQL 은 `ROW`·`MIXED`·`STATEMENT` 셋 다 지원하지만, 복제 불일치 위험 때문에 `ROW` 를 쓰는 게 맞다. RDS 기본값이 `ROW` 라 보통 따로 손댈 일은 없다. RDS MySQL 기본값이 `ROW`라 보통 따로 건드릴 일은 없지만, 파라미터 그룹을 커스텀하게 관리하는 환경이라면 확인해둬야 한다.

```sql
-- blue 인스턴스에서 확인
SHOW VARIABLES LIKE 'binlog_format';
SHOW VARIABLES LIKE 'log_bin';
```

`log_bin`이 `ON`이고 `binlog_format`이 `ROW`나 `MIXED`이면 조건을 충족한다. `OFF`라면 `backup_retention_period`를 1 이상으로 수정하고 재시작해야 한다.

그 외 blue로 지정할 수 없는 케이스가 있다. Read Replica가 붙어있는 인스턴스, 이미 다른 Blue/Green Deployment의 green인 인스턴스, RDS on Outposts, `db.t2` 인스턴스 클래스는 사용할 수 없다.

## 3. Green 환경 생성과 검증

blue 인스턴스를 소스로 지정하고 Blue/Green Deployment를 만든다.

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name my-upgrade \
  --source arn:aws:rds:ap-northeast-2:123456789012:db:my-mysql57-db \
  --target-engine-version 8.0.35 \
  --target-db-parameter-group-name my-mysql80-pg
```

버전 업그레이드 없이 파라미터 변경이나 DDL만 적용하는 경우라면 `--target-engine-version`을 생략하거나 현재와 같은 버전을 지정하면 된다.

green 생성에는 수십 분이 걸린다. 데이터가 수백 GB 이상이면 한두 시간이 걸리기도 한다. 상태는 아래로 확인한다.

```bash
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier bgd-abc123
```

`Status`가 `AVAILABLE`로 바뀌면 green이 준비된 것이다. 이 시점부터 green 인스턴스에 직접 붙어서 테스트할 수 있다. 스테이징 애플리케이션을 green 엔드포인트에 연결해서 실제 쿼리를 돌려보는 것이 유일하게 믿을 수 있는 검증 방법이다.

switchover 전에 replica lag을 반드시 확인한다.

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=<green-instance-id> \
  --start-time 2026-07-24T02:00:00Z \
  --end-time 2026-07-24T02:30:00Z \
  --period 60 \
  --statistics Average
```

lag이 수 초 이내로 안정적인 상태에서 switchover를 진행한다.

## 4. Switchover 과정과 쓰기 중단

switchover를 실행하면 짧은 쓰기 중단이 발생한다. 대부분 30초~1분 안쪽으로 끝나지만 이유를 이해해야 시간을 예측할 수 있다.

```bash
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier bgd-abc123 \
  --switchover-timeout 300
```

switchover가 시작되면 이 순서로 진행된다.

1. blue에 쓰기를 차단한다. 이미 진행 중인 트랜잭션은 완료될 때까지 기다리고, 새 쓰기 트랜잭션은 받지 않는다.
2. green이 남은 binlog events를 모두 적용한다. lag이 0이 되는 시점까지 기다린다.
3. blue와 green의 데이터 일치를 확인한다.
4. DNS 엔드포인트 이름을 교체한다. RDS가 DNS TTL을 짧게 관리하지만, 기존 연결 풀이 캐시한 IP 주소를 버리고 재연결하는 시간이 필요하다.
5. green에서 쓰기를 다시 허용한다.

30초~1분이 걸리는 이유는 2번과 4번이다. replica lag이 전혀 없어도 DNS 전파와 클라이언트 재연결에 시간이 소요된다. lag이 남아있다면 그만큼 더 길어진다. 이래서 switchover 직전 lag을 최대한 줄이고, 쓰기 트래픽이 낮은 시간대에 실행하는 게 중요하다.

`--switchover-timeout` 시간 안에 완료되지 않으면 switchover가 취소되고 blue가 그대로 유지된다. 애플리케이션이 DB 연결 재시도 로직 없이 오류를 그대로 노출하는 구조라면, 이 30초~1분 동안 에러가 터진다. switchover 전에 재시도 로직을 반드시 확인해야 한다.

## 5. 롤백 가능 시점과 불가 시점

switchover가 끝나도 옛 blue 인스턴스는 살아 있다. 이름에 접미사가 붙은 채로 잠시 남아있어서, 이론상 되돌릴 수 있다.

롤백이 현실적인 시점은 switchover 직후 몇 분 안이다. green에 쌓인 데이터가 적어서 되돌릴 때의 데이터 손실 규모가 작다. 치명적인 오류가 switchover 직후 바로 터진다면 빠르게 판단해서 되돌릴 수 있다.

시간이 지나면 이야기가 달라진다. switchover 이후 green에 들어간 모든 쓰기가 blue로 복제되지 않는다. 한 시간 후에 되돌리면 그 한 시간치 데이터는 사라진다. 현실적으로 롤백이 아니라 green에서 문제를 직접 수정하는 쪽을 택하게 된다. 이래서 switchover 전 green에서의 충분한 검증이 진짜 안전장치다.

아예 롤백이 불가능한 시점은 Blue/Green Deployment 리소스를 삭제한 이후다. 삭제는 blue나 green 인스턴스를 지우는 게 아니라 배포 구성 자체를 정리하는 것인데, 이후에는 되돌릴 방법이 없다.

```bash
# Blue/Green Deployment 삭제 (green이 운영으로 자리잡은 뒤 정리)
# --delete-target 없이 실행하면 옛 blue 인스턴스는 남는다
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier bgd-abc123

# 옛 blue까지 완전 삭제할 때만 이 플래그를 붙인다
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier bgd-abc123 \
  --delete-target
```

며칠 동안 지표를 모니터링한 뒤 완전히 안정됐다고 판단될 때 `--delete-target`을 붙여서 정리하는 게 안전하다.

## 6. Multi-AZ 페일오버와의 차이

Multi-AZ와 Blue/Green은 DNS 교체라는 메커니즘은 같지만 목적과 동작이 다르다.

Multi-AZ 페일오버는 가용성 목적이다. primary에 장애가 생기면 standby가 자동으로 승격되고 DNS가 자동 교체된다. 사람이 트리거하는 게 아니다. primary와 standby는 항상 같은 엔진 버전과 스키마를 유지한다. standby는 읽기도 안 되는 완전한 대기 상태고, 페일오버 후 옛 primary는 새 standby가 된다.

Blue/Green Deployment는 변경 목적이다. switchover는 수동으로 실행한다. blue와 green이 서로 다른 엔진 버전, 파라미터, 스키마를 가질 수 있다. green에서 실제 애플리케이션을 연결해 검증하는 시간이 있고, switchover 이후 옛 blue가 남아서 롤백 여지를 준다.

| 항목 | Multi-AZ 페일오버 | Blue/Green Switchover |
|---|---|---|
| 목적 | 가용성 (장애 대응) | 변경 배포 (업그레이드, DDL) |
| 트리거 | 자동 (장애 감지 시) | 수동 |
| 엔진 버전 차이 | 불가 | 가능 |
| 검증 시간 | 없음 | switchover 전 green에서 검증 가능 |
| 쓰기 중단 | 1~2분 | 30초~1분 |
| 롤백 | 없음 | switchover 직후 일정 시간 가능 |

blue 인스턴스가 Multi-AZ 구성이면 green도 자동으로 Multi-AZ로 만들어진다.

## 7. 버전 업그레이드에 활용

메이저 버전 업그레이드를 Blue/Green으로 하는 이유는 검증 시간 확보다. 인플레이스 업그레이드는 시작하면 되돌리기 어렵다. Blue/Green은 green에서 버전을 올려두고 실제 쿼리를 돌려보면서 문제를 확인한 다음 전환한다.

### MySQL 5.7 → 8.0

MySQL 5.7 표준 지원이 2023년 10월 종료됐다. RDS 5.7 인스턴스는 extended support 비용이 추가로 붙는다. 8.0으로 올려야 하는데, 5.7→8.0이 MySQL 역사에서 가장 많이 깨지는 구간이다.

green 생성 시 8.0용 파라미터 그룹을 미리 만들어야 한다. 5.7과 8.0은 파라미터 그룹을 공유하지 못하고, 5.7에만 있는 파라미터를 8.0 그룹에 넣으면 적용이 거부된다.

| 파라미터 | 5.7 | 8.0 |
|---|---|---|
| `query_cache_type` | 존재 | 제거 (쿼리 캐시 자체가 없어짐) |
| `query_cache_size` | 존재 | 제거 |
| `innodb_file_format` | 존재 | 제거 |
| `innodb_large_prefix` | 존재 | 제거 |
| `tx_isolation` | 존재 | `transaction_isolation`으로 이름 변경 |

### DDL 호환성 이슈

**예약어**: 8.0에서 윈도우 함수 관련 키워드가 예약어로 추가됐다. `RANK`, `GROUPS`, `ROW`, `LATERAL`, `DENSE_RANK` 등을 컬럼명이나 테이블명으로 백틱 없이 써왔다면 8.0에서 오류가 난다.

```sql
-- 5.7 통과, 8.0 오류
SELECT rank FROM leaderboard ORDER BY rank;

-- 8.0에서는 백틱 필요
SELECT `rank` FROM leaderboard ORDER BY `rank`;

-- 스키마에서 예약어 충돌 컬럼 찾기
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME IN ('rank', 'groups', 'row', 'lateral', 'dense_rank', 'lead', 'lag')
  AND TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys');
```

컬럼명을 바꾸는 작업은 8.0 green 생성 전에 5.7에서 끝내는 게 낫다. 8.0에서 오류가 나는 상태로는 ALTER TABLE 자체가 안 돌기 때문이다.

**인증 플러그인**: 5.7 기본이 `mysql_native_password`, 8.0 기본이 `caching_sha2_password`다. 기존 계정은 `mysql_native_password`로 남지만, 오래된 드라이버(MySQL JDBC 5.1.x 등)가 `caching_sha2_password`를 처리하지 못한다.

```sql
-- 계정별 인증 플러그인 확인
SELECT user, host, plugin FROM mysql.user;

-- 필요시 기존 방식 유지 (임시 조치)
ALTER USER 'appuser'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
```

장기적으로는 드라이버를 올리고 `caching_sha2_password`로 이행해야 한다. MySQL Connector/J 8.0+, PyMySQL 1.0.2+, mysqlclient 2.1.0+ 이상이면 지원한다.

**제거된 함수**: `PASSWORD()`, `ENCODE()`, `DECODE()`, `ENCRYPT()` 함수가 8.0에서 삭제됐다. 코드베이스에서 직접 호출하는 곳을 찾아 수정해야 한다.

**ONLY_FULL_GROUP_BY**: 8.0에서 기본 활성화된다. `GROUP BY` 절에 없는 컬럼을 `SELECT`에 넣는 쿼리가 오류를 낸다. ORM이 생성하는 쿼리에도 이 패턴이 섞여 있는 경우가 있어서, green에서 실제 애플리케이션 쿼리를 돌려보기 전까지 모두 잡히지 않는다.

### 사전 점검

green 생성 전에 MySQL Shell로 호환성 문제를 확인할 수 있다.

```bash
mysqlsh --host=mydb.xxxxx.ap-northeast-2.rds.amazonaws.com \
  --user=admin --password \
  -- util checkForServerUpgrade
```

운영 인스턴스에 직접 돌리기 부담스러우면 스냅샷을 복원해서 별도 인스턴스를 만들고 거기서 돌리면 된다. `error` 수준 항목은 반드시 해결해야 하고, `warning`도 동작이 달라질 수 있어서 같이 봐야 한다.

## 8. 실제 운영 순서

스냅샷에서 복원한 임시 인스턴스에서 `checkForServerUpgrade`를 돌려 error/warning 목록을 파악한다. error 항목을 운영 DB에서 수정한다(예약어 컬럼명 변경, 제거된 함수 코드 수정, 드라이버 버전 업). 8.0용 파라미터 그룹을 만든다. Blue/Green Deployment를 생성하면 green이 8.0으로 올라온다. `AVAILABLE` 상태가 되면 green에 스테이징 애플리케이션을 붙여서 쿼리 오류, 인증 플러그인 문제, `ONLY_FULL_GROUP_BY` 위반 등을 확인한다. replica lag이 수 초 이내로 안정되면 트래픽이 낮은 시간대에 switchover를 실행한다. switchover 직후 30초~1분 동안 모니터링한다. 며칠간 green 지표를 보면서 이상이 없으면 Blue/Green Deployment를 삭제한다.

green에서 실제 쿼리를 돌려보는 단계가 가장 중요하다. 사전 점검 도구가 잡아내지 못하는 애플리케이션 레벨 호환성 문제는 여기서만 걸린다. switchover를 되돌리는 게 현실적으로 어렵다는 점을 감안하면, 전환 전 검증에 시간을 충분히 쓰는 게 낫다.
