---
title: 브라우저 렌더링 파이프라인
tags: [frontend, javascript, performance]
updated: 2026-08-27
---

## 파이프라인 다섯 단계

브라우저가 화면을 그리는 과정은 Parse → Style → Layout → Paint → Composite 순서로 진행된다. 각 단계는 앞 단계의 결과를 입력으로 받는다. 어느 단계에서 변경이 발생했느냐에 따라 뒤에 오는 단계 전부가 다시 실행될 수 있다.

**Parse**: HTML을 DOM 트리로, CSS를 CSSOM 트리로 변환한다. `<script>` 태그가 `defer`나 `async` 없이 `<head>`에 있으면 파싱을 멈추고 스크립트를 실행한다. 이 시점에 DOM이 아직 완성되지 않아서 스크립트가 DOM을 조작하면 예상과 다른 결과가 나온다.

**Style**: DOM과 CSSOM을 합쳐서 각 엘리먼트에 최종 스타일을 계산한다(Computed Style). 셀렉터 매칭이 이 단계에서 일어난다. 브라우저는 셀렉터를 오른쪽에서 왼쪽으로 읽는다. `.container .list .item span`은 먼저 모든 `span`을 찾고, 그중 `.item` 자식인 것을 걸러내는 방식이다. 셀렉터가 길고 조상 조건이 많을수록 매칭 비용이 올라간다.

**Layout**(Reflow라고도 한다): 각 엘리먼트의 위치와 크기를 계산한다. `width`, `height`, `margin`, `padding`, `top`, `left` 같은 기하 속성이 이 단계에 영향을 준다. 한 엘리먼트의 크기가 바뀌면 주변 엘리먼트의 레이아웃도 다시 계산해야 한다. DOM 트리 상위 엘리먼트에 변경이 발생하면 하위 트리 전체가 대상이 된다.

**Paint**: Layout 결과를 바탕으로 실제 픽셀을 레이어 단위로 계산한다. `color`, `background`, `box-shadow`, `border-radius` 같은 시각 속성이 이 단계다. Layout을 건드리지 않는 변경은 Paint부터 실행된다.

**Composite**: 페인트된 레이어들을 합성해서 최종 화면을 만든다. GPU가 이 단계를 담당한다. `transform`과 `opacity`만 바뀌면 Layout과 Paint를 건너뛰고 Composite만 실행된다. 애니메이션에서 이 두 속성이 권장되는 이유다.

```
CSS 속성 변경이 건드리는 파이프라인 단계:

width/height/margin  →  Layout → Paint → Composite
color/background     →           Paint → Composite
transform/opacity    →                   Composite
```

`left: 100px`과 `transform: translateX(100px)`은 결과가 같아 보이지만 브라우저가 처리하는 단계 수가 다르다. 전자는 매 프레임마다 Layout을 다시 계산하고, 후자는 GPU가 레이어만 이동시킨다.

---

## 강제 레이아웃이 발생하는 패턴

JavaScript로 DOM의 기하 속성을 읽으면 브라우저는 현재까지 쌓인 스타일 변경을 즉시 반영하고 Layout을 계산한다. 이걸 강제 동기 레이아웃(Forced Synchronous Layout)이라고 한다.

강제 레이아웃을 발생시키는 속성과 메서드:

- `offsetWidth`, `offsetHeight`, `offsetTop`, `offsetLeft`
- `scrollWidth`, `scrollHeight`, `scrollTop`, `scrollLeft`
- `clientWidth`, `clientHeight`, `clientTop`, `clientLeft`
- `getBoundingClientRect()`
- `getComputedStyle()`

단독으로 읽는 것 자체가 문제는 아니다. **쓰기 후 즉시 읽기**가 문제다.

```javascript
// Layout Thrashing — 매 반복마다 강제 레이아웃 발생
const items = document.querySelectorAll('.item');
items.forEach(item => {
  const width = item.offsetWidth; // 읽기 → 강제 레이아웃
  item.style.width = width * 2 + 'px'; // 쓰기 → 브라우저 내부에 변경 누적
  // 다음 반복에서 offsetWidth를 읽으면 직전 쓰기 때문에 또 레이아웃 실행
});
```

루프가 100번 돌면 Layout이 100번 강제 실행된다. DevTools Performance 탭에서 보면 레이아웃 태스크가 촘촘하게 쌓여 있는 모습으로 나타난다.

읽기를 먼저 모아서 처리하고, 쓰기를 나중에 일괄 처리하면 Layout은 한 번만 실행된다.

```javascript
// 읽기 먼저 수집
const items = Array.from(document.querySelectorAll('.item'));
const widths = items.map(item => item.offsetWidth);

// 쓰기를 나중에 일괄 처리
items.forEach((item, i) => {
  item.style.width = widths[i] * 2 + 'px';
});
```

실무에서 이 패턴이 자주 나오는 곳은 드래그 앤 드롭 구현, 스크롤 이벤트 핸들러, 아코디언 애니메이션이다. 스크롤 핸들러 안에서 `getBoundingClientRect()`를 호출하고 스타일을 바꾸면 프레임마다 강제 레이아웃이 발생한다.

---

## will-change와 transform으로 GPU 레이어 분리

`will-change` 속성은 브라우저에게 이 엘리먼트가 곧 변경될 것임을 미리 알려서 별도 합성 레이어를 만들도록 한다.

```css
.animated-modal {
  will-change: transform;
}
```

`will-change: transform`이 붙은 엘리먼트는 별도 합성 레이어(Compositing Layer)로 분리된다. 이 엘리먼트에 `transform`이나 `opacity` 변경이 일어나면 다른 엘리먼트에 영향을 주지 않고 GPU가 독립적으로 처리한다. 모달이 올라오는 애니메이션 동안 배경 콘텐츠가 repaint되지 않는 이유다.

`transform: translateZ(0)`이나 `transform: translate3d(0,0,0)`도 레이어를 분리하는 효과가 있다. `will-change` 지원 전에 쓰던 방법이다. 지금은 `will-change`가 의도를 더 명확하게 표현한다.

**남용하면 역효과가 난다.** 레이어를 분리하면 그 레이어를 GPU 메모리(VRAM)에 올려야 한다. 이미지가 많은 큰 엘리먼트에 `will-change: transform`을 붙이면 VRAM 사용량이 급증한다. 모바일에서 특히 문제가 된다. 페이지에 레이어가 100개를 넘어가면 합성 자체가 병목이 된다.

DevTools의 Layers 패널에서 현재 페이지의 레이어를 볼 수 있다. 의도하지 않은 레이어가 많이 생겨 있으면 `will-change`나 `transform: translateZ(0)`이 남용된 것이다.

사용 원칙은 단순하다. 실제로 애니메이션이 일어나는 엘리먼트에만, 애니메이션 직전에 붙이고 끝나면 제거한다.

```javascript
button.addEventListener('click', () => {
  modal.style.willChange = 'transform, opacity';
  modal.classList.add('modal--entering');
});

modal.addEventListener('transitionend', () => {
  modal.style.willChange = 'auto';
});
```

페이지 로드 시점부터 모든 인터랙티브 엘리먼트에 `will-change`를 붙여두는 CSS를 쓰는 경우가 있는데, 그러면 초기 레이어 생성 비용이 올라간다. CSS에서 `will-change`를 정적으로 쓸 때는 항상 애니메이션이 실행되는 엘리먼트(회전하는 로더, 항상 떠 있는 플로팅 버튼)로 한정한다.

`transform`으로 이동 애니메이션을 구현할 때 주의할 점이 있다. `transform`은 시각적 위치만 바꾼다. 실제 레이아웃 위치는 원래 자리에 그대로 남는다. `transform`으로 이동한 엘리먼트와 다른 엘리먼트가 겹치면 클릭 이벤트는 원래 위치에서 잡힌다.

---

## requestAnimationFrame을 올바르게 쓰는 방법

`setTimeout(fn, 16)`으로 애니메이션을 만들면 브라우저 렌더링 주기와 동기화되지 않는다. 렌더 직후에 실행되면 다음 렌더까지 거의 32ms를 기다리거나, 렌더 직전에 실행되면 변경이 이번 프레임에 포함되지 못한다. 결과적으로 프레임 드롭이나 불규칙한 애니메이션이 나온다.

`requestAnimationFrame`은 다음 프레임을 그리기 직전에 콜백을 실행한다. 브라우저 렌더링 주기와 정확히 맞물린다.

```javascript
let startTime = null;
const duration = 300; // ms

function animate(timestamp) {
  if (!startTime) startTime = timestamp;
  
  const elapsed = timestamp - startTime;
  const progress = Math.min(elapsed / duration, 1);
  
  element.style.transform = `translateX(${progress * 200}px)`;
  
  if (progress < 1) {
    requestAnimationFrame(animate);
  }
}

requestAnimationFrame(animate);
```

`timestamp` 매개변수를 써야 한다. 프레임당 경과 시간이 일정하지 않기 때문이다. 60fps면 16.6ms, 120fps면 8.3ms, 배터리 절약 모드에서는 30fps로 떨어진다. `timestamp`를 무시하고 매 콜백마다 고정 값을 더하면 화면 주사율에 따라 애니메이션 속도가 달라진다.

rAF 콜백 안에서도 읽기-쓰기를 반복하면 강제 레이아웃이 발생한다. rAF는 타이밍 문제만 해결하고, 읽기-쓰기 순서는 직접 관리해야 한다.

```javascript
// 잘못된 패턴 — rAF 안이어도 강제 레이아웃 발생
function loop() {
  const height = element.offsetHeight; // 읽기
  element.style.height = height + 1 + 'px'; // 쓰기
  requestAnimationFrame(loop);
}
```

탭이 백그라운드로 가면 브라우저가 rAF 콜백 실행을 멈춘다. 애니메이션 루프 안에서 타이머나 게임 상태를 업데이트하고 있었다면 탭 전환 순간 멈춘다. Page Visibility API로 처리한다.

```javascript
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    cancelAnimationFrame(animId);
  } else {
    startTime = null; // 복귀 시 타임스탬프 리셋
    animId = requestAnimationFrame(animate);
  }
});
```

컴포넌트 언마운트 시 `cancelAnimationFrame`을 호출하지 않으면 루프가 계속 실행되면서 메모리 누수가 생긴다.

```typescript
useEffect(() => {
  let animId: number;
  let startTime: number | null = null;

  function loop(timestamp: number) {
    if (!startTime) startTime = timestamp;
    const elapsed = timestamp - startTime;
    
    // 애니메이션 로직
    
    animId = requestAnimationFrame(loop);
  }

  animId = requestAnimationFrame(loop);

  return () => {
    cancelAnimationFrame(animId);
  };
}, []);
```

---

## 스크롤·리사이즈 핸들러의 강제 레이아웃 회피

스크롤 이벤트는 초당 수십 번 발생한다. 핸들러 안에서 DOM을 읽고 스타일을 바꾸면 매 이벤트마다 강제 레이아웃이 발생한다.

rAF로 묶으면 프레임 단위로 한 번만 처리된다.

```javascript
let scheduled = false;

window.addEventListener('scroll', () => {
  if (scheduled) return;
  
  scheduled = true;
  requestAnimationFrame(() => {
    const scrollY = window.scrollY;
    updateStickyHeader(scrollY);
    scheduled = false;
  });
});
```

스크롤 이벤트가 한 프레임 안에 여러 번 발생해도 rAF 콜백은 다음 프레임에 한 번만 실행된다. `window.scrollY`는 rAF 콜백 안에서 읽으면 강제 레이아웃 없이 읽을 수 있다. rAF 직전에 브라우저가 레이아웃을 이미 계산해둔 상태이기 때문이다.

엘리먼트 크기 변화를 감지할 때는 `ResizeObserver`가 낫다. 이 API는 레이아웃 계산 후에 콜백을 호출하므로 강제 레이아웃 없이 현재 크기를 읽을 수 있다.

```javascript
const observer = new ResizeObserver(entries => {
  for (const entry of entries) {
    const { width, height } = entry.contentRect;
    updateLayout(width, height);
  }
});

observer.observe(container);

// 정리
observer.disconnect();
```

`window.addEventListener('resize', ...)`로 창 크기 변화를 감지하다가 `getBoundingClientRect()`를 호출하면 매 resize 이벤트마다 강제 레이아웃이 발생한다. `ResizeObserver`로 대체하면 브라우저가 최적화된 시점에 콜백을 호출하므로 이 문제가 없다.

viewport에 들어온 엘리먼트를 감지할 때도 스크롤 이벤트 + `getBoundingClientRect()` 조합 대신 `IntersectionObserver`를 쓴다. 같은 이유다.

```javascript
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target); // 한 번만 감지하면 해제
    }
  });
}, {
  rootMargin: '0px 0px -100px 0px', // 뷰포트 하단 100px 전부터 감지
  threshold: 0.1
});

document.querySelectorAll('.lazy-section').forEach(el => {
  observer.observe(el);
});
```
