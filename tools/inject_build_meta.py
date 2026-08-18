"""
MkDocs hook: 빌드 시점 메타 자동 주입 및 최근 변경 문서 페이지 생성.

1. index.md 의 하드코딩된 '최근 업데이트 YYYY.MM' 을 마지막 git 커밋 날짜로 교체.
2. Develop/최근.md 를 최근 60일 내 변경된 문서 목록으로 자동 생성.
3. index.md 의 <!-- YG_RECENT --> 자리에 최근 문서 카드를 채움.
   대문에서 "무엇이 새로 올라왔는지" 바로 보이게 하는 용도. 하드코딩하면 낡으므로
   반드시 빌드 시점에 생성한다.
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


_FM_TITLE_RE = re.compile(r"^title\s*:\s*(.+?)\s*$", re.MULTILINE)

# 최근 목록에서 제외할 메타 페이지 (문서가 아니라 사이트 장치)
_META_PAGES = {"index.md", "최근.md", "404.md", "tags.md", "todo.md"}


def _is_generated(abs_path):
    """tools/section_index.py 가 빌드마다 다시 만드는 페이지인가."""
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return "AUTO-SECTION-INDEX" in f.read(500)
    except Exception:
        return False


def _doc_title(abs_path, fallback):
    """프론트매터 title 을 우선 사용. 없으면 파일명 기반 fallback."""
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            head = f.read(1500)
    except Exception:
        return fallback
    if not head.startswith("---"):
        return fallback
    end = head.find("\n---", 3)
    if end == -1:
        return fallback
    m = _FM_TITLE_RE.search(head[3:end])
    if not m:
        return fallback
    return m.group(1).strip().strip('"').strip("'") or fallback


def _doc_url(rel_path):
    """Develop 기준 상대 경로를 사이트 URL 조각으로 변환.

    index.md(사이트 루트)에 직접 써넣는 raw HTML 전용이다. 루트 기준이라
    디렉터리형 경로가 그대로 맞다.
    """
    if rel_path.endswith("/index.md"):
        base = rel_path[: -len("index.md")]
    elif rel_path.endswith(".md"):
        base = rel_path[: -len(".md")] + "/"
    else:
        base = rel_path
    return base.replace(" ", "%20")


def _doc_md_link(rel_path):
    """마크다운 링크의 destination 을 만든다.

    디렉터리형 URL(`AI/X/Y/`)을 마크다운에 쓰면 mkdocs 가 내부 문서 링크로 인식하지
    못해 그대로 두고, 결과적으로 그 페이지 기준 상대경로로 풀려 전부 404가 된다
    (`/최근/AI/X/Y/`). `.md` 경로로 줘야 mkdocs 가 올바른 URL 로 바꿔준다.
    공백이 있는 경로는 <> 로 감싸야 파서가 끊어 읽지 않는다.
    """
    return f"<{rel_path}>" if " " in rel_path else rel_path


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
            # 메타 페이지는 "최근에 쓴 글"이 아니다. 404·태그·todo 가 목록에 섞이면
            # 새 글을 보러 온 사람에게 노이즈가 된다.
            # rel 은 'Backend/Caching/index.md' 같은 전체 경로인데 _META_PAGES 는
            # 파일명 집합이라, 이 비교는 사이트 루트 index.md 하나에만 걸렸다.
            # 하위 섹션 인덱스는 전부 통과해서 "Caching 전체 보기" 같은 자동 생성
            # 목록 페이지가 최근 글에 올라왔다.
            #
            # 파일명(basename)으로 거르면 사람이 직접 쓴 섹션 랜딩까지 날아간다.
            # 자동 생성물에만 들어가는 마커를 보고 판단한다.
            if rel in seen or os.path.basename(rel) in _META_PAGES:
                continue
            seen.add(rel)
            abs_path = os.path.join(docs_dir, rel)
            if os.path.basename(rel) == "index.md" and _is_generated(abs_path):
                continue
            # 이후 커밋에서 삭제·이동된 문서는 목록에 남기지 않는다(죽은 링크 방지).
            if not os.path.isfile(abs_path):
                continue
            name = _doc_title(abs_path, Path(rel).stem.replace("_", " "))
            entries.append((current_date, name, rel))

    return entries


# on_pre_build 에서 계산해 on_page_markdown 이 재사용한다(git 호출 1회로 끝내기 위함).
_recent_cache = []


def on_pre_build(config, **kwargs):
    global _recent_cache
    docs_dir = config["docs_dir"]
    repo_root = os.path.dirname(docs_dir)
    entries = _recent_docs(repo_root, docs_dir)
    _recent_cache = entries

    # tags·updated 는 check_frontmatter.py 가 요구하는 필수 필드다.
    # 생성 파일이라고 빼면 검증이 매번 실패한다.
    lines = [
        "---\n",
        "title: 최근 변경 문서\n",
        "tags: []\n",
        f"updated: {date.today().isoformat()}\n",
        "hide:\n  - toc\n",
        "---\n\n",
        "# 최근 변경 문서\n\n",
        "최근 60일 내 추가·수정된 문서입니다. 빌드 시점에 자동 생성됩니다.\n\n",
    ]

    if entries:
        lines.append("| 날짜 | 문서 |\n")
        lines.append("|------|------|\n")
        for d, name, path in entries[:80]:
            lines.append(f"| {d} | [{name}]({_doc_md_link(path)}) |\n")
    else:
        lines.append("_(변경 이력 없음 또는 git 정보를 읽을 수 없습니다)_\n")

    recent_path = os.path.join(docs_dir, "최근.md")
    with open(recent_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


_RECENT_MARKER_RE = re.compile(r"<!--\s*YG_RECENT:.*?-->", re.DOTALL)

# 최상위 디렉터리명 → 카드에 붙일 라벨
_CAT_LABEL = {
    "_hub": "주제별 가이드",
    "DataBase": "Database",
}


def _recent_cards_html(entries, limit=6):
    if not entries:
        return '<p class="yg-empty">최근 변경 이력을 읽을 수 없습니다.</p>'
    out = ['<div class="yg-series-grid">']
    for d, name, rel in entries[:limit]:
        top = rel.split("/")[0]
        label = _CAT_LABEL.get(top, top)
        out.append(
            f'  <a class="yg-series" href="{_doc_url(rel)}">\n'
            f'    <div class="yg-series-body">\n'
            f'      <span class="yg-series-tag">{label} · {d}</span>\n'
            f"      <h3>{name}</h3>\n"
            f"    </div>\n"
            f"  </a>"
        )
    out.append("</div>")
    return "\n".join(out)


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_path != "index.md":
        return markdown
    last_date = _last_commit_date()
    markdown = re.sub(
        r"최근 업데이트 <strong>[^<]+</strong>",
        f"최근 업데이트 <strong>{last_date}</strong>",
        markdown,
    )
    return _RECENT_MARKER_RE.sub(
        lambda _: _recent_cards_html(_recent_cache), markdown, count=1
    )
