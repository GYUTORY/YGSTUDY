---
title: "가상 메모리 (Virtual Memory)"
tags: [OS, Virtual Memory, Paging, TLB, Page Fault, Swap, Linux]
updated: 2026-03-25
---

# 가상 메모리 (Virtual Memory)

프로세스마다 독립적인 메모리 공간을 제공하는 메커니즘이다. 각 프로세스는 자기만의 연속된 주소 공간을 갖고 있다고 생각하지만, 실제 물리 메모리에는 여기저기 흩어져 있다.

물리 메모리보다 큰 주소 공간을 사용할 수 있고, 프로세스 간 메모리 격리가 보장된다. 이게 없으면 프로세스 하나가 다른 프로세스의 메모리를 덮어쓰는 참사가 벌어진다.

---

## 페이징 (Paging)

가상 메모리의 기본 단위다. 가상 주소 공간을 고정 크기 블록(페이지)으로 나누고, 물리 메모리도 같은 크기의 프레임으로 나눈다. 리눅스 기본 페이지 크기는 4KB다.

```
가상 주소 공간              물리 메모리
┌─────────┐               ┌─────────┐
│ Page 0  │ ──────────→   │ Frame 5 │
├─────────┤               ├─────────┤
│ Page 1  │ ──────────→   │ Frame 2 │
├─────────┤               ├─────────┤
│ Page 2  │ ── (디스크) │ Frame 0 │
├─────────┤               ├─────────┤
│ Page 3  │ ──────────→   │ Frame 7 │
└─────────┘               └─────────┘
```

가상 주소는 두 부분으로 나뉜다.

| 구성 요소 | 역할 |
|-----------|------|
| 페이지 번호 (Page Number) | 페이지 테이블의 인덱스 |
| 오프셋 (Offset) | 페이지 내에서의 위치 |

4KB 페이지 기준으로 하위 12비트가 오프셋, 나머지가 페이지 번호다. 64비트 시스템에서는 실제로 48비트만 가상 주소로 사용하는 경우가 많다 (x86-64 기준).

---

## 페이지 테이블 (Page Table)

가상 페이지 번호를 물리 프레임 번호로 변환하는 매핑 테이블이다. 프로세스마다 별도의 페이지 테이블을 갖는다.

### 페이지 테이블 엔트리 (PTE)

각 엔트리에는 프레임 번호 외에 여러 플래그가 들어있다.

| 플래그 | 의미 |
|--------|------|
| Present/Valid | 해당 페이지가 물리 메모리에 있는지 |
| Read/Write | 쓰기 가능 여부 |
| User/Supervisor | 유저 모드에서 접근 가능한지 |
| Dirty | 페이지가 수정됐는지 |
| Accessed | 최근에 접근됐는지 |

### 멀티 레벨 페이지 테이블

64비트 시스템에서 단일 페이지 테이블은 크기가 비현실적이다. 48비트 주소 공간 기준, 단일 테이블이면 엔트리가 2^36개 필요하다.

리눅스(x86-64)는 4단계 또는 5단계 페이지 테이블을 사용한다.

```
가상 주소 (48비트)
┌──────┬──────┬──────┬──────┬────────┐
│ PGD  │ PUD  │ PMD  │ PTE  │ Offset │
│ 9bit │ 9bit │ 9bit │ 9bit │ 12bit  │
└──┬───┴──┬───┴──┬───┴──┬───┴────────┘
   │      │      │      │
   ▼      ▼      ▼      ▼
 1단계  2단계  3단계  4단계 → 물리 프레임
```

각 단계는 512개 엔트리(9비트)를 가진 테이블이다. 실제로 사용하는 주소 범위만 테이블을 할당하므로 메모리 낭비를 줄인다.

---

## TLB (Translation Lookaside Buffer)

페이지 테이블 조회는 메모리 접근이 여러 번 필요하다. 4단계 페이지 테이블이면 한 번의 주소 변환에 메모리 접근이 4번 발생한다. 이걸 매번 하면 성능이 바닥을 친다.

TLB는 최근 사용된 페이지 테이블 엔트리를 캐싱하는 하드웨어다. CPU 내부에 있어서 접근이 빠르다.

```
가상 주소 → TLB 조회
              │
       ┌──────┴──────┐
     Hit            Miss
       │              │
  물리 주소 반환   페이지 테이블 조회
                      │
                 TLB에 캐싱
                      │
                 물리 주소 반환
```

TLB 히트율이 성능에 직접적인 영향을 미친다. 일반적인 워크로드에서 히트율은 99% 이상이다.

### TLB 관련 주의사항

- **컨텍스트 스위칭 시 TLB 플러시**: 프로세스가 바뀌면 TLB를 비워야 한다. ASID(Address Space ID)를 지원하는 CPU는 프로세스별로 TLB 엔트리를 구분해서 전체 플러시를 피할 수 있다.
- **Huge Page**: 4KB 대신 2MB나 1GB 페이지를 사용하면 TLB 엔트리 하나로 더 넓은 범위를 커버한다. 데이터베이스나 JVM처럼 큰 메모리를 쓰는 애플리케이션에서 효과가 크다.

```bash
# 리눅스에서 Huge Page 설정 확인
cat /proc/meminfo | grep Huge

# Transparent Huge Pages 상태 확인
cat /sys/kernel/mm/transparent_hugepage/enabled
```

---

## 페이지 폴트 (Page Fault)

프로세스가 접근하려는 페이지가 물리 메모리에 없을 때 발생한다. CPU가 인터럽트를 발생시키고, 커널의 페이지 폴트 핸들러가 처리한다.

### 종류

| 종류 | 원인 | 처리 |
|------|------|------|
| Minor (Soft) | 페이지가 메모리에 있지만 PTE가 매핑되지 않은 상태 | PTE만 갱신하면 됨. 디스크 I/O 없음 |
| Major (Hard) | 페이지가 디스크(스왑)에 있어서 읽어와야 하는 상태 | 디스크 I/O 발생. 느림 |
| Invalid | 잘못된 주소 접근 | SIGSEGV (Segmentation Fault) |

Minor 폴트는 큰 문제가 아니다. 디맨드 페이징이나 Copy-on-Write에서 정상적으로 발생한다. Major 폴트가 빈번하면 성능 문제가 생긴다.

```bash
# 프로세스별 페이지 폴트 확인
ps -o pid,min_flt,maj_flt -p <PID>

# 실시간 모니터링
pidstat -r 1

# perf로 페이지 폴트 추적
perf stat -e page-faults,minor-faults,major-faults -p <PID>
```

---

## 디맨드 페이징 (Demand Paging)

프로세스 시작 시 모든 페이지를 메모리에 올리지 않는다. 실제로 접근할 때 페이지 폴트가 발생하고, 그때 메모리에 올린다.

`malloc()`으로 메모리를 할당해도 실제 물리 메모리를 쓰지 않는다. 가상 주소 공간만 예약하고, 처음 접근할 때 물리 프레임이 할당된다.

```c
// 1GB 할당 - 이 시점에서는 물리 메모리를 안 쓴다
char *buf = malloc(1024 * 1024 * 1024);

// 첫 접근 시 페이지 폴트 → 물리 프레임 할당
buf[0] = 'A';
```

이 때문에 `top`이나 `ps`에서 보이는 VIRT(가상 메모리)와 RSS(실제 사용 물리 메모리)가 크게 차이나는 경우가 있다. VIRT가 크다고 문제가 되는 건 아니다. RSS를 봐야 한다.

### Copy-on-Write (COW)

`fork()` 시 부모 프로세스의 메모리를 복사하지 않고, 페이지 테이블만 공유한다. 어느 한쪽이 페이지를 수정하면 그때 복사한다.

```
fork() 직후:
부모 PTE ──→ Frame A (읽기 전용으로 표시)
자식 PTE ──→ Frame A (같은 프레임 공유)

자식이 쓰기 시도:
부모 PTE ──→ Frame A
자식 PTE ──→ Frame B (새 프레임에 복사 후 수정)
```

---

## 페이지 교체 알고리즘

물리 메모리가 부족하면 기존 페이지를 내보내고 새 페이지를 올려야 한다. 어떤 페이지를 내보낼지 결정하는 게 페이지 교체 알고리즘이다.

### OPT (Optimal)

앞으로 가장 오랫동안 사용되지 않을 페이지를 교체한다. 미래를 알아야 하므로 실제 구현은 불가능하다. 다른 알고리즘의 성능 비교 기준으로 쓰인다.

### FIFO

가장 먼저 들어온 페이지를 교체한다. 구현이 단순하지만, 오래 전에 올라왔더라도 자주 쓰는 페이지를 쫓아낼 수 있다. Belady의 이상 현상(프레임 수를 늘렸는데 폴트가 늘어나는 현상)이 발생할 수 있다.

### LRU (Least Recently Used)

가장 오래 전에 사용된 페이지를 교체한다. OPT에 가까운 성능을 보이지만, 정확한 구현에는 타임스탬프 관리 비용이 크다.

하드웨어 지원 없이 순수 LRU를 구현하면 매 메모리 접근마다 시간 기록이 필요해서 현실적이지 않다.

### Clock (Second Chance)

리눅스 커널이 실제로 사용하는 방식의 기반이다. LRU를 근사(approximation)하면서 오버헤드를 줄인다.

```
원형 버퍼에 페이지를 배치하고, 포인터가 순회한다.

    ┌→ Page A (ref=1) → 접근됨, ref=0으로 바꾸고 넘어감
    │  Page B (ref=0) → 교체 대상
    │  Page C (ref=1)
    └─ Page D (ref=0)
```

동작 방식:
1. 포인터가 가리키는 페이지의 참조 비트(Accessed bit) 확인
2. 참조 비트가 1이면 0으로 바꾸고 다음으로 이동 (한 번 더 기회를 줌)
3. 참조 비트가 0이면 교체 대상으로 선택

### 리눅스 커널의 실제 구현

리눅스는 Active/Inactive 두 개의 리스트를 사용한다. LRU와 Clock을 결합한 형태다.

```
Active List:   자주 접근되는 페이지
Inactive List: 한동안 접근되지 않은 페이지

승격: Inactive → Active (재접근 시)
강등: Active → Inactive (메모리 압박 시)
회수: Inactive 리스트의 꼬리에서 페이지를 회수
```

파일 캐시 페이지와 익명(Anonymous) 페이지를 별도 리스트로 관리한다. `vm.swappiness` 파라미터가 이 둘 사이의 회수 비율을 조절한다.

---

## 스왑 (Swap)

물리 메모리가 부족할 때, 사용 빈도가 낮은 페이지를 디스크로 내보내는 메커니즘이다. 리눅스에서는 스왑 파티션이나 스왑 파일로 구성한다.

```bash
# 스왑 상태 확인
swapon --show
free -h

# 스왑 파일 생성 (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# /etc/fstab에 영구 등록
# /swapfile none swap sw 0 0
```

### 스왑이 발생하면 어떻게 되나

Major 페이지 폴트가 발생하고, 디스크 I/O를 기다려야 한다. SSD 기준으로도 메모리 접근 대비 수천 배 느리다. 서버에서 스왑이 활발히 일어나면 응답 시간이 급격히 나빠진다.

스왑이 아예 없으면 OOM Killer가 프로세스를 강제 종료한다. 프로덕션 서버에서는 스왑을 적당히 두되, 스왑 사용이 증가하면 알림을 걸어야 한다.

---

## Linux vm 관련 커널 파라미터

`/proc/sys/vm/` 아래에 가상 메모리 관련 파라미터가 있다.

### vm.swappiness

```bash
# 현재 값 확인
cat /proc/sys/vm/swappiness

# 변경 (0~200, 기본값 60)
sudo sysctl vm.swappiness=10
```

| 값 | 동작 |
|----|------|
| 0 | 스왑을 거의 안 함. OOM이 발생할 수 있음 |
| 10~30 | DB 서버에서 많이 쓰는 값. 파일 캐시를 우선 회수 |
| 60 | 기본값 |
| 100 | 익명 페이지와 파일 캐시를 동등하게 회수 |

데이터베이스 서버에서는 10~30으로 낮추는 경우가 많다. 쿼리 성능에 직접적인 영향을 미치기 때문이다.

### vm.overcommit_memory

```bash
cat /proc/sys/vm/overcommit_memory
```

| 값 | 동작 |
|----|------|
| 0 | 기본값. 커널이 적당히 판단해서 오버커밋 허용 |
| 1 | 항상 허용. `malloc()`이 실패하지 않음 |
| 2 | 물리 메모리 + 스왑의 `overcommit_ratio`% 이상 할당 불가 |

Redis는 fork() 시 COW를 쓰는데, `overcommit_memory=0`이면 fork가 실패할 수 있다. Redis 공식 문서에서 `vm.overcommit_memory=1`을 권장한다.

### vm.dirty_ratio / vm.dirty_background_ratio

```bash
# 더티 페이지 비율
cat /proc/sys/vm/dirty_ratio              # 기본 20(%)
cat /proc/sys/vm/dirty_background_ratio   # 기본 10(%)
```

- `dirty_background_ratio`: 이 비율을 넘으면 백그라운드에서 디스크 쓰기 시작
- `dirty_ratio`: 이 비율을 넘으면 프로세스가 직접 디스크에 쓰기 시작 (블로킹)

I/O가 많은 서버에서 `dirty_ratio`에 도달하면 쓰기 지연이 발생한다. 로그가 밀리거나 응답이 느려지는 원인이 될 수 있다.

### vm.min_free_kbytes

```bash
cat /proc/sys/vm/min_free_kbytes
```

커널이 유지하려는 최소 여유 메모리 크기다. 이 값보다 여유 메모리가 적어지면 적극적으로 페이지를 회수한다.

너무 낮으면 메모리 할당 실패가 발생할 수 있고, 너무 높으면 사용 가능한 메모리가 줄어든다.

---

## 실무에서 page fault 추적 및 swap 문제 대응

### 문제 징후 파악

서버 응답이 갑자기 느려졌을 때, 메모리부터 의심해야 하는 경우가 있다.

```bash
# 메모리 상태 한눈에 보기
free -h

# 스왑 사용량 추이 확인
vmstat 1

# vmstat 출력에서 확인할 항목
# si (swap in): 디스크 → 메모리
# so (swap out): 메모리 → 디스크
# si/so가 지속적으로 0이 아니면 스왑이 활발한 것
```

### 어떤 프로세스가 메모리를 잡아먹는지 확인

```bash
# RSS 기준 상위 프로세스
ps aux --sort=-%mem | head -20

# 특정 프로세스의 메모리 상세
cat /proc/<PID>/status | grep -E "VmRSS|VmSwap|VmSize"

# 모든 프로세스의 스왑 사용량 확인
for pid in /proc/[0-9]*; do
    name=$(cat $pid/comm 2>/dev/null)
    swap=$(grep VmSwap $pid/status 2>/dev/null | awk '{print $2}')
    [ -n "$swap" ] && [ "$swap" -gt 0 ] && echo "$swap kB - $name ($(basename $pid))"
done | sort -rn | head -20
```

### 페이지 폴트 원인 분석

```bash
# perf로 페이지 폴트가 발생하는 코드 위치 추적
perf record -e page-faults -p <PID> -g -- sleep 10
perf report

# strace로 mmap 호출 추적
strace -e mmap,mprotect,brk -p <PID>
```

### 대응 방법

**스왑 사용량이 계속 증가하는 경우**

1. 어떤 프로세스가 메모리를 많이 쓰는지 확인
2. 메모리 누수인지, 정상적인 사용량 증가인지 판단
3. 메모리 누수라면 애플리케이션 수준에서 수정
4. 정상적인 증가라면 메모리 증설 또는 서비스 분산

**OOM Killer가 프로세스를 죽이는 경우**

```bash
# OOM 로그 확인
dmesg | grep -i "oom\|killed process"
journalctl -k | grep -i oom

# 특정 프로세스의 OOM 점수 확인 (낮을수록 죽을 확률 낮음)
cat /proc/<PID>/oom_score

# 중요 프로세스는 OOM Killer 대상에서 제외
echo -1000 > /proc/<PID>/oom_score_adj
```

**cgroup으로 메모리 제한**

컨테이너 환경에서는 cgroup으로 프로세스 그룹의 메모리를 제한한다. 쿠버네티스의 `resources.limits.memory`가 이걸 쓴다.

```bash
# cgroup v2 메모리 사용량 확인
cat /sys/fs/cgroup/<group>/memory.current
cat /sys/fs/cgroup/<group>/memory.max
```

컨테이너 내부에서 `free`를 치면 호스트 전체 메모리가 보인다. 컨테이너의 실제 메모리 제한은 cgroup에서 확인해야 한다.

---

## 정리

가상 메모리는 OS가 프로세스에게 독립적인 메모리 공간을 제공하는 핵심 메커니즘이다.

| 개념 | 핵심 |
|------|------|
| 페이징 | 가상 주소를 고정 크기 페이지로 나눠서 물리 프레임에 매핑 |
| 페이지 테이블 | 가상→물리 주소 변환 테이블. 멀티 레벨로 구성 |
| TLB | 주소 변환 캐시. 히트율이 성능을 좌우 |
| 페이지 폴트 | Minor는 정상, Major가 빈번하면 성능 문제 |
| 디맨드 페이징 | 실제 접근할 때 메모리 할당. VIRT와 RSS 차이의 원인 |
| 페이지 교체 | 리눅스는 Active/Inactive 리스트 기반 LRU 근사 |
| 스왑 | 메모리 부족 시 디스크 사용. 활발하면 성능 급락 |

서버 운영 시 `vmstat`의 si/so, `free`의 swap 항목, `dmesg`의 OOM 로그를 주기적으로 확인하는 습관이 필요하다.
