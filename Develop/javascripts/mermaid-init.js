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

  function render() {
    var nodes = collect();
    if (!nodes.length) return;

    load()
      .then(function (mermaid) {
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
          themeVariables: { fontSize: "12px" },
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
