---
title: Java 클래스와 메서드 설계 기준
tags: [language, java, 객체지향-프로그래밍-oop, class, design]
updated: 2026-06-22
---

## 무엇을 결정하는 문서인가

클래스와 메서드의 문법적 차이나 호출 메커니즘은 별도 문서에서 다룬다. 여기서는 "이 동작을 새 클래스로 뺄까, 기존 클래스 메서드로 둘까", "이 메서드 파라미터가 다섯 개인데 괜찮은가", "정적 유틸로 만들까 객체로 만들까" 같은 설계 판단을 다룬다. 코드는 문법만 맞으면 돌아가지만, 이 판단이 어긋나면 6개월 뒤에 수정 한 줄이 클래스 열 개를 건드리게 된다.

설계 기준에 정답은 없다. 다만 실무에서 반복적으로 쓰이는 판단 신호가 있고, 그 신호를 놓치면 어떤 식으로 코드가 망가지는지는 꽤 예측 가능하다. 그 신호들을 정리한다.

---

## 새 클래스를 만들 기준: 책임 단위로 자른다

클래스를 새로 만들지, 기존 클래스에 메서드를 추가할지 고민될 때 첫 질문은 "이 코드가 바뀌는 이유가 기존 클래스가 바뀌는 이유와 같은가"이다. 단일 책임 원칙(SRP)을 "한 클래스는 한 가지 일만 한다"로 외우면 실무에서 적용이 안 된다. 더 쓸 만한 정의는 "한 클래스는 한 종류의 액터(변경을 요청하는 주체)에게만 응답해야 한다"이다.

예를 들어 주문 데이터를 다루는 클래스가 있다고 하자.

```java
public class Order {
    private final long id;
    private final List<OrderLine> lines;
    private OrderStatus status;

    // 도메인 규칙: 주문 금액 계산
    public Money totalAmount() {
        return lines.stream()
                .map(OrderLine::subtotal)
                .reduce(Money.ZERO, Money::add);
    }

    // 화면 표시용 포맷
    public String toDisplayString() {
        return "주문 #" + id + " / " + totalAmount().toKrw() + "원";
    }

    // DB 저장용 SQL
    public String toInsertSql() {
        return "INSERT INTO orders (id, status) VALUES (" + id + ", '" + status + "')";
    }
}
```

`totalAmount`는 도메인 규칙이 바뀔 때 수정된다. `toDisplayString`은 기획자가 화면 문구를 바꾸자고 할 때 수정된다. `toInsertSql`은 DBA가 스키마를 바꿀 때 수정된다. 변경을 요청하는 주체가 셋 다 다르다. 이 세 가지가 한 클래스에 있으면, 화면 문구 하나 바꾸려다 도메인 클래스를 다시 컴파일하고 다시 배포해야 한다. 표시 로직은 `OrderView`로, 영속화는 `OrderRepository`나 매퍼로 빼는 게 맞다.

반대로 클래스를 너무 잘게 쪼개는 것도 문제다. 필드 하나에 게터 하나만 있는 클래스가 수십 개면, 코드를 읽을 때 파일 사이를 계속 점프해야 해서 흐름이 안 잡힌다. 새 클래스를 만드는 기준은 "독립적으로 변경되는 책임이 있는가"이지 "코드 줄 수가 많은가"가 아니다. 50줄짜리 메서드 하나가 한 가지 책임만 한다면 그대로 두는 게 낫고, 10줄짜리라도 두 가지 책임이 섞여 있으면 나눈다.

판단이 애매할 때 쓰는 실무 신호 하나. 클래스 이름을 지어 보고 "그리고(And)"나 "또는(Or)"이 들어가야 설명이 되면 책임이 둘 이상이다. `OrderValidatorAndNotifier` 같은 이름이 나오면 검증과 알림을 나눠야 한다는 뜻이다.

---

## 응집도와 결합도로 클래스 크기를 판단한다

클래스가 "너무 크다"는 건 줄 수 문제가 아니라 응집도가 낮다는 뜻이다. 응집도가 높은 클래스는 모든 메서드가 같은 필드 집합을 함께 쓴다. 응집도가 낮으면 메서드 그룹마다 쓰는 필드가 갈린다.

God Class는 이 신호가 극단적으로 나타나는 안티패턴이다. 필드가 20개쯤 있고, 메서드 A,B,C는 앞쪽 필드 5개만 쓰고, 메서드 D,E,F는 뒤쪽 필드 7개만 쓰는데 두 그룹이 서로 안 겹친다면, 그건 사실 클래스 두 개가 한 파일에 들어 있는 것이다.

```java
public class MemberManager {
    // 인증 관련 필드
    private String passwordHash;
    private int failedLoginCount;
    private Instant lockedUntil;

    // 프로필 관련 필드
    private String nickname;
    private String profileImageUrl;
    private String introduction;

    // --- 인증 관련 메서드: 위쪽 3개 필드만 사용 ---
    public boolean verifyPassword(String raw) { /* passwordHash 사용 */ }
    public void recordLoginFailure() { /* failedLoginCount, lockedUntil 사용 */ }
    public boolean isLocked() { /* lockedUntil 사용 */ }

    // --- 프로필 관련 메서드: 아래쪽 3개 필드만 사용 ---
    public void changeNickname(String nickname) { /* nickname 사용 */ }
    public void updateProfileImage(String url) { /* profileImageUrl 사용 */ }
}
```

`verifyPassword`/`recordLoginFailure`/`isLocked`는 인증 필드만 만지고, `changeNickname`/`updateProfileImage`는 프로필 필드만 만진다. 두 묶음이 공유하는 필드가 없다. 이건 `Credential`(인증)과 `Profile`(프로필)로 분리하라는 신호다. 분리하면 인증 로직 테스트에 프로필 필드를 채울 필요가 없어지고, 락 정책을 바꿔도 프로필 코드를 건드리지 않는다.

이 "메서드가 특정 필드 집합만 쓰는가"는 눈으로 보기 어려울 때가 있다. IntelliJ의 경우 필드에서 `Find Usages`를 돌리면 어떤 메서드가 그 필드를 쓰는지 나오고, 메서드-필드 사용 매트릭스를 머릿속에 그릴 수 있다. 사용 그룹이 두 덩어리로 깔끔하게 갈리면 분해 후보다.

결합도는 반대 방향의 신호다. 한 클래스가 다른 클래스 내부를 너무 많이 안다면 결합도가 높다. 대표적인 냄새가 디미터 법칙 위반이다.

```java
// 결합도 높음: order 내부 구조를 호출자가 다 안다
String city = order.getCustomer().getAddress().getCity();

// 결합도 낮음: order에게 물어본다
String city = order.shippingCity();
```

위 코드는 `Order`가 `Customer`를 가지고 `Customer`가 `Address`를 가진다는 내부 구조에 호출자가 묶여 있다. `Customer`가 주소를 여러 개 갖도록 바뀌면 이 한 줄이 깨진다. `order.shippingCity()`로 위임하면 내부 구조가 바뀌어도 `Order` 안에서만 고치면 된다. 다만 위임 메서드를 무한정 늘리면 `Order`가 다시 비대해지므로, 자주 쓰이는 접근 경로에만 위임을 만든다.

---

## 동작을 메서드로 둘까, 별도 클래스로 추출할까

새 동작이 생겼을 때 메서드로 충분한 경우가 대부분이다. 별도 클래스로 빼야 하는 건 다음 중 하나에 해당할 때다.

동작에 자체 상태가 필요할 때. 메서드는 호출이 끝나면 지역 변수가 사라진다. 계산 중간 상태를 여러 단계에 걸쳐 들고 있어야 한다면 그 상태를 담을 객체가 필요하다.

같은 종류의 동작이 여러 변형으로 갈릴 때. 배송비 계산이 일반 배송, 도서산간, 해외 배송으로 갈리고 각각 규칙이 다르면, `if-else`로 메서드 안에 다 넣기보다 전략(Strategy)으로 빼는 게 낫다.

```java
public interface ShippingPolicy {
    Money calculate(Order order);
}

public class StandardShipping implements ShippingPolicy {
    public Money calculate(Order order) {
        return order.totalWeight() > 20_000 ? Money.of(5000) : Money.of(3000);
    }
}

public class RemoteAreaShipping implements ShippingPolicy {
    public Money calculate(Order order) {
        return new StandardShipping().calculate(order).add(Money.of(4000));
    }
}
```

전략으로 빼는 기준은 "분기 조건이 런타임에 결정되는가"와 "새 변형이 앞으로 더 생길 것 같은가"이다. 분기가 두 개뿐이고 더 안 늘어날 거면 `if-else` 메서드가 더 읽기 쉽다. 추출은 비용이 있으니 변형이 실제로 셋 이상 되거나 늘어날 게 확실할 때 한다.

값 객체(Value Object)로 빼는 신호는 또 다르다. 원시 타입 여러 개가 항상 같이 다니면 그건 묶어야 할 개념이다. `String city, String street, String zipCode`를 메서드 파라미터로 매번 같이 넘기고 있다면 `Address`라는 값 객체가 숨어 있는 것이다. 이걸 "데이터 뭉치(Data Clump)"라고 부른다. 묶으면 파라미터 개수가 줄고, 주소 검증 규칙을 한곳에 모을 수 있다.

```java
public record Address(String city, String street, String zipCode) {
    public Address {
        if (zipCode == null || !zipCode.matches("\\d{5}")) {
            throw new IllegalArgumentException("우편번호 형식 오류: " + zipCode);
        }
    }
}
```

메서드 추출(Extract Method)의 실무 트리거는 더 단순하다. 메서드 본문에 주석으로 "// 여기부터 재고 차감"처럼 단락을 설명하고 있으면, 그 단락이 메서드로 빠져야 한다는 신호다. 주석 대신 메서드 이름이 그 일을 한다. 또 같은 코드 덩어리가 두 곳 이상에 복사돼 있으면 추출한다. 반복문 안쪽 로직이 길어져 루프 구조가 안 보이면, 안쪽을 메서드로 빼서 루프는 "각 항목에 대해 무엇을 한다"만 보이게 한다.

---

## 메서드 설계 기준

### 파라미터 개수

파라미터가 많을수록 호출하는 쪽이 외우기 어렵고, 순서를 헷갈려 인자를 바꿔 넣는 버그가 생긴다. 특히 같은 타입 파라미터가 연달아 있으면 컴파일러가 못 잡는다.

```java
// boolean 세 개 — 호출부에서 무슨 의미인지 안 보인다
reportService.generate(true, false, true);

// 호출부: 이게 뭘 켜고 끄는 건지 알 수 없다
```

파라미터가 셋을 넘어가기 시작하면 묶을 개념이 있는지 본다. 위처럼 boolean 플래그가 여러 개면 옵션 객체나 빌더로 묶는다. 연관된 데이터면 값 객체로 묶는다. 그래도 안 줄면 메서드가 너무 많은 일을 하는 것일 수 있으니 메서드 자체를 나눈다.

```java
public record ReportOptions(boolean includeChart, boolean includeRawData, boolean compress) {}

reportService.generate(new ReportOptions(true, false, true));
// record 생성자에서 필드 이름이 보이므로 호출 의도가 드러난다
```

### 추상화 수준을 한 메서드 안에서 섞지 않는다

읽기 어려운 메서드의 흔한 원인은 높은 수준의 흐름과 낮은 수준의 디테일이 한 메서드에 섞여 있는 것이다.

```java
public void placeOrder(Cart cart) {
    // 높은 수준: 주문 흐름
    validate(cart);

    // 낮은 수준: 갑자기 SQL 문자열을 조립한다
    StringBuilder sql = new StringBuilder("INSERT INTO orders ");
    sql.append("(user_id, total) VALUES (");
    sql.append(cart.userId()).append(", ");
    sql.append(cart.total()).append(")");
    jdbcTemplate.update(sql.toString());

    // 다시 높은 수준
    sendConfirmationEmail(cart);
}
```

`validate`와 `sendConfirmationEmail`은 "무엇을 한다" 수준인데, 중간의 SQL 조립은 "어떻게 한다" 수준이다. 읽는 사람이 추상화 계단을 오르내려야 해서 흐름이 끊긴다. SQL 조립도 `saveOrder(cart)` 같은 메서드로 빼서 세 줄 다 같은 높이에 두면, `placeOrder`는 주문 흐름만 한눈에 보인다. 한 메서드 안의 문장들은 비슷한 추상화 수준이어야 한다.

### 명령과 조회를 분리한다 (CQS)

명령-조회 분리(CQS)는 "값을 돌려주는 메서드는 상태를 바꾸지 않고, 상태를 바꾸는 메서드는 값을 돌려주지 않는다"는 기준이다. 조회인 줄 알고 부른 메서드가 몰래 상태를 바꾸면 디버깅이 지옥이 된다.

```java
// 나쁜 예: getter 이름인데 내부 상태를 바꾼다
public int getNextId() {
    return ++this.counter;  // 호출할 때마다 counter가 증가
}
```

`getNextId`를 로그 찍으려고 두 번 호출하면 ID가 두 칸 뛴다. 이름은 조회처럼 생겼는데 부수효과가 있다. 상태를 바꾸는 거라면 이름을 `issueNextId`나 `incrementAndGet`처럼 명령으로 짓고, 순수 조회는 부수효과를 없앤다. 이 규칙을 지키면 "이 메서드를 불러도 안전한가"를 이름만 보고 판단할 수 있다.

완벽하게 지키기 어려운 경우도 있다. 큐의 `poll()`은 원소를 꺼내면서(상태 변경) 그 원소를 반환(조회)한다. 동시성 자료구조에서는 "확인하고 바꾸기"를 원자적으로 해야 해서 분리가 불가능하다. 이런 건 예외로 인정하되, 일반 도메인 메서드에서는 분리를 기본으로 둔다.

### 부수효과를 다루는 법

부수효과 자체가 나쁜 건 아니다. DB에 쓰고, 메일을 보내고, 로그를 남기는 건 다 부수효과다. 문제는 부수효과가 메서드 이름에서 예상되지 않을 때다. `calculateTotal()`이 계산만 할 줄 알았는데 안에서 결제 API를 호출하면, 단위 테스트로 금액 계산만 검증하려다 결제 시스템까지 띄워야 한다.

설계 기준은 "예상되지 않는 부수효과를 만들지 않는다"이다. 순수 계산은 부수효과 없이 두고, 부수효과가 필요하면 그게 드러나는 이름과 위치에 모은다. 입력을 받아 출력만 내는 함수가 많을수록 테스트가 쉬워진다.

---

## 정적 유틸 클래스 vs 인스턴스 객체

같은 동작을 정적 메서드로 둘지 인스턴스 메서드로 둘지의 판단은 두 가지를 본다. 상태 의존성과 테스트 가능성이다.

상태가 없고 입력만으로 출력이 정해지는 순수 함수는 정적 메서드가 자연스럽다. 문자열 포맷, 수학 계산, 단위 변환 같은 것이다.

```java
public final class StringUtils {
    private StringUtils() {}  // 인스턴스화 막기

    public static boolean isBlank(String s) {
        return s == null || s.trim().isEmpty();
    }
}
```

유틸 클래스는 생성자를 `private`으로 막아 인스턴스화를 못 하게 한다. 상태가 없으니 객체를 만들 이유가 없고, 실수로 `new StringUtils()`를 막아 둔다.

문제는 정적 메서드 안에서 외부 시스템에 의존하기 시작할 때다.

```java
// 정적 메서드 안에서 외부 의존이 박혀 있다
public final class NotificationUtils {
    public static void notify(String userId, String message) {
        SmtpClient.connect("smtp.internal:25")   // 하드코딩된 의존
                  .send(userId, message);
    }
}
```

`notify`를 호출하는 코드를 테스트하려면 진짜 SMTP 서버가 떠 있어야 한다. Mockito 같은 일반 모킹 도구는 정적 메서드를 가로채지 못한다(`mockito-inline`으로 가능하지만 느리고 설정 비용이 있다). 그래서 외부 시스템과 통신하는 동작은 인스턴스로 만들고 의존성을 주입받는다.

```java
public class NotificationService {
    private final MailSender mailSender;  // 인터페이스로 주입

    public NotificationService(MailSender mailSender) {
        this.mailSender = mailSender;
    }

    public void notify(String userId, String message) {
        mailSender.send(userId, message);
    }
}
```

`MailSender`를 인터페이스로 두면 테스트에서 가짜 구현을 넣을 수 있다. 정적 메서드는 이 교체가 불가능하다. 정리하면, 상태도 없고 외부 의존도 없는 순수 계산은 정적 유틸, 상태가 있거나 나중에 구현을 바꿔 끼워야 하거나 테스트에서 대체해야 하는 동작은 인스턴스 객체로 둔다.

정적 메서드를 남발할 때 또 하나 놓치기 쉬운 건 다형성을 못 쓴다는 점이다. 정적 메서드는 오버라이드되지 않으므로, 미래에 구현을 갈아끼울 여지가 조금이라도 있으면 인터페이스 + 인스턴스로 가는 게 안전하다.

---

## 트러블슈팅: 실무에서 겪는 신호와 대응

### 클래스가 계속 비대해질 때

서비스 클래스가 1000줄을 넘어가고 메서드가 30개쯤 되면, 어디에 무슨 메서드가 있는지 안 외워진다. 이때 줄 수로 자르면 안 된다. 앞서 말한 필드-메서드 사용 매트릭스를 본다. 메서드 묶음마다 쓰는 필드가 갈리면 그 경계로 클래스를 나눈다.

실제로 자주 겪는 케이스는 `UserService`에 가입, 로그인, 프로필 수정, 권한 관리가 다 들어가 있는 경우다. 인증 관련 메서드는 `passwordEncoder`, `tokenProvider`를 쓰고, 프로필 관련 메서드는 `profileRepository`만 쓴다. 이 의존성 사용 패턴이 클래스를 나누는 선을 그려 준다. `AuthService`와 `ProfileService`로 갈라지면 각각이 주입받는 의존성도 줄어들어서, 생성자 파라미터가 8개에서 3개로 떨어진다. 생성자 파라미터가 너무 많다는 것 자체가 그 클래스가 너무 많은 일을 한다는 신호이기도 하다.

분해할 때 주의할 점은 한 번에 다 나누려 하지 않는 것이다. 가장 응집도가 낮은 묶음 하나를 먼저 빼고 테스트를 돌려서 동작이 같은지 확인한 뒤 다음을 뺀다. 한 번에 다 옮기면 중간에 뭐가 깨졌는지 추적이 안 된다.

### 메서드 시그니처가 계속 늘어날 때

처음에 `createOrder(userId, productId)`였던 메서드가 요구사항이 추가될 때마다 `createOrder(userId, productId, couponId, usePoint, memo, isGift)`로 늘어나는 경우가 흔하다. 파라미터를 추가할 때마다 기존 호출부를 다 고쳐야 하고, 안 쓰는 경우엔 `null`이나 `false`를 채워 넣게 된다.

```java
// 점점 늘어난 시그니처 — 호출부가 null과 false로 지저분해진다
orderService.createOrder(userId, productId, null, false, null, false);
```

이럴 때는 파라미터를 요청 객체로 묶는다. 새 옵션이 생겨도 객체에 필드를 추가하면 되고, 기존 호출부는 안 건드린다.

```java
public record OrderRequest(
        long userId,
        long productId,
        Long couponId,      // 선택 항목은 null 허용
        boolean usePoint,
        String memo,
        boolean isGift
) {}

orderService.createOrder(request);
```

값이 선택적이고 조합이 많으면 빌더를 붙여서 `OrderRequest.builder().userId(1).productId(2).useGift().build()`처럼 필요한 것만 채우게 한다. 다만 요청 객체로 묶는 것도 비용이라, 파라미터가 둘셋이고 더 안 늘어날 것 같으면 그냥 두는 게 낫다. "계속 늘어나는 추세인가"가 판단 기준이다.

또 하나 자주 보는 패턴은 같은 동작인데 인자만 다른 오버로딩이 너무 많아지는 것이다. `find(id)`, `find(id, includeDeleted)`, `find(id, includeDeleted, withLock)`처럼 늘어나면, 어떤 오버로드가 어떤 기본값을 쓰는지 외우기 어렵다. 이것도 조회 조건 객체로 묶으면 오버로딩 개수가 줄어든다.

### 어디에 둘지 모를 메서드가 생길 때

새 동작을 짜다 보면 "이게 `Order`에 들어가야 하나, `Member`에 들어가야 하나" 애매한 경우가 있다. 기준은 "그 메서드가 가장 많이 쓰는 데이터를 가진 클래스에 둔다"이다. 주문 항목들을 순회하며 합계를 내는 로직은 그 데이터를 가진 `Order`에 둔다. `Member`에 두면 `order.getLines()`로 데이터를 꺼내 와야 해서 결합도가 올라간다. 데이터와 그 데이터를 다루는 동작을 같은 곳에 두는 게 객체지향의 기본이고, 동작이 자기가 안 가진 데이터를 자꾸 꺼내 쓰면 그 동작은 데이터를 가진 쪽으로 옮겨야 한다는 신호다(Feature Envy).
</content>
</invoke>
