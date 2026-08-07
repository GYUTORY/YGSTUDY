import unicodedata, pathlib
changed = []
for p in pathlib.Path('Develop').rglob('*.md'):
    s = p.read_text(encoding='utf-8')
    n = unicodedata.normalize('NFC', s)
    if s != n:
        p.write_text(n, encoding='utf-8')
        changed.append(str(p))
print(f"NFC 정규화 완료: {len(changed)}개")
for f in changed:
    print(' -', f)
