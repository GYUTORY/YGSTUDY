---
title: 데이터베이스 락(Lock) 시스템 완벽 가이드
tags: [database, rdbms, lock, concurrency-control, deadlock]
updated: 2025-08-10
---

# 데이터베이스 락(Lock) 시스템

## 배경

데이터베이스에서 락(Lock)은 동시성 제어(Concurrency Control)의 핵심 메커니즘입니다. 여러 트랜잭션이 동시에 데이터에 접근할 때 데이터의 일관성과 무결성을 보장하기 위해 사용됩니다. 락은 데이터베이스 관리 시스템(DBMS)이 자동으로 관리하며, 개발자가 직접 제어할 수도 있습니다.

### 락 시스템의 필요성
- **데이터 일관성**: 동시 접근 시 데이터 무결성 보장
- **트랜잭션 격리**: ACID 속성 중 Isolation 구현
- **동시성 제어**: 여러 사용자의 동시 접근 관리
- **성능 최적화**: 적절한 락 전략으로 성능 향상

### 기본 개념
- **락**: 데이터에 대한 접근을 제어하는 메커니즘
- **트랜잭션**: 데이터베이스의 논리적 작업 단위
- **동시성**: 여러 트랜잭션이 동시에 실행되는 상태
- **격리 수준**: 트랜잭션 간 격리 정도를 정의

## 핵심

### 1. 락의 종류

#### 공유 락(Shared Lock, S-Lock)
공유 락은 데이터를 읽기만 할 때 사용하는 락입니다.

```sql
-- 공유 락이 자동으로 설정됨
SELECT * FROM employees WHERE department = 'IT';
```

**특징**:
- 여러 트랜잭션이 동시에 같은 데이터에 대해 공유 락을 가질 수 있음
- 다른 트랜잭션이 데이터를 수정하는 것을 방지
- SELECT 문이 실행될 때 자동으로 설정됨
- 읽기 전용 작업에 적합

#### 배타 락(Exclusive Lock, X-Lock)
배타 락은 데이터를 수정할 때 사용하는 락입니다.

```sql
-- 배타 락이 자동으로 설정됨
UPDATE employees SET salary = salary * 1.1 WHERE department = 'IT';
```

**특징**:
- 한 트랜잭션만 락을 가질 수 있음
- 다른 트랜잭션의 읽기/쓰기 모두 차단
- UPDATE, INSERT, DELETE 문이 실행될 때 자동으로 설정됨
- 데이터 수정 시 필수

#### 의도 락(Intent Lock)
의도 락은 테이블과 행 수준의 락을 효율적으로 관리하기 위한 락입니다.

**종류**:
- **IS(Intent Shared)**: 테이블의 일부 행에 공유 락을 걸 의도
- **IX(Intent Exclusive)**: 테이블의 일부 행에 배타 락을 걸 의도
- **SIX(Shared with Intent Exclusive)**: 테이블에 공유 락과 일부 행에 배타 락을 걸 의도

```sql
-- 테이블에 IX 락, 특정 행에 X 락이 설정됨
UPDATE employees SET salary = salary * 1.1 WHERE employee_id = 100;
```

### 2. 락의 범위

#### 행 수준 락(Row-Level Lock)
```sql
-- 특정 행에만 락 설정
UPDATE employees SET salary = 50000 WHERE employee_id = 100;
```

**장점**:
- 동시성 향상
- 락 경합 감소
- 세밀한 제어 가능

**단점**:
- 락 관리 오버헤드 증가
- 데드락 가능성 증가

#### 테이블 수준 락(Table-Level Lock)
```sql
-- 전체 테이블에 락 설정
LOCK TABLES employees WRITE;
UPDATE employees SET salary = salary * 1.1;
UNLOCK TABLES;
```

**장점**:
- 락 관리 단순
- 데드락 가능성 낮음

**단점**:
- 동시성 저하
- 성능 병목 가능

#### 페이지 수준 락(Page-Level Lock)
```sql
-- 페이지 단위로 락 설정 (일부 DBMS에서 지원)
-- 데이터베이스 엔진이 자동으로 관리
```

### 3. 락 호환성

#### 락 호환성 매트릭스
| 현재 락 | 요청된 락 | 호환성 |
|---------|-----------|--------|
| **S** | **S** | ✅ 호환 |
| **S** | **X** | ❌ 호환 안됨 |
| **X** | **S** | ❌ 호환 안됨 |
| **X** | **X** | ❌ 호환 안됨 |

#### 락 업그레이드
```sql
-- 공유 락에서 배타 락으로 업그레이드
SELECT * FROM employees WHERE employee_id = 100 FOR UPDATE;
```

## 예시

### 1. 실제 사용 사례

#### 은행 계좌 이체 시스템
```sql
-- 트랜잭션 1: 계좌 A에서 계좌 B로 1000원 이체
BEGIN;
-- 계좌 A에 배타 락 설정
UPDATE accounts SET balance = balance - 1000 WHERE account_id = 'A';
-- 계좌 B에 배타 락 설정
UPDATE accounts SET balance = balance + 1000 WHERE account_id = 'B';
COMMIT;

-- 트랜잭션 2: 계좌 B에서 계좌 C로 500원 이체
BEGIN;
-- 계좌 B에 배타 락 설정 (트랜잭션 1 완료까지 대기)
UPDATE accounts SET balance = balance - 500 WHERE account_id = 'B';
-- 계좌 C에 배타 락 설정
UPDATE accounts SET balance = balance + 500 WHERE account_id = 'C';
COMMIT;
```

#### 재고 관리 시스템
```sql
-- 재고 확인 (공유 락)
SELECT quantity FROM inventory WHERE product_id = 100;

-- 재고 감소 (배타 락)
UPDATE inventory SET quantity = quantity - 1 WHERE product_id = 100 AND quantity > 0;
```

### 2. 고급 패턴

#### 낙관적 락(Optimistic Locking)
```sql
-- 버전 기반 낙관적 락
UPDATE products 
SET name = 'New Product Name', version = version + 1 
WHERE product_id = 100 AND version = 5;

-- 타임스탬프 기반 낙관적 락
UPDATE orders 
SET status = 'shipped', updated_at = NOW() 
WHERE order_id = 1000 AND updated_at = '2023-01-01 10:00:00';
```

#### 명시적 락 설정
```sql
-- MySQL에서 명시적 락 설정
SELECT * FROM employees WHERE department = 'IT' FOR UPDATE;

-- PostgreSQL에서 명시적 락 설정
SELECT * FROM employees WHERE department = 'IT' FOR UPDATE NOWAIT;

-- SQL Server에서 명시적 락 설정
SELECT * FROM employees WITH (UPDLOCK) WHERE department = 'IT';
```

## 운영 팁

### 성능 최적화

#### 락 경합 최소화
```sql
-- 락 획득 순서 표준화
-- 항상 account_id 순서로 락 획득
UPDATE accounts SET balance = balance - 100 WHERE account_id = 'A';
UPDATE accounts SET balance = balance + 100 WHERE account_id = 'B';

-- 인덱스 활용으로 락 범위 최소화
CREATE INDEX idx_employee_department ON employees(department);
UPDATE employees SET salary = salary * 1.1 WHERE department = 'IT';
```

#### 배치 처리 활용
```sql
-- 대량 업데이트 시 배치 처리
UPDATE employees 
SET salary = CASE 
    WHEN department = 'IT' THEN salary * 1.1
    WHEN department = 'HR' THEN salary * 1.05
    ELSE salary
END
WHERE department IN ('IT', 'HR');
```

### 에러 처리

#### 데드락 감지 및 해결
```sql
-- MySQL 데드락 정보 확인
SHOW ENGINE INNODB STATUS;

-- PostgreSQL 데드락 정보 확인
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- 데드락 타임아웃 설정
SET innodb_lock_wait_timeout = 50;
```

#### 락 타임아웃 설정
```sql
-- MySQL 락 타임아웃 설정
SET innodb_lock_wait_timeout = 30;

-- PostgreSQL 락 타임아웃 설정
SET lock_timeout = '30s';

-- SQL Server 락 타임아웃 설정
SET LOCK_TIMEOUT 30000;
```

### 주의사항

#### 데드락 방지
```sql
-- 락 획득 순서 일관성 유지
-- 항상 작은 ID부터 큰 ID 순서로 락 획득
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE account_id = 1;
UPDATE accounts SET balance = balance + 100 WHERE account_id = 2;
COMMIT;

-- 트랜잭션 크기 최소화
BEGIN;
-- 필요한 작업만 수행
UPDATE critical_table SET status = 'processing' WHERE id = 100;
-- 다른 작업은 별도 트랜잭션으로 분리
COMMIT;
```

## 참고

### 락 모니터링

#### MySQL 락 모니터링
```sql
-- 현재 락 상태 확인
SHOW PROCESSLIST;
SHOW ENGINE INNODB STATUS;

-- 락 대기 정보 확인
SELECT * FROM information_schema.INNODB_LOCKS;
SELECT * FROM information_schema.INNODB_LOCK_WAITS;
```

#### PostgreSQL 락 모니터링
```sql
-- 현재 락 상태 확인
SELECT * FROM pg_locks;
SELECT * FROM pg_stat_activity;

-- 락 대기 정보 확인
SELECT 
    l.pid,
    l.mode,
    l.granted,
    a.query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid;
```

### 락 전략 비교

| 전략 | 장점 | 단점 | 사용 시기 |
|------|------|------|-----------|
| **비관적 락** | 데이터 일관성 보장 | 동시성 저하 | 높은 일관성 요구 |
| **낙관적 락** | 동시성 향상 | 충돌 시 재시도 필요 | 낮은 충돌 가능성 |
| **행 수준 락** | 세밀한 제어 | 오버헤드 증가 | 세밀한 동시성 제어 |
| **테이블 수준 락** | 단순한 관리 | 동시성 저하 | 대량 데이터 처리 |

### 결론
데이터베이스 락은 동시성 제어의 핵심 메커니즘입니다.
적절한 락 전략을 선택하여 성능과 일관성의 균형을 맞추세요.
데드락을 방지하기 위해 락 획득 순서를 일관되게 유지하세요.
락 모니터링을 통해 성능 병목을 사전에 감지하고 해결하세요.













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

