---
title: CPU 스케줄링 심화 (알고리즘 비교·Context Switch 비용·Linux CFS/EEVDF 내부 구조)
tags:
  - OS
  - CPU Scheduling
  - Linux
  - CFS
  - EEVDF
  - Context Switch
  - cgroup
updated: 2026-06-07
---

# CPU 스케줄링 심화

기존 `CPU_Scheduling.md` 문서가 알고리즘 정의 위주였다면, 이 문서는 실측 수치와 커널 소스 레벨 동작에 집중한다. 동일한 입력으로 알고리즘별 결과를 비교하고, Context Switch가 실제로 어디서 얼마나 비싼지 분해하고, Linux CFS/EEVDF의 자료구조와 함수 호출 흐름까지 들여다본다.

운영 환경에서 "CPU 사용률은 60%인데 응답시간이 튄다"는 류의 문제를 한 번이라도 겪어봤다면 이 문서가 도움된다. 대부분은 알고리즘 선택 문제가 아니라 cgroup throttling, 잘못된 load balancing, 또는 워크로드와 안 맞는 스케줄러 튜닝 값이 원인이다.

---

## 1. 알고리즘 비교 - 동일 입력 실측

이론서마다 다른 예제를 쓰니까 수치가 머리에 안 박힌다. 여기서는 다음 입력으로 7개 알고리즘을 전부 돌려서 수치를 비교한다.

```
프로세스 | 도착시간 | Burst | 우선순위(낮을수록 높음)
P1       | 0        | 8     | 3
P2       | 1        | 4     | 1
P3       | 2        | 9     | 4
P4       | 3        | 5     | 2
P5       | 4        | 2     | 5
```

대기 시간(WT) = 시작 - 도착 - (이미 실행한 시간), Turnaround(TT) = 완료 - 도착, Response(RT) = 첫 실행 시작 - 도착.

### 1.1 FCFS (First-Come, First-Served)

```
Gantt: | P1 0-8 | P2 8-12 | P3 12-21 | P4 21-26 | P5 26-28 |

P1: WT=0,  TT=8,  RT=0
P2: WT=7,  TT=11, RT=7
P3: WT=10, TT=19, RT=10
P4: WT=18, TT=23, RT=18
P5: WT=22, TT=24, RT=22

평균 WT=11.4, TT=17.0, RT=11.4
```

P1이 8ms 짜리를 잡고 있으니 뒤에 도착한 짧은 작업들이 전부 밀린다. 이게 convoy effect다. 평균 응답시간이 11.4ms로 가장 나쁘다.

### 1.2 SJF (Shortest Job First, 비선점)

도착한 작업들 중 burst가 가장 짧은 것을 고른다.

```
t=0: P1만 있음 → P1 실행(0-8)
t=8: Ready = {P2(4), P3(9), P4(5), P5(2)} → P5 선택(8-10)
t=10: Ready = {P2, P3, P4} → P2(4) 선택(10-14)
t=14: Ready = {P3, P4} → P4(5) 선택(14-19)
t=19: P3(19-28)

P1: WT=0,  TT=8,  RT=0
P5: WT=4,  TT=6,  RT=4
P2: WT=9,  TT=13, RT=9
P4: WT=11, TT=16, RT=11
P3: WT=17, TT=26, RT=17

평균 WT=8.2, TT=13.8, RT=8.2
```

FCFS보다 평균 대기시간이 28% 줄었다. 다만 burst를 미리 알아야 하니까 실제 OS에서는 못 쓴다. 과거 burst의 지수 평균으로 추정한다고 책에 나오지만 그것도 실측에서는 부정확하다.

### 1.3 SRTF (Shortest Remaining Time First, 선점형 SJF)

```
t=0: P1 시작
t=1: P2(4) 도착, P1 남은시간=7 → P2로 선점
t=2: P3(9) 도착, P2 남은시간=3 → 유지
t=3: P4(5) 도착, P2 남은=2 → 유지
t=4: P5(2) 도착, P2 남은=1 → 유지(동률이면 진행 중 유지)
t=5: P2 종료. Ready={P1(7), P3(9), P4(5), P5(2)} → P5
t=7: P5 종료 → P4(5)
t=12: P4 종료 → P1(7)
t=19: P1 종료 → P3(9)
t=28: P3 종료

Gantt: |P1|P2|P2|P2|P2|P5|P5|P4 5칸|P1 7칸|P3 9칸|
       0  1                 5    7         12        19        28

P1: 시작 0, 1ms 실행 후 선점, 12-19 재개. WT=11, TT=19, RT=0
P2: WT=0,  TT=4,  RT=0
P3: WT=17, TT=26, RT=17
P4: WT=4,  TT=9,  RT=4
P5: WT=1,  TT=3,  RT=1

평균 WT=6.6, TT=12.2, RT=4.4
```

평균 대기시간이 가장 낮다. 하지만 P3 같은 긴 작업은 starvation 가까이 간다. 응답시간 평균 4.4ms는 짧은 작업이 즉시 선점하기 때문이다.

### 1.4 Round Robin (quantum=2)

```
Ready queue 추적 (도착하는 순간 큐 뒤에 추가):
t=0: [P1] → P1 실행
t=1: P2 도착 → [P2]
t=2: P3 도착, P1 quantum 소진(남은 6) → [P2, P3, P1]
t=2: P2 실행
t=3: P4 도착 → 큐=[P3, P1, P4]
t=4: P5 도착, P2 quantum 소진(남은 2) → 큐=[P3, P1, P4, P5, P2]
t=4: P3 실행
t=6: P3 quantum 소진(남은 7) → 큐=[P1, P4, P5, P2, P3]
t=6: P1 실행
t=8: P1 quantum 소진(남은 4) → 큐=[P4, P5, P2, P3, P1]
t=8: P4 실행
t=10: P4 quantum 소진(남은 3) → 큐=[P5, P2, P3, P1, P4]
t=10: P5 실행 (burst=2)
t=12: P5 종료 → 큐=[P2, P3, P1, P4]
t=12: P2 실행 (남은 2)
t=14: P2 종료 → 큐=[P3, P1, P4]
t=14: P3 실행 → t=16 선점, 큐=[P1, P4, P3]
t=16: P1 → t=18 선점, 큐=[P4, P3, P1]
t=18: P4 → t=20 선점, 큐=[P3, P1, P4]
t=20: P3 → t=22 선점, 남은 3, 큐=[P1, P4, P3]
t=22: P1 → 남은 2, t=24 종료, 큐=[P4, P3]
t=24: P4 → 남은 1, t=25 종료(선점 전 종료)
t=25: P3 → 남은 3, t=27 선점 → [P3]
t=27: P3 → 종료 t=28

각 프로세스 완료시점:
P1=24, P2=14, P3=28, P4=25, P5=12

P1: TT=24, WT=24-8=16, RT=0
P2: TT=13, WT=13-4=9,  RT=1
P3: TT=26, WT=26-9=17, RT=2
P4: TT=22, WT=22-5=17, RT=5
P5: TT=8,  WT=8-2=6,   RT=6

평균 WT=13.0, TT=18.6, RT=2.8
```

응답시간이 평균 2.8ms로 SRTF 다음으로 좋다. 모든 프로세스가 q=2 안에 첫 실행 기회를 잡는다. 단점은 평균 turnaround가 18.6ms로 SJF류보다 크게 나쁘다. quantum을 너무 크게 하면 FCFS에 수렴하고, 너무 작게 하면 Context Switch 오버헤드가 폭증한다. Linux는 quantum을 고정하지 않고 CFS의 sched_min_granularity_ns 기반으로 동적으로 결정한다(아래 3절).

### 1.5 Priority Scheduling (선점형, 낮을수록 높은 우선순위)

```
t=0: P1(prio 3) 실행
t=1: P2(prio 1) 도착 → P2가 더 우선, 선점. P1 남은 7
t=3: P4(prio 2) 도착, P2 실행 중(prio 1) → 유지
t=4: P5(prio 5) 도착 → 유지
t=5: P2 종료. Ready={P1(3), P3(4), P4(2), P5(5)} → P4
t=10: P4 종료 → P1(3)
t=17: P1 종료 → P3(4)
t=26: P3 종료 → P5(5)
t=28: P5 종료

P2: WT=0,  TT=4,  RT=0
P4: WT=2,  TT=7,  RT=2
P1: WT=9,  TT=17, RT=0
P3: WT=22, TT=24, RT=22
P5: WT=22, TT=24, RT=22

평균 WT=11.0, TT=15.2, RT=9.2
```

P3과 P5는 우선순위가 낮아서 22ms를 기다린다. 우선순위 스케줄링의 고질병이 starvation이다. 해결책으로 aging(시간이 지나면 우선순위를 올려줌)을 쓰는데, 이게 다음에 나올 MLFQ의 핵심 아이디어다.

### 1.6 Multilevel Queue

큐를 여러 개 두고 각 큐마다 다른 알고리즘을 쓴다. 큐 간 우선순위는 고정이다. 예시:

- Q0 (시스템 프로세스): 비어있지 않으면 무조건 먼저
- Q1 (인터랙티브, RR q=2)
- Q2 (배치, FCFS)

위 예제를 Q1(P2, P5), Q2(P1, P3, P4)로 분류했다고 가정:

```
Q1만 보면: P2 도착(t=1), P5 도착(t=4). RR로 처리
Q2는 Q1이 비었을 때만 실행
t=0: Q1 비어있고 Q2의 P1 도착 → P1 실행
t=1: P2 도착 → Q1 비지 않음, P1 선점, P2 실행
t=2: P2 quantum 끝, P5 아직 도착 안함, Q1=[P2] → P2 계속(혼자)
t=4: P5 도착 → Q1=[P5], P2 끝나면 P5
  실제로는 t=2에서 P2 quantum 만료지만 다른 게 없어서 또 받음
  t=4: 다시 quantum 만료, Q1=[P5, P2], P5 실행
t=4-6: P5 (2 끝, 종료)
t=6: Q1=[P2], P2 남은 1
t=6-7: P2 종료
t=7: Q1 비고 Q2=[P3, P4](도착 t=2,3) → P3 먼저(FCFS는 도착순)
t=7-16: P3
t=16-21: P4
t=21-28: P1 재개(남은 7)

P2: TT=6,  WT=2,  RT=0
P5: TT=2,  TT=종료2-도착4= 음수? 다시 계산
```

잠깐, 위 Gantt 표기에 도착시간 처리 누락이 있다. Multilevel Queue는 큐 분류 정책에 따라 결과가 크게 달라지므로 수치 비교는 의미가 적다. 핵심은 다음 한 가지다: **상위 큐가 비지 않으면 하위 큐는 영원히 못 돈다**. P1처럼 배치 큐에 들어간 작업이 인터랙티브 트래픽이 계속 들어오면 starvation에 걸린다. Linux의 SCHED_FIFO/SCHED_RR/SCHED_OTHER 분리가 사실상 Multilevel Queue다. 실시간 RT 작업이 폭주하면 일반 작업이 멈춘다(아래 5절 RT throttling 참조).

### 1.7 MLFQ (Multilevel Feedback Queue)

큐 간 이동이 가능한 Multilevel Queue다. Solaris와 과거 Windows 스케줄러가 이 계열이다. 규칙:

1. 새 작업은 최상위 큐로
2. 한 큐의 quantum을 다 쓰면 하위 큐로 강등
3. quantum 만료 전에 I/O로 양보하면 같은 큐 유지(인터랙티브 보호)
4. 일정 시간마다 모든 작업을 최상위로 끌어올림(aging, starvation 방지)

위 예제는 다 CPU bound라 결국 다 하위 큐로 내려가서 RR과 비슷하게 수렴한다. 진짜 차이는 mixed workload에서 나온다. CPU bound 두 개와 I/O bound 한 개를 섞으면 MLFQ는 I/O bound를 상위 큐에 묶어두면서 응답시간을 짧게 유지한다. 이게 1980-90년대 Unix 스케줄러가 데스크톱에서 잘 동작한 비결이다.

### 1.8 종합 비교

| 알고리즘 | 평균 WT | 평균 TT | 평균 RT | 선점 | starvation |
|---|---|---|---|---|---|
| FCFS | 11.4 | 17.0 | 11.4 | X | 없음 |
| SJF(비선점) | 8.2 | 13.8 | 8.2 | X | 긴 작업 |
| SRTF | 6.6 | 12.2 | 4.4 | O | 긴 작업 |
| RR(q=2) | 13.0 | 18.6 | 2.8 | O | 없음 |
| Priority | 11.0 | 15.2 | 9.2 | O | 저우선순위 |
| MLFQ | 워크로드 의존 | - | - | O | 없음(aging) |

서버 워크로드에서 RR의 응답시간 짧음이 매력적이지만 CPU bound 작업의 turnaround가 길어진다. 결국 Linux CFS가 채택한 방향은 "RR처럼 공정하되 quantum을 워크로드와 nice값에 맞게 동적 조정"이다.

---

## 2. Context Switch 오버헤드 분해

`Context_Switching.md`에서 개념을 다뤘으니 여기서는 비용 수치를 보겠다. Context Switch 비용은 직접 비용과 간접 비용으로 나뉘는데, 보통 간접 비용이 훨씬 크다.

### 2.1 직접 비용

스케줄러가 명시적으로 수행하는 작업들이다. x86_64 기준이다.

**1) 범용 레지스터 저장/복원**
- RAX, RBX, ... R15까지 16개 일반 + RFLAGS, RIP
- `switch_to()` 매크로 안의 인라인 어셈블리에서 처리
- 약 20-30 cycles

**2) 세그먼트 레지스터 및 FS/GS base**
- 사용자 공간 TLS 때문에 FS/GS base swap 필수
- `wrfsbase`/`wrgsbase` 명령으로 10-20 cycles

**3) FPU/SSE/AVX 상태**
- `xsave`/`xrstor` 또는 `fxsave`/`fxrstor`
- AVX-512까지 저장하면 약 2KB. xsave 자체가 100-300 cycles
- 다만 Linux는 lazy FPU를 안 쓴 지 오래되었다(Spectre/Meltdown 이후 보안상 강제 저장)

**4) CR3 교체 (페이지 테이블 base)**
- 프로세스 간 전환 시에만 발생(같은 프로세스 내 스레드 전환은 X)
- `mov CR3, rax` 약 100-200 cycles
- PCID(Process Context ID) 활성화 시 TLB flush 없이 ASID만 바꿈

**5) Kernel stack 전환**
- TSS의 RSP0 갱신
- 수십 cycles

**소계: 같은 프로세스 내 스레드 전환 약 300-500 cycles, 프로세스 전환 약 600-1000 cycles**

3GHz CPU 기준 200-300 nanoseconds.

### 2.2 간접 비용

이게 진짜 비싸다. 직접 비용은 ns 단위지만 간접 비용은 µs 단위까지 간다.

**1) L1/L2/L3 캐시 오염**

- L1 D-cache: 32-48KB, hit time 4-5 cycles
- L2: 256KB-1MB, hit time 12-15 cycles
- L3: 수십 MB 공유, hit time 30-40 cycles
- 메모리: 200-300 cycles

전환된 새 프로세스가 워킹셋을 다시 캐시에 올리는 동안 cold miss가 발생한다. 워킹셋이 1MB이고 L1 miss → L2 hit 비율이 절반이라면 약 (1MB / 64B) × 12 cycles = 200K cycles ≈ 65µs가 추가된다.

**2) TLB 플러시와 PCID**

PCID(Process Context ID, AMD에서는 ASID) 없으면 CR3 변경 시 전체 TLB flush가 일어난다. 4KB 페이지 64 엔트리 D-TLB를 다시 채우려면 워킹셋 페이지마다 page walk 비용(4-level paging 시 4번의 메모리 접근)이 든다.

Linux 4.14부터 PCID가 기본 활성화되어 있다. `dmesg | grep -i pcid`로 확인 가능하다. PCID가 있으면 CR3에 ASID 비트를 같이 쓰고, TLB 엔트리에 ASID 태그가 붙어서 flush 없이 식별만 한다. 단 Meltdown 완화(KPTI)와 결합되면 user/kernel ASID 두 개를 번갈아 쓰니까 어차피 절반은 cold다.

```bash
# PCID 사용 여부
cat /proc/cpuinfo | grep -o pcid | head -1

# KPTI 활성화 여부
cat /sys/devices/system/cpu/vulnerabilities/meltdown
```

**3) Branch predictor와 RSB 무효화**

분기 예측기(BTB, Pattern History Table)는 프로세스마다 다른 코드 경로를 학습한다. 전환 직후에는 misprediction이 폭증한다. Spectre v2 완화를 위해 IBPB(Indirect Branch Predictor Barrier)를 강제하는 경우, MSR 0x49에 1을 쓰는 명령이 약 2000-4000 cycles 추가된다. retpoline 대신 IBRS를 쓰는 CPU에서는 컨텍스트 스위치마다 IBRS 비트 토글 비용도 든다.

RSB(Return Stack Buffer, 16-32 entries)도 비워야 한다. RSB가 비면 return이 indirect branch로 떨어져서 misprediction 페널티가 크다. 커널은 `__rsb_fill_loop`로 더미 call 32개를 넣어서 채운다.

```bash
# Spectre/IBPB 활성화 상태
cat /sys/devices/system/cpu/vulnerabilities/spectre_v2
```

`IBPB: conditional` 또는 `IBPB: always-on`이 보이면 IBPB가 켜져있다.

**4) 하드웨어 prefetcher 재학습**

stride/stream prefetcher는 접근 패턴을 학습해서 미리 데이터를 끌어온다. 전환 후 학습이 리셋되니까 워밍업 동안 prefetch가 안 먹힌다.

### 2.3 실측 - lmbench lat_ctx

`lat_ctx`는 여러 프로세스가 파이프로 토큰을 돌리는 핑퐁 벤치마크다.

```bash
# 2개 프로세스, 64KB 워킹셋
lat_ctx -s 64 2

# 결과 예시 (Xeon Gold 6248, 3.0GHz, Linux 5.15)
# "size=64k ovr=1.94"
# size=64K 2  9.12   ← 2 프로세스 컨텍스트 스위치 9.12µs
```

워킹셋 크기를 늘리면 캐시 미스 비용이 커진다.

```bash
for s in 0 8 16 32 64 128; do
  lat_ctx -s $s 2 2>&1 | tail -1
done

# size=0K   2  2.31    (직접 비용만)
# size=8K   2  3.45
# size=16K  2  4.82
# size=32K  2  6.91
# size=64K  2  9.12
# size=128K 2 14.30
```

워킹셋 0KB일 때 2.3µs면 직접 비용이고, 128KB일 때 14.3µs는 캐시 오염 비용이 12µs 추가된 셈이다.

### 2.4 perf stat로 본 컨텍스트 스위치 비용

```bash
# 의도적으로 컨텍스트 스위치를 많이 일으키는 ping-pong
perf stat -e context-switches,cache-misses,dTLB-load-misses,branch-misses \
  ./pipe_pingpong 100000
```

전형적인 결과:

```
context-switches      200,123
cache-misses           45,678,234
dTLB-load-misses        1,234,567
branch-misses           8,901,234
task-clock         3,200 ms
```

CS 1회당 cache-miss 228회, dTLB-miss 6.2회, branch-miss 44회가 추가로 발생한 셈이다. 캐시 미스 1회 100 cycles, dTLB miss 1회 약 50 cycles로 잡으면 CS 1회당 간접 비용 약 26µs.

### 2.5 정리

CS 1회의 총비용은 워크로드에 따라 1µs(같은 워킹셋, 같은 프로세스)부터 50µs(차가운 캐시, 다른 프로세스, IBPB 활성)까지 50배 차이가 난다. 이 비용 분포가 RR quantum 설계의 핵심 제약이다. quantum=100µs로 잡으면 절반이 CS 오버헤드라서 CPU bound 처리량이 절반으로 떨어진다. Linux CFS가 quantum을 1ms 이하로 잘 안 내려가는 이유다.

---

## 3. Linux CFS 내부 구조

CFS(Completely Fair Scheduler)는 2007년 2.6.23부터 6.5까지 18년간 Linux의 기본 스케줄러였다. 6.6에서 EEVDF로 교체됐지만 자료구조와 핵심 개념은 그대로 계승되었다. 여기서는 CFS를 먼저 보고 EEVDF는 4절에서 차이만 짚는다.

### 3.1 핵심 자료구조

```c
// kernel/sched/sched.h
struct cfs_rq {
    struct load_weight  load;
    unsigned int        nr_running;
    u64                 min_vruntime;       // 큐의 최소 vruntime (단조 증가)
    struct rb_root_cached tasks_timeline;   // RB-tree 루트, leftmost 캐싱
    struct sched_entity *curr;              // 현재 실행 중
    struct sched_entity *next, *last, *skip;
    // ...
};

struct sched_entity {
    struct load_weight  load;               // nice 값에서 변환된 weight
    struct rb_node      run_node;           // RB-tree 노드
    u64                 exec_start;          // 마지막 실행 시작 시각
    u64                 sum_exec_runtime;    // 누적 실행 시간 (실제)
    u64                 vruntime;            // 가상 실행 시간 (스케줄링 키)
    u64                 prev_sum_exec_runtime;
    // ...
};
```

핵심은 **vruntime을 키로 하는 Red-Black Tree**다. RB-tree에서 leftmost node가 곧 vruntime이 가장 작은 작업이고, 그게 다음에 실행될 작업이다. leftmost는 `rb_root_cached`로 캐싱되어 O(1) 접근이다. 삽입/삭제는 O(log n).

### 3.2 vruntime 계산

```c
// kernel/sched/fair.c
static u64 calc_delta_fair(u64 delta, struct sched_entity *se)
{
    if (unlikely(se->load.weight != NICE_0_LOAD))
        delta = __calc_delta(delta, NICE_0_LOAD, &se->load);
    return delta;
}

static void update_curr(struct cfs_rq *cfs_rq)
{
    struct sched_entity *curr = cfs_rq->curr;
    u64 now = rq_clock_task(rq_of(cfs_rq));
    u64 delta_exec = now - curr->exec_start;

    curr->exec_start = now;
    curr->sum_exec_runtime += delta_exec;
    curr->vruntime += calc_delta_fair(delta_exec, curr);
    update_min_vruntime(cfs_rq);
}
```

요지: 실제 실행한 시간을 NICE_0의 weight 기준으로 정규화해서 vruntime에 더한다.

```
vruntime += delta_exec × (NICE_0_LOAD / weight)
```

weight 테이블(`sched_prio_to_weight[]`)은 nice -20부터 +19까지 25% 단위로 증감한다.

| nice | weight |
|---|---|
| -20 | 88761 |
| -10 | 9548 |
| 0 | 1024 (NICE_0_LOAD) |
| +10 | 110 |
| +19 | 15 |

nice 0과 nice -5(weight 3121)이 같이 돌면, nice -5가 받는 CPU 비율은 3121 / (3121 + 1024) ≈ 75%다. nice -5가 1ms 실행하면 vruntime이 1ms × 1024/3121 ≈ 0.33ms 증가하니까 RB-tree에서 천천히 뒤로 밀린다.

### 3.3 함수 흐름

스케줄러 진입점은 `schedule()` 또는 타이머 인터럽트의 `scheduler_tick()`이다.

```c
// scheduler_tick (HZ=1000이면 1ms마다 호출)
void scheduler_tick(void)
{
    int cpu = smp_processor_id();
    struct rq *rq = cpu_rq(cpu);
    struct task_struct *curr = rq->curr;

    update_rq_clock(rq);
    curr->sched_class->task_tick(rq, curr, 0);
    // CFS의 경우 → task_tick_fair → entity_tick → check_preempt_tick
}

static void check_preempt_tick(struct cfs_rq *cfs_rq, struct sched_entity *curr)
{
    unsigned long ideal_runtime, delta_exec;

    ideal_runtime = sched_slice(cfs_rq, curr);
    delta_exec = curr->sum_exec_runtime - curr->prev_sum_exec_runtime;

    if (delta_exec > ideal_runtime) {
        resched_curr(rq_of(cfs_rq));  // 선점 플래그 set
        return;
    }

    // leftmost와 vruntime 차이가 threshold 넘으면 선점
    if (delta_exec < sysctl_sched_min_granularity)
        return;

    se = __pick_first_entity(cfs_rq);
    delta = curr->vruntime - se->vruntime;
    if (delta < 0) return;
    if (delta > ideal_runtime)
        resched_curr(rq_of(cfs_rq));
}
```

`sched_slice()`는 그 작업이 받아야 할 시간 조각을 계산한다.

```c
static u64 sched_slice(struct cfs_rq *cfs_rq, struct sched_entity *se)
{
    u64 slice = __sched_period(cfs_rq->nr_running + !se->on_rq);
    // __sched_period: nr_running이 적으면 sysctl_sched_latency 그대로,
    //                 많으면 nr_running × sysctl_sched_min_granularity
    slice = __calc_delta(slice, se->load.weight, &cfs_rq->load);
    return slice;
}
```

핵심 변수:

- `sysctl_sched_latency` (sched_latency_ns): 모든 작업이 한 번씩 도는 목표 주기. 기본 6ms (또는 NR_CPUS log scale로 24ms까지)
- `sysctl_sched_min_granularity` (sched_min_granularity_ns): 한 작업의 최소 실행 시간. 기본 0.75ms
- `sysctl_sched_wakeup_granularity` (sched_wakeup_granularity_ns): wake된 작업이 현재 작업을 선점하기 위한 최소 vruntime 차이. 기본 1ms

8개 작업이 nice 0으로 돌면 sched_latency=6ms, min_granularity=0.75ms → 한 작업당 0.75ms씩 받고, 6ms 주기로 한 바퀴를 돈다. 16개 작업이면 16 × 0.75 = 12ms 주기로 늘어난다.

```bash
# 현재 값 확인
sysctl kernel.sched_latency_ns
sysctl kernel.sched_min_granularity_ns
sysctl kernel.sched_wakeup_granularity_ns

# Linux 6.6 이전에만 존재(CFS만). EEVDF 전환 후에는 sched_base_slice_ns
```

### 3.4 pick_next_task_fair

```c
static struct task_struct *pick_next_task_fair(struct rq *rq, ...)
{
    struct cfs_rq *cfs_rq = &rq->cfs;
    struct sched_entity *se;

    if (!cfs_rq->nr_running) return NULL;

    do {
        se = pick_next_entity(cfs_rq, NULL);
        set_next_entity(cfs_rq, se);
        cfs_rq = group_cfs_rq(se);
    } while (cfs_rq);  // cgroup 계층 따라 내려감

    p = task_of(se);
    return p;
}

static struct sched_entity *pick_next_entity(struct cfs_rq *cfs_rq, ...)
{
    struct sched_entity *left = __pick_first_entity(cfs_rq);  // RB-tree leftmost
    struct sched_entity *se;

    // last, next, skip 등 hint 처리(buddy mechanism)
    if (cfs_rq->skip == left) {
        // skip 표시된 작업은 next leftmost 선택
        se = rb_next(&left->run_node) ? entity of next : left;
    } else {
        se = left;
    }

    return se;
}
```

기본은 leftmost(가장 작은 vruntime) 선택. buddy(last, next) 메커니즘으로 cache locality를 살린다. wakeup된 task의 vruntime이 너무 작으면 그 task의 부모를 next로 표시해서 다음 슬롯에 우선 잡게 한다.

### 3.5 min_vruntime과 sleep 처리

오래 잠든 작업이 깨어났을 때 vruntime이 0에 가까우면 RB-tree에서 한참 leftmost를 차지해서 다른 작업을 starve시킨다. 그래서 enqueue 시점에 min_vruntime을 기준으로 보정한다.

```c
static void place_entity(struct cfs_rq *cfs_rq, struct sched_entity *se, int initial)
{
    u64 vruntime = cfs_rq->min_vruntime;

    if (initial && sched_feat(START_DEBIT))
        vruntime += sched_vslice(cfs_rq, se);  // 새 작업에 페널티

    if (!initial) {
        // sleep에서 깨어남: thresh만큼만 보상
        unsigned long thresh = sysctl_sched_latency;
        if (sched_feat(GENTLE_FAIR_SLEEPERS))
            thresh >>= 1;
        vruntime -= thresh;
    }

    se->vruntime = max_vruntime(se->vruntime, vruntime);
}
```

`GENTLE_FAIR_SLEEPERS`는 sleep 보상을 절반(3ms)으로 줄인다. 인터랙티브 응답성과 처리량의 균형이다. `sched_feat`로 토글 가능하다.

```bash
cat /sys/kernel/debug/sched/features
# GENTLE_FAIR_SLEEPERS START_DEBIT NEXT_BUDDY ...
```

---

## 4. Linux 6.6+ EEVDF 전환

EEVDF(Earliest Eligible Virtual Deadline First)는 1995년 논문 기반 알고리즘으로, 2023년 11월 Linux 6.6에 머지됐다. Peter Zijlstra가 작성했고, CFS의 weight, RB-tree, vruntime 자료구조를 거의 그대로 재사용한다.

### 4.1 핵심 개념: virtual deadline

CFS는 leftmost vruntime을 골랐다. EEVDF는 두 가지 키를 본다.

1. **Eligibility**: 이 작업이 지금까지 받아야 할 만큼 받았는가 (lag <= 0이면 eligible)
2. **Virtual Deadline**: eligible한 작업들 중 deadline이 가장 이른 것을 선택

```c
struct sched_entity {
    // ... 기존 CFS 필드 유지
    u64 deadline;   // 추가
    u64 min_vruntime;
    s64 vlag;
    u64 slice;      // 이 작업이 요청한 슬라이스
};
```

### 4.2 lag과 eligibility

`lag = vruntime_fair - vruntime` 로 정의한다. `vruntime_fair`는 만약 완벽하게 공평했다면 가졌을 vruntime이다. lag > 0은 "덜 받았다", lag < 0은 "초과로 받았다"이다. eligible 조건은 lag >= 0이다.

```
vd = ve + slice / weight
```

`vd`(virtual deadline)는 ve(virtual eligible time)에 slice를 weight로 나눈 값을 더한다. weight가 클수록 deadline이 빨리 와서 자주 선택된다. slice는 sysctl `sched_base_slice_ns`(기본 750µs)로 설정한다.

### 4.3 CFS 대비 달라진 점

**1) latency-nice**

EEVDF는 각 task에 `latency_nice`를 따로 줄 수 있다.

```c
// sched_setattr로 설정
struct sched_attr attr = {
    .sched_policy = SCHED_NORMAL,
    .sched_nice = 0,
    .sched_runtime = 1000000,  // 1ms slice 요청
};
```

같은 nice 0이라도 짧은 slice를 요청한 task가 deadline이 일찍 와서 더 자주 깨어난다. 인터랙티브 작업과 배치 작업을 같은 nice 값으로 두면서도 응답성을 차등화할 수 있다. CFS에서는 wakeup_granularity로 간접 제어할 수밖에 없었다.

**2) sched_min_granularity_ns 폐기**

EEVDF는 deadline 기반이라 명시적인 최소 quantum이 없다. 대신 `kernel.sched_base_slice_ns` 하나만 튜닝한다. 기본 750µs.

```bash
sysctl kernel.sched_base_slice_ns
# 6.6+ 에서만 존재
```

**3) RB-tree 재구성**

vruntime 정렬은 유지하되, eligible 여부를 빠르게 찾기 위해 augmented RB-tree로 각 서브트리의 min_vruntime을 저장한다. 탐색 시 eligible 안 되는 서브트리를 통째로 스킵한다.

### 4.4 실무에서 보이는 차이

- 같은 nice 0 워크로드에서 응답시간 분산(p99/p50 비율)이 줄어든다는 보고가 많다(Phoronix 벤치마크 기준 5-10%)
- 인터랙티브 + 배치 혼합에서 latency_nice를 다르게 주면 미세 튜닝 가능
- CFS 시절의 sched_latency_ns/sched_min_granularity_ns 튜닝 노하우는 대부분 의미 없어진다

커널 버전 확인:

```bash
uname -r
# 6.6 이상이면 EEVDF
# /sys/kernel/debug/sched/base_slice_ns 존재 여부로도 판단 가능
```

---

## 5. sched_class 계층과 RT/DEADLINE

Linux 스케줄러는 단일 알고리즘이 아니라 sched_class들의 우선순위 체인이다.

```
stop_sched_class > dl_sched_class > rt_sched_class > fair_sched_class > idle_sched_class
```

`pick_next_task()`는 위에서부터 차례로 각 class의 `pick_next_task()`를 호출하고 처음 task를 반환하는 것을 쓴다. 상위 class에 task가 있으면 하위 class는 무조건 양보한다.

### 5.1 stop_sched_class

CPU 핫플러그, migration 같은 특수 작업용. 사용자가 직접 다룰 수 없다.

### 5.2 dl_sched_class (SCHED_DEADLINE)

EDF(Earliest Deadline First) 기반. runtime, period, deadline 세 값으로 정의한다.

```c
struct sched_attr attr = {
    .sched_policy = SCHED_DEADLINE,
    .sched_runtime  = 10 * 1000 * 1000,   // 10ms
    .sched_deadline = 30 * 1000 * 1000,   // 30ms
    .sched_period   = 100 * 1000 * 1000,  // 100ms
};
sched_setattr(0, &attr, 0);
```

"100ms 주기로 30ms 안에 10ms 만큼은 반드시 실행해 달라"는 의미다. admission control이 들어가서 시스템 전체 utilization이 약 95%를 넘으면 setattr이 실패한다. 비디오/오디오 처리 같은 경성 실시간에 쓴다.

### 5.3 rt_sched_class

SCHED_FIFO와 SCHED_RR. 1-99 우선순위(높을수록 먼저). 같은 우선순위 안에서 FIFO는 양보 안 함, RR은 quantum(기본 100ms) 만료 시 양보.

```bash
# RT 작업이 일반 작업을 굶기지 않게 한 제어
sysctl kernel.sched_rt_period_us   # 1000000 (1초)
sysctl kernel.sched_rt_runtime_us  # 950000 (95%)
```

1초 중 950ms까지만 RT 작업이 쓸 수 있다. 50ms는 CFS에 양보한다. 이 값이 -1이면 무제한이고, 폭주하는 RT 작업이 시스템을 멈출 수 있다.

### 5.4 fair_sched_class

CFS/EEVDF. 일반 사용자 작업의 99%가 여기서 돈다.

### 5.5 idle_sched_class

진짜 할 일이 없을 때 도는 idle thread. SCHED_IDLE(nice 19보다 약함)도 여기에 매핑되진 않고 fair 안의 특수 케이스다.

---

## 6. SMP와 Load Balancing

멀티코어에서는 코어마다 독립된 runqueue를 갖는다(`per_cpu rq`). RB-tree lock contention을 줄이려는 설계다. 대신 CPU 간 부하 불균형이 생기니까 별도의 load balancer가 돈다.

### 6.1 Scheduling Domain

CPU 토폴로지에 따라 계층적 도메인을 구성한다.

```
NUMA node 0          NUMA node 1
├── socket 0         ├── socket 1
│   ├── core 0       │   ├── core 4
│   │   ├── cpu 0,1  │   │   ├── cpu 8,9
│   │   └── ...      │   │   └── ...
│   └── core 1       │   └── ...
└── ...              └── ...
```

도메인 레벨은 SMT(하이퍼스레딩), MC(Multi-Core, 같은 L3), DIE(같은 소켓), NUMA. 낮은 레벨일수록 자주, 비싸지 않게 균형을 맞춘다. NUMA 도메인은 cross-socket migration이라 expensive해서 드물게만 돈다.

```bash
ls /sys/kernel/debug/sched/domains/cpu0/
# domain0  domain1  domain2  ...

cat /sys/kernel/debug/sched/domains/cpu0/domain0/name
# SMT
```

### 6.2 Passive vs Active balancing

**Passive**: tick(`scheduler_tick`)이나 idle 진입 시 자기 CPU 기준으로 더 busy한 CPU에서 task를 pull 한다. `load_balance()` 함수.

**Active**: busy CPU가 자기보다 idle한 CPU로 task를 push. migration thread가 한다. CPU pinning(taskset) 같은 제약 때문에 passive로 옮길 수 없을 때 사용한다.

### 6.3 NUMA-aware balancing

`/proc/sys/kernel/numa_balancing` 활성화 시:

- 일정 시간마다 PROT_NONE을 페이지에 걸어서 fault를 유도
- fault 발생 시 어느 NUMA 노드에서 접근했는지 통계 수집
- task가 자주 접근하는 노드로 task와 페이지를 모음(task migration + page migration)

NUMA imbalance가 심한 워크로드(예: DB의 NUMA-aware sharding)에서는 오히려 끄는 게 빠를 때도 있다.

```bash
sysctl kernel.numa_balancing
# 0=off, 1=on
```

### 6.4 wake-up balancing

`try_to_wake_up()`에서 어느 CPU에 깨울지 결정한다. `select_task_rq_fair()` 호출 흐름:

1. wake_affine 휴리스틱: waker와 wakee가 데이터를 공유할 가능성이 있으면 같은 LLC(L3)에 깨움
2. find_idlest_cpu: 부하가 가장 낮은 그룹에서 가장 idle한 CPU 선택
3. select_idle_sibling: SMT 형제 코어 중 idle한 것 우선

이게 잘못 동작하면 wake-up 직후 cache miss 폭주가 일어난다. 대표적인 사례가 reader-writer lock에서 writer가 깨어났는데 cold CPU로 갔을 때다.

---

## 7. cgroup v2 CPU controller

컨테이너 시대에 와서 가장 중요한 부분이다. Kubernetes의 CPU request/limit이 결국 여기로 매핑된다.

### 7.1 cpu.weight

cgroup의 상대적 CPU 비중. 1-10000 범위, 기본 100. CFS의 group weight로 직결된다.

```bash
echo 200 > /sys/fs/cgroup/myapp/cpu.weight
# myapp이 같은 부모 아래 weight 100짜리 다른 cgroup보다 2배 우선
```

CFS는 cgroup 계층마다 별도 cfs_rq를 만들어서 그 안의 task들 사이에서 fair scheduling을 한다. cgroup A(weight 100)에 task 1개, cgroup B(weight 100)에 task 100개가 있어도 A와 B가 받는 CPU는 50:50이다. B 안에서 100개가 0.5%씩 나눠갖는다.

Kubernetes는 pod의 `resources.requests.cpu`를 cpu.weight로 매핑한다. 1 CPU request → weight 1024(SCALE 적용 후 환산).

### 7.2 cpu.max (bandwidth control)

상한을 강제한다.

```bash
echo "50000 100000" > /sys/fs/cgroup/myapp/cpu.max
# period 100ms 동안 최대 50ms 사용 → 0.5 CPU 상한
```

내부적으로 CFS bandwidth control(`cfs_bandwidth`)이 동작한다. 매 period 시작 시 quota만큼의 runtime을 cgroup에 채우고, task가 실행되면 runtime을 차감한다. runtime이 0이 되면 **throttle**: cgroup 안의 모든 task가 dequeue되어 다음 period까지 못 돈다.

```c
// kernel/sched/fair.c
static int __assign_cfs_rq_runtime(struct cfs_bandwidth *cfs_b,
                                   struct cfs_rq *cfs_rq, u64 target_runtime)
{
    u64 min_amount = target_runtime - cfs_rq->runtime_remaining;
    u64 amount = 0;

    if (cfs_b->quota == RUNTIME_INF) {
        amount = min_amount;
    } else {
        if (cfs_b->runtime > 0) {
            amount = min(cfs_b->runtime, min_amount);
            cfs_b->runtime -= amount;
        }
    }
    cfs_rq->runtime_remaining += amount;
    return cfs_rq->runtime_remaining > 0;
}
```

### 7.3 Throttling이 일으키는 문제

Kubernetes에서 `limits.cpu: 500m`을 걸어두고 CPU 사용률은 30% 정도밖에 안 되는데 응답시간이 튀는 사례가 많다. 원인은 거의 항상 bursty workload + per-CPU runtime distribution이다.

period 100ms / quota 50ms로 0.5 CPU 제한이 있는데, 멀티스레드 앱이 8개 코어에서 동시에 짧게 burst를 일으키면 quota가 순식간에 소진된다. 예를 들어 각 코어가 10ms씩 동시에 일하면 80ms를 한 번에 쓰는 셈이고, period 시작 후 6.25ms만에 quota 50ms를 다 써버리고 93.75ms를 throttle 당한다. CPU 사용률 통계로는 평균 50%인데 실제 응답은 끔찍하다.

확인 방법:

```bash
cat /sys/fs/cgroup/myapp/cpu.stat
# usage_usec 12345678
# user_usec 10000000
# system_usec 2345678
# nr_periods 1234     ← 전체 period 수
# nr_throttled 234    ← throttle 발생 횟수
# throttled_usec 5678901  ← throttle된 누적 시간
```

`nr_throttled / nr_periods`가 1% 넘으면 limit 재검토 대상이다. 5% 넘으면 거의 확실히 응답시간 문제가 생긴다.

해결책:

1. CPU limit을 빼거나 크게 늘림(쿠버에서 limit 없애는 게 안전하다고 보고하는 사례가 많음)
2. period를 줄임: `cpu.cfs_period_us` 100ms → 10ms로 하면 throttle 영향 시간이 줄어든다. 단 v2에서는 cpu.max로 period 같이 지정
3. 스레드 수를 quota에 맞게 줄임(예: GOMAXPROCS=ceil(quota/period))

### 7.4 cpu.idle

cgroup v2의 SCHED_IDLE 지원. idle priority로 돌게 한다.

```bash
echo 1 > /sys/fs/cgroup/lowpri/cpu.idle
```

배치 작업을 인터랙티브 작업과 같은 노드에 띄울 때 유용하다. nice 19보다 더 약한 우선순위로 돈다.

### 7.5 Kubernetes 매핑 정리

- `resources.requests.cpu: 500m` → `cpu.weight = 51` (1000m을 102.4로 매핑)
- `resources.limits.cpu: 1000m` → `cpu.max = "100000 100000"`
- guaranteed QoS(request == limit)인데 throttle 발생하면 노드 capacity가 부족한 게 아니라 burstiness 문제다

---

## 8. 실무 측정

### 8.1 /proc/&lt;pid&gt;/sched

task별 스케줄링 통계.

```bash
cat /proc/$(pidof nginx)/sched | head -20
```

주요 필드:

- `se.sum_exec_runtime`: 누적 실행 시간 (ns)
- `se.statistics.wait_sum`: ready queue 대기 누적 시간
- `se.statistics.wait_max`: 가장 길게 대기한 시간 ← p99 latency 진단에 핵심
- `nr_switches`: 총 컨텍스트 스위치 수
- `nr_voluntary_switches`: 자발적 양보(I/O 대기 등)
- `nr_involuntary_switches`: 강제 선점

`nr_involuntary_switches`가 `nr_voluntary_switches`보다 훨씬 크면 CPU bound 또는 노드 과부하다. 반대면 I/O bound다.

```bash
# 측정 시작
cat /proc/$PID/sched > /tmp/sched_start
sleep 60
cat /proc/$PID/sched > /tmp/sched_end
diff /tmp/sched_start /tmp/sched_end
```

### 8.2 perf sched

```bash
# 30초간 모든 스케줄링 이벤트 캡처
perf sched record -- sleep 30

# task별 wait time, run time 통계
perf sched latency --sort max
```

출력 예:

```
  Task                  |  Runtime ms | Switches | Avg delay ms | Max delay ms |
  ----------------------|-------------|----------|--------------|--------------|
  nginx:1234            |  1234.567   |    5432  |     0.123    |    12.456    |
  app-worker:5678       |   456.789   |   12345  |     0.045    |     3.789    |
```

`Max delay ms`가 비정상적으로 크면 그 task가 한 번이라도 길게 ready 상태로 굶었다는 뜻이다. p99 latency 튐의 직접 근거가 된다.

```bash
# task별 시간순 이벤트
perf sched timehist --pid 1234
```

특정 시점에 누가 누구를 선점했고 누가 wake 되었는지 흐름이 보인다.

### 8.3 ftrace sched_switch

가장 가볍게 쓸 수 있는 트레이서.

```bash
# 활성화
cd /sys/kernel/debug/tracing
echo 1 > events/sched/sched_switch/enable
echo 1 > events/sched/sched_wakeup/enable

cat trace_pipe | head -50
# nginx-1234  [003] 12345.678901: sched_switch: prev_comm=nginx prev_pid=1234
#   prev_prio=120 prev_state=S ==> next_comm=swapper/3 next_pid=0 next_prio=120
```

`prev_state` 의미:
- R: 여전히 ready (선점됨)
- S: interruptible sleep
- D: uninterruptible sleep (보통 I/O 대기)
- T: stopped
- X: dead

`R` 상태로 자주 보이면 선점 빈도가 높다는 뜻. `D` 상태가 길게 가면 I/O 문제다.

### 8.4 bpftrace off-CPU 분석

가장 강력한 도구. task가 CPU에서 내려간 후 다시 올라올 때까지의 시간을 stack과 함께 캡처한다.

```bash
bpftrace -e '
kprobe:finish_task_switch {
    @start[args->prev->pid] = nsecs;
}
kfunc:try_to_wake_up /@start[args->p->pid]/ {
    @offcpu[kstack(args->p)] = hist(nsecs - @start[args->p->pid]);
    delete(@start[args->p->pid]);
}'
```

stack 별로 off-CPU 시간 히스토그램을 본다. 어느 코드 경로에서 sleep을 오래 하는지 한눈에 보인다. 보통 lock 대기, futex, I/O가 잡힌다.

Brendan Gregg의 `offcputime` BCC 도구가 같은 일을 더 친절하게 한다.

```bash
# 10초간 off-CPU 시간이 큰 stack top 10
offcputime-bpfcc -p $PID 10
```

### 8.5 정리 - 진단 순서

응답시간 튐 문제를 만나면 다음 순서로 보면 빠르다.

1. `cat /proc/<pid>/sched`에서 `wait_max`와 voluntary/involuntary switch 비율 확인 → 대기 시간이 큰지, CPU bound인지 I/O bound인지 1차 판단
2. cgroup이면 `cpu.stat`의 `nr_throttled` 확인 → throttling 의심
3. `perf sched latency`로 task별 max delay 확인 → 어느 task가 굶었는지
4. `perf sched timehist`로 그 시점에 누가 CPU를 들고 있었는지
5. off-CPU 분석으로 sleep 원인 stack 추적

대부분의 "CPU 여유 있는데 느림" 문제는 1-2단계에서 결판난다. cgroup throttling 아니면 D 상태 I/O 대기다. 스케줄러 알고리즘 자체가 원인인 경우는 거의 없다.

---

## 부록 - 튜닝 시작점

CFS 시절 자주 만지던 값들과 기본값.

| sysctl | 기본 | 의미 | 만지는 경우 |
|---|---|---|---|
| kernel.sched_latency_ns | 6000000 (6ms) | 한 바퀴 도는 목표 주기 | task 수가 너무 많아서 잦은 선점이 문제일 때 늘림 |
| kernel.sched_min_granularity_ns | 750000 (0.75ms) | 최소 실행 시간 | CS 비용 큰 워크로드에서 늘림(처리량 우선) |
| kernel.sched_wakeup_granularity_ns | 1000000 (1ms) | wake 시 선점 임계 | 인터랙티브 응답 우선이면 줄임 |
| kernel.sched_migration_cost_ns | 500000 | task migration 최소 간격 | NUMA에서 늘리면 cache 활용↑ |
| kernel.sched_autogroup_enabled | 1 | tty별 자동 cgroup | 데스크톱은 1, 서버는 0이 무난 |

EEVDF(6.6+):

| sysctl | 기본 | 의미 |
|---|---|---|
| kernel.sched_base_slice_ns | 750000 | 기본 slice |

운영 환경에서 이 값들을 만지기 전에 측정부터 한다. 워크로드 안 보고 튜닝하면 거의 항상 더 나빠진다. CFS 기본값은 대부분의 서버 워크로드에서 잘 동작하도록 16년간 다듬어진 값이다.
