#!/usr/bin/env python3
"""
프론트매터 필수 필드 검증 스크립트.

각 .md 파일의 YAML 프론트매터에서 title / tags / updated 가 있는지 확인하고,
서로 다른 문서가 같은 제목을 쓰고 있지 않은지 본다.
CI 에서 실행: python3 tools/check_frontmatter.py [--strict]
  --strict: 위반 파일 발견 시 exit code 1 반환
"""

import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"

REQUIRED_FIELDS = ["title", "tags", "updated"]
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# 빌드 때 만들어지는 랜딩 페이지들. 사람이 쓰는 문서가 아니라
# updated 같은 필드를 요구할 대상이 아니다(section_index.py 가 생성).
SKIP_DIRS = {"_hub", "_group"}
SKIP_FILES = {"index.md", "todo.md", "404.md"}


# ── 제목 중복 ─────────────────────────────────────────────
# 왜 검사하는가: Loki 문서 2편이 H1 도 frontmatter title 도 "Loki 로그 집계" 로
# 똑같았다. 내용은 수집 구성 / 레이블 설계로 갈리는데 — 겹치는 산문 문장이 0개다 —
# 이름이 같으니 사이드바에도 검색 결과에도 구별할 단서가 없었고,
# Monitoring/index.md 에는 글자까지 동일한 링크가 두 줄 나란히 있었다.
# 나중에 쓴 쪽은 첫 번째가 있는 줄 모르고 만들어졌다. 제목이 같으면 검색해도
# 자기가 쓰려던 글이 이미 있는지 알 수 없기 때문이다.
#
# 게이트로 삼을 자격을 먼저 쟀다. 전체 1,165편에 걸린 것이 그 한 쌍뿐이고
# 오탐이 0이었다. 정밀도가 이만하지 않으면 게이트로 만들면 안 된다
# (tools/list_support_claims.py 의 머리말에 왜 그런지 적어 뒀다).
TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)

# 제목이 같아도 되는 문서. 지금은 비어 있다.
# 정말 같아야 한다면 여기 넣고 왜 그런지 한 줄 적을 것 — 비워 두는 편이 기본값이다.
DUP_TITLE_ALLOW: set[str] = set()


def _title(md: Path) -> str | None:
    try:
        content = md.read_text(encoding="utf-8")
    except Exception:
        return None
    m = FRONT_MATTER_RE.match(content)
    if not m:
        return None
    t = TITLE_RE.search(m.group(1))
    return t.group(1).strip() if t else None


def _norm_title(t: str) -> str:
    """대소문자·공백·문장부호를 걷어낸 비교용 형태.

    자모 분리(NFD)로 저장된 한글이 섞여 있어도 같은 제목으로 잡히게 NFC 로 맞춘다
    — macOS 에서 만든 파일이 그렇게 들어온 적이 있다.
    """
    return re.sub(r"[^a-z0-9가-힣]", "", unicodedata.normalize("NFC", t).lower())


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
        help="자동 생성 디렉터리(_hub·_group) 건너뜀 (기본값 on)"
    )
    args = parser.parse_args()

    violations: list[tuple[Path, list[str]]] = []
    by_title: dict[str, list[Path]] = defaultdict(list)

    for md in sorted(DOCS_DIR.rglob("*.md")):
        # SKIP_DIRS 는 선언만 돼 있고 정작 "_hub" 가 하드코딩돼 있어서,
        # 목록에 디렉터리를 더해도 아무 일이 없었다. 선언을 실제로 쓴다.
        if args.skip_hub and SKIP_DIRS.intersection(md.parts):
            continue
        if md.name in SKIP_FILES:
            continue
        missing = check_file(md)
        if missing:
            violations.append((md, missing))
        t = _title(md)
        if t and _norm_title(t) not in DUP_TITLE_ALLOW:
            by_title[_norm_title(t)].append(md)

    dups = [ps for ps in by_title.values() if len(ps) > 1]

    if dups:
        print(f"⚠ 제목이 같은 문서 {len(dups)}쌍:\n")
        for ps in dups:
            print(f"  '{_title(ps[0])}'")
            for p in ps:
                print(f"      {p.relative_to(REPO_ROOT)}")
        print(
            "\n  같은 제목이면 사이드바에도 검색 결과에도 둘을 구별할 단서가 없다.\n"
            "  내용이 겹치면 한쪽으로 합치고, 겹치지 않으면 제목을 각자 무엇을 다루는지로 바꿀 것.\n"
        )

    if not violations and not dups:
        total = sum(1 for _ in DOCS_DIR.rglob("*.md"))
        print(f"✓ 전체 {total}개 문서 프론트매터 이상 없음 (제목 중복 0쌍).")
        return

    if not violations:
        if args.strict:
            sys.exit(1)
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
