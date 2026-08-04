---
title: Prompt Caching
tags: [ai, prompt-caching, anthropic, gemini, context-caching, cost-optimization, llm]
updated: 2026-08-04
---

# Prompt Caching

LLM API 호출에서 입력 토큰 비용은 대화가 길어질수록 빠르게 불어난다. 에이전트 루프에서 도구를 5번 호출하면, 동일한 시스템 프롬프트와 이전 대화 내역을 5번 반복해서 보낸다. Prompt Caching은 이 반복 구간을 서버가 KV 캐시로 보관해뒀다가 재사용하는 기능이다. 비용 절감이 목적이지만, prefill 시간도 줄어들어 TTFT(Time To First Token)에도 영향을 준다.

벤더마다 구현 방식이 다르다. Anthropic은 명시적 마크업, Gemini는 캐시 객체 사전 생성, OpenAI는 자동 감지다. 이 문서는 Anthropic과 Gemini를 중심으로 동작 방식, 비용 계산, 히트율 패턴, 무효화 케이스를 정리한다.

## Anthropic Prompt Caching

### 동작 원리

`cache_control: {"type": "ephemeral"}`을 메시지 블록에 붙이면, 그 블록까지의 prefix가 캐시 대상이 된다. 서버는 요청이 들어오면 prefix를 앞부터 순서대로 비교하고, 저장된 캐시와 일치하는 구간까지의 KV를 재사용한다.

캐시는 메시지 전체가 아니라 prefix 단위다. 요청 시작부터 특정 지점까지가 이전 요청과 100% 동일해야 히트한다. 중간에 한 토큰이라도 다르면, 그 지점 이후는 전부 미스다.

`cache_control`은 하나의 요청에 최대 4개까지 붙일 수 있다. 각 마크업이 캐시 브레이크포인트를 만드는 구조다.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "당신은 주문 처리 시스템 전문가다. ...(긴 시스템 프롬프트)...",
            "cache_control": {"type": "ephemeral"}  # 여기까지 캐싱
        }
    ],
    messages=[
        {"role": "user", "content": "ORD-12345 상태 확인해줘"}
    ]
)

usage = response.usage
print(f"캐시 생성: {usage.cache_creation_input_tokens}")
print(f"캐시 히트: {usage.cache_read_input_tokens}")
print(f"일반 입력: {usage.input_tokens}")
```

`cache_creation_input_tokens`가 0이 아니면 이번 요청에서 캐시가 새로 쓰였다(1.25배 과금). `cache_read_input_tokens`가 0이 아니면 히트했다(0.1배 과금). 둘 다 0이면 캐시 제어를 안 넣었거나 미스다.

### TTL과 비용 계산식

캐시는 마지막 히트 시점으로부터 TTL 동안 유지된다. TTL이 지나면 캐시가 사라지고, 다음 요청에서 다시 쓰기가 발생한다.

| TTL | 옵션 | 추가 비용 |
|---|---|---|
| 5분 | `ephemeral` (기본) | 없음 |
| 1시간 | `ephemeral` + 별도 플래그 (모델별 지원 여부 확인) | 캐시 저장 시간당 과금 |

**기본 요금 배수 (Anthropic)**

| 상황 | 배수 |
|---|---|
| 캐시 쓰기 (첫 요청, 캐시 생성) | 1.25× |
| 캐시 읽기 (히트) | 0.1× |
| 캐시 미스 (캐시 없는 일반 입력) | 1.0× |

**손익분기점 계산**

캐시 쓰기 비용(1.25)을 회수하려면 최소 두 번째 히트부터 이득이다. N회 요청한다고 하면:

```
캐시 없이 N회: N × 1.0 = N
캐시 사용 N회: 1.25 + (N-1) × 0.1

손익분기: 1.25 + (N-1) × 0.1 < N
→ N > 약 1.39 → 2회부터 이득
```

실제 절감율:

| 요청 횟수 | 캐시 없이 | 캐시 사용 | 절감율 |
|---|---|---|---|
| 3회 | 3.0 | 1.25 + 0.2 = 1.45 | 52% |
| 5회 | 5.0 | 1.25 + 0.4 = 1.65 | 67% |
| 10회 | 10.0 | 1.25 + 0.9 = 2.15 | 79% |
| 20회 | 20.0 | 1.25 + 1.9 = 3.15 | 84% |

에이전트 루프처럼 같은 세션 안에서 도구를 반복 호출하는 패턴에서 절감율이 가장 크다. 대신 TTL 5분이 지나면 캐시가 날아가니, 요청 간격이 5분을 초과하는 배치 작업에서는 효과가 없다.

**최소 토큰 요건**

캐시 생성에는 최소 토큰이 필요하다. 이 기준을 충족하지 못하면 `cache_control`을 붙여도 캐시가 생성되지 않는다.

| 모델 | 최소 캐시 가능 토큰 |
|---|---|
| Claude Haiku, Sonnet 계열 | 1,024 토큰 |
| Claude Opus 계열 | 2,048 토큰 |

시스템 프롬프트가 짧으면 캐시가 아예 안 만들어진다. 짧은 프롬프트에 문서를 포함시키거나, 멀티턴 대화에서 이전 대화 내역과 함께 캐시 경계를 잡아야 한다.

## Gemini Context Caching

### 동작 원리

Gemini는 Anthropic과 구조가 다르다. 요청 시점에 마크업을 넣는 게 아니라, 캐시 객체를 미리 만들어두고 API 호출 시 핸들을 참조하는 방식이다.

```python
import google.generativeai as genai
from google.generativeai import caching
import datetime

# 1단계: 캐시 객체 생성
cache = caching.CachedContent.create(
    model="models/gemini-1.5-pro-002",
    system_instruction="당신은 주문 처리 시스템 전문가다. ...(긴 시스템 프롬프트)...",
    contents=[
        # 반복 참조할 문서, 코드베이스 등
        {"role": "user", "parts": [{"text": "...(긴 참조 문서)..."}]},
    ],
    ttl=datetime.timedelta(hours=1),  # 명시적 TTL 지정
)

print(f"캐시 이름: {cache.name}")

# 2단계: 캐시를 참조해서 호출
model = genai.GenerativeModel.from_cached_content(cached_content=cache)
response = model.generate_content("ORD-12345 상태 확인해줘")
print(response.text)
```

캐시 객체에는 이름이 붙고, 다른 요청에서도 같은 캐시를 재사용할 수 있다. 동일 세션이 아니어도 된다는 점이 Anthropic과 다르다. 여러 사용자가 공통 문서(예: 긴 제품 매뉴얼, 코드베이스)를 참조하는 패턴에서 유용하다.

### TTL과 비용 계산식

Gemini Context Caching은 스토리지 비용이 별도로 발생한다. TTL이 길수록 저장 비용이 쌓인다.

**Gemini 1.5 Pro 기준 (2025년 기준, 변동 가능)**

| 항목 | 비용 |
|---|---|
| 캐시 저장 | 시간당 토큰당 과금 (일반 입력가의 약 1/4 수준) |
| 캐시 사용 (히트) | 일반 입력가의 25% (75% 할인) |
| 최소 캐시 가능 토큰 | 32,768 토큰 |

Anthropic(90% 할인)보다 할인율은 낮지만, TTL을 시간 단위로 길게 잡을 수 있고 스토리지 비용은 상대적으로 저렴하다. 수백만 토큰 짜리 긴 문서를 여러 사용자가 장시간 반복 참조하는 케이스에서는 Gemini 방식이 더 유리할 수 있다.

**손익분기점**

스토리지 비용(저장 유지 시간 × 토큰 수)과 캐시 사용 절감액을 비교해야 한다. 캐시를 만들어두고 한 번만 쓰면 오히려 손해다. 최소한 저장 비용을 초과할 만큼 히트가 발생해야 한다.

```
절감액 = 히트 횟수 × 토큰 수 × (입력 단가 - 캐시 단가)
저장 비용 = TTL 시간 × 토큰 수 × 시간당 저장 단가

절감액 > 저장 비용인 경우에만 이득
```

## Anthropic vs Gemini 비교

| 항목 | Anthropic | Gemini |
|---|---|---|
| 캐시 생성 방식 | 요청 시 `cache_control` 마크업 | 사전 캐시 객체 생성 |
| TTL 기본값 | 5분 | 수동 지정 (분~시간) |
| 최소 토큰 | 1,024~2,048 | 32,768 |
| 캐시 히트 할인 | 90% | 75% |
| 캐시 쓰기 추가 비용 | +25% (1.25×) | 없음 (저장 비용 별도) |
| 저장 비용 | 없음 | 시간당 토큰 단위 과금 |
| 세션 간 재사용 | 불가 (prefix 매칭, 요청 단위) | 가능 (캐시 객체 이름으로 참조) |
| 멀티 사용자 공유 | 불가 | 가능 |

## 캐시 히트율을 높이는 프롬프트 구조 패턴

### 기본 원칙: 고정 → 동적 순서

Anthropic은 prefix 매칭 방식이라 앞부분이 달라지면 뒤는 전부 미스다. 변하지 않는 내용을 앞에, 자주 바뀌는 내용을 뒤에 배치해야 한다.

```
캐시 효과 있는 순서:
1. system prompt (정적, 자주 안 바뀜)        → cache_control 부착
2. 참조 문서 / 코드베이스 스냅샷 (정적)      → cache_control 부착
3. tools 정의 (세션 내 고정)                 → cache_control 부착 가능
4. 이전 대화 내역 (점진적으로 누적)           → 마지막 turn에 cache_control
5. 현재 사용자 메시지 (매번 다름)             → cache_control 없음
```

### 멀티턴 대화 패턴

에이전트 루프에서 턴마다 마지막 `tool_result`에 `cache_control`을 붙이는 패턴이 효율적이다.

```python
messages = []

for turn in range(max_turns):
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }],
        tools=TOOLS,
        messages=messages,
    )

    if response.stop_reason != "tool_use":
        break

    tool_block = next(b for b in response.content if b.type == "tool_use")
    result = execute_tool(tool_block)

    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_block.id,
            "content": str(result),
            "cache_control": {"type": "ephemeral"}  # 다음 턴에서 여기까지 캐시됨
        }]
    })
```

2번째 턴부터 system prompt + 이전 대화 전체가 캐시 히트한다. 도구를 10번 호출하는 루프라면 9번의 캐시 히트가 발생한다.

### 대량 추출 패턴

같은 스키마로 수백 개 문서에서 데이터를 추출할 때 system prompt와 tool 정의가 캐시된다.

```python
# system + tools는 동일 → 두 번째 요청부터 캐시 히트
for doc in documents:
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{
            "type": "text",
            "text": "다음 문서에서 구조화된 데이터를 추출해라...",
            "cache_control": {"type": "ephemeral"}
        }],
        tools=EXTRACTION_TOOLS,
        messages=[{"role": "user", "content": doc}],  # 문서만 바뀜
    )
```

## 캐시가 무효화되는 케이스

### 1. 프롬프트 내 동적 값 삽입

가장 흔한 실수다. 타임스탬프, 요청 ID, 세션 ID를 system prompt 안에 넣으면 매 요청마다 prefix가 달라진다.

```python
# 캐시 미스 발생
system_prompt = f"현재 시각: {datetime.now()}. 당신은 주문 처리 전문가다..."

# 캐시 히트 가능
system_prompt = "당신은 주문 처리 전문가다..."
# 동적 정보는 user 메시지로 분리
user_message = f"현재 시각 {datetime.now()} 기준으로 ORD-12345 확인해줘"
```

### 2. Tools 배열 순서 변경

tools 정의를 동적으로 만들면 순서가 매 요청마다 달라질 수 있다. set이나 dict에서 변환하면 순서 보장이 안 된다.

```python
# 순서 불안정 → 캐시 미스
tools = list({tool for tool in get_available_tools()})

# 순서 고정 → 캐시 히트 가능
tools = sorted(get_available_tools(), key=lambda t: t["name"])
```

### 3. TTL 초과 후 재생성

5분 TTL 안에 동일 prefix로 요청이 오지 않으면 캐시가 사라진다. 배치 작업에서 작업 간격이 5분을 넘으면, 다음 작업에서 캐시를 다시 쓴다. `cache_creation_input_tokens`가 갑자기 올라가면 TTL 만료 신호다.

```python
# 로그로 TTL 만료 추적
if usage.cache_creation_input_tokens > 0 and usage.cache_read_input_tokens == 0:
    logger.warning("캐시 재생성 발생 - TTL 만료 또는 prefix 변경")
```

### 4. 대화 내역 중간 수정

이전 대화 내역에서 메시지를 삭제하거나 요약으로 대체하면, 그 시점 이후의 prefix가 깨진다.

```python
# 이렇게 하면 캐시 무효화
messages.pop(2)  # 중간 메시지 삭제 → 이후 모든 메시지의 prefix가 변경됨

# 대화가 길어지면 앞에서 잘라야 하는데, 자르는 순간 캐시는 새로 시작한다
# 긴 대화에서는 캐시 경계를 다시 잡아야 한다
```

### 5. 모델 버전 변경

`claude-opus-4-7`과 `claude-opus-4-8`은 별도 캐시를 가진다. 배포 중에 모델 버전이 바뀌면 그 시점에 캐시가 전부 미스로 돌아간다.

### 6. 최소 토큰 미달

Opus에서 2,048 토큰 미만의 system prompt를 캐싱하려 해도 캐시가 생성되지 않는다. `cache_creation_input_tokens`가 0이면 미달 여부를 확인해봐야 한다.

```python
# 캐시 생성 실패 진단
if usage.cache_creation_input_tokens == 0 and usage.cache_read_input_tokens == 0:
    # cache_control을 붙였음에도 캐시가 없는 상태
    # → 토큰 수가 최소 기준 미달이거나 prefix가 이전 요청과 다른 것
    total_input = count_tokens(system_prompt + str(messages))
    if total_input < 2048:  # Opus 기준
        logger.warning(f"캐시 최소 토큰 미달: {total_input}")
```

### 7. Gemini: 캐시 TTL 만료 후 참조

Gemini에서 캐시 객체를 생성한 뒤 TTL이 지나면 그 이름으로 더 이상 참조할 수 없다. 장시간 돌아가는 서비스라면 캐시 갱신 로직이 필요하다.

```python
import time

def get_or_refresh_cache(cache_name, ttl_hours=1):
    try:
        cache = caching.CachedContent.get(cache_name)
        # 만료 임박 시 갱신
        remaining = (cache.expire_time - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        if remaining < 300:  # 5분 이내 만료 예정
            cache.update(ttl=datetime.timedelta(hours=ttl_hours))
        return cache
    except Exception:
        # 만료된 경우 재생성
        return create_cache(ttl_hours)
```

## 실무 관찰

Anthropic Prompt Caching은 에이전트 루프에서 비용 절감 효과가 가장 두드러진다. 도구를 10번 호출하는 작업이라면 2번째 호출부터 캐시가 적용되고, 입력 토큰이 많을수록 절감액이 커진다. system prompt가 5,000토큰이고 대화 내역이 누적 10,000토큰이라면, 캐시 없이 10번 호출 시 입력 비용의 대부분을 반복해서 낸다.

반면 단순 Q&A처럼 요청마다 내용이 완전히 다른 패턴에서는 캐시 효과가 없다. 시스템 프롬프트만 짧게 캐싱해봐야 절감액이 미미하다.

Gemini Context Caching은 공통 문서를 여러 사용자가 공유 참조하는 RAG 패턴에 맞다. 1M 토큰 짜리 코드베이스를 캐시해두고 팀원 여러 명이 질의하는 구조에서는 저장 비용보다 절감액이 훨씬 크다. 단, 최소 32,768토큰이라는 기준 때문에 짧은 문서에는 적용이 안 된다.

캐시 히트율 모니터링은 필수다. 의도한 대로 캐시가 작동하는지는 로그를 보기 전까지 알 수 없다. `cache_read_input_tokens`를 요청별로 기록하고, 갑자기 0이 되는 시점을 추적하면 무효화 원인을 빠르게 찾을 수 있다.
