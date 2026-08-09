# 게이트 부채 등록부

모든 게이트 `--strict` 복원 완료 (2026-08-09).

## 현황

| 게이트 | 현재 | 비고 |
|--------|------|------|
| gen_tags.py | `--strict` | 태그 3,038종 → 65종 정규화 완료 (`6e0b5cc`) |
| check_sources.py | `--strict` | 전체 스캔 131건 잔존, CI는 push diff 새 줄만 검사 |
| check_frontmatter.py | `--strict` | — |
| check_links.py | `--strict` | — |
| mkdocs build | `--strict` | — |

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
| 태그 정리 (문서 1,164개) | ✅ 완료 | `6e0b5cc` — 태그 3,038종 → 65종 정규화, gen_tags.py 전건 통과 |
