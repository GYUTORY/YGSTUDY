---
title: JavaScript 쓰로틀링(Throttling)
tags: [language, javascript, 03성능최적화, throttling, performance-optimization]
updated: 2025-08-10
---

# JavaScript 쓰로틀링(Throttling)

## 배경

쓰로틀링은 **특정 시간 동안 함수의 실행 횟수를 제한하는 기술**입니다. 쉽게 말해서, "1초에 한 번만 실행해!"라고 제한을 두는 것입니다.

### 쓰로틀링의 필요성
웹 페이지에서 스크롤이나 리사이즈 같은 이벤트는 매우 빈번하게 발생합니다. 이런 이벤트가 발생할 때마다 함수를 실행하면:
- 브라우저가 느려짐
- 배터리 소모 증가
- 서버에 불필요한 요청 증가

쓰로틀링을 사용하면 이런 문제를 해결할 수 있습니다.

### 쓰로틀링 vs 디바운싱
- **쓰로틀링**: 일정 시간 간격으로 함수 실행을 제한
- **디바운싱**: 연속된 이벤트를 그룹화하여 마지막 이벤트만 처리

## 핵심

### 1. 기본 쓰로틀링 구현

#### 기본 쓰로틀링 함수
```javascript
// 기본 쓰로틀링 함수
function throttle(func, delay) {
    let lastCall = 0;
    
    return function(...args) {
        const now = Date.now();
        
        if (now - lastCall >= delay) {
            lastCall = now;
            return func.apply(this, args);
        }
    };
}

// 사용 예시
const throttledScroll = throttle(() => {
    console.log('스크롤 이벤트 처리');
}, 1000);

window.addEventListener('scroll', throttledScroll);
```

#### 고급 쓰로틀링 함수 (선행/후행 옵션)
```javascript
// 고급 쓰로틀링 함수
function advancedThrottle(func, delay, options = {}) {
    let lastCall = 0;
    let timeoutId = null;
    const { leading = true, trailing = true } = options;
    
    return function(...args) {
        const now = Date.now();
        const timeSinceLastCall = now - lastCall;
        
        // 선행 실행 (leading)
        if (leading && timeSinceLastCall >= delay) {
            lastCall = now;
            return func.apply(this, args);
        }
        
        // 후행 실행 (trailing)
        if (trailing && !timeoutId) {
            timeoutId = setTimeout(() => {
                lastCall = Date.now();
                timeoutId = null;
                func.apply(this, args);
            }, delay - timeSinceLastCall);
        }
    };
}

// 사용 예시
const throttledHandler = advancedThrottle(() => {
    console.log('고급 쓰로틀링 처리');
}, 1000, { leading: true, trailing: true });
```

### 2. 클래스 기반 쓰로틀링

#### 쓰로틀링 관리자 클래스
```javascript
// 쓰로틀링 관리자 클래스
class ThrottleManager {
    constructor() {
        this.throttledFunctions = new Map();
    }
    
    // 함수를 쓰로틀링으로 래핑
    throttle(key, func, delay, options = {}) {
        if (this.throttledFunctions.has(key)) {
            return this.throttledFunctions.get(key);
        }
        
        const throttledFunc = this.createThrottledFunction(func, delay, options);
        this.throttledFunctions.set(key, throttledFunc);
        
        return throttledFunc;
    }
    
    // 쓰로틀링 함수 생성
    createThrottledFunction(func, delay, options = {}) {
        let lastCall = 0;
        let timeoutId = null;
        const { leading = true, trailing = true } = options;
        
        const throttledFunc = function(...args) {
            const now = Date.now();
            const timeSinceLastCall = now - lastCall;
            
            // 선행 실행
            if (leading && timeSinceLastCall >= delay) {
                lastCall = now;
                return func.apply(this, args);
            }
            
            // 후행 실행
            if (trailing && !timeoutId) {
                timeoutId = setTimeout(() => {
                    lastCall = Date.now();
                    timeoutId = null;
                    func.apply(this, args);
                }, delay - timeSinceLastCall);
            }
        };
        
        // 취소 메서드 추가
        throttledFunc.cancel = () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
        };
        
        return throttledFunc;
    }
    
    // 특정 함수 취소
    cancel(key) {
        const throttledFunc = this.throttledFunctions.get(key);
        if (throttledFunc && throttledFunc.cancel) {
            throttledFunc.cancel();
        }
    }
    
    // 모든 함수 취소
    cancelAll() {
        for (const [key, throttledFunc] of this.throttledFunctions) {
            if (throttledFunc.cancel) {
                throttledFunc.cancel();
            }
        }
    }
    
    // 관리 중인 함수 목록
    getThrottledFunctions() {
        return Array.from(this.throttledFunctions.keys());
    }
}

// 사용 예시
const throttleManager = new ThrottleManager();

const scrollHandler = throttleManager.throttle('scroll', () => {
    console.log('스크롤 처리');
}, 1000);

const resizeHandler = throttleManager.throttle('resize', () => {
    console.log('리사이즈 처리');
}, 500);

window.addEventListener('scroll', scrollHandler);
window.addEventListener('resize', resizeHandler);
```

## 예시

### 1. 실제 사용 사례

#### 스크롤 이벤트 최적화
```javascript
// 스크롤 기반 애니메이션 최적화
class ScrollAnimator {
    constructor() {
        this.elements = document.querySelectorAll('.animate-on-scroll');
        this.throttledCheck = throttle(this.checkVisibility.bind(this), 100);
        this.init();
    }
    
    init() {
        window.addEventListener('scroll', this.throttledCheck);
        this.checkVisibility(); // 초기 체크
    }
    
    checkVisibility() {
        const windowHeight = window.innerHeight;
        const scrollTop = window.pageYOffset;
        
        this.elements.forEach(element => {
            const elementTop = element.offsetTop;
            const elementHeight = element.offsetHeight;
            
            // 요소가 화면에 보이는지 확인
            if (scrollTop + windowHeight > elementTop && 
                scrollTop < elementTop + elementHeight) {
                this.animateElement(element);
            }
        });
    }
    
    animateElement(element) {
        if (!element.classList.contains('animated')) {
            element.classList.add('animated');
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }
    }
    
    destroy() {
        window.removeEventListener('scroll', this.throttledCheck);
    }
}

// 사용 예시
const scrollAnimator = new ScrollAnimator();
```

#### 검색 자동완성 최적화
```javascript
// 검색 자동완성 컴포넌트
class SearchAutocomplete {
    constructor(inputElement, suggestionsContainer) {
        this.input = inputElement;
        this.container = suggestionsContainer;
        this.throttledSearch = throttle(this.performSearch.bind(this), 300);
        this.init();
    }
    
    init() {
        this.input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query.length > 0) {
                this.throttledSearch(query);
            } else {
                this.clearSuggestions();
            }
        });
    }
    
    async performSearch(query) {
        try {
            // 로딩 상태 표시
            this.showLoading();
            
            // API 호출 (실제 구현에서는 실제 API 사용)
            const results = await this.searchAPI(query);
            
            // 결과 표시
            this.displaySuggestions(results);
        } catch (error) {
            console.error('검색 오류:', error);
            this.showError();
        }
    }
    
    async searchAPI(query) {
        // 실제 API 호출 시뮬레이션
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

### 2. 게임 개발에서의 쓰로틀링

#### 게임 루프 최적화
```javascript
// 게임 루프 쓰로틀링
class GameLoop {
    constructor(fps = 60) {
        this.fps = fps;
        this.frameTime = 1000 / fps;
        this.lastFrameTime = 0;
        this.isRunning = false;
        this.updateCallback = null;
        this.renderCallback = null;
    }
    
    start(updateCallback, renderCallback) {
        this.updateCallback = updateCallback;
        this.renderCallback = renderCallback;
        this.isRunning = true;
        this.gameLoop();
    }
    
    stop() {
        this.isRunning = false;
    }
    
    gameLoop(currentTime = 0) {
        if (!this.isRunning) return;
        
        const deltaTime = currentTime - this.lastFrameTime;
        
        if (deltaTime >= this.frameTime) {
            // 업데이트 로직 실행
            if (this.updateCallback) {
                this.updateCallback(deltaTime);
            }
            
            // 렌더링 로직 실행
            if (this.renderCallback) {
                this.renderCallback();
            }
            
            this.lastFrameTime = currentTime;
        }
        
        requestAnimationFrame((time) => this.gameLoop(time));
    }
}

// 게임 예시
class SimpleGame {
    constructor() {
        this.player = { x: 0, y: 0, speed: 5 };
        this.gameLoop = new GameLoop(60);
        this.init();
    }
    
    init() {
        this.gameLoop.start(
            this.update.bind(this),
            this.render.bind(this)
        );
        
        // 키보드 입력 처리 (쓰로틀링 적용)
        this.throttledKeyHandler = throttle(this.handleKeyPress.bind(this), 16);
        document.addEventListener('keydown', this.throttledKeyHandler);
    }
    
    update(deltaTime) {
        // 게임 로직 업데이트
        this.player.x += this.player.speed * (deltaTime / 1000);
    }
    
    render() {
        // 화면 렌더링
        console.log(`플레이어 위치: (${this.player.x.toFixed(2)}, ${this.player.y.toFixed(2)})`);
    }
    
    handleKeyPress(event) {
        switch (event.key) {
            case 'ArrowUp':
                this.player.y -= 10;
                break;
            case 'ArrowDown':
                this.player.y += 10;
                break;
            case 'ArrowLeft':
                this.player.x -= 10;
                break;
            case 'ArrowRight':
                this.player.x += 10;
                break;
        }
    }
    
    destroy() {
        this.gameLoop.stop();
        document.removeEventListener('keydown', this.throttledKeyHandler);
    }
}

// 게임 시작
const game = new SimpleGame();
```

## 운영 팁

### 성능 최적화

#### 디바이스별 최적화
```javascript
// 디바이스별 최적화된 시간 간격
class DeviceOptimizedThrottle {
    static getThrottleTime() {
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const isSlowDevice = navigator.hardwareConcurrency <= 4;
        const isLowMemory = navigator.deviceMemory < 4;
        
        if (isMobile && isSlowDevice) return 1000; // 모바일 + 느린 디바이스: 1초
        if (isMobile) return 500; // 모바일: 0.5초
        if (isSlowDevice || isLowMemory) return 250; // 느린 디바이스: 0.25초
        return 100; // 일반적인 디바이스: 0.1초
    }
    
    static createOptimizedThrottle(func) {
        const delay = this.getThrottleTime();
        return throttle(func, delay);
    }
}

// 사용 예시
const optimizedHandler = DeviceOptimizedThrottle.createOptimizedThrottle(() => {
    console.log('디바이스에 최적화된 이벤트 처리');
});

window.addEventListener('scroll', optimizedHandler);
```

#### 메모리 누수 방지
```javascript
// 메모리 누수 방지를 위한 컴포넌트
class ThrottledComponent {
    constructor() {
        this.handler = throttle(this.handleEvent.bind(this), 1000);
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        window.addEventListener('scroll', this.handler);
        window.addEventListener('resize', this.handler);
        window.addEventListener('mousemove', this.handler);
    }
    
    handleEvent(event) {
        console.log('이벤트 처리 중...', event.type);
        // 실제 처리 로직
    }
    
    // 컴포넌트 정리 시 이벤트 리스너 제거
    cleanup() {
        window.removeEventListener('scroll', this.handler);
        window.removeEventListener('resize', this.handler);
        window.removeEventListener('mousemove', this.handler);
        
        // 쓰로틀링 함수 취소
        if (this.handler.cancel) {
            this.handler.cancel();
        }
    }
}

// 사용 예시
const component = new ThrottledComponent();

// 컴포넌트가 더 이상 필요 없을 때
component.cleanup();
```

### 쓰로틀링과 디바운싱 조합

#### 하이브리드 최적화
```javascript
// 쓰로틀링과 디바운싱을 조합한 최적화
class HybridOptimizer {
    constructor() {
        this.throttleManager = new ThrottleManager();
    }
    
    // UI 업데이트용 쓰로틀링 (빠른 반응)
    createUIThrottle(func, delay = 16) {
        return this.throttleManager.throttle(`ui_${Date.now()}`, func, delay, {
            leading: true,
            trailing: false
        });
    }
    
    // 데이터 저장용 디바운싱 (마지막에 한 번만)
    createDataDebounce(func, delay = 1000) {
        return this.debounce(func, delay);
    }
    
    // 디바운싱 함수 구현
    debounce(func, delay) {
        let timeoutId;
        
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                func.apply(this, args);
            }, delay);
        };
    }
    
    // 복합 이벤트 핸들러 생성
    createHybridHandler(uiUpdateFunc, dataSaveFunc) {
        const throttledUI = this.createUIThrottle(uiUpdateFunc);
        const debouncedSave = this.createDataDebounce(dataSaveFunc);
        
        return function(event) {
            throttledUI(event); // 즉시 반응하는 UI
            debouncedSave(event); // 나중에 저장
        };
    }
}

// 사용 예시
const optimizer = new HybridOptimizer();

const hybridHandler = optimizer.createHybridHandler(
    // UI 업데이트 (빠른 반응)
    (event) => {
        console.log('UI 업데이트:', event.type);
        // 즉시 화면에 반영되는 로직
    },
    // 데이터 저장 (마지막에 한 번만)
    (event) => {
        console.log('데이터 저장:', event.type);
        // 서버에 데이터 저장하는 로직
    }
);

window.addEventListener('scroll', hybridHandler);
```

## 참고

### 쓰로틀링 사용 권장 사례

#### 적절한 사용 시나리오
```javascript
// 쓰로틀링이 적합한 경우들
const throttleUseCases = {
    scroll: {
        description: '스크롤 이벤트 처리',
        delay: 100,
        reason: '스크롤은 매우 빈번하게 발생하므로 제한 필요'
    },
    resize: {
        description: '윈도우 리사이즈 처리',
        delay: 250,
        reason: '리사이즈 중에는 불필요한 계산 방지'
    },
    mousemove: {
        description: '마우스 이동 처리',
        delay: 16,
        reason: '60fps로 제한하여 부드러운 애니메이션'
    },
    gameInput: {
        description: '게임 입력 처리',
        delay: 16,
        reason: '게임 루프와 동기화'
    },
    apiCall: {
        description: 'API 호출 제한',
        delay: 1000,
        reason: '서버 부하 방지'
    }
};

// 사용 예시
Object.entries(throttleUseCases).forEach(([event, config]) => {
    console.log(`${event}: ${config.description} - ${config.delay}ms`);
});
```

### 성능 측정

#### 쓰로틀링 성능 측정
```javascript
// 쓰로틀링 성능 측정 도구
class ThrottlePerformanceTester {
    static measureThrottlePerformance(throttledFunc, eventCount = 1000, interval = 10) {
        let callCount = 0;
        let executionCount = 0;
        const startTime = performance.now();
        
        // 원본 함수 래핑
        const originalFunc = throttledFunc;
        const wrappedFunc = function(...args) {
            callCount++;
            const result = originalFunc.apply(this, args);
            if (result !== undefined) {
                executionCount++;
            }
            return result;
        };
        
        // 이벤트 시뮬레이션
        const simulateEvents = () => {
            for (let i = 0; i < eventCount; i++) {
                setTimeout(() => {
                    wrappedFunc({ type: 'test', timestamp: Date.now() });
                }, i * interval);
            }
        };
        
        simulateEvents();
        
        // 결과 측정
        setTimeout(() => {
            const endTime = performance.now();
            const totalTime = endTime - startTime;
            
            console.log('쓰로틀링 성능 측정 결과:');
            console.log(`총 호출 횟수: ${callCount}`);
            console.log(`실제 실행 횟수: ${executionCount}`);
            console.log(`제한률: ${((callCount - executionCount) / callCount * 100).toFixed(2)}%`);
            console.log(`총 소요 시간: ${totalTime.toFixed(2)}ms`);
            console.log(`평균 실행 간격: ${totalTime / executionCount}ms`);
        }, eventCount * interval + 1000);
    }
}

// 성능 테스트 실행
const testThrottledFunc = throttle(() => {
    console.log('실행됨:', Date.now());
}, 100);

ThrottlePerformanceTester.measureThrottlePerformance(testThrottledFunc, 100, 10);
```

### 결론
쓰로틀링은 빈번한 이벤트를 효율적으로 처리하는 강력한 기법입니다.
적절한 시간 간격 설정이 성능 최적화의 핵심입니다.
디바이스 성능에 따라 다른 쓰로틀링 간격을 적용하는 것이 좋습니다.
메모리 누수를 방지하기 위해 컴포넌트 정리 시 쓰로틀링 함수도 함께 정리해야 합니다.
쓰로틀링과 디바운싱을 적절히 조합하여 최적의 사용자 경험을 제공할 수 있습니다.
