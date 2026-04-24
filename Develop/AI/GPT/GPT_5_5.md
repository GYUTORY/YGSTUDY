---
title: GPT-5.5 모델 종합 가이드
tags: [ai, openai, gpt, gpt-5-5, llm, api]
updated: 2026-04-24
---

# GPT-5.5

## 1. GPT-5.5 개요

GPT-5.5는 OpenAI가 GPT-5 후속으로 출시한 멀티모달 모델이다. 단순히 GPT-5의 성능을 끌어올린 것이 아니라 추론(reasoning) 토큰을 모델 내부에서 처리하는 방식이 달라졌고, 함수 호출 안정성과 구조화된 출력 품질이 크게 개선되었다. 라인업은 `gpt-5.5`, `gpt-5.5-mini`, `gpt-5.5-nano` 세 가지로 나뉘며, 각각 가격과 응답 지연(latency)에서 차이가 난다.

5년 동안 OpenAI 모델을 다뤄오면서 느낀 건 메이저 버전 업그레이드마다 동일한 프롬프트가 다른 결과를 낸다는 점이다. GPT-5.5도 예외가 아니어서, GPT-4o 시절에 잘 동작하던 프롬프트가 갑자기 JSON 스키마 위반을 내거나, 거꾸로 GPT-5에서 자주 깨지던 함수 호출이 안정적으로 돌기도 한다. 이 문서는 그런 실무 차이점에 집중한다.

### 1.1 모델 라인업

| 모델 | Context Window | Max Output | 입력 가격 | 출력 가격 | 비고 |
|------|----------------|------------|-----------|-----------|------|
| `gpt-5.5` | 400K | 100K | $1.25 / 1M | $10.00 / 1M | 플래그십 |
| `gpt-5.5-mini` | 400K | 100K | $0.25 / 1M | $2.00 / 1M | 가성비 |
| `gpt-5.5-nano` | 200K | 32K | $0.05 / 1M | $0.40 / 1M | 초경량 |

가격은 백만(1M) 토큰 기준이며, 캐시 히트(cached input)는 입력 가격의 약 10% 수준으로 청구된다. `gpt-5.5-mini`는 GPT-4o-mini의 후속이라기보다는 GPT-5와 GPT-5.5의 중간 포지션에 가깝다. 단순 분류, 라벨링, 임베딩 전 텍스트 정제 같은 작업은 `gpt-5.5-nano`만 써도 충분하다.

### 1.2 이전 모델 대비 변경점

GPT-4o, GPT-5에서 GPT-5.5로 넘어올 때 가장 크게 바뀐 부분을 정리하면 다음과 같다.

| 항목 | GPT-4o | GPT-5 | GPT-5.5 |
|------|--------|-------|---------|
| Context Window | 128K | 256K | 400K |
| Reasoning 모드 | 별도 (`o1`, `o3`) | 통합 (reasoning_effort) | 통합 + 동적 |
| 함수 호출 정확도 | 약 88% | 약 94% | 약 97% |
| JSON Schema 강제 | response_format | response_format | response_format + structured_outputs |
| 비전 입력 | 지원 | 지원 | 지원 (해상도 자동 조정) |
| 오디오 입력 | gpt-4o-audio | gpt-5-audio | 통합 (audio modality) |
| 프롬프트 캐싱 | 자동 | 자동 + 명시적 | 자동 + 명시적 + TTL 조정 |

가장 와닿는 변화는 reasoning 모드 통합이다. GPT-4o 시절에는 `o1`, `o3`처럼 별도 모델로 추론을 호출해야 했고, 일반 모델과 가격/응답 형식이 달라서 코드를 분기해야 했다. GPT-5.5는 `reasoning_effort` 파라미터 하나로 동일 엔드포인트에서 추론 강도를 조절한다.

---

## 2. Context Window와 토큰

### 2.1 400K 토큰의 의미

GPT-5.5의 context window는 400K 토큰이다. 한국어 기준으로 대략 60~70만 자(공백 포함) 수준이라고 보면 되고, 영어는 100~150만 자 정도 들어간다. 단순히 "많이 넣을 수 있다"가 아니라, 응답 품질이 컨텍스트 위치에 따라 달라진다는 점이 중요하다.

실무에서 200K가 넘는 컨텍스트를 넣으면 중간 부분의 정보를 놓치는 lost-in-the-middle 현상이 여전히 관찰된다. GPT-5.5는 GPT-5보다 이 현상이 줄긴 했지만 완전히 해소된 건 아니다. 긴 문서를 다룰 때는 다음 패턴을 쓴다.

- 핵심 컨텍스트는 시스템 메시지 또는 가장 마지막 user 메시지에 배치
- 참고 자료는 중간에 넣고, 마지막에 "위 참고 자료 중 X 항목을 기준으로" 같은 명시적 지시를 추가
- 200K가 넘으면 사실상 RAG로 분할 검색하는 게 정확도와 비용 모두에서 유리하다

### 2.2 토큰 카운트와 출력 한계

출력 한계는 100K 토큰까지 늘어났지만, 실제로 그만큼 받는 건 거의 없다. 한 번에 50K 이상 출력을 시키면 응답이 중간에 잘리거나, `finish_reason`이 `length`로 끝나는 경우가 많다. 긴 문서 생성은 다음과 같이 청크 단위로 나누는 편이 안정적이다.

```python
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-5.5")
tokens = encoder.encode(prompt)
print(f"입력 토큰 수: {len(tokens)}")

if len(tokens) > 380_000:
    raise ValueError("컨텍스트 한계 초과")
```

`tiktoken` 라이브러리가 GPT-5.5 인코딩을 즉시 지원하지 않을 때가 있는데, 이 경우 `o200k_base`를 강제로 지정하면 된다. 정확도는 ±2% 수준이라 비용 견적용으로는 충분하다.

---

## 3. 주요 API 파라미터

### 3.1 temperature

GPT-5.5의 temperature는 GPT-4o와 동일하게 0~2 범위지만, 체감상 같은 값이라도 출력 분산이 줄어들었다. GPT-4o의 `temperature=0.7`이 GPT-5.5의 `temperature=1.0`과 비슷한 다양성을 낸다고 보면 된다.

코드 생성, 데이터 추출처럼 결정적 출력이 필요한 작업은 `temperature=0`을 쓰지만, GPT-5.5는 `temperature=0`에서도 완전히 결정적이지 않다. 동일 프롬프트를 100번 호출하면 95번 정도는 같은 결과가 나오지만 5번은 다르다. 완전 결정성이 필요하면 `seed` 파라미터를 함께 사용해야 한다.

### 3.2 reasoning_effort

추론 강도를 조절하는 파라미터로 `minimal`, `low`, `medium`, `high` 네 단계가 있다. 기본값은 `medium`이고, 값이 올라갈수록 모델이 내부적으로 reasoning 토큰을 더 많이 생성한다. 청구는 reasoning 토큰도 출력 토큰으로 계산되기 때문에 비용에 직접 영향을 준다.

| effort | 평균 reasoning 토큰 | 응답 시간 | 사용 사례 |
|--------|---------------------|-----------|-----------|
| minimal | 0~50 | 0.5~2초 | 단순 질의응답, 분류 |
| low | 100~500 | 2~5초 | 일반 코드 생성 |
| medium | 500~2,000 | 5~15초 | 복잡한 디버깅, 설계 |
| high | 2,000~10,000 | 15~60초 | 수학 증명, 알고리즘 설계 |

실무에서는 사용자 응답이 필요한 인터랙티브 환경(채팅봇)은 `low` 이하로 고정하고, 백그라운드 작업이나 분석 파이프라인만 `medium` 이상을 쓴다. `high`로 올렸을 때 결과가 좋아지는 비율은 전체 케이스의 15% 정도라서, 비용 대비 효율이 떨어지는 경우가 많다.

### 3.3 response_format

JSON 출력을 강제할 때 쓰는 파라미터다. GPT-5.5에서는 세 가지 모드를 지원한다.

```python
# 1. text (기본)
response_format={"type": "text"}

# 2. json_object - JSON이긴 하지만 스키마는 자유
response_format={"type": "json_object"}

# 3. json_schema - 스키마 강제
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "user_profile",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age", "email"],
            "additionalProperties": False
        }
    }
}
```

`strict: True`를 켜면 모델이 스키마를 위반하는 출력을 만들지 않도록 강제된다. GPT-5에서는 strict 모드에서도 가끔 추가 필드가 들어오거나 enum 위반이 발생했는데, GPT-5.5는 99% 이상 스키마를 지킨다. 다만 `strict` 모드를 쓰면 첫 호출 시 스키마 컴파일 시간이 추가되어 100~300ms 정도 응답이 느려진다.

---

## 4. 함수 호출과 툴 사용

### 4.1 기본 함수 호출

GPT-5.5의 함수 호출은 `tools` 파라미터로 정의한다.

```python
from openai import OpenAI

client = OpenAI()

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "지정한 도시의 현재 날씨를 조회한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "도시명"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["city"]
            },
            "strict": True
        }
    }
]

response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "서울 날씨 알려줘"}],
    tools=tools,
    tool_choice="auto"
)

tool_call = response.choices[0].message.tool_calls[0]
print(tool_call.function.name)
print(tool_call.function.arguments)
```

`strict: True`를 함수 정의에 넣으면 인자 스키마를 강제할 수 있다. GPT-4o 시절에는 함수 인자에 누락 필드가 들어오거나 타입이 안 맞는 경우가 자주 있었는데, GPT-5.5에서는 거의 발생하지 않는다.

### 4.2 병렬 함수 호출

GPT-5.5는 한 번의 응답에서 여러 함수를 동시에 호출할 수 있다.

```python
response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[
        {"role": "user", "content": "서울, 부산, 제주 날씨 모두 알려줘"}
    ],
    tools=tools,
    parallel_tool_calls=True
)

for call in response.choices[0].message.tool_calls:
    print(call.function.name, call.function.arguments)
```

병렬 호출이 기본값으로 켜져 있어서 의도치 않게 여러 호출이 발생할 수 있다. 순차 처리가 필요한 경우(예: 이전 함수 결과가 다음 함수 입력이 되는 경우)에는 명시적으로 `parallel_tool_calls=False`를 지정해야 한다.

### 4.3 함수 호출 후 응답 처리

함수를 호출하고 결과를 모델에 다시 넘기는 흐름은 다음과 같다.

```python
messages = [{"role": "user", "content": "서울 날씨 알려줘"}]
response = client.chat.completions.create(
    model="gpt-5.5", messages=messages, tools=tools
)

assistant_message = response.choices[0].message
messages.append(assistant_message)

for tool_call in assistant_message.tool_calls:
    result = call_actual_function(tool_call.function.name, tool_call.function.arguments)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(result)
    })

final_response = client.chat.completions.create(
    model="gpt-5.5", messages=messages, tools=tools
)
print(final_response.choices[0].message.content)
```

`tool_call_id`를 정확히 매칭하지 않으면 400 에러가 발생한다. 비동기 처리 중 ID 순서가 꼬이는 버그를 자주 봤기 때문에, dict로 ID-결과를 매핑한 뒤 순서대로 추가하는 게 안전하다.

---

## 5. 스트리밍

### 5.1 기본 스트리밍

```python
stream = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "긴 글 써줘"}],
    stream=True,
    stream_options={"include_usage": True}
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:
        print(f"\n[토큰: {chunk.usage.total_tokens}]")
```

`stream_options={"include_usage": True}`를 켜야 마지막 청크에 사용량 정보가 들어온다. GPT-5.5에서 추가된 옵션으로, GPT-4o에서는 별도 호출이 필요했다. 이걸 안 켜면 스트리밍 응답에서는 토큰 수를 알 수 없어 비용 추적이 불가능하다.

### 5.2 스트리밍 + 함수 호출

스트리밍 중 함수 호출이 발생하는 경우, `delta.tool_calls`로 부분 인자가 청크 단위로 들어온다.

```python
tool_call_buffer = {}

for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.tool_calls:
        for tc in delta.tool_calls:
            idx = tc.index
            if idx not in tool_call_buffer:
                tool_call_buffer[idx] = {"name": "", "arguments": ""}
            if tc.function.name:
                tool_call_buffer[idx]["name"] += tc.function.name
            if tc.function.arguments:
                tool_call_buffer[idx]["arguments"] += tc.function.arguments
```

함수 인자가 JSON 문자열로 청크 단위로 쪼개져 오기 때문에, 모든 청크를 합쳐야 파싱 가능한 JSON이 된다. 중간에 파싱하려고 하면 100% 실패한다.

---

## 6. 멀티모달 입력

### 6.1 비전 입력

이미지는 base64 인코딩 또는 URL로 전달한다.

```python
import base64

with open("screenshot.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "이 화면에서 에러 메시지 찾아줘"},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_data}",
                    "detail": "high"
                }
            }
        ]
    }]
)
```

`detail` 옵션은 `low`, `high`, `auto` 세 가지다. `low`는 512x512로 다운스케일하고 약 85토큰을 쓰며, `high`는 원본 해상도를 타일 단위로 처리해 이미지당 수천 토큰이 들어간다. GPT-5.5는 `auto`가 기본인데, 이미지 내용을 보고 자동으로 detail을 결정한다. 코드 스크린샷 같은 텍스트가 많은 이미지는 알아서 high로 처리하지만, 단순 사진은 low로 떨어뜨려서 비용을 절약한다.

### 6.2 오디오 입력

GPT-5.5는 별도 모델 없이 오디오 입력을 받을 수 있다.

```python
import base64

with open("voice.mp3", "rb") as f:
    audio_data = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="gpt-5.5",
    modalities=["text"],
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "이 음성을 요약해줘"},
            {
                "type": "input_audio",
                "input_audio": {"data": audio_data, "format": "mp3"}
            }
        ]
    }]
)
```

지원 포맷은 mp3, wav, m4a, flac이다. 오디오 1초당 약 25토큰으로 계산되며, 1시간짜리 음성은 약 90,000 토큰이라 비용이 빠르게 늘어난다. 단순 STT(음성 인식)만 필요하면 `whisper-1` API가 훨씬 저렴하니 분리해 쓰는 게 낫다.

---

## 7. Node.js 코드 예제

```javascript
import OpenAI from "openai";

const client = new OpenAI();

async function chat() {
  const response = await client.chat.completions.create({
    model: "gpt-5.5",
    messages: [
      { role: "system", content: "너는 친절한 백엔드 개발자다" },
      { role: "user", content: "PostgreSQL에서 인덱스 안 타는 쿼리 디버깅 방법" }
    ],
    reasoning_effort: "medium",
    temperature: 0.3,
    max_tokens: 2000
  });

  console.log(response.choices[0].message.content);
  console.log(`사용 토큰: ${response.usage.total_tokens}`);
}

chat();
```

스트리밍 버전:

```javascript
const stream = await client.chat.completions.create({
  model: "gpt-5.5",
  messages: [{ role: "user", content: "긴 답변 부탁" }],
  stream: true,
  stream_options: { include_usage: true }
});

for await (const chunk of stream) {
  const content = chunk.choices[0]?.delta?.content;
  if (content) process.stdout.write(content);
  if (chunk.usage) console.log(`\n[총 토큰: ${chunk.usage.total_tokens}]`);
}
```

Node.js SDK는 4.x부터 GPT-5.5를 정식 지원한다. 3.x를 쓰고 있으면 `reasoning_effort` 같은 신규 파라미터가 타입 에러로 막히니 업그레이드 필수다.

---

## 8. 레이트 리밋과 타임아웃

### 8.1 레이트 리밋 구조

OpenAI는 RPM(Requests Per Minute)과 TPM(Tokens Per Minute) 두 가지로 제한한다. Tier 1(결제 $50 이상)에서 GPT-5.5의 기본값은 다음과 같다.

| 모델 | RPM | TPM | TPD |
|------|-----|-----|-----|
| gpt-5.5 | 500 | 30,000 | 90,000 |
| gpt-5.5-mini | 5,000 | 200,000 | 2,000,000 |
| gpt-5.5-nano | 5,000 | 1,000,000 | 무제한 |

Tier가 올라갈수록 한도가 커지고, Tier 5(누적 결제 $1,000 이상)에서는 GPT-5.5의 TPM이 2,000,000까지 늘어난다. 헤더의 `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens`로 잔량을 확인할 수 있다.

### 8.2 429 에러 처리

레이트 리밋을 초과하면 429 응답이 오는데, 헤더의 `retry-after`를 보고 백오프해야 한다.

```python
import time
from openai import OpenAI, RateLimitError

client = OpenAI()

def chat_with_retry(messages, max_retries=5):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-5.5", messages=messages
            )
        except RateLimitError as e:
            wait = int(e.response.headers.get("retry-after", 2 ** attempt))
            time.sleep(wait)
    raise Exception("최대 재시도 초과")
```

지수 백오프(exponential backoff)는 OpenAI SDK가 기본 제공하지만, `max_retries=2`로 짧게 잡혀 있다. 배치 작업이라면 직접 구현해서 늘리는 편이 낫다.

### 8.3 타임아웃

기본 타임아웃은 SDK 기준 600초(10분)다. `reasoning_effort=high`에서 long context를 다루면 5~10분이 걸리기도 해서, 짧은 타임아웃을 두면 자주 끊긴다.

```python
client = OpenAI(timeout=120.0)  # 전역 설정

response = client.with_options(timeout=300.0).chat.completions.create(
    model="gpt-5.5", messages=messages
)
```

스트리밍을 안 쓰고 동기 호출하면 클라이언트 쪽에서 응답을 받을 때까지 연결이 열려 있어야 한다. 로드밸런서나 API Gateway 뒤에서 호출하는 경우 60초 idle timeout에 걸려 502가 떨어지는 일이 종종 있다. 이런 환경에서는 무조건 스트리밍을 쓰거나 비동기 큐를 둬야 한다.

---

## 9. 프로덕션에서 자주 겪는 문제

### 9.1 응답 지연

GPT-5.5는 GPT-4o보다 평균 응답 속도가 빠르지만, `reasoning_effort`를 잘못 설정하면 오히려 느려진다. 사용자 대기 시간이 중요한 경우 다음 패턴을 쓴다.

- 첫 토큰까지 시간(Time to First Token)을 줄이려면 스트리밍 필수
- `reasoning_effort=minimal`이면 GPT-4o-mini와 비슷한 속도(0.5~2초)
- 첫 호출은 콜드 스타트로 200~500ms 추가 지연이 있다

엣지 리전(예: 아시아에서 미국 리전 호출)은 RTT만으로 200ms씩 더해진다. Azure OpenAI를 쓰면 한국/일본 리전 배포가 가능해 지연이 절반 이하로 줄어든다.

### 9.2 토큰 초과

400K 컨텍스트라도 출력 토큰을 합치면 의외로 빨리 한계에 닿는다. 입력 380K + 출력 100K를 시도하면 480K가 되어 422 에러가 난다.

```python
try:
    response = client.chat.completions.create(...)
except openai.BadRequestError as e:
    if "context_length_exceeded" in str(e):
        # 입력을 줄이거나 모델을 더 큰 컨텍스트로 변경
        pass
```

미리 `tiktoken`으로 입력 토큰을 계산하고 `max_tokens`을 동적으로 조정하면 422를 줄일 수 있다.

### 9.3 JSON 파싱 실패

`response_format={"type": "json_object"}`만 쓰면 스키마 검증이 없어서 키 누락이 발생한다. `json_schema` + `strict: True`로 바꾸면 거의 사라지지만, 그래도 다음 케이스에서는 깨진다.

- 스키마에 `additionalProperties: false`를 안 쓴 경우
- enum 값이 한글이거나 특수문자를 포함한 경우(가끔 이스케이프 오류)
- 깊이 5단계 이상 중첩 객체

방어 코드는 항상 둬야 한다.

```python
import json

try:
    data = json.loads(response.choices[0].message.content)
except json.JSONDecodeError:
    # finish_reason 확인
    if response.choices[0].finish_reason == "length":
        # 잘린 경우 - max_tokens 늘리기
        pass
    else:
        # 다른 이유 - 재시도
        pass
```

`finish_reason`이 `length`면 출력이 잘렸다는 뜻이라 JSON 끝의 `}`나 `]`가 빠진다. `max_tokens`를 늘리거나 출력을 분할해야 한다.

### 9.4 프롬프트 캐싱 미스

GPT-5.5는 프롬프트 캐싱이 자동으로 동작하지만, 캐시 히트 조건이 까다롭다.

- 시스템 메시지 + 초반 user 메시지가 1024 토큰 이상일 때 캐싱 대상
- 캐시 키는 메시지 prefix의 정확한 일치(공백 하나만 달라도 미스)
- 캐시 TTL은 기본 5~10분, 첫 호출 후 10분 안에 재사용해야 효과 있음

캐싱이 성공하면 `usage.prompt_tokens_details.cached_tokens`에 캐시된 토큰 수가 표시된다. 이게 0이면 캐시 미스다.

```python
print(response.usage.prompt_tokens_details.cached_tokens)
```

캐시 히트율을 높이려면 시스템 메시지와 few-shot 예제를 메시지 앞쪽에 고정 배치하고, 사용자 입력은 끝에 두는 구조가 유리하다. 시스템 프롬프트 안에 사용자 ID나 timestamp를 넣으면 캐시가 절대 히트하지 않는다.

### 9.5 결정성 문제

`temperature=0`에 `seed`까지 넣어도 OpenAI는 100% 결정성을 보장하지 않는다. 응답 헤더의 `system_fingerprint`가 같으면 같은 결과가 나온다고 명시되어 있지만, OpenAI가 백엔드 모델 버전을 업데이트하면 fingerprint가 바뀌어 결과가 달라진다.

테스트 코드에서 LLM 응답을 그대로 비교하면 무조건 깨지니까, 의미적 동등성(semantic equivalence)을 검증하는 별도 평가자(LLM-as-judge)를 두거나 정규식 기반으로 핵심 필드만 비교해야 한다.

---

## 10. Claude/Gemini 대비 선택 기준

### 10.1 모델 비교

| 항목 | GPT-5.5 | Claude Opus 4.7 | Gemini 3 Pro |
|------|---------|-----------------|--------------|
| Context | 400K | 1M (베타) / 200K | 2M |
| 입력 가격 | $1.25/1M | $15/1M | $1.25/1M |
| 출력 가격 | $10/1M | $75/1M | $5/1M |
| 함수 호출 | 매우 안정 | 안정 | 보통 |
| JSON Schema | strict 모드 | tool_use 우회 | response_schema |
| 코딩 능력 | 매우 우수 | 매우 우수 | 우수 |
| 한국어 | 우수 | 매우 우수 | 우수 |
| 응답 속도 | 빠름 | 보통 | 매우 빠름 |
| 멀티모달 | 텍스트+이미지+오디오 | 텍스트+이미지 | 전부 |

### 10.2 어떤 경우에 어떤 모델을 쓰나

**GPT-5.5가 유리한 경우**
- 함수 호출/툴 사용이 핵심인 에이전트 (가장 안정적)
- JSON Schema를 엄격하게 강제해야 하는 데이터 추출
- 음성을 단일 호출로 처리해야 하는 경우
- 토큰 비용이 중요한 대량 처리(특히 mini, nano)

**Claude를 쓰는 게 나은 경우**
- 긴 글쓰기, 한국어 자연스러움이 중요한 콘텐츠 생성
- 코드 리팩토링, 복잡한 디버깅(Claude Opus가 여전히 우위)
- 긴 컨텍스트(1M)에서 정확한 정보 추출

**Gemini를 쓰는 게 나은 경우**
- 2M 토큰 같은 초장문 컨텍스트 (전체 코드베이스 분석)
- 이미지 + 비디오 처리
- 비용을 극단적으로 낮춰야 하는 경우(Flash 모델)

### 10.3 실제 의사결정 흐름

새 프로젝트에서 모델을 선택할 때 보통 이렇게 판단한다.

1. 실시간 인터랙티브가 필요한가 → 응답 속도 우선 → GPT-5.5 nano/mini, Gemini Flash
2. 함수 호출/도구 연동이 핵심인가 → GPT-5.5
3. 긴 글쓰기, 톤 일관성이 중요한가 → Claude
4. 200K 이상 컨텍스트가 필수인가 → Claude(1M), Gemini(2M)
5. 비용이 가장 중요한가 → GPT-5.5-nano, Gemini Flash

여러 모델을 동시에 호출해서 결과를 비교하는 라우터 패턴을 쓰는 회사도 늘었다. 단일 모델에 종속되지 않으려면 추상화 계층을 처음부터 두는 게 낫다.

---

## 11. 마이그레이션 시 주의점

### 11.1 GPT-4o → GPT-5.5

`model` 파라미터만 바꾸면 일단 동작하지만, 다음을 확인해야 한다.

- 토크나이저가 달라져서 동일 텍스트의 토큰 수가 5~10% 변동
- 응답이 더 길어지는 경향이 있어 `max_tokens`를 늘려야 할 수 있음
- 함수 호출 인자 형식이 더 엄격해졌기 때문에 GPT-4o에서 통과되던 느슨한 스키마가 거부될 수 있음
- system 프롬프트에 영향을 주는 default 동작이 일부 변경(예: 마크다운 출력 빈도가 줄음)

특히 system 프롬프트에서 "JSON으로만 답해"라고 했는데도 GPT-5.5가 코드블록(\`\`\`json ... \`\`\`)으로 감싸서 보낼 때가 있다. response_format을 강제하지 않으면 파싱 코드가 깨진다.

### 11.2 GPT-5 → GPT-5.5

같은 5 계열이라 호환성이 높지만, reasoning_effort 기본값이 GPT-5의 `low`에서 GPT-5.5의 `medium`으로 바뀌었다. 명시적으로 지정하지 않으면 응답 시간과 비용이 증가할 수 있다.

```python
# GPT-5 기본 동작 유지하려면
response = client.chat.completions.create(
    model="gpt-5.5",
    messages=messages,
    reasoning_effort="low"
)
```

### 11.3 점진적 마이그레이션

전체 트래픽을 한 번에 전환하지 말고, 다음 단계로 진행한다.

1. 동일 프롬프트로 GPT-4o/GPT-5와 GPT-5.5를 병렬 호출하고 결과 비교 (섀도우 트래픽)
2. 평가 데이터셋으로 정확도/응답 시간/비용 측정
3. 10% → 50% → 100% 단계적 트래픽 전환
4. 롤백 가능하도록 모델명을 환경변수로 관리

```python
import os
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
```

A/B 테스트 도구를 쓰는 경우, 동일 사용자에게는 같은 모델을 일관되게 노출해야 한다. 사용자가 응답 품질 차이를 체감하면 혼란스러워지기 때문이다.

### 11.4 비용 모니터링

마이그레이션 직후 첫 일주일은 일별 비용을 확인해야 한다. GPT-5.5는 출력 가격이 GPT-4o-mini의 5배 수준이라, mini로 충분한 작업을 5.5로 돌리면 비용이 급증한다. OpenAI 대시보드의 사용량 알림을 일별 임계값으로 설정해두는 게 좋다.

```python
# 호출 시 모델별 비용 누적
PRICING = {
    "gpt-5.5": {"input": 1.25, "output": 10.00},
    "gpt-5.5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5.5-nano": {"input": 0.05, "output": 0.40},
}

def calc_cost(usage, model):
    p = PRICING[model]
    return (usage.prompt_tokens * p["input"] + usage.completion_tokens * p["output"]) / 1_000_000
```

이 함수를 모든 호출 후에 돌려서 누적 비용을 로그로 남기면, 비정상적으로 비용이 증가하는 호출 패턴을 빠르게 잡을 수 있다.
