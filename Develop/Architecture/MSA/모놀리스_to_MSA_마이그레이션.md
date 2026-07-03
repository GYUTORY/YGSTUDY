---
title: 모놀리스 to MSA 마이그레이션
tags: [msa, migration, strangler-fig, branch-by-abstraction, dual-write, database-split, monolith]
updated: 2026-04-01
---

# 모놀리스 to MSA 마이그레이션

## 왜 마이그레이션이 어려운가

모놀리스에서 MSA로 전환한다는 건, 운행 중인 비행기의 엔진을 교체하는 것과 비슷하다. 서비스는 멈추면 안 되고, 데이터는 유실되면 안 되고, 기존 기능은 그대로 동작해야 한다.

서비스 분해나 도메인 설계는 "어디를 자를 것인가"를 다루지만, 실제 마이그레이션은 그 이후의 문제다. 기존 모놀리스의 트래픽을 어떻게 새 서비스로 넘기는가. 데이터베이스를 어떤 순서로 분리하는가. 새 서비스에 문제가 생기면 어떻게 되돌리는가. 이런 실무 과정이 없으면 설계만 하고 실행은 못 하게 된다.

한 번에 전환하는 빅뱅 방식은 거의 실패한다. 수개월 동안 새 시스템을 만들고, 특정 날짜에 한 번에 전환하면, 잘못된 부분을 발견했을 때 되돌리기가 불가능에 가깝다. 그래서 점진적 마이그레이션 패턴들이 존재한다.

## Strangler Fig 패턴

### 개념

기존 모놀리스를 감싸는 형태로 새 서비스를 하나씩 붙여나가는 방식이다. 이름은 열대 지방의 교살무화과(Strangler Fig)에서 따왔다. 기존 나무를 감싸면서 자라다가 결국 기존 나무를 대체하는 것처럼, 모놀리스의 기능을 하나씩 새 서비스로 옮기면서 최종적으로 모놀리스를 제거한다.

### 동작 구조

모놀리스 앞에 라우팅 레이어(프록시)를 둔다. 이 프록시가 요청을 모놀리스로 보낼지, 새 서비스로 보낼지 결정한다.

```
클라이언트 → 프록시(라우팅 레이어) → 모놀리스
                                    → 새 서비스 A
                                    → 새 서비스 B
```

마이그레이션 진행 과정은 이렇다.

**1단계: 프록시 배치**

모놀리스 앞에 API Gateway나 리버스 프록시를 둔다. 처음에는 모든 요청을 모놀리스로 포워딩한다. 기존 동작에 영향이 없어야 한다.

```nginx
# nginx 예시 - 초기 상태: 전부 모놀리스로 라우팅
upstream monolith {
    server monolith-app:8080;
}

server {
    location / {
        proxy_pass http://monolith;
    }
}
```

**2단계: 새 서비스 배포 + 라우팅 전환**

특정 경로의 요청을 새 서비스로 보낸다.

```nginx
upstream monolith {
    server monolith-app:8080;
}

upstream product-service {
    server product-service:8081;
}

server {
    # 상품 관련 API만 새 서비스로 라우팅
    location /api/products {
        proxy_pass http://product-service;
    }

    # 나머지는 모놀리스
    location / {
        proxy_pass http://monolith;
    }
}
```

**3단계: 반복**

서비스를 하나씩 떼어내면서 모놀리스의 코드를 줄여나간다. 모놀리스에서 해당 기능의 코드를 삭제한다.

### 라우팅 전환 시 주의점

라우팅을 한 번에 100% 전환하면 안 된다. 비율을 단계적으로 올려야 한다.

```yaml
# 카나리 배포 형태의 트래픽 분배 (Istio VirtualService 예시)
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: product-routing
spec:
  hosts:
    - product-api
  http:
    - route:
        - destination:
            host: monolith
          weight: 90
        - destination:
            host: product-service
          weight: 10
```

처음에는 10% 정도만 새 서비스로 보내면서 에러율, 응답시간, 데이터 정합성을 확인한다. 문제가 없으면 비율을 높인다. 50% → 90% → 100% 순서로 전환한다.

모니터링 없이 비율을 올리면 안 된다. 새 서비스의 에러율이 기존 대비 높아지면 즉시 비율을 되돌려야 한다.

### 롤백 계획

Strangler Fig의 롤백은 간단하다. 프록시 설정을 되돌리면 트래픽이 다시 모놀리스로 간다.

하지만 데이터를 이미 새 서비스의 DB에 쓰기 시작했다면, 라우팅만 되돌리는 것으로는 부족하다. 모놀리스 DB와 새 서비스 DB 사이의 데이터 정합성이 깨져 있을 수 있다. 이 문제는 뒤에서 다루는 듀얼 라이트와 연결된다.

## Branch by Abstraction

### 개념

모놀리스 내부에서 코드 레벨로 전환하는 방식이다. Strangler Fig이 외부 프록시로 트래픽을 분배한다면, Branch by Abstraction은 코드 내부에서 기존 구현과 새 구현을 전환한다.

모놀리스 코드베이스 안에서 작업하기 때문에, 인프라 변경 없이 마이그레이션을 시작할 수 있다.

### 적용 과정

**1단계: 추상화 레이어 삽입**

기존 코드에서 교체 대상 모듈을 호출하는 곳에 인터페이스를 끼워넣는다.

```java
// 기존 코드: NotificationSender를 직접 사용
public class OrderService {
    private final NotificationSender notificationSender;

    public void completeOrder(Order order) {
        // ... 주문 처리 로직
        notificationSender.sendEmail(order.getUserEmail(), "주문 완료");
    }
}
```

```java
// 1단계: 인터페이스 도입
public interface NotificationPort {
    void sendOrderComplete(String email, Order order);
}

// 기존 구현을 인터페이스 뒤로 숨긴다
public class LegacyNotificationAdapter implements NotificationPort {
    private final NotificationSender notificationSender;

    @Override
    public void sendOrderComplete(String email, Order order) {
        notificationSender.sendEmail(email, "주문 완료");
    }
}

public class OrderService {
    private final NotificationPort notificationPort;

    public void completeOrder(Order order) {
        // ... 주문 처리 로직
        notificationPort.sendOrderComplete(order.getUserEmail(), order);
    }
}
```

이 시점에서 동작은 기존과 동일하다. `LegacyNotificationAdapter`가 그대로 기존 로직을 실행한다.

**2단계: 새 구현 추가**

인터페이스의 새 구현체를 만든다. 이 구현체가 새 마이크로서비스를 호출한다.

```java
public class MsaNotificationAdapter implements NotificationPort {
    private final NotificationServiceClient client;

    @Override
    public void sendOrderComplete(String email, Order order) {
        client.send(new NotificationRequest(email, "ORDER_COMPLETE", order.getId()));
    }
}
```

**3단계: 전환**

설정값이나 피처 플래그로 어떤 구현체를 사용할지 전환한다.

```java
@Configuration
public class NotificationConfig {

    @Value("${notification.use-msa:false}")
    private boolean useMsa;

    @Bean
    public NotificationPort notificationPort(
            NotificationSender legacySender,
            NotificationServiceClient msaClient) {
        if (useMsa) {
            return new MsaNotificationAdapter(msaClient);
        }
        return new LegacyNotificationAdapter(legacySender);
    }
}
```

`notification.use-msa=true`로 바꾸면 새 서비스를 호출하고, `false`로 돌리면 기존 로직으로 돌아간다. 배포 없이 설정 변경만으로 전환과 롤백이 가능하다.

**4단계: 정리**

새 구현이 안정적으로 동작하면, 레거시 구현체와 전환 로직을 제거한다. 인터페이스만 남기고, `MsaNotificationAdapter`가 직접 주입되게 변경한다.

### Strangler Fig과의 차이

| 구분 | Strangler Fig | Branch by Abstraction |
|------|--------------|----------------------|
| 전환 위치 | 프록시(외부) | 코드 내부 |
| 인프라 변경 | 필요 | 불필요 |
| 적용 단위 | API 경로 단위 | 모듈/클래스 단위 |
| 롤백 방법 | 프록시 설정 변경 | 설정값 변경 |

둘을 같이 쓰는 경우가 많다. 외부 API는 Strangler Fig으로, 내부 모듈은 Branch by Abstraction으로 전환한다.

## 점진적 DB 분리

### 왜 DB 분리가 가장 어려운가

코드를 분리하는 건 상대적으로 쉽다. 서비스 경계를 정하고, 코드를 복사하고, API로 연결하면 된다. 문제는 데이터베이스다.

모놀리스에서 하나의 DB를 공유하는 구조일 때, 서비스를 분리하면서 DB도 같이 분리해야 한다. 그런데 DB에는 이미 운영 중인 데이터가 들어 있고, 서비스 간 조인을 하는 쿼리가 수십 개 존재하고, FK(외래 키)로 연결된 테이블이 얽혀 있다.

### 분리 순서

DB를 한 번에 분리하면 실패한다. 다음 순서로 진행해야 한다.

**1단계: 공유 DB 내에서 스키마 분리**

물리적으로 같은 DB 인스턴스를 사용하지만, 논리적으로 스키마를 나눈다.

```sql
-- 기존: 모든 테이블이 public 스키마에 혼재
-- 변경: 서비스별 스키마 분리
CREATE SCHEMA order_schema;
CREATE SCHEMA product_schema;
CREATE SCHEMA user_schema;

-- 테이블 이동
ALTER TABLE products SET SCHEMA product_schema;
ALTER TABLE categories SET SCHEMA product_schema;
ALTER TABLE orders SET SCHEMA order_schema;
ALTER TABLE order_items SET SCHEMA order_schema;
```

이 시점에서 기존 조인 쿼리는 스키마 접두사만 붙이면 그대로 동작한다. 하지만 "어떤 서비스가 어떤 테이블을 소유하는가"가 명확해진다.

**2단계: 크로스 스키마 쿼리 제거**

서비스 A가 서비스 B의 스키마에 직접 접근하는 쿼리를 찾아서 API 호출로 변경한다.

```java
// 변경 전: 주문 서비스에서 상품 테이블을 직접 조인
@Query("SELECT o.*, p.name FROM order_schema.orders o " +
       "JOIN product_schema.products p ON o.product_id = p.id")
List<OrderWithProduct> findOrdersWithProducts();

// 변경 후: 주문 서비스에서 상품 서비스 API를 호출
public List<OrderWithProduct> findOrdersWithProducts() {
    List<Order> orders = orderRepository.findAll();
    List<Long> productIds = orders.stream()
        .map(Order::getProductId)
        .distinct()
        .toList();

    Map<Long, Product> productMap = productServiceClient
        .getProductsByIds(productIds)
        .stream()
        .collect(Collectors.toMap(Product::getId, Function.identity()));

    return orders.stream()
        .map(o -> new OrderWithProduct(o, productMap.get(o.getProductId())))
        .toList();
}
```

이 과정이 가장 오래 걸린다. 모놀리스에 조인 쿼리가 수십 개 있으면 하나씩 변환해야 한다. 한 번에 다 바꾸려고 하면 대형 사고가 난다.

**3단계: FK 제거**

스키마 간 외래 키를 제거한다. 데이터 정합성은 애플리케이션 레벨에서 보장해야 한다.

```sql
-- order_items가 products를 FK로 참조하고 있다면 제거
ALTER TABLE order_schema.order_items
    DROP CONSTRAINT fk_order_items_product_id;
```

FK를 제거하면 잘못된 product_id가 들어올 수 있다. 주문 서비스에서 상품 ID를 받을 때 상품 서비스에 존재 여부를 확인하는 검증 로직을 넣어야 한다.

**4단계: 물리적 DB 분리**

스키마가 분리되고, 크로스 스키마 쿼리가 없고, FK도 제거된 상태에서 비로소 물리적으로 DB를 분리할 수 있다.

```
기존: PostgreSQL 인스턴스 1개 (order_schema + product_schema + user_schema)
변경: PostgreSQL 인스턴스 3개 (order_db, product_db, user_db)
```

이 시점에서 데이터 마이그레이션이 필요하다. `pg_dump`로 스키마별로 데이터를 추출하고, 새 DB에 적재한다. 다운타임을 줄이려면 CDC(Change Data Capture)로 실시간 복제 후 커넥션 스트링만 전환하는 방법을 쓴다.

### 데이터 이관 시 주의사항

데이터 이관 중에도 서비스는 계속 돌아가야 한다. 이관 절차는 다음과 같다.

1. 새 DB에 스키마를 생성한다
2. 기존 DB의 데이터를 새 DB로 복제한다 (초기 마이그레이션)
3. 복제 완료 시점부터 이관 완료 시점까지의 변경분을 CDC로 동기화한다
4. 양쪽 데이터가 일치하는지 검증한다 (레코드 수, 체크섬 비교)
5. 커넥션 스트링을 새 DB로 전환한다
6. 일정 기간 기존 DB를 유지하다가 제거한다

4번 검증을 빼먹으면 안 된다. 데이터가 다른 상태에서 전환하면 되돌리기 힘들다.

## 듀얼 라이트 (Dual Write)

### 개념

전환 기간 동안 기존 DB와 새 DB에 동시에 쓰는 방식이다. 두 곳에 같은 데이터를 기록해서, 전환 중에도 양쪽 데이터를 일관되게 유지한다.

### 왜 필요한가

Strangler Fig으로 라우팅을 전환하면, 새 서비스가 새 DB에 데이터를 쓰기 시작한다. 이 시점에서 롤백하면 트래픽은 모놀리스로 돌아가는데, 새 DB에만 있는 데이터를 모놀리스가 모른다. 듀얼 라이트는 전환 기간 동안 양쪽 DB를 동기화 상태로 유지해서 롤백을 가능하게 한다.

### 구현 방식

두 가지 방식이 있다.

**방식 1: 애플리케이션 레벨 듀얼 라이트**

서비스 코드에서 두 DB에 직접 쓴다.

```java
@Service
public class ProductService {

    private final ProductRepository newRepo;      // 새 DB
    private final LegacyProductDao legacyDao;     // 기존 DB

    @Transactional
    public Product createProduct(ProductCreateRequest request) {
        Product product = Product.from(request);

        // 새 DB에 저장
        Product saved = newRepo.save(product);

        // 기존 DB에도 저장 (롤백 대비)
        try {
            legacyDao.insert(saved);
        } catch (Exception e) {
            log.warn("레거시 DB 쓰기 실패: productId={}", saved.getId(), e);
            // 레거시 쓰기 실패를 비즈니스 실패로 처리할지 결정 필요
        }

        return saved;
    }
}
```

이 방식의 문제는 두 DB 간 트랜잭션이 보장되지 않는다는 점이다. 새 DB에는 성공하고 기존 DB에는 실패하면 데이터 불일치가 발생한다. 반대도 마찬가지다.

**방식 2: CDC 기반 듀얼 라이트**

한쪽 DB에만 쓰고, CDC(Change Data Capture)로 다른 쪽에 비동기 복제한다.

```
새 서비스 → 새 DB → CDC (Debezium 등) → 기존 DB
```

이 방식은 트랜잭션 문제가 없다. 대신 비동기이므로 약간의 지연(보통 수백 ms ~ 수 초)이 있다. 이 지연이 비즈니스 로직에 문제가 되는지 확인해야 한다.

### 듀얼 라이트의 위험성

듀얼 라이트는 임시 수단이다. 장기간 운영하면 다음 문제가 생긴다.

**데이터 충돌**: 양쪽 DB에서 동시에 같은 레코드를 수정하면, 어느 쪽이 최종 상태인지 판단할 수 없다. 전환 기간에는 반드시 한쪽을 "소스 오브 트루스(source of truth)"로 정해야 한다.

**성능 저하**: 모든 쓰기 작업이 두 번 발생한다. 쓰기 부하가 높은 서비스에서는 응답시간이 눈에 띄게 늘어난다.

**복잡성 증가**: 듀얼 라이트 관련 코드가 비즈니스 로직에 섞이면, 나중에 제거하기가 어려워진다. 전환이 완료되면 즉시 제거해야 한다.

듀얼 라이트 기간은 짧을수록 좋다. 보통 1~2주 이내로 전환을 마치고 레거시 쪽 쓰기를 제거하는 것을 목표로 한다.

## 마이그레이션 롤백 계획

### 롤백이 가능한 상태를 유지해야 한다

마이그레이션 중 "이건 되돌릴 수 없습니다"라는 말이 나오면 위험 신호다. 모든 단계에서 롤백 가능 여부를 확인하고 진행해야 한다.

### 단계별 롤백 방법

**라우팅 전환 롤백**

프록시 설정을 원래대로 돌리면 된다. 가장 쉬운 롤백이다.

```yaml
# 롤백: weight를 다시 모놀리스 100%로
- destination:
    host: monolith
  weight: 100
- destination:
    host: product-service
  weight: 0
```

**코드 전환 롤백 (Branch by Abstraction)**

설정값을 `false`로 돌리면 레거시 구현체로 복귀한다. 배포가 필요 없다.

```properties
notification.use-msa=false
```

**DB 전환 롤백**

이게 가장 까다롭다. 듀얼 라이트를 하고 있었다면 기존 DB에 데이터가 있으므로 커넥션 스트링만 되돌리면 된다. 듀얼 라이트 없이 새 DB로 완전 전환한 상태에서 롤백해야 한다면, 새 DB의 데이터를 기존 DB로 역이관해야 한다. 이 작업은 다운타임이 발생할 수 있다.

### 롤백 판단 기준

미리 롤백 기준을 정해둬야 한다. 전환 후 다음 지표가 임계값을 넘으면 롤백한다.

- 에러율이 전환 전 대비 2배 이상 증가
- p99 응답시간이 전환 전 대비 3배 이상 증가
- 데이터 정합성 검증 실패 건수가 발생

"좀 더 지켜보자"고 하다가 문제가 커지는 경우가 많다. 기준을 숫자로 정해놓고 기계적으로 롤백하는 게 안전하다.

## 실무에서 겪는 문제들

### 마이그레이션 순서 결정

어떤 서비스부터 분리할 것인가. 보통 다음 기준으로 정한다.

- **의존성이 적은 서비스부터**: 다른 서비스와 조인이 적고, 독립적으로 동작하는 서비스가 첫 번째 대상이다. 알림 서비스, 파일 업로드 서비스 같은 유틸리티성 서비스가 여기에 해당한다.
- **변경이 잦은 서비스**: 자주 수정되는 부분을 먼저 분리하면 배포 독립성의 이득이 크다.
- **팀이 이미 나뉘어 있는 경우**: 팀 구조와 서비스 구조를 맞추는 게 자연스럽다(역콘웨이 법칙).

처음부터 핵심 도메인(주문, 결제 등)을 분리하면 안 된다. 경험을 쌓은 뒤에 복잡한 서비스를 다루는 게 맞다.

### 전환 기간의 코드 관리

전환 기간에는 모놀리스와 새 서비스 양쪽에 코드가 존재한다. 이 기간에 버그 수정이 들어오면 양쪽을 다 고쳐야 하는 상황이 생긴다. 이 이중 관리 비용을 줄이려면 전환 기간을 짧게 가져가야 한다. 하나의 서비스를 분리하는 데 3개월 이상 걸리고 있다면, 분리 단위가 너무 큰 것이다.

### 팀 간 협업

모놀리스 팀과 새 서비스 팀이 다르면, API 계약(Contract)을 먼저 합의하고 작업해야 한다. API 스펙이 바뀔 때마다 양쪽이 코드를 수정해야 하므로, 초기에 인터페이스를 확정하는 데 시간을 투자하는 게 전체 일정을 줄인다.

### 데이터 정합성 검증

전환 기간 내내 양쪽 시스템의 데이터를 비교하는 검증 잡을 돌려야 한다.

```java
@Scheduled(fixedRate = 60000) // 1분 주기
public void validateDataConsistency() {
    long legacyCount = legacyDao.countProducts();
    long newCount = newRepo.count();

    if (legacyCount != newCount) {
        alertService.send("데이터 불일치 감지: legacy=" + legacyCount
            + ", new=" + newCount);
    }

    // 최근 변경 건에 대해 필드 단위 비교
    List<Product> recentLegacy = legacyDao.findModifiedAfter(
        Instant.now().minus(Duration.ofMinutes(5)));
    for (Product legacy : recentLegacy) {
        Product newProduct = newRepo.findById(legacy.getId()).orElse(null);
        if (newProduct == null || !legacy.equals(newProduct)) {
            alertService.send("레코드 불일치: productId=" + legacy.getId());
        }
    }
}
```

이 검증이 없으면 전환 후에야 데이터가 틀어진 걸 발견하게 되고, 그때는 이미 늦은 경우가 많다.
