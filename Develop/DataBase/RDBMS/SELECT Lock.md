
# 개요
- [Lock](Lock.md) 에 이어서, 일반적으로 SELECT에서는 락이 안걸리는 것으로 알고있다.
- 그러면, 어느 상황에 SELECT에서 Lock 걸리는 상황이 발생하는지 알아보자. 

---

## SELECT 문에서 락이 걸리는 경우

## 1. SELECT 문에서 락이 발생하는 경우
### 📌 1.1 `SELECT ... FOR UPDATE`
- **행 레벨 락(Row-Level Lock)**을 발생시킴.
- 데이터 조회와 동시에 **해당 데이터의 수정을 위해 잠금**.

```sql
SELECT * FROM employees 
WHERE department = 'IT' 
FOR UPDATE;
```

**사용 사례:**
- 급여를 조정하는 동안 해당 직원의 정보가 변경되지 않도록 보호.

---

### 📌 1.2 `SELECT ... LOCK IN SHARE MODE`
- **공유 락(Shared Lock)** 발생.
- 다른 트랜잭션에서 **읽기만 가능**하고, 쓰기는 불가능.

```sql
SELECT * FROM products 
WHERE category = 'Electronics' 
LOCK IN SHARE MODE;
```

**사용 사례:**
- 상품 정보를 조회하는 동안 다른 사용자가 데이터를 변경하지 못하게 방지.

---

### 📌 1.3 `SELECT` 문과 트랜잭션 격리 수준
**트랜잭션 격리 수준(Isolation Level)**에 따라 락의 발생 여부가 달라집니다.

| **격리 수준**            | **특징**                          | **락 발생 가능성**      |
|--------------------------|---------------------------------|------------------------|
| READ UNCOMMITTED         | 커밋되지 않은 데이터 읽기 허용       | 거의 없음              |
| READ COMMITTED           | 커밋된 데이터만 읽기 가능          | 낮음                   |
| REPEATABLE READ          | 동일 트랜잭션 내에서 일관된 데이터  | 중간 (공유락 발생 가능)|
| SERIALIZABLE             | 가장 높은 일관성, 모든 접근 차단   | 높음 (락 발생 가능)   |

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT * FROM orders;
```

---

## 2. 락 관련 예제 🧑‍💻

### ✅ 4.1 SELECT FOR UPDATE 사용 예제
```sql
BEGIN;

SELECT * FROM accounts 
WHERE account_id = 1 
FOR UPDATE;

UPDATE accounts 
SET balance = balance - 100 
WHERE account_id = 1;

COMMIT;
```

- 트랜잭션이 완료될 때까지 **다른 사용자는 해당 계좌 데이터를 수정할 수 없음**.

---

### ✅ 2.2 SELECT LOCK IN SHARE MODE 사용 예제
```sql
BEGIN;

SELECT * FROM products 
WHERE product_id = 1 
LOCK IN SHARE MODE;

UPDATE products 
SET price = price + 10 
WHERE product_id = 1;

COMMIT;
```

- **다른 사용자는 읽기 가능**하지만 **데이터 수정은 불가능**.

---

### ✅ 2.3 데드락(Deadlock) 예제
```sql
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

- **데드락(Deadlock)**: 두 트랜잭션이 서로가 가진 자원을 기다리며 무한 대기.

---

## 3. 락 해제와 방지 🛡️
### 🔓 락 해제 방법
- **명시적으로 커밋 (COMMIT)**: 트랜잭션을 완료하면 락 해제.
- **롤백 (ROLLBACK)**: 트랜잭션 취소 시 락 해제.

### 🛡️ 락 방지 모범 사례
- **최소한의 트랜잭션 사용**: 트랜잭션을 짧게 유지.
- **적절한 격리 수준 선택**: READ COMMITTED 사용 추천.
- **적절한 인덱스 구성**: 인덱스 활용으로 데이터 접근 최소화.

---

## 4. SELECT 락의 장단점
| **구분**             | **장점**                          | **단점**                        |
|----------------------|---------------------------------|---------------------------------|
| **FOR UPDATE**       | 데이터 일관성 유지, 경합 방지      | 동시성 저하                    |
| **LOCK IN SHARE MODE** | 읽기 가능, 수정 제한            | 업데이트 충돌 가능성 존재      |
| **SERIALIZABLE**     | 최대 일관성 보장                  | 성능 저하, 데드락 발생 위험     |

---

## 5. 결론 ✅
- **SELECT 문도 특정 상황에서 락을 발생시킬 수 있습니다.**
- **트랜잭션 격리 수준**과 **명시적인 FOR UPDATE** 사용 시 주의해야 합니다.
- **데드락 방지 및 성능 최적화**를 위해 **적절한 트랜잭션 설계**가 중요합니다.
