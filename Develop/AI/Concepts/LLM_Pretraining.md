---
title: LLM 사전학습 파이프라인
tags: [ai, llm]
updated: 2026-07-25
volatility: high
---

# LLM 사전학습 파이프라인

Karpathy가 2024년에 공개한 "Let's reproduce GPT-2" 영상과 nanoGPT 코드를 기준으로 쓴다. 수조 토큰 규모 학습의 전체 흐름을 알고 싶은 사람보다, "왜 학습이 터지는지", "데이터를 어떻게 준비하는지"가 궁금한 사람에게 맞춰 썼다.

---

## 1. 사전학습이 하는 일

사전학습의 목표는 단 하나다. 다음 토큰을 예측하는 것이다.

```
입력: "The transformer architecture was"
예측: "proposed"
```

이걸 수조 토큰에 반복하면, 모델은 언어 구조, 사실 관계, 추론 패턴을 전부 파라미터에 새긴다. 목적함수는 cross-entropy loss다.

```text
loss = -sum(log P(t_i | t_1, ..., t_{i-1})) / N
```

사전학습을 마친 base model은 대화를 못한다. "파이썬에서 파일 읽는 방법은?"이라고 물으면 "파이썬에서 파일 읽는 방법은? 자바에서는? C++에서는?"처럼 다음에 올 법한 텍스트를 그냥 이어쓴다. SFT와 RLHF가 필요한 이유다. 이 부분은 5장에서 다룬다.

---

## 2. 데이터 파이프라인

### 2.1 Common Crawl과 그 한계

대부분의 대형 LLM은 Common Crawl을 기반으로 한다. Common Crawl은 2008년부터 웹을 크롤링해서 쌓은 공개 데이터셋으로, 매달 수백 TB의 HTML 덤프가 쌓인다. 규모로는 타의 추종을 불허한다.

문제는 품질이다. 그냥 가져다 쓰면 스팸, 광고 복사본, 무의미한 반복 텍스트, SEO 쓰레기가 절반 이상이다. Karpathy는 GPT-2 재현 과정에서 HuggingFace의 FineWeb(Common Crawl 필터링 버전)을 썼는데, 필터링 전후로 모델 품질이 눈에 띄게 달랐다고 했다.

**데이터 소스 구성의 현실:**

| 소스 | 비율 (대략) | 특성 |
|------|------------|------|
| Common Crawl (필터링 후) | 50~70% | 주된 소스. 품질 편차 크다 |
| 코드 (GitHub 등) | 10~20% | 추론 능력에 직접 영향 |
| Wikipedia | 3~5% | 사실 관계가 깨끗하다 |
| 책 (Books3 등) | 5~15% | 긴 문맥 학습에 효과적 |
| 학술 논문 | 3~5% | 정제된 텍스트 |

코드 데이터를 섞는 건 단순히 코딩을 잘하게 만들려는 게 아니다. 코드는 구조화된 논리를 담고 있어서 수학적 추론, 단계별 문제 풀기 같은 능력 전반에 영향을 준다. GPT-3.5 이후 모델들이 GPT-3보다 추론이 좋아진 데는 코드 데이터 비율을 높인 영향도 있다.

### 2.2 품질 필터링

필터링은 크게 두 단계로 나뉜다.

**휴리스틱 필터**: 빠르고 비용이 없다. 구현은 단순하지만 쓰레기 데이터의 80%는 여기서 걸러진다.

```python
def heuristic_filter(text: str) -> bool:
    # 너무 짧거나 긴 문서 제거
    if len(text) < 200 or len(text) > 100_000:
        return False

    # 알파벳/한글 비율이 낮으면 제거 (URL 덩어리, 숫자만 있는 문서)
    alpha_ratio = sum(c.isalpha() for c in text) / len(text)
    if alpha_ratio < 0.5:
        return False

    # 반복 라인 비율이 높으면 제거
    lines = text.split('\n')
    unique_ratio = len(set(lines)) / len(lines)
    if unique_ratio < 0.8:
        return False

    # 특수문자 과다 문서 제거
    punct_ratio = sum(not c.isalnum() and not c.isspace() for c in text) / len(text)
    if punct_ratio > 0.3:
        return False

    return True
```

**모델 기반 필터**: fastText 분류기를 학습시켜서 "고품질 문서"와 "저품질 문서"를 구분한다. Wikipedia 문서를 positive 예시로, 랜덤 크롤 문서를 negative로 쓰는 방식이 흔하다. Karpathy는 GPT-2 재현에서 FineWeb이 이미 이 작업을 해줬기 때문에 직접 구현하지 않았지만, 자체 데이터셋을 구축하면 이 단계를 직접 해야 한다.

### 2.3 Deduplication

중복 제거는 데이터 파이프라인에서 가장 중요한 단계 중 하나다. 같은 텍스트가 학습 데이터에 여러 번 나타나면 모델이 그 텍스트를 과도하게 외운다. 개인정보가 담긴 문서가 중복으로 들어가면 모델이 그 정보를 생성하게 되는 문제도 있다.

중복 제거 방법은 세 가지다.

**Exact matching**: URL 또는 내용 해시가 완전히 동일한 문서를 제거한다. 가장 빠르고 단순하다. 완전히 동일한 복사본은 잡아내지만 약간 다른 버전은 통과한다.

**Near-duplicate detection (MinHash)**: MinHash + LSH(Locality Sensitive Hashing)로 문서를 signature로 변환하고, 유사도가 높은 쌍을 찾아낸다. 문서 하나를 2048개 이상의 shingle(n-gram 단위)로 쪼개고, 각 shingle에 여러 해시 함수를 적용해서 MinHash signature를 만든다.

```python
from datasketch import MinHash, MinHashLSH

def make_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for word in text.split():
        m.update(word.encode('utf-8'))
    return m

# Jaccard 유사도 0.8 이상인 문서를 중복으로 처리
lsh = MinHashLSH(threshold=0.8, num_perm=128)

for doc_id, text in documents:
    mh = make_minhash(text)
    duplicates = lsh.query(mh)
    if not duplicates:
        lsh.insert(doc_id, mh)
    # duplicates가 있으면 이 문서는 건너뜀
```

**Substring matching (Suffix Array)**: 문서 경계를 넘어서 반복되는 긴 문자열을 찾는다. 같은 뉴스 기사가 여러 사이트에 복사된 경우를 잡는 데 효과적이다. 구현 비용이 높아서 대규모 데이터셋에서는 MinHash를 먼저 쓰고 나서 Suffix Array로 보완하는 경우가 많다.

### 2.4 토크나이징

필터링, 중복 제거가 끝나면 텍스트를 토큰 ID 배열로 변환한다. GPT-2 재현에는 GPT-2의 BPE 토크나이저(vocab size 50,257)를 그대로 쓴다.

```python
import tiktoken
enc = tiktoken.get_encoding("gpt2")

# 문서 → 토큰 배열, <|endoftext|>로 문서 경계 표시
tokens = enc.encode_ordinary(text)
tokens.append(enc.eot_token)  # 50256
```

토큰화 결과를 `.npy` 파일로 저장해두고 학습 루프에서 메모리맵으로 읽는다. 데이터를 사전에 전부 토큰화해두지 않으면 학습 중 CPU에서 토큰화 병목이 생긴다.

---

## 3. 학습 안정성

### 3.1 Loss Spike가 발생하는 경우

사전학습 중 갑자기 loss가 치솟는 현상이 loss spike다. 10시간 학습하다가 loss가 2배로 뛰면 멘탈이 나간다. Karpathy도 재현 과정에서 이 문제를 여러 번 겪었다.

원인은 보통 세 가지다.

**데이터 품질 문제**: 특정 배치에 비정상적인 문서가 들어가는 경우다. 토큰이 10만 개짜리 문서가 배치에 끼면 loss가 폭발할 수 있다. 데이터 사전 검증 단계에서 최대 문서 길이를 제한해야 한다.

**Learning rate가 너무 큰 경우**: 학습 초반에 lr이 과도하면 loss가 발산한다. 특히 warmup 없이 전체 lr로 시작하면 초반 수백 스텝에서 loss가 오락가락한다.

**gradient exploding**: 특정 파라미터의 gradient가 매우 커져서 업데이트가 비정상적으로 이뤄지는 경우다. Gradient clipping으로 완화한다.

### 3.2 Gradient Clipping

gradient의 global norm이 threshold를 넘으면 스케일을 줄여서 적용한다.

```python
# 실제 학습 루프에서
loss.backward()
norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```

`max_norm=1.0`이 표준값이다. GPT-2, GPT-3 논문 모두 1.0을 쓴다. norm이 1.0을 초과하면 모든 gradient를 비율로 축소한다. 이 값을 너무 작게 설정하면 학습이 너무 느려지고, 너무 크면 clipping의 효과가 없어진다.

실제 norm 값을 로깅해두면 학습 안정성 진단에 쓸 수 있다. norm이 갑자기 10배 이상 뛰었다면 그 배치가 문제다.

```python
# norm을 로깅
if step % 100 == 0:
    writer.add_scalar('grad_norm', norm.item(), step)
```

### 3.3 Learning Rate Schedule

Karpathy는 GPT-2 재현에서 cosine decay with warmup을 썼다.

```python
def get_lr(step: int, warmup_steps: int, max_steps: int, max_lr: float, min_lr: float) -> float:
    # 1. Linear warmup
    if step < warmup_steps:
        return max_lr * (step + 1) / warmup_steps

    # 2. Min lr 이하로 떨어지지 않도록
    if step > max_steps:
        return min_lr

    # 3. Cosine decay
    decay_ratio = (step - warmup_steps) / (max_steps - warmup_steps)
    coeff = 0.5 * (1.0 + math.cos(math.pi * decay_ratio))
    return min_lr + coeff * (max_lr - min_lr)
```

GPT-2 124M 재현 기준 파라미터:

| 파라미터 | 값 |
|---------|---|
| max_lr | 6e-4 |
| min_lr | max_lr * 0.1 |
| warmup_steps | 715 (약 10%) |
| max_steps | 19073 |

warmup이 필요한 이유는 초반에 파라미터가 랜덤 초기화 상태라서 큰 lr을 바로 적용하면 학습 방향이 불안정하기 때문이다. 10~20%를 warmup에 쓰는 게 일반적이다.

### 3.4 Mixed Precision (BF16)

FP32로 학습하면 메모리가 두 배 이상 든다. A100/H100에서는 BF16이 사실상 표준이다.

```python
# PyTorch autocast 사용
with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
    logits, loss = model(x, y)
```

BF16은 FP16과 달리 FP32와 같은 지수 범위를 가져서 overflow가 거의 없다. 다만 V100 이전 GPU에서는 BF16이 지원되지 않는다. T4(AWS g4dn 인스턴스)에서는 FP16을 써야 하는데, 이 경우 GradScaler가 필요하다.

```python
# FP16이면 GradScaler 필요
scaler = torch.cuda.amp.GradScaler()
with torch.autocast(device_type='cuda', dtype=torch.float16):
    loss = model(x, y)
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

BF16 환경에서 loss가 nan으로 가면 대부분 loss scale 문제다.

### 3.5 Gradient Accumulation

배치 크기를 늘리고 싶은데 GPU 메모리가 부족할 때 쓴다. 여러 mini-batch의 gradient를 누적해서 한 번에 업데이트한다.

```python
grad_accum_steps = 8
optimizer.zero_grad()

for micro_step in range(grad_accum_steps):
    x, y = get_batch()
    with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
        logits, loss = model(x, y)
    loss = loss / grad_accum_steps  # 평균 낼 때 나누기
    loss.backward()

clip_grad_norm_(model.parameters(), 1.0)
optimizer.step()
```

Karpathy가 강조한 주의사항: `loss / grad_accum_steps` 나누는 걸 빠뜨리면 gradient가 accumulation 횟수만큼 커져서 학습이 불안정해진다.

---

## 4. 체크포인트 관리

### 4.1 저장 주기

수십 시간짜리 학습이 마지막 10분에서 죽으면 전부 날린다. 체크포인트는 충분히 자주 저장해야 한다.

```python
checkpoint_interval = 1000  # 1000 스텝마다

if step % checkpoint_interval == 0:
    checkpoint = {
        'step': step,
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict(),
        'config': model_config,
        'val_loss': val_loss,
    }
    torch.save(checkpoint, f'checkpoints/step_{step:06d}.pt')
```

optimizer state_dict를 같이 저장하지 않으면 재시작 후 학습 동작이 달라진다. Adam의 moment 추정값이 리셋되기 때문이다.

### 4.2 체크포인트 선택

학습 중 val_loss가 가장 낮은 체크포인트가 항상 최종 사용 모델이 아니다. Val_loss는 사전학습 데이터의 품질과 분포에 따라 달라지기 때문에, 다운스트림 태스크(코드 생성, QA 등)에서 직접 평가해서 고르는 게 맞다.

저장 공간이 문제라면 최근 N개만 남기는 방식을 쓴다.

```python
import glob
checkpoints = sorted(glob.glob('checkpoints/step_*.pt'))
if len(checkpoints) > 5:
    for old in checkpoints[:-5]:
        os.remove(old)
```

### 4.3 Resume

```python
resume_from = 'checkpoints/step_010000.pt'
checkpoint = torch.load(resume_from)

model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
start_step = checkpoint['step']

# 데이터 로더 위치도 맞춰야 한다
# 이미 본 데이터를 다시 보면 학습에 영향을 준다
data_loader.skip(start_step * batch_size)
```

데이터 로더 위치를 맞추는 부분을 빠뜨리는 경우가 많다. skip을 안 하면 초반 데이터를 두 번 본다.

---

## 5. Karpathy가 GPT-2 재현하면서 밝힌 실전 사항

### 5.1 Flash Attention

Karpathy는 nanoGPT에서 PyTorch의 `scaled_dot_product_attention`을 쓰면 Flash Attention이 자동으로 적용된다는 걸 보여줬다.

```python
# 이걸 쓰면
y = torch.nn.functional.scaled_dot_product_attention(
    q, k, v,
    attn_mask=None,
    dropout_p=self.dropout if self.training else 0,
    is_causal=True  # causal mask 자동 처리
)

# 이렇게 직접 구현하는 것보다 메모리를 훨씬 덜 쓰고 빠르다
att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(k.size(-1)))
att = att.masked_fill(self.bias[:,:,:T,:T] == 0, float('-inf'))
att = F.softmax(att, dim=-1)
y = att @ v
```

attention 행렬을 메모리에 올리지 않고 재계산하는 방식이라서, 시퀀스 길이가 길수록 메모리 절약 효과가 커진다. 4096 이상 컨텍스트에서는 사실상 필수다.

### 5.2 컴파일

PyTorch 2.0의 `torch.compile`은 첫 번째 포워드 패스에서 CUDA kernel fusion을 적용한다. Karpathy 측정 기준으로 A100에서 약 30% 속도 향상이 있었다.

```python
model = torch.compile(model)
```

첫 배치에서 컴파일 때문에 1~2분 걸린다. 그 이후부터 빨라진다. 컴파일 후 디버깅이 어려워지는 단점이 있어서, 모델 구조 확정 전까지는 꺼두는 게 낫다.

### 5.3 HellaSwag로 학습 진행 확인

Karpathy는 val_loss 외에 HellaSwag 정확도를 100 스텝마다 측정했다. HellaSwag는 4지선다형 상식 추론 문제 데이터셋으로, 추가 fine-tuning 없이 base model의 능력을 간단히 측정하는 데 쓴다.

val_loss가 내려가는데 HellaSwag 정확도가 안 올라가면 뭔가 문제가 있다는 신호다. loss는 토큰 단위 예측 지표이고, 실제 언어 이해 능력은 다운스트림 태스크에서만 보인다.

### 5.4 작은 것부터 검증하는 습관

Karpathy가 강조한 원칙: 전체 학습을 돌리기 전에 과적합 테스트를 먼저 한다. 배치 하나(32개 시퀀스)에 1000 스텝을 돌려서 loss가 0에 가깝게 떨어지는지 확인한다. 이게 안 되면 모델 구현이나 학습 루프에 버그가 있다는 뜻이다.

```python
# 과적합 테스트
for step in range(1000):
    x, y = fixed_batch  # 같은 배치만 반복
    logits, loss = model(x, y)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()
    if step % 100 == 0:
        print(f"step {step}: loss={loss.item():.4f}")

# loss가 0.01 이하로 떨어져야 정상
```

---

## 6. SFT와 RLHF 전환점

### 6.1 Base Model이 왜 직접 사용이 안 되는가

사전학습을 마친 모델은 "언어 패턴을 아는 상태"다. 질문을 받아도 대화 형식으로 응답하는 법을 모른다. 인터넷 텍스트에는 질문-답변 패턴보다 기사, 소설, 토론 텍스트가 훨씬 많아서, 모델이 "질문에는 답변이 따른다"는 걸 충분히 학습하지 못했다.

직접 테스트해보면 체감된다. GPT-2 base를 그대로 쓰면 "수도는 어디입니까?" 뒤에 "수도는 어디입니까? 국토부 관계자는..."처럼 기사체로 이어진다.

### 6.2 SFT가 행동을 바꾸는 방식

SFT는 데이터 양이 적어도 된다. InstructGPT 논문 기준으로 13K 정도의 (질문, 답변) 쌍이면 행동 패턴이 바뀐다. 단, 이 답변은 사람이 작성한 고품질 답변이어야 한다. 저품질 데이터로 SFT하면 base model보다 나빠질 수 있다.

SFT의 한계는 "좋은 답변과 나쁜 답변을 구분하는 능력"이 없다는 것이다. 그냥 주어진 답변 형식을 학습하는 것이지, "더 정확한 답변"을 추구하도록 만들지는 못한다.

### 6.3 RLHF와 DPO의 선택 기준

RLHF는 보상 모델을 별도로 학습시켜야 한다. 구현 복잡도가 높고, 보상 해킹(reward hacking) 문제가 생긴다. 보상 모델이 실제 품질이 아닌 형식적 특성(길이, 특정 단어 빈도)을 과도하게 반영하면 모델이 그걸 최대화하는 방향으로 가버린다.

DPO는 RLHF를 대체하기 위해 나왔다. (질문, 선호 답변, 비선호 답변) 형태의 데이터만 있으면 보상 모델 없이 직접 학습이 된다. 2024년 기준 공개 모델 대부분이 DPO 또는 그 변형(SimPO, ORPO)을 쓴다.

실무에서 선택 기준: 데이터가 충분하고 보상 모델 학습 인프라가 있으면 RLHF, 그게 아니라면 DPO가 현실적이다.

---

## 7. 규모별 실제 소요 자원

소규모 팀이 직접 사전학습을 한다면 GPT-2 수준(124M)이 현실적인 상한이다. 그 이상은 클라우드 비용이 급격히 올라간다.

| 모델 규모 | 토큰 수 | GPU (A100 기준) | 소요 시간 | 비용 (대략) |
|---------|---------|---------------|---------|-----------|
| GPT-2 124M | 10B | A100 1장 | 4시간 | $10 |
| GPT-2 124M | 100B | A100 8장 | 2일 | $200 |
| GPT-3 수준 (175B) | 300B | A100 1024장 | 수개월 | $수백만 |

Karpathy가 GPT-2를 재현한 실제 조건은 A100 8장, 약 1시간이었다. OpenAI가 원래 GPT-2를 학습시킬 때는 TPU v3를 사용했고, 그 비용을 A100 기준으로 환산하면 약 $40,000 수준으로 추산된다.

직접 사전학습 대신 base model을 가져와서 fine-tuning하는 게 현실적인 이유가 여기에 있다. LoRA나 QLoRA로 7B 모델을 도메인 특화 데이터로 fine-tuning하는 비용은 A100 1장 기준 수 시간 이내다.
