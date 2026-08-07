#!/usr/bin/env python3
"""check_links.py 회귀 테스트.

실행: python3 -m pytest tools/tests/test_check_links.py -v
또는: python3 tools/tests/test_check_links.py
"""
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_links  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _tracked() -> set[str]:
    """테스트용 tracked 파일 집합 — 픽스처 파일만 포함."""
    return {
        unicodedata.normalize("NFC", str(p.relative_to(REPO_ROOT)))
        for p in FIXTURES.rglob("*.md")
    }


def test_code_fence_links_ignored():
    """코드 펜스 안의 깨진 링크는 보고되면 안 된다."""
    md = FIXTURES / "code_fence.md"
    broken = check_links.check_file(md, _tracked())
    # 깨진 링크가 0개여야 한다
    assert broken == [], f"코드 펜스 안 링크가 잘못 보고됨: {broken}"


def test_html_img_broken_reported():
    """<img src="없는파일.png">는 반드시 보고돼야 한다."""
    md = FIXTURES / "html_img.md"
    broken = check_links.check_file(md, _tracked())
    assert any("nonexistent-image-fixture" in link for link, _ in broken), (
        f"html img 깨진 링크가 보고되지 않음. broken={broken}"
    )


def test_nfd_content_detection():
    """NFD 문자가 포함된 텍스트를 올바르게 감지한다."""
    nfd_text = unicodedata.normalize("NFD", "한글 경로 테스트")
    nfc_text = unicodedata.normalize("NFC", "한글 경로 테스트")
    assert nfd_text != nfc_text, "NFD != NFC 전제 조건 실패"
    assert nfd_text != unicodedata.normalize("NFC", nfd_text), "NFD → NFC 변환이 동일하면 안 됨"


if __name__ == "__main__":
    tests = [test_code_fence_links_ignored, test_html_img_broken_reported, test_nfd_content_detection]
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
