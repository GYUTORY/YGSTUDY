---
title: "React.lazy와 Suspense"
tags: [frontend, react, performance, javascript]
updated: 2026-09-14
---

## 코드 분할이 필요한 이유

SPA는 번들 파일 하나에 모든 라우트의 코드를 담는다. 사용자가 대시보드 진입 시 결제 페이지 코드까지 받는다. 빌드 산출물이 커질수록 첫 화면이 뜨기까지 걸리는 시간이 선형으로 늘어난다.

`React.lazy`는 동적 `import()`를 래핑해서 컴포넌트를 별도 청크로 분리한다. 라우트 단위로 끊으면 초기 번들을 60~70% 줄이는 경우가 흔하다. 그 대가는 첫 진입 시 청크를 네트워크에서 받는 지연이다.

## 기본 사용 패턴

```jsx
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));

function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

`lazy()`에 넘기는 함수는 `default export`를 가진 모듈을 반환해야 한다. named export만 있으면 `lazy(() => import('./Foo').then(m => ({ default: m.Foo })))` 형태로 변환해야 한다.

Suspense가 없으면 lazy 컴포넌트가 로딩 상태일 때 React가 에러를 던진다. Suspense는 반드시 lazy 컴포넌트의 **조상** 어딘가에 있어야 한다.

## 중첩 Suspense 경계 설계

경계를 하나만 두면 페이지 전체가 fallback으로 교체된다. 사이드바는 이미 로드됐는데 메인 콘텐츠 때문에 사이드바까지 사라지는 상황이 발생한다.

경계를 나누는 기준은 **독립적으로 로드될 수 있는 단위**다.

```jsx
function DashboardPage() {
  return (
    <Layout>
      {/* 사이드바는 이미 번들에 포함 — Suspense 불필요 */}
      <Sidebar />

      <main>
        {/* 메인 콘텐츠 영역만 fallback */}
        <Suspense fallback={<ContentSkeleton />}>
          <MainContent />
        </Suspense>

        {/* 위젯은 서로 독립적으로 로드 */}
        <div className="widgets">
          <Suspense fallback={<WidgetSkeleton />}>
            <RevenueWidget />
          </Suspense>
          <Suspense fallback={<WidgetSkeleton />}>
            <TrafficWidget />
          </Suspense>
        </div>
      </main>
    </Layout>
  );
}
```

위젯을 하나의 Suspense로 묶으면 RevenueWidget이 느릴 때 TrafficWidget도 기다려야 한다. 독립 경계를 두면 빠른 위젯이 먼저 나타난다.

경계를 너무 잘게 나누면 fallback이 여기저기서 동시에 튀어나와 화면이 어수선해진다. 실제로 쓸 때는 3~5개 수준이 적당하다.

## fallback 깜박임 문제

청크가 캐시됐거나 네트워크가 빠르면 fallback이 100ms 미만으로 나타났다 사라진다. 사용자 입장에서 순간 번쩍이는 것처럼 보인다.

React 18 이전에는 직접 타이머를 걸어서 일정 시간 이하면 fallback을 숨기는 패턴을 많이 썼다. React 18에서는 `startTransition`이 이 문제를 다르게 접근한다.

```jsx
import { startTransition, useState } from 'react';

function Navigation() {
  const [route, setRoute] = useState('home');

  function navigate(to) {
    // startTransition으로 감싸면 React가 현재 콘텐츠를 유지하면서
    // 백그라운드에서 다음 화면을 준비한다
    startTransition(() => {
      setRoute(to);
    });
  }

  return (
    <nav>
      <button onClick={() => navigate('dashboard')}>대시보드</button>
      <button onClick={() => navigate('settings')}>설정</button>
    </nav>
  );
}
```

`startTransition` 없이 라우트를 바꾸면 React가 즉시 현재 화면을 내리고 fallback을 올린다. `startTransition`으로 감싸면 새 컴포넌트가 준비될 때까지 이전 화면을 유지한다. 준비가 오래 걸리면 그때 fallback으로 전환한다.

`useTransition` 훅을 쓰면 전환 중임을 알리는 `isPending` 상태를 받을 수 있다.

```jsx
import { useTransition, Suspense } from 'react';

function App() {
  const [isPending, startTransition] = useTransition();
  const [page, setPage] = useState('home');

  return (
    <div>
      <nav style={{ opacity: isPending ? 0.6 : 1 }}>
        <button onClick={() => startTransition(() => setPage('dashboard'))}>
          대시보드
        </button>
      </nav>

      <Suspense fallback={<PageSkeleton />}>
        {page === 'dashboard' && <Dashboard />}
      </Suspense>
    </div>
  );
}
```

네비게이션 버튼의 opacity를 낮춰서 전환 중임을 표시하는 패턴이다. fallback이 뜨지 않아도 사용자가 "뭔가 진행 중"임을 알 수 있다.

## 레이아웃 흔들림

fallback 높이가 실제 콘텐츠 높이와 다르면 콘텐츠가 로드될 때 레이아웃이 움직인다. Cumulative Layout Shift(CLS) 점수가 나빠지고 사용자가 클릭 실수를 한다.

fallback을 만들 때 실제 콘텐츠와 같은 높이를 잡아줘야 한다.

```jsx
// 나쁜 예: 높이 지정 없음
function BadSkeleton() {
  return <div className="skeleton" />;
}

// 좋은 예: 실제 카드와 같은 높이 고정
function CardSkeleton() {
  return (
    <div
      className="skeleton"
      style={{ height: '240px', borderRadius: '8px' }}
    />
  );
}
```

리스트 아이템 skeleton은 실제 아이템 개수를 모를 때 몇 개를 보여줘야 하는지 판단이 필요하다. 일반적으로 최초 로드에서 보이는 개수를 기준으로 5~10개 정도 고정하는 편이다.

## React Query와 연동

React Query 5에서는 `useSuspenseQuery`로 데이터 페칭을 Suspense에 연결할 수 있다.

```jsx
import { useSuspenseQuery } from '@tanstack/react-query';

// 이 컴포넌트는 데이터가 준비될 때까지 suspend된다
function UserProfile({ userId }) {
  const { data: user } = useSuspenseQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
  });

  // loading/error 분기 없이 바로 렌더
  return <div>{user.name}</div>;
}

// 부모에서 Suspense와 ErrorBoundary로 감쌈
function ProfilePage({ userId }) {
  return (
    <ErrorBoundary fallback={<ErrorMessage />}>
      <Suspense fallback={<ProfileSkeleton />}>
        <UserProfile userId={userId} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

`useQuery`는 컴포넌트 안에서 `isLoading`/`isError`를 직접 처리한다. `useSuspenseQuery`는 그 책임을 Suspense와 ErrorBoundary로 위임한다. 컴포넌트 자체는 데이터가 있다고 가정하고 렌더 로직만 담게 된다.

주의할 점이 있다. `useSuspenseQuery`를 쓰는 컴포넌트 여러 개가 같은 Suspense 경계 안에 있으면 폭포수(waterfall) 현상이 생긴다. 첫 번째 쿼리가 끝나야 두 번째 컴포넌트가 마운트되고 두 번째 쿼리가 시작된다.

```jsx
// 폭포수 발생: UserProfile이 끝나야 UserPosts가 시작됨
function ProfilePage({ userId }) {
  return (
    <Suspense fallback={<Skeleton />}>
      <UserProfile userId={userId} />
      <UserPosts userId={userId} />  {/* UserProfile이 resolve될 때까지 마운트 안 됨 */}
    </Suspense>
  );
}
```

해결법은 두 가지다. 경계를 분리하거나, 부모에서 미리 prefetch한다.

```jsx
// 방법 1: 각자 경계를 갖게 분리
function ProfilePage({ userId }) {
  return (
    <div>
      <Suspense fallback={<ProfileSkeleton />}>
        <UserProfile userId={userId} />
      </Suspense>
      <Suspense fallback={<PostsSkeleton />}>
        <UserPosts userId={userId} />
      </Suspense>
    </div>
  );
}

// 방법 2: 부모에서 prefetch
function ProfilePage({ userId }) {
  // 컴포넌트가 마운트되면 즉시 두 쿼리를 병렬로 시작
  usePrefetchQuery({ queryKey: ['user', userId], queryFn: () => fetchUser(userId) });
  usePrefetchQuery({ queryKey: ['posts', userId], queryFn: () => fetchPosts(userId) });

  return (
    <Suspense fallback={<Skeleton />}>
      <UserProfile userId={userId} />
      <UserPosts userId={userId} />
    </Suspense>
  );
}
```

## 실제 라우터 연동

React Router v6와 조합할 때는 라우트 정의 위치에서 lazy를 선언하는 편이 관리하기 쉽다.

```jsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const Profile = lazy(() => import('./pages/Profile'));

const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      {
        path: 'dashboard',
        element: (
          <Suspense fallback={<PageSkeleton />}>
            <Dashboard />
          </Suspense>
        ),
      },
      {
        path: 'settings',
        element: (
          <Suspense fallback={<PageSkeleton />}>
            <Settings />
          </Suspense>
        ),
      },
    ],
  },
]);
```

라우트마다 Suspense를 붙이면 페이지 전환 시 각 페이지 fallback이 독립적으로 작동한다. 최상위 하나만 두면 설정 페이지로 이동할 때 레이아웃 전체가 사라진다.

## 청크 프리로드

사용자가 버튼에 hover하는 시점에 청크를 미리 받으면 클릭 시 지연이 없다.

```jsx
const Dashboard = lazy(() => import('./pages/Dashboard'));

// hover 시점에 import를 호출해 청크를 미리 로드
// 실제 렌더는 아직 안 하지만 네트워크 요청은 시작됨
function NavLink({ to, children }) {
  function preload() {
    if (to === '/dashboard') {
      import('./pages/Dashboard');
    }
  }

  return (
    <Link to={to} onMouseEnter={preload}>
      {children}
    </Link>
  );
}
```

`import()`는 같은 경로를 여러 번 호출해도 브라우저가 캐시해서 한 번만 요청한다. hover 시점에 한 번, 실제 렌더 시 한 번 호출되더라도 네트워크 요청은 하나다.
