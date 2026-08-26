---
title: 컴포넌트 패턴
tags: [frontend, design-patterns, javascript, typescript]
updated: 2026-08-26
---

## 패턴이 생긴 이유

React에 훅이 없던 시절, 클래스 컴포넌트 사이에서 로직을 공유할 방법이 두 가지뿐이었다. HOC와 Render Props다. 둘 다 "함수를 인자로 받거나 함수를 반환한다"는 원리로 작동하고, 당시에는 실용적인 선택이었다.

훅이 나오면서 상황이 바뀌었다. HOC와 Render Props가 해결하려 했던 문제의 대부분을 커스텀 훅이 더 단순하게 처리한다. 하지만 HOC와 Render Props가 완전히 사라진 건 아니다. 여전히 쓸 이유가 있는 자리가 있다.

---

## HOC — 컴포넌트를 감싸는 함수

HOC(Higher-Order Component)는 컴포넌트를 받아서 새 컴포넌트를 반환하는 함수다. 핵심은 원래 컴포넌트를 건드리지 않고 기능을 주입한다는 점이다.

```typescript
function withAuth<P extends object>(WrappedComponent: React.ComponentType<P>) {
  return function AuthGuard(props: P) {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated) {
      return <Redirect to="/login" />;
    }

    return <WrappedComponent {...props} />;
  };
}

const ProtectedDashboard = withAuth(Dashboard);
```

HOC가 적합한 경우는 명확하다. **컴포넌트 자체를 조건부로 교체하거나 래핑해야 할 때**다. 인증 게이트, 에러 바운더리 래퍼, 퍼미션 체크처럼 "이 컴포넌트를 렌더링할지 말지"를 결정하는 로직이 여기에 해당한다.

### HOC가 만드는 문제들

prop이 어디서 왔는지 추적하기 어렵다. `withAuth(withLogging(withPermission(Dashboard)))` 형태로 쌓이면, Dashboard가 받는 prop이 어느 HOC에서 주입된 건지 코드를 보고 파악하기 어렵다. TypeScript를 써도 제네릭 타입이 여러 겹으로 합성되면 타입 에러 메시지가 난해해진다.

displayName을 직접 설정하지 않으면 React DevTools에서 `Component` 같은 이름으로 뭉개진다. 디버깅할 때 컴포넌트 트리가 의미 없는 이름들로 채워진다.

```typescript
// displayName 설정 안 하면 DevTools에서 추적 불가
AuthGuard.displayName = `withAuth(${WrappedComponent.displayName ?? WrappedComponent.name})`;
```

---

## Render Props — 렌더링 로직을 위임하는 방식

Render Props는 컴포넌트가 children이나 특정 prop으로 함수를 받고, 그 함수에 내부 상태를 넘겨서 렌더링을 위임하는 패턴이다.

```typescript
interface MouseTrackerProps {
  render: (position: { x: number; y: number }) => React.ReactNode;
}

function MouseTracker({ render }: MouseTrackerProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent) => {
    setPosition({ x: e.clientX, y: e.clientY });
  };

  return (
    <div onMouseMove={handleMouseMove}>
      {render(position)}
    </div>
  );
}

// 사용
<MouseTracker
  render={({ x, y }) => <Tooltip x={x} y={y} />}
/>
```

HOC와 달리 prop이 어디서 왔는지 명확하다. 함수 인자로 받는 데이터가 바로 보이기 때문에, 타입 추론도 자연스럽게 된다.

문제는 중첩이다. 여러 Render Props 컴포넌트를 조합하면 콜백이 안으로 계속 들어가는 구조가 된다. 예전에 Promise 콜백이 지옥처럼 중첩되던 것과 같은 패턴이다.

```typescript
// 이런 형태가 생긴다
<DataFetcher render={(data) =>
  <MouseTracker render={({ x, y }) =>
    <SomeOtherProvider render={(ctx) =>
      <Component data={data} x={x} y={y} ctx={ctx} />
    } />
  } />
} />
```

---

## 커스텀 훅으로 교체하는 시점

HOC나 Render Props를 커스텀 훅으로 교체해도 되는 기준은 단순하다. **로직만 공유하고, 렌더링 결과는 각 컴포넌트가 직접 결정해야 하는 경우**다.

```typescript
// 커스텀 훅으로 추출
function useMousePosition() {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return position;
}

// 각 컴포넌트에서 그냥 쓴다
function Tooltip() {
  const { x, y } = useMousePosition();
  return <div style={{ left: x, top: y }}>...</div>;
}
```

교체하지 말아야 하는 경우도 있다. HOC가 클래스 컴포넌트를 감싸야 하는 상황이라면 커스텀 훅으로 대체할 수 없다. 클래스 컴포넌트 안에서 훅을 쓸 수 없기 때문이다. 레거시 코드베이스에서 클래스 컴포넌트가 섞여 있으면 HOC가 남는다.

`react-redux`의 `connect`처럼 서드파티 라이브러리가 HOC로 설계된 API를 제공하는 경우에도 굳이 훅으로 바꿀 이유가 없다. 이미 훅 버전(`useSelector`, `useDispatch`)이 있다면 신규 코드에서는 훅을 쓰면 된다.

---

## Compound Component — 연관된 컴포넌트 묶기

Compound Component는 여러 컴포넌트가 내부 상태를 공유하면서 하나의 단위처럼 동작하게 만드는 패턴이다. HTML의 `<select>`와 `<option>`이 동작하는 방식을 떠올리면 이해하기 쉽다.

```typescript
// Select는 현재 선택된 값을 관리하고
// Option은 Select의 상태를 보고 선택 여부를 결정한다
<Select value={selected} onChange={setSelected}>
  <Select.Option value="a">옵션 A</Select.Option>
  <Select.Option value="b">옵션 B</Select.Option>
</Select>
```

### Context 없이 구현: children 클론

Context를 쓰지 않는 방법은 `React.Children.map`으로 children을 순회하면서 `React.cloneElement`로 prop을 주입하는 것이다.

```typescript
function Select({ value, onChange, children }: SelectProps) {
  return (
    <div className="select">
      {React.Children.map(children, (child) => {
        if (!React.isValidElement(child)) return child;
        return React.cloneElement(child, {
          selectedValue: value,
          onSelect: onChange,
        } as any);
      })}
    </div>
  );
}

function Option({ value, selectedValue, onSelect, children }: OptionProps) {
  return (
    <div
      className={selectedValue === value ? 'selected' : ''}
      onClick={() => onSelect?.(value)}
    >
      {children}
    </div>
  );
}

Select.Option = Option;
```

이 방법은 직접적이고 외부 의존성이 없다. 하지만 children이 한 단계 더 감싸져 있으면 prop이 전달되지 않는다.

```typescript
// 이렇게 쓰면 Option이 prop을 못 받는다
<Select value={selected} onChange={setSelected}>
  <div className="group">
    <Select.Option value="a">옵션 A</Select.Option>
  </div>
</Select>
```

### Context 기반 구현

Context를 쓰면 children의 깊이에 상관없이 상태를 공유할 수 있다.

```typescript
interface SelectContext {
  value: string;
  onChange: (value: string) => void;
}

const SelectCtx = React.createContext<SelectContext | null>(null);

function Select({ value, onChange, children }: SelectProps) {
  return (
    <SelectCtx.Provider value={{ value, onChange }}>
      <div className="select">{children}</div>
    </SelectCtx.Provider>
  );
}

function Option({ value, children }: { value: string; children: React.ReactNode }) {
  const ctx = React.useContext(SelectCtx);
  if (!ctx) throw new Error('Option은 Select 안에서만 써야 한다');

  return (
    <div
      className={ctx.value === value ? 'selected' : ''}
      onClick={() => ctx.onChange(value)}
    >
      {children}
    </div>
  );
}
```

### Context를 쓸 때 생기는 트레이드오프

Context는 Provider 안의 모든 컴포넌트를 구독자로 만든다. Select의 `value`가 바뀌면 `useContext(SelectCtx)`를 호출하는 Option 전부가 리렌더된다. Option이 10개면 10개 전부 리렌더된다.

클론 방식은 prop을 직접 전달하기 때문에 React의 일반적인 리렌더 규칙을 따른다. `React.memo`를 Option에 씌우면 변경된 것만 리렌더된다.

Context 방식에서 불필요한 리렌더를 줄이려면 value와 onChange를 각각 별도 Context로 분리하는 방법을 쓴다.

```typescript
const SelectValueCtx = React.createContext<string>('');
const SelectDispatchCtx = React.createContext<(value: string) => void>(() => {});

function Option({ value, children }: OptionProps) {
  const selectedValue = React.useContext(SelectValueCtx);
  const onChange = React.useContext(SelectDispatchCtx);

  // onChange Context가 바뀌지 않으면 리렌더 안 됨
  return (
    <div
      className={selectedValue === value ? 'selected' : ''}
      onClick={() => onChange(value)}
    >
      {children}
    </div>
  );
}
```

실무에서는 대부분 Option이 10~20개 수준이고 각각이 단순한 DOM이라 성능 문제가 표면으로 나오지 않는다. 최적화가 필요한 시점은 측정 결과가 나왔을 때다.

**Context 방식을 선택해야 하는 경우**: Option이 임의 깊이에서 쓰일 수 있는 경우, 또는 사용하는 쪽이 자유롭게 레이아웃을 구성해야 하는 경우다.

**클론 방식으로 충분한 경우**: children 구조가 항상 1단계이고 라이브러리 외부로 노출되지 않는 내부 컴포넌트인 경우다.

---

## Controlled vs Uncontrolled

Controlled 컴포넌트는 외부 상태로 값을 관리한다. Uncontrolled 컴포넌트는 DOM이 직접 상태를 들고 있고, 필요할 때 ref로 꺼낸다.

```typescript
// Controlled
function ControlledInput({ value, onChange }: Props) {
  return <input value={value} onChange={(e) => onChange(e.target.value)} />;
}

// Uncontrolled
function UncontrolledInput() {
  const ref = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    console.log(ref.current?.value);
  };

  return (
    <>
      <input ref={ref} defaultValue="초기값" />
      <button onClick={handleSubmit}>제출</button>
    </>
  );
}
```

### 실무에서 선택 기준

값이 바뀔 때마다 다른 UI에 즉각 반영해야 하면 Controlled가 필요하다. 검색 입력창이 바뀔 때마다 목록을 필터링하거나, 입력값을 기준으로 다른 필드를 활성화하는 경우가 여기다.

제출 시점에만 값이 필요하고, 입력 도중에 다른 무언가가 반응할 필요가 없다면 Uncontrolled가 단순하다. 이미지 업로드 폼이나 단순한 문의 폼이 그 예다. `react-hook-form`이 기본적으로 Uncontrolled 방식을 쓰는 이유도 여기에 있다. 리렌더 횟수가 줄어든다.

문제는 컴포넌트를 라이브러리로 배포할 때 생긴다. 사용자가 Controlled로 쓸지 Uncontrolled로 쓸지 미리 알 수 없다면, 두 방식을 모두 지원해야 한다. 이때 `value`가 있으면 Controlled, `defaultValue`만 있으면 Uncontrolled로 동작하게 만드는 패턴을 쓴다.

```typescript
function Input({
  value,
  defaultValue,
  onChange,
}: {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
}) {
  const isControlled = value !== undefined;
  const [internalValue, setInternalValue] = useState(defaultValue ?? '');

  const currentValue = isControlled ? value : internalValue;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isControlled) {
      setInternalValue(e.target.value);
    }
    onChange?.(e.target.value);
  };

  return <input value={currentValue} onChange={handleChange} />;
}
```

Controlled에서 Uncontrolled로, 또는 반대로 전환하면 React가 경고를 낸다. `value`가 `undefined`에서 실제 값으로 바뀌면 Uncontrolled에서 Controlled로 전환이 일어난다. 초기값으로 `undefined`가 들어오지 않도록 처리해야 한다.

```typescript
// 이렇게 하면 처음엔 Uncontrolled, 데이터 로드 후 Controlled로 전환된다
const [name, setName] = useState<string | undefined>(undefined); // 위험

// 빈 문자열로 초기화해야 한다
const [name, setName] = useState<string>('');
```
