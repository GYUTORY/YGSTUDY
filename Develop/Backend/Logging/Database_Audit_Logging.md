---
title: DB 레벨 감사 로깅
tags: [database, rdbms, postgresql, mysql, security, backend, observability]
updated: 2026-09-23
---

# DB 레벨 감사 로깅

애플리케이션 코드에서 감사 로그를 쌓아도 DBA가 psql로 직접 접속해 데이터를 수정하거나, Flyway 마이그레이션이 배치로 UPDATE를 실행하면 그 기록이 어디에도 남지 않는다. 금융권 침해 사고 조사에서 DBA 계정으로 이루어진 직접 쿼리가 애플리케이션 로그에 없어 이상 접근을 한참 뒤에야 발견한 경우가 실제로 있다.

DB 레벨 감사는 이 공백을 메운다. 데이터베이스 엔진이 직접 SQL을 기록하거나 트리거로 변경 이력을 보관하므로, 접근 경로와 무관하게 추적된다.

## 애플리케이션 레이어를 우회하는 접근

서비스가 커지면 DB에 직접 닿는 경로가 여러 개 생긴다.

- DBA가 장애 복구나 데이터 정정을 위해 psql/mysql 클라이언트로 직접 쿼리
- Flyway, Liquibase 같은 마이그레이션 도구가 스키마 변경과 함께 데이터 수정
- ETL 파이프라인이 분석 목적으로 직접 SELECT
- 데이터 복구 스크립트가 비상용 계정으로 실행
- 레거시 배치 잡이 ORM 없이 JDBC로 직접 실행

이 중 어느 경로든 감사 대상 테이블을 건드리면 애플리케이션 감사 로그에는 흔적이 없다. 규제 심사에서 "해당 기간 해당 테이블에 대한 DBA 접근 기록을 제출하라"는 요청이 왔을 때 DB 레벨 감사가 없으면 답이 없다.

## PostgreSQL — pg_audit

pg_audit은 PostgreSQL 확장으로, 선택한 오브젝트나 사용자의 SQL 실행 내역을 서버 로그에 기록한다. `pgaudit`이라는 이름으로 RDS, Aurora PostgreSQL에서도 활성화할 수 있다.

### 설치와 기본 설정

```bash
# postgresql.conf에 shared_preload_libraries 추가 필요
echo "shared_preload_libraries = 'pgaudit'" >> /etc/postgresql/15/main/postgresql.conf

# PostgreSQL 재시작 후
psql -U postgres -c "CREATE EXTENSION pgaudit;"
```

`shared_preload_libraries`에 추가하지 않으면 `CREATE EXTENSION`이 성공해도 감사가 동작하지 않는다. 기존 운영 서버에 적용할 때는 재시작이 필요하다는 점을 사전에 확인해야 한다.

```sql
-- 세션 레벨 감사 설정 (전체 DB 대상)
ALTER SYSTEM SET pgaudit.log = 'write, ddl';
-- write: INSERT, UPDATE, DELETE, TRUNCATE
-- ddl: CREATE, ALTER, DROP
-- read: SELECT, COPY (데이터가 많은 환경에서는 로그 폭발 주의)
-- all: 전부 (일반적으로 너무 많음)

SELECT pg_reload_conf();
```

실제 운영 환경에서 `pgaudit.log = 'all'`을 켜면 로그 볼륨이 수십 배로 뛴다. `write, ddl`로 좁히고, 민감 테이블에만 오브젝트 감사를 추가로 거는 방식이 현실적이다.

### 오브젝트 레벨 감사

특정 테이블만 감사하려면 전용 역할을 만들어 감사 대상 테이블에 권한을 부여한다.

```sql
-- 감사 전용 역할
CREATE ROLE audit_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO audit_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON payments TO audit_role;

-- 오브젝트 레벨 감사 활성화
ALTER SYSTEM SET pgaudit.role = 'audit_role';
SELECT pg_reload_conf();
```

이후 `users` 또는 `payments` 테이블에 대한 모든 DML이 서버 로그에 기록된다. `pg_reload_conf()` 후 반드시 테스트 쿼리를 실행하고 로그에 audit 항목이 찍히는지 확인한다.

### 로그 출력 형태

```
AUDIT: SESSION,1,1,DDL,CREATE TABLE,TABLE,public.orders,"CREATE TABLE orders (...)",<none>
AUDIT: OBJECT,2,1,WRITE,UPDATE,TABLE,public.users,"UPDATE users SET role='admin' WHERE id=1",<none>
```

`OBJECT` 타입은 오브젝트 레벨 감사, `SESSION` 타입은 세션 레벨 감사에서 나온다. 로그 파서를 구현할 때 두 타입을 구분해야 한다.

### RDS PostgreSQL에서 pg_audit

RDS에서는 파라미터 그룹으로 설정한다.

```
shared_preload_libraries: pgaudit
pgaudit.log: write,ddl
pgaudit.log_catalog: 0       # pg_catalog 시스템 테이블 감사 제외
pgaudit.log_relation: 1      # 각 관계(테이블)마다 별도 로그 항목
```

RDS는 `shared_preload_libraries` 변경 후 인스턴스 재부팅이 필요하다. 재부팅 전에 `pgaudit.log` 파라미터만 변경해도 감사가 동작하지 않는다. 로그는 CloudWatch Logs로 전달하도록 설정하면 장기 보관과 쿼리가 편하다.

## MySQL — 감사 로깅

MySQL은 버전과 에디션에 따라 감사 방법이 갈린다.

### MySQL Enterprise Audit

MySQL Enterprise Edition은 `audit_log` 플러그인을 제공한다.

```sql
-- 플러그인 설치 확인
SHOW PLUGINS LIKE 'audit%';

-- 설치
INSTALL PLUGIN audit_log SONAME 'audit_log.so';
```

`my.cnf`에 설정을 넣는다.

```ini
[mysqld]
plugin-load-add=audit_log.so
audit_log_policy=ALL          # ALL, LOGINS, QUERIES, NONE
audit_log_format=JSON
audit_log_file=/var/log/mysql/audit.log
audit_log_rotate_on_size=100M
```

`audit_log_policy=ALL`은 로그인과 쿼리 전부를 기록한다. 쿼리가 많은 환경에서는 `audit_log_connection_policy`와 `audit_log_statement_policy`를 분리 설정해 로그인만 전수 기록하고 쿼리는 특정 데이터베이스만 기록하는 식으로 범위를 조정한다.

### MySQL Community — MariaDB 내장 감사 플러그인

엔터프라이즈 라이선스 없이 MariaDB를 쓰는 경우 내장 감사 플러그인을 쓴다.

```sql
INSTALL SONAME 'server_audit';

SET GLOBAL server_audit_logging = ON;
SET GLOBAL server_audit_events = 'CONNECT,QUERY,TABLE';
SET GLOBAL server_audit_incl_users = 'dba_user,batch_user';
```

`server_audit_incl_users`로 감사할 계정을 특정하면 로그 볼륨을 대폭 줄일 수 있다. 일반 애플리케이션 계정을 제외하고 DBA 계정과 배치 계정만 지정하는 방식이 현실적이다.

### AWS Aurora MySQL Advanced Auditing

RDS MySQL Community Edition은 Enterprise Audit 플러그인을 지원하지 않는다. Aurora MySQL에서는 파라미터 그룹에서 `server_audit_logging=ON`으로 활성화하고 `server_audit_events`로 기록할 이벤트를 지정한다. CloudWatch Logs로 바로 내보낼 수 있어 별도 파일 관리가 필요 없다.

## Audit Trigger 패턴

DB 엔진 감사 기능을 쓸 수 없거나, 애플리케이션 로그와 동일한 포맷으로 변경 이력을 관리해야 할 때 트리거를 쓴다.

### 변경 이력 테이블 설계

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    table_name  TEXT        NOT NULL,
    operation   TEXT        NOT NULL,   -- INSERT, UPDATE, DELETE
    row_id      TEXT        NOT NULL,
    old_data    JSONB,
    new_data    JSONB,
    changed_by  TEXT,                   -- current_user (DB 접속 계정)
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    app_user_id TEXT,                   -- application.user_id 세션 변수
    client_addr INET
);

CREATE INDEX ON audit_log (table_name, changed_at DESC);
CREATE INDEX ON audit_log (row_id, table_name);
```

`old_data`, `new_data`를 JSONB로 저장하면 스키마 변경에 무관하게 이력을 남길 수 있다. 컬럼이 추가되거나 타입이 바뀌어도 트리거를 수정할 필요가 없다.

`app_user_id`는 PostgreSQL 세션 변수(`current_setting`)로 채운다. 애플리케이션이 쿼리 실행 전 `SET LOCAL application.user_id = '...'`를 실행하면 트리거에서 읽어 저장한다.

### 트리거 함수 (PostgreSQL)

```sql
CREATE OR REPLACE FUNCTION audit_trigger_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    app_user TEXT;
BEGIN
    -- 애플리케이션이 세션 변수로 넘긴 사용자 ID
    BEGIN
        app_user := current_setting('application.user_id');
    EXCEPTION WHEN OTHERS THEN
        app_user := NULL;
    END;

    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log(table_name, operation, row_id, old_data, changed_by, app_user_id, client_addr)
        VALUES (TG_TABLE_NAME, TG_OP, OLD.id::TEXT, to_jsonb(OLD), current_user, app_user, inet_client_addr());
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log(table_name, operation, row_id, old_data, new_data, changed_by, app_user_id, client_addr)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.id::TEXT, to_jsonb(OLD), to_jsonb(NEW), current_user, app_user, inet_client_addr());
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log(table_name, operation, row_id, new_data, changed_by, app_user_id, client_addr)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.id::TEXT, to_jsonb(NEW), current_user, app_user, inet_client_addr());
        RETURN NEW;
    END IF;
END;
$$;
```

`current_setting('application.user_id')`는 세션 변수가 없으면 예외를 던진다. `EXCEPTION WHEN OTHERS` 블록으로 감싸지 않으면 트리거가 실패하고 원본 DML도 롤백된다. DBA가 직접 접속한 경우에는 세션 변수가 없으므로 `NULL`로 기록하는 것이 맞다.

`AFTER` 트리거를 써야 한다. `BEFORE` 트리거는 실제 변경 전에 실행되므로, 이후 제약 조건 위반으로 롤백되어도 감사 로그가 남는다.

```sql
CREATE TRIGGER users_audit
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();

CREATE TRIGGER payments_audit
AFTER INSERT OR UPDATE OR DELETE ON payments
FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();
```

### 애플리케이션에서 세션 변수 설정

```java
@Aspect
@Component
public class AuditContextAspect {

    @PersistenceContext
    private EntityManager em;

    @Around("@annotation(org.springframework.transaction.annotation.Transactional)")
    public Object setAuditContext(ProceedingJoinPoint jp) throws Throwable {
        String userId = SecurityContextHolder.getContext()
            .getAuthentication().getName();

        em.createNativeQuery("SET LOCAL application.user_id = :userId")
            .setParameter("userId", userId)
            .executeUpdate();

        return jp.proceed();
    }
}
```

`SET LOCAL`은 현재 트랜잭션 범위에서만 유효하다. `SET SESSION`으로 설정하면 커넥션 풀에서 해당 커넥션을 재사용할 때 이전 사용자의 ID가 남아있을 수 있다.

## Temporal Table / System-Versioned Table

Temporal Table은 행 단위 이력을 DB 엔진이 자동으로 관리하는 기능이다. SQL:2011 표준에 포함되어 있고 MariaDB 10.3+에서 지원한다.

### MariaDB System-Versioned Table

```sql
CREATE TABLE orders (
    id        BIGINT        NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id   BIGINT        NOT NULL,
    amount    DECIMAL(10,2) NOT NULL,
    status    VARCHAR(20)   NOT NULL,
    row_start DATETIME(6)   GENERATED ALWAYS AS ROW START,
    row_end   DATETIME(6)   GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME(row_start, row_end)
) WITH SYSTEM VERSIONING;
```

`orders`에 UPDATE나 DELETE가 발생하면 MariaDB가 이전 행을 이력 파티션에 자동으로 보관한다.

```sql
-- 특정 시점의 데이터 조회
SELECT * FROM orders FOR SYSTEM_TIME AS OF '2026-09-01 00:00:00';

-- 특정 기간 동안의 모든 버전 조회
SELECT * FROM orders FOR SYSTEM_TIME BETWEEN '2026-08-01' AND '2026-09-23';

-- 전체 이력 조회
SELECT * FROM orders FOR SYSTEM_TIME ALL;
```

트리거 없이 시점 조회가 가능하다는 것이 Temporal Table의 장점이다. 하지만 `누가 바꿨는지`는 기록하지 않는다. `changed_by` 같은 컬럼은 명시적으로 관리해야 한다.

### 이력 파티션 관리

MariaDB Temporal Table의 이력은 별도 파티션에 쌓인다. 파티션을 관리하지 않으면 이력 데이터가 원본 테이블 크기를 수십 배 초과한다.

```sql
-- 6개월 이상 된 이력 삭제
DELETE HISTORY FROM orders BEFORE SYSTEM_TIME '2026-03-01';
```

MariaDB 10.4.5 이상에서는 `ALTER TABLE orders MODIFY HISTORY INTERVAL 1 YEAR`로 자동 정리 정책을 설정할 수 있다.

### PostgreSQL temporal 대안

PostgreSQL은 SQL:2011 Temporal Table을 기본 지원하지 않는다. `temporal_tables` 확장을 쓰거나, 앞서 설명한 트리거 방식으로 직접 구현한다. `pgTAP` 기반 테스트가 잘 구성되어 있다면 직접 트리거 구현도 유지보수가 크게 어렵지 않다.

## 성능 비용

DB 레벨 감사는 모든 DML에 추가 I/O를 발생시킨다.

### pg_audit 성능 영향

pg_audit은 서버 로그에 쓰는 방식이라 별도 테이블 I/O가 없다. `pgaudit.log = 'write'`를 켠 상태에서 INSERT 집중 워크로드의 TPS가 약 5~8% 감소한 케이스가 있다. `pgaudit.log = 'read'`까지 추가하면 SELECT 쿼리마다 로그가 찍혀 I/O가 두드러지게 늘어난다. 읽기 감사가 반드시 필요한 경우에만 켠다.

### Audit Trigger 성능 영향

트리거는 각 DML마다 트리거 함수를 실행하고 `audit_log` 테이블에 INSERT를 실행한다. `to_jsonb(OLD)`, `to_jsonb(NEW)` 직렬화 비용도 있다.

대량 배치 INSERT에 트리거가 걸려있으면 배치 시간이 수 배로 늘어날 수 있다. 100만 건 INSERT를 실행했을 때 트리거 없이 4.2초, 트리거 포함 시 11.7초가 나온 경우가 있다. 마이그레이션 배치는 트리거를 임시 비활성화하고 실행하되, 비활성화 자체와 실행 내역은 별도로 기록해야 한다.

```sql
-- 배치 작업 전후 (SUPERUSER 권한 필요)
ALTER TABLE users DISABLE TRIGGER users_audit;
-- ... 배치 실행 ...
ALTER TABLE users ENABLE TRIGGER users_audit;
```

비활성화 이력을 pg_audit이나 외부 시스템에 남겨두면 "해당 시간대 감사 공백"을 설명할 수 있다.

## audit_log 테이블 파티셔닝

파티셔닝 없이 운영하면 6개월쯤 뒤부터 조회 속도 저하가 눈에 띈다. 시간 기반 월별 파티셔닝이 일반적이다.

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL,
    table_name  TEXT        NOT NULL,
    operation   TEXT        NOT NULL,
    row_id      TEXT        NOT NULL,
    old_data    JSONB,
    new_data    JSONB,
    changed_by  TEXT,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    app_user_id TEXT,
    client_addr INET
) PARTITION BY RANGE (changed_at);

-- 파티션 생성
CREATE TABLE audit_log_2026_09
    PARTITION OF audit_log
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

CREATE TABLE audit_log_2026_10
    PARTITION OF audit_log
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
```

파티션은 사전에 만들어둬야 한다. 파티션이 없는 날짜 범위에 INSERT를 시도하면 오류가 난다. cron이나 Airflow로 매월 다음 달 파티션을 자동 생성하는 작업을 걸어야 한다.

```sql
-- 다음 달 파티션 자동 생성
DO $$
DECLARE
    next_month     DATE := date_trunc('month', now() + INTERVAL '1 month');
    partition_name TEXT := 'audit_log_' || to_char(next_month, 'YYYY_MM');
    start_date     TEXT := to_char(next_month, 'YYYY-MM-DD');
    end_date       TEXT := to_char(next_month + INTERVAL '1 month', 'YYYY-MM-DD');
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_log FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END $$;
```

오래된 파티션은 `DROP TABLE`로 삭제한다. 파티션 전체를 드롭하면 DELETE보다 훨씬 빠르고 테이블 bloat이 없다.

```sql
-- 보존 기간 초과 파티션 삭제
DROP TABLE IF EXISTS audit_log_2024_09;
```

파티션 삭제 전에 해당 기간 로그가 규제 보존 기간 밖에 있는지 반드시 확인한다. 삭제 작업 자체도 감사 로그 관리 대장에 기록해둔다.

## DB 감사와 애플리케이션 감사의 역할 분담

두 레이어를 모두 운영할 때 같은 이벤트가 두 군데 기록된다. 조사 시 혼란을 줄이려면 역할을 나눠야 한다.

**DB 레벨**은 DML 전수 기록을 담당한다. 누가, 언제, 어떤 SQL을, 어떤 행에 실행했는지. 애플리케이션 컨텍스트(어느 API 엔드포인트, 비즈니스 이벤트 의미)는 없다.

**애플리케이션 레벨**은 비즈니스 이벤트를 기록한다. 결제 승인, 계정 정지, 권한 변경처럼 DB 쿼리 수준보다 높은 추상화 단위다. `actor`, `action.type`, `resource` 구조로 감사 심사에서 쓸 수 있는 포맷이다.

두 레이어가 `trace_id`로 연결되면 침해 조사에서 "이 비즈니스 이벤트가 실제로 어떤 SQL을 실행했는가"를 추적할 수 있다. 애플리케이션이 트랜잭션 시작 시 `SET LOCAL application.trace_id = '...'`를 실행하고, 트리거가 그 값을 `audit_log`에 저장하면 연결고리가 생긴다.
