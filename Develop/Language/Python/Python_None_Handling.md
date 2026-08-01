---
title: Python None 처리
tags:
  - python
  - none
  - "null"
  - optional
  - type-narrowing
  - typing
updated: 2026-07-27
---

# Python None 처리

Python에서 None은 싱글톤이다. 프로세스 전체에서 하나만 존재한다. 이 특성 때문에 동등성 비교(`==`)가 아니라 동일성 비교(`is`)를 써야 하는데, 대부분의 경우 작동은 똑같이 하면서도 의미는 다르다. None을 제대로 다루려면 이 차이부터 명확히 해야 한다.

---

## 1. `is None` vs `== None`

`is`는 동일한 객체인지 확인한다. `==`는 `__eq__` 메서드를 호출해서 동등한지 확인한다.

```python
x = None
x is None    # True — 동일성 비교, 항상 안전
x == None    # True — __eq__ 호출, 대부분 True지만 예외 있음
```

문제는 `__eq__`를 재정의한 클래스다.

```python
import numpy as np

arr = np.array([1, 2, 3])
arr == None  # array([False, False, False]) — 예외 발생 안 함, 엉뚱한 결과
arr is None  # False — 정확하게 동작
```

pandas DataFrame도 마찬가지다. `df == None`은 원소별 비교를 시도한다. `df is None`이 의도한 동작이다.

None 체크는 항상 `is None`이나 `is not None`을 써라. `== None`은 작동하는 경우가 많지만, 커스텀 `__eq__`가 있는 객체를 만나는 순간 예상치 못한 결과가 나온다. linter(pylint, flake8)도 `== None` 쓰면 경고를 낸다.

```python
# 잘못된 패턴
if result == None:
    ...

# 올바른 패턴
if result is None:
    ...

if result is not None:
    ...
```

---

## 2. mutable default 인자와 None

Python 함수의 default 인자는 함수 정의 시점에 한 번만 평가된다. 이 때문에 mutable 객체를 default로 쓰면 함수 호출 간에 상태가 공유된다.

```python
# 버그: items는 모든 호출이 같은 리스트 객체를 공유함
def append_item(item, items=[]):
    items.append(item)
    return items

append_item(1)  # [1]
append_item(2)  # [1, 2] — 새 리스트가 아님
append_item(3)  # [1, 2, 3]
```

None을 sentinel로 쓰는 이유가 여기 있다. None은 불변(immutable)이라 공유돼도 안전하고, 함수 내부에서 매번 새 객체를 만든다.

```python
def append_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items

append_item(1)         # [1]
append_item(2)         # [2] — 독립된 리스트
append_item(3, [10])   # [10, 3] — 명시적으로 전달한 리스트
```

이 패턴은 함수 시그니처에서 "인자를 넘기지 않으면 새로 만든다"는 의도를 표현한다. `items=[]`는 그 의도를 표현하려다 버그를 만드는 코드다.

같은 함정이 딕셔너리, 셋, 커스텀 객체에도 있다.

```python
def create_config(extra_options=None):
    defaults = {"timeout": 30, "retries": 3}
    if extra_options is not None:
        defaults.update(extra_options)
    return defaults
```

---

## 3. `Optional[T]`와 `Union[T, None]`

Python 3.10 미만에서는 `typing.Optional[T]`와 `Union[T, None]`이 완전히 동일한 표현이다.

```python
from typing import Optional, Union

def find_user(user_id: int) -> Optional[str]:
    ...

# 위와 완전히 같은 의미
def find_user(user_id: int) -> Union[str, None]:
    ...
```

`Optional[str]`은 내부적으로 `Union[str, None]`으로 처리된다. mypy나 pyright 모두 동일하게 취급한다.

Python 3.10부터는 `|` 문법을 쓸 수 있다.

```python
def find_user(user_id: int) -> str | None:
    ...
```

세 표현이 런타임 동작은 같지만, 가독성에서 차이가 있다. `Optional[T]`는 "T이거나 None"이라는 의미가 명확하지만, `Optional[Optional[T]]` 같은 실수를 유발하기도 한다.

```python
# 실수: Optional[Optional[str]]은 Optional[str]과 같다
# 의도는 str | None | None 이지만 실제로는 str | None
def bad_func() -> Optional[Optional[str]]:
    ...
```

`Union[str, None]`은 여러 타입과 묶을 때 명확하다.

```python
from typing import Union

# str, int, None 중 하나
def parse(value: str) -> Union[str, int, None]:
    ...

# Python 3.10+
def parse(value: str) -> str | int | None:
    ...
```

실무에서는 Python 버전을 올릴 수 없는 프로젝트가 많아서 `Optional[T]`가 여전히 자주 쓰인다. 3.10+ 환경이면 `str | None` 형태가 더 직관적이다.

---

## 4. None 반환 vs 예외

함수가 결과를 못 만들었을 때 None을 반환할지 예외를 던질지는 "값이 없는 것이 정상적인 경우인가"로 판단한다.

None 반환이 적절한 경우:

```python
def find_user_by_email(email: str) -> Optional[User]:
    # 이메일로 유저를 못 찾는 것은 흔한 케이스
    return db.query(User).filter(User.email == email).first()

user = find_user_by_email("test@example.com")
if user is None:
    # 정상 흐름으로 처리
    return "가입되지 않은 이메일입니다"
```

예외가 적절한 경우:

```python
def get_user_by_id(user_id: int) -> User:
    # ID로 유저를 못 찾으면 데이터 정합성 문제 — 예외적인 상황
    user = db.query(User).get(user_id)
    if user is None:
        raise UserNotFoundError(f"user_id={user_id} 없음")
    return user
```

구분 기준은 호출하는 쪽의 코드를 보면 된다. None 반환이면 호출하는 쪽이 항상 `is None` 체크를 해야 한다. 예외면 예외 처리를 선택적으로 할 수 있다.

None을 쓰면 안 되는 상황이 있다. 호출 체인 중간에 None이 섞이는 경우다.

```python
def get_city(user_id: int) -> Optional[str]:
    user = find_user_by_id(user_id)
    if user is None:
        return None
    address = get_address(user)
    if address is None:
        return None
    return address.city
```

이런 코드가 길어지면 None이 어디서 왔는지 추적하기 어렵다. None 대신 예외를 쓰거나, 중간 계층에서 빠른 실패(fail fast)를 선택하는 게 낫다.

---

## 5. None의 조용한 전파와 조기 반환

None이 무서운 이유는 에러 없이 흘러가다가 한참 뒤에 문제가 터진다는 점이다.

```python
def process_order(order_id: int):
    order = fetch_order(order_id)          # None 반환 가능
    user = get_user(order.user_id)         # order가 None이면 AttributeError
    # ...
```

`fetch_order`가 None을 반환해도 즉시 오류가 안 난다. `order.user_id`에 접근하는 시점에서야 `AttributeError: 'NoneType' object has no attribute 'user_id'`가 터진다. 스택 트레이스를 보면 `process_order`의 두 번째 줄에서 터졌다는 것만 나오고, None이 어디서 왔는지 역추적해야 한다.

조기 반환(early return)으로 None을 즉시 처리한다.

```python
def process_order(order_id: int) -> Optional[ProcessResult]:
    order = fetch_order(order_id)
    if order is None:
        logger.warning("order_id=%d 주문 없음", order_id)
        return None

    user = get_user(order.user_id)
    if user is None:
        logger.error("order_id=%d user_id=%d 유저 없음", order_id, order.user_id)
        return None

    # 여기서부터 order, user 모두 None이 아님을 보장
    return do_process(order, user)
```

조기 반환을 쓰면 None 전파 지점이 명확해지고, 로그도 각 지점에서 남길 수 있다.

None이 조용히 전파되는 또 다른 케이스는 `str.format`이나 f-string이다.

```python
name = get_user_name()  # None 반환 가능
message = f"안녕하세요, {name}님"  # "안녕하세요, None님" — 오류 없음
send_email(message)  # 잘못된 내용이 전송됨
```

`None`을 문자열에 직접 쓰면 `"None"` 문자열이 된다. 이건 런타임 오류가 아니라 잘못된 데이터다. `name is None` 체크를 빠뜨리면 사용자에게 "안녕하세요, None님"이 나간다.

---

## 6. type narrowing: isinstance와 assert

TypeScript처럼 None 체크 이후 자동으로 타입이 좁혀지지 않는다. mypy와 pyright는 일부 패턴을 이해하지만, 런타임에는 아무 차이 없다.

mypy가 인식하는 narrowing 패턴:

```python
from typing import Optional

def process(value: Optional[str]) -> str:
    if value is None:
        return "default"
    # 여기서부터 mypy는 value를 str로 인식
    return value.upper()

def process2(value: Optional[str]) -> str:
    assert value is not None, "value는 None이 아니어야 함"
    # assert 이후 mypy는 str로 인식
    return value.upper()
```

`assert`는 `-O` 플래그로 최적화 실행 시 제거된다. 프로덕션에서 `-O`를 쓰는 경우는 드물지만, 안전이 중요한 코드에서는 `assert` 대신 명시적 예외를 던져라.

```python
def process(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("value는 None이 아니어야 함")
    return value.upper()
```

`isinstance`는 None 체크뿐만 아니라 여러 타입을 좁힐 때 쓴다.

```python
from typing import Union

def handle(value: Union[str, int, None]) -> str:
    if value is None:
        return "없음"
    if isinstance(value, int):
        # 여기서 value는 int
        return str(value)
    # 여기서 value는 str
    return value.upper()
```

mypy는 이 패턴을 이해하고 각 분기에서 올바른 타입을 추론한다. `isinstance` 체크 없이 `value.upper()`를 호출하면 mypy가 `int`에 `upper` 없다고 경고를 낸다.

TypeScript처럼 narrowing이 자동으로 안 되는 구간이 있다.

```python
class UserService:
    def __init__(self):
        self._cache: Optional[dict] = None

    def process(self):
        if self._cache is not None:
            # mypy는 여기서도 _cache를 Optional[dict]로 볼 수 있음
            # 다른 스레드나 메서드 호출이 _cache를 None으로 바꿀 수 있어서
            use(self._cache)
```

`self` 속성은 narrowing이 유지되지 않는 경우가 있다. 이럴 때는 지역 변수에 할당해서 narrowing을 확정한다.

```python
def process(self):
    cache = self._cache
    if cache is not None:
        # 지역 변수는 narrowing이 유지됨
        use(cache)
```

mypy의 `reveal_type()`으로 특정 지점에서 추론된 타입을 확인할 수 있다. CI에서 돌리면 에러가 나지만, 개발 중에 타입 확인 목적으로 쓴다.

```python
def process(value: Optional[str]) -> None:
    reveal_type(value)  # Revealed type is "Optional[str]"
    if value is not None:
        reveal_type(value)  # Revealed type is "str"
```
