---
title: Spring Data JPA 심화 - 동적 쿼리, 락, 영속성 컨텍스트, 대용량 처리
tags: [framework, java, spring, jpa, hibernate, querydsl, locking, projection, performance]
updated: 2026-05-01
---

# Spring Data JPA 심화

기초 Repository와 단순 CRUD만으로는 실무 요구사항을 감당하기 어렵다. 동적 쿼리, 동시성 제어, 대용량 처리, 멀티 데이터소스 같은 주제는 JPA를 깊이 있게 이해해야 풀 수 있다. 이 문서는 `Spring_Data_JPA.md`의 기초·중급 내용을 알고 있다는 전제로, 실제 프로덕션에서 부딪히는 문제와 해결 방법을 정리한다.

## QueryDSL과 동적 쿼리

`@Query` JPQL은 문자열 기반이라 컴파일 타임에 오타를 잡지 못하고, 동적으로 조건을 조합하는 일이 까다롭다. QueryDSL은 Q클래스를 통한 타입 세이프 쿼리 작성이 가능하고, `BooleanBuilder`나 `BooleanExpression`으로 조건을 자연스럽게 합칠 수 있다.

### 설정

Gradle에서 QueryDSL JPA를 추가할 때 Hibernate 6.x 기반 Spring Boot 3.x에서는 `jakarta` 분류자가 필요하다.

```groovy
dependencies {
    implementation 'com.querydsl:querydsl-jpa:5.1.0:jakarta'
    annotationProcessor 'com.querydsl:querydsl-apt:5.1.0:jakarta'
    annotationProcessor 'jakarta.annotation:jakarta.annotation-api'
    annotationProcessor 'jakarta.persistence:jakarta.persistence-api'
}
```

`jakarta` 분류자를 빼먹으면 `javax.persistence.Entity` 기반 Q클래스가 생성되어 `NoClassDefFoundError`를 만난다. Boot 2.x → 3.x 마이그레이션 중 흔히 겪는 문제다.

### 동적 검색 조건

```java
@RequiredArgsConstructor
public class OrderRepositoryImpl implements OrderRepositoryCustom {

    private final JPAQueryFactory queryFactory;

    @Override
    public Page<OrderDto> search(OrderSearchCond cond, Pageable pageable) {
        QOrder order = QOrder.order;
        QMember member = QMember.member;

        List<OrderDto> content = queryFactory
            .select(Projections.constructor(OrderDto.class,
                order.id, order.orderNumber, member.name, order.totalPrice))
            .from(order)
            .leftJoin(order.member, member)
            .where(
                memberNameEq(cond.getMemberName()),
                statusEq(cond.getStatus()),
                orderedAtBetween(cond.getFromDate(), cond.getToDate())
            )
            .orderBy(order.id.desc())
            .offset(pageable.getOffset())
            .limit(pageable.getPageSize())
            .fetch();

        JPAQuery<Long> countQuery = queryFactory
            .select(order.count())
            .from(order)
            .leftJoin(order.member, member)
            .where(
                memberNameEq(cond.getMemberName()),
                statusEq(cond.getStatus()),
                orderedAtBetween(cond.getFromDate(), cond.getToDate())
            );

        return PageableExecutionUtils.getPage(content, pageable, countQuery::fetchOne);
    }

    private BooleanExpression memberNameEq(String name) {
        return StringUtils.hasText(name) ? QMember.member.name.eq(name) : null;
    }

    private BooleanExpression statusEq(OrderStatus status) {
        return status != null ? QOrder.order.status.eq(status) : null;
    }

    private BooleanExpression orderedAtBetween(LocalDate from, LocalDate to) {
        if (from == null && to == null) return null;
        if (from == null) return QOrder.order.orderedAt.loe(to.atTime(LocalTime.MAX));
        if (to == null) return QOrder.order.orderedAt.goe(from.atStartOfDay());
        return QOrder.order.orderedAt.between(from.atStartOfDay(), to.atTime(LocalTime.MAX));
    }
}
```

`BooleanExpression` 메서드가 `null`을 반환하면 `where`에서 자동으로 무시한다. `BooleanBuilder`보다 메서드 단위로 조건을 조합·재사용하기 쉽다. `PageableExecutionUtils.getPage`는 콘텐츠 수가 페이지 크기보다 작거나 마지막 페이지인 경우 count 쿼리 실행을 생략해 약간의 성능 이득이 있다.

### DTO 프로젝션

QueryDSL에서 DTO로 받는 방법은 세 가지다.

- `Projections.bean(...)`: setter 호출. DTO에 setter가 있어야 한다.
- `Projections.fields(...)`: 필드 직접 주입. private 필드여도 리플렉션으로 접근.
- `Projections.constructor(...)`: 생성자 호출. 인자 순서·타입이 정확히 맞아야 한다.

`@QueryProjection`을 DTO 생성자에 붙이면 컴파일 타임에 검증되는 가장 안전한 방식이지만, DTO가 QueryDSL에 의존하게 되는 단점이 있다. 도메인 DTO는 외부 의존을 두지 않는 게 원칙이라 `Projections.constructor`를 더 자주 쓴다.

## Specification API와 Criteria 빌더

QueryDSL을 도입할 수 없는 환경(빌드 도구 제약, 정책)에서 동적 쿼리를 풀려면 Spring Data JPA의 `Specification`을 사용한다. JPA Criteria API를 감싼 인터페이스로, 람다 한 줄로 조건을 조합할 수 있다.

```java
public class OrderSpecs {

    public static Specification<Order> memberNameEq(String name) {
        return (root, query, cb) -> {
            if (!StringUtils.hasText(name)) return cb.conjunction();
            Join<Order, Member> member = root.join("member");
            return cb.equal(member.get("name"), name);
        };
    }

    public static Specification<Order> statusIn(Collection<OrderStatus> statuses) {
        return (root, query, cb) -> {
            if (CollectionUtils.isEmpty(statuses)) return cb.conjunction();
            return root.get("status").in(statuses);
        };
    }
}

// 사용
Specification<Order> spec = Specification
    .where(OrderSpecs.memberNameEq(cond.getMemberName()))
    .and(OrderSpecs.statusIn(cond.getStatuses()));
Page<Order> page = orderRepository.findAll(spec, pageable);
```

문제는 Criteria API 자체가 장황하고, JPQL이나 SQL을 머릿속에서 변환해보지 않으면 어떤 쿼리가 나갈지 직관적으로 알기 어렵다는 점이다. 실무에서는 정적 분석이 어려워 디버깅에 시간이 더 걸리는 경우가 많다. 단순 필터 검색이 아니라 정렬·조인·서브쿼리가 들어가면 QueryDSL 쪽이 압도적으로 가독성이 좋다.

`cb.conjunction()`은 `WHERE 1=1`에 해당하는 기본 참 조건이다. null을 반환하면 Spring Data JPA가 무시해주지만, 직접 조립할 때는 명시적으로 conjunction을 반환하는 편이 안전하다.

## Custom Repository 구현 패턴

Spring Data JPA에서 Repository에 직접 작성하기 어려운 쿼리(QueryDSL, 네이티브 SQL, EntityManager 직접 사용)는 Custom Repository 패턴으로 분리한다.

```java
public interface OrderRepositoryCustom {
    Page<OrderDto> search(OrderSearchCond cond, Pageable pageable);
    void bulkUpdateStatus(List<Long> ids, OrderStatus status);
}

@RequiredArgsConstructor
public class OrderRepositoryImpl implements OrderRepositoryCustom {
    private final JPAQueryFactory queryFactory;
    private final EntityManager em;
    // 구현
}

public interface OrderRepository extends JpaRepository<Order, Long>, OrderRepositoryCustom {
    Optional<Order> findByOrderNumber(String orderNumber);
}
```

규칙은 두 가지다.

1. 구현체 클래스 이름은 인터페이스 이름 + `Impl`이어야 한다 (`OrderRepositoryCustom` → `OrderRepositoryImpl`이 아니라 `OrderRepository` + `Impl`이다. 헷갈리지 말자).
2. 구현체와 Custom 인터페이스가 같은 패키지에 있어야 자동 인식된다. 다른 패키지로 옮기려면 `@EnableJpaRepositories(repositoryImplementationPostfix = "Impl")` 같은 설정을 손봐야 한다.

여러 Repository에서 공유하는 로직(예: soft-delete 일괄 처리)은 베이스 Repository를 만들어 `@EnableJpaRepositories(repositoryBaseClass = ...)`로 등록하는 방법도 있다. 다만 베이스 클래스를 바꾸는 순간 모든 Repository에 영향을 주므로 도입 결정은 신중해야 한다.

## Projection 종류와 성능 차이

엔티티 전체가 아니라 일부 컬럼만 필요한 경우 Projection을 쓴다. 세 가지 방식이 있고, 동작과 성능이 모두 다르다.

### Interface Projection

```java
public interface OrderSummary {
    Long getId();
    String getOrderNumber();
    BigDecimal getTotalPrice();
}

List<OrderSummary> findByMemberId(Long memberId);
```

- **Closed projection**: getter가 엔티티 필드명과 1:1로 매칭되는 경우. Hibernate가 SELECT 절에 필요한 컬럼만 포함시킨다.
- **Open projection**: `@Value("#{target.firstName + ' ' + target.lastName}")` 같은 SpEL을 쓰는 경우. 모든 필드를 SELECT한 뒤 메모리에서 계산한다. SELECT * 쿼리가 나가므로 컬럼 수가 많은 테이블에서 성능 차이가 크다.

```java
public interface MemberFullName {
    @Value("#{target.firstName + ' ' + target.lastName}")
    String getFullName();
}
```

이 코드는 firstName, lastName만 필요해 보이지만 실제로는 모든 컬럼이 SELECT된다. closed projection으로 가져온 뒤 서비스 계층에서 합치는 편이 더 빠르다.

### Class Projection (DTO)

```java
public class OrderDto {
    private final Long id;
    private final String orderNumber;
    public OrderDto(Long id, String orderNumber) { ... }
}

@Query("SELECT new com.example.OrderDto(o.id, o.orderNumber) FROM Order o WHERE o.member.id = :memberId")
List<OrderDto> findOrderDtos(@Param("memberId") Long memberId);
```

JPQL `new` 키워드로 즉시 DTO에 매핑한다. 컬럼만 SELECT되고 영속성 컨텍스트에 엔티티가 올라가지 않아 메모리·캐시 부담이 작다. 다만 패키지 풀 경로를 적어야 해서 길어진다.

### Dynamic Projection

```java
<T> List<T> findByMemberId(Long memberId, Class<T> type);

// 호출
List<OrderSummary> summaries = repository.findByMemberId(1L, OrderSummary.class);
List<OrderDetail> details = repository.findByMemberId(1L, OrderDetail.class);
```

같은 메서드로 여러 Projection을 골라 쓸 수 있다. 화면별로 필요한 필드가 다른 경우 메서드를 여러 개 만들지 않아도 된다.

## 비관적 락과 낙관적 락

동시성 문제를 푸는 방식에 따라 구현 방법이 갈린다.

### 낙관적 락 (Optimistic Lock)

`@Version` 컬럼으로 변경 충돌을 감지한다. 트랜잭션이 짧고 충돌 가능성이 낮을 때 적합하다.

```java
@Entity
public class Stock {
    @Id @GeneratedValue private Long id;
    private Long productId;
    private Long quantity;

    @Version
    private Long version;

    public void decrease(Long quantity) {
        if (this.quantity < quantity) {
            throw new IllegalStateException("재고 부족");
        }
        this.quantity -= quantity;
    }
}
```

UPDATE 시 `WHERE id = ? AND version = ?`이 자동으로 붙고, 영향받은 row가 0이면 `OptimisticLockException`이 던져진다 (Spring에서는 `ObjectOptimisticLockingFailureException`).

문제는 충돌 시 사용자에게 그대로 에러를 돌려줄 수 없다는 점이다. 일반적으로 짧은 재시도 로직을 둔다.

```java
@Service
@RequiredArgsConstructor
public class StockService {

    private final StockRepository stockRepository;

    @Retryable(
        retryFor = ObjectOptimisticLockingFailureException.class,
        maxAttempts = 3,
        backoff = @Backoff(delay = 50, multiplier = 2)
    )
    @Transactional
    public void decrease(Long productId, Long quantity) {
        Stock stock = stockRepository.findByProductId(productId)
            .orElseThrow();
        stock.decrease(quantity);
    }
}
```

`@Retryable`은 트랜잭션 메서드 바깥에 있어야 한다. 같은 메서드에 `@Transactional`과 `@Retryable`을 같이 두면 동일 트랜잭션 안에서 재시도하게 되어 의미가 없다. 호출 계층을 분리하거나 AOP 우선순위를 조정해야 한다.

### 비관적 락 (Pessimistic Lock)

DB 수준에서 row를 잠근다. 충돌이 잦거나 손실이 큰 작업(결제, 재고 차감)에 적합하다.

```java
public interface StockRepository extends JpaRepository<Stock, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT s FROM Stock s WHERE s.productId = :productId")
    Optional<Stock> findByProductIdForUpdate(@Param("productId") Long productId);
}
```

MySQL InnoDB에서는 `SELECT ... FOR UPDATE`로 변환된다. 트랜잭션이 커밋되거나 롤백될 때까지 다른 트랜잭션은 같은 row를 변경할 수 없다.

비관적 락은 락 대기 시간이 길어지면 데드락이나 타임아웃을 유발한다. PostgreSQL은 `lock_timeout`, MySQL은 `innodb_lock_wait_timeout`으로 제어한다. JPA에서는 힌트로 명시할 수 있다.

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@QueryHints({@QueryHint(name = "jakarta.persistence.lock.timeout", value = "3000")})
@Query("SELECT s FROM Stock s WHERE s.id = :id")
Optional<Stock> findByIdForUpdate(@Param("id") Long id);
```

타임아웃 단위는 ms이지만 DB 벤더가 무시하는 경우가 있다. 운영에서는 DB 파라미터로 직접 잡는 게 더 확실하다.

## @EntityGraph 심화

Fetch Join을 어노테이션으로 정의하는 방식이다. 같은 Repository 메서드에서 페치 전략을 바꿔 쓸 수 있다.

```java
@Entity
@NamedEntityGraph(
    name = "Order.withMemberAndItems",
    attributeNodes = {
        @NamedAttributeNode("member"),
        @NamedAttributeNode(value = "orderItems", subgraph = "items-subgraph")
    },
    subgraphs = @NamedSubgraph(
        name = "items-subgraph",
        attributeNodes = @NamedAttributeNode("product")
    )
)
public class Order { ... }

public interface OrderRepository extends JpaRepository<Order, Long> {

    @EntityGraph(value = "Order.withMemberAndItems")
    Optional<Order> findById(Long id);

    @EntityGraph(attributePaths = {"member", "orderItems"})
    List<Order> findByStatus(OrderStatus status);
}
```

서브그래프는 N뎁스 이상의 연관관계를 한 번에 페치할 때 쓴다. 다만 깊어질수록 카티전 곱이 폭발하므로 두 단계 이상은 별도 쿼리로 끊는 게 낫다.

`@EntityGraph`로 페치하면 Hibernate가 LEFT OUTER JOIN을 만든다. INNER JOIN이 필요하면 EntityGraph로는 표현이 안 되고 JPQL Fetch Join을 직접 써야 한다.

## 벌크 연산과 영속성 컨텍스트 비동기화

JPQL UPDATE/DELETE는 영속성 컨텍스트를 거치지 않고 DB에 직접 반영된다. 1차 캐시에 있는 엔티티와 DB 상태가 어긋난다는 뜻이다.

```java
@Modifying(clearAutomatically = true, flushAutomatically = true)
@Query("UPDATE Order o SET o.status = :status WHERE o.id IN :ids")
int bulkUpdateStatus(@Param("ids") List<Long> ids, @Param("status") OrderStatus status);
```

- `flushAutomatically = true`: 쿼리 실행 전에 영속성 컨텍스트 변경분을 flush한다. 안 하면 직전에 수정한 엔티티가 DB에 반영되지 않은 상태에서 벌크 UPDATE가 나가서 일관성이 깨진다.
- `clearAutomatically = true`: 쿼리 실행 후 영속성 컨텍스트를 비운다. 안 비우면 1차 캐시가 옛날 값을 들고 있어 같은 트랜잭션에서 조회 시 stale 데이터가 반환된다.

같은 트랜잭션에서 벌크 UPDATE 후 다시 엔티티를 조회·수정하는 코드는 종종 미묘한 버그를 만든다. 벌크 연산은 가능한 한 트랜잭션 끝부분에서 단발성으로 실행하고, 같은 트랜잭션에서 후속 작업이 필요하면 `entityManager.refresh()`로 명시적으로 다시 읽는다.

벌크 DELETE도 비슷한 문제가 있다. 자식 엔티티가 영속성 컨텍스트에 있는 상태에서 부모를 벌크 DELETE 하면, 자식 flush 시점에 무결성 위반이 난다.

## 영속성 컨텍스트 심화

### FlushMode

기본값은 `AUTO`다. 쿼리 실행 직전, 트랜잭션 커밋 직전에 자동 flush된다. 같은 트랜잭션에서 변경한 데이터가 후속 쿼리에 반영되도록 하는 안전장치다.

`COMMIT`으로 바꾸면 커밋 시점에만 flush한다. 대량 삽입 후 통계 쿼리를 여러 번 날리는 배치에서 매번 flush가 일어나면 성능이 떨어지는데, 이때만 한정적으로 쓴다. 단, 변경 사항이 후속 쿼리에 반영되지 않을 수 있어 위험하다.

### 1차 캐시 한계

영속성 컨텍스트는 트랜잭션 단위 1차 캐시다. 한 트랜잭션 안에서 같은 ID로 조회하면 DB에 다시 가지 않는다. 하지만 다음 한계가 있다.

- 트랜잭션을 벗어나면 사라진다. 분산 환경에서 캐시 역할을 기대할 수 없다.
- JPQL은 1차 캐시를 우회한다. ID 기반 `find()`만 1차 캐시를 본다. JPQL은 항상 DB로 쿼리를 날리고, 결과를 영속성 컨텍스트에 병합한다.
- 메모리에 모두 올라가므로 100만 건을 조회하면 OOM이 난다. 대용량 처리에서는 의도적으로 컨텍스트를 비워야 한다.

### clear/detach 사용 시점

```java
@Transactional
public void migrate() {
    int batchSize = 1000;
    for (int i = 0; i < totalCount; i += batchSize) {
        List<Order> orders = orderRepository.findBatch(i, batchSize);
        orders.forEach(this::convert);
        em.flush();
        em.clear();  // 1차 캐시 비움 → 다음 배치를 위한 메모리 확보
    }
}
```

배치 처리는 일정 단위로 flush + clear가 정석이다. clear를 빼먹으면 영속성 컨텍스트가 계속 커져 GC 압박이 심해지고 결국 OOM에 도달한다.

`detach(entity)`는 특정 엔티티만 컨텍스트에서 분리한다. 일부 엔티티만 변경 추적에서 제외하고 싶을 때 쓰지만, 실수로 detach된 엔티티를 변경하면 DB 반영이 안 된 채 사라진다는 함정이 있어 자주 쓰지 않는다.

## Hibernate Stateless Session과 대용량 처리

영속성 컨텍스트, dirty checking, 캐시, 캐스케이드 같은 모든 것이 부담이 되는 경우가 있다. 100만 건 일괄 처리, ETL 같은 작업은 stateless하게 흘려보내야 한다.

### StatelessSession

```java
@PersistenceContext
private EntityManager em;

public void importLargeFile() {
    Session session = em.unwrap(Session.class);
    StatelessSession stateless = session.getSessionFactory().openStatelessSession();
    Transaction tx = stateless.beginTransaction();
    try {
        for (Order order : largeOrderStream) {
            stateless.insert(order);
        }
        tx.commit();
    } finally {
        stateless.close();
    }
}
```

`StatelessSession`은 1차 캐시도, 변경 감지도, 캐스케이드도 없다. 그냥 SQL을 실행하는 수준에 가깝다. 속도는 빠르지만, JPA 라이프사이클 이벤트(`@PrePersist` 등)가 동작하지 않는 점에 유의한다.

### ScrollableResults / Stream

```java
@Transactional(readOnly = true)
public void process() {
    Session session = em.unwrap(Session.class);
    try (ScrollableResults<Order> scroll = session
            .createQuery("FROM Order o WHERE o.status = :s", Order.class)
            .setParameter("s", OrderStatus.PENDING)
            .setFetchSize(500)
            .scroll(ScrollMode.FORWARD_ONLY)) {

        int count = 0;
        while (scroll.next()) {
            Order o = scroll.get();
            handle(o);
            if (++count % 500 == 0) {
                em.flush();
                em.clear();
            }
        }
    }
}
```

MySQL JDBC 드라이버는 기본적으로 모든 결과를 메모리에 올린다. `useCursorFetch=true` 또는 `setFetchSize(Integer.MIN_VALUE)`를 설정해야 진짜 스트리밍이 된다. PostgreSQL은 autoCommit=false 상태에서만 fetchSize가 동작한다. 드라이버별 동작 차이가 커서 실제로 메모리 모니터링을 해야 안전하다.

Spring Data JPA의 `Stream<T>` 반환 타입은 내부적으로 ScrollableResults를 쓴다. try-with-resources로 닫는 것을 잊으면 커서가 누수된다.

```java
@QueryHints(value = @QueryHint(name = HINT_FETCH_SIZE, value = "500"))
@Query("SELECT o FROM Order o WHERE o.status = :status")
Stream<Order> streamByStatus(@Param("status") OrderStatus status);
```

## @DynamicUpdate / @DynamicInsert

기본 동작은 변경된 컬럼만 UPDATE에 포함하지 않는다. Hibernate는 모든 컬럼을 SET하는 UPDATE문을 미리 생성해두고 재사용한다. 컬럼 100개짜리 테이블에서 한 컬럼만 바꿔도 SET 절에 100개가 들어간다.

`@DynamicUpdate`를 붙이면 매번 dirty 컬럼만 SET하는 UPDATE를 동적으로 생성한다.

```java
@Entity
@DynamicUpdate
public class WideTable { ... }
```

장점은 명확하지만 트레이드오프가 있다.

- UPDATE문을 매번 생성·파싱하므로 prepared statement 캐시 효율이 떨어진다.
- 전체 컬럼 갱신이 잦은 엔티티에는 오히려 손해다.
- 컬럼이 많고, 한 번에 일부만 바뀌는 패턴(audit 테이블, 와이드 테이블)에서만 의미 있다.

`@DynamicInsert`도 비슷하다. NULL인 컬럼을 INSERT에서 제외해 DB 기본값(`DEFAULT CURRENT_TIMESTAMP` 등)이 적용되도록 한다. INSERT 시 명시적으로 `NULL`을 넣으면 컬럼 default가 무시되는 게 일반적인 SQL 동작이라, default 값에 의존하는 컬럼이 있을 때 필요하다.

## AttributeConverter

Java 타입과 DB 컬럼을 변환하는 표준 메커니즘이다. enum, VO, 암호화 컬럼 매핑에 자주 쓴다.

```java
@Converter
public class OrderStatusConverter implements AttributeConverter<OrderStatus, String> {
    @Override
    public String convertToDatabaseColumn(OrderStatus status) {
        return status == null ? null : status.getCode();
    }
    @Override
    public OrderStatus convertToEntityAttribute(String code) {
        return code == null ? null : OrderStatus.fromCode(code);
    }
}

@Entity
public class Order {
    @Convert(converter = OrderStatusConverter.class)
    private OrderStatus status;
}
```

`@Enumerated(EnumType.STRING)`은 enum 이름을 그대로 저장한다. enum 이름을 바꾸면 DB 데이터와 불일치가 나서 운영 중 변경이 어렵다. AttributeConverter로 코드 값(`"PD"`, `"CP"`)을 따로 두면 enum 리네이밍이 자유롭다.

암호화 컬럼도 같은 패턴이다.

```java
@Converter
@RequiredArgsConstructor
public class EncryptedStringConverter implements AttributeConverter<String, String> {
    private final AesEncryptor encryptor;

    @Override
    public String convertToDatabaseColumn(String plain) {
        return plain == null ? null : encryptor.encrypt(plain);
    }
    @Override
    public String convertToEntityAttribute(String cipher) {
        return cipher == null ? null : encryptor.decrypt(cipher);
    }
}
```

문제는 암호화 컬럼은 LIKE/EQUAL 검색이 안 된다는 점이다. EQUAL은 결정적 암호화(deterministic)일 때만 가능하고, LIKE는 원천적으로 불가능하다. 검색이 필요하면 별도 hash 컬럼을 두거나 Searchable Encryption을 도입해야 한다.

## Multi-DataSource 라우팅 (Read/Write 분리)

읽기 쿼리는 replica로, 쓰기 쿼리는 primary로 보내는 패턴이다. `AbstractRoutingDataSource`로 트랜잭션 readOnly 속성에 따라 라우팅한다.

```java
public class RoutingDataSource extends AbstractRoutingDataSource {
    @Override
    protected Object determineCurrentLookupKey() {
        return TransactionSynchronizationManager.isCurrentTransactionReadOnly()
            ? "replica" : "primary";
    }
}

@Configuration
public class DataSourceConfig {

    @Bean
    public DataSource routingDataSource(
        @Qualifier("primary") DataSource primary,
        @Qualifier("replica") DataSource replica
    ) {
        RoutingDataSource ds = new RoutingDataSource();
        Map<Object, Object> targets = new HashMap<>();
        targets.put("primary", primary);
        targets.put("replica", replica);
        ds.setTargetDataSources(targets);
        ds.setDefaultTargetDataSource(primary);
        return ds;
    }

    @Bean
    @Primary
    public DataSource dataSource(@Qualifier("routingDataSource") DataSource routing) {
        return new LazyConnectionDataSourceProxy(routing);
    }
}
```

`LazyConnectionDataSourceProxy`로 한 번 더 감싸는 게 핵심이다. 트랜잭션 시작 시점에는 readOnly 속성을 확인할 수 없는 타이밍 이슈가 있다. Lazy 프록시는 실제 쿼리가 실행될 때까지 커넥션 획득을 미루어 readOnly 플래그가 확정된 후에 라우팅이 일어나도록 한다.

주의할 점은 replica 지연(replication lag)이다. 쓰기 직후 readOnly 트랜잭션으로 같은 데이터를 읽으면 stale 데이터가 보일 수 있다. 사용자 본인이 막 작성한 데이터는 primary로 강제 라우팅하거나, "본인 데이터는 일정 시간 primary에서 읽기" 같은 정책이 필요하다.

## 2차 캐시

Hibernate 2차 캐시는 SessionFactory 단위 공유 캐시다. EhCache, Caffeine, Hazelcast, Redis(via Redisson) 등을 backend로 쓴다.

```java
@Entity
@Cache(usage = CacheConcurrencyStrategy.READ_WRITE)
public class Product {
    @Id private Long id;
    private String name;
    private BigDecimal price;
}
```

설정해야 할 것이 세 가지로 나뉜다.

- **엔티티 캐시**: ID 기반 조회만 캐시. `find()`만 캐시 hit. JPQL은 우회.
- **컬렉션 캐시**: `@OneToMany` 같은 컬렉션 자체를 캐시. 컬렉션 안의 엔티티는 별도로 엔티티 캐시 설정이 필요하다. 컬렉션 캐시만 켜고 엔티티 캐시를 안 켜면 ID만 캐시되고 매번 엔티티는 DB에서 다시 읽는다.
- **쿼리 캐시**: JPQL 결과(엔티티 ID 목록)를 캐시. 엔티티 캐시와 같이 켜야 의미 있다.

쿼리 캐시는 함정이 많아 운영에서는 보수적으로 쓴다. 같은 쿼리·같은 파라미터에만 hit하고, 캐시된 테이블이 한 번이라도 변경되면 invalid 처리된다. 변경이 잦은 테이블에 쿼리 캐시를 걸면 hit율이 0에 가까워지면서 캐시 무효화 비용만 추가된다.

분산 환경에서는 invalidation 전파가 정확해야 한다. 한 인스턴스에서 UPDATE한 결과가 다른 인스턴스 캐시에 즉시 반영되지 않으면 stale read가 난다. Redis나 Hazelcast 기반의 distributed cache가 이런 이유로 선택된다.

## LazyInitializationException과 OSIV

`LazyInitializationException`은 Lazy 연관관계를 영속성 컨텍스트가 닫힌 뒤에 접근할 때 난다. 가장 흔한 원인은 트랜잭션이 종료된 컨트롤러/뷰 계층에서 엔티티의 Lazy 프로퍼티를 건드리는 경우다.

Spring Boot 기본값은 OSIV(Open Session In View) `true`다. 영속성 컨텍스트를 HTTP 응답이 끝날 때까지 열어두어 컨트롤러/뷰에서도 Lazy 로딩이 동작한다. 개발은 편하지만 다음 문제가 있다.

- DB 커넥션 점유 시간이 응답 종료까지 길어진다. 외부 API 호출 같은 IO가 끼면 커넥션 풀이 빠르게 고갈된다.
- 비즈니스 로직과 무관한 N+1 쿼리가 뷰 렌더링 중에 터진다.

대규모 트래픽 서비스는 OSIV를 끈다.

```yaml
spring:
  jpa:
    open-in-view: false
```

OSIV off 환경에서는 다음 패턴이 필요하다.

- **DTO 변환을 트랜잭션 내부에서 끝낸다**: `@Transactional(readOnly = true)` 서비스 메서드 안에서 엔티티를 DTO로 매핑한 뒤 반환한다. 컨트롤러는 DTO만 받는다.
- **필요한 연관관계는 fetch join이나 EntityGraph로 미리 로드한다**: 서비스에서 명시적으로 가져온다.
- **양방향 연관관계 무한 루프 주의**: Jackson 직렬화 단계에서 Lazy 프로퍼티를 건드리면 예외가 난다. DTO 변환을 거치므로 자연스럽게 차단된다.

OSIV off는 한 번 적용하면 코드 전반에 영향이 크다. 신규 프로젝트는 처음부터 off로 시작하는 게 낫다.

## Fetch Join과 페이징

Fetch Join + 페이징을 같이 쓰면 Hibernate가 다음 경고를 띄운다.

```
HHH000104: firstResult/maxResults specified with collection fetch; applying in memory!
```

컬렉션 fetch join은 카티전 곱이 일어나기 때문에 LIMIT을 SQL에서 적용할 수 없다. Hibernate는 모든 row를 메모리에 올린 뒤 페이징한다. 데이터가 1만 건인데 메모리로 다 올라오면 사실상 페이징의 의미가 없다.

해결 방법은 두 가지다.

1. **부모를 먼저 페이징하고, 자식은 별도 쿼리로 fetch**: `@BatchSize(size = 100)` 또는 `hibernate.default_batch_fetch_size`를 설정한다. 부모 ID 100개씩 묶어 IN 쿼리로 자식을 가져온다.

```yaml
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 100
```

2. **ToOne 관계만 fetch join, ToMany는 batch fetch**: ToOne(@ManyToOne, @OneToOne)은 카티전 곱이 안 일어나므로 fetch join + 페이징이 정상 동작한다. ToMany만 batch로 분리한다.

### MultipleBagFetchException

서로 다른 컬렉션 두 개를 fetch join하면 발생한다.

```java
@Query("SELECT DISTINCT o FROM Order o " +
       "JOIN FETCH o.orderItems " +
       "JOIN FETCH o.payments")  // 두 번째 컬렉션 fetch join
List<Order> findWithItemsAndPayments();
```

```
org.hibernate.loader.MultipleBagFetchException: cannot simultaneously fetch multiple bags
```

`List`는 Hibernate에서 bag으로 취급되어 두 개를 동시에 fetch join할 수 없다. 카티전 곱이 두 번 일어나면 결과 row 수가 폭발한다.

해결책:

- 한쪽을 `Set`으로 바꾸면 일단 예외는 사라지지만 카티전 곱은 여전하다. row 수 폭발 가능성은 그대로다.
- 한쪽만 fetch join하고 나머지는 batch fetch로 가져온다. 일반적으로 이 방법을 쓴다.

## @DataJpaTest와 Testcontainers

`@DataJpaTest`는 JPA 관련 빈만 로드하는 슬라이스 테스트다. 기본적으로 H2 같은 임베디드 DB를 사용하고 트랜잭션을 자동 롤백한다.

문제는 H2와 운영 DB(MySQL, PostgreSQL)의 SQL 방언 차이다. native query, 함수, 락 동작이 다를 수 있어 H2에서 통과한 테스트가 운영에서 실패하는 경우가 자주 있다. Testcontainers로 실제 DB를 띄우는 게 정석이다.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class OrderRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("test")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired private OrderRepository orderRepository;

    @Test
    void findByOrderNumber_returnsOrder() {
        Order saved = orderRepository.save(Order.create("ORD-001"));
        Optional<Order> found = orderRepository.findByOrderNumber("ORD-001");
        assertThat(found).isPresent();
    }
}
```

`@AutoConfigureTestDatabase(replace = NONE)`이 핵심이다. 이걸 빼먹으면 `@DataJpaTest`가 임베디드 DB로 갈아치워서 Testcontainers가 무시된다.

컨테이너 부팅이 느려 테스트마다 띄우면 시간이 늘어난다. `@Container`를 static으로 두고 클래스 단위로 재사용하거나, `withReuse(true)`로 컨테이너를 재사용한다 (`testcontainers.properties`에 `testcontainers.reuse.enable=true` 필요).

## Hibernate 6.x 신규 기능

### @SQLRestriction

`@Where`가 deprecated되고 `@SQLRestriction`으로 대체됐다. 의미는 같다. 엔티티 조회 시 자동으로 WHERE 절에 추가되는 조건이다.

```java
@Entity
@SQLRestriction("deleted_at IS NULL")
public class Member {
    @Id private Long id;
    private LocalDateTime deletedAt;
}
```

soft-delete 패턴에 자주 쓴다. 다만 `findById()`처럼 ID 직접 조회에서도 적용되어, soft-delete된 row를 의도적으로 조회하려면 native query를 따로 만들어야 한다.

### JPA Criteria 개선

Hibernate 6는 자체 Criteria 확장(`HibernateCriteriaBuilder`)에 union, intersect, lateral join, JSON 함수 같은 기능을 추가했다. 표준 JPA Criteria로는 표현 못 하는 쿼리를 작성할 수 있다.

```java
HibernateCriteriaBuilder cb = (HibernateCriteriaBuilder) em.getCriteriaBuilder();
JpaCriteriaQuery<Member> query = cb.createQuery(Member.class);
JpaRoot<Member> root = query.from(Member.class);
query.where(cb.like(root.get("email"), cb.literal("%@example.com")));
```

QueryDSL을 못 쓰고 Criteria로 가야 하는 환경에서 유용하지만, 일반적으로는 QueryDSL 쪽이 훨씬 편하다.

## 마무리

Spring Data JPA 심화는 결국 Hibernate 동작을 깊이 이해하는 일이다. 영속성 컨텍스트의 라이프사이클, 1차/2차 캐시, fetch 전략, 락 동작이 머릿속에 정확히 그려져야 트러블슈팅이 가능하다. 운영 환경에서 마주치는 N+1, OOM, 데드락, stale read 대부분은 위 개념들의 조합으로 설명된다. 라이브러리 사용법보다 동작 원리를 먼저 익히는 게 결국 빠른 길이다.
