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

    # 아래는 전체 경로 키. 같은 이름의 폴더가 여러 곳에 있으면 잎 이름만으로는
    # 어느 설명인지 정할 수 없어(예: Security 는 5곳) 잎 이름 조회를 막아 뒀다.
    # 그래서 각 위치에 맞는 설명을 경로로 직접 지정한다.
    "AI": "Claude·Gemini·GPT 같은 모델과 Claude Code·Cursor 같은 도구, 그리고 LLM·RAG·MCP 개념.",
    "Cloud/AWS/AI": "Bedrock·SageMaker 등 AWS 가 제공하는 AI·머신러닝 서비스.",
    "Network": "OSI 7계층, HTTP/TLS, TCP, DNS, 프록시.",
    "Cloud/AWS/Network": "VPC·Route 53·CloudFront 등 AWS 네트워크 서비스.",
    "Cloud/GCP/Network": "VPC·Cloud DNS·Cloud CDN 등 GCP 네트워크 서비스.",
    "Security": "인증·인가, 암호화, 웹 취약점, 공급망과 제로트러스트.",
    "Backend/Security": "서버 애플리케이션에서 다루는 보안 — 감사 로깅과 접근 통제.",
    "Cloud/AWS/Security": "IAM·KMS·WAF·GuardDuty 등 AWS 보안 서비스.",
    "Cloud/GCP/Security": "IAM·Secret Manager 등 GCP 보안 서비스.",
    "Network/Security": "네트워크 계층의 보안 — TLS, 방화벽, 트래픽 보호.",
}

SECOND_LEVEL = ["Cloud/AWS", "Cloud/GCP", "DevOps/Linux", "DevOps/Kubernetes", "Language/Java", "Language/JavaScript", "Language/TypeScript"]

# 사이드바 레벨 2 제한 지원: depth 1-3 디렉터리에 허브 페이지 자동 생성
# gen_nav.py --write 이전에 단독 실행해 index.md 를 미리 만들어 둔다.
MAX_HUB_DEPTH = 3   # docs_dir 기준 하위 디렉터리 깊이 상한

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


def _label_for(key, leaf_counts):
    """섹션 표시 이름.

    폴더 이름만 쓰면 Backend/Security 와 Cloud/AWS/Security 가 둘 다
    "Security 전체 보기" 가 되어 검색 결과에서 구분이 안 된다(Security 5개,
    Network·Testing 각 3개가 실제로 겹쳐 있었다).
    겹치는 이름에만 바로 위 폴더를 붙인다 — 안 겹치면 그대로 둬서 길어지지 않게.
    """
    parts = key.split("/")
    name = parts[-1]
    if leaf_counts.get(name, 0) > 1 and len(parts) > 1:
        return "%s · %s" % (parts[-2].replace("_", " "), name.replace("_", " "))
    return name.replace("_", " ")


def _build_one(docs_dir, key, counts, leaf_counts=None):
    """key 는 docs_dir 기준 상대 경로. 최상위든 2단계든 같은 처리를 한다."""
    name = key.split("/")[-1]
    label = _label_for(key, leaf_counts or {})
    section = os.path.join(docs_dir, *key.split("/"))
    if not os.path.isdir(section):
        return
    if True:  # 들여쓰기 유지용

        index_path = os.path.join(section, "index.md")
        # 사람이 직접 쓴 index.md 가 있으면 건드리지 않는다.
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                if "AUTO-SECTION-INDEX" not in f.read(400):
                    return

        # 하위 그룹별로 문서를 모은다. 섹션 바로 아래 문서는 "개요"로 묶는다.
        groups = {}
        total = 0
        for root, dirs, files in os.walk(section):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
            mds = [f for f in files if f.endswith(".md") and f not in ("index.md", "README.md")]
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

        counts[key] = total
        if not total:
            return

        lines = [
            "---\n",
            f"title: {label} 전체 보기\n",
            "tags: []\n",
            "hide:\n  - toc\n",
            "---\n\n",
            "<!-- AUTO-SECTION-INDEX: tools/section_index.py 가 빌드마다 다시 만든다. 직접 고치지 말 것. -->\n\n",
            f"# {label} 전체 보기\n\n",
        ]
        # BLURB 를 잎 이름으로만 찾으면 Backend/Security(문서 1개)에도
        # Cloud/AWS/Security 용 설명이 그대로 붙는다. 전체 경로를 먼저 보고,
        # 이름이 겹치지 않을 때만 잎 이름으로 떨어진다.
        blurb = BLURB.get(key)
        if blurb is None and leaf_counts.get(name, 0) <= 1:
            blurb = BLURB.get(name)
        if blurb:
            lines.append(blurb + "\n\n")
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


def _collect_keys(docs_dir, max_depth=MAX_HUB_DEPTH):
    """docs_dir 아래 depth 1~max_depth 의 모든 디렉터리 키를 모은다."""
    keys = []

    def _scan(rel_parts):
        if len(rel_parts) > max_depth:
            return
        full = os.path.join(docs_dir, *rel_parts) if rel_parts else docs_dir
        try:
            entries = sorted(os.listdir(full))
        except OSError:
            return
        for e in entries:
            if e.startswith(".") or e in SKIP_DIRS:
                continue
            child = os.path.join(full, e)
            if not os.path.isdir(child):
                continue
            child_key = "/".join(rel_parts + [e])
            keys.append(child_key)
            _scan(rel_parts + [e])

    _scan([])
    return keys


def _leaf_counts(keys):
    """폴더 이름이 트리 전체에서 몇 번 나오는지 — 제목 중복 판정용."""
    c = {}
    for k in keys:
        leaf = k.split("/")[-1]
        c[leaf] = c.get(leaf, 0) + 1
    return c


def on_pre_build(config, **kwargs):
    docs_dir = config["docs_dir"]
    counts = {}

    keys = _collect_keys(docs_dir)
    leaf_counts = _leaf_counts(keys)
    for key in keys:
        _build_one(docs_dir, key, counts, leaf_counts)

    # 홈 카드가 읽을 단일 소스. 카드와 섹션 페이지가 같은 값을 쓰게 해서
    # "카드는 74개인데 들어가면 64개" 같은 불일치를 원천 차단한다.
    import json
    with open(os.path.join(docs_dir, "section_counts.json"), "w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False)


if __name__ == "__main__":
    import json
    import sys
    docs_dir = sys.argv[1] if len(sys.argv) > 1 else "Develop"
    counts = {}
    keys = _collect_keys(docs_dir)
    leaf_counts = _leaf_counts(keys)
    for key in keys:
        _build_one(docs_dir, key, counts, leaf_counts)
    print(f"허브 페이지 생성 완료: {len(counts)}개 섹션")
