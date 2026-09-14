---
title: React.memo와 렌더링 최적화
tags: [frontend, performance]
updated: 2026-09-14
---

# React.memo와 렌더링 최적화

React.memo는 컴포넌트를 감싸 이전 props와 현재 props를 비교한 뒤, 변경이 없으면 리렌더링을 건너뛴다. 부모가 리렌더링될 때마다 자식도 따라 리렌더링되는 기본 동작을 막는 용도다.

## props 얕은 비교가 실제로 하는 일

내부적으로 `Object.is`를 쓴다. 원시값은 값 자체를 비교하고, 객체·배열·함수는 참조를 비교한다.

```js
// Object.is 동작
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

// 부모에서
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

주의할 점이 있다. `style`이 바뀌어도 위 비교 함수는 false를 반환하지 않으니 화면이 갱신되지 않는다. 비교 함수에서 누락한 props는 사실상 무시된다.

커스텀 비교 함수는 비교 로직이 기본 얕은 비교보다 확실히 저렴할 때만 쓴다. 그렇지 않으면 비교 비용만 추가된다.

## memo가 효과 없는 3가지 경우

### children prop

```jsx
const Wrapper = React.memo(({ children }) => {
  return <div className="wrapper">{children}</div>;
});

// 부모에서
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

실제로 문제가 생긴 경우에만 적용한다:

- Profiler로 측정했을 때 특정 컴포넌트가 불필요하게 자주 렌더링되고 있다
- 그 컴포넌트의 렌더링 비용이 충분히 무겁다 (복잡한 계산, 큰 리스트 등)
- props가 안정적인 참조로 만들어질 수 있는 구조다

마지막 조건이 안 맞으면 useCallback/useMemo로 props를 먼저 안정화한 다음에 memo를 붙여야 한다. 순서가 반대면 memo만 달고 효과 없다고 결론 내리는 실수가 생긴다.
