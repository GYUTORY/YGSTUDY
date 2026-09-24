---
title: 프롬프트 버전 관리와 A/B 테스트
tags: [ai, llm, testing, observability]
updated: 2026-09-24
---

# 프롬프트 버전 관리와 A/B 테스트

프롬프트는 코드다. "일단 써보고 좋으면 쓴다"는 방식은 코드 리뷰도, 테스트도 없이 기능을 배포하는 것과 같다. 모델이 같아도 프롬프트 한 줄이 바뀌면 출력 분포가 통째로 달라진다. 특히 few-shot 예시 순서, system 메시지 톤, 지시 위치(앞/뒤)처럼 사소해 보이는 변경이 정확도를 10~20% 흔드는 경우가 흔하다.

그래서 프롬프트 변경을 feature flag처럼 다루게 된다. v1을 일부 트래픽에 유지하면서 v2를 나머지에 흘리고, 충분한 샘플이 쌓이면 승자를 전량 배포하는 흐름이다.

---

## 무엇을 지표로 삼을 것인가

A/B 테스트를 시작하기 전에 지표부터 정해야 한다. 지표를 안 정하면 "느낌상 v2가 낫다"는 주관 판단으로 끝난다.

**정확도 (Correctness)**

정답이 있는 태스크(분류, 추출, QA)는 직접 측정이 가능하다. 그 외의 태스크는 LLM-as-judge 방식을 많이 쓴다. GPT-4나 Claude에게 "어느 답변이 요구사항에 더 부합하는가"를 판정하게 하는 것이다. 이 방식은 인간 평가와 상관관계가 높지만, 판정 모델 자체의 편향이 들어간다는 점을 알고 써야 한다.

```python
# LLM-as-judge 예시
def judge_response(question: str, response_a: str, response_b: str) -> str:
    prompt = f"""다음 두 응답 중 어느 것이 질문에 더 정확하게 답했는가?
질문: {question}

응답 A: {response_a}

응답 B: {response_b}

'A' 또는 'B'만 출력하라."""
    result = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    return result.content[0].text.strip()
```

**지연시간 (Latency)**

p50이 아니라 p95, p99를 봐야 한다. 프롬프트 길이가 길어지면 TTFT(Time to First Token)는 거의 변하지 않지만 total duration이 늘어난다. streaming 응답이라면 사용자가 느끼는 체감은 TTFT에 가깝다.

**비용 (Cost)**

입력 토큰 × 입력 단가 + 출력 토큰 × 출력 단가. 프롬프트가 길어질수록 입력 비용이 늘고, few-shot 예시가 많을수록 더 늘어난다. Prompt Caching을 쓰는 경우 캐시 히트율도 같이 추적한다.

```python
def calculate_cost(usage, model: str = "claude-sonnet-4-6") -> float:
    # claude-sonnet-4-6 기준 (2026-09 시점)
    INPUT_PRICE = 3.0 / 1_000_000   # $3 per 1M tokens
    OUTPUT_PRICE = 15.0 / 1_000_000  # $15 per 1M tokens
    return usage.input_tokens * INPUT_PRICE + usage.output_tokens * OUTPUT_PRICE
```

---

## 샘플 크기 계산

"100개 돌려봤는데 v2가 낫더라"는 판단이 틀릴 확률이 얼마나 될까. 통계 검정 없이 결론을 내면 나중에 프로덕션에서 반대 결과가 나온다.

이진 지표(정답/오답)라면 두 비율 차이의 검정이다. 기대하는 최소 효과 크기(Minimum Detectable Effect, MDE)와 검정력(Power)을 먼저 정한다.

```python
from math import ceil, sqrt
from scipy.stats import norm

def sample_size_for_proportion_test(
    baseline: float,  # 현재 정확도 (예: 0.72)
    mde: float,       # 탐지하려는 최소 차이 (예: 0.05 = 5%p)
    alpha: float = 0.05,
    power: float = 0.80
) -> int:
    """
    각 그룹(control, treatment)에 필요한 최소 샘플 수를 반환한다.
    two-tailed test 기준.
    """
    p1 = baseline
    p2 = baseline + mde
    p_avg = (p1 + p2) / 2

    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)

    n = (z_alpha * sqrt(2 * p_avg * (1 - p_avg)) + z_beta * sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    n /= (p1 - p2) ** 2

    return ceil(n)

# 현재 정확도 72%, 5%p 개선을 탐지하려면
n = sample_size_for_proportion_test(baseline=0.72, mde=0.05)
print(f"각 그룹당 {n}개 필요")  # → 약 1,180개
```

연속 지표(지연시간)라면 t-test나 Mann-Whitney를 쓴다. 지연시간은 분포가 치우쳐있어서 Mann-Whitney가 더 robust하다.

샘플 크기 계산을 건너뛰면 두 가지 실수가 생긴다. 너무 일찍 중단해서 우연한 차이를 실제 차이로 오해하거나, 반대로 이미 충분한 데이터가 있는데도 계속 실험을 돌려 비용만 낭비하게 된다.

---

## Promptfoo로 오프라인 벤치마크

온라인 A/B 테스트(프로덕션 트래픽 분할) 전에 오프라인 평가를 먼저 돌리는 게 맞다. 프로덕션에 뭔가 나가기 전에 기준 테스트셋으로 두 버전을 비교하는 것이다.

[Promptfoo](https://promptfoo.dev)는 이걸 yaml로 선언적으로 정의할 수 있다.

```yaml
# promptfooconfig.yaml
description: "프롬프트 v1 vs v2 비교"

prompts:
  - id: v1
    raw: |
      당신은 고객 지원 담당자다.
      다음 문의에 한국어로 간결하게 답하라.
      문의: {{query}}

  - id: v2
    raw: |
      당신은 5년 경력의 고객 지원 담당자다.
      아래 문의를 읽고 공감부터 표현한 뒤, 해결 방법을 3문장 이내로 설명하라.
      문의: {{query}}

providers:
  - id: anthropic:messages:claude-sonnet-4-6
    config:
      max_tokens: 512

tests:
  - vars:
      query: "결제가 계속 실패합니다"
    assert:
      - type: llm-rubric
        value: "공감 표현이 포함되어 있고, 구체적인 해결 방법을 제시했는가"
      - type: latency
        threshold: 3000  # 3초 이내

  - vars:
      query: "환불 신청은 어떻게 하나요"
    assert:
      - type: contains
        value: "환불"
      - type: cost
        threshold: 0.01  # $0.01 이내
```

```bash
npx promptfoo eval
npx promptfoo view  # 브라우저에서 결과 확인
```

결과 화면에서 각 프롬프트별 pass rate, 평균 비용, 평균 지연시간을 한눈에 볼 수 있다. "v2가 pass rate는 높은데 비용이 1.4배다"처럼 트레이드오프를 수치로 보고 결정을 내린다.

---

## LangSmith로 프로덕션 추적

오프라인 평가가 통과하면 프로덕션에 배포한다. 이때 각 호출을 LangSmith에 추적하면서 프롬프트 버전별 성능을 실시간으로 비교한다.

```python
import anthropic
from langsmith import Client
from langsmith.wrappers import wrap_anthropic
import os

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "ls__..."

# Anthropic 클라이언트를 LangSmith wrapper로 감싼다
client = wrap_anthropic(anthropic.Anthropic())

PROMPTS = {
    "v1": "당신은 고객 지원 담당자다.\n문의: {query}",
    "v2": "당신은 5년 경력의 고객 지원 담당자다.\n공감 후 해결 방법을 제시하라.\n문의: {query}",
}

def get_prompt_version(user_id: str) -> str:
    """
    user_id의 해시값으로 트래픽을 분할한다.
    50% v1, 50% v2.
    """
    return "v2" if hash(user_id) % 2 == 0 else "v1"

def handle_query(user_id: str, query: str) -> str:
    version = get_prompt_version(user_id)
    prompt = PROMPTS[version].format(query=query)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
        # LangSmith 메타데이터 — 대시보드에서 필터링 가능
        extra_headers={
            "X-Prompt-Version": version,
        }
    )

    # LangSmith SDK로 실행 결과에 메타데이터 추가
    ls_client = Client()
    # run_id는 LangSmith가 자동 생성하며 wrap_anthropic이 연결함
    
    return response.content[0].text
```

LangSmith 대시보드에서 `X-Prompt-Version` 태그로 필터링하면 버전별 지연시간, 토큰 사용량, 에러율을 분리해서 볼 수 있다. 충분한 호출이 쌓이면 두 버전의 분포를 비교 탭에서 바로 볼 수 있다.

---

## 롤백 기준

실험 중단 기준을 미리 정해두지 않으면 "조금만 더 지켜보자"가 반복된다.

**즉시 롤백** 조건은 명확하다.

- 에러율(5xx, timeout)이 baseline 대비 2배 이상
- p99 지연시간이 SLO 초과
- 비용이 예산 한도 초과

**실험 종료 후 v1 유지** 조건도 미리 정한다.

- 통계적 유의미한 차이 없음 (p-value > 0.05)
- 정확도 차이가 MDE 미만

자동 롤백 로직을 넣으려면 메트릭을 모니터링하다가 임계값 초과 시 feature flag를 뒤집는 방식으로 구현한다.

```python
class PromptABController:
    def __init__(self):
        self.error_counts = {"v1": 0, "v2": 0}
        self.call_counts = {"v1": 0, "v2": 0}
        self.rollback_active = False

    def record_call(self, version: str, success: bool):
        self.call_counts[version] += 1
        if not success:
            self.error_counts[version] += 1
        self._check_rollback()

    def _check_rollback(self):
        v2_calls = self.call_counts["v2"]
        if v2_calls < 50:  # 50개 미만은 판단하지 않는다
            return

        v1_error_rate = self.error_counts["v1"] / max(self.call_counts["v1"], 1)
        v2_error_rate = self.error_counts["v2"] / v2_calls

        if v2_error_rate > v1_error_rate * 2:
            self.rollback_active = True
            # 알림 전송, feature flag 변경 등

    def get_version(self, user_id: str) -> str:
        if self.rollback_active:
            return "v1"
        return "v2" if hash(user_id) % 2 == 0 else "v1"
```

---

## 실험 기록 관리

실험 결과를 어디에 기록하느냐가 의외로 중요하다. "지난번에 왜 v2로 바꿨지?"를 6개월 뒤에 다시 파야 하는 경우가 생긴다.

최소한 이 정보는 남긴다.

```markdown
## 실험: system-prompt-tone-v2
- 기간: 2026-09-01 ~ 2026-09-08
- 트래픽: 50/50
- 샘플: 각 1,240건
- 결과:
  - 정확도: v1 72.3% vs v2 78.1% (p=0.003)
  - p95 지연시간: v1 2.1s vs v2 2.4s
  - 비용/1K호출: v1 $0.82 vs v2 $1.05
- 결정: v2 전량 배포 (정확도 개선이 비용 증가를 정당화)
- 담당: @gyutory
```

Promptfoo는 `promptfoo eval --output results.json`으로 결과를 저장하고 git에 커밋할 수 있다. 프롬프트 파일 자체도 git으로 버전 관리하면 언제든 이전 버전으로 돌아갈 수 있다.

---

## 주의할 것

**트래픽 분할은 user_id 기준으로 한다.** 요청 단위로 무작위 분할하면 같은 사용자가 v1과 v2를 번갈아 받아서 경험이 일관성 없게 된다. 이 문제를 "leakage"라고 부른다.

**novelty effect에 주의한다.** v2로 바뀐 직후 잠깐 지표가 올라가는 경우가 있다. 새 프롬프트가 실제로 나은 게 아니라 단순히 달라서 생기는 반응이다. 최소 3~5일은 지켜본다.

**여러 변수를 동시에 바꾸지 않는다.** "system 메시지 + few-shot 예시 + temperature"를 한꺼번에 바꾸면 어느 변경이 효과를 낸 건지 알 수 없다. 변수 하나씩 실험한다.

**지표가 서로 반대로 움직이는 경우가 있다.** 정확도는 올라가는데 지연시간도 늘어난다. 이건 실험이 알려주는 게 아니라 팀이 결정해야 할 트레이드오프다.
