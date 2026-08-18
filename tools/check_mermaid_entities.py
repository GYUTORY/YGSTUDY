#!/usr/bin/env python3
"""sequenceDiagram 안의 이름 있는 HTML 엔티티를 잡는다.

mermaid 10.x 렉서는 `&word;` 를 액터 구분 문법으로 물어버려 파싱이 죽는다.
숫자 엔티티(`&#124;`)와 날것 `&`, `<`, `>`, 괄호, 콜론, 참여자명의 공백은 모두 안전하다.

주의 — 이 검사를 만든 이유:
mermaid 파스 에러는 실제 원인 줄이 아니라 **그 아래 줄**을 가리킨다. 렉서가 `&` 에서
잘못된 모드로 들어가 다음 줄까지 삼킨 뒤 에러를 보고하기 때문이다. 실제로 원인이
8행인데 에러는 9행으로 찍혔고, 그 탓에 엉뚱한 줄(괄호·콜론)을 세 번 고치며 헛돌았다.
줄 번호를 믿고 추적하지 말고 이 검사로 원인을 직접 짚을 것.

사용법:
  python3 tools/check_mermaid_entities.py          # 위반 시 exit 1
"""

import os
import re
import sys

ENTITY = re.compile(r"&[a-zA-Z][a-zA-Z0-9]*;")
FENCE = re.compile(r"```mermaid\n(.*?)```", re.S)


def main():
    bad = []
    # 저장소 루트가 아닌 곳에서 실행하면 상대경로 "Develop" 이 안 잡혀
    # 0건을 훑고 OK 를 찍는다. 0건 통과는 통과가 아니라 미검사다.
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Develop")
    fences = seq = 0
    for root, _, files in os.walk(docs_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            try:
                text = open(path, encoding="utf-8").read()
            except Exception:
                continue
            for m in FENCE.finditer(text):
                body = m.group(1)
                fences += 1
                if not body.strip().startswith("sequence"):
                    continue
                seq += 1
                base = text[: m.start()].count("\n") + 2
                for i, line in enumerate(body.splitlines()):
                    if ENTITY.search(line):
                        bad.append(f"{path}:{base + i}: {line.strip()[:80]}")

    if bad:
        print(f"sequenceDiagram 안에 이름 있는 HTML 엔티티 {len(bad)}건 — 파싱이 죽습니다.")
        print("  → 〈 〉 같은 타이포그래픽 문자나 날것 < > 로 바꾸세요.")
        print("\n".join("  " + b for b in bad))
        return 1
    if fences == 0:
        print(f"검사 대상이 0건입니다 — {docs_dir} 를 못 찾았습니다.")
        return 2
    print(f"OK: mermaid {fences}블록 중 sequenceDiagram {seq}블록 검사 — 엔티티 위반 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
