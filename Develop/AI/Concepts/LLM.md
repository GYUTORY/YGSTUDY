---
title: LLM 동작 원리와 프로덕션 통합
tags: [ai, llm, transformer, inference, backend]
updated: 2026-03-29
---

# LLM 동작 원리와 프로덕션 통합

## 1. Transformer 아키텍처

현재 LLM은 거의 다 Transformer 기반이다. 2017년 구글의 "Attention Is All You Need" 논문에서 시작했고, GPT·Claude·Gemini 모두 이 구조를 사용한다.

### 1.1 핵심 구조

Transformer는 **인코더-디코더** 구조지만, 현재 대부분의 LLM은 **디코더 전용(Decoder-only)** 구조를 사용한다.

```
입력 토큰 → Embedding → [Decoder Block × N] → Linear → Softmax → 다음 토큰 확률
                              │
                    ┌─────────┴─────────┐
                    │  Masked Self-Attention  │
                    │  Feed-Forward Network   │
                    │  Layer Normalization    │
                    └───────────────────┘
```

디코더 블록이 수십~수백 개 쌓여 있다. GPT-4 급 모델은 100개 이상의 레이어를 가진 것으로 알려져 있다.

### 1.2 Self-Attention 메커니즘

Self-Attention은 입력 시퀀스의 각 토큰이 다른 모든 토큰과의 관련도를 계산하는 방식이다.

```
Query(Q), Key(K), Value(V) 세 벡터를 계산:

Attention(Q, K, V) = softmax(QK^T / √d_k) × V
```

- **Q(Query)**: "이 토큰이 무엇을 찾는가"
- **K(Key)**: "이 토큰이 무엇을 제공하는가"
- **V(Value)**: "실제 전달할 정보"
- **√d_k**: 스케일링 팩터. 이걸 안 나누면 softmax가 극단적인 값으로 수렴해서 학습이 안 된다.

```
"서버가 요청을 처리한다"라는 문장에서:

"처리한다"의 Attention 가중치:
  서버가  → 0.35  (주어, 높은 관련도)
  요청을  → 0.45  (목적어, 가장 높은 관련도)
  처리한다 → 0.20  (자기 자신)
```

**Multi-Head Attention**은 이 과정을 여러 번 병렬로 수행한다. 각 head가 다른 관점에서 관계를 포착한다. 한 head는 문법적 관계를, 다른 head는 의미적 관계를 학습하는 식이다.

### 1.3 컨텍스트 윈도우와 KV Cache

Attention 연산은 시퀀스 길이의 제곱에 비례하는 연산량이 든다. 토큰이 1000개면 1,000,000번의 유사도 계산이 필요하다. 이게 컨텍스트 윈도우에 제한이 있는 근본적인 이유다.

**KV Cache**: LLM이 토큰을 하나씩 생성할 때, 이전 토큰들의 Key/Value를 매번 다시 계산하면 낭비다. 그래서 이전 토큰의 K, V 값을 메모리에 캐싱해두고 재사용한다. 프로덕션에서 GPU 메모리를 많이 차지하는 주범이 바로 이 KV Cache다.

---

## 2. 토크나이저

LLM은 텍스트를 직접 이해하지 못한다. 텍스트를 **토큰**(정수 ID)으로 변환해야 하고, 이 변환을 토크나이저가 담당한다.

### 2.1 BPE (Byte Pair Encoding)

GPT 계열이 사용하는 방식이다. OpenAI의 `tiktoken` 라이브러리로 직접 확인할 수 있다.

```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4")
tokens = enc.encode("서버가 요청을 처리한다")
print(tokens)       # [12345, 67890, ...]  정수 배열
print(len(tokens))  # 토큰 수 = 비용 산정 기준
```

BPE의 동작 방식:
1. 모든 텍스트를 바이트 단위로 쪼갠다
2. 가장 자주 등장하는 바이트 쌍을 하나의 토큰으로 합친다
3. 이 과정을 반복해서 어휘 사전을 만든다

영어는 한 단어가 1~2토큰이지만, 한국어는 3~5토큰이 되는 경우가 많다. API 비용을 계산할 때 이 차이를 반드시 고려해야 한다.

### 2.2 SentencePiece

구글 계열(Gemini, T5) 모델이 주로 사용한다. BPE와의 차이:

| 항목 | BPE (tiktoken) | SentencePiece |
|------|----------------|---------------|
| 입력 단위 | UTF-8 바이트 | 유니코드 문자 |
| 공백 처리 | 별도 토큰 | `▁`로 표시 |
| 한국어 효율 | 상대적으로 낮음 | 상대적으로 높음 |
| 대표 모델 | GPT-4, Claude | Gemini, Llama |

### 2.3 실무에서 토크나이저가 중요한 이유

- **비용**: API 과금 단위가 토큰이다. 같은 한국어 텍스트도 모델에 따라 토큰 수가 2배 이상 차이 난다.
- **컨텍스트 제한**: 128K 컨텍스트라고 해도, 한국어는 영어 대비 같은 글자 수에 더 많은 토큰을 소비한다.
- **프롬프트 설계**: 시스템 프롬프트가 너무 길면 실제 대화에 쓸 수 있는 토큰이 줄어든다.

```python
# 토큰 수 미리 계산해서 컨텍스트 초과를 방지하는 패턴
def trim_to_token_limit(text: str, max_tokens: int, model: str = "gpt-4") -> str:
    enc = tiktoken.encoding_for_model(model)
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])
```

---

## 3. 추론 파라미터

API 호출 시 설정하는 파라미터들이 출력 품질에 직접 영향을 준다. 대충 기본값으로 두면 원하는 결과가 안 나오는 경우가 많다.

### 3.1 Temperature

0.0~2.0 사이 값. 다음 토큰을 선택할 때의 확률 분포를 조절한다.

```
Temperature = 0.0 → 항상 확률이 가장 높은 토큰 선택 (결정적)
Temperature = 1.0 → 원래 확률 분포 그대로 샘플링
Temperature = 2.0 → 확률 분포를 평탄하게 만들어서 다양한 토큰이 선택됨
```

실무 기준:
- **코드 생성, 데이터 추출, 분류**: `0.0~0.3` — 일관된 결과가 필요하다
- **일반 대화, 요약**: `0.5~0.7` — 적당한 다양성
- **창작, 브레인스토밍**: `0.8~1.2` — 다양한 응답

### 3.2 Top-p (Nucleus Sampling)

확률 상위 p%에 해당하는 토큰들 중에서만 샘플링한다.

```
Top-p = 0.1 → 확률 상위 10%에 해당하는 토큰들만 후보
Top-p = 0.9 → 확률 상위 90%까지 후보 (대부분의 토큰 포함)
Top-p = 1.0 → 모든 토큰이 후보 (필터링 없음)
```

Temperature와 Top-p를 동시에 낮추면 출력이 너무 제한적이 되고, 둘 다 높이면 횡설수설하는 결과가 나온다. 보통 하나만 조절하고 다른 하나는 기본값으로 두는 게 낫다.

### 3.3 Max Tokens / Stop Sequences

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "서버 상태를 JSON으로 알려줘"}],
    temperature=0.0,
    max_tokens=500,          # 응답 최대 길이 제한
    stop=["\n\n", "---"],    # 이 문자열을 만나면 생성 중단
)
```

`max_tokens`를 설정하지 않으면 모델이 토큰 제한까지 계속 생성하면서 비용이 불필요하게 올라간다. 용도에 맞게 항상 설정해야 한다.

### 3.4 Frequency Penalty / Presence Penalty

같은 단어가 반복되는 문제를 제어한다.

- **Frequency Penalty**: 이미 등장한 토큰의 등장 횟수에 비례해서 확률을 낮춘다. 반복이 심한 출력에 적용한다.
- **Presence Penalty**: 이미 등장한 토큰이면 횟수와 무관하게 확률을 낮춘다. 다양한 주제를 언급하게 하고 싶을 때 쓴다.

---

## 4. Function Calling / Tool Use

LLM이 외부 함수를 호출할 수 있게 하는 패턴이다. LLM 자체가 함수를 실행하는 게 아니라, "이 함수를 이 인자로 호출하라"는 JSON을 생성하는 것이다. 실제 실행은 백엔드가 담당한다.

### 4.1 동작 흐름

```
사용자: "서울 날씨 알려줘"
    ↓
LLM: { "function": "get_weather", "arguments": { "city": "Seoul" } }  ← 함수 호출 결정
    ↓
백엔드: get_weather("Seoul") 실행 → { "temp": 15, "condition": "맑음" }
    ↓
LLM: "서울은 현재 15도이고 맑습니다."  ← 결과를 자연어로 변환
```

### 4.2 OpenAI 스타일 구현

```python
import openai
import json

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "주문 ID로 현재 배송 상태를 조회한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "주문번호 (예: ORD-12345)"
                    }
                },
                "required": ["order_id"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "ORD-12345 배송 어디까지 왔어?"}],
    tools=tools,
    tool_choice="auto",  # 모델이 알아서 호출 여부 판단
)

# 모델이 함수 호출을 결정한 경우
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)

    # 실제 함수 실행
    result = get_order_status(args["order_id"])

    # 결과를 다시 모델에 전달
    messages.append(response.choices[0].message)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result)
    })

    # 최종 응답 생성
    final_response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=tools,
    )
```

### 4.3 Anthropic(Claude) 스타일 구현

```python
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_order_status",
        "description": "주문 ID로 현재 배송 상태를 조회한다",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "주문번호 (예: ORD-12345)"
                }
            },
            "required": ["order_id"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4-6-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "ORD-12345 배송 어디까지 왔어?"}]
)

# stop_reason이 "tool_use"인 경우 함수 호출 처리
for block in response.content:
    if block.type == "tool_use":
        result = get_order_status(block.input["order_id"])

        # tool_result로 응답
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result)
            }]
        })
```

### 4.4 주의사항

- **함수 설명(description)이 품질을 결정한다.** 모델은 description을 보고 어떤 함수를 호출할지 판단한다. 모호하게 쓰면 잘못된 함수를 호출하거나 아예 호출하지 않는다.
- **파라미터 검증은 반드시 백엔드에서 해야 한다.** 모델이 생성한 JSON의 인자값을 그대로 신뢰하면 안 된다. SQL Injection이나 경로 조작 같은 공격이 가능하다.
- **tool_choice="auto"**를 쓰면 모델이 판단하고, `"required"`로 설정하면 반드시 함수를 호출한다. 특정 작업 흐름에서는 `"required"`가 더 안정적이다.
- **병렬 호출**: 모델이 여러 함수를 한 번에 호출하는 경우가 있다. `tool_calls` 배열에 여러 항목이 들어오므로, 순차 처리가 아닌 병렬 처리를 해야 응답이 빨라진다.

---

## 5. Structured Output (JSON Mode)

LLM 응답을 JSON 등 정해진 형식으로 받아야 하는 경우가 많다. 프롬프트에 "JSON으로 답해줘"라고 쓰는 것만으로는 형식이 보장되지 않는다.

### 5.1 JSON Mode

```python
# OpenAI JSON Mode
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "응답을 JSON 형식으로 출력한다."},
        {"role": "user", "content": "서버 상태를 알려줘"}
    ],
    response_format={"type": "json_object"}
)

result = json.loads(response.choices[0].message.content)
```

JSON Mode는 출력이 유효한 JSON이라는 것만 보장한다. 특정 스키마를 따르는지는 보장하지 않는다.

### 5.2 Structured Outputs (스키마 강제)

OpenAI의 Structured Outputs는 JSON Schema를 지정하면 모델이 그 스키마를 정확히 따르게 한다.

```python
from pydantic import BaseModel

class ServerStatus(BaseModel):
    hostname: str
    cpu_usage: float
    memory_usage: float
    status: str  # "healthy" | "warning" | "critical"

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "서버 상태를 분석해줘: CPU 78%, 메모리 92%"}],
    response_format=ServerStatus,
)

status = response.choices[0].message.parsed  # ServerStatus 객체
print(status.cpu_usage)   # 78.0
print(status.status)      # "warning"
```

### 5.3 파싱 실패 처리

Structured Output을 쓰더라도 파싱이 실패하는 경우가 있다. `max_tokens`에 도달해서 JSON이 잘리거나, 모델이 거부(refusal)하는 경우다.

```python
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=messages,
    response_format=ServerStatus,
)

message = response.choices[0].message

if message.refusal:
    # 모델이 응답을 거부한 경우
    log.warning(f"모델 거부: {message.refusal}")
    return fallback_response()

if message.parsed is None:
    # max_tokens 도달 등으로 파싱 실패
    log.error("JSON 파싱 실패, 원본 텍스트 확인 필요")
    return fallback_response()

return message.parsed
```

---

## 6. 멀티 프로바이더 Fallback 패턴

프로덕션에서 단일 LLM 프로바이더에만 의존하면 장애 시 서비스 전체가 멈춘다. 여러 프로바이더를 두고 fallback 하는 구조가 필요하다.

### 6.1 기본 Fallback 구조

```python
from dataclasses import dataclass
from typing import Optional
import time
import logging

log = logging.getLogger(__name__)

@dataclass
class LLMProvider:
    name: str
    client: object
    model: str
    timeout: float = 30.0
    is_healthy: bool = True
    last_failure: float = 0.0
    cooldown: float = 60.0  # 실패 후 재시도까지 대기 시간

class MultiProviderLLM:
    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers

    def _is_available(self, provider: LLMProvider) -> bool:
        if provider.is_healthy:
            return True
        # cooldown 시간이 지나면 다시 시도
        return time.time() - provider.last_failure > provider.cooldown

    def chat(self, messages: list[dict], **kwargs) -> Optional[str]:
        errors = []

        for provider in self.providers:
            if not self._is_available(provider):
                continue

            try:
                response = provider.client.chat.completions.create(
                    model=provider.model,
                    messages=messages,
                    timeout=provider.timeout,
                    **kwargs,
                )
                provider.is_healthy = True
                return response.choices[0].message.content

            except Exception as e:
                provider.is_healthy = False
                provider.last_failure = time.time()
                errors.append((provider.name, str(e)))
                log.warning(f"{provider.name} 실패: {e}, 다음 프로바이더로 전환")

        log.error(f"모든 프로바이더 실패: {errors}")
        raise RuntimeError(f"모든 LLM 프로바이더 응답 불가: {errors}")
```

### 6.2 프로바이더 간 호환 주의사항

프로바이더마다 API 형식이 미묘하게 다르다.

- **시스템 메시지**: OpenAI는 `role: "system"`, Anthropic은 `system` 파라미터로 별도 전달
- **Tool 스키마**: OpenAI는 `parameters`, Anthropic은 `input_schema`
- **응답 형식**: `choices[0].message.content` vs `content[0].text`
- **스트리밍**: 이벤트 형식과 종료 조건이 다르다

LiteLLM 같은 프록시 라이브러리를 쓰면 이런 차이를 추상화할 수 있지만, 프로바이더별 고유 기능(Structured Outputs 등)을 쓸 때는 결국 분기 처리가 필요하다.

---

## 7. 비용 모니터링과 레이턴시 관리

### 7.1 비용 구조

LLM API 비용은 입력 토큰과 출력 토큰 단위로 과금된다. 출력 토큰이 입력보다 3~5배 비싸다.

```
비용 계산 예시 (GPT-4o 기준, 2026년 초):
- 입력: $2.50 / 1M tokens
- 출력: $10.00 / 1M tokens

하루 10,000건 요청, 평균 입력 500토큰 / 출력 200토큰이면:
  입력: 10,000 × 500 = 5M tokens → $12.50
  출력: 10,000 × 200 = 2M tokens → $20.00
  일일 비용: $32.50 → 월 약 $975
```

### 7.2 비용 절감 방법

**프롬프트 캐싱**: 같은 시스템 프롬프트를 반복 전송하면 캐싱 할인이 적용된다. Anthropic의 경우 캐시 히트 시 입력 비용이 90% 감소한다.

**모델 라우팅**: 모든 요청을 비싼 모델로 보내지 않는다.

```python
def select_model(task_type: str) -> str:
    """작업 복잡도에 따라 모델을 선택한다"""
    routing = {
        "classification": "gpt-4o-mini",     # 단순 분류 → 저렴한 모델
        "extraction": "gpt-4o-mini",          # 데이터 추출 → 저렴한 모델
        "code_generation": "gpt-4o",          # 코드 생성 → 중간 모델
        "complex_reasoning": "claude-opus-4-6-20250514",  # 복잡한 추론 → 고성능 모델
    }
    return routing.get(task_type, "gpt-4o-mini")
```

**배치 API**: 실시간 응답이 필요 없는 작업(로그 분석, 데이터 라벨링 등)은 배치 API를 쓴다. OpenAI 배치 API는 50% 할인이 적용된다.

### 7.3 레이턴시 관리

LLM API 응답 시간은 출력 토큰 수에 비례한다. 첫 토큰까지의 시간(TTFT, Time To First Token)과 전체 응답 시간을 구분해서 측정해야 한다.

```python
import time

class LLMMetrics:
    def __init__(self):
        self.metrics = []

    def timed_request(self, client, **kwargs):
        start = time.monotonic()
        first_token_time = None

        # 스트리밍으로 TTFT 측정
        stream = client.chat.completions.create(**kwargs, stream=True)
        chunks = []

        for chunk in stream:
            if first_token_time is None and chunk.choices[0].delta.content:
                first_token_time = time.monotonic() - start

            if chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)

        total_time = time.monotonic() - start
        content = "".join(chunks)

        self.metrics.append({
            "ttft": first_token_time,
            "total_time": total_time,
            "output_tokens": len(content.split()),  # 대략적인 추정
            "model": kwargs.get("model"),
        })

        return content
```

**레이턴시를 줄이는 방법**:
- `max_tokens`를 용도에 맞게 제한한다
- 스트리밍을 사용해서 사용자에게 점진적으로 응답을 보여준다
- 간단한 작업에는 작은 모델을 쓴다 (모델 라우팅)
- 프롬프트 길이를 줄인다 — 긴 시스템 프롬프트는 TTFT를 느리게 한다

---

## 8. 로컬 LLM 셀프호스팅

외부 API로 데이터를 보낼 수 없는 환경(금융, 의료, 군사 등)이거나, API 비용을 줄이고 싶은 경우 로컬에서 LLM을 직접 운영한다.

### 8.1 Ollama

개발 환경이나 소규모 서비스에서 가장 접근하기 쉬운 방법이다.

```bash
# 설치 후 모델 다운로드
ollama pull llama3.1:8b

# 서버 실행 (기본 포트 11434)
ollama serve

# API 호출 (OpenAI 호환)
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Ollama는 OpenAI 호환 API를 제공하므로, 기존 OpenAI SDK 코드에서 `base_url`만 바꾸면 된다.

```python
from openai import OpenAI

# Ollama 로컬 서버에 연결
client = OpenAI(base_url="http://localhost:11434/v1", api_key="unused")

response = client.chat.completions.create(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": "서버 로그 분석해줘"}],
)
```

### 8.2 vLLM

프로덕션 수준의 처리량이 필요하면 vLLM을 쓴다. 핵심 기능은 **PagedAttention**으로, KV Cache를 페이징 방식으로 관리해서 GPU 메모리를 훨씬 효율적으로 쓴다.

```bash
# vLLM 서버 실행
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 2  # GPU 2장 병렬
```

Ollama vs vLLM 선택 기준:

| 항목 | Ollama | vLLM |
|------|--------|------|
| 용도 | 개발, 테스트, 소규모 서비스 | 프로덕션, 대규모 트래픽 |
| 설정 난이도 | 쉬움 (설치 후 바로 사용) | 중간 (Python 환경, GPU 설정 필요) |
| 동시 요청 처리 | 제한적 | Continuous Batching으로 높은 처리량 |
| GPU 메모리 효율 | 보통 | PagedAttention으로 높음 |
| 모델 관리 | 내장 (ollama pull) | HuggingFace에서 직접 다운로드 |

### 8.3 셀프호스팅 시 고려사항

**GPU 메모리 계산**: 모델 파라미터 수 × 2바이트(FP16 기준)가 최소 필요 메모리다. 8B 모델이면 약 16GB, 70B 모델이면 약 140GB가 필요하다. 여기에 KV Cache와 오버헤드를 더하면 실제로는 20~30% 더 필요하다.

```
모델 크기별 필요 GPU:
  7~8B   → GPU 1장 (24GB, RTX 4090 또는 A10G)
  13~14B → GPU 1장 (40GB, A100 40GB)
  70B    → GPU 2~4장 (A100 80GB × 2)
  405B   → GPU 8장 이상 (H100 × 8)
```

**양자화(Quantization)**: 모델 가중치를 FP16에서 INT8이나 INT4로 줄이면 메모리 사용량이 반~1/4로 줄어든다. 품질 저하가 있지만, 8B 모델의 INT4 양자화는 실용적인 수준이다. GGUF 포맷(llama.cpp)이나 AWQ, GPTQ 포맷을 많이 사용한다.

**네트워크 구성**: 로컬 LLM은 내부 네트워크에서만 접근하게 한다. 외부에 노출하면 무제한 추론 요청이 들어올 수 있고, GPU 리소스를 전부 소진당할 수 있다. Rate limiting과 인증은 반드시 적용해야 한다.
