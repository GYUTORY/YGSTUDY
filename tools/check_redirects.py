#!/usr/bin/env python3
"""redirect 전수 확인:
1. site/<출발경로>/index.html 존재 여부
2. meta refresh 태그 존재 여부
3. 목적지 site/<도착경로>/index.html 존재 여부
"""
import os, re, sys
from urllib.parse import unquote

# 경로가 '/root/YGSTUDY' 로 박혀 있어 이 저장소를 옮긴 뒤로는 첫 줄에서 죽었다.
# 호출처가 0곳이라 아무도 몰랐다.
YGSTUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.environ.get('SITE_DIR') or os.path.join(YGSTUDY, 'site')

with open(os.path.join(YGSTUDY, 'mkdocs.yml'), encoding='utf-8') as f:
    content = f.read()

m = re.search(r'redirect_maps:\s*\n((?:[ \t]+.+\n)*)', content)
if not m:
    print('redirect_maps 섹션을 찾을 수 없습니다')
    sys.exit(1)

block = m.group(1)
redirect_maps = {}
for line in block.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        continue
    if ':' not in stripped:
        continue
    colon = stripped.index(':')
    src = stripped[:colon].strip().strip('"\'')
    dst = stripped[colon+1:].strip().strip('"\'')
    if src and dst and src.endswith('.md') and dst.endswith('.md'):
        redirect_maps[src] = dst

print(f'redirect_maps 총 {len(redirect_maps)}개')

errors = []
for src, dst in sorted(redirect_maps.items()):
    # 1. 출발지 HTML 존재
    src_html = os.path.join(SITE, src.replace('.md', ''), 'index.html')
    if not os.path.exists(src_html):
        errors.append(f'MISSING SRC: {src.replace(".md","")}/')
        continue

    # 2. meta refresh 태그 존재
    html_content = open(src_html, encoding='utf-8').read()
    rm = re.search(r'http-equiv=["\']refresh["\']', html_content, re.I)
    if not rm:
        errors.append(f'NO REFRESH: {src.replace(".md","")}/')
        continue

    # 3. 목적지 HTML 존재
    dst_html = os.path.join(SITE, dst.replace('.md', ''), 'index.html')
    if not os.path.exists(dst_html):
        errors.append(f'DEAD DST: {src} -> {dst.replace(".md","")}/')

if errors:
    print(f'\n오류 {len(errors)}건:')
    for e in errors:
        print(' ', e)
    sys.exit(1)
else:
    print(f'전수 확인 완료 — 오류 0건')
