/* 레이아웃 스래싱 회귀 테스트.

   왜 두는가: 화면에 뭐가 잘렸는지 표시하는 코드들이 요소마다 "재고 → 쓰고"
   를 번갈아 했다. 쓰면 레이아웃이 무효가 되므로 다음 요소를 잴 때 다시
   계산된다. 요소 수만큼 레이아웃이 반복된다. 이 저장소에서 가장 큰 문서는
   코드블록이 164개고, 그 스캔이 로드·폰트·load 로 세 번 돈다.

   화면 결과는 똑같아서 눈으로는 못 잡는다. 느려질 뿐이다.
   여기서는 "쓰기 뒤에 읽기가 몇 번 오는가" 를 센다 — 그게 강제 레이아웃 횟수다.

   실행:
     npm i jsdom
     node tools/tests/layout_thrash.test.mjs <빌드디렉터리>
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

// 코드블록이 가장 많은 문서를 고른다
function pickHeaviest() {
  let best = null;
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name === "index.html") {
        const n = (fs.readFileSync(p, "utf8").match(/class="highlight"/g) || []).length;
        if (!best || n > best.n) best = { p, n };
      }
    }
  };
  if (!fs.existsSync(SITE)) return null;
  walk(SITE);
  return best;
}

const target = pickHeaviest();
if (!target || target.n === 0) {
  console.log(`SKIP  ${SITE} 에서 코드블록이 있는 문서를 못 찾았다 — 먼저 mkdocs build`);
  process.exit(0);
}

const rel = path.relative(SITE, target.p).replace(/\/index\.html$/, "");
console.log(`대상: ${rel}  (코드블록 ${target.n}개)\n`);

const dom = new JSDOM(fs.readFileSync(target.p, "utf8"), {
  url: ORIGIN + rel + "/",
  virtualConsole: new VirtualConsole(),
  runScripts: "outside-only",
  pretendToBeVisual: true,
});
const w = dom.window;
w.fetch = async () => ({ ok: false, json: async () => null });

/* 읽기/쓰기 순서를 기록한다. jsdom 은 실제 레이아웃이 없어 값은 0 이지만,
   "호출 순서" 는 그대로라 스래싱 여부는 정확히 드러난다. */
let seq = [];
for (const prop of ["scrollWidth", "clientWidth", "scrollLeft"]) {
  const d = Object.getOwnPropertyDescriptor(w.Element.prototype, prop);
  Object.defineProperty(w.Element.prototype, prop, {
    configurable: true,
    get() { seq.push("R"); return d && d.get ? d.get.call(this) : 0; },
  });
}
const setAttr = w.Element.prototype.setAttribute;
w.Element.prototype.setAttribute = function (n, v) {
  if (n === "data-yg-scroll") seq.push("W");
  return setAttr.call(this, n, v);
};
const removeAttr = w.Element.prototype.removeAttribute;
w.Element.prototype.removeAttribute = function (n) {
  if (n === "data-yg-scroll") seq.push("W");
  return removeAttr.call(this, n);
};

w.eval(fs.readFileSync(path.join(ROOT, "Develop/javascripts/extra.js"), "utf8"));
seq = [];
w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
await new Promise((r) => setTimeout(r, 80));

// 쓰기 다음에 읽기가 오면 그 지점에서 레이아웃이 강제된다
let forced = 0;
for (let i = 1; i < seq.length; i++) {
  if (seq[i] === "R" && seq[i - 1] === "W") forced++;
}
const reads = seq.filter((x) => x === "R").length;
const writes = seq.filter((x) => x === "W").length;

console.log(`  읽기 ${reads}회 / 쓰기 ${writes}회`);
console.log(`  쓰기 직후 읽기(강제 레이아웃) ${forced}회`);
console.log(`  (요소마다 번갈아 하면 요소 수만큼 — 나눠서 하면 한 자릿수)`);

const ok = forced <= 3;
console.log(`\n${ok ? "PASS" : "FAIL"}  강제 레이아웃 ${forced}회`);
process.exit(ok ? 0 : 1);
