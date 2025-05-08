# SQL 인젝션(SQL Injection)

## 개념
**SQL 인젝션**(SQL Injection)은 웹 애플리케이션의 보안 취약점 중 하나로, 공격자가 웹 애플리케이션의 데이터베이스 쿼리를 조작할 수 있도록 하는 보안 취약점입니다. 이는 OWASP Top 10에서 가장 위험한 웹 애플리케이션 보안 취약점 중 하나로 꼽힙니다.

### 발생 원인
SQL 인젝션이 발생하는 주요 원인은 다음과 같습니다:
1. 사용자 입력값의 불충분한 검증
2. 동적 SQL 쿼리 생성 시 문자열 연결 사용
3. 데이터베이스 오류 메시지의 과도한 노출
4. 최소 권한 원칙 미준수

### 공격 가능한 영역
- 로그인 폼
- 검색 기능
- URL 파라미터
- HTTP 헤더
- 쿠키 값
- XML 데이터
- JSON 데이터

### 공격으로 인한 피해
1. **데이터 노출**
   - 사용자 정보
   - 비밀번호 해시
   - 개인 식별 정보
   - 금융 정보
   - 기업 기밀

2. **데이터 조작**
   - 데이터 삽입
   - 데이터 수정
   - 데이터 삭제
   - 권한 변경

3. **시스템 접근**
   - 관리자 권한 획득
   - 운영체제 명령어 실행
   - 네트워크 접근
   - 다른 시스템 침투

---

## SQL 인젝션 동작 방식

### 1. 기본적인 SQL 인젝션
```sql
-- 원본 쿼리
SELECT * FROM users WHERE username = '$username' AND password = '$password';

-- 공격자가 입력한 값
username: admin' --
password: anything

-- 변형된 쿼리
SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything';
```

### 2. UNION 기반 공격
```sql
-- 원본 쿼리
SELECT product_name, price FROM products WHERE category = '$category';

-- 공격자가 입력한 값
category: Electronics' UNION SELECT username, password FROM users --

-- 변형된 쿼리
SELECT product_name, price FROM products WHERE category = 'Electronics' 
UNION SELECT username, password FROM users --';
```

### 3. 조건부 공격
```sql
-- 원본 쿼리
SELECT * FROM articles WHERE id = $id;

-- 공격자가 입력한 값
id: 1 AND 1=1

-- 변형된 쿼리
SELECT * FROM articles WHERE id = 1 AND 1=1;
```

---

## SQL 인젝션 종류

### 1. 블라인드 SQL 인젝션 (Blind SQL Injection)
- **특징**
  - 데이터베이스 오류 메시지가 표시되지 않음
  - 참/거짓 결과만으로 데이터 추출
  - 시간 지연 기반 공격 가능

- **예시**
```sql
-- 시간 지연 기반 공격
SELECT * FROM users WHERE username = 'admin' AND IF(1=1, SLEEP(5), 0);
```

### 2. 오류 기반 SQL 인젝션 (Error-Based SQL Injection)
- **특징**
  - 데이터베이스 오류 메시지를 활용
  - 시스템 정보 추출
  - 데이터베이스 구조 파악

- **예시**
```sql
-- MySQL에서 버전 정보 추출
SELECT * FROM users WHERE id = 1 AND extractvalue(1, concat(0x5c, version()));
```

### 3. 유니온 기반 SQL 인젝션 (Union-Based SQL Injection)
- **특징**
  - UNION 연산자 사용
  - 다중 쿼리 결과 결합
  - 데이터 추출 용이

- **예시**
```sql
-- 사용자 테이블과 시스템 테이블 정보 추출
SELECT username, password FROM users WHERE id = 1 
UNION SELECT table_name, column_name FROM information_schema.columns;
```

### 4. 스토어드 프로시저 SQL 인젝션 (Stored Procedure Injection)
- **특징**
  - 저장 프로시저 내 SQL 인젝션
  - 시스템 명령어 실행 가능
  - 확장 저장 프로시저 악용

- **예시**
```sql
-- MSSQL에서 xp_cmdshell 실행
EXEC master..xp_cmdshell 'net user hacker Password123 /add';
```

---

## SQL 인젝션 예방 방법

### 1. **프리페어드 스테이트먼트(Prepared Statement) 사용**
```python
# Python 예시
import sqlite3

def safe_login(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 안전한 쿼리 실행
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                  (username, password))
    
    result = cursor.fetchone()
    conn.close()
    return result

# Java 예시
String query = "SELECT * FROM users WHERE username = ? AND password = ?";
PreparedStatement stmt = connection.prepareStatement(query);
stmt.setString(1, username);
stmt.setString(2, password);
ResultSet rs = stmt.executeQuery();
```

### 2. **입력 데이터 검증**
```python
def validate_input(input_data):
    # SQL 메타 문자 필터링
    forbidden_chars = ["'", '"', ";", "--", "/*", "*/", "xp_"]
    for char in forbidden_chars:
        if char in input_data:
            return False
    
    # 입력 길이 제한
    if len(input_data) > 100:
        return False
    
    # 정규식 패턴 검증
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', input_data):
        return False
    
    return True
```

### 3. **최소 권한 원칙 적용**
```sql
-- 데이터베이스 사용자 권한 설정
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT, INSERT ON database.users TO 'app_user'@'localhost';
REVOKE ALL PRIVILEGES ON *.* FROM 'app_user'@'localhost';
```

### 4. **웹 애플리케이션 방화벽(WAF) 설정**
```nginx
# Nginx WAF 설정 예시
location / {
    # SQL 인젝션 패턴 차단
    if ($request_uri ~* "union.*select|xp_cmdshell") {
        return 403;
    }
    
    # 특수 문자 필터링
    if ($args ~* "[;'\"<>]") {
        return 403;
    }
}
```

### 5. **데이터베이스 오류 메시지 관리**
```php
// PHP 예시
try {
    $result = $db->query($sql);
} catch (PDOException $e) {
    // 프로덕션 환경에서는 일반적인 오류 메시지만 표시
    error_log($e->getMessage());
    echo "데이터베이스 오류가 발생했습니다. 관리자에게 문의하세요.";
}
```

### 6. **ORM 사용**
```python
# Django ORM 예시
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

# 안전한 쿼리 실행
User.objects.filter(username=username, password=password)
```

---

## SQL 인젝션 테스트 방법

### 1. 수동 테스트
```sql
-- 기본 테스트
' OR '1'='1
' OR '1'='1' --
admin' --

-- UNION 테스트
' UNION SELECT null, null --
' UNION SELECT username, password FROM users --

-- 오류 기반 테스트
' AND 1=CONVERT(int,(SELECT @@version)) --
```

### 2. 자동화 도구
- **SQLmap**
  ```bash
  # 기본 스캔
  sqlmap -u "http://example.com/login.php" --forms
  
  # 데이터베이스 덤프
  sqlmap -u "http://example.com/login.php" --dump -D database
  
  # OS 쉘 획득
  sqlmap -u "http://example.com/login.php" --os-shell
  ```

- **Burp Suite**
  - Proxy 기능을 통한 요청/응답 분석
  - Intruder 기능을 통한 자동화된 테스트
  - Scanner 기능을 통한 취약점 스캔

---

## 결론
SQL 인젝션은 여전히 가장 위험한 웹 애플리케이션 취약점 중 하나입니다. 이를 방지하기 위해서는:

1. **코드 레벨에서의 방어**
   - 프리페어드 스테이트먼트 사용
   - 입력값 검증
   - ORM 활용

2. **인프라 레벨에서의 방어**
   - WAF 구성
   - 데이터베이스 권한 관리
   - 로깅 및 모니터링

3. **운영 레벨에서의 방어**
   - 정기적인 보안 점검
   - 취약점 스캔
   - 보안 패치 관리

이러한 다층적인 방어 전략을 통해 SQL 인젝션 공격으로부터 안전한 웹 애플리케이션을 구축할 수 있습니다.

