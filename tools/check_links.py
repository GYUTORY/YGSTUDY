#!/usr/bin/env python3
"""
내부 링크 검사 스크립트.

Develop/ 하위 .md 파일의 상대 링크가 실제 파일을 가리키는지 확인합니다.
외부 URL(http/https)과 앵커(#)는 무시합니다.

CI 에서 실행: python3 tools/check_links.py [--strict]
  --strict: 깨진 링크 발견 시 exit code 1 반환
"""

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"

LINK_RE = re.compile(r'\[(?:[^\[\]]*)\]\(([^)]+)\)')


def resolve_link(src: Path, raw_link: str) -> Path | None:
    """링크를 절대 경로로 변환. 해석 불가능하면 None."""
    link = raw_link.split('#')[0].strip()
    if not link:
        return None
    decoded = urllib.parse.unquote(link)
    if decoded.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
        return None
    if decoded.startswith('/'):
        # 절대 경로 → docs_dir 기준
        return DOCS_DIR / decoded.lstrip('/')
    return (src.parent / decoded).resolve()


def check_file(md: Path) -> list[tuple[str, str]]:
    """[(링크, 소스_경로)] 형태의 깨진 링크 반환."""
    try:
        content = md.read_text(encoding='utf-8')
    except Exception:
        return []

    broken = []
    for m in LINK_RE.finditer(content):
        raw = m.group(1)
        target = resolve_link(md, raw)
        if target is None:
            continue
        # .md 확장자 없이 쓴 경우 보정
        candidates = [target, target.with_suffix('.md')]
        if target.suffix == '':
            candidates.append(target / 'index.md')

        if not any(c.exists() for c in candidates):
            rel_src = md.relative_to(REPO_ROOT)
            broken.append((raw, str(rel_src)))

    return broken


def main():
    parser = argparse.ArgumentParser(description='내부 링크 검사')
    parser.add_argument('--strict', action='store_true', help='깨진 링크 발견 시 exit 1')
    args = parser.parse_args()

    all_broken: list[tuple[str, str]] = []
    for md in sorted(DOCS_DIR.rglob('*.md')):
        all_broken.extend(check_file(md))

    if not all_broken:
        total = sum(1 for _ in DOCS_DIR.rglob('*.md'))
        print(f'✓ {total}개 파일 내부 링크 이상 없음.')
        return

    print(f'⚠ 깨진 내부 링크 {len(all_broken)}건:\n')
    for link, src in all_broken[:50]:
        print(f'  {src}  →  {link}')
    if len(all_broken) > 50:
        print(f'  ... 외 {len(all_broken) - 50}건')

    if args.strict:
        sys.exit(1)


if __name__ == '__main__':
    main()
