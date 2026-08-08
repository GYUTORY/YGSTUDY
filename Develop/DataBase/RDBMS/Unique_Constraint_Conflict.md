---
title: 유니크 제약 충돌
tags: [rdbms, mysql, postgresql, java]
updated: 2026-08-03
---

# 유니크 제약 충돌

유니크 제약을 걸면 반드시 충돌 상황이 발생한다. 비즈니스 로직으로 중복을 막는 코드를 아무리 잘 짜도, 동시 요청이나 재처리 케이스에서 DB 레벨까지 뚫린다. 에러가 터졌을 때 어떤 DB인지, 어느 컬럼인지 파악하고 핸들링하는 흐름이 핵심이다.

## DB별 에러 코드

### MySQL — Error 1062

```
Error Code: 1062
SQLSTATE: 23000
Message: Duplicate entry 'value' for key 'table_name.index_name'
```

MySQL은 에러 메시지에 중복된 값과 인덱스명이 직접 찍힌다. `users` 테이블의 `email` 유니크 인덱스를 `uk_users_email`로 명명했다면 이렇게 나온다:

```
Duplicate entry 'foo@example.com' for key 'users.uk_users_email'
```

JDBC 드라이버를 통해 올라오는 `SQLIntegrityConstraintViolationException`의 `getErrorCode()`가 1062이면 유니크 위반이다.

### PostgreSQL — SQLSTATE 23505

```
ERROR: duplicate key value violates unique constraint "users_email_key"
DETAIL: Key (email)=(foo@example.com) already exists.
```

PostgreSQL은 SQLSTATE `23505`를 유니크 위반 전용으로 쓴다. `23503`은 FK 위반, `23502`는 NOT NULL 위반, `23000`은 상위 범주다. DETAIL 절에 어느 컬럼에서 어떤 값이 충돌했는지 나온다.

## ORM·프레임워크별 예외 판별

### JPA (Spring) — DataIntegrityViolationException

Spring Data JPA에서 유니크 위반이 발생하면 `DataIntegrityViolationException`이 올라온다. 이 예외가 유니크 위반만 담당하지 않는다는 게 문제다. FK 위반, NOT NULL 위반, 체크 제약 위반도 같은 예외 타입으로 올라오기 때문에, 원인을 구분하려면 원인 예외를 파고 들어야 한다.

```java
try {
    userRepository.save(user);
} catch (DataIntegrityViolationException e) {
    Throwable cause = e.getCause();
    if (cause instanceof ConstraintViolationException cve) {
        String constraintName = cve.getConstraintName();
        // MySQL: "uk_users_email", PostgreSQL: "users_email_key"
        if (constraintName != null && constraintName.contains("uk_users_email")) {
            throw new DuplicateEmailException();
        }
    }
    throw e;
}
```

`ConstraintViolationException`은 Hibernate 예외다. `getConstraintName()`으로 제약 이름을 꺼낼 수 있다. DB마다 제약 이름 형식이 달라서 `contains`로 부분 일치를 쓰는 경우가 많은데, 제약 이름을 명시적으로 지정해두면 정확하게 매칭할 수 있다.

```java
@Table(
    uniqueConstraints = @UniqueConstraint(
        name = "uk_users_email",
        columnNames = "email"
    )
)
public class User { ... }
```

### TypeORM — QueryFailedError

TypeORM은 DB 에러를 `QueryFailedError`로 감싼다. `UniqueConstraintError` 같은 별도 클래스가 없다.

```typescript
import { QueryFailedError } from 'typeorm';

try {
    await userRepository.save(user);
} catch (e) {
    if (e instanceof QueryFailedError) {
        const driverError = (e as any).driverError;

        // MySQL: driverError.code === 'ER_DUP_ENTRY'
        // driverError.sqlMessage에 충돌값과 인덱스명이 들어옴
        if (driverError.code === 'ER_DUP_ENTRY') {
            throw new DuplicateEmailException();
        }

        // PostgreSQL: driverError.code === '23505'
        // driverError.constraint에 제약 이름, driverError.detail에 충돌 상세가 들어옴
        if (driverError.code === '23505') {
            if (driverError.constraint === 'users_email_key') {
                throw new DuplicateEmailException();
            }
        }
    }
    throw e;
}
```

### Prisma — P2002

Prisma는 자체 에러 코드 체계를 쓴다. 유니크 위반은 `P2002`다.

```typescript
import { PrismaClientKnownRequestError } from '@prisma/client/runtime/library';

try {
    await prisma.user.create({ data: { email: 'foo@example.com' } });
} catch (e) {
    if (e instanceof PrismaClientKnownRequestError && e.code === 'P2002') {
        // e.meta.target: ['email'] — 충돌한 필드 배열
        const fields = e.meta?.target as string[];
        if (fields?.includes('email')) {
            throw new DuplicateEmailException();
        }
    }
    throw e;
}
```

Prisma의 `P2002`는 `meta.target`에 충돌한 필드명 배열이 들어온다. ORM 중에서 어느 컬럼에서 충돌했는지 가장 명확하게 알려주는 편이다.

## UPSERT 패턴

유니크 충돌을 예외로 처리하는 대신, DB 레벨에서 충돌 시 동작을 지정하는 UPSERT를 쓰는 상황이 있다. 충돌이 발생해도 에러로 처리하지 않고 특정 컬럼을 갱신하거나 무시하고 싶을 때다.

### MySQL — INSERT ... ON DUPLICATE KEY UPDATE

```sql
INSERT INTO user_settings (user_id, theme, updated_at)
VALUES (1, 'dark', NOW())
ON DUPLICATE KEY UPDATE
    theme = VALUES(theme),
    updated_at = VALUES(updated_at);
```

`VALUES(column)` 함수는 INSERT 시 지정한 값을 참조한다. MySQL 8.0.20+에서는 `VALUES()` 대신 별칭을 쓰는 방식이 권장된다:

```sql
INSERT INTO user_settings (user_id, theme, updated_at)
VALUES (1, 'dark', NOW()) AS new_row
ON DUPLICATE KEY UPDATE
    theme = new_row.theme,
    updated_at = new_row.updated_at;
```

주의할 점이 있다. `ON DUPLICATE KEY UPDATE`는 유니크 인덱스가 여러 개인 테이블에서 예상치 못한 행이 업데이트될 수 있다. 충돌한 인덱스가 어느 것인지 MySQL이 보장하지 않기 때문이다. 가능하면 단일 유니크 인덱스 테이블에 쓰는 게 안전하다.

### PostgreSQL — INSERT ... ON CONFLICT DO UPDATE

```sql
INSERT INTO user_settings (user_id, theme, updated_at)
VALUES (1, 'dark', NOW())
ON CONFLICT (user_id)
DO UPDATE SET
    theme = EXCLUDED.theme,
    updated_at = EXCLUDED.updated_at;
```

PostgreSQL은 어느 컬럼(또는 제약 이름)에서 충돌했을 때 동작할지 명시한다. `EXCLUDED`는 INSERT 시 시도한 행을 참조한다.

제약 이름으로 지정할 수도 있다:

```sql
ON CONFLICT ON CONSTRAINT uk_user_settings_user_id
DO UPDATE SET ...
```

충돌이 발생했을 때 아무것도 하지 않으려면 `DO NOTHING`을 쓴다:

```sql
INSERT INTO idempotency_keys (key, created_at)
VALUES ('req-abc123', NOW())
ON CONFLICT (key) DO NOTHING;
```

중복 요청 방어용 멱등성 키 테이블에 자주 쓰는 패턴이다.

## 동시 INSERT와 TOCTOU 경쟁 조건

코드 레벨에서 중복 체크 후 INSERT를 하는 패턴은 동시 요청에서 깨진다.

```python
# 두 요청이 동시에 들어오면 둘 다 exists=False를 받고 INSERT 시도
# 둘 중 하나는 1062/23505 에러를 받음
if not User.objects.filter(email=email).exists():
    User.objects.create(email=email)
```

SELECT와 INSERT 사이의 시간 간격 동안 다른 요청이 끼어드는 TOCTOU(Time-Of-Check-Time-Of-Use) 문제다. 단일 서버라도 비동기 처리나 스레드 환경에서 발생하고, 다중 서버 환경에서는 피할 방법이 없다.

가장 단순한 해법은 SELECT 없이 바로 INSERT하고 예외를 잡는 것이다. DB가 충돌을 보장하고, 애플리케이션은 예외를 받아 처리한다. 충돌이 드물게 발생하는 상황이라면 이 방식이 조회 비용도 없고 코드도 단순하다.

충돌 시 특정 동작(업데이트 또는 무시)이 필요하다면 위에서 설명한 UPSERT가 적합하다. `ON DUPLICATE KEY UPDATE` / `ON CONFLICT DO UPDATE`는 충돌 감지와 후속 처리가 원자적으로 실행된다.

`SELECT ... FOR UPDATE`로 잠근 뒤 INSERT하는 방법도 있지만 성능 비용이 있고, 단순 유니크 충돌에는 오버스펙이 되는 경우가 대부분이다.

애플리케이션 레벨에서 중복을 완벽하게 막으려는 시도는 결국 DB 유니크 제약과의 이중화가 된다. DB 제약을 믿고 예외 처리를 명확히 하는 쪽이 낫다.

## 복합 유니크 제약에서 충돌 컬럼 특정

`(user_id, content_id)` 같은 복합 유니크 제약은 예외 메시지에서 어느 조합이 충돌했는지는 알 수 있지만, 컬럼 개별로 어느 값이 문제인지를 구분하는 방법은 없다. 복합 제약은 조합 단위로 유일성을 보장하기 때문에 설계상 당연한 제한이다.

어느 제약에서 충돌했는지는 제약 이름으로 판별한다. 이 때문에 복합 유니크 제약에는 명시적 이름을 붙여두는 게 낫다.

```sql
ALTER TABLE user_content_likes
ADD CONSTRAINT uk_ucl_user_content UNIQUE (user_id, content_id);
```

```java
// Hibernate: getConstraintName() = "uk_ucl_user_content"
if ("uk_ucl_user_content".equals(constraintName)) {
    throw new AlreadyLikedException();
}
```

PostgreSQL `23505` 에러에서는 `pg_constraint` 시스템 카탈로그로 제약에 속한 컬럼 목록을 조회할 수 있다. 다만 애플리케이션 코드에서 실시간으로 이 조회를 할 이유는 없다. 배포 전에 제약 이름을 확인하고 코드에 명시해두는 게 현실적이다.

Prisma는 `meta.target` 배열이 복합 제약에서도 정상 동작한다:

```typescript
// P2002: e.meta.target = ['user_id', 'content_id']
const fields = e.meta?.target as string[];
// 복합 유니크 제약임을 알 수 있고, 어느 필드 조합인지도 파악 가능
```

## 소프트 삭제와의 충돌

소프트 삭제(`deleted_at IS NULL`) 상태의 행과 유니크 제약이 겹치면 별도 처리가 필요하다. 삭제된 행이 실제로는 유니크 인덱스에 잔류하기 때문에, 같은 값으로 재삽입할 때 충돌이 발생한다. 이 내용은 [소프트 삭제](./Soft_Delete.md)에서 다룬다.
