---
title: Go sync 패키지 심화
tags: [go, language]
updated: 2026-07-23
---

# Go sync 패키지 심화

Go_Concurrency.md에서 WaitGroup과 Mutex/RWMutex를 다뤘다. 여기서는 나머지 sync 패키지 타입들과 race detector 깊은 사용법을 다룬다. 이 타입들은 쓰임새가 명확하지만, 잘못 쓰면 오히려 버그를 만든다.

## sync/atomic

`sync/atomic` 패키지는 CPU 레벨 원자적 연산을 제공한다. Mutex 없이 정수형 값을 안전하게 읽고 쓸 수 있다.

### 기본 연산

```go
import "sync/atomic"

var counter int64

// 원자적으로 1 증가
atomic.AddInt64(&counter, 1)

// 값 읽기
val := atomic.LoadInt64(&counter)

// 값 쓰기
atomic.StoreInt64(&counter, 0)

// CAS: expected 값과 같으면 new로 교체, 성공 여부 반환
swapped := atomic.CompareAndSwapInt64(&counter, 0, 100)
```

`AddInt64`는 `counter++`과 달리 read-modify-write 전체가 원자적이다. `counter++`는 어셈블리 수준에서 세 단계로 쪼개지기 때문에 여러 고루틴이 동시에 실행하면 race가 발생한다.

Go 1.19부터 `atomic.Int64`, `atomic.Bool` 같은 타입 기반 API가 추가됐다. 기존 함수 API보다 실수하기 어렵다.

```go
var counter atomic.Int64

counter.Add(1)
val := counter.Load()
counter.Store(0)

var flag atomic.Bool
flag.Store(true)
if flag.Load() {
    // ...
}
```

### atomic.Value

임의 타입을 원자적으로 교체할 때 `atomic.Value`를 쓴다. 설정을 핫 리로드하거나 캐시를 교체할 때 자주 쓰인다.

```go
type Config struct {
    Timeout  time.Duration
    MaxConns int
}

var currentConfig atomic.Value

// 초기화
currentConfig.Store(&Config{Timeout: 5 * time.Second, MaxConns: 100})

// 읽기
cfg := currentConfig.Load().(*Config)
doWork(cfg)

// 교체 (핫 리로드)
func reloadConfig(newCfg *Config) {
    currentConfig.Store(newCfg)
}
```

`atomic.Value.Store`에 nil을 넣으면 패닉이 발생한다. 처음 저장한 타입과 다른 타입을 저장하면 패닉이 발생한다. 한 번 `Store`한 타입은 이후에도 동일 타입이어야 한다.

### atomic vs Mutex 선택 기준

단순 카운터나 플래그 하나를 여러 고루틴에서 읽고 쓸 때는 atomic이 낫다. 코드가 단순하고 Mutex 잠금/해제 오버헤드가 없다.

여러 값을 동시에 일관성 있게 수정해야 한다면 Mutex를 써야 한다. atomic은 변수 하나씩 원자적으로 처리하기 때문에, 두 변수를 함께 갱신할 때 원자성을 보장하지 못한다.

```go
// 잘못된 패턴: x와 y의 쌍이 일관성이 없을 수 있다
var x, y atomic.Int64
x.Store(1)
// 다른 고루틴이 여기서 x=1, y=0 상태를 볼 수 있다
y.Store(1)

// 올바른 패턴: 두 값을 함께 보호해야 할 때는 Mutex
var mu sync.Mutex
var x, y int64
mu.Lock()
x = 1
y = 1
mu.Unlock()
```

---

## sync.Once

`sync.Once`는 초기화 코드를 딱 한 번만 실행하게 보장한다. 여러 고루틴이 동시에 `Do`를 호출해도 함수는 한 번만 실행된다.

```go
var (
    instance *DB
    once     sync.Once
)

func GetDB() *DB {
    once.Do(func() {
        instance = connectDB() // 이 코드는 프로그램 수명 동안 한 번만 실행된다
    })
    return instance
}
```

### 주의사항

`Do` 안에서 패닉이 발생해도 Once는 완료 상태가 된다. 패닉이 복구되더라도 함수는 두 번 다시 호출되지 않는다.

```go
var once sync.Once
var err error

func initOnce() error {
    once.Do(func() {
        // 이 함수가 패닉하면 once는 완료 상태가 됩니다
        // 이후 initOnce()를 호출해도 다시 실행되지 않는다
        panic("init failed")
    })
    return err
}
```

초기화 실패를 재시도해야 한다면 `sync.Once`가 맞지 않는다. 별도 상태 변수와 Mutex로 직접 구현해야 한다.

`Do` 안에서 같은 Once의 `Do`를 다시 호출하면 데드락이 발생한다.

```go
// 데드락 패턴
var once sync.Once
once.Do(func() {
    once.Do(func() { // 여기서 데드락
        fmt.Println("inner")
    })
})
```

---

## sync.Map

`sync.Map`은 동시 접근에 안전한 맵이다. 표준 `map`은 동시 읽기는 안전하지만 동시 쓰기는 race가 발생한다.

```go
var m sync.Map

// 저장
m.Store("key", "value")

// 읽기
val, ok := m.Load("key")
if ok {
    fmt.Println(val.(string))
}

// 없으면 저장하고 값 반환 (로드 또는 스토어)
actual, loaded := m.LoadOrStore("key", "default")
if loaded {
    fmt.Println("이미 있었음:", actual)
} else {
    fmt.Println("새로 저장:", actual)
}

// 삭제
m.Delete("key")

// 전체 순회
m.Range(func(key, value any) bool {
    fmt.Printf("%v: %v\n", key, value)
    return true // false를 반환하면 순회 중단
})
```

### 언제 sync.Map을 쓰나

`sync.Map`은 두 가지 상황에서 `map + RWMutex`보다 낫다.

첫째, 키 집합이 한 번 쓰고 여러 번 읽는 패턴일 때. 예를 들어 서버 시작 시 설정을 한 번 로드하고 이후에는 읽기만 하는 경우다.

둘째, 고루틴마다 자기 키에만 쓰는 패턴일 때. 고루틴 ID를 키로 쓰는 경우처럼 같은 키에 대한 경쟁이 없을 때다.

그 외의 경우에는 `map + RWMutex`가 더 빠르다. 특히 쓰기가 잦으면 `sync.Map`의 내부 복사 오버헤드가 커진다.

```go
// 자주 쓰는 캐시는 RWMutex + map이 낫다
type Cache struct {
    mu    sync.RWMutex
    items map[string]Item
}

// 고루틴당 독립 상태 추적은 sync.Map이 낫다
var goroutineState sync.Map // goroutineID -> state
```

`sync.Map`은 타입 안전성이 없다. `Load`의 반환 타입이 `any`라서 타입 단언이 필요하다. 잘못된 타입 단언이 패닉을 일으킬 수 있다.

---

## sync.Cond

`sync.Cond`는 특정 조건이 충족될 때까지 고루틴을 대기시키는 데 쓴다. 채널로는 구현하기 번거로운 패턴을 처리할 때 유용하다.

```go
type Queue struct {
    mu    sync.Mutex
    cond  *sync.Cond
    items []int
}

func NewQueue() *Queue {
    q := &Queue{}
    q.cond = sync.NewCond(&q.mu)
    return q
}

// 항목 추가 후 대기 중인 소비자를 깨운다
func (q *Queue) Enqueue(item int) {
    q.mu.Lock()
    q.items = append(q.items, item)
    q.cond.Signal() // 대기 중인 고루틴 하나를 깨운다
    q.mu.Unlock()
}

// 항목이 생길 때까지 대기
func (q *Queue) Dequeue() int {
    q.mu.Lock()
    defer q.mu.Unlock()
    for len(q.items) == 0 {
        q.cond.Wait() // 락을 해제하고 대기, 깨어나면 락을 다시 잡는다
    }
    item := q.items[0]
    q.items = q.items[1:]
    return item
}
```

`Wait`는 반드시 for 루프 안에서 써야 한다. `Signal`이나 `Broadcast`로 깨어나도 조건이 충족되지 않았을 수 있다 (spurious wakeup). `if` 대신 `for`로 조건을 다시 확인하는 게 필수다.

### Signal vs Broadcast

`Signal`은 대기 중인 고루틴 중 하나만 깨운다. `Broadcast`는 대기 중인 모든 고루틴을 깨운다.

```go
// 소비자가 여럿인 큐에서 생산자가 여러 항목을 한번에 추가할 때
func (q *Queue) EnqueueBatch(items []int) {
    q.mu.Lock()
    q.items = append(q.items, items...)
    q.cond.Broadcast() // 대기 중인 소비자 전체를 깨운다
    q.mu.Unlock()
}
```

조건이 여러 고루틴에 해당하면 `Broadcast`, 한 고루틴만 처리할 수 있는 조건이면 `Signal`이다.

### 실무에서 sync.Cond를 쓸 때

`sync.Cond`는 채널로 대체할 수 없는 경우에만 쓰는 게 낫다. 대부분의 producer-consumer 패턴은 버퍼드 채널로 더 간단하게 구현된다.

`sync.Cond`가 적합한 경우는 조건 자체가 복잡하거나, 대기 중인 고루틴 수가 동적으로 변하거나, 같은 조건 변수에 여러 종류의 조건을 연결할 때다.

---

## sync.Pool

`sync.Pool`은 생성 비용이 비싼 객체를 재사용하는 풀이다. 자주 할당하고 해제하는 임시 객체에 쓰면 GC 압력을 줄일 수 있다.

```go
var bufPool = sync.Pool{
    New: func() any {
        return new(bytes.Buffer)
    },
}

func process(data []byte) string {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset() // 반환 전에 반드시 초기화
        bufPool.Put(buf)
    }()

    buf.Write(data)
    // ... 처리
    return buf.String()
}
```

### 주의사항

`sync.Pool`은 GC가 돌 때 풀에 있는 객체를 모두 해제한다. 풀에서 꺼낸 객체가 다음 번에도 거기 있다는 보장이 없다. 이 때문에 Pool은 영구 캐시가 아니다.

`Get`이 반환하는 객체는 이전 사용자가 남긴 상태를 그대로 담고 있을 수 있다. `bytes.Buffer`는 `Reset`, 슬라이스는 `[:0]`으로 초기화하고 쓰는 게 안전하다.

```go
// 초기화 안 하고 재사용하면 이전 데이터가 남는다
buf := bufPool.Get().(*bytes.Buffer)
// buf에 이전 Write 내용이 남아있을 수 있다
buf.Reset() // 반드시 초기화 후 사용
```

Pool에 포인터가 아닌 값 타입을 넣으면 `Get` 시 복사가 일어난다. 항상 포인터를 넣어야 의미가 있다.

---

## Race Detector

race detector는 Go 런타임에 내장된 도구다. `-race` 플래그를 붙이면 메모리 접근을 추적해서 동기화 없이 발생하는 동시 접근을 탐지한다.

```bash
go test -race ./...
go build -race -o myapp ./cmd/myapp
go run -race main.go
```

### 출력 해석

race가 탐지되면 두 접근을 함께 보여준다.

```
WARNING: DATA RACE
Write at 0x00c000102070 by goroutine 8:
  main.(*Counter).Increment()
      /home/user/app/counter.go:18 +0x44

Previous read at 0x00c000102070 by goroutine 7:
  main.(*Counter).Value()
      /home/user/app/counter.go:23 +0x34

Goroutine 8 (running) created at:
  main.main()
      /home/user/app/main.go:31 +0x88

Goroutine 7 (running) created at:
  main.main()
      /home/user/app/main.go:28 +0x64
```

`Write at`과 `Previous read at`이 같은 주소를 보면, 잠금 없이 한쪽은 쓰고 다른 쪽은 읽고 있다는 의미다. 파일 경로와 줄 번호가 나오므로 바로 해당 코드를 찾아갈 수 있다.

### GORACE 환경 변수

race detector 동작을 `GORACE` 환경 변수로 제어할 수 있다.

```bash
GORACE="halt_on_error=1" go test -race ./...
```

- `halt_on_error=1`: race를 발견하면 즉시 프로그램을 종료. 기본값은 계속 실행하고 보고만 함
- `log_path=stderr`: 출력 경로. 파일 경로를 지정하면 파일로 기록
- `history_size=1`: race 탐지에 사용하는 메모리 크기 (1~7, 기본값 1). 높일수록 더 많은 접근을 추적하지만 메모리를 더 씀

```bash
GORACE="halt_on_error=1 log_path=/tmp/race" go test -race ./...
```

### 실제 데이터 레이스 패턴과 수정

**패턴 1: 동시 맵 쓰기**

```go
// Race 발생
func countWords(texts []string) map[string]int {
    counts := make(map[string]int)
    var wg sync.WaitGroup

    for _, text := range texts {
        wg.Add(1)
        go func(t string) {
            defer wg.Done()
            for _, word := range strings.Fields(t) {
                counts[word]++ // 동시 쓰기 - race
            }
        }(text)
    }
    wg.Wait()
    return counts
}
```

```go
// 수정: Mutex로 맵 접근 보호
func countWords(texts []string) map[string]int {
    counts := make(map[string]int)
    var mu sync.Mutex
    var wg sync.WaitGroup

    for _, text := range texts {
        wg.Add(1)
        go func(t string) {
            defer wg.Done()
            local := make(map[string]int) // 로컬 맵에 먼저 집계
            for _, word := range strings.Fields(t) {
                local[word]++
            }
            mu.Lock()
            for k, v := range local {
                counts[k] += v
            }
            mu.Unlock()
        }(text)
    }
    wg.Wait()
    return counts
}
```

**패턴 2: 구조체 필드 race**

```go
type Server struct {
    mu      sync.Mutex
    running bool
    conns   int
}

// Race 발생: 락 없이 읽기
func (s *Server) IsRunning() bool {
    return s.running // mu 없이 읽기
}

// 쓰기는 락으로 보호하는데 읽기는 빠뜨린 경우
func (s *Server) Start() {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.running = true
}
```

```go
// 수정: 읽기도 락 필요
func (s *Server) IsRunning() bool {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.running
}

// 또는 atomic.Bool 사용
type Server struct {
    running atomic.Bool
    mu      sync.Mutex
    conns   int
}

func (s *Server) IsRunning() bool {
    return s.running.Load()
}

func (s *Server) Start() {
    s.running.Store(true)
}
```

**패턴 3: 클로저 캡처 race**

```go
// Race 발생
results := make([]int, 10)
var wg sync.WaitGroup

for i := 0; i < 10; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        results[i] = i * 2 // i를 캡처 - race 가능성
    }()
}
wg.Wait()
```

Go 1.22 이전에는 루프 변수 `i`가 공유되어, 고루틴이 실행될 시점의 `i` 값을 쓴다. race detector가 이를 잡는다.

```go
// 수정: 인덱스를 명시적으로 넘긴다
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(idx int) {
        defer wg.Done()
        results[idx] = idx * 2 // 각자 다른 인덱스
    }(i)
}
```

다른 인덱스를 쓰므로 같은 슬라이스 요소에 동시 접근하지 않는다. `results[0]`과 `results[1]`은 다른 메모리 위치다.

**패턴 4: 초기화 중 race**

```go
// Race 발생: 초기화 전에 고루틴이 읽을 수 있다
var cache map[string]string

func init() {
    go func() {
        // 초기화가 끝나기 전에 cache를 읽으려는 고루틴
        time.Sleep(1 * time.Millisecond)
        fmt.Println(cache["key"])
    }()
    cache = make(map[string]string)
    cache["key"] = "value"
}
```

```go
// 수정: sync.Once로 초기화 보장
var (
    cache     map[string]string
    cacheOnce sync.Once
)

func getCache() map[string]string {
    cacheOnce.Do(func() {
        cache = make(map[string]string)
        cache["key"] = "value"
    })
    return cache
}
```

### race detector의 한계

race detector는 실제로 실행된 코드 경로만 검사한다. 특정 타이밍에서만 발생하는 race는 해당 실행 경로가 테스트에서 커버되지 않으면 탐지되지 않는다.

모든 고루틴 조합을 커버하는 테스트를 짜기 어렵기 때문에, `-race` 결과가 깨끗하다고 race가 없다는 의미가 아니다. 코드 리뷰와 병행해서 사용해야 한다.

race detector는 실행 시 5~10배 느리고 메모리도 5~10배 더 쓴다. 프로덕션 바이너리에는 붙이지 않는다. CI에서는 붙이는 게 맞다.

### 테스트에서 race를 재현하는 방법

race를 테스트로 확인하려면 고루틴들이 실제로 겹쳐 실행되도록 해야 한다. `sync.WaitGroup`으로 모두 준비된 뒤 동시에 출발시키는 패턴이 효과적이다.

```go
func TestCounterRace(t *testing.T) {
    var counter int64
    const goroutines = 100

    var ready sync.WaitGroup
    var start sync.WaitGroup
    var done sync.WaitGroup

    start.Add(1) // 출발 신호
    for i := 0; i < goroutines; i++ {
        ready.Add(1)
        done.Add(1)
        go func() {
            ready.Done()
            start.Wait() // 모두 준비될 때까지 대기
            counter++   // 동시에 접근 - race
            done.Done()
        }()
    }

    ready.Wait() // 모든 고루틴이 준비되면
    start.Done() // 동시에 출발
    done.Wait()

    _ = counter
}
```

이 테스트에 `go test -race`를 붙이면 `counter++`의 race를 잡는다.

```go
// 수정
var counter atomic.Int64

go func() {
    ready.Done()
    start.Wait()
    counter.Add(1) // 원자적
    done.Done()
}()
```

---

## Pool + Cond 패턴: 리소스 풀

`sync.Cond`를 써서 크기 제한이 있는 리소스 풀을 직접 구현하는 경우가 있다. 데이터베이스 연결 풀을 직접 구현할 때 이 패턴을 쓴다.

```go
type ResourcePool struct {
    mu        sync.Mutex
    cond      *sync.Cond
    resources []Resource
    maxSize   int
}

func NewResourcePool(maxSize int) *ResourcePool {
    p := &ResourcePool{maxSize: maxSize}
    p.cond = sync.NewCond(&p.mu)
    return p
}

func (p *ResourcePool) Acquire() Resource {
    p.mu.Lock()
    defer p.mu.Unlock()
    for len(p.resources) == 0 {
        p.cond.Wait() // 리소스가 생길 때까지 대기
    }
    r := p.resources[len(p.resources)-1]
    p.resources = p.resources[:len(p.resources)-1]
    return r
}

func (p *ResourcePool) Release(r Resource) {
    p.mu.Lock()
    p.resources = append(p.resources, r)
    p.cond.Signal() // 대기 중인 고루틴 하나를 깨운다
    p.mu.Unlock()
}
```

실무에서 데이터베이스 연결 풀이 필요하다면 이 패턴을 직접 구현하기보다 `database/sql`의 내장 풀이나 `pgxpool` 같은 라이브러리를 쓰는 게 낫다. 이 패턴은 커스텀 리소스 풀이 필요할 때 참고용이다.
