#!/usr/bin/env python3
"""extra.css 의 전경·배경 색 쌍이 WCAG 대비를 넘는지 검사한다.

왜 필요한가: 색을 한쪽 모드에서만 손보면 반대쪽이 조용히 깨진다. 화면은
"보이긴 하는데 안 읽히는" 상태가 되고, 빌드도 링크 검사도 통과한다.
실제로 mermaid 다이어그램이 그렇게 깨져 있었다 — 다크 12색, 라이트 4색.

## 이 검사가 보는 것과 못 보는 것 (반드시 읽을 것)

이 검사는 **같은 규칙 안에 color 와 background 가 함께 있는 쌍**만 본다.
초록불이 "이 사이트의 대비가 안전하다"는 뜻이 **아니다**. 그래서 결론 줄에
판정 분모를 같이 찍는다 — 분모 없는 초록불은 통과가 아니라 미검사다.

못 보는 것:
  · 배경이 부모에서 오는 경우 (`hr`·아이콘·배지·카드 테두리 대부분이 여기다)
  · 반투명 배경 (뒤 표면을 알아야 실효색이 나온다)
  · Material 팔레트가 소유한 색 (extra.css 가 선언하지 않아 값을 모른다)
  · 문서 안 raw SVG 의 하드코딩 fill/stroke

## 두 가지 함정 — 둘 다 실제로 밟았다

**1. 변수 블록은 하나가 아니다.**
`:root` 도 `[data-md-color-scheme="slate"]` 도 파일 안에 여러 번 나온다.
처음엔 첫 블록만 읽어 slate 의 `--warm-white` 를 못 찾고 라이트 배경값으로
풀었다. 멀쩡한 목차 제목이 2.02:1 로 나왔고(실제 8.10:1) 없는 결함을 고칠
뻔했다. 전부 모아서 뒤에 오는 것이 이기게 해야 한다.

**2. 선택자에 slate 가 없다고 라이트 전용 규칙이 아니다.**
그 규칙은 다크에서도 그대로 적용되고, 그때 `var()` 는 다크 값으로 풀린다.
처음엔 `"slate" in sel` 로만 갈라서, slate 짝이 없는 선언 93건을 통째로
놓쳤다. 실제 결함 하나(blockquote 다크 2.19:1)가 그 구멍에 있었다.

다만 비-slate 규칙을 다크 표로 그냥 돌리면 오탐이 난다 — slate 오버라이드가
이기는 경우가 있다. 그래서 **같은 요소를 겨냥한 slate 규칙이 같은 속성을
재정의하는지**까지 보고, 재정의하면 그 규칙의 다크 평가를 건너뛴다.

사용: python3 tools/check_contrast.py [--strict] [--min 4.5]
"""
import math
import re
import sys
from pathlib import Path

CSS = Path(__file__).parent.parent / "Develop" / "stylesheets" / "extra.css"
DEFAULT_MIN = 4.5  # WCAG AA 본문
SLATE = '[data-md-color-scheme="slate"]'


def parse_color(s):
    """불투명한 색만 값으로 본다. 반투명은 뒤가 비쳐 실제 배경을 알 수 없다."""
    s = s.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        if len(h) == 8 and int(h[6:], 16) < 255:
            return None
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\(([^)]+)\)", s)
    if not m:
        return None
    parts = [p for p in re.split(r"[,\s/]+", m.group(1)) if p]
    try:
        nums = [float(p) for p in parts[:4]]
    except ValueError:
        return None
    if len(nums) < 3 or (len(nums) > 3 and nums[3] < 1):
        return None
    return tuple(nums[:3])


def rel_luminance(rgb):
    def ch(v):
        x = v / 255
        return x / 12.92 if x <= 0.03928 else math.pow((x + 0.055) / 1.055, 2.4)

    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = rel_luminance(a), rel_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def collect_vars(css, pattern):
    """같은 셀렉터의 블록이 여러 개다. 전부 모으고 뒤에 오는 것이 이긴다."""
    out = {}
    for block in re.finditer(pattern, css):
        for v in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", block.group(1)):
            out[v.group(1)] = v.group(2).strip()
    return out


def resolve(value, table, depth=0):
    if depth > 6:
        return value
    m = re.search(r"var\((--[\w-]+)(?:\s*,\s*([^)]+))?\)", str(value))
    if not m:
        return value
    got = table.get(m.group(1), m.group(2) or "")
    return resolve(str(value).replace(m.group(0), got), table, depth + 1)


def norm_sel(sel):
    """주석을 떼고 공백을 정리한다.

    규칙 앞에 붙은 `/* ... */` 가 선택자 텍스트에 딸려 들어온다. 그대로 두면
    `.md-typeset blockquote` 와 `/* blockquote */ .md-typeset blockquote` 가
    다른 것으로 잡혀서, slate 오버라이드가 있는데도 없다고 판정한다.
    실제로 그래서 이미 고친 결함이 계속 걸렸다.
    """
    return " ".join(re.sub(r"/\*.*?\*/", " ", sel, flags=re.S).split())


def slate_overrides(rules, sel, prop):
    """이 요소를 겨냥한 slate 규칙이 같은 속성을 재정의하는가.

    `[slate] .foo` 는 `.foo` 를 덮는다. 쉼표로 묶인 선택자도 각각 본다.
    덮는다면 그 규칙의 다크 평가는 의미가 없으므로 건너뛴다.
    """
    targets = [norm_sel(p) for p in sel.split(",") if p.strip()]
    for s2, body2 in rules:
        if SLATE not in s2:
            continue
        if not re.search(rf"(?:^|;)\s*{prop}\s*:", body2):
            continue
        for p2 in s2.split(","):
            bare = norm_sel(p2.replace(SLATE, ""))
            if not bare:
                continue
            if any(bare == t or t.endswith(" " + bare) or bare.endswith(" " + t) for t in targets):
                return True
    return False


def main():
    strict = "--strict" in sys.argv
    minimum = DEFAULT_MIN
    if "--min" in sys.argv:
        minimum = float(sys.argv[sys.argv.index("--min") + 1])

    css = CSS.read_text(encoding="utf-8")
    light = collect_vars(css, r":root\s*\{([\s\S]*?)\n\}")
    dark = {**light, **collect_vars(css, rf'{re.escape(SLATE)}\s*\{{([\s\S]*?)\n\}}')}

    rules = [(r.group(1), r.group(2), r.start()) for r in re.finditer(r"([^{}]+)\{([^}]*)\}", css)]
    plain = [(s, b) for s, b, _ in rules]

    judged, skipped, bad = 0, 0, []
    for sel, body, pos in rules:
        if "@" in sel:
            continue
        cm = re.search(r"(?:^|;)\s*color\s*:\s*([^;!]+)", body)
        bm = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;!]+)", body)
        if not cm or not bm:
            continue

        is_slate = SLATE in sel
        # slate 규칙은 다크로만, 그 외는 라이트 + (오버라이드가 없으면) 다크로도 본다
        modes = [("다크", dark)] if is_slate else [("라이트", light)]
        if not is_slate:
            overridden = (
                slate_overrides(plain, sel, "color")
                or slate_overrides(plain, sel, "background")
                or slate_overrides(plain, sel, "background-color")
            )
            if not overridden:
                modes.append(("다크", dark))

        for mode, table in modes:
            bg_raw = resolve(bm.group(1).strip(), table)
            if re.search(r"gradient|url\(|none|transparent", bg_raw):
                skipped += 1
                continue
            fg = parse_color(resolve(cm.group(1).strip(), table))
            bg = parse_color(bg_raw)
            if not fg or not bg:
                skipped += 1
                continue
            judged += 1
            ratio = contrast(fg, bg)
            if ratio < minimum:
                line = css[:pos].count("\n") + 1
                bad.append((ratio, mode, line, norm_sel(sel)[:60],
                            cm.group(1).strip(), bm.group(1).strip()))

    denom = (
        f"판정 {judged}쌍 / 미판정 {skipped}쌍 — "
        "부모 배경·반투명·Material 팔레트 소유 색은 검사 범위 밖"
    )

    if not bad:
        print(f"✓ {minimum}:1 미만 없음.  ({denom})")
        return

    print(f"⚠ {minimum}:1 미만 {len(bad)}건  ({denom})\n")
    for ratio, mode, line, sel, fg, bg in sorted(bad):
        print(f"  {ratio:.2f}:1  [{mode}] extra.css:{line}  {sel}")
        print(f"          {fg}  on  {bg}")
    if strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
