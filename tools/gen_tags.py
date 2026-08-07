#!/usr/bin/env python3
"""
태그 통제 어휘 검증 스크립트.

tools/tags.yml 의 allowed 목록과 비교해 위반 태그를 보고합니다.
CI 에서 실행: python3 tools/gen_tags.py [--strict]
  --strict: 위반 태그 발견 시 exit code 1 반환
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML 필요: pip install pyyaml")
    sys.exit(2)

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "Develop"
TAGS_YML = Path(__file__).parent / "tags.yml"


def load_allowed():
    with open(TAGS_YML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {t.lower() for t in data.get("allowed", [])}


def scan_violations(allowed):
    violations = []  # [(file, tag)]
    tag_pat = re.compile(r"^tags:\s*\[(.+?)\]", re.MULTILINE)

    for md in DOCS_DIR.rglob("*.md"):
        try:
            content = md.read_text(encoding="utf-8")
        except Exception:
            continue
        m = tag_pat.search(content)
        if not m:
            continue
        for raw in m.group(1).split(","):
            tag = raw.strip().lower()
            if tag and tag not in allowed:
                violations.append((str(md.relative_to(REPO_ROOT)), tag))

    return violations


def main():
    parser = argparse.ArgumentParser(description="태그 통제 어휘 검증")
    parser.add_argument("--strict", action="store_true", help="위반 시 exit 1")
    args = parser.parse_args()

    allowed = load_allowed()
    violations = scan_violations(allowed)

    if not violations:
        print(f"✓ 모든 태그가 허용 목록({len(allowed)}개) 안에 있습니다.")
        return

    # 태그별로 묶어서 출력
    from collections import defaultdict
    by_tag = defaultdict(list)
    for path, tag in violations:
        by_tag[tag].append(path)

    print(f"⚠ 비허용 태그 {len(by_tag)}종 / 총 {len(violations)}건:\n")
    for tag in sorted(by_tag, key=lambda t: -len(by_tag[t])):
        print(f"  [{len(by_tag[tag]):3d}건] {tag}")
        for p in by_tag[tag][:3]:
            print(f"          {p}")
        if len(by_tag[tag]) > 3:
            print(f"          ... 외 {len(by_tag[tag]) - 3}개")

    print(f"\n허용 태그 목록: {TAGS_YML}")
    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
