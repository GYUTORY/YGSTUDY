---
title: PostgreSQL Advisory Lock
tags: [postgresql, architecture, os, spring]
updated: 2026-07-30
---

# PostgreSQL Advisory Lock

Advisory Lock은 PostgreSQL이 제공하는 애플리케이션 수준의 사용자 정의 락이다. 테이블 행이나 인덱스에 자동으로 걸리는 일반 락과 달리, 개발자가 직접 획득·해제 시점을 제어한다. 락 키는 64bit 정수이며, 그 의미는 애플리케이션이 정의한다.

주로 쓰이는 상황은 이렇다. 같은 주문 ID에 대한 중복 요청이 동시에 들어왔을 때 하나만 처리하게 막거나, 특정 배치 작업이 다중 인스턴스 중 한 곳에서만 실행되도록 보장해야 할 때다.

## pg_advisory_lock vs pg_try_advisory_lock

두 함수의 차이는 블로킹 여부다.

`pg_advisory_lock(key bigint)`는 락을 획득할 수 있을 때까지 블로킹한다. 다른 세션이 같은 키로 락을 잡고 있으면 그 세션이 해제할 때까지 대기한다.

`pg_try_advisory_lock(key bigint)`는 즉시 반환한다. 락 획득에 성공하면 `true`, 이미 다른 세션이 잡고 있으면 `false`를 돌려준다.

```sql
-- 블로킹: 락이 풀릴 때까지 대기
SELECT pg_advisory_lock(12345);

-- 비블로킹: 즉시 결과 반환
SELECT pg_try_advisory_lock(12345);  -- true 또는 false
```

실무에서는 `pg_try_advisory_lock`을 더 많이 쓴다. 블로킹 방식은 상대 세션이 예외로 죽거나 커넥션이 끊겨도 대기가 이어지기 때문에 `lock_timeout`을 별도로 설정해줘야 한다. `SET lock_timeout = '5s'`를 먼저 실행하거나, 처음부터 비블로킹 방식을 쓰는 게 낫다.

## 세션 레벨 vs 트랜잭션 레벨

Advisory Lock은 세션 레벨과 트랜잭션 레벨 두 가지가 있다. 커넥션 풀 환경에서 이 둘을 혼동하면 락 누수가 발생한다.

**세션 레벨**은 트랜잭션이 커밋되거나 롤백되어도 락이 유지된다. 명시적으로 `pg_advisory_unlock(key)`를 호출하거나 세션(커넥션) 자체가 종료될 때 해제된다. 함수는 `pg_advisory_lock`, `pg_try_advisory_lock`이다.

**트랜잭션 레벨**은 트랜잭션이 끝나면 자동으로 해제된다. 함수는 `pg_advisory_xact_lock`, `pg_try_advisory_xact_lock`이다.

```sql
-- 세션 레벨: 명시적 해제가 필요하다
SELECT pg_advisory_lock(12345);
-- ... 작업 ...
SELECT pg_advisory_unlock(12345);  -- 반드시 호출해야 한다

-- 트랜잭션 레벨: 트랜잭션 종료 시 자동 해제
BEGIN;
SELECT pg_advisory_xact_lock(12345);
-- ... 작업 ...
COMMIT;  -- 여기서 락 자동 해제
```

HikariCP 같은 커넥션 풀을 쓰는 환경에서 세션 레벨 락을 쓰면 문제가 생긴다. 커넥션이 풀에 반환된 뒤에도 락이 유지되기 때문에, 다음에 그 커넥션을 할당받은 요청이 이미 락이 잡힌 상태로 시작한다. 예외가 발생해서 `pg_advisory_unlock`을 호출하지 못한 채 커넥션이 반환되면 그 락은 해당 커넥션이 풀에서 완전히 제거될 때까지 남는다.

트랜잭션 레벨 락은 이 문제가 없다. Spring `@Transactional` 범위와 락 범위가 일치하므로 트랜잭션이 끝나면 락도 같이 해제된다. 커넥션 풀 환경에서는 트랜잭션 레벨 락을 기본으로 써야 한다.

## 64bit 정수 키 설계

Advisory Lock의 키는 `bigint`(64bit signed integer) 하나이거나, `int`(32bit) 두 개의 조합이다. 키의 의미는 전적으로 애플리케이션에서 정의한다.

같은 PostgreSQL 인스턴스를 여러 서비스나 도메인이 공유하면 키 충돌이 발생한다. `12345`라는 키를 주문 서비스와 결제 서비스가 동시에 쓰면 서로 블로킹한다.

**비트 분할 방식**: 상위 32bit을 도메인 코드, 하위 32bit을 리소스 ID로 쓴다.

```sql
-- 도메인 코드: order=1, payment=2, inventory=3
-- order 도메인의 리소스 1234
SELECT pg_try_advisory_xact_lock(
    (1::bigint << 32) | 1234::bigint
);

-- payment 도메인의 리소스 1234 — 키 값이 다르다
SELECT pg_try_advisory_xact_lock(
    (2::bigint << 32) | 1234::bigint
);
```

두 개의 `int`를 받는 오버로드를 쓰면 비트 연산 없이 더 직관적이다.

```sql
-- pg_try_advisory_xact_lock(int, int)
-- 첫 번째 인자: 도메인 코드, 두 번째 인자: 리소스 ID
SELECT pg_try_advisory_xact_lock(1, 1234);  -- order 1234
SELECT pg_try_advisory_xact_lock(2, 1234);  -- payment 1234
```

두 번째 방식이 실수할 여지가 적다. 도메인 코드와 리소스 ID를 분리해서 넘기기 때문에 비트 연산 실수가 없다.

**hashtext 방식**도 쓰이지만 주의가 필요하다. `hashtext('order:1234')::bigint`처럼 문자열에서 키를 만들면 사람이 읽기 쉽지만, `hashtext`가 32bit 해시를 생성하므로 `bigint`로 캐스팅할 때 충돌 가능성이 남는다. 도메인이 적고 리소스 ID가 크지 않으면 비트 분할 방식이 더 안전하다.

## Spring JdbcTemplate 패턴

JPA를 쓰더라도 Advisory Lock은 JdbcTemplate으로 잡는 게 일반적이다. JPQL이나 `@Query`로는 PostgreSQL 전용 함수를 호출하기 번거롭다.

트랜잭션 레벨 락은 `@Transactional` 메서드 안에서 호출해야 한다. 트랜잭션이 시작된 뒤에 락을 잡아야 트랜잭션 종료 시 락도 같이 해제된다.

```java
@Component
@RequiredArgsConstructor
public class PostgresAdvisoryLock {

    private final JdbcTemplate jdbcTemplate;

    public boolean tryLock(int domainCode, int resourceId) {
        return Boolean.TRUE.equals(
            jdbcTemplate.queryForObject(
                "SELECT pg_try_advisory_xact_lock(?, ?)",
                Boolean.class,
                domainCode,
                resourceId
            )
        );
    }
}
```

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private static final int DOMAIN_ORDER = 1;

    private final PostgresAdvisoryLock advisoryLock;
    private final OrderRepository orderRepository;

    @Transactional
    public void processOrder(Long orderId) {
        if (!advisoryLock.tryLock(DOMAIN_ORDER, orderId.intValue())) {
            throw new ConcurrentModificationException("이미 처리 중인 주문입니다: " + orderId);
        }

        Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new EntityNotFoundException("주문을 찾을 수 없습니다"));

        order.process();
        // @Transactional 종료 시 Advisory Lock 자동 해제
    }
}
```

`tryLock`이 `false`를 돌려줄 때 처리 방식은 상황에 따라 다르다. 결제처럼 중복 실행이 절대 안 되는 경우는 예외를 던지고, 배치처럼 "이미 실행 중이면 이 인스턴스는 건너뛴다"는 경우는 `false` 반환 후 조용히 종료한다.

`pg_try_advisory_xact_lock`은 트랜잭션 밖에서 호출하면 오류가 발생한다. `@Transactional`이 없는 메서드에서 호출하면 안 된다. 로컬 테스트 시 `@Transactional`을 빠뜨려서 `ERROR: pg_try_advisory_xact_lock cannot be used outside a transaction block`을 보는 경우가 있다.

## InnoDB 기반 MySQL과의 차이

MySQL InnoDB도 `GET_LOCK()` / `RELEASE_LOCK()` 함수로 애플리케이션 레벨 락을 쓸 수 있다.

```sql
-- MySQL
SELECT GET_LOCK('order:1234', 0);    -- 0초 타임아웃 (즉시 반환)
-- ... 작업 ...
SELECT RELEASE_LOCK('order:1234');
```

MySQL `GET_LOCK()`은 문자열 키를 쓰고, PostgreSQL Advisory Lock은 정수 키를 쓴다. 결정적인 차이는 트랜잭션과의 관계다. MySQL `GET_LOCK()`은 트랜잭션과 완전히 독립적이다. 트랜잭션을 롤백해도 락은 그대로 남는다. PostgreSQL `pg_advisory_xact_lock`처럼 트랜잭션 종료와 연동되는 기능이 없다.

락 전략 선택 기준도 다르다. MySQL InnoDB는 기본 격리 수준이 `REPEATABLE READ`이고 Next-Key Lock으로 Phantom Read를 막는다. 범위 조건이 있는 `SELECT FOR UPDATE`로도 동시성 제어가 되는 경우가 많아서 Advisory Lock을 쓸 필요성이 상대적으로 낮다.

PostgreSQL은 기본 격리 수준이 `READ COMMITTED`이고 MVCC 구현상 행 버전을 테이블에 저장(Heap에 다중 버전 유지)한다. 높은 격리 수준이 필요하면 `SERIALIZABLE`로 올리거나 Advisory Lock을 쓴다. 특히 여러 행에 걸친 논리적 묶음(같은 사용자의 여러 주문 등)에 대해 복잡한 `FOR UPDATE` 쿼리 없이 락을 잡을 때 Advisory Lock이 간결하다.

## 운영 시 확인 방법

현재 잡혀 있는 Advisory Lock 목록은 `pg_locks`로 확인한다.

```sql
SELECT
    pid,
    locktype,
    classid,
    objid,
    granted
FROM pg_locks
WHERE locktype = 'advisory';
```

`classid`와 `objid`가 락 키를 나타낸다. 두 개의 `int` 오버로드를 쓰면 `classid`가 첫 번째 인자, `objid`가 두 번째 인자에 해당한다. `granted = false`이면 락을 획득하려고 대기 중인 세션이다.

락이 장기간 잡혀 있는 경우를 찾을 때는 `pg_stat_activity`와 조인한다.

```sql
SELECT
    a.pid,
    a.query,
    a.state,
    a.query_start,
    l.classid,
    l.objid,
    l.granted
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.locktype = 'advisory'
ORDER BY a.query_start;
```

세션 레벨 락이 풀리지 않은 채로 커넥션이 풀에 남아 있을 때 이 쿼리로 진단한다. `pid`로 해당 세션을 확인하고 필요하면 `SELECT pg_terminate_backend(pid)`로 강제 종료한다.
