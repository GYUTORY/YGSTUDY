# 게이트 부채 등록부

배포 복구를 위해 `|| true` 로 내려둔 게이트 목록.
**이 상태로 방치하면 게이트는 이름만 남고 실효 0.**

복원 완료 항목은 이 파일에서 행을 삭제하고 커밋한다.

## 현황

| 게이트 | 현재 | 차단 사유 | 복원 조건 | 정의 위치 |
|--------|------|-----------|-----------|-----------|
| gen_tags.py | `\|\| true` | 고유 태그 2,951 / 1회성 1,887 / 위반 문서 1,103 | 태그 정리 후 `--strict` | `.github/actions/docs-checks/action.yml` |
| check_sources.py | `\|\| true` | 위반 403/1,158. utf8mb4→'8mb', Java 8·Go 1 오탐, RFC 번호 위반 처리 | 패턴 정밀화 완료 → 재실측 후 `--strict` | `.github/actions/docs-checks/action.yml` |
| check_frontmatter.py | `--strict` | — | 유지 | — |
| check_links.py | `--strict` | — | 유지 | — |
| mkdocs build | `--strict` | — | 유지 | — |

## 복원 절차

1. 복원 조건 충족 확인 (로컬에서 `--strict` 로 직접 실행)
2. `action.yml` 에서 해당 스텝의 `|| true` 제거 또는 `--strict` 추가
3. CI 통과 확인
4. 이 파일에서 해당 행 삭제 후 커밋

## 사고 이력

| 날짜 | 원인 | 중단 시간 | 교훈 |
|------|------|-----------|------|
| 2026-08-07 | `mkdocs.yml` rss 플러그인 `feeds_filenames` 잘못된 키 | 약 5.5시간 | 로컬 `mkdocs build --strict` 가 가장 빠른 진단 |

## 운영 원칙

1. **게이트는 통과하는 상태를 먼저 만들고 켠다.**
   못 넘는 게이트는 방어선이 아니라 벽이다. `|| true` 4개를 동시에 켠 것이 이번 사고의 근본 원인.

2. **되돌릴 때는 하나씩 켜고 하나씩 푸시해 검증한다.**
   `--strict` 특성상 첫 오류에서 중단하므로, 여러 개를 동시에 켜면 한 번에 하나씩만 드러나 사이클이 배가된다.

3. **배포 성공을 능동적으로 감시한다.**
   5.5시간 동안 아무도 몰랐던 게 가장 큰 문제. Deploy 워크플로 실패 시 알림(GitHub 알림 설정 또는 웹훅)을 붙여라. 실패가 조용하면 게이트는 의미가 없다.

4. **CI 로그를 못 볼 때는 로컬 재현이 답이다.**
   `pip install -r requirements-docs.txt && mkdocs build --strict` 로 몇 분이면 동일 결과를 얻는다.

## 별건 추적

| 항목 | 상태 | 비고 |
|------|------|------|
| 대문 문서 수 카운터 `data-yg-total` 대시 | 확인 필요 | `extra.js` sitemap.xml fetch 실패 가능성. 브라우저에서 직접 확인 필요 |
| 앵커 링크 어긋남 (INFO) | 낮은 우선순위 | MQTT.md, AMQP vs MQTT.md, Forward_Proxy.md. 빌드는 통과, 제목 변경 후 앵커 밀림 가능 |
| 저장소 용량 (GitHub 6.13GiB) | 추적 중 | `git count-objects -vH` 로 실측 후 BFG/git-filter-repo 검토 |
| 태그 정리 (문서 1,164개) | 별도 회차 | 허용 목록 확장으로 해결 불가. `tools/tags.yml` 61개 기준으로 문서 태그 매핑 필요 |
