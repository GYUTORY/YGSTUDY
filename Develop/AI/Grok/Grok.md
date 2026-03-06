---
title: Grok 사용법 및 핵심 개념
tags: [ai, grok, xai, coding-assistant, api]
updated: 2026-03-01
---

# Grok

## 1. Grok이란

**Grok**은 Elon Musk가 설립한 **xAI**에서 개발한 AI 어시스턴트이자 대규모 언어 모델 패밀리이다. X(구 Twitter)와의 실시간 연동이 특징이며, 코딩 전용 모델(`grok-code-fast-1`)과 CLI 도구(Grok Build)를 통해 개발자 워크플로우를 지원한다.

### 1.1 주요 특징

- **실시간 정보 접근**: X/Twitter 통합으로 최신 트렌드와 공개 담론 데이터 활용
- **초고속 응답**: 코딩 제안 2초 이내, 일반 응답도 거의 즉시
- **대규모 컨텍스트**: 최대 2M 토큰 컨텍스트 윈도우 (Fast 모델)
- **저렴한 가격**: Fast 모델 기준 $0.20/$0.50 per 1M 토큰
- **OpenAI SDK 호환**: 기존 OpenAI SDK를 `base_url`만 변경하여 사용 가능
- **멀티모달**: 텍스트, 이미지 생성/이해, 비디오 생성, 음성까지 통합 API

### 1.2 다른 AI 도구와의 비교

| 특징 | Grok | Claude Code | Codex |
|------|------|------------|-------|
| **개발사** | xAI | Anthropic | OpenAI |
| **코딩 전용 모델** | grok-code-fast-1 | Claude Opus/Sonnet | gpt-5.3-codex |
| **컨텍스트 윈도우** | 최대 2M 토큰 | 200K 토큰 | 모델별 상이 |
| **실시간 정보** | X/Twitter 네이티브 | WebSearch | WebSearch |
| **API 가격 (입력)** | $0.20/1M (Fast) | 모델별 상이 | $1.75/1M |
| **CLI 도구** | Grok Build | Claude Code | Codex CLI |
| **오픈소스** | CLI 일부 | 비공개 | Apache-2.0 |

---

## 2. 모델 라인업

### 2.1 주요 모델

| 모델 | 컨텍스트 | 입력 가격 | 출력 가격 | 주요 기능 |
|------|---------|----------|----------|----------|
| **grok-4-1-fast-reasoning** | 2M | $0.20 | $0.50 | 함수 호출, 구조화 출력, 추론, 비전 |
| **grok-4-1-fast-non-reasoning** | 2M | $0.20 | $0.50 | 함수 호출, 구조화 출력, 비전 |
| **grok-4-0709** | 256K | $3.00 | $15.00 | 최상위 추론, 비전 |
| **grok-3** | 131K | $3.00 | $15.00 | 함수 호출, 구조화 출력 |
| **grok-3-mini** | 131K | $0.30 | $0.50 | 경량 추론 |
| **grok-code-fast-1** | 256K | $0.20 | $1.50 | 코딩 특화, 추론 |

> 가격은 1M 토큰 기준 (USD)

### 2.2 코딩 전용 모델: grok-code-fast-1

코딩 작업에 최적화된 추론 모델이다.

- **SWE-Bench-Verified**: 70.8%
- **코딩 정확도**: 93.0%
- **지원 언어**: TypeScript, Python, Java, Rust, C++, Go
- **추론 트레이스 노출**: 응답에서 추론 과정을 확인 가능
- **함수 호출 & 구조화 출력**: 자율 에이전트 구축에 적합
- **개발 도구 숙련**: grep, 터미널, 파일 편집 등

### 2.3 특수 모델

| 모델 | 용도 | 가격 |
|------|------|------|
| **grok-2-image-1212** | 텍스트→이미지 | $0.07/장 |
| **grok-imagine-image** | 텍스트/이미지→이미지 | $0.02/장 |
| **grok-imagine-video** | 텍스트/이미지→비디오 | $0.05/초 |

---

## 3. 설치 및 설정

### 3.1 API 접근 설정

```bash
# 1. x.ai에서 계정 생성 및 API 키 발급
#    https://console.x.ai/

# 2. 환경 변수 설정
export XAI_API_KEY="your_api_key"

# .zshrc에 영구 설정
echo 'export XAI_API_KEY="your_api_key"' >> ~/.zshrc
```

📌 **무료 크레딧**: 신규 가입 시 **$25 무료 크레딧** 제공. 데이터 공유 프로그램 참여 시 월 **$150 추가** 제공.

### 3.2 Grok Build (공식 CLI)

2026년 2월에 출시된 xAI 공식 코딩 에이전트 도구이다.

- CLI 기반으로 여러 머신에서 동시 작업 가능
- 코드는 **로컬에서 실행** (클라우드 전송 없음)
- 자동 작업 계획, 정보 검색, 멀티스텝 워크플로우
- GitHub 통합 내장
- 여러 Grok 모델 선택 가능

### 3.3 grok-cli (오픈소스)

```bash
# bun으로 설치
bun add -g @vibe-kit/grok-cli

# 또는 npm으로 설치
npm install -g @vibe-kit/grok-cli
```

**주요 기능**:
- Grok 모델 기반 대화형 AI
- 파일 읽기/생성/수정
- Bash 명령 실행
- 최대 400라운드 도구 실행
- 기본 엔드포인트: `https://api.x.ai/v1`

---

## 4. API 사용법

### 4.1 OpenAI SDK 호환 (Python)

기존 OpenAI SDK의 `base_url`만 변경하면 바로 사용 가능하다.

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_xai_api_key",
    base_url="https://api.x.ai/v1"
)

# 코딩 전용 모델 사용
completion = client.chat.completions.create(
    model="grok-code-fast-1",
    messages=[
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Python으로 퀵소트 구현해줘"}
    ]
)

print(completion.choices[0].message.content)
```

### 4.2 xAI 네이티브 SDK (Python)

```bash
pip install xai-sdk
```

### 4.3 JavaScript (Vercel AI SDK)

```bash
npm install @ai-sdk/xai
```

### 4.4 REST API 직접 호출

```bash
curl https://api.x.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -d '{
    "model": "grok-code-fast-1",
    "messages": [
      {"role": "user", "content": "TypeScript로 Express 서버 만들어줘"}
    ]
  }'
```

### 4.5 API 엔드포인트

| 엔드포인트 | 용도 |
|-----------|------|
| `POST /v1/chat/completions` | 채팅 완성 |
| `POST /v1/responses` | 응답 생성 |
| **Base URL** | `https://api.x.ai` |
| **리전 엔드포인트** | `us-east-1` (미국), `eu-west-1` (유럽) |

### 4.6 도구 호출 가격

Web Search, X Search, Code Execution, Document Search: **$5 / 1,000 호출**

---

## 5. IDE 통합

### 5.1 GitHub Copilot

Grok Code Fast 1은 GitHub Copilot의 모델 선택기에서 바로 사용 가능하다.

**지원 환경**:
- github.com
- GitHub Mobile
- VS Code
- Visual Studio
- JetBrains IDEs
- Xcode
- Eclipse

### 5.2 Cursor 설정

```
1. Cursor 설치
2. Cursor Settings → Models → API Keys
3. Override OpenAI Base URL: https://api.x.ai/v1
4. xAI API Key 입력
5. Custom Model 추가: grok-code-fast-1
```

### 5.3 Cline (VS Code 확장)

```
1. VS Code 마켓플레이스에서 Cline 설치
2. Cline 열기 → "Use your own API key"
3. xAI API Key 입력 후 저장
4. Cline Settings → API Configuration → grok-code-fast-1 선택
```

### 5.4 기타 지원 에디터

OpenCode, Kilo Code, Roo Code, Windsurf 등에서도 사용 가능하다.

---

## 6. 핵심 기능

### 6.1 추론 모드

| 모드 | 설명 |
|------|------|
| **Think Mode** | 기본 추론. 복잡한 문제에 대해 단계적 사고 |
| **Big Brain Mode** | 더 많은 연산을 할당하여 심층 추론 수행 |

### 6.2 실시간 검색

X/Twitter와의 네이티브 통합으로 다른 AI 도구에 없는 실시간 소셜 데이터에 접근 가능하다.

```python
# X Search 활용 예시
completion = client.chat.completions.create(
    model="grok-4-1-fast-reasoning",
    messages=[
        {"role": "user", "content": "최근 React 19 관련 트렌드 분석해줘"}
    ],
    tools=[{"type": "x_search"}]  # X 검색 도구 활용
)
```

### 6.3 Batch API

대량 처리 시 **표준 가격의 50%**로 비동기 처리 가능. 대부분 24시간 이내 완료.

### 6.4 멀티모달 통합

텍스트, 이미지 생성, 이미지 이해, 비디오 생성, 음성이 **하나의 API**에서 모두 지원된다. 별도 서비스 불필요.

---

## 7. 비용 관리 팁

| 전략 | 설명 |
|------|------|
| **Fast 모델 활용** | 일반 작업에는 grok-4-1-fast ($0.20/$0.50)로 비용 절감 |
| **코딩은 전용 모델** | 코딩 작업에는 grok-code-fast-1 사용 |
| **Batch API** | 대량 처리 시 50% 할인 |
| **무료 크레딧** | 가입 시 $25 무료 + 데이터 공유 시 월 $150 |
| **캐싱 활용** | 반복 요청은 캐싱하여 API 호출 줄이기 |

---

## 8. 다른 도구에서 마이그레이션

### OpenAI에서 Grok으로

```python
# 변경 전 (OpenAI)
client = OpenAI(api_key="sk-...")

# 변경 후 (Grok) — base_url만 추가
client = OpenAI(
    api_key="xai-...",
    base_url="https://api.x.ai/v1"
)
```

API 호환성이 높아 `base_url`과 `api_key`, `model`만 변경하면 기존 코드가 대부분 동작한다.

---

## 참고

- [xAI 공식 사이트](https://x.ai)
- [xAI API 문서](https://docs.x.ai)
- [xAI 모델 및 가격](https://docs.x.ai/developers/models)
- [Grok Code Fast 1 발표](https://x.ai/news/grok-code-fast-1)
- [코드 에디터 연동 가이드](https://docs.x.ai/docs/guides/use-with-code-editors)
- [xAI API 튜토리얼](https://docs.x.ai/docs/tutorial)
- [Grok Build](https://grokai.build)
