---
title: "컨텍스트 스위칭 (Context Switching)"
tags: [OS, Process, Thread, Context Switching, PCB, 성능]
updated: 2026-03-24
---

# 컨텍스트 스위칭 (Context Switching)

CPU가 현재 실행 중인 프로세스(또는 스레드)를 멈추고, 다른 프로세스로 전환하는 과정이다. 운영체제 스케줄러가 이 전환을 담당한다.

멀티태스킹의 핵심 메커니즘이지만, 공짜가 아니다. 전환할 때마다 CPU 시간이 소모되고, 캐시가 날아간다.

---

## 전환 과정

컨텍스트 스위칭은 크게 두 단계로 나뉜다.

### 1단계: 현재 프로세스 상태 저장

현재 실행 중인 프로세스의 상태를 PCB(Process Control Block)에 저장한다.

PCB에 저장되는 정보:

| 항목 | 설명 |
|------|------|
| Program Counter (PC) | 다음에 실행할 명령어 주소 |
| CPU 레지스터 | 범용 레지스터, 스택 포인터 등 |
| 메모리 관리 정보 | 페이지 테이블 베이스 레지스터, 세그먼트 정보 |
| 프로세스 상태 | Running → Ready 또는 Waiting |
| I/O 상태 | 열린 파일 디스크립터, 소켓 등 |

### 2단계: 다음 프로세스 상태 복원

스케줄러가 선택한 다음 프로세스의 PCB에서 상태를 읽어와 CPU에 로드한다.

```
[프로세스 A 실행 중]
    │
    ▼
인터럽트 또는 시스템 콜 발생
    │
    ▼
커널 모드 진입
    │
    ▼
프로세스 A의 레지스터 → PCB_A에 저장
    │
    ▼
스케줄러: 다음 실행할 프로세스 B 선택
    │
    ▼
PCB_B에서 레지스터 → CPU에 복원
    │
    ▼
프로세스 B의 페이지 테이블로 전환 (CR3 레지스터 변경)
    │
    ▼
유저 모드 복귀
    │
    ▼
[프로세스 B 실행 시작]
```

Linux에서 실제 전환을 수행하는 핵심 함수는 `context_switch()`이고, 내부적으로 `switch_mm()`(메모리 공간 전환)과 `switch_to()`(레지스터 전환)를 호출한다.

---

## 컨텍스트 스위칭 비용

### 직접 비용 (Direct Cost)

PCB 저장/복원에 드는 CPU 사이클이다. 하드웨어와 OS에 따라 다르지만, 보통 수 마이크로초(μs) 수준이다.

x86-64 기준으로 레지스터 저장/복원 자체는 몇 백 나노초면 끝난다. 문제는 이게 전부가 아니라는 점이다.

### 간접 비용 (Indirect Cost) — 진짜 비싼 부분

직접 비용보다 간접 비용이 훨씬 크다. 실무에서 성능 문제를 일으키는 것도 이쪽이다.

**캐시 오염 (Cache Pollution)**

프로세스 A가 열심히 워밍업한 L1/L2/L3 캐시가 프로세스 B로 전환하면 쓸모없어진다. 프로세스 B가 자기 데이터를 캐시에 올리는 동안 캐시 미스가 연쇄적으로 발생한다.

L3 캐시 미스 한 번이 DRAM 접근으로 이어지면 약 100ns가 걸린다. 전환 직후 수백~수천 번의 캐시 미스가 터지면, 그 비용은 직접 비용의 수십 배에 달할 수 있다.

**TLB 플러시**

프로세스 간 전환 시 TLB(Translation Lookaside Buffer)가 무효화된다. 가상 주소 → 물리 주소 변환을 다시 해야 하므로 페이지 테이블 워킹이 발생한다.

PCID(Process Context ID)를 지원하는 CPU에서는 TLB 전체를 플러시하지 않고 PCID로 구분할 수 있다. Linux 4.14부터 PCID를 적극 활용한다.

**브랜치 예측기 오염**

CPU의 분기 예측기(Branch Predictor)도 프로세스별 패턴을 학습한다. 전환하면 이 예측 정보가 맞지 않아 파이프라인 스톨이 발생한다.

---

## 프로세스 전환 vs 스레드 전환

같은 프로세스 내의 스레드 간 전환은 프로세스 간 전환보다 가볍다.

| 비교 항목 | 프로세스 간 전환 | 스레드 간 전환 (같은 프로세스) |
|-----------|-----------------|-------------------------------|
| 레지스터 저장/복원 | 필요 | 필요 |
| 메모리 공간 전환 | 필요 (CR3 변경) | 불필요 (같은 주소 공간) |
| TLB 플러시 | 발생 (PCID 없으면 전체 플러시) | 불필요 |
| 캐시 영향 | 큼 (데이터 공유 없음) | 작음 (힙, 코드 영역 공유) |
| 페이지 테이블 전환 | 필요 | 불필요 |

핵심 차이는 **메모리 공간 전환 여부**다. 스레드는 같은 주소 공간을 공유하기 때문에 `switch_mm()`을 건너뛸 수 있고, TLB도 유지된다.

실측 기준으로 프로세스 간 전환은 약 3~5μs, 같은 프로세스 내 스레드 간 전환은 약 1~2μs 정도 걸린다. (하드웨어, 커널 버전에 따라 차이가 크다)

---

## Linux에서 컨텍스트 스위칭 측정

### /proc/[pid]/status

프로세스별 컨텍스트 스위칭 횟수를 확인할 수 있다.

```bash
# 특정 프로세스의 컨텍스트 스위칭 횟수
cat /proc/<pid>/status | grep ctxt

# 출력 예시
voluntary_ctxt_switches:     1523
nonvoluntary_ctxt_switches:  42
```

- `voluntary_ctxt_switches`: 프로세스가 스스로 CPU를 양보한 횟수 (I/O 대기, sleep 등)
- `nonvoluntary_ctxt_switches`: 타임 슬라이스가 만료되어 강제로 전환된 횟수

`nonvoluntary`가 비정상적으로 높으면 CPU 바운드 프로세스가 너무 많거나, 스케줄러 설정에 문제가 있을 수 있다.

### /proc/[pid]/sched

더 상세한 스케줄링 통계를 볼 수 있다.

```bash
cat /proc/<pid>/sched
# nr_switches, nr_voluntary_switches, nr_involuntary_switches 등 확인 가능
```

### vmstat

시스템 전체의 컨텍스트 스위칭 빈도를 확인한다.

```bash
vmstat 1
# cs 컬럼이 초당 컨텍스트 스위칭 횟수

procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 2  0      0 123456  12345 234567    0    0     0     0  150 3200 15  5 80  0  0
```

`cs` 값이 수만 이상으로 올라가면, 프로세스가 너무 많이 경쟁하고 있다는 신호다.

### perf

하드웨어 이벤트 레벨에서 컨텍스트 스위칭을 측정한다.

```bash
# 컨텍스트 스위칭 이벤트 카운트
perf stat -e context-switches,cpu-migrations -p <pid> sleep 10

# 출력 예시
Performance counter stats for process id '<pid>':
             2,847      context-switches
                12      cpu-migrations

      10.001234567 seconds time elapsed
```

```bash
# 컨텍스트 스위칭이 발생하는 시점을 기록
perf record -e context-switches -g -p <pid> sleep 10
perf report
```

`-g` 옵션을 주면 콜스택까지 기록되어, 어떤 코드 경로에서 컨텍스트 스위칭이 자주 발생하는지 추적할 수 있다.

### pidstat

프로세스별로 컨텍스트 스위칭 빈도를 실시간 모니터링한다.

```bash
# 1초 간격으로 특정 프로세스 모니터링
pidstat -w -p <pid> 1

# 출력 예시
Average:      UID       PID   cswch/s nvcswch/s  Command
Average:     1000     12345     45.00      2.00  my_server
```

`cswch/s`는 voluntary, `nvcswch/s`는 nonvoluntary 초당 횟수다.

---

## 컨텍스트 스위칭이 문제가 되는 상황

### 과도한 스레드 생성

스레드를 수천 개 만들면 스케줄러가 바빠지고, 실제 작업보다 전환에 더 많은 시간을 쓰게 된다. 이걸 **thrashing**이라 부르기도 한다.

```java
// 이렇게 하면 안 된다
for (int i = 0; i < 10000; i++) {
    new Thread(() -> doWork()).start();
}

// 스레드 풀을 써야 한다
ExecutorService pool = Executors.newFixedThreadPool(
    Runtime.getRuntime().availableProcessors()
);
for (int i = 0; i < 10000; i++) {
    pool.submit(() -> doWork());
}
```

### 락 경합 (Lock Contention)

여러 스레드가 같은 락을 잡으려고 경쟁하면, 락을 못 잡은 스레드는 블로킹되면서 voluntary 컨텍스트 스위칭이 발생한다.

```java
// synchronized 블록이 길면 경합이 심해진다
synchronized (lock) {
    // DB 조회, 외부 API 호출 등 오래 걸리는 작업
    // → 다른 스레드들이 줄줄이 대기하면서 컨텍스트 스위칭 폭발
}
```

`voluntary_ctxt_switches`가 급증하면 락 경합을 의심해야 한다.

### 빈번한 I/O

디스크 I/O나 네트워크 I/O를 기다릴 때마다 컨텍스트 스위칭이 발생한다. 비동기 I/O(epoll, io_uring)를 쓰면 스위칭 횟수를 줄일 수 있다.

---

## 컨텍스트 스위칭 비용 직접 측정하기

간단한 벤치마크로 스위칭 비용을 체감할 수 있다. 파이프로 연결된 두 프로세스가 번갈아 1바이트씩 주고받으면, 매번 컨텍스트 스위칭이 발생한다.

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

#define ITERATIONS 100000

int main() {
    int pipe1[2], pipe2[2];
    pipe(pipe1);
    pipe(pipe2);

    char buf = 'x';
    pid_t pid = fork();

    if (pid == 0) {
        // 자식 프로세스
        for (int i = 0; i < ITERATIONS; i++) {
            read(pipe1[0], &buf, 1);
            write(pipe2[1], &buf, 1);
        }
        exit(0);
    }

    // 부모 프로세스
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    for (int i = 0; i < ITERATIONS; i++) {
        write(pipe1[1], &buf, 1);
        read(pipe2[0], &buf, 1);
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) * 1e9
                   + (end.tv_nsec - start.tv_nsec);
    // 왕복 1회에 컨텍스트 스위칭 2번
    printf("컨텍스트 스위칭 1회 평균: %.0f ns\n",
           elapsed / (ITERATIONS * 2));

    return 0;
}
```

일반적인 Linux 서버에서 이 벤치마크를 돌리면 1~5μs 정도가 나온다. 여기에 캐시 워밍업 비용은 포함되지 않으므로, 실제 워크로드에서는 더 오래 걸린다.
