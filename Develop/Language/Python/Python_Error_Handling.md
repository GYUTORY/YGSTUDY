---
title: Python 예외 처리
tags: [python, backend, language]
updated: 2026-07-18
---

# Python 예외 처리

Python은 예외를 흐름 제어 수단으로 적극 쓴다. `StopIteration`으로 이터레이터 종료를 알리고, `KeyboardInterrupt`로 Ctrl+C를 처리하는 것처럼, 예외가 "오류"만을 의미하지 않는다. 이 구조를 제대로 이해하지 않으면 잡아야 할 예외를 놓치거나, 잡으면 안 되는 예외까지 삼켜버리는 실수를 한다.

---

## 1. try/except/else/finally 실제 동작

`else` 블록은 처음 보면 용도가 애매해 보인다. `try` 블록이 예외 없이 완료됐을 때만 실행된다.

```python
def read_config(path: str) -> dict:
    try:
        f = open(path)
    except FileNotFoundError:
        return {}
    else:
        # try가 성공했을 때만 여기 진입
        # f.read()에서 발생하는 예외는 위 except에 잡히지 않음
        data = f.read()
        f.close()
        return json.loads(data)
    finally:
        # 예외 발생 여부와 무관하게 항상 실행
        # return이 있어도 실행됨
        print("read_config 종료")
```

`else`를 쓰는 이유는 예외 범위를 좁히기 위해서다. `try` 안에 `f.read()`까지 넣으면 `FileNotFoundError`로 잡아야 할 예외 외에 `json.JSONDecodeError`도 같은 `except` 블록에 들어올 수 있다. 의도치 않은 예외를 조용히 삼키는 원인이 된다.

`finally`는 함수 안에 `return`이 있어도 실행된다. 단, `finally` 블록 자체에 `return`이 있으면 `try`나 `except`의 `return` 값을 덮어쓴다. 이건 헷갈리는 동작이라 `finally`에는 정리(close, rollback) 코드만 두는 게 낫다.

---

## 2. 예외 계층 구조

```
BaseException
├── SystemExit
├── KeyboardInterrupt
├── GeneratorExit
└── Exception
    ├── RuntimeError
    ├── ValueError
    ├── TypeError
    ├── OSError
    │   └── FileNotFoundError
    ├── StopIteration
    └── ...
```

`except Exception`은 `SystemExit`, `KeyboardInterrupt`, `GeneratorExit`를 잡지 않는다. 세 가지는 `BaseException`의 직접 자식이다.

`except BaseException`이나 `except:` (빈 except)를 쓰면 Ctrl+C로 프로세스를 종료할 수 없게 된다. `KeyboardInterrupt`까지 삼켜버리기 때문이다. 서버 코드에서 이런 패턴이 있으면 배포 후 종료가 안 된다.

```python
# 나쁜 패턴 — KeyboardInterrupt를 삼킴
while True:
    try:
        do_something()
    except BaseException:
        pass

# 의도적으로 KeyboardInterrupt를 처리해야 한다면 명시적으로
while True:
    try:
        do_something()
    except KeyboardInterrupt:
        cleanup()
        break
    except Exception as e:
        logger.error(e)
```

`SystemExit`은 `sys.exit()`이 내부적으로 던지는 예외다. `except Exception`으로는 잡히지 않아서 정상 종료 흐름을 방해하지 않는다.

---

## 3. 예외 체이닝

예외를 변환할 때 원인이 되는 예외 정보를 보존해야 한다. `raise ... from`이 그 역할을 한다.

```python
class DatabaseError(Exception):
    pass

def get_user(user_id: int):
    try:
        result = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    except sqlite3.OperationalError as e:
        raise DatabaseError(f"사용자 조회 실패: {user_id}") from e
```

`from e`를 붙이면 트레이스백에 원인 예외가 함께 출력된다.

```
DatabaseError: 사용자 조회 실패: 42

The above exception was the direct cause of the following exception:
...
```

`from None`을 쓰면 체인을 끊는다. 외부에 내부 구현 세부 사항(SQL 에러 메시지 등)을 노출하지 않으려 할 때 쓴다.

```python
raise DatabaseError("연결 실패") from None
```

`raise` 단독 사용(인자 없음)은 현재 처리 중인 예외를 그대로 다시 던진다. 로깅 후 예외를 상위로 전파할 때 쓴다.

```python
try:
    risky_operation()
except ValueError:
    logger.exception("예상치 못한 입력값")
    raise  # 예외 정보 그대로 상위로 전파
```

---

## 4. contextlib.suppress

특정 예외를 무시할 때 `try/except/pass` 대신 쓸 수 있다.

```python
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove("/tmp/cache.tmp")
```

편리해 보이지만 남용하면 문제가 생긴다. `suppress`는 컨텍스트 블록 안에서 발생한 모든 해당 예외를 삼킨다. 블록 안에 코드가 여러 줄이면 어느 줄에서 예외가 발생했는지 파악하기 어렵다.

```python
# 이렇게 쓰면 어디서 FileNotFoundError가 났는지 모름
with suppress(FileNotFoundError):
    config = load_config("/etc/app/config.yaml")
    process(config)  # 여기서 발생한 FileNotFoundError도 삼킴
```

`suppress`는 단일 동작, 예외 발생이 명확하게 예상되는 곳에서만 쓴다. 여러 줄 블록에는 명시적인 `try/except`가 더 안전하다.

---

## 5. 커스텀 예외 설계

커스텀 예외를 만들 때 `Exception`을 직접 상속하는 건 작은 프로젝트에서나 통한다. 실무에서는 도메인별 기반 클래스를 두고 그 아래로 구체 예외를 파생시킨다.

```python
class AppError(Exception):
    """애플리케이션 전체 기반 예외"""
    pass

class ServiceError(AppError):
    """비즈니스 로직 레이어 예외"""
    pass

class RepositoryError(AppError):
    """데이터 접근 레이어 예외"""
    pass
```

이렇게 해두면 특정 레이어 예외만 잡거나(`except ServiceError`), 전체 앱 예외를 잡는(`except AppError`) 두 가지 레벨로 처리할 수 있다.

예외에 추가 정보를 담을 때는 `__init__`을 오버라이드한다.

```python
class ApiError(AppError):
    def __init__(self, message: str, status_code: int, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        return f"[{self.status_code}] {super().__str__()}"
```

```python
try:
    call_external_api()
except ApiError as e:
    if e.status_code == 429:
        time.sleep(retry_after)
    elif e.status_code >= 500:
        logger.error("외부 서비스 장애: %s", e.response_body)
        raise
```

`args`를 통해 접근하는 방식(`e.args[0]`, `e.args[1]`)은 쓰지 않는 게 낫다. 인덱스로 접근하면 필드 추가나 순서 변경 시 조용히 깨진다.

---

## 6. ExceptionGroup과 except*

Python 3.11에서 추가됐다. 여러 예외를 한 번에 수집해서 전파할 때 쓴다. asyncio에서 여러 태스크를 동시에 실행하고 발생한 예외를 모아서 처리할 때 주로 등장한다.

```python
# ExceptionGroup 직접 생성
eg = ExceptionGroup("여러 유효성 오류", [
    ValueError("이름이 너무 짧음"),
    TypeError("나이는 정수여야 함"),
])
raise eg
```

`except*`는 `ExceptionGroup` 안에서 특정 타입의 예외만 골라 처리한다.

```python
try:
    raise ExceptionGroup("오류 묶음", [
        ValueError("잘못된 값"),
        KeyError("없는 키"),
        ValueError("또 다른 잘못된 값"),
    ])
except* ValueError as eg:
    # ValueError 두 개가 새 ExceptionGroup으로 묶여 들어옴
    for exc in eg.exceptions:
        print(f"값 오류: {exc}")
except* KeyError as eg:
    for exc in eg.exceptions:
        print(f"키 오류: {exc}")
```

`except*`는 일반 `except`와 같은 `try` 블록에서 섞어 쓸 수 없다. `ExceptionGroup`이 아닌 일반 예외에는 `except*`가 동작하지 않는다.

`asyncio.TaskGroup`을 쓸 때 이 구조가 자연스럽게 나온다.

```python
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch_users())
            tg.create_task(fetch_orders())
    except* NetworkError as eg:
        # 두 태스크 중 하나 또는 둘 다 NetworkError를 던진 경우
        for exc in eg.exceptions:
            logger.error("네트워크 오류: %s", exc)
```

3.11 미만이라면 `asyncio.gather(return_exceptions=True)`로 비슷하게 처리하되, 각 결과를 직접 타입 체크해야 한다.

---

## 7. async 함수에서 예외 전파

`async def` 안에서 예외가 발생하면 코루틴 객체 안에 갇힌다. `await` 없이 코루틴을 호출하기만 하면 예외가 전파되지 않는다.

```python
async def risky():
    raise ValueError("실패")

# 이건 예외가 발생하지 않는 것처럼 보임
coro = risky()  # 코루틴 객체 생성만 함, 실행 안 됨

# await 해야 예외가 전파됨
await risky()  # 여기서 ValueError 발생
```

`asyncio.create_task()`로 생성한 태스크는 태스크가 완료될 때까지 예외가 보류된다. 태스크를 `await`하거나 `task.result()`를 호출하기 전까지 예외가 조용히 묻힌다.

```python
async def main():
    task = asyncio.create_task(risky())
    # task를 await하지 않으면 예외가 무시될 수 있음
    await asyncio.sleep(1)
    # task가 끝났는데도 예외 확인 안 함
```

태스크를 추적하지 않으면 `asyncio`가 태스크 GC 시점에 "Task exception was never retrieved" 경고를 출력한다. 로그에서 이 메시지가 보인다면 어딘가 예외를 놓친 태스크가 있다는 신호다.

```python
async def main():
    task = asyncio.create_task(risky())
    try:
        await task
    except ValueError as e:
        logger.error("태스크 실패: %s", e)
```

`asyncio.gather`는 기본적으로 첫 번째 예외가 발생하면 즉시 해당 예외를 전파하고 다른 코루틴은 취소된다. `return_exceptions=True`를 주면 모든 코루틴이 끝날 때까지 기다리고 결과 리스트에 예외 객체를 섞어서 돌려준다.

```python
results = await asyncio.gather(
    fetch_a(),
    fetch_b(),
    return_exceptions=True,
)

for result in results:
    if isinstance(result, Exception):
        logger.error("서브 태스크 실패: %s", result)
    else:
        process(result)
```

---

## 8. 빈 except 안티패턴

실무에서 가장 많이 보이는 문제다.

```python
# 안티패턴 1: 모든 예외를 삼킴
try:
    do_something()
except:
    pass

# 안티패턴 2: Exception 잡고 무시
try:
    do_something()
except Exception:
    pass
```

첫 번째는 `KeyboardInterrupt`까지 삼킨다. 두 번째는 `KeyboardInterrupt`는 피하지만 `do_something` 안에서 발생한 모든 예외를 조용히 무시한다.

문제는 이 패턴이 디버깅을 거의 불가능하게 만든다는 점이다. 코드가 "잘 돌아가는 것처럼 보이지만" 실제로는 절반이 실패하고 있는 상황을 만든다. 최소한 로깅이라도 해야 한다.

```python
try:
    do_something()
except Exception:
    logger.exception("예상치 못한 오류")  # 트레이스백 포함 로깅
```

`logger.exception()`은 자동으로 현재 예외의 트레이스백을 포함한다. `logger.error(str(e))`처럼 메시지만 남기면 원인 파악이 어렵다.

잡아야 할 예외는 구체적으로 명시한다. `ValueError`와 `KeyError`가 모두 발생할 수 있다면 둘을 별도 `except`로 처리하거나 `except (ValueError, KeyError)`처럼 명시적으로 묶는다. 예외 범위를 좁힐수록 의도치 않은 예외가 숨어드는 공간이 줄어든다.
