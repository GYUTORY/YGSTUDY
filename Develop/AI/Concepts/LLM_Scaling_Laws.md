---
title: LLM 스케일링 법칙
tags: [ai, llm, scaling-laws, chinchilla, compute-optimal, emergent-capabilities, karpathy]
updated: 2026-07-25
volatility: high
---

# LLM 스케일링 법칙

Karpathy의 'State of GPT'(2023)에서 가장 실용적으로 다룬 주제가 스케일링 법칙이다. 모델을 크게 만드는 게 능사가 아니라, 주어진 compute 예산 안에서 파라미터와 학습 데이터를 어떻게 배분하느냐가 핵심이라는 얘기다.

---

## 1. 스케일링 법칙의 출발점: Kaplan vs Chinchilla

2020년 OpenAI의 Kaplan et al. 논문이 스케일링 법칙의 출발점이다. 핵심 주장은 "compute 예산이 고정되어 있을 때, 파라미터를 최대한 크게 키우고 데이터는 상대적으로 덜 써도 된다"는 것이었다. GPT-3(175B)가 이 법칙대로 설계됐다. 300B 토큰으로 175B짜리 모델을 학습시켰다.

2022년 DeepMind의 Chinchilla 논문(Hoffmann et al.)이 이걸 정면으로 반박했다. 같은 compute를 쓰면서 GPT-3보다 4배 작은 70B 모델에 1.4T 토큰을 먹였더니 GPT-3을 성능에서 앞질렀다. GPT-3이 파라미터 대비 데이터가 너무 적은, "under-trained" 상태였다는 게 결론이다.

Chinchilla 논문이 제시한 공식은 단순하다.

```
N_opt ≈ sqrt(C / 6)
D_opt ≈ sqrt(C / 6) × 20

N: 파라미터 수
D: 학습 토큰 수
C: 총 compute (FLOP)
```

파라미터 1개당 학습 토큰 약 20개가 Chinchilla-optimal이다. 1B 파라미터 모델이면 20B 토큰이 필요하고, 70B면 1.4T 토큰이 필요하다.

---

## 2. FLOP 계산: 학습 예산을 숫자로

"얼마나 큰 모델을 얼마나 긴 데이터로 학습시킬 수 있는가"는 보유한 GPU로 계산 가능하다.

학습 1번의 FLOP 추정식이다.

```
C = 6 × N × D

C: 총 FLOP
N: 파라미터 수
D: 학습 토큰 수
```

6이 붙는 이유는 forward pass(2N FLOP) + backward pass(4N FLOP)를 합친 값이기 때문이다.

실제 GPU 기준으로 계산해보면 이렇다.

```python
# A100 80GB 기준 학습 예산 계산
# fp16 이론상 312 TFLOP/s, 실제 utilization 35~40%

gpu_tflops = 312e12          # A100 fp16 이론값 (FLOP/s)
utilization = 0.38           # 실제 utilization
gpu_count = 64
training_days = 14

total_flop = gpu_tflops * utilization * gpu_count * (training_days * 86400)
# ≈ 1.1 × 10^21 FLOP

# Chinchilla-optimal 배분
import math
N_opt = math.sqrt(total_flop / 6)   # ≈ 13.5B 파라미터
D_opt = N_opt * 20                   # ≈ 270B 토큰
```

현실에서 utilization 35~40%를 넘기기가 힘들다. IO 병목, 통신 오버헤드, gradient sync 시간이 다 깎아먹는다. 논문에서 "우리는 A100 256장으로 2주 학습시켰다"는 문장이 나오면 이 계산식으로 C를 역산해서 모델 규모가 합리적인지 확인할 수 있다.

---

## 3. 파라미터 vs 데이터 vs 컴퓨트 트레이드오프

셋 중 어디에 돈을 쓸지가 실무 결정이다.

파라미터를 늘리면 모델 용량이 커져서 더 복잡한 패턴을 암기할 수 있다. 대신 inference 비용이 같이 올라간다. 70B를 서빙하는 것은 7B 서빙보다 GPU 비용이 10배다.

데이터를 늘리면 작은 모델도 잘 동작하게 만들 수 있다. Chinchilla 이후 흐름이 이쪽으로 갔다. Llama 2(70B)는 2T 토큰으로 학습해서 Chinchilla-optimal보다 더 많이 학습시켰다. 서빙할 때는 작고 잘 학습된 모델이 크고 덜 학습된 모델보다 practical하다.

compute를 늘리면 당연히 두 다 올린다. 하지만 compute는 GPU 수량과 전기값으로 결정되는 실물 제약이라, 배분 문제가 된다.

이 트레이드오프를 정리하면 아래와 같다.

| 선택지 | training 비용 | inference 비용 | 주 사용 사례 |
|--------|--------------|----------------|-------------|
| 파라미터 ↑ (과소 학습) | 중간 | 높음 | 일반적으로 비효율 |
| 파라미터 = Chinchilla-opt | 높음 | 낮음 | 서빙 중심 프로덕션 |
| 데이터 추가 (over-train) | 높음 | 낮음 | inference 집약적 서비스 |

Llama 모델이 compute-optimal보다 더 학습시키는 이유가 여기 있다. 학습은 한 번 하면 되지만 inference는 매 요청마다 발생한다. inference 비용을 줄이려면 작은 모델을 충분히 학습시키는 게 장기적으로 이득이다.

---

## 4. Emergent Capabilities: 왜 갑자기 나타나는가

Wei et al.(2022)의 emergence 논문은 "모델이 특정 크기를 넘으면 갑자기 능력이 생긴다"는 현상을 기록했다. 작은 모델에서는 0에 가깝던 성능이, 임계점을 넘는 순간 급격히 올라간다.

메커니즘을 직관적으로 설명하면 이렇다. 멀티 스텝 추론이 필요한 태스크는 각 단계가 모두 성공해야 최종 정답이 나온다. 예를 들어 세 자리 수 덧셈은 세 자릿수 각각의 덧셈 + carry 계산 + 결합이 전부 맞아야 한다. 모델이 각 서브태스크를 50% 확률로 맞히면, 세 단계가 모두 맞을 확률은 0.5³ = 12.5%다. 각 서브태스크 정확도가 80%면 전체는 51.2%로 올라간다. 서브태스크 정확도가 연속적으로 상승해도 복합 태스크는 threshold를 넘는 순간 갑자기 올라가는 것처럼 보인다.

2023년 Schaeffer et al.이 다른 각도에서 반론을 제기했다. 비선형 metric(예: exact match)을 쓸 때 emergence처럼 보이는 것이지, linear metric(partial credit)으로 보면 연속적으로 상승한다는 것이다. Karpathy는 이 두 관점 모두를 인정하면서 "emergence가 완전히 환상은 아니지만, metric 선택에 따라 과장될 수 있다"는 입장이다.

실무적으로 중요한 점은 이거다. 소형 모델에서 잘 안 되는 태스크를 포기하기 전에, 모델 크기를 키우거나 학습 데이터를 늘렸을 때 갑자기 동작할 가능성이 있다. 선형 보간으로 "이 모델은 이 태스크를 못 할 것"이라는 예측이 틀리는 케이스가 있다.

---

## 5. 실제 학습 예산 계산

팀에서 "70B 모델을 파인튜닝하고 싶다"는 요청이 들어왔을 때, 현실적인 compute 요구량을 계산하는 방법이다.

```python
def estimate_compute(param_b: float, tokens_b: float) -> dict:
    """
    param_b: 파라미터 수 (단위: 십억)
    tokens_b: 학습 토큰 수 (단위: 십억)
    """
    N = param_b * 1e9
    D = tokens_b * 1e9
    
    total_flop = 6 * N * D
    
    # A100 SXM 80GB 기준
    a100_fp16_tflops = 312e12
    utilization = 0.35
    effective_tflops = a100_fp16_tflops * utilization
    
    # 단일 GPU 기준 초
    seconds_single_gpu = total_flop / effective_tflops
    
    return {
        "total_exaflop": total_flop / 1e18,
        "single_a100_days": seconds_single_gpu / 86400,
        "8gpu_node_days": seconds_single_gpu / 86400 / 8,
        "64gpu_days": seconds_single_gpu / 86400 / 64,
    }

# 사례 1: 7B 모델, 140B 토큰 (Chinchilla-optimal)
result = estimate_compute(7, 140)
# total_exaflop: 5.88
# 64 GPU 기준 약 4.4일

# 사례 2: 70B 모델, 1400B 토큰 (Chinchilla-optimal)
result = estimate_compute(70, 1400)
# total_exaflop: 588
# 64 GPU 기준 약 440일 → A100 512장이면 약 55일

# 사례 3: 7B 모델, 2T 토큰 (Llama 스타일 over-training)
result = estimate_compute(7, 2000)
# total_exaflop: 84
# 64 GPU 기준 약 63일
```

파인튜닝의 경우 데이터 규모가 대개 수백만~수십억 토큰이라 사전학습 대비 compute가 100~1000배 작다. 하지만 gradient checkpointing, mixed precision, gradient accumulation 설정에 따라 실제 시간은 크게 달라진다. 위 계산은 상한선 추정용이다.

---

## 6. Scaling이 실패하는 경우

스케일링 법칙은 이론상 "모델과 데이터를 같이 키우면 성능이 예측 가능하게 오른다"는 전제를 깔고 있다. 하지만 이게 무너지는 경우가 여러 가지 있다.

**데이터 품질이 낮을 때**

인터넷 크롤링 데이터는 중복, 오염, 저품질 텍스트가 섞여 있다. MassiveText, C4, Dolma 같은 데이터셋이 중복 제거와 품질 필터링에 그렇게 공을 들이는 이유가 여기 있다. 같은 토큰 수라도 품질이 낮으면 스케일링 법칙이 예측하는 성능이 나오지 않는다. 쓰레기를 더 많이 보여준다고 더 똑똑해지지 않는다.

**에포크를 반복할 때**

학습 데이터가 고갈되면 같은 데이터를 여러 번 돌린다. 에포크 2~3회까지는 큰 문제가 없는 경우도 있지만, 반복이 늘어날수록 수익 체감이 심해진다. Chinchilla 법칙은 에포크 1회를 가정한다. "데이터 1T 토큰"이 실제로는 100B 토큰을 10번 돌린 것이라면 별개의 이야기다.

**특수 도메인: 코딩, 수학**

일반 언어 태스크와 달리 코딩/수학은 도메인 데이터 비율이 성능에 결정적이다. 코드 특화 데이터를 10배 더 먹이면 코딩 성능이 스케일링 법칙의 예측을 넘기도 한다. DeepSeek-Coder, WizardCoder 계열이 파라미터 대비 코딩 성능이 높은 게 이 때문이다. 반대로 말하면 일반 텍스트로 아무리 키워도 코딩 태스크는 도메인 데이터 없이는 한계가 있다.

**Architecture 병목**

단순히 레이어를 쌓거나 파라미터를 늘리는 것이 항상 동작하지 않는다. Attention의 quadratic complexity는 컨텍스트 길이가 길어질수록 부담이 된다. 이 경우 파라미터를 두 배 늘려도 긴 문서 처리 성능이 두 배가 되지 않는다. Mamba, RetNet 같은 linear attention 계열이 나온 배경이다.

**Fine-tuning에서의 착각**

사전학습된 모델에 fine-tuning을 할 때 스케일링 법칙을 그대로 적용하면 틀린다. fine-tuning은 새 지식을 집어넣는 작업이 아니라, 이미 학습된 표현을 특정 방향으로 조정하는 작업이다. 여기서는 데이터 양보다 데이터 품질과 구성이 훨씬 중요하다. 10만 개의 평범한 instruction 데이터보다 1천 개의 정교한 예제가 나은 경우가 많다.

---

## 7. 현재 시점에서의 해석

Chinchilla 법칙이 나온 이후 업계 관행이 바뀌었다. "파라미터를 무조건 키우자"에서 "inference 효율을 위해 소형 모델을 충분히 학습시키자"로 이동했다. Llama 시리즈, Mistral, Qwen 계열이 전부 이 방향이다.

한편 최근에는 Chinchilla-optimal보다 훨씬 많은 데이터로 학습시키는 경향이 강해지고 있다. 학습 compute를 조금 더 쓰더라도 모델을 작게 유지해서 inference 비용을 줄이는 편이 실 서비스에서는 더 이득이기 때문이다. 학습은 한 번이지만 inference는 억 번 일어난다.

스케일링 법칙이 LLM 개발의 핵심 설계 원리로 자리 잡은 건 맞지만, 이 법칙이 모든 것을 설명하지는 않는다. 데이터 품질, 도메인 구성, 학습 안정성, 그리고 아직 이해가 충분히 되지 않은 emergence 현상이 추가 변수로 작용한다. 숫자로 계산 가능한 부분과 실험으로 확인해야 하는 부분을 구분해서 봐야 한다.
