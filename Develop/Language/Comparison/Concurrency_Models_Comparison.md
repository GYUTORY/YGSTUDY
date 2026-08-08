---
title: 언어별 동시성 모델 비교
tags: [java, go, rust, javascript]
updated: 2026-07-09
---

# 언어별 동시성 모델 비교

Java, Go, Rust, JavaScript는 동시성을 근본적으로 다르게 처리한다. Java는 OS 스레드를 직접 다루고, Go는 런타임이 관리하는 경량 고루틴을 쓰고, Rust는 컴파일 타임에 데이터 경쟁을 막고, JavaScript는 싱글 스레드 이벤트 루프로 논블로킹 I/O를 처리한다. 같은 HTTP 요청 수천 개를 처리하는 서버를 만들어도 언어마다 코드 구조와 주의사항이 완전히 다르다.

## Java: 스레드와 CompletableFuture

Java의 전통적인 동시성 모델은 OS 스레드다. `Thread` 클래스나 `ExecutorService`로 스레드를 만들고 작업을 제출한다. 스레드 하나당 스택 메모리가 기본 512KB~1MB를 차지하기 때문에, 수천 개의 동시 요청을 처리하는 서버에서 스레드 수를 무한정 늘릴 수 없다. 실무에서는 스레드 풀을 고정 크기로 잡고, 큐에 작업을 쌓는 방식을 사용한다.

```java
ExecutorService executor = Executors.newFixedThreadPool(50);

executor.submit(() -> {
    // I/O 작업 — 스레드가 블로킹됨
    String result = callExternalApi();
    processResult(result);
});
```

스레드가 I/O를 기다리는 동안 블로킹되는 것이 핵심 문제다. DB 쿼리 하나에 100ms가 걸리면, 그 시간 동안 스레드는 아무것도 못하고 대기한다. 스레드 풀이 50개면 동시에 처리할 수 있는 요청 수는 50개가 상한이다.

Java 8에서 도입된 `CompletableFuture`는 논블로킹 체이닝을 제공한다.

```java
CompletableFuture<User> future = CompletableFuture
    .supplyAsync(() -> userRepository.findById(userId), executor)
    .thenApplyAsync(user -> {
        user.setLastLoginAt(LocalDateTime.now());
        return user;
    }, executor)
    .exceptionally(ex -> {
        log.error("유저 조회 실패: {}", ex.getMessage());
        return null;
    });

// 결과가 필요한 시점에 블로킹
User user = future.get(); // 또는 future.join()
```

`CompletableFuture`는 코드가 복잡해질수록 콜백 체이닝이 깊어진다. 에러 처리를 `exceptionally`나 `handle`로 해야 하는데, 여러 단계에서 에러가 날 수 있으면 각 단계마다 처리 로직을 붙여야 한다. 스택 트레이스도 스레드 경계를 넘으면 추적하기 어렵다.

Java 21에서 정식으로 들어온 가상 스레드(Virtual Thread)는 이 구조를 바꾼다. OS 스레드가 아닌 JVM 관리 경량 스레드로, 수십만 개를 만들어도 메모리 부담이 낮다. 블로킹 코드를 그대로 쓰면서 높은 동시성을 얻을 수 있다.

```java
// 가상 스레드 — Java 21+
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> {
        // 블로킹 코드 그대로 사용 가능
        String result = callExternalApi(); // I/O 블로킹해도 OK
        processResult(result);
    });
}
```

### 공유 상태 접근

Java에서 여러 스레드가 같은 데이터를 건드리면 `synchronized`, `ReentrantLock`, 또는 `java.util.concurrent` 패키지의 자료구조를 써야 한다. `ConcurrentHashMap`, `AtomicInteger`, `BlockingQueue` 등이 대표적이다.

```java
// AtomicInteger — 락 없이 원자적 카운터
private final AtomicInteger requestCount = new AtomicInteger(0);

public void handleRequest() {
    int count = requestCount.incrementAndGet();
    // ...
}

// ConcurrentHashMap — 스레드 안전한 맵
private final Map<String, User> cache = new ConcurrentHashMap<>();
```

`synchronized` 블록을 잘못 쓰면 데드락이 발생한다. 락 순서가 일관되지 않으면 두 스레드가 서로를 기다리며 멈춰버린다. 실무에서 데드락은 재현하기 어렵고 스레드 덤프를 분석해야 원인을 찾을 수 있다.

## Go: 고루틴과 채널

Go의 고루틴은 OS 스레드가 아니라 Go 런타임이 관리하는 경량 실행 단위다. 초기 스택이 2KB 정도로 시작해서 필요에 따라 늘어난다. 수십만 개를 동시에 띄워도 메모리 부담이 크지 않다.

```go
// 고루틴은 go 키워드 하나로 시작
go func() {
    result, err := callExternalApi()
    if err != nil {
        log.Printf("API 호출 실패: %v", err)
        return
    }
    processResult(result)
}()
```

고루틴 시작 비용이 워낙 낮아서, HTTP 요청 하나에 고루틴 하나를 붙이는 패턴이 기본이다. Go의 `net/http` 패키지는 요청마다 고루틴을 하나씩 생성한다.

스케줄링은 GOMAXPROCS 수만큼의 OS 스레드 위에서 M:N 방식으로 동작한다. 고루틴이 I/O로 블로킹되면 런타임이 그 고루틴을 파킹하고 다른 고루틴을 OS 스레드에 할당한다. 코드는 동기식으로 보이지만 실제로는 논블로킹으로 동작한다.

```go
// 동기식 코드처럼 보이지만 블로킹 I/O에서 런타임이 다른 고루틴으로 전환
func handleRequest(w http.ResponseWriter, r *http.Request) {
    user, err := db.QueryUser(r.Context(), userID)
    if err != nil {
        http.Error(w, "user not found", http.StatusNotFound)
        return
    }
    json.NewEncoder(w).Encode(user)
}
```

### 채널을 이용한 통신

Go의 동시성 철학은 "공유 메모리로 통신하지 말고, 통신으로 메모리를 공유하라"다. 고루틴 간 데이터 전달은 채널로 한다.

```go
func fetchUsers(ids []int) []User {
    results := make(chan User, len(ids))
    
    for _, id := range ids {
        id := id // 루프 변수 캡처 주의 (Go 1.22 이전)
        go func() {
            user, err := db.QueryUser(context.Background(), id)
            if err != nil {
                log.Printf("유저 조회 실패 %d: %v", id, err)
                return
            }
            results <- user
        }()
    }
    
    users := make([]User, 0, len(ids))
    for range ids {
        users = append(users, <-results)
    }
    return users
}
```

채널을 쓸 때 주의할 점이 있다. 버퍼 없는 채널은 보내는 쪽과 받는 쪽이 동시에 준비되지 않으면 블로킹된다. 고루틴이 채널에 쓰려고 기다리는데 받는 쪽이 없으면 고루틴 누수(goroutine leak)가 발생한다. 서버가 오래 돌수록 메모리가 조금씩 새는 원인 중 하나다.

```go
// 고루틴 누수 패턴 — 채널을 받는 쪽이 에러로 먼저 리턴하면 고루틴이 영원히 막힘
func badPattern(ctx context.Context) (string, error) {
    ch := make(chan string) // 버퍼 없는 채널
    
    go func() {
        result := expensiveOperation()
        ch <- result // ctx가 취소됐으면 여기서 영원히 블로킹
    }()
    
    select {
    case result := <-ch:
        return result, nil
    case <-ctx.Done():
        return "", ctx.Err() // 고루틴은 여전히 살아있음
    }
}

// 버퍼 채널 1개로 해결
func goodPattern(ctx context.Context) (string, error) {
    ch := make(chan string, 1) // 버퍼 1 — 받는 쪽 없어도 쓸 수 있음
    
    go func() {
        result := expensiveOperation()
        ch <- result
    }()
    
    select {
    case result := <-ch:
        return result, nil
    case <-ctx.Done():
        return "", ctx.Err()
    }
}
```

`sync.WaitGroup`, `sync.Mutex`도 자주 쓴다. 공유 맵에 여러 고루틴이 동시에 쓰면 패닉이 발생하기 때문에 맵 접근에는 뮤텍스가 필요하다.

```go
type SafeCache struct {
    mu    sync.RWMutex
    items map[string]User
}

func (c *SafeCache) Get(key string) (User, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    u, ok := c.items[key]
    return u, ok
}

func (c *SafeCache) Set(key string, u User) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = u
}
```

## Rust: async/await와 tokio

Rust의 비동기는 `async fn`과 `await` 키워드로 표현하지만, 실행 자체는 런타임이 없다. 표준 라이브러리는 `Future` 트레이트만 정의하고, 실제 스케줄링은 tokio나 async-std 같은 외부 런타임이 담당한다. 실무에서는 거의 tokio를 사용한다.

```rust
use tokio;

#[tokio::main]
async fn main() {
    let result = fetch_user(1).await;
    println!("{:?}", result);
}

async fn fetch_user(id: u64) -> Result<User, Error> {
    let user = db::query_user(id).await?; // ?로 에러 전파
    Ok(user)
}
```

`async fn`은 호출하면 `Future`를 반환한다. `.await`를 붙여야 실제로 실행된다. `.await` 없이 `async fn`만 호출하면 아무것도 실행되지 않는다.

tokio 런타임은 워커 스레드 풀을 관리한다. 기본적으로 CPU 코어 수만큼 워커 스레드를 만들고, 태스크를 스레드들에 분산한다. `tokio::spawn`으로 태스크를 런타임에 넘기면 런타임이 적절한 스레드에서 실행한다.

```rust
use tokio::task;

async fn process_requests(ids: Vec<u64>) -> Vec<User> {
    let handles: Vec<_> = ids.into_iter()
        .map(|id| task::spawn(async move {
            fetch_user(id).await
        }))
        .collect();
    
    let mut users = Vec::new();
    for handle in handles {
        if let Ok(Ok(user)) = handle.await {
            users.push(user);
        }
    }
    users
}
```

여러 작업을 병렬로 실행할 때는 `tokio::join!`이나 `futures::future::join_all`을 쓴다.

```rust
use tokio::join;

async fn fetch_dashboard_data(user_id: u64) -> DashboardData {
    let (user, orders, notifications) = join!(
        fetch_user(user_id),
        fetch_orders(user_id),
        fetch_notifications(user_id),
    );
    
    DashboardData {
        user: user.unwrap(),
        orders: orders.unwrap(),
        notifications: notifications.unwrap(),
    }
}
```

### 공유 상태와 소유권

Rust에서 공유 상태 접근은 컴파일러가 강제한다. 여러 태스크가 같은 데이터를 건드리려면 `Arc<Mutex<T>>`나 `Arc<RwLock<T>>`를 써야 한다.

```rust
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

type SharedCache = Arc<Mutex<HashMap<String, User>>>;

async fn get_user_cached(cache: SharedCache, key: &str) -> Option<User> {
    let cache = cache.lock().unwrap(); // 뮤텍스 락
    cache.get(key).cloned()
} // 함수 종료 시 자동으로 락 해제

async fn set_user_cached(cache: SharedCache, key: String, user: User) {
    let mut cache = cache.lock().unwrap();
    cache.insert(key, user);
}
```

async 코드에서 `std::sync::Mutex`를 `.await` 지점에 걸쳐 들고 있으면 컴파일 에러가 난다. `.await` 동안 락을 잡고 있으면 다른 태스크를 블로킹할 수 있기 때문에, `.await`를 넘어가야 하는 경우에는 `tokio::sync::Mutex`를 써야 한다.

```rust
use tokio::sync::Mutex;

async fn fetch_and_cache(cache: Arc<Mutex<HashMap<String, User>>>, id: u64) {
    let user = fetch_user(id).await.unwrap(); // 여기서 .await
    
    let mut cache = cache.lock().await; // tokio Mutex — .await 가능
    cache.insert(id.to_string(), user);
}
```

Rust의 동시성에서 가장 큰 차이는 데이터 경쟁이 컴파일 타임에 막힌다는 점이다. 락 없이 여러 스레드에서 같은 데이터를 수정하려고 하면 컴파일 자체가 안 된다. 런타임 패닉이나 미정의 동작이 아니라 컴파일 에러로 처리된다.

## JavaScript: 이벤트 루프

JavaScript는 싱글 스레드다. 동시에 두 개의 코드가 실행되는 일이 없다. 대신 비동기 I/O 완료, 타이머, Promise 등의 콜백을 이벤트 루프가 순서대로 처리한다.

이벤트 루프의 동작은 다음과 같다. 콜 스택이 비어있을 때, 이벤트 루프는 마이크로태스크 큐(Promise 콜백)를 먼저 모두 처리하고, 그 다음 매크로태스크 큐(setTimeout, I/O 콜백)에서 하나를 가져와 실행한다.

```javascript
console.log('1'); // 동기

setTimeout(() => console.log('2'), 0); // 매크로태스크

Promise.resolve().then(() => console.log('3')); // 마이크로태스크

console.log('4'); // 동기

// 출력 순서: 1, 4, 3, 2
```

`async/await`는 Promise 위에 올라간 문법 설탕이다. `await` 키워드는 Promise가 완료될 때까지 현재 async 함수를 일시 중단하고 이벤트 루프에 제어를 돌려준다.

```javascript
async function handleRequest(req, res) {
    const user = await db.query('SELECT * FROM users WHERE id = ?', [req.userId]);
    const orders = await db.query('SELECT * FROM orders WHERE user_id = ?', [user.id]);
    
    res.json({ user, orders });
}
```

위 코드는 `user` 쿼리가 완료된 후에 `orders` 쿼리를 시작한다. 순차 실행이다. 병렬로 돌리려면 `Promise.all`을 써야 한다.

```javascript
async function handleRequest(req, res) {
    // 병렬 실행
    const [user, latestNews] = await Promise.all([
        db.query('SELECT * FROM users WHERE id = ?', [req.userId]),
        fetchExternalApi('/news/latest'),
    ]);
    
    res.json({ user, latestNews });
}
```

Node.js에서 CPU 집약적인 작업을 이벤트 루프에서 실행하면 전체 서버가 멈춘다. 싱글 스레드이기 때문에 하나의 동기 코드가 100ms 동안 CPU를 점유하면 그 시간 동안 다른 요청을 전혀 처리하지 못한다.

```javascript
// 이벤트 루프를 막는 패턴 — 절대 피해야 함
app.get('/compute', (req, res) => {
    const result = heavyComputation(); // 동기 CPU 연산 — 서버 전체 블로킹
    res.json({ result });
});

// Worker Thread로 CPU 작업 분리
const { Worker } = require('worker_threads');

app.get('/compute', (req, res) => {
    const worker = new Worker('./heavy-computation.js');
    worker.postMessage({ data: req.body });
    worker.on('message', (result) => res.json({ result }));
    worker.on('error', (err) => res.status(500).json({ error: err.message }));
});
```

## 같은 작업, 각 언어로

HTTP API 세 개를 병렬로 호출해서 결과를 합치는 패턴을 비교한다.

**Java (CompletableFuture)**

```java
public DashboardData getDashboard(long userId) throws ExecutionException, InterruptedException {
    CompletableFuture<User> userFuture = 
        CompletableFuture.supplyAsync(() -> userApi.getUser(userId), executor);
    CompletableFuture<List<Order>> ordersFuture = 
        CompletableFuture.supplyAsync(() -> orderApi.getOrders(userId), executor);
    CompletableFuture<List<Notification>> notifFuture = 
        CompletableFuture.supplyAsync(() -> notifApi.getNotifications(userId), executor);
    
    CompletableFuture.allOf(userFuture, ordersFuture, notifFuture).join();
    
    return new DashboardData(
        userFuture.get(),
        ordersFuture.get(),
        notifFuture.get()
    );
}
```

**Go**

```go
func getDashboard(ctx context.Context, userID int64) (*DashboardData, error) {
    type result[T any] struct {
        data T
        err  error
    }
    
    userCh := make(chan result[*User], 1)
    ordersCh := make(chan result[[]*Order], 1)
    notifCh := make(chan result[[]*Notification], 1)
    
    go func() {
        u, err := userApi.GetUser(ctx, userID)
        userCh <- result[*User]{u, err}
    }()
    go func() {
        o, err := orderApi.GetOrders(ctx, userID)
        ordersCh <- result[[]*Order]{o, err}
    }()
    go func() {
        n, err := notifApi.GetNotifications(ctx, userID)
        notifCh <- result[[]*Notification]{n, err}
    }()
    
    userRes := <-userCh
    ordersRes := <-ordersCh
    notifRes := <-notifCh
    
    if userRes.err != nil {
        return nil, userRes.err
    }
    // 나머지 에러 체크...
    
    return &DashboardData{
        User:          userRes.data,
        Orders:        ordersRes.data,
        Notifications: notifRes.data,
    }, nil
}
```

**Rust (tokio)**

```rust
async fn get_dashboard(user_id: u64) -> Result<DashboardData, Error> {
    let (user, orders, notifications) = tokio::join!(
        user_api::get_user(user_id),
        order_api::get_orders(user_id),
        notif_api::get_notifications(user_id),
    );
    
    Ok(DashboardData {
        user: user?,
        orders: orders?,
        notifications: notifications?,
    })
}
```

**JavaScript**

```javascript
async function getDashboard(userId) {
    const [user, orders, notifications] = await Promise.all([
        userApi.getUser(userId),
        orderApi.getOrders(userId),
        notifApi.getNotifications(userId),
    ]);
    
    return { user, orders, notifications };
}
```

## 스케줄링 방식 정리

| 언어 | 실행 단위 | 스케줄러 | 스레드 모델 |
|------|-----------|----------|-------------|
| Java (전통) | OS 스레드 | OS 커널 | 1:1 (스레드당 OS 스레드) |
| Java (가상 스레드) | 가상 스레드 | JVM | M:N |
| Go | 고루틴 | Go 런타임 | M:N |
| Rust + tokio | Future/Task | tokio 런타임 | M:N (워커 스레드 풀) |
| JavaScript (Node.js) | 이벤트 루프 태스크 | libuv | 싱글 스레드 (I/O는 스레드 풀) |

Go와 Rust/tokio의 M:N 모델은 논리적 실행 단위(고루틴, Future) 수가 OS 스레드 수보다 훨씬 많다. I/O 블로킹이 생기면 런타임이 다른 작업을 같은 OS 스레드에서 실행해 CPU 낭비를 줄인다.

## 실제 서버 코드에서 나타나는 차이

**타임아웃과 취소**: Go는 `context.Context`를 거의 모든 함수에 전달한다. 요청 취소 시 컨텍스트가 취소되고, 컨텍스트를 존중하는 라이브러리들은 작업을 중단한다. Java는 `Future.cancel()` 또는 인터럽트로 처리하는데, 모든 라이브러리가 인터럽트를 지원하지 않아 실제 취소가 안 되는 경우가 있다. Rust는 `tokio_util::CancellationToken`이나 `select!` 매크로를 쓴다.

**에러 처리**: Go는 모든 함수가 에러를 값으로 반환하기 때문에 고루틴 안에서 발생한 에러를 채널로 돌려줘야 한다. Java의 `CompletableFuture`는 예외를 내부에 가두고 `.get()` 호출 시 `ExecutionException`으로 감싸서 던진다. Rust는 `?` 연산자로 에러를 전파하고 `join!` 결과에서 각각 `?`로 처리한다. JavaScript는 `await`한 Promise가 reject되면 예외가 던져지므로 `try/catch`로 잡는다.

**CPU 집약 작업**: Java는 별도 스레드에서 실행하면 되고 기존 스레드 풀에 넣을 수 있다. Go에서 CPU 작업이 길면 고루틴이 선점되지 않아 다른 고루틴이 대기할 수 있다. Go 1.14부터 비동기 선점이 도입됐지만 긴 루프에서는 여전히 주의가 필요하다. Rust/tokio에서 CPU 집약 작업은 `task::spawn_blocking`으로 별도 스레드 풀에 보내야 한다. 그냥 async 태스크 안에 넣으면 워커 스레드 전체가 막힌다. JavaScript는 `Worker`를 써서 별도 프로세스에 넘겨야 한다.
