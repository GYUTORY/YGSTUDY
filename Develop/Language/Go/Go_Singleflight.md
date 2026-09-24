---
title: singleflight — 중복 요청 병합
tags: [go, backend, performance, cache]
updated: 2026-09-25
---

# singleflight — 중복 요청 병합

`golang.org/x/sync/singleflight`는 동일한 키로 동시에 들어온 호출을 하나로 묶어 실행하고, 결과를 대기 중인 모든 호출에 공유한다.

## cache stampede가 실제로 어떻게 터지나

캐시 만료 시점에 트래픽이 몰리면 같은 DB 쿼리가 수백 번 동시에 실행된다. 캐시가 없으니 전부 DB로 떨어지고, DB가 응답이 느려지면 요청이 더 쌓이고, 결국 DB가 죽는다. 이게 thundering herd 문제다.

mutex로 막으려는 시도가 있지만, mutex는 한 번에 하나씩 직렬화한다. 100개 요청이 들어오면 첫 번째가 끝나야 두 번째가 시작하고, 결국 100번 DB를 친다. singleflight는 다르다. 100개 요청 중 첫 번째만 실제로 실행하고, 나머지 99개는 그 결과를 기다렸다가 그대로 받는다.

## Do()의 동작

```go
var g singleflight.Group

func fetchUser(id string) (*User, error) {
    v, err, shared := g.Do("user:"+id, func() (interface{}, error) {
        return db.QueryUser(id)
    })
    if err != nil {
        return nil, err
    }
    return v.(*User), nil
}
```

세 번째 반환값 `shared`는 이 결과가 다른 호출과 공유됐는지 나타낸다. `true`면 내 호출이 새로 실행된 게 아니라 기존 호출에 편승한 것이다. 캐시 갱신 여부 판단이나 메트릭 기록에 활용한다.

`Do()`는 블로킹이다. 같은 키로 진행 중인 호출이 있으면 그게 끝날 때까지 현재 고루틴이 대기한다. 대기 중에 컨텍스트 취소를 처리해야 한다면 `DoChan()`을 써야 한다.

## 에러 전파 — 가장 많이 실수하는 부분

singleflight에서 실제 호출이 에러를 반환하면, 그 에러가 대기 중인 모든 호출에 그대로 전달된다. 의도한 동작이지만, 운영에서 예상 밖으로 작동하는 경우가 있다.

DB가 일시적으로 죽었을 때다. 실제 호출 하나가 에러를 반환하면 대기 중이던 99개 전부가 에러를 받는다. 순간적으로 대량의 요청이 동시에 실패한다. `Do()` 하나가 에러를 내면 그게 99배로 증폭된다고 보면 된다.

`Do()` 내부에서 재시도하는 코드를 짜면 의미가 없다. 실제 호출이 에러를 반환하는 순간 대기자들이 에러를 받고 흩어지기 때문이다. 재시도는 `Do()` 바깥 레이어에서 처리한다.

```go
// 이렇게 쓰면 재시도가 대기자들에게 적용되지 않는다
v, err, _ := g.Do("key", func() (interface{}, error) {
    for i := 0; i < 3; i++ {
        result, err := fetch()
        if err == nil {
            return result, nil
        }
    }
    return nil, lastErr  // 여기서 에러가 나면 대기자 전부에게 전파된다
})
```

반환된 값은 포인터로 공유된다. 받은 `*User`를 수정하면 같은 결과를 받은 다른 고루틴에도 영향을 준다. 공유 결과를 받았을 때는 반드시 복사해서 쓴다.

## DoChan()으로 컨텍스트 취소 처리

`Do()`는 블로킹이라 컨텍스트 취소를 직접 지원하지 않는다. HTTP 핸들러에서 클라이언트가 연결을 끊어도 `Do()`가 반환할 때까지 고루틴이 살아있다. `DoChan()`은 채널을 즉시 반환하므로 `select`로 처리한다.

```go
func fetchWithContext(ctx context.Context, id string) (*User, error) {
    ch := g.DoChan("user:"+id, func() (interface{}, error) {
        return db.QueryUser(id)
    })

    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    case res := <-ch:
        if res.Err != nil {
            return nil, res.Err
        }
        return res.Val.(*User), nil
    }
}
```

컨텍스트가 취소돼도 실제 호출은 계속 실행된다. 다른 대기자가 있을 수 있기 때문이다. 취소는 이 고루틴이 결과를 포기하는 것이지, 실제 작업을 중단하는 게 아니다.

`singleflight.Result` 구조체에는 `Val`, `Err`, `Shared` 세 필드가 있다. `Do()`의 세 반환값과 같은 내용이다.

## Forget()으로 재시도 허용하기

`Do()`는 진행 중인 호출이 있으면 새 호출을 막는다. 타임아웃이 긴 호출이 막혀 있을 때, 정상 경로로 새 호출을 시작하고 싶은 경우가 있다.

```go
func fetchWithRetryWindow(id string) (*User, error) {
    key := "user:" + id

    timer := time.AfterFunc(500*time.Millisecond, func() {
        // 500ms 경과 후 이 키의 진입 제한을 해제한다
        g.Forget(key)
    })
    defer timer.Stop()

    v, err, _ := g.Do(key, func() (interface{}, error) {
        return db.QueryUser(id)
    })
    if err != nil {
        return nil, err
    }
    return v.(*User), nil
}
```

`Forget(key)`를 호출하면 이후 같은 키로 들어오는 요청은 새 호출을 시작한다. 단, 이미 대기 중인 호출들은 원래 호출 결과를 그대로 받는다. `Forget()`은 대기 중인 호출을 깨우지 않는다.

`Forget()`을 너무 공격적으로 쓰면 singleflight의 효과가 사라진다. 짧은 간격으로 계속 호출하면 매 요청이 새 호출을 시작하게 된다. 타임아웃 대응이나 명시적인 캐시 무효화 신호가 왔을 때만 쓰는 게 맞다.

## Redis 캐시와 함께 쓰는 패턴

캐시 읽기 → 없으면 DB 조회 → 캐시 쓰기 패턴에서 캐시 만료 직후 트래픽 폭발을 막는 용도로 singleflight를 쓴다.

```go
type UserCache struct {
    g     singleflight.Group
    redis *redis.Client
    db    *sql.DB
}

func (c *UserCache) Get(ctx context.Context, id string) (*User, error) {
    // 캐시 히트는 singleflight 바깥에서 처리한다
    if cached, err := c.redis.Get(ctx, "user:"+id).Bytes(); err == nil {
        var u User
        if err := json.Unmarshal(cached, &u); err == nil {
            return &u, nil
        }
    }

    // 캐시 미스는 singleflight로 묶는다
    v, err, _ := c.g.Do("user:"+id, func() (interface{}, error) {
        user, err := c.db.QueryUser(ctx, id)
        if err != nil {
            return nil, err
        }
        data, _ := json.Marshal(user)
        c.redis.Set(ctx, "user:"+id, data, 5*time.Minute)
        return user, nil
    })
    if err != nil {
        return nil, err
    }

    // 공유 결과는 복사해서 반환한다
    result := *v.(*User)
    return &result, nil
}
```

캐시 히트를 `Do()` 안에서 처리하면 안 된다. singleflight가 동작 중인 상태에서 캐시가 채워져도 대기 중인 고루틴들이 Redis에서 읽지 못하고 DB 결과를 기다린다. 캐시 확인은 항상 바깥에서 먼저 한다.

DB 쿼리 중복 제거도 같은 패턴이다. `LIMIT 1`이 아닌 무거운 집계 쿼리를 대시보드 같은 여러 위젯이 동시에 요청할 때, 쿼리 결과를 singleflight로 묶으면 DB 부하를 크게 줄인다.

## 그룹별 singleflight 분리

`singleflight.Group`은 모든 키를 하나의 그룹에서 관리한다. 리소스 종류가 다른 호출을 같은 그룹에 넣으면 키 충돌 위험이 있다.

```go
// 키 프리픽스로 구분하는 방식 — 프리픽스를 빠뜨리면 버그가 생긴다
var g singleflight.Group
g.Do("user:123", ...)
g.Do("product:123", ...)

// 그룹을 분리하면 키 충돌이 없다
var (
    userGroup    singleflight.Group
    productGroup singleflight.Group
)
userGroup.Do("123", ...)
productGroup.Do("123", ...)
```

엔티티마다 별도 그룹을 두는 게 관리하기 쉽다. 쓰기 경로와 읽기 경로는 반드시 분리한다. 쓰기가 느릴 때 읽기가 대기하는 상황이 생기기 때문이다.

`singleflight.Group`은 값 타입이 아니라 포인터로 쓴다. 값으로 복사하면 내부 뮤텍스가 복사되면서 동기화가 깨진다. 구조체 필드로 쓸 때는 항상 포인터로 임베드하거나 직접 `singleflight.Group` 필드로 선언한다(포인터 없이 선언해도 제로값이 유효하다).

## 쓰기 전에 확인할 것들

singleflight는 멱등성이 보장된 읽기 작업에만 쓴다. 쓰기나 side effect가 있는 작업에 쓰면, 대기 중이던 99개 호출 전부가 한 번의 결과를 공유한다. 이게 올바른 동작인지 먼저 확인해야 한다.

키 설계가 중요하다. 요청 파라미터가 달라도 같은 결과를 공유할 수 있으면 키를 넓게 잡고, 파라미터마다 결과가 달라야 한다면 키를 충분히 세분화한다. 너무 세분화하면 중복 제거 효과가 없어진다.

에러가 자주 나는 환경에서는 에러가 모든 대기자에게 퍼진다는 점을 반드시 고려해야 한다. 한 번의 에러가 순간적으로 많은 요청을 동시에 실패시킨다. 이런 환경에서는 서킷 브레이커와 함께 쓰는 게 안전하다.