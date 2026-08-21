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

// 저장소 문서에서 실제로 쓰이는 배경색 (빈도순). 새 색이 늘면 여기에 더한다.
const FILLS = [
  "#66bb6a", "#4fc3f7", "#ff9800", "#9c27b0", "#dbeafe", "#fef3c7",
  "#dcfce7", "#ffcdd2", "#fecaca", "#f5f5f5", "#c8e6c9", "#e0e7ff",
  "#e0f2fe", "#fce7f3",
];
const MIN = 4.5; // WCAG AA 본문 기준

let fail = 0;
const check = (ok, msg) => { if (!ok) fail++; console.log(`  ${ok ? "PASS" : "FAIL"}  ${msg}`); };

console.log("실제 쓰이는 배경색에서 고른 글자색의 대비\n");
console.log("  배경        글자     대비      흰글자면");
for (const fill of FILLS) {
  const bg = ctx.parseColor(fill);
  if (!bg) { check(false, `${fill} 을 못 읽었다`); continue; }
  const text = ctx.pickTextColor(bg);
  const got = ctx.contrastRatio(bg, text === "#000000" ? [0, 0, 0] : [255, 255, 255]);
  const white = ctx.contrastRatio(bg, [255, 255, 255]);
  console.log(
    `  ${fill.padEnd(10)} ${text}  ${got.toFixed(2).padStart(6)}:1  ${white.toFixed(2).padStart(5)}:1${white < MIN ? "  ← 그대로 뒀으면 안 읽힘" : ""}`
  );
  if (got < MIN) { fail++; console.log(`        FAIL  ${fill} 에서 대비 ${got.toFixed(2)}:1 (${MIN} 미만)`); }
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
