"""MkDocs hook: 검색 인덱스를 손질한다.

0) 코드 블록을 인덱스에서 뺀다 (준비 시간)
   인덱스를 절반으로 줄여도 검색이 준비되기까지 6초는 그대로였다. 시간이
   회선이 아니라 CPU 로 나갔기 때문이다 — 워커가 색인을 만드는 데 5,747ms,
   다운로드 31ms, JSON 파싱 43ms 였다(로컬 실측). 그 5.7초는 인덱스에 담긴
   글자 수에 거의 정비례한다. 그런데 원본 마크다운 1,840만 자 중 절반(49.5%)이
   ``` 코드 블록이다. 사람은 코드 본문으로 검색하지 않는데, 색인은 그걸 다
   토큰으로 쪼개고 위치까지 기록하느라 시간을 쓴다.
   Material 파서는 `pre` 를 기본으로 인덱싱하지만 `data-search-exclude` 속성이
   붙은 요소는 통째로 건너뛴다. 그래서 렌더된 HTML 의 모든 `<pre>` 에 그 속성만
   달아준다. 화면에 나가는 코드는 그대로다 — 속성 하나가 늘 뿐이다.

1) 소제목 본문에 상한을 둔다 (용량)
   인덱스가 46MB(압축 10.6MB)까지 불어서, 페이지를 열 때마다 워커가 그걸
   다시 받아 재구축하느라 5초씩 돌았다. 메인 스레드는 안 막히지만 CPU 와
   회선을 계속 먹고, GitHub Pages 캐시가 10분이라 조금만 둘러봐도 다시 받는다.
   항목 33,193개 중 31,835개가 문서 안 소제목이고 본문의 99%가 거기 있었다.

2) 한글 음차어를 붙인다 (검색 적중)
   `docker` 로 치면 1위인데 `도커` 로 치면 상위 10건에 한 건뿐이었다.
   Docker 문서가 16건 있는데 '도커'라는 글자는 인덱스에 0번 나온다 —
   문서를 영문 표기로만 썼기 때문이다. 한국어로 검색하는 사람이 못 찾는다.
   제목·경로에 영문 표기가 있으면 그 문서의 인덱스 tags 에 한글 음차를 더한다.
   화면에 보이는 내용도, 태그 페이지도 그대로다 — 검색 인덱스에만 붙는다.
"""

import json
import os
import re

# ── 0) 코드 블록 제외 ──────────────────────────────────────
# 여는 `<pre` 마다 속성을 하나 끼운다. 본문에 글로 적힌 <pre 는 이미
# &lt;pre 로 이스케이프돼 있어 걸리지 않는다.
_PRE_OPEN = re.compile(r"<pre\b")


def on_page_content(html, page, config, files):
    """렌더된 HTML 의 코드 블록에 검색 제외 표시를 단다.

    인라인 `<code>` 는 건드리지 않는다. 산문 속 API 이름은 실제로 검색에
    쓰이는데다 분량이 전체의 5% 뿐이라 시간에 거의 기여하지 않는다.

    부수 효과로 검색이 더 잘 찾게 됐다. 코드가 아래 600자 예산을 먼저
    까먹는 바람에 산문 꼬리가 잘려나가던 섹션이 11,996개였는데 4,140개로
    줄었고, 그 덕에 한글 낱말 6,385개가 새로 색인에 들어왔다.
    """
    return _PRE_OPEN.sub("<pre data-search-exclude", html)


# ── 1) 용량 ────────────────────────────────────────────────
# 소제목 하나가 인덱스에 실을 수 있는 본문 길이(글자).
# 올리면 검색이 더 찾고 인덱스가 커진다. 실측:
#   상한 없음 18.0M자 / 1200자 15.7M자 / 600자 약 11M자 / 300자 7.0M자
MAX_SECTION_CHARS = 600
_BACKOFF = 40  # 자를 때 공백을 찾아 뒤로 물러설 수 있는 최대 거리

# ── 2) 음차 ────────────────────────────────────────────────
# 영문 표기 -> 한국어로 검색할 법한 말들.
# 제목이나 경로에 왼쪽 낱말이 있으면 오른쪽 말들을 그 문서 검색어에 더한다.
# 낱말 경계로 찾으므로 'go' 가 'google' 에 걸리지 않는다.
ALIASES = {
    "docker": "도커 컨테이너",
    "kubernetes": "쿠버네티스 쿠버 케이팔에스",
    "k8s": "쿠버네티스",
    "redis": "레디스",
    "kafka": "카프카",
    "nginx": "엔진엑스 엔진x",
    "caddy": "캐디",
    "linux": "리눅스",
    "aws": "아마존 에이더블유에스",
    "gcp": "구글클라우드 지씨피",
    "cloud": "클라우드",
    "container": "컨테이너",
    "containers": "컨테이너",
    "network": "네트워크",
    "security": "보안",
    "database": "데이터베이스",
    "cache": "캐시 캐싱",
    "caching": "캐싱 캐시",
    "index": "인덱스 색인",
    "transaction": "트랜잭션",
    "queue": "큐 대기열",
    "thread": "스레드 쓰레드",
    "process": "프로세스",
    "memory": "메모리",
    "scheduling": "스케줄링",
    "javascript": "자바스크립트",
    "typescript": "타입스크립트",
    "java": "자바",
    "python": "파이썬",
    "spring": "스프링",
    "nestjs": "네스트제이에스 네스트",
    "node": "노드 노드제이에스",
    "react": "리액트",
    "architecture": "아키텍처 구조",
    "pattern": "패턴",
    "framework": "프레임워크",
    "backend": "백엔드",
    "frontend": "프론트엔드",
    "server": "서버",
    "proxy": "프록시",
    "protocol": "프로토콜",
    "session": "세션",
    "token": "토큰",
    "encryption": "암호화",
    "algorithm": "알고리즘",
    "sorting": "정렬",
    "search": "탐색 검색",
    "logging": "로깅 로그",
    "monitoring": "모니터링 관측",
    "deploy": "배포",
    "deployment": "배포",
    "pipeline": "파이프라인",
    "migration": "마이그레이션 이관",
    "backup": "백업",
    "cluster": "클러스터",
    "load": "부하",
    "balancer": "로드밸런서 부하분산",
    "gateway": "게이트웨이",
    "message": "메시지",
    "messaging": "메시징 메시지",
    "event": "이벤트",
    "stream": "스트림",
    "batch": "배치",
    "test": "테스트",
    "testing": "테스트",
    "performance": "성능",
    "optimization": "최적화",
    "storage": "스토리지 저장소",
    "serverless": "서버리스",
    "lambda": "람다",
    "bucket": "버킷",
    "firewall": "방화벽",
    "certificate": "인증서",
    "authentication": "인증",
    "authorization": "인가 권한",
}

_WORD = re.compile(r"[a-z0-9]+")

# 음차를 어디에 넣을지 정하기까지 두 번 헛짚었다. 같은 실수를 반복하지 않게 남긴다.
#
#   1) text 에만 넣기 — 찾아지긴 하는데 순위가 엉켰다. 점수는 낱말이 몇 번
#      나오는지를 따지는데, 'DuckDNS 설정' 글이 본문에서 '도커'를 여러 번
#      쓰는 바람에 정작 Docker 문서가 8위로 밀렸다.
#   2) boost 필드 주입 — 아무 효과가 없었다. 3.0 도 50.0 도 순위가 한 칸도
#      안 움직였다. 빌드가 끝난 인덱스에 넣은 boost 는 검색이 읽지 않는다.
#   3) tags 에 넣기 — 이게 먹었다. '도커' 상위 10건이 전부 Docker 문서가 됐다.
#
# tags 는 인덱스에만 넣는다. 태그 페이지는 원본 frontmatter 로 빌드 중에
# 이미 만들어지므로, 여기서 더한 음차는 그 페이지에 나타나지 않는다.


def _trim(text):
    if len(text) <= MAX_SECTION_CHARS:
        return text, False
    cut = text.rfind(" ", MAX_SECTION_CHARS - _BACKOFF, MAX_SECTION_CHARS)
    if cut == -1:
        cut = MAX_SECTION_CHARS
    return text[:cut].rstrip(), True


def _topic_terms(doc):
    """이 문서가 정면으로 다루는 주제의 영문 낱말들.

    제목에 그 낱말이 있거나 주소(폴더 경로)에 들어 있으면 그 주제로 본다.
    남 이야기하다 본문에서 언급만 한 글은 걸리지 않는다 —
    제목도 경로도 아닌 곳의 등장은 보지 않기 때문이다.
    """
    words = set(_WORD.findall(doc.get("title", "").lower()))
    words |= set(_WORD.findall(doc.get("location", "").lower()))
    return [en for en in ALIASES if en in words]


def on_post_build(config, **kwargs):
    path = os.path.join(config["site_dir"], "search", "search_index.json")
    if not os.path.exists(path):
        return

    before = os.path.getsize(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = data.get("docs", [])

    # 페이지별 음차를 먼저 정해 둔다. 소제목은 자기 페이지 것을 물려받는다.
    page_alias = {}
    for doc in docs:
        loc = doc.get("location", "")
        if "#" in loc:
            continue
        terms = _topic_terms(doc)
        if terms:
            words = []
            for en in terms:
                words.extend(ALIASES[en].split())
            page_alias[loc] = sorted(set(words))

    trimmed = 0
    aliased = 0
    for doc in docs:
        loc = doc.get("location", "")
        if "#" in loc:
            text = doc.get("text", "")
            if text:
                new, did = _trim(text)
                if did:
                    doc["text"] = new
                    trimmed += 1

        # 소제목도 자기 페이지의 음차를 물려받는다 — 소제목만 걸린 결과에서도
        # 같은 문서로 이어져야 하기 때문.
        words = page_alias.get(loc.split("#", 1)[0])
        if words:
            tags = list(doc.get("tags") or [])
            for w in words:
                if w not in tags:
                    tags.append(w)
            doc["tags"] = tags
            aliased += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    after = os.path.getsize(path)
    sections = sum(1 for d in docs if "#" in d.get("location", ""))
    print(
        "  검색 인덱스: %.1fMB -> %.1fMB (%d%% 절감) · 소제목 %s개 중 %s개 자름 · 음차 %s개 항목"
        % (
            before / 1048576,
            after / 1048576,
            round((1 - after / before) * 100),
            format(sections, ","),
            format(trimmed, ","),
            format(aliased, ","),
        )
    )
