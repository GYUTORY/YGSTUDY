---
title: "Oracle에서의 MSA"
tags: [msa, Oracle, 분산 트랜잭션, XA, Transactional Outbox, RAC, 커넥션 풀]
updated: 2026-07-03
---

# Oracle에서의 MSA

MSA 이론은 대부분 PostgreSQL이나 MySQL을 전제로 쓰여 있다. "서비스마다 DB를 분리하라"는 말은 쉽지만, 회사에 이미 Oracle Enterprise Edition RAC가 깔려 있고 DBA 조직이 있고 라이선스 비용이 코어당 붙는 환경에서는 이야기가 다르다. Oracle을 쓰는 조직에서 MSA를 하면 겪는 문제들을 정리한다. Oracle 특유의 오류 코드와 트러블슈팅 위주로 다룬다.

## 서비스별 DB 격리를 Oracle에서 구현하기

MSA의 대원칙은 서비스가 자기 데이터를 독점하고 다른 서비스는 API로만 접근하는 것이다. Oracle에서 이걸 구현하는 방법은 세 가지이고, 각각 라이선스와 운영 부담이 크게 다르다.

### 인스턴스 분리

서비스마다 별도 Oracle 인스턴스(별도 서버 또는 별도 DB)를 띄운다. 격리는 가장 확실하다. 서비스 A의 테이블 스캔이 서비스 B의 버퍼 캐시를 오염시키는 일이 없고, 한 서비스의 폭주가 다른 서비스의 SGA를 잡아먹지 않는다.

문제는 비용이다. Oracle EE는 코어 단위로 라이선스를 산다. 인스턴스를 20개로 쪼개면 각 인스턴스가 최소한의 코어를 먹고, 그게 다 라이선스 대상이다. 게다가 인스턴스마다 SGA/PGA 메모리를 따로 잡으니 물리 서버 메모리도 빨리 고갈된다. 소규모 서비스 15개를 각각 인스턴스로 띄우면 실사용률은 5%인데 라이선스는 100% 내는 상황이 나온다.

### 스키마(user)-per-service

Oracle에서 스키마와 유저는 같은 개념이다. `CREATE USER order_svc`를 하면 `order_svc`라는 스키마가 생기고, 그 안에 테이블이 들어간다. 서비스마다 유저를 하나씩 만들고, 서비스 애플리케이션은 자기 유저로만 접속한다.

```sql
CREATE USER order_svc IDENTIFIED BY ...
  DEFAULT TABLESPACE ts_order
  QUOTA UNLIMITED ON ts_order;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE TO order_svc;

CREATE USER payment_svc IDENTIFIED BY ...
  DEFAULT TABLESPACE ts_payment
  QUOTA UNLIMITED ON ts_payment;
```

같은 인스턴스 안에 유저만 나눠서 쓰니 라이선스는 인스턴스 하나 값만 낸다. 중소 규모에서 현실적으로 가장 많이 선택하는 방식이다.

격리가 약하다는 게 함정이다. 물리적으로 같은 인스턴스라 버퍼 캐시, 리두 로그, undo 세그먼트, 그리고 무엇보다 `processes`/`sessions` 파라미터를 전 서비스가 공유한다. 한 서비스가 커넥션을 다 잡아먹으면 다른 서비스가 `ORA-00020: maximum number of processes exceeded`로 접속조차 못 한다. 그리고 유저 권한을 조금만 느슨하게 주면 `SELECT * FROM payment_svc.transactions` 같은 크로스 스키마 접근이 너무 쉽게 열린다. 이건 뒤에서 다시 다룬다.

### Multitenant PDB 분리

12c부터 나온 Multitenant 아키텍처는 하나의 컨테이너 DB(CDB) 안에 여러 개의 플러그형 DB(PDB)를 넣는다. 서비스마다 PDB를 하나씩 주면, 논리적으로는 완전히 분리된 DB처럼 보이면서 물리 인스턴스는 하나를 공유한다. PDB 단위로 백업/복구/이관이 되고, PDB끼리는 기본적으로 서로 안 보인다. 스키마-per-service의 격리 약점과 인스턴스 분리의 비용 부담 사이의 절충안이다.

라이선스를 반드시 확인해야 한다. 19c 기준으로 CDB에 PDB 3개까지는 Multitenant 옵션 없이 쓸 수 있지만, 4개째부터는 Multitenant 옵션 라이선스를 따로 사야 한다(버전별로 규칙이 바뀌므로 계약을 확인해야 한다). MSA는 서비스가 수십 개인데 PDB 3개 제한은 의미가 없다. 결국 Multitenant를 제대로 쓰려면 옵션 비용이 붙는다.

### 실무 선택 기준

정답은 규모와 라이선스 계약에 달렸다.

- 서비스 5개 미만, 트래픽 작음 → 스키마-per-service. 인스턴스 하나에 다 넣고 유저만 나눈다.
- 서비스 많고 이미 Multitenant 옵션 계약이 있음 → PDB-per-service.
- 특정 서비스만 트래픽이 압도적으로 크거나 규제상 물리 분리가 필요함 → 그 서비스만 인스턴스 분리, 나머지는 스키마로.

핵심은 "논리적 분리를 코드/권한 레벨에서 강제하는가"다. 물리 분리를 못 하더라도 서비스가 자기 스키마 밖을 못 건드리게 권한을 잠그면, 나중에 트래픽이 커졌을 때 그 스키마만 뽑아서 별도 인스턴스로 옮길 수 있다. 처음부터 크로스 스키마 조인을 허용하면 그 이관이 불가능해진다.

## DB Link와 공유 스키마의 유혹

Oracle을 쓰는 조직에서 MSA를 망치는 첫 번째 원인은 대부분 DB Link다.

서비스 A가 서비스 B의 데이터를 필요로 할 때, 정석은 B의 REST API를 호출하는 것이다. 하지만 DBA에게 "B 스키마로 가는 DB Link 하나만 만들어 주세요" 하면 5분 만에 끝난다. API를 만들 필요도, 네트워크 타임아웃을 다룰 필요도 없다.

```sql
-- order_svc 스키마에서
CREATE DATABASE LINK payment_link
  CONNECT TO payment_svc IDENTIFIED BY ...
  USING 'PAYMENT_DB';

-- 그냥 조인해버린다
SELECT o.order_id, p.paid_amount
FROM orders o
JOIN payment@payment_link p ON o.order_id = p.order_id;
```

이 한 줄이 MSA를 조용히 모놀리스로 되돌린다.

문제가 바로 안 보인다는 게 진짜 위험한 점이다. 개발할 때는 조인 한 방이 API 여러 번보다 빠르고 편하다. 6개월 지나면 서비스 15개가 서로 DB Link로 얽혀서, payment 스키마의 컬럼 하나를 못 바꾼다. 어디서 누가 `payment@payment_link`로 그 컬럼을 참조하는지 전수조사가 불가능하기 때문이다. 스키마 소유권이라는 MSA의 근간이 무너진다.

순환 참조도 생긴다. A가 B의 테이블을 조인하고, B가 A의 테이블을 조인하면, 두 서비스는 배포 순서를 맞춰야 하고 한쪽 스키마 변경이 다른 쪽 쿼리를 깨뜨린다. 이건 서비스가 아니라 그냥 분산된 모놀리스다.

DB Link를 쓰면 트랜잭션까지 자동으로 분산 트랜잭션이 된다. `payment@payment_link`를 건드리는 순간 그 세션은 분산 트랜잭션으로 승격되고, 다음 절에서 다룰 온갖 문제가 딸려온다.

현실적인 대응은 DB Link 생성을 DBA 승인 프로세스로 막고, 이미 있는 것들은 목록을 뽑아서 하나씩 API로 걷어내는 것이다.

```sql
-- 인스턴스에 존재하는 DB Link 전수조사
SELECT owner, db_link, host, created FROM dba_db_links ORDER BY owner;
```

이 쿼리 결과가 서비스 개수보다 많으면 이미 강결합이 상당히 진행된 상태다.

## 분산 트랜잭션: Oracle XA와 2PC가 안티패턴인 이유

여러 서비스의 DB를 하나의 트랜잭션으로 묶고 싶은 유혹은 항상 있다. 주문을 넣으면서 재고를 까고 결제를 잡는 걸 all-or-nothing으로 하고 싶다. Oracle은 이걸 두 가지로 지원한다. XA(Java의 `XADataSource`로 애플리케이션이 여러 리소스를 2PC로 묶는 것)와 DB Link 분산 트랜잭션(서로 다른 인스턴스의 테이블을 하나의 트랜잭션에서 갱신하는 것)이다. 둘 다 내부적으로 2PC(Two-Phase Commit)를 쓴다.

2PC의 흐름은 이렇다.

```
Coordinator                Resource A              Resource B
    |------- prepare ------->|                        |
    |------- prepare -------------------------------->|
    |<------ ready ----------|                        |
    |<------ ready -----------------------------------|
    |------- commit -------->|                        |
    |------- commit --------------------------------->|
```

prepare 단계에서 모든 리소스가 "커밋할 준비 됐다"고 답하면, coordinator가 commit을 뿌린다. 여기서 MSA에 치명적인 문제가 두 가지다.

첫째, prepare와 commit 사이에 리소스가 잠긴다. A가 prepare로 "ready" 하고 나서 B의 응답을 기다리는 동안, A가 건드린 행(row)들은 잠긴 채로 커밋도 롤백도 못 한다. 이 상태에서 coordinator가 죽으면 그 트랜잭션은 in-doubt(미결) 상태가 되어 무한정 락을 잡는다. 서비스 하나가 느려지면 그 락을 기다리는 다른 서비스가 줄줄이 멈춘다. 마이크로서비스의 독립성이 근본적으로 깨진다.

둘째, 실제로 자주 터지는 게 타임아웃이다. DB Link 분산 트랜잭션에서 원격 노드 응답이 `distributed_lock_timeout`(기본 60초)을 넘기면 이 오류가 난다.

```
ORA-02049: timeout: distributed transaction waiting for lock
```

원격 노드가 잠깐 느려지거나 네트워크가 출렁이면 바로 발생한다. 네트워크가 항상 흔들리는 게 전제인 MSA 환경에서 60초 락 대기는 재앙이다.

in-doubt 트랜잭션이 남으면 이렇게 확인하고 강제 정리한다.

```sql
-- 미결 분산 트랜잭션 조회
SELECT local_tran_id, state, mixed, host, commit_comment
FROM dba_2pc_pending;

-- DBA가 수동으로 강제 커밋/롤백. state를 보고 판단해야 한다
COMMIT FORCE '<local_tran_id>';
-- 또는
ROLLBACK FORCE '<local_tran_id>';
```

`FORCE`로 한쪽만 커밋하고 다른 쪽을 롤백하면 데이터 정합성이 깨진 mixed 상태가 되고, `dba_2pc_pending`의 `mixed` 컬럼이 `yes`로 남는다. 이건 사람이 데이터를 직접 대조해서 맞춰야 한다. 새벽에 이걸 하고 있으면 XA를 쓴 걸 후회하게 된다.

`ORA-24756: transaction does not exist`도 XA 환경에서 자주 본다. 애플리케이션(트랜잭션 매니저)이 인지한 트랜잭션과 DB가 인지한 트랜잭션 상태가 어긋날 때 나온다. 보통 타임아웃으로 한쪽이 트랜잭션을 이미 정리했는데 다른 쪽이 뒤늦게 커밋을 시도하면 발생한다.

결론은 MSA에서 서비스 간 원자성이 필요하면 2PC가 아니라 Saga나 아웃박스로 최종적 일관성(eventual consistency)을 받아들이는 것이다. 즉시 정합성을 포기하는 대신 서비스의 독립성과 가용성을 얻는다. Saga는 [Saga_패턴_및_분산_트랜잭션](Saga_패턴_및_분산_트랜잭션.md), 아웃박스는 [트랜잭셔널_아웃박스_패턴](트랜잭셔널_아웃박스_패턴.md)에서 다룬다. 여기서는 그 구현을 Oracle로 할 때의 디테일을 본다.

XA를 정말로 못 피하는 경우가 있긴 하다. 레거시 EJB 컨테이너나 상용 패키지가 XA를 강제할 때다. 그럴 때는 XA 참여 리소스를 최소한으로 줄이고, `distributed_lock_timeout`을 짧게(예: 10초) 잡아서 락 대기가 오래 끌리지 않게 하는 방어가 최선이다.

## 트랜잭셔널 아웃박스를 Oracle로 구현하기

아웃박스 패턴 자체는 [트랜잭셔널_아웃박스_패턴](트랜잭셔널_아웃박스_패턴.md)에 있으니, 여기서는 Oracle에서 폴링 워커를 만들 때 부딪히는 것들만 본다.

### SKIP LOCKED 폴링 (11g+)

폴링 워커를 여러 개 띄우면 같은 아웃박스 행을 두 워커가 동시에 집어서 메시지가 중복 발행될 수 있다. `FOR UPDATE`로 락을 잡으면 중복은 막지만, 워커 B가 워커 A가 잡은 행이 풀릴 때까지 기다리느라 처리량이 안 나온다.

`SKIP LOCKED`는 이미 다른 세션이 잠근 행을 기다리지 않고 건너뛴다. Oracle은 11g부터 지원한다(그전에도 내부적으로 쓰였지만 문서화된 문법은 11g부터다).

```sql
SELECT id, aggregate_id, event_type, payload
FROM outbox
WHERE status = 'PENDING'
ORDER BY id
FETCH FIRST 100 ROWS ONLY   -- 12c+ 문법
FOR UPDATE SKIP LOCKED;
```

11g에서는 `FETCH FIRST`가 없으니 `ROWNUM`으로 처리한다. `FOR UPDATE`와 `ROWNUM`을 한 쿼리에 섞으면 순서 문제가 생기므로 인라인 뷰로 감싼다.

```sql
SELECT id, aggregate_id, event_type, payload
FROM (
  SELECT id, aggregate_id, event_type, payload
  FROM outbox
  WHERE status = 'PENDING'
  ORDER BY id
)
WHERE ROWNUM <= 100
FOR UPDATE SKIP LOCKED;
```

이렇게 하면 워커를 N개 띄워도 각자 다른 행을 집어간다. 워커마다 100건씩 잡아서 발행하고 `status = 'SENT'`로 업데이트한 뒤 커밋한다.

### ORA-00060 데드락

아웃박스 워커를 여럿 돌리다 보면 이걸 만난다.

```
ORA-00060: deadlock detected while waiting for resource
```

원인은 대개 `ORDER BY` 없이 `SKIP LOCKED`를 쓰거나, 워커들이 아웃박스 행뿐 아니라 다른 테이블(예: 처리 로그, 집계 테이블)까지 서로 다른 순서로 잠글 때다. 워커 A는 outbox → log 순으로, 워커 B는 log → outbox 순으로 잠그면 교착이 생긴다.

대응은 두 가지다. 락 획득 순서를 모든 워커에서 동일하게 통일한다(항상 `id` 오름차순, 항상 같은 테이블 순서). 그리고 아웃박스 워커는 아웃박스 테이블만 건드리게 하고, 부가 작업은 발행 후 별도 트랜잭션으로 분리한다. Oracle은 데드락이 나면 한쪽 트랜잭션의 마지막 문장만 롤백하고 `ORA-00060`을 던지므로, 애플리케이션에서 이 예외를 잡아 트랜잭션 전체를 롤백하고 재시도하게 만들어야 한다. 재시도하지 않으면 그 배치가 통째로 유실된다.

### SEQUENCE 캐싱과 순서 보장

아웃박스에 이벤트 순서가 중요할 때(예: 같은 주문의 CREATED → PAID → SHIPPED 순서), `id`를 `SEQUENCE`로 뽑는데 여기서 함정이 있다.

성능을 위해 시퀀스는 기본적으로 값을 캐시한다(`CACHE 20`이 기본). RAC 환경에서는 노드마다 시퀀스 캐시를 따로 갖는다. 노드 1이 1~20을, 노드 2가 21~40을 캐시하면, 노드 2에서 커밋된 이벤트가 노드 1에서 커밋된 이벤트보다 시간상 먼저인데 `id`는 더 클 수 있다. 즉 `ORDER BY id`가 실제 커밋 시간 순서를 보장하지 않는다.

순서가 정말 중요하면 방법이 있다.

- `ORDER` 옵션을 준 시퀀스(`CREATE SEQUENCE ... ORDER NOCACHE`). RAC에서 전 노드가 순서를 맞추지만 노드 간 조율 비용이 커서 성능이 크게 떨어진다. 고빈도 발행에는 못 쓴다.
- `id`로 순서를 잡으려 하지 말고, 발행 시점 정렬은 `aggregate_id`(예: 주문 ID) 단위로만 보장하고 그 안에서 애플리케이션이 부여한 버전 컬럼을 쓴다. 전역 순서를 포기하고 집합체 단위 순서만 지키는 게 현실적이다.

단일 인스턴스라면 시퀀스 캐시가 순서를 뒤집지는 않는다. 다만 인스턴스가 재시작되면 캐시에 있던 미사용 값이 날아가서 시퀀스에 구멍(gap)이 생긴다. 아웃박스 `id`는 순서 판단용이지 연속성을 가정하면 안 된다. gap이 있어도 동작에 문제없게 설계해야 한다.

### CDC로 폴링을 대체하기

폴링 워커는 결국 DB를 주기적으로 긁는다. 폴링 주기를 짧게 하면 부하가 커지고, 길게 하면 지연이 커진다. 규모가 커지면 폴링 대신 CDC(Change Data Capture)로 넘어가는 걸 검토하게 된다.

Oracle에서 CDC는 GoldenGate나 LogMiner 기반이다. 리두 로그(redo log)를 읽어서 아웃박스 테이블의 INSERT를 감지하고 그걸 그대로 메시지로 흘려보낸다. 애플리케이션은 아웃박스에 INSERT만 하고, 폴링 워커 없이 CDC가 알아서 발행한다. Debezium의 Oracle 커넥터도 내부적으로 LogMiner(또는 GoldenGate)를 쓴다.

장점은 DB에 폴링 부하를 안 준다는 것과 지연이 작다는 것이다. 단점이 만만치 않다.

- LogMiner 기반 CDC는 리두 로그를 파싱하는데, 이게 CPU를 꽤 먹고 DDL이나 대용량 배치 트랜잭션이 있으면 지연이 급증한다.
- Supplemental logging을 켜야 한다(`ALTER DATABASE ADD SUPPLEMENTAL LOG DATA`). 이걸 켜면 리두 로그 양이 늘어서 스토리지와 아카이빙 부담이 커진다. DBA와 반드시 협의해야 한다.
- GoldenGate는 별도 라이선스 제품이라 비용이 크다.

작은 규모에서 CDC까지 가는 건 과하다. 폴링으로 시작해서 폴링 부하가 실제로 문제가 될 때 CDC를 검토하는 순서가 맞다. Debezium/CDC의 일반론은 아웃박스 문서에 있다.

## Oracle AQ를 메시지 브로커로 쓰기

Oracle에는 AQ(Advanced Queuing)라는 DB 내장 메시지 큐가 있다. 큐가 DB 테이블로 구현되어 있어서, 메시지 발행이 일반 DML과 같은 트랜잭션에 들어간다. 아웃박스 패턴에서 고민하는 "DB 커밋과 메시지 발행의 원자성" 문제가 AQ에서는 그냥 사라진다. 비즈니스 데이터 INSERT와 큐 enqueue가 같은 트랜잭션이니 둘 다 커밋되거나 둘 다 롤백된다.

```sql
-- 큐 테이블과 큐 생성
BEGIN
  DBMS_AQADM.CREATE_QUEUE_TABLE(
    queue_table => 'order_events_qt',
    queue_payload_type => 'order_event_typ');
  DBMS_AQADM.CREATE_QUEUE(
    queue_name => 'order_events_q',
    queue_table => 'order_events_qt');
  DBMS_AQADM.START_QUEUE(queue_name => 'order_events_q');
END;
/
```

비즈니스 로직과 같은 트랜잭션에서 enqueue한다.

```sql
DECLARE
  enqueue_options    DBMS_AQ.enqueue_options_t;
  message_properties DBMS_AQ.message_properties_t;
  message_handle     RAW(16);
  payload            order_event_typ;
BEGIN
  INSERT INTO orders (...) VALUES (...);   -- 비즈니스 데이터

  payload := order_event_typ('ORDER_CREATED', ...);
  DBMS_AQ.ENQUEUE(
    queue_name => 'order_events_q',
    enqueue_options => enqueue_options,
    message_properties => message_properties,
    payload => payload,
    msgid => message_handle);

  COMMIT;   -- INSERT와 ENQUEUE가 함께 커밋된다
END;
/
```

장점은 명확하다. 트랜잭션 원자성이 공짜다. 아웃박스 테이블도, 폴링 워커도, CDC도 필요 없다. 이미 Oracle을 쓰고 DBA가 있는 조직이라면 새 인프라(Kafka 클러스터, 주키퍼/KRaft, 모니터링) 없이 큐를 바로 쓸 수 있다. 트랜잭션 보장이 필요한 소규모 내부 서비스 간 통신에는 나쁘지 않다.

단점이 왜 대부분 Kafka로 가는지를 설명한다.

- 처리량. AQ는 결국 DB 테이블이다. 초당 수만~수십만 메시지를 Kafka처럼 흘려보내는 용도가 아니다. 발행량이 늘면 DB의 리두 로그와 undo에 그대로 부하가 간다. 큐가 곧 DB 부하다.
- DB 결합. AQ에 의존하면 모든 컨슈머가 Oracle에 붙어야 한다. 소비 측 서비스가 Node.js든 Go든 Oracle 클라이언트와 AQ 프로토콜을 물어야 한다. Kafka는 언어 중립적인 클라이언트 생태계가 넓다.
- 재처리와 보관. Kafka는 로그를 보관해서 컨슈머가 오프셋을 되감아 재처리할 수 있다. AQ는 dequeue하면 메시지가 소비되어 사라지는 큐 모델이라(멀티 컨슈머 큐로 흉내낼 수는 있지만) 이벤트 소싱이나 대규모 fan-out에는 안 맞는다.
- 운영 생태계. Kafka는 모니터링, 스키마 레지스트리, 커넥터 생태계가 성숙해 있다. AQ는 DBA 영역이라 애플리케이션 팀이 큐 상태를 관찰하기 불편하다.

선택 기준은 이렇게 잡는다. 트랜잭션 원자성이 핵심이고 발행량이 크지 않고 컨슈머가 몇 개 안 되며 이미 Oracle 조직이면 AQ가 합리적이다. 처리량이 크거나, 여러 컨슈머가 이벤트를 각자 재처리해야 하거나, 폴리글랏(다언어) 서비스가 붙거나, 이벤트 스트림을 데이터 플랫폼으로 흘려야 하면 Kafka다. 현실에서는 트랜잭션이 중요한 일부 경로만 AQ로 하고 나머지는 아웃박스+Kafka로 가는 혼합이 많다.

## 커넥션 관리: processes/sessions 고갈

MSA로 넘어가면서 Oracle에서 가장 먼저 터지는 게 커넥션이다. 모놀리스일 때는 애플리케이션 인스턴스 몇 개가 커넥션 풀을 나눠 썼는데, MSA는 서비스 15개 × 각 서비스 인스턴스 4개 × 풀 사이즈 20 = 1200 커넥션이 된다. 이게 인스턴스 하나의 Oracle을 그대로 친다.

```
ORA-00020: maximum number of processes (%s) exceeded
```

Oracle은 전용 서버 모드(dedicated server)에서 세션 하나당 서버 프로세스 하나를 띄운다. `processes` 파라미터가 상한이고, `sessions`는 대략 `processes * 1.1 + 5`로 자동 계산된다. 현재 사용량은 이렇게 본다.

```sql
SELECT resource_name, current_utilization, max_utilization, limit_value
FROM v$resource_limit
WHERE resource_name IN ('processes', 'sessions');
```

`max_utilization`이 `limit_value`에 근접하면 곧 `ORA-00020`이 난다. `processes`를 무작정 올리면(예: 3000) 세션마다 PGA 메모리를 먹으니 서버 메모리가 터진다. 프로세스 수와 메모리는 트레이드오프다.

### 풀 사이징이 먼저다

파라미터를 올리기 전에 커넥션 풀부터 손봐야 한다. 흔한 착각이 "풀을 크게 잡으면 빠르다"인데, DB 커넥션은 CPU 코어 수의 몇 배를 넘어가면 오히려 컨텍스트 스위칭으로 느려진다. HikariCP 문서의 권장도 작은 풀이다.

HikariCP를 Oracle에 붙일 때 실무 설정.

```
# 서비스 인스턴스 하나당 풀 크기. 서비스 인스턴스 수 × 이 값이
# Oracle processes 안에 들어와야 한다
maximumPoolSize=10
minimumIdle=10          # min과 max를 같게 두면 풀 크기가 요동치지 않는다
connectionTimeout=3000  # 풀에서 커넥션 못 얻으면 3초 만에 실패 (무한 대기 금지)
maxLifetime=1800000     # 30분. RAC/방화벽이 유휴 커넥션을 끊기 전에 먼저 재생성
validationTimeout=2000
connectionTestQuery=SELECT 1 FROM DUAL   # Oracle은 SELECT 1이 안 되니 DUAL 필요
```

`maxLifetime`을 안 잡으면 방화벽이나 RAC가 유휴 커넥션을 조용히 끊은 걸 애플리케이션이 모르고 있다가, 그 죽은 커넥션을 꺼내 쓰는 순간 이 오류가 난다.

```
ORA-03113: end-of-file on communication channel
ORA-03135: connection lost contact
```

`maxLifetime`을 DB/방화벽의 유휴 타임아웃보다 짧게 잡아서 풀이 먼저 커넥션을 갈아끼우게 하면 이 문제가 크게 준다.

전체 커넥션 총량 관리가 핵심이다. 서비스별 풀 크기 합이 Oracle `processes`의 70~80% 안에 들어오도록 역산해야 한다. 서비스를 추가할 때마다 이 총량 계산을 다시 해야 하고, 이걸 안 하고 서비스만 계속 붙이면 어느 날 갑자기 `ORA-00020`으로 전 서비스가 접속 불가가 된다.

### UCP와 RAC의 FAN/FCF

Oracle에는 자체 커넥션 풀인 UCP(Universal Connection Pool)가 있다. HikariCP보다 무겁지만 RAC 환경에서 UCP만 되는 기능이 있다. FAN(Fast Application Notification)과 FCF(Fast Connection Failover)다.

RAC는 여러 노드가 하나의 DB를 서비스한다. 노드 하나가 죽으면, HikariCP 같은 범용 풀은 그 노드로 붙어 있던 커넥션이 죽은 걸 다음에 쓸 때야 안다. 그 사이 요청들이 죽은 커넥션을 꺼내 쓰다 에러가 난다. UCP는 FAN 이벤트를 RAC로부터 실시간으로 받아서, 노드가 내려가는 즉시 그 노드로 향한 커넥션을 풀에서 제거하고 살아 있는 노드로 재분배한다(FCF). 새 노드가 붙으면 부하를 자동으로 그쪽으로 흘린다(런타임 로드 밸런싱).

RAC를 쓰고 노드 장애 시 빠른 페일오버가 필요하면 UCP를 쓰는 게 맞다. RAC가 아니거나 단순한 구성이면 HikariCP로 충분하고 더 가볍다. RAC인데 HikariCP를 쓴다면, 최소한 `maxLifetime`을 짧게 잡고 커넥션 검증을 켜서 죽은 커넥션이 오래 안 남게 방어해야 한다.

## 스키마 마이그레이션과 라이브러리 캐시 락

서비스가 독립 배포되면 스키마 변경도 서비스마다 독립적이어야 한다. 각 서비스가 자기 스키마의 마이그레이션을 Flyway나 Liquibase로 관리한다. order_svc는 `order_svc` 스키마의 `flyway_schema_history`만, payment_svc는 자기 것만 본다. 서비스별로 마이그레이션 이력이 완전히 분리되니, 공유 스키마를 쓰지 않는 게 여기서도 전제 조건이다.

```
# order_svc의 Flyway 설정. 자기 스키마만 관리한다
flyway.url=jdbc:oracle:thin:@//host:1521/PAYMENT_PDB
flyway.user=order_svc
flyway.schemas=order_svc
flyway.locations=classpath:db/migration/order
```

Oracle 마이그레이션에서 특히 조심할 건 DDL이 유발하는 락이다.

### DDL과 라이브러리 캐시 락

Oracle에서 테이블에 DDL(`ALTER TABLE`, `CREATE INDEX` 등)을 걸면, 그 테이블을 참조하는 SQL 커서를 라이브러리 캐시에서 무효화(invalidate)해야 한다. 이를 위해 라이브러리 캐시 락을 잡는데, 그 테이블에 실행 중인 트랜잭션(DML)이 있으면 DDL이 그 락을 못 얻고 대기한다.

```
ORA-04021: timeout occurred while waiting to lock object
ORA-00054: resource busy and acquire with NOWAIT specified or timeout expired
```

트래픽이 있는 시간에 `ALTER TABLE`을 실행하면, 진행 중인 트랜잭션 뒤에서 DDL이 대기하고, 그 대기하는 DDL 뒤로 새 트랜잭션들이 또 줄줄이 막힌다. DDL 하나가 그 테이블 전체를 얼려버린다. 무중단 배포를 한다면서 마이그레이션 스크립트에 `ALTER TABLE ... ADD COLUMN NOT NULL`을 넣으면 운영 중에 서비스가 멈춘다.

11g부터 `DDL_LOCK_TIMEOUT`을 세션에 걸어서 DDL이 락을 무한정 안 기다리게 할 수 있다.

```sql
ALTER SESSION SET ddl_lock_timeout = 10;  -- 10초 안에 락 못 얻으면 ORA-00054로 실패
ALTER TABLE orders ADD (memo VARCHAR2(200));
```

이러면 DDL이 실패하더라도 트래픽을 오래 막지는 않는다. 실패하면 트래픽 적은 시간에 재시도한다.

### 무중단 스키마 변경

Oracle 무중단 변경의 원칙은 다른 DB와 같다. 파괴적 변경을 여러 단계로 쪼갠다.

- 컬럼 추가는 nullable로만. `NOT NULL` + default를 한 번에 걸면 구버전 테이블 전체를 다시 쓰는 락이 걸린다(11g부터 default 있는 NOT NULL 추가가 메타데이터만 바꾸도록 개선됐지만, 버전과 조건에 따라 다르니 운영 테이블에서는 nullable로 추가 → 백필 → 제약 추가로 나누는 게 안전하다).
- 컬럼 삭제는 즉시 하지 말고 `SET UNUSED`로 논리적으로만 끊었다가 나중에 물리 삭제한다. `DROP COLUMN`은 테이블을 다시 쓰므로 큰 테이블에서 오래 걸린다.

```sql
-- 즉시: 메타데이터만 바꿔 컬럼을 안 보이게
ALTER TABLE orders SET UNUSED (legacy_flag);
-- 나중에 트래픽 적을 때: 물리 삭제
ALTER TABLE orders DROP UNUSED COLUMNS;
```

- 인덱스는 `CREATE INDEX ... ONLINE`으로 만들어서 생성 중에도 DML이 되게 한다. `ONLINE` 없이 큰 테이블에 인덱스를 걸면 그동안 그 테이블 쓰기가 막힌다.

```sql
CREATE INDEX idx_orders_status ON orders(status) ONLINE;
```

마이그레이션과 애플리케이션 배포 순서도 중요하다. 컬럼을 추가할 때는 DB 먼저(구버전 코드는 새 컬럼을 몰라도 됨), 컬럼을 제거할 때는 코드 먼저 배포해서 아무도 그 컬럼을 안 쓰게 만든 다음 DB에서 제거한다. 순서를 반대로 하면 배포 중간에 `ORA-00904: invalid identifier`(없는 컬럼 참조)나 `ORA-01400: cannot insert NULL`이 난다.

## RAC와 Data Guard로 가용성·읽기 분산

Oracle을 쓰는 조직이 MSA에서 얻는 게 있다면 이미 갖춘 고가용성 인프라다.

### RAC로 노드 장애 대응

RAC(Real Application Clusters)는 여러 노드가 공유 스토리지 위에서 하나의 DB를 서비스한다. 노드 하나가 죽어도 나머지 노드가 서비스를 계속한다. MSA 관점에서 RAC의 값은 DB 단일 장애점을 없애는 것이다. 앞서 말한 FAN/FCF와 UCP를 붙이면 노드 장애 시 애플리케이션이 거의 무중단으로 살아 있는 노드로 넘어간다.

주의할 건 RAC가 만능이 아니라는 것이다. 여러 노드가 같은 블록을 동시에 갱신하려 하면 노드 간에 블록을 인터커넥트로 주고받는데(cache fusion), 이때 이 대기 이벤트가 뜬다.

```
gc buffer busy acquire / gc current block busy
```

핫한 행(예: 카운터, 시퀀스, 좁은 범위의 인덱스)에 여러 노드가 동시에 쓰면 인터커넥트 병목이 생겨서 오히려 단일 노드보다 느려질 수 있다. MSA에서는 서비스별로 접속할 RAC 서비스(service_name)를 나눠서, 특정 서비스는 특정 노드에 주로 붙게 하면(서비스별 노드 어피니티) 이 경합을 줄일 수 있다.

```sql
-- 서비스를 특정 노드에 선호 배치
srvctl add service -d ORCL -s order_svc_srv -preferred node1 -available node2
srvctl add service -d ORCL -s payment_svc_srv -preferred node2 -available node1
```

order_svc는 `order_svc_srv`로, payment_svc는 `payment_svc_srv`로 접속하게 하면, 평상시엔 서비스별로 노드가 나뉘어 cache fusion 경합이 줄고, 노드 하나가 죽으면 available 노드로 자동 페일오버된다.

### Data Guard로 읽기 분산

Data Guard는 주(primary) DB의 변경을 대기(standby) DB로 복제한다. 재해 복구가 주 목적이지만, Active Data Guard 옵션(별도 라이선스)을 켜면 standby를 읽기 전용으로 열어서 조회 부하를 그쪽으로 보낼 수 있다.

MSA에서 읽기가 압도적으로 많은 서비스(조회 전용 API, 리포트, 대시보드)의 SELECT를 standby로 돌리면 primary의 부하가 준다. 커넥션 문자열이나 서비스 라우팅으로 읽기 트래픽을 standby 쪽 서비스로 보낸다.

함정은 복제 지연(replication lag)이다. Data Guard는 비동기 복제가 기본이라 standby가 primary보다 몇 초 뒤처질 수 있다. 방금 primary에 쓴 데이터를 바로 standby에서 읽으면 없거나 옛날 값이 나온다. "주문을 넣고 바로 주문 목록을 조회" 같은 read-your-own-write가 필요한 경로는 standby로 보내면 안 된다. 이런 경로는 primary로 읽고, 지연을 감수해도 되는 조회(어제까지의 집계, 통계)만 standby로 보낸다. 이건 CQRS에서 읽기 모델을 분리하는 것과 같은 고민이고, [이벤트_소싱_및_CQRS](이벤트_소싱_및_CQRS.md)와도 연결된다.

## 정리하면서 남기는 실무 감각

Oracle 위에서 MSA를 한다는 건 대개 "이미 Oracle에 크게 투자한 조직"이라는 뜻이다. 그래서 이론적으로 이상적인 "서비스마다 독립 오픈소스 DB"를 처음부터 하긴 어렵다. 현실적인 선은 이렇다.

물리 분리를 못 하더라도 논리 분리(스키마-per-service)를 코드와 권한으로 강제하고, 크로스 스키마 조인과 DB Link를 금지해서 나중에 뽑아낼 수 있는 상태를 유지한다. 분산 트랜잭션은 XA/2PC 대신 Saga·아웃박스로 가고, 아웃박스는 SKIP LOCKED 폴링으로 시작해서 규모가 커지면 CDC를 검토한다. 커넥션은 서비스 추가마다 총량을 역산해서 `ORA-00020`을 예방하고, RAC를 쓴다면 UCP+FAN으로 페일오버를 챙긴다. 스키마 변경은 DDL 락을 의식해서 파괴적 변경을 단계로 쪼갠다.

Oracle이 가진 RAC/Data Guard 같은 가용성 자산은 MSA에서도 그대로 값을 한다. 문제는 그 강력한 기능들(DB Link, XA)이 MSA의 원칙을 어기기 너무 쉽게 만든다는 것이다. 편한 길이 대부분 강결합으로 가는 길이라, 의식적으로 그 유혹을 막는 게 Oracle MSA의 핵심이다.
