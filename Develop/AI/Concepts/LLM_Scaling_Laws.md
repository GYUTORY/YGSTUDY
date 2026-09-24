---
title: LLM 스케일링 법칙
tags: [ai, llm]
updated: 2026-09-24
volatility: high
---

# LLM 스케일링 법칙

Karpathy의 'State of GPT'(2023)에서 가장 실용적으로 다룬 주제가 스케일링 법칙이다. 모델을 크게 만드는 게 능사가 아니라, 주어진 compute 예산 안에서 파라미터와 학습 데이터를 어떻게 배분하느냐가 핵심이다.

---

## 1. Kaplan vs Chinchilla

2020년 OpenAI의 Kaplan et al. 논문이 스케일링 법칙의 출발점이다. "compute 예산이 고정되어 있을 때, 파라미터를 최대한 크게 키우고 데이터는 상대적으로 덜 써도 된다"는 주장이었다. GPT-3(175B)가 이 법칙대로 설계됐다. 300B 토큰으로 175B짜리 모델을 학습시켰다.

2022년 DeepMind의 Chinchilla 논문(Hoffmann et al.)이 이걸 정면으로 반박했다. 같은 compute를 쓰면서 GPT-3보다 4배 작은 70B 모델에 1.4T 토큰을 먹였더니 GPT-3을 성능에서 앞질렀다. GPT-3이 파라미터 대비 데이터가 너무 적은, "under-trained" 상태였다는 게 결론이다.

Chinchilla가 제시한 규칙은 단순하다. 파라미터 1개당 학습 토큰 약 20개가 최적이다. 1B 모델이면 20B 토큰, 70B 모델이면 1.4T 토큰이다.

---

## 2. FLOP 계산과 compute-optimal 배분

학습에 필요한 총 FLOP는 이 공식으로 추정한다.

```
C = 6 × N × D

C: 총 FLOP
N: 파라미터 수
D: 학습 토큰 수
```

6이 붙는 이유는 forward pass(2N FLOP) + backward pass(4N FLOP)를 합친 값이기 때문이다.

Chinchilla-optimal 조건은 D = 20N이다. 이를 `C = 6ND`에 대입하면 `C = 120N²`가 된다. 역산하면:

```
N_opt = sqrt(C / 120)
D_opt = 20 × N_opt
```

`sqrt(C / 6)`이 아니다. 그 공식은 D = N, 즉 토큰 수와 파라미터 수가 같다는 전제로, Chinchilla 비율(20:1)과 다르다.

```python
import math

def chinchilla_optimal(
    compute_flop: float | None = None,
    n_params: float | None = None,
    n_tokens: float | None = None,
) -> dict:
    """
    C = 6ND, D/N ≈ 20 (Chinchilla ratio)
    셋 중 하나를 넘기면 나머지 둘과 함께 반환한다.
    """
    if compute_flop is not None:
        n_opt = (compute_flop / 120) ** 0.5
        d_opt = 20 * n_opt
        return {"n_params": n_opt, "n_tokens": d_opt, "compute_flop": compute_flop}
    elif n_params is not None:
        d_opt = 20 * n_params
        return {"n_params": n_params, "n_tokens": d_opt, "compute_flop": 6 * n_params * d_opt}
    elif n_tokens is not None:
        n_opt = n_tokens / 20
        return {"n_params": n_opt, "n_tokens": n_tokens, "compute_flop": 6 * n_opt * n_tokens}
    raise ValueError("세 인자 중 하나는 필요하다")


# 사용 예
r = chinchilla_optimal(n_params=7e9)
print(f"7B optimal: {r['n_tokens']/1e9:.0f}B 토큰, {r['compute_flop']/1e18:.0f} ExaFLOP")
# 7B optimal: 140B 토큰, 5880 ExaFLOP

r = chinchilla_optimal(n_tokens=1e12)
print(f"1T 토큰 optimal: {r['n_params']/1e9:.0f}B 파라미터")
# 1T 토큰 optimal: 50B 파라미터
```

GPU 예산에서 compute를 역산하는 함수다.

```python
def gpu_compute_budget(
    gpu_count: int,
    days: int,
    gpu_tflops: float = 312e12,  # A100 SXM fp16 이론값
    utilization: float = 0.38,   # IO 병목·통신 오버헤드 포함 실측치
) -> float:
    return gpu_tflops * utilization * gpu_count * (days * 86400)


# 64 A100, 14일
budget = gpu_compute_budget(64, 14)  # ≈ 9.18e21 FLOP
optimal = chinchilla_optimal(compute_flop=budget)
print(f"파라미터: {optimal['n_params']/1e9:.1f}B, 토큰: {optimal['n_tokens']/1e9:.0f}B")
# 파라미터: 8.8B, 토큰: 175B
```

utilization 35~40%는 실제 학습에서 넘기기 어렵다. 파이프라인 버블, all-reduce 통신, 체크포인트 I/O가 전부 깎아먹는다. 논문에서 "256장 A100으로 14일" 같은 조건이 나오면 이 계산으로 C를 역산해서 모델 규모가 합리적인지 확인할 수 있다.

---

## 3. 모델 선택 기준

### VRAM이 상한선이다

모델 크기는 학습보다 서빙에서 더 직접적인 제약이 된다. fp16 가중치는 2바이트/파라미터이고, kv cache와 activation을 위한 여유가 추가로 필요하다.

```python
def max_params_for_vram(vram_gb: float, dtype_bytes: int = 2, kv_reserve_gb: float = 8) -> float:
    """반환값: 십억 파라미터 수 (fp16 기준)"""
    available_bytes = (vram_gb - kv_reserve_gb) * 1e9
    return available_bytes / dtype_bytes / 1e9


print(max_params_for_vram(24))      # RTX 4090 1장: ≈ 8B
print(max_params_for_vram(80))      # A100 1장: ≈ 36B
print(max_params_for_vram(80 * 4))  # A100 4장 텐서 병렬: ≈ 144B
```

70B를 A100 단일로 올리려면 fp16 가중치만 140GB가 필요해서 불가능하다. 4비트 양자화(AWQ, GPTQ)를 쓰면 약 35GB로 줄어서 단일 A100에 올라간다. quantization은 품질 손실이 있으므로 태스크별 평가가 필요하다.

### 태스크 복잡도에 따른 판단

모델 크기와 태스크 복잡도의 관계는 스케일링 법칙보다 경험으로 파악되는 부분이 크다. 단순 분류, 키워드 추출, 정형 데이터 파싱은 fine-tuned 7B가 GPT-4보다 빠르고 싸게 동작하는 경우가 많다. 멀티홉 추론, 장문 코드 생성, 복잡한 instruction following은 모델 크기에 민감하다.

실무에서 쓰는 판단 기준이다. 정답이 잘 정의된 태스크 — 출력 형식이 고정되고 정답/오답이 명확 — 는 소형 fine-tuning이 유리하다. 열린 답변이 필요하거나 태스크 정의 자체가 불명확하면 대형 모델이 낫다. 경계선에 있으면 7B로 시작해서 품질 평가 후 올리는 게 현실적이다.

### Over-training이 inference 비용을 줄인다

Chinchilla-optimal보다 데이터를 더 먹인 모델이 서빙에는 유리하다. Llama-2 7B는 2T 토큰으로 학습했다. Chinchilla-optimal(140B)의 14배다. 학습 compute는 더 쓰지만 모델 크기는 7B로 유지된다. inference 때 GPU 메모리는 동일하고 품질은 Chinchilla-optimal보다 높다.

학습은 한 번이지만 inference는 요청마다 발생한다. 학습 compute를 30~40% 더 써서 inference 비용 없이 품질을 올릴 수 있다면 그 편이 낫다. 오픈소스 기준 "Llama 방식 over-training"이 사실상 표준이 된 이유다.

---

## 4. 파라미터 vs 데이터 vs 컴퓨트 트레이드오프

셋 중 어디에 돈을 쓸지가 실무 결정이다.

파라미터를 늘리면 모델 용량이 커져서 더 복잡한 패턴을 암기할 수 있다. 대신 inference 비용이 같이 올라간다. 70B를 서빙하는 것은 7B 서빙보다 GPU 비용이 10배다.

데이터를 늘리면 작은 모델도 잘 동작하게 만들 수 있다. Chinchilla 이후 흐름이 이쪽으로 갔다. Llama 2(70B)는 2T 토큰으로 학습해서 Chinchilla-optimal보다 더 많이 학습시켰다. 서빙할 때는 작고 잘 학습된 모델이 크고 덜 학습된 모델보다 practical하다.

compute를 늘리면 둘 다 올린다. 하지만 compute는 GPU 수량과 전기값으로 결정되는 실물 제약이라, 배분 문제가 된다.

| 선택지 | training 비용 | inference 비용 | 주 사용 사례 |
|--------|--------------|----------------|-------------|
| 파라미터 ↑ (과소 학습) | 중간 | 높음 | 일반적으로 비효율 |
| 파라미터 = Chinchilla-opt | 높음 | 낮음 | 서빙 중심 프로덕션 |
| 데이터 추가 (over-train) | 높음 | 낮음 | inference 집약적 서비스 |

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

    a100_fp16_tflops = 312e12
    utilization = 0.35
    effective_tflops = a100_fp16_tflops * utilization
    seconds_single_gpu = total_flop / effective_tflops

    return {
        "total_exaflop": total_flop / 1e18,
        "single_a100_days": seconds_single_gpu / 86400,
        "8gpu_node_days": seconds_single_gpu / 86400 / 8,
        "64gpu_days": seconds_single_gpu / 86400 / 64,
    }


# 사례 1: 7B 모델, 140B 토큰 (Chinchilla-optimal)
r = estimate_compute(7, 140)
# total_exaflop: 5,880 / 64 GPU 기준 약 9.7일

# 사례 2: 70B 모델, 1400B 토큰 (Chinchilla-optimal)
r = estimate_compute(70, 1400)
# total_exaflop: 588,000 / A100 512장이면 약 122일

# 사례 3: 7B 모델, 2T 토큰 (Llama 스타일 over-training)
r = estimate_compute(7, 2000)
# total_exaflop: 84,000 / 64 GPU 기준 약 139일
```

파인튜닝의 경우 데이터 규모가 대개 수백만~수십억 토큰이라 사전학습 대비 compute가 100~1000배 작다. 위 계산은 상한선 추정용이다.

### 예산 역산: 가진 GPU로 무엇을 학습할 수 있나

```python
# 시나리오: A100 8장, 7일
budget = gpu_compute_budget(8, 7)   # ≈ 5.73e20 FLOP
optimal = chinchilla_optimal(compute_flop=budget)
print(f"Chinchilla-optimal: {optimal['n_params']/1e9:.1f}B params, {optimal['n_tokens']/1e9:.0f}B tokens")
# Chinchilla-optimal: 2.2B params, 44B tokens

# 이 예산으로 7B 모델을 학습하면?
tokens_possible = budget / (6 * 7e9)
print(f"7B로 소화 가능한 토큰: {tokens_possible/1e9:.0f}B")
# 7B로 소화 가능한 토큰: 14B  (Chinchilla-optimal 140B의 10%)

# 7B를 Chinchilla-optimal로 학습하려면?
needed = chinchilla_optimal(n_params=7e9)   # compute = 5.88e21 FLOP
needed_days = needed['compute_flop'] / gpu_compute_budget(8, 1)
print(f"7B Chinchilla-optimal: A100 8장으로 {needed_days:.0f}일 필요")
# 7B Chinchilla-optimal: A100 8장으로 72일 필요
```

8장 A100, 7일 예산이라면 Chinchilla-optimal 기준으로 2B 모델이 적정하다. 7B를 같은 조건에서 돌리면 optimal 토큰의 10%만 소화해 심각하게 under-trained 상태로 끝난다.

---

## 6. Emergent Capabilities: 왜 갑자기 나타나는가

Wei et al.(2022)의 emergence 논문은 "모델이 특정 크기를 넘으면 갑자기 능력이 생긴다"는 현상을 기록했다. 작은 모델에서는 0에 가깝던 성능이, 임계점을 넘는 순간 급격히 올라간다.

메커니즘을 직관적으로 설명하면 이렇다. 멀티 스텝 추론이 필요한 태스크는 각 단계가 모두 성공해야 최종 정답이 나온다. 세 자리 수 덧셈은 각 자릿수 계산 + carry + 결합이 전부 맞아야 한다. 모델이 각 서브태스크를 50% 확률로 맞히면, 세 단계 전체 정확도는 0.5³ = 12.5%다. 서브태스크 정확도가 80%면 전체는 51.2%로 올라간다. 서브태스크 정확도가 연속적으로 상승해도 복합 태스크는 threshold를 넘는 순간 갑자기 올라가는 것처럼 보인다.

2023년 Schaeffer et al.이 다른 각도에서 반론을 제기했다. 비선형 metric(예: exact match)을 쓸 때 emergence처럼 보이는 것이지, linear metric(partial credit)으로 보면 연속적으로 상승한다는 것이다. Karpathy는 "emergence가 완전히 환상은 아니지만, metric 선택에 따라 과장될 수 있다"는 입장이다.

실무에서 중요한 점은 이거다. 소형 모델에서 잘 안 되는 태스크를 포기하기 전에, 모델 크기를 키우거나 학습 데이터를 늘렸을 때 갑자기 동작할 가능성이 있다. 선형 보간으로 "이 모델은 이 태스크를 못 할 것"이라는 예측이 틀리는 케이스가 있다.

---

## 7. Scaling이 실패하는 경우

스케일링 법칙은 "모델과 데이터를 같이 키우면 성능이 예측 가능하게 오른다"는 전제를 깔고 있다. 이게 무너지는 경우가 여러 가지 있다.

**데이터 품질이 낮을 때**

인터넷 크롤링 데이터는 중복, 오염, 저품질 텍스트가 섞여 있다. MassiveText, C4, Dolma 같은 데이터셋이 중복 제거와 품질 필터링에 공을 들이는 이유가 여기 있다. 같은 토큰 수라도 품질이 낮으면 스케일링 법칙이 예측하는 성능이 나오지 않는다.

**에포크를 반복할 때**

학습 데이터가 고갈되면 같은 데이터를 여러 번 돌린다. 에포크 2~3회까지는 큰 문제가 없는 경우도 있지만, 반복이 늘어날수록 수익 체감이 심해진다. Chinchilla 법칙은 에포크 1회를 가정한다. "데이터 1T 토큰"이 실제로는 100B 토큰을 10번 돌린 것이라면 별개의 이야기다.

**특수 도메인: 코딩, 수학**

일반 언어 태스크와 달리 코딩/수학은 도메인 데이터 비율이 성능에 결정적이다. 코드 특화 데이터를 10배 더 먹이면 코딩 성능이 스케일링 법칙의 예측을 넘기도 한다. DeepSeek-Coder, WizardCoder 계열이 파라미터 대비 코딩 성능이 높은 게 이 때문이다. 일반 텍스트로 아무리 키워도 코딩 태스크는 도메인 데이터 없이는 한계가 있다.

**Architecture 병목**

Attention의 quadratic complexity는 컨텍스트 길이가 길어질수록 부담이 된다. 파라미터를 두 배 늘려도 긴 문서 처리 성능이 두 배가 되지 않는다. Mamba, RetNet 같은 linear attention 계열이 나온 배경이다.

**Fine-tuning에서의 착각**

사전학습된 모델에 fine-tuning할 때 스케일링 법칙을 그대로 적용하면 틀린다. fine-tuning은 새 지식을 집어넣는 작업이 아니라, 이미 학습된 표현을 특정 방향으로 조정하는 작업이다. 데이터 양보다 데이터 품질과 구성이 훨씬 중요하다. 10만 개의 평범한 instruction 데이터보다 1천 개의 정교한 예제가 나은 경우가 많다.

---

## 8. 현재 시점에서의 해석

Chinchilla 법칙이 나온 이후 업계 관행이 바뀌었다. "파라미터를 무조건 키우자"에서 "inference 효율을 위해 소형 모델을 충분히 학습시키자"로 이동했다. Llama 시리즈, Mistral, Qwen 계열이 전부 이 방향이다.

최근에는 Chinchilla-optimal보다 훨씬 많은 데이터로 학습시키는 경향이 강해지고 있다. 학습 compute를 조금 더 쓰더라도 모델을 작게 유지해서 inference 비용을 줄이는 편이 실 서비스에서는 더 이득이기 때문이다.

스케일링 법칙이 LLM 개발의 핵심 설계 원리로 자리 잡은 건 맞지만, 이 법칙이 모든 것을 설명하지는 않는다. 데이터 품질, 도메인 구성, 학습 안정성, 그리고 아직 이해가 충분히 되지 않은 emergence 현상이 추가 변수로 작용한다. 숫자로 계산 가능한 부분과 실험으로 확인해야 하는 부분을 구분해서 봐야 한다.
