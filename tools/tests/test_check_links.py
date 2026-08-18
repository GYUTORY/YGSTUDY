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


def test_nfd_path_matches_nfc_tracked_entry():
    """NFD 로 쓴 한글 경로가 git 이 들고 있는 NFC 이름과 연결돼야 한다.

    macOS 는 파일명을 NFD 로 내놓고 git 은 NFC 로 들고 있다. 정규화를 안 하면
    멀쩡한 한글 링크가 전부 깨진 것으로 잡힌다. check_links 는 비교 직전에
    NFC 로 맞춰 이걸 흡수한다 — 그 흡수가 실제로 되는지 본다.

    일부러 디스크에 없는 파일을 대상으로 삼는다. macOS 파일시스템은 NFD/NFC 를
    가리지 않고 열어주기 때문에, 실제 파일이 있으면 정규화를 꺼도 통과해 버려서
    아무것도 검증하지 못한다. tracked 집합으로만 맞춰야 정규화 코드가 실제로 탄다.

    이 자리에는 원래 unicodedata.normalize 가 NFD != NFC 를 내는지만 보는
    테스트가 있었다. 표준 라이브러리만 확인하는 것이라 check_links 를 통째로
    지워도 통과했다. 죽어서 안 도는 검사보다 살아서 아무것도 안 보는 검사가
    더 오래 숨는다.
    """
    md = FIXTURES / "nfd_link.md"
    # git 은 NFC 로 들고 있고, 디스크에는 없는 이름
    nfc_name = unicodedata.normalize("NFC", "한글 대상 문서")
    tracked = {
        unicodedata.normalize("NFC", str((FIXTURES / f"{nfc_name}.md").relative_to(REPO_ROOT)))
    }
    links, _images = check_links.check_file(md, tracked)
    assert links == [], f"NFD 경로가 NFC 추적 항목과 연결되지 않았다: {links}"


if __name__ == "__main__":
    tests = [
        test_code_fence_links_ignored,
        test_html_img_broken_reported,
        test_markdown_image_not_false_positive,
        test_markdown_image_broken_still_reported,
        test_nfd_path_matches_nfc_tracked_entry,
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
