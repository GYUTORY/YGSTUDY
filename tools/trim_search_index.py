"""MkDocs hook: 빌드 후 검색 인덱스의 소제목 본문에 상한을 둔다.

왜: 인덱스가 46MB(압축 10.6MB)까지 불어서, 페이지를 열 때마다 워커가 그걸
다시 받아 재구축하느라 5초씩 돌았다. 메인 스레드는 안 막히지만 CPU 와 회선을
계속 먹고, GitHub Pages 캐시가 10분이라 조금만 둘러봐도 다시 받는다.

항목 33,193개 중 31,835개가 문서 안 소제목이고 본문의 99%가 거기 들어 있다.
소제목 자체는 전부 남기고(앵커 이동·제목 검색 그대로), 각 소제목의 본문만
앞부분으로 자른다. 긴 절의 뒷부분은 검색에 안 걸리는 대신 절반으로 줄어든다.

자르는 자리는 단어 중간이 아니라 가장 가까운 공백이다 — 잘린 조각이
엉뚱한 토큰으로 색인되지 않게.
"""

import json
import os

# 소제목 하나가 인덱스에 실을 수 있는 본문 길이(글자).
# 이 값을 올리면 검색이 더 찾고 인덱스가 커진다. 실측 기준:
#   상한 없음 18.0M자 / 1200자 15.7M자 / 600자 약 11M자 / 300자 7.0M자
MAX_SECTION_CHARS = 600

# 자를 때 뒤로 물러설 수 있는 최대 거리. 이 안에 공백이 없으면 그냥 자른다.
_BACKOFF = 40


def _trim(text):
    if len(text) <= MAX_SECTION_CHARS:
        return text, False
    cut = text.rfind(" ", MAX_SECTION_CHARS - _BACKOFF, MAX_SECTION_CHARS)
    if cut == -1:
        cut = MAX_SECTION_CHARS
    return text[:cut].rstrip(), True


def on_post_build(config, **kwargs):
    path = os.path.join(config["site_dir"], "search", "search_index.json")
    if not os.path.exists(path):
        return

    before = os.path.getsize(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = data.get("docs", [])
    trimmed = 0
    for doc in docs:
        # 페이지 자체(앵커 없는 항목)는 건드리지 않는다 — 본문이 거의 없다.
        if "#" not in doc.get("location", ""):
            continue
        text = doc.get("text", "")
        if not text:
            continue
        new, did = _trim(text)
        if did:
            doc["text"] = new
            trimmed += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    after = os.path.getsize(path)
    print(
        "  검색 인덱스: %.1fMB -> %.1fMB (%d%% 절감) · 소제목 %s개 중 %s개 자름"
        % (
            before / 1048576,
            after / 1048576,
            round((1 - after / before) * 100),
            format(sum(1 for d in docs if "#" in d.get("location", "")), ","),
            format(trimmed, ","),
        )
    )
