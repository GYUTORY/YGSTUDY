#!/usr/bin/env bash
# 문서 빌드용 venv 를 만든다. 이미 있으면 패키지만 맞춘다.
#
# 사용: bash tools/setup_venv.sh
#
# 왜 이 스크립트가 있나: 예전엔 venv 가 /tmp/v3 에 있었는데 macOS 가 /tmp 를
# 주기적으로 비운다. 어느 날 통째로 사라졌고, verify.sh 는 그걸 "mkdocs build
# --strict FAIL" 로만 보고해서 없는 문서 결함을 쫓게 만들었다. 기본 위치를
# 홈 아래로 옮기고, 복구를 한 줄로 만들었다.
set -eu
cd "$(dirname "$0")/.."

VENV="${YG_VENV:-$HOME/.venvs/ygstudy}"

if [ ! -x "$VENV/bin/python" ]; then
  echo "→ venv 생성: $VENV"
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
else
  echo "→ venv 있음: $VENV"
fi

echo "→ 패키지 설치 (requirements-docs.txt)"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r requirements-docs.txt

echo "→ jsdom · mermaid (브라우저 없는 DOM 테스트용)"
if command -v npm >/dev/null 2>&1; then
  npm i --silent >/dev/null 2>&1 || echo "   ⚠ npm i 실패 — DOM 테스트는 SKIP 된다"
else
  echo "   ⚠ npm 이 없다 — DOM 테스트는 SKIP 된다"
fi

echo ""
"$VENV/bin/mkdocs" --version
echo "✓ 준비 완료. 이제 'bash tools/verify.sh' 가 돈다."
