---
title: Error Boundary 테스트
tags: [frontend, javascript, typescript, testing]
updated: 2026-09-14
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

## jest에서 console.error 억제

React 개발 모드는 Error Boundary가 잡은 에러를 콘솔에 두 번 출력한다. 첫 번째는 에러가 발생한 시점, 두 번째는 React가 내부적으로 다시 던지는 시점이다. 여기에 `act(...)` 관련 경고까지 겹치면 테스트 출력이 에러 로그로 가득 찬다. 실제 의미 있는 테스트 실패 메시지가 묻히는 문제가 생긴다.

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
