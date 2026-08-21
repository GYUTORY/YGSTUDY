#!/usr/bin/env bash
# 푸시 전 로컬 검증 — CI 와 동일한 순서. 전부 통과해야 푸시한다.
# 사용: bash tools/verify.sh
set -u
cd "$(dirname "$0")/.."
FAIL=0
export PATH=/tmp/v3/bin:$PATH
run() { printf '  %-34s' "$1"; shift; if "$@" >/tmp/_v.log 2>&1; then echo "OK"; else echo "FAIL"; tail -12 /tmp/_v.log|sed 's/^/      /'; FAIL=1; fi; }

[ -x .git/hooks/pre-commit ] || echo "  ⚠ git 훅 미설치 — bash tools/install_hooks.sh (NFD 차단·updated 자동갱신이 안 걸려 있다)"
# 생성물을 먼저 다시 만든다.
#
# 왜: check_links 는 section_index.py 가 만드는 index.md 를 검사하는데,
# 그걸 다시 만드는 건 아래 mkdocs build 다. 순서가 거꾸로라 문서를 지우거나
# 이름을 바꾸면 첫 실행이 반드시 실패하고 두 번째가 통과한다. 실제로 이번에
# 세 번 겪었다. 더 나쁜 건 "다시 돌리면 통과" 가 학습되면 진짜 깨진 링크도
# 같은 방식으로 넘어간다는 것이다.
python3 tools/section_index.py >/dev/null

echo "── 문서 검사 ──"
run "gen_tags"            python3 tools/gen_tags.py --strict
run "check_frontmatter"   python3 tools/check_frontmatter.py --strict
run "check_mermaid"       python3 tools/check_mermaid_entities.py
run "checker_tests"       bash -c 'set -e; n=0; for t in tools/tests/test_*.py; do [ -e "$t" ] || continue; python3 "$t"; n=$((n+1)); done; [ "$n" -gt 0 ]'
run "check_links"         python3 tools/check_links.py --strict
# 다이어그램 글자 대비. 계산이 틀어지면 "그려지긴 하는데 안 읽히는" 상태가 되고
# 빌드는 통과한다. jsdom 없이 도는 순수 계산이라 게이트에 넣을 수 있다.
run "mermaid contrast"    node tools/tests/mermaid_contrast.test.mjs
# CSS 의 전경·배경 쌍. 한쪽 모드만 손보면 반대쪽이 조용히 깨진다.
run "css contrast"        python3 tools/check_contrast.py --strict
# .pages 의 nav 는 적은 것만 싣는다 — 목록에서 빠진 문서는 사이드바에서 조용히
# 사라지고 빌드도 --strict 도 안 잡는다. 반대 방향(nav 에 적었는데 파일이 없다)은
# awesome-pages 가 strict 기본값으로 예외를 던지므로 이미 막혀 있다.
run "gen_nav --audit"     python3 tools/gen_nav.py --audit
# CI 에는 있는데 여기 없어서 "로컬 전부 통과 → CI 빨간불" 이 가능했다.
# BEFORE_SHA 를 안 주면 90일 전체를 훑어 과거 빚에 걸리므로 CI 와 같은 범위로 좁힌다.
BEFORE_SHA="$(git merge-base origin/main HEAD 2>/dev/null || echo '')" \
AFTER_SHA="$(git rev-parse HEAD)" \
run "check_sources"       python3 tools/check_sources.py --strict

echo "── 빌드 (약 55초, minify·rss·git-date 제외) ──"
DISABLE_MKDOCS_2_WARNING=true run "mkdocs build --strict" mkdocs build --strict -d /tmp/_verify_site

echo "── 산출물 검사 ──"
run "built assets"        python3 tools/check_built_assets.py /tmp/_verify_site --strict
# 사이드바 펼침이 이 파일에 달려 있다. 비어도 화면은 멀쩡해 보인다 —
# 화살표는 그대로 있고 눌렀을 때만 아무 일이 없어서 눈으로는 못 잡는다.
run "nav index"           python3 tools/check_nav_index.py /tmp/_verify_site --strict
SITE_DIR=/tmp/_verify_site run "redirects"        python3 tools/check_redirects.py

[ $FAIL -eq 0 ] && echo "✓ 전부 통과 — 푸시 가능" || echo "✗ 실패 있음 — 푸시하지 말 것"
exit $FAIL
