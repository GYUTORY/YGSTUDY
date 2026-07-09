---
title: 언어별 에러 처리 방식 비교
tags: [Java, Go, Rust, JavaScript, Error Handling, Exception, Result]
updated: 2026-07-09
---

# 언어별 에러 처리 방식 비교

에러 처리는 언어 설계 철학이 가장 직접적으로 드러나는 부분이다. Java는 예외를 타입 시스템으로 강제하고, Go는 값으로 돌려주고, Rust는 컴파일러가 처리 여부를 확인하고, JavaScript는 예외를 던지되 처리는 개발자 몫이다. 같은 기능을 구현해도 언어마다 코드 모양이 완전히 달라지는 이유가 여기 있다.

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
        // 에러 처리
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

체크드 예외는 좋은 의도로 설계됐지만 실무에서 골칫거리가 많다. 라이브러리 하나를 잘못 선택하면 예외 선언이 호출 스택을 타고 올라가며 `throws Exception`으로 퇴화하는 경우가 흔하다. 이 때문에 Spring, Hibernate 같은 프레임워크들은 체크드 예외를 언체크드로 감싸서 돌려주는 패턴을 사용한다.

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

## JavaScript/TypeScript: try-catch와 Promise

JavaScript의 에러 처리는 두 가지 세계로 나뉜다. 동기 코드는 `try-catch`, 비동기 코드는 Promise의 `.catch()` 또는 `async/await` + `try-catch`다.

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
        throw e; // 다시 던지거나 처리
    }
}
```

JavaScript의 에러는 어느 타입이든 던질 수 있다(`throw "string"`, `throw 42`도 가능). 실무에서는 `Error` 클래스나 이를 상속한 커스텀 에러를 쓴다. TypeScript에서 `catch (e)`의 `e`는 `unknown` 타입이라 타입 좁히기가 필요하다.

```typescript
class NotFoundError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "NotFoundError";
    }
}

async function findUser(id: number): Promise<User> {
    const user = await db.users.findOne(id);
    if (!user) {
        throw new NotFoundError(`유저 ${id} 없음`);
    }
    return user;
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

JavaScript에서 가장 많이 실수하는 부분은 비동기 에러를 놓치는 것이다. `async` 함수 내에서 던진 에러는 반환된 Promise를 거부(reject)하는데, 이걸 처리하지 않으면 조용히 사라진다. Node.js에서는 `unhandledRejection` 이벤트로 잡아낼 수 있지만, 그게 발동된다는 건 이미 에러가 새어나간 것이다.

```javascript
// 잘못된 패턴 — Promise 에러를 놓침
async function badPattern() {
    fetchUser(42); // await 없음, 에러 무시됨
}

// 올바른 패턴
async function goodPattern() {
    try {
        await fetchUser(42);
    } catch (e) {
        // 처리
    }
}
```

## 언어별 접근법 비교

| 항목 | Java | Go | Rust | JavaScript |
|---|---|---|---|---|
| 에러 표현 방식 | 예외 객체 | 반환값 | `Result<T, E>` | 예외 객체 |
| 강제 처리 여부 | 체크드 예외만 강제 | 강제 안 함 | 컴파일러가 경고 | 강제 안 함 |
| 에러 전파 | `throws`, 재던지기 | `return err` | `?` 연산자 | `throw`, `reject` |
| 비동기 에러 | Future/CompletableFuture | goroutine + channel | `async fn` + `Result` | Promise `.catch()` |
| 에러 무시 | 빈 catch 블록 | `_` 할당 | `let _ =`, `unwrap()` | 아무것도 안 함 |

Java의 체크드 예외는 의도는 좋지만 보일러플레이트가 많다. Go는 에러를 코드 흐름에서 눈에 보이게 만들되, 실제 처리를 강제하지는 않는다. Rust는 타입 시스템으로 처리 여부를 컴파일 타임에 보장한다. JavaScript는 던지고 잡는 구조 자체는 단순하지만, 비동기에서 빠뜨리기 쉽다.

어느 방식이 낫다는 것보다, 각 언어의 에러 처리 방식을 이해하고 그 언어의 관례를 따르는 것이 중요하다. Go 코드에 Java식으로 예외를 모방하거나, Rust에서 `unwrap()`을 남발하면 그 언어의 에러 처리 모델이 주는 이점을 전혀 못 가져간다.
