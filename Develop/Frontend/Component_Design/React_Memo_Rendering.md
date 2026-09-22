---
title: React.memo와 렌더링 최적화
tags: [frontend, performance]
updated: 2026-09-22
---

# React.memo와 렌더링 최적화

React.memo는 컴포넌트를 감싸 이전 props와 현재 props를 비교한 뒤, 변경이 없으면 리렌더링을 건너뛴다. 부모가 리렌더링될 때마다 자식도 따라 리렌더링되는 기본 동작을 막는 용도다.

## props 얕은 비교가 실제로 하는 일

내부적으로 `Object.is`를 쓴다. 원시값은 값 자체를 비교하고, 객체·배열·함수는 참조를 비교한다.

```js
Object.is(1, 1)      // true
Object.is('a', 'a')  // true
Object.is({}, {})    // false — 참조가 다름
Object.is([], [])    // false — 참조가 다름
```

얕은 비교는 props의 각 키에 대해 이 비교를 한 번씩만 한다. 중첩된 객체 내부까지는 보지 않는다.

```jsx
const Child = React.memo(({ config }) => {
  return <div>{config.timeout}</div>;
});

const Parent = () => {
  const [count, setCount] = useState(0);

  // 리렌더링마다 새 객체 생성 → memo 무효화
  const config = { timeout: 3000 };

  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>증가</button>
      <Child config={config} />
    </>
  );
};
```

`config`가 매번 새 객체로 만들어지면 `Object.is(prevConfig, nextConfig)`가 false를 반환해서 memo가 아무 효과가 없다.

## TypeScript와 함께 쓸 때

### 제네릭 타입 지정

```tsx
interface CardProps {
  userId: number;
  name: string;
}

// 방법 1: 제네릭으로 명시
const UserCard = React.memo<CardProps>(({ userId, name }) => {
  return <div data-id={userId}>{name}</div>;
});

// 방법 2: 파라미터에 직접 타입 지정
const UserCard = React.memo(({ userId, name }: CardProps) => {
  return <div data-id={userId}>{name}</div>;
});
```

커스텀 비교 함수를 넣을 때는 `prev`와 `next`의 타입이 `CardProps`로 자동 추론된다.

```tsx
const UserCard = React.memo<CardProps>(
  ({ userId, name }) => <div data-id={userId}>{name}</div>,
  (prev, next) => prev.userId === next.userId // prev, next 모두 CardProps로 추론
);
```

### React.FC와 조합하면 타입 오류가 난다

```tsx
// 타입 오류 — React.FC는 함수 타입이고 React.memo()는 MemoExoticComponent를 반환한다
const UserCard: React.FC<CardProps> = React.memo(({ userId, name }) => {
  return <div>{name}</div>;
});
```

`React.FC<CardProps>`는 `(props: CardProps) => JSX.Element` 함수 타입이다. `React.memo()`가 반환하는 `MemoExoticComponent`와 구조가 달라서 TypeScript가 타입 불일치를 잡아낸다. 타입 추론에 맡기는 게 안전하다.

## 커스텀 비교 함수

두 번째 인자로 직접 비교 함수를 넘길 수 있다. 반환값이 `true`면 이전 렌더 결과를 재사용하고, `false`면 리렌더링한다.

```jsx
const Child = React.memo(
  ({ data, style }) => {
    return <div style={style}>{data.label}</div>;
  },
  (prevProps, nextProps) => {
    // data.id가 같으면 리렌더링 안 함
    // style은 무시
    return prevProps.data.id === nextProps.data.id;
  }
);
```

`style`이 바뀌어도 위 비교 함수는 false를 반환하지 않으니 화면이 갱신되지 않는다. 비교 함수에서 누락한 props는 사실상 무시된다.

커스텀 비교 함수는 비교 로직이 기본 얕은 비교보다 확실히 저렴할 때만 쓴다. 그렇지 않으면 비교 비용만 추가된다.

## memo가 효과 없는 경우

### children prop

```jsx
const Wrapper = React.memo(({ children }) => {
  return <div className="wrapper">{children}</div>;
});

const Parent = () => {
  return (
    <Wrapper>
      <SomeComponent />  {/* 매번 새 JSX 엘리먼트 생성 */}
    </Wrapper>
  );
};
```

`children`은 JSX를 렌더링할 때마다 새 React 엘리먼트 객체로 만들어진다. `Object.is`로 비교하면 항상 다른 참조라서 memo가 매번 리렌더링을 허용한다.

children을 전달하는 컴포넌트에 memo를 붙이는 건 대부분 의미가 없다.

### 객체·배열 props

```jsx
const Chart = React.memo(({ options }) => {
  return <canvas data-options={JSON.stringify(options)} />;
});

const Dashboard = () => {
  const [theme, setTheme] = useState('light');

  return (
    <Chart
      options={{ color: theme === 'light' ? '#000' : '#fff', size: 300 }}
    />
  );
};
```

`options`이 인라인 객체 리터럴이면 `theme`이 바뀌든 안 바뀌든 매번 새 참조다. `Chart`에 memo를 붙여도 소용없다.

### 인라인 함수 props

```jsx
const Button = React.memo(({ onClick, label }) => {
  return <button onClick={onClick}>{label}</button>;
});

const Form = () => {
  const [value, setValue] = useState('');

  return (
    <>
      <input value={value} onChange={e => setValue(e.target.value)} />
      <Button
        onClick={() => console.log(value)}  {/* 매번 새 함수 */}
        label="제출"
      />
    </>
  );
};
```

화살표 함수는 렌더링마다 새 함수 객체를 만든다. `Button`에 memo가 있어도 `onClick`이 매번 달라지니 결국 리렌더링된다.

### Context 구독

`useContext`로 Context를 구독하는 컴포넌트는 memo가 있어도 Context 값이 바뀌면 리렌더된다. memo는 부모가 리렌더링할 때 props가 같으면 건너뛰는 장치지, Context 구독을 막지는 않는다.

```tsx
const ThemeContext = createContext({ dark: false });

const ThemedButton = React.memo(({ label }: { label: string }) => {
  const { dark } = useContext(ThemeContext); // Context 구독

  return <button className={dark ? 'dark' : 'light'}>{label}</button>;
});

// ThemeContext 값이 바뀌면 label이 그대로여도 ThemedButton은 리렌더된다
```

DevTools Profiler에서 보면 "Context changed"가 렌더링 이유로 찍힌다. "Props changed"가 아니라서 memo를 달았는데도 리렌더링되는 원인을 못 찾는 경우가 있다.

Context 변경 범위를 줄이려면 Context 값을 props로 받는 순수 컴포넌트와 분리한다.

```tsx
// Context 값을 props로 받는 순수 컴포넌트
const PureButton = React.memo(({ label, dark }: { label: string; dark: boolean }) => {
  return <button className={dark ? 'dark' : 'light'}>{label}</button>;
});

// Context를 구독하는 래퍼 — memo 필요 없음
const ThemedButton = ({ label }: { label: string }) => {
  const { dark } = useContext(ThemeContext);
  return <PureButton label={label} dark={dark} />;
};
```

`ThemeContext`가 바뀔 때 `ThemedButton`은 리렌더되지만 `PureButton`은 `dark` 값이 실제로 바뀌었을 때만 리렌더된다.

## forwardRef와 memo 조합

ref를 전달해야 하는 컴포넌트에 memo도 붙여야 할 때 순서가 중요하다. `forwardRef`로 컴포넌트를 만든 다음 `memo`로 감싼다.

```tsx
interface InputProps {
  value: string;
  onChange: (val: string) => void;
}

const Input = React.memo(
  React.forwardRef<HTMLInputElement, InputProps>(({ value, onChange }, ref) => {
    return (
      <input
        ref={ref}
        value={value}
        onChange={e => onChange(e.target.value)}
      />
    );
  })
);
```

순서가 반대인 코드를 자주 본다.

```tsx
// 잘못된 순서 — ref가 제대로 전달되지 않는다
const Input = React.forwardRef(
  React.memo(({ value, onChange }: InputProps) => {
    return <input value={value} onChange={e => onChange(e.target.value)} />;
  })
);
```

`React.forwardRef`는 두 번째 인자로 `ref`를 받는 렌더 함수 `(props, ref) => JSX`를 기대한다. `React.memo`가 반환하는 것은 렌더 함수가 아니라 컴포넌트 래퍼(`MemoExoticComponent`)다. TypeScript에서는 여기서 타입 오류가 발생한다. JavaScript에서는 타입 오류 없이 실행되지만 ref가 null로 남는 케이스가 생긴다.

두 번 감싸면 DevTools에서 `memo(ForwardRef)` 처럼 이름이 중첩되어 보인다. `displayName`을 직접 지정하면 깔끔해진다.

```tsx
const Input = React.memo(
  React.forwardRef<HTMLInputElement, InputProps>(({ value, onChange }, ref) => {
    return <input ref={ref} value={value} onChange={e => onChange(e.target.value)} />;
  })
);
Input.displayName = 'Input';
```

## useCallback과 useMemo 조합

객체와 함수를 안정적인 참조로 만들어야 memo가 실제로 작동한다.

```jsx
const Chart = React.memo(({ options, onDataClick }) => {
  return (
    <canvas
      onClick={() => onDataClick(options.id)}
    />
  );
});

const Dashboard = () => {
  const [theme, setTheme] = useState('light');
  const [selectedId, setSelectedId] = useState(null);

  // useMemo: options 객체를 theme이 바뀔 때만 새로 만든다
  const options = useMemo(() => ({
    color: theme === 'light' ? '#000' : '#fff',
    size: 300,
    id: 'main-chart',
  }), [theme]);

  // useCallback: setSelectedId가 stable하므로 이 함수도 stable하다
  const handleDataClick = useCallback((id) => {
    setSelectedId(id);
  }, []);

  return <Chart options={options} onDataClick={handleDataClick} />;
};
```

`useCallback`의 의존성 배열에 있는 값이 바뀌면 함수도 새로 만들어진다. 의존성을 빠뜨리면 클로저가 오래된 값을 물고 있어서 버그가 생긴다.

```jsx
// 잘못된 사용: value가 의존성에 없다
const handleSubmit = useCallback(() => {
  console.log(value);  // value가 항상 초기값
}, []);  // value 누락

// 올바른 사용
const handleSubmit = useCallback(() => {
  console.log(value);
}, [value]);  // value가 바뀔 때마다 함수 재생성
```

의존성을 넣으면 value가 바뀔 때 함수도 바뀐다. 그러면 Button이 리렌더링된다. 이 경우엔 useCallback이 오히려 불필요한 복잡성만 추가한다.

## React 18 useDeferredValue와 memo

`useDeferredValue`는 무거운 렌더링을 낮은 우선순위로 미루는 React 18 기능이다. memo 없이는 제대로 작동하지 않는다.

흐름을 순서대로 보면 이렇다. 입력값이 바뀌면 React는 고우선순위 렌더를 시작한다. 이 렌더에서 `deferredQuery`는 아직 이전 값이다. memo가 있으면 React는 `query` prop이 같다고 판단해서 비싼 컴포넌트를 건너뛴다. 이후 낮은 우선순위 렌더에서 `deferredQuery`가 최신 값으로 바뀌고, 그때 비싼 컴포넌트를 그린다.

memo가 없으면 고우선순위 렌더에서도 비싼 컴포넌트를 렌더해야 해서 입력 응답성이 나빠진다.

```tsx
// memo 없으면 deferredQuery가 이전 값이어도 리렌더된다
const SearchResults = ({ query }: { query: string }) => {
  const results = expensiveFilter(query); // 무거운 연산
  return <ul>{results.map(r => <li key={r.id}>{r.name}</li>)}</ul>;
};

// memo가 있어야 deferral이 실제로 작동한다
const SearchResults = React.memo(({ query }: { query: string }) => {
  const results = expensiveFilter(query);
  return <ul>{results.map(r => <li key={r.id}>{r.name}</li>)}</ul>;
});

const SearchPage = () => {
  const [input, setInput] = useState('');
  const deferredQuery = useDeferredValue(input);

  // input과 deferredQuery가 다르면 이전 결과를 흐리게 표시
  const isPending = input !== deferredQuery;

  return (
    <>
      <input value={input} onChange={e => setInput(e.target.value)} />
      <div style={{ opacity: isPending ? 0.5 : 1 }}>
        <SearchResults query={deferredQuery} />
      </div>
    </>
  );
};
```

`isPending`을 쓰면 deferral이 진행 중일 때 이전 결과를 흐리게 보여주는 식으로 로딩 상태를 표현할 수 있다.

## React DevTools Profiler로 효과 검증

memo를 달았다고 실제로 리렌더링이 줄었는지는 측정해봐야 안다.

브라우저 확장에서 Profiler 탭을 열고 "Record" 버튼을 누른 다음 상호작용을 하고 멈춘다.

렌더링 이유를 보려면 Profiler 설정에서 **"Record why each component rendered while profiling"**을 켜야 한다. 기본값이 꺼져 있어서 이걸 모르고 그냥 쓰다가 원인을 못 찾는 경우가 있다.

```
컴포넌트 상세 패널에서 볼 수 있는 렌더링 이유:
- "Props changed" — props 중 하나가 바뀜
- "State changed" — 컴포넌트 내부 state 변경
- "Context changed" — 구독 중인 Context 변경
- "Hooks changed" — useCallback/useMemo 등 훅 변경
- "The parent component rendered" — 부모 리렌더링, memo 없거나 비교 실패
```

memo를 달았는데도 "Props changed"가 뜨면 어떤 prop이 바뀌는지 확인해야 한다. 같은 패널에서 변경된 prop을 이전값/다음값과 함께 보여준다.

Profiler의 불꽃 그래프(Flamegraph)에서 회색으로 표시된 컴포넌트는 memo가 리렌더링을 막은 것이다. 노란색/빨간색은 실제로 렌더링된 컴포넌트다.

## 어디에 쓸지 판단하는 기준

memo 자체도 비용이다. props 비교를 매 렌더링마다 실행한다. 가벼운 컴포넌트에 memo를 붙이면 비교 비용이 렌더링 비용보다 커질 수 있다.

단순 텍스트 하나를 렌더링하는 컴포넌트는 렌더 자체가 0.05ms 수준이다. props 비교(객체 key 순회, Object.is 호출 반복)가 이보다 느릴 수 있다. Flamegraph에서 회색(memo로 건너뜀) 막대 옆에 걸리는 시간을 보고, 그냥 렌더링하는 비용이 더 작다면 memo를 빼는 게 맞다.

과적용 패턴은 보통 이렇게 나온다. 부모 컴포넌트에 memo를 달면서 자식 컴포넌트에도 습관적으로 붙이는데, 자식의 props는 대부분 원시값이라 어차피 안정적이다. 이 경우 부모의 memo가 이미 리렌더를 막고 있어서 자식 memo는 아무 역할을 못 한다.

Profiler로 측정했을 때 특정 컴포넌트가 불필요하게 자주 렌더링되고, 그 렌더링 비용이 충분히 무거울 때(복잡한 계산, 큰 리스트 등), props가 안정적인 참조로 만들어질 수 있는 구조일 때 적용한다.

마지막 조건이 안 맞으면 useCallback/useMemo로 props를 먼저 안정화한 다음에 memo를 붙여야 한다. 순서가 반대면 memo만 달고 효과 없다고 결론 내리는 실수가 생긴다.
