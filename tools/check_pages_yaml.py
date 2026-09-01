#!/usr/bin/env python3
"""`.pages` 파일이 YAML 로 파싱되는지 본다.

왜 필요한가: awesome-pages 의 `.pages` 는 사이드바 구조 자체다. 하나가
깨지면 **빌드가 통째로 죽는다.** 그런데 그때 화면에 나오는 건 PyYAML 의
스택 트레이스 20줄이고, 게이트에서는 그게 `mkdocs build --strict FAIL` 한
줄로 덮여 어느 파일인지도 안 보인다.

실제로 그 일이 났다. 봇이 만든 항목 하나가

    - React 내장 상태 관리: useState, useReducer, Context API: React_Built_in_State.md

였다. 제목 안에 콜론이 있어서 `키: 값` 이 두 번 나오는 꼴이 됐다. YAML 은
여기서 `mapping values are not allowed here` 를 던진다. 결과는 nav.json
미생성 + redirects 12건 MISSING SRC 로 번져서, 진짜 원인이 뭔지 알아보기
어려운 모양이 됐다. 한 줄 고치니 전부 통과했다.

**제목에 콜론을 쓰는 건 자연스러운 일**이라 앞으로도 또 난다. 그래서
빌드보다 먼저, 파일 이름과 줄과 이유를 그대로 내는 검사를 둔다.
55초짜리 빌드가 스택 트레이스로 죽는 것과, 3초 만에 "이 파일 이 줄" 이
나오는 것의 차이다.

사용: python3 tools/check_pages_yaml.py [--strict]
"""
import glob
import io
import os
import sys

try:
    import yaml
except ImportError:
    print("SKIP  PyYAML 이 없다 — venv 로 돌린다 (bash tools/setup_venv.sh)")
    sys.exit(0)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    strict = "--strict" in sys.argv
    files = sorted(glob.glob(os.path.join(ROOT, "Develop", "**", ".pages"), recursive=True))
    files += sorted(glob.glob(os.path.join(ROOT, "Develop", ".pages")))
    files = sorted(set(files))

    bad = []
    for path in files:
        raw = io.open(path, encoding="utf-8").read()
        rel = os.path.relpath(path, ROOT)
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            line = mark.line + 1 if mark else None
            why = getattr(e, "problem", None) or str(e).split("\n")[0]
            src = raw.split("\n")[mark.line] if mark and mark.line < len(raw.split("\n")) else ""
            bad.append((rel, line, why, src.strip()))
            continue
        # 파싱은 됐는데 구조가 이상한 경우도 잡는다
        if data is not None and not isinstance(data, dict):
            bad.append((rel, None, f"최상위가 매핑이 아니다 ({type(data).__name__})", ""))

    if bad:
        print(f"✗ .pages {len(files)}개 중 {len(bad)}개가 깨졌다 — 빌드가 여기서 죽는다\n")
        for rel, line, why, src in bad:
            where = f"{rel}:{line}" if line else rel
            print(f"  {where}")
            print(f"      {why}")
            if src:
                print(f"      > {src}")
            if "mapping values are not allowed" in why:
                print("      제목에 콜론이 있으면 따옴표로 감싼다:")
                print('      - "제목: 부제": 파일.md')
            print()
        if strict:
            sys.exit(1)
    else:
        print(f"✓ .pages {len(files)}개 전부 파싱된다.")


if __name__ == "__main__":
    main()
