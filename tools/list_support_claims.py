#!/usr/bin/env python3
"""제품·라이브러리의 '지원 부재'를 단정하는 문장 중 시점/버전 스코프가 없는 것을 나열한다.

게이트가 아니다. 언제나 exit 0 이고, 목록만 출력한다.

왜 게이트가 아닌가:
  검출 150건 중 실제로 스코프가 필요한 건 20건 남짓이다(정밀도 ~15%).
  걸리는 것 대부분은 릴리스로 뒤집히지 않는 설계 사실이다 —
  "DynamoDB는 JOIN을 지원하지 않는다", "Bash는 소수점 계산을 지원하지 않는다",
  "getopts는 long option을 지원하지 않는다" 류.
  이걸 빌드 실패로 만들면 check_sources.py 가 겪은 길(오탐이 많아 `|| true` 로 꺼짐)을
  그대로 반복한다. 그래서 분기에 한 번 사람이 훑는 목록으로 쓴다.

왜 이 목록이 필요한가:
  낡은 전제는 저장소 안에서 닫히지 않는다. 링크나 산술과 달리 바깥이 움직였는지를
  알아야 판정된다. 자동 검사가 불가능한 대신, 후보를 좁혀두면 사람이 훑는 비용이 준다.
  스코프가 붙은 문장은 자동으로 빠지므로 규약이 정착할수록 목록이 줄어든다.

한계 (재현율 ~89%):
  가장 위험한 문장이 가장 안 잡힌다. 단정적으로 쓸수록 '아직'·'현재' 같은 표시가
  사라지기 때문이다. "PostgreSQL은 SQL:2011 APPLICATION_TIME을 네이티브로 지원하지
  않는다" 에는 시간 표시가 없다. 이 목록은 사람 검토를 돕는 것이지 대신하지 않는다.

스코프를 다는 형태는 셋을 섞는다. 하나로 통일하려 하면 억지가 된다:
  문서가 버전을 이미 밝혔으면 버전   — "Prisma 5 기준"
  플랫폼 버전 축이 있으면 그것       — "Fargate 1.3.0 미만"
  둘 다 없으면 날짜                  — "2024년 기준으로"

사용법:
  python3 tools/list_support_claims.py            # 사람이 읽는 목록
  python3 tools/list_support_claims.py --json     # CI 아티팩트용
  python3 tools/list_support_claims.py --stats    # 건수만
  python3 tools/list_support_claims.py --all      # 스코프 있는 것까지 전부
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"

CLAIM_RE = re.compile(
    r"(?:"
    r"공식(?:적으로|적인)?\s*(?:지원|기능|문법|타입|패키지|드라이버|구현|API|방법)"
    r"[^.\n]{0,8}?(?:없|않는|안\s*된|않았)"
    r"|(?:네이티브|내장|빌트인)(?:으로|하게)?\s*"
    r"(?:지원|함수|기능|API|구현|타입|옵션|설정)?[^.\n]{0,8}?(?:없|않는|않아|미지원)"
    r"|지원(?:하지|되지)\s*않(?:는다|아|고|으며|는)"
    r"|아직\s*[^.\n]{0,25}?(?:정식\s*)?(?:지원|제공|구현)[^.\n]{0,8}?(?:없|않|전이|안)"
    r"|정식\s*지원이\s*없"
    r")"
)

SCOPE_RES = [
    re.compile(r"20\d\d[-./\s]?\d{0,2}\s*(?:년|월)?\s*(?:기준|현재|시점)|기준까지|현재\s*기준"),
    re.compile(
        r"\d+\.\d+(?:\.\d+)?\s*(?:이상|이하|이전|이후|부터|까지|미만|기준)"
        r"|\bv\d+(?:\.\d+)*\b"
        r"|(?:[A-Z][A-Za-z.+#-]{1,20}|Node|Java|Python|Go)\s*\d+(?:\.\d+)?\s*"
        r"(?:이상|이하|이전|이후|부터|까지|기준|에서)"
    ),
    re.compile(r"오픈소스\s*(?:버전|판)|Community\s*Edition|무료\s*버전|(?:Plus|Enterprise)\s*(?:버전|판)"),
]

COND_RE = re.compile(r"(?:하면|경우(?:가|에|엔|는)?\s|면\s|때\s|라면|으면)")

STOPWORDS = {
    "The", "This", "That", "When", "Where", "What", "With", "From", "And", "But",
    "For", "Not", "You", "OK", "ID", "CRUD", "REST", "RPC", "CLI", "GUI", "SDK",
    "IDE", "VM", "API", "HTTP", "JSON", "URL", "TCP", "UDP", "DNS", "TLS", "SSL",
    "CPU", "RAM", "SQL", "YAML", "URI", "UUID", "OS", "DB",
}
PROPER_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.#_-]{2,24}\b")
BACKTICK_RE = re.compile(r"`([A-Za-z_][\w.\-]{2,})`")


def strip_fences(text):
    """코드 펜스 내용을 비우되 줄 수는 보존한다 (줄 번호가 밀리지 않게)."""
    out, in_fence, marker = [], False, None
    for line in text.split("\n"):
        stripped = line.lstrip()
        m = re.match(r"^(`{3,}|~{3,})", stripped)
        if m and not in_fence:
            in_fence, marker = True, m.group(1)[0]
            out.append("")
            continue
        if in_fence:
            if re.match(r"^(`{3,}|~{3,})\s*$", stripped) and stripped[0] == marker:
                in_fence = False
            out.append("")
            continue
        out.append(line)
    return out


def read_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].split("\n"):
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def named_subject(sentence):
    """문장에 제품·기술 이름이 있으면 그 첫 토큰을 반환."""
    m = BACKTICK_RE.search(sentence)
    if m:
        return m.group(1)
    for m in PROPER_RE.finditer(sentence):
        w = m.group()
        if w not in STOPWORDS and len(w) >= 3:
            return w
    return None


def scan():
    rows = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = read_frontmatter(text)
        for i, line in enumerate(strip_fences(text)):
            if not line.strip() or line.lstrip().startswith("|"):
                continue
            for sent in re.split(r"(?<=[.。!?])\s+|(?<=다)\.\s*", line):
                sent = sent.strip()
                if len(sent) < 15:
                    continue
                m = CLAIM_RE.search(sent)
                if not m:
                    continue
                if COND_RE.search(sent[: m.start()]):
                    continue
                subject = named_subject(sent)
                if not subject:
                    continue
                rows.append({
                    "file": str(path.relative_to(REPO_ROOT)),
                    "line": i + 1,
                    "updated": fm.get("updated", ""),
                    "subject": subject,
                    "scoped": any(r.search(sent) for r in SCOPE_RES),
                    "text": sent[:240],
                })
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="JSON 출력 (CI 아티팩트용)")
    ap.add_argument("--stats", action="store_true", help="건수만 출력")
    ap.add_argument("--all", action="store_true", help="스코프가 이미 있는 것까지 전부")
    args = ap.parse_args()

    rows = scan()
    unscoped = [r for r in rows if not r["scoped"]]
    target = rows if args.all else unscoped

    if args.json:
        json.dump(target, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0

    print(f"지원 부재 단정문 {len(rows)}건 "
          f"— 스코프 있음 {len(rows) - len(unscoped)} / 없음 {len(unscoped)}")
    if args.stats:
        return 0

    print("\n아래는 '시점 또는 버전 스코프가 없는' 문장이다.")
    print("전부 고칠 대상이 아니다 — 릴리스로 뒤집힐 수 있는 것만 고르면 된다.")
    print("(바뀌지 않는 설계 사실은 그대로 두는 게 맞다)\n")
    for r in target:
        mark = "  " if r["scoped"] else "* "
        print(f"{mark}{r['file']}:{r['line']}  [upd {r['updated'] or '?'}]  <{r['subject']}>")
        print(f"    {r['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
