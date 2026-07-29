---
title: Codd 12 Rules
tags: [database, codd, relational-model, rdbms, integrity, normalization, sql]
updated: 2026-07-28
---

# Codd 12 Rules

Edgar Codd가 1985년 *Computerworld* 기고문에서 정의한 13개 규칙이다. Rule 0부터 Rule 12까지라 "12 Rules"라고 불리는데, Rule 0이 나머지 12개의 메타 규칙 역할을 한다.

당시 IBM이 SQL/DS와 DB2를 "관계형 데이터베이스"로 마케팅하면서 정작 관계형 모델을 제대로 구현하지 않는 상황에 Codd가 반응한 것이다. 규칙의 본질은 "RDBMS를 자처하려면 이 조건들을 만족해야 한다"는 기준 제시다.

MySQL, PostgreSQL 모두 이 규칙들을 완전히 충족하지 않는다. 규칙이 이론적으로 완벽한 관계형 시스템을 기술하기 때문에 실무 RDBMS는 대부분 어느 지점에서 타협한다.

---

## Rule 0: Foundation Rule

**RDBMS를 표방하는 시스템은 관계형 기능만으로 데이터를 완전하게 관리할 수 있어야 한다.**

나머지 12개 규칙의 전제다. 관계형 인터페이스를 제공하면서 핵심 기능은 비관계형 방식으로만 접근 가능한 시스템은 Rule 0부터 위반한다.

위반 사례로 자주 나오는 게 초기 MySQL이다. 트랜잭션은 `BEGIN`/`COMMIT` SQL로 제어 가능했지만, 일부 데이터 정합성 기능은 스토리지 엔진 레이어에서만 처리되고 SQL 레벨에서는 제어할 수 없었다. 외래키 제약이 MyISAM에서는 파싱은 되지만 무시되던 것이 대표적이다.

```sql
-- MyISAM에서는 이 외래키가 파싱은 되지만 적용 안 됨
CREATE TABLE orders (
    order_id  INT PRIMARY KEY,
    user_id   INT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=MyISAM;

-- user_id=9999가 users에 없어도 INSERT 성공
INSERT INTO orders VALUES (1, 9999);
```

InnoDB로 전환하면서 이 문제는 해소됐지만, MySQL에서 여전히 `SET FOREIGN_KEY_CHECKS=0`으로 외래키를 통째로 끄는 관행이 남아 있다.

---

## Rule 1: Information Rule

**관계형 데이터베이스의 모든 정보는 테이블의 열값으로만 표현된다.**

데이터를 저장하는 방법이 오직 테이블 행의 값이어야 한다는 뜻이다. 파일 경로, 포인터, 메타데이터 파일, 숨겨진 시스템 컬럼 같은 수단으로 정보를 표현하면 위반이다.

실무에서 이 규칙이 어긋나는 경우는 주로 ORM이나 프레임워크가 테이블 외부에 스키마 정보를 저장할 때 발생한다. 마이그레이션 이력을 별도 파일로만 관리하고 DB 카탈로그에 반영하지 않는다거나, 타입 정보를 ORM 코드에만 두고 DB에는 `VARCHAR` 하나로 퉁치는 식이다.

```sql
-- 위반: 상태값을 DB 밖에서 정의하고 DB에는 숫자만 저장
-- application code에 Status.PENDING=0, Status.ACTIVE=1로만 존재
CREATE TABLE orders (
    status TINYINT NOT NULL  -- 0=대기, 1=처리중, 2=완료 (코드에만 있음)
);

-- 준수: 의미가 DB에도 표현됨
CREATE TABLE orders (
    status ENUM('PENDING', 'PROCESSING', 'COMPLETED') NOT NULL
);

-- 또는 별도 코드 테이블
CREATE TABLE order_statuses (
    code        TINYINT     PRIMARY KEY,
    description VARCHAR(50) NOT NULL
);
```

---

## Rule 2: Guaranteed Access Rule

**관계형 데이터베이스의 모든 원자 값은 테이블 이름, 기본키 값, 컬럼 이름의 조합으로 접근 가능해야 한다.**

기본키가 없는 테이블, 중복 행이 있는 테이블은 이 규칙을 위반한다. 중복 행이 있으면 특정 행을 유일하게 지정할 방법이 없다.

MySQL에서 기본키 없는 테이블은 만들 수 있다. InnoDB는 내부적으로 숨겨진 6바이트 rowid를 생성하지만, 이 rowid는 SQL로 직접 접근 불가능하다. Rule 2 관점에서는 rowid는 "테이블 이름, 기본키, 컬럼 이름" 조합이 아니다.

```sql
-- Rule 2 위반: 기본키 없음, 중복 행 허용
CREATE TABLE event_log (
    event_type VARCHAR(50),
    occurred_at TIMESTAMP
);

-- 같은 이벤트가 두 번 들어오면 둘 중 특정 행에 접근할 방법이 없다
INSERT INTO event_log VALUES ('LOGIN', '2026-07-28 10:00:00');
INSERT INTO event_log VALUES ('LOGIN', '2026-07-28 10:00:00');
```

실무에서 로그 테이블이나 임시 집계 테이블에 기본키를 빼는 경우가 있다. INSERT 속도 때문이다. 특정 행을 삭제하거나 수정할 필요가 없다면 문제가 드러나지 않지만, 나중에 중복 제거나 특정 레코드 수정이 필요해지면 난감해진다.

---

## Rule 3: Systematic Treatment of Null Values

**NULL은 모든 데이터 타입에서 누락된 정보와 적용 불가 정보를 표현하기 위해 체계적으로 지원돼야 한다.**

NULL이 숫자 0이나 빈 문자열과 구분되어야 하고, NULL을 다루는 연산이 일관성 있게 동작해야 한다.

이 규칙 자체는 대부분의 RDBMS가 지원한다. 문제는 NULL의 3값 논리(True, False, Unknown)가 직관에 어긋나는 결과를 만들 때다.

```sql
-- NULL 비교의 함정
SELECT NULL = NULL;   -- NULL (Unknown, True가 아님)
SELECT NULL != NULL;  -- NULL (Unknown)
SELECT NULL IS NULL;  -- 1 (True)

-- WHERE 절에서 NULL 행이 빠지는 이유
SELECT * FROM users WHERE deleted_at != '2026-01-01';
-- deleted_at이 NULL인 행은 결과에 포함 안 됨
-- NULL != '2026-01-01'은 Unknown이므로 WHERE 조건 불충족

-- 의도한 결과를 얻으려면
SELECT * FROM users WHERE deleted_at != '2026-01-01' OR deleted_at IS NULL;
```

NULL이 포함된 집계도 주의해야 한다.

```sql
SELECT AVG(score) FROM students;
-- score가 NULL인 학생은 분모와 분자 모두에서 제외됨
-- "점수 기록이 없는 학생"과 "0점 학생"이 다르게 처리됨

SELECT AVG(COALESCE(score, 0)) FROM students;
-- NULL을 0으로 처리하려면 COALESCE 필요
```

Rule 3를 준수한다고 해서 NULL이 편하다는 뜻이 아니다. NULL을 남발하면 쿼리가 복잡해지고 버그 발생 빈도가 올라간다. NOT NULL 제약으로 막을 수 있는 컬럼은 처음부터 막는 편이 낫다.

---

## Rule 4: Dynamic Online Catalog Based on the Relational Model

**데이터베이스의 메타데이터(스키마 정보)는 일반 데이터와 같은 방식으로 저장되고 동일한 쿼리 언어로 조회 가능해야 한다.**

`information_schema`가 이 규칙의 구현이다. 테이블 목록, 컬럼 정의, 인덱스, 제약 조건 모두 SQL로 조회할 수 있다.

```sql
-- 특정 테이블의 컬럼 정보 조회
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'mydb'
  AND table_name   = 'users'
ORDER BY ordinal_position;

-- 외래키 제약 확인
SELECT constraint_name, table_name, column_name, referenced_table_name, referenced_column_name
FROM information_schema.key_column_usage
WHERE referenced_table_schema = 'mydb';

-- 인덱스가 없는 테이블 찾기
SELECT t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.statistics s
       ON t.table_schema = s.table_schema
      AND t.table_name   = s.table_name
WHERE t.table_schema = 'mydb'
  AND t.table_type   = 'BASE TABLE'
  AND s.index_name IS NULL;
```

PostgreSQL은 `pg_catalog` 스키마로 더 상세한 메타데이터를 제공한다. MySQL의 `information_schema`는 일부 항목이 실시간이 아닌 캐시된 값을 반환하는 경우가 있다. `table_rows` 컬럼이 그렇다. 정확한 행 수가 필요하면 `SELECT COUNT(*)`를 직접 써야 한다.

---

## Rule 5: Comprehensive Data Sublanguage Rule

**시스템은 데이터 정의, 뷰 정의, 데이터 조작, 무결성 제약, 권한 관리, 트랜잭션 경계를 모두 하나의 언어로 처리할 수 있어야 한다.**

SQL이 이 규칙의 답이다. DDL(CREATE, ALTER, DROP), DML(SELECT, INSERT, UPDATE, DELETE), DCL(GRANT, REVOKE), TCL(BEGIN, COMMIT, ROLLBACK)이 모두 SQL 안에 있다.

Rule 5 위반처럼 보이는 경우는 PostgreSQL의 PL/pgSQL이나 MySQL의 스토어드 프로시저를 필수로 써야만 처리 가능한 로직이 생길 때다. SQL 표준만으로 표현 불가능한 제약이나 로직을 절차형 언어로만 구현하면, SQL 외부에 비즈니스 규칙이 분산된다.

```sql
-- 무결성 제약을 SQL로 표현 (Rule 5 준수)
ALTER TABLE orders
    ADD CONSTRAINT chk_positive_amount CHECK (amount > 0);

ALTER TABLE users
    ADD CONSTRAINT uq_email UNIQUE (email);

-- 권한 관리
GRANT SELECT, INSERT ON orders TO app_user;
REVOKE DELETE ON orders FROM app_user;

-- 트랜잭션
BEGIN;
UPDATE accounts SET balance = balance - 1000 WHERE user_id = 1;
UPDATE accounts SET balance = balance + 1000 WHERE user_id = 2;
COMMIT;
```

---

## Rule 6: View Updating Rule

**이론적으로 갱신 가능한 뷰는 시스템이 실제로 갱신을 허용해야 한다.**

단순 뷰(하나의 기반 테이블에서 일부 컬럼과 행을 선택한 뷰)는 이론적으로 갱신 가능하다. 집계나 DISTINCT, 복수 테이블 JOIN이 포함된 뷰는 갱신이 어렵거나 불가능하다.

MySQL과 PostgreSQL 모두 단순 뷰의 `INSERT`, `UPDATE`, `DELETE`를 지원한다.

```sql
-- 단순 뷰: 갱신 가능
CREATE VIEW active_users AS
SELECT user_id, email, name
FROM users
WHERE deleted_at IS NULL;

UPDATE active_users SET name = '홍길동' WHERE user_id = 1;
-- users.name이 실제로 업데이트됨

-- 집계 뷰: 갱신 불가
CREATE VIEW user_order_count AS
SELECT user_id, COUNT(*) AS order_count
FROM orders
GROUP BY user_id;

UPDATE user_order_count SET order_count = 5 WHERE user_id = 1;
-- 오류: 집계가 포함된 뷰는 갱신 불가
```

PostgreSQL은 `INSTEAD OF` 트리거로 복잡한 뷰의 갱신을 구현할 수 있다.

```sql
CREATE OR REPLACE FUNCTION update_active_user()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users SET name = NEW.name WHERE user_id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_active_users
INSTEAD OF UPDATE ON active_users
FOR EACH ROW EXECUTE FUNCTION update_active_user();
```

Rule 6가 "이론적으로 가능한 경우"라고 명시한 이유는 모든 뷰가 갱신 가능하다는 게 아니라, 가능한 경우는 시스템이 막지 말아야 한다는 뜻이다. 현실에서는 갱신 가능한 뷰를 쓰기 인터페이스로 노출하는 경우가 드물다. 뷰는 주로 읽기 용도로 쓴다.

---

## Rule 7: High-Level Insert, Update, and Delete

**데이터 조작은 단건이 아닌 집합 단위로 처리 가능해야 한다.**

SQL의 `WHERE` 절로 여러 행을 한 번에 처리하는 게 이 규칙의 핵심이다. 행 단위 반복 처리를 강제하는 언어는 Rule 7을 위반한다.

```sql
-- 집합 기반 처리 (Rule 7 준수)
UPDATE products SET price = price * 1.1 WHERE category_id = 5;
DELETE FROM sessions WHERE expired_at < NOW() - INTERVAL 7 DAY;

-- 비교: 애플리케이션 레벨 반복 처리
-- 이걸 한다고 Rule 7을 "위반"하는 건 아니지만, RDBMS가 제공하는 기능을 쓰지 않는 것
for (let product of products) {
    await db.query('UPDATE products SET price = ? WHERE product_id = ?',
        [product.price * 1.1, product.id]);
}
```

ORM을 쓸 때 이 규칙이 실무에서 문제가 되는 지점이 있다. TypeORM의 `save()` 메서드는 엔티티 하나를 받아서 단건 UPDATE를 발생시킨다. 1000개 행을 업데이트하려면 1000번의 쿼리가 나간다.

```typescript
// 비효율: 1000번 UPDATE
for (const user of users) {
    user.isVerified = true;
    await userRepository.save(user);
}

// 집합 기반: 1번 UPDATE
await userRepository.update(
    { isVerified: false, createdAt: LessThan(thirtyDaysAgo) },
    { isVerified: true }
);

// 또는 QueryBuilder
await userRepository.createQueryBuilder()
    .update()
    .set({ isVerified: true })
    .where('is_verified = false AND created_at < :date', { date: thirtyDaysAgo })
    .execute();
```

---

## Rule 8: Physical Data Independence

**저장소 표현 방식이나 접근 방법을 변경해도 애플리케이션은 영향을 받지 않아야 한다.**

인덱스를 추가하거나 제거해도 SQL 쿼리 자체는 바뀌지 않는다. 테이블스페이스를 다른 디스크로 옮겨도 쿼리는 그대로 동작한다. 이게 Rule 8이다.

MySQL과 PostgreSQL 모두 이 규칙을 잘 지원한다. 운영 중 인덱스 추가/삭제, 파티션 변경, 스토리지 파라미터 조정이 가능하다.

```sql
-- 인덱스 추가: 기존 쿼리 변경 없이 성능만 달라짐
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- 쿼리는 그대로
SELECT * FROM orders WHERE user_id = 123;

-- InnoDB에서 테이블스페이스 이동 (파일 경로 변경)
ALTER TABLE large_table TABLESPACE fast_ssd;

-- 파티션 추가 (MySQL)
ALTER TABLE logs PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027)
);
-- SELECT는 기존과 동일하게 동작
```

Rule 8이 실무에서 어긋나는 경우는 ORM이 내부 구조를 가정하는 힌트나 쿼리를 생성할 때다. MySQL에서 `FORCE INDEX` 힌트를 코드에 박아 두면, 인덱스 이름이 바뀌거나 인덱스가 재구성되면 쿼리가 깨진다.

```sql
-- 이 힌트는 물리 구조에 의존
SELECT * FROM orders FORCE INDEX (idx_orders_status) WHERE status = 'PENDING';
-- idx_orders_status가 삭제되면 쿼리 오류 발생
```

---

## Rule 9: Logical Data Independence

**기반 테이블에 정보 보존적 변경을 가해도 애플리케이션은 영향을 받지 않아야 한다.**

테이블에 컬럼을 추가하거나 테이블을 분리해도 기존 뷰와 애플리케이션이 동작해야 한다는 뜻이다.

Rule 8보다 달성하기 어렵다. 컬럼을 추가하면 `SELECT *`를 쓰는 코드가 예상 밖의 컬럼을 받게 된다. 테이블 분리 후 기존 쿼리가 깨지는 경우도 많다.

```sql
-- users 테이블에 컬럼 추가
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);

-- SELECT *를 쓰는 코드는 phone_number를 받게 됨
-- 일부 ORM은 이를 알 수 없는 컬럼으로 오류 처리하기도 함

-- 뷰로 논리 구조를 추상화하면 Rule 9에 더 가까워짐
CREATE VIEW user_profile AS
SELECT user_id, email, name  -- 필요한 컬럼만 선택
FROM users;
-- 기반 테이블에 컬럼이 추가돼도 뷰를 통한 조회는 영향 없음
```

테이블 분리 시나리오는 더 복잡하다.

```sql
-- 기존 구조
-- users: user_id, email, name, bio, profile_image_url, ...

-- users 테이블을 users와 user_profiles로 분리
CREATE TABLE user_profiles (
    user_id           BIGINT PRIMARY KEY REFERENCES users(user_id),
    bio               TEXT,
    profile_image_url VARCHAR(500)
);
ALTER TABLE users DROP COLUMN bio, DROP COLUMN profile_image_url;

-- 기존 쿼리 보호를 위한 뷰
CREATE VIEW users_v AS
SELECT u.user_id, u.email, u.name,
       p.bio, p.profile_image_url
FROM users u
LEFT JOIN user_profiles p ON u.user_id = p.user_id;
```

이론적으로는 뷰로 보호하면 되지만, 뷰 위에서 `INSERT`/`UPDATE`가 동작하게 만드는 건 복잡하다. Rule 9는 현실 RDBMS 운영에서 완전히 지켜지기 어렵다.

---

## Rule 10: Integrity Independence

**무결성 제약은 데이터베이스에 저장되어야 하고 SQL로 정의 가능해야 한다. 애플리케이션 코드에만 존재해서는 안 된다.**

이 규칙이 실무에서 가장 많이 위반된다.

```sql
-- Rule 10 준수: 제약이 DB에 저장됨
ALTER TABLE orders
    ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    ADD CONSTRAINT chk_amount     CHECK (amount > 0),
    ADD CONSTRAINT chk_status     CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED'));

-- Rule 10 위반: 제약이 애플리케이션 코드에만 있음
// service code
if (amount <= 0) throw new Error('금액은 0보다 커야 합니다');
if (!['PENDING', 'PROCESSING', 'COMPLETED'].includes(status)) {
    throw new Error('유효하지 않은 상태값');
}
```

애플리케이션 코드에만 제약이 있으면, 배치 스크립트, 마이그레이션, DBA의 직접 쿼리, 다른 서비스의 DB 접근 등 우회 경로가 항상 존재한다.

MySQL에서 Rule 10을 위반하게 되는 흔한 이유:

```sql
-- MySQL 8.0 이전: CHECK 제약이 파싱은 되지만 실행 시 무시됨
CREATE TABLE products (
    price DECIMAL(10, 2) CHECK (price > 0)  -- MySQL 5.7에서 무시됨
);

INSERT INTO products (price) VALUES (-100);  -- 성공해버림
```

MySQL 8.0.16부터 CHECK 제약이 실제로 동작한다. 그 이전 버전을 쓰던 팀은 CHECK 대신 트리거로 제약을 구현하거나 애플리케이션에만 두는 방식을 택했고, 그 관행이 8.0 이후에도 남아 있는 경우가 있다.

외래키 제약을 끄는 것도 Rule 10 위반이다.

```sql
-- 마이그레이션에서 자주 보이는 패턴
SET FOREIGN_KEY_CHECKS = 0;
-- ... 데이터 조작
SET FOREIGN_KEY_CHECKS = 1;
```

이 패턴은 마이그레이션 중 일시적으로 정합성을 포기하는 것이다. 스크립트가 중간에 실패하면 외래키가 꺼진 상태에서 정합성이 깨진 데이터가 남는다.

---

## Rule 11: Distribution Independence

**사용자는 데이터가 어디에 분산되어 있는지 알 필요가 없어야 한다. 단일 서버에 있을 때와 동일한 SQL로 접근 가능해야 한다.**

샤딩, 파티셔닝, 복제 구조가 SQL 인터페이스 뒤에 숨어 있어야 한다.

MySQL과 PostgreSQL은 단일 인스턴스 수준에서 파티셔닝을 투명하게 처리한다.

```sql
-- 파티션 테이블: SQL은 동일, 물리 저장만 분산
SELECT * FROM logs WHERE created_at BETWEEN '2026-01-01' AND '2026-03-31';
-- 쿼리 플래너가 자동으로 해당 파티션만 읽음 (Partition Pruning)
```

이 규칙이 현실에서 부서지는 지점은 샤딩이다. 샤딩을 애플리케이션 레이어에서 처리하면, 어느 샤드를 쓸지 결정하는 로직이 코드에 드러난다.

```typescript
// 샤드 키 기반 라우팅이 애플리케이션 코드에 노출됨 (Rule 11 위반)
const shardIndex = userId % SHARD_COUNT;
const ds = shardDataSources[shardIndex];
```

Vitess(MySQL), Citus(PostgreSQL) 같은 솔루션이 Rule 11을 지키면서 샤딩하려는 시도다. 이 레이어에서 라우팅을 처리해서 애플리케이션은 단일 엔드포인트만 보게 만든다.

크로스 샤드 JOIN이나 트랜잭션은 여전히 문제다. 분산 트랜잭션의 복잡도 때문에 많은 팀이 Rule 11을 포기하고 애플리케이션 레벨 샤딩을 선택한다.

---

## Rule 12: Nonsubversion Rule

**행 단위 저수준 인터페이스가 있더라도, 그 인터페이스로 SQL 레벨의 무결성 제약을 우회할 수 없어야 한다.**

저수준 API로 DB에 직접 접근해도 CHECK 제약, 외래키, NOT NULL 같은 제약을 건너뛸 수 없어야 한다는 뜻이다.

InnoDB 스토리지 엔진은 내부 API로 직접 접근하더라도 무결성 제약을 강제한다. 문제는 SQL 레이어가 아닌 파일 레벨 접근이다.

```
실제 Rule 12 위반 시나리오:
- mysqldump로 백업 후 복원 시 SET FOREIGN_KEY_CHECKS=0으로 제약 없이 삽입
- MySQL 데이터 파일(.ibd)을 직접 복사/교체
- MySQL의 innochecksum 도구를 우회한 파일 수정
- MyISAM 테이블의 .MYD 파일 직접 편집
```

현실에서 가장 흔한 Rule 12 위반은 `SET FOREIGN_KEY_CHECKS=0`으로 외래키를 끄거나, `SET SQL_MODE=''`로 엄격 모드를 비활성화하는 것이다.

```sql
-- Rule 12 위반: 제약을 SQL로 끄고 비정상 데이터 삽입
SET SQL_MODE = '';
SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO order_items (order_id, product_id, quantity)
VALUES (99999, 99999, -1);  -- 존재하지 않는 order/product, 음수 수량

SET FOREIGN_KEY_CHECKS = 1;
SET SQL_MODE = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,...';
```

---

## 실무에서 이 규칙들이 지켜지지 않는 이유

Codd가 정의한 규칙은 이상적인 관계형 시스템의 스펙이다. 현실 RDBMS는 성능, 운영 편의성, 하위 호환성 때문에 타협한다.

**성능 트레이드오프**가 가장 크다. 외래키 제약은 참조 무결성을 보장하지만, 대규모 INSERT 배치에서 매 행마다 참조 테이블을 조회하는 오버헤드가 발생한다. 초당 수만 건의 이벤트를 처리하는 시스템에서 외래키를 켜면 처리량이 눈에 띄게 떨어진다. 이 때문에 외래키를 끄고 정합성을 애플리케이션으로 가져가는 선택을 하는 팀이 있다.

```sql
-- 외래키 유무에 따른 INSERT 성능 차이 측정
-- 10만 건 INSERT
-- 외래키 있음: ~8.2초
-- 외래키 없음: ~1.4초 (실측값은 환경마다 다름)
```

**마이그레이션 편의성**도 이유가 된다. 레거시 데이터를 새 스키마로 옮길 때 모든 제약을 켠 채로 마이그레이션하면 순서 문제가 생긴다. 부모 테이블을 먼저 채워야 자식 테이블을 채울 수 있는데, 원본 DB에서 그 순서를 정확히 따르기가 까다로울 수 있다.

**샤딩이나 분산 구조**로 전환할 때 Rule 11이 무너진다. 단일 RDBMS로 감당이 안 되는 트래픽에서 샤딩은 불가피하고, 완전한 투명성을 유지하는 미들웨어를 도입하는 것보다 애플리케이션 레벨 샤딩이 더 쉬운 선택이다.

결국 이 규칙들의 가치는 "모두 지켜야 한다"가 아니라, "어느 규칙을 왜 포기했는지 의식적으로 알고 있어야 한다"에 있다. Rule 10을 어기고 제약을 코드에만 두기로 했다면, 그 결정이 어떤 리스크를 만드는지 팀이 알아야 한다. 외래키를 끈 채로 운영한다면 정합성 검증 쿼리를 주기적으로 돌리는 보완이 필요하다.
