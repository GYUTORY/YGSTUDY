---
title: Go 테스트
tags: [go, testing, language]
updated: 2026-07-10
---

# Go 테스트

Go의 테스트는 표준 라이브러리 `testing` 패키지만으로 웬만한 걸 다 처리할 수 있다. testify 같은 외부 라이브러리 없이도 충분히 쓸만하다. 파일명은 `_test.go`로 끝나야 하고, 함수 시그니처는 `func TestXxx(t *testing.T)`여야 한다.

```bash
go test ./...
go test -v ./...          # 각 테스트 이름과 결과 출력
go test -run TestFoo ./...  # 특정 테스트만 실행
```

## testing.T 기본

`t.Error`와 `t.Fatal`의 차이를 먼저 구분해야 한다. `t.Error`는 실패를 기록하고 테스트를 계속 진행한다. `t.Fatal`은 실패를 기록하고 즉시 해당 테스트 함수를 종료한다.

```go
func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d, want 5", result)
    }
}
```

`t.Errorf`는 `t.Error` + 포맷팅이다. `t.Fatalf`도 마찬가지다.

DB 연결이나 임시 디렉터리처럼 정리가 필요한 리소스는 `t.Cleanup`을 쓴다. `defer`보다 `t.Cleanup`이 나은 이유는, 서브테스트(`t.Run`)에서도 상위 테스트의 정리 로직이 제대로 실행된다는 점이다.

```go
func TestWithDB(t *testing.T) {
    db := openTestDB(t)
    t.Cleanup(func() {
        db.Close()
    })
    // 테스트 로직
}
```

`t.Helper()`는 헬퍼 함수 안에서 호출하면, 실패 시 헬퍼 함수 라인이 아닌 호출자 라인을 가리킨다. 없으면 에러가 헬퍼 내부를 가리켜서 디버깅이 힘들다.

```go
func assertEqual(t *testing.T, got, want int) {
    t.Helper()
    if got != want {
        t.Errorf("got %d, want %d", got, want)
    }
}
```

## testify 없이 assertion

testify를 쓰면 편하지만, 의존성이 늘어난다. 표준 라이브러리만으로도 충분한 경우가 많다.

기본 비교는 그냥 `==`로 처리한다. 슬라이스나 맵은 `reflect.DeepEqual`을 쓴다.

```go
import "reflect"

func TestSlice(t *testing.T) {
    got := processItems([]int{1, 2, 3})
    want := []int{2, 4, 6}
    if !reflect.DeepEqual(got, want) {
        t.Errorf("got %v, want %v", got, want)
    }
}
```

에러 타입을 검사할 때는 `errors.Is`나 `errors.As`를 쓴다.

```go
func TestError(t *testing.T) {
    _, err := findUser(-1)
    if !errors.Is(err, ErrNotFound) {
        t.Errorf("expected ErrNotFound, got %v", err)
    }
}
```

에러가 nil인지 확인할 때는 `if err != nil`로 충분하다. testify의 `assert.NoError`가 하는 일이 그게 전부다.

```go
result, err := doSomething()
if err != nil {
    t.Fatalf("unexpected error: %v", err)
}
```

## Table-driven test

여러 입력 케이스를 테스트할 때 사용하는 패턴이다. Go 커뮤니티에서 사실상 표준으로 쓰인다.

```go
func TestDivide(t *testing.T) {
    tests := []struct {
        name    string
        a, b    float64
        want    float64
        wantErr bool
    }{
        {"normal", 10, 2, 5, false},
        {"zero divisor", 10, 0, 0, true},
        {"negative", -6, 2, -3, false},
    }

    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got, err := Divide(tc.a, tc.b)
            if (err != nil) != tc.wantErr {
                t.Fatalf("Divide() error = %v, wantErr %v", err, tc.wantErr)
            }
            if !tc.wantErr && got != tc.want {
                t.Errorf("Divide() = %v, want %v", got, tc.want)
            }
        })
    }
}
```

`t.Run`으로 서브테스트를 만들면 개별 케이스만 실행할 수 있다.

```bash
go test -run TestDivide/zero_divisor ./...
```

케이스 이름의 공백은 자동으로 `_`로 변환된다.

구조체 필드에 `name`을 넣는 게 귀찮다면 그냥 생략해도 되지만, 실패 시 어떤 케이스가 실패했는지 바로 알 수 없어서 디버깅이 힘들어진다. `name` 필드는 넣는 게 낫다.

## Mock 패턴

Go에서 mock을 만드는 방법은 크게 세 가지다. 인터페이스 기반 수동 mock, `gomock`, `testify/mock`이다.

### 인터페이스 기반 수동 mock

가장 단순한 방법이다. 인터페이스만 잘 설계하면 외부 라이브러리 없이도 mock을 만들 수 있다.

```go
// 실제 코드
type UserRepository interface {
    FindByID(ctx context.Context, id int64) (*User, error)
    Save(ctx context.Context, user *User) error
}

type UserService struct {
    repo UserRepository
}

func (s *UserService) GetUser(ctx context.Context, id int64) (*User, error) {
    return s.repo.FindByID(ctx, id)
}
```

```go
// 테스트용 mock
type mockUserRepo struct {
    findByIDFn func(ctx context.Context, id int64) (*User, error)
    saveFn     func(ctx context.Context, user *User) error
}

func (m *mockUserRepo) FindByID(ctx context.Context, id int64) (*User, error) {
    return m.findByIDFn(ctx, id)
}

func (m *mockUserRepo) Save(ctx context.Context, user *User) error {
    return m.saveFn(ctx, user)
}

func TestGetUser(t *testing.T) {
    repo := &mockUserRepo{
        findByIDFn: func(ctx context.Context, id int64) (*User, error) {
            if id == 1 {
                return &User{ID: 1, Name: "alice"}, nil
            }
            return nil, ErrNotFound
        },
    }

    svc := &UserService{repo: repo}
    user, err := svc.GetUser(context.Background(), 1)
    if err != nil {
        t.Fatalf("GetUser() error: %v", err)
    }
    if user.Name != "alice" {
        t.Errorf("Name = %s, want alice", user.Name)
    }
}
```

이 방식은 코드가 좀 길어지지만, mock이 어떻게 동작하는지 명확히 보인다. 팀에 Go가 익숙하지 않은 사람이 있을 때 오히려 이 방식이 낫다.

### gomock

`go.uber.org/mock` (구 `golang/mock`)을 쓰면 인터페이스에서 mock을 자동 생성한다. 호출 횟수나 순서까지 검증해야 할 때 쓴다.

```bash
go install go.uber.org/mock/mockgen@latest
mockgen -source=repository.go -destination=mocks/mock_repository.go -package=mocks
```

```go
func TestGetUser_WithGomock(t *testing.T) {
    ctrl := gomock.NewController(t)
    // ctrl.Finish()는 Go 1.14+ 에서 t.Cleanup으로 자동 등록됨

    mockRepo := mocks.NewMockUserRepository(ctrl)
    mockRepo.EXPECT().
        FindByID(gomock.Any(), int64(1)).
        Return(&User{ID: 1, Name: "alice"}, nil).
        Times(1)

    svc := &UserService{repo: mockRepo}
    user, err := svc.GetUser(context.Background(), 1)
    if err != nil {
        t.Fatalf("GetUser() error: %v", err)
    }
    if user.Name != "alice" {
        t.Errorf("Name = %s, want alice", user.Name)
    }
}
```

`EXPECT().Times(1)`처럼 호출 횟수를 강제할 수 있다. 캐시 구현 테스트처럼 "DB는 딱 한 번만 호출해야 한다"는 걸 검증할 때 유용하다.

### testify/mock

`github.com/stretchr/testify/mock`은 `gomock`보다 설정이 덜 엄격하다. 호출 횟수 검증보다 반환값 설정에 집중할 때 쓰기 좋다.

```go
type MockUserRepo struct {
    mock.Mock
}

func (m *MockUserRepo) FindByID(ctx context.Context, id int64) (*User, error) {
    args := m.Called(ctx, id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*User), args.Error(1)
}

func TestGetUser_WithTestify(t *testing.T) {
    mockRepo := new(MockUserRepo)
    mockRepo.On("FindByID", mock.Anything, int64(1)).
        Return(&User{ID: 1, Name: "alice"}, nil)

    svc := &UserService{repo: mockRepo}
    user, err := svc.GetUser(context.Background(), 1)
    if err != nil {
        t.Fatalf("GetUser() error: %v", err)
    }
    if user.Name != "alice" {
        t.Errorf("Name = %s, want alice", user.Name)
    }

    mockRepo.AssertExpectations(t)
}
```

`mock.Anything`은 해당 인자를 무시한다. context처럼 테스트마다 달라지는 인자에 쓴다.

### 언제 어떤 방식을 쓸까

수동 mock은 인터페이스 메서드가 5개 이하이고, 반환값만 제어하면 될 때 쓴다. gomock은 호출 순서나 횟수가 중요한 테스트에 쓴다. testify/mock은 팀이 이미 testify를 쓰고 있고, gomock 설정이 번거롭게 느껴질 때 쓴다.

인터페이스가 없는 외부 패키지를 mock해야 할 때는 wrapper를 만들어서 그 wrapper 인터페이스를 mock하는 방식을 쓴다. 직접 함수를 mock할 수 없으므로 인터페이스로 한 번 감싸는 게 기본 전제다.

## 단위 테스트 vs 통합 테스트 판단 기준

"모든 걸 단위 테스트로 짜야 한다"는 규칙은 없다. 실무에서는 상황에 따라 다르게 접근한다.

단위 테스트가 맞는 경우는 순수 로직이 있을 때다. 날짜 파싱, 금액 계산, 입력값 유효성 검사처럼 외부 의존성 없이 입력과 출력이 명확한 함수들이다. 이런 코드는 mock도 필요 없고, 빠르게 실행되고, 피드백도 즉각적이다.

통합 테스트가 맞는 경우는 DB 쿼리나 외부 API 호출이 실제로 올바르게 동작하는지 확인해야 할 때다. ORM이나 쿼리 빌더를 쓰더라도 실제 DB 스키마와 인덱스에서 쿼리가 의도대로 동작하는지는 mock으로 검증하기 어렵다. DB 인덱스 누락으로 쿼리가 잘못 실행되는 상황은 mock으로 잡을 수 없다.

```go
// Build tag로 통합 테스트 분리
//go:build integration

package repository_test

import (
    "testing"
)

func TestUserRepository_FindByID(t *testing.T) {
    // 실제 DB에 붙어서 테스트
}
```

```bash
go test -tags=integration ./...
```

build tag로 통합 테스트를 분리하면 기본 `go test ./...` 실행 시 빠른 단위 테스트만 돌고, CI 파이프라인에서는 `-tags=integration`을 붙여 전체를 돌리는 구조를 만들 수 있다.

서비스 레이어는 mock을 쓰는 단위 테스트로 충분한 경우가 많다. 하지만 트랜잭션 처리, 외래 키 제약 위반, DB 레벨 유니크 제약 같은 부분은 실제 DB 없이는 검증이 안 된다.

`t.Skip`으로 환경 변수가 없을 때 테스트를 건너뛰게 하면 로컬에서도 선택적으로 실행할 수 있다.

```go
func TestWithRealDB(t *testing.T) {
    dsn := os.Getenv("TEST_DB_DSN")
    if dsn == "" {
        t.Skip("TEST_DB_DSN not set")
    }
    // 실제 DB 테스트
}
```

## testcontainers

통합 테스트에서 실제 DB가 필요할 때 `testcontainers-go`를 쓰면 테스트 시작 시 Docker 컨테이너를 띄우고, 테스트가 끝나면 자동으로 정리한다. Docker가 설치된 환경이면 별도 인프라 세팅 없이 통합 테스트를 돌릴 수 있다.

```bash
go get github.com/testcontainers/testcontainers-go
go get github.com/testcontainers/testcontainers-go/modules/postgres
```

```go
//go:build integration

package repository_test

import (
    "context"
    "testing"

    "github.com/testcontainers/testcontainers-go/modules/postgres"
    "github.com/testcontainers/testcontainers-go/wait"
)

func TestUserRepository(t *testing.T) {
    ctx := context.Background()

    pgContainer, err := postgres.RunContainer(ctx,
        testcontainers.WithImage("postgres:15-alpine"),
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("user"),
        postgres.WithPassword("password"),
        testcontainers.WithWaitStrategy(
            wait.ForLog("database system is ready to accept connections").
                WithOccurrence(2),
        ),
    )
    if err != nil {
        t.Fatalf("failed to start postgres container: %v", err)
    }
    t.Cleanup(func() {
        if err := pgContainer.Terminate(ctx); err != nil {
            t.Logf("failed to terminate container: %v", err)
        }
    })

    connStr, err := pgContainer.ConnectionString(ctx, "sslmode=disable")
    if err != nil {
        t.Fatalf("failed to get connection string: %v", err)
    }

    db, err := sql.Open("postgres", connStr)
    if err != nil {
        t.Fatalf("failed to open db: %v", err)
    }
    t.Cleanup(func() { db.Close() })

    // 스키마 적용
    if _, err := db.ExecContext(ctx, schemaSQL); err != nil {
        t.Fatalf("failed to apply schema: %v", err)
    }

    repo := NewUserRepository(db)

    // 실제 테스트
    user := &User{Name: "alice", Email: "alice@example.com"}
    if err := repo.Save(ctx, user); err != nil {
        t.Fatalf("Save() error: %v", err)
    }

    found, err := repo.FindByID(ctx, user.ID)
    if err != nil {
        t.Fatalf("FindByID() error: %v", err)
    }
    if found.Name != "alice" {
        t.Errorf("Name = %s, want alice", found.Name)
    }
}
```

컨테이너 시작에 몇 초 걸리므로, 테스트마다 새 컨테이너를 띄우면 느리다. `TestMain`에서 컨테이너를 한 번 띄우고 패키지 내 모든 테스트가 공유하는 패턴을 쓰는 게 낫다.

```go
var testDB *sql.DB

func TestMain(m *testing.M) {
    ctx := context.Background()

    pgContainer, err := postgres.RunContainer(ctx, /* ... */)
    if err != nil {
        log.Fatalf("failed to start postgres: %v", err)
    }
    defer pgContainer.Terminate(ctx)

    connStr, _ := pgContainer.ConnectionString(ctx, "sslmode=disable")
    testDB, _ = sql.Open("postgres", connStr)
    defer testDB.Close()

    // 스키마 적용
    testDB.ExecContext(ctx, schemaSQL)

    os.Exit(m.Run())
}

func TestUserRepository_FindByID(t *testing.T) {
    // testDB를 공유해서 사용
    repo := NewUserRepository(testDB)
    // ...
}
```

각 테스트가 서로 간섭하지 않도록 테스트마다 트랜잭션을 시작하고 끝에 롤백하는 방식도 자주 쓴다.

```go
func newTestTx(t *testing.T, db *sql.DB) *sql.Tx {
    t.Helper()
    tx, err := db.Begin()
    if err != nil {
        t.Fatalf("failed to begin tx: %v", err)
    }
    t.Cleanup(func() { tx.Rollback() })
    return tx
}
```

## 벤치마크 테스트

함수 시그니처는 `func BenchmarkXxx(b *testing.B)`이고, `b.N`번 반복 실행한다. `go test`는 `b.N`을 자동으로 조정해서 신뢰할 수 있는 측정값을 얻는다.

```go
func BenchmarkProcessItems(b *testing.B) {
    items := generateItems(1000)
    b.ResetTimer() // 준비 시간 제외

    for i := 0; i < b.N; i++ {
        ProcessItems(items)
    }
}
```

```bash
go test -bench=. ./...
go test -bench=BenchmarkProcessItems -benchmem ./...
```

`-benchmem`을 붙이면 할당 횟수와 바이트 수도 같이 나온다.

```
BenchmarkProcessItems-8    100000    15234 ns/op    4096 B/op    3 allocs/op
```

`15234 ns/op`은 한 번 실행에 15마이크로초, `4096 B/op`은 한 번에 4KB 할당, `3 allocs/op`은 힙 할당이 3번 발생한다는 의미다.

여러 입력 크기에 대해 비교할 때는 서브벤치마크를 쓴다.

```go
func BenchmarkProcessItems(b *testing.B) {
    sizes := []int{10, 100, 1000, 10000}

    for _, size := range sizes {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            items := generateItems(size)
            b.ResetTimer()
            for i := 0; i < b.N; i++ {
                ProcessItems(items)
            }
        })
    }
}
```

벤치마크 결과를 비교할 때는 `golang.org/x/perf/cmd/benchstat`을 쓴다. 최적화 전후 결과를 파일로 저장하고 비교하면 통계적으로 유의미한 차이인지 확인할 수 있다.

```bash
go test -bench=. -count=10 ./... > before.txt
# 코드 수정 후
go test -bench=. -count=10 ./... > after.txt
benchstat before.txt after.txt
```

`-count=10`으로 10번 반복해서 측정 편차를 줄인다. 한 번만 돌린 결과로 성능 비교를 하면 노이즈가 크다.

벤치마크에서 컴파일러 최적화로 인한 dead code elimination을 막으려면 결과값을 패키지 레벨 변수에 할당한다.

```go
var result int

func BenchmarkCalculate(b *testing.B) {
    var r int
    for i := 0; i < b.N; i++ {
        r = Calculate(i)
    }
    result = r // 최적화 방지
}
```

## Fuzzing

Go 1.18부터 표준 라이브러리에 fuzz 테스트가 추가됐다. 함수 시그니처는 `func FuzzXxx(f *testing.F)`이고, 시드 코퍼스와 fuzz 대상 함수를 등록한다.

```go
func FuzzParseURL(f *testing.F) {
    // 시드 코퍼스: 알려진 입력값들
    f.Add("https://example.com/path?q=1")
    f.Add("http://localhost:8080")
    f.Add("")

    f.Fuzz(func(t *testing.T, input string) {
        // 패닉 없이 실행되어야 하는 함수
        result, err := ParseURL(input)
        if err != nil {
            return // 에러는 괜찮음, 패닉이 문제
        }
        // 파싱 후 재직렬화하면 동일해야 한다는 속성 검증
        if result.String() == "" && input != "" {
            t.Errorf("ParseURL(%q).String() returned empty", input)
        }
    })
}
```

```bash
# 단순 실행 (시드 코퍼스만 테스트)
go test -run FuzzParseURL ./...

# 실제 퍼징 실행 (새로운 입력을 생성해서 테스트)
go test -fuzz=FuzzParseURL -fuzztime=30s ./...
```

`-fuzztime`을 지정하지 않으면 무한히 돌아간다. CI에서는 시드 코퍼스만 실행하고, 퍼징은 별도 작업으로 돌리는 게 일반적이다.

퍼징 중 패닉이나 실패를 발견하면 `testdata/fuzz/FuzzXxx/` 디렉터리에 해당 입력이 저장된다. 이후 `go test -run`으로 회귀 테스트로 쓸 수 있다.

fuzz 테스트가 유용한 경우는 파서, 직렬화/역직렬화, 암호화 함수처럼 임의의 바이트 입력을 처리하는 코드다. 예상치 못한 입력에 패닉이 없어야 한다는 조건만 있어도 fuzz 테스트를 적용할 가치가 있다.

`f.Fuzz` 함수 안에서 `t.Skip`을 쓰면 특정 입력을 건너뛸 수 있다. 하지만 남용하면 퍼징의 의미가 없어진다.

## httptest 활용

HTTP 핸들러 테스트는 `net/http/httptest` 패키지로 처리한다. 실제 서버를 띄울 필요가 없다.

```go
import (
    "net/http"
    "net/http/httptest"
    "testing"
)

func TestHealthHandler(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/health", nil)
    rec := httptest.NewRecorder()

    HealthHandler(rec, req)

    if rec.Code != http.StatusOK {
        t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
    }
}
```

`httptest.NewRecorder()`는 `http.ResponseWriter`를 구현한 구조체다. 핸들러가 기록한 상태 코드, 헤더, 바디를 나중에 꺼내볼 수 있다.

JSON 응답을 검증할 때는 바디를 디코딩해서 확인한다.

```go
func TestCreateUserHandler(t *testing.T) {
    body := strings.NewReader(`{"name": "alice"}`)
    req := httptest.NewRequest(http.MethodPost, "/users", body)
    req.Header.Set("Content-Type", "application/json")
    rec := httptest.NewRecorder()

    CreateUserHandler(rec, req)

    if rec.Code != http.StatusCreated {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusCreated)
    }

    var resp map[string]any
    if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
        t.Fatalf("failed to decode response: %v", err)
    }
    if resp["name"] != "alice" {
        t.Errorf("name = %v, want alice", resp["name"])
    }
}
```

외부 HTTP API를 호출하는 코드를 테스트할 때는 `httptest.NewServer`로 목 서버를 띄운다.

```go
func TestFetchUser(t *testing.T) {
    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        fmt.Fprintln(w, `{"id": 1, "name": "alice"}`)
    }))
    defer server.Close()

    client := &UserClient{BaseURL: server.URL}
    user, err := client.FetchUser(1)
    if err != nil {
        t.Fatalf("FetchUser() error: %v", err)
    }
    if user.Name != "alice" {
        t.Errorf("Name = %s, want alice", user.Name)
    }
}
```

`server.URL`이 목 서버의 주소다. 테스트 대상 코드가 `BaseURL`을 주입받는 구조여야 이 패턴이 가능하다. 하드코딩된 URL이면 이 방법으로 테스트할 수 없다.

## -race 플래그로 data race 감지

Go 런타임에는 race detector가 내장되어 있다. `-race` 플래그를 붙이면 런타임에 동시 접근을 추적해서 data race를 감지한다.

```bash
go test -race ./...
```

race detector는 빌드 시 계측 코드를 삽입한다. 실행이 5~10배 느려지고 메모리도 더 쓴다. CI에서는 `-race`를 붙이고, 로컬 개발 중에는 필요할 때만 쓴다.

실제로 race condition이 있는 코드를 테스트하면 이렇게 나온다.

```
WARNING: DATA RACE
Write at 0x00c000016068 by goroutine 7:
  main.counter()
      /tmp/main.go:14 +0x44

Previous read at 0x00c000016068 by goroutine 6:
  main.counter()
      /tmp/main.go:12 +0x30
```

race detector는 실제로 실행된 코드 경로만 검사한다. 테스트가 특정 고루틴 조합을 실행하지 않으면 그 race는 잡히지 않는다. race detector가 아무것도 안 잡았다고 race가 없다는 의미가 아니다.

병렬 테스트에서 race를 감지하려면 `t.Parallel()`을 함께 써야 효과가 있다.

```go
func TestCounter(t *testing.T) {
    tests := []struct {
        name string
        n    int
    }{
        {"small", 10},
        {"large", 1000},
    }

    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            t.Parallel()
            result := Counter(tc.n)
            if result != tc.n {
                t.Errorf("Counter(%d) = %d, want %d", tc.n, result, tc.n)
            }
        })
    }
}
```

Go 1.22부터는 루프 변수가 각 반복마다 새로 생성되어 `tc := tc` 관용구가 필요 없다.

race가 실제로 발생하는지 검증하는 테스트를 짤 때는 `sync.WaitGroup`으로 고루틴들을 동시에 출발시키는 방식을 쓴다.

```go
func TestMapConcurrentWrite(t *testing.T) {
    m := make(map[string]int)
    var wg sync.WaitGroup

    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func(n int) {
            defer wg.Done()
            m[fmt.Sprintf("key%d", n)] = n // race!
        }(i)
    }
    wg.Wait()
}
```

이 테스트에 `-race`를 붙이면 race를 잡는다. 수정 방법은 `sync.Map`을 쓰거나 `sync.Mutex`로 맵 접근을 보호하는 것이다.
