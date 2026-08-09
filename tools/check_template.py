#!/usr/bin/env python3
"""문서가 판박이 틀로 찍혔는지 검사한다.

배경 → 핵심 → 예시 → 운영 팁 → 참고 라는 H2 골격이 51개 문서에 글자 하나 안 틀리고
동일했다. never·unknown·void 처럼 성격이 다른 주제가 같은 5단 틀에 들어가 있으면
읽는 사람은 즉시 "찍어낸 것"임을 안다. void 문서의 "성능 최적화" 절에는 void 와
아무 상관 없는 메모이제이션 예제가 들어 있었다 — 틀이 칸을 요구하니 없는 내용을
만들어 채운 것이다.

섹션은 주제가 정해야 한다. 틀을 먼저 잡고 채우면 안 된다.

사용법:
  python3 tools/check_template.py                 # 전체 (경고만)
  python3 tools/check_template.py --file X.md     # 단일 파일
  python3 tools/check_template.py --strict        # 위반 시 exit 1
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / "Develop"

# 주제와 무관하게 반복되는 무의미한 제목.
BANNED_HEADINGS = {
    "배경", "핵심", "예시", "운영 팁",
    "성능 최적화", "에러 처리", "고급 패턴", "실제 사용 사례",
}

# 이 골격이 그대로 나오면 틀로 찍은 것이다.
TEMPLATE_SKELETON = ["배경", "핵심", "예시", "운영 팁", "참고"]

H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)


def check(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    heads = [h.strip() for h in H2.findall(text)]
    issues = []

    banned = [h for h in heads if h in BANNED_HEADINGS]
    if banned:
        issues.append("무의미한 제목: " + ", ".join(sorted(set(banned))))

    if heads[: len(TEMPLATE_SKELETON)] == TEMPLATE_SKELETON:
        issues.append("판박이 골격(배경→핵심→예시→운영 팁→참고) 그대로")

    return issues


def main():
    strict = "--strict" in sys.argv
    if "--file" in sys.argv:
        targets = [Path(sys.argv[sys.argv.index("--file") + 1])]
    else:
        targets = sorted(ROOT.rglob("*.md"))

    bad = []
    for p in targets:
        if p.name == "index.md":
            continue
        for msg in check(p):
            bad.append(f"{p}: {msg}")

    if not bad:
        print(f"OK: 틀 위반 없음 ({len(targets)}개 검사)")
        return 0

    print(f"틀로 찍힌 문서 {len(bad)}건:")
    print("\n".join("  " + b for b in bad[:40]))
    if len(bad) > 40:
        print(f"  ... 외 {len(bad) - 40}건")
    print("\n섹션 제목은 그 문서가 실제로 할 말에서 나와야 합니다.")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
