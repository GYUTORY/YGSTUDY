#!/usr/bin/env bash
# git 훅 설치 (pre-commit, pre-push)
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"

install_hook() {
  local name="$1"
  local src="$REPO_ROOT/tools/hooks/$name"
  local dst="$REPO_ROOT/.git/hooks/$name"
  if [ -f "$dst" ] && [ ! -L "$dst" ]; then
    echo "기존 $name 훅이 있습니다. ${dst}.bak 으로 백업합니다."
    mv "$dst" "${dst}.bak"
  fi
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "✓ $name 훅 설치 완료: $dst"
}

install_hook pre-commit
install_hook pre-push
