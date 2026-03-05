---
title: 교착 상태 (Deadlock) 가이드
tags: [os, deadlock, synchronization, mutex, resource-allocation, concurrency]
updated: 2026-03-01
---

# 교착 상태 (Deadlock)

## 개요

교착 상태(Deadlock)는 둘 이상의 프로세스가 서로가 점유한 자원을 기다리며 **무한히 대기하는 상태**이다. 어떤 프로세스도 진행할 수 없고, 외부 개입 없이는 해결되지 않는다.

```
P1: "A 잠금 획득 → B 잠금 대기 중..."
P2: "B 잠금 획득 → A 잠금 대기 중..."

→ 서로 상대가 놓아줄 때까지 무한 대기 = Deadlock
```

### 일상 비유

```
교차로 교착 상태:

       ↓ 차2
  ─────┼─────
차1 →  │  ← 차3
  ─────┼─────
       ↑ 차4

네 대의 차가 동시에 교차로에 진입
→ 모두 앞차가 빠질 때까지 대기
→ 아무도 움직이지 못함
```

## 핵심

### 1. 교착 상태의 4가지 조건

Deadlock이 발생하려면 4가지 조건이 **모두 동시에** 성립해야 한다 (Coffman 조건).

| 조건 | 설명 | 비유 |
|------|------|------|
| **상호 배제 (Mutual Exclusion)** | 자원은 한 번에 하나의 프로세스만 사용 | 화장실 칸은 한 명만 사용 |
| **점유 대기 (Hold and Wait)** | 자원을 점유한 채 다른 자원을 대기 | 포크 하나 들고 다른 포크 기다림 |
| **비선점 (No Preemption)** | 다른 프로세스의 자원을 강제로 뺏을 수 없음 | 남의 포크를 빼앗을 수 없음 |
| **순환 대기 (Circular Wait)** | 프로세스 간 순환 형태의 대기 관계 | A→B→C→A 순환 |

```
하나라도 깨지면 Deadlock은 발생하지 않는다.
```

### 2. 자원 할당 그래프

프로세스-자원 관계를 그래프로 표현하여 Deadlock을 시각적으로 판별한다.

```
Deadlock 있음 (순환 존재):
  P1 ──요청──▶ R1 ──할당──▶ P2
  ▲                         │
  │                         │
  └──할당── R2 ◀──요청──────┘

  P1 → R1 → P2 → R2 → P1 (순환!)


Deadlock 없음 (순환 없음):
  P1 ──요청──▶ R1 ──할당──▶ P2
                            │
  P3 ◀──할당── R2 ◀──요청───┘

  P2 → R2 → P3 (P3가 종료하면 R2 해제 → P2 진행)
```

### 3. Deadlock 해결 전략

#### 전략 비교

| 전략 | 접근 | 오버헤드 | 자원 이용률 |
|------|------|---------|-----------|
| **예방 (Prevention)** | 4가지 조건 중 하나를 원천 차단 | 높음 | 낮음 |
| **회피 (Avoidance)** | 안전 상태만 허용 (Banker's) | 중간 | 중간 |
| **탐지 & 복구 (Detection)** | 발생 후 탐지하여 처리 | 낮음 (평시) | 높음 |
| **무시 (Ostrich)** | 무시 (발생 확률 낮을 때) | 없음 | 높음 |

### 4. Deadlock 예방 (Prevention)

4가지 조건 중 하나를 **구조적으로 불가능**하게 만든다.

#### 상호 배제 제거

읽기 전용 자원은 공유 가능하게 한다. 하지만 프린터, 쓰기 잠금 등은 상호 배제가 필수이므로 제한적이다.

#### 점유 대기 제거

```
방법 1: 필요한 자원을 한 번에 모두 요청
  P1: lock(A, B)     ← 둘 다 가능할 때만 획득
  P2: lock(A, B)     ← P1이 끝날 때까지 대기 (Deadlock 불가)

방법 2: 자원 요청 전 점유 자원을 모두 해제
  P1: lock(A) → 작업 → unlock(A) → lock(B) → 작업 → unlock(B)
```

| 장점 | 단점 |
|------|------|
| Deadlock 원천 차단 | 자원 이용률 저하 (사용하지 않는 자원도 점유) |
| | 기아 현상 가능 |

#### 비선점 제거 (자원 강제 회수)

```
P1이 A를 점유하고 B를 요청했는데 B가 불가능하면:
  → P1의 A를 강제 해제
  → P1은 A와 B를 모두 다시 요청
```

CPU 레지스터, 메모리 등은 선점 가능하지만, 프린터, 파일 잠금 등은 선점이 어렵다.

#### 순환 대기 제거 (자원 순서 지정)

**가장 실용적인 예방 방법**. 모든 자원에 번호를 매기고, **오름차순으로만 요청**하도록 강제한다.

```
자원 순서: A=1, B=2, C=3

✅ 올바른 순서:
  P1: lock(A) → lock(B)     (1 → 2)
  P2: lock(A) → lock(B)     (1 → 2)
  → 순환 불가, Deadlock 없음

❌ 잘못된 순서:
  P1: lock(B) → lock(A)     (2 → 1, 순서 위반!)
```

```java
// Java에서 순서 기반 Deadlock 예방
public void transfer(Account from, Account to, int amount) {
    // 계좌 ID 순서로 잠금 → 순환 대기 방지
    Account first = from.getId() < to.getId() ? from : to;
    Account second = from.getId() < to.getId() ? to : from;

    synchronized (first) {
        synchronized (second) {
            from.withdraw(amount);
            to.deposit(amount);
        }
    }
}
```

### 5. Deadlock 회피 (Avoidance)

자원 할당 전에 **안전한지 검사**한 후, 안전하면 할당, 불안전하면 거부한다.

#### 안전 상태 (Safe State)

```
안전 상태: 모든 프로세스가 자원을 할당받아 완료할 수 있는 순서가 존재
불안전 상태: 그런 순서가 존재하지 않음 (Deadlock 가능성)

안전 상태 ⊂ Deadlock 없음
불안전 상태 ⊃ Deadlock (불안전해도 반드시 Deadlock은 아님)
```

#### Banker's Algorithm (은행원 알고리즘)

은행이 대출할 때 모든 고객이 최대 대출을 받아도 파산하지 않는지 확인하는 것과 같다.

```
자원 총량: 12개

프로세스  최대 필요  현재 할당  추가 필요
  P1        10         5         5
  P2         4         2         2
  P3         9         2         7

가용 자원: 12 - (5+2+2) = 3개

안전 순서 찾기:
  1. P2에 2개 할당 가능 (3 ≥ 2) → P2 완료 → 가용 = 3+2 = 5
  2. P1에 5개 할당 가능 (5 ≥ 5) → P1 완료 → 가용 = 5+5 = 10
  3. P3에 7개 할당 가능 (10 ≥ 7) → P3 완료

안전 순서: <P2, P1, P3> 존재 → 안전 상태 ✅
```

```
만약 P1이 1개를 추가 요청하면?

가용: 3 → 2 (P1에 1개 할당)
  P2: 2개 필요, 가용 2개 → 가능 → 완료 후 가용 4개
  P1: 4개 필요, 가용 4개 → 가능 → 완료 후 가용 10개
  P3: 7개 필요, 가용 10개 → 가능

→ 안전 → 요청 승인 ✅
```

### 6. Deadlock 탐지 & 복구

Deadlock을 허용하되, 주기적으로 탐지하여 해결한다.

#### 탐지 (Detection)

**Wait-for Graph**: 프로세스 간 대기 관계 그래프에서 **사이클**이 있으면 Deadlock.

```
P1 → P2 → P3 → P1  (사이클 존재 = Deadlock!)
```

#### 복구 (Recovery)

| 방법 | 설명 | 부작용 |
|------|------|--------|
| **프로세스 종료** | Deadlock 프로세스 중 하나 종료 | 작업 손실 |
| **자원 선점** | 프로세스의 자원을 강제 회수 | 상태 롤백 필요 |
| **체크포인트/롤백** | 이전 안전 상태로 되돌림 | 오버헤드 |

```
종료 대상 선택 기준:
  - 우선순위가 낮은 프로세스
  - 실행 시간이 짧은 프로세스 (손실 최소화)
  - 사용 자원이 적은 프로세스
  - 완료까지 남은 작업이 많은 프로세스
```

### 7. 실무에서의 Deadlock

#### 데이터베이스 Deadlock

```sql
-- 트랜잭션 1
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- Row 1 잠금
UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- Row 2 대기...

-- 트랜잭션 2 (동시 실행)
BEGIN;
UPDATE accounts SET balance = balance - 50 WHERE id = 2;   -- Row 2 잠금
UPDATE accounts SET balance = balance + 50 WHERE id = 1;   -- Row 1 대기...

-- → Deadlock! DB가 자동 탐지 후 하나를 롤백
```

**해결**: 항상 같은 순서로 행을 잠근다 (예: ID 오름차순).

```sql
-- 항상 ID가 작은 행을 먼저 잠금
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- 먼저
UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- 나중
COMMIT;
```

#### Java에서의 Deadlock

```java
// ❌ Deadlock 가능
public void method1() {
    synchronized (lockA) {
        synchronized (lockB) { /* 작업 */ }
    }
}

public void method2() {
    synchronized (lockB) {   // 순서 반대!
        synchronized (lockA) { /* 작업 */ }
    }
}

// ✅ tryLock으로 Deadlock 회피
public void safeMethod() {
    while (true) {
        if (lockA.tryLock(100, TimeUnit.MILLISECONDS)) {
            try {
                if (lockB.tryLock(100, TimeUnit.MILLISECONDS)) {
                    try {
                        // 작업 수행
                        return;
                    } finally {
                        lockB.unlock();
                    }
                }
            } finally {
                lockA.unlock();
            }
        }
        Thread.sleep(50);  // 잠시 대기 후 재시도
    }
}
```

#### Deadlock 탐지 도구

```bash
# Java: 스레드 덤프로 Deadlock 확인
jstack <PID>
# 출력에 "Found one Java-level deadlock" 표시

# MySQL: Deadlock 로그 확인
SHOW ENGINE INNODB STATUS;
# LATEST DETECTED DEADLOCK 섹션 확인

# PostgreSQL
SELECT * FROM pg_locks WHERE NOT granted;
```

### 8. 현대 OS의 Deadlock 대응

| OS | 전략 |
|----|------|
| **Linux** | 대부분 무시 (Ostrich). 커널 내부는 순서 기반 잠금으로 예방 |
| **Windows** | 무시 + 타임아웃 기반 탐지 |
| **Database** | 자동 탐지 + 롤백 (Wait-for Graph) |
| **Java** | `tryLock` 타임아웃 + `jstack` 덤프 분석 |

## 참고

- [Operating System Concepts (공룡책)](https://www.os-book.com/) — Chapter 8: Deadlocks
- [프로세스 & 스레드](Process & Thread/Process & Thread.md) — 프로세스 기본 개념
- [레이스 컨디션](Process & Thread/레이스_컨디션.md) — 동기화 문제
- [CPU 스케줄링](CPU_Scheduling.md) — 프로세스 스케줄링
