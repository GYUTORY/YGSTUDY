---
title: 언어별 에러 처리 방식 비교
tags: [java, Go, Rust, javascript, python, error-handling, exception, Result]
updated: 2026-07-18
---

# 언어별 에러 처리 방식 비교

에러 처리는 언어 설계 철학이 가장 직접적으로 드러나는 부분이다. Java는 예외를 타입 시스템으로 강제하고, Go는 값으로 돌려주고, Rust는 컴파일러가 처리 여부를 확인하고, Python은 예외를 흐름 제어로 적극 활용하며, JavaScript는 예외를 던지되 처리는 개발자 몫이다. 같은 기능을 구현해도 언어마다 코드 모양이 완전히 달라지는 이유가 여기 있다.

## Java: Checked/Unchecked 예외

Java의 예외 시스템에서 핵심은 체크드(checked)와 언체크드(unchecked) 예외의 구분이다.

체크드 예외는 `Exception`을 상속하며, 메서드 시그니처에 `throws`를 선언하거나 `try-catch`로 처리해야 컴파일된다. `IOException`, `SQLException`이 대표적이다. 언체크드 예외는 `RuntimeException`을 상속하며 선언 없이도 던질 수 있다. `NullPointerException`, `IllegalArgumentException`이 여기 속한다.

```java
// 체크드 예외 — 처리하지 않으면 컴파일 에러
public String readFile(String path) throws IOException {
    return Files.readString(Path.of(path));
}

// 호출하는 쪽에서 반드시 처리해야 함
public void process() {
    try {
        String content = readFile("/etc/hosts");
        System.out.println(content);
    } catch (IOException e) {
        logger.error("파일 읽기 실패: {}", e.getMessage());
    }
}
```

```java
// 언체크드 예외 — throws 선언 없어도 됨
public int divide(int a, int b) {
    if (b == 0) {
        throw new IllegalArgumentException("0으로 나눌 수 없음");
    }
    return a / b;
}
```

체크드 예외는 좋은 의도로 설계됐지만 실무에서 골칫거리가 많다. 라이브러리 하나를 잘못 선택하면 예외 선언이 호출 스택을 타고 올라가며 `throws Exception`으로 퇴화하는 경우가 흔하다. Spring, Hibernate 같은 프레임워크들은 체크드 예외를 언체크드로 감싸서 돌려주는 패턴을 쓴다.

```java
// Spring에서 흔히 보는 패턴
public User findUser(Long id) {
    try {
        return jdbcTemplate.queryForObject(...);
    } catch (DataAccessException e) {
        // DataAccessException은 RuntimeException 계열
        throw new UserNotFoundException("유저를 찾을 수 없음: " + id, e);
    }
}
```

예외를 복구하는 경우는 드물다. 대부분 로깅하고 상위로 전파하거나, HTTP 응답 코드로 변환하는 것이 전부다. Java에서 예외를 `catch`하고 아무것도 안 하는 빈 블록(`catch (Exception e) {}`)은 가장 위험한 안티패턴인데, 조용히 삼켜버리기 때문에 디버깅이 불가능해진다.

## Go: 에러를 값으로 반환

Go는 예외 메커니즘이 없다. 에러는 마지막 반환값으로 돌아온다. `error` 인터페이스를 구현하는 값이면 무엇이든 에러다.

```go
// Go의 기본 패턴: (결과, 에러) 반환
func readFile(path string) (string, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return "", fmt.Errorf("파일 읽기 실패 %s: %w", path, err)
    }
    return string(data), nil
}

func main() {
    content, err := readFile("/etc/hosts")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(content)
}
```

`if err != nil`이 반복되는 것을 보고 처음엔 불편하다고 느끼는 사람이 많다. 실제로 Go 코드에서 이 패턴이 전체 코드의 20~30%를 차지하기도 한다. Go 팀이 의도한 것이기도 하다. 에러 처리를 명시적으로 강제해서, 에러를 그냥 흘려보내는 상황을 코드 레벨에서 보이게 만든다.

에러 전파에는 `%w`로 래핑하는 방식을 쓴다. Go 1.13부터 `errors.Is`, `errors.As`로 래핑된 에러를 언래핑해서 타입을 확인할 수 있다.

```go
var ErrNotFound = errors.New("not found")

func findUser(id int) (*User, error) {
    user, err := db.QueryRow(id)
    if err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, fmt.Errorf("유저 %d: %w", id, ErrNotFound)
        }
        return nil, fmt.Errorf("DB 조회 실패: %w", err)
    }
    return user, nil
}

// 호출하는 쪽에서 특정 에러 타입 확인
user, err := findUser(42)
if errors.Is(err, ErrNotFound) {
    // 404 처리
}
```

Go에도 `panic`과 `recover`가 있지만, 이건 예외 처리용이 아니라 프로그램이 계속 실행할 수 없는 상황(인덱스 초과, nil 포인터 역참조 등)에서 쓴다. 라이브러리 코드에서 `panic`을 `recover`로 잡아 `error`로 변환하는 패턴은 종종 쓰이지만, 일반적인 에러 흐름에 `panic`을 쓰는 것은 Go 관례에 맞지 않는다.

## Rust: Result 타입과 ? 연산자

Rust는 에러 처리를 타입 시스템에 완전히 통합했다. 실패할 수 있는 함수는 `Result<T, E>`를 반환한다. `Ok(T)`는 성공, `Err(E)`는 실패다.

```rust
use std::fs;
use std::io;

fn read_file(path: &str) -> Result<String, io::Error> {
    let content = fs::read_to_string(path)?;
    Ok(content)
}
```

`?` 연산자가 핵심이다. `Result`가 `Err`이면 즉시 현재 함수에서 그 에러를 반환하고, `Ok`면 내부 값을 꺼낸다. Go의 `if err != nil { return err }` 패턴을 한 글자로 줄인 것이다.

```rust
// ? 없이 쓰면 이렇게 된다
fn read_file_verbose(path: &str) -> Result<String, io::Error> {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => return Err(e),
    };
    Ok(content)
}

// ? 쓰면 이렇게 된다
fn read_file(path: &str) -> Result<String, io::Error> {
    let content = fs::read_to_string(path)?;
    Ok(content)
}
```

에러 타입이 다를 때는 `From` 트레이트로 변환하거나, `Box<dyn Error>` 또는 `anyhow::Error` 같은 라이브러리를 쓴다. 실무에서는 `thiserror`로 커스텀 에러 타입을 정의하고, `anyhow`로 애플리케이션 레벨 에러를 처리하는 조합을 많이 쓴다.

```rust
use thiserror::Error;

#[derive(Error, Debug)]
enum AppError {
    #[error("파일을 찾을 수 없음: {0}")]
    NotFound(String),
    #[error("IO 에러: {0}")]
    Io(#[from] std::io::Error),
}

fn process_file(path: &str) -> Result<(), AppError> {
    if !std::path::Path::new(path).exists() {
        return Err(AppError::NotFound(path.to_string()));
    }
    let _content = std::fs::read_to_string(path)?; // io::Error -> AppError::Io 자동 변환
    Ok(())
}
```

Rust도 `panic!`이 있지만, 회복 불가능한 프로그래밍 오류에만 써야 한다는 점은 Go와 같다. `unwrap()`과 `expect()`는 `Result`에서 값을 꺼내되 `Err`면 패닉하므로, 프로토타입이나 테스트 코드 외에는 쓰지 않는 것이 좋다.

컴파일러가 `Result`를 반환하는 함수의 결과를 무시하면 경고를 낸다. 의도적으로 무시할 때는 `let _ = some_result_fn();`처럼 명시해야 한다.

## Python: 예외를 흐름 제어로 쓰는 언어

Python은 EAFP(Easier to Ask Forgiveness than Permission) 방식을 권장한다. 무언가를 하기 전에 조건을 먼저 확인하는 대신, 그냥 시도하고 예외가 나면 처리하는 방식이다.

```python
# LBYL(Look Before You Leap) — Python에서 권장하지 않는 방식
if os.path.exists(path):
    with open(path) as f:
        content = f.read()

# EAFP — Python다운 방식
try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    content = None
```

파일 존재 여부를 확인하고 열면 TOCTOU(Time-of-Check Time-of-Use) 문제가 생긴다. 확인하는 순간과 사용하는 순간 사이에 파일이 삭제될 수 있다. EAFP는 이 문제를 원천적으로 피한다.

`try/except/else/finally` 네 블록을 모두 쓰는 경우가 있다. `else`는 예외가 발생하지 않았을 때만 실행된다.

```python
def read_config(path: str) -> dict | None:
    try:
        f = open(path)
    except FileNotFoundError:
        return None
    else:
        # 파일 열기 성공한 경우만 진입
        with f:
            return json.load(f)
```

`else` 블록을 `try` 안에 넣는 것과 차이가 있다. `try` 안에 `json.load(f)`를 넣으면 `FileNotFoundError`와 `JSONDecodeError`를 같은 `except`로 잡는다. `else`에 넣으면 파일 열기 실패와 JSON 파싱 실패를 별도로 처리할 수 있다.

Python의 예외 계층은 `BaseException`에서 시작한다. `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`는 `BaseException`을 직접 상속하기 때문에 `except Exception`으로는 잡히지 않는다. bare `except:`를 쓰면 이것들까지 잡아버린다.

```python
# 위험한 패턴 — Ctrl+C로 종료가 안 됨
while True:
    try:
        process_batch()
    except:  # bare except
        logger.error("에러 발생")

# 올바른 패턴
while True:
    try:
        process_batch()
    except Exception as e:
        logger.error("에러 발생: %s", e)
```

커스텀 예외는 도메인별로 계층을 만든다. 라이브러리를 만든다면 루트 예외 클래스를 하나 두고 나머지는 거기서 상속받는다. 사용자가 `except MyLibraryError`로 라이브러리 전체 에러를 한 번에 잡을 수 있어야 한다.

```python
class AppError(Exception):
    """애플리케이션 루트 예외"""

class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: int):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} {resource_id} 없음")

class ValidationError(AppError):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")
```

예외 체이닝은 `raise X from Y` 문법으로 한다. 원인 예외를 보존해서 스택 트레이스를 이어준다.

```python
def find_user(user_id: int) -> User:
    try:
        return db.query(User).filter_by(id=user_id).one()
    except NoResultFound as e:
        raise NotFoundError("User", user_id) from e
```

`raise X from None`은 원인 예외를 의도적으로 숨길 때 쓴다. 내부 구현 세부사항을 감출 때 유용하지만, 과도하게 쓰면 디버깅이 어려워진다.

asyncio에서 Task 예외가 조용히 사라지는 경우가 있다. `asyncio.create_task()`로 생성한 태스크가 예외로 종료돼도, 그 태스크를 `await`하거나 직접 확인하지 않으면 예외가 없어진다. Python 3.11부터는 GC가 처리되지 않은 태스크 예외를 감지하면 경고를 낸다.

```python
# 예외가 사라지는 패턴
async def bad():
    asyncio.create_task(risky_operation())  # await 없음, 실패해도 아무도 모름

# 올바른 패턴
async def good():
    task = asyncio.create_task(risky_operation())
    try:
        await task
    except Exception as e:
        logger.error("태스크 실패: %s", e)
```

Python 3.11부터는 `ExceptionGroup`과 `except*` 문법이 추가됐다. `asyncio.TaskGroup`을 쓰면 여러 태스크가 동시에 실패했을 때 모든 예외를 `ExceptionGroup`으로 받는다.

```python
# Python 3.11+
async def fetch_all():
    try:
        async with asyncio.TaskGroup() as tg:
            user_task = tg.create_task(fetch_user())
            order_task = tg.create_task(fetch_orders())
    except* NetworkError as eg:
        for exc in eg.exceptions:
            logger.error("네트워크 에러: %s", exc)
```

## JavaScript/TypeScript: try-catch와 비동기 에러

JavaScript의 에러 처리는 동기와 비동기 두 세계로 나뉜다. 동기 코드는 `try-catch`, 비동기 코드는 Promise의 `.catch()` 또는 `async/await` + `try-catch`다.

```javascript
// 동기 코드
function parseJSON(str) {
    try {
        return JSON.parse(str);
    } catch (e) {
        console.error("JSON 파싱 실패:", e.message);
        return null;
    }
}

// 비동기 코드
async function fetchUser(id) {
    try {
        const response = await fetch(`/api/users/${id}`);
        if (!response.ok) {
            throw new Error(`HTTP 에러: ${response.status}`);
        }
        return await response.json();
    } catch (e) {
        console.error("유저 조회 실패:", e);
        throw e;
    }
}
```

JavaScript의 에러는 어느 타입이든 던질 수 있다(`throw "string"`, `throw 42`도 가능). 실무에서는 `Error` 클래스나 이를 상속한 커스텀 에러를 쓴다. TypeScript에서 `catch (e)`의 `e`는 `unknown` 타입이라 타입 좁히기가 필요하다.

```typescript
class NotFoundError extends Error {
    constructor(
        message: string,
        public readonly resourceId: number
    ) {
        super(message);
        this.name = "NotFoundError";
        // V8 엔진 스택 트레이스 정상화
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, NotFoundError);
        }
    }
}

// TypeScript에서 catch 블록 타입 처리
try {
    const user = await findUser(42);
} catch (e) {
    if (e instanceof NotFoundError) {
        // 404 처리
    } else if (e instanceof Error) {
        console.error(e.message);
    }
}
```

### unhandledRejection

Promise가 reject됐는데 아무도 처리하지 않으면 `unhandledRejection` 이벤트가 발생한다. Node.js 15+에서는 이 이벤트가 기본으로 프로세스를 종료시킨다. 브라우저에서는 콘솔 경고로 끝나지만 에러가 무음 처리된다.

```javascript
// Node.js
process.on('unhandledRejection', (reason, promise) => {
    logger.error('처리되지 않은 Promise 거부:', reason);
    // 대부분의 경우 프로세스를 종료하는 것이 안전하다
    process.exit(1);
});

// 브라우저
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled Promise rejection:', event.reason);
    event.preventDefault(); // 브라우저 기본 콘솔 에러 막기
});
```

`unhandledRejection`이 발동됐다는 것 자체가 버그다. 이걸 잡는 것으로 해결된 게 아니라, 에러가 새어나간 위치를 찾아야 한다.

가장 흔한 실수는 `await` 없이 async 함수를 호출하는 것이다.

```javascript
// 에러가 사라지는 패턴
async function processItems(items) {
    items.forEach(item => {
        processItem(item); // async 함수인데 await 없음
    });
}

// 올바른 패턴
async function processItems(items) {
    await Promise.all(items.map(item => processItem(item)));
}
```

Express.js에서도 이 패턴이 자주 나온다. async 핸들러에서 에러가 발생하면 `next(err)`로 넘겨야 Express 에러 미들웨어가 받는다. Express 5부터는 async 핸들러 에러가 자동으로 전달되지만, Express 4 기반 프로젝트가 아직 많다.

```javascript
// Express 4에서 잘못된 패턴 — 에러가 Express 에러 핸들러로 안 감
app.get('/users/:id', async (req, res, next) => {
    const user = await findUser(req.params.id);
    res.json(user);
});

// 올바른 패턴
app.get('/users/:id', async (req, res, next) => {
    try {
        const user = await findUser(req.params.id);
        res.json(user);
    } catch (e) {
        next(e);
    }
});

// 래퍼로 반복 제거
const asyncHandler = fn => (req, res, next) =>
    Promise.resolve(fn(req, res, next)).catch(next);

app.get('/users/:id', asyncHandler(async (req, res) => {
    const user = await findUser(req.params.id);
    res.json(user);
}));
```

### AbortController

타임아웃이나 사용자 취소가 필요한 비동기 작업에서는 `AbortController`를 쓴다. `fetch()`는 `AbortSignal`을 기본 지원한다.

```javascript
async function fetchWithTimeout(url, timeoutMs = 5000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        return await response.json();
    } catch (e) {
        if (e.name === 'AbortError') {
            throw new Error(`요청 타임아웃: ${url}`);
        }
        throw e;
    }
}
```

React에서 컴포넌트 언마운트 시 진행 중인 요청을 취소하는 패턴이다.

```javascript
useEffect(() => {
    const controller = new AbortController();

    fetchUser(userId, controller.signal)
        .then(setUser)
        .catch(e => {
            if (e.name !== 'AbortError') {
                setError(e);
            }
        });

    return () => controller.abort();
}, [userId]);
```

### async 이터레이터 에러

async generator에서 에러가 나면 `for await...of` 루프 바깥의 `try-catch`로 잡는다. 루프를 `break`로 빠져나가거나 에러가 발생하면 제너레이터의 `finally` 블록이 실행된다.

```javascript
async function* streamData(url) {
    const response = await fetch(url);
    const reader = response.body.getReader();

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            yield value;
        }
    } finally {
        reader.releaseLock(); // 루프 중단 시에도 정리됨
    }
}

async function processStream(url) {
    try {
        for await (const chunk of streamData(url)) {
            process(chunk);
        }
    } catch (e) {
        console.error("스트림 처리 실패:", e);
    }
}
```

`Promise.all`은 하나라도 reject되면 즉시 reject되고 나머지는 무시한다. 모든 결과가 필요할 때는 `Promise.allSettled`를 쓴다.

```javascript
// 하나 실패하면 전체 실패
const results = await Promise.all([
    fetchUser(1),
    fetchUser(2),
    fetchUser(3),
]);

// 실패한 것과 성공한 것 분리
const settled = await Promise.allSettled([
    fetchUser(1),
    fetchUser(2),
    fetchUser(3),
]);

const succeeded = settled
    .filter(r => r.status === 'fulfilled')
    .map(r => r.value);
const failed = settled
    .filter(r => r.status === 'rejected')
    .map(r => r.reason);
```

Worker Threads를 쓰는 경우 에러 객체가 경계를 넘으면 프로토타입 체인이 사라진다. `instanceof NotFoundError`로 타입을 확인할 수 없게 되므로, 에러 `name` 프로퍼티나 별도 코드 필드로 식별해야 한다.

## 컴파일 타임 vs 런타임 에러 보장

언어마다 에러 처리 강제 시점이 다르다. 이 차이가 시스템 안정성 요구사항에 따른 언어 선택 기준이 된다.

Rust는 `Result`를 반환하는 함수를 호출하고 결과를 아무것도 안 하면 컴파일러가 경고를 낸다. `#[must_use]` 속성이 붙은 타입을 사용하지 않으면 경고다.

```rust
fn main() {
    std::fs::remove_file("temp.txt"); // warning: unused `Result` that must be used
    let _ = std::fs::remove_file("temp.txt"); // 명시적 무시
}
```

Java의 체크드 예외는 컴파일 타임에 처리를 강제한다. 하지만 `throws Exception`으로 선언하거나 체크드 예외를 언체크드로 감싸면 런타임으로 밀려난다. Spring 생태계에서는 체크드 예외가 거의 쓰이지 않는 이유가 이것이다.

Go는 컴파일 타임 강제가 없다. `err`를 `_`로 무시해도 컴파일된다. `errcheck`나 `golangci-lint` 설정으로 보완하는 팀이 많다.

Python과 JavaScript는 완전히 런타임이다. 타입 힌트(Python mypy)나 TypeScript를 써도 에러 처리 누락 자체를 컴파일 타임에 잡지는 못한다. `pylint`나 `eslint` 규칙으로 일부 패턴을 감지할 수 있지만 완벽하지 않다.

결제 시스템이나 인프라 도구에서 Rust를 선택하는 이유 중 하나가 바로 컴파일 타임 에러 처리 보장이다. 빠른 개발 속도가 중요하고 테스트로 런타임 에러를 커버할 수 있다면 Python이나 JavaScript도 충분하다.

## 에러 계층 설계: 라이브러리와 애플리케이션의 차이

라이브러리와 애플리케이션은 에러를 다루는 방식이 달라야 한다.

라이브러리는 구체적인 에러 타입을 노출해야 한다. 사용자가 특정 에러를 잡아서 복구할 수 있도록 타입이 충분히 세분화돼야 한다. 내부에서 예외를 너무 일찍 잡으면 사용자가 에러 원인을 파악할 수 없다.

```python
# 나쁜 라이브러리 설계 — 에러 정보가 사라짐
class MyHttpClient:
    def get(self, url: str):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError("요청 실패") from None  # 원인 없앰

# 좋은 라이브러리 설계
class MyClientError(Exception):
    """라이브러리 루트 예외"""

class ConnectionTimeoutError(MyClientError):
    def __init__(self, url: str, timeout: float):
        self.url = url
        self.timeout = timeout
        super().__init__(f"{url} 연결 타임아웃 ({timeout}s)")

class HttpError(MyClientError):
    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code}: {url}")

class MyHttpClient:
    def get(self, url: str):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            raise ConnectionTimeoutError(url, 5) from None
        except requests.HTTPError as e:
            raise HttpError(e.response.status_code, url) from e
```

애플리케이션은 에러를 최종적으로 처리하는 층이다. 도메인 에러를 HTTP 상태 코드나 사용자 메시지로 변환하고, 로깅하고, 모니터링 시스템에 알린다.

```python
# FastAPI에서 전역 예외 핸들러
@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": str(exc), "resource": exc.resource}
    )

@app.exception_handler(ValidationError)
async def validation_handler(request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": exc.message, "field": exc.field}
    )

@app.exception_handler(Exception)
async def unhandled_handler(request, exc: Exception):
    logger.exception("처리되지 않은 예외")
    return JSONResponse(status_code=500, content={"error": "서버 에러"})
```

Go에서는 에러 래핑으로 라이브러리 레이어와 애플리케이션 레이어의 경계를 구분한다.

```go
// 라이브러리 레이어 — 도메인 에러 정의
var ErrUserNotFound = errors.New("user not found")

func (r *UserRepo) FindByID(ctx context.Context, id int) (*User, error) {
    row := r.db.QueryRowContext(ctx, "SELECT * FROM users WHERE id = ?", id)
    var user User
    if err := row.Scan(&user.ID, &user.Name); err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, fmt.Errorf("user %d: %w", id, ErrUserNotFound)
        }
        return nil, fmt.Errorf("db query: %w", err)
    }
    return &user, nil
}

// 애플리케이션 레이어 — HTTP 응답으로 변환
func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    id := parseID(r)
    user, err := h.repo.FindByID(r.Context(), id)
    if err != nil {
        if errors.Is(err, ErrUserNotFound) {
            http.Error(w, "not found", http.StatusNotFound)
            return
        }
        log.Printf("unexpected error: %v", err)
        http.Error(w, "internal server error", http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(user)
}
```

Rust에서 라이브러리는 `thiserror`로 구체적인 에러 타입을 정의하고, 애플리케이션은 `anyhow`로 여러 에러 타입을 통합해 처리한다.

```rust
// 라이브러리 크레이트 — thiserror로 공개 에러 정의
#[derive(Error, Debug)]
pub enum UserError {
    #[error("user {0} not found")]
    NotFound(i64),
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),
}

// 애플리케이션 크레이트 — anyhow로 다양한 에러 통합
use anyhow::{Context, Result};

async fn handle_get_user(id: i64) -> Result<User> {
    let user = user_repo::find_by_id(id)
        .await
        .with_context(|| format!("failed to fetch user {}", id))?;
    Ok(user)
}
```

## 언어별 접근법 비교

| 항목 | Java | Go | Rust | Python | JavaScript |
|---|---|---|---|---|---|
| 에러 표현 방식 | 예외 객체 | 반환값 | `Result<T, E>` | 예외 객체 | 예외 객체 |
| 컴파일 타임 보장 | 체크드 예외만 | 없음 | 완전 보장 | 없음 | 없음 |
| 에러 전파 | `throws`, 재던지기 | `return err` | `?` 연산자 | `raise` | `throw`, `reject` |
| 비동기 에러 | CompletableFuture | goroutine + channel | `async fn` + `Result` | asyncio Task | Promise `.catch()` |
| 에러 무시 방법 | 빈 catch 블록 | `_ =` 할당 | `let _ =` | pass in except | 아무것도 안 함 |
| 에러 체이닝 | `initCause()` | `%w` 래핑 | `#[from]`, `?` | `raise X from Y` | `cause` 프로퍼티 |
| 커스텀 에러 | `extends Exception` | sentinel 변수, 구조체 | `thiserror` | `class X(Exception)` | `extends Error` |
| 미처리 감지 | 컴파일러(체크드) | 정적 분석 필요 | 컴파일러 경고 | 런타임 | `unhandledRejection` |
| 주요 안티패턴 | 빈 catch 블록 | err 무시 | `unwrap()` 남발 | bare `except:` | await 누락 |
| 라이브러리 관례 | 언체크드로 래핑 | 도메인 에러 변수 | `thiserror` 공개 | 루트 예외 클래스 | `Error` 서브클래스 |

언어 선택이 이미 결정됐다면 에러 처리 방식은 그 언어의 관례를 따르는 것이 맞다. Go 코드에 Java식 예외를 모방하거나, Rust에서 `unwrap()`을 남발하면 그 언어가 주는 안전성 보장을 전혀 활용하지 못한다.

Java는 체크드 예외로 처리를 강제하려 했지만 생태계 자체가 언체크드 방향으로 굳어졌다. Python은 EAFP 덕에 에러 처리가 코드 흐름에 자연스럽게 녹아들지만, asyncio에서 Task 예외를 잃어버리는 함정이 있다. JavaScript는 구조 자체는 단순하지만 `await` 하나를 빠뜨리면 에러가 사라진다. 각 언어에서 가장 자주 나오는 버그 패턴을 파악하고 있으면 코드 리뷰에서 금방 눈에 띈다.
