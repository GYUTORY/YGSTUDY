---
title: Error Boundary
tags: [frontend, javascript, typescript]
updated: 2026-09-14
---

## 클래스 컴포넌트여야 하는 이유

Error Boundary는 `getDerivedStateFromError`와 `componentDidCatch` 두 라이프사이클 메서드로 작동한다. 함수형 컴포넌트에는 이 두 메서드를 대체하는 훅이 없어서, React 18 기준으로도 Error Boundary 자체는 반드시 클래스 컴포넌트로 작성해야 한다.

`getDerivedStateFromError`는 렌더 단계에서 호출되고 상태를 반환해서 fallback UI가 뭘 보여줄지 결정한다. `componentDidCatch`는 커밋 단계에서 호출되고 에러 로깅에 쓴다. 둘의 역할이 다르다.

## Props/State 타입 정의

클래스 컴포넌트로 작성할 때 타입을 명시하지 않으면 나중에 Props를 확장할 때 어디에 뭘 추가해야 하는지 파악하기 어렵다. 처음부터 인터페이스를 분리해두는 게 낫다.

```tsx
interface FallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  fallbackComponent?: React.ComponentType<FallbackProps>;
  onReset?: () => void;
  onError?: (error: Error, info: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.props.onError?.(error, info);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      const Fallback = this.props.fallbackComponent;
      if (Fallback) {
        return <Fallback error={this.state.error!} resetErrorBoundary={this.reset} />;
      }
      return this.props.fallback ?? <div>오류가 발생했습니다.</div>;
    }
    return this.props.children;
  }
}
```

`getDerivedStateFromError`는 static이라 `this`에 접근하지 못한다. 에러 정보를 상태에 담아서 `render`에서 꺼내 쓰는 방식이어야 한다.

## 어느 에러를 잡고 어느 에러를 잡지 못하나

Error Boundary가 잡는 에러:
- 자식 컴포넌트의 `render` 실행 중 던진 에러
- 생명주기 메서드(`componentDidMount`, `componentDidUpdate` 등) 안에서 던진 에러
- 클래스 컴포넌트의 생성자에서 던진 에러

Error Boundary가 잡지 못하는 에러:
- `setTimeout`, `setInterval` 콜백
- Promise rejection (`fetch`, `async/await`)
- 이벤트 핸들러 (`onClick`, `onChange` 등)
- Error Boundary 컴포넌트 자기 자신 안의 에러

**비동기 에러가 잡히지 않는 이유**는 React의 렌더 사이클과 관계가 없어서다. Error Boundary는 React가 컴포넌트 트리를 렌더링하는 도중에 던진 에러를 잡는 `try/catch`다. `setTimeout` 콜백은 React 렌더 사이클 밖에서 실행되고, Promise rejection도 마찬가지다. React가 감시하는 범위 밖에서 일어나는 일이라 Error Boundary 레이어까지 버블링 자체가 안 된다.

이벤트 핸들러도 마찬가지다. `onClick` 안에서 에러가 터져도 그건 렌더 중이 아니라 DOM 이벤트를 처리하는 중이고, 표준 `try/catch`로 직접 잡아야 한다.

비동기 에러를 억지로 Error Boundary에 넘기는 패턴이 있기는 하다.

```tsx
function AsyncComponent() {
  const [, forceUpdate] = useState(null);

  const handleClick = async () => {
    try {
      await fetchSomething();
    } catch (error) {
      // state 업데이트로 렌더를 트리거하면서 에러를 던지면 잡힌다
      forceUpdate(() => { throw error; });
    }
  };

  return <button onClick={handleClick}>실행</button>;
}
```

쓸 수는 있지만 직관적이지 않고 react-error-boundary 라이브러리의 `useErrorBoundary` 훅이 같은 일을 더 깔끔하게 한다.

## 컴포넌트 계층별 세분화

Error Boundary를 앱 최상단에 하나만 두면 어느 한 컴포넌트가 터질 때 화면 전체가 fallback으로 교체된다. 실제 서비스에서 이건 대부분 과한 반응이다.

세분화 수준을 결정할 때 판단 기준은 "이 영역이 터졌을 때 나머지 영역이 계속 작동해야 하는가"다.

```
AppErrorBoundary          ← 최후 보루. 앱 전체를 날리는 치명적 에러만 여기서 잡는다
├── NavigationErrorBoundary ← nav가 터져도 본문은 살린다
├── PageErrorBoundary       ← 페이지 단위
│   ├── SidebarErrorBoundary
│   └── ContentErrorBoundary
│       ├── ChartErrorBoundary  ← 차트 하나가 터져도 나머지 콘텐츠는 보인다
│       └── TableErrorBoundary
```

차트 라이브러리는 특히 예외 처리가 불안정한 경우가 있어서 컴포넌트 단위로 감싸는 게 안전하다. 데이터가 예상치 못한 형태로 오면 렌더 중 터지는 경우가 생각보다 많다.

페이지 단위 이하로 내릴수록 UX는 좋아지지만 경계 개수가 늘어난다. 실무에서는 보통 앱 전체, 페이지, 독립 위젯(차트·에디터·지도 등) 세 수준으로 구분한다.

## fallback UI 설계

fallback UI가 해야 할 일이 두 가지다. 사용자에게 "지금 이 영역이 동작하지 않는다"는 사실을 알리는 것, 그리고 사용자가 다음에 뭘 할 수 있는지를 보여주는 것.

에러 메시지를 원문 그대로 보여주면 안 된다. 스택 트레이스나 `Cannot read properties of undefined` 같은 메시지는 개발자 외에는 아무 정보도 주지 못하고 오히려 불안감만 준다.

```tsx
function ChartFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="chart-error">
      <p>차트를 불러오지 못했습니다.</p>
      <button onClick={resetErrorBoundary}>다시 시도</button>
    </div>
  );
}
```

reset 버튼이 없는 fallback은 사용자를 막힌 상태에 가둔다. 페이지 새로고침 없이 복구할 경로를 제공한다.

에러 경계 수준에 따라 fallback의 크기도 다르다. 최상단 경계라면 전체 페이지 레이아웃을 그린 에러 페이지, 차트 단위라면 차트 영역 크기에 맞는 간단한 메시지면 충분하다. 전체 화면 fallback을 위젯 단위에 붙이면 레이아웃이 깨진다.

## reset 패턴

에러가 난 뒤 `state.hasError`를 `false`로 되돌리면 자식 컴포넌트를 다시 렌더링한다. 그런데 그냥 리셋하면 같은 에러가 다시 난다. 데이터를 다시 fetch하거나 캐시를 비우는 작업이 같이 일어나야 한다.

`onReset` 콜백에서 상위에서 데이터 재요청을 트리거하는 식으로 쓴다. react-query를 쓴다면 `queryClient.invalidateQueries`를 거기서 호출한다.

`resetKeys` 패턴도 있다. 특정 값이 바뀌면 자동으로 에러 상태를 초기화하는 방식이다. 라우팅이 바뀔 때 에러 상태를 자동으로 지우고 싶다면 `location.pathname`을 resetKey로 넘기면 된다.

```tsx
// react-error-boundary의 resetKeys 방식
<ErrorBoundary
  FallbackComponent={ChartFallback}
  resetKeys={[queryKey]}  // queryKey가 바뀌면 에러 상태 자동 초기화
  onReset={() => queryClient.invalidateQueries(queryKey)}
>
  <Chart />
</ErrorBoundary>
```

## react-error-boundary 라이브러리

클래스 컴포넌트 직접 작성 없이 쓸 수 있고, `useErrorBoundary` 훅으로 비동기 에러도 Error Boundary로 넘길 수 있다.

```tsx
import { ErrorBoundary, useErrorBoundary } from 'react-error-boundary';

function AsyncDataComponent() {
  const { showBoundary } = useErrorBoundary();

  useEffect(() => {
    fetchData()
      .then(setData)
      .catch(showBoundary);  // Promise rejection을 Error Boundary로 넘긴다
  }, []);

  return <div>{data}</div>;
}

function App() {
  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={(error, info) => logError(error, info)}
      onReset={() => queryClient.clear()}
      resetKeys={[currentRoute]}
    >
      <AsyncDataComponent />
    </ErrorBoundary>
  );
}
```

`showBoundary`를 `catch`에 넘기면 비동기 에러를 강제로 렌더 사이클로 밀어 넣는다. 내부적으로 앞서 소개한 `forceUpdate(() => { throw error; })` 패턴과 같은 원리다.

주의할 점은 `withErrorBoundary` HOC다. 컴포넌트를 감싸서 반환하는 형태인데, 이 방식을 쓰면 displayName이 깨져서 React DevTools에서 컴포넌트 이름을 추적하기 어렵다. 가능하면 JSX로 직접 감싸는 편이 디버깅하기 낫다.

## Next.js App Router error.tsx

App Router에서는 `error.tsx` 파일이 내장 Error Boundary 역할을 한다. 별도로 클래스 컴포넌트를 만들 필요 없이 라우트 세그먼트마다 에러 처리를 붙일 수 있다.

```tsx
// app/dashboard/error.tsx
'use client';  // error.tsx는 반드시 Client Component여야 한다

import { useEffect } from 'react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div>
      <p>대시보드를 불러오지 못했습니다.</p>
      <button onClick={reset}>다시 시도</button>
    </div>
  );
}
```

`digest` 필드는 서버 컴포넌트에서 에러가 났을 때 붙는 해시값이다. 서버 측 에러는 클라이언트에 원문이 전달되지 않아서, 이 digest를 서버 로그와 대조해 어떤 에러인지 찾아야 한다.

`reset` 함수를 호출하면 해당 라우트 세그먼트를 다시 렌더링한다. 서버 컴포넌트가 포함된 경우 서버에 재요청이 발생한다. 단순 상태 초기화가 아니라 실제로 다시 fetch가 일어난다.

루트 레이아웃에서 터지는 에러는 `app/error.tsx`가 아니라 `app/global-error.tsx`가 처리한다. `error.tsx`는 레이아웃을 그대로 두고 콘텐츠 영역만 교체하지만, `global-error.tsx`는 루트 레이아웃 전체를 대체하므로 `<html>`, `<body>`를 직접 포함해야 한다.

```tsx
// app/global-error.tsx
'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <h2>앱 전체에 문제가 발생했습니다.</h2>
        <button onClick={reset}>다시 시도</button>
      </body>
    </html>
  );
}
```

## Sentry 연동

`componentDidCatch`에서 `Sentry.captureException`만 호출하면 컴포넌트 스택이 누락된다. `withScope`로 컨텍스트를 묶어야 원인 컴포넌트까지 추적된다.

```tsx
import * as Sentry from '@sentry/react';

componentDidCatch(error: Error, info: React.ErrorInfo) {
  Sentry.withScope((scope) => {
    scope.setTag('boundary', this.props.name ?? 'ErrorBoundary');
    scope.setExtra('componentStack', info.componentStack);
    scope.setLevel('error');
    Sentry.captureException(error);
  });
  this.props.onError?.(error, info);
}
```

`info.componentStack`은 에러가 어느 컴포넌트에서 비롯됐는지 추적하는 핵심 데이터다. Sentry UI에서는 "Component Stack" 탭에 보인다. 이게 없으면 "어느 파일 몇 번째 줄"은 알아도 "React 트리 어디서 터졌는가"는 알 수 없다.

프로덕션 빌드에서 컴포넌트 이름이 minify되면 스택이 `t → n → r` 같은 무의미한 이름으로 나온다. Sentry 소스맵을 연동해야 원래 이름이 복원된다. `@sentry/webpack-plugin` 또는 `@sentry/vite-plugin`을 빌드 파이프라인에 붙이는 작업이 필요하다.

Next.js App Router의 `error.tsx`에서 Sentry를 쓸 때는 `useEffect` 안에서 호출해야 한다. 렌더 중에 직접 호출하면 서버/클라이언트 실행 타이밍이 엇갈려 중복 보고가 생긴다.

```tsx
// app/dashboard/error.tsx
'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error, {
      extra: { digest: error.digest },
    });
  }, [error]);

  return (
    <div>
      <p>문제가 발생했습니다.</p>
      <button onClick={reset}>다시 시도</button>
    </div>
  );
}
```

## 개발 모드 console.error 억제

개발 모드에서 React는 Error Boundary가 잡은 에러도 콘솔에 두 번 출력한다. 첫 번째는 에러가 던져진 시점, 두 번째는 React가 내부적으로 다시 던지는 시점이다. 의도적인 동작이고 프로덕션에서는 일어나지 않는다.

빨간 에러 오버레이도 함께 뜨는데, 오버레이를 닫으면 fallback UI가 보인다. Error Boundary가 제대로 작동하는 중이니 오버레이가 뜨는 게 오류가 아니다.

테스트 코드에서 Error Boundary를 검증할 때 이 콘솔 출력이 노이즈가 되는 경우가 있다. 그럴 때는 테스트 스코프 안에서 `console.error`를 임시로 막는다.

```typescript
describe('ErrorBoundary', () => {
  const originalError = console.error;

  beforeEach(() => {
    console.error = jest.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it('에러 발생 시 fallback을 렌더한다', () => {
    const ThrowingComponent = () => {
      throw new Error('테스트 에러');
    };

    render(
      <ErrorBoundary fallback={<div>에러 화면</div>}>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('에러 화면')).toBeInTheDocument();
  });
});
```

컴포넌트 코드 자체에서 개발 모드 콘솔 출력을 막으려는 시도는 하지 않는 게 낫다. React가 의도적으로 출력하는 것이고, 이걸 막으면 개발 중에 다른 예상치 못한 에러도 콘솔에서 안 보이게 될 수 있다.

## Suspense와 함께 쓸 때

Suspense와 Error Boundary는 같이 쓰는 경우가 많다. Suspense는 로딩 상태를, Error Boundary는 에러 상태를 처리한다. 순서는 Error Boundary가 바깥이어야 한다. Suspense가 바깥이면 에러 상태에서 Suspense의 fallback이 보이는 경우가 생긴다.

```tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <Suspense fallback={<Spinner />}>
    <LazyComponent />
  </Suspense>
</ErrorBoundary>
```

React 18의 서버 컴포넌트 환경에서 Error Boundary는 클라이언트 컴포넌트 경계 안에 있어야 한다. `'use client'`가 붙은 파일에서 정의하거나 import해야 한다.
