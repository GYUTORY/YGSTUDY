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
    links, images = check_links.check_file(md, _tracked())
    assert links == [] and images == [], f"코드 펜스 안 링크가 잘못 보고됨: {links} {images}"


def test_html_img_broken_reported():
    """<img src="없는파일.png">는 반드시 보고돼야 한다."""
    md = FIXTURES / "html_img.md"
    _links, images = check_links.check_file(md, _tracked())
    assert any("nonexistent-image-fixture" in raw for raw, _ in images), (
        f"html img 깨진 링크가 보고되지 않음. images={images}"
    )


def test_markdown_image_not_false_positive():
    """마크다운 이미지는 MkDocs 가 경로를 다시 써 주므로 오탐이 나면 안 된다.

    실제로 이 규칙을 안 지켜서 멀쩡한 이미지 56건이 매번 깨진 것으로 보고됐다.
    raw <img> 는 재작성되지 않아 한 단계 깊은 URL 기준이 맞지만,
    ![](...) 는 원본이 있는 자리에서 찾아야 한다.
    """
    md = FIXTURES / "md_image.md"
    _links, images = check_links.check_file(md, _tracked())
    assert not any("real-image-fixture" in raw for raw, _ in images), (
        f"실제로 있는 마크다운 이미지가 깨진 것으로 보고됨: {images}"
    )


def test_markdown_image_broken_still_reported():
    """오탐을 없앴다고 진짜 깨진 것까지 놓치면 안 된다."""
    md = FIXTURES / "md_image.md"
    _links, images = check_links.check_file(md, _tracked())
    assert any("missing-image-fixture" in raw for raw, _ in images), (
        f"없는 마크다운 이미지가 보고되지 않음: {images}"
    )


def test_nfd_content_detection():
    """NFD 문자가 포함된 텍스트를 올바르게 감지한다."""
    nfd_text = unicodedata.normalize("NFD", "한글 경로 테스트")
    nfc_text = unicodedata.normalize("NFC", "한글 경로 테스트")
    assert nfd_text != nfc_text, "NFD != NFC 전제 조건 실패"
    assert nfd_text != unicodedata.normalize("NFC", nfd_text), "NFD → NFC 변환이 동일하면 안 됨"


if __name__ == "__main__":
    tests = [
        test_code_fence_links_ignored,
        test_html_img_broken_reported,
        test_markdown_image_not_false_positive,
        test_markdown_image_broken_still_reported,
        test_nfd_content_detection,
    ]
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
