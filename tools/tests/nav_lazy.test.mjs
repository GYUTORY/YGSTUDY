/* 사이드바 지연 펼침 회귀 테스트.

   왜 두는가: `navigation.prune` 때문에 현재 경로 밖 섹션은 자식이 렌더되지
   않는데 화살표는 남는다. 눌러도 안 열리는 상태로 한참 굴러갔다. 지금은
   nav.json 을 받아 그 자리에서 그리는데, 이게 깨져도 페이지는 멀쩡해 보인다
   — 화살표가 그대로 있고 눌렀을 때만 아무 일이 없다. 눈으로는 못 잡는다.

   브라우저를 쓸 수 없어서 jsdom 으로 실제 빌드 산출물에 스크립트를 얹는다.
   레이아웃은 없으므로 "무엇이 그려졌나"가 아니라 "무엇이 DOM 에 생겼나"와
   "scrollTop 에 무엇을 썼나"를 본다.

   실행:
     npm i jsdom            # 이 테스트에만 필요하다. verify.sh 에는 안 넣는다.
     node tools/tests/nav_lazy.test.mjs <빌드디렉터리>

   빌드 디렉터리를 안 주면 site/ 를 쓴다.
*/
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SITE = path.resolve(process.argv[2] || path.join(ROOT, "site"));
const ORIGIN = "https://gyutory.github.io/YGSTUDY/";

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = await import("jsdom"));
} catch {
  console.log("SKIP  jsdom 이 없다 — `npm i jsdom` 후 다시 돌린다");
  process.exit(0);
}

if (!fs.existsSync(path.join(SITE, "nav.json"))) {
  console.log(`SKIP  ${SITE}/nav.json 이 없다 — 먼저 mkdocs build 를 돌린다`);
  process.exit(0);
}

const EXTRA = fs.readFileSync(path.join(ROOT, "Develop/javascripts/extra.js"), "utf8");

function pageFor(rel) {
  const html = fs.readFileSync(path.join(SITE, rel, "index.html"), "utf8");
  const dom = new JSDOM(html, {
    url: ORIGIN + rel + "/",
    virtualConsole: new VirtualConsole(),
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  dom.window.fetch = async (href) => {
    const p = path.join(SITE, href.replace(ORIGIN, ""));
    if (!fs.existsSync(p)) return { ok: false, json: async () => null };
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(p, "utf8")) };
  };
  return dom.window;
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const check = (ok, msg, extra) => {
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}${extra ? "  — " + extra : ""}`);
};

// 어떤 페이지를 볼지: 섹션이 서로 다른 곳을 몇 개 고른다
const PAGES = ["AI/Claude/Claude", "Framework/Node/NestJS/Nest_JS_Guards", "DataBase/RDBMS/Valid_Time"]
  .filter((p) => fs.existsSync(path.join(SITE, p, "index.html")));

if (!PAGES.length) {
  console.log("SKIP  검사할 페이지를 못 찾았다 (문서가 옮겨졌는지 확인)");
  process.exit(0);
}

for (const rel of PAGES) {
  console.log(`\n${rel}`);
  const w = pageFor(rel);
  let fetches = 0;
  const realFetch = w.fetch;
  w.fetch = async (h) => { fetches++; return realFetch(h); };

  w.eval(EXTRA);
  w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
  await wait(40);

  const side = w.document.querySelector(".md-sidebar--primary");
  const items = [...side.querySelectorAll("li[data-yg-lazy]")];
  check(items.length > 0, `잘린 가지를 펼침 가능으로 바꿈 (${items.length}개)`);

  // 화살표가 링크 밖으로 나왔는가 — 안 그러면 화살표를 눌러도 페이지가 이동한다
  const stuck = side.querySelectorAll("li[data-yg-lazy] > .md-nav__container > a > .md-nav__icon").length;
  check(stuck === 0, "화살표가 링크 안에 남아 있지 않음", stuck ? `${stuck}개 남음` : "");

  // 전부 펼쳐 본다
  let empty = 0;
  for (const li of items) {
    li.querySelector(":scope > .md-nav__container > label").click();
    await wait(25);
    const sub = li.querySelector(":scope > nav.md-nav");
    if (!sub || sub.querySelectorAll(":scope > ul > li").length === 0) empty++;
  }
  check(empty === 0, `모든 가지가 자식을 그림`, empty ? `${empty}개가 빈 채로 남음` : "");
  check(fetches === 1, `요청은 nav.json 한 번뿐`, `실제 ${fetches}회`);

  const ids = [...side.querySelectorAll(".md-nav__toggle[id]")].map((i) => i.id);
  check(ids.length === new Set(ids).size, "토글 id 가 페이지 안에서 유일함");
}

// 펼침 클릭이 사이드바 스크롤을 되돌리지 않는가 (되돌리면 목록이 위로 튄다)
{
  console.log("\n스크롤 튐");
  const w = pageFor(PAGES[0]);
  w.eval(EXTRA);
  w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
  await wait(40);

  const sb = w.document.querySelector(".md-sidebar__scrollwrap");
  let writes = [];
  let val = 0;
  Object.defineProperty(sb, "scrollTop", {
    configurable: true,
    get: () => val,
    set: (v) => { writes.push(v); val = v; },
  });

  const li = w.document.querySelector(".md-sidebar--primary li[data-yg-lazy]");
  writes = [];
  li.querySelector(":scope > .md-nav__container > label")
    .dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await wait(220);
  check(writes.length === 0, "펼침 클릭은 스크롤을 건드리지 않음", writes.length ? JSON.stringify(writes) : "");

  const a = w.document.querySelector(".md-sidebar--primary li.md-nav__item:not([data-yg-lazy]) > a.md-nav__link");
  if (a) {
    writes = [];
    a.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    await wait(220);
    check(writes.length > 0, "이동하는 링크에서는 복원이 계속 동작함");
  }
}

// 진행바가 스크롤마다 문서 높이를 다시 재지 않는가 (재면 매번 레이아웃이 강제된다)
{
  console.log("\n진행바");
  const w = pageFor(PAGES[0]);
  let reads = 0;
  const de = w.document.documentElement;
  for (const prop of ["scrollHeight", "clientHeight"]) {
    const orig = Object.getOwnPropertyDescriptor(w.Element.prototype, prop);
    Object.defineProperty(de, prop, {
      configurable: true,
      get() { reads++; return orig ? orig.get.call(this) : 0; },
    });
  }
  w.eval(EXTRA);
  w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
  await wait(40);

  const base = reads;
  for (let i = 0; i < 60; i++) w.dispatchEvent(new w.Event("scroll"));
  await wait(60);
  const per = reads - base;
  check(per <= 2, `스크롤 60회에 문서 높이 읽기 ${per}회`, per > 2 ? "핸들러 안에서 읽고 있다" : "");
}

console.log(`\n${failures === 0 ? "전부 통과" : "실패 " + failures + "건"}`);
process.exit(failures ? 1 : 0);
