"""
MkDocs hook: 각 페이지 하단에 동일 태그를 공유하는 "관련 문서" 블록 자동 삽입.

mkdocs.yml 의 hooks 섹션에 추가:
  hooks:
    - tools/related_docs.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

FM_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)
TAGS_RE = re.compile(r'^tags\s*:\s*\[([^\]]+)\]', re.MULTILINE)
TAGS_BLOCK_RE = re.compile(r'^tags\s*:\s*\n((?:\s*-\s*.+\n?)+)', re.MULTILINE)

# 빌드 중 수집된 문서 메타 캐시 {src_path: {title, tags, url}}
_doc_meta: dict[str, dict] = {}

# 관련 문서 최대 표시 수
MAX_RELATED = 5
# 최소 공유 태그 수 (1이면 태그 하나만 같아도 표시)
MIN_SHARED_TAGS = 1


def _extract_tags(fm_body: str) -> list[str]:
    """프론트매터 본문에서 tags 값 추출."""
    # tags: [A, B, C] 인라인 형식
    m = TAGS_RE.search(fm_body)
    if m:
        return [t.strip().strip('"\'') for t in m.group(1).split(',') if t.strip()]
    # tags:\n  - A\n  - B 블록 형식
    m = TAGS_BLOCK_RE.search(fm_body)
    if m:
        return [
            line.strip().lstrip('- ').strip()
            for line in m.group(1).splitlines()
            if line.strip().startswith('-')
        ]
    return []


def _extract_title(fm_body: str) -> str:
    m = re.search(r'^title\s*:\s*(.+)$', fm_body, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else ''


def on_page_markdown(markdown: str, page, **kwargs) -> str:
    """페이지 마크다운 처리 시 메타 수집 + 이전 페이지에 관련 문서 블록 삽입."""
    fm_match = FM_RE.match(markdown)
    if not fm_match:
        return markdown

    fm_body = fm_match.group(1)
    tags = _extract_tags(fm_body)
    title = _extract_title(fm_body) or page.title or ''

    src = page.file.src_path

    # 현재 페이지 메타 저장
    _doc_meta[src] = {
        'title': title,
        'tags': set(tags),
        'url': page.url or src.replace('.md', '/'),
    }

    # 태그 없으면 스킵
    if not tags:
        return markdown

    # 이미 관련 문서 블록이 있으면 스킵 (재빌드 시 중복 방지)
    if '<!-- related-docs -->' in markdown:
        return markdown

    # 공유 태그가 있는 다른 문서 찾기
    current_tags = set(tags)
    related = []
    for other_src, meta in _doc_meta.items():
        if other_src == src:
            continue
        shared = current_tags & meta['tags']
        if len(shared) >= MIN_SHARED_TAGS:
            related.append((len(shared), meta['title'], meta['url']))

    if not related:
        return markdown

    related.sort(key=lambda x: -x[0])
    related = related[:MAX_RELATED]

    block_lines = [
        '\n\n<!-- related-docs -->',
        '---',
        '**관련 문서**',
        '',
    ]
    for _, title_r, url_r in related:
        block_lines.append(f'- [{title_r}]({url_r})')

    return markdown + '\n'.join(block_lines)


def on_pre_build(config, **kwargs):
    """빌드 시작 시 메타 캐시 초기화."""
    _doc_meta.clear()
