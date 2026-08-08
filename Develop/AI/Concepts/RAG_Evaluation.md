---
title: RAG 품질 평가 - RAGAS와 TruLens 실무
tags: [rag, llm, ai]
updated: 2026-08-04
volatility: high
---

# RAG 품질 평가

RAG 파이프라인을 프로덕션에 올리고 나서 "잘 돌아가는 것 같다"로 끝내는 경우가 많다. 실제로 측정해보면 사용자 불만의 원인이 검색에 있는지 생성에 있는지조차 모르는 상태인 경우가 대부분이다.

RAGAS와 TruLens는 RAG 파이프라인의 각 단계를 분리해서 숫자로 측정한다. 지표 자체보다 "어느 단계가 문제인가"를 진단하는 도구로 써야 한다.

## 지표 구조

RAG는 크게 두 단계다. 문서를 검색하는 Retrieval과 검색 결과를 바탕으로 답변을 생성하는 Generation. 지표도 이 두 단계에 각각 대응한다.

```
질문
  └─ 검색 (Retrieval) ──→ Context (청크 N개)
                                └─ 생성 (Generation) ──→ 최종 답변
```

RAGAS와 TruLens 모두 이 흐름에서 각 구간의 품질을 쪼개서 측정한다.

## RAGAS 지표

RAGAS는 `question`, `answer`, `contexts`, `ground_truth` 네 가지 입력을 받아서 지표를 계산한다.

### Faithfulness

생성된 답변이 검색된 컨텍스트에 근거하는지를 측정한다. LLM이 자기 사전 지식에서 꺼내서 답하는지, 실제로 청크에 있는 내용을 바탕으로 답하는지 구분하는 지표다.

계산 방식은 답변을 여러 개의 주장(claim)으로 쪼갠 뒤, 각 주장이 컨텍스트에서 뒷받침되는지를 LLM으로 판단한다.

```
Faithfulness = 컨텍스트로 뒷받침되는 주장 수 / 전체 주장 수
```

0.7 미만이면 답변이 컨텍스트 없이 만들어지는 비율이 높다는 뜻이다. 할루시네이션 문제일 가능성이 높다.

### Answer Relevancy

답변이 질문에 얼마나 관련 있는지를 측정한다. Faithfulness와 다르다. Faithfulness는 "컨텍스트에 근거하는가"를 보고, Answer Relevancy는 "질문에 답하는가"를 본다.

계산 방식은 생성된 답변으로부터 역으로 질문을 N개 생성한 뒤, 원래 질문과의 코사인 유사도를 평균낸다.

```
Answer Relevancy = avg(cosine_similarity(original_q, generated_q_i))
```

답변이 장황하거나 질문을 벗어나면 낮게 나온다. "이 제품의 배송 기간은 얼마나 걸리나요?"라는 질문에 반품 정책까지 섞어서 답하면 Answer Relevancy가 낮아진다.

### Context Recall

정답(ground truth)에 등장하는 정보가 검색된 컨텍스트에 포함되어 있는지를 측정한다. Retrieval 단계의 품질을 직접 측정하는 지표다.

```
Context Recall = 컨텍스트에 있는 정답 문장 수 / 전체 정답 문장 수
```

이 값이 낮으면 검색이 문제다. 청킹 전략, 임베딩 모델, 검색 알고리즘(BM25, 벡터, 하이브리드)을 점검해야 한다.

### Context Precision

검색된 청크 중에 실제로 답변에 필요한 청크 비율을 측정한다. top-k를 높게 잡아서 노이즈 청크가 많이 들어오면 낮아진다.

```
Context Precision = 관련 청크 수 / 전체 검색된 청크 수
```

Context Recall은 높은데 Context Precision이 낮은 경우, top-k를 줄이거나 리랭킹을 적용하면 생성 품질이 올라가는 경우가 있다.

## TruLens 지표

TruLens는 LLM as a Judge 방식으로 각 단계를 평가한다. RAGAS와 유사하지만 프레임워크 구조가 다르다. TruLens는 세 가지 핵심 지표(RAG Triad)를 쓴다.

| 지표 | 측정 대상 | RAGAS 대응 |
|------|-----------|------------|
| Answer Relevance | 질문 → 답변 | Answer Relevancy |
| Context Relevance | 질문 → 컨텍스트 | Context Precision |
| Groundedness | 컨텍스트 → 답변 | Faithfulness |

TruLens는 각 평가를 LLM 호출로 처리하고, 0~1 사이 점수와 이유(reasoning)를 함께 반환한다. 실패한 케이스를 따라가서 원인을 파악할 때 이유 필드가 유용하다.

## 코드로 실행하기

### RAGAS

```python
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)

data = {
    "question": ["배송은 며칠 걸리나요?"],
    "answer": ["평균 3~5 영업일이 소요됩니다."],
    "contexts": [
        [
            "당사 배송은 일반적으로 3~5 영업일 내 도착합니다.",
            "도서산간 지역은 추가 기간이 필요합니다.",
        ]
    ],
    "ground_truth": ["3~5 영업일"],
}

dataset = Dataset.from_dict(data)
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
)

# 개별 케이스 확인
df = result.to_pandas()
print(df[["question", "faithfulness", "context_recall"]].sort_values("faithfulness"))
```

평가용 LLM을 별도로 지정하지 않으면 OpenAI GPT-4를 기본으로 쓴다. 비용이 나오는 구조다. `llm` 파라미터로 다른 모델을 지정할 수 있다.

### TruLens

```python
from trulens.apps.langchain import TruChain
from trulens.core import TruSession
from trulens.providers.openai import OpenAI as TruOpenAI
from trulens.feedback import Groundedness, AnswerRelevance, ContextRelevance

session = TruSession()
provider = TruOpenAI()

groundedness = Groundedness(groundedness_provider=provider)
answer_relevance = AnswerRelevance(provider=provider)
context_relevance = ContextRelevance(provider=provider)

tru_chain = TruChain(
    rag_chain,
    app_name="prod-rag-v2",
    feedbacks=[groundedness, answer_relevance, context_relevance],
)

with tru_chain:
    result = rag_chain.invoke({"question": "환불 정책이 어떻게 되나요?"})

# 점수 확인
session.get_leaderboard()
```

TruLens는 평가 결과를 로컬 SQLite에 저장하고 대시보드로 시각화한다. 실패 케이스를 눌러서 각 청크별 점수와 판단 이유를 볼 수 있다.

## 품질 저하 원인 진단

지표가 낮게 나왔을 때 단계별로 원인을 좁혀야 한다.

**Context Recall이 낮은 경우 — Retrieval 문제**

청크가 너무 크거나 작다. 1500토큰짜리 청크를 한 번에 검색하면 필요한 부분이 희석된다. 임베딩 모델이 도메인에 맞지 않는 경우도 있다. 법률 문서에 general-purpose 임베딩을 쓰면 전문 용어 검색이 약하다. 질문과 문서의 어휘가 다를 때도 낮아진다. 사용자가 "환불"로 물어보는데 문서는 "반품 처리"로 표기된 경우 벡터 유사도가 낮게 나온다. BM25 + 벡터 하이브리드 검색으로 보완할 수 있다.

**Faithfulness가 낮은 경우 — Generation 문제**

시스템 프롬프트에 "컨텍스트에 없는 내용은 답하지 마라"는 지시가 없거나 약한 경우가 가장 흔하다. top-k가 너무 높아서 관련 없는 청크가 섞였을 때도 낮아진다. 모델이 노이즈 청크에서 엉뚱한 정보를 끌어올 수 있다. 모델 자체의 사전 지식이 강한 도메인이라 컨텍스트를 무시하는 경향도 있다.

**Answer Relevancy가 낮은 경우 — 프롬프트 문제**

답변 포맷 지시가 없어서 장황하게 출력되는 경우다. 컨텍스트에 여러 주제가 섞여서 모델이 질문 범위를 초과해서 답하는 케이스도 있다. 질문 자체가 모호해서 모델이 여러 해석으로 답하는 경우도 마찬가지다.

## 지표만 보고 잘못된 결론 내리는 사례

지표가 높다고 파이프라인이 좋은 건 아니다. 지표의 계산 방식을 알면 허점도 보인다.

**Faithfulness 0.9인데 사용자 불만이 쌓이는 경우**

Faithfulness는 답변이 컨텍스트에 근거하는지를 본다. 컨텍스트 자체가 오래된 문서라면, 컨텍스트에 충실한 답변이 오히려 틀린 정보를 전달한다. "2023년 기준 환불 기간은 7일"이라는 청크가 검색되고 그 내용으로 답하면 Faithfulness는 1.0이지만 현재 정책(14일)과 다르다. 지표 외에 문서 신선도(최근 업데이트 날짜) 관리가 필요하다.

**Context Recall 0.85인데 실제 검색 품질이 낮은 경우**

Context Recall은 ground truth 문장이 컨텍스트에 포함되는지를 본다. ground truth 자체가 단순하거나 짧으면 낮은 k로도 Recall이 높게 나온다. "배송은 3일이다"라는 단문 ground truth는 top-3 검색으로도 쉽게 커버된다. 복잡한 조건 질문("주말에 주문하면 배송일이 어떻게 바뀌나요?")에서는 같은 파이프라인이 무너진다. 테스트셋을 단순 질문으로만 구성하면 Recall이 실제보다 과장된다.

**지표가 전부 0.8 이상인데 특정 질문 유형에서 계속 실패하는 경우**

평균 지표는 데이터셋의 분포를 반영한다. 테스트셋이 FAQ 스타일 단순 질문 중심이면 평균이 높게 나온다. 비교 질문("A 요금제와 B 요금제의 차이가 뭔가요?"), 다단계 추론 질문("작년 대비 이번 달 배송비가 올랐나요?")은 별도로 측정하지 않으면 평균에 묻힌다. 테스트셋을 질문 유형별로 층화 샘플링해야 평균이 실제 성능을 반영한다.

**TruLens Groundedness가 높은데 답변이 부정확한 경우**

Groundedness는 LLM as a Judge 방식이다. 판단 자체가 LLM 호출이라 평가 LLM의 한계를 그대로 갖는다. 판단 LLM이 모르는 도메인 용어가 포함된 답변은 근거 판단을 틀리게 할 수 있다. 의료·법률·금융 도메인에서 판단 LLM을 GPT-3.5로 쓰면 점수 신뢰도가 떨어진다. 평가 LLM도 파이프라인 LLM만큼 신경 써서 골라야 한다.

## 실무에서 측정하는 방법

매 배포마다 전체 평가를 돌리면 비용과 시간이 많이 든다. 최소한으로 운영하려면:

골든셋 100~200문항을 만들어서 PR마다 실행한다. 지표가 이전 버전 대비 5% 이상 떨어지면 배포를 막는다. Faithfulness와 Context Recall만 먼저 측정하는 것으로 시작해도 충분하다. 이 두 지표가 Retrieval과 Generation 단계를 각각 대표한다.

지표가 낮은 케이스는 개별로 들어가서 어느 청크가 문제인지 확인한다. RAGAS는 `result.to_pandas()`로 개별 케이스를 볼 수 있고, TruLens는 대시보드에서 드릴다운할 수 있다.

Faithfulness는 올리기 쉬운 편이다. 시스템 프롬프트에 제약을 강화하면 빠르게 오른다. Context Recall을 올리려면 청킹·임베딩·검색 알고리즘 전체를 손봐야 하는 경우가 많아서 시간이 더 걸린다.
