---
title: "RBAC/ABAC 권한 모델 설계와 구현"
tags: [RBAC, ABAC, 권한, 인가, Spring Security, 접근제어]
updated: 2026-03-26
---

# RBAC/ABAC 권한 모델 설계와 구현

## RBAC (Role-Based Access Control)

사용자에게 역할(Role)을 부여하고, 역할에 권한(Permission)을 매핑하는 방식이다. 대부분의 서비스에서 기본 인가 모델로 사용한다.

핵심 개념은 세 가지다:

- **User**: 실제 사용자
- **Role**: 사용자에게 부여되는 역할 (ADMIN, MANAGER, USER 등)
- **Permission**: 역할이 수행할 수 있는 구체적인 행위 (READ_USER, WRITE_ORDER 등)

사용자가 직접 권한을 갖는 게 아니라, 역할을 통해 간접적으로 권한을 갖는다. 사용자가 수백 명이어도 역할은 몇 개로 관리할 수 있다.

---

## RBAC DB 스키마 설계

```sql
-- 사용자
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 역할
CREATE TABLE roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,  -- ROLE_ADMIN, ROLE_MANAGER
    description VARCHAR(200)
);

-- 권한
CREATE TABLE permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,  -- USER_READ, ORDER_WRITE
    description VARCHAR(200)
);

-- 사용자-역할 매핑 (N:M)
CREATE TABLE user_roles (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- 역할-권한 매핑 (N:M)
CREATE TABLE role_permissions (
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (permission_id) REFERENCES permissions(id)
);
```

테이블이 5개다. `user_roles`와 `role_permissions` 두 개의 매핑 테이블이 핵심이다.

한 가지 주의할 점은 역할 이름에 `ROLE_` 접두사를 붙이는 것이다. Spring Security에서 `hasRole("ADMIN")`을 쓰면 내부적으로 `ROLE_ADMIN`을 찾는다. DB에 `ADMIN`으로 저장하면 `hasRole()`이 동작하지 않아서 삽질하는 경우가 많다. `hasAuthority()`를 쓰면 접두사 없이 동작하지만, 팀 내 컨벤션을 통일하는 게 낫다.

### 역할 계층 구조가 필요한 경우

ADMIN이 MANAGER의 권한을 포함하고, MANAGER가 USER의 권한을 포함하는 구조라면 별도 테이블을 추가한다:

```sql
CREATE TABLE role_hierarchy (
    parent_role_id BIGINT NOT NULL,
    child_role_id BIGINT NOT NULL,
    PRIMARY KEY (parent_role_id, child_role_id),
    FOREIGN KEY (parent_role_id) REFERENCES roles(id),
    FOREIGN KEY (child_role_id) REFERENCES roles(id)
);
```

Spring Security에서는 `RoleHierarchy` 빈으로 설정할 수 있다:

```java
@Bean
public RoleHierarchy roleHierarchy() {
    return RoleHierarchyImpl.fromHierarchy(
        "ROLE_ADMIN > ROLE_MANAGER\nROLE_MANAGER > ROLE_USER"
    );
}
```

이렇게 하면 ADMIN으로 로그인한 사용자는 MANAGER, USER 권한을 모두 갖는다. `role_permissions` 테이블에 ADMIN에게 모든 권한을 일일이 매핑하지 않아도 된다.

---

## Spring Security에서 역할-권한 매핑 구현

### Entity 설계

```java
@Entity
@Table(name = "users")
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String username;
    private String password;
    private boolean enabled;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
        name = "user_roles",
        joinColumns = @JoinColumn(name = "user_id"),
        inverseJoinColumns = @JoinColumn(name = "role_id")
    )
    private Set<Role> roles = new HashSet<>();
}

@Entity
@Table(name = "roles")
public class Role {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
        name = "role_permissions",
        joinColumns = @JoinColumn(name = "role_id"),
        inverseJoinColumns = @JoinColumn(name = "permission_id")
    )
    private Set<Permission> permissions = new HashSet<>();
}

@Entity
@Table(name = "permissions")
public class Permission {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
```

`FetchType.LAZY`로 설정한다. EAGER로 하면 사용자를 조회할 때마다 역할과 권한까지 전부 JOIN해서 가져온다. 인증 시점에만 필요한 데이터를 매 조회마다 끌어오면 성능 문제가 생긴다.

### UserDetailsService 구현

```java
@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {

    private final UserRepository userRepository;

    @Override
    @Transactional(readOnly = true)
    public UserDetails loadUserByUsername(String username) {
        User user = userRepository.findByUsername(username)
            .orElseThrow(() -> new UsernameNotFoundException("사용자 없음: " + username));

        return new org.springframework.security.core.userdetails.User(
            user.getUsername(),
            user.getPassword(),
            user.isEnabled(),
            true, true, true,
            getAuthorities(user)
        );
    }

    private Collection<? extends GrantedAuthority> getAuthorities(User user) {
        Set<GrantedAuthority> authorities = new HashSet<>();

        for (Role role : user.getRoles()) {
            // 역할 자체를 authority로 추가
            authorities.add(new SimpleGrantedAuthority(role.getName()));

            // 역할에 매핑된 권한도 authority로 추가
            for (Permission permission : role.getPermissions()) {
                authorities.add(new SimpleGrantedAuthority(permission.getName()));
            }
        }
        return authorities;
    }
}
```

`@Transactional(readOnly = true)`이 없으면 `LazyInitializationException`이 발생한다. `roles`와 `permissions`가 LAZY로 설정되어 있어서, 트랜잭션 밖에서 접근하면 프록시가 초기화되지 않는다.

### SecurityConfig에서 사용

```java
@Configuration
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/users/**").hasAuthority("USER_READ")
                .requestMatchers("/api/orders/**").hasAnyAuthority("ORDER_READ", "ORDER_WRITE")
                .anyRequest().authenticated()
            );
        return http.build();
    }
}
```

메서드 레벨에서 세밀하게 제어할 수도 있다:

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @GetMapping
    @PreAuthorize("hasAuthority('ORDER_READ')")
    public List<Order> getOrders() { ... }

    @PostMapping
    @PreAuthorize("hasAuthority('ORDER_WRITE')")
    public Order createOrder(@RequestBody OrderRequest request) { ... }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void deleteOrder(@PathVariable Long id) { ... }
}
```

---

## 동적 권한 관리 — DB 변경이 즉시 반영되지 않는 문제

실무에서 자주 마주치는 문제다. 관리자가 어떤 역할의 권한을 DB에서 변경했는데, 이미 로그인한 사용자에게 변경 사항이 반영되지 않는다.

### 왜 이런 일이 생기나

Spring Security는 인증 시점에 `UserDetailsService.loadUserByUsername()`을 호출해서 권한 정보를 `SecurityContext`에 저장한다. 이후 요청에서는 SecurityContext에 캐싱된 권한을 사용한다. DB가 바뀌어도 SecurityContext는 그대로다.

JWT를 쓰는 경우 더 심하다. 토큰 안에 권한 정보가 들어가 있으면, 토큰이 만료될 때까지 이전 권한이 유지된다.

### 해결 방법 1: 매 요청마다 권한 재조회

```java
@Component
@RequiredArgsConstructor
public class DynamicAuthorizationFilter extends OncePerRequestFilter {

    private final UserRepository userRepository;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated()) {
            // DB에서 최신 권한 조회
            User user = userRepository.findByUsername(auth.getName()).orElse(null);
            if (user != null) {
                Collection<GrantedAuthority> freshAuthorities = loadAuthorities(user);

                // Authentication 객체 교체
                Authentication newAuth = new UsernamePasswordAuthenticationToken(
                    auth.getPrincipal(), auth.getCredentials(), freshAuthorities
                );
                SecurityContextHolder.getContext().setAuthentication(newAuth);
            }
        }
        filterChain.doFilter(request, response);
    }
}
```

매 요청마다 DB를 조회하므로 부하가 크다. 사용자 수가 많은 서비스에서는 쓰면 안 된다.

### 해결 방법 2: 캐시 + 이벤트 기반 갱신 (실무에서 많이 씀)

```java
@Service
@RequiredArgsConstructor
public class PermissionCacheService {

    private final UserRepository userRepository;
    private final Cache<String, Collection<GrantedAuthority>> permissionCache;

    public PermissionCacheService(UserRepository userRepository) {
        this.userRepository = userRepository;
        this.permissionCache = Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(5))
            .build();
    }

    public Collection<GrantedAuthority> getAuthorities(String username) {
        return permissionCache.get(username, this::loadFromDb);
    }

    private Collection<GrantedAuthority> loadFromDb(String username) {
        User user = userRepository.findByUsername(username).orElseThrow();
        Set<GrantedAuthority> authorities = new HashSet<>();
        for (Role role : user.getRoles()) {
            authorities.add(new SimpleGrantedAuthority(role.getName()));
            for (Permission perm : role.getPermissions()) {
                authorities.add(new SimpleGrantedAuthority(perm.getName()));
            }
        }
        return authorities;
    }

    // 권한 변경 시 호출
    public void evictUser(String username) {
        permissionCache.invalidate(username);
    }

    // 역할의 권한이 변경되면 해당 역할을 가진 모든 사용자의 캐시를 날린다
    public void evictByRole(String roleName) {
        List<String> usernames = userRepository.findUsernamesByRoleName(roleName);
        usernames.forEach(permissionCache::invalidate);
    }
}
```

관리자 API에서 권한을 변경할 때 `evictByRole()`을 호출한다:

```java
@RestController
@RequestMapping("/admin/roles")
@PreAuthorize("hasRole('ADMIN')")
@RequiredArgsConstructor
public class RoleManagementController {

    private final RoleService roleService;
    private final PermissionCacheService permissionCacheService;

    @PutMapping("/{roleId}/permissions")
    public void updatePermissions(@PathVariable Long roleId,
                                  @RequestBody List<Long> permissionIds) {
        Role role = roleService.updatePermissions(roleId, permissionIds);
        permissionCacheService.evictByRole(role.getName());
    }
}
```

캐시 TTL을 5분으로 설정했으므로, 이벤트가 누락되더라도 최대 5분 뒤에는 반영된다. 완전한 실시간은 아니지만 대부분의 서비스에서 충분하다.

### 해결 방법 3: JWT + 짧은 만료 시간 + 블랙리스트

JWT를 쓴다면 토큰에 권한을 넣지 않는 방법도 있다. 토큰에는 사용자 식별 정보만 넣고, 권한은 매번 서버에서 조회한다:

```java
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {
        String token = extractToken(request);
        if (token != null && jwtProvider.validate(token)) {
            String username = jwtProvider.getUsername(token);

            // 토큰에서 권한을 꺼내지 않고, 캐시에서 조회
            Collection<GrantedAuthority> authorities =
                permissionCacheService.getAuthorities(username);

            Authentication auth = new UsernamePasswordAuthenticationToken(
                username, null, authorities
            );
            SecurityContextHolder.getContext().setAuthentication(auth);
        }
        filterChain.doFilter(request, response);
    }
}
```

토큰에 권한을 넣으면 토큰 크기가 커지는 문제도 해결된다. 권한이 20개만 되어도 JWT 크기가 상당히 커진다.

---

## ABAC (Attribute-Based Access Control)

RBAC은 "이 사용자가 어떤 역할인가"로 판단한다. ABAC은 여기에 더해 사용자 속성, 리소스 속성, 환경 속성을 조합해서 판단한다.

예를 들어 "부서가 '영업팀'이고 문서의 보안등급이 '일반'이면 읽기 허용"은 RBAC으로 표현하기 어렵다. 이런 조건을 처리하려면 ABAC이 필요하다.

### ABAC 정책 구성 요소

| 구성 요소 | 설명 | 예시 |
|-----------|------|------|
| Subject | 요청 주체의 속성 | 부서, 직급, 소속 팀 |
| Resource | 대상 리소스의 속성 | 문서 보안등급, 소유자, 생성일 |
| Action | 수행하려는 행위 | READ, WRITE, DELETE |
| Environment | 요청 환경 | 시간, IP 대역, 접속 위치 |

### 정책 정의

```java
public class Policy {
    private String name;
    private String description;
    private PolicyEffect effect;        // PERMIT, DENY
    private SubjectCondition subject;
    private ResourceCondition resource;
    private ActionCondition action;
    private EnvironmentCondition environment;
}

public enum PolicyEffect {
    PERMIT, DENY
}

@Data
public class SubjectCondition {
    private String department;       // null이면 조건 무시
    private String position;
    private Integer minLevel;
}

@Data
public class ResourceCondition {
    private String securityLevel;
    private String ownerDepartment;
    private String resourceType;
}

@Data
public class ActionCondition {
    private Set<String> allowedActions;
}

@Data
public class EnvironmentCondition {
    private LocalTime accessTimeFrom;
    private LocalTime accessTimeTo;
    private Set<String> allowedIpRanges;
}
```

### 정책 평가 엔진

```java
@Service
@RequiredArgsConstructor
public class PolicyEvaluator {

    private final PolicyRepository policyRepository;

    public boolean evaluate(AccessRequest request) {
        List<Policy> policies = policyRepository.findActivePolicies();

        // 기본 거부 (Deny by default)
        boolean permitted = false;

        for (Policy policy : policies) {
            if (!matches(policy, request)) {
                continue;
            }

            // DENY가 하나라도 매칭되면 즉시 거부
            if (policy.getEffect() == PolicyEffect.DENY) {
                return false;
            }

            if (policy.getEffect() == PolicyEffect.PERMIT) {
                permitted = true;
            }
        }

        return permitted;
    }

    private boolean matches(Policy policy, AccessRequest request) {
        return matchesSubject(policy.getSubject(), request)
            && matchesResource(policy.getResource(), request)
            && matchesAction(policy.getAction(), request)
            && matchesEnvironment(policy.getEnvironment(), request);
    }

    private boolean matchesSubject(SubjectCondition condition, AccessRequest request) {
        if (condition == null) return true;

        if (condition.getDepartment() != null
            && !condition.getDepartment().equals(request.getUserDepartment())) {
            return false;
        }
        if (condition.getMinLevel() != null
            && request.getUserLevel() < condition.getMinLevel()) {
            return false;
        }
        return true;
    }

    private boolean matchesResource(ResourceCondition condition, AccessRequest request) {
        if (condition == null) return true;

        if (condition.getSecurityLevel() != null
            && !condition.getSecurityLevel().equals(request.getResourceSecurityLevel())) {
            return false;
        }
        if (condition.getOwnerDepartment() != null
            && !condition.getOwnerDepartment().equals(request.getResourceOwnerDepartment())) {
            return false;
        }
        return true;
    }

    private boolean matchesAction(ActionCondition condition, AccessRequest request) {
        if (condition == null) return true;
        return condition.getAllowedActions().contains(request.getAction());
    }

    private boolean matchesEnvironment(EnvironmentCondition condition, AccessRequest request) {
        if (condition == null) return true;

        LocalTime now = LocalTime.now();
        if (condition.getAccessTimeFrom() != null && now.isBefore(condition.getAccessTimeFrom())) {
            return false;
        }
        if (condition.getAccessTimeTo() != null && now.isAfter(condition.getAccessTimeTo())) {
            return false;
        }
        return true;
    }
}
```

DENY 우선 방식을 쓴다. PERMIT과 DENY가 동시에 매칭되면 DENY가 이긴다. 보안 정책에서는 거부가 허용보다 우선해야 한다.

### Spring Security와 연동

`@PreAuthorize`에서 커스텀 빈을 호출하는 방식으로 연동한다:

```java
@Component("abac")
@RequiredArgsConstructor
public class AbacPermissionEvaluator {

    private final PolicyEvaluator policyEvaluator;

    public boolean check(Authentication auth, String resourceType,
                         String resourceId, String action) {
        AccessRequest request = AccessRequest.builder()
            .username(auth.getName())
            .userDepartment(getUserDepartment(auth))
            .userLevel(getUserLevel(auth))
            .resourceType(resourceType)
            .resourceId(resourceId)
            .action(action)
            .build();

        return policyEvaluator.evaluate(request);
    }
}
```

```java
@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    @GetMapping("/{id}")
    @PreAuthorize("@abac.check(authentication, 'DOCUMENT', #id, 'READ')")
    public Document getDocument(@PathVariable String id) { ... }

    @DeleteMapping("/{id}")
    @PreAuthorize("@abac.check(authentication, 'DOCUMENT', #id, 'DELETE')")
    public void deleteDocument(@PathVariable String id) { ... }
}
```

`@abac`은 스프링 빈 이름이다. `@Component("abac")`으로 등록한 빈의 `check()` 메서드를 SpEL에서 호출한다.

---

## 실무에서 RBAC + ABAC 혼합 패턴

대부분의 서비스에서 RBAC만으로 충분하다. ABAC은 "같은 역할이지만 조건에 따라 접근이 달라야 하는 경우"에만 도입한다.

### 패턴: 1차 RBAC, 2차 ABAC

```java
@Component("authz")
@RequiredArgsConstructor
public class HybridAuthorizationService {

    private final PolicyEvaluator abacEvaluator;

    /**
     * RBAC으로 기본 접근 여부를 판단하고,
     * 추가 조건이 필요한 경우 ABAC 정책을 평가한다.
     */
    public boolean check(Authentication auth, String resourceType,
                         String resourceId, String action) {
        // 1차: RBAC — ADMIN은 모든 접근 허용
        if (hasRole(auth, "ROLE_ADMIN")) {
            return true;
        }

        // 1차: RBAC — 해당 권한이 없으면 바로 거부
        String requiredPermission = resourceType + "_" + action;
        if (!hasAuthority(auth, requiredPermission)) {
            return false;
        }

        // 2차: ABAC — 세부 조건 평가
        AccessRequest request = buildRequest(auth, resourceType, resourceId, action);
        return abacEvaluator.evaluate(request);
    }

    private boolean hasRole(Authentication auth, String role) {
        return auth.getAuthorities().stream()
            .anyMatch(a -> a.getAuthority().equals(role));
    }

    private boolean hasAuthority(Authentication auth, String authority) {
        return auth.getAuthorities().stream()
            .anyMatch(a -> a.getAuthority().equals(authority));
    }
}
```

```java
@GetMapping("/api/documents/{id}")
@PreAuthorize("@authz.check(authentication, 'DOCUMENT', #id, 'READ')")
public Document getDocument(@PathVariable String id) { ... }
```

이 방식의 장점은 RBAC에서 걸러지면 ABAC 정책 평가를 하지 않는다는 것이다. ABAC 정책이 수십 개라도 RBAC에서 먼저 걸러내면 불필요한 연산을 줄일 수 있다.

### 실무에서 자주 쓰는 ABAC 조건들

```
# 본인 데이터만 접근 가능
subject.id == resource.ownerId

# 같은 부서 데이터만 접근 가능
subject.department == resource.department

# 업무 시간에만 접근 가능 (금융권에서 자주 씀)
environment.time >= 09:00 AND environment.time <= 18:00

# 사내 IP에서만 접근 가능
environment.ip IN allowedIpRanges

# 보안등급이 사용자 등급 이하인 리소스만 접근 가능
resource.securityLevel <= subject.clearanceLevel
```

"본인 데이터만 접근"은 거의 모든 서비스에서 필요한데, RBAC만으로는 표현이 안 된다. 이 하나 때문에라도 ABAC을 부분적으로 도입하는 경우가 많다.

### 주의할 점

**ABAC 정책을 DB에 저장하면 디버깅이 어렵다.** 왜 접근이 거부됐는지 추적하려면 어떤 정책이 매칭됐는지 로그를 남겨야 한다:

```java
public boolean evaluate(AccessRequest request) {
    List<Policy> policies = policyRepository.findActivePolicies();
    boolean permitted = false;

    for (Policy policy : policies) {
        if (!matches(policy, request)) {
            continue;
        }

        log.info("정책 매칭: policy={}, effect={}, user={}, resource={}, action={}",
            policy.getName(), policy.getEffect(),
            request.getUsername(), request.getResourceId(), request.getAction());

        if (policy.getEffect() == PolicyEffect.DENY) {
            log.warn("접근 거부: policy={}, user={}", policy.getName(), request.getUsername());
            return false;
        }
        permitted = true;
    }

    if (!permitted) {
        log.warn("매칭된 PERMIT 정책 없음: user={}, resource={}, action={}",
            request.getUsername(), request.getResourceId(), request.getAction());
    }

    return permitted;
}
```

**정책 순서 의존성을 만들지 않는다.** 정책 간에 순서가 중요해지면 관리가 불가능해진다. "DENY 우선" 규칙 하나로 충분하다. 정책 순서에 따라 결과가 달라지는 구조는 시간이 지나면 아무도 이해하지 못한다.

**RBAC으로 해결 가능한 건 RBAC으로 한다.** ABAC은 유연하지만 복잡하다. "관리자만 삭제 가능"을 ABAC 정책으로 만들 이유가 없다. `@PreAuthorize("hasRole('ADMIN')")`이면 된다.
