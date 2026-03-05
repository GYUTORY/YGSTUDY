---
title: IPC (프로세스 간 통신) 가이드
tags: [os, ipc, pipe, shared-memory, message-queue, socket, signal, semaphore]
updated: 2026-03-01
---

# IPC (Inter-Process Communication)

## 개요

IPC(프로세스 간 통신)는 독립된 프로세스끼리 **데이터를 주고받는 메커니즘**이다. 프로세스는 각자 독립된 메모리 공간을 가지므로, 직접 메모리를 공유할 수 없다. 따라서 OS가 제공하는 IPC 메커니즘을 사용해야 한다.

```
프로세스 A [메모리 공간 A]     프로세스 B [메모리 공간 B]
     │                              │
     └────── IPC 메커니즘 ──────────┘
             (파이프, 공유 메모리, 소켓 등)
```

### IPC가 필요한 이유

| 상황 | 예시 |
|------|------|
| **데이터 공유** | 웹 서버와 DB 프로세스 간 쿼리 전달 |
| **작업 분배** | 프로듀서-컨슈머 패턴 |
| **이벤트 알림** | 자식 프로세스 종료 시 부모에게 통보 |
| **프로세스 동기화** | 여러 프로세스가 순서대로 작업 수행 |

## 핵심

### 1. IPC 메커니즘 비교

| 메커니즘 | 방향 | 관계 | 속도 | 데이터 크기 | 네트워크 |
|---------|------|------|------|-----------|---------|
| **파이프 (Pipe)** | 단방향 | 부모-자식 | 빠름 | 제한적 | 불가 |
| **Named Pipe (FIFO)** | 단방향 | 무관 | 빠름 | 제한적 | 불가 |
| **메시지 큐** | 양방향 | 무관 | 보통 | 메시지 단위 | 불가 |
| **공유 메모리** | 양방향 | 무관 | **가장 빠름** | 대용량 | 불가 |
| **시그널** | 단방향 | 무관 | 빠름 | 없음 (알림만) | 불가 |
| **소켓** | 양방향 | 무관 | 보통 | 무제한 | **가능** |

### 2. 파이프 (Pipe)

가장 기본적인 IPC. **단방향** 데이터 흐름을 제공한다.

```
부모 프로세스                    자식 프로세스
  write(fd[1]) ──────────────▶ read(fd[0])
               파이프 (커널 버퍼)
```

#### 쉘에서의 파이프

```bash
# | 기호가 파이프
ls -la | grep ".md" | wc -l

# ls의 stdout → grep의 stdin → wc의 stdin
```

#### C 코드 예시

```c
#include <unistd.h>
#include <stdio.h>
#include <string.h>

int main() {
    int fd[2];          // fd[0]: 읽기, fd[1]: 쓰기
    pipe(fd);           // 파이프 생성

    pid_t pid = fork();

    if (pid == 0) {
        // 자식 프로세스: 읽기
        close(fd[1]);   // 쓰기 끝 닫기
        char buf[100];
        read(fd[0], buf, sizeof(buf));
        printf("자식이 받은 메시지: %s\n", buf);
        close(fd[0]);
    } else {
        // 부모 프로세스: 쓰기
        close(fd[0]);   // 읽기 끝 닫기
        char *msg = "Hello from parent!";
        write(fd[1], msg, strlen(msg) + 1);
        close(fd[1]);
    }
    return 0;
}
```

#### Named Pipe (FIFO)

부모-자식 관계가 아닌 프로세스 간에도 사용 가능하다. 파일 시스템에 이름을 가진 특수 파일로 존재한다.

```bash
# Named Pipe 생성
mkfifo /tmp/myfifo

# 프로세스 A: 쓰기
echo "Hello" > /tmp/myfifo

# 프로세스 B: 읽기 (다른 터미널)
cat /tmp/myfifo    # "Hello" 출력
```

### 3. 메시지 큐 (Message Queue)

커널이 관리하는 큐에 **메시지 단위**로 데이터를 주고받는다. 메시지에 타입을 지정하여 선택적으로 수신할 수 있다.

```
프로세스 A ──┐                  ┌── 프로세스 B
프로세스 C ──┤→ [메시지 큐] →──┤── 프로세스 D
프로세스 E ──┘   (커널 관리)    └── 프로세스 F
```

```c
#include <sys/msg.h>

struct message {
    long type;          // 메시지 타입 (1 이상)
    char text[256];     // 메시지 내용
};

// 메시지 큐 생성
int msgid = msgget(IPC_PRIVATE, 0666 | IPC_CREAT);

// 메시지 전송
struct message msg = { .type = 1 };
strcpy(msg.text, "Hello!");
msgsnd(msgid, &msg, sizeof(msg.text), 0);

// 메시지 수신 (타입 1만)
struct message received;
msgrcv(msgid, &received, sizeof(received.text), 1, 0);
```

| 장점 | 단점 |
|------|------|
| 메시지 타입으로 선택적 수신 | 메시지 크기 제한 |
| 비동기 통신 가능 | 커널 오버헤드 |
| 여러 프로세스가 공유 가능 | POSIX 호환성 이슈 |

### 4. 공유 메모리 (Shared Memory)

여러 프로세스가 **같은 물리 메모리 영역**을 자신의 주소 공간에 매핑하여 직접 읽고 쓴다. **가장 빠른 IPC**.

```
프로세스 A [가상 주소 공간]         프로세스 B [가상 주소 공간]
  0x1000 ─┐                         ┌─ 0x2000
          │    ┌─────────────┐      │
          └───▶│ 공유 메모리  │◀─────┘
               │ (물리 메모리) │
               └─────────────┘
  → 같은 물리 메모리를 서로 다른 가상 주소로 매핑
```

```c
#include <sys/shm.h>
#include <sys/mman.h>

// POSIX 공유 메모리 (현대적 방식)
int fd = shm_open("/my_shm", O_CREAT | O_RDWR, 0666);
ftruncate(fd, 4096);  // 크기 설정

// 메모리 매핑
char *ptr = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

// 쓰기
sprintf(ptr, "Hello from process A!");

// 읽기 (다른 프로세스에서)
printf("받은 메시지: %s\n", ptr);

// 정리
munmap(ptr, 4096);
shm_unlink("/my_shm");
```

**주의**: 공유 메모리는 동기화를 **별도로 처리**해야 한다. 세마포어나 뮤텍스를 함께 사용한다.

```
공유 메모리 + 세마포어:
  Writer:  sem_wait() → 쓰기 → sem_post()
  Reader:  sem_wait() → 읽기 → sem_post()
```

### 5. 시그널 (Signal)

프로세스에 **비동기 이벤트를 알리는** 소프트웨어 인터럽트이다. 데이터는 전달하지 않고 이벤트만 통보한다.

#### 주요 시그널

| 시그널 | 번호 | 기본 동작 | 용도 |
|--------|------|----------|------|
| `SIGHUP` | 1 | 종료 | 설정 리로드 |
| `SIGINT` | 2 | 종료 | Ctrl+C 인터럽트 |
| `SIGKILL` | 9 | 종료 (차단 불가) | 강제 종료 |
| `SIGTERM` | 15 | 종료 | 정상 종료 요청 |
| `SIGSTOP` | 19 | 정지 (차단 불가) | 프로세스 일시 정지 |
| `SIGCONT` | 18 | 계속 | 정지된 프로세스 재개 |
| `SIGCHLD` | 17 | 무시 | 자식 프로세스 종료 알림 |
| `SIGUSR1` | 10 | 종료 | 사용자 정의 |

```bash
# 시그널 전송
kill -SIGTERM 1234        # PID 1234에 종료 요청
kill -9 1234              # 강제 종료 (SIGKILL)
kill -HUP $(cat nginx.pid)  # Nginx 설정 리로드

# 전체 프로세스 그룹에 시그널
kill -TERM -$(pgrep -o myapp)
```

```c
#include <signal.h>

// 시그널 핸들러 등록
void handler(int sig) {
    printf("시그널 %d 수신, 정리 중...\n", sig);
    // 리소스 정리
    exit(0);
}

int main() {
    signal(SIGTERM, handler);   // SIGTERM 핸들러 등록
    signal(SIGINT, handler);    // Ctrl+C 핸들러 등록
    // SIGKILL, SIGSTOP은 핸들러 등록 불가

    while (1) {
        pause();  // 시그널 대기
    }
}
```

### 6. 소켓 (Socket)

네트워크를 통한 IPC. **다른 머신의 프로세스**와도 통신 가능하다. TCP/UDP 프로토콜을 사용한다.

```
서버 프로세스                     클라이언트 프로세스
  socket()                         socket()
  bind()                              │
  listen()                             │
  accept() ◀──── 3-way handshake ──── connect()
     │                                  │
  read/write ◀──── 데이터 교환 ────▶ read/write
     │                                  │
  close()                            close()
```

#### Unix Domain Socket

같은 머신 내 프로세스 간 통신에 최적화된 소켓. 네트워크 스택을 거치지 않아 TCP보다 빠르다.

```bash
# Docker, Nginx, MySQL 등이 Unix Socket 사용
mysql -S /var/run/mysqld/mysqld.sock

# Docker
docker -H unix:///var/run/docker.sock ps
```

```
성능 비교 (같은 머신 내):
  공유 메모리:     ████████████████████  (가장 빠름, 커널 거치지 않음)
  Unix Socket:     ███████████████       (커널 버퍼 사용)
  TCP Loopback:    ██████████            (네트워크 스택 통과)
  Named Pipe:      ████████████████      (단방향, 빠름)
```

### 7. IPC 선택 가이드

```
같은 머신 + 부모-자식?
  ├── Yes → 파이프 (Pipe)
  └── No
       │
       대용량 데이터?
       ├── Yes → 공유 메모리 + 세마포어
       └── No
            │
            이벤트 알림만?
            ├── Yes → 시그널 (Signal)
            └── No
                 │
                 다른 머신과 통신?
                 ├── Yes → 소켓 (TCP/UDP)
                 └── No → 메시지 큐 또는 Unix Socket
```

| 사용 사례 | 추천 IPC |
|----------|---------|
| 쉘 파이프라인 (`ls | grep`) | 파이프 |
| 데이터베이스 공유 버퍼 | 공유 메모리 |
| 웹 서버 ↔ 앱 서버 (같은 머신) | Unix Socket |
| 마이크로서비스 간 통신 | TCP Socket (gRPC) |
| 프로세스 종료 알림 | 시그널 (SIGCHLD) |
| 프로세스 간 작업 큐 | 메시지 큐 |
| Nginx ↔ PHP-FPM | Unix Socket |
| Docker 데몬 통신 | Unix Socket |

### 8. 실무에서의 IPC

#### MSA에서의 IPC

마이크로서비스 아키텍처에서는 프로세스 간 통신이 **네트워크 기반 IPC**로 확장된다.

| 통신 방식 | IPC 매핑 | 예시 |
|----------|---------|------|
| REST API | TCP Socket | HTTP/JSON |
| gRPC | TCP Socket | HTTP/2 + Protobuf |
| 메시지 브로커 | 메시지 큐 확장 | Kafka, RabbitMQ |
| 공유 캐시 | 공유 메모리 확장 | Redis |

#### 컨테이너 환경

```
Docker 컨테이너 간 IPC:
  - 네트워크: Docker Network (브릿지, 오버레이)
  - 볼륨: 공유 볼륨 마운트 (파일 기반 IPC)
  - IPC namespace: --ipc=shareable (공유 메모리)

Kubernetes Pod 내:
  - 같은 Pod의 컨테이너는 IPC namespace 공유
  - localhost로 TCP/Unix Socket 통신 가능
  - emptyDir 볼륨으로 파일 공유
```

## 참고

- [Linux Programmer's Manual — IPC](https://man7.org/linux/man-pages/man7/svipc.7.html)
- [프로세스 & 스레드](Process & Thread/Process & Thread.md) — 프로세스 기본 개념
- [교착 상태](Deadlock.md) — 동기화로 인한 Deadlock
- [메시지 큐](../Backend/Messaging/Message_Queue.md) — MSA에서의 메시징 (Kafka, RabbitMQ)
