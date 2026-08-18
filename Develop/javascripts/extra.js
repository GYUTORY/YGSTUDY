(function () {
  // GitHub releases API 호출 차단 — 릴리스가 없어 매 페이지 404 낭비
  var _fetch = window.fetch;
  window.fetch = function (url, opts) {
    if (typeof url === 'string' && url.indexOf('api.github.com') !== -1 && url.indexOf('/releases/latest') !== -1) {
      return Promise.resolve(new Response('null', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    return _fetch.apply(this, arguments);
  };

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
      // 사용자가 직접 스크롤한 경우에만 위치 저장
      sb.addEventListener("wheel", function () { pos = sb.scrollTop; }, { passive: true });
      sb.addEventListener("touchmove", function () { pos = sb.scrollTop; }, { passive: true });

      // MutationObserver: active 클래스 변화 감지 후 1회 정확히 복원
      var restoring = false;
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

      // 메뉴 클릭 fallback
      document.addEventListener("click", function (e) {
        if (!e.target.closest || !e.target.closest(".md-nav")) return;
        var p = pos;
        setTimeout(function () { sb.scrollTop = p; }, 100);
      });
    }

    // Reading Progress Bar
    var bar = document.createElement("div");
    bar.id = "reading-progress";
    document.body.appendChild(bar);

    function updateProgress() {
      var scrollTop = window.scrollY || document.documentElement.scrollTop;
      var docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      var progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = Math.min(progress, 100) + "%";
    }

    window.addEventListener("scroll", updateProgress, { passive: true });
    updateProgress();

    // ----- 사이드바 형제 메뉴 공통 prefix 자동 축약 -----
    function stripCommonPrefixes() {
      var listsTotal = 0;
      var stripsTotal = 0;
      var lists = document.querySelectorAll(".md-nav--primary .md-nav__list");
      lists.forEach(function (list) {
        listsTotal += 1;
        var items = [];
        for (var i = 0; i < list.children.length; i++) {
          var li = list.children[i];
          if (!li || li.tagName !== "LI") continue;
          // 직접 자식 중 a 또는 label 찾기 (input은 건너뜀)
          var link = null;
          for (var c = 0; c < li.children.length; c++) {
            var ch = li.children[c];
            if ((ch.tagName === "A" || ch.tagName === "LABEL") &&
                ch.classList && ch.classList.contains("md-nav__link")) {
              link = ch;
              break;
            }
          }
          if (!link || link.dataset.origLabel) continue;
          var span = link.querySelector(".md-ellipsis");
          if (!span) continue;
          var orig = (span.textContent || "").replace(/\s+/g, " ").trim();
          if (!orig) continue;
          items.push({ link: link, span: span, orig: orig });
        }
        if (items.length < 3) return;

        var splits = items.map(function (it) { return it.orig.split(" "); });
        var maxPrefix = Math.min.apply(null, splits.map(function (s) { return s.length; }));
        var commonCount = 0;
        for (var k = 0; k < maxPrefix; k++) {
          var first = splits[0][k];
          var allMatch = true;
          for (var s = 0; s < splits.length; s++) {
            if (splits[s][k] !== first) { allMatch = false; break; }
          }
          if (allMatch) commonCount = k + 1;
          else break;
        }
        if (commonCount < 1) return;
        var commonWords = splits[0].slice(0, commonCount).join(" ");
        if (commonWords.length < 4) return;

        var planned = items.map(function (it) {
          var stripped = it.orig.slice(commonWords.length).replace(/^[\s\-_·:|]+/, "").trim();
          return { it: it, stripped: stripped };
        });
        var meaningful = 0;
        for (var p = 0; p < planned.length; p++) {
          if (planned[p].stripped.length >= 2) meaningful += 1;
        }
        if (meaningful < 2) return;

        planned.forEach(function (p) {
          if (!p.stripped || p.stripped.length < 2) return;
          p.it.link.dataset.origLabel = p.it.orig;
          p.it.link.setAttribute("title", p.it.orig);
          p.it.span.textContent = p.stripped;
          stripsTotal += 1;
        });
      });
      document.body.setAttribute("data-yg-strip", listsTotal + "/" + stripsTotal);
    }
    // 즉시 실행 + 사이드바 변동 감지 시 재실행 (instant nav, 동적 토글 대응)
    stripCommonPrefixes();
    var sidebar = document.querySelector(".md-sidebar--primary");
    if (sidebar) {
      var moTimer = null;
      var mo = new MutationObserver(function () {
        clearTimeout(moTimer);
        moTimer = setTimeout(stripCommonPrefixes, 80);
      });
      mo.observe(sidebar, { childList: true, subtree: true });
    }

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
    if (document.querySelector(".md-skip")) return;
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
  function mark(code) {
    var wrap = code.parentElement && code.parentElement.parentElement;
    if (!wrap || !wrap.classList.contains("highlight")) return;
    var max = code.scrollWidth - code.clientWidth;
    if (max <= 4) {
      wrap.removeAttribute("data-yg-scroll");
      return;
    }
    var sides = [];
    if (code.scrollLeft > 2) sides.push("l");
    if (code.scrollLeft < max - 2) sides.push("r");
    wrap.setAttribute("data-yg-scroll", sides.join(" "));
  }

  function scanAll() {
    document.querySelectorAll(".md-typeset .highlight > pre > code").forEach(mark);
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

  function markScroll(box) {
    var max = box.scrollWidth - box.clientWidth;
    if (max <= 4) { box.removeAttribute("data-yg-scroll"); return; }
    var sides = [];
    if (box.scrollLeft > 2) sides.push("l");
    if (box.scrollLeft < max - 2) sides.push("r");
    box.setAttribute("data-yg-scroll", sides.join(" "));
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
    markScroll(box);
    return true;
  }

  function scan() {
    var pending = 0;
    document.querySelectorAll(".md-typeset .yg-mermaid").forEach(function (box) {
      if (!apply(box)) pending++;
    });
    // 표도 같은 처지다 — Material 이 overflow:auto 래퍼에 넣어 옆으로 굴리는데
    // 잘렸다는 표시가 없다(한 문서에서 표 6개 중 3개가 최대 220px 씩 숨었다).
    document.querySelectorAll(".md-typeset__table").forEach(markScroll);
    return pending;
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.querySelector(".md-typeset .yg-mermaid, .md-typeset__table")) return;
    scan();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(scan);
    window.addEventListener("load", scan);

    // mermaid 는 화면에 들어올 때 그린다. svg 가 꽂히는 것을 보고 그때 처리한다.
    var mo = new MutationObserver(function (list) {
      list.forEach(function (m) {
        var box = m.target.closest && m.target.closest(".yg-mermaid");
        if (box) apply(box);
      });
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

  function run() {
    nameToggles();
    unmarkCodeNav();
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
