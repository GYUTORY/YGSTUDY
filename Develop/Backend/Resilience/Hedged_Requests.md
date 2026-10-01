---
title: 헤지 요청 - 꼬리 지연을 줄이고 부하로 값을 치르는 방법
tags: [backend, performance, architecture, python]
updated: 2026-10-01
---

# 헤지 요청 - 꼬리 지연을 줄이고 부하로 값을 치르는 방법

평균 응답 시간이 20ms인 서비스에서 가끔 300ms가 걸리는 요청이 섞여 있다고 하자. 호출 하나만 보면 1%의 일이다. 그런데 화면 하나가 이 서비스를 병렬로 100번 부르면 그 화면이 느려질 확률은 1 - 0.99^100 = 63.4%다. 10번이면 9.6%, 1번이면 1%다. 팬아웃이 커질수록 p99는 "가끔"이 아니라 "거의 매번"이 된다. 구글이 이 현상을 정리한 글이 [The Tail at Scale](https://research.google/pubs/the-tail-at-scale/)이고, 그 글에서 제안하는 방어책 중 가장 단순한 것이 **헤지 요청**이다.

헤지 요청은 첫 요청이 일정 시간 안에 응답하지 않으면 **같은 요청을 다른 복제본에 한 번 더 보내고 먼저 오는 응답을 쓰는** 방식이다. 재시도와 비슷해 보이지만 첫 요청을 끊지 않고 계속 기다린다는 점이 다르다. 타임아웃 후 재시도는 실패를 가정하고, 헤지는 "느릴 뿐 아직 살아 있다"를 가정한다.

이 문서는 헤지가 p99를 얼마나 줄이는지와, 그 대가인 추가 부하가 어느 조건에서 효과를 뒤집는지를 직접 돌린 결과로 보인다. 아래 수치는 이 문서의 가짜 백엔드와 시뮬레이터에서 나온 값이고, 실제 서비스의 분포는 다르다. 재시도·서킷브레이커 같은 일반 장애 대응은 [장애 대응 패턴](Fault_Tolerance.md), 과부하를 막는 격벽은 [Rate Limiting · Bulkhead](Rate_Limiting_and_Bulkhead.md)에 있다. 헤지는 같은 요청이 두 번 실행될 수 있으니 [API 멱등성](../API/API_Idempotency.md)이 먼저 갖춰져 있어야 한다.

## 가장 작은 구현

asyncio로 쓴 헤지다. 백엔드는 90%가 20ms, 10%가 300ms에 응답하는 가짜 서비스다.

```python
import asyncio, random, time

async def backend(name: str, rnd: random.Random) -> str:
    await asyncio.sleep(0.3 if rnd.random() < 0.10 else 0.02)
    return name

async def hedged(call, delay: float, replicas: list[str]):
    """첫 요청이 delay 안에 안 끝나면 다음 복제본에 같은 요청을 보내고, 먼저 끝난 쪽을 쓴다."""
    tasks = [asyncio.ensure_future(call(replicas[0]))]
    try:
        for nxt in replicas[1:]:
            done, _ = await asyncio.wait(tasks, timeout=delay, return_when=asyncio.FIRST_COMPLETED)
            if done:
                break
            tasks.append(asyncio.ensure_future(call(nxt)))
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        return next(iter(done)).result()
    finally:
        for t in tasks:                       # 진 쪽을 반드시 취소한다
            if not t.done():
                t.cancel()
```

2,000번씩 순차 호출한 결과다(Python 3.10).

```text
헤지 없음   p50=  20.2ms  p99= 300.7ms  max= 340.1ms
헤지 50ms   p50=  20.3ms  p99=  77.0ms  max= 301.3ms
```

p99가 300ms에서 77ms로 내려갔고 p50은 그대로다. 느린 요청(300ms)이 걸리면 50ms를 기다린 뒤 두 번째 복제본에 보내고, 거기서 20ms에 응답이 오니 70ms 안팎에서 끝난다. 600번 돌려 지연을 10ms 단위로 묶어 본 분포는 20ms가 538건, 70ms가 52건, 300ms가 10건이었다. 300ms로 남은 것은 첫 요청과 두 번째 요청이 **둘 다** 느린 경우(0.1 × 0.1 = 1%)이고, max가 여전히 301ms인 이유도 이것이다. 헤지는 느릴 확률을 제곱으로 줄일 뿐 0으로 만들지는 않는다.

헤지로 나간 추가 요청은 첫 요청이 50ms 안에 끝나지 않은 비율, 즉 약 10%다. 요청당 평균 1.1번 호출하는 셈이다. 이 비용이 바로 다음 절에서 문제가 된다.

## 시뮬레이션: 부하가 오르면 어떻게 달라지나

위 실험은 백엔드가 요청 수에 영향을 받지 않는 이상적인 경우다. 실제 서버는 큐가 있고, 헤지 요청도 그 큐에 줄을 선다. 서버 10대, 서버당 워커 1개와 FIFO 큐, 서비스 시간은 95%가 평균 10ms, 5%가 평균 100ms인 지수분포로 이벤트 시뮬레이션을 짰다. 서비스 시간만 따지면 p50 7.4ms, p95 40ms, p99 161ms다. 부하 ρ는 **헤지를 안 했을 때** 서버 이용률이다.

```python
import heapq, random, itertools
from collections import deque

def sim(rho, hedge_delay=None, cancel=True, correlated=False, n_servers=10, n_req=60000, seed=1):
    rnd = random.Random(seed)
    def svc():
        return rnd.expovariate(1/0.100) if rnd.random() < 0.05 else rnd.expovariate(1/0.010)
    mean_svc = 0.95*0.010 + 0.05*0.100
    lam = rho * n_servers / mean_svc
    ev, seq = [], itertools.count()
    push = lambda t, kind, *a: heapq.heappush(ev, (t, next(seq), kind, a))
    q = [deque() for _ in range(n_servers)]
    cur = [None]*n_servers                  # 서버가 처리 중인 copy
    t = 0.0
    for i in range(n_req):
        t += rnd.expovariate(lam); push(t, 'arr', i)
    lat, copies_sent = {}, 0

    def start_next(s, now):
        while q[s]:
            c = q[s].popleft()
            if c['cancel']: continue
            cur[s] = c; c['srv'] = s
            push(now + c['svc'], 'done', c)
            return
        cur[s] = None

    def enqueue(r, s, now):
        nonlocal copies_sent
        copies_sent += 1
        c = {'req': r, 'cancel': False, 'svc': r['svc0'] if correlated and r['copies'] else svc(), 'srv': None}
        r['copies'].append(c)
        q[s].append(c)
        if cur[s] is None: start_next(s, now)

    while ev:
        now, _, kind, a = heapq.heappop(ev)
        if kind == 'arr':
            r = {'id': a[0], 'arrive': now, 'done': False, 'copies': [], 'svc0': svc(), 'first': rnd.randrange(n_servers)}
            c = {'req': r, 'cancel': False, 'svc': r['svc0'], 'srv': None}   # correlated 면 헤지 copy 도 svc0 를 쓴다
            r['copies'].append(c); copies_sent += 1; q[r['first']].append(c)
            if cur[r['first']] is None: start_next(r['first'], now)
            if hedge_delay is not None: push(now + hedge_delay, 'hedge', r)
        elif kind == 'hedge':
            r = a[0]
            if not r['done']:
                s = rnd.choice([x for x in range(n_servers) if x != r['first']])
                enqueue(r, s, now)
        else:
            c = a[0]
            if c['cancel']: continue
            r = c['req']; s = c['srv']
            cur[s] = None
            if not r['done']:
                r['done'] = True; lat[r['id']] = now - r['arrive']
                if cancel:
                    for o in r['copies']:
                        if o is c or o['cancel']: continue
                        o['cancel'] = True
                        if o['srv'] is not None and cur[o['srv']] is o:      # 처리 중이면 즉시 중단
                            s2 = o['srv']; cur[s2] = None; start_next(s2, now)
            start_next(s, now)
    xs = sorted(lat.values())
    pct = lambda p: xs[int(p*(len(xs)-1))]*1000
    return pct(.5), pct(.99), pct(.999), copies_sent/n_req
```

`cancel`은 먼저 끝난 요청의 복제본을 큐에서 빼거나 처리 중이면 중단시키는지, `correlated`는 느린 이유가 서버가 아니라 **요청 자체**(무거운 쿼리, 큰 페이로드)여서 두 번째 복제본도 같은 시간이 걸리는지를 정한다. 지연은 30ms로 두었다(서비스 시간 p90과 p95 사이). 단위는 ms이고 마지막 열은 요청 하나당 실제로 서버에 들어간 요청 수다.

| 부하 | 조건 | p50 | p99 | p99.9 | 요청수/요청 |
|---|---|---|---|---|---|
| 0.3 | 헤지 없음 | 11.0 | 323.7 | 542.8 | 1.00 |
| 0.3 | 헤지, 취소 O | 9.6 | 52.1 | 94.2 | 1.13 |
| 0.3 | 헤지, 취소 X | 12.9 | 127.7 | 265.4 | 1.26 |
| 0.3 | 헤지, 취소 O, 지연이 요청에 고정 | 13.3 | 218.0 | 427.6 | 1.28 |
| 0.6 | 헤지 없음 | 22.3 | 514.1 | 900.3 | 1.00 |
| 0.6 | 헤지, 취소 O | 13.8 | 63.3 | 105.4 | 1.22 |
| 0.6 | 헤지, 취소 X | 10,850 | 27,749 | 30,548 | 1.99 |
| 0.6 | 헤지, 취소 O, 지연이 요청에 고정 | 33.0 | 311.4 | 542.6 | 1.55 |
| 0.8 | 헤지 없음 | 67.8 | 1,016 | 1,501 | 1.00 |
| 0.8 | 헤지, 취소 O | 18.7 | 76.8 | 134.9 | 1.32 |
| 0.8 | 헤지, 취소 X | 29,450 | 62,469 | 65,877 | 2.00 |
| 0.8 | 헤지, 취소 O, 지연이 요청에 고정 | 338.4 | 865.1 | 1,056 | 1.96 |

헤지 없이도 p99가 서비스 시간 p99(161ms)보다 2~6배 큰 것은 느린 요청이 앞에서 서버를 잡고 있는 동안 뒤의 요청이 같이 기다리는 큐잉 때문이다. 이 뒤에 서는 요청은 서버가 멀쩡해도 느려진다.

표에서 읽어야 할 것은 세 가지다.

**취소 X는 부하를 두 배로 만들고 시스템을 무너뜨린다.** 부하가 오르면 큐 대기만으로 30ms를 넘기는 요청이 늘어 거의 모든 요청이 헤지되고(요청수/요청 1.99), 이긴 쪽이 응답한 뒤에도 진 쪽이 계속 서버를 점유하면 이용률이 0.6 × 2 = 1.2로 100%를 넘는다. 큐가 끝없이 자라서 p50이 10초대로 올라갔다(시뮬레이션이 끝날 때까지 쌓인 대기 시간이라 절댓값에 큰 의미는 없고, 발산했다는 사실이 핵심이다). 부하 0.3에서는 이용률이 0.6 안팎에 머물러 버텼고 취소 O보다 p99가 2.5배 나쁜 수준에서 끝났다. **같은 코드가 평소에는 멀쩡하다가 트래픽이 늘어난 날 갑자기 무너진다.** 로컬 테스트나 한가한 시간대 측정으로는 안 보인다.

**지연이 요청에 고정되어 있으면 헤지는 이득 없이 부하만 낸다.** 요청 자체가 무거운 경우(전체 기간 집계 쿼리, 거대한 응답)는 어느 서버에 보내도 느리다. 부하 0.3에서는 p99가 323에서 218로 줄어 아직 보람이 있지만, 부하 0.8에서는 p50이 67.8에서 338.4로 5배 나빠졌다. 느린 이유가 서버 쪽 일시 현상(GC, 컴팩션, 이웃 부하, 캐시 미스)인지 요청 쪽 고정 비용인지 모르고 헤지를 켜면 이 칸에 떨어진다.

**취소가 있으면 부하 0.8에서도 이득이 유지된다.** p99가 1,016ms에서 76.8ms로 내려가고 요청수는 1.32배다. 헤지의 추가 비용은 "복제본이 아직 처리 중일 때 중단할 수 있느냐"에 달려 있다.

## 헤지 지연은 어떻게 정하나

너무 짧으면 거의 모든 요청이 두 번 나가고, 너무 길면 효과가 없다. 부하 0.6, 취소 O에서 지연만 바꿔 돌렸다(서비스 시간 p95 = 40ms).

| 헤지 지연 | p50 | p99 | p99.9 | 요청수/요청 |
|---|---|---|---|---|
| 없음 | 22.3 | 514.1 | 900.3 | 1.00 |
| 5ms | 8.7 | 41.2 | 77.2 | 1.76 |
| 15ms | 12.7 | 49.8 | 91.0 | 1.44 |
| 30ms | 13.8 | 63.3 | 105.4 | 1.22 |
| 60ms | 15.6 | 96.9 | 161.8 | 1.11 |
| 150ms | 18.7 | 178.6 | 256.1 | 1.05 |

지연을 짧게 줄일수록 p99는 좋아지지만 추가 요청 비율이 올라간다. 위 구간에서는 60ms 근처(요청수 +11%에 p99 514에서 97)가 비용 대비 효율이 좋고, 5ms는 p99는 가장 낮아도 서버 호출이 76% 늘어난다. 서비스에 따라 최적점은 달라서 **"p95 근처"를 출발점으로 두고 추가 요청 비율이 몇 %를 넘지 않게 상한을 걸어 가며 조정**하는 식으로 접근한다. The Tail at Scale도 지연을 해당 요청 종류의 p95 근처로 두라고 제안한다. 정적 값으로 박아 두면 서비스가 느려지는 날 모든 요청이 헤지되므로, 지연은 최근 응답 시간 분포에서 주기적으로 다시 계산한다.

## 조용히 깨지는 지점

- **취소를 구현하지 않았다.** 위 asyncio 코드에서 `finally` 블록의 `t.cancel()`을 빼면 호출자 쪽 태스크는 계속 돈다. 더 큰 문제는 취소가 **서버까지 전달되는지**다. 클라이언트가 연결을 끊어도 서버 핸들러가 끝까지 도는 프레임워크가 있다. gRPC는 컨텍스트 취소가 전파되지만 서버 코드가 그 컨텍스트를 확인해야 한다. 서버가 무시하면 위 표의 "취소 X" 줄과 같은 결과다.
- **멱등하지 않은 호출에 건다.** 결제, 재고 차감, 메시지 발송에 헤지를 걸면 같은 요청이 두 번 실행될 수 있다. 읽기 요청이나 멱등 키가 있는 쓰기에만 건다.
- **헤지 위에 재시도를 쌓는다.** 헤지(최대 2배)가 재시도(최대 3회)와 곱해져 장애 때 서버 호출이 6배까지 늘 수 있다. 장애 중에는 이미 느린 서버에 호출이 몰려 회복을 막는다. 헤지·재시도가 합쳐서 쓸 수 있는 추가 요청의 **총량 상한**을 두고, 서킷브레이커가 열리면 헤지도 끈다.
- **복제본이 같은 것에 의존한다.** 두 복제본이 같은 DB 샤드를 보면 느림의 원인이 공유 자원일 때 둘 다 느려진다. 위 `correlated` 줄과 같은 결과다.
- **효과를 지표로 안 본다.** 헤지 발동률(헤지가 나간 요청 비율)과 헤지 승률(두 번째 요청이 이긴 비율)을 따로 기록한다. 승률이 낮은데 발동률이 높으면 지연이 너무 짧거나 느린 원인이 요청 쪽에 있다는 신호다.

## 헤지를 쓰지 않는 편이 나은 경우

- 서버가 이미 포화 상태다. 추가 요청은 큐를 키운다. 부하를 먼저 줄인다.
- 복제본이 하나뿐이다. 같은 서버에 두 번 보내면 큐에서 자기 자신과 경쟁한다.
- 응답이 크거나 비용이 큰 쓰기다. 두 번 처리하는 것 자체가 낭비다.
- p99가 아니라 p50이 문제다. 헤지는 꼬리만 자른다. p50이 느리다면 쿼리, 인덱스, N+1 문제를 먼저 본다.

참고: [The Tail at Scale (Dean, Barroso)](https://research.google/pubs/the-tail-at-scale/).
