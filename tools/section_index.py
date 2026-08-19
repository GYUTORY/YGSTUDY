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

# 랜딩 페이지 제목과 그 안의 그룹 제목은 폴더 이름이 아니라 사이드바 라벨을 쓴다.
# 누른 이름과 도착한 페이지 이름이 다르면 잘못 눌렀나 싶어진다.
# 예전엔 여기에 짝을 손으로 적어 뒀는데, 사이드바를 고칠 때마다 같이 고쳐야 해서
# 넷만 맞고 다섯은 어긋나 있었다('IaC' 로 들어간 페이지 안에 '## Infrastructure as
# Code' 가 있는 식). 지금은 .pages 에서 직접 읽는다 — 어긋날 수가 없다.
PAGES_TITLE = re.compile(r"^title\s*:\s*(.+?)\s*$", re.MULTILINE)


def _pages_title(pages_path):
    """<dir>/.pages 의 title: (사이드바가 그 폴더에 붙이는 이름)"""
    try:
        with open(pages_path, "r", encoding="utf-8") as f:
            m = PAGES_TITLE.search(f.read())
    except OSError:
        return None
    return m.group(1).strip().strip('"').strip("'") if m else None


def _pages_child_label(pages_path, folder):
    """부모 .pages 의 nav 가 이 폴더에 붙인 라벨.  '- IaC: Infrastructure_as_Code'"""
    try:
        with open(pages_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    for raw in lines:
        item = raw.strip()
        if not item.startswith("- "):
            continue
        item = item[2:].strip()
        if ": " in item:
            label, target = item.split(": ", 1)
            if target.strip() == folder:
                return label.strip()
        elif item == folder:
            return None      # 라벨 없이 폴더명 그대로 — 기본 규칙에 맡긴다
    return None


def _sidebar_label(docs_dir, key):
    """docs_dir 기준 경로가 사이드바에 나타나는 이름."""
    parts = key.split("/")
    own = _pages_title(os.path.join(docs_dir, *parts, ".pages"))
    if own:
        return own
    if len(parts) > 1:
        parent = _pages_child_label(
            os.path.join(docs_dir, *parts[:-1], ".pages"), parts[-1])
        if parent:
            return parent
    return parts[-1].replace("_", " ")

# 사이드바 레벨 2 제한 지원: depth 1-3 디렉터리에 허브 페이지 자동 생성
# gen_nav.py --write 이전에 단독 실행해 index.md 를 미리 만들어 둔다.
MAX_HUB_DEPTH = 3   # docs_dir 기준 하위 디렉터리 깊이 상한

# 로드맵은 여기서 뺐다. 허브가 없으면 사이드바에서 '로드맵' 을 눌렀을 때
# 목록이 아니라 첫 문서(AWS 실무 입문 15선)로 바로 떨어진다.
# _hub 는 _build_hub_landing 이 따로 만들므로 그대로 건너뛴다.
SKIP_DIRS = {"assets", "javascripts", "stylesheets", "etc", ".omc", "_hub", "_group"}
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


def _label_for(docs_dir, key, leaf_counts):
    """섹션 표시 이름.

    폴더 이름만 쓰면 Backend/Security 와 Cloud/AWS/Security 가 둘 다
    "Security 전체 보기" 가 되어 검색 결과에서 구분이 안 된다(Security 5개,
    Network·Testing 각 3개가 실제로 겹쳐 있었다).
    겹치는 이름에만 바로 위 폴더를 붙인다 — 안 겹치면 그대로 둬서 길어지지 않게.
    """
    parts = key.split("/")
    label = _sidebar_label(docs_dir, key)
    if leaf_counts.get(parts[-1], 0) > 1 and len(parts) > 1:
        return "%s · %s" % (parts[-2].replace("_", " "), label)
    return label


def _build_one(docs_dir, key, counts, leaf_counts=None):
    """key 는 docs_dir 기준 상대 경로. 최상위든 2단계든 같은 처리를 한다."""
    name = key.split("/")[-1]
    label = _label_for(docs_dir, key, leaf_counts or {})
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

        # 그룹 제목도 사이드바가 쓰는 이름으로. 'IaC' 를 눌러 들어온 페이지 안에
        # '## Infrastructure as Code' 가 있으면 같은 폴더인지 알 수 없다.
        # 정렬도 폴더명이 아니라 보이는 이름으로 한다 — 안 그러면 '개념'(Concepts)이
        # Codex 와 Cursor 사이에 끼어 순서가 아무렇게나 놓인 것처럼 보인다.
        heading = {g: _sidebar_label(docs_dir, key + "/" + g) if g else "개요"
                   for g in groups}
        for group in sorted(groups, key=lambda g: (g == "", heading[g])):
            items = sorted(groups[group], key=lambda x: x[0])
            lines.append("## %s\n\n" % heading[group])
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
            # nav 항목 '- index.md' 가 이미 있는지를 본다. 문자열 포함으로 보면
            # 'RDBMS에서의 index.md' 같은 파일명에 걸려 이미 있다고 착각한다.
            # 실제로 DataBase/RDBMS 가 이 오탐으로 index.md 를 못 받아, 사이드바에서
            # 'RDBMS' 를 누르면 섹션 목록이 아니라 첫 문서(부분_인덱스)로 갔다.
            has_index = any(
                line.strip() in ("- index.md", "- index.md:")
                for line in txt.splitlines()
            )
            if not has_index and "\nnav:" in "\n" + txt:
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


def _build_hub_landing(docs_dir):
    """_hub/index.md — 주제별 가이드 목록."""
    d = os.path.join(docs_dir, "_hub")
    if not os.path.isdir(d):
        return
    items = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md") or f == "index.md":
            continue
        path = os.path.join(d, f)
        title = _title_of(path, os.path.splitext(f)[0])
        blurb = ""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                body = fh.read(1600).split("---", 2)[-1]
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith(("#", "<!--", "!!!", "|", "-")):
                    blurb = line[:80]
                    break
        except Exception:
            pass
        items.append((title, f, blurb))
    if not items:
        return

    out = [
        "---\n", "title: 주제별 가이드\n", "tags: []\n", "hide:\n  - toc\n", "---\n\n",
        "<!-- AUTO-SECTION-INDEX: tools/section_index.py 가 빌드마다 다시 만든다. 직접 고치지 말 것. -->\n\n",
        "# 주제별 가이드\n\n",
        "메뉴는 문서를 폴더 하나에만 놓는다. 실제로 하나를 이해하려면 여러 폴더를 오가야 한다.\n",
        "아래 가이드는 그 흩어진 문서들을 읽는 순서대로 다시 엮은 것이다.\n\n",
    ]
    for title, f, blurb in items:
        out.append("- [%s](%s)%s\n" % (title, _md_link(f), (" — " + blurb) if blurb else ""))
    out.append("\n")
    with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
        fh.writelines(out)


# 최상위 메뉴의 묶음. Develop/.pages 의 nav 와 짝을 이룬다.
#
# 왜 필요한가: 홈의 'Backend' 카드가 /Framework/ 로 갔다. 거기에 Kafka 도
# 인증도 없다 — 그것들은 형제 폴더인 Backend/ 소속이다. 누른 이름과 도착한
# 페이지 이름이 달라(Backend -> "Framework 전체 보기") 잘못 눌렀나 싶어진다.
# 'Infra' 카드는 부제에 Kubernetes·Docker 를 적어 놓고 Cloud/ 로 보냈는데
# 그 둘은 DevOps/ 에 있다. 묶음을 대표하는 페이지가 없어서 생긴 일이라
# 여기서 만든다.
GROUPS = {
    "backend": ("Backend", "서버를 만들고 굴리는 일 — 프레임워크, API 와 인증, 구조 설계.",
                [("Framework", "Framework"), ("Backend", "API·인증·메시징"), ("Architecture", "Architecture")]),
    "infra": ("Infra", "돌아가게 만드는 쪽 — 클라우드, 컨테이너와 배포, 웹 서버.",
              [("Cloud", "Cloud"), ("DevOps", "DevOps"), ("WebServer", "WebServer")]),
    "cs": ("CS", "밑에 깔린 것들 — 네트워크, 운영체제, 알고리즘, 보안.",
           [("Network", "Network"), ("OS", "OS"), ("Algorithm", "Algorithm"), ("Security", "Security")]),
}


def _build_groups(docs_dir, counts):
    """묶음 랜딩 페이지 — Develop/_group/{key}.md"""
    d = os.path.join(docs_dir, "_group")
    os.makedirs(d, exist_ok=True)
    # 참고: 묶음 랜딩 페이지의 브레드크럼은 "홈 › group" 으로 나온다(_group 폴더 이름).
    # _group/.pages 에 title 을 줘도 안 먹는다 — awesome-pages 는 nav 에서 걸러낸
    # 섹션의 title 을 설정하지 않고(navigation.py:70 _nav -> 71 _process_child_sections),
    # _group 은 Develop/.pages 의 nav 에 없어서 걸러지는 쪽이다.
    for key, (title, blurb, members) in GROUPS.items():
        total = sum(counts.get(m, 0) for m, _ in members)
        lines = [
            "---\n", f"title: {title}\n", "tags: []\n", "hide:\n  - toc\n", "---\n\n",
            "<!-- AUTO-SECTION-INDEX: tools/section_index.py 가 빌드마다 다시 만든다. 직접 고치지 말 것. -->\n\n",
            f"# {title}\n\n", blurb + "\n\n", f"문서 {total}개.\n\n",
        ]
        for name, label in members:
            n = counts.get(name, 0)
            # index.md 까지 적어야 MkDocs 가 실제 문서로 인식해 주소를 다시 쓴다.
            # "../Framework/" 처럼 폴더로만 적으면 그대로 남아서
            # /_group/Framework/ 를 가리키는 죽은 링크가 된다.
            lines.append(f"- [{label}](../{name}/index.md) — 문서 {n}개\n")
        lines.append("\n")
        with open(os.path.join(d, key + ".md"), "w", encoding="utf-8") as f:
            f.writelines(lines)
        counts["group:" + key] = total


def on_pre_build(config, **kwargs):
    docs_dir = config["docs_dir"]
    counts = {}

    keys = _collect_keys(docs_dir)
    leaf_counts = _leaf_counts(keys)
    for key in keys:
        _build_one(docs_dir, key, counts, leaf_counts)

    # 홈 카드가 읽을 단일 소스. 카드와 섹션 페이지가 같은 값을 쓰게 해서
    # "카드는 74개인데 들어가면 64개" 같은 불일치를 원천 차단한다.
    #
    # SKIP_DIRS 의 _hub·로드맵 은 "허브 페이지를 만들지 않는다"는 뜻이지
    # "세지 않는다"는 뜻이 아니다. 둘을 구분하지 않아 홈의 '가이드' 카드만
    # 개수가 비어 `—` 로 남아 있었다(다른 카드는 전부 숫자라 미완성으로 보였다).
    # 허브는 그대로 만들지 않고 개수만 따로 센다.
    for extra in ("_hub", "로드맵"):
        d = os.path.join(docs_dir, extra)
        if not os.path.isdir(d):
            continue
        n = 0
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            n += len([f for f in files if f.endswith(".md") and f not in ("index.md", "README.md")])
        counts[extra] = n

    # 홈 '가이드' 카드가 _hub/ 로 보내는데 거기엔 인덱스가 없어서 404 였다.
    # (_hub 는 SKIP_DIRS 라 위 루프가 허브를 만들지 않는다.)
    # 첫 화면에서 1클릭에 막다른 길이라 여기서 따로 만든다.
    _build_hub_landing(docs_dir)
    _build_groups(docs_dir, counts)

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
