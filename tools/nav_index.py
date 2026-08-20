"""사이드바 전체 트리를 nav.json 한 파일로 내보낸다.

왜 필요한가: `navigation.prune` 은 현재 경로 밖 섹션의 자식을 렌더하지 않는다.
그런데 화살표는 남는다. 펼쳐질 것처럼 보이는데 눌러도 아무 일이 없었다.

prune 을 끄면 펼쳐지긴 한다. 대신 사이드바 항목이 페이지당 135개에서
1,158개로 늘고(8.6배) 페이지가 201KB → 640KB, 사이트가 205MB → 781MB 다.
메뉴 하나 펼치자고 모든 페이지가 그 값을 치를 이유가 없다.

대신 트리를 한 파일로 빼서 처음 펼칠 때 한 번만 받는다(gzip 약 14KB).
브라우저가 캐시하므로 그 뒤로는 요청이 없다.

페이지를 긁어오는 방법을 먼저 만들었다가 버렸다. Backend·Infra·CS 는 여러
최상위 폴더를 묶은 가상 섹션이라 자기 index 페이지가 없다. 그래서
`_group/backend/` 에 가도 그 섹션이 pruned 로 나온다 — 긁어올 원본이 없다.

**직렬화는 반드시 on_post_build 에서 한다.** on_nav 시점에는 Page.title 이
아직 None 이다(제목은 그 뒤 페이지를 읽으면서 채워진다). 거기서 트리를 뜨면
`.pages` 에 이름을 손으로 적어 둔 항목만 남고 나머지가 통째로 사라진다.
실제로 그렇게 만들었다가 Node.js 자식이 13개에서 5개로 줄고 Java 가 통째로
빠졌다. nav 객체는 같은 것을 계속 들고 있으므로 참조만 보관했다가
빌드가 끝난 뒤 훑으면 제목이 다 채워져 있다.
"""
import json
import os

# 사이드바에 안 보이는 항목은 트리에도 넣지 않는다.
_SKIP_TITLES = {"태그", "Tags"}

_NAV = None


def _node(item):
    """nav 항목 하나를 {t: 제목, u: URL, c: [자식]} 로 줄인다.

    키를 한 글자로 쓰는 건 취향이 아니라 용량 때문이다. 항목이 700개가 넘어
    "title"/"url"/"children" 을 그대로 쓰면 그만큼이 곱해진다.
    """
    title = getattr(item, "title", None)
    if not title or title in _SKIP_TITLES:
        return None

    if getattr(item, "is_section", False):
        kids = [n for n in (_node(c) for c in (item.children or [])) if n]
        if not kids:
            return None
        # 섹션 자체의 링크: navigation.indexes 로 승격된 index 페이지가 있으면 그것,
        # 없으면 첫 자식. Material 이 화면에 그리는 것과 같게 맞춘다.
        idx = next(
            (
                c.url
                for c in (item.children or [])
                if getattr(c, "is_page", False) and getattr(c, "is_index", False)
            ),
            None,
        )
        return {"t": title, "u": idx or kids[0].get("u", ""), "c": kids}

    if getattr(item, "is_page", False) or getattr(item, "is_link", False):
        return {"t": title, "u": getattr(item, "url", "") or ""}

    return None


def _count(nodes):
    n = 0
    for x in nodes:
        n += 1
        if "c" in x:
            n += _count(x["c"])
    return n


def on_nav(nav, config, files, **kwargs):
    # 여기서 직렬화하면 안 된다 — 제목이 아직 없다. 참조만 잡아 둔다.
    global _NAV
    _NAV = nav
    return nav


def on_post_build(config, **kwargs):
    if _NAV is None:
        return

    tree = [n for n in (_node(i) for i in _NAV) if n]
    path = os.path.join(config["site_dir"], "nav.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(path)
    print(f"  사이드바 트리: {_count(tree):,}개 항목 -> nav.json {size / 1024:.0f}KB")
