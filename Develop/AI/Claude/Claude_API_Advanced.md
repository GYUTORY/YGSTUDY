---
title: Claude API 고급 기능
tags: [ai, claude, anthropic, api, batch, citations, files, structured-output, prompt-caching]
updated: 2026-04-15
---

# Claude API 고급 기능

기본 Messages API만으로도 대부분의 작업이 가능하지만, 실무에서 대량 처리나 출처 관리, 파일 업로드가 필요한 순간이 온다. 이 문서는 Claude API에서 제공하는 고급 기능들을 다룬다.

---

## 1. Message Batches API

### 1.1 배치 처리가 필요한 상황

수천 건의 고객 리뷰를 분류하거나, 로그 파일 수백 개를 분석하거나, 대량의 코드 파일에 리뷰를 돌리는 작업이 있다. 이런 건 건당 API를 호출하면 시간도 오래 걸리고 비용도 부담된다.

Message Batches API는 최대 100,000건의 요청을 하나의 배치로 묶어서 비동기로 처리한다. 개별 Messages API와 동일한 파라미터를 쓰지만, 결과를 바로 받지 않고 나중에 조회하는 방식이다. 대신 **요금이 50% 할인**된다. Sonnet 기준으로 출력 토큰이 $15에서 $7.5로 내려가는 셈이다.

24시간 이내에 결과가 나온다. 보통은 수 분에서 수십 분 안에 끝나지만, 보장되는 건 24시간이다. 실시간 응답이 필요 없는 작업에만 써야 한다.

### 1.2 배치 생성

```python
import anthropic
import json

client = anthropic.Anthropic()

# 배치 요청 생성
batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": "review-001",
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": "이 리뷰의 감성을 분석해줘: '배송은 빨랐는데 포장이 엉망이다'"}
                ]
            }
        },
        {
            "custom_id": "review-002",
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": "이 리뷰의 감성을 분석해줘: '가격 대비 품질이 괜찮다'"}
                ]
            }
        }
    ]
)

print(batch.id)              # "msgbatch_01ABC..."
print(batch.processing_status)  # "in_progress"
```

`custom_id`는 각 요청을 식별하는 키다. 결과를 조회할 때 이 ID로 어떤 요청의 결과인지 구분한다. 중복되면 에러가 난다.

`params`는 일반 `messages.create()`에 넘기는 파라미터와 동일하다. `model`, `max_tokens`, `messages`, `system`, `tools` 등을 그대로 쓴다. 배치 안에서 요청마다 다른 모델을 쓸 수도 있다.

### 1.3 배치 상태 조회와 결과 수집

```python
# 상태 조회
batch = client.messages.batches.retrieve(batch.id)
print(batch.processing_status)  # "in_progress" | "ended"

# 처리 건수 확인
counts = batch.request_counts
print(f"처리 중: {counts.processing}")
print(f"성공: {counts.succeeded}")
print(f"에러: {counts.errored}")
```

`processing_status`가 `"ended"`가 되면 결과를 가져올 수 있다. 전체가 끝나야 조회 가능한 게 아니라, 개별 건이 완료되는 대로 스트리밍으로 받을 수 있다.

```python
# 결과 순회 — JSONL 스트리밍
for result in client.messages.batches.results(batch.id):
    match result.result.type:
        case "succeeded":
            message = result.result.message
            print(f"[{result.custom_id}] {message.content[0].text}")
        case "errored":
            print(f"[{result.custom_id}] 에러: {result.result.error}")
        case "expired":
            print(f"[{result.custom_id}] 24시간 내 미처리")
```

결과는 JSONL 형식으로 온다. 각 결과의 `type`이 `succeeded`, `errored`, `expired` 중 하나다. `expired`는 24시간 안에 처리되지 못한 건이다. 서버 부하가 심할 때 드물게 발생한다.

### 1.4 대량 배치 실무 패턴

실제로 수천 건을 처리할 때는 파일에서 읽어서 배치를 만드는 경우가 대부분이다.

```python
import csv

def create_batch_from_csv(client, csv_path):
    requests = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            requests.append({
                "custom_id": row["id"],
                "params": {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 256,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"다음 텍스트를 positive/negative/neutral 중 하나로 분류해. 분류 결과만 출력해.\n\n{row['text']}"
                        }
                    ]
                }
            })

    # 100,000건 제한이 있으니 나눠서 보내야 할 수 있다
    BATCH_SIZE = 100_000
    batches = []
    for i in range(0, len(requests), BATCH_SIZE):
        chunk = requests[i:i + BATCH_SIZE]
        batch = client.messages.batches.create(requests=chunk)
        batches.append(batch.id)

    return batches
```

분류처럼 단순한 작업은 Haiku를 쓰면 비용이 크게 줄어든다. 배치 50% 할인에 Haiku의 낮은 단가가 겹치면, Opus 실시간 호출 대비 수십 배 차이가 난다.

### 1.5 배치 취소

진행 중인 배치를 취소할 수 있다. 이미 완료된 건은 그대로 남고, 아직 처리 안 된 건만 취소된다.

```python
client.messages.batches.cancel(batch.id)
```

취소해도 이미 처리된 건에 대한 비용은 청구된다.

---

## 2. Citations API

### 2.1 출처 추적이 필요한 이유

LLM에게 문서를 넘기고 질문하면 답은 잘 하는데, "이 내용이 원본 문서의 어디에 있는 건지" 확인하기 어렵다. 사내 문서 검색 시스템이나 고객 응대 봇에서 이게 문제가 된다. 답변의 근거를 보여줘야 신뢰할 수 있기 때문이다.

Citations API는 Claude의 응답에서 각 문장이 어떤 소스의 어느 부분을 참조했는지 자동으로 추적해준다. 개발자가 출처 파싱 로직을 직접 만들 필요가 없다.

### 2.2 사용법

소스 문서를 `content` 배열에 `document` 타입으로 넣고, `citations`를 활성화한다.

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": "2026년 1분기 매출은 전년 대비 23% 증가한 450억원을 기록했다. "
                               "영업이익률은 15.2%로 전 분기 대비 2.1%p 상승했다. "
                               "신규 서비스 매출이 전체의 35%를 차지하며 성장을 견인했다."
                    },
                    "title": "2026 Q1 실적 보고서",
                    "citations": {"enabled": True}
                },
                {
                    "type": "text",
                    "text": "1분기 실적 요약해줘"
                }
            ]
        }
    ]
)
```

응답의 `content` 배열에 `text` 블록과 `cite` 블록이 섞여서 온다.

```python
for block in response.content:
    if block.type == "text":
        print(block.text, end="")
    elif block.type == "cite":
        print(block.text, end="")
        # 출처 정보
        print(f" [출처: {block.document_title}, "
              f"위치: {block.start_index}~{block.end_index}]")
```

`cite` 블록에는 원본 문서의 제목(`document_title`)과 참조 위치(`start_index`, `end_index`)가 포함된다. 이 인덱스로 원본 텍스트에서 해당 구간을 하이라이트할 수 있다.

### 2.3 소스 타입

Citations API는 여러 종류의 소스를 지원한다.

```python
# 일반 텍스트
{
    "type": "document",
    "source": {"type": "text", "media_type": "text/plain", "data": "..."},
    "title": "참고 문서",
    "citations": {"enabled": True}
}

# base64 인코딩된 PDF
{
    "type": "document",
    "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_base64},
    "title": "계약서.pdf",
    "citations": {"enabled": True}
}

# URL로 제공하는 문서
{
    "type": "document",
    "source": {"type": "url", "url": "https://example.com/doc.pdf"},
    "title": "외부 문서",
    "citations": {"enabled": True}
}
```

PDF를 넘기면 페이지 번호까지 추적된다. RAG 파이프라인에서 검색된 청크 여러 개를 각각 document로 넘기면, Claude가 답변할 때 어떤 청크를 참조했는지 자동으로 매핑해준다.

### 2.4 주의사항

- Citations를 켜면 응답 토큰이 약간 늘어난다. 출처 메타데이터가 응답에 포함되기 때문이다.
- 여러 문서를 넘길 때 문서마다 `citations`를 개별로 켜고 끌 수 있다. 참고용으로만 넘기는 문서는 꺼두면 토큰을 아낀다.
- Claude가 문서에 없는 내용을 생성하면 citation이 붙지 않는다. 이걸 이용해서 hallucination 여부를 판단하는 데 쓸 수 있다. citation 없는 문장은 모델이 자체 생성한 내용일 가능성이 높다.

---

## 3. Files API

### 3.1 파일 업로드가 필요한 경우

Messages API에 직접 base64로 파일을 넣으면, 같은 파일을 여러 번 쓸 때마다 매번 전송해야 한다. 10MB짜리 PDF를 대화 5번에 걸쳐 참조하면 50MB를 전송하는 셈이다.

Files API는 파일을 한 번 업로드하면 ID로 참조할 수 있게 해준다. 업로드된 파일은 서버에 보관되고, 여러 API 호출에서 재사용한다.

### 3.2 파일 업로드

```python
# 파일 업로드
with open("codebase_report.pdf", "rb") as f:
    uploaded = client.files.create(
        file=f,
        purpose="vision"  # 이미지/PDF 분석용
    )

print(uploaded.id)    # "file-abc123..."
print(uploaded.filename)
print(uploaded.size)
```

업로드 가능한 파일 타입은 PDF, 이미지(PNG, JPEG, GIF, WebP), 텍스트 파일 등이다. 파일 크기 제한은 용도에 따라 다르지만, 일반적으로 최대 32MB까지 가능하다.

### 3.3 업로드된 파일 사용

```python
# Messages API에서 파일 ID로 참조
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": uploaded.id
                    }
                },
                {
                    "type": "text",
                    "text": "이 보고서에서 성능 병목 구간을 찾아줘"
                }
            ]
        }
    ]
)
```

파일 ID를 `source`에 넣으면 된다. base64로 매번 인코딩하는 것보다 깔끔하고, 같은 파일을 여러 대화에서 재사용할 때 전송량이 줄어든다.

### 3.4 파일 관리

```python
# 파일 목록 조회
files = client.files.list()
for f in files.data:
    print(f"{f.id} — {f.filename} ({f.size} bytes)")

# 파일 삭제
client.files.delete(uploaded.id)
```

업로드된 파일은 명시적으로 삭제하지 않으면 계속 남아 있다. 더 이상 필요 없는 파일은 정리해야 한다. 배치 작업이 끝난 뒤 임시 파일을 삭제하는 로직을 넣어두는 게 좋다.

### 3.5 배치와 조합

Files API는 배치 처리와 함께 쓸 때 유용하다. 대량의 PDF를 먼저 업로드하고, 배치 요청에서 파일 ID로 참조하면 데이터 전송이 한 번으로 끝난다.

```python
# 1. 파일들을 먼저 업로드
file_ids = []
for pdf_path in pdf_paths:
    with open(pdf_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="vision")
        file_ids.append((pdf_path, uploaded.id))

# 2. 배치 요청에서 파일 ID로 참조
requests = []
for path, file_id in file_ids:
    requests.append({
        "custom_id": path,
        "params": {
            "model": "claude-sonnet-4-6",
            "max_tokens": 2048,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id}
                        },
                        {"type": "text", "text": "이 문서를 3줄로 요약해줘"}
                    ]
                }
            ]
        }
    })

batch = client.messages.batches.create(requests=requests)
```

---

## 4. Structured Output

### 4.1 JSON 응답이 필요한 상황

API에서 받은 응답을 파싱해서 DB에 넣거나 다른 시스템에 넘겨야 할 때, 자유 형식 텍스트로 오면 곤란하다. "긍정적이에요"라는 텍스트를 받으면 `positive`로 매핑하는 로직을 따로 짜야 한다. JSON으로 오면 바로 쓸 수 있다.

Claude에서 구조화된 응답을 받는 방법은 크게 두 가지다.

### 4.2 tool_use를 활용한 스키마 강제

가장 확실한 방법이다. 도구를 정의하되 실제로 실행하지 않고, Claude가 반환하는 `input` 객체를 결과로 쓴다. JSON Schema로 출력 형식을 강제하니 파싱 실패가 거의 없다.

```python
# 출력 스키마를 도구로 정의
tools = [
    {
        "name": "classify_review",
        "description": "리뷰 감성 분류 결과를 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"]
                },
                "confidence": {
                    "type": "number",
                    "description": "0.0~1.0 사이의 신뢰도"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "핵심 키워드 목록"
                }
            },
            "required": ["sentiment", "confidence", "keywords"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "tool", "name": "classify_review"},  # 이 도구를 반드시 사용하게 강제
    messages=[
        {"role": "user", "content": "리뷰: '배송은 빨랐는데 포장이 엉망이다. 제품 자체는 괜찮음.'"}
    ]
)

# tool_use 블록에서 구조화된 데이터를 꺼낸다
tool_block = next(b for b in response.content if b.type == "tool_use")
result = tool_block.input
print(result)
# {"sentiment": "neutral", "confidence": 0.7, "keywords": ["배송", "포장", "제품"]}
```

핵심은 `tool_choice`를 `{"type": "tool", "name": "classify_review"}`로 설정하는 것이다. 이러면 Claude가 무조건 이 도구를 호출하고, `input_schema`에 맞는 JSON을 생성한다. 텍스트 응답 없이 바로 구조화된 데이터만 온다.

이 패턴의 장점은 JSON Schema의 `enum`, `required`, 타입 제약 등을 그대로 쓸 수 있다는 점이다. `sentiment`가 반드시 세 값 중 하나여야 하고, `confidence`가 숫자여야 하는 등의 제약이 스키마 레벨에서 강제된다.

### 4.3 프롬프트 기반 JSON 응답

도구 없이 프롬프트에서 JSON 출력을 요청하는 방법이다. 간단한 경우에 쓸 수 있지만, 형식이 깨지는 경우가 있어서 프로덕션에서는 tool_use 방식을 권장한다.

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="응답은 반드시 JSON 형식으로만 해. 다른 텍스트를 포함하지 마.",
    messages=[
        {
            "role": "user",
            "content": (
                "다음 리뷰를 분석해서 JSON으로 반환해.\n"
                '형식: {"sentiment": "positive|negative|neutral", "score": 0~10}\n\n'
                "리뷰: '가격 대비 품질이 괜찮다'"
            )
        }
    ]
)

import json
try:
    result = json.loads(response.content[0].text)
except json.JSONDecodeError:
    # Claude가 JSON 앞뒤에 설명 텍스트를 붙이는 경우가 있다
    pass
```

이 방식의 문제점:

- Claude가 JSON 앞에 "결과는 다음과 같습니다:" 같은 텍스트를 붙이는 경우가 있다
- 스키마 제약이 프롬프트 수준이라 필드가 빠지거나 타입이 바뀔 수 있다
- `json.loads()`가 실패하면 재시도 로직이 필요하다

프롬프트에서 JSON을 달라고 할 때는 prefill 기법을 쓰면 확률이 올라간다. assistant 메시지를 `{`로 시작하게 만들면 Claude가 JSON으로 이어 쓸 가능성이 높아진다.

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "리뷰 분석해서 JSON으로: '배송이 느리다'"},
        {"role": "assistant", "content": "{"}  # prefill — JSON으로 시작하게 유도
    ]
)

# 응답이 "{"로 시작하지 않으니 붙여줘야 한다
text = "{" + response.content[0].text
result = json.loads(text)
```

### 4.4 복잡한 스키마 설계

중첩 객체나 배열이 포함된 복잡한 출력도 tool_use로 처리할 수 있다.

```python
tools = [
    {
        "name": "extract_api_spec",
        "description": "API 문서에서 엔드포인트 정보를 추출한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "endpoints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                            "path": {"type": "string"},
                            "description": {"type": "string"},
                            "parameters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "required": {"type": "boolean"}
                                    },
                                    "required": ["name", "type", "required"]
                                }
                            }
                        },
                        "required": ["method", "path", "description"]
                    }
                }
            },
            "required": ["endpoints"]
        }
    }
]
```

스키마가 복잡할수록 도구 정의에 소모되는 토큰이 늘어난다. 스키마 자체가 매 요청의 입력 토큰에 포함되기 때문이다. 배치 처리에서 같은 스키마를 수천 번 쓸 때는 프롬프트 캐싱과 조합하면 비용을 줄일 수 있다.

---

## 5. Prompt Caching 심화

### 5.1 캐싱 원리 복습

Prompt Caching은 요청의 프리픽스(앞부분)가 이전 요청과 동일하면 해당 부분의 토큰 처리를 생략하고 캐시에서 가져오는 기능이다. 캐시 히트 시 해당 토큰의 입력 비용이 90% 할인된다.

캐시 판정은 **프리픽스 매칭**으로 동작한다. 요청의 앞부분부터 순서대로 비교해서, 이전 요청과 동일한 구간까지가 캐시 대상이다. 중간에 하나라도 다르면 그 지점 이후는 전부 캐시 미스가 된다.

```
요청 1: [system prompt] + [tools 정의] + [대화 내역] + [새 메시지]
요청 2: [system prompt] + [tools 정의] + [대화 내역] + [새 메시지 2]
         ─────────────────────────────────────────────
         이 구간이 동일하면 캐시 히트 → 90% 할인
```

### 5.2 캐시 히트율을 높이는 프리픽스 순서

프리픽스 매칭이라는 특성 때문에, **변하지 않는 내용을 앞에, 자주 바뀌는 내용을 뒤에** 배치해야 캐시 히트율이 올라간다.

```python
# 캐시 히트율이 높은 순서
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": long_system_prompt,          # 1. 시스템 프롬프트 — 거의 안 바뀜
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": reference_documentation,      # 2. 참고 문서 — 세션 동안 고정
            "cache_control": {"type": "ephemeral"}
        }
    ],
    tools=tools_with_cache,                       # 3. 도구 정의 — 세션 동안 고정
    messages=[
        # 4. 이전 대화 내역 — 점진적으로 늘어남
        {"role": "user", "content": "이전 질문"},
        {"role": "assistant", "content": "이전 답변"},
        # 5. 새 메시지 — 매번 다름
        {"role": "user", "content": "새 질문"}
    ]
)
```

이 순서를 뒤집으면 어떻게 될까. 새 메시지를 앞에 넣으면 첫 토큰부터 달라지니 캐시가 전혀 히트하지 않는다. 당연한 얘기 같지만, 실제로 RAG 컨텍스트를 system prompt 안에 동적으로 넣거나, 대화 내역 중간에 검색 결과를 삽입하면 프리픽스가 깨진다.

### 5.3 cache_control 배치

`cache_control`은 "이 지점까지를 캐시 경계로 삼아라"는 표시다. 캐시 브레이크포인트라고 생각하면 된다.

```python
system=[
    {
        "type": "text",
        "text": "시스템 프롬프트 내용...",
        "cache_control": {"type": "ephemeral"}  # 브레이크포인트 1
    }
]

tools=[
    {
        "name": "search",
        "description": "검색 도구",
        "input_schema": {...},
        "cache_control": {"type": "ephemeral"}  # 브레이크포인트 2 — tools 배열의 마지막 도구에 붙인다
    }
]

messages=[
    {"role": "user", "content": "이전 질문"},
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "이전 답변...",
                "cache_control": {"type": "ephemeral"}  # 브레이크포인트 3
            }
        ]
    },
    {"role": "user", "content": "새 질문"}
]
```

브레이크포인트는 최대 4개까지 설정할 수 있다. 너무 많이 넣는다고 더 좋아지는 게 아니다. 변경 빈도가 다른 구간의 경계에만 넣으면 된다.

캐시 가능한 최소 토큰 수가 있다. Sonnet/Haiku는 1,024토큰, Opus는 2,048토큰 이상이어야 캐시가 생성된다. 시스템 프롬프트가 짧으면 캐시가 아예 안 된다.

### 5.4 캐시 TTL과 비용 구조

캐시는 마지막 사용 시점으로부터 **5분** 동안 유지된다. 5분 안에 같은 프리픽스로 요청이 오면 TTL이 갱신된다. 5분이 지나면 캐시가 사라지고, 다음 요청에서 다시 캐시를 생성해야 한다.

| 구분 | 비용 (기본 입력 토큰 대비) |
|------|-------------------------|
| 캐시 쓰기 (첫 요청) | 1.25배 — 25% 추가 |
| 캐시 읽기 (히트) | 0.1배 — 90% 할인 |
| 캐시 미스 | 1.0배 — 기본 요금 |

계산해보면, 동일 프리픽스로 2회 이상 요청하면 캐시 쓰기 비용을 회수하고 이득이 시작된다.

```
캐시 없이 3회: 1.0 + 1.0 + 1.0 = 3.0
캐시 사용 3회: 1.25 + 0.1 + 0.1 = 1.45  → 52% 절감
```

### 5.5 캐시 히트 확인

응답의 `usage` 필드에서 캐시 관련 토큰 수를 확인할 수 있다.

```python
response = client.messages.create(...)

usage = response.usage
print(f"입력 토큰: {usage.input_tokens}")
print(f"캐시 생성 토큰: {usage.cache_creation_input_tokens}")
print(f"캐시 읽기 토큰: {usage.cache_read_input_tokens}")
```

- `cache_creation_input_tokens` > 0 : 캐시가 새로 생성됨 (1.25배 과금)
- `cache_read_input_tokens` > 0 : 캐시 히트 (0.1배 과금)
- 둘 다 0 : 캐시 미스이거나 캐시 제어를 안 넣었음

멀티턴 대화에서 `cache_read_input_tokens`가 꾸준히 늘어나면 캐시가 잘 작동하고 있는 것이다. 갑자기 0이 되면 프리픽스가 깨졌거나 TTL이 만료된 것이다.

### 5.6 캐싱이 깨지는 패턴

실무에서 캐시가 기대대로 동작하지 않는 경우가 꽤 있다.

**RAG 컨텍스트를 system prompt에 넣는 경우**

```python
# 캐시가 깨지는 패턴
system=[
    {"type": "text", "text": "기본 지시사항..."},
    {"type": "text", "text": rag_results},  # 매번 다른 검색 결과
    # → 두 번째 블록부터 달라지니 첫 번째 블록만 캐시됨
]

# 개선: RAG 결과는 messages에 넣는다
system=[
    {
        "type": "text",
        "text": "기본 지시사항...",
        "cache_control": {"type": "ephemeral"}
    }
]
messages=[
    {
        "role": "user",
        "content": [
            {"type": "text", "text": f"참고 자료:\n{rag_results}"},
            {"type": "text", "text": "질문 내용"}
        ]
    }
]
```

**대화 중간에 내용을 수정하는 경우**

이전 대화 내역을 요약해서 바꾸거나, 중간 메시지를 삭제하면 그 지점 이후의 캐시가 전부 무효화된다. 대화 내역은 앞에서부터 추가만 해야 프리픽스가 유지된다.

**도구 정의 순서를 바꾸는 경우**

`tools` 배열의 순서가 달라지면 캐시 미스가 발생한다. 도구 정의는 항상 같은 순서로 보내야 한다.

### 5.7 에이전트 루프에서의 캐싱

도구 호출이 반복되는 에이전트 패턴에서 Prompt Caching이 특히 중요하다. 도구를 한 번 호출할 때마다 전체 대화 내역을 다시 보내야 하는데, 캐싱이 없으면 대화가 길어질수록 비용이 급증한다.

```python
def run_agent_with_cache(client, tools, user_message, system_prompt):
    # 도구 정의의 마지막 항목에 cache_control 추가
    cached_tools = tools.copy()
    cached_tools[-1] = {
        **cached_tools[-1],
        "cache_control": {"type": "ephemeral"}
    }

    messages = [{"role": "user", "content": user_message}]

    for turn in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            tools=cached_tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            return response.content

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        # 마지막 tool_result에 cache_control을 붙여서
        # 다음 턴에서 여기까지 캐시되게 한다
        tool_results[-1]["cache_control"] = {"type": "ephemeral"}
        messages.append({"role": "user", "content": tool_results})
```

에이전트 루프에서 턴마다 마지막 `tool_result`에 `cache_control`을 붙이면, 다음 턴에서 system prompt + tools + 이전 대화 전체가 캐시 히트한다. 도구를 5번 호출하는 에이전트라면 2~5번째 호출에서 캐시가 적용되니 비용 차이가 크다.

---

## 6. 기능 조합 실무 패턴

### 6.1 대량 문서 분석 파이프라인

Files API + Batch API + Citations를 조합하면 대량 문서 분석 파이프라인을 만들 수 있다.

```python
def analyze_documents(client, pdf_paths, question):
    # 1단계: 파일 업로드
    file_ids = {}
    for path in pdf_paths:
        with open(path, "rb") as f:
            uploaded = client.files.create(file=f, purpose="vision")
            file_ids[path] = uploaded.id

    # 2단계: 배치 요청 생성 — Citations 활성화
    requests = []
    for path, file_id in file_ids.items():
        requests.append({
            "custom_id": path,
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 2048,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {"type": "file", "file_id": file_id},
                                "title": path,
                                "citations": {"enabled": True}
                            },
                            {"type": "text", "text": question}
                        ]
                    }
                ]
            }
        })

    # 3단계: 배치 실행
    batch = client.messages.batches.create(requests=requests)
    return batch.id
```

이 패턴이면 PDF 1,000개를 분석하는 데 50% 비용 할인을 받으면서 출처 추적까지 된다.

### 6.2 구조화된 데이터 추출 + 캐싱

같은 스키마로 대량의 텍스트에서 데이터를 추출할 때, Structured Output과 Prompt Caching을 조합한다.

```python
extraction_tool = {
    "name": "extract_entity",
    "description": "텍스트에서 인물, 조직, 날짜 정보를 추출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "people": {"type": "array", "items": {"type": "string"}},
            "organizations": {"type": "array", "items": {"type": "string"}},
            "dates": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["people", "organizations", "dates"]
    },
    "cache_control": {"type": "ephemeral"}
}

system_prompt = {
    "type": "text",
    "text": "텍스트에서 개체명을 추출하는 시스템이다. 한국어 텍스트를 처리한다.",
    "cache_control": {"type": "ephemeral"}
}

# 여러 텍스트에 반복 적용 — system + tools가 캐시됨
for text in texts:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=[system_prompt],
        tools=[extraction_tool],
        tool_choice={"type": "tool", "name": "extract_entity"},
        messages=[{"role": "user", "content": text}]
    )
    result = next(b for b in response.content if b.type == "tool_use").input
    save_to_db(result)
```

system prompt와 tool 정의가 매번 동일하니 두 번째 요청부터 캐시 히트가 발생한다. 대량 처리에서 입력 토큰 비용을 크게 줄일 수 있다.

---

## 7. 자주 겪는 문제

### 배치 처리 시 부분 실패

배치의 일부 건이 실패하는 경우가 있다. 전체를 재시도하면 이미 성공한 건까지 다시 처리하게 된다. `custom_id`로 실패한 건만 골라서 새 배치를 만들어야 한다.

```python
failed_ids = []
for result in client.messages.batches.results(batch_id):
    if result.result.type != "succeeded":
        failed_ids.append(result.custom_id)

# 실패한 건만 재시도
if failed_ids:
    retry_requests = [r for r in original_requests if r["custom_id"] in failed_ids]
    client.messages.batches.create(requests=retry_requests)
```

### tool_use로 JSON 받을 때 필드 누락

`required`에 넣지 않은 필드는 Claude가 생략하는 경우가 있다. 반드시 필요한 필드는 전부 `required`에 포함해야 한다. `enum` 제약도 가끔 무시되는 경우가 있는데, system prompt에 "반드시 정의된 값만 사용해"라고 추가하면 줄어든다.

### 캐시가 히트하지 않는 경우

`cache_read_input_tokens`가 계속 0이면 다음을 확인해야 한다.

- 캐시 대상 토큰이 최소 기준(1,024 또는 2,048) 이상인지
- 요청 간 시간이 5분을 넘기지 않는지
- 프리픽스가 정확히 동일한지 — 공백 하나, 줄바꿈 하나만 달라도 미스가 난다
- `tools` 배열의 순서가 바뀌지 않았는지
