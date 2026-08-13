#!/usr/bin/env python3
"""빌드 산출물의 이미지/에셋 링크가 실제로 존재하는지 검사한다.

소스 기준 검사(check_links.py)로는 못 잡는 부류를 잡는다:
  · raw <img src="..."> 는 mkdocs 가 경로를 재작성하지 않는다.
    use_directory_urls=true 라 출력이 한 단계 깊어지므로 ../ 가 하나 더 필요하다.
  · <figure> 안의 마크다운은 markdown="1" 없으면 파싱되지 않고 그대로 출력된다.

사용: python3 tools/check_built_assets.py <site_dir> [--strict]
"""
import os, re, sys, posixpath, urllib.parse

IMG = re.compile(r'<img[^>]+src="([^"]+)"')
SKIP = ('http://', 'https://', 'data:', '//')

def main():
    site = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'site'
    strict = '--strict' in sys.argv
    if not os.path.isdir(site):
        print(f'✗ 산출물 디렉터리 없음: {site} — mkdocs build 를 먼저 실행하세요')
        sys.exit(2)

    miss, total = [], 0
    for dp, _, fs in os.walk(site):
        for f in fs:
            if not f.endswith('.html'):
                continue
            page = os.path.join(dp, f)
            html = open(page, encoding='utf-8', errors='replace').read()
            for src in IMG.findall(html):
                if src.startswith(SKIP):
                    continue
                total += 1
                target = posixpath.normpath(posixpath.join(dp, urllib.parse.unquote(src)))
                if not os.path.exists(target):
                    miss.append((os.path.relpath(page, site), src))

    if not miss:
        print(f'✓ 산출물 이미지 {total}개 모두 정상.')
        return

    print(f'⚠ 깨진 이미지 {len(miss)}건 / 전체 {total}개:\n')
    for page, src in miss[:40]:
        print(f'  {page}  →  {src}')
    if len(miss) > 40:
        print(f'  ... 외 {len(miss) - 40}건')
    print('\n  raw <img> 는 mkdocs 가 경로를 고쳐주지 않습니다.')
    print('  마크다운 ![](...) 로 바꾸거나, ../ 를 한 단계 더 붙이세요.')
    print('  <figure> 안에 마크다운을 쓸 때는 <figure markdown="1"> 이어야 합니다.')
    if strict:
        sys.exit(1)

if __name__ == '__main__':
    main()
