#!/usr/bin/env python3
import re

with open('/root/YGSTUDY/site/index.html', encoding='utf-8') as f:
    content = f.read()

sections = ['_hub', 'Language', 'Framework', 'AI', 'Backend', 'Architecture',
            'Cloud', 'DevOps', 'Network', 'DataBase', 'Algorithm',
            'Security', 'WebServer', 'OS', 'Frontend']

missing = []
for s in sections:
    pattern = re.escape(s)
    found = bool(re.search(pattern, content))
    status = 'OK' if found else 'MISSING'
    if not found:
        missing.append(s)
    print(f'  {status}: {s}')

links = len(re.findall(r'md-nav__link', content))
print(f'\nmd-nav__link 총 {links}개 (기준 1375개)')

if missing:
    print(f'\n누락 섹션: {missing}')
else:
    print('\n14개 섹션 모두 확인됨')
