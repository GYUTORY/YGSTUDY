# 데이터베이스 락(Lock) 시스템

## 개요
- 데이터베이스에서 락(Lock)은 동시성 제어(Concurrency Control)의 핵심 메커니즘입니다.
- 여러 트랜잭션이 동시에 데이터에 접근할 때 데이터의 일관성과 무결성을 보장하기 위해 사용됩니다.
- 락은 데이터베이스 관리 시스템(DBMS)이 자동으로 관리하며, 개발자가 직접 제어할 수도 있습니다.

---

## 락의 종류와 특성

### 1. 공유 락(Shared Lock, S-Lock)
- **목적**: 데이터를 읽기만 할 때 사용
- **특징**:
  - 여러 트랜잭션이 동시에 같은 데이터에 대해 공유 락을 가질 수 있음
  - 다른 트랜잭션이 데이터를 수정하는 것을 방지
  - SELECT 문이 실행될 때 자동으로 설정됨
- **예시**:
  ```sql
  -- 공유 락이 자동으로 설정됨
  SELECT * FROM employees WHERE department = 'IT';
  ```

### 2. 배타 락(Exclusive Lock, X-Lock)
- **목적**: 데이터를 수정할 때 사용
- **특징**:
  - 한 트랜잭션만 락을 가질 수 있음
  - 다른 트랜잭션의 읽기/쓰기 모두 차단
  - UPDATE, INSERT, DELETE 문이 실행될 때 자동으로 설정됨
- **예시**:
  ```sql
  -- 배타 락이 자동으로 설정됨
  UPDATE employees SET salary = salary * 1.1 WHERE department = 'IT';
  ```

### 3. 의도 락(Intent Lock)
- **목적**: 테이블과 행 수준의 락을 효율적으로 관리
- **종류**:
  - IS(Intent Shared): 테이블의 일부 행에 공유 락을 걸 의도
  - IX(Intent Exclusive): 테이블의 일부 행에 배타 락을 걸 의도
  - SIX(Shared with Intent Exclusive): 테이블에 공유 락과 일부 행에 배타 락을 걸 의도
- **예시**:
  ```sql
  -- 테이블에 IX 락, 특정 행에 X 락이 설정됨
  UPDATE employees SET salary = salary * 1.1 WHERE employee_id = 100;
  ```

---

## 락의 범위(Level)

### 1. 행 수준 락(Row-Level Lock)
- **장점**:
  - 동시성 최대화
  - 락 충돌 최소화
- **단점**:
  - 락 관리 오버헤드 증가
  - 데드락 가능성 증가
- **사용 예**:
  ```sql
  -- 특정 행에만 락이 걸림
  UPDATE orders SET status = 'SHIPPED' WHERE order_id = 123;
  ```

### 2. 페이지 수준 락(Page-Level Lock)
- **특징**:
  - 데이터베이스 페이지 단위로 락 설정
  - 행 수준과 테이블 수준의 중간 단계
- **사용 예**:
  ```sql
  -- 페이지 단위로 락이 걸림
  UPDATE large_table SET column = value WHERE id BETWEEN 1000 AND 2000;
  ```

### 3. 테이블 수준 락(Table-Level Lock)
- **장점**:
  - 락 관리 오버헤드 감소
  - 구현이 단순
- **단점**:
  - 동시성 감소
  - 성능 저하 가능성
- **사용 예**:
  ```sql
  -- 전체 테이블에 락이 걸림
  ALTER TABLE employees ADD COLUMN bonus DECIMAL(10,2);
  ```

---

## 락 관련 문제와 해결방법

### 1. 데드락(Deadlock)
- **정의**: 두 개 이상의 트랜잭션이 서로가 가진 자원을 기다리며 무한 대기하는 상태
- **발생 조건**:
  1. 상호 배제(Mutual Exclusion)
  2. 점유와 대기(Hold and Wait)
  3. 비선점(No Preemption)
  4. 순환 대기(Circular Wait)
- **예시**:
  ```sql
  -- 트랜잭션 1
  BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  -- 트랜잭션 2
  BEGIN;
  UPDATE accounts SET balance = balance - 200 WHERE id = 2;
  -- 트랜잭션 1
  UPDATE accounts SET balance = balance + 100 WHERE id = 2; -- 대기
  -- 트랜잭션 2
  UPDATE accounts SET balance = balance + 200 WHERE id = 1; -- 데드락 발생
  ```
- **해결 방법**:
  1. 타임아웃 설정
  2. 락 획득 순서 표준화
  3. 데드락 감지 및 해소

### 2. 락 경합(Lock Contention)
- **정의**: 여러 트랜잭션이 같은 데이터에 접근하려 할 때 발생하는 경쟁 상태
- **해결 방법**:
  1. 트랜잭션 격리 수준 조정
  2. 인덱스 최적화
  3. 배치 처리 사용
  4. 낙관적 락 사용

---

## 락 모니터링과 최적화

### 1. 락 모니터링
```sql
-- MySQL
SHOW PROCESSLIST;
SHOW ENGINE INNODB STATUS;

-- PostgreSQL
SELECT * FROM pg_locks;
SELECT * FROM pg_stat_activity;

-- Oracle
SELECT * FROM v$lock;
SELECT * FROM v$session;
```

### 2. 락 최적화 전략
1. **적절한 격리 수준 선택**
   - READ UNCOMMITTED
   - READ COMMITTED
   - REPEATABLE READ
   - SERIALIZABLE

2. **인덱스 설계**
   - 자주 조회되는 컬럼에 인덱스 생성
   - 복합 인덱스 최적화

3. **트랜잭션 설계**
   - 트랜잭션 크기 최소화
   - 락 유지 시간 단축
   - 일관된 락 획득 순서 유지

4. **애플리케이션 레벨 최적화**
   - 낙관적 락 사용
   - 캐시 활용
   - 비동기 처리 고려

---

## 실제 사례와 모범 사례

### 1. 은행 시스템 예시
```sql
-- 안전한 계좌 이체
BEGIN;
-- 출금 계좌에 배타 락
SELECT balance FROM accounts WHERE account_id = 1 FOR UPDATE;
-- 입금 계좌에 배타 락
SELECT balance FROM accounts WHERE account_id = 2 FOR UPDATE;

UPDATE accounts SET balance = balance - 100 WHERE account_id = 1;
UPDATE accounts SET balance = balance + 100 WHERE account_id = 2;
COMMIT;
```

### 2. 재고 관리 시스템
```sql
-- 안전한 재고 감소
BEGIN;
-- 재고 확인 및 락
SELECT quantity FROM inventory WHERE product_id = 100 FOR UPDATE;

IF quantity >= 1 THEN
    UPDATE inventory SET quantity = quantity - 1 WHERE product_id = 100;
    COMMIT;
ELSE
    ROLLBACK;
END IF;
```

### 3. 모범 사례
1. **락 범위 최소화**
   - 필요한 최소한의 데이터에만 락 적용
   - 행 수준 락 선호

2. **락 유지 시간 최소화**
   - 트랜잭션을 가능한 짧게 유지
   - 락을 획득하기 전에 필요한 모든 준비 작업 수행

3. **일관된 락 획득 순서**
   - 모든 트랜잭션이 동일한 순서로 락을 획득하도록 설계
   - 데드락 예방

4. **적절한 격리 수준 선택**
   - 애플리케이션 요구사항에 맞는 최소한의 격리 수준 사용
   - 불필요한 락 경합 방지




