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
  });
})();
