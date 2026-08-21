---
title: Go 동시성 - 고루틴과 채널
tags: [go, os, language]
updated: 2026-07-08
---

# Go 동시성 - 고루틴과 채널

Go의 동시성 모델은 CSP(Communicating Sequential Processes)에 기반한다. 공유 메모리 대신 메시지 전달을 기본으로 설계됐는데, 실무에서는 이 원칙을 지키는 경우보다 지키지 않는 경우가 더 많다. 어떤 상황에서 채널을 써야 하고 어떤 상황에서 Mutex를 써야 하는지를 잘못 판단하면 goroutine leak이나 deadlock으로 돌아온다.

## 고루틴 생성 비용

고루틴은 OS 스레드가 아니다. Go 런타임이 관리하는 경량 스레드로, 초기 스택 크기가 2KB에서 시작해 필요에 따라 커진다. OS 스레드가 보통 1~8MB 스택으로 시작하는 것과 다르다.

고루틴 생성 자체는 수 마이크로초 수준이다. 수천 개를 띄워도 메모리와 스케줄링 부담이 OS 스레드 수백 개보다 낮다. 그래서 Go에서는 HTTP 요청당 고루틴 하나를 만드는 패턴이 자연스럽다.

```go
go func() {
    // 이 함수는 새 고루틴에서 실행된다
    doWork()
}()
```

단, 고루틴을 아무 제한 없이 생성하면 문제가 생긴다. 각 고루틴이 결국 메모리를 쓰고, 스케줄러 부담도 누적된다. 초당 수만 개를 만드는 상황이면 worker pool 패턴을 고려해야 한다.

```go
// worker pool - 고루틴 수를 제한한다
func workerPool(jobs <-chan Job, numWorkers int) {
    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                process(job)
            }
        }()
    }
    wg.Wait()
}
```

## 채널 방향성

채널은 선언할 때 방향을 지정할 수 있다. 함수 시그니처에서 방향을 명시하면 컴파일러가 잘못된 사용을 잡아준다.

```go
func producer(out chan<- int) { // 송신 전용
    out <- 42
}

func consumer(in <-chan int) { // 수신 전용
    val := <-in
    fmt.Println(val)
}

func main() {
    ch := make(chan int, 1) // 양방향 채널
    go producer(ch)
    consumer(ch)
}
```

`chan<- int`는 송신만 가능하고, `<-chan int`는 수신만 가능하다. 방향을 명시하지 않으면 어디서든 송신과 수신이 모두 가능하기 때문에 의도하지 않은 방향으로 사용해도 컴파일러가 잡지 못한다. 함수 인자로 채널을 넘길 때는 항상 방향을 명시하는 게 맞다.

### 버퍼드 채널 vs 언버퍼드 채널

언버퍼드 채널은 송신자와 수신자가 동시에 준비됐을 때만 값이 전달된다. 버퍼드 채널은 버퍼가 가득 찰 때까지 블로킹 없이 송신할 수 있다.

```go
// 언버퍼드: 수신자가 없으면 블로킹
ch1 := make(chan int)

// 버퍼드: 버퍼 크기만큼 쌓을 수 있다
ch2 := make(chan int, 10)
```

버퍼드 채널을 잘못 쓰면 오히려 문제를 숨긴다. 버퍼 크기를 넉넉하게 잡아서 당장 블로킹이 안 일어나는 것처럼 보이지만, 수신 속도가 송신 속도를 따라가지 못하면 결국 가득 찬다. 버퍼 크기는 벤치마크를 기반으로 결정해야 한다.

## select

select는 여러 채널 연산 중 준비된 것을 처리한다. 여러 채널이 동시에 준비됐으면 무작위로 하나를 선택한다.

```go
func fanIn(ch1, ch2 <-chan string) <-chan string {
    out := make(chan string)
    go func() {
        defer close(out)
        for {
            select {
            case v, ok := <-ch1:
                if !ok {
                    ch1 = nil // nil 채널은 select에서 무시된다
                    break     // continue 면 아래 종료 검사를 건너뛴다
                }
                out <- v
            case v, ok := <-ch2:
                if !ok {
                    ch2 = nil
                    break
                }
                out <- v
            }
            if ch1 == nil && ch2 == nil {
                return
            }
        }
    }()
    return out
}
```

채널이 닫혔을 때 nil로 만드는 패턴은 자주 쓰인다. nil 채널에서 수신하면 영원히 블로킹되기 때문에 select 안에서 해당 case가 선택되지 않는다.

**`break`가 아니라 `continue`를 쓰면 여기서 고루틴이 샌다.** Go의 `break`는 `select` 하나만 빠져나가므로 그 아래 종료 검사가 그대로 실행된다. `continue`는 for 루프 맨 위로 튀어 그 검사를 건너뛴다. 마지막 채널이 닫혀 양쪽이 nil이 된 직후 `continue`로 돌아가면, 다음 `select`는 고를 수 있는 case가 하나도 없어 영원히 대기한다. `defer close(out)`이 실행되지 않으니 소비자의 `range out`도 끝나지 않는다.

두 채널에 값을 하나씩 넣고 닫은 뒤 실행하면 이렇게 갈린다.

```
continue :  2초 타임아웃 — out 이 끝내 안 닫힘. 그때까지 받은 값=[a1 b1]
break    :  정상 종료 — out 이 닫혔다. 받은 값=[b1 a1]
```

값은 둘 다 제대로 흘러나온 뒤라 겉보기엔 멀쩡하다. 끝나지 않을 뿐이다. 테스트에서 타임아웃을 걸지 않으면 이 부류는 통과한 것처럼 보인다.

timeout 처리는 `time.After`나 `context`로 한다.

```go
func fetchWithTimeout(ctx context.Context, ch <-chan Result) (Result, error) {
    select {
    case result := <-ch:
        return result, nil
    case <-ctx.Done():
        return Result{}, ctx.Err()
    }
}
```

`time.After`는 타이머 고루틴이 GC되지 않고 남는 경우가 있어서, 루프 안에서 반복 호출하면 메모리 누수가 생긴다. 루프 안에서는 `time.NewTimer`를 쓰고 명시적으로 `Reset`하거나 `Stop`해야 한다.

## WaitGroup

고루틴 여러 개가 끝날 때까지 기다려야 할 때 WaitGroup을 쓴다.

```go
func processAll(items []Item) {
    var wg sync.WaitGroup

    for _, item := range items {
        wg.Add(1)
        go func(it Item) {
            defer wg.Done()
            process(it)
        }(item)
    }

    wg.Wait()
}
```

`wg.Add(1)`은 고루틴을 띄우기 전에 호출해야 한다. 고루틴 안에서 호출하면 `Wait`이 먼저 리턴되는 레이스 컨디션이 생긴다.

루프 변수 캡처 문제도 자주 발생한다. Go 1.22 이전에는 루프 변수를 고루틴 클로저가 캡처하면 루프가 끝난 시점의 값을 보는 버그가 있었다. 위 예제처럼 함수 인자로 명시적으로 넘겨야 안전하다. Go 1.22부터는 루프 변수 캡처 시맨틱이 바뀌어서 각 반복마다 새 변수가 생기지만, 구버전 호환을 고려하면 명시적으로 넘기는 습관을 유지하는 게 낫다.

에러를 수집해야 한다면 `errgroup`이 편하다.

```go
import "golang.org/x/sync/errgroup"

func processAll(ctx context.Context, items []Item) error {
    g, ctx := errgroup.WithContext(ctx)

    for _, item := range items {
        it := item
        g.Go(func() error {
            return process(ctx, it)
        })
    }

    return g.Wait() // 첫 번째 에러를 반환한다
}
```

`errgroup.Wait`는 첫 번째 에러만 반환한다. 모든 에러를 수집해야 한다면 직접 구현해야 한다.

## Mutex vs 채널 선택 기준

Go 공식 문서에 "공유 메모리로 통신하지 말고 통신으로 메모리를 공유하라"는 말이 있다. 하지만 실제로 둘 중 뭘 써야 하는지 판단이 필요한 상황이 자주 온다.

**Mutex를 쓰는 경우:**

공유 상태를 단순히 보호할 때다. 캐시, 카운터, 맵처럼 여러 고루틴이 같은 데이터를 읽고 쓰는 경우에 Mutex가 더 직관적이다.

```go
type Cache struct {
    mu    sync.RWMutex
    items map[string]Item
}

func (c *Cache) Get(key string) (Item, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    item, ok := c.items[key]
    return item, ok
}

func (c *Cache) Set(key string, item Item) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = item
}
```

읽기가 많고 쓰기가 적으면 `sync.RWMutex`를 쓴다. `RLock`은 여러 고루틴이 동시에 잡을 수 있다.

**채널을 쓰는 경우:**

작업을 고루틴 간에 전달할 때, 결과를 수집할 때, 종료 신호를 보낼 때다.

```go
// 종료 신호 전달 - done 채널 패턴
func worker(done <-chan struct{}) {
    for {
        select {
        case <-done:
            return
        default:
            doWork()
        }
    }
}

func main() {
    done := make(chan struct{})
    go worker(done)

    time.Sleep(5 * time.Second)
    close(done) // 모든 수신자에게 신호가 간다
}
```

채널로 종료 신호를 보낼 때는 `close`를 쓴다. `close`는 채널을 수신 대기 중인 모든 고루틴에 동시에 신호를 보내지만, 값을 보내는 방식은 하나의 고루틴만 받는다.

실무에서는 `context.Context`가 종료 신호 역할을 대부분 담당한다.

```go
func worker(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return
        default:
            doWork()
        }
    }
}
```

판단 기준을 단순하게 정리하면 이렇다. 상태를 보호하면 Mutex, 데이터나 신호를 전달하면 채널이다. 채널로 상태를 보호하려 하면 코드가 복잡해진다.

## goroutine leak 패턴과 방지법

고루틴 누수는 고루틴이 종료되지 않고 계속 메모리를 점유하는 상태다. 서비스가 오래 돌면 메모리가 계속 늘어나는 형태로 나타난다.

### 채널 수신 대기 누수

수신 대기 중인 고루틴에 아무도 값을 보내지 않으면 영원히 블로킹된다.

```go
// 누수 패턴
func leak() {
    ch := make(chan int)
    go func() {
        val := <-ch // 아무도 보내지 않으면 여기서 영원히 블로킹
        fmt.Println(val)
    }()
    // ch에 아무것도 보내지 않고 함수가 끝난다
    // 고루틴은 살아있다
}
```

수정 방법은 context나 done 채널로 탈출 경로를 만드는 것이다.

```go
func noLeak(ctx context.Context) {
    ch := make(chan int)
    go func() {
        select {
        case val := <-ch:
            fmt.Println(val)
        case <-ctx.Done():
            return // 컨텍스트가 취소되면 종료
        }
    }()
}
```

### 채널 송신 대기 누수

버퍼가 없거나 가득 찬 채널에 아무도 수신하지 않을 때 블로킹된다.

```go
// 누수 패턴 - 에러 반환 후 채널 무시
func startWorker() <-chan Result {
    ch := make(chan Result) // 언버퍼드
    go func() {
        result := doExpensiveWork()
        ch <- result // 수신자가 없으면 여기서 블로킹
    }()
    return ch
}

func main() {
    ch := startWorker()
    // ch를 무시하고 함수가 리턴하면 고루틴이 남는다
    if someCondition {
        return
    }
    result := <-ch
    use(result)
}
```

버퍼드 채널로 방지할 수 있다.

```go
func startWorker(ctx context.Context) <-chan Result {
    ch := make(chan Result, 1) // 버퍼 1로 블로킹 방지
    go func() {
        result := doExpensiveWork()
        select {
        case ch <- result:
        case <-ctx.Done(): // 컨텍스트 취소 시 종료
        }
    }()
    return ch
}
```

### HTTP 핸들러에서의 누수

```go
// 누수 패턴
func handler(w http.ResponseWriter, r *http.Request) {
    ch := make(chan string)
    go func() {
        result := fetchData() // 오래 걸리는 작업
        ch <- result
    }()
    // 클라이언트가 연결을 끊어도 고루틴은 계속 실행된다
    result := <-ch
    w.Write([]byte(result))
}
```

`r.Context()`를 넘기면 클라이언트 연결이 끊겼을 때 컨텍스트가 취소된다.

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ch := make(chan string, 1)
    ctx := r.Context()
    go func() {
        result := fetchDataWithContext(ctx)
        select {
        case ch <- result:
        case <-ctx.Done():
        }
    }()

    select {
    case result := <-ch:
        w.Write([]byte(result))
    case <-ctx.Done():
        http.Error(w, "request cancelled", http.StatusRequestTimeout)
    }
}
```

### 누수 감지

`runtime.NumGoroutine()`으로 고루틴 수를 모니터링하거나, `goleak` 라이브러리로 테스트 시 누수를 감지한다.

```go
import "go.uber.org/goleak"

func TestHandler(t *testing.T) {
    defer goleak.VerifyNone(t) // 테스트 종료 후 고루틴 누수 체크

    // ... 테스트 코드
}
```

프로덕션에서는 pprof의 goroutine 프로파일을 보는 게 직접적이다.

```bash
# 실행 중인 서버의 고루틴 덤프
curl http://localhost:6060/debug/pprof/goroutine?debug=2
```

같은 스택 트레이스를 가진 고루틴이 수백 개 이상이면 누수를 의심한다.
