#!/usr/bin/env python3
"""YGSTUDY .pages 전면 재생성.

원칙
  1. 파일은 절대 옮기지 않는다 (URL 보존)
  2. 유령 항목(디스크에 없는 nav 엔트리) 제거
  3. 고아 문서(디스크에 있는데 nav에 없는 것) 복구
  4. 상위 디렉터리가 이미 말하고 있는 접두사는 라벨에서 제거
  5. 부제(— 뒤)는 사이드바 라벨에서 떼어낸다 (문서 제목 자체는 그대로)
  6. 문서 1개짜리 디렉터리는 부모로 끌어올려 펼침 단계를 없앤다
  7. 기존 큐레이션 순서는 보존

사용:  python3 gen_nav.py [--write]
"""
import os, re, sys

ROOT = 'Develop'
SKIP_DIRS = {'assets', 'javascripts', 'stylesheets', '.omc', 'etc', 'images',
             'example', 'snippets', 'img'}
WRITE = '--write' in sys.argv

# 사이드바 라벨 길이 목표 (넘으면 부제를 떼어낸다)
LABEL_SOFT_MAX = 20


# ---------------------------------------------------------------- 제목 읽기

def doc_title(path):
    """MkDocs가 실제로 쓰는 제목: frontmatter title > H1 > 파일명."""
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return os.path.basename(path)[:-3]
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if m:
        mm = re.search(r'^title:\s*(.+)$', m.group(1), re.M)
        if mm:
            return mm.group(1).strip().strip('"\'')
    hm = re.search(r'^#\s+(.+)$', text, re.M)
    if hm:
        return hm.group(1).strip()
    return os.path.basename(path)[:-3].replace('_', ' ')


# ---------------------------------------------------------------- 라벨 정리

EXTRA_PREFIXES = {
    'Go': ['Go'], 'Rust': ['Rust'], 'Python': ['Python'], 'Java': ['Java'],
    'Kotlin': ['Kotlin'], 'JavaScript': ['JavaScript', 'JS'],
    'TypeScript': ['TypeScript', 'TS'], 'Node': ['Node.js', 'Node'],
    'Claude_Code': ['Claude Code'], 'Claude': ['Claude'],
    'Cursor': ['Cursor'], 'Gemini': ['Gemini'], 'Grok': ['Grok'],
    'AWS': ['AWS', 'Amazon'], 'GCP': ['GCP', 'Google Cloud'],
    'Nginx': ['Nginx'], 'Caddy': ['Caddy'], 'Apache': ['Apache'],
    'Kubernetes': ['Kubernetes', 'K8s'], 'MSA': ['MSA'], 'Docker': ['Docker'],
    'Linux': ['Linux'], 'DevOps': ['DevOps'], 'NestJS': ['NestJS'],
    'Redis': ['Redis'], 'MongoDB': ['MongoDB'],
    'OMO': ['Online-Merge-Offline', 'OMO'],
    # 'Spring Boot X'에서 'Spring'만 떼면 'Boot X'가 되어 뜻이 깨진다
    'Spring': ['Spring Boot', 'Spring'],
}

# ---- 형제 묶기 ----------------------------------------------------------
# 같은 이름으로 시작하는 형제가 여럿이면 접기 가능한 그룹으로 묶는다.
# (AWS/Containers의 'ECS ...' 29개 같은 경우)
GROUP_MIN = 3

# 그룹 이름이 될 수 없는 말 — 제품명이 아니라 벤더/범용어라 묶으면 뜻이 깨진다
GROUP_BLOCK = {'cloud', 'aws', 'amazon', 'google', 'azure', 'microsoft',
               'apache', 'the', 'a', 'an'}

# 이 말로 시작하게 잘리면 라벨이 문장처럼 깨진다 -> 원래 라벨을 유지
BAD_HEAD = re.compile(
    r'^(vs|and|or|to|for|with|over|under|into|from|by|at|as|on|in|및|와|과)\b',
    re.I)

GROUP_NAME_OK = re.compile(r'^[A-Za-z][A-Za-z0-9.+#/-]*$')

# 최상위 섹션 순서 — 언어/프레임워크 → 백엔드 → 데이터 → 인프라 → 클라우드 → 기타
TOP_ORDER = [
    'index.md', '_hub',
    'Language', 'Algorithm', 'Framework', 'Frontend',
    'Backend', 'Architecture', 'DataBase', 'DataRepresentation',
    'Network', 'Security', 'OS', 'Linux', 'WebServer',
    'DevOps', 'Infra', 'AWS', 'GCP',
    'Git', 'AI',
    'tags.md',
]

# 특정 디렉터리의 자식 순서 지정 (여기 없는 항목은 뒤에 알파벳순)
ORDER_OVERRIDE = {
    # 기초를 실전보다 앞에
    # README.md는 MkDocs가 섹션 index로 매핑하므로 맨 앞에 와야 한다
    'Develop/Framework/Node': ['README.md', '함수형 프로그래밍.md',
                               'Functional_Programming.md'],
    # 개요격 문서를 맨 앞으로
    'Develop/Architecture/MSA': ['Microservices_Architecture.md'],
    'Develop/Architecture/OMO': ['Online_Merge_Offline.md', 'OMO_운영_실무.md'],
    'Develop/AI': [
        'Concepts', 'Claude', 'Claude_Code', 'Cursor', 'GitHub_Copilot',
        'Codex', 'Gemini', 'GPT', 'Grok', 'Qwen', 'DeepSeek', 'Ollama',
        'MCP', 'CodeSight', 'Clawsweeper', 'GBrain', 'OMO',
    ],
}

# 파일명이 디렉터리명과 같아도 '개요'가 아닌 문서
# (Static/static.md 는 개요가 아니라 실무 패턴 문서다)
NO_OVERVIEW = {
    'Develop/Language/Java/객체지향 프로그래밍 (OOP)/Static/static.md',
}

# 디렉터리 자체의 표시 이름
DIR_LABEL = {
    'Develop/AI/Concepts': '개념',
    'Develop/_hub': '주제별 허브',
}

DASHES = [' — ', ' – ', ' - ']


def split_subtitle(label):
    """'Redis — 내부 동작 원리' -> ('Redis', '내부 동작 원리')"""
    for d in DASHES:
        if d in label:
            head, tail = label.split(d, 1)
            return head.strip(), tail.strip()
    return label, None


def strip_prefix(title, ancestors, report=False):
    cands = []
    for a in ancestors:
        cands.extend(EXTRA_PREFIXES.get(a, []))
        cands.append(a.replace('_', ' '))
    cands = sorted({c for c in cands if c}, key=len, reverse=True)
    out = title
    # 접두사는 한 번만 뗀다. 두 번 떼면 'Network Gateway 심화'가
    # (Network, GateWay 둘 다 조상이라) '심화'만 남아 뜻이 사라진다.
    changed = True
    while changed:
        changed = False
        for c in cands:
            for sep in [' — ', ' - ', ': ', ' ']:
                pre = c + sep
                if out.lower().startswith(pre.lower()):
                    rest = out[len(pre):].strip()
                    # 여는 괄호로 시작하면 그 이름의 부연설명을 잘라낸 것이다
                    # ('Online-Merge-Offline (OMO) 아키텍처' -> '(OMO) 아키텍처')
                    if rest and not looks_broken(rest):
                        return (rest, True) if report else rest
            if changed:
                break
    return (out, False) if report else out


# 항상 떼는 상투어 — 어떤 문서에나 붙을 수 있어 변별력이 없다
FILLER_ALWAYS = re.compile(
    r'\s*('
    r'사용법 및 핵심 개념|모델 패밀리 개요와 실무 사용|모델 종합 가이드|'
    r'개요와 실무 사용|종합 가이드|완벽 가이드|실전 가이드|실무 가이드|'
    r'핵심 개념|사용법|모범사례|완벽 정리|총정리|허브'
    r')$'
)

# 라벨이 길 때만 떼는 상투어 — 짧을 땐 남겨두는 편이 구별에 도움이 된다
FILLER_IF_LONG = re.compile(
    r'\s*('
    r'개념과 예제|완전 정복|개념과 활용|상세 비교|한눈에 보기|'
    r'정리와 활용|이해하기|알아보기|다루기|살펴보기'
    r')$'
)


# 잘라내다 이런 꼴이 되면 라벨이 깨진 것이다 -> 자르기 전으로 되돌린다
DANGLING = re.compile(
    r'('
    r'(과|와|및|의|에서|으로|로|이나|에|를|을|은|는|이|가)$'   # 매달린 조사·접속
    r'|[,\-+/&·|]$'                                        # 매달린 기호
    r'|\b(vs|and|or|to|for|with|in|on|의)$'                 # 매달린 영어 접속사
    r')'
)


def looks_broken(label):
    """축약 결과가 말이 안 되는 꼴인지."""
    if not label or len(label.strip()) < 2:
        return True
    s = label.strip()
    if DANGLING.search(s):
        return True
    if BAD_HEAD.match(s):
        return True
    if s[0] in '([{)]}':
        return True
    return False


def safe(new, old):
    """새 후보가 깨졌으면 이전 값을 유지한다."""
    return old if looks_broken(new) else new


def _strip_repeat(label, pattern):
    prev = None
    while prev != label:
        prev = label
        cut = pattern.sub('', label).strip()
        label = safe(cut, prev) if cut else prev
        if label == prev:
            break
    return label


def shorten(label):
    """사이드바 라벨 축약: 부제 -> 괄호 부연 -> 상투어 순으로 떼어낸다."""
    label = _strip_repeat(label, FILLER_ALWAYS)
    # 부제('제목 — 부제')는 사이드바에서 항상 떼어낸다. 본문 제목은 그대로 남는다.
    head, _ = split_subtitle(label)
    if head:
        label = safe(head, label)
    if len(label) > LABEL_SOFT_MAX:
        # 끝에 붙은 괄호 부연 (안쪽에 괄호가 또 있어도 잡도록 greedy)
        label = safe(re.sub(r'\s*\(.*\)\s*$', '', label).strip(), label)
    if len(label) > LABEL_SOFT_MAX:
        # 중간에 낀 괄호 부연:  'SHA (Secure Hash Algorithm) 해시 함수'
        label = safe(re.sub(r'\s*\([^()]*\)\s*', ' ', label).strip(), label)
    if len(label) > LABEL_SOFT_MAX:
        label = _strip_repeat(label, FILLER_IF_LONG)
    return re.sub(r'\s{2,}', ' ', label).strip()


def label_ladder(path, ancestors):
    """가장 짧은 후보부터 원제목까지, 축약 단계별 라벨 후보들.

    형제끼리 겹치지 않는 '가장 짧은' 후보를 고르기 위한 사다리다.
    """
    base, stripped = strip_prefix(doc_title(path), ancestors, report=True)
    first = shorten(base)
    if not stripped:
        # 축약하고 나서야 접두사가 드러나는 경우가 있다
        # ('Online-Merge-Offline (OMO) 아키텍처' -> 'OMO 아키텍처' -> '아키텍처')
        first = strip_prefix(first, ancestors)
    cands = [first]

    # 부제만 떼어낸 중간 단계
    head, tail = split_subtitle(base)
    if tail:
        cands.append(head)
        cands.append(f'{head} — {tail}' if len(base) > len(head) else base)

    # 괄호 부연만 떼어낸 중간 단계
    nop = re.sub(r'\s*\(.*\)\s*$', '', base).strip()
    if nop and nop != base:
        cands.append(nop)

    cands.append(base)
    cands.append(os.path.basename(path)[:-3].replace('_', ' '))

    out = []
    for c in cands:
        c = re.sub(r'\s{2,}', ' ', (c or '').strip())
        if c and c not in out:
            out.append(c)
    return out


def make_label(path, ancestors, is_overview=False):
    if is_overview:
        return '개요'
    return label_ladder(path, ancestors)[0]


def hoisted_label(subdir, solo, ancestors):
    """문서 1개짜리 디렉터리를 부모로 끌어올릴 때의 라벨.

    디렉터리명이 제목 안에 들어있으면 그건 제품/기술 이름이므로
    디렉터리명을 쓴다 (Codex, Grok, GitHub Copilot ...).
    아니면 디렉터리명은 그냥 분류함이므로 문서 제목을 쓴다
    (Secrets/HashiCorp Vault, Infrastructure_as_Code/Terraform ...).
    """
    dname = os.path.basename(subdir)
    title = strip_prefix(doc_title(os.path.join(subdir, solo)), ancestors)
    if norm(dname) and norm(dname) in norm(title):
        return dname.replace('_', ' ')
    label = shorten(title)
    if len(label) > LABEL_SOFT_MAX:
        return dname.replace('_', ' ')
    return label


def norm(s):
    return re.sub(r'[\s_\-\.]+', '', s).strip().lower()


# ---------------------------------------------------------------- 디렉터리 스캔

def children(dirpath):
    files, dirs = [], []
    try:
        entries = sorted(os.listdir(dirpath))
    except OSError:
        return files, dirs
    for e in entries:
        full = os.path.join(dirpath, e)
        if e.startswith('.'):
            continue
        if os.path.isdir(full):
            if e in SKIP_DIRS:
                continue
            if any(f.endswith('.md') for _, _, fs in os.walk(full) for f in fs):
                dirs.append(e)
        elif e.endswith('.md'):
            files.append(e)
    return files, dirs


def only_md(dirpath):
    """디렉터리가 md 파일 딱 하나뿐이면 그 파일명, 아니면 None."""
    files, dirs = children(dirpath)
    if len(files) == 1 and not dirs:
        return files[0]
    return None


def old_order(dirpath):
    """기존 .pages의 나열 순서 (정렬 기준으로만 쓴다)."""
    p = os.path.join(dirpath, '.pages')
    order = []
    if not os.path.exists(p):
        return order
    in_nav = False
    for line in open(p, encoding='utf-8'):
        raw = line.rstrip('\n')
        if re.match(r'^nav:\s*$', raw):
            in_nav = True
            continue
        if in_nav:
            m = re.match(r'^\s+-\s+(.*)$', raw)
            if not m:
                if raw.strip():
                    in_nav = False
                continue
            item = m.group(1).strip()
            if ': ' in item:
                item = item.split(': ', 1)[1].strip()
            order.append(item.strip())
    return order


def existing_title(dirpath):
    p = os.path.join(dirpath, '.pages')
    if not os.path.exists(p):
        return None
    for line in open(p, encoding='utf-8'):
        if line.startswith('title:'):
            return line.split(':', 1)[1].strip()
    return None


# ---------------------------------------------------------------- nav 생성

def build(dirpath, ancestors):
    """이 디렉터리의 nav 엔트리 목록 [(label, target)] 을 만든다."""
    files, dirs = children(dirpath)
    dirname = os.path.basename(dirpath)
    key = dirpath.replace(os.sep, '/')
    # override는 '앞에 오길 바라는 것'만 적는 힌트다.
    # 나머지는 기존 .pages 순서를 그대로 따른다.
    prev = old_order(dirpath)
    hint = ORDER_OVERRIDE.get(key, [])
    order = hint + [o for o in prev if norm(o) not in {norm(h) for h in hint}]

    def rank(name):
        for i, o in enumerate(order):
            if norm(o) == norm(name):
                return i
        return len(order) + 1000

    entries = []

    # 1) 디렉터리 대표 문서를 맨 앞에
    overview = None
    for f in files:
        if norm(f[:-3]) == norm(dirname):
            if f'{key}/{f}' in NO_OVERVIEW:
                continue
            overview = f
            break
    if overview:
        entries.append(('개요', overview))

    # 2) 'DDD/' 와 형제 'DDD.md' 처럼 짝이 지는 건 하나로 합친다
    merged = {}
    for d in dirs:
        sibling = f'{d}.md'
        match = next((f for f in files if norm(f[:-3]) == norm(d)), None)
        if match and match != overview:
            merged[d] = match

    rest = [f for f in files if f != overview and f not in merged.values()]
    # 문서를 먼저, 하위 섹션을 뒤로. 섞여 있으면 사이드바가 어수선해진다.
    # (각 묶음 안에서는 기존 큐레이션 순서를 지킨다)
    fitems = sorted((('f', f) for f in rest), key=lambda t: (rank(t[1]), t[1]))
    ditems = sorted((('d', d) for d in dirs), key=lambda t: (rank(t[1]), t[1]))
    items = fitems + ditems

    for kind, name in items:
        if kind == 'f':
            entries.append((make_label(os.path.join(dirpath, name),
                                       ancestors + [dirname]), name))
        else:
            sub = os.path.join(dirpath, name)
            solo = only_md(sub)
            if solo:
                # 문서 1개짜리 디렉터리 -> 부모로 끌어올린다
                lbl = hoisted_label(sub, solo, ancestors + [dirname])
                entries.append((lbl, f'{name}/{solo}'))
            elif name in merged:
                # 개요 파일 + 하위 디렉터리를 한 그룹으로 묶는다 (파일 이동 없이)
                sub_entries = [('개요', merged[name])]
                for sf in sorted(children(sub)[0]):
                    sub_entries.append(
                        (make_label(os.path.join(sub, sf),
                                    ancestors + [dirname, name]),
                         f'{name}/{sf}'))
                for sd in sorted(children(sub)[1]):
                    sub_entries.append((sd.replace('_', ' '), f'{name}/{sd}'))
                entries.append((name.replace('_', ' '), sub_entries))
            else:
                sub_key = f'{key}/{name}'
                entries.append((DIR_LABEL.get(sub_key, name.replace('_', ' ')),
                                name))

    entries = dedupe(entries, dirpath, ancestors + [dirname])
    return group_siblings(entries)


def build_top():
    """최상위 Develop/.pages — 유령 항목 제거 + 주제 순서 정렬."""
    files, dirs = children(ROOT)
    have = set(files) | set(dirs)
    entries = []
    for name in TOP_ORDER:
        if name not in have:
            continue
        if name.endswith('.md'):
            entries.append((None, name))          # index.md / tags.md 는 라벨 없이
        else:
            entries.append((DIR_LABEL.get(f'Develop/{name}',
                                          name.replace('_', ' ')), name))
    # TOP_ORDER에 없는 게 새로 생기면 뒤에 붙인다 (다시는 고아가 되지 않도록)
    for name in sorted(have - set(TOP_ORDER)):
        if name == '_hub':
            continue
        entries.append((None, name) if name.endswith('.md')
                       else (name.replace('_', ' '), name))
    return entries


def group_siblings(entries):
    """같은 이름으로 시작하는 형제들을 접기 가능한 그룹으로 묶는다.

    'ECS', 'ECS Exec', 'ECS Task Placement', ... 30여 개가 평평하게 늘어서 있으면
    사이드바에서 읽히지 않는다. 'ECS' 그룹 하나로 접고 접두사는 떼어낸다.
    'ECS에서 ...'처럼 조사가 바로 붙은 것도 같은 그룹으로 본다.
    """
    flat = [(i, l, t) for i, (l, t) in enumerate(entries)
            if not isinstance(t, list) and l]

    # 그룹 이름 후보: 라벨의 첫 낱말 (영문 고유명사만)
    cands = set()
    for _, label, _ in flat:
        words = label.split()
        if not words or not GROUP_NAME_OK.match(words[0]):
            continue
        if words[0].lower() in GROUP_BLOCK:
            # 'Cloud SQL'처럼 벤더 공통어는 두 낱말까지 붙여야 제품이 된다
            if len(words) > 1 and words[1].lower() not in GROUP_BLOCK:
                cands.add(' '.join(words[:2]))
        else:
            cands.add(words[0])

    def members_of(name):
        pat = re.compile(re.escape(name) + r'(\s|[가-힣])')
        return [i for i, label, _ in flat
                if label == name or pat.match(label)]

    def extend(name, idxs):
        """'SQL' 3개가 전부 'SQL Injection ...' 이면 그룹 이름을 늘린다."""
        toks = [entries[i][0].split() for i in idxs]
        pre = []
        for k in range(min(len(x) for x in toks)):
            words = {x[k] for x in toks}
            if len(words) != 1:
                break
            pre.append(words.pop())
            if any(len(x) == k + 1 for x in toks):
                break      # 한 항목을 통째로 삼켰다 -> 그게 그룹의 개요다
        return ' '.join(pre) if pre else name

    plan = {}
    for name in sorted(cands, key=len, reverse=True):
        idxs = [i for i in members_of(name)
                if not any(i in v for v in plan.values())]
        if len(idxs) >= GROUP_MIN:
            plan[extend(name, idxs)] = idxs
    if not plan:
        return entries

    out, consumed = [], set()
    for idx, (label, target) in enumerate(entries):
        if idx in consumed:
            continue
        owner = next((p for p, idxs in plan.items() if idx in idxs), None)
        if owner is None:
            out.append((label, target))
            continue
        members = []
        for j in plan[owner]:
            consumed.add(j)
            jl, jt = entries[j]
            rest = jl[len(owner):]
            if not rest.strip():
                rest = '개요'
            elif not rest.startswith(' '):
                rest = jl          # 조사가 바로 붙은 경우는 원래 라벨을 유지
            else:
                rest = rest.strip()
                if looks_broken(rest):
                    rest = jl
            members.append((rest, jt))
        members.sort(key=lambda m: 0 if m[0] == '개요' else 1)
        out.append((owner, members))
    return out


def dedupe(entries, dirpath, ancestors):
    """형제끼리 라벨이 겹치면, 겹치지 않는 '가장 짧은' 후보로 올라간다."""
    taken = set()
    for i, (lbl, tgt) in enumerate(entries):
        if lbl.lower() not in taken:
            taken.add(lbl.lower())
            continue
        if isinstance(tgt, list) or not tgt.endswith('.md'):
            taken.add(lbl.lower())
            continue
        for cand in label_ladder(os.path.join(dirpath, tgt), ancestors):
            if cand.lower() not in taken:
                entries[i] = (cand, tgt)
                lbl = cand
                break
        else:
            # 사다리를 다 올라가도 겹치면 파일명으로 구분
            entries[i] = (os.path.basename(tgt)[:-3].replace('_', ' '), tgt)
            lbl = entries[i][0]
        taken.add(lbl.lower())
    return entries


def write_pages(dirpath, entries, title=None):
    lines = []
    if title:
        lines.append(f'title: {title}')
    lines.append('nav:')
    for label, target in entries:
        if isinstance(target, list):
            lines.append(f'  - {label}:')
            for sl, st in target:
                lines.append(f'    - {sl}: {st}')
            continue
        # 라벨이 target에서 자연스럽게 나오면 굳이 적지 않는다
        if label is None or label == target.replace('_', ' '):
            lines.append(f'  - {target}')
        else:
            lines.append(f'  - {label}: {target}')
    content = '\n'.join(lines) + '\n'
    path = os.path.join(dirpath, '.pages')
    if WRITE:
        open(path, 'w', encoding='utf-8').write(content)
    return path, content


def walk_and_generate():
    generated = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        parts = dirpath.split(os.sep)
        if any(p in SKIP_DIRS for p in parts) or any(p.startswith('.') for p in parts[1:]):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith('.')]
        if dirpath == ROOT:
            generated[dirpath] = write_pages(ROOT, build_top())[1]
            continue
        # 문서 1개짜리 디렉터리는 부모가 흡수했으므로 .pages 불필요
        if only_md(dirpath):
            p = os.path.join(dirpath, '.pages')
            if os.path.exists(p) and WRITE:
                os.remove(p)
            generated[dirpath] = None
            continue
        ancestors = parts[1:-1]
        entries = build(dirpath, ancestors)
        title = existing_title(dirpath)
        generated[dirpath] = write_pages(dirpath, entries, title)[1]
    return generated


if __name__ == '__main__':
    gen = walk_and_generate()
    n = sum(1 for v in gen.values() if v)
    rm = sum(1 for v in gen.values() if v is None)
    print(f"{'작성' if WRITE else '미리보기'}: .pages {n}개 생성, {rm}개 제거(1문서 디렉터리)")
