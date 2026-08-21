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
import glob
import math
import os
import re
import sys
from pathlib import Path

CSS = Path(__file__).parent.parent / "Develop" / "stylesheets" / "extra.css"
DEFAULT_MIN = 4.5  # WCAG AA 본문
SLATE = '[data-md-color-scheme="slate"]'


def parse_rgba(s):
    """색을 (r, g, b, a) 로 읽는다. 못 읽으면 None.

    예전에는 반투명을 만나면 그대로 포기했다("뒤가 비쳐 실제 배경을 알 수
    없다"). 그 결과 미판정이 28쌍까지 늘었고, 그 안에 사이드바 선택 항목
    타이틴트·태그 hover·코드 배경처럼 **실제로 위험한 자리가 전부** 들어
    있었다. 미판정은 통과가 아니라 미검사인데, 출력 줄만 보면 초록불이라
    통과처럼 읽힌다. 그래서 알파를 버리지 말고 값으로 들고 온다."""
    s = s.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        a = int(h[6:], 16) / 255 if len(h) == 8 else 1.0
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4)) + (a,)
    m = re.fullmatch(r"rgba?\(([^)]+)\)", s)
    if not m:
        return None
    parts = [p for p in re.split(r"[,\s/]+", m.group(1)) if p]
    try:
        nums = [float(p.rstrip("%")) for p in parts[:4]]
    except ValueError:
        return None
    if len(nums) < 3:
        return None
    a = nums[3] if len(nums) > 3 else 1.0
    if "%" in "".join(parts[3:4]):
        a /= 100
    return (nums[0], nums[1], nums[2], a)


def flatten(rgba, backdrop):
    """반투명 색을 뒤 배경 위에 얹어 실제로 보이는 색을 낸다."""
    if rgba is None:
        return None
    r, g, b, a = rgba
    if a >= 1:
        return (r, g, b)
    if backdrop is None:
        return None
    return tuple(c * a + d * (1 - a) for c, d in zip((r, g, b), backdrop))


def parse_color(s):
    """불투명한 색만 값으로 보는 옛 계약. 면 검사가 이걸 그대로 쓴다."""
    v = parse_rgba(s)
    if v is None or v[3] < 1:
        return None
    return v[:3]


def gradient_stops(value):
    """그라디언트에서 색 정지점을 뽑는다. 양 끝이 각각 다른 대비를 갖는다."""
    if "gradient" not in value:
        return []
    return [
        c
        for c in (
            parse_rgba(m.group(0))
            for m in re.finditer(r"#[0-9a-f]{3,8}\b|rgba?\([^)]*\)", value, re.I)
        )
        if c
    ]


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


# ---------------------------------------------------------------------------
# 특이도 검사 — Material 규칙에 지는 선언 찾기
#
# 왜 여기 붙였나: 대비 계산과 같은 부류의 "조용한 실패" 다. CSS 를 적어 뒀는데
# 적용이 안 되고, 화면은 멀쩡히 뜨고, 에러도 안 난다.
#
# 이 저장소에서 실제로 일어난 일:
#   Material    .md-nav__link[href]:hover                        (0,3,0)
#   라이트 규칙  .md-nav__link:hover                              (0,2,0)  ← 짐
#   다크 규칙    [data-md-color-scheme="slate"] .md-nav__link:hover (0,3,0) ← 이김
#
# `[data-md-color-scheme="slate"]` 접두사가 특이도를 하나 공짜로 얹어 준다.
# 그래서 **다크만 멀쩡하고 라이트는 한 번도 안 칠해진** 상태가 된다.
# 같은 파일에 나란히 있는 두 규칙이라 눈으로는 차이를 못 본다.
# ---------------------------------------------------------------------------
def specificity(sel):
    s = sel.strip()
    ids = len(re.findall(r"#[\w-]+", s))
    cls = (
        len(re.findall(r"\.[\w-]+", s))
        + len(re.findall(r"\[[^\]]+\]", s))
        + len(re.findall(r":(?!:)(?:hover|focus|active|checked|not|first|last|nth|target|visited|disabled)[\w-]*", s))
    )
    el = len(re.findall(r"(?:^|[\s>+~])([a-z][\w-]*)", s))
    return (ids, cls, el)


def check_specificity(css, site_dir):
    """Material 스타일시트를 찾아 같은 대상을 겨냥한 규칙끼리 특이도를 견준다."""
    found = glob.glob(os.path.join(site_dir, "assets/stylesheets/main.*.css"))
    found = [f for f in found if not f.endswith(".map")]
    if not found:
        return None  # 빌드 산출물이 없으면 판정하지 않는다
    material = open(found[0], encoding="utf-8").read()

    def beats(sel_part):
        """이 선택자를 이기는 Material 규칙이 있으면 그 규칙을 낸다."""
        base = re.sub(r"\[[^\]]+\]", "", sel_part)
        sp = specificity(sel_part)
        for mm in re.finditer(r"([^{}@]+)\{([^}]*)\}", material):
            if "color" not in mm.group(2):
                continue
            for mp in mm.group(1).split(","):
                mp = mp.strip()
                if re.sub(r"\[[^\]]+\]", "", mp) != base:
                    continue
                if specificity(mp) > sp:
                    return (mp, specificity(mp))
        return None

    losing, seen = [], set()
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sel = norm_sel(m.group(1))
        if not sel or "@" in sel or SLATE in sel:
            continue
        if "color" not in m.group(2):
            continue
        parts = [p.strip() for p in sel.split(",") if p.strip().startswith(".md-")]
        if not parts:
            continue
        # 쉼표 그룹은 하나만 이기면 선언이 적용된다. 전부 지는 규칙만 잡는다.
        verdicts = [(p, beats(p)) for p in parts]
        if any(v is None for _, v in verdicts):
            continue
        line = css[: m.start()].count("\n") + 1
        p0, (mp, msp) = verdicts[0]
        if p0 in seen:
            continue
        seen.add(p0)
        losing.append((line, p0, specificity(p0), mp, msp))
    return losing


# 페이지 배경과 같은 면을 **일부러** 쓰는 자리. 사유를 반드시 적는다.
# 여기 없는 것이 걸리면 결함이다 — 대비 계산으로는 안 잡히는 부류라
# 이 목록이 유일한 방어선이다.
SAME_SURFACE_OK = {
    ".md-nav--secondary .md-nav__title":
        "sticky 제목. 배경이 투명하면 항목이 그 밑을 지나며 글자가 포개진다. "
        "페이지 배경색을 깔아 밑을 가리는 게 목적이라 같은 색이 맞다.",
    ".md-typeset .social-link:hover":
        "빌드 산출물에 렌더 0건 (legacy). 고쳐도 화면에 영향이 없다.",
    ".md-typeset .portfolio-card img":
        "빌드 산출물에 렌더 0건 (legacy).",
    ".yg-404-links a":
        "테두리(--border)로 경계를 낸다. 채우기가 없어도 알약 모양이 보인다.",
}


def check_invisible_surface(css, light, dark):
    """면을 깔았는데 그 면이 페이지 배경과 같은 색인 규칙을 찾는다.

    대비 계산으로는 안 걸린다 — 전경·배경 쌍이 아니라 "배경과 배경"의 문제라
    글자 대비는 멀쩡하다. 그런데 화면에서는 카드·코드블록·표 헤더가 통째로
    사라진다.

    이 저장소에서 실제로 있던 일: `--warm-white` 가 라이트에서 `#FDFBFA` 로
    페이지 배경과 **완전히 같은 값**이다. 그걸 표면으로 쓴 규칙들이 라이트에서만
    픽셀이 하나도 안 바뀌었다 — 코드블록(문서 1,156개), 인라인 코드(1,110개),
    표 헤더(674개), 푸터 호버(1,359개), 인용문(52개). 다크에는 전부 면이 있었다.

    판정: 배경끼리 1.02:1 미만이면 사실상 같은 면이다.
    """
    page = {"라이트": light.get("--warm-white"), "다크": dark.get("--warm-white")}
    out = []
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        sel = norm_sel(m.group(1))
        if not sel or "@" in sel:
            continue
        # 페이지 배경 자체를 정의하는 규칙은 당연히 같다
        if re.match(r"^(body|html)\b", sel):
            continue
        # 여러 줄 주석이 앞 규칙에서 넘어오면 선택자에 산문이 섞인다.
        # 한글이 들어간 건 선택자가 아니다.
        if re.search(r"[가-힣]", sel):
            continue
        bm = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;!]+)", m.group(2))
        if not bm:
            continue
        mode = "다크" if SLATE in sel else "라이트"
        table = dark if mode == "다크" else light
        surf = parse_color(resolve(bm.group(1).strip(), table))
        base = parse_color(resolve(page[mode] or "", table))
        if not surf or not base:
            continue
        if contrast(surf, base) >= 1.02:
            continue
        bare = sel.replace(SLATE, "").strip()
        if bare in SAME_SURFACE_OK or sel in SAME_SURFACE_OK:
            continue
        out.append((css[: m.start()].count("\n") + 1, mode, sel[:58], bm.group(1).strip()))
    return out


def main():
    strict = "--strict" in sys.argv
    minimum = DEFAULT_MIN
    if "--min" in sys.argv:
        minimum = float(sys.argv[sys.argv.index("--min") + 1])

    css = CSS.read_text(encoding="utf-8")
    # 라이트 변수는 :root 에만 있는 게 아니다. --md-default-bg-color 는
    # [data-md-color-scheme="default"] 안에 있어서, :root 만 긁던 동안
    # "페이지 바닥이 무슨 색인지" 를 몰랐다. 바닥을 모르면 반투명도
    # transparent 도 계산이 안 되니 라이트 쪽이 통째로 미판정으로 빠졌다.
    light = collect_vars(css, r":root\s*\{([\s\S]*?)\n\}")
    light.update(collect_vars(css, r'\[data-md-color-scheme="default"\]\s*\{([\s\S]*?)\n\}'))
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
            fg_raw = resolve(cm.group(1).strip(), table)
            # 이 모드에서 페이지가 깔고 있는 바닥. 반투명·transparent 는
            # 결국 이 위에 얹힌다.
            page = parse_color(resolve("var(--md-default-bg-color)", table))

            # color: inherit 는 부모를 따라간다. 우리 셀렉터는 전부 본문
            # 안이라 본문 기본 글자색이 그 부모다.
            if fg_raw.strip() in ("inherit", "currentcolor"):
                fg_raw = resolve("var(--md-typeset-color)", table)
                if "var(" in fg_raw or not parse_color(fg_raw):
                    fg_raw = resolve("var(--md-default-fg-color)", table)

            if re.search(r"url\(", bg_raw):
                skipped += 1
                continue

            # 배경 후보를 만든다. 그라디언트는 정지점마다 대비가 달라서
            # 양 끝을 각각 본다 — 한쪽만 맞으면 나머지 절반이 안 읽힌다.
            if "gradient" in bg_raw:
                cands = [flatten(c, page) for c in gradient_stops(bg_raw)]
            elif re.fullmatch(r"\s*(transparent|none)\s*", bg_raw):
                cands = [page]
            else:
                cands = [flatten(parse_rgba(bg_raw), page)]
            cands = [c for c in cands if c]

            fg = flatten(parse_rgba(fg_raw), cands[0] if cands else page)
            if not fg or not cands:
                skipped += 1
                continue

            judged += 1
            ratio = min(contrast(fg, bg) for bg in cands)
            if ratio < minimum:
                line = css[:pos].count("\n") + 1
                bad.append((ratio, mode, line, norm_sel(sel)[:60],
                            cm.group(1).strip(), bm.group(1).strip()))

    denom = (
        f"판정 {judged}쌍 / 미판정 {skipped}쌍 — "
        "반투명·transparent·inherit 는 페이지 바닥 위에 얹어 계산하고, "
        "그라디언트는 정지점 중 최악을 쓴다"
    )

    # 특이도 검사는 빌드 산출물이 있을 때만 (Material 스타일시트가 필요하다)
    site = os.environ.get("YG_SITE_DIR", "/tmp/_verify_site")
    losing = check_specificity(css, site)

    if bad:
        print(f"⚠ {minimum}:1 미만 {len(bad)}건  ({denom})\n")
        for ratio, mode, line, sel, fg, bg in sorted(bad):
            print(f"  {ratio:.2f}:1  [{mode}] extra.css:{line}  {sel}")
            print(f"          {fg}  on  {bg}")
    else:
        print(f"✓ {minimum}:1 미만 없음.  ({denom})")

    invisible = check_invisible_surface(css, light, dark)
    if invisible:
        print(f"\n⚠ 페이지 배경과 같은 색을 면으로 쓴 규칙 {len(invisible)}건 — 화면에서 안 보인다\n")
        for line, mode, sel, val in invisible:
            print(f"  [{mode}] extra.css:{line}  {sel}")
            print(f"          background: {val}")
    else:
        print("  면 검사: 페이지 배경과 같은 면 없음")

    if losing is None:
        print("  특이도 검사: 건너뜀 — 빌드 산출물이 없다 (YG_SITE_DIR 로 지정 가능)")
    elif losing:
        print(f"\n⚠ Material 규칙에 특이도로 지는 선언 {len(losing)}건 — 적어 뒀지만 적용되지 않는다\n")
        for line, sel, sp, msel, msp in losing:
            print(f"  extra.css:{line}  {sel}  {sp}")
            print(f"        Material  {msel}  {msp}  ← 이김")
    else:
        print("  특이도 검사: Material 에 지는 선언 없음")

    if strict and (bad or losing or invisible):
        sys.exit(1)


if __name__ == "__main__":
    main()
