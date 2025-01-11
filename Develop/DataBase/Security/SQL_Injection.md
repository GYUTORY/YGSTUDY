
# SQL 인젝션(SQL Injection)

## 개념
**SQL 인젝션**(SQL Injection)은 웹 애플리케이션의 보안 취약점 중 하나로, 공격자가 웹 애플리케이션의 데이터베이스 쿼리를 조작할 수 있도록 하는 보안 취약점입니다. 주로 웹 양식(input field)이나 URL 파라미터 등을 이용하여 악성 SQL 코드를 삽입하는 방식으로 이루어집니다.

공격자가 이러한 취약점을 악용하면 다음과 같은 행동을 할 수 있습니다:
- 데이터베이스의 데이터 조회
- 데이터베이스의 데이터 변경 (삽입, 수정, 삭제)
- 인증 우회
- 데이터베이스 서버의 권한 상승

---

## SQL 인젝션 동작 방식
SQL 인젝션은 웹 애플리케이션이 사용자 입력값을 직접 SQL 쿼리에 포함시킬 때 발생합니다.

### 예제 1: 취약한 로그인 시스템
```sql
SELECT * FROM users WHERE username = '$username' AND password = '$password';
```

위의 쿼리는 사용자가 입력한 `username`과 `password`를 그대로 사용하고 있습니다. 공격자가 다음과 같은 입력을 제공할 경우:

- **Username:** `admin' --`
- **Password:** `anything`

실행되는 쿼리는 다음과 같이 변형됩니다:
```sql
SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything';
```

`--` 주석 처리를 사용하여 비밀번호 확인 로직을 무시하고, `admin` 사용자로 로그인할 수 있습니다.

---

## SQL 인젝션 종류

### 1. 블라인드 SQL 인젝션 (Blind SQL Injection)
- 데이터베이스의 오류 메시지를 반환하지 않지만, 참/거짓에 따른 결과를 확인하여 데이터를 추측하는 기법.
- 예시: 참과 거짓에 따른 웹 페이지의 다른 응답을 확인.

### 2. 오류 기반 SQL 인젝션 (Error-Based SQL Injection)
- SQL 에러 메시지를 통해 데이터베이스 정보를 노출시키는 공격.
- 예시: `1=1`과 같은 조건을 사용하여 쿼리 오류 유발.

### 3. 유니온 기반 SQL 인젝션 (Union-Based SQL Injection)
- `UNION SELECT` 문을 사용하여 다중 쿼리 결과를 결합하는 공격.
- 예시:
  ```sql
  SELECT username, password FROM users WHERE id=1 UNION SELECT null, version();
  ```

### 4. 스토어드 프로시저 SQL 인젝션 (Stored Procedure Injection)
- 데이터베이스의 저장 프로시저를 조작하여 시스템 명령어 실행.

---

## SQL 인젝션 예제와 시나리오

### 시나리오: 웹사이트에서 사용자 데이터 조회
```sql
SELECT * FROM customers WHERE customer_id = '$customer_id';
```

공격자가 `customer_id` 입력란에 다음을 입력하면:
```sql
1 OR 1=1
```

결과:
```sql
SELECT * FROM customers WHERE customer_id = '1 OR 1=1';
```
모든 고객 데이터를 조회할 수 있습니다.

---

## SQL 인젝션 예방 방법

### 1. **프리페어드 스테이트먼트(Prepared Statement) 사용**
```python
import sqlite3

conn = sqlite3.connect('example.db')
cursor = conn.cursor()

username = "admin"
password = "password123"

cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
conn.commit()
conn.close()
```

### 2. **입력 데이터 검증**
- 사용자 입력 데이터에서 SQL 메타 문자(`'`, `"`, `;`, `--` 등)를 필터링.

### 3. **최소 권한 원칙 적용**
- 데이터베이스 사용자에게 최소 권한만 부여.

### 4. **웹 애플리케이션 방화벽(WAF) 사용**
- 웹 요청을 필터링하여 악성 SQL 인젝션 시도를 차단.

### 5. **데이터베이스 오류 메시지 숨기기**
- 프로덕션 환경에서는 데이터베이스 오류 메시지를 사용자에게 노출하지 않음.

---

## SQL 인젝션 테스트 도구
- **SQLmap**: 자동화된 SQL 인젝션 탐지 및 실행 도구.
- **Burp Suite**: 웹 애플리케이션 취약점 스캐너.

---

## 결론
SQL 인젝션은 웹 애플리케이션에서 흔히 발생하는 심각한 보안 취약점 중 하나입니다. 이를 방지하기 위해서는 **프리페어드 스테이트먼트** 사용, **입력값 검증**, **최소 권한 설정** 등의 보안 조치를 반드시 적용해야 합니다.

