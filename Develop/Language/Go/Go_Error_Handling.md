---
title: Go 에러 처리
tags: [Go, Error, errors.Is, errors.As, panic, wrapping]
updated: 2026-07-08
---

# Go 에러 처리

Go의 에러 처리는 예외(exception) 없이 반환값으로만 에러를 전달한다. 단순해 보이지만 실무에서 제대로 쓰지 않으면 에러가 어디서 발생했는지 추적하기 어렵고, 호출자가 에러를 판별하지 못해 잘못된 분기를 타는 경우가 생�다.

## errors.Is / errors.As

### errors.Is

`errors.Is`는 에러 체인을 따라가며 대상 에러와 일치하는지 확인한다.

```go
var ErrNotFound = errors.New("not found")

func findUser(id int) error {
    return fmt.Errorf("findUser: %w", ErrNotFound)
}

err := findUser(42)
if errors.Is(err, ErrNotFound) {
    // wrapping 되어 있어도 감지된다
}
```

`==` 비교는 wrapping된 에러에서 동작하지 않는다. Go 1.13 이전 코드를 마이그레이션할 때 `==`로 sentinel 에러를 비교하는 곳을 놓치면 조용히 버그가 생긴다.

### errors.As

에러 체인에서 특정 타입을 꺼낼 때 쓴다.

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

func validate(name string) error {
    if name == "" {
        return fmt.Errorf("validate: %w", &ValidationError{
            Field:   "name",
            Message: "must not be empty",
        })
    }
    return nil
}

err := validate("")
var ve *ValidationError
if errors.As(err, &ve) {
    fmt.Println(ve.Field)   // "name"
    fmt.Println(ve.Message) // "must not be empty"
}
```

`errors.As`에 포인터의 포인터를 넘겨야 한다는 점을 자주 틀린다. `errors.As(err, ve)` 처럼 쓰면 컴파일은 되지만 패닉이 난다.

## fmt.Errorf %w로 에러 wrapping

`%w`는 에러를 wrapping해서 체인에 원본 에러를 보존한다.

```go
func getConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("getConfig: %w", err)
    }
    // ...
}

func loadApp(configPath string) error {
    cfg, err := getConfig(configPath)
    if err != nil {
        return fmt.Errorf("loadApp: %w", err)
    }
    // ...
    return nil
}
```

에러 메시지에 함수명을 prefix로 붙이면 스택 없이도 콜 체인을 추적할 수 있다. `loadApp: getConfig: open /etc/app.conf: no such file or directory` 형태로 출력된다.

`%v`를 쓰면 wrapping이 안 된다. `errors.Is`나 `errors.As`로 원본 에러를 꺼낼 수 없게 된다. 호출자가 특정 에러 타입을 분기해야 할 때 문제가 생긴다.

## Sentinel Error vs Custom Error Type

### Sentinel Error

패키지 수준에서 미리 정의해두는 에러 값이다.

```go
package store

var (
    ErrNotFound   = errors.New("not found")
    ErrDuplicate  = errors.New("duplicate entry")
    ErrPermission = errors.New("permission denied")
)

func (s *Store) Get(key string) ([]byte, error) {
    val, ok := s.data[key]
    if !ok {
        return nil, ErrNotFound
    }
    return val, nil
}
```

호출자가 `errors.Is(err, store.ErrNotFound)` 로 간단히 분기할 수 있다. 에러에 추가 정보가 필요 없을 때 적합하다.

sentinel 에러를 `var`가 아닌 `const`로 정의하고 싶을 때가 있는데, `errors.New` 반환값은 인터페이스라 `const`로 선언이 안 된다. 외부 패키지에서 같은 이름의 sentinel을 재정의해서 `errors.Is` 비교를 우회하는 공격은 드물지만 보안 민감한 코드에선 신경 써야 한다.

### Custom Error Type

에러에 추가 정보를 담아야 할 때 구조체로 정의한다.

```go
type DBError struct {
    Op    string
    Query string
    Err   error
}

func (e *DBError) Error() string {
    return fmt.Sprintf("db %s [%s]: %v", e.Op, e.Query, e.Err)
}

func (e *DBError) Unwrap() error {
    return e.Err
}

func (db *DB) Query(q string) ([]Row, error) {
    rows, err := db.conn.Query(q)
    if err != nil {
        return nil, &DBError{Op: "Query", Query: q, Err: err}
    }
    return rows, nil
}
```

`Unwrap()` 메서드를 구현하면 `errors.Is`, `errors.As`가 체인을 타고 내려갈 수 있다. 빠뜨리면 wrapping한 에러를 꺼낼 수 없다.

sentinel과 custom type을 같이 쓸 수도 있다.

```go
type NotFoundError struct {
    Resource string
    ID       int
}

func (e *NotFoundError) Error() string {
    return fmt.Sprintf("%s with id %d not found", e.Resource, e.ID)
}

func (e *NotFoundError) Is(target error) bool {
    _, ok := target.(*NotFoundError)
    return ok
}
```

`Is` 메서드를 정의하면 `errors.Is`가 타입 수준 비교를 한다. 특정 ID를 신경 쓰지 않고 NotFoundError인지만 확인하고 싶을 때 유용하다.

## 에러 컨텍스트 전파

에러가 여러 레이어를 거칠 때 각 레이어에서 컨텍스트를 붙여나가야 한다.

```go
func (s *UserService) CreateUser(ctx context.Context, req CreateUserRequest) (*User, error) {
    if err := s.validate(req); err != nil {
        return nil, fmt.Errorf("CreateUser: %w", err)
    }

    user, err := s.repo.Save(ctx, req)
    if err != nil {
        return nil, fmt.Errorf("CreateUser: %w", err)
    }

    return user, nil
}

func (r *UserRepository) Save(ctx context.Context, req CreateUserRequest) (*User, error) {
    result, err := r.db.ExecContext(ctx, insertQuery, req.Name, req.Email)
    if err != nil {
        return nil, fmt.Errorf("UserRepository.Save: %w", err)
    }
    // ...
}
```

에러 메시지를 쌓아가면 최종적으로 `CreateUser: UserRepository.Save: pq: duplicate key value violates unique constraint "users_email_key"` 같은 메시지가 나온다. 스택 트레이스 없이도 경로를 파악할 수 있다.

주의할 점은 에러를 로깅하는 위치다. 에러를 wrapping해서 위로 올릴 때마다 로그를 남기면 같은 에러가 여러 번 기록된다. 에러는 한 곳에서만 로깅하고, 중간 레이어는 wrapping해서 반환만 한다.

```go
// 잘못된 패턴 - 중간 레이어에서 로그
func (s *UserService) CreateUser(ctx context.Context, req CreateUserRequest) (*User, error) {
    user, err := s.repo.Save(ctx, req)
    if err != nil {
        log.Printf("repo.Save failed: %v", err)  // 여기서도 찍고
        return nil, fmt.Errorf("CreateUser: %w", err)
    }
    return user, nil
}

// HTTP 핸들러에서도 로그 - 같은 에러가 두 번 찍힌다
func (h *Handler) createUser(w http.ResponseWriter, r *http.Request) {
    user, err := h.service.CreateUser(r.Context(), req)
    if err != nil {
        log.Printf("CreateUser failed: %v", err)  // 두 번째 로그
        http.Error(w, "internal error", 500)
    }
}
```

에러 로깅은 최상위 핸들러나 미들웨어에서 한 번만 한다.

## panic을 써야 하는 경우와 쓰면 안 되는 경우

### panic을 써도 되는 경우

프로그램이 더 이상 실행될 수 없는 상태, 즉 프로그래머 실수로 인한 불변식 위반에 쓴다.

```go
func NewServer(cfg *Config) *Server {
    if cfg == nil {
        panic("NewServer: cfg must not be nil")
    }
    // ...
}
```

`nil` config로 서버를 만들면 어차피 나중에 더 이상한 곳에서 터진다. 초기화 시점에 빠르게 실패하는 게 낫다.

패키지 초기화 때 정규식 컴파일이나 템플릿 파싱에도 관용적으로 쓴다.

```go
var emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`)
```

`MustCompile`은 내부에서 컴파일 실패 시 panic을 일으킨다. 패턴이 리터럴이라면 런타임 에러가 아니라 배포 전에 발견해야 할 버그이므로 panic이 맞다.

### panic을 쓰면 안 되는 경우

외부 입력이나 런타임 상황에 따라 발생할 수 있는 에러는 panic을 쓰면 안 된다.

```go
// 잘못된 패턴
func ParseConfig(data []byte) *Config {
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        panic(err)  // 외부 데이터 파싱 실패에 panic
    }
    return &cfg
}

// 올바른 패턴
func ParseConfig(data []byte) (*Config, error) {
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("ParseConfig: %w", err)
    }
    return &cfg, nil
}
```

라이브러리 코드에서 panic을 쓰면 사용자 코드가 recover를 직접 감싸야 한다. 라이브러리는 에러를 반환하고 panic은 쓰지 않는 게 원칙이다.

HTTP 핸들러처럼 goroutine 경계에서는 recover로 panic을 잡아야 한다. goroutine 하나가 panic으로 죽으면 전체 프로세스가 죽는다.

```go
func safeHandler(h http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                log.Printf("panic recovered: %v\n%s", rec, debug.Stack())
                http.Error(w, "internal server error", http.StatusInternalServerError)
            }
        }()
        h(w, r)
    }
}
```

미들웨어에서 한 번 감싸두면 개별 핸들러에서 신경 쓰지 않아도 된다.

## 에러 타입 선택 기준

호출자가 에러 종류를 분기할 필요가 없다면 `fmt.Errorf`로 메시지만 붙여서 반환한다. 호출자가 특정 에러를 구분해서 다르게 처리해야 한다면 sentinel 에러나 custom type을 쓴다. 에러에 추가 데이터(필드명, 쿼리, ID 등)가 필요하면 custom type이 맞다.

패키지 외부에 공개하는 에러는 문서화해야 한다. 내부 구현 에러를 그대로 노출하면 나중에 구현을 바꿀 때 호출자 코드가 깨진다.
