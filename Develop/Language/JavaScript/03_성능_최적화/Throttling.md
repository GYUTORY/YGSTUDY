# JavaScript 쓰로틀링(Throttling)

## 📋 목차
- [쓰로틀링이란?](#쓰로틀링이란)
- [쓰로틀링 vs 디바운싱](#쓰로틀링-vs-디바운싱)
- [쓰로틀링 구현 방법](#쓰로틀링-구현-방법)
- [실제 사용 사례](#실제-사용-사례)
- [성능 최적화 팁](#성능-최적화-팁)

---

## 🎯 쓰로틀링이란?

### 개념 설명
쓰로틀링은 **특정 시간 동안 함수의 실행 횟수를 제한하는 기술**입니다. 쉽게 말해서, "1초에 한 번만 실행해!"라고 제한을 두는 것입니다.

### 왜 필요한가?
웹 페이지에서 스크롤이나 리사이즈 같은 이벤트는 매우 빈번하게 발생합니다. 이런 이벤트가 발생할 때마다 함수를 실행하면:
- 브라우저가 느려짐
- 배터리 소모 증가
- 서버에 불필요한 요청 증가

쓰로틀링을 사용하면 이런 문제를 해결할 수 있습니다.

### 기본 예시
```javascript
// 쓰로틀링 없이 - 매번 실행됨
window.addEventListener('scroll', () => {
    console.log('스크롤!'); // 스크롤할 때마다 계속 실행
});

// 쓰로틀링 적용 - 1초에 한 번만 실행
const throttledScroll = throttle(() => {
    console.log('스크롤!'); // 1초에 한 번만 실행
}, 1000);

window.addEventListener('scroll', throttledScroll);
```

---

## 🔄 쓰로틀링 vs 디바운싱

### 차이점 이해하기

| 구분 | 쓰로틀링 | 디바운싱 |
|------|----------|----------|
| **동작 방식** | 일정 시간마다 한 번씩 실행 | 마지막 이벤트 후 일정 시간 지나면 실행 |
| **실행 시점** | 정해진 간격으로 실행 | 이벤트 중단 후 실행 |
| **적합한 상황** | 실시간 업데이트가 필요한 경우 | 최종 결과만 필요한 경우 |

### 시각적 비교
```javascript
// 이벤트 발생: [1초] [1초] [1초] [1초] [1초]
// 쓰로틀링:     [실행] [대기] [실행] [대기] [실행]
// 디바운싱:     [대기] [대기] [대기] [대기] [실행]
```

### 실제 비교 예시
```javascript
// 쓰로틀링 - 1초마다 실행
const throttledFunction = throttle(() => {
    console.log('쓰로틀링 실행!');
}, 1000);

// 디바운싱 - 마지막 이벤트 후 1초 뒤 실행
const debouncedFunction = debounce(() => {
    console.log('디바운싱 실행!');
}, 1000);

// 연속으로 호출해보기
for (let i = 0; i < 5; i++) {
    setTimeout(() => {
        throttledFunction(); // 1초마다 한 번씩 실행
        debouncedFunction(); // 마지막에 한 번만 실행
    }, i * 200);
}
```

---

## 🛠️ 쓰로틀링 구현 방법

### 1. 기본 구현 (플래그 방식)
```javascript
function throttle(func, limit) {
    let inThrottle = false; // 쓰로틀링 상태를 추적하는 플래그
    
    return function(...args) {
        if (!inThrottle) { // 쓰로틀링 중이 아니라면
            func.apply(this, args); // 함수 실행
            inThrottle = true; // 쓰로틀링 상태로 변경
            
            setTimeout(() => {
                inThrottle = false; // 제한 시간 후 쓰로틀링 해제
            }, limit);
        }
    }
}
```

**동작 원리:**
1. `inThrottle` 플래그로 현재 쓰로틀링 상태를 추적
2. 함수가 호출되면 플래그를 확인
3. 쓰로틀링 중이 아니면 함수 실행 후 플래그를 true로 설정
4. 제한 시간 후 플래그를 false로 변경

### 2. 타임스탬프 기반 구현
```javascript
function throttleWithTimestamp(func, limit) {
    let lastCall = 0; // 마지막 호출 시간을 저장
    
    return function(...args) {
        const now = Date.now(); // 현재 시간
        
        if (now - lastCall >= limit) { // 제한 시간이 지났다면
            func.apply(this, args); // 함수 실행
            lastCall = now; // 마지막 호출 시간 업데이트
        }
    }
}
```

**장점:**
- 더 정확한 시간 제어
- 메모리 사용량이 적음
- setTimeout 없이 동작

### 3. 고급 구현 (마지막 호출 보장)
```javascript
function throttleWithTrailing(func, limit) {
    let lastCall = 0;
    let timeoutId = null;
    
    return function(...args) {
        const now = Date.now();
        
        if (now - lastCall >= limit) {
            // 제한 시간이 지났으면 즉시 실행
            if (timeoutId) {
                clearTimeout(timeoutId);
                timeoutId = null;
            }
            func.apply(this, args);
            lastCall = now;
        } else if (!timeoutId) {
            // 제한 시간이 안 지났으면 나중에 실행
            timeoutId = setTimeout(() => {
                func.apply(this, args);
                lastCall = Date.now();
                timeoutId = null;
            }, limit - (now - lastCall));
        }
    }
}
```

**특징:**
- 마지막 호출이 반드시 실행됨
- 더 부드러운 사용자 경험 제공

---

## 💡 실제 사용 사례

### 1. 스크롤 이벤트 처리
```javascript
// 무한 스크롤 구현
const loadMoreContent = throttle(() => {
    const scrollHeight = document.documentElement.scrollHeight; // 전체 스크롤 높이
    const scrollTop = window.scrollY; // 현재 스크롤 위치
    const clientHeight = document.documentElement.clientHeight; // 화면 높이
    
    // 스크롤이 하단 100px 근처에 도달했는지 확인
    if (scrollTop + clientHeight >= scrollHeight - 100) {
        console.log('추가 콘텐츠 로드!');
        fetchMoreContent(); // API 호출
    }
}, 1000); // 1초에 한 번만 실행

window.addEventListener('scroll', loadMoreContent);
```

### 2. 리사이즈 이벤트 처리
```javascript
// 반응형 레이아웃 조정
const handleResize = throttle(() => {
    const width = window.innerWidth;
    
    if (width < 768) {
        console.log('모바일 레이아웃 적용');
        adjustMobileLayout();
    } else {
        console.log('데스크톱 레이아웃 적용');
        adjustDesktopLayout();
    }
}, 250); // 250ms에 한 번만 실행 (더 빠른 반응)

window.addEventListener('resize', handleResize);
```

### 3. 게임 컨트롤러 입력 처리
```javascript
class GameController {
    constructor() {
        // 16ms = 약 60fps로 제한
        this.movePlayer = throttle(this.movePlayer.bind(this), 16);
    }
    
    movePlayer(direction) {
        // 플레이어 위치 업데이트
        this.player.x += direction.x;
        this.player.y += direction.y;
        
        // 게임 상태 업데이트
        this.updateGameState();
        this.render();
    }
    
    handleInput(event) {
        const direction = this.getDirectionFromInput(event);
        this.movePlayer(direction);
    }
}

// 사용 예시
const game = new GameController();
document.addEventListener('keydown', (e) => game.handleInput(e));
```

### 4. API 요청 제한
```javascript
class APIClient {
    constructor() {
        // API 요청을 1초에 한 번으로 제한
        this.request = throttle(this.makeRequest.bind(this), 1000);
    }
    
    async makeRequest(endpoint, data) {
        try {
            console.log('API 요청 전송:', endpoint);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            return await response.json();
        } catch (error) {
            console.error('API 요청 실패:', error);
        }
    }
    
    // 외부에서 호출하는 메서드
    sendData(endpoint, data) {
        return this.request(endpoint, data);
    }
}

// 사용 예시
const apiClient = new APIClient();

// 연속으로 호출해도 1초에 한 번만 실제 요청이 발생
apiClient.sendData('/api/users', { name: 'John' });
apiClient.sendData('/api/users', { name: 'Jane' });
apiClient.sendData('/api/users', { name: 'Bob' });
```

---

## ⚡ 성능 최적화 팁

### 1. 적절한 시간 간격 선택
```javascript
// 디바이스별 최적화된 시간 간격
const getThrottleTime = () => {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const isSlowDevice = navigator.hardwareConcurrency <= 4;
    
    if (isMobile) return 1000; // 모바일: 1초
    if (isSlowDevice) return 500; // 느린 디바이스: 0.5초
    return 250; // 일반적인 디바이스: 0.25초
};

const optimizedHandler = throttle(() => {
    // 이벤트 처리 로직
    console.log('최적화된 이벤트 처리');
}, getThrottleTime());
```

### 2. 메모리 누수 방지
```javascript
class ThrottledComponent {
    constructor() {
        this.handler = throttle(this.handleEvent.bind(this), 1000);
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        window.addEventListener('scroll', this.handler);
        window.addEventListener('resize', this.handler);
    }
    
    handleEvent() {
        console.log('이벤트 처리 중...');
        // 실제 처리 로직
    }
    
    // 컴포넌트 정리 시 이벤트 리스너 제거
    cleanup() {
        window.removeEventListener('scroll', this.handler);
        window.removeEventListener('resize', this.handler);
    }
}

// 사용 예시
const component = new ThrottledComponent();

// 컴포넌트가 더 이상 필요 없을 때
component.cleanup();
```

### 3. 쓰로틀링과 디바운싱 조합
```javascript
function createOptimizedHandler() {
    // UI 업데이트는 빠르게 (16ms = 60fps)
    const throttledUIUpdate = throttle(() => {
        updateUI();
        console.log('UI 업데이트');
    }, 16);
    
    // 상태 저장은 마지막에 한 번만
    const debouncedSave = debounce(() => {
        saveState();
        console.log('상태 저장');
    }, 1000);
    
    return function(event) {
        throttledUIUpdate(event); // 즉시 반응하는 UI
        debouncedSave(event);     // 나중에 저장
    }
}

// 디바운싱 함수 (참고용)
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    }
}
```

---

## 📚 추가 학습 자료

- [MDN Web Docs - Event Throttling](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener)
- [JavaScript.info - Throttling and Debouncing](https://javascript.info/throttling-debouncing)
- [Lodash Documentation - throttle](https://lodash.com/docs/#throttle)
