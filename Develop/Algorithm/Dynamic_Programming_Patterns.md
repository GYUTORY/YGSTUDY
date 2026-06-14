---
title: Dynamic Programming 유형 (자릿수·기댓값·카운팅·점화식 가속)
tags: [algorithm, dynamic-programming, digit-dp, expected-value-dp, counting-dp, monotonic-deque, convex-hull-trick]
updated: 2026-06-14
---

# Dynamic Programming 유형 (자릿수·기댓값·카운팅·점화식 가속)

## 들어가며

기본 문서에서 메모이제이션과 타뷸레이션, LIS, LCS, 배낭, 편집 거리를 다뤘고, 심화 문서에서 비트마스킹·구간·트리 DP와 Knuth·분할정복 최적화를 다뤘다. 이 문서는 그 둘에서 빠진 유형을 채운다. 자릿수 DP, 확률·기댓값 DP, 경우의 수 카운팅 DP, 그리고 점화식 전이 자체를 빠르게 만드는 단조 큐 최적화와 볼록 껍질 트릭이다.

이 네 가지는 성격이 제각각이다. 자릿수 DP는 "1부터 N까지 어떤 조건을 만족하는 수가 몇 개냐"를 자릿수 단위로 세는 기법이고, 기댓값 DP는 확률 과정의 평균값을 점화식으로 푼다. 카운팅 DP는 답이 너무 커서 MOD를 씌우는 순간 디버깅이 까다로워진다. 단조 큐와 CHT는 O(N²) 전이를 O(N) 또는 O(N log N)으로 줄이는 가속 기법이다. 공통점은 상태 정의가 까다롭고, 한 군데 실수하면 답이 미세하게 어긋나서 어디가 틀렸는지 찾기 힘들다는 점이다.

실무에서 이걸 직접 짤 일은 드물지만, 정산 시스템에서 특정 패턴의 거래 건수를 세거나, 큐 대기 시간의 기댓값을 추정하거나, 슬라이딩 윈도우 기반 집계를 빠르게 갱신할 때 같은 사고가 그대로 나온다. 코딩테스트에서는 후반부 변별 문제로 자주 등장한다.

## 자릿수 DP (Digit DP)

### 어떤 문제를 푸는가

"0 이상 N 이하의 정수 중에서 어떤 조건을 만족하는 것의 개수"를 묻는 문제다. N이 10^18처럼 커서 하나씩 세는 게 불가능할 때 자릿수를 앞에서부터 채워가며 센다. 예를 들어 "1부터 N까지 숫자 3을 포함하는 수의 개수", "각 자리 합이 K인 수의 개수", "인접한 자리가 같지 않은 수의 개수" 같은 게 전형적이다.

핵심 아이디어는 N을 문자열로 보고 최상위 자리부터 한 자리씩 결정하면서, 지금까지 만든 접두사가 N의 접두사와 같은지(tight) 여부를 상태로 들고 가는 것이다.

### 상태 정의

```
dp[pos][tight][...추가 상태]
```

- `pos`: 지금 결정할 자리 위치 (0부터 시작, 최상위 자리부터)
- `tight`: 지금까지 채운 자리가 N의 같은 위치 접두사와 정확히 일치하는지 여부. true면 이번 자리는 N의 해당 자리 숫자까지만 놓을 수 있고, false면 0~9 전부 놓을 수 있다.
- 추가 상태: 문제마다 다르다. 자리 합이면 `sum`, 직전 자리 숫자면 `prev`, 3의 포함 여부면 `boolean`.

tight의 의미를 정확히 잡는 게 전부다. tight가 true라는 건 "아직 N에 딱 붙어 있는 상태"라서 다음 자리에 N의 자릿수보다 큰 걸 놓으면 N을 초과한다. tight가 false면 이미 앞 어딘가에서 N보다 작은 숫자를 놓았으니 뒤는 자유롭게 0~9를 다 쓸 수 있다.

### 점화식과 전이

pos 자리에 놓을 숫자를 d라고 하면, d의 범위는 tight에 따라 갈린다.

- tight == true: d는 0부터 `num[pos]`까지
- tight == false: d는 0부터 9까지

그리고 다음 tight는 `tight && (d == num[pos])`로 갱신된다. 즉 지금도 딱 붙어 있었고 이번에 N의 자릿수와 똑같은 숫자를 놓아야만 다음 자리도 tight가 유지된다.

```java
public class DigitDP {
    static int[] num;       // N의 각 자리 숫자
    static int len;
    static Long[][][] memo;  // dp[pos][tight][sum]

    // 0 이상 N 이하에서 자리 합이 target인 수의 개수
    static long count(int pos, int tight, int sum, int target) {
        if (sum > target) return 0;
        if (pos == len) return sum == target ? 1 : 0;
        if (tight == 0 && memo[pos][tight][sum] != null) {
            return memo[pos][tight][sum];
        }

        int limit = (tight == 1) ? num[pos] : 9;
        long ret = 0;
        for (int d = 0; d <= limit; d++) {
            int nextTight = (tight == 1 && d == limit) ? 1 : 0;
            ret += count(pos + 1, nextTight, sum + d, target);
        }

        if (tight == 0) memo[pos][tight][sum] = ret;
        return ret;
    }

    public static long solve(long N, int target) {
        String s = Long.toString(N);
        len = s.length();
        num = new int[len];
        for (int i = 0; i < len; i++) num[i] = s.charAt(i) - '0';
        memo = new Long[len][2][target + 1];
        return count(0, 1, 0, target);
    }
}
```

### tight일 때 메모이제이션을 하면 안 되는 이유

위 코드에서 `if (tight == 0)`일 때만 memo를 읽고 쓴다. 이게 자릿수 DP에서 가장 많이 틀리는 부분이다.

tight가 true인 상태는 N의 실제 자릿수에 종속적이라 같은 (pos, sum)이라도 N이 다르면 결과가 다르다. 사실 한 번의 solve 호출 안에서 tight == true인 경로는 정확히 하나뿐이다(N의 접두사를 그대로 따라가는 경로). 그래서 tight 상태를 캐싱해도 재사용될 일이 없고, 오히려 여러 N에 대해 같은 memo 배열을 재활용하면 틀린 값이 남는다. tight == false 상태만 N과 무관하게 순수하게 (pos, sum)에 의존하므로 캐싱한다.

### leading zero 처리

자리 수 자체가 의미를 갖는 문제(예: "0이 아닌 자리의 개수", "서로 다른 자릿수의 개수")에서는 앞쪽의 0을 실제 자리로 세면 안 된다. 7을 0000007로 보면 0이 6개 붙는데, 이걸 진짜 0 자리로 취급하면 답이 망가진다.

leading zero를 처리하려면 상태에 `started` 플래그를 하나 더 둔다. started가 false면 아직 유효 숫자가 시작 안 된 상태고, 이때 d == 0을 놓으면 여전히 started == false다. d > 0을 처음 놓는 순간 started == true로 바뀐다.

```java
// 1 이상 N 이하에서 서로 다른 자릿수만으로 이루어진 수의 개수
// mask: 지금까지 사용한 숫자 비트마스크
static long count(int pos, int tight, int started, int mask) {
    if (pos == len) {
        return started == 1 ? 1 : 0;  // 0은 제외하려면 started 체크
    }
    if (tight == 0 && started == 1 && memo[pos][mask] != null) {
        return memo[pos][mask];
    }

    int limit = (tight == 1) ? num[pos] : 9;
    long ret = 0;
    for (int d = 0; d <= limit; d++) {
        int nextTight = (tight == 1 && d == limit) ? 1 : 0;
        if (started == 0 && d == 0) {
            // 아직 시작 안 함: leading zero, mask 갱신 안 함
            ret += count(pos + 1, nextTight, 0, mask);
        } else {
            if ((mask & (1 << d)) != 0) continue;  // 이미 쓴 숫자면 스킵
            ret += count(pos + 1, nextTight, 1, mask | (1 << d));
        }
    }

    if (tight == 0 && started == 1) memo[pos][mask] = ret;
    return ret;
}
```

started까지 상태에 넣으면 메모이제이션 조건이 `tight == 0 && started == 1`로 길어진다. started == 0인 구간도 캐싱 안 하는 게 안전하다. 시작 전 상태는 mask가 항상 0이라 경로가 사실상 하나뿐이라 캐싱 이득도 없다.

### [a, b] 구간 처리

"a 이상 b 이하"는 `solve(b) - solve(a - 1)`로 푼다. 한쪽 끝만 세는 함수를 만들고 누적 차를 쓰는 게 정석이다. a가 0일 수 있으니 `a - 1`이 음수가 되는 경우(a == 0)를 따로 처리하거나, solve가 0을 포함하도록 설계해 둔다.

자릿수 DP에서 흔한 실수를 모아보면:

- tight 상태를 캐싱해서 다른 테스트 케이스 사이에 오염되는 경우
- leading zero를 무시해서 "자리 개수"나 "0의 개수"를 잘못 세는 경우
- `solve(b) - solve(a-1)`에서 a == 0 경계를 안 막는 경우
- memo 배열을 테스트 케이스마다 초기화 안 해서 이전 N의 값이 남는 경우

## 확률·기댓값 DP

### 기댓값의 선형성과 점화식

기댓값 DP는 어떤 확률 과정의 결과 기댓값을 상태로 두고 푼다. `E[s]`를 상태 s에서 시작했을 때 목표까지의 기댓값(보통 횟수나 비용)으로 정의하면, 한 단계 전이의 확률 분포로 점화식을 세운다.

전형적인 예가 주사위 게임이다. 1번 칸에서 시작해 주사위를 굴려 6칸까지 가는 데 필요한 굴림 횟수의 기댓값을 구한다고 하자.

```
E[i] = 1 + (1/6) * (E[i+1] + E[i+2] + ... + E[i+6])
E[목표 이상] = 0
```

칸 번호가 뒤로만 가니까 큰 번호부터 채우면 사이클이 없고 그냥 역순 계산으로 끝난다.

```java
// 1번 칸에서 N번 칸 이상 도달까지 주사위 굴림 횟수 기댓값
static double diceExpectation(int N) {
    double[] E = new double[N + 7];
    for (int i = N; i < N + 7; i++) E[i] = 0;  // 목표 도달
    for (int i = N - 1; i >= 1; i--) {
        double sum = 0;
        for (int d = 1; d <= 6; d++) sum += E[i + d];
        E[i] = 1 + sum / 6.0;
    }
    return E[1];
}
```

여기까지는 위상정렬이 가능한 DAG라 쉽다. 상태 의존 그래프에 사이클이 없으면 의존 순서대로 한 번씩 계산하면 된다.

### 상태가 사이클을 가질 때: 가우스 소거

문제가 어려워지는 건 "제자리에 머무를 확률"이 있을 때다. 예를 들어 어떤 칸에서 동전을 던져 앞면이면 다음 칸, 뒷면이면 그 자리에 그대로 있는다고 하면 `E[i]`가 자기 자신에 의존한다.

```
E[i] = 1 + p * E[i+1] + (1-p) * E[i]
```

이건 자기 항을 넘겨서 풀 수 있다.

```
E[i] - (1-p) * E[i] = 1 + p * E[i+1]
p * E[i] = 1 + p * E[i+1]
E[i] = 1/p + E[i+1]
```

자기 루프 하나 정도는 이렇게 대수적으로 정리되지만, 여러 상태가 서로 얽혀서 순환 의존을 만들면 더 이상 단순 대입으로 못 푼다. 상태 간 의존이 양방향이거나 사이클을 이루면 연립 일차방정식이 되고, 미지수가 E[0], E[1], ..., E[n-1]인 선형 시스템을 가우스 소거로 풀어야 한다.

각 상태마다 `E[s] = c_s + Σ p(s→t) * E[t]` 형태의 식이 하나씩 나온다. 이걸 행렬 형태 `A·E = b`로 정리한다. E[s] 식을 옮기면 `E[s] - Σ p(s→t) E[t] = c_s`이 되고, A의 (s, s) 성분은 `1 - p(s→s)`, (s, t) 성분은 `-p(s→t)`, b의 s 성분은 `c_s`다.

```java
// n개의 상태, trans[s][t] = s에서 t로 갈 확률, cost[s] = s에서의 즉시 비용
// E[s] = cost[s] + sum_t trans[s][t] * E[t] 를 가우스 소거로 푼다
static double[] solveExpected(int n, double[][] trans, double[] cost) {
    double[][] A = new double[n][n + 1];
    for (int s = 0; s < n; s++) {
        for (int t = 0; t < n; t++) {
            A[s][t] = (s == t ? 1.0 : 0.0) - trans[s][t];
        }
        A[s][n] = cost[s];  // 우변 b
    }

    // 가우스 소거 (부분 피벗팅)
    for (int col = 0; col < n; col++) {
        int pivot = col;
        for (int r = col + 1; r < n; r++) {
            if (Math.abs(A[r][col]) > Math.abs(A[pivot][col])) pivot = r;
        }
        double[] tmp = A[col]; A[col] = A[pivot]; A[pivot] = tmp;

        double diag = A[col][col];
        for (int r = 0; r < n; r++) {
            if (r == col) continue;
            double factor = A[r][col] / diag;
            for (int c = col; c <= n; c++) {
                A[r][c] -= factor * A[col][c];
            }
        }
    }

    double[] E = new double[n];
    for (int s = 0; s < n; s++) E[s] = A[s][n] / A[s][s];
    return E;
}
```

가우스 소거는 O(n³)이라 상태가 수천 개를 넘어가면 못 쓴다. 문제 대부분은 상태가 작거나(보통 수십~수백), 사이클이 국소적이라 사이클을 이루는 상태 그룹만 따로 묶어서 작은 연립방정식으로 풀고 나머지는 위상 순서로 처리하는 식으로 쪼갠다.

### 기댓값 DP에서 자주 틀리는 부분

- 부분 피벗팅(가장 큰 절댓값을 피벗으로) 없이 가우스 소거를 돌리면 피벗이 0에 가까울 때 부동소수 오차가 폭발한다. 반드시 피벗 선택을 넣는다.
- "목표 도달까지의 기댓값"인데 도달 불가능한 상태(흡수 안 되는 상태)가 있으면 기댓값이 무한대로 발산한다. A가 특이행렬(singular)에 가까워져 해가 안 나오니, 문제 조건에서 항상 도달 가능한지 먼저 확인한다.
- 확률 합이 1이 안 되는 전이(나가는 확률 합 < 1)를 빼먹으면 식이 어긋난다. 자기 루프나 흡수 상태를 빠뜨리지 않았는지 본다.
- 정수 비용을 double로 안 바꾸고 계산해서 정수 나눗셈으로 깨지는 경우. `sum / 6`이 아니라 `sum / 6.0`이다.

## 경우의 수 카운팅 DP

### 기본 형태

"조건을 만족하는 경우의 수"를 세는 DP다. 점화식 자체는 평범하지만 답이 지수적으로 커져서 보통 `10^9 + 7` 같은 소수로 나눈 나머지를 요구한다. 여기서 MOD 연산 때문에 생기는 함정이 여럿이다.

계단 오르기로 예를 들면, 한 번에 1칸 또는 2칸 오를 때 N칸을 오르는 경우의 수는 `dp[i] = dp[i-1] + dp[i-2]`다.

```java
static final int MOD = 1_000_000_007;

static long countWays(int N) {
    long[] dp = new long[N + 1];
    dp[0] = 1;
    dp[1] = 1;
    for (int i = 2; i <= N; i++) {
        dp[i] = (dp[i - 1] + dp[i - 2]) % MOD;
    }
    return dp[N];
}
```

### MOD 연산에서 틀리는 지점

덧셈은 단순하지만 곱셈과 뺄셈이 함정이다.

곱셈: `int * int`는 int 범위를 넘는다. MOD가 10^9 근처면 두 수의 곱이 10^18까지 가서 int는 물론 곱하기 전에 long으로 캐스팅 안 하면 오버플로한다.

```java
// 틀림: a, b가 int면 a * b가 먼저 int로 계산되어 오버플로
int wrong = (a * b) % MOD;

// 맞음: long으로 곱한다
long ok = (long) a % MOD * (b % MOD) % MOD;
```

뺄셈: MOD 연산에서 뺄셈 결과가 음수가 될 수 있다. `(a - b) % MOD`가 음수면 그대로 두면 안 되고 MOD를 더해 양수로 만든다. 포함배제(inclusion-exclusion)로 중복을 빼는 카운팅에서 자주 나온다.

```java
// 음수 방지
long sub = ((a - b) % MOD + MOD) % MOD;
```

누적: 루프 안에서 더할 때마다 `% MOD`를 안 하고 마지막에 한 번만 하면, 중간 합이 long 범위를 넘어 오버플로한다. 더하는 즉시 모듈러를 취하거나, 최소한 몇 번에 한 번씩은 줄여줘야 한다.

### 중복 카운트 방지

카운팅 DP에서 진짜 까다로운 건 MOD가 아니라 같은 경우를 두 번 세는 것이다. 점화식이 겹치는 경로를 만들면 답이 부풀어 오른다.

동전 거스름돈 경우의 수가 대표적이다. 동전 {1, 2, 5}로 금액 N을 만드는 방법의 수를 셀 때, 순서를 구분하지 않으려면(즉 1+2와 2+1을 같은 것으로) 동전을 바깥 루프에 둬야 한다.

```java
// 순서 구분 안 함 (조합): 동전이 바깥 루프
static long countCombinations(int[] coins, int N) {
    long[] dp = new long[N + 1];
    dp[0] = 1;
    for (int coin : coins) {
        for (int amount = coin; amount <= N; amount++) {
            dp[amount] = (dp[amount] + dp[amount - coin]) % MOD;
        }
    }
    return dp[N];
}

// 순서 구분 함 (순열): 금액이 바깥 루프
static long countPermutations(int[] coins, int N) {
    long[] dp = new long[N + 1];
    dp[0] = 1;
    for (int amount = 1; amount <= N; amount++) {
        for (int coin : coins) {
            if (amount >= coin) {
                dp[amount] = (dp[amount] + dp[amount - coin]) % MOD;
            }
        }
    }
    return dp[N];
}
```

루프 순서만 바꿨는데 의미가 완전히 달라진다. 동전을 바깥에 두면 각 동전을 "한 번씩 순서대로" 고려하므로 {1 다음 2}만 세고 {2 다음 1}은 안 센다. 금액을 바깥에 두면 같은 금액을 만드는 모든 동전 조합을 매번 다시 보므로 순서까지 구분된다. 이걸 헷갈려서 조합을 원하는데 순열을 세거나 그 반대로 하는 실수가 흔하다.

카운팅 DP에서 답이 예상보다 크면 거의 항상 중복 카운트고, 작으면 경로를 빠뜨린 거다. MOD를 씌우기 전에 작은 입력으로 손계산과 맞춰보는 게 디버깅의 시작이다. MOD를 씌우고 나면 값이 뒤섞여서 어디서 틀렸는지 안 보인다.

## 점화식 가속: 단조 큐 최적화

### 슬라이딩 윈도우 전이

`dp[i] = max(dp[j] + cost) (i-K <= j <= i-1)` 처럼 전이 범위가 고정 폭 윈도우인 경우, 매 i마다 K개를 다 보면 O(NK)다. 윈도우가 한 칸씩 미끄러지므로 단조 덱(monotonic deque)으로 윈도우 내 최댓값(또는 최솟값)을 O(1)에 유지하면 전체가 O(N)이 된다.

핵심은 덱에 인덱스를 저장하되, 덱 안의 dp 값이 단조 감소(최댓값 유지 시)하도록 유지하는 것이다. 새 인덱스를 넣기 전에 덱 뒤쪽에서 자기보다 작거나 같은 값들을 빼버린다. 그 값들은 앞으로 절대 최댓값이 될 수 없으니 버려도 된다.

```java
import java.util.*;

// dp[i] = a[i] + max(dp[j], i-K <= j <= i-1), dp[0] = a[0]
static long slidingWindowMax(long[] a, int K) {
    int n = a.length;
    long[] dp = new long[n];
    Deque<Integer> dq = new ArrayDeque<>();  // 인덱스 저장, dp 값 단조 감소
    dp[0] = a[0];
    dq.addLast(0);

    for (int i = 1; i < n; i++) {
        // 윈도우 벗어난 앞쪽 제거
        while (!dq.isEmpty() && dq.peekFirst() < i - K) {
            dq.pollFirst();
        }
        // 덱 앞이 윈도우 내 최댓값
        dp[i] = a[i] + dp[dq.peekFirst()];

        // 새 dp[i]를 넣기 전, 뒤쪽에서 작거나 같은 값 제거
        while (!dq.isEmpty() && dp[dq.peekLast()] <= dp[i]) {
            dq.pollLast();
        }
        dq.addLast(i);
    }
    return dp[n - 1];
}
```

### 처리 순서가 어긋나는 실수

덱 연산 순서가 정해져 있다. 매 i마다 (1) 앞쪽에서 윈도우 벗어난 인덱스 제거 → (2) 덱 앞으로 dp[i] 계산 → (3) 뒤쪽 정리 후 i 추가다. 이 순서를 지켜야 한다.

가장 많이 하는 실수가 dp[i]를 계산하기 전에 i를 덱에 넣는 것이다. 그러면 dp[i] 전이에 자기 자신이 후보로 들어가서 틀린다. dp[i]를 먼저 확정하고 나서 덱에 넣어야 한다.

또 하나는 윈도우 경계 조건이다. `j`의 범위가 `[i-K, i-1]`인지 `[i-K, i]`인지, 양 끝이 닫힌 구간인지에 따라 `dq.peekFirst() < i - K`의 부등호와 i를 넣는 시점이 달라진다. 문제의 전이 범위를 정확히 적어놓고 부등호를 맞춘다.

최댓값이 아니라 최솟값이 필요하면 뒤쪽 제거 조건의 부등호 방향만 `>=`로 뒤집으면 된다. 덱이 단조 증가하도록 유지하는 것이다.

## 점화식 가속: 볼록 껍질 트릭 (Convex Hull Trick)

### 언제 쓰는가

`dp[i] = min(dp[j] + a[j] * b[i])` 꼴, 즉 전이가 j에 대한 일차식 `y = a[j] * x + dp[j]`이고 x = b[i]인 경우다. 각 j는 기울기 `a[j]`, y절편 `dp[j]`인 직선 하나에 대응한다. dp[i]를 구하는 건 "x = b[i]에서 모든 직선 중 최솟값을 찾는 것"과 같다.

직선들의 하한 포락선(lower envelope)은 볼록 껍질을 이룬다. 직선을 추가하면서 이 껍질을 유지하면, 각 질의를 O(log N) 또는 (단조 조건이면) 분할상환 O(1)에 처리한다. 전체 O(N²)가 O(N log N) 또는 O(N)으로 준다.

조건이 까다롭다. 기울기 `a[j]`가 단조(증가 또는 감소)로 추가되고, 질의 x = b[i]도 단조면 덱 기반 O(N) 버전을 쓴다. 단조가 안 깨지면 이게 제일 간단하다.

### 단조 버전 구현

기울기가 감소 순서로 추가되고 질의 x가 증가하는 최솟값 문제를 예로 든다.

```java
// 직선 y = m*x + c 들의 하한 포락선을 덱으로 유지
// 기울기 m이 감소 순으로 추가, 질의 x가 증가 순
static class CHT {
    long[] M, C;  // 기울기, 절편
    int head = 0, tail = 0;

    CHT(int n) { M = new long[n]; C = new long[n]; }

    // 직선 (a3,b3)이 (a1,b1)과 (a2,b2)의 교점 바깥에서 무용지물인지 판정
    // 부동소수 대신 교차 곱으로 비교 (오버플로 주의)
    private boolean bad(int l1, int l2, int l3) {
        // (C[l3]-C[l1]) / (M[l1]-M[l3]) <= (C[l2]-C[l1]) / (M[l1]-M[l2])
        return (C[l3] - C[l1]) * (M[l1] - M[l2])
             <= (C[l2] - C[l1]) * (M[l1] - M[l3]);
    }

    void addLine(long m, long c) {
        M[tail] = m; C[tail] = c;
        while (tail - head >= 2 && bad(tail - 2, tail - 1, tail)) {
            // 가운데 직선 제거
            M[tail - 1] = M[tail];
            C[tail - 1] = C[tail];
            tail--;
        }
        tail++;
    }

    long query(long x) {
        // x 증가 단조: head를 앞으로만 민다
        while (tail - head >= 2
                && M[head + 1] * x + C[head + 1] <= M[head] * x + C[head]) {
            head++;
        }
        return M[head] * x + C[head];
    }
}
```

### 흔한 실수와 주의점

기울기·질의 단조 가정 위반. 위 덱 버전은 기울기가 단조로 들어오고 질의도 단조라는 전제에서만 맞다. 기울기가 아무 순서로 들어오거나 질의가 단조가 아니면 head를 앞으로만 미는 게 틀린다. 이 경우는 Li Chao Tree를 쓰거나, 정렬 후 이분 탐색으로 질의하는 일반 버전으로 가야 한다. 단조 조건을 확인 안 하고 덱 버전을 쓰는 게 가장 흔한 실수다.

`bad` 판정의 오버플로. 교점을 부동소수 나눗셈으로 비교하면 정밀도 문제가 생기니 교차 곱으로 비교하는데, `(C[l3]-C[l1]) * (M[l1]-M[l2])`가 long 범위를 넘을 수 있다. 좌표가 크면 곱이 10^18을 넘어 오버플로한다. 값 범위를 미리 따져보고 필요하면 `__int128` 대용으로 BigInteger를 쓰거나 입력 범위를 확인한다.

최댓값 vs 최솟값. 위 코드는 최솟값(하한 포락선)이다. 최댓값을 원하면 기울기 부호를 뒤집어 넣거나(직선 전체를 -1배) `bad`와 `query`의 부등호를 모두 뒤집어 상한 포락선을 유지한다. 부등호 하나만 뒤집고 나머지를 안 맞춰서 절반만 틀리게 동작하는 경우가 많다.

언제 CHT까지 가야 하는가. 전이가 `dp[j] + a[j]*b[i]` 꼴로 깔끔하게 분리되는지부터 확인한다. `a[j]`가 j에만, `b[i]`가 i에만 의존해서 곱으로 분리돼야 직선으로 볼 수 있다. 이 분리가 안 되면 CHT를 못 쓴다. 분리되는지 확인 안 하고 식을 억지로 끼워 맞추려다 시간 버리는 경우가 있다.

## 정리

네 유형 모두 상태 정의가 절반이다. 자릿수 DP는 tight와 started 두 플래그의 의미를 정확히 잡고 tight 상태를 캐싱하지 않는 게 핵심이다. 기댓값 DP는 의존 그래프에 사이클이 있으면 가우스 소거로 연립방정식을 풀고, 부분 피벗팅을 빼먹지 않는다. 카운팅 DP는 MOD의 곱셈 오버플로와 음수 뺄셈, 그리고 루프 순서로 갈리는 중복 카운트를 조심한다. 단조 큐와 CHT는 전이 식의 구조(고정 윈도우인지, j와 i가 곱으로 분리되는지)를 먼저 확인하고 단조 조건이 성립할 때만 덱 버전을 쓴다.

손에 익히는 방법은 작은 입력으로 브루트포스 답과 맞춰보는 것이다. 특히 카운팅과 기댓값은 MOD나 부동소수가 끼면 틀린 자리를 눈으로 못 찾으니, MOD 없는 작은 케이스나 손계산으로 먼저 검증하고 가속·모듈러를 입히는 순서로 가는 게 안전하다.
