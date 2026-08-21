#!/usr/bin/env python3
"""extra.css 의 전경·배경 색 쌍이 WCAG 대비를 넘는지 검사한다.

왜 필요한가: 색을 한쪽 모드에서만 손보면 반대쪽이 조용히 깨진다. 화면은
"보이긴 하는데 안 읽히는" 상태가 되고, 빌드도 링크 검사도 통과한다.
실제로 mermaid 다이어그램이 그렇게 깨져 있었다 — 다크 12색, 라이트 4색.

**주의: CSS 변수 블록은 하나가 아니다.**
`:root` 도 `[data-md-color-scheme="slate"]` 도 파일 안에 여러 번 나온다.
처음 이 계산을 짤 때 첫 블록만 읽었더니 slate 의 `--warm-white` 를 못 찾아
라이트 배경값으로 풀었고, 멀쩡한 목차 제목이 2.02:1 로 나왔다(실제 8.10:1).
없는 결함을 고칠 뻔했다. 전부 모아서 뒤에 오는 것이 이기게 해야 한다.

판정 대상은 **같은 규칙 안에 color 와 background 가 함께 있는 것**뿐이다.
배경이 부모에서 오는 경우는 CSS 만 봐서는 알 수 없어 판정하지 않는다.
그라디언트·투명·url() 도 실제 배경을 알 수 없어 제외한다.

사용: python3 tools/check_contrast.py [--strict] [--min 4.5]
"""
import math
import re
import sys
from pathlib import Path

CSS = Path(__file__).parent.parent / "Develop" / "stylesheets" / "extra.css"
DEFAULT_MIN = 4.5  # WCAG AA 본문


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


def main():
    strict = "--strict" in sys.argv
    minimum = DEFAULT_MIN
    if "--min" in sys.argv:
        minimum = float(sys.argv[sys.argv.index("--min") + 1])

    css = CSS.read_text(encoding="utf-8")
    light = collect_vars(css, r":root\s*\{([\s\S]*?)\n\}")
    dark = {**light, **collect_vars(css, r'\[data-md-color-scheme="slate"\]\s*\{([\s\S]*?)\n\}')}

    judged, skipped, bad = 0, 0, []
    for rule in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sel, body = rule.group(1), rule.group(2)
        if "@" in sel:
            continue
        cm = re.search(r"(?:^|;)\s*color\s*:\s*([^;!]+)", body)
        bm = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;!]+)", body)
        if not cm or not bm:
            continue
        is_dark = "slate" in sel
        table = dark if is_dark else light
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
            line = css[: rule.start()].count("\n") + 1
            bad.append((ratio, "다크" if is_dark else "라이트", line,
                        " ".join(sel.split())[:60], cm.group(1).strip(), bm.group(1).strip()))

    print(f"  변수 — 라이트 {len(light)}개 / 다크(병합) {len(dark)}개")
    print(f"  전경·배경이 같은 규칙에 있는 쌍: 판정 {judged}개 / 미판정 {skipped}개")
    print(f"    (미판정 = 그라디언트·투명·url()·해석 불가. 배경이 부모에서 오는 경우도 판정 안 함)")

    if not bad:
        print(f"✓ {minimum}:1 미만 없음.")
        return

    print(f"\n⚠ {minimum}:1 미만 {len(bad)}건:\n")
    for ratio, mode, line, sel, fg, bg in sorted(bad):
        print(f"  {ratio:.2f}:1  [{mode}] extra.css:{line}  {sel}")
        print(f"          {fg}  on  {bg}")
    if strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
