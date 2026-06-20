---
title: JUnit 5 + Mockito 단위 테스트
tags: [framework, java, spring, junit, mockito, testing, unit-test]
updated: 2026-06-20
---

# JUnit 5 + Mockito 단위 테스트

## 개요

단위 테스트는 클래스 하나, 메서드 하나를 외부 의존성에서 떼어내 검증한다. Repository나 외부 API를 직접 부르지 않고 Mockito로 가짜 객체를 끼워 넣어 입력과 출력만 본다. Spring Boot 프로젝트라면 `spring-boot-starter-test`에 JUnit 5, Mockito, AssertJ가 같이 딸려 오므로 의존성을 따로 추가할 일은 거의 없다.

여기서는 단위 테스트, 그러니까 `@ExtendWith(MockitoExtension.class)` 기반 테스트와 Mockito를 쓰면서 실제로 막히는 지점을 다룬다. `@WebMvcTest`, `@DataJpaTest`, `@SpringBootTest` 같은 슬라이스 테스트는 [Spring_Test.md](../Spring/Spring_Test.md)에서 따로 정리한다.

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

`@BeforeAll`과 `@AfterAll`은 static이어야 한다. 인스턴스 메서드로 선언하면 `@TestInstance(Lifecycle.PER_CLASS)`를 붙이지 않는 한 실행되지 않고 컴파일 단계에서 막힌다. 처음 JUnit 4에서 넘어오면 `@Before` → `@BeforeEach`, `@BeforeClass` → `@BeforeAll`로 이름이 바뀐 걸 자주 헷갈린다.

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

`mock()`을 `@BeforeEach`에서 직접 만들고 생성자로 주입하는 방식은 `@ExtendWith(MockitoExtension.class)` + `@InjectMocks`보다 코드는 길지만 주입 방식이 명시적이라 디버깅하기 쉽다. 의존성이 두세 개면 이쪽이 오히려 낫다.

### Assertions

AssertJ를 쓴다. JUnit 기본 `assertEquals`보다 체이닝이 읽기 편하고 실패 메시지가 구체적이다.

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

`assertThat(actual).isEqualTo(expected)`에서 인자 순서를 바꿔 쓰면 실패 메시지의 expected/actual이 거꾸로 나와 디버깅할 때 헷갈린다. 검증 대상이 항상 `assertThat()` 안에 들어간다.

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

`@MethodSource`가 가리키는 메서드는 static이어야 한다. 인스턴스 메서드로 두려면 클래스에 `@TestInstance(Lifecycle.PER_CLASS)`를 붙여야 한다. `@CsvSource`에서 빈 문자열과 null을 구분해야 하면 `@CsvSource(nullValues = "NULL")` 같은 옵션을 써야 한다. 기본값으로는 빈 칸이 빈 문자열로 들어간다.

---

## Mockito 기본

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

// 검증
verify(userRepo, times(1)).save(any(User.class));
verify(userRepo, never()).delete(any());
verify(userRepo, atLeast(1)).findById(anyLong());
```

void 메서드는 `when(...).thenThrow(...)`로 stub할 수 없다. void는 반환값이 없어 `when()`에 넘길 게 없으므로 `doThrow().when()` 형태를 써야 한다. void 메서드를 mock할 때는 항상 `doXxx().when()` 계열을 쓴다고 외워두는 편이 낫다.

### @ExtendWith(MockitoExtension.class)

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @InjectMocks
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

`@ExtendWith(MockitoExtension.class)`를 빼먹으면 `@Mock` 필드가 전부 null이 된다. 어노테이션은 붙였는데 NPE가 난다면 extension을 빠뜨렸는지부터 본다.

---

## 실무에서 자주 막히는 지점

### UnnecessaryStubbingException과 strict/lenient

`MockitoExtension`은 기본이 STRICT_STUBS 모드다. stub을 선언해놓고 테스트에서 한 번도 호출하지 않으면 테스트가 실패한다.

```java
@Test
void someTest() {
    // 이 stub을 아래 코드에서 안 쓰면 UnnecessaryStubbingException
    when(userRepository.findById(1L)).thenReturn(Optional.of(user));

    userService.doSomethingElse();  // findById를 안 부름
}
```

이게 처음엔 짜증나는데, 실제로는 쓸모가 있다. 리팩토링으로 메서드 호출이 사라졌는데 stub만 남는 경우를 잡아준다. 죽은 stub을 그대로 두면 테스트가 무엇을 검증하는지 흐려진다.

특정 stub만 검사에서 빼고 싶으면 `lenient()`를 쓴다.

```java
lenient().when(userRepository.findByEmail(anyString()))
    .thenReturn(Optional.empty());
```

`@BeforeEach`에서 여러 테스트가 공유하는 stub을 깔아놓는 경우, 일부 테스트가 그 stub을 안 쓰면 STRICT 모드에서 다 터진다. 이럴 때 공유 stub에 `lenient()`를 붙이거나, 클래스 전체를 `@MockitoSettings(strictness = Strictness.LENIENT)`로 풀 수 있다. 다만 전체를 lenient로 푸는 건 죽은 stub 경고를 통째로 꺼버리는 거라 권하지 않는다. 문제 되는 stub만 골라서 푼다.

### ArgumentMatchers 섞어 쓰기 — InvalidUseOfMatchersException

`any()`, `eq()` 같은 matcher와 실제 값을 한 호출에 섞으면 터진다.

```java
// 터진다: InvalidUseOfMatchersException
when(service.transfer(any(), 1000L)).thenReturn(true);

// 정상: 전부 matcher
when(service.transfer(any(), eq(1000L))).thenReturn(true);
```

Mockito의 matcher는 인자별로 값을 비교하는 게 아니라 호출 시점에 스택에 matcher를 쌓아두고 메서드 호출이 끝나면 꺼내 쓰는 방식이다. 한 인자라도 matcher를 쓰면 나머지 인자도 전부 matcher여야 한다. 실제 값을 그대로 넘기고 싶으면 `eq(1000L)`로 감싼다.

에러 메시지가 가끔 엉뚱한 다음 테스트에서 뜬다. matcher가 스택에 남아 다음 stub 선언에서 터지기 때문이다. `InvalidUseOfMatchersException`이 났는데 해당 줄이 멀쩡해 보이면 바로 위 stub에서 matcher를 섞어 썼는지 본다.

### thenReturn vs thenAnswer

`thenReturn`은 stub 선언 시점에 값이 한 번 평가되어 고정된다. `thenAnswer`는 호출될 때마다 람다가 실행된다.

```java
// 매 호출마다 같은 객체를 돌려준다. 호출 인자를 못 본다
when(repo.save(any())).thenReturn(fixedOrder);

// 호출된 인자를 그대로 돌려준다 (save 후 받은 엔티티를 그대로 쓸 때)
when(repo.save(any())).thenAnswer(inv -> inv.getArgument(0));

// 호출 인자를 가공해 돌려준다
when(repo.save(any(User.class))).thenAnswer(inv -> {
    User u = inv.getArgument(0);
    return new User(100L, u.getName());  // ID가 부여된 것처럼
});
```

JPA `save()`처럼 입력 엔티티에 ID를 붙여 돌려주는 메서드를 mock할 때 `thenReturn(고정객체)`를 쓰면, 테스트마다 다른 입력을 줘도 같은 객체가 나와 검증이 무의미해진다. 이럴 땐 `thenAnswer(inv -> inv.getArgument(0))`로 입력을 되돌려주는 게 맞다.

연속 호출에서 매번 다른 값을 주고 싶으면 `thenReturn`을 이어 붙인다.

```java
when(counter.next()).thenReturn(1, 2, 3);
// 첫 호출 1, 둘째 2, 셋째 3, 이후로는 계속 3

when(repo.findById(1L))
    .thenReturn(Optional.empty())       // 첫 조회: 없음
    .thenReturn(Optional.of(user));     // 재시도 후: 있음
```

### @Mock과 @Spy 혼용, @InjectMocks 주입 실패

`@Spy`는 실제 객체를 감싸 일부 메서드만 stub한다. `@Mock`과 같이 `@InjectMocks` 대상에 주입할 수 있지만 주의할 점이 있다.

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Spy
    private DiscountPolicy discountPolicy = new DefaultDiscountPolicy();

    @InjectMocks
    private OrderService orderService;
}
```

`@Spy` 필드는 직접 인스턴스를 만들어 초기화해줘야 한다. `@Spy private DiscountPolicy policy;`처럼 인터페이스 타입만 두고 인스턴스를 안 주면 Mockito가 무엇을 감쌀지 몰라 주입에 실패한다. 구체 클래스라면 기본 생성자로 자동 생성해주지만, 의존성이 있는 클래스나 인터페이스는 직접 `= new ...()`로 채워야 한다.

`@InjectMocks`가 주입에 실패해도 예외를 던지지 않고 그냥 필드를 null로 둔다. 그래서 테스트 실행 중 NPE로 나타난다. 주입이 안 됐다 싶으면 대상 클래스의 생성자/필드 타입과 `@Mock`/`@Spy` 필드 타입이 정확히 맞는지 본다. 같은 타입 mock이 두 개 있으면 필드명으로 매칭하는데, 필드명이 안 맞으면 엉뚱하게 주입된다.

### @InjectMocks의 주입 순서

`@InjectMocks`는 세 가지 방식을 순서대로 시도한다.

1. 생성자 주입: 인자가 가장 많은 생성자를 골라 mock을 채운다
2. 세터 주입: 생성자로 안 되면 setter
3. 필드 주입: 그래도 안 되면 필드에 리플렉션으로 직접 꽂는다

생성자가 하나면 그걸 쓴다. 문제는 생성자가 여러 개일 때다. Mockito는 인자 수가 가장 많은 생성자를 고르는데, 그 생성자 인자 중 mock으로 채울 수 없는 게 있으면 해당 자리에 null이 들어간다. 생성자 주입을 쓰는 클래스라면 테스트가 의도한 생성자를 타는지 확인해야 한다. `final` 필드로 생성자 주입을 강제하는 클래스는 필드 주입이 불가능하므로 생성자 매칭이 안 되면 그냥 null이 된다.

직접 `new`로 만들어 주입하는 게 가장 확실하다. 의존성이 많지 않다면 `@InjectMocks` 대신 `@BeforeEach`에서 생성자 호출로 조립하는 방식을 권한다.

### static 메서드 mocking — mockito-inline

`LocalDateTime.now()`나 유틸 클래스의 static 메서드를 mock하려면 `mockito-inline`이 필요하다. Mockito 5부터는 기본 mock-maker가 inline이라 별도 의존성이 필요 없지만, Mockito 3~4를 쓰는 프로젝트는 의존성을 추가해야 한다.

```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-inline</artifactId>
    <scope>test</scope>
</dependency>
```

```java
@Test
void createsOrderWithFixedTime() {
    LocalDateTime fixed = LocalDateTime.of(2026, 6, 20, 10, 0);

    try (MockedStatic<LocalDateTime> mocked = mockStatic(LocalDateTime.class)) {
        mocked.when(LocalDateTime::now).thenReturn(fixed);

        Order order = orderService.create();

        assertThat(order.getCreatedAt()).isEqualTo(fixed);
    }
    // try 블록을 벗어나면 LocalDateTime.now()가 원래대로 돌아온다
}
```

`mockStatic`은 반드시 try-with-resources로 닫아야 한다. 안 닫으면 그 static mock이 같은 스레드의 다음 테스트까지 살아남아, 전혀 관계없는 테스트가 깨진다. 이런 오염은 단독 실행하면 통과하고 전체 실행하면 깨지는 식이라 원인 찾기가 고약하다.

static mock은 mock을 만든 스레드에서만 적용된다. 테스트가 별도 스레드를 띄워 static 메서드를 부르면 mock이 안 먹는다.

`final` 클래스나 `final` 메서드도 inline mock-maker가 있어야 mock된다. 시간 의존 로직은 사실 `Clock`을 주입받게 설계하면 static mock 없이 `Clock.fixed()`로 테스트할 수 있다. 새로 짜는 코드라면 그쪽이 깔끔하다.

### InOrder — 호출 순서 검증

여러 mock에 걸친 호출 순서를 검증한다. 보상 트랜잭션이나 결제처럼 순서가 중요한 로직에 쓴다.

```java
@Test
void payment_locksBeforeCharge() {
    paymentService.pay(orderId);

    InOrder inOrder = inOrder(lockManager, paymentGateway);
    inOrder.verify(lockManager).lock(orderId);
    inOrder.verify(paymentGateway).charge(any());
    inOrder.verify(lockManager).unlock(orderId);
}
```

`InOrder`는 검증한 호출들의 상대 순서만 본다. 중간에 다른 호출이 끼어 있어도 통과한다. 검증하지 않은 호출까지 막으려면 `inOrder.verifyNoMoreInteractions()`를 끝에 둔다.

### verify timeout — 비동기 호출 검증

`@Async`나 별도 스레드에서 일어나는 호출은 테스트 스레드가 먼저 끝나버려 `verify`가 호출을 못 본다. `timeout`을 주면 지정 시간까지 폴링하며 기다린다.

```java
@Test
void sendsEmailAsynchronously() {
    notificationService.notifyAsync(user);

    // 최대 1초 동안 호출을 기다린다. 호출이 잡히면 즉시 통과
    verify(emailService, timeout(1000)).send(any());

    // 1초 안에 정확히 1번 호출되는지
    verify(emailService, timeout(1000).times(1)).send(any());
}
```

`Thread.sleep`으로 고정 대기하는 것보다 낫다. 호출이 잡히는 즉시 넘어가므로 테스트가 빠르고, 느린 CI에서도 타임아웃 여유 안에서 잘 돌아간다. `after(1000)`은 timeout과 달리 1초를 꽉 채워 기다린 뒤 검증한다. "1초 동안 호출이 한 번도 없어야 한다" 같은 검증에 쓴다.

### ArgumentCaptor — 다중 호출 캡처

캡처는 검증할 인자가 복잡하거나 객체 내부 필드를 봐야 할 때 쓴다.

```java
@Test
void save_setsCorrectFields() {
    ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);

    userService.register("Alice", "alice@example.com");

    verify(userRepository).save(captor.capture());
    User saved = captor.getValue();
    assertThat(saved.getName()).isEqualTo("Alice");
    assertThat(saved.getEmail()).isEqualTo("alice@example.com");
}
```

같은 메서드가 여러 번 호출되면 `getValue()`는 마지막 인자만 준다. 전부 보려면 `getAllValues()`로 리스트를 받는다.

```java
@Test
void batchSave_capturesAllUsers() {
    userService.registerAll(List.of("Alice", "Bob", "Charlie"));

    ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
    verify(userRepository, times(3)).save(captor.capture());

    List<User> allSaved = captor.getAllValues();
    assertThat(allSaved).extracting(User::getName)
        .containsExactly("Alice", "Bob", "Charlie");
}
```

`captor.capture()`는 stub(`when`)이 아니라 검증(`verify`)에서 쓴다. stub에서 캡처하면 호출 순서 문제로 값이 안 잡히는 경우가 있다. 캡처는 verify에서만 한다고 생각하는 편이 안전하다.

캡처를 verify 안에서 `assertThat(captor.capture())`처럼 한 줄로 쓰고 싶은 유혹이 있는데, 검증과 캡처를 분리하는 게 읽기 좋다. `verify(...).save(captor.capture())`로 호출을 검증하고, 그 다음 줄에서 `captor.getValue()`로 꺼내 단언한다.

### BDD 스타일

`given/willReturn`, `then/should`로 given-when-then 흐름에 맞춘다. 동작은 `when/thenReturn`과 같고 읽는 맛만 다르다.

```java
given(userRepository.findById(1L)).willReturn(Optional.of(user));

userService.updateUser(1L, updateRequest);

then(userRepository).should().save(any(User.class));
then(userRepository).should(never()).delete(any());
```

한 프로젝트 안에서 `when/verify`와 `given/then`을 섞으면 읽는 사람이 헷갈린다. 팀에서 하나로 정해 쓰는 게 낫다.

---

## 테스트 더블 정리

| 종류 | 설명 | 사용 상황 |
|------|------|---------|
| Mock | 호출 검증 가능한 가짜 객체 | 메서드 호출 여부 확인 필요 시 |
| Stub | 미리 정해진 값을 반환 | 반환값만 필요하고 검증 불필요 시 |
| Spy | 실제 객체 + 일부만 Mock | 일부 메서드만 override 필요 시 |
| Fake | 실제 구현을 단순화한 객체 | in-memory DB, 가짜 이메일 서버 |

```java
// Spy — 실제 객체를 감싸되 일부만 변경
List<String> realList = new ArrayList<>();
List<String> spyList = spy(realList);

spyList.add("item");  // 실제 add 호출

// 주의: spy는 thenReturn보다 doReturn을 쓴다
doReturn(100).when(spyList).size();

assertThat(spyList.get(0)).isEqualTo("item"); // 실제 값
assertThat(spyList.size()).isEqualTo(100);    // Mock 값
```

Spy에서 `when(spyList.size()).thenReturn(100)`을 쓰면 `spyList.size()`가 stub 선언 시점에 실제로 호출된다. 빈 리스트면 괜찮지만 `spyList.get(0)`처럼 실제 호출이 예외를 던지는 메서드를 stub하려 하면 stub을 거는 순간 예외가 터진다. Spy를 stub할 때는 `doReturn(...).when(spy).method()`를 써서 실제 호출을 막아야 한다.

---

## 단위 테스트와 슬라이스 테스트의 경계

단위 테스트는 Spring 컨텍스트를 띄우지 않는다. `@ExtendWith(MockitoExtension.class)`만 있으면 컨텍스트 로딩 없이 millisecond 단위로 끝난다. 의존성을 전부 mock으로 채우고 한 클래스의 로직만 검증한다. 비즈니스 로직, 계산, 분기, 예외 처리는 전부 여기서 잡는다.

Repository의 실제 쿼리, Controller의 직렬화와 검증, 컨텍스트 로딩이 필요한 검증은 슬라이스 테스트나 통합 테스트의 영역이다. 이쪽은 컨텍스트를 띄우므로 느리다. `@WebMvcTest`, `@DataJpaTest`, `@SpringBootTest`의 사용법과 주의점은 [Spring_Test.md](../Spring/Spring_Test.md)에 정리돼 있다.

비율로 따지면 빠른 단위 테스트가 다수를 차지하고, 슬라이스와 통합 테스트가 그 위에 얇게 얹힌다. 단위 테스트로 잡을 수 있는 로직을 매번 `@SpringBootTest`로 검증하면 전체 테스트 시간이 금방 분 단위로 늘어난다. mock으로 떼어낼 수 있는 건 단위 테스트로 내리는 게 빌드 속도에 직결된다.

| 어노테이션 | 범위 | 속도 | 컨텍스트 |
|----------|------|------|---------|
| `@ExtendWith(MockitoExtension)` | 단일 클래스 | 매우 빠름 | 안 띄움 |
| `@WebMvcTest` | Controller + Filter | 빠름 | 일부 슬라이스 |
| `@DataJpaTest` | Repository + JPA | 보통 | 일부 슬라이스 |
| `@SpringBootTest` | 전체 애플리케이션 | 느림 | 전체 |
