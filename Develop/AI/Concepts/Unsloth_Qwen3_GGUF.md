---
title: unsloth/Qwen3.6-27B-GGUF 로컬 구동
tags: [ai, llm, qwen, unsloth, gguf, llama-cpp, ollama, quantization, local-inference]
updated: 2026-04-24
---

# unsloth/Qwen3.6-27B-GGUF 로컬 구동

## 1. 왜 이 저장소를 골라야 하는가

Hugging Face에 올라온 Qwen3.6 27B 가중치를 그대로 받아서 쓰면 bf16 기준 약 54GB 짜리 safetensors 파일들이 내려온다. 이걸 로컬에서 돌리려면 H100 같은 80GB짜리 한 장이나 A6000 48GB 두 장을 묶어야 하고, 컨슈머 GPU에서는 아예 올라가지도 않는다. 그래서 개인 장비나 소규모 서버에서 Qwen3.6 27B를 만져보려면 양자화된 GGUF 버전이 거의 유일한 선택지가 된다.

`unsloth/Qwen3.6-27B-GGUF`가 눈에 띄는 이유는 세 가지다. 하나는 Unsloth가 Qwen 팀이 공식 배포한 체크포인트에서 토크나이저 특수 토큰과 chat template를 누락 없이 가져오는 편이라는 점, 다른 하나는 Q2_K부터 Q8_0까지 양자화 변형을 한 레포에 전부 몰아서 올려둬서 비교가 편하다는 점, 마지막은 Unsloth가 fine-tuning 워크플로우도 함께 제공해서 학습 → GGUF 변환 과정을 같은 팀 도구로 이어갈 수 있다는 점이다.

Qwen 팀이 직접 올리는 공식 GGUF(`Qwen/Qwen3.6-27B-GGUF`)도 있지만, 커뮤니티에서 Unsloth 빌드를 더 많이 쓰는 이유는 토크나이저 패치가 빠르게 반영되는 편이기 때문이다. 초기 공식 GGUF는 `<|im_start|>` 같은 특수 토큰을 BPE 합쳐서 내보내는 버그가 몇 번 있었는데, 그때마다 Unsloth 쪽이 하루 이틀 안에 재업로드를 해주는 걸 여러 번 봤다.

---

## 2. Qwen3.6 27B 모델 개요

구조부터 정리한다. 숫자를 정확히 알아야 VRAM 계산이 맞는다.

- 파라미터 수: 약 27B (정확히는 27.2B, active 파라미터도 27.2B로 dense 모델)
- 레이어: 64
- hidden size: 5120
- attention head: 40 (KV head 8, GQA 적용)
- context length: 공식 32K, YaRN 스케일링으로 131K까지 확장 지원
- vocab size: 151936 (Qwen3 계열과 동일한 토크나이저)
- 아키텍처: transformer decoder-only, RoPE, SwiGLU, RMSNorm
- MoE 여부: 아니다. Qwen3.6 계열에서 MoE는 A3B, A22B 같은 별도 모델이다. 27B는 dense다.

Qwen3 계열부터 들어온 특징 중 실무에서 체감되는 것들이 몇 개 있다.

하나는 `<think>...</think>` 블록을 내부적으로 사용하는 reasoning 모드다. Qwen3.6-27B는 reasoning 토글이 system prompt 또는 `enable_thinking` 인자로 제어된다. GGUF로 변환해도 chat template에 이 분기가 남아 있어서, `tokenizer_config.json`에 있던 template가 그대로 들어온다. reasoning을 끄고 싶으면 `enable_thinking=False`에 해당하는 플래그를 llama.cpp 쪽에 넘겨야 한다.

다른 하나는 GQA의 KV head 수가 8로 줄어든 점이다. 이게 중요한 이유는 context 길이 늘릴 때 KV cache 메모리가 head 수에 비례하기 때문인데, 64 레이어 × 5120 hidden × 8 KV head 기준으로 32K 컨텍스트에서 fp16 KV cache가 약 4GB 수준이다. 128K로 늘리면 16GB가 KV cache로만 날아간다. 이 숫자를 미리 계산해두지 않으면 긴 문서 요약을 돌리다가 OOM이 터지는 이유를 못 찾는다.

한국어 토큰화는 Qwen3 계열의 tiktoken-스타일 BPE를 그대로 쓴다. 한글 1글자가 대체로 1.5~2 토큰 정도로 쪼개지는데, 한자 병기된 문서는 오히려 1토큰으로 붙기도 한다. 이 특성 때문에 한국어 문서를 잘라서 입력할 때 영어 기준 토큰 수를 그대로 적용하면 실제로는 훨씬 빨리 32K를 넘긴다.

---

## 3. GGUF 포맷과 양자화가 실제로 하는 일

GGUF는 GPT-Generated Unified Format의 약자지만 이름은 중요하지 않다. 실제로는 llama.cpp가 쓰는 단일 파일 포맷이다. 텐서 가중치 + 메타데이터(토크나이저, chat template, 모델 하이퍼파라미터) + 양자화 스킴이 한 파일 안에 들어 있다. safetensors와 달리 별도의 `tokenizer.json`, `config.json`을 같이 들고 다닐 필요가 없다는 게 운영 관점에서 큰 장점이다.

양자화 스킴은 텐서 블록 단위로 스케일을 공유하는 방식으로 동작한다. Q4_K_M을 예로 들면, 32개 값마다 하나의 fp16 스케일을 공유하면서 개별 값은 4bit로 저장한다. K-quant 계열(Q2_K, Q3_K, Q4_K, Q5_K, Q6_K)은 super-block 구조를 쓰고, `_M`, `_S`, `_L` 접미사는 attention과 FFN 텐서 일부를 더 높은 정밀도로 남기는지에 대한 변형이다. 숫자가 같아도 `_M`이 `_S`보다 품질이 좋지만 용량은 조금 더 크다.

실무에서 기억해야 할 건 단순하다.

- Q2_K, Q3_K_S 같은 극단적 저정밀도는 27B 모델에서는 품질 손상이 확연히 보인다. 한국어 토크나이제이션 이슈랑 겹치면 반말/존댓말 섞임, 숫자 계산 틀어짐이 자주 나온다.
- Q4_K_M이 대부분의 경우 sweet spot이다. 품질 손상이 bf16 대비 3% 미만으로 측정되는 편이고, VRAM도 가장 현실적이다.
- Q6_K, Q8_0은 bf16과 거의 구분이 안 된다. 대신 용량 대비 이득이 작아서, VRAM이 남지 않는 이상 잘 안 쓴다.
- f16/bf16 GGUF는 사실상 원본이다. 양자화 전 디버깅 용도 외에는 GGUF로 쓸 이유가 없다.

---

## 4. 양자화 변형별 디스크/VRAM 요구량

`unsloth/Qwen3.6-27B-GGUF` 레포에 올라오는 파일들의 대략적인 크기다. 버전에 따라 몇백 MB 차이는 난다.

| Quant | 디스크 | 최소 VRAM (32K ctx) | 체감 품질 | 권장 환경 |
|-------|--------|---------------------|----------|----------|
| Q2_K | 약 10GB | 12GB | 명확히 떨어짐 | 4060 Ti 16GB, M1 Pro |
| Q3_K_M | 약 13GB | 15GB | 가벼운 작업 가능 | 4070 Ti 16GB |
| Q4_K_M | 약 16GB | 20GB | 원본 대비 미세 손상 | 4090 24GB, M2 Max 32GB |
| Q5_K_M | 약 19GB | 23GB | 거의 동일 | 4090 24GB 빡빡하게 |
| Q6_K | 약 22GB | 27GB | 동일 수준 | 5090 32GB, A6000 48GB |
| Q8_0 | 약 28GB | 33GB | 동일 | A6000 48GB, M3 Ultra |
| bf16 | 약 54GB | 60GB | 원본 | A100/H100 |

VRAM 요구량은 모델 가중치 + KV cache + 작업 버퍼의 합이다. 위 표는 32K 컨텍스트를 fp16 KV cache로 잡았을 때의 값이고, `-ctk q8_0 -ctv q8_0` 옵션으로 KV cache를 양자화하면 2~3GB 정도 절약된다. 다만 KV cache 양자화는 긴 문서 요약에서 약간의 품질 저하가 있으니 무조건 켤 일은 아니다.

Mac의 경우 unified memory라 "VRAM"이 아니라 "시스템 메모리에서 할당 가능한 양"이 기준이 된다. M2 Max 32GB에서 Q4_K_M은 돌아가지만 브라우저를 많이 열어놓은 상태면 swap이 시작되면서 tokens/sec이 1/5로 떨어진다. Metal은 `wired memory limit`을 기본 18GB 정도로 잡기 때문에, `sudo sysctl iogpu.wired_limit_mb=28000` 같은 명령으로 한도를 올려줘야 실제로 쓸 만해진다.

---

## 5. llama.cpp로 로딩하는 기본 흐름

llama.cpp는 이 생태계의 뿌리에 있는 구현이고, Ollama, LM Studio, llama-cpp-python 모두 내부적으로 llama.cpp 바이너리나 라이브러리를 쓴다. 직접 빌드해서 써보는 게 이해가 가장 빠르다.

```bash
# CUDA 빌드
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j

# Metal 빌드 (Mac)
cmake -B build -DGGML_METAL=ON
cmake --build build --config Release -j
```

모델 다운로드는 huggingface-cli 한 줄이면 된다.

```bash
huggingface-cli download \
  unsloth/Qwen3.6-27B-GGUF \
  Qwen3.6-27B-Q4_K_M.gguf \
  --local-dir ./models
```

기본 실행은 이렇다.

```bash
./build/bin/llama-cli \
  -m ./models/Qwen3.6-27B-Q4_K_M.gguf \
  -ngl 99 \
  -c 32768 \
  -n 512 \
  --temp 0.7 \
  --top-p 0.8 \
  --top-k 20 \
  -p "서울의 지하철 2호선에 대해 설명해줘."
```

주의할 옵션 몇 가지만 짚고 넘어간다.

- `-ngl` (n_gpu_layers): GPU에 올릴 레이어 수. 99를 주면 전부 GPU로 올린다. VRAM이 부족하면 이 값을 40, 50 식으로 줄여서 일부만 GPU에 올리고 나머지는 CPU로 돌린다. 이걸 offload라고 부르고, CPU로 내려가는 레이어가 많을수록 tokens/sec이 급격히 떨어진다.
- `-c` (context size): 32768까지는 안전하고, 그 이상은 YaRN 스케일링이 필요하다. `--rope-scaling yarn --yarn-orig-ctx 32768` 같은 옵션을 추가해야 131K 컨텍스트가 제대로 동작한다.
- `-fa` (flash attention): CUDA 빌드에서 켜면 긴 컨텍스트에서 속도가 눈에 띄게 올라간다. Metal에서는 자동이다.
- `--chat-template`: GGUF 안에 template가 들어있으니 보통은 지정할 필요 없다. 하지만 Qwen3 계열에서 `<think>` 토글을 수동으로 제어하려면 `--jinja` 플래그와 함께 커스텀 template를 넘겨야 할 때가 있다.

---

## 6. Ollama, LM Studio, llama-cpp-python 예제

### 6.1 Ollama

Ollama는 GGUF를 Modelfile로 감싸서 쓰는 래퍼다. 이미 다운받은 Unsloth GGUF를 등록하려면 Modelfile을 쓴다.

```
FROM ./models/Qwen3.6-27B-Q4_K_M.gguf

PARAMETER num_ctx 32768
PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 20
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"

TEMPLATE """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
"""
```

그리고 등록한다.

```bash
ollama create qwen3.6-27b -f Modelfile
ollama run qwen3.6-27b "한국의 장마철 강수 패턴을 설명해줘."
```

Ollama를 그냥 `ollama pull qwen3.6:27b`로 받으면 Ollama 레지스트리에 올라온 버전이 내려오는데, 이건 Unsloth 빌드가 아니라 Ollama 팀이 재패키징한 버전이다. 토크나이저 패치 이슈가 있을 때는 Unsloth GGUF를 직접 Modelfile로 등록하는 게 낫다.

### 6.2 LM Studio

LM Studio는 GUI 기반이고 Hugging Face에서 직접 검색해서 받는 방식이라 가장 진입 장벽이 낮다. 검색창에 `unsloth Qwen3.6 27B GGUF`라고 치면 양자화 변형이 드롭다운으로 뜨고, 그중 하나를 고르면 된다. 내부적으로는 llama.cpp를 쓰지만 binding이 조금 오래된 경우가 있어서, 최신 모델을 돌릴 때는 앱을 먼저 최신 버전으로 올려야 한다. 특히 Qwen3 계열의 `<think>` 블록 파싱은 LM Studio 0.3.x 중반 이후 버전에서 정상 처리된다.

### 6.3 llama-cpp-python

API로 붙이거나 스크립트에서 호출할 때 쓴다.

```python
from llama_cpp import Llama

llm = Llama(
    model_path="./models/Qwen3.6-27B-Q4_K_M.gguf",
    n_ctx=32768,
    n_gpu_layers=99,
    n_threads=8,
    flash_attn=True,
    verbose=False,
)

messages = [
    {"role": "system", "content": "너는 친절한 한국어 어시스턴트다."},
    {"role": "user", "content": "GGUF 포맷이 safetensors와 뭐가 다른지 설명해줘."},
]

output = llm.create_chat_completion(
    messages=messages,
    temperature=0.7,
    top_p=0.8,
    top_k=20,
    max_tokens=1024,
)
print(output["choices"][0]["message"]["content"])
```

`create_chat_completion`은 내부에서 GGUF 메타데이터에 들어있는 chat template을 jinja로 렌더링해서 prompt를 조립한다. 이 점이 `__call__` 방식과의 차이인데, 수동으로 prompt를 만들다 보면 `<|im_start|>` 토큰을 빼먹거나 순서를 틀리게 넣어서 모델이 이상하게 답하는 경우가 많다. 특별한 이유 없으면 chat completion 인터페이스를 쓰는 게 안전하다.

---

## 7. 환경별 성능 수치

실제 경험한 대략적인 값이다. 프롬프트 길이, 배치, 빌드 옵션에 따라 30%씩은 움직인다.

| 환경 | 양자화 | prefill (tok/s) | decode (tok/s) | 메모 |
|------|-------|----------------|---------------|------|
| RTX 4090 24GB + CUDA | Q4_K_M | 1800 | 38 | 32K ctx, flash attn 켬 |
| RTX 4090 24GB + CUDA | Q5_K_M | 1600 | 32 | 32K ctx, KV cache fp16 |
| RTX 5090 32GB + CUDA | Q6_K | 2400 | 55 | 32K ctx |
| A6000 48GB + CUDA | Q8_0 | 1400 | 28 | 여유 있게 돌아감 |
| M3 Max 64GB + Metal | Q4_K_M | 450 | 18 | wired limit 조정 필요 |
| M3 Ultra 128GB + Metal | Q8_0 | 700 | 25 | 긴 컨텍스트도 swap 없음 |
| Ryzen 7950X + 64GB RAM (CPU only) | Q4_K_M | 80 | 2.5 | 실용적이진 않음 |
| Threadripper 7980X + 256GB (CPU) | Q4_K_M | 180 | 5 | 배치로 돌리면 쓸만함 |

decode 속도가 tokens/sec 20 이하로 떨어지면 대화형 용도로는 답답해지기 시작한다. 일반적으로는 30 이상을 목표로 잡고 양자화를 결정하는 편이다.

prefill(입력 프롬프트 처리)은 GPU에서는 수천 토큰을 몇 초 안에 소화하지만, CPU only로 가면 긴 문서 요약이 사실상 불가능해진다. 16K 컨텍스트 하나 처리하는 데 2~3분이 걸린다. 이 차이 때문에 RAG 파이프라인에서 retrieval로 컨텍스트를 줄여서 넣는 게 CPU 환경에서는 필수다.

---

## 8. 실무에서 자주 만나는 문제들

### 8.1 OOM: 그런데 여유 VRAM이 있다고 찍힌다

Q4_K_M이 16GB인데 24GB GPU에서 OOM이 난다면 십중팔구는 KV cache다. llama.cpp가 `n_ctx`만큼의 KV를 미리 잡기 때문에, 32K 컨텍스트를 요청하면 모델 외에 4GB가 추가로 잡힌다. 거기에 CUDA graph buffer, cuBLAS workspace까지 합치면 5~6GB가 추가로 필요하다.

해결은 세 가지다. 컨텍스트를 줄이거나 (`-c 16384`), KV cache를 양자화하거나 (`-ctk q8_0 -ctv q8_0`), 일부 레이어를 CPU로 offload하거나 (`-ngl 50` 식). 나는 보통 순서대로 시도한다. 컨텍스트 줄여서 해결되면 그게 제일 싸게 먹히기 때문이다.

### 8.2 컨텍스트 길이 초과: 32K로 설정했는데 답이 중간에 끊긴다

두 가지 경우가 있다. 하나는 실제로 입력이 32K를 넘은 경우다. 한국어 기준으로 A4 30페이지 정도 되면 이미 30K에 근접한다. 입력 토큰 수를 세려면 `llama-tokenize` 유틸을 쓴다.

```bash
./build/bin/llama-tokenize \
  -m ./models/Qwen3.6-27B-Q4_K_M.gguf \
  -p "$(cat 문서.md)" \
  --show-count
```

다른 하나는 YaRN 없이 32K를 넘겼을 때 품질이 확 떨어지는 현상이다. Qwen3.6은 32K를 기본으로 훈련됐고 YaRN rope scaling으로 131K까지 확장을 지원하는데, 이걸 안 켜면 32K 근처부터 모델이 횡설수설하기 시작한다. `--rope-scaling yarn --yarn-orig-ctx 32768` 옵션을 반드시 같이 넣어야 한다.

### 8.3 한국어 토큰화 이슈

Qwen3 계열의 vocab은 중국어와 영어가 주력이고, 한국어는 BPE 분할 비율이 상대적으로 높다. "괜찮아"가 3 토큰, "안녕하세요"가 4 토큰 식으로 쪼개진다. 이 때문에 두 가지 문제가 생긴다.

하나는 출력 속도가 영어 대비 체감상 느리게 느껴진다는 점이다. tokens/sec은 같아도 한국어는 한 "글자"를 만드는 데 더 많은 토큰이 필요하니, characters/sec으로 바꿔 보면 영어의 60% 수준이다.

다른 하나는 특수 기호, 이모지, 구두점이 섞인 한국어에서 종종 이상한 토큰을 뱉는다는 점이다. "~" 물결 기호나 "…" 말줄임표에서 일부 Q2_K, Q3_K 양자화 버전이 UTF-8 바이트 중간에서 디코딩이 깨지는 경우를 봤다. 해결책은 양자화를 Q4_K_M 이상으로 올리는 것이고, 그래도 재현되면 stop 토큰을 명시해서 응답을 조기 종료시켜 회피한다.

### 8.4 Ollama가 컨텍스트를 내 설정대로 안 잡는다

Ollama는 `OLLAMA_CONTEXT_LENGTH` 환경변수나 Modelfile의 `PARAMETER num_ctx`를 무시하고 기본 2048로 잡는 버그가 여러 번 있었다. 현재 버전에서는 Modelfile 설정이 우선이지만, 변경을 적용하려면 `ollama rm` 후 `ollama create`로 모델을 다시 등록해야 한다. 단순히 Modelfile만 수정해서는 반영되지 않는다.

### 8.5 `<think>` 블록이 출력에 그대로 섞여 나온다

Qwen3.6은 reasoning 모드가 기본 켜져 있어서, `<think>...</think>` 안에 내부 추론 과정을 뱉는다. 이걸 사용자에게 바로 보여주면 UX가 엉망이 되니, 후처리로 제거하거나 애초에 끄는 게 낫다. chat template에서 `enable_thinking=False`에 해당하는 플래그를 넘기면 되고, llama-cpp-python에서는 `chat_template_kwargs`로 전달한다.

```python
output = llm.create_chat_completion(
    messages=messages,
    chat_template_kwargs={"enable_thinking": False},
)
```

다만 reasoning을 끄면 코드 생성이나 수학 문제에서 정확도가 눈에 띄게 떨어진다. 상담용 챗봇이라면 꺼도 되지만, 기술 Q&A라면 켜두고 후처리하는 쪽을 택하는 게 맞다.

---

## 9. Unsloth로 fine-tuning하고 GGUF로 내보내는 파이프라인

Unsloth는 LoRA/QLoRA fine-tuning을 1/2 VRAM, 2배 속도로 돌리는 것을 목표로 한 라이브러리다. Qwen3.6 27B를 full fine-tuning하려면 A100 여러 장이 필요하지만, LoRA라면 4090 24GB 한 장에서도 가능하다.

전체 흐름은 학습 → LoRA merge → HF → GGUF 변환 → 양자화다.

```python
# 1. Unsloth로 학습
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen3.6-27B-bnb-4bit",
    max_seq_length=4096,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

# ... TrainingArguments, SFTTrainer 설정, train() ...

# 2. LoRA merge + HF 포맷 저장
model.save_pretrained_merged(
    "./qwen3.6-27b-merged",
    tokenizer,
    save_method="merged_16bit",
)
```

여기서 `save_method="merged_16bit"`는 LoRA를 base에 합쳐서 bf16 HF 체크포인트로 저장한다는 의미다. `merged_4bit`도 있지만 나중에 GGUF로 넘길 거면 16bit가 안전하다.

그 다음이 llama.cpp의 변환 스크립트다.

```bash
python llama.cpp/convert_hf_to_gguf.py \
  ./qwen3.6-27b-merged \
  --outfile qwen3.6-27b-custom-f16.gguf \
  --outtype f16
```

이 단계에서 토크나이저와 chat template가 GGUF 안으로 임베드된다. 스크립트가 Qwen3.6 아키텍처를 인식 못 하면 llama.cpp 쪽을 최신으로 업데이트해야 한다. 새 모델이 나온 직후에는 이 스크립트에 아키텍처 추가 PR이 며칠 늦게 머지되는 경우가 있다.

마지막이 양자화다.

```bash
./build/bin/llama-quantize \
  qwen3.6-27b-custom-f16.gguf \
  qwen3.6-27b-custom-Q4_K_M.gguf \
  Q4_K_M
```

Unsloth는 이 과정을 `save_pretrained_gguf` 한 줄로 감싸서 제공하기도 한다.

```python
model.save_pretrained_gguf(
    "./qwen3.6-27b-custom",
    tokenizer,
    quantization_method=["q4_k_m", "q5_k_m", "q8_0"],
)
```

편하긴 한데, 내부적으로는 위 세 단계를 순차 실행하는 것이고 중간에 실패하면 어디서 깨졌는지 파악하기 어렵다. 프로덕션 파이프라인을 짤 때는 각 단계를 따로 실행하는 게 디버깅이 쉽다.

---

## 10. API 서버로 붙일 때 주의할 점

로컬에서 CLI로 돌리는 것과 서버로 붙이는 건 완전히 다른 문제다. 동시 요청, 스트리밍, 컨텍스트 재사용, 모니터링이 한꺼번에 들어온다.

### 10.1 llama.cpp server

가장 가벼운 선택지다. 빌드된 바이너리를 `llama-server`로 띄우면 OpenAI 호환 API가 나온다.

```bash
./build/bin/llama-server \
  -m ./models/Qwen3.6-27B-Q4_K_M.gguf \
  -ngl 99 \
  -c 32768 \
  -np 4 \
  --host 0.0.0.0 \
  --port 8080 \
  --api-key sk-local
```

`-np 4`는 parallel slot 수다. 4개를 주면 동시에 4개의 요청을 처리할 수 있지만, 각 슬롯이 컨텍스트를 따로 잡기 때문에 VRAM이 4배 더 든다. 즉 32K × 4 = 128K 만큼의 KV cache 공간이 필요하다. 이 계산을 놓치면 3번째 요청에서 OOM이 터진다.

continuous batching은 자동으로 켜져 있다. prefill 단계에서 여러 요청의 토큰을 하나의 배치로 묶어 처리하기 때문에 단일 요청 대비 throughput이 2~3배로 올라간다. 대신 latency는 약간 늘어난다.

### 10.2 vLLM과 GGUF

vLLM은 GGUF 로딩을 실험적으로 지원한다. PagedAttention과 continuous batching이 들어있어서 throughput은 llama.cpp server보다 확연히 높지만, 몇 가지 제약이 있다.

하나는 vLLM이 GGUF를 내부적으로 dequantize해서 fp16으로 풀어 올린다는 점이다. 디스크에서는 Q4_K_M이 16GB여도, VRAM에 올라간 상태는 54GB bf16과 거의 같다. "GGUF를 썼으니 VRAM이 절약되겠지"라는 기대가 깨진다.

다른 하나는 K-quant 계열 중 일부는 아직 지원이 없다는 점이다. Q2_K, Q3_K 같은 극단적 양자화는 vLLM에서 돌다가 중간에 에러가 나는 경우가 있다. vLLM 환경에서는 어차피 fp16으로 풀 거라면 GGUF 대신 AWQ나 GPTQ 같은 GPU-native 양자화 포맷을 쓰는 게 맞는 선택이다.

정리하면, 소규모 동시성(1~10 QPS)에는 llama.cpp server, 대규모 동시성과 긴 컨텍스트에는 vLLM + AWQ/GPTQ, 이런 식으로 갈라 쓰는 게 현실적이다.

### 10.3 공통 주의점

프로덕션에 올릴 때 한 번씩은 물렸던 것들을 나열해둔다.

응답 스트리밍에서 `<think>` 블록이 그대로 흘러나오는 문제가 있다. 스트리밍 중에 `<think>`를 만나면 버퍼링하고 `</think>`까지 받아서 버린 다음 그 이후 토큰만 클라이언트로 보내야 한다. 이걸 안 하면 사용자가 내부 추론을 그대로 보게 된다.

stop 토큰을 제대로 명시하지 않으면 모델이 계속 다음 turn을 생성해버리는 경우가 있다. `<|im_end|>`, `<|endoftext|>`는 기본이고, chat template 특성에 따라 추가 토큰이 필요할 수 있다. 예상치 못한 다음 턴이 붙어나오면 stop 토큰 누락을 먼저 의심한다.

로드밸런서 뒤에 여러 인스턴스를 세워도 KV cache는 인스턴스마다 별개다. 같은 세션이 다른 인스턴스로 가면 prefill을 다시 해야 해서 latency가 튄다. sticky session이 필요하거나, prefix caching을 지원하는 서빙 엔진으로 옮겨야 한다. llama.cpp server는 최근 버전에서 prompt cache를 지원하지만, 디스크 기반이라 multi-instance에서 공유는 안 된다.

모델 로딩 시간이 길다. Q4_K_M 16GB GGUF를 SSD에서 VRAM으로 올리는 데만 20~40초가 걸린다. 무중단 배포를 하려면 blue-green으로 새 인스턴스가 완전히 warm up된 다음 기존 인스턴스를 내리는 순서를 지켜야 한다. health check를 단순히 프로세스 up 여부로 잡으면 아직 모델을 로드 중인 인스턴스에 트래픽이 들어가서 first request가 몇십 초 걸린다.

---

## 11. 정리

27B dense 모델을 로컬에서 돌리는 건 불과 2년 전만 해도 워크스테이션급 장비가 있어야 가능했다. 지금은 4090 한 장, 혹은 Mac Studio 한 대로 Qwen3.6 27B를 30 tokens/sec로 돌릴 수 있고, Unsloth가 제공하는 GGUF 빌드 덕분에 양자화 선택지도 풍부하다.

모델 선택은 단순하다. VRAM 24GB 근처라면 Q4_K_M이 가장 안전하고, 여유가 있으면 Q5_K_M, 넉넉하면 Q6_K다. Q2_K, Q3_K는 실험용이 아니면 피하는 편이 낫다. fine-tuning을 같이 할 거라면 Unsloth 학습 → `save_pretrained_gguf` 파이프라인을 그대로 따라가면 되고, 서빙은 동시성 규모에 따라 llama.cpp server와 vLLM 중에서 고르면 된다.

로컬 LLM이 프로덕션에서 쓸 만해진 시점이 이쯤이라고 본다. 클라우드 API가 안 맞는 조건(오프라인, 데이터 반출 불가, 비용 구조)이면 진지하게 검토할 만한 선택지다.
