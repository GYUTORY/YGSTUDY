---
title: 논리 시계 - 벽시계 LWW가 쓰기를 버리는 빈도와 Lamport, 벡터 시계
tags: [architecture, backend, python]
updated: 2026-10-03
---

# 논리 시계 - 벽시계 LWW가 쓰기를 버리는 빈도와 Lamport, 벡터 시계

여러 노드가 같은 키를 쓰는 저장소에서 충돌을 푸는 가장 흔한 규칙은 "나중에 쓴 쪽이 이긴다"(last-write-wins, LWW)다. 각 쓰기에 타임스탬프를 붙이고 큰 쪽을 남긴다. 구현이 쉽고 조회도 단순해서 많이 쓰인다. 그런데 "나중"을 노드의 벽시계로 판단하는 순간 노드 사이의 시계 오차가 곧 데이터 유실률이 된다. 이 문서는 시계 오차에 따라 정상적인 쓰기가 얼마나 버려지는지를 시뮬레이션으로 재고, 벽시계를 대신하는 Lamport 시계와 벡터 시계가 각각 무엇을 보장하고 무엇을 못 하는지를 같은 방식으로 확인한다. 다중 리전에서 양쪽이 같은 키를 쓸 때 LWW가 데이터를 잃는 상황은 [인프라 고가용성](../DevOps/Principles/Infrastructure_High_Availability.md)에서 짧게 언급한다.

## 벽시계 LWW는 정상 쓰기를 버린다

모델은 단순하다. 노드 세 개가 같은 키를 번갈아 쓰고, 각 쓰기는 저장소에서 최신 값을 읽은 직후 일어난다. 그러니 쓰기 i+1은 쓰기 i 뒤에 일어난 것이 분명하고, 저장소는 매번 새 쓰기를 받아들여야 맞다. 노드마다 시계 오차를 `±skew` 범위에서 하나씩 정해 고정하고, 쓰기 사이의 실제 간격은 평균 `gap`인 지수분포로 뽑았다. 벽시계 방식은 `실제 시각 + 노드 오차`를 타임스탬프로 쓴다. 저장소에 있는 값보다 타임스탬프가 크지 않은 쓰기는 버려진다. 같은 이벤트열에 Lamport 방식도 같이 적용했다. 복제 지연은 없다고 가정했는데, 이것은 벽시계 방식에 가장 유리한 조건이다.

```python
"""벽시계 LWW 가 새 쓰기를 버리는 빈도를 센다.
노드 3 개가 같은 키를 번갈아 쓴다. 매 쓰기는 저장소에서 최신 값을 읽은 뒤에 일어난다.
즉 쓰기 i+1 은 쓰기 i 에 인과적으로 뒤따르므로, 저장소는 매번 새 쓰기를 받아들여야 한다."""
import random, statistics

def run(skew_ms, gap_ms, writes=1000, seed=0):
    rng = random.Random(seed)
    offsets = [rng.uniform(-skew_ms, skew_ms) for _ in range(3)]    # 노드별 시계 오차 (고정)
    t = 0.0                                                         # 실제 시각
    wall_ts = -1e18                                                 # 저장소에 있는 값의 벽시계 타임스탬프
    lamport = [0, 0, 0]; lam_stamp = (0, 0)                        # 노드별 Lamport 시계 / 저장소 값의 (시계, 노드)
    dropped_wall = dropped_lam = 0
    for _ in range(writes):
        t += rng.expovariate(1 / gap_ms)                            # 쓰기 사이의 실제 간격
        node = rng.randrange(3)

        ts = t + offsets[node]                                      # 벽시계: 로컬 시계 = 실제 시각 + 오차
        if ts > wall_ts: wall_ts = ts
        else: dropped_wall += 1                                     # 더 늦게 쓴 값인데 낡은 값으로 취급되어 버려진다

        lamport[node] = max(lamport[node], lam_stamp[0]) + 1        # Lamport: 읽은 값의 시계를 반영하고 +1
        stamp = (lamport[node], node)                               # 동률은 노드 번호로 깬다
        if stamp > lam_stamp: lam_stamp = stamp
        else: dropped_lam += 1
        # 복제 지연은 없다고 가정한다. 벽시계 방식에 가장 유리한 조건이다.
    return dropped_wall / writes, dropped_lam / writes

print("오차(±ms)  쓰기간격(ms)  버려진 쓰기 비율: 벽시계 LWW   Lamport")
for skew in (0, 5, 50, 500):
    for gap in (10, 100):
        rows = [run(skew, gap, seed=s) for s in range(300)]
        print(f"{skew:>8}  {gap:>10}   {statistics.mean(r[0] for r in rows):10.2%}   {statistics.mean(r[1] for r in rows):8.2%}")
```

```text
오차(±ms)  쓰기간격(ms)  버려진 쓰기 비율: 벽시계 LWW   Lamport
       0          10        0.00%      0.00%
       0         100        0.00%      0.00%
       5          10        9.75%      0.00%
       5         100        1.09%      0.00%
      50          10       44.32%      0.00%
      50         100        9.75%      0.00%
     500          10       63.75%      0.00%
     500         100       44.32%      0.00%
```

300번 반복한 평균이다. 읽는 법은 이렇다.

- 오차가 0이면 벽시계 방식도 하나도 버리지 않는다. 시계만 맞으면 문제가 없다.
- 오차 ±5ms, 쓰기 간격 평균 10ms일 때 쓰기의 9.75%가 버려졌다. 쓰기 열 번에 한 번꼴이다. 간격을 100ms로 늘리면 1.09%로 줄어든다.
- 오차가 간격의 몇 배가 되면 절반 가까이 버려진다. ±50ms에 간격 10ms에서 44.32%, ±500ms에 간격 10ms에서 63.75%였다.
- 오차와 간격의 비율이 같으면 결과도 같았다. (±5, 10)과 (±50, 100)이 모두 9.75%, (±50, 10)과 (±500, 100)이 모두 44.32%다. 중요한 건 오차의 절대 크기가 아니라 오차를 쓰기 간격으로 나눈 값이다. 쓰기가 몰리는 키일수록 작은 오차에도 취약하다.

이 숫자는 모델의 가정에서 나온다. 노드 오차를 한 번 정해 고정했고 시계 보정이 없으며, 오차 분포는 균등분포다. 실제 시스템의 시계 오차가 얼마인지는 이 실험에서 정할 수 없다. 의미가 있는 결론은 쓰기 간격이 시계 오차보다 충분히 크지 않으면 벽시계 LWW가 쓰기를 소리 없이 버린다는 것이다. 버려진 쓰기는 오류로 보고되지 않는다. 저장소 입장에서는 정상적인 충돌 해결이다.

Lamport 쪽은 같은 이벤트열에서 버려진 쓰기가 하나도 없다. 읽은 값의 시계를 반영해서 올리기 때문이다.

## Lamport 시계가 보장하는 것

Lamport 시계는 노드마다 카운터 하나를 둔다. 규칙은 두 가지다.

1. 이벤트가 일어날 때 자기 카운터를 1 올린다.
2. 메시지(또는 읽은 값)를 받으면 `max(내 카운터, 받은 카운터) + 1`로 맞춘다.

이렇게 하면 "a가 b보다 먼저 일어났다(a → b)"면 반드시 `L(a) < L(b)`다. 위 시뮬레이션에서 Lamport가 쓰기를 버리지 않은 이유다. 쓰기가 읽은 값 뒤에 일어났으니 시계는 거기서 이어진다. 물리 시각은 아무 역할도 하지 않으므로 노드의 시계 오차와 무관하다.

반대 방향은 성립하지 않는다. `L(a) < L(b)`라고 해서 a가 b보다 먼저 일어난 것은 아니다. 서로 정보를 주고받은 적 없는 동시 이벤트도 숫자는 앞뒤가 정해진다. 이것이 얼마나 자주 일어나는지 벡터 시계를 정답으로 놓고 셌다. 프로세스가 메시지를 주고받으며 이벤트를 만들고, `L(a) < L(b)`인 모든 이벤트 쌍 중 실제로는 인과 관계가 없는 쌍의 비율이다. 코드는 `a → b`이면 `L(a) < L(b)`가 항상 성립하는지 `assert`로도 확인한다.

```python
# converse.py  (vclock.py 의 vc_cmp 를 사용)
"""Lamport 타임스탬프가 L(a) < L(b) 라고 해도 실제로는 동시일 수 있다. 벡터 시계를 정답으로 놓고 센다."""
import random
from vclock import vc_cmp

def simulate(n_proc, n_events, p_msg, seed):
    rng = random.Random(seed)
    L = [0] * n_proc                              # 프로세스별 Lamport 시계
    V = [[0] * n_proc for _ in range(n_proc)]     # 프로세스별 벡터 시계 (정답용)
    events, inflight = [], []                     # 이벤트 기록 / 아직 안 받은 메시지
    for _ in range(n_events):
        p = rng.randrange(n_proc)
        if inflight and rng.random() < 0.5:       # 대기 중인 메시지 하나를 p 가 받는다
            ql, qv = inflight.pop(rng.randrange(len(inflight)))
            L[p] = max(L[p], ql) + 1
            V[p] = [max(a, b) for a, b in zip(V[p], qv)]
        else:                                     # 지역 이벤트
            L[p] += 1
        V[p][p] += 1
        events.append((L[p], dict(enumerate(V[p]))))
        if rng.random() < p_msg:                  # 이 이벤트에서 메시지를 내보낸다
            inflight.append((L[p], list(V[p])))
    return events

print("프로세스  메시지확률  L(a)<L(b) 쌍 중 실제로는 동시인 비율")
for n_proc in (3, 10):
    for p_msg in (0.9, 0.3, 0.1):
        tot = conc = 0
        for seed in range(20):
            ev = simulate(n_proc, 200, p_msg, seed)
            for la, va in ev:
                for lb, vb in ev:
                    rel = vc_cmp(va, vb)
                    if rel == "before": assert la < lb      # a -> b 이면 L(a) < L(b) 는 항상 성립한다
                    if la < lb:
                        tot += 1
                        conc += rel == "concurrent"
        print(f"{n_proc:>6}  {p_msg:>9}   {conc/tot:8.1%}   (쌍 {tot:,}개)")
```

```text
프로세스  메시지확률  L(a)<L(b) 쌍 중 실제로는 동시인 비율
     3        0.9      16.4%   (쌍 394,699개)
     3        0.3      10.7%   (쌍 395,223개)
     3        0.1      27.2%   (쌍 394,760개)
    10        0.9      49.4%   (쌍 387,101개)
    10        0.3      46.8%   (쌍 389,064개)
    10        0.1      78.2%   (쌍 385,550개)
```

200개 이벤트로 20번씩 돌린 결과다. 이 값들이 말하는 바는 이렇다.

- 프로세스가 3개일 때도 숫자상 앞선 쌍의 10%에서 27%가 실제로는 동시였다. 10개일 때는 47%에서 78%였다. Lamport 순서를 "실제 선후 관계"로 읽으면 이 비율만큼 틀린다.
- 메시지 확률이 높다고 단조롭게 줄지 않았다(3개 프로세스에서 0.9일 때 16.4%, 0.3일 때 10.7%). 메시지를 받는 쪽이 임의의 프로세스이고 도착 순서도 무작위인 이 모델에서 왜 이런 모양이 나오는지는 확인하지 않았다.
- 그러니 Lamport 시계는 충돌을 "해결할 순서"를 만들어 준다. 하지만 동시에 일어난 두 쓰기를 동시라고 알려 주지는 못한다. 한쪽이 버려진다는 점은 LWW와 같다. 유실 여부가 시계 오차에 의존하느냐 아니냐만 다르다.

## 동시 쓰기를 찾아내는 벡터 시계

동시인 쓰기를 알아내려면 벡터 시계가 필요하다. 노드마다 카운터를 따로 가진 벡터를 쓰기에 붙인다. 두 벡터를 비교해서 한쪽이 모든 항목에서 작거나 같으면 앞선 것이고, 한쪽이 어떤 항목에서는 더 크고 다른 항목에서는 더 작으면 동시다. 동시인 쓰기는 하나를 버리지 않고 둘 다 보관한다(형제 버전). 아래는 장바구니를 두 복제본에 나눠 쓰는 경우다.

```python
# vclock.py
import random

def vc_cmp(a, b):
    """'before' | 'after' | 'equal' | 'concurrent'"""
    keys = set(a) | set(b)
    le = all(a.get(k, 0) <= b.get(k, 0) for k in keys)
    ge = all(a.get(k, 0) >= b.get(k, 0) for k in keys)
    if le and ge: return "equal"
    if le: return "before"
    if ge: return "after"
    return "concurrent"

class Replica:
    def __init__(self, name):
        self.name = name
        self.versions = []                       # [(값, 벡터시계)]  동시 쓰기면 여러 개(형제)가 남는다
    def write(self, value, context=None):
        base = dict(context or {})               # 클라이언트가 읽고 온 시계
        base[self.name] = base.get(self.name, 0) + 1
        # 새 시계보다 "이전"인 버전은 버리고, 동시인 버전은 남긴다
        self.versions = [(v, c) for v, c in self.versions if vc_cmp(c, base) not in ("before", "equal")]
        self.versions.append((value, base))
        return base
    def merge_from(self, other):
        for v, c in other.versions:
            if any(vc_cmp(c, mine) in ("before", "equal") for _, mine in self.versions):
                continue
            self.versions = [(v2, c2) for v2, c2 in self.versions if vc_cmp(c2, c) != "before"]
            self.versions.append((v, c))

if __name__ == "__main__":
    A, B = Replica("A"), Replica("B")
    ctx = A.write("장바구니: 우유")                    # 최초 쓰기
    B.merge_from(A)                                    # B 도 복제본을 받는다
    # --- 네트워크 분리 ---
    ctxA = A.write("장바구니: 우유, 빵", ctx)           # 클라이언트 1 이 A 에서 수정
    ctxB = B.write("장바구니: 우유, 계란", ctx)         # 클라이언트 2 가 B 에서 수정
    print("A:", A.versions); print("B:", B.versions)
    print("두 시계의 관계:", vc_cmp(ctxA, ctxB))
    # --- 분리 해소 ---
    A.merge_from(B); B.merge_from(A)
    print("병합 후 A 가 가진 버전 수:", len(A.versions), [v for v, _ in A.versions])
    # 클라이언트가 형제를 읽고 합쳐서 쓴다
    merged_ctx = {}
    for _, c in A.versions:
        for k, n in c.items(): merged_ctx[k] = max(merged_ctx.get(k, 0), n)
    A.write("장바구니: 우유, 빵, 계란", merged_ctx)
    print("해소 후:", A.versions)
```

```text
A: [('장바구니: 우유, 빵', {'A': 2})]
B: [('장바구니: 우유, 계란', {'A': 1, 'B': 1})]
두 시계의 관계: concurrent
병합 후 A 가 가진 버전 수: 2 ['장바구니: 우유, 빵', '장바구니: 우유, 계란']
해소 후: [('장바구니: 우유, 빵, 계란', {'A': 3, 'B': 1})]
```

네트워크 분리 중에 A는 `{'A': 2}`, B는 `{'A': 1, 'B': 1}`라는 벡터를 받았다. 어느 한쪽도 다른 쪽보다 모든 항목에서 크지 않아 `concurrent`가 나왔고, 분리가 풀려 병합한 뒤 A는 두 버전을 둘 다 가지고 있다. 이것을 읽는 클라이언트는 두 버전을 합쳐서(`우유, 빵, 계란`) 다시 쓴다. 이때 두 벡터의 항목별 최댓값(`{'A': 2, 'B': 1}`)을 컨텍스트로 넘기면 새 쓰기가 두 버전을 모두 대체하고(`{'A': 3, 'B': 1}`), 형제는 하나로 정리된다. LWW였다면 두 쓰기 중 타임스탬프가 큰 하나만 남고 다른 하나의 수정은 오류 없이 사라진다.

벡터 시계가 공짜인 것은 아니다.

- 충돌 해결을 저장소가 못 한다. 형제 버전을 합치는 일은 애플리케이션이 해야 한다. 장바구니는 합집합이면 되지만 합칠 규칙이 없는 데이터에는 쓸 수 없다.
- 벡터의 항목 수는 그 키를 쓴 노드(또는 클라이언트) 수에 따라 는다. Dynamo 논문은 쓰기를 맡는 노드가 많을 때 벡터가 커질 수 있다고 설명하고, 쌍이 임계값(논문의 예는 10개)에 이르면 가장 오래된 쌍을 제거하는 방식을 쓴다고 한다. 논문은 이렇게 하면 선후 관계를 정확히 도출할 수 없어 조정 효율이 떨어질 수 있다고 인정한다. 출처는 [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)다.
- 위 구현은 개념 설명용이라 동기화 프로토콜이나 가비지 컬렉션이 없다.

## 선택 기준

| 상황 | 쓸 수 있는 것 | 유실 가능성 |
|---|---|---|
| 노드 시계가 충분히 정확하고 쓰기 간격이 그보다 훨씬 크다 | 벽시계 LWW | 오차/간격 비율에 비례(위 표) |
| 쓰기가 읽은 값을 이어받는다(읽고 쓰기) | Lamport | 읽은 값 뒤의 쓰기는 버려지지 않는다 |
| 서로 모르는 노드가 동시에 쓸 수 있고 유실이 곤란하다 | 벡터 시계 + 병합 규칙 | 병합 규칙이 없으면 해결 불가 |

읽지 않고 쓰는 경우에는 Lamport도 소용이 없다. 위 시뮬레이션에서 Lamport가 한 건도 안 버린 것은 모든 쓰기가 저장소의 최신 값을 읽은 직후였기 때문이다. 쓰기가 서로 읽지 않고 독립적으로 일어나면 숫자가 무엇이든 하나만 남는 규칙이라 다른 쪽은 사라진다. 이 유실을 막으려면 위에서 본 벡터 시계 같은 동시성 감지가 필요하다.

## 정리

- 벽시계 LWW에서 버려진 쓰기 비율은 시계 오차를 쓰기 간격으로 나눈 값에 따라 정해졌다. 비율 0.5(±5ms/10ms)에서 9.75%, 5에서 44.32%, 50에서 63.75%였다.
- Lamport 시계는 "읽고 나서 쓴" 쓰기를 시계 오차와 무관하게 올바른 순서로 둔다. 그러나 숫자가 앞선다고 인과 관계가 있다는 뜻은 아니다. 프로세스 10개 모델에서 숫자상 앞선 쌍의 47%에서 78%는 실제로 동시였다.
- 벡터 시계는 동시 쓰기를 `concurrent`로 가려내고 둘 다 보관한다. 대신 병합을 애플리케이션이 해야 하고 벡터가 노드 수만큼 커진다.
