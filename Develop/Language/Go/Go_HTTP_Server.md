---
title: Go net/http 서버
tags: [go, http, devops, language]
updated: 2026-07-08
---

# Go net/http 서버

Go 표준 라이브러리의 `net/http`는 프로덕션에서 그대로 쓸 수 있는 수준이다. Nginx 같은 리버스 프록시 뒤에 두는 구조라면 서드파티 라이브러리 없이 표준 라이브러리만으로 서버를 운영하는 팀도 많다.

## Handler와 HandlerFunc

`net/http`에서 요청을 처리하는 단위는 `Handler` 인터페이스다.

```go
type Handler interface {
    ServeHTTP(ResponseWriter, *Request)
}
```

`ServeHTTP`를 구현한 타입은 모두 핸들러다. 구조체 기반 핸들러는 의존성을 필드로 들고 다닐 때 쓴다.

```go
type OrderHandler struct {
    db    *sql.DB
    cache *redis.Client
}

func (h *OrderHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    // h.db, h.cache 사용 가능
    orders, err := fetchOrders(r.Context(), h.db)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(orders)
}
```

함수 하나로 핸들러를 만들고 싶을 때는 `http.HandlerFunc`를 쓴다. `HandlerFunc`는 함수 타입에 `ServeHTTP`를 구현해 둔 것이다.

```go
type HandlerFunc func(ResponseWriter, *Request)

func (f HandlerFunc) ServeHTTP(w ResponseWriter, r *Request) {
    f(w, r)
}
```

직접 함수를 핸들러로 등록할 때 내부에서 이 변환이 일어난다.

```go
http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
})
```

의존성이 없는 단순 엔드포인트는 `HandlerFunc`로 충분하고, DB나 외부 클라이언트가 필요한 핸들러는 구조체로 만드는 게 테스트하기 편하다.

## ServeMux vs 서드파티 라우터

### 표준 ServeMux

Go 1.22 이전의 `http.ServeMux`는 패턴 매칭이 단순하다. 경로 변수, HTTP 메서드 구분, 와일드카드가 없다.

```go
mux := http.NewServeMux()
mux.HandleFunc("/api/orders", handleOrders)     // 정확히 /api/orders
mux.HandleFunc("/api/orders/", handleOrdersPrefix) // /api/orders/로 시작하는 모든 경로
```

`/api/orders/`처럼 슬래시로 끝나는 패턴은 해당 접두사를 가진 모든 경로에 매칭된다. `/api/orders`만 처리하고 싶은데 `/api/orders/123`까지 들어오면 핸들러 안에서 직접 파싱해야 한다.

Go 1.22부터 ServeMux가 크게 개선됐다.

```go
// Go 1.22+
mux := http.NewServeMux()

// HTTP 메서드 + 경로 변수 지원
mux.HandleFunc("GET /api/orders/{id}", func(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    // ...
})

mux.HandleFunc("POST /api/orders", createOrder)
mux.HandleFunc("DELETE /api/orders/{id}", deleteOrder)
```

1.22 이상을 쓸 수 있다면 서드파티 라우터 없이 표준 라이브러리로 해결되는 경우가 많아졌다.

### 서드파티 라우터가 필요한 경우

`chi`, `gorilla/mux`, `gin`의 라우터 부분처럼 서드파티를 쓰는 주된 이유는 두 가지다.

첫째, 1.22 미만 Go 버전을 유지해야 하는 경우다. 경로 변수나 메서드 라우팅을 표준 라이브러리로 구현하려면 직접 파싱 코드를 작성해야 한다.

둘째, 라우트 그룹과 서브라우터가 필요한 경우다. API 버전별로 미들웨어를 다르게 적용하거나, 인증이 필요한 라우트와 공개 라우트를 구분하는 구조를 만들 때 `chi`의 서브라우터가 편하다.

```go
// chi를 쓸 때
r := chi.NewRouter()

r.Group(func(r chi.Router) {
    r.Use(authMiddleware)
    r.Get("/api/orders", handleGetOrders)
    r.Post("/api/orders", handleCreateOrder)
})

r.Group(func(r chi.Router) {
    r.Get("/health", handleHealth)
    r.Get("/metrics", handleMetrics)
})
```

`gin`은 라우터뿐 아니라 바인딩, 검증, 렌더링까지 포함한 프레임워크다. 팀 전체가 gin 생태계에 익숙하거나 빠르게 프로토타입을 만들어야 하는 상황이면 쓸 수 있지만, 표준 `net/http`와 인터페이스가 달라서 나중에 라이브러리 교체가 어려워진다.

`chi`는 표준 `http.Handler`와 호환되기 때문에 기존 미들웨어를 그대로 쓸 수 있다. 서드파티를 써야 한다면 `chi`를 선택하는 게 표준 라이브러리와 이질감이 적다.

## 미들웨어 체인

미들웨어는 `Handler`를 받아서 `Handler`를 반환하는 함수다.

```go
type Middleware func(http.Handler) http.Handler
```

로깅 미들웨어를 예로 들면:

```go
func logging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
    })
}
```

여러 미들웨어를 체이닝할 때는 중첩 호출로 이어 붙인다.

```go
handler := logging(rateLimit(auth(mux)))
```

이 코드에서 요청이 들어오면 `logging` → `rateLimit` → `auth` → `mux` 순서로 실행된다. 읽는 순서와 실행 순서가 같다.

체인이 길어지면 헬퍼 함수를 만든다.

```go
func chain(h http.Handler, middlewares ...Middleware) http.Handler {
    for i := len(middlewares) - 1; i >= 0; i-- {
        h = middlewares[i](h)
    }
    return h
}

handler := chain(mux, logging, rateLimit, auth)
```

역순으로 적용해야 실행 순서가 선언 순서와 일치한다.

### 응답 코드를 캡처하는 미들웨어

로깅 미들웨어에서 응답 상태 코드를 기록하려면 `ResponseWriter`를 래핑해야 한다. 기본 `ResponseWriter`는 `WriteHeader` 이후 상태 코드를 꺼내는 방법이 없다.

```go
type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}

func logging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
        start := time.Now()
        next.ServeHTTP(rw, r)
        log.Printf("%s %s %d %v", r.Method, r.URL.Path, rw.statusCode, time.Since(start))
    })
}
```

`WriteHeader`를 명시적으로 호출하지 않으면 상태 코드는 200이므로 기본값을 200으로 설정한다.

### context를 통한 값 전달

인증 미들웨어에서 핸들러로 사용자 정보를 넘길 때 context를 쓴다.

```go
type contextKey struct{ name string }

var userKey = &contextKey{"user"}

func auth(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        user, err := validateToken(token)
        if err != nil {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return
        }

        ctx := context.WithValue(r.Context(), userKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func userFromContext(ctx context.Context) (*User, bool) {
    u, ok := ctx.Value(userKey).(*User)
    return u, ok
}
```

## Graceful Shutdown

서버를 그냥 종료하면 처리 중인 요청이 끊긴다. `http.Server`의 `Shutdown` 메서드는 새 연결 수락을 멈추고 기존 요청이 완료될 때까지 기다린다.

```go
func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("GET /health", handleHealth)

    server := &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }

    // 서버를 별도 고루틴에서 실행
    go func() {
        if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            log.Fatalf("server error: %v", err)
        }
    }()

    // SIGINT, SIGTERM 대기
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("shutting down...")

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := server.Shutdown(ctx); err != nil {
        log.Printf("forced shutdown: %v", err)
    }
}
```

`Shutdown` 이후 `ListenAndServe`는 `http.ErrServerClosed`를 반환한다. 이 에러는 정상 종료이므로 체크해서 걸러내야 한다. 그냥 `log.Fatal`로 처리하면 정상 종료인데도 에러 로그가 남는다.

타임아웃 30초는 가장 긴 요청이 얼마나 걸릴 수 있는지에 맞춰 정한다. 배치 작업이나 파일 업로드 엔드포인트가 있다면 그 시간을 고려해야 한다.

`Shutdown`은 웹소켓처럼 Hijack된 연결은 닫지 않는다. 웹소켓 연결이 있으면 별도 처리가 필요하다.

## 타임아웃 설정 실수 패턴

`http.Server`에는 여러 타임아웃 설정이 있다.

```go
server := &http.Server{
    Addr:         ":8080",
    Handler:      mux,
    ReadTimeout:  5 * time.Second,
    WriteTimeout: 10 * time.Second,
    IdleTimeout:  120 * time.Second,
}
```

### ReadTimeout과 WriteTimeout

`ReadTimeout`은 요청 헤더와 바디를 읽는 시간 전체에 적용된다. 파일 업로드 엔드포인트가 있는데 `ReadTimeout`을 짧게 설정하면 큰 파일 업로드가 중간에 끊긴다.

`WriteTimeout`은 응답을 쓰기 시작하는 시점부터가 아니라 요청 읽기가 끝난 시점부터 카운트된다. DB 쿼리가 오래 걸리거나 외부 API를 호출하는 핸들러라면 `WriteTimeout` 안에 처리 시간이 포함된다.

자주 하는 실수는 `ReadTimeout`만 설정하고 `WriteTimeout`을 빠뜨리는 것이다. 클라이언트가 응답을 읽지 않으면 서버 고루틴이 계속 대기 상태로 남는다.

### 핸들러 타임아웃

서버 수준 타임아웃과 별개로 특정 엔드포인트에만 타임아웃을 걸 때는 `http.TimeoutHandler`를 쓴다.

```go
slowHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    time.Sleep(10 * time.Second)
    w.Write([]byte("done"))
})

// 이 핸들러는 3초 안에 응답하지 않으면 503 반환
mux.Handle("/slow", http.TimeoutHandler(slowHandler, 3*time.Second, "request timeout"))
```

`TimeoutHandler`는 내부적으로 고루틴을 띄워서 핸들러를 실행하고 타임아웃이 지나면 503을 클라이언트에 보낸다. 그런데 핸들러 고루틴 자체는 멈추지 않는다. 핸들러가 context 취소를 무시하고 계속 실행되는 경우 고루틴이 쌓인다.

`TimeoutHandler`를 제대로 쓰려면 핸들러가 `r.Context()`를 확인해야 한다.

```go
mux.Handle("/slow", http.TimeoutHandler(
    http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        ctx := r.Context()

        result, err := doSlowWork(ctx) // ctx 전달
        if err != nil {
            if errors.Is(err, context.DeadlineExceeded) {
                return // TimeoutHandler가 이미 503 보냄
            }
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }
        json.NewEncoder(w).Encode(result)
    }),
    3*time.Second,
    "request timeout",
))
```

### IdleTimeout 미설정

Keep-Alive 연결을 재사용하는 클라이언트가 연결을 무기한 열어두면 서버 측 파일 디스크립터가 고갈된다. `IdleTimeout`을 설정하지 않으면 `KeepAlive` 연결이 영원히 살아있을 수 있다.

`ReadHeaderTimeout`도 분리해서 설정하는 게 낫다. Slowloris 같은 공격에서 클라이언트가 헤더를 아주 천천히 보내면 `ReadTimeout`이 있어도 연결이 오래 유지된다. 헤더 읽기에만 짧은 타임아웃을 걸 수 있다.

```go
server := &http.Server{
    Addr:              ":8080",
    Handler:           mux,
    ReadHeaderTimeout: 2 * time.Second,
    ReadTimeout:       10 * time.Second,
    WriteTimeout:      30 * time.Second,
    IdleTimeout:       120 * time.Second,
}
```

### TLS 서버의 WriteTimeout

TLS를 직접 처리하는 경우 `WriteTimeout`에 TLS 핸드셰이크 시간이 포함된다. 클라이언트 수가 많고 TLS 핸드셰이크가 느리면 `WriteTimeout`을 너무 짧게 설정했을 때 핸드셰이크 중에 타임아웃이 발생할 수 있다.

## 실제 서버 구성 예시

```go
package main

import (
    "context"
    "errors"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    mux := http.NewServeMux()

    // 핸들러 등록
    orderHandler := &OrderHandler{db: db}
    mux.Handle("GET /api/orders/{id}", orderHandler)
    mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
    })

    // 미들웨어 체인
    handler := chain(mux, requestID, logging, recover)

    server := &http.Server{
        Addr:              ":8080",
        Handler:           handler,
        ReadHeaderTimeout: 2 * time.Second,
        ReadTimeout:       10 * time.Second,
        WriteTimeout:      30 * time.Second,
        IdleTimeout:       120 * time.Second,
    }

    go func() {
        log.Printf("listening on %s", server.Addr)
        if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            log.Fatalf("server error: %v", err)
        }
    }()

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := server.Shutdown(ctx); err != nil {
        log.Printf("shutdown error: %v", err)
    }
}
```

패닉 복구 미들웨어는 미들웨어 체인에서 가장 안쪽에 두면 핸들러 패닉을 잡지 못할 수 있다. 체인의 가장 바깥에 두거나, 적어도 로깅 미들웨어보다 안쪽에 두어야 패닉 발생 시 요청 정보도 함께 로깅된다.
