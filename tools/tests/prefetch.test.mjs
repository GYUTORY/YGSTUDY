/* 링크 선반입(hover prefetch) 회귀 테스트.

   왜 두는가: 이 기능은 **잘 돌아갈 때 아무 표시도 남기지 않는다.** 페이지는
   어차피 열리고, 콘솔도 조용하다. 그래서 통째로 죽어 있어도 화면만 봐서는
   알 방법이 없다. 반대로 폭주해도 마찬가지다 — 사이드바를 한 번 훑는 것만으로
   1,679쪽짜리 사이트를 긁어 대도 사용자 화면은 멀쩡하다.

   양쪽 다 조용한 실패라서, 확인은 코드가 자기 출력을 검사하는 수밖에 없다.

   보는 것:
     (1) 손이 닿으면 실제로 받아 오는가          — 안 되면 기능이 없는 것과 같다
     (2) 남의 출처는 안 건드리는가                — 방문 이력이 새 나간다
     (3) 같은 쪽 앵커는 건너뛰는가                — 지금 보는 문서를 또 받는다
     (4) 세션 상한이 지켜지는가                   — 남의 데이터를 태운다
     (5) 스쳐 지나간 커서는 무시하는가            — 상한을 헛되이 축낸다
     (6) Save-Data / 2g 면 아예 안 도는가         — 종량제 회선에서 재앙
     (7) Safari(rel=prefetch 미지원)도 데워지는가 — 지원 검사만 하고 손 놓으면
                                                    Safari 사용자에게는 없는 기능

   실행:
     npm i jsdom
     node tools/tests/prefetch.test.mjs
*/
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SRC_PATH = path.join(ROOT, "Develop", "javascripts", "extra.js");

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = await import("jsdom"));
} catch {
  console.log("SKIP  jsdom 이 없다 — `npm i jsdom` 후 다시 돌린다");
  process.exit(0);
}

const FULL = fs.readFileSync(SRC_PATH, "utf8");
const MARK = "링크에 손이 닿으면 미리 받아 둔다";
const at = FULL.indexOf(MARK);
if (at === -1) {
  console.log("  FAIL  extra.js 에서 선반입 블록을 못 찾았다");
  process.exit(1);
}
const SRC = FULL.slice(FULL.lastIndexOf("/*", at));

let fail = 0;
const check = (ok, msg, extra) => {
  if (!ok) fail++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}${extra ? "  — " + extra : ""}`);
};

const ORIGIN = "https://gyutory.github.io";
const HERE = ORIGIN + "/YGSTUDY/Architecture/MSA/";

/* 한 판을 차린다. conn 으로 회선 상태를, prefetchOK 로 Safari 여부를 흉내낸다. */
function setup({ conn = null, prefetchOK = true, links = [] } = {}) {
  const html =
    "<body><nav class='md-sidebar--primary'>" +
    links.map((h, i) => `<a class="md-nav__link" href="${h}">항목 ${i}</a>`).join("") +
    "</nav></body>";

  const dom = new JSDOM(html, {
    url: HERE,
    virtualConsole: new VirtualConsole(),
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const w = dom.window;

  // relList.supports 를 갈아 끼워 Safari 를 만든다
  const origSupports = w.DOMTokenList.prototype.supports;
  w.DOMTokenList.prototype.supports = function (t) {
    if (t === "prefetch") return prefetchOK;
    return origSupports ? origSupports.call(this, t) : false;
  };

  Object.defineProperty(w.navigator, "connection", { value: conn, configurable: true });

  // 실제로 나간 것만 센다
  const fetched = [];
  w.fetch = (u) => {
    fetched.push(String(u));
    return Promise.resolve({ body: null });
  };

  w.eval(SRC);

  const prefetched = () =>
    [...w.document.head.querySelectorAll('link[rel="prefetch"]')].map((l) => l.href);

  const hover = (el, { leave = false } = {}) => {
    el.dispatchEvent(new w.MouseEvent("mouseover", { bubbles: true }));
    if (leave) el.dispatchEvent(new w.MouseEvent("mouseout", { bubbles: true }));
  };

  const a = (i) => w.document.querySelectorAll("a")[i];
  const settle = () => new Promise((r) => setTimeout(r, 140)); // DWELL(65) 보다 넉넉히

  return { w, a, hover, settle, prefetched, fetched, warmed: () => prefetched().concat(fetched) };
}

/* (1) 기본 — 손이 닿으면 받아 온다 */
{
  const t = setup({ links: ["/YGSTUDY/Cloud/GCP/index.html"] });
  t.hover(t.a(0));
  await t.settle();
  check(t.warmed().length === 1, "링크 위에 머물면 선반입한다", `나간 것 ${t.warmed().length}건`);
}

/* (2) 남의 출처 — 방문 이력을 흘리지 않는다 */
{
  const t = setup({ links: ["https://example.com/tracker"] });
  t.hover(t.a(0));
  await t.settle();
  check(t.warmed().length === 0, "다른 출처는 선반입하지 않는다", t.warmed().join(","));
}

/* (3) 지금 보고 있는 쪽 — 또 받을 이유가 없다 */
{
  const t = setup({ links: [HERE + "#section"] });
  t.hover(t.a(0));
  await t.settle();
  check(t.warmed().length === 0, "같은 문서의 앵커는 건너뛴다", t.warmed().join(","));
}

/* (4) 상한 — 사이드바를 훑는 것만으로 사이트를 긁으면 안 된다 */
{
  const many = Array.from({ length: 45 }, (_, i) => `/YGSTUDY/p${i}/`);
  const t = setup({ links: many });
  for (let i = 0; i < many.length; i++) {
    t.hover(t.a(i));
    await t.settle();
  }
  const n = t.warmed().length;
  check(n === 30, "세션 상한 30건에서 멈춘다", `실제 ${n}건`);
}

/* (5) 스쳐 지나간 커서 — 머물지 않았으면 쏘지 않는다 */
{
  const t = setup({ links: ["/YGSTUDY/Cloud/GCP/index.html"] });
  t.hover(t.a(0), { leave: true });
  await t.settle();
  check(t.warmed().length === 0, "머물지 않고 지나가면 쏘지 않는다", t.warmed().join(","));
}

/* (6) 종량제 회선 — 아예 돌지 않아야 한다 */
for (const [name, conn] of [
  ["Save-Data", { saveData: true, effectiveType: "4g" }],
  ["2g", { saveData: false, effectiveType: "2g" }],
  ["느린 2g", { saveData: false, effectiveType: "slow-2g" }],
]) {
  const t = setup({ conn, links: ["/YGSTUDY/Cloud/GCP/index.html"] });
  t.hover(t.a(0));
  await t.settle();
  check(t.warmed().length === 0, `${name} 회선에서는 선반입하지 않는다`, t.warmed().join(","));
}

/* (7) Safari — rel=prefetch 가 없어도 캐시는 데워야 한다 */
{
  const t = setup({ prefetchOK: false, links: ["/YGSTUDY/Cloud/GCP/index.html"] });
  t.hover(t.a(0));
  await t.settle();
  check(
    t.prefetched().length === 0 && t.fetched.length === 1,
    "rel=prefetch 미지원 브라우저는 fetch 로 대체한다",
    `link ${t.prefetched().length} / fetch ${t.fetched.length}`
  );
}

/* (8) 터치 — 머무는 시간이 없으니 닿는 즉시 */
{
  const t = setup({ links: ["/YGSTUDY/Cloud/GCP/index.html"] });
  const el = t.a(0);
  el.dispatchEvent(new t.w.Event("touchstart", { bubbles: true }));
  check(t.warmed().length === 1, "터치는 대기 없이 바로 선반입한다", `${t.warmed().length}건`);
}

console.log(`\n${fail === 0 ? "전부 통과" : "실패 " + fail + "건"}`);
process.exit(fail ? 1 : 0);
