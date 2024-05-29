
# 개요
- [Lock](Lock.md) 에 이어서, 일반적으로 SELECT에서는 락이 안걸리는 것으로 알고있다.
- 그러면, 어느 상황에 SELECT에서 Lock 걸리는 상황이 발생하는지 알아보자. 

---

## SELECT 문에서 락이 걸리는 경우

### 1. SELECT ... FOR UPDATE 
- 이 명령어는 선택된 행들에 대해 쓰기 락(exclusive lock)을 걸어서 다른 트랜잭션이 해당 행을 수정하지 못하도록 합니다. 
- 주로 트랜잭션의 일관성을 유지하기 위해 사용됩니다. 

```sql
BEGIN TRANSACTION;
SELECT balance FROM accounts WHERE account_id = 1 FOR UPDATE;
-- 이 시점에서 account_id가 1인 행에 대해 Exclusive Lock이 걸림
```

### 2. SELECT ... FOR SHARE (또는 SELECT ... LOCK IN SHARE MODE)
- 이 명령어는 선택된 행들에 대해 읽기 락(shared lock)을 걸어서 다른 트랜잭션이 해당 행을 수정하지 못하게 합니다. 
- 여러 트랜잭션이 동시에 데이터를 읽을 수 있지만, 쓰기 작업은 불가능하게 만듭니다.

```sql
BEGIN TRANSACTION;
SELECT balance FROM accounts WHERE account_id = 1 FOR SHARE;
-- 이 시점에서 account_id가 1인 행에 대해 Shared Lock이 걸림
```

---> 이어서 작성 