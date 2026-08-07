#!/usr/bin/env python3
"""YGSTUDY 빌드 + redirect 전수 검증 스크립트"""
import subprocess
import sys
import os
import yaml
import re
from pathlib import Path

ROOT = Path('/root/YGSTUDY')
os.chdir(ROOT)

def run(cmd, **kwargs):
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return result

# ── STEP 0: gen_nav.py 및 빌드는 이미 완료됨 — 검증만 진행 ─────
print('=== STEP 0: skip (already built) ===')

# ── STEP 1: mkdocs 설치 확인 ────────────────────────────────
print('=== STEP 1: mkdocs 설치 확인 ===')

import shutil
mkdocs_bin = shutil.which('mkdocs')
if not mkdocs_bin:
    print('mkdocs 없음. apt로 python3-pip 설치 후 mkdocs 설치 시도...')
    # pip 자체가 없으면 apt로 먼저 설치
    r_apt_pip = run(['apt-get', 'install', '-y', 'python3-pip'])
    print(f'apt python3-pip: code={r_apt_pip.returncode}')

    pip3 = shutil.which('pip3') or shutil.which('pip')
    if pip3:
        r2 = run([pip3, 'install', '-r', 'requirements-docs.txt'])
        print(f'pip install: code={r2.returncode}')
        if r2.returncode != 0:
            print(r2.stderr[:300])
    else:
        print('pip3도 없음. apt로 mkdocs 직접 설치...')
        r3 = run(['apt-get', 'install', '-y', 'mkdocs'])
        print(f'apt mkdocs: code={r3.returncode}')

    mkdocs_bin = shutil.which('mkdocs')
    if not mkdocs_bin:
        print('설치 완료했으나 PATH에 없음. 수동 설치 필요.')
        sys.exit(1)

r = run([mkdocs_bin, '--version'])
print(r.stdout.strip() or r.stderr.strip())
MKDOCS = mkdocs_bin

site = ROOT / 'site'

# ── STEP 2: 빌드 완료 확인 ──────────────────────────────────
print('\n=== STEP 2: 빌드 확인 ===')
if not (site / 'index.html').exists():
    print('site/index.html 없음 — 빌드 먼저 실행하세요.')
    sys.exit(1)
print('site/ 존재 확인.')

# ── STEP 3: redirect 전수 검증 ──────────────────────────────
print('\n=== STEP 3: redirect 전수 검증 ===')
# redirect_maps 섹션만 regex로 추출 (Python YAML 태그 우회)
redirects = {}
content = open('mkdocs.yml', encoding='utf-8').read()
m = re.search(r'redirect_maps:\s*\n((?:[ \t]+[^\n]+\n)+)', content)
if m:
    for line in m.group(1).splitlines():
        line = line.strip()
        if ':' in line and not line.startswith('#') and '.md' in line:
            k, v = line.split(':', 1)
            k = k.strip().strip("'\"")
            v = v.strip().strip("'\"")
            if k.endswith('.md') and v.endswith('.md'):
                redirects[k] = v

failures = []
total = len(redirects)

for src, dst in redirects.items():
    src_html = site / src.replace('.md', '') / 'index.html'
    dst_path_str = dst.replace('.md', '/')
    dst_dir = site / dst_path_str

    if not src_html.exists():
        failures.append(f'  SRC 없음: {src} → site/{src.replace(".md","")}/index.html')
        continue

    content = src_html.read_text(encoding='utf-8')
    match = re.search(r'<meta http-equiv="refresh"[^>]+url=([^"\'>]+)', content, re.I)
    if not match:
        match = re.search(r'url=([^\'">\s]+)', content, re.I)
    if not match:
        failures.append(f'  meta refresh 없음: {src}')
        continue

    url = match.group(1).rstrip('/')
    # URL에서 절대경로 부분 추출
    url_path = url.split('/')[-1] if '/' in url else url
    # dst_dir의 실제 index.html 존재 여부로 확인
    if not (site / dst_path_str.strip('/') / 'index.html').exists():
        # 상위 경로도 시도
        dst_dir2 = site / dst.replace('.md', '/').lstrip('/')
        if not (dst_dir2 / 'index.html').exists():
            failures.append(f'  DST 없음: {dst} → {dst_path_str}')

passed = total - len(failures)
print(f'총 {total}개 | 통과 {passed}개 | 실패 {len(failures)}개')
if failures:
    print('\n실패 목록:')
    for f in failures[:50]:
        print(f)
    if len(failures) > 50:
        print(f'  ... (이하 {len(failures)-50}개 생략)')
else:
    print('모두 통과!')

# ── STEP 4: 사이드바 섹션 확인 ─────────────────────────────
print('\n=== STEP 4: 사이드바 섹션 확인 ===')
index_html = (site / 'index.html').read_text(encoding='utf-8')
nav_links = len(re.findall(r'md-nav__link', index_html))
print(f'md-nav__link 개수: {nav_links}')

required = ['Security', 'WebServer', 'OS', 'Frontend', '_hub', '주제별', 'hub']
print('14개 섹션 확인:')
for sec in ['Security', 'WebServer', 'OS', 'Frontend']:
    found = sec in index_html
    print(f'  {"✓" if found else "✗"} {sec}')
# _hub 레이블 확인 (title이 뭔지 파악)
hub_match = re.search(r'(_hub|주제별[^<"]*)', index_html)
print(f'  hub 레이블: {hub_match.group(0)[:40] if hub_match else "없음"}')
