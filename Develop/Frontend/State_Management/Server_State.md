---
title: 서버 상태 관리 — React Query / SWR
tags: [frontend, javascript, typescript, api]
updated: 2026-08-26
---

# 서버 상태 관리 — React Query / SWR

서버 상태는 클라이언트 상태와 성격이 다르다. 클라이언트 상태는 내가 완전히 제어한다. 초기화, 변경, 삭제 모두 내 코드 안에서 일어난다. 서버 상태는 서버가 소유한다. 내가 갖는 건 복사본이고, 그 복사본이 언제 낡는지, 언제 다시 가져올지 결정하는 게 서버 상태 관리의 핵심이다.

## 클라이언트 상태에 서버 데이터를 넣으면 생기는 일

Redux나 Zustand 같은 클라이언트 상태 관리 라이브러리에 API 응답을 그대로 집어넣는 경우가 있다. 처음엔 잘 작동하는 것처럼 보이지만 코드가 쌓이면 몇 가지 문제가 나타난다.

동기화 코드가 반복된다. 화면 진입 시 fetch, 탭 전환 시 fetch, 특정 action dispatch 후 재fetch — 이 타이밍을 직접 관리해야 한다. 놓치는 케이스가 생기고, 캐시를 무효화해야 할 시점이 늘어날수록 누가 어떤 action을 언제 dispatch해야 하는지 파악하기 어려워진다.

데이터가 낡은 상태로 남는다. 사용자 A가 주문을 취소했는데, 관리자 화면에서는 여전히 "처리 중"으로 보인다. 배경에서 자동으로 갱신하는 로직을 직접 구현하지 않으면 항상 이 문제가 생긴다.

로딩·에러 상태 관리가 중복된다. `isLoading`, `error`, `data`를 저장소마다 따로 선언하고 관리한다.

React Query나 SWR을 쓰면 이 중에서 두 번째와 세 번째가 라이브러리 책임으로 넘어간다.

## staleTime과 cacheTime — 두 개념을 헷갈리면 생기는 문제

React Query에서 가장 많이 틀리는 부분이다.

`staleTime`은 데이터를 "신선하다"고 볼 시간이다. 이 시간 안에 같은 쿼리를 다시 실행하면 네트워크 요청 없이 캐시를 그대로 쓴다. 기본값은 0 — 즉 캐시가 있어도 항상 재요청한다.

`cacheTime`(v5에서는 `gcTime`으로 이름이 바뀌었다)은 구독자가 없는 캐시를 메모리에서 얼마나 유지할지를 정한다. 컴포넌트가 unmount되면 해당 쿼리의 구독자가 사라진다. cacheTime이 지나면 가비지 컬렉터가 그 캐시를 지운다. 기본값은 5분.

흔한 오해가 있다. staleTime을 늘리면 cacheTime도 늘려야 한다고 생각하는 것. staleTime이 cacheTime보다 길면 의미가 없다 — 캐시가 먼저 사라지기 때문이다. staleTime을 늘릴 때는 cacheTime도 같이 늘려야 의도대로 동작한다.

```tsx
import { useQuery } from '@tanstack/react-query'

function useUserProfile(userId: string) {
  return useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
    staleTime: 5 * 60 * 1000,   // 5분 동안 신선
    gcTime: 10 * 60 * 1000,     // 10분 동안 메모리 유지
  })
}
```

모든 쿼리마다 staleTime을 지정하는 대신 `QueryClient`에 기본값을 설정하고 필요한 곳에서만 오버라이드하는 방식이 관리하기 편하다.

```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,   // 기본 1분
      gcTime: 5 * 60 * 1000,  // 기본 5분
      retry: 1,
    },
  },
})
```

이 설정 없이 기본값 그대로 쓰면 staleTime이 0이라 컴포넌트 마운트마다 요청이 나간다. 페이지 이동 후 돌아올 때마다 같은 API를 호출하는 현상이 여기서 나온다.

## staleTime 튜닝 기준

데이터 특성에 따라 staleTime 설정이 달라진다.

자주 바뀌지 않는 데이터 — 국가 코드, 카테고리 목록, 설정값 — 는 staleTime을 길게 가져가도 된다. 30분~1시간 정도가 적당하다.

사용자 입력이 없어도 변할 수 있는 데이터 — 주문 상태, 재고 수량, 알림 수 — 는 다른 사용자의 행동이나 백엔드 처리로 값이 바뀐다. staleTime을 짧게 유지하거나 0으로 둔다. `refetchOnWindowFocus`(기본 true)가 여기서 도움이 된다.

실시간성이 중요한 데이터는 staleTime 0에 `refetchInterval`을 추가한다.

```tsx
function useOrderStatus(orderId: string) {
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: () => fetchOrderStatus(orderId),
    staleTime: 0,
    refetchInterval: (query) => {
      // 주문이 완료되면 폴링 중단
      const status = query.state.data?.status
      if (status === 'delivered' || status === 'cancelled') return false
      return 10 * 1000  // 10초마다
    },
  })
}
```

`refetchInterval`에 함수를 넘기면 현재 데이터 상태에 따라 폴링 여부를 동적으로 결정할 수 있다.

## mutation 후 캐시 무효화

서버 상태를 변경하고 나면 관련된 캐시를 무효화해야 한다. 방법은 두 가지다.

### invalidateQueries — 간단하지만 네트워크를 쓴다

```tsx
const queryClient = useQueryClient()

const { mutate: updateUser } = useMutation({
  mutationFn: (data: UpdateUserRequest) => updateUserApi(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['user'] })
  },
})
```

`invalidateQueries`는 캐시를 stale 상태로 만들고, 해당 쿼리를 구독 중인 컴포넌트가 있으면 바로 재요청을 트리거한다. 구독 중인 컴포넌트가 없으면 다음 마운트 시점에 재요청한다.

쿼리 키가 `['user', userId]`처럼 배열이면 `['user']`만 전달해도 하위 키 전체가 무효화된다.

### setQueryData — 네트워크 없이 캐시를 직접 갱신한다

서버 응답에 이미 갱신된 데이터가 있을 때 쓴다.

```tsx
const { mutate: updateUser } = useMutation({
  mutationFn: (data: UpdateUserRequest) => updateUserApi(data),
  onSuccess: (updatedUser) => {
    queryClient.setQueryData(['user', updatedUser.id], updatedUser)

    // 목록 캐시에서 해당 사용자만 교체
    queryClient.setQueryData<User[]>(['users'], (prev) => {
      if (!prev) return prev
      return prev.map((user) =>
        user.id === updatedUser.id ? updatedUser : user
      )
    })
  },
})
```

목록이 복잡하거나 페이지네이션이 있으면 `setQueryData`로 직접 맞추는 게 까다로워진다. 그럴 때는 `invalidateQueries`로 재요청하는 게 더 안전하다.

## optimistic update 구현과 롤백

사용자가 버튼을 눌렀을 때 서버 응답을 기다리지 않고 UI를 먼저 갱신한다. 네트워크 지연이 500ms 이상일 때 체감 속도 차이가 명확하다.

React Query에서 optimistic update는 `onMutate`, `onError`, `onSettled` 세 콜백으로 구현한다.

```tsx
const { mutate: toggleLike } = useMutation({
  mutationFn: (postId: string) => toggleLikeApi(postId),

  onMutate: async (postId) => {
    // 진행 중인 refetch를 취소한다 — optimistic update와 충돌하면 안 된다
    await queryClient.cancelQueries({ queryKey: ['post', postId] })

    // 롤백을 위해 현재 캐시 값을 저장한다
    const previousPost = queryClient.getQueryData<Post>(['post', postId])

    // 낙관적으로 캐시를 갱신한다
    queryClient.setQueryData<Post>(['post', postId], (prev) => {
      if (!prev) return prev
      return {
        ...prev,
        liked: !prev.liked,
        likeCount: prev.liked ? prev.likeCount - 1 : prev.likeCount + 1,
      }
    })

    return { previousPost }
  },

  onError: (err, postId, context) => {
    // 에러 발생 시 이전 캐시로 롤백한다
    if (context?.previousPost) {
      queryClient.setQueryData(['post', postId], context.previousPost)
    }
  },

  onSettled: (data, err, postId) => {
    // 성공이든 실패든 서버 데이터로 최종 동기화한다
    queryClient.invalidateQueries({ queryKey: ['post', postId] })
  },
})
```

`cancelQueries`를 빠뜨리면 문제가 생긴다. optimistic update로 캐시를 `liked: true`로 만들었는데, 진행 중이던 refetch가 완료되어 `liked: false`를 덮어쓰는 경우다. 사용자 눈에는 좋아요가 눌렸다가 1초 뒤 다시 풀리는 것처럼 보인다.

## 목록 optimistic update의 복잡성

단일 항목은 단순하지만, 목록에서 항목을 추가하거나 삭제하는 optimistic update는 더 복잡하다.

항목을 낙관적으로 추가할 때 임시 id가 필요하다. 서버가 실제 id를 반환하기 전이니 클라이언트가 임시로 만들어야 한다.

```tsx
const { mutate: addTodo } = useMutation({
  mutationFn: (text: string) => addTodoApi(text),

  onMutate: async (text) => {
    await queryClient.cancelQueries({ queryKey: ['todos'] })
    const previousTodos = queryClient.getQueryData<Todo[]>(['todos'])

    const optimisticTodo: Todo = {
      id: `temp-${Date.now()}`,
      text,
      completed: false,
    }

    queryClient.setQueryData<Todo[]>(['todos'], (prev) => {
      return prev ? [...prev, optimisticTodo] : [optimisticTodo]
    })

    return { previousTodos }
  },

  onError: (err, text, context) => {
    if (context?.previousTodos) {
      queryClient.setQueryData(['todos'], context.previousTodos)
    }
  },

  onSettled: () => {
    // 서버가 반환한 실제 id로 임시 항목을 교체한다
    queryClient.invalidateQueries({ queryKey: ['todos'] })
  },
})
```

`onSettled`에서 `invalidateQueries`를 호출하는 이유는, 서버가 반환한 실제 id로 임시 항목을 교체해야 하기 때문이다. `setQueryData`로 직접 교체하려면 임시 id와 실제 id를 매핑하는 로직이 필요한데, 그냥 재요청하는 게 더 단순하다.

## SWR과의 차이

SWR은 React Query보다 API가 단순하다. 빠르게 쓸 수 있지만 mutation 관련 기능이 상대적으로 빈약하다.

```tsx
import useSWR, { useSWRMutation } from 'swr'

const { data, error, mutate } = useSWR('/api/user', fetcher)
const { trigger } = useSWRMutation('/api/user', updateUser)

// mutation 후 재요청
await trigger(updatedData)
await mutate()
```

SWR의 `mutate` 함수에 데이터를 직접 넘기면 optimistic update도 가능하다.

```tsx
await mutate(
  updateUser(updatedData),
  {
    optimisticData: { ...data, ...updatedData },
    rollbackOnError: true,  // 에러 시 자동 롤백
  }
)
```

`rollbackOnError: true` 하나로 롤백 로직이 자동 처리된다는 점은 React Query보다 편하다. 단, React Query의 `onMutate`/`onError`/`onSettled`처럼 세밀하게 제어하기 어렵다.

복잡한 mutation 시나리오가 많으면 React Query를 쓰는 게 낫다. 단순한 CRUD 위주라면 SWR이 코드 양이 적다.

## 쿼리 의존성 — enabled 옵션

쿼리가 다른 쿼리의 결과에 의존할 때 `enabled` 옵션으로 실행 시점을 제어한다.

```tsx
function useUserOrders(userId: string | undefined) {
  return useQuery({
    queryKey: ['orders', userId],
    queryFn: () => fetchOrders(userId!),
    enabled: !!userId,  // userId가 있을 때만 실행한다
  })
}
```

`enabled`에 falsy 값을 넣으면 컴포넌트가 마운트돼도 요청이 나가지 않는다. 의존하는 데이터가 준비되면 자동으로 요청한다.

병렬 쿼리는 `useQueries`로 묶는다.

```tsx
const results = useQueries({
  queries: userIds.map((id) => ({
    queryKey: ['user', id],
    queryFn: () => fetchUser(id),
    staleTime: 5 * 60 * 1000,
  })),
})
```

`useQuery`를 반복문 안에서 호출하면 Hook 규칙을 위반한다. `useQueries`가 이 케이스를 처리하는 올바른 방법이다.
