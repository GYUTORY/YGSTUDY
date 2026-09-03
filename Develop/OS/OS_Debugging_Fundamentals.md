---
title: OS 레벨 진단 패턴
tags: [os, linux, performance, monitoring, observability, backend]
updated: 2026-09-03
---

## 가상 메모리 구조와 /proc/meminfo

리눅스는 물리 메모리가 부족해도 프로세스가 즉시 죽지 않는다. 스왑과 페이지 캐시라는 두 완충층이 있기 때문이다. 이 구조를 모르면 `/proc/meminfo`를 읽어도 뭐가 문제인지 모른다.

`/proc/meminfo`의 핵심 항목:

```
MemTotal:       16384000 kB   # 물리 메모리 전체
MemFree:          512000 kB   # 아무도 안 쓰는 메모리
MemAvailable:    8192000 kB   # 실제로 쓸 수 있는 메모리 (캐시 회수 가능분 포함)
Buffers:          512000 kB   # 블록 장치 버퍼
Cached:          6144000 kB   # 파일 페이지 캐시
SwapTotal:       8192000 kB
SwapFree:        7168000 kB
SwapCached:       128000 kB   # 스왑에서 읽어왔지만 아직 스왑에도 남은 페이지
Dirty:             32000 kB   # 아직 디스크에 안 쓴 페이지
Writeback:           512 kB   # 지금 쓰는 중인 페이지
Slab:             512000 kB   # 커널 내부 캐시
```

`MemFree`가 낮아도 `MemAvailable`이 충분하면 문제없다. 커널이 파일 캐시를 반납할 수 있어서다. `MemAvailable`까지 낮고 `SwapFree`도 줄고 있으면 실제 메모리 압박 상태다.

`Dirty`가 수백 MB씩 쌓이고 있으면 쓰기 플러시가 I/O를 못 따라가는 것이다. 이 상태에서 `fsync`를 부르는 호출이 들어오면 갑자기 레이턴시가 튄다.

```bash
# 메모리 현황을 1초 간격으로 추적
watch -n 1 'grep -E "MemAvailable|SwapFree|Dirty|Writeback" /proc/meminfo'

# 프로세스별 메모리 상세 (RSS, PSS)
cat /proc/<pid>/status | grep -E "VmRSS|VmPeak|VmSize"
cat /proc/<pid>/smaps_rollup  # PSS 기준 실제 점유량
```

RSS는 공유 라이브러리를 포함하지 않고, PSS는 공유 메모리를 프로세스 수로 나눠 할당한다. 여러 프로세스의 RSS를 더하면 물리 메모리 사용량을 과다 계상한다. `smaps_rollup`의 `Pss` 값을 써야 정확하다.

---

## vmstat·iostat으로 CPU와 I/O 병목 구분

서버가 느릴 때 CPU 문제인지 I/O 문제인지 먼저 구분해야 한다. `vmstat`으로 시작한다.

```bash
vmstat 1 10
```

```
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 2  0      0 512000 131072 4096000    0    0     0    32  850 1200 45 10 45  0  0
 0  5      0 256000 131072 4096000    0    0  8192  4096 1200 2000  5  3 12 80  0
```

`b` (blocked): I/O를 기다리는 프로세스 수. 이 값이 계속 0보다 크면 디스크나 네트워크가 막혔다.

`wa` (wait): CPU가 I/O 완료를 기다린 시간 비율. 두 번째 줄에서 80%다. CPU는 놀고 있지만 서버는 느린 상태다. CPU 코어를 늘려도 해결이 안 된다.

`r` (run queue): 실행 대기 중인 프로세스 수. CPU 코어 수보다 지속적으로 크면 CPU가 병목이다.

I/O가 의심되면 `iostat`으로 디바이스별로 파고든다.

```bash
iostat -xz 1
```

```
Device            r/s     w/s    rkB/s    wkB/s   await r_await w_await  util
sda              0.00  512.00     0.00 16384.00   32.00    0.00   32.00 98.00
```

`util` 98%는 이 디스크가 포화 상태라는 뜻이다. `await`은 요청 제출부터 완료까지 걸린 시간(ms)이고, `r_await`과 `w_await`으로 읽기·쓰기를 분리해서 볼 수 있다.

SSD라면 `await` 1ms 이하가 정상이다. HDD는 5~10ms. 이 값이 100ms를 넘으면 큐가 쌓이고 있다는 신호다.

---

## strace로 시스템 콜 추적

애플리케이션이 왜 느린지 코드만 봐서는 모를 때 쓴다. 프로세스가 커널에 뭘 요청하는지 직접 보는 것이다.

```bash
strace -p <pid> -T -e trace=network,file 2>&1 | head -100
```

`-T`: 각 시스템 콜 소요 시간을 `<0.003456>` 형태로 붙여준다.  
`-e trace=network,file`: 네트워크·파일 관련 콜만 본다. 안 걸면 너무 많이 나온다.

특정 콜이 느린지 통계로 보려면:

```bash
strace -p <pid> -c -f 2>&1 &
sleep 30
kill -INT $!
```

```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 45.32    0.453200         453      1000           epoll_wait
 32.10    0.321000          64      5000           read
 15.20    0.152000       30400         5         4 connect
  7.38    0.073800          49      1500           write
```

`connect`가 5번밖에 없는데 30초나 걸렸다면 타임아웃이 날 때까지 기다린 것이다. `-e trace=connect`로 좁히면 어느 주소로 연결하다 막혔는지 보인다.

주의점: `strace`는 프로세스에 `ptrace`를 걸어서 모든 시스템 콜에서 멈추게 한다. 운영 서버에 걸면 성능이 수십 배 느려질 수 있다. 짧게 걸고 바로 뗀다.

---

## /proc/pid/fd 파일 디스크립터 누수 탐지

소켓이나 파일을 열고 닫지 않으면 `fd` 수가 계속 늘어난다. 일정 시간이 지나면 `Too many open files` 에러가 난다.

```bash
# 현재 fd 수 확인
ls -l /proc/<pid>/fd | wc -l

# fd 종류별 분포
ls -la /proc/<pid>/fd/ | awk '{print $NF}' | grep -oP '(socket|pipe|anon_inode|/\S+)' | sort | uniq -c | sort -rn
```

출력 예시:
```
4892 socket:[...]
 312 /dev/null
  44 pipe:[...]
   8 anon_inode:[eventpoll]
```

소켓이 5000개 가까이 열려 있다면 문제다. 실제로 사용 중인 소켓인지 `ss`로 확인한다:

```bash
ss -tp | grep <pid>
```

`ss` 결과에는 없는데 `/proc/pid/fd`에는 있는 소켓은 이미 피어가 닫았는데 코드에서 `close()`를 안 한 것이다.

fd 수가 한도에 걸리기 전에 경보를 받으려면:

```bash
# 시스템 한도 확인
cat /proc/sys/fs/file-max

# 프로세스 한도 확인 (ulimit -n 과 동일)
cat /proc/<pid>/limits | grep "open files"
```

프로세스 fd 수가 소프트 리밋의 80% 이상이면 누수를 의심할 시점이다.

---

## OOM killer 로그 해석

물리 메모리와 스왑이 전부 소진되면 커널이 프로세스 하나를 골라 죽인다. 서버 프로세스가 갑자기 사라지는 현상의 원인 중 하나다.

```bash
# 커널 메시지에서 OOM 이벤트 확인
dmesg | grep -E "oom_kill|Out of memory|Killed process"

# systemd 환경
journalctl -k | grep -E "oom|killed"
```

전형적인 OOM 로그:

```
[ 8432.914751] Out of memory: Kill process 12345 (java) score 892 or sacrifice child
[ 8432.914758] Killed process 12345 (java) total-vm:16777216kB, anon-rss:14680064kB, file-rss:131072kB, shmem-rss:0kB
[ 8432.914762] oom_reaper: reaped process 12345 (java), now anon-rss:0kB, file-rss:0kB, shmem-rss:0kB
```

`score 892`: `oom_score_adj`와 메모리 점유율을 합산한 값이다. 1000에 가까울수록 먼저 죽는다. 죽이면 안 되는 프로세스(DB 등)는 미리 낮춰 놓는다:

```bash
echo -500 > /proc/<pid>/oom_score_adj   # -1000 ~ 1000, 낮을수록 보호
```

`anon-rss`가 크고 `file-rss`가 작은 경우: 힙 할당이 많은 프로세스다(JVM, 애플리케이션 서버). 반대면 파일을 많이 mmap한 경우다.

OOM이 반복된다면 어느 시점에 메모리가 급증했는지 찾아야 한다. `dmesg` 타임스탬프 직전의 애플리케이션 로그와 비교한다. 타임스탬프는 부팅 후 초 단위라 절대 시각으로 환산해야 한다:

```bash
# 부팅 시각 기준으로 dmesg 타임스탬프 8432초를 절대 시각으로 환산
date -d "@$(($(date +%s) - $(awk '{print int($1)}' /proc/uptime) + 8432))"
```

---

## 데드락 탐지

### JVM (jstack)

JVM 프로세스가 CPU는 낮은데 스레드가 전부 멈춘 것처럼 보일 때 쓴다.

```bash
jstack <pid> > /tmp/thread_dump.txt
grep -A 5 "BLOCKED" /tmp/thread_dump.txt
grep -A 3 "Found.*deadlock" /tmp/thread_dump.txt
```

jstack은 `Found one Java-level deadlock:` 섹션을 자동으로 만들어준다:

```
Found one Java-level deadlock:
=============================
"thread-pool-1":
  waiting to lock monitor 0x00007f3c4c004e28 (object 0x00000000f2012a30, a com.example.LockA),
  which is held by "thread-pool-2"
"thread-pool-2":
  waiting to lock monitor 0x00007f3c4c0052c8 (object 0x00000000f2012b40, a com.example.LockB),
  which is held by "thread-pool-1"
```

`thread-pool-1`이 LockA를 잡고 LockB를 기다리고, `thread-pool-2`가 LockB를 잡고 LockA를 기다린다. 락 획득 순서가 불일치한 전형적인 데드락이다.

스레드 덤프는 순간 스냅샷이라 확신이 안 서면 10초 간격으로 세 번 찍어 비교한다. 세 번 모두 같은 스레드가 `BLOCKED` 상태로 같은 모니터를 기다리고 있으면 데드락이다.

### C/C++ (gdb)

```bash
gdb -p <pid>
(gdb) thread apply all bt
```

각 스레드의 콜스택이 출력된다. `pthread_mutex_lock`이나 `futex`에서 멈춘 스레드를 찾는다:

```
Thread 3 (Thread 0x7f3c4c000700 (LWP 12348)):
#0  0x00007f3c4b8d5a7d in pthread_mutex_lock () from /lib/x86_64-linux-gnu/libpthread.so.0
#1  0x0000000000401234 in acquire_resource_b ()
#2  0x0000000000401100 in worker_thread_a ()

Thread 2 (Thread 0x7f3c4c001700 (LWP 12347)):
#0  0x00007f3c4b8d5a7d in pthread_mutex_lock () from /lib/x86_64-linux-gnu/libpthread.so.0
#1  0x0000000000401890 in acquire_resource_a ()
#2  0x0000000000401200 in worker_thread_b ()
```

어느 스레드가 어느 락에서 멈췄는지 콜스택으로 추적한다. gdb는 실행 중인 프로세스를 일시 정지시키므로 프로덕션에서는 최소한의 시간만 붙인다.

Go는 별도 도구 없이 `SIGQUIT`을 보내면 모든 goroutine 스택을 출력한다:

```bash
kill -QUIT <pid>
```

---

## 진단 순서 조합

성능 문제는 보통 한 가지 원인에서 오지 않는다. CPU `wa`가 높고 소켓 fd 수가 비정상적으로 많다면 DB 커넥션 누수가 I/O 병목으로 번진 것일 수 있다. `vmstat → /proc/pid/fd → strace -e trace=connect` 순서로 좁히면 대부분 원인이 나온다.

메모리 급증 + 프로세스 재시작이 반복된다면 OOM 로그를 먼저 확인하고, OOM이 아니면 `jstack`이나 `/proc/pid/status`로 스레드 상태를 본다.
