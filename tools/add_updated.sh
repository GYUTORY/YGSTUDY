#!/usr/bin/env bash
# updated 필드가 없는 .md 파일에 오늘 날짜를 일괄 삽입
# 사용: bash tools/add_updated.sh

TODAY=${1:-$(date +%Y-%m-%d)}
DOCS_DIR="Develop"
INSERTED=0

while IFS= read -r file; do
  [ -f "$file" ] || continue

  # 프론트매터 없으면 스킵
  if ! head -1 "$file" | grep -q '^---'; then
    continue
  fi

  # 두 번째 --- 직전에 updated 삽입
  awk -v today="$TODAY" '
    /^---/ { dash++ }
    dash == 2 && !inserted && !/^---/ {
      print "updated: " today
      inserted = 1
    }
    { print }
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

  INSERTED=$((INSERTED + 1))
done < <(grep -rL "^updated:" "$DOCS_DIR" --include="*.md")

echo "완료: ${INSERTED}개 파일에 updated: $TODAY 삽입"
