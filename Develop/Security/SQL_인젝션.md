---
title: SQL Injection (SQL 인젝션)
tags: [database, security, sql-injection, web-security, owasp]
updated: 2026-03-28
---

# SQL Injection (SQL 인젝션)

## 정의

SQL 인젝션은 사용자 입력값이 SQL 쿼리의 일부로 해석되면서, 공격자가 의도하지 않은 쿼리를 실행할 수 있는 취약점이다. 2024년 기준 OWASP Top 10에 여전히 포함되어 있고, 실무에서도 자주 발견된다.

발생 원인은 단순하다.

- 사용자 입력을 문자열 연결로 쿼리에 넣는다
- 파라미터 바인딩을 쓰지 않는다
- DB 오류 메시지를 클라이언트에 그대로 내려준다

## 공격 방식

### 인증 우회

가장 흔한 형태다. 로그인 쿼리에서 패스워드 검증을 무력화한다.

```sql
-- 원본 쿼리
SELECT * FROM users WHERE username = '$username' AND password = '$password';

-- 공격자 입력: username에 admin' -- 입력
SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything';
-- 주석 처리로 패스워드 검증이 사라진다
```

### UNION 기반 데이터 추출

다른 테이블의 데이터를 끌어올 수 있다. 컬럼 수가 맞아야 하므로 공격자는 먼저 `ORDER BY`로 컬럼 수를 파악한다.

```sql
-- 원본 쿼리
SELECT product_name, price FROM products WHERE category = '$category';

-- 공격자 입력
Electronics' UNION SELECT username, password FROM users --

-- 결과: 상품 목록에 사용자 계정 정보가 섞여 나온다
```

### 블라인드 SQL 인젝션

에러 메시지가 안 보여도 응답 시간이나 참/거짓 차이로 데이터를 한 글자씩 뽑아낸다.

```sql
-- Boolean 기반: 응답 내용 차이로 판별
SELECT * FROM users WHERE id = 1 AND (SELECT LENGTH(password) FROM users WHERE username='admin') = 8;

-- Time 기반: 응답 시간 차이로 판별
SELECT * FROM users WHERE id = 1 AND IF(LENGTH(password)=8, SLEEP(5), 0);
```

Time 기반은 WAF를 우회하기 쉬워서 실제 공격에서 많이 쓰인다. `SLEEP` 대신 `BENCHMARK()`나 heavy query를 쓰는 변형도 있다.

## 방어 방법

### Prepared Statement — 가장 확실한 방어

파라미터 바인딩을 쓰면 사용자 입력이 SQL 구문이 아닌 값으로만 처리된다. 모든 언어, 모든 DB 드라이버가 지원한다.

**Node.js (MySQL / PostgreSQL):**

```javascript
// 취약한 코드
const query = `SELECT * FROM users WHERE id = ${userId}`;
connection.query(query);

// MySQL — ? 플레이스홀더
const query = 'SELECT * FROM users WHERE id = ?';
connection.query(query, [userId]);

// PostgreSQL — $1, $2 플레이스홀더
const query = 'SELECT * FROM users WHERE username = $1 AND email = $2';
client.query(query, [username, email]);
```

**Java — JdbcTemplate:**

```java
// 취약한 코드
String sql = "SELECT * FROM users WHERE username = '" + username + "'";
jdbcTemplate.queryForList(sql);

// 안전한 코드 — ? 바인딩
String sql = "SELECT * FROM users WHERE username = ? AND status = ?";
jdbcTemplate.queryForList(sql, username, "ACTIVE");
```

**Java — JPA (JPQL):**

```java
// 취약한 코드 — 문자열 연결
String jpql = "SELECT u FROM User u WHERE u.username = '" + username + "'";
em.createQuery(jpql).getResultList();

// 안전한 코드 — 파라미터 바인딩
String jpql = "SELECT u FROM User u WHERE u.username = :username";
em.createQuery(jpql, User.class)
  .setParameter("username", username)
  .getResultList();
```

JPA의 `Criteria API`를 쓰면 쿼리 자체가 코드로 생성되므로 인젝션 가능성이 없다. 하지만 `@Query`에 `nativeQuery = true`로 네이티브 쿼리를 쓸 때는 반드시 파라미터 바인딩을 해야 한다.

```java
// Spring Data JPA — nativeQuery 사용 시
@Query(value = "SELECT * FROM users WHERE email = :email", nativeQuery = true)
List<User> findByEmail(@Param("email") String email);
```

**MyBatis:**

```xml
<!-- 취약한 코드 — ${} 사용 -->
<select id="findUser" resultType="User">
  SELECT * FROM users WHERE username = '${username}'
</select>

<!-- 안전한 코드 — #{} 사용 -->
<select id="findUser" resultType="User">
  SELECT * FROM users WHERE username = #{username}
</select>
```

MyBatis에서 `${}`는 문자열 치환이고 `#{}`는 파라미터 바인딩이다. `${}`는 테이블명이나 컬럼명 같은 식별자에만 써야 하고, 사용자 입력에는 절대 쓰면 안 된다. 코드 리뷰에서 `${}` 사용처를 검색하는 것만으로도 취약점을 찾아낼 수 있다.

### ORM을 쓰면서도 취약한 경우

ORM을 쓴다고 자동으로 안전하지는 않다. raw query나 literal 표현식을 쓰는 순간 같은 문제가 생긴다.

**Sequelize — `literal()` 함수:**

```javascript
// 취약한 코드 — literal()에 사용자 입력을 넣으면 그대로 SQL이 된다
const users = await User.findAll({
  where: Sequelize.literal(`username = '${userInput}'`)
});

// 안전한 코드 — where 객체 사용
const users = await User.findAll({
  where: { username: userInput }
});

// literal()을 써야 하는 경우 — 바인딩 사용
const users = await User.findAll({
  where: Sequelize.literal('username = ?'),
  replacements: [userInput]
});
```

`Sequelize.literal()`은 계산 컬럼이나 DB 함수 호출에 쓰는 것이고, 사용자 입력을 넣는 용도가 아니다.

**TypeORM — raw query와 QueryBuilder 오용:**

```typescript
// 취약한 코드 — query()에 문자열 연결
const users = await dataSource.query(
  `SELECT * FROM users WHERE name = '${name}'`
);

// 취약한 코드 — QueryBuilder에 문자열 연결
const users = await userRepository
  .createQueryBuilder("user")
  .where(`user.name = '${name}'`)
  .getMany();

// 안전한 코드 — 파라미터 바인딩
const users = await userRepository
  .createQueryBuilder("user")
  .where("user.name = :name", { name })
  .getMany();
```

TypeORM의 `QueryBuilder`를 쓰더라도 `.where()` 안에 문자열 연결을 하면 인젝션에 취약하다. `:name` 같은 named parameter를 쓰고 두 번째 인자로 값을 넘겨야 한다.

**Django ORM — `extra()`와 `RawSQL`:**

```python
# 취약한 코드
User.objects.extra(where=[f"username = '{name}'"])

# 안전한 코드
User.objects.filter(username=name)

# raw query가 필요한 경우
User.objects.raw("SELECT * FROM users WHERE username = %s", [name])
```

Django의 `extra()`는 deprecated 상태이고 SQL 인젝션 위험이 있으므로 쓰지 않는다.

### 동적 쿼리 안전하게 만들기

검색 필터, 정렬, 페이징 같은 기능에서 동적 쿼리를 만들어야 하는 경우가 많다. 이때 파라미터 바인딩만으로는 해결이 안 되는 부분이 있다.

**동적 WHERE 조건:**

```java
// Java — 조건부 WHERE 절 추가
public List<User> search(String name, String email, String status) {
    StringBuilder sql = new StringBuilder("SELECT * FROM users WHERE 1=1");
    List<Object> params = new ArrayList<>();

    if (name != null) {
        sql.append(" AND name = ?");
        params.add(name);
    }
    if (email != null) {
        sql.append(" AND email = ?");
        params.add(email);
    }
    if (status != null) {
        sql.append(" AND status = ?");
        params.add(status);
    }

    return jdbcTemplate.queryForList(sql.toString(), params.toArray());
}
```

값은 파라미터 바인딩으로 넣고, 쿼리 구조(어떤 조건을 붙일지)는 서버 코드에서 결정한다.

**동적 ORDER BY:**

ORDER BY 절에는 파라미터 바인딩을 쓸 수 없다. 컬럼명은 값이 아니라 식별자이기 때문이다.

```java
// 취약한 코드 — 사용자 입력을 ORDER BY에 직접 넣는다
String sql = "SELECT * FROM users ORDER BY " + sortColumn + " " + sortDirection;

// 안전한 코드 — 화이트리스트로 검증
private static final Map<String, String> ALLOWED_COLUMNS = Map.of(
    "name", "name",
    "email", "email",
    "created", "created_at"  // 클라이언트 키와 실제 컬럼명을 분리
);

private static final Set<String> ALLOWED_DIRECTIONS = Set.of("ASC", "DESC");

public List<User> findAllSorted(String sortColumn, String sortDirection) {
    String column = ALLOWED_COLUMNS.get(sortColumn);
    if (column == null) {
        column = "created_at"; // 기본값
    }

    String direction = ALLOWED_DIRECTIONS.contains(sortDirection.toUpperCase())
        ? sortDirection.toUpperCase()
        : "ASC";

    String sql = "SELECT * FROM users ORDER BY " + column + " " + direction;
    return jdbcTemplate.queryForList(sql);
}
```

클라이언트가 보낸 값을 그대로 쓰지 않고, 미리 정의한 맵에서 실제 컬럼명을 꺼내 쓴다. 클라이언트에 실제 테이블 컬럼명을 노출하지 않는 효과도 있다.

**동적 IN 절:**

```java
// 취약한 코드 — 문자열 연결로 IN 절 생성
String ids = String.join(",", userIds); // "1,2,3" 이겠지만 보장할 수 없다
String sql = "SELECT * FROM users WHERE id IN (" + ids + ")";

// 안전한 코드 — 플레이스홀더 동적 생성
public List<User> findByIds(List<Long> ids) {
    String placeholders = ids.stream()
        .map(id -> "?")
        .collect(Collectors.joining(","));

    String sql = "SELECT * FROM users WHERE id IN (" + placeholders + ")";
    return jdbcTemplate.queryForList(sql, ids.toArray());
}
```

```javascript
// Node.js — MySQL
const ids = [1, 2, 3];
const placeholders = ids.map(() => '?').join(',');
const sql = `SELECT * FROM users WHERE id IN (${placeholders})`;
connection.query(sql, ids);

// MySQL2 라이브러리는 배열을 자동으로 풀어준다
connection.query('SELECT * FROM users WHERE id IN (?)', [ids]);
```

Spring의 `NamedParameterJdbcTemplate`을 쓰면 IN 절 처리가 간단하다.

```java
String sql = "SELECT * FROM users WHERE id IN (:ids)";
MapSqlParameterSource params = new MapSqlParameterSource("ids", ids);
namedParameterJdbcTemplate.queryForList(sql, params);
```

### Second-Order SQL Injection

입력 시점에는 문제가 없지만, 저장된 데이터가 다른 쿼리에서 사용될 때 발생하는 2차 인젝션이다. 1차 인젝션보다 발견하기 어렵고, 코드 리뷰에서도 놓치기 쉽다.

흐름은 이렇다.

1. 공격자가 회원가입 시 이름에 `admin'--`을 입력한다
2. 가입 처리 코드는 Prepared Statement를 써서 안전하게 저장한다 — 여기까지는 문제없다
3. 나중에 비밀번호 변경 기능에서 DB에 저장된 이름을 꺼내 다른 쿼리에 넣는다

```java
// 1단계: 회원가입 — Prepared Statement로 안전하게 저장
String insertSql = "INSERT INTO users (username, password) VALUES (?, ?)";
jdbcTemplate.update(insertSql, "admin'--", hashedPassword);
// DB에 username = "admin'--" 이 그대로 저장된다

// 2단계: 비밀번호 변경 — DB에서 꺼낸 값을 신뢰하고 문자열 연결
String username = getCurrentUserName(); // DB에서 "admin'--" 를 가져온다
String updateSql = "UPDATE users SET password = '" + newPassword
    + "' WHERE username = '" + username + "'";
// 실행되는 쿼리:
// UPDATE users SET password = 'newpw' WHERE username = 'admin'--'
// admin 계정의 비밀번호가 변경된다
```

방어 원칙은 간단하다. **DB에서 꺼낸 값이라도 쿼리에 넣을 때는 파라미터 바인딩을 쓴다.** "이 값은 우리 DB에서 나왔으니 안전하다"는 가정 자체가 위험하다.

```java
// 안전한 코드 — DB에서 꺼낸 값도 바인딩
String updateSql = "UPDATE users SET password = ? WHERE username = ?";
jdbcTemplate.update(updateSql, newPassword, username);
```

2차 인젝션이 발생하기 쉬운 패턴:

- 배치 작업에서 한 테이블의 데이터를 읽어 다른 쿼리에 사용하는 경우
- 로그 테이블의 데이터를 리포트 쿼리에 사용하는 경우
- 사용자가 설정한 값(프로필명, 팀명 등)을 관리자 페이지 쿼리에 사용하는 경우

### Stored Procedure와 SQL 인젝션

"Stored Procedure를 쓰면 SQL 인젝션을 막을 수 있다"는 말이 있는데, 반만 맞다.

Stored Procedure 안에서 파라미터를 바인딩하면 안전하다. 하지만 프로시저 내부에서 동적 SQL을 만들면 같은 문제가 생긴다.

```sql
-- 취약한 Stored Procedure — 동적 SQL에 문자열 연결
CREATE PROCEDURE SearchUsers(IN searchName VARCHAR(100))
BEGIN
    SET @sql = CONCAT('SELECT * FROM users WHERE name = ''', searchName, '''');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END;

-- 안전한 Stored Procedure — 파라미터 바인딩
CREATE PROCEDURE SearchUsers(IN searchName VARCHAR(100))
BEGIN
    SELECT * FROM users WHERE name = searchName;
    -- 파라미터가 직접 조건으로 사용되므로 인젝션 불가
END;

-- 동적 SQL이 필요한 경우 — PREPARE에 바인딩
CREATE PROCEDURE SearchUsers(IN searchName VARCHAR(100))
BEGIN
    SET @sql = 'SELECT * FROM users WHERE name = ?';
    SET @name = searchName;
    PREPARE stmt FROM @sql;
    EXECUTE stmt USING @name;
    DEALLOCATE PREPARE stmt;
END;
```

Stored Procedure를 방어 수단으로 쓸 때 주의할 점:

- 프로시저 내부에서 `CONCAT`으로 SQL을 만들면 인젝션에 취약하다. 특히 검색 기능에서 동적으로 조건을 붙이는 프로시저에 이 패턴이 많다
- 프로시저 호출 자체를 문자열 연결로 하면 의미가 없다. `"CALL SearchUsers('" + name + "')"` 이런 코드는 프로시저를 쓰는 의미가 없다
- 레거시 시스템에서 프로시저가 수백 개일 때, 어떤 프로시저가 내부에서 동적 SQL을 쓰는지 파악하기 어렵다. DB 카탈로그에서 `CONCAT`이나 `PREPARE`가 포함된 프로시저를 검색해서 점검한다

```sql
-- MySQL에서 동적 SQL을 사용하는 프로시저 찾기
SELECT ROUTINE_NAME, ROUTINE_DEFINITION
FROM information_schema.ROUTINES
WHERE ROUTINE_TYPE = 'PROCEDURE'
  AND (ROUTINE_DEFINITION LIKE '%CONCAT%'
       OR ROUTINE_DEFINITION LIKE '%PREPARE%');
```

## SQL 키워드 필터링이 안티패턴인 이유

현재 많은 튜토리얼에서 미들웨어로 SQL 키워드를 차단하는 방식을 소개하는데, 프로덕션에서는 쓰면 안 된다.

```javascript
// 이런 코드는 쓰지 않는다
function sqlInjectionProtection(req, res, next) {
  const sqlPatterns = [
    /(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)/gi,
    /(-{2}|\/\*|\*\/|;|'|")/g
  ];
  // ...
}
```

문제점:

- **False positive가 많다.** "I'll **select** the blue one"이라는 상품 리뷰를 쓸 수 없다. "O'Brien"이라는 이름을 입력할 수 없다. "--" 가 포함된 전화번호 형식도 차단된다
- **우회가 쉽다.** 대소문자 혼합(`SeLeCt`), URL 인코딩(`%53ELECT`), 주석 삽입(`SEL/**/ECT`) 등으로 간단히 우회된다
- **근본적 해결이 아니다.** 입력에서 키워드를 걸러내는 것은 문제를 애플리케이션 계층이 아닌 엉뚱한 곳에서 해결하려는 것이다

대신 해야 하는 것:

- 모든 쿼리에서 파라미터 바인딩을 사용한다 — 이것 하나로 SQL 인젝션의 대부분을 막는다
- WAF(Web Application Firewall)를 도입한다면, 직접 만든 정규식이 아니라 검증된 룰셋(ModSecurity CRS 등)을 쓴다. WAF는 방어의 보조 수단이지 주 수단이 아니다
- 입력 검증은 비즈니스 로직 수준에서 한다. 이메일이면 이메일 형식을 검증하고, 숫자면 숫자 타입으로 변환하는 것이 SQL 키워드를 거르는 것보다 정확하다

## 데이터베이스 권한 관리

SQL 인젝션이 발생해도 피해를 최소화하려면 DB 계정 권한을 최소한으로 줄여야 한다.

```sql
-- 애플리케이션용 계정 — 필요한 테이블에 필요한 권한만
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE ON mydb.users TO 'app_user'@'localhost';
GRANT SELECT, INSERT, UPDATE ON mydb.orders TO 'app_user'@'localhost';

-- 리포트/조회용 계정
CREATE USER 'readonly_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT ON mydb.* TO 'readonly_user'@'localhost';

-- DROP, ALTER, FILE, PROCESS 같은 권한은 부여하지 않는다
-- FILE 권한이 있으면 LOAD_FILE()로 서버 파일을 읽을 수 있다
```

## 참고

| 방법 | 인젝션 차단 | 비고 |
|------|-----------|------|
| Prepared Statement | 확실하다 | 모든 쿼리에 기본으로 쓴다 |
| ORM 기본 메서드 | 확실하다 | raw query, literal 사용 시 동일하게 주의 |
| Stored Procedure | 내부 구현에 따라 다르다 | 동적 SQL이 있으면 취약 |
| SQL 키워드 필터링 | 우회 가능하다 | 프로덕션에서 쓰지 않는다 |
| 입력 검증 | 보조 수단이다 | 비즈니스 로직 검증과 병행 |

- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [PortSwigger SQL Injection](https://portswigger.net/web-security/sql-injection)
