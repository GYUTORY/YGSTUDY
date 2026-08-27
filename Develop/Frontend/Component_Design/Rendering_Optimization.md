---
title: 렌더링 최적화
tags: [frontend, javascript, typescript, performance]
updated: 2026-08-27
---

## React.memo가 실제로 하는 일

React.memo는 이전 props와 현재 props를 얕게(shallow) 비교해서 같으면 리렌더를 건너뛴다. 핵심은 "얕게"라는 단어다.

```tsx
const Item = React.memo(({ user }: { user: User }) => {
  return <div>{user.name}</div>;
});

function Parent() {
  const [count, setCount] = useState(0);
  const user = { name: 'Alice' }; // 매 렌더마다 새 객체
  return <Item user={user} />;
}
```

`user` 객체는 참조가 매번 달라지므로 memo가 있어도 Item은 매번 리렌더된다. 원시값(string, number, boolean)만 props로 받을 때 memo가 제대로 작동한다. 객체나 배열을 넘겨야 한다면 부모에서 `useMemo`로 참조를 안정시켜야 한다.

memo의 두 번째 인수로 커스텀 비교 함수를 넣을 수 있다. 비교 로직이 실제 렌더 비용보다 무거워지는 경우가 생겨서 피하는 편이 낫다.

memo가 의미 없는 경우가 있다. 자식 컴포넌트가 `children`을 받으면 JSX는 매번 새 객체라서 memo가 항상 false를 반환한다.

```tsx
// memo를 달아도 children 때문에 항상 리렌더됨
const Wrapper = React.memo(({ children }: { children: ReactNode }) => {
  return <div>{children}</div>;
});
```

---

## useMemo와 useCallback이 오히려 느려지는 경우

두 Hook은 의존성 배열을 비교하는 비용이 항상 발생한다. 렌더 비용이 작은 컴포넌트에 무작위로 달면 오히려 느려진다.

```tsx
// 단순 계산에 useMemo 달기 — 오버헤드가 계산 비용보다 크다
const doubled = useMemo(() => count * 2, [count]);

// 그냥 쓰는 게 낫다
const doubled = count * 2;
```

useCallback이 실제로 필요한 경우는 두 가지다. React.memo로 감싼 자식 컴포넌트에 함수를 prop으로 넘길 때, useEffect의 의존성 배열에 함수가 들어갈 때.

의존성이 5개 이상이면 useMemo/useCallback보다 컴포넌트 구조 자체를 재검토하는 게 맞다.

---

## Context API가 만드는 대규모 리렌더

Context는 프로젝트 규모가 커질수록 조용히 성능을 갉아먹는다. 문제는 `Context.Provider`의 `value`가 바뀌면 해당 Context를 구독하는 컴포넌트 전부가 리렌더된다는 점이다.

```tsx
const AppContext = createContext<{
  user: User;
  theme: 'light' | 'dark';
  setTheme: (t: 'light' | 'dark') => void;
} | null>(null);

function App() {
  const [user, setUser] = useState<User>(initialUser);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  // user가 바뀔 때마다 theme만 구독하는 컴포넌트도 리렌더됨
  return (
    <AppContext.Provider value={{ user, theme, setTheme }}>
      <Layout />
    </AppContext.Provider>
  );
}
```

`user`가 바뀌었을 때 `theme`만 읽는 `ThemeToggle` 컴포넌트도 리렌더된다. value 객체의 참조가 매 렌더마다 달라지기 때문이다.

**값을 변경 빈도 기준으로 Context를 분리**하면 전파 범위를 줄일 수 있다.

```tsx
const UserContext = createContext<User | null>(null);
const ThemeContext = createContext<'light' | 'dark'>('light');
const ThemeDispatchContext = createContext<(t: 'light' | 'dark') => void>(() => {});

function App() {
  const [user] = useState<User>(initialUser);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  return (
    <UserContext.Provider value={user}>
      <ThemeContext.Provider value={theme}>
        <ThemeDispatchContext.Provider value={setTheme}>
          <Layout />
        </ThemeDispatchContext.Provider>
      </ThemeContext.Provider>
    </UserContext.Provider>
  );
}
```

`ThemeToggle`은 `ThemeContext`와 `ThemeDispatchContext`만 구독한다. `user`가 바뀌어도 이 컴포넌트는 리렌더되지 않는다.

`useReducer`를 쓰면 state Context와 dispatch Context 분리 패턴이 자연스럽게 나온다. dispatch 함수는 참조가 안정적이라 dispatch Context 구독자는 state가 바뀌어도 리렌더되지 않는다.

```tsx
type Action = { type: 'SET_THEME'; payload: 'light' | 'dark' } | { type: 'SET_USER'; payload: User };

const StateContext = createContext<AppState | null>(null);
const DispatchContext = createContext<Dispatch<Action> | null>(null);

function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </StateContext.Provider>
  );
}
```

버튼 클릭 핸들러만 있는 컴포넌트는 `DispatchContext`만 구독한다. 상태가 아무리 바뀌어도 dispatch 참조는 바뀌지 않으니 이 컴포넌트는 리렌더되지 않는다.

Context 분리로도 해결이 안 되는 경우 — 예를 들어 전역 스토어가 매우 크고 구독 단위를 세밀하게 제어해야 할 때 — 는 Zustand나 Jotai 같은 외부 상태 관리 라이브러리가 낫다. 이들은 셀렉터 기반으로 필요한 슬라이스만 구독할 수 있다.

---

## key prop이 만드는 상태 초기화 버그

key는 React가 리스트 아이템을 식별하는 데 쓰는 값이다. key가 바뀌면 React는 해당 컴포넌트를 언마운트하고 새로 마운트한다. 이 특성이 버그를 만든다.

배열 index를 key로 쓰면 아이템이 추가·삭제·재정렬될 때 index가 달라져서 엉뚱한 컴포넌트가 상태를 가져간다. 입력 필드가 있는 리스트 아이템에서 이게 터지면 사용자가 입력한 내용이 다른 행으로 이동하는 버그가 된다.

```tsx
// 아이템 고유 id를 key로 써야 한다
{items.map(item => (
  <ListItem key={item.id} item={item} />
))}
```

key를 랜덤하게 만들면 매 렌더마다 모든 아이템이 언마운트/마운트된다.

반대로 의도적으로 key를 활용하는 패턴도 있다. 검색어가 바뀔 때 컴포넌트 내부 상태를 초기화하고 싶다면 key에 검색어를 넣는다.

```tsx
<SearchResult key={query} query={query} />
```

props로 초기값을 받아서 내부 state에 담는 컴포넌트는 props가 바뀌어도 내부 state는 그대로다. key를 바꾸는 방법이 가장 명확하게 초기화를 보장한다.

---

## 긴 목록은 react-window로 잘라낸다

아이템이 1,000개인 리스트를 그대로 렌더하면 DOM 노드가 1,000개 생긴다. 스크롤 이벤트마다 레이아웃 계산이 1,000개 노드를 훑는다. 처음 200~300개부터 버벅이기 시작한다.

가상화(virtualization)는 화면에 보이는 영역의 아이템만 DOM에 유지하고, 스크롤하면 밖으로 나간 노드를 재활용한다. `react-window`가 가장 많이 쓰이는 구현체다.

아이템 높이가 균일하면 `FixedSizeList`를 쓴다.

```tsx
import { FixedSizeList } from 'react-window';

interface RowData {
  items: User[];
}

const Row = ({ index, style, data }: { index: number; style: CSSProperties; data: RowData }) => {
  const user = data.items[index];
  return (
    <div style={style}>
      {user.name} — {user.email}
    </div>
  );
};

function UserList({ users }: { users: User[] }) {
  return (
    <FixedSizeList
      height={600}
      width="100%"
      itemCount={users.length}
      itemSize={48}
      itemData={{ items: users }}
    >
      {Row}
    </FixedSizeList>
  );
}
```

`style` prop을 반드시 Row 루트 엘리먼트에 붙여야 한다. react-window가 이 style로 각 아이템의 위치를 계산한다. 빼먹으면 아이템이 전부 겹쳐서 보인다.

클로저로 데이터를 캡처하지 말고 `itemData`로 넘겨야 한다. 클로저로 캡처하면 Row 컴포넌트가 `React.memo`여도 부모 리렌더마다 새 함수가 만들어져서 가상화의 이점이 사라진다.

```tsx
// 잘못된 방법 — users가 클로저로 캡처됨
<FixedSizeList ...>
  {({ index, style }) => <div style={style}>{users[index].name}</div>}
</FixedSizeList>
```

아이템 높이가 제각각이면 `VariableSizeList`를 쓴다. `itemSize`에 함수를 넘기면 된다.

```tsx
import { VariableSizeList } from 'react-window';

const getItemSize = (index: number) => heights[index] ?? 60;

<VariableSizeList
  height={600}
  width="100%"
  itemCount={items.length}
  itemSize={getItemSize}
  itemData={{ items }}
>
  {Row}
</VariableSizeList>
```

`VariableSizeList`는 내부적으로 높이를 캐시한다. 동적으로 높이가 바뀌면 `listRef.current.resetAfterIndex(index)`를 호출해서 캐시를 무효화해야 한다. 안 하면 스크롤 위치 계산이 틀어진다.

react-window는 스크롤 컨테이너를 직접 관리한다. 기존 CSS의 `overflow: hidden`이 부모에 걸려 있으면 스크롤이 막힌다. 부모의 overflow를 확인한다.

---

## useTransition과 useDeferredValue — 긴급도 구분

React 18은 상태 업데이트에 긴급도 개념을 도입했다. 사용자 입력처럼 즉각 반응해야 하는 업데이트와, 그 결과로 파생되는 무거운 렌더링은 우선순위가 달라야 한다.

`useTransition`은 특정 상태 업데이트를 낮은 우선순위로 표시한다.

```tsx
import { useState, useTransition } from 'react';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [isPending, startTransition] = useTransition();

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value); // 즉시 반영 — 입력창 표시용

    startTransition(() => {
      setResults(filterItems(allItems, e.target.value)); // 낮은 우선순위
    });
  };

  return (
    <>
      <input value={query} onChange={handleChange} />
      {isPending && <div>검색 중...</div>}
      <ResultList items={results} />
    </>
  );
}
```

`startTransition` 안의 업데이트는 브라우저가 더 급한 작업(입력, 스크롤)을 먼저 처리하도록 양보한다. `isPending`이 true인 동안 이전 결과가 유지되다가 낮은 우선순위 업데이트가 완료되면 교체된다. 사용자 입장에서는 타이핑이 버벅이지 않고, 결과 목록은 조금 늦게 갱신된다.

`useDeferredValue`는 상태 세터를 감싸지 않고 값을 감싼다. 상태가 외부(부모 컴포넌트나 라이브러리)에서 오는 경우에 쓴다.

```tsx
import { useDeferredValue, memo } from 'react';

function SearchPage({ query }: { query: string }) {
  const deferredQuery = useDeferredValue(query);

  return (
    <>
      <input value={query} ... />
      <ResultList query={deferredQuery} />
    </>
  );
}

const ResultList = memo(({ query }: { query: string }) => {
  const results = filterItems(allItems, query); // 무거운 계산
  return <ul>{results.map(...)}</ul>;
});
```

`deferredQuery`는 `query`보다 늦게 업데이트된다. `ResultList`는 `deferredQuery`가 바뀔 때만 리렌더된다. `memo`로 감싸야 deferral이 실제로 동작한다 — 감싸지 않으면 부모가 리렌더될 때 같이 리렌더돼서 의미가 없다.

두 API의 차이는 명확하다. `useTransition`은 상태 세터를 직접 감쌀 수 있을 때 쓰고, `useDeferredValue`는 prop이나 외부에서 받은 값을 지연시킬 때 쓴다.

주의할 점이 있다. 두 API 모두 실제 작업량을 줄이지는 않는다. 계산 자체는 반드시 일어나고, 그 시점을 지연시키는 것뿐이다. 계산이 메인 스레드를 수백 ms 동안 점유한다면 낮은 우선순위 업데이트도 결국 그 시간을 사용한다. 근본적으로 무거운 계산은 Web Worker로 분리하는 게 맞다.

또 `startTransition` 안에서 비동기 작업을 시작할 수 없다. 콜백은 동기여야 한다. 비동기 데이터 패칭에 Suspense를 결합하는 패턴은 별도다.

---

## React.lazy + Suspense로 코드 분리하기

번들 크기가 커지면 초기 로딩이 느려진다. 당장 필요 없는 컴포넌트는 동적 import로 분리한다.

```tsx
import { lazy, Suspense } from 'react';

const HeavyChart = lazy(() => import('./HeavyChart'));

function Dashboard() {
  return (
    <Suspense fallback={<div>로딩 중...</div>}>
      <HeavyChart />
    </Suspense>
  );
}
```

Suspense는 가장 가까운 부모 Suspense 경계까지 올라가서 fallback을 보여준다. 여러 lazy 컴포넌트를 하나의 Suspense로 묶으면 하나라도 로딩 중이면 전체 fallback이 표시된다. 각 컴포넌트가 독립적인 로딩 상태를 가져야 한다면 Suspense를 분리한다.

```tsx
<Suspense fallback={<ChartSkeleton />}>
  <HeavyChart />
</Suspense>
<Suspense fallback={<TableSkeleton />}>
  <HeavyTable />
</Suspense>
```

라우트 단위 분리가 효과가 가장 크다.

```tsx
const HomePage = lazy(() => import('../pages/Home'));
const ProfilePage = lazy(() => import('../pages/Profile'));

function App() {
  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </Suspense>
  );
}
```

named export만 있는 모듈은 default export가 없어서 바로 lazy에 못 쓴다.

```tsx
const HeavyChart = lazy(() =>
  import('./HeavyChart').then(m => ({ default: m.HeavyChart }))
);
```

---

## Profiler로 병목 위치 특정하기

"느리다"는 감각으로 useMemo를 무작위로 달면 코드만 복잡해진다. React DevTools Profiler로 실제로 무거운 컴포넌트를 찾아서 거기에만 적용한다.

Flamegraph 뷰에서 가로 폭이 넓은 컴포넌트가 오래 걸린 것이다. 코드에서 직접 측정하려면 `<Profiler>` 컴포넌트를 쓴다.

```tsx
import { Profiler } from 'react';

function onRender(
  id: string,
  phase: 'mount' | 'update',
  actualDuration: number,
  baseDuration: number,
) {
  if (actualDuration > 16) {
    console.warn(`${id} 렌더 ${actualDuration.toFixed(1)}ms (phase: ${phase})`);
  }
}

<Profiler id="UserList" onRender={onRender}>
  <UserList users={users} />
</Profiler>
```

`actualDuration`은 이번 렌더에 실제로 소요된 시간, `baseDuration`은 memo 없이 전체를 렌더했을 때 예상 시간이다. 두 값의 차이가 크면 memo가 효과를 내고 있다는 뜻이다. 차이가 없으면 memo가 작동하지 않거나 의존성이 항상 바뀌는 것이다.

16ms는 60fps 기준 한 프레임 시간이다. 이걸 넘으면 프레임이 드롭된다.

Profiler는 프로덕션 빌드에서 기본으로 제거된다. 프로덕션에서도 수집이 필요하면 `react-dom/profiling` 번들을 써야 한다.

병목을 찾을 때 가장 먼저 볼 것은 "왜 리렌더가 발생했는가"다. DevTools에서 "Highlight updates when components render" 옵션을 켜두면 리렌더되는 컴포넌트가 하이라이트된다. 예상보다 많은 컴포넌트가 깜빡이면 props나 context가 불필요하게 변하고 있는 것이다.
