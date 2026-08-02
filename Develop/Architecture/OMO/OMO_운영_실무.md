---
title: OMO 운영 실무
tags: [omo, online-merge-offline, 채널통합, 재고동기화, 주문라우팅, 고객식별, e-commerce, backend]
updated: 2026-07-23
---

# OMO 운영 실무
## 1. OMO란

OMO는 온라인과 오프라인 채널을 하나의 구매 흐름으로 합치는 리테일 운영 방식이다. "앱에서 주문하고 매장에서 픽업", "매장에서 재고를 확인하고 앱으로 결제", "온라인 쿠폰을 오프라인 매장에서 사용"이 전형적인 시나리오다.

프론트엔드에서 이 흐름을 만드는 건 어렵지 않다. 문제는 백엔드에서 재고, 주문, 고객 데이터를 단일한 진실로 수렴시키는 부분이다. 온라인 몰 DB와 POS 시스템이 서로 다른 재고를 바라보고 있으면, 화면에서는 통합처럼 보여도 내부는 이미 충돌 상태다.

백엔드 관점에서 OMO 구현의 핵심 문제는 세 가지로 압축된다. 재고 동기화, 주문 라우팅, 고객 식별 통합이다. 셋 모두 "온라인에서 발생한 사건이 오프라인에도 즉시 반영되어야 하고, 그 반대도 마찬가지"라는 요구에서 비롯된다.

## 2. 재고 동기화

### 2.1 채널 분리 구조의 문제

오프라인 매장 재고는 POS가 관리하고, 온라인 주문 재고는 별도 서비스가 잡고 있는 구조가 기존 레거시에서 흔하다. 두 채널이 같은 SKU를 팔 때 차감을 각자 처리하면 oversell이 난다. 매장에서 마지막 한 개를 팔았는데 온라인에서도 주문이 성공하는 상황이다.

기본 해결 방향은 재고 원장을 단일 서비스로 모으고, 두 채널이 모두 이 서비스에 차감을 요청하는 구조다.

```
온라인 주문 ─┐
              ├──▶ 재고 서비스 ──▶ DB (단일 원장)
POS 판매   ──┘
```

POS가 직접 DB를 건드리는 구조라면 마이그레이션이 필요하다. POS 벤더가 외부 API 연동을 지원하지 않는 경우, POS DB 변경을 CDC(Change Data Capture)로 감지해서 재고 서비스로 이벤트를 흘리는 방식을 우회책으로 쓰기도 한다.

### 2.2 선차감과 확정 차감

재고 차감을 단순히 주문 확정 시점에 한 번만 하면 결제 실패 후 롤백이 복잡해진다. 보통 선차감(reservation)과 확정 차감(commit)을 분리한다.

```
주문 생성 요청
    │
    ▼
재고 선차감 (available → reserved)
    │
    ├── 성공 → 주문 확정 → 재고 확정 차감 (reserved → sold)
    │
    └── 실패 (재고 부족) → 주문 거절
            결제 실패 → 선차감 롤백 (reserved → available)
```

재고 상태를 `available`, `reserved`, `sold`로 구분하면 동시 주문에서 충돌을 줄일 수 있다.

```java
@Transactional
public ReservationResult reserve(String sku, int qty, String orderId) {
    Stock stock = stockRepository.findBySkuForUpdate(sku); // SELECT FOR UPDATE
    if (stock.getAvailable() < qty) {
        return ReservationResult.insufficient();
    }
    stock.reserve(qty, orderId);
    stockRepository.save(stock);
    return ReservationResult.success();
}
```

`SELECT FOR UPDATE`로 행 잠금을 잡는 방식은 구현이 단순하다. 단, 매장 수가 많고 인기 SKU에 트래픽이 몰리면 잠금 경합이 심해진다. 이 경우 매장별 재고 버킷을 분리해서 경합 범위를 좁히거나, 낙관적 락과 재시도로 전환한다.

### 2.3 POS 오프라인 동기화

오프라인 매장 POS는 네트워크 상태가 불안정한 환경에서 돌아간다. POS가 실시간으로 재고 서비스를 호출하지 못하는 경우를 위해 로컬 캐시를 두고 나중에 일괄 동기화하는 패턴을 쓴다.

문제는 POS 오프라인 시간 동안 온라인이 같은 재고를 소진했을 때다. POS는 재고가 있다고 보고 판매했는데, 동기화하면 이미 없는 상황이 된다.

대응 방향은 두 가지다. 재고를 음수로 허용하고 후처리로 보상하거나, 매장 전용 재고 버킷을 따로 잡아서 온라인과 충돌하지 않도록 격리한다. 음수 허용 방식은 구현이 단순하지만 재고 불일치 리포트가 지저분해진다. 버킷 분리 방식은 버킷 간 재고 이동 로직이 추가로 필요하다. 매장 수가 많으면 버킷 분리가 더 안정적이다.

## 3. 주문 라우팅

### 3.1 라우팅 결정 구조

온라인 주문이 들어왔을 때 어느 물류 거점에서 처리할지 결정하는 것이 주문 라우팅이다. 물류 거점 후보는 중앙 물류 창고, 인근 매장, 지역 배송 허브로 나뉜다.

라우팅 결정에 필요한 정보는 다음과 같다.

- 거점별 해당 SKU 가용 재고 수량
- 배송지까지 예상 배송 시간
- 주문 유형(배송, 매장 픽업)
- 거점 운영 상태와 현재 처리 작업량

```java
public FulfillmentCenter route(Order order) {
    List<FulfillmentCenter> candidates = centerRepository
        .findCandidates(order.getItems(), order.getDeliveryAddress());

    return candidates.stream()
        .filter(c -> c.hasStock(order.getItems()))
        .filter(c -> c.isOperational())
        .min(Comparator.comparingInt(
            c -> c.estimatedDeliveryHours(order.getDeliveryAddress())))
        .orElseThrow(() -> new NoAvailableCenterException(order.getId()));
}
```

매장 재고를 온라인 주문에 무제한으로 열면 오프라인 고객이 매장에서 재고를 못 보는 상황이 생긴다. 매장 재고는 일정 임계값 이상일 때만 온라인 라우팅 대상에 포함시킨다.

```java
.filter(c -> {
    if (c.getType() == CenterType.STORE) {
        return c.getAvailableStock(sku) > STORE_ONLINE_ROUTING_THRESHOLD;
    }
    return true;
})
```

임계값 설정은 매장 카테고리마다 다르게 가져간다. 회전율이 높은 식품은 넉넉하게 잡고, 장기 전시가 필요한 가구나 가전은 낮게 잡는다.

### 3.2 BOPIS (Buy Online, Pick-up In Store)

고객이 온라인으로 주문하고 매장에서 직접 수령하는 방식이다. 배송 시간이 없어서 당일 처리가 가능하고, 물류비가 줄어드는 대신 픽업 전 고객 알림과 미수령 처리 로직이 필요하다.

주문 상태 흐름:

```
주문 확정 → PENDING_STORE
매장 수령 확인 → PREPARING
준비 완료 → READY_FOR_PICKUP  (→ 고객 알림 발송)
고객 수령 → COMPLETED
n일 미수령 → CANCELLED  (→ 재고 롤백)
```

미수령 자동 취소 처리가 빠지면 재고가 reserved 상태로 무기한 묶인다. 스케줄러로 n일 경과 BOPIS 주문을 주기적으로 조회해서 자동 취소하고 재고를 돌려놓는 로직이 반드시 있어야 한다.

## 4. 고객 식별 통합

### 4.1 채널별 ID 불일치

온라인 시스템에는 회원 ID가 있고, 오프라인 POS CRM에는 전화번호나 멤버십 카드 번호 기반 레코드가 있다. 같은 고객인데 두 시스템에서 다른 ID로 존재한다.

통합하지 않으면 구매 이력, 포인트, 쿠폰이 채널마다 따로 쌓인다. 앱에서 적립한 포인트를 매장에서 사용하려면 두 시스템이 같은 사람을 인식해야 한다.

### 4.2 매핑 테이블 구조

가장 단순한 방법은 식별자 매핑 테이블을 별도로 두는 것이다.

```sql
CREATE TABLE customer_identity_mapping (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    online_id   VARCHAR(64) NOT NULL,
    offline_id  VARCHAR(64) NOT NULL,
    matched_at  TIMESTAMP NOT NULL,
    match_type  VARCHAR(20) NOT NULL,  -- PHONE, EMAIL, MANUAL
    confidence  DECIMAL(3,2) NOT NULL, -- 0.00 ~ 1.00
    INDEX idx_online (online_id),
    INDEX idx_offline (offline_id),
    UNIQUE KEY uq_pair (online_id, offline_id)
);
```

`confidence`는 자동 매핑과 수동 매핑을 구분하고, 매핑의 신뢰도에 따라 사용 범위를 제한하기 위해 둔다. 전화번호 정확히 일치는 1.0, 이름+생년월일 일치는 0.8, 수동 연결은 0.95로 관리하는 식이다. confidence가 낮은 매핑은 주문 이력 조회에는 쓰더라도 포인트 합산에는 사용하지 않는 정책을 두기도 한다.

### 4.3 중복 고객 처리

고객 한 명이 온라인에 여러 계정을 가지거나, POS에 전화번호를 다르게 입력해서 레코드가 여러 개인 경우가 있다. 자동 매핑에 중복 감지 로직이 없으면 매핑이 N:1이나 1:N으로 오염된다.

매핑 삽입 전에 기존 매핑과 충돌하는지 확인하고, 충돌 시 자동 처리하지 않고 검토 큐에 넣는 방식이 안전하다.

```java
public void mapIdentities(String onlineId, String offlineId,
                          MatchType type, double confidence) {
    boolean hasConflict = mappingRepository
        .existsConflict(onlineId, offlineId);

    if (hasConflict) {
        conflictQueue.enqueue(new IdentityConflict(onlineId, offlineId, type));
        return;
    }

    mappingRepository.save(
        new CustomerIdentityMapping(onlineId, offlineId, type, confidence));
}
```

자동으로 다 합치다가 실제로 다른 두 사람의 포인트를 합산하는 사고가 나면 복구가 매우 어렵다. 자동 매핑은 confidence 0.95 이상에만 적용하고, 나머지는 CS팀이 수동 처리하도록 큐에 쌓아두는 방식을 쓰는 편이 낫다.

## 5. 트러블슈팅

### 5.1 재고 불일치

OMO 시스템에서 가장 자주 터지는 장애는 채널마다 재고 숫자가 다른 상황이다. 원인 패턴은 거의 정해져 있다.

**이벤트 중복 처리**: 재고 차감 이벤트가 두 번 소비되어 재고가 두 번 빠진다. Kafka 컨슈머에서 멱등성 처리가 없으면 재시도 시 중복 차감이 발생한다.

```java
@KafkaListener(topics = "stock-deduction")
public void consumeDeduction(StockDeductionEvent event) {
    if (deductionLogRepository.existsByEventId(event.getEventId())) {
        return; // 멱등 처리
    }
    stockService.deduct(event.getSku(), event.getQty());
    deductionLogRepository.save(new DeductionLog(event.getEventId()));
}
```

**트랜잭션 경계 오류**: 재고 차감과 이벤트 발행이 같은 트랜잭션 안에 없으면, 차감은 커밋됐는데 이벤트가 발행 안 된 상태나 반대 상황이 생긴다. Transactional Outbox 패턴으로 이벤트를 DB에 먼저 저장하고 별도 릴레이 프로세스가 발행하게 하면 이 문제를 막는다.

**POS 동기화 실패 후 미재처리**: POS가 오프라인 중 기록한 판매 이력을 동기화할 때 실패하면, 재시도 없이 버려지는 경우가 있다. Dead Letter Queue에 넣고 알람을 보내서 반드시 후처리하는 구조가 필요하다.

재고 불일치가 의심될 때 가장 먼저 하는 건 채널별 차감 로그를 같은 시간대로 붙여보는 것이다. 재고 서비스 차감 합계와 POS 판매 합계를 시간대별로 비교하는 배치를 돌리면 불일치가 언제부터 시작됐는지 좁힐 수 있다.

### 5.2 이벤트 유실

재고 차감, 주문 상태 변경, 픽업 준비 완료 알림이 유실되면 데이터가 틀어지고 사용자 경험이 망가진다.

Kafka 프로듀서가 `acks=0` 또는 `acks=1`로 설정되어 있으면, 브로커 장애 시 메시지가 유실된다. 재고와 주문에 직결된 이벤트는 `acks=all`에 `min.insync.replicas=2` 이상으로 설정한다.

컨슈머가 처리 전에 오프셋을 먼저 커밋하면(`enable.auto.commit=true`), 처리 중 장애가 나도 오프셋이 이미 앞으로 이동해서 해당 메시지를 다시 읽지 않는다. 수동 커밋으로 처리 완료 후에만 커밋해야 한다.

```java
@KafkaListener(topics = "order-events")
public void consume(ConsumerRecord<String, OrderEvent> record,
                    Acknowledgment acknowledgment) {
    try {
        orderService.process(record.value());
        acknowledgment.acknowledge(); // 처리 완료 후 커밋
    } catch (Exception e) {
        // 미커밋 → 재시도
        throw e;
    }
}
```

이벤트 유실 감지는 이벤트 ID 기반 시퀀스 추적으로 한다. 주문 이벤트에 단조 증가하는 시퀀스 번호를 붙이고, 컨슈머 쪽에서 마지막 처리 시퀀스와 수신 시퀀스 간 gap을 모니터링한다. Gap이 임계값을 넘으면 알람을 보낸다.

POS 동기화 이벤트는 별도 배치로 보정한다. POS DB와 재고 서비스 DB를 주기적으로 비교해서 불일치 항목을 찾아 수동 검토 큐에 넣는다. 자동 보정은 양방향 충돌 시 어느 쪽이 진실인지 판단하기 어려워서, 정상 데이터를 덮어쓰는 사고가 날 수 있다. 자동 보정 범위는 단방향으로 명확히 틀린 경우에만 제한하고, 나머지는 사람이 검토한다.

## 관련 문서

- [이벤트 기반 아키텍처](../../Architecture/Event_Driven_Architecture.md)
- [분산 트랜잭션](../../DataBase/RDBMS/Distributed_Transaction.md)
- [Saga 패턴 및 분산 트랜잭션](../../Architecture/MSA/Saga_패턴_및_분산_트랜잭션.md)
