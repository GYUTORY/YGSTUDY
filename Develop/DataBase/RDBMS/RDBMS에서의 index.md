---
title: RDBMS에서의 Index
tags: [database, rdbms, index, b-tree, innodb, clustering-index]
updated: 2026-03-29
---

# RDBMS에서의 Index

## 인덱스란

인덱스는 테이블의 특정 컬럼 값과 해당 행의 위치를 매핑하는 별도의 자료구조다. 테이블에 100만 행이 있을 때 인덱스 없이 `WHERE email = 'foo@bar.com'`을 실행하면 100만 행을 전부 읽어야 한다. 인덱스가 있으면 B-Tree를 타고 3~4번의 페이지 접근만으로 찾는다.

인덱스는 디스크에 별도 공간을 차지하고, 데이터 변경(INSERT/UPDATE/DELETE)마다 같이 갱신된다. 읽기가 빨라지는 대신 쓰기에 비용이 생긴다. 이 트레이드오프를 모르고 인덱스를 무작정 만들면 오히려 성능이 나빠진다.

## B-Tree (B+Tree) 내부 구조

MySQL InnoDB, PostgreSQL, Oracle 모두 기본 인덱스 구조로 B+Tree를 쓴다. B+Tree는 B-Tree의 변형으로, 실제 데이터 포인터가 리프 노드에만 존재한다.

### 노드 구성

```
루트 노드       [10 | 20 | 30]
               /    |    |    \
브랜치 노드  [5,8] [12,15] [22,25] [35,40]
              |      |       |       |
리프 노드   [1,3,5,7,8] → [10,12,13,15] → [20,22,23,25] → [30,35,38,40]
            (이전/다음 리프를 가리키는 포인터로 연결)
```

핵심 특성:

- 루트에서 모든 리프까지의 깊이가 동일하다 (balanced)
- 리프 노드끼리 양방향 링크드 리스트로 연결되어 있어 범위 스캔이 가능하다
- 각 노드는 하나의 페이지(InnoDB 기준 16KB)에 대응한다
- 트리 깊이는 보통 3~4 수준이다. INT 타입 PK 기준 약 2천만 행까지 깊이 3으로 커버한다

### 페이지 내부 구조

InnoDB 인덱스 페이지(16KB) 하나의 실제 레이아웃:

```
┌───────────────────────────────────────┐
│ File Header (38 bytes)                │
│  - 페이지 번호, 이전/다음 페이지 포인터 │
├───────────────────────────────────────┤
│ Page Header (56 bytes)                │
│  - 레코드 수, 힙 상위 포인터          │
├───────────────────────────────────────┤
│ Infimum / Supremum Records            │
│  - 페이지 내 최소/최대 경계 레코드     │
├───────────────────────────────────────┤
│ User Records                          │
│  [키값 | 트랜잭션ID | 롤백포인터 | 컬럼들] │
│  [키값 | 트랜잭션ID | 롤백포인터 | 컬럼들] │
│  ...                                  │
├───────────────────────────────────────┤
│ Free Space                            │
├───────────────────────────────────────┤
│ Page Directory (슬롯 배열)            │
│  - 페이지 내 이진 탐색용 슬롯         │
├───────────────────────────────────────┤
│ File Trailer (8 bytes)                │
│  - 체크섬                             │
└───────────────────────────────────────┘
```

Page Directory의 슬롯은 페이지 내부에서 이진 탐색을 하기 위한 구조다. 레코드가 수백 개 들어있어도 슬롯 배열을 통해 빠르게 위치를 찾는다.

### 탐색 과정

`WHERE id = 25`를 실행할 때 일어나는 일:

1. 버퍼 풀에서 루트 페이지를 읽는다 (루트는 거의 항상 메모리에 있다)
2. 루트 페이지의 키를 비교해서 다음에 읽을 브랜치 페이지 번호를 결정한다
3. 브랜치 페이지에서 같은 방식으로 리프 페이지 번호를 결정한다
4. 리프 페이지에서 Page Directory 슬롯을 이용해 이진 탐색으로 레코드를 찾는다

디스크 I/O는 최악의 경우 트리 깊이만큼(보통 3~4회) 발생한다. 자주 접근하는 상위 노드 페이지는 버퍼 풀에 캐시되어 있어 실제 디스크 읽기는 리프 노드 접근 1~2회 정도다.

## InnoDB의 클러스터링 인덱스

InnoDB에서 인덱스를 이해하려면 클러스터링 인덱스(Clustered Index)와 세컨더리 인덱스(Secondary Index)의 구분이 필수다. 이 구조를 모르면 쿼리 성능을 예측할 수 없다.

### 클러스터링 인덱스

InnoDB 테이블의 데이터는 PK 순서대로 물리적으로 정렬되어 저장된다. 테이블 자체가 PK 기준의 B+Tree다. 리프 노드에 행 데이터 전체가 들어있다.

```
클러스터링 인덱스 (PK = id)

루트        [id=500]
           /        \
브랜치  [id=100,200] [id=600,800]
         /    |   \
리프  [id=1, 전체 행 데이터] → [id=2, 전체 행 데이터] → [id=3, 전체 행 데이터] → ...
```

PK가 없는 테이블이면 InnoDB가 UNIQUE NOT NULL 컬럼을 찾아서 쓰고, 그것도 없으면 내부적으로 6바이트 숨겨진 ROW_ID를 생성한다.

PK를 `UUID`로 잡으면 삽입 순서가 랜덤이라 페이지 분할이 빈번하게 발생한다. AUTO_INCREMENT가 순차 삽입이라 페이지 분할이 거의 없다. UUID를 PK로 써야 하는 상황이면 MySQL 8.0의 `UUID_TO_BIN(UUID(), 1)` 같은 순서 보장 UUID 변환을 고려한다.

### 세컨더리 인덱스의 PK 참조 구조

세컨더리 인덱스(일반 인덱스)의 리프 노드에는 행 데이터가 아니라 **PK 값**이 들어있다.

```
세컨더리 인덱스 (idx_name)

리프: [name='Alice', PK=3] → [name='Bob', PK=1] → [name='Charlie', PK=2]

'Alice'를 찾으면:
1) 세컨더리 인덱스에서 name='Alice' → PK=3 획득
2) 클러스터링 인덱스에서 PK=3으로 다시 탐색 → 행 데이터 획득
```

이 두 번째 탐색을 **랜덤 I/O를 동반한 클러스터링 인덱스 룩업**이라 한다. 세컨더리 인덱스로 조회한 결과가 많으면 PK 룩업 횟수도 그만큼 늘어나서, 옵티마이저가 차라리 풀 테이블 스캔을 선택하는 경우가 있다.

이 구조 때문에 생기는 실무 영향:

- **PK가 크면 모든 세컨더리 인덱스가 커진다.** 세컨더리 인덱스마다 PK를 저장하므로, PK가 BIGINT(8바이트)인 것과 VARCHAR(36) UUID(36바이트)인 것은 인덱스 크기 차이가 상당하다
- **커버링 인덱스가 중요해진다.** 세컨더리 인덱스만으로 쿼리에 필요한 컬럼을 다 가져올 수 있으면 클러스터링 인덱스 룩업을 생략한다. 커버링 인덱스 설계는 [쿼리 옵티마이저](쿼리_옵티마이저.md) 문서 참고
- **PK 범위 스캔은 순차 I/O다.** 클러스터링 인덱스 리프가 PK 순서로 물리적으로 연속이므로, `WHERE id BETWEEN 1000 AND 2000` 같은 PK 범위 조회는 매우 빠르다

### PostgreSQL과의 차이

PostgreSQL은 힙 테이블 구조로, 테이블 데이터가 PK 순서와 무관하게 저장된다. 인덱스 리프에는 ctid(물리적 행 위치)가 들어있어서 PK 룩업 없이 바로 행에 접근한다. 대신 MVCC 가시성 확인을 위해 힙 페이지를 반드시 방문해야 하는데, 이를 줄이기 위해 Visibility Map과 Index-Only Scan을 활용한다.

## Hash 인덱스

해시 함수로 키를 해시값으로 변환하고, 해시값에 대응하는 버킷에서 데이터를 찾는 구조다.

- 동등 비교(`=`)만 가능하다. 범위 검색(`>`, `<`, `BETWEEN`), 정렬(`ORDER BY`)에 사용할 수 없다
- 복합 키 `(A, B, C)`를 해시하면 세 컬럼 전체를 합쳐서 하나의 해시값을 만든다. A만으로는 조회 불가능하다
- MySQL InnoDB는 Adaptive Hash Index를 내부적으로 자동 생성하지만, 사용자가 직접 해시 인덱스를 만들 수는 없다 (MEMORY 엔진에서만 가능)
- PostgreSQL은 해시 인덱스를 지원하지만 WAL 로깅 문제로 오래 기피되었고, PostgreSQL 10부터 WAL 지원이 추가되었다

실무에서 해시 인덱스를 직접 지정할 일은 거의 없다. B-Tree가 동등 비교도 충분히 빠르고, 범위 검색까지 되기 때문이다.

## 인덱스 종류별 특성

### 유니크 인덱스 vs 일반 인덱스

유니크 인덱스는 중복 값을 허용하지 않는다. InnoDB에서 유니크 인덱스와 일반 인덱스의 읽기 성능 차이는 거의 없다. 차이가 나는 건 쓰기 쪽이다.

일반 인덱스는 Change Buffer를 활용할 수 있다. 인덱스 페이지가 버퍼 풀에 없을 때, 변경 내용을 Change Buffer에 기록해두고 나중에 병합한다. 유니크 인덱스는 중복 체크를 위해 반드시 인덱스 페이지를 읽어야 하므로 Change Buffer를 쓸 수 없다.

쓰기가 많은 테이블에서 비즈니스적으로 유니크 보장이 필요 없다면 일반 인덱스가 쓰기 성능에 유리하다.

### 함수 기반 인덱스

MySQL 8.0과 PostgreSQL은 표현식에 대한 인덱스를 지원한다.

```sql
-- MySQL 8.0
CREATE INDEX idx_lower_email ON users ((LOWER(email)));

-- PostgreSQL
CREATE INDEX idx_lower_email ON users (LOWER(email));
```

`WHERE LOWER(email) = 'foo@bar.com'` 같은 쿼리에서 인덱스를 탈 수 있다. 이 인덱스가 없으면 `LOWER(email)` 계산 때문에 인덱스를 사용하지 못하고 풀 스캔이 발생한다.

### 부분 인덱스 (PostgreSQL)

PostgreSQL은 조건을 만족하는 행만 인덱싱하는 부분 인덱스를 지원한다.

```sql
-- active 상태인 행만 인덱싱
CREATE INDEX idx_active_users ON users (email) WHERE active = true;
```

전체 행의 10%만 active라면 인덱스 크기가 10분의 1로 줄어든다. MySQL에서는 부분 인덱스를 지원하지 않는다.

### 특수 인덱스

- **Full-Text 인덱스**: 텍스트 검색용. 역색인(inverted index) 구조. MySQL FULLTEXT, PostgreSQL GIN
- **Spatial 인덱스**: 지리 데이터용. R-Tree 구조. `ST_Contains`, `ST_Distance` 같은 공간 함수와 함께 사용
- **GIN (Generalized Inverted Index)**: PostgreSQL. 배열, JSONB, 전문검색에 사용. 한 행이 여러 키를 가질 때 적합
- **BRIN (Block Range Index)**: PostgreSQL. 물리적으로 정렬된 대용량 테이블에서 소량의 인덱스 공간으로 범위 필터링. 시계열 데이터의 timestamp 컬럼에 적합

## 인덱스와 락

인덱스 구조는 트랜잭션 격리 수준과 락 동작에 직접적으로 영향을 준다. 특히 InnoDB의 REPEATABLE READ 격리 수준에서 이 부분을 모르면 데드락이나 예상 밖의 락 대기를 겪게 된다.

### InnoDB의 행 단위 락은 인덱스에 건다

InnoDB의 행 락(row lock)은 테이블 행 자체가 아니라 **인덱스 레코드**에 건다. `WHERE name = 'Alice'`로 UPDATE를 실행하면, `name` 컬럼의 인덱스 레코드에 락이 걸린다.

인덱스가 없으면? 클러스터링 인덱스(PK)의 **모든 레코드**에 락이 걸린다. 사실상 테이블 락과 같은 효과다. 이것이 인덱스 설계가 동시성에 직결되는 이유다.

```sql
-- employees 테이블에 name 인덱스가 없는 경우
BEGIN;
UPDATE employees SET salary = 5000 WHERE name = 'Alice';
-- name에 인덱스가 없으므로 풀 스캔 → 모든 행에 락
-- 다른 트랜잭션에서 Bob을 UPDATE하려 해도 대기
```

### Gap Lock과 Next-Key Lock

REPEATABLE READ에서 InnoDB는 팬텀 리드를 방지하기 위해 Gap Lock과 Next-Key Lock을 사용한다.

**Record Lock**: 특정 인덱스 레코드 하나에만 걸리는 락

**Gap Lock**: 인덱스 레코드 사이의 "간격"에 걸리는 락. 해당 간격에 새로운 행이 INSERT되는 것을 방지한다

**Next-Key Lock**: Record Lock + 그 앞 Gap Lock의 조합. InnoDB의 기본 락 단위다

```sql
-- age 컬럼에 인덱스가 있고, 현재 age 값이 10, 20, 30인 행이 있다고 가정

BEGIN;
SELECT * FROM users WHERE age = 20 FOR UPDATE;
```

이 쿼리가 잡는 락 범위:

```
인덱스 레코드:  10 ... 20 ... 30
                   ^^^^^^^^^^^^
                   (10, 20] 에 Next-Key Lock
                   (20, 30) 에 Gap Lock

→ 다른 트랜잭션에서 age=15 INSERT 불가 (Gap Lock)
→ 다른 트랜잭션에서 age=20 UPDATE 불가 (Record Lock)
→ 다른 트랜잭션에서 age=25 INSERT 불가 (Gap Lock)
```

### 인덱스 설계가 락 범위를 결정한다

같은 쿼리라도 인덱스가 어떻게 잡혀있느냐에 따라 락 범위가 완전히 달라진다.

```sql
-- 시나리오: status='pending'인 주문을 처리

-- Case 1: status에 인덱스 없음
UPDATE orders SET status = 'processing' WHERE status = 'pending';
-- → 풀 스캔 → 모든 행에 넥스트키 락 → 사실상 테이블 전체 잠금

-- Case 2: status에 인덱스 있음
UPDATE orders SET status = 'processing' WHERE status = 'pending';
-- → 인덱스 스캔 → status='pending'인 레코드와 그 주변 간격만 잠금
```

Case 1에서는 `status = 'shipped'`인 주문을 조회하는 것조차 락 대기에 걸릴 수 있다. 인덱스를 추가하는 것만으로 동시성이 극적으로 개선되는 사례다.

데드락 분석 시 `SHOW ENGINE INNODB STATUS`의 LATEST DETECTED DEADLOCK 섹션에서 어떤 인덱스의 어떤 레코드에 락이 걸렸는지 확인한다. 인덱스 구조를 모르면 이 출력을 해석할 수 없다.

## 인덱스가 쓰기에 미치는 영향

인덱스는 읽기를 빠르게 하지만, 모든 쓰기 작업에 오버헤드를 추가한다.

### INSERT

새 행이 추가되면 모든 인덱스의 B-Tree에 키를 삽입해야 한다. 인덱스가 10개면 INSERT 한 번에 B-Tree 삽입이 10번 발생한다.

키 삽입 위치가 리프 페이지의 빈 공간에 들어가면 문제없지만, 페이지가 가득 찬 상태면 **페이지 분할(page split)**이 발생한다. 페이지 분할은 새 페이지를 할당하고 기존 페이지의 절반을 이동시키는 작업이라 비용이 크다.

### UPDATE

인덱싱된 컬럼의 값이 바뀌면 기존 인덱스 엔트리를 삭제 마킹하고 새 엔트리를 삽입한다. 인덱싱되지 않은 컬럼만 변경되면 인덱스에는 영향이 없다.

InnoDB는 실제로 엔트리를 즉시 물리 삭제하지 않고 delete mark만 하고 나중에 퍼지 스레드가 정리한다.

### DELETE

DELETE된 행의 인덱스 엔트리도 즉시 제거되지 않고 delete mark 처리된다. 대량 DELETE 후에는 인덱스에 삭제 마킹된 레코드가 쌓여서 스캔 효율이 떨어질 수 있다.

### 대량 데이터 적재 시 팁

수백만 건을 한 번에 INSERT할 때는 인덱스 오버헤드가 심하다.

```sql
-- MySQL: 세컨더리 인덱스를 삭제하고 적재 후 재생성
ALTER TABLE big_table DROP INDEX idx_name;
ALTER TABLE big_table DROP INDEX idx_email;

LOAD DATA INFILE '/path/to/data.csv' INTO TABLE big_table ...;

ALTER TABLE big_table ADD INDEX idx_name (name);
ALTER TABLE big_table ADD INDEX idx_email (email);
```

인덱스를 삭제하고 적재하면, B-Tree 삽입과 페이지 분할이 없어서 적재 속도가 수 배 빨라진다. 적재 후 인덱스를 한 번에 만들면 정렬된 데이터를 순차적으로 빌드하므로 더 효율적이다.

## 온라인 DDL로 인덱스 관리

운영 중인 서비스에서 인덱스를 추가하거나 삭제하는 건 DML(INSERT/UPDATE/DELETE)을 차단할 수 있어서 신중해야 한다.

### MySQL 온라인 DDL

MySQL 5.6부터 온라인 DDL이 도입되었다. 인덱스 추가/삭제는 대부분 `ALGORITHM=INPLACE, LOCK=NONE`으로 처리할 수 있어 DML을 차단하지 않는다.

```sql
-- 온라인으로 인덱스 추가 (DML 차단 없음)
ALTER TABLE orders ADD INDEX idx_status (status), ALGORITHM=INPLACE, LOCK=NONE;
```

주의할 점:

- **메타데이터 락(MDL)**: DDL 시작과 끝에 짧은 시간 동안 메타데이터 락을 획득한다. 이 순간에 장시간 실행 중인 트랜잭션이 있으면 DDL이 대기하고, DDL 뒤에 오는 모든 쿼리도 연쇄적으로 대기한다. DDL 실행 전에 `information_schema.innodb_trx`에서 오래된 트랜잭션이 없는지 확인한다
- **임시 디스크 공간**: 온라인 인덱스 빌드 중 임시 정렬 파일이 생긴다. `innodb_tmpdir`이 충분한 공간을 가진 디스크를 가리키는지 확인한다. 테이블 크기의 1~2배 여유 공간이 필요하다
- **리플리케이션 지연**: 온라인 DDL이 완료된 후 바이너리 로그에 기록되므로, 레플리카에서는 해당 DDL이 한 번에 적용된다. 대형 테이블이면 레플리카에서 상당한 지연이 발생할 수 있다

### pt-online-schema-change / gh-ost

MySQL 온라인 DDL의 메타데이터 락 문제를 피하려면 외부 도구를 쓸 수 있다.

- **pt-online-schema-change** (Percona): 임시 테이블을 만들고 트리거로 변경 사항을 복제한 뒤 테이블을 교체한다
- **gh-ost** (GitHub): 트리거 대신 바이너리 로그를 파싱해서 변경 사항을 복제한다. 트리거의 오버헤드가 없고 일시정지/재개가 가능하다

대형 테이블(수억 행 이상)에서 인덱스를 추가할 때는 이런 도구를 사용하는 것이 안전하다.

### PostgreSQL의 CONCURRENTLY

PostgreSQL에서는 `CREATE INDEX CONCURRENTLY`를 쓰면 테이블에 대한 쓰기를 차단하지 않고 인덱스를 생성할 수 있다.

```sql
CREATE INDEX CONCURRENTLY idx_status ON orders (status);
```

일반 `CREATE INDEX`는 테이블에 `SHARE` 락을 잡아서 쓰기를 차단한다. `CONCURRENTLY`는 테이블을 두 번 스캔하는 방식으로 락 없이 인덱스를 생성하지만, 시간이 더 걸리고 실패할 수 있다. 실패하면 `INVALID` 상태의 인덱스가 남으므로 `DROP INDEX`로 정리해야 한다.

## 미사용 인덱스 탐지와 정리

인덱스는 만들어놓고 잊어버리기 쉽다. 쿼리 패턴이 바뀌면서 더 이상 사용되지 않는 인덱스가 쌓이면, 쓰기 성능 저하와 디스크 낭비가 누적된다.

### MySQL

```sql
-- MySQL 8.0: sys 스키마에서 미사용 인덱스 조회
SELECT * FROM sys.schema_unused_indexes
WHERE object_schema NOT IN ('mysql', 'sys', 'performance_schema');
```

`performance_schema`의 `table_io_waits_summary_by_index_usage` 테이블에서 인덱스별 사용 횟수를 확인할 수 있다. 서버 재시작 후 충분한 시간(최소 1주일, 가능하면 1개월)이 지난 뒤에 판단한다. 월말 배치나 분기별 리포트에서만 쓰는 인덱스를 놓칠 수 있기 때문이다.

```sql
-- 인덱스별 사용 통계 상세 조회
SELECT
    object_schema,
    object_name,
    index_name,
    count_read,
    count_write,
    count_fetch
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = 'mydb'
  AND index_name IS NOT NULL
ORDER BY count_read ASC;
```

`count_read = 0`이고 `count_write > 0`이면 쓰기 오버헤드만 발생하고 읽기에는 전혀 쓰이지 않는 인덱스다.

### PostgreSQL

```sql
-- 인덱스 스캔 횟수 조회
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

`idx_scan = 0`인 인덱스가 미사용 후보다. `pg_stat_reset()` 이후 충분한 시간이 지난 뒤에 판단한다.

### 정리 절차

미사용 인덱스를 발견했다고 바로 삭제하면 안 된다.

1. `INVISIBLE` (MySQL 8.0) 또는 이름 변경으로 비활성화한다
2. 1~2주 모니터링하며 문제가 없는지 확인한다
3. 문제가 없으면 삭제한다

```sql
-- MySQL 8.0: 인덱스를 보이지 않게 설정 (옵티마이저가 무시)
ALTER TABLE orders ALTER INDEX idx_old_status INVISIBLE;

-- 문제없으면 삭제
ALTER TABLE orders DROP INDEX idx_old_status;
```

MySQL 8.0의 `INVISIBLE INDEX`는 옵티마이저가 해당 인덱스를 사용하지 않도록 하면서도 인덱스 자체는 유지한다. 문제가 생기면 `VISIBLE`로 바로 복구할 수 있어서 안전하다.

## 인덱스 조각화와 재구성

데이터가 계속 변경되면 인덱스 페이지에 빈 공간이 생기고, 페이지 분할로 물리적 순서가 논리적 순서와 어긋나게 된다. 이것이 인덱스 조각화다.

### 조각화 확인

```sql
-- MySQL: 인덱스 통계 확인
ANALYZE TABLE orders;

SELECT
    table_name,
    index_name,
    stat_name,
    stat_value
FROM mysql.innodb_index_stats
WHERE table_name = 'orders'
  AND stat_name IN ('n_leaf_pages', 'size');
```

`size`(전체 페이지 수) 대비 `n_leaf_pages`(리프 페이지 수)의 비율이 크게 차이나면 내부 조각화가 심한 상태다.

```sql
-- PostgreSQL: bloat 추정
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE schemaname = 'public';
```

PostgreSQL에서는 `pgstattuple` 확장의 `pgstatindex()` 함수로 정확한 조각화 비율을 확인할 수 있다.

### 재구성 방법

**MySQL:**

```sql
-- 테이블과 인덱스 전체 재구성
ALTER TABLE orders ENGINE=InnoDB;

-- 또는 특정 인덱스 재구성 (MySQL 8.0.12+)
ALTER TABLE orders DROP INDEX idx_status, ADD INDEX idx_status (status);
```

`ALTER TABLE ... ENGINE=InnoDB`는 테이블을 완전히 재빌드한다. 온라인으로 처리되지만 임시 공간이 필요하다.

**PostgreSQL:**

```sql
-- 인덱스 재구성 (테이블 락 발생)
REINDEX INDEX idx_status;

-- 락 없이 재구성 (PostgreSQL 12+)
REINDEX INDEX CONCURRENTLY idx_status;
```

### 재구성 시점 판단

인덱스 재구성은 I/O 부하가 크므로 무조건 주기적으로 하는 것보다 필요할 때만 한다.

재구성을 고려하는 경우:

- 대량 DELETE/UPDATE 후 인덱스 크기가 줄지 않을 때
- 범위 스캔 성능이 점진적으로 느려질 때
- 인덱스의 물리적 크기가 예상보다 훨씬 클 때

InnoDB는 자체적으로 페이지 병합을 수행하므로, 일반적인 OLTP 워크로드에서는 인덱스 재구성이 자주 필요하지 않다. 대량 데이터 삭제 후가 가장 효과가 큰 시점이다.

## 인덱스 설계 시 고려사항

복합 인덱스의 컬럼 순서와 EXPLAIN 분석은 [쿼리 옵티마이저](쿼리_옵티마이저.md) 문서에서, 전반적인 성능 튜닝 관점은 [데이터베이스 성능 튜닝](데이터베이스_성능_튜닝.md) 문서에서 다룬다. 여기서는 인덱스 자체에 집중한다.

### 선택도(Cardinality)

선택도가 낮은 컬럼(성별처럼 2~3가지 값만 있는)에 단독 인덱스를 만들면 효과가 거의 없다. 인덱스로 절반을 걸러내봤자 나머지 절반을 다시 PK 룩업해야 하니, 옵티마이저가 풀 스캔을 선택한다.

그렇다고 선택도가 낮은 컬럼이 인덱스에 무조건 쓸모없는 건 아니다. 복합 인덱스에서 앞쪽에 고선택도 컬럼을 놓고, 뒤쪽에 저선택도 컬럼을 두면 유용할 수 있다.

### 인덱스 개수 관리

테이블당 인덱스 개수에 정해진 상한은 없지만, 경험적으로 OLTP 테이블에서 세컨더리 인덱스가 5~6개를 넘으면 점검이 필요하다. 인덱스가 많아질수록:

- INSERT 성능이 선형적으로 나빠진다
- 옵티마이저의 실행 계획 선택지가 늘어나서 잘못된 인덱스를 고를 확률이 높아진다
- 버퍼 풀에서 인덱스 페이지가 차지하는 비중이 커져 데이터 페이지 캐시 적중률이 떨어진다

### 프리픽스 인덱스

긴 문자열 컬럼에 인덱스를 걸 때 앞부분 N자만 인덱싱할 수 있다.

```sql
-- email 컬럼의 앞 10자만 인덱싱
CREATE INDEX idx_email_prefix ON users (email(10));
```

인덱스 크기가 줄어드는 장점이 있지만, 커버링 인덱스로 사용할 수 없고 `ORDER BY`에도 활용할 수 없다. 프리픽스 길이가 너무 짧으면 선택도가 낮아져서 인덱스 효과가 떨어진다.

적절한 프리픽스 길이를 결정하는 방법:

```sql
-- 프리픽스 길이별 고유 값 비율 확인
SELECT
    COUNT(DISTINCT LEFT(email, 5)) / COUNT(*) AS sel_5,
    COUNT(DISTINCT LEFT(email, 10)) / COUNT(*) AS sel_10,
    COUNT(DISTINCT LEFT(email, 15)) / COUNT(*) AS sel_15,
    COUNT(DISTINCT email) / COUNT(*) AS sel_full
FROM users;
```

전체 선택도의 90% 이상을 커버하는 길이를 선택한다.

## 정리

| 구분 | 핵심 |
|------|------|
| B+Tree | 기본 인덱스 구조. 범위 스캔, 정렬, 부분 키 검색 가능 |
| 클러스터링 인덱스 | InnoDB 테이블 = PK 기준 B+Tree. 리프에 행 데이터 전체 |
| 세컨더리 인덱스 | 리프에 PK 값 저장. PK가 크면 세컨더리 인덱스도 커짐 |
| 인덱스와 락 | 행 락은 인덱스 레코드에 걸림. 인덱스 없으면 사실상 테이블 락 |
| 온라인 DDL | 운영 중 인덱스 추가 시 MDL, 임시 공간, 레플리카 지연 주의 |
| 미사용 인덱스 | 주기적으로 탐지하고, INVISIBLE로 비활성화 후 안전하게 삭제 |
| 조각화 | 대량 삭제 후가 재구성 효과가 가장 큰 시점 |
