#!/usr/bin/env python3
"""
프론트매터 필수 필드 검증 스크립트.

각 .md 파일의 YAML 프론트매터에서 title / tags / updated 가 있는지 확인합니다.
CI 에서 실행: python3 tools/check_frontmatter.py [--strict]
  --strict: 위반 파일 발견 시 exit code 1 반환
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"

REQUIRED_FIELDS = ["title", "tags", "updated"]
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

SKIP_DIRS = {"_hub"}


def check_file(md: Path) -> list[str]:
    """누락된 필드 목록 반환. 문제 없으면 []."""
    try:
        content = md.read_text(encoding="utf-8")
    except Exception:
        return []

    m = FRONT_MATTER_RE.match(content)
    if not m:
        return REQUIRED_FIELDS[:]

    fm = m.group(1)
    missing = []
    for field in REQUIRED_FIELDS:
        if not re.search(rf"^{field}\s*:", fm, re.MULTILINE):
            missing.append(field)
    return missing


def main():
    parser = argparse.ArgumentParser(description="프론트매터 필수 필드 검증")
    parser.add_argument("--strict", action="store_true", help="위반 시 exit 1")
    parser.add_argument(
        "--skip-hub", action="store_true", default=True,
        help="_hub/ 디렉토리 건너뜀 (기본값 on)"
    )
    args = parser.parse_args()

    violations: list[tuple[Path, list[str]]] = []

    for md in sorted(DOCS_DIR.rglob("*.md")):
        if args.skip_hub and "_hub" in md.parts:
            continue
        missing = check_file(md)
        if missing:
            violations.append((md, missing))

    if not violations:
        total = sum(1 for _ in DOCS_DIR.rglob("*.md"))
        print(f"✓ 전체 {total}개 문서 프론트매터 이상 없음.")
        return

    print(f"⚠ 프론트매터 위반 {len(violations)}개 파일:\n")

    field_counts: dict[str, int] = {f: 0 for f in REQUIRED_FIELDS}
    for _, missing in violations:
        for f in missing:
            field_counts[f] += 1

    print("  누락 필드별 집계:")
    for field, cnt in field_counts.items():
        if cnt:
            print(f"    {field:12s}: {cnt}건")
    print()

    for md, missing in violations[:30]:
        rel = md.relative_to(REPO_ROOT)
        print(f"  {rel}  →  누락: {', '.join(missing)}")
    if len(violations) > 30:
        print(f"  ... 외 {len(violations) - 30}개")

    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
