---
title: SELECT Lock
tags: [database, rdbms, select-lock]
updated: 2025-08-10
---

## 배경
- [Lock](Lock.md) 에 이어서, 일반적으로 SELECT에서는 락이 안걸리는 것으로 알고있다.
- 그러나 실제로는 다양한 상황에서 SELECT 문에서도 락이 발생할 수 있으며, 이는 데이터베이스의 일관성과 동시성 제어에 중요한 역할을 한다.
- 본 문서에서는 SELECT 문에서 락이 발생하는 다양한 상황과 그에 따른 영향, 그리고 최적의 사용 방법에 대해 자세히 알아본다.

---

1. **명시적 커밋**
```sql
BEGIN;
-- 트랜잭션 작업 수행
COMMIT; -- 모든 락 해제
```

2. **롤백**
```sql
BEGIN;
-- 트랜잭션 작업 수행
ROLLBACK; -- 모든 락 해제
```

3. **세션 종료**
- 세션이 종료되면 모든 락이 자동으로 해제됨

1. **트랜잭션 최적화**
   - 트랜잭션을 최대한 짧게 유지
   - 불필요한 락 사용 피하기
   - 적절한 격리 수준 선택

2. **인덱스 최적화**
```sql
-- 적절한 인덱스 생성
CREATE INDEX idx_department ON employees(department);
CREATE INDEX idx_product_category ON products(category);
```

3. **락 타임아웃 설정**
```sql
-- 락 대기 시간 설정
SET innodb_lock_wait_timeout = 30;
```

4. **배치 처리 최적화**
```sql
-- 대량 업데이트 시 배치 처리
UPDATE employees 
SET salary = salary * 1.1 
WHERE department = 'IT' 
LIMIT 1000;
```

---






1. **명시적 커밋**
```sql
BEGIN;
-- 트랜잭션 작업 수행
COMMIT; -- 모든 락 해제
```

2. **롤백**
```sql
BEGIN;
-- 트랜잭션 작업 수행
ROLLBACK; -- 모든 락 해제
```

3. **세션 종료**
- 세션이 종료되면 모든 락이 자동으로 해제됨

1. **트랜잭션 최적화**
   - 트랜잭션을 최대한 짧게 유지
   - 불필요한 락 사용 피하기
   - 적절한 격리 수준 선택

2. **인덱스 최적화**
```sql
-- 적절한 인덱스 생성
CREATE INDEX idx_department ON employees(department);
CREATE INDEX idx_product_category ON products(category);
```

3. **락 타임아웃 설정**
```sql
-- 락 대기 시간 설정
SET innodb_lock_wait_timeout = 30;
```

4. **배치 처리 최적화**
```sql
-- 대량 업데이트 시 배치 처리
UPDATE employees 
SET salary = salary * 1.1 
WHERE department = 'IT' 
LIMIT 1000;
```

---






- [Lock](Lock.md) 에 이어서, 일반적으로 SELECT에서는 락이 안걸리는 것으로 알고있다.
- 그러나 실제로는 다양한 상황에서 SELECT 문에서도 락이 발생할 수 있으며, 이는 데이터베이스의 일관성과 동시성 제어에 중요한 역할을 한다.
- 본 문서에서는 SELECT 문에서 락이 발생하는 다양한 상황과 그에 따른 영향, 그리고 최적의 사용 방법에 대해 자세히 알아본다.

---

## SELECT 문에서 락이 걸리는 경우

## 1. SELECT 문에서 락이 발생하는 경우
### 📌 1.1 `SELECT ... FOR UPDATE`
- **행 레벨 락(Row-Level Lock)**을 발생시킴.
- 데이터 조회와 동시에 **해당 데이터의 수정을 위해 잠금**.
- 다른 트랜잭션에서 해당 행을 읽거나 수정하는 것을 차단.

```sql
-- 기본 사용법
SELECT * FROM employees 
WHERE department = 'IT' 
FOR UPDATE;

-- 특정 컬럼만 선택하여 락
SELECT employee_id, salary FROM employees 
WHERE department = 'IT' 
FOR UPDATE;

-- NOWAIT 옵션 사용 (락 획득 실패 시 즉시 에러 반환)
SELECT * FROM employees 
WHERE department = 'IT' 
FOR UPDATE NOWAIT;

-- SKIP LOCKED 옵션 사용 (락이 걸린 행은 건너뛰기)
SELECT * FROM employees 
WHERE department = 'IT' 
FOR UPDATE SKIP LOCKED;
```

**사용 사례:**
1. **급여 조정 시스템**
```sql
BEGIN;
-- 특정 부서의 직원 급여 조회 및 잠금
SELECT * FROM employees 
WHERE department = 'IT' 
FOR UPDATE;

-- 급여 인상 처리
UPDATE employees 
SET salary = salary * 1.1 
WHERE department = 'IT';

COMMIT;
```

2. **재고 관리 시스템**
```sql
BEGIN;
-- 특정 상품의 재고 확인 및 잠금
SELECT * FROM inventory 
WHERE product_id = 123 
FOR UPDATE;

-- 재고 감소 처리
UPDATE inventory 
SET quantity = quantity - 1 
WHERE product_id = 123;

COMMIT;
```

**주의사항:**
- FOR UPDATE는 성능에 영향을 줄 수 있으므로 필요한 경우에만 사용
- 데드락 발생 가능성이 있으므로 락 획득 순서에 주의
- 트랜잭션을 최대한 짧게 유지

---

### 📌 1.2 `SELECT ... LOCK IN SHARE MODE`
- **공유 락(Shared Lock)** 발생.
- 다른 트랜잭션에서 **읽기만 가능**하고, 쓰기는 불가능.
- 여러 트랜잭션이 동시에 공유 락을 가질 수 있음.

```sql
-- 기본 사용법
SELECT * FROM products 
WHERE category = 'Electronics' 
LOCK IN SHARE MODE;

-- 특정 컬럼만 선택하여 락
SELECT product_id, price FROM products 
WHERE category = 'Electronics' 
LOCK IN SHARE MODE;
```

**사용 사례:**
1. **상품 정보 조회 시스템**
```sql
BEGIN;
-- 상품 정보 조회 및 공유 락
SELECT * FROM products 
WHERE product_id = 456 
LOCK IN SHARE MODE;

-- 상품 정보 표시
-- 다른 트랜잭션에서도 동시에 읽기 가능
COMMIT;
```

2. **데이터 분석 시스템**
```sql
BEGIN;
-- 특정 기간의 주문 데이터 조회
SELECT * FROM orders 
WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31'
LOCK IN SHARE MODE;

-- 데이터 분석 수행
-- 다른 트랜잭션에서도 동시에 읽기 가능
COMMIT;
```

**주의사항:**
- 공유 락은 배타적 락과 충돌할 수 있음
- 너무 많은 공유 락은 성능 저하를 일으킬 수 있음
- 필요한 경우에만 사용하고 트랜잭션을 짧게 유지

---

### 📌 1.3 `SELECT` 문과 트랜잭션 격리 수준
**트랜잭션 격리 수준(Isolation Level)**에 따라 락의 발생 여부와 동작이 달라집니다.

| **격리 수준**            | **특징**                          | **락 발생 가능성**      | **동시성** | **일관성** |
|--------------------------|---------------------------------|------------------------|------------|------------|
| READ UNCOMMITTED         | 커밋되지 않은 데이터 읽기 허용       | 거의 없음              | 매우 높음  | 매우 낮음  |
| READ COMMITTED           | 커밋된 데이터만 읽기 가능          | 낮음                   | 높음       | 낮음       |
| REPEATABLE READ          | 동일 트랜잭션 내에서 일관된 데이터  | 중간                   | 중간       | 중간       |
| SERIALIZABLE             | 가장 높은 일관성, 모든 접근 차단   | 높음                   | 낮음       | 매우 높음  |

**격리 수준 설정 예제:**
```sql
-- 세션 레벨 설정
SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- 트랜잭션 레벨 설정
START TRANSACTION;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT * FROM orders;
COMMIT;
```

**각 격리 수준별 특징:**
1. **READ UNCOMMITTED**
   - Dirty Read 가능
   - Non-repeatable Read 가능
   - Phantom Read 가능
   - 성능은 가장 좋지만 일관성 보장이 가장 낮음

2. **READ COMMITTED**
   - Dirty Read 방지
   - Non-repeatable Read 가능
   - Phantom Read 가능
   - 대부분의 DBMS의 기본 격리 수준

3. **REPEATABLE READ**
   - Dirty Read 방지
   - Non-repeatable Read 방지
   - Phantom Read 가능
   - MySQL의 기본 격리 수준

4. **SERIALIZABLE**
   - Dirty Read 방지
   - Non-repeatable Read 방지
   - Phantom Read 방지
   - 가장 높은 일관성 보장

---

## 2. 락 관련 예제 🧑‍💻

### ✅ 2.1 SELECT FOR UPDATE 사용 예제
```sql
-- 계좌 이체 시스템
BEGIN;

-- 출금 계좌 잠금
SELECT * FROM accounts 
WHERE account_id = 1 
FOR UPDATE;

-- 입금 계좌 잠금
SELECT * FROM accounts 
WHERE account_id = 2 
FOR UPDATE;

-- 출금 처리
UPDATE accounts 
SET balance = balance - 100 
WHERE account_id = 1;

-- 입금 처리
UPDATE accounts 
SET balance = balance + 100 
WHERE account_id = 2;

COMMIT;
```

**주의사항:**
- 계좌 잠금 순서를 일관되게 유지하여 데드락 방지
- 트랜잭션을 최대한 짧게 유지
- 에러 발생 시 롤백 처리

---

### ✅ 2.2 SELECT LOCK IN SHARE MODE 사용 예제
```sql
-- 상품 가격 조회 및 수정 시스템
BEGIN;

-- 상품 정보 조회 및 공유 락
SELECT * FROM products 
WHERE product_id = 1 
LOCK IN SHARE MODE;

-- 가격 수정을 위한 배타적 락
SELECT * FROM products 
WHERE product_id = 1 
FOR UPDATE;

-- 가격 수정
UPDATE products 
SET price = price + 10 
WHERE product_id = 1;

COMMIT;
```

**주의사항:**
- 공유 락에서 배타적 락으로의 전환 시 주의
- 트랜잭션 격리 수준에 따른 동작 차이 확인
- 락 획득 실패 시 적절한 에러 처리

---

### ✅ 2.3 데드락(Deadlock) 예제와 해결방법
```sql
-- 데드락 발생 시나리오
-- 세션 1
BEGIN;
SELECT * FROM orders WHERE order_id = 1 FOR UPDATE;

-- 세션 2
BEGIN;
SELECT * FROM orders WHERE order_id = 2 FOR UPDATE;

-- 세션 1 (데드락 발생)
UPDATE orders SET status = 'Shipped' WHERE order_id = 2;

-- 세션 2 (데드락 발생)
UPDATE orders SET status = 'Shipped' WHERE order_id = 1;
```

**데드락 방지 방법:**
1. **락 획득 순서 통일**
```sql
-- 올바른 락 획득 순서
BEGIN;
-- 항상 작은 ID부터 락 획득
SELECT * FROM orders WHERE order_id = 1 FOR UPDATE;
SELECT * FROM orders WHERE order_id = 2 FOR UPDATE;
```

2. **타임아웃 설정**
```sql
-- 타임아웃 설정
SET innodb_lock_wait_timeout = 50; -- 50초
```

3. **NOWAIT 옵션 사용**
```sql
SELECT * FROM orders 
WHERE order_id = 1 
FOR UPDATE NOWAIT;
```

4. **SKIP LOCKED 옵션 사용**
```sql
SELECT * FROM orders 
WHERE order_id = 1 
FOR UPDATE SKIP LOCKED;
```

---

## 3. 락 해제와 방지 🛡️
## 4. SELECT 락의 장단점
| **구분**             | **장점**                          | **단점**                        | **사용 시나리오**                |
|----------------------|---------------------------------|---------------------------------|----------------------------------|
| **FOR UPDATE**       | 데이터 일관성 유지, 경합 방지      | 동시성 저하                    | 계좌 이체, 재고 관리             |
| **LOCK IN SHARE MODE** | 읽기 가능, 수정 제한            | 업데이트 충돌 가능성 존재      | 데이터 조회, 보고서 생성         |
| **SERIALIZABLE**     | 최대 일관성 보장                  | 성능 저하, 데드락 발생 위험     | 금융 거래, 정확성 요구 시스템    |

---

## 5. 결론 ✅
1. **SELECT 문도 특정 상황에서 락을 발생시킬 수 있으며, 이는 데이터베이스의 일관성과 동시성 제어에 중요합니다.**
2. **트랜잭션 격리 수준과 명시적인 FOR UPDATE 사용 시 주의해야 합니다.**
3. **데드락 방지 및 성능 최적화를 위해 적절한 트랜잭션 설계가 중요합니다.**
4. **실제 시스템에서는 다음과 같은 원칙을 지켜야 합니다:**
   - 필요한 경우에만 락 사용
   - 트랜잭션을 최대한 짧게 유지
   - 적절한 격리 수준 선택
   - 인덱스 최적화
   - 락 획득 순서 통일
   - 타임아웃 설정
   - 에러 처리 구현

