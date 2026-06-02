---
title: Spring Data JPA 핵심 개념과 실전 적용
tags: [framework, java, spring, jpa, hibernate, orm, database, query]
updated: 2026-05-14
---

# Spring Data JPA 핵심 개념과 실전 적용

## 배경

Spring Data JPA는 JPA(Java Persistence API) 스펙을 Spring 방식으로 감싼 모듈이다. Repository 인터페이스만 정의해두면 CRUD와 페이징 쿼리를 런타임에 만들어주고, 직접 SQL을 써야 할 때는 JPQL이나 네이티브 쿼리, QueryDSL을 함께 쓸 수 있다.

내부에서는 보통 Hibernate가 구현체로 동작한다. 즉 Spring Data JPA → JPA 스펙 → Hibernate → JDBC → DB 순으로 호출이 내려간다. 코드 한 줄이 SQL 한 번이 아니라 영속성 컨텍스트의 상태 변화와 트랜잭션 커밋 시점에 따라 여러 번 또는 0번 나가는 일이 흔하다는 점을 항상 의식하면서 써야 한다.

### 핵심 용어

- Entity: DB 테이블에 매핑되는 자바 클래스. `@Entity`가 붙어있고 식별자가 있다.
- EntityManager: Entity의 CRUD를 처리하는 JPA의 핵심 인터페이스. 영속성 컨텍스트 하나를 들고 있다.
- 영속성 컨텍스트(Persistence Context): EntityManager가 관리하는 1차 캐시. 같은 식별자의 Entity는 컨텍스트 안에서 단 하나의 인스턴스만 존재한다.
- Repository: 데이터 접근 계층을 인터페이스로 추상화한 것. Spring Data JPA가 프록시로 구현체를 만들어준다.
- JPQL: 테이블이 아니라 Entity와 필드를 대상으로 쓰는 쿼리 언어. 최종적으로는 SQL로 번역된다.

## 핵심

### 1. Entity 설계

```java
@Entity
@Table(name = "users")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 100)
    private String email;

    @Column(nullable = false)
    private String password;

    @Column(nullable = false, length = 50)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    @Builder
    public User(String email, String password, String name, Role role) {
        this.email = email;
        this.password = password;
        this.name = name;
        this.role = role;
    }
}
```

`@NoArgsConstructor(access = PROTECTED)`는 JPA가 리플렉션으로 Entity를 만들 때 기본 생성자가 필요해서 둔다. `public`으로 열어두면 도메인 외부에서 빈 객체를 만들어 쓸 수 있어 무결성이 깨진다. Setter도 같은 이유로 두지 않고, 의미가 있는 메서드(`changeName(...)`, `markAsPaid()` 같은)를 별도로 만든다.

#### 연관관계 매핑

```java
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();

    private int totalPrice;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    public void addItem(OrderItem item) {
        items.add(item);
        item.setOrder(this);
    }
}
```

연관관계를 잡을 때 신경 쓸 부분은 다음이 거의 전부다. `@ManyToOne`과 `@OneToOne`은 기본이 EAGER다. 명시적으로 LAZY로 바꿔야 한다. 양방향 매핑은 진짜 양쪽에서 조회 필요할 때만 만든다. 한쪽만 알아도 되면 단방향으로 두는 편이 단순하다. 양방향이면 편의 메서드를 만들어서 양쪽 컬렉션과 참조를 같이 갱신해줘야 한다. `cascade = ALL`과 `orphanRemoval = true`는 부모-자식 라이프사이클이 진짜로 묶여 있는 경우(주문-주문항목, 게시글-첨부파일)에만 쓰고, 단순 연관에는 절대 걸지 않는다. 잘못 걸면 Order 하나 지웠는데 User까지 같이 지워지는 사고가 난다.

### 2. Repository

```java
public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
    List<User> findByNameContaining(String keyword);
    List<User> findByRoleAndCreatedAtAfter(Role role, LocalDateTime date);

    void deleteByEmail(String email);

    Page<User> findByRole(Role role, Pageable pageable);
}
```

Spring Data JPA는 메서드 이름을 파싱해서 쿼리를 만들어준다. `findBy`, `existsBy`, `countBy` 같은 도입부 뒤에 필드 이름과 조건 키워드(`And`, `Or`, `Between`, `In`, `IsNull`, `OrderBy` 등)를 붙이면 된다.

#### 메서드 이름 쿼리의 한계와 함정

규칙대로 쓰면 편하지만 문제도 분명하다.

이름이 길어질수록 가독성이 빠르게 나빠진다. `findByRoleAndCreatedAtAfterAndDeletedAtIsNullOrderByCreatedAtDescNameAsc` 같은 메서드 이름을 본 적이 있을 텐데, 이 정도가 되면 차라리 `@Query`를 쓰는 게 읽기 쉽다. 경험적으로 조건이 셋을 넘어가면 메서드 이름 파싱은 포기하고 JPQL로 바꾸는 편이 낫다.

필드 이름을 잘못 적었을 때 컴파일이 안 되는 게 아니라 애플리케이션 기동 시점에 터진다. `findByEmal`로 오타를 내면 컴파일러는 통과시키고, Spring이 빈을 초기화하면서 "No property 'emal' found for type User" 같은 예외를 던진다. 운 좋게 통합 테스트에서 잡히지 않으면 운영 첫 호출에서 터진다.

키워드와 필드 이름이 충돌하는 경우도 있다. `OrderBy`라는 키워드가 정렬 의미로 예약되어 있는데, 만약 필드 이름에 `Or`나 `And`가 들어 있으면 파서가 혼란을 일으킨다. `firstName`, `findByName`은 괜찮지만 `findByOrAndOr` 같은 이름은 절대 못 만든다. 필드 이름에 `Is`, `Not`, `In`, `Between` 같은 키워드가 부분 문자열로 들어가 있으면 의도와 다르게 파싱될 수 있어 `@Query`로 풀어줘야 한다.

리팩터링에도 약하다. Entity 필드 이름을 IDE로 바꾸면 메서드 이름은 같이 바뀌지 않는다. `name`을 `displayName`으로 바꿔도 `findByName`은 그대로 남아 있다가 기동 시 깨진다. JPQL은 IDE가 Entity 필드를 인식하면 같이 바꿔주는 경우가 많아서, 리네이밍이 잦은 도메인은 JPQL 쪽이 안전하다.

복잡한 동적 조건이 필요한 경우엔 메서드 이름 쿼리로는 답이 없다. 검색 조건이 옵션 5개 중 일부만 들어오는 화면이라면 모든 조합에 대해 메서드를 만들 수 없다. 이때는 `Specification`이나 QueryDSL을 쓴다.

#### JPQL 쿼리

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    @Query("SELECT o FROM Order o JOIN FETCH o.user WHERE o.status = :status")
    List<Order> findByStatusWithUser(@Param("status") OrderStatus status);

    @Query("SELECT new com.example.dto.OrderSummary(o.id, o.totalPrice, u.name) " +
           "FROM Order o JOIN o.user u WHERE u.id = :userId")
    List<OrderSummary> findOrderSummariesByUserId(@Param("userId") Long userId);

    @Query(value = "SELECT * FROM orders WHERE total_price > :price", nativeQuery = true)
    List<Order> findExpensiveOrders(@Param("price") int price);

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Order o SET o.status = :status WHERE o.createdAt < :date")
    int updateOldOrdersStatus(@Param("status") OrderStatus status,
                              @Param("date") LocalDateTime date);
}
```

`@Modifying`을 쓰는 벌크 연산은 영속성 컨텍스트를 우회한다. 이미 1차 캐시에 올라와 있는 Entity가 있다면 DB와 메모리가 어긋날 수 있어 `clearAutomatically = true`로 컨텍스트를 비워주거나, 호출 직후 `entityManager.clear()`를 하거나, 벌크 이후에는 새로 트랜잭션을 열어 쓰는 방식 중 하나를 선택해야 한다.

### 3. ID 생성 전략

`@GeneratedValue`의 `strategy`는 네 가지 옵션이 있다. 어떤 걸 고르느냐에 따라 INSERT 시점, batch insert 가능 여부, DB 종속성이 달라진다.

`GenerationType.IDENTITY`는 DB의 auto-increment 컬럼에 의지하는 방식이다. MySQL/MariaDB의 `auto_increment`, PostgreSQL의 `SERIAL`/`IDENTITY`가 여기에 해당한다. 가장 쉽고 직관적이라 가장 많이 쓴다. 단점이 명확한데, `persist()`를 호출하는 순간 ID 값을 얻기 위해 즉시 INSERT 문이 나간다. 트랜잭션 끝까지 모아서 한 번에 보내는 batch insert가 원천적으로 불가능하다. 1만 건을 저장한다면 INSERT가 1만 번 나간다. JDBC 배치 사이즈를 늘려도 효과가 없다.

`GenerationType.SEQUENCE`는 DB의 시퀀스 객체를 호출해서 ID를 미리 가져온다. Oracle, PostgreSQL, H2가 시퀀스를 지원한다. 핵심 장점은 ID를 INSERT 전에 알 수 있다는 점이다. 그래서 영속성 컨텍스트가 INSERT를 트랜잭션 커밋 시점까지 모아두는 쓰기 지연이 가능하고, JDBC batch insert도 동작한다. `allocationSize`를 50, 100 같은 값으로 두면 시퀀스 호출 1번에 ID 50개를 한꺼번에 받아와 메모리에서 분배한다. 대량 INSERT가 잦은 시스템에서는 필수다.

`GenerationType.TABLE`은 별도의 테이블에 시퀀스 흉내를 내는 방식이다. 모든 DB에서 동작하지만 매번 그 테이블에 락을 걸어야 해서 동시성이 나쁘다. 시퀀스를 지원하지 않는 DB(과거 MySQL)에서 어쩔 수 없이 썼던 옵션이고, 지금은 거의 안 쓴다.

`GenerationType.AUTO`는 방언(Dialect)에 따라 위 셋 중 하나를 자동 선택한다. MySQL이면 IDENTITY, PostgreSQL/Oracle이면 SEQUENCE로 매핑된다. Hibernate 6부터 PostgreSQL에서 AUTO가 SEQUENCE로 가도록 명확해졌지만, DB를 바꿀 일이 있다면 명시적으로 strategy를 박아두는 게 의도를 분명히 한다.

#### MySQL auto_increment와 PostgreSQL sequence 차이

겉으로는 비슷해 보여도 동작이 다르다. MySQL의 `auto_increment`는 테이블 컬럼 속성이다. INSERT가 실행되면 그 시점에 다음 값을 자동으로 매겨주고, INSERT가 성공해야 그 값이 확정된다. 따라서 ID를 미리 받아올 수 없고, JPA에서 batch insert도 못 한다. 또한 트랜잭션이 롤백되어도 auto_increment 카운터는 되돌아오지 않는다. 1, 2, 3이 끝나고 4번이 롤백되면 다음 INSERT는 5번부터다. 운영하다 보면 ID에 구멍이 생기는데 정상 동작이다.

PostgreSQL의 sequence는 독립 객체다. `nextval('users_seq')`를 호출하면 트랜잭션과 무관하게 값이 증가한다. 그래서 INSERT 전에 ID를 미리 알 수 있고, batch insert가 가능하다. PostgreSQL에서 `SERIAL`, `BIGSERIAL`, `IDENTITY` 컬럼을 만들어도 내부적으로는 sequence가 깔린다. 즉 PostgreSQL에서 `GenerationType.IDENTITY`를 쓰면 시퀀스가 깔려 있는데도 JPA는 IDENTITY 의미로만 다뤄서 batch insert를 막아버린다. PostgreSQL이라면 `SEQUENCE` 전략을 명시적으로 쓰는 게 거의 항상 옳다.

```java
// PostgreSQL에서 batch insert를 의도한다면
@Entity
@SequenceGenerator(name = "user_seq", sequenceName = "users_seq", allocationSize = 50)
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "user_seq")
    private Long id;
}
```

```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc.batch_size: 50
        order_inserts: true
        order_updates: true
```

이 조합이라야 실제로 INSERT가 묶여 나간다. MySQL을 쓰면서 대량 INSERT 성능이 필요하면 JPA를 포기하고 `JdbcTemplate`의 `batchUpdate`로 내려가거나, 직접 시퀀스 흉내내는 테이블을 두는 식으로 우회한다.

### 4. N+1 문제와 해결

JPA에서 가장 흔하고 비싸게 치르는 실수다.

```java
List<Order> orders = orderRepository.findAll();
for (Order order : orders) {
    System.out.println(order.getUser().getName());
}
```

`Order.user`가 LAZY라서 처음 `findAll()`은 SELECT 하나로 끝난다. 그러나 루프에서 `getUser().getName()`을 호출하는 순간 각 Order마다 User를 별도 SELECT로 조회한다. 주문이 100개면 SQL이 101번 나간다. 운영에서 이걸 놓치면 응답 시간이 수십 밀리초에서 수 초로 튄다.

해결은 상황에 따라 다르다. 단건이나 1:N의 N쪽을 조회하면서 연관 Entity가 같이 필요한 경우는 `JOIN FETCH`가 가장 직관적이다. 조인 하나로 끝난다. 다만 `@OneToMany`를 fetch join하면 결과 행이 부풀어 페이징과 같이 쓸 수 없다. 이때는 `@BatchSize`나 `default_batch_fetch_size`로 IN 절을 묶는 방식이 안전하다.

```java
@Query("SELECT o FROM Order o JOIN FETCH o.user")
List<Order> findAllWithUser();
```

```java
@EntityGraph(attributePaths = {"user", "items"})
@Query("SELECT o FROM Order o")
List<Order> findAllWithDetails();
```

```java
@Entity
public class Order {
    @BatchSize(size = 100)
    @OneToMany(mappedBy = "order")
    private List<OrderItem> items;
}
```

읽기 전용이면 처음부터 Entity가 아니라 DTO로 프로젝션하는 게 빠르고 안전하다. DTO 프로젝션은 영속성 컨텍스트에 올라가지 않고, dirty checking도 일어나지 않는다.

### 5. EntityManager와 영속성 컨텍스트의 실제 동작

다이어그램으로 외우면 실전에서 헤맨다. 시나리오로 보면 명확해진다.

다음 코드를 한 줄씩 따라가보자.

```java
@Transactional
public Long createUser(String email) {
    User user = User.builder().email(email).name("kim").build(); // ①
    userRepository.save(user);                                     // ②
    User same = userRepository.findById(user.getId()).orElseThrow();// ③
    same.changeName("park");                                       // ④
    return user.getId();                                           // ⑤
}
```

①에서 `new User(...)`를 만든 순간 이 객체는 비영속(transient) 상태다. 영속성 컨텍스트는 이 객체의 존재를 모른다. ID 필드는 null이다.

②에서 `save()`를 호출한다. 내부적으로 `entityManager.persist(user)`가 불린다. 이 시점에 영속성 컨텍스트가 user를 받아들여 관리 대상으로 삼는다. `GenerationType.IDENTITY`라면 ID를 얻으려고 즉시 INSERT가 나간다(DB에서 auto_increment 값을 받아야 하니까). `GenerationType.SEQUENCE`라면 시퀀스 호출만 일어나고 INSERT는 커밋 시점으로 미뤄진다. 둘 다 user는 이제 영속(managed) 상태고, 1차 캐시에 ID를 키로 들어가 있다.

③에서 `findById(user.getId())`를 호출한다. 영속성 컨텍스트가 먼저 1차 캐시를 들여다본다. 같은 식별자가 이미 있으니 DB로 SELECT를 보내지 않고 캐시에 있는 인스턴스를 그대로 돌려준다. 즉 `user == same`이 true다. 동일 트랜잭션 안에서는 같은 ID의 Entity가 단 하나라는 보장이 여기서 나온다.

④에서 `same.changeName("park")`을 부른다. save도, update도, 어떤 Repository 메서드도 부르지 않았다. 그러나 영속 상태 Entity의 필드를 변경했기 때문에 영속성 컨텍스트가 변경 감지(dirty checking) 대상으로 표시해둔다.

⑤를 지나 메서드가 끝나면서 트랜잭션이 커밋된다. 이 시점에 flush가 일어난다. flush는 영속성 컨텍스트의 상태 변경을 SQL로 변환해서 DB로 내보내는 작업이다. ② 단계에서 SEQUENCE였다면 INSERT가 여기서 나가고, ④의 변경은 UPDATE로 나간다. 그러고 나서 트랜잭션이 커밋된다.

준영속(detached)과 삭제(removed) 상태도 정리해두면 좋다. 준영속은 영속성 컨텍스트가 닫혔거나 `entityManager.detach()`로 떼어낸 상태다. 변경해도 dirty checking이 일어나지 않는다. 다시 영속으로 만들려면 `merge()`를 부른다. `merge()`는 들어온 detached 객체의 값을 같은 ID의 영속 객체에 복사해 넣는다. 같은 ID가 캐시에 없으면 DB에서 가져온 뒤 복사한다. 들어온 객체 자체가 영속이 되는 게 아니라 새로 영속화된 사본이 반환된다는 점이 함정이다. 삭제는 `remove()`를 부르면 즉시 SQL이 나가는 게 아니라, 트랜잭션 커밋 시점에 DELETE가 나간다.

### 6. equals/hashCode의 함정

Entity의 `equals`와 `hashCode`를 어떻게 구현할지 결정해야 하는 순간이 온다. 보통 두 가지 선택지가 떠오른다. `@Id`로만 비교하거나, 비즈니스 키(예: 이메일)로 비교하거나.

`@Id` 기반 구현이 위험한 이유부터 보자.

```java
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof User other)) return false;
    return Objects.equals(this.id, other.id);
}

@Override
public int hashCode() {
    return Objects.hash(id);
}
```

겉보기엔 단순하고 합리적이다. 문제는 `GenerationType.IDENTITY`나 `SEQUENCE`로 ID가 영속화 시점에 할당된다는 데 있다.

```java
User a = new User("a@x.com");
Set<User> set = new HashSet<>();
set.add(a);                        // hashCode(a) = Objects.hash(null) = 0
userRepository.save(a);            // 영속화 후 a.id = 1
set.contains(a);                   // hashCode(a) = Objects.hash(1) = 다른 값
                                   // → false 반환
```

영속화 전후로 같은 인스턴스의 `hashCode`가 바뀐다. `HashSet`이나 `HashMap`에 넣어두면 같은 객체인데 못 찾는 사태가 벌어진다. JPA가 내부적으로 컬렉션을 다룰 때 이 문제로 깨질 수도 있다.

또 하나 비슷한 함정이 LAZY 프록시다. `a.equals(b)`를 호출했는데 `b`가 Hibernate 프록시면 `instanceof User`가 어떻게 평가될지부터 봐야 한다. 같은 ID인데 한쪽은 실제 클래스, 한쪽은 프록시면 `getClass()`로 비교하는 구현은 거의 항상 false가 나온다. `instanceof`를 써야 안전하다.

실용적인 절충안은 이렇다. ID가 null이면 `equals`는 `this == other`(레퍼런스 비교)로 처리하고, null이 아니면 ID로 비교한다. `hashCode`는 ID 값을 쓰지 않고 클래스 상수를 돌려준다.

```java
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof User other)) return false;
    return id != null && id.equals(other.id);
}

@Override
public int hashCode() {
    return getClass().hashCode();
}
```

`hashCode`가 모든 인스턴스에서 같은 값이 나오므로 `HashSet` 안에서 모든 비교가 `equals`로 떨어진다는 단점이 있지만, Entity를 거대한 Set에 잔뜩 담는 일은 흔하지 않다. ID 기반 hashCode가 깨지는 사고보다 훨씬 낫다.

비즈니스 키가 진짜 불변이라면(예: 이메일이 정말로 변하지 않는 도메인이라면) 그쪽으로 `equals`를 짜는 것도 방법이다. 그러나 "지금은 안 바뀐다"는 보장은 시간이 지나면 깨지는 경우가 많아서 ID 기반 절충안을 기본으로 잡고, 비즈니스 키는 별도의 `isSameUser(...)` 같은 메서드로 두는 편을 선호한다.

### 7. 페이징과 정렬

```java
@GetMapping("/users")
public Page<UserResponse> getUsers(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        @RequestParam(defaultValue = "createdAt") String sort) {

    Pageable pageable = PageRequest.of(page, size, Sort.by(sort).descending());
    return userRepository.findByRole(Role.USER, pageable)
        .map(UserResponse::from);
}
```

```java
public interface UserRepository extends JpaRepository<User, Long> {

    Page<User> findByRole(Role role, Pageable pageable);

    @Query(value = "SELECT u FROM User u WHERE u.role = :role",
           countQuery = "SELECT COUNT(u.id) FROM User u WHERE u.role = :role")
    Page<User> findByRoleOptimized(@Param("role") Role role, Pageable pageable);
}
```

기본 카운트 쿼리는 본문 쿼리를 그대로 본떠서 만들어진다. 본문에 JOIN FETCH가 있으면 카운트 쿼리도 부풀어서 비싸진다. 카운트가 느리면 `countQuery`를 분리하거나, 카운트가 정확할 필요가 없다면 `Slice`를 써서 `hasNext()`만 확인하는 방식으로 바꾼다.

## 예시

### Auditing 설정

```java
@Configuration
@EnableJpaAuditing
public class JpaConfig { }

@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
@Getter
public abstract class BaseEntity {

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;
}

@Entity
public class User extends BaseEntity {
    // createdAt, updatedAt 자동 관리
}
```

### Soft Delete

```java
@Entity
@SQLRestriction("deleted_at IS NULL")   // Spring Boot 3.x (Hibernate 6.3+)
public class User extends BaseEntity {

    private LocalDateTime deletedAt;

    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
    }

    public boolean isDeleted() {
        return deletedAt != null;
    }
}
```

```java
@Transactional
public void deleteUser(Long userId) {
    User user = userRepository.findById(userId)
        .orElseThrow(() -> new UserNotFoundException(userId));
    user.softDelete();
}
```

## 운영 팁

### open-in-view를 둘러싼 사고들

Spring Boot의 기본값이 `spring.jpa.open-in-view=true`다. 의미는 영속성 컨텍스트를 트랜잭션 경계보다 길게, HTTP 응답이 클라이언트로 나가기 직전까지 살려두겠다는 뜻이다. 컨트롤러나 뷰 렌더링 단계에서 LAZY 연관을 건드려도 `LazyInitializationException`이 안 터지니까 개발 초기엔 편하다. 문제는 운영에 들어가면서 시작된다.

첫 번째는 커넥션 점유 시간이 길어진다. OSIV가 켜져 있으면 트랜잭션이 끝나도 영속성 컨텍스트가 DB 커넥션을 끝까지 들고 있다. 컨트롤러가 외부 API를 호출하거나, 뷰 렌더링이 오래 걸리면 그동안 커넥션이 풀에 반환되지 않는다. HikariCP의 풀 크기를 10으로 잡아둔 서비스에서 동시 요청 11개가 들어오면 11번째가 커넥션을 기다리며 멈춘다. 외부 API 응답이 느려질 때 동시에 DB 커넥션 풀까지 마르는 사고를 종종 본다.

두 번째는 컨트롤러/뷰 단계에서 의도치 않은 LAZY 로딩이 일어난다. 서비스에서 Order만 조회해서 반환했는데 컨트롤러가 응답 직렬화하면서 `order.getUser().getName()`을 건드리면 그 자리에서 SELECT가 나간다. 응답 객체 하나에 LAZY 필드가 여럿 있으면 N+1이 컨트롤러 단에서 일어난다. 서비스 단에서는 보이지 않으니 디버깅이 어렵다.

세 번째는 트랜잭션 경계가 흐려진다. 컨트롤러 코드에서 무심코 Entity를 수정하면 OSIV 환경에서는 영속성 컨텍스트는 살아있지만 트랜잭션은 끝나 있어서, 변경이 DB에 반영되지 않는다. "왜 데이터가 안 바뀌지?"를 한참 찾다가 트랜잭션 안에서 수정하지 않았다는 걸 깨닫는다. 반대로 OSIV가 꺼져 있으면 컨트롤러에서 LAZY 필드를 건드리는 순간 예외가 터지니까 차라리 명확하다.

운영에서는 `open-in-view=false`로 두고, 컨트롤러/뷰에 넘기기 전에 서비스 안에서 필요한 데이터를 전부 fetch join이나 DTO로 끌어와 두는 방식이 안전하다. OSIV를 끄면 LazyInitializationException이 우수수 터지는데, 그게 정상이다. 각각이 다 "여기 LAZY 접근이 트랜잭션 밖에서 일어나고 있다"는 신호다. 그 자리를 서비스 단에서 fetch join이나 DTO 프로젝션으로 막으면 된다.

### 권장 설정과 환경별 선택

운영용 `application.yml`은 다음 형태를 기본으로 잡는다.

```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false
    properties:
      hibernate:
        default_batch_fetch_size: 100
        format_sql: true
        jdbc.batch_size: 50
        order_inserts: true
        order_updates: true
logging:
  level:
    org.hibernate.SQL: debug
    org.hibernate.orm.jdbc.bind: trace
```

`ddl-auto`는 운영에서는 반드시 `validate`다. `update`나 `create`로 두면 애플리케이션이 스키마를 마음대로 바꾼다. 스키마 변경은 Flyway나 Liquibase 같은 마이그레이션 도구로만 관리하는 게 원칙이고, 운영 DB에 JPA가 ALTER를 날리는 일은 사고로 이어진다.

`open-in-view`는 위에서 본 이유로 운영은 무조건 `false`다. 로컬 개발에서도 가급적 `false`로 두고 미리 LAZY 누락을 발견하는 편이 좋다.

`default_batch_fetch_size`는 LAZY 컬렉션을 IN 절로 묶어서 가져오게 만든다. 100~500 사이에서 도메인 크기에 맞춰 잡으면 된다. `jdbc.batch_size`와 `order_inserts`, `order_updates`는 batch insert/update를 활성화한다. ID 전략이 IDENTITY면 어차피 효과가 없으니, SEQUENCE를 쓰는 PostgreSQL/Oracle 환경에서 의미가 있다.

`show-sql`보다는 `logging.level.org.hibernate.SQL`로 로그를 켜는 편을 권한다. 로그 포맷이 일관되고, 바인딩 파라미터는 `org.hibernate.orm.jdbc.bind`(Hibernate 6) 또는 `org.hibernate.type.descriptor.sql`(Hibernate 5) 레벨로 따로 켤 수 있다. 운영에서는 둘 다 꺼야 한다. 모든 SQL을 찍으면 디스크가 차고, 바인딩 파라미터 로그는 비밀번호나 토큰 같은 민감값을 그대로 남길 수 있다.

스테이징은 운영과 동일하게 두는 게 원칙이다. 로컬 개발만 `ddl-auto`를 `create`나 `update`로 풀어서 빠르게 실험하고, 나머지 환경은 운영 설정을 그대로 따라가야 환경 차이로 인한 버그를 줄일 수 있다.

## 참고

- [Spring Data JPA 공식 문서](https://docs.spring.io/spring-data/jpa/reference/)
- [Hibernate 공식 문서](https://hibernate.org/orm/documentation/)
- [데이터베이스 심화](../../../Backend/Database/Database_Deep_Dive.md)
- [데이터베이스 성능 튜닝](../../../DataBase/RDBMS/데이터베이스_성능_튜닝.md)
