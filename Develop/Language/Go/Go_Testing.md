---
title: Go 테스트
tags:
  - Go
  - Golang
  - testing
  - table-driven-test
  - httptest
  - race-condition
updated: 2026-07-08
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

race detector는 빌드 시 계측 코드를 삽입한다. 실행이 5~10배 느려지고 메모리도 더 쓴다. 그래서 CI에서는 `-race`를 붙이고, 로컬 개발 중에는 필요할 때만 쓴다.

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
        tc := tc // Go 1.22 이전에는 루프 변수 캡처 주의
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
