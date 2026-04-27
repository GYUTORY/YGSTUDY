---
title: Java static 사용 패턴과 안티패턴 (실무 시나리오 중심)
tags: [language, java, 객체지향-프로그래밍-oop, static, anti-pattern, jvm]
updated: 2026-04-27
---

# Java static 사용 패턴과 안티패턴

`static`이 무엇인지, 메모리 어디에 살고 어떤 종류가 있는지는 [Static_Concept.md](Static_Concept.md)에서 정리했다. 이 문서는 그 위에 실무에서 반복적으로 만나는 패턴 — 그리고 더 자주 만나는 안티패턴 — 만 모아서 풀어쓴 것이다. 5년 넘게 자바 코드를 다루며 본 사례 중에서, 신입 시절의 나에게 보여줬으면 좋았겠다 싶은 것들 위주로 추렸다.

## 인스턴스 변수와 static 변수의 메모리 배치

같은 클래스 안에 인스턴스 필드와 static 필드가 같이 있으면 입문서에서는 흔히 "static은 공유, 인스턴스는 개별"이라고만 설명하고 끝낸다. JVM 관점에서 이 차이는 좀 더 구체적이다.

```java
public class Account {
    static long totalCount;     // (A) static 필드
    static String bankName = "ACME"; // (B) static 필드
    private long balance;       // (C) 인스턴스 필드
    private String owner;       // (D) 인스턴스 필드
}
```

`Account` 클래스가 처음 참조되는 순간, JVM은 클래스 로더를 통해 바이트코드를 읽어 `java.lang.Class<Account>` 객체를 Heap에 만든다. (A), (B) 같은 static 필드의 슬롯은 이 Class 객체 안에 자리잡고, 슬롯에 들어가는 값(또는 참조)도 Class 객체와 함께 Heap에 산다. 클래스 메타데이터(메서드 바이트코드, 필드 디스크립터, 상수 풀 등)는 Heap이 아니라 Metaspace로 빠진다.

`new Account()`를 한 번 부를 때마다 별도의 Account 인스턴스가 Heap에 만들어지고, 그 인스턴스 안에 (C), (D)에 해당하는 슬롯이 들어간다. `balance`, `owner`는 인스턴스마다 따로 잡히는 메모리이고 인스턴스가 GC되면 같이 사라진다. 반면 `totalCount`, `bankName`은 Class 객체에 한 번 잡혀 있고, 이 Class 객체는 클래스 로더가 살아있는 한 GC 루트로 취급되어 거의 영원히 살아남는다.

여기서 두 가지 실무 함정이 나온다.

첫 번째, "static 필드 = GC 안 됨"이라는 말은 절반만 맞다. 정확히는 "static 필드가 참조하는 객체는, 클래스 로더가 언로드될 때까지 GC 루트에서 끊기지 않는다". 일반 애플리케이션 클래스로더는 거의 언로드되지 않으므로 결과적으로 영원히 안 죽는 것처럼 보일 뿐이다. Tomcat 같은 컨테이너에서 웹 앱을 reload하면 클래스 로더가 바뀌면서 비로소 언로드 시도가 일어나는데, 이때 static 필드가 외부 ClassLoader의 객체를 붙들고 있으면 클래스 로더 자체가 누수되는 고전적인 PermGen/Metaspace 누수 문제가 된다.

두 번째, 인스턴스 필드는 객체별로 메모리가 분리되니 동시성 걱정이 덜하지만(`this`마다 다른 인스턴스), static 필드는 **JVM 안의 모든 스레드가 같은 슬롯을 본다**. 인스턴스 필드 시절엔 안전하던 코드가 static으로 옮기는 순간 레이스 컨디션이 생기는 게 이 때문이다.

## 카운터/캐시/플래그를 static으로 둘 때 생기는 일

가장 자주 보는 안티패턴이 이 셋이다. "전역에서 접근하기 쉬우니까", "객체 안 만들어도 되니까"가 보통의 동기인데, 시간 지나면 거의 예외 없이 사고가 난다.

### 카운터 — 스레드 경합

```java
public class HitCounter {
    static int hit = 0;

    public static void increment() { hit++; }
    public static int get() { return hit; }
}
```

서비스 트래픽이 작을 때는 잘 돌다가 동시 요청이 늘면서 `hit` 값이 실제 호출 횟수보다 작아진다. `hit++`은 읽기-증가-쓰기 세 단계라서 두 스레드가 동시에 진입하면 한쪽 증가가 사라진다. 모니터링 지표가 어긋나기 시작하면 원인을 찾는 데 한참 걸린다. 단순한 카운터 한 줄이 그렇게 까다로운 디버깅거리가 된다.

해결은 `AtomicInteger`나 `LongAdder`로 바꾸거나, 애초에 metric 라이브러리(예: Micrometer의 `Counter`)에 위임하는 쪽이다. `volatile int hit`은 가시성만 보장하고 `hit++`의 원자성은 보장하지 않으니, 증감에는 의미가 없다.

### 캐시 — 테스트 간 상태 누수와 메모리 누수

```java
public class UserCache {
    static final Map<Long, User> CACHE = new HashMap<>();

    public static void put(long id, User u) { CACHE.put(id, u); }
    public static User get(long id) { return CACHE.get(id); }
}
```

운영에서는 `HashMap`을 여러 스레드가 동시에 쓰면 내부 링크가 꼬여 `get()`이 무한 루프에 빠지는 사례가 자바 8 이전에 유명했고, 자바 8 이후로도 데이터가 사라지거나 ConcurrentModificationException이 터진다. 일단 `ConcurrentHashMap`으로 바꿔야 하지만, 그게 끝이 아니다.

이 캐시는 만료 정책이 없어서 시간이 지날수록 엔트리가 쌓인다. static이라 클래스 로더가 살아있는 동안 GC도 안 된다. 며칠 단위로 운영하면 Old 영역이 차오르다 풀 GC가 자주 돌고, 결국 OOM으로 죽는다. 일반 인스턴스 필드였으면 객체가 GC될 때 같이 사라졌을 텐데 static이라 빠져나갈 길이 없다.

테스트 입장에서도 골치다. `UserCache.put(1L, ...)`를 하는 테스트가 먼저 돌고 나면, 그 뒤에 도는 다른 테스트가 캐시를 빈 상태로 가정하고 짠 코드라면 통과/실패가 실행 순서에 따라 갈린다. JUnit이 한 JVM 안에서 모든 테스트를 도는 게 기본이라, static 상태는 테스트 간 격리를 자연스럽게 깨뜨린다.

운영 사고 사례 하나. 세션 단위 데이터를 static `Map`에 넣고 세션 종료 훅에서만 삭제하는 코드가 있었는데, 종료 훅이 비정상 케이스에서 호출되지 않는 경로가 있었다. 일주일에 수만 개씩 엔트리가 새는 양이라 처음엔 안 보이다가, 한 달쯤 지나서 GC 시간이 부쩍 늘어나며 발견됐다. 캐시가 필요했다면 `Caffeine`처럼 만료 정책이 있는 라이브러리를 인스턴스 필드로 두고 DI로 받는 게 맞았다.

### 플래그 — 클래스 언로드와 묶이는 수명

```java
public class FeatureFlag {
    public static volatile boolean USE_NEW_PRICING = false;
}
```

기능 토글을 static volatile 플래그로 두는 건 JVM 안에서는 동작한다. 그러나 운영하다 보면 "이 플래그 다시 false로 돌리려면 재배포해야 한다"는 인스턴스의 스코프 문제로 옮겨가고, 결국 외부 토글 시스템(Unleash, LaunchDarkly 등)으로 이전하는 작업을 하게 된다. 이때 static 플래그는 호출부가 `FeatureFlag.USE_NEW_PRICING`처럼 박혀 있어서 인스턴스 기반 인터페이스(`FeatureFlagClient.isEnabled("use_new_pricing")`)로 바꾸려면 호출부 전부를 손봐야 한다. 처음부터 인스턴스로 두고 DI로 받았으면 구현체만 갈아끼우면 끝났을 일이다.

## static 메서드 hiding을 다형성으로 오해하는 실수

```java
class PaymentProcessor {
    static String description() { return "default"; }
    void process() {
        System.out.println("[" + description() + "] processing");
    }
}

class CardPaymentProcessor extends PaymentProcessor {
    static String description() { return "card"; }
}
```

`CardPaymentProcessor cpp = new CardPaymentProcessor(); cpp.process();`를 호출했을 때 출력이 `[card] processing`이 될 것이라 기대했다가, 실제로는 `[default] processing`이 나오는 일을 본 적이 있다. 작성자는 인스턴스 메서드 오버라이딩처럼 동작할 거라 믿었던 거다.

원인은 `description()`이 `static`이기 때문이다. static 메서드는 오버라이딩되지 않고 hiding(숨김)된다. 호출부의 바인딩이 인스턴스 타입이 아니라 **컴파일 타임의 참조 타입**에 따라 결정된다. `process()`가 `PaymentProcessor` 안에서 정의되어 있고 그 안에서 `description()`을 부르면, 컴파일러는 `PaymentProcessor.description()`으로 결정해 버린다. 자식이 같은 시그니처로 새 static 메서드를 만들어도 부모 메서드를 가릴 뿐, 부모 컨텍스트에서의 호출은 부모 것을 그대로 본다.

디버깅이 더 까다로워지는 건 IDE에서 호출 그래프를 따라가면 `description()`이 두 군데에 정의돼 있으니 사람이 보기엔 다형성처럼 보인다는 것이다. 단위 테스트에서 `CardPaymentProcessor`를 instantiate해서 `process()`를 호출해도, 그 안의 `description()`은 부모 것이 불린다. 한참 들여다보다가 메서드에 `@Override`를 붙여보면 그제야 컴파일러가 "static 메서드는 오버라이드 못 한다"고 알려줘서 정신을 차리게 된다.

다형성이 필요한 자리에는 static을 쓰지 않는다. 인스턴스 메서드로 바꾸고, 정말 동작이 클래스에 묶여야 한다면 추상 메서드 + 구현 클래스로 푼다. `@Override` 어노테이션을 강제로 붙이는 코딩 스타일을 팀에 깔아두면 이런 종류의 실수는 컴파일 타임에 거의 다 잡힌다.

## static import 남용으로 호출부 추적이 깨지는 케이스

```java
import static com.acme.util.MoneyUtils.*;
import static com.acme.util.DateUtils.*;
import static com.acme.util.StringUtils.*;
import static com.acme.domain.PriceRules.*;

public class OrderService {
    public Money settle(Order order) {
        Money base = round(sum(order.items()));
        if (isWeekend(order.date())) {
            base = applyHolidayRule(base);
        }
        return ensurePositive(base);
    }
}
```

리팩터링 작업 중에 이런 코드를 만난 적이 있다. `round`, `sum`, `isWeekend`, `applyHolidayRule`, `ensurePositive` 다섯 개의 호출이 어디서 온 건지 본문만 봐서는 모른다. IDE의 "Go to Declaration"으로 하나씩 따라가야 알 수 있고, 새 메서드를 비슷한 이름으로 추가하면 어느 import가 먼저 잡히는지 헷갈리는 충돌이 생긴다.

`MoneyUtils.round(...)`, `DateUtils.isWeekend(...)`처럼 클래스명을 살려두면 본문에서 이미 출처가 드러나서 코드 리뷰에서도 이슈가 잘 보인다. static import는 표현력보다 추적성을 더 많이 깎아먹기 때문에 프로젝트 내부 유틸리티에는 안 쓰는 쪽이 길게 보면 편하다.

자주 정하는 기준선을 적자면, `Math.sqrt` 같은 표준 라이브러리의 잘 알려진 메서드, AssertJ/JUnit/Mockito 같은 테스트 DSL은 static import를 허용한다. 프로젝트 내부 클래스는 일반 호출로 두는 쪽으로 정리한다. 이 정도만 합의해도 코드 리뷰 부담이 크게 줄어든다.

## 싱글톤 구현 비교 — Holder 패턴, enum 싱글톤, DCL

싱글톤이 정말 필요할 때(스프링 같은 DI 컨테이너를 안 쓰거나, 컨테이너 외부에서 살아야 하는 경우) 자바에서 자주 쓰는 세 가지 구현이 있다. 각각의 특성을 풀어보면 이렇다.

**Holder 패턴**은 static 중첩 클래스가 외부 클래스와 따로 로드된다는 점을 이용한다. 외부 클래스 `HeavyService`가 로드되는 시점에는 `HeavyService.Holder`는 아직 로드되지 않고, `getInstance()`가 처음 호출되는 순간에야 `Holder`가 로드된다. 클래스 로딩 자체가 JVM 락으로 보호되어 있어서, 별도의 `synchronized`나 `volatile` 없이도 정확히 한 번만 인스턴스가 생성된다. 코드가 제일 짧고, 동기화 비용도 없다. 다만 직렬화·역직렬화가 들어가면 `readResolve()`를 직접 구현해야 단일성이 깨지지 않고, 리플렉션으로 private 생성자를 호출하면 두 번째 인스턴스를 만들 수 있다.

**enum 싱글톤**은 자바가 enum의 인스턴스 단일성을 언어 수준에서 보장한다는 점을 이용한다. `public enum HeavyService { INSTANCE; ... }` 한 줄로 끝나고, 직렬화/역직렬화도 자동으로 안전하게 처리된다. 리플렉션 공격에도 안전한데, `Constructor.newInstance`가 enum 생성자에 대해서는 명시적으로 막혀 있기 때문이다. 단점은 지연 초기화가 안 된다는 점이다. `HeavyService.INSTANCE`를 처음 참조하는 순간 enum 클래스 전체가 로드되며 모든 enum 상수가 만들어진다. 초기화 비용이 진짜로 무거우면 이게 부담될 수 있고, 단순한 형태라 외부에서 받는 의존성이 있을 때(예: 생성자 인자) 다루기가 어색하다.

**DCL(Double-Checked Locking)**은 `volatile` 필드와 두 단계 null 체크로 동기화 비용을 한 번만 치르도록 짠 방식이다. `volatile`이 빠지면 자바 메모리 모델에서 부분 초기화된 인스턴스를 다른 스레드가 보는 케이스가 생기므로 반드시 붙어야 한다. 코드가 길고, 한 줄만 빼먹어도 깨지는 미묘함이 있어서 실무에서 새로 짤 일은 거의 없다. 레거시 코드에서 만나면 그대로 두기보다 Holder 패턴이나 enum으로 바꾸는 쪽을 권한다.

세 가지를 서술형으로 비교하면, 일반적인 지연 초기화 싱글톤은 Holder 패턴이 가장 깔끔하다. 직렬화나 리플렉션까지 신경 써야 하면 enum 싱글톤이 안전하다. DCL은 학습용 외에 새로 쓸 이유가 거의 없다. 그리고 사실 가장 좋은 답은 "정말 싱글톤이 필요한가"를 다시 묻는 것이다. 스프링 같은 DI 컨테이너에서 빈을 싱글톤 스코프로 두면 모든 문제가 사라진다. static 키워드 자체가 등장할 일이 없어진다.

## static 블록의 ExceptionInInitializerError가 NoClassDefFoundError로 전이되는 함정

```java
public class ExternalConfig {
    static final String API_KEY = System.getenv("API_KEY").trim();
    static final URL ENDPOINT = new URL(System.getenv("ENDPOINT"));

    static {
        Files.readAllBytes(Path.of("/etc/app/license"));
    }
}
```

이 클래스를 처음 사용하는 코드에서 `ExternalConfig.API_KEY`를 참조하면 JVM은 클래스 초기화에 들어간다. 환경변수 `API_KEY`가 비어 있으면 `null.trim()`에서 NPE가 나고, JVM은 그걸 `ExceptionInInitializerError`로 감싸 던진다. 여기까지가 1차 사고다.

실무에서 더 골치 아픈 건 2차 사고다. 한 번 초기화에 실패한 클래스는 JVM 안에서 "초기화 실패 상태(erroneous state)"로 기록된다. 같은 JVM 프로세스 안에서 그 클래스를 다시 참조하면, 이제부터는 `ExceptionInInitializerError`가 아니라 `NoClassDefFoundError`가 던져진다. 메시지가 "Could not initialize class ExternalConfig"라고 나오는데, 처음 보는 사람은 보통 클래스패스 문제로 오인한다. 의존성 jar가 빠졌나, ClassLoader가 잘못됐나 한참 뒤지다가, 로그를 더 위로 올려서 1차 사고의 `ExceptionInInitializerError`를 찾아내야 비로소 환경변수 문제임을 깨닫는다.

스프링 환경에서 이게 더 무서운 이유는 컨텍스트 시작 중에 동시성으로 클래스 초기화가 일어나면서, 1차 사고 로그가 다른 빈 초기화 로그와 섞여 사라지기 쉽기 때문이다. 결과만 `NoClassDefFoundError`가 보이고 원인은 묻혀버린다.

대처는 두 가지다. static 초기화에서 외부 자원에 의존하는 로직(환경변수 파싱, 파일 읽기, 네트워크 호출 등)은 가능하면 빼고, 인스턴스 시점이나 명시적 초기화 메서드로 미룬다. 꼭 static으로 둬야 하면 기본값과 방어 코드를 넣어 초기화 자체는 절대 실패하지 않게 만든다. 초기화 단계에서 죽을 수 있는 코드는 한 번 죽으면 그 JVM 인스턴스에서는 영영 못 살아난다는 점을 기억해 두면 된다.

## static 안 써야 하는 케이스 판별 기준

새 코드를 짜면서 "이거 static으로 둘까"가 떠오를 때마다 다음 질문들을 순서대로 던지면 거의 답이 나온다.

이 값이 런타임에 변하는가. 가변 상태(카운터, 캐시, 세션, 토글 플래그)면 static에 두지 말고 인스턴스로 둔다. 동시성과 테스트 격리, 두 방향 모두에서 곤란해진다.

다형성이나 목킹이 필요한가. 메서드 시그니처가 같은 다른 구현으로 갈아끼울 가능성이 조금이라도 있으면 인스턴스 메서드로 둔다. static 메서드는 인터페이스 뒤에 숨길 수 없고 hiding이 다형성처럼 동작하지 않는다.

외부 자원에 의존하는가. DB, 네트워크, 환경변수, 파일 같은 외부 의존을 static 초기화로 가져오면 `ExceptionInInitializerError` 함정에 노출된다. 인스턴스 시점이나 명시적 초기화 메서드로 옮긴다.

테스트에서 어떻게 초기화할 것인가. 이 질문에 답이 안 나오면 static을 안 쓰는 쪽이 거의 항상 맞다. 인스턴스 필드는 테스트마다 새 객체를 만들면 자동으로 초기화되지만, static 필드는 명시적으로 reset해야 하고 그것도 누락되기 쉽다.

이 셋 다 아니라면 — 즉 변하지 않는 상수, 외부 의존이 없는 순수 함수형 유틸리티, 외부 인스턴스 참조가 필요 없는 중첩 클래스, 싱글톤의 Holder — 정도가 static을 써도 사고가 거의 안 나는 자리다. 자바를 5년 정도 쓰면서 정착한 기준이고, 새 클래스를 만들 때 머릿속에서 한 번 돌려보면 나중에 디버깅 시간을 꽤 아껴준다.
