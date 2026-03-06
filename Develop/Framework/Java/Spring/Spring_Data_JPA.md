---
title: Spring Data JPA 핵심 개념과 실전 적용
tags: [framework, java, spring, jpa, hibernate, orm, database, query]
updated: 2026-03-01
---

# Spring Data JPA 핵심 개념과 실전 적용

## 배경

Spring Data JPA는 JPA(Java Persistence API)를 더 쉽게 사용할 수 있도록 Spring이 제공하는 모듈이다. Repository 인터페이스만 정의하면 CRUD 쿼리를 자동 생성해주며, 복잡한 쿼리도 메서드 이름이나 JPQL, QueryDSL로 처리할 수 있다.

### 계층 구조

```
Spring Data JPA          ← 추상화 (Repository, 메서드 쿼리)
       │
      JPA                ← 표준 스펙 (EntityManager, JPQL)
       │
   Hibernate             ← 구현체 (실제 SQL 생성, 캐시)
       │
     JDBC                ← DB 연결 (Connection, Statement)
       │
   PostgreSQL/MySQL      ← 데이터베이스
```

### 핵심 용어

| 용어 | 설명 |
|------|------|
| **Entity** | DB 테이블에 매핑되는 Java 클래스 |
| **EntityManager** | Entity의 CRUD를 처리하는 JPA 핵심 인터페이스 |
| **영속성 컨텍스트** | Entity를 관리하는 1차 캐시 영역 |
| **Repository** | 데이터 접근 계층의 추상화 인터페이스 |
| **JPQL** | 테이블이 아닌 Entity 기반 쿼리 언어 |

## 핵심

### 1. Entity 설계

#### 기본 Entity

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

📌 **설계 원칙:**
- `@NoArgsConstructor(access = PROTECTED)`: JPA 요구사항. 외부에서 기본 생성자 호출 방지
- `@Builder`: 명확한 생성 패턴 제공
- Setter 없음: 변경이 필요한 경우 의미 있는 메서드명 사용 (`changeName()` 등)

#### 연관관계 매핑

```java
// 1:N 관계 (User → Order)
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)   // 지연 로딩 (필수!)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();

    private int totalPrice;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    // 연관관계 편의 메서드
    public void addItem(OrderItem item) {
        items.add(item);
        item.setOrder(this);
    }
}
```

**연관관계 매핑 원칙:**

| 원칙 | 설명 | 이유 |
|------|------|------|
| **`@ManyToOne`은 항상 LAZY** | `fetch = FetchType.LAZY` | N+1 문제 방지 |
| **양방향 매핑 최소화** | 꼭 필요할 때만 양방향 | 복잡도 증가 방지 |
| **연관관계 편의 메서드** | 양방향일 때 양쪽 동기화 | 데이터 불일치 방지 |
| **`cascade` 신중하게** | 부모-자식 관계에서만 | 의도치 않은 삭제 방지 |

### 2. Repository

#### 기본 Repository

```java
public interface UserRepository extends JpaRepository<User, Long> {

    // 쿼리 메서드 — 메서드 이름으로 쿼리 자동 생성
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
    List<User> findByNameContaining(String keyword);
    List<User> findByRoleAndCreatedAtAfter(Role role, LocalDateTime date);

    // 삭제
    void deleteByEmail(String email);

    // 정렬 및 페이징
    Page<User> findByRole(Role role, Pageable pageable);
}
```

**쿼리 메서드 키워드:**

| 키워드 | 예시 | 생성되는 SQL |
|--------|------|-------------|
| `findBy` | `findByEmail(email)` | `WHERE email = ?` |
| `existsBy` | `existsByEmail(email)` | `SELECT EXISTS(...)` |
| `countBy` | `countByRole(role)` | `SELECT COUNT(...)` |
| `And` / `Or` | `findByNameAndEmail(...)` | `WHERE name = ? AND email = ?` |
| `OrderBy` | `findByRoleOrderByCreatedAtDesc(...)` | `ORDER BY created_at DESC` |
| `Between` | `findByCreatedAtBetween(start, end)` | `WHERE created_at BETWEEN ? AND ?` |
| `In` | `findByIdIn(ids)` | `WHERE id IN (?, ?, ?)` |
| `IsNull` | `findByDeletedAtIsNull()` | `WHERE deleted_at IS NULL` |

#### JPQL 쿼리

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    // JPQL: Entity 기반 쿼리
    @Query("SELECT o FROM Order o JOIN FETCH o.user WHERE o.status = :status")
    List<Order> findByStatusWithUser(@Param("status") OrderStatus status);

    // DTO 프로젝션
    @Query("SELECT new com.example.dto.OrderSummary(o.id, o.totalPrice, u.name) " +
           "FROM Order o JOIN o.user u WHERE u.id = :userId")
    List<OrderSummary> findOrderSummariesByUserId(@Param("userId") Long userId);

    // 네이티브 쿼리 (필요 시)
    @Query(value = "SELECT * FROM orders WHERE total_price > :price", nativeQuery = true)
    List<Order> findExpensiveOrders(@Param("price") int price);

    // 벌크 업데이트
    @Modifying(clearAutomatically = true)
    @Query("UPDATE Order o SET o.status = :status WHERE o.createdAt < :date")
    int updateOldOrdersStatus(@Param("status") OrderStatus status,
                              @Param("date") LocalDateTime date);
}
```

### 3. N+1 문제와 해결

JPA를 사용할 때 가장 흔하고 심각한 성능 문제이다.

#### 문제 상황

```java
// N+1 발생: 주문 10개 조회 시 → 1(주문) + 10(사용자) = 11번 쿼리
List<Order> orders = orderRepository.findAll();
for (Order order : orders) {
    System.out.println(order.getUser().getName());  // 여기서 각각 SELECT 발생
}
```

```sql
-- 실행되는 쿼리 (11번!)
SELECT * FROM orders;                    -- 1번
SELECT * FROM users WHERE id = 1;       -- 2번
SELECT * FROM users WHERE id = 2;       -- 3번
...                                      -- N번
```

#### 해결 방법

| 방법 | 코드 | 적합한 상황 |
|------|------|-----------|
| **Fetch Join** | `JOIN FETCH o.user` | 가장 일반적, 1:1/N:1 |
| **@EntityGraph** | `@EntityGraph(attributePaths = {"user"})` | 간단한 경우 |
| **@BatchSize** | `@BatchSize(size = 100)` | 컬렉션 로딩 |
| **DTO 프로젝션** | `SELECT new DTO(...)` | 읽기 전용 |

```java
// 해결 1: Fetch Join (가장 권장)
@Query("SELECT o FROM Order o JOIN FETCH o.user")
List<Order> findAllWithUser();
// → SELECT * FROM orders o JOIN users u ON o.user_id = u.id (1번!)

// 해결 2: EntityGraph
@EntityGraph(attributePaths = {"user", "items"})
@Query("SELECT o FROM Order o")
List<Order> findAllWithDetails();

// 해결 3: BatchSize (Entity 클래스에 적용)
@Entity
public class Order {
    @BatchSize(size = 100)
    @OneToMany(mappedBy = "order")
    private List<OrderItem> items;
}
// → WHERE order_id IN (1, 2, 3, ... 100) 으로 묶어서 조회
```

### 4. 영속성 컨텍스트

JPA의 핵심 개념이다. Entity의 상태를 관리하고, **1차 캐시**와 **변경 감지(Dirty Checking)**를 제공한다.

#### Entity 생명주기

```
                    persist()
  비영속(new) ────────────────▶ 영속(managed)
                                  │     ▲
                           find() │     │ merge()
                                  ▼     │
                               준영속(detached)
                                  │
                           remove()│
                                  ▼
                               삭제(removed)
```

#### 변경 감지 (Dirty Checking)

```java
@Transactional
public void updateUserName(Long userId, String newName) {
    User user = userRepository.findById(userId)
        .orElseThrow(() -> new UserNotFoundException(userId));

    user.changeName(newName);  // setter 대신 의미 있는 메서드
    // save() 호출 불필요! 트랜잭션 커밋 시 변경 감지로 자동 UPDATE
}
```

📌 `@Transactional` 범위 내에서 영속 상태 Entity를 수정하면 **자동으로 UPDATE 쿼리가 실행**된다. `save()`를 다시 호출할 필요가 없다.

### 5. 페이징과 정렬

```java
// Controller
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
// Repository
public interface UserRepository extends JpaRepository<User, Long> {

    Page<User> findByRole(Role role, Pageable pageable);

    // 커스텀 카운트 쿼리 (성능 최적화)
    @Query(value = "SELECT u FROM User u WHERE u.role = :role",
           countQuery = "SELECT COUNT(u.id) FROM User u WHERE u.role = :role")
    Page<User> findByRoleOptimized(@Param("role") Role role, Pageable pageable);
}
```

**응답 예시:**
```json
{
  "content": [ ... ],
  "totalElements": 150,
  "totalPages": 8,
  "size": 20,
  "number": 0,
  "first": true,
  "last": false
}
```

## 예시

### 1. Auditing 설정 (생성일/수정일 자동 관리)

```java
// 설정
@Configuration
@EnableJpaAuditing
public class JpaConfig { }

// BaseEntity
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

// Entity에서 상속
@Entity
public class User extends BaseEntity {
    // createdAt, updatedAt 자동 관리
}
```

### 2. Soft Delete 패턴

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
// Service
@Transactional
public void deleteUser(Long userId) {
    User user = userRepository.findById(userId)
        .orElseThrow(() -> new UserNotFoundException(userId));
    user.softDelete();  // UPDATE users SET deleted_at = NOW() WHERE id = ?
}
```

## 운영 팁

### 성능 최적화 체크리스트

| 항목 | 설명 | 우선순위 |
|------|------|---------|
| **N+1 확인** | 로그에 `hibernate.show_sql=true`로 쿼리 수 확인 | ✅ 필수 |
| **LAZY 로딩** | `@ManyToOne`은 반드시 LAZY | ✅ 필수 |
| **Fetch Join** | 연관 Entity가 필요한 곳에 적용 | ✅ 필수 |
| **DTO 프로젝션** | 읽기 전용 조회는 Entity 대신 DTO | ⭐ 권장 |
| **벌크 연산** | 대량 UPDATE/DELETE는 `@Modifying` 사용 | ⭐ 권장 |
| **인덱스** | 자주 조회하는 컬럼에 `@Index` 추가 | ⭐ 권장 |
| **커넥션 풀** | HikariCP 설정 최적화 | ⭐ 권장 |

### application.yml 권장 설정

```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: validate        # 프로덕션: validate (스키마 변경 차단)
    open-in-view: false          # OSIV 비활성화 (성능/예측 가능성)
    properties:
      hibernate:
        default_batch_fetch_size: 100   # BatchSize 글로벌 설정
        format_sql: true                # SQL 포맷팅 (개발 환경)

  # 개발 환경에서만
  # jpa.show-sql: true           → logging으로 대체 권장
logging:
  level:
    org.hibernate.SQL: debug             # 실행 SQL
    org.hibernate.orm.jdbc.bind: trace   # 바인딩 파라미터
```

| 설정 | 개발 | 스테이징 | 프로덕션 |
|------|------|---------|---------|
| `ddl-auto` | create / update | validate | validate |
| `show-sql` | true | false | false |
| `open-in-view` | true (편의) | false | false |
| `format_sql` | true | false | false |

## 참고

- [Spring Data JPA 공식 문서](https://docs.spring.io/spring-data/jpa/reference/)
- [Hibernate 공식 문서](https://hibernate.org/orm/documentation/)
- [데이터베이스 심화](../../Backend/Database/Database_Deep_Dive.md)
- [데이터베이스 성능 튜닝](../../DataBase/RDBMS/데이터베이스_성능_튜닝.md)
