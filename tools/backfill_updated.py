#!/usr/bin/env python3
"""updated 필드가 없는 .md 파일에 마지막 git 커밋 날짜를 삽입"""
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

fixed = 0
for md in sorted(DOCS_DIR.rglob("*.md")):
    content = md.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(content)
    if not m:
        continue
    fm = m.group(1)
    if re.search(r"^updated\s*:", fm, re.MULTILINE):
        continue

    # git log date
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=format:%Y-%m-%d", "--", str(md)],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    git_date = result.stdout.strip() or "2026-08-07"

    # 두 번째 --- 직전에 삽입
    close = m.end()
    insert_pos = content.rfind("\n---", m.start(), close) + 1
    new_content = content[:insert_pos] + f"updated: {git_date}\n" + content[insert_pos:]
    md.write_text(new_content, encoding="utf-8")
    fixed += 1

print(f"완료: {fixed}개 파일 updated 백필")
