---
title: Online-Merge-Offline (OMO) 아키텍처
tags: [messaging, redis, event-driven, backend]
updated: 2026-07-23
---

# Online-Merge-Offline (OMO) 아키텍처

## 1. 배경

OMO는 온라인과 오프라인 채널을 하나의 구매 흐름으로 통합한 운영 방식이다. "앱에서 주문하고 매장에서 픽업", "매장에서 QR 스캔 후 온라인 결제", "온라인 적립 포인트를 오프라인에서 사용"이 대표적인 시나리오다.

기술적으로 어려운 건 프론트가 아니다. 두 채널이 같은 재고, 같은 주문 상태, 같은 고객 ID를 바라보게 하는 백엔드 구조가 핵심이다. 온라인 몰 DB와 오프라인 POS가 각자 재고를 관리하는 레거시 구조에서는, 같은 SKU에 대해 채널마다 다른 재고 숫자를 갖게 되는 게 일상이다. 화면상 통합처럼 보여도 내부는 이미 충돌 상태인 경우가 많다.

이 문서는 OMO 구현의 세 가지 핵심 문제인 OMS 기반 주문 처리, 재고 실시간 동기화, 고객 식별 통합을 다룬다. 각 영역에서 이벤트 기반 설계를 어떻게 적용하는지, 실무에서 자주 만나는 장애 패턴은 무엇인지 위주로 설명한다.

## 2. 핵심 기술 구성

### 2.1 OMS (Order Management System)

OMS는 온라인과 오프라인에서 발생한 주문을 단일 흐름으로 처리하는 허브다. 채널별로 따로 존재하던 주문 처리 로직을 하나로 통합하고, 어느 채널에서 주문이 들어오든 동일한 상태 전이와 이행 로직을 적용한다.

OMS가 담당하는 주요 역할은 다음 세 가지다.

첫째, 주문 라우팅이다. 온라인 주문이 들어왔을 때 중앙 물류 창고에서 배송할지, 인근 매장 재고로 처리할지, 매장 픽업으로 갈지를 결정한다. 라우팅 기준은 SKU별 가용 재고, 배송지까지 예상 소요 시간, 매장 운영 상태를 조합한다.

둘째, 주문 상태 관리다. 온라인 주문과 오프라인 판매를 동일한 상태 모델로 관리한다. `PENDING → CONFIRMED → PROCESSING → READY → COMPLETED` 흐름을 채널에 무관하게 적용하고, 각 상태 전이 시 이벤트를 발행해서 재고 서비스, 알림 서비스, POS와 동기화한다.

셋째, 이행 조율이다. BOPIS(Buy Online Pick-up In Store) 같은 크로스 채널 이행에서 온라인 결제와 오프라인 수령을 연결한다.

```
온라인 주문  ──┐
               │
POS 판매    ──┼──▶  OMS  ──▶  재고 서비스  ──▶  단일 재고 원장
               │        │
앱 픽업     ──┘        └──▶  이벤트 브로커  ──▶  POS / 알림 / 정산
```

### 2.2 재고 실시간 동기화

재고 동기화에서 가장 먼저 해결해야 할 건 진실의 원천(source of truth)을 하나로 확정하는 것이다. POS 재고 DB와 온라인 몰 재고 DB가 각자 살아있는 구조에서는 동기화 자체가 불가능하다. 어느 쪽이 원장인지를 먼저 정해야 한다.

원장을 확정했으면, 다른 쪽은 쓰기를 원장에 위임하는 구조로 바꾼다. POS가 직접 자체 DB에 판매 차감을 쓰던 구조라면, POS가 원장 API를 호출하거나 POS DB 변경을 CDC로 감지해서 원장에 전파하는 방식 중 하나를 선택해야 한다.

재고 차감은 선차감(reservation)과 확정 차감(commit)으로 나누는 게 일반적이다.

```
주문 생성 요청
    │
    ▼
재고 선차감 (available → reserved)
    │
    ├── 성공 → 결제 진행
    │              ├── 성공 → 확정 차감 (reserved → sold)
    │              └── 실패 → 선차감 롤백 (reserved → available)
    │
    └── 실패 (재고 부족) → 주문 거절
```

선차감 없이 주문 확정 시점에 한 번에 차감하면, 결제 실패 후 롤백 타이밍이 맞지 않아서 재고가 묶이는 경우가 생긴다. 선차감 상태에서 결제가 타임아웃되거나 PG 응답이 늦어지면 재고가 reserved 상태로 오래 남아있게 되므로, 선차감에 TTL을 걸어서 일정 시간 후 자동으로 available로 돌아오게 해야 한다.

### 2.3 고객 식별 통합

온라인 시스템의 회원 ID와 오프라인 POS의 멤버십 번호 또는 전화번호 기반 레코드는 같은 사람이지만 서로를 모른다. 채널 통합 전에는 문제가 없었지만, 포인트나 쿠폰을 크로스 채널로 사용하려는 순간 두 시스템을 연결해야 한다.

식별자 매핑 테이블을 별도로 두는 방식이 가장 단순하다.

```sql
CREATE TABLE customer_identity_mapping (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    online_id    VARCHAR(64) NOT NULL,
    offline_id   VARCHAR(64) NOT NULL,
    match_type   VARCHAR(20) NOT NULL,  -- PHONE, EMAIL, MANUAL
    confidence   DECIMAL(3,2) NOT NULL,
    created_at   TIMESTAMP NOT NULL,
    UNIQUE KEY uq_pair (online_id, offline_id),
    INDEX idx_online (online_id),
    INDEX idx_offline (offline_id)
);
```

`confidence` 컬럼은 자동 매핑과 수동 매핑의 신뢰도를 구분하기 위해 둔다. 전화번호 일치는 1.0, 이름+생년월일 조합은 0.8, 수동 연결은 0.95 식으로 관리한다. confidence가 낮은 매핑은 조회 목적으로만 쓰고, 포인트 합산처럼 금전적 영향이 있는 작업에는 쓰지 않는 정책을 운영한다.

## 3. 이벤트 기반 설계 패턴

### 3.1 채널 간 데이터 동기화 구조

온라인 주문이 발생하면 재고 차감, 배송 준비, 알림 발송, 포인트 적립이 연쇄로 발생한다. 이 작업들을 하나의 트랜잭션으로 묶으면 한 곳에서 실패했을 때 전체가 롤백되거나 커플링이 심해진다. 이벤트 브로커를 통해 각 작업을 독립적인 컨슈머로 분리하는 구조가 일반적이다.

Kafka를 기준으로 채널 간 동기화 흐름은 아래와 같다.

```
OMS                  Kafka                   Consumers
 │                     │                        │
 ├── order.created ──▶ │ ──▶ 재고 서비스 (차감)   │
 │                     │ ──▶ 알림 서비스 (푸시)   │
 │                     │ ──▶ POS 동기화           │
 │                     │ ──▶ 포인트 서비스         │
 │                     │                        │
 ├── order.pickup_ready ▶ │ ──▶ 알림 서비스 (픽업 준비)
 │                     │ ──▶ POS 화면 갱신        │
```

토픽은 도메인 이벤트 단위로 설계한다. `order-events`, `stock-events`, `customer-events`처럼 도메인별로 분리하고, 컨슈머 그룹은 각 서비스가 독립적으로 가져간다. 하나의 토픽에 모든 이벤트를 때려넣으면 컨슈머마다 필터링 로직이 중복되고, 특정 이벤트만 소비 속도가 느릴 때 lag이 전체에 영향을 준다.

### 3.2 Kafka 재고 이벤트 처리

재고 차감 이벤트는 정확히 한 번 처리되어야 한다. Kafka의 기본 at-least-once 보장으로 인해 이벤트가 중복 전달될 수 있으므로, 컨슈머에서 멱등성 처리가 필수다.

```java
@KafkaListener(topics = "stock-events", groupId = "stock-deduction-group")
public void handleStockDeduction(StockDeductionEvent event,
                                  Acknowledgment acknowledgment) {
    if (deductionLogRepository.existsByEventId(event.getEventId())) {
        acknowledgment.acknowledge();
        return;
    }

    stockService.deduct(event.getSku(), event.getQty(), event.getOrderId());
    deductionLogRepository.save(new DeductionLog(event.getEventId()));
    acknowledgment.acknowledge();
}
```

`enable.auto.commit=false`로 설정하고 처리 완료 후 수동으로 커밋한다. 자동 커밋(`enable.auto.commit=true`)은 처리 중 장애가 나도 오프셋이 앞으로 이동하기 때문에, 해당 이벤트를 다시 읽지 못한다. 재고와 주문에 직결된 이벤트는 프로듀서도 `acks=all`, `min.insync.replicas=2` 이상으로 설정해야 한다.

이벤트 발행과 DB 쓰기의 원자성 문제는 Transactional Outbox 패턴으로 해결한다. 재고 차감과 이벤트 발행을 같은 트랜잭션 안에 묶으려다 보면, 차감은 커밋됐는데 이벤트 발행이 실패하거나 그 반대 상황이 생긴다. 이벤트를 Kafka에 직접 쏘는 대신 동일 DB의 outbox 테이블에 먼저 저장하고, 별도 릴레이 프로세스가 outbox를 읽어서 Kafka에 발행하는 구조를 쓴다.

```sql
CREATE TABLE outbox_events (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_id    VARCHAR(64) NOT NULL UNIQUE,
    topic       VARCHAR(128) NOT NULL,
    payload     JSON NOT NULL,
    status      VARCHAR(20) DEFAULT 'PENDING',
    created_at  TIMESTAMP NOT NULL,
    published_at TIMESTAMP
);
```

### 3.3 Redis Pub-Sub 활용

Kafka는 영속성이 필요한 이벤트(재고 차감, 주문 상태 변경)에 적합하다. 반면 POS 화면 실시간 갱신이나 픽업 카운터 알림처럼 유실돼도 다음 폴링에서 만회할 수 있는 이벤트는 Redis Pub-Sub로 처리한다.

Redis Pub-Sub는 메시지를 저장하지 않는다. 구독자가 연결 끊긴 동안 발행된 메시지는 유실된다. 이 특성 때문에 재고 차감이나 주문 확정처럼 유실이 문제가 되는 이벤트에는 절대 쓰면 안 된다.

```java
// 픽업 준비 완료 시 POS 화면 갱신 (유실 허용 가능한 알림성 이벤트)
public void notifyPickupReady(String storeId, String orderId) {
    String channel = "store:" + storeId + ":pickup-ready";
    String payload = objectMapper.writeValueAsString(
        Map.of("orderId", orderId, "timestamp", Instant.now())
    );
    redisTemplate.convertAndSend(channel, payload);
}
```

POS가 Redis 채널을 구독하고 있으면 즉시 알림을 받아 화면을 갱신한다. POS가 재시작된 상태라면 메시지를 못 받지만, POS는 어차피 OMS를 주기적으로 폴링해서 최신 상태를 가져오므로 영향이 없다.

## 4. 실무 주의사항

### 4.1 재고 이중 차감 방지

재고 이중 차감은 OMO 시스템에서 가장 자주 나오는 장애다. 원인은 거의 정해져 있다.

**이벤트 중복 소비**: 컨슈머 재시작 또는 Kafka 리밸런싱 과정에서 같은 이벤트를 두 번 처리하는 경우다. 앞서 설명한 `event_id` 기반 멱등성 처리로 막는다.

**트랜잭션 없이 두 번 호출**: 주문 서비스가 장애로 재시작되면서 이미 차감 요청을 보낸 이벤트를 다시 발행하는 경우다. 이벤트에 주문 ID를 포함시키고 차감 로그에 주문 ID 기준 유니크 인덱스를 걸면 DB 레벨에서 중복 삽입이 막힌다.

**POS 동기화와 온라인 이벤트 동시 처리**: POS가 오프라인 상태에서 쌓아둔 판매 이력을 일괄 동기화할 때, 해당 재고가 온라인에서도 차감된 경우다. 동기화 요청에도 POS 판매 트랜잭션 ID를 포함시키고 멱등 처리를 동일하게 적용한다.

재고 불일치 감지는 배치로 한다. 재고 서비스의 차감 합계와 POS 판매 합계를 시간대별로 비교하는 배치를 1시간 주기로 돌리면 불일치가 언제부터 시작됐는지 좁힐 수 있다.

### 4.2 고객 ID 매핑 충돌

자동 매핑 로직을 열심히 짜다 보면 실제로 다른 두 사람의 데이터를 합치는 사고가 난다. 특히 전화번호 기반 매핑에서 번호를 변경한 경우가 문제다. 이전 소유자의 온라인 계정과 새 소유자의 오프라인 레코드가 같은 전화번호로 연결될 수 있다.

매핑 삽입 전에 기존 매핑과 충돌하는지 반드시 확인한다.

```java
public MappingResult mapIdentities(String onlineId, String offlineId,
                                    MatchType type, double confidence) {
    Optional<CustomerIdentityMapping> existing =
        mappingRepository.findByOnlineIdOrOfflineId(onlineId, offlineId);

    if (existing.isPresent()) {
        CustomerIdentityMapping current = existing.get();
        if (!current.getOnlineId().equals(onlineId)
                || !current.getOfflineId().equals(offlineId)) {
            conflictQueue.enqueue(
                new IdentityConflict(onlineId, offlineId, current, type));
            return MappingResult.conflicted();
        }
        return MappingResult.alreadyMapped();
    }

    mappingRepository.save(
        new CustomerIdentityMapping(onlineId, offlineId, type, confidence));
    return MappingResult.success();
}
```

confidence 0.95 미만은 자동 매핑 대상에서 제외하고 CS팀 검토 큐에 넣는 정책을 쓴다. 잘못된 매핑 복구는 양쪽 시스템의 포인트, 이력, 쿠폰을 수동으로 되돌려야 하므로 비용이 크다.

### 4.3 Eventually Consistent 재고 처리

이벤트 기반 구조에서 재고는 엄밀히 말하면 Eventually Consistent다. 주문이 확정된 직후 재고 서비스가 이벤트를 처리하기 전에 다른 주문이 같은 SKU를 조회하면, 아직 반영 안 된 재고 숫자를 볼 수 있다.

이 짧은 시간 동안 oversell이 발생할 수 있는지, 발생해도 괜찮은 상품인지를 카테고리마다 달리 판단해야 한다. 수량이 넉넉한 일반 상품은 약간의 oversell을 허용하고 후처리로 대응하는 게 현실적이다. 한정판이나 단수 재고 상품은 재고 서비스에서 직접 동기 방식으로 차감하고 응답을 받아야 한다.

```java
// 한정 수량 상품: 동기 차감
public OrderResult orderLimitedItem(String sku, int qty, String orderId) {
    DeductionResult result = stockService.deductSync(sku, qty, orderId);
    if (!result.isSuccess()) {
        throw new InsufficientStockException(sku);
    }
    return confirmOrder(orderId);
}

// 일반 상품: 선차감 후 이벤트 발행
public OrderResult orderRegularItem(String sku, int qty, String orderId) {
    stockService.reserve(sku, qty, orderId);
    eventPublisher.publish(new OrderConfirmedEvent(orderId, sku, qty));
    return OrderResult.pending(orderId);
}
```

POS 오프라인 구간의 재고 처리도 Eventually Consistent 문제다. POS가 네트워크 없이 로컬 캐시로 판매를 처리하는 동안 온라인이 같은 재고를 소진하면, 동기화 시점에 음수 재고가 된다. 매장 전용 버킷을 분리해서 온라인 재고와 격리하는 방식이 장기적으로 안정적이다. 음수를 허용하고 보상 처리하는 방식은 구현이 단순하지만 재고 리포트가 지저분해지고 보상 로직이 쌓이면서 복잡도가 올라간다.

## 관련 문서

- [이벤트 기반 아키텍처](../Event_Driven_Architecture.md)
- [분산 트랜잭션](../../DataBase/RDBMS/Distributed_Transaction.md)
- [Saga 패턴 및 분산 트랜잭션](../MSA/Saga_패턴_및_분산_트랜잭션.md)
