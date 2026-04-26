---
title: BFF 패턴 (Backend for Frontend)
tags: [backend, msa, bff, api-gateway, graphql, architecture]
updated: 2026-04-06
---

# BFF 패턴 (Backend for Frontend)

## BFF가 뭔지

BFF는 클라이언트 유형별로 전용 API 서버를 두는 구조다. 모바일 앱, 웹 브라우저, 관리자 콘솔 같은 클라이언트마다 별도의 백엔드 서비스를 만든다.

일반적인 API Gateway는 모든 클라이언트의 요청을 하나의 진입점에서 처리한다. 여기서 문제가 생긴다. 모바일 앱은 데이터를 최소한으로 받아야 하고, 웹은 한 화면에 여러 도메인의 데이터를 한번에 보여줘야 하고, 관리자 콘솔은 내부 시스템 정보까지 포함해야 한다. 하나의 API로 이 요구사항을 전부 맞추려면 API가 점점 복잡해진다.

BFF는 이 문제를 클라이언트별 분리로 해결한다.

```
[모바일 앱] → [Mobile BFF] → [주문 서비스]
                             [결제 서비스]
                             [상품 서비스]

[웹 브라우저] → [Web BFF]  → [주문 서비스]
                             [결제 서비스]
                             [상품 서비스]

[관리자 콘솔] → [Admin BFF] → [주문 서비스]
                              [결제 서비스]
                              [사용자 관리 서비스]
```

각 BFF는 자기 클라이언트가 필요로 하는 형태로 데이터를 가공해서 내려준다. Mobile BFF는 응답에서 불필요한 필드를 제거하고, Web BFF는 여러 서비스 호출 결과를 하나의 응답으로 합친다.

---

## 실제 구현 구조

### 기본적인 BFF 서버 구성

Spring Boot로 Web BFF를 구성하면 대략 이런 모양이 된다.

```java
@RestController
@RequestMapping("/api/orders")
public class OrderBffController {

    private final OrderServiceClient orderClient;
    private final PaymentServiceClient paymentClient;
    private final ProductServiceClient productClient;

    @GetMapping("/{orderId}")
    public OrderDetailResponse getOrderDetail(@PathVariable Long orderId) {
        // 여러 서비스를 호출해서 웹에 맞는 응답을 조합한다
        OrderDto order = orderClient.getOrder(orderId);
        PaymentDto payment = paymentClient.getPayment(order.getPaymentId());
        List<ProductDto> products = productClient.getProducts(order.getProductIds());

        return OrderDetailResponse.builder()
                .orderId(order.getId())
                .orderStatus(order.getStatus())
                .paymentMethod(payment.getMethod())
                .paymentStatus(payment.getStatus())
                .products(products.stream()
                        .map(p -> ProductSummary.of(p.getName(), p.getPrice(), p.getThumbnailUrl()))
                        .toList())
                .build();
    }
}
```

같은 주문 조회인데 Mobile BFF는 다르게 내려준다.

```java
@RestController
@RequestMapping("/api/orders")
public class MobileOrderBffController {

    private final OrderServiceClient orderClient;
    private final PaymentServiceClient paymentClient;

    @GetMapping("/{orderId}")
    public MobileOrderResponse getOrderDetail(@PathVariable Long orderId) {
        OrderDto order = orderClient.getOrder(orderId);
        PaymentDto payment = paymentClient.getPayment(order.getPaymentId());

        // 모바일은 상품 상세 정보가 필요 없다. 주문 상태와 결제 정보만 내린다.
        return MobileOrderResponse.builder()
                .orderId(order.getId())
                .status(order.getStatus())
                .paymentStatus(payment.getStatus())
                .build();
    }
}
```

웹은 한 화면에 주문, 결제, 상품 정보를 전부 보여주니까 3개 서비스를 호출한다. 모바일은 목록에서 주문 상태만 보여주니까 2개만 호출하고 응답 필드도 적다.

### 비동기 호출로 응답 시간 줄이기

BFF에서 여러 서비스를 순차 호출하면 응답 시간이 길어진다. 서비스 3개를 각각 100ms씩 걸리면 300ms가 된다. 의존 관계가 없는 호출은 병렬로 처리한다.

```java
@GetMapping("/{orderId}")
public OrderDetailResponse getOrderDetail(@PathVariable Long orderId) {
    OrderDto order = orderClient.getOrder(orderId);

    // 결제와 상품 조회는 서로 의존성이 없으니 병렬 호출
    CompletableFuture<PaymentDto> paymentFuture =
            CompletableFuture.supplyAsync(() -> paymentClient.getPayment(order.getPaymentId()));
    CompletableFuture<List<ProductDto>> productsFuture =
            CompletableFuture.supplyAsync(() -> productClient.getProducts(order.getProductIds()));

    PaymentDto payment = paymentFuture.join();
    List<ProductDto> products = productsFuture.join();

    return OrderDetailResponse.of(order, payment, products);
}
```

주문 정보를 먼저 가져와야 결제 ID와 상품 ID를 알 수 있으니 주문 조회는 먼저 실행한다. 결제와 상품은 서로 독립적이니 동시에 호출한다. 300ms가 200ms로 줄어든다.

Spring WebFlux를 쓰면 이런 식으로 바뀐다.

```java
@GetMapping("/{orderId}")
public Mono<OrderDetailResponse> getOrderDetail(@PathVariable Long orderId) {
    return orderClient.getOrder(orderId)
            .flatMap(order -> Mono.zip(
                    paymentClient.getPayment(order.getPaymentId()),
                    productClient.getProducts(order.getProductIds())
            ).map(tuple -> OrderDetailResponse.of(order, tuple.getT1(), tuple.getT2())));
}
```

---

## BFF에서 처리하는 것과 하면 안 되는 것

BFF의 역할 범위를 명확히 잡아야 한다. 범위를 잘못 잡으면 BFF가 비대해지는 문제로 이어진다.

**BFF에서 처리하는 것:**

- 응답 데이터 조합: 여러 서비스의 응답을 클라이언트에 맞게 합치기
- 필드 필터링: 클라이언트가 쓰지 않는 필드 제거
- 데이터 포맷 변환: 날짜 포맷, 금액 단위, 다국어 처리
- 클라이언트별 인증/인가 흐름: 소셜 로그인은 웹과 모바일에서 흐름이 다르다
- 페이지네이션 어댑터: 웹은 offset 기반, 모바일은 cursor 기반 등

**BFF에서 하면 안 되는 것:**

- 비즈니스 로직: 할인 계산, 재고 차감 같은 로직은 도메인 서비스에 있어야 한다
- 데이터 직접 조회: BFF가 DB에 직접 접근하면 안 된다. 반드시 내부 서비스를 통해야 한다
- 서비스 간 오케스트레이션: 주문 생성 → 결제 → 재고 차감 같은 트랜잭션 흐름은 별도 오케스트레이션 서비스에서 처리한다

---

## GraphQL Federation과 비교

BFF와 비교 대상으로 자주 나오는 게 GraphQL Federation이다. 둘 다 "클라이언트가 필요한 데이터를 한번에 가져온다"는 문제를 해결하지만 접근 방식이 다르다.

### GraphQL Federation 구조

```
[클라이언트] → [Apollo Gateway/Router] → [주문 서브그래프]
                                        [결제 서브그래프]
                                        [상품 서브그래프]
```

각 도메인 서비스가 자기 도메인의 GraphQL 스키마(서브그래프)를 정의한다. Gateway가 이 스키마들을 합쳐서(Federation) 하나의 통합 스키마를 클라이언트에 제공한다.

```graphql
# 주문 서브그래프
type Order @key(fields: "id") {
    id: ID!
    status: String!
    paymentId: ID!
    productIds: [ID!]!
}

# 결제 서브그래프 - Order 타입을 확장한다
extend type Order @key(fields: "id") {
    id: ID! @external
    payment: Payment
}

type Payment {
    method: String!
    status: String!
    amount: Int!
}
```

클라이언트가 쿼리를 보내면 Gateway가 필요한 서브그래프에만 요청을 분배한다.

```graphql
# 웹에서는 전체 정보를 요청한다
query {
    order(id: "123") {
        status
        payment { method status amount }
        products { name price thumbnailUrl }
    }
}

# 모바일에서는 필요한 필드만 요청한다
query {
    order(id: "123") {
        status
        payment { status }
    }
}
```

### 핵심 차이

| 기준 | BFF | GraphQL Federation |
|------|-----|--------------------|
| 응답 형태 결정 | 서버(BFF)가 결정 | 클라이언트가 쿼리로 결정 |
| 클라이언트 추가 시 | 새 BFF 서버를 만든다 | 기존 스키마를 그대로 쓴다 |
| 팀 구조 | BFF마다 담당팀이 필요 | 각 도메인팀이 서브그래프 관리 |
| 오버페칭 | BFF가 적절히 조합 | 클라이언트가 필요한 것만 요청 |
| 러닝 커브 | REST 기반이라 낮다 | GraphQL 스키마 설계 이해 필요 |
| 캐싱 | HTTP 캐싱 그대로 사용 | 별도 캐싱 레이어 필요 |

### 어떤 상황에서 뭘 쓰는가

BFF가 맞는 경우:

- 클라이언트 유형이 2~3개이고 크게 늘어날 가능성이 없다
- 팀이 REST에 익숙하고 GraphQL 도입 비용을 감당하기 어렵다
- 클라이언트별 비즈니스 로직 차이가 크다 (모바일 전용 푸시 알림 연동 등)

GraphQL Federation이 맞는 경우:

- 클라이언트 유형이 많거나 자주 추가된다
- 각 도메인팀이 독립적으로 API를 발전시켜야 한다
- 오버페칭/언더페칭 문제가 심하다

실무에서는 둘 다 쓰는 경우도 있다. 외부 클라이언트(앱, 웹)는 GraphQL Gateway를 사용하고, 관리자 콘솔처럼 내부 도구는 별도 BFF를 두는 식이다.

---

## BFF가 비대해지는 문제

BFF 도입 초기에는 깔끔하다. 시간이 지나면서 문제가 생긴다.

### 비대화가 일어나는 과정

1단계: 주문 상세 페이지용 API를 BFF에 만든다. 3개 서비스 호출, 응답 조합.

2단계: "이 API에 배송 정보도 추가해주세요." 배송 서비스 호출이 추가된다.

3단계: "VIP 회원이면 할인 쿠폰 목록도 같이 내려주세요." 조건 분기가 생긴다.

4단계: "결제 실패 시 재시도 로직을 BFF에서 처리해주세요." 비즈니스 로직이 들어온다.

5단계: BFF가 7개 서비스를 호출하고, 조건 분기가 10개이고, 재시도 로직까지 있다. 더 이상 "프레젠테이션 레이어"가 아니다.

### 비대화를 알 수 있는 신호

- BFF에 if-else 분기가 많아진다: 클라이언트 버전별, 사용자 등급별 분기가 쌓이면 비즈니스 로직이 침투한 것이다
- 하나의 API 핸들러에서 호출하는 내부 서비스가 5개를 넘는다
- BFF의 코드 변경 빈도가 도메인 서비스보다 높다
- BFF 테스트가 어려워진다: Mock이 10개 필요한 테스트는 뭔가 잘못된 것이다

### 대응 방법

**1. 컴포지션 서비스 분리**

여러 서비스를 조합하는 로직이 복잡해지면 BFF에서 빼내서 별도 서비스로 만든다.

```
변경 전:
[Web BFF] → 주문 서비스 + 결제 서비스 + 상품 서비스 + 배송 서비스 + 쿠폰 서비스

변경 후:
[Web BFF] → [주문 상세 컴포지션 서비스] → 주문 서비스
                                         결제 서비스
                                         상품 서비스
                                         배송 서비스
                                         쿠폰 서비스
```

BFF는 컴포지션 서비스를 한번만 호출하면 된다. 데이터 조합 로직은 컴포지션 서비스가 담당한다. Web BFF와 Mobile BFF가 같은 컴포지션 서비스를 공유하되, 응답에서 필요한 필드만 골라서 내려주면 된다.

**2. BFF 코드 리뷰 기준 세우기**

PR 리뷰에서 다음 항목을 체크한다.

- BFF에 새로운 서비스 호출이 추가되면 "이게 BFF에 있어야 하는가?" 질문하기
- 조건 분기가 추가되면 해당 로직이 도메인 서비스에 있어야 하는 건 아닌지 확인
- BFF 핸들러 하나가 호출하는 서비스 수가 5개를 넘으면 컴포지션 서비스 분리 검토

**3. 공유 BFF 라이브러리 만들기**

Mobile BFF와 Web BFF에서 중복되는 코드가 생기면 공통 모듈로 뺀다. 서비스 클라이언트 코드, 공통 DTO 변환 로직, 에러 핸들링 같은 것들이 대상이다.

```
bff-common/
├── client/          # 내부 서비스 호출 클라이언트
├── dto/             # 공통 응답 DTO
└── error/           # 공통 에러 처리

mobile-bff/
├── (bff-common 의존)
└── ...

web-bff/
├── (bff-common 의존)
└── ...
```

단, 공통 모듈에 클라이언트별 로직이 들어가면 안 된다. 공통 모듈이 특정 클라이언트에 의존하는 순간 분리한 의미가 없어진다.

---

## 배포와 장애 격리

### BFF 단위 배포

BFF는 클라이언트별로 독립 배포가 가능하다. 모바일 앱 화면이 바뀌어서 Mobile BFF를 수정해도 Web BFF는 영향이 없다.

```yaml
# mobile-bff deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mobile-bff
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: mobile-bff
          image: registry/mobile-bff:1.2.0
          resources:
            requests:
              memory: "256Mi"
              cpu: "200m"
```

모바일 트래픽이 많은 서비스라면 Mobile BFF의 replica를 더 많이 잡고, Web BFF는 적게 잡는다. 각 BFF의 트래픽 특성에 맞게 스케일링 정책을 독립적으로 설정한다.

### 장애 격리

Mobile BFF에 장애가 나도 Web BFF는 정상 동작한다. 단일 API Gateway 구조에서는 Gateway가 죽으면 모든 클라이언트가 영향을 받지만, BFF 구조에서는 피해 범위가 해당 클라이언트로 한정된다.

다만 BFF가 호출하는 하위 서비스에 장애가 나면 여러 BFF가 동시에 영향을 받는다. 주문 서비스가 죽으면 Mobile BFF와 Web BFF 모두 주문 관련 기능이 안 된다. 이건 BFF 패턴의 한계가 아니라 MSA 공통 문제다. Circuit Breaker, Fallback 같은 장애 격리 패턴을 BFF 레벨에서 적용해야 한다.

---

## 실무에서 주의할 점

**BFF를 API Gateway와 혼동하지 않기**

API Gateway는 라우팅, 인증, 속도 제한 같은 인프라 관심사를 처리한다. BFF는 데이터 조합과 클라이언트 맞춤 응답을 처리한다. 둘은 같이 쓴다. 클라이언트 → API Gateway → BFF → 내부 서비스 순서로 요청이 흐른다. API Gateway에 BFF 역할을 합치면 Gateway가 비대해지는 같은 문제를 겪는다.

**BFF 수를 무한정 늘리지 않기**

클라이언트 유형이 생길 때마다 BFF를 만들면 관리가 안 된다. iOS BFF, Android BFF를 따로 만들 필요는 없다. iOS와 Android의 데이터 요구사항이 거의 같다면 Mobile BFF 하나로 충분하다. BFF를 나누는 기준은 플랫폼이 아니라 "데이터 요구사항의 차이"다.

**BFF 간 통신 금지**

Web BFF가 Mobile BFF를 호출하는 구조를 만들면 안 된다. BFF 간 의존이 생기면 독립 배포가 불가능해지고 장애가 전파된다. 공통 로직이 필요하면 공유 라이브러리나 하위 서비스로 빼야 한다.
