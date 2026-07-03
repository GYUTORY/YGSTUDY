---
title: Google AI Studio 웹 도구
tags: [ai, gemini, google, ai-studio, prototyping]
updated: 2026-05-30
---

# Google AI Studio 웹 도구

## 1. AI Studio의 위치

aistudio.google.com은 Gemini 계열 모델을 브라우저에서 바로 찔러볼 수 있는 프로토타이핑 도구다. 코드 한 줄 없이 프롬프트, 모델, 파라미터를 바꿔가며 응답을 확인하고, 만족스러운 조합이 나오면 그 설정을 그대로 코드로 export 해서 서비스에 붙이는 흐름이 기본이다.

같은 Gemini API를 쓰지만 입구가 두 개라는 점이 자주 헷갈린다. AI Studio(generativelanguage.googleapis.com)와 Vertex AI(<region>-aiplatform.googleapis.com)는 모델 이름까지 거의 같아 보이지만 인증 방식, 과금 단위, 데이터 학습 정책, 사용 가능한 모델 버전이 전부 다르다. AI Studio는 "개인 Google 계정으로 무료 또는 종량제로 빠르게 돌려보는 곳"이고, Vertex AI는 "GCP 프로젝트와 IAM 안에서 운영하는 곳"이라고 보면 된다.

이 문서는 AI Studio 웹 UI 자체와, 거기서 만든 프롬프트를 실제 코드로 옮길 때 걸리는 부분을 정리한다. SDK 호출 방법은 [Gemini_API.md](Gemini_API.md)에 따로 있다.

---

## 2. 접속과 계정

aistudio.google.com에 일반 Google 계정으로 로그인하면 바로 들어간다. Workspace 계정이라면 관리자가 "Early Access Apps" 또는 "Generative AI" 카테고리를 차단해뒀을 가능성이 있어서, 회사 계정으로 안 들어가지면 개인 계정으로 시도하는 게 빠르다.

지역 제약도 있다. 한국 IP, 한국 Google 계정으로는 대부분의 모델이 정상적으로 열리지만, 일부 신규 모델(특히 미리보기 단계의 멀티모달이나 Veo, Imagen 계열)은 미국·유럽 일부 국가에만 먼저 풀린다. "Model not available in your region"이라고 뜨면 VPN으로 우회하기보다는 Vertex AI에서 같은 모델을 찾는 편이 안전하다. AI Studio는 Google 계정 region을 기준으로 차단하기 때문에 VPN만 켜도 안 풀리는 경우가 많다.

조직 정책 관점에서 회사 데이터를 AI Studio에 넣어도 되는지 한 번은 확인해야 한다. 뒤에서 다루지만 무료 티어의 입력 데이터는 모델 학습에 쓰인다. 사내 코드, 고객 데이터를 무료 티어로 그냥 넣었다가 보안팀에 걸리는 경우가 종종 있다.

---

## 3. API Key 발급과 권한 범위

좌측 상단의 "Get API key" 메뉴에서 키를 발급받는다. 키는 Google Cloud 프로젝트에 묶이는데, 이 부분이 처음 쓰는 사람들이 가장 헷갈리는 지점이다.

- "Create API key in new project"를 누르면 AI Studio가 임의의 GCP 프로젝트를 하나 만들고 거기에 키를 발급한다. 프로젝트 이름이 "Generative Language Client" 같은 식으로 자동 생성되어서 나중에 GCP 콘솔에서 찾을 때 헷갈린다.
- 기존 GCP 프로젝트에 키를 만들고 싶다면 "Create API key in existing project"를 골라 프로젝트를 직접 지정해라. 결제 계정이 붙어있는 프로젝트를 골라야 무료 티어 한도를 넘긴 다음에도 끊기지 않는다.

발급된 키는 한 번만 풀로 보여주는 게 아니라 언제든 다시 볼 수 있어서, 키 자체를 잃어버리는 문제는 잘 없다. 대신 키 권한 범위가 GCP 콘솔에서 보는 일반 API Key와는 살짝 다르다. AI Studio에서 만든 키는 기본적으로 generativelanguage.googleapis.com에만 통한다. 같은 키로 Vertex AI(aiplatform.googleapis.com)는 호출되지 않는다. Vertex AI 쪽은 OAuth나 서비스 계정 키가 필요하다.

키 노출 사고가 나면 AI Studio 화면에서 해당 키를 Delete하고 새로 발급하면 된다. 키 자체에 별도의 quota 제한 같은 건 안 걸려 있어서, 깃허브 public repo에 키가 푸시되면 그날 안에 한도가 다 털린다. AI Studio에서 만든 키도 GitHub의 secret scanning에 잡히고 자동 폐기 알림이 메일로 온다.

```bash
# AI Studio에서 받은 키는 이렇게 쓴다 (헤더가 아니라 query string)
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key=${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"안녕"}]}]}'
```

Authorization 헤더가 아니라 `?key=` query parameter로 보낸다는 점도 Vertex AI와 다르다. 로그에 키가 남기 쉬워서, nginx/CloudFront access log에서 query string을 마스킹하는 설정을 한 번 점검해두는 게 좋다.

---

## 4. 프롬프트 프로토타이핑 UI

좌측 사이드바에 "Create new prompt" 종류가 세 가지로 나뉜다.

- **Chat prompt**: 멀티턴 대화. 일반적인 챗봇 시나리오를 짤 때 쓴다.
- **Structured prompt**: input/output 예시 테이블을 채워 few-shot 프롬프트를 만든다. 분류·추출 작업처럼 입출력 패턴이 고정될 때 유용하다.
- **Freeform prompt**: 단일 입력 단일 출력. 요약, 번역, 코드 생성 같은 일회성 호출에 쓴다.

화면 가운데가 프롬프트 입력창, 우측이 모델·파라미터 설정 패널이다. 우측 패널에서 바꾸는 모든 값은 "Get code" 버튼을 눌렀을 때 Python/JavaScript/Swift 등 코드로 그대로 직렬화된다. 그래서 프로토타이핑하면서 슬라이더만 만지면 그게 곧 운영 설정이 된다.

한 가지 주의할 점은 화면을 새로고침하거나 다른 prompt로 이동하면 현재 프롬프트가 저장이 안 될 수 있다. 좌측 상단의 폴더 아이콘으로 명시적으로 "Save to Drive"를 누르지 않으면 일부 상태가 휘발한다. 길게 다듬은 system instruction이 날아가는 경우가 종종 있어서, 중요한 프롬프트는 별도 파일에 복사해두는 습관이 안전하다.

---

## 5. System Instructions

우측 패널 상단 또는 프롬프트 입력창 위쪽에 System Instructions 필드가 있다. 모델의 페르소나, 응답 스타일, 금지 사항 같은 상위 지침을 여기에 적는다.

System Instructions는 일반 user turn보다 우선순위가 높게 처리되도록 설계되어 있지만, "절대로 ~하지 마"라고 강하게 적어도 사용자 입력에 의해 깨질 때가 있다. 특히 한국어로 길게 적은 지침은 영어로 적은 지침보다 무시되는 확률이 약간 더 높다는 인상이 있다. 핵심 제약(예: "JSON만 출력하고 설명 문장 금지")은 영어로 한 줄, 한국어 부연 설명을 그 아래에 붙이는 식으로 쓰면 비교적 안정적이다.

코드로 옮길 때는 `system_instruction` 파라미터로 들어간다.

```python
from google import genai

client = genai.Client(api_key=API_KEY)
response = client.models.generate_content(
    model="gemini-2.5-pro",
    config={
        "system_instruction": "You are a senior backend engineer. Answer in Korean."
    },
    contents="Redis와 Memcached 중 무엇을 쓸까?"
)
```

AI Studio UI에서 System Instructions를 비워두고 export 하면 해당 파라미터 자체가 코드에 안 들어간다. UI에서는 한 줄이라도 적혀 있다가 지운 흔적이 남으면 빈 문자열로 export되는 경우가 있으니, 코드를 받았으면 한 번 훑어보고 빈 system_instruction은 지워라. 빈 문자열을 그대로 넘기면 일부 SDK 버전에서 에러를 낸다.

---

## 6. 모델 선택과 Compare 모드

우측 패널의 Model 드롭다운에서 사용할 모델을 고른다. AI Studio가 보여주는 이름과 API에서 쓰는 모델 ID가 살짝 다른 점이 함정이다.

| AI Studio 표기 | API 모델 ID 예시 |
|---|---|
| Gemini 2.5 Pro | gemini-2.5-pro |
| Gemini 2.5 Flash | gemini-2.5-flash |
| Gemini 2.0 Flash (Experimental) | gemini-2.0-flash-exp |
| Gemini 2.5 Flash-Lite | gemini-2.5-flash-lite |

UI에는 사람이 읽기 좋은 이름으로 나오지만 코드에는 정확한 ID가 들어가야 한다. "(Experimental)", "(Preview)" 같은 접미사가 ID에서는 `-exp`, `-preview-XXXX` 같은 식으로 바뀌고, 같은 이름이라도 시간이 지나면서 ID가 GA 버전으로 바뀐다. UI에서 동작하던 코드가 며칠 뒤 갑자기 404를 내면 모델 ID가 deprecate된 것일 가능성이 높다. AI Studio 화면에서 같은 이름을 다시 골라 코드를 export 받아보면 ID가 바뀌어 있다.

Compare 모드는 같은 프롬프트를 두세 모델에 동시에 보내 응답을 나란히 보여준다. Pro와 Flash의 응답 품질 차이, 또는 미리보기 모델이 GA 모델보다 더 나은지 비교할 때 유용하다. 다만 Compare 모드는 호출 횟수도 그만큼 늘어나서 무료 티어 quota를 빠르게 소진한다.

---

## 7. Temperature, Top-K, Top-P 슬라이더

우측 패널 아래쪽 Advanced settings를 펼치면 sampling 파라미터가 나온다. 실무에서 자주 만지는 것들이다.

- **Temperature** (0.0~2.0): 응답의 무작위성. 0에 가까우면 같은 입력에 거의 같은 출력. JSON 추출, 분류처럼 결정적이어야 하는 작업은 0.0~0.3. 글쓰기, 아이디어 생성은 0.7~1.0. 1.5 이상으로 올리면 한국어가 문법적으로 깨지기 시작한다.
- **Top-P** (0.0~1.0): nucleus sampling. 누적 확률 P까지의 토큰만 후보로 본다. Gemini는 기본값이 0.95라서 거의 모든 토큰이 후보다. 0.5 이하로 내리면 응답이 단조로워진다.
- **Top-K**: 상위 K개 토큰만 후보. Gemini 2.5 계열은 기본 40. 보통 안 건드린다.
- **Max output tokens**: 최대 출력 길이. 무한이 아니다. 한국어는 영어보다 토큰 효율이 나빠서, 같은 8192 토큰이라도 영어로는 6000단어, 한국어로는 3000~4000자 수준이다. 긴 응답이 도중에 잘리면 이 값을 먼저 의심해라.

Temperature와 Top-P를 같이 낮추는 건 효과가 중복되기 때문에 보통 둘 중 하나만 조정한다. Google 공식 문서도 Temperature 위주로 튜닝하라고 안내한다.

---

## 8. Safety Settings

Advanced settings 안에 Safety settings 섹션이 있다. Harassment, Hate speech, Sexually explicit, Dangerous content 네 카테고리에 대해 차단 임계값을 설정한다.

- Block none
- Block few (default for some models)
- Block some (default)
- Block most

기본값이 "Block some"인데, 정상적인 기술 문서 번역에서도 차단되는 경우가 꽤 자주 발생한다. 보안 관련 글을 처리하면 "Dangerous content"가 막고, 코드 리뷰 글에서 욕설 비슷한 표현(예: "이 코드는 미쳤다")이 들어가면 "Harassment"가 막는다. B2B 서비스를 만든다면 거의 다 "Block none"으로 내려야 운영이 가능하다.

응답이 빈 문자열로 오고 `finish_reason`이 `SAFETY`로 찍히면 안전 필터에 걸린 것이다. AI Studio UI에서는 빨간 경고 박스로 어떤 카테고리에서 막혔는지 보여줘서 디버깅이 편하다. 코드에서는 response 객체의 `prompt_feedback.safety_ratings`를 봐야 한다.

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt,
    config={
        "safety_settings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    },
)
```

BLOCK_NONE이 무조건 안전한 건 아니다. 일부 모델(특히 미리보기 버전)은 Civic Integrity 같은 추가 카테고리를 내부적으로 강제해서, BLOCK_NONE을 설정해도 정치·선거 관련 응답은 거부한다. 이건 끌 수가 없다.

---

## 9. Structured Output 모드

JSON으로 응답을 받고 싶을 때 쓴다. 우측 패널의 "Structured output" 토글을 켜고 스키마를 정의하면, 모델이 그 스키마에 맞는 JSON만 출력하도록 강제된다.

UI에서는 JSON Schema를 직접 입력하거나, 예시 JSON을 붙여넣으면 자동으로 스키마를 추론해준다. 추론된 스키마는 화면에서 확인하고 필드 타입을 수정할 수 있다.

```python
from pydantic import BaseModel

class BugReport(BaseModel):
    title: str
    severity: str
    affected_files: list[str]

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="이 에러 로그를 보고 버그 리포트를 만들어줘: ...",
    config={
        "response_mime_type": "application/json",
        "response_schema": BugReport,
    },
)
bug = response.parsed  # BugReport 인스턴스
```

Structured output을 켜도 가끔 스키마를 위반하는 응답이 온다. 특히 `enum` 필드에서 정의에 없는 값이 들어오거나, 배열 minItems 제약을 무시하는 경우가 있다. 받은 JSON을 파싱한 뒤 한 번 더 검증하는 코드를 두는 게 안전하다. 그리고 JSON 출력 모드는 Markdown 코드블록(```json ... ```)을 자동으로 벗기지 않는 케이스가 있어서, 가끔 응답 문자열 앞뒤에 백틱이 남아 있다. parsed 필드 대신 raw text를 직접 다룬다면 strip 처리가 필요하다.

---

## 10. Function Calling 테스트

Tools 섹션에서 함수 정의를 추가하면 모델이 그 함수를 호출하도록 유도할 수 있다. AI Studio UI는 함수 호출을 시뮬레이션해서 보여준다. 실제로 함수가 실행되지는 않고, 모델이 "이 함수를 이런 인자로 부르겠다"는 응답을 만들면 UI가 그것을 가로채 디스플레이한다.

```json
{
  "name": "get_weather",
  "description": "특정 도시의 현재 날씨를 가져온다",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {"type": "string"},
      "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
    },
    "required": ["city"]
  }
}
```

UI에서 함수 정의를 등록하고 "서울 날씨 알려줘"라고 입력하면 모델이 `get_weather(city="Seoul", unit="celsius")` 호출을 제안한다. AI Studio에서는 그 결과로 가짜 응답을 사용자가 직접 입력해서 멀티턴을 이어갈 수 있다.

실무에서 자주 막히는 부분은 "함수를 호출하지 않고 자연어로만 답변"하는 케이스다. 모델이 함수 호출이 필요한 상황을 인식하지 못하면 그냥 일반 답변을 내는데, AI Studio Tool config에서 `mode`를 `ANY`로 강제하면 무조건 함수를 호출하게 만들 수 있다. 그러나 `ANY` 모드에서는 일반 대화가 불가능해지므로, 라우터 단계에서 함수 호출이 필요한지 먼저 분기하고 호출이 필요할 때만 `ANY`로 다시 호출하는 두 단계 구조가 안정적이다.

---

## 11. Grounding with Google Search

Tools 섹션 안에 "Grounding with Google Search" 토글이 있다. 켜면 모델이 답변하기 전에 Google 검색을 한 번 돌리고, 그 결과를 컨텍스트에 넣어 답한다. 사실 확인이 필요한 질문, 최신 정보를 묻는 질문에서 hallucination이 줄어드는 효과가 있다.

응답에 grounding metadata가 같이 오는데, 어떤 검색 쿼리를 썼는지, 어떤 URL을 참조했는지 다 보인다. 사용자에게 출처 링크를 보여줘야 하는 서비스에서는 이 메타데이터가 그대로 쓸만하다.

다만 grounding을 켜면 응답 시간이 1~3초 정도 느려지고, 비용도 추가된다. 검색 한 번당 별도 과금이 붙는데(Pro 기준 검색 1000건당 $35 수준), 실시간 챗봇에 무조건 켜두면 비용이 빠르게 누적된다. 사용자가 명시적으로 "최신 정보로 답해줘"라고 했을 때만 켜는 식의 분기가 보통이다.

Grounding은 Vertex AI에서도 쓸 수 있지만 활성화 방법이 다르고, Vertex 쪽은 Google Search 외에 사용자 정의 데이터스토어(Vertex AI Search)와도 grounding할 수 있다. AI Studio는 Google Search grounding만 지원한다.

---

## 12. 코드 Export

오른쪽 위 "Get code" 버튼이 AI Studio의 핵심 기능이다. 현재 UI 상태(프롬프트, system instruction, 모델, sampling 파라미터, safety settings, tools, structured output schema)를 모두 직렬화해서 Python, JavaScript, cURL, Swift, Android, Dart로 export 한다.

Python 코드는 `google-genai` SDK 기준이다. 예전 `google-generativeai` 패키지가 아니라 새로운 통합 SDK(`google-genai`)로 export되는데, 이 둘은 import 경로와 API 표면이 다르다. 기존 코드베이스가 구 SDK를 쓰고 있다면 export된 코드를 그대로 붙여넣으면 안 된다.

```python
# 신규 SDK (AI Studio가 export하는 형태)
from google import genai

# 구 SDK (기존 코드베이스에서 자주 보이는 형태)
import google.generativeai as genai
```

cURL export는 디버깅용으로 자주 쓴다. SDK 응답이 이상할 때 같은 요청을 cURL로 날려보면 SDK 버그인지 모델 응답 자체의 문제인지 빠르게 구분된다.

---

## 13. Tuned Models (Fine-tuning)

좌측 사이드바에 "Tuned models" 메뉴가 있다. AI Studio 안에서 fine-tuning 데이터셋을 업로드하고 학습을 돌릴 수 있다. 데이터는 CSV 또는 JSONL로 input/output 페어를 넣는다.

- 지원 모델은 제한적이다. 2026년 5월 기준 AI Studio에서 튜닝 가능한 모델은 Gemini 1.5 Flash, 2.5 Flash 정도. Pro 모델은 AI Studio에서는 튜닝 불가, Vertex AI에서만 가능.
- 학습 시간은 데이터셋 크기에 따라 수십 분에서 몇 시간. UI에서 진행률이 표시된다.
- 튜닝된 모델은 `tunedModels/your-model-name` 형식의 ID로 호출한다. 이 ID는 키 발급한 프로젝트에 종속되어서, 다른 프로젝트의 키로는 호출 안 된다.

소규모 분류, 추출 작업에서 prompt engineering으로 잘 안 풀리는 패턴이 있을 때 튜닝이 효과적이다. 다만 학습 데이터 100~500건 수준으로는 큰 차이가 안 나고, 보통 1000건 이상부터 의미 있는 개선이 보인다.

실무에서는 AI Studio에서 prototyping → Vertex AI에서 본격 튜닝 흐름이 일반적이다. AI Studio 튜닝은 빠르고 간편하지만 학습 옵션이 단순하고, 운영 환경의 SLA·monitoring과 연결되지 않기 때문이다.

---

## 14. 무료 티어, Quota, 데이터 학습 정책

이 섹션이 AI Studio 도입 시 보안팀이 가장 먼저 묻는 부분이다.

### 14.1 무료 티어와 유료 티어

AI Studio에서 발급한 키는 처음에 무료 티어로 시작한다. 무료 티어 한도는 모델별로 다르지만 대략적으로,

- Gemini 2.5 Flash: 분당 10~15 RPM, 일일 1,500 요청
- Gemini 2.5 Pro: 분당 2~5 RPM, 일일 50~100 요청

수치는 Google 정책에 따라 자주 바뀐다. 실제 한도는 ai.google.dev/pricing에서 최신 값을 확인하는 게 정확하다.

GCP 프로젝트에 결제 계정을 연결하면 자동으로 유료 티어로 승격되고 한도가 풀린다. 같은 키 그대로 호출은 계속 되지만 응답 시간과 사용 가능한 모델 목록이 늘어난다. 일부 신모델(미리보기 단계)은 유료 티어에서만 풀리는 경우가 있다.

### 14.2 데이터 학습 정책 (제일 중요한 부분)

**무료 티어로 보낸 입력과 출력은 Google이 모델 개선에 사용한다.** 이게 기본 정책이다. AI Studio 약관에 명시되어 있고, "Free Quota"로 호출되는 한 끄는 옵션이 없다. 사람의 리뷰도 일부 거친다고 명시되어 있다.

**유료 티어로 결제 계정이 연결되어 있고 그 키로 호출하면, 입력과 출력은 학습에 쓰이지 않는다.** 이건 Google의 공식 약속이다. 단, 정책 위반 감지를 위한 자동화된 안전 검사는 여전히 거친다.

사내에서 AI Studio를 쓰려면 무조건 결제 계정을 연결해 유료 티어로 만든 다음 그 키를 배포해야 한다. 무료 티어 키를 그냥 쓰면 사내 코드, 고객 데이터, 시스템 프롬프트가 전부 학습 데이터로 들어간다. 무료 티어가 정말 무료가 아닌 이유다.

Vertex AI는 처음부터 학습 비사용이 기본값이라서, 데이터 민감도가 높은 워크로드는 Vertex로 가는 게 마음 편하다.

### 14.3 Quota 초과 시 동작

429 응답을 받는다. 응답 헤더에 `Retry-After`가 들어오는 경우와 안 들어오는 경우가 섞여 있어서, 클라이언트 쪽에서 exponential backoff을 직접 구현해야 한다. AI Studio UI에서도 quota를 다 쓰면 "Resource exhausted" 에러가 빨갛게 뜨고, 자정(태평양 시간) 기준으로 리셋된다. 한국 시간으로는 오후 4~5시쯤이다.

---

## 15. AI Studio vs Vertex AI 차이 정리

같은 Gemini 모델이지만 운영 환경 관점에서 본 차이.

| 항목 | AI Studio | Vertex AI |
|---|---|---|
| 인증 | API Key (query string) | OAuth / 서비스 계정 |
| 엔드포인트 | generativelanguage.googleapis.com | <region>-aiplatform.googleapis.com |
| Region 선택 | 자동 (미국 중심) | 명시적 선택 (asia-northeast3 등) |
| 데이터 학습 (무료) | O (입력 학습됨) | 해당 없음 (무료 티어 없음) |
| 데이터 학습 (유료) | X | X |
| IAM 통합 | X | O |
| VPC Service Controls | X | O |
| Audit Log | 제한적 | Cloud Audit Logs 완전 통합 |
| Tuning | Flash 모델 일부 | 거의 모든 모델 |
| Grounding | Google Search만 | Google Search + Vertex AI Search |
| SLA | 없음 (best effort) | 있음 (모델별) |
| 신규 모델 출시 | 더 빠름 | 약간 늦음 |

요약하면 AI Studio는 "빠르게 시도해보고 export 받는 도구", Vertex AI는 "운영하는 곳"이다. 두 환경에서 같은 모델 ID를 쓴다고 해서 응답이 100% 같진 않다. region이 다르고, 내부적으로 적용되는 안전 정책 미세 차이가 있어서, AI Studio에서 잘 동작하던 프롬프트가 Vertex AI에서 차단되는 케이스도 있다. 운영 옮기기 전에 Vertex AI에서 다시 한 번 회귀 테스트를 돌려야 한다.

---

## 16. 한국어 응답 품질에 관한 실무 메모

AI Studio에서 모델을 비교하다 보면 한국어 응답 품질이 영어와 다르게 느껴진다. 몇 가지 패턴.

- **Pro vs Flash 차이가 한국어에서 더 크다.** 영어 응답은 Pro와 Flash가 비슷한 품질을 내지만, 한국어로 긴 글을 생성시키면 Flash 쪽이 문장 구조가 어색해지고 반복이 늘어난다. 한국어 글쓰기 작업은 가능한 한 Pro를 쓰는 게 결과가 안정적이다.
- **System Instruction 영어 권장.** 앞에서도 적었지만, 한국어로 길게 적은 지침보다 영어 짧은 지침이 더 잘 지켜진다. "Respond in Korean. Use formal tone. Do not use emojis." 같은 영어 한두 줄이 한국어 다섯 줄보다 효과적이다.
- **Structured output 한국어 enum.** enum 값을 한국어로 정의하면 모델이 enum에 없는 변형(예: 정의는 "긍정"인데 응답이 "긍정적")을 출력하는 빈도가 영어 enum보다 높다. enum 값은 영어로 두고 UI 렌더링에서 한국어로 매핑하는 편이 안전하다.
- **토큰 효율.** 한국어는 1글자가 평균 2~3 토큰을 차지한다. 영어 문서를 한국어로 번역해서 처리하면 토큰 비용이 2~3배 늘어난다. 비용에 민감한 워크로드라면 system instruction이나 few-shot 예시는 영어로 두고 사용자 입력만 한국어로 받는 식으로 절약할 수 있다.

이런 부분은 모델 버전이 바뀌면 또 달라진다. AI Studio Compare 모드로 분기마다 한 번씩 새 모델과 기존 모델을 비교해두면 회귀를 빨리 잡을 수 있다.
