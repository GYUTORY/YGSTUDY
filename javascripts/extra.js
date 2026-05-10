(function () {
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

    // ----- 홈 카테고리 카운트 (sitemap.xml 기반) -----
    var countTargets = document.querySelectorAll("[data-yg-count]");
    var totalTarget = document.querySelector("[data-yg-total]");
    if (!countTargets.length && !totalTarget) return;

    fetch("sitemap.xml", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (text) {
        if (!text) return;
        var xml = new DOMParser().parseFromString(text, "text/xml");
        var locs = xml.querySelectorAll("loc");
        if (!locs.length) return;

        // 사이트 베이스 경로 (예: /YGSTUDY/) 추정
        var basePath = window.location.pathname.replace(/[^\/]*$/, "");

        var counts = {};
        var total = 0;
        locs.forEach(function (node) {
          var href = (node.textContent || "").trim();
          if (!href) return;
          var path;
          try { path = new URL(href).pathname; } catch (e) { return; }
          if (basePath && path.indexOf(basePath) === 0) {
            path = path.slice(basePath.length);
          } else {
            path = path.replace(/^\/+/, "");
          }
          if (!path || path === "/" || path === "index.html") return;
          var seg = path.split("/")[0];
          if (!seg || seg === "tags") return;
          counts[seg] = (counts[seg] || 0) + 1;
          total += 1;
        });

        countTargets.forEach(function (el) {
          var key = el.getAttribute("data-yg-count");
          var n = counts[key] || 0;
          el.textContent = n > 0 ? n + "개" : "—";
        });
        if (totalTarget) totalTarget.textContent = total > 0 ? total : "—";
      })
      .catch(function () { /* 무시 — 초기 로딩 실패시 placeholder 유지 */ });
  });
})();
