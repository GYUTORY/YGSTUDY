/* 페이지마다 나가던 GitHub 릴리스 요청 차단 회귀 테스트.

   왜 두는가: 이 저장소는 릴리스가 없어 그 조회가 매번 404 다. 그런데
   Material 은 페이지를 옮길 때마다 부른다. 인증 없는 GitHub API 는 IP 당
   시간 60회라, 문서를 30쪽만 넘겨도 한도가 차고 그때부터 헤더의 별·포크
   숫자까지 같이 죽는다.

   막는 코드가 extra.js 에 있었는데 **두 겹으로 안 먹고 있었다.**
     (1) `window.fetch` 만 가로챘는데 Material 은 XMLHttpRequest 를 쓴다
         (번들의 to() 가 `new XMLHttpRequest`)
     (2) extra.js 는 body 끝이라 Material 번들보다 뒤에 돈다
   둘 다 조용한 실패다 — 콘솔에 아무것도 안 남고 화면도 멀쩡하다.

   그래서 네 가지를 본다. 막아야 할 것을 막는가, 막으면 안 되는 것까지
   막지는 않는가, 검색 인덱스 보류는 그대로인가, 그리고 그 코드가
   번들보다 먼저 오는 자리에 있는가.

   실행:
     npm i jsdom
     node tools/tests/xhr_block.test.mjs <빌드디렉터리>
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
let fail = 0;
const check = (ok, msg, extra) => {
  if (!ok) fail++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}${extra ? "  — " + extra : ""}`);
};

/* 순서 검사부터. 번들보다 뒤에 있으면 무슨 코드를 넣든 늦는다. */
{
  const inlineAt = html.indexOf("releases/latest");
  const bundleAt = html.search(/<script[^>]*src="[^"]*bundle\.[^"]*\.js"/);
  check(
    inlineAt !== -1 && bundleAt !== -1 && inlineAt < bundleAt,
    "차단 코드가 Material 번들보다 앞에 있다",
    inlineAt === -1 ? "차단 코드를 못 찾음" : `차단 ${inlineAt} vs 번들 ${bundleAt}`
  );
}

const dom = new JSDOM(html, {
  url: ORIGIN + REL + "/",
  virtualConsole: new VirtualConsole(),
  runScripts: "outside-only",
  pretendToBeVisual: true,
});
const w = dom.window;

// 실제로 나가는 요청만 기록한다 (전송은 하지 않는다)
const sent = [];
const open = w.XMLHttpRequest.prototype.open;
w.XMLHttpRequest.prototype.open = function (m, u) {
  this.__u = u;
  return open.apply(this, arguments);
};
w.XMLHttpRequest.prototype.send = function () {
  sent.push(this.__u);
};

const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((s) => s.includes("releases/latest"));
if (!inline) {
  console.log("  FAIL  빌드 결과에서 차단 스크립트를 못 찾았다");
  process.exit(1);
}
w.eval(inline);

let aborted = 0;
const ask = (u) => {
  const x = new w.XMLHttpRequest();
  x.addEventListener("abort", () => aborted++);
  x.open("GET", u);
  x.send();
};

ask("https://api.github.com/repos/gyutory/YGSTUDY/releases/latest");
ask("https://api.github.com/repos/gyutory/YGSTUDY");
ask(ORIGIN + "search/search_index.json");

const went = (frag) => sent.some((u) => u.includes(frag));

check(!went("releases/latest"), "릴리스 조회는 나가지 않는다");
check(aborted >= 1, "막힌 요청은 abort 로 완료 처리된다 (에러로 끝내면 콘솔이 빨개진다)");
check(went("/repos/gyutory/YGSTUDY") && !went("releases"),
  "저장소 정보는 그대로 나간다 (헤더의 별·포크 숫자가 이걸 쓴다)");
check(!went("search_index.json"),
  "검색 인덱스는 여전히 보류된다 (검색창을 건드릴 때까지)");

console.log(`\n  실제로 나간 요청: ${sent.map((u) => u.replace("https://", "")).join(", ") || "없음"}`);
console.log(`\n${fail === 0 ? "전부 통과" : "실패 " + fail + "건"}`);
process.exit(fail ? 1 : 0);
