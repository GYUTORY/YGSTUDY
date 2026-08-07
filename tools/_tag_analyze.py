import os, re
from collections import Counter

tags = Counter()
for root, dirs, files in os.walk('/root/YGSTUDY/Develop'):
    for f in files:
        if not f.endswith('.md'):
            continue
        try:
            content = open(os.path.join(root, f)).read()
        except Exception:
            continue
        m = re.search(r'^tags:\s*\[(.+?)\]', content, re.MULTILINE)
        if m:
            for t in m.group(1).split(','):
                tags[t.strip()] += 1

print('Top 70:')
for tag, cnt in tags.most_common(70):
    print(f'{cnt:4d} {tag}')
print(f'\nTotal unique: {len(tags)}, used once: {sum(1 for c in tags.values() if c==1)}')
