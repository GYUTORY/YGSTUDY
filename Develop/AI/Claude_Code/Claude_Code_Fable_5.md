---
title: Claude Fable 5
tags: [ai, claude, anthropic, llm, fable-5, claude-5]
updated: 2026-08-07
volatility: high
---

# Claude Fable 5

## 1. 개요

Claude Fable 5(`claude-fable-5`)는 Anthropic의 일반 공개 모델 중 가장 뛰어난 등급이다. 2026-06-09에 Claude API, Amazon Bedrock, Claude Platform on AWS, Google Cloud, Microsoft Foundry에 GA됐다. Opus 5, Sonnet 5와 함께 Claude 5 계열을 이룬다.

포지션은 장기 실행 에이전트 작업이다. 깊은 추론이 필요한 작업, 복잡한 분석, 대용량 문서 처리에 쓴다. 빠른 응답이나 대량 처리가 목적이라면 Sonnet 5나 Haiku 4.5가 낫다.

---

## 2. 스펙

| 항목 | 값 |
|------|-----|
| API 모델 ID | `claude-fable-5` |
| AWS Bedrock ID | `anthropic.claude-fable-5` |
| Google Cloud ID | `claude-fable-5` |
| 컨텍스트 윈도우 | 1M 토큰 |
| 최대 출력 | 128K 토큰 (동기 Messages API 기준) |
| 입력 단가 | $10 / MTok |
| 출력 단가 | $50 / MTok |
| Adaptive thinking | 지원 (항상 켜짐) |
| 상대 지연 | 느림 |
| 지식 컷오프 | 2026-01 |

### 최대 출력 단서

128K는 동기 Messages API 기준이다. Batch API의 `output-300k-2026-03-24` 베타 헤더로 최대 300K 출력이 가능한 모델 목록에 **Fable 5는 포함되지 않는다.**

### 모델 ID는 핀 고정 스냅샷

`claude-fable-5`는 "항상 최신을 가리키는 포인터"가 아니라 해당 릴리스에 고정된 스냅샷이다. Claude 4.6 이전 세대의 날짜 suffix 없는 에일리어스와 다르다.

---

## 3. 가격

### 표준 · 캐시 · 배치

| 구분 | 단가 (/ MTok) |
|------|---------------|
| 기본 입력 | $10 |
| 5분 캐시 write | $12.50 |
| 1시간 캐시 write | $20 |
| 캐시 read | $1 |
| 출력 | $50 |
| Batch API 입력 | $5 |
| Batch API 출력 | $25 |

배수 규칙: 5분 캐시 write = 기본 × 1.25 / 1시간 캐시 write = 기본 × 2 / 캐시 read = 기본 × 0.1 / Batch = 50% 할인.

---

## 4. API 특성 — Fable 5만의 동작

### 4.1 Adaptive Thinking (항상 켜짐)

Fable 5는 thinking이 항상 켜져 있다. `thinking` 파라미터를 생략하거나 `{"type": "adaptive"}`만 허용된다. `{"type": "disabled"}`와 `{"type": "enabled", "budget_tokens": N}` 둘 다 **400 오류**다.

```python
# 올바른 사용 (생략 or adaptive)
response = client.messages.create(
    model="claude-fable-5",
    max_tokens=4096,
    messages=[{"role": "user", "content": "..."}]
)

# thinking 깊이 조절은 output_config.effort (low ~ max)
response = client.messages.create(
    model="claude-fable-5",
    max_tokens=8192,
    thinking={"type": "adaptive"},
    output_config={"effort": "max"},
    messages=[{"role": "user", "content": "..."}]
)

# 오류 → 400
# thinking={"type": "disabled"}
# thinking={"type": "enabled", "budget_tokens": 10000}
```

### 4.2 원시 사고 과정 미반환

thinking 블록은 요약 형태로만 반환된다. `display: "summarized"`로 요약을 볼 수 있고, 기본값(`display: "omitted"`)에서는 thinking 필드가 빈 문자열이다. raw thinking text는 반환되지 않는다.

이전 세대 Extended Thinking에서 `block.thinking`으로 추론 과정 전문을 읽던 코드는 Fable 5에서 동작하지 않는다.

### 4.3 Assistant Prefill 미지원

`messages` 배열 마지막 항목을 `role: "assistant"`로 끝내는 prefill이 안 된다. 구조화 출력이 필요하면 `output_config.format`이나 시스템 프롬프트로 대체한다.

### 4.4 30일 데이터 보존 필수

ZDR(Zero Data Retention) 조직에서 Fable 5를 호출하면 **모든 요청이 400 `invalid_request_error`**다. ZDR 정책을 적용 중인 환경에서는 사용 불가.

### 4.5 stop_reason: "refusal"

안전 분류기가 요청을 거절할 때 HTTP 에러가 아닌 **200 응답**에 `stop_reason: "refusal"`로 온다. `content[0].text`를 분기 없이 읽는 코드는 예외가 발생하거나 빈 응답을 반환할 수 있다.

```python
response = client.messages.create(
    model="claude-fable-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "..."}]
)

if response.stop_reason == "refusal":
    handle_refusal()
elif response.stop_reason == "end_turn":
    text = response.content[0].text
```

---

## 5. 토크나이저

Fable 5는 Opus 4.8과 같은 토크나이저를 쓴다. Opus 4.7에서 새 토크나이저가 도입됐고, 같은 텍스트가 4.6 세대보다 **약 30% 더 많은 토큰**이 된다.

| 세대 | 1M 토큰의 실제 글자 수 |
|------|----------------------|
| Fable 5 / Opus 5 / Sonnet 5 | ~55.5만 단어 / 유니코드 250만 자 |
| Opus 4.6 / Sonnet 4.6 세대 | ~75만 단어 / 유니코드 340만 자 |

4.6 세대 기준으로 비용을 추정하면 실제보다 30% 낮게 나온다.

---

## 6. Claude 5 계열 비교

| 항목 | Fable 5 | Opus 5 | Sonnet 5 | Haiku 4.5 |
|------|---------|--------|----------|-----------|
| 포지션 | 에이전트 / 최고 지능 | 복잡한 코딩·엔터프라이즈 | 속도·지능 균형 | 경량·고속 |
| 컨텍스트 | 1M | 1M | 1M | 200K |
| 입력 단가 | $10 | $5 | $3 | $1 |
| 출력 단가 | $50 | $25 | $15 | $5 |
| Adaptive thinking | 항상 켜짐 | 지원 | 지원 | — |
| 상대 지연 | 느림 | 보통 | 빠름 | 매우 빠름 |

Sonnet 5는 2026-08-31까지 인트로 가격($2 입력 / $10 출력)이 적용된다. 9월 1일부터 $3 / $15.

---

## 7. Fast Mode 호환성

`speed: "fast"` 파라미터는 **Opus 5 / Opus 4.8 전용**이다. Fable 5에서 요청하면 에러가 난다. first-party Claude API에서만 동작하며 Bedrock / Google Cloud / Microsoft Foundry는 미지원이고 Batch API와도 병용 불가다.

---

[^mythos]: **Claude Mythos 5** (`claude-mythos-5`)는 Fable 5와 스펙·가격이 동일하나 Project Glasswing 초대 전용이며 방어적 사이버보안 워크플로 대상 모델이다. 셀프서브 가입 경로 없음.
