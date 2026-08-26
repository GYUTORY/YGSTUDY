---
title: "React 내장 상태 관리: useState, useReducer, Context API"
tags: [frontend, javascript, typescript, design-patterns, performance]
updated: 2026-08-26
---

# React 내장 상태 관리

## 상태의 범위를 먼저 정한다

도구를 고르기 전에 "이 상태가 어디까지 퍼지는가"를 먼저 따진다.

- 컴포넌트 하나 안에서만 쓰인다 → `useState` 또는 `useReducer`
- 트리 여러 곳에서 읽어야 한다 → Context API
- 전혀 다른 트리, 또는 서버 캐시와 연동이 필요하다 → 외부 라이브러리(Zustand, TanStack Query 등)

이 구분을 흐리면 불필요하게 전역 상태를 만들거나, 반대로 prop drilling을 감수하게 된다.

---

## useState

단일 값, 서로 독립적인 값 여러 개를 다룰 때 쓴다. 상태 전환 로직이 setter 호출 한두 줄로 끝나면 `useState`가 맞다.

```tsx
// 독립적인 상태는 분리해서 관리한다
const [isOpen, setIsOpen] = useState(false);
const [selectedId, setSelectedId] = useState<string | null>(null);

// 하나의 객체로 합치면 매번 스프레드가 생긴다 — 이득 없음
const [state, setState] = useState({ isOpen: false, selectedId: null });
```

상태 두 개가 항상 같이 바뀐다면 하나로 합치는 게 맞다. 그렇지 않으면 분리하는 쪽이 렌더링 추적이 명확하다.

이전 상태에 의존하는 업데이트는 반드시 함수형으로 쓴다.

```tsx
// 연속 호출 시 최신 값이 반영되지 않을 수 있다
setCount(count + 1);

// 이전 상태에 의존할 때는 함수형 업데이트
setCount(prev => prev + 1);
```

이벤트 핸들러 안에서 `setCount(count + 1)`을 세 번 호출하면 `count`가 3 늘어날 것 같지만, 클로저가 같은 `count` 값을 참조해서 결국 1만 늘어난다. 함수형 업데이트는 이 문제를 피한다.

---

## useReducer — useState에서 갈아타는 시점

상태 전환 경우의 수가 늘어나기 시작하면 `useReducer`로 바꾼다.

```tsx
type Action =
  | { type: 'INCREMENT' }
  | { type: 'DECREMENT' }
  | { type: 'RESET' };

function reducer(state: number, action: Action): number {
  switch (action.type) {
    case 'INCREMENT': return state + 1;
    case 'DECREMENT': return state - 1;
    case 'RESET': return 0;
    default: return state;
  }
}

const [count, dispatch] = useReducer(reducer, 0);
```

갈아타는 기준을 잡자면:

1. 상태 전환 조건이 셋 이상이다 — `if-else` 체인이 setter 안에 들어가기 시작한다
2. 다음 상태가 이전 상태의 여러 필드에 동시에 의존한다
3. 테스트할 때 컴포넌트를 렌더링하지 않고 reducer 함수만 단위 테스트하고 싶다

세 번째 이유가 실무에서 생각보다 강하다. reducer는 순수 함수라 컴포넌트 없이 독립적으로 테스트된다.

객체 상태를 `useReducer`로 다루면 스프레드가 많아진다. 불편하면 Immer를 같이 쓴다.

```tsx
import { produce } from 'immer';

function reducer(state: State, action: Action) {
  return produce(state, draft => {
    if (action.type === 'UPDATE_NAME') {
      draft.user.name = action.payload;
    }
  });
}
```

---

## Context가 리렌더링을 트리거하는 방식

Context의 동작 방식을 정확히 알아야 실수를 안 한다.

```tsx
const ThemeContext = createContext<Theme>('light');

function App() {
  const [theme, setTheme] = useState<Theme>('light');

  return (
    <ThemeContext.Provider value={theme}>
      <Sidebar />
      <Main />
    </ThemeContext.Provider>
  );
}
```

`Provider`의 `value`가 바뀌면 `useContext(ThemeContext)`를 호출한 컴포넌트는 전부 리렌더링된다. 선택적으로 구독하는 게 불가능하다. value 객체 안에서 일부 필드만 바뀌어도 전체 구독자가 리렌더링된다.

```tsx
// theme이 바뀔 때마다 새 객체가 만들어진다
// user를 쓰는 컴포넌트까지 전부 리렌더링됨
function App() {
  const [theme, setTheme] = useState('light');
  const [user, setUser] = useState(null);

  return (
    <AppContext.Provider value={{ theme, user }}>
      ...
    </AppContext.Provider>
  );
}
```

매 렌더마다 `{ theme, user }` 객체 리터럴이 새로 생성된다. 참조 비교(`Object.is`)로 value 변경 여부를 판단하므로, 실제 값이 안 바뀌어도 새 객체면 구독자 전체가 리렌더링된다.

---

## value 분리로 리렌더링 줄이기

Context를 나누면 구독자 범위가 좁아진다.

```tsx
const ThemeContext = createContext<Theme>('light');
const UserContext = createContext<User | null>(null);

function App() {
  const [theme, setTheme] = useState<Theme>('light');
  const [user, setUser] = useState<User | null>(null);

  return (
    <ThemeContext.Provider value={theme}>
      <UserContext.Provider value={user}>
        <AppLayout />
      </UserContext.Provider>
    </ThemeContext.Provider>
  );
}
```

이제 `theme`이 바뀌면 `useContext(ThemeContext)` 구독자만 리렌더링된다. `user`를 쓰는 컴포넌트는 그대로다.

상태와 setter를 같이 Context에 넣는 경우도 분리한다.

```tsx
const CountContext = createContext<number>(0);
const CountDispatchContext = createContext<Dispatch<Action>>(() => {});

function CountProvider({ children }: { children: ReactNode }) {
  const [count, dispatch] = useReducer(reducer, 0);

  return (
    <CountDispatchContext.Provider value={dispatch}>
      <CountContext.Provider value={count}>
        {children}
      </CountContext.Provider>
    </CountDispatchContext.Provider>
  );
}
```

`dispatch`는 리렌더링마다 새로 만들어지지 않는다. `useReducer`가 항상 같은 참조를 반환한다. `CountDispatchContext`를 구독하는 컴포넌트(버튼 같은 것)는 `count`가 바뀌어도 리렌더링되지 않는다.

`useState`도 동일하다. `setValue`는 컴포넌트 생명주기 동안 참조가 바뀌지 않으므로 setter만 쓰는 컴포넌트를 별도 context로 분리하면 value 변경 시 리렌더링을 막을 수 있다.

---

## value 객체를 useMemo로 안정화하기

Context value로 객체를 넘겨야 할 때, 렌더마다 새 객체가 생기는 문제를 `useMemo`로 막는다.

```tsx
function ModalProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [content, setContent] = useState<ReactNode>(null);

  const value = useMemo(() => ({
    isOpen,
    content,
    open: (node: ReactNode) => { setContent(node); setIsOpen(true); },
    close: () => setIsOpen(false),
  }), [isOpen, content]);

  return (
    <ModalContext.Provider value={value}>
      {children}
    </ModalContext.Provider>
  );
}
```

`isOpen`이나 `content`가 바뀔 때만 새 value 객체가 만들어진다. 부모 컴포넌트가 다른 이유로 리렌더링되어도 Context 구독자는 영향받지 않는다.

`useMemo` 자체가 공짜는 아니다. 매 렌더마다 의존성 배열을 비교하는 비용이 있다. 리렌더링이 잦은 Provider, 또는 구독자가 많은 Context에서만 쓸 가치가 있다.

`open` 함수처럼 Context value 안에 콜백을 넣으면 `useCallback`도 같이 챙겨야 한다. 그렇지 않으면 `isOpen`이 바뀔 때마다 함수가 새로 생성되어 `useMemo`의 의존성이 매번 바뀐다.

---

## Context만으로 부족해지는 시점

자주 바뀌지 않는 전역 값(테마, 로케일, 인증된 사용자 정보)은 Context로 충분하다.

그 외에 Context가 한계를 보이는 경우들이 있다.

**비동기 상태** — API 호출 결과, 로딩 상태, 에러 상태를 Context로 관리하면 boilerplate가 급격히 늘어난다. 캐시 무효화, 재시도, 백그라운드 갱신까지 직접 구현해야 한다. TanStack Query나 SWR이 이 용도로 맞다.

**파생 상태** — 기존 상태에서 계산되는 값을 Context에 넣으면 중복 상태가 생긴다. 원본이 바뀔 때 파생 값을 동기화하는 코드를 직접 관리해야 한다.

**세밀한 구독** — Context는 전체 value 기준으로 리렌더링된다. 필드 단위로 구독하려면 use-context-selector 같은 별도 패키지가 필요하다. 이 수준이 되면 Zustand selector를 쓰는 게 더 직관적이다.
