#!/usr/bin/env python3
"""check_contrast.py 의 색 계산 회귀 테스트.

실행: python3 tools/tests/test_check_contrast.py

왜 테스트를 두는가: 이 검사기는 **초록불이 정상 상태**다. 그래서 판정
로직이 죽어도 출력이 그대로라 아무도 모른다. 실제로 두 번 당했다.

  (1) `:root` 블록을 하나만 읽어서, 뒤에 오는 블록의 값을 못 봤다.
      멀쩡한 목차 제목을 2.02:1 로 잡았다(실제 8.10:1). 하마터면
      결함이 아닌 걸 고칠 뻔했다.
  (2) 반투명을 만나면 그냥 포기했다. 미판정이 28쌍까지 늘었고 그 안에
      사이드바 선택 항목·태그 hover·코드 배경이 전부 들어 있었다.
      출력 줄은 "4.5:1 미만 없음" 이라 초록불이었다. **미판정은 통과가
      아니라 미검사인데 통과처럼 읽혔다.**

두 사고 모두 "검사기가 조용히 아무것도 안 하고 있었다" 는 한 가지 유형이다.
그래서 여기서는 값을 알고 있는 색을 넣고 그 값이 나오는지를 본다.
"""
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "cc", REPO_ROOT / "tools" / "check_contrast.py"
)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def test_contrast_matches_wcag_reference():
    """WCAG 정의값. 이게 틀리면 아래 전부가 의미 없다."""
    assert round(cc.contrast(WHITE, BLACK), 2) == 21.0
    assert round(cc.contrast(WHITE, WHITE), 2) == 1.0
    # W3C 예제: #777 on #fff = 4.48:1 (AA 를 아슬하게 못 넘긴다)
    assert round(cc.contrast(cc.parse_color("#777777"), WHITE), 2) == 4.48


def test_parse_rgba_keeps_alpha():
    """알파를 버리면 반투명이 통째로 미판정이 된다 — 사고 (2) 의 원인."""
    assert cc.parse_rgba("#ffffff") == (255, 255, 255, 1.0)
    assert cc.parse_rgba("rgba(255, 255, 255, 0.06)")[3] == 0.06
    assert cc.parse_rgba("rgb(1,2,3)") == (1, 2, 3, 1.0)
    assert cc.parse_rgba("#0000") == (0, 0, 0, 0.0)
    assert cc.parse_rgba("탈것") is None


def test_flatten_composites_over_backdrop():
    """반투명 흰색 6% 를 검정 위에 얹으면 6% 회색이 된다."""
    assert cc.flatten((255, 255, 255, 0.0), BLACK) == BLACK
    assert cc.flatten((255, 255, 255, 1.0), BLACK) == WHITE
    got = cc.flatten((255, 255, 255, 0.06), BLACK)
    assert all(abs(v - 15.3) < 0.01 for v in got), got
    # 불투명하면 바닥이 없어도 답이 나와야 한다
    assert cc.flatten((10, 20, 30, 1.0), None) == (10, 20, 30)
    # 반투명인데 바닥을 모르면 답이 없다 — 아는 척하면 안 된다
    assert cc.flatten((10, 20, 30, 0.5), None) is None


def test_parse_color_still_rejects_translucent():
    """면 검사가 쓰는 옛 계약. 반투명은 '그 면이다' 라고 말할 수 없다."""
    assert cc.parse_color("#7FB3D5") == (127, 179, 213)
    assert cc.parse_color("rgba(0,0,0,0.5)") is None
    assert cc.parse_color("#00000080") is None


def test_gradient_stops_finds_both_ends():
    """양 끝 대비가 다르다. 한쪽만 보면 나머지 절반이 안 읽혀도 통과한다."""
    stops = cc.gradient_stops("linear-gradient(135deg, #387CAA, #7F6F9D)")
    assert [s[:3] for s in stops] == [(0x38, 0x7C, 0xAA), (0x7F, 0x6F, 0x9D)]
    assert cc.gradient_stops("#387CAA") == []


def test_collect_vars_merges_every_block():
    """같은 셀렉터 블록이 여러 개다. 하나만 읽던 게 사고 (1) 이었다."""
    css = ":root {\n  --a: #111;\n}\n.x { color: red; }\n:root {\n  --b: #222;\n}\n"
    got = cc.collect_vars(css, r":root\s*\{([\s\S]*?)\n\}")
    assert got == {"--a": "#111", "--b": "#222"}, got


def test_light_table_includes_scheme_default_block():
    """--md-default-bg-color 는 :root 가 아니라 scheme=default 안에 있다.
    이걸 못 읽으면 '페이지 바닥' 을 몰라서 라이트 쪽이 통째로 미판정이 된다."""
    css = cc.CSS.read_text(encoding="utf-8")
    root_only = cc.collect_vars(css, r":root\s*\{([\s\S]*?)\n\}")
    merged = dict(root_only)
    merged.update(
        cc.collect_vars(css, r'\[data-md-color-scheme="default"\]\s*\{([\s\S]*?)\n\}')
    )
    assert "--md-default-bg-color" not in root_only, (
        "전제가 바뀌었다 — :root 로 옮겨졌으면 main() 의 병합도 정리할 것"
    )
    assert cc.parse_color(merged["--md-default-bg-color"]) is not None


def test_real_stylesheet_has_a_light_and_dark_floor():
    """실제 스타일시트로 양 모드 바닥이 잡히는지. 여기가 None 이면
    반투명·transparent 계산이 전부 조용히 미판정으로 빠진다."""
    css = cc.CSS.read_text(encoding="utf-8")
    light = cc.collect_vars(css, r":root\s*\{([\s\S]*?)\n\}")
    light.update(
        cc.collect_vars(css, r'\[data-md-color-scheme="default"\]\s*\{([\s\S]*?)\n\}')
    )
    dark = {**light, **cc.collect_vars(
        css, r'\[data-md-color-scheme="slate"\]\s*\{([\s\S]*?)\n\}'
    )}
    for name, table in (("라이트", light), ("다크", dark)):
        floor = cc.parse_color(cc.resolve("var(--md-default-bg-color)", table))
        assert floor is not None, f"{name} 바닥색을 못 찾았다"
    assert cc.parse_color(cc.resolve("var(--md-default-bg-color)", light)) != \
        cc.parse_color(cc.resolve("var(--md-default-bg-color)", dark)), \
        "두 모드 바닥이 같다 — 변수 병합이 어긋났다"


def test_end_to_end_denominator_does_not_shrink():
    """**이 테스트가 이 파일의 핵심이다.**

    위 검사들은 함수 하나하나를 본다. 그런데 두 사고 모두 함수가 아니라
    main() 의 배선이 끊긴 것이었다 — 함수는 멀쩡한데 호출부가 반투명을
    그냥 건너뛰고 있었다. 부품 검사만으로는 그걸 못 잡는다.

    그래서 실제로 돌려서 분모를 읽는다. 판정 수가 줄면 검사기가 조용히
    일을 덜 하고 있다는 뜻이고, 그건 초록불이어도 후퇴다.

    숫자를 올려 잡는 건 자유다. 내리려면 왜 덜 봐도 되는지가 있어야 한다."""
    import re
    import subprocess

    out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_contrast.py")],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout
    m = re.search(r"판정 (\d+)쌍 / 미판정 (\d+)쌍", out)
    assert m, f"분모 줄을 못 찾았다:\n{out}"
    judged, skipped = int(m.group(1)), int(m.group(2))
    assert judged >= 46, f"판정이 46쌍에서 {judged}쌍으로 줄었다 — 검사 범위 후퇴"
    assert skipped <= 3, f"미판정이 3쌍에서 {skipped}쌍으로 늘었다 — 미판정은 통과가 아니다"


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            fails.append((name, e))
            print(f"  FAIL  {name}  — {e}")
    print(f"\n{'전부 통과' if not fails else f'실패 {len(fails)}건'}")
    sys.exit(1 if fails else 0)
