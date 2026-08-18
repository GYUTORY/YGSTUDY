/*
 * 머메이드 렌더링을 우리가 직접 제어한다.
 *
 * 왜: Material 번들은 `pre.mermaid` 를 발견하면 CDN 에서 mermaid 최신본을 끌어와
 * 렌더한다. 그 버전이 올라가면서 궁합이 깨졌고, 결과적으로 938개 다이어그램이
 * 전부 빈 상자로 나갔다. 남의 CDN 최신 태그에 렌더링을 맡기면 언제 또 깨질지
 * 알 수 없으므로 버전을 고정해서 우리가 초기화한다.
 *
 * 대상 마크업은 superfences 가 만드는 `<pre class="mermaid-diagram"><code>...</code></pre>` 다.
 * 클래스가 `mermaid` 가 아닌 이유: Material 번들이 그 이름을 먼저 낚아채 pre 를 빈 div 로
 * 바꿔버려 소스가 증발한다. 실제로 그것이 다이어그램 938개가 빈 상자였던 원인이다.
 * 렌더 결과도 `.yg-mermaid` 로 둔다 — instant navigation 에서 Material 이 다시 훑을 때
 * `.mermaid` 였다면 또 지워질 수 있다.
 */
(function () {
  "use strict";

  var MERMAID_VERSION = "10.9.3"; // 고정. 올릴 때는 반드시 브라우저에서 확인하고 올린다.
  var SRC = "https://cdn.jsdelivr.net/npm/mermaid@" + MERMAID_VERSION + "/dist/mermaid.esm.min.mjs";

  var loading = null;
  var initialized = false; // mermaid.initialize 는 한 번만
  var seq = 0; // 렌더 id 일련번호 (배치가 나뉘어도 충돌 없게)
  var queue = []; // 그릴 순서 (전역 단일 큐)
  var draining = false; // 큐 처리 중 여부 — 동시 렌더 금지

  function isDark() {
    var el = document.body;
    return el && el.getAttribute("data-md-color-scheme") === "slate";
  }

  /** pre.mermaid > code 를 div.mermaid 로 정규화하고, 원본 소스를 보관한다. */
  function collect() {
    var nodes = [];
    document.querySelectorAll("pre.mermaid-diagram").forEach(function (pre) {
      var code = pre.querySelector("code");
      var src = (code ? code.textContent : pre.textContent) || "";
      if (!src.trim()) return;
      var div = document.createElement("div");
      div.className = "yg-mermaid";
      div.setAttribute("data-mermaid-src", src);
      div.textContent = src;
      pre.replaceWith(div);
      nodes.push(div);
    });
    // 이미 div 형태로 존재하고 아직 렌더되지 않은 것도 포함
    document.querySelectorAll("div.yg-mermaid:not([data-mermaid-done])").forEach(function (div) {
      if (nodes.indexOf(div) !== -1) return;
      var src = div.getAttribute("data-mermaid-src") || div.textContent || "";
      if (!src.trim()) return;
      div.setAttribute("data-mermaid-src", src);
      nodes.push(div);
    });
    return nodes;
  }

  function load() {
    if (!loading) {
      loading = import(/* webpackIgnore: true */ SRC).then(function (mod) {
        return mod.default || mod;
      });
    }
    return loading;
  }

  /**
   * 화면에 들어오는 다이어그램만 그린다.
   *
   * 왜: 렌더는 메인 스레드를 잡는다. 다이어그램이 14개인 문서에서 전부 순차로 그리면
   * 롱태스크가 1초 넘게 쌓여 첫 스크롤이 끊긴다. 대부분은 접혀 있어 보이지도 않는다.
   * rootMargin 을 한 화면치 줘서 스크롤이 닿기 전에 미리 그린다.
   * IntersectionObserver 가 없으면 예전처럼 전부 그린다(동작 동일, 속도만 손해).
   */
  function renderWhenVisible(nodes) {
    if (typeof IntersectionObserver !== "function") return enqueue(nodes);
    var io = new IntersectionObserver(
      function (entries) {
        var due = [];
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          io.unobserve(e.target);
          due.push(e.target);
        });
        if (due.length) enqueue(due);
      },
      { rootMargin: "600px 0px" }
    );
    nodes.forEach(function (n) {
      io.observe(n);
    });
  }

  function render() {
    var nodes = collect();
    if (!nodes.length) return;
    renderWhenVisible(nodes);
  }

  /**
   * 전역 단일 큐.
   *
   * mermaid 10 은 렌더할 때 공용 DOM 샌드박스를 쓴다. 화면에 들어오는 대로 배치마다
   * 렌더 체인을 따로 만들면 그 체인들이 겹치면서 일부가 조용히 실패한다
   * (14개 중 10개만 그려지고 예외도 안 났다). 배치와 무관하게 한 줄로 세워서 그린다.
   */
  function enqueue(nodes) {
    for (var i = 0; i < nodes.length; i++) {
      if (queue.indexOf(nodes[i]) === -1) queue.push(nodes[i]);
    }
    pump();
  }

  function pump() {
    if (draining) return;
    var node = queue.shift();
    if (!node) return;
    draining = true;
    drawOne(node)["catch"](function () {})
      .then(function () {
        draining = false;
        pump();
      });
  }

  function drawOne(node) {
    var src = node.getAttribute("data-mermaid-src") || "";
    return load()
      .then(function (mermaid) {
        // 여러 번 불리므로 초기화는 한 번만 한다
        if (!initialized) {
          initialized = true;
          mermaid.initialize({
            startOnLoad: false,
            securityLevel: "loose",
            theme: isDark() ? "dark" : "default",
            flowchart: {
              htmlLabels: true,
              useMaxWidth: true,
              padding: 18,
              nodeSpacing: 55,
              rankSpacing: 65,
              wrappingWidth: 180,
            },
            sequence: { useMaxWidth: true },
            themeVariables: { fontSize: "11px" },
          });
        }
        // 배치가 나뉘어 그려지므로 인덱스 대신 전역 일련번호로 id 충돌을 막는다
        var id = "mmd-" + (seq++).toString(36) + "-" + Date.now().toString(36);
        return mermaid.render(id, src).then(function (out) {
          node.innerHTML = out.svg;
          node.setAttribute("data-mermaid-done", "1");
          if (typeof out.bindFunctions === "function") out.bindFunctions(node);
        });
      })
      ["catch"](function (err) {
        // 숨기지 않는다. 깨진 건 보이게 두고 원본 소스를 남긴다.
        node.setAttribute("data-mermaid-done", "error");
        node.classList.add("mermaid-error");
        node.textContent =
          "다이어그램을 그리지 못했습니다: " + (err && err.message ? err.message : err) + "\n\n" + src;
        if (window.console) console.error("[mermaid] render failed", err);
      });
  }

  /**
   * 테마를 바꾸면 그 페이지의 다이어그램을 다시 그린다.
   *
   * mermaid.initialize 를 한 번만 부르게 막아 둔 탓에 theme 값이 첫 렌더 시점에
   * 굳는다. 그래서 라이트로 들어와 다크로 토글하면 페이지 배경만 어두워지고
   * 다이어그램은 라이트 그대로 남았다 — 연결선 대비가 1.34:1 로 사실상 안 보였다.
   * 다른 문서로 이동하면 정상이라 "토글한 그 페이지" 에서만 나던 문제다.
   *
   * 이미 그린 것을 원본 소스로 되돌리고 큐를 비운 뒤 처음부터 다시 세운다.
   */
  var lastScheme = null;

  function redrawForTheme() {
    var scheme = document.body && document.body.getAttribute("data-md-color-scheme");
    if (scheme === lastScheme) return;
    lastScheme = scheme;
    if (!initialized) return; // 아직 한 번도 안 그렸으면 그냥 두면 된다

    initialized = false;
    queue.length = 0;
    draining = false;

    document.querySelectorAll("div.yg-mermaid[data-mermaid-done]").forEach(function (div) {
      var src = div.getAttribute("data-mermaid-src");
      if (!src) return;
      div.removeAttribute("data-mermaid-done");
      div.classList.remove("mermaid-error");
      div.textContent = src;
    });
    render();
  }

  if (typeof MutationObserver === "function" && document.body) {
    new MutationObserver(redrawForTheme).observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"],
    });
    lastScheme = document.body.getAttribute("data-md-color-scheme");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }

  // Material 의 instant navigation 은 페이지 전체를 다시 로드하지 않는다.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(render);
  }
})();
