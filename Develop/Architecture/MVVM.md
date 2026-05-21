---
title: MVVM (Model-View-ViewModel)
tags:
  - Architecture
  - MVVM
  - Frontend
  - Backend
  - DataBinding
updated: 2026-05-21
---

# MVVM (Model-View-ViewModel)

MVVM은 화면과 데이터 사이에 *ViewModel*이라는 중간층을 두고, 그 둘을 데이터 바인딩으로 연결하는 패턴이다. WPF에서 처음 자리잡았고 지금은 Android(Jetpack), Vue, SwiftUI, React(상태 라이브러리 조합) 같은 거의 모든 선언적 UI 환경에 녹아 있다.

백엔드 개발자가 MVVM을 알아야 하는 이유는 단순하다. 프론트가 MVVM이면 API 응답 형태, 에러 처리 방식, 상태 동기화 모델이 달라진다. ViewModel은 화면이 무엇을 보여주는지를 그대로 옮긴 객체라서, 백엔드가 도메인 모델을 그대로 던지면 프론트가 매번 변환 코드를 짜야 한다. 반대로 ViewModel 친화적으로 응답을 만들면 백엔드 도메인이 화면에 끌려다닌다. 이 균형을 잡는 게 실무에서 가장 어렵다.

이 문서는 MVVM의 이론보다는 "왜 이렇게 짜는가"와 "어디서 망가지는가"에 집중한다.

---

## 1. MVC, MVP, MVVM의 차이

세 패턴 모두 화면(View)과 데이터(Model)를 분리하려는 목적은 같다. 차이는 *둘 사이를 누가 어떻게 잇는가*다.

### MVC (Model-View-Controller)

가장 오래된 패턴이다. Controller가 사용자 입력을 받아 Model을 갱신하고, View는 Model을 직접 읽어 그린다.

```
사용자 입력 → Controller → Model 변경 → View가 Model을 읽어 갱신
```

문제는 View가 Model을 직접 알아야 한다는 점이다. 화면 종류가 늘어나면 View마다 Model을 어떻게 읽을지 다르게 짜야 하고, View와 Model 사이의 결합이 슬금슬금 강해진다. 서버 사이드(Spring MVC, Rails)에서는 매 요청마다 Controller가 새로 만들어지고 화면을 한 번만 렌더링하므로 큰 문제가 안 됐다. 데스크톱·모바일처럼 화면이 계속 살아 있는 환경에서는 결합도가 빠르게 누적된다.

### MVP (Model-View-Presenter)

Presenter가 View와 Model 사이에 끼어들어 둘을 갈라놓는다. View는 Presenter만 알고, Model은 Presenter가 다룬다.

```
사용자 입력 → View → Presenter → Model 조회/변경 → Presenter가 View를 직접 호출해 갱신
```

핵심은 *Presenter가 View 인터페이스를 명시적으로 호출한다*는 것이다. `view.showLoading()`, `view.setUserName(name)` 같은 식으로 Presenter가 View에 명령한다. View는 인터페이스로 추상화돼서 테스트할 때 Mock으로 갈아끼울 수 있다.

문제는 호출이 많아진다는 점이다. 필드가 20개 있는 화면이면 Presenter에 `setField1`, `setField2`... 같은 메서드가 줄줄이 늘어선다. View가 추가될 때마다 Presenter도 같이 부풀어 오른다.

### MVVM

ViewModel은 View가 보여줄 상태를 *데이터 그 자체로* 노출한다. View는 그 데이터를 바인딩해서 자동으로 따라간다. ViewModel이 View를 호출하는 일이 없다.

```
사용자 입력 → (바인딩) → ViewModel 상태 변경 → (바인딩) → View 자동 갱신
```

ViewModel은 자기가 어떤 View에 붙는지 모른다. 그저 상태(`userName`, `isLoading`, `errors`)와 명령(`submit()`, `cancel()`)을 노출할 뿐이다. 화살표가 양쪽으로 자동으로 흐르기 때문에 코드량이 줄고, 같은 ViewModel을 여러 View가 공유할 수 있다.

|구분|중간층|View → Model|Model → View|결합도|테스트 난이도|
|---|---|---|---|---|---|
|MVC|Controller|Controller가 처리|View가 Model 구독|View-Model 직접 결합|중간|
|MVP|Presenter|View가 Presenter 호출|Presenter가 View 메서드 호출|View-Presenter 양방향 결합|낮음 (View 인터페이스 Mock)|
|MVVM|ViewModel|바인딩이 처리|바인딩이 처리|View → ViewModel 단방향 의존|낮음 (View 없이 ViewModel 단독 테스트)|

실무에서 MVVM이 자리잡은 결정적 이유는 *바인딩이 표준화*됐기 때문이다. WPF의 `{Binding}`, Android의 LiveData/StateFlow, Vue의 reactive, SwiftUI의 `@State`/`@Published` 모두 같은 발상이다. 사람이 매번 `setText()` 호출을 적지 않아도 된다.

---

## 2. ViewModel이 가진 책임

ViewModel을 처음 짤 때 가장 헷갈리는 건 "Model이랑 뭐가 다르냐"다. 결론부터 말하면 ViewModel은 *화면 좌표계*에서 생각하는 객체다.

### Model

도메인을 표현한다. 백엔드에서 받아온 `User`, `Order`, `Product` 같은 객체가 여기 속한다. 화면에 어떻게 보일지는 모른다.

```kotlin
data class User(
    val id: Long,
    val email: String,
    val createdAt: Instant,
    val role: Role
)
```

### ViewModel

화면이 필요로 하는 형태로 가공한 상태와, 화면에서 일어나는 사용자 동작을 처리할 명령을 담는다.

```kotlin
class UserProfileViewModel(
    private val userRepo: UserRepository
) : ViewModel() {
    val displayName = MutableStateFlow("")
    val joinedYearsAgo = MutableStateFlow(0)
    val isAdminBadgeVisible = MutableStateFlow(false)
    val isLoading = MutableStateFlow(false)
    val errorMessage = MutableStateFlow<String?>(null)

    fun load(userId: Long) {
        viewModelScope.launch {
            isLoading.value = true
            runCatching { userRepo.find(userId) }
                .onSuccess { user ->
                    displayName.value = user.email.substringBefore('@')
                    joinedYearsAgo.value = yearsSince(user.createdAt)
                    isAdminBadgeVisible.value = user.role == Role.ADMIN
                }
                .onFailure { errorMessage.value = it.message }
            isLoading.value = false
        }
    }
}
```

여기서 `displayName`은 Model의 `email`을 화면용으로 가공한 결과다. `isAdminBadgeVisible`도 마찬가지로 `role == ADMIN`이라는 화면용 판단을 미리 끝낸 값이다. View는 이 값을 *그대로 화면에 꽂으면 끝*이다.

이 분리가 무너지는 순간 ViewModel이 거대해진다. 가장 흔한 실수는 View에서 `if (vm.user.role == "ADMIN") showBadge()` 같은 분기를 두는 것이다. 그 분기는 ViewModel에 있어야 한다.

### ViewModel이 절대 가지면 안 되는 것

- View에 대한 참조 (Activity, Fragment, DOM, Window 등)
- 화면 좌표·픽셀·색상 같은 표현 단위
- 안드로이드의 `Context`, WPF의 `Dispatcher`처럼 플랫폼에 종속된 객체

이 원칙이 깨지면 단위 테스트에서 ViewModel을 단독으로 띄울 수 없다. ViewModel은 UI 프레임워크 없이 JVM이나 Node 위에서 그냥 인스턴스화돼야 한다.

---

## 3. 데이터 바인딩

MVVM에서 가장 신비롭게 보이는 부분이 바인딩이다. 사실 동작 원리는 간단하다. *값이 바뀌었다는 신호*를 어떻게 전파하느냐의 문제일 뿐이다.

### 단방향 바인딩 (ViewModel → View)

ViewModel의 상태가 바뀌면 View가 자동으로 갱신된다. 보통 *옵저버 패턴* 위에 얹혀 있다.

```kotlin
val name = MutableStateFlow("guest")

lifecycleScope.launch {
    name.collect { binding.nameLabel.text = it }
}
```

`MutableStateFlow`는 값이 바뀔 때마다 등록된 collector에게 새 값을 흘려보낸다. View는 collector로 등록만 해두면 갱신이 알아서 일어난다.

Vue 3는 Proxy로 같은 일을 한다.

```javascript
const state = reactive({ name: 'guest' })
// 템플릿: <span>{{ state.name }}</span>
// state.name = 'kim' 하는 순간 Proxy가 변경을 감지해 렌더 큐에 넣는다.
```

WPF는 `INotifyPropertyChanged`라는 인터페이스로 직접 이벤트를 발행한다.

```csharp
public class UserViewModel : INotifyPropertyChanged
{
    private string _name;
    public string Name
    {
        get => _name;
        set
        {
            _name = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Name)));
        }
    }
    public event PropertyChangedEventHandler PropertyChanged;
}
```

이 모든 게 결국 옵저버 패턴이다. 다르게 보일 뿐이다.

### 양방향 바인딩 (View ↔ ViewModel)

입력 필드처럼 사용자가 값을 바꾸기도 하고 ViewModel이 바꾸기도 하는 경우다. 흔히 보는 `v-model`, WPF의 `Mode=TwoWay`가 이것이다.

양방향 바인딩의 동작은 두 개의 단방향 바인딩이 맞물린 것이다.

```
ViewModel.name = "kim"  →  View 입력칸이 "kim"으로 갱신 (단방향)
사용자가 "lee" 입력      →  ViewModel.name = "lee"로 갱신 (단방향)
```

이때 *무한 루프*가 위험하다. ViewModel이 값을 바꿔서 View가 갱신되고, 그 갱신이 다시 ViewModel을 호출하는 식이다. 라이브러리들은 보통 "값이 이전과 같으면 알림을 발행하지 않는다"는 가드로 이 루프를 끊는다. 직접 양방향 바인딩을 구현할 일이 있으면 이 가드를 반드시 넣어야 한다.

```typescript
set value(newVal: string) {
    if (this._value === newVal) return;  // 무한 루프 방지
    this._value = newVal;
    this.notify();
}
```

### 변경 감지 비용

바인딩이 공짜로 동작하는 것처럼 보이지만 매번 비용이 따라온다. 어떤 환경에서 얼마나 무거운지를 알아야 큰 화면을 짤 때 헛수고를 줄일 수 있다.

- **WPF**: PropertyChanged 이벤트가 발행되면 바인딩 엔진이 reflection 기반으로 대상 프로퍼티를 찾아 갱신한다. 한 화면에 수천 개 바인딩이 깔리면 reflection 비용이 누적된다. `Mode=OneTime`으로 바꿀 수 있는 건 바꾸는 게 답이다.
- **Android LiveData/StateFlow**: lifecycle-aware 옵저버를 통해 갱신된다. 액티비티가 백그라운드면 알림을 건너뛴다. 다만 `combine`이나 `map`을 무겁게 체이닝하면 main 스레드에서 비용이 누적된다.
- **Vue 3**: Proxy로 의존성 추적이 자동이라 편하지만, 깊게 중첩된 객체를 `reactive`로 감싸면 모든 하위 속성마다 Proxy가 생긴다. 큰 트리에는 `shallowRef`나 `markRaw`로 의도적으로 추적을 끊어야 한다.
- **React**: 엄밀히는 MVVM이 아니지만 Zustand/Jotai/Recoil 같은 라이브러리가 ViewModel 역할을 한다. setState가 부르는 리렌더 범위를 `useMemo`/`React.memo`로 좁히지 않으면 트리 전체가 다시 그려진다.

화면이 멈춰 보이거나 입력 지연이 생길 때 가장 먼저 의심해야 할 게 *바인딩 폭주*다.

---

## 4. Command 패턴

ViewModel이 노출하는 두 번째 축이 Command다. "사용자가 저장 버튼을 눌렀다"는 사건을 ViewModel이 어떻게 받느냐의 문제다.

가장 단순한 형태는 메서드다.

```kotlin
class LoginViewModel {
    fun submit() { /* ... */ }
}
```

WPF는 `ICommand` 인터페이스를 표준으로 제공한다.

```csharp
public class LoginViewModel
{
    public ICommand SubmitCommand { get; }

    public LoginViewModel()
    {
        SubmitCommand = new RelayCommand(
            execute: _ => Submit(),
            canExecute: _ => !string.IsNullOrEmpty(Email)
        );
    }
}
```

`ICommand`가 메서드보다 가지는 장점은 `CanExecute`다. 버튼의 활성/비활성 상태를 Command 자체가 알고 있어서 View는 따로 분기할 필요가 없다. `<Button Command="{Binding SubmitCommand}" />`만 적으면 `CanExecute`가 false일 때 버튼이 자동으로 비활성화된다.

이 발상은 다른 환경에서도 그대로 적용된다.

```kotlin
// Android
val canSubmit: StateFlow<Boolean> = email.map { it.contains("@") }
    .stateIn(viewModelScope, SharingStarted.Eagerly, false)
```

```vue
<!-- Vue -->
<button :disabled="!canSubmit" @click="submit">저장</button>
```

핵심은 *버튼이 눌릴 수 있는지의 판단을 View가 하지 않는다*는 것이다. ViewModel이 상태로 가지고 있어야 한다.

### 비동기 Command의 함정

Submit 같은 동작은 거의 다 비동기다. 네트워크 호출이 진행 중일 때 사용자가 버튼을 또 누르는 일을 막아야 한다. 직접 짜는 코드는 보통 이렇게 시작한다.

```kotlin
fun submit() {
    viewModelScope.launch {
        api.save(form)
    }
}
```

여기에 빠진 게 세 가지다.

1. 진행 중인지 알리는 `isSubmitting` 상태
2. 진행 중일 때 다시 못 누르게 막는 가드
3. 에러를 어디로 흘려보낼지

제대로 짜면 이렇게 된다.

```kotlin
private val _isSubmitting = MutableStateFlow(false)
val isSubmitting: StateFlow<Boolean> = _isSubmitting

private val _errors = MutableSharedFlow<String>()
val errors: SharedFlow<String> = _errors

fun submit() {
    if (_isSubmitting.value) return
    viewModelScope.launch {
        _isSubmitting.value = true
        try {
            api.save(form)
        } catch (e: Exception) {
            _errors.emit(e.message ?: "알 수 없는 오류")
        } finally {
            _isSubmitting.value = false
        }
    }
}
```

이 정도가 비동기 Command의 최소 골격이다. 라이브러리에 따라 `MutableSharedFlow` 대신 토스트 채널이나 이벤트 큐를 쓰지만, 핵심은 동일하다.

---

## 5. 상태 관리

MVVM에서 상태 관리란 결국 *ViewModel을 어떻게 묶고 쪼개느냐*의 문제다.

### 화면당 하나의 ViewModel

가장 흔한 출발점이다. 화면(Activity, Page, Route)마다 ViewModel 하나를 둔다. WPF, Android, SwiftUI가 모두 이 방식을 따른다.

장점은 명확하다. ViewModel의 생명주기가 화면과 일치한다. 화면이 사라지면 ViewModel도 같이 정리된다.

단점은 두 가지다.

- 화면 사이의 공유 상태가 자연스럽게 사라진다. 예를 들어 *현재 로그인한 유저*는 여러 화면이 알아야 하는데, 각 ViewModel이 따로 들고 있으면 동기화가 망가진다.
- 한 화면이 너무 복잡하면 ViewModel이 거대해진다. (안티패턴 절에서 다룬다)

### 공유 상태를 따로 빼는 방법

전역으로 살아남는 상태는 ViewModel 바깥에 둬야 한다. Android는 보통 `Repository` 계층에서, Vue는 Pinia, React는 Zustand/Jotai 같은 store가 그 자리를 차지한다.

```kotlin
// 전역 single source
class AuthRepository {
    private val _currentUser = MutableStateFlow<User?>(null)
    val currentUser: StateFlow<User?> = _currentUser
    fun signIn(user: User) { _currentUser.value = user }
    fun signOut() { _currentUser.value = null }
}

// 각 ViewModel은 같은 repository를 주입받아 같은 StateFlow를 본다
class HomeViewModel(authRepo: AuthRepository) {
    val greeting = authRepo.currentUser.map { "안녕, ${it?.name ?: "손님"}" }
}
```

이 구조의 이점은 *한 곳을 갱신하면 모든 화면이 같이 갱신된다*는 점이다. 로그인이 끝나서 `AuthRepository.signIn`을 호출하면 홈 화면 인사말, 헤더 프로필, 사이드바 메뉴가 동시에 바뀐다.

### ViewModel 사이의 의존

ViewModel이 다른 ViewModel을 직접 참조하는 건 피해야 한다. 대신 공통 의존(Repository, UseCase, Service)을 두 ViewModel이 같이 주입받는 구조를 만든다. 그래야 ViewModel의 생명주기가 서로 엉키지 않는다.

---

## 6. 실제 구현 예제

같은 화면("이메일을 입력하고 회원가입 버튼을 누르면 가입 처리")을 네 환경에서 어떻게 짜는지 비교한다.

### WPF

```csharp
public class SignUpViewModel : ObservableObject
{
    private string _email = "";
    public string Email
    {
        get => _email;
        set => SetProperty(ref _email, value);
    }

    public bool CanSubmit => Email.Contains("@");

    public ICommand SubmitCommand { get; }

    public SignUpViewModel(IUserService service)
    {
        SubmitCommand = new AsyncRelayCommand(
            execute: () => service.SignUp(Email),
            canExecute: () => CanSubmit
        );
    }
}
```

```xml
<TextBox Text="{Binding Email, UpdateSourceTrigger=PropertyChanged}" />
<Button Command="{Binding SubmitCommand}" Content="가입" />
```

### Android (Kotlin + Jetpack)

```kotlin
class SignUpViewModel(
    private val service: UserService
) : ViewModel() {
    val email = MutableStateFlow("")
    val canSubmit = email.map { it.contains("@") }
        .stateIn(viewModelScope, SharingStarted.Eagerly, false)
    val isSubmitting = MutableStateFlow(false)

    fun submit() {
        if (isSubmitting.value) return
        viewModelScope.launch {
            isSubmitting.value = true
            try { service.signUp(email.value) }
            finally { isSubmitting.value = false }
        }
    }
}
```

```xml
<EditText android:text="@={viewModel.email}" />
<Button
    android:onClick="@{() -> viewModel.submit()}"
    android:enabled="@{viewModel.canSubmit}" />
```

### Vue 3

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { signUpApi } from '@/api'

const email = ref('')
const isSubmitting = ref(false)
const canSubmit = computed(() => email.value.includes('@'))

async function submit() {
    if (isSubmitting.value) return
    isSubmitting.value = true
    try { await signUpApi(email.value) }
    finally { isSubmitting.value = false }
}
</script>

<template>
    <input v-model="email" />
    <button :disabled="!canSubmit || isSubmitting" @click="submit">가입</button>
</template>
```

Vue는 `<script setup>` 자체가 ViewModel이라고 봐도 된다. `ref`, `computed`가 바인딩 가능한 상태, 함수가 Command다.

### React (Zustand 조합)

```typescript
import { create } from 'zustand'
import { signUpApi } from './api'

type SignUpVM = {
    email: string
    isSubmitting: boolean
    canSubmit: () => boolean
    setEmail: (v: string) => void
    submit: () => Promise<void>
}

export const useSignUpVM = create<SignUpVM>((set, get) => ({
    email: '',
    isSubmitting: false,
    canSubmit: () => get().email.includes('@'),
    setEmail: (v) => set({ email: v }),
    submit: async () => {
        if (get().isSubmitting) return
        set({ isSubmitting: true })
        try { await signUpApi(get().email) }
        finally { set({ isSubmitting: false }) }
    }
}))

function SignUpForm() {
    const vm = useSignUpVM()
    return (
        <>
            <input value={vm.email} onChange={(e) => vm.setEmail(e.target.value)} />
            <button disabled={!vm.canSubmit() || vm.isSubmitting} onClick={vm.submit}>
                가입
            </button>
        </>
    )
}
```

React는 양방향 바인딩 문법을 언어 차원에서 막아놨기 때문에 `value`와 `onChange`를 명시적으로 적어야 한다. 그래서 React가 MVVM이냐 아니냐를 두고 논쟁이 있지만, 패턴의 의도는 같다.

---

## 7. 백엔드가 MVVM 프론트와 일할 때 주의할 점

이 절이 이 문서에서 가장 실무적인 부분이다.

### 응답 형태를 ViewModel 친화적으로 만들지, 도메인 그대로 던질지

극단을 보면 이렇다.

A안. 도메인 그대로 던진다.

```json
{
    "id": 12,
    "email": "kim@example.com",
    "createdAt": "2023-01-04T10:23:00Z",
    "role": "ADMIN"
}
```

B안. 화면이 필요한 형태로 가공해서 던진다.

```json
{
    "displayName": "kim",
    "joinedYearsAgo": 2,
    "isAdminBadgeVisible": true
}
```

A안의 장점은 백엔드가 변경되지 않는다는 것이다. 단점은 프론트가 매번 같은 변환을 반복한다는 것이다.

B안의 장점은 프론트가 받자마자 그대로 바인딩만 하면 된다는 것이다. 단점은 *백엔드 응답이 화면 디자인에 끌려다닌다*는 점이다. 화면이 바뀌면 API도 바뀐다.

실무에서는 보통 절충한다. 도메인을 던지되, 화면 전용 가공이 무거운 경우만 별도 엔드포인트로 뽑는다. 예를 들어 `/users/12`는 도메인을 던지고, `/users/12/profile-card`는 카드 화면 전용 응답을 던진다. BFF(Backend for Frontend) 패턴이 이 절충의 한 형태다.

### 상태 동기화의 출처

MVVM 프론트는 *모든 상태가 ViewModel에 있다*는 가정 위에서 동작한다. 백엔드에서 데이터가 바뀐 걸 프론트가 모르면 ViewModel이 거짓말을 하게 된다. 처리 방법은 보통 셋 중 하나다.

- **Polling**: 일정 주기로 다시 GET한다. 가장 단순하지만 트래픽이 늘고 실시간성이 떨어진다.
- **WebSocket / SSE**: 백엔드가 변경을 푸시한다. ViewModel은 푸시를 받아 상태를 갱신한다. 실시간성이 좋지만 연결 관리가 복잡하다.
- **낙관적 업데이트(optimistic update)**: 사용자 입력 직후 ViewModel을 먼저 갱신하고, 서버 응답이 늦거나 실패하면 롤백한다. 응답성은 최고지만 롤백 로직이 까다롭다.

ViewModel 안에 들어가는 데이터가 *얼마나 최신이어야 하는가*를 백엔드가 미리 합의해두지 않으면 프론트가 매번 다르게 짜고, 화면마다 동작이 달라진다.

### ETag, 버전, 동시 수정

낙관적 업데이트와 동시 수정이 만나면 그날 야근이 확정된다. 두 사용자가 같은 리소스를 수정할 때 누가 마지막에 저장하느냐로 데이터가 덮인다.

해결은 보통 ETag 또는 version 필드다.

```http
GET /users/12
ETag: "v17"

PUT /users/12
If-Match: "v17"
```

서버는 현재 버전이 17이 아니면 409 Conflict를 반환한다. 프론트의 ViewModel은 이 409를 받아서 "다른 사용자가 먼저 수정했습니다. 다시 불러올까요?" 같은 흐름을 처리한다.

ViewModel이 단순히 `currentUser`만 가지고 있으면 이 흐름을 짤 수 없다. ETag나 version도 ViewModel에 같이 들고 있어야 한다. 응답 DTO에 `_version` 필드를 같이 내려주는 백엔드는 그래서 일 잘하는 백엔드다.

### 에러 모델

프론트 ViewModel이 에러를 받아서 화면에 적절히 분기하려면 *에러가 일관된 형태*여야 한다. 어떤 엔드포인트는 `{ "error": "string" }`, 어떤 엔드포인트는 `{ "errors": [{...}] }`, 어떤 엔드포인트는 그냥 500 빈 응답이면 프론트가 매번 다르게 처리하다가 한 화면이 빠진다.

RFC 7807 (Problem Details for HTTP APIs)이 표준이긴 한데, 사내에서 형태를 하나로 정하기만 해도 충분하다.

```json
{
    "type": "VALIDATION",
    "code": "EMAIL_DUPLICATED",
    "message": "이미 사용 중인 이메일입니다",
    "fields": { "email": "EMAIL_DUPLICATED" }
}
```

`fields`까지 같이 내려주면 프론트 ViewModel이 `emailError` 같은 필드별 상태에 그대로 바인딩한다. 메시지를 프론트에서 만들 필요도 없다.

---

## 8. 테스트 용이성

MVVM의 가장 큰 실용적 장점이 *ViewModel을 UI 없이 단독으로 테스트할 수 있다*는 점이다.

```kotlin
@Test
fun `이메일에 @가 없으면 submit이 비활성화된다`() = runTest {
    val service = FakeUserService()
    val vm = SignUpViewModel(service)

    vm.email.value = "invalid"
    advanceUntilIdle()

    assertFalse(vm.canSubmit.value)
}

@Test
fun `submit 진행 중에는 중복 호출이 무시된다`() = runTest {
    val service = FakeUserService(delayMs = 1000)
    val vm = SignUpViewModel(service)
    vm.email.value = "kim@example.com"

    vm.submit()
    vm.submit()  // 즉시 두 번째 호출
    advanceTimeBy(2000)

    assertEquals(1, service.callCount)
}
```

이 테스트는 Android Studio 없이 JVM 위에서만 돌아간다. 화면이 없어도 가설을 검증할 수 있다.

같은 테스트를 MVC로 짜려면 Activity를 띄우고 클릭 이벤트를 시뮬레이션해야 한다. MVP라면 View 인터페이스를 Mock으로 만들고, 메서드가 호출됐는지 검증해야 한다. MVVM은 *상태만 검사하면 끝*이다.

다만 비동기 코드의 테스트는 어렵다. `runTest`, `TestDispatcher`, `advanceUntilIdle` 같은 도구를 정확히 써야 한다. 안 그러면 "테스트가 끝났는데 비동기 작업이 안 끝남"이라는 거짓 통과가 나온다.

---

## 9. 안티패턴

MVVM을 도입했다고 모든 게 깔끔해지는 건 아니다. 잘못 짜면 MVC보다 나빠지는 경우도 있다.

### 거대 ViewModel

가장 흔하다. 한 화면이 복잡해지면서 ViewModel이 2000줄짜리 신이 된다. 사용자 프로필, 결제 내역, 알림 설정, 친구 목록을 한 화면이 다 보여주면 그 화면 ViewModel은 정말로 그 네 가지를 다 안다.

해결은 *ViewModel을 화면 단위가 아니라 컴포넌트 단위로 쪼개는 것*이다. 프로필 카드 ViewModel, 결제 내역 ViewModel을 따로 만들고, 화면은 그 ViewModel들을 조립해서 보여준다.

```kotlin
class MyPageViewModel(
    val profile: ProfileCardViewModel,
    val payments: PaymentHistoryViewModel,
    val notifications: NotificationSettingsViewModel
)
```

각각 자기 책임만 가진다. 테스트도 따로 쓸 수 있다.

### View 로직이 ViewModel에 새는 경우

반대 안티패턴이다. ViewModel이 색상이나 픽셀을 다룬다.

```kotlin
// 잘못된 예
class UserViewModel {
    val nameColor = MutableStateFlow("#FF0000")  // 어드민이면 빨강
    val nameSize = MutableStateFlow(18)  // sp 단위
}
```

이건 View 책임이다. ViewModel은 `isAdmin` 같은 *의미*만 노출하고, 그 의미를 보고 빨갛게 칠할지 말지는 View가 결정한다.

```kotlin
// 올바른 예
class UserViewModel {
    val isAdmin = MutableStateFlow(false)
}

// View
nameLabel.setTextColor(if (vm.isAdmin.value) Color.RED else Color.BLACK)
```

이 분리가 깨지면 디자인 시스템을 바꿀 때 ViewModel을 다 뜯어야 한다.

### View 로직이 View에 새는 경우 (반대 방향)

또 흔하다. 의미상 ViewModel에 있어야 할 로직이 View에 있다.

```kotlin
// View
if (vm.user.value.role == "ADMIN" && vm.user.value.createdAt.isBefore(twoYearsAgo)) {
    veteranBadge.visibility = View.VISIBLE
}
```

이런 로직은 ViewModel로 옮겨야 한다.

```kotlin
val isVeteranBadgeVisible = user.map {
    it.role == Role.ADMIN && it.createdAt.isBefore(twoYearsAgo)
}.stateIn(...)
```

View는 그저 `binding.veteranBadge.isVisible = vm.isVeteranBadgeVisible.value`만 적는다. View에 분기가 있으면 단위 테스트가 불가능해진다.

### 바인딩 누수

옵저버를 등록하고 해제하지 않으면 메모리 누수가 발생한다. 화면이 닫혔는데 ViewModel이 계속 살아서 사라진 View를 갱신하려고 한다.

```kotlin
// 잘못된 예
vm.name.collect { binding.nameLabel.text = it }  // 어디서도 해제 안 됨
```

Android는 `viewLifecycleOwner.lifecycleScope`, WPF는 `Unloaded` 이벤트, Vue는 `onUnmounted`로 정리해야 한다.

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    repeatOnLifecycle(Lifecycle.State.STARTED) {
        vm.name.collect { binding.nameLabel.text = it }
    }
}
```

`repeatOnLifecycle`은 화면이 백그라운드로 가면 collect를 멈췄다가 다시 돌아오면 재개한다. 이게 빠지면 *백그라운드 화면이 계속 갱신되어 메모리와 배터리를 낭비*한다.

### 이벤트와 상태를 섞어 쓰는 실수

토스트 메시지나 화면 이동 같은 *일회성 이벤트*를 `StateFlow`에 담으면 안 된다. 화면이 회전되어 ViewModel을 다시 구독하는 순간, 같은 토스트가 또 뜬다.

```kotlin
// 잘못된 예 — 화면 회전 시 같은 토스트가 다시 뜬다
val errorMessage = MutableStateFlow<String?>(null)
```

이런 건 `Channel`이나 `SharedFlow(replay = 0)`로 처리해야 한다.

```kotlin
private val _errors = Channel<String>()
val errors = _errors.receiveAsFlow()
```

`Channel`은 한 번 소비되면 사라진다. 상태는 `StateFlow`, 이벤트는 `Channel`로 구분해야 한다. 이 구분이 처음에는 헷갈리는데, "구독자가 새로 들어왔을 때 이 값을 다시 보여줘야 하나?"를 기준으로 판단하면 거의 틀리지 않는다.

---

## 10. 정리하지 않는 정리

MVVM은 데이터 바인딩이라는 도구가 잘 갖춰진 환경에서 가장 빛난다. 바인딩 라이브러리가 없으면 MVVM은 MVP의 변종에 불과하다. 반대로 바인딩이 잘 자리 잡으면, 화면이 늘어나도 코드가 산발적으로 부풀지 않고 ViewModel만 늘어난다.

백엔드 개발자가 가장 자주 망치는 부분은 *ViewModel을 도메인 모델로 착각*하는 것이다. ViewModel은 도메인이 아니다. 화면이 무엇을 보여줄 것인가에 대한 *결정*이 들어 있는 객체다. 도메인은 백엔드에 있고, ViewModel은 그 도메인을 받아서 화면용으로 *번역*하는 계층이다. 이 두 층을 섞으면 백엔드가 화면 디자인에 끌려다니거나, 프론트가 매번 같은 변환을 반복한다.

가장 마지막으로 기억할 것 하나만 꼽으면, *ViewModel은 View 없이도 인스턴스화돼야 한다*는 것이다. 이 한 줄이 깨지지 않으면 나머지 대부분은 따라온다.
