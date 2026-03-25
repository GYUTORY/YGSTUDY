---
title: Claude
tags: [ai, claude, anthropic, llm, api]
updated: 2026-03-25
---

# Claude

## 1. Claude란

Anthropic이 만든 대규모 언어 모델이다. GPT-4o, Gemini와 함께 현재 실무에서 가장 많이 쓰이는 LLM 중 하나다.

Constitutional AI라는 자체 안전 학습 방식을 적용했고, 코딩·분석·글쓰기 등 범용 작업에서 높은 성능을 보인다. 2025년 기준 Claude 3.5 시리즈에서 Claude 4 시리즈로 넘어왔고, 2026년 현재 Claude 4.5/4.6이 최신이다.

---

## 2. 모델 패밀리

Claude는 세 가지 등급으로 나뉜다. 같은 세대라도 등급에 따라 성능과 비용 차이가 크다.

### 2.1 Opus / Sonnet / Haiku

| 구분 | Opus | Sonnet | Haiku |
|------|------|--------|-------|
| **포지션** | 최상위 모델 | 중간 모델 | 경량 모델 |
| **속도** | 느림 | 중간 | 빠름 |
| **비용** | 가장 비쌈 | 중간 | 저렴 |
| **적합한 용도** | 복잡한 코드 분석, 긴 문서 작성, 고난도 추론 | 일반 코딩, 질의응답, 대부분의 작업 | 분류, 요약, 단순 변환, 대량 처리 |

### 2.2 실제 사용감 차이

**Opus**: 복잡한 코드베이스를 분석하거나 여러 파일에 걸친 리팩토링을 시킬 때 확실히 차이가 난다. 코드 문맥을 더 잘 유지하고, 엣지 케이스를 스스로 찾아서 처리하는 경우가 많다. 다만 응답 속도가 느려서 단순한 질문에 쓰면 답답하다.

**Sonnet**: 실무에서 가장 많이 쓰게 되는 모델이다. 코드 리뷰, 버그 수정, 기능 구현 등 대부분의 작업을 무난하게 처리한다. Opus와 비교하면 아주 복잡한 멀티스텝 추론에서 차이가 나지만, 일반적인 개발 작업에서는 체감 차이가 크지 않다.

**Haiku**: 로그 파싱, 텍스트 분류, 간단한 코드 변환 같은 반복 작업에 적합하다. API 호출 단가가 낮아서 대량 처리 파이프라인에 넣기 좋다. 복잡한 코딩 작업에 쓰면 실수가 잦다.

### 2.3 모델 선택 기준

```
복잡한 아키텍처 설계, 대규모 리팩토링 → Opus
일반 개발 작업, 코드 리뷰, 문서 작성    → Sonnet
분류, 추출, 단순 변환, 대량 배치       → Haiku
```

비용이 제한적이라면 Sonnet으로 시작하고, 결과물 품질이 부족할 때만 Opus로 올리는 게 현실적이다.

---

## 3. API 사용법

### 3.1 Messages API 기본

Claude API는 Messages API를 사용한다. OpenAI의 Chat Completions API와 구조가 비슷하지만, 파라미터 이름과 역할 구분 방식이 다르다.

```python
import anthropic

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Python에서 dataclass와 Pydantic 모델의 차이를 설명해줘"}
    ]
)

print(message.content[0].text)
```

### 3.2 System Prompt

System prompt는 `messages` 배열이 아닌 별도 파라미터로 전달한다. OpenAI처럼 messages 안에 `role: system`으로 넣으면 에러가 난다.

```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="너는 시니어 백엔드 개발자야. 코드 리뷰를 할 때 보안 이슈를 우선 지적해.",
    messages=[
        {"role": "user", "content": "이 코드 리뷰해줘:\n\n" + code}
    ]
)
```

System prompt에 역할, 제약 조건, 출력 형식 등을 넣는다. 길이 제한은 따로 없지만, 너무 길면 토큰을 많이 소모하니 핵심만 넣어야 한다.

### 3.3 멀티턴 대화

```python
messages = [
    {"role": "user", "content": "JWT 토큰 검증 미들웨어를 만들어줘"},
    {"role": "assistant", "content": "...이전 응답..."},
    {"role": "user", "content": "리프레시 토큰 로직도 추가해줘"}
]

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=messages
)
```

`user`와 `assistant`가 번갈아 나와야 한다. 같은 role이 연속으로 오면 에러가 발생한다.

### 3.4 Streaming

긴 응답을 받을 때는 streaming을 쓴다. 사용자에게 실시간으로 보여줘야 하는 경우 필수다.

```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=[
        {"role": "user", "content": "Spring Boot 3에서 WebFlux 마이그레이션 방법을 설명해줘"}
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

스트리밍 응답에서 전체 결과를 모아야 할 때는 `stream.get_final_message()`로 최종 메시지 객체를 얻을 수 있다.

### 3.5 TypeScript SDK

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const message = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [
    { role: "user", content: "Express에서 에러 핸들링 미들웨어 패턴 알려줘" }
  ],
});

console.log(message.content[0].text);
```

---

## 4. 토큰과 과금

### 4.1 토큰 과금 구조

Claude API는 입력 토큰과 출력 토큰을 따로 과금한다. 출력이 입력보다 비싸다.

| 모델 (4.6 기준) | 입력 (1M 토큰) | 출력 (1M 토큰) |
|-----------------|---------------|---------------|
| Opus 4.6 | $15 | $75 |
| Sonnet 4.6 | $3 | $15 |
| Haiku 4.5 | $0.80 | $4 |

가격은 수시로 변동되니 공식 문서를 확인해야 한다. Opus는 출력 토큰 단가가 Haiku의 거의 20배다.

### 4.2 토큰 계산 시 주의사항

- System prompt도 매 요청마다 입력 토큰에 포함된다. 멀티턴 대화에서 system prompt가 길면 비용이 빠르게 늘어난다.
- 이전 대화 내역을 계속 붙여 보내므로, 대화가 길어질수록 입력 토큰이 기하급수적으로 증가한다.
- 이미지를 포함하면 토큰 소모가 크다. 고해상도 이미지 하나가 수천 토큰을 차지하는 경우가 있다.

### 4.3 비용 절감 방법

```python
# 1. 대화 내역 잘라내기 — 오래된 메시지 제거
if len(messages) > 20:
    messages = messages[-10:]  # 최근 10개만 유지

# 2. Prompt Caching — 반복되는 긴 컨텍스트에 캐싱 적용
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": long_system_prompt,
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=messages
)
```

Prompt Caching을 쓰면 캐시 히트 시 입력 토큰 비용이 90% 줄어든다. 긴 system prompt나 대량의 참고 문서를 반복 전송할 때 효과가 크다.

---

## 5. 컨텍스트 윈도우

### 5.1 모델별 컨텍스트 크기

| 모델 | 컨텍스트 윈도우 |
|------|----------------|
| Claude 4.6 Opus | 200K (1M 확장 지원) |
| Claude 4.6 Sonnet | 200K |
| Claude 4.5 Haiku | 200K |

200K 토큰은 대략 코드 파일 수백 개, 일반 텍스트 기준 책 한 권 분량이다.

### 5.2 컨텍스트 크기별 활용

**짧은 컨텍스트 (1K~10K 토큰)**
단일 함수 리뷰, 간단한 질문, 코드 변환 등. 대부분의 일상적인 API 호출이 여기에 해당한다.

**중간 컨텍스트 (10K~50K 토큰)**
파일 여러 개를 넘겨서 리팩토링하거나, API 문서를 참고하며 코드를 생성하는 작업. 실무에서 가장 자주 쓰는 범위다.

**긴 컨텍스트 (50K~200K 토큰)**
대규모 코드베이스 분석, 긴 문서 요약, 여러 파일에 걸친 의존성 추적. 컨텍스트가 길어질수록 중간 부분의 정보를 놓치는 현상(lost in the middle)이 발생할 수 있다. 중요한 정보는 앞이나 뒤에 배치하는 게 좋다.

### 5.3 컨텍스트 관리 실무 팁

- 전체 코드베이스를 무작정 넣지 말고, 관련 파일만 선별해서 넣어야 한다.
- RAG(검색 증강 생성)를 조합하면 필요한 코드 조각만 컨텍스트에 넣을 수 있어서 토큰 낭비를 줄인다.
- 대화가 길어지면 요약 후 새 대화를 시작하는 방식이 품질과 비용 모두에 유리하다.

---

## 6. Claude Web / Desktop 앱

API가 아닌 claude.ai 웹이나 Desktop 앱으로 사용할 때의 주요 기능이다.

### 6.1 Projects

프로젝트 단위로 대화를 묶고, 공유 지식을 설정할 수 있다.

- **Project Knowledge**: 프로젝트에 파일이나 텍스트를 등록하면 해당 프로젝트의 모든 대화에서 자동으로 참조한다. API의 system prompt와 비슷한 역할이다.
- **Custom Instructions**: 프로젝트별로 응답 스타일이나 제약 조건을 지정한다.
- 팀 플랜에서는 프로젝트를 팀원과 공유할 수 있다. 코드 리뷰 기준, 코딩 컨벤션 문서를 넣어두면 팀 전체가 동일한 기준으로 사용하게 된다.

### 6.2 Artifacts

대화 중에 생성된 코드, 문서, SVG, HTML 등을 별도 패널에 렌더링해서 보여주는 기능이다.

- 코드를 생성하면 별도 창에서 바로 확인할 수 있다.
- HTML/CSS/JS 조합은 실시간 프리뷰가 된다.
- Mermaid 다이어그램, SVG 등도 렌더링된다.
- 생성된 artifact를 복사하거나 다운로드할 수 있다.

실무에서는 프로토타입 UI를 빠르게 확인하거나, 아키텍처 다이어그램을 Mermaid로 그릴 때 쓸만하다.

---

## 7. 다른 LLM과의 체감 비교

### 7.1 Claude vs GPT-4o

| 항목 | Claude | GPT-4o |
|------|--------|--------|
| **코딩** | 긴 코드 생성, 리팩토링에서 맥락 유지가 잘 됨 | 짧은 코드 스니펫, 빠른 답변에 강함 |
| **지시 따르기** | system prompt를 꼼꼼하게 따르는 편 | 가끔 지시를 무시하거나 자의적으로 해석 |
| **한국어** | 자연스러운 편이나 가끔 번역투 | 비슷한 수준 |
| **안전 거부** | 과도하게 거부하는 경우가 있음 | 상대적으로 덜 거부 |
| **멀티모달** | 이미지 입력 가능, 이미지 생성 불가 | 이미지 입출력 모두 가능 |
| **도구 연동** | Function calling 지원 | Function calling + 자체 플러그인 |

코딩 작업에서 Claude는 긴 컨텍스트에서 일관성을 유지하는 능력이 좋다. 파일 10개를 넘겨서 "이 구조를 리팩토링해줘"라고 하면 GPT-4o보다 맥락을 잘 따라가는 경우가 많다. 반면 GPT-4o는 짧은 질문에 빠르게 답하는 데 강하고, 이미지 생성이 필요한 작업에서는 대안이 없다.

### 7.2 Claude vs Gemini

| 항목 | Claude | Gemini |
|------|--------|--------|
| **코딩** | 코드 품질이 안정적 | 간단한 작업은 잘 하지만, 복잡하면 실수가 느는 편 |
| **컨텍스트** | 200K (Opus 1M) | 1M~2M |
| **멀티모달** | 이미지, PDF 입력 | 이미지, 비디오, 오디오 입력 |
| **Google 연동** | 없음 | Google Workspace, Search 연동 |
| **가격** | 중간~높음 | 상대적으로 저렴 |

Gemini는 컨텍스트 윈도우가 크고 Google 생태계와 연동이 되는 게 장점이다. 대량의 문서를 한번에 분석하거나 Google Docs/Sheets와 연결해서 쓸 때 편하다. 코딩 작업의 정확도에서는 Claude가 앞서는 경우가 많다.

### 7.3 실무에서의 선택

모델 하나만 고집할 필요는 없다. 작업 성격에 따라 섞어 쓰는 게 현실적이다.

- **코드 리뷰, 리팩토링, 문서 작성**: Claude가 낫다
- **빠른 질문, 이미지 생성**: GPT-4o
- **대량 문서 분석, Google 생태계 연동**: Gemini
- **비용 민감한 대량 처리**: Claude Haiku나 Gemini Flash

어떤 모델이 "최고"인지는 작업마다 다르다. 중요한 건 각 모델의 특성을 파악하고, 상황에 맞게 고르는 것이다.

---

## 8. API 사용 시 자주 겪는 문제

### 8.1 Rate Limit

요청이 많으면 429 에러가 발생한다. 분당 요청 수(RPM)와 분당 토큰 수(TPM) 제한이 있다.

```python
import time
from anthropic import RateLimitError

def call_with_retry(client, **kwargs):
    for attempt in range(5):
        try:
            return client.messages.create(**kwargs)
        except RateLimitError:
            wait = 2 ** attempt
            time.sleep(wait)
    raise Exception("Rate limit 초과, 재시도 실패")
```

Tier가 높을수록 제한이 느슨해진다. 사용량이 많으면 Anthropic에 Tier 업그레이드를 요청해야 한다.

### 8.2 max_tokens 관련

`max_tokens`는 필수 파라미터다. 빼먹으면 에러가 난다. OpenAI API와 다른 부분이니 주의해야 한다.

응답이 `max_tokens`에 도달하면 `stop_reason`이 `"end_turn"`이 아닌 `"max_tokens"`로 온다. 코드 생성 중 잘린 건지 정상 종료인지 확인하려면 이 값을 체크해야 한다.

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,  # 필수
    messages=[...]
)

if response.stop_reason == "max_tokens":
    print("응답이 잘렸음 — max_tokens를 늘리거나 이어서 요청 필요")
```

### 8.3 이미지 전송

이미지는 base64로 인코딩해서 보낸다. URL 직접 전달도 가능하다.

```python
import base64

with open("screenshot.png", "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "이 스크린샷에서 에러 원인을 찾아줘"
                }
            ],
        }
    ],
)
```

---

## 9. Extended Thinking

Claude는 Extended Thinking 기능을 지원한다. 복잡한 문제에서 모델이 답변 전에 내부적으로 추론 과정을 거치게 하는 기능이다.

```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000  # thinking에 쓸 토큰 예산
    },
    messages=[
        {"role": "user", "content": "이 알고리즘의 시간 복잡도를 분석해줘:\n\n" + code}
    ]
)

# thinking 블록과 실제 응답이 분리되어 옴
for block in response.content:
    if block.type == "thinking":
        print("추론 과정:", block.thinking)
    elif block.type == "text":
        print("답변:", block.text)
```

thinking에 할당한 토큰도 출력 토큰으로 과금된다. 단순한 질문에 thinking을 켜면 비용만 늘고 답변 품질 차이는 거의 없다. 복잡한 수학 문제, 다단계 논리 추론, 대규모 코드 분석 같은 작업에서만 켜는 게 좋다.
