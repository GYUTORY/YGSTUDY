#!/usr/bin/env bash
# 푸시 전 로컬 검증 — CI 와 동일한 순서. 전부 통과해야 푸시한다.
# 사용: bash tools/verify.sh
set -u
cd "$(dirname "$0")/.."
FAIL=0

# ── venv 찾기 ──────────────────────────────────────────────
# 예전엔 /tmp/v3 하나로 하드코딩돼 있었다. 그런데 macOS 가 /tmp 를 주기적으로
# 비우기 때문에 어느 날 통째로 사라진다. 실제로 그렇게 날아갔고, 그때
# `mkdocs build --strict` 가 FAIL 로만 찍혀서 원인을 찾는 데 한참 걸렸다.
# 진짜 메시지(`mkdocs: command not found`)는 로그 꼬리 12줄 안에 있었는데
# 봇이 그걸 "빌드 실패" 로만 보고해 아무도 못 봤다.
#
# 그래서 두 가지를 바꿨다.
#   (1) 기본 위치를 지워지지 않는 ~/.venvs/ygstudy 로 옮긴다
#   (2) 없으면 검사를 시작하지 않고 **왜 없는지와 복구 명령**을 먼저 낸다
# 도구 부재를 "검사 실패" 로 보고하면 없는 결함을 쫓게 된다.
YG_VENV="${YG_VENV:-$HOME/.venvs/ygstudy}"
YG_TRIED=""
for cand in "$YG_VENV" /tmp/v3; do
  YG_TRIED="$YG_TRIED $cand"
  if [ -x "$cand/bin/mkdocs" ]; then YG_VENV="$cand"; break; fi
done
if [ ! -x "$YG_VENV/bin/mkdocs" ]; then
  echo "✗ mkdocs 를 못 찾았다 — 검사를 시작하지 않는다."
  # 실제로 뒤진 경로를 그대로 낸다. 여기에 고정 문구를 적어 두면 YG_VENV 를
  # 바꿔 돌렸을 때 "찾아본 곳" 이 거짓말이 된다.
  echo "  찾아본 곳:$YG_TRIED"
  echo "  이건 문서 결함이 아니라 도구 부재다. 아래 한 줄로 복구한다:"
  echo ""
  echo "    bash tools/setup_venv.sh"
  echo ""
  echo "  (/tmp 에 있던 venv 라면 macOS 가 비웠을 수 있다. 새 기본 위치는"
  echo "   ~/.venvs/ygstudy 라 다시 지워지지 않는다.)"
  exit 1
fi
export PATH="$YG_VENV/bin:$PATH"

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
# .pages 는 사이드바 구조 자체라 하나만 깨져도 빌드가 통째로 죽는다.
# 그때 나오는 건 PyYAML 스택 트레이스고 게이트에서는 그게 "mkdocs build
# --strict FAIL" 한 줄로 덮인다. 55초 기다린 끝에 어느 파일인지도 모르는
# 상태가 되므로, 빌드보다 먼저 3초 만에 파일·줄·이유를 낸다.
run "pages yaml"          python3 tools/check_pages_yaml.py --strict
run "gen_tags"            python3 tools/gen_tags.py --strict
run "check_frontmatter"   python3 tools/check_frontmatter.py --strict
run "check_mermaid"       python3 tools/check_mermaid_entities.py
run "checker_tests"       bash -c 'set -e; n=0; for t in tools/tests/test_*.py; do [ -e "$t" ] || continue; python3 "$t"; n=$((n+1)); done; [ "$n" -gt 0 ]'
run "check_links"         python3 tools/check_links.py --strict
# 다이어그램 글자 대비. 계산이 틀어지면 "그려지긴 하는데 안 읽히는" 상태가 되고
# 빌드는 통과한다. jsdom 없이 도는 순수 계산이라 게이트에 넣을 수 있다.
run "mermaid contrast"    node tools/tests/mermaid_contrast.test.mjs
# CSS 의 전경·배경 쌍. 한쪽 모드만 손보면 반대쪽이 조용히 깨진다.
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
# css contrast 는 빌드 뒤로 옮긴다 — 특이도 검사에 Material 스타일시트가 필요하다
# (빌드 산출물이 없으면 그 검사만 건너뛰고 대비 검사는 그대로 돈다)
YG_SITE_DIR=/tmp/_verify_site run "css contrast" python3 tools/check_contrast.py --strict
run "nav index"           python3 tools/check_nav_index.py /tmp/_verify_site --strict
SITE_DIR=/tmp/_verify_site run "redirects"        python3 tools/check_redirects.py
# 브라우저 없이 도는 DOM 테스트. 여기 걸리는 것들은 전부 **조용한 실패**라
# 빌드·링크 검사로는 절대 안 잡힌다 — 사이드바 펼침, 검색 인덱스 보류,
# 레이아웃 재계산, GitHub 릴리스 요청 차단, 링크 선반입.
#
# 이 파일들은 한동안 저장소에만 있고 게이트에는 없었다. 즉 회귀가 나도
# 아무도 안 돌리니 조용히 지나갔다. 테스트는 돌아야 테스트다.
# jsdom 이 없으면 각 테스트가 스스로 SKIP 하고 0 으로 끝난다.
run "브라우저 없는 DOM 테스트" bash -c '
  set -e
  for t in tools/tests/*.test.mjs; do
    case "$t" in *mermaid_contrast*) continue ;; esac   # 위에서 이미 돌았다
    echo "── $t"
    node "$t" /tmp/_verify_site
  done'

[ $FAIL -eq 0 ] && echo "✓ 전부 통과 — 푸시 가능" || echo "✗ 실패 있음 — 푸시하지 말 것"
exit $FAIL
