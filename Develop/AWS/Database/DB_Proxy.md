---
title: AWS DB Proxy
tags: [aws, database, dbproxy, rds, aurora]
updated: 2026-04-26
---

# AWS DB Proxy

## 1. 개요

RDS Proxy는 애플리케이션과 RDS/Aurora 사이에 끼는 완전관리형 커넥션 풀이다. 기존에 ProxySQL, PgBouncer를 EC2에 띄워서 운영하던 것을 AWS가 매니지드로 제공한다고 보면 된다.

직접 PgBouncer를 운영해 본 사람이라면 Proxy의 동작 방식이 익숙할 것이다. 다만 매니지드 서비스이기 때문에 내부 동작을 직접 들여다볼 수 없고, 튜닝 가능한 파라미터가 제한적이라는 점이 가장 큰 차이다. 그래서 Pinning이나 borrow timeout 같은 동작을 모르고 도입하면 "분명히 풀링이 되어야 하는데 왜 DB 연결이 안 줄어들지?"라는 상황을 자주 만난다.

## 2. 도입을 고민할 시점

다음 상황 중 하나에 해당하면 Proxy 도입을 검토할 만하다.

- Lambda 동시 실행 수가 100을 넘어가면서 DB의 `max_connections`에 근접하고 있다
- ECS task가 오토스케일링으로 늘어났을 때 DB 연결이 폭증한다
- RDS failover 시 애플리케이션이 DNS 캐시 때문에 1분 넘게 끊긴다
- 애플리케이션 코드를 건드리지 않고 IAM 인증으로 전환하고 싶다

반대로 도입 효과가 거의 없는 경우도 있다. 단일 EC2/ECS에서 이미 HikariCP 같은 풀러로 연결을 잘 관리하고 있는 워크로드, prepared statement를 매 쿼리마다 새로 만드는 ORM 환경, 트랜잭션이 길게 유지되는 OLAP 워크로드는 Proxy를 둬도 풀링 효과를 거의 못 본다.

## 3. 풀링 동작의 핵심 — Multiplexing과 Pinning

Proxy의 풀링은 클라이언트 연결 N개가 백엔드 DB 연결 M개를 공유하는 구조다. 이상적으로는 N >> M이 되어야 의미가 있다. 그런데 실무에서 "왜 백엔드 연결이 클라이언트 연결만큼 많지?"라는 일이 자주 생기는데, 거의 대부분 Pinning이 원인이다.

### 3.1 Pinning이 발생하는 조건

Proxy가 클라이언트 세션을 특정 백엔드 연결에 고정시키는 것을 Pinning(핀닝)이라고 한다. 핀이 박힌 연결은 풀로 반환되지 않고 클라이언트가 연결을 끊을 때까지 점유된다. 즉 그 시간 동안 풀링 효과가 사라진다.

MySQL에서 Pinning이 일어나는 대표적인 케이스는 다음과 같다.

- `SET` 문으로 세션 변수 변경 (`SET autocommit`, `SET time_zone`, `SET names` 등)
- 사용자 정의 변수 사용 (`SET @var = 1`, `SELECT @var := 1`)
- 임시 테이블 생성 (`CREATE TEMPORARY TABLE`)
- 명시적 `LOCK TABLES`
- prepared statement (드라이버에 따라 다름, 뒤에 별도 설명)
- `GET_LOCK()` 같은 advisory lock

PostgreSQL은 조건이 조금 다르다.

- `SET LOCAL`이 아닌 `SET` 문 (세션 단위 설정 변경)
- `LISTEN/NOTIFY`
- 임시 테이블 (`CREATE TEMP TABLE`)
- 커서를 트랜잭션 밖에서 유지 (`DECLARE ... WITH HOLD`)
- prepared statement (named statement)

문제는 ORM이나 드라이버가 자동으로 이런 명령을 실행하는 경우가 많다는 것이다. JDBC가 연결 직후 `SET autocommit=0`을 보내거나, Sequelize가 `SET time_zone`을 매번 실행하거나, 일부 PostgreSQL 드라이버가 prepared statement를 named로 캐싱하면 사실상 모든 클라이언트 세션이 핀닝된다. 이런 환경에서는 Proxy 도입 후 풀 활용률이 0%에 가까워진다.

### 3.2 핀닝 모니터링

CloudWatch에서 풀링이 제대로 되고 있는지 가장 빠르게 확인할 수 있는 메트릭은 `DatabaseConnectionsCurrentlySessionPinned`다. 이 값이 `DatabaseConnections` 대비 얼마나 차지하는지가 풀 효율의 직접적인 지표가 된다.

해석 기준을 잡으면:

- 핀닝 비율 10% 미만: 풀링이 정상 작동 중
- 10~50%: 일부 세션이 핀닝됨, ORM/드라이버 설정 점검 필요
- 50% 이상: 사실상 풀링이 안 되는 상태, 풀러를 둔 의미가 없음

Performance Insights에서 `EnhancedMonitoring`을 켜면 어떤 SQL이 핀닝을 유발했는지 RDS Proxy logs에서 추적할 수 있다. 로그에 `The client session was pinned to the database connection ... for the remainder of the session. Reason: ...` 형태로 핀닝 사유가 남는다. 이걸 `aws logs filter-log-events`로 한 번 훑어보면 어떤 패턴 때문에 풀이 망가지는지 바로 잡힌다.

### 3.3 prepared statement 핀닝의 함정

prepared statement는 드라이버 구현에 따라 핀닝 여부가 갈린다. MySQL의 경우 Proxy는 `COM_STMT_PREPARE`를 받으면 해당 세션을 즉시 핀닝한다. JDBC `useServerPrepStmts=true`, mysql2 Node.js의 `mysql.createConnection().prepare()`, Python `cursor.execute(prepared=True)` 같은 옵션이 켜져 있으면 모든 쿼리가 핀닝된다.

해결 방법은 두 가지다. 하나는 클라이언트 측에서 prepare를 끄고 driver-side string interpolation으로 변경하는 것(보안 검토 필수), 다른 하나는 prepared statement를 포기하지 못하면 풀러로서의 효과를 어느 정도 포기하고 백엔드 연결 수를 늘려서 운영하는 것이다. PostgreSQL은 unnamed prepared statement(`PREPARE ""`)는 핀닝하지 않으므로, 드라이버 옵션을 unnamed로 바꿀 수 있는지 먼저 확인한다.

## 4. Transaction-level vs Session-level Pooling

PgBouncer를 써본 사람은 `pool_mode = transaction`과 `pool_mode = session`의 차이를 알 것이다. RDS Proxy는 기본적으로 transaction-level에 가까운 동작을 한다. 트랜잭션이 끝나면(또는 단발 쿼리가 끝나면) 백엔드 연결을 풀로 반환한다.

이 동작 때문에 PostgreSQL에서 한 가지 주의할 점이 생긴다. `BEGIN`만 보내고 다음 쿼리를 한참 안 보내는 클라이언트가 있으면, 그동안 백엔드 연결이 점유된 채로 풀에 못 돌아간다. 이걸 `idle_in_transaction` 상태라고 하는데, RDS PostgreSQL은 `idle_in_transaction_session_timeout` 파라미터로 강제 종료할 수 있지만 Proxy 자체는 트랜잭션 중인 연결을 강제로 회수하지 않는다.

실무에서는 RDS 파라미터 그룹에 `idle_in_transaction_session_timeout = 30000` (30초) 정도를 설정해두는 편이 안전하다. 트랜잭션을 열어두고 외부 API를 호출하는 코드가 어딘가 숨어 있으면 풀이 순식간에 고갈된다. MySQL에서도 비슷하게 `wait_timeout`을 짧게 잡아두면 좀비 트랜잭션이 백엔드 연결을 잡고 있는 시간을 줄일 수 있다.

세션 수준 동작이 강제되는 케이스(앞서 본 핀닝 조건)에서는 transaction-level의 장점이 사라지기 때문에, 핀닝 모니터링과 `idle_in_transaction` 모니터링은 같이 봐야 한다.

## 5. Lambda + RDS Proxy 실무 이슈

Lambda가 Proxy의 가장 흔한 사용처지만, 막상 붙여보면 골치 아픈 부분이 몇 가지 있다.

### 5.1 IAM 토큰 만료

`generateAuthToken`으로 받은 IAM 인증 토큰은 발급 시점부터 15분 동안만 유효하다. Lambda 컨테이너가 재사용되면서 핸들러 밖의 connection 객체를 캐싱하는 일반적인 패턴에서는, 15분이 지나면 다음 요청에서 인증 실패가 난다.

```javascript
let connection;
let tokenIssuedAt = 0;
const TOKEN_TTL_MS = 14 * 60 * 1000; // 14분, 안전 마진

exports.handler = async (event) => {
  const now = Date.now();
  if (!connection || now - tokenIssuedAt > TOKEN_TTL_MS) {
    if (connection) await connection.end().catch(() => {});
    connection = await getConnection();
    tokenIssuedAt = now;
  }
  // ...
};
```

토큰 만료 시점을 14분으로 두는 이유는 Lambda 실행 중에 토큰이 만료되어 쿼리가 실패하는 사고를 막기 위해서다. 14분 시점에서 재발급해두면 1분의 안전 마진이 생긴다.

### 5.2 IAM 토큰 발급 throttling

IAM 인증 토큰은 STS 기반이라 발급 자체에 throttling이 걸린다. Lambda 동시 실행이 갑자기 수천 개로 튀면 `RDS Proxy`로 가기 전에 토큰 생성 단계에서 실패하는 일이 생긴다. 로그에 `Rate exceeded` 또는 `ThrottlingException`이 보이면 이 케이스다.

대응은 두 가지다. 첫째, 토큰을 핸들러 밖에서 캐싱해서 컨테이너 재사용 시 재발급을 줄인다(위 코드 패턴이 그것이다). 둘째, IAM 인증이 굳이 필요 없는 워크로드면 Secrets Manager 인증만 쓰는 것도 선택지다. Proxy가 자동으로 Secrets Manager에서 자격증명을 가져오므로 클라이언트는 평문 password처럼 사용한다.

### 5.3 init_connection_timeout

Lambda VPC Config가 붙어 있는 함수가 cold start 후 처음으로 Proxy에 연결할 때, ENI 할당이 늦어지면 기본 타임아웃 3초로는 빠듯하다. 드라이버 레벨 connect timeout을 10초 정도로 늘려두는 편이 안전하다.

```javascript
mysql.createConnection({
  host: process.env.PROXY_ENDPOINT,
  user: 'lambda_user',
  password: token,
  database: 'myapp',
  ssl: { rejectUnauthorized: true },
  connectTimeout: 10000,
});
```

VPC Lambda의 cold start가 충분히 짧아진 지금도 가끔 timeout이 발생하는데, 거의 ENI 할당 지연 아니면 보안 그룹 설정 누락이다.

## 6. Failover 동작과 실제 끊김 시간

Proxy를 도입하는 가장 큰 명분 중 하나가 빠른 failover다. RDS DNS는 TTL이 5초지만, JVM 같은 환경에서는 OS DNS 캐시 때문에 실제로는 30초~1분씩 끊기는 경우가 많다. Proxy를 두면 클라이언트 입장에서 DNS는 그대로고 백엔드 라우팅을 Proxy가 처리한다.

실제 측정해본 결과:

- Aurora MySQL/PostgreSQL: failover 시 약 2초 내외로 회복. Aurora의 storage 분리 구조 덕분에 promotion이 빠르다
- RDS Multi-AZ (인스턴스 페일오버): 6~10초. standby 인스턴스가 active로 promote되는 시간이 추가로 든다
- RDS Multi-AZ Cluster (writer + 2 reader): 약 35초였던 기존 구조에서 5초 이하로 단축됨

in-flight query 동작도 알아둬야 한다. failover 순간에 진행 중이던 쿼리는 어떻게든 실패한다. Proxy가 자동으로 retry해주지는 않는다. 클라이언트가 받는 에러는 보통 `Communications link failure` (MySQL) 또는 `terminating connection due to administrator command` (PostgreSQL)다. 애플리케이션 레벨에서 idempotent한 read 쿼리는 retry 로직을 두는 편이 좋다.

write 쿼리는 retry가 위험하다. failover 시점에 해당 트랜잭션이 커밋됐는지 안 됐는지 클라이언트가 확신할 수 없기 때문이다. 멱등성 키(idempotency key)나 `INSERT ... ON CONFLICT DO NOTHING`으로 중복 실행에 안전하게 만들어 두지 않으면 retry로 데이터를 망가뜨릴 수 있다.

## 7. Aurora Reader endpoint vs Proxy Read-only endpoint

Aurora를 쓰면 원래 reader endpoint가 있다. 그러면 Proxy의 read-only endpoint는 뭐가 다른가?

| 항목 | Aurora Reader endpoint | Proxy Read-only endpoint |
|------|----------------------|------------------------|
| 라우팅 단위 | DNS 라운드로빈 | 연결 단위 라우팅 |
| failover 처리 | DNS TTL 의존 | Proxy가 즉시 라우팅 변경 |
| 연결 풀링 | 없음 | 있음 |
| reader 인스턴스 추가 | 자동 반영 (TTL 후) | 자동 반영 (즉시) |
| writer로 쓰기 시도 | read-only 에러 | read-only 에러 |

Aurora reader endpoint는 DNS 레벨 분산이라서 한 번 연결을 맺으면 그 연결은 특정 reader에 고정된다. reader 한 대에 트래픽이 쏠리면 다른 reader가 놀고 있어도 균형이 안 맞는다. Proxy read-only endpoint는 쿼리 단위로 reader를 선택하기 때문에 분산이 균일하다. reader 인스턴스가 추가되거나 빠질 때도 Proxy는 즉시 반영하지만, reader endpoint는 DNS TTL만큼 지연된다.

writer 쿼리를 read-only endpoint에 보내면 둘 다 에러가 나는 건 동일하다. ORM에 read/write splitting을 구현할 때 Proxy를 쓴다고 해서 자동으로 분리되지는 않는다. 애플리케이션이 명시적으로 endpoint를 골라줘야 한다.

## 8. Secrets Manager 자격증명 로테이션 이슈

Secrets Manager가 자격증명을 자동 로테이션할 때 일시적인 인증 실패가 발생할 수 있다. 동작 순서가 이렇다.

1. Secrets Manager가 새 password 생성
2. Lambda 로테이션 함수가 DB에 새 password 적용 (`ALTER USER ... PASSWORD ...`)
3. Secrets Manager의 `AWSCURRENT` 라벨을 새 password로 이동
4. Proxy가 변경을 감지하고 새 password로 백엔드 연결 갱신

3번과 4번 사이에 Proxy가 아직 이전 password를 쓰고 있는데 DB는 이미 새 password를 받았다면, 그 동안의 신규 백엔드 연결은 인증 실패한다. 이 시간이 짧으면 수 초, 길면 수십 초까지 갈 수 있다.

대응 방법은 다음과 같다.

- 로테이션 함수에서 `multi-user` 패턴을 쓴다. AWS가 제공하는 RDS rotation Lambda 템플릿 중 `single-user`와 `multi-user`가 있는데, multi-user는 두 개의 DB 사용자를 번갈아 사용한다. 로테이션 시점에 한쪽 사용자가 점진적으로 전환되므로 인증 실패 윈도우가 거의 없다
- 애플리케이션 레벨에서 인증 실패 시 짧은 backoff retry를 둔다. 1초 sleep 후 한 번 더 시도하면 대부분 통과한다
- 로테이션 일정을 트래픽이 적은 시간대로 맞춘다. cron expression으로 지정 가능하다

운영 환경에서는 multi-user 패턴이 사실상 필수다. single-user는 PoC 수준에서만 쓴다.

## 9. 트러블슈팅 사례

실제로 마주친 케이스들을 정리한다.

### 9.1 connection borrow timeout

가장 자주 보는 에러다. 클라이언트가 Proxy에 연결은 됐는데 백엔드 연결을 빌려오기까지 대기하다가 timeout이 난다.

원인은 대부분 둘 중 하나다. 백엔드 풀이 가득 찼거나(다 핀닝되어 있거나 진짜로 트래픽이 많거나), `connection_borrow_timeout`이 너무 짧거나. 기본값은 120초인데 이걸 줄이는 건 거의 의미가 없다. 늘려도 본질적인 해결은 안 된다. 핵심은 풀이 왜 가득 찼는지를 봐야 한다.

조사 순서는:

1. CloudWatch에서 `DatabaseConnections` vs `MaxDatabaseConnections` 비교. 100% 근접이면 풀 부족
2. `DatabaseConnectionsCurrentlySessionPinned` 비율 확인. 높으면 핀닝이 원인
3. `MaxDatabaseConnections`는 `max_connections_percent`(기본 100)와 RDS 인스턴스의 `max_connections` 파라미터 곱이다. RDS `max_connections`가 충분한지 확인
4. RDS Performance Insights에서 long-running query 또는 `idle in transaction` 세션 확인

`max_connections_percent`를 200처럼 100 이상으로 설정할 수도 있다. 이건 클라이언트 연결 N개에 대해 백엔드를 N의 200%까지 띄울 수 있다는 게 아니라, RDS 인스턴스의 `max_connections` 대비 비율이다. 100을 넘기면 burst 트래픽을 받을 때 잠깐 더 띄울 수 있는 여지가 생기지만, 실제로 많이 쓰지는 않는다.

### 9.2 풀 효과가 거의 0%인 케이스

도입 후 백엔드 연결 수가 줄지 않는다는 클레임이 가장 흔하다. 이미 위에서 설명한 핀닝이 거의 모든 원인이다. 한 번은 Spring Boot + HikariCP + JDBC `useServerPrepStmts=true` 조합에서 모든 쿼리가 핀닝되어 Proxy를 둔 의미가 사라진 적이 있었다. `useServerPrepStmts=false`로 바꾸자 핀닝 비율이 80%에서 5%로 떨어졌다.

PostgreSQL에서는 PgJDBC의 `prepareThreshold` 기본값(5)이 문제다. 같은 쿼리를 5번 실행하면 자동으로 named prepared statement로 전환되어 핀닝된다. `prepareThreshold=0`으로 설정해 자동 전환을 끄거나, `preparedStatementCacheQueries=0`으로 캐시를 비활성화하면 된다.

### 9.3 ProxySQL/PgBouncer 대비 한계

PgBouncer를 직접 운영해본 사람이라면 RDS Proxy가 답답하게 느껴질 수 있다. 안 되는 것들이 있다.

- 쿼리 라우팅 규칙 (PgBouncer의 read-only/read-write 분리, ProxySQL의 query rule)
- 쿼리 캐싱 (ProxySQL의 query cache)
- 쿼리 리라이팅
- 세부 풀 모드 선택 (PgBouncer의 statement-level pooling 같은 옵션)
- 쿼리 로깅 수준 제어

대신 매니지드라는 점, IAM 인증, Secrets Manager 통합, AWS 보안 그룹 기반 격리가 장점이다. 트레이드오프를 알고 도입한다.

복잡한 라우팅 로직이 필요하면 RDS Proxy 대신 ECS에 PgBouncer/ProxySQL을 띄우는 편이 낫다. 단순한 풀링과 빠른 failover만 필요하면 RDS Proxy가 운영 부담이 훨씬 적다.

## 10. 모니터링 메트릭 정리

CloudWatch에서 봐야 하는 메트릭과 해석 기준을 묶어둔다.

| 메트릭 | 의미 | 이상 신호 |
|--------|------|----------|
| `ClientConnections` | 클라이언트→Proxy 연결 수 | 평균 대비 급증 |
| `DatabaseConnections` | Proxy→DB 백엔드 연결 수 | `MaxDatabaseConnections`의 80% 초과 |
| `DatabaseConnectionsCurrentlySessionPinned` | 핀닝된 백엔드 연결 수 | `DatabaseConnections`의 50% 초과 시 풀링 효과 거의 없음 |
| `ClientConnectionsClosed` | 클라이언트 연결 종료 수 | 갑작스러운 spike는 timeout/에러 의심 |
| `DatabaseConnectionsBorrowLatency` | 백엔드 연결 빌리는 데 걸린 시간 | 100ms 이상이면 풀 경합 |
| `QueryDatabaseResponseLatency` | DB의 쿼리 응답 시간 | Proxy 도입 후 늘어났다면 문제 |

`DatabaseConnectionsBorrowLatency`가 늘어나기 시작하면 borrow timeout이 곧 발생한다는 신호다. timeout이 실제로 터지기 전에 alarm을 걸어두면 대응 시간을 벌 수 있다.

쿼리 로깅이 필요하면 `EnhancedMonitoring`을 켠다. 다만 로그 양이 많아지므로 운영 환경에서는 평소엔 끄고 디버깅 시점에만 켜는 패턴을 쓴다. 토큰 발급 로그까지 다 남기면 비용이 빠르게 늘어난다.

## 11. 코드 예제

### AWS CLI — RDS Proxy 생성

```bash
SECRET_ARN=$(aws secretsmanager create-secret \
  --name "prod/mydb/credentials" \
  --secret-string '{"username":"admin","password":"s3cr3t"}' \
  --query 'ARN' --output text)

aws rds create-db-proxy \
  --db-proxy-name "myapp-proxy" \
  --engine-family MYSQL \
  --auth '[{
    "AuthScheme": "SECRETS",
    "SecretArn": "'$SECRET_ARN'",
    "IAMAuth": "REQUIRED"
  }]' \
  --role-arn arn:aws:iam::123456789012:role/RDSProxyRole \
  --vpc-subnet-ids subnet-aaa subnet-bbb \
  --vpc-security-group-ids sg-xxxxxxxx

aws rds describe-db-proxies \
  --db-proxy-name myapp-proxy \
  --query 'DBProxies[0].Endpoint' --output text

aws rds register-db-proxy-targets \
  --db-proxy-name myapp-proxy \
  --db-instance-identifiers my-mysql-instance
```

### Terraform — RDS Proxy 설정

```hcl
resource "aws_secretsmanager_secret" "db_creds" {
  name = "prod/mydb/credentials"
}

resource "aws_secretsmanager_secret_version" "db_creds" {
  secret_id = aws_secretsmanager_secret.db_creds.id
  secret_string = jsonencode({
    username = "admin"
    password = var.db_password
  })
}

resource "aws_iam_role" "rds_proxy" {
  name = "rds-proxy-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "rds.amazonaws.com" }
    }]
  })
}

resource "aws_db_proxy" "main" {
  name                   = "myapp-proxy"
  engine_family          = "MYSQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_security_group_ids = [aws_security_group.proxy.id]
  vpc_subnet_ids         = aws_subnet.private[*].id

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "REQUIRED"
    secret_arn  = aws_secretsmanager_secret.db_creds.arn
  }
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

resource "aws_db_proxy_target" "main" {
  db_instance_identifier = aws_db_instance.main.id
  db_proxy_name          = aws_db_proxy.main.name
  target_group_name      = aws_db_proxy_default_target_group.main.name
}
```

### Lambda — IAM 토큰 갱신 패턴 (Node.js)

```javascript
const mysql = require('mysql2/promise');
const { Signer } = require('@aws-sdk/rds-signer');

const TOKEN_TTL_MS = 14 * 60 * 1000;
let connection;
let tokenIssuedAt = 0;

async function getConnection() {
  const signer = new Signer({
    hostname: process.env.PROXY_ENDPOINT,
    port: 3306,
    region: 'ap-northeast-2',
    username: 'lambda_user',
  });

  const token = await signer.getAuthToken();

  return mysql.createConnection({
    host:           process.env.PROXY_ENDPOINT,
    user:           'lambda_user',
    password:       token,
    database:       'myapp',
    ssl:            { rejectUnauthorized: true },
    connectTimeout: 10000,
  });
}

exports.handler = async (event) => {
  const now = Date.now();
  if (!connection || now - tokenIssuedAt > TOKEN_TTL_MS) {
    if (connection) {
      await connection.end().catch(() => {});
    }
    connection = await getConnection();
    tokenIssuedAt = now;
  }

  try {
    const [rows] = await connection.execute(
      'SELECT * FROM users WHERE id = ?',
      [event.userId],
    );
    return { statusCode: 200, body: JSON.stringify(rows) };
  } catch (err) {
    connection = null;
    tokenIssuedAt = 0;
    throw err;
  }
};
```

### CloudWatch 알람 — 핀닝 비율 모니터링

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-proxy-pinning-ratio-high" \
  --metric-name DatabaseConnectionsCurrentlySessionPinned \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ProxyName,Value=myapp-proxy \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:db-alerts
```

## 12. 참고 링크

- [AWS 공식 문서 - RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.html)
- [RDS Proxy Pinning 동작](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html#rds-proxy-pinning)
- [RDS Proxy CloudWatch Metrics](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.monitoring.html)
- [Secrets Manager rotation Lambda templates](https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html)
- [Pricing](https://aws.amazon.com/rds/proxy/pricing/)
