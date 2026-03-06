---
title: Spring 테스트 전략 가이드
tags: [framework, java, spring, testing, junit5, mockito, testcontainers, integration-test]
updated: 2026-03-01
---

# Spring 테스트 전략 가이드

## 배경

Spring 애플리케이션의 테스트는 단위 테스트부터 통합 테스트, E2E 테스트까지 계층적으로 구성한다. Spring Boot는 `spring-boot-starter-test`로 JUnit 5, Mockito, AssertJ 등을 기본 제공한다.

### 테스트 피라미드

```
         ┌──────┐
         │ E2E  │         적음, 느림, 비쌈
         ├──────┤
         │ 통합  │         중간
         ├──────┤
         │ 단위  │         많음, 빠름, 저렴
         └──────┘
```

| 계층 | 범위 | 속도 | Spring 컨텍스트 |
|------|------|------|----------------|
| **단위 테스트** | 클래스/메서드 하나 | 매우 빠름 | 불필요 |
| **슬라이스 테스트** | 특정 레이어 (Web, JPA) | 빠름 | 부분 로드 |
| **통합 테스트** | 여러 레이어 연동 | 느림 | 전체 로드 |
| **E2E 테스트** | API 호출 → DB 확인 | 매우 느림 | 전체 로드 + DB |

### 의존성

```gradle
dependencies {
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    // JUnit 5, Mockito, AssertJ, Hamcrest, JSONassert 포함

    testImplementation 'org.testcontainers:junit-jupiter'
    testImplementation 'org.testcontainers:postgresql'
}
```

## 핵심

### 1. 단위 테스트

Spring 컨텍스트 없이 순수 Java 코드만으로 테스트한다. 가장 빠르고 많이 작성해야 하는 테스트이다.

#### Service 단위 테스트

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @InjectMocks
    private UserService userService;

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Test
    @DisplayName("회원가입 성공")
    void signup_success() {
        // given
        SignupRequest request = new SignupRequest("test@email.com", "password123", "홍길동");

        given(userRepository.existsByEmail("test@email.com")).willReturn(false);
        given(passwordEncoder.encode("password123")).willReturn("encoded_password");
        given(userRepository.save(any(User.class))).willAnswer(invocation -> {
            User user = invocation.getArgument(0);
            ReflectionTestUtils.setField(user, "id", 1L);
            return user;
        });

        // when
        UserResponse response = userService.signup(request);

        // then
        assertThat(response.getEmail()).isEqualTo("test@email.com");
        assertThat(response.getName()).isEqualTo("홍길동");
        then(userRepository).should().save(any(User.class));
    }

    @Test
    @DisplayName("중복 이메일로 회원가입 시 예외 발생")
    void signup_duplicateEmail_throwsException() {
        // given
        SignupRequest request = new SignupRequest("existing@email.com", "password", "홍길동");
        given(userRepository.existsByEmail("existing@email.com")).willReturn(true);

        // when & then
        assertThatThrownBy(() -> userService.signup(request))
            .isInstanceOf(DuplicateEmailException.class)
            .hasMessageContaining("existing@email.com");

        then(userRepository).should(never()).save(any());
    }

    @Test
    @DisplayName("사용자 조회 - 존재하지 않는 ID")
    void getUser_notFound() {
        // given
        given(userRepository.findById(999L)).willReturn(Optional.empty());

        // when & then
        assertThatThrownBy(() -> userService.getUser(999L))
            .isInstanceOf(ResourceNotFoundException.class);
    }
}
```

**핵심 패턴:**
- `@ExtendWith(MockitoExtension.class)`: Spring 없이 Mockito만 사용
- `@InjectMocks`: 테스트 대상 객체 (의존성을 Mock으로 주입)
- `@Mock`: 가짜 객체
- **given-when-then** 패턴으로 구조화

#### Mockito 주요 API

| 분류 | 메서드 | 용도 |
|------|--------|------|
| **Stubbing** | `given(...).willReturn(...)` | 반환값 설정 |
| | `given(...).willThrow(...)` | 예외 발생 설정 |
| | `willDoNothing().given(mock).method()` | void 메서드 |
| **검증** | `then(mock).should().method()` | 호출 확인 |
| | `then(mock).should(times(2)).method()` | 호출 횟수 확인 |
| | `then(mock).should(never()).method()` | 미호출 확인 |
| **매처** | `any()`, `any(Class.class)` | 아무 값 |
| | `eq("value")` | 특정 값 |
| | `argThat(arg -> ...)` | 조건 매칭 |

### 2. 슬라이스 테스트

특정 레이어만 로드하여 테스트한다. 전체 컨텍스트보다 빠르다.

#### @WebMvcTest (Controller 테스트)

```java
@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean   // Spring 컨텍스트의 Bean을 Mock으로 교체
    private UserService userService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("POST /api/v1/users - 회원가입 성공")
    void createUser_success() throws Exception {
        // given
        CreateUserRequest request = new CreateUserRequest(
            "test@email.com", "password123", "홍길동");
        UserResponse response = new UserResponse(1L, "test@email.com", "홍길동",
            "USER", LocalDateTime.now());

        given(userService.createUser(any())).willReturn(response);

        // when & then
        mockMvc.perform(post("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.email").value("test@email.com"))
            .andExpect(jsonPath("$.name").value("홍길동"))
            .andDo(print());
    }

    @Test
    @DisplayName("POST /api/v1/users - 유효성 검증 실패")
    void createUser_invalidEmail() throws Exception {
        CreateUserRequest request = new CreateUserRequest(
            "invalid-email", "pw", "");

        mockMvc.perform(post("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
            .andExpect(jsonPath("$.errors").isArray())
            .andExpect(jsonPath("$.errors.length()").value(3));
    }

    @Test
    @DisplayName("GET /api/v1/users/{id} - 사용자 없음 404")
    void getUser_notFound() throws Exception {
        given(userService.getUser(999L))
            .willThrow(new ResourceNotFoundException("User", 999L));

        mockMvc.perform(get("/api/v1/users/999"))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }
}
```

#### @DataJpaTest (Repository 테스트)

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class UserRepositoryTest {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private TestEntityManager em;

    @Test
    @DisplayName("이메일로 사용자 조회")
    void findByEmail() {
        // given
        User user = User.builder()
            .email("test@email.com")
            .password("encoded")
            .name("홍길동")
            .role(Role.USER)
            .build();
        em.persistAndFlush(user);
        em.clear();

        // when
        Optional<User> found = userRepository.findByEmail("test@email.com");

        // then
        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("홍길동");
    }

    @Test
    @DisplayName("Soft Delete된 사용자는 조회되지 않음")
    void findByEmail_softDeleted() {
        // given
        User user = User.builder()
            .email("deleted@email.com")
            .password("encoded")
            .name("삭제된 사용자")
            .role(Role.USER)
            .build();
        em.persistAndFlush(user);
        user.softDelete();
        em.persistAndFlush(user);
        em.clear();

        // when
        Optional<User> found = userRepository.findByEmail("deleted@email.com");

        // then
        assertThat(found).isEmpty();
    }
}
```

### 3. 통합 테스트

전체 Spring 컨텍스트를 로드하여 레이어 간 연동을 테스트한다.

#### @SpringBootTest + TestRestTemplate

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class UserIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    @DisplayName("회원가입 → 로그인 → 프로필 조회 통합 테스트")
    void fullUserFlow() {
        // 1. 회원가입
        CreateUserRequest signupRequest = new CreateUserRequest(
            "user@test.com", "password123", "테스트");

        ResponseEntity<AuthResponse> signupResponse = restTemplate.postForEntity(
            "/api/auth/signup", signupRequest, AuthResponse.class);

        assertThat(signupResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        String accessToken = signupResponse.getBody().getAccessToken();

        // 2. 프로필 조회 (인증 포함)
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(accessToken);

        ResponseEntity<UserResponse> profileResponse = restTemplate.exchange(
            "/api/v1/users/me", HttpMethod.GET,
            new HttpEntity<>(headers), UserResponse.class);

        assertThat(profileResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(profileResponse.getBody().getEmail()).isEqualTo("user@test.com");
    }
}
```

### 4. Testcontainers (실제 DB 테스트)

H2 대신 실제 PostgreSQL/MySQL을 Docker로 띄워 테스트한다. 프로덕션 환경과 동일한 DB에서 테스트할 수 있다.

```java
@SpringBootTest
@Testcontainers
@ActiveProfiles("test")
class OrderServiceIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private OrderService orderService;

    @Autowired
    private UserRepository userRepository;

    @Test
    @DisplayName("주문 생성 - 실제 DB 테스트")
    void createOrder_withRealDB() {
        // given
        User user = userRepository.save(User.builder()
            .email("test@email.com")
            .password("encoded")
            .name("홍길동")
            .role(Role.USER)
            .build());

        CreateOrderRequest request = new CreateOrderRequest(
            List.of(new OrderItemRequest(1L, 2)));

        // when
        OrderResponse response = orderService.createOrder(user.getEmail(), request);

        // then
        assertThat(response.getStatus()).isEqualTo("CREATED");
        assertThat(response.getItems()).hasSize(1);
    }
}
```

#### Testcontainers 공통 설정

```java
// 테스트 전체에서 공유하는 추상 클래스
@SpringBootTest
@Testcontainers
@ActiveProfiles("test")
public abstract class IntegrationTestSupport {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }
}

// 각 테스트에서 상속
class OrderServiceTest extends IntegrationTestSupport {
    @Test
    void test() { ... }
}
```

### 5. 테스트 유틸리티

#### 테스트 픽스처

```java
// 테스트 데이터 생성 헬퍼
public class UserFixture {

    public static User createUser() {
        return User.builder()
            .email("test@email.com")
            .password("encoded_password")
            .name("홍길동")
            .role(Role.USER)
            .build();
    }

    public static User createAdmin() {
        return User.builder()
            .email("admin@email.com")
            .password("encoded_password")
            .name("관리자")
            .role(Role.ADMIN)
            .build();
    }

    public static CreateUserRequest createSignupRequest() {
        return new CreateUserRequest("test@email.com", "password123", "홍길동");
    }
}
```

#### AssertJ 주요 API

```java
// 기본 검증
assertThat(value).isEqualTo("expected");
assertThat(value).isNotNull();
assertThat(value).isInstanceOf(String.class);

// 컬렉션 검증
assertThat(list).hasSize(3);
assertThat(list).contains("a", "b");
assertThat(list).extracting("name").containsExactly("홍길동", "김철수");

// 예외 검증
assertThatThrownBy(() -> service.getUser(999L))
    .isInstanceOf(ResourceNotFoundException.class)
    .hasMessageContaining("999");

// 시간 검증
assertThat(createdAt).isAfter(LocalDateTime.now().minusMinutes(1));
```

## 예시

### 테스트 디렉토리 구조

```
src/test/java/com/example/
├── unit/                          # 단위 테스트
│   ├── service/
│   │   ├── UserServiceTest.java
│   │   └── OrderServiceTest.java
│   └── domain/
│       └── UserTest.java          # Entity 비즈니스 로직
├── integration/                   # 통합 테스트
│   ├── IntegrationTestSupport.java
│   ├── UserIntegrationTest.java
│   └── OrderIntegrationTest.java
├── controller/                    # Controller 테스트
│   ├── UserControllerTest.java
│   └── OrderControllerTest.java
├── repository/                    # Repository 테스트
│   └── UserRepositoryTest.java
└── fixture/                       # 테스트 데이터
    ├── UserFixture.java
    └── OrderFixture.java
```

## 운영 팁

### 테스트 전략 요약

| 레이어 | 어노테이션 | Mock 대상 | 검증 포인트 |
|--------|-----------|-----------|------------|
| **Controller** | `@WebMvcTest` | Service | 요청/응답 형식, 상태코드, Validation |
| **Service** | `@ExtendWith(Mockito)` | Repository, 외부 서비스 | 비즈니스 로직, 예외 처리 |
| **Repository** | `@DataJpaTest` | 없음 (실제 DB) | 쿼리 정확성, 제약조건 |
| **통합** | `@SpringBootTest` | 없음 (전체 실행) | 레이어 연동, 전체 흐름 |

### 흔한 실수

| 실수 | 문제 | 해결 |
|------|------|------|
| 모든 테스트에 `@SpringBootTest` | 매우 느림 | 단위 테스트 우선, 슬라이스 테스트 활용 |
| 테스트 간 데이터 공유 | 테스트 순서에 따라 결과 변경 | `@BeforeEach`로 초기화 |
| H2로만 테스트 | 프로덕션 DB와 동작 차이 | Testcontainers 사용 |
| 테스트에서 `@Transactional` 남용 | 실제 커밋되지 않아 놓치는 버그 | 통합 테스트는 실제 커밋 후 검증 |
| private 메서드 테스트 | 구현 세부사항에 의존 | public 메서드를 통해 간접 검증 |

### Gradle 테스트 설정

```gradle
tasks.named('test') {
    useJUnitPlatform()

    // 테스트 병렬 실행
    maxParallelForks = Runtime.runtime.availableProcessors().intdiv(2) ?: 1

    // 테스트 결과 출력
    testLogging {
        events "passed", "skipped", "failed"
        showStandardStreams = true
    }
}
```

## 참고

- [Spring Boot 테스트 공식 문서](https://docs.spring.io/spring-boot/reference/testing/)
- [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
- [Mockito 공식 문서](https://site.mockito.org/)
- [Testcontainers 공식 문서](https://testcontainers.com/)
- [AssertJ 공식 문서](https://assertj.github.io/doc/)
