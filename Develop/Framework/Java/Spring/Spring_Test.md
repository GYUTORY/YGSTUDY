---
title: Spring 테스트
tags: [framework, java, spring, testing, junit5, mockito, testcontainers, integration-test, spring-security]
updated: 2026-06-14
---

# Spring 테스트

## 배경

Spring 애플리케이션 테스트는 단위, 슬라이스, 통합, E2E 순으로 범위가 넓어진다. 범위가 넓어질수록 Spring 컨텍스트를 더 많이 띄우고, 그만큼 느려진다. 실무에서 테스트가 느려서 CI가 10분, 20분씩 걸리는 일이 생기는데 대부분 원인은 "단위로 끝낼 걸 통합으로 짰다"거나 "컨텍스트가 쓸데없이 여러 번 떠서"다. 그래서 각 계층을 언제 쓰는지 구분하는 게 테스트 작성법 자체보다 중요하다.

Spring Boot는 `spring-boot-starter-test` 하나로 JUnit 5, Mockito, AssertJ, JSONassert를 끌고 온다.

### 계층별 비교

| 계층 | 범위 | 속도 | Spring 컨텍스트 |
|------|------|------|----------------|
| 단위 테스트 | 클래스/메서드 하나 | 매우 빠름 | 안 띄움 |
| 슬라이스 테스트 | 특정 레이어 (Web, JPA) | 빠름 | 일부만 로드 |
| 통합 테스트 | 여러 레이어 연동 | 느림 | 전체 로드 |
| E2E 테스트 | API 호출 → DB 확인 | 매우 느림 | 전체 로드 + 실제 DB |

단위 테스트를 많이 쓰고 통합/E2E는 핵심 흐름에만 쓴다. 모든 테스트를 `@SpringBootTest`로 짜면 컨텍스트 로딩 때문에 테스트 한 개당 수 초가 추가되고, 그게 수백 개 쌓이면 빌드가 못 돌아간다.

### 의존성

```gradle
dependencies {
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    // JUnit 5, Mockito, AssertJ, Hamcrest, JSONassert 포함

    // Spring Security 테스트 (@WithMockUser 등)
    testImplementation 'org.springframework.security:spring-security-test'

    testImplementation 'org.testcontainers:junit-jupiter'
    testImplementation 'org.testcontainers:postgresql'

    // RestAssured (선택 — E2E)
    testImplementation 'io.rest-assured:rest-assured'
}
```

## 단위 테스트

Spring 컨텍스트 없이 순수 Java 객체만 검증한다. 가장 빠르고 가장 많이 짜야 하는 테스트다.

### Service 단위 테스트

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
}
```

`@ExtendWith(MockitoExtension.class)`는 Spring을 안 띄우고 Mockito만 돌린다. `@InjectMocks`가 테스트 대상이고 `@Mock`으로 만든 가짜들을 생성자로 주입한다. given-when-then으로 끊어 두면 나중에 깨졌을 때 어디가 문제인지 빨리 찾는다.

주의할 점: `MockitoExtension`은 stubbing 해놓고 안 쓰면 `UnnecessaryStubbingException`을 던진다. 여러 테스트가 공유하는 `@BeforeEach`에서 stubbing을 몰아 넣으면 특정 테스트에서 안 쓰는 stub 때문에 실패하는데, 이때는 해당 stub을 각 테스트로 옮기거나 `lenient()`를 쓴다. `lenient()` 남발은 진짜 안 쓰는 stub을 못 잡게 만드니 최소한으로 쓴다.

### Mockito 주요 API

| 분류 | 메서드 | 용도 |
|------|--------|------|
| Stubbing | `given(...).willReturn(...)` | 반환값 설정 |
| | `given(...).willThrow(...)` | 예외 발생 설정 |
| | `willDoNothing().given(mock).method()` | void 메서드 |
| 검증 | `then(mock).should().method()` | 호출 확인 |
| | `then(mock).should(times(2)).method()` | 호출 횟수 |
| | `then(mock).should(never()).method()` | 미호출 확인 |
| 매처 | `any()`, `any(Class.class)` | 아무 값 |
| | `eq("value")` | 특정 값 |
| | `argThat(arg -> ...)` | 조건 매칭 |

매처를 한 인자라도 쓰면 모든 인자를 매처로 맞춰야 한다. `given(repo.find(eq(1L), "active"))`처럼 섞으면 `InvalidUseOfMatchersException`이 나니 `eq("active")`로 통일한다.

## 슬라이스 테스트

특정 레이어만 로드한다. 전체 컨텍스트보다 빠르고, 그 레이어 관심사만 본다.

### @WebMvcTest (Controller 테스트)

```java
@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean   // Spring Boot 3.4+ — 컨텍스트의 Bean을 Mock으로 교체
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
        CreateUserRequest request = new CreateUserRequest("invalid-email", "pw", "");

        mockMvc.perform(post("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
            .andExpect(jsonPath("$.errors").isArray());
    }
}
```

`@WebMvcTest`는 Controller 레이어만 띄우니 Service는 빈으로 안 올라온다. 그래서 `@MockitoBean`으로 가짜를 컨텍스트에 넣어줘야 한다. 여기서 Service까지 진짜로 주입하려 하면 빈을 못 찾아 컨텍스트가 안 뜬다.

### @MockBean / @SpyBean deprecated 주의

이게 버전별로 바뀌어서 실무에서 많이 헷갈린다.

Spring Boot 3.4부터 `@MockBean`, `@SpyBean`이 deprecated됐다. 대체재는 Spring Framework 6.2가 제공하는 `@MockitoBean`, `@MockitoSpyBean`이다. 패키지도 바뀐다.

```java
// Spring Boot 3.3 이하
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;

@MockBean
private UserService userService;

// Spring Boot 3.4+
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

@MockitoBean
private UserService userService;
```

마이그레이션 시 주의:

- 어노테이션 이름과 import 패키지가 둘 다 바뀐다. IDE의 자동 import가 옛 패키지를 잡는 경우가 있어 컴파일은 되는데 deprecated 경고만 뜬다. import 라인을 직접 확인한다.
- `@MockitoBean`은 빈 이름이 아니라 타입으로 찾는 게 기본이다. 같은 타입 빈이 여러 개면 `@MockitoBean(name = "...")`으로 지정해야 한다.
- 3.4 미만이면 `@MockitoBean`이 아예 없으니 버전부터 확인한다. Spring Boot 3.4 = Spring Framework 6.2 조합이어야 쓸 수 있다.
- 동작 자체는 같다. deprecated라고 당장 안 도는 건 아니지만, 새 코드는 `@MockitoBean`으로 쓰고 기존 코드는 버전 올릴 때 같이 정리한다.

`@MockitoBean`이 통합 테스트 속도에 미치는 영향은 뒤의 트러블슈팅에서 다룬다.

### @DataJpaTest (Repository 테스트)

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
        em.clear();   // 1차 캐시 비우기 — 실제 쿼리 나가게

        // when
        Optional<User> found = userRepository.findByEmail("test@email.com");

        // then
        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("홍길동");
    }
}
```

`@DataJpaTest`는 기본으로 임베디드 DB(H2)로 바꿔치기하고 각 테스트를 트랜잭션으로 감싸 롤백한다. 실제 DB로 돌리려면 `@AutoConfigureTestDatabase(replace = NONE)`를 붙인다.

`em.persistAndFlush()` 후 `em.clear()`를 빼먹으면 조회가 1차 캐시에서 그냥 객체를 돌려줘서 쿼리가 안 나간다. 그러면 매핑이 틀려도 테스트가 통과한다. 1차 캐시 함정은 뒤에서 더 자세히 본다.

## Spring Security 연동 테스트

시큐리티가 붙은 컨트롤러는 인증 없이 호출하면 401/403이 떨어져서, 평범한 `@WebMvcTest`가 갑자기 다 깨진다. `spring-security-test`가 주는 도구로 인증 상태를 흉내 낸다.

### @WithMockUser

```java
@WebMvcTest(UserController.class)
class UserControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private UserService userService;

    @Test
    @DisplayName("인증 없이 보호된 엔드포인트 호출 시 401")
    void getMe_unauthenticated() throws Exception {
        mockMvc.perform(get("/api/v1/users/me"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "user@test.com", roles = "USER")
    @DisplayName("USER 권한으로 내 정보 조회")
    void getMe_asUser() throws Exception {
        given(userService.getMyProfile("user@test.com"))
            .willReturn(new UserResponse(1L, "user@test.com", "홍길동", "USER", LocalDateTime.now()));

        mockMvc.perform(get("/api/v1/users/me"))
            .andExpect(status().isOk());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER가 관리자 전용 API 호출 시 403")
    void adminApi_forbiddenForUser() throws Exception {
        mockMvc.perform(get("/api/v1/admin/users"))
            .andExpect(status().isForbidden());
    }
}
```

`@WithMockUser(roles = "USER")`는 내부에서 `ROLE_USER`로 권한을 만든다. 그래서 `roles`에는 `ROLE_` 접두사를 빼고 적는다. `authorities = "ROLE_USER"`처럼 권한 문자열을 직접 줄 때는 접두사를 포함해야 한다. 이 둘을 헷갈려서 403이 안 풀리는 경우가 흔하다.

### @WebMvcTest와 시큐리티 필터

`@WebMvcTest`는 슬라이스라서 `SecurityFilterChain` 빈이 같이 안 올라오는 경우가 있다. 그러면 시큐리티 설정(어떤 URL을 누가 접근 가능한지)이 테스트에 반영 안 돼서, 401이 떠야 할 곳이 200으로 통과한다. 시큐리티 설정 클래스를 명시적으로 끌어와야 한다.

```java
@WebMvcTest(UserController.class)
@Import(SecurityConfig.class)   // 시큐리티 설정을 슬라이스에 포함
class UserControllerSecurityTest { ... }
```

`SecurityConfig`가 `UserDetailsService`나 JWT 디코더 같은 다른 빈을 요구하면 그것까지 `@MockitoBean`으로 채워야 컨텍스트가 뜬다. 이 의존성 체인이 길어지면 차라리 `@SpringBootTest` 통합 테스트로 시큐리티를 검증하는 게 낫다.

특정 테스트에서만 시큐리티를 끄고 싶으면 `@AutoConfigureMockMvc(addFilters = false)`로 필터 자체를 뺀다. 단 이러면 인증/인가를 전혀 안 보는 거라, 컨트롤러 로직만 보는 테스트에 한정해서 쓴다.

### SecurityMockMvcRequestPostProcessors

어노테이션 대신 요청 단위로 인증을 주입하는 방법이다. `@ParameterizedTest`로 권한별 케이스를 돌릴 때 어노테이션보다 편하다.

```java
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.*;

@Test
void postWithUser() throws Exception {
    mockMvc.perform(post("/api/v1/orders")
            .with(user("user@test.com").roles("USER"))   // 요청에 인증 주입
            .with(csrf())                                 // CSRF 토큰 (POST/PUT/DELETE)
            .contentType(MediaType.APPLICATION_JSON)
            .content("{}"))
        .andExpect(status().isCreated());
}
```

CSRF가 켜진 상태에서 POST/PUT/DELETE를 `.with(csrf())` 없이 보내면 403이 난다. REST API라 CSRF를 끈 설정이면 안 붙여도 되지만, 폼 기반이거나 기본 설정이면 거의 항상 필요하다. 인증 자체는 됐는데 403이 안 풀린다면 십중팔구 CSRF 토큰 누락이다.

JWT나 OAuth2를 쓰면 `jwt()`, `oauth2Login()` 같은 전용 post processor가 따로 있다.

## 실전 테스트 패턴

### @Nested로 시나리오 그룹핑

메서드 하나에 대한 성공/실패 케이스가 흩어지면 읽기 어렵다. `@Nested`로 묶으면 IDE 테스트 트리에서도 계층으로 보인다.

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @InjectMocks OrderService orderService;
    @Mock OrderRepository orderRepository;
    @Mock StockService stockService;

    @Nested
    @DisplayName("주문 생성")
    class CreateOrder {

        @Test
        @DisplayName("재고가 충분하면 주문이 생성된다")
        void success() { ... }

        @Test
        @DisplayName("재고가 부족하면 OutOfStockException")
        void outOfStock() { ... }

        @Test
        @DisplayName("존재하지 않는 상품이면 ProductNotFoundException")
        void productNotFound() { ... }
    }

    @Nested
    @DisplayName("주문 취소")
    class CancelOrder {

        @Test
        @DisplayName("배송 전이면 취소된다")
        void beforeShipping() { ... }

        @Test
        @DisplayName("배송 후면 취소 불가")
        void afterShipping() { ... }
    }
}
```

`@Nested` 클래스는 `static`이 아니어야 한다. JUnit 5가 inner class로 인스턴스를 만들기 때문이다. 실수로 `static`을 붙이면 테스트가 실행 자체를 안 한다.

### @ParameterizedTest로 경계값 테스트

비밀번호 길이, 할인율 구간 같은 경계값을 한 메서드로 돌린다.

```java
@ParameterizedTest(name = "비밀번호 길이 {0} → 유효성 {1}")
@CsvSource({
    "7,  false",   // 최소 8자 미만
    "8,  true",    // 경계값
    "20, true",    // 최대 20자
    "21, false"    // 초과
})
@DisplayName("비밀번호 길이 경계값 검증")
void validatePasswordLength(int length, boolean expected) {
    String password = "a".repeat(length);
    assertThat(passwordValidator.isValid(password)).isEqualTo(expected);
}

@ParameterizedTest
@ValueSource(strings = {"", "  ", "\t"})
@DisplayName("이름이 비거나 공백이면 예외")
void blankName(String name) {
    assertThatThrownBy(() -> new User(name))
        .isInstanceOf(IllegalArgumentException.class);
}

// 복잡한 객체는 @MethodSource
@ParameterizedTest
@MethodSource("discountCases")
void calculateDiscount(int amount, Grade grade, int expected) {
    assertThat(discountPolicy.apply(amount, grade)).isEqualTo(expected);
}

static Stream<Arguments> discountCases() {
    return Stream.of(
        Arguments.of(10000, Grade.BRONZE, 0),
        Arguments.of(10000, Grade.GOLD, 1000),
        Arguments.of(10000, Grade.VIP, 2000)
    );
}
```

경계값은 "딱 경계인 값"과 "경계 바로 옆 값"을 같이 넣어야 의미가 있다. 8자가 통과하는지만 보고 7자를 안 넣으면 `>=` 를 `>`로 잘못 짠 버그를 못 잡는다.

### @Sql로 데이터 세팅

통합 테스트에서 Java 코드로 엔티티를 일일이 저장하는 대신 SQL 파일로 초기 데이터를 깐다.

```java
@SpringBootTest
@AutoConfigureMockMvc
class OrderQueryTest {

    @Autowired MockMvc mockMvc;

    @Test
    @Sql("/sql/orders-fixture.sql")              // 테스트 전 실행
    @Sql(scripts = "/sql/cleanup.sql",
         executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)   // 테스트 후 정리
    void searchOrders() throws Exception {
        mockMvc.perform(get("/api/v1/orders?status=PAID"))
            .andExpect(jsonPath("$.content.length()").value(3));
    }
}
```

```sql
-- src/test/resources/sql/orders-fixture.sql
INSERT INTO users (id, email, name) VALUES (1, 'u@test.com', '홍길동');
INSERT INTO orders (id, user_id, status, amount) VALUES
    (1, 1, 'PAID', 10000),
    (2, 1, 'PAID', 20000),
    (3, 1, 'CANCELLED', 5000);
```

조회 쿼리처럼 읽기만 하는 테스트는 픽스처 양이 많아질수록 `@Sql`이 Java 빌더보다 보기 쉽다. 반대로 도메인 생성 로직 자체를 검증할 때는 SQL로 우회 삽입하면 그 로직을 안 거치니 Java로 만든다.

## 통합 테스트

전체 컨텍스트를 띄워 레이어 연동을 본다. 느리니 핵심 흐름에만 쓴다.

### @SpringBootTest + TestRestTemplate

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
    @DisplayName("회원가입 → 로그인 → 프로필 조회")
    void fullUserFlow() {
        CreateUserRequest signupRequest = new CreateUserRequest(
            "user@test.com", "password123", "테스트");

        ResponseEntity<AuthResponse> signupResponse = restTemplate.postForEntity(
            "/api/auth/signup", signupRequest, AuthResponse.class);

        assertThat(signupResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        String accessToken = signupResponse.getBody().getAccessToken();

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

`RANDOM_PORT`로 실제 톰캣을 띄우면 `TestRestTemplate`이 진짜 HTTP로 호출한다. 이때는 별도 스레드라 테스트 메서드의 트랜잭션이 서버 쪽에 안 걸린다. 그래서 `@Transactional`을 붙여도 롤백이 안 되니, `@BeforeEach`에서 직접 데이터를 지운다.

### @AutoConfigureMockMvc + @SpringBootTest

`RANDOM_PORT` 대신 MockMvc로 컨트롤러를 호출하는 조합이다. 실제 네트워크를 안 타니 더 빠르고, 전체 컨텍스트가 떠 있어서 서비스/리포지토리는 진짜로 동작한다.

```java
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class OrderApiTest {

    @Autowired MockMvc mockMvc;
    @Autowired OrderRepository orderRepository;

    @Test
    @WithMockUser(username = "user@test.com", roles = "USER")
    void createOrder() throws Exception {
        mockMvc.perform(post("/api/v1/orders")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"items\":[{\"productId\":1,\"quantity\":2}]}"))
            .andExpect(status().isCreated());

        assertThat(orderRepository.count()).isEqualTo(1);
    }
}
```

`@WebMvcTest`와 다른 점: `@WebMvcTest`는 컨트롤러만 띄우고 서비스는 mock이지만, 이 조합은 전체 빈이 진짜라 서비스/DB까지 실제로 흐른다. `@WithMockUser`가 MockMvc 호출에 그대로 먹는 것도 이 조합의 장점이다.

## E2E 옵션 비교

| 방식 | 네트워크 | 컨텍스트 | 인증 흉내 | 쓰는 경우 |
|------|---------|---------|----------|----------|
| `@WebMvcTest` + MockMvc | 안 탐 | 컨트롤러만 | `@WithMockUser` | 컨트롤러 단위 검증 |
| `@SpringBootTest` + MockMvc | 안 탐 | 전체 | `@WithMockUser` | 레이어 연동, 빠른 통합 |
| `@SpringBootTest(RANDOM_PORT)` + TestRestTemplate | 탐 | 전체 | 토큰 직접 헤더 | 실제 HTTP, 직렬화까지 |
| `@SpringBootTest(RANDOM_PORT)` + RestAssured | 탐 | 전체 | 토큰 직접 헤더 | 가독성 좋은 E2E |

대부분의 통합 테스트는 `@SpringBootTest` + MockMvc면 충분하다. 실제 직렬화/역직렬화, 필터, HTTP 상태까지 진짜로 확인해야 하는 핵심 시나리오만 `RANDOM_PORT`를 쓴다. 네트워크를 타는 쪽이 당연히 느리다.

### RestAssured

API 호출/검증을 BDD 스타일로 쓴다. 응답 JSON 검증이 길어질 때 MockMvc의 `jsonPath` 체인보다 읽기 편하다는 사람이 많다.

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class OrderE2ETest {

    @LocalServerPort
    int port;

    @BeforeEach
    void setUp() {
        RestAssured.port = port;
    }

    @Test
    void createAndGetOrder() {
        String token = obtainAccessToken();

        // 주문 생성
        int orderId =
            given()
                .header("Authorization", "Bearer " + token)
                .contentType(ContentType.JSON)
                .body(Map.of("items", List.of(Map.of("productId", 1, "quantity", 2))))
            .when()
                .post("/api/v1/orders")
            .then()
                .statusCode(201)
                .body("status", equalTo("CREATED"))
                .extract().path("id");

        // 조회
        given()
            .header("Authorization", "Bearer " + token)
        .when()
            .get("/api/v1/orders/" + orderId)
        .then()
            .statusCode(200)
            .body("items.size()", equalTo(1));
    }
}
```

`@LocalServerPort`로 랜덤 포트를 받아 `RestAssured.port`에 넣어야 한다. 안 그러면 기본 8080으로 쏴서 연결이 안 된다. MockMvc와 달리 진짜 서버를 치는 거라 토큰도 실제 헤더로 넣어야 한다.

## Testcontainers (실제 DB 테스트)

H2 대신 실제 PostgreSQL/MySQL을 Docker로 띄운다. H2는 방언(dialect)이 달라서 통과하는데 프로덕션 DB에선 깨지는 쿼리가 종종 있다. 윈도우 함수, `JSONB`, 특정 인덱스 힌트 같은 게 대표적이다.

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

    @Autowired private OrderService orderService;
    @Autowired private UserRepository userRepository;

    @Test
    @DisplayName("주문 생성 - 실제 DB")
    void createOrder_withRealDB() {
        User user = userRepository.save(User.builder()
            .email("test@email.com").password("encoded")
            .name("홍길동").role(Role.USER).build());

        CreateOrderRequest request = new CreateOrderRequest(
            List.of(new OrderItemRequest(1L, 2)));

        OrderResponse response = orderService.createOrder(user.getEmail(), request);

        assertThat(response.getStatus()).isEqualTo("CREATED");
        assertThat(response.getItems()).hasSize(1);
    }
}
```

`@Container`를 `static`으로 두면 클래스 내 모든 테스트가 컨테이너 하나를 공유한다. 인스턴스 필드로 두면 메서드마다 컨테이너를 새로 띄워서 엄청 느려진다. 거의 항상 `static`으로 쓴다.

### 싱글톤 컨테이너 패턴

클래스마다 컨테이너를 따로 띄우면, 통합 테스트 클래스가 많아질 때 컨테이너 시작/종료 비용이 쌓인다. 컨테이너 하나를 JVM 전체에서 공유하는 패턴을 쓴다.

```java
public abstract class IntegrationTestSupport {

    static final PostgreSQLContainer<?> POSTGRES;

    static {
        POSTGRES = new PostgreSQLContainer<>("postgres:16")
            .withDatabaseName("testdb");
        POSTGRES.start();   // 한 번만 시작, 명시적으로 stop 안 함 (JVM 종료 시 정리)
    }

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }
}
```

`@Testcontainers`/`@Container`를 안 쓰고 static 초기화 블록에서 직접 `start()`한다. JUnit이 클래스 단위로 컨테이너를 관리하지 않으니 모든 테스트 클래스가 이 컨테이너 하나를 쓴다. `stop()`을 명시적으로 안 부르는데, Testcontainers의 Ryuk 컨테이너가 테스트 JVM 종료를 감지해 정리한다.

### withReuse — 컨테이너 재사용

로컬에서 반복 실행할 때 매번 컨테이너를 새로 띄우는 시간을 줄인다. 테스트가 끝나도 컨테이너를 안 죽이고 다음 실행 때 재사용한다.

```java
static final PostgreSQLContainer<?> POSTGRES =
    new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withReuse(true);   // 재사용 활성화
```

`withReuse(true)`만으로는 안 되고, 사용자 홈의 `~/.testcontainers.properties`에 `testcontainers.reuse.enable=true`가 있어야 동작한다. 이 설정은 개발자 로컬 환경에만 두고 CI에는 안 둔다. CI는 매번 깨끗한 컨테이너로 돌아야 하고, 재사용 컨테이너에 이전 데이터가 남아 테스트가 서로 오염되는 걸 막아야 한다.

재사용을 켜면 컨테이너가 안 죽으니 이전 실행의 데이터가 그대로 남는다. 각 테스트가 자기 데이터를 직접 정리하거나(`@Sql` cleanup, `deleteAll`) 트랜잭션 롤백에 의존해야 한다. 안 그러면 두 번째 실행부터 "이미 있는 데이터" 때문에 깨진다.

## 컨텍스트 캐싱과 테스트 속도

통합 테스트가 느린 진짜 원인은 대부분 ApplicationContext를 여러 번 띄우는 거다. 이걸 이해하면 CI 시간이 크게 준다.

### 컨텍스트는 캐싱된다

Spring TestContext Framework는 같은 설정의 컨텍스트를 캐시해서 재사용한다. 테스트 클래스마다 컨텍스트를 새로 안 띄우고, 설정이 같으면 한 번 띄운 걸 공유한다. 캐시 키는 `@SpringBootTest`의 properties, `@ActiveProfiles`, `@MockitoBean` 구성, `@Import` 같은 설정 조합이다.

문제는 이 키가 조금만 달라도 별개 컨텍스트로 취급해 새로 띄운다는 점이다. 테스트마다 `@ActiveProfiles`나 properties를 조금씩 다르게 주면 컨텍스트가 N개 생겨서 그만큼 느려진다. 통합 테스트 설정을 공통 부모 클래스로 통일하면 컨텍스트 하나로 모든 통합 테스트가 돌아간다.

### @MockitoBean이 캐시를 깨뜨린다

`@MockitoBean`(과거 `@MockBean`)은 컨텍스트 캐시 키에 포함된다. 그래서 어떤 빈을 mock으로 바꾸면 그 조합은 별개 컨텍스트가 되어 새로 뜬다.

테스트 클래스마다 서로 다른 빈을 `@MockitoBean`으로 바꾸면, 클래스 수만큼 컨텍스트가 생긴다. 통합 테스트 10개가 각자 다른 mock을 쓰면 컨텍스트가 10번 뜨고, 캐싱 이득이 사라진다. 통합 테스트는 가능하면 mock 없이 진짜 빈으로 돌리고, mock이 필요하면 단위/슬라이스 테스트로 내린다. 굳이 통합에서 mock을 써야 하면 같은 mock 구성을 공통 부모로 묶어 컨텍스트를 공유시킨다.

### @DirtiesContext 오남용

`@DirtiesContext`는 테스트가 컨텍스트를 더럽혔다고 표시해서, 그 다음 테스트가 컨텍스트를 새로 띄우게 한다. 컨텍스트 캐싱의 이득을 통째로 버리는 어노테이션이다.

"테스트 격리가 안 되는 것 같으니 일단 붙이자"는 식으로 남용하면 모든 테스트가 매번 컨텍스트를 새로 띄워 빌드가 몇 배 느려진다. 실제로는 격리 문제 대부분이 데이터 정리(`@BeforeEach` cleanup, 트랜잭션 롤백)나 mock 리셋으로 풀린다. `@DirtiesContext`는 정말 컨텍스트 자체(빈 상태, 정적 설정)가 오염될 때만 쓴다.

```java
// 이런 식으로 클래스 전체에 붙이면 모든 메서드마다 컨텍스트 재생성 — 거의 항상 잘못된 사용
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
class SlowTest { ... }
```

## @Transactional 롤백 테스트의 함정

통합 테스트에 `@Transactional`을 붙이면 각 테스트가 끝날 때 롤백돼서 DB가 깨끗하게 유지된다. 편하지만, 이 편리함이 진짜 버그를 가린다.

### 1차 캐시로 인한 가짜 통과

`@Transactional` 테스트는 트랜잭션이 안 끝나서 영속성 컨텍스트(1차 캐시)가 살아 있다. 저장 직후 조회하면 DB가 아니라 1차 캐시에서 같은 객체를 그대로 돌려준다. 그래서 실제로는 INSERT 쿼리가 안 나가도, 컬럼 매핑이 틀려도 테스트가 통과한다.

```java
@SpringBootTest
@Transactional
class UserServiceTxTest {

    @Autowired UserService userService;
    @Autowired UserRepository userRepository;
    @Autowired EntityManager em;

    @Test
    void saveAndFind_가짜통과_위험() {
        userService.signup(new SignupRequest("a@test.com", "pw", "홍길동"));

        // 1차 캐시에서 그대로 반환 — DB에 진짜 들어갔는지, 매핑이 맞는지 검증 못 함
        User found = userRepository.findByEmail("a@test.com").orElseThrow();
        assertThat(found.getName()).isEqualTo("홍길동");   // 항상 통과
    }

    @Test
    void saveAndFind_제대로검증() {
        userService.signup(new SignupRequest("a@test.com", "pw", "홍길동"));

        em.flush();   // 강제로 INSERT 쿼리 실행 — 제약조건/매핑 오류가 여기서 터짐
        em.clear();   // 1차 캐시 비우기 — 이후 조회는 실제 DB SELECT

        User found = userRepository.findByEmail("a@test.com").orElseThrow();
        assertThat(found.getName()).isEqualTo("홍길동");
    }
}
```

`em.flush()`는 쌓인 변경을 DB로 내보내서 NOT NULL 위반, 유니크 제약, 컬럼 길이 초과 같은 오류를 실제로 터뜨린다. `em.clear()`는 1차 캐시를 비워 다음 조회가 진짜 SELECT를 날리게 한다. flush 없이 짜면 운영에서 터질 제약조건 위반을 테스트가 못 잡는다.

### flush 시점 때문에 예외를 못 잡는 경우

유니크 제약 위반 같은 건 flush 시점에 터진다. `@Transactional` 테스트에서 커밋이 안 일어나면 flush도 안 돼서, 예외를 기대한 테스트가 예외 없이 끝나버린다.

```java
@Test
void duplicateEmail_제약위반() {
    userRepository.save(new User("dup@test.com"));
    userRepository.save(new User("dup@test.com"));   // 유니크 위반인데...

    // flush 전이라 아직 예외 안 남 — 이대로 끝나면 테스트는 통과(가짜)
    assertThatThrownBy(() -> userRepository.flush())   // flush를 직접 불러야 예외 발생
        .isInstanceOf(DataIntegrityViolationException.class);
}
```

### 진짜 커밋 동작을 봐야 할 때

`@TransactionalEventListener(phase = AFTER_COMMIT)`로 커밋 후 동작을 검증하거나, 실제 커밋된 데이터를 별도 트랜잭션에서 확인해야 한다면 `@Transactional`을 빼야 한다. 대신 `@BeforeEach`/`@AfterEach`나 `@Sql` cleanup으로 데이터를 직접 정리한다. `RANDOM_PORT` 통합 테스트는 어차피 서버가 별도 트랜잭션을 쓰므로 테스트 메서드의 `@Transactional`이 롤백을 못 한다는 점도 같이 기억한다.

## 테스트 유틸리티

### 테스트 픽스처

```java
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

### AssertJ 주요 API

```java
// 기본
assertThat(value).isEqualTo("expected");
assertThat(value).isNotNull();
assertThat(value).isInstanceOf(String.class);

// 컬렉션
assertThat(list).hasSize(3);
assertThat(list).contains("a", "b");
assertThat(list).extracting("name").containsExactly("홍길동", "김철수");

// 예외
assertThatThrownBy(() -> service.getUser(999L))
    .isInstanceOf(ResourceNotFoundException.class)
    .hasMessageContaining("999");

// 시간
assertThat(createdAt).isAfter(LocalDateTime.now().minusMinutes(1));
```

객체 여러 필드를 한 번에 비교할 때는 `usingRecursiveComparison()`이 편하다. equals를 안 오버라이드한 DTO도 필드 단위로 비교한다.

```java
assertThat(actual)
    .usingRecursiveComparison()
    .ignoringFields("id", "createdAt")
    .isEqualTo(expected);
```

## 디렉토리 구조

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
├── controller/                    # Controller 슬라이스
│   ├── UserControllerTest.java
│   └── OrderControllerTest.java
├── repository/                    # Repository 슬라이스
│   └── UserRepositoryTest.java
└── fixture/                       # 테스트 데이터
    ├── UserFixture.java
    └── OrderFixture.java
```

## 운영 팁

### 계층별 정리

| 레이어 | 어노테이션 | Mock 대상 | 보는 것 |
|--------|-----------|-----------|--------|
| Controller | `@WebMvcTest` | Service (`@MockitoBean`) | 요청/응답 형식, 상태코드, Validation |
| Service | `@ExtendWith(Mockito)` | Repository, 외부 서비스 | 비즈니스 로직, 예외 처리 |
| Repository | `@DataJpaTest` | 없음 (실제/임베디드 DB) | 쿼리 정확성, 제약조건 |
| 통합 | `@SpringBootTest` | 없음 (전체 실행) | 레이어 연동, 전체 흐름 |

### 자주 겪는 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 모든 테스트에 `@SpringBootTest` | 컨텍스트 반복 로딩 | 단위 우선, 슬라이스 활용 |
| 통합 테스트가 클래스마다 느려짐 | `@MockitoBean` 구성이 달라 컨텍스트 N개 | mock 구성을 공통 부모로 통일 |
| `@DirtiesContext` 남용 | 매번 컨텍스트 재생성 | 데이터 정리/mock 리셋으로 대체 |
| 저장 후 조회가 항상 통과 | 1차 캐시 반환 | `em.flush()` + `em.clear()` |
| 제약 위반 예외를 못 잡음 | flush 전이라 쿼리 미실행 | `flush()` 직접 호출 후 검증 |
| 시큐리티 테스트 401/403 안 풀림 | 필터 미적용 또는 CSRF 누락 | `@Import(SecurityConfig)`, `.with(csrf())` |
| H2만 테스트 | 방언 차이로 프로덕션과 다름 | Testcontainers |
| 컨테이너가 메서드마다 뜸 | `@Container` 인스턴스 필드 | `static`으로 변경 |

### Gradle 테스트 설정

```gradle
tasks.named('test') {
    useJUnitPlatform()

    // 병렬 실행 — 컨테이너 재사용/싱글톤 컨테이너와 함께 쓸 때 주의
    maxParallelForks = Runtime.runtime.availableProcessors().intdiv(2) ?: 1

    testLogging {
        events "passed", "skipped", "failed"
        showStandardStreams = true
    }
}
```

병렬 실행은 컨텍스트가 여러 개 동시에 뜨므로 메모리를 많이 먹는다. 싱글톤 컨테이너 하나를 여러 포크가 공유하면 데이터 충돌이 나니, 병렬을 켤 때는 포크별로 컨테이너를 분리하거나 스키마/스키프를 나눠야 한다.

## 참고

- [Spring Boot 테스트 공식 문서](https://docs.spring.io/spring-boot/reference/testing/)
- [Spring Framework Bean Overriding (@MockitoBean)](https://docs.spring.io/spring-framework/reference/testing/annotations/integration-spring/annotation-mockitobean.html)
- [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
- [Mockito 공식 문서](https://site.mockito.org/)
- [Spring Security Testing](https://docs.spring.io/spring-security/reference/servlet/test/index.html)
- [Testcontainers 공식 문서](https://testcontainers.com/)
- [RestAssured](https://rest-assured.io/)
- [AssertJ 공식 문서](https://assertj.github.io/doc/)
