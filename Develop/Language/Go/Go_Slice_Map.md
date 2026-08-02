---
title: Go 슬라이스와 맵 내부 구조
tags: [Go, Golang, Slice, map, sync.Map, 동시성]
---

# Go 슬라이스와 맵 내부 구조

Go의 슬라이스와 맵은 겉으로 단순해 보이지만, 내부 동작을 모르고 쓰다가 데이터가 예기치 않게 바뀌거나 goroutine panic이 나는 경우를 자주 만난다. 특히 슬라이스 공유로 인한 데이터 오염은 디버깅하기 까다롭다. 내부 구조부터 실무에서 실제로 발생하는 문제 상황까지 다룬다.

## 슬라이스 내부 구조

슬라이스는 배열 포인터, 길이(len), 용량(cap) 세 필드로 구성된 헤더 구조체다.

```go
// runtime/slice.go 내부 구조 (개념적 표현)
type slice struct {
    array unsafe.Pointer // 실제 데이터가 있는 배열 포인터
    len   int            // 현재 사용 중인 요소 수
    cap   int            // 배열에 할당된 공간
}
```

`make([]int, 3, 5)`를 하면 길이 3, 용량 5짜리 슬라이스가 생긴다. 내부적으로 크기 5인 배열이 힙에 할당되고, 슬라이스 헤더는 그 배열의 시작점을 가리킨다. `len`이 3이므로 인덱스 0~2만 접근 가능하지만, 배열에는 5개 공간이 있다.

### append 동작과 용량 증가

`append`는 `len < cap`이면 기존 배열에 추가하고, `len == cap`이면 새 배열을 할당한 뒤 기존 데이터를 복사한다.

```go
s := make([]int, 3, 5)
fmt.Println(len(s), cap(s)) // 3 5

s = append(s, 10) // cap이 남아있으므로 기존 배열에 추가
fmt.Println(len(s), cap(s)) // 4 5

s = append(s, 20) // 5 5, 아직 기존 배열
s = append(s, 30) // len == cap이므로 새 배열 할당
fmt.Println(len(s), cap(s)) // 6 10
```

용량 증가 배수는 Go 버전마다 다르다. Go 1.17 이하에서는 현재 용량이 1024 미만이면 2배, 1024 이상이면 1.25배였다. Go 1.18부터 이 기준이 256으로 바뀌었고, 증가 공식도 변경됐다. 정확한 값이 필요하면 `cap()`으로 직접 확인해야 한다.

새 배열 할당이 반복되면 GC 압박이 생긴다. 최종 크기를 미리 알 수 있으면 `make([]T, 0, n)`으로 초기 용량을 지정해 두는 게 낫다.

```go
// 루프로 1000개를 append할 때
// 초기 용량 지정 없이: 여러 번 재할당 발생
s1 := []int{}
for i := 0; i < 1000; i++ {
    s1 = append(s1, i)
}

// 초기 용량 지정: 재할당 없음
s2 := make([]int, 0, 1000)
for i := 0; i < 1000; i++ {
    s2 = append(s2, i)
}
```

## 슬라이스 공유로 인한 데이터 오염

슬라이스를 다른 변수에 대입하거나 함수에 전달하면 헤더(포인터, len, cap)가 복사된다. 두 슬라이스 헤더가 같은 배열을 가리키기 때문에, 한쪽에서 요소를 수정하면 다른 쪽도 바뀐다.

```go
a := []int{1, 2, 3, 4, 5}
b := a[1:3] // b는 a의 인덱스 1~2를 가리킴, len=2, cap=4

b[0] = 99
fmt.Println(a) // [1 99 3 4 5] — a도 바뀐다
```

함수 내부에서 슬라이스를 수정할 때 의도치 않게 발생하는 경우가 많다.

```go
func process(items []string) {
    items[0] = "modified" // 원본도 바뀐다
}

original := []string{"a", "b", "c"}
process(original)
fmt.Println(original[0]) // "modified"
```

`append`가 끼면 더 헷갈린다. cap이 남아있는 상태에서 `append`를 하면 원본 배열에 쓰게 된다.

```go
a := make([]int, 3, 6)
a[0], a[1], a[2] = 1, 2, 3

b := a[:2] // b는 a의 앞 2개, cap=6

b = append(b, 99) // cap이 남아있으므로 a[2]에 씀
fmt.Println(a) // [1 2 99] — a[2]가 바뀐다
```

이 동작이 버그로 이어지는 패턴은 주로 슬라이스를 잘라서 넘기고, 받은 쪽에서 append하는 경우다. cap이 언제 초과될지 호출자 입장에서 예측하기 어렵다.

## three-index expression으로 cap 제한

Go 1.2에서 추가된 `a[low:high:max]` 형태다. `high`와 `max`가 같은 값이면 해당 슬라이스의 cap이 `high - low`로 고정된다. 슬라이스를 다른 함수나 라이브러리에 넘길 때 의도치 않은 배열 공유를 차단하는 용도로 쓴다.

```go
a := make([]int, 5, 10)
a[0], a[1], a[2], a[3], a[4] = 1, 2, 3, 4, 5

// 2-index: b의 cap은 a의 남은 용량 그대로
b := a[0:3]    // len=3, cap=10

// 3-index: cap을 3으로 강제
c := a[0:3:3]  // len=3, cap=3

b = append(b, 99) // a[3]에 쓴다. a[3]은 4 → 99로 바뀜
c = append(c, 88) // cap 초과 → 새 배열 할당, a에 영향 없음

fmt.Println(a) // [1 2 3 99 5] — b는 a를 공유
fmt.Println(a[3]) // 99
```

패키지 경계를 넘어서 슬라이스를 넘길 때 3-index로 넘기는 습관을 들이면 디버깅하기 어려운 버그를 줄일 수 있다.

```go
// 내부 버퍼를 외부로 넘길 때
type Buffer struct {
    buf []byte
}

func (b *Buffer) Bytes() []byte {
    // 3-index를 쓰면 받는 쪽이 append해도 b.buf가 오염되지 않는다
    return b.buf[0:len(b.buf):len(b.buf)]
}
```

## copy 함정

`copy`는 `min(len(dst), len(src))`만큼만 복사한다. dst의 len이 작으면 src가 잘린다.

```go
src := []int{1, 2, 3, 4, 5}

// 흔한 실수: dst를 make로 할당했지만 len을 지정하지 않은 경우
dst := make([]int, 0, len(src)) // len=0, cap=5
n := copy(dst, src)
fmt.Println(n, dst) // 0, [] — 아무것도 복사되지 않음

// 올바른 방법: len을 지정해야 한다
dst2 := make([]int, len(src))
n = copy(dst2, src)
fmt.Println(n, dst2) // 5, [1 2 3 4 5]
```

`make([]T, 0, n)`으로 만든 슬라이스는 len이 0이라서 copy가 0개를 복사한다. `make([]T, n)`이나 `make([]T, n, n)`을 써야 원하는 만큼 복사된다.

부분 복사도 마찬가지다. 오버랩 범위만 복사되는 걸 모르고 쓰다가 데이터가 잘리는 경우가 있다.

```go
a := []int{1, 2, 3, 4, 5}
b := make([]int, 3) // len=3

copy(b, a) // min(3, 5) = 3개만 복사
fmt.Println(b) // [1 2 3] — 4, 5는 복사 안 됨
```

슬라이스 요소가 포인터나 슬라이스, 맵 같은 참조 타입이면 copy는 얕은 복사다. 내부 포인터까지 독립 복사가 필요하면 직접 순회해서 복사해야 한다.

```go
type Node struct {
    Children []int
}

src := []Node{{Children: []int{1, 2, 3}}}
dst := make([]Node, len(src))
copy(dst, src)

dst[0].Children[0] = 99
fmt.Println(src[0].Children[0]) // 99 — Children은 공유됨
```

## 맵 삭제 후 메모리가 반환되지 않는 문제

맵에서 `delete`로 키를 지워도 내부 버킷 메모리는 해제되지 않는다. 맵이 한번 커진 버킷 배열은 GC 대상이 되지 않는다.

```go
m := make(map[string]string)

// 100만 개를 추가했다 지워도 버킷 메모리는 남는다
for i := 0; i < 1_000_000; i++ {
    m[fmt.Sprintf("key-%d", i)] = "value"
}
for i := 0; i < 1_000_000; i++ {
    delete(m, fmt.Sprintf("key-%d", i))
}

fmt.Println(len(m)) // 0, 하지만 메모리는 여전히 점유 중
```

이 동작은 Go 스펙에 명시된 내용은 아니지만, 현재 런타임 구현상 delete가 버킷을 축소하지 않는다. 큰 맵을 임시로 쓰고 비우는 패턴에서 메모리가 예상보다 높게 유지되는 원인이 된다.

메모리를 실제로 회수하려면 새 맵으로 교체해야 한다.

```go
// 기존 맵을 새 맵으로 교체
m = make(map[string]string)
// 또는 nil로 대체
m = nil
```

값 타입이 포인터인 경우 버킷이 살아있는 동안 GC가 포인터가 가리키는 객체도 수집하지 못한다. 큰 구조체를 값으로 들고 있는 맵이라면 delete 후에도 해당 구조체들이 메모리에 남아있다.

```go
type BigStruct struct {
    Data [1024]byte
}

cache := make(map[string]*BigStruct)
cache["key"] = &BigStruct{}

// delete해도 포인터가 버킷에 남아있을 수 있어서
// BigStruct가 GC되지 않을 수 있다
delete(cache, "key")
// cache를 교체해야 확실히 해제된다
cache = make(map[string]*BigStruct)
```

프로세스가 장시간 구동되면서 맵에 데이터를 넣고 지우는 패턴을 반복하는 서비스라면 메모리 사용량이 서서히 올라가는 증상이 나타날 수 있다. 이럴 때는 일정 주기로 맵을 새로 교체하거나 아예 다른 캐시 라이브러리를 고려하는 게 현실적이다.

## 맵 동시 접근 패닉

Go의 맵은 동시 접근이 안전하지 않다. 여러 goroutine에서 동시에 읽기/쓰기를 하면 런타임 패닉이 발생한다.

```
fatal error: concurrent map read and map write
```

race condition이기 때문에 항상 재현되지 않는다. 로컬에서는 괜찮다가 트래픽이 몰릴 때만 터지는 경우가 있어서 찾기 어렵다.

```go
// 이 코드는 패닉이 날 수 있다
m := map[string]int{}

go func() {
    for i := 0; i < 1000; i++ {
        m["key"] = i
    }
}()

go func() {
    for i := 0; i < 1000; i++ {
        _ = m["key"]
    }
}()
```

`-race` 플래그로 빌드하면 race condition을 탐지할 수 있다.

```bash
go run -race main.go
go test -race ./...
```

개발 단계에서 `-race`를 습관적으로 쓰는 게 좋다. 성능 오버헤드가 있어서 프로덕션 바이너리에는 보통 안 넣는다.

### mutex로 보호

맵에 동시 접근이 필요하면 `sync.RWMutex`로 감싸는 방법이 있다.

```go
type SafeMap struct {
    mu sync.RWMutex
    m  map[string]int
}

func (s *SafeMap) Get(key string) (int, bool) {
    s.mu.RLock()
    defer s.mu.RUnlock()
    v, ok := s.m[key]
    return v, ok
}

func (s *SafeMap) Set(key string, value int) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.m[key] = value
}
```

읽기가 많고 쓰기가 적은 경우 `RWMutex`가 `Mutex`보다 낫다. 읽기는 동시에 여러 goroutine이 할 수 있고, 쓰기는 독점 잠금을 사용한다.

## sync.Map 사용 시점

`sync.Map`은 Go 1.9에서 추가된 동시성 안전 맵이다. 내부적으로 두 개의 맵(read map, dirty map)을 사용하고, 읽기는 atomic 연산으로, 쓰기는 mutex로 처리한다.

```go
var m sync.Map

m.Store("key", 42)

value, ok := m.Load("key")
if ok {
    fmt.Println(value.(int)) // 42
}

m.Delete("key")

m.Range(func(key, value any) bool {
    fmt.Println(key, value)
    return true // false를 반환하면 순회 중단
})
```

`sync.Map`이 `RWMutex + map`보다 나은 경우는 두 가지다.

키가 한 번 쓰고 여러 번 읽히는 패턴: 캐시처럼 키가 write 한 번, read 여러 번인 경우. `sync.Map`의 read map은 atomic 읽기를 사용하므로 잠금 경합이 거의 없다.

여러 goroutine이 서로 다른 키를 쓰는 패턴: 키별로 goroutine이 고정되거나, 키 집합이 안정적일 때. dirty map 승격 빈도가 낮아서 성능이 좋다.

반대로 `sync.Map`이 불리한 경우가 있다. 키를 자주 추가하고 삭제하는 패턴에서는 dirty map 승격이 자주 일어나서 `RWMutex + map`보다 느릴 수 있다. `sync.Map`은 타입이 `any`라서 타입 단언이 필요하고, 컴파일 타임 타입 체크가 없다.

```go
// sync.Map은 타입 단언 필수
value, ok := m.Load("key")
if ok {
    n := value.(int) // 틀리면 런타임 패닉
}
```

벤치마크를 돌려보기 전에는 `RWMutex + map`을 먼저 쓰고, 프로파일링에서 잠금 경합이 병목으로 나오면 `sync.Map`으로 바꾸는 게 낫다.

## 맵 순회 순서와 ordered map 패턴

맵의 반복 순서는 보장되지 않는다. 같은 맵을 두 번 range로 돌리면 순서가 다를 수 있다. Go 런타임이 의도적으로 맵 순회 시작 위치를 랜덤하게 정한다.

순서가 필요하면 키를 별도 슬라이스에 담아서 정렬한 뒤 접근해야 한다.

```go
m := map[string]int{"c": 3, "a": 1, "b": 2}

keys := make([]string, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
sort.Strings(keys)

for _, k := range keys {
    fmt.Println(k, m[k])
}
// a 1
// b 2
// c 3
```

삽입 순서를 유지해야 하는 경우라면 슬라이스와 맵을 함께 쓰는 패턴이 실무에서 자주 등장한다. 키 목록을 슬라이스로 관리하고, 값은 맵에서 가져오는 방식이다.

```go
type OrderedMap struct {
    keys []string
    m    map[string]int
}

func NewOrderedMap() *OrderedMap {
    return &OrderedMap{
        m: make(map[string]int),
    }
}

func (o *OrderedMap) Set(key string, value int) {
    if _, exists := o.m[key]; !exists {
        o.keys = append(o.keys, key)
    }
    o.m[key] = value
}

func (o *OrderedMap) Get(key string) (int, bool) {
    v, ok := o.m[key]
    return v, ok
}

func (o *OrderedMap) Delete(key string) {
    if _, exists := o.m[key]; !exists {
        return
    }
    delete(o.m, key)
    for i, k := range o.keys {
        if k == key {
            o.keys = append(o.keys[:i], o.keys[i+1:]...)
            break
        }
    }
}

func (o *OrderedMap) Range(fn func(key string, value int)) {
    for _, k := range o.keys {
        fn(k, o.m[k])
    }
}
```

Delete에서 슬라이스 요소를 제거하는 부분이 O(n)이라 키가 많으면 느려진다. 삭제가 빈번하지 않고 순서 유지가 중요한 경우에 쓰기 적합하다. 삭제가 자주 일어나면 순서 유지 슬라이스에 tombstone을 표시하고 주기적으로 압축하는 방식을 쓰기도 한다.

외부 라이브러리를 쓰는 것도 선택지다. `github.com/elliotchance/orderedmap` 같은 패키지가 있지만, 위 구조 정도는 직접 구현해도 몇 줄이라 의존성을 추가하는 게 항상 유리한 건 아니다.

## 슬라이스 vs 맵 — 흔히 만나는 실수

슬라이스를 nil 체크 없이 순회하는 건 문제없다. nil 슬라이스의 len은 0이므로 range가 그냥 실행되지 않는다.

```go
var s []int
for _, v := range s { // 안전, 순회만 안 됨
    fmt.Println(v)
}
```

맵은 nil 맵에서 읽기는 되지만 쓰기는 패닉이 난다.

```go
var m map[string]int
_ = m["key"] // 0, false — 패닉 없음

m["key"] = 1 // panic: assignment to entry in nil map
```

맵은 반드시 `make`로 초기화하거나 리터럴로 생성해야 한다.

```go
m := make(map[string]int)
// 또는
m := map[string]int{}
```
