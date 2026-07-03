---
title: Brute Force (완전탐색)
tags: [algorithm, brute-force, backtracking, combinatorics, bitmask]
updated: 2026-04-18
---

# Brute Force (완전탐색)

## 들어가며

알고리즘 문제를 풀 때 처음으로 떠올려야 하는 접근은 거의 항상 완전탐색이다. "모든 경우를 다 해본다"는 단순한 발상이지만, 많은 문제에서 이게 진짜 답이다. 제출 전에 시간 복잡도만 맞으면 그대로 통과되고, 시간이 안 되면 그때부터 가지치기, 메모이제이션, DP, 그리디 같은 최적화로 넘어간다.

실무에서도 같은 패턴이 자주 나온다. 뭔가 계산해야 하는데 정확한 알고리즘이 아직 떠오르지 않을 때, 일단 N이 작은 케이스를 완전탐색으로 돌려서 정답을 만들어 놓고 그걸 기준 삼아 점진적으로 최적화해 나간다. 이 문서에서는 알고리즘 기법으로서의 완전탐색만 다룬다. 비밀번호를 무작위로 대입하는 brute-force attack은 보안 영역이라 별도 문서(`Develop/Security/...`)에서 다룬다.

## 완전탐색이란

완전탐색은 해가 될 수 있는 모든 후보를 빠짐없이 검사해서 조건을 만족하는 것을 찾는 방식이다. 수학적으로 해의 공간(search space)을 전부 열거한다. 영어로는 brute force, exhaustive search라고 부른다.

핵심 전제는 두 가지다. 첫째, 해가 될 수 있는 모든 경우를 빠짐없이 생성할 수 있어야 한다. 둘째, 그 경우의 수가 시간 제한 안에 들어와야 한다. 이 두 조건을 동시에 만족시키는 것이 완전탐색 구현의 전부다.

### 언제 써야 하는가

완전탐색이 성립하는 조건은 생각보다 명확하다. 입력 크기가 작아서 경우의 수가 감당 가능한 수준이거나, 문제 구조상 더 나은 알고리즘이 없는 경우다.

- 입력 크기가 작다. N이 20 이하면 2^N 부분집합이 약 100만 개라 대부분 통과된다
- 더 똑똑한 알고리즘이 존재하지 않는다. NP-hard 문제(외판원, 배낭 문제 일부 변형)는 작은 N에서는 완전탐색이 유일한 정답
- 정답이 꼭 필요한 검증용. 최적화된 알고리즘을 만들 때 비교 기준으로 완전탐색 결과를 사용한다
- 면접, 코딩테스트에서 정답률을 올려야 하는 상황. 부분 점수라도 받으려면 일단 완전탐색부터 제출

반대로 완전탐색을 피해야 할 때도 분명하다. N이 30을 넘어서면서 2^N 조합을 만들어야 하는 문제, N이 15 이상인데 N! 순열을 돌려야 하는 문제, 상태 공간이 기하급수적으로 커지는데 메모이제이션이 불가능한 구조 등이다.

## 시간복잡도 판단 기준

이게 완전탐색에서 제일 중요하다. 문제를 보자마자 "이거 완전탐색 돌려도 되나?"를 머릿속으로 계산하는 감각이 필요하다. 실제 경쟁 프로그래밍 환경(1초 제한, C++ 기준 약 1억~2억 연산) 기준으로 대략적인 허용 범위는 다음과 같다.

| 복잡도 | N의 허용 범위 | 대표 문제 유형 |
|--------|--------------|----------------|
| O(N!) | N ≤ 10 | 순열 전체 탐색, 외판원 |
| O(2^N) | N ≤ 20~25 | 부분집합 전체 탐색, 비트마스크 DP |
| O(N^4) | N ≤ 100 | 네 개 선택, 사각형 탐색 |
| O(N^3) | N ≤ 300~500 | 삼중 루프, 플로이드-워셜 |
| O(N^2) | N ≤ 5,000 | 이중 루프, 구간 계산 |
| O(N log N) | N ≤ 500,000 | 정렬 후 처리 |
| O(N) | N ≤ 10,000,000 | 단순 순회 |

Java나 Python은 C++보다 상수가 크다. 파이썬은 대략 10배, Java는 2~3배 느리다고 잡으면 된다. 파이썬에서 2^25는 위험하고, 2^22 정도가 현실적인 한계다.

실전에서 가장 많이 실수하는 포인트는 "각 경우마다 내부 연산이 얼마나 드는가"를 빼먹는 것이다. 2^N으로 부분집합을 만드는데 각 부분집합마다 O(N) 계산을 하면 실제 복잡도는 O(N · 2^N)이다. N=20이면 2천만 연산이라 통과, N=25면 8억이라 위험하다.

## 대표 구현 패턴

### 반복문 중첩

가장 단순한 완전탐색은 for 루프를 여러 겹 쌓는 것이다. "배열에서 세 수의 합이 특정 값이 되는 경우"같은 문제.

```python
def find_triplet_sum(nums, target):
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if nums[i] + nums[j] + nums[k] == target:
                    return (nums[i], nums[j], nums[k])
    return None
```

O(N^3)이다. N=500이면 약 2천만 연산으로 통과되지만 N=1000이면 10억이라 시간 초과가 난다. 이런 문제는 정렬 후 투 포인터로 O(N^2)로 낮추는 게 정석이다.

### 순열 생성

N개 중 전부 혹은 일부를 순서 있게 뽑는 경우다. Python은 `itertools.permutations`로 한 줄에 끝나지만, 내부 구현을 이해하고 있어야 커스텀 로직을 넣을 수 있다.

```python
def permutations(arr, k):
    result = []
    used = [False] * len(arr)

    def backtrack(path):
        if len(path) == k:
            result.append(path[:])
            return
        for i in range(len(arr)):
            if used[i]:
                continue
            used[i] = True
            path.append(arr[i])
            backtrack(path)
            path.pop()
            used[i] = False

    backtrack([])
    return result
```

N!은 생각보다 빨리 폭발한다. 10! = 362만, 12! = 4.7억이다. N이 10을 넘어가면 순열 완전탐색은 거의 불가능하다.

### 조합 생성

순서 상관없이 N개 중 K개를 뽑는 경우다. C(N, K)로 계산된다.

```python
def combinations(arr, k):
    result = []

    def backtrack(start, path):
        if len(path) == k:
            result.append(path[:])
            return
        for i in range(start, len(arr)):
            path.append(arr[i])
            backtrack(i + 1, path)
            path.pop()

    backtrack(0, [])
    return result
```

`start` 인덱스로 이미 선택한 원소를 다시 고르지 않게 막는다. 이 트릭이 순열과 조합의 유일한 구현 차이다.

### 부분집합 (Subset)

모든 부분집합을 만드는 경우는 2^N이다. 재귀로 각 원소를 포함/불포함으로 나누거나, 비트마스크로 돌리면 된다.

```python
def all_subsets(arr):
    n = len(arr)
    result = []
    for mask in range(1 << n):
        subset = [arr[i] for i in range(n) if mask & (1 << i)]
        result.append(subset)
    return result
```

비트마스크 방식이 재귀보다 빠르고 코드도 짧다. N이 20~25 이하일 때 많이 쓴다.

### 비트마스크

상태를 정수 하나로 표현할 수 있을 때 강력하다. 예를 들어 "N개의 도시를 어떤 조합으로 방문했는가"를 N비트 정수 하나로 관리한다. 외판원 문제의 비트마스크 DP가 대표적이다.

```python
def tsp(dist):
    n = len(dist)
    INF = float('inf')
    # dp[mask][i] = mask에 포함된 도시들을 방문하고 현재 i에 있을 때 최소 비용
    dp = [[INF] * n for _ in range(1 << n)]
    dp[1][0] = 0  # 0번 도시에서 시작

    for mask in range(1 << n):
        for u in range(n):
            if dp[mask][u] == INF:
                continue
            if not (mask & (1 << u)):
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                new_mask = mask | (1 << v)
                dp[new_mask][v] = min(dp[new_mask][v], dp[mask][u] + dist[u][v])

    # 모든 도시를 방문하고 0번으로 돌아옴
    full = (1 << n) - 1
    return min(dp[full][i] + dist[i][0] for i in range(1, n))
```

순수 완전탐색은 N!이지만 비트마스크 DP로 O(2^N · N^2)로 낮출 수 있다. N=20 기준 2^20 · 400 = 약 4억 연산이라 빡빡하지만 가능하다. N=15면 편하게 돌아간다.

### 재귀 백트래킹

현재 상태에서 유망하지 않으면 더 들어가지 않고 되돌아가는(backtrack) 방식이다. N-Queen이 교과서적인 예시다.

```python
def solve_n_queen(n):
    result = []
    cols = [-1] * n

    def is_safe(row, col):
        for r in range(row):
            c = cols[r]
            if c == col or abs(c - col) == abs(r - row):
                return False
        return True

    def backtrack(row):
        if row == n:
            result.append(cols[:])
            return
        for col in range(n):
            if is_safe(row, col):
                cols[row] = col
                backtrack(row + 1)
                cols[row] = -1

    backtrack(0)
    return result
```

순수 완전탐색이라면 N^N이지만, `is_safe`로 가지치기를 하면 실질적으로는 훨씬 적게 탐색한다. N=8일 때 실제 탐색 노드는 수천 개 수준이다.

## 완전탐색 → 가지치기 → DP 전환 사례

완전탐색으로 시작해서 최적화하는 흐름을 피보나치 수로 보면 감이 잡힌다.

### 1단계: 순수 완전탐색

```python
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

O(2^N). n=40이면 이미 체감 가능하게 느리다. 같은 부분문제를 여러 번 계산하는 게 문제.

### 2단계: 메모이제이션 (Top-Down DP)

```python
def fib(n, memo={}):
    if n <= 1:
        return n
    if n in memo:
        return memo[n]
    memo[n] = fib(n - 1, memo) + fib(n - 2, memo)
    return memo[n]
```

O(N)으로 떨어진다. 완전탐색 구조는 그대로 두고 캐시만 씌운 것이다.

### 3단계: Bottom-Up DP

```python
def fib(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
```

재귀 호출 오버헤드를 없애고 공간도 O(1)로 더 줄일 수 있다.

이 패턴이 완전탐색 최적화의 전형이다. "재귀 호출로 해의 공간을 다 뒤진다 → 중복 부분문제가 있는지 본다 → 메모이제이션 → 반복문으로 전환"이 흐름이다. 중복 부분문제가 없으면 DP로 바꿀 수 없고, 그때는 가지치기나 그리디로 방향을 튼다.

## 복잡도별 실패/성공 경계

실전에서 자주 마주치는 경계선을 정리해둔다. 경쟁 프로그래밍 기준 1초 제한, C++ 약 1억 연산.

### 2^N 계열

- N=20: 약 100만, 여유 있게 통과
- N=25: 약 3천 3백만, 내부 연산 단순하면 통과
- N=30: 약 10억, 거의 실패. 가지치기나 meet-in-the-middle 필요
- N=40: 약 1조, 절대 불가능. meet-in-the-middle로 2^(N/2)로 낮춰야 한다

### N! 계열

- N=8: 4만, 여유
- N=10: 360만, 통과
- N=11: 4천만, 아슬아슬
- N=12: 5억, 실패. 비트마스크 DP로 전환

### N^K 계열

- N=100, K=3: 100만, 통과
- N=500, K=3: 1억 2천, 보통 통과
- N=1000, K=3: 10억, 실패
- N=10000, K=2: 1억, 통과

이 숫자들을 감각적으로 기억해두면 문제를 보자마자 "아, N이 20이니까 2^N 비트마스크 쓰라는 거구나" 같은 판단이 빨라진다.

## 디버깅에 완전탐색 쓰는 트릭

복잡한 최적화 알고리즘을 구현했을 때 맞는지 틀리는지 확인하는 가장 확실한 방법은 완전탐색으로 만든 정답과 비교하는 것이다. 이걸 스트레스 테스트(stress testing)라고 한다.

```python
import random

def brute_force(arr):
    # 느리지만 확실히 맞는 완전탐색 버전
    ...

def optimized(arr):
    # 빠르지만 버그가 있을 수 있는 최적화 버전
    ...

def stress_test():
    for _ in range(10000):
        n = random.randint(1, 10)
        arr = [random.randint(1, 100) for _ in range(n)]
        expected = brute_force(arr)
        actual = optimized(arr)
        if expected != actual:
            print(f"Mismatch on input: {arr}")
            print(f"Expected: {expected}, Got: {actual}")
            break
    else:
        print("All tests passed")

stress_test()
```

랜덤 입력을 작게 만들어서 두 구현을 돌리고 결과가 다르면 그 입력으로 디버깅한다. 경쟁 프로그래밍 고수들이 실제로 많이 쓰는 기법이다. "맞는 답을 알 수 있는" 기준 구현이 있다는 게 핵심이다.

## 제출 전 입력 최대치로 시간 재기

코딩테스트에서 "이론적으로는 통과해야 하는데 시간 초과가 난다"는 경험이 한 번쯤은 있을 거다. 제출 전에 최대 입력을 만들어서 로컬에서 시간을 재보는 습관을 들이면 이게 크게 줄어든다.

```python
import time
import random

def make_worst_case(n):
    # 최악 입력 생성
    return [random.randint(1, 10**9) for _ in range(n)]

n = 200000  # 문제에서 주어진 최대 N
arr = make_worst_case(n)

start = time.perf_counter()
result = my_solution(arr)
elapsed = time.perf_counter() - start
print(f"Elapsed: {elapsed:.3f}s")
```

제한이 1초면 로컬에서 0.5초 이하로 들어와야 안전하다고 본다. 채점 서버가 로컬보다 빠를 수도, 느릴 수도 있어서 여유를 둬야 한다. 특히 파이썬은 로컬 환경 따라 편차가 큰데, `PyPy`로 제출 가능한 환경이면 CPython 대비 5~10배 빨라진다.

## 중복 상태 제거와 메모이제이션

완전탐색에서 성능이 폭발적으로 개선되는 지점은 대부분 "같은 상태를 여러 번 계산하고 있다"는 걸 발견했을 때다.

동전 교환 문제를 예로 보자. "동전 [1, 5, 10, 25]로 30원을 만드는 최소 동전 개수."

### 순수 완전탐색

```python
def min_coins(coins, amount):
    if amount == 0:
        return 0
    if amount < 0:
        return float('inf')
    return 1 + min(min_coins(coins, amount - c) for c in coins)
```

amount를 줄여가며 모든 경우를 탐색. 시간 복잡도는 대략 O(K^amount)로 금세 터진다.

### 메모이제이션

```python
from functools import lru_cache

def min_coins(coins, amount):
    @lru_cache(maxsize=None)
    def solve(remaining):
        if remaining == 0:
            return 0
        if remaining < 0:
            return float('inf')
        return 1 + min(solve(remaining - c) for c in coins)

    result = solve(amount)
    return result if result != float('inf') else -1
```

같은 `remaining`에 대해 한 번만 계산한다. O(amount · K)로 떨어진다.

완전탐색 코드에서 함수 인자 조합이 같으면 결과도 같다는 게 보이면, 그 인자들을 key로 캐싱하면 된다. 이게 DP로 넘어가는 가장 자연스러운 경로다.

## 실무 코드에서의 완전탐색 패턴

경쟁 프로그래밍뿐 아니라 실무에서도 비슷한 흐름이 자주 나온다. 예를 들어 이런 상황들이다.

- 신규 스케줄링 로직을 짜야 하는데, 정답 기준이 애매한 상황. 일단 모든 조합을 돌려서 최적해를 찾아놓고, 그걸 기준으로 빠른 휴리스틱을 만든다
- 테스트 케이스를 자동 생성할 때. 입력 공간이 작으면 완전탐색으로 모든 엣지 케이스를 만든다
- 프로덕션 배치 작업에서 "느리지만 확실히 맞는" 버전과 "빠르지만 근사해 가능성 있는" 버전을 병행 운영. 월 1회 정합성 검증을 한다

중요한 건 "완전탐색으로 돌아가는지 먼저 확인"하는 감각이다. N이 작고 돌릴 수 있으면 굳이 최적화할 필요가 없다. 최적화는 돌려봤는데 안 돌아갈 때 하는 거지, 미리 하는 게 아니다. 조기 최적화가 만악의 근원이라는 말은 알고리즘 문제 풀이에서도 그대로 통한다.

완전탐색 먼저 작성 → 프로파일링/시간 측정 → 병목 식별 → 해당 부분만 최적화. 이 순서를 지키면 코드도 단순해지고 버그도 줄어든다. 처음부터 "이건 느릴 것 같으니 DP로 가야지" 하고 뛰어들면 잘못된 점화식을 잡아서 한 시간을 날리는 일이 잦다.

## 마무리

완전탐색은 알고리즘의 기본이자 최후의 방어선이다. 문제를 보자마자 "완전탐색으로 풀면 복잡도가 얼마나 되는가"를 계산할 수 있어야 하고, 그게 시간 안에 안 들어오면 어떤 방향으로 최적화할지 판단할 수 있어야 한다.

외우는 것보다 돌려보는 게 더 빠르다. N=20 문제가 나오면 2^N 부분집합, N=10 문제면 N! 순열, N=8 문제면 N^N도 가능. 이 몇 가지 숫자 감각만 있어도 완전탐색이 답인 문제는 놓치지 않는다. 최적화는 그 다음 문제다.
