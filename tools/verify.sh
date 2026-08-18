#!/usr/bin/env bash
# 푸시 전 로컬 검증 — CI 와 동일한 순서. 전부 통과해야 푸시한다.
# 사용: bash tools/verify.sh
set -u
cd "$(dirname "$0")/.."
FAIL=0
export PATH=/tmp/v3/bin:$PATH
run() { printf '  %-34s' "$1"; shift; if "$@" >/tmp/_v.log 2>&1; then echo "OK"; else echo "FAIL"; tail -12 /tmp/_v.log|sed 's/^/      /'; FAIL=1; fi; }

echo "── 문서 검사 ──"
run "gen_tags"            python3 tools/gen_tags.py --strict
run "check_frontmatter"   python3 tools/check_frontmatter.py --strict
run "check_mermaid"       python3 tools/check_mermaid_entities.py
run "checker_tests"       python3 tools/tests/test_check_links.py
run "check_links"         python3 tools/check_links.py --strict

echo "── 빌드 (약 55초, minify·rss·git-date 제외) ──"
DISABLE_MKDOCS_2_WARNING=true run "mkdocs build --strict" mkdocs build --strict -d /tmp/_verify_site

echo "── 산출물 검사 ──"
run "built assets"        python3 tools/check_built_assets.py /tmp/_verify_site --strict

[ $FAIL -eq 0 ] && echo "✓ 전부 통과 — 푸시 가능" || echo "✗ 실패 있음 — 푸시하지 말 것"
exit $FAIL
