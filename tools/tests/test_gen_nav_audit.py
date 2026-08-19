#!/usr/bin/env python3
"""gen_nav.py 의 사이드바 누락 감사(--audit) 회귀 테스트.

실행: python3 tools/tests/test_gen_nav_audit.py

왜 테스트를 두는가: 이 감사는 "아무것도 안 잡히는 것"이 정상 상태다.
그래서 잡는 쪽 로직이 죽어도 출력이 똑같아 아무도 모른다.
같은 파일에 SKIP_DIRS 가 선언만 되고 안 쓰이던 전례가 있다
(test_check_frontmatter.py 머리말 참고). 통과만 확인한 검사기는
조용히 아무것도 안 하게 된다 — 그래서 일부러 깨뜨려 잡히는지를 본다.

감사가 무엇을 판정하는가: awesome-pages 의 .pages nav 는 거기 적은 것만
싣는다. 목록에 없는 파일은 경고 없이 빠지고, 빌드도 --strict 도 안 잡는다
(`- ...` 를 적어 둔 자리가 있을 때만 나머지가 자동으로 실린다).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

sys.argv = ["gen_nav.py"]          # --write 플래그가 켜지지 않게
import gen_nav as G  # noqa: E402


NAV = "nav:\n  - index.md\n  - 첫 문서: a.md\n  - 둘째: b.md\n  - Sub\n"


def _tree(nav=NAV, files=("index.md", "a.md", "b.md"), dirs=("Sub",),
          key="Develop/T"):
    return ({key: (list(files), list(dirs))}, {key: nav})


def test_clean_tree_reports_nothing():
    """.pages 가 자식을 모두 싣고 있으면 검출 0."""
    assert G.audit_tree(*_tree()) == []


def test_dropped_document_is_caught():
    """nav 에서 한 줄이 사라지면 그 문서를 잡는다 — 이 감사의 본래 목적."""
    nav = NAV.replace("  - 둘째: b.md\n", "")
    miss = G.audit_tree(*_tree(nav=nav))
    assert len(miss) == 1, f"놓쳤다: {miss}"
    assert "b.md" in miss[0], miss


def test_dropped_subdirectory_is_caught():
    """문서뿐 아니라 하위 섹션이 빠진 것도 잡는다."""
    nav = NAV.replace("  - Sub\n", "")
    miss = G.audit_tree(*_tree(nav=nav))
    assert len(miss) == 1 and "Sub" in miss[0], miss


def test_new_file_not_yet_in_pages_is_caught():
    """문서를 새로 넣고 gen_nav 를 안 돌린 상태 — 사이드바에서 안 보인다."""
    miss = G.audit_tree(*_tree(files=("index.md", "a.md", "b.md", "새문서.md")))
    assert len(miss) == 1 and "새문서.md" in miss[0], miss


def test_rest_placeholder_disables_check():
    """`- ...` 가 있으면 나머지가 자동으로 실리므로 검출하지 않는다."""
    nav = NAV.replace("  - Sub\n", "  - ...\n")
    assert G.audit_tree(*_tree(nav=nav)) == []


def test_deep_directory_is_out_of_scope():
    """깊이 3+ 는 index.md 만 싣는 것이 설계다(MAX_SIDEBAR_DEPTH)."""
    deep = "Develop/A/B/C/D"
    entries = {deep: (["index.md", "x.md"], [])}
    assert G.audit_tree(entries, {deep: "nav:\n  - index.md\n"}) == []


def test_hidden_and_hoisted_are_not_flagged():
    """일부러 뺀 것(HIDDEN)과 다른 자리로 올린 것(HOIST_OUT)은 검출 대상이 아니다."""
    root = "Develop"
    entries = {root: (["index.md", "todo.md"], [])}
    assert "Develop/todo.md" in G.HIDDEN, "HIDDEN 목록이 바뀌었다"
    assert G.audit_tree(entries, {root: "nav:\n  - index.md\n"}) == []

    k = "Develop/DevOps/Kubernetes"
    assert f"{k}/Docker" in G.HOIST_OUT, "HOIST_OUT 목록이 바뀌었다"
    entries = {k: (["index.md"], ["Docker"])}
    assert G.audit_tree(entries, {k: "nav:\n  - index.md\n"}) == []


def test_group_members_count_as_listed():
    """묶음 안에 든 문서도 nav 에 실린 것으로 본다 (중첩 목록 파싱)."""
    nav = "nav:\n  - index.md\n  - 묶음:\n    - 첫 문서: a.md\n    - 둘째: b.md\n  - Sub\n"
    assert G.audit_tree(*_tree(nav=nav)) == []


def test_missing_pages_file_is_not_flagged():
    """.pages 가 아예 없으면 awesome-pages 가 알아서 전부 싣는다 — 검출 대상 아님."""
    key = "Develop/T"
    assert G.audit_tree({key: (["a.md"], [])}, {}) == []


def test_stale_path_key_is_caught():
    """설정이 가리키는 문서가 이름이 바뀌면 잡는다.

    실제로 세 건이 이 상태로 커밋에 들어가 있었다 — 붙잡지 못한 문서는
    묶음 밖으로 떨어질 뿐이라 화면만 봐서는 알 수 없었다.
    """
    real = {p for p in list(G.LABEL_OVERRIDE) + list(G.MANUAL_GROUPS)}
    real.add("Develop/Cloud/AWS/Network/Private_vs_Public_Subnet.md")

    def exists(p):
        return p in real or p in {f"{k}/{r}" for k, v in G.MANUAL_GROUPS.items()
                                  for _, ms in v for _, r in ms}

    # 있다고 답하는 세상에서는 조용하다
    assert G.audit_paths(exists=lambda p: True, isdir=lambda p: True) == []
    # 딱 한 건만 없다고 답하면 그 한 건을 짚는다
    gone = "Develop/Language/Go/Go_Generics.md"
    stale = G.audit_paths(exists=lambda p: p != gone, isdir=lambda p: True)
    assert len(stale) == 1 and gone in stale[0], stale


def test_path_keys_are_all_real():
    """저장소 기준으로 지금 뒤처진 줄이 없는지. 게이트로 쓰는 근거다."""
    import os

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        stale = G.audit_paths()
    finally:
        os.chdir(cwd)
    assert not stale, "가리키는 대상이 없는 설정: " + "; ".join(stale)


def test_repository_is_currently_clean():
    """실제 저장소가 지금 통과 상태인지. 게이트로 쓰는 근거다."""
    import os

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        miss = G.audit_tree(*G.scan_disk())
    finally:
        os.chdir(cwd)
    assert not miss, "사이드바에서 빠진 항목이 있다: " + "; ".join(miss)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
