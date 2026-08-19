#!/usr/bin/env python3
"""check_frontmatter.py 회귀 테스트.

실행: python3 -m pytest tools/tests/test_check_frontmatter.py -v
또는: python3 tools/tests/test_check_frontmatter.py

왜 테스트를 두는가: 이 파일에는 전례가 있다. SKIP_DIRS 가 선언만 돼 있고
정작 본문은 "_hub" 를 하드코딩해서, 목록에 디렉터리를 더해도 아무 일이
일어나지 않던 기간이 있었다. 잡는 걸 확인하지 않은 검사기는 통과만 하다가
조용히 아무것도 안 하게 된다.
"""
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_frontmatter as cf  # noqa: E402


def test_title_extracted():
    """frontmatter 의 title 을 읽어낸다."""
    p = REPO_ROOT / "Develop" / "DevOps" / "Monitoring" / "Loki_Log_Aggregation.md"
    assert p.exists(), f"픽스처로 삼은 문서가 없다: {p}"
    assert cf._title(p), "title 을 못 읽었다"


def test_no_frontmatter_returns_none():
    """프론트매터가 없으면 None — 제목 중복 판정에서 빠진다."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write("# 제목만 있고 프론트매터가 없다\n본문.\n")
        tmp = Path(f.name)
    try:
        assert cf._title(tmp) is None
    finally:
        tmp.unlink()


def test_norm_ignores_case_and_punctuation():
    """대소문자·공백·문장부호 차이는 같은 제목으로 본다."""
    assert cf._norm_title("Loki 로그 집계") == cf._norm_title("loki  로그, 집계!")
    assert cf._norm_title("AWS IAM") == cf._norm_title("aws-iam")


def test_norm_matches_nfd_hangul():
    """자모 분리(NFD)로 저장된 한글도 같은 제목으로 잡힌다.

    macOS 에서 만든 파일이 NFD 로 들어온 적이 있어서, 눈에는 같은 글자인데
    비교에서 갈리면 중복을 놓친다.
    """
    nfc = "Loki 레이블 설계와 카디널리티"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd, "이 테스트가 성립하려면 두 형태가 실제로 달라야 한다"
    assert cf._norm_title(nfc) == cf._norm_title(nfd)


def test_norm_keeps_distinct_titles_distinct():
    """서로 다른 제목까지 뭉개면 오탐이 난다 — 게이트로 쓸 수 없게 된다."""
    assert cf._norm_title("Loki 수집 구성과 운영") != cf._norm_title(
        "Loki 레이블 설계와 카디널리티"
    )
    assert cf._norm_title("SQL Injection 공격 원리와 ORM 함정") != cf._norm_title(
        "SQL Injection 방어와 권한 설계"
    )


def test_repo_has_no_duplicate_titles():
    """실제 저장소에 제목이 같은 문서가 없다.

    이 검사를 게이트로 삼을 자격은 정밀도에서 나왔다 — 전체 문서에 걸린 것이
    Loki 한 쌍뿐이었고 오탐이 0이었다. 오탐이 생기기 시작하면 이 테스트가
    먼저 깨지므로, 그때 DUP_TITLE_ALLOW 를 쓸지 판정 자체를 고칠지 정하면 된다.
    """
    from collections import defaultdict

    by_title = defaultdict(list)
    for md in sorted((REPO_ROOT / "Develop").rglob("*.md")):
        if cf.SKIP_DIRS.intersection(md.parts) or md.name in cf.SKIP_FILES:
            continue
        t = cf._title(md)
        if t and cf._norm_title(t) not in cf.DUP_TITLE_ALLOW:
            by_title[cf._norm_title(t)].append(md)

    dups = {k: v for k, v in by_title.items() if len(v) > 1}
    assert not dups, "제목이 같은 문서가 있다: " + "; ".join(
        f"{k} -> {[str(p.relative_to(REPO_ROOT)) for p in v]}" for k, v in dups.items()
    )


if __name__ == "__main__":
    # 테스트 함수를 손으로 목록에 적으면, 함수를 추가하고 목록에 안 넣었을 때
    # 조용히 안 돈다 — 통과 개수만 늘지 않을 뿐 아무도 눈치채지 못한다.
    # 모듈에 정의된 test_* 를 전부 찾아 돈다.
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
