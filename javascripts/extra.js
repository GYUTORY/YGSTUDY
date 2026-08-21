(function () {
  /* GitHub 릴리스 조회 차단 코드가 여기 있었는데 지웠다 — 두 겹으로 안 먹었다.
     (1) `window.fetch` 만 가로챘는데 Material 은 XMLHttpRequest 를 쓴다.
     (2) 이 파일은 body 끝이라 Material 번들보다 뒤에 돈다.
     번들보다 먼저 도는 자리(overrides/main.html 의 head 인라인)로 옮겼다. */

  var pos = 0;

  // 사이드바 내 scrollIntoView 완전 차단
  var _siv = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function (a) {
    if (this.closest && this.closest(".md-sidebar")) return;
    _siv.call(this, a);
  };

  document.addEventListener("DOMContentLoaded", function () {
    var sb = document.querySelector(".md-sidebar__scrollwrap");

    if (sb) {
      var restoring = false;

      // 사용자가 직접 스크롤한 경우에만 위치 저장
      sb.addEventListener("wheel", function () { pos = sb.scrollTop; }, { passive: true });
      sb.addEventListener("touchmove", function () { pos = sb.scrollTop; }, { passive: true });
      /* 휠과 터치만 보면 스크롤바를 끌거나 키보드로 움직인 건 놓친다. 그러면
         pos 가 옛날 값인 채로 남아 있다가, 복원이 걸리는 순간 사용자가 보던
         자리에서 엉뚱한 데로 튄다. 스크롤 자체를 보되 우리가 되돌리는
         중일 때는 세지 않는다. */
      sb.addEventListener("scroll", function () {
        if (!restoring) pos = sb.scrollTop;
      }, { passive: true });

      // MutationObserver: active 클래스 변화 감지 후 1회 정확히 복원
      var nav = document.querySelector(".md-sidebar--primary .md-nav");
      if (nav) {
        var observer = new MutationObserver(function () {
          if (restoring) return;
          restoring = true;
          sb.scrollTop = pos;
          setTimeout(function () {
            sb.scrollTop = pos;
            restoring = false;
          }, 50);
        });
        observer.observe(nav, { subtree: true, attributes: true, attributeFilter: ["class"] });
      }

      /* 메뉴 클릭 fallback — 페이지를 떠나는 클릭에서만 위치를 되돌린다.

         원래는 `.md-nav` 안이면 무엇을 눌렀든 100ms 뒤에 스크롤을 되돌렸다.
         펼침 화살표를 눌렀을 때도 되돌아가서, 방금 펼친 자리에서 목록이
         위로 튀었다. 휠을 굴린 적이 없으면 pos 가 0 이라 맨 위까지 올라간다.

         "화살표가 아니면" 으로 걸렀더니 부족했다. `<label for>` 를 누르면
         브라우저가 체크박스에도 클릭을 한 번 더 보내는데, 그 이벤트의
         target 은 label 이 아니라 input 이라 걸러지지 않았다.
         무엇이 아닌지 대신 무엇인지로 판정한다 — 링크를 눌렀을 때만. */
      document.addEventListener("click", function (e) {
        if (!e.target.closest) return;
        if (!e.target.closest(".md-nav a.md-nav__link")) return;
        var p = pos;
        setTimeout(function () { sb.scrollTop = p; }, 100);
      });
    }

    // Reading Progress Bar
    var bar = document.createElement("div");
    bar.id = "reading-progress";
    document.body.appendChild(bar);

    /* 스크롤 한 번에 레이아웃을 한 번씩 강제로 계산하던 자리다.

       원래는 scroll 이벤트마다 scrollHeight 와 clientHeight 를 읽고 곧바로
       bar.style.width 를 썼다. 읽고 쓰는 걸 같은 핸들러에서 하면 브라우저가
       그때마다 레이아웃을 다시 계산한다. 이 저장소는 한 문서가 4만 픽셀
       (53화면)까지 가서 그 계산이 싸지 않다.

       높이는 스크롤 중에 안 변한다. 미리 재 두고 창 크기나 내용이 바뀔 때만
       다시 잰다. 쓰기는 프레임당 한 번으로 묶는다. */
    var docH = 0;
    var ticking = false;

    function measure() {
      docH = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    }

    function paint() {
      ticking = false;
      var top = window.scrollY || document.documentElement.scrollTop;
      bar.style.width = Math.min(docH > 0 ? (top / docH) * 100 : 0, 100) + "%";
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(paint);
    }

    measure();
    paint();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", function () { measure(); onScroll(); }, { passive: true });
    // 이미지·머메이드가 늦게 그려지면 문서 높이가 바뀐다.
    if (window.ResizeObserver) {
      new ResizeObserver(function () { measure(); onScroll(); }).observe(document.body);
    } else {
      window.addEventListener("load", function () { measure(); onScroll(); });
    }

    /* 사이드바 형제 메뉴 라벨의 공통 접두어를 잘라내던 코드를 여기서 지웠다.
       (2026-08-21, 지우기 직전 커밋 a4e8e8a040)

       한 번도 걸리지 않았다. 실제 문서 60개 표본에서 메뉴 리스트를 전부 훑어
       축약된 라벨이 0개였다. 선택자가 잘못됐나 싶어 — 항목의 <a> 가 <li> 직속이
       아니라 <div class="md-nav__container"> 안에 있는 경우를 못 찾는다 —
       그쪽까지 찾도록 고쳐서 다시 재 봤는데 여전히 0개였다.

       선택자 문제가 아니라 조건이 성립하는 자리가 없다. 형제 3개 이상이
       4글자 넘는 공통 접두어를 가져야 하는데, 라벨이 이미 .pages 에서
       사람 손으로 정리돼 있어 그런 묶음이 안 생긴다.

       비용은 있었다. 페이지를 열 때마다 사이드바 리스트를 전부 훑고,
       사이드바가 바뀔 때마다(80ms 디바운스) 또 훑었다. 잘린 가지를 펼치는
       기능이 들어오면서 그 재실행이 더 잦아졌다.

       다시 필요해지면 되살리는 것보다 다시 쓰는 편이 낫다. 그때는 어떤
       라벨 묶음을 줄이려는 건지부터 실제 문서에서 확인할 것. */

    // ----- 홈 카테고리 카운트 -----
    // 빌드 때 tools/section_index.py 가 만든 section_counts.json 을 읽는다.
    // 예전에는 sitemap 경로를 세그먼트로 세었는데, 그러면 Backend/Security/,
    // Cloud/AWS/Security/ 같은 다른 섹션 하위 폴더까지 Security 로 집계돼
    // 카드 숫자와 섹션 페이지 숫자가 어긋났다(13개 섹션 전부, Security 는 10건 차이).
    // 두 숫자가 영원히 같으려면 같은 소스에서 나와야 한다.
    var countTargets = document.querySelectorAll("[data-yg-count]");
    var totalTarget = document.querySelector("[data-yg-total]");
    if (!countTargets.length && !totalTarget) return;

    var base = document.querySelector("link[rel=canonical]");
    var root = base ? new URL(base.href).pathname.replace(/[^\/]*$/, "") : "/";

    fetch(root + "section_counts.json", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (counts) {
        if (!counts) return;
        var total = 0;
        Object.keys(counts).forEach(function (k) {
          if (k.indexOf("/") === -1) total += counts[k];
        });
        countTargets.forEach(function (el) {
          // 한 카드가 여러 폴더를 묶는 경우가 있다(가이드 = _hub + 로드맵 + Frontend).
          // 쉼표로 여러 키를 받아 합산한다.
          var n = el
            .getAttribute("data-yg-count")
            .split(",")
            .reduce(function (sum, k) {
              return sum + (counts[k.trim()] || 0);
            }, 0);
          el.textContent = n ? n + "개" : "—";
        });
        if (totalTarget) totalTarget.textContent = total > 0 ? total : "—";
      })
      .catch(function () { /* 실패 시 placeholder 유지 */ });
  });
})();

/* 헤더의 저장소 스타·포크 숫자.
 *
 * 개인 블로그라 둘 다 0이고, 화면에는 "☆0 ⑂0" 으로 나온다.
 * 숫자가 0인 배지는 정보가 아니라 덜 만든 자리처럼 읽힌다.
 * 그렇다고 아예 지우면 나중에 스타가 붙어도 안 보이므로,
 * 0일 때만 감춘다. Material 이 GitHub API 응답을 받아 채운 뒤 판단해야 해서
 * 잠깐 기다렸다가 본다.
 */
(function () {
  function hideZeroFacts() {
    var facts = document.querySelectorAll(".md-source__fact");
    if (!facts.length) return false;
    var shown = 0;
    facts.forEach(function (el) {
      var n = parseInt((el.textContent || "").replace(/[^0-9]/g, ""), 10);
      // 버전 표기 등 숫자가 아닌 항목은 건드리지 않는다
      if (el.textContent.trim() && n === 0) el.style.display = "none";
      else shown++;
    });
    var list = document.querySelector(".md-source__facts");
    if (list && shown === 0) list.style.display = "none";
    return true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var tries = 0;
    var timer = setInterval(function () {
      if (hideZeroFacts() || ++tries > 20) clearInterval(timer);
    }, 300);
  });
})();

/* 본문으로 건너뛰기.
 *
 * Material 은 목차 첫 항목을 목적지로 삼아 스킵 링크를 만든다. 대문은 toc 를
 * 숨긴 raw HTML 이라 목적지가 없어 링크 자체가 안 나왔고, 키보드로 첫 카드까지
 * 가는 데 Tab 16번이 걸렸다(문서 페이지는 1번). 없을 때만 같은 모양으로 만든다.
 */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // Material 이 이미 skip 을 만든 문서 페이지에서는, 그 링크가 해시만 옮기고
    // 포커스는 안 옮긴다(실측: Enter 후 activeElement 가 BODY). 그러면 포커스 링이
    // 사라져 지금 어디인지 알 수 없다. 만들지는 말고 동작만 보태 준다.
    var made = document.querySelector(".md-skip");
    if (made) {
      var href = made.getAttribute("href") || "";
      var dst = href.charAt(0) === "#" && document.getElementById(href.slice(1));
      if (dst) {
        if (!dst.hasAttribute("tabindex")) dst.setAttribute("tabindex", "-1");
        made.addEventListener("click", function () {
          setTimeout(function () { dst.focus({ preventScroll: false }); }, 0);
        });
      }
      return;
    }
    var target = document.querySelector(".md-content__inner") || document.querySelector(".md-content");
    if (!target) return;
    if (!target.id) target.id = "yg-main";
    target.setAttribute("tabindex", "-1");

    var a = document.createElement("a");
    a.href = "#" + target.id;
    a.className = "md-skip";
    a.textContent = "본문으로 건너뛰기";
    // 해시 이동만으로는 포커스가 따라가지 않아, 그 다음 Tab 이 다시 헤더로 돌아간다.
    a.addEventListener("click", function () {
      setTimeout(function () { target.focus({ preventScroll: false }); }, 0);
    });
    document.body.insertBefore(a, document.body.firstChild);
  });
})();

/* 히어로 검색 상자의 단축키 배지.
 *
 * "⌘K" 라고 적혀 있는데 실제로 눌러도 아무 일이 없었다(실측: Meta+K·Ctrl+K 모두
 * 검색 안 열림, 열리는 건 "/" 뿐). 표기를 "/" 로 낮추는 대신 배지대로 동작하게
 * 만든다 — Cmd/Ctrl+K 는 지금 대부분의 검색 UI 가 쓰는 조합이라 먼저 눌러보게 된다.
 * 검색 열기는 Material 이 change 이벤트로 감지하므로 체크박스를 직접 클릭한다.
 */
(function () {
  var isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent || "");

  document.addEventListener("DOMContentLoaded", function () {
    if (!isMac) {
      document.querySelectorAll("[data-yg-kbd]").forEach(function (el) {
        el.textContent = "Ctrl K";
      });
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.shiftKey) return;
    if (!(e.metaKey || e.ctrlKey)) return;
    if ((e.key || "").toLowerCase() !== "k") return;
    var toggle = document.querySelector("#__search");
    if (!toggle) return;
    e.preventDefault();
    if (!toggle.checked) toggle.click();
    var input = document.querySelector(".md-search__input");
    if (input) setTimeout(function () { input.focus(); input.select(); }, 20);
  });
})();

/* 코드블록 가로 스크롤 표시.
 *
 * 한 문서에서 코드블록 88개 중 25개가 가로로 넘치고 최대 510px 이 숨는데
 * (모바일은 54개·565px) 잘렸다는 표시가 없었다. macOS overlay 스크롤바는
 * 스크롤을 시작해야 나타나서 가만히 있는 화면에서는 단서가 되지 않는다.
 * 남은 내용이 있는 쪽에만 그림자를 켠다(그림자 자체는 extra.css).
 */
(function () {
  /* 읽기와 쓰기를 반드시 나눠서 한다.

     원래는 코드블록 하나마다 scrollWidth 를 읽고 곧바로 속성을 썼다. 속성을
     쓰면 레이아웃이 무효가 되므로 다음 블록을 읽을 때 다시 계산된다. 블록
     수만큼 레이아웃이 반복된다 — 이 저장소에서 가장 큰 문서는 코드블록이
     164개고, scanAll 은 DOMContentLoaded·폰트 로드·load 로 세 번 돈다.

     전부 재고 나서 전부 쓰면 레이아웃은 한 번이면 된다. */
  function measure(code) {
    var wrap = code.parentElement && code.parentElement.parentElement;
    if (!wrap || !wrap.classList.contains("highlight")) return null;
    var max = code.scrollWidth - code.clientWidth;
    if (max <= 4) return { wrap: wrap, sides: null };
    var sides = [];
    if (code.scrollLeft > 2) sides.push("l");
    if (code.scrollLeft < max - 2) sides.push("r");
    return { wrap: wrap, sides: sides.join(" ") };
  }

  function apply(m) {
    if (!m) return;
    if (m.sides === null) m.wrap.removeAttribute("data-yg-scroll");
    else m.wrap.setAttribute("data-yg-scroll", m.sides);
  }

  function mark(code) {
    apply(measure(code));
  }

  function scanAll() {
    var out = [];
    document.querySelectorAll(".md-typeset .highlight > pre > code")
      .forEach(function (c) { out.push(measure(c)); });   // 읽기만
    out.forEach(apply);                                    // 그 다음 쓰기만
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.querySelector(".md-typeset .highlight")) return;
    scanAll();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(scanAll);
    window.addEventListener("load", scanAll);

    // scroll 은 버블링하지 않으므로 캡처 단계에서 받는다.
    document.addEventListener("scroll", function (e) {
      var t = e.target;
      if (t && t.tagName === "CODE") mark(t);
    }, true);

    var t = null;
    window.addEventListener("resize", function () {
      clearTimeout(t);
      t = setTimeout(scanAll, 150);
    }, { passive: true });
  });
})();

/* 다이어그램이 읽을 수 없을 만큼 줄어드는 것 막기.
 *
 * mermaid SVG 는 max-width:100% 라 칸보다 넓으면 무조건 줄어든다. 표본 49개를
 * 재보니 데스크톱(720px 칸)에서 13개가 0.8배 미만, 최소 0.39배였고, 모바일
 * (390px)에서는 38개가 0.8배 미만에 최소 0.19배였다. 그 배율이면 그림 안
 * 글자가 데스크톱 최소 4.3px, 모바일 중앙값 5.6px·최소 2.1px 가 된다.
 *
 * 그래서 "본래 폭 × 0.8" 을 min-width 로 박는다. 칸이 그보다 넓으면 아무 일도
 * 일어나지 않고(작은 그림은 그대로), 좁으면 0.8배에서 멈추고 가로 스크롤로
 * 넘어간다. 잘린 쪽 표시는 코드블록과 같은 data-yg-scroll 을 쓴다.
 */
(function () {
  var FLOOR = 0.8;

  function naturalWidth(svg) {
    var vb = svg.getAttribute("viewBox");
    if (vb) {
      var n = parseFloat(vb.split(/[\s,]+/)[2]);
      if (n > 0) return n;
    }
    var w = parseFloat(svg.getAttribute("width"));
    return w > 0 ? w : 0;
  }

  function measureScroll(box) {
    var max = box.scrollWidth - box.clientWidth;
    if (max <= 4) return { box: box, sides: null };
    var sides = [];
    if (box.scrollLeft > 2) sides.push("l");
    if (box.scrollLeft < max - 2) sides.push("r");
    return { box: box, sides: sides.join(" ") };
  }

  function applyScroll(m) {
    if (m.sides === null) m.box.removeAttribute("data-yg-scroll");
    else m.box.setAttribute("data-yg-scroll", m.sides);
  }

  function markScroll(box) {
    applyScroll(measureScroll(box));
  }

  function apply(box) {
    var svg = box.querySelector(":scope > svg");
    if (!svg) return false;
    var nat = naturalWidth(svg);
    if (nat > 0 && !box.dataset.ygFloor) {
      // svg 의 style 속성에 직접 쓰면 안 된다 — mermaid 가 렌더 끝에
      // style="max-width:...px" 를 통째로 덮어써서 지워진다(실측).
      // 컨테이너의 커스텀 속성에 남기고 값 적용은 CSS 가 한다.
      box.style.setProperty("--yg-diagram-min", Math.round(nat * FLOOR) + "px");
      box.dataset.ygFloor = "1";
    }
    return true;
  }

  /* 최소폭을 박는 것과 잘림 표시를 두 단계로 나눈다.

     한 상자마다 `--yg-diagram-min` 을 쓰고 곧바로 scrollWidth 를 읽으면,
     쓰기가 레이아웃을 무효로 만들어 놓고 바로 읽으니 상자 수만큼 레이아웃이
     반복된다. 최소폭을 전부 박고 나서 잘림을 전부 재면 두 번이면 된다. */
  function scan() {
    var pending = 0;
    var boxes = [];
    document.querySelectorAll(".md-typeset .yg-mermaid").forEach(function (box) {
      if (apply(box)) boxes.push(box);
      else pending++;
    });
    // 표도 같은 처지다 — Material 이 overflow:auto 래퍼에 넣어 옆으로 굴리는데
    // 잘렸다는 표시가 없다(한 문서에서 표 6개 중 3개가 최대 220px 씩 숨었다).
    document.querySelectorAll(".md-typeset__table").forEach(function (t) { boxes.push(t); });

    var measured = boxes.map(measureScroll);   // 읽기만
    measured.forEach(applyScroll);             // 그 다음 쓰기만
    return pending;
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.querySelector(".md-typeset .yg-mermaid, .md-typeset__table")) return;
    scan();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(scan);
    window.addEventListener("load", scan);

    /* mermaid 는 화면에 들어올 때 그린다. svg 가 꽂히는 것을 보고 그때 처리한다.

       한 번에 여러 개가 꽂힐 수 있어서(화면에 두 개가 같이 들어오는 경우)
       상자마다 쓰고-읽고 하지 않는다. 최소폭을 먼저 다 박고, 잘림은 그 뒤에
       한꺼번에 잰다. 같은 상자가 두 번 들어오는 것도 걸러 낸다. */
    var mo = new MutationObserver(function (list) {
      var seen = [];
      list.forEach(function (m) {
        var box = m.target.closest && m.target.closest(".yg-mermaid");
        if (box && seen.indexOf(box) === -1 && apply(box)) seen.push(box);
      });
      if (!seen.length) return;
      seen.map(measureScroll).forEach(applyScroll);
    });
    mo.observe(document.querySelector(".md-typeset"), { childList: true, subtree: true });

    document.addEventListener("scroll", function (e) {
      var t = e.target;
      if (!t || !t.classList) return;
      if (t.classList.contains("yg-mermaid") || t.classList.contains("md-typeset__table")) markScroll(t);
    }, true);

    var t = null;
    window.addEventListener("resize", function () {
      clearTimeout(t);
      t = setTimeout(scan, 150);
    }, { passive: true });
  });
})();

/* 사이드바 펼침 토글에 이름 붙이기.
 *
 * Material 은 접히는 섹션마다 아이콘만 든 빈 label 을 만들고 tabindex="0" 을
 * 준다. 키보드로 멈추는 자리인데 읽어줄 글자가 없다. 게다가
 * <nav aria-labelledby="__nav_8_label"> 이 그 빈 label 을 가리켜서
 * nav 랜드마크 이름까지 빈 값이 된다 — 한 문서에서 nav 63개 중 40개가 그랬다.
 *
 * 섹션 이름은 바로 옆 <a> 에 이미 있다("AI", "개념"). 그걸 가져다 쓴다.
 * 화면에 보이는 것은 아무것도 바뀌지 않는다.
 */
(function () {
  function nameToggles() {
    document.querySelectorAll("label.md-nav__link").forEach(function (label) {
      if (label.getAttribute("aria-label")) return;
      if (label.textContent.trim()) return;
      var item = label.closest(".md-nav__item");
      var link = item && item.querySelector(":scope > a.md-nav__link, :scope > .md-nav__container > a");
      var name = link && link.textContent.trim();
      if (!name) {
        // index 페이지가 없는 섹션은 형제 a 가 없다. nav 안의 제목을 쓴다.
        var nav = item && item.querySelector(":scope > nav > .md-nav__title");
        name = nav && nav.textContent.trim();
      }
      if (!name) return;
      label.setAttribute("aria-label", name + " 하위 목록 펼치기");

      // aria-labelledby 는 가리킨 요소의 '글자' 만 읽는다. label 에 aria-label 을
      // 달아도 그걸 참조하는 nav 는 여전히 이름이 빈 채로 남는다.
      // 그래서 nav 쪽에 직접 이름을 준다.
      var nested = item.querySelector(":scope > nav");
      if (nested && !nested.getAttribute("aria-label")) {
        nested.setAttribute("aria-label", name);
      }
    });
  }

  /* 코드블록의 복사 버튼은 <nav class="md-code__nav"> 로 감싸여 나온다.
   * 링크가 하나도 없는데 랜드마크로 잡혀서, 스크린리더 랜드마크 목록이
   * 이름 없는 nav 로 뒤덮인다(한 문서에 39개). 실제로 길찾기 영역이 아니므로
   * 랜드마크에서 빼는 게 맞다. 버튼 자체는 title 로 이미 이름이 있다. */
  function unmarkCodeNav() {
    document.querySelectorAll("nav.md-code__nav").forEach(function (nav) {
      if (nav.querySelector("a")) return;
      nav.setAttribute("role", "presentation");
    });
  }

  /* 중첩 nav 를 랜드마크에서 뺀다.
   *
   * 목차 섹션마다, 사이드바 하위 목록마다 nav 가 하나씩 생겨서 다이어그램 문서에서
   * 랜드마크가 30개까지 늘어난다. "랜드마크로 건너뛰기" 목록이 쓸모없어진다.
   *
   * role="presentation" 은 여기서 무시된다 — 이 nav 들은 aria-labelledby 와
   * aria-expanded 를 갖고 있어 presentational role 충돌 해소 규칙에 걸린다.
   * (코드블록 nav 는 aria 속성이 없어서 먹혔다.) group 은 랜드마크가 아니면서
   * 이름을 유지한다. list 는 안 된다 — 이 nav 안에는 label 제목과 ul 이 함께 있다.
   *
   * 최상위 목차(md-nav--secondary)는 좁은 화면에서 드로어 안으로 들어가므로
   * 반드시 제외한다.
   */
  function ungroupNestedNav() {
    document.querySelectorAll("nav.md-nav nav.md-nav:not(.md-nav--secondary)").forEach(function (nav) {
      nav.setAttribute("role", "group");
    });
  }

  function run() {
    nameToggles();
    unmarkCodeNav();
    ungroupNestedNav();
  }

  document.addEventListener("DOMContentLoaded", run);
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(run);
  }
})();


/* 스크린리더가 놓치던 것 세 가지.
 *
 * 1) 본문 맨 위 태그 칩 목록(nav.md-tags)에 이름이 없다. 링크가 있는 진짜
 *    내비게이션이라 랜드마크에서 뺄 수는 없고 이름만 주면 된다.
 * 2) 검색 결과 건수가 바뀌어도 음성으로 전달되지 않는다. 페이지 전체에
 *    aria-live 가 하나도 없어서, 결과가 나왔는지조차 알 수 없었다.
 * 3) 제목 앵커가 한글 사이트에서 제목마다 "Permanent link" 로 읽힌다.
 */
(function () {
  function label() {
    document.querySelectorAll("nav.md-tags:not([aria-label])").forEach(function (n) {
      n.setAttribute("aria-label", "문서 태그");
    });
    var meta = document.querySelector(".md-search-result__meta");
    if (meta && !meta.getAttribute("aria-live")) {
      meta.setAttribute("aria-live", "polite");
      meta.setAttribute("role", "status");
    }
    // 제목 앵커는 접근성 트리에서 뺀다.
    //
    // 처음엔 aria-label 로 이름을 줬는데, 그 이름이 부모 heading 의 접근 이름
    // 계산에 들어가는 바람에 제목이 두 번씩 읽혔다("부분 인덱스 부분 인덱스 링크").
    // 한 문서에 제목이 63개면 63번 그렇다 — 고치기 전(Permanent link)보다 나빠졌다.
    //
    // 앵커는 제목 자체로 가는 중복 링크라 빼도 잃는 정보가 없고,
    // 덤으로 문서당 수십 개의 불필요한 탭 정지점도 사라진다.
    // aria-hidden 을 쓰므로 tabindex="-1" 을 함께 줘야 한다
    // — 숨겨졌는데 포커스는 가능한 상태를 만들지 않기 위해서다.
    document.querySelectorAll("a.headerlink").forEach(function (a) {
      a.removeAttribute("aria-label");
      a.setAttribute("aria-hidden", "true");
      a.setAttribute("tabindex", "-1");
    });
  }

  document.addEventListener("DOMContentLoaded", label);
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(label);
  }
})();

/* 검색이 준비되는 동안 그렇다고 알린다.
 *
 * 왜: 검색 색인은 페이지가 뜨자마자 워커에서 만들어지는데, 그게 데스크톱에서
 * 6.7초, 모바일 3G·저사양 CPU 에서는 39초가 걸린다(실측). 그동안 검색창은
 * 멀쩡히 열리고 글자도 쳐지는데 결과 영역은 "검색 초기화" 그대로다.
 * 다운로드는 71ms 라 회선 문제가 아니라 전부 CPU 다 — 즉 기다리면 되는데,
 * 기다리라는 말이 없어서 고장 난 것처럼 보인다.
 *
 * 색인 자체를 줄이는 일은 따로 하고, 여기서는 상태만 정직하게 보여 준다.
 * 워커가 처음 응답하면 Material 이 이 자리를 결과 건수로 덮어쓰므로
 * 우리 문구는 그때 저절로 사라진다.
 */
(function () {
  var PREPARING = "검색 준비 중입니다. 처음 한 번만 걸립니다…";

  function wire() {
    var meta = document.querySelector(".md-search-result__meta");
    var input = document.querySelector(".md-search__input");
    if (!meta || !input || meta.hasAttribute("data-yg-wait")) return;
    meta.setAttribute("data-yg-wait", "1");

    var ready = false;
    var initial = (meta.textContent || "").trim();

    // 워커가 처음 응답하면 Material 이 이 자리 문구를 결과 건수로 바꾼다.
    // 그 변화를 준비 완료 신호로 쓴다 — 결과가 0건이어도 문구는 바뀐다.
    var obs = new MutationObserver(function () {
      var now = (meta.textContent || "").trim();
      if (now !== initial && now !== PREPARING) {
        ready = true;
        obs.disconnect();
      }
    });
    obs.observe(meta, { childList: true, characterData: true, subtree: true });

    input.addEventListener("input", function () {
      if (ready || !input.value.trim()) return;
      if ((meta.textContent || "").trim() === PREPARING) return;
      meta.textContent = PREPARING;
    });
  }

  document.addEventListener("DOMContentLoaded", wire);
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(wire);
  }
})();


/* 키보드로만 쓸 때 막히는 자리들.
 *
 * 실측(Playwright, Tab 전수 추적)으로 나온 것 셋을 고친다.
 *
 * 1) 375px 에서 사이트 내비게이션에 아예 못 간다. 햄버거가
 *    <label class="md-header__button" for="__drawer"> 인데 label 은 기본
 *    포커스 대상이 아니고 tabindex 도 없다. 375px 4개 페이지 전수 Tab 에서
 *    primary nav 정지점이 0개였다 — 검색이 유일한 통로였다.
 * 2) Esc 로 검색을 닫으면 포커스가 body 로 사라진다. 다음 Tab 이 페이지
 *    맨 처음부터 다시 시작한다.
 * 3) .md-search__scrollwrap 이 Material 템플릿에서 tabindex="0" 으로 박혀 있어,
 *    검색이 닫혀 있어도 페이지마다 아무 데도 안 보이는 정지점이 하나 생긴다.
 */
(function () {
  function wire() {
    // 1) 햄버거를 키보드로
    var burger = document.querySelector('label.md-header__button[for="__drawer"]');
    var drawer = document.getElementById("__drawer");
    if (burger && drawer && !burger.hasAttribute("data-yg-kbd")) {
      burger.setAttribute("data-yg-kbd", "1");
      burger.setAttribute("tabindex", "0");
      burger.setAttribute("role", "button");
      burger.setAttribute("aria-label", "내비게이션 메뉴 열기");
      burger.setAttribute("aria-expanded", String(drawer.checked));
      // 여는 일 자체는 브라우저가 한다. tabindex 만 주면 Enter 로 라벨이 활성화되고
      // for= 대상 체크박스가 켜진다(실측). 여기서 또 토글하면 두 번 뒤집혀
      // 도로 닫힌다 — 처음에 그렇게 짰다가 "Enter 를 눌러도 안 열린다" 로 한참 헤맸다.
      // 우리가 할 일은 상태를 알리고 포커스를 안으로 넣는 것뿐이다.
      burger.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        setTimeout(function () {
          burger.setAttribute("aria-expanded", String(drawer.checked));
          if (!drawer.checked) return;
          // 안 그러면 연 다음 Tab 이 드로어를 지나쳐 본문으로 가버린다.
          // 드로어가 transform 으로 미끄러져 들어오는 동안은 visibility 가 hidden 이라
          // focus() 가 조용히 무시된다. 보일 때까지 몇 번 다시 시도한다.
          // 첫 번째 링크를 그냥 집으면 안 된다 — 접혀 있는 하위 항목이 앞에 오는
          // 경우가 있어 visibility:hidden 인 요소를 잡고, focus() 가 조용히 무시된다
          // (실측: 링크 53개 중 43개만 보이는데 첫 번째가 숨은 쪽이었다).
          // 드로어가 미끄러져 들어오는 동안도 hidden 이라 보일 때까지 다시 시도한다.
          var tries = 0;
          (function grab() {
            var nav = document.querySelector(".md-sidebar--primary");
            var links = nav ? nav.querySelectorAll("a.md-nav__link") : [];
            for (var i = 0; i < links.length; i++) {
              // visibility 만 보면 안 된다 — display:none 인 요소도 visibility 는
              // visible 로 계산된다(현재 문서 링크가 실제로 그렇다). 실제로 자리를
              // 차지하는지로 판단해야 focus() 가 먹는다.
              if (getComputedStyle(links[i]).visibility === "visible" &&
                  links[i].getClientRects().length > 0) {
                links[i].focus();
                return;
              }
            }
            if (++tries < 12) setTimeout(grab, 50);
          })();
        }, 60);
      });
      drawer.addEventListener("change", function () {
        burger.setAttribute("aria-expanded", String(drawer.checked));
      });
    }

    // 2) Esc 로 검색을 닫으면 원래 자리로 포커스를 돌려준다
    var search = document.getElementById("__search");
    if (search && !search.hasAttribute("data-yg-kbd")) {
      search.setAttribute("data-yg-kbd", "1");
      var from = null;
      document.addEventListener("focusin", function (e) {
        if (search.checked) return;
        if (e.target && e.target.closest && e.target.closest(".md-search")) return;
        from = e.target;
      }, true);
      search.addEventListener("change", function () {
        if (search.checked || !from || !document.contains(from)) return;
        var back = from;
        setTimeout(function () { try { back.focus(); } catch (err) {} }, 0);
      });
    }

    // 3) 닫힌 검색의 빈 정지점 제거
    var wrap = document.querySelector(".md-search__scrollwrap");
    if (wrap && search) {
      var sync = function () {
        if (search.checked) wrap.setAttribute("tabindex", "0");
        else wrap.removeAttribute("tabindex");
      };
      sync();
      if (!wrap.hasAttribute("data-yg-kbd")) {
        wrap.setAttribute("data-yg-kbd", "1");
        search.addEventListener("change", sync);
      }
    }
  }

  document.addEventListener("DOMContentLoaded", wire);
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(wire);
  }
})();


/* 잘린 가지를 눌러서 펼친다.

   navigation.prune 은 현재 경로 밖 섹션의 자식을 렌더하지 않는다. 그런데
   화살표는 남는다. 펼쳐질 것처럼 보이는데 눌러도 아무 일이 없었다.
   화살표와 글자가 한 <a> 안에 있어서, 화살표를 눌러도 그냥 페이지가 이동했다.

   prune 을 끄면 펼쳐지긴 한다. 대신 사이드바 항목이 페이지당 135개에서
   1,158개로 늘고(8.6배) 페이지가 201KB → 640KB, 사이트가 205MB → 781MB 다.
   메뉴 하나 펼치자고 모든 페이지가 그 값을 치를 이유가 없다.

   그래서 트리를 nav.json 하나로 빼 뒀다(gzip 13.9KB). 처음 펼칠 때 한 번만
   받고 브라우저가 캐시한다. 화면에 그리는 것도 누른 가지의 한 단계뿐이라
   DOM 은 계속 작게 유지된다.

   페이지를 긁어오는 방법을 먼저 만들었다가 버렸다. Backend·Infra·CS 는
   여러 최상위 폴더를 묶은 가상 섹션이라 자기 index 페이지가 없다. 그래서
   _group/backend/ 에 가도 그 섹션이 pruned 로 나온다 — 긁어올 원본이 없다.
   11개 중 3개가 못 펼치는 채로 남았고, 그 셋이 하필 최상위 메뉴였다. */
(function () {
  var seq = 0;
  var treeP = null;                      // nav.json 로드 약속 (한 번만)
  var data = new WeakMap();              // li -> 트리 노드
  var root = null;                       // 사이트 루트 절대 URL

  function siteRoot() {
    if (root) return root;
    var el = document.getElementById("__config");
    var base = ".";
    if (el) {
      try { base = JSON.parse(el.textContent).base || "."; } catch (e) {}
    }
    root = new URL(base.replace(/\/?$/, "/"), location.href).href;
    return root;
  }

  function norm(u) {
    try { return new URL(u, siteRoot()).href.replace(/\/$/, ""); } catch (e) { return ""; }
  }

  function loadTree() {
    if (treeP) return treeP;
    treeP = fetch(siteRoot() + "nav.json", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
    return treeP;
  }

  /* 제목과 URL 이 함께 맞는 노드를 찾는다.
     섹션과 그 첫 자식이 같은 URL 을 갖는 경우가 있어(예: Backend 와 "백엔드 전체")
     URL 만으로 고르면 자식 없는 쪽이 걸린다. */
  function find(nodes, title, href) {
    var byBoth = null, byUrl = null;
    (function walk(list) {
      for (var i = 0; i < list.length; i++) {
        var n = list[i];
        if (n.c) {
          var u = n.u ? norm(n.u) : "";
          if (n.t === title && u === href) { byBoth = byBoth || n; }
          else if (!byUrl && u === href) { byUrl = n; }
          walk(n.c);
        }
      }
    })(nodes);
    return byBoth || byUrl;
  }

  function el(tag, cls, attrs) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    return e;
  }

  function makeLink(node) {
    var a = el("a", "md-nav__link");
    a.href = node.u ? new URL(node.u, siteRoot()).href : "#";
    var s = el("span", "md-ellipsis");
    s.textContent = node.t;
    a.appendChild(s);
    return a;
  }

  /* 자식 하나를 <li> 로. 자식이 또 있으면 펼칠 수 있는 모양으로 만들되
     안쪽은 아직 그리지 않는다 — 누를 때 그린다. */
  function makeItem(node, level) {
    var li = el("li", "md-nav__item");
    if (!node.c) {
      li.appendChild(makeLink(node));
      return li;
    }
    li.className = "md-nav__item md-nav__item--nested";
    data.set(li, node);
    attach(li, makeLink(node), node.t, level);
    return li;
  }

  function makeNav(node, id, level) {
    var nav = el("nav", "md-nav", {
      "data-md-level": String(level),
      "aria-labelledby": id + "_label",
      "aria-expanded": "true",
    });
    var title = el("label", "md-nav__title", { for: id });
    title.appendChild(el("span", "md-nav__icon md-icon"));
    title.appendChild(document.createTextNode(node.t));
    var ul = el("ul", "md-nav__list", { "data-md-scrollfix": "" });
    node.c.forEach(function (child) { ul.appendChild(makeItem(child, level + 1)); });
    nav.appendChild(title);
    nav.appendChild(ul);
    return nav;
  }

  /* 글자(링크)와 화살표(펼침)를 분리한다. 지금까지 둘이 한 <a> 였던 게
     "눌러도 안 열린다"의 직접 원인이다. */
  function attach(li, anchor, title, level) {
    var id = "__ygnav_" + (++seq);
    var input = el("input", "md-nav__toggle md-toggle", { type: "checkbox", id: id });
    var box = el("div", "md-nav__link md-nav__container");
    var label = el("label", "md-nav__link", {
      for: id, id: id + "_label", tabindex: "0",
      "aria-label": title + " 펼치기",
    });
    label.appendChild(el("span", "md-nav__icon md-icon"));
    box.appendChild(anchor);
    box.appendChild(label);
    li.insertBefore(input, li.firstChild);
    li.appendChild(box);
    li.setAttribute("data-yg-lazy", "1");

    // label 은 키보드로 기본 활성화가 안 된다.
    label.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
    });

    input.addEventListener("change", function () {
      if (!input.checked || li.querySelector(":scope > nav.md-nav")) return;
      var node = data.get(li);
      if (node && node.c) { li.appendChild(makeNav(node, id, level)); return; }
      // 서버가 그린 항목이라 아직 노드를 모른다 — 트리를 받아 찾는다.
      li.setAttribute("data-yg-loading", "1");
      loadTree().then(function (tree) {
        li.removeAttribute("data-yg-loading");
        var hit = tree && find(tree, title, norm(anchor.href));
        if (!hit) {
          // 못 찾으면 거짓 화살표로 남기지 않는다. 링크로 되돌린다.
          li.setAttribute("data-yg-failed", "1");
          input.checked = false;
          label.remove();
          return;
        }
        data.set(li, hit);
        li.appendChild(makeNav(hit, id, level));
      });
    });
  }

  function upgrade(li) {
    if (li.hasAttribute("data-yg-lazy")) return;
    var a = li.querySelector(":scope > a.md-nav__link");
    if (!a) return;
    var icon = a.querySelector(":scope > .md-nav__icon");
    if (!icon) return;
    icon.remove();
    var nav = li.closest("nav.md-nav[data-md-level]");
    var level = nav ? Number(nav.getAttribute("data-md-level")) + 1 : 1;
    attach(li, a, (a.textContent || "").trim(), level);
  }

  function wire() {
    var side = document.querySelector(".md-sidebar--primary") || document;
    side.querySelectorAll("li.md-nav__item--pruned").forEach(upgrade);
  }

  document.addEventListener("DOMContentLoaded", wire);
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(wire);
  }
})();

/* 링크에 손이 닿으면 미리 받아 둔다.
   ------------------------------------------------------------------
   navigation.instant 를 끈 이유는 mkdocs.yml 에 적어 뒀다 — prune 때문에
   페이지마다 사이드바 트리가 달라져서, instant 가 그 교체를 화면 안에서
   그대로 보여주면 메뉴가 통째로 요동친다.

   그런데 instant 를 끄면 클릭 한 번이 온전한 왕복이 된다. 실측으로 중간
   크기 문서가 107KB(본문 25KB, 사이드바 39KB, 나머지 골격)라 GitHub Pages
   왕복이 그대로 체감된다.

   그래서 화면 교체 방식은 그대로 두고 **받아 오는 시점만** 앞당긴다.
   포인터가 링크 위에 머무는 순간 HTTP 캐시를 데워 두면, 200~400ms 뒤
   도착하는 클릭은 캐시에서 끝난다. instant 의 이득만 가져오고 요동은
   안 가져오는 셈이다.

   지키는 선:
   - 같은 출처의 문서 링크만. 앵커·다운로드·외부는 건너뛴다
   - 세션당 상한을 둔다. 이 사이트는 1,679쪽 176MB 라 상한이 없으면
     사이드바를 훑는 것만으로 남의 데이터를 태운다
   - Save-Data 나 2g/3g 면 아예 안 한다
   - 65ms 머문 뒤에 쏜다. 지나가는 커서까지 받으면 상한만 축낸다
   - Safari 는 <link rel=prefetch> 를 지원하지 않는다. 그쪽은 낮은
     우선순위 fetch 로 같은 캐시를 데운다 */
(function () {
  var LIMIT = 30;     // 세션당 최대 선반입 수
  var DWELL = 65;     // 이만큼 머물러야 쏜다 (ms)

  var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (conn && (conn.saveData || /^([23]g|slow-2g)$/.test(conn.effectiveType || ""))) return;

  var done = new Set();
  var timer = null;

  // rel=prefetch 를 실제로 지원하는가 (Safari 는 false)
  var supportsPrefetch = (function () {
    try {
      var l = document.createElement("link");
      return l.relList && l.relList.supports && l.relList.supports("prefetch");
    } catch (e) {
      return false;
    }
  })();

  function eligible(a) {
    if (!a || !a.href) return false;
    if (a.hasAttribute("download") || a.target === "_blank") return false;
    var u;
    try {
      u = new URL(a.href, location.href);
    } catch (e) {
      return false;
    }
    if (u.origin !== location.origin) return false;
    if (u.pathname === location.pathname) return false;   // 같은 쪽의 앵커
    if (/\.(png|jpe?g|gif|svg|webp|pdf|zip|mp4)$/i.test(u.pathname)) return false;
    return u.href.split("#")[0];
  }

  function warm(url) {
    if (done.size >= LIMIT || done.has(url)) return;
    done.add(url);
    if (supportsPrefetch) {
      var link = document.createElement("link");
      link.rel = "prefetch";
      link.href = url;
      link.as = "document";
      document.head.appendChild(link);
      return;
    }
    // Safari 경로. 응답을 쓰지 않고 버려도 HTTP 캐시에는 남는다.
    try {
      fetch(url, { credentials: "omit", mode: "same-origin", priority: "low" })
        .then(function (r) { return r && r.body && r.body.cancel && r.body.cancel(); })
        .catch(function () {});
    } catch (e) {}
  }

  function onEnter(e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    var url = eligible(a);
    if (!url) return;
    clearTimeout(timer);
    timer = setTimeout(function () { warm(url); }, DWELL);
  }

  function onLeave() {
    clearTimeout(timer);
  }

  // 터치는 머무는 시간이 없다. 손가락이 닿는 순간 바로 쏜다 —
  // 화면에서 손을 떼기까지 보통 100ms 는 벌 수 있다.
  function onTouch(e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    var url = eligible(a);
    if (url) warm(url);
  }

  document.addEventListener("mouseover", onEnter, { passive: true });
  document.addEventListener("mouseout", onLeave, { passive: true });
  document.addEventListener("touchstart", onTouch, { passive: true });
})();
