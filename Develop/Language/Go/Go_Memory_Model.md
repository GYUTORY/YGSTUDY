---
title: Go 메모리 모델 심화
tags: [Go, Memory Model, Happens-Before, goroutine, channel, Mutex, atomic, concurrency]
updated: 2026-07-27
---

# Go 메모리 모델 심화

Go 메모리 모델은 여러 고루틴이 같은 데이터를 읽고 쓸 때 어떤 결과를 관찰할 수 있는지를 정의한다. "어떤 쓰기가 어떤 읽기에 보여야 하는가"라는 질문의 답이다.

Go 1.19 이전까지는 커뮤니티 해석에 의존해야 했다. 2022년 Go 1.19 릴리스에서 `https://go.dev/ref/mem`이 전면 재작성되면서 메모리 모델이 공식 문서화됐다.

## Happens-Before 관계

happens-before는 연산 실행 순서가 아니라 **메모리 가시성**의 보장이다. 연산 A가 연산 B보다 happens-before라면, A의 메모리 쓰기 결과가 B에서 반드시 보인다.

단일 고루틴 내에서는 코드 작성 순서대로 happens-before 관계가 성립한다. 고루틴 간에는 명시적 동기화가 없으면 이 관계가 성립하지 않는다.

공식 문서는 세 가지 관계로 구분한다.

- **프로그램 순서(program order)**: 단일 고루틴 내에서 앞에 오는 연산이 뒤에 오는 연산보다 happens-before
- **동기화 순서(synchronized-before)**: 채널 송수신, Mutex Lock/Unlock 같은 동기화 연산이 만드는 관계
- **happens-before**: 위 두 관계의 전이적 폐포(transitive closure)

## 동기화 없이 읽을 때 보장되는 것

아무것도 보장되지 않는다.

컴파일러는 최적화를 위해 메모리 접근 순서를 재배치(reorder)할 수 있다. CPU도 마찬가지다. 단일 고루틴 내에서는 관찰 가능한 동작이 바뀌지 않는 범위에서만 재배치가 허용되지만, 다른 고루틴의 관점에서는 어떤 순서로 보여도 규격 위반이 아니다.

보장되지 않는 것들:

- 다른 고루틴이 변수에 쓴 최신 값을 읽는다는 것
- 다른 고루틴이 여러 변수에 순서대로 쓴 것이 같은 순서로 보인다는 것
- 컴파일러가 변수 읽기를 최적화로 제거하지 않는다는 것

## Race 없이도 틀린 결과가 나오는 사례

### 초기화 순서 문제

```go
var done bool
var result int

func setup() {
    result = 42
    done = true
}

func main() {
    go setup()
    for !done {
        runtime.Gosched()
    }
    fmt.Println(result) // 42가 아닐 수 있다
}
```

`done`이 true가 됐을 때 `result`가 42라는 보장이 없다. 컴파일러가 `done` 쓰기를 `result` 쓰기보다 먼저 재배치할 수 있고, CPU 캐시 때문에 다른 코어에서는 다른 순서로 보일 수 있다.

race detector로 이 코드를 돌리면 race가 잡힌다. 하지만 재배치 자체는 undefined behavior 영역이라 항상 재현되지 않는다.

### 컴파일러 최적화로 인한 무한 루프

```go
var stop bool

func worker() {
    for !stop {
        // CPU를 쓰는 작업
    }
}

func main() {
    go worker()
    time.Sleep(time.Second)
    stop = true
}
```

`worker` 루프 내에서 `stop`이 변경되지 않는다고 컴파일러가 판단하면 `stop`을 레지스터에 한 번만 읽고 이후에는 레지스터 값을 사용한다. `main`에서 `stop = true`를 써도 `worker`가 보지 못하고 무한 루프에 빠진다.

Go 컴파일러가 현재 이 최적화를 적극적으로 하지는 않는다. 하지만 규격상 허용되고, 컴파일러 버전이 바뀌면 언제든 달라질 수 있다.

### 반쯤 초기화된 구조체

```go
type Node struct {
    value int
    next  *Node
}

var head *Node

func publish() {
    n := &Node{value: 42}
    head = n // (A)
}

func consume() {
    if h := head; h != nil { // (B)
        fmt.Println(h.value) // 0이 출력될 수 있다
    }
}
```

(A)에서 포인터 저장과 구조체 필드 초기화가 CPU 수준에서 순서가 바뀔 수 있다. (B)에서 `head`가 nil이 아닌 것을 봤을 때 `value`가 아직 42로 쓰이지 않은 상태일 수 있다.

## Channel의 Happens-Before 보장

**unbuffered channel**: 수신 완료가 송신 완료보다 happens-before다.

```go
var c = make(chan int)
var x int

func f() {
    x = 1
    c <- 0 // x 쓰기가 완료된 후 송신
}

func main() {
    go f()
    <-c              // 수신 완료 이후
    fmt.Println(x)  // 반드시 1
}
```

단일 고루틴 내에서 `x = 1`은 `c <- 0`보다 happens-before다. unbuffered channel에서 `c <- 0` 송신은 `<-c` 수신이 완료될 때 happens-before 관계가 성립한다. 두 관계의 전이로 `<-c` 이후 `x`를 읽으면 반드시 1이다.

**buffered channel**: 버퍼 크기가 C인 채널에서, n번째 수신 완료는 (n+C)번째 송신 완료보다 happens-before다.

```go
var limit = make(chan struct{}, 3) // 동시 3개 제한

func work() {
    limit <- struct{}{}
    defer func() { <-limit }()
    // 실제 작업
}
```

세마포어 패턴이다. happens-before 보장 덕에 안전하게 동시성을 제어할 수 있다.

**channel close**: 채널 닫기는 zero value 수신보다 happens-before다.

```go
var c = make(chan int)
var x int

func f() {
    x = 1
    close(c)
}

func main() {
    go f()
    <-c             // 닫힌 채널에서 zero value 수신
    fmt.Println(x) // 반드시 1
}
```

## sync.Mutex의 Happens-Before 보장

n번째 `Unlock()` 호출은 n+1번째 `Lock()` 반환보다 happens-before다.

```go
var mu sync.Mutex
var x int

func f() {
    mu.Lock()
    x = 1
    mu.Unlock() // (A)
}

func g() {
    mu.Lock()       // (B) - (A)가 완료된 후 진입
    fmt.Println(x) // 반드시 1
    mu.Unlock()
}
```

`f()`가 먼저 락을 잡고 해제했다면 `g()`에서 락을 얻은 후 `x`를 읽으면 `f()`에서 쓴 값이 반드시 보인다.

`RWMutex`도 동일하다. `RUnlock()` n번째 호출은 `Lock()` n+1번째 반환보다 happens-before다.

실무에서 자주 실수하는 패턴이 있다.

```go
type Server struct {
    mu      sync.Mutex
    clients map[string]*Client
    count   int
}

func (s *Server) Count() int {
    return s.count // 락 없이 읽으면 안 된다
}
```

"읽기만 하니까 괜찮겠지"라고 판단하고 락 없이 접근하는 경우다. 공유 상태는 전부 같은 락으로 보호하거나, 채널로 소유권을 이전하거나, `sync/atomic`을 명시적으로 쓴다.

## sync.WaitGroup의 Happens-Before 보장

`wg.Done()`은 `wg.Wait()` 반환보다 happens-before다.

```go
var wg sync.WaitGroup
results := make([]int, 10)

for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(i int) {
        defer wg.Done()
        results[i] = compute(i) // (A)
    }(i)
}

wg.Wait()            // (B)
fmt.Println(results) // (A)의 모든 쓰기가 보임
```

`wg.Wait()` 이후에 `results`를 읽으면 모든 워커가 쓴 값이 보인다.

## sync.Once의 Happens-Before 보장

`once.Do(f)`에서 `f`의 반환은 다른 모든 `once.Do(f)` 반환보다 happens-before다.

```go
var once sync.Once
var cfg *Config

func getConfig() *Config {
    once.Do(func() {
        cfg = loadConfig() // (A)
    })
    return cfg // (B)
}
```

첫 번째 호출에서 `loadConfig()`가 실행되고 `cfg`가 설정된다. 이후 어떤 고루틴에서 `getConfig()`를 호출해도 (A)가 (B)보다 happens-before이므로 초기화된 `cfg`를 읽는다.

## sync/atomic의 Happens-Before 보장

Go 1.19에서 공식적으로 정의됐다. atomic 연산들은 sequentially consistent하다. 즉, 모든 고루틴이 atomic 연산들을 같은 순서로 관찰한다.

단, 이 보장은 atomic 변수 자체에만 해당한다.

```go
var flag int32
var data int // 일반 변수

func writer() {
    data = 42               // (A)
    atomic.StoreInt32(&flag, 1) // (B)
}

func reader() {
    if atomic.LoadInt32(&flag) == 1 { // (C)
        fmt.Println(data)             // data가 42라는 보장이 없다
    }
}
```

`flag`가 1인 것을 (C)에서 봤어도 `data`에 대한 happens-before가 없다. (A)와 (B) 사이에는 단일 고루틴 내 프로그램 순서 happens-before가 있지만, 이것이 (C)까지 전이되려면 (B)와 (C) 사이에 synchronized-before 관계가 필요하다. atomic 연산 간 synchronized-before는 같은 변수에 대해서만 성립한다.

모든 것을 atomic으로 바꿔도 해결되지 않는다.

```go
var flag int32
var data int32

func writer() {
    atomic.StoreInt32(&data, 42)
    atomic.StoreInt32(&flag, 1)
}

func reader() {
    if atomic.LoadInt32(&flag) == 1 {
        fmt.Println(atomic.LoadInt32(&data)) // 여전히 보장 없음
    }
}
```

`flag`와 `data`는 서로 다른 변수다. `flag`에 대한 atomic 순서가 `data`에 대한 접근 순서를 보장하지 않는다. 이런 용도에는 `sync.Mutex`를 쓴다.

Go 1.19 이전에는 `sync/atomic`이 어떤 수준의 동기화를 제공하는지 스펙이 없었다. 실제 구현이 sequentially consistent했지만 공식 보장이 아니었다. 1.19 이후에는 이 점이 명시됐다.

## Double-Checked Locking은 Go에서 안전한가

안전하지 않다.

```go
var mu sync.Mutex
var instance *Singleton

func GetInstance() *Singleton {
    if instance != nil { // (A) 락 없이 읽기
        return instance
    }
    mu.Lock()
    defer mu.Unlock()
    if instance == nil { // (B) 락 안에서 재확인
        instance = &Singleton{...}
    }
    return instance
}
```

(A)에서 `instance`를 락 없이 읽는다. `instance`는 일반 포인터라 읽기가 원자적이지 않다.

문제는 `instance = &Singleton{...}` 할당이 두 단계다. 메모리에 `Singleton` 구조체를 초기화하는 것과 포인터를 `instance`에 저장하는 것이 CPU나 컴파일러 수준에서 순서가 바뀔 수 있다. 포인터가 먼저 저장되고 구조체 필드 초기화가 뒤에 오면, (A)에서 nil이 아닌 포인터를 읽고 초기화되지 않은 구조체에 접근하게 된다.

Java에서 `volatile`로, C++에서 `std::atomic<T*>`로 해결하는 그 문제와 동일하다.

Go에서는 `sync.Once`를 쓴다.

```go
var once sync.Once
var instance *Singleton

func GetInstance() *Singleton {
    once.Do(func() {
        instance = &Singleton{...}
    })
    return instance
}
```

`sync.Once`의 happens-before 보장 덕에 `Do` 안에서 초기화한 값은 `Do` 이후에 읽는 모든 고루틴에서 완전히 초기화된 상태로 보인다.

Go 1.19에서 추가된 `atomic.Pointer[T]`로 포인터 자체의 원자적 읽기/쓰기를 보장받는 방법도 있다.

```go
var instance atomic.Pointer[Singleton]

func GetInstance() *Singleton {
    if p := instance.Load(); p != nil {
        return p
    }
    mu.Lock()
    defer mu.Unlock()
    if instance.Load() == nil {
        instance.Store(&Singleton{...})
    }
    return instance.Load()
}
```

이 방법은 포인터 접근 자체는 원자적이지만 구조체 내부 필드 초기화 순서 문제는 여전히 존재한다. `sync.Once`가 의도가 명확하고 실수할 여지가 없다.

## Go 1.19 공식화 이후 달라진 점

2022년 Go 1.19에서 메모리 모델 공식 문서가 전면 재작성됐다.

**이전**: happens-before가 어렴풋이 언급됐고, "동기화 없이 공유 변수에 접근하지 말라"는 수준의 설명이 전부였다. `sync/atomic`이 어떤 메모리 보장을 제공하는지 스펙이 없었다.

**이후**:

- happens-before를 프로그램 순서, synchronized-before, happens-before 세 관계로 정의했다.
- `sync/atomic`의 연산들이 sequentially consistent하다고 명시했다.
- race condition의 정의가 명확해졌다. 두 메모리 접근이 happens-before 관계 없이 같은 변수를 접근하고, 그 중 하나 이상이 쓰기이면 race다.
- `sync.Mutex`, `sync.RWMutex`, `sync.WaitGroup`, `sync.Once`, `sync.Cond`, channel, `sync/atomic` 각각의 happens-before 보장이 명시됐다.
- `sync.Cond`가 처음으로 공식 문서에 포함됐다. `cond.Broadcast()` 또는 `cond.Signal()` 호출은 이후 `cond.Wait()` 반환보다 happens-before다.

Go 팀은 1.19에서 규격을 강화한 게 아니라 기존 구현이 제공하던 보장을 문서화한 것이라고 밝혔다. 1.19 이전 코드도 동일한 규칙이 적용됐다.

## Race Detector 활용

race detector는 `-race` 플래그로 켠다.

```bash
go test -race ./...
go run -race main.go
go build -race -o server .
```

race detector는 동적 분석이라 실행 경로에서 실제로 race가 발생해야 감지한다. 모든 race를 잡는 게 아니다. 특정 실행 경로에서만 발생하는 race는 해당 경로가 실행될 때만 감지된다.

CI 파이프라인에서 `go test -race`를 돌리는 건 기본이다. race detector가 잡지 못하는 경우를 대비해 코드 리뷰에서 고루틴 간 메모리 접근을 의식적으로 확인해야 한다.

race detector의 오버헤드는 CPU 5~10배, 메모리 2~3배 수준이다. 프로덕션 바이너리에는 기본적으로 넣지 않는다.
