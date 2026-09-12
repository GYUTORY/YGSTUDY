---
title: Gemini API 실무 사용법
tags: [ai, api]
updated: 2026-09-12
volatility: high
---

# Gemini API 실무 사용법

## 1. API 접근 방식

Gemini API는 Google AI Studio 경유(ai.google.dev)와 Vertex AI 경유(cloud.google.com) 두 가지 엔드포인트로 나뉜다. 개인 프로젝트나 프로토타입은 Google AI Studio 쪽이 간단하고, 프로덕션 환경에서 IAM 권한 관리나 VPC 내부 호출이 필요하면 Vertex AI를 쓴다.

### 1.1 REST API 직접 호출

```bash
# Google AI Studio 엔드포인트
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{"text": "HTTP 상태 코드 502와 504의 차이를 설명해줘"}]
    }]
  }'
```

응답 구조에서 `candidates[0].content.parts[0].text`가 실제 답변 텍스트다. `candidates`가 배열인 이유는 `candidateCount` 파라미터로 여러 답변을 받을 수 있기 때문인데, 실무에서는 거의 1개만 쓴다.

### 1.2 Vertex AI 엔드포인트

```bash
# Vertex AI 경유 (GCP 프로젝트 필요)
curl -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/gemini-2.5-pro:generateContent" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{"text": "질문 내용"}]
    }]
  }'
```

Vertex AI 쪽은 API Key가 아니라 OAuth 토큰을 쓴다. `gcloud auth print-access-token`으로 받은 토큰은 1시간짜리라서, 장시간 돌아가는 배치 작업에서는 토큰 갱신 로직을 넣어야 한다.

---

## 2. SDK 설정

### 2.1 Python SDK

```bash
pip install google-genai
```

```python
from google import genai

# API Key 방식 (Google AI Studio)
client = genai.Client(api_key="YOUR_API_KEY")

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Spring Boot에서 @Transactional의 propagation 옵션 차이를 알려줘"
)
print(response.text)
```

```python
# Vertex AI 방식 (GCP 프로젝트)
client = genai.Client(
    vertexai=True,
    project="my-project-id",
    location="us-central1"
)
```

Vertex AI 방식에서는 `GOOGLE_APPLICATION_CREDENTIALS` 환경변수에 서비스 계정 키 JSON 경로를 설정하거나, GCE/GKE 위에서 돌리면 기본 서비스 계정을 자동으로 잡는다.

주의할 점: `google-generativeai` 패키지(구버전)와 `google-genai` 패키지(신버전)가 별개다. 2025년 이후로는 `google-genai`를 쓰는 게 맞다. 둘 다 설치되어 있으면 import 충돌이 나서, 기존에 `google-generativeai`가 있으면 먼저 제거해야 한다.

### 2.2 Node.js SDK

```bash
npm install @google/genai
```

```typescript
import { GoogleGenAI } from "@google/genai";

// API Key 방식
const ai = new GoogleGenAI({ apiKey: "YOUR_API_KEY" });

async function ask() {
  const response = await ai.models.generateContent({
    model: "gemini-2.5-pro",
    contents: "Node.js에서 메모리 누수를 찾는 방법을 알려줘",
  });
  console.log(response.text);
}
```

```typescript
// Vertex AI 방식
import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({
  vertexai: true,
  project: "my-project-id",
  location: "us-central1",
});
```

### 2.3 환경변수 관리

API Key를 코드에 직접 넣는 건 기본 중의 기본 실수다. `.env` 파일에 넣고 `.gitignore`에 추가하는 것도 로컬에서만 유효한 방법이고, 프로덕션에서는 Secret Manager나 환경변수 주입을 써야 한다.

```bash
# .env
GEMINI_API_KEY=AIza...

# GCP Secret Manager에 저장하는 경우
gcloud secrets create gemini-api-key --data-file=- <<< "AIza..."
```

```python
import os
from google import genai

# 환경변수에서 읽기
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
```

```python
# GCP Secret Manager에서 읽기 (Cloud Run, GKE 환경)
from google.cloud import secretmanager

def get_api_key() -> str:
    sm = secretmanager.SecretManagerServiceClient()
    name = "projects/my-project/secrets/gemini-api-key/versions/latest"
    response = sm.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")

client = genai.Client(api_key=get_api_key())
```

키가 유출되면 Google AI Studio에서 즉시 삭제하고 재발급해야 한다. 기존 키를 revoke해도 이미 유출된 키를 사용한 요청은 과금된다.

---

## 3. 인증: API Key vs OAuth

### 3.1 어떤 걸 써야 하나

| 상황 | 인증 방식 |
|------|----------|
| 로컬 개발, 프로토타입 | API Key |
| 프로덕션 서버 | 서비스 계정 + ADC |
| GKE/Cloud Run 위 | Workload Identity |
| CI/CD 파이프라인 | 서비스 계정 키 (Secret Manager 저장) |

### 3.2 서비스 계정 설정

```bash
# 서비스 계정 키 파일 경로 설정
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

```python
# ADC(Application Default Credentials) 사용
# 환경변수만 설정하면 SDK가 자동으로 인증 처리
client = genai.Client(
    vertexai=True,
    project="my-project-id",
    location="us-central1"
)
```

GKE 위에서 돌릴 때는 Workload Identity를 설정해서 키 파일 없이 인증하는 게 낫다. 키 파일은 로테이션 관리가 번거롭고, 컨테이너 이미지에 키 파일을 굽는 실수가 자주 발생한다.

---

## 4. 파일 업로드 API

### 4.1 File API 개요와 제한

File API는 PDF, 이미지, 오디오, 비디오를 업로드해두고 여러 요청에서 재사용하는 방식이다. 큰 파일을 매 요청마다 base64로 인코딩해서 보내면 요청 크기 제한에 걸리기 때문에 이 방식을 써야 한다.

주요 제한 사항:

- 업로드된 파일은 **48시간 후 자동 삭제**된다. 48시간 이후에도 사용해야 하면 재업로드해야 한다.
- 파일 하나의 최대 크기: 텍스트/이미지 50MB, 비디오 2GB
- 업로드 즉시 사용 가능한 게 아니라 `PROCESSING` 상태를 거쳐 `ACTIVE` 상태가 돼야 모델에 넘길 수 있다.
- 동시에 저장할 수 있는 파일 수 제한: 프로젝트당 20GB

### 4.2 업로드와 상태 확인

```python
from google import genai
from google.genai import types
import time

client = genai.Client(api_key="YOUR_API_KEY")

# 파일 업로드
uploaded = client.files.upload(
    file="api-spec.pdf",
    config=types.UploadFileConfig(
        mime_type="application/pdf",
        display_name="API 명세서",  # 나중에 파일 목록에서 식별할 때 씀
    )
)

print(f"파일 URI: {uploaded.uri}")
print(f"초기 상태: {uploaded.state}")  # PROCESSING
```

비디오나 큰 PDF는 업로드 후 처리에 수십 초가 걸린다. `PROCESSING` 상태인 파일을 그냥 모델에 넘기면 `400 INVALID_ARGUMENT`가 발생한다. 상태를 확인하고 `ACTIVE`가 된 뒤에 써야 한다.

```python
def wait_for_active(client, file_name: str, timeout: int = 300) -> types.File:
    """파일이 ACTIVE 상태가 될 때까지 폴링한다."""
    start = time.time()
    while True:
        f = client.files.get(name=file_name)
        if f.state == "ACTIVE":
            return f
        if f.state == "FAILED":
            raise RuntimeError(f"파일 처리 실패: {f.name}")
        if time.time() - start > timeout:
            raise TimeoutError(f"{timeout}초 안에 ACTIVE 상태가 되지 않았다: {f.name}")
        time.sleep(5)

active_file = wait_for_active(client, uploaded.name)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 API 명세에서 인증이 필요한 엔드포인트 목록을 뽑아줘"),
            types.Part.from_uri(
                file_uri=active_file.uri,
                mime_type=active_file.mime_type
            ),
        ])
    ]
)
```

### 4.3 파일 목록 조회와 삭제

```python
# 업로드된 파일 목록 확인
for f in client.files.list():
    print(f"{f.name}: {f.display_name} ({f.state}), {f.size_bytes} bytes")
    # files/abc123: API 명세서 (ACTIVE), 2457600 bytes

# 특정 파일 삭제
client.files.delete(name="files/abc123")

# 48시간 이전에 직접 정리하는 배치 예시
def cleanup_old_files(client, max_age_hours: int = 24):
    from datetime import datetime, timezone, timedelta
    threshold = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    for f in client.files.list():
        if f.create_time < threshold:
            client.files.delete(name=f.name)
            print(f"삭제: {f.name}")
```

### 4.4 한 요청에 여러 파일

File API로 업로드한 파일을 여러 개 한 요청에 넣을 수 있다.

```python
pdf_file = wait_for_active(client, uploaded_pdf.name)
img_file = wait_for_active(client, uploaded_img.name)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("PDF의 내용이 이 이미지와 일치하는지 확인해줘"),
            types.Part.from_uri(file_uri=pdf_file.uri, mime_type=pdf_file.mime_type),
            types.Part.from_uri(file_uri=img_file.uri, mime_type=img_file.mime_type),
        ])
    ]
)
```

---

## 5. 멀티모달 입력

### 5.1 이미지 처리

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

# 로컬 파일 — 20MB 미만이면 inline으로 보내도 된다
with open("architecture-diagram.webp", "rb") as f:
    image_data = f.read()

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 아키텍처 다이어그램에서 SPOF가 될 수 있는 부분을 찾아줘"),
            types.Part.from_bytes(data=image_data, mime_type="image/webp"),
        ])
    ]
)
```

```python
# URL로 직접 전달
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 에러 스크린샷을 분석해줘"),
            types.Part.from_uri(
                file_uri="https://example.com/error-screenshot.webp",
                mime_type="image/webp"
            ),
        ])
    ]
)
```

이미지를 큰 것 그대로 보내면 내부적으로 리사이즈된다. 에러 로그 스크린샷처럼 작은 글씨가 중요한 경우 해당 영역만 크롭해서 보내는 게 인식률이 높다.

### 5.2 PDF와 대용량 파일

20MB를 넘거나, 같은 파일을 여러 번 쓸 예정이면 File API로 업로드한다. 상태 확인 방법은 §4를 참고한다.

```python
uploaded_file = client.files.upload(
    file="api-spec.pdf",
    config=types.UploadFileConfig(mime_type="application/pdf")
)
active_file = wait_for_active(client, uploaded_file.name)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 API 명세에서 인증이 필요한 엔드포인트 목록을 뽑아줘"),
            types.Part.from_uri(
                file_uri=active_file.uri,
                mime_type=active_file.mime_type
            ),
        ])
    ]
)
```

---

## 6. Function Calling

외부 시스템과 연동할 때 쓴다. 모델이 직접 함수를 실행하는 게 아니라, "이 함수를 이 파라미터로 호출해야 한다"고 알려주면 개발자가 실행하고 결과를 다시 모델에 넘기는 구조다.

### 6.1 함수 정의

```python
from google.genai import types

get_weather_func = types.FunctionDeclaration(
    name="get_current_weather",
    description="지정한 도시의 현재 날씨를 조회한다",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING,
                description="도시명 (예: Seoul, Tokyo)"
            ),
            "unit": types.Schema(
                type=types.Type.STRING,
                enum=["celsius", "fahrenheit"],
                description="온도 단위"
            ),
        },
        required=["city"],
    ),
)

tools = types.Tool(function_declarations=[get_weather_func])
```

### 6.2 단일 함수 호출 흐름

```python
# 1단계: 모델에게 도구와 함께 질문
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="서울 날씨 어때?",
    config=types.GenerateContentConfig(tools=[tools])
)

# 2단계: 모델이 function call을 요청했는지 확인
part = response.candidates[0].content.parts[0]
if part.function_call:
    fc = part.function_call
    print(f"함수: {fc.name}, 인자: {fc.args}")
    # 출력: 함수: get_current_weather, 인자: {'city': 'Seoul'}

    # 3단계: 실제 함수 실행 (개발자가 구현)
    weather_result = {"temperature": 18, "condition": "맑음", "unit": "celsius"}

    # 4단계: 함수 결과를 모델에 전달
    function_response = types.Content(parts=[
        types.Part.from_function_response(
            name="get_current_weather",
            response=weather_result
        )
    ])

    final_response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[
            types.Content(parts=[types.Part.from_text("서울 날씨 어때?")]),
            response.candidates[0].content,  # 모델의 function call 응답
            function_response,               # 함수 실행 결과
        ],
        config=types.GenerateContentConfig(tools=[tools])
    )
    print(final_response.text)
```

### 6.3 병렬 함수 호출

모델이 한 번에 여러 함수를 호출하라고 응답하는 경우가 있다. "서울과 도쿄 날씨를 비교해줘"처럼 명확히 독립적인 두 데이터가 필요한 질문에서 자주 나온다. `parts` 배열에 `function_call`이 여러 개 들어온다.

```python
def dispatch_function_calls(parts) -> list[types.Part]:
    """모델이 요청한 function call을 전부 실행하고 결과 Part 목록을 반환한다."""
    result_parts = []
    for part in parts:
        if not part.function_call:
            continue
        fc = part.function_call
        # 함수 이름으로 실제 구현체를 찾아 실행
        handler = FUNCTION_REGISTRY.get(fc.name)
        if handler is None:
            raise ValueError(f"등록되지 않은 함수: {fc.name}")
        result = handler(**fc.args)
        result_parts.append(
            types.Part.from_function_response(name=fc.name, response=result)
        )
    return result_parts

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="서울이랑 도쿄 날씨 비교해줘",
    config=types.GenerateContentConfig(tools=[tools])
)

result_parts = dispatch_function_calls(response.candidates[0].content.parts)

final_response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[types.Part.from_text("서울이랑 도쿄 날씨 비교해줘")]),
        response.candidates[0].content,
        types.Content(parts=result_parts),
    ],
    config=types.GenerateContentConfig(tools=[tools])
)
```

주의사항:

- 함수 이름과 description을 명확하게 작성해야 한다. 모델이 함수를 호출할지 판단하는 기준이 이름과 description이다.
- 모델이 function call을 안 하고 텍스트로 직접 답변하는 경우도 있다. `function_call` 존재 여부를 항상 체크해야 한다.
- `tool_config`로 `mode="ANY"`를 설정하면 반드시 function call을 하도록 강제할 수 있다.

---

## 7. Structured Output (JSON 모드)

API 응답을 파싱해서 써야 하는 경우, JSON 형식으로 출력을 고정할 수 있다.

### 7.1 response_mime_type 지정

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Java, Python, Go의 주요 특징을 비교해줘",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
    )
)

import json
data = json.loads(response.text)
```

이렇게만 하면 JSON 형식은 보장되지만, 키 이름이나 구조는 모델 마음대로다. 일관된 구조가 필요하면 스키마를 지정해야 한다.

### 7.2 스키마 지정

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Java, Python, Go의 주요 특징을 비교해줘",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "language": types.Schema(type=types.Type.STRING),
                    "typing": types.Schema(type=types.Type.STRING),
                    "concurrency_model": types.Schema(type=types.Type.STRING),
                    "main_use_case": types.Schema(type=types.Type.STRING),
                },
                required=["language", "typing", "concurrency_model", "main_use_case"],
            ),
        ),
    )
)
```

스키마를 지정하면 응답이 항상 그 구조를 따른다. 스키마가 복잡해질수록 모델이 제약 조건을 맞추느라 답변 품질이 떨어지는 경우가 있다. 필수 필드는 최소한으로 잡는 게 좋다.

---

## 8. 스트리밍 응답

긴 응답을 받을 때 전체 생성이 끝날 때까지 기다리면 사용자 경험이 나쁘다. 스트리밍으로 청크 단위로 받으면 첫 토큰이 나오자마자 화면에 뿌릴 수 있다.

### 8.1 Python 동기 스트리밍

```python
response_stream = client.models.generate_content_stream(
    model="gemini-2.5-pro",
    contents="마이크로서비스 아키텍처에서 서비스 간 통신 방식의 장단점을 설명해줘"
)

full_text = ""
for chunk in response_stream:
    if chunk.text:
        print(chunk.text, end="", flush=True)
        full_text += chunk.text

# 마지막 청크에서 finish_reason 확인
last_chunk = chunk
if last_chunk.candidates[0].finish_reason == "MAX_TOKENS":
    print("\n[경고: 토큰 한도로 잘렸다]")
```

### 8.2 Python 비동기 스트리밍

웹 서버처럼 비동기 환경에서는 `aio` 네임스페이스를 쓴다.

```python
import asyncio
from google import genai
from google.genai import types

async def stream_response(client: genai.Client, prompt: str):
    full_text = ""
    async for chunk in await client.aio.models.generate_content_stream(
        model="gemini-2.5-pro",
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text
            full_text += chunk.text
    return full_text

# FastAPI SSE 예시
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/stream")
async def stream_endpoint(q: str):
    async def event_generator():
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        async for text in stream_response(client, q):
            # SSE 형식
            yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 8.3 Node.js 스트리밍

```typescript
const response = await ai.models.generateContentStream({
  model: "gemini-2.5-pro",
  contents: "질문 내용",
});

let fullText = "";
for await (const chunk of response) {
  if (chunk.text) {
    process.stdout.write(chunk.text);
    fullText += chunk.text;
  }
}
```

### 8.4 스트리밍 도중 오류 처리

스트리밍 중 네트워크가 끊기거나 서버 오류가 나면 `for` 루프가 예외를 던지며 중단된다. 부분 응답이 남는다.

```python
from google.api_core import exceptions

def stream_with_recovery(client, contents: str, max_retries: int = 3) -> str:
    full_text = ""
    for attempt in range(max_retries):
        try:
            for chunk in client.models.generate_content_stream(
                model="gemini-2.5-pro",
                contents=contents,
            ):
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_text += chunk.text
            return full_text  # 정상 종료
        except (exceptions.ServiceUnavailable, exceptions.InternalServerError) as e:
            if attempt == max_retries - 1:
                raise
            # 부분 응답이 있으면 이어받기를 시도한다
            if full_text:
                contents = [
                    contents,
                    f"[이전 응답이 중단됨: {full_text}]",
                    "이어서 계속 작성해줘",
                ]
                full_text = ""  # 이어받기 요청이므로 리셋
            wait = 2 ** attempt
            time.sleep(wait)
    return full_text
```

Function Calling과 스트리밍을 함께 쓸 때, function call 응답은 스트리밍 마지막에 한번에 온다. 중간 청크에서는 빈 텍스트만 올 수 있다.

---

## 9. 오류 코드

Gemini API는 gRPC 상태 코드를 HTTP 상태 코드로 매핑해서 반환한다. Python SDK에서는 `google.api_core.exceptions` 하위 예외 클래스로 변환된다.

### 9.1 오류 코드 목록

| HTTP | gRPC 상태 | 예외 클래스 | 주요 원인 |
|------|-----------|-------------|-----------|
| 400 | INVALID_ARGUMENT | `InvalidArgument` | 잘못된 파라미터, PROCESSING 상태 파일 참조, 지원 안 되는 MIME 타입 |
| 403 | PERMISSION_DENIED | `PermissionDenied` | API Key 무효, 빌링 미설정, Vertex AI 권한 없음 |
| 404 | NOT_FOUND | `NotFound` | 존재하지 않는 모델명, 만료된 File API 파일 |
| 429 | RESOURCE_EXHAUSTED | `ResourceExhausted` | RPM/TPM 한도 초과 |
| 500 | INTERNAL | `InternalServerError` | 서버 내부 오류 (일시적) |
| 503 | UNAVAILABLE | `ServiceUnavailable` | 서비스 과부하 (일시적) |
| 504 | DEADLINE_EXCEEDED | `DeadlineExceeded` | 요청 타임아웃 |

### 9.2 실제 오류 메시지 예시

`400 INVALID_ARGUMENT`는 원인이 다양하다. 오류 메시지를 읽어야 원인을 알 수 있다.

```
# 파일이 아직 PROCESSING 상태일 때
google.api_core.exceptions.InvalidArgument: 400 File is not in an ACTIVE state.
Please wait for the file to be processed before using it.

# 지원 안 되는 모델명
google.api_core.exceptions.NotFound: 404 models/gemini-99-ultra is not found

# 입력 토큰이 컨텍스트 한도 초과
google.api_core.exceptions.InvalidArgument: 400 Request too large. 
Total tokens in request: 2000100, max: 2000000

# 안전 필터에 걸린 경우 — 예외가 아니라 finish_reason으로 온다
response.candidates[0].finish_reason  # "SAFETY"
response.candidates[0].safety_ratings  # 어떤 카테고리에 걸렸는지
```

`403 PERMISSION_DENIED`는 두 가지 경우가 많다.

```
# API Key가 잘못됐거나 revoke된 경우
google.api_core.exceptions.PermissionDenied: 403 API key not valid.
Please pass a valid API key.

# Vertex AI에서 서비스 계정에 권한이 없는 경우
google.api_core.exceptions.PermissionDenied: 403 Caller does not have permission
'aiplatform.endpoints.predict' on resource 'projects/...'
```

### 9.3 finish_reason 처리

응답이 왔어도 정상 종료가 아닐 수 있다.

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="질문 내용"
)

candidate = response.candidates[0]
match candidate.finish_reason:
    case "STOP":
        # 정상 종료
        text = candidate.content.parts[0].text
    case "MAX_TOKENS":
        # 토큰 한도로 잘림. max_output_tokens 늘리거나 이어받기 요청
        text = candidate.content.parts[0].text + "...[잘림]"
    case "SAFETY":
        # 안전 필터 차단. safety_ratings로 어떤 카테고리인지 확인
        raise ValueError(f"안전 필터 차단: {candidate.safety_ratings}")
    case "RECITATION":
        # 저작권 관련 차단
        raise ValueError("저작권 관련 차단")
    case _:
        raise ValueError(f"예상치 못한 finish_reason: {candidate.finish_reason}")
```

---

## 10. 재시도 로직

### 10.1 재시도 대상 오류 구분

모든 오류에 재시도하면 안 된다. `400`이나 `403`은 재시도해도 달라지지 않는다.

- **재시도 대상**: `429`(rate limit), `500`(서버 오류), `503`(서비스 불가), `504`(타임아웃)
- **재시도 불가**: `400`(요청 자체가 잘못됨), `403`(권한 없음), `404`(존재하지 않음)

### 10.2 지수 백오프 구현

```python
import time
import random
from google.api_core import exceptions

RETRYABLE_EXCEPTIONS = (
    exceptions.ResourceExhausted,   # 429
    exceptions.ServiceUnavailable,  # 503
    exceptions.InternalServerError, # 500
    exceptions.DeadlineExceeded,    # 504
)

def call_with_retry(client, contents, model="gemini-2.5-pro", max_retries=5):
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents
            )
        except RETRYABLE_EXCEPTIONS as e:
            if attempt == max_retries - 1:
                raise
            # 지수 백오프 + 랜덤 지터
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"재시도 {attempt + 1}/{max_retries}: {type(e).__name__}, {wait:.1f}초 대기")
            time.sleep(wait)
        except (exceptions.InvalidArgument, exceptions.PermissionDenied, exceptions.NotFound):
            # 재시도해도 의미없는 오류는 바로 올린다
            raise
```

지수 백오프는 1초, 2초, 4초, 8초... 식으로 대기 시간을 늘린다. 랜덤 지터를 추가해서 여러 클라이언트가 동시에 재시도하는 thundering herd 문제를 피한다.

### 10.3 배치 요청에서 동시성 제한

배치 작업을 돌릴 때 한꺼번에 수백 건을 보내면 바로 rate limit에 걸린다. `asyncio.Semaphore`로 동시 요청 수를 제한해야 한다.

```python
import asyncio

semaphore = asyncio.Semaphore(5)  # 동시 최대 5개 요청

async def limited_call(client, contents):
    async with semaphore:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-pro",
            contents=contents
        )
        return response

async def process_batch(client, questions: list[str]):
    tasks = [limited_call(client, q) for q in questions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"질문 {i} 실패: {result}")
        else:
            print(f"질문 {i}: {result.text[:50]}...")
    return results
```

### 10.4 Quota 모니터링

GCP Console의 `API & Services > Quotas`에서 현재 사용량과 한도를 확인할 수 있다. 한도를 올리려면 quota 증가 요청을 해야 하는데, 승인까지 며칠 걸리는 경우가 있으니 미리 신청해두는 게 좋다.

429 응답 헤더에 `Retry-After`가 붙어오는 경우 그 값을 대기 시간으로 쓰는 게 지수 백오프보다 정확하다.

```python
import httpx

async def call_with_retry_header(client, contents, max_retries=5):
    for attempt in range(max_retries):
        try:
            return await client.aio.models.generate_content(
                model="gemini-2.5-pro",
                contents=contents
            )
        except exceptions.ResourceExhausted as e:
            if attempt == max_retries - 1:
                raise
            # gRPC 메타데이터에서 retry delay 확인
            retry_delay = None
            if hasattr(e, 'metadata'):
                for key, value in e.metadata:
                    if key == 'retry-delay':
                        retry_delay = float(value)
            wait = retry_delay if retry_delay else (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait)
```

---

## 11. 토큰 카운팅과 비용 계산

### 11.1 토큰 수 확인

요청을 보내기 전에 토큰 수를 미리 확인할 수 있다.

```python
count_response = client.models.count_tokens(
    model="gemini-2.5-pro",
    contents="카운트할 텍스트 내용"
)
print(f"토큰 수: {count_response.total_tokens}")
```

멀티모달 입력의 토큰 수도 같은 방식으로 확인한다. 이미지는 해상도에 따라 토큰 소비량이 크게 달라진다.

### 11.2 응답에서 사용량 확인

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="질문 내용"
)

usage = response.usage_metadata
print(f"입력 토큰: {usage.prompt_token_count}")
print(f"출력 토큰: {usage.candidates_token_count}")
print(f"총 토큰: {usage.total_token_count}")
```

### 11.3 비용을 줄이는 방법

Gemini API 가격은 모델과 토큰 수 기준이다. 공식 문서(https://ai.google.dev/pricing)에서 현재 가격을 확인한다.

- **모델 선택**: 간단한 분류나 추출 작업에 Gemini 2.5 Pro를 쓰면 낭비다. Gemini 2.5 Flash가 훨씬 싸고 이런 작업에는 충분하다.
- **출력 토큰 제한**: `max_output_tokens`를 설정해서 불필요하게 긴 응답을 막는다.
- **컨텍스트 캐싱**: 반복되는 긴 시스템 프롬프트나 문서가 있으면 `cached_content`로 캐싱해서 입력 토큰 비용을 줄일 수 있다. 캐시 생성 비용이 있으니, 같은 컨텍스트를 여러 번 재사용할 때만 이득이다.

```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="이 로그에서 ERROR 레벨만 추출해줘: ...",
    config=types.GenerateContentConfig(
        max_output_tokens=1000,
    )
)
```
