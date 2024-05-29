

# 개요
- 종종 개발 및 쿼리를 구현하다 보면, 예상치 못한 락(lock)에 걸리는 상황이 발생하는 경우가 있다. 
- 이 때, 락에 왜 걸리는지 락을 누가 거는지에 대해 알아보도록 하자.

---

# 락이 걸리는 경우
### 1. 트랜잭션 중 데이터 수정
* 쓰기 락(exclusive lock): 한 트랜잭션이 데이터를 수정하려고 할 때 해당 데이터에 락이 걸립니다. 이 락은 다른 트랜잭션이 해당 데이터에 접근하지 못하도록 방지합니다. 예를 들어, UPDATE, INSERT, DELETE 명령어가 실행될 때 발생합니다.
* 읽기 락(shared lock): 여러 트랜잭션이 동시에 데이터를 읽을 수 있도록 허용하지만, 데이터를 수정하려는 트랜잭션은 기다려야 합니다. SELECT 명령어가 실행될 때 발생합니다.


### 2. 데이터베이스 오브젝트 수정
- 테이블 구조를 변경하는 DDL (Data Definition Language) 명령어(ALTER TABLE, DROP TABLE 등)가 실행될 때 락이 걸립니다. 이 경우, 테이블에 대해 일시적으로 독점적인 락이 걸려 다른 트랜잭션이 해당 테이블에 접근하지 못하도록 합니다.
### 3. 데드락
- 두 개 이상의 트랜잭션이 서로가 필요한 자원에 대해 락을 걸고 대기하는 상황입니다. 
- 이는 트랜잭션이 무한히 기다리는 교착 상태를 초래합니다. DBMS는 주기적으로 데드락을 감지하고 이를 해소하기 위해 트랜잭션을 강제 종료합니다.

---

# 락을 누가 거는가?
### DBMS
- 락은 데이터베이스 관리 시스템(DBMS)이 자동으로 관리합니다. 트랜잭션이 시작되고 데이터에 접근할 때, DBMS는 해당 데이터에 대한 락을 설정하고 해제합니다. 사용자는 특정 데이터에 대한 락을 직접 설정하지 않습니다.
### 사용자 정의
- 특정 상황에서는 사용자가 명시적으로 락을 걸 수 있습니다. 예를 들어, SELECT ... FOR UPDATE와 같은 SQL 명령어를 사용하면 특정 행에 대해 명시적으로 락을 걸 수 있습니다.

--- 

## 락의 예시
### 1. Exclusive Lock 예시
```javascript
BEGIN TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE account_id = 1;
-- 이 시점에서 account_id가 1인 행에 대해 Exclusive Lock이 걸림
COMMIT;
```


### 2. Shared Lock 예시
```javascript
BEGIN TRANSACTION;
SELECT balance FROM accounts WHERE account_id = 1;
-- 이 시점에서 account_id가 1인 행에 대해 Shared Lock이 걸림
COMMIT;
```


### 2. Intent Lock 예시
```javascript
BEGIN TRANSACTION;
-- 테이블 수준에서 Intent Exclusive Lock이 설정됨
UPDATE accounts SET balance = balance - 100 WHERE account_id = 1;
-- 특정 행에 대해 Exclusive Lock이 설정됨
COMMIT;
```
---

### 1. 데드락 예시 
```javascript
-- 트랜잭션 1
BEGIN TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE account_id = 1;

-- 트랜잭션 2
BEGIN TRANSACTION;
UPDATE accounts SET balance = balance - 200 WHERE account_id = 2;

-- 트랜잭션 1
UPDATE accounts SET balance = balance - 100 WHERE account_id = 2; -- 대기

-- 트랜잭션 2
UPDATE accounts SET balance = balance - 200 WHERE account_id = 1; -- 대기 (데드락 발생)

```




