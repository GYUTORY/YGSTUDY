---
title: 프로세스 자원 한계값
tags: [os]
updated: 2026-07-13
---

# 프로세스 자원 한계값

리눅스에서 프로세스가 쓸 수 있는 자원에는 상한이 있다. 파일 디스크립터 수, 스택 크기, 열 수 있는 파일 수, 프로세스가 쓸 수 있는 메모리 크기 등이 모두 커널 수준에서 제어된다. 이 한계값을 이해하지 못하면 "Too many open files"나 core dump가 안 생기는 문제처럼 원인을 찾기 어려운 장애를 만난다.

---

## ulimit — soft limit과 hard limit

`ulimit`은 셸 세션에서 자원 한계값을 조회하고 변경하는 명령이다. 모든 한계값에는 두 가지 레벨이 있다.

- **soft limit**: 실제로 적용되는 한계값이다. 프로세스는 이 값을 hard limit까지 올릴 수 있다.
- **hard limit**: soft limit의 상한선이다. 일반 사용자는 hard limit을 올릴 수 없다. root만 가능하다.

```bash
# 모든 한계값 조회
$ ulimit -a

# soft limit과 hard limit을 함께 조회
$ ulimit -Sn    # soft limit, 파일 디스크립터 수
$ ulimit -Hn    # hard limit, 파일 디스크립터 수

# soft limit을 hard limit까지 올리기 (일반 사용자도 가능)
$ ulimit -n 65536

# hard limit 올리기는 root만 가능
$ sudo ulimit -Hn 1000000
```

주의할 점이 있다. `ulimit`으로 설정한 값은 현재 셸과 그 셸에서 실행되는 자식 프로세스에만 적용된다. systemd로 관리되는 서비스는 셸에서 `ulimit`을 아무리 바꿔도 영향이 없다. systemd 유닛 파일에서 별도로 지정해야 한다.

```ini
# /etc/systemd/system/myapp.service
[Service]
LimitNOFILE=65536
LimitCORE=infinity
```

`/etc/security/limits.conf`는 PAM 기반 로그인 세션(SSH, su 등)에 적용된다. systemd 서비스에는 적용되지 않는다. 서비스 배포 환경에서 limits.conf만 수정하고 왜 안 되는지 헤매는 경우가 많다.

```bash
# /etc/security/limits.conf
*    soft    nofile    65536
*    hard    nofile    1000000
myuser soft  nproc     4096
```

---

## /proc/[pid]/limits — 실제 적용된 값 확인

실행 중인 프로세스에 실제로 어떤 한계값이 적용되어 있는지는 `/proc/[pid]/limits`에서 확인한다. `ulimit` 출력은 현재 셸의 값이고, 프로세스가 이미 실행 중이라면 기동 당시의 환경이 적용된 것이라 다를 수 있다.

```bash
$ cat /proc/$(pidof nginx)/limits
Limit                     Soft Limit           Hard Limit           Units
Max cpu time              unlimited            unlimited            seconds
Max file size             unlimited            unlimited            bytes
Max data size             unlimited            unlimited            bytes
Max stack size            8388608              unlimited            bytes
Max core file size        0                    unlimited            bytes
Max resident set          unlimited            unlimited            bytes
Max processes             31234                31234                processes
Max open files            65536                65536                files
Max locked memory         65536                65536                bytes
Max address space         unlimited            unlimited            bytes
Max file locks            unlimited            unlimited            locks
Max pending signals       31234                31234                signals
Max msgqueue size         819200               819200               bytes
Max nice priority         0                    0
Max realtime priority     0                    0
Max realtime timeout      unlimited            unlimited            us
```

서비스 장애 상황에서 가장 먼저 확인해야 할 항목은 `Max open files`다. 이 값이 1024나 4096처럼 낮으면 트래픽이 늘었을 때 파일 디스크립터를 다 써서 새 연결을 못 받는 상황이 된다.

---

## getrlimit / setrlimit — 시스템 콜 수준 제어

프로세스 내부에서 자원 한계값을 읽고 쓰는 시스템 콜이다.

```c
#include <sys/resource.h>

struct rlimit {
    rlim_t rlim_cur;  // soft limit
    rlim_t rlim_max;  // hard limit
};

int getrlimit(int resource, struct rlimit *rlim);
int setrlimit(int resource, const struct rlimit *rlim);
```

서버 데몬이 시작할 때 파일 디스크립터 한계를 늘리는 코드는 이렇게 쓴다.

```c
#include <sys/resource.h>
#include <stdio.h>
#include <errno.h>

int raise_fd_limit(rlim_t target) {
    struct rlimit rl;
    
    if (getrlimit(RLIMIT_NOFILE, &rl) != 0) {
        perror("getrlimit");
        return -1;
    }
    
    printf("현재: soft=%lu, hard=%lu\n", rl.rlim_cur, rl.rlim_max);
    
    // hard limit을 넘을 수는 없다
    if (target > rl.rlim_max) {
        target = rl.rlim_max;
    }
    
    rl.rlim_cur = target;
    if (setrlimit(RLIMIT_NOFILE, &rl) != 0) {
        perror("setrlimit");
        return -1;
    }
    
    return 0;
}
```

주요 resource 상수:

| 상수 | 내용 |
|------|------|
| RLIMIT_NOFILE | 열 수 있는 파일 디스크립터 최대 수 |
| RLIMIT_CORE | core dump 파일 최대 크기 (바이트) |
| RLIMIT_AS | 가상 주소 공간 최대 크기 (바이트) |
| RLIMIT_STACK | 스택 최대 크기 |
| RLIMIT_CPU | CPU 시간 최대 사용량 (초) |
| RLIMIT_NPROC | 이 UID가 만들 수 있는 최대 프로세스 수 |
| RLIMIT_MEMLOCK | mlock으로 잠글 수 있는 최대 메모리 크기 |

`prlimit` 시스템 콜은 다른 프로세스의 한계값을 조회/변경할 수 있다. root 권한이 필요하다.

```bash
# prlimit 명령어로 실행 중인 프로세스의 한계값 변경
$ prlimit --nofile=65536:65536 --pid $(pidof nginx)

# 새 프로세스를 특정 한계값으로 실행
$ prlimit --nofile=65536 ./myserver
```

---

## 파일 디스크립터 한계와 Too many open files

"Too many open files"는 EMFILE(프로세스 한도 초과)과 ENFILE(시스템 전체 한도 초과) 두 경우에 발생한다. 에러 번호가 다르다.

```bash
# 시스템 전체 파일 핸들 한도
$ cat /proc/sys/fs/file-max
9223372036854775807

# 현재 시스템에서 열린 파일 수
$ cat /proc/sys/fs/file-nr
6432    0    9223372036854775807
# 열린 수  할당됐다가 해제된 수  최대값
```

프로세스 수준에서 원인을 추적할 때는 실제로 열린 파일 디스크립터가 몇 개인지 먼저 본다.

```bash
# 특정 프로세스가 열고 있는 파일 디스크립터 수
$ ls /proc/<pid>/fd | wc -l

# 어떤 파일들을 열고 있는지
$ ls -la /proc/<pid>/fd | head -30
lrwxrwxrwx 1 www www 64 Jul 13 10:00 0 -> /dev/null
lrwxrwxrwx 1 www www 64 Jul 13 10:00 1 -> /var/log/app.log
lrwxrwxrwx 1 www www 64 Jul 13 10:00 2 -> /var/log/app.log
lrwxrwxrwx 1 www www 64 Jul 13 10:00 5 -> socket:[12345]
lrwxrwxrwx 1 www www 64 Jul 13 10:00 6 -> socket:[12346]
```

소켓이 대량으로 열려 있으면 연결을 닫지 않는 코드가 의심된다.

```bash
# lsof로 프로세스별 파일 디스크립터 사용 현황
$ lsof -p <pid> | wc -l

# 소켓 상태별 분류 (TIME_WAIT가 많으면 연결 누수 의심)
$ ss -tnp | grep <pid> | awk '{print $1}' | sort | uniq -c

# 타입별로 분류해서 보기
$ lsof -p <pid> | awk '{print $5}' | sort | uniq -c | sort -rn
    523 IPv4
    200 REG
     50 IPv6
      3 CHR
      2 DIR
```

파일 디스크립터가 계속 늘어난다면 소켓이나 파일을 닫지 않는 코드를 찾아야 한다. Go에서는 `defer f.Close()` 빠뜨리는 게 흔한 원인이고, Java에서는 try-with-resources를 안 쓰는 경우다.

운영 중에 한계값을 올려야 한다면 `/proc/[pid]/fd` 디렉토리의 링크 수로 현황을 파악하고, `prlimit`으로 실행 중인 프로세스의 hard/soft limit을 올린다. 재시작 없이 가능하다.

---

## core dump 크기 설정과 디버깅

프로세스가 시그널로 종료될 때(SIGSEGV, SIGABRT 등) 메모리 상태를 파일로 덤프한다. 이게 core dump다. 기본 soft limit이 0이라 아무것도 안 남는 경우가 많다.

```bash
# core dump가 비활성화되어 있는지 확인
$ ulimit -c
0  # 0이면 core dump 생성 안 함

# 무제한으로 설정
$ ulimit -c unlimited

# 특정 크기 (킬로바이트) 지정
$ ulimit -c 524288  # 512MB
```

core dump 파일 위치와 이름 패턴은 `/proc/sys/kernel/core_pattern`으로 제어한다.

```bash
$ cat /proc/sys/kernel/core_pattern
|/usr/share/apport/apport -p%p -s%s -c%c -d%d -P%P -u%u -g%g -- %E

# Ubuntu는 기본적으로 apport로 전달된다
# 파일로 직접 저장하려면
$ echo "/tmp/core-%e-%p-%t" > /proc/sys/kernel/core_pattern
# %e: 실행 파일명, %p: PID, %t: 타임스탬프
```

systemd를 쓰는 환경에서는 기본적으로 `systemd-coredump`가 코어를 수집한다.

```bash
# systemd-coredump로 저장된 core dump 목록
$ coredumpctl list

# 가장 최근 core dump 분석
$ coredumpctl debug

# 특정 PID의 core dump
$ coredumpctl debug <pid>

# core dump를 파일로 추출
$ coredumpctl dump -o /tmp/app.core
```

gdb로 core dump를 분석하는 기본 흐름이다.

```bash
$ gdb ./myserver /tmp/core-myserver-12345-1720836000

(gdb) bt         # 스택 트레이스 출력
#0  0x00007f8a1c2b3456 in malloc_consolidate ()
#1  0x000000000040a123 in handle_request (conn=0x0) at server.c:145
#2  0x000000000040b456 in worker_thread (arg=0x7f8a1c000b20) at worker.c:89

(gdb) frame 1    # 프레임 선택
(gdb) list       # 해당 소스 코드 확인
(gdb) info locals # 지역 변수 확인
(gdb) print conn  # 변수 값 출력
```

컨테이너 환경에서는 core dump 경로가 호스트의 `core_pattern`을 따른다. 컨테이너 내부에서 경로를 설정해도 호스트 커널 설정이 우선이다. core dump를 컨테이너 내부에 저장하려면 호스트의 `core_pattern`을 바꾸거나, 볼륨 마운트 경로를 활용해야 한다.

---

## RLIMIT_AS — 메모리 주소 공간 상한

`RLIMIT_AS`는 프로세스의 가상 주소 공간 전체 크기를 제한한다. 이 한계를 넘는 `mmap()`, `brk()`, `mmap()`이 ENOMEM을 반환한다.

```bash
# 현재 가상 주소 공간 한계
$ ulimit -v
unlimited

# 500MB로 제한
$ ulimit -v 512000  # 킬로바이트 단위
```

운영 서비스에 `RLIMIT_AS`를 거는 경우는 드물다. 가상 주소 공간은 물리 메모리와 다르고, JVM이나 Go 런타임처럼 메모리 관리를 자체적으로 하는 런타임은 큰 가상 주소 공간을 예약해두기 때문이다. JVM은 힙 크기와 무관하게 수십 GB의 가상 주소 공간을 잡아두는 경우가 있다.

코드에서 직접 제한을 걸 때는 이렇게 한다.

```c
#include <sys/resource.h>

void limit_memory(size_t max_bytes) {
    struct rlimit rl;
    rl.rlim_cur = max_bytes;
    rl.rlim_max = max_bytes;
    
    if (setrlimit(RLIMIT_AS, &rl) != 0) {
        perror("setrlimit RLIMIT_AS");
    }
}

// 예: 샌드박스에서 외부 코드 실행 시 메모리 제한
limit_memory(256 * 1024 * 1024);  // 256MB
exec_user_code();
```

`RLIMIT_AS`와 `RLIMIT_DATA`는 다르다. `RLIMIT_AS`는 가상 주소 공간 전체, `RLIMIT_DATA`는 힙과 데이터 영역만 제한한다. 보통 `RLIMIT_AS`가 더 광범위하게 사용된다.

---

## cgroups v2와 컨테이너 자원 제한

`ulimit`과 `rlimit`은 프로세스 단위 제한이다. 컨테이너처럼 여러 프로세스를 묶어서 제한하려면 cgroups를 써야 한다. Docker/Kubernetes는 내부적으로 cgroups v2를 사용한다.

```bash
# cgroups v2가 마운트되어 있는지 확인
$ mount | grep cgroup
cgroup2 on /sys/fs/cgroup type cgroup2 (rw,nosuid,nodev,noexec,relatime,nsdelegate,memory_recursiveprot)

# 현재 프로세스가 속한 cgroup 확인
$ cat /proc/self/cgroup
0::/user.slice/user-1000.slice/session-3.scope
```

Docker 컨테이너의 경우 `/proc/[pid]/cgroup`을 보면 컨테이너 ID가 포함된 경로가 나온다.

```bash
$ cat /proc/1/cgroup
0::/system.slice/docker-a3f8c9d2e1b4f5678901234567890123456789012345678901234567890.scope
```

이 경로로 cgroup 디렉토리를 찾아가면 실제로 적용된 자원 제한을 볼 수 있다.

```bash
# Docker 컨테이너의 cgroup 경로
$ CGROUP_PATH="/sys/fs/cgroup/system.slice/docker-<container_id>.scope"

# 메모리 한계 확인
$ cat $CGROUP_PATH/memory.max
536870912  # 512MB (바이트 단위)

# 현재 메모리 사용량
$ cat $CGROUP_PATH/memory.current
134217728  # 128MB

# CPU 제한 확인 (quota/period)
$ cat $CGROUP_PATH/cpu.max
100000 100000  # 100ms/100ms = 100% 1 core
# "max 100000"이면 제한 없음

# 현재 CPU 사용 통계
$ cat $CGROUP_PATH/cpu.stat
usage_usec 45234567
user_usec 32123456
system_usec 13111111
nr_throttled 15
throttled_usec 8234567  # 스로틀링된 총 시간
```

`nr_throttled`가 0이 아니면 컨테이너가 CPU 제한에 걸려서 스로틀링되고 있다는 뜻이다. 응답이 느려지는 원인을 찾을 때 여기를 봐야 한다.

```bash
# 메모리 상세 통계
$ cat $CGROUP_PATH/memory.stat
anon 104857600         # 익명 매핑 (힙, 스택 등)
file 28311552          # 파일 기반 매핑 (공유 라이브러리 등)
kernel 5242880         # 커널이 사용하는 메모리
pgfault 234567         # 페이지 폴트 수
pgmajfault 12          # major 페이지 폴트 (디스크 I/O 발생)
workingset_refault_anon 0
oom 0                  # OOM 발생 횟수
oom_kill 0             # OOM으로 프로세스가 죽은 횟수
```

`oom_kill`이 0이 아니면 컨테이너 내부에서 OOM이 발생한 적이 있다는 뜻이다. Kubernetes Pod이 CrashLoopBackOff 상태인데 원인이 명확하지 않을 때 이 값을 확인한다.

Docker로 컨테이너를 실행할 때 자원 제한을 거는 방법이다.

```bash
# 메모리 512MB, CPU 0.5코어 제한
$ docker run --memory=512m --cpus=0.5 myapp

# 위 명령은 내부적으로 cgroup에 아래 값을 설정한다
# memory.max = 536870912
# cpu.max = 50000 100000
```

Kubernetes에서는 `resources.limits`가 cgroup의 hard limit으로 들어가고, `resources.requests`는 스케줄링 기준으로만 사용된다. Pod이 limits을 초과하면 메모리는 OOM kill, CPU는 스로틀링이 발생한다.

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

limits는 설정했는데 requests가 없거나 너무 낮으면 노드가 overcommit 상태가 되어 실제로 메모리 압박이 생겼을 때 예상치 못한 Pod eviction이 발생할 수 있다.

---

## 참조

- `man 2 getrlimit` — getrlimit/setrlimit/prlimit 시스템 콜
- `man 5 proc` — /proc 파일시스템 (limits, cgroup 항목 포함)
- `man 1 ulimit` — 셸 내장 ulimit 명령
- `man 1 prlimit` — 실행 중인 프로세스의 한계값 변경
- Linux Kernel: `Documentation/admin-guide/cgroup-v2.rst`
- `man 1 coredumpctl` — systemd-coredump 로그 관리
