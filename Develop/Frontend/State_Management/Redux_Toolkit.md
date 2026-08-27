---
title: Redux Toolkit 실무 패턴
tags: [frontend, javascript, typescript, design-patterns, performance, testing]
updated: 2026-08-27
---

## Redux Toolkit 이 등장한 이유

기존 Redux 는 action type 상수, action creator, reducer를 별도 파일에 나눠 쓰는 게 관행이었다. 간단한 기능 하나를 추가하려면 파일 세 개를 손댔고, 그 파일들 사이에 오타가 나도 런타임 전까지 잡히지 않았다. 보일러플레이트가 많다는 비판은 맞는 말이었다.

Redux Toolkit(RTK)은 그 보일러플레이트를 줄이면서도 Redux의 단방향 데이터 흐름은 유지한다. `createSlice` 하나로 action type, action creator, reducer를 한 곳에서 정의하고, `immer`를 내장해서 불변성 처리를 숨겨준다. RTK Query까지 쓰면 서버 데이터 페칭 로직도 slice에서 분리할 수 있다.

그런데 보일러플레이트가 줄었다고 삽질도 줄어드는 건 아니다. 오히려 immer를 이해하지 못한 채 쓰다가 이상한 버그를 만나거나, selector를 무심코 인라인으로 쓰다가 렌더 횟수가 폭발하는 경우가 생긴다.

---

## createSlice — 기본 구조와 자주 놓치는 지점

```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface CartState {
  items: { id: string; qty: number }[];
  status: 'idle' | 'loading';
}

const initialState: CartState = {
  items: [],
  status: 'idle',
};

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    addItem(state, action: PayloadAction<{ id: string; qty: number }>) {
      const existing = state.items.find(i => i.id === action.payload.id);
      if (existing) {
        existing.qty += action.payload.qty; // immer가 허용하는 직접 변이
      } else {
        state.items.push(action.payload);
      }
    },
    clearCart(state) {
      state.items = []; // 새 배열 할당도 가능
    },
  },
});

export const { addItem, clearCart } = cartSlice.actions;
export default cartSlice.reducer;
```

`name` 필드는 action type 접두사가 된다. `cart/addItem`, `cart/clearCart` 식이다. DevTools에서 action을 추적할 때 이 이름이 보이므로 slice 이름을 의미 있게 짓는 게 중요하다. `slice1`, `dataSlice` 같은 이름은 디버깅할 때 고통이다.

---

## TypeScript store 타입 설정

RootState와 AppDispatch는 매번 수동으로 선언하는 게 아니라 store에서 추론해서 쓴다.

```typescript
// store.ts
import { configureStore } from '@reduxjs/toolkit';
import cartReducer from './cartSlice';
import { userApi } from './services/userApi';

export const store = configureStore({
  reducer: {
    cart: cartReducer,
    [userApi.reducerPath]: userApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(userApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

reducer가 바뀌면 `RootState`도 자동으로 갱신된다. 수동으로 인터페이스를 선언하면 reducer와 타입이 따로 놀게 된다.

typed hooks는 별도 파일에 만들어 두는 게 편하다.

```typescript
// hooks.ts
import { useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from './store';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector = <T>(selector: (state: RootState) => T) =>
  useSelector<RootState, T>(selector);
```

`useDispatch`를 그대로 쓰면 dispatch 타입이 `Dispatch<AnyAction>`으로 잡혀서 `createAsyncThunk`가 반환하는 thunk를 dispatch할 때 타입 에러가 난다. `useAppDispatch`를 쓰면 `AppDispatch`가 적용되어 thunk까지 타입 검사가 된다.

`useAppSelector`를 쓰면 매 selector 함수마다 `(state: RootState)` 타입 주석을 달지 않아도 된다. 처음에는 사소해 보이지만 selector가 많아지면 차이가 난다.

---

## Immer 가변 업데이트 오해

RTK가 내장한 immer 덕분에 `state.items.push(...)` 같은 코드를 쓸 수 있다. 그런데 두 가지 방식을 섞으면 문제가 생긴다.

직접 변이와 새 값 반환을 동시에 하면 안 된다.

```typescript
// 이렇게 하면 안 된다
reducers: {
  resetItems(state) {
    state.items = [];
    return state; // state를 직접 변이한 뒤 반환하면 immer가 무엇을 써야 할지 모른다
  },
}
```

immer의 규칙은 단순하다. reducer 안에서 둘 중 하나만 한다:
- `state`를 직접 변이한다 (반환값 없음)
- 완전히 새로운 값을 `return`한다 (state는 건드리지 않음)

둘을 섞으면 immer가 경고를 던지거나 예측 불가능한 동작을 한다.

또 다른 흔한 실수는 `state` 자체를 교체할 때다.

```typescript
// 잘못된 방식 — state 자체를 재할당해도 반영 안 된다
resetItems(state) {
  state = []; // state는 immer 프록시의 참조라 이렇게 해도 아무 의미 없다
},

// 올바른 방식
resetItems(state) {
  return []; // 새 값을 반환
  // 또는
  // state.items = [];
},
```

배열 자체가 state인 경우와 state 안의 프로퍼티인 경우를 구분해야 한다. `initialState`가 배열이면 `return newArray`를 써야 하고, 객체 안의 프로퍼티면 `state.prop = newValue`를 쓰면 된다.

---

## createAsyncThunk — 비동기 처리

서버 요청은 `createAsyncThunk`로 정의하고, slice의 `extraReducers`에서 처리한다.

```typescript
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchUser = createAsyncThunk(
  'user/fetchById',
  async (userId: string, thunkAPI) => {
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) {
      return thunkAPI.rejectWithValue({ status: response.status });
    }
    return response.json();
  }
);

const userSlice = createSlice({
  name: 'user',
  initialState: { data: null, loading: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUser.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
      })
      .addCase(fetchUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});
```

`thunkAPI.rejectWithValue`를 쓰지 않으면 `action.error.message`만 전달된다. HTTP 상태 코드나 서버가 보낸 에러 바디를 그대로 처리하려면 반드시 `rejectWithValue`로 감싸야 한다.

`createAsyncThunk`는 thunk를 dispatch했을 때 Promise를 반환한다. 컴포넌트에서 결과를 직접 처리해야 할 때는 이렇게 쓴다:

```typescript
const handleSubmit = async () => {
  const result = await dispatch(fetchUser(userId));
  if (fetchUser.fulfilled.match(result)) {
    navigate('/dashboard');
  }
};
```

`fetchUser.fulfilled.match(result)`로 성공 여부를 판별하면 타입 좁히기까지 된다.

---

## createEntityAdapter — 정규화 상태 관리

목록 데이터를 배열로 관리하다 보면 두 가지 문제를 자주 만난다. 특정 id의 항목을 찾으려면 `find()`로 배열을 순회해야 하고, 같은 데이터가 여러 slice에 중복으로 들어가면 동기화하기 어렵다.

`createEntityAdapter`는 엔티티를 `{ ids: string[], entities: { [id]: T } }` 구조로 정규화해 id로 O(1) 접근하게 한다.

```typescript
import { createSlice, createEntityAdapter, PayloadAction } from '@reduxjs/toolkit';

interface Product {
  id: string;
  name: string;
  price: number;
  stock: number;
}

const productsAdapter = createEntityAdapter<Product>({
  sortComparer: (a, b) => a.name.localeCompare(b.name),
});

// initialState는 { ids: [], entities: {} } + 추가 필드
const initialState = productsAdapter.getInitialState({
  status: 'idle' as 'idle' | 'loading' | 'error',
});

const productsSlice = createSlice({
  name: 'products',
  initialState,
  reducers: {
    productAdded: productsAdapter.addOne,
    productsLoaded: productsAdapter.setAll,
    productUpdated: productsAdapter.upsertOne,
    productRemoved: productsAdapter.removeOne,
    stockDecremented(state, action: PayloadAction<{ id: string; amount: number }>) {
      const product = state.entities[action.payload.id];
      if (product) {
        product.stock -= action.payload.amount;
      }
    },
  },
});

export const productActions = productsSlice.actions;
export default productsSlice.reducer;
```

adapter가 제공하는 주요 CRUD 메서드다.

- `addOne` — 이미 id가 있으면 무시
- `setOne` — 없으면 추가, 있으면 완전 교체
- `upsertOne` — 없으면 추가, 있으면 shallow merge
- `updateOne(state, { id, changes })` — 특정 필드만 수정
- `removeOne`, `removeMany`, `removeAll`
- `setAll` — ids·entities 전체 교체

selector는 `getSelectors()`로 만든다.

```typescript
export const {
  selectAll: selectAllProducts,
  selectById: selectProductById,
  selectIds: selectProductIds,
  selectTotal: selectProductCount,
} = productsAdapter.getSelectors((state: RootState) => state.products);
```

`selectAll`은 `ids` 배열 순서대로 정렬된 배열을 반환한다. `sortComparer`를 지정하면 항목 추가·수정 시 ids 배열을 정렬 상태로 유지한다.

`upsertOne`의 동작을 정확히 이해해야 한다. 해당 id가 없는 상태에서 `upsertOne`을 쓰면 partial 객체 그대로가 entity로 저장된다. 필수 필드가 빠진 채 저장될 수 있다. 존재 여부를 먼저 확인하거나 `updateOne`을 조건부로 쓰는 게 안전하다.

`selectById`는 없는 id를 조회하면 `undefined`를 반환한다. RTK 2.x에서는 `state.entities[id]`도 `T | undefined`로 추론되므로 null check 없이 접근하면 컴파일 에러가 난다. 배열 기반 slice에서 `find()` 결과를 undefined 체크 없이 쓰던 습관에서 오는 실수다.

---

## Selector 최적화 누락

가장 조용히 성능을 갉아먹는 부분이다. `useSelector`에 인라인 함수를 쓰면 렌더마다 새 참조가 생긴다.

```typescript
// 렌더마다 새 배열을 만든다 — 참조가 항상 달라서 불필요한 렌더가 발생한다
const completedItems = useSelector((state) =>
  state.cart.items.filter(item => item.completed)
);
```

`reselect`의 `createSelector`를 쓰면 입력 selector의 결과가 바뀌지 않으면 이전 값을 그대로 반환한다:

```typescript
import { createSelector } from '@reduxjs/toolkit'; // RTK가 reselect를 재수출한다

const selectCartItems = (state: RootState) => state.cart.items;

export const selectCompletedItems = createSelector(
  [selectCartItems],
  (items) => items.filter(item => item.completed)
);

// 컴포넌트에서
const completedItems = useAppSelector(selectCompletedItems);
```

`createSelector`는 메모이제이션을 하나의 호출 결과에 대해서만 한다. 여러 컴포넌트 인스턴스가 각자 다른 인자로 같은 selector를 쓸 때는 각 인스턴스가 독립된 메모이제이션 캐시를 가져야 한다.

```typescript
// id를 인자로 받아야 할 때 — 팩토리 패턴으로 인스턴스별 selector 생성
const makeSelectItemById = () =>
  createSelector(
    [(state: RootState) => state.cart.items, (_: RootState, id: string) => id],
    (items, id) => items.find(item => item.id === id)
  );

// 컴포넌트에서
const selectItem = useMemo(makeSelectItemById, []);
const item = useAppSelector((state) => selectItem(state, itemId));
```

`useMemo`로 컴포넌트 인스턴스마다 selector를 만들면 각자 독립된 캐시를 유지한다.

---

## RTK Query 기초

RTK Query는 서버 상태를 별도로 관리한다. 클라이언트 상태(UI 상태, 폼 값 등)는 slice로, 서버에서 오는 데이터는 RTK Query로 분리하는 게 권장되는 패턴이다.

```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const userApi = createApi({
  reducerPath: 'userApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  tagTypes: ['User'],
  endpoints: (builder) => ({
    getUserById: builder.query<User, string>({
      query: (id) => `/users/${id}`,
      providesTags: (result, error, id) => [{ type: 'User', id }],
    }),
    updateUser: builder.mutation<User, Partial<User> & { id: string }>({
      query: ({ id, ...patch }) => ({
        url: `/users/${id}`,
        method: 'PATCH',
        body: patch,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: 'User', id }],
    }),
  }),
});

export const { useGetUserByIdQuery, useUpdateUserMutation } = userApi;
```

`tagTypes`, `providesTags`, `invalidatesTags`는 캐시 무효화 흐름이다. `updateUser` 성공 후 `{ type: 'User', id }`를 무효화하면 같은 id로 캐시된 `getUserById` 결과가 자동으로 다시 요청된다.

store 설정에 추가하는 걸 빠뜨리는 경우가 있다:

```typescript
import { configureStore } from '@reduxjs/toolkit';
import { userApi } from './services/userApi';

export const store = configureStore({
  reducer: {
    [userApi.reducerPath]: userApi.reducer,
    // 다른 reducer들
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(userApi.middleware), // 이걸 빠뜨리면 캐시가 동작 안 한다
});
```

`userApi.middleware`를 추가하지 않으면 캐시 수명, polling, 자동 재요청이 전부 동작하지 않는다. store 설정에서 middleware 체인에 추가하는 게 필수다.

---

## RTK Query 고급 기능

### polling

실시간 데이터가 필요한데 웹소켓을 쓰기 부담스러운 경우, `pollingInterval`로 주기적 재요청을 설정한다.

```typescript
const { data, isLoading } = useGetDashboardStatsQuery(undefined, {
  pollingInterval: 30000,        // 30초마다 재요청
  refetchOnFocus: true,           // 탭 포커스 복귀 시 재요청
  skipPollingIfUnfocused: true,   // 백그라운드 탭에서는 polling 중단
});
```

컴포넌트가 unmount되면 polling이 자동으로 멈춘다. `skipPollingIfUnfocused`를 명시하지 않으면 백그라운드 탭에서도 요청이 계속 나간다. 대시보드를 여러 탭에 열어두는 경우에 불필요한 서버 부하가 생긴다.

### 조건부 fetching

id가 없거나 로그인하지 않은 상태에서 쿼리가 실행되는 걸 막으려면 `skip` 옵션이나 `skipToken`을 쓴다.

```typescript
// skip 옵션
const { data: user } = useGetUserByIdQuery(userId, {
  skip: !userId,
});

// skipToken — TypeScript 타입 추론에 더 유리하다
import { skipToken } from '@reduxjs/toolkit/query/react';

const { data: user } = useGetUserByIdQuery(userId ?? skipToken);
```

`skip: !userId`를 쓰면 `data` 타입이 `User | undefined`로 남고 `userId`가 `string`임을 TypeScript가 보장하지 않는다. `skipToken`을 쓰면 `userId`가 있을 때만 쿼리가 실행되고, 그 경우 `userId`가 `string`임이 타입 레벨에서 명확해진다.

### prepareHeaders — 인증 토큰 삽입

모든 요청에 인증 헤더를 붙이는 건 `baseQuery`의 `prepareHeaders`에서 처리한다. 각 endpoint마다 헤더를 설정할 필요가 없다.

```typescript
export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token;
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  endpoints: (builder) => ({ ... }),
});
```

토큰 만료 처리가 필요하면 `fetchBaseQuery`를 래핑하는 reauth 패턴을 쓴다. 401을 받았을 때 토큰을 갱신하고 원래 요청을 재시도한다.

```typescript
import type { BaseQueryFn } from '@reduxjs/toolkit/query';

const baseQuery = fetchBaseQuery({ baseUrl: '/api', prepareHeaders: ... });

const baseQueryWithReauth: BaseQueryFn = async (args, api, extraOptions) => {
  let result = await baseQuery(args, api, extraOptions);
  if (result.error?.status === 401) {
    const refreshResult = await baseQuery('/auth/refresh', api, extraOptions);
    if (refreshResult.data) {
      api.dispatch(setCredentials(refreshResult.data as AuthCredentials));
      result = await baseQuery(args, api, extraOptions); // 원래 요청 재시도
    } else {
      api.dispatch(logout());
    }
  }
  return result;
};
```

재시도 중에 다른 컴포넌트에서도 동시에 401이 나면 토큰 갱신 요청이 여러 번 나갈 수 있다. 실제 운영 코드에서는 mutex나 flag로 갱신 중 상태를 관리해야 한다.

### optimistic update

서버 응답을 기다리지 않고 UI를 먼저 업데이트하는 패턴이다. 요청이 실패하면 되돌린다.

```typescript
updateUser: builder.mutation<User, Partial<User> & { id: string }>({
  query: ({ id, ...patch }) => ({
    url: `/users/${id}`,
    method: 'PATCH',
    body: patch,
  }),
  async onQueryStarted({ id, ...patch }, { dispatch, queryFulfilled }) {
    const patchResult = dispatch(
      api.util.updateQueryData('getUserById', id, (draft) => {
        Object.assign(draft, patch);
      })
    );
    try {
      await queryFulfilled;
    } catch {
      patchResult.undo(); // 요청 실패 시 캐시를 이전 값으로 되돌린다
    }
  },
  invalidatesTags: (result, error, { id }) => [{ type: 'User', id }],
}),
```

요청이 실패하면 `patchResult.undo()`가 캐시를 이전 상태로 되돌린다. 성공하면 `invalidatesTags`가 서버에서 최신 데이터를 다시 받아온다. 서버가 응답에 `updatedAt` 같은 추가 필드를 포함해서 반환하는 경우, optimistic하게 설정한 값과 서버 값이 잠깐 다를 수 있다.

`onQueryStarted`에서는 `dispatch(someAction())`으로 일반 action도 보낼 수 있다. RTK Query 캐시와 일반 slice 상태를 같이 업데이트해야 하는 경우에 쓴다.

---

## 테스트

Redux를 포함한 컴포넌트 테스트에는 실제 store를 만들어서 쓴다. `redux-mock-store`는 reducer가 실제로 실행되지 않아서 상태 변화를 검증하기 어렵다.

### renderWithProviders 패턴

```typescript
// test/utils.tsx
import React from 'react';
import { configureStore } from '@reduxjs/toolkit';
import type { RenderOptions } from '@testing-library/react';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import cartReducer from '../cartSlice';
import { userApi } from '../services/userApi';
import type { RootState } from '../store';

function makeTestStore(preloadedState?: Partial<RootState>) {
  return configureStore({
    reducer: {
      cart: cartReducer,
      [userApi.reducerPath]: userApi.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(userApi.middleware),
    preloadedState,
  });
}

type TestStore = ReturnType<typeof makeTestStore>;

interface ExtendedRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  preloadedState?: Partial<RootState>;
  store?: TestStore;
}

export function renderWithProviders(
  ui: React.ReactElement,
  {
    preloadedState = {},
    store = makeTestStore(preloadedState),
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }
  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}
```

`preloadedState`로 초기 상태를 원하는 값으로 설정하면 특정 상태에서 컴포넌트가 어떻게 동작하는지 테스트하기 쉽다.

```typescript
// CartItem.test.tsx
import { renderWithProviders } from '../test/utils';
import CartItem from '../CartItem';
import { screen, fireEvent } from '@testing-library/react';

test('수량이 0이 되면 항목이 제거된다', () => {
  const { store } = renderWithProviders(<CartItem id="prod-1" />, {
    preloadedState: {
      cart: {
        items: [{ id: 'prod-1', name: '상품', qty: 1 }],
        status: 'idle',
      },
    },
  });

  fireEvent.click(screen.getByRole('button', { name: /감소/ }));

  expect(store.getState().cart.items).toHaveLength(0);
});
```

### RTK Query 엔드포인트 테스트

RTK Query는 MSW(Mock Service Worker)와 함께 쓰는 게 현실적이다. 실제 fetch를 인터셉트해서 원하는 응답을 반환한다.

```typescript
import { setupServer } from 'msw/node';
import { rest } from 'msw';

const server = setupServer(
  rest.get('/api/users/:id', (req, res, ctx) =>
    res(ctx.json({ id: req.params.id, name: '테스터' }))
  )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('사용자 데이터가 로드된다', async () => {
  const { store } = renderWithProviders(<UserProfile id="user-1" />);

  await screen.findByText('테스터');

  const result = userApi.endpoints.getUserById.select('user-1')(store.getState());
  expect(result.status).toBe('fulfilled');
  expect(result.data?.name).toBe('테스터');
});
```

각 테스트마다 새 store를 만들지 않으면 이전 테스트의 캐시가 남아 다음 테스트에 영향을 준다. `afterEach`에서 `server.resetHandlers()`를 불러도 RTK Query 캐시는 store에 그대로 남는다. `makeTestStore()`를 각 테스트에서 새로 호출하거나, `afterEach`에서 `store.dispatch(userApi.util.resetApiState())`를 실행해야 한다.

---

## 실제로 버그를 만드는 패턴

**slice 이름 충돌.** 두 slice가 같은 `name`을 쓰면 DevTools에서 action이 섞여 보인다. `name`은 저장소 전체에서 유일해야 한다.

**`extraReducers`에서 상태를 직접 반환.** `createAsyncThunk`의 fulfilled 케이스에서 state를 직접 변이하면서 동시에 return하는 실수를 간혹 한다. immer 규칙과 동일하게, 둘 중 하나만 해야 한다.

**RTK Query 응답 타입 미검증.** `builder.query<User, string>`에서 `User`는 타입스크립트 타입이지, 런타임 검증이 아니다. 서버가 예상과 다른 구조를 보내도 TypeScript는 잡지 못한다. 중요한 응답은 `zod` 같은 런타임 검증과 함께 쓴다.

**`invalidatesTags`를 너무 넓게 설정.** `invalidatesTags: ['User']`로 타입 전체를 무효화하면 목록 페이지와 상세 페이지가 동시에 재요청된다. id 기준으로 좁게 무효화하는 게 낫다.
