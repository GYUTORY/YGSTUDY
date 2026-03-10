---
title: JUnit 5 + Mockito 테스트 가이드
tags: [framework, java, spring, junit, mockito, testing, unit-test, integration-test, tdd]
updated: 2026-03-08
---

# JUnit 5 + Mockito 테스트 가이드

## 개요

테스트는 코드의 신뢰성을 보장하고 리팩토링을 안전하게 한다. Spring Boot에서는 JUnit 5 + Mockito 조합이 표준이다.

```
테스트 계층 전략:
  Unit Test        — 단일 클래스/메서드 격리 테스트 (빠름, 외부 의존성 Mock)
  Integration Test — 여러 레이어를 실제로 연결해 테스트 (DB, 캐시 포함)
  E2E Test         — 전체 API를 HTTP로 호출해 테스트 (느림, 실제 환경과 동일)
```

---

## JUnit 5 핵심 어노테이션

```java
@Test                    // 테스트 메서드
@BeforeEach              // 각 테스트 전 실행
@AfterEach               // 각 테스트 후 실행
@BeforeAll               // 클래스 내 모든 테스트 전 1회 실행 (static)
@AfterAll                // 클래스 내 모든 테스트 후 1회 실행 (static)
@Disabled("이유")        // 테스트 비활성화
@DisplayName("설명")     // 테스트 이름 지정
@Nested                  // 중첩 테스트 클래스
@Tag("slow")             // 태그로 테스트 그룹화
```

### 기본 테스트 구조

```java
class OrderServiceTest {

    private OrderRepository orderRepository;
    private OrderService orderService;

    @BeforeEach
    void setUp() {
        orderRepository = mock(OrderRepository.class);
        orderService = new OrderService(orderRepository);
    }

    @Test
    @DisplayName("주문 생성 시 총 금액이 올바르게 계산된다")
    void createOrder_calculatesCorrectTotal() {
        // given
        OrderRequest request = new OrderRequest("product-1", 3, 10_000);

        // when
        Order order = orderService.createOrder(request);

        // then
        assertThat(order.getTotalAmount()).isEqualTo(30_000);
    }
}
```

### Assertions

```java
import static org.assertj.core.api.Assertions.*;

// 값 비교
assertThat(actual).isEqualTo(expected);
assertThat(actual).isNotNull();
assertThat(actual).isInstanceOf(Order.class);

// 컬렉션
assertThat(list).hasSize(3);
assertThat(list).contains("a", "b");
assertThat(list).extracting("name").containsExactly("Alice", "Bob");

// 예외
assertThatThrownBy(() -> service.doSomething(null))
    .isInstanceOf(IllegalArgumentException.class)
    .hasMessage("id는 null일 수 없습니다");

// 예외 발생 안 함
assertThatCode(() -> service.doSomething(1L)).doesNotThrowAnyException();
```

### 파라미터화 테스트

```java
@ParameterizedTest
@ValueSource(ints = {1, 2, 3})
void test_withMultipleValues(int value) {
    assertThat(value).isPositive();
}

@ParameterizedTest
@CsvSource({
    "1000, 1, 1000",
    "1000, 3, 3000",
    "500, 2, 1000",
})
void calculateTotal(int price, int quantity, int expected) {
    assertThat(price * quantity).isEqualTo(expected);
}

@ParameterizedTest
@MethodSource("provideOrders")
void test_withMethodSource(OrderRequest request, int expectedTotal) {
    Order order = orderService.createOrder(request);
    assertThat(order.getTotalAmount()).isEqualTo(expectedTotal);
}

static Stream<Arguments> provideOrders() {
    return Stream.of(
        Arguments.of(new OrderRequest("p1", 2, 1000), 2000),
        Arguments.of(new OrderRequest("p2", 1, 5000), 5000)
    );
}
```

---

## Mockito

### 기본 사용

```java
import static org.mockito.Mockito.*;
import static org.mockito.BDDMockito.*;

// Mock 생성
UserRepository userRepo = mock(UserRepository.class);

// 반환값 설정
when(userRepo.findById(1L)).thenReturn(Optional.of(new User(1L, "Alice")));
when(userRepo.findById(99L)).thenReturn(Optional.empty());

// 예외 발생 설정
when(userRepo.save(any())).thenThrow(new DataIntegrityViolationException("중복"));

// void 메서드 예외 설정
doThrow(new RuntimeException()).when(userRepo).delete(any());

// 검증 (호출 여부 확인)
verify(userRepo, times(1)).save(any(User.class));
verify(userRepo, never()).delete(any());
verify(userRepo, atLeast(1)).findById(anyLong());
```

### ArgumentCaptor — 인자 캡처

```java
@Test
void save_setsCorrectFields() {
    // given
    ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);

    // when
    userService.register("Alice", "alice@example.com");

    // then
    verify(userRepository).save(captor.capture());
    User saved = captor.getValue();
    assertThat(saved.getName()).isEqualTo("Alice");
    assertThat(saved.getEmail()).isEqualTo("alice@example.com");
    assertThat(saved.getCreatedAt()).isNotNull();
}
```

### BDD 스타일

```java
// given-when-then 구조에 맞는 BDD Mockito
given(userRepository.findById(1L)).willReturn(Optional.of(user));

userService.updateUser(1L, updateRequest);

then(userRepository).should().save(any(User.class));
then(userRepository).should(never()).delete(any());
```

---

## @ExtendWith(MockitoExtension.class)

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @InjectMocks  // @Mock 필드를 자동 주입
    private UserService userService;

    @Test
    void register_sendsWelcomeEmail() {
        // given
        given(userRepository.save(any())).willAnswer(i -> i.getArgument(0));

        // when
        userService.register("Alice", "alice@example.com");

        // then
        then(emailService).should().sendWelcome("alice@example.com");
    }
}
```

---

## Spring Boot Test

### @SpringBootTest — 통합 테스트

```java
@SpringBootTest
@Transactional  // 각 테스트 후 롤백
class OrderIntegrationTest {

    @Autowired
    private OrderService orderService;

    @Autowired
    private OrderRepository orderRepository;

    @Test
    void createOrder_persistsToDatabase() {
        // given
        OrderRequest request = new OrderRequest("product-1", 2, 1000);

        // when
        Order created = orderService.createOrder(request);

        // then
        Order found = orderRepository.findById(created.getId()).orElseThrow();
        assertThat(found.getTotalAmount()).isEqualTo(2000);
    }
}
```

### @WebMvcTest — 컨트롤러 레이어만 테스트

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean  // Spring Context의 Bean을 Mock으로 교체
    private OrderService orderService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void createOrder_returns201() throws Exception {
        // given
        OrderRequest request = new OrderRequest("product-1", 2, 1000);
        Order order = Order.builder().id(1L).totalAmount(2000).build();
        given(orderService.createOrder(any())).willReturn(order);

        // when & then
        mockMvc.perform(post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.id").value(1))
            .andExpect(jsonPath("$.totalAmount").value(2000));
    }

    @Test
    void createOrder_returns400_whenInvalidRequest() throws Exception {
        OrderRequest invalid = new OrderRequest(null, 0, -1); // 유효하지 않은 요청

        mockMvc.perform(post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalid)))
            .andExpect(status().isBadRequest());
    }
}
```

### @DataJpaTest — JPA 레포지토리만 테스트

```java
@DataJpaTest
class UserRepositoryTest {

    @Autowired
    private UserRepository userRepository;

    @Test
    void findByEmail_returnsUser() {
        // given
        User user = User.builder()
            .name("Alice")
            .email("alice@example.com")
            .build();
        userRepository.save(user);

        // when
        Optional<User> found = userRepository.findByEmail("alice@example.com");

        // then
        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("Alice");
    }

    @Test
    void findByEmail_returnsEmpty_whenNotExists() {
        Optional<User> found = userRepository.findByEmail("notexist@example.com");
        assertThat(found).isEmpty();
    }
}
```

---

## 테스트 계층 전략

```
테스트 피라미드:

        /\
       /E2E\         소수 (느림, 비용 높음)
      /------\
     /  통합  \      중간 (DB 연동, 슬라이스 테스트)
    /----------\
   /  단위 테스트 \  다수 (빠름, 격리됨)
  /--------------\

권장 비율: Unit 70% : Integration 20% : E2E 10%
```

| 어노테이션 | 범위 | 속도 | Mock 필요 |
|----------|------|------|---------|
| `@ExtendWith(MockitoExtension)` | 단일 클래스 | 매우 빠름 | 모든 의존성 |
| `@WebMvcTest` | Controller + Filter | 빠름 | Service 이하 |
| `@DataJpaTest` | Repository + JPA | 보통 | 없음 |
| `@SpringBootTest` | 전체 애플리케이션 | 느림 | 없음 (실제 Bean) |

---

## 테스트 더블 개념 정리

| 종류 | 설명 | 사용 상황 |
|------|------|---------|
| **Mock** | 호출 검증 가능한 가짜 객체 | 메서드 호출 여부 확인 필요 시 |
| **Stub** | 미리 정해진 값을 반환 | 반환값만 필요하고 검증 불필요 시 |
| **Spy** | 실제 객체 + 일부만 Mock | 일부 메서드만 Override 필요 시 |
| **Fake** | 실제 구현을 단순화한 객체 | In-memory DB, 가짜 이메일 서버 |

```java
// Spy — 실제 객체를 감싸되 일부만 변경
List<String> realList = new ArrayList<>();
List<String> spyList = spy(realList);

spyList.add("item");  // 실제 add 호출
when(spyList.size()).thenReturn(100); // size만 Mock

assertThat(spyList.get(0)).isEqualTo("item"); // 실제 값
assertThat(spyList.size()).isEqualTo(100);    // Mock 값
```

---

## 체크리스트

- [ ] 테스트 메서드명: `메서드명_시나리오_기대결과` 패턴 사용
- [ ] given-when-then 구조 유지
- [ ] 단위 테스트는 `@ExtendWith(MockitoExtension.class)` 사용
- [ ] 컨트롤러 테스트는 `@WebMvcTest` — `@SpringBootTest` 남용 금지
- [ ] 각 테스트는 독립적으로 실행 가능해야 함
- [ ] `@Transactional` 통합 테스트에서 데이터 오염 방지
- [ ] 외부 API 호출은 WireMock 등으로 Mock
