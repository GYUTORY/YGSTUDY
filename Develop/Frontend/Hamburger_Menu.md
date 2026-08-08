---
title: 프론트엔드에서의 햄버거 메뉴
tags: [frontend, javascript]
updated: 2026-08-02
---

# 프론트엔드에서의 햄버거 메뉴

세 줄짜리 아이콘 하나지만, 제대로 만들려면 생각보다 고려할 게 많다. CSS only로 끝내려다가 접근성 문제로 JS를 도입하게 되고, 모바일에서 iOS Safari 때문에 한 번 더 삽질하는 게 일반적인 흐름이다.

## CSS only vs JS 토글

### CSS only

```css
/* checkbox hack */
#nav-toggle {
  display: none;
}

#nav-toggle:checked ~ .nav-menu {
  display: block;
}

label[for="nav-toggle"] {
  cursor: pointer;
}
```

```html
<input type="checkbox" id="nav-toggle" />
<label for="nav-toggle">
  <span class="bar"></span>
  <span class="bar"></span>
  <span class="bar"></span>
</label>
<nav class="nav-menu">...</nav>
```

checkbox hack 방식은 JS 없이 동작하지만, `aria-expanded` 같은 접근성 속성을 동적으로 바꿀 수 없다는 문제가 있다. 스크린 리더 사용자는 메뉴 상태를 알 수 없다. 간단한 인터랙션 데모나 정적 사이트가 아니라면 쓰지 않는다.

### JS 토글

실무에서는 JS 토글이 기본이다. 상태를 직접 관리하므로 접근성 속성 처리가 자유롭다.

```javascript
const btn = document.querySelector('.hamburger-btn');
const menu = document.querySelector('.nav-menu');

btn.addEventListener('click', () => {
  const isOpen = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!isOpen));
  menu.classList.toggle('is-open');
});
```

## 3선 애니메이션 (X 변환)

CSS transform 조합으로 3개의 막대를 X 모양으로 변환한다.

```html
<button class="hamburger-btn" aria-expanded="false" aria-controls="nav-menu" aria-label="메뉴 열기">
  <span class="bar bar--top"></span>
  <span class="bar bar--mid"></span>
  <span class="bar bar--bot"></span>
</button>
```

```css
.hamburger-btn {
  width: 40px;
  height: 40px;
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  padding: 0;
}

.bar {
  display: block;
  width: 24px;
  height: 2px;
  background: currentColor;
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform-origin: center;
}

.hamburger-btn[aria-expanded="true"] .bar--top {
  transform: translateY(8px) rotate(45deg);
}

.hamburger-btn[aria-expanded="true"] .bar--mid {
  opacity: 0;
  transform: scaleX(0);
}

.hamburger-btn[aria-expanded="true"] .bar--bot {
  transform: translateY(-8px) rotate(-45deg);
}
```

`translateY` 값은 `gap` + `bar` 높이 합산으로 계산한다. gap이 6px, bar가 2px이면 이동값은 6 + 2 = 8px. 이 값이 맞지 않으면 X가 비틀어진다.

## 접근성 처리

### aria-expanded / aria-label / aria-controls

```html
<button
  class="hamburger-btn"
  aria-expanded="false"
  aria-controls="nav-menu"
  aria-label="메뉴 열기"
>
  ...
</button>

<nav id="nav-menu" class="nav-menu">...</nav>
```

```javascript
btn.addEventListener('click', () => {
  const isOpen = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!isOpen));
  btn.setAttribute('aria-label', isOpen ? '메뉴 열기' : '메뉴 닫기');
});
```

`aria-controls`는 버튼이 제어하는 요소의 id를 가리킨다. `aria-expanded`는 `"true"` / `"false"` 문자열이어야 한다. 불리언 값을 그대로 넣으면 일부 스크린 리더에서 인식 못하는 경우가 있다.

### focus trap

메뉴가 열린 상태에서 Tab을 계속 누르면 포커스가 메뉴 밖으로 나가버린다. 모달처럼 포커스를 가두는 처리가 필요하다.

```javascript
function trapFocus(element) {
  const focusable = element.querySelectorAll(
    'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  element.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });
}
```

메뉴가 열릴 때 `trapFocus(menu)`를 호출하고, 닫힐 때 이벤트 리스너를 제거해야 한다. 제거를 빠뜨리면 메뉴가 닫혀있는데도 Tab 동작이 의도치 않게 바뀐다.

## 키보드 네비게이션

### ESC로 닫기

```javascript
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && menu.classList.contains('is-open')) {
    closeMenu();
    btn.focus(); // 닫힌 후 포커스를 버튼으로 되돌린다
  }
});
```

ESC로 닫은 후 포커스를 햄버거 버튼으로 돌려보내야 한다. 돌려보내지 않으면 포커스가 body로 올라가서 키보드 사용자가 위치를 잃는다.

### 함수 분리

열기/닫기 로직을 한 곳에 모아두면 버튼 클릭, ESC 키, 오버레이 클릭 등 여러 트리거에서 재사용하기 편하다.

```javascript
function openMenu() {
  menu.classList.add('is-open');
  btn.setAttribute('aria-expanded', 'true');
  btn.setAttribute('aria-label', '메뉴 닫기');
  document.body.style.overflow = 'hidden';
  menu.querySelector('a, button')?.focus();
}

function closeMenu() {
  menu.classList.remove('is-open');
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-label', '메뉴 열기');
  document.body.style.overflow = '';
  btn.focus();
}
```

## 반응형 breakpoint에서 display 전환

데스크탑에서는 햄버거 버튼을 숨기고 풀 네비게이션을 보여준다.

```css
.hamburger-btn {
  display: flex;
}

.nav-menu {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #fff;
  z-index: 100;
}

.nav-menu.is-open {
  display: block;
}

@media (min-width: 768px) {
  .hamburger-btn {
    display: none;
  }

  .nav-menu {
    display: flex;
    position: static;
    height: auto;
    background: transparent;
  }
}
```

JS에서 메뉴를 조작할 때 `display: none`을 직접 건드리지 않고 클래스로만 제어해야 한다. 인라인 스타일이 섞이면 CSS media query와 충돌한다.

## 모바일 터치 이벤트 처리

햄버거 버튼 자체는 `click` 이벤트로 처리해도 되지만, 모바일에서 300ms 딜레이가 신경 쓰이는 경우 `touchend`를 병행하기도 한다.

```javascript
btn.addEventListener('touchend', (e) => {
  e.preventDefault(); // click 이벤트 중복 방지
  btn.click();
});
```

`e.preventDefault()`를 빠뜨리면 `touchend` 후 300ms 뒤에 `click`이 또 발생해서 메뉴가 열렸다가 바로 닫힌다.

요즘 모던 브라우저는 `touch-action: manipulation`을 CSS에 선언하는 걸로 딜레이를 없애기도 한다.

```css
.hamburger-btn {
  touch-action: manipulation;
}
```

## body scroll lock

메뉴가 열렸을 때 배경 콘텐츠가 스크롤되면 사용자가 혼란스럽다. `overflow: hidden`만으로는 iOS Safari에서 스크롤이 막히지 않는다.

```javascript
let scrollY = 0;

function lockScroll() {
  scrollY = window.scrollY;
  document.body.style.position = 'fixed';
  document.body.style.top = `-${scrollY}px`;
  document.body.style.width = '100%';
}

function unlockScroll() {
  document.body.style.position = '';
  document.body.style.top = '';
  document.body.style.width = '';
  window.scrollTo(0, scrollY);
}
```

`position: fixed`로 body를 고정하면 iOS Safari에서도 동작한다. `scrollY`를 저장해뒀다가 복원하지 않으면 메뉴를 닫았을 때 페이지 최상단으로 튀어 올라간다.

## 오버레이 배경 클릭 닫기

```html
<div class="overlay"></div>
<nav id="nav-menu" class="nav-menu">...</nav>
```

```css
.overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

.overlay.is-visible {
  display: block;
}
```

```javascript
const overlay = document.querySelector('.overlay');

function openMenu() {
  menu.classList.add('is-open');
  overlay.classList.add('is-visible');
  lockScroll();
  // ...
}

function closeMenu() {
  menu.classList.remove('is-open');
  overlay.classList.remove('is-visible');
  unlockScroll();
  // ...
}

overlay.addEventListener('click', closeMenu);
```

오버레이 z-index는 메뉴보다 1 낮게 설정한다. 같거나 높으면 메뉴 내부 클릭이 오버레이로 전파될 수 있다.

## 트러블슈팅

### z-index 충돌

헤더가 `position: sticky`이고 메뉴가 `position: fixed`인 경우, 헤더의 z-index가 메뉴보다 높으면 메뉴가 헤더 아래에 숨는다. 레이어 순서를 명시적으로 정해두는 게 낫다.

```css
/* z-index 레이어 정의 */
:root {
  --z-overlay: 100;
  --z-menu: 200;
  --z-header: 300;
}
```

메뉴가 헤더 위에 와야 하는 디자인이면 헤더 z-index를 메뉴보다 낮춰야 한다. 이걸 변수 없이 파일 여기저기에 숫자로 박아두면 나중에 충돌 원인 찾는 데 시간이 오래 걸린다.

### iOS Safari 스크롤 버그

`overflow: hidden`을 body에 걸어도 iOS Safari에서는 터치 드래그로 배경이 스크롤된다. 위에서 설명한 `position: fixed` 방식으로 해결한다.

추가로, iOS에서 `position: fixed` 요소 내부에 `input`이 있으면 키보드 올라올 때 뷰포트가 밀리는 문제도 있다. 메뉴 안에 검색창이 있는 경우에 발생한다. 이때는 `visualViewport` API로 뷰포트 높이를 추적해서 메뉴 높이를 동적으로 보정한다.

```javascript
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    menu.style.height = `${window.visualViewport.height}px`;
  });
}
```

### 메뉴 상태가 breakpoint 전환 후에도 남는 문제

모바일에서 메뉴를 열고 창을 넓히면 데스크탑 breakpoint로 전환되는데, `is-open` 클래스와 scroll lock이 그대로 남아있는 경우가 있다.

```javascript
const mediaQuery = window.matchMedia('(min-width: 768px)');

mediaQuery.addEventListener('change', (e) => {
  if (e.matches) {
    closeMenu();
  }
});
```

`matchMedia`로 breakpoint 변경을 감지해서 메뉴 상태를 초기화한다.

### 애니메이션 중 클릭 중복 처리

애니메이션 진행 중에 버튼을 빠르게 여러 번 누르면 상태가 꼬이는 경우가 있다. 애니메이션이 끝날 때까지 클릭을 막거나, 상태 플래그로 처리한다.

```javascript
let isAnimating = false;

btn.addEventListener('click', () => {
  if (isAnimating) return;
  isAnimating = true;

  // 토글 처리...

  menu.addEventListener('transitionend', () => {
    isAnimating = false;
  }, { once: true });
});
```
