---
title: "React 내장 상태 관리: useState, useReducer, Context API"
tags: [frontend, javascript, typescript, design-patterns, performance]
updated: 2026-08-29
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

## useState 지연 초기화

초기값으로 비싼 계산이 들어갈 때, 값을 직접 넘기면 렌더마다 그 계산이 반복 실행된다.

```tsx
// localStorage에서 읽는 비용이 매 렌더마다 발생한다
const [filters, setFilters] = useState(
  JSON.parse(localStorage.getItem('filters') ?? '{}')
);
```

`useState`의 초기값 인자는 렌더마다 평가된다. 초기 마운트 이후에는 쓰이지도 않는 값을 계속 만든다. 함수로 감싸면 최초 한 번만 실행된다.

```tsx
// () => 로 감싸면 초기 마운트 때만 실행된다
const [filters, setFilters] = useState(() =>
  JSON.parse(localStorage.getItem('filters') ?? '{}')
);
```

컴포넌트가 자주 리렌더링되거나, 초기값이 배열 탐색·정렬·파싱처럼 O(n) 이상의 계산을 포함하면 지연 초기화를 기본으로 쓰는 게 낫다.

주의할 점이 있다. 함수 자체를 상태로 저장하고 싶을 때 헷갈리는 경우가 생긴다.

```tsx
// initState가 함수면 React가 lazy initializer로 호출해버린다
const [fn, setFn] = useState(initState);   // initState()의 반환값이 초기 상태가 됨

// 함수를 상태로 저장하려면 한 번 더 감싼다
const [fn, setFn] = useState(() => initState);   // initState 자체가 초기 상태가 됨
```

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

## useReducer init 함수

`useReducer`는 세 번째 인자로 초기화 함수를 받는다. 이걸 모르면 초기화 로직이 reducer 내부에 `INIT` 같은 액션으로 묻히거나, "리셋" 기능을 구현할 때 초기 상태 객체를 두 곳에서 유지해야 하는 상황이 생긴다.

`useReducer(reducer, arg, init)` 형태로 쓰면 `init(arg)`의 반환값이 초기 상태가 된다.

```tsx
type CounterState = { count: number; step: number };

type Action =
  | { type: 'INCREMENT' }
  | { type: 'RESET' };

function initCounter(step: number): CounterState {
  return { count: 0, step };
}

function reducer(state: CounterState, action: Action): CounterState {
  switch (action.type) {
    case 'INCREMENT': return { ...state, count: state.count + state.step };
    case 'RESET': return initCounter(state.step);  // 초기화 함수 재사용
    default: return state;
  }
}

const [state, dispatch] = useReducer(reducer, initialStep, initCounter);
```

`RESET` 케이스에서 `initCounter`를 그대로 재사용할 수 있다는 게 핵심이다. init 함수 없이 구현하면 이런 모양이 된다.

```tsx
case 'RESET': return { count: 0, step: state.step };
```

초기 상태 형태가 바뀔 때마다 `RESET` 케이스도 같이 고쳐야 한다. init 함수를 쓰면 이 동기화 문제가 사라진다.

---

## Context 소비 — useContext

`createContext`와 `Provider`만 있으면 절반이다. 소비하는 쪽이 어떻게 연결되는지 봐야 전체 그림이 잡힌다.

```tsx
const ThemeContext = createContext<Theme>('light');

function App() {
  const [theme, setTheme] = useState<Theme>('light');
  return (
    <ThemeContext.Provider value={theme}>
      <Toolbar setTheme={setTheme} />
    </ThemeContext.Provider>
  );
}

// 소비 측 — useContext로 꺼낸다
function ThemedButton() {
  const theme = useContext(ThemeContext);
  return (
    <button className={`btn-${theme}`}>
      현재 테마: {theme}
    </button>
  );
}
```

`useContext(ThemeContext)`는 가장 가까운 상위 `ThemeContext.Provider`의 `value`를 반환한다. Provider가 없으면 `createContext`에 넘긴 기본값(`'light'`)을 반환한다.

Provider 없이 기본값이 반환되는 상황이 조용한 버그가 된다. `'light'`가 반환되니 에러는 안 나는데 화면이 이상하게 동작하는 경우다.

---

## Context를 감싸는 커스텀 훅

`useContext`를 컴포넌트에 직접 쓰면 두 가지 문제가 생긴다. Provider 없이 쓸 경우 기본값이 조용히 반환되고, TypeScript에서 기본값을 `null`로 설정하면 소비 측마다 null 체크가 반복된다.

```tsx
const ThemeContext = createContext<Theme | null>(null);

function ThemedButton() {
  const theme = useContext(ThemeContext);
  if (!theme) return null;  // 모든 소비 컴포넌트에 이 체크가 붙는다
  return <button className={`btn-${theme}`}>{theme}</button>;
}
```

커스텀 훅으로 감싸면 이 체크를 한 곳에 모을 수 있다.

```tsx
const ThemeContext = createContext<Theme | null>(null);

export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  if (!theme) {
    throw new Error('useTheme은 ThemeProvider 안에서만 쓸 수 있다');
  }
  return theme;
}

// 소비 측 — null 체크 없이 바로 쓴다
function ThemedButton() {
  const theme = useTheme();
  return <button className={`btn-${theme}`}>{theme}</button>;
}
```

Provider 밖에서 `useTheme()`을 호출하면 즉시 에러가 던져진다. "테마가 없는데 버튼이 이상하게 보인다"는 디버깅 대신 "useTheme은 ThemeProvider 안에서만 쓸 수 있다"는 메시지가 바로 뜬다.

상태와 setter를 함께 노출해야 하는 모달 같은 경우:

```tsx
type ModalContextType = {
  isOpen: boolean;
  open: (content: ReactNode) => void;
  close: () => void;
};

const ModalContext = createContext<ModalContextType | null>(null);

export function useModal(): ModalContextType {
  const ctx = useContext(ModalContext);
  if (!ctx) {
    throw new Error('useModal은 ModalProvider 안에서만 쓸 수 있다');
  }
  return ctx;
}

export function ModalProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [content, setContent] = useState<ReactNode>(null);

  const value = useMemo(() => ({
    isOpen,
    open: (node: ReactNode) => { setContent(node); setIsOpen(true); },
    close: () => setIsOpen(false),
  }), [isOpen]);

  return (
    <ModalContext.Provider value={value}>
      {children}
    </ModalContext.Provider>
  );
}
```

커스텀 훅 패턴을 쓰면 Context 내부 구조가 바뀌어도 소비 컴포넌트는 손대지 않아도 된다. `useModal()`의 반환 타입만 유지하면 된다.

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

## React DevTools로 리렌더링 추적

Context 관련 버그는 "왜 이 컴포넌트가 리렌더링되는가"를 알아야 잡힌다. React DevTools의 Profiler가 이 용도에 맞다.

브라우저에 React DevTools 확장을 설치하면 개발자 도구에 Components, Profiler 두 탭이 생긴다.

**Components 탭에서 구독 확인하기**

Components 탭에서 컴포넌트를 선택하면 오른쪽 패널 "hooks" 섹션 아래에 해당 컴포넌트가 소비하는 Context 목록이 나온다. `useContext(ThemeContext)`를 호출하는 컴포넌트라면 `Context.ThemeContext: "dark"` 같은 형태로 현재 값이 표시된다.

Context에 `displayName`을 설정하면 DevTools에서 구분하기 훨씬 쉬워진다.

```tsx
const ThemeContext = createContext<Theme>('light');
ThemeContext.displayName = 'ThemeContext';

const UserContext = createContext<User | null>(null);
UserContext.displayName = 'UserContext';
```

`displayName` 없이는 DevTools에서 전부 "Context"로 표시된다. Context가 여러 개면 어느 게 어느 건지 구분이 안 된다.

**Profiler 탭에서 리렌더링 원인 찾기**

Profiler 탭에서 녹화를 시작하고 문제가 되는 동작을 한 뒤 녹화를 멈추면, 각 컴포넌트의 렌더링 여부와 원인이 플레임 차트로 나온다.

컴포넌트를 클릭하면 오른쪽 패널에 "Why did this render?" 항목이 뜬다. Context 값이 바뀌어서 리렌더링된 경우 "Context changed"라고 표시된다.

```
ThemedButton
  Why did this render?
  - Context changed (ThemeContext)
```

이 정보로 어떤 Context 변경이 이 컴포넌트를 건드렸는지 바로 확인할 수 있다. `useMemo`나 Context 분리가 실제로 효과가 있었는지도 같은 방법으로 확인한다. Profiler 녹화에서 해당 컴포넌트가 회색(렌더링 안 됨)으로 나오면 최적화가 먹힌 거다.

이 항목은 React 개발 빌드에서만 보인다. 프로덕션 빌드(`NODE_ENV=production`)에서는 표시되지 않는다. CRA나 Vite 기본 설정에서 개발 서버(`npm run dev`)로 실행하면 개발 빌드가 켜진다.

---

## Context만으로 부족해지는 시점

자주 바뀌지 않는 전역 값(테마, 로케일, 인증된 사용자 정보)은 Context로 충분하다.

그 외에 Context가 한계를 보이는 경우들이 있다.

**비동기 상태** — API 호출 결과, 로딩 상태, 에러 상태를 Context로 관리하면 boilerplate가 급격히 늘어난다. 캐시 무효화, 재시도, 백그라운드 갱신까지 직접 구현해야 한다. TanStack Query나 SWR이 이 용도로 맞다.

**파생 상태** — 기존 상태에서 계산되는 값을 Context에 넣으면 중복 상태가 생긴다. 원본이 바뀔 때 파생 값을 동기화하는 코드를 직접 관리해야 한다.

**세밀한 구독** — Context는 전체 value 기준으로 리렌더링된다. 필드 단위로 구독하려면 use-context-selector 같은 별도 패키지가 필요하다. 이 수준이 되면 Zustand selector를 쓰는 게 더 직관적이다.
