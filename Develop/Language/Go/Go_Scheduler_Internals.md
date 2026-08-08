---
title: Go 런타임 스케줄러 내부 구조
tags: [go, os, language]
updated: 2026-07-27
---

# Go 런타임 스케줄러 내부 구조

Go는 goroutine을 OS 스레드 위에서 M:N으로 멀티플렉싱한다. N개의 goroutine을 M개의 OS 스레드에서 실행하되, OS가 아닌 Go 런타임이 스케줄링을 담당한다. 이 구조의 핵심이 GMP 모델이다. 표면적으로 보이는 goroutine의 동작 방식은 내부적으로 꽤 복잡한 과정을 거치는데, 성능 문제를 디버깅하거나 goroutine 수가 수만 개에 달하는 상황에서 이 내부 구조를 모르면 원인을 짚기 어렵다.

## GMP 모델

세 가지 엔티티가 스케줄러를 구성한다.

**G (Goroutine)**: Go 런타임이 관리하는 경량 실행 단위다. goroutine 하나당 `g` 구조체 하나가 존재하며, 스택 포인터·프로그램 카운터·상태 필드 등을 담는다. 초기 스택은 2KB에서 시작해 최대 1GB까지 자동으로 커진다.

**M (Machine)**: 실제 실행을 담당하는 OS 스레드다. `m` 구조체로 표현되며, 코드를 실행하려면 반드시 P를 하나 보유해야 한다. P 없이는 G를 실행하지 못한다.

**P (Processor)**: 스케줄링 컨텍스트다. G를 실행하는 데 필요한 리소스(로컬 실행 큐, 메모리 캐시 등)를 보관한다. P의 수는 `GOMAXPROCS` 값으로 결정되며 프로세스 시작 시 고정된다. M이 아무리 많아도 P 수만큼만 동시에 Go 코드를 실행할 수 있다.

M이 P를 보유한 상태에서 G를 꺼내 실행한다. G가 syscall로 블로킹되면 M은 P를 내려놓고, 다른 M이 그 P를 가져가 계속 실행한다.

## 실행 큐 구조

스케줄러는 두 종류의 큐로 실행 대기 중인 goroutine을 관리한다.

**로컬 실행 큐 (LRQ)**: 각 P마다 붙어있는 256개 용량의 링 버퍼다. 새 goroutine을 만들면 현재 P의 로컬 큐에 먼저 들어간다. 로컬 큐가 꽉 찬 경우에만 글로벌 큐로 넘어간다.

**글로벌 실행 큐 (GRQ)**: 전체 P가 공유하는 큐다. 접근할 때마다 뮤텍스를 잡아야 해서 로컬 큐보다 느리다. 런타임은 스케줄 사이클마다 61회 중 1회 비율로 글로벌 큐를 먼저 확인한다. 이 빈도 제한이 없으면 로컬 큐의 G가 장시간 대기하는 상황이 생긴다.

## Work Stealing

P의 로컬 큐가 비면 idle 상태로 남지 않는다. 다른 P의 로컬 큐에서 절반을 가져온다.

```
P1 로컬 큐: [G5, G6, G7, G8]   (P2가 뒤쪽 절반을 가져감)
P2 로컬 큐: []

stealing 후:
P1 로컬 큐: [G5, G6]
P2 로컬 큐: [G7, G8]
```

뒤쪽에서 가져오는 이유는 앞쪽(곧 실행될 G)을 건드리지 않기 위해서다. work stealing 순서는 현재 P 로컬 큐 → 글로벌 큐(61회마다 1회) → netpoller → 다른 P의 로컬 큐 순이다.

모든 큐가 비고 다른 P에도 G가 없으면 M은 idle 상태가 된다. P를 내려놓고 스레드 풀에 반납된다.

## Goroutine 상태 전이

goroutine은 실행 사이클 동안 여러 상태를 거친다. `runtime/runtime2.go`의 `g` 구조체에서 `status` 필드로 관리한다.

`Grunnable`: 실행 준비가 됐지만 아직 P를 할당받지 못한 상태다. 로컬 큐나 글로벌 큐에 들어가 있다.

`Grunning`: M과 P를 보유하고 실제로 실행 중인 상태다. 한 시점에 하나의 M에서만 실행된다.

`Gwaiting`: 채널 수신, `sync.Mutex.Lock`, `time.Sleep`, 시스템 콜 대기 등으로 블로킹된 상태다. 큐에서 빠져나와 대기 중이며, 조건이 충족되면 `Grunnable`로 돌아간다.

`Gsyscall`: 시스템 콜 실행 중인 상태다. M은 묶여있지만 P는 분리된다.

`Gdead`: 실행이 끝난 상태다. goroutine 구조체는 풀에 반납되어 재사용 대기 상태가 된다.

기본 흐름은 `Grunnable → Grunning → Gdead`이고, 중간에 `Grunning → Gwaiting → Grunnable`이나 `Grunning → Gsyscall → Grunnable` 루프가 섞인다.

## 협력적 선점과 비동기 선점

Go 1.14 이전까지는 협력적 선점만 사용했다. goroutine이 함수 호출이나 채널 연산 같은 safe point에 도달할 때만 스케줄러가 개입할 수 있었다. for문 안에서 함수 호출 없이 계산만 계속하는 goroutine은 P를 독점해 다른 goroutine을 굶길 수 있었다.

```go
// 1.14 이전에는 이 goroutine이 P를 독점한다
go func() {
    i := 0
    for {
        i++ // safe point 없음
    }
}()
```

Go 1.14부터 비동기 선점이 추가됐다. sysmon이 10ms 이상 실행 중인 goroutine을 감지하면 OS signal(SIGURG)을 보내 강제로 중단시킨다. signal handler가 goroutine의 실행을 멈추고 스케줄러로 제어를 돌린다.

단, GC 중 STW(Stop-The-World)를 시작하려면 모든 goroutine이 safe point에 도달해야 한다. 이 경우는 비동기 선점이 아닌 협력적 방식으로 각 goroutine에 선점 요청 플래그를 세운다.

## Syscall 처리 시 M-P 분리

blocking syscall(파일 읽기, 네트워크 I/O 등)이 들어오면 해당 M은 OS에서 블로킹된다. M이 P를 계속 붙들면 다른 goroutine이 실행되지 못한다.

M이 blocking syscall에 진입하기 전, 런타임은 P를 분리(handoff)한다. 분리된 P는 idle M이나 새로 만든 M에 넘겨진다. syscall이 끝나면 원래 M은 P를 다시 찾으려 한다. P가 없으면 G를 글로벌 큐에 넣고 idle 상태가 된다.

```
[syscall 전]  G가 M1-P1에서 실행 중
[syscall 진입] M1 블로킹, P1을 M2에게 넘김
              M2(또는 새 M)가 P1을 받아 다른 G 실행
[syscall 완료] M1이 빈 P를 찾는다
              P가 없으면 G를 글로벌 큐에 넣고 M1 idle
```

sysmon은 syscall에 묶인 M이 P를 20μs 이상 보유하면 P를 강제로 빼앗는다(retake). 이 임계값은 `runtime/proc.go`의 `retake` 함수에서 확인한다.

## netpoller와 Non-blocking I/O

Go의 네트워크 I/O는 내부적으로 전부 non-blocking이다. `net.Conn.Read()`를 호출하면 blocking처럼 보이지만 OS 스레드를 블로킹하지 않는다.

소켓을 non-blocking 모드로 열고 read를 시도한다. 데이터가 없으면 `EAGAIN`을 받고, goroutine은 `Gwaiting` 상태로 전환되며 fd를 epoll/kqueue에 등록한다. M은 P를 보유한 채 다른 G를 실행한다. 데이터가 준비되면 netpoller가 깨어나 해당 goroutine을 `Grunnable`로 만든다.

```go
// 사용자 코드는 그냥 Read를 호출하지만
// 내부에서 goroutine이 park되고 다른 G가 실행된다
n, err := conn.Read(buf)
```

netpoller는 별도 OS 스레드에서 `epoll_wait`(Linux) / `kqueue`(macOS)로 I/O 이벤트를 기다린다. 이 스레드는 P 없이 동작하므로 GOMAXPROCS에 영향을 주지 않는다.

수만 개의 동시 연결을 처리할 때 OS 스레드를 수만 개 만들 필요가 없는 이유가 이 구조다. goroutine이 I/O를 대기하는 동안 M은 다른 goroutine을 실행하고 있다.

## sysmon 감시 스레드

sysmon은 P 없이 돌아가는 특수 OS 스레드다. Go 런타임이 시작될 때 만들어지며, 다른 P·M·G와 독립적으로 동작한다.

주로 하는 일은 네 가지다. 10ms 이상 실행 중인 goroutine에 SIGURG를 보내 비동기 선점을 유발한다. syscall에 묶인 M이 너무 오래 P를 보유하면 P를 강제로 빼앗는다. idle P가 있을 때 netpoller를 호출해 I/O가 완료된 goroutine을 깨운다. 힙 사용량이 임계치를 초과하면 GC를 시작하고, `time.Sleep`으로 대기 중인 goroutine 중 만료된 것을 깨운다.

```go
// runtime/proc.go의 sysmon 루프 (단순화)
func sysmon() {
    for {
        checkdead()     // deadlock 감지
        retake(now)     // P retake + 선점
        forcegchelper() // GC 강제 트리거
        netpoll(delay)  // I/O 이벤트 확인
        sleep(delay)    // 20μs ~ 10ms
    }
}
```

sysmon의 sleep 간격은 초기 20μs에서 시작해 idle 상태가 지속되면 최대 10ms까지 늘어난다. 시스템이 바쁠수록 더 자주 깨어나는 구조다.

## 스케줄러 디버깅

스케줄러 동작을 직접 보려면 `GODEBUG=schedtrace=1000`을 사용한다. 1000ms 간격으로 스케줄러 상태를 stderr에 출력한다.

```
SCHED 1000ms: gomaxprocs=4 idleprocs=1 threads=6 spinningthreads=0 idlethreads=2 runqueue=3 [2 0 1 0]
```

`idleprocs`는 idle 상태인 P 수, `threads`는 전체 OS 스레드 수, `runqueue`는 글로벌 큐의 G 수, 마지막 배열은 각 P의 로컬 큐 G 수다.

글로벌 큐(`runqueue`)가 계속 높으면 P가 부족하거나 goroutine 생성 속도가 처리 속도를 앞선다. `threads`가 계속 늘어나면 blocking syscall이 M을 계속 소모하는 중이다.

```bash
GODEBUG=schedtrace=1000,scheddetail=1 ./myapp 2>&1 | grep "^SCHED"
```

`scheddetail=1`을 추가하면 각 G, M, P의 상태를 상세하게 출력한다. pprof goroutine 덤프와 함께 보면 어떤 goroutine이 어떤 이유로 대기 중인지 파악한다.
