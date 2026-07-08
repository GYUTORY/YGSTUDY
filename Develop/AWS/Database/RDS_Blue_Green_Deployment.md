---
title: RDS Blue/Green Deployment로 MySQL 5.7 → 8.0 업그레이드
tags: [aws, rds, mysql, blue-green, upgrade, switchover, ddl, compatibility]
updated: 2026-07-08
---

# RDS Blue/Green Deployment로 MySQL 5.7 → 8.0 업그레이드

MySQL 5.7의 표준 지원은 2023년 10월 종료됐다. RDS 5.7 인스턴스는 extended support로 자동 전환되고, 해당 기간 동안 인스턴스 비용에 vCPU당 추가 요금이 붙는다. 결국 8.0으로 올려야 한다.

문제는 5.7 → 8.0이 MySQL 역사에서 가장 많이 깨지는 구간이라는 점이다. 예약어가 늘었고, 파라미터 여러 개가 사라졌고, 인증 플러그인 기본값이 바뀌었다. 단순히 버전 번호를 올리는 수준이 아니라 동작이 실제로 달라진다.

RDS는 2022년부터 Blue/Green Deployment를 지원한다. 운영 인스턴스(blue)를 복제한 별도 환경(green)을 만들고, 거기서 먼저 8.0으로 올려 검증한 다음 switchover로 트래픽을 넘기는 방식이다. 다운타임을 최소화하면서 롤백 여지를 남길 수 있다.

---

## 1. RDS Blue/Green Deployment 동작 방식

Blue/Green은 운영 DB 인스턴스(blue)를 소스로 삼아 green을 만든다. green은 blue의 논리적 복제본으로, binlog 기반 복제로 blue의 변경을 계속 따라잡는다. green이 완성된 뒤에도 애플리케이션은 blue만 바라본다. green은 뒤에서 binlog를 받아 적용하며 대기한다.

switchover는 DNS 엔드포인트 이름을 교체하는 방식으로 트래픽을 전환한다. blue의 엔드포인트 이름(예: `mydb.xxxxx.ap-northeast-2.rds.amazonaws.com`)을 green이 가져가고, blue는 다른 이름으로 밀려난다. 애플리케이션 접속 문자열을 바꾸지 않아도 자동으로 green을 바라보게 된다.

```
[앱] → mydb.xxxxx.ap-northeast-2.rds.amazonaws.com (blue, MySQL 5.7)
                                ↓ binlog 복제
                         (green, MySQL 8.0)

switchover 후:

[앱] → mydb.xxxxx.ap-northeast-2.rds.amazonaws.com (green, MySQL 8.0)
                                ↓ (옛 blue는 다른 이름으로 남음)
```

blue에서 green으로 이어지는 복제는 단방향이다. switchover 이후 green에 들어간 쓰기는 blue로 흘러가지 않는다. 이 점이 롤백 조건과 직결된다.

---

## 2. green 환경 생성

blue 인스턴스를 지정해서 Blue/Green Deployment를 만든다. 이때 green의 엔진 버전을 8.0으로 지정한다.

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name mysql80-upgrade \
  --source arn:aws:rds:ap-northeast-2:123456789012:db:my-mysql57-db \
  --target-engine-version 8.0.35 \
  --target-db-parameter-group-name my-mysql80-pg
```

`--target-db-parameter-group-name`은 8.0용 파라미터 그룹을 미리 만들어서 지정해야 한다. 5.7 그룹을 그대로 쓸 수 없다. 8.0에서 제거된 파라미터가 포함돼 있으면 green 생성이 실패하거나 적용 도중 오류가 난다.

green 생성에는 보통 수십 분이 걸린다. 인스턴스 크기와 데이터 양에 따라 다르다. RDS 콘솔이나 CLI로 상태를 확인한다.

```bash
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier bgd-abc123
```

`Status`가 `AVAILABLE`이 되면 green이 준비된 것이다.

binlog 복제가 동작하려면 blue 인스턴스에 `binlog_format`이 설정돼 있어야 한다. RDS에서는 `ROW` 또는 `MIXED`로 잡아야 한다. 5.7 기본값이 `MIXED`라 대부분 별도 설정 없이 된다. 확인만 해두면 된다.

```sql
SHOW VARIABLES LIKE 'binlog_format';
```

---

## 3. 컷오버 타이밍

switchover는 replica lag이 0에 수렴한 상태에서 해야 한다. lag이 크면 switchover 동안 green이 남은 binlog를 모두 적용할 때까지 쓰기가 막히고, 그 시간이 다운타임이 된다.

```bash
# replica lag 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=green-instance-id \
  --start-time 2026-07-08T10:00:00Z \
  --end-time 2026-07-08T10:30:00Z \
  --period 60 \
  --statistics Average
```

lag이 수 초 이내로 안정적이면 switchover를 진행한다. 피크 트래픽이 몰리는 시간대는 피하는 게 낫다. 쓰기가 많을수록 lag이 순간적으로 튀고, 그만큼 switchover 중 대기 시간이 늘어난다.

```bash
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier bgd-abc123 \
  --switchover-timeout 300
```

`--switchover-timeout`은 초 단위다. 이 시간 안에 switchover가 끝나지 않으면 취소되고 blue가 그대로 유지된다. 300초(5분)이면 충분한 편이지만, lag이 크거나 데이터가 아주 많다면 더 넉넉하게 잡아야 한다.

switchover 과정:
1. blue에 쓰기 차단
2. green이 남은 binlog 전부 적용
3. 데이터 일치 확인
4. DNS 엔드포인트 이름 교체
5. 쓰기 재개 (green에서)

이 사이클이 보통 1분 안쪽에 끝난다. 짧은 연결 끊김이 발생하므로 애플리케이션이 재연결 로직을 갖추고 있어야 한다.

---

## 4. 롤백 조건

switchover 직후 옛 blue 인스턴스는 `old1` 접미사가 붙은 이름으로 살아 있다. 여기서 치명적인 문제가 발견되면 blue로 트래픽을 되돌릴 수는 있다. 단, 이때 switchover 이후 green에 들어간 쓰기는 blue에 없다. 되돌리면 그 데이터는 잃는다.

현실적으로 롤백이 안전한 시간은 switchover 직후 몇 분이다. 이 안에 치명적인 애플리케이션 오류를 확인하고 결정해야 한다. 시간이 지나 green에 데이터가 쌓이면 되돌리기보다는 green에서 문제를 수정하는 게 낫다.

롤백을 실행하기보다는 switchover 전 green에서 충분히 검증하는 것이 실제로 유효한 안전장치다. green에 읽기 트래픽 일부를 먼저 보내거나, 스테이징 애플리케이션을 green에 연결해서 회귀 테스트를 돌려보는 방식으로 쓴다.

---

## 5. MySQL 5.7 → 8.0 DDL 호환성 이슈

업그레이드 전 사전 점검에서 잡아내지 못하면 green 생성 단계에서 막히거나, 애플리케이션이 올라간 뒤 쿼리가 깨진다.

### 5.1 예약어 충돌

8.0에서 새로 예약어가 된 단어들이 있다. `RANK`, `GROUPS`, `ROW`, `LATERAL`, `SYSTEM`, `CUME_DIST`, `DENSE_RANK`, `PERCENT_RANK` 같은 윈도우 함수 관련 키워드가 대표적이다. 이 단어를 테이블명이나 컬럼명으로 백틱 없이 써왔다면 8.0에서 문법 오류가 난다.

```sql
-- 5.7에서는 통과, 8.0에서 오류
SELECT rank FROM leaderboard ORDER BY rank;

-- 백틱으로 감싸야 한다
SELECT `rank` FROM leaderboard ORDER BY `rank`;
```

스키마에 이런 컬럼명이 박혀 있으면 컬럼명을 바꾸거나 쿼리를 전부 백틱 처리해야 한다. 어떤 테이블에 충돌하는 컬럼이 있는지 확인하는 쿼리를 돌려보면 된다.

```sql
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME IN (
  'rank', 'groups', 'row', 'lateral', 'system',
  'cume_dist', 'dense_rank', 'percent_rank', 'first_value',
  'last_value', 'nth_value', 'ntile', 'lead', 'lag'
)
AND TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys');
```

컬럼명을 바꾸는 작업은 8.0으로 올린 다음이 아니라 5.7에서 미리 끝내는 게 낫다. 8.0에서 오류가 나는 상태로는 ALTER TABLE 자체가 안 돌기 때문이다.

### 5.2 인증 플러그인 변경

5.7의 기본 인증 플러그인은 `mysql_native_password`다. 8.0은 `caching_sha2_password`로 바뀌었다. 업그레이드 전에 만들어진 사용자 계정은 `mysql_native_password`로 남아 있어서 8.0에서 그대로 동작한다. 문제는 기존 드라이버나 커넥터가 `caching_sha2_password`를 지원하지 않는 경우다.

오래된 MySQL JDBC 드라이버(5.1.x)나 PHP `mysql_` 확장(이미 deprecated) 같은 구버전 클라이언트는 `caching_sha2_password` 핸드셰이크를 처리하지 못한다. 8.0으로 올리면서 새로 만드는 계정은 `caching_sha2_password`가 기본이라, 신규 계정이 생기는 곳에서 연결이 실패한다.

```sql
-- 계정별 인증 플러그인 확인
SELECT user, host, plugin FROM mysql.user;

-- 필요하다면 명시적으로 native password 유지
ALTER USER 'appuser'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
```

운영에서 쓰는 드라이버 버전이 `caching_sha2_password`를 지원하는지 먼저 확인해야 한다. MySQL Connector/J 8.0+, PyMySQL 1.0.2+, mysqlclient 2.1.0+ 등은 지원한다.

### 5.3 제거된 함수

8.0에서 `PASSWORD()`, `ENCODE()`, `DECODE()`, `ENCRYPT()`, `DES_ENCRYPT()`, `DES_DECRYPT()` 함수가 제거됐다. 5.7까지 `PASSWORD()` 함수를 직접 쿼리에서 호출하는 코드가 있다면 8.0에서 오류가 난다.

```sql
-- 5.7에서는 동작, 8.0에서 오류
SELECT PASSWORD('mypassword');

-- 8.0에서는 SHA2 또는 다른 해시 함수를 직접 써야 한다
SELECT SHA2('mypassword', 256);
```

레거시 코드에서 `PASSWORD()` 함수를 쓰는 경우가 드물지 않다. 코드베이스에서 이 함수를 직접 호출하는 곳을 찾아서 바꿔야 한다.

### 5.4 ONLY_FULL_GROUP_BY 기본 활성화

8.0에서 `ONLY_FULL_GROUP_BY`가 `sql_mode`에 기본으로 들어간다. 5.7에서도 기본값이지만 파라미터 그룹을 통해 끄고 쓰는 경우가 있었다. 8.0에서는 이걸 끄더라도 일부 동작이 달라진다.

`GROUP BY` 절에 없는 컬럼을 `SELECT`에 넣는 쿼리가 5.7에서는 (`ONLY_FULL_GROUP_BY`가 꺼진 상태에서) 통과했다면 8.0에서는 오류 또는 경고가 난다.

```sql
-- ONLY_FULL_GROUP_BY 위반 예시
-- category만 GROUP BY에 있는데 name을 SELECT
SELECT category, name, COUNT(*) FROM products GROUP BY category;

-- 8.0에서 올바른 형태
SELECT category, MIN(name), COUNT(*) FROM products GROUP BY category;
-- 또는 name도 GROUP BY에 추가
SELECT category, name, COUNT(*) FROM products GROUP BY category, name;
```

ORM이 자동 생성하는 쿼리가 이 패턴을 타는 경우도 있다. 8.0 green 환경에서 실제 애플리케이션 쿼리를 돌려보기 전까지 모두 잡히지 않을 수 있다.

---

## 6. 파라미터 차이 처리

5.7과 8.0은 파라미터 그룹을 공유할 수 없다. 8.0용 파라미터 그룹을 따로 만들어야 한다. 이 과정에서 5.7에서 쓰던 파라미터 중 8.0에서 사라진 것들을 정리해야 한다.

### 제거된 파라미터

| 파라미터 | 5.7 | 8.0 |
|----------|-----|-----|
| `query_cache_type` | 존재 | 제거 (쿼리 캐시 자체가 없어짐) |
| `query_cache_size` | 존재 | 제거 |
| `innodb_file_format` | 존재 | 제거 (Barracuda가 유일한 포맷) |
| `innodb_file_format_max` | 존재 | 제거 |
| `innodb_large_prefix` | 존재 | 제거 (항상 활성화 상태) |
| `innodb_support_xa` | 존재 | 제거 |
| `tx_isolation` | 존재 | `transaction_isolation`으로 이름 변경 |

커스텀 파라미터 그룹에 이 항목들이 있으면 8.0 그룹에서는 빼야 한다. 그냥 두면 적용 자체가 안 되거나 오류가 날 수 있다.

### 인증 플러그인 기본값

파라미터 그룹에서 `default_authentication_plugin`을 명시적으로 `mysql_native_password`로 잡아두면 8.0에서도 새 계정을 native password 방식으로 만든다. 기존 클라이언트 호환성을 유지해야 하는 상황에서 임시 조치로 쓴다.

```
default_authentication_plugin = mysql_native_password
```

다만 이건 임시 조치다. 장기적으로는 드라이버를 올리고 `caching_sha2_password`로 이행해야 한다.

### sql_mode 확인

5.7 파라미터 그룹에 `sql_mode`를 커스텀으로 설정해뒀다면 8.0 그룹에도 같은 값을 넣되, 8.0에서 추가된 모드가 있는지 확인해야 한다. 5.7에서 `NO_AUTO_CREATE_USER`가 `sql_mode`에 있었다면 8.0에서는 이 모드가 제거됐으므로 빼야 한다. 8.0에서 모르는 모드 이름을 넣으면 파라미터 그룹 적용이 거부된다.

```bash
# 현재 blue의 sql_mode 확인
aws rds describe-db-parameters \
  --db-parameter-group-name my-mysql57-pg \
  --query "Parameters[?ParameterName=='sql_mode']"
```

---

## 7. 사전 점검: pre-upgrade 체크

green 생성 전에 업그레이드 가능 여부를 확인할 수 있다. MySQL 공식 `mysqlcheck` 도구 또는 MySQL Shell의 `util.checkForServerUpgrade()`를 쓴다.

MySQL Shell을 blue 인스턴스에 연결해서 돌리면 호환성 문제 목록을 뽑아준다.

```bash
mysqlsh --host=mydb.xxxxx.ap-northeast-2.rds.amazonaws.com \
  --user=admin --password \
  -- util checkForServerUpgrade
```

`error` 수준으로 찍힌 항목은 업그레이드 전에 반드시 해결해야 한다. `warning`은 진행은 되지만 동작이 달라질 수 있다는 뜻이라 같이 봐야 한다.

운영 인스턴스에 직접 돌리기 부담스러우면 최신 스냅샷을 복원해서 별도 인스턴스를 만들고 거기서 돌리면 된다. green 생성 비용 없이 호환성 문제만 먼저 파악할 수 있다.

---

## 8. 실제 업그레이드 순서

정리하면 실제 작업은 이 순서로 간다.

스냅샷을 복원한 임시 인스턴스에서 `checkForServerUpgrade`를 돌려 error/warning 목록을 전부 파악한다. error 항목을 운영 DB에서 수정한다 — 예약어 컬럼명 변경, 제거된 함수 코드 수정, 드라이버 버전 업. 8.0용 파라미터 그룹을 만든다. Blue/Green Deployment를 생성하면 green이 8.0으로 올라온다. green에 스테이징 애플리케이션을 붙여서 쿼리 오류, 인증 플러그인 문제, `ONLY_FULL_GROUP_BY` 위반 등을 확인한다. replica lag이 안정되면 트래픽이 낮은 시간대에 switchover를 실행한다. switchover 후 며칠 동안 옛 blue를 살려두면서 지표를 모니터링한 뒤 삭제한다.

green에서 실제 쿼리를 돌려보는 단계가 가장 중요하다. 사전 점검 도구가 잡아내지 못하는 애플리케이션 레벨 호환성 문제는 여기서 걸린다. switchover를 되돌리는 게 현실적으로 어렵다는 점을 감안하면, 전환 전 검증에 시간을 충분히 쓰는 게 낫다.
