---
title: "Gemini 트러블슈팅"
tags: [Gemini, Troubleshooting, API, Google AI]
updated: 2026-04-15
---

# Gemini 트러블슈팅

Gemini API를 실무에서 쓰다 보면 문서에 안 나오는 에러를 자주 만난다. 특히 429 에러, 인증 만료, 멀티모달 파일 제한 같은 문제는 처음 겪으면 원인 파악에 시간을 꽤 쓰게 된다. 여기서는 자주 발생하는 문제와 실제 대응 방법을 정리한다.

---

## API 에러 코드별 원인과 대응

### 429 Too Many Requests

가장 흔하게 만나는 에러다. Gemini API는 분당 요청 수(RPM)와 분당 토큰 수(TPM) 두 가지 제한이 있다.

**발생 원인**

- 무료 티어: RPM 15, TPM 100만으로 제한이 꽤 빡빡하다
- 유료 티어(Pay-as-you-go): RPM 2000까지 올라가지만, 동시 요청이 몰리면 여전히 걸린다
- 배치 처리에서 sleep 없이 반복 호출하면 거의 확실하게 발생한다

**대응 방법**

Exponential backoff를 직접 구현하는 게 가장 확실하다:

```python
import time
import google.generativeai as genai

def call_with_retry(model, prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            if "429" in str(e):
                wait_time = (2 ** attempt) + 1
                print(f"Rate limited. {wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("최대 재시도 횟수 초과")
```

주의할 점은 429 응답 헤더에 `Retry-After` 값이 항상 들어오지는 않는다는 것이다. 들어오면 그 값을 쓰고, 없으면 exponential backoff로 처리한다.

배치 처리가 많다면 요청 간격을 미리 확보하는 게 낫다. 429를 받고 재시도하는 것보다 처음부터 초당 요청 수를 조절하는 방식이 전체 처리 시간이 더 짧은 경우가 많다.

### 400 Invalid Argument

요청 본문이 잘못됐을 때 발생하는데, 메시지가 모호한 경우가 있다.

**자주 겪는 원인들**

- **빈 content 전달**: `contents`에 빈 문자열이나 `None`을 넘기면 발생한다
- **지원하지 않는 모델명**: `gemini-pro`처럼 deprecated된 모델명을 쓰면 발생한다. `gemini-2.0-flash` 같은 현재 모델명을 확인해야 한다
- **role 값 오류**: Chat에서 role은 `user`와 `model`만 허용한다. `assistant`나 `system`을 쓰면 에러가 난다
- **멀티모달에서 잘못된 MIME 타입**: 이미지를 보내면서 MIME 타입을 명시하지 않거나 잘못 지정하면 발생한다

```python
# 잘못된 예 - role 이름
chat = model.start_chat(history=[
    {"role": "assistant", "parts": ["안녕하세요"]}  # 에러 발생
])

# 올바른 예
chat = model.start_chat(history=[
    {"role": "model", "parts": ["안녕하세요"]}
])
```

### 403 Permission Denied

**원인 구분이 중요하다:**

- API 키가 잘못된 경우: 키를 재발급받아야 한다
- API가 활성화되지 않은 경우: Google Cloud Console에서 "Generative Language API"가 활성화됐는지 확인한다
- 리전 제한: 일부 리전에서 Gemini API 접근이 제한될 수 있다. 이 경우 VPN이나 프록시가 아니라 Google Cloud 프로젝트 설정을 확인해야 한다

### 500 Internal Server Error / 503 Service Unavailable

Google 서버 쪽 문제다. 할 수 있는 건 재시도뿐이다. 다만 몇 가지 확인할 게 있다:

- 요청 payload가 너무 크지 않은지 확인한다. 특히 멀티모달 요청에서 큰 파일을 보내면 서버 타임아웃이 날 수 있다
- `generateContent` 대신 `streamGenerateContent`로 바꾸면 타임아웃을 피할 수 있는 경우가 있다
- 같은 에러가 반복되면 [Google Cloud Status Dashboard](https://status.cloud.google.com/)를 확인한다

---

## 긴 컨텍스트에서의 Hallucination 문제

Gemini 2.5 Pro는 100만 토큰 컨텍스트를 지원하지만, 긴 컨텍스트를 넣는다고 항상 좋은 결과가 나오는 건 아니다.

### "Lost in the Middle" 현상

긴 문서를 컨텍스트로 넣으면 문서의 앞부분과 뒷부분 정보는 잘 활용하지만, 중간에 있는 정보를 놓치거나 잘못 인용하는 경우가 있다. 이건 Gemini만의 문제가 아니라 LLM 전반의 특성이다.

**실무에서 겪는 패턴:**

- 10만 토큰 이상의 코드베이스를 통째로 넣고 특정 함수를 찾아달라고 하면, 비슷한 이름의 다른 함수를 가져오는 경우가 있다
- 여러 문서를 concat해서 넣으면 문서 간 내용을 섞어서 답변하는 경우가 있다

**대응 방법:**

컨텍스트가 5만 토큰을 넘으면 몇 가지를 시도해볼 수 있다:

1. 관련 있는 부분만 추출해서 넣는다. 전체를 넣는 것보다 정확도가 높다
2. 컨텍스트 앞쪽에 중요한 정보를 배치한다
3. 질문을 구체적으로 만든다. "이 코드에서 문제를 찾아줘"보다 "auth.py 파일의 `verify_token` 함수에서 토큰 만료 처리가 맞는지 확인해줘"가 낫다
4. System instruction에 "제공된 컨텍스트에 없는 내용은 '확인할 수 없다'고 답변하라"를 명시한다

```python
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro",
    system_instruction="제공된 문서에 명시되지 않은 내용은 추측하지 말고 '해당 정보를 확인할 수 없다'고 답변하라."
)
```

---

## Code Assist IDE 플러그인 연결 문제

### VS Code에서 Gemini Code Assist가 동작하지 않을 때

**증상별 확인 사항:**

**플러그인이 로드되지 않는 경우**

- VS Code 버전을 확인한다. Gemini Code Assist는 최소 1.83.0 이상이 필요하다
- 다른 AI 코드 어시스턴트 확장(GitHub Copilot 등)과 충돌하는 경우가 있다. 한쪽을 비활성화하고 테스트한다
- 출력 패널(Output Panel)에서 "Gemini Code Assist"를 선택하면 구체적인 에러 로그를 볼 수 있다

**로그인은 됐는데 자동완성이 안 되는 경우**

- Google Cloud 프로젝트에서 Cloud AI Companion API가 활성화됐는지 확인한다
- 회사 계정을 쓰는 경우, 조직 정책에서 Gemini 접근을 차단하고 있을 수 있다. 관리자에게 확인이 필요하다
- 프록시 환경이면 VS Code의 `http.proxy` 설정을 확인한다

### JetBrains IDE에서 연결 안 될 때

JetBrains 플러그인은 VS Code보다 업데이트가 느린 편이다.

- 플러그인 버전이 최신인지 확인한다. JetBrains Marketplace에서 직접 업데이트해야 하는 경우가 있다
- `Help > Diagnostic Tools > Debug Log Settings`에서 `#google.cloud.tools`를 추가하면 상세 로그를 볼 수 있다
- IDE 재시작 후에도 안 되면 `~/.config/google-cloud-tools-java/` (Linux/Mac) 또는 `%APPDATA%\google-cloud-tools-java\` (Windows) 디렉토리를 삭제하고 재인증한다

---

## CLI 인증 만료 처리

### gcloud 기반 인증

Gemini API를 gcloud 인증으로 사용하는 경우, 토큰 만료가 자주 발생한다.

```bash
# 현재 인증 상태 확인
gcloud auth list

# 토큰 갱신
gcloud auth login

# Application Default Credentials 갱신
gcloud auth application-default login
```

**자주 겪는 문제:**

- `gcloud auth application-default login`과 `gcloud auth login`은 다른 credential이다. API 호출에는 전자가 필요하다
- credential 파일 위치: `~/.config/gcloud/application_default_credentials.json`
- 이 파일이 손상되면 인증 에러가 나는데, 에러 메시지만으로는 파악이 어렵다. 파일을 삭제하고 다시 `gcloud auth application-default login`을 실행하는 게 빠르다

### API 키 방식에서의 문제

```python
import google.generativeai as genai

# 환경 변수로 설정하는 게 안전하다
import os
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
```

API 키가 만료되거나 삭제된 경우:

- Google AI Studio(aistudio.google.com)에서 키 상태를 확인한다
- 키를 새로 발급받으면 기존 키는 즉시 무효화된다
- 여러 환경(로컬, 서버, CI)에서 같은 키를 쓰고 있으면 한 곳에서 키를 재발급하면 전부 깨진다. 환경별로 키를 분리하는 게 맞다

### 서비스 계정 인증

프로덕션 환경에서는 서비스 계정을 쓰는 게 일반적이다:

```bash
# 서비스 계정 키 파일로 인증
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

서비스 계정에서 겪는 문제:

- 키 파일의 권한이 너무 열려있으면(`chmod 777` 등) 일부 라이브러리에서 경고가 발생한다. `chmod 600`으로 설정한다
- 서비스 계정에 "Vertex AI User" 역할이 없으면 Vertex AI 경유 Gemini 호출에서 403이 발생한다
- 키 파일 경로에 한글이나 공백이 있으면 인식 못하는 경우가 있다

---

## 프롬프트 캐싱 미적용 디버깅

Gemini API의 Context Caching은 동일한 컨텍스트를 반복 사용할 때 비용과 지연을 줄여준다. 그런데 캐싱을 설정했는데 실제로 적용이 안 되는 경우가 자주 있다.

### 캐싱이 동작하지 않는 경우

**최소 토큰 수 미달**

캐싱이 적용되려면 캐시할 컨텐츠가 최소 토큰 수를 넘어야 한다. Gemini 2.5 Pro 기준 최소 4,096 토큰이 필요하다. 짧은 system instruction만 캐싱하려고 하면 적용되지 않는다.

**캐시 생성 확인**

```python
from google.generativeai import caching
import datetime

# 캐시 생성
cache = caching.CachedContent.create(
    model="models/gemini-2.5-pro",
    display_name="my-cache",
    contents=[long_document],
    ttl=datetime.timedelta(hours=1)
)

# 캐시가 실제로 생성됐는지 확인
print(f"Cache name: {cache.name}")
print(f"Token count: {cache.usage_metadata.total_token_count}")

# 캐시를 사용해서 모델 생성
model = genai.GenerativeModel.from_cached_content(cache)
response = model.generate_content("이 문서를 요약해줘")
```

**캐시가 적용됐는지 확인하는 방법**

응답의 `usage_metadata`에서 `cached_content_token_count`를 확인한다. 이 값이 0이면 캐싱이 적용되지 않은 것이다:

```python
response = model.generate_content("질문")
print(response.usage_metadata)
# cached_content_token_count가 0보다 커야 캐싱이 적용된 것
```

**TTL 만료**

캐시의 기본 TTL은 1시간이다. 만료되면 자동으로 삭제된다. 긴 작업이면 TTL을 넉넉히 설정하거나, 만료 전에 갱신한다:

```python
# TTL 업데이트
cache.update(ttl=datetime.timedelta(hours=4))
```

**모델 변경 시 캐시 무효화**

캐시는 특정 모델에 종속된다. 같은 컨텐츠라도 모델을 바꾸면 캐시를 새로 만들어야 한다.

---

## 멀티모달 입력 시 파일 크기 및 형식 제한

### 이미지 제한

| 항목 | 제한 |
|------|------|
| 지원 형식 | PNG, JPEG, WEBP, HEIC, HEIF |
| 최대 파일 크기 | 20MB (inline), File API 사용 시 2GB |
| 요청당 최대 이미지 수 | 3,600개 |
| 최대 해상도 | 제한 없음 (자동 리사이징) |

**자주 겪는 문제:**

- Base64 인코딩으로 이미지를 보내면 원본보다 크기가 약 33% 커진다. 15MB 이미지도 인코딩하면 20MB를 넘길 수 있다
- GIF는 첫 프레임만 처리된다. 애니메이션 GIF 분석이 필요하면 프레임을 개별 이미지로 추출해서 보내야 한다
- HEIC 파일은 macOS/iOS에서 기본 촬영 포맷인데, 서버에서 처리할 때 라이브러리가 없어서 실패하는 경우가 있다

```python
# 큰 이미지는 File API를 사용한다
import google.generativeai as genai

# 파일 업로드
uploaded_file = genai.upload_file("large_image.png")

# 업로드 상태 확인 - 큰 파일은 처리에 시간이 걸린다
import time
while uploaded_file.state.name == "PROCESSING":
    time.sleep(2)
    uploaded_file = genai.get_file(uploaded_file.name)

if uploaded_file.state.name == "FAILED":
    raise ValueError(f"파일 처리 실패: {uploaded_file.state.name}")

model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content([uploaded_file, "이 이미지를 분석해줘"])
```

### 비디오 제한

| 항목 | 제한 |
|------|------|
| 지원 형식 | MP4, MPEG, MOV, AVI, FLV, MKV, WEBM 등 |
| 최대 파일 크기 | File API로 2GB |
| 최대 영상 길이 | 약 1시간 |

**주의사항:**

- 비디오는 반드시 File API로 업로드해야 한다. inline으로 보내면 에러가 발생한다
- 업로드 후 처리 완료까지 대기해야 한다. 처리가 끝나기 전에 호출하면 400 에러가 난다
- 오디오 트랙도 함께 분석된다. 자막 없는 영상에서 음성 내용을 물어볼 수 있다

### 오디오 제한

| 항목 | 제한 |
|------|------|
| 지원 형식 | MP3, WAV, AIFF, AAC, OGG, FLAC |
| 최대 파일 크기 | File API로 2GB |
| 최대 길이 | 약 9.5시간 |

### PDF 제한

| 항목 | 제한 |
|------|------|
| 최대 페이지 수 | 3,600페이지 |
| 최대 파일 크기 | File API로 2GB |

**PDF에서 겪는 문제:**

- 스캔된 PDF(이미지 기반)는 OCR 정확도가 떨어질 수 있다. 텍스트 레이어가 있는 PDF가 결과가 좋다
- 표가 많은 PDF에서 표 구조를 정확히 파싱하지 못하는 경우가 있다. 이런 경우 표만 별도로 추출해서 텍스트로 전달하는 게 낫다

### File API 공통 주의사항

```python
# 업로드된 파일 목록 확인
for f in genai.list_files():
    print(f"{f.name} | {f.display_name} | {f.state.name}")

# 파일 삭제 - 48시간 후 자동 삭제되지만, 수동 삭제도 가능
genai.delete_file(uploaded_file.name)
```

- 업로드된 파일은 48시간 후 자동 삭제된다. 그 전에 다시 쓰려면 파일 name을 저장해둬야 한다
- 파일 업로드 API에는 별도의 rate limit이 있다. 대량 업로드 시 429를 만날 수 있다
- 업로드한 파일은 해당 API 키나 프로젝트에 종속된다. 다른 프로젝트에서 접근할 수 없다
