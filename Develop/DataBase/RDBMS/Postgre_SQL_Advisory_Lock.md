---
title: PostgreSQL Advisory Lock
tags: [postgresql, database, spring, java, backend]
updated: 2026-09-28
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

## 공유 락 변형

Advisory Lock에는 배타 락 외에 공유 락 변형도 있다. 같은 키의 공유 락끼리는 호환되지만 배타 락과는 충돌한다.

| 함수 | 레벨 | 블로킹 |
|---|---|---|
| `pg_advisory_lock_shared(key)` | 세션 | O |
| `pg_try_advisory_lock_shared(key)` | 세션 | X |
| `pg_advisory_xact_lock_shared(key)` | 트랜잭션 | O |
| `pg_try_advisory_xact_lock_shared(key)` | 트랜잭션 | X |

```sql
-- 여러 세션이 동시에 공유 락을 획득할 수 있다
SELECT pg_try_advisory_xact_lock_shared(100);  -- 세션 A: true
SELECT pg_try_advisory_xact_lock_shared(100);  -- 세션 B: true

-- 공유 락이 잡혀 있는 상태에서 배타 락 시도
SELECT pg_try_advisory_xact_lock(100);  -- 세션 C: false
```

공유 락이 실제로 필요한 경우는 제한적이다. "읽기는 동시에 허용하되 쓰기 작업이 시작되면 읽기도 차단"하는 상황인데, 대부분 MVCC로 해결된다. 스케줄러가 동작 중일 때 설정 변경을 막는 식의 관리 작업에서 간혹 쓰인다.

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
SELECT pg_try_advisory_xact_lock((1::bigint << 32) | 1234::bigint);  -- order 1234
SELECT pg_try_advisory_xact_lock((2::bigint << 32) | 1234::bigint);  -- payment 1234
```

두 개의 `int`를 받는 오버로드를 쓰면 비트 연산 없이 더 직관적이다.

```sql
-- pg_try_advisory_xact_lock(int, int)
SELECT pg_try_advisory_xact_lock(1, 1234);  -- order 1234
SELECT pg_try_advisory_xact_lock(2, 1234);  -- payment 1234
```

두 번째 방식이 실수할 여지가 적다. 도메인 코드와 리소스 ID를 분리해서 넘기기 때문에 비트 연산 실수가 없다.

`hashtext('order:1234')::bigint`처럼 문자열에서 키를 만들면 사람이 읽기 쉽지만, `hashtext`가 32bit 해시를 생성하므로 `bigint`로 캐스팅할 때 충돌 가능성이 남는다. 도메인이 적고 리소스 ID가 크지 않으면 비트 분할 방식이 더 안전하다.

## Spring JdbcTemplate 패턴

JPA를 쓰더라도 Advisory Lock은 JdbcTemplate으로 잡는 게 일반적이다. JPQL이나 `@Query`로는 PostgreSQL 전용 함수를 호출하기 번거롭다.

트랜잭션 레벨 락은 `@Transactional` 메서드 안에서 호출해야 한다. `pg_try_advisory_xact_lock`은 트랜잭션 블록 밖에서 호출하면 `ERROR: pg_try_advisory_xact_lock cannot be used outside a transaction block`을 낸다.

```java
@Component
@RequiredArgsConstructor
public class PostgresAdvisoryLock {

    private final JdbcTemplate jdbcTemplate;

    // domainCode: 서비스별 고유 코드, resourceId: Long 타입 그대로 받는다
    public boolean tryLock(int domainCode, long resourceId) {
        // bigint 단일 키 오버로드 — Long 값을 그대로 전달한다
        long key = ((long) domainCode << 32) | (resourceId & 0xFFFFFFFFL);
        return Boolean.TRUE.equals(
            jdbcTemplate.queryForObject(
                "SELECT pg_try_advisory_xact_lock(?)",
                Boolean.class,
                key
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
        if (!advisoryLock.tryLock(DOMAIN_ORDER, orderId)) {
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

### orderId.intValue() 오버플로 버그

두 개의 `int` 오버로드를 쓸 때 `orderId.intValue()`를 그대로 넘기면 오버플로가 발생한다.

```java
// 잘못된 코드
jdbcTemplate.queryForObject(
    "SELECT pg_try_advisory_xact_lock(?, ?)",
    Boolean.class,
    DOMAIN_ORDER,
    orderId.intValue()  // Long → int 변환 시 상위 32bit 소실
);
```

`Long.intValue()`는 단순히 하위 32bit만 취한다. orderId가 `Integer.MAX_VALUE(2,147,483,647)`를 넘는 순간부터 문제가 생긴다. 예를 들어 orderId=2,147,483,648(=2^31)은 `intValue()` 결과가 `-2,147,483,648`이고, orderId=6,442,450,944(=2^31 + 2^32)는 `intValue()` 결과도 `-2,147,483,648`이다. 실제로는 다른 주문인데 같은 락 키로 매핑되어, 아무 관계 없는 두 요청이 서로를 블로킹한다.

현대 서비스에서 주문 ID가 20억을 넘는 것은 흔한 일이다. `BIGSERIAL`로 생성된 ID는 처음부터 Long 범위를 쓴다고 가정해야 한다.

안전한 방법은 bigint 단일 키 오버로드를 써서 Long 값 전체를 전달하거나, 위 예제처럼 도메인 코드와 리소스 ID를 비트 연산으로 조합해 하나의 `long`으로 만드는 것이다.

## Spring REQUIRES_NEW 전파에서의 우회

`@Transactional(propagation = Propagation.REQUIRES_NEW)`는 현재 트랜잭션을 잠시 중단하고 새 트랜잭션을 **별도 커넥션**으로 시작한다. Advisory Lock은 세션(커넥션)에 귀속되기 때문에, 내부 트랜잭션이 잡으려는 락은 외부 트랜잭션과 다른 PostgreSQL 세션에서 평가된다.

```java
@Transactional
public void outer(Long orderId) {
    // 커넥션 A에서 락 획득 → true
    advisoryLock.tryLock(DOMAIN_ORDER, orderId);

    inner(orderId);
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
public void inner(Long orderId) {
    // 커넥션 B(새 세션)에서 같은 키로 tryLock 호출
    // PostgreSQL은 A와 B를 다른 세션으로 보기 때문에 true 반환
    // — outer가 이미 락을 잡았지만 inner가 이를 우회한다
    advisoryLock.tryLock(DOMAIN_ORDER, orderId);
}
```

이 경우 같은 orderId에 대해 두 개의 트랜잭션이 동시에 실행된다. Advisory Lock의 중복 처리 방지 목적이 완전히 무력화된다.

반대로 REQUIRED 전파에서는 같은 커넥션을 재사용하기 때문에 다른 문제가 생긴다. Advisory Lock은 재진입(reentrant)이다. 같은 세션에서 같은 키를 두 번 잡으면 내부 카운터가 2가 되고, 두 번 해제해야 락이 실제로 풀린다. REQUIRED 전파로 중첩된 `@Transactional`에서 같은 키로 락을 두 번 잡으면 외부 트랜잭션이 커밋되어도 락이 해제되지 않는다.

Advisory Lock은 트랜잭션 전파 수준이 단순한 진입점 하나에서만 사용해야 한다. REQUIRES_NEW를 쓰는 내부 서비스에는 Advisory Lock을 추가하지 않는 것이 맞다.

## PgBouncer transaction mode의 함정

PgBouncer를 transaction pooling mode로 운영할 때 Advisory Lock 사용에 제약이 생긴다.

PgBouncer transaction mode는 클라이언트가 트랜잭션을 시작하면 PostgreSQL 백엔드 커넥션을 배정하고, 트랜잭션이 끝나면 그 커넥션을 풀에 돌려보낸다. 각 트랜잭션마다 다른 PostgreSQL 세션을 쓸 수 있다.

**세션 레벨 락은 transaction mode에서 완전히 깨진다.** 커넥션 A에서 `pg_advisory_lock(123)`으로 락을 잡은 뒤 트랜잭션이 끝나면 PgBouncer가 A를 풀에 반환한다. 다음 트랜잭션은 커넥션 B를 받는다. B에서 `pg_advisory_unlock(123)`을 호출하면 B는 그 락을 갖고 있지 않으므로 해제가 되지 않는다. A의 락은 A가 풀에서 완전히 제거될 때까지 남아 해당 키로 들어오는 모든 요청을 블로킹한다.

**트랜잭션 레벨 락은 transaction mode에서 정상 동작한다.** `pg_advisory_xact_lock`은 트랜잭션 종료와 함께 해제되고, PgBouncer transaction mode에서 하나의 트랜잭션은 반드시 하나의 백엔드 커넥션에 매핑된다. 트랜잭션이 커밋·롤백되면 락도 함께 풀린다.

PgBouncer에는 statement pooling mode도 있다. 이 모드는 쿼리마다 다른 백엔드를 배정한다. 이 경우 트랜잭션 레벨 락도 의미가 없어진다. `SELECT pg_advisory_xact_lock(123)`이 커넥션 A에서 실행되고, `COMMIT`이 커넥션 B에서 실행되면 A의 락은 트랜잭션이 끝나지 않은 채로 남는다. statement mode는 Advisory Lock과 함께 쓸 수 없다.

PgBouncer를 쓰는 환경이라면 `SHOW POOLS;`나 설정 파일로 pooling mode를 먼저 확인한다. session mode라면 세션·트랜잭션 레벨 모두 쓸 수 있고, transaction mode라면 반드시 트랜잭션 레벨 락만 써야 한다.

## 다중 PostgreSQL 인스턴스에서의 한계

Advisory Lock은 단일 PostgreSQL 인스턴스 범위에서만 동작한다. 같은 키로 락을 잡아도 인스턴스가 다르면 서로 간섭하지 않는다.

**멀티 프라이머리 환경**: 두 개 이상의 프라이머리가 동시에 쓰기를 받는 환경에서 Advisory Lock은 분산 락이 되지 못한다. 각 프라이머리 인스턴스가 독립적인 락 상태를 갖기 때문에, 인스턴스 A에 요청 1이 들어오고 인스턴스 B에 요청 2가 들어오면 각각 락을 획득하고 둘 다 처리를 진행한다.

**샤딩 환경**: 주문 ID 범위에 따라 다른 PostgreSQL 인스턴스로 라우팅되는 구성에서도 같다. orderId=1000이 샤드 A로, orderId=2000이 샤드 B로 가면 두 요청은 각자의 샤드에서 락을 독립적으로 획득한다. 락 키가 같아도 다른 인스턴스에 있으면 충돌이 발생하지 않는다.

**읽기 복제본**: 복제본에서 Advisory Lock을 잡으면 프라이머리와 독립적으로 동작한다. 복제 지연과 무관하게 락 상태가 인스턴스별로 분리된다.

단일 프라이머리 + 읽기 복제본 구성에서 모든 쓰기 요청이 같은 프라이머리로 가는 일반적인 구성에서는 Advisory Lock이 정상적으로 동작한다. 인스턴스 하나가 락 관리자 역할을 하기 때문이다.

멀티 프라이머리나 샤딩 환경에서 인스턴스 경계를 넘는 배타성이 필요하면 Advisory Lock만으로는 보장할 수 없다. Redis SET NX 또는 Zookeeper 기반 분산 락을 추가로 고려해야 한다.

## InnoDB 기반 MySQL과의 차이

MySQL InnoDB도 `GET_LOCK()` / `RELEASE_LOCK()` 함수로 애플리케이션 레벨 락을 쓸 수 있다.

```sql
-- MySQL
SELECT GET_LOCK('order:1234', 0);    -- 0초 타임아웃 (즉시 반환)
-- ... 작업 ...
SELECT RELEASE_LOCK('order:1234');
```

MySQL `GET_LOCK()`은 문자열 키를 쓰고, PostgreSQL Advisory Lock은 정수 키를 쓴다. 결정적인 차이는 트랜잭션과의 관계다. MySQL `GET_LOCK()`은 트랜잭션과 완전히 독립적이다. 트랜잭션을 롤백해도 락은 그대로 남는다. PostgreSQL `pg_advisory_xact_lock`처럼 트랜잭션 종료와 연동되는 기능이 없다.

PostgreSQL은 기본 격리 수준이 `READ COMMITTED`이고 MVCC 구현상 행 버전을 테이블에 저장한다. 높은 격리 수준이 필요하면 `SERIALIZABLE`로 올리거나 Advisory Lock을 쓴다. 여러 행에 걸친 논리적 묶음(같은 사용자의 여러 주문 등)에 대해 복잡한 `FOR UPDATE` 쿼리 없이 락을 잡을 때 Advisory Lock이 간결하다.

## 운영 시 확인 방법

현재 잡혀 있는 Advisory Lock 목록은 `pg_locks`로 확인한다.

```sql
SELECT
    pid,
    locktype,
    classid,
    objid,
    mode,
    granted
FROM pg_locks
WHERE locktype = 'advisory';
```

`classid`와 `objid`가 락 키를 나타낸다. 두 개의 `int` 오버로드를 쓰면 `classid`가 첫 번째 인자, `objid`가 두 번째 인자에 해당한다. `granted = false`이면 락을 획득하려고 대기 중인 세션이다. `mode`가 `ShareLock`이면 공유 락, `ExclusiveLock`이면 배타 락이다.

락이 장기간 잡혀 있는 경우를 찾을 때는 `pg_stat_activity`와 조인한다.

```sql
SELECT
    a.pid,
    a.query,
    a.state,
    a.query_start,
    l.classid,
    l.objid,
    l.mode,
    l.granted
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.locktype = 'advisory'
ORDER BY a.query_start;
```

세션 레벨 락이 풀리지 않은 채로 커넥션이 풀에 남아 있을 때 이 쿼리로 진단한다. `pid`로 해당 세션을 확인하고 필요하면 `SELECT pg_terminate_backend(pid)`로 강제 종료한다.

Advisory Lock 관련 대기가 쌓이기 시작하면 `granted = false`인 행의 수가 늘어난다. 이 상태가 지속되면 `pg_stat_activity`에서 `wait_event_type = 'Lock'`인 세션과 `wait_event = 'advisory'`를 함께 확인해 어느 키에서 병목이 생기는지 특정한다.
