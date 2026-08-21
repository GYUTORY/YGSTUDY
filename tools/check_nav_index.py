#!/usr/bin/env python3
"""빌드가 낸 nav.json 이 쓸 만한지 검사한다.

왜 필요한가: 사이드바에서 잘린 가지를 펼치는 동작이 이 파일에 전적으로
의존한다. 그런데 이게 비어도 페이지는 멀쩡해 보인다 — 화살표는 그대로
있고, 눌렀을 때만 아무 일이 없다. 눈으로는 못 잡는다.

실제로 한 번 그렇게 만들었다. 훅이 on_nav 에서 트리를 뜨는 바람에 Page.title
이 아직 없어서, `.pages` 에 이름을 손으로 적어 둔 항목만 남고 나머지가
사라졌다(1,005 -> 741). 빌드는 통과했고 파일도 생겼고 크기도 그럴듯했다.

그래서 "파일이 있나" 만 보지 않는다. 개수가 갑자기 줄지 않았는지,
문서 수와 견줘 말이 되는지, 최상위 묶음이 다 있는지를 본다.

사용: python3 tools/check_nav_index.py <site_dir> [--strict]
"""
import json
import os
import sys

# 이 아래로 떨어지면 무언가 통째로 빠진 것이다. 실측 1,005개 기준으로
# 여유를 두되, 741개까지 줄었던 그 사고는 잡히는 자리에 놓는다.
MIN_ITEMS = 900

# .pages 의 최상위 묶음. 하나라도 없으면 트리가 잘린 것이다.
REQUIRED_TOP = {"Language", "Backend", "Database", "Infra", "CS", "AI", "가이드"}


def count(nodes):
    n = 0
    for x in nodes:
        n += 1
        if "c" in x:
            n += count(x["c"])
    return n


def leaves(nodes):
    """문서 하나에 해당하는 항목(자식 없는 노드) 수."""
    n = 0
    for x in nodes:
        if "c" in x:
            n += leaves(x["c"])
        else:
            n += 1
    return n


def main():
    site = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "site"
    strict = "--strict" in sys.argv
    path = os.path.join(site, "nav.json")

    if not os.path.exists(path):
        print(f"✗ {path} 없음 — tools/nav_index.py 훅이 안 돌았습니다.")
        print("  이게 없으면 사이드바에서 잘린 가지를 펼칠 수 없습니다.")
        sys.exit(2 if strict else 0)

    try:
        tree = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"✗ nav.json 을 읽을 수 없음: {e}")
        sys.exit(1 if strict else 0)

    problems = []
    total = count(tree)
    docs = leaves(tree)
    tops = {n.get("t") for n in tree}

    if total < MIN_ITEMS:
        problems.append(
            f"항목이 {total}개뿐입니다 (최소 {MIN_ITEMS}개 기대). "
            "제목이 없는 항목을 버리고 있는지 확인하세요 — "
            "직렬화는 on_post_build 에서 해야 Page.title 이 채워져 있습니다."
        )

    missing = REQUIRED_TOP - tops
    if missing:
        problems.append(f"최상위 묶음이 빠졌습니다: {sorted(missing)}")

    # 링크가 없는 항목은 눌러도 못 가는 항목이다
    def no_url(nodes, path_=""):
        out = []
        for x in nodes:
            here = path_ + " > " + x.get("t", "?")
            if not x.get("u"):
                out.append(here)
            if "c" in x:
                out += no_url(x["c"], here)
        return out

    dead = no_url(tree)
    if dead:
        problems.append(f"URL 이 빈 항목 {len(dead)}개: {dead[:5]}")

    size = os.path.getsize(path)
    if not problems:
        print(f"✓ nav.json 정상 — 항목 {total:,}개(문서 {docs:,}개) {size / 1024:.0f}KB")
        return

    print(f"⚠ nav.json 이상 — 항목 {total:,}개 {size / 1024:.0f}KB\n")
    for p in problems:
        print(f"  · {p}")
    if strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
