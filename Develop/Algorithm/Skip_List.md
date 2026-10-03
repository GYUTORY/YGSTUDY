---
title: 스킵 리스트 - 균형 트리 없이 O(log n)을 얻는 법과 p를 1/4로 잡는 이유
tags: [algorithm, redis, python]
updated: 2026-10-03
---

# 스킵 리스트 - 균형 트리 없이 O(log n)을 얻는 법과 p를 1/4로 잡는 이유

정렬된 상태를 유지하면서 삽입, 삭제, 검색, 범위 조회, 순위 조회를 다 하고 싶을 때 교과서가 내놓는 답은 AVL이나 레드-블랙 같은 균형 이진 트리다. 그런데 Redis의 Sorted Set(`ZADD`, `ZRANGE`, `ZRANK`)은 균형 트리가 아니라 스킵 리스트로 구현돼 있다. 스킵 리스트는 정렬된 연결 리스트 위에 "건너뛰는 층"을 확률로 쌓은 구조라서, 회전도 재균형도 없다. 이 문서는 파이썬으로 구현해서 비교 횟수가 정말 `O(log n)`인지, Redis가 층을 올릴 확률을 왜 1/4로 잡았는지, 파이썬에서 `bisect.insort`와 붙이면 어디서 역전되는지를 직접 돌려 본 결과로 정리한다. 정렬과 복잡도의 기본은 [정렬 알고리즘](Sorting.md)과 [시간복잡도와 공간복잡도](Time_Complexity.md)에 있다.

## 층을 확률로 쌓는다

정렬된 연결 리스트에서 검색은 `O(n)`이다. 노드를 하나씩 따라가야 하기 때문이다. 이 리스트 위에 "두 개 건너 하나씩" 이어 주는 층을 하나 더 얹으면 검색은 윗층에서 크게 건너뛰고 아랫층에서 마무리하는 식이 된다. 층을 계속 쌓으면 이진 탐색과 비슷해진다. 문제는 삽입이다. 노드가 하나 끼어들면 "정확히 두 개 건너 하나"라는 규칙이 깨지고, 이를 유지하려면 뒤쪽 층을 전부 다시 이어야 한다.

스킵 리스트는 이 규칙을 포기한다. 새 노드를 넣을 때 동전을 던져서 노드가 몇 층까지 올라갈지 정한다. 1층은 항상 있고, 다음 층에 올라갈 확률이 `p`다. 층 수는 이렇게 기하분포를 따르고, 노드 n개가 있으면 k층 이상인 노드는 평균 `n·p^(k-1)`개다. 규칙을 지키려고 이웃을 건드릴 필요가 없고, 새 노드가 올라간 층마다 앞 노드의 포인터 하나만 바꾸면 된다.

Redis의 소스에서도 이 구조를 그대로 확인할 수 있다. 층을 올릴 확률 `ZSKIPLIST_P`는 0.25이고 최대 층은 32다([server.h](https://github.com/redis/redis/blob/unstable/src/server.h)). 노드는 점수, 이전 노드를 가리키는 `backward` 포인터, 층마다 `forward` 포인터와 `span`을 가진다. `span`이 뒤에서 순위 계산에 쓰이는 값이다. Sorted Set이 작을 때는 스킵 리스트 대신 listpack으로 저장하며 그 기준은 기본 설정 `zset-max-listpack-entries 128`, `zset-max-listpack-value 64`다([redis.conf](https://github.com/redis/redis/blob/unstable/redis.conf)). 이 문서는 Redis를 실행한 게 아니라 소스와 설정 파일을 읽은 것이므로 Redis 쪽 수치는 거기까지만 인용한다.

## 구현

삽입, 검색, 삭제, 범위 조회, 순위 조회까지 있는 구현이다. `span[i]`는 `forward[i]`까지 건너뛰는 0층 노드 수를 기록한다. 순위 조회는 검색 경로에서 `span`을 더하기만 하면 되고, 이것이 Redis의 `ZRANK`가 `O(log n)`인 이유다. 삽입과 삭제는 이 `span`을 같이 갱신해야 해서 코드의 대부분이 거기에 쓰인다.

```python
# skiplist.py
import random

MAXLEVEL = 32

class Node:
    __slots__ = ("key", "forward", "span")
    def __init__(self, key, level):
        self.key = key
        self.forward = [None] * level      # forward[i]: i 층에서 다음 노드
        self.span = [0] * level            # span[i]: forward[i] 까지 건너뛰는 노드 수 (순위 계산용)

class SkipList:
    def __init__(self, p=0.25, seed=None):
        self.p = p
        self.rng = random.Random(seed)
        self.head = Node(None, MAXLEVEL)
        self.level = 1                     # 현재 사용 중인 최대 층
        self.size = 0
        self.compares = 0                  # 측정용: 키 비교 횟수

    def _random_level(self):
        lvl = 1
        while lvl < MAXLEVEL and self.rng.random() < self.p:
            lvl += 1
        return lvl

    def insert(self, key):
        update = [None] * MAXLEVEL         # 각 층에서 "새 노드 바로 앞" 노드
        rank = [0] * MAXLEVEL              # 그 노드의 순위(몇 번째인지)
        x = self.head
        for i in range(self.level - 1, -1, -1):
            rank[i] = 0 if i == self.level - 1 else rank[i + 1]
            while x.forward[i] is not None and x.forward[i].key < key:
                rank[i] += x.span[i]
                x = x.forward[i]
            update[i] = x
        lvl = self._random_level()
        if lvl > self.level:
            for i in range(self.level, lvl):
                rank[i] = 0
                update[i] = self.head
                self.head.span[i] = self.size
            self.level = lvl
        node = Node(key, lvl)
        for i in range(lvl):
            node.forward[i] = update[i].forward[i]
            update[i].forward[i] = node
            node.span[i] = update[i].span[i] - (rank[0] - rank[i])
            update[i].span[i] = (rank[0] - rank[i]) + 1
        for i in range(lvl, self.level):   # 새 노드가 안 닿는 층은 건너뛰는 거리만 1 늘어난다
            update[i].span[i] += 1
        self.size += 1

    def find(self, key):
        x = self.head
        for i in range(self.level - 1, -1, -1):
            while x.forward[i] is not None:
                self.compares += 1
                if x.forward[i].key < key:
                    x = x.forward[i]
                else:
                    break
        x = x.forward[0]
        self.compares += 1
        return x is not None and x.key == key

    def rank(self, key):                   # key 보다 작은 원소 수 (0부터)
        x, r = self.head, 0
        for i in range(self.level - 1, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < key:
                r += x.span[i]
                x = x.forward[i]
        return r

    def range(self, lo, hi):               # lo <= key < hi, 시작점은 O(log n), 이후는 0층을 따라 걷는다
        x = self.head
        for i in range(self.level - 1, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < lo:
                x = x.forward[i]
        x = x.forward[0]
        while x is not None and x.key < hi:
            yield x.key
            x = x.forward[0]

    def delete(self, key):
        update = [None] * MAXLEVEL
        x = self.head
        for i in range(self.level - 1, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < key:
                x = x.forward[i]
            update[i] = x
        x = x.forward[0]
        if x is None or x.key != key:
            return False
        for i in range(self.level):
            if update[i].forward[i] is x:
                update[i].span[i] += x.span[i] - 1
                update[i].forward[i] = x.forward[i]
            else:
                update[i].span[i] -= 1
        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1
        self.size -= 1
        return True

    def pointers(self):                    # 노드가 가진 forward 포인터 총합
        total, x = 0, self.head.forward[0]
        while x is not None:
            total += len(x.forward); x = x.forward[0]
        return total
```

균형 트리 구현과 같은 값을 돌려주는지는 `bisect`로 만든 정렬 리스트와 대조해서 확인했다.

```python
# check.py
import random, bisect
from skiplist import SkipList
rng = random.Random(1)
sl, ref = SkipList(seed=2), []
for _ in range(20000):
    k = rng.randrange(10**9)
    if k in ref: continue
    sl.insert(k); bisect.insort(ref, k)
for k in rng.sample(ref, 5000):
    assert sl.delete(k); ref.remove(k)
assert sl.size == len(ref)
for k in rng.sample(ref, 2000):
    assert sl.find(k)
    assert sl.rank(k) == bisect.bisect_left(ref, k)
lo, hi = ref[100], ref[400]
assert list(sl.range(lo, hi)) == ref[100:400]
assert not sl.find(-1)
print("검증 통과: 크기", sl.size, "층", sl.level)
```

```text
검증 통과: 크기 15000 층 7
```

20,000개를 넣고 5,000개를 지운 뒤 남은 15,000개에서 검색, 순위(`bisect_left`와 같은 값), 범위 조회가 모두 일치했다.

## 비교 횟수는 정말 2·log2(n)인가

`find`가 키를 비교한 횟수를 세었다. 층별로 "다음 노드가 목표보다 작은가"를 묻는 비교와, 그 층을 떠나게 되는 비교(작지 않아서 아래층으로 내려가는 순간)를 둘 다 센 값이다. 같은 키 순서(셔플한 0..n-1)로 `p`만 바꿔서 5,000번 검색하고 평균과 p99를 쟀다.

```python
# steps.py
import math, random, statistics
from skiplist import SkipList

def build(n, p, seed):
    sl = SkipList(p=p, seed=seed)
    keys = list(range(n)); random.Random(seed).shuffle(keys)
    for k in keys: sl.insert(k)
    return sl

print("p      n        평균비교   2·log2(n)  p99비교  최대층  노드당 포인터  (이론 1/(1-p))")
for p in (0.5, 0.25, 0.125):
    for n in (1_000, 10_000, 100_000):
        sl = build(n, p, seed=7)
        rng = random.Random(99); costs = []
        for _ in range(5000):
            sl.compares = 0; sl.find(rng.randrange(n)); costs.append(sl.compares)
        costs.sort()
        print(f"{p:<6} {n:<8} {statistics.mean(costs):8.1f}  {2*math.log2(n):9.1f}  {costs[int(len(costs)*.99)]:7d}  {sl.level:6d}  {sl.pointers()/n:12.3f}  ({1/(1-p):.3f})")
```

```text
p      n        평균비교   2·log2(n)  p99비교  최대층  노드당 포인터  (이론 1/(1-p))
0.5    1000         20.6       19.9       30      12         2.068  (2.000)
0.5    10000        26.2       26.6       37      16         2.020  (2.000)
0.5    100000       31.0       33.2       46      16         2.003  (2.000)
0.25   1000         17.3       19.9       31       6         1.381  (1.333)
0.25   10000        26.2       26.6       49       7         1.339  (1.333)
0.25   100000       30.8       33.2       52      11         1.335  (1.333)
0.125  1000         26.8       19.9       51       4         1.157  (1.143)
0.125  10000        32.3       26.6       70       5         1.144  (1.143)
0.125  100000       39.2       33.2       79       8         1.143  (1.143)
```

세 가지가 보인다.

- n이 100배(1,000에서 100,000) 늘 때 평균 비교는 20.6에서 31.0으로 늘었다. 로그 증가다. 2·log2(n) 근사와 맞는다.
- `p=1/2`과 `p=1/4`는 평균 비교 횟수가 거의 같다(n=100,000에서 31.0 대 30.8). 반면 노드가 가진 포인터 수는 노드당 2.003개 대 1.335개로, `p=1/4`가 3분의 1 정도 적다. 비교는 같은데 메모리는 덜 쓰는 것이다. Redis가 1/2이 아니라 1/4를 택한 이유로 합리적으로 설명되는 부분이다. 이유를 소스 주석에서 확인한 것은 아니다. 확인한 것은 이 측정값뿐이다.
- `p=1/8`은 포인터가 더 줄지만(1.143개) 비교가 늘고 p99가 79까지 올라간다. 층이 너무 얇아 윗층에서 건너뛸 수 있는 구간이 줄어든 것이다. 메모리와 검색 비용 사이의 균형점이 1/4 근처라는 말이다.

노드당 포인터 수의 이론값 `1/(1-p)`와 실측이 소수 셋째 자리까지 맞았다. 층 수가 기하분포라는 모델이 실제 동작을 정확히 설명한다는 뜻이다.

## 확률에 맡긴 구조가 한쪽으로 쏠리지 않나

균형 트리는 입력 순서에 따라 한쪽으로 기울 수 있어서 재균형이 필요하다. 스킵 리스트는 입력과 무관하게 층을 정하므로 입력이 오름차순이어도 똑같이 동작해야 한다. n=10,000에서 셔플 순서를 고정하고 층 결정용 난수 시드만 바꿔 200개 구조를 만들어 보았다.

```text
200 개 구조, n=10000: 평균 비교 최소 22.7  중앙 25.0  최대 32.2
오름차순 입력 평균 비교 24.7
```

운 나쁜 구조도 있다. 최대 32.2는 중앙값 25.0보다 29% 크다. 검색 비용이 보장이 아니라 기댓값이라는 점은 사실이다. 그래도 200번 중 최악이 중앙값의 1.3배 정도였고, 오름차순 입력이 나쁘지 않았다는 것(24.7)은 입력 순서에 취약하지 않다는 증거가 된다. 최악 시간을 반드시 보장해야 하는 곳이라면 균형 트리가 맞다. 확률이 나빠질 가능성을 몇 번 반복해서 감수하는 구조이기 때문이다.

## 파이썬에서 bisect.insort와 붙이면

`bisect.insort`는 정렬 리스트에 삽입하는 `O(n)` 연산이다. 이진 탐색으로 위치를 찾고 그 뒤 원소를 한 칸씩 밀기 때문이다. 이론으로는 스킵 리스트가 이긴다. 파이썬에서 실제로 어디서 역전되는지 셔플한 키를 하나씩 삽입하는 시간을 쟀다. CPython 3.10.12, 한 번씩 돌린 결과이고 `p=1/4`다.

| n | 스킵 리스트 삽입 총 시간 | `bisect.insort` 총 시간 |
|---|---|---|
| 10,000 | 0.17초 | 0.01초 |
| 100,000 | 2.50초 | 2.22초 |
| 300,000 | 12.22초 | 19.46초 |
| 1,000,000 | 51.97초 | 398.17초 |

10,000개에서는 `insort`가 17배 빠르다. 스킵 리스트는 순수 파이썬 객체와 반복문으로 층을 오르내리고, `insort`는 C로 구현된 `memmove`가 원소를 민다. 이 구간에서는 상수 배가 이긴다. 100,000개 근처에서 두 시간이 같아지고, 300,000개부터 `insort`가 느려진다. 1,000,000개에서는 스킵 리스트가 7.7배 빠르다.

`insort`는 100,000개에서 300,000개로 늘 때 8.8배(n이 3배면 이차 증가의 9배와 맞는다), 300,000개에서 1,000,000개로 늘 때 20.5배(n이 3.3배면 이차 증가로는 11배)가 되어 이차보다도 가파르다. 이유까지 확인하지는 않았다. 어쨌든 정렬된 상태에서 계속 삽입하는 워크로드가 수십만 건을 넘는다면 배열 삽입은 선택지에서 빠진다.

실무에서는 파이썬이라면 둘 다 직접 짜지 않고 검증된 라이브러리를 쓰는 게 맞다. 이 비교의 의미는 "어느 크기부터 구조가 상수 배를 이기는가"를 보는 것이다. 다른 언어로 구현하면 교차점이 다른 곳에 있다.

## 순위와 범위 조회가 같은 구조에서 나온다

스킵 리스트에서 범위 조회는 단순하다. `range(lo, hi)`는 윗층에서 `lo` 직전까지 건너뛰고, 그 뒤에는 0층 연결 리스트를 `hi`까지 걷는다. 시작점 찾기가 `O(log n)`이고 그 뒤는 결과 개수만큼이다. 트리에서는 중위 순회로 다음 노드를 찾는 작업이 따로 필요하다. 순위 조회는 위에서 본 `span` 합산이다.

앞의 `check.py`에서 `rank(k)`가 `bisect_left`와 같은 값을 돌려주고, `range(ref[100], ref[400])`가 `ref[100:400]`과 일치하는 것까지 확인했다. 둘 다 비교 횟수가 `find`와 같은 `O(log n)`이다. 이 문서에서는 `rank`의 시간을 따로 재지 않았다.

## 쓰지 않을 이유

- 상수 배가 작은 언어나 작은 데이터에서는 정렬 배열이 이긴다. 위 표의 10,000개 구간이 그 경우다.
- 최악 시간을 보장해야 하면 맞지 않다. 200개 구조 실험에서 보듯 구조마다 비용이 달랐다.
- 노드마다 층 수가 다른 가변 길이 포인터 배열을 가진다. 디스크 기반 구조로는 B-트리 계열이 맞다. 이 문서에서는 디스크나 캐시 라인 효율을 측정하지 않았다.
- 위 구현은 같은 키를 두 번 넣어도 막지 않는다. 중복을 허용하지 않으려면 `insert` 앞에서 `find`로 먼저 확인해야 한다.

## 정리

- 스킵 리스트는 정렬 리스트에 확률적으로 층을 얹은 구조고 재균형이 없다. 삽입은 새 노드가 올라간 층마다 포인터 하나를 바꾸는 일이다.
- 검색 평균 비교는 약 2·log2(n)이었다. n=100,000에서 31.0회.
- `p`를 1/2에서 1/4로 낮추면 비교는 같고(31.0 대 30.8) 노드당 포인터는 2.003개에서 1.335개로 줄었다. Redis는 `ZSKIPLIST_P`를 0.25, 최대 층을 32로 둔다.
- 200개 구조 중 최악은 중앙값의 1.3배였다. 입력이 오름차순이어도 비용이 같았다.
- 파이썬 구현은 약 100,000개 부근에서 `bisect.insort`와 시간이 같아졌고, 1,000,000개에서는 51.97초 대 398.17초였다.
- Redis Sorted Set의 동작은 [Redis](../DataBase/NoSQL/Redis/Redis.md) 문서에서 이어진다.
