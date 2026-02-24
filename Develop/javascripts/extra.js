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
    if (!sb) return;

    // 사용자가 직접 스크롤한 경우에만 위치 저장
    sb.addEventListener("wheel", function () { pos = sb.scrollTop; }, { passive: true });
    sb.addEventListener("touchmove", function () { pos = sb.scrollTop; }, { passive: true });

    // 메뉴 클릭 시 스크롤 위치를 반복적으로 강제 복원
    document.addEventListener("click", function (e) {
      if (!e.target.closest || !e.target.closest(".md-nav")) return;
      var p = pos;
      [0, 10, 30, 60, 100, 200, 400].forEach(function (t) {
        setTimeout(function () { sb.scrollTop = p; }, t);
      });
    });
  });
})();
