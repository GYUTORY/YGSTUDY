# JavaScript 디바운싱(Debouncing) 완벽 가이드

## 목차
1. [디바운싱이란?](#디바운싱이란)
2. [왜 디바운싱이 필요한가?](#왜-디바운싱이-필요한가)
3. [디바운싱의 동작 원리](#디바운싱의-동작-원리)
4. [기본 디바운스 함수 구현](#기본-디바운스-함수-구현)
5. [실제 사용 예시](#실제-사용-예시)
6. [고급 디바운싱 패턴](#고급-디바운싱-패턴)
7. [성능 최적화 팁](#성능-최적화-팁)

## 디바운싱이란?

디바운싱(Debouncing)은 **연속적으로 발생하는 이벤트를 그룹화하여 마지막 이벤트만 처리하는 프로그래밍 기법**입니다.

### 쉽게 이해하기

실생활의 예시로 설명하면:
- **엘리베이터 버튼**: 여러 사람이 연속으로 버튼을 눌러도 엘리베이터는 한 번만 움직입니다
- **자동문**: 사람들이 연속으로 지나가도 문이 한 번만 열리고 닫힙니다

웹 개발에서는:
- 사용자가 검색창에 "안녕하세요"를 타이핑할 때
- 각 글자를 입력할 때마다 API를 호출하는 대신
- 타이핑을 멈춘 후 300ms가 지난 후에만 API를 호출합니다

### 디바운싱 vs 쓰로틀링

| 구분 | 디바운싱 | 쓰로틀링 |
|------|----------|----------|
| 동작 | 마지막 이벤트만 실행 | 일정 간격으로 실행 |
| 예시 | 검색 자동완성 | 스크롤 이벤트 |
| 타이밍 | 이벤트 발생 후 대기 | 이벤트 발생 즉시 실행 후 대기 |

## 왜 디바운싱이 필요한가?

### 1. 성능 문제 해결

**문제 상황:**
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
```

**해결 방법:**
```javascript
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

- **API 호출 횟수 감소**: 불필요한 네트워크 요청 방지
- **데이터베이스 부하 감소**: 중복 쿼리 실행 방지
- **비용 절약**: 클라우드 서비스 사용량 감소

### 3. 사용자 경험 개선

- **빠른 응답**: 불필요한 연산 제거로 UI 반응성 향상
- **일관된 결과**: 마지막 입력값에 대한 정확한 결과 제공
- **배터리 절약**: 모바일 기기에서 배터리 소모 감소

## 디바운싱의 동작 원리

### 기본 개념

1. **이벤트 발생**: 사용자가 이벤트를 발생시킴
2. **타이머 시작**: 일정 시간(예: 300ms) 타이머 시작
3. **새 이벤트 발생**: 타이머가 끝나기 전에 새 이벤트 발생
4. **타이머 리셋**: 기존 타이머 취소하고 새 타이머 시작
5. **최종 실행**: 마지막 이벤트 후 지정된 시간이 지나면 함수 실행

### 시각적 설명

```
사용자 입력: "안" → "안녕" → "안녕하" → "안녕하세" → "안녕하세요"
시간:       0ms    100ms   200ms    300ms     400ms

타이머:     [300ms] [300ms] [300ms] [300ms] [300ms]
실행:                                              ↑
                                                 여기서만 실행!
```

## 기본 디바운스 함수 구현

### 1. 가장 기본적인 디바운스 함수

```javascript
function debounce(func, wait) {
    let timeout; // 타이머를 저장할 변수
    
    return function executedFunction(...args) {
        // 이전 타이머가 있다면 취소
        clearTimeout(timeout);
        
        // 새로운 타이머 설정
        timeout = setTimeout(() => {
            func(...args); // 지정된 시간 후 함수 실행
        }, wait);
    };
}
```

### 2. 코드 설명

```javascript
function debounce(func, wait) {
    let timeout; // 클로저를 통해 타이머 ID를 저장
    
    return function executedFunction(...args) {
        // clearTimeout(timeout): 이전에 설정된 타이머를 취소
        // 이렇게 하면 연속된 이벤트에서 마지막 이벤트만 실행됨
        clearTimeout(timeout);
        
        // setTimeout(): 지정된 시간(wait) 후에 함수를 실행
        timeout = setTimeout(() => {
            func(...args); // 원래 함수를 실행
        }, wait);
    };
}
```

### 3. 즉시 실행 옵션이 있는 디바운스 함수

```javascript
function debounce(func, wait, immediate = false) {
    let timeout;
    
    return function executedFunction(...args) {
        // immediate가 true이고 타이머가 없으면 즉시 실행
        const callNow = immediate && !timeout;
        
        const later = () => {
            timeout = null;
            // immediate가 false일 때만 나중에 실행
            if (!immediate) func(...args);
        };
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        
        // 즉시 실행 조건이 만족되면 실행
        if (callNow) func(...args);
    };
}
```

### 4. 즉시 실행 옵션 사용 예시

```javascript
// 즉시 실행하지 않는 경우 (기본값)
const debouncedSearch = debounce(searchAPI, 300);
// 사용자가 타이핑을 멈춘 후 300ms 후에 실행

// 즉시 실행하는 경우
const debouncedSearchImmediate = debounce(searchAPI, 300, true);
// 첫 번째 입력 시 즉시 실행, 이후 입력은 300ms 후 실행
```

## 실제 사용 예시

### 1. 검색 기능 구현

```html
<!-- HTML -->
<input type="text" id="searchInput" placeholder="검색어를 입력하세요">
<div id="searchResults"></div>
```

```javascript
// JavaScript
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

// 실제 검색 API 호출 함수
function searchAPI(query) {
    console.log(`"${query}" 검색 중...`);
    
    // 실제로는 여기서 API 호출
    // fetch(`/api/search?q=${query}`)
    //     .then(response => response.json())
    //     .then(data => {
    //         displayResults(data);
    //     });
    
    // 예시용 결과 표시
    searchResults.innerHTML = `<p>"${query}"에 대한 검색 결과를 찾는 중...</p>`;
}

// 디바운스 적용
const debouncedSearch = debounce(searchAPI, 300);

// 이벤트 리스너 등록
searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    
    if (query.length === 0) {
        searchResults.innerHTML = '';
        return;
    }
    
    debouncedSearch(query);
});

// 결과 표시 함수
function displayResults(data) {
    searchResults.innerHTML = data.map(item => 
        `<div>${item.title}</div>`
    ).join('');
}
```

### 2. 윈도우 리사이즈 처리

```javascript
// 윈도우 크기 변경 시 실행될 함수
function handleResize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    console.log(`윈도우 크기: ${width} x ${height}`);
    
    // 레이아웃 재계산
    recalculateLayout();
    
    // 반응형 디자인 적용
    if (width < 768) {
        applyMobileLayout();
    } else {
        applyDesktopLayout();
    }
}

// 디바운스 적용 (250ms 대기)
const debouncedResize = debounce(handleResize, 250);

// 리사이즈 이벤트 리스너
window.addEventListener('resize', debouncedResize);

// 레이아웃 관련 함수들
function recalculateLayout() {
    // 레이아웃 재계산 로직
    console.log('레이아웃 재계산 중...');
}

function applyMobileLayout() {
    console.log('모바일 레이아웃 적용');
}

function applyDesktopLayout() {
    console.log('데스크톱 레이아웃 적용');
}
```

### 3. 스크롤 이벤트 처리

```javascript
// 스크롤 위치에 따른 함수 실행
function handleScroll() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    
    console.log(`스크롤 위치: ${scrollTop}px`);
    
    // 무한 스크롤 구현
    if (scrollTop + windowHeight >= documentHeight - 100) {
        loadMoreContent();
    }
    
    // 스크롤 기반 애니메이션
    updateScrollAnimations(scrollTop);
}

// 디바운스 적용 (100ms 대기)
const debouncedScroll = debounce(handleScroll, 100);

// 스크롤 이벤트 리스너
window.addEventListener('scroll', debouncedScroll);

// 추가 콘텐츠 로드
function loadMoreContent() {
    console.log('추가 콘텐츠 로드 중...');
    // 실제로는 여기서 API 호출하여 추가 데이터 로드
}

// 스크롤 애니메이션 업데이트
function updateScrollAnimations(scrollTop) {
    // 스크롤 위치에 따른 애니메이션 적용
    const elements = document.querySelectorAll('.animate-on-scroll');
    
    elements.forEach(element => {
        const elementTop = element.offsetTop;
        if (scrollTop > elementTop - window.innerHeight) {
            element.classList.add('animated');
        }
    });
}
```

### 4. 폼 유효성 검사

```html
<!-- HTML -->
<form id="registrationForm">
    <div>
        <label for="email">이메일:</label>
        <input type="email" id="email" name="email" required>
        <span id="emailMessage"></span>
    </div>
    
    <div>
        <label for="password">비밀번호:</label>
        <input type="password" id="password" name="password" required>
        <span id="passwordMessage"></span>
    </div>
    
    <button type="submit">가입하기</button>
</form>
```

```javascript
// 이메일 유효성 검사
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// 비밀번호 유효성 검사
function validatePassword(password) {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    return password.length >= minLength && 
           hasUpperCase && 
           hasLowerCase && 
           hasNumbers && 
           hasSpecialChar;
}

// 유효성 검사 결과 표시
function showValidationMessage(elementId, isValid, message) {
    const messageElement = document.getElementById(elementId);
    messageElement.textContent = message;
    messageElement.style.color = isValid ? '#28a745' : '#dc3545';
    messageElement.style.fontSize = '14px';
}

// 디바운스 적용된 유효성 검사
const debouncedEmailValidation = debounce((email) => {
    const isValid = validateEmail(email);
    const message = isValid ? '유효한 이메일 형식입니다.' : '올바른 이메일 형식을 입력해주세요.';
    showValidationMessage('emailMessage', isValid, message);
}, 300);

const debouncedPasswordValidation = debounce((password) => {
    const isValid = validatePassword(password);
    const message = isValid ? '안전한 비밀번호입니다.' : '비밀번호는 8자 이상, 대소문자, 숫자, 특수문자를 포함해야 합니다.';
    showValidationMessage('passwordMessage', isValid, message);
}, 300);

// 이벤트 리스너 등록
document.getElementById('email').addEventListener('input', (e) => {
    debouncedEmailValidation(e.target.value);
});

document.getElementById('password').addEventListener('input', (e) => {
    debouncedPasswordValidation(e.target.value);
});

// 폼 제출 처리
document.getElementById('registrationForm').addEventListener('submit', (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (validateEmail(email) && validatePassword(password)) {
        console.log('폼 제출 성공!');
        // 실제 제출 로직
    } else {
        console.log('유효성 검사 실패');
    }
});
```

## 고급 디바운싱 패턴

### 1. 취소 가능한 디바운스

```javascript
function cancellableDebounce(func, wait) {
    let timeout;
    
    function debounced(...args) {
        const later = () => {
            timeout = null;
            func(...args);
        };
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    }
    
    // 취소 메서드 추가
    debounced.cancel = function() {
        clearTimeout(timeout);
        timeout = null;
    };
    
    // 즉시 실행 메서드 추가
    debounced.flush = function() {
        if (timeout) {
            clearTimeout(timeout);
            timeout = null;
            func();
        }
    };
    
    return debounced;
}

// 사용 예시
const debouncedFn = cancellableDebounce(() => {
    console.log('디바운스 함수 실행됨');
}, 1000);

debouncedFn(); // 타이머 시작
debouncedFn(); // 타이머 리셋
debouncedFn.cancel(); // 실행 취소

// 또는 즉시 실행
debouncedFn.flush(); // 즉시 실행
```

### 2. 최대 대기 시간이 있는 디바운스

```javascript
function debounceWithMaxWait(func, wait, maxWait) {
    let timeout;
    let lastCall = 0;
    
    return function executedFunction(...args) {
        const now = Date.now();
        
        const later = () => {
            timeout = null;
            lastCall = now;
            func(...args);
        };
        
        clearTimeout(timeout);
        
        // 최대 대기 시간을 초과했으면 즉시 실행
        if (now - lastCall >= maxWait) {
            later();
        } else {
            // 그렇지 않으면 일반적인 디바운스 동작
            timeout = setTimeout(later, wait);
        }
    };
}

// 사용 예시
const debouncedWithMaxWait = debounceWithMaxWait(() => {
    console.log('실행됨');
}, 1000, 5000); // 최소 1초, 최대 5초 대기

// 연속으로 호출해도 최대 5초 후에는 반드시 실행됨
```

### 3. 디바운스 상태 추적

```javascript
function debounceWithState(func, wait) {
    let timeout;
    let isPending = false;
    let callCount = 0;
    
    function debounced(...args) {
        callCount++;
        const currentCall = callCount;
        
        console.log(`호출 #${currentCall} 발생`);
        
        const later = () => {
            console.log(`호출 #${currentCall} 실행`);
            isPending = false;
            func(...args);
        };
        
        clearTimeout(timeout);
        isPending = true;
        timeout = setTimeout(later, wait);
    }
    
    // 상태 확인 메서드들
    debounced.isPending = () => isPending;
    debounced.getCallCount = () => callCount;
    
    return debounced;
}

// 사용 예시
const debouncedWithState = debounceWithState(() => {
    console.log('실행 완료');
}, 1000);

debouncedWithState();
console.log('대기 중:', debouncedWithState.isPending()); // true

setTimeout(() => {
    console.log('대기 중:', debouncedWithState.isPending()); // false
    console.log('총 호출 횟수:', debouncedWithState.getCallCount());
}, 2000);
```

## 성능 최적화 팁

### 1. 적절한 대기 시간 선택

```javascript
// 상황별 권장 대기 시간
const DEBOUNCE_TIMES = {
    SEARCH: 300,        // 검색 자동완성
    RESIZE: 250,        // 윈도우 리사이즈
    SCROLL: 100,        // 스크롤 이벤트
    KEYBOARD: 200,      // 키보드 입력
    MOUSE_MOVE: 16,     // 마우스 이동 (60fps)
    TOUCH: 150          // 터치 이벤트
};

// 사용 예시
const debouncedSearch = debounce(searchAPI, DEBOUNCE_TIMES.SEARCH);
const debouncedResize = debounce(handleResize, DEBOUNCE_TIMES.RESIZE);
```

### 2. 메모리 누수 방지

```javascript
class DebounceManager {
    constructor() {
        this.debouncedFunctions = new Map();
    }
    
    // 디바운스 함수 생성 및 관리
    createDebounce(key, func, wait) {
        // 이미 존재하는 함수가 있으면 반환
        if (this.debouncedFunctions.has(key)) {
            return this.debouncedFunctions.get(key);
        }
        
        // 새로운 디바운스 함수 생성
        const debouncedFn = debounce(func, wait);
        this.debouncedFunctions.set(key, debouncedFn);
        
        return debouncedFn;
    }
    
    // 특정 디바운스 함수 취소
    cancel(key) {
        const debouncedFn = this.debouncedFunctions.get(key);
        if (debouncedFn && debouncedFn.cancel) {
            debouncedFn.cancel();
        }
    }
    
    // 모든 디바운스 함수 취소
    cancelAll() {
        this.debouncedFunctions.forEach((debouncedFn) => {
            if (debouncedFn.cancel) {
                debouncedFn.cancel();
            }
        });
        this.debouncedFunctions.clear();
    }
}

// 사용 예시
const debounceManager = new DebounceManager();

// 컴포넌트에서 사용
const searchDebounced = debounceManager.createDebounce('search', searchAPI, 300);
const resizeDebounced = debounceManager.createDebounce('resize', handleResize, 250);

// 컴포넌트 언마운트 시
function cleanup() {
    debounceManager.cancelAll();
}
```

### 3. 디버깅을 위한 로깅

```javascript
function debounceWithLogging(func, wait, name = 'anonymous') {
    let timeout;
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
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 사용 예시
const loggedSearch = debounceWithLogging(searchAPI, 300, '검색');
```

### 4. 성능 측정

```javascript
function debounceWithPerformance(func, wait) {
    let timeout;
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
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
```

## 결론

디바운싱은 웹 애플리케이션의 성능을 크게 향상시킬 수 있는 강력한 기법입니다. 적절한 상황에서 디바운싱을 적용하면 불필요한 연산을 줄이고 사용자 경험을 개선할 수 있습니다.

### 핵심 포인트

1. **적절한 대기 시간 설정**: 상황에 맞는 타이밍 선택
2. **메모리 누수 방지**: 컴포넌트 정리 시 디바운스 함수 취소
3. **디버깅 용이성**: 로깅과 성능 측정 도구 활용
4. **재사용성**: 공통 디바운스 함수 관리

### 자주 사용되는 상황

- **검색 자동완성**: 사용자 입력 완료 후 API 호출
- **무한 스크롤**: 스크롤 이벤트 최적화
- **폼 유효성 검사**: 실시간 입력 검증
- **윈도우 리사이즈**: 레이아웃 재계산 최적화
- **API 호출 최적화**: 중복 요청 방지

이러한 요소들을 고려하여 구현하면 더 효율적이고 유지보수가 용이한 코드를 작성할 수 있습니다. 