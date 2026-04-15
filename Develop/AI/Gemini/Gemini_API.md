---
title: Gemini API 실무 사용법
tags: [ai, gemini, google, api, multimodal, function-calling]
updated: 2026-04-15
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

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="질문 내용"
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

---

## 3. 인증: API Key vs OAuth

### 3.1 API Key

Google AI Studio(https://aistudio.google.com)에서 발급한다. 가장 간단하지만 권한 범위를 좁힐 수 없다. Key가 유출되면 해당 프로젝트의 Gemini API를 아무나 호출할 수 있다.

```python
# 환경변수로 관리
import os
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
```

API Key는 소스 코드에 하드코딩하면 안 된다. `.env` 파일에 넣고 `.gitignore`에 추가하는 건 기본이고, 프로덕션에서는 Secret Manager를 쓴다.

### 3.2 OAuth / 서비스 계정

프로덕션 환경에서는 서비스 계정(Service Account)을 쓴다.

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

### 3.3 어떤 걸 써야 하나

| 상황 | 인증 방식 |
|------|----------|
| 로컬 개발, 프로토타입 | API Key |
| 프로덕션 서버 | 서비스 계정 + ADC |
| GKE/Cloud Run 위 | Workload Identity |
| CI/CD 파이프라인 | 서비스 계정 키 (Secret Manager 저장) |

---

## 4. 멀티모달 입력

Gemini의 가장 큰 특징은 텍스트, 이미지, PDF, 오디오, 비디오를 하나의 요청에 섞어 보낼 수 있다는 것이다.

### 4.1 이미지 처리

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

# 로컬 파일
with open("architecture-diagram.png", "rb") as f:
    image_data = f.read()

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 아키텍처 다이어그램에서 SPOF가 될 수 있는 부분을 찾아줘"),
            types.Part.from_bytes(data=image_data, mime_type="image/png"),
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
                file_uri="https://example.com/error-screenshot.png",
                mime_type="image/png"
            ),
        ])
    ]
)
```

이미지 크기 제한은 모델 버전마다 다른데, 큰 이미지를 보내면 자동으로 리사이즈된다. 다만 리사이즈 과정에서 작은 글씨가 뭉개질 수 있어서, 에러 로그 스크린샷 같은 경우 해당 영역만 크롭해서 보내는 게 인식률이 높다.

### 4.2 PDF 처리

```python
# File API로 업로드 후 참조
uploaded_file = client.files.upload(
    file="api-spec.pdf",
    config=types.UploadFileConfig(mime_type="application/pdf")
)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 API 명세에서 인증이 필요한 엔드포인트 목록을 뽑아줘"),
            types.Part.from_uri(
                file_uri=uploaded_file.uri,
                mime_type=uploaded_file.mime_type
            ),
        ])
    ]
)
```

PDF는 페이지 수가 많으면 File API로 업로드하는 방식을 써야 한다. inline으로 base64 인코딩해서 보내면 요청 크기 제한에 걸린다. File API로 업로드한 파일은 48시간 후 자동 삭제된다.

### 4.3 오디오 처리

```python
uploaded_audio = client.files.upload(
    file="meeting-recording.mp3",
    config=types.UploadFileConfig(mime_type="audio/mp3")
)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 회의 녹음에서 결정된 사항을 정리해줘"),
            types.Part.from_uri(
                file_uri=uploaded_audio.uri,
                mime_type=uploaded_audio.mime_type
            ),
        ])
    ]
)
```

오디오 파일도 File API를 통해 업로드한다. MP3, WAV, FLAC 등을 지원하며, 최대 길이 제한이 있으니 긴 녹음은 분할해서 보내야 한다.

---

## 5. Function Calling

외부 시스템과 연동할 때 쓴다. 모델이 직접 함수를 실행하는 게 아니라, "이 함수를 이 파라미터로 호출해야 한다"고 알려주면 개발자가 실행하고 결과를 다시 모델에 넘기는 구조다.

### 5.1 함수 정의

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

### 5.2 호출 흐름

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

    # 이전 대화 내용 + 함수 결과를 함께 전달
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

주의사항:

- 함수 이름과 설명을 명확하게 작성해야 한다. 모델이 함수를 호출할지 판단하는 기준이 이름과 description이다.
- 한 번의 요청에서 여러 함수를 동시에 호출하라고 응답할 수 있다. `parts` 배열에 `function_call`이 여러 개 들어오는 경우를 처리해야 한다.
- 모델이 function call을 안 하고 텍스트로 직접 답변하는 경우도 있다. `function_call` 존재 여부를 항상 체크해야 한다.

---

## 6. Structured Output (JSON 모드)

API 응답을 파싱해서 써야 하는 경우, JSON 형식으로 출력을 고정할 수 있다.

### 6.1 response_mime_type 지정

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

### 6.2 스키마 지정

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

스키마를 지정하면 응답이 항상 그 구조를 따른다. 다만 스키마가 복잡해질수록 모델이 제약 조건을 맞추느라 답변 품질이 떨어지는 경우가 있다. 필수 필드는 최소한으로 잡는 게 좋다.

---

## 7. 스트리밍 응답

긴 응답을 받을 때 전체 생성이 끝날 때까지 기다리면 사용자 경험이 나쁘다. 스트리밍으로 청크 단위로 받으면 첫 토큰이 나오자마자 화면에 뿌릴 수 있다.

### 7.1 Python 스트리밍

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
```

### 7.2 Node.js 스트리밍

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

### 7.3 스트리밍에서 주의할 점

- 스트리밍 중 네트워크가 끊기면 부분 응답만 남는다. 청크를 모아서 전체 응답을 조립하는 로직과, 중간에 끊겼을 때 재시도 로직이 필요하다.
- Function Calling과 스트리밍을 함께 쓸 때, function call 응답은 스트리밍 마지막에 한번에 온다. 중간 청크에서는 빈 텍스트만 올 수 있다.
- `finish_reason`이 `STOP`이면 정상 종료, `MAX_TOKENS`면 토큰 한도에 걸린 것이다. 잘린 응답을 이어받으려면 이전 응답을 context에 넣고 이어서 생성하라고 요청해야 한다.

---

## 8. 토큰 카운팅과 비용 계산

### 8.1 토큰 수 확인

요청을 보내기 전에 토큰 수를 미리 확인할 수 있다.

```python
count_response = client.models.count_tokens(
    model="gemini-2.5-pro",
    contents="카운트할 텍스트 내용"
)
print(f"토큰 수: {count_response.total_tokens}")
```

멀티모달 입력의 토큰 수도 같은 방식으로 확인한다. 이미지는 해상도에 따라 토큰 소비량이 크게 달라진다.

### 8.2 응답에서 사용량 확인

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

### 8.3 비용 계산

Gemini API 가격은 모델과 토큰 수 기준이다. 가격은 수시로 바뀌니 공식 문서(https://ai.google.dev/pricing)를 확인해야 한다.

비용을 줄이는 방법:

- **컨텍스트 캐싱**: 반복되는 긴 시스템 프롬프트나 문서가 있으면 `cached_content`로 캐싱해서 입력 토큰 비용을 줄일 수 있다. 캐시 생성 비용이 있으니, 같은 컨텍스트를 여러 번 재사용할 때만 이득이다.
- **모델 선택**: 간단한 분류나 추출 작업에 Gemini 2.5 Pro를 쓰면 낭비다. Gemini 2.5 Flash가 훨씬 싸고 이런 작업에는 충분하다.
- **출력 토큰 제한**: `max_output_tokens`를 설정해서 불필요하게 긴 응답을 막는다.

```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="이 로그에서 ERROR 레벨만 추출해줘: ...",
    config=types.GenerateContentConfig(
        max_output_tokens=1000,
    )
)
```

---

## 9. Rate Limit 대응과 재시도 로직

### 9.1 Rate Limit 종류

Gemini API는 RPM(분당 요청 수)과 TPM(분당 토큰 수) 두 가지 제한이 있다. 무료 티어와 유료 티어에서 한도가 다르고, 모델별로도 다르다. `429 Too Many Requests` 응답이 오면 한도에 걸린 것이다.

### 9.2 재시도 구현

```python
import time
import random
from google.api_core import exceptions

def call_with_retry(client, contents, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=contents
            )
            return response
        except exceptions.ResourceExhausted as e:
            # 429 에러: rate limit
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limit 도달. {wait_time:.1f}초 후 재시도 ({attempt + 1}/{max_retries})")
            time.sleep(wait_time)
        except exceptions.ServiceUnavailable:
            # 503 에러: 서버 일시 장애
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
```

핵심은 **지수 백오프(exponential backoff)**다. 1초, 2초, 4초, 8초... 식으로 대기 시간을 늘리면서 재시도한다. 여기에 랜덤 지터(jitter)를 추가해서 여러 클라이언트가 동시에 재시도하는 thundering herd 문제를 피한다.

### 9.3 실무에서 자주 겪는 문제

**요청이 몰리는 시간대**: 배치 작업을 돌릴 때 한꺼번에 수백 건을 보내면 바로 rate limit에 걸린다. `asyncio.Semaphore`나 토큰 버킷 같은 방식으로 동시 요청 수를 제한해야 한다.

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

# 여러 요청을 동시에 실행하되 최대 5개로 제한
tasks = [limited_call(client, q) for q in questions]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**quota 모니터링**: GCP Console의 API & Services > Quotas 페이지에서 현재 사용량과 한도를 확인할 수 있다. 한도를 올리려면 quota 증가 요청을 해야 하는데, 승인까지 며칠 걸리는 경우가 있으니 미리 신청해두는 게 좋다.

**에러 응답 구분**: `429`만 재시도하면 안 된다. `500`(내부 서버 오류)이나 `503`(서비스 불가)도 일시적인 문제일 수 있어서 재시도 대상에 포함해야 한다. 반면 `400`(잘못된 요청)이나 `403`(권한 없음)은 재시도해도 소용없다.
