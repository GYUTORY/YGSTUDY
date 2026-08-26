---
title: Zustand 실무 사용법
tags: [frontend, typescript, javascript]
updated: 2026-08-26
---

# Zustand 실무 사용법

Redux 보일러플레이트 없이 전역 상태를 관리할 때 Zustand를 선택하는 경우가 많다. 설치하고 10분이면 동작하는 수준의 단순함이 있지만, 프로젝트가 커지면 store 분리 기준이 모호해지고, selector를 제대로 쓰지 않으면 불필요한 리렌더가 쌓인다.

## store를 어디서 나눌 것인가

가장 흔한 실수는 전역 상태를 전부 하나의 store에 넣는 것이다. 처음엔 단순해 보이지만 store 크기가 커질수록 특정 slice만 구독하기 어려워진다.

분리 기준은 두 가지다.

첫째, **업데이트 주기가 다른 데이터는 다른 store에 넣는다.** 사용자 세션 정보(로그인 유지 동안 거의 변하지 않음)와 UI 상태(탭 선택, 모달 열림 여부)를 같은 store에 두면, UI 상태가 바뀔 때마다 세션 정보를 구독하는 컴포넌트들도 리렌더를 검토해야 한다.

둘째, **도메인 경계를 따라 나눈다.** 주문 관련 상태와 사용자 프로필 상태는 서로를 직접 참조할 이유가 없다. 참조가 생기기 시작하면 store 간 의존성이 생겨 테스트하기 어려워진다.

```ts
// 세션 store
const useSessionStore = create<SessionState>()((set) => ({
  userId: null,
  token: null,
  setSession: (userId: string, token: string) => set({ userId, token }),
  clearSession: () => set({ userId: null, token: null }),
}))

// UI store — 세션 store와 독립적으로 존재한다
const useUIStore = create<UIState>()((set) => ({
  sidebarOpen: false,
  activeTab: 'home',
  setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
  setActiveTab: (tab: string) => set({ activeTab: tab }),
}))
```

store 파일 하나에 관련 타입, `create` 호출, 개별 selector 훅을 전부 모아두는 방식이 관리하기 편하다. 파일이 길어지면 타입과 store를 각각 나눠도 되지만, 처음부터 쪼개는 건 불필요한 파일 이동만 늘린다.

## selector로 리렌더 막기

Zustand의 `useStore`는 기본적으로 store 전체를 구독한다. store의 어떤 값이라도 바뀌면 해당 훅을 쓰는 컴포넌트는 리렌더된다.

```ts
// store의 모든 변경에 리렌더된다
const { userId, token } = useSessionStore()

// userId가 바뀔 때만 리렌더된다
const userId = useSessionStore((state) => state.userId)
```

객체나 배열을 반환하는 selector는 따로 주의가 필요하다. 매번 새 객체를 생성하면 참조가 달라져 값이 같아도 리렌더가 발생한다.

```ts
// 매 렌더마다 새 객체 생성 → 값이 같아도 항상 리렌더
const user = useSessionStore((state) => ({
  id: state.userId,
  token: state.token,
}))
```

이 경우 `useShallow`로 얕은 비교를 적용한다. Zustand v5부터 `shallow`를 두 번째 인자로 넘기는 방식은 deprecated됐고, `useShallow`로 대체됐다.

```ts
import { useShallow } from 'zustand/react/shallow'

const { userId, token } = useSessionStore(
  useShallow((state) => ({ userId: state.userId, token: state.token }))
)
```

필드가 독립적이라면 각각 따로 구독하는 게 더 명확하다.

```ts
const userId = useSessionStore((state) => state.userId)
const token = useSessionStore((state) => state.token)
```

배열에서 특정 항목을 찾는 selector는 조심해야 한다. `find`로 찾은 객체를 그대로 반환하면, 해당 객체의 참조가 바뀔 때마다 리렌더된다. 필요한 필드만 꺼내거나 `useShallow`를 함께 쓴다.

## subscribe로 React 밖에서 상태 감시하기

컴포넌트 외부에서 상태 변화에 반응해야 할 때 `subscribe`를 쓴다. 웹소켓 연결 관리, 분석 이벤트 전송이 여기에 해당한다.

기본 `subscribe`는 store 전체 상태를 넘겨준다. 특정 값이 바뀔 때만 실행하려면 `subscribeWithSelector` 미들웨어가 필요하다.

```ts
import { subscribeWithSelector } from 'zustand/middleware'

const useSessionStore = create<SessionState>()(
  subscribeWithSelector((set) => ({
    userId: null,
    token: null,
    setSession: (userId: string, token: string) => set({ userId, token }),
    clearSession: () => set({ userId: null, token: null }),
  }))
)

// 컴포넌트 외부, 앱 초기화 시점에 등록
const unsubscribe = useSessionStore.subscribe(
  (state) => state.userId,
  (userId, prevUserId) => {
    if (userId && !prevUserId) {
      analytics.track('login', { userId })
      websocket.connect(userId)
    } else if (!userId && prevUserId) {
      websocket.disconnect()
    }
  },
)

// 앱 종료나 cleanup 시점에 해제
unsubscribe()
```

`subscribe`의 세 번째 인자로 옵션을 넘길 수 있다. `equalityFn`으로 커스텀 비교 함수를, `fireImmediately: true`로 구독 등록 즉시 현재 값으로 한 번 실행할 수 있다.

## persist 미들웨어와 hydration 타이밍

`persist`를 쓰면 localStorage나 sessionStorage에 store 상태를 저장하고 복원한다. 설정 자체는 단순하지만, Next.js 환경에서 hydration 타이밍 문제가 반드시 나타난다.

```ts
import { persist } from 'zustand/middleware'

const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'light' as const,
      language: 'ko',
      setTheme: (theme: 'light' | 'dark') => set({ theme }),
    }),
    {
      name: 'settings-storage',
    }
  )
)
```

문제는 서버 렌더링과 클라이언트 hydration 사이의 상태 불일치다. 서버는 초기값(`theme: 'light'`)으로 HTML을 생성하지만, 클라이언트는 localStorage에서 복원한 값(`theme: 'dark'`)을 갖고 있다. React는 이 불일치를 hydration mismatch 경고로 알리고, 더 심하면 화면이 깨진다.

`_hasHydrated` 패턴으로 처리한다.

```ts
interface SettingsState {
  theme: 'light' | 'dark'
  language: string
  setTheme: (theme: 'light' | 'dark') => void
  _hasHydrated: boolean
  setHasHydrated: (state: boolean) => void
}

const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'light',
      language: 'ko',
      setTheme: (theme) => set({ theme }),
      _hasHydrated: false,
      setHasHydrated: (state) => set({ _hasHydrated: state }),
    }),
    {
      name: 'settings-storage',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)
```

컴포넌트에서는 hydration이 끝나기 전까지 서버와 동일한 기본값을 보여준다.

```ts
function ThemeToggle() {
  const hasHydrated = useSettingsStore((state) => state._hasHydrated)
  const theme = useSettingsStore((state) => state.theme)
  const setTheme = useSettingsStore((state) => state.setTheme)

  if (!hasHydrated) {
    // 서버 렌더링 결과와 일치하는 기본값을 보여준다
    return <button>light</button>
  }

  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      {theme}
    </button>
  )
}
```

저장할 필드를 선택하고 싶을 때는 `partialize`를 쓴다. 민감한 값이나 임시 상태는 저장에서 제외하는 게 맞다.

```ts
persist(
  (set) => ({ ... }),
  {
    name: 'settings-storage',
    partialize: (state) => ({
      theme: state.theme,
      // language는 브라우저 기본값에서 읽을 것이므로 저장 제외
    }),
  }
)
```

localStorage 대신 다른 스토리지를 쓸 때는 `storage` 옵션으로 교체한다. sessionStorage, IndexedDB, 쿠키 등 `getItem`/`setItem`/`removeItem`을 구현하면 된다.

## immer 통합

중첩된 객체를 업데이트할 때 spread 연산자가 길어지는 문제가 있다. `immer` 미들웨어를 쓰면 mutable 방식으로 작성하면서 실제로는 불변 업데이트가 일어난다.

```ts
import { immer } from 'zustand/middleware/immer'

interface CartState {
  items: Array<{
    id: string
    quantity: number
    price: number
  }>
  updateQuantity: (id: string, quantity: number) => void
  removeItem: (id: string) => void
  clearCart: () => void
}

const useCartStore = create<CartState>()(
  immer((set) => ({
    items: [],
    updateQuantity: (id, quantity) =>
      set((state) => {
        const item = state.items.find((i) => i.id === id)
        if (item) {
          item.quantity = quantity  // draft 객체를 직접 수정한다
        }
      }),
    removeItem: (id) =>
      set((state) => {
        state.items = state.items.filter((i) => i.id !== id)
      }),
    clearCart: () =>
      set((state) => {
        state.items = []
      }),
  }))
)
```

immer 없이 같은 코드를 쓰면 이렇게 된다.

```ts
updateQuantity: (id, quantity) =>
  set((state) => ({
    items: state.items.map((item) =>
      item.id === id ? { ...item, quantity } : item
    ),
  })),
```

깊이가 두 단계만 넘어가도 spread가 급격히 복잡해진다. 상태 구조가 3~4단계 중첩될 때 immer의 효과가 명확히 드러난다.

immer를 쓸 때 주의할 점이 있다. `set` 안에서 draft 객체를 반환하면 안 된다. draft를 수정하거나 새 값을 반환하는 두 방식 중 하나만 써야 한다. 둘 다 하면 immer가 어느 쪽을 써야 할지 몰라 에러를 던진다.

```ts
// 잘못된 패턴 — draft 수정하면서 반환까지 한다
set((state) => {
  state.items = []
  return state  // 이러면 안 된다
})

// 올바른 패턴 1 — draft 수정만
set((state) => {
  state.items = []
})

// 올바른 패턴 2 — 새 값 반환만
set(() => ({ items: [] }))
```

## 미들웨어 조합 순서

`persist`, `immer`, `devtools`, `subscribeWithSelector`를 함께 쓸 때 순서가 중요하다. 일반적으로 `devtools`가 가장 바깥에, `immer`가 가장 안쪽에 온다.

```ts
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

const useCartStore = create<CartState>()(
  devtools(
    persist(
      subscribeWithSelector(
        immer((set) => ({
          items: [],
          // ...
        }))
      ),
      { name: 'cart-storage' }
    ),
    { name: 'CartStore' }
  )
)
```

`immer`를 `persist` 바깥에 두면 persist가 immer의 draft 객체를 직렬화하려다 문제가 생긴다. `devtools`를 안쪽에 두면 다른 미들웨어의 상태 변화를 추적하지 못한다.

DevTools에서 액션 이름을 남기려면 `set`의 세 번째 인자를 쓴다.

```ts
set(
  (state) => {
    state.items = []
  },
  false,        // replace 여부 (true면 state 전체 교체)
  'clearCart',  // DevTools에 표시될 액션 이름
)
```
