---
title: JPA 소프트 삭제 (deleted_at)
tags: [spring, java, database, jpa]
updated: 2026-09-22
---

# JPA 소프트 삭제 (deleted_at)

소프트 삭제는 행을 물리적으로 제거하지 않고 `deleted_at` 컬럼에 삭제 시각을 기록해 논리적으로 삭제 처리하는 방식이다. 감사 로그, 복구 요건, 외래 키 참조 유지가 필요할 때 쓴다.

## 기본 설정: @SQLDelete와 조회 필터

`@SQLDelete`는 JPA가 DELETE SQL을 발행할 때 가로채 다른 SQL로 교체한다. 조회 필터는 Hibernate 버전에 따라 쓰는 애노테이션이 다르다.

```java
@Entity
@Table(name = "users")
@SQLDelete(sql = "UPDATE users SET deleted_at = NOW() WHERE id = ?")
@SQLRestriction("deleted_at IS NULL")   // Hibernate 6.x (Spring Boot 3.x)
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

`repository.delete(user)`를 호출하면 실제로 `UPDATE users SET deleted_at = NOW() WHERE id = ?`가 실행된다. `@SQLRestriction`이 붙어 있기 때문에 `findById`, `findAll` 등 모든 조회에 `deleted_at IS NULL` 조건이 자동으로 붙는다.

## Hibernate 6에서 @Where → @SQLRestriction

Spring Boot 3.x는 Hibernate 6.x를 쓴다. Hibernate 6.3부터 `@Where`가 deprecated 됐고 `@SQLRestriction`으로 대체됐다.

```java
// Hibernate 5.x / Spring Boot 2.x
@Where(clause = "deleted_at IS NULL")

// Hibernate 6.3+ / Spring Boot 3.x
@SQLRestriction("deleted_at IS NULL")
```

동작 차이가 있다. `@Where`는 `clause` 속성에 SQL 조각을 받았고, 연관 엔티티 조회 시 JOIN ON 절에 붙는 방식이 Hibernate 버전마다 다소 달랐다. `@SQLRestriction`은 테이블 별칭을 자동으로 처리해서 JOIN이 있는 쿼리에서 조건이 더 안정적으로 붙는다.

레거시 코드에서 `@Where`를 쓰고 있으면 Spring Boot 3로 올릴 때 컴파일 경고가 나온다. 동작 자체는 유지되지만 `@SQLRestriction`으로 교체하는 게 맞다.

`@SQLRestriction`도 네이티브 쿼리에는 적용되지 않는다. `@Query(nativeQuery = true)`를 쓰면 조건을 직접 추가해야 한다.

## @MappedSuperclass로 소프트 삭제 기반 클래스 만들기

엔티티마다 `deleted_at` 필드를 반복 선언하는 대신, 기반 클래스 하나에 모아두면 관리가 편하다.

```java
@MappedSuperclass
public abstract class SoftDeletableEntity {

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
    }

    public boolean isDeleted() {
        return deletedAt != null;
    }

    public LocalDateTime getDeletedAt() {
        return deletedAt;
    }
}
```

엔티티는 이 클래스를 상속받는다.

```java
@Entity
@Table(name = "users")
@SQLDelete(sql = "UPDATE users SET deleted_at = NOW() WHERE id = ?")
@SQLRestriction("deleted_at IS NULL")
public class User extends SoftDeletableEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String username;
    private String email;
}
```

`@SQLDelete`와 `@SQLRestriction`은 기반 클래스로 올릴 수 없다. 이 애노테이션들은 테이블별로 SQL이 달라지기 때문에 각 엔티티에 붙어야 한다. 기반 클래스에 붙여도 동작하지 않는다.

`softDelete()` 메서드를 직접 호출하면 엔티티 상태만 바뀌고 DB에 반영되지 않는다. `flush()`가 일어나기 전까지는 UPDATE가 나가지 않는다. 실제 삭제 처리는 `repository.delete()`로 하고, `softDelete()`는 영속성 컨텍스트 안에서 상태를 바꿔야 할 때만 쓰는 게 혼선을 줄인다.

`@CreatedDate`, `@LastModifiedDate`와 함께 쓴다면 한 기반 클래스에 모아두는 구조가 흔하다.

```java
@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
public abstract class BaseEntity extends SoftDeletableEntity {

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
```

## Hibernate Filter로 전역 필터 관리

`@SQLRestriction`은 항상 조건을 강제하는 반면, `@Filter`는 세션 단위로 on/off가 가능하다. 삭제된 데이터를 조회해야 하는 관리자 기능이 있다면 `@Filter` 쪽이 낫다.

```java
@Entity
@Table(name = "users")
@SQLDelete(sql = "UPDATE users SET deleted_at = NOW() WHERE id = ?")
@FilterDef(name = "deletedFilter", parameters = @ParamDef(name = "isDeleted", type = Boolean.class))
@Filter(name = "deletedFilter", condition = "deleted_at IS NULL = :isDeleted")
public class User extends SoftDeletableEntity {
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

실무에서는 보통 `@Aspect`나 인터셉터로 요청마다 필터를 자동으로 활성화한다. 트랜잭션 경계와 맞물려 예상치 못한 동작을 일으키는 경우가 있다. 필터 활성화 코드가 트랜잭션 시작 전에 실행되면 세션이 달라져 필터가 적용되지 않는 상황이 생긴다.

## JPQL에서 deleted_at IS NULL 조건 누락 문제

`@SQLRestriction`을 쓰면 대부분의 경우 조건이 자동으로 붙지만, JPQL에서 조인을 직접 쓸 때 누락되는 경우가 있다.

```java
// @SQLRestriction이 있어도 이 경우 조건이 제대로 전파되지 않는 버전의 Hibernate가 있다
@Query("SELECT o FROM Order o JOIN o.user u WHERE o.status = :status")
List<Order> findByStatus(@Param("status") String status);
```

Hibernate 버전에 따라 연관 엔티티에 붙은 `@SQLRestriction` 조건이 JOIN ON 절에 포함되지 않는 케이스가 있었다. Hibernate 6.x로 올라오면서 이 부분이 개선됐지만, 레거시 프로젝트에서는 직접 확인해야 한다.

생성되는 SQL을 `show_sql: true` 옵션으로 반드시 확인하고, 조건이 빠져있으면 JPQL에 명시적으로 추가해야 한다.

```java
@Query("SELECT o FROM Order o JOIN o.user u WHERE o.status = :status AND u.deletedAt IS NULL")
List<Order> findByStatus(@Param("status") String status);
```

## QueryDSL에서 deleted_at IS NULL 처리

QueryDSL을 쓰면 `@SQLRestriction`이 자동으로 적용되지 않는다는 점을 많은 사람이 놓친다. `@SQLRestriction`은 Hibernate 세션 레벨에서 동작하는데, QueryDSL이 생성하는 쿼리는 이 메커니즘을 우회할 수 있다.

```java
// 위험한 코드 - deleted_at IS NULL 조건 없음
List<User> users = queryFactory
    .selectFrom(user)
    .where(user.email.eq(email))
    .fetch();
```

직접 조건을 추가하거나, 공통 BooleanExpression을 만들어서 재사용한다.

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

팀에서 QueryDSL을 쓴다면 베이스 리포지토리에 `notDeleted()` 표현식을 만들어두고 항상 포함시키는 방식이 현실적이다. 개인마다 조건 추가 여부가 달라지면 조용히 데이터가 새는 버그가 생긴다.

## withDeleted 패턴

관리자 기능이나 감사 로그 조회처럼 삭제된 데이터까지 봐야 할 때가 있다.

Spring Data JPA에서는 `EntityManager`로 `@SQLRestriction`을 우회하는 방법이 없다. 해당 엔티티의 모든 쿼리에 강제로 붙기 때문에, 삭제된 데이터를 포함해 조회하려면 네이티브 쿼리나 JDBC를 써야 한다.

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

`@SQLRestriction` 대신 `@Filter`를 선택하는 주된 이유가 바로 이 유연성이다. 단, 필터를 껐다 켰다 하는 코드가 많아지면 관리가 어려워진다.

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

`fetchType = LAZY`로 설정된 `User`를 루프에서 접근하면 N+1이 발생한다. fetch join을 쓰면 문제가 복잡해진다.

```java
// fetch join으로 N+1 해결 시도
@Query("SELECT o FROM Order o JOIN FETCH o.user u WHERE o.createdAt > :date")
List<Order> findRecentOrders(@Param("date") LocalDateTime date);
```

`JOIN FETCH`를 쓸 때 `@SQLRestriction`의 조건이 ON 절에 올바르게 포함되는지 SQL 로그로 확인해야 한다. Hibernate 5.x 일부 버전에서는 `JOIN FETCH`와 `@Where`가 함께 쓰일 때 조건이 WHERE 절이 아닌 ON 절에 붙어야 하는 상황에서 누락되는 버그가 있었다.

배치 페치(batch fetch)와 소프트 삭제 필터가 충돌하는 케이스도 있다.

```java
@Entity
@BatchSize(size = 100)
public class Tag {
    // ...
}
```

`@BatchSize`를 쓰는 엔티티에 `@SQLRestriction`이 붙어 있으면, 배치로 IN 쿼리를 날릴 때 `deleted_at IS NULL` 조건이 제대로 포함되는지 확인해야 한다. 이 경우에는 실제 쿼리 로그를 보는 것 외에 다른 방법이 없다.

## CascadeType.ALL과 @SQLDelete 조합의 함정

`@SQLDelete`와 `CascadeType.ALL`을 같이 쓸 때 자식 엔티티가 soft delete되지 않고 물리적으로 삭제되는 경우가 있다.

```java
@Entity
@SQLDelete(sql = "UPDATE orders SET deleted_at = NOW() WHERE id = ?")
@SQLRestriction("deleted_at IS NULL")
public class Order extends SoftDeletableEntity {

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();
}

@Entity
@SQLDelete(sql = "UPDATE order_items SET deleted_at = NOW() WHERE id = ?")
@SQLRestriction("deleted_at IS NULL")
public class OrderItem extends SoftDeletableEntity {

    @ManyToOne
    @JoinColumn(name = "order_id")
    private Order order;
}
```

`orderRepository.delete(order)`를 호출할 때 어떤 일이 일어나는지가 문제다.

**정상 동작 케이스**: `items` 컬렉션이 영속성 컨텍스트에 로드된 상태라면 Hibernate가 각 `OrderItem`에 대해 개별 `remove()`를 호출하고, `@SQLDelete`가 걸려서 soft delete가 된다.

**버그 케이스**: `items` 컬렉션이 lazy로 설정되어 있고 아직 로드되지 않은 상태에서 부모를 삭제하면, Hibernate가 개별 엔티티 삭제 대신 `DELETE FROM order_items WHERE order_id = ?` 형태의 bulk delete를 발행할 수 있다. 이 bulk delete는 `@SQLDelete`를 타지 않는다. 결과적으로 `Order`는 soft delete가 되고 `OrderItem`은 물리적으로 삭제된다.

```java
// 버그 재현 케이스
Order order = orderRepository.findById(id).orElseThrow();
// order.getItems()를 한 번도 호출하지 않음 → items는 lazy 미로드 상태

orderRepository.delete(order);
// Order: UPDATE orders SET deleted_at = NOW() WHERE id = ? ✓
// OrderItem: DELETE FROM order_items WHERE order_id = ? ✗ (@SQLDelete 무시됨)
```

해결 방법은 세 가지다.

첫 번째: 삭제 전에 컬렉션을 명시적으로 로드한다.

```java
Order order = orderRepository.findById(id).orElseThrow();
order.getItems().size();  // 컬렉션 초기화
orderRepository.delete(order);
```

두 번째: `FetchType.EAGER`로 변경한다. 성능 문제가 따라오므로 컬렉션이 작고 항상 함께 쓰이는 경우에만 적합하다.

세 번째: cascade 삭제를 JPA에 맡기지 않고 직접 처리한다.

```java
@Transactional
public void deleteOrder(Long orderId) {
    orderItemRepository.softDeleteAllByOrderId(orderId);
    orderRepository.deleteById(orderId);
}

// Repository
@Modifying
@Query("UPDATE OrderItem oi SET oi.deletedAt = NOW() WHERE oi.order.id = :orderId AND oi.deletedAt IS NULL")
void softDeleteAllByOrderId(@Param("orderId") Long orderId);
```

세 번째 방식이 가장 명확하다. cascade 동작에 의존하지 않아 Hibernate 버전 차이로 인한 버그를 피할 수 있다.

DB 레벨 FK `ON DELETE CASCADE`와 혼용하면 더 복잡해진다. 부모를 soft delete(UPDATE)하면 DB cascade가 발동하지 않기 때문에 자식은 그대로 남는다. `deleted_at IS NULL` 필터가 붙어 있어서 조회에는 안 나오지만, 데이터는 남아 있는 상태가 된다. 의도한 동작인지 확인해야 한다.

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

## @DataJpaTest에서 소프트 삭제 테스트

`@DataJpaTest`는 H2 인메모리 DB와 Hibernate 설정을 같이 올려주기 때문에 `@SQLDelete`와 `@SQLRestriction` 동작을 테스트하기에 적합하다.

```java
@DataJpaTest
class UserRepositoryTest {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    void softDelete_thenNotFound() {
        User user = userRepository.save(new User("test@example.com", "testuser"));

        userRepository.delete(user);
        entityManager.flush();
        entityManager.clear();

        Optional<User> result = userRepository.findById(user.getId());
        assertThat(result).isEmpty();
    }

    @Test
    void softDelete_setsDeletedAt() {
        User user = userRepository.save(new User("test@example.com", "testuser"));
        Long userId = user.getId();

        userRepository.delete(user);
        entityManager.flush();
        entityManager.clear();

        // 네이티브 쿼리로 @SQLRestriction을 우회해서 실제 deleted_at 확인
        User deletedUser = (User) entityManager.getEntityManager()
            .createNativeQuery("SELECT * FROM users WHERE id = :id", User.class)
            .setParameter("id", userId)
            .getSingleResult();

        assertThat(deletedUser.getDeletedAt()).isNotNull();
    }
}
```

`entityManager.flush()`와 `entityManager.clear()`를 반드시 호출해야 한다. flush 없이 `findById`를 호출하면 1차 캐시에서 삭제된 엔티티를 그대로 반환하는 경우가 있다. clear 없이는 다음 조회가 DB를 안 보고 캐시에서 응답한다. 이 두 줄이 없으면 테스트가 `@SQLRestriction` 동작을 검증하는 게 아니라 1차 캐시 동작을 검증하는 꼴이 된다.

`@Filter`를 사용하는 구조라면 테스트에서도 필터를 직접 활성화해야 한다.

```java
@DataJpaTest
class UserRepositoryFilterTest {

    @Autowired
    private EntityManager em;

    @BeforeEach
    void enableFilter() {
        em.unwrap(Session.class)
          .enableFilter("deletedFilter")
          .setParameter("isDeleted", true);
    }

    @Test
    void filterEnabled_excludesSoftDeleted() {
        // 필터가 활성화된 상태에서 조회 테스트
    }
}
```

`@DataJpaTest`는 기본적으로 H2를 쓴다. `@SQLDelete`에서 MySQL 전용 함수(`UNIX_TIMESTAMP()`)를 쓰면 H2에서 실패한다. H2는 `NOW()`를 지원하지만 `UNIX_TIMESTAMP()`는 지원하지 않는다. 실제 DB와 동일한 환경에서 테스트하려면 Testcontainers를 써야 한다.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class UserRepositoryMySQLTest {

    @Container
    static MySQLContainer<?> mysql = new MySQLContainer<>("mysql:8.0");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", mysql::getJdbcUrl);
        registry.add("spring.datasource.username", mysql::getUsername);
        registry.add("spring.datasource.password", mysql::getPassword);
    }
}
```

## 실무 체크

`@SQLRestriction`과 `@Filter` 중에 선택하는 기준은 단순하다. 삭제된 데이터를 절대 조회할 일이 없으면 `@SQLRestriction`, 조회해야 하는 경우가 생기면 `@Filter`를 쓴다. 한 번 `@SQLRestriction`으로 설계하고 나중에 요건이 바뀌면 전체 구조를 바꿔야 하는 상황이 생기므로, 처음부터 요건을 확인하는 게 낫다.

QueryDSL을 도입한 팀이라면 `notDeleted()` 표현식을 공통 베이스 클래스에 두고 팀 전체에서 일관되게 쓰도록 강제해야 한다. 개인마다 조건 추가 여부가 달라지면 조용히 데이터가 새는 버그가 생긴다.

`CascadeType.ALL`과 `@SQLDelete`를 같이 쓸 때는 자식 엔티티의 소프트 삭제 동작을 SQL 로그로 반드시 확인해야 한다. 컬렉션이 lazy 로드 상태라면 bulk DELETE가 나갈 수 있다.

`deleted_at` 컬럼에는 반드시 인덱스를 걸어야 한다. `WHERE deleted_at IS NULL` 조건이 항상 붙는데 인덱스가 없으면 풀 스캔이 발생한다. 데이터가 적을 때는 모르지만 수십만 건이 넘어가면 바로 느려진다.
