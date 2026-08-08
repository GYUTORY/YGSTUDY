---
title: Go context 패키지
tags: [go, language]
updated: 2026-07-08
---

# Go context 패키지

`context` 패키지는 요청 범위의 데이터와 취소 신호, 타임아웃을 고루틴 사이에 전달하는 수단이다. 1.7에서 표준 라이브러리로 편입됐고, 지금은 HTTP 핸들러, DB 쿼리, gRPC 호출 어디에나 `ctx context.Context`가 첫 번째 인자로 들어간다.

실무에서 context를 잘못 쓰면 두 가지 문제가 생긴다. 취소가 전파되지 않아 고루틴이 남거나, value에 뭐든 다 넣어서 함수 시그니처가 숨겨지는 문제다.

## WithCancel, WithTimeout, WithDeadline 차이

세 함수 모두 부모 context에서 파생된 자식 context와 취소 함수를 반환한다. 차이는 취소 조건이다.

**WithCancel**

명시적으로 `cancel()`을 호출해야 취소된다. 취소 시점을 코드에서 직접 제어할 때 쓴다.

```go
ctx, cancel := context.WithCancel(parentCtx)
defer cancel() // 반드시 호출해야 리소스가 해제된다

go func() {
    select {
    case result := <-workCh:
        processResult(result)
    case <-ctx.Done():
        return
    }
}()

// 조건이 충족되면 취소
if earlyExit {
    cancel()
}
```

**WithTimeout**

현재 시각 기준으로 duration 후에 자동 취소된다. 내부적으로 `WithDeadline(parent, time.Now().Add(timeout))`과 동일하다.

```go
ctx, cancel := context.WithTimeout(parentCtx, 3*time.Second)
defer cancel()

resp, err := http.Get("https://example.com")
```

**WithDeadline**

절대 시각을 지정한다. 여러 작업이 같은 마감 시각을 공유해야 할 때 쓴다.

```go
deadline := time.Now().Add(5 * time.Second)
ctx, cancel := context.WithDeadline(parentCtx, deadline)
defer cancel()
```

세 경우 모두 `defer cancel()`을 빠뜨리면 안 된다. 타임아웃이 만료돼서 context가 취소됐더라도 `cancel()`을 명시적으로 호출해야 내부 타이머 고루틴이 정리된다. 호출하지 않으면 부모 context가 살아있는 동안 타이머 고루틴이 계속 남아있다.

### 이미 만료된 context 판별

```go
ctx, cancel := context.WithTimeout(parentCtx, 3*time.Second)
defer cancel()

// 남은 시간 확인
if deadline, ok := ctx.Deadline(); ok {
    remaining := time.Until(deadline)
    log.Printf("deadline in %v", remaining)
}

// 이미 취소됐는지 확인
select {
case <-ctx.Done():
    return ctx.Err() // context.DeadlineExceeded 또는 context.Canceled
default:
}
```

`ctx.Err()`는 context가 취소되지 않은 상태면 nil을 반환하고, 취소됐으면 `context.Canceled` 또는 `context.DeadlineExceeded`를 반환한다. 둘의 차이로 타임아웃인지 명시적 취소인지 구분한다.

## context 전파 규칙

context는 트리 구조로 전파된다. 부모가 취소되면 자식도 전부 취소된다. 반대는 성립하지 않는다. 자식이 취소돼도 부모나 다른 형제 context에는 영향이 없다.

```
context.Background()
    └── WithCancel (요청 레벨)
            ├── WithTimeout (DB 쿼리, 500ms)
            └── WithTimeout (외부 API 호출, 2s)
```

HTTP 서버에서 각 요청은 `r.Context()`로 context를 받는다. 클라이언트가 연결을 끊으면 이 context가 취소된다. 핸들러 안에서 이 context를 DB 드라이버나 HTTP 클라이언트에 넘기면 클라이언트가 사라졌을 때 진행 중인 작업이 자동으로 중단된다.

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()

    // DB 쿼리에 ctx를 넘긴다
    rows, err := db.QueryContext(ctx, "SELECT * FROM orders WHERE user_id = $1", userID)
    if err != nil {
        if errors.Is(err, context.Canceled) {
            // 클라이언트가 연결을 끊었다
            return
        }
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    // ...
}
```

context를 넘기지 않으면 클라이언트가 사라진 후에도 DB 쿼리가 끝까지 실행된다. 네트워크가 느린 환경이나 쿼리가 오래 걸리는 경우 서버 리소스를 불필요하게 소모한다.

### context를 끊어야 하는 경우

부모 context가 취소돼도 작업을 계속해야 하는 경우가 있다. 요청이 취소됐지만 감사 로그는 남겨야 한다거나, 결제 요청이 취소됐는데 트랜잭션 롤백은 완료해야 하는 경우다.

```go
func handler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()

    if err := processPayment(ctx); err != nil {
        // 결제 실패, 롤백은 요청 context와 무관하게 수행
        rollbackCtx := context.Background() // 또는 별도 timeout 부여
        if rbErr := rollback(rollbackCtx, txID); rbErr != nil {
            log.Printf("rollback failed: %v", rbErr)
        }
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    // ...
}
```

`context.Background()`나 `context.WithoutCancel()`(Go 1.21+)로 부모와 독립된 context를 만든다. `context.WithoutCancel`은 값은 상속하되 취소 신호만 차단한다.

```go
// Go 1.21+
cleanupCtx := context.WithoutCancel(ctx)
go func() {
    defer cleanup(cleanupCtx) // 요청 ctx가 취소돼도 실행된다
}()
```

## goroutine 취소 패턴

고루틴을 띄울 때 항상 어떻게 종료할지를 먼저 설계해야 한다. context 없이 고루틴을 띄우면 그 고루틴은 프로세스가 끝날 때까지 살아있을 수 있다.

### 단일 고루틴 취소

```go
func doWork(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }

        if err := step(); err != nil {
            return err
        }
    }
}
```

루프마다 `ctx.Done()`을 체크하는 게 기본 패턴이다. `default` 케이스가 없으면 `ctx.Done()`이 닫힐 때까지 블로킹된다. 작업이 CPU를 점유하는 루프라면 위 패턴이 맞고, 블로킹 IO가 있는 경우는 IO 자체에 context를 넘기는 게 낫다.

### 여러 고루틴을 한 번에 취소

```go
func runParallel(ctx context.Context, tasks []Task) error {
    ctx, cancel := context.WithCancel(ctx)
    defer cancel()

    errCh := make(chan error, len(tasks))

    for _, task := range tasks {
        t := task
        go func() {
            errCh <- t.Run(ctx)
        }()
    }

    for range tasks {
        if err := <-errCh; err != nil {
            cancel() // 하나가 실패하면 나머지를 취소
            // errCh는 버퍼가 있으므로 나머지 고루틴도 결과를 보낼 수 있다
        }
    }

    return nil
}
```

`errgroup`을 쓰면 이 패턴을 더 간결하게 처리한다.

```go
func runParallel(ctx context.Context, tasks []Task) error {
    g, ctx := errgroup.WithContext(ctx)

    for _, task := range tasks {
        t := task
        g.Go(func() error {
            return t.Run(ctx)
        })
    }

    return g.Wait()
}
```

`errgroup.WithContext`는 내부적으로 `WithCancel`을 생성해서 어떤 고루틴이든 에러를 반환하면 나머지 고루틴의 context가 취소된다.

### 블로킹 시스템 호출 취소

DB 드라이버, HTTP 클라이언트, gRPC 클라이언트처럼 context를 지원하는 라이브러리는 `ctx`를 넘기면 내부에서 취소를 처리한다. 문제는 context를 지원하지 않는 구형 라이브러리다.

```go
func callLegacyAPI(ctx context.Context, req Request) (Response, error) {
    resultCh := make(chan struct {
        resp Response
        err  error
    }, 1)

    go func() {
        resp, err := legacyClient.Do(req) // context를 모른다
        resultCh <- struct {
            resp Response
            err  error
        }{resp, err}
    }()

    select {
    case result := <-resultCh:
        return result.resp, result.err
    case <-ctx.Done():
        // 고루틴은 계속 실행되지만 결과는 버린다
        // resultCh에 버퍼가 있어서 고루틴이 쌓이지 않는다
        return Response{}, ctx.Err()
    }
}
```

이 패턴은 고루틴 누수를 완전히 막지는 못한다. 레거시 호출이 끝나야 고루틴이 종료된다. 레거시 클라이언트에 자체 타임아웃 설정이 없다면 고루틴이 오래 살 수 있다.

## context value 남용 문제

`context.WithValue`는 요청 범위 데이터를 전달하는 수단이지만, 잘못 쓰면 함수 시그니처에서 의존성이 숨어버린다.

```go
// 나쁜 예 - context에서 꺼내는 값이 많아지면 무슨 데이터가 필요한지 알 수 없다
func processOrder(ctx context.Context) error {
    userID := ctx.Value("user_id").(string)
    tenantID := ctx.Value("tenant_id").(string)
    traceID := ctx.Value("trace_id").(string)
    // ...
}
```

context value에 넣어도 괜찮은 것과 함수 인자로 넘겨야 하는 것을 구분해야 한다.

**context value에 넣을 것:**
- 추적 ID, 요청 ID (로깅/트레이싱용)
- 인증 토큰이나 사용자 세션 (미들웨어가 설정하는 값)
- 요청 메타데이터 (Accept-Language 등)

**함수 인자로 넘길 것:**
- 비즈니스 로직에 직접 사용되는 값
- 함수가 동작하기 위해 반드시 필요한 파라미터
- 테스트에서 쉽게 변경해야 하는 값

context value는 타입 안전성이 없다. `ctx.Value(key)`는 `interface{}`를 반환하므로 타입 단언이 필요하고, 키를 잘못 쓰면 nil이 나온다.

```go
// 타입 안전하게 쓰는 방법
type contextKey struct{ name string }

var (
    traceIDKey = &contextKey{"trace_id"}
    userIDKey  = &contextKey{"user_id"}
)

func WithTraceID(ctx context.Context, traceID string) context.Context {
    return context.WithValue(ctx, traceIDKey, traceID)
}

func TraceIDFromContext(ctx context.Context) (string, bool) {
    id, ok := ctx.Value(traceIDKey).(string)
    return id, ok
}
```

키를 공개된 문자열 대신 unexported 타입으로 만들면 외부 패키지에서 같은 키로 충돌하는 사고를 막는다. 문자열 키를 쓰면 다른 패키지가 실수로 같은 키를 쓸 때 값이 덮어써진다.

### context value로 의존성 주입 금지

데이터베이스 연결이나 서비스 객체를 context에 넣는 코드를 가끔 본다. 테스트하기 어려워지고, 어떤 의존성이 필요한지 추적이 안 된다.

```go
// 하면 안 되는 패턴
func GetUser(ctx context.Context, id int) (*User, error) {
    db := ctx.Value("db").(*sql.DB) // DB를 context에서 꺼낸다
    // ...
}

// 올바른 방법
type UserRepository struct {
    db *sql.DB
}

func (r *UserRepository) GetUser(ctx context.Context, id int) (*User, error) {
    return queryUser(ctx, r.db, id)
}
```

의존성은 구조체 필드나 함수 인자로 명시적으로 전달해야 한다.

## 실무에서 자주 겪는 문제

### context가 이미 취소된 상태에서 새 작업 시작

```go
// ctx가 이미 취소된 상태면 WithTimeout도 즉시 취소된 상태로 반환된다
ctx, cancel := context.WithTimeout(cancelledCtx, 5*time.Second)
defer cancel()

// 이 시점에서 ctx.Err() != nil
```

부모가 취소되면 자식도 즉시 취소 상태다. 드물지만 이미 취소된 context를 넘겨서 작업이 시작도 안 하고 실패하는 경우가 있다. HTTP 미들웨어에서 context를 수정하다가 실수로 취소된 context를 핸들러에 넘기는 패턴에서 나타난다.

### select에서 context 우선순위

```go
select {
case result := <-workCh:
    return result, nil
case <-ctx.Done():
    return nil, ctx.Err()
}
```

`workCh`와 `ctx.Done()`이 동시에 준비됐을 때 Go는 무작위로 하나를 선택한다. context가 취소됐더라도 이미 workCh에 값이 있으면 그걸 처리할 수 있다. 취소 시 반드시 결과를 버려야 한다면 별도 처리가 필요하다.

```go
select {
case <-ctx.Done():
    return nil, ctx.Err()
default:
}

select {
case result := <-workCh:
    return result, nil
case <-ctx.Done():
    return nil, ctx.Err()
}
```

첫 번째 select로 이미 취소됐는지 먼저 확인하면 취소 상태에서 작업 결과가 선택될 가능성을 줄인다.
