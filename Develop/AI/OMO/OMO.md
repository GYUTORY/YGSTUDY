---
title: Oh My Open Code (OMO)
tags: [ai, omo, open-source, aider, cursor, ollama, agentic-coding]
updated: 2026-06-29
---

# Oh My Open Code (OMO)

## 1. OMO란

Oh My Open Code(OMO)는 특정 벤더에 묶이지 않는 오픈소스 AI 코딩 도구를 한 설정으로 묶어 쓰는 에코시스템이다. Aider, Cursor 같은 도구를 각자 따로 설정하는 대신, OMO가 공통 설정 파일과 모델 백엔드 추상화를 제공해서 도구 사이를 옮겨다닐 때 설정을 다시 짜지 않게 해준다.

이름은 `oh-my-zsh`에서 따왔다. zsh 설정을 플러그인 단위로 관리하듯, AI 코딩 도구의 모델·프롬프트·컨텍스트 규칙을 한 곳에서 관리한다는 발상이다.

핵심은 두 가지다.

- 모델 백엔드를 코드와 분리한다. 같은 워크플로우를 로컬 Ollama로도, 원격 API로도 돌린다.
- 도구별 설정을 하나의 `omo.yaml`로 모은다. Aider의 `.aider.conf.yml`, Cursor의 규칙 파일을 OMO가 생성하고 동기화한다.

## 2. 등장 배경

Claude Code, Codex 같은 도구는 편하지만 벤더에 종속된다. 모델을 못 바꾸고, 설정이 그 도구 안에 갇히고, 회사가 가격 정책을 바꾸면 그대로 따라가야 한다. 사내망 격리 환경에서 외부 API를 못 쓰는 경우도 많다.

실무에서 자주 겪는 상황은 이렇다. 개인 프로젝트는 원격 API로 빠르게, 회사 코드는 보안 때문에 로컬 모델로만 돌려야 한다. 도구가 벤더에 묶여 있으면 환경마다 다른 도구를 쓰고 설정을 두 벌 관리하게 된다.

OMO는 이 지점을 노린다. 도구와 모델을 분리하고, 설정을 한 벌로 유지해서 환경이 바뀌어도 같은 워크플로우를 쓰게 한다.

## 3. 구성 요소

OMO 자체는 오케스트레이션 레이어다. 실제 코드 생성은 연동된 도구가 한다.

| 레이어 | 역할 | 대표 도구 |
|--------|------|-----------|
| 설정 | 공통 설정 관리, 도구별 설정 생성 | `omo` CLI |
| 코딩 도구 | 실제 편집·생성 | Aider, Cursor |
| 모델 백엔드 | 추론 | Ollama(로컬), OpenAI·Anthropic·기타 API(원격) |
| 라우팅 | 작업별 모델 선택 | OMO 라우터 |

연동 방식은 어댑터 구조다. OMO가 도구별 어댑터를 두고, 공통 설정을 각 도구가 읽는 형식으로 변환한다. Aider는 `.aider.conf.yml`과 환경변수로, Cursor는 규칙 파일과 모델 설정으로 받는다. 도구를 추가하려면 해당 어댑터만 붙이면 된다.

## 4. 설치 및 기본 설정

설치는 CLI 하나로 끝난다.

```bash
# pipx 권장 (전역 의존성 오염 방지)
pipx install oh-my-open-code

# 프로젝트 루트에서 초기화
cd ~/projects/my-service
omo init
```

`omo init`을 돌리면 프로젝트 루트에 `omo.yaml`이 생긴다.

```yaml
# omo.yaml
version: 1

# 기본으로 쓸 모델 프로파일
default_backend: remote-claude

backends:
  remote-claude:
    type: api
    provider: anthropic
    model: claude-opus-4-8
    api_key_env: ANTHROPIC_API_KEY   # 키는 파일에 직접 쓰지 않는다

  local-qwen:
    type: ollama
    model: qwen2.5-coder:32b
    host: http://localhost:11434

# OMO가 관리할 도구
tools:
  - aider
  - cursor

# 컨텍스트에서 항상 제외할 경로
ignore:
  - node_modules
  - dist
  - "*.log"
```

설정을 저장한 뒤 동기화를 돌리면 OMO가 각 도구 설정 파일을 만들어준다.

```bash
omo sync
# .aider.conf.yml 생성/갱신
# .cursor/rules 생성/갱신
```

이후 Aider든 Cursor든 평소처럼 실행하면 OMO가 만든 설정을 그대로 읽는다. 도구를 직접 설정할 일은 거의 없어진다.

## 5. 모델 백엔드 교체

OMO를 쓰는 가장 큰 이유가 백엔드 교체다. 같은 작업을 로컬과 원격에서 바꿔 돌릴 수 있다.

명령행에서 한 번만 바꾸려면 플래그를 준다.

```bash
# 이번 세션만 로컬 모델로
omo run aider --backend local-qwen

# 기본 백엔드(remote-claude)로 그냥 실행
omo run aider
```

기본값 자체를 바꾸려면 설정을 고치거나 환경변수를 쓴다.

```bash
# 환경변수가 omo.yaml의 default_backend를 덮어쓴다
export OMO_BACKEND=local-qwen
omo run cursor
```

작업 종류에 따라 모델을 자동으로 가르려면 라우팅 규칙을 둔다. 간단한 수정은 로컬, 복잡한 리팩토링은 원격으로 보내는 식이다.

```yaml
# omo.yaml에 추가
routing:
  rules:
    - match: { task: commit-message }   # 커밋 메시지는 가볍게
      backend: local-qwen
    - match: { task: refactor }         # 큰 리팩토링은 원격 고성능 모델
      backend: remote-claude
  fallback: local-qwen                  # 규칙에 안 걸리면 로컬
```

로컬 백엔드를 쓰려면 Ollama가 먼저 떠 있어야 한다. 모델을 미리 받아두지 않으면 첫 실행에서 수 GB를 내려받느라 멈춘 것처럼 보인다.

```bash
ollama pull qwen2.5-coder:32b
ollama list   # 받아진 모델 확인
```

## 6. Claude Code / Codex와의 차이, 마이그레이션 주의점

Claude Code나 Codex는 도구와 모델이 한 묶음이다. 설치하면 바로 쓸 수 있고 품질도 안정적이지만, 모델을 못 고르고 설정이 그 안에 갇힌다. OMO는 반대로 도구·모델을 분리하는 대신 직접 설정해야 하고, 모델 품질도 고른 백엔드를 따라간다.

| 항목 | Claude Code / Codex | OMO |
|------|---------------------|-----|
| 모델 선택 | 벤더 고정 | 백엔드 교체 자유 |
| 초기 설정 | 거의 없음 | `omo.yaml` 직접 작성 |
| 로컬 모델 | 불가 | Ollama 등 가능 |
| 결과 일관성 | 높음 | 백엔드에 따라 편차 |
| 오프라인 | 불가 | 로컬 백엔드면 가능 |

Claude Code에서 넘어올 때 자주 막히는 지점이 몇 개 있다.

`CLAUDE.md`에 쌓아둔 프로젝트 규칙은 자동으로 안 옮겨진다. OMO는 공통 컨텍스트를 `omo.yaml`의 `context` 항목이나 별도 규칙 파일로 받는다. 기존 `CLAUDE.md` 내용을 그쪽으로 옮겨야 도구가 같은 맥락을 본다.

```yaml
# omo.yaml
context:
  files:
    - CLAUDE.md        # 기존 규칙 파일을 그대로 컨텍스트로 재사용
    - docs/arch.md
```

Claude Code의 슬래시 커맨드나 서브에이전트 같은 기능은 1:1 대응이 없다. OMO는 라우팅과 도구 조합으로 비슷하게 흉내 낼 뿐, 같은 사용 경험을 기대하면 안 된다. 마이그레이션을 한 번에 다 하려 하지 말고, 커밋 메시지 생성처럼 단순한 작업부터 OMO로 옮기고 결과를 보면서 범위를 넓히는 편이 안전하다.

## 7. 실무 도입 시 겪는 문제와 해결

### 7.1 설정 충돌

`omo sync`가 만든 `.aider.conf.yml`을 손으로 또 고치면, 다음 `sync`에서 덮어써져 수정이 날아간다. 도구 설정은 직접 건드리지 말고 `omo.yaml`만 고치는 게 원칙이다. 도구별 예외 설정이 필요하면 OMO의 오버라이드 블록을 쓴다.

```yaml
# omo.yaml — 도구별 예외는 여기서
overrides:
  aider:
    auto_commit: false      # aider만 자동 커밋 끄기
  cursor:
    max_context_files: 20
```

팀에서 쓸 때는 `omo.yaml`은 커밋하고, 도구가 생성하는 파일(`.aider.conf.yml`, `.cursor/`)은 `.gitignore`에 넣는다. 생성물을 커밋하면 사람마다 `sync` 결과가 달라 충돌이 난다.

### 7.2 토큰 비용

원격 API를 기본으로 두면 비용이 빨리 는다. 큰 코드베이스에서 컨텍스트를 통째로 보내면 호출 한 번에 수십만 토큰이 나가는 경우가 있다. 두 가지로 막는다.

```yaml
# omo.yaml
limits:
  max_context_tokens: 32000   # 컨텍스트 상한
  warn_cost_usd: 1.0          # 호출당 예상 비용이 넘으면 경고
```

가벼운 작업은 라우팅으로 로컬 모델에 넘기고, 원격은 정말 필요한 작업에만 쓴다. `omo cost`로 누적 사용량을 확인하면서 어떤 작업이 비싼지 본다.

```bash
omo cost --since 2026-06-01
```

### 7.3 모델별 결과 편차

같은 프롬프트라도 백엔드마다 결과가 다르다. 로�� 32B 모델과 원격 최신 모델은 코드 품질 차이가 크고, 로컬 모델은 긴 컨텍스트에서 앞부분을 잘 놓친다. 백엔드를 바꿨는데 결과가 갑자기 나빠졌다면 모델 차이를 먼저 의심한다.

대응은 작업과 모델을 맞추는 것이다. 리뷰·리팩토링처럼 정확도가 중요한 작업은 원격 고성능 모델로 고정하고, 보일러플레이트 생성이나 커밋 메시지처럼 실패해도 손해가 작은 작업만 로컬로 돌린다. 백엔드를 바꿀 때는 같은 입력으로 양쪽 결과를 한 번씩 비교해보고 차이를 파악한 뒤 적용한다.

```bash
# 같은 작업을 두 백엔드로 돌려 결과 비교
omo run aider --backend local-qwen --dry-run
omo run aider --backend remote-claude --dry-run
```

로컬 모델은 하드웨어도 본다. 32B급 모델을 VRAM 부족한 장비에서 돌리면 응답이 느려 체감 생산성이 떨어진다. 장비가 못 받쳐주면 더 작은 모델로 내리거나 원격으로 돌리는 게 현실적이다.

## 관련 문서

- [Claude Code 실전 팁](../Claude_Code/Claude_Code_Tips.md)
- [Aider 연동에 쓰는 로컬 모델 — Ollama](../Ollama/Ollama.md)
- [Cursor](../Cursor/Cursor.md)