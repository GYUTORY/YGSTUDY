---
title: JavaScript 디바운싱(Debouncing)
tags: [language, javascript, 03성능최적화, debouncing, performance-optimization]
updated: 2025-08-10
---

# JavaScript 디바운싱(Debouncing)

## 배경

디바운싱(Debouncing)은 **연속적으로 발생하는 이벤트를 그룹화하여 마지막 이벤트만 처리하는 프로그래밍 기법**입니다.

### 디바운싱의 필요성
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

- **API 호출 횟수 감소**: 불필요한 네트워크 요청 방지
- **데이터베이스 부하 감소**: 중복 쿼리 실행 방지
- **비용 절약**: 클라우드 서비스 사용량 감소

### 3. 사용자 경험 개선

- **빠른 응답**: 불필요한 연산 제거로 UI 반응성 향상
- **일관된 결과**: 마지막 입력값에 대한 정확한 결과 제공
- **배터리 절약**: 모바일 기기에서 배터리 소모 감소

### 4. 디바운싱의 동작 원리

#### 기본 개념
1. **이벤트 발생**: 사용자가 이벤트를 발생시킴
2. **타이머 시작**: 일정 시간(예: 300ms) 타이머 시작
3. **새 이벤트 발생**: 타이머가 끝나기 전에 새 이벤트 발생
4. **타이머 리셋**: 기존 타이머 취소하고 새 타이머 시작
5. **최종 실행**: 마지막 이벤트 후 지정된 시간이 지나면 함수 실행

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
디바운싱은 웹 애플리케이션의 성능을 크게 향상시킬 수 있는 강력한 기법입니다.
적절한 지연 시간 설정이 성능 최적화의 핵심입니다.
디바이스 성능에 따라 다른 지연 시간을 적용하는 것이 좋습니다.
메모리 누수를 방지하기 위해 컴포넌트 정리 시 디바운스 함수도 함께 정리해야 합니다.
디바운싱은 사용자 경험을 개선하면서도 서버 부하를 줄이는 효과적인 방법입니다.






