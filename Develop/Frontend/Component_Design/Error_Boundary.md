---
title: Error Boundary
tags: [frontend, javascript, react]
updated: 2026-09-14
---

## 클래스 컴포넌트여야 하는 이유

Error Boundary는 `getDerivedStateFromError`와 `componentDidCatch` 두 라이프사이클 메서드로 작동한다. 함수형 컴포넌트에는 이 두 메서드를 대체하는 훅이 없어서, React 18 기준으로도 Error Boundary 자체는 반드시 클래스 컴포넌트로 작성해야 한다.

`getDerivedStateFromError`는 렌더 단계에서 호출되고 상태를 반환해서 fallback UI가 뭘 보여줄지 결정한다. `componentDidCatch`는 커밋 단계에서 호출되고 에러 로깅에 쓴다. 둘의 역할이 다르다.

```tsx
class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // info.componentStack에 어느 컴포넌트에서 터졌는지 스택이 들어온다
    logErrorToService(error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? <div>오류가 발생했습니다.</div>;
    }
    return this.props.children;
  }
}
```

`getDerivedStateFromError`는 static이라 `this`에 접근하지 못한다. 에러 정보를 상태에 담아서 `render`에서 꺼내 쓰는 식으로 한다.

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

```tsx
class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      const Fallback = this.props.fallbackComponent;
      return <Fallback error={this.state.error!} resetErrorBoundary={this.reset} />;
    }
    return this.props.children;
  }
}
```

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

## 프로덕션에서 실제로 쓸 때

에러가 났을 때 `componentDidCatch`의 `info.componentStack`은 컴포넌트 이름이 minify되어 있으면 읽기 어렵다. Sentry 같은 에러 트래킹 도구와 연동할 때 소스맵이 있어야 스택이 읽힌다.

개발 모드에서 React는 Error Boundary가 잡은 에러도 콘솔에 출력한다. 의도적인 동작이다. 프로덕션에서는 콘솔 출력이 없다. 개발 중에 Error Boundary가 작동하는데 빨간 에러 오버레이가 뜨는 건 정상이다. 오버레이를 닫으면 fallback UI가 보인다.

Suspense와 Error Boundary는 같이 쓰는 경우가 많다. Suspense는 로딩 상태를, Error Boundary는 에러 상태를 처리한다. 순서는 Error Boundary가 바깥이어야 한다. Suspense가 바깥이면 에러 상태에서 Suspense의 fallback이 보이는 경우가 생긴다.

```tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <Suspense fallback={<Spinner />}>
    <LazyComponent />
  </Suspense>
</ErrorBoundary>
```

React 18의 서버 컴포넌트 환경에서 Error Boundary는 클라이언트 컴포넌트 경계 안에 있어야 한다. `'use client'`가 붙은 파일에서 정의하거나 import해야 한다.
