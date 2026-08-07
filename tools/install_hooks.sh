#!/usr/bin/env bash
# git pre-commit 훅 설치
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$REPO_ROOT/tools/hooks/pre-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

if [ -f "$HOOK_DST" ] && [ ! -L "$HOOK_DST" ]; then
  echo "기존 pre-commit 훅이 있습니다. $HOOK_DST.bak 으로 백업합니다."
  mv "$HOOK_DST" "$HOOK_DST.bak"
fi

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "✓ pre-commit 훅 설치 완료: $HOOK_DST"
