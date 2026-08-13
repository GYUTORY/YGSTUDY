#!/usr/bin/env python3
"""버전·수치·벤치마크 주장이 있는 문서 중 외부 출처 링크가 없는 것을 검출한다.

사용법:
  python3 tools/check_sources.py             # 전체 스캔 (경고만)
  python3 tools/check_sources.py --strict    # 최근 90일 변경 파일만 검사, 위반 시 exit 1
  python3 tools/check_sources.py --file path/to/file.md  # 단일 파일 검사
  python3 tools/check_sources.py --file X.md --base-ref SHA --strict
                                             # SHA 대비 새로 추가된 줄만 검사
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / "Develop"

# 사실 주장 패턴 — 출처가 필요한 서술
#
# 정밀도 우선. 넓게 잡았을 때 131건이 걸렸는데 대부분이 오탐이었다:
#   "타임아웃 5초"(설명), "메모리 64MB"(문제 조건), "벤치마크를 돌려보면"(도구 언급),
#   "Java 21"(맥락), "v1.2"(목차). 전부 출처를 요구할 성질이 아니다.
# 그래서 게이트가 `|| true` 로 꺼져 있었다 — 오탐이 많으면 아무도 안 본다.
#
# 남긴 것은 "검증 가능한 정량 비교 주장"뿐이다. 이건 근거 없이 쓰면 실제로 틀린다.
CLAIM_PATTERNS = [
    # "30% 빨라진다" 류 — 비율로 성능을 단정하는 문장
    r"\d+(?:\.\d+)?\s*%\s*(?:이상\s*)?(?:더\s*)?(?:빠르|느리|향상|감소|개선|절약|단축|증가)",
    # "2배 빠르다" 류
    r"\d+(?:\.\d+)?\s*배\s*(?:이상\s*)?(?:더\s*)?(?:빠르|느리|향상|개선)",
    # 벤치마크 '결과'를 수치로 제시하는 경우 (도구 이름만 언급하는 건 제외)
    r"(?:벤치마크|benchmark)\s*(?:결과|상)?[^\n]{0,24}?\d+(?:\.\d+)?\s*(?:%|배|ms|req/s|rps|tps)",
    # RFC/ISO/OWASP 는 그 자체가 출처이므로 제외
]

# 측정값 단독은 주장이 아니다. 같은 줄에 비교 서술이 있을 때만 주장으로 본다.
# (?<![A-Za-z]) — 앞에 영문자가 붙으면 측정값이 아님 (utf8mb4의 '8mb' 오탐 방지)
_MEASUREMENT_RE = re.compile(
    r"(?<![A-Za-z])\d+(?:\.\d+)?\s*(?:ms|μs|ns|MB|GB|KB)",
    re.IGNORECASE,
)
# "성능"·"벤치마크" 같은 단어가 스쳐 지나가는 줄까지 잡던 것을 좁혔다.
# 두 대상을 견주는 표현이 있을 때만 근거를 요구한다.
_COMPARISON_CTX_RE = re.compile(
    r"(?:대비|보다)\s*\S*\s*(?:빠르|느리|향상|감소|개선|절약)|"
    r"(?:빠르|느리)(?:다|고|며|지만)|측정\s*결과|벤치마크\s*결과",
)

EXTERNAL_LINK_RE = re.compile(r"https?://(?!(?:localhost|127\.|example\.com|evil\.com))")


def has_claim(text: str) -> list[str]:
    found = []
    for pat in CLAIM_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            found.append(m.group(0))
    # 측정값은 비교 맥락 줄에서만 주장으로 판단
    for line in text.splitlines():
        m = _MEASUREMENT_RE.search(line)
        if m and _COMPARISON_CTX_RE.search(line):
            found.append(m.group(0))
            break
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


def get_push_diff_files() -> set[Path]:
    """BEFORE_SHA/AFTER_SHA 환경변수가 있으면 push diff 기준으로 검사.
    없으면 최근 90일 fallback. NFC 일괄 정규화 같은 대량 변경이 전체 검사를 유발하는 문제 방지."""
    before = os.environ.get("BEFORE_SHA", "").strip()
    after = os.environ.get("AFTER_SHA", "HEAD").strip() or "HEAD"
    if not before or before == "0000000000000000000000000000000000000000":
        return get_recent_files(90)
    result = subprocess.run(
        ["git", "diff", "--name-only", before, after],
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


def added_lines(path: Path, base_ref: str) -> str | None:
    """base_ref 대비 이 파일에서 새로 추가된 줄만 이어붙여 반환.

    오래된 문서를 한 줄만 고쳐도 파일 전체의 과거 무출처 주장이 걸리면
    게이트로 쓸 수 없다. 이번에 새로 들어온 주장만 보기 위한 것.
    diff 를 얻지 못하면 None(=전체 검사로 폴백).
    """
    try:
        r = subprocess.run(
            ["git", "diff", "--unified=0", base_ref, "--", str(path)],
            capture_output=True, text=True, cwd=ROOT.parent,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = []
    for line in r.stdout.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            out.append(line[1:])
    return "\n".join(out)


def check_file(path: Path, base_ref: str | None = None) -> tuple[bool, list[str]]:
    """(위반여부, 매칭된_주장들) 반환"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False, []

    # 주장 탐지 대상. base_ref 가 있으면 새로 추가된 줄만 본다.
    target = text
    if base_ref:
        added = added_lines(path, base_ref)
        if added is not None:
            target = added

    # 코드블록 내부 제거 (언어 태그 없는 것 포함)
    text_no_code = re.sub(r"```[\s\S]*?```", "", target)

    claims = has_claim(text_no_code)
    if not claims:
        return False, []

    # 출처 링크는 파일 전체에서 찾는다. 문서 어딘가에 근거가 있으면 통과.
    if has_external_link(text):
        return False, []

    return True, claims


def main():
    strict = "--strict" in sys.argv
    base_ref = None
    if "--base-ref" in sys.argv:
        base_ref = sys.argv[sys.argv.index("--base-ref") + 1]
    else:
        # 명시적으로 안 줬으면 push diff 기준을 그대로 쓴다.
        # get_push_diff_files 가 "어떤 파일"을 고르고, base_ref 가 "그 파일의 어느 줄"을 고른다.
        # 둘을 같이 걸어야 오래된 문서를 한 줄만 고쳤을 때 과거 부채가 안 걸린다.
        _before = os.environ.get("BEFORE_SHA", "").strip()
        if _before and _before != "0000000000000000000000000000000000000000":
            base_ref = _before

    single_file = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        single_file = Path(sys.argv[idx + 1])

    if single_file:
        targets = [single_file]
    elif strict:
        before = os.environ.get("BEFORE_SHA", "").strip()
        targets = list(get_push_diff_files())
        if before and before != "0000000000000000000000000000000000000000":
            print(f"푸시 diff 파일 {len(targets)}개 검사 ({before[:8]}..HEAD)")
        else:
            print(f"최근 90일 변경 파일 {len(targets)}개 검사")
    else:
        targets = list(ROOT.rglob("*.md"))
        print(f"전체 {len(targets)}개 파일 검사")

    violations = []
    for path in sorted(targets):
        violated, claims = check_file(path, base_ref)
        if violated:
            # --file 로 상대경로를 주면 relative_to 가 ValueError 로 죽었다.
            # 표시용 경로일 뿐이라 실패하면 받은 경로를 그대로 쓴다.
            try:
                rel = path.resolve().relative_to(ROOT.parent.resolve())
            except ValueError:
                rel = path
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
