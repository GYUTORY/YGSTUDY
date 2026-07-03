---
title: IEEE 754 부동소수점 표현 심화
tags: [datarepresentation, ieee-754, floating-point, nan, rounding, precision, subnormal, kahan-summation]
updated: 2026-06-05
---

# IEEE 754 부동소수점 표현 심화

`0.1 + 0.2 != 0.3` 는 누구나 한 번쯤 본 결과다. 이걸 "부동소수점은 부정확하다" 정도로 정리하고 넘어가면, 결제 시스템에서 1원이 사라지거나 머신러닝 학습 도중에 NaN이 전파되어 모든 가중치가 망가지는 상황에서 원인을 못 잡는다.

IEEE 754는 1985년에 표준화된 부동소수점 표현이고, 거의 모든 CPU와 GPU가 이 규격을 따른다. 비트 패턴 하나하나에 의미가 있고, 정규화 수와 비정규화 수의 경계, NaN의 페이로드, 다섯 가지 반올림 모드, ULP 단위까지 전부 표준에 박혀 있다. 이 문서는 그 표준의 디테일과, 실무에서 그 디테일이 어떻게 문제로 튀어나오는지를 다룬다.

엔디언이나 2의 보수, `0.1 + 0.2` 같은 기초는 [엔디언과 2의 보수, IEEE 754 부동소수점](엔디언과 2의 보수, IEEE 754 부동소수점.md) 문서에서 다뤘다. 여기서는 그 다음 단계 — 왜 그런 결과가 나오는지, 어떻게 통제하는지 — 를 본다.

---

## 비트 레이아웃 복습 — 부호·지수·가수

IEEE 754 single precision(`float`, 32비트)을 다시 보면 이렇다.

| 영역 | 비트 수 | 의미 |
|------|---------|------|
| 부호 (S) | 1 | 0이면 양수, 1이면 음수 |
| 지수 (E) | 8 | 바이어스 127을 더한 값 |
| 가수 (M) | 23 | 정규화 수일 때 앞에 `1.` 이 숨어있음 |

double precision(`double`, 64비트)은 지수 11비트, 가수 52비트, 바이어스 1023이다.

정규화 수의 실제 값은 이렇게 복원한다.

```
value = (-1)^S × 1.M(2진수) × 2^(E - bias)
```

`1.0` 을 single precision으로 표현하면:

- S = 0
- E = 127 (= 01111111)
- M = 00000000000000000000000

비트 패턴은 `0 01111111 00000000000000000000000` = `0x3F800000`.

여기서 중요한 게 "숨어있는 1"이다. 가수 비트는 23개지만 실제로는 24비트의 정밀도를 가진다. `1.M` 의 맨 앞 1은 비트로 저장하지 않고 항상 있다고 가정한다. 이 가정이 깨지는 영역이 바로 비정규화 수다.

---

## 정규화 수 vs 비정규화 수 (서브노멀)

### 지수 필드 값별 의미

E 비트 패턴은 8가지 영역으로 나뉜다.

| E 값 (single) | 의미 |
|---------------|------|
| `00000000` (0) | 0 또는 비정규화 수 (subnormal) |
| `00000001` ~ `11111110` (1~254) | 정규화 수 |
| `11111111` (255) | 무한대 또는 NaN |

E가 0일 때는 숨은 1이 사라지고 가수 앞에 `0.` 이 붙는다. 그리고 지수는 `1 - bias` (= -126) 로 고정된다.

```
정규화 수:     (-1)^S × 1.M × 2^(E - 127)
비정규화 수:   (-1)^S × 0.M × 2^(1 - 127) = (-1)^S × 0.M × 2^(-126)
```

### 점진적 언더플로우 (Gradual Underflow)

비정규화 수가 왜 필요한가. 정규화 수만 쓴다면 표현 가능한 가장 작은 양수는 `1.0 × 2^(-126)` (≈ 1.175e-38) 이다. 이보다 작은 수는 전부 0으로 떨어진다. 이걸 abrupt underflow(급격한 언더플로우)라 한다.

문제는 두 정규화 수 `a`, `b` 가 다른데 `a - b == 0` 이 되어버리는 경우다. 예를 들어 `a = 1.0e-38`, `b = 1.0e-38 - 1.0e-45` 라면 둘 다 정규화 영역 근처에 있고 차이는 매우 작다. 차이가 정규화 영역의 최솟값보다 작으면 0이 된다. 그러면 코드에서 `if (a == b)` 검사가 통과해버린다.

비정규화 수가 있으면 이 차이가 0이 아니라 `1.0e-45` 같은 비정규화 수로 표현된다. 정규화 영역의 끝에서 0까지 점진적으로(gradually) 정밀도가 떨어지면서 내려간다.

표현 가능한 가장 작은 양수는:

- 가장 작은 정규화 수 (single): `2^(-126)` ≈ 1.175e-38
- 가장 작은 비정규화 수 (single): `2^(-149)` ≈ 1.401e-45

### 비정규화 수의 성능 함정

비정규화 수는 정확성을 위한 안전장치지만, 성능에서는 함정이다. x86 CPU 대부분은 비정규화 수가 연산에 들어오면 마이크로코드로 처리하면서 수십~수백 배 느려진다. 정규화 수 곱셈이 1 사이클이면 비정규화 수가 끼면 100 사이클을 넘기는 경우도 있다.

DSP나 오디오 처리에서 이게 자주 터진다. 잔향(reverb) 같은 필터가 점점 감쇠하면서 비정규화 영역에 진입하면, 갑자기 CPU 사용률이 치솟는다. 이런 경우 FTZ(Flush To Zero), DAZ(Denormals Are Zero) 플래그를 켜서 비정규화 수를 무조건 0으로 처리하는 방법을 쓴다.

```c
#include <xmmintrin.h>
#include <pmmintrin.h>

// SSE 레지스터에서 FTZ, DAZ 활성화
_MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
_MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
```

다만 FTZ/DAZ를 켜면 점진적 언더플로우의 보장이 사라진다. 과학 계산에서는 끄고, 오디오/그래픽처럼 정확도보다 성능이 중요한 영역에서 켠다.

---

## 0과 음수 0

IEEE 754에는 `+0` 과 `-0` 이 따로 있다.

- `+0`: `0 00000000 00000000000000000000000`
- `-0`: `1 00000000 00000000000000000000000`

`+0 == -0` 은 true다. 표준이 같다고 보도록 정의했다. 하지만 비트 패턴은 다르고, `1.0 / +0.0 = +Infinity`, `1.0 / -0.0 = -Infinity` 로 결과가 다르다.

이게 문제가 되는 경우가 있다. 해시 테이블 키로 부동소수점을 쓸 때 `+0` 과 `-0` 이 같은 값이지만 비트 패턴이 다르면 해시값이 다르게 나올 수 있다. Java의 `Double.hashCode(0.0)` 과 `Double.hashCode(-0.0)` 은 다른 값을 반환한다. `equals` 도 비트 패턴 비교라서 두 값을 다르다고 본다. `==` 와 동작이 다른 함정이다.

```java
System.out.println(0.0 == -0.0);                 // true
System.out.println(Double.compare(0.0, -0.0));   // 1 (0.0 > -0.0)
System.out.println(Double.valueOf(0.0).equals(Double.valueOf(-0.0))); // false
```

`Double.compare` 는 `-0.0 < +0.0` 으로 정렬한다. 정렬 결과가 `==` 비교와 다르다는 걸 모르면 디버깅이 어렵다.

---

## NaN — Not a Number

### NaN이 만들어지는 연산

다음 연산은 NaN을 반환한다.

- `0.0 / 0.0`
- `Infinity - Infinity`
- `Infinity * 0.0`
- `sqrt(-1.0)`
- `log(-1.0)`
- 모든 비교 연산은 한쪽이 NaN이면 false (단 `!=` 는 true)

### NaN의 비트 패턴

NaN의 비트 패턴은 "지수가 전부 1이고 가수가 0이 아닌" 모든 패턴이다.

```
S EEEEEEEE MMMMMMMMMMMMMMMMMMMMMMM
? 11111111 ?????????????????????? (가수 ≠ 0)
```

지수 8비트가 다 1이고 가수가 0이면 무한대고, 가수에 1이 하나라도 있으면 NaN이다. single precision에서 NaN으로 표현 가능한 비트 패턴은 `2 × (2^23 - 1) = 16,777,214` 개나 된다. double precision은 `2 × (2^52 - 1)` 개.

### qNaN vs sNaN

NaN은 두 종류로 나뉜다.

- **qNaN (Quiet NaN)**: 가수의 최상위 비트가 1. 연산에 전파될 뿐 예외를 발생시키지 않는다.
- **sNaN (Signaling NaN)**: 가수의 최상위 비트가 0이고 나머지 중 하나 이상이 1. 연산에 들어오면 invalid operation 예외를 발생시켜야 한다 (실제로는 언어/런타임마다 다름).

기본적으로 `0.0 / 0.0` 같은 연산이 만드는 NaN은 qNaN이다. sNaN은 일부러 만들지 않으면 잘 안 나타난다.

### NaN 페이로드

가수 비트의 나머지 22비트(single 기준)는 페이로드(payload)다. 표준은 이걸 디버깅 정보로 활용할 수 있게 비워뒀다. 어디서 NaN이 발생했는지를 비트 패턴에 인코딩해서 추적하는 용도다.

JavaScript의 V8 엔진은 NaN-boxing이라는 기법으로 이 페이로드를 활용한다. double 64비트 안에 작은 정수나 포인터를 인코딩해서, 모든 값을 64비트 double로 통일한다. NaN의 페이로드 영역에 실제 타입 정보를 박아넣는 식이다.

### NaN 전파 — 한 번 들어가면 끝까지 간다

```python
import numpy as np

a = np.array([1.0, 2.0, np.nan, 4.0])
print(a.sum())     # nan
print(a.mean())    # nan
print(a.max())     # nan
```

NaN이 한 번 끼면 그 다음 모든 연산이 NaN이 된다. 머신러닝 학습 중에 어딘가에서 NaN이 발생하면, 한 스텝 만에 모든 가중치가 NaN이 되고 모델이 망가진다. 이걸 막으려면 `np.nansum`, `np.nanmean` 같은 NaN-aware 함수를 쓰거나, `torch.isnan(loss).any()` 같은 검사를 매 스텝마다 한다.

### NaN 비교의 함정

```python
import math

nan = float('nan')
print(nan == nan)   # False
print(nan != nan)   # True
print(nan < 1.0)    # False
print(nan > 1.0)    # False
print(math.isnan(nan))  # True
```

`nan == nan` 이 False라는 게 표준이다. NaN 검사는 반드시 `math.isnan` 이나 `x != x` 패턴으로 한다.

### NaN과 정렬

`Arrays.sort(double[])` 에 NaN이 끼면 어떻게 정렬되는가. Java는 NaN을 가장 큰 값으로 본다 (`Double.compare` 기준). 그래서 정렬 결과에서 NaN은 맨 뒤로 간다.

C++의 `std::sort` 는 strict weak ordering이 깨져서 정의되지 않은 동작(undefined behavior)이다. NaN이 끼면 정렬이 망가지거나 무한 루프에 빠질 수 있다. 정렬 전에 NaN을 제거하거나 별도 처리해야 한다.

Pandas는 `sort_values(na_position='last')` 옵션으로 NaN 위치를 명시할 수 있다.

---

## 무한대

`±Infinity` 의 비트 패턴은:

- `+Infinity`: `0 11111111 00000000000000000000000` = `0x7F800000`
- `-Infinity`: `1 11111111 00000000000000000000000` = `0xFF800000`

지수가 전부 1이고 가수가 전부 0이다.

무한대가 발생하는 연산:

- `1.0 / 0.0` = `+Infinity`
- `-1.0 / 0.0` = `-Infinity`
- `log(0.0)` = `-Infinity`
- 오버플로우: `1e308 * 10.0` (double) = `+Infinity`

무한대끼리의 연산은 일부만 잘 정의된다.

```
Infinity + Infinity   = Infinity
Infinity - Infinity   = NaN
Infinity * 0.0        = NaN
Infinity / Infinity   = NaN
1.0 / Infinity        = 0.0
```

무한대도 전파성이 있다. `Infinity * 2 = Infinity`, `Infinity + 1 = Infinity`. 다만 NaN과 달리 빼기나 나누기로 NaN으로 변할 수 있다.

---

## 반올림 모드

`1/3` 같은 무한소수를 유한 비트로 표현하려면 반올림이 필요하다. IEEE 754는 다섯 가지 반올림 모드를 정의한다.

### 다섯 가지 반올림 모드

| 모드 | 동작 |
|------|------|
| roundTiesToEven | 가장 가까운 수로. 정확히 중간이면 짝수 쪽으로 |
| roundTiesToAway | 가장 가까운 수로. 정확히 중간이면 0에서 먼 쪽으로 |
| roundTowardPositive | 양의 무한대 방향으로 (ceiling) |
| roundTowardNegative | 음의 무한대 방향으로 (floor) |
| roundTowardZero | 0 방향으로 (truncation) |

`roundTiesToEven` 이 IEEE 754 기본값이고, 거의 모든 언어에서 기본값이다.

### Banker's Rounding이 기본인 이유

`roundTiesToEven` 을 Banker's Rounding이라고도 한다. 0.5, 1.5, 2.5, 3.5를 반올림하면:

- 일반 반올림 (half-up): 1, 2, 3, 4
- Banker's Rounding: 0, 2, 2, 4

Banker's Rounding이 기본인 이유는 통계적 편향을 줄이기 때문이다. 0.5를 항상 올림하면 평균이 위로 치우친다. 짝수 쪽으로 반올림하면 위/아래 확률이 같아져서 합산할 때 편향이 누적되지 않는다.

금융권에서 수백만 건의 거래를 합산할 때 이게 중요하다. 일반 반올림으로 1원짜리 편향이 100만 건 누적되면 100만 원의 차이가 난다.

Python의 `round` 함수도 Banker's Rounding이다.

```python
print(round(0.5))   # 0  (사람들이 보통 기대하는 건 1)
print(round(1.5))   # 2
print(round(2.5))   # 2
print(round(3.5))   # 4
```

half-up 반올림이 필요하면 `decimal.Decimal` 을 쓰거나 `math.floor(x + 0.5)` 같이 직접 구현한다.

### 다른 반올림 모드를 쓰는 경우

대부분 기본값을 쓰지만, 다른 모드가 필요한 경우가 있다.

- **roundTowardZero (truncation)**: C/C++의 `int` 캐스팅이 이 모드다. `(int)3.7 = 3`, `(int)-3.7 = -3`. 부호와 무관하게 소수부를 버린다.
- **roundTowardNegative (floor)**: 구간 산술(interval arithmetic) 에서 하한을 보장할 때 쓴다.
- **roundTowardPositive (ceiling)**: 마찬가지로 상한 보장.

구간 산술은 결과가 어떤 구간 안에 있다고 보장하는 계산법이다. 하한 계산은 floor 모드, 상한 계산은 ceiling 모드로 해서 양쪽 끝을 안전하게 잡는다.

### 런타임에 반올림 모드 바꾸기

C99에서는 `fenv.h` 로 반올림 모드를 변경할 수 있다.

```c
#include <fenv.h>

fesetround(FE_DOWNWARD);   // floor
double a = 1.0 / 3.0;
fesetround(FE_UPWARD);     // ceiling
double b = 1.0 / 3.0;
// a < b, 둘 사이가 1/3의 진짜 값을 포함하는 구간
```

JVM에서는 반올림 모드를 직접 바꿀 수 없다. `BigDecimal` 의 `setScale(scale, RoundingMode.HALF_UP)` 같이 객체 단위로 지정한다.

---

## ULP와 머신 엡실론

### ULP (Unit in the Last Place)

ULP는 어떤 부동소수점 값과 그 다음으로 표현 가능한 값 사이의 거리다. 부동소수점은 등간격이 아니라서 값에 따라 ULP가 다르다.

`1.0` 근처에서 single precision의 ULP는 `2^(-23)` ≈ 1.19e-7 이다. 이게 우리가 흔히 말하는 single precision의 정밀도 "약 7자리"의 근거다.

`1.0e6` 근처에서는 ULP가 훨씬 크다. `1.0e6` 의 다음 single precision 값은 `1.0e6 + 0.0625` 정도다. `1000000.0 + 0.01` 을 single precision으로 하면 결과가 그대로 `1000000.0` 이다. 0.01이 ULP보다 작아서 흡수(absorption)된다.

```java
float a = 1_000_000f;
float b = 0.01f;
System.out.println(a + b == a);  // true
```

ULP를 직접 측정하는 함수도 있다.

```java
System.out.println(Math.ulp(1.0f));        // 1.1920929E-7
System.out.println(Math.ulp(1_000_000f));  // 0.0625
System.out.println(Math.ulp(1.0e30f));     // 약 1.4e23
```

### 머신 엡실론

머신 엡실론(machine epsilon)은 `1.0` 에서의 ULP다. "1에 더했을 때 1과 다른 결과를 만드는 가장 작은 양수"로 정의되기도 한다.

| 타입 | 머신 엡실론 |
|------|-------------|
| float (single) | 약 1.19e-7 |
| double | 약 2.22e-16 |
| half (FP16) | 약 9.77e-4 |

머신 엡실론은 부동소수점 비교의 임계값으로 자주 쓰인다.

```python
import math

def almost_equal(a, b, eps=1e-9):
    return abs(a - b) <= eps * max(abs(a), abs(b))
```

다만 단순한 절대값 비교(`abs(a - b) < 1e-9`)는 큰 수에서 의미가 없다. `1e20` 과 `1e20 + 1` 의 차이는 1인데, ULP가 이미 1만 단위라서 `1e-9` 보다 훨씬 크다. 상대 비교(relative tolerance)와 절대 비교를 함께 쓰는 게 보통이다.

```python
def is_close(a, b, rel_tol=1e-9, abs_tol=1e-12):
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
```

Python의 `math.isclose` 가 이 방식이다.

---

## 정밀도 손실 — 자주 터지는 케이스

### Catastrophic Cancellation (재앙적 상쇄)

비슷한 크기의 두 수를 뺄 때, 상위 비트들이 상쇄되면서 의미 있는 정보가 사라지는 현상이다.

```python
a = 1.0000001
b = 1.0000000
c = a - b
print(c)  # 1.0000000005838672e-07
```

`a` 와 `b` 는 double 정밀도로 약 16자리. 빼고 나면 결과는 `1e-7` 근처고, 의미 있는 자릿수는 처음 1자리뿐이다. 나머지는 거의 노이즈다.

이게 진짜 문제가 되는 건 이차방정식의 근의 공식이다.

```python
import math

def quadratic_naive(a, b, c):
    d = math.sqrt(b * b - 4 * a * c)
    x1 = (-b + d) / (2 * a)
    x2 = (-b - d) / (2 * a)
    return x1, x2

# b가 매우 크면 -b + sqrt(...) 에서 cancellation 발생
print(quadratic_naive(1, 1e8, 1))
# (-7.450580596923828e-09, -100000000.0)
# 첫 번째 근의 실제 값은 약 -1e-8, 7.45e-9는 부정확
```

해결책은 곱셈을 이용해서 상쇄를 피하는 것이다.

```python
def quadratic_stable(a, b, c):
    d = math.sqrt(b * b - 4 * a * c)
    if b >= 0:
        x1 = (-b - d) / (2 * a)
        x2 = (2 * c) / (-b - d)
    else:
        x1 = (2 * c) / (-b + d)
        x2 = (-b + d) / (2 * a)
    return x1, x2

print(quadratic_stable(1, 1e8, 1))
# (-99999999.99999999, -1e-08)
```

### Absorption (흡수)

큰 수에 작은 수를 더할 때 작은 수가 사라진다. 위의 `1_000_000f + 0.01f` 가 그 예다. 합산 순서가 결과를 바꾼다.

```python
small = [1e-10] * 10_000_000
big = 1.0

# 작은 수 누적 후 큰 수 더하기
s1 = sum(small) + big
# 큰 수에 작은 수를 계속 더하기
s2 = big
for x in small:
    s2 += x

print(s1)  # 1.001
print(s2)  # 1.0007275957614183 정도 (오차 누적)
```

작은 수를 먼저 다 더하면 누적값이 커져서 의미 있는 자릿수를 유지하지만, 큰 수에 작은 수를 하나씩 더하면 매번 흡수돼서 오차가 쌓인다.

### Kahan Summation — 보상 합산

Kahan summation은 흡수로 잃어버리는 비트를 별도로 추적해서 보상하는 알고리즘이다.

```python
def kahan_sum(values):
    s = 0.0
    c = 0.0  # 손실된 저자릿수
    for x in values:
        y = x - c          # 이전에 잃은 부분을 보상
        t = s + y          # 흡수 발생
        c = (t - s) - y    # 흡수된 양을 다시 c에 저장
        s = t
    return s

values = [1e-10] * 10_000_000 + [1.0]
print(sum(values))         # 0.9999999999999998 정도
print(kahan_sum(values))   # 1.001 (정확)
```

`c` 가 매 스텝마다 흡수된 양을 기억해서 다음 스텝에 보상한다. 연산량은 4배 늘지만 정밀도가 크게 개선된다.

NumPy의 `np.sum` 은 기본적으로 pairwise summation을 쓴다. Kahan보다 빠르면서 단순 누적보다 정확하다. 진짜 정확한 합산이 필요하면 `math.fsum` 을 쓴다. 이건 정확한 합산을 보장한다 (Shewchuk's algorithm).

```python
import math

print(math.fsum([0.1] * 10))    # 1.0 (정확)
print(sum([0.1] * 10))           # 0.9999999999999999
```

---

## float vs double vs FP16 vs BF16

| 타입 | 총 비트 | 부호 | 지수 | 가수 | 약 유효 자릿수 | 표현 범위 |
|------|---------|------|------|------|----------------|-----------|
| half (FP16) | 16 | 1 | 5 | 10 | 3~4 | ±6.55e4 |
| bfloat16 (BF16) | 16 | 1 | 8 | 7 | 2~3 | ±3.4e38 |
| float (single) | 32 | 1 | 8 | 23 | 7~8 | ±3.4e38 |
| double | 64 | 1 | 11 | 52 | 15~17 | ±1.8e308 |
| quad | 128 | 1 | 15 | 112 | 33~36 | ±1.2e4932 |

FP16과 BF16은 머신러닝에서 메모리·대역폭·연산 속도를 위해 도입됐다. 둘 다 16비트지만 트레이드오프가 다르다.

- **FP16**: 가수 10비트로 정밀도가 그나마 있지만, 지수가 5비트라서 범위가 ±6.55e4 로 좁다. 학습 도중 그라디언트가 작아지면 언더플로우로 0이 되거나, 크면 오버플로우로 무한대가 된다. loss scaling 같은 기법으로 우회한다.
- **BF16**: 가수를 7비트로 줄이고 지수를 float와 같은 8비트로 맞췄다. 정밀도는 떨어지지만 float와 동일한 범위라서 오버플로우/언더플로우가 거의 없다. 학습 안정성이 좋아서 구글 TPU, NVIDIA A100/H100에서 기본으로 쓴다.

BF16의 비트 패턴은 float의 상위 16비트와 같다. float → BF16 변환이 단순히 하위 16비트를 잘라내는 것이다 (반올림은 따로 처리). 이 호환성이 BF16 채택의 큰 이유다.

### FP16 학습의 NaN 함정

```python
import torch

# FP16으로 학습하면 그라디언트가 매우 작거나 클 때 NaN/Inf 발생
x = torch.tensor([1e-5], dtype=torch.float16)
y = x * x  # 1e-10, FP16 최솟값 약 6e-8 보다 작아서 언더플로우
print(y)   # tensor([0.], dtype=torch.float16)

z = torch.tensor([1e3], dtype=torch.float16)
w = z * z  # 1e6, FP16 최댓값 약 6.55e4 초과
print(w)   # tensor([inf], dtype=torch.float16)
```

이래서 mixed precision 학습은 forward/backward는 FP16으로 빠르게 하고, 가중치 업데이트는 FP32로 한다.

---

## 비트 직접 디코딩

`float` 를 비트로 풀어서 부호·지수·가수를 직접 읽어보면 표준이 명확히 보인다.

### Python으로 single precision 디코딩

```python
import struct

def decode_float(f):
    # float -> 4바이트 -> 32비트 정수
    bits = struct.unpack('>I', struct.pack('>f', f))[0]
    sign = (bits >> 31) & 0x1
    exp = (bits >> 23) & 0xFF
    mantissa = bits & 0x7FFFFF

    print(f"value: {f}")
    print(f"bits:  {bits:032b}")
    print(f"sign:  {sign}")
    print(f"exp:   {exp} (biased), {exp - 127} (unbiased)")
    print(f"mantissa: {mantissa:023b}")
    print()

decode_float(1.0)
# value: 1.0
# bits:  00111111100000000000000000000000
# sign:  0
# exp:   127 (biased), 0 (unbiased)
# mantissa: 00000000000000000000000

decode_float(0.1)
# value: 0.1
# bits:  00111101110011001100110011001101
# sign:  0
# exp:   123 (biased), -4 (unbiased)
# mantissa: 10011001100110011001101
# 1.10011001100110011001101 × 2^-4 = 0.10000000149... (0.1과 다름)
```

`0.1` 의 가수가 `1100` 의 반복인 게 보인다. 0.1은 2진수로 무한소수 `0.0001100110011...` 이라서, 유한 비트에서는 정확히 표현 못 한다. 이게 `0.1 + 0.2 != 0.3` 의 진짜 원인이다.

### Java로 비트 보기

```java
float f = 0.1f;
int bits = Float.floatToIntBits(f);
System.out.println(Integer.toBinaryString(bits));
// 111101110011001100110011001101

double d = 0.1;
long lbits = Double.doubleToLongBits(d);
System.out.println(Long.toBinaryString(lbits));
```

`floatToIntBits` 와 `floatToRawIntBits` 의 차이는 NaN 처리다. `floatToIntBits` 는 모든 NaN을 정규 NaN(canonical NaN) 으로 통일하지만, `floatToRawIntBits` 는 원래 비트 패턴을 그대로 반환한다. NaN 페이로드를 보존하려면 `raw` 버전을 쓴다.

---

## 컴파일러·런타임 옵션이 동작에 미치는 영향

### Java strictfp

Java는 원래 모든 부동소수점 연산을 IEEE 754로 엄격히 보장하려 했다. 하지만 x86 FPU의 80비트 확장 정밀도(double extended) 때문에 중간 계산이 더 정확해질 수 있어서, 플랫폼별로 미세한 차이가 생겼다.

`strictfp` 키워드는 "중간 계산도 무조건 64비트 double로 해라" 를 강제한다. JDK 17부터는 x86이 64비트 정밀도를 지원하면서 `strictfp` 가 사실상 기본 동작이 됐고, 키워드는 no-op이 됐다.

### FMA (Fused Multiply-Add)

`a * b + c` 같은 연산은 보통 두 단계로 처리된다.

1. `a * b` 계산 후 64비트로 반올림
2. 결과에 `c` 를 더해 다시 반올림

FMA는 이걸 한 번에 처리한다. `a * b + c` 의 중간 결과를 무한 정밀도로 유지하고, 마지막에 한 번만 반올림한다. 정밀도가 더 좋아진다.

```java
// JDK 9 이상
double r = Math.fma(a, b, c);
```

FMA는 Haswell 이후 x86, ARMv8 이상에서 하드웨어로 지원한다. 단일 명령어로 처리해서 빠르기까지 하다. 단점은 결과가 비-FMA 버전과 다르다는 것이다. 같은 코드를 다른 머신에서 돌렸을 때 결과 비트가 다를 수 있다.

### `-ffast-math` (GCC/Clang)

`-ffast-math` 는 IEEE 754 표준 일부를 포기하고 최적화 여지를 주는 옵션이다. 구체적으로:

- NaN, 무한대를 신경 쓰지 않음 → 분기 제거
- 결합법칙 적용 가능 → `(a + b) + c` 를 `a + (b + c)` 로 재배열해서 벡터화
- `x / y` 를 `x * (1 / y)` 로 치환 (역수 곱셈이 빠름)
- `-0.0 == 0.0` 같은 케이스 통합

성능은 2~3배 빨라질 수 있지만, NaN을 못 잡고 정밀도가 떨어진다. 머신러닝 추론처럼 정확성 요구가 낮은 곳에서는 켜고, 과학 계산이나 금융에서는 절대 켜지 않는다.

CUDA의 `--use_fast_math` 도 같은 맥락이다. GPU에서 `sin`, `cos`, `exp` 같은 함수를 부정확하지만 빠른 근사 버전으로 치환한다.

---

## 실무에서 터지는 사례

### 금융 — 결제 합산의 1원 차이

```java
double total = 0.0;
for (Transaction t : transactions) {
    total += t.getAmount();  // double로 누적
}
// 100만 건 누적 후 회계 시스템과 1~10원 차이
```

해결책은 둘 중 하나다.

1. **정수로 저장**: 금액을 원 단위가 아니라 전(=1/100원) 단위 정수로 저장. `long` 이면 ±9.2e18 까지 표현 가능해서 천문학적 금액도 OK.
2. **BigDecimal**: 십진수 기반으로 정확하게 계산. 느리지만 정확하다.

```java
BigDecimal total = BigDecimal.ZERO;
for (Transaction t : transactions) {
    total = total.add(t.getAmount());  // BigDecimal로 누적
}
```

`BigDecimal` 의 함정은 `equals` 와 `compareTo` 다. `new BigDecimal("1.0")` 과 `new BigDecimal("1.00")` 은 값은 같지만 scale이 달라서 `equals` 가 false다. 비교할 때는 항상 `compareTo` 를 쓴다.

### 그래픽 — Z-fighting

3D 렌더링에서 두 표면이 거의 같은 깊이에 있을 때, depth buffer의 부동소수점 정밀도 한계로 어느 쪽이 앞인지 판단이 흔들리면서 깜빡이는 현상.

원근 투영 후 depth는 `1/z` 로 분포한다. 카메라에 가까운 영역은 정밀도가 높고, 먼 영역은 정밀도가 낮다. far plane을 너무 크게 잡으면 (예: `1.0` ~ `10000.0`) 먼 영역의 ULP가 커져서 표면이 겹친다. 해결은 reverse-Z (z를 뒤집어서 정밀도 분포를 맞춤), depth bias 추가, 카메라 near plane을 의미 있는 값으로 잡기 등이다.

### 머신러닝 — Loss가 NaN으로 폭발

```python
# 학습 도중 loss가 갑자기 nan
import torch

loss = compute_loss(model, batch)
if torch.isnan(loss):
    print("NaN 발생, 학습 중단")
    break
```

원인 후보:

- 학습률이 너무 크다 → 가중치가 폭발
- `log(0)` 호출 → `log(p + eps)` 처럼 eps 추가
- `0/0` → 분모에 eps 추가
- FP16 오버플로우 → loss scaling
- 그라디언트 폭발 → gradient clipping

```python
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

PyTorch의 `torch.autograd.set_detect_anomaly(True)` 를 켜면 NaN이 처음 발생한 연산을 추적해준다. 느리지만 디버깅에 유용하다.

### 시계열 — 누적 합산의 드리프트

센서 데이터를 long-running 프로세스에서 누적 평균 내는 경우, 단순 누적은 시간이 지날수록 정밀도가 떨어진다. Welford's online algorithm 같은 수치적으로 안정적인 알고리즘을 쓴다.

```python
def welford_update(state, x):
    count, mean, m2 = state
    count += 1
    delta = x - mean
    mean += delta / count
    delta2 = x - mean
    m2 += delta * delta2
    return count, mean, m2
```

이 방식은 평균과 분산을 한 패스로 정확하게 계산한다. 단순히 `sum / count`, `sum_sq / count - mean^2` 로 계산하면 큰 수의 뺄셈에서 catastrophic cancellation이 발생한다.

---

## 정리 — 언제 무엇을 쓰는가

부동소수점은 "근사값을 빠르게" 가 본질이다. 정확성이 필요하면 다른 표현을 쓴다.

- **빠른 계산, 근사값 OK**: float / double
- **머신러닝 학습**: BF16 + FP32 mixed precision
- **금융 계산**: 정수 또는 BigDecimal / Decimal
- **위치 좌표(GPS, GIS)**: double (위도 1도가 약 111km, double 정밀도 16자리면 cm 단위까지 무리 없음)
- **누적 합산**: Kahan summation 또는 `math.fsum`
- **두 부동소수점 비교**: 절대 `==` 쓰지 말고 ULP 또는 상대 오차로
- **NaN 처리**: 명시적으로 검사. 한 번 들어가면 전파됨

`0.1 + 0.2 != 0.3` 을 "부동소수점은 부정확" 이 아니라 "2진 부동소수점은 10진 소수를 정확히 표현 못 함" 으로 이해해야 한다. 이 차이를 알면 BigDecimal 쓸 곳과 double 써도 되는 곳을 구분할 수 있다.
