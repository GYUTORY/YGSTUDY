/* 문서 안 mermaid 블록을 실제 파서에 물려 본다.

   왜 두는가: mermaid 문법이 틀리면 **빌드도 링크 검사도 전부 통과한다.**
   브라우저에서만 빈 상자나 빨간 오류 글씨가 뜬다. 941개 중 하나가 그렇게
   돼도 그 문서를 직접 열어 보기 전에는 알 방법이 없다.

   이미 있는 check_mermaid_entities.py 는 HTML 엔티티만 본다. 문법은 안 본다.

   두 가지를 지킨다.

   1. **사이트가 고정한 버전으로 본다.** mermaid-init.js 의 MERMAID_VERSION
      이 정본이다. 설치된 게 그와 다르면 결과를 믿을 수 없으니 실패로
      끝낸다 — 11 로 검사하고 "이상 없음" 이라 적는 게 제일 나쁘다.

   2. **검사기가 깨진 걸 잡는지부터 확인한다.** "실패 0개" 는 문서가
      깨끗하다는 뜻일 수도 있고 파서가 죽어서 아무것도 안 잡는다는 뜻일
      수도 있는데, 출력만 보면 둘이 똑같다. 그래서 일부러 틀린 것 넷을
      먼저 넣어 보고, 그게 안 걸리면 나머지 검사를 아예 하지 않는다.

   실행:
     npm i jsdom mermaid@10.9.3
     node tools/tests/mermaid_parse.test.mjs
*/
import fs from "fs";
import path from "path";
import { createRequire } from "module";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const DOCS = path.join(ROOT, "Develop");
const INIT = path.join(DOCS, "javascripts", "mermaid-init.js");

/* 사이트가 실제로 싣는 버전 */
const pinned = (fs.readFileSync(INIT, "utf8").match(/MERMAID_VERSION\s*=\s*"([^"]+)"/) || [])[1];
if (!pinned) {
  console.log("  FAIL  mermaid-init.js 에서 MERMAID_VERSION 을 못 읽었다");
  process.exit(1);
}

const require_ = createRequire(import.meta.url);
function locate(pkg) {
  for (const base of [ROOT, "/tmp/mmv"]) {
    const p = path.join(base, "node_modules", pkg);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

const mermaidDir = locate("mermaid");
const jsdomDir = locate("jsdom");
if (!mermaidDir || !jsdomDir) {
  console.log(`SKIP  mermaid/jsdom 이 없다 — \`npm i jsdom mermaid@${pinned}\` 후 다시 돌린다`);
  process.exit(0);
}

const installed = require_(path.join(mermaidDir, "package.json")).version;
if (installed !== pinned) {
  console.log(`  FAIL  버전이 다르다 — 사이트는 ${pinned}, 설치본은 ${installed}`);
  console.log("        다른 판으로 검사하고 '이상 없음' 이라 적는 게 제일 나쁘다.");
  console.log(`        고치려면: npm i mermaid@${pinned}`);
  process.exit(1);
}

const { JSDOM, VirtualConsole } = await import(path.join(jsdomDir, "lib", "api.js"));
const dom = new JSDOM("<body></body>", {
  url: "https://example.com/",
  virtualConsole: new VirtualConsole(),
  pretendToBeVisual: true,
});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
// node 22 의 globalThis.navigator 는 getter 전용이라 그냥 대입하면 터진다
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });

const { default: mermaid } = await import(path.join(mermaidDir, "dist", "mermaid.core.mjs"));
mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

/* mermaid 10 의 파서는 렉서 진행 상황을 console 로 쏟아 낸다. 결과가 그
   안에 파묻히므로 파싱 동안만 입을 막는다. */
const REAL = {
  log: console.log, debug: console.debug, info: console.info,
  warn: console.warn, error: console.error,
};
const mute = () => { for (const k of Object.keys(REAL)) console[k] = () => {}; };
const unmute = () => { for (const k of Object.keys(REAL)) console[k] = REAL[k]; };

async function parses(src) {
  mute();
  try {
    await mermaid.parse(src);
    return true;
  } catch {
    return false;
  } finally {
    unmute();
  }
}

/* ── 1단계: 검사기가 눈을 뜨고 있는가 ── */
const PROBES = [
  ["정상 flowchart", "graph LR\n  A[시작] --> B[끝]", true],
  ["정상 sequence", "sequenceDiagram\n  A->>B: 안녕", true],
  ["없는 다이어그램 종류", "graf LR\n  A --> B", false],
  ["화살표 오타", "graph LR\n  A --< B", false],
  ["대괄호 안 닫힘", "graph LR\n  A[시작 --> B", false],
  ["sequence 화살표 오타", "sequenceDiagram\n  A-->>>B: 안녕", false],
];

let blind = 0;
for (const [name, src, shouldPass] of PROBES) {
  const ok = await parses(src);
  if (ok !== shouldPass) {
    blind++;
    console.log(`  FAIL  자기검사: ${name} — ${shouldPass ? "통과해야" : "걸려야"} 하는데 ${ok ? "통과" : "걸림"}`);
  }
}
if (blind) {
  console.log(`\n검사기가 정상·비정상을 구분하지 못한다 (${blind}건). 문서 검사는 건너뛴다 — 결과를 믿을 수 없다.`);
  process.exit(1);
}

/* ── 2단계: 실제 문서 ── */
function walk(d, out = []) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith(".md")) out.push(p);
  }
  return out;
}

const blocks = [];
for (const file of walk(DOCS)) {
  const lines = fs.readFileSync(file, "utf8").split("\n");
  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (start === -1) {
      if (/^\s*```mermaid\s*$/.test(lines[i])) start = i;
    } else if (/^\s*```\s*$/.test(lines[i])) {
      blocks.push({ file, line: start + 1, src: lines.slice(start + 1, i).join("\n") });
      start = -1;
    }
  }
}

const bad = [];
for (const b of blocks) {
  if (!(await parses(b.src))) {
    let msg = "";
    mute();
    try { await mermaid.parse(b.src); } catch (e) { msg = String((e && e.message) || e); }
    unmute();
    bad.push({ ...b, msg: msg.split("\n").slice(0, 3).join(" / ").slice(0, 220) });
  }
}

const docs = new Set(blocks.map((b) => b.file)).size;
console.log(
  `  ${bad.length ? "FAIL" : "PASS"}  mermaid ${blocks.length}개 (문서 ${docs}개) 파싱 — 실패 ${bad.length}개  [v${installed}]`
);
for (const b of bad) {
  console.log(`        ${path.relative(ROOT, b.file)}:${b.line}`);
  console.log(`          ${b.msg}`);
  console.log(`          첫 줄: ${b.src.split("\n")[0].trim().slice(0, 90)}`);
}

console.log(`\n${bad.length === 0 ? "전부 통과" : "실패 " + bad.length + "건"}`);
process.exit(bad.length ? 1 : 0);
