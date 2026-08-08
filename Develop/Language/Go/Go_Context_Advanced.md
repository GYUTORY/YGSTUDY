---
title: Go Context 심화
tags: [go, performance, language]
updated: 2026-07-27
---

# Go Context 심화

기본 context 사용법은 `Go_Context.md`에서 다뤘다. 여기서는 Go 1.20/1.21에 추가된 API, 내부 구현 구조, WithValue 성능 비용, 테스트 패턴, 서비스 경계 전파까지 실무에서 직접 맞닥뜨린 부분들을 정리한다.

## Go 1.20: WithCancelCause와 Cause

기존 `WithCancel`의 문제는 취소 이유를 알 수 없다는 것이었다. `ctx.Err()`는 `context.Canceled`나 `context.DeadlineExceeded`만 반환하고, 왜 취소됐는지는 담지 못했다.

`context.WithCancelCause`는 취소 원인을 임의 에러로 지정한다.

```go
ctx, cancel := context.WithCancelCause(parentCtx)
defer cancel(nil) // nil을 넘기면 context.Canceled로 처리된다

// 특정 에러로 취소
cancel(fmt.Errorf("upstream unavailable: %w", ErrServiceDown))

// 취소 원인 꺼내기
cause := context.Cause(ctx) // "upstream unavailable: service down"
err := ctx.Err()            // context.Canceled
```

`context.Cause(ctx)`는 `cancel(err)`에 넘긴 값을 반환한다. `cancel(nil)`로 호출했거나 부모가 타임아웃으로 취소됐다면 `ctx.Err()`와 동일한 값이 나온다.

실무에서는 `errgroup`의 내부 구현처럼 여러 고루틴 중 어떤 고루틴이 어떤 이유로 실패해서 전체가 취소됐는지 추적할 때 유용하다.

```go
func runPipeline(ctx context.Context, stages []Stage) error {
    ctx, cancel := context.WithCancelCause(ctx)
    defer cancel(nil)

    var wg sync.WaitGroup
    for _, s := range stages {
        stage := s
        wg.Add(1)
        go func() {
            defer wg.Done()
            if err := stage.Run(ctx); err != nil {
                cancel(fmt.Errorf("stage %s failed: %w", stage.Name, err))
            }
        }()
    }

    wg.Wait()
    if cause := context.Cause(ctx); cause != nil {
        return cause
    }
    return nil
}
```

`cancel`을 여러 번 호출해도 첫 번째 호출만 효과가 있다. 두 번째 이후는 무시된다.

### WithDeadlineCause, WithTimeoutCause

Go 1.21에서 타임아웃 계열에도 cause 버전이 추가됐다.

```go
ctx, cancel := context.WithTimeoutCause(
    parentCtx,
    3*time.Second,
    fmt.Errorf("payment gateway timeout"),
)
defer cancel()

// 타임아웃 발생 시:
// ctx.Err()  → context.DeadlineExceeded
// context.Cause(ctx) → "payment gateway timeout"
```

이전에는 타임아웃과 명시적 취소를 구분하려면 `ctx.Err()`의 반환값 타입으로만 판단했는데, 이제 더 구체적인 원인을 담을 수 있다.

## Go 1.21: AfterFunc

`context.AfterFunc`는 context가 취소됐을 때 별도 고루틴에서 함수를 실행한다. Done 채널에 select 걸기 어려운 구조에서 쓸 수 있다.

```go
stop := context.AfterFunc(ctx, func() {
    // ctx가 취소되면 새 고루틴에서 이 함수가 실행된다
    conn.Close()
})
defer stop() // stop()을 호출하면 AfterFunc 등록이 취소된다
             // ctx가 이미 취소됐으면 아무 효과 없다
```

`stop()`의 반환값은 bool인데, AfterFunc가 아직 실행되지 않은 상태에서 stop()을 호출했으면 true, 이미 실행됐거나 실행 중이면 false다.

```go
// cleanup이 실행됐는지 확인이 필요한 경우
stop := context.AfterFunc(ctx, cleanup)

// ... 작업 수행 ...

if !stop() {
    // cleanup이 이미 실행 중이거나 완료됐다
    // cleanup 완료를 기다려야 한다면 sync 수단이 별도 필요
}
```

AfterFunc는 콜백 기반 라이브러리를 context와 연결할 때 유용하다. 예를 들어 io.Reader를 감싸서 context 취소 시 읽기를 중단하는 구조를 만들 수 있다.

```go
type contextReader struct {
    ctx  context.Context
    r    io.Reader
    conn net.Conn
}

func NewContextReader(ctx context.Context, conn net.Conn) io.Reader {
    cr := &contextReader{ctx: ctx, r: conn, conn: conn}
    context.AfterFunc(ctx, func() {
        conn.SetDeadline(time.Now()) // 블로킹 Read를 풀어준다
    })
    return cr
}
```

## 내부 전파 메커니즘

### propagation tree 구조

`WithCancel`, `WithTimeout`, `WithDeadline`은 내부적으로 `cancelCtx` 구조체를 만들고, 부모 context의 Done 채널에서 취소 신호를 기다리는 고루틴을 등록한다.

정확히는 고루틴을 띄우는 게 아니라 부모 cancelCtx의 자식 맵에 자신을 등록한다. 부모가 취소될 때 자식 맵을 순회하며 `cancel()`을 호출하는 구조다.

```
Background (취소 불가)
  └── cancelCtx A
        ├── cancelCtx B  ← A의 children 맵에 등록
        │     └── timerCtx C  ← B의 children 맵에 등록
        └── cancelCtx D  ← A의 children 맵에 등록
```

A를 취소하면 B와 D가 즉시 취소되고, B가 취소되면서 C도 취소된다. 취소는 재귀적으로 전파된다.

`WithValue`는 이 트리에 노드를 추가하지만 취소 관련 필드가 없다. propagation 관점에서 투명한 래퍼다. `WithValue`로 만든 context의 부모 취소가 어떻게 전파되는지는 내부적으로 부모를 따라 올라가며 cancelCtx를 찾는 방식으로 처리된다.

### Done 채널의 lazy initialization

`cancelCtx`의 Done 채널은 처음 `Done()`을 호출할 때 생성된다. `WithCancel`로 context를 만들어도 아무도 Done을 조회하지 않으면 채널이 만들어지지 않는다.

```go
// runtime/context.go 내부 구조 (단순화)
type cancelCtx struct {
    Context
    mu       sync.Mutex
    done     atomic.Value // chan struct{}, lazy init
    children map[canceler]struct{}
    err      error
    cause    error
}

func (c *cancelCtx) Done() <-chan struct{} {
    d := c.done.Load()
    if d != nil {
        return d.(chan struct{})
    }
    c.mu.Lock()
    defer c.mu.Unlock()
    d = c.done.Load()
    if d == nil {
        d = make(chan struct{})
        c.done.Store(d)
    }
    return d.(chan struct{})
}
```

이 구조 때문에 context를 만들어도 Done을 조회하지 않으면 채널 생성 비용이 없다. 취소 신호 전파는 채널이 아니라 children 맵 순회로 처리되기 때문에 Done 채널 없이도 동작한다.

취소 시에는 채널이 있으면 닫고, 없으면 닫지 않는다. select로 기다리는 고루틴이 없는 context를 취소해도 문제없다.

## WithValue의 성능 비용

### 호출당 힙 할당

`context.WithValue`는 매 호출마다 새 구조체를 힙에 할당한다.

```go
// 내부적으로 이런 구조체가 생성된다
type valueCtx struct {
    Context
    key, val any
}
```

값 하나를 추가할 때마다 힙 할당이 한 번 일어난다. GC 압박이 있는 고빈도 경로에서 WithValue를 남발하면 문제가 된다.

```go
// HTTP 요청당 이런 코드가 실행된다면
ctx = context.WithValue(ctx, traceIDKey, traceID)    // 할당 1
ctx = context.WithValue(ctx, userIDKey, userID)      // 할당 2
ctx = context.WithValue(ctx, tenantIDKey, tenantID)  // 할당 3
ctx = context.WithValue(ctx, requestIDKey, reqID)    // 할당 4
```

초당 수만 건의 요청을 처리하는 서버라면 이 할당이 GC 부하로 쌓인다. 해결 방법은 값들을 하나의 구조체로 묶는 것이다.

```go
type RequestMeta struct {
    TraceID   string
    UserID    int64
    TenantID  string
    RequestID string
}

var requestMetaKey = &struct{ name string }{"request_meta"}

func WithRequestMeta(ctx context.Context, meta RequestMeta) context.Context {
    return context.WithValue(ctx, requestMetaKey, meta)
}

func RequestMetaFromContext(ctx context.Context) (RequestMeta, bool) {
    meta, ok := ctx.Value(requestMetaKey).(RequestMeta)
    return meta, ok
}
```

할당이 4번에서 1번으로 줄어든다.

### 체인 깊이와 Value 조회 성능

`ctx.Value(key)`는 현재 context에서 키를 찾지 못하면 부모로 올라가는 선형 탐색이다. 체인이 깊을수록 조회가 느려진다.

```
valueCtx{reqID}
  └── valueCtx{tenantID}
        └── valueCtx{userID}
              └── valueCtx{traceID}
                    └── cancelCtx
                          └── Background
```

`ctx.Value(reqID)`는 첫 번째 노드에서 찾고, `ctx.Value(traceID)`는 네 번째 노드까지 내려가야 한다. 체인 깊이가 10, 20으로 늘어나면 자주 조회하는 값의 접근 비용도 선형으로 증가한다.

미들웨어를 여러 계층으로 쌓는 프레임워크에서 각 미들웨어가 WithValue를 호출하면 실제로 이런 깊은 체인이 생긴다. 성능에 민감하다면 위처럼 값을 묶거나, 자주 접근하는 값은 별도 변수로 꺼내두는 게 낫다.

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    meta, _ := RequestMetaFromContext(ctx) // 한 번만 조회

    // meta.TraceID, meta.UserID 등 직접 사용
    doWork(ctx, meta)
}
```

## context 의존 함수 테스트 패턴

### 취소 동작 테스트

```go
func TestProcessWithCancellation(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())

    resultCh := make(chan error, 1)
    go func() {
        resultCh <- Process(ctx, input)
    }()

    // 잠시 후 취소
    time.Sleep(10 * time.Millisecond)
    cancel()

    err := <-resultCh
    if !errors.Is(err, context.Canceled) {
        t.Errorf("expected context.Canceled, got %v", err)
    }
}
```

`time.Sleep`은 테스트를 불안정하게 만든다. 가능하면 테스트 대상 함수가 취소 신호를 받았음을 검증할 수 있는 다른 수단을 쓰는 게 낫다.

```go
func TestProcessRespondsToCancel(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    cancel() // 처음부터 취소된 context

    err := Process(ctx, input)
    if !errors.Is(err, context.Canceled) {
        t.Errorf("expected context.Canceled, got %v", err)
    }
}
```

이미 취소된 context를 넘기면 함수가 즉시 반환하는지 검증할 수 있다. 함수가 루프 시작 전에 ctx.Done()을 체크하는 구조라면 이 테스트가 빠르게 동작한다.

### 타임아웃 테스트

```go
func TestProcessTimesOut(t *testing.T) {
    // 실제 시간 기다리는 방식 - 느리고 flaky하다
    ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
    defer cancel()

    err := Process(ctx, slowInput)
    if !errors.Is(err, context.DeadlineExceeded) {
        t.Errorf("expected DeadlineExceeded, got %v", err)
    }
}
```

타임아웃 테스트는 실제 시간을 기다려야 해서 테스트 속도에 영향을 준다. 인터페이스로 시간을 추상화하거나, 타임아웃 값을 파라미터로 받아서 테스트에서는 짧게 설정하는 방법을 쓴다.

### context value 검증

미들웨어가 context에 값을 제대로 설정하는지 테스트할 때는 핸들러를 목으로 만들어서 context를 캡처한다.

```go
func TestAuthMiddlewareSetsClaims(t *testing.T) {
    var capturedCtx context.Context

    handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        capturedCtx = r.Context()
        w.WriteHeader(http.StatusOK)
    })

    mw := AuthMiddleware(handler)
    req := httptest.NewRequest("GET", "/", nil)
    req.Header.Set("Authorization", "Bearer "+validToken)

    mw.ServeHTTP(httptest.NewRecorder(), req)

    claims, ok := ClaimsFromContext(capturedCtx)
    if !ok {
        t.Fatal("claims not set in context")
    }
    if claims.UserID != expectedUserID {
        t.Errorf("userID mismatch: got %d, want %d", claims.UserID, expectedUserID)
    }
}
```

### WithCancelCause 테스트

```go
func TestPipelineFailureCause(t *testing.T) {
    ctx := context.Background()
    expectedErr := fmt.Errorf("stage B: %w", ErrDataCorrupted)

    err := runPipeline(ctx, []Stage{
        {Name: "A", Run: func(ctx context.Context) error { return nil }},
        {Name: "B", Run: func(ctx context.Context) error { return ErrDataCorrupted }},
    })

    if !errors.Is(err, ErrDataCorrupted) {
        t.Errorf("expected ErrDataCorrupted in cause chain, got %v", err)
    }
}
```

## HTTP/gRPC 서비스 간 context 전파

### HTTP: trace ID 전파

서비스 사이에 context를 그대로 넘길 수는 없다. context는 프로세스 내부 개념이고 네트워크 경계를 넘지 못한다. 대신 context에 담긴 값을 HTTP 헤더나 gRPC 메타데이터로 직렬화해서 넘긴다.

```go
const traceIDHeader = "X-Trace-ID"

// 아웃바운드 HTTP 요청에 trace ID를 헤더로 주입
func NewTracedHTTPClient(base http.RoundTripper) http.RoundTripper {
    if base == nil {
        base = http.DefaultTransport
    }
    return &tracedTransport{base: base}
}

type tracedTransport struct {
    base http.RoundTripper
}

func (t *tracedTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    req = req.Clone(req.Context())
    if traceID, ok := TraceIDFromContext(req.Context()); ok {
        req.Header.Set(traceIDHeader, traceID)
    }
    return t.base.RoundTrip(req)
}

// 인바운드 요청에서 trace ID를 꺼내 context에 주입
func TraceIDMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        traceID := r.Header.Get(traceIDHeader)
        if traceID == "" {
            traceID = generateTraceID()
        }
        ctx := WithTraceID(r.Context(), traceID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

취소 전파는 별도 문제다. HTTP 클라이언트에 context를 넘기면 클라이언트가 연결을 취소하지만, 서버 측에서는 클라이언트 연결이 끊겼을 때 이미 처리 중인 요청이 자동으로 취소되지 않는다. 서버가 클라이언트 연결 종료를 감지하려면 `r.Context()`의 Done 채널을 모니터링해야 한다.

```go
func longRunningHandler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()

    resultCh := make(chan Result, 1)
    go func() {
        resultCh <- expensiveQuery(ctx)
    }()

    select {
    case result := <-resultCh:
        json.NewEncoder(w).Encode(result)
    case <-ctx.Done():
        // 클라이언트가 연결을 끊었다
        // w에 쓰는 건 의미 없지만 서버 로그는 남긴다
        log.Printf("client disconnected: %v", ctx.Err())
    }
}
```

### gRPC: 메타데이터와 timeout 전파

gRPC는 context를 통해 deadline과 메타데이터를 전파하는 구조가 내장돼 있다. 클라이언트에서 `context.WithTimeout`으로 deadline을 설정하면 gRPC 프레임워크가 이를 헤더로 직렬화해서 서버로 보내고, 서버 측에서는 수신한 deadline을 기반으로 context를 재구성한다.

```go
// 클라이언트
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

resp, err := client.GetUser(ctx, &pb.GetUserRequest{Id: userID})
// gRPC 프레임워크가 ctx의 deadline을 grpc-timeout 헤더로 전송한다
```

```go
// 서버 - 별도 처리 없이 ctx를 그대로 사용
func (s *userServer) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    // ctx.Deadline()이 클라이언트가 설정한 deadline을 반영한다
    user, err := s.repo.FindByID(ctx, req.Id)
    if err != nil {
        return nil, status.Errorf(codes.Internal, "query failed: %v", err)
    }
    return toProto(user), nil
}
```

커스텀 메타데이터는 gRPC 인터셉터에서 처리한다.

```go
// 클라이언트 인터셉터 - context에서 trace ID를 꺼내 gRPC 메타데이터에 주입
func traceIDUnaryClientInterceptor(
    ctx context.Context,
    method string,
    req, reply any,
    cc *grpc.ClientConn,
    invoker grpc.UnaryInvoker,
    opts ...grpc.CallOption,
) error {
    if traceID, ok := TraceIDFromContext(ctx); ok {
        md := metadata.Pairs("x-trace-id", traceID)
        ctx = metadata.NewOutgoingContext(ctx, md)
    }
    return invoker(ctx, method, req, reply, cc, opts...)
}

// 서버 인터셉터 - gRPC 메타데이터에서 trace ID를 꺼내 context에 주입
func traceIDUnaryServerInterceptor(
    ctx context.Context,
    req any,
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (any, error) {
    if md, ok := metadata.FromIncomingContext(ctx); ok {
        if vals := md.Get("x-trace-id"); len(vals) > 0 {
            ctx = WithTraceID(ctx, vals[0])
        }
    }
    return handler(ctx, req)
}
```

### 서비스 간 deadline 슬랙 처리

upstream에서 받은 deadline을 그대로 downstream에 전달하면 downstream이 응답하기 전에 upstream이 타임아웃을 맞는 문제가 생긴다. deadline의 일부를 여유로 남기는 패턴을 쓴다.

```go
func callDownstream(ctx context.Context) (*Response, error) {
    deadline, ok := ctx.Deadline()
    if ok {
        remaining := time.Until(deadline)
        if remaining < 100*time.Millisecond {
            // 남은 시간이 너무 짧아서 downstream 호출 자체를 포기
            return nil, fmt.Errorf("insufficient deadline: %v remaining", remaining)
        }
        // 네트워크 왕복 등을 고려해 50ms 슬랙을 뺀다
        var cancel context.CancelFunc
        ctx, cancel = context.WithDeadline(ctx, deadline.Add(-50*time.Millisecond))
        defer cancel()
    }

    return downstreamClient.Call(ctx, req)
}
```

이 패턴은 deadline propagation을 다루는 흔한 방법이다. 정확한 슬랙 값은 네트워크 레이턴시와 서비스 SLA에 따라 조정해야 한다.
