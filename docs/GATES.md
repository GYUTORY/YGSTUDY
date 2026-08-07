# 게이트 부채 등록부

배포 복구를 위해 `|| true` 로 내려둔 게이트 목록.
**이 상태로 방치하면 게이트는 이름만 남고 실효 0.**

복원 완료 항목은 이 파일에서 행을 삭제하고 커밋한다.

## 현황

| 게이트 | 정의 위치 | 현재 상태 | 복원 조건 | 내린 날짜 |
|--------|-----------|-----------|-----------|-----------|
| Check tags | `.github/actions/docs-checks/action.yml` | `\|\| true` | `gen_tags.py --strict` 통과 확인 후 `\|\| true` 제거 | 2026-08-06 |
| Check sources | `.github/actions/docs-checks/action.yml` | `\|\| true` | 패턴 정밀화 + push diff 모드 검증 후 `--strict` 복원 | 2026-08-07 |

## 복원 절차

1. 복원 조건 충족 확인 (로컬에서 `--strict` 로 직접 실행)
2. `action.yml` 에서 해당 스텝의 `|| true` 제거 또는 `--strict` 추가
3. CI 통과 확인
4. 이 파일에서 해당 행 삭제 후 커밋

## 사고 이력

| 날짜 | 원인 | 중단 시간 | 교훈 |
|------|------|-----------|------|
| 2026-08-07 | `mkdocs.yml` rss 플러그인 `feeds_filenames` 잘못된 키 | 약 5.5시간 | 로컬 `mkdocs build --strict` 가 가장 빠른 진단 |
