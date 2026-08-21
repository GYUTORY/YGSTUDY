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

  /* 다이어그램에 이름과 관계 설명을 준다.
   *
   * 왜: SVG 941개가 role="graphics-document" 인데 이름이 없다. 게다가 안쪽은
   * subgraph 제목 -> 엣지 라벨 -> 노드 라벨 순으로, 각 무리가 소스와 역순으로
   * 읽힌다. 시간 흐름 다이어그램이 2020 -> 1990 으로 거꾸로 읽히는 식이다.
   * "무엇에서 무엇으로" 가 사라져 읽어도 뜻이 통하지 않는다.
   *
   * 소스는 우리가 파싱하지 않는다. mermaid 가 getDiagramFromText 로 파싱 결과를
   * 그대로 내준다 — 941개 전부 성공, 중앙 0.7ms. 정규식으로 흉내내면 체인 엣지
   * (A --> B --> C)와 <br/> 가 섞인 라벨에서 무너져 20.6% 밖에 못 읽는다.
   *
   * role="img" 만으로는 안쪽이 안 감춰진다 — Chromium 은 SVG 자식을 계속
   * 노출한다(실측 333노드 그대로). 자식에 aria-hidden 을 직접 건다.
   * 단 설명을 못 만들었으면 감추지 않는다. 감추면 정보가 사라진다.
   */
  function clean(v) {
    return String(v == null ? "" : v)
      .replace(/<br\s*\/?>/gi, " ").replace(/<[^>]+>/g, "")
      .replace(/\\n/g, " ").replace(/[─━]{2,}/g, " ")
      .replace(/\s+/g, " ").trim();
  }

  /* 다이어그램 하나당 한 번만 찾는다.
   *
   * 왜: 이름을 지을 때 "같은 제목 아래 몇 번째인가" 를 세느라 문서의 모든
   * 다이어그램에 대해 제목을 다시 찾는다. 17개짜리 문서면 17 x (1 + 17) = 306회고,
   * 그 안에서 h1~h6 훑기가 540회, headerlink 제거가 306회 돈다. 제목은 이 흐름에서
   * 바뀌지 않으므로 노드마다 한 번 찾아 두면 그만이다.
   *
   * 키가 DOM 노드라 WeakMap 이면 충분하다 — instant navigation 으로 문서가 갈리면
   * 노드가 통째로 새것이라 캐시가 저절로 비고, 옛 노드는 같이 회수된다.
   */
  var headingCache = new WeakMap();

  /** 다이어그램 바로 앞의 제목. 941개 전부 하나씩 있다(누락 0). */
  function nearestHeading(el) {
    if (headingCache.has(el)) return headingCache.get(el);
    var out = findHeading(el);
    headingCache.set(el, out);
    return out;
  }

  function findHeading(el) {
    var n = el, h = null;
    while (n && !h) {
      var prev = n.previousElementSibling;
      while (prev) {
        if (/^H[1-6]$/.test(prev.tagName)) { h = prev; break; }
        var q = prev.querySelectorAll && prev.querySelectorAll("h1,h2,h3,h4,h5,h6");
        if (q && q.length) { h = q[q.length - 1]; break; }
        prev = prev.previousElementSibling;
      }
      n = n.parentElement;
    }
    if (!h) return null;
    var c = h.cloneNode(true);
    c.querySelectorAll(".headerlink").forEach(function (x) { x.remove(); });
    return c.textContent.trim();
  }

  function relations(db) {
    var i, out = [];
    if (db.getVertices && db.getEdges) {                    // flowchart / graph 649
      var V = db.getVertices(), E = db.getEdges();
      var L = function (id) { return clean((V[id] && V[id].text) || id); };
      for (i = 0; i < E.length; i++)
        out.push(L(E[i].start) + " → " + L(E[i].end) + (E[i].text ? " (" + clean(E[i].text) + ")" : ""));
      if (!out.length) for (var k in V) out.push(L(k));     // 관계 없는 나열형
    } else if (db.getActors && db.getMessages) {            // sequence 227
      var A = db.getActors(), M = db.getMessages();
      var LA = function (id) { return clean((A[id] && (A[id].description || A[id].name)) || id); };
      for (i = 0; i < M.length; i++) if (M[i].from && M[i].to)
        out.push(LA(M[i].from) + " → " + LA(M[i].to) + (M[i].message ? " (" + clean(M[i].message) + ")" : ""));
    } else if (db.getRootDocV2 || db.getRootDoc) {          // state 12
      // getStates() 는 렌더 중에 채워져 파싱 시점엔 비어 있다. 원문서를 훑는다.
      var doc = (db.getRootDocV2 && db.getRootDocV2()) || db.getRootDoc();
      (function walk(list) {
        (list || []).forEach(function (st) {
          if (st.stmt === "relation") out.push(
            stateName(st.state1) + " → " + stateName(st.state2) +
            (st.description ? " (" + clean(st.description) + ")" : ""));
          if (st.doc) walk(st.doc);
          if (st.state1 && st.state1.doc) walk(st.state1.doc);
          if (st.state2 && st.state2.doc) walk(st.state2.doc);
        });
      })(doc.doc || doc);
    } else if (db.getRelations && db.getClasses) {          // class 6
      var R = db.getRelations();
      for (i = 0; i < R.length; i++) out.push(clean(R[i].id1) + " → " + clean(R[i].id2));
    } else if (db.getSections && db.getShowData !== undefined) {   // pie 3
      var P = db.getSections();
      for (var key in P) out.push(clean(key) + ": " + P[key]);
    } else if (db.getTasks) {                               // gantt 5 / timeline 2
      var T = db.getTasks();
      for (i = 0; i < T.length; i++)
        out.push(clean(T[i].task) + (T[i].events ? ": " + T[i].events.map(clean).join(", ") : ""));
    } else if (db.getMindmap) {                             // mindmap 11 (계층은 평평해진다)
      (function w(nd) { if (!nd) return; out.push(clean(nd.descr || nd.nodeId)); (nd.children || []).forEach(w); })(db.getMindmap());
    } else if (db.getBlocksFlat) {                          // block 9
      db.getBlocksFlat().forEach(function (bk) { if (bk.label) out.push(clean(bk.label)); });
    } else if (db.getDrawableElem) {                        // xychart 16
      db.getDrawableElem().forEach(function (g) { (g.data || []).forEach(function (d) { if (d.text) out.push(clean(d.text)); }); });
    } else if (db.getQuadrantData) {                        // quadrant 1
      (db.getQuadrantData().points || []).forEach(function (pt) { out.push(clean(pt.text && pt.text.text)); });
    }
    return out.filter(Boolean);
  }

  /** mermaid 가 [*] 에 붙이는 내부 id 를 사람이 읽는 말로 바꾼다. */
  function stateName(st) {
    var v = clean((st && (st.description || st.id)) || "");
    if (v === "root_start") return "시작";
    if (v === "root_end") return "끝";
    return v;
  }

  /* 배경색만 지정된 노드의 글자색을 배경 휘도에 맞춰 정한다.
   *
   * 왜: 문서 85개가 `style A fill:#e0f2fe` 처럼 배경만 주고 글자색을 안 준다(623줄).
   * 글자색은 테마가 정하는데 다크는 #ccc, 라이트는 #333 로 고정이다. 그래서 다크에서는
   * 밝은 배경(#e0f2fe) 위에 밝은 글자가, 라이트에서는 어두운 배경(#1a1a2e) 위에
   * 어두운 글자가 얹힌다. 양쪽 다 안 읽힌다.
   *
   * 문서 623줄을 고치는 대신 렌더가 끝난 뒤 배경을 실제로 읽어 검정/흰색 중
   * 대비가 큰 쪽을 준다. 어떤 불투명 배경이든 최소 4.58:1 이 나온다 — 검정과 흰색의
   * 대비가 같아지는 중간 휘도(0.179)가 최악이고 그때가 4.58:1 이다.
   *
   * 이미 4.5:1 이 나오는 것은 건드리지 않는다. 배경을 안 준 노드(테마가 맞춰 둔 것)와
   * 저자가 `color:` 를 직접 준 노드가 이 검사에서 그대로 통과해 빠진다.
   */
  var CONTRAST_MIN = 4.5;
  var SHAPE_SEL = "rect,circle,ellipse,polygon,path";
  var LABEL_SEL = ".nodeLabel,.cluster-label span,.cluster-label p,.cluster-label text";

  /** "#abc" / "#aabbcc" / "rgb()" / "rgba()" -> [r,g,b]. 반투명·none 은 판단하지 않는다. */
  function parseColor(v) {
    if (!v) return null;
    var s = String(v).trim().toLowerCase();
    if (s === "none" || s === "transparent") return null;
    var m = s.match(/^#([0-9a-f]+)$/);
    if (m) {
      var h = m[1];
      if (h.length === 3 || h.length === 4) {
        h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2] + (h.length === 4 ? h[3] + h[3] : "");
      }
      if (h.length !== 6 && h.length !== 8) return null;
      if (h.length === 8 && parseInt(h.slice(6), 16) < 255) return null;
      return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
    }
    m = s.match(/^rgba?\(([^)]+)\)$/);
    if (!m) return null;
    var p = m[1].split(/[,\s/]+/).filter(Boolean).map(parseFloat);
    if (p.length < 3 || p.slice(0, 3).some(isNaN)) return null;
    if (p.length > 3 && p[3] < 1) return null;
    return [p[0], p[1], p[2]];
  }

  /** WCAG 2.x 상대 휘도. */
  function relLuminance(rgb) {
    var c = rgb.map(function (v) {
      var x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }

  function contrastRatio(a, b) {
    var la = relLuminance(a), lb = relLuminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }

  /** 배경 위에서 대비가 더 큰 쪽. */
  function pickTextColor(bg) {
    return contrastRatio(bg, [0, 0, 0]) >= contrastRatio(bg, [255, 255, 255]) ? "#000000" : "#ffffff";
  }

  function fixContrast(node) {
    if (typeof window.getComputedStyle !== "function") return;
    var svg = node.querySelector("svg");
    if (!svg) return;
    var groups = svg.querySelectorAll("g.node,g.cluster");
    var jobs = [], i, j;

    // 읽기를 먼저 다 하고 쓰기를 몰아서 한다. 번갈아 하면 노드마다 스타일이 다시 계산된다.
    for (i = 0; i < groups.length; i++) {
      var shape = groups[i].querySelector(SHAPE_SEL);
      if (!shape) continue;
      var bg = parseColor(window.getComputedStyle(shape).fill);
      if (!bg) continue;
      var labels = groups[i].querySelectorAll(LABEL_SEL);
      for (j = 0; j < labels.length; j++) {
        var lb = labels[j];
        var cur = parseColor(window.getComputedStyle(lb).color);
        if (cur && contrastRatio(bg, cur) >= CONTRAST_MIN) continue;
        jobs.push([lb, pickTextColor(bg)]);
      }
    }
    for (i = 0; i < jobs.length; i++) {
      jobs[i][0].style.color = jobs[i][1];
      jobs[i][0].style.fill = jobs[i][1]; // <text> 라벨은 fill 이 글자색이다
    }
  }

  function describe(mermaid, node, src) {
    if (!mermaid.mermaidAPI || !mermaid.mermaidAPI.getDiagramFromText) return;
    return mermaid.mermaidAPI.getDiagramFromText(src).then(function (d) {
      var db = d.db, svg = node.querySelector("svg");
      if (!svg || !db) return;

      // 이름: 소스에 title 이 있으면 그것(25개), 없으면 바로 앞 제목
      var name = clean((db.getDiagramTitle && db.getDiagramTitle()) ||
                       (db.getAccTitle && db.getAccTitle()) || "");
      if (!name) {
        var h = nearestHeading(node);
        if (h) {
          // 순번은 카운터로 세지 않는다. 재렌더가 일어나면 같은 다이어그램이
          // 두 번 세어져 "(2번째)" 가 붙는다. 문서 순서로 그때그때 계산하면
          // 몇 번을 다시 그려도 같은 값이 나온다.
          var all = [].slice.call(document.querySelectorAll("div.yg-mermaid"));
          var same = all.filter(function (el) { return nearestHeading(el) === h; });
          var idx = same.indexOf(node) + 1;
          name = h + (same.length > 1 ? " (" + idx + "번째)" : "") + " 다이어그램";
        } else {
          name = "다이어그램";
        }
      }
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", name);

      var rel = relations(db);
      if (!rel.length) return;   // 설명을 못 만들었으면 안쪽을 감추지 않는다

      var descId = (svg.id || "mmd") + "-desc";
      var prev = node.querySelector(".yg-mermaid-desc");
      if (prev) prev.remove();   // 다시 그렸으면 이전 설명을 갈아끼운다
      var box = document.createElement("div");
      box.id = descId;
      box.className = "yg-mermaid-desc";
      // 트리에 두 번 싣지 않는다. aria-describedby 가 직접 가리키는 요소는
      // aria-hidden 이어도 설명 계산에 그대로 쓰인다(accname 규격). 이게 없으면
      // 같은 문장이 그림의 설명으로 한 번, 본문 텍스트로 또 한 번 올라간다.
      box.setAttribute("aria-hidden", "true");
      box.textContent = rel.join(". ") + ".";
      node.appendChild(box);
      svg.setAttribute("aria-describedby", descId);
      for (var i = 0; i < svg.children.length; i++) svg.children[i].setAttribute("aria-hidden", "true");
    })["catch"](function () { /* 파싱 실패 시 지금 상태 그대로 둔다 */ });
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
          fixContrast(node);
          return describe(mermaid, node, src);
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
      var old = div.querySelector(".yg-mermaid-desc");
      if (old) old.remove();
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
