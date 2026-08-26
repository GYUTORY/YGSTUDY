---
title: 렌더링 최적화
tags: [frontend, javascript, typescript, performance]
updated: 2026-08-26
---

## React.memo가 실제로 하는 일

React.memo는 이전 props와 현재 props를 얕게(shallow) 비교해서 같으면 리렌더를 건너뛴다. 핵심은 "얕게"라는 단어다.

```tsx
const Item = React.memo(({ user }: { user: User }) => {
  return <div>{user.name}</div>;
});

// 부모
function Parent() {
  const [count, setCount] = useState(0);
  const user = { name: 'Alice' }; // 매 렌더마다 새 객체
  return <Item user={user} />;
}
```

`user` 객체는 참조가 매번 달라지므로 memo가 있어도 Item은 매번 리렌더된다. 원시값(string, number, boolean)만 props로 받을 때 memo가 제대로 작동한다.

객체나 배열을 props로 넘겨야 한다면 부모에서 `useMemo`로 참조를 안정시켜야 한다.

```tsx
function Parent() {
  const user = useMemo(() => ({ name: 'Alice' }), []);
  return <Item user={user} />;
}
```

memo의 두 번째 인수로 커스텀 비교 함수를 넣을 수 있다. 하지만 이 방법은 비교 로직이 실제 렌더 비용보다 무거워지는 경우가 생겨서 피하는 게 낫다.

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

useCallback도 마찬가지다. 함수를 자식 컴포넌트에 넘기지 않는데 useCallback으로 감싸면 쓸모없다.

```tsx
function Parent() {
  // handleClick을 자식에 넘기지 않고 내부에서만 쓴다
  const handleClick = useCallback(() => {
    setCount(c => c + 1);
  }, []);
  
  return <button onClick={handleClick}>+</button>;
}
```

useCallback이 실제로 필요한 경우는 두 가지다. 첫째, React.memo로 감싼 자식 컴포넌트에 함수를 prop으로 넘길 때. 둘째, useEffect의 의존성 배열에 함수가 들어갈 때.

의존성 배열이 길어지면 비교 비용도 올라간다. 의존성이 5개 이상이면 useMemo/useCallback보다 컴포넌트 구조 자체를 재검토하는 게 맞다.

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

Suspense는 가장 가까운 부모 Suspense 경계까지 올라가서 fallback을 보여준다. 여러 lazy 컴포넌트가 있을 때 하나의 Suspense로 묶으면 하나라도 로딩 중이면 전체 fallback이 표시된다.

```tsx
// 개별 Suspense로 분리해야 각자 로딩 표시를 가진다
<Suspense fallback={<ChartSkeleton />}>
  <HeavyChart />
</Suspense>
<Suspense fallback={<TableSkeleton />}>
  <HeavyTable />
</Suspense>
```

라우트 단위 분리가 가장 효과가 크다. 페이지별로 lazy를 적용하면 각 라우트의 코드가 별도 청크로 분리된다.

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
// named export만 있는 경우
export const HeavyChart = () => { ... };

// lazy로 쓰려면
const HeavyChart = lazy(() =>
  import('./HeavyChart').then(m => ({ default: m.HeavyChart }))
);
```

---

## key prop이 만드는 상태 초기화 버그

key는 React가 리스트 아이템을 식별하는 데 쓰는 값이다. 하지만 key가 바뀌면 React는 해당 컴포넌트를 언마운트하고 새로 마운트한다. 이 특성이 버그를 만든다.

```tsx
// 검색어가 바뀔 때마다 SearchResult를 새로 마운트하고 싶다면 key를 활용
<SearchResult key={query} query={query} />
```

이건 의도적 사용이다. 문제는 의도치 않게 key가 바뀌는 경우다.

```tsx
function Parent() {
  const items = getItems(); // 매 렌더마다 새 배열

  return (
    <ul>
      {items.map((item, index) => (
        <ListItem key={index} item={item} />
      ))}
    </ul>
  );
}
```

배열 index를 key로 쓰면 아이템이 추가·삭제·재정렬될 때 index가 달라져서 엉뚱한 컴포넌트가 상태를 가져간다. 입력 필드가 있는 리스트 아이템에서 이게 터지면 사용자가 입력한 내용이 다른 행으로 이동하는 버그가 된다.

```tsx
// 아이템 고유 id를 key로 써야 한다
{items.map(item => (
  <ListItem key={item.id} item={item} />
))}
```

key를 랜덤하게 만들면 매 렌더마다 모든 아이템이 언마운트/마운트된다.

```tsx
// 절대 하지 말 것
{items.map(item => (
  <ListItem key={Math.random()} item={item} />
))}
```

렌더링 성능보다 상태 보존이 더 중요한 경우가 있다. 탭 전환 시 폼 입력 내용을 유지하고 싶다면 `display: none`으로 숨기고 key를 고정하는 방법을 쓴다. key가 바뀌면 상태가 날아가기 때문이다.

---

## Profiler로 병목 위치 특정하기

"느리다"는 감각으로 useMemo를 무작위로 달면 코드만 복잡해진다. React DevTools Profiler로 실제로 무거운 컴포넌트를 찾아서 거기에만 적용한다.

브라우저에서 React DevTools를 열고 Profiler 탭으로 간다. "Record" 버튼을 누르고 느린 인터랙션을 재현한 뒤 중단하면 렌더 시간을 컴포넌트별로 볼 수 있다. Flamegraph 뷰에서 가로 폭이 넓은 컴포넌트가 오래 걸린 것이다.

코드에서 직접 측정하려면 `<Profiler>` 컴포넌트를 쓴다.

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

16ms 기준은 60fps 기준 한 프레임 시간이다. 이걸 넘으면 프레임이 드롭된다.

Profiler는 프로덕션 빌드에서 기본으로 제거된다. 프로덕션에서도 수집이 필요하면 `react-dom/profiling` 번들을 써야 한다.

```bash
# package.json alias 설정
"react-dom": "react-dom/profiling"
```

병목을 찾을 때 가장 먼저 볼 것은 "왜 리렌더가 발생했는가"다. DevTools에서 "Highlight updates when components render" 옵션을 켜두면 리렌더되는 컴포넌트가 하이라이트된다. 예상보다 많은 컴포넌트가 깜빡이면 props나 context가 불필요하게 변하고 있는 것이다.
