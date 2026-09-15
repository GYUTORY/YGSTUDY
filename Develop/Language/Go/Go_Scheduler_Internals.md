---
title: Go 런타임 스케줄러 내부 구조
tags: [go, os, language, performance]
updated: 2026-09-15
---

# Go 런타임 스케줄러 내부 구조

Go는 goroutine을 OS 스레드 위에서 M:N으로 멀티플렉싱한다. N개의 goroutine을 M개의 OS 스레드에서 실행하되, OS가 아닌 Go 런타임이 스케줄링을 담당한다. 이 구조의 핵심이 GMP 모델이다. goroutine이 수만 개에 달하는 상황에서 성능 문제를 디버깅하거나 goroutine 누수를 추적할 때, 이 내부 구조를 모르면 원인을 찾기 어렵다.

## GMP 모델

세 가지 엔티티가 스케줄러를 구성한다.

**G (Goroutine)**: Go 런타임이 관리하는 경량 실행 단위다. goroutine 하나당 `g` 구조체 하나가 존재하며, `runtime/runtime2.go`에 정의돼 있다. 스택 포인터·프로그램 카운터·상태 필드(`status`)·현재 보유 중인 M과 P에 대한 포인터를 담는다. defer 체인과 panic 정보도 `g` 구조체 안에 저장된다.

**M (Machine)**: 실제 실행을 담당하는 OS 스레드다. `m` 구조체로 표현되며, 코드를 실행하려면 반드시 P를 하나 보유해야 한다. P 없이는 G를 실행하지 못한다. M 수는 `GOMAXPROCS`와 무관하게 blocking syscall에 의해 늘어날 수 있다. 기본 한계는 10,000개이며 `runtime/debug.SetMaxThreads`로 조정한다.

**P (Processor)**: 스케줄링 컨텍스트다. G를 실행하는 데 필요한 로컬 실행 큐(256개 링 버퍼), 메모리 캐시(`mcache`), 작은 객체 풀을 보관한다. P의 수는 `GOMAXPROCS`로 결정되며 프로세스 시작 시 고정된다. M이 아무리 많아도 P 수만큼만 동시에 Go 코드를 실행할 수 있다.

```
          goroutine pool
         G1  G2  G3  G4
          |   |
    P1 --[LRQ: G1, G2]-- M1 (실행 중)
    P2 --[LRQ: G3, G4]-- M2 (실행 중)
    P3 --[LRQ: empty ]-- M3 (stealing)
    P4 --[LRQ: empty ]-- idle

    GRQ (글로벌 큐): G5, G6, G7
```

M이 P를 보유한 상태에서 G를 꺼내 실행한다. G가 blocking syscall로 넘어가면 M은 P를 내려놓고, 다른 M이 그 P를 가져가 실행을 이어간다.

## 실행 큐와 Work Stealing

스케줄러는 두 종류의 큐로 실행 대기 중인 goroutine을 관리한다.

**로컬 실행 큐 (LRQ)**: 각 P마다 붙어있는 256개 용량의 링 버퍼다. 새 goroutine을 만들면 현재 P의 로컬 큐에 먼저 들어간다. 로컬 큐가 꽉 찬 경우에만 글로벌 큐로 넘어간다. 로컬 큐는 락 없이 접근할 수 있어서 빠르다.

**글로벌 실행 큐 (GRQ)**: 전체 P가 공유하는 큐다. 접근할 때마다 뮤텍스를 잡아야 해서 로컬 큐보다 느리다. 런타임은 스케줄 사이클마다 61회 중 1회 비율로 글로벌 큐를 먼저 확인한다. 이 빈도 제한이 없으면 로컬 큐의 G가 장시간 대기할 수 있다.

P의 로컬 큐가 비면 idle 상태로 남지 않는다. 다른 P의 로컬 큐에서 절반을 가져온다(work stealing).

```
stealing 전:
  P1 로컬 큐: [G5, G6, G7, G8]
  P2 로컬 큐: []

stealing 후 (P2가 P1 뒤쪽 절반을 가져감):
  P1 로컬 큐: [G5, G6]
  P2 로컬 큐: [G7, G8]
```

뒤쪽에서 가져오는 이유는 앞쪽(곧 실행될 G)을 건드리지 않기 위해서다. G를 가져가는 순서는 현재 P 로컬 큐 → 글로벌 큐(61회마다 1회) → netpoller → 다른 P의 로컬 큐 순이다.

모든 큐가 비고 다른 P에도 G가 없으면 M은 idle 상태가 된다. P를 내려놓고 스레드 풀에 반납된다.

## Goroutine 생명주기

### 상태 전이

goroutine은 실행 사이클 동안 여러 상태를 거친다. `runtime/runtime2.go`의 `g` 구조체 `status` 필드로 관리한다.

`Grunnable`: 실행 준비가 됐지만 P를 아직 할당받지 못한 상태다. 로컬 큐나 글로벌 큐에 들어가 있다.

`Grunning`: M과 P를 보유하고 실제로 실행 중인 상태다. 한 시점에 하나의 M에서만 실행된다.

`Gwaiting`: 채널 수신, `sync.Mutex.Lock`, `time.Sleep`, I/O 대기 등으로 블로킹된 상태다. 큐에서 빠져나와 대기 중이며, 조건이 충족되면 `Grunnable`로 돌아간다.

`Gsyscall`: blocking syscall 실행 중인 상태다. M은 묶여있지만 P는 분리된다.

`Gdead`: 실행이 끝난 상태다. goroutine 구조체는 풀에 반납되어 재사용 대기 상태가 된다.

기본 흐름은 `Grunnable → Grunning → Gdead`이고, 중간에 `Grunning → Gwaiting → Grunnable`이나 `Grunning → Gsyscall → Grunnable` 루프가 섞인다.

### 생성·소멸 비용

`go` 키워드 하나의 실제 비용은 생각보다 낮다. 벤치마크 기준으로 goroutine 하나 생성에 약 2~5μs, 약 2~4KB 메모리가 든다. OS 스레드 생성(`pthread_create`)이 수십μs ~ 수백μs인 것과 비교하면 훨씬 가볍다.

비용이 낮은 이유는 두 가지다. 첫째, goroutine은 OS 스레드가 아니라 런타임 내부의 구조체 할당이다. 둘째, 종료된 goroutine의 `g` 구조체와 스택은 풀에 반납돼 다음 `go` 호출 시 재사용된다.

그럼에도 무제한으로 생성하면 문제가 된다. goroutine 하나가 최소 2~4KB 스택을 점유하기 때문에, 100만 개면 2~4GB다. 스케줄러 큐 관리와 GC 루트 탐색 비용도 goroutine 수에 비례해 늘어난다.

```go
// goroutine pool 없이 무한 생성 — 메모리와 스케줄러 부하
for req := range requests {
    go handle(req)
}

// worker pool 패턴 — goroutine 수 제한
sem := make(chan struct{}, 100)
for req := range requests {
    sem <- struct{}{}
    go func(r Request) {
        defer func() { <-sem }()
        handle(r)
    }(req)
}
```

### 스택 성장 메커니즘

goroutine은 초기 스택이 2KB에서 시작한다. 스택이 부족해지면 런타임이 자동으로 키운다. 커지는 방식은 Go 버전에 따라 달랐다.

**Go 1.3 이전: segmented stack**

스택이 부족하면 새 세그먼트를 할당해 연결리스트로 이었다. 이 구조는 "hot split" 문제가 있었다. 함수 호출이 세그먼트 경계 근처에서 반복되면 스택 성장·축소가 계속 발생해 성능이 급락했다.

**Go 1.4+: contiguous stack (copying)**

스택이 꽉 차면 두 배 크기의 새 메모리를 할당하고 전체 내용을 복사한다. 스택 내 포인터는 전부 새 주소로 재조정된다. 세그먼트 연결리스트를 없애서 hot split 문제가 사라졌다.

```
초기:  [  2KB  ]
성장:  [  4KB  ] (복사)
성장:  [  8KB  ] (복사)
성장:  [ 16KB  ] (복사)
...
최대: [  1GB  ] (runtime.maxstacksize)
```

스택 축소는 GC 도중 발생한다. 현재 사용 중인 스택이 최대 용량의 1/4 미만이면 절반으로 줄인다. 이 기준이 없으면 일시적으로 커진 스택이 영구적으로 메모리를 점유한다.

스택 복사 시 goroutine의 모든 스택 포인터를 업데이트해야 하므로 불변 규칙이 있다. **스택 상의 goroutine 포인터를 힙에 저장하면 런타임이 이를 추적하지 못한다.** `go:noescape` 어노테이션이 없는 함수에 스택 주소를 넘기면 컴파일러가 해당 변수를 힙으로 escape시키는 이유가 이것이다.

```go
// 스택 escape 예시
func badStore(p **int) {
    x := 42
    *p = &x  // x는 힙으로 escape된다
}
```

`go build -gcflags="-m"` 으로 어떤 변수가 heap으로 escape되는지 확인한다.

## 선점 스케줄링

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

GC 중 STW(Stop-The-World)를 시작하려면 모든 goroutine이 safe point에 도달해야 한다. 이 경우는 비동기 선점이 아닌 협력적 방식으로 각 goroutine에 선점 요청 플래그(`stackPreempt`)를 세운다. 다음 함수 프롤로그에서 goroutine이 이 플래그를 확인하고 스케줄러로 제어를 넘긴다.

## Syscall 처리와 netpoller

### Blocking Syscall

blocking syscall(파일 읽기, `os.File` 기반 I/O 등)이 들어오면 해당 M은 OS에서 블로킹된다. M이 P를 계속 붙들면 다른 goroutine이 실행되지 못한다.

M이 blocking syscall에 진입하기 전, 런타임은 P를 분리(handoff)한다. 분리된 P는 idle M이나 새로 만든 M에 넘겨진다. syscall이 끝나면 원래 M은 P를 다시 찾으려 한다. P가 없으면 G를 글로벌 큐에 넣고 idle 상태가 된다.

```
[syscall 전]   G가 M1-P1에서 실행 중
[syscall 진입] M1 블로킹, P1을 M2에게 넘김
               M2(또는 새 M)가 P1을 받아 다른 G 실행
[syscall 완료] M1이 빈 P를 찾는다
               P가 없으면 G를 글로벌 큐에 넣고 M1 idle
```

sysmon은 syscall에 묶인 M이 P를 20μs 이상 보유하면 P를 강제로 빼앗는다(retake). `runtime/proc.go`의 `retake` 함수에서 확인한다.

blocking syscall을 대량으로 호출하면 M 수가 계속 늘어난다. `GODEBUG=schedtrace=1000` 출력에서 `threads` 값이 계속 오르는 것이 이 증상이다.

### Non-blocking I/O와 netpoller

Go의 네트워크 I/O는 내부적으로 전부 non-blocking이다. `net.Conn.Read()`를 호출하면 blocking처럼 보이지만 OS 스레드를 블로킹하지 않는다.

소켓을 non-blocking 모드로 열고 read를 시도한다. 데이터가 없으면 `EAGAIN`을 받고, goroutine은 `Gwaiting` 상태로 전환되며 fd를 epoll/kqueue에 등록한다. M은 P를 보유한 채 다른 G를 실행한다. 데이터가 준비되면 netpoller가 해당 goroutine을 `Grunnable`로 만든다.

```go
// 사용자 코드는 그냥 Read를 호출하지만
// 내부에서 goroutine이 park되고 다른 G가 실행된다
n, err := conn.Read(buf)
```

netpoller는 별도 OS 스레드에서 `epoll_wait`(Linux) / `kqueue`(macOS)로 I/O 이벤트를 기다린다. 이 스레드는 P 없이 동작하므로 GOMAXPROCS에 영향을 주지 않는다.

수만 개의 동시 연결을 처리할 때 OS 스레드를 수만 개 만들 필요가 없는 이유가 이 구조다.

## sysmon 감시 스레드

sysmon은 P 없이 돌아가는 특수 OS 스레드다. Go 런타임이 시작될 때 만들어지며, 다른 P·M·G와 독립적으로 동작한다.

주된 역할은 네 가지다. 10ms 이상 실행 중인 goroutine에 SIGURG를 보내 비동기 선점을 유발한다. syscall에 묶인 M이 너무 오래 P를 보유하면 P를 강제로 빼앗는다. idle P가 있을 때 netpoller를 호출해 I/O가 완료된 goroutine을 깨운다. 힙 사용량이 임계치를 초과하면 GC를 시작한다.

```go
// runtime/proc.go의 sysmon 루프 (단순화)
func sysmon() {
    for {
        checkdead()     // deadlock 감지
        retake(now)     // P retake + 비동기 선점
        forcegchelper() // GC 강제 트리거
        netpoll(delay)  // I/O 이벤트 확인
        sleep(delay)    // 20μs ~ 10ms
    }
}
```

sysmon의 sleep 간격은 초기 20μs에서 시작해 idle 상태가 지속되면 최대 10ms까지 늘어난다. 시스템이 바쁠수록 더 자주 깨어나는 구조다.

## GOMAXPROCS와 실제 성능

`GOMAXPROCS`는 동시에 Go 코드를 실행할 수 있는 OS 스레드 수, 즉 P의 수다. 기본값은 `runtime.NumCPU()`다.

**CPU bound 작업**: GOMAXPROCS를 늘리면 실제로 병렬 실행되는 goroutine 수가 늘어나 성능이 오른다. CPU 코어 수 이상으로 올려도 이득이 없고 컨텍스트 스위치 비용만 늘어난다.

**I/O bound 작업**: GOMAXPROCS 값이 작아도 netpoller 덕분에 많은 동시 연결을 처리할 수 있다. goroutine이 I/O를 대기하는 동안 M은 다른 goroutine을 실행한다. 이 경우 GOMAXPROCS를 높여도 처리량이 거의 늘지 않는다.

**컨테이너 환경 주의**: Docker나 Kubernetes에서 CPU limit을 설정하면 `runtime.NumCPU()`는 여전히 호스트 코어 수를 반환한다. 예를 들어 32코어 호스트에서 2코어 limit을 걸면 GOMAXPROCS=32로 잡혀 스케줄러 오버헤드가 커진다.

```go
import _ "go.uber.org/automaxprocs"
// automaxprocs가 cgroup CPU quota를 읽어 GOMAXPROCS를 자동 조정한다
```

`uber-go/automaxprocs`를 쓰거나, 직접 cgroup 정보를 읽어 `runtime.GOMAXPROCS(n)`을 호출해야 한다.

GOMAXPROCS를 런타임 중 변경하면 P 수가 바뀌면서 재조정이 일어난다. 운영 중에 건드리는 경우는 드물지만, 벤치마크나 진단 목적으로 쓰는 경우가 있다.

```go
// CPU 집약적 구간에서 일시적으로 P 수를 줄여 경합 완화
old := runtime.GOMAXPROCS(2)
defer runtime.GOMAXPROCS(old)
```

## 스케줄러 진단

### schedtrace로 스케줄러 상태 보기

`GODEBUG=schedtrace=1000`은 1000ms 간격으로 스케줄러 상태를 stderr에 출력한다.

```
SCHED 1000ms: gomaxprocs=4 idleprocs=1 threads=6 spinningthreads=0 idlethreads=2 runqueue=3 [2 0 1 0]
```

각 필드의 의미는 다음과 같다.

- `idleprocs`: idle 상태인 P 수
- `threads`: 전체 OS 스레드 수
- `runqueue`: 글로벌 큐의 G 수
- `[2 0 1 0]`: 각 P의 로컬 큐 G 수

글로벌 큐(`runqueue`)가 계속 높으면 P가 부족하거나 goroutine 생성 속도가 처리 속도를 앞선 것이다. `threads`가 계속 늘어나면 blocking syscall이 M을 계속 소모하는 중이다.

```bash
GODEBUG=schedtrace=1000,scheddetail=1 ./myapp 2>&1 | grep "^SCHED"
```

`scheddetail=1`을 추가하면 각 G, M, P의 상태를 상세하게 출력한다. pprof goroutine 덤프와 함께 보면 어떤 goroutine이 어떤 이유로 대기 중인지 파악할 수 있다.

### Goroutine 누수 탐지

goroutine 누수는 생성된 goroutine이 종료되지 않고 계속 쌓이는 문제다. 채널에서 영구적으로 블로킹되거나, for loop에서 종료 조건이 없거나, context cancel을 받지 않는 경우가 대부분이다.

**pprof로 goroutine 덤프 확인**

```go
import _ "net/http/pprof"

// 서버에 pprof 핸들러를 붙인다
go http.ListenAndServe(":6060", nil)
```

```bash
# goroutine 수와 스택 트레이스 확인
curl http://localhost:6060/debug/pprof/goroutine?debug=2

# goroutine 수만 확인
curl -s http://localhost:6060/debug/pprof/goroutine | head -1
```

goroutine 수가 요청 처리량과 무관하게 계속 오르면 누수다. 한 번 덤프를 뜨고 잠시 후 다시 떠서 비교하면 어떤 함수 스택에서 늘어나는지 보인다.

**runtime으로 직접 확인**

```go
var prevCount int

func monitorGoroutines() {
    for range time.Tick(10 * time.Second) {
        count := runtime.NumGoroutine()
        if count > prevCount+100 {
            log.Printf("goroutine 급증: %d -> %d", prevCount, count)
        }
        prevCount = count
    }
}
```

**흔한 누수 패턴**

```go
// 누수: consumer가 없으면 producer goroutine이 영구 블로킹
ch := make(chan Result)
go func() {
    ch <- compute() // 받는 쪽이 없으면 여기서 멈춤
}()
// ch를 읽지 않으면 goroutine이 살아있다

// 수정: context로 취소 신호 전달
go func() {
    select {
    case ch <- compute():
    case <-ctx.Done():
        return
    }
}()
```

```go
// 누수: ticker를 Stop하지 않으면 goroutine이 살아있다
ticker := time.NewTicker(time.Second)
go func() {
    for range ticker.C {
        doWork()
    }
}()
// ticker.Stop() 호출 없으면 goroutine 영구 실행
```

**goleak으로 테스트**

`go.uber.org/goleak`은 테스트 종료 시점에 goroutine 누수를 탐지한다.

```go
func TestMain(m *testing.M) {
    goleak.VerifyTestMain(m)
}

func TestSomething(t *testing.T) {
    defer goleak.VerifyNone(t)
    // ...
}
```

테스트에서 goroutine이 정리되지 않으면 실패로 처리한다. 프로덕션 코드에 실수로 누수를 만들면 CI에서 잡힌다.

**GODEBUG=schedtrace로 goroutine 누수 확인**

```bash
GODEBUG=schedtrace=5000 ./myapp 2>&1 | awk '/^SCHED/ {print $1, $3}'
```

goroutine 수가 `runqueue`와 각 P의 로컬 큐 합산으로 나타나진 않는다. `Gwaiting` 상태 goroutine은 큐에 없어서 `schedtrace`만으로는 전체 goroutine 수를 알기 어렵다. 누수 탐지에는 `runtime.NumGoroutine()`이나 pprof가 더 직접적이다.
