#!/usr/bin/env bash
# updated 필드가 없는 .md 파일에 마지막 git 커밋 날짜를 삽입
DOCS_DIR="Develop"
FIXED=0

while IFS= read -r file; do
  [ -f "$file" ] || continue

  # 프론트매터 없으면 스킵
  head -1 "$file" | grep -q '^---' || continue

  # 마지막 커밋 날짜 (없으면 오늘)
  GIT_DATE=$(git log -1 --format=%ad --date=format:%Y-%m-%d -- "$file" 2>/dev/null)
  [ -z "$GIT_DATE" ] && GIT_DATE=$(date +%Y-%m-%d)

  # 두 번째 --- 직전에 updated 삽입
  awk -v date="$GIT_DATE" '
    /^---/ {
      dash++
      if (dash == 2 && !inserted) {
        print "updated: " date
        inserted = 1
      }
    }
    { print }
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

  FIXED=$((FIXED + 1))
done < <(grep -rL "^updated:" "$DOCS_DIR" --include="*.md")

echo "완료: ${FIXED}개 파일 updated 백필"
