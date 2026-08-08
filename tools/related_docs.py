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
    # mkdocs 는 프론트매터를 걷어낸 본문을 넘긴다. 여기서 다시 파싱하려 들면 항상 실패한다
    # (이 훅이 오랫동안 아무것도 출력하지 않던 이유다). 메타는 page.meta 에서 읽는다.
    meta = getattr(page, 'meta', None) or {}
    raw_tags = meta.get('tags') or []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    tags = [str(t).strip() for t in raw_tags if str(t).strip()]
    title = str(meta.get('title') or page.title or '').strip()

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

    # 공유 태그가 있는 다른 문서 찾기.
    #
    # 태그를 통제 어휘 65종으로 줄인 뒤로는 태그 1개만 겹치는 문서가 수백 개씩 나온다.
    # 공유 개수만으로 정렬하면 동점이 대량으로 생기고, 그 안에서는 사실상 무작위로 잘린다.
    # 같은 섹션(최상위 디렉터리) 문서를 먼저 놓고, 그다음 제목순으로 확정한다.
    # 제목순은 취향이 아니라 결정성을 위한 것 — 빌드마다 결과가 흔들리면 안 된다.
    current_tags = set(tags)
    section = src.split('/')[0] if '/' in src else ''
    related = []
    for other_src, meta in _doc_meta.items():
        if other_src == src:
            continue
        shared = current_tags & meta['tags']
        if len(shared) >= MIN_SHARED_TAGS:
            other_section = other_src.split('/')[0] if '/' in other_src else ''
            same_section = 1 if (section and other_section == section) else 0
            related.append((len(shared), same_section, meta['title'], meta['url']))

    if not related:
        return markdown

    related.sort(key=lambda x: (-x[0], -x[1], x[2]))
    related = [(s, t, u) for s, _, t, u in related[:MAX_RELATED]]

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


def _url_for(rel_path: str) -> str:
    """use_directory_urls 기준 URL 조각. index.md 는 디렉터리 자체가 된다."""
    if rel_path == 'index.md':
        return ''
    if rel_path.endswith('/index.md'):
        return rel_path[: -len('index.md')]
    if rel_path.endswith('.md'):
        return rel_path[: -len('.md')] + '/'
    return rel_path


def on_files(files, config, **kwargs):
    """페이지 렌더링 전에 전체 문서 메타를 먼저 채운다.

    on_page_markdown 에서만 수집하면 그때까지 처리된 문서만 후보가 된다.
    빌드 순서상 앞쪽 문서는 관련 문서가 비거나 빈약해지고, 결과가 순서에 따라
    달라진다. 여기서 한 번에 모아두면 모든 문서가 같은 후보군을 본다.
    """
    docs_dir = Path(config['docs_dir'])
    for f in files:
        rel = f.src_path
        if not rel.endswith('.md'):
            continue
        try:
            text = (docs_dir / rel).read_text(encoding='utf-8')
        except Exception:
            continue
        m = FM_RE.match(text)
        if not m:
            continue
        fm_body = m.group(1)
        _doc_meta[rel] = {
            'title': _extract_title(fm_body) or Path(rel).stem.replace('_', ' '),
            'tags': set(_extract_tags(fm_body)),
            'url': _url_for(rel),
        }
    return files
