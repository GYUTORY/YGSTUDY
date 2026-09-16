---
title: Error Boundary 테스트
tags: [frontend, javascript, typescript, testing]
updated: 2026-09-16
---

## ThrowError 헬퍼 컴포넌트

Error Boundary 테스트는 렌더 중 에러를 발생시켜야 한다. 이벤트 핸들러나 `useEffect` 안의 에러는 Error Boundary가 잡지 않으니 의미 없다. 헬퍼 컴포넌트가 렌더 타이밍에 에러를 던지도록 만들어야 실제 동작을 검증한다.

두 가지 형태로 쓴다.

항상 던지는 형태:

```tsx
const ThrowOnRender = () => {
  throw new Error('렌더 에러');
  return null; // TypeScript 타입 추론용
};
```

제어 가능한 형태:

```tsx
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('제어 가능한 에러');
  return <div>정상 렌더</div>;
};
```

제어 가능한 형태는 reset 테스트에서 필수다. reset 후 자식 컴포넌트가 정상적으로 다시 렌더되는지 검증하려면, 에러를 끄고 다시 렌더했을 때 fallback이 사라지는 걸 확인해야 한다. 항상 던지는 컴포넌트로는 이 시나리오를 테스트할 수 없다.

`test-utils/` 나 `__tests__/helpers.tsx` 에 한 번 모아두면 파일마다 다시 정의하는 수고를 덜 수 있다.

## console.error 억제

React 개발 모드는 Error Boundary가 잡은 에러를 콘솔에 두 번 출력한다. 첫 번째는 에러가 발생한 시점, 두 번째는 React가 내부적으로 다시 던지는 시점이다. 여기에 `act(...)` 관련 경고까지 겹치면 테스트 출력이 에러 로그로 가득 찬다. 실제 의미 있는 테스트 실패 메시지가 묻히는 문제가 생긴다.

### Jest

가장 단순한 방법은 `beforeEach`에서 `console.error`를 mock으로 교체하는 것이다:

```typescript
describe('ErrorBoundary', () => {
  const originalError = console.error;

  beforeEach(() => {
    console.error = jest.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });
});
```

이 방법은 모든 콘솔 에러를 막는다. 테스트 코드 자체의 실수로 나온 에러까지 삼켜버린다.

선택적으로 억제하는 방식이 낫다:

```typescript
describe('ErrorBoundary', () => {
  const originalError = console.error;

  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
      const msg = typeof args[0] === 'string' ? args[0] : '';
      if (
        msg.includes('The above error occurred in the') ||
        msg.includes('act(') ||
        msg.includes('Warning: An update to')
      ) {
        return;
      }
      originalError(...args);
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });
});
```

`jest.restoreAllMocks()` 는 `afterEach` 에 두는 편이 안전하다. `afterAll` 에 두면 같은 `describe` 블록 안 후속 테스트들이 spy가 살아있는 상태에서 실행되는 경우가 생긴다.

### Vitest

Vitest에서 구조는 비슷하지만 `jest` 대신 `vi` API를 쓴다. 한 가지 주의할 게 있다 — spy 안에서 `console.error` 를 다시 부르면 spy가 자기 자신을 재귀 호출하는 구조가 된다. `originalError` 를 spy 등록 전에 반드시 저장해둬야 한다:

```typescript
import { vi, beforeEach, afterEach, describe } from 'vitest';

describe('ErrorBoundary', () => {
  const originalError = console.error.bind(console);

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
      const msg = typeof args[0] === 'string' ? args[0] : '';
      if (
        msg.includes('The above error occurred in the') ||
        msg.includes('act(') ||
        msg.includes('Warning: An update to') ||
        msg.includes('Consider adding an error boundary')
      ) {
        return;
      }
      originalError(...args);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
});
```

React 18 + Vitest 조합에서 `act` 경고가 Jest보다 자주 나온다. `@testing-library/react` v14 이상은 내부적으로 `act` 를 감싸지만, 커스텀 이벤트를 직접 디스패치하거나 비동기 훅을 수동으로 다룰 때는 `act` 로 명시적으로 감싸야 경고가 사라진다.

`vite.config.ts` 에 `test.globals: true` 를 설정하면 `vi`, `describe`, `it`, `expect` 를 import 없이 쓸 수 있다. Jest와 동일한 느낌으로 작성할 수 있고, 이 경우 `jest.fn()` 자리에 `vi.fn()` 만 바꾸면 된다.

## fallback UI 검증

기본 검증은 에러 발생 후 fallback이 DOM에 나타나는지 확인하는 것이다:

```tsx
import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

it('에러 발생 시 fallback을 렌더한다', () => {
  render(
    <ErrorBoundary fallback={<div>오류가 발생했습니다</div>}>
      <ThrowOnRender />
    </ErrorBoundary>
  );

  expect(screen.getByText('오류가 발생했습니다')).toBeInTheDocument();
  expect(screen.queryByText('정상 렌더')).not.toBeInTheDocument();
});
```

`FallbackComponent`를 쓰는 경우 에러 객체가 props로 제대로 전달되는지 검증한다:

```tsx
it('FallbackComponent에 error 객체를 전달한다', () => {
  const FallbackComponent = ({ error }: { error: Error }) => (
    <div>{error.message}</div>
  );

  render(
    <ErrorBoundary FallbackComponent={FallbackComponent}>
      <ThrowOnRender />
    </ErrorBoundary>
  );

  expect(screen.getByText('렌더 에러')).toBeInTheDocument();
});
```

`onError` 콜백이 있다면 호출 여부와 인자를 함께 검증한다:

```tsx
it('에러 발생 시 onError 콜백을 호출한다', () => {
  const onError = jest.fn();

  render(
    <ErrorBoundary fallback={<div>에러</div>} onError={onError}>
      <ThrowOnRender />
    </ErrorBoundary>
  );

  expect(onError).toHaveBeenCalledTimes(1);
  expect(onError).toHaveBeenCalledWith(
    expect.any(Error),
    expect.objectContaining({ componentStack: expect.any(String) })
  );
});
```

`componentStack` 은 `React.ErrorInfo` 타입의 두 번째 인자다. Sentry 같은 에러 추적 도구에서 컴포넌트 트리 어디서 에러가 났는지 추적하는 데 이 값을 쓴다. 전달 여부를 검증해두는 게 나중에 도움이 된다.

## reset 테스트

reset 테스트에서 함정이 있다. Error Boundary가 reset된 후 자식 컴포넌트를 다시 렌더하는데, 자식이 여전히 에러를 던지면 또 fallback으로 돌아간다. "reset이 됐는데 fallback이 그대로다"는 상황이 생기는데, Error Boundary 구현 문제가 아니라 자식 컴포넌트가 다시 에러를 던지는 것이다.

`onReset` 콜백만 검증하는 테스트로 이 복잡성을 피할 수 있다:

```tsx
it('reset 버튼 클릭 시 onReset 콜백을 호출한다', async () => {
  const onReset = jest.fn();
  const FallbackWithReset = ({ resetErrorBoundary }: { resetErrorBoundary: () => void }) => (
    <button onClick={resetErrorBoundary}>다시 시도</button>
  );

  render(
    <ErrorBoundary FallbackComponent={FallbackWithReset} onReset={onReset}>
      <ThrowOnRender />
    </ErrorBoundary>
  );

  await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));

  expect(onReset).toHaveBeenCalledTimes(1);
});
```

reset 후 정상 상태로 복구되는 전체 흐름을 검증하려면 제어 가능한 헬퍼가 필요하다:

```tsx
it('reset 후 에러가 해소되면 자식 컴포넌트를 다시 렌더한다', async () => {
  let shouldThrow = true;

  const ControlledThrower = () => {
    if (shouldThrow) throw new Error('에러');
    return <div>정상 상태</div>;
  };

  const FallbackWithReset = ({ resetErrorBoundary }: { resetErrorBoundary: () => void }) => (
    <button onClick={resetErrorBoundary}>다시 시도</button>
  );

  render(
    <ErrorBoundary FallbackComponent={FallbackWithReset}>
      <ControlledThrower />
    </ErrorBoundary>
  );

  expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument();

  shouldThrow = false;
  await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));

  expect(screen.getByText('정상 상태')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument();
});
```

`shouldThrow` 를 클로저로 참조하는 방식이다. `rerender` 로는 Error Boundary의 내부 에러 상태를 초기화할 수 없다. `rerender` 를 호출해도 Error Boundary가 이미 에러 상태에 있으면 fallback을 그대로 보여준다.

`resetKeys` 를 구현한 경우에는 prop 변경으로 자동 reset되는 동작을 검증할 수 있다. 단, resetKeys 변경으로 reset이 일어나면 자식이 다시 렌더되고, 자식이 여전히 에러를 던지면 즉시 fallback으로 돌아간다. "reset됐다가 다시 fallback으로"가 의도된 흐름이다. reset 자체가 일어났다는 사실은 `onReset` 콜백으로 검증하는 편이 명확하다:

```tsx
it('resetKeys 변경 시 onReset 콜백을 호출한다', () => {
  const onReset = jest.fn();
  const FallbackWithReset = ({ resetErrorBoundary }: { resetErrorBoundary: () => void }) => (
    <button onClick={resetErrorBoundary}>다시 시도</button>
  );

  const { rerender } = render(
    <ErrorBoundary
      FallbackComponent={FallbackWithReset}
      onReset={onReset}
      resetKeys={['key1']}
    >
      <ThrowOnRender />
    </ErrorBoundary>
  );

  rerender(
    <ErrorBoundary
      FallbackComponent={FallbackWithReset}
      onReset={onReset}
      resetKeys={['key2']}
    >
      <ThrowOnRender />
    </ErrorBoundary>
  );

  expect(onReset).toHaveBeenCalledTimes(1);
});
```

## useErrorBoundary 훅 테스트

`react-error-boundary` 의 `useErrorBoundary` 는 비동기 에러를 Error Boundary로 넘기는 훅이다. 이 훅을 쓰는 컴포넌트를 테스트할 때는 반드시 `ErrorBoundary` 로 감싸서 렌더해야 한다. `ErrorBoundary` 컨텍스트 없이 `showBoundary` 를 호출하면 에러가 발생한다.

```tsx
import { ErrorBoundary, useErrorBoundary } from 'react-error-boundary';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

function DataFetcher({ fetchFn }: { fetchFn: () => Promise<string> }) {
  const { showBoundary } = useErrorBoundary();
  const [data, setData] = useState<string | null>(null);

  const handleFetch = async () => {
    try {
      const result = await fetchFn();
      setData(result);
    } catch (err) {
      showBoundary(err);
    }
  };

  return (
    <div>
      <button onClick={handleFetch}>데이터 로드</button>
      {data && <span>{data}</span>}
    </div>
  );
}

it('fetch 실패 시 ErrorBoundary의 fallback을 렌더한다', async () => {
  const failingFetch = jest.fn().mockRejectedValue(new Error('서버 에러'));

  render(
    <ErrorBoundary fallback={<div>fetch 실패</div>}>
      <DataFetcher fetchFn={failingFetch} />
    </ErrorBoundary>
  );

  await userEvent.click(screen.getByRole('button', { name: '데이터 로드' }));

  expect(await screen.findByText('fetch 실패')).toBeInTheDocument();
});
```

`screen.findByText` 를 쓰는 이유는 `showBoundary` 호출과 fallback 렌더가 비동기로 진행되기 때문이다. `getByText` 를 바로 쓰면 fallback이 DOM에 나타나기 전에 검증이 실행된다.

훅을 직접 테스트하고 싶다면 `renderHook` 에 `wrapper` 를 제공해야 한다:

```tsx
import { renderHook } from '@testing-library/react';
import { ErrorBoundary, useErrorBoundary } from 'react-error-boundary';

it('showBoundary 함수를 반환한다', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <ErrorBoundary fallback={<div>에러</div>}>{children}</ErrorBoundary>
  );

  const { result } = renderHook(() => useErrorBoundary(), { wrapper });

  expect(typeof result.current.showBoundary).toBe('function');
});
```

`wrapper` 없이 `renderHook(() => useErrorBoundary())` 만 쓰면 `ErrorBoundary` 컨텍스트가 없어서 훅이 정상 작동하지 않는다.

## 중첩 Error Boundary

Error Boundary를 중첩으로 사용하면 안쪽 Boundary가 에러를 먼저 잡는다. 바깥 Boundary는 안쪽 Boundary 트리 안에서 발생한 에러를 받지 못한다. 어느 Boundary가 잡는지 검증하는 테스트가 필요한 경우는 보통 두 가지다 — Boundary별로 다른 fallback을 보여주는 구조이거나, 에러 타입에 따라 상위로 전파되는지 확인하는 경우다.

안쪽 Boundary가 잡는지 검증:

```tsx
it('안쪽 Boundary가 자식 에러를 잡는다', () => {
  render(
    <ErrorBoundary fallback={<div>바깥 에러</div>}>
      <ErrorBoundary fallback={<div>안쪽 에러</div>}>
        <ThrowOnRender />
      </ErrorBoundary>
    </ErrorBoundary>
  );

  expect(screen.getByText('안쪽 에러')).toBeInTheDocument();
  expect(screen.queryByText('바깥 에러')).not.toBeInTheDocument();
});
```

페이지 일부만 Error Boundary로 감싸서, 한 영역에서 에러가 나도 나머지는 정상 렌더되는 구조도 검증할 수 있다:

```tsx
it('에러 발생 영역만 fallback을 렌더하고 나머지는 정상 렌더한다', () => {
  render(
    <div>
      <ErrorBoundary fallback={<div>위젯 에러</div>}>
        <ThrowOnRender />
      </ErrorBoundary>
      <div>사이드바</div>
    </div>
  );

  expect(screen.getByText('위젯 에러')).toBeInTheDocument();
  expect(screen.getByText('사이드바')).toBeInTheDocument();
});
```

안쪽 Boundary가 에러를 다시 던지거나 특정 타입만 처리하도록 구현한 경우에는 바깥 Boundary까지 전파된다. 이 케이스는 에러 타입별 분기 섹션에서 다룬다.

## Suspense와 Error Boundary 조합

`<Suspense>` 와 `<ErrorBoundary>` 를 함께 쓰는 구조는 두 상태를 모두 테스트해야 한다 — 로딩 중(Suspense fallback)과 에러 발생(ErrorBoundary fallback). 이 두 상태는 서로 다른 조건에서 나타나고, 각각 제어하는 방식도 다르다.

로딩 상태는 Promise가 resolve되지 않은 시점을 잡아야 하고, 에러 상태는 Promise가 reject되거나 컴포넌트가 throw하는 시점이다.

```tsx
// Promise 상태를 외부에서 제어하는 테스트용 리소스
function createSuspenseResource<T>(promise: Promise<T>) {
  let status: 'pending' | 'success' | 'error' = 'pending';
  let result: T;
  let error: unknown;

  promise.then(
    (data) => { status = 'success'; result = data; },
    (err) => { status = 'error'; error = err; }
  );

  return {
    read() {
      if (status === 'pending') throw promise;
      if (status === 'error') throw error;
      return result!;
    },
  };
}

function DataComponent({ resource }: { resource: ReturnType<typeof createSuspenseResource<string>> }) {
  const data = resource.read();
  return <div>{data}</div>;
}
```

로딩 상태 검증:

```tsx
it('데이터 로딩 중에는 Suspense fallback을 보여준다', () => {
  const resource = createSuspenseResource(new Promise<string>(() => {})); // 절대 resolve되지 않는다

  render(
    <ErrorBoundary fallback={<div>에러 발생</div>}>
      <Suspense fallback={<div>로딩 중</div>}>
        <DataComponent resource={resource} />
      </Suspense>
    </ErrorBoundary>
  );

  expect(screen.getByText('로딩 중')).toBeInTheDocument();
  expect(screen.queryByText('에러 발생')).not.toBeInTheDocument();
});
```

에러 상태 검증:

```tsx
it('데이터 로딩 실패 시 ErrorBoundary fallback을 보여준다', async () => {
  const resource = createSuspenseResource(Promise.reject(new Error('로딩 실패')));

  render(
    <ErrorBoundary fallback={<div>에러 발생</div>}>
      <Suspense fallback={<div>로딩 중</div>}>
        <DataComponent resource={resource} />
      </Suspense>
    </ErrorBoundary>
  );

  expect(await screen.findByText('에러 발생')).toBeInTheDocument();
  expect(screen.queryByText('로딩 중')).not.toBeInTheDocument();
});
```

`findByText` 를 쓰는 이유는 Promise reject 이후 React가 에러를 처리하고 fallback을 렌더하는 타이밍이 비동기라서다.

로딩 완료 후 데이터가 정상 렌더되는 흐름도 검증해두는 편이 좋다:

```tsx
it('데이터 로딩 완료 후 콘텐츠를 렌더한다', async () => {
  const resource = createSuspenseResource(Promise.resolve('콘텐츠'));

  render(
    <ErrorBoundary fallback={<div>에러 발생</div>}>
      <Suspense fallback={<div>로딩 중</div>}>
        <DataComponent resource={resource} />
      </Suspense>
    </ErrorBoundary>
  );

  expect(await screen.findByText('콘텐츠')).toBeInTheDocument();
  expect(screen.queryByText('로딩 중')).not.toBeInTheDocument();
  expect(screen.queryByText('에러 발생')).not.toBeInTheDocument();
});
```

React 18의 `use` 훅을 쓰는 컴포넌트도 구조는 같다. `use(promise)` 가 내부적으로 Promise를 throw하는 방식이라 위 패턴이 그대로 적용된다.

## 에러 타입별 분기

특정 에러만 처리하고 나머지는 상위 Boundary로 전파하는 구현을 테스트할 때는 두 케이스를 모두 검증해야 한다 — 처리 대상 에러와 전파되는 에러.

`getDerivedStateFromError` 에서 에러 타입을 확인하고 해당하지 않으면 re-throw하는 구현:

```tsx
class NetworkErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    if (error.name === 'NetworkError') {
      return { hasError: true };
    }
    // NetworkError가 아니면 상위 Boundary로 전파
    throw error;
  }

  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}
```

`getDerivedStateFromError` 에서 re-throw하면 React가 그 에러를 상위 트리에서 처리한다. 이 동작을 검증한다:

```tsx
class NetworkError extends Error {
  name = 'NetworkError' as const;
}

it('NetworkError는 NetworkErrorBoundary가 잡는다', () => {
  const ThrowNetworkError = () => { throw new NetworkError('네트워크 실패'); return null; };

  render(
    <ErrorBoundary fallback={<div>상위 에러</div>}>
      <NetworkErrorBoundary fallback={<div>네트워크 에러</div>}>
        <ThrowNetworkError />
      </NetworkErrorBoundary>
    </ErrorBoundary>
  );

  expect(screen.getByText('네트워크 에러')).toBeInTheDocument();
  expect(screen.queryByText('상위 에러')).not.toBeInTheDocument();
});

it('일반 에러는 상위 Boundary로 전파된다', () => {
  render(
    <ErrorBoundary fallback={<div>상위 에러</div>}>
      <NetworkErrorBoundary fallback={<div>네트워크 에러</div>}>
        <ThrowOnRender />
      </NetworkErrorBoundary>
    </ErrorBoundary>
  );

  expect(screen.getByText('상위 에러')).toBeInTheDocument();
  expect(screen.queryByText('네트워크 에러')).not.toBeInTheDocument();
});
```

`getDerivedStateFromError` 에서 re-throw하는 패턴은 React 공식 문서에는 없다. 동작하는 건 React의 에러 처리 플로우가 static 메서드에서 throw된 에러를 catch해서 다시 상위 Boundary에 전파하는 방식으로 구현됐기 때문이다.

`componentDidCatch` 기반으로 전파를 구현하는 경우, 상태가 이미 `hasError: true` 로 바뀐 뒤에 실행되므로 상태를 롤백해야 한다:

```tsx
componentDidCatch(error: Error, info: React.ErrorInfo) {
  if (error.name !== 'NetworkError') {
    this.setState({ hasError: false });
    throw error;
  }
  this.props.onError?.(error, info);
}
```

이 방식은 `getDerivedStateFromError` 와 `componentDidCatch` 사이에 한 렌더가 끼어들 수 있다. fallback이 잠깐 보였다 사라지는 플래시가 발생하는 경우가 있고, React strict mode에서는 더 두드러진다.

## Next.js App Router error.tsx

Next.js App Router의 `error.tsx` 는 자동으로 Client Component로 처리된다. React Error Boundary를 내부적으로 쓰지만, 직접 구현한 ErrorBoundary와 다른 부분이 하나 있다 — `reset` prop이 `router.refresh()` 를 호출한다. `react-error-boundary` 의 `resetErrorBoundary` 처럼 자식 컴포넌트를 unmount/mount하는 게 아니라, Next.js가 서버 컴포넌트 트리를 다시 패치하는 방식이다.

`error.tsx` 컴포넌트 시그니처:

```tsx
'use client';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <h2>문제가 발생했습니다</h2>
      <p>{error.message}</p>
      <button onClick={reset}>다시 시도</button>
    </div>
  );
}
```

`digest` 필드는 서버에서 발생한 에러를 클라이언트에 노출하지 않을 때 붙는 해시값이다. 서버 컴포넌트에서 던진 에러 메시지는 클라이언트에 전달되지 않고, `digest` 만 온다. 클라이언트에서 `error.message` 를 UI에 노출하는 코드는 서버 에러에 대해서는 빈 문자열을 출력하게 된다.

`error.tsx` 를 단위 테스트로 검증할 때는 컴포넌트 자체만 분리해서 렌더한다. `reset` 이 직접 전달되는 함수라 실제 Router 동작과 무관하게 테스트할 수 있다:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorPage from './error';

it('에러 메시지를 렌더한다', () => {
  const error = new Error('서버 오류');
  const reset = jest.fn();

  render(<ErrorPage error={error} reset={reset} />);

  expect(screen.getByText('서버 오류')).toBeInTheDocument();
});

it('다시 시도 클릭 시 reset 함수를 호출한다', async () => {
  const error = new Error('서버 오류');
  const reset = jest.fn();

  render(<ErrorPage error={error} reset={reset} />);

  await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));

  expect(reset).toHaveBeenCalledTimes(1);
});

it('digest가 있는 에러는 일반 메시지를 보여준다', () => {
  // 서버 에러는 message가 비어있고 digest만 온다
  const error = Object.assign(new Error(''), { digest: 'abc123' });
  const reset = jest.fn();

  render(<ErrorPage error={error} reset={reset} />);

  expect(screen.getByText('문제가 발생했습니다')).toBeInTheDocument();
});
```

`reset` 이 실제로 `router.refresh()` 를 호출하는지 통합 수준에서 검증하려면 `next/navigation` 을 mock해야 한다:

```typescript
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    refresh: jest.fn(),
  }),
}));
```

실제 App Router 통합 테스트는 `@playwright/test` 기반 E2E 테스트로 하는 편이 낫다. Jest 환경에서 서버 컴포넌트 렌더를 시뮬레이션하는 건 설정 비용이 높고, 테스트가 Next.js 내부 구현에 결합되는 문제가 있다.

`error.tsx` 에서 `useEffect` 로 에러를 Sentry에 리포팅하는 패턴이 있다:

```tsx
useEffect(() => {
  reportError(error);
}, [error]);
```

`reportError` 를 mock하고 호출 여부를 검증할 때는 `waitFor` 로 감싸야 한다. `useEffect` 는 렌더 후 비동기로 실행되므로 렌더 직후 바로 검증하면 아직 호출되지 않은 상태일 수 있다:

```tsx
it('에러 발생 시 reportError를 호출한다', async () => {
  const reportError = jest.fn();
  const error = new Error('서버 오류');

  render(<ErrorPage error={error} reset={jest.fn()} reportError={reportError} />);

  await waitFor(() => {
    expect(reportError).toHaveBeenCalledWith(error);
  });
});
```
