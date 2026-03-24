---
title: "프로세스 간 통신 (IPC)"
tags: [OS, IPC, pipe, shared-memory, socket, signal, message-queue]
updated: 2026-03-25
---

# 프로세스 간 통신 (IPC)

IPC(Inter-Process Communication)는 서로 다른 프로세스가 데이터를 주고받는 방법이다. 프로세스는 각자 독립된 가상 메모리 공간을 가지기 때문에, 커널이 제공하는 메커니즘 없이는 직접 데이터를 공유할 수 없다.

리눅스에서 실무적으로 쓰이는 IPC 방식은 크게 6가지다.

| 방식 | 데이터 흐름 | 속도 | 관계 제약 |
|------|------------|------|----------|
| Pipe | 단방향 바이트 스트림 | 빠름 | 부모-자식 프로세스 |
| Named Pipe (FIFO) | 단방향 바이트 스트림 | 빠름 | 제약 없음 (파일 경로 공유) |
| Unix Domain Socket | 양방향 바이트/데이터그램 | 빠름 | 제약 없음 |
| Shared Memory | 양방향 메모리 직접 접근 | 가장 빠름 | 제약 없음 |
| Message Queue | 양방향 메시지 단위 | 보통 | 제약 없음 |
| Signal | 비동기 알림 (데이터 없음) | - | 제약 없음 |

---

## Pipe

가장 단순한 IPC다. `pipe()` 시스템 콜로 파일 디스크립터 2개를 만들고, `fork()` 후 부모-자식 간에 데이터를 주고받는다.

```c
#include <stdio.h>
#include <unistd.h>
#include <string.h>

int main(void)
{
    int fd[2];
    pid_t pid;
    char buf[128];

    if (pipe(fd) == -1) {
        perror("pipe");
        return 1;
    }

    pid = fork();
    if (pid == -1) {
        perror("fork");
        return 1;
    }

    if (pid == 0) {
        /* 자식: 읽기만 한다 */
        close(fd[1]);
        ssize_t n = read(fd[0], buf, sizeof(buf) - 1);
        buf[n] = '\0';
        printf("child received: %s\n", buf);
        close(fd[0]);
    } else {
        /* 부모: 쓰기만 한다 */
        close(fd[0]);
        const char *msg = "hello from parent";
        write(fd[1], msg, strlen(msg));
        close(fd[1]);
    }

    return 0;
}
```

### 실무에서 겪는 문제

**pipe buffer가 가득 차면 write가 블록된다.** 리눅스 기본 pipe buffer 크기는 65,536바이트(64KB)다. 자식 프로세스가 읽기를 안 하고 있으면 부모의 `write()`가 멈춘다. 반대로 buffer가 비어 있으면 `read()`가 블록된다.

```bash
# pipe buffer 크기 확인 (리눅스)
cat /proc/sys/fs/pipe-max-size
```

`fcntl(fd, F_SETPIPE_SZ, size)`로 pipe buffer 크기를 조정할 수 있지만, `pipe-max-size` 이상으로는 못 올린다.

**읽는 쪽이 먼저 종료되면 SIGPIPE가 발생한다.** 자식이 `close(fd[0])` 하거나 죽은 상태에서 부모가 `write()`를 호출하면 SIGPIPE 시그널이 날아온다. 기본 동작이 프로세스 종료이므로, 데몬 프로세스에서는 `signal(SIGPIPE, SIG_IGN)` 처리가 필수다.

---

## Named Pipe (FIFO)

일반 pipe는 `fork()`로 파일 디스크립터를 공유해야 하므로 부모-자식 관계에서만 동작한다. named pipe는 파일 시스템에 경로를 만들어서 아무 프로세스나 열 수 있다.

**writer.c**
```c
#include <stdio.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>

int main(void)
{
    const char *fifo_path = "/tmp/my_fifo";

    mkfifo(fifo_path, 0666);

    int fd = open(fifo_path, O_WRONLY);
    const char *msg = "data from writer";
    write(fd, msg, strlen(msg));
    close(fd);

    return 0;
}
```

**reader.c**
```c
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int main(void)
{
    const char *fifo_path = "/tmp/my_fifo";
    char buf[128];

    int fd = open(fifo_path, O_RDONLY);
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    buf[n] = '\0';
    printf("reader got: %s\n", buf);
    close(fd);

    unlink(fifo_path);  /* 다 쓰면 정리 */
    return 0;
}
```

### 실무에서 겪는 문제

**reader 없이 writer가 `open()`하면 블록된다.** 양쪽 다 열려야 `open()`이 리턴한다. 타임아웃 처리를 하려면 `O_NONBLOCK`으로 열어야 하는데, 이 경우 writer는 reader가 없으면 `open()`이 `ENXIO`로 실패한다.

**FIFO 파일이 정리 안 되는 경우가 많다.** 프로세스가 비정상 종료하면 `/tmp/my_fifo` 파일이 남는다. 프로그램 시작 시 `unlink()` 후 `mkfifo()`를 다시 호출하는 패턴이 안전하다.

---

## Unix Domain Socket

TCP/UDP 소켓과 같은 API를 쓰지만, 네트워크 스택을 타지 않고 커널 내부에서 데이터를 복사한다. 양방향 통신이 되고, `SOCK_STREAM`(TCP처럼)과 `SOCK_DGRAM`(UDP처럼) 둘 다 지원한다.

nginx, PostgreSQL, Docker, MySQL 등 대부분의 서버 소프트웨어가 로컬 통신에 Unix domain socket을 사용한다.

**server.c**
```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

#define SOCK_PATH "/tmp/my_uds.sock"

int main(void)
{
    int server_fd, client_fd;
    struct sockaddr_un addr;
    char buf[256];

    unlink(SOCK_PATH);

    server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd == -1) {
        perror("socket");
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCK_PATH, sizeof(addr.sun_path) - 1);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("bind");
        return 1;
    }

    listen(server_fd, 5);
    printf("server waiting...\n");

    client_fd = accept(server_fd, NULL, NULL);
    ssize_t n = read(client_fd, buf, sizeof(buf) - 1);
    buf[n] = '\0';
    printf("server received: %s\n", buf);

    const char *reply = "ack";
    write(client_fd, reply, strlen(reply));

    close(client_fd);
    close(server_fd);
    unlink(SOCK_PATH);

    return 0;
}
```

**client.c**
```c
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

#define SOCK_PATH "/tmp/my_uds.sock"

int main(void)
{
    int fd;
    struct sockaddr_un addr;
    char buf[256];

    fd = socket(AF_UNIX, SOCK_STREAM, 0);

    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCK_PATH, sizeof(addr.sun_path) - 1);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("connect");
        return 1;
    }

    const char *msg = "hello from client";
    write(fd, msg, strlen(msg));

    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    buf[n] = '\0';
    printf("client received: %s\n", buf);

    close(fd);
    return 0;
}
```

### 실무에서 겪는 문제

**소켓 파일이 남아 있으면 `bind()`가 실패한다.** `EADDRINUSE` 에러가 나는데, 서버 시작 전에 `unlink()`를 호출해야 한다. 위 예제처럼 서버 시작 시 기존 소켓 파일을 지우는 게 일반적인 패턴이다.

**sun_path 길이 제한이 있다.** `sockaddr_un.sun_path`는 108바이트까지만 된다(리눅스 기준). 경로가 긴 디렉토리에 소켓 파일을 만들면 잘린다. `/tmp`이나 `/var/run` 같은 짧은 경로를 쓰는 이유다.

**파일 권한 문제.** 소켓 파일에도 파일 퍼미션이 적용된다. 다른 유저의 프로세스가 접속해야 한다면 `chmod()`로 권한을 열어줘야 한다.

---

## Shared Memory

커널을 거치지 않고 프로세스 간에 메모리를 직접 공유하는 방식이다. 데이터 복사가 없으므로 대량 데이터 전송에서 가장 빠르다. 두 가지 API가 있다.

### shmget (System V)

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <unistd.h>

#define SHM_SIZE 4096

int main(void)
{
    key_t key = ftok("/tmp", 'A');
    int shmid = shmget(key, SHM_SIZE, IPC_CREAT | 0666);
    if (shmid == -1) {
        perror("shmget");
        return 1;
    }

    pid_t pid = fork();

    if (pid == 0) {
        /* 자식: 읽기 */
        sleep(1);  /* 부모가 쓸 시간을 줌 */
        char *data = (char *)shmat(shmid, NULL, SHM_RDONLY);
        printf("child read: %s\n", data);
        shmdt(data);
    } else {
        /* 부모: 쓰기 */
        char *data = (char *)shmat(shmid, NULL, 0);
        strcpy(data, "shared memory data");
        shmdt(data);

        wait(NULL);
        shmctl(shmid, IPC_RMID, NULL);  /* 정리 */
    }

    return 0;
}
```

### mmap (POSIX)

`mmap`은 파일이나 익명 메모리를 프로세스 주소 공간에 매핑한다. `MAP_SHARED`와 `MAP_ANONYMOUS` 플래그 조합으로 shared memory를 만들 수 있다.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    size_t size = 4096;

    /* MAP_SHARED | MAP_ANONYMOUS: 파일 없이 공유 메모리 생성 */
    char *shared = mmap(NULL, size,
                        PROT_READ | PROT_WRITE,
                        MAP_SHARED | MAP_ANONYMOUS,
                        -1, 0);
    if (shared == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    pid_t pid = fork();

    if (pid == 0) {
        sleep(1);
        printf("child read: %s\n", shared);
    } else {
        strcpy(shared, "mmap shared data");
        wait(NULL);
        munmap(shared, size);
    }

    return 0;
}
```

### 실무에서 겪는 문제

**shmget으로 만든 공유 메모리는 프로세스가 죽어도 남아 있다.** `shmctl(shmid, IPC_RMID, NULL)` 호출을 안 하면 시스템에 좀비 shared memory가 쌓인다. `ipcs -m`으로 확인하고 `ipcrm -m <shmid>`로 수동 정리해야 하는 경우가 생긴다.

```bash
# 현재 시스템의 공유 메모리 세그먼트 확인
ipcs -m

# 특정 세그먼트 삭제
ipcrm -m <shmid>
```

**동기화를 직접 해야 한다.** shared memory 자체에는 락이 없다. 여러 프로세스가 동시에 쓰면 데이터가 깨진다. 세마포어(`sem_open`, `semget`)나 뮤텍스(`pthread_mutex`의 `PTHREAD_PROCESS_SHARED` 속성)를 같이 써야 한다. 위 예제에서 `sleep(1)`을 쓴 것은 동기화를 대충 한 것이고, 실제 코드에서는 세마포어를 써야 한다.

**mmap의 MAP_ANONYMOUS는 fork() 관계에서만 공유된다.** 관련 없는 프로세스 간에 mmap으로 공유하려면 `shm_open()`으로 이름 있는 공유 메모리 객체를 만들어야 한다.

```c
int fd = shm_open("/my_shm", O_CREAT | O_RDWR, 0666);
ftruncate(fd, 4096);
char *ptr = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
/* ... 사용 후 ... */
shm_unlink("/my_shm");  /* 정리 */
```

---

## Message Queue

메시지 단위로 데이터를 주고받는다. pipe와 달리 메시지 경계가 보존되고, 메시지 타입별로 선택적 수신이 가능하다. POSIX message queue(`mq_open`)와 System V message queue(`msgget`)가 있는데, POSIX 쪽이 API가 깔끔하다.

### POSIX Message Queue

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <mqueue.h>
#include <unistd.h>
#include <sys/wait.h>

#define QUEUE_NAME "/test_queue"
#define MAX_MSG_SIZE 256
#define MAX_MSG_COUNT 10

int main(void)
{
    struct mq_attr attr;
    attr.mq_flags = 0;
    attr.mq_maxmsg = MAX_MSG_COUNT;
    attr.mq_msgsize = MAX_MSG_SIZE;
    attr.mq_curmsgs = 0;

    mq_unlink(QUEUE_NAME);  /* 이전 잔여물 정리 */

    pid_t pid = fork();

    if (pid == 0) {
        /* 자식: 수신 */
        sleep(1);
        mqd_t mq = mq_open(QUEUE_NAME, O_RDONLY);
        if (mq == (mqd_t)-1) {
            perror("mq_open (reader)");
            return 1;
        }
        char buf[MAX_MSG_SIZE + 1];
        unsigned int prio;
        ssize_t n = mq_receive(mq, buf, MAX_MSG_SIZE, &prio);
        buf[n] = '\0';
        printf("received (prio=%u): %s\n", prio, buf);
        mq_close(mq);
    } else {
        /* 부모: 송신 */
        mqd_t mq = mq_open(QUEUE_NAME, O_CREAT | O_WRONLY, 0666, &attr);
        if (mq == (mqd_t)-1) {
            perror("mq_open (writer)");
            return 1;
        }
        const char *msg = "message queue data";
        mq_send(mq, msg, strlen(msg), 1);  /* priority = 1 */
        mq_close(mq);

        wait(NULL);
        mq_unlink(QUEUE_NAME);
    }

    return 0;
}
```

컴파일 시 `-lrt` 링크가 필요하다.

```bash
gcc -o mq_demo mq_demo.c -lrt
```

### 실무에서 겪는 문제

**큐가 가득 차면 `mq_send()`가 블록된다.** `mq_maxmsg` 개수만큼 쌓이면 블록되거나 `O_NONBLOCK` 모드에서는 `EAGAIN`이 리턴된다. 수신 측이 느리면 송신 측이 멈추는 건 pipe와 같다.

**message queue도 프로세스 종료 후 남아 있다.** `mq_unlink()`를 안 하면 `/dev/mqueue/` 아래에 파일이 남는다. 리눅스에서는 `ls /dev/mqueue/`로 확인할 수 있다.

**메시지 크기 제한이 있다.** `/proc/sys/fs/mqueue/msgsize_max`로 시스템 최대값이 정해져 있다. 기본값은 8,192바이트다. 큰 데이터를 보내려면 shared memory를 쓰고, message queue는 알림용으로만 쓰는 패턴이 일반적이다.

---

## Signal

signal은 프로세스에 비동기 이벤트를 알리는 방법이다. 데이터를 전달하는 용도는 아니고, 특정 이벤트가 발생했다는 사실만 통보한다.

```c
#include <stdio.h>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>

volatile sig_atomic_t got_signal = 0;

void handler(int sig)
{
    got_signal = 1;
}

int main(void)
{
    pid_t pid = fork();

    if (pid == 0) {
        /* 자식: SIGUSR1을 기다림 */
        struct sigaction sa;
        sa.sa_handler = handler;
        sa.sa_flags = 0;
        sigemptyset(&sa.sa_mask);
        sigaction(SIGUSR1, &sa, NULL);

        printf("child waiting for signal...\n");
        while (!got_signal)
            pause();  /* 시그널 올 때까지 sleep */

        printf("child got SIGUSR1\n");
    } else {
        /* 부모: 1초 후 자식에게 시그널 전송 */
        sleep(1);
        kill(pid, SIGUSR1);
        wait(NULL);
    }

    return 0;
}
```

### 실무에서 겪는 문제

**signal handler 안에서 할 수 있는 일이 제한된다.** `printf()`, `malloc()`, `mutex lock` 등은 signal handler 안에서 호출하면 안 된다(async-signal-safe가 아닌 함수). handler에서는 플래그만 세우고, 메인 루프에서 처리하는 패턴을 써야 한다.

**같은 signal이 연속으로 오면 하나만 처리된다.** 리눅스의 표준 시그널은 큐잉되지 않는다. SIGUSR1을 3번 보내도 pending 상태에서 1번만 전달될 수 있다. 큐잉이 필요하면 `sigqueue()`와 real-time signal(`SIGRTMIN` ~ `SIGRTMAX`)을 써야 한다.

**`signal()` 대신 `sigaction()`을 써야 한다.** `signal()`은 시스템마다 동작이 다르다. handler가 한 번 호출된 후 기본 동작으로 리셋되는 시스템도 있다. `sigaction()`은 동작이 명확하게 정의되어 있어서 이식성 문제가 없다.

---

## 성능 비교

같은 머신에서 1MB 데이터를 전송하는 기준으로 대략적인 처리량을 비교하면 다음과 같다.

| 방식 | 처리량 (대략) | 특징 |
|------|-------------|------|
| Shared Memory | 수 GB/s | 커널 개입 없음. 메모리 복사 자체가 없다 |
| Unix Domain Socket | 수백 MB/s ~ 수 GB/s | 커널 내 데이터 복사 1회 |
| Pipe / Named Pipe | 수백 MB/s | 커널 버퍼 경유, 단방향 |
| Message Queue | 수십 ~ 수백 MB/s | 메시지 단위 오버헤드 |
| Signal | 해당 없음 | 데이터 전송 용도가 아님 |

shared memory가 압도적으로 빠르지만, 동기화 코드를 직접 짜야 하는 부담이 있다. 대부분의 경우 Unix domain socket이 성능과 편의성의 균형점이다.

---

## 어떤 걸 쓸지 판단하는 기준

**부모-자식 간 단순 데이터 전달** → pipe가 가장 간단하다. shell의 `|` 파이프가 이것이다.

**관련 없는 프로세스 간 통신** → Unix domain socket을 먼저 고려한다. 양방향이고 API가 TCP/UDP와 동일해서 나중에 네트워크 통신으로 전환하기 쉽다.

**대용량 데이터 공유** → shared memory + 세마포어 조합. 데이터를 복사하지 않으므로 수십 MB 이상의 데이터를 주고받을 때 의미가 있다.

**메시지 단위 통신이 필요할 때** → message queue. 메시지 경계가 보존되고 우선순위 기반 수신이 가능하다.

**프로세스에 이벤트 알림만 보낼 때** → signal. `SIGTERM`으로 graceful shutdown 요청하는 게 대표적인 예다.
