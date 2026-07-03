---
title: Ollama로 로컬 LLM 서빙하기 - 운영 실무
tags: [ai, llm, ollama, local-llm, gguf, self-hosting, vllm]
updated: 2026-06-22
---

# Ollama

## 1. Ollama가 뭘 해주는 도구인지부터

Ollama는 로컬 머신에서 LLM을 돌리는 일을 `docker run` 수준으로 단순화한 런타임이다. 내부적으로는 llama.cpp를 엔진으로 쓰고, 그 위에 모델 다운로드/버전 관리/REST API 서버를 얹어놨다. 직접 llama.cpp를 빌드하고 GGUF 파일을 받아서 `--n-gpu-layers` 같은 플래그를 손으로 맞춰본 적 있으면, Ollama가 그 과정을 통째로 감춰준다는 게 바로 와닿는다.

핵심은 두 가지다. 하나는 모델을 이미지처럼 다루는 레지스트리 개념(`ollama pull llama3.2`), 다른 하나는 백그라운드 데몬이 11434 포트로 HTTP API를 열어준다는 점이다. 이 두 개 덕분에 "노트북에서 모델 한번 띄워보기"부터 "사내 서버에 추론 엔드포인트 깔기"까지 같은 도구로 커버된다.

주의할 건 Ollama는 단일 노드 추론 도구라는 점이다. 멀티 GPU 한 대에서 모델을 쪼개 올리는 것까지는 되지만, 여러 노드에 걸친 분산 서빙이나 대규모 동시 트래픽 처리는 설계 목표가 아니다. 이 경계를 넘어가면 vLLM 같은 도구로 갈아타야 하는데, 그 판단 기준은 뒤에서 따로 정리한다.

---

## 2. 설치와 첫 실행

macOS/Linux는 설치 스크립트 한 줄이면 끝난다.

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# 설치되면 systemd 서비스로 데몬이 자동 등록된다
systemctl status ollama
```

설치 후 모델을 받아서 바로 띄워본다.

```bash
# 모델 다운로드 + 대화형 실행
ollama run llama3.2

# 다운로드만 (실행 안 함)
ollama pull qwen2.5:7b

# 받아놓은 모델 목록
ollama list
```

`ollama run`은 모델이 없으면 먼저 받고 나서 REPL을 띄운다. 모델 태그는 `이름:파라미터수-양자화` 형태인데, 태그를 생략하면 기본값이 붙는다. `llama3.2`는 사실상 `llama3.2:3b-instruct-q4_K_M`을 가리킨다. 운영 환경에 깔 때 태그를 명시하지 않으면 나중에 기본 태그가 바뀌어 다른 양자화 모델이 받아지는 사고가 난다. 항상 풀 태그를 박아야 한다.

```bash
# 이렇게 박아라
ollama pull qwen2.5:7b-instruct-q4_K_M
```

데몬은 기본적으로 `127.0.0.1:11434`에만 바인딩된다. 다른 머신에서 붙어야 하면 환경변수로 바인딩 주소를 바꾼다.

```bash
# systemd 환경이면 override로 넣는다
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

이렇게 0.0.0.0으로 열 거면 앞단에 리버스 프록시나 방화벽을 반드시 둬라. Ollama 자체에는 인증이 없다. 11434를 외부에 그대로 노출하면 누구나 모델을 호출하고 GPU를 점유한다. 사내망이라도 그냥 열어두면 안 된다.

---

## 3. 모델 저장 구조와 GGUF 로딩

### 3.1 모델이 어디에 어떻게 저장되나

받은 모델은 `~/.ollama/models`(Linux는 `/usr/share/ollama/.ollama/models`)에 저장된다. 구조는 도커 레이어와 비슷하다.

```
~/.ollama/models/
├── blobs/          # 실제 가중치 데이터 (sha256 해시 파일명)
└── manifests/      # 모델 메타데이터, 어떤 blob들을 조합하는지
```

같은 베이스 모델을 공유하는 변종이 여러 개여도 blob은 중복 저장되지 않는다. 디스크 용량을 볼 때 `ollama list`의 합산 크기와 실제 디스크 사용량이 안 맞는 이유가 이거다.

모델 저장 경로를 바꾸려면 `OLLAMA_MODELS` 환경변수를 쓴다. 루트 디스크가 작고 데이터 디스크가 따로 있는 서버에서는 거의 필수다.

```bash
Environment="OLLAMA_MODELS=/data/ollama/models"
```

### 3.2 직접 받은 GGUF 파일 올리기

허깅페이스에서 받은 GGUF나 직접 양자화한 GGUF를 Ollama에 등록하려면 Modelfile을 쓴다. 도커파일과 비슷한 포맷이다.

```dockerfile
# Modelfile
FROM ./my-model-Q4_K_M.gguf

# 프롬프트 템플릿 (모델에 맞는 걸 넣어야 한다)
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.7
PARAMETER num_ctx 8192
PARAMETER stop "<|im_end|>"
```

```bash
ollama create my-model -f Modelfile
ollama run my-model
```

여기서 제일 자주 터지는 게 TEMPLATE를 안 맞춰서 생기는 문제다. Ollama 레지스트리에서 받은 모델은 템플릿이 이미 박혀 있지만, raw GGUF를 직접 올리면 템플릿이 비어 있거나 기본값이 들어간다. 모델이 학습된 채팅 포맷(ChatML, Llama 포맷 등)과 TEMPLATE가 안 맞으면 응답이 이상하게 끊기거나 특수 토큰이 그대로 출력된다. 모델 카드에서 정확한 프롬프트 포맷을 확인하고 STOP 토큰까지 맞춰야 한다.

`num_ctx`는 컨텍스트 길이인데, 이걸 올리면 KV 캐시 메모리가 선형으로 늘어난다. 모델이 128K를 지원한다고 무턱대고 `num_ctx 131072`를 박으면 7B 모델이라도 KV 캐시만으로 수십 GB를 먹어서 OOM이 난다. 실제 필요한 만큼만 잡아야 한다.

---

## 4. 메모리 요구사항 - 이게 제일 중요하다

로컬 서빙에서 실패하는 대부분의 케이스는 메모리 계산을 안 해서 생긴다. 모델이 메모리에 안 올라가면 Ollama는 일부 레이어를 CPU로 떨어뜨리거나(GPU+CPU 혼합), 아예 전부 CPU로 돌린다. 둘 다 속도가 급격히 떨어진다.

### 4.1 가중치 메모리 어림 계산

양자화 레벨별 대략적인 메모리(가중치만, KV 캐시 별도)는 파라미터 수에 양자화 비트를 곱해서 잡는다.

| 양자화 | 비트/파라미터 | 7B 모델 | 14B 모델 | 32B 모델 | 70B 모델 |
|--------|--------------|---------|----------|----------|----------|
| Q4_K_M | ~4.5 | ~4.5GB  | ~9GB     | ~20GB    | ~42GB    |
| Q5_K_M | ~5.5 | ~5.5GB  | ~11GB    | ~24GB    | ~50GB    |
| Q8_0   | ~8.5 | ~7.5GB  | ~15GB    | ~35GB    | ~70GB    |
| F16    | 16   | ~14GB   | ~28GB    | ~64GB    | ~140GB   |

여기에 KV 캐시와 실행 오버헤드로 1~3GB를 더 잡아야 한다. 실무에서는 GPU VRAM의 80% 정도를 모델이 쓸 수 있는 한계선으로 본다. 24GB VRAM(RTX 4090, A10)이면 Q4 기준 14B까지는 편하게, 32B는 컨텍스트를 짧게 잡으면 빠듯하게 올라간다.

### 4.2 Q4_K_M이 기본인 이유

Ollama 기본 양자화가 Q4_K_M인 데는 이유가 있다. Q4 아래로 내려가면(Q3, Q2) 품질 저하가 체감되기 시작하고, Q5~Q8로 올려도 품질 개선이 메모리 증가폭에 비해 작다. 7B 모델 기준 Q4와 Q8의 품질 차이는 대부분의 실무 태스크에서 구분하기 어렵다. VRAM이 빠듯하면 Q4를 쓰고 모델 사이즈를 키우는 쪽이, 작은 모델을 Q8로 쓰는 것보다 거의 항상 낫다.

### 4.3 GPU에 다 안 올라갈 때

VRAM이 부족하면 Ollama는 일부 레이어를 RAM에 올리고 CPU로 계산한다(레이어 오프로딩). `ollama ps`로 현재 분배를 볼 수 있다.

```bash
ollama ps
# NAME            ID    SIZE    PROCESSOR        UNTIL
# qwen2.5:14b     ...   11 GB   38%/62% CPU/GPU  4 minutes from now
```

`38%/62% CPU/GPU`는 가중치의 38%가 CPU(RAM)에, 62%가 GPU에 올라갔다는 뜻이다. 이 상태면 추론 속도가 GPU 전용 대비 5~10배 느려진다. CPU 메모리 대역폭이 병목이라 코어 수를 늘려도 별로 안 빨라진다. 토큰 생성이 답답할 정도로 느리면 십중팔구 이 오프로딩 상태다. `ollama ps`부터 확인해라.

오프로딩을 피하려면 더 작은 모델이나 더 낮은 양자화를 쓰거나, `num_ctx`를 줄여서 KV 캐시 공간을 확보하는 수밖에 없다.

---

## 5. OpenAI 호환 API

운영 입장에서 Ollama의 제일 쓸모 있는 부분이다. `/v1/chat/completions` 엔드포인트가 OpenAI API와 호환되어서, 기존 OpenAI SDK 코드를 base_url만 바꿔서 그대로 붙일 수 있다.

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # 아무 문자열이나. 검증 안 함
)

resp = client.chat.completions.create(
    model="qwen2.5:7b-instruct-q4_K_M",
    messages=[
        {"role": "system", "content": "한국어로 간결하게 답한다."},
        {"role": "user", "content": "GGUF가 뭔지 한 문장으로 설명해줘"},
    ],
    temperature=0.7,
)
print(resp.choices[0].message.content)
```

스트리밍, 함수 호출(tool calling), 임베딩(`/v1/embeddings`)도 지원한다. 다만 호환이 100%는 아니다. `logprobs`, 일부 샘플링 파라미터, OpenAI 전용 기능은 무시되거나 안 먹는다. 기존 코드를 그대로 옮길 때 이런 파라미터가 조용히 무시되는 걸 모르고 넘어가면 동작이 미묘하게 달라진다.

Ollama 네이티브 API(`/api/generate`, `/api/chat`)도 따로 있는데, 모델 로딩 제어(`keep_alive`)나 raw 프롬프트 모드 같은 세밀한 기능은 네이티브 쪽에만 있다. 운영 통합은 OpenAI 호환을 쓰고, 모델 라이프사이클 제어가 필요하면 네이티브를 섞어 쓰는 식이 된다.

### 5.1 모델 언로드 타이밍 제어

기본적으로 Ollama는 마지막 요청 후 5분간 모델을 메모리에 유지하고 그 뒤 내린다. 트래픽이 띄엄띄엄 들어오는 환경에서는 매번 5분 뒤에 언로드됐다가 다음 요청에서 다시 로딩되느라 첫 응답이 수 초씩 느려진다. 항상 떠 있어야 하는 서비스면 `keep_alive`를 무한으로 잡는다.

```bash
# 요청 시점에 지정
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [{"role":"user","content":"hi"}],
  "keep_alive": -1
}'

# 또는 환경변수로 전역 설정
# Environment="OLLAMA_KEEP_ALIVE=-1"
```

반대로 GPU를 여러 모델이 돌아가며 써야 하면 `keep_alive`를 짧게 잡아서 빨리 내리게 한다. 모델 스위칭이 잦은 환경에서 이걸 무한으로 두면 첫 모델이 VRAM을 안 놓아서 다음 모델 로딩이 실패한다.

---

## 6. 동시 요청 처리 한계

Ollama로 운영하다 트래픽이 늘면 제일 먼저 부딪히는 벽이다. 동작 방식을 정확히 알아야 한다.

관련 환경변수는 두 개다.

```bash
# 한 모델이 동시에 처리하는 요청 수 (배치 병렬)
Environment="OLLAMA_NUM_PARALLEL=4"

# 동시에 메모리에 올라가는 서로 다른 모델 수
Environment="OLLAMA_MAX_LOADED_MODELS=2"
```

`OLLAMA_NUM_PARALLEL`이 핵심이다. 이 값이 4면 한 모델이 요청 4개를 동시에 배치로 처리한다. 그런데 병렬 슬롯마다 KV 캐시 공간이 따로 필요하다. `num_ctx`가 8192이고 `NUM_PARALLEL`이 4면 KV 캐시를 8192×4 토큰분 잡는다. 이게 VRAM을 추가로 먹어서, 병렬도를 올리면 그만큼 메모리 여유가 있어야 한다. 무턱대고 올리면 OOM이 나거나 컨텍스트가 강제로 줄어든다.

5번째 요청부터는 큐에 쌓여서 앞 요청이 끝나길 기다린다. 즉 Ollama는 동시성이 낮은 환경(사내 도구, 개발용, 소규모 서비스)에는 충분하지만, 수십~수백 동시 요청이 들어오는 프로덕션 트래픽은 감당 못 한다. 배치 처리 효율도 vLLM 같은 전용 서빙 엔진보다 떨어진다.

기준을 잡자면, 동시 사용자가 한 자릿수에서 십몇 명 수준이고 응답이 약간 느려도 되는 내부용이면 Ollama로 충분하다. 그 이상으로 처리량과 지연시간을 쥐어짜야 하면 도구를 바꿔야 한다.

---

## 7. vLLM과의 비교 - 언제 갈아타나

둘 다 로컬 LLM을 서빙하지만 타겟이 완전히 다르다.

| 항목 | Ollama | vLLM |
|------|--------|------|
| 설계 목표 | 간편한 로컬 실행 | 고처리량 프로덕션 서빙 |
| 모델 포맷 | GGUF (양자화 위주) | 주로 FP16/AWQ/GPTQ (HF safetensors) |
| 동시 처리 | 낮음 (NUM_PARALLEL 기반) | 높음 (continuous batching) |
| 메모리 효율 | llama.cpp 수준 | PagedAttention으로 KV 캐시 최적화 |
| 셋업 난이도 | 낮음 (한 줄 설치) | 중간 (CUDA/의존성 맞춰야 함) |
| GPU 없이 실행 | 됨 (CPU 추론) | 사실상 GPU 전제 |
| 멀티 GPU/노드 | 단일 노드 한 대 | 텐서 병렬, 분산 서빙 지원 |

vLLM의 핵심은 continuous batching과 PagedAttention이다. continuous batching은 요청이 들어오고 끝나는 시점이 제각각이어도 빈 배치 슬롯을 실시간으로 채워서 GPU를 놀리지 않는다. Ollama의 고정 배치 방식보다 동시 요청 처리량이 몇 배 높다. PagedAttention은 KV 캐시를 페이지 단위로 관리해서 메모리 낭비를 줄인다.

판단 기준은 이렇게 잡는다.

- 노트북/개발 머신에서 모델 띄워서 테스트, 사내 소수 인원용 도구, GPU 없는 환경 → Ollama
- 프로덕션 트래픽, 동시 요청 수십 개 이상, 처리량/지연시간이 SLA에 걸림 → vLLM
- GGUF 양자화 모델을 꼭 써야 하고 VRAM이 빠듯함 → Ollama (vLLM은 양자화 지원이 제한적이고 메모리를 더 먹는다)

실무에서는 두 단계로 가는 경우가 많다. 프로토타입과 내부 검증은 Ollama로 빠르게 돌리고, 트래픽이 실제로 붙어서 처리량이 문제가 되는 시점에 같은 모델을 vLLM으로 옮긴다. Ollama로 검증한 모델 선택과 프롬프트는 그대로 가져갈 수 있어서 마이그레이션 비용이 크진 않다.

---

## 8. 운영하면서 실제로 겪는 문제들

**모델이 갑자기 CPU로 떨어진다.** 같은 모델인데 어제는 빠르고 오늘은 느리면 다른 모델이 VRAM을 점유했거나 `num_ctx`가 커진 요청이 들어와서 오프로딩이 일어난 거다. `ollama ps`로 확인하고, `OLLAMA_MAX_LOADED_MODELS`로 동시 로딩 모델 수를 제한해라.

**첫 요청만 유독 느리다.** `keep_alive` 만료로 모델이 언로드됐다가 재로딩되는 콜드 스타트다. 70B 모델은 디스크에서 VRAM으로 올리는 데만 수십 초 걸린다. 상시 서비스면 `OLLAMA_KEEP_ALIVE=-1`로 박아라.

**raw GGUF를 올렸더니 응답이 깨진다.** TEMPLATE와 STOP 토큰이 모델과 안 맞는 거다. 모델 카드의 채팅 포맷을 확인하고 Modelfile을 맞춰라. 이미 같은 모델이 Ollama 레지스트리에 있으면 그걸 받아서 `ollama show --modelfile`로 템플릿을 베끼는 게 빠르다.

```bash
ollama show --modelfile qwen2.5:7b
```

**디스크가 꽉 찬다.** 모델을 이것저것 받다 보면 blob이 쌓인다. `ollama list`로 안 쓰는 모델 확인하고 `ollama rm`으로 지운다. 32B, 70B 모델 몇 개면 수백 GB가 우습게 나간다.

**동시 요청이 큐에서 멈춘 것처럼 보인다.** `OLLAMA_NUM_PARALLEL` 한계를 넘어선 요청이 대기 중인 거다. 로그에 명시적 에러가 안 떠서 헷갈리는데, 요청이 그냥 느린 게 아니라 앞 요청을 기다리는 중이다. 동시성이 필요하면 병렬도를 올리되 VRAM 여유를 먼저 확인하고, 그래도 부족하면 vLLM을 검토해라.
