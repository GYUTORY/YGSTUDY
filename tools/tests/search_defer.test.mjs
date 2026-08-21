/* 검색 인덱스를 언제 받고 언제 안 받는지 회귀 테스트.

   왜 두는가: search_index.json 은 20MB(gzip 5.6MB)다. 파일은 브라우저가
   캐시하지만 lunr 색인은 캐시가 안 돼서, 페이지를 옮길 때마다 워커가 20MB를
   처음부터 다시 훑는다. 그게 메뉴 클릭이 굼뜨게 느껴지던 원인이었다.

   지금은 세션에 한 번만 미리 받고, 그 뒤로는 검색창을 건드릴 때만 받는다.
   이 규칙이 깨져도 화면은 멀쩡하다 — 느려질 뿐이라 눈으로 못 잡는다.

   실행:
     npm i jsdom
     node tools/tests/search_defer.test.mjs <빌드디렉터리>
*/
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SITE = path.resolve(process.argv[2] || path.join(ROOT, "site"));
const ORIGIN = "https://gyutory.github.io/YGSTUDY/";
const REL = "AI/Claude/Claude";

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = await import("jsdom"));
} catch {
  console.log("SKIP  jsdom 이 없다 — `npm i jsdom` 후 다시 돌린다");
  process.exit(0);
}

const page = path.join(SITE, REL, "index.html");
if (!fs.existsSync(page)) {
  console.log(`SKIP  ${page} 가 없다 — 먼저 mkdocs build 를 돌린다`);
  process.exit(0);
}

const html = fs.readFileSync(page, "utf8");
// head 안에 인라인으로 들어간 그 스크립트만 뽑는다
const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((s) => s.includes("search_index.json"));

if (!inline) {
  console.log("FAIL  빌드 결과에서 검색 지연 스크립트를 못 찾았다");
  process.exit(1);
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const check = (ok, msg, extra) => {
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}${extra ? "  — " + extra : ""}`);
};

/** 한 번의 페이지 로드를 흉내낸다. prefetched=true 면 이미 세션에서 받은 상태. */
async function load({ prefetched, settle = 400 }) {
  const dom = new JSDOM("<!doctype html><html><head></head><body></body></html>", {
    url: ORIGIN + REL + "/",
    virtualConsole: new VirtualConsole(),
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const w = dom.window;
  if (prefetched) w.sessionStorage.setItem("yg-search-prefetched", "1");

  // 인덱스 요청이 실제로 나갔는지만 센다
  const asked = [];
  w.fetch = async (u) => {
    asked.push(String(u));
    return { ok: true, json: async () => ({}), text: async () => "" };
  };

  w.eval(inline);
  // Material 번들이 하듯 인덱스를 요청한다 — 붙잡히면 asked 에 안 들어간다
  w.fetch(ORIGIN + "search/search_index.json");
  w.dispatchEvent(new w.Event("load"));
  // jsdom 에는 requestIdleCallback 이 없어 setTimeout(1500) 경로로 간다.
  // load 뒤 300ms + 1500ms 를 넘겨서 기다린다.
  await wait(settle);
  return { w, asked };
}

console.log("첫 페이지 (세션에서 아직 안 받음)");
{
  const { asked } = await load({ prefetched: false, settle: 2200 });
  check(
    asked.some((u) => u.includes("search_index.json")),
    "한가해지면 미리 받는다",
    asked.length ? "" : "요청이 안 나감"
  );
}

console.log("\n다음 페이지 (같은 세션)");
{
  const { w, asked } = await load({ prefetched: true });
  check(
    !asked.some((u) => u.includes("search_index.json")),
    "다시 받지 않는다 (색인을 또 만들지 않는다)",
    asked.length ? `요청 ${asked.length}건이 나감` : ""
  );

  // 그래도 검색을 열면 받아야 한다 — 안 그러면 검색이 영영 준비 안 된다
  const box = w.document.createElement("div");
  box.className = "md-search";
  const input = w.document.createElement("input");
  box.appendChild(input);
  w.document.body.appendChild(box);
  input.dispatchEvent(new w.FocusEvent("focusin", { bubbles: true }));
  await wait(60);
  check(
    asked.some((u) => u.includes("search_index.json")),
    "검색창을 건드리면 그때 받는다"
  );
}

console.log(`\n${failures === 0 ? "전부 통과" : "실패 " + failures + "건"}`);
process.exit(failures ? 1 : 0);
