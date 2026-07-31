---
title: 타임존 테스트
tags: [timezone, testing, clock, dst, java, spring, nestjs, jest, backend]
updated: 2026-07-31
---

# 타임존 테스트

## 왜 타임존 테스트가 어려운가

타임존 버그는 재현 조건이 까다롭다. DST 전환 직전, 자정, 월말, 윤년 같은 경계에서만 터지는데, 그 조건을 재현하려면 시스템 시각을 통제해야 한다.

근본 문제는 프로덕션 코드 내부에서 `Instant.now()`나 `new Date()`를 직접 호출한다는 것이다. 이 코드는 시스템 시계에 직접 묶여 있어 테스트에서 제어할 방법이 없다. 특정 시각 기준 동작을 검증하려면 OS 시계를 직접 건드리거나, 실제 그 시각이 올 때까지 기다려야 한다. 둘 다 현실적이지 않다.

해결 방향은 시각을 제공하는 객체 자체를 외부에서 주입받는 것이다. Java에서는 `Clock`, Node.js/Jest에서는 `jest.useFakeTimers()`가 그 역할을 한다.

## Java: Clock 주입 패턴

`java.time.Clock`은 Java 8부터 있다. `Instant.now(clock)`처럼 Clock 인스턴스를 받아 현재 시각을 계산한다. 프로덕션에서는 `Clock.systemUTC()`를 쓰고, 테스트에서는 `Clock.fixed()`로 고정된 시각을 제공한다.

서비스 코드에서 `Instant.now()`를 직접 호출하는 순간 그 코드는 테스트에서 제어 불가능한 상태가 된다.

```java
// 테스트에서 제어 불가
public Order createOrder(Long userId) {
    Instant now = Instant.now();
    return new Order(userId, now);
}
```

Clock을 생성자로 주입받으면 테스트에서 원하는 시각을 넣을 수 있다.

```java
@Service
public class OrderService {
    private final Clock clock;
    private final OrderRepository orderRepository;

    public OrderService(Clock clock, OrderRepository orderRepository) {
        this.clock = clock;
        this.orderRepository = orderRepository;
    }

    public Order createOrder(Long userId) {
        Instant now = Instant.now(clock);
        return orderRepository.save(new Order(userId, now));
    }
}
```

프로덕션 Bean은 이렇게 등록한다.

```java
@Configuration
public class ClockConfig {
    @Bean
    public Clock clock() {
        return Clock.systemUTC();
    }
}
```

### 단위 테스트에서 Clock.fixed() 사용

Spring Context 없이 단위 테스트를 작성할 때는 `Clock.fixed()`로 만든 인스턴스를 생성자에 직접 넣는다.

```java
class OrderServiceTest {

    @Test
    void 주문_생성_시각이_UTC로_저장된다() {
        Instant fixedTime = Instant.parse("2024-03-15T09:00:00Z");
        Clock fixedClock = Clock.fixed(fixedTime, ZoneOffset.UTC);

        OrderRepository mockRepo = mock(OrderRepository.class);
        OrderService service = new OrderService(fixedClock, mockRepo);
        when(mockRepo.save(any())).thenAnswer(i -> i.getArgument(0));

        Order order = service.createOrder(1L);

        assertThat(order.getCreatedAt()).isEqualTo(fixedTime);
    }
}
```

`Clock.fixed()`는 호출할 때마다 같은 `Instant`를 반환한다. 시각이 흐르지 않기 때문에 "현재 시각" 기준 로직을 예측 가능하게 만든다.

### 시각을 진행시키는 테스트: Clock.offset()

"30일 후 만료" 같이 시간 경과에 따른 동작을 검증할 때는 `Clock.offset()`을 쓴다.

```java
@Test
void 30일_후_쿠폰이_만료된다() {
    Instant issueTime = Instant.parse("2024-01-01T00:00:00Z");
    Clock issueClock = Clock.fixed(issueTime, ZoneOffset.UTC);

    Coupon coupon = couponService.issue(userId, issueClock);
    assertThat(coupon.isExpired(issueClock)).isFalse();

    Clock day29 = Clock.offset(issueClock, Duration.ofDays(29));
    assertThat(coupon.isExpired(day29)).isFalse();

    Clock day30 = Clock.offset(issueClock, Duration.ofDays(30));
    assertThat(coupon.isExpired(day30)).isTrue();
}
```

`Clock.offset(base, duration)`은 base Clock에서 duration만큼 이동한 새 Clock을 반환한다. 원본 Clock은 변하지 않아서 테스트 간 상태 공유 문제가 없다.

## Spring TestContext에서 고정 Clock 빈 등록

통합 테스트에서는 실제 Spring Context를 띄우면서 시각만 고정해야 하는 경우가 많다. `@TestConfiguration`으로 테스트 전용 Clock 빈을 등록한다.

```java
@SpringBootTest
class OrderIntegrationTest {

    @TestConfiguration
    static class TestClockConfig {
        @Bean
        @Primary
        public Clock testClock() {
            return Clock.fixed(
                Instant.parse("2024-11-03T05:00:00Z"),
                ZoneOffset.UTC
            );
        }
    }

    @Autowired
    private OrderService orderService;

    @Test
    void DST_전환_직후_주문이_정상_저장된다() {
        Order order = orderService.createOrder(1L);
        assertThat(order.getCreatedAt()).isEqualTo(Instant.parse("2024-11-03T05:00:00Z"));
    }
}
```

`@Primary`를 붙이지 않으면 프로덕션 `Clock` 빈과 충돌해 `NoUniqueBeanDefinitionException`이 발생한다. `@Bean(name = "clock")`으로 이름을 명시하는 방식도 같은 효과다.

테스트마다 다른 시각을 써야 한다면 `@BeforeEach`에서 Clock을 교체하려는 시도를 하게 되는데, Spring Context를 공유하는 상황에서 빈을 교체하기 어렵다. 이런 경우 두 가지 방법이 있다.

첫 번째, 테스트 클래스마다 별도 `@TestConfiguration`을 정의한다. 테스트 클래스 수가 많아지면 관리가 번거롭지만 Context 격리가 명확하다.

두 번째, `Clock`을 Mockito로 모킹해서 `when(clock.instant()).thenReturn(...)` 식으로 테스트마다 다른 시각을 지정한다. 이 방법은 `@MockBean`을 쓸 때 Context를 재사용하면서도 시각을 바꿀 수 있다.

```java
@SpringBootTest
class OrderServiceMockClockTest {

    @MockBean
    private Clock clock;

    @Autowired
    private OrderService orderService;

    @Test
    void 특정_시각_기준_주문_처리() {
        Instant target = Instant.parse("2024-12-31T14:59:59Z");
        when(clock.instant()).thenReturn(target);
        when(clock.getZone()).thenReturn(ZoneOffset.UTC);

        Order order = orderService.createOrder(1L);

        assertThat(order.getCreatedAt()).isEqualTo(target);
    }
}
```

## DST 전환 시점 테스트

한국은 DST를 쓰지 않아 직접 경험하기 어렵다. 미국, 유럽 사용자가 있는 서비스라면 반드시 커버해야 한다.

미국 동부 기준으로 봄 전환(EST → EDT)은 2시에서 3시로 점프하고, 가을 전환(EDT → EST)은 2시에서 1시로 되돌아간다.

### 봄 전환: 존재하지 않는 시간

2024년 3월 10일 봄 전환에서 `America/New_York` 기준 02:00~02:59 구간 자체가 없다. 이 시간대를 기준으로 동작하는 스케줄러나 날짜 계산 로직이 어떻게 처리하는지 확인한다.

```java
@Test
void 봄_DST_전환_직후_배치가_정상_실행된다() {
    // 봄 전환 직후: EDT 03:00 = UTC 07:00
    Instant afterDst = Instant.parse("2024-03-10T07:00:00Z");
    Clock dstClock = Clock.fixed(afterDst, ZoneOffset.UTC);

    // 존재하지 않는 로컬 타임(2:30 AM)을 ZonedDateTime으로 만들면
    // Java는 예외 없이 DST 이후로 조정한다
    ZoneId newYork = ZoneId.of("America/New_York");
    LocalDateTime nonExistent = LocalDateTime.of(2024, 3, 10, 2, 30);
    ZonedDateTime adjusted = ZonedDateTime.of(nonExistent, newYork);

    // 존재하지 않는 2:30 AM은 3:30 AM으로 조정됨
    assertThat(adjusted.getHour()).isEqualTo(3);
    assertThat(adjusted.getOffset()).isEqualTo(ZoneOffset.of("-04:00")); // EDT

    // 배치 스케줄러가 예외 없이 실행되는지 확인
    batchScheduler.setClock(dstClock);
    assertThatCode(() -> batchScheduler.runDailyBatch()).doesNotThrowAnyException();
}
```

`ZonedDateTime.of(LocalDateTime, ZoneId)`는 존재하지 않는 시각에 대해 예외를 던지지 않고 DST 이후로 자동 조정한다. 이 동작을 모르고 "2:30 AM에 실행"을 로컬 타임으로 스케줄링하면 봄 전환일에 3:30 AM에 실행된다. UTC 기준으로 스케줄링하면 이 문제가 없다.

### 가을 전환: 중복되는 시간

2024년 11월 3일 가을 전환에서 EDT 1:00 AM → EST 1:00 AM으로 되돌아간다. 로컬 타임 1:00~1:59 구간이 두 번 존재한다.

```java
@Test
void 가을_DST_전환_중복_시각이_UTC로_구분된다() {
    ZoneId newYork = ZoneId.of("America/New_York");

    // 첫 번째 1:30 AM (EDT, UTC-4) = UTC 05:30
    Instant firstOccurrence = Instant.parse("2024-11-03T05:30:00Z");
    // 두 번째 1:30 AM (EST, UTC-5) = UTC 06:30
    Instant secondOccurrence = Instant.parse("2024-11-03T06:30:00Z");

    ZonedDateTime first = firstOccurrence.atZone(newYork);
    ZonedDateTime second = secondOccurrence.atZone(newYork);

    // 로컬 타임은 같지만 UTC는 다름
    assertThat(first.toLocalDateTime()).isEqualTo(second.toLocalDateTime());
    assertThat(first.toInstant()).isNotEqualTo(second.toInstant());

    // UTC로 저장된 주문은 순서가 보장됨
    Order order1 = createOrderAt(firstOccurrence);
    Order order2 = createOrderAt(secondOccurrence);
    assertThat(order1.getCreatedAt()).isBefore(order2.getCreatedAt());
}
```

로컬 타임으로만 저장한 경우 `2024-11-03T01:30:00`이 두 건 존재하고 어느 것이 먼저인지 알 수 없다. UTC로 저장하면 UTC 값 자체가 다르므로 순서가 명확하다. DST 전환 버그 대부분이 로컬 타임 저장에서 비롯된다.

## 날짜 경계 테스트

### 자정

"오늘 주문 내역 조회"처럼 특정 날짜를 기준으로 범위를 잡는 쿼리는 자정에서 오작동하기 쉽다. 사용자 타임존 기준 자정과 UTC 자정이 다르기 때문이다.

KST 기준 자정(00:00)은 UTC 기준 전날 15:00다. UTC 기준으로 날짜 범위를 잡으면 KST 사용자 입장에서 "오늘"이 아닌 데이터가 포함된다.

```java
@Test
void 자정_직전_주문이_해당_날짜에_포함된다() {
    ZoneId seoul = ZoneId.of("Asia/Seoul");

    // KST 2024-03-15 23:59:59 = UTC 14:59:59
    Instant justBeforeMidnight = Instant.parse("2024-03-15T14:59:59Z");
    // KST 2024-03-16 00:00:00 = UTC 15:00:00
    Instant midnight = Instant.parse("2024-03-15T15:00:00Z");

    Order lateOrder = createOrderAt(justBeforeMidnight);
    Order nextDayOrder = createOrderAt(midnight);

    LocalDate targetDate = LocalDate.of(2024, 3, 15);
    Instant startOfDay = targetDate.atStartOfDay(seoul).toInstant();
    Instant endOfDay = targetDate.plusDays(1).atStartOfDay(seoul).toInstant();

    List<Order> orders = orderRepository.findByCreatedAtBetween(startOfDay, endOfDay);

    assertThat(orders).contains(lateOrder);
    assertThat(orders).doesNotContain(nextDayOrder);
}
```

날짜 범위 계산은 사용자 타임존을 기준으로 `atStartOfDay(zoneId).toInstant()`로 변환해서 UTC로 넘겨야 한다. 서비스 레이어에서 이 변환을 담당하고, 쿼리 파라미터는 항상 UTC `Instant`다.

### 월말, 연말

월별 통계 집계나 정산 배치는 월말 경계에서 실수가 잦다. 윤년, 30일인 달, 12월 말을 각각 케이스로 넣는다.

```java
@ParameterizedTest
@MethodSource("monthEndBoundaries")
void 월말_날짜_경계에서_집계가_다음_달로_넘어간다(Instant monthEnd, Instant nextMonthStart) {
    Clock endClock = Clock.fixed(monthEnd, ZoneOffset.UTC);
    Clock startClock = Clock.fixed(nextMonthStart, ZoneOffset.UTC);

    MonthlyStats endStats = statsService.aggregateMonthly(endClock);
    MonthlyStats startStats = statsService.aggregateMonthly(startClock);

    assertThat(endStats.getYearMonth()).isNotEqualTo(startStats.getYearMonth());
}

static Stream<Arguments> monthEndBoundaries() {
    return Stream.of(
        Arguments.of(
            Instant.parse("2024-01-31T23:59:59Z"),
            Instant.parse("2024-02-01T00:00:00Z")
        ),
        Arguments.of(
            Instant.parse("2024-02-29T23:59:59Z"), // 윤년
            Instant.parse("2024-03-01T00:00:00Z")
        ),
        Arguments.of(
            Instant.parse("2023-02-28T23:59:59Z"), // 평년
            Instant.parse("2023-03-01T00:00:00Z")
        ),
        Arguments.of(
            Instant.parse("2024-12-31T23:59:59Z"),
            Instant.parse("2025-01-01T00:00:00Z")
        )
    );
}
```

KST 기준 월말이 UTC 기준 전날이라는 점도 별도로 확인한다. KST 1월 31일 마지막 순간은 UTC 기준 1월 31일 14:59:59다. KST 2월 1일 자정은 UTC 기준 1월 31일 15:00:00이다. 월별 통계를 UTC 기준으로 끊으면 KST 사용자 입장에서 기준 날짜가 다르게 보인다.

```java
@Test
void KST_기준_월말이_UTC_기준_전날임을_고려한다() {
    ZoneId seoul = ZoneId.of("Asia/Seoul");

    // KST 1월 31일 23:59:59
    LocalDateTime kstLastMoment = LocalDateTime.of(2024, 1, 31, 23, 59, 59);
    Instant utcEquivalent = kstLastMoment.atZone(seoul).toInstant();

    // UTC로는 1월 31일 14:59:59
    assertThat(utcEquivalent).isEqualTo(Instant.parse("2024-01-31T14:59:59Z"));

    // KST 2월 1일 자정
    LocalDateTime kstFebFirst = LocalDateTime.of(2024, 2, 1, 0, 0, 0);
    Instant utcFebFirst = kstFebFirst.atZone(seoul).toInstant();

    // UTC로는 1월 31일 15:00:00
    assertThat(utcFebFirst).isEqualTo(Instant.parse("2024-01-31T15:00:00Z"));
}
```

## Node.js/NestJS: jest.useFakeTimers

Jest의 `useFakeTimers()`는 `Date`, `setTimeout`, `setInterval` 등 시각 관련 전역 객체를 가로챈다. `setSystemTime()`으로 원하는 시각을 주입한다.

```typescript
describe('OrderService', () => {
    let service: OrderService;

    beforeEach(async () => {
        const module = await Test.createTestingModule({
            providers: [OrderService],
        }).compile();
        service = module.get<OrderService>(OrderService);
    });

    afterEach(() => {
        jest.useRealTimers(); // 반드시 복원
    });

    it('주문 생성 시각이 UTC ISO 형식으로 저장된다', () => {
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2024-03-15T09:00:00Z'));

        const order = service.createOrder(1);

        expect(order.createdAt).toBe('2024-03-15T09:00:00.000Z');
    });
});
```

`afterEach`에서 `jest.useRealTimers()`를 빠뜨리면 이후 테스트 파일에서 시각이 고정된 채 실행된다. Jest 워커 프로세스를 공유할 때 다른 테스트 파일에도 영향을 준다.

### NestJS에서 타임존 기준 날짜 테스트

Node.js `Date`의 로컬 시각 계산은 `TZ` 환경변수를 따른다. 테스트에서 특정 타임존 기준 동작을 검증하려면 `TZ`를 설정한다.

```typescript
describe('DailyReportService', () => {
    let service: DailyReportService;
    const originalTZ = process.env.TZ;

    beforeAll(() => {
        process.env.TZ = 'Asia/Seoul';
    });

    afterAll(() => {
        process.env.TZ = originalTZ;
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    it('KST 자정 기준으로 일별 리포트를 집계한다', () => {
        // KST 2024-03-15 00:00:00 = UTC 2024-03-14 15:00:00
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2024-03-14T15:00:00Z'));

        const report = service.generateDailyReport();

        expect(report.date).toBe('2024-03-15');
    });
});
```

`process.env.TZ` 변경은 테스트 파일 실행 초기에 해야 한다. Node.js가 프로세스 시작 시 `TZ`를 읽어서 내부에 캐시하기 때문에 실행 도중 변경이 반영되지 않을 수 있다. Jest 설정에서 `--runInBand` 옵션이나 별도 워커로 격리하거나, `jest.config.js`의 `testEnvironment`를 분리하면 더 안전하다.

### 날짜 경계 케이스 일괄 처리

경계값 케이스는 `it.each()`로 한꺼번에 다룬다.

```typescript
describe('날짜 경계 처리', () => {
    afterEach(() => {
        jest.useRealTimers();
    });

    const boundaries = [
        { desc: 'KST 자정 직전', utc: '2024-03-15T14:59:59.999Z', expected: '2024-03-15' },
        { desc: 'KST 자정',      utc: '2024-03-15T15:00:00.000Z', expected: '2024-03-16' },
        { desc: 'KST 1월 말',    utc: '2024-01-31T14:59:59.999Z', expected: '2024-01-31' },
        { desc: 'KST 2월 초',    utc: '2024-01-31T15:00:00.000Z', expected: '2024-02-01' },
        { desc: 'KST 연말',      utc: '2024-12-31T14:59:59.999Z', expected: '2024-12-31' },
        { desc: 'KST 연초',      utc: '2024-12-31T15:00:00.000Z', expected: '2025-01-01' },
        { desc: '윤년 2월 말',   utc: '2024-02-29T14:59:59.999Z', expected: '2024-02-29' },
    ];

    it.each(boundaries)('$desc에 KST 날짜를 올바르게 반환한다', ({ utc, expected }) => {
        jest.useFakeTimers();
        jest.setSystemTime(new Date(utc));

        const result = dateService.getTodayInKST();

        expect(result).toBe(expected);
    });
});
```

케이스를 상수 배열로 분리해두면 나중에 케이스 추가가 편하다. 자정, 월말, 연말을 한 번에 확인할 수 있어서 놓치는 경계가 없다.

### DST 전환 테스트

```typescript
describe('미국 동부 DST 전환', () => {
    afterEach(() => jest.useRealTimers());

    it('봄 전환: 스케줄러가 존재하지 않는 2시 처리를 예외 없이 통과한다', () => {
        // 2024-03-10 봄 전환: EDT로 전환 직후 UTC 07:00
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2024-03-10T07:00:00Z'));

        expect(() => scheduler.runMidnightBatch('America/New_York')).not.toThrow();
    });

    it('가을 전환: 중복 1시 30분 두 건의 UTC 순서가 보장된다', () => {
        const firstOccurrence = new Date('2024-11-03T05:30:00Z');  // EDT 1:30 AM
        const secondOccurrence = new Date('2024-11-03T06:30:00Z'); // EST 1:30 AM

        jest.useFakeTimers();
        jest.setSystemTime(firstOccurrence);
        const order1 = orderService.createOrder(1);

        jest.setSystemTime(secondOccurrence);
        const order2 = orderService.createOrder(2);

        expect(new Date(order1.createdAt) < new Date(order2.createdAt)).toBe(true);
    });
});
```

## 자주 발생하는 문제

### Clock 주입 누락

`Clock`을 서비스에 주입했는데도 내부 헬퍼 메서드에서 `Instant.now()`를 직접 호출하면 제어가 깨진다. 호출 스택 어딘가에 `Instant.now()` 직접 호출이 있으면 테스트에서 고정한 시각과 다른 값이 섞인다.

```java
public void process() {
    Instant now = clock.instant();    // 제어됨
    helper.doSomething();             // 내부에서 Instant.now() 직접 호출하면 제어 안 됨
}
```

시각이 필요한 지점에 `Instant`를 파라미터로 넘겨서 호출 스택 전체가 같은 시각을 쓰게 만든다.

```java
public void process() {
    Instant now = clock.instant();
    helper.doSomething(now);          // 외부에서 주입
}
```

### jest.useRealTimers() 복원 누락

`afterEach`에서 `jest.useRealTimers()`를 빠뜨리면, 같은 Jest 워커 프로세스에서 실행되는 이후 테스트가 고정된 시각으로 돌아간다. CI에서 테스트 실행 순서가 달라지면 의도하지 않은 실패가 생긴다.

`jest.config.js`에 `fakeTimers` 설정을 추가하면 매 테스트마다 자동으로 초기화된다.

```javascript
// jest.config.js
module.exports = {
    fakeTimers: {
        enableGlobally: false, // 명시적으로 useFakeTimers()를 호출한 테스트에서만 적용
    },
};
```

### 타임존 ID 없이 오프셋만 쓰는 경우

API에서 사용자 타임존을 `+09:00` 오프셋으로만 받으면 DST 전환 시점을 처리할 수 없다. `+09:00`은 항상 같은 오프셋이지만, `America/New_York`은 여름엔 `-04:00`, 겨울엔 `-05:00`으로 바뀐다.

DST가 있는 지역 사용자를 처리해야 한다면 타임존 ID(`America/New_York`)를 받아야 한다. 테스트에서도 오프셋 대신 타임존 ID를 기준으로 케이스를 작성한다.
