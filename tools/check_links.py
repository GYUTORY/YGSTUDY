#!/usr/bin/env python3
"""
내부 링크 검사 스크립트.

Develop/ 하위 .md 파일 + 루트 INDEX.md 의 상대 링크가
실제 파일을 가리키는지 확인합니다.
외부 URL(http/https)과 앵커(#)는 무시합니다.

CI 에서 실행: python3 tools/check_links.py [--strict]
  --strict: 깨진 링크 발견 시 exit code 1 반환
"""

import argparse
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"

# HTML img src 패턴
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')


def _git_tracked_files() -> set[str]:
    """git ls-files 로 추적 중인 파일 목록(NFC 정규화)을 반환."""
    try:
        out = subprocess.check_output(
            ['git', 'ls-files'], cwd=REPO_ROOT, text=True
        )
        return {unicodedata.normalize('NFC', p.strip()) for p in out.splitlines()}
    except Exception:
        return set()


def _strip_code_blocks(text: str) -> str:
    """코드 펜스(``` / ~~~)와 인라인 백틱을 공백으로 치환."""
    # 펜스 블록 (``` ... ``` 또는 ~~~ ... ~~~)
    text = re.sub(r'```[\s\S]*?```', lambda m: ' ' * len(m.group()), text)
    text = re.sub(r'~~~[\s\S]*?~~~', lambda m: ' ' * len(m.group()), text)
    # 인라인 백틱
    text = re.sub(r'`[^`]+`', lambda m: ' ' * len(m.group()), text)
    return text


def _extract_md_links(text: str) -> list[str]:
    """[text](url) 형식 링크를 추출. 괄호 깊이 균형 처리."""
    results = []
    i = 0
    while i < len(text):
        # '](' 를 찾는다
        bracket = text.find('](', i)
        if bracket == -1:
            break
        # 괄호 깊이 추적
        depth = 1
        j = bracket + 2
        while j < len(text) and depth > 0:
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
            j += 1
        if depth == 0:
            results.append(text[bracket + 2:j - 1])
        i = bracket + 2
    return results


def resolve_link(src: Path, raw_link: str, tracked: set[str]) -> tuple[bool, str] | None:
    """
    링크를 검사.
    반환값: None(스킵), (True, '') 정상, (False, resolved_str) 깨짐
    """
    link = raw_link.split('#')[0].strip()
    if not link:
        return None
    # <경로> 형식의 앵글 브라켓 제거
    if link.startswith('<') and link.endswith('>'):
        link = link[1:-1]
    decoded = urllib.parse.unquote(link)
    if decoded.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
        return None

    if decoded.startswith('/'):
        return None  # MkDocs site root 절대경로 스킵
    else:
        target = (src.parent / decoded).resolve()

    # NFC 정규화 후 git 추적 목록과 대조
    try:
        rel = unicodedata.normalize('NFC', str(target.relative_to(REPO_ROOT)))
    except ValueError:
        rel = unicodedata.normalize('NFC', str(target))

    candidates = [rel]
    if not target.suffix:
        candidates.append(rel + '.md')
        candidates.append(rel.rstrip('/') + '/index.md')
    elif target.suffix == '.md':
        candidates.append(rel)

    # git 목록 우선, 없으면 파일시스템 fallback
    for c in candidates:
        if c in tracked:
            return (True, '')
        if (REPO_ROOT / c).exists():
            return (True, '')

    return (False, rel)


def check_file(md: Path, tracked: set[str]) -> list[tuple[str, str]]:
    """[(링크, 소스_경로)] 형태의 깨진 링크 반환."""
    try:
        content = md.read_text(encoding='utf-8')
    except Exception:
        return []

    clean = _strip_code_blocks(content)
    broken = []

    # Markdown 링크
    for raw in _extract_md_links(clean):
        result = resolve_link(md, raw, tracked)
        if result is not None and not result[0]:
            rel_src = md.relative_to(REPO_ROOT)
            broken.append((raw, str(rel_src)))

    # HTML <img src>
    for m in IMG_RE.finditer(clean):
        raw = m.group(1)
        result = resolve_link(md, raw, tracked)
        if result is not None and not result[0]:
            rel_src = md.relative_to(REPO_ROOT)
            broken.append((raw, str(rel_src)))

    return broken


def check_redirect_maps() -> list[str]:
    """mkdocs.yml redirect_maps 우변(목적지)이 Develop/ 아래 실제 파일인지 확인."""
    mkdocs_yml = REPO_ROOT / 'mkdocs.yml'
    if not mkdocs_yml.exists():
        return []

    try:
        with open(mkdocs_yml, encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception:
        return []

    redirect_maps: dict = {}
    for plugin in (config.get('plugins') or []):
        if isinstance(plugin, dict) and 'redirects' in plugin:
            redirect_maps = plugin['redirects'].get('redirect_maps') or {}
            break

    broken = []
    for src_path, dst_path in redirect_maps.items():
        target = REPO_ROOT / 'Develop' / dst_path
        if not target.exists():
            broken.append(f'  redirect_maps 목적지 없음: {dst_path!r}  (from {src_path!r})')
    return broken


def main():
    parser = argparse.ArgumentParser(description='내부 링크 검사')
    parser.add_argument('--strict', action='store_true', help='깨진 링크 발견 시 exit 1')
    args = parser.parse_args()

    tracked = _git_tracked_files()

    # 검사 대상: Develop/ 전체 + 루트 INDEX.md
    targets: list[Path] = sorted(DOCS_DIR.rglob('*.md'))
    root_index = REPO_ROOT / 'INDEX.md'
    if root_index.exists():
        targets.insert(0, root_index)

    all_broken: list[tuple[str, str]] = []
    for md in targets:
        all_broken.extend(check_file(md, tracked))

    redirect_broken = check_redirect_maps()

    has_error = bool(all_broken) or bool(redirect_broken)

    if not has_error:
        print(f'✓ {len(targets)}개 파일 내부 링크 이상 없음. redirect_maps 목적지 이상 없음.')
        return

    if all_broken:
        print(f'⚠ 깨진 내부 링크 {len(all_broken)}건:\n')
        for link, src in all_broken[:50]:
            print(f'  {src}  →  {link}')
        if len(all_broken) > 50:
            print(f'  ... 외 {len(all_broken) - 50}건')

    if redirect_broken:
        print(f'\n⚠ redirect_maps 목적지 오류 {len(redirect_broken)}건:\n')
        for msg in redirect_broken:
            print(msg)

    if args.strict:
        sys.exit(1)


if __name__ == '__main__':
    main()
