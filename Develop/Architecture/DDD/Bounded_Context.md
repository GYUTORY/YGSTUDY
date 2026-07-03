---
title: Bounded Context
tags: [ddd, bounded-context, context-map, ubiquitous-language, anti-corruption-layer, strategic-design]
updated: 2026-05-01
---

# Bounded Context

## 이 문서의 위치

DDD의 전략적 설계에서 가장 중심에 있는 개념이 Bounded Context다. 이 문서는 모델과 언어의 경계로서의 Bounded Context에 집중한다. 같은 단어가 컨텍스트마다 다른 의미를 갖는 현상이 왜 생기고, 그걸 코드와 패키지 구조에 어떻게 옮기고, 컨텍스트끼리는 어떤 관계를 맺는지를 다룬다.

서비스를 어떻게 쪼개고 어떤 단위로 배포하는지는 [서비스_분해_및_도메인_설계.md](../MSA/서비스_분해_및_도메인_설계.md)에서 다룬다. 그쪽이 "배포 가능한 아키텍처 단위"의 분해라면, 이 문서는 "한 모델이 일관성을 유지하는 언어적·의미적 경계"의 분해다. Bounded Context 하나가 항상 마이크로서비스 하나와 일치하지는 않는다. 하나의 모놀리스 안에 Bounded Context가 4~5개 들어 있을 수도 있고, 반대로 너무 잘게 쪼갠 마이크로서비스 두세 개가 사실은 같은 Context였다는 사실이 나중에 드러나기도 한다.

Aggregate, Entity, Repository 같은 Context 내부의 빌딩 블록은 [DDD_Building_Blocks.md](DDD_Building_Blocks.md)에서, Context 간 통신의 한 형태인 도메인 이벤트는 [Domain_Event.md](Domain_Event.md)에서 다룬다.

---

## Bounded Context란 무엇인가

### 모델이 일관성을 유지하는 경계

Bounded Context는 특정 도메인 모델과 그 모델을 표현하는 유비쿼터스 언어가 일관된 의미를 유지하는 명시적 경계를 말한다. 핵심은 "명시적"이라는 부분이다. 경계가 어디까지인지가 분명하지 않으면, 같은 클래스 이름이 코드 곳곳에서 조금씩 다른 의미로 쓰이면서 모델이 서서히 부패한다.

신입 시절 한 모놀리스에서 `User`라는 이름의 클래스가 12군데 모듈에서 각자 조금씩 다른 필드를 들고 있는 걸 본 적이 있다. 인증 모듈의 User는 비밀번호 해시와 권한 토큰을 들고 있었고, 마케팅 모듈의 User는 동의 항목과 수신 채널을 들고 있었으며, 정산 모듈의 User는 세금 정보와 사업자 등록번호를 들고 있었다. 누군가 회원 가입 화면에 필드를 하나 추가하면 이 12개 User에 흩어진 매핑 코드가 전부 깨졌다. 이게 Bounded Context를 무시한 결과다. "User"라는 단어는 같지만, 각 모듈에서 부르는 User는 사실 다른 모델이었다.

### 컨텍스트가 다르면 같은 단어가 다른 모델이다

이커머스 도메인에서 "주문(Order)"이라는 단어를 보자.

- **카트 컨텍스트**의 Order: 아직 결제 전 상태의 임시 묶음. 수량 변경, 상품 추가/삭제가 자유롭다.
- **주문 처리 컨텍스트**의 Order: 결제까지 완료된 확정 주문. 주문번호가 부여되고 상태 머신을 따라간다.
- **배송 컨텍스트**의 Order: 운송장 번호와 매핑된 배송 단위. 한 개 주문이 두 개 운송장으로 쪼개지기도 한다.
- **정산 컨텍스트**의 Order: 매출 인식과 부가세 계산의 단위. 환불 발생 시 음수 매출로 처리된다.

같은 "Order"라는 단어를 쓰지만 네 곳의 모델은 다르다. 카트의 Order에는 "결제 완료 시간"이라는 필드가 의미가 없고, 정산의 Order에는 "장바구니 추가 시각"이 의미가 없다. 이걸 하나의 Order 클래스로 통합하려고 하면 필드가 30~40개로 불어나고, 한쪽 컨텍스트의 변경이 나머지 세 곳을 모두 건드리게 된다.

### 컨텍스트 경계 = 모델 번역의 경계

Bounded Context의 경계를 넘는 순간 모델은 번역되어야 한다. 카트 컨텍스트가 "OrderPlaced" 이벤트를 발행하면, 주문 처리 컨텍스트는 그 페이로드를 자기 컨텍스트의 Order로 다시 만들어낸다. 그대로 들고 가는 게 아니라 자기 모델로 변환하는 것이 원칙이다. 이 번역이 빠지면 컨텍스트 사이가 모델 단위로 결합되어, 한쪽 컨텍스트가 필드 하나만 바꿔도 다른 쪽이 깨진다.

---

## 같은 용어, 다른 의미 — 실제 사례

### "고객(Customer)"의 변주

규모가 어느 정도 있는 시스템에서 "고객"이라는 단어를 컨텍스트별로 다 펴보면 거의 항상 다음과 같은 모습이 나온다.

```
회원 가입 컨텍스트의 Customer:
  - id, email, password_hash, agreed_at, marketing_opt_in
  - 행위: register, withdraw, changePassword

마케팅 컨텍스트의 Customer:
  - id, segment, ltv, last_active_at, channels
  - 행위: classifySegment, sendCampaign, recordEngagement

CS 컨텍스트의 Customer:
  - id, vip_level, complaint_count, last_contact_at, memo
  - 행위: assignAgent, escalate, attachNote

정산 컨텍스트의 Customer (B2B):
  - id, business_no, tax_invoice_email, payment_term
  - 행위: issueTaxInvoice, calculateMonthlyDue
```

같은 사람을 가리키지만 각 컨텍스트가 보는 단면이 다르다. 회원 가입 컨텍스트는 인증의 주체로 본다. 마케팅 컨텍스트는 행동 패턴을 가진 세그먼트의 한 점으로 본다. CS 컨텍스트는 응대해야 할 상대로 본다. 정산 컨텍스트는 청구 대상으로 본다.

이걸 하나의 `Customer` 테이블로 두고 모든 컨텍스트가 직접 조회하게 만들면, 이 테이블이 곧 시스템의 결합 중심이 된다. 마케팅에서 새로운 세그먼트 필드가 필요하다고 회원 테이블에 컬럼을 추가하면, CS 화면을 만드는 팀이 갑자기 마이그레이션 영향을 받는다. 컨텍스트별로 자기 Customer 모델을 따로 들고, 공통 식별자(`customer_id`)만 공유하는 게 정석이다.

### "예약(Reservation)"이 컨텍스트마다 다르게 흐른다

호텔 시스템에서 "예약"이 어떻게 변하는지를 보면 컨텍스트의 의미가 와닿는다.

- **검색 컨텍스트**: 예약은 잠재 행위다. 객실 가용성 캐시와 가격 표시만 다룬다.
- **예약 트랜잭션 컨텍스트**: 예약은 객실 점유 권한이다. 결제와 묶인 트랜잭션의 단위.
- **체크인 컨텍스트**: 예약은 "입실 자격"이다. 본인 확인과 객실 배정에 쓰인다.
- **수익 관리 컨텍스트**: 예약은 매출 예측의 인풋이다. 취소율, 노쇼율과 함께 통계로 다뤄진다.

수익 관리 컨텍스트의 Reservation에는 고객 이름이 사실상 의미가 없고, 체크인 컨텍스트의 Reservation에는 매출 예측 가중치가 의미가 없다. 컨텍스트를 나누지 않으면 "왜 수익 관리 화면에 고객 개인정보가 보이지" 같은 보안 이슈가 따라온다.

---

## Context Map — 컨텍스트 간 관계 패턴

Context Map은 시스템에 존재하는 Bounded Context들과 그들 사이의 관계를 그린 지도다. 어떤 컨텍스트가 어떤 컨텍스트에 의존하고, 그 관계의 성격이 무엇인지를 명시한다. 관계의 성격이란 결국 "한쪽 모델이 바뀌었을 때 다른 쪽이 어떻게 영향을 받는가"의 문제다.

### Shared Kernel

두 컨텍스트가 모델의 일부를 의도적으로 공유하는 관계다. 공통 라이브러리, 공통 모듈로 묶어서 양쪽이 같은 코드를 임포트한다.

언뜻 효율적으로 보이지만 실무에서 잘 안 쓴다. Shared Kernel에 있는 모델을 한쪽이 변경하려면 다른 쪽 팀의 동의를 받아야 하기 때문이다. 두 팀의 릴리즈 사이클이 강하게 묶이고, Shared Kernel을 아무도 책임지지 않으면 점점 부패한다. 정말로 두 컨텍스트가 떼어놓을 수 없는 핵심 모델을 공유한다는 확신이 있을 때만 쓰는 게 좋다. 통화(Currency), 국가 코드, 측정 단위 같은 진짜 변하지 않는 값 객체 정도에 한정하는 편이 안전하다.

### Customer-Supplier

상류(Upstream)와 하류(Downstream)가 명확한 협력 관계다. 하류 팀이 자신의 요구사항을 상류 팀에 전달할 수 있고, 상류 팀이 그걸 일정에 반영해 준다. 양쪽이 같은 회사 안의 다른 팀일 때 자주 쓴다.

예를 들어 주문 컨텍스트(상류)가 배송 컨텍스트(하류)에 데이터를 흘려주는 관계다. 배송 팀이 "주소 정규화 필드를 페이로드에 추가해 주세요"라고 요청하면 주문 팀이 우선순위를 받아서 작업한다. 이 관계가 성립하려면 두 팀 사이의 커뮤니케이션 채널과 우선순위 협의 프로세스가 실제로 작동해야 한다. 그게 안 되면 다음 패턴인 Conformist로 떨어진다.

### Conformist

하류가 상류 모델을 그대로 따르는 관계다. 상류 팀에 영향력을 행사할 수 없을 때 선택한다. 외부 SaaS API를 쓰거나, 사내라도 우선순위 협상이 안 되는 다른 팀의 시스템에 의존할 때가 여기에 해당한다.

Conformist 관계는 단순하지만 위험이 크다. 상류 모델이 바뀌면 하류 코드가 같이 깨지고, 상류 모델의 어색한 부분(예: 어이없는 enum 값, 일관성 없는 필드명)이 하류 도메인 안에 그대로 박힌다. 그래서 Conformist는 "임시로 빨리 가야 할 때"만 선택하고, 가능하면 다음 패턴인 Anti-Corruption Layer로 옮긴다.

### Anti-Corruption Layer (ACL)

외부 모델이 내부 도메인으로 새어 들어오지 않도록 막는 변환 계층이다. 외부의 어색한 모델, 레거시의 이상한 데이터 구조, 다른 팀의 부패한 도메인이 우리 컨텍스트에 침투하지 못하게 한다. 실무에서 가장 자주 쓰는 Context Map 패턴이다.

```java
// 외부 결제 SDK의 응답 구조 (우리가 통제할 수 없는 모델)
public class ExternalPaymentResponse {
    public String txn_id;
    public int rslt_cd;          // 0=성공, 1=실패, 2=대기, 99=알 수 없음
    public String rslt_msg;
    public String approved_at;   // "20260501143022" 형태
    public Map<String, Object> meta;
}

// ACL — 외부 모델을 우리 도메인으로 번역
@Component
public class PaymentGatewayAdapter {

    private final ExternalPaymentClient client;

    public PaymentResult charge(PaymentRequest request) {
        ExternalPaymentResponse raw = client.request(toExternalForm(request));
        return translate(raw);
    }

    private PaymentResult translate(ExternalPaymentResponse raw) {
        PaymentStatus status = switch (raw.rslt_cd) {
            case 0  -> PaymentStatus.APPROVED;
            case 1  -> PaymentStatus.DECLINED;
            case 2  -> PaymentStatus.PENDING;
            default -> PaymentStatus.UNKNOWN;
        };

        LocalDateTime approvedAt = raw.approved_at == null
                ? null
                : LocalDateTime.parse(raw.approved_at, DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));

        return new PaymentResult(
                new TransactionId(raw.txn_id),
                status,
                approvedAt,
                raw.rslt_msg
        );
    }
}
```

ACL의 핵심은 우리 도메인 안에서는 외부 모델의 흔적이 보이지 않아야 한다는 것이다. `rslt_cd`라는 어색한 필드명, `99=알 수 없음`이라는 기괴한 코드 체계가 도메인 코드에 새어 들어오면 안 된다. 도메인 객체는 `PaymentStatus.APPROVED` 같은 깔끔한 모델만 본다.

ACL을 안 두면 어떻게 되나. 외부 결제사를 한 군데서 두 군데로 늘리는 순간, 결제사마다 응답 형식이 다른데 그 분기가 비즈니스 로직 곳곳에 박혀 있게 된다. 결제사 교체가 "코드 한 군데 갈아끼우기"가 아니라 "도메인 전체를 헤집는 작업"이 된다.

### Open Host Service (OHS)

상류 컨텍스트가 자신의 모델을 외부에 공개할 때 표준화된 프로토콜과 모델을 제공하는 패턴이다. 하류가 여러 개일 때 각각에 맞춰 변환하지 않고, 표준 인터페이스 하나만 잘 만들어 두는 것이다.

REST API의 공개 스펙, gRPC 서비스 정의, GraphQL 스키마가 OHS의 흔한 형태다. 내부 모델과 OHS 모델은 다르다. 내부 Aggregate를 그대로 응답에 노출하면, 내부 리팩터링 한 번에 모든 클라이언트가 깨진다. OHS의 모델은 의도적으로 안정성을 우선해서 설계해야 한다.

### Published Language

여러 컨텍스트가 통신할 때 공유하는 잘 정의된 공용 언어다. JSON 스키마, Avro 스키마, Protobuf 정의 같은 게 여기에 해당한다. OHS와 자주 함께 쓰인다. OHS가 "문(door)"이라면 Published Language는 "그 문 너머에서 오가는 말의 문법"이다.

이벤트 기반 통신에서 특히 중요하다. `OrderPlaced` 이벤트의 페이로드 스키마가 Published Language로 정의되어 있으면, 새로 생긴 구독자도 그 스키마만 보고 자기 코드를 작성할 수 있다. Schema Registry(Confluent, Apicurio 등)를 두는 이유가 이걸 강제하기 위해서다.

```json
// OrderPlaced 이벤트의 Published Language (Avro 스키마 일부)
{
  "type": "record",
  "name": "OrderPlaced",
  "namespace": "com.shop.order.v1",
  "fields": [
    {"name": "orderId", "type": "string"},
    {"name": "customerId", "type": "string"},
    {"name": "occurredAt", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "totalAmount", "type": {
      "type": "record",
      "name": "Money",
      "fields": [
        {"name": "amount", "type": "string"},
        {"name": "currency", "type": "string"}
      ]
    }}
  ]
}
```

Published Language는 한 번 공개되면 함부로 못 바꾼다. 필드를 빼는 변경, 타입을 바꾸는 변경은 호환성을 깨뜨린다. 그래서 처음에 페이로드를 설계할 때 "이 안에 들어가는 모든 필드는 미래에도 유지될 수 있는가"를 따지게 된다. 자세한 호환성 전략은 [API_버전_관리.md](../MSA/API_버전_관리.md) 쪽을 보면 된다.

### Separate Ways

두 컨텍스트가 통합할 가치가 없다고 판단해서 의도적으로 갈라서는 관계다. 통합 비용이 통합으로 얻는 이득보다 클 때 선택한다.

회의록 시스템과 회계 시스템처럼 정말 서로 무관한 영역, 또는 한 도메인을 두 컨텍스트가 각자의 방식으로 들고 가는 게 더 빠른 경우다. 한 회사 안에서 마케팅이 자체 분석 시스템에 고객 데이터를 직접 적재하고, 정산 시스템도 별도로 자기 데이터를 쌓는 식이다. 두 시스템을 통합하려면 막대한 매핑 비용이 들고, 어차피 서로의 데이터를 거의 안 보기 때문이다.

Separate Ways는 "통합을 안 한다"는 명시적 결정이다. 무언가가 빠졌거나 잊힌 것과는 다르다. Context Map에 Separate Ways를 그어 두면, 나중에 누가 "왜 이 둘을 안 묶었지"라고 물었을 때 의도를 설명할 수 있다.

### Context Map을 그릴 때 주의할 점

```
[카탈로그] ── publishes ──▶ [검색]              (OHS + Published Language)
[주문]     ── upstream ──▶ [배송]               (Customer-Supplier)
[주문]     ── publishes ──▶ [정산]              (Published Language)
[정산]     ── conforms to ──▶ [외부 회계 시스템] (Conformist, ACL 검토 중)
[추천]     ── separate ──── [정산]              (Separate Ways)
```

Context Map은 "지금 어떤 모양인가"와 "어떤 모양이어야 하는가"를 모두 담을 수 있다. 둘을 구분해서 그리는 게 좋다. 현재 Conformist지만 ACL을 도입할 계획이라면 그 의도를 표시한다. 그래야 어디부터 손을 댈지가 보인다.

---

## Context 경계를 코드와 패키지 구조로 표현하기

### 패키지 구조 = Context 경계의 1차 표현

코드 안에서 Bounded Context를 가장 먼저 드러내는 방법이 패키지 구조다. 잘 짠 코드를 열어 보면 최상위 패키지가 컨텍스트 단위로 나뉜다.

```
com.shop
 ├── catalog           ← 카탈로그 컨텍스트
 │    ├── domain
 │    ├── application
 │    └── infrastructure
 ├── order             ← 주문 컨텍스트
 │    ├── domain
 │    ├── application
 │    └── infrastructure
 ├── payment           ← 결제 컨텍스트
 │    ├── domain
 │    ├── application
 │    └── infrastructure
 └── shipment          ← 배송 컨텍스트
      ├── domain
      ├── application
      └── infrastructure
```

이 구조에서 중요한 건 한 컨텍스트의 `domain` 패키지가 다른 컨텍스트의 `domain` 패키지를 임포트하지 않는 것이다. `order.domain`이 `payment.domain.Payment`를 직접 가져다 쓰는 순간 두 도메인이 결합된다. 다른 컨텍스트의 데이터가 필요하면 ID로 참조하거나, 자기 컨텍스트 안에 자기만의 모델로 다시 정의한다.

### 계층(layer) 우선이 아니라 컨텍스트(context) 우선

다음과 같은 구조는 흔하지만 Bounded Context를 코드에 표현하지 못한 형태다.

```
com.shop
 ├── controller        ← 모든 컨텍스트의 컨트롤러가 한곳에
 ├── service
 ├── repository
 └── domain            ← 모든 컨텍스트의 도메인 모델이 한곳에
```

이 구조에서는 `domain` 패키지를 열면 Order, Payment, Customer, Shipment가 한꺼번에 보인다. 누군가 Order에서 Payment를 import하더라도 IDE가 경고하지 않고, 컨텍스트의 경계가 흐려진다. 컨텍스트별 패키지를 먼저 두고 그 안에 계층을 두는 구조가 경계를 강제하기에 훨씬 낫다.

### 모듈로 한 단계 더 강제하기

같은 모놀리스 안에서 컨텍스트 경계를 더 단단히 만들려면 빌드 시스템 모듈로 분리하는 방법이 있다. Gradle 멀티 프로젝트, Maven 멀티 모듈로 컨텍스트마다 모듈을 만들면 의존성 그래프가 빌드 도구 수준에서 검증된다.

```
shop-monolith/
 ├── catalog/build.gradle          (의존: 없음)
 ├── order/build.gradle            (의존: catalog의 공개 API만)
 ├── payment/build.gradle          (의존: order의 공개 API만)
 ├── shipment/build.gradle         (의존: order의 공개 API만)
 └── shared-kernel/build.gradle    (의존: 없음, 정말 공유할 모델만)
```

각 모듈이 외부에 노출하는 API를 의도적으로 좁게 가져가면, 다른 컨텍스트는 그 좁은 표면에만 의존한다. 내부 도메인 모델은 패키지 가시성으로 막거나 별도 internal 모듈로 격리한다. Java 9 이상의 모듈 시스템(JPMS)이나 ArchUnit 같은 도구로 의존성 규칙을 테스트로 강제하는 것도 좋다.

```java
// ArchUnit으로 컨텍스트 간 의존성을 테스트로 강제
@AnalyzeClasses(packages = "com.shop")
class BoundedContextRulesTest {

    @ArchTest
    static final ArchRule order_domain_should_not_depend_on_other_contexts =
            noClasses()
                    .that().resideInAPackage("..order.domain..")
                    .should().dependOnClassesThat()
                    .resideInAnyPackage(
                            "..payment.domain..",
                            "..shipment.domain..",
                            "..catalog.domain.."
                    );
}
```

이런 테스트를 하나 박아 두면, 누가 무심코 다른 컨텍스트의 도메인을 임포트했을 때 CI에서 바로 잡힌다.

### DB 스키마 분리

같은 DB 인스턴스를 쓰더라도 컨텍스트마다 스키마(또는 테이블 prefix)를 분리하는 게 좋다. 한 컨텍스트가 다른 컨텍스트의 테이블을 직접 SELECT하지 못하게 하는 것이 첫 번째 방어선이다.

```sql
-- 컨텍스트별 스키마 분리
CREATE SCHEMA catalog;
CREATE SCHEMA order_ctx;     -- order는 SQL 예약어라 변형
CREATE SCHEMA payment;
CREATE SCHEMA shipment;

-- 각 애플리케이션 사용자가 자기 스키마만 접근 가능하도록
GRANT ALL ON SCHEMA order_ctx TO order_app_user;
REVOKE ALL ON SCHEMA payment FROM order_app_user;
```

직접 조회하는 길을 막아 두면, 컨텍스트 간 데이터가 필요할 때 자연스럽게 API나 이벤트로 가져오게 된다. "잠깐만 JOIN 한 번이면 끝나는데" 하면서 컨텍스트 경계를 무너뜨리는 것을 물리적으로 차단하는 효과가 크다.

---

## Context 간 통신 방식

Context 간 통신은 크게 동기와 비동기로 나뉘고, 동기 안에서도 모델이 새어 들어오느냐 막히느냐로 다시 갈린다.

### 동기 호출 + ACL

상대 컨텍스트의 데이터가 즉시 필요할 때 쓴다. 한 컨텍스트의 응답을 기다려서 다음 처리를 진행하는 패턴이다.

```java
// 주문 컨텍스트 안에서 카탈로그 컨텍스트의 정보가 필요한 경우
@Service
public class OrderApplicationService {

    private final CatalogClient catalogClient;        // 카탈로그 컨텍스트의 OHS 호출
    private final CatalogTranslator translator;       // ACL — 카탈로그 모델을 주문 컨텍스트로 번역

    public Order placeOrder(OrderCommand command) {
        for (LineItemCommand item : command.items()) {
            CatalogProductDto remote = catalogClient.fetch(item.productId());
            ProductSnapshot snapshot = translator.toSnapshot(remote);
            // snapshot은 주문 컨텍스트의 자체 모델
            // 카탈로그의 모든 필드를 들고 오지 않고, 주문에 필요한 것만 들고 온다
            command.attachSnapshot(item.productId(), snapshot);
        }
        return orderFactory.create(command);
    }
}
```

여기서 `ProductSnapshot`은 주문 컨텍스트의 모델이다. 카탈로그 컨텍스트의 `Product`를 그대로 가져다 쓰지 않는다. 주문 입장에서는 주문 시점의 상품명과 가격만 알면 된다. 이미지 URL이나 카테고리 트리 같은 카탈로그의 풍부한 정보는 주문 컨텍스트에 들어올 필요가 없다.

동기 호출의 단점은 가용성 결합이다. 카탈로그가 죽으면 주문이 못 들어온다. 그래서 동기로 가져온 데이터를 주문 컨텍스트 안에 스냅샷으로 저장해 두는 패턴이 자주 쓰인다. 주문이 한 번 들어오고 나면 그 주문에 필요한 카탈로그 정보는 더 이상 카탈로그를 호출하지 않아도 된다.

### 비동기 이벤트 + 자체 Read Model

다른 컨텍스트의 상태 변화를 구독해서 자기 컨텍스트 안에 필요한 형태의 Read Model로 다시 만드는 패턴이다.

```
[카탈로그] ── ProductPriceChanged 이벤트 ──▶ Kafka ──▶ [주문]
                                                       └── 주문 컨텍스트 내부의
                                                           product_snapshot 테이블 갱신
```

주문 컨텍스트가 카탈로그를 매번 호출하지 않고, 카탈로그가 발행하는 이벤트를 듣고 자기 안에 필요한 데이터를 미리 만들어 둔다. 이렇게 하면 가용성 결합이 풀리고, 조회 성능도 자기 DB 안에서 끝난다.

대가는 결과적 일관성(eventual consistency)이다. 카탈로그에서 가격이 바뀌고 주문 컨텍스트에 반영되기까지 수 초~수 분의 지연이 있을 수 있다. 이 지연이 비즈니스적으로 허용되는지 확인해야 한다. 결제 직전 가격 표시처럼 정확성이 중요한 경우에는 동기 호출로 한 번 더 확인하는 식의 보정이 필요하다.

이벤트 기반 통신의 인프라적 보장(브로커 장애, 중복 처리, 순서 보장)은 [메시지_큐_및_분산_락.md](../MSA/메시지_큐_및_분산_락.md)와 [트랜잭셔널_아웃박스_패턴.md](../MSA/트랜잭셔널_아웃박스_패턴.md)에서 다룬다.

### 통신 방식 선택 기준

선택은 다음 질문들로 좁혀진다.

- 상대 컨텍스트의 데이터가 "지금 이 트랜잭션 안에서" 정확해야 하는가? → 동기
- 약간의 지연을 두고 받아도 비즈니스 결과가 같은가? → 비동기 이벤트
- 상대 컨텍스트가 죽었을 때 우리 컨텍스트도 같이 죽어도 되는가? → 동기 가능, 아니면 비동기로 결합 풀기
- 데이터를 한 번 가져오고 그 후엔 우리가 들고 있을 수 있는가? → 가져온 시점의 스냅샷을 저장하는 패턴 추천

실무에서는 한 컨텍스트와 통신할 때 이 두 방식을 섞어 쓴다. 결제 직전 가격 확인은 동기로, 가격 변동 추적용 Read Model 갱신은 비동기 이벤트로 하는 식이다.

---

## 경계를 잘못 잡았을 때 나타나는 신호

Context 경계는 한 번에 정답을 못 찾는다. 처음에 그은 경계가 시간이 지나면서 어긋나고, 비즈니스가 자라면서 다시 그어야 할 때가 온다. 다음 신호들이 나타나면 경계를 점검할 시점이다.

### 신호 1: 한 변경이 항상 두세 컨텍스트를 동시에 수정하게 만든다

기능 하나를 추가하는데 매번 컨텍스트 A, B, C의 코드를 같이 손대야 한다면, 그 셋은 사실 하나의 컨텍스트를 잘못 쪼갠 결과일 가능성이 높다. 진짜로 분리되어 있다면 한 변경은 한 컨텍스트 안에서 끝나야 한다.

주문과 결제를 별도 컨텍스트로 나눴는데, 새 결제 수단을 추가할 때마다 주문 도메인의 상태 머신을 같이 수정해야 한다면 경계가 잘못 그어진 것이다. 둘 사이의 결합이 도메인 수준에서 너무 강하다는 뜻이다.

### 신호 2: 한 컨텍스트가 다른 컨텍스트를 너무 자주 호출한다

컨텍스트 A가 한 요청을 처리하면서 컨텍스트 B를 5번, 10번 호출한다면 둘은 사실 같은 컨텍스트로 묶이는 게 자연스럽다. 같은 데이터를 여러 번 가져오는 것은 데이터의 위치가 잘못됐다는 신호다.

이 신호는 N+1 호출 문제로도 자주 드러난다. 주문 목록을 조회하면서 각 주문의 결제 상태를 가져오기 위해 결제 컨텍스트를 N번 호출한다면, 결제 상태 일부는 주문 컨텍스트가 자체 Read Model로 들고 있는 것이 맞다.

### 신호 3: 같은 단어를 두 컨텍스트가 정확히 같은 의미로 쓴다

"고객"이 회원 컨텍스트와 마케팅 컨텍스트에서 정확히 같은 필드와 같은 행위를 갖는다면, 둘은 사실 한 컨텍스트일 수 있다. Bounded Context의 핵심은 의미의 변주다. 같은 단어가 같은 의미라면 굳이 나눌 이유가 없다.

반대로, 한 컨텍스트 안에서 같은 단어가 다른 의미로 쓰이고 있다면 그 컨텍스트를 더 쪼개야 한다는 신호다. 한 모듈의 코드를 읽다가 "이 메서드의 Order는 카트의 Order인가, 확정된 Order인가?"가 헷갈리기 시작하면 그 모듈은 사실 두 컨텍스트가 섞여 있는 것이다.

### 신호 4: 트랜잭션이 컨텍스트 경계를 자주 넘는다

분산 트랜잭션, Saga, 보상 트랜잭션이 자꾸 등장하면 경계를 점검해야 한다. 두 컨텍스트가 항상 한 트랜잭션처럼 동작해야 한다면, 그 둘은 사실 한 Aggregate, 더 나아가 한 Bounded Context에 속해야 할 가능성이 있다.

물론 진짜로 다른 컨텍스트지만 결과적 일관성으로 처리해야 하는 경우도 있다. 주문과 적립금이 그렇다. 하지만 비즈니스 요구가 "둘이 무조건 강한 일관성을 가져야 한다"라면 그건 경계가 잘못 그어진 것이다.

### 신호 5: 컨텍스트 간 통신 페이로드가 비대해진다

컨텍스트 A가 컨텍스트 B에 보내는 이벤트나 API 응답이 점점 커진다. 처음에 5개 필드였던 것이 30개가 된다. 이건 B가 A의 데이터에 점점 깊이 의존한다는 신호다. 결국 B가 A의 내부 모델을 거의 그대로 들고 있게 되면, 두 컨텍스트는 모델 단위로 결합된 셈이다.

이 경우 둘 중 하나다. 정말 그 데이터가 다 필요하면 두 컨텍스트를 합쳐야 하고, 그 정도까지는 아니라면 페이로드 설계를 다시 해서 B가 정말 필요한 정보만 골라 받게 해야 한다.

---

## 경계를 다시 그리는 방법

경계가 잘못됐다는 진단이 섰다면, 어떻게 다시 그어야 하는가. 한 번에 큰 수술을 하는 것보다는 점진적으로 옮기는 편이 안전하다.

### 합쳐야 할 때

두 컨텍스트가 사실은 하나라는 결론에 도달했다면, 다음 순서로 합친다.

1. **공유 Aggregate 파악**: 두 컨텍스트가 공유해야 하는 핵심 모델을 식별한다.
2. **한쪽으로 모델 통합**: 두 컨텍스트 중 의미적으로 더 강한 쪽(예: 주문)을 기준으로 다른 쪽(결제)의 모델을 흡수한다.
3. **API와 이벤트 단순화**: 컨텍스트 간 호출이었던 것을 메서드 호출로 바꾼다.
4. **DB 스키마 합치기**: 트랜잭션 일관성이 필요했던 데이터를 같은 트랜잭션 안에서 다룰 수 있도록 스키마를 통합한다.

이 작업은 사실상 마이크로서비스를 다시 합치는 일과 같다. 마이그레이션 비용이 크기 때문에 결정 전에 정말로 합쳐야 하는지를 충분히 검증해야 한다.

### 더 쪼개야 할 때

한 컨텍스트가 사실은 두세 개라는 결론이라면, 패키지 단위 분리부터 시작한다.

1. **단어 정리부터**: 컨텍스트 안에서 같은 단어가 다른 의미로 쓰이는 지점들을 모두 찾아서 새 이름을 붙인다. `Order`를 `CartOrder`와 `ConfirmedOrder`로 나누는 식이다. 이름을 나누는 순간 모델이 자연스럽게 나뉘기 시작한다.
2. **패키지 분리**: 새로 정의한 컨텍스트 단위로 패키지를 나눈다. 이 시점에서 컨텍스트 간 직접 의존이 드러난다.
3. **인터페이스 도입**: 컨텍스트 간 호출을 인터페이스로 추상화한다. 같은 프로세스 안에서 메서드 호출이지만, 곧 API 호출이나 이벤트로 바꿀 수 있는 형태로 만든다.
4. **모듈 분리**: 빌드 모듈로 분리해서 컴파일러가 경계를 강제하게 만든다.
5. **(필요시) 서비스 분리**: 별도 배포가 의미 있다면 마이크로서비스로 분리한다.

순서가 중요하다. 1~4단계는 모놀리스 안에서 안전하게 할 수 있고, 잘못됐다면 되돌리기 쉽다. 5단계로 가는 순간부터는 비용이 급격히 커지므로, 1~4단계에서 경계가 안정됐다는 확신이 든 후에 가는 것이 좋다.

### 경계 재조정의 비용을 줄이는 습관

경계가 변하는 것은 정상이다. 처음부터 완벽한 경계를 그릴 수 있다는 환상을 버리는 게 맞다. 변경 비용을 줄이려면 다음 습관이 도움이 된다.

- 컨텍스트 간 통신은 항상 인터페이스(API, 이벤트)를 거치게 한다. 직접 메서드 호출이나 DB JOIN을 허용하지 않는다.
- 컨텍스트 간에 흐르는 데이터는 항상 자기 모델로 번역한다. 외부 모델이 도메인에 새어 들어오지 않게 한다.
- Context Map을 문서로 유지한다. 머릿속에만 있는 경계는 사람이 바뀌면 사라진다.
- 경계 변경은 작은 단위로 자주 한다. "분기 한 번에 큰 재설계"보다 "스프린트마다 작은 조정"이 안전하다.

Bounded Context는 한 번 긋고 끝나는 선이 아니라, 도메인을 이해해 가면서 계속 다시 그리는 지도다. 처음에 잘못 그었더라도 그것이 잘못됐다는 신호를 빨리 알아차리고 고칠 수 있는 구조를 갖추는 것이 더 중요하다.
