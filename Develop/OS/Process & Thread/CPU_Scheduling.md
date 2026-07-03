---
title: CPU 스케줄링
tags:
  - OS
  - CPU Scheduling
  - Process
  - Linux
updated: 2026-03-31
---

# CPU 스케줄링

## CPU 스케줄링이란

프로세스가 여러 개 있을 때, CPU를 누구에게 먼저 줄 것인지 결정하는 메커니즘이다. 단일 코어 기준으로, CPU는 한 번에 하나의 프로세스만 실행할 수 있다. Ready Queue에 대기 중인 프로세스 중 하나를 골라서 CPU를 할당하는 것이 스케줄러의 역할이다.

스케줄링 성능을 평가할 때 주로 보는 지표:

- **CPU Utilization**: CPU가 놀지 않고 일하는 비율
- **Throughput**: 단위 시간당 완료된 프로세스 수
- **Turnaround Time**: 프로세스가 제출된 시점부터 완료까지 걸린 총 시간
- **Waiting Time**: Ready Queue에서 대기한 시간의 합
- **Response Time**: 요청 후 첫 번째 응답이 나올 때까지 걸린 시간

서버 환경에서는 Response Time이 가장 중요하다. 사용자 요청에 대한 첫 응답이 늦으면 타임아웃이 걸리기 때문이다.

---

## 선점(Preemptive) vs 비선점(Non-preemptive)

**비선점**: 프로세스가 CPU를 잡으면 스스로 반납할 때까지 뺏을 수 없다. 구현이 단순하지만, 하나가 오래 걸리면 뒤에 있는 프로세스는 계속 기다린다.

**선점**: OS가 실행 중인 프로세스에서 CPU를 강제로 회수할 수 있다. 현대 OS는 전부 선점형이다. 비선점이면 하나의 프로세스가 무한 루프에 빠졌을 때 시스템 전체가 먹통이 된다.

선점형에서는 Context Switch 비용이 발생한다. 레지스터 저장/복원, TLB flush, 캐시 미스 등이 생기기 때문에 너무 자주 선점하면 오히려 성능이 떨어진다.

---

## 스케줄링 알고리즘

### FCFS (First-Come, First-Served)

먼저 온 프로세스가 먼저 실행된다. 비선점형이다.

```
도착 순서: P1(24ms) → P2(3ms) → P3(3ms)

|---- P1(24ms) ----|-- P2(3ms) --|-- P3(3ms) --|
0                  24            27            30

평균 대기 시간: (0 + 24 + 27) / 3 = 17ms
```

문제는 **Convoy Effect**다. CPU burst가 긴 프로세스가 앞에 오면, 뒤에 있는 짧은 작업들이 전부 대기한다. 위 예시에서 P2, P3는 3ms짜리 작업인데 P1 때문에 24ms 이상 기다린다.

실무에서 이런 현상을 보는 경우가 있다. DB 커넥션 풀에서 하나의 슬로우 쿼리가 커넥션을 오래 점유하면, 뒤에 대기 중인 빠른 쿼리들까지 전부 지연되는 상황이 이것과 같은 구조다.

### SJF (Shortest Job First)

CPU burst가 가장 짧은 프로세스를 먼저 실행한다. 평균 대기 시간이 이론적으로 최소가 되는 알고리즘이다.

```
프로세스: P1(6ms), P2(8ms), P3(7ms), P4(3ms)

SJF 순서: P4(3ms) → P1(6ms) → P3(7ms) → P2(8ms)

|-- P4 --|---- P1 ----|------ P3 ------|-------- P2 --------|
0        3            9               16                    24

평균 대기 시간: (3 + 16 + 9 + 0) / 4 = 7ms
```

문제는 CPU burst 시간을 미리 알 수 없다는 것이다. 실제로는 과거 실행 시간을 기반으로 예측하는데, 정확하지 않다. 그리고 **Starvation** 문제가 있다. CPU burst가 긴 프로세스는 짧은 프로세스가 계속 들어오면 영원히 실행되지 못할 수 있다.

### SRTF (Shortest Remaining Time First)

SJF의 선점형 버전이다. 새 프로세스가 도착했을 때 남은 시간이 더 짧으면 현재 실행 중인 프로세스를 선점한다.

```
시간 0: P1(7ms) 도착 → P1 실행
시간 2: P2(4ms) 도착 → P2가 P1 선점 (P2 남은 4ms < P1 남은 5ms)
시간 4: P3(1ms) 도착 → P3가 P2 선점
시간 5: P3 완료 → P2 재개 (남은 2ms)
시간 7: P2 완료 → P1 재개 (남은 5ms)
시간 12: P1 완료
```

이론적으로 평균 대기 시간이 가장 짧지만, 실제 시스템에서 남은 실행 시간을 정확히 아는 건 불가능하다.

### Round Robin

각 프로세스에게 고정된 시간(Time Quantum)만큼 CPU를 주고, 시간이 끝나면 Ready Queue 뒤로 보낸다. 선점형이다.

```
Time Quantum = 4ms
프로세스: P1(24ms), P2(3ms), P3(3ms)

|-- P1 --|-- P2 --|-- P3 --|-- P1 --|-- P1 --|-- P1 --|-- P1 --|-- P1 --|
0        4        7       10       14       18       22       26       30

평균 대기 시간: (6 + 4 + 7) / 3 = 5.67ms
```

Time Quantum 설정이 핵심이다:

- **너무 크면**: FCFS와 다를 게 없다
- **너무 작으면**: Context Switch가 너무 자주 발생해서 오버헤드가 커진다

일반적으로 Context Switch 시간의 10배 이상으로 설정한다. Linux에서는 보통 1ms~10ms 사이다.

Round Robin은 Response Time이 짧다. 모든 프로세스가 빠르게 한 번씩은 실행되기 때문이다. 대화형 시스템(웹 서버 등)에 적합하다.

### Priority Scheduling

각 프로세스에 우선순위를 부여하고, 높은 우선순위부터 실행한다. 선점/비선점 둘 다 가능하다.

```
프로세스: P1(우선순위 3), P2(우선순위 1), P3(우선순위 4), P4(우선순위 2)
(숫자가 작을수록 높은 우선순위)

실행 순서: P2 → P4 → P1 → P3
```

SJF와 마찬가지로 Starvation 문제가 있다. 낮은 우선순위의 프로세스가 무한정 대기할 수 있다.

해결책은 **Aging**이다. 대기 시간이 길어질수록 우선순위를 점진적으로 올려주는 방식이다.

### Multilevel Queue

Ready Queue를 여러 개로 분리한다. 각 큐마다 다른 스케줄링 알고리즘을 적용한다.

```
[실시간 프로세스 큐]     ← 최우선, Priority Scheduling
[시스템 프로세스 큐]     ← 높은 우선순위
[대화형 프로세스 큐]     ← Round Robin
[배치 프로세스 큐]       ← FCFS
```

프로세스는 한 번 큐에 배정되면 다른 큐로 이동하지 못한다. 이게 문제가 되는 경우가 있어서 **Multilevel Feedback Queue**가 나왔다.

### Multilevel Feedback Queue

프로세스가 큐 사이를 이동할 수 있다. CPU를 오래 쓰는 프로세스는 낮은 우선순위 큐로 내려가고, I/O 위주 프로세스는 높은 우선순위 큐에 머문다.

```
[Q0: Time Quantum 8ms, RR]    ← 새 프로세스는 여기서 시작
         ↓ (8ms 내 완료 못하면)
[Q1: Time Quantum 16ms, RR]
         ↓ (16ms 내 완료 못하면)
[Q2: FCFS]                     ← CPU bound 프로세스가 여기로 내려옴
```

I/O bound 프로세스는 CPU를 짧게 쓰고 반납하니까 Q0에서 빠르게 처리된다. CPU bound 프로세스는 점점 아래 큐로 밀려난다. 대부분의 현대 OS가 이 방식의 변형을 사용한다.

주기적으로 모든 프로세스를 최상위 큐로 올리는 **Priority Boost**를 적용해서 Starvation을 방지한다.

### 알고리즘 비교

| 알고리즘 | 선점 | Starvation | 평균 대기 | 응답 시간 | 실제 사용처 |
|---------|------|------|----------|----------|----------|
| FCFS | 비선점 | 없음 | 길 수 있음 | 길 수 있음 | 배치 시스템 |
| SJF | 비선점 | 있음 | 최소 (이론) | 보통 | 이론적 |
| SRTF | 선점 | 있음 | 최소 | 좋음 | 이론적 |
| Priority | 둘 다 | 있음 (Aging으로 해결) | 보통 | 보통 | 실시간 시스템 |
| Round Robin | 선점 | 없음 | 보통 | 좋음 | 타임셰어링 |
| MLFQ | 선점 | 없음 (Boost) | 좋음 | 좋음 | 현대 범용 OS |

---

## 컨텍스트 스위칭 비용

프로세스 전환 시 현재 상태를 저장하고 다음 프로세스의 상태를 복원하는 과정이다. 스케줄링 알고리즘이 아무리 좋아도, 컨텍스트 스위칭 비용이 크면 의미가 없다.

```
1. 현재 프로세스(P1)의 PCB에 상태 저장
   - 레지스터, 프로그램 카운터, 스택 포인터 저장

2. 다음 프로세스(P2)의 PCB에서 상태 복원
   - 저장된 레지스터, PC 등 복원

3. P2 실행 재개
```

프로세스 전환과 스레드 전환의 비용 차이가 크다.

| 항목 | 프로세스 전환 | 스레드 전환 |
|------|-------------|-----------|
| 저장/복원 대상 | 전체 메모리 맵, 레지스터, PCB | 레지스터, 스택 포인터만 |
| TLB | flush 필요 (주소 공간이 다르므로) | flush 불필요 (주소 공간 공유) |
| 캐시 영향 | cold start (캐시 미스 급증) | warm 상태 유지 가능 |
| 소요 시간 | 수~수십 us | 수 us 이하 |

프로세스 전환이 비싼 이유는 TLB flush 때문이다. TLB는 가상 주소 → 물리 주소 변환을 캐싱하는데, 프로세스가 바뀌면 주소 공간이 달라지니까 TLB 전체를 비워야 한다. 전환 직후에는 모든 메모리 접근에서 TLB 미스가 발생하고, 페이지 테이블을 다시 탐색해야 한다. 이 비용이 레지스터 저장/복원보다 훨씬 크다.

스레드는 같은 프로세스 내에서 주소 공간을 공유하니까 TLB를 비울 필요가 없다. 그래서 멀티스레드 프로그래밍이 멀티프로세스보다 컨텍스트 스위칭 측면에서 유리하다.

---

## 실시간 스케줄링: RM vs EDF

일반적인 서버 애플리케이션에서는 쓸 일이 거의 없지만, 임베디드나 산업용 시스템에서는 데드라인을 반드시 지켜야 하는 경우가 있다.

### RM (Rate Monotonic)

주기가 짧은 태스크에 높은 우선순위를 부여한다. 우선순위가 한 번 정해지면 바뀌지 않는 정적 방식이다.

```
Task A: 주기 10ms, 실행 3ms → 우선순위 높음 (주기 짧음)
Task B: 주기 20ms, 실행 5ms → 우선순위 낮음

|-- A --|---- B ----|-- A --|---- B ----|-- A --|...
0       3          8      10     13     18     20
```

RM의 스케줄 가능 조건은 CPU 이용률로 판단한다.

```
U = Σ(Ci / Ti) ≤ n(2^(1/n) - 1)

Task A: 3/10 = 0.3
Task B: 5/20 = 0.25
U = 0.55

n=2일 때 한계: 2(2^0.5 - 1) ≈ 0.828
0.55 ≤ 0.828 → 스케줄 가능
```

분석이 쉽다는 게 RM의 장점이다. 설계 단계에서 수학적으로 데드라인 충족 여부를 검증할 수 있다. 하지만 CPU 이용률 상한이 100%가 아니라서, 자원을 완전히 활용하지 못하는 경우가 있다.

### EDF (Earliest Deadline First)

데드라인이 가장 가까운 태스크를 먼저 실행한다. 우선순위가 동적으로 바뀐다.

```
시간 0: A 데드라인 10ms, B 데드라인 20ms → A 먼저 실행
시간 3: A 완료, B 실행
시간 8: B 실행 중, A의 새 주기 시작 (데드라인 20ms)
        → B 데드라인 20ms와 같으므로 B 계속 실행
시간 10: B 완료, A 실행
```

EDF는 이론적으로 CPU 이용률 100%까지 스케줄 가능하다. RM보다 자원을 빈틈없이 쓸 수 있다. 하지만 구현이 복잡하고, 과부하 상태에서 어떤 태스크가 데드라인을 놓칠지 예측하기 어렵다. RM은 우선순위가 고정이라 낮은 우선순위 태스크가 먼저 밀리지만, EDF는 과부하 시 연쇄적으로 데드라인을 놓칠 수 있다.

### RM vs EDF 정리

| 항목 | RM | EDF |
|------|-----|-----|
| 우선순위 | 정적 (주기 기반) | 동적 (데드라인 기반) |
| CPU 이용률 상한 | n(2^(1/n) - 1), 약 69% (n→∞) | 100% (이론적) |
| 과부하 시 동작 | 낮은 우선순위 태스크만 밀림 | 예측 불가, 연쇄 실패 가능 |
| 구현 난이도 | 단순 | 복잡 (매 시점 우선순위 재계산) |
| 분석 용이성 | 수학적 검증 쉬움 | 시뮬레이션 필요한 경우 있음 |

실무에서는 안정성과 예측 가능성 때문에 RM을 먼저 검토하고, CPU 이용률이 부족할 때 EDF를 고려하는 식으로 접근한다.

---

## Linux CFS (Completely Fair Scheduler)

Linux 2.6.23부터 도입된 기본 스케줄러다. "완전히 공정한 스케줄러"라는 이름답게, 모든 프로세스에게 CPU 시간을 공평하게 나누는 것이 목표다.

### 동작 원리

CFS는 전통적인 Time Quantum 기반이 아니다. 대신 **vruntime(virtual runtime)**이라는 값을 사용한다.

```
vruntime = 실제 실행 시간 × (NICE_0_LOAD / 프로세스의 weight)
```

- 모든 프로세스의 vruntime이 같아지도록 스케줄링한다
- vruntime이 가장 작은 프로세스에게 CPU를 준다
- Red-Black Tree로 프로세스를 관리해서, 가장 작은 vruntime을 O(1)에 찾는다

nice 값이 낮은(우선순위가 높은) 프로세스는 weight가 크다. 같은 시간을 실행해도 vruntime이 적게 증가한다. 결과적으로 CPU를 더 많이 받는다.

### nice 값과 weight의 관계

```c
// Linux 커널 sched/core.c에 정의된 weight 테이블 (일부)
// nice  0 → weight 1024
// nice -1 → weight 1277
// nice  1 → weight  820
// nice -20 → weight 88761
// nice  19 → weight  15
```

nice 값이 1 차이나면 CPU 시간이 약 1.25배 차이난다. nice -20과 nice 19는 약 5900배 차이다.

```bash
# 프로세스의 nice 값 확인
ps -eo pid,ni,comm

# nice 값 변경 (root 권한 필요)
renice -n -5 -p 1234

# nice 값을 지정해서 프로세스 시작
nice -n 10 ./batch_job.sh
```

### CFS의 스케줄링 주기

CFS는 고정된 Time Quantum이 없다. 대신 **sched_latency**라는 값을 사용한다.

```bash
# 기본값 확인
cat /proc/sys/kernel/sched_latency_ns
# 보통 6000000 (6ms)

cat /proc/sys/kernel/sched_min_granularity_ns
# 보통 750000 (0.75ms)
```

- `sched_latency`: 모든 프로세스가 최소 한 번은 실행되는 주기
- `sched_min_granularity`: 한 프로세스가 최소한 실행되는 시간

프로세스가 8개 있으면, 각각 6ms / 8 = 0.75ms씩 받는다. 프로세스가 100개가 되면 6ms / 100 = 0.06ms인데, 이건 `sched_min_granularity`보다 작으니까 0.75ms로 올려잡는다. 이 경우 전체 주기가 75ms로 늘어난다.

### 실시간 스케줄링 클래스

CFS는 일반 프로세스(SCHED_NORMAL)에만 적용된다. 실시간 프로세스는 별도 스케줄링 클래스를 사용한다.

```
우선순위: SCHED_DEADLINE > SCHED_FIFO/SCHED_RR > SCHED_NORMAL(CFS)
```

```bash
# 현재 프로세스의 스케줄링 정책 확인
chrt -p <PID>

# SCHED_FIFO로 변경 (우선순위 50)
chrt -f -p 50 <PID>

# SCHED_RR로 변경
chrt -r -p 30 <PID>
```

실시간 스케줄링은 일반 애플리케이션에서는 거의 쓸 일이 없다. 잘못 설정하면 시스템이 먹통이 된다. SCHED_FIFO 프로세스가 무한 루프에 빠지면 같은 우선순위 이하의 프로세스는 전부 실행이 안 된다.

---

## 스케줄링이 서버 응답 시간에 미치는 영향

### CPU bound vs I/O bound

웹 서버는 대부분 I/O bound다. 요청을 받고 → DB 쿼리 날리고 → 응답을 보내는 과정에서 CPU를 쓰는 시간은 짧고, I/O 대기 시간이 길다.

CFS에서 I/O bound 프로세스는 자연스럽게 유리하다. CPU를 조금만 쓰고 반납하니까 vruntime이 천천히 증가하고, 다시 깨어났을 때 빠르게 CPU를 받는다.

문제는 CPU bound 작업이 같은 서버에서 돌아갈 때다. 이미지 리사이징, 암호화, JSON 직렬화 같은 작업이 CPU를 오래 잡으면 I/O bound 프로세스의 응답이 늦어진다.

### 실무에서 겪는 문제들

**1. 배치 작업이 API 서버 응답을 느리게 만드는 경우**

같은 서버에서 배치 작업과 API 서버를 같이 돌리면 문제가 생긴다. 배치 작업이 CPU를 많이 쓰면 API 서버의 응답 시간이 올라간다.

```bash
# 배치 작업의 nice 값을 올려서 우선순위를 낮춘다
nice -n 19 ./batch_job.sh

# 또는 cgroup으로 CPU 사용량을 제한한다
# /sys/fs/cgroup/cpu/batch/ 아래에 설정
echo 50000 > /sys/fs/cgroup/cpu/batch/cpu.cfs_quota_us
echo 100000 > /sys/fs/cgroup/cpu/batch/cpu.cfs_period_us
# → 배치 작업이 CPU의 50%만 사용 가능
```

**2. 컨테이너 환경에서 CPU throttling**

Kubernetes에서 CPU limit을 설정하면, CFS bandwidth control이 동작한다.

```yaml
resources:
  requests:
    cpu: "500m"    # 0.5 코어 요청
  limits:
    cpu: "1000m"   # 1 코어 제한
```

limit을 너무 타이트하게 잡으면 throttling이 발생한다. 프로세스가 할당된 CPU 시간을 다 쓰면, 다음 주기까지 강제로 멈춘다. 이게 응답 시간 spike의 원인이 되는 경우가 많다.

```bash
# throttling 발생 여부 확인
cat /sys/fs/cgroup/cpu/cpu.stat
# nr_throttled: throttling 발생 횟수
# throttled_time: 총 throttling 시간 (ns)
```

**3. NUMA 환경에서 스케줄러의 영향**

멀티소켓 서버에서는 프로세스가 어떤 CPU에 스케줄링되느냐에 따라 메모리 접근 시간이 달라진다. 원격 노드의 메모리에 접근하면 로컬 대비 1.5~2배 느리다.

```bash
# NUMA 노드 정보 확인
numactl --hardware

# 특정 노드에 바인딩
numactl --cpunodebind=0 --membind=0 ./server
```

---

## 스케줄링 관련 디버깅

서버 응답이 느릴 때, CPU 스케줄링 문제인지 확인하는 방법:

```bash
# 1. CPU 사용률 확인
top -b -n 1 | head -20

# 2. Context Switch 횟수 확인
vmstat 1
# cs 컬럼이 Context Switch 횟수

# 3. 프로세스별 스케줄링 통계
cat /proc/<PID>/sched
# se.sum_exec_runtime: 총 실행 시간
# se.nr_migrations: CPU 간 마이그레이션 횟수
# nr_involuntary_switches: 비자발적 Context Switch (선점당한 횟수)
# nr_voluntary_switches: 자발적 Context Switch (I/O 등으로 자발적 반납)

# 4. 스케줄링 지연 확인 (perf 사용)
perf sched latency
```

`nr_involuntary_switches`가 비정상적으로 높으면 CPU 경쟁이 심한 상태다. 프로세스 수를 줄이거나, CPU를 추가하거나, cgroup으로 격리해야 한다.

`nr_voluntary_switches`가 높으면 I/O 대기가 많다는 뜻이다. 이 경우는 디스크나 네트워크 I/O를 줄이는 게 답이다.
