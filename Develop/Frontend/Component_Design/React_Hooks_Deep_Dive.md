---
title: React Hooks 깊이 파기
tags: [frontend, javascript, typescript]
updated: 2026-08-26
---

## 훅을 쓰면 생기는 문제들

훅은 클래스 컴포넌트 시절보다 코드가 짧아지는 대신, 클로저와 의존성 배열 때문에 생기는 버그가 전혀 다른 형태로 나타난다. 겉으로는 작동하는 것처럼 보이다가 특정 조건에서 조용히 틀린 값을 쓰는 경우가 많다. 에러가 던져지는 게 아니라 그냥 오래된 값을 쓰는 거라 로그도 없고 찾기가 어렵다.

---

## useEffect 의존성 배열

의존성 배열에서 가장 많이 틀리는 건 "무엇을 넣어야 하나"가 아니라 "왜 넣어야 하는지"를 모르는 경우다.

useEffect 안에서 참조하는 값은 전부 의존성 배열에 들어가야 한다. 컴포넌트가 렌더링될 때마다 새로운 클로저가 생성되는데, 의존성 배열은 "이 클로저를 언제 새로 만들 것인지"를 결정한다. 배열에서 빠진 값이 있으면 이전 렌더의 클로저가 오래된 값을 계속 들고 있게 된다.

```typescript
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      // 의존성 배열이 []이면 count는 항상 0이다
      // 인터벌 콜백이 첫 렌더 시점의 클로저를 계속 쓰기 때문
      setCount(count + 1);
    }, 1000);
    return () => clearInterval(id);
  }, []); // count를 빠뜨린 경우

  return <div>{count}</div>;
}
```

이 코드는 화면에 숫자가 올라가는 것처럼 보이지 않는다. `count + 1`이 계속 `0 + 1 = 1`을 반환해서 1에서 멈춘다.

해결 방법은 두 가지다. `count`를 의존성 배열에 넣거나, 상태 업데이트를 함수형으로 바꾸는 것이다.

```typescript
// 방법 1: count를 의존성에 추가 (인터벌이 매번 재생성됨)
useEffect(() => {
  const id = setInterval(() => {
    setCount(count + 1);
  }, 1000);
  return () => clearInterval(id);
}, [count]);

// 방법 2: 함수형 업데이트 (인터벌 재생성 없음)
useEffect(() => {
  const id = setInterval(() => {
    setCount(prev => prev + 1);
  }, 1000);
  return () => clearInterval(id);
}, []);
```

setInterval처럼 지속적으로 실행되는 경우에는 방법 2가 맞다. 방법 1은 인터벌이 1초마다 재생성되므로 타이밍이 틀어질 수 있다.

### 객체와 배열이 의존성에 들어갈 때

객체나 배열을 의존성 배열에 넣으면 렌더링마다 새로운 참조가 생기기 때문에 useEffect가 매번 실행된다.

```typescript
function Component({ config }) {
  useEffect(() => {
    fetchData(config);
  }, [config]); // config가 매번 새 객체면 이 effect는 매 렌더마다 실행됨
}

// 부모에서
<Component config={{ timeout: 5000 }} /> // 렌더링마다 새 객체 생성
```

`{ timeout: 5000 }`은 렌더링마다 새로운 객체 참조를 만든다. 자바스크립트에서 `{} === {}` 는 `false`다. 이 경우 `useMemo`로 config를 메모이제이션하거나, 필요한 값만 분해해서 의존성에 넣는 게 낫다.

```typescript
// config 객체 대신 필요한 값만 받는 구조
function Component({ timeout }) {
  useEffect(() => {
    fetchData({ timeout });
  }, [timeout]); // 원시값은 값 비교가 됨
}
```

---

## Stale Closure — 오래된 클로저 문제

클로저 stale 문제는 useEffect뿐 아니라 이벤트 핸들러, 타이머, 비동기 콜백 어디서나 생긴다. 패턴 자체를 이해해두지 않으면 비슷한 버그를 반복해서 만나게 된다.

```typescript
function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  const search = async () => {
    const data = await fetchSearch(query);
    // 비동기 작업이 끝났을 때 query가 바뀌어 있을 수 있다
    // 하지만 이 클로저는 search를 호출한 시점의 query를 들고 있음
    setResults(data);
  };

  return (
    <input
      value={query}
      onChange={e => setQuery(e.target.value)}
      onKeyDown={e => e.key === 'Enter' && search()}
    />
  );
}
```

사용자가 'react'를 입력하고 엔터를 치는 사이에 'typescript'로 query를 바꾸면, 응답이 'react' 결과를 가져와도 `setResults`가 그대로 실행된다. 레이스 컨디션이다.

useRef로 최신 값을 항상 추적하거나, 요청마다 abort controller를 써서 이전 요청을 취소하는 방식으로 처리한다.

```typescript
function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const abortRef = useRef<AbortController | null>(null);

  const search = async (currentQuery: string) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const data = await fetchSearch(currentQuery, { signal: abortRef.current.signal });
      setResults(data);
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
    }
  };

  return (
    <input
      value={query}
      onChange={e => setQuery(e.target.value)}
      onKeyDown={e => e.key === 'Enter' && search(query)}
    />
  );
}
```

---

## useCallback과 useMemo 남용

"렌더링 최적화를 위해 useCallback을 써야 한다"는 말을 많이 듣는데, 실제로 useCallback 자체가 비용이 있다. 의존성 비교 비용 + 메모이제이션된 함수를 메모리에 유지하는 비용이 발생한다. 렌더링 비용이 이 비용보다 작으면 useCallback이 오히려 느리게 만든다.

useCallback이 실제로 의미 있는 경우는 두 가지다.

**자식 컴포넌트에 함수를 props로 넘기는데 그 자식이 React.memo로 감싸져 있는 경우.** React.memo는 props의 얕은 비교를 한다. 함수는 렌더링마다 새로 생성되므로 useCallback 없이는 React.memo가 무의미해진다.

**useEffect의 의존성 배열에 함수가 들어가는 경우.** 함수가 매번 새로 생성되면 effect가 매 렌더마다 실행된다.

```typescript
// 이건 useMemo가 없어도 되는 경우
const filteredList = useMemo(
  () => items.filter(item => item.active),
  [items]
);
// items 배열이 바뀌지 않는 한 filter 실행 자체가 충분히 빠름
// 그 비용이 useMemo 관리 비용보다 작을 수 있음

// 이건 useMemo가 의미 있는 경우
const processedData = useMemo(
  () => heavyComputation(largeDataset),
  [largeDataset]
);
// heavyComputation이 수백 ms 걸리는 경우
```

프로파일링 없이 useMemo와 useCallback을 코드 전체에 뿌리는 건 권장하지 않는다. React DevTools의 Profiler 탭에서 실제로 느린 컴포넌트를 찾아서 적용하는 게 맞다.

---

## useRef의 실제 용도

useRef는 DOM 접근에만 쓰는 도구라고 알고 있는 경우가 많은데, 렌더링 사이에 값을 유지하는 용도가 실무에서 더 자주 쓰인다.

useState와 useRef의 차이는 명확하다. `setState`를 호출하면 리렌더링이 발생한다. `ref.current`를 바꾸면 리렌더링이 없다.

### 렌더링과 무관하게 값을 유지해야 할 때

```typescript
function VideoPlayer() {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const play = () => {
    setIsPlaying(true);
    intervalRef.current = setInterval(() => {
      // 프레임 업데이트 로직
    }, 16);
  };

  const pause = () => {
    setIsPlaying(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // intervalRef.current는 상태가 아님
  // 렌더링에 영향 없고, 렌더링이 일어나도 값이 유지됨
}
```

타이머 ID, WebSocket 인스턴스, 이전 렌더의 props 값 등을 저장할 때 useRef를 쓴다. 이 값들은 화면에 표시할 필요가 없고 단지 로직에서 참조만 필요한 경우다.

### 이전 값 추적

```typescript
function Component({ value }) {
  const prevValueRef = useRef(value);

  useEffect(() => {
    if (prevValueRef.current !== value) {
      console.log(`${prevValueRef.current} -> ${value}`);
      prevValueRef.current = value;
    }
  });

  return <div>{value}</div>;
}
```

`useEffect`의 의존성 배열 없이 매 렌더마다 실행하고, ref로 이전 값을 들고 있는 패턴이다. useState로 이전 값을 저장하면 그 setState가 또 리렌더링을 발생시키는 루프가 생길 수 있다.

### DOM 접근

```typescript
function FocusInput() {
  const inputRef = useRef<HTMLInputElement>(null);

  const focusInput = () => {
    inputRef.current?.focus();
  };

  return (
    <>
      <input ref={inputRef} />
      <button onClick={focusInput}>포커스</button>
    </>
  );
}
```

서드파티 라이브러리가 DOM 요소를 직접 필요로 하거나, 애니메이션 라이브러리를 쓸 때 DOM 노드에 직접 접근해야 하는 경우가 있다. 그 외에 스크롤 위치 제어, 동영상 플레이어 제어 같은 명령형 API를 써야 할 때 ref가 필요하다.

---

## useLayoutEffect vs useEffect

두 훅의 차이는 실행 타이밍이다.

`useEffect`는 브라우저가 화면을 그린 후에 실행된다. 비동기에 가깝게 동작한다.

`useLayoutEffect`는 DOM 업데이트 직후, 브라우저가 화면을 그리기 전에 실행된다. 동기적으로 실행되므로 여기서 긴 작업을 하면 화면이 버벅인다.

```typescript
function Tooltip({ targetRef, content }) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  // useEffect를 쓰면 툴팁이 잘못된 위치에 잠깐 보였다가 이동하는 깜박임이 생김
  useLayoutEffect(() => {
    const target = targetRef.current;
    const tooltip = tooltipRef.current;
    if (!target || !tooltip) return;

    const rect = target.getBoundingClientRect();
    setPosition({
      top: rect.bottom + window.scrollY,
      left: rect.left + window.scrollX,
    });
  }, [targetRef]);

  return (
    <div
      ref={tooltipRef}
      style={{ position: 'absolute', top: position.top, left: position.left }}
    >
      {content}
    </div>
  );
}
```

DOM 크기나 위치를 측정해서 그 결과를 바탕으로 스타일을 적용해야 하는 경우에는 `useLayoutEffect`가 맞다. `useEffect`로 하면 브라우저가 먼저 잘못된 위치에 렌더링하고, 그 다음에 측정 후 이동하는 순서가 되어 화면 깜박임이 생긴다.

서버 사이드 렌더링(Next.js 등)에서는 `useLayoutEffect`가 경고를 낸다. 서버에는 DOM이 없기 때문에 실행 자체가 안 된다. SSR 환경에서는 `useEffect`로 대체하거나, 해당 컴포넌트를 클라이언트 전용으로 처리해야 한다.

```typescript
// SSR 환경 대응
const useIsomorphicLayoutEffect =
  typeof window !== 'undefined' ? useLayoutEffect : useEffect;
```

대부분의 경우는 `useEffect`로 충분하다. DOM 측정 후 즉시 스타일 적용이 필요한 경우에만 `useLayoutEffect`를 쓴다.

---

## 훅 규칙과 커스텀 훅

훅은 컴포넌트 최상단에서만 호출해야 한다. 조건문이나 반복문 안에서 호출하면 React가 훅의 호출 순서를 추적하지 못해 버그가 생긴다.

```typescript
// 이렇게 하면 안 됨
function BadComponent({ condition }) {
  if (condition) {
    const [value, setValue] = useState(0); // 조건에 따라 훅 수가 달라짐
  }
  return <div />;
}
```

로직이 조건에 따라 달라져야 한다면, 조건을 훅 안으로 넣는다.

```typescript
function GoodComponent({ condition }) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!condition) return; // 조건을 effect 안에서 처리
    // ...
  }, [condition]);

  return <div />;
}
```

커스텀 훅은 복잡한 훅 조합을 컴포넌트 밖으로 빼내는 도구다. 로직을 재사용하거나, 컴포넌트 코드가 너무 길어질 때 쓴다.

```typescript
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// 사용
function SearchComponent() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery) {
      fetchSearch(debouncedQuery);
    }
  }, [debouncedQuery]);
}
```

커스텀 훅 안에서도 훅 규칙이 동일하게 적용된다. `use`로 시작하는 함수명을 써야 React가 훅 규칙 위반을 잡아줄 수 있다.
