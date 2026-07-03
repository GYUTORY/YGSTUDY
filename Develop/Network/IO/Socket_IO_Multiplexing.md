---
title: 소켓 I/O 멀티플렉싱 - select, poll, epoll, kqueue, IOCP
tags:
  - Network
  - IO
  - Multiplexing
  - epoll
  - kqueue
  - IOCP
  - C10K
updated: 2026-05-04
---

## I/O 멀티플렉싱이 왜 필요한가

서버가 클라이언트 한 명만 받는다면 멀티플렉싱은 필요 없다. `accept()` 하고 `read()` 하고 `write()` 하면 끝이다. 문제는 클라이언트가 100명, 1000명, 10만 명이 될 때 시작된다.

가장 단순한 해법은 클라이언트마다 스레드를 띄우는 thread-per-connection 모델이다. 5년 전쯤 사내 정산 서버를 이 방식으로 운영했는데, 평소엔 잘 돌다가 트래픽이 몰리면 스레드가 5천 개씩 생기면서 컨텍스트 스위치 오버헤드로 CPU가 멎어버렸다. 스레드 하나당 기본 스택이 1MB라서 메모리도 5GB가 그냥 날아간다. 이게 바로 C10K 문제의 본질이다.

I/O 멀티플렉싱은 한 스레드가 여러 소켓을 동시에 감시하다가 "어느 소켓이 읽을 준비가 됐는지" 커널에 물어보는 방식이다. blocking I/O처럼 한 소켓에 묶이지 않으니 스레드 하나로 수만 개의 연결을 처리할 수 있다.

## blocking, non-blocking, 그리고 멀티플렉싱

용어가 자주 헷갈린다. 명확히 구분해두자.

- **blocking I/O**: `read()` 호출하면 데이터가 올 때까지 스레드가 멈춘다.
- **non-blocking I/O**: `read()` 호출했는데 데이터가 없으면 즉시 `EAGAIN`(또는 `EWOULDBLOCK`)을 반환한다. 폴링으로 계속 호출해야 데이터를 받을 수 있다.
- **I/O 멀티플렉싱**: 여러 fd를 한 번에 감시하다가 준비된 fd가 생기면 알려준다. `select`, `poll`, `epoll`, `kqueue`가 여기 속한다.
- **비동기 I/O (AIO)**: 커널이 데이터를 사용자 버퍼까지 복사한 뒤 완료 통보한다. 리눅스의 `io_uring`, 윈도우의 IOCP가 진정한 의미의 AIO다.

흔히 epoll을 비동기 I/O라고 부르지만 엄밀히는 non-blocking I/O 알림 메커니즘이다. 데이터 복사는 여전히 사용자가 `read()`를 호출해서 직접 한다. IOCP만 데이터 복사까지 커널이 해준다.

## select

가장 오래된 멀티플렉싱 API다. 1983년 BSD에서 등장했고 모든 OS에서 동작한다.

```c
#include <sys/select.h>

fd_set readfds;
FD_ZERO(&readfds);
FD_SET(server_fd, &readfds);

struct timeval tv = {5, 0};
int ready = select(server_fd + 1, &readfds, NULL, NULL, &tv);

if (ready > 0 && FD_ISSET(server_fd, &readfds)) {
    int client_fd = accept(server_fd, NULL, NULL);
}
```

select의 치명적 한계는 두 가지다.

첫째, `fd_set`이 비트마스크라서 감시 가능한 fd 수가 `FD_SETSIZE`(보통 1024)로 고정된다. 컴파일 타임 상수라 런타임에 늘릴 수 없다. 1024개 넘는 연결을 받으려면 select로는 안 된다.

둘째, 호출할 때마다 모든 fd 비트맵을 커널로 복사하고, 커널은 모든 fd를 순회하며 상태를 체크한다. 1000개 감시하면 매번 1000번 검사하는 O(n) 동작이다. 게다가 select가 리턴하면 어느 fd가 준비됐는지 모르니 다시 1000번 `FD_ISSET`을 돌려야 한다. fd 수가 많아지면 select 호출 자체가 병목이 된다.

select가 리턴하면 `fd_set`이 변경되니 매번 다시 세팅해야 한다는 점도 실수하기 좋은 포인트다.

## poll

select의 1024 한계를 풀려고 1986년 System V에서 도입됐다.

```c
#include <poll.h>

struct pollfd fds[MAX_CLIENTS];
fds[0].fd = server_fd;
fds[0].events = POLLIN;

int ready = poll(fds, nfds, 5000);

for (int i = 0; i < nfds; i++) {
    if (fds[i].revents & POLLIN) {
        // 처리
    }
}
```

`pollfd` 배열을 동적으로 할당하니 fd 개수 제한이 사라졌다. 하지만 본질적인 O(n) 문제는 그대로다. 호출할 때마다 모든 pollfd를 커널로 복사하고, 커널은 전부 순회한다. 리턴 후 어느 fd가 준비됐는지 찾으려면 사용자도 전부 순회해야 한다.

select보다 약간 낫지만 fd가 수만 개로 늘어나면 똑같이 무너진다.

## epoll

리눅스 2.5.44에서 등장한 메커니즘이다. select/poll의 O(n) 문제를 O(1)에 가깝게 풀었다.

핵심 아이디어는 "감시 대상 fd 목록을 커널에 등록해두고, 이벤트가 발생한 fd만 받아오자"다. 매번 전체 목록을 주고받는 select/poll과 결정적으로 다르다.

```c
#include <sys/epoll.h>

int epfd = epoll_create1(0);

struct epoll_event ev;
ev.events = EPOLLIN;
ev.data.fd = server_fd;
epoll_ctl(epfd, EPOLL_CTL_ADD, server_fd, &ev);

struct epoll_event events[64];
int n = epoll_wait(epfd, events, 64, 5000);

for (int i = 0; i < n; i++) {
    int fd = events[i].data.fd;
    // 처리
}
```

세 가지 시스템 콜로 나뉜다.

- `epoll_create1()`: 커널에 epoll 인스턴스를 만든다. 내부적으로 red-black tree와 ready list를 관리한다.
- `epoll_ctl()`: 감시 대상 fd를 등록/수정/삭제한다. 한 번만 등록하면 끝이다.
- `epoll_wait()`: 준비된 fd만 받아온다. ready list에서 가져오니 O(준비된 fd 수).

10만 개 fd를 감시해도 실제로 데이터가 온 100개만 epoll_wait이 반환한다. 사용자가 전체를 순회할 일이 없다.

내부적으로 fd마다 콜백이 등록돼서, 데이터가 도착하면 해당 fd가 ready list에 추가된다. 인터럽트 기반이라 폴링 오버헤드가 없다.

## kqueue

FreeBSD, macOS, NetBSD가 쓰는 메커니즘이다. epoll과 비슷한 시기(2000년경)에 나왔는데 설계가 더 일반적이다.

```c
#include <sys/event.h>

int kq = kqueue();

struct kevent change;
EV_SET(&change, server_fd, EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, NULL);

struct kevent events[64];
int n = kevent(kq, &change, 1, events, 64, NULL);
```

kqueue가 epoll보다 강한 점은 소켓 이벤트뿐 아니라 파일 변경, 시그널, 프로세스 종료, 타이머까지 같은 인터페이스로 처리할 수 있다는 거다. `EVFILT_READ`, `EVFILT_VNODE`, `EVFILT_SIGNAL`, `EVFILT_TIMER` 등 다양한 필터를 지원한다.

API는 `EV_SET`이라는 매크로로 변경 사항과 결과를 한 구조체에 담는다. 한 번의 `kevent()` 호출로 등록과 대기를 동시에 할 수 있어서 시스템 콜 횟수를 줄인다.

macOS에서 Node.js나 nginx를 돌리면 내부적으로 kqueue를 쓴다. epoll과 동작 모델은 거의 같다고 봐도 된다.

## IOCP

윈도우의 I/O Completion Port다. 위 셋과는 모델이 근본적으로 다르다.

select/poll/epoll/kqueue는 "fd가 준비됐다"는 readiness 알림이다. 사용자는 알림을 받고 직접 `read()`를 호출해야 한다. 반면 IOCP는 "I/O가 완료됐다"는 completion 알림이다. 사용자가 `WSARecv()`로 비동기 읽기를 요청하면 커널이 데이터를 사용자 버퍼까지 복사한 뒤 완료를 알려준다.

```c
HANDLE iocp = CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, 0, 0);
CreateIoCompletionPort((HANDLE)socket, iocp, (ULONG_PTR)context, 0);

WSARecv(socket, &buf, 1, NULL, &flags, &overlapped, NULL);

DWORD bytes;
ULONG_PTR key;
LPOVERLAPPED ov;
GetQueuedCompletionStatus(iocp, &bytes, &key, &ov, INFINITE);
```

스레드 풀이 `GetQueuedCompletionStatus()`로 대기하다가 완료된 I/O를 처리한다. 커널이 알아서 활성 스레드 수를 CPU 코어 수에 맞게 조절해서 컨텍스트 스위치를 최소화한다.

성능은 epoll/kqueue와 비슷하지만 프로그래밍 모델은 더 복잡하다. 모든 I/O 호출에 `OVERLAPPED` 구조체를 매달아야 하고 라이프타임 관리가 까다롭다.

리눅스에도 비슷한 모델이 있다. 옛날 `aio_*` API는 거의 안 쓰이고, 2019년 등장한 `io_uring`이 IOCP와 가장 유사한 진정한 비동기 I/O다.

## 다섯 가지 비교

| 특성 | select | poll | epoll | kqueue | IOCP |
|---|---|---|---|---|---|
| OS | 모든 POSIX, Windows | POSIX | Linux | BSD, macOS | Windows |
| fd 개수 제한 | FD_SETSIZE(1024) | 없음 | 없음 | 없음 | 없음 |
| 시간 복잡도 | O(n) | O(n) | O(1) | O(1) | O(1) |
| 매 호출 데이터 복사 | 전체 fd 셋 | 전체 pollfd | 없음 | 변경분만 | 없음 |
| 모델 | readiness | readiness | readiness | readiness | completion |
| edge-trigger | 불가 | 불가 | 가능 | 가능 | N/A |

## level-triggered와 edge-triggered

epoll과 kqueue가 지원하는 두 가지 트리거 모드다. 잘못 이해하면 데이터 누락이나 무한 루프를 만든다.

**level-triggered (LT)**: fd에 읽을 데이터가 있는 동안 계속 알린다. 100바이트 도착했는데 50바이트만 읽으면 다음 `epoll_wait()`도 그 fd를 다시 알려준다. select/poll의 기본 동작과 같다. epoll의 기본값이기도 하다.

**edge-triggered (ET)**: 상태가 "데이터 없음 → 있음"으로 바뀐 순간에만 알린다. 100바이트 중 50바이트만 읽고 다음 `epoll_wait()`을 부르면 새 데이터가 오기 전엔 알림이 안 온다. 알림 한 번에 가능한 모든 데이터를 읽어야 한다.

ET 모드를 쓸 때 반드시 지켜야 할 규칙이 있다.

```c
ev.events = EPOLLIN | EPOLLET;
epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev);

while (1) {
    ssize_t n = read(fd, buf, sizeof(buf));
    if (n == -1) {
        if (errno == EAGAIN) break;  // 모든 데이터 다 읽음
        // 에러 처리
    }
    if (n == 0) break;  // 연결 종료
    // 데이터 처리
}
```

1. fd는 반드시 non-blocking이어야 한다. blocking이면 `EAGAIN` 없이 멈춘다.
2. `EAGAIN`이 나올 때까지 read를 반복해야 한다. 한 번만 읽고 끝내면 남은 데이터를 영영 못 읽는다.
3. write도 마찬가지로 `EAGAIN`이 나올 때까지 써야 한다.

ET가 LT보다 빠른 이유는 `epoll_wait` 호출 횟수가 줄어서다. 같은 fd가 반복 알림되지 않으니 시스템 콜 오버헤드가 적다. 하지만 코딩 난이도가 올라가서 nginx 같은 고성능 서버 정도가 아니면 LT를 권한다.

실제로 신입 시절 ET 모드에서 read를 한 번만 호출했다가 클라이언트가 보낸 큰 메시지가 잘려서 들어오는 버그를 만든 적이 있다. 디버깅에 며칠 걸렸다. ET를 쓸 거면 처음부터 루프로 감싸야 한다.

## C10K 문제

1999년 댄 케겔(Dan Kegel)이 정리한 문제다. "한 서버에서 동시 연결 1만 개를 어떻게 처리할까?" thread-per-connection으로는 답이 안 나오니 새로운 접근이 필요했다.

해결의 축은 세 가지였다.

1. **non-blocking I/O + I/O 멀티플렉싱**: 스레드를 늘리지 말고 한 스레드가 여러 연결을 다루자. 이게 epoll/kqueue의 직접적인 동기다.
2. **이벤트 루프 모델**: 콜백 기반으로 I/O 이벤트를 처리. nginx, Node.js, Redis가 모두 이 패턴.
3. **커널 최적화**: zero-copy(sendfile), SO_REUSEPORT, TCP fast open 등.

C10K가 풀린 뒤로는 C10M(천만 동시 연결) 문제가 새 화두가 됐다. 여기선 커널 자체가 병목이라 DPDK처럼 커널을 우회하는 user-space 네트워킹으로 간다.

## Non-blocking I/O와 이벤트 루프

이벤트 루프의 기본 골격은 단순하다.

```c
int epfd = epoll_create1(0);
// listen 소켓 등록 (LT 또는 ET, non-blocking 설정)

while (running) {
    int n = epoll_wait(epfd, events, MAX_EVENTS, -1);
    for (int i = 0; i < n; i++) {
        if (events[i].data.fd == server_fd) {
            // 새 연결 accept
            int client_fd = accept4(server_fd, NULL, NULL, SOCK_NONBLOCK);
            // epoll에 등록
        } else {
            // 클라이언트 fd 처리 (read/write)
        }
    }
}
```

이벤트 루프의 황금 규칙은 "절대 블로킹하지 말 것"이다. 한 콜백이 1초 멈추면 그동안 다른 모든 연결이 멈춘다. DB 쿼리, 파일 I/O, 암호화 같은 무거운 작업은 별도 스레드 풀로 넘긴다.

Node.js가 정확히 이 구조다. 메인 스레드(이벤트 루프)는 epoll/kqueue로 네트워크 I/O를 돌리고, libuv가 관리하는 4개짜리 스레드 풀(`UV_THREADPOOL_SIZE`)이 파일 I/O와 DNS 같은 블로킹 작업을 처리한다.

## Netty, libuv, Node.js의 내부

각 프레임워크가 어떻게 멀티플렉싱을 쓰는지 보면 추상화가 어떻게 만들어지는지 보인다.

### libuv

Node.js가 쓰는 C 라이브러리다. 플랫폼 차이를 흡수한다.

- 리눅스: epoll
- macOS/BSD: kqueue
- 윈도우: IOCP
- Solaris: event ports

`uv_loop_t`가 이벤트 루프 인스턴스다. 내부에서 단계별(timer → pending → poll → check → close)로 콜백을 실행한다. poll 단계에서 epoll/kqueue/IOCP를 호출한다.

윈도우의 IOCP는 completion 모델이라 readiness 모델인 epoll/kqueue와 의미가 다르지만, libuv가 그 차이를 숨겨준다.

### Node.js

libuv 위에 V8을 얹은 구조다. 자바스크립트 코드는 메인 스레드에서만 실행되지만 I/O는 libuv가 비동기로 처리한다.

`fs.readFile`은 libuv 스레드 풀로 가고, `http.get`은 epoll/kqueue로 처리된다. 같은 비동기 콜백이라도 내부 경로가 다르다.

CPU 바운드 작업을 메인 스레드에서 돌리면 이벤트 루프가 멎는다. JSON 파싱이 1MB 넘어가면 눈에 띄게 느려지는 게 이 때문이다. `worker_threads`로 빼야 한다.

### Netty

JVM 진영의 비동기 네트워크 프레임워크다. NIO 추상화 위에 만들어졌다.

- `NioEventLoopGroup`: 자바 NIO Selector를 쓴다. 내부적으로 epoll/kqueue/IOCP에 매핑되지만 JNI 오버헤드가 있다.
- `EpollEventLoopGroup`: 리눅스 전용. JNI로 epoll을 직접 호출한다. NIO보다 GC 압박이 적고 ET 모드 같은 리눅스 고유 기능을 쓸 수 있다.
- `KQueueEventLoopGroup`: BSD/macOS 전용.

리눅스 프로덕션에선 `EpollEventLoopGroup`이 권장된다. 자바의 기본 NIO가 어차피 리눅스에선 epoll을 쓰지만, 한 단계 추상화가 끼어 있어서 마이크로벤치에서 차이가 보인다.

Netty의 EventLoop는 "한 EventLoop = 한 스레드 = 한 epoll fd"다. 채널이 한번 EventLoop에 바인딩되면 그 채널의 모든 콜백은 동일 스레드에서 실행되니 공유 상태에 락을 걸 필요가 없다.

## accept thundering herd

여러 프로세스/스레드가 같은 listen 소켓에서 `accept()`를 기다릴 때, 새 연결이 들어오면 커널이 모두를 깨우는 현상이다. 한 명만 accept에 성공하고 나머지는 다시 잠든다. 깨운 비용이 낭비된다.

prefork 모델이나 멀티 스레드 accept에서 자주 본다. Apache의 prefork MPM이 대표적이었다.

리눅스는 2.6 시절부터 accept thundering herd를 어느 정도 줄였다. `accept()`는 하나만 깨우게 패치됐다. 하지만 epoll에선 여전히 문제다. 여러 epoll 인스턴스가 같은 listen fd를 등록하고 `epoll_wait`로 대기하면, 새 연결이 들어올 때 모든 epoll_wait가 깨어난다. 리눅스 4.5의 `EPOLLEXCLUSIVE` 플래그가 이걸 해결했다.

```c
ev.events = EPOLLIN | EPOLLEXCLUSIVE;
epoll_ctl(epfd, EPOLL_CTL_ADD, listen_fd, &ev);
```

이러면 새 연결당 한 epoll_wait만 깨어난다.

## SO_REUSEPORT

리눅스 3.9에 들어온 옵션이다. 여러 소켓이 같은 포트에 바인딩할 수 있게 해준다. BSD에는 더 일찍 있었다.

```c
int sock = socket(AF_INET, SOCK_STREAM, 0);
int opt = 1;
setsockopt(sock, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt));
bind(sock, ...);
listen(sock, ...);
```

같은 포트에 여러 listen 소켓을 만들고 각 워커가 자기 소켓만 listen 한다. 커널이 들어오는 연결을 워커별로 분배한다. 분배는 5-tuple 해시 기반이라 부하가 고르게 퍼진다.

SO_REUSEPORT가 thundering herd를 근본적으로 해결한다. 워커마다 별도 listen 큐를 가지니 커널이 한 명만 깨우면 된다. nginx 1.9.1부터 SO_REUSEPORT를 지원하면서 멀티 워커 환경의 성능이 크게 개선됐다.

주의할 점: SO_REUSEPORT는 같은 UID로 만든 소켓끼리만 공유된다. 보안 목적이다. 그리고 워커가 죽으면 그 워커의 listen 큐에 쌓인 연결은 RST된다. 그래서 graceful shutdown이 까다롭다.

`SO_REUSEADDR`와 헷갈리지 마라. `SO_REUSEADDR`는 TIME_WAIT 상태의 포트를 재사용할 수 있게 하는 옵션이고, `SO_REUSEPORT`는 동시에 같은 포트를 여러 소켓이 바인딩할 수 있게 하는 옵션이다.

## 실무에서 마주치는 문제

### epoll에서 fd가 자꾸 빠져나간다

`close(fd)` 하면 epoll에서 자동으로 제거된다고 알려져 있지만, 다른 프로세스가 `dup`한 fd가 있으면 안 빠진다. 명시적으로 `epoll_ctl(epfd, EPOLL_CTL_DEL, fd, NULL)` 호출하는 습관을 들이는 게 안전하다.

### EPOLLONESHOT

ET 모드에서도 멀티스레드 환경이면 같은 fd가 동시에 여러 워커에 알림될 수 있다. `EPOLLONESHOT` 플래그를 주면 한 번 알림 후 자동으로 비활성화된다. 처리 끝나면 `EPOLL_CTL_MOD`로 다시 활성화해야 한다. 워커 풀에서 fd를 안전하게 분배할 때 자주 쓴다.

### Selector wakeup 비용

자바 NIO Selector나 epoll에서 다른 스레드가 깨우려 할 때 보통 self-pipe trick이나 `eventfd`를 쓴다. `eventfd`가 self-pipe보다 가볍다. Netty는 `eventfd`를 쓴다.

### Backlog 튜닝

`listen(fd, backlog)`의 backlog는 SYN_RCVD 상태와 ESTABLISHED 상태 큐 크기에 영향을 준다. 리눅스에선 `/proc/sys/net/core/somaxconn`이 상한이다. 기본값이 128(커널 5.4부터 4096)인데 트래픽 많은 서버는 작다. accept가 못 따라가면 새 연결이 RST된다. `ss -lnt`로 큐 사용량을 모니터링할 수 있다.

## 정리

select/poll은 1024개 한계와 O(n) 동작 때문에 현대 서버에선 거의 안 쓴다. 리눅스는 epoll, BSD/macOS는 kqueue, 윈도우는 IOCP가 사실상 표준이다. 모델 차이(readiness vs completion)가 있어서 코드 호환성은 없지만 libuv 같은 추상화 레이어가 그 간격을 메운다.

ET 모드는 빠르지만 까다롭다. non-blocking + EAGAIN 루프를 정확히 구현 못 하면 데이터가 사라진다. 처음 작성하는 서버라면 LT 모드로 시작하고, 정말 필요한 경우에만 ET로 옮긴다.

다중 워커 환경에선 SO_REUSEPORT가 거의 필수다. thundering herd를 피하면서 부하 분산까지 커널이 해주니 따로 로드밸런서를 둘 필요가 줄어든다.

C10K가 풀린 시대지만 그 해법(epoll, 이벤트 루프, non-blocking)은 여전히 모든 고성능 서버의 기반이다. Node.js를 쓰든 Netty를 쓰든 Redis를 쓰든 그 밑에선 같은 메커니즘이 돈다.
