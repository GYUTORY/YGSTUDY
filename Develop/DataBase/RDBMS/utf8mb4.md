---
title: MySQL utf8mb4
tags: [mysql, database, devops, rdbms]
updated: 2026-08-05
---

# MySQL utf8mb4

## MySQL의 utf8은 진짜 UTF-8이 아니다

MySQL에서 `utf8`이라고 설정하면 유니코드를 처리할 수 있다고 생각하기 쉽다. 실제로는 최대 3바이트만 지원한다. UTF-8 표준은 4바이트까지 쓰는데, MySQL은 초기 버전부터 3바이트짜리 구현을 `utf8`이라는 이름으로 제공해왔다.

이 문제가 드러나는 건 이모지나 일부 한자를 저장할 때다. 유니코드 코드포인트가 U+10000 이상인 문자는 4바이트가 필요한데, MySQL `utf8`은 이걸 받아들이지 못하고 오류를 낸다.

```sql
-- utf8로 설정된 테이블에 이모지 저장 시도
INSERT INTO messages (body) VALUES ('안녕하세요 😊');
-- ERROR 1366: Incorrect string value: '\xF0\x9F\x98\x8A' for column 'body'
```

`\xF0\x9F\x98\x8A`가 바로 4바이트짜리 이모지(U+1F60A)다. 3바이트까지만 받는 컬럼은 이 값을 거부한다.

`utf8mb4`는 MySQL이 만든 해결책이다. `mb4`는 "multibyte 4"를 의미하고, 1~4바이트를 모두 처리한다. 표준 UTF-8과 동일하게 동작한다.

## 실제 사고 패턴

이모지 저장 실패가 가장 흔하다. 채팅, 댓글, 사용자 프로필 같은 기능에서 `utf8` 컬럼을 쓰면 특정 문자만 골라서 저장이 안 된다.

더 조용한 실패 케이스도 있다. MySQL `strict` 모드가 꺼져 있으면 저장에 실패하는 대신 4바이트 이후 데이터를 잘라버린다. 이모지가 들어간 메시지가 이모지 직전까지만 잘려서 저장되는 상황이다. 운영 중에 발견하면 원인을 찾기 어렵다.

```sql
-- strict 모드 OFF 상태에서 잘림 발생
-- '안녕 😊 반가워' 대신 '안녕 '만 저장됨
-- Warning: 1366 Incorrect string value
```

애플리케이션 로그에서 이런 Warning이 대량으로 나오기 시작하면 charset 문제를 의심한다.

## utf8 → utf8mb4 마이그레이션

### 서버 설정 변경

`my.cnf`에서 기본값을 바꾼다.

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4

[mysql]
default-character-set = utf8mb4
```

서버 재시작 후 적용됐는지 확인한다.

```sql
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';
```

서버 설정만 바꾸면 새로 만드는 데이터베이스는 utf8mb4가 기본이 된다. 기존 데이터베이스와 테이블은 여전히 utf8이다.

### 데이터베이스 변경

```sql
ALTER DATABASE mydb
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
```

데이터베이스 기본값만 바꾸는 거라 기존 테이블에는 영향이 없다. 이후 새로 만드는 테이블이 utf8mb4를 기본으로 쓴다.

### 테이블과 컬럼 변경

```sql
-- 테이블 기본 charset 변경 + 기존 컬럼 데이터도 컨버팅
ALTER TABLE users
  CONVERT TO CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

`CONVERT TO`를 쓰면 테이블 기본값 변경과 동시에 모든 문자열 컬럼의 데이터를 변환한다. 데이터가 많으면 시간이 걸리고 테이블 락이 발생할 수 있다. 운영 중인 테이블에 바로 실행하면 서비스에 영향이 간다.

`CHANGE CHARACTER SET`과 `CONVERT TO CHARACTER SET`은 다르다. `CHANGE CHARACTER SET`는 기본값만 바꾸고 기존 데이터를 변환하지 않는다.

특정 컬럼만 바꿔야 하는 경우다.

```sql
ALTER TABLE users
  MODIFY COLUMN name VARCHAR(100)
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci NOT NULL;
```

대용량 테이블 마이그레이션은 pt-online-schema-change나 gh-ost를 쓰는 게 현실적이다. 직접 ALTER를 걸면 테이블 락으로 쿼리가 다 밀린다.

## JDBC URL 설정

JDBC 연결 문자열에 charset을 명시해야 한다.

```
jdbc:mysql://localhost:3306/mydb?characterEncoding=UTF-8&useUnicode=true
```

`characterEncoding=UTF-8`을 쓰면 JDBC 드라이버가 서버에 `utf8mb4`로 연결한다. `characterEncoding=utf8mb4`라고 직접 쓰는 건 구버전 드라이버에서 인식 못 하는 경우가 있어서 `UTF-8`로 쓰는 게 호환성이 좋다.

MySQL Connector/J 8.x부터는 기본 charset이 UTF-8이라 명시하지 않아도 되지만, 명시하는 게 의도를 명확히 한다.

## Spring Boot DataSource 설정

### application.yml

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb?characterEncoding=UTF-8&useUnicode=true&serverTimezone=Asia/Seoul
    username: root
    password: secret
    driver-class-name: com.mysql.cj.jdbc.Driver
```

### HikariCP를 쓰는 경우 connectionInitSql 추가

드라이버 설정이 제대로 적용됐는지 불안하면 커넥션 생성 시 명시적으로 charset을 설정한다.

```yaml
spring:
  datasource:
    hikari:
      connection-init-sql: "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
```

`SET NAMES`는 클라이언트 연결의 `character_set_client`, `character_set_connection`, `character_set_results`를 한 번에 설정한다. 연결을 맺을 때마다 실행되기 때문에 커넥션 풀에서 재사용하는 커넥션도 올바른 charset으로 동작한다.

### 연결 charset 확인

```sql
SHOW SESSION VARIABLES LIKE 'character_set%';
```

`character_set_client`, `character_set_connection`, `character_set_results`가 모두 `utf8mb4`면 정상이다.

## 인덱스 key length 767바이트 제한

utf8에서 utf8mb4로 바꾸면 인덱스 생성에 실패하는 케이스가 생긴다.

utf8은 문자당 최대 3바이트다. utf8mb4는 최대 4바이트다. `VARCHAR(255)` 컬럼에 인덱스를 걸면 `255 × 4 = 1020바이트`가 필요한데, InnoDB의 기본 인덱스 key 최대 길이는 767바이트다.

```sql
-- utf8mb4에서 이 인덱스는 실패한다
ALTER TABLE users ADD INDEX idx_email (email(255));
-- ERROR 1071: Specified key was too long; max key length is 767 bytes
```

### innodb_large_prefix로 해결

MySQL 5.7 이상에서는 `innodb_large_prefix`를 활성화하면 3072바이트까지 허용한다. `ROW_FORMAT`도 함께 설정해야 한다.

```ini
[mysqld]
innodb_large_prefix = ON
innodb_file_format = Barracuda
innodb_file_per_table = ON
```

테이블 생성 시 ROW_FORMAT을 명시한다.

```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(191) NOT NULL,
  ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;

ALTER TABLE users ADD UNIQUE INDEX idx_email (email);
```

`ROW_FORMAT=DYNAMIC` 또는 `COMPRESSED`일 때만 innodb_large_prefix가 적용된다.

### MySQL 8.0에서는 기본 해결

MySQL 8.0부터 `innodb_large_prefix`가 기본 활성화 상태고, `ROW_FORMAT=DYNAMIC`이 기본값이다. 8.0을 쓰면 이 제한을 신경 쓸 필요가 없다.

### VARCHAR(191) 관행

5.7 이하에서 utf8mb4를 쓰면서 인덱스도 걸어야 하는 경우, `VARCHAR(191)`이 관행적으로 쓰인다. `191 × 4 = 764`로 767바이트 제한 안에 들어온다.

이 숫자가 갑자기 나오면 charset 제한을 맞추기 위한 값이라는 걸 알아야 한다. Django 같은 프레임워크도 MySQL에서 utf8mb4를 쓸 때 email 필드를 자동으로 191로 잡는다.

## collation 선택

utf8mb4로 바꿀 때 collation도 같이 정해야 한다.

`utf8mb4_general_ci`는 빠르지만 언어별 정렬 규칙을 무시한다. `utf8mb4_unicode_ci`는 유니코드 표준에 따른 정렬이다. `utf8mb4_unicode_520_ci`는 유니코드 5.2.0 기준이고, `utf8mb4_0900_ai_ci`는 MySQL 8.0에서 추가된 유니코드 9.0 기준이다.

실무에서는 `utf8mb4_unicode_ci`가 무난하다. 한글 처리에 문제가 없고 MySQL 5.7, 8.0 모두 동일하게 동작한다. 8.0만 쓴다면 `utf8mb4_0900_ai_ci`가 성능이 더 낫다.

`_ci`는 case-insensitive(대소문자 구분 안 함)다. 이메일, 아이디 같은 컬럼은 대소문자를 구분하지 않는 게 보통이라 `_ci`가 맞다. 대소문자를 구분해야 하면 `_cs`를 쓴다.

collation이 다른 컬럼끼리 비교하거나 조인하면 `Illegal mix of collations` 오류가 난다.

```sql
-- 오류 예시
SELECT * FROM a JOIN b ON a.name = b.name;
-- ERROR 1267: Illegal mix of collations (utf8mb4_unicode_ci,IMPLICIT)
--   and (utf8_general_ci,IMPLICIT) for operation '='
```

마이그레이션할 때 모든 테이블의 collation을 통일하지 않으면 나중에 이 오류를 마주한다.

## MariaDB 호환성 주의사항

MariaDB는 MySQL의 포크지만 charset 동작이 다른 부분이 있다.

MariaDB 10.3 이하에서는 `utf8mb4_unicode_ci`와 `utf8_unicode_ci`가 alias 관계여서 테이블 생성 시 자동으로 `utf8_unicode_ci`로 바뀌는 경우가 있다. 테이블 생성 후 `SHOW CREATE TABLE`로 확인하는 습관이 필요하다.

MariaDB 10.4부터는 서버 기본 charset이 `utf8mb4`로 바뀌었다. `utf8`이라고 설정해도 실제로는 `utf8mb4`로 동작한다. MySQL과 반대 방향이다.

MySQL과 MariaDB를 섞어 쓰는 환경에서는 `SHOW CREATE TABLE` 결과를 양쪽에서 비교해두는 게 안전하다. 특히 Galera Cluster나 replication으로 MySQL과 MariaDB를 연결하는 경우 charset 불일치로 복제가 깨질 수 있다.

MariaDB는 `utf8mb4_0900_ai_ci` 를 **어느 버전에서도 지원하지 않는다**. `0900` 계열은 MySQL 8.0 의 UCA 9.0.0 collation 이고, MariaDB 가 따로 도입한 건 UCA 14.0.0 계열(`utf8mb4_uca1400_*`, 10.10+)이라 계보가 다르다. 10.6 이든 11.4 든 `ERROR 1273 unknown collation` 이 난다. MySQL 8.0 덤프를 MariaDB에 복원하면 이 collation 때문에 실패한다. 덤프할 때 `--skip-set-charset` 또는 sed로 collation을 바꿔서 임포트해야 한다.

```bash
# MySQL 8.0 덤프를 MariaDB로 임포트할 때
mysqldump --single-transaction mydb | \
  sed 's/utf8mb4_0900_ai_ci/utf8mb4_unicode_ci/g' | \
  mysql -h mariadb_host mydb
```
