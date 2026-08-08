/*
 * 머메이드 렌더링을 우리가 직접 제어한다.
 *
 * 왜: Material 번들은 `pre.mermaid` 를 발견하면 CDN 에서 mermaid 최신본을 끌어와
 * 렌더한다. 그 버전이 올라가면서 궁합이 깨졌고, 결과적으로 938개 다이어그램이
 * 전부 빈 상자로 나갔다. 남의 CDN 최신 태그에 렌더링을 맡기면 언제 또 깨질지
 * 알 수 없으므로 버전을 고정해서 우리가 초기화한다.
 *
 * 대상 마크업은 superfences 가 만드는 `<pre class="mermaid"><code>...</code></pre>` 다.
 * mermaid 는 요소의 textContent 를 읽으므로, 렌더 전에 코드 텍스트만 남긴
 * `<div class="mermaid">` 로 바꿔준다.
 */
(function () {
  "use strict";

  var MERMAID_VERSION = "10.9.3"; // 고정. 올릴 때는 반드시 브라우저에서 확인하고 올린다.
  var SRC = "https://cdn.jsdelivr.net/npm/mermaid@" + MERMAID_VERSION + "/dist/mermaid.esm.min.mjs";

  var loading = null;

  function isDark() {
    var el = document.body;
    return el && el.getAttribute("data-md-color-scheme") === "slate";
  }

  /** pre.mermaid > code 를 div.mermaid 로 정규화하고, 원본 소스를 보관한다. */
  function collect() {
    var nodes = [];
    document.querySelectorAll("pre.mermaid").forEach(function (pre) {
      var code = pre.querySelector("code");
      var src = (code ? code.textContent : pre.textContent) || "";
      if (!src.trim()) return;
      var div = document.createElement("div");
      div.className = "mermaid";
      div.setAttribute("data-mermaid-src", src);
      div.textContent = src;
      pre.replaceWith(div);
      nodes.push(div);
    });
    // 이미 div 형태로 존재하고 아직 렌더되지 않은 것도 포함
    document.querySelectorAll("div.mermaid:not([data-mermaid-done])").forEach(function (div) {
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

  function render() {
    var nodes = collect();
    if (!nodes.length) return;

    load()
      .then(function (mermaid) {
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "loose",
          theme: isDark() ? "dark" : "default",
          flowchart: { htmlLabels: true, useMaxWidth: true },
          sequence: { useMaxWidth: true },
        });
        return nodes.reduce(function (chain, node, i) {
          return chain.then(function () {
            var src = node.getAttribute("data-mermaid-src") || "";
            var id = "mmd-" + Date.now().toString(36) + "-" + i;
            return mermaid
              .render(id, src)
              .then(function (out) {
                node.innerHTML = out.svg;
                node.setAttribute("data-mermaid-done", "1");
                if (typeof out.bindFunctions === "function") out.bindFunctions(node);
              })
              .catch(function (err) {
                // 숨기지 않는다. 깨진 건 보이게 두고 원본 소스를 남긴다.
                node.setAttribute("data-mermaid-done", "error");
                node.classList.add("mermaid-error");
                node.textContent =
                  "다이어그램을 그리지 못했습니다: " + (err && err.message ? err.message : err) + "\n\n" + src;
              });
          });
        }, Promise.resolve());
      })
      .catch(function (err) {
        // 라이브러리 자체를 못 불러온 경우 — 소스라도 읽을 수 있게 남긴다.
        nodes.forEach(function (node) {
          node.setAttribute("data-mermaid-done", "error");
          node.classList.add("mermaid-error");
          node.textContent =
            "다이어그램 라이브러리를 불러오지 못했습니다.\n\n" + (node.getAttribute("data-mermaid-src") || "");
        });
        if (window.console) console.error("[mermaid] load failed", err);
      });
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
