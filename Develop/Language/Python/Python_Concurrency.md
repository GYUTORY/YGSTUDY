---
title: Python 동시성 모델 비교
tags: [python, os, language]
updated: 2026-07-16
---

# Python 동시성 모델 비교

Python의 동시성은 처음부터 헷갈린다. threading을 쓰면 멀티코어를 못 쓴다는 말도 있고, asyncio가 있으니 threading은 쓸모없다는 말도 있다. 둘 다 절반씩 맞고 절반씩 틀렸다. 무엇을 골라야 하는지는 결국 I/O bound냐 CPU bound냐에서 갈린다.

---

## 1. GIL이 실제로 하는 일

GIL(Global Interpreter Lock)은 CPython 인터프리터가 내부 자료구조를 보호하려고 만든 락이다. Python 바이트코드를 한 번에 하나의 스레드만 실행할 수 있게 막는다.

오해가 많은 부분이 있다. GIL이 있어도 threading이 전혀 쓸모없는 건 아니다. I/O 대기 중에는 GIL을 해제한다. 소켓 read, 파일 read, `time.sleep` 같은 blocking call이 실행되는 동안 다른 스레드가 GIL을 획득해서 코드를 실행할 수 있다.

```python
import time
import threading

def io_task(n):
    time.sleep(1)  # GIL을 해제하는 blocking call
    print(f"task {n} done")

# 순차 실행: 약 3초
for i in range(3):
    io_task(i)

# threading: 약 1초 (GIL이 해제되는 구간에서 병렬 실행)
threads = [threading.Thread(target=io_task, args=(i,)) for i in range(3)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

반면 CPU 작업은 GIL을 거의 해제하지 않는다. 아래 상황을 보면 스레드를 늘려도 오히려 느려진다.

```python
import threading
import time

def cpu_task():
    count = 0
    for _ in range(10_000_000):
        count += 1

# 단일 스레드: 약 0.5초
start = time.time()
cpu_task()
print(time.time() - start)

# 2 스레드: 약 0.9초 (GIL 경쟁 오버헤드로 더 느림)
start = time.time()
t1 = threading.Thread(target=cpu_task)
t2 = threading.Thread(target=cpu_task)
t1.start(); t2.start()
t1.join(); t2.join()
print(time.time() - start)
```

GIL 경쟁이 발생하면 컨텍스트 스위칭 비용까지 붙어서 단일 스레드보다 나빠진다.

---

## 2. I/O bound에서의 threading

실무에서 threading이 유효한 케이스는 주로 레거시 라이브러리 연동이나 blocking API 호출이다. requests 같은 동기 HTTP 라이브러리를 asyncio로 전환하기 어려울 때 ThreadPoolExecutor를 쓴다.

```python
from concurrent.futures import ThreadPoolExecutor
import requests

urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

def fetch(url):
    resp = requests.get(url, timeout=5)
    return resp.status_code

# 순차 실행: 약 3초
results = [fetch(url) for url in urls]

# ThreadPoolExecutor: 약 1초
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch, urls))
```

주의사항이 있다. `max_workers`를 너무 크게 잡으면 연결 수가 폭발한다. DB 커넥션 풀이 10개인데 스레드를 50개 띄우면 커넥션 대기로 병목이 바뀔 뿐이다. 대상 서비스의 커넥션 제한을 먼저 확인하고 그 안에서 설정해야 한다.

스레드 간 공유 자원에 접근할 때는 `threading.Lock`이 필요하다. GIL이 있어도 여러 연산의 원자성은 보장하지 않는다.

```python
import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    with lock:
        # read-modify-write가 원자적으로 처리됨
        counter += 1
```

`counter += 1`은 바이트코드 레벨에서 LOAD, ADD, STORE 세 단계다. GIL이 각 바이트코드 사이에서 해제될 수 있어서 락 없이는 레이스 컨디션이 생긴다.

---

## 3. CPU bound에서 multiprocessing

CPU bound 작업은 multiprocessing으로 해결한다. 프로세스마다 별도의 Python 인터프리터와 GIL을 가지므로 멀티코어를 실제로 활용할 수 있다.

```python
from multiprocessing import Pool
import os

def cpu_task(n):
    # CPU를 실제로 사용하는 작업
    result = sum(i * i for i in range(n))
    return result

if __name__ == "__main__":
    data = [5_000_000] * 8  # 8개 작업

    # 순차: 약 8초
    results = [cpu_task(n) for n in data]

    # ProcessPool (CPU 코어 수만큼 병렬): 약 2초 (4코어 기준)
    with Pool(processes=os.cpu_count()) as pool:
        results = pool.map(cpu_task, data)
```

multiprocessing의 비용은 프로세스 생성과 IPC(Inter-Process Communication)다. 프로세스 생성은 수십 밀리초가 걸리고, 프로세스 간 데이터 전달은 pickling을 거친다. 작업 하나당 처리 시간이 수십 밀리초 미만이라면 오버헤드가 이득을 상쇄한다.

```python
# 이 경우는 multiprocessing이 오히려 느리다
def trivial_task(n):
    return n * 2  # 마이크로초 수준 작업

# pickling + 프로세스 통신 비용이 계산 시간보다 크다
with Pool() as pool:
    pool.map(trivial_task, range(10000))  # 순차보다 느림
```

데이터를 프로세스 간에 공유해야 하는 경우에는 `multiprocessing.Queue`, `multiprocessing.Value`, `multiprocessing.Array`를 쓴다. 일반 Python 객체는 공유가 안 된다.

---

## 4. asyncio 이벤트 루프 구조

asyncio는 단일 스레드에서 I/O 대기 시간을 겹쳐서 처리한다. 여러 코루틴이 번갈아 실행되는데, I/O 대기 중에 다른 코루틴에게 제어권을 넘긴다.

```
이벤트 루프 실행 흐름:

coroutine A 실행
  → await io_operation()  (I/O 대기 시작, 제어권 반환)
    coroutine B 실행
      → await io_operation()  (I/O 대기 시작, 제어권 반환)
        coroutine C 실행
          → 완료
    coroutine A의 I/O 완료 → 재개
    coroutine B의 I/O 완료 → 재개
```

```python
import asyncio
import aiohttp

async def fetch(session, url):
    async with session.get(url) as resp:
        return await resp.text()

async def main():
    urls = ["https://httpbin.org/delay/1"] * 10

    async with aiohttp.ClientSession() as session:
        # gather로 10개를 동시에 대기
        results = await asyncio.gather(
            *[fetch(session, url) for url in urls]
        )
    return results

asyncio.run(main())  # 약 1초
```

asyncio의 핵심 제약은 모든 코드가 비동기여야 한다는 점이다. 중간에 blocking call이 하나라도 들어오면 이벤트 루프 전체가 멈춘다.

```python
import asyncio
import time

async def bad_coroutine():
    time.sleep(2)  # 이벤트 루프를 2초 동안 완전히 블록시킨다
    return "done"

async def other_task():
    await asyncio.sleep(0.1)
    return "other"

async def main():
    # bad_coroutine이 실행되는 동안 other_task는 전혀 실행되지 못한다
    await asyncio.gather(bad_coroutine(), other_task())
```

`requests` 같은 동기 라이브러리를 asyncio 코드에서 직접 호출하면 이 문제가 생긴다. `aiohttp`, `httpx` 같은 비동기 라이브러리로 교체하거나 `run_in_executor`를 써야 한다.

---

## 5. concurrent.futures 비교

`concurrent.futures`는 threading과 multiprocessing을 통일된 인터페이스로 감싼다. `ThreadPoolExecutor`와 `ProcessPoolExecutor`가 같은 API를 쓴다.

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time

def task(n):
    time.sleep(0.1)
    return n * 2

# ThreadPoolExecutor: I/O bound에 적합
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(task, i) for i in range(20)]
    results = [f.result() for f in futures]

# ProcessPoolExecutor: CPU bound에 적합
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(task, i) for i in range(20)]
    results = [f.result() for f in futures]
```

`executor.map`은 결과를 입력 순서대로 반환한다. 완료 순서대로 처리하려면 `as_completed`를 쓴다.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_data(url):
    # 실제 HTTP 요청이라고 가정
    import time
    time.sleep(1)
    return f"data from {url}"

urls = ["url1", "url2", "url3", "url4", "url5"]

with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_url = {executor.submit(fetch_data, url): url for url in urls}

    for future in as_completed(future_to_url):
        url = future_to_url[future]
        try:
            data = future.result()
            print(f"{url}: {data}")
        except Exception as e:
            print(f"{url}: failed with {e}")
```

`executor.submit()`은 `Future` 객체를 반환한다. `future.result()`를 호출하면 완료될 때까지 블록된다. 타임아웃을 지정하지 않으면 무한 대기한다.

```python
future = executor.submit(some_task)
try:
    result = future.result(timeout=5.0)  # 5초 안에 끝나지 않으면 예외
except TimeoutError:
    print("task timed out")
    future.cancel()  # 아직 시작 안 했으면 취소, 시작했으면 효과 없음
```

`ThreadPoolExecutor`의 기본 `max_workers`는 판올림마다 바뀌었다. Python 3.8~3.12 는 `min(32, os.cpu_count() + 4)` 이고, `os.process_cpu_count()` 가 들어온 3.13 부터는 `min(32, (os.process_cpu_count() or 1) + 4)` 다(3.14.6 에서 `inspect.getsource` 로 확인). 컨테이너에서 CPU 를 제한해 두면 두 값이 달라진다. 어느 쪽이든 I/O bound 작업에는 이 기본값이 너무 작을 수 있다.

---

## 6. asyncio + run_in_executor 혼합 패턴

실무에서 가장 자주 마주치는 패턴이다. asyncio 기반 서버에서 동기 라이브러리를 써야 하거나, CPU bound 작업을 asyncio 안에서 실행해야 할 때 쓴다.

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import requests

# 동기 함수
def sync_http_call(url):
    resp = requests.get(url, timeout=10)
    return resp.json()

def cpu_heavy(n):
    return sum(i ** 2 for i in range(n))

async def main():
    loop = asyncio.get_event_loop()

    # 동기 I/O를 스레드풀에서 실행
    thread_executor = ThreadPoolExecutor(max_workers=20)
    result = await loop.run_in_executor(
        thread_executor,
        sync_http_call,
        "https://httpbin.org/json"
    )
    print(result)

    # CPU bound를 프로세스풀에서 실행
    process_executor = ProcessPoolExecutor(max_workers=4)
    cpu_result = await loop.run_in_executor(
        process_executor,
        cpu_heavy,
        10_000_000
    )
    print(cpu_result)

asyncio.run(main())
```

`run_in_executor`에 `None`을 넘기면 기본 executor를 쓴다. 기본 executor는 스레드풀이다.

```python
async def fetch_with_requests(url):
    loop = asyncio.get_event_loop()
    # None = 기본 ThreadPoolExecutor
    return await loop.run_in_executor(None, requests.get, url)
```

FastAPI나 Starlette 기반 앱에서 동기 함수를 엔드포인트로 쓰면 내부적으로 이 패턴이 적용된다. `def` 함수로 정의한 경로 핸들러는 자동으로 스레드풀에서 실행된다.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/sync")
def sync_endpoint():
    # FastAPI가 자동으로 run_in_executor로 실행
    return {"result": slow_db_query()}

@app.get("/async")
async def async_endpoint():
    # 이벤트 루프에서 직접 실행
    # 여기서 blocking call을 쓰면 이벤트 루프가 멈춘다
    return {"result": await async_db_query()}
```

---

## 7. 타 언어와의 차이점

**Go 고루틴**

Go는 GIL이 없다. 고루틴은 Go 런타임이 OS 스레드 여러 개에 분산시킨다(M:N 스레딩). CPU bound 작업도 고루틴만으로 멀티코어를 쓸 수 있다. 초기 스택이 2KB에서 시작해 필요에 따라 커지므로 수만 개를 띄워도 메모리 부담이 작다.

Python에서 수만 개의 동시 연결을 처리하려면 asyncio가 강제된다. Go에서는 고루틴당 커넥션 패턴이 자연스럽고, asyncio 같은 별도 이벤트 루프가 필요하지 않다.

**Java 가상 스레드 (Virtual Threads)**

Java 21에서 도입된 가상 스레드는 Go 고루틴과 유사한 개념이다. JVM이 OS 스레드 위에서 수백만 개의 가상 스레드를 스케줄링한다. blocking I/O 호출이 발생하면 JVM이 자동으로 OS 스레드를 다른 가상 스레드에게 넘긴다.

Python asyncio와 달리 `await` 같은 문법 변경 없이 기존 동기 코드를 그대로 가상 스레드에서 실행할 수 있다. 라이브러리 교체 없이 동시성을 얻는 점이 큰 차이다.

Python은 이 수준의 투명한 동시성을 지원하지 않는다. asyncio를 쓰면 라이브러리부터 코드 구조까지 전부 비동기로 맞춰야 한다. GIL 때문에 고루틴이나 가상 스레드처럼 OS 스레드를 자유롭게 활용하는 모델 자체가 CPython에서는 불가능하다.

3.13 에서 실험적으로 들어온 free-threading 빌드는 3.14 부터 PEP 779 로 정식 지원 단계에 올라갔다. 이제 CPython 에서도 스레드가 여러 코어를 실제로 나눠 쓴다. 다만 여전히 기본 빌드가 아니고, C 확장을 쓰는 서드파티 패키지 중에는 준비가 안 돼 로드 시점에 GIL 을 도로 켜버리는 것들이 있다. 도입 전에 의존성부터 확인해야 한다. 아직 기본값이 아니고 서드파티 C 확장 호환성 문제가 남아있어서 실무 투입은 이르다.

---

## 8. 선택 기준

작업 특성에 따라 구분이 명확하다.

```
I/O bound, 동기 코드 유지 필요   → ThreadPoolExecutor
I/O bound, 비동기 전환 가능      → asyncio + 비동기 라이브러리
CPU bound                        → ProcessPoolExecutor 또는 multiprocessing.Pool
asyncio 앱 + 동기 라이브러리     → loop.run_in_executor(thread_executor, ...)
asyncio 앱 + CPU bound           → loop.run_in_executor(process_executor, ...)
```

실무에서 자주 생기는 실수가 있다. asyncio 앱에서 DB 쿼리를 동기 드라이버로 하는 경우다. SQLAlchemy 2.x 이전의 sync session을 asyncio 핸들러에서 직접 쓰면 이벤트 루프가 블록된다. `asyncpg`, `SQLAlchemy async`, `databases` 같은 비동기 드라이버로 전환하거나 `run_in_executor`로 격리해야 한다.

worker 수를 정하는 방법도 작업 특성에 따라 다르다. I/O bound는 대기 시간 대비 처리 시간 비율을 보고 결정한다. 대기가 99%, 처리가 1%라면 스레드 100개로 거의 100배 처리량이 나온다. CPU bound는 코어 수가 상한이다. 코어보다 많은 프로세스는 컨텍스트 스위칭 비용만 늘린다.
