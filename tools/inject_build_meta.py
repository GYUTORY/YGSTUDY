"""
MkDocs hook: 빌드 시점 메타 자동 주입 및 최근 변경 문서 페이지 생성.

1. index.md 의 하드코딩된 '최근 업데이트 YYYY.MM' 을 마지막 git 커밋 날짜로 교체.
2. Develop/최근.md 를 최근 60일 내 변경된 문서 목록으로 자동 생성.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import date


def _last_commit_date():
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=format:%Y.%m"],
            capture_output=True, text=True, check=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        return r.stdout.strip() or date.today().strftime("%Y.%m")
    except Exception:
        return date.today().strftime("%Y.%m")


def _recent_docs(repo_root, docs_dir, limit=60):
    """최근 60일 내 변경된 .md 파일 목록 반환 [(date_str, display_name, rel_path)]"""
    try:
        r = subprocess.run(
            ["git", "log",
             "--pretty=format:DATE:%ad", "--date=short",
             "--name-only", "--diff-filter=AM",
             f"--since={limit} days ago",
             "--", "Develop/"],
            capture_output=True, text=True, check=True, cwd=repo_root
        )
    except Exception:
        return []

    entries = []
    current_date = None
    seen = set()

    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("DATE:"):
            current_date = line[5:]
        elif line.endswith(".md") and current_date:
            rel = line.replace("Develop/", "", 1)
            if rel in seen or rel == "index.md" or rel == "최근.md":
                continue
            seen.add(rel)
            name = Path(rel).stem.replace("_", " ")
            entries.append((current_date, name, rel))

    return entries


def on_pre_build(config, **kwargs):
    docs_dir = config["docs_dir"]
    repo_root = os.path.dirname(docs_dir)
    entries = _recent_docs(repo_root, docs_dir)

    lines = [
        "---\n",
        "title: 최근 변경 문서\n",
        "hide:\n  - toc\n",
        "---\n\n",
        "# 최근 변경 문서\n\n",
        "최근 60일 내 추가·수정된 문서입니다. 빌드 시점에 자동 생성됩니다.\n\n",
    ]

    if entries:
        lines.append("| 날짜 | 문서 |\n")
        lines.append("|------|------|\n")
        for d, name, path in entries[:80]:
            url = path.replace(".md", "/").replace(" ", "%20")
            lines.append(f"| {d} | [{name}]({url}) |\n")
    else:
        lines.append("_(변경 이력 없음 또는 git 정보를 읽을 수 없습니다)_\n")

    recent_path = os.path.join(docs_dir, "최근.md")
    with open(recent_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_path != "index.md":
        return markdown
    last_date = _last_commit_date()
    return re.sub(
        r"최근 업데이트 <strong>[^<]+</strong>",
        f"최근 업데이트 <strong>{last_date}</strong>",
        markdown,
    )
