#!/usr/bin/env python3
"""버전·수치·벤치마크 주장이 있는 문서 중 외부 출처 링크가 없는 것을 검출한다.

사용법:
  python3 tools/check_sources.py             # 전체 스캔 (경고만)
  python3 tools/check_sources.py --strict    # 최근 90일 변경 파일만 검사, 위반 시 exit 1
  python3 tools/check_sources.py --file path/to/file.md  # 단일 파일 검사
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / "Develop"

# 사실 주장 패턴 — 출처가 필요한 서술
CLAIM_PATTERNS = [
    r"\bv\d+\.\d+",                          # v1.23 같은 버전 표기
    r"(?:Node\.js|Java|Python|Go|Rust|PHP|Ruby|Kotlin|Swift)\s+\d+",  # 런타임 버전
    r"\d+(?:\.\d+)?\s*(?:ms|μs|ns|MB|GB|KB|초|밀리초|마이크로초)",  # 수치 측정값
    r"\d+(?:\.\d+)?\s*%\s*(?:빠르|느리|향상|감소|개선|절약)",       # 성능 수치 비교
    r"(?:벤치마크|benchmark|autocannon|wrk|ab\s+테스트|JMH|k6)",     # 벤치마크 도구
    r"(?:~부터\s*지원|버전부터\s*(?:지원|추가|도입))",               # 버전별 지원 여부
    r"(?:deprecated|폐기|제거됨)\s+(?:in|in\s+v|since\s+v)",        # deprecation 버전
    r"(?:RFC|ISO|OWASP)\s*\d+",                                     # 표준 문서 참조
]

EXTERNAL_LINK_RE = re.compile(r"https?://(?!(?:localhost|127\.|example\.com|evil\.com))")


def has_claim(text: str) -> list[str]:
    found = []
    for pat in CLAIM_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            found.append(m.group(0))
    return found


def has_external_link(text: str) -> bool:
    return bool(EXTERNAL_LINK_RE.search(text))


def get_recent_files(days: int = 90) -> set[Path]:
    result = subprocess.run(
        ["git", "log", f"--since={days} days ago", "--name-only", "--pretty=format:"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
    )
    paths = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.endswith(".md"):
            p = ROOT.parent / line
            if p.exists():
                paths.add(p)
    return paths


def check_file(path: Path) -> tuple[bool, list[str]]:
    """(위반여부, 매칭된_주장들) 반환"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False, []

    # 코드블록 내부 제거 (언어 태그 없는 것 포함)
    text_no_code = re.sub(r"```[\s\S]*?```", "", text)

    claims = has_claim(text_no_code)
    if not claims:
        return False, []

    if has_external_link(text):
        return False, []

    return True, claims


def main():
    strict = "--strict" in sys.argv
    single_file = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        single_file = Path(sys.argv[idx + 1])

    if single_file:
        targets = [single_file]
    elif strict:
        targets = list(get_recent_files(90))
        print(f"최근 90일 변경 파일 {len(targets)}개 검사")
    else:
        targets = list(ROOT.rglob("*.md"))
        print(f"전체 {len(targets)}개 파일 검사")

    violations = []
    for path in sorted(targets):
        violated, claims = check_file(path)
        if violated:
            rel = path.relative_to(ROOT.parent)
            violations.append((rel, claims))

    if not violations:
        print("✓ 출처 위반 없음")
        sys.exit(0)

    print(f"\n출처 필요 문서 {len(violations)}개:\n")
    for rel, claims in violations:
        print(f"  {rel}")
        print(f"    주장 예시: {', '.join(claims[:3])}")

    if strict:
        print(f"\n[STRICT] {len(violations)}건 위반 — CI 실패")
        sys.exit(1)
    else:
        print(f"\n(--strict 없이 실행 시 exit 0)")


if __name__ == "__main__":
    main()
