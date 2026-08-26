---
title: Redux Toolkit 실무 패턴
tags: [frontend, javascript, typescript, design-patterns, performance]
updated: 2026-08-26
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

## Immer 가변 업데이트 오해

RTK가 내장한 immer 덕분에 `state.items.push(...)` 같은 코드를 쓸 수 있다. 그런데 이걸 오해해서 두 가지 방식을 섞으면 문제가 생긴다.

**직접 변이와 새 값 반환을 동시에 하면 안 된다.**

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
const completedItems = useSelector(selectCompletedItems);
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
const item = useSelector((state) => selectItem(state, itemId));
```

`useMemo`로 컴포넌트 인스턴스마다 selector를 만들면 각자 독립된 캐시를 유지한다.

---

## 실제로 버그를 만드는 패턴

**slice 이름 충돌.** 두 slice가 같은 `name`을 쓰면 DevTools에서 action이 섞여 보인다. `name`은 저장소 전체에서 유일해야 한다.

**`extraReducers`에서 상태를 직접 반환.** `createAsyncThunk`의 fulfilled 케이스에서 state를 직접 변이하면서 동시에 return하는 실수를 간혹 한다. immer 규칙과 동일하게, 둘 중 하나만 해야 한다.

**RTK Query 응답 타입 미검증.** `builder.query<User, string>`에서 `User`는 타입스크립트 타입이지, 런타임 검증이 아니다. 서버가 예상과 다른 구조를 보내도 TypeScript는 잡지 못한다. 중요한 응답은 `zod` 같은 런타임 검증과 함께 쓴다.

**`invalidatesTags`를 너무 넓게 설정.** `invalidatesTags: ['User']`로 타입 전체를 무효화하면 목록 페이지와 상세 페이지가 동시에 재요청된다. id 기준으로 좁게 무효화하는 게 낫다.
