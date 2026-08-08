---
title: Go 고급 동시성 패턴
tags: [go, os, ci-cd, language]
updated: 2026-07-23
---

# Go 고급 동시성 패턴

실무에서 자주 등장하는 동시성 패턴들이다. 고루틴과 채널을 어떻게 조합하느냐에 따라 코드의 안전성과 가독성이 크게 달라진다. 패턴 이름보다 각 패턴이 어떤 문제를 해결하는지 먼저 이해해야 한다.

## 파이프라인 패턴

파이프라인은 여러 처리 단계를 채널로 연결하는 구조다. 각 단계는 독립적인 고루틴에서 실행되고, 데이터는 채널을 타고 다음 단계로 흐른다.

처리 단계가 많고 각 단계의 처리 시간이 다를 때 유용하다. 느린 단계가 병목이 되더라도 다른 단계는 계속 실행된다.

```go
// 각 단계는 입력 채널을 받아 출력 채널을 반환한다
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for _, n := range nums {
            out <- n
        }
    }()
    return out
}

func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            out <- n * n
        }
    }()
    return out
}

func filter(in <-chan int, pred func(int) bool) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            if pred(n) {
                out <- n
            }
        }
    }()
    return out
}

func main() {
    nums := generate(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    squared := square(nums)
    even := filter(squared, func(n int) bool { return n%2 == 0 })

    for n := range even {
        fmt.Println(n)
    }
}
```

파이프라인에서 중간 단계를 취소해야 할 때 문제가 생긴다. 수신자가 더 이상 데이터를 읽지 않으면 송신자는 채널에서 블로킹된다. done 채널이나 context를 함께 받아야 한다.

```go
func squareWithDone(done <-chan struct{}, in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            select {
            case out <- n * n:
            case <-done:
                return
            }
        }
    }()
    return out
}
```

파이프라인 단계마다 done 채널을 받도록 설계하면 어느 단계에서든 취소가 전파된다.

## fan-out / fan-in

fan-out은 하나의 채널에서 여러 고루틴이 데이터를 읽는 패턴이다. 처리가 CPU 집약적이거나 I/O 대기가 길 때 병렬 처리를 위해 쓴다.

```go
// 같은 채널을 여러 worker가 읽는다
func fanOut(done <-chan struct{}, in <-chan int, numWorkers int) []<-chan int {
    outputs := make([]<-chan int, numWorkers)
    for i := 0; i < numWorkers; i++ {
        outputs[i] = squareWithDone(done, in)
    }
    return outputs
}
```

같은 채널을 여러 고루틴이 읽으면 Go 런타임이 알아서 분배한다. 채널에서 값 하나를 읽으면 정확히 하나의 고루틴만 가져간다.

fan-in은 반대 방향이다. 여러 채널의 결과를 하나의 채널로 합친다.

```go
func fanIn(done <-chan struct{}, channels ...<-chan int) <-chan int {
    var wg sync.WaitGroup
    merged := make(chan int)

    drain := func(c <-chan int) {
        defer wg.Done()
        for n := range c {
            select {
            case merged <- n:
            case <-done:
                return
            }
        }
    }

    wg.Add(len(channels))
    for _, c := range channels {
        go drain(c)
    }

    go func() {
        wg.Wait()
        close(merged)
    }()

    return merged
}
```

fan-out과 fan-in을 조합하면 병렬 파이프라인이 된다.

```go
func main() {
    done := make(chan struct{})
    defer close(done)

    in := generate(1, 2, 3, 4, 5)

    // fan-out: 3개 worker에 분배
    c1 := squareWithDone(done, in)
    c2 := squareWithDone(done, in)
    c3 := squareWithDone(done, in)

    // fan-in: 결과를 하나로 합친다
    for n := range fanIn(done, c1, c2, c3) {
        fmt.Println(n)
    }
}
```

fan-out에서 주의할 점은 처리 순서가 보장되지 않는다는 것이다. 입력 순서대로 결과를 받아야 한다면 fan-out 대신 인덱스를 함께 전달하거나 다른 방식을 써야 한다.

## 채널로 구현하는 세마포어

동시에 실행할 수 있는 고루틴 수를 제한할 때 세마포어를 쓴다. Go에서는 버퍼드 채널로 세마포어를 구현한다.

```go
type Semaphore chan struct{}

func NewSemaphore(n int) Semaphore {
    return make(Semaphore, n)
}

func (s Semaphore) Acquire() {
    s <- struct{}{} // 버퍼가 가득 차면 블로킹
}

func (s Semaphore) Release() {
    <-s // 하나 꺼내서 자리를 만든다
}
```

버퍼 크기가 최대 동시 실행 수다. 버퍼가 가득 차면 Acquire가 블로킹되어 대기한다.

```go
func fetchAll(ctx context.Context, urls []string) []string {
    sem := NewSemaphore(10) // 동시에 최대 10개 요청
    results := make([]string, len(urls))
    var wg sync.WaitGroup

    for i, url := range urls {
        wg.Add(1)
        go func(idx int, u string) {
            defer wg.Done()
            sem.Acquire()
            defer sem.Release()
            results[idx] = fetch(ctx, u)
        }(i, url)
    }

    wg.Wait()
    return results
}
```

`golang.org/x/sync/semaphore`에는 가중치를 지원하는 세마포어가 있다. 요청마다 소비하는 리소스 양이 다를 때 유용하다.

```go
import "golang.org/x/sync/semaphore"

var sem = semaphore.NewWeighted(100) // 총 가중치 100

// 일반 작업: 가중치 1 소비
if err := sem.Acquire(ctx, 1); err != nil {
    return err
}
defer sem.Release(1)

// 무거운 작업: 가중치 10 소비
if err := sem.Acquire(ctx, 10); err != nil {
    return err
}
defer sem.Release(10)
```

context를 받는 Acquire는 취소나 타임아웃도 처리한다. 직접 구현한 채널 세마포어는 context를 지원하려면 select를 추가해야 한다.

## 채널 소유권과 close 책임

채널 close는 항상 송신 측에서 해야 한다. 수신 측에서 close하면 송신자가 닫힌 채널에 보내다가 패닉이 난다. 채널을 만드는 쪽이 close 책임을 갖는다는 원칙을 지키면 이 문제를 피할 수 있다.

소유권은 채널을 만들고, 값을 쓰고, 닫을 책임을 말한다. 소유권을 명확히 하는 방법은 채널 생성과 close를 같은 함수나 같은 고루틴에서 처리하는 것이다.

```go
// close 책임이 불명확한 패턴
func bad() {
    ch := make(chan int)
    go sender(ch)   // sender가 close해야 하나?
    go receiver(ch) // receiver가 close해야 하나?
}

// 소유권이 명확한 패턴
func producer() <-chan int {
    ch := make(chan int) // 채널을 만든다
    go func() {
        defer close(ch) // 같은 goroutine에서 닫는다
        for i := 0; i < 10; i++ {
            ch <- i
        }
    }()
    return ch // 수신 전용으로 외부에 노출한다
}
```

수신 전용 채널(`<-chan`)로 반환하면 외부에서 close를 호출할 수 없다. 타입 시스템으로 소유권을 강제하는 방법이다.

여러 송신자가 있을 때 close가 복잡해진다. 두 곳에서 close를 호출하면 패닉이 난다.

```go
// 여러 송신자가 있을 때 - 조율자 하나가 close한다
func merge(sources ...<-chan int) <-chan int {
    var wg sync.WaitGroup
    out := make(chan int)

    relay := func(c <-chan int) {
        defer wg.Done()
        for v := range c {
            out <- v
        }
    }

    wg.Add(len(sources))
    for _, c := range sources {
        go relay(c)
    }

    // 조율자 고루틴만 close한다
    go func() {
        wg.Wait()
        close(out)
    }()

    return out
}
```

실무에서는 여러 고루틴이 닫아야 하는 상황 자체를 피하도록 설계하는 게 낫다. WaitGroup으로 송신자들이 모두 끝날 때까지 기다렸다가 하나의 고루틴이 close하는 구조가 일반적이다.

## done 채널 브로드캐스트

채널을 close하면 해당 채널을 수신 대기 중인 모든 고루틴이 즉시 깨어난다. 이 성질로 취소 신호를 브로드캐스트한다.

```go
func main() {
    done := make(chan struct{})

    for i := 0; i < 5; i++ {
        go func(id int) {
            select {
            case <-done:
                fmt.Printf("worker %d: 종료\n", id)
            case <-time.After(10 * time.Second):
                fmt.Printf("worker %d: 타임아웃\n", id)
            }
        }(i)
    }

    time.Sleep(2 * time.Second)
    close(done) // 5개 고루틴이 동시에 깨어난다
}
```

값을 보내는 방식(`done <- struct{}{}`)은 고루틴 하나만 깨운다. 모두에게 신호를 보내려면 반드시 close를 써야 한다.

지금은 `context.Context`가 done 채널 역할을 대부분 대체한다. 하지만 context 없이 고루틴 종료를 제어해야 하거나, context 취소를 done 채널로 변환해야 하는 경우는 여전히 있다.

```go
// context 취소를 done 채널로 변환
func contextToDone(ctx context.Context) <-chan struct{} {
    done := make(chan struct{})
    go func() {
        <-ctx.Done()
        close(done)
    }()
    return done
}
```

done 채널은 재사용할 수 없다. close된 채널은 다시 열 수 없기 때문에, 반복적으로 취소와 재시작이 필요하다면 매번 새 채널을 만들어야 한다.

## GOMAXPROCS와 CPU 집약 고루틴

`GOMAXPROCS`는 Go 런타임이 동시에 실행할 수 있는 OS 스레드 수를 결정한다. Go 1.5부터 기본값이 CPU 코어 수로 설정된다.

```go
import "runtime"

// 현재 값 확인 (0을 넘기면 변경 없이 현재 값만 반환)
fmt.Println(runtime.GOMAXPROCS(0))

// 변경
runtime.GOMAXPROCS(4)
```

대부분의 경우 기본값을 건드릴 필요가 없다. 컨테이너 환경에서 문제가 생기는 경우가 있다. Go 런타임이 cgroup 제한을 무시하고 호스트 CPU 수를 기준으로 GOMAXPROCS를 설정하기 때문이다. 호스트 CPU가 96코어인데 컨테이너에 2코어만 할당됐다면 96개 스레드로 설정되어 스케줄링 오버헤드가 커진다. `uber-go/automaxprocs`가 이를 자동으로 처리한다.

```go
import _ "go.uber.org/automaxprocs" // import만 해도 자동 설정
```

### runtime.Gosched()

CPU를 오래 점유하는 고루틴이 있으면 같은 OS 스레드에서 실행되는 다른 고루틴이 스케줄링 기회를 얻지 못한다. `runtime.Gosched()`는 현재 고루틴의 CPU를 명시적으로 양보한다.

```go
func cpuIntensive() {
    for i := 0; i < 1_000_000_000; i++ {
        if i%10000 == 0 {
            runtime.Gosched() // 주기적으로 양보
        }
        compute(i)
    }
}
```

Go 스케줄러는 함수 호출 지점에서 고루틴을 선점할 수 있다. 순수한 CPU 루프처럼 함수 호출이 없는 코드는 선점 포인트가 없어서 다른 고루틴이 실행될 기회를 얻지 못한다.

Go 1.14부터 비동기 선점(asynchronous preemption)이 추가되어 시그널 기반으로 CPU 루프도 선점할 수 있다. 대부분의 경우 `Gosched()`를 명시적으로 쓰지 않아도 된다. 다만 Go 1.14 미만을 지원해야 하거나, 타이트한 루프가 다른 고루틴을 굶기고 있다는 pprof 결과를 봤을 때는 써볼 수 있다.

그 외의 상황에서는 `Gosched()`보다 작업 자체를 분할하는 방식이 낫다.

```go
// Gosched 대신 청크 단위로 분할하는 방식
func processInChunks(data []int) {
    const chunkSize = 10000
    var wg sync.WaitGroup

    for i := 0; i < len(data); i += chunkSize {
        end := i + chunkSize
        if end > len(data) {
            end = len(data)
        }
        wg.Add(1)
        chunk := data[i:end]
        go func() {
            defer wg.Done()
            processSlice(chunk)
        }()
    }

    wg.Wait()
}
```

## 실무에서 자주 겪는 패턴 문제

### 조기 리턴 시 고루틴 누수

결과 수집 채널의 크기를 잘못 잡으면 조기 리턴 후 고루틴이 남는다.

```go
// 조기 리턴 시 누수 위험
func processURLs(urls []string) []string {
    ch := make(chan string) // 언버퍼드
    for _, u := range urls {
        go func(url string) {
            result := fetch(url)
            ch <- result // main이 읽기를 멈추면 여기서 영원히 블로킹
        }(u)
    }

    results := make([]string, 0)
    for i := 0; i < len(urls); i++ {
        r := <-ch
        if isError(r) {
            return results // 나머지 고루틴들이 ch <- result에서 블로킹된 채 남는다
        }
        results = append(results, r)
    }
    return results
}

// 버퍼드 채널로 개선
func processURLsSafe(ctx context.Context, urls []string) []string {
    ch := make(chan string, len(urls)) // 결과 수만큼 버퍼
    for _, u := range urls {
        go func(url string) {
            select {
            case ch <- fetch(url): // 수신자 없이도 쓸 수 있다
            case <-ctx.Done():
            }
        }(u)
    }

    results := make([]string, 0)
    for i := 0; i < len(urls); i++ {
        select {
        case r := <-ch:
            if isError(r) {
                return results
            }
            results = append(results, r)
        case <-ctx.Done():
            return results
        }
    }
    return results
}
```

버퍼 크기를 `len(urls)`로 잡으면 모든 고루틴이 블로킹 없이 결과를 쓸 수 있다. 결과 수가 고정되어 있을 때 유효한 방법이다. 결과 수가 가변적이라면 WaitGroup과 done 채널을 조합해야 한다.

### 파이프라인 중간 취소 시 블로킹

파이프라인 중간 단계에서 수신을 멈추면 이전 단계가 송신에서 블로킹된다.

```go
// main이 3개만 읽고 나가면 나머지 고루틴이 블로킹된다
func main() {
    nums := generate(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    squared := square(nums)

    for i := 0; i < 3; i++ {
        fmt.Println(<-squared)
    }
    // squared와 nums 채널을 읽는 고루틴들이 블로킹된 채 남는다
}

// done 채널로 해결
func main() {
    done := make(chan struct{})
    defer close(done) // main이 끝나면 모든 단계에 신호가 간다

    nums := generateWithDone(done, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    squared := squareWithDone(done, nums)

    for i := 0; i < 3; i++ {
        fmt.Println(<-squared)
    }
}
```

`defer close(done)`을 쓰면 main이 끝날 때 자동으로 모든 단계가 종료된다.
