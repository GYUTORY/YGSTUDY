---
title: Python asyncio 심화
tags: [python, os, language]
updated: 2026-07-19
---

# Python asyncio 심화

asyncio를 처음 배울 때는 `async def`와 `await`만 알면 되는 것처럼 보인다. 실제 서비스에 올려놓으면 Task가 제대로 취소되지 않거나, 타임아웃이 걸렸는데 코루틴이 여전히 실행되거나, 이벤트 루프 블로킹을 진단하지 못해서 레이턴시가 튀는 문제를 마주친다. 여기서는 그 부분들을 다룬다.

---

## 1. Task 생명주기

코루틴 자체는 아무것도 실행하지 않는다. `asyncio.create_task()`로 Task를 만들어야 이벤트 루프가 실행을 예약한다.

```python
import asyncio

async def work():
    await asyncio.sleep(1)
    return "done"

async def main():
    # 코루틴 객체만 생성, 실행 안 됨
    coro = work()

    # Task로 감싸야 이벤트 루프가 실행을 예약
    task = asyncio.create_task(coro)

    print(task.done())       # False (아직 실행 중)
    print(task.cancelled())  # False

    result = await task
    print(task.done())       # True
    print(task.result())     # "done"
```

Task는 네 가지 상태를 거친다.

- **Pending**: `create_task()` 직후. 이벤트 루프 큐에 올라가 있음
- **Running**: 이벤트 루프가 코루틴을 실제로 실행 중
- **Done**: 정상 완료, 예외 발생, 또는 취소로 인해 종료
- **Cancelled**: `task.cancel()`이 성공한 경우 (Done의 하위 상태)

`task.result()`는 Done 상태가 아니면 `InvalidStateError`를 던진다. `task.exception()`은 예외로 종료된 경우 예외 객체를 반환하고, 취소된 경우 `CancelledError`를 던진다.

---

## 2. Task.cancel()과 CancelledError

`task.cancel()`은 실행 중인 코루틴에 `CancelledError`를 주입하는 요청이다. 즉시 종료가 아니다. 코루틴이 `await` 지점에 도달해야 `CancelledError`가 발생한다.

```python
import asyncio

async def cancellable():
    try:
        print("starting")
        await asyncio.sleep(10)  # 여기서 CancelledError 주입됨
        print("이 줄은 실행되지 않는다")
    except asyncio.CancelledError:
        print("취소 처리 중")
        # cleanup 코드 실행 가능
        raise  # 반드시 다시 raise해야 한다

async def main():
    task = asyncio.create_task(cancellable())
    await asyncio.sleep(0.1)  # task가 실행될 시간을 준다

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("task가 취소됨")
        print(task.cancelled())  # True
```

`except asyncio.CancelledError`에서 `raise`를 빠뜨리면 Task가 취소됐는데도 정상 완료로 처리된다. 이 경우 `task.cancelled()`가 `False`로 나온다. 부모 코루틴이 취소 여부를 판단할 수 없게 되므로, cleanup 후 반드시 재발생시켜야 한다.

`task.cancel()`이 `True`를 반환했다고 Task가 실제로 취소된 건 아니다. 코루틴이 `CancelledError`를 잡아서 무시한 경우에도 `cancel()`은 `True`를 반환한다. 실제 취소 여부는 `await task` 이후 `task.cancelled()`로 확인해야 한다.

취소 메시지도 전달할 수 있다.

```python
task.cancel(msg="timeout exceeded")

try:
    await task
except asyncio.CancelledError as e:
    print(e)  # Python 3.9+에서 msg 접근 가능
```

---

## 3. asyncio.shield()

취소 요청을 받아도 특정 코루틴은 완료시켜야 하는 경우가 있다. DB 트랜잭션 커밋이나 결제 처리처럼 중간에 끊으면 안 되는 작업이다.

`asyncio.shield()`는 내부 코루틴을 취소로부터 격리한다. 외부 Task가 취소되면 `await shield(...)` 지점에서 `CancelledError`가 발생하지만, 내부 작업은 계속 실행된다.

```python
import asyncio

async def critical_cleanup():
    print("cleanup 시작")
    await asyncio.sleep(2)  # 이 작업은 취소되면 안 됨
    print("cleanup 완료")

async def main_task():
    try:
        await asyncio.shield(critical_cleanup())
    except asyncio.CancelledError:
        print("main_task는 취소됐지만 cleanup은 계속 실행됨")
        raise

async def main():
    task = asyncio.create_task(main_task())
    await asyncio.sleep(0.1)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # cleanup은 아직 실행 중이므로 기다려야 한다
    await asyncio.sleep(3)
```

`shield()`가 반환한 Future를 별도 변수에 저장하지 않으면 내부 코루틴이 완료돼도 결과를 가져올 방법이 없다. cleanup처럼 반환값이 필요 없는 경우엔 상관없지만, 반환값이 필요하다면 shield된 Future를 저장해야 한다.

```python
async def main_task():
    shielded = asyncio.shield(critical_cleanup())
    try:
        result = await shielded
    except asyncio.CancelledError:
        # shielded는 계속 실행 중
        # 나중에 await shielded로 결과를 가져올 수 있다
        raise
```

---

## 4. TaskGroup (Python 3.11+)

`asyncio.gather()`로 여러 Task를 실행할 때 예외 처리가 까다롭다. 하나가 실패해도 나머지 Task는 계속 실행되고, 예외는 `gather()`를 `await`할 때 첫 번째 것만 올라온다.

`TaskGroup`은 구조적 동시성을 구현한다. `async with` 블록 안에서 생성된 모든 Task는 블록을 벗어날 때 반드시 완료되거나 취소된다.

```python
import asyncio

async def fetch(n):
    await asyncio.sleep(n * 0.1)
    if n == 3:
        raise ValueError(f"task {n} failed")
    return f"result {n}"

async def main():
    results = []

    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch(i)) for i in range(5)]
    except* ValueError as eg:
        # ExceptionGroup을 except*로 처리 (Python 3.11+)
        for exc in eg.exceptions:
            print(f"처리된 예외: {exc}")

    # TaskGroup 블록이 끝난 후 완료된 task의 결과 접근
    for task in tasks:
        if not task.cancelled() and task.exception() is None:
            results.append(task.result())

    print(results)
```

`TaskGroup`에서 하나의 Task가 예외를 던지면 나머지 Task가 자동으로 취소된다. `gather(return_exceptions=True)`처럼 예외를 묻지 않고, 실패 즉시 전체를 정리한다.

`except*`는 `ExceptionGroup`을 처리하는 문법이다. 여러 Task가 동시에 예외를 던진 경우 모두 수집해서 `ExceptionGroup`으로 묶어준다.

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(failing_task_1())
        tg.create_task(failing_task_2())
    # 두 예외가 모두 ExceptionGroup에 담긴다
```

`gather()`와 비교하면 차이가 명확하다.

```
gather()
  - 예외 발생 시 나머지 Task는 계속 실행 (기본)
  - 예외는 첫 번째 것만 전파
  - Task 취소는 수동으로 해야 함

TaskGroup
  - 예외 발생 시 나머지 Task 자동 취소
  - 모든 예외를 ExceptionGroup으로 수집
  - 블록 종료 시 모든 Task 완료 보장
```

---

## 5. gather 예외 처리 패턴

`asyncio.gather()`는 3.11 이전 코드베이스나 예외를 개별적으로 처리해야 하는 경우에 여전히 자주 쓴다.

기본 동작은 첫 번째 예외를 그대로 전파한다.

```python
import asyncio

async def task(n):
    if n == 2:
        raise ValueError("task 2 failed")
    await asyncio.sleep(n * 0.1)
    return n

async def main():
    try:
        # 기본: 첫 예외가 전파되고 나머지 task는 계속 실행됨
        results = await asyncio.gather(
            task(1),
            task(2),  # 여기서 예외 발생
            task(3),  # 이 task는 백그라운드에서 계속 실행됨
        )
    except ValueError as e:
        print(f"예외: {e}")
        # task(3)은 아직 실행 중. 취소하지 않으면 결과가 버려진다
```

`return_exceptions=True`를 쓰면 예외를 결과 목록에 담아서 반환한다.

```python
async def main():
    results = await asyncio.gather(
        task(1),
        task(2),
        task(3),
        return_exceptions=True
    )

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"task {i} failed: {result}")
        else:
            print(f"task {i} succeeded: {result}")
```

예외 Task만 재시도하거나 개별 처리할 때 `return_exceptions=True`가 편하다.

한 가지 주의점이 있다. `CancelledError`도 `return_exceptions=True`로 잡힌다. Python 3.8 이후 `CancelledError`는 `Exception`의 하위 클래스다. `gather()`가 취소되면 `CancelledError`가 결과 배열에 들어온다.

```python
results = await asyncio.gather(*tasks, return_exceptions=True)

for result in results:
    if isinstance(result, asyncio.CancelledError):
        print("이 task는 취소됐다")
    elif isinstance(result, Exception):
        print(f"이 task는 실패했다: {result}")
    else:
        print(f"성공: {result}")
```

---

## 6. asyncio.timeout과 wait_for 차이

`asyncio.wait_for()`는 타임아웃이 걸리면 내부 코루틴을 취소하고 `TimeoutError`를 던진다.

```python
import asyncio

async def slow_task():
    await asyncio.sleep(10)
    return "done"

async def main():
    try:
        result = await asyncio.wait_for(slow_task(), timeout=1.0)
    except asyncio.TimeoutError:
        print("타임아웃")
```

Python 3.11에서 `asyncio.timeout()`이 추가됐다. 컨텍스트 매니저 형태라서 여러 `await`에 걸쳐 타임아웃을 적용할 수 있다.

```python
import asyncio

async def main():
    try:
        async with asyncio.timeout(5.0):
            await asyncio.sleep(1)
            # 타임아웃이 여기에도 계속 적용됨
            result = await fetch_data()
            await process_result(result)
    except TimeoutError:
        print("전체 블록 타임아웃")
```

`wait_for()`는 단일 코루틴 하나에 적용한다. `timeout()`은 블록 안의 모든 `await`에 누적으로 적용된다.

```
wait_for(coro, timeout=N)
  - 단일 코루틴 하나에 타임아웃
  - 타임아웃 시 내부 코루틴 취소
  - TimeoutError 발생

asyncio.timeout(N)
  - 블록 전체에 타임아웃 (여러 await 포함)
  - 타임아웃 시 현재 await 중인 Task 취소
  - TimeoutError 발생
```

`timeout()`은 타임아웃 시간을 동적으로 변경할 수 있다.

```python
async def main():
    async with asyncio.timeout(10.0) as cm:
        result = await step_1()

        # 남은 시간을 확인하고 조정
        cm.reschedule(asyncio.get_event_loop().time() + 5.0)

        result2 = await step_2()
```

`wait_for()`에서 주의할 점이 있다. 타임아웃이 발생하면 내부 코루틴 취소를 기다린다. 내부 코루틴이 `CancelledError`를 잡아서 오래 걸리는 정리 작업을 하면 `wait_for()`가 타임아웃 후에도 한동안 블록된다.

```python
async def slow_cleanup():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        await asyncio.sleep(5)  # 취소 후에도 5초 더 걸림
        raise

# wait_for의 timeout=1.0인데 실제로는 6초 걸릴 수 있다
await asyncio.wait_for(slow_cleanup(), timeout=1.0)
```

---

## 7. 이벤트 루프 직접 제어

대부분의 경우 `asyncio.run()`으로 충분하다. 프레임워크를 만들거나 테스트 환경을 구성하거나 이벤트 루프를 공유해야 할 때 직접 제어가 필요하다.

```python
import asyncio

# asyncio.run()이 하는 일을 직접 구현하면
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

try:
    result = loop.run_until_complete(main())
finally:
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.run_until_complete(loop.shutdown_default_executor())
    loop.close()
```

`asyncio.get_event_loop()`는 현재 실행 중인 루프를 반환한다. 코루틴 안에서는 `asyncio.get_running_loop()`를 써야 한다. `get_event_loop()`는 실행 중인 루프가 없을 때 경고 없이 새 루프를 만들 수 있어서 예상치 못한 동작이 생긴다.

```python
async def get_loop_example():
    # 코루틴 안에서는 이걸 써라
    loop = asyncio.get_running_loop()
```

스레드에서 이벤트 루프에 코루틴을 제출해야 하는 경우가 있다.

```python
import asyncio
import threading
import time

loop = None

def run_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

# 별도 스레드에서 이벤트 루프 실행
thread = threading.Thread(target=run_loop, daemon=True)
thread.start()

time.sleep(0.1)  # loop가 시작될 시간을 준다

# 메인 스레드에서 이벤트 루프에 코루틴 제출
future = asyncio.run_coroutine_threadsafe(some_coroutine(), loop)
result = future.result(timeout=5.0)  # 결과를 동기적으로 대기
```

`asyncio.run_coroutine_threadsafe()`는 스레드 안전하다. `loop.call_soon()`과 달리 다른 스레드에서 호출할 수 있다.

---

## 8. asyncio 디버그 모드

디버그 모드를 켜면 이벤트 루프가 추가적인 검사를 수행한다.

- 100ms 이상 블록하는 코루틴 감지
- 코루틴을 `await` 없이 사용하면 경고
- `Future`를 닫을 때 미처리 예외 경고
- 느린 콜백 로깅

```python
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

async def main():
    await asyncio.sleep(1)

asyncio.run(main(), debug=True)
```

환경 변수로도 켤 수 있다.

```bash
PYTHONASYNCIODEBUG=1 python my_script.py
```

디버그 모드에서 블로킹 코드를 넣으면 바로 잡힌다.

```python
import asyncio
import time

async def bad():
    time.sleep(0.2)  # 200ms 블록

async def main():
    await bad()

asyncio.run(main(), debug=True)
# Executing <Task ...> took 0.201 seconds
# 100ms 이상 블록했다는 경고가 출력된다
```

slow callback 감지 임계값을 낮출 수 있다.

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
    loop.slow_callback_duration = 0.05  # 50ms 이상이면 경고 (기본 100ms)

    await run_app()
```

디버그 모드는 성능 오버헤드가 있다. 프로덕션에서는 꺼야 하고, 개발 중이나 성능 문제 진단 시에만 켠다.

---

## 9. 블로킹 코드 혼입 진단

asyncio 앱에서 레이턴시가 갑자기 튀거나, 높은 부하에서 처리량이 예상보다 낮을 때 블로킹 코드 혼입을 먼저 의심해야 한다.

코드에서 직접 찾는다면 `time.sleep`, `requests.get`, 동기 DB 쿼리 같은 패턴을 찾는다.

```python
# 이것들이 asyncio 코루틴 안에 있으면 문제다
import time
time.sleep(1)          # 이벤트 루프 블록

import requests
requests.get(url)      # 이벤트 루프 블록

import psycopg2
conn.execute(query)    # 동기 DB 쿼리, 이벤트 루프 블록
```

ORM 혼용 실수가 실무에서 자주 나온다. SQLAlchemy ORM을 asyncio 코드에서 sync session으로 쓰거나, Django ORM을 직접 호출하는 경우다.

```python
# 이 코드는 이벤트 루프를 블록시킨다
async def get_user(user_id: int):
    user = User.objects.get(id=user_id)  # Django ORM sync, 블로킹
    return user

# 방법 1: 비동기 ORM 사용
async def get_user(user_id: int):
    user = await User.objects.aget(id=user_id)  # Django 4.1+
    return user

# 방법 2: run_in_executor로 격리
async def get_user(user_id: int):
    loop = asyncio.get_running_loop()
    user = await loop.run_in_executor(
        None,
        lambda: User.objects.get(id=user_id)
    )
    return user
```

Python 파일 I/O도 문제가 된다. `open()`과 `f.read()`는 블로킹이다. 파일 작업이 많다면 `aiofiles`를 쓴다.

```python
import aiofiles

async def read_config():
    async with aiofiles.open("config.json", "r") as f:
        content = await f.read()
    return content
```

`subprocess.run()`도 블로킹이다. asyncio에서는 `asyncio.create_subprocess_exec()`를 쓴다.

```python
import asyncio

async def run_command(cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode()
```
