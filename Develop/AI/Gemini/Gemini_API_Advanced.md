---
title: Gemini API 심화 (멀티모달, Function Calling, Streaming, Safety, Context Caching)
tags: [ai, gemini, google, api, multimodal, function-calling, streaming, safety, caching]
updated: 2026-04-18
---

# Gemini API 심화

Gemini_API.md에서 다룬 기초 SDK 사용법 위에 쌓이는 내용을 정리한다. 인증, 기본 호출, 간단한 멀티모달 입력은 기초 문서를 참고하고, 여기서는 실제 운영에서 마주치는 디테일 위주로 다룬다.

---

## 1. 멀티모달 심화

### 1.1 비디오 프레임 샘플링 제어

Gemini는 비디오를 내부적으로 프레임 단위로 잘라서 이미지 토큰으로 변환한다. 기본값은 1fps로 샘플링하고, 초당 오디오도 함께 처리한다. 60분짜리 영상이면 3600프레임 + 오디오 토큰이 그대로 쌓여서 토큰이 순식간에 100만을 넘는다.

실무에서는 `fps`와 `offset`으로 샘플링을 직접 조절해야 한다.

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

uploaded = client.files.upload(
    file="interview.mp4",
    config=types.UploadFileConfig(mime_type="video/mp4")
)

# ACTIVE 상태가 될 때까지 대기 (섹션 1.4 참고)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("이 인터뷰 영상에서 화자가 바뀌는 지점을 타임스탬프로 알려줘"),
            types.Part(
                file_data=types.FileData(
                    file_uri=uploaded.uri,
                    mime_type=uploaded.mime_type,
                ),
                video_metadata=types.VideoMetadata(
                    fps=0.5,              # 2초당 1프레임
                    start_offset="30s",   # 30초부터
                    end_offset="5m30s",   # 5분 30초까지
                ),
            ),
        ])
    ]
)
```

`fps=0.5`로 내려도 인터뷰나 강연처럼 프레임 변화가 적은 영상은 내용 이해에 지장이 없다. 반대로 스포츠 중계나 액션 장면이 필요한 영상에서는 1fps가 기본인 이유가 있다. 2fps 이상은 토큰 효율이 급격히 떨어지니 정말 필요한 구간만 `start_offset`/`end_offset`으로 자르고 fps를 올리는 게 낫다.

비디오 토큰 계산은 `(fps × 초) × 프레임당 약 258토큰 + 오디오 토큰`이다. 1fps로 10분짜리 영상이면 600 × 258 ≈ 154,800토큰이 이미지 쪽에만 들어간다. 입력 토큰 한도를 다 쓰는 상황이라 사전에 `count_tokens`로 확인하는 습관이 필요하다.

### 1.2 여러 이미지 비교

하나의 요청에 이미지 여러 개를 섞으면 모델이 순서대로 인식한다. 비교·차이 분석에는 프롬프트에 이미지 순번을 명시적으로 넣어야 한다.

```python
def read_image(path, mime):
    with open(path, "rb") as f:
        return types.Part.from_bytes(data=f.read(), mime_type=mime)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text(
                "세 장의 로그인 UI 스크린샷이다. "
                "1번은 v1.0, 2번은 v1.1, 3번은 v1.2 디자인이다. "
                "버전 간 시각적 변경점을 순서대로 정리해줘."
            ),
            read_image("login_v1.png", "image/png"),
            read_image("login_v1_1.png", "image/png"),
            read_image("login_v1_2.png", "image/png"),
        ])
    ]
)
```

이미지 순서를 텍스트로 명시하지 않으면 모델이 "첫 번째", "두 번째"라고만 응답하거나, 순서가 뒤섞인 답을 내놓는 경우가 꽤 있다. 8~10장을 넘어가면 각 이미지의 세부 사항을 놓치기 시작한다. 페어(pair) 비교를 여러 번 돌리는 게 정확도가 높을 때도 있다.

이미지 해상도가 섞여 있을 때 주의할 점 하나 더 있다. Gemini는 768px보다 큰 이미지를 내부적으로 타일로 쪼개서 각 타일을 별개 이미지처럼 처리한다. 4K 스크린샷 한 장이 FullHD 한 장보다 4배 가까운 토큰을 먹는다. 고해상도가 꼭 필요한 경우가 아니라면 업로드 전에 1280px 정도로 리사이즈하는 게 낫다.

### 1.3 이미지 + PDF 혼합 컨텍스트 토큰 계산

기획서 PDF와 화면 스크린샷 여러 장을 함께 보내서 "이 기획서대로 구현됐는지 확인해줘" 같은 요청을 자주 하게 된다. 이때 토큰이 예상을 벗어나는 원인이 대체로 PDF 쪽이다.

PDF는 페이지당 텍스트 토큰(OCR 결과) + 페이지 이미지 토큰 두 가지로 계산된다. 텍스트 위주의 기술 문서는 페이지당 200~600토큰 수준이지만, 도표와 이미지가 많은 기획서는 1,500~2,500토큰까지 올라간다.

```python
# 토큰 구성 요소 분리 확인
total = client.models.count_tokens(
    model="gemini-2.5-pro",
    contents=[
        types.Content(parts=[
            types.Part.from_text("확인해달라는 프롬프트"),
            types.Part.from_uri(file_uri=pdf.uri, mime_type="application/pdf"),
            read_image("screen1.png", "image/png"),
            read_image("screen2.png", "image/png"),
        ])
    ]
)

# 구성 요소별로 호출해서 분해
text_only = client.models.count_tokens(
    model="gemini-2.5-pro",
    contents="확인해달라는 프롬프트"
)
pdf_only = client.models.count_tokens(
    model="gemini-2.5-pro",
    contents=[types.Content(parts=[
        types.Part.from_uri(file_uri=pdf.uri, mime_type="application/pdf"),
    ])]
)
# total - text_only - pdf_only ≈ 이미지 2장 토큰
```

혼합 컨텍스트를 캐싱할 때도 이 분해가 유용하다. PDF만 공통 캐시로 올리고 스크린샷은 요청마다 바꿔 보내는 식으로 비용을 아낄 수 있다(섹션 5 참고).

### 1.4 File API 업로드 상태 폴링

File API에 업로드한 파일은 바로 쓸 수 있는 게 아니다. `state`가 `PROCESSING`에서 `ACTIVE`로 바뀌어야 `generate_content`에 참조할 수 있다. 비디오/오디오는 길이에 따라 수 초~수 분이 걸린다. `ACTIVE` 확인 없이 바로 호출하면 `FAILED_PRECONDITION` 에러가 난다.

```python
import time

def upload_and_wait(client, path, mime, timeout=300, poll_interval=2):
    uploaded = client.files.upload(
        file=path,
        config=types.UploadFileConfig(mime_type=mime)
    )

    deadline = time.monotonic() + timeout
    while uploaded.state.name == "PROCESSING":
        if time.monotonic() > deadline:
            raise TimeoutError(f"업로드 처리 시간 초과: {uploaded.name}")
        time.sleep(poll_interval)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name == "FAILED":
        raise RuntimeError(f"업로드 실패: {uploaded.name}")

    return uploaded
```

여기서 `poll_interval`을 너무 짧게 주면(500ms 같은) 파일 API의 RPM에 걸리는 경우가 있다. 2~3초 정도가 무난하다. 비디오는 보통 파일 크기 MB당 0.5~1초쯤 잡으면 되고, 30분 넘는 영상은 `timeout`을 600초 이상으로 늘리는 게 안전하다.

파일이 48시간 후 자동 삭제되는 특성 때문에, 장기 실행 배치에서는 실행 중 파일이 만료되는 경우도 생긴다. 배치 시작 시점에 일괄 업로드하고 실행 시간이 48시간에 근접하면 중간에 재업로드하는 로직이 필요하다.

---

## 2. Function Calling 심화

### 2.1 Parallel Function Calling

한 번의 응답에 `function_call` 파트가 여러 개 나올 수 있다. "서울 날씨랑 뉴욕 날씨 비교해줘" 같은 요청에서 모델은 `get_current_weather(city="Seoul")`과 `get_current_weather(city="New York")`을 동시에 호출하려고 한다.

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="서울, 뉴욕, 도쿄 날씨 비교해줘",
    config=types.GenerateContentConfig(tools=[weather_tool]),
)

calls = [p.function_call for p in response.candidates[0].content.parts
         if p.function_call]

# 병렬 실행
import asyncio

async def run_all(calls):
    tasks = [execute_function(c.name, c.args) for c in calls]
    return await asyncio.gather(*tasks)

results = asyncio.run(run_all(calls))

# 결과를 순서대로 다시 모델에 전달
function_parts = [
    types.Part.from_function_response(name=call.name, response=result)
    for call, result in zip(calls, results)
]
```

함수 호출 순서는 응답에 나온 파트 순서와 동일하게 맞춰서 돌려줘야 한다. 순서가 꼬이면 모델이 엉뚱한 결과를 엉뚱한 함수 호출에 매핑한다. 병렬 호출이라도 응답 배열 순서는 보존해야 한다.

모든 질문이 병렬화되는 건 아니다. 결과가 서로 의존하면 모델은 순차적으로 나눠서 호출한다. "주문번호 12345의 배송지 도시의 날씨" 같은 질문이 그 예다.

### 2.2 Compositional Function Calling (함수 체이닝)

위 예시처럼 한 함수의 결과를 다음 함수의 입력으로 쓰는 패턴이다. 모델이 알아서 여러 턴에 걸쳐 호출을 이어간다.

```python
get_order = types.FunctionDeclaration(
    name="get_order",
    description="주문번호로 주문 정보를 조회한다. 배송지 도시가 포함된다.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={"order_id": types.Schema(type=types.Type.STRING)},
        required=["order_id"],
    ),
)

get_weather = types.FunctionDeclaration(
    name="get_weather",
    description="도시명으로 현재 날씨를 조회한다.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={"city": types.Schema(type=types.Type.STRING)},
        required=["city"],
    ),
)

tools = types.Tool(function_declarations=[get_order, get_weather])

# 대화를 유지하면서 반복 호출
history = [types.Content(role="user", parts=[
    types.Part.from_text("주문 A-12345의 배송지 날씨가 어때?")
])]

while True:
    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=history,
        config=types.GenerateContentConfig(tools=[tools]),
    )
    parts = resp.candidates[0].content.parts
    calls = [p.function_call for p in parts if p.function_call]

    if not calls:
        print(resp.text)
        break

    history.append(resp.candidates[0].content)

    func_resp_parts = []
    for c in calls:
        result = execute_function(c.name, dict(c.args))
        func_resp_parts.append(
            types.Part.from_function_response(name=c.name, response=result)
        )
    history.append(types.Content(role="user", parts=func_resp_parts))
```

루프 종료 조건을 걸 때 `function_call`이 없으면 종료한다는 게 기본이지만, 프로덕션에서는 최대 반복 횟수(예: 10회)도 함께 걸어야 한다. 모델이 어떤 이유로 같은 함수를 무한 반복 호출하는 경우가 있고, 그 상태가 되면 토큰을 계속 먹으면서 응답이 안 나온다.

### 2.3 Automatic Function Calling (AFC) vs 수동 모드

Python SDK에는 AFC라는 편의 기능이 있다. 함수 선언 대신 실제 파이썬 함수를 그대로 넘기면 SDK가 스키마를 자동 추출하고, 모델이 호출을 요청하면 SDK가 알아서 실행해서 다시 모델에 넘기고, 최종 텍스트만 돌려준다.

```python
def get_weather(city: str, unit: str = "celsius") -> dict:
    """도시의 현재 날씨를 반환한다.

    Args:
        city: 도시명
        unit: celsius 또는 fahrenheit
    """
    return {"temp": 18, "condition": "맑음", "unit": unit}

# AFC: 함수 객체를 그대로 tools에 전달
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="서울 날씨 어때?",
    config=types.GenerateContentConfig(tools=[get_weather]),
)
print(response.text)  # 이미 함수 실행 결과를 반영한 최종 답변
```

AFC는 프로토타입에 편한데, 운영 환경에서는 안 쓰는 걸 추천한다. 이유가 몇 가지 있다.

첫째, 함수 실행이 SDK 내부에서 일어나서 실행 전 파라미터 검증이나 권한 체크 훅을 끼우기 어렵다. 둘째, 모델이 의도치 않은 함수를 호출해도 바로 실행되니까 민감한 작업(DB 쓰기, 결제 등)에 쓰면 위험하다. 셋째, 디버깅이 어렵다. 중간 턴에서 어떤 함수가 어떤 인자로 호출됐는지 로그를 남기려면 결국 콜백을 걸어야 하는데, 그럴 거면 수동 모드가 더 명확하다.

AFC를 끄려면 `AutomaticFunctionCallingConfig(disable=True)`로 명시할 수 있다.

```python
config=types.GenerateContentConfig(
    tools=[get_weather],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(
        disable=True
    ),
)
```

이렇게 두면 `FunctionDeclaration`으로 변환된 스키마만 쓰고, 실행은 개발자가 책임진다.

### 2.4 tool_config: 함수 호출 강제/차단

`tool_config`로 모델의 함수 호출 동작을 모드 단위로 제어할 수 있다. 모드는 세 가지다.

| 모드 | 동작 |
|------|------|
| `AUTO` | 기본값. 모델이 상황에 따라 함수 호출 여부를 판단한다. |
| `ANY` | 반드시 함수 중 하나를 호출한다. 텍스트 답변을 내놓지 않는다. |
| `NONE` | 함수를 절대 호출하지 않는다. 텍스트만 답변한다. |

```python
# ANY: 무조건 함수 중 하나를 호출
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="서울 날씨 알려줘",
    config=types.GenerateContentConfig(
        tools=[weather_tool],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.ANY,
                allowed_function_names=["get_current_weather"],
            )
        ),
    ),
)
```

`ANY` 모드는 구조화된 API 응답이 꼭 필요한 라우팅 레이어에서 유용하다. 사용자의 자연어 요청을 반드시 내부 API 호출로 매핑해야 하는 챗봇이나, 작업 분류기 같은 용도다. `allowed_function_names`로 특정 함수만 선택지로 제한할 수도 있다.

`NONE`은 도구를 정의해둔 채로 특정 턴에만 호출을 막고 싶을 때 쓴다. 예를 들어 사용자가 "방금 뭘 조회했는지 설명해줘"라고 하면 또 조회하지 말고 대화 기록만으로 답해야 한다. 이런 턴에서는 `NONE`으로 전환한다.

### 2.5 Function Calling + Streaming 조합

스트리밍과 Function Calling을 같이 쓰면 골치 아픈 지점이 하나 있다. `function_call` 파트는 스트리밍 중간 청크에서 오지 않고, 거의 마지막 청크에 한 번에 실린다. 텍스트 청크처럼 부분적으로 쌓이는 구조가 아니다.

```python
stream = client.models.generate_content_stream(
    model="gemini-2.5-pro",
    contents="서울 날씨 알려줘",
    config=types.GenerateContentConfig(tools=[weather_tool]),
)

function_calls = []
text_buffer = ""

for chunk in stream:
    if not chunk.candidates:
        continue
    for part in chunk.candidates[0].content.parts:
        if part.text:
            text_buffer += part.text
            print(part.text, end="", flush=True)
        elif part.function_call:
            function_calls.append(part.function_call)

# 스트림이 다 끝난 뒤에 함수 호출 처리
if function_calls:
    # 수집한 function_call들을 실행하고 다시 모델에 전달
    ...
```

UI에서 "답변 생성 중..." 인디케이터를 돌리다가, 스트림이 끝났는데 `text_buffer`가 비어 있고 `function_calls`만 있으면 "도구를 사용하는 중..."으로 인디케이터를 바꿔야 한다. 사용자 경험상 이 전환을 놓치면 응답이 느리게 느껴진다.

함수 실행이 끝난 뒤 다시 모델에 결과를 넘기는 호출도 스트리밍으로 하면, 이번에는 텍스트만 청크로 나온다. 클라이언트 측에서는 여러 단계의 스트림을 이어 붙이는 상태 머신이 필요하다.

---

## 3. Streaming 심화

### 3.1 SSE 프로토콜 구조

Gemini의 스트리밍은 Server-Sent Events(SSE)로 내려온다. `alt=sse` 쿼리 파라미터가 붙은 엔드포인트를 호출하면 다음 형식으로 응답이 오며, SDK는 이걸 파싱해서 `chunk` 객체로 변환한다.

```
data: {"candidates":[{"content":{"parts":[{"text":"안녕"}],"role":"model"},"index":0}]}

data: {"candidates":[{"content":{"parts":[{"text":"하세요"}],"role":"model"},"index":0}]}

data: {"candidates":[{"content":{"parts":[{"text":"."}],"role":"model"},"finishReason":"STOP","index":0}],"usageMetadata":{"promptTokenCount":8,"candidatesTokenCount":3,"totalTokenCount":11}}
```

각 `data:` 라인이 하나의 chunk다. 빈 줄로 구분된다. HTTP 프록시나 로드밸런서가 응답을 버퍼링하면 청크가 묶여서 늦게 도착하는 일이 생긴다. AWS ALB 같은 경우 기본값이 짧아서 문제가 적지만, Nginx 앞에 두면 `proxy_buffering off`를 걸어야 스트리밍이 실시간으로 흐른다.

### 3.2 청크 누락과 재조립

네트워크가 중간에 끊기면 스트림은 에러로 끝난다. 이때까지 받은 텍스트는 "부분 응답"으로 남는데, 이걸 그대로 사용자에게 보여주고 재시도 버튼을 띄우거나, 받은 부분까지 context에 넣고 "이어서 생성" 요청을 하는 두 가지 방식이 있다.

```python
def stream_with_reassembly(client, contents, max_retries=2):
    full_text = ""
    attempt = 0

    while attempt <= max_retries:
        try:
            # 재시도일 때는 이전까지 받은 텍스트를 assistant 턴으로 끼워넣는다
            turns = list(contents)
            if full_text:
                turns.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(full_text)]
                ))
                turns.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text("방금 잘린 부분부터 이어서 계속해줘.")]
                ))

            stream = client.models.generate_content_stream(
                model="gemini-2.5-pro",
                contents=turns,
            )
            for chunk in stream:
                if chunk.text:
                    full_text += chunk.text
                    yield chunk.text
            return  # 정상 종료
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                raise
```

"이어서 생성" 방식의 약점은 이음새가 어색하게 나올 수 있다는 점이다. 문장 중간에 끊겼다가 "계속해줘"라고 요청하면 새 문장으로 시작하거나 같은 문장을 반복하는 경우가 있다. 실제 운영에서는 일정 길이 이상일 때만 이어 붙이기를 시도하고, 짧으면 전체 재요청하는 식으로 분기한다.

`finish_reason`도 확인 대상이다. `STOP`은 정상, `MAX_TOKENS`는 토큰 한도 도달, `SAFETY`는 안전 필터에 걸림, `RECITATION`은 학습 데이터 일부를 그대로 출력하려던 게 차단된 경우다. 각각 대응이 다르다.

### 3.3 usage_metadata는 마지막 청크에만

토큰 사용량을 스트리밍에서 얻으려면 마지막 청크까지 다 받아야 한다. 중간 청크의 `usage_metadata`는 없거나 부분값이다.

```python
last_usage = None
for chunk in stream:
    if chunk.text:
        yield chunk.text
    if chunk.usage_metadata:
        last_usage = chunk.usage_metadata

# 스트림 끝난 뒤 사용량 로깅
if last_usage:
    log.info(
        "tokens prompt=%d output=%d total=%d",
        last_usage.prompt_token_count,
        last_usage.candidates_token_count,
        last_usage.total_token_count,
    )
```

사용량 기록이 중요한 SaaS에서는 스트림이 비정상 종료된 경우에도 근사치를 찍어야 한다. 받은 텍스트 길이로 출력 토큰을 추정하거나, 재시도 시 누적된 청구 로직을 다시 확인해야 한다. 가장 확실한 방법은 스트림이 끝난 후 응답 전체 텍스트와 원본 요청으로 `count_tokens`를 한 번 더 호출하는 것이다.

### 3.4 AsyncIterator 취소 처리

비동기 스트리밍 중 사용자가 "중단" 버튼을 눌렀을 때, 연결을 제대로 끊지 않으면 모델은 계속 생성을 진행하고 토큰이 과금된다. 서버가 연결을 닫으면 Gemini가 생성을 중단한다.

```python
import asyncio

async def stream_and_relay(client, contents, ws):
    try:
        stream = await client.aio.models.generate_content_stream(
            model="gemini-2.5-pro",
            contents=contents,
        )
        async for chunk in stream:
            if chunk.text:
                await ws.send_text(chunk.text)
    except asyncio.CancelledError:
        # 클라이언트가 연결을 끊음: 스트림 컨텍스트가 닫히면서 HTTP 연결도 닫힌다
        raise
    finally:
        # aclose로 명시적으로 정리
        await stream.aclose()
```

FastAPI에서 WebSocket을 쓸 때, 클라이언트가 나가면 `WebSocketDisconnect`가 뜨는데 이걸 잡아서 취소하지 않으면 백그라운드에서 스트림이 계속 돈다. `asyncio.Task`로 스트리밍을 돌리고 `task.cancel()`을 호출하는 패턴이 깔끔하다.

주의: 일부 LB나 프록시는 연결 종료를 모델 서버까지 전달하지 않는 경우가 있다. 이럴 땐 과금이 끝까지 난다. 큰 응답을 생성 중이라면 `max_output_tokens`로 상한을 두는 게 방어책이 된다.

---

## 4. Safety Settings

### 4.1 HARM_CATEGORY 4종과 임계값

Gemini는 응답을 생성한 뒤 네 가지 카테고리로 유해성을 분류하고, 임계값을 넘으면 응답을 차단한다.

| 카테고리 | 대상 |
|----------|------|
| `HARM_CATEGORY_HARASSMENT` | 개인 대상 괴롭힘, 비하 |
| `HARM_CATEGORY_HATE_SPEECH` | 특정 집단 대상 혐오 발언 |
| `HARM_CATEGORY_SEXUALLY_EXPLICIT` | 성적으로 노골적인 콘텐츠 |
| `HARM_CATEGORY_DANGEROUS_CONTENT` | 폭력, 자해, 무기 제조 등 |

임계값은 네 단계다. 엄격한 순서대로 `BLOCK_LOW_AND_ABOVE` → `BLOCK_MEDIUM_AND_ABOVE` → `BLOCK_ONLY_HIGH` → `BLOCK_NONE`이다. 모델이 내부적으로 콘텐츠를 NEGLIGIBLE/LOW/MEDIUM/HIGH 4단계로 평가하고, 설정한 임계값을 넘으면 차단한다.

```python
from google.genai import types

safety = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="보안 취약점 분석 요청 내용",
    config=types.GenerateContentConfig(safety_settings=safety),
)
```

### 4.2 차단된 응답 처리

차단은 두 단계에서 일어난다. 하나는 입력 프롬프트 자체가 막히는 경우, 다른 하나는 모델이 생성한 출력이 막히는 경우다.

```python
# 프롬프트 차단: prompt_feedback.block_reason이 설정됨
if response.prompt_feedback and response.prompt_feedback.block_reason:
    reason = response.prompt_feedback.block_reason
    ratings = response.prompt_feedback.safety_ratings
    # 사용자에게 "요청이 안전 정책에 의해 차단됐습니다"로 응답

# 출력 차단: candidate.finish_reason == "SAFETY"
for cand in response.candidates:
    if cand.finish_reason.name == "SAFETY":
        # 어느 카테고리에서 걸렸는지 확인
        for rating in cand.safety_ratings:
            if rating.blocked:
                print(f"차단 카테고리: {rating.category}, 확률: {rating.probability}")
```

출력 차단은 스트리밍 도중에도 발생한다. 앞부분까지는 내려오다가 갑자기 스트림이 끝나면서 마지막 청크의 `finish_reason`이 `SAFETY`가 된다. 이미 사용자 화면에 일부 내용이 표시된 상태라 UX가 어색해진다. 스트리밍에서 이게 문제라면 일부 카테고리의 임계값을 느슨하게 잡고, 최종 결과를 별도 후처리 필터로 한 번 더 검사하는 식으로 우회한다.

### 4.3 False Positive 줄이기

기본 설정(대부분 `BLOCK_MEDIUM_AND_ABOVE`)은 기술 질문에도 자주 걸린다. 특히 다음 유형이 많다.

- 보안 취약점 분석, 침투 테스트 질문 → `DANGEROUS_CONTENT`에 걸림
- 의학·자해 관련 정책 문서 요약 → `DANGEROUS_CONTENT` 또는 `HARASSMENT`
- 역사적 갈등, 정치 이슈 분석 → `HATE_SPEECH`
- 성인용 콘텐츠 필터링 로직을 만들 때 테스트 케이스 생성 → `SEXUALLY_EXPLICIT`

프로덕션 B2B 도구(코드 리뷰, 보안 분석 등)에서는 대체로 네 카테고리 모두 `BLOCK_ONLY_HIGH`로 낮춰두고, 전체를 `BLOCK_NONE`으로 열지는 않는다. 사용자 대면 챗봇은 `BLOCK_MEDIUM_AND_ABOVE` 유지하는 게 안전하다. 서비스 성격에 따라 카테고리별로 다르게 잡는다.

Vertex AI에는 `HARM_CATEGORY_CIVIC_INTEGRITY`(시민 통합성: 선거·투표 관련) 카테고리가 추가로 있다. 선거 정보를 다루는 서비스면 이것도 고려 대상이다.

전체를 `BLOCK_NONE`으로 설정하는 옵션도 있지만, 일부 모델 버전에서는 이 설정 자체가 허용되지 않거나 승인된 계정에만 열린다. 무분별하게 풀면 서비스 신뢰도 문제가 되고, 유료 고객이 악의적 입력을 시도할 때 방어선이 없어진다.

### 4.4 민감 주제 대응 패턴

사용자 입력을 그대로 모델에 넣기 전에 1차 필터를 거치는 방식이 실전에서 자주 쓰인다.

```python
def preflight_check(text):
    # Perspective API 같은 사전 필터로 명백한 어뷰즈 걸러내기
    toxicity = check_toxicity(text)
    if toxicity > 0.9:
        return "rejected", "명백한 어뷰즈 입력"
    if toxicity > 0.6:
        return "review", "검토 필요"
    return "ok", None

status, reason = preflight_check(user_input)
if status == "rejected":
    return "요청을 처리할 수 없습니다."

# 나머지는 Gemini에 보내고, 안전 설정으로 2차 필터
```

이중 필터는 false positive가 누적되는 문제가 있지만, 신뢰성 기준이 높은 서비스에서는 피하기 어렵다. 로그에 차단 이유를 꼭 남겨두고, 사용자 이의제기를 받는 루트를 만드는 게 운영상 중요하다.

---

## 5. Context Caching 심화

### 5.1 최소 토큰과 사용 판단

Context Caching은 반복되는 긴 컨텍스트(시스템 프롬프트, 참조 문서, tool 선언 등)를 미리 캐시에 올려두고, 요청 시 캐시 ID만 참조하는 기능이다. 캐시된 부분은 입력 토큰 단가가 크게 낮아진다.

2025년 말 기준 최소 토큰은 모델별로 정해져 있다.

| 모델 | 최소 캐시 토큰 |
|------|---------------|
| Gemini 2.5 Pro | 4,096 |
| Gemini 2.5 Flash | 1,024 |

이보다 짧으면 캐시를 만들 수 없다. FAQ 답변 몇 개 정도는 캐시가 안 되고, 제품 매뉴얼이나 긴 시스템 프롬프트 수준은 되어야 한다.

캐시가 이득이 되는 기준은 "재사용 횟수"다. 캐시 생성에 입력 토큰 전체가 한 번 청구되고, 이후 저장료(시간 단위)가 붙는다. 같은 컨텍스트로 몇 번 이상 질의할 건지, 캐시 TTL 동안 몇 번을 쓸 건지 계산해야 한다.

### 5.2 캐시 생성과 참조

```python
from google.genai import types

cache = client.caches.create(
    model="gemini-2.5-pro",
    config=types.CreateCachedContentConfig(
        display_name="product-manual-v3",
        system_instruction="당신은 제품 매뉴얼을 보고 답하는 어시스턴트다.",
        contents=[
            types.Content(role="user", parts=[
                types.Part.from_uri(
                    file_uri=manual_pdf.uri,
                    mime_type="application/pdf",
                ),
            ])
        ],
        ttl="3600s",  # 1시간
    ),
)

print(cache.name)  # "cachedContents/abc123..."
print(cache.usage_metadata.total_token_count)  # 캐시된 토큰 수
```

이후 호출에서 `cached_content`에 캐시 리소스명만 전달하면 된다.

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="환불 정책이 뭐야?",
    config=types.GenerateContentConfig(
        cached_content=cache.name,
    ),
)

print(response.usage_metadata.cached_content_token_count)  # 캐시에서 쓴 토큰
print(response.usage_metadata.prompt_token_count)          # 총 입력 토큰
```

`cached_content_token_count`가 0이거나 없으면 캐시가 실제로 참조되지 않은 것이다. 모델이 다르거나, 캐시가 만료됐거나, 리전이 안 맞는 경우에 그렇다. 항상 이 값을 로깅해서 캐시 hit 여부를 검증해야 한다. 캐시가 있다고 생각했는데 히트가 안 나면 비용이 예상과 전혀 다르게 나온다.

### 5.3 TTL 관리와 자동 갱신

기본 TTL은 1시간이다. 최대는 모델/플랜에 따라 다르지만 보통 수십 분~몇 시간 단위로 잡는다. TTL이 짧으면 만료된 뒤 다시 만들어야 해서 초기화 비용이 반복된다.

```python
# TTL 연장
updated = client.caches.update(
    name=cache.name,
    config=types.UpdateCachedContentConfig(ttl="7200s"),
)
```

실전에서는 캐시를 쓰는 워커가 주기적으로 TTL을 갱신한다. 예를 들어 10분마다 남은 TTL을 확인하고, 20분 미만이면 1시간으로 연장하는 식이다.

```python
from datetime import datetime, timezone

def ensure_cache_fresh(client, cache_name, min_remaining_sec=1200):
    cache = client.caches.get(name=cache_name)
    remaining = (cache.expire_time - datetime.now(timezone.utc)).total_seconds()
    if remaining < min_remaining_sec:
        client.caches.update(
            name=cache_name,
            config=types.UpdateCachedContentConfig(ttl="3600s"),
        )
```

트래픽이 불규칙한 서비스에서는 캐시 만료 직후 첫 요청이 비용 스파이크를 만든다. 첫 요청이 들어올 때 캐시를 만드는 lazy 패턴보다, 서비스 시작 시점이나 배포 후에 미리 만들어두는 warm 패턴이 운영상 편하다.

### 5.4 캐시 비용 모델

캐시 비용은 세 가지로 나뉜다.

1. **생성 비용**: 캐시를 만들 때 들어간 전체 토큰이 일반 입력 요금으로 한 번 청구된다.
2. **저장 비용**: 캐시된 토큰 × 저장 시간(시간 단위). 저장 단가는 일반 입력 토큰보다 꽤 비싸다.
3. **조회 비용**: 캐시를 참조한 요청마다, 캐시된 토큰이 할인된 단가로 입력에 포함된다. 보통 일반 입력 단가의 25% 수준.

예시로 비교해본다. 50만 토큰짜리 매뉴얼을 1시간에 100번 조회하는 경우.

- **캐시 미사용**: 50만 × 100 = 5,000만 토큰 × 일반 단가
- **캐시 사용**: 50만(생성) + 50만 × 100 × 0.25(조회) + 50만 × 1시간(저장)
  = 50만 + 1,250만 + 저장료 = 1,300만 + α

이 경우 대략 4배 가까이 싸진다. 반대로 같은 컨텍스트를 2~3번만 조회하면 캐시 생성 + 저장료 때문에 오히려 손해다.

단, 저장료가 생각보다 크다. 하루 종일 5M 토큰을 캐시에 올려두고 드문드문 조회하는 케이스는 조회 할인으로 얻는 이득보다 저장료가 커질 수 있다. 조회 패턴이 예측 가능한 피크 시간대에만 올리고, 유휴 시간에는 삭제하는 운영이 현실적이다.

### 5.5 system_instruction / tools와 함께 캐싱

캐시할 수 있는 대상은 `contents`뿐 아니라 `system_instruction`, `tools`, `tool_config`도 포함된다. RAG 챗봇에서 긴 system prompt + tool 선언 전체를 캐시에 올리고, 요청마다 사용자 질의와 검색된 passage만 `contents`에 넣는 패턴이 자주 쓰인다.

```python
cache = client.caches.create(
    model="gemini-2.5-pro",
    config=types.CreateCachedContentConfig(
        system_instruction="""당신은 사내 Wiki 검색 어시스턴트다.
        답변은 항상 출처 문서명과 함께 제시한다.
        ...(긴 지침)...""",
        tools=[search_wiki_tool, get_doc_tool, list_team_tool],
        ttl="3600s",
    ),
)

# 요청 시: 캐시된 system + tools + 새로운 user 메시지
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        types.Content(role="user", parts=[
            types.Part.from_text(f"질문: {user_query}\n\n참고 문서:\n{passages}"),
        ])
    ],
    config=types.GenerateContentConfig(cached_content=cache.name),
)
```

단, 캐시된 `tools`를 참조하는 요청에서 `config`에 새로운 `tools`를 또 넘기면 동작이 모호해진다. 에러가 나거나, 캐시가 무시되거나, 둘이 합쳐진다(SDK 버전에 따라 다름). 캐시를 쓸 땐 tools도 전부 캐시에 담고 요청에서는 `tools`를 비워두는 쪽이 안전하다.

### 5.6 캐시 무효화 트리거

다음 경우에 캐시를 새로 만들어야 한다.

- **모델 변경**: `gemini-2.5-pro`로 만든 캐시는 `gemini-2.5-flash`에서 못 쓴다. 버전 picking(예: `-001` 접미사) 수준도 분리된다.
- **system_instruction / tools 스키마 변경**: 함수 선언의 파라미터나 설명이 바뀌면 캐시를 재생성해야 한다. 매뉴얼만 고정돼 있고 tool만 바뀌어도 전체 캐시를 버리고 다시 만들어야 한다.
- **파일 업데이트**: 캐시에 포함된 File API 파일이 만료되거나 내용이 바뀌면 캐시가 stale 상태가 된다. SDK는 이걸 자동으로 감지하지 못한다.
- **리전/프로젝트 변경**: Vertex AI에서 캐시는 리전 단위로 묶인다. 리전이 다르면 별도로 만들어야 한다.

운영 팁: 캐시 `display_name`에 버전 해시를 넣어두면 관리가 쉽다. 예를 들어 `product-manual-v3-sha-abc123` 형태로, 시스템 프롬프트나 문서 내용의 해시를 찍어두면 변경 시 새 캐시가 만들어지고 이전 캐시를 정리하는 배치를 돌리기 편하다.

```python
import hashlib

def cache_key(system_instr, tools_def, doc_bytes):
    h = hashlib.sha256()
    h.update(system_instr.encode())
    h.update(str(tools_def).encode())
    h.update(doc_bytes)
    return h.hexdigest()[:12]

display = f"wiki-bot-{cache_key(sys_prompt, tools, manual_bytes)}"
```

---

## 6. 정리

여기서 다룬 주제는 전부 "처음엔 기본 예제대로 돌아가는데, 트래픽이 늘거나 요구사항이 세밀해지면서 마주치는 문제"들이다. 비디오 fps 조절, File API 폴링, parallel function calling 순서 보존, 스트리밍 중 function_call 타이밍, safety false positive, 캐시 hit 검증 같은 것들은 공식 문서 예제만 보면 잘 안 드러난다. 실제로 붙여봐야 알게 되는 영역이라, 운영 로그에 각 단계의 메타데이터(토큰 수, finish_reason, cached_content_token_count, safety rating)를 남겨두는 게 결국 가장 큰 무기가 된다.
