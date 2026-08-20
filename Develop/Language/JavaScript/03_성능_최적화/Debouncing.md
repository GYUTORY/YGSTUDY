---
title: JavaScript 디바운싱(Debouncing)
tags: [language, javascript]
updated: 2025-08-10
---

# JavaScript 디바운싱(Debouncing)

## 배경

디바운싱은 연속으로 발생하는 이벤트를 하나로 묶어 마지막 이벤트만 처리하는 기법이다.

### 디바운싱의 필요성
실생활에 빗대면 이렇다.
- **엘리베이터 버튼**: 여러 사람이 연달아 눌러도 엘리베이터는 한 번만 움직인다
- **자동문**: 사람들이 줄줄이 지나가도 문은 한 번만 열리고 닫힌다

웹 개발이라면 이렇다.
- 사용자가 검색창에 "안녕하세요"를 타이핑할 때
- 각 글자를 입력할 때마다 API를 호출하는 대신
- 타이핑을 멈추고 300ms가 지난 뒤에만 API를 호출한다

### 디바운싱 vs 쓰로틀링

| 구분 | 디바운싱 | 쓰로틀링 |
|------|----------|----------|
| 동작 | 마지막 이벤트만 실행 | 일정 간격으로 실행 |
| 예시 | 검색 자동완성 | 스크롤 이벤트 |
| 타이밍 | 이벤트 발생 후 대기 | 이벤트 발생 즉시 실행 후 대기 |

## 핵심

### 1. 성능 문제 해결

#### 문제 상황과 해결 방법
```javascript
// 문제가 있는 코드
const searchInput = document.getElementById('searchInput');

searchInput.addEventListener('input', (e) => {
    // 사용자가 "안녕하세요"를 타이핑하면
    // "안" → API 호출
    // "안녕" → API 호출  
    // "안녕하" → API 호출
    // "안녕하세" → API 호출
    // "안녕하세요" → API 호출
    // 총 5번의 API 호출이 발생!
    searchAPI(e.target.value);
});

// 디바운싱을 적용한 코드
const debouncedSearch = debounce(searchAPI, 300);

searchInput.addEventListener('input', (e) => {
    // 사용자가 "안녕하세요"를 타이핑하면
    // 타이핑을 멈춘 후 300ms 후에만 API 호출
    // 결과적으로 1번의 API 호출만 발생!
    debouncedSearch(e.target.value);
});
```

### 2. 서버 부하 감소

- **API 호출 횟수 감소**: 쓸데없는 네트워크 요청을 막는다
- **데이터베이스 부하 감소**: 중복 쿼리 실행을 막는다
- **비용 절약**: 클라우드 서비스 사용량이 줄어든다

### 3. 사용자 경험 개선

- **빠른 응답**: 군더더기 연산이 사라져 UI 반응성이 좋아진다
- **일관된 결과**: 마지막 입력값에 대한 정확한 결과가 나온다
- **배터리 절약**: 모바일 기기에서 배터리 소모가 준다

### 4. 디바운싱의 동작 원리

#### 기본 개념
1. **이벤트 발생**: 사용자가 이벤트를 발생시킨다
2. **타이머 시작**: 일정 시간(예: 300ms) 타이머를 건다
3. **새 이벤트 발생**: 타이머가 끝나기 전에 새 이벤트가 들어온다
4. **타이머 리셋**: 기존 타이머를 취소하고 새 타이머를 건다
5. **최종 실행**: 마지막 이벤트 후 지정된 시간이 지나면 함수가 실행된다

#### 시각적 설명
```javascript
// 이벤트 발생: [입력] [입력] [입력] [입력] [입력]
// 타이머:      [300ms] [300ms] [300ms] [300ms] [실행]
// 결과:        마지막 입력 후 300ms 뒤에만 실행됨
```

### 5. 기본 디바운스 함수 구현

#### 기본 디바운스 함수
```javascript
// 기본 디바운스 함수
function debounce(func, delay) {
    let timeoutId;
    
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

// 사용 예시
const debouncedFunction = debounce(() => {
    console.log('디바운스 실행!');
}, 300);

// 연속으로 호출해도 마지막에 한 번만 실행
for (let i = 0; i < 5; i++) {
    setTimeout(() => {
        debouncedFunction();
    }, i * 100);
}
```

#### 고급 디바운스 함수 (즉시 실행 옵션)
```javascript
// 고급 디바운스 함수
function advancedDebounce(func, delay, options = {}) {
    let timeoutId;
    const { immediate = false } = options;
    
    return function(...args) {
        const callNow = immediate && !timeoutId;
        
        clearTimeout(timeoutId);
        
        timeoutId = setTimeout(() => {
            timeoutId = null;
            if (!immediate) {
                func.apply(this, args);
            }
        }, delay);
        
        if (callNow) {
            func.apply(this, args);
        }
    };
}

// 사용 예시
const immediateDebounced = advancedDebounce(() => {
    console.log('즉시 실행 + 디바운스');
}, 300, { immediate: true });
```

## 예시

### 1. 실제 사용 예시

#### 검색 자동완성
```javascript
// 검색 자동완성 컴포넌트
class SearchAutocomplete {
    constructor(inputElement, suggestionsContainer) {
        this.input = inputElement;
        this.container = suggestionsContainer;
        this.debouncedSearch = debounce(this.performSearch.bind(this), 300);
        this.init();
    }
    
    init() {
        this.input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query.length > 0) {
                this.debouncedSearch(query);
            } else {
                this.clearSuggestions();
            }
        });
    }
    
    async performSearch(query) {
        try {
            this.showLoading();
            
            // 실제 API 호출 시뮬레이션
            const results = await this.searchAPI(query);
            this.displaySuggestions(results);
        } catch (error) {
            console.error('검색 오류:', error);
            this.showError();
        }
    }
    
    async searchAPI(query) {
        return new Promise(resolve => {
            setTimeout(() => {
                resolve([
                    `${query} 관련 결과 1`,
                    `${query} 관련 결과 2`,
                    `${query} 관련 결과 3`
                ]);
            }, 200);
        });
    }
    
    displaySuggestions(suggestions) {
        this.container.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.textContent = suggestion;
            div.addEventListener('click', () => {
                this.input.value = suggestion;
                this.clearSuggestions();
            });
            this.container.appendChild(div);
        });
    }
    
    showLoading() {
        this.container.innerHTML = '<div class="loading">검색 중...</div>';
    }
    
    showError() {
        this.container.innerHTML = '<div class="error">검색 중 오류가 발생했습니다.</div>';
    }
    
    clearSuggestions() {
        this.container.innerHTML = '';
    }
}

// 사용 예시
const searchInput = document.getElementById('search-input');
const suggestionsContainer = document.getElementById('suggestions');
const autocomplete = new SearchAutocomplete(searchInput, suggestionsContainer);
```

디바운스는 **요청 수를 줄일 뿐 순서를 보장하지 않는다.** 타이핑을 잠깐 멈췄다가 이어 치면 요청 두 개가 모두 나가고, 늦게 보낸 것이 먼저 도착할 수 있다.

```
화면 표시: 서울시 결과     ← 나중에 보낸 요청이 먼저 왔다
화면 표시: 서울 결과       ← 먼저 보낸 요청이 뒤늦게 도착해 덮어썼다
최종 화면 = 서울 결과       (마지막에 입력한 것은 '서울시')
```

`displaySuggestions` 가 도착 순서대로 화면을 갈아치우기 때문에 **마지막에 도착한 낡은 응답**이 남는다. 사용자에게는 검색어와 결과가 안 맞는 것으로 보이고, 재현이 네트워크 상황에 달려 있어 개발 중에는 거의 안 나타난다.

디바운스 시간을 늘려도 해결되지 않는다. 두 요청이 모두 나가는 상황 자체를 막지 못하기 때문이다. 필요한 것은 **취소** 아니면 **순번 확인**이다.

```javascript
// 1) 이전 요청을 취소한다
let controller;
async function performSearch(query) {
  controller?.abort();
  controller = new AbortController();
  try {
    const res = await fetch(url, { signal: controller.signal });
    this.displaySuggestions(await res.json());
  } catch (e) {
    if (e.name !== 'AbortError') throw e;   // 취소는 에러가 아니다
  }
}

// 2) 취소할 수 없는 API 라면 순번을 붙여 늦게 온 것을 버린다
let seq = 0;
async function performSearch(query) {
  const mine = ++seq;
  const results = await this.searchAPI(query);
  if (mine !== seq) return;                 // 그 사이 새 요청이 나갔으면 폐기
  this.displaySuggestions(results);
}
```

`AbortError` 를 일반 에러와 함께 잡아 `showError()` 를 부르면, 정상 취소마다 "검색 중 오류가 발생했습니다"가 뜬다. 취소는 에러 처리에서 걸러야 한다.

같은 문제가 아래 `FormValidator` 에도 있다. `input` 은 500ms 디바운스인데 `blur` 는 `validateField` 를 **곧바로** 부른다. 입력하다 바로 다른 칸으로 옮기면 즉시 검증이 먼저 돌고, 대기 중이던 디바운스가 그 뒤에 옛 값으로 다시 돌아 방금 띄운 결과를 덮는다. 즉시 검증 쪽에서 `debouncedValidate.cancel()` 을 먼저 불러야 한다 — 그러려면 디바운스 함수가 `cancel` 을 제공해야 하고, 이 문서의 기본 `debounce` 에는 그게 없다.

#### 폼 검증
```javascript
// 폼 검증 컴포넌트
class FormValidator {
    constructor(formElement) {
        this.form = formElement;
        this.fields = {};
        this.init();
    }
    
    init() {
        const inputs = this.form.querySelectorAll('input[data-validate]');
        
        inputs.forEach(input => {
            const validationType = input.dataset.validate;
            const debouncedValidate = debounce(
                this.validateField.bind(this, input, validationType),
                500
            );
            
            input.addEventListener('input', debouncedValidate);
            input.addEventListener('blur', () => {
                this.validateField(input, validationType);
            });
        });
    }
    
    validateField(input, type) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        switch (type) {
            case 'email':
                isValid = this.isValidEmail(value);
                errorMessage = '유효한 이메일 주소를 입력해주세요.';
                break;
            case 'password':
                isValid = this.isValidPassword(value);
                errorMessage = '비밀번호는 8자 이상이어야 합니다.';
                break;
            case 'username':
                isValid = this.isValidUsername(value);
                errorMessage = '사용자명은 3-20자 사이여야 합니다.';
                break;
        }
        
        this.showFieldValidation(input, isValid, errorMessage);
        return isValid;
    }
    
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    isValidPassword(password) {
        return password.length >= 8;
    }
    
    isValidUsername(username) {
        return username.length >= 3 && username.length <= 20;
    }
    
    showFieldValidation(input, isValid, errorMessage) {
        const errorElement = input.parentNode.querySelector('.error-message');
        
        if (isValid) {
            input.classList.remove('error');
            input.classList.add('valid');
            if (errorElement) {
                errorElement.remove();
            }
        } else {
            input.classList.remove('valid');
            input.classList.add('error');
            
            if (!errorElement) {
                const error = document.createElement('div');
                error.className = 'error-message';
                error.textContent = errorMessage;
                input.parentNode.appendChild(error);
            }
        }
    }
}

// 사용 예시
const form = document.getElementById('signup-form');
const validator = new FormValidator(form);
```

### 2. 고급 디바운싱 패턴

#### 디바운싱 관리자
```javascript
// 디바운싱 관리자 클래스
class DebounceManager {
    constructor() {
        this.debouncedFunctions = new Map();
    }
    
    // 함수를 디바운싱으로 래핑
    debounce(key, func, delay, options = {}) {
        if (this.debouncedFunctions.has(key)) {
            return this.debouncedFunctions.get(key);
        }
        
        const debouncedFunc = this.createDebouncedFunction(func, delay, options);
        this.debouncedFunctions.set(key, debouncedFunc);
        
        return debouncedFunc;
    }
    
    // 디바운싱 함수 생성
    createDebouncedFunction(func, delay, options = {}) {
        let timeoutId;
        const { immediate = false, maxWait = null } = options;
        let lastCallTime = 0;
        
        const debouncedFunc = function(...args) {
            const now = Date.now();
            const timeSinceLastCall = now - lastCallTime;
            
            const callNow = immediate && !timeoutId;
            
            clearTimeout(timeoutId);
            
            // maxWait 옵션이 설정된 경우
            if (maxWait && timeSinceLastCall >= maxWait) {
                lastCallTime = now;
                func.apply(this, args);
                return;
            }
            
            timeoutId = setTimeout(() => {
                timeoutId = null;
                lastCallTime = Date.now();
                if (!immediate) {
                    func.apply(this, args);
                }
            }, delay);
            
            if (callNow) {
                lastCallTime = now;
                func.apply(this, args);
            }
        };
        
        // 취소 메서드 추가
        debouncedFunc.cancel = () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
        };
        
        // 즉시 실행 메서드 추가
        debouncedFunc.flush = function(...args) {
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
                lastCallTime = Date.now();
                func.apply(this, args);
            }
        };
        
        return debouncedFunc;
    }
    
    // 특정 함수 취소
    cancel(key) {
        const debouncedFunc = this.debouncedFunctions.get(key);
        if (debouncedFunc && debouncedFunc.cancel) {
            debouncedFunc.cancel();
        }
    }
    
    // 모든 함수 취소
    cancelAll() {
        for (const [key, debouncedFunc] of this.debouncedFunctions) {
            if (debouncedFunc.cancel) {
                debouncedFunc.cancel();
            }
        }
    }
    
    // 관리 중인 함수 목록
    getDebouncedFunctions() {
        return Array.from(this.debouncedFunctions.keys());
    }
}

// 사용 예시
const debounceManager = new DebounceManager();

const searchHandler = debounceManager.debounce('search', (query) => {
    console.log('검색 실행:', query);
}, 300);

const saveHandler = debounceManager.debounce('save', (data) => {
    console.log('저장 실행:', data);
}, 1000, { maxWait: 5000 }); // 최대 5초 대기

// 사용
searchHandler('검색어');
saveHandler({ user: 'data' });
```

`maxWait` 를 준 `saveHandler` 는 **첫 호출부터 디바운스를 건너뛴다.**

```
저장 실행! 호출 후 1ms
```

`lastCallTime` 이 `0` 으로 시작하기 때문이다. 첫 호출에서 `timeSinceLastCall = Date.now() - 0` 은 1조가 넘는 값이고, `timeSinceLastCall >= maxWait` 가 당연히 참이라 곧바로 `func` 를 부르고 `return` 한다. "최대 5초까지는 미뤄도 된다"는 옵션이 "무조건 즉시 실행"으로 뒤집혔다.

자동 저장에 붙였다면 편집을 시작하자마자 첫 저장 요청이 나간다. 두 번째 호출부터는 정상이라, 로그를 보면 첫 줄만 이상하고 나머지는 멀쩡해서 넘어가기 쉽다.

`lastCallTime` 을 `0` 이 아니라 첫 호출 시각으로 초기화하거나, `maxWait` 판정 앞에 "대기 중인 타이머가 있을 때만"이라는 조건을 넣어야 한다. **`Date.now() - 0` 은 언제나 거대한 수**라는 것이 이 부류 버그의 공통점이다.

`DebounceManager.debounce` 에도 함정이 있다. 같은 `key` 로 다시 부르면 **인자로 준 함수와 delay 를 통째로 무시하고** 처음 등록한 것을 돌려준다.

```javascript
const h1 = manager.debounce('search', () => console.log('첫 번째'), 300);
const h2 = manager.debounce('search', () => console.log('두 번째'), 300);

h2();            // '첫 번째'  ← 새로 준 함수가 아니다
h1 === h2;       // true
```

컴포넌트가 다시 마운트되면서 새 클로저(새 상태를 참조하는)로 등록하면 옛 클로저가 계속 살아 있는다. 화면은 갱신됐는데 저장되는 값은 예전 것인 상황이 여기서 나온다. 캐시가 목적이라면 최소한 함수와 delay 가 같은지 확인하거나, 키에 그 정보를 포함해야 한다.

`debounceWithLogging` 은 `func.apply(this, args)` 가 아니라 `func(...args)` 를 쓴다. **`this` 가 사라진다.**

```javascript
const obj = { name: 'OBJ', run: debounceWithLogging(function () { console.log(this?.name); }, 10) };
obj.run();   // undefined
```

디버깅용 래퍼를 잠깐 끼웠을 뿐인데 동작이 달라진다. 래퍼는 원본과 호출 규약이 같아야 한다 — `this` 와 인자를 그대로 넘기고, 반환값도 돌려준다.

## 운영 팁

### 성능 최적화

#### 적절한 지연 시간 설정
```javascript
// 상황별 최적 지연 시간
class DebounceTiming {
    static getOptimalDelay(useCase) {
        const timings = {
            search: 300,      // 검색: 300ms
            formValidation: 500,  // 폼 검증: 500ms
            windowResize: 250,    // 윈도우 리사이즈: 250ms
            scroll: 100,      // 스크롤: 100ms
            mousemove: 16,    // 마우스 이동: 16ms (60fps)
            apiCall: 1000,    // API 호출: 1000ms
            save: 2000        // 저장: 2000ms
        };
        
        return timings[useCase] || 300;
    }
    
    // 디바이스별 최적화
    static getDeviceOptimizedDelay(baseDelay) {
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const isSlowDevice = navigator.hardwareConcurrency <= 4;
        
        if (isMobile && isSlowDevice) return baseDelay * 2;
        if (isMobile) return baseDelay * 1.5;
        if (isSlowDevice) return baseDelay * 1.2;
        
        return baseDelay;
    }
}

// 사용 예시
const searchDelay = DebounceTiming.getOptimalDelay('search');
const optimizedDelay = DebounceTiming.getDeviceOptimizedDelay(searchDelay);

const optimizedSearch = debounce(searchAPI, optimizedDelay);
```

#### 메모리 누수 방지
```javascript
// 메모리 누수 방지를 위한 컴포넌트
class DebouncedComponent {
    constructor() {
        this.handlers = new Map();
        this.init();
    }
    
    init() {
        // 검색 핸들러
        this.handlers.set('search', debounce(this.handleSearch.bind(this), 300));
        
        // 저장 핸들러
        this.handlers.set('save', debounce(this.handleSave.bind(this), 1000));
        
        // 이벤트 리스너 등록
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        const searchInput = document.getElementById('search');
        if (searchInput) {
            searchInput.addEventListener('input', this.handlers.get('search'));
        }
        
        const saveButton = document.getElementById('save');
        if (saveButton) {
            saveButton.addEventListener('click', this.handlers.get('save'));
        }
    }
    
    handleSearch(event) {
        console.log('검색 처리:', event.target.value);
        // 실제 검색 로직
    }
    
    handleSave(event) {
        console.log('저장 처리');
        // 실제 저장 로직
    }
    
    // 컴포넌트 정리
    cleanup() {
        // 모든 디바운스 함수 취소
        for (const [key, handler] of this.handlers) {
            if (handler.cancel) {
                handler.cancel();
            }
        }
        
        // 이벤트 리스너 제거
        const searchInput = document.getElementById('search');
        if (searchInput) {
            searchInput.removeEventListener('input', this.handlers.get('search'));
        }
        
        const saveButton = document.getElementById('save');
        if (saveButton) {
            saveButton.removeEventListener('click', this.handlers.get('save'));
        }
        
        this.handlers.clear();
    }
}

// 사용 예시
const component = new DebouncedComponent();

// 컴포넌트가 더 이상 필요 없을 때
component.cleanup();
```

### 디버깅을 위한 로깅

#### 디바운싱 디버깅 도구
```javascript
// 디바운싱 디버깅을 위한 래퍼
function debounceWithLogging(func, delay, name = 'anonymous') {
    let timeoutId;
    let callCount = 0;
    let executionCount = 0;
    
    return function executedFunction(...args) {
        callCount++;
        const callNumber = callCount;
        
        console.log(`[${name}] 호출 #${callNumber} 발생 (총 ${callCount}번 호출)`);
        
        const later = () => {
            executionCount++;
            console.log(`[${name}] 호출 #${callNumber} 실행 (실제 실행: ${executionCount}번)`);
            console.log(`[${name}] 실행 시간: ${new Date().toLocaleTimeString()}`);
            func(...args);
        };
        
        clearTimeout(timeoutId);
        timeoutId = setTimeout(later, delay);
    };
}

// 사용 예시
const loggedSearch = debounceWithLogging(searchAPI, 300, '검색');
```

#### 성능 측정
```javascript
// 디바운싱 성능 측정
function debounceWithPerformance(func, delay) {
    let timeoutId;
    let startTime;
    
    return function executedFunction(...args) {
        if (!startTime) {
            startTime = performance.now();
        }
        
        const later = () => {
            const endTime = performance.now();
            const duration = endTime - startTime;
            
            console.log(`디바운스 실행 시간: ${duration.toFixed(2)}ms`);
            
            startTime = null;
            func(...args);
        };
        
        clearTimeout(timeoutId);
        timeoutId = setTimeout(later, delay);
    };
}

// 사용 예시
const performanceSearch = debounceWithPerformance(searchAPI, 300);
```

## 참고

### 디바운싱 사용 권장 사례

#### 적절한 사용 시나리오
```javascript
// 디바운싱이 적합한 경우들
const debounceUseCases = {
    search: {
        description: '검색 자동완성',
        delay: 300,
        reason: '사용자가 타이핑을 멈춘 후 검색 실행'
    },
    formValidation: {
        description: '폼 실시간 검증',
        delay: 500,
        reason: '입력 완료 후 검증 실행'
    },
    windowResize: {
        description: '윈도우 리사이즈 처리',
        delay: 250,
        reason: '리사이즈 완료 후 레이아웃 조정'
    },
    apiCall: {
        description: 'API 호출 제한',
        delay: 1000,
        reason: '서버 부하 방지'
    },
    save: {
        description: '자동 저장',
        delay: 2000,
        reason: '편집 완료 후 저장'
    }
};

// 사용 예시
Object.entries(debounceUseCases).forEach(([useCase, config]) => {
    console.log(`${useCase}: ${config.description} - ${config.delay}ms`);
});
```

### 결론
디바운싱은 웹 애플리케이션 성능을 크게 끌어올린다.
지연 시간을 얼마로 잡느냐가 성능 최적화의 핵심이다.
기기 성능에 따라 지연 시간을 다르게 주는 편이 낫다.
메모리 누수를 막으려면 컴포넌트를 정리할 때 디바운스 함수도 같이 정리한다.
디바운싱은 사용자 경험을 개선하면서 서버 부하까지 줄인다.






