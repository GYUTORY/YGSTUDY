---
title: MVCC
tags: [database, rdbms, 트랜잭션격리수준mvcc데드락진단]
updated: 2025-08-10
---
## 1) 트랜잭션 격리수준 한눈 비교

격리수준은 동시에 처리되는 트랜잭션들이 서로에게 얼마나 간섭할 수 있는지의 기준이다. 낮출수록 성능은 좋아지지만, 이상현상(Dirty/Non-repeatable/Phantom)이 발생할 수 있다.

| 격리수준 | 허용되는 이상현상 | MySQL(InnoDB) 기본 | PostgreSQL 기본 |
|---|---|---|---|
| Read Uncommitted | Dirty Read까지 허용 | 지원은 하지만 거의 사용 안 함 | 미지원 |
| Read Committed | Non-repeatable, Phantom 가능 | 선택적 | 기본값 |
| Repeatable Read | Phantom(이론상 가능) | 기본값(Next-key Lock으로 Phantom 대부분 차단) | 선택적 |
| Serializable | 이상현상 방지 | 락 기반 직렬화(성능 비용 큼) | SSI 기반 직렬화(충돌 감지로 롤백) |

용어 정리
- Dirty Read: 커밋되지 않은 변경을 읽음
- Non-repeatable Read: 같은 조건을 두 번 읽을 때 값이 달라짐
- Phantom Read: 같은 조건을 두 번 읽을 때 결과 집합의 “행 수”가 달라짐(새 행이 생기거나 사라짐)

운영 팁
- 기본은 Read Committed(PostgreSQL) 또는 Repeatable Read(MySQL). 비즈니스 요구가 명확할 때만 Serializable로 올린다.
- “조회 + 집계”는 Read Committed로도 충분한 경우가 많다. “정합성이 최우선인 결제/재고”처럼 민감 영역은 트랜잭션 경계를 짧게 가져가고 적절한 락을 사용한다.

---

## 2) MVCC 핵심: InnoDB vs PostgreSQL

둘 다 “같은 데이터를 보는 시점이 달라도 일관된 스냅샷”을 제공한다. 구현 방식과 부수 비용이 다르다.

- MySQL InnoDB
  - Undo Log 기반 스냅샷: 커밋 이전 버전은 Undo Log로 복구해 일관 읽기 제공
  - Next-key Lock: 레코드락 + 갭락 조합으로 Phantom을 대부분 차단(Repeatable Read)
  - Purge/History Length 관리: 오래된 버전은 퍼지 스레드가 정리. 업데이트 폭주 시 Undo가 길어져 지연이 늘 수 있음
- PostgreSQL
  - 다중 버전 튜플(xmin/xmax): 새로운 튜플을 추가하고, 오래된 버전은 VACUUM으로 청소
  - Snapshot Isolation: 기본 Read Committed/Repeatable Read에서 스냅샷 제공, Serializable은 SSI로 충돌 감지·롤백
  - Autovacuum: 튜플 청소·통계 갱신. 지연이 잦다면 autovacuum 설정과 인덱스 설계를 함께 본다

용어 정리
- Undo Log: 과거 버전을 재구성하기 위한 변경 이력
- 갭 락(Gap Lock): 특정 범위의 “빈 공간”에 대한 삽입을 막는 락
- VACUUM/Autovacuum: 사용하지 않는 튜플/인덱스 엔트리 청소

---

## 3) 데드락(Deadlock) 진단과 대응

데드락은 서로가 서로의 락을 기다려 영원히 진행되지 않는 상태다. 두 DB 모두 주기적으로 데드락을 감지하고 “더 싸게” 롤백 가능한 트랜잭션을 희생시킨다.

원인 패턴
- 동일 자원에 대해 다른 순서로 락을 획득(락 순서 불일치)
- 넓은 범위 락(인덱스 부재로 테이블/범위 락 확대)
- 긴 트랜잭션(오래 쥐고 있는 락이 많아짐)

진단 쿼리 예시
- MySQL(InnoDB)
  - 최근 데드락 로그: `SHOW ENGINE INNODB STATUS\G` (최근 1건)
  - 락 대기 관찰: `SELECT * FROM performance_schema.data_locks;` / `SELECT * FROM performance_schema.metadata_locks;`
  - sys 스키마 뷰: `SELECT * FROM sys.schema_lock_waits;`
- PostgreSQL
  - 현재 락/대기: `pg_locks` 조인 `pg_stat_activity`
  - 예: 대기 관계 보기
    ```sql
    SELECT bl.pid AS blocked_pid, ka.query AS blocking_query, a.query AS blocked_query
    FROM pg_locks bl
    JOIN pg_stat_activity a ON a.pid = bl.pid
    JOIN pg_locks kl ON kl.locktype = bl.locktype AND kl.pid <> bl.pid AND kl.granted
    JOIN pg_stat_activity ka ON ka.pid = kl.pid
    WHERE NOT bl.granted;
    ```

대응 원칙
- 락 순서를 통일(예: 항상 id 오름차순으로 접근)
- 트랜잭션을 짧게. SELECT … FOR UPDATE 범위를 작게(적절한 인덱스 필수)
- 불필요한 갭락 유발 방지: 커버링/복합 인덱스로 범위를 좁혀 삽입 충돌 완화
- 재시도 전략: 데드락은 일부 상황에서 정상 동작. 실패 시 재시도(backoff+jitter) 구현

---

## 4) EXPLAIN 해석 기초(MySQL vs PostgreSQL)

### MySQL EXPLAIN 주요 컬럼
| 컬럼 | 설명 |
|---|---|
| id | SELECT 단위 식별자(서브쿼리/파생 테이블 포함) |
| select_type | SIMPLE/PRIMARY/DERIVED 등 쿼리 유형 |
| table | 접근 테이블 |
| type | 접근 방식: ALL(풀스캔) < index < range < ref < eq_ref < const/system |
| possible_keys | 후보 인덱스 |
| key | 실제 사용 인덱스 |
| key_len | 인덱스 사용 길이(선두열만 쓰였는지 체크) |
| ref | 조인 키 기준 |
| rows | 추정 스캔 행 수 |
| filtered | 필터링 비율(%) |
| Extra | Using index/where/temporary/filesort 등 힌트 |

간단 팁
- `type`이 `ALL`이면 인덱스 부재 가능성 큼. 조건에 맞는 인덱스 설계
- `key_len`으로 복합 인덱스의 선두열 활용 여부 확인
- `Using temporary`/`filesort`는 정렬/그룹 비용 신호. 가능한 인덱스 정렬로 대체

### PostgreSQL EXPLAIN(ANALYZE)
- Scan: Seq Scan(풀 스캔), Index Scan(순차 접근), Bitmap Index + Heap Scan(대량 범위에 유리)
- Join: Nested Loop(소량/인덱스 유리), Hash Join(대량/해시 가능), Merge Join(정렬된 입력)
- 비용 표기: `cost=시작..끝 rows=예상 width=바이트`
  - `ANALYZE` 옵션을 붙이면 실제 시간/행 수도 출력 → 통계 정확도 확인 가능

간단 팁
- 예상(rows) vs 실제(actual rows)가 크게 다르면 통계 갱신(ANALYZE) 또는 조건/인덱스 재설계
- 작은 범위/고선택도 조건은 Index Scan, 넓은 범위는 Bitmap Scan이 유리할 때가 많음

예시(공통 시나리오)
```sql
-- 공통: 사용자 주문 조회
-- 필요한 인덱스(예): orders(user_id, created_at), users(id)

-- MySQL
EXPLAIN SELECT *
FROM orders o
JOIN users u ON u.id = o.user_id
WHERE o.user_id = ? AND o.created_at >= ?
ORDER BY o.created_at DESC
LIMIT 50;

-- PostgreSQL
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders o
JOIN users u ON u.id = o.user_id
WHERE o.user_id = $1 AND o.created_at >= $2
ORDER BY o.created_at DESC
LIMIT 50;
```

---

## 5) 운영에 바로 쓰는 요령
격리수준은 업무별로 필요한 만큼만 올리고, Serializable은 정말 필요한 구간만 짧게 잡는 게 낫다. 인덱스는 조건열을 선두로 두고 정렬/조인 열 순서를 맞춘다. 데드락은 재현보다 관찰이 빠르다. `pg_locks`나 `performance_schema`, 최근 데드락 로그를 상시로 본다. 트랜잭션은 짧게 유지하고, 사용자 인터랙션 중에는 걸어두지 않는다. 배치 작업은 청크로 쪼개고, 재시도는 백오프와 지터를 섞어 멱등하게 처리하자.

---

## 6) 관련 문서
- `Lock.md`: 락 종류/동작 더 자세히
- `RDBMS에서의 index.md`: 인덱스 설계 심화

## 배경





실무에서 성능과 안정성을 동시에 잡으려면, 격리수준과 MVCC 동작, 그리고 데드락을 어떻게 다루는지가 핵심이다. 아래는 MySQL(InnoDB)와 PostgreSQL 기준으로 핵심만 자연스럽게 정리했다.

---





# 트랜잭션 격리수준 / MVCC / 데드락 진단

