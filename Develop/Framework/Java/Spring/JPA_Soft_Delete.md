---
title: JPA 소프트 삭제 (deleted_at)
tags: [spring, java]
updated: 2026-08-03
---

# JPA 소프트 삭제 (deleted_at)

소프트 삭제는 행을 물리적으로 제거하지 않고 `deleted_at` 컬럼에 삭제 시각을 기록해 논리적으로 삭제 처리하는 방식이다. 감사 로그, 복구 요건, 외래 키 참조 유지가 필요할 때 많이 쓴다.

## 기본 설정: @SQLDelete와 @Where

`@SQLDelete`는 JPA가 DELETE SQL을 발행할 때 이를 가로채 다른 SQL로 교체한다. `@Where`는 해당 엔티티를 조회하는 모든 쿼리에 조건절을 추가한다.

```java
@Entity
@Table(name = "users")
@SQLDelete(sql = "UPDATE users SET deleted_at = NOW() WHERE id = ?")
@Where(clause = "deleted_at IS NULL")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String username;
    private String email;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;
}
```

`repository.delete(user)`를 호출하면 실제로 `UPDATE users SET deleted_at = NOW() WHERE id = ?`가 실행된다. `@Where`가 붙어 있기 때문에 `findById`, `findAll` 등 모든 조회에서 `deleted_at IS NULL` 조건이 자동으로 붙는다.

주의할 점이 있다. `@Where`는 Hibernate의 기능이며 JPQL 쿼리에도 적용되지만, 네이티브 쿼리에는 적용되지 않는다. `@Query(nativeQuery = true)`를 쓰면 조건을 직접 추가해야 한다.

## Hibernate Filter로 전역 필터 관리

`@Where`는 항상 조건을 강제하는 반면, `@Filter`는 세션 단위로 on/off가 가능하다. 삭제된 데이터를 조회해야 하는 관리자 기능이 있다면 `@Filter` 쪽이 더 낫다.

```java
@Entity
@Table(name = "users")
@SQLDelete(sql = "UPDATE users SET deleted_at = NOW() WHERE id = ?")
@FilterDef(name = "deletedFilter", parameters = @ParamDef(name = "isDeleted", type = Boolean.class))
@Filter(name = "deletedFilter", condition = "deleted_at IS NULL = :isDeleted")
public class User {
    // ...
}
```

필터를 활성화하려면 `EntityManager`에서 직접 켜야 한다.

```java
@Component
public class SoftDeleteFilter {

    @PersistenceContext
    private EntityManager em;

    public void enableSoftDeleteFilter() {
        Session session = em.unwrap(Session.class);
        session.enableFilter("deletedFilter")
               .setParameter("isDeleted", true);
    }
}
```

실무에서는 보통 `@Aspect`나 인터셉터를 써서 요청마다 자동으로 필터를 활성화한다. 그러나 이 방식은 트랜잭션 경계와 맞물려 예상치 못한 동작을 일으키는 경우가 있다. 필터 활성화 코드가 트랜잭션 시작 전에 실행되면 세션이 달라져 필터가 적용되지 않는 상황이 발생할 수 있다.

## JPQL에서 deleted_at IS NULL 조건 누락 문제

`@Where`를 쓰면 대부분의 경우 조건이 자동으로 붙지만, JPQL에서 조인을 직접 쓸 때 누락되는 경우가 있다.

```java
// @Where가 있어도 이 경우 조건이 제대로 전파되지 않는 버전의 Hibernate가 있다
@Query("SELECT o FROM Order o JOIN o.user u WHERE o.status = :status")
List<Order> findByStatus(@Param("status") String status);
```

Hibernate 버전에 따라 연관 엔티티에 붙은 `@Where` 조건이 JOIN ON 절에 포함되지 않는 케이스가 있었다. Hibernate 6.x로 올라오면서 이 부분이 개선됐지만, 레거시 프로젝트에서는 직접 확인해야 한다.

생성되는 SQL을 `show_sql: true` 옵션으로 반드시 확인하고, 조건이 빠져있으면 JPQL에 명시적으로 추가해야 한다.

```java
@Query("SELECT o FROM Order o JOIN o.user u WHERE o.status = :status AND u.deletedAt IS NULL")
List<Order> findByStatus(@Param("status") String status);
```

## QueryDSL에서 deleted_at IS NULL 처리

QueryDSL을 쓰면 `@Where`가 자동으로 적용되지 않는다는 점을 많은 사람이 놓친다. `@Where`는 Hibernate 세션 레벨에서 동작하는데, QueryDSL이 생성하는 쿼리는 이 메커니즘을 우회할 수 있다.

```java
// 위험한 코드 - deleted_at IS NULL 조건 없음
List<User> users = queryFactory
    .selectFrom(user)
    .where(user.email.eq(email))
    .fetch();
```

직접 조건을 추가하거나, 공통 BooleanExpression을 만들어서 재사용하는 방식으로 해결한다.

```java
public class UserQueryRepository {

    private final JPAQueryFactory queryFactory;

    private BooleanExpression notDeleted() {
        return user.deletedAt.isNull();
    }

    public List<User> findActiveByEmail(String email) {
        return queryFactory
            .selectFrom(user)
            .where(notDeleted(), user.email.eq(email))
            .fetch();
    }
}
```

팀에서 QueryDSL을 쓴다면 베이스 리포지토리에 `notDeleted()` 표현식을 만들어두고 항상 포함시키는 방식이 현실적이다.

## withDeleted 패턴

관리자 기능이나 감사 로그 조회처럼 삭제된 데이터까지 봐야 할 때가 있다. 이때 쓰는 패턴이 `withDeleted`다.

Spring Data JPA에서는 `EntityManager`로 `@Where`를 우회하는 방법이 없다. `@Where`는 해당 엔티티의 모든 쿼리에 강제로 붙기 때문에, 삭제된 데이터를 포함해 조회하려면 네이티브 쿼리나 JDBC를 써야 한다.

```java
public interface UserRepository extends JpaRepository<User, Long> {

    // 삭제된 사용자 포함 조회는 네이티브 쿼리로
    @Query(value = "SELECT * FROM users WHERE id = :id", nativeQuery = true)
    Optional<User> findByIdIncludingDeleted(@Param("id") Long id);

    @Query(value = "SELECT * FROM users WHERE email = :email", nativeQuery = true)
    Optional<User> findByEmailIncludingDeleted(@Param("email") String email);
}
```

`@Filter`를 쓰는 구조라면 필터를 비활성화해서 처리할 수 있다.

```java
@Transactional(readOnly = true)
public User findUserIncludingDeleted(Long id) {
    Session session = em.unwrap(Session.class);
    session.disableFilter("deletedFilter");
    return userRepository.findById(id)
        .orElseThrow(() -> new EntityNotFoundException("User not found"));
}
```

`@Where` 대신 `@Filter`를 선택하는 주된 이유가 바로 이 유연성이다. 단, 필터를 껐다 켰다 하는 코드가 많아지면 관리가 어려워진다.

## N+1과 소프트 삭제 필터 충돌

소프트 삭제와 N+1 문제가 얽히면 디버깅이 복잡해진다.

```java
@Entity
public class Order {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;
}
```

`fetchType = LAZY`로 설정된 `User`를 루프에서 접근하면 N+1이 발생한다. 이때 fetch join을 쓰면 문제가 복잡해진다.

```java
// fetch join으로 N+1 해결 시도
@Query("SELECT o FROM Order o JOIN FETCH o.user u WHERE o.createdAt > :date")
List<Order> findRecentOrders(@Param("date") LocalDateTime date);
```

`JOIN FETCH`를 쓸 때 `@Where`의 조건이 ON 절에 올바르게 포함되는지 SQL 로그로 확인해야 한다. Hibernate 5.x 일부 버전에서는 `JOIN FETCH`와 `@Where`가 함께 쓰일 때 조건이 WHERE 절이 아닌 ON 절에 붙어야 하는 상황에서 누락되는 버그가 있었다.

배치 페치(batch fetch)와 소프트 삭제 필터가 충돌하는 케이스도 있다.

```java
@Entity
@BatchSize(size = 100)
public class Tag {
    // ...
}
```

`@BatchSize`를 쓰는 엔티티에 `@Where`가 붙어 있으면, 배치로 IN 쿼리를 날릴 때 `deleted_at IS NULL` 조건이 제대로 포함되는지 확인해야 한다. 이 경우에는 특히 실제 쿼리 로그를 보는 것 외에 다른 방법이 없다.

## 복합 유니크 제약과 소프트 삭제

소프트 삭제를 쓸 때 유니크 제약이 문제가 되는 경우가 많다. 이메일 컬럼에 유니크 인덱스가 걸려 있으면, 같은 이메일로 가입 → 소프트 삭제 → 재가입 시 중복 오류가 발생한다.

해결 방법은 두 가지다.

첫 번째는 유니크 인덱스를 `deleted_at IS NULL`을 포함한 부분 인덱스(partial index)로 변경하는 것이다.

```sql
-- MySQL 8.0+에서는 함수 기반 인덱스로 처리
CREATE UNIQUE INDEX uk_users_email_active
ON users (email, (CASE WHEN deleted_at IS NULL THEN 1 ELSE NULL END));

-- PostgreSQL
CREATE UNIQUE INDEX uk_users_email_active
ON users (email) WHERE deleted_at IS NULL;
```

두 번째는 소프트 삭제 시 이메일 값을 변조하는 방법이다. 실무에서는 이 방식을 종종 쓴다.

```java
@SQLDelete(sql = """
    UPDATE users
    SET deleted_at = NOW(),
        email = CONCAT(email, '_deleted_', UNIX_TIMESTAMP())
    WHERE id = ?
""")
```

이 방식은 데이터를 오염시킨다는 단점이 있지만, 인덱스 변경 없이 재가입 처리가 가능하다.

## 실무 체크

`@Where`와 `@Filter` 중에 선택하는 기준은 단순하다. 삭제된 데이터를 절대 조회할 일이 없으면 `@Where`, 조회해야 하는 경우가 생기면 `@Filter`를 쓴다. 한 번 `@Where`로 설계하고 나중에 요건이 바뀌면 전체 구조를 바꿔야 하는 상황이 생기므로, 처음부터 요건을 확인하는 게 낫다.

QueryDSL을 도입한 팀이라면 `notDeleted()` 표현식을 공통 베이스 클래스에 두고 팀 전체에서 일관되게 쓰도록 강제해야 한다. 개인마다 조건 추가 여부가 달라지면 조용히 데이터가 새는 버그가 생긴다.

`deleted_at` 컬럼에는 반드시 인덱스를 걸어야 한다. `WHERE deleted_at IS NULL` 조건이 항상 붙는데 인덱스가 없으면 풀 스캔이 발생한다. 데이터가 적을 때는 모르지만 수십만 건이 넘어가면 바로 느려진다.
