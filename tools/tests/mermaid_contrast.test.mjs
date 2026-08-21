/* 다이어그램 글자 대비 회귀 테스트.

   왜 두는가: 문서들이 `style A fill:#e0f2fe` 처럼 배경색만 지정하고 글자색을
   안 준다. 측정하니 mermaid 안에서 배경을 지정한 1,171줄 중 623줄이 그렇다
   (85개 문서). 다크 테마는 글자를 밝게 칠하므로 밝은 배경 + 밝은 글자가 되어
   아예 안 읽힌다.

   623줄을 고치는 대신 mermaid-init.js 가 렌더 후 배경 휘도를 재서 글자색을
   정한다. 그 계산이 틀어지면 화면은 "그려지긴 하는데 안 읽히는" 상태가 된다 —
   빌드도 통과하고 에러도 없어서 눈으로만 잡힌다.

   jsdom 은 SVG 레이아웃·getComputedStyle 을 제대로 안 하므로, 여기서는
   계산 함수 자체를 실제 저장소에서 쓰이는 배경색으로 검증한다.

   실행:
     node tools/tests/mermaid_contrast.test.mjs
*/
import fs from "fs";
import path from "path";
import vm from "vm";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SRC = fs.readFileSync(path.join(ROOT, "Develop/javascripts/mermaid-init.js"), "utf8");

/** 소스에서 함수 하나를 중괄호 균형으로 떼어 온다. */
function extract(sig) {
  const i = SRC.indexOf(sig);
  if (i < 0) throw new Error(`${sig} 를 못 찾았다 — 이름이 바뀌었는지 확인`);
  let depth = 0;
  for (let k = SRC.indexOf("{", i); k < SRC.length; k++) {
    if (SRC[k] === "{") depth++;
    else if (SRC[k] === "}" && --depth === 0) return SRC.slice(i, k + 1);
  }
  throw new Error(`${sig} 의 끝을 못 찾았다`);
}

const ctx = vm.createContext({});
vm.runInContext(
  ["function parseColor", "function relLuminance", "function contrastRatio", "function pickTextColor"]
    .map(extract)
    .join("\n"),
  ctx
);

/* 저장소 문서에서 실제로 쓰이는 배경색 — 빈도 상위 14. 새 색이 늘면 여기에 더한다.
   뽑는 법: mermaid 펜스 안의 style/classDef 줄에서 fill: 값을 세면 된다. */
const FILLS = [
  ["#66bb6a", 87], ["#4fc3f7", 71], ["#ff9800", 61], ["#9c27b0", 42],
  ["#ef5350", 42], ["#dbeafe", 38], ["#fef3c7", 36], ["#1a1a2e", 33],
  ["#2d333b", 22], ["#dcfce7", 21], ["#4ade80", 21], ["#4a9eff", 18],
  ["#d1fae5", 18], ["#fbbf24", 16],
];

/* mermaid 가 실제로 쓰는 기본 글자색. 검정/흰색이 아니다 —
   실물(mermaid 10.9.3)을 렌더해 DOM 에서 확인한 값이다.
   이 기준을 틀리게 잡으면 "무엇이 깨져 있었는지" 자체가 어긋난다. */
const THEME_TEXT = { 라이트: "#333333", 다크: "#cccccc" };
const MIN = 4.5; // WCAG AA 본문 기준

let fail = 0;
const check = (ok, msg) => { if (!ok) fail++; console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}`); };

console.log("보정 전후 대비 — 라이트와 다크 양쪽\n");
console.log("  배경       쓰인수   라이트(전)    다크(전)     보정 후");
let brokenLight = 0, brokenDark = 0;
for (const [fill, uses] of FILLS) {
  const bg = ctx.parseColor(fill);
  if (!bg) { check(false, `${fill} 을 못 읽었다`); continue; }
  const before = {};
  for (const [name, hex] of Object.entries(THEME_TEXT)) {
    before[name] = ctx.contrastRatio(bg, ctx.parseColor(hex));
  }
  if (before["라이트"] < MIN) brokenLight++;
  if (before["다크"] < MIN) brokenDark++;

  const text = ctx.pickTextColor(bg);
  const after = ctx.contrastRatio(bg, text === "#000000" ? [0, 0, 0] : [255, 255, 255]);
  const mark = (v) => (v < MIN ? "←깨짐" : "     ");
  console.log(
    `  ${fill}  ${String(uses).padStart(4)}   ` +
    `${before["라이트"].toFixed(2).padStart(6)}:1${mark(before["라이트"])} ` +
    `${before["다크"].toFixed(2).padStart(6)}:1${mark(before["다크"])}  ` +
    `${text} ${after.toFixed(2)}:1`
  );
  if (after < MIN) { fail++; console.log(`        FAIL  ${fill} 보정 후 ${after.toFixed(2)}:1 (${MIN} 미만)`); }
}
console.log(`\n  보정 전 기준 미달: 라이트 ${brokenLight}색 / 다크 ${brokenDark}색`);
check(brokenLight > 0 && brokenDark > 0,
  "이 검사가 실제로 무언가를 잡고 있다 (양쪽 모드에 깨진 색이 있었다)");
console.log();

/* 색공간 전체에서 보증되는가.
   검정과 흰색의 대비가 같아지는 중간 휘도가 최악의 경우다. */
{
  let worst = Infinity, at = null;
  for (let r = 0; r < 256; r += 3) {
    for (let g = 0; g < 256; g += 3) {
      for (let b = 0; b < 256; b += 3) {
        const t = ctx.pickTextColor([r, g, b]);
        const v = ctx.contrastRatio([r, g, b], t === "#000000" ? [0, 0, 0] : [255, 255, 255]);
        if (v < worst) { worst = v; at = [r, g, b]; }
      }
    }
  }
  console.log(`  전 색공간 최저 대비 ${worst.toFixed(2)}:1 @ rgb(${at})`);
  check(worst >= MIN, `어떤 불투명 배경에서도 ${MIN}:1 이상`);
}
console.log();

// 색 파싱이 형식별로 되는가
check(String(ctx.parseColor("#fff")) === "255,255,255", "3자리 hex");
check(String(ctx.parseColor("#e0f2fe")) === "224,242,254", "6자리 hex");
check(String(ctx.parseColor("rgb(1, 2, 3)")) === "1,2,3", "rgb()");
check(String(ctx.parseColor("rgba(1,2,3,1)")) === "1,2,3", "불투명 rgba()");
check(ctx.parseColor("rgba(1,2,3,0.5)") === null, "반투명은 판정 포기 (뒤가 비쳐 배경을 모른다)");
check(ctx.parseColor("none") === null, "none 은 판정 포기");
check(ctx.parseColor("url(#grad)") === null, "그라디언트는 판정 포기");

// 경계
check(ctx.pickTextColor([255, 255, 255]) === "#000000", "흰 배경 → 검은 글자");
check(ctx.pickTextColor([0, 0, 0]) === "#ffffff", "검은 배경 → 흰 글자");
check(Math.abs(ctx.contrastRatio([255, 255, 255], [0, 0, 0]) - 21) < 0.01, "흑백 대비는 21:1");

// 배선 — 계산만 맞고 안 불리면 아무 소용이 없다
check(/fixContrast\(node\)/.test(SRC), "렌더 뒤 fixContrast 가 실제로 호출된다");

console.log(`\n${fail === 0 ? "전부 통과" : "실패 " + fail + "건"}`);
process.exit(fail ? 1 : 0);
