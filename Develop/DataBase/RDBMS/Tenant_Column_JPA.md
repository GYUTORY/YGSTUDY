---
title: 테넌트 컬럼 JPA
tags: [database, java, spring, rdbms]
updated: 2026-08-04
---

# 테넌트 컬럼 JPA

Spring Boot + JPA/Hibernate 환경에서 `tenant_id` 컬럼 기반 멀티테넌시를 구현할 때 세 가지 문제를 해결해야 한다. 첫째, 현재 요청이 어느 테넌트 소속인지 JPA 레이어까지 전달하는 것. 둘째, 모든 SELECT 쿼리에 `tenant_id` 조건이 자동으로 붙도록 보장하는 것. 셋째, 관리자 기능처럼 테넌트 경계를 넘어야 하는 경우를 안전하게 처리하는 것이다.

---

## 엔티티 설계

`tenant_id`를 모든 테넌트 데이터 엔티티에 강제하려면 슈퍼클래스로 묶는 게 낫다. 엔티티마다 직접 선언하면 누락이 생긴다.

```java
@MappedSuperclass
public abstract class TenantEntity {

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private String tenantId;

    @PrePersist
    protected void setTenantId() {
        if (this.tenantId == null) {
            this.tenantId = TenantContextHolder.get();
        }
    }
}

@Entity
@Table(name = "orders")
@FilterDef(
    name = "tenantFilter",
    parameters = @ParamDef(name = "tenantId", type = String.class)
)
@Filter(name = "tenantFilter", condition = "tenant_id = :tenantId")
public class Order extends TenantEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;
    private BigDecimal amount;
    private String status;

    @CreationTimestamp
    private LocalDateTime createdAt;
}
```

`updatable = false`를 빠뜨리면 JPA가 UPDATE 쿼리에 `SET tenant_id = ?`를 포함한다. 생성 후 테넌트가 바뀌는 경우는 없으므로 반드시 설정한다.

`@PrePersist`에서 `null` 체크를 하는 이유는 관리자가 데이터 이관 시 `tenant_id`를 명시적으로 설정하는 경우를 허용하기 위해서다. 무조건 덮어쓰면 이관 작업에서 의도한 테넌트와 다른 값이 들어간다.

---

## 테넌트 컨텍스트 전파

### ThreadLocal 홀더

요청 스레드에 테넌트를 보관하는 가장 단순한 방법이다. `RequestContextHolder`도 내부적으로 `ThreadLocal`을 사용하는데, 테넌트 전용 홀더를 별도로 두면 `HttpServletRequest`에 의존하지 않아도 된다.

```java
public class TenantContextHolder {

    private static final ThreadLocal<String> TENANT_ID = new ThreadLocal<>();

    public static void set(String tenantId) {
        TENANT_ID.set(tenantId);
    }

    public static String get() {
        String tenantId = TENANT_ID.get();
        if (tenantId == null) {
            throw new IllegalStateException("Tenant context not set");
        }
        return tenantId;
    }

    public static void clear() {
        TENANT_ID.remove();
    }
}
```

`remove()`를 호출하지 않으면 Tomcat 스레드 풀에서 이전 요청의 테넌트 ID가 다음 요청에 남는다. 필터에서 반드시 `finally` 블록에서 `clear()`를 호출해야 한다.

### 서블릿 필터에서 설정

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TenantFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain)
            throws ServletException, IOException {

        try {
            String tenantId = extractTenantId(request);
            TenantContextHolder.set(tenantId);
            // RequestContextHolder를 직접 쓰는 코드와 호환하려면 request attribute에도 설정
            request.setAttribute("tenantId", tenantId);
            chain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear();
        }
    }

    private String extractTenantId(HttpServletRequest request) {
        String tenantId = request.getHeader("X-Tenant-ID");
        if (tenantId == null || tenantId.isBlank()) {
            throw new TenantResolutionException("Tenant ID not found in request");
        }
        return tenantId;
    }
}
```

`RequestContextHolder.getRequestAttributes()`를 통해 `request.getAttribute("tenantId")`를 읽는 방식도 동작한다. 다만 이 방식은 request 스코프 밖(스케줄러, 비동기 작업)에서 사용할 수 없다. `TenantContextHolder`는 `TaskDecorator`로 전파가 가능하므로 비동기 처리에서 더 유연하다.

---

## Spring Security 연동

### JWT에서 테넌트 추출

JWT에 `tenant_id` 클레임을 포함시키고, 인증 필터에서 `SecurityContext` 설정과 함께 처리하면 인증과 테넌트 식별이 한 번에 된다.

```java
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private JwtTokenProvider tokenProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain)
            throws ServletException, IOException {

        try {
            String token = extractToken(request);
            if (token != null && tokenProvider.isValid(token)) {
                Claims claims = tokenProvider.parse(token);

                String tenantId = claims.get("tenant_id", String.class);
                TenantContextHolder.set(tenantId);

                Authentication auth = buildAuthentication(claims, tenantId);
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
            chain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear();
            SecurityContextHolder.clearContext();
        }
    }

    private String extractToken(HttpServletRequest request) {
        String bearer = request.getHeader("Authorization");
        if (bearer != null && bearer.startsWith("Bearer ")) {
            return bearer.substring(7);
        }
        return null;
    }
}
```

`SecurityContextHolder.clearContext()`와 `TenantContextHolder.clear()` 모두 `finally`에서 처리한다. 하나만 빠져도 스레드 풀에서 이전 요청의 상태가 남는다.

### Authentication 객체에 테넌트 포함

`SecurityContextHolder`에서 테넌트를 꺼낼 수 있으면 `TenantContextHolder`를 직접 조회하지 않아도 된다.

```java
public class TenantAuthentication extends UsernamePasswordAuthenticationToken {

    private final String tenantId;

    public TenantAuthentication(Object principal,
                                 Collection<? extends GrantedAuthority> authorities,
                                 String tenantId) {
        super(principal, null, authorities);
        this.tenantId = tenantId;
    }

    public String getTenantId() {
        return tenantId;
    }
}
```

`@Async`나 `CompletableFuture`에서 `SecurityContextHolder`를 `MODE_INHERITABLETHREADLOCAL`로 설정하면 자식 스레드에서도 `Authentication`을 통해 테넌트를 읽을 수 있다. 다만 이 설정은 스레드 풀 환경에서 주의가 필요하다.

### Spring Security 설정에서 테넌트 필터 순서

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http,
                                            JwtAuthenticationFilter jwtFilter) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .build();
    }
}
```

`JwtAuthenticationFilter`에서 테넌트 컨텍스트를 설정하므로 별도의 `TenantFilter`는 필요 없다. 둘 다 있으면 순서에 따라 덮어쓰는 문제가 생긴다. 하나로 합치거나 명확한 실행 순서를 지정한다.

---

## CurrentTenantIdentifierResolver

Hibernate의 멀티테넌시 기능에서 현재 테넌트를 알려주는 인터페이스다. `DISCRIMINATOR` 방식을 쓸 때 Hibernate가 내부적으로 호출한다.

```java
@Component
public class TenantIdentifierResolver implements CurrentTenantIdentifierResolver<String> {

    @Override
    public String resolveCurrentTenantIdentifier() {
        try {
            return TenantContextHolder.get();
        } catch (IllegalStateException e) {
            // 스케줄러나 이벤트 리스너처럼 요청 컨텍스트가 없는 상황
            return "SYSTEM";
        }
    }

    @Override
    public boolean validateExistingCurrentSessions() {
        return true;
    }
}
```

`validateExistingCurrentSessions()`를 `true`로 두면 기존 Hibernate 세션의 테넌트 식별자가 현재 컨텍스트와 다를 때 새 세션을 연다. `false`로 두면 세션을 재사용하다가 다른 테넌트 데이터가 섞일 수 있다.

Hibernate 설정에 `CurrentTenantIdentifierResolver`를 연결한다.

```java
@Configuration
public class HibernateConfig {

    @Bean
    public LocalContainerEntityManagerFactoryBean entityManagerFactory(
            DataSource dataSource,
            TenantIdentifierResolver tenantIdentifierResolver) {

        LocalContainerEntityManagerFactoryBean em = new LocalContainerEntityManagerFactoryBean();
        em.setDataSource(dataSource);
        em.setPackagesToScan("com.example.domain");
        em.setJpaVendorAdapter(new HibernateJpaVendorAdapter());

        Properties props = new Properties();
        props.setProperty("hibernate.multiTenancy", "DISCRIMINATOR");
        em.setJpaProperties(props);

        Map<String, Object> vendorProps = new HashMap<>();
        vendorProps.put("hibernate.tenant_identifier_resolver", tenantIdentifierResolver);
        em.setJpaPropertyMap(vendorProps);

        return em;
    }
}
```

Hibernate 6 이전 버전에서는 `DISCRIMINATOR` 방식이 없었다. 그 경우 `CurrentTenantIdentifierResolver`는 `SCHEMA` 방식(schema-per-tenant)에서 주로 쓰였고, 컬럼 기반 격리는 `@Filter`로 직접 구현해야 했다.

---

## @Filter/@FilterDef로 자동 필터링

`@Filter`는 SELECT에만 적용된다. INSERT 시 `tenant_id` 자동 설정은 `@PrePersist`나 `@EntityListeners`로 별도 처리해야 한다. 이 두 기능의 역할을 혼동해서 `@Filter`만 달아놓고 INSERT 때 `tenant_id`가 NULL로 들어가는 문제가 실제로 자주 생긴다.

### 필터 활성화

`@FilterDef`와 `@Filter`를 엔티티에 선언해도 자동으로 동작하지 않는다. 각 Hibernate 세션에서 명시적으로 활성화해야 한다.

```java
@Aspect
@Component
public class TenantFilterAspect {

    @PersistenceContext
    private EntityManager entityManager;

    @Around("execution(* com.example.repository..*(..))")
    public Object applyTenantFilter(ProceedingJoinPoint pjp) throws Throwable {
        Session session = entityManager.unwrap(Session.class);
        session.enableFilter("tenantFilter")
               .setParameter("tenantId", TenantContextHolder.get());

        try {
            return pjp.proceed();
        } finally {
            session.disableFilter("tenantFilter");
        }
    }
}
```

`disableFilter`를 `finally`에서 처리하지 않으면 같은 세션에서 다음 쿼리에도 필터가 적용된 채로 남는다. 특히 Spring의 Open Session in View 패턴이 활성화된 경우 세션이 요청 전체에서 공유되므로 누적 효과가 생길 수 있다.

트랜잭션 시작 시점에 `@TransactionalEventListener`나 `AbstractRoutingDataSource`에서 필터를 활성화하는 방식도 있다. AOP보다 시점 제어가 명확하지만 설정이 복잡하다.

### 연관 엔티티 로딩 시 동작

`@Filter`는 연관 엔티티 로딩 시에도 적용된다. `Order`에서 `@OneToMany`로 연결된 `OrderItem`을 로딩할 때도 `tenant_id` 조건이 붙는다. 문제는 `@Filter`와 EAGER 로딩을 함께 쓸 때 Hibernate가 생성하는 JOIN 쿼리가 예상과 다를 수 있다는 것이다. 연관 관계는 LAZY로 두고 필요한 경우에만 fetch join을 쓴다.

```java
// fetch join에서 tenantFilter가 WHERE에 포함되는지 확인한다
// JPQL 예시
String jpql = "SELECT o FROM Order o JOIN FETCH o.items WHERE o.status = :status";
```

fetch join 쿼리에서 `@Filter`가 WHERE 절에 포함되는지는 Hibernate 버전과 설정에 따라 다르다. SQL 로그를 직접 확인해서 `tenant_id` 조건이 붙는지 검증한다.

---

## QueryDSL 테넌트 조건 처리

QueryDSL에서 `@Filter`가 동작하는지는 쿼리 타입에 따라 다르다. JPQL 기반 QueryDSL(`JPAQuery`)은 Hibernate가 처리하므로 필터가 적용된다. Native 쿼리는 적용되지 않는다. 어떤 경우든 `WHERE tenant_id = ?` 조건을 직접 추가하는 게 동작을 보장하는 유일한 방법이다.

### Repository에서 조건 관리

```java
@Repository
@RequiredArgsConstructor
public class OrderQueryRepository {

    private final JPAQueryFactory queryFactory;
    private final QOrder order = QOrder.order;

    private BooleanExpression tenantCondition() {
        return order.tenantId.eq(TenantContextHolder.get());
    }

    public List<Order> findByStatus(String status) {
        return queryFactory
            .selectFrom(order)
            .where(tenantCondition(), order.status.eq(status))
            .orderBy(order.createdAt.desc())
            .fetch();
    }

    public long countByUserId(Long userId) {
        return queryFactory
            .select(order.count())
            .from(order)
            .where(tenantCondition(), order.userId.eq(userId))
            .fetchOne();
    }
}
```

`tenantCondition()`을 private 메서드로 분리하면 WHERE 절마다 하드코딩하는 것보다 누락 가능성이 줄어든다. 누락 자체를 방지하지는 않으므로 코드 리뷰에서 `QueryDSL` 쿼리에 `tenantCondition()` 호출이 있는지 확인하는 컨벤션이 함께 있어야 한다.

### Projections에서 주의사항

`Projections.constructor`나 `Projections.fields`를 쓰는 DTO 프로젝션은 JPA 엔티티가 아니다. Hibernate `@Filter`가 동작하지 않는다. `tenantCondition()`을 WHERE에 반드시 넣어야 한다.

```java
public List<OrderSummaryDto> findOrderSummaries(String status) {
    return queryFactory
        .select(Projections.constructor(OrderSummaryDto.class,
            order.id,
            order.amount,
            order.status,
            order.createdAt
        ))
        .from(order)
        .where(
            tenantCondition(),  // Projections 사용 시에도 반드시 포함
            order.status.eq(status)
        )
        .orderBy(order.createdAt.desc())
        .fetch();
}
```

`Projections`를 쓰는 쿼리에서 `tenantCondition()`이 빠진 채로 서비스가 운영된 경우가 있었다. `@Filter`가 붙어 있어서 일반 엔티티 조회에서는 동작했고 DTO 쿼리만 전체 테넌트 데이터를 반환하고 있었다. SQL 로그를 주기적으로 샘플링해서 확인하는 게 필요하다.

### 복합 조건 처리

동적 쿼리에서 `where` 인자에 `null`을 넣으면 QueryDSL이 해당 조건을 무시한다. `tenantCondition()`이 절대 `null`을 반환하지 않도록 해야 한다. `TenantContextHolder.get()`이 예외를 던지도록 구현했다면 null 반환 걱정은 없다.

```java
public List<Order> search(String status, Long userId) {
    return queryFactory
        .selectFrom(order)
        .where(
            tenantCondition(),
            status != null ? order.status.eq(status) : null,
            userId != null ? order.userId.eq(userId) : null
        )
        .fetch();
}
```

`tenantCondition()`은 항상 첫 번째 인자로 두는 컨벤션을 유지하면 코드 리뷰에서 누락을 쉽게 잡을 수 있다.

---

## 관리자 쿼리 예외 처리

### 관리자용 Repository 분리

테넌트 필터 없이 전체 데이터를 다루는 관리자 기능은 타입을 분리한다. 같은 Repository에 관리자용 메서드를 섞으면 의도치 않게 일반 사용자 코드에서 호출될 수 있다.

```java
@Repository
@RequiredArgsConstructor
public class AdminOrderRepository {

    private final JPAQueryFactory queryFactory;
    private final QOrder order = QOrder.order;

    public List<TenantOrderSummary> findAllTenantsSummary(LocalDate from, LocalDate to) {
        return queryFactory
            .select(Projections.constructor(TenantOrderSummary.class,
                order.tenantId,
                order.count(),
                order.amount.sum()
            ))
            .from(order)
            .where(order.createdAt.between(
                from.atStartOfDay(),
                to.plusDays(1).atStartOfDay()
            ))
            .groupBy(order.tenantId)
            .fetch();
    }

    public Page<Order> findAllByTenant(String tenantId, Pageable pageable) {
        List<Order> content = queryFactory
            .selectFrom(order)
            .where(order.tenantId.eq(tenantId))
            .offset(pageable.getOffset())
            .limit(pageable.getPageSize())
            .orderBy(order.createdAt.desc())
            .fetch();

        Long total = queryFactory
            .select(order.count())
            .from(order)
            .where(order.tenantId.eq(tenantId))
            .fetchOne();

        return new PageImpl<>(content, pageable, total != null ? total : 0L);
    }
}
```

### 서비스 레이어에서 권한 제어

```java
@Service
@RequiredArgsConstructor
public class AdminOrderService {

    private final AdminOrderRepository adminOrderRepository;
    private final TenantRepository tenantRepository;

    @PreAuthorize("hasRole('ADMIN')")
    public List<TenantOrderSummary> getTenantSummaries(LocalDate from, LocalDate to) {
        return adminOrderRepository.findAllTenantsSummary(from, to);
    }

    @PreAuthorize("hasRole('ADMIN')")
    public Page<Order> getOrdersByTenant(String tenantId, Pageable pageable) {
        // 존재하는 테넌트인지 검증하지 않으면 임의의 tenantId로 조회 가능
        tenantRepository.findById(tenantId)
            .orElseThrow(() -> new TenantNotFoundException(tenantId));

        return adminOrderRepository.findAllByTenant(tenantId, pageable);
    }
}
```

`@PreAuthorize`를 컨트롤러가 아닌 서비스 레이어에 붙이는 이유는 이벤트 리스너나 스케줄러에서 서비스를 직접 호출하는 경우에도 권한 검사가 적용되게 하기 위해서다.

### 특정 테넌트로 컨텍스트 강제 설정

관리자가 특정 테넌트의 데이터를 일반 Repository 메서드를 통해 처리해야 할 때, `TenantContextHolder`에 직접 테넌트를 설정하는 방식을 쓴다.

```java
@PreAuthorize("hasRole('ADMIN')")
public List<Order> processOrdersForTenant(String tenantId, String status) {
    tenantRepository.findById(tenantId)
        .orElseThrow(() -> new TenantNotFoundException(tenantId));

    TenantContextHolder.set(tenantId);
    try {
        return orderQueryRepository.findByStatus(status);
    } finally {
        TenantContextHolder.clear();
    }
}
```

`finally`에서 `clear()`를 반드시 호출한다. 이 메서드 호출 후 같은 스레드에서 다른 테넌트 컨텍스트가 설정되어야 하는 요청이 처리될 경우, `clear()` 없이 이전 테넌트 ID가 남아있으면 다른 테넌트 데이터가 노출된다.

---

## 비동기 처리에서 컨텍스트 전파

`@Async`를 쓰면 `ThreadLocal`이 자식 스레드로 전파되지 않는다. `TenantContextHolder.get()`을 비동기 메서드에서 호출하면 `IllegalStateException`이 발생한다.

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(20);
        executor.setQueueCapacity(100);
        executor.setTaskDecorator(new TenantAwareTaskDecorator());
        executor.initialize();
        return executor;
    }
}

public class TenantAwareTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        String tenantId;
        try {
            tenantId = TenantContextHolder.get();
        } catch (IllegalStateException e) {
            // 요청 컨텍스트가 없는 경우 (스케줄러 등)
            return runnable;
        }

        return () -> {
            TenantContextHolder.set(tenantId);
            try {
                runnable.run();
            } finally {
                TenantContextHolder.clear();
            }
        };
    }
}
```

`TaskDecorator`는 부모 스레드에서 실행되어 `tenantId`를 캡처하고, `Runnable` 내부에서 자식 스레드에 설정한다. `SecurityContextHolder`도 같은 문제가 있다. `DelegatingSecurityContextTaskDecorator`를 함께 쓰려면 두 Decorator를 체이닝해야 한다.

```java
executor.setTaskDecorator(runnable -> {
    String tenantId;
    try {
        tenantId = TenantContextHolder.get();
    } catch (IllegalStateException e) {
        tenantId = null;
    }

    SecurityContext securityContext = SecurityContextHolder.getContext();
    String finalTenantId = tenantId;

    return () -> {
        SecurityContextHolder.setContext(securityContext);
        if (finalTenantId != null) {
            TenantContextHolder.set(finalTenantId);
        }
        try {
            runnable.run();
        } finally {
            TenantContextHolder.clear();
            SecurityContextHolder.clearContext();
        }
    };
});
```

`CompletableFuture.supplyAsync()`는 `TaskDecorator`가 적용된 Executor를 명시적으로 전달해야 한다. 기본 `ForkJoinPool`을 쓰면 컨텍스트가 전파되지 않는다.

---

## 관련 문서

- Shared_Table.md — 공유 테이블 DB 설계 (인덱스, 파티셔닝, RLS)
- Schema_Per_Tenant.md — 스키마 분리 방식 구현
- Cross_Schema.md — 세 가지 멀티테넌시 패턴 비교
