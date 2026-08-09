"""
MkDocs hook: 최상위 섹션마다 랜딩 페이지(index.md)를 빌드 시점에 생성한다.

왜: navigation.indexes 가 켜져 있는데 섹션에 index.md 가 없어서 `/AI/`, `/OS/` 같은
주소가 전부 404였다. 사이드바에서 섹션을 눌러도 펼쳐지기만 하고 "이 주제에 뭐가
있는지" 한눈에 볼 페이지가 없었다.

하드코딩하지 않는 이유는 최근.md 와 같다 — 문서가 늘고 줄 때마다 손으로 고칠 수
없고, 결국 낡아서 거짓말이 된다.
"""

import os
import re

# 섹션별 한 줄 설명. 없으면 이름만 쓴다.
BLURB = {
    "AI": "Claude·Gemini·GPT 같은 모델과 Claude Code·Cursor 같은 도구, 그리고 LLM·RAG·MCP 개념.",
    "Language": "Java·JavaScript·TypeScript·Go·Rust·Python 의 문법과 런타임 동작.",
    "Framework": "Spring 과 Node 계열 프레임워크의 구조, 설정, 운영.",
    "Backend": "API 설계, 인증, 캐싱, 메시징, 로깅처럼 서버를 굴리는 데 필요한 것들.",
    "Architecture": "MSA, DDD, 디자인 패턴, 그리고 시스템을 나누고 붙이는 기준.",
    "Cloud": "AWS 와 GCP 의 컴퓨트·네트워크·스토리지·보안 서비스.",
    "DevOps": "쿠버네티스, 도커, CI/CD, IaC, 리눅스, 모니터링.",
    "Network": "OSI 7계층, HTTP/TLS, TCP, DNS, 프록시.",
    "DataBase": "RDBMS 와 NoSQL, 인덱스와 트랜잭션, 데이터 표현.",
    "Algorithm": "탐색·정렬·동적 계획법 같은 기본기.",
    "Security": "인증·인가, 암호화, 웹 취약점, 공급망과 제로트러스트.",
    "WebServer": "Nginx·Caddy 설정과 리버스 프록시 운영.",
    "OS": "프로세스와 스레드, 메모리, 스케줄링.",
    "Frontend": "브라우저 쪽 주제.",
}

SKIP_DIRS = {"assets", "javascripts", "stylesheets", "etc", ".omc", "_hub", "로드맵"}
FM_TITLE = re.compile(r"^title\s*:\s*(.+?)\s*$", re.MULTILINE)


def _title_of(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(1200)
    except Exception:
        return fallback
    if not head.startswith("---"):
        return fallback
    end = head.find("\n---", 3)
    if end == -1:
        return fallback
    m = FM_TITLE.search(head[3:end])
    if not m:
        return fallback
    return m.group(1).strip().strip('"').strip("'") or fallback


def _md_link(rel):
    """마크다운 링크 destination. 공백이 있으면 <> 로 감싼다."""
    return "<%s>" % rel if " " in rel else rel


def on_pre_build(config, **kwargs):
    docs_dir = config["docs_dir"]

    for name in sorted(os.listdir(docs_dir)):
        section = os.path.join(docs_dir, name)
        if not os.path.isdir(section) or name.startswith(".") or name in SKIP_DIRS:
            continue

        index_path = os.path.join(section, "index.md")
        # 사람이 직접 쓴 index.md 가 있으면 건드리지 않는다.
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                if "AUTO-SECTION-INDEX" not in f.read(400):
                    continue

        # 하위 그룹별로 문서를 모은다. 섹션 바로 아래 문서는 "개요"로 묶는다.
        groups = {}
        total = 0
        for root, dirs, files in os.walk(section):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
            mds = [f for f in files if f.endswith(".md") and f != "index.md"]
            if not mds:
                continue
            rel_dir = os.path.relpath(root, section)
            group = "" if rel_dir == "." else rel_dir.split(os.sep)[0]
            for f in sorted(mds):
                rel = os.path.relpath(os.path.join(root, f), section)
                groups.setdefault(group, []).append(
                    (_title_of(os.path.join(root, f), os.path.splitext(f)[0]), rel)
                )
                total += 1

        if not total:
            continue

        lines = [
            "---\n",
            f"title: {name}\n",
            "tags: []\n",
            "hide:\n  - toc\n",
            "---\n\n",
            "<!-- AUTO-SECTION-INDEX: tools/section_index.py 가 빌드마다 다시 만든다. 직접 고치지 말 것. -->\n\n",
            f"# {name}\n\n",
        ]
        if name in BLURB:
            lines.append(BLURB[name] + "\n\n")
        lines.append(f"문서 {total}개.\n\n")

        for group in sorted(groups, key=lambda g: (g == "", g)):
            items = sorted(groups[group], key=lambda x: x[0])
            if group:
                lines.append(f"## {group.replace('_', ' ')}\n\n")
            else:
                lines.append("## 개요\n\n")
            for title, rel in items:
                lines.append(f"- [{title}]({_md_link(rel)})\n")
            lines.append("\n")

        with open(index_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # 만들어만 두면 어디서도 링크되지 않아 고아가 된다.
        # navigation.indexes 가 켜져 있으므로 .pages 의 nav 맨 앞에 index.md 를 물리면
        # 사이드바의 섹션 제목 자체가 이 페이지로 가는 링크가 된다.
        pages_path = os.path.join(section, ".pages")
        if os.path.exists(pages_path):
            with open(pages_path, "r", encoding="utf-8") as f:
                txt = f.read()
            if "index.md" not in txt and "\nnav:" in "\n" + txt:
                txt = txt.replace("nav:\n", "nav:\n  - index.md\n", 1)
                with open(pages_path, "w", encoding="utf-8") as f:
                    f.write(txt)
